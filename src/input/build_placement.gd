class_name BuildPlacement
extends Node3D
## The build ghost (juice BLD-01, BLD-02; visual only, driven by CommandInput's "place" mode):
## the building's model drawn as a surveyor's sketch (paper fill, ink hull, hatching where the sun
## does not reach; red ink and a crossing hatch when the spot is refused, grey ink when the cost
## cannot be met) over a cell grid of the footprint and a 2-cell border (Construction.cell_states:
## valid, blocked, unexplored, too close to a Gold Seam). The ghost glides to the snapped spot
## under the cursor on a spring (ω 40, ζ 0.72: ≈ 4 % overshoot, settled in ≈ 140 ms), hovers
## 0.08 m up, ticks 4 % in Y on each cell change and lands with a wooden tock once a valid spot
## has held for 80 ms (≤ 4 a second). A refused click shakes it (0.12 m); a placement stamps it.
## All motion runs on real frame time with exact springs and closed-form curves, so it looks the
## same at any refresh rate. Never touches sim state.

const OMEGA := 40.0
const ZETA := 0.72
const HOVER_M := 0.08
const BORDER := 2
const TICK_S := 0.09
const TICK_AMP := 0.04
const TOCK_AFTER_S := 0.08
const SHAKE_M := 0.12
const SHAKE_S := 0.28
const STAMP_S := 0.16
const INK := Color(0.17, 0.13, 0.09, 0.85)
const INK_REFUSED := Color(0.753, 0.224, 0.169, 0.9)     ## #C0392B
const INK_POOR := Color(0.541, 0.561, 0.588, 0.85)       ## #8A8F96
const DEPTH_SHADER := preload("res://src/fx/sketch_depth.gdshader")
const FILL_SHADER := preload("res://src/fx/sketch_fill.gdshader")
const INK_SHADER := preload("res://src/fx/sketch_ink.gdshader")
const GRID_SHADER := preload("res://src/fx/placement_grid.gdshader")

var world: World
var camera: RtsCamera
var player_id: int = 0
var def_id: String = ""
## The snapped footprint centre under the cursor (y = ground), INF before the first frame.
var spot: Vector3 = Vector3.INF
var valid: bool = false
var affordable: bool = true
var reason: String = ""            ## Construction.can_place reason of the spot ("" = valid)
## Tests: a fixed screen point instead of the mouse.
var screen_override: Vector2 = Vector2.INF

var _model: Node3D
var _grid: MeshInstance3D
var _depth_mat: ShaderMaterial
var _fill_mat: ShaderMaterial
var _ink_mat: ShaderMaterial
var _offset := Vector3.ZERO        ## spring offset from `spot`
var _vel := Vector3.ZERO
var _cell_age := 10.0              ## seconds since the spot last changed
var _tocked: bool = true
var _shake_age := 10.0
var _stamp_age := 10.0
var _grid_key: String = ""
var _fit := Vector3.ONE            ## the model's footprint fit scale (tick and stamp multiply it)


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	visible = false
	_depth_mat = ShaderMaterial.new()
	_depth_mat.shader = DEPTH_SHADER
	_fill_mat = ShaderMaterial.new()
	_fill_mat.shader = FILL_SHADER
	_fill_mat.render_priority = 1
	_ink_mat = ShaderMaterial.new()
	_ink_mat.shader = INK_SHADER
	_ink_mat.render_priority = 2
	_depth_mat.next_pass = _fill_mat
	_fill_mat.next_pass = _ink_mat
	_grid = MeshInstance3D.new()
	_grid.name = "Grid"
	_grid.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var gm := ShaderMaterial.new()
	gm.shader = GRID_SHADER
	gm.render_priority = -1
	_grid.material_override = gm
	_grid.top_level = true
	add_child(_grid)


func setup(w: World, cam: RtsCamera, pid: int) -> void:
	world = w
	camera = cam
	player_id = pid


## Starts placing `id` (the ghost appears at the cursor on the next frame).
func begin(id: String) -> void:
	if id != def_id:
		_set_model(id)
	def_id = id
	spot = Vector3.INF
	_offset = Vector3.ZERO
	_vel = Vector3.ZERO
	_grid_key = ""
	visible = true


func end() -> void:
	def_id = ""
	visible = false
	if _model != null:
		_model.queue_free()
		_model = null


## A refused click: the ghost shakes (ECO-14).
func refuse() -> void:
	_shake_age = 0.0


## A placement: a quick stamp down (BLD-04).
func stamp() -> void:
	_stamp_age = 0.0


func _set_model(id: String) -> void:
	if _model != null:
		_model.queue_free()
		_model = null
	var d := Defs.unit(id)
	var path := AssetLibrary.model_path(d, id)
	var m: Node3D = null
	if not path.is_empty():
		m = AssetLibrary.instantiate(path, "structure")
		if m != null:
			UnitView.add_structure_parts(m, d, path)
			m.scale = Vector3.ONE * UnitView.structure_fit(d, path)
	if m == null:
		m = _block(d)
	m.name = "Ghost"
	add_child(m)
	_model = m
	_fit = m.scale
	for g: GeometryInstance3D in m.find_children("*", "GeometryInstance3D", true, false):
		g.material_override = _depth_mat
		g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


## A footprint-sized block with a pyramid roof for buildings without a model.
static func _block(d: Dictionary) -> Node3D:
	var fp: Array = d.get("footprint", [8, 8])
	var w := float(fp[0]) * Grid.CELL * 0.9
	var depth := float(fp[1]) * Grid.CELL * 0.9
	var h := float(d.get("height", 3.0))
	var root := Node3D.new()
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(w, h * 0.55, depth)
	body.mesh = box
	body.position.y = h * 0.275
	root.add_child(body)
	var roof := MeshInstance3D.new()
	var pyr := CylinderMesh.new()
	pyr.top_radius = 0.0
	pyr.bottom_radius = maxf(w, depth) * 0.72
	pyr.height = h * 0.45
	pyr.radial_segments = 4
	pyr.rings = 1
	roof.mesh = pyr
	roof.rotation.y = PI * 0.25
	roof.position.y = h * 0.55 + h * 0.225
	root.add_child(roof)
	return root


func _process(delta: float) -> void:
	if def_id.is_empty() or world == null or camera == null:
		return
	var dt := minf(delta, 0.1)
	var at := screen_override if screen_override != Vector2.INF else get_viewport().get_mouse_position()
	var ground := camera.screen_to_ground(at)
	if ground != Vector3.INF:
		_track(ground)
	if spot == Vector3.INF:
		return
	_cell_age += dt
	_shake_age += dt
	_stamp_age += dt
	for axis in 3:
		var r := Juice.spring(_offset[axis], _vel[axis], OMEGA, ZETA, dt)
		_offset[axis] = r.x
		_vel[axis] = r.y
	var shake := 0.0
	if _shake_age < SHAKE_S:
		shake = JuiceCurves.shake(_shake_age, SHAKE_M, 0.09, SHAKE_S)
	var xf_pos := spot + _offset + Vector3(shake, HOVER_M, 0.0)
	var tick := TICK_AMP * sin(PI * clampf(_cell_age / TICK_S, 0.0, 1.0))
	var squash := 0.0
	if _stamp_age < STAMP_S:
		squash = 0.08 * sin(PI * _stamp_age / STAMP_S)
	if _model != null:
		_model.position = xf_pos
		_model.scale = _fit * Vector3(1.0 + squash * 0.5, 1.0 + tick - squash, 1.0 + squash * 0.5)
	if not _tocked and valid and affordable and _cell_age >= TOCK_AFTER_S:
		_tocked = true
		Audio.play_2d("ui_click_%s" % Audio.ui_faction, {"volume_db": -18.0, "spacing_ms": 250})
	_paint()


## The snapped spot under the cursor: re-checks the cells and re-bases the spring so the drawn
## ghost does not jump (it glides from where it is).
func _track(ground: Vector3) -> void:
	var cs := world.construction.cell_states(player_id, def_id, ground, BORDER)
	var target: Vector3 = cs["pos"]
	target.y = world.map.height_at(target.x, target.z)
	if target != spot:
		if spot != Vector3.INF:
			_offset += spot - target
			_cell_age = 0.0
			_tocked = false
		spot = target
	var states: PackedByteArray = cs["states"]
	var outer: Rect2i = cs["outer"]
	reason = ""
	for r: Array in Construction.REASON_OF:
		if states.has(int(r[0])):
			reason = str(r[1])
			break
	valid = reason == ""
	var p := world.player(player_id)
	var cost: Dictionary = Defs.unit(def_id).get("cost", {})
	affordable = p != null and p.gold >= int(cost.get("gold", 0)) and p.lumber >= int(cost.get("lumber", 0))
	var key := "%s|%s" % [outer, states.hex_encode()]
	if key != _grid_key:
		_grid_key = key
		_grid.mesh = _grid_mesh(outer, states)


func _paint() -> void:
	var refused := not valid
	var ink := INK_REFUSED if refused else (INK if affordable else INK_POOR)
	var boil := floorf(FxClock.ui_now * 8.0)
	_fill_mat.set_shader_parameter("ink", ink)
	_fill_mat.set_shader_parameter("refused", 1.0 if refused else 0.0)
	_fill_mat.set_shader_parameter("boil", boil)
	_ink_mat.set_shader_parameter("ink", ink)
	_ink_mat.set_shader_parameter("boil", boil)
	var sun := world.day_night.sun if world.day_night != null else null
	if sun != null:
		_fill_mat.set_shader_parameter("sun_to", sun.global_transform.basis.z)


## One quad per cell of `outer`, laid on the terrain (COLOR.r = cell state).
func _grid_mesh(outer: Rect2i, states: PackedByteArray) -> ArrayMesh:
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	var c := Grid.CELL
	for y in outer.size.y:
		for x in outer.size.x:
			var cell := outer.position + Vector2i(x, y)
			var col := Color(float(states[y * outer.size.x + x]) / 255.0, 0.0, 0.0, 1.0)
			var x0 := cell.x * c
			var z0 := cell.y * c
			var base := verts.size()
			for corner: Vector2 in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
				var px := x0 + corner.x * c
				var pz := z0 + corner.y * c
				verts.append(Vector3(px, world.map.height_at(px, pz) + 0.04, pz))
				uvs.append(corner)
				cols.append(col)
			idx.append_array([base, base + 1, base + 2, base, base + 2, base + 3])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
