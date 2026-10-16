class_name SelectionCircles
extends MultiMeshInstance3D
## Team-relation coloured rings under selected units, drawn with one MultiMesh. Updated every
## render frame from interpolated unit positions; rings tilt to the terrain normal on ramps.

const RING_SHADER := preload("res://src/fx/ring.gdshader")
const OWN := Color(0.25, 1.0, 0.3)
const ENEMY := Color(1.0, 0.22, 0.18)
const NEUTRAL := Color(1.0, 0.9, 0.25)
const FLOATS := 16       ## 12 transform + 4 colour per instance

var world: World
var units: Array = []
var _buf := PackedFloat32Array()


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = RING_SHADER
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.mesh = quad
	material_override = mat
	_grow(64)
	Events.selection_changed.connect(_on_selection_changed)


func setup(w: World) -> void:
	world = w
	var s := w.map.size_world()
	custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 40, s.y + 10))


func _on_selection_changed(sel: Array) -> void:
	units = sel.duplicate()


func relation_color(u: Unit) -> Color:
	if world == null:
		return OWN
	if u.player_id == world.local_player_id:
		return OWN
	if world.is_enemy(world.local_player_id, u.player_id):
		return ENEMY
	return NEUTRAL


func _process(_delta: float) -> void:
	if world == null:
		return
	if units.size() > multimesh.instance_count:
		_grow(units.size() * 2)
	var n := 0
	for u: Unit in units:
		if not is_instance_valid(u) or not u.alive:
			continue
		_write(n, u)
		n += 1
	multimesh.visible_instance_count = n
	if n > 0:
		multimesh.buffer = _buf


func _write(slot: int, u: Unit) -> void:
	var p := u.display_pos()
	var r := _ring_radius(u)
	var nrm := _terrain_normal(p, r)
	var z := Vector3(1, 0, 0).cross(nrm).normalized()
	var x := nrm.cross(z).normalized()
	var o := slot * FLOATS
	var c := relation_color(u)
	var y := world.map.height_at(p.x, p.z) + 0.06
	# 3x4 row-major: basis rows then origin component
	_buf[o + 0] = x.x * r
	_buf[o + 1] = nrm.x * r
	_buf[o + 2] = z.x * r
	_buf[o + 3] = p.x
	_buf[o + 4] = x.y * r
	_buf[o + 5] = nrm.y * r
	_buf[o + 6] = z.y * r
	_buf[o + 7] = y
	_buf[o + 8] = x.z * r
	_buf[o + 9] = nrm.z * r
	_buf[o + 10] = z.z * r
	_buf[o + 11] = p.z
	_buf[o + 12] = c.r
	_buf[o + 13] = c.g
	_buf[o + 14] = c.b
	_buf[o + 15] = 0.95


func _ring_radius(u: Unit) -> float:
	if u.footprint.size != Vector2i.ZERO:
		return maxf(u.footprint.size.x, u.footprint.size.y) * Grid.CELL * 0.62
	return u.radius * 1.35 + 0.1


func _terrain_normal(p: Vector3, r: float) -> Vector3:
	var m := world.map
	var dx := m.height_at(p.x + r, p.z) - m.height_at(p.x - r, p.z)
	var dz := m.height_at(p.x, p.z + r) - m.height_at(p.x, p.z - r)
	return Vector3(-dx, 2.0 * r, -dz).normalized()


func _grow(count: int) -> void:
	multimesh.instance_count = count
	multimesh.visible_instance_count = 0
	_buf.resize(count * FLOATS)
