class_name VehicleRig
extends RefCounted
## Procedural motion of a multi-node vehicle model (tools/kits/siege.py; visual only, never
## writes sim state). The model's moving parts are child nodes whose origin is their pivot:
##   - `Wheel_*` roll about local X with the distance the unit travels along its facing (from
##     the interpolated display position, so the sum over frames is the same at any refresh rate);
##   - `*_Leg_*` swing about local X on that distance phase (left / right in opposition, each crew
##     a quarter cycle apart), `Crew_*` bodies bob on it; both settle to rest as the unit stops;
##   - `Barrel` recoils along +Z (back) and kicks up when the shot leaves: the kick is latched on
##     the fx clock at the sim's damage point (back-dated to the tick), slams back in 40 ms and
##     runs out to battery over the next 0.8 s, so it never snaps when the swing ends;
##   - `Arm` (the Sling-Cart's throwing arm) is posed from the sim's swing progress: it cocks back
##     over the first 70 % of the wind-up, whips forward through upright to the release on the
##     damage tick, and settles over the backswing; a cancelled swing eases back to upright.
## Node extras from the kit (glTF `extras`: `radius_m`, `recoil_m`) override the defaults.

const DEFAULT_WHEEL_R := 0.52
const DEFAULT_RECOIL_M := 0.2
const STRIDE_M := 1.15             ## metres per full leg cycle (two steps)
const LEG_SWING_RAD := 0.42
const BOB_M := 0.025
const MAX_STEP_M := 3.0            ## a frame jump larger than this is a teleport (ignored)
const RECOIL_IN_S := 0.04
const RECOIL_HOLD_S := 0.12
const RECOIL_OUT_S := 0.8
const RECOIL_KICK_RAD := 0.07
const ARM_COCK_RAD := 0.5           ## tip back (rotation.x > 0 tips the arm towards +Z, the back)
const ARM_RELEASE_RAD := -1.05      ## tip forward at the release
const ARM_SETTLE_K := 6.0           ## a cancelled swing eases back at this exponential rate

var wheels: Array[Node3D] = []
var wheel_r: Array[float] = []
var legs: Array[Node3D] = []
var leg_phase: Array[float] = []
var crews: Array[Node3D] = []
var crew_rest: Array[Vector3] = []
var crew_phase: Array[float] = []
var barrel: Node3D
var barrel_rest: Vector3
var arm: Node3D
var recoil_m: float = DEFAULT_RECOIL_M
## Signed metres travelled along the facing (visual).
var distance: float = 0.0
## fx time of the latest shot (-1 = none yet).
var fired_at: float = -1.0
var _last_pos: Vector3 = Vector3.INF
var _was_past_dp: bool = false


## The rig of a model that has `Wheel_*` nodes, else null.
static func find(model: Node3D) -> VehicleRig:
	if model == null:
		return null
	var found: Array[Node] = model.find_children("Wheel_*", "Node3D", true, false)
	if found.is_empty():
		return null
	var r := VehicleRig.new()
	found.sort_custom(func(a: Node, b: Node) -> bool: return str(a.name) < str(b.name))
	for n: Node in found:
		r.wheels.append(n as Node3D)
		r.wheel_r.append(float(_extras(n).get("radius_m", DEFAULT_WHEEL_R)))
	var crews: Array[Node] = model.find_children("Crew_*", "Node3D", true, false)
	crews.sort_custom(func(a: Node, b: Node) -> bool: return str(a.name) < str(b.name))
	for n: Node in crews:
		var nm := str(n.name)
		var crew_i := 0 if nm.begins_with("Crew_A") else 1
		if nm.contains("_Leg_"):
			r.legs.append(n as Node3D)
			r.leg_phase.append(crew_i * PI * 0.5 + (PI if nm.ends_with("_R") else 0.0))
		else:
			r.crews.append(n as Node3D)
			r.crew_rest.append((n as Node3D).position)
			r.crew_phase.append(crew_i * PI * 0.5)
	r.arm = model.find_child("Arm", true, false) as Node3D
	r.barrel = model.find_child("Barrel", true, false) as Node3D
	if r.barrel != null:
		r.barrel_rest = r.barrel.position
		r.recoil_m = float(_extras(r.barrel).get("recoil_m", DEFAULT_RECOIL_M))
	return r


static func _extras(n: Node) -> Dictionary:
	var e: Variant = n.get_meta("extras", {}) if n.has_meta("extras") else {}
	return e if e is Dictionary else {}


## Once per frame from UnitView._process (`move` = the view's smoothed 0..1 movement factor,
## `delta` = the frame's real seconds).
func update(u: Unit, move: float, delta: float = 0.0) -> void:
	var p := u.display_pos()
	if _last_pos != Vector3.INF:
		var d := p - _last_pos
		d.y = 0.0
		if d.length() < MAX_STEP_M:
			distance += d.dot(Vector3(-sin(u.facing), 0.0, -cos(u.facing)))
	_last_pos = p
	for i in wheels.size():
		wheels[i].rotation.x = -distance / maxf(wheel_r[i], 0.05)
	var phase := distance / STRIDE_M * TAU
	for i in legs.size():
		legs[i].rotation.x = LEG_SWING_RAD * move * sin(phase + leg_phase[i])
	for i in crews.size():
		crews[i].position = crew_rest[i] + Vector3(0.0, BOB_M * move * absf(sin(phase + crew_phase[i])), 0.0)
	_update_recoil(u)
	_update_arm(u, delta)


func _update_arm(u: Unit, delta: float) -> void:
	if arm == null:
		return
	var swing := u.swing_progress()
	if swing >= 0.0:
		arm.rotation.x = arm_pose(swing, u.damage_point_ratio())
	else:
		arm.rotation.x = Juice.damp(arm.rotation.x, 0.0, ARM_SETTLE_K, delta)


## The throwing arm's angle (rad, rotation about local X) at swing progress `s` with the damage
## point at `dp`: cock back, whip forward to the release on the damage point, settle to upright.
static func arm_pose(s: float, dp: float) -> float:
	dp = clampf(dp, 0.05, 0.95)
	var cock := dp * 0.7
	if s < cock:
		return ARM_COCK_RAD * smoothstep(0.0, 1.0, s / cock)
	if s < dp:
		var k := (s - cock) / (dp - cock)
		return lerpf(ARM_COCK_RAD, ARM_RELEASE_RAD, k * k)
	var r := clampf((s - dp) / (1.0 - dp), 0.0, 1.0)
	return ARM_RELEASE_RAD * (1.0 - smoothstep(0.0, 1.0, r))


func _update_recoil(u: Unit) -> void:
	if barrel == null:
		return
	var swing := u.swing_progress()
	var dp := u.damage_point_ratio()
	var past := swing >= 0.0 and swing >= dp
	if past and not _was_past_dp:
		var total := (u.damage_point_ticks + u.backswing_ticks) * World.DT
		fired_at = FxClock.fx_now - maxf((swing - dp) * total, 0.0)
	_was_past_dp = past
	var k := recoil_at(FxClock.fx_now - fired_at) if fired_at >= 0.0 else 0.0
	barrel.position = barrel_rest + Vector3(0.0, -0.12, 1.0).normalized() * recoil_m * k
	barrel.rotation.x = RECOIL_KICK_RAD * k


## Recoil amount 0..1, `t` seconds after the shot: slam back, a short hold, then out to battery.
static func recoil_at(t: float) -> float:
	if t < 0.0:
		return 0.0
	if t < RECOIL_IN_S:
		return t / RECOIL_IN_S
	if t < RECOIL_IN_S + RECOIL_HOLD_S:
		return 1.0
	return 1.0 - smoothstep(0.0, 1.0, (t - RECOIL_IN_S - RECOIL_HOLD_S) / RECOIL_OUT_S)
