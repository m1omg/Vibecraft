class_name MapGenerator
extends RefCounted
## Deterministic generator for the 96x96 test slice: point-symmetric (180 deg) two-player map
## with a level-0 basin + lake in the middle, level-2 plateaus (one level-3 hill each), ramps,
## forest borders/clusters, two start locations with gold mines and four creep camps.

const SIZE := 96
const RAMP_HALF_W := 1        ## ramp width = 2 * RAMP_HALF_W + 1 tiles
const START_TILE := Vector2i(77, 18)   ## player 1 (NE); player 0 is the mirror (SW)
const MINE_OFFSET := Vector3(8.0, 0.0, -6.0)      ## metres, relative to the NE start
const LUMBER_DIR := Vector2(1.0, 0.35)             ## NE start lumber band direction

# Texture layers (see terrain.gdshader)
const T_GRASS := 0
const T_DARK_GRASS := 1
const T_DIRT := 2
const T_ROUGH := 3
const T_ROCK := 4
const T_SAND := 5
const T_DRY := 6
const T_PAVED := 7

var m: MapData
var noise: FastNoiseLite
var rng: RandomNumberGenerator
var _locked: PackedByteArray   ## tiles reserved by ramps and their approaches
var _ramp_centres: Array[Vector3] = []


static func test_map(seed_value: int = 1337) -> MapData:
	return MapGenerator.new().build(seed_value)


func build(seed_value: int) -> MapData:
	m = MapData.new()
	m.name = "test_slice"
	m.init_empty(SIZE, SIZE, 1, T_GRASS)
	noise = FastNoiseLite.new()
	noise.seed = seed_value
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	rng = RandomNumberGenerator.new()
	rng.seed = seed_value
	_locked = PackedByteArray()
	_locked.resize(SIZE * SIZE)
	_shape_levels()
	_place_ramps()
	_place_lake()
	m.compute_heights()
	_place_starts_and_mines()
	_place_camps()
	_paint_textures()
	_place_trees()
	return m


static func mirror_tile(t: Vector2i) -> Vector2i:
	return Vector2i(SIZE - 1 - t.x, SIZE - 1 - t.y)


static func mirror_world(p: Vector3) -> Vector3:
	return Vector3(SIZE * Grid.TILE - p.x, p.y, SIZE * Grid.TILE - p.z)


# --- cliff levels --------------------------------------------------------------------------

func _shape_levels() -> void:
	var centre := Vector2(SIZE * 0.5, SIZE * 0.5)
	_blob(centre, 15.0, 2.5, 0, 11.0)
	_blob(Vector2(24, 24), 10.0, 2.0, 2, 23.0)
	_blob(Vector2(20, 20), 4.5, 1.0, 3, 37.0)
	_flatten_disc(Vector2(START_TILE) + Vector2(0.5, 0.5), 13.0, 1)
	_mirror_layer(m.cliff)


## Sets tiles inside a noisy circle to `level` (only raising/lowering tiles by one feature).
func _blob(c: Vector2, radius: float, wobble: float, level: int, salt: float) -> void:
	for y in SIZE:
		for x in SIZE:
			var p := Vector2(x + 0.5, y + 0.5) - c
			var ang := p.angle()
			var r := radius + wobble * noise.get_noise_2d(cos(ang) * 30.0 + salt * 13.0,
				sin(ang) * 30.0 + salt * 7.0)
			if p.length() < r:
				m.cliff[m.idx(x, y)] = level


func _flatten_disc(c: Vector2, radius: float, level: int) -> void:
	for y in SIZE:
		for x in SIZE:
			if Vector2(x + 0.5, y + 0.5).distance_to(c) < radius:
				m.cliff[m.idx(x, y)] = level


## Copies the first half (by index) onto the second half rotated 180 degrees.
@warning_ignore("integer_division")
func _mirror_layer(layer: PackedByteArray) -> void:
	var n := SIZE * SIZE
	for i in range(n / 2, n):
		layer[i] = layer[n - 1 - i]


# --- ramps ---------------------------------------------------------------------------------

@warning_ignore("integer_division")
func _place_ramps() -> void:
	var centre := Vector2i(SIZE / 2 - 1, SIZE / 2 - 1)
	# basin <-> base level, one per side
	_ramp_pair(centre, Vector2i(-1, 0))
	_ramp_pair(centre, Vector2i(0, -1))
	# plateau <-> base level
	_ramp_pair(Vector2i(24, 24), Vector2i(1, 0))
	_ramp_pair(Vector2i(24, 24), Vector2i(0, 1))
	# hill <-> plateau
	_ramp_pair(Vector2i(20, 20), Vector2i(1, 0))


func _ramp_pair(from: Vector2i, dir: Vector2i) -> void:
	_ramp_on_ray(from, dir)
	_ramp_on_ray(mirror_tile(from), -dir)


## Walks from `from` along `dir` to the first level change and cuts a ramp across it.
func _ramp_on_ray(from: Vector2i, dir: Vector2i) -> void:
	var inner := m.level_at_tile(from.x, from.y)
	var p := from
	while m.in_bounds(p.x + dir.x, p.y + dir.y) and m.level_at_tile(p.x, p.y) == inner:
		p += dir
	var outer := m.level_at_tile(p.x, p.y)
	if absi(outer - inner) != 1:
		push_warning("MapGenerator: no single-level boundary from %s along %s" % [from, dir])
		return
	var asc := dir if outer > inner else -dir
	var low := mini(inner, outer)
	var low_tile := (p - dir) if outer > inner else p
	_cut_ramp(low_tile, asc, low)


func _cut_ramp(low_tile: Vector2i, asc: Vector2i, low: int) -> void:
	var lat := Vector2i(absi(asc.y), absi(asc.x))
	var high_tile := low_tile + asc
	for l in range(-RAMP_HALF_W - 1, RAMP_HALF_W + 2):
		for k in [1, 2, 3]:
			_force_tile(low_tile - asc * k + lat * l, low)
			_force_tile(high_tile + asc * k + lat * l, low + 1)
		_force_tile(low_tile + lat * l, low)
		_force_tile(high_tile + lat * l, low + 1)
	var a := low_tile - lat * RAMP_HALF_W
	var b := high_tile + lat * RAMP_HALF_W
	var rect := Rect2i(Vector2i(mini(a.x, b.x), mini(a.y, b.y)),
		Vector2i(absi(b.x - a.x) + 1, absi(b.y - a.y) + 1))
	m.add_ramp(rect, asc, low)
	var c := Vector3((rect.position.x + rect.size.x * 0.5) * Grid.TILE, 0.0,
		(rect.position.y + rect.size.y * 0.5) * Grid.TILE)
	_ramp_centres.append(c)


func _force_tile(t: Vector2i, level: int) -> void:
	if not m.in_bounds(t.x, t.y):
		return
	var i := m.idx(t.x, t.y)
	m.cliff[i] = level
	m.ramp[i] = 0
	_locked[i] = 1


# --- water ---------------------------------------------------------------------------------

@warning_ignore("integer_division")
func _place_lake() -> void:
	var c := Vector2(SIZE * 0.5, SIZE * 0.5)
	for y in SIZE / 2:
		for x in SIZE:
			var p := Vector2(x + 0.5, y + 0.5) - c
			var r := 6.0 + 1.5 * noise.get_noise_2d(cos(p.angle()) * 25.0 + 300.0, sin(p.angle()) * 25.0)
			if p.length() < r and _level0_neighbourhood(x, y, 2):
				m.water[m.idx(x, y)] = 1
	_mirror_layer(m.water)


func _level0_neighbourhood(x: int, y: int, r: int) -> bool:
	for oy in range(-r, r + 1):
		for ox in range(-r, r + 1):
			if not m.in_bounds(x + ox, y + oy):
				return false
			var i := m.idx(x + ox, y + oy)
			if m.cliff[i] != 0 or m.ramp[i] != 0:
				return false
	return true


# --- placements ----------------------------------------------------------------------------

func _place_starts_and_mines() -> void:
	var s1 := Grid.tile_to_world(START_TILE)
	s1.y = m.height_at(s1.x, s1.z)
	var s0 := mirror_world(s1)
	m.start_locations = [s0, s1]
	var mine1 := s1 + MINE_OFFSET
	mine1.y = m.height_at(mine1.x, mine1.z)
	m.gold_mines = [mirror_world(mine1), mine1]


func _place_camps() -> void:
	var spots: Array[Vector2i] = [Vector2i(28, 28), Vector2i(36, 55)]
	var creeps: Array = [["dummy_creep", "dummy_creep", "dummy_creep"], ["dummy_creep", "dummy_creep"]]
	for i in spots.size():
		for t: Vector2i in [spots[i], mirror_tile(spots[i])]:
			var p := Grid.tile_to_world(t)
			p.y = m.height_at(p.x, p.z)
			m.creep_camps.append({"pos": p, "creeps": creeps[i].duplicate()})


# --- textures ------------------------------------------------------------------------------

func _paint_textures() -> void:
	for y in SIZE:
		for x in SIZE:
			m.tex[m.idx(x, y)] = _tile_texture(x, y)
	for s in m.start_locations:
		_paint_disc(s, 9.0, T_PAVED)
		_paint_disc(s, 14.0, T_DIRT, true)
	for g in m.gold_mines:
		_paint_disc(g, 6.0, T_DIRT)
	for c in m.creep_camps:
		_paint_disc(c["pos"], 5.0, T_ROUGH)


func _tile_texture(x: int, y: int) -> int:
	var i := m.idx(x, y)
	var n1 := noise.get_noise_2d(x * 4.0 + 500.0, y * 4.0)
	var n2 := noise.get_noise_2d(x * 6.0, y * 6.0 + 900.0)
	if m.water[i] == 1:
		return T_SAND if n1 > 0.0 else T_DIRT
	if m.ramp[i] > 0:
		return T_ROUGH
	if _near_water(x, y):
		return T_SAND
	match m.cliff[i]:
		0:
			return T_DIRT if n1 > 0.1 else (T_DRY if n2 > 0.3 else T_GRASS)
		2:
			return T_ROUGH if n1 > 0.35 else T_DARK_GRASS
		3:
			return T_ROCK if n2 > -0.2 else T_ROUGH
	if n1 > 0.3:
		return T_DARK_GRASS
	if n2 > 0.4:
		return T_DRY
	return T_GRASS


func _near_water(x: int, y: int) -> bool:
	for oy in range(-1, 2):
		for ox in range(-1, 2):
			if m.is_water_tile(x + ox, y + oy):
				return true
	return false


func _paint_disc(p: Vector3, radius_m: float, layer: int, only_grass: bool = false) -> void:
	var t := Grid.world_to_tile(p)
	var r := ceili(radius_m / Grid.TILE)
	for y in range(t.y - r, t.y + r + 1):
		for x in range(t.x - r, t.x + r + 1):
			if not m.in_bounds(x, y):
				continue
			var d := Vector2((x + 0.5) * Grid.TILE - p.x, (y + 0.5) * Grid.TILE - p.z).length()
			var jitter := noise.get_noise_2d(x * 9.0, y * 9.0) * 2.0
			if d + jitter > radius_m:
				continue
			var i := m.idx(x, y)
			if m.ramp[i] > 0 or m.water[i] == 1:
				continue
			if only_grass and m.tex[i] == T_PAVED:
				continue
			m.tex[i] = layer


# --- trees ---------------------------------------------------------------------------------

@warning_ignore("integer_division")
func _place_trees() -> void:
	var blocked := m.compute_blocked_cells()
	var cw := m.width * Grid.CELLS_PER_TILE
	var tw := m.width * 2   # tree grid size (1 m)
	var half := tw * tw / 2
	var forest := FastNoiseLite.new()
	forest.seed = noise.seed + 17
	forest.frequency = 0.035
	for gy in tw:
		for gx in tw:
			if gy * tw + gx >= half:
				continue
			if not _tree_wanted(gx, gy, forest, blocked, cw):
				continue
			var mg := Vector2i(tw - 1 - gx, tw - 1 - gy)
			var type := 0 if rng.randf() < 0.7 else 1
			m.trees.append(Vector2i(gx, gy))
			m.tree_types.append(type)
			m.trees.append(mg)
			m.tree_types.append(type)
	for t in m.trees:
		var i := m.idx(t.x / 2, t.y / 2)
		if m.tex[i] == T_GRASS or m.tex[i] == T_DRY:
			m.tex[i] = T_DARK_GRASS


@warning_ignore("integer_division")
func _tree_wanted(gx: int, gy: int, forest: FastNoiseLite, blocked: PackedByteArray, cw: int) -> bool:
	for oy in 2:
		for ox in 2:
			if blocked[(gy * 2 + oy) * cw + gx * 2 + ox] == 1:
				return false
	var tile := Vector2i(gx / 2, gy / 2)
	var ti := m.idx(tile.x, tile.y)
	if m.ramp[ti] > 0 or _locked[ti] == 1:
		return false
	var p := Vector3(gx + 0.5, 0.0, gy + 0.5)
	var lumber_band := false
	for s in m.start_locations:
		var d := Grid.flat_dist(p, s)
		if d < 16.0:
			return false
		if d < 24.0 and _in_lumber_band(p, s):
			lumber_band = true
	for g in m.gold_mines:
		if Grid.flat_dist(p, g) < 7.0:
			return false
	for c in m.creep_camps:
		if Grid.flat_dist(p, c["pos"]) < 7.0:
			return false
	for r in _ramp_centres:
		if Grid.flat_dist(p, r) < 8.0:
			return false
	var size := m.size_world()
	var edge := minf(minf(p.x, p.z), minf(size.x - p.x, size.y - p.z))
	if edge < 6.0 + 3.0 * forest.get_noise_2d(gx * 3.0, gy * 3.0):
		return true
	if lumber_band:
		return rng.randf() > 0.08
	if m.cliff[ti] == 0 and _near_water(tile.x, tile.y):
		return false
	return forest.get_noise_2d(gx, gy) > 0.3 and rng.randf() > 0.12


func _in_lumber_band(p: Vector3, start: Vector3) -> bool:
	var dir := LUMBER_DIR.normalized()
	if start.x < m.size_world().x * 0.5:
		dir = -dir
	var to := Vector2(p.x - start.x, p.z - start.z)
	return to.length() > 17.0 and to.normalized().dot(dir) > cos(deg_to_rad(55.0))
