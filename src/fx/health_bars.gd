class_name HealthBars
extends MultiMeshInstance3D
## Camera-facing health bars for every living unit in one MultiMesh (billboarding and the fill
## are done in health_bar.gdshader). Per instance custom data: r = hp ratio, g = width (m),
## b = height (m), a = mana ratio; colour: r = damage ghost, g = border flash, b = highlight.
## CMB-29 (juice bible §3.7, SM-05): the value is exact on the event frame; only the ghost lags:
##   - the lost segment turns into a ghost (#FFE3A0) that holds 400 ms after the latest hit,
##     then drains in closed form (exponential at 7/s, never slower than 0.25 bar/s), so it is
##     the same at any refresh rate; heals pull the ghost down with the bar;
##   - every hit latches a 70 ms white border flash (it starts at its peak);
##   - the hovered and selected units' bars always draw, highlighted (SEL-02), even when bars
##     are hidden; dead units' bars vanish on the death frame.
## The ghost runs on the fx clock (it holds while paused). Visual only.

const BAR_SHADER := preload("res://src/fx/health_bar.gdshader")
const FLOATS := 20       ## 12 transform + 4 colour + 4 custom per instance
const BAR_H := 0.16

var world: World
var circles: SelectionCircles
var _buf := PackedFloat32Array()
var _state: Dictionary = {}          ## unit id -> Ghost


class Ghost:
	var last: float = 1.0            ## hp ratio seen last frame
	var g0: float = 1.0              ## ghost ratio when the hold ended
	var r0: float = 1.0              ## hp ratio when the hold ended
	var hit_t: float = -100.0        ## fx time of the latest hit
	var held: float = 1.0            ## ghost ratio during the hold
	var draining: bool = false


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
	multimesh.use_colors = true
	multimesh.use_custom_data = true
	multimesh.mesh = quad
	material_override = mat
	_grow(256)


func setup(w: World) -> void:
	world = w
	circles = get_node_or_null("../SelectionCircles") as SelectionCircles
	var s := w.map.size_world()
	custom_aabb = AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 60, s.y + 10))


## The closed-form ghost drain: the ghost-to-bar gap `d0` at the end of the hold, `t` seconds
## later. dg/dt = −max(rate · gap, min_rate).
static func ghost_gap(d0: float, t: float) -> float:
	var fc := FeelConstants.c()
	var rate := fc.ghost_damp
	var lin := fc.ghost_min_rate
	if d0 <= 0.0 or t <= 0.0:
		return maxf(d0, 0.0)
	var k := lin / rate
	if d0 <= k:
		return maxf(d0 - lin * t, 0.0)
	var t1 := log(d0 / k) / rate
	if t < t1:
		return d0 * exp(-rate * t)
	return maxf(k - lin * (t - t1), 0.0)


## Updates and returns the ghost ratio of a unit whose hp ratio is `ratio` at fx time `now`.
func ghost_for(id: int, ratio: float, now: float) -> float:
	var hold := FeelConstants.c().ghost_hold_ms / 1000.0
	var g: Ghost = _state.get(id)
	if g == null:
		g = Ghost.new()
		g.last = ratio
		g.held = ratio
		g.g0 = ratio
		g.r0 = ratio
		_state[id] = g
	var cur := _ghost_value(g, now, hold)
	if ratio < g.last - 1e-5:
		g.held = maxf(cur, g.last)
		g.hit_t = now
		g.draining = false
	g.last = ratio
	cur = _ghost_value(g, now, hold)
	if cur <= ratio:
		g.held = ratio
		g.g0 = ratio
		g.r0 = ratio
		g.draining = false
		g.hit_t = -100.0
		return ratio
	return cur


func _ghost_value(g: Ghost, now: float, hold: float) -> float:
	if now - g.hit_t < hold:
		return g.held
	if not g.draining:
		g.draining = true
		g.g0 = g.held
		g.r0 = g.last
	return g.r0 + ghost_gap(g.g0 - g.r0, now - g.hit_t - hold)


## Latched 70 ms border flash of a unit at fx time `now` (peak on the hit frame).
func border_flash(id: int, now: float) -> float:
	var g: Ghost = _state.get(id)
	if g == null:
		return 0.0
	return Juice.latched(now - g.hit_t, 1.0, FeelConstants.c().bar_flash_ms / 1000.0)


func _process(_delta: float) -> void:
	if world == null:
		return
	var show_all := Settings.always_show_health_bars or Input.is_key_pressed(KEY_ALT)
	var hovered: Unit = circles.hovered if circles != null else null
	var selected: Array = circles.units if circles != null else []
	var list := world.unit_list
	if list.size() > multimesh.instance_count:
		_grow(list.size() * 2)
	var now := FxClock.fx_now
	var n := 0
	for u in list:
		if not u.alive or u.is_resource or u.hidden:
			continue
		var ratio := clampf(u.hp / maxf(u.max_hp, 0.001), 0.0, 1.0)
		var ghost := ghost_for(u.id, ratio, now)
		var hi := 1.0 if (u == hovered or selected.has(u)) else 0.0
		if not show_all and hi <= 0.0:
			continue
		_write(n, u, ratio, ghost, border_flash(u.id, now), hi)
		n += 1
	if _state.size() > list.size() * 2 + 64:
		_prune()
	multimesh.visible_instance_count = n
	if n > 0:
		multimesh.buffer = _buf


func _prune() -> void:
	for id: int in _state.keys():
		var u := world.get_unit(id)
		if u == null or not u.alive:
			_state.erase(id)


func _write(slot: int, u: Unit, ratio: float, ghost: float, flash: float, hi: float) -> void:
	var p := u.display_pos()
	var top := u.top_height()
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
	_buf[o + 12] = ghost
	_buf[o + 13] = flash
	_buf[o + 14] = hi
	_buf[o + 15] = 1.0
	_buf[o + 16] = ratio
	_buf[o + 17] = width
	_buf[o + 18] = BAR_H
	_buf[o + 19] = u.mana / u.max_mana if u.max_mana > 0.0 else 0.0


func _grow(count: int) -> void:
	multimesh.instance_count = count
	multimesh.visible_instance_count = 0
	_buf.resize(count * FLOATS)
