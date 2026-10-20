class_name Juice
extends RefCounted
## The juice maths core (juice bible §4.2, combat FND-1). Static and allocation-free.
## Rule: motion is a closed-form function of age. Springs are exact for any dt (an impulse or a
## step response sampled at 30, 60 or 144 Hz lands on the same curve); `damp` replaces
## lerp(a, b, k); randomness comes from stateless hashes, never an RNG; periodic patterns stay at
## or below 12 Hz. Nothing here touches sim state.

# --- Penner easings (t in 0..1) ------------------------------------------------------------

static func out_quad(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return t * (2.0 - t)


static func in_quad(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return t * t


static func out_cubic(t: float) -> float:
	t = clampf(t, 0.0, 1.0) - 1.0
	return t * t * t + 1.0


static func in_cubic(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return t * t * t


static func in_out_sine(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return 0.5 - 0.5 * cos(PI * t)


static func in_out_cubic(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return 4.0 * t * t * t if t < 0.5 else 1.0 - pow(-2.0 * t + 2.0, 3.0) * 0.5


static func out_quart(t: float) -> float:
	t = 1.0 - clampf(t, 0.0, 1.0)
	return 1.0 - t * t * t * t


static func out_quint(t: float) -> float:
	t = 1.0 - clampf(t, 0.0, 1.0)
	return 1.0 - t * t * t * t * t


static func out_expo(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return 1.0 if t >= 1.0 else 1.0 - pow(2.0, -10.0 * t)


## Back-out. c1 only from the bible table: 1.1 (TIMBER_SNAP), 1.3 (kingdom snaps, crits),
## 1.6 (marker pin, emblem), 1.70158 (UI stamp family), 2.0 (kingdom recoil, 40-50 ms only).
static func out_back(t: float, c1: float = 1.70158) -> float:
	t = clampf(t, 0.0, 1.0) - 1.0
	var c3 := c1 + 1.0
	return 1.0 + c3 * t * t * t + c1 * t * t


static func in_back(t: float, c1: float = 1.70158) -> float:
	t = clampf(t, 0.0, 1.0)
	return (c1 + 1.0) * t * t * t - c1 * t * t


static func out_bounce(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	const N := 7.5625
	const D := 2.75
	if t < 1.0 / D:
		return N * t * t
	if t < 2.0 / D:
		t -= 1.5 / D
		return N * t * t + 0.75
	if t < 2.5 / D:
		t -= 2.25 / D
		return N * t * t + 0.9375
	t -= 2.625 / D
	return N * t * t + 0.984375


# --- springs (exact for any dt) -------------------------------------------------------------

## Damped spring towards 0: x = offset from rest, v = velocity. Returns (x, v) after dt.
## Under-, critically- and over-damped branches, each the exact solution.
static func spring(x: float, v: float, omega: float, zeta: float, dt: float) -> Vector2:
	if zeta < 0.995:
		var wd := omega * sqrt(1.0 - zeta * zeta)
		var e := exp(-zeta * omega * dt)
		var c := cos(wd * dt)
		var s := sin(wd * dt)
		return Vector2(e * (x * c + (v + zeta * omega * x) / wd * s),
			e * (v * c - (omega * omega * x + zeta * omega * v) / wd * s))
	if zeta <= 1.005:
		var e1 := exp(-omega * dt)
		var b := v + omega * x
		return Vector2((x + b * dt) * e1, (v - omega * b * dt) * e1)
	var q := omega * sqrt(zeta * zeta - 1.0)
	var r1 := -zeta * omega + q
	var r2 := -zeta * omega - q
	var c1 := (v - r2 * x) / (r1 - r2)
	var c2 := x - c1
	var ea := exp(r1 * dt)
	var eb := exp(r2 * dt)
	return Vector2(c1 * ea + c2 * eb, c1 * r1 * ea + c2 * r2 * eb)


## Spring following a target that moves linearly a0 -> a1 during dt (first-order hold): exact
## for ramps, <= 1 % off a 1 kHz reference for targets smooth over a 30 Hz frame. Returns the
## new absolute position and velocity.
static func spring_track(x: float, v: float, a0: float, a1: float, omega: float, zeta: float, dt: float) -> Vector2:
	if dt <= 0.0:
		return Vector2(x, v)
	var u := (a1 - a0) / dt
	var bias := 2.0 * zeta * u / omega
	var r := spring(x - a0 + bias, v - u, omega, zeta, dt)
	return Vector2(r.x + a1 - bias, r.y + u)


## Impulse factor k(zeta): a kick v0 = k * A * omega peaks at offset A (underdamped).
static func peak_factor(zeta: float) -> float:
	zeta = clampf(zeta, 0.0, 0.99)
	return exp(zeta * acos(zeta) / sqrt(1.0 - zeta * zeta))


static func kick_for_peak(amplitude: float, omega: float, zeta: float) -> float:
	return peak_factor(zeta) * amplitude * omega


## Time of the first peak after an impulse (underdamped).
static func peak_time(omega: float, zeta: float) -> float:
	zeta = clampf(zeta, 0.0, 0.99)
	return acos(zeta) / (omega * sqrt(1.0 - zeta * zeta))


## Elastic family: the spring's step response from rest, 0 -> 1 with ringing (FELT_BOB,
## BRONZE_RING). Never on stone, unit bodies or routine HUD (bible §4.2).
static func ring(t: float, omega: float, zeta: float) -> float:
	if t <= 0.0:
		return 0.0
	return 1.0 + spring(-1.0, 0.0, omega, zeta, t).x


# --- the shared anticipation curve -----------------------------------------------------------

## One anticipation curve for every strike, swing, cast and final blow (bible §4.2).
## u: phase 0..1 of the whole action; contact: phase of the sim event (damage point ratio, grid
## point, predicted completion, release tick); hold: visual hit-stop after contact (phase units).
## split / hang: shares of the wind-up spent loading / holding the loaded pose; pull <= 0;
## c1: recovery overshoot. anticipate(contact) == 1.0 exactly, so a pose lands on its tick.
static func anticipate(u: float, contact: float, hold: float, split: float, hang: float, pull: float, c1: float) -> float:
	contact = clampf(contact, 0.001, 1.0)
	if u < contact:
		var w := u / contact
		if w < split:
			return pull * out_quad(w / maxf(split, 0.001))
		if w < split + hang:
			return pull
		return lerpf(pull, 1.0, in_cubic((w - split - hang) / maxf(1.0 - split - hang, 0.001)))
	if u < contact + hold:
		return 1.0
	return 1.0 - out_back((u - contact - hold) / maxf(1.0 - contact - hold, 0.001), c1)


## Clip-time warp for skinned strikes (CMB-16): maps the sim swing progress s (0..1, contact at
## dp) to the clip progress fed to UnitView.strike_clip_time(), whose [0, dp] spans the wind-up
## and [dp, 1] the recovery. The wind-up eases into the loaded pose (0.45 of the clip's wind-up
## by `split`), then snaps (in_quad) so the strike frame is reached exactly at s = dp; the clip
## then holds the contact frame for `hold` (visual hit-stop, the sim is unaffected) and the
## recovery is compressed so the clip still ends when the sim backswing ends.
static func strike_phase(s: float, dp: float, hold: float, split: float) -> float:
	dp = clampf(dp, 0.02, 0.98)
	if s < dp:
		var u := s / dp
		var w := 0.0
		if u < split:
			w = 0.45 * in_out_sine(u / maxf(split, 0.001))
		else:
			w = lerpf(0.45, 1.0, in_quad((u - split) / maxf(1.0 - split, 0.001)))
		return dp * w
	hold = clampf(hold, 0.0, 0.35 * (1.0 - dp))
	if s < dp + hold:
		return dp
	return dp + (1.0 - dp) * clampf((s - dp - hold) / maxf(1.0 - dp - hold, 0.001), 0.0, 1.0)


# --- helpers -------------------------------------------------------------------------------

## Frame-rate independent exponential approach (replaces lerp(a, b, k) per frame).
static func damp(a: float, b: float, rate: float, dt: float) -> float:
	return lerpf(a, b, 1.0 - exp(-rate * dt))


static func damp_v3(a: Vector3, b: Vector3, rate: float, dt: float) -> Vector3:
	return a.lerp(b, 1.0 - exp(-rate * dt))


## Stateless hash in [0, 1): the same (id, seq, salt) always gives the same value. Juice never
## draws from an RNG (it would desync between refresh rates and must never touch World.rng).
static func hash01(id: int, seq: int = 0, salt: int = 0) -> float:
	var h: int = (id * 0x27d4eb2d) ^ (seq * 0x165667b1) ^ (salt * 0x61C88647) ^ 0x5bd1e995
	h = (h ^ (h >> 15)) * 0x2c1b3c6d
	h = (h ^ (h >> 12)) * 0x297a2d39
	h = h ^ (h >> 15)
	return float(h & 0xFFFFFF) / 16777216.0


## Signed hash in [-1, 1).
static func hash11(id: int, seq: int = 0, salt: int = 0) -> float:
	return hash01(id, seq, salt) * 2.0 - 1.0


## Smooth value noise in [-1, 1] at `hz` (<= 12 Hz for anything periodic, bible rule 3).
static func vnoise(id: int, t: float, hz: float) -> float:
	var x := t * minf(hz, 12.0)
	var i := floori(x)
	var f := x - i
	f = f * f * (3.0 - 2.0 * f)
	return lerpf(hash11(id, i, 77), hash11(id, i + 1, 77), f)


## Crossing test: true when the value passed `thr` going up between two samples.
static func crossed(prev: float, cur: float, thr: float) -> bool:
	return prev < thr and cur >= thr


## Back-dated accumulator: returns (remaining accumulator, whole intervals elapsed), so periodic
## spawns happen the same number of times at any frame rate.
static func accumulate(acc: float, dt: float, interval: float) -> Vector2:
	acc += dt
	var n := floorf(acc / maxf(interval, 0.0001))
	return Vector2(acc - n * interval, n)


## Latched peak: the first rendered frame shows the peak (age 0 -> peak), then out_quad to 0
## over `decay` seconds. Anything shorter than ~60 ms must start at its peak (bible rule 3).
static func latched(age: float, peak: float, decay: float) -> float:
	if age < 0.0 or age >= decay:
		return 0.0
	return peak * (1.0 - out_quad(age / maxf(decay, 0.0001)))


## Wraps an angle difference to [-PI, PI].
static func wrap_angle(a: float) -> float:
	return wrapf(a, -PI, PI)


## 0..1 progress of `age` through a window [start, start + length], clamped.
static func window(age: float, start: float, length: float) -> float:
	return clampf((age - start) / maxf(length, 0.0001), 0.0, 1.0)
