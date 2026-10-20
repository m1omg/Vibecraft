class_name MaterialFlash
extends RefCounted
## The material flash helper (juice bible §4.3): one energy-conserving term everywhere,
##   f = S · (0.3 + 0.7 · rim), rim = (1 − N·V)²; ALBEDO *= 1 − 0.6·f; EMISSION += tint × 0.45·f
## (src/render/unit.gdshader + unit_uniforms.gdshaderinc), so units never bloom (≤ 0.95 linear).
## The flash is written once per event as (t0 on the fx clock, strength, duration, hold) and the
## shader evaluates the latched curve: exact at any refresh rate (R25). Callers never touch the
## uniforms directly:
##   - `hit(view, amount, max_hp)`: #FFF6EC -> #FF5A48 over 80 ms (heroes 100 ms); hits under
##     2 % of max HP flash at 0.5; a re-hit inside the window keeps the max; `reduce_flash`
##     halves the strength;
##   - `death_beat(view)`: white held 60 ms, then out to warm red (CMB-30 death beat);
##   - `structure_hit(view)`: the heat gate (≤ 2.5 Hz, S = min(0.6, heat)), drawn by the
##     structure shader as a value dip, never white.
## `curve(age, strength, duration, hold)` is the CPU mirror of the shader curve (tests).

const PEAK := Color(1.0, 0.965, 0.925)        ## #FFF6EC
const WARM := Color(1.0, 0.353, 0.282)        ## #FF5A48
const STRUCTURE_GATE_S := 0.4

static var reduce_flash: bool = false
static var _heat: Dictionary = {}             ## unit id -> Vector2(last gate open fx time, heat)


static func hit(view: UnitView, amount: float, max_hp: float, is_hero: bool = false) -> void:
	if view == null:
		return
	var s := 1.0
	if max_hp > 0.0 and amount < max_hp * FeelConstants.c().small_hit_frac:
		s = 0.5
	if reduce_flash:
		s *= 0.5
	view.flash(s, WARM, 0.1 if is_hero else 0.08)


static func death_beat(view: UnitView) -> void:
	if view == null:
		return
	var hold := FeelConstants.c().death_beat_ms / 1000.0
	view.flash(0.5 if reduce_flash else 1.0, WARM, hold + 0.08, hold)


## Structures: at most one flash per 400 ms; strength grows with accumulated heat (≤ 0.6).
static func structure_hit(view: UnitView, unit_id: int, amount: float, max_hp: float) -> bool:
	if view == null:
		return false
	var now := FxClock.fx_now
	var st: Vector2 = _heat.get(unit_id, Vector2(-100.0, 0.0))
	var heat := maxf(st.y - (now - st.x) * 0.5, 0.0) + amount / maxf(max_hp, 1.0) * 6.0
	if now - st.x < STRUCTURE_GATE_S:
		_heat[unit_id] = Vector2(st.x, heat)
		return false
	_heat[unit_id] = Vector2(now, heat)
	view.flash(minf(0.6, heat), Color(1.0, 0.69, 0.44), 0.24)
	return true


## CPU mirror of vc_flash_curve(): flash strength at `age`.
static func curve(age: float, strength: float, duration: float, hold: float = 0.0) -> float:
	var h := hold if hold > 0.0 else 0.03
	var dur := maxf(duration, h + 0.01)
	if age < 0.0 or age > dur or strength <= 0.0:
		return 0.0
	var k := clampf((age - h) / (dur - h), 0.0, 1.0)
	return (1.0 - k * (2.0 - k)) * strength
