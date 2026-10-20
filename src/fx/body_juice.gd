class_name BodyJuice
extends RefCounted
## The unit body composer for the slice P0 rows (combat CMB-01, 02, 03, 10, 13, 16, 21, 30).
## One per mobile UnitView. Additive layers sum into ONE write per frame of the view's `rig`
## transform (pivot at the feet; physics interpolation off, so it composes with the Unit's
## interpolated transform): pitch (lean, push-off, stop plant, nods, acks), roll (banking into
## turns), knockback offset + tilt + tremble, volume-preserving squash. Rings and health bars
## stay on the sim position: only the body moves.
## Refresh-rate independence by construction: the pitch is a piecewise closed-form function of
## age (each segment starts from the value of the previous one at a back-dated transition time),
## knockback is the exact spring solution from its last impulse, nods and acks are closed-form
## curves of ui time, stride plants are crossing tests on travelled distance, and the bank uses
## an exact spring between ticks. Reads sim state only; never writes it.

enum Gait { IDLE, SHUFFLE, WALK }
enum Seg { SPRING, PUSHOFF, STOP }

var view: UnitView
var unit: Unit
var sheet: Dictionary = {}
var gait: int = Gait.IDLE
var dust_spawned: int = 0
var whooshes: int = 0

var _fc: FeelConstants
var _above: float = 0.0
var _below: float = 0.0
# pitch segment (degrees, forward positive)
var _seg: int = Seg.SPRING
var _seg_t0: float = -100.0
var _seg_p0: float = 0.0
var _seg_target: float = 0.0
var _squash_t0: float = -100.0
# bank
var _last_tick: int = -1
var _last_facing: float = 0.0
var _yaw_rate: float = 0.0
var _roll := Vector2.ZERO
# nods and acks (ui clock)
var _nod_t0: float = -100.0
var _nod_scale: float = 1.0
var _ack_t0: float = -100.0
var _ack_kind: int = 0
# knockback (unit-local XZ) from the last impulse
var _k_t0: float = -100.0
var _k_x0 := Vector2.ZERO
var _k_v0 := Vector2.ZERO
var _k_omega: float = 24.0
var _k_zeta: float = 0.5
var _k_tilt: float = 1.2
var _tremble_t0: float = -100.0
# stride
var _phase: float = 0.0
var _last_pos := Vector3.INF
# swing
var _swing_prev: float = -1.0
var _whoosh_done: bool = false
# death
var _death_dust: bool = false


func _init(v: UnitView) -> void:
	view = v
	unit = v.unit
	sheet = FxDefs.sheet(unit)
	_fc = FeelConstants.c()
	_last_facing = unit.facing
	_k_omega = clampf(24.0 / sqrt(maxf(mass(), 0.1)), 12.0, 30.0)
	_k_zeta = clampf(0.5 + 0.08 * (mass() - 1.0), 0.46, 0.8)
	if mass() >= 2.5:
		_k_zeta = 0.8
		_k_tilt = 0.6


func mass() -> float:
	return float(sheet.get("mass", 1.0))


# --- events ----------------------------------------------------------------------------------

## Order ripple nod (CMB-10), starting at ui time `t0` (may be in the future: the ripple delay).
## At most one nod per `nod_min_gap_ms` per unit; returns false when rate-limited.
func nod(t0: float, scale: float = 1.0) -> bool:
	if t0 - _nod_t0 < _fc.nod_min_gap_ms / 1000.0 and t0 >= _nod_t0:
		return false
	_nod_t0 = t0
	_nod_scale = scale
	return true


## Voice ack (CMB-13): 0 = "what" chin-up (pitch -8° in 100 ms, spring back ω 12 ζ 0.5);
## 1 = order ack (the grammar's nod, 1.25x).
func ack(kind: int, t0: float = FxClock.ui_now) -> void:
	if t0 - _ack_t0 < _fc.ack_min_gap_ms / 1000.0 and kind == _ack_kind:
		return
	_ack_t0 = t0
	_ack_kind = kind


## Knockback impulse (CMB-21) away from `origin` (attacker for melee, impact point for missiles).
func knock(origin: Vector3, amount: float, max_hp: float, base_m: float, crit: bool = false) -> void:
	if origin == Vector3.INF:
		return
	var p := unit.display_pos()
	var d := Vector2(p.x - origin.x, p.z - origin.z)
	if d.length_squared() < 1e-6:
		d = Vector2(sin(unit.facing), cos(unit.facing))
	d = d.normalized()
	var a := base_m * clampf(0.6 + amount / maxf(0.08 * max_hp, 0.01), 0.6, 1.6) * (1.6 if crit else 1.0)
	a /= maxf(mass(), 0.3)
	if unit.is_swinging():
		a *= 0.6
	if unit.holding:
		a *= 0.5
	a = minf(a, _fc.knock_max_m)
	# world XZ -> unit-local XZ (the unit's yaw is `facing`, forward = -Z)
	var c := cos(unit.facing)
	var s := sin(unit.facing)
	var local := Vector2(c * d.x - s * d.y, s * d.x + c * d.y)
	var now := FxClock.fx_now
	var st := _knock_state(now)
	var kick := Juice.kick_for_peak(a, _k_omega, minf(_k_zeta, 0.99))
	_k_x0 = Vector2(st.x, st.y)
	_k_v0 = Vector2(st.z, st.w) + local * kick
	_k_t0 = now
	_tremble_t0 = now


## Per-frame composition. `dt` = the frame's fx delta (0 while paused).
func compose(dt: float) -> void:
	if view == null or view.rig == null or not is_instance_valid(unit):
		return
	var now := FxClock.fx_now
	var ui := FxClock.ui_now
	_update_gait(dt, now)
	_update_bank(dt)
	var pitch := pitch_at(now) + nod_at(ui) + ack_at(ui)
	var roll := rad_to_deg(_roll.x)
	var sy := squash_at(now)
	var ks := _knock_state(now)
	var off := Vector3(ks.x, 0.0, ks.y)
	var tr_age := now - _tremble_t0
	var tr_len := _fc.tremble_ms / 1000.0
	if tr_age >= 0.0 and tr_age < tr_len:
		var k := (1.0 - tr_age / tr_len) * _fc.tremble_m
		off.x += Juice.vnoise(unit.id, now, _fc.tremble_hz) * k
		off.z += Juice.vnoise(unit.id + 7919, now, _fc.tremble_hz) * k
	var lim := _fc.body_offset_max_m
	if off.length() > lim:
		off = off.normalized() * lim
	var b := Basis.from_euler(Vector3(deg_to_rad(-pitch), 0.0, deg_to_rad(roll)))
	var flat := Vector2(off.x, off.z)
	if flat.length_squared() > 1e-8:
		var axis := Vector3.UP.cross(Vector3(off.x, 0.0, off.z).normalized())
		b = Basis(axis.normalized(), flat.length() * _k_tilt) * b
	if absf(sy - 1.0) > 1e-4:
		var side := 1.0 / sqrt(maxf(sy, 0.1))
		b = b * Basis.from_scale(Vector3(side, sy, side))
	view.rig.transform = Transform3D(b, off)
	_update_stride()
	_update_swing()


# --- closed-form layers ------------------------------------------------------------------------

## Body pitch in degrees (forward positive) at fx time `t` from the current segment.
func pitch_at(t: float) -> float:
	var age := t - _seg_t0
	match _seg:
		Seg.PUSHOFF:
			var ramp := _fc.pushoff_ms / 1000.0
			if age < ramp:
				return lerpf(_seg_p0, _fc.pushoff_deg, Juice.out_quad(age / ramp))
			return _seg_target + Juice.spring(_fc.pushoff_deg - _seg_target, 0.0, _fc.cruise_omega,
				_fc.cruise_zeta, age - ramp).x
		Seg.STOP:
			var ramp2 := _fc.stop_ms / 1000.0
			if age < ramp2:
				return lerpf(_seg_p0, -_fc.stop_deg, Juice.out_quad(age / ramp2))
			var z := float(sheet.get("stop_zeta", _fc.stop_zeta))
			return Juice.spring(-_fc.stop_deg, 0.0, _fc.stop_omega, z, age - ramp2).x
	return _seg_target + Juice.spring(_seg_p0 - _seg_target, 0.0, _fc.cruise_omega, _fc.cruise_zeta, maxf(age, 0.0)).x


func squash_at(t: float) -> float:
	var age := t - _squash_t0
	var len := _fc.stop_squash_ms / 1000.0
	if age < 0.0 or age >= len:
		return 1.0
	return lerpf(float(sheet.get("stop_squash", _fc.stop_squash)), 1.0, Juice.out_quad(age / len))


## Order nod (degrees, forward positive) at ui time `t`.
func nod_at(t: float) -> float:
	var age := t - _nod_t0
	var deg := float(sheet.get("nod_deg", 8.0)) * _nod_scale
	var down := float(sheet.get("nod_down_ms", 50.0)) / 1000.0
	var up := float(sheet.get("nod_up_ms", 110.0)) / 1000.0
	if age < 0.0 or age >= down + up:
		return 0.0
	if age < down:
		return deg * Juice.out_quad(age / down)
	return deg * (1.0 - Juice.in_out_sine((age - down) / up))


func ack_at(t: float) -> float:
	var age := t - _ack_t0
	if age < 0.0 or age > 0.6:
		return 0.0
	if _ack_kind == 0:
		if age < 0.1:
			return -8.0 * Juice.out_quad(age / 0.1)
		return Juice.spring(-8.0, 0.0, 12.0, 0.5, age - 0.1).x
	var deg := float(sheet.get("nod_deg", 8.0)) * 1.25
	var down := float(sheet.get("nod_down_ms", 50.0)) / 1000.0
	var up := float(sheet.get("nod_up_ms", 110.0)) / 1000.0
	if age < down:
		return deg * Juice.out_quad(age / down)
	return deg * (1.0 - Juice.in_out_sine(clampf((age - down) / up, 0.0, 1.0)))


## Knockback state at fx time `t`: (x, z, vx, vz) in unit-local metres.
func _knock_state(t: float) -> Vector4:
	var age := t - _k_t0
	if age < 0.0 or age > 2.0:
		return Vector4.ZERO
	var z := minf(_k_zeta, 0.99)
	var ax := Juice.spring(_k_x0.x, _k_v0.x, _k_omega, z, age)
	var az := Juice.spring(_k_x0.y, _k_v0.y, _k_omega, z, age)
	return Vector4(ax.x, az.x, ax.y, az.y)


func knock_offset(t: float = FxClock.fx_now) -> Vector2:
	var s := _knock_state(t)
	return Vector2(s.x, s.y)


# --- gait, bank, stride, swing -------------------------------------------------------------------

func _update_gait(dt: float, now: float) -> void:
	var ratio := 0.0
	if unit.speed > 0.0 and unit.alive:
		ratio = unit.velocity.length() / unit.speed
	if unit.is_swinging():
		ratio = 0.0
	var enter := _fc.walk_enter_ms / 1000.0
	var leave := _fc.idle_enter_ms / 1000.0
	if ratio > _fc.walk_enter_ratio:
		_above += dt
		_below = 0.0
	elif ratio < _fc.idle_enter_ratio:
		_below += dt
		_above = 0.0
	else:
		_above = 0.0
		_below = 0.0
	if gait != Gait.WALK and _above >= enter:
		# back-dated: the push-off starts exactly when the hysteresis was satisfied
		var t0 := now - (_above - enter)
		_start_seg(Seg.PUSHOFF, t0, float(sheet.get("lean_deg", 4.0)))
		gait = Gait.WALK
		if view.on_screen():
			_dust_at_feet(1.5)
	elif gait == Gait.WALK and _below >= leave:
		var t1 := now - (_below - leave)
		_start_seg(Seg.STOP, t1, 0.0)
		_squash_t0 = t1
		gait = Gait.IDLE
		if view.on_screen():
			_dust_at_feet(1.0)
	elif gait == Gait.IDLE and ratio >= _fc.idle_enter_ratio and ratio <= _fc.walk_enter_ratio:
		gait = Gait.SHUFFLE
	elif gait == Gait.SHUFFLE and _below >= leave:
		gait = Gait.IDLE


func _start_seg(seg: int, t0: float, target: float) -> void:
	_seg_p0 = pitch_at(t0)
	_seg = seg
	_seg_t0 = t0
	_seg_target = target


func _update_bank(dt: float) -> void:
	var w := unit.world
	if w == null:
		return
	if w.tick_count != _last_tick:
		var ticks := maxi(w.tick_count - _last_tick, 1) if _last_tick >= 0 else 1
		_yaw_rate = Juice.wrap_angle(unit.facing - _last_facing) / (ticks * World.DT)
		_last_facing = unit.facing
		_last_tick = w.tick_count
	var ratio := unit.velocity.length() / unit.speed if unit.speed > 0.0 else 0.0
	var k := _fc.bank_k if str(sheet.get("gait", "biped")) == "biped" else 0.0
	var lim := deg_to_rad(_fc.bank_max_deg)
	var target := clampf(_yaw_rate * clampf(ratio, 0.0, 1.0) * k, -lim, lim)
	var r := Juice.spring(_roll.x - target, _roll.y, _fc.bank_omega, _fc.bank_zeta, dt)
	_roll = Vector2(r.x + target, r.y)


func _update_stride() -> void:
	var p := unit.display_pos()
	if _last_pos == Vector3.INF:
		_last_pos = p
		return
	var dist := Vector2(p.x - _last_pos.x, p.z - _last_pos.z).length()
	_last_pos = p
	if dist > 2.0:
		return   # teleport
	var stride := maxf(float(sheet.get("stride_len_m", 1.4)), 0.2)
	var prev := _phase
	_phase += dist / stride * TAU
	# a plant at every half cycle: crossing multiples of PI
	var plants := floori(_phase / PI) - floori(prev / PI)
	if plants > 0 and gait == Gait.WALK and _fc.footstep_dust:
		if _phase > 1.0e6:
			_phase = fmod(_phase, TAU)
		if view.on_screen() and _near_focus(p):
			var side := 1.0 if floori(_phase / PI) % 2 == 0 else -1.0
			var right := Vector3(cos(unit.facing), 0.0, -sin(unit.facing))
			var foot := p + right * side * unit.radius * 0.35
			if Vfx.instance != null and Vfx.instance.particles != null:
				Vfx.instance.particles.burst("dust_step", foot + Vector3(0, 0.05, 0), Vector3.UP, 0.7, 0)
				dust_spawned += 1


func _near_focus(p: Vector3) -> bool:
	var cam := view.get_viewport().get_camera_3d() if view.is_inside_tree() else null
	if cam == null:
		return true
	var f: Variant = cam.get("focus")
	var c: Vector3 = f if f is Vector3 else cam.global_position
	return Vector2(p.x - c.x, p.z - c.z).length() <= _fc.footstep_dust_max_m


func _dust_at_feet(mult: float) -> void:
	if Vfx.instance == null or Vfx.instance.particles == null or not _near_focus(unit.display_pos()):
		return
	Vfx.instance.particles.burst("dust_step", unit.display_pos() + Vector3(0, 0.05, 0), Vector3.UP, mult, 0)
	dust_spawned += 1


## Melee whoosh (CMB-16): its peak lands on contact. Started by a crossing test on the swing
## time at contact - peak; a swing that is shorter than the peak lead starts it at once.
func _update_swing() -> void:
	var s := unit.swing_progress()
	if s < 0.0:
		_swing_prev = -1.0
		return
	if _swing_prev < 0.0 or s < _swing_prev - 0.2:
		_whoosh_done = false
	var prev := maxf(_swing_prev, 0.0)
	_swing_prev = s
	if _whoosh_done or not unit.projectile.is_empty():
		return
	var total := (unit.damage_point_ticks + unit.backswing_ticks) * World.DT
	var dp := unit.damage_point_ratio()
	var family := str(sheet.get("whoosh", ""))
	if family.is_empty() or total <= 0.0:
		return
	var peak := Audio.peak_s(family) if Audio != null else 0.12
	var start := dp * total - peak
	if s * total >= start and (prev * total < start or start <= 0.0):
		_whoosh_done = true
		if view.on_screen():
			Audio.event("whoosh", unit.display_pos() + Vector3(0, 1.0, 0), {"family": family,
				"mass": mass(), "from": maxf(-start, 0.0), "seed": unit.id * 7 + unit.world.tick_count})
			whooshes += 1


# --- swing remap (hit-stop) -----------------------------------------------------------------

## Visual hit-stop length as a phase of the swing (CMB-16): h = min(hs / T, 0.35 (1 - dp)).
func hold_phase() -> float:
	var total := (unit.damage_point_ticks + unit.backswing_ticks) * World.DT
	if total <= 0.0:
		return 0.0
	var hs := float(sheet.get("hit_stop_ms", 45.0)) + (_fc.hitstop_hero_bonus_ms if unit.is_hero else 0.0)
	return minf(hs / 1000.0 / total, _fc.hitstop_max_frac * (1.0 - unit.damage_point_ratio()))


## Clip progress for a skinned strike: the contact frame lands on the damage tick and is held
## for the hit-stop (Juice.strike_phase).
func remap_swing(s: float) -> float:
	return Juice.strike_phase(s, unit.damage_point_ratio(), hold_phase(), float(sheet.get("split", 0.6)))


## Placeholder strike pose P (Juice.anticipate): load, snap, hold, recover.
func swing_pose(s: float) -> float:
	return Juice.anticipate(s, unit.damage_point_ratio(), hold_phase(), float(sheet.get("split", 0.6)),
		0.0, float(sheet.get("pull", -0.3)), float(sheet.get("c1", 1.3)))


# --- death ---------------------------------------------------------------------------------------

## Death contact (CMB-30): a ring of dust at the hips when the body lands. `contact_s` from the
## death beat; called every frame while dead.
func compose_dead(contact_s: float) -> void:
	if view == null or view.rig == null:
		return
	view.rig.transform = Transform3D.IDENTITY
	if _death_dust:
		return
	var t := unit.dead_time() - _fc.death_beat_ms / 1000.0
	if t < contact_s:
		return
	_death_dust = true
	if Vfx.instance != null and view.on_screen():
		Vfx.instance.body_landed(unit, unit.display_pos())
