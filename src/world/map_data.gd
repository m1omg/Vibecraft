class_name MapData
extends RefCounted
## Terrain + placement data for one map. Per-tile layers (texture index, cliff level, water,
## ramp id), explicit ramp records, start locations, mines, camps, trees.
## Heights: every tile has 4 corner heights (flat at level * CLIFF_H, ramps interpolate,
## water beds sink); `height_at` is the bilinear surface, matching the rendered mesh.

const WATER_DEPTH := 1.2
const HEIGHT_EPS := 0.05
const FORMAT_VERSION := 1

var name: String = "untitled"
var width: int = 0             ## tiles
var height: int = 0            ## tiles
var tex: PackedByteArray       ## 0..7 texture layer per tile
var cliff: PackedByteArray     ## cliff level 0..3 per tile
var water: PackedByteArray     ## 1 = water tile
var ramp: PackedByteArray      ## 0 = none, else index + 1 into `ramps`
var ramps: Array[Dictionary] = []   ## {rect: Rect2i (tiles), dir: Vector2i (ascending), low: int}
var water_level: float = -0.45
var start_locations: Array[Vector3] = []
var gold_mines: Array[Vector3] = []
var creep_camps: Array[Dictionary] = []      ## {pos: Vector3, creeps: Array[String]}
var neutral_buildings: Array[Dictionary] = [] ## {def: String, pos: Vector3}
var trees: Array[Vector2i] = []   ## tree grid coords (1 m); a tree covers cells 2x..2x+1, 2y..2y+1
var tree_types: PackedByteArray   ## index into TREE_TYPES per tree
var corner_h: PackedFloat32Array  ## 4 per tile: (x0,z0) (x1,z0) (x0,z1) (x1,z1)

const TREE_TYPES: Array[String] = ["tree_pine", "tree_round"]


func init_empty(w: int, h: int, level: int = 1, tex_index: int = 0) -> void:
	width = w
	height = h
	var n := w * h
	tex = PackedByteArray()
	tex.resize(n)
	tex.fill(tex_index)
	cliff = PackedByteArray()
	cliff.resize(n)
	cliff.fill(level)
	water = PackedByteArray()
	water.resize(n)
	ramp = PackedByteArray()
	ramp.resize(n)
	ramps.clear()
	trees.clear()
	tree_types = PackedByteArray()
	compute_heights()


func size_tiles() -> Vector2i:
	return Vector2i(width, height)


func size_cells() -> Vector2i:
	return Vector2i(width, height) * Grid.CELLS_PER_TILE


func size_world() -> Vector2:
	return Vector2(width, height) * Grid.TILE


func idx(x: int, y: int) -> int:
	return y * width + x


func in_bounds(x: int, y: int) -> bool:
	return x >= 0 and y >= 0 and x < width and y < height


func level_at_tile(x: int, y: int) -> int:
	return cliff[idx(x, y)]


func is_water_tile(x: int, y: int) -> bool:
	return in_bounds(x, y) and water[idx(x, y)] == 1


## Registers a ramp covering `rect` tiles that ascends from level `low` to `low + 1` along `dir`.
func add_ramp(rect: Rect2i, dir: Vector2i, low: int) -> void:
	ramps.append({"rect": rect, "dir": dir, "low": low})
	var id := ramps.size()
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			if in_bounds(x, y):
				ramp[idx(x, y)] = id
				cliff[idx(x, y)] = low


func ramp_height(r: Dictionary, px: float, pz: float) -> float:
	var rect: Rect2i = r["rect"]
	var dir: Vector2i = r["dir"]
	var t := 0.0
	if dir.x != 0:
		t = (px - rect.position.x * Grid.TILE) / (rect.size.x * Grid.TILE)
		if dir.x < 0:
			t = 1.0 - t
	else:
		t = (pz - rect.position.y * Grid.TILE) / (rect.size.y * Grid.TILE)
		if dir.y < 0:
			t = 1.0 - t
	return (float(r["low"]) + clampf(t, 0.0, 1.0)) * Grid.CLIFF_H


func compute_heights() -> void:
	corner_h = PackedFloat32Array()
	corner_h.resize(width * height * 4)
	for ty in height:
		for tx in width:
			var i := idx(tx, ty)
			var base := float(cliff[i]) * Grid.CLIFF_H
			for c in 4:
				var vx := tx + (c & 1)
				var vy := ty + (c >> 1)
				var h := base
				if ramp[i] > 0:
					h = ramp_height(ramps[ramp[i] - 1], vx * Grid.TILE, vy * Grid.TILE)
				elif water[i] == 1 and _vertex_all_water(vx, vy):
					h = base - WATER_DEPTH
				corner_h[i * 4 + c] = h


func corner_height(tx: int, ty: int, c: int) -> float:
	return corner_h[idx(tx, ty) * 4 + c]


func _vertex_all_water(vx: int, vy: int) -> bool:
	for oy in [-1, 0]:
		for ox in [-1, 0]:
			if not is_water_tile(vx + ox, vy + oy):
				return false
	return true


## Bilinear terrain surface height (metres) at world x/z. Clamped to the map.
func height_at(x: float, z: float) -> float:
	var fx := x / Grid.TILE
	var fz := z / Grid.TILE
	var tx := clampi(floori(fx), 0, width - 1)
	var tz := clampi(floori(fz), 0, height - 1)
	var u := clampf(fx - tx, 0.0, 1.0)
	var v := clampf(fz - tz, 0.0, 1.0)
	var b := (tz * width + tx) * 4
	var h0 := lerpf(corner_h[b], corner_h[b + 1], u)
	var h1 := lerpf(corner_h[b + 2], corner_h[b + 3], u)
	return lerpf(h0, h1, v)


func height_at_v(p: Vector3) -> float:
	return height_at(p.x, p.z)


## Wall between tile (tx-1,ty) and (tx,ty) (vertical edge at x = tx*TILE).
func has_wall_x(tx: int, ty: int) -> bool:
	if tx <= 0 or tx >= width:
		return false
	return absf(corner_height(tx - 1, ty, 1) - corner_height(tx, ty, 0)) > HEIGHT_EPS \
		or absf(corner_height(tx - 1, ty, 3) - corner_height(tx, ty, 2)) > HEIGHT_EPS


## Wall between tile (tx,ty-1) and (tx,ty) (horizontal edge at z = ty*TILE).
func has_wall_z(tx: int, ty: int) -> bool:
	if ty <= 0 or ty >= height:
		return false
	return absf(corner_height(tx, ty - 1, 2) - corner_height(tx, ty, 0)) > HEIGHT_EPS \
		or absf(corner_height(tx, ty - 1, 3) - corner_height(tx, ty, 1)) > HEIGHT_EPS


## True when the 4 tiles around grid vertex (vx,vy) disagree on its height (cliff corner).
func vertex_is_cliff(vx: int, vy: int) -> bool:
	if vx <= 0 or vy <= 0 or vx >= width or vy >= height:
		return false
	var h := corner_height(vx - 1, vy - 1, 3)
	return absf(corner_height(vx, vy - 1, 2) - h) > HEIGHT_EPS \
		or absf(corner_height(vx - 1, vy, 1) - h) > HEIGHT_EPS \
		or absf(corner_height(vx, vy, 0) - h) > HEIGHT_EPS


## Per pathing cell: 1 = blocked by terrain (water, cliff edges, map border).
func compute_blocked_cells() -> PackedByteArray:
	var cw := width * Grid.CELLS_PER_TILE
	var ch := height * Grid.CELLS_PER_TILE
	var out := PackedByteArray()
	out.resize(cw * ch)
	var k := Grid.CELLS_PER_TILE
	for ty in height:
		for tx in width:
			if water[idx(tx, ty)] == 1:
				for cy in range(ty * k, ty * k + k):
					for cx in range(tx * k, tx * k + k):
						out[cy * cw + cx] = 1
			if has_wall_x(tx, ty):
				for cy in range(ty * k, ty * k + k):
					out[cy * cw + tx * k - 1] = 1
					out[cy * cw + tx * k] = 1
			if has_wall_z(tx, ty):
				for cx in range(tx * k, tx * k + k):
					out[(ty * k - 1) * cw + cx] = 1
					out[(ty * k) * cw + cx] = 1
	for vy in range(1, height):
		for vx in range(1, width):
			if vertex_is_cliff(vx, vy):
				for oy in [-1, 0]:
					for ox in [-1, 0]:
						out[(vy * k + oy) * cw + vx * k + ox] = 1
	for x in cw:
		out[x] = 1
		out[(ch - 1) * cw + x] = 1
	for y in ch:
		out[y * cw] = 1
		out[y * cw + cw - 1] = 1
	return out


## Marches a ray against the height field. Returns Vector3.INF when nothing is hit.
func raycast(origin: Vector3, dir: Vector3, max_dist: float = 600.0) -> Vector3:
	dir = dir.normalized()
	var step := 0.5
	var prev := origin
	var t := 0.0
	var size := size_world()
	while t < max_dist:
		t += step
		var p := origin + dir * t
		if p.y <= height_at(p.x, p.z):
			var lo := prev
			var hi := p
			for i in 10:
				var mid := (lo + hi) * 0.5
				if mid.y <= height_at(mid.x, mid.z):
					hi = mid
				else:
					lo = mid
			hi.y = height_at(hi.x, hi.z)
			return hi
		prev = p
		if dir.y >= 0.0 and p.y > 50.0:
			break
		if p.y < -20.0 or (p.x < -50.0 or p.z < -50.0 or p.x > size.x + 50.0 or p.z > size.y + 50.0):
			break
	return Vector3.INF


func clamp_to_map(p: Vector3, margin: float = 0.0) -> Vector3:
	var s := size_world()
	return Vector3(clampf(p.x, margin, s.x - margin), p.y, clampf(p.z, margin, s.y - margin))


# --- serialization -------------------------------------------------------------------------

func to_dict() -> Dictionary:
	var ramp_list: Array = []
	for r in ramps:
		var rect: Rect2i = r["rect"]
		var dir: Vector2i = r["dir"]
		ramp_list.append({"rect": [rect.position.x, rect.position.y, rect.size.x, rect.size.y],
			"dir": [dir.x, dir.y], "low": r["low"]})
	var tree_list: Array = []
	for i in trees.size():
		tree_list.append([trees[i].x, trees[i].y, tree_types[i]])
	var camps: Array = []
	for c in creep_camps:
		camps.append({"pos": _v3_to_arr(c["pos"]), "creeps": c["creeps"]})
	var neutrals: Array = []
	for nb in neutral_buildings:
		neutrals.append({"def": nb["def"], "pos": _v3_to_arr(nb["pos"])})
	return {
		"version": FORMAT_VERSION, "name": name, "width": width, "height": height,
		"water_level": water_level,
		"tex": _layer_to_rows(tex), "cliff": _layer_to_rows(cliff), "water": _layer_to_rows(water),
		"ramps": ramp_list,
		"start_locations": _v3_list(start_locations),
		"gold_mines": _v3_list(gold_mines),
		"creep_camps": camps, "neutral_buildings": neutrals, "trees": tree_list,
	}


static func from_dict(d: Dictionary) -> MapData:
	var m := MapData.new()
	m.name = d.get("name", "untitled")
	m.init_empty(int(d["width"]), int(d["height"]))
	m.water_level = float(d.get("water_level", -0.45))
	m.tex = _rows_to_layer(d["tex"], m.width, m.height)
	m.cliff = _rows_to_layer(d["cliff"], m.width, m.height)
	m.water = _rows_to_layer(d.get("water", []), m.width, m.height)
	for r: Dictionary in d.get("ramps", []):
		var a: Array = r["rect"]
		m.add_ramp(Rect2i(int(a[0]), int(a[1]), int(a[2]), int(a[3])),
			Vector2i(int(r["dir"][0]), int(r["dir"][1])), int(r["low"]))
	for p: Array in d.get("start_locations", []):
		m.start_locations.append(_arr_to_v3(p))
	for p: Array in d.get("gold_mines", []):
		m.gold_mines.append(_arr_to_v3(p))
	for c: Dictionary in d.get("creep_camps", []):
		m.creep_camps.append({"pos": _arr_to_v3(c["pos"]), "creeps": c.get("creeps", [])})
	for nb: Dictionary in d.get("neutral_buildings", []):
		m.neutral_buildings.append({"def": nb["def"], "pos": _arr_to_v3(nb["pos"])})
	for t: Array in d.get("trees", []):
		m.trees.append(Vector2i(int(t[0]), int(t[1])))
		m.tree_types.append(int(t[2]) if t.size() > 2 else 0)
	m.compute_heights()
	return m


static func load_json(path: String) -> MapData:
	var text := FileAccess.get_file_as_string(path)
	var data: Variant = JSON.parse_string(text)
	if not data is Dictionary:
		push_error("MapData: cannot parse %s" % path)
		return null
	return from_dict(data)


func save_json(path: String) -> Error:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(to_dict(), " "))
	return OK


func _layer_to_rows(layer: PackedByteArray) -> Array:
	var rows: Array = []
	for y in height:
		var s := ""
		for x in width:
			s += str(layer[idx(x, y)])
		rows.append(s)
	return rows


static func _rows_to_layer(rows: Array, w: int, h: int) -> PackedByteArray:
	var out := PackedByteArray()
	out.resize(w * h)
	for y in mini(rows.size(), h):
		var s: String = rows[y]
		for x in mini(s.length(), w):
			out[y * w + x] = s.unicode_at(x) - 48
	return out


static func _v3_list(list: Array[Vector3]) -> Array:
	var out: Array = []
	for v in list:
		out.append(_v3_to_arr(v))
	return out


static func _v3_to_arr(v: Vector3) -> Array:
	return [snappedf(v.x, 0.01), snappedf(v.y, 0.01), snappedf(v.z, 0.01)]


static func _arr_to_v3(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))
