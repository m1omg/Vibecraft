class_name GroundMarks
extends MultiMeshInstance3D
## Decal-substitute ground projector (juice bible §4.4): every transient ground mark (order
## ripples, attack-move chevrons, target blinks, dust rings, crosshairs, patrol arrows, waypoint
## and rally dashes) is one instance of a flat quad laid on the terrain in this single MultiMesh
## (one draw). Marks are records with a kind, a start time on the ui or fx clock and a life; each
## frame the live ones are evaluated in closed form from (now - t0) (`eval_mark`) and packed,
## expired ones are swap-removed, and `visible_instance_count` is the live count. Frame marks
## (`add_frame`) are drawn for one frame only (waypoint lines rebuilt each frame).
## Visual only. No node, Tween or Dictionary per mark.

enum Shape { RING, RING_DASHED, RING_NOTCHED, SOFT_RING, CHEVRONS, CROSSHAIR, DISC, DASH_LINE, ARROWS }
enum Kind { RIPPLE, DUST_RING, CHEVRON_IN, CROSSHAIR_IN, PATROL, TARGET_BLINK, FLASH_RING }

const SHADER := preload("res://src/fx/ground_mark.gdshader")
const CAP := 192
const FLOATS := 20               ## 12 transform + 4 colour + 4 custom
const LIFT := 0.055

var world: World
var live: int = 0
var frame_count: int = 0
var dropped: int = 0

var _kind := PackedInt32Array()
var _pos := PackedVector3Array()
var _follow: Array = []          ## Unit or null
var _r0 := PackedFloat32Array()
var _r1 := PackedFloat32Array()
var _col := PackedColorArray()
var _t0 := PackedFloat64Array()
var _life := PackedFloat32Array()
var _ui := PackedByteArray()
var _param := PackedFloat32Array()
var _buf := PackedFloat32Array()
var _frame_buf := PackedFloat32Array()


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.render_priority = 2
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	multimesh.instance_count = CAP
	multimesh.visible_instance_count = 0
	material_override = mat
	_buf.resize(CAP * FLOATS)
	# packed arrays are values: resize each member directly
	_kind.resize(CAP)
	_pos.resize(CAP)
	_r0.resize(CAP)
	_r1.resize(CAP)
	_col.resize(CAP)
	_t0.resize(CAP)
	_life.resize(CAP)
	_ui.resize(CAP)
	_param.resize(CAP)
	_follow.resize(CAP)


func setup(w: World) -> void:
	world = w
	var s := w.map.size_world()
	multimesh.custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 50, s.y + 10))
	custom_aabb = multimesh.custom_aabb


## Adds a mark. `t_offset` delays it (negative age is invisible); `follow` keeps it on a unit's
## interpolated position; `ui_clock` false = the fx clock (pauses with the game).
func add(kind: int, pos: Vector3, r0: float, r1: float, color: Color, life: float,
		t_offset: float = 0.0, param: float = 0.0, follow: Unit = null, ui_clock: bool = true) -> void:
	if live >= CAP:
		# the oldest mark yields (never a live information mark: they are short)
		_remove(_oldest())
		dropped += 1
	var i := live
	live += 1
	_kind[i] = kind
	_pos[i] = pos
	_follow[i] = follow
	_r0[i] = r0
	_r1[i] = r1
	_col[i] = color
	_t0[i] = (FxClock.ui_now if ui_clock else FxClock.fx_now) + t_offset
	_life[i] = life
	_ui[i] = 1 if ui_clock else 0
	_param[i] = param


## A mark drawn for this frame only, with an explicit transform (basis scaled to the quad's
## half-size) and shape data.
func add_frame(xf: Transform3D, shape: int, color: Color, thickness: float, param: float, outline: float = 0.0) -> void:
	if live + frame_count >= CAP:
		return
	var o := frame_count * FLOATS
	if _frame_buf.size() < o + FLOATS:
		_frame_buf.resize(o + FLOATS * 16)
	_pack(_frame_buf, o, xf, color, shape, thickness, param, outline)
	frame_count += 1


## Closed-form state of mark `i` at its clock's `now`: (shape, radius m, thickness fraction,
## alpha, param, outline). Returns radius < 0 when not visible yet, alpha < 0 when expired.
func eval_mark(i: int, now: float) -> PackedFloat32Array:
	var age := now - _t0[i]
	var life := _life[i]
	var out := PackedFloat32Array([Shape.RING, -1.0, 0.1, 0.0, 0.0, 0.0])
	if age < 0.0:
		return out
	if age >= life:
		out[3] = -1.0
		return out
	var u := age / life
	match _kind[i]:
		Kind.RIPPLE:
			var r := lerpf(_r0[i], _r1[i], Juice.out_cubic(u))
			out[1] = r
			out[2] = lerpf(0.06, 0.02, u) / maxf(r, 0.05) * 2.4
			out[3] = 0.95 * (1.0 - Juice.in_quad(u))
			out[5] = 0.6
		Kind.DUST_RING:
			out[0] = Shape.SOFT_RING
			var r2 := lerpf(_r0[i], _r1[i], Juice.out_quad(u))
			out[1] = r2
			out[2] = 0.55
			out[3] = 1.0 - u
		Kind.CHEVRON_IN:
			out[0] = Shape.CHEVRONS
			out[1] = _r0[i]
			var conv := 0.26
			var k := clampf(age / conv, 0.0, 1.0)
			out[4] = lerpf(1.0, 0.35 / maxf(_r0[i], 0.1), Juice.in_quad(k)) * 0.82
			out[3] = 1.0 if age < conv else 1.0 - Juice.window(age, conv, life - conv)
			out[5] = 0.5
		Kind.CROSSHAIR_IN:
			out[0] = Shape.CROSSHAIR
			out[1] = _r0[i]
			out[2] = 0.09
			out[4] = lerpf(1.1, 0.42, Juice.out_cubic(Juice.window(age, 0.0, 0.2)))
			out[3] = 1.0 - Juice.window(age, life - 0.2, 0.2)
			out[5] = 0.5
		Kind.PATROL:
			out[0] = Shape.ARROWS
			out[1] = _r0[i]
			out[2] = 0.16
			out[4] = PI * Juice.in_out_sine(clampf(age / 0.6, 0.0, 1.0)) + 0.6
			out[3] = 1.0 - Juice.window(age, life - 0.15, 0.15)
			out[5] = 0.5
		Kind.TARGET_BLINK:
			out[0] = Shape.RING_NOTCHED if _param[i] > 0.0 else Shape.RING
			out[1] = _r0[i]
			out[2] = 0.16
			out[4] = _param[i]
			out[3] = target_blink_alpha(age)
			out[5] = 0.55
		Kind.FLASH_RING:
			out[1] = lerpf(_r0[i], _r1[i], Juice.out_quad(u))
			out[2] = 0.12
			out[3] = 1.0 - Juice.out_quad(u)
			out[5] = 0.4
	return out


## CMB-09: on 0-80, off 80-150, on 150-230, off 230-300, on 300-380, fading 380-460 ms.
static func target_blink_alpha(age: float) -> float:
	var ms := age * 1000.0
	if ms < 80.0 or (ms >= 150.0 and ms < 230.0) or (ms >= 300.0 and ms < 380.0):
		return 1.0
	if ms >= 380.0 and ms < 460.0:
		return 1.0 - (ms - 380.0) / 80.0
	return 0.0


func count_kind(kind: int) -> int:
	var n := 0
	for i in live:
		if _kind[i] == kind:
			n += 1
	return n


func _process(_delta: float) -> void:
	if world == null:
		return
	var i := 0
	var n := 0
	while i < live:
		var f: Variant = _follow[i]
		if f != null:
			if not is_instance_valid(f) or not (f as Unit).alive:
				_follow[i] = null
			else:
				_pos[i] = (f as Unit).display_pos()
		var now := FxClock.ui_now if _ui[i] == 1 else FxClock.fx_now
		var st := eval_mark(i, now)
		if st[3] < 0.0:
			_remove(i)
			continue
		if st[1] > 0.0 and st[3] > 0.003:
			var col := _col[i]
			col.a *= st[3]
			_pack(_buf, n * FLOATS, _ground_xf(_pos[i], st[1], i), col, int(st[0]), st[2], st[4], st[5])
			n += 1
		i += 1
	if frame_count > 0:
		var m := mini(frame_count, CAP - n)
		for k in m * FLOATS:
			_buf[n * FLOATS + k] = _frame_buf[k]
		n += m
		frame_count = 0
	multimesh.visible_instance_count = n
	if n > 0:
		multimesh.buffer = _buf


func _ground_xf(p: Vector3, r: float, salt: int) -> Transform3D:
	var m := world.map
	var s := maxf(r, 0.3)
	var dx := m.height_at(p.x + s, p.z) - m.height_at(p.x - s, p.z)
	var dz := m.height_at(p.x, p.z + s) - m.height_at(p.x, p.z - s)
	var nrm := Vector3(-dx, 2.0 * s, -dz).normalized()
	var z := Vector3(1, 0, 0).cross(nrm).normalized()
	var x := nrm.cross(z).normalized()
	var y := m.height_at(p.x, p.z) + LIFT + float(salt % 8) * 0.002
	return Transform3D(Basis(x * r, nrm * r, z * r), Vector3(p.x, y, p.z))


static func _pack(buf: PackedFloat32Array, o: int, xf: Transform3D, col: Color, shape: int,
		thickness: float, param: float, outline: float) -> void:
	var b := xf.basis
	buf[o + 0] = b.x.x
	buf[o + 1] = b.y.x
	buf[o + 2] = b.z.x
	buf[o + 3] = xf.origin.x
	buf[o + 4] = b.x.y
	buf[o + 5] = b.y.y
	buf[o + 6] = b.z.y
	buf[o + 7] = xf.origin.y
	buf[o + 8] = b.x.z
	buf[o + 9] = b.y.z
	buf[o + 10] = b.z.z
	buf[o + 11] = xf.origin.z
	buf[o + 12] = col.r
	buf[o + 13] = col.g
	buf[o + 14] = col.b
	buf[o + 15] = col.a
	buf[o + 16] = float(shape)
	buf[o + 17] = thickness
	buf[o + 18] = param
	buf[o + 19] = outline


func _oldest() -> int:
	var best := 0
	for i in live:
		if _t0[i] < _t0[best]:
			best = i
	return best


func _remove(i: int) -> void:
	var last := live - 1
	if i != last:
		_kind[i] = _kind[last]
		_pos[i] = _pos[last]
		_follow[i] = _follow[last]
		_r0[i] = _r0[last]
		_r1[i] = _r1[last]
		_col[i] = _col[last]
		_t0[i] = _t0[last]
		_life[i] = _life[last]
		_ui[i] = _ui[last]
		_param[i] = _param[last]
	_follow[last] = null
	live = last
