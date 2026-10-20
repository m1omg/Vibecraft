class_name Smears
extends MultiMeshInstance3D
## Painted swing smears (juice bible CMB-20, SM-05): one quad per live melee swing in a single
## MultiMesh (pool `CAP`, Compatibility 8). The body composers submit their smear for this frame
## (`submit`), from the swing progress and the fx clock in closed form; `_process` (after the
## views, process_priority 10) uploads the frame's list. The stroke reveals over the last 15 %
## of the wind-up so its head reaches the weapon tip on the damage tick, then fades over
## 80 + 20·mass ms (≤ 140 ms). Shapes from the weapon class (`smear` in data/fx_units.json):
## "over" (overhead arc, blunt / chop), "side" (a sweeping arc in front, slash), "thrust" (a
## streak along the attack, pierce). The arc starts outside the unit's hull. Visual only.

const SHADER := preload("res://src/fx/smear.gdshader")
const CAP := 24
const CAP_COMPAT := 8
const FLOATS := 16                ## 12 transform + 4 custom

var submitted: int = 0
var dropped: int = 0
var _cap: int = CAP
var _n: int = 0
var _buf := PackedFloat32Array()


func _ready() -> void:
	process_priority = 10
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if RenderingServer.get_current_rendering_method() == "gl_compatibility":
		_cap = CAP_COMPAT
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.render_priority = 4
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	multimesh.instance_count = _cap
	multimesh.visible_instance_count = 0
	material_override = mat
	_buf.resize(_cap * FLOATS)


func setup(w: World) -> void:
	var s := w.map.size_world()
	custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 50, s.y + 10))
	multimesh.custom_aabb = custom_aabb


func capacity() -> int:
	return _cap


## One smear for this frame. `xf`: the swing plane (basis x = the arc's 0° direction scaled to
## the reach, y = its 90° direction, origin = the pivot); angles in degrees; shape 0 arc, 1 thrust
## (head / tail are then 0..1 along the reach).
func submit(xf: Transform3D, head: float, tail: float, alpha: float, shape: int) -> bool:
	if _n >= _cap:
		dropped += 1
		return false
	var o := _n * FLOATS
	var b := xf.basis
	_buf[o + 0] = b.x.x
	_buf[o + 1] = b.y.x
	_buf[o + 2] = b.z.x
	_buf[o + 3] = xf.origin.x
	_buf[o + 4] = b.x.y
	_buf[o + 5] = b.y.y
	_buf[o + 6] = b.z.y
	_buf[o + 7] = xf.origin.y
	_buf[o + 8] = b.x.z
	_buf[o + 9] = b.y.z
	_buf[o + 10] = b.z.z
	_buf[o + 11] = xf.origin.z
	_buf[o + 12] = head / 180.0 if shape == 0 else head
	_buf[o + 13] = tail / 180.0 if shape == 0 else tail
	_buf[o + 14] = alpha
	_buf[o + 15] = float(shape)
	_n += 1
	submitted += 1
	return true


func _process(_delta: float) -> void:
	multimesh.visible_instance_count = _n
	if _n > 0:
		multimesh.buffer = _buf
	_n = 0


## The smear of a swing at swing progress `s` (−1 = not swinging) and `age` seconds after its
## contact (−1 = before contact): (head, tail, alpha) along the arc [a0 -> a1], alpha ≤ 0 = none.
## Closed form: the same at any refresh rate.
static func look(s: float, dp: float, age: float, a0: float, a1: float, fade: float) -> Vector3:
	if age >= 0.0:
		if age >= fade:
			return Vector3(a1, a1, 0.0)
		var k := age / fade
		return Vector3(a1, lerpf(a0, a1, Juice.out_quad(k)), 0.85 * (1.0 - k))
	var start := dp * 0.85
	if s < start or s >= dp or dp <= 0.0:
		return Vector3(a0, a0, 0.0)
	var rev := (s - start) / maxf(dp - start, 0.0001)
	return Vector3(lerpf(a0, a1, Juice.in_quad(rev)), a0, 0.85)
