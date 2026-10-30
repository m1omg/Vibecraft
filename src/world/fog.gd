class_name Fog
extends SimSystem
## Fog of war and vision (owner: agent E; rules.md §14, docs/architecture.md §8; data:
## rules.vision, rules.daynight). Stage: fog. Off until `enabled` is set (Main turns it on for
## real matches from rules.vision.fog_of_war; engine tests keep the old "everything visible").
## Model:
##   - one grid per team (allies share vision, rules §14.1) at rules.vision.fog_cell (2 m, the
##     classic game's resolution; 1 m cost 4× as much per re-stamp in GDScript):
##     per cell a count of the sight sources that see it, an explored flag, and the L8 texture
##     byte (0 unexplored, 128 fogged, 255 visible) kept current as counts change;
##   - every living unit of a non-neutral player that is not hidden (in a mine) is a sight
##     source; neutral players have no fog. A source is "stamped" into its team's counts and
##     remembers the cells it marked, so it is only re-stamped when its cell, its sight radius
##     (day / night with the 3.2 s transition) or its eye level changes, and unstamped exactly
##     when it moves, dies or leaves the sim. Re-stamps are budgeted per update (cells visited);
##     the rest wait for the next update (0.1 s later), oldest first;
##   - line of sight on precomputed ray stamps: every offset of a radius knows its parent cell one
##     step nearer the viewer, so one pass in distance order decides each cell from its parent:
##     a cell is seen when its parent passes sight and its terrain level is not above the
##     viewer's eye level (cliffs block upward sight; ramps have fractional levels); a cell
##     passes sight when it is seen and its occluder top (terrain, or a tree's base level + 2,
##     rules §14.3) is not above the eye. Flyers and timed reveals ignore occluders;
##   - timed reveals (`reveal()`: Signal Shell, flares, the attack reveal of 1.5 m for 1 s when an
##     unseen attacker hits) are sources too; they expire in the sim;
##   - structures a team has seen are remembered (`seen_structure`), so their ghosts stay drawn
##     in the fog; mobile enemies are drawn only while `can_see`.
## Every tick re-stamps a slice of the sources (a third of the per-update budget, walking
## unit_list from a cursor), so a full sweep takes rules.vision.fog_update (0.1 s = 3 ticks) and the
## cost never lands on one tick; deterministic (unit_list order, no clocks). The local team's texture (L8, linear filtering) goes to the terrain / water / tree
## shaders (World.set_fog_texture) and the minimap.
## Signals (Events): fog_updated(pid) after each recompute (pid = the local player).
## Called by: Unit (find_target: no acquisition of what the player cannot see), Construction
##   (is_explored for placement), effects (reveal), HUD / minimap / selection / fx (state_at,
##   is_visible, shows), AiPlayer (only what its own fog shows), FogView (unit visibility).

const UNEXPLORED := 0
const FOGGED := 1
const VISIBLE := 2
const LEVEL_EPS := 0.05            ## eye height tolerance (flat tiles sit exactly on their level)
const LEVEL_Q := 20.0              ## eye levels are compared in 1/20 steps (re-stamp threshold)
const NO_OCCLUDER := -100.0
## Cells a single update may visit while re-stamping (≈ 60 sources at 21.9 m on 2 m cells); the
## rest wait for the next update, oldest first.
const STAMP_BUDGET := 24000
const ATTACK_REVEAL_R := 1.5
const ATTACK_REVEAL_S := 1.0

var enabled: bool = false
var cell_m: float = 1.0
var size := Vector2i.ZERO          ## grid size in cells
var update_ticks: int = 3
## Stats of the latest update (tests, perf): re-stamped sources, cells visited, deferred.
var last_stats: Dictionary = {}

var _lvl := PackedFloat32Array()   ## terrain level per cell (height / CLIFF_H; ramps fractional)
var _top := PackedFloat32Array()   ## occluder top per cell (max of the level and tree base + 2)
var _teams: Dictionary = {}        ## team id -> TeamGrid
var _sources: Dictionary = {}      ## unit id (or -reveal handle) -> Source
var _stamps: Dictionary = {}       ## radius in cells -> Stamp
var _pass := PackedByteArray()     ## scratch: does offset i pass sight
var _reveals: Array[Dictionary] = []   ## {handle, pid, pos, radius, ticks, detect}
var _next_reveal: int = 1
var _cursor: int = 0                ## unit_list index the next update starts at (deferred re-stamps)
var _image: Image
var _texture: ImageTexture
var _tex_team: int = -1


class TeamGrid:
	var counts := PackedInt32Array()
	var explored := PackedByteArray()
	var tex := PackedByteArray()          ## L8: 0 unexplored, 128 fogged, 255 visible
	var tex_dirty: bool = true
	var seen: Dictionary = {}              ## structure id -> true (ghost memory)


class Source:
	var team: int = 0
	var key: Vector4i = Vector4i(-1, -1, -1, -1)   ## cell x, cell y, radius cells, eye level q
	var flyer: bool = false
	var cells := PackedInt32Array()


class Stamp:
	var ox := PackedInt32Array()
	var oy := PackedInt32Array()
	var parent := PackedInt32Array()


func setup(w: World) -> void:
	super.setup(w)
	cell_m = maxf(float(Defs.rule("vision.fog_cell", 1.0)), 0.25)
	update_ticks = maxi(1, roundi(float(Defs.rule("vision.fog_update", 0.1)) * World.TICK_RATE))
	if w.map == null:
		return
	var sw := w.map.size_world()
	size = Vector2i(ceili(sw.x / cell_m), ceili(sw.y / cell_m))
	var n := size.x * size.y
	_lvl.resize(n)
	_top.resize(n)
	for y in size.y:
		for x in size.x:
			var c := y * size.x + x
			var l := w.map.height_at((x + 0.5) * cell_m, (y + 0.5) * cell_m) / Grid.CLIFF_H
			_lvl[c] = l
			_top[c] = l
	if bool(Defs.rule("vision.trees_block_sight", true)) and w.doodads != null:
		var lift := float(Defs.rule("vision.tree_occluder_levels", 2))
		for i in w.doodads.trees.size():
			if w.doodads.alive[i] == 1:
				_set_tree(w.doodads.trees[i], true, lift)
	if not Events.tree_felled.is_connected(_on_tree_felled):
		Events.tree_felled.connect(_on_tree_felled)


func _exit_tree() -> void:
	if Events.tree_felled.is_connected(_on_tree_felled):
		Events.tree_felled.disconnect(_on_tree_felled)


func hooks() -> Array[StringName]:
	return [&"died", &"removed", &"damaged"]


func on_unit_died(u: Unit, _killer: Unit) -> void:
	_drop_source(u.id)


func on_unit_removed(u: Unit) -> void:
	_drop_source(u.id)


## Attack reveal (rules §14.3): an attacker its victim's owner cannot see is revealed to that
## player in a 1.5 m radius for 1 s.
func on_unit_damaged(u: Unit, _amount: float, src: Unit) -> void:
	if not enabled or src == null or not src.alive or u.player_id >= PlayerState.NEUTRAL_HOSTILE:
		return
	if world.is_ally(u.player_id, src.player_id) or can_see(u.player_id, src):
		return
	reveal(u.player_id, src.pos, ATTACK_REVEAL_R, ATTACK_REVEAL_S)


# --- queries -------------------------------------------------------------------------------

func cell_of(pos: Vector3) -> Vector2i:
	return Vector2i(clampi(floori(pos.x / cell_m), 0, maxi(size.x - 1, 0)),
		clampi(floori(pos.z / cell_m), 0, maxi(size.y - 1, 0)))


func _grid_for(pid: int) -> TeamGrid:
	if pid < 0 or pid >= PlayerState.NEUTRAL_HOSTILE:
		return null
	return _team_grid(world.team_of(pid))


func _team_grid(team: int) -> TeamGrid:
	var g: TeamGrid = _teams.get(team)
	if g == null and size.x > 0:
		g = TeamGrid.new()
		var n := size.x * size.y
		g.counts.resize(n)
		g.explored.resize(n)
		g.tex.resize(n)
		_teams[team] = g
	return g


func state_at(pid: int, pos: Vector3) -> int:
	if not enabled:
		return VISIBLE
	var g := _grid_for(pid)
	if g == null:
		return VISIBLE
	var c := cell_of(pos)
	var i := c.y * size.x + c.x
	if g.counts[i] > 0:
		return VISIBLE
	return FOGGED if g.explored[i] == 1 else UNEXPLORED


func is_visible(pid: int, pos: Vector3) -> bool:
	return state_at(pid, pos) == VISIBLE


func is_explored(pid: int, pos: Vector3) -> bool:
	return state_at(pid, pos) != UNEXPLORED


## Can player `pid` see unit `u` now (rules §14.1: the cell under its centre is visible; large
## units and structures count any visible footprint cell)? Own and allied units always.
func can_see(pid: int, u: Unit) -> bool:
	if u == null or u.hidden:
		return false
	if world.is_ally(pid, u.player_id):
		return true
	if u.status.has("invisible") and not detects(pid, u.pos):
		return false        # rules §11: invisible to enemies (creeps too) unless detected
	if not enabled or pid >= PlayerState.NEUTRAL_HOSTILE:
		return true
	var g := _grid_for(pid)
	if g == null:
		return true
	if _cell_visible(g, u.pos):
		return true
	if u.footprint.size != Vector2i.ZERO or u.radius > 0.7:
		return _area_visible(g, u)
	return false


## True when a detecting reveal of `pid`'s team covers `pos` (Bronze Window rank 3; rules §11).
func detects(pid: int, pos: Vector3) -> bool:
	for r: Dictionary in _reveals:
		if r["detect"] and world.is_ally(pid, int(r["pid"])) \
				and Vector2(pos.x - r["pos"].x, pos.z - r["pos"].z).length() <= float(r["radius"]):
			return true
	return false


## Should player `pid`'s view draw unit `u`? Visible units, plus structures (and Gold Seams) the
## team has seen: their ghosts stay drawn in the fog (rules §14.1). Invisible enemies are hidden
## even with fog off.
func shows(pid: int, u: Unit) -> bool:
	if u == null:
		return true
	if not enabled:
		return can_see(pid, u)
	if can_see(pid, u):
		return true
	if u.footprint.size != Vector2i.ZERO:
		var g := _grid_for(pid)
		return g != null and g.seen.has(u.id)
	return false


## True when team of `pid` has ever seen structure `u` (its ghost is remembered).
func seen_structure(pid: int, u: Unit) -> bool:
	var g := _grid_for(pid)
	return g == null or g.seen.has(u.id)


func _cell_visible(g: TeamGrid, p: Vector3) -> bool:
	var c := cell_of(p)
	return g.counts[c.y * size.x + c.x] > 0


func _area_visible(g: TeamGrid, u: Unit) -> bool:
	var lo: Vector2i
	var hi: Vector2i
	if u.footprint.size != Vector2i.ZERO:
		var r := u.footprint
		lo = cell_of(Vector3(r.position.x * Grid.CELL, 0, r.position.y * Grid.CELL))
		hi = cell_of(Vector3(r.end.x * Grid.CELL - 0.01, 0, r.end.y * Grid.CELL - 0.01))
	else:
		lo = cell_of(u.pos - Vector3(u.radius, 0, u.radius))
		hi = cell_of(u.pos + Vector3(u.radius, 0, u.radius))
	for y in range(lo.y, hi.y + 1):
		for x in range(lo.x, hi.x + 1):
			if g.counts[y * size.x + x] > 0:
				return true
	return false


## Reveals a circle to `pid`'s team for `duration` seconds (detect: shows invisible units; not
## used yet). Ignores occluders. Returns a handle.
func reveal(pid: int, pos: Vector3, radius: float, duration: float, detect: bool = false) -> int:
	var h := _next_reveal
	_next_reveal += 1
	_reveals.append({"handle": h, "pid": pid, "pos": pos, "radius": radius,
		"ticks": maxi(1, roundi(duration * World.TICK_RATE)), "detect": detect})
	if enabled and pid < PlayerState.NEUTRAL_HOSTILE:
		var s := _source_for(-h, world.team_of(pid))
		s.flyer = true
		var c := cell_of(pos)
		_restamp(s, Vector4i(c.x, c.y, maxi(1, ceili(radius / cell_m)), 10000))
	return h


func reveals() -> Array[Dictionary]:
	return _reveals


## The team grid of `pid` as L8 bytes (0 unexplored, 128 fogged, 255 visible), row-major
## (size.x per row). Empty while fog is off.
func grid(pid: int) -> PackedByteArray:
	var g := _grid_for(pid) if enabled else null
	return g.tex if g != null else PackedByteArray()


## The local team's fog texture (L8) for the shaders and the minimap; null while fog is off.
func texture(pid: int) -> Texture2D:
	if not enabled:
		return null
	var g := _grid_for(pid)
	if g == null:
		return null
	if _texture == null or _tex_team != world.team_of(pid):
		_tex_team = world.team_of(pid)
		_image = Image.create_from_data(size.x, size.y, false, Image.FORMAT_L8, g.tex)
		_texture = ImageTexture.create_from_image(_image)
		g.tex_dirty = false
	return _texture


## Seconds-of-night factor 0..1 at sim time `t` (rules.daynight: sight moves between the day
## and night values over sight_transition seconds after dusk / dawn).
static func night_factor(t: float) -> float:
	var trans := float(Defs.rule("daynight.sight_transition", 3.2))
	var hour := DayNight.hour_at(t)
	var sec_per_hour := DayNight.DAY_LENGTH / 24.0
	var dusk := float(Defs.rule("daynight.dusk", DayNight.DUSK))
	var dawn := float(Defs.rule("daynight.dawn", DayNight.DAWN))
	var since_dusk := fposmod(hour - dusk, 24.0) * sec_per_hour
	var since_dawn := fposmod(hour - dawn, 24.0) * sec_per_hour
	if since_dawn < since_dusk:     # day: the last change was dawn
		return 1.0 - clampf(since_dawn / maxf(trans, 0.001), 0.0, 1.0)
	return clampf(since_dusk / maxf(trans, 0.001), 0.0, 1.0)


func sight_of(u: Unit, night: float) -> float:
	return lerpf(u.sight, u.sight_night, night)


# --- the tick --------------------------------------------------------------------------------

func sim_tick(w: World, _dt: float) -> void:
	var i := _reveals.size() - 1
	while i >= 0:
		_reveals[i]["ticks"] = int(_reveals[i]["ticks"]) - 1
		if int(_reveals[i]["ticks"]) <= 0:
			_drop_source(-int(_reveals[i]["handle"]))
			_reveals.remove_at(i)
		i -= 1
	if not enabled or size.x == 0:
		return
	_sweep(w, ceili(float(STAMP_BUDGET) / update_ticks), false)


## Recomputes every source now, with no budget (boot, tests).
func update_now(w: World) -> void:
	_cursor = 0
	_sweep(w, 1 << 30, true)


## Walks unit_list from the cursor, re-stamping sources whose cell, radius or eye level changed,
## until `budget` cells were visited or the whole list was walked; at the end of the list (a full
## sweep) the structure memory, the texture and fog_updated follow.
func _sweep(w: World, budget: int, full: bool) -> void:
	var night := night_factor(w.time)
	var restamped := 0
	var visited := 0
	var deferred := 0
	var count := w.unit_list.size()
	var start := mini(_cursor, count)
	var idx := start
	while idx < count:
		var u: Unit = w.unit_list[idx]
		if not _is_source(u):
			if _sources.has(u.id):
				_drop_source(u.id)
			idx += 1
			continue
		var c := cell_of(u.pos)
		var r := maxi(1, ceili(sight_of(u, night) / cell_m - 0.5))
		var eye := 10000 if u.is_flying else roundi((w.map.height_at(u.pos.x, u.pos.z) / Grid.CLIFF_H + LEVEL_EPS) * LEVEL_Q)
		var key := Vector4i(c.x, c.y, r, eye)
		var s: Source = _sources.get(u.id)
		if s != null and s.key == key:
			idx += 1
			continue
		var cost := _stamp_of(r).ox.size()
		if budget < cost and not full:
			deferred += 1
			break   # the rest of the list waits for the next tick
		if s == null:
			s = _source_for(u.id, w.team_of(u.player_id))
		s.flyer = u.is_flying
		_restamp(s, key)
		budget -= cost
		visited += cost
		restamped += 1
		idx += 1
	_cursor = idx
	last_stats = {"restamped": restamped, "visited": visited, "deferred": deferred, "sources": _sources.size()}
	_upload(w)
	if idx >= count:
		_cursor = 0
		_update_seen(w)
		Events.fog_updated.emit(w.local_player_id)


func _is_source(u: Unit) -> bool:
	return u.alive and not u.hidden and not u.is_item and not u.is_resource \
		and u.player_id >= 0 and u.player_id < PlayerState.NEUTRAL_HOSTILE


func _source_for(key: int, team: int) -> Source:
	var s: Source = _sources.get(key)
	if s == null:
		s = Source.new()
		s.team = team
		_sources[key] = s
	return s


func _drop_source(key: int) -> void:
	var s: Source = _sources.get(key)
	if s == null:
		return
	_unstamp(s)
	_sources.erase(key)


func _unstamp(s: Source) -> void:
	var g := _team_grid(s.team)
	if g == null or s.cells.is_empty():
		s.key = Vector4i(-1, -1, -1, -1)
		return
	# packed arrays are copy-on-write: take them out of the grid so the writes do not copy them
	var counts := g.counts
	g.counts = PackedInt32Array()
	var tex := g.tex
	g.tex = PackedByteArray()
	for c in s.cells:
		var n := counts[c] - 1
		counts[c] = n
		if n == 0:
			tex[c] = 128
	g.counts = counts
	g.tex = tex
	g.tex_dirty = true
	s.cells = PackedInt32Array()
	s.key = Vector4i(-1, -1, -1, -1)


## Unstamps the source and stamps it again at `key` (cell x, cell y, radius cells, eye level q).
func _restamp(s: Source, key: Vector4i) -> void:
	_unstamp(s)
	s.key = key
	var g := _team_grid(s.team)
	if g == null:
		return
	var st := _stamp_of(key.z)
	var ox := st.ox
	var oy := st.oy
	var par := st.parent
	var n := ox.size()
	# take the packed arrays out of their owners while writing (copy-on-write would copy them)
	var passes := _pass
	_pass = PackedByteArray()
	if passes.size() < n:
		passes.resize(n)
	var counts := g.counts
	g.counts = PackedInt32Array()
	var explored := g.explored
	g.explored = PackedByteArray()
	var tex := g.tex
	g.tex = PackedByteArray()
	var lvl := _lvl
	var top := _top
	var w := size.x
	var h := size.y
	var cx := key.x
	var cy := key.y
	var eye := float(key.w) / LEVEL_Q
	var flyer := s.flyer
	var cells := PackedInt32Array()
	cells.resize(n)
	var k := 0
	for i in n:
		var x := cx + ox[i]
		var y := cy + oy[i]
		if x < 0 or y < 0 or x >= w or y >= h:
			passes[i] = 0
			continue
		if i > 0 and passes[par[i]] == 0:
			passes[i] = 0
			continue
		var c := y * w + x
		if not flyer and lvl[c] > eye:
			passes[i] = 0     # cannot see up: unseen, and it hides what lies behind
			continue
		var cnt := counts[c] + 1
		counts[c] = cnt
		if cnt == 1:
			tex[c] = 255
			explored[c] = 1
		cells[k] = c
		k += 1
		passes[i] = 1 if flyer or top[c] <= eye else 0
	cells.resize(k)
	s.cells = cells
	_pass = passes
	g.counts = counts
	g.explored = explored
	g.tex = tex
	g.tex_dirty = true


## The ray stamp of radius `r` cells: offsets in distance order (ties by y, then x), each with
## the index of its parent one step nearer the centre.
func _stamp_of(r: int) -> Stamp:
	var st: Stamp = _stamps.get(r)
	if st != null:
		return st
	st = Stamp.new()
	var list: Array = []
	var r2 := (r + 0.5) * (r + 0.5)
	for dy in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var d2 := dx * dx + dy * dy
			if d2 <= r2:
				list.append(Vector3i(d2, dy, dx))
	list.sort()
	var index := {}
	for i in list.size():
		var v: Vector3i = list[i]
		st.ox.append(v.z)
		st.oy.append(v.y)
		index[Vector2i(v.z, v.y)] = i
	st.parent.resize(list.size())
	st.parent[0] = -1
	for i in range(1, list.size()):
		var dx := st.ox[i]
		var dy := st.oy[i]
		var d := sqrt(float(dx * dx + dy * dy))
		var f := (d - 1.0) / d
		var p := Vector2i(roundi(dx * f), roundi(dy * f))
		var pi: int = index.get(p, -1)
		if pi < 0 or pi >= i:
			p = Vector2i(dx - signi(dx), dy - signi(dy))
			pi = index.get(p, 0)
		st.parent[i] = pi
	_stamps[r] = st
	return st


func _set_tree(g: Vector2i, present: bool, lift: float) -> void:
	var x := floori((g.x + 0.5) / cell_m)
	var y := floori((g.y + 0.5) / cell_m)
	if x < 0 or y < 0 or x >= size.x or y >= size.y:
		return
	var c := y * size.x + x
	_top[c] = _lvl[c] + lift if present else _lvl[c]


## A felled tree stops occluding: its cell's top drops to the terrain and every source that can
## reach it is re-stamped on the next update.
func _on_tree_felled(pos: Vector3) -> void:
	if size.x == 0:
		return
	_set_tree(Vector2i(floori(pos.x), floori(pos.z)), false, 0.0)
	if not enabled:
		return
	var c := cell_of(pos)
	for key: int in _sources:
		var s: Source = _sources[key]
		var dx := s.key.x - c.x
		var dy := s.key.y - c.y
		if dx * dx + dy * dy <= (s.key.z + 1) * (s.key.z + 1):
			s.key = Vector4i(-1, -1, -1, -1)   # forces a re-stamp (the old cells stay counted until then)


## Every structure (and Gold Seam) of another team that a team sees now is remembered.
func _update_seen(w: World) -> void:
	for team: int in _teams:
		var g: TeamGrid = _teams[team]
		for u: Unit in w.unit_list:
			if u.footprint.size == Vector2i.ZERO or not u.alive or g.seen.has(u.id):
				continue
			if u.player_id < PlayerState.NEUTRAL_HOSTILE and w.team_of(u.player_id) == team:
				continue
			if _cell_visible(g, u.pos) or _area_visible(g, u):
				g.seen[u.id] = true


func _upload(w: World) -> void:
	if _texture == null:
		return
	var g := _team_grid(w.team_of(w.local_player_id))
	if g == null or not g.tex_dirty:
		return
	_image.set_data(size.x, size.y, false, Image.FORMAT_L8, g.tex)
	_texture.update(_image)
	g.tex_dirty = false
