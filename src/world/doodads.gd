class_name Doodads
extends Node3D
## Trees (not entities): one tree occupies 2x2 pathing cells (a 1 m "tree grid" cell).
## Holds per-tree lumber, blocks pathing, renders through one MultiMesh per tree type and
## frees the cells when a tree is depleted.

const TREE_SHADER := preload("res://src/world/tree.gdshader")

var world: World
var trees: Array[Vector2i] = []        ## tree-grid coords
var tree_type: PackedByteArray
var lumber: PackedInt32Array
var alive: PackedByteArray
var alive_count: int = 0
var _index: Dictionary = {}            ## tree-grid Vector2i -> tree index
var _slot: PackedInt32Array            ## instance index inside its type's MultiMesh
var _mm: Array[MultiMesh] = []
var material: ShaderMaterial


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
	if not _mm.is_empty():
		_mm[tree_type[i]].set_instance_transform(_slot[i], Transform3D(Basis.from_scale(Vector3.ZERO), tree_pos(i)))
	Events.tree_felled.emit(tree_pos(i))


func set_fog_texture(tex: Texture2D) -> void:
	if material != null:
		material.set_shader_parameter("fog_tex", tex)
		material.set_shader_parameter("fog_enabled", tex != null)


func _cells_of(i: int) -> Array[Vector2i]:
	var g := trees[i] * 2
	return [g, g + Vector2i(1, 0), g + Vector2i(0, 1), g + Vector2i(1, 1)]


# --- visuals -------------------------------------------------------------------------------

func _build_visuals() -> void:
	for c in get_children():
		c.queue_free()
	_mm.clear()
	material = ShaderMaterial.new()
	material.shader = TREE_SHADER
	material.set_shader_parameter("map_size_m", world.map.size_world())
	var meshes: Array[Mesh] = [_pine_mesh(), _round_mesh()]
	var counts: Array[int] = [0, 0]
	_slot = PackedInt32Array()
	_slot.resize(trees.size())
	for i in trees.size():
		_slot[i] = counts[tree_type[i]]
		counts[tree_type[i]] += 1
	for t in meshes.size():
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = meshes[t]
		mm.instance_count = counts[t]
		_mm.append(mm)
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Trees_%s" % MapData.TREE_TYPES[t]
		mmi.multimesh = mm
		mmi.material_override = material
		mmi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		add_child(mmi)
	for i in trees.size():
		var h := _hash(i)
		var p := tree_pos(i) + Vector3((h.x - 0.5) * 0.3, -0.05, (h.y - 0.5) * 0.3)
		var s := 0.85 + h.z * 0.35
		var xf := Transform3D(Basis(Vector3.UP, h.x * TAU).scaled(Vector3(s, s * (0.9 + h.y * 0.25), s)), p)
		var mm := _mm[tree_type[i]]
		mm.set_instance_transform(_slot[i], xf)
		var tint := 0.82 + h.z * 0.3
		mm.set_instance_color(_slot[i], Color(tint, tint * (0.95 + h.x * 0.1), tint * 0.9))


## Deterministic per-tree pseudo random triple in [0,1).
func _hash(i: int) -> Vector3:
	var g := trees[i]
	var a := sin(g.x * 12.9898 + g.y * 78.233) * 43758.5453
	var b := sin(g.x * 39.3468 + g.y * 11.135) * 24634.6345
	var c := sin(g.x * 73.156 + g.y * 52.235) * 12345.6789
	return Vector3(a - floorf(a), b - floorf(b), c - floorf(c))


static func _pine_mesh() -> ArrayMesh:
	var trunk := Color(0.33, 0.22, 0.13)
	var g1 := Color(0.10, 0.26, 0.12)
	var g2 := Color(0.13, 0.31, 0.14)
	var g3 := Color(0.16, 0.36, 0.16)
	return ProcMesh.merge([
		{"mesh": ProcMesh.cylinder(0.11, 0.16, 1.2, 6), "xform": ProcMesh.at(Vector3(0, 0.6, 0)), "color": trunk},
		{"mesh": ProcMesh.cylinder(0.0, 1.05, 1.9, 8), "xform": ProcMesh.at(Vector3(0, 1.65, 0)), "color": g1},
		{"mesh": ProcMesh.cylinder(0.0, 0.82, 1.6, 8), "xform": ProcMesh.at(Vector3(0, 2.55, 0), Vector3.ONE, 0.4), "color": g2},
		{"mesh": ProcMesh.cylinder(0.0, 0.55, 1.3, 8), "xform": ProcMesh.at(Vector3(0, 3.35, 0), Vector3.ONE, 0.8), "color": g3},
	])


static func _round_mesh() -> ArrayMesh:
	var trunk := Color(0.36, 0.25, 0.15)
	var g1 := Color(0.20, 0.36, 0.12)
	var g2 := Color(0.25, 0.42, 0.14)
	return ProcMesh.merge([
		{"mesh": ProcMesh.cylinder(0.12, 0.18, 1.6, 6), "xform": ProcMesh.at(Vector3(0, 0.8, 0)), "color": trunk},
		{"mesh": ProcMesh.sphere(1.0, 9, 6), "xform": ProcMesh.at(Vector3(0, 2.2, 0), Vector3(1.0, 0.85, 1.0)), "color": g1},
		{"mesh": ProcMesh.sphere(0.7, 8, 5), "xform": ProcMesh.at(Vector3(0.25, 2.85, 0.1)), "color": g2},
		{"mesh": ProcMesh.sphere(0.55, 8, 5), "xform": ProcMesh.at(Vector3(-0.35, 2.6, -0.25)), "color": g2},
	])
