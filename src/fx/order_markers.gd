class_name OrderMarkers
extends Node3D
## Order feedback for the local player's commands (juice bible §3.6, SM-01): CMB-08 markers,
## CMB-09 target flash, CMB-10 order ripple, CMB-11 shift waypoint lines and the rally flag.
## Driven by `Events.command_issued` (drained by Vfx on the input frame) and by read-only looks
## at the selection's orders; never writes sim state. Every curve is closed form on the ui
## clock, so marks are identical at any refresh rate and keep running while paused.
##   - move: three ripple rings (r 0.25 -> R = clamp(1 + 0.25·√n, 1, 2.2) m, 420 ms out_cubic,
##     70 ms apart, #57E36A with a dark outline) and a chunky pin that drops from +0.9 m to
##     +0.15 m (160 ms out_back 1.6), kicks 3 dust puffs, holds until 450 ms, then shrinks
##     (180 ms in_back);
##   - attack-move: four red chevrons converging; patrol: two arrowheads chasing round a ring;
##     attack ground: a crosshair; a targeted unit (attack, follow, gather): three blinks of a
##     ring under it (notched when hostile) and a rim pulse on the unit;
##   - spam: a re-click within 250 ms and 1.5 m becomes a 200 ms tap (one small ring); at most
##     `marker_pool` (8) live markers, the oldest yields;
##   - ripple (CMB-10): the unit nearest the click pulses its ring ×1.22 and nods on the input
##     frame, the others follow 28 ms per rank (cap 308 ms); a unit re-nods ≤ once per 450 ms;
##   - waypoint lines: while Shift is held, or for 1.4 s after a queued order, dashed lines run
##     from each selected unit through its queued order goals;
##   - rally flag: a pole and pennant at the rally point of each selected own structure, with a
##     damped stab wobble when the point is set.

const MOVE_COL := Color("#57E36A")
const ATTACK_COL := Color("#FF5A48")
const NEUTRAL_COL := Color("#F2D04A")
const PATROL_COL := Color("#7FD8FF")
const PIN_CAP := 8
const PIN_SCALE := 1.4          ## the 0.35 m pin reads at the default zoom (the bible's 0.35 m at 1.0)
const FLAG_CAP := 12
const ORDER_TYPES_WITH_GOAL: Array[String] = ["move", "smart", "attack_move", "patrol", "attack",
	"follow", "gather", "attack_ground", "rally"]

var world: World
var vfx: Vfx
var markers: int = 0            ## markers spawned (taps included)
var taps: int = 0
var nods: int = 0
var pulses: int = 0
var lines_drawn: int = 0

var _live: Array[Vector4] = []  ## (x, z, ui t0, life) of live markers (pool of 8)
var _last_click := Vector4(0, 0, -100, 0)
var _pins: MultiMeshInstance3D
var _pin_t0 := PackedFloat64Array()
var _pin_pos := PackedVector3Array()
var _pin_col := PackedColorArray()
var _pin_dust := PackedByteArray()
var _pin_next: int = 0
var _pin_buf := PackedFloat32Array()
var _flags: MultiMeshInstance3D
var _flag_buf := PackedFloat32Array()
var _rally_t0: Dictionary = {}  ## structure id -> ui time the rally point was set
var _targets: Array = []        ## [Unit, ui t0]
var _waypoint_until: float = -100.0


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	process_mode = Node.PROCESS_MODE_ALWAYS
	_pins = _make_mm("Pins", _pin_mesh(), PIN_CAP, true)
	_pin_t0.resize(PIN_CAP)
	_pin_pos.resize(PIN_CAP)
	_pin_col.resize(PIN_CAP)
	_pin_dust.resize(PIN_CAP)
	for i in PIN_CAP:
		_pin_t0[i] = -100.0
	_pin_buf.resize(PIN_CAP * 16)
	_flags = _make_mm("RallyFlags", _flag_mesh(), FLAG_CAP, false)
	_flag_buf.resize(FLAG_CAP * 12)


func _make_mm(n: String, mesh: Mesh, cap: int, colors: bool) -> MultiMeshInstance3D:
	var mmi := MultiMeshInstance3D.new()
	mmi.name = n
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	mmi.multimesh = MultiMesh.new()
	mmi.multimesh.transform_format = MultiMesh.TRANSFORM_3D
	mmi.multimesh.use_colors = colors
	mmi.multimesh.mesh = mesh
	mmi.multimesh.instance_count = cap
	mmi.multimesh.visible_instance_count = 0
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED if colors else BaseMaterial3D.SHADING_MODE_PER_PIXEL
	m.vertex_color_use_as_albedo = true
	m.disable_receive_shadows = colors
	mmi.material_override = m
	add_child(mmi)
	return mmi


func setup(w: World, v: Vfx) -> void:
	world = w
	vfx = v
	var s := w.map.size_world()
	var aabb := AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 50, s.y + 10))
	for mmi: MultiMeshInstance3D in [_pins, _flags]:
		mmi.multimesh.custom_aabb = aabb
		mmi.custom_aabb = aabb


func live_markers(now: float = FxClock.ui_now) -> int:
	var n := 0
	for m in _live:
		if now - m.z < m.w:
			n += 1
	return n


# --- commands (drained on the input frame) -----------------------------------------------------

func on_command(cmd: Dictionary) -> void:
	if world == null:
		return
	var t := FxClock.ui_now
	var kind := str(cmd.get("type", ""))
	var units := _units(cmd)
	var target := world.get_unit(int(cmd.get("target", 0))) if cmd.has("target") else null
	var has_pos := cmd.get("pos") is Vector3
	var pos: Vector3 = cmd["pos"] if has_pos else (target.pos if target != null else Vector3.INF)
	var structures_only := not units.is_empty()
	for u: Unit in units:
		if u.is_mobile():
			structures_only = false
	if bool(cmd.get("queue", false)):
		_waypoint_until = t + FeelConstants.c().waypoint_show_ms / 1000.0
	if kind == "rally" or (structures_only and kind == "smart" and pos != Vector3.INF):
		for u: Unit in units:
			_rally_t0[u.id] = t
		if pos != Vector3.INF:
			_ripple(pos, 1, NEUTRAL_COL, t, true)
		vfx.trace("CMB-08.rally", -1)
		return
	if not ORDER_TYPES_WITH_GOAL.has(kind):
		# stop / hold / instant orders: the selection still nods (the order was heard)
		_wave(units, _centre(units), t, Color(0.9, 0.9, 0.8))
		return
	var col := MOVE_COL
	if target != null and target.alive:
		var hostile := world.is_enemy(world.local_player_id, target.player_id)
		col = ATTACK_COL if hostile else (MOVE_COL if target.player_id == world.local_player_id else NEUTRAL_COL)
		target_flash(target, hostile, t)
		_wave(units, target.display_pos(), t, col)
		vfx.trace("CMB-09.target", target.id)
		return
	if pos == Vector3.INF:
		return
	match kind:
		"attack_move":
			col = ATTACK_COL
			_spawn(GroundMarks.Kind.CHEVRON_IN, pos, 1.25, 0.0, col, 0.55, t)
		"patrol":
			col = PATROL_COL
			_spawn(GroundMarks.Kind.PATROL, pos, 1.1, 0.0, col, 0.75, t)
		"attack", "attack_ground":
			col = ATTACK_COL
			_spawn(GroundMarks.Kind.CROSSHAIR_IN, pos, 1.0, 0.0, col, 0.6, t)
		_:
			_ripple(pos, maxi(units.size(), 1), col, t, false)
	_wave(units, pos, t, col)
	vfx.trace("CMB-08.marker", -1)


func _units(cmd: Dictionary) -> Array:
	var out: Array = []
	for id: Variant in cmd.get("units", []):
		var u := world.get_unit(int(id))
		if u != null and u.alive and u.player_id == world.local_player_id:
			out.append(u)
	return out


static func _centre(units: Array) -> Vector3:
	if units.is_empty():
		return Vector3.ZERO
	var c := Vector3.ZERO
	for u: Unit in units:
		c += u.pos
	return c / units.size()


## Move marker: three ripple rings + the pin, or a tap when re-clicked within 250 ms and 1.5 m.
func _ripple(pos: Vector3, n: int, col: Color, t: float, small: bool) -> void:
	var fc := FeelConstants.c()
	var tap := t - _last_click.z <= fc.tap_window_ms / 1000.0 \
		and Vector2(pos.x - _last_click.x, pos.z - _last_click.y).length() <= fc.tap_radius_m
	_last_click = Vector4(pos.x, pos.z, t, 0.0)
	var big := clampf(1.0 + 0.25 * sqrt(float(n)), 1.0, 2.2)
	if tap or small:
		_reserve(pos, t, 0.2)
		vfx.marks.add(GroundMarks.Kind.RIPPLE, pos, 0.25, big * 0.6, col, 0.2)
		taps += 1
		markers += 1
		return
	_reserve(pos, t, fc.ripple_ms / 1000.0 + 2.0 * fc.ripple_stagger_ms / 1000.0)
	for k in 3:
		vfx.marks.add(GroundMarks.Kind.RIPPLE, pos, 0.25, big, col, fc.ripple_ms / 1000.0,
			k * fc.ripple_stagger_ms / 1000.0)
	_add_pin(pos, col, t)
	markers += 1


func _spawn(kind: int, pos: Vector3, r: float, r1: float, col: Color, life: float, t: float) -> void:
	_reserve(pos, t, life)
	vfx.marks.add(kind, pos, r, r1, col, life)
	_last_click = Vector4(pos.x, pos.z, t, 0.0)
	markers += 1


## Keeps at most `marker_pool` live markers: the oldest is cut short.
func _reserve(pos: Vector3, t: float, life: float) -> void:
	var cap := FeelConstants.c().marker_pool
	var i := 0
	while i < _live.size():
		if t - _live[i].z >= _live[i].w:
			_live.remove_at(i)
		else:
			i += 1
	while _live.size() >= cap:
		var old := _live[0]
		vfx.marks.expire_near(Vector3(old.x, 0.0, old.y), old.z)
		_live.remove_at(0)
	_live.append(Vector4(pos.x, pos.z, t, life))


## CMB-10 order ripple: rank by distance to the order point; rank r starts r × 28 ms after the
## input frame (cap 308 ms): ring pulse ×1.22 tinted to the order colour, and a nod.
func _wave(units: Array, at: Vector3, t: float, col: Color) -> void:
	if units.is_empty():
		return
	var fc := FeelConstants.c()
	var ranked := units.duplicate()
	ranked.sort_custom(func(a: Unit, b: Unit) -> bool:
		var da := Vector2(a.pos.x - at.x, a.pos.z - at.z).length_squared()
		var db := Vector2(b.pos.x - at.x, b.pos.z - at.z).length_squared()
		return da < db if da != db else a.id < b.id)
	for r in ranked.size():
		var u: Unit = ranked[r]
		var delay := minf(r * fc.ripple_step_ms, fc.ripple_cap_ms) / 1000.0
		if vfx.circles != null:
			vfx.circles.pulse(u, t + delay, col)
			pulses += 1
		var v := u.view as UnitView
		if v != null and v.juice != null and v.juice.nod(t + delay):
			nods += 1


## CMB-09: three blinks under the target (notched when hostile) and a rim pulse on it.
func target_flash(target: Unit, hostile: bool, t: float = FxClock.ui_now) -> void:
	var r := _ring_radius(target)
	vfx.marks.add(GroundMarks.Kind.TARGET_BLINK, target.display_pos(), r, r,
		ATTACK_COL if hostile else NEUTRAL_COL, 0.46, 0.0, 4.0 if hostile else 0.0, target)
	for e: Array in _targets:
		if e[0] == target:
			e[1] = t
			return
	_targets.append([target, t])


static func _ring_radius(u: Unit) -> float:
	if u.footprint.size != Vector2i.ZERO:
		return maxf(u.footprint.size.x, u.footprint.size.y) * Grid.CELL * 0.62
	return u.radius * 1.35 + 0.1


# --- per frame ----------------------------------------------------------------------------------

func _process(_delta: float) -> void:
	if world == null or not is_instance_valid(world):
		return
	var t := FxClock.ui_now
	_update_pins(t)
	_update_targets(t)
	_update_waypoints(t)
	_update_flags(t)


func _add_pin(pos: Vector3, col: Color, t: float) -> void:
	var i := _pin_next
	_pin_next = (_pin_next + 1) % PIN_CAP
	_pin_t0[i] = t
	_pin_pos[i] = Vector3(pos.x, world.map.height_at(pos.x, pos.z), pos.z)
	_pin_col[i] = col
	_pin_dust[i] = 0


## Pin height and scale at `age` (SM-01): drop +0.9 -> +0.15 m in 160 ms (out_back 1.6), hold
## to 450 ms, shrink over 180 ms (in_back). Returns (height, scale); scale <= 0 when gone.
static func pin_look(age: float) -> Vector2:
	var fc := FeelConstants.c()
	var drop := fc.pin_drop_ms / 1000.0
	var hold := fc.pin_hold_ms / 1000.0
	var shrink := fc.pin_shrink_ms / 1000.0
	if age < 0.0 or age >= hold + shrink:
		return Vector2(0.0, 0.0)
	var h := lerpf(0.9, 0.15, Juice.out_back(age / drop, 1.6)) if age < drop else 0.15
	var s := 1.0
	if age >= hold:
		s = 1.0 - Juice.in_back((age - hold) / shrink, 1.70158)
	return Vector2(h, maxf(s, 0.0))


func _update_pins(t: float) -> void:
	var n := 0
	var drop := FeelConstants.c().pin_drop_ms / 1000.0
	for i in PIN_CAP:
		var age := t - _pin_t0[i]
		var lk := pin_look(age)
		if lk.y <= 0.001:
			continue
		var p := _pin_pos[i]
		if _pin_dust[i] == 0 and age >= drop:
			_pin_dust[i] = 1
			if vfx != null and vfx.particles != null:
				vfx.particles.burst("dust_step", p + Vector3(0, 0.08, 0), Vector3.UP, 1.0, 1)
		var spin := Basis(Vector3.UP, 0.6 * age)
		var b := spin.scaled(Vector3.ONE * lk.y * PIN_SCALE)
		var o := n * 16
		_pin_buf[o + 0] = b.x.x
		_pin_buf[o + 1] = b.y.x
		_pin_buf[o + 2] = b.z.x
		_pin_buf[o + 3] = p.x
		_pin_buf[o + 4] = b.x.y
		_pin_buf[o + 5] = b.y.y
		_pin_buf[o + 6] = b.z.y
		_pin_buf[o + 7] = p.y + lk.x
		_pin_buf[o + 8] = b.x.z
		_pin_buf[o + 9] = b.y.z
		_pin_buf[o + 10] = b.z.z
		_pin_buf[o + 11] = p.z
		var c := _pin_col[i]
		_pin_buf[o + 12] = c.r
		_pin_buf[o + 13] = c.g
		_pin_buf[o + 14] = c.b
		_pin_buf[o + 15] = 1.0
		n += 1
	_pins.multimesh.visible_instance_count = n
	if n > 0:
		_pins.multimesh.buffer = _pin_buf


func live_pins(t: float = FxClock.ui_now) -> int:
	var n := 0
	for i in PIN_CAP:
		if pin_look(t - _pin_t0[i]).y > 0.001:
			n += 1
	return n


## Target rim pulse follows the blink pattern (0.5 on, 0 off), then clears.
func _update_targets(t: float) -> void:
	var i := 0
	while i < _targets.size():
		var e: Array = _targets[i]
		var u: Variant = e[0]
		if not is_instance_valid(u):
			_targets.remove_at(i)
			continue
		var age := t - float(e[1])
		var v := (u as Unit).view as UnitView
		if age > 0.5:
			if v != null:
				v.set_rim_pulse(0.0)
			_targets.remove_at(i)
			continue
		if v != null:
			v.set_rim_pulse(0.5 * GroundMarks.target_blink_alpha(age))
		i += 1


## CMB-11: dashed lines through the queued order goals of the selected own units.
func _update_waypoints(t: float) -> void:
	var show := t < _waypoint_until or Input.is_key_pressed(KEY_SHIFT)
	if not show or vfx == null or vfx.marks == null:
		return
	var drawn := 0
	for u: Variant in vfx.selected:
		if drawn >= 24 or not is_instance_valid(u):
			continue
		var unit := u as Unit
		if not unit.alive or unit.player_id != world.local_player_id or not unit.is_mobile():
			continue
		var pts := PackedVector3Array([unit.display_pos()])
		var list: Array = []
		if unit.current != null:
			list.append(unit.current)
		list.append_array(unit.orders)
		for o: Order in list:
			var g := _goal(o)
			if g != Vector3.INF:
				pts.append(g)
		if pts.size() < 3 and t >= _waypoint_until:
			continue
		for k in range(1, pts.size()):
			_dash(pts[k - 1], pts[k], MOVE_COL if k == 1 else Color(MOVE_COL, 0.8))
		drawn += 1


func _goal(o: Order) -> Vector3:
	if o.target_id != 0:
		var tu := world.get_unit(o.target_id)
		return tu.display_pos() if tu != null else Vector3.INF
	match o.type:
		Order.Type.MOVE, Order.Type.ATTACK_MOVE, Order.Type.PATROL, Order.Type.SMART, \
				Order.Type.ATTACK_GROUND, Order.Type.BUILD, Order.Type.CAST:
			return o.target_pos
	return Vector3.INF


func _dash(a: Vector3, b: Vector3, col: Color) -> void:
	var d := Vector3(b.x - a.x, 0.0, b.z - a.z)
	var length := d.length()
	if length < 0.3:
		return
	var dir := d / length
	var mid := (a + b) * 0.5
	var y := world.map.height_at(mid.x, mid.z) + GroundMarks.LIFT + 0.01
	var side := Vector3(-dir.z, 0.0, dir.x)
	var xf := Transform3D(Basis(side * 0.07, Vector3.UP, dir * (length * 0.5)), Vector3(mid.x, y, mid.z))
	vfx.marks.add_frame(xf, GroundMarks.Shape.DASH_LINE, Color(col, col.a * 0.85), 0.5,
		maxf(round(length / 0.55), 1.0), 0.5)
	lines_drawn += 1


## Rally flags of the selected own structures; a fresh rally point wobbles (pole_wobble).
func _update_flags(t: float) -> void:
	var n := 0
	if vfx != null:
		for u: Variant in vfx.selected:
			if n >= FLAG_CAP or not is_instance_valid(u):
				continue
			var s := u as Unit
			if not s.alive or s.player_id != world.local_player_id or not s.is_building:
				continue
			var rp := s.rally_pos
			if s.rally_id != 0:
				var ru := world.get_unit(s.rally_id)
				rp = ru.display_pos() if ru != null else Vector3.INF
			if rp == Vector3.INF:
				continue
			var age := t - float(_rally_t0.get(s.id, -100.0))
			var wob := deg_to_rad(FeelConstants.c().rally_wobble_deg) * JuiceCurves.pole_wobble(age)
			var drop := 1.0 - Juice.out_back(clampf(age / 0.16, 0.0, 1.0), 1.6) if age < 0.16 else 0.0
			var b := Basis(Vector3.RIGHT, wob)
			var y := world.map.height_at(rp.x, rp.z) + drop * 0.8
			var o := n * 12
			_flag_buf[o + 0] = b.x.x
			_flag_buf[o + 1] = b.y.x
			_flag_buf[o + 2] = b.z.x
			_flag_buf[o + 3] = rp.x
			_flag_buf[o + 4] = b.x.y
			_flag_buf[o + 5] = b.y.y
			_flag_buf[o + 6] = b.z.y
			_flag_buf[o + 7] = y
			_flag_buf[o + 8] = b.x.z
			_flag_buf[o + 9] = b.y.z
			_flag_buf[o + 10] = b.z.z
			_flag_buf[o + 11] = rp.z
			n += 1
	_flags.multimesh.visible_instance_count = n
	if n > 0:
		_flags.multimesh.buffer = _flag_buf


func live_flags() -> int:
	return _flags.multimesh.visible_instance_count


# --- placeholder meshes (runs without art) -------------------------------------------------------

## A 0.35 m chunky chevron pin pointing down (vertex colour white: the instance colour tints it),
## with a dark rim so it reads on bright grass.
static func _pin_mesh() -> Mesh:
	var cone := CylinderMesh.new()
	cone.top_radius = 0.2
	cone.bottom_radius = 0.0
	cone.height = 0.35
	cone.radial_segments = 4
	cone.rings = 1
	var cap := CylinderMesh.new()
	cap.top_radius = 0.23
	cap.bottom_radius = 0.23
	cap.height = 0.05
	cap.radial_segments = 4
	cap.rings = 1
	return ProcMesh.merge([
		{"mesh": cone, "xform": ProcMesh.at(Vector3(0, 0.175, 0)), "color": Color(1, 1, 1)},
		{"mesh": cap, "xform": ProcMesh.at(Vector3(0, 0.37, 0)), "color": Color(0.35, 0.35, 0.35)},
	])


## A rally flag: pole, finial and a team-neutral pennant (2.0 m tall, pivot at the foot).
static func _flag_mesh() -> Mesh:
	var pole := CylinderMesh.new()
	pole.top_radius = 0.03
	pole.bottom_radius = 0.04
	pole.height = 2.0
	pole.radial_segments = 6
	pole.rings = 1
	var cloth := BoxMesh.new()
	cloth.size = Vector3(0.7, 0.42, 0.03)
	var knob := SphereMesh.new()
	knob.radius = 0.06
	knob.height = 0.12
	knob.radial_segments = 6
	knob.rings = 3
	return ProcMesh.merge([
		{"mesh": pole, "xform": ProcMesh.at(Vector3(0, 1.0, 0)), "color": Color(0.42, 0.3, 0.18)},
		{"mesh": cloth, "xform": ProcMesh.at(Vector3(0.37, 1.7, 0)), "color": Color("#E8C547")},
		{"mesh": knob, "xform": ProcMesh.at(Vector3(0, 2.04, 0)), "color": Color("#D9B55A")},
	])
