class_name HealthBars
extends MultiMeshInstance3D
## Camera-facing health bars for every living unit in one MultiMesh (billboarding and the fill
## are done in health_bar.gdshader). Per instance custom data: r = hp ratio, g = width (m),
## b = height (m), a = mana ratio (unused yet). Cheap enough for hundreds of units.

const BAR_SHADER := preload("res://src/fx/health_bar.gdshader")
const FLOATS := 16       ## 12 transform + 4 custom per instance
const BAR_H := 0.16

var world: World
var _buf := PackedFloat32Array()


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0, 1.0)
	var mat := ShaderMaterial.new()
	mat.shader = BAR_SHADER
	mat.render_priority = 10
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	material_override = mat
	_grow(256)


func setup(w: World) -> void:
	world = w
	var s := w.map.size_world()
	custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 60, s.y + 10))


func _process(_delta: float) -> void:
	if world == null:
		return
	visible = Settings.always_show_health_bars or Input.is_key_pressed(KEY_ALT)
	if not visible:
		return
	var list := world.unit_list
	if list.size() > multimesh.instance_count:
		_grow(list.size() * 2)
	var n := 0
	for u in list:
		if not u.alive or u.is_resource:
			continue
		_write(n, u)
		n += 1
	multimesh.visible_instance_count = n
	if n > 0:
		multimesh.buffer = _buf


func _write(slot: int, u: Unit) -> void:
	var p := u.display_pos()
	var top := float(u.def.get("height", 1.5)) * float(u.def.get("scale", 1.0))
	var width := clampf(u.radius * 2.4, 0.9, 1.6)
	if u.footprint.size != Vector2i.ZERO:
		width = clampf(u.footprint.size.x * Grid.CELL * 0.6, 1.6, 3.6)
		top += 0.3
	var o := slot * FLOATS
	_buf[o + 0] = 1.0
	_buf[o + 1] = 0.0
	_buf[o + 2] = 0.0
	_buf[o + 3] = p.x
	_buf[o + 4] = 0.0
	_buf[o + 5] = 1.0
	_buf[o + 6] = 0.0
	_buf[o + 7] = p.y + top + 0.45
	_buf[o + 8] = 0.0
	_buf[o + 9] = 0.0
	_buf[o + 10] = 1.0
	_buf[o + 11] = p.z
	_buf[o + 12] = u.hp / u.max_hp
	_buf[o + 13] = width
	_buf[o + 14] = BAR_H
	_buf[o + 15] = u.mana / u.max_mana if u.max_mana > 0.0 else 0.0


func _grow(count: int) -> void:
	multimesh.instance_count = count
	multimesh.visible_instance_count = 0
	_buf.resize(count * FLOATS)
