class_name Doodads
extends Node3D
## Trees (not entities): one tree occupies 2x2 pathing cells (a 1 m "tree grid" cell).
## Holds per-tree lumber, blocks pathing, and frees the cells when a tree is depleted (sim side).
## Visuals (only when World.visuals): the Greenvale doodad kit's hill oak / linden / hazel GLBs
## (assets/models/doodads; card-cluster trees from the foliage atlases when they are missing),
## one MultiMesh per (species, LOD, 32 m chunk) so off-screen chunks cull: trees on a forest
## edge use the full mesh, trees enclosed on 4 sides the LOD1 mesh (promoted when a neighbour
## falls), a stump replaces a felled tree. Per-instance hue / value jitter in INSTANCE_CUSTOM,
## wind sway in foliage.gdshader. Plus a deterministic, non-blocking decor scatter (grass tufts,
## wildflowers, scree rocks, reeds, lily pads, mushrooms) that never touches pathing.

const CHUNK_M := 32.0
const DOODAD_DIR := "res://assets/models/doodads/"
const FOLIAGE_SHADER := preload("res://src/render/foliage.gdshader")
## Visual species: GLB base name, canopy-fit scale (XZ, Y) for the 1 m tree grid (canopy ~2.8 m,
## crown top >= 4.5 m, bible §6.4) and the card-tree fallback atlas.
const SPECIES: Array[Dictionary] = [
	{"id": "tree_hill_oak", "xz": 0.44, "y": 0.8, "atlas": "oak_clumps.png"},
	{"id": "tree_linden", "xz": 0.6, "y": 0.78, "atlas": "linden_clumps.png"},
	{"id": "tree_hazel", "xz": 0.64, "y": 0.98, "atlas": "oak_clumps.png"},
]
## Map tree type (MapData.TREE_TYPES) -> species picks by hash (2-3 species mixed, bible §6.4).
const TYPE_SPECIES: Array = [[0, 0, 0, 0, 2], [1, 1, 1, 0, 2]]
## Decor kinds: GLB, scale range.
const DECOR: Array[Dictionary] = [
	{"id": "grass_tuft", "s": Vector2(0.7, 1.15)},
	{"id": "wildflowers_yellow", "s": Vector2(0.7, 1.0)},
	{"id": "wildflowers_white", "s": Vector2(0.7, 1.0)},
	{"id": "wildflowers_mixed", "s": Vector2(0.7, 1.0)},
	{"id": "rock_boulder_small", "s": Vector2(0.7, 1.2)},
	{"id": "rock_boulder_medium", "s": Vector2(0.7, 1.1)},
	{"id": "reeds_clump", "s": Vector2(0.7, 1.1)},
	{"id": "lily_pads", "s": Vector2(0.6, 0.9)},
	{"id": "mushroom_ring", "s": Vector2(0.5, 0.8)},
]

var world: World
var trees: Array[Vector2i] = []        ## tree-grid coords
var tree_type: PackedByteArray
var lumber: PackedInt32Array
var alive: PackedByteArray
var alive_count: int = 0
var _index: Dictionary = {}            ## tree-grid Vector2i -> tree index
var material: ShaderMaterial           ## leaves material of the first species (fog hook, tests)
var materials: Array[ShaderMaterial] = []

# visuals
var _species: PackedByteArray          ## visual species per tree
var _vis_mm: PackedInt32Array          ## MultiMesh index currently showing the tree (-1 none)
var _vis_slot: PackedInt32Array
var _stump_mm: PackedInt32Array
var _stump_slot: PackedInt32Array
var _mms: Array[MultiMesh] = []
var _groups: Dictionary = {}           ## "kind|chunk" -> MultiMesh index
var _meshes: Dictionary = {}           ## glb id -> ArrayMesh (with foliage materials)
var _decor: Dictionary = {}            ## MultiMesh index -> PackedVector3Array instance positions


func setup(w: World, m: MapData) -> void:
	world = w
	trees = m.trees.duplicate()
	tree_type = m.tree_types.duplicate()
	var n := trees.size()
	lumber = PackedInt32Array()
	lumber.resize(n)
	alive = PackedByteArray()
	alive.resize(n)
	alive.fill(1)
	alive_count = n
	_index.clear()
	var cells: Array[Vector2i] = []
	for i in n:
		var def := Defs.doodad(MapData.TREE_TYPES[tree_type[i]])
		lumber[i] = int(def.get("lumber", 50))
		_index[trees[i]] = i
		cells.append_array(_cells_of(i))
	w.pathing.set_trees_bulk(cells)
	if w.visuals:
		_build_visuals()


func tree_pos(i: int) -> Vector3:
	var g := trees[i]
	var p := Vector3(g.x + 0.5, 0.0, g.y + 0.5)
	p.y = world.map.height_at(p.x, p.z)
	return p


func tree_alive(i: int) -> bool:
	return i >= 0 and i < trees.size() and alive[i] == 1


## Tree index covering a pathing cell, or -1.
func tree_at_cell(c: Vector2i) -> int:
	var i: int = _index.get(Vector2i(c.x >> 1, c.y >> 1), -1)
	return i if i >= 0 and alive[i] == 1 else -1


func nearest_tree(p: Vector3, max_r: float) -> int:
	var g := Vector2i(floori(p.x), floori(p.z))
	var best := -1
	var best_d := max_r * max_r
	var r := ceili(max_r)
	for y in range(g.y - r, g.y + r + 1):
		for x in range(g.x - r, g.x + r + 1):
			var i: int = _index.get(Vector2i(x, y), -1)
			if i < 0 or alive[i] == 0:
				continue
			var d := Vector2(x + 0.5 - p.x, y + 0.5 - p.z).length_squared()
			if d < best_d:
				best_d = d
				best = i
	return best


## Removes up to `amount` lumber; returns what was actually taken. Depleted trees disappear.
func harvest(i: int, amount: int) -> int:
	if i < 0 or i >= trees.size() or alive[i] == 0:
		return 0
	var taken := mini(amount, lumber[i])
	lumber[i] -= taken
	if lumber[i] <= 0:
		remove_tree(i)
	return taken


func remove_tree(i: int) -> void:
	if alive[i] == 0:
		return
	alive[i] = 0
	alive_count -= 1
	for c in _cells_of(i):
		world.pathing.set_tree(c, false)
	if not _mms.is_empty():
		_on_tree_removed(i)
	Events.tree_felled.emit(tree_pos(i))


func set_fog_texture(tex: Texture2D) -> void:
	for m in materials:
		m.set_shader_parameter("fog_tex", tex)
		m.set_shader_parameter("fog_enabled", tex != null)


func _cells_of(i: int) -> Array[Vector2i]:
	var g := trees[i] * 2
	return [g, g + Vector2i(1, 0), g + Vector2i(0, 1), g + Vector2i(1, 1)]


# --- visuals: trees ------------------------------------------------------------------------

## Visual species of a tree (deterministic by grid position).
func species_of(i: int) -> int:
	var picks: Array = TYPE_SPECIES[mini(tree_type[i], TYPE_SPECIES.size() - 1)]
	return picks[int(_hash(trees[i]).y * picks.size()) % picks.size()]


## True when all 4 tree-grid neighbours hold live trees (the tree is hidden inside a canopy).
func is_enclosed(i: int) -> bool:
	for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		var j: int = _index.get(trees[i] + d, -1)
		if j < 0 or alive[j] == 0:
			return false
	return true


## Mesh kind showing a tree: "species|full", "species|lod" or "" when felled.
func tree_mesh_kind(i: int) -> String:
	if _vis_mm.is_empty() or _vis_mm[i] < 0:
		return ""
	for key: String in _groups:
		if _groups[key] == _vis_mm[i]:
			return key.get_slice("@", 0)
	return ""


func _build_visuals() -> void:
	for c in get_children():
		c.queue_free()
	_mms.clear()
	_groups.clear()
	_decor.clear()
	materials.clear()
	var n := trees.size()
	_species = PackedByteArray()
	_species.resize(n)
	_vis_mm = PackedInt32Array()
	_vis_mm.resize(n)
	_vis_slot = PackedInt32Array()
	_vis_slot.resize(n)
	_stump_mm = PackedInt32Array()
	_stump_mm.resize(n)
	_stump_slot = PackedInt32Array()
	_stump_slot.resize(n)
	# count instances per group first (MultiMesh sizes are fixed once allocated)
	var counts := {}
	for i in n:
		_species[i] = species_of(i)
		var ch := _chunk_key(tree_pos(i))
		var sp: String = SPECIES[_species[i]]["id"]
		for lod in ["full", "lod"]:
			# full meshes get capacity for every tree: enclosed trees are promoted when exposed
			var k := "%s|%s@%s" % [sp, lod, ch]
			counts[k] = int(counts.get(k, 0)) + 1
		var sk := "tree_stump|stump@%s" % ch
		counts[sk] = int(counts.get(sk, 0)) + 1
	var used := {}
	for i in n:
		var ch := _chunk_key(tree_pos(i))
		var sp: String = SPECIES[_species[i]]["id"]
		var lod := "lod" if is_enclosed(i) else "full"
		var mmi := _group("%s|%s@%s" % [sp, lod, ch], sp if lod == "full" else sp + "_lod1", counts)
		_vis_mm[i] = mmi
		_vis_slot[i] = _take_slot(mmi, used)
		_mms[mmi].set_instance_transform(_vis_slot[i], _tree_xform(i))
		_mms[mmi].set_instance_custom_data(_vis_slot[i], _tree_tint(i))
		var smi := _group("tree_stump|stump@%s" % ch, "tree_stump", counts)
		_stump_mm[i] = smi
		_stump_slot[i] = -1
	for mmi in used:
		_mms[mmi].visible_instance_count = used[mmi]
	if not materials.is_empty():
		material = materials[0]
	_build_decor.call_deferred()


func _chunk_key(p: Vector3) -> String:
	return "%d_%d" % [floori(p.x / CHUNK_M), floori(p.z / CHUNK_M)]


## MultiMesh for a group key, created on first use with the capacity from `counts`.
func _group(key: String, glb: String, counts: Dictionary) -> int:
	if _groups.has(key):
		return _groups[key]
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	# white instance colours: the Compatibility renderer multiplies COLOR by them (zero when absent)
	mm.use_colors = true
	mm.mesh = _mesh_for(glb)
	mm.instance_count = int(counts.get(key, 0))
	for k in mm.instance_count:
		mm.set_instance_color(k, Color.WHITE)
	mm.visible_instance_count = 0
	_mms.append(mm)
	var idx := _mms.size() - 1
	_groups[key] = idx
	var mmi := MultiMeshInstance3D.new()
	mmi.name = key.replace("|", "_").replace("@", "_")
	mmi.multimesh = mm
	mmi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	if glb.begins_with("grass") or glb.begins_with("wildflowers") or glb.begins_with("lily"):
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)
	return idx


func _take_slot(mmi: int, used: Dictionary) -> int:
	var s: int = used.get(mmi, 0)
	used[mmi] = s + 1
	return s


func _tree_xform(i: int) -> Transform3D:
	var h := _hash(trees[i])
	var sp: Dictionary = SPECIES[_species[i]]
	var p := tree_pos(i) + Vector3((h.x - 0.5) * 0.35, -0.05, (h.z - 0.5) * 0.35)
	var s := 0.85 + h.z * 0.3     # +-15 %
	var sxz: float = sp["xz"] * s
	var sy: float = sp["y"] * s * (0.92 + h.x * 0.16)
	return Transform3D(Basis(Vector3.UP, h.x * TAU).scaled(Vector3(sxz, sy, sxz)), p)


## Per-tree hue (+-3 deg) and value (+-7 %) jitter.
func _tree_tint(i: int) -> Color:
	var h := _hash(trees[i])
	var v := 0.93 + h.y * 0.14
	var warm := (h.z - 0.5) * 0.08
	return Color(v * (1.0 + warm), v, v * (1.0 - warm * 1.5), 1.0)


func _on_tree_removed(i: int) -> void:
	var mm := _mms[_vis_mm[i]]
	mm.set_instance_transform(_vis_slot[i], Transform3D(Basis.from_scale(Vector3.ZERO), tree_pos(i)))
	_vis_mm[i] = -1
	# stump
	var smm := _mms[_stump_mm[i]]
	var slot := smm.visible_instance_count
	if slot < smm.instance_count:
		smm.visible_instance_count = slot + 1
		_stump_slot[i] = slot
		var h := _hash(trees[i])
		smm.set_instance_transform(slot, Transform3D(Basis(Vector3.UP, h.y * TAU).scaled(Vector3.ONE * (0.5 + h.z * 0.15)), tree_pos(i)))
		smm.set_instance_custom_data(slot, _tree_tint(i))
	# neighbours that were hidden in the canopy now face the clearing: promote to the full mesh
	for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		var j: int = _index.get(trees[i] + d, -1)
		if j < 0 or alive[j] == 0 or _vis_mm[j] < 0:
			continue
		var key := tree_mesh_kind(j)
		if not key.ends_with("|lod"):
			continue
		var old := _mms[_vis_mm[j]]
		old.set_instance_transform(_vis_slot[j], Transform3D(Basis.from_scale(Vector3.ZERO), tree_pos(j)))
		var sp: String = SPECIES[_species[j]]["id"]
		var full_key := "%s|full@%s" % [sp, _chunk_key(tree_pos(j))]
		var fi: int = _groups.get(full_key, -1)
		if fi < 0:
			continue
		var fm := _mms[fi]
		var fs := fm.visible_instance_count
		if fs >= fm.instance_count:
			continue
		fm.visible_instance_count = fs + 1
		fm.set_instance_transform(fs, _tree_xform(j))
		fm.set_instance_custom_data(fs, _tree_tint(j))
		_vis_mm[j] = fi
		_vis_slot[j] = fs


# --- meshes and materials ------------------------------------------------------------------

## The kit mesh of a GLB with foliage materials (SWAY -> leaves, else bark / rock / AO multiply);
## card-cluster trees from the foliage atlases when a tree GLB is missing.
func _mesh_for(glb: String) -> Mesh:
	if _meshes.has(glb):
		return _meshes[glb]
	var mesh: Mesh = null
	var path := DOODAD_DIR + glb + ".glb"
	if ResourceLoader.exists(path):
		var inst := (load(path) as PackedScene).instantiate()
		var mi: MeshInstance3D = null
		for c in inst.find_children("*", "MeshInstance3D", true, false):
			mi = c as MeshInstance3D
			break
		if mi != null and mi.mesh != null:
			mesh = mi.mesh.duplicate() as ArrayMesh
			for s in mesh.get_surface_count():
				var src := mesh.surface_get_material(s) as BaseMaterial3D
				mesh.surface_set_material(s, _foliage_mat(src))
		inst.free()
	if mesh == null and glb.begins_with("tree_") and not glb.begins_with("tree_stump"):
		mesh = _card_tree(glb)
	if mesh == null:
		var box := BoxMesh.new()
		box.material = _foliage_mat(null)
		mesh = box
	_meshes[glb] = mesh
	return mesh


func _foliage_mat(src: BaseMaterial3D) -> ShaderMaterial:
	var leaves := src != null and src.resource_name.contains("SWAY")
	var m := ShaderMaterial.new()
	m.shader = FOLIAGE_SHADER
	m.set_shader_parameter("multimesh", true)
	m.set_shader_parameter("is_leaves", leaves)
	m.set_shader_parameter("map_size_m", world.map.size_world())
	if src != null:
		m.set_shader_parameter("albedo_tex", src.albedo_texture)
		if leaves:
			m.set_shader_parameter("alpha_cutoff", clampf(src.alpha_scissor_threshold, 0.3, 0.6))
	if not leaves:
		m.set_shader_parameter("sway_amp", 0.02)
	RenderAtmos.register(m)
	if leaves:
		materials.insert(0, m)
	else:
		materials.append(m)
	return m


func _exit_tree() -> void:
	for m in materials:
		RenderAtmos.unregister(m)


## Fallback tree: a bark trunk and ~14 crossed leaf cards from the foliage atlas (4 x 2 clump
## cells), with the kit's vertex conventions (COLOR r sway, g AO, b phase; UV2.y height).
func _card_tree(glb: String) -> ArrayMesh:
	var atlas_name := "oak_clumps.png"
	for sp: Dictionary in SPECIES:
		if glb.begins_with(sp["id"]):
			atlas_name = sp["atlas"]
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(glb)
	var top := 6.2
	for k in 14:
		var a := rng.randf() * TAU
		var r := rng.randf_range(0.6, 2.3)
		var c := Vector3(cos(a) * r, rng.randf_range(2.6, 5.4), sin(a) * r)
		var size := rng.randf_range(1.6, 2.3)
		var cell := Vector2(k % 4, int(k / 4.0) % 2) * Vector2(0.25, 0.5)
		for yaw in [0.0, PI * 0.5]:
			var right := Vector3(cos(a + yaw), 0, sin(a + yaw)) * size * 0.5
			var up := Vector3(0, size * 0.5, 0)
			var corners := [c - right - up, c + right - up, c + right + up, c - right + up]
			var uvs := [cell + Vector2(0, 0.5), cell + Vector2(0.25, 0.5), cell + Vector2(0.25, 0), cell]
			for tri in [[0, 1, 2], [0, 2, 3]]:
				for v: int in tri:
					var p: Vector3 = corners[v]
					st.set_color(Color(clampf(p.y / top, 0.2, 1.0), 0.75 + 0.25 * p.y / top, float(k) / 14.0))
					st.set_uv(uvs[v])
					st.set_uv2(Vector2(clampf(p.y / top, 0, 1), p.y / top))
					st.set_normal((p - Vector3(0, 3.8, 0)).normalized())
					st.add_vertex(p)
	var leaves := st.commit()
	var lm := ShaderMaterial.new()
	lm.shader = FOLIAGE_SHADER
	lm.set_shader_parameter("multimesh", true)
	lm.set_shader_parameter("albedo_tex", load("res://assets/textures/foliage/" + atlas_name))
	RenderAtmos.register(lm)
	materials.insert(0, lm)
	leaves.surface_set_material(0, lm)
	var trunk := ProcMesh.cylinder(0.14, 0.24, 3.4, 7)
	var tm := ShaderMaterial.new()
	tm.shader = FOLIAGE_SHADER
	tm.set_shader_parameter("multimesh", true)
	tm.set_shader_parameter("is_leaves", false)
	tm.set_shader_parameter("albedo_tex", TerrainTextures.mipmapped("bark_oak.png", Color("#5A4630")))
	RenderAtmos.register(tm)
	materials.append(tm)
	var arrays := trunk.get_mesh_arrays()
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var cols := PackedColorArray()
	var uv2 := PackedVector2Array()
	for i in verts.size():
		verts[i].y += 1.7
		cols.append(Color(1, 1, 1))
		uv2.append(Vector2(0.0, verts[i].y / top))
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_TEX_UV2] = uv2
	leaves.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	leaves.surface_set_material(1, tm)
	return leaves


# --- visuals: decor scatter ----------------------------------------------------------------

## Non-blocking decor from the map's terrain (visual only, deterministic by tile hash). Runs after
## the terrain is built so it can read the painted ladder slots.
func _build_decor() -> void:
	var m := world.map
	if m == null or not is_inside_tree():
		return
	var terrain := world.terrain
	var tree_tiles := {}
	for t in trees:
		tree_tiles[Vector2i(t.x >> 1, t.y >> 1)] = true
	var picks: Array = []     # [decor index, position, yaw, scale]
	for ty in m.height:
		for tx in m.width:
			var i := m.idx(tx, ty)
			var c := Grid.tile_to_world(Vector2i(tx, ty))
			if _near_sites(c):
				continue
			var h := _hash(Vector2i(tx * 7 + 3, ty * 13 + 1))
			var slot := terrain.ladder_at(tx, ty) if terrain != null else 5
			var forest := tree_tiles.has(Vector2i(tx, ty))
			if m.water[i] == 1:
				if _shore(tx, ty) and h.x < 0.16:
					picks.append([7, c + Vector3((h.y - 0.5) * 1.2, 0, (h.z - 0.5) * 1.2), h.y * TAU, 0.0])
				continue
			if m.ramp[i] > 0:
				continue
			if _shore(tx, ty) and h.x < 0.55:
				picks.append([6, c + Vector3((h.y - 0.5) * 1.4, 0, (h.z - 0.5) * 1.4), h.z * TAU, 0.0])
			if forest:
				if h.z < 0.04:
					picks.append([8, c, h.x * TAU, 0.0])
				continue
			match slot:
				TerrainTextures.MEADOW, TerrainTextures.THICK_MEADOW, TerrainTextures.GRASSY_DIRT:
					var n := 3 if slot == TerrainTextures.THICK_MEADOW else (2 if slot == TerrainTextures.MEADOW else 1)
					var p_tuft := 0.5 if slot == TerrainTextures.GRASSY_DIRT else 0.8
					for k in n:
						var hk := _hash(Vector2i(tx * 31 + k * 5, ty * 17 + k * 11))
						if hk.x < p_tuft:
							picks.append([0, c + Vector3((hk.y - 0.5) * 1.8, 0, (hk.z - 0.5) * 1.8), hk.z * TAU, 0.0])
					if slot != TerrainTextures.GRASSY_DIRT and h.y < 0.09:
						picks.append([1 + int(h.z * 3.0) % 3, c + Vector3((h.x - 0.5) * 1.4, 0, (h.z - 0.5) * 1.4), h.x * TAU, 0.0])
				TerrainTextures.SCREE:
					if h.x < 0.4:
						picks.append([4 if h.y < 0.7 else 5, c + Vector3((h.y - 0.5) * 1.4, 0, (h.z - 0.5) * 1.4), h.z * TAU, 0.0])
	# group by (kind, chunk)
	var counts := {}
	var keys: Array[String] = []
	for pk: Array in picks:
		var k := "%s|decor@%s" % [DECOR[pk[0]]["id"], _chunk_key(pk[1])]
		keys.append(k)
		counts[k] = int(counts.get(k, 0)) + 1
	var used := {}
	for n in picks.size():
		var pk: Array = picks[n]
		var d: Dictionary = DECOR[pk[0]]
		var mmi := _group(keys[n], d["id"], counts)
		var slot := _take_slot(mmi, used)
		var p: Vector3 = pk[1]
		p.y = m.water_level + 0.02 if d["id"] == "lily_pads" else m.height_at(p.x, p.z) - 0.03
		var hh := _hash(Vector2i(int(p.x * 7.0), int(p.z * 7.0)))
		var sv: Vector2 = d["s"]
		var s := lerpf(sv.x, sv.y, hh.x)
		_mms[mmi].set_instance_transform(slot, Transform3D(Basis(Vector3.UP, pk[2]).scaled(Vector3.ONE * s), p))
		var v := 0.92 + hh.y * 0.16
		_mms[mmi].set_instance_custom_data(slot, Color(v, v, v * (0.96 + hh.z * 0.08), 1.0))
		if not _decor.has(mmi):
			_decor[mmi] = PackedVector3Array()
		(_decor[mmi] as PackedVector3Array).append(p)
	for mmi in used:
		_mms[mmi].visible_instance_count = used[mmi]


## Hides decor inside a world-space rectangle (building footprints). Visual only.
func clear_decor(rect: Rect2) -> void:
	for mmi: int in _decor:
		var pts: PackedVector3Array = _decor[mmi]
		for s in pts.size():
			if rect.has_point(Vector2(pts[s].x, pts[s].z)):
				_mms[mmi].set_instance_transform(s, Transform3D(Basis.from_scale(Vector3.ZERO), pts[s]))


## Decor count (tests).
func decor_count() -> int:
	var n := 0
	for mmi: int in _decor:
		n += (_decor[mmi] as PackedVector3Array).size()
	return n


func _near_sites(p: Vector3) -> bool:
	var m := world.map
	for s in m.start_locations:
		if Grid.flat_dist(p, s) < 13.0:
			return true
	for g in m.gold_mines:
		if Grid.flat_dist(p, g) < 6.0:
			return true
	for c in m.creep_camps:
		if Grid.flat_dist(p, c["pos"]) < 3.0:
			return true
	return false


func _shore(tx: int, ty: int) -> bool:
	var m := world.map
	var wet := m.water[m.idx(tx, ty)] == 1
	for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		if m.in_bounds(tx + d.x, ty + d.y) and (m.water[m.idx(tx + d.x, ty + d.y)] == 1) != wet:
			return true
	return false


## Deterministic per-cell pseudo random triple in [0,1).
static func _hash(g: Vector2i) -> Vector3:
	var a := sin(g.x * 12.9898 + g.y * 78.233) * 43758.5453
	var b := sin(g.x * 39.3468 + g.y * 11.135) * 24634.6345
	var c := sin(g.x * 73.156 + g.y * 52.235) * 12345.6789
	return Vector3(a - floorf(a), b - floorf(b), c - floorf(c))
