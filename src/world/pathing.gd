class_name Pathing
extends RefCounted
## Grid pathfinding over 0.5 m cells. Wraps two AStarGrid2D instances: the normal grid and an
## "inflated" grid (obstacles grown by one cell) for units with radius > LARGE_RADIUS.
## Blocking sources are tracked separately (terrain, trees, footprints) so they can be undone.
##
## Performance notes (measured on the 384x384 slice): Godot's JPS is slower than plain A* here,
## so jumping is off and every cell gets a weight scale < 1, which turns the search into
## weighted A* (heuristic x ~1.5): ~0.5 ms for a cross-map query instead of ~10-20 ms, with
## near-identical lengths after string pulling. Connected-component labels let unreachable
## goals snap to the closest reachable cell without exhausting the whole grid.

const LARGE_RADIUS := 0.5
const DEFAULT_BUDGET := 24
const SNAP_RADIUS := 24          ## cells searched when snapping a blocked goal
const REACH_RADIUS := 96         ## cells searched for the closest reachable cell
const CLEARANCE := 0.3           ## side offset checked by line_of_walk
const COST_SCALE := 0.66         ## per-cell weight scale => weighted A* (1 / 0.66 ~ 1.5)
const RELABEL_CELLS_PER_TICK := 6000
const SPLIT_WINDOW := 8          ## cells around a new obstacle searched for a local detour

var size: Vector2i               ## in cells
var max_queries_per_tick: int = DEFAULT_BUDGET
var queries_this_tick: int = 0
var total_queries: int = 0

var _terrain: PackedByteArray    ## 1 = blocked by terrain
var _trees: PackedByteArray      ## 1 = tree
var _footprints: PackedByteArray ## overlap count of building footprints
var _solid: PackedByteArray      ## combined state, normal grid
var _solid_large: PackedByteArray ## combined state grown by one cell
var _astar := AStarGrid2D.new()
var _astar_large := AStarGrid2D.new()

# Connected components (0 = solid). Merges are applied immediately; splits (cells becoming
# solid) mark labels dirty and a resumable relabel job runs a bounded amount per tick.
var _comp := PackedInt32Array()
var _comp_large := PackedInt32Array()
var _next_label: int = 1
var _labels_dirty: bool = false
var _split_rect := Rect2i()          ## cells that became solid since the last split check
var _split_rect_large := Rect2i()
var _job: Dictionary = {}


func setup(map: MapData) -> void:
	setup_raw(map.size_cells(), map.compute_blocked_cells())


## Builds from a raw blocked-cell array (used by tests and by `setup`).
func setup_raw(cells: Vector2i, terrain_blocked: PackedByteArray) -> void:
	size = cells
	var n := size.x * size.y
	_terrain = terrain_blocked.duplicate()
	if _terrain.size() != n:
		_terrain.resize(n)
	_trees = PackedByteArray()
	_trees.resize(n)
	_footprints = PackedByteArray()
	_footprints.resize(n)
	for g: AStarGrid2D in [_astar, _astar_large]:
		g.region = Rect2i(Vector2i.ZERO, size)
		g.cell_size = Vector2.ONE
		g.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
		g.default_compute_heuristic = AStarGrid2D.HEURISTIC_OCTILE
		g.default_estimate_heuristic = AStarGrid2D.HEURISTIC_OCTILE
		g.jumping_enabled = false
		g.update()
		g.fill_weight_scale_region(g.region, COST_SCALE)
	_rebuild_all()


func begin_tick() -> void:
	queries_this_tick = 0
	if _labels_dirty or not _job.is_empty():
		_relabel_step(RELABEL_CELLS_PER_TICK)


func has_budget() -> bool:
	return queries_this_tick < max_queries_per_tick


func is_walkable(c: Vector2i, large: bool = false) -> bool:
	if c.x < 0 or c.y < 0 or c.x >= size.x or c.y >= size.y:
		return false
	return (_solid_large if large else _solid)[c.y * size.x + c.x] == 0


func is_walkable_world(p: Vector3, large: bool = false) -> bool:
	return is_walkable(Vector2i(floori(p.x / Grid.CELL), floori(p.z / Grid.CELL)), large)


func is_tree(c: Vector2i) -> bool:
	return _in(c) and _trees[c.y * size.x + c.x] == 1


func set_tree(c: Vector2i, present: bool) -> void:
	if not _in(c):
		return
	var i := c.y * size.x + c.x
	_trees[i] = 1 if present else 0
	_refresh(i)
	_resolve_splits()


## Blocks (or releases) building footprint cells. Overlapping footprints are reference counted.
func set_footprint(cells: Array[Vector2i], blocked: bool) -> void:
	for c in cells:
		if not _in(c):
			continue
		var i := c.y * size.x + c.x
		_footprints[i] = clampi(_footprints[i] + (1 if blocked else -1), 0, 255)
		_refresh(i)
	_resolve_splits()


func set_footprint_rect(r: Rect2i, blocked: bool) -> void:
	set_footprint(Grid.rect_cells(r), blocked)


func is_rect_free(r: Rect2i) -> bool:
	for y in range(r.position.y, r.end.y):
		for x in range(r.position.x, r.end.x):
			if not is_walkable(Vector2i(x, y)):
				return false
	return true


## Bulk tree placement (avoids per-cell incremental updates of the inflated grid).
func set_trees_bulk(cells: Array[Vector2i]) -> void:
	for c in cells:
		if _in(c):
			_trees[c.y * size.x + c.x] = 1
	_astar.fill_solid_region(_astar.region, false)
	_astar_large.fill_solid_region(_astar_large.region, false)
	_rebuild_all()


## True when both cells are walkable and in the same connected region (labels may lag behind
## a recent split by a few ticks; they never report false negatives).
func same_region(a: Vector2i, b: Vector2i, large: bool = false) -> bool:
	if not is_walkable(a, large) or not is_walkable(b, large):
		return false
	var comp := _comp_large if large else _comp
	return comp[a.y * size.x + a.x] == comp[b.y * size.x + b.x]


# --- queries -------------------------------------------------------------------------------

## Finds a path between two world points. Blocked or unreachable goals snap to the closest
## reachable cell. The result is string-pulled and starts with `from` (y = 0; callers sample
## terrain height). Empty when the start is enclosed with no walkable cell nearby.
func find_path(from: Vector3, to: Vector3, large: bool = false) -> PackedVector3Array:
	queries_this_tick += 1
	total_queries += 1
	var grid := _astar_large if large else _astar
	var out := PackedVector3Array()
	var start := nearest_walkable(Grid.world_to_cell(from), large)
	if start.x < 0:
		return out
	var want := Grid.world_to_cell(to)
	var goal := closest_reachable(start, want, large)
	if goal.x < 0:
		return out
	var ids := grid.get_id_path(start, goal, true)
	if ids.is_empty():
		return out
	var pts := PackedVector3Array()
	pts.append(Vector3(from.x, 0.0, from.z))
	var last_dir := Vector2i.ZERO
	for i in range(1, ids.size()):
		var d := ids[i] - ids[i - 1]
		if d == last_dir and i < ids.size() - 1:
			pts[pts.size() - 1] = Grid.cell_to_world(ids[i])
		else:
			pts.append(Grid.cell_to_world(ids[i]))
		last_dir = d
	if ids[ids.size() - 1] == want and is_walkable(want, large):
		pts[pts.size() - 1] = Vector3(to.x, 0.0, to.z)
	return smooth_path(pts, large)


## Closest cell to `want` (by distance) that is reachable from `start`; `want` itself when it
## is already reachable. Falls back to the nearest walkable cell (partial A*) when nothing in
## the start's region lies within REACH_RADIUS.
func closest_reachable(start: Vector2i, want: Vector2i, large: bool = false) -> Vector2i:
	want = want.clamp(Vector2i.ZERO, size - Vector2i.ONE)
	if same_region(start, want, large):
		return want
	var comp := _comp_large if large else _comp
	var label := comp[start.y * size.x + start.x]
	for r in range(1, REACH_RADIUS + 1):
		var best := Vector2i(-1, -1)
		var best_d := INF
		for y in range(maxi(want.y - r, 0), mini(want.y + r, size.y - 1) + 1):
			var edge_row := absi(y - want.y) == r
			var step := 1 if edge_row else 2 * r
			var x := want.x - r
			while x <= want.x + r:
				if x >= 0 and x < size.x and comp[y * size.x + x] == label:
					var dd := Vector2(x - want.x, y - want.y).length_squared()
					if dd < best_d:
						best_d = dd
						best = Vector2i(x, y)
				x += step
		if best.x >= 0:
			return best
	return nearest_walkable(want, large)


## Greedy string pulling over the corner points: from each anchor, advance while the next
## waypoint is still in straight-line reach; the last reachable one becomes the new anchor.
func smooth_path(pts: PackedVector3Array, large: bool = false) -> PackedVector3Array:
	if pts.size() <= 2:
		return pts
	var out := PackedVector3Array()
	out.append(pts[0])
	var anchor := 0
	var i := 2
	while i < pts.size():
		if not line_of_walk(pts[anchor], pts[i], large):
			anchor = i - 1
			out.append(pts[anchor])
		i += 1
	out.append(pts[pts.size() - 1])
	return out


## True when a unit can walk straight from a to b: the centre line must cross only walkable
## cells, and two parallel lines offset by CLEARANCE are checked too (except at the ends) so
## paths do not shave obstacle corners.
func line_of_walk(a: Vector3, b: Vector3, large: bool = false) -> bool:
	var a2 := Vector2(a.x, a.z)
	var b2 := Vector2(b.x, b.z)
	if not _ray_clear(a2, b2, large):
		return false
	var d := b2 - a2
	var length := d.length()
	if length < CLEARANCE * 3.0:
		return true
	var dir := d / length
	var side := Vector2(-dir.y, dir.x) * CLEARANCE
	var trim := dir * CLEARANCE
	return _ray_clear(a2 + trim + side, b2 - trim + side, large) \
		and _ray_clear(a2 + trim - side, b2 - trim - side, large)


## Amanatides-Woo grid traversal: every cell the segment touches must be walkable.
func _ray_clear(a: Vector2, b: Vector2, large: bool) -> bool:
	var solid := _solid_large if large else _solid
	var inv := 1.0 / Grid.CELL
	var x := floori(a.x * inv)
	var y := floori(a.y * inv)
	var ex := floori(b.x * inv)
	var ey := floori(b.y * inv)
	var dx := b.x - a.x
	var dy := b.y - a.y
	var sx := 1 if dx > 0.0 else -1
	var sy := 1 if dy > 0.0 else -1
	var t_dx := absf(Grid.CELL / dx) if dx != 0.0 else INF
	var t_dy := absf(Grid.CELL / dy) if dy != 0.0 else INF
	var nx := (x + (1 if sx > 0 else 0)) * Grid.CELL
	var ny := (y + (1 if sy > 0 else 0)) * Grid.CELL
	var t_mx := (nx - a.x) / dx if dx != 0.0 else INF
	var t_my := (ny - a.y) / dy if dy != 0.0 else INF
	var guard := absi(ex - x) + absi(ey - y) + 2
	while guard > 0:
		if x < 0 or y < 0 or x >= size.x or y >= size.y or solid[y * size.x + x] == 1:
			return false
		if x == ex and y == ey:
			return true
		if t_mx < t_my:
			t_mx += t_dx
			x += sx
		else:
			t_my += t_dy
			y += sy
		guard -= 1
	return true


## Nearest walkable cell to `c` in growing square rings, or (-1,-1) when none within range.
func nearest_walkable(c: Vector2i, large: bool = false, max_r: int = SNAP_RADIUS) -> Vector2i:
	c = c.clamp(Vector2i.ZERO, size - Vector2i.ONE)
	if is_walkable(c, large):
		return c
	for r in range(1, max_r + 1):
		var best := Vector2i(-1, -1)
		var best_d := INF
		for y in range(c.y - r, c.y + r + 1):
			for x in range(c.x - r, c.x + r + 1):
				if absi(x - c.x) != r and absi(y - c.y) != r:
					continue
				var q := Vector2i(x, y)
				if is_walkable(q, large):
					var dd := Vector2(q - c).length_squared()
					if dd < best_d:
						best_d = dd
						best = q
		if best.x >= 0:
			return best
	return Vector2i(-1, -1)


# --- internal state ------------------------------------------------------------------------

func _in(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < size.x and c.y < size.y


func _refresh(i: int) -> void:
	var solid := _terrain[i] == 1 or _trees[i] == 1 or _footprints[i] > 0
	if solid != (_solid[i] == 1):
		_set_solid(i, solid)


## Full rebuild of both grids and component labels from the blocking layers.
@warning_ignore("integer_division")
func _rebuild_all() -> void:
	var n := size.x * size.y
	_solid = PackedByteArray()
	_solid.resize(n)
	_solid_large = PackedByteArray()
	_solid_large.resize(n)
	for i in n:
		if _terrain[i] == 0 and _trees[i] == 0 and _footprints[i] == 0:
			continue
		_solid[i] = 1
		var x := i % size.x
		var y := i / size.x
		_astar.set_point_solid(Vector2i(x, y), true)
		for oy in range(maxi(y - 1, 0), mini(y + 2, size.y)):
			for ox in range(maxi(x - 1, 0), mini(x + 2, size.x)):
				_solid_large[oy * size.x + ox] = 1
	for i in n:
		if _solid_large[i] == 1:
			_astar_large.set_point_solid(Vector2i(i % size.x, i / size.x), true)
	_job.clear()
	_labels_dirty = false
	_comp = _label_all(_solid)
	_comp_large = _label_all(_solid_large)


@warning_ignore("integer_division")
func _set_solid(i: int, solid: bool) -> void:
	_solid[i] = 1 if solid else 0
	var c := Vector2i(i % size.x, i / size.x)
	_astar.set_point_solid(c, solid)
	_update_label(_comp, _solid, i, false)
	for oy in range(-1, 2):
		for ox in range(-1, 2):
			var q := c + Vector2i(ox, oy)
			if not _in(q):
				continue
			var qi := q.y * size.x + q.x
			var s := 1 if _any_solid_around(q) else 0
			if s != _solid_large[qi]:
				_solid_large[qi] = s
				_astar_large.set_point_solid(q, s == 1)
				_update_label(_comp_large, _solid_large, qi, true)


func _any_solid_around(c: Vector2i) -> bool:
	for oy in range(-1, 2):
		for ox in range(-1, 2):
			var q := c + Vector2i(ox, oy)
			if _in(q) and _solid[q.y * size.x + q.x] == 1:
				return true
	return false


# --- connected components ------------------------------------------------------------------

func _label_all(solid: PackedByteArray) -> PackedInt32Array:
	var n := size.x * size.y
	var comp := PackedInt32Array()
	comp.resize(n)
	var queue := PackedInt32Array()
	queue.resize(n)
	for i in n:
		if solid[i] == 1 or comp[i] != 0:
			continue
		_flood(solid, comp, queue, i, _next_label, -1)
		_next_label += 1
	return comp


## Breadth-first fill of label `label` from `seed`. With `budget` >= 0 it stops early and
## returns the unfinished queue segment [head, tail) via `_job`; otherwise runs to completion.
func _flood(solid: PackedByteArray, comp: PackedInt32Array, queue: PackedInt32Array, seed: int,
		label: int, budget: int, head: int = 0, tail: int = 0) -> int:
	var w := size.x
	if seed >= 0:
		comp[seed] = label
		queue[0] = seed
		head = 0
		tail = 1
	while head < tail:
		if budget == 0:
			_job["head"] = head
			_job["tail"] = tail
			return -1
		budget -= 1
		var i := queue[head]
		head += 1
		var x := i % w
		if x > 0 and solid[i - 1] == 0 and comp[i - 1] != label:
			comp[i - 1] = label
			queue[tail] = i - 1
			tail += 1
		if x < w - 1 and solid[i + 1] == 0 and comp[i + 1] != label:
			comp[i + 1] = label
			queue[tail] = i + 1
			tail += 1
		if i >= w and solid[i - w] == 0 and comp[i - w] != label:
			comp[i - w] = label
			queue[tail] = i - w
			tail += 1
		if i + w < solid.size() and solid[i + w] == 0 and comp[i + w] != label:
			comp[i + w] = label
			queue[tail] = i + w
			tail += 1
	return budget


## Incremental label maintenance for a single cell change. New obstacles are only recorded
## here; `_resolve_splits` decides after the batch whether a global relabel is needed.
@warning_ignore("integer_division")
func _update_label(comp: PackedInt32Array, solid: PackedByteArray, i: int, large: bool) -> void:
	if solid[i] == 1:
		comp[i] = 0
		var cell := Rect2i(i % size.x, i / size.x, 1, 1)
		if large:
			_split_rect_large = cell if _split_rect_large.size == Vector2i.ZERO else _split_rect_large.merge(cell)
		else:
			_split_rect = cell if _split_rect.size == Vector2i.ZERO else _split_rect.merge(cell)
		return
	var w := size.x
	var x := i % w
	var labels: Array[int] = []
	for j: int in [i - 1 if x > 0 else -1, i + 1 if x < w - 1 else -1, i - w, i + w]:
		if j >= 0 and j < comp.size() and solid[j] == 0 and comp[j] != 0 and not labels.has(comp[j]):
			labels.append(comp[j])
	if labels.is_empty():
		comp[i] = _next_label
		_next_label += 1
		return
	comp[i] = labels[0]
	if labels.size() > 1:
		# merge: relabel the other regions into labels[0]
		var queue := PackedInt32Array()
		queue.resize(comp.size())
		_flood(solid, comp, queue, i, labels[0], -1)
	if not _job.is_empty():
		_job["restart"] = true


## A new obstacle can only split a region if the walkable cells bordering it can no longer reach
## each other. Checking that locally (inside a small window) avoids most global relabels, e.g.
## for buildings placed in the open.
func _resolve_splits() -> void:
	var needs := false
	if _split_rect.size != Vector2i.ZERO:
		needs = not _ring_connected(_solid, _split_rect)
	if not needs and _split_rect_large.size != Vector2i.ZERO:
		needs = not _ring_connected(_solid_large, _split_rect_large)
	_split_rect = Rect2i()
	_split_rect_large = Rect2i()
	if needs:
		_labels_dirty = true
		if not _job.is_empty():
			_job["restart"] = true


@warning_ignore("integer_division")
func _ring_connected(solid: PackedByteArray, rect: Rect2i) -> bool:
	var full := Rect2i(Vector2i.ZERO, size)
	var ring_rect := rect.grow(1).intersection(full)
	var win := rect.grow(SPLIT_WINDOW).intersection(full)
	var ring: Array[int] = []
	for y in range(ring_rect.position.y, ring_rect.end.y):
		for x in range(ring_rect.position.x, ring_rect.end.x):
			var i := y * size.x + x
			if not rect.has_point(Vector2i(x, y)) and solid[i] == 0:
				ring.append(i)
	if ring.size() <= 1:
		return true
	var seen := {}
	var queue: Array[int] = [ring[0]]
	seen[ring[0]] = true
	var head := 0
	while head < queue.size():
		var i := queue[head]
		head += 1
		var x := i % size.x
		var y := i / size.x
		for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var q := Vector2i(x + d.x, y + d.y)
			if not win.has_point(q):
				continue
			var qi := q.y * size.x + q.x
			if solid[qi] == 0 and not seen.has(qi):
				seen[qi] = true
				queue.append(qi)
	for i in ring:
		if not seen.has(i):
			return false
	return true


## Resumable relabel of both grids, at most `budget` cells per call.
func _relabel_step(budget: int) -> void:
	if _job.is_empty() or _job.get("restart", false):
		_labels_dirty = false
		var n := size.x * size.y
		var q := PackedInt32Array()
		q.resize(n)
		var fresh_a := PackedInt32Array()
		fresh_a.resize(n)
		var fresh_b := PackedInt32Array()
		fresh_b.resize(n)
		_job = {"grid": 0, "cursor": 0, "head": 0, "tail": 0, "queue": q, "labels": [fresh_a, fresh_b],
			"label": -1}
	while budget > 0:
		var g: int = _job["grid"]
		if g > 1:
			_comp = _job["labels"][0]
			_comp_large = _job["labels"][1]
			_job.clear()
			return
		var solid := _solid if g == 0 else _solid_large
		var comp: PackedInt32Array = _job["labels"][g]
		var queue: PackedInt32Array = _job["queue"]
		if int(_job["head"]) < int(_job["tail"]):
			var left := _flood(solid, comp, queue, -1, _job["label"], budget, _job["head"], _job["tail"])
			if left < 0:
				return
			budget = left
			_job["head"] = 0
			_job["tail"] = 0
			continue
		var cursor: int = _job["cursor"]
		while cursor < solid.size() and budget > 0 and (solid[cursor] == 1 or comp[cursor] != 0):
			cursor += 1
			budget -= 1
		_job["cursor"] = cursor
		if budget <= 0:
			return
		if cursor >= solid.size():
			_job["grid"] = g + 1
			_job["cursor"] = 0
			continue
		_job["label"] = _next_label
		_next_label += 1
		comp[cursor] = _job["label"]
		queue[0] = cursor
		_job["head"] = 0
		_job["tail"] = 1
