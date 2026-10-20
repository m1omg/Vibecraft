class_name TerrainBuilder
extends Node3D
## Builds the terrain as chunked ArrayMeshes (CHUNK_TILES x CHUNK_TILES tiles per chunk): tile tops
## (2x2 subdivided) at their corner heights, cliff walls with noise bulges (UV2.x = 1, UV2.y = height
## fraction up the wall for the painted lip and dark foot) and the water plane.
## Ground look (terrain.gdshader): the Greenvale 7-tile ladder (TerrainTextures) blended WC3-style
## with a 16-case corner mask on the dual grid of tile centres. Per-tile data lives in `tile_info`
## (RG8, nearest): R = ladder slot (0 scree .. 6 thick meadow), G = 8 connectivity bits (+x, -x,
## +z, -z, then the 4 diagonals) so textures never blend across a cliff wall. `paint_tiles()`
## repaints it at runtime (building pads). Vertex COLOR on tile tops: r = cliff-foot AO, g = cliff-top
## lip. Visual only: the sim reads MapData, never this node.

const CHUNK_TILES := 16
const WALL_COLS := 4
const WALL_ROW_H := 0.45
const WALL_JITTER := 0.42
const TERRAIN_SHADER := preload("res://src/world/terrain.gdshader")
const WATER_SHADER := preload("res://src/world/water.gdshader")
## MapData legacy layer index (0 grass, 1 dark grass, 2 dirt, 3 rough, 4 rock, 5 sand, 6 dry grass,
## 7 paved) -> Greenvale ladder slot. Maps authored in ladder order set `tex_set = "gv_ladder"`.
const LEGACY_TO_LADDER: Array[int] = [5, 6, 2, 1, 0, 4, 4, 3]
const CONNECT_BITS: Array[Vector2i] = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1),
	Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]

var map: MapData
var material: ShaderMaterial
var water_material: ShaderMaterial
var chunks: Array[MeshInstance3D] = []
var water: MeshInstance3D
var tile_info: ImageTexture
var height_tex: ImageTexture

var _info: Image
var _noise := FastNoiseLite.new()

# per-chunk scratch buffers
var _v := PackedVector3Array()
var _n := PackedVector3Array()
var _c := PackedColorArray()
var _uv2 := PackedVector2Array()
var _idx := PackedInt32Array()


func build(m: MapData) -> void:
	map = m
	for c in get_children():
		c.queue_free()
	chunks.clear()
	_noise.seed = 4242
	_noise.frequency = 0.9
	_build_tile_info()
	_build_height_tex()
	material = ShaderMaterial.new()
	material.shader = TERRAIN_SHADER
	material.set_shader_parameter("map_size_m", map.size_world())
	material.set_shader_parameter("map_tiles", Vector2(map.width, map.height))
	material.set_shader_parameter("tile_info", tile_info)
	material.set_shader_parameter("ground_tex", TerrainTextures.ladder_array())
	material.set_shader_parameter("cliff_tex", TerrainTextures.mipmapped("cliff_limestone.png", Color("#7D766A")))
	material.set_shader_parameter("water_level", map.water_level)
	RenderAtmos.register(material)
	var ncx := ceili(float(map.width) / CHUNK_TILES)
	var ncy := ceili(float(map.height) / CHUNK_TILES)
	for cy in ncy:
		for cx in ncx:
			var mi := MeshInstance3D.new()
			mi.name = "Chunk_%d_%d" % [cx, cy]
			mi.mesh = _build_chunk(cx, cy)
			mi.material_override = material
			mi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
			add_child(mi)
			chunks.append(mi)
	_build_water()


func _exit_tree() -> void:
	RenderAtmos.unregister(material)
	RenderAtmos.unregister(water_material)


func set_fog_texture(tex: Texture2D) -> void:
	for mat: ShaderMaterial in [material, water_material]:
		if mat != null:
			mat.set_shader_parameter("fog_tex", tex)
			mat.set_shader_parameter("fog_enabled", tex != null)


## Ladder slot shown on a tile (after the visual overrides).
func ladder_at(tx: int, ty: int) -> int:
	return _info.get_pixel(tx, ty).r8 if _info != null else -1


## Repaints tiles (e.g. a building pad: kingdom gv_dirt, clans gv_grassy_dirt; bible §6.1).
## Water and ramp tiles keep their look. Visual only.
func paint_tiles(rect: Rect2i, ladder: int) -> void:
	if _info == null:
		return
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			if not map.in_bounds(x, y) or map.water[map.idx(x, y)] == 1 or map.ramp[map.idx(x, y)] > 0:
				continue
			var px := _info.get_pixel(x, y)
			_info.set_pixel(x, y, Color8(ladder, px.g8, 0, 255))
	tile_info.update(_info)


# --- tile data -----------------------------------------------------------------------------

func _layer_table() -> Array[int]:
	var ts: Variant = map.get("tex_set")
	if ts != null and str(ts) == "gv_ladder":
		return [0, 1, 2, 3, 4, 5, 6, 6]
	return LEGACY_TO_LADDER


func _build_tile_info() -> void:
	var table := _layer_table()
	_info = Image.create(map.width, map.height, false, Image.FORMAT_RGBA8)
	for ty in map.height:
		for tx in map.width:
			var i := map.idx(tx, ty)
			var slot := table[clampi(map.tex[i], 0, 7)]
			if map.ramp[i] > 0:
				slot = TerrainTextures.DIRT
			elif map.water[i] == 0 and _at_cliff_foot(tx, ty) and slot != TerrainTextures.ROAD \
					and slot != TerrainTextures.DIRT and _hash(tx, ty) < 0.8:
				slot = TerrainTextures.SCREE   # bible §6.2: a band of scree at every cliff base
			var bits := 0
			for b in CONNECT_BITS.size():
				if _connected(tx, ty, CONNECT_BITS[b]):
					bits |= 1 << b
			_info.set_pixel(tx, ty, Color8(slot, bits, 0, 255))
	tile_info = ImageTexture.create_from_image(_info)


## A neighbour shares a surface with this tile (no wall in between): textures may blend.
func _connected(tx: int, ty: int, d: Vector2i) -> bool:
	if not map.in_bounds(tx + d.x, ty + d.y):
		return false
	if d.x != 0 and d.y != 0:
		return (_connected(tx, ty, Vector2i(d.x, 0)) and _connected(tx + d.x, ty, Vector2i(0, d.y))) \
			or (_connected(tx, ty, Vector2i(0, d.y)) and _connected(tx, ty + d.y, Vector2i(d.x, 0)))
	if d.x == 1:
		return not map.has_wall_x(tx + 1, ty)
	if d.x == -1:
		return not map.has_wall_x(tx, ty)
	if d.y == 1:
		return not map.has_wall_z(tx, ty + 1)
	return not map.has_wall_z(tx, ty)


## True when a wall rises from one of this tile's edges (it is the lower side).
func _at_cliff_foot(tx: int, ty: int) -> bool:
	var h := _tile_height(tx, ty)
	for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		if map.in_bounds(tx + d.x, ty + d.y) and not _connected(tx, ty, d) \
				and _tile_height(tx + d.x, ty + d.y) > h + 0.5:
			return true
	return false


func _tile_height(tx: int, ty: int) -> float:
	var b := map.idx(tx, ty) * 4
	return (map.corner_h[b] + map.corner_h[b + 1] + map.corner_h[b + 2] + map.corner_h[b + 3]) * 0.25


## Lowest surface height at every grid vertex (water depth for the water shader).
func _build_height_tex() -> void:
	var img := Image.create(map.width + 1, map.height + 1, false, Image.FORMAT_RF)
	for vy in map.height + 1:
		for vx in map.width + 1:
			var h := INF
			for oy in [-1, 0]:
				for ox in [-1, 0]:
					var tx: int = vx + ox
					var ty: int = vy + oy
					if map.in_bounds(tx, ty):
						h = minf(h, map.corner_height(tx, ty, (vx - tx) + 2 * (vy - ty)))
			img.set_pixel(vx, vy, Color(h, 0, 0))
	height_tex = ImageTexture.create_from_image(img)


static func _hash(x: int, y: int) -> float:
	var a := sin(x * 12.9898 + y * 78.233) * 43758.5453
	return a - floorf(a)


# --- chunk meshes --------------------------------------------------------------------------

func _build_chunk(cx: int, cy: int) -> ArrayMesh:
	_v.clear()
	_n.clear()
	_c.clear()
	_uv2.clear()
	_idx.clear()
	var x0 := cx * CHUNK_TILES
	var y0 := cy * CHUNK_TILES
	var x1 := mini(x0 + CHUNK_TILES, map.width)
	var y1 := mini(y0 + CHUNK_TILES, map.height)
	for ty in range(y0, y1):
		for tx in range(x0, x1):
			_add_tile_top(tx, ty)
			if map.has_wall_x(tx, ty):
				_add_wall_x(tx, ty)
			if map.has_wall_z(tx, ty):
				_add_wall_z(tx, ty)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _v
	arrays[Mesh.ARRAY_NORMAL] = _n
	arrays[Mesh.ARRAY_COLOR] = _c
	arrays[Mesh.ARRAY_TEX_UV2] = _uv2
	arrays[Mesh.ARRAY_INDEX] = _idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## 3x3 vertex grid per tile; heights bilinear from the 4 corners. COLOR.r darkens the foot of a
## wall rising from this tile's edge, COLOR.g marks the lip where this tile's edge drops away.
func _add_tile_top(tx: int, ty: int) -> void:
	var i := map.idx(tx, ty)
	var h0 := map.corner_h[i * 4]
	var h1 := map.corner_h[i * 4 + 1]
	var h2 := map.corner_h[i * 4 + 2]
	var h3 := map.corner_h[i * 4 + 3]
	var th := _tile_height(tx, ty)
	# per edge: -1 foot of a wall (neighbour higher), +1 lip (neighbour lower), 0 open
	var edge := [0, 0, 0, 0]   # -x, +x, -z, +z
	var dirs: Array[Vector2i] = [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]
	for e in 4:
		var d := dirs[e]
		if map.in_bounds(tx + d.x, ty + d.y) and not _connected(tx, ty, d):
			edge[e] = -1 if _tile_height(tx + d.x, ty + d.y) > th else 1
	var start := _v.size()
	for j in 3:
		var v := j * 0.5
		for k in 3:
			var u := k * 0.5
			var h := lerpf(lerpf(h0, h1, u), lerpf(h2, h3, u), v)
			_v.append(Vector3((tx + u) * Grid.TILE, h, (ty + v) * Grid.TILE))
			var dhu := lerpf(h1 - h0, h3 - h2, v) / Grid.TILE
			var dhv := lerpf(h2 - h0, h3 - h1, u) / Grid.TILE
			_n.append(Vector3(-dhu, 1.0, -dhv).normalized())
			var ao := 1.0
			var lip := 0.0
			var near: Array[float] = [1.0 - u * 2.0, u * 2.0 - 1.0, 1.0 - v * 2.0, v * 2.0 - 1.0]
			for e in 4:
				var w := clampf(near[e], 0.0, 1.0)
				if edge[e] < 0:
					ao = minf(ao, 1.0 - 0.38 * w)
				elif edge[e] > 0:
					lip = maxf(lip, w)
			_c.append(Color(ao, lip, 0.0, 1.0))
			_uv2.append(Vector2(0.0, 0.0))
	for j in 2:
		for k in 2:
			var a := start + j * 3 + k
			_idx.append_array([a, a + 1, a + 4, a, a + 4, a + 3])


## Wall on the vertical edge x = tx*TILE between tiles (tx-1,ty) and (tx,ty).
func _add_wall_x(tx: int, ty: int) -> void:
	var x := tx * Grid.TILE
	var e0 := Vector3(x, 0.0, ty * Grid.TILE)
	var e1 := Vector3(x, 0.0, (ty + 1) * Grid.TILE)
	var a0 := map.corner_height(tx - 1, ty, 1)
	var a1 := map.corner_height(tx - 1, ty, 3)
	var b0 := map.corner_height(tx, ty, 0)
	var b1 := map.corner_height(tx, ty, 2)
	var out := Vector3(1, 0, 0) if a0 + a1 > b0 + b1 else Vector3(-1, 0, 0)
	_add_wall(e0, e1, minf(a0, b0), maxf(a0, b0), minf(a1, b1), maxf(a1, b1), out)


## Wall on the horizontal edge z = ty*TILE between tiles (tx,ty-1) and (tx,ty).
func _add_wall_z(tx: int, ty: int) -> void:
	var z := ty * Grid.TILE
	var e0 := Vector3(tx * Grid.TILE, 0.0, z)
	var e1 := Vector3((tx + 1) * Grid.TILE, 0.0, z)
	var a0 := map.corner_height(tx, ty - 1, 2)
	var a1 := map.corner_height(tx, ty - 1, 3)
	var b0 := map.corner_height(tx, ty, 0)
	var b1 := map.corner_height(tx, ty, 1)
	var out := Vector3(0, 0, 1) if a0 + a1 > b0 + b1 else Vector3(0, 0, -1)
	_add_wall(e0, e1, minf(a0, b0), maxf(a0, b0), minf(a1, b1), maxf(a1, b1), out)


## Subdivided wall quad from bottom to top heights at both ends, bulged towards `out`
## (the lower side) by noise. Seams (ends, top, bottom) stay exact so walls stay watertight.
func _add_wall(e0: Vector3, e1: Vector3, bot0: float, top0: float, bot1: float, top1: float,
		out: Vector3) -> void:
	var tall := maxf(top0 - bot0, top1 - bot1)
	var rows := maxi(1, ceili(tall / WALL_ROW_H))
	var grid: Array[Vector3] = []
	var frac: Array[float] = []
	for r in rows + 1:
		var v := float(r) / rows
		for k in WALL_COLS + 1:
			var u := float(k) / WALL_COLS
			var p := e0.lerp(e1, u)
			p.y = lerpf(lerpf(bot0, top0, v), lerpf(bot1, top1, v), u)
			# pillow bulge, fuller near the top so the cliff reads as a chunky rock shoulder
			var bulge := sin(PI * u) * sin(PI * v) * (0.75 + 0.6 * smoothstep(0.35, 0.85, v))
			if bulge > 0.001:
				var nz := _noise.get_noise_3d(p.x, p.y * 1.3, p.z)
				p += out * WALL_JITTER * bulge * (0.45 + 0.55 * nz)
				p.y += 0.12 * bulge * _noise.get_noise_3d(p.z + 50.0, p.y, p.x)
			grid.append(p)
			frac.append(v)
	var cols := WALL_COLS + 1
	for r in rows:
		for k in WALL_COLS:
			var i00 := r * cols + k
			var i10 := i00 + 1
			var i01 := i00 + cols
			var i11 := i01 + 1
			_add_tri(grid[i00], grid[i10], grid[i11], frac[i00], frac[i10], frac[i11], out)
			_add_tri(grid[i00], grid[i11], grid[i01], frac[i00], frac[i11], frac[i01], out)


## Flat-shaded triangle wound so its front face points along `facing`; UV2 = (1, height fraction).
func _add_tri(a: Vector3, b: Vector3, c: Vector3, fa: float, fb: float, fc: float, facing: Vector3) -> void:
	var nrm := (c - a).cross(b - a)
	if nrm.length_squared() < 1e-10:
		return
	if nrm.dot(facing) < 0.0:
		var t := b
		b = c
		c = t
		var tf := fb
		fb = fc
		fc = tf
		nrm = -nrm
	nrm = nrm.normalized()
	var base := _v.size()
	for p in [a, b, c]:
		_v.append(p)
		_n.append(nrm)
		_c.append(Color(1, 0, 0, 1))
	for f in [fa, fb, fc]:
		_uv2.append(Vector2(1.0, f))
	_idx.append_array([base, base + 1, base + 2])


# --- water ---------------------------------------------------------------------------------

func _build_water() -> void:
	var lo := Vector2i(map.width, map.height)
	var hi := Vector2i(-1, -1)
	for ty in map.height:
		for tx in map.width:
			if map.water[map.idx(tx, ty)] == 1:
				lo = Vector2i(mini(lo.x, tx), mini(lo.y, ty))
				hi = Vector2i(maxi(hi.x, tx), maxi(hi.y, ty))
	if hi.x < 0:
		return
	lo -= Vector2i(2, 2)
	hi += Vector2i(3, 3)
	var size := Vector2(hi - lo) * Grid.TILE
	var plane := PlaneMesh.new()
	plane.size = size
	plane.subdivide_width = 8
	plane.subdivide_depth = 8
	water_material = ShaderMaterial.new()
	water_material.shader = WATER_SHADER
	water_material.set_shader_parameter("map_size_m", map.size_world())
	water_material.set_shader_parameter("map_tiles", Vector2(map.width, map.height))
	water_material.set_shader_parameter("height_tex", height_tex)
	water_material.set_shader_parameter("water_level", map.water_level)
	water_material.set_shader_parameter("ripple_tex", TerrainTextures.mipmapped("water_ripples.png", Color("#4FA3A0")))
	RenderAtmos.register(water_material)
	water = MeshInstance3D.new()
	water.name = "Water"
	water.mesh = plane
	water.material_override = water_material
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	water.position = Vector3(lo.x * Grid.TILE + size.x * 0.5, map.water_level, lo.y * Grid.TILE + size.y * 0.5)
	water.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(water)
