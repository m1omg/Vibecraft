class_name TerrainBuilder
extends Node3D
## Builds the terrain as chunked ArrayMeshes (CHUNK_TILES x CHUNK_TILES tiles per chunk):
## tile tops (2x2 subdivided, splat weights in COLOR + CUSTOM0), cliff walls with noise jitter
## (flagged in UV2.x for triplanar rock), and a water plane over the lake.

const CHUNK_TILES := 16
const WALL_COLS := 3
const WALL_ROW_H := 0.55
const WALL_JITTER := 0.35
const TERRAIN_SHADER := preload("res://src/world/terrain.gdshader")
const WATER_SHADER := preload("res://src/world/water.gdshader")

var map: MapData
var material: ShaderMaterial
var water_material: ShaderMaterial
var chunks: Array[MeshInstance3D] = []
var water: MeshInstance3D

var _weights: PackedFloat32Array   ## 8 per tile corner
var _noise := FastNoiseLite.new()

# per-chunk scratch buffers
var _v := PackedVector3Array()
var _n := PackedVector3Array()
var _c := PackedColorArray()
var _c1 := PackedFloat32Array()
var _uv2 := PackedVector2Array()
var _idx := PackedInt32Array()


func build(m: MapData) -> void:
	map = m
	for c in get_children():
		c.queue_free()
	chunks.clear()
	_noise.seed = 4242
	_noise.frequency = 0.9
	material = ShaderMaterial.new()
	material.shader = TERRAIN_SHADER
	material.set_shader_parameter("map_size_m", map.size_world())
	_compute_corner_weights()
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


func set_fog_texture(tex: Texture2D) -> void:
	for mat: ShaderMaterial in [material, water_material]:
		if mat != null:
			mat.set_shader_parameter("fog_tex", tex)
			mat.set_shader_parameter("fog_enabled", tex != null)


# --- splat weights -------------------------------------------------------------------------

## Each tile corner averages the one-hot layer of every tile sharing that vertex at the same
## height, so texture borders blend across tiles but never across cliff walls.
func _compute_corner_weights() -> void:
	_weights = PackedFloat32Array()
	_weights.resize(map.width * map.height * 32)
	for ty in map.height:
		for tx in map.width:
			for c in 4:
				var vx := tx + (c & 1)
				var vy := ty + (c >> 1)
				var h := map.corner_height(tx, ty, c)
				var base := (map.idx(tx, ty) * 4 + c) * 8
				var total := 0.0
				for ny in range(vy - 1, vy + 1):
					for nx in range(vx - 1, vx + 1):
						if not map.in_bounds(nx, ny):
							continue
						var nc := (vx - nx) + 2 * (vy - ny)
						if absf(map.corner_height(nx, ny, nc) - h) > MapData.HEIGHT_EPS:
							continue
						_weights[base + map.tex[map.idx(nx, ny)]] += 1.0
						total += 1.0
				for k in 8:
					_weights[base + k] /= total


# --- chunk meshes --------------------------------------------------------------------------

func _build_chunk(cx: int, cy: int) -> ArrayMesh:
	_v.clear()
	_n.clear()
	_c.clear()
	_c1.clear()
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
	arrays[Mesh.ARRAY_CUSTOM0] = _c1
	arrays[Mesh.ARRAY_INDEX] = _idx
	var mesh := ArrayMesh.new()
	var flags := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
	return mesh


## 3x3 vertex grid per tile; heights and weights bilinear from the 4 corners.
func _add_tile_top(tx: int, ty: int) -> void:
	var i := map.idx(tx, ty)
	var h0 := map.corner_h[i * 4]
	var h1 := map.corner_h[i * 4 + 1]
	var h2 := map.corner_h[i * 4 + 2]
	var h3 := map.corner_h[i * 4 + 3]
	var wb := i * 32
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
			var w := PackedFloat32Array()
			w.resize(8)
			for l in 8:
				var a := lerpf(_weights[wb + l], _weights[wb + 8 + l], u)
				var b := lerpf(_weights[wb + 16 + l], _weights[wb + 24 + l], u)
				w[l] = lerpf(a, b, v)
			_c.append(Color(w[0], w[1], w[2], w[3]))
			_c1.append_array([w[4], w[5], w[6], w[7]])
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
	for r in rows + 1:
		var v := float(r) / rows
		for k in WALL_COLS + 1:
			var u := float(k) / WALL_COLS
			var p := e0.lerp(e1, u)
			p.y = lerpf(lerpf(bot0, top0, v), lerpf(bot1, top1, v), u)
			var bulge := sin(PI * u) * sin(PI * v)
			if bulge > 0.001:
				var nz := _noise.get_noise_3d(p.x, p.y * 1.3, p.z)
				p += out * WALL_JITTER * bulge * (0.45 + 0.55 * nz)
				p.y += 0.12 * bulge * _noise.get_noise_3d(p.z + 50.0, p.y, p.x)
			grid.append(p)
	var cols := WALL_COLS + 1
	for r in rows:
		for k in WALL_COLS:
			var p00 := grid[r * cols + k]
			var p10 := grid[r * cols + k + 1]
			var p01 := grid[(r + 1) * cols + k]
			var p11 := grid[(r + 1) * cols + k + 1]
			_add_tri(p00, p10, p11, out)
			_add_tri(p00, p11, p01, out)


## Flat-shaded triangle wound so its front face points along `facing`.
func _add_tri(a: Vector3, b: Vector3, c: Vector3, facing: Vector3) -> void:
	var nrm := (c - a).cross(b - a)
	if nrm.length_squared() < 1e-10:
		return
	if nrm.dot(facing) < 0.0:
		var t := b
		b = c
		c = t
		nrm = -nrm
	nrm = nrm.normalized()
	var base := _v.size()
	for p in [a, b, c]:
		_v.append(p)
		_n.append(nrm)
		_c.append(Color(1, 0, 0, 0))
		_c1.append_array([0.0, 0.0, 0.0, 0.0])
		_uv2.append(Vector2(1.0, 0.0))
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
	water = MeshInstance3D.new()
	water.name = "Water"
	water.mesh = plane
	water.material_override = water_material
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	water.position = Vector3(lo.x * Grid.TILE + size.x * 0.5, map.water_level, lo.y * Grid.TILE + size.y * 0.5)
	water.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(water)
