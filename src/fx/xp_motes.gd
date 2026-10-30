class_name XpMotes
extends MultiMeshInstance3D
## XP that flies to the heroes who earned it (juice HER-03, Playtest 3 subset): per receiving
## hero n = clamp(round(amount / 15), 1, 6) motes in its faction's material (kingdom ivory
## spoke-chips, Tormai bronze flecks) leave the kill point at 1 m height 25 ms apart: a 100 ms
## burst 0.4 m outward and up (out_quad), an 80 ms hang, then a 220–340 ms home along a
## quadratic Bézier (control 1 m above the hang point, in_cubic) to the hero's chest, re-read every
## frame, shrinking to 0.7 on arrival. When the kill crosses a level they fly straight in 180 ms,
## so the XP lands before the level-up it causes. The first arrival clicks (kingdom) or tings
## (Tormai). One MultiMesh, closed-form on the fx clock, at most CAP motes (the oldest yields).

signal arrived(hero: Unit)

const SHADER := preload("res://src/fx/xp_mote.gdshader")
const CAP := 32
const BURST_S := 0.1
const HANG_S := 0.08
const DIRECT_S := 0.18
const STAGGER_S := 0.025
const SIZE := 0.13
const IVORY := Color("#EDE2C8")
const BRONZE := Color("#D9A55E")

var motes: Array[Mote] = []
var launched: int = 0
var _buf := PackedFloat32Array()


class Mote:
	var hero: Unit
	var from: Vector3
	var dir: Vector3
	var t0: float
	var home_s: float
	var shape: int
	var direct: bool
	var lead: bool                 ## the group's first mote: its arrival plays the click


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.render_priority = 6
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	multimesh.instance_count = CAP
	multimesh.visible_instance_count = 0
	material_override = mat
	_buf.resize(CAP * 20)


## Sends `amount` XP's motes from `from` to `hero` (`levels` > 0: the kill crossed a level).
func launch(hero: Unit, amount: float, from: Vector3, levels: int) -> void:
	var n := clampi(roundi(amount / 15.0), 1, 6)
	var shape := 1 if hero.def_id.begins_with("clans_") else 0
	var now := FxClock.fx_now
	for i in n:
		if motes.size() >= CAP:
			motes.remove_at(0)
		var m := Mote.new()
		m.hero = hero
		m.from = from + Vector3(0, 1.0, 0)
		var a := TAU * Juice.hash01(hero.id, launched + i, 31)
		m.dir = Vector3(cos(a), 0.9, sin(a)).normalized()
		m.t0 = now + STAGGER_S * i
		m.home_s = lerpf(0.22, 0.34, Juice.hash01(hero.id, launched + i, 47))
		m.shape = shape
		m.direct = levels > 0
		m.lead = i == 0
		motes.append(m)
	launched += n


## Position, scale and alpha of `m` at fx time `now`; alpha < 0 = not launched yet; scale < 0 = arrived.
static func eval(m: Mote, now: float) -> Array:
	var t := now - m.t0
	if t < 0.0:
		return [m.from, 1.0, -1.0]
	var chest := m.hero.display_pos() + Vector3(0, 0.6 * m.hero.top_height(), 0) if is_instance_valid(m.hero) else m.from
	if m.direct:
		if t >= DIRECT_S:
			return [chest, -1.0, 0.0]
		var u := Juice.in_cubic(t / DIRECT_S)
		return [m.from.lerp(chest, u), lerpf(1.0, 0.7, u), 1.0]
	var hang := m.from + m.dir * 0.4
	if t < BURST_S:
		return [m.from.lerp(hang, Juice.out_quad(t / BURST_S)), 1.0, 1.0]
	if t < BURST_S + HANG_S:
		return [hang, 1.0, 1.0]
	var h := (t - BURST_S - HANG_S) / m.home_s
	if h >= 1.0:
		return [chest, -1.0, 0.0]
	var u := Juice.in_cubic(h)
	var c := hang + Vector3(0, 1.0, 0)
	var q := hang.lerp(c, u).lerp(c.lerp(chest, u), u)
	return [q, lerpf(1.0, 0.7, u), 1.0]


func _process(_delta: float) -> void:
	var now := FxClock.fx_now
	var n := 0
	var i := 0
	while i < motes.size():
		var m := motes[i]
		var e := eval(m, now)
		if float(e[1]) < 0.0:
			if m.lead and is_instance_valid(m.hero):
				arrived.emit(m.hero)
				Audio.play_3d("hero_xp_clans" if m.shape == 1 else "hero_xp_kingdom", m.hero.pos, {"volume_db": -6.0})
			motes.remove_at(i)
			continue
		i += 1
		if float(e[2]) < 0.0:
			continue
		var s := SIZE * float(e[1])
		var p: Vector3 = e[0]
		var o := n * 20
		var b := Basis.IDENTITY.scaled(Vector3(s, s, s))
		_buf[o + 0] = b.x.x
		_buf[o + 1] = b.y.x
		_buf[o + 2] = b.z.x
		_buf[o + 3] = p.x
		_buf[o + 4] = b.x.y
		_buf[o + 5] = b.y.y
		_buf[o + 6] = b.z.y
		_buf[o + 7] = p.y
		_buf[o + 8] = b.x.z
		_buf[o + 9] = b.y.z
		_buf[o + 10] = b.z.z
		_buf[o + 11] = p.z
		var col := BRONZE if m.shape == 1 else IVORY
		_buf[o + 12] = col.r
		_buf[o + 13] = col.g
		_buf[o + 14] = col.b
		_buf[o + 15] = float(e[2])
		_buf[o + 16] = float(m.shape)
		_buf[o + 17] = 1.0
		_buf[o + 18] = 0.0
		_buf[o + 19] = 0.0
		n += 1
	multimesh.buffer = _buf
	multimesh.visible_instance_count = n
