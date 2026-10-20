class_name CameraJuice
extends RefCounted
## The camera impulse system (juice bible §4.7, UCA-F2, CAM-05): the only thing that moves the
## camera besides the player's own hands. Results land in member variables (no per-frame
## allocation) that RtsCamera._apply() writes once per frame:
##   - trauma τ per channel (combat ≤ 0.35, ability ≤ 0.5, cinematic ≤ 1.0; gameplay total
##     ≤ 0.6), linear decay 1.6/s; shake s = τ², translation 0.9 m × (d / 28) in the camera
##     plane (`h_offset` / `v_offset`, constant in pixels at any zoom), roll 1.2°, no pitch or
##     yaw; noise is FastNoiseLite simplex with FRACTAL_NONE sampled at 14 Hz on the ui clock;
##   - the directional kick: one impulse into a 2D spring (ω 28, ζ 0.32) along −u, u pointing
##     from the screen centre to the event, so the view jolts away from the blast;
##   - falloff 1 − smoothstep(r_in, r_out, d) from the camera focus; gates: in the frustum
##     (2 m) and visible to the local player; ×0.3 during precision work (drag box, targeting);
##     `enabled` false (settings, reduce motion) → nothing.
## Whitelist (exhaustive, ui §5.4): siege powder +0.35 / pots +0.25 (CMB-27), own slam
## ultimates +0.40, end-sequence collapse. Anything else is a review reject.
## Every term is a closed-form function of (ui_now − t0): identical at any refresh rate.

const CHANNELS: Array[StringName] = [&"combat", &"ability", &"cinematic"]

static var current: CameraJuice

var enabled: bool = true
var precision: bool = false
var shake_offset := Vector2.ZERO          ## metres in the camera plane (x right, y up)
var shake_roll: float = 0.0               ## radians about the view axis
var kick_offset := Vector2.ZERO
var added: int = 0
var rejected: int = 0

var _tau0: Dictionary = {}                ## channel -> Vector2(τ at t0, t0)
var _kick_x0 := Vector2.ZERO
var _kick_v0 := Vector2.ZERO
var _kick_t0: float = -100.0
var _noise := FastNoiseLite.new()
var _camera: Camera3D


func _init(cam: Camera3D = null) -> void:
	_camera = cam
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX
	_noise.fractal_type = FastNoiseLite.FRACTAL_NONE
	_noise.frequency = 1.0
	_noise.seed = 9137
	for c in CHANNELS:
		_tau0[c] = Vector2(0.0, -100.0)


## Current trauma of a channel at ui time `t`.
func trauma(channel: StringName, t: float = FxClock.ui_now) -> float:
	var s: Vector2 = _tau0.get(channel, Vector2.ZERO)
	return maxf(s.x - FeelConstants.c().trauma_decay * (t - s.y), 0.0)


func total_trauma(t: float = FxClock.ui_now) -> float:
	var sum := 0.0
	for c in CHANNELS:
		sum += trauma(c, t)
	return minf(sum, 1.0)


## The only call site pattern: `CameraJuice.current.add_trauma(&"combat", 0.35, impact_pos)`.
## Returns false when gated out.
func add_trauma(channel: StringName, amount: float, world_pos: Vector3, r_in: float = 6.0, r_out: float = 10.0) -> bool:
	if not enabled or not _tau0.has(channel) or amount <= 0.0:
		rejected += 1
		return false
	var fc := FeelConstants.c()
	var falloff := 1.0
	var u := Vector2.ZERO
	var d := 28.0
	if _camera != null and _camera.is_inside_tree():
		var focus: Variant = _camera.get("focus")
		var f: Vector3 = focus if focus is Vector3 else world_pos
		d = float(_camera.get("distance")) if _camera.get("distance") != null else 28.0
		falloff = 1.0 - smoothstep(r_in, r_out, Vector2(world_pos.x - f.x, world_pos.z - f.z).length())
		if not _in_frustum(world_pos):
			falloff = 0.0
		var vp := _camera.get_viewport().get_visible_rect().size
		var sp := _camera.unproject_position(world_pos)
		u = (sp - vp * 0.5)
		u = Vector2(u.x, -u.y).normalized() if u.length_squared() > 1.0 else Vector2.ZERO
	if falloff <= 0.0:
		rejected += 1
		return false
	if precision:
		amount *= fc.precision_factor
	var cap := fc.trauma_cap_combat
	if channel == &"ability":
		cap = fc.trauma_cap_ability
	elif channel == &"cinematic":
		cap = fc.trauma_cap_cinematic
	var now := FxClock.ui_now
	var cur := trauma(channel, now)
	var room := cap if channel == &"cinematic" else minf(cap, fc.trauma_cap_total - (total_trauma(now) - cur))
	_tau0[channel] = Vector2(clampf(cur + amount * falloff, 0.0, maxf(room, cur)), now)
	# directional kick away from the event
	var a := fc.kick_amp_m * amount * falloff * (d / 28.0)
	var st := _kick_state(now)
	_kick_x0 = Vector2(st.x, st.y)
	_kick_v0 = Vector2(st.z, st.w) - u * Juice.kick_for_peak(a, fc.kick_omega, fc.kick_zeta)
	_kick_t0 = now
	added += 1
	return true


func _in_frustum(p: Vector3) -> bool:
	for pl in _camera.get_frustum():
		if pl.distance_to(p) > 2.0:
			return false
	return true


func _kick_state(t: float) -> Vector4:
	var age := t - _kick_t0
	if age < 0.0 or age > 3.0:
		return Vector4.ZERO
	var fc := FeelConstants.c()
	var x := Juice.spring(_kick_x0.x, _kick_v0.x, fc.kick_omega, fc.kick_zeta, age)
	var y := Juice.spring(_kick_x0.y, _kick_v0.y, fc.kick_omega, fc.kick_zeta, age)
	return Vector4(x.x, y.x, x.y, y.y)


## Evaluates the shake and kick at ui time `t` for a camera at `distance`.
func evaluate(t: float, distance: float) -> void:
	var fc := FeelConstants.c()
	if not enabled:
		shake_offset = Vector2.ZERO
		shake_roll = 0.0
		kick_offset = Vector2.ZERO
		return
	var s := total_trauma(t)
	s *= s
	var hz := minf(fc.shake_hz, 15.0)
	if s > 0.0:
		var nx := clampf(_noise.get_noise_2d(t * hz, 11.0) / 0.7, -1.0, 1.0)
		var ny := clampf(_noise.get_noise_2d(t * hz, 47.0) / 0.7, -1.0, 1.0)
		var nr := clampf(_noise.get_noise_2d(t * hz, 83.0) / 0.7, -1.0, 1.0)
		var tr := fc.shake_translation_m * (distance / 28.0) * s
		shake_offset = Vector2(nx, ny) * tr
		shake_roll = deg_to_rad(fc.shake_roll_deg) * s * nr
	else:
		shake_offset = Vector2.ZERO
		shake_roll = 0.0
	var k := _kick_state(t)
	kick_offset = Vector2(k.x, k.y)
