class_name SelectionCircles
extends MultiMeshInstance3D
## Selection, hover and order-pulse rings in one MultiMesh (juice bible §3.6: SEL-01, SEL-02,
## CMB-10, CMB-13; SM-01). Rings are drawn by the shared ground-mark shader (decal substitute)
## from interpolated unit positions, tilted to the terrain. Shape-coded as well as coloured:
## own and allied rings are solid, enemy players' notched, creeps' dashed, hover dashed.
##   - SEL-01 pop-in: scale 0.80 -> 1.06 in 70 ms (out_quad) -> 1.00 by 160 ms (in_out_sine),
##     alpha 0 -> 1 in 60 ms, thickness 1.4x -> 1.0x over 160 ms; a box selection paints in
##     from the drag-start corner (each ring waits 4 ms per 10 px, capped at 140 ms);
##     a deselected ring leaves a quiet ghost (110 ms fade and shrink);
##   - SEL-02 hover: the unit under the cursor (not over the HUD) gets a dashed ring (α 0.45),
##     its rim (UnitView.set_hovered) and its health bar;
##   - CMB-10 pulse: ×1.0 -> 1.22 in 60 ms, back in 120 ms, tinted to the order colour for 180 ms
##     (the order ripple delays each rank 28 ms);
##   - CMB-13 shimmer: the speaking unit's ring is brighter and 30 % wider for its line.
## Every curve is a closed-form function of ui time: identical at any refresh rate.

const OWN := Color(0.25, 1.0, 0.3)
const ALLY := Color(0.3, 0.75, 1.0)
const ENEMY := Color(1.0, 0.22, 0.18)
const NEUTRAL := Color(1.0, 0.9, 0.25)
const FLOATS := GroundMarks.FLOATS
const BAND := 0.16
const SHIMMER_MIN_S := 0.45

var world: World
var units: Array = []
var hovered: Unit = null
var hover_enabled: bool = true
var press_pos := Vector2(-1, -1)       ## drag-start corner of the last left press (screen px)

var _sel_t0: Dictionary = {}           ## unit -> ui time its ring starts popping in
var _ghosts: Array = []                ## [Unit, ui t0]
var _pulses: Dictionary = {}           ## unit -> [ui t0, Color]
var _shimmer: Dictionary = {}          ## unit -> Vector2(ui t0, length)
var _hover_t0: float = -100.0
var _buf := PackedFloat32Array()


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	process_mode = Node.PROCESS_MODE_ALWAYS
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = GroundMarks.SHADER
	mat.render_priority = 3
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	material_override = mat
	_grow(64)
	Events.selection_changed.connect(_on_selection_changed)


func _exit_tree() -> void:
	if Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.disconnect(_on_selection_changed)
	_set_hover(null)


func setup(w: World) -> void:
	world = w
	var s := w.map.size_world()
	custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 40, s.y + 10))


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and (event as InputEventMouseButton).pressed \
			and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		press_pos = (event as InputEventMouseButton).position


func _on_selection_changed(sel: Array) -> void:
	var now := FxClock.ui_now
	var fc := FeelConstants.c()
	var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
	for u: Variant in units:
		if is_instance_valid(u) and not sel.has(u) and (u as Unit).alive:
			_ghosts.append([u, now])
	var next: Dictionary = {}
	for u: Variant in sel:
		if not is_instance_valid(u):
			continue
		if _sel_t0.has(u):
			next[u] = _sel_t0[u]
			continue
		var delay := 0.0
		if sel.size() > 1 and cam != null and press_pos.x >= 0.0:
			var p := (u as Unit).display_pos()
			if not cam.is_position_behind(p):
				var px := cam.unproject_position(p).distance_to(press_pos)
				delay = minf(px / 10.0 * fc.sel_paint_ms_per_10px, fc.sel_paint_cap_ms) / 1000.0
		next[u] = now + delay
	_sel_t0 = next
	units = sel.duplicate()


## Ui time when a unit's ring starts its pop-in (tests, QA traces); -1 when not selected.
func ring_start(u: Unit) -> float:
	return float(_sel_t0.get(u, -1.0))


## CMB-10: a ring pulse starting at ui time `t0` (the ripple delay may put it in the future).
func pulse(u: Unit, t0: float, col: Color) -> void:
	_pulses[u] = [t0, col]


func pulse_start(u: Unit) -> float:
	var p: Variant = _pulses.get(u)
	return float(p[0]) if p != null else -1.0


## CMB-13: the speaker's ring shimmers for its line.
func shimmer(u: Unit, length: float = 0.0) -> void:
	_shimmer[u] = Vector2(FxClock.ui_now, maxf(length, SHIMMER_MIN_S))


func relation_color(u: Unit) -> Color:
	if world == null or u.player_id == world.local_player_id:
		return OWN
	if world.is_enemy(world.local_player_id, u.player_id):
		return ENEMY
	if u.player_id == PlayerState.NEUTRAL_PASSIVE:
		return NEUTRAL
	return ALLY


func relation_shape(u: Unit) -> int:
	if world != null and u.player_id != world.local_player_id and world.is_enemy(world.local_player_id, u.player_id):
		return GroundMarks.Shape.RING_DASHED if u.player_id == PlayerState.NEUTRAL_HOSTILE else GroundMarks.Shape.RING_NOTCHED
	return GroundMarks.Shape.RING


## SEL-01 ring look at `age` (s since its pop-in started): (scale, alpha, thickness factor).
static func pop_look(age: float) -> Vector3:
	if age < 0.0:
		return Vector3(0.8, 0.0, 1.4)
	var fc := FeelConstants.c()
	var s := JuiceCurves.pop_in(age, fc.sel_pop_peak, fc.sel_pop_in_ms / 1000.0, fc.sel_pop_settle_ms / 1000.0, 0.8)
	var a := clampf(age / (fc.sel_alpha_in_ms / 1000.0), 0.0, 1.0)
	var th := lerpf(fc.sel_thick_peak, 1.0, Juice.out_quad(age / (fc.sel_thick_ms / 1000.0)))
	return Vector3(s, a, th)


## CMB-10 pulse at `age`: (scale factor, tint weight).
static func pulse_look(age: float) -> Vector2:
	var fc := FeelConstants.c()
	var up := fc.pulse_up_ms / 1000.0
	var down := fc.pulse_down_ms / 1000.0
	if age < 0.0 or age >= up + down + 0.2:
		return Vector2(1.0, 0.0)
	var s := 1.0
	if age < up:
		s = lerpf(1.0, fc.pulse_scale, Juice.out_quad(age / up))
	elif age < up + down:
		s = lerpf(fc.pulse_scale, 1.0, Juice.in_out_sine((age - up) / down))
	var tint := 1.0 - Juice.window(age, 0.0, fc.pulse_tint_ms / 1000.0)
	return Vector2(s, tint)


func _process(_delta: float) -> void:
	if world == null:
		return
	var now := FxClock.ui_now
	_update_hover(now)
	var need := units.size() + _ghosts.size() + 1
	if need > multimesh.instance_count:
		_grow(need * 2)
	var n := 0
	for u: Variant in units:
		if not is_instance_valid(u) or not (u as Unit).alive:
			continue
		var unit := u as Unit
		var lk := pop_look(now - float(_sel_t0.get(unit, now)))
		var col := relation_color(unit)
		var scale := lk.x
		var th := BAND * lk.z
		var alpha := 0.95 * lk.y
		var pl: Variant = _pulses.get(unit)
		if pl != null:
			var pk := pulse_look(now - float(pl[0]))
			scale *= pk.x
			col = col.lerp(pl[1], pk.y * 0.85)
			if pk.y <= 0.0 and now - float(pl[0]) > 0.4:
				_pulses.erase(unit)
		var sh: Variant = _shimmer.get(unit)
		if sh != null:
			var sv: Vector2 = sh
			var sa := now - sv.x
			if sa >= 0.0 and sa < sv.y:
				var k := 1.0 - Juice.window(sa, sv.y - 0.15, 0.15)
				th *= 1.0 + 0.3 * k
				alpha = maxf(alpha, lk.y * (0.95 + 0.05 * k))
				col = col.lightened(0.25 * k)
			elif sa >= sv.y:
				_shimmer.erase(unit)
		_write(n, unit, scale, col, alpha, relation_shape(unit), th)
		n += 1
	var gi := 0
	var desel := FeelConstants.c().desel_ms / 1000.0
	while gi < _ghosts.size():
		var g: Array = _ghosts[gi]
		var age := now - float(g[1])
		if age >= desel or not is_instance_valid(g[0]) or not (g[0] as Unit).alive or units.has(g[0]):
			_ghosts.remove_at(gi)
			continue
		var k2 := age / desel
		_write(n, g[0], lerpf(1.0, 0.85, Juice.out_quad(k2)), relation_color(g[0]), 0.5 * (1.0 - k2),
			relation_shape(g[0]), BAND * 0.8)
		n += 1
		gi += 1
	if hovered != null and is_instance_valid(hovered) and hovered.alive and not units.has(hovered):
		var ha := clampf((now - _hover_t0) / 0.06, 0.0, 1.0) * FeelConstants.c().hover_alpha
		_write(n, hovered, 1.0, relation_color(hovered), ha, GroundMarks.Shape.RING_DASHED, BAND * 0.85, 14.0)
		n += 1
	multimesh.visible_instance_count = n
	if n > 0:
		multimesh.buffer = _buf


func _write(slot: int, u: Unit, scale: float, c: Color, alpha: float, shape: int, th: float, param: float = 4.0) -> void:
	var p := u.display_pos()
	var r := _ring_radius(u) * scale
	var nrm := _terrain_normal(p, r)
	var z := Vector3(1, 0, 0).cross(nrm).normalized()
	var x := nrm.cross(z).normalized()
	var y := world.map.height_at(p.x, p.z) + 0.06
	var xf := Transform3D(Basis(x * r, nrm * r, z * r), Vector3(p.x, y, p.z))
	var sp := param
	if shape == GroundMarks.Shape.RING_DASHED and param == 4.0:
		sp = 12.0
	GroundMarks._pack(_buf, slot * FLOATS, xf, Color(c, alpha), shape, th, sp, 0.55)


# --- hover (SEL-02) -------------------------------------------------------------------------------

func _update_hover(now: float) -> void:
	if not hover_enabled or not is_inside_tree():
		_set_hover(null)
		return
	var vp := get_viewport()
	var cam := vp.get_camera_3d()
	if cam == null or vp.gui_get_hovered_control() != null:
		_set_hover(null)
		return
	var m := vp.get_mouse_position()
	var size := vp.get_visible_rect().size
	if m.x <= 0 or m.y <= 0 or m.x >= size.x or m.y >= size.y:
		_set_hover(null)
		return
	var u := pick(cam, m)
	if u != hovered:
		_hover_t0 = now
	_set_hover(u)


func _set_hover(u: Unit) -> void:
	if u == hovered:
		return
	if hovered != null and is_instance_valid(hovered) and hovered.view is UnitView:
		(hovered.view as UnitView).set_hovered(false)
	hovered = u
	if hovered != null and hovered.view is UnitView:
		(hovered.view as UnitView).set_hovered(true)


## The unit under a screen position, by the same rule as Selection.pick_unit (closest projected
## centre within its projected radius), fog-honest. Visual only.
func pick(cam: Camera3D, screen_pos: Vector2) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in world.unit_list:
		if not u.alive or u.hidden:
			continue
		var h := u.top_height()
		var p := u.display_pos() + Vector3(0, h * 0.5, 0)
		if cam.is_position_behind(p):
			continue
		var c := cam.unproject_position(p)
		var r := u.radius
		if u.footprint.size != Vector2i.ZERO:
			r = maxf(u.footprint.size.x, u.footprint.size.y) * Grid.CELL * 0.5
		var edge := cam.unproject_position(p + cam.global_basis.x * maxf(r, h * 0.45))
		var rad := maxf(edge.distance_to(c), 12.0)
		var d := c.distance_to(screen_pos)
		if d <= rad and d / rad < best_d:
			best_d = d / rad
			best = u
	if best != null and world.fog != null and best.player_id != world.local_player_id \
			and not world.fog.is_visible(world.local_player_id, best.pos):
		return null
	return best


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
