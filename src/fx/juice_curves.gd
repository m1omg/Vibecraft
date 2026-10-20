class_name JuiceCurves
extends RefCounted
## Named material and UI motion tokens built on Juice (juice bible §4.2, economy §2.4). Every
## token is a closed-form function of age in seconds (or a normalised phase), so a call site
## names a material, never a raw easing. Every periodic token declares its frequency and stays
## at or below 12 Hz (FREQ_HZ; tests/unit/test_juice.gd asserts it).

## Periodic tokens and their frequencies (Hz).
const FREQ_HZ: Dictionary = {
	"felt_bob": 2.2,          ## ring(t, 14, 0.35): ω_d / 2π
	"bronze_ring": 4.4,       ## ring(t, 28, 0.12)
	"shake": 11.1,            ## 90 ms period
	"tremble": 12.0,          ## knockback tremble noise
	"pole_wobble": 2.8,       ## rally pole, ω 18 rad/s
}

# --- world motion ----------------------------------------------------------------------------

## Dry wooden settle: ≈ 4.5 % overshoot (out_back 1.1). u = 0..1.
static func timber_snap(u: float) -> float:
	return Juice.out_back(u, 1.1)


## Felt bob: two visible bounces, settled in ≈ 0.8 s.
static func felt_bob(t: float) -> float:
	return Juice.ring(t, 14.0, 0.35)


## Stone thud: no overshoot at all.
static func stone_thud(u: float) -> float:
	return Juice.out_quad(u)


## Bronze ring: ≥ 3 oscillations, started with its sound.
static func bronze_ring(t: float) -> float:
	return Juice.ring(t, 28.0, 0.12)


## Damped pole wobble (rally flag stab, CMB / BLD-13): angle factor in [-1, 1], 9° at 1.
static func pole_wobble(t: float) -> float:
	if t < 0.0:
		return 0.0
	return Juice.spring(1.0, 0.0, 18.0, 0.25, t).x


# --- UI and glyph tokens -----------------------------------------------------------------------

## Stamp pop-in (SEL-01 ring pop, popups): 0.80 -> peak in `in_s` (out_quad), then -> 1.0 in
## `settle_s` (in_out_sine). Returns the scale.
static func pop_in(age: float, peak: float = 1.06, in_s: float = 0.07, settle_s: float = 0.09, from: float = 0.8) -> float:
	if age <= 0.0:
		return from
	if age < in_s:
		return lerpf(from, peak, Juice.out_quad(age / in_s))
	return lerpf(peak, 1.0, Juice.in_out_sine((age - in_s) / maxf(settle_s, 0.001)))


## Punch: a 1 -> 1 + amp bump over `len_s` (merge bumps, counter bumps).
static func punch(age: float, amp: float = 0.12, len_s: float = 0.06) -> float:
	if age < 0.0 or age >= len_s:
		return 1.0
	return 1.0 + amp * sin(PI * age / len_s)


## Denial shake: 6 px, 90 ms period, 280 ms, decaying. Returns the offset in px.
static func shake(age: float, amp_px: float = 6.0, period_s: float = 0.09, len_s: float = 0.28) -> float:
	if age < 0.0 or age >= len_s:
		return 0.0
	return amp_px * (1.0 - age / len_s) * sin(TAU * age / period_s)


## Rise and fade (popup text): returns (rise 0..1, alpha). The fade covers the last `fade_frac`.
static func rise_fade(age: float, life: float, fade_frac: float = 0.4) -> Vector2:
	if age < 0.0:
		return Vector2(0.0, 0.0)
	var u := clampf(age / maxf(life, 0.001), 0.0, 1.0)
	var f := Juice.window(u, 1.0 - fade_frac, fade_frac)
	return Vector2(Juice.out_cubic(u), 1.0 - f * f * (3.0 - 2.0 * f))


## Flare: latched peak decaying over `len_s` (impact stars, border flashes).
static func flare(age: float, len_s: float = 0.07) -> float:
	return Juice.latched(age, 1.0, len_s)


## Crit pop (bible §4.5): 0 -> 1.45 in 90 ms (out_back), 1.0 by 220 ms.
static func crit_pop(age: float) -> float:
	if age <= 0.0:
		return 0.0
	if age < 0.09:
		return 1.45 * Juice.out_back(age / 0.09, 1.3)
	return lerpf(1.45, 1.0, Juice.in_out_sine((age - 0.09) / 0.13))
