class_name TimeOfDay
extends RefCounted
## Greenvale time-of-day keys (juice world doc §5.1, art bible §1.5) and their derived channels
## (§5.2). `sample(hour)` interpolates every channel between the bracketing keys (smoothstep), so
## dawn and dusk glide. Visual only: DayNight applies the result to lights, environment and the
## shared material uniforms.

const MOON := Color("#8EA6FF")
## hour, sun colour (null = no sun), sun energy, moon energy, ambient, ambient energy, depth-fog
## colour, saturation, contrast, shadow alpha, cloud strength, glow intensity
const KEYS: Array = [
	[0.0, null, 0.0, 0.38, "#3B4A80", 0.50, "#1E2648", 0.94, 1.04, 0.32, 0.12, 0.85],
	[4.5, null, 0.0, 0.36, "#45508A", 0.53, "#2A3156", 0.96, 1.03, 0.28, 0.12, 0.85],
	[5.333, "#FFA88A", 0.0, 0.30, "#5A5A92", 0.60, "#5A5A86", 0.98, 1.02, 0.10, 0.11, 0.82],
	[5.667, "#FFA88A", 0.24, 0.20, "#6A6496", 0.62, "#8C7FA8", 1.00, 1.02, 0.00, 0.10, 0.80],
	[6.333, "#FFB38A", 0.60, 0.0, "#8E8AB8", 0.56, "#D8A898", 1.06, 1.03, 0.40, 0.20, 0.76],
	[6.5, "#FFB38A", 0.72, 0.0, "#8E8AB8", 0.55, "#E8B7A0", 1.08, 1.03, 0.45, 0.22, 0.75],
	[8.0, "#FFE7C4", 1.00, 0.0, "#9DB3D6", 0.55, "#CFE3F0", 1.08, 1.02, 0.60, 0.30, 0.70],
	[12.0, "#FFF4E2", 1.12, 0.0, "#A6BAD8", 0.58, "#D6E6F2", 1.06, 1.02, 0.62, 0.32, 0.70],
	[16.5, "#FFC98A", 1.05, 0.0, "#9C9CC8", 0.52, "#F2D3A8", 1.12, 1.05, 0.66, 0.30, 0.72],
	[17.667, "#FF9A5C", 0.72, 0.06, "#8A7FB4", 0.54, "#E89A7A", 1.12, 1.05, 0.50, 0.26, 0.75],
	[18.25, "#FF8A5C", 0.24, 0.24, "#4E5A9A", 0.68, "#3A4478", 1.00, 1.03, 0.00, 0.12, 0.80],
	[18.667, null, 0.0, 0.32, "#45528E", 0.66, "#2A3360", 0.96, 1.04, 0.20, 0.12, 0.82],
	[19.5, null, 0.0, 0.38, "#3B4A80", 0.55, "#1E2648", 0.94, 1.04, 0.32, 0.12, 0.85],
]


static func _bump(a: float, b: float, c: float, h: float) -> float:
	return smoothstep(a, b, h) * (1.0 - smoothstep(b, c, h))


## All channels at a game hour (0..24).
static func sample(hour: float) -> Dictionary:
	hour = fposmod(hour, 24.0)
	var n := KEYS.size()
	var i := n - 1
	for k in n:
		if float(KEYS[k][0]) <= hour:
			i = k
	var a: Array = KEYS[i]
	var b: Array = KEYS[(i + 1) % n]
	var h0 := float(a[0])
	var h1 := float(b[0]) if i + 1 < n else float(b[0]) + 24.0
	var hh := hour if hour >= h0 else hour + 24.0
	var t := smoothstep(0.0, 1.0, clampf((hh - h0) / maxf(h1 - h0, 0.001), 0.0, 1.0))
	var sun_a: Color = Color(a[1]) if a[1] != null else Color(b[1]) if b[1] != null else Color("#FF8A5C")
	var sun_b: Color = Color(b[1]) if b[1] != null else sun_a
	var out := {
		"hour": hour,
		"sun_color": sun_a.lerp(sun_b, t),
		"sun_energy": lerpf(a[2], b[2], t),
		"moon_energy": lerpf(a[3], b[3], t),
		"ambient": Color(a[4]).lerp(Color(b[4]), t),
		"ambient_energy": lerpf(a[5], b[5], t),
		"fog_color": Color(a[6]).lerp(Color(b[6]), t),
		"saturation": lerpf(a[7], b[7], t),
		"contrast": lerpf(a[8], b[8], t),
		"shadow_alpha": lerpf(a[9], b[9], t),
		"cloud_strength": lerpf(a[10], b[10], t),
		"glow": lerpf(a[11], b[11], t),
	}
	# derived channels (§5.2)
	var daylight := smoothstep(5.7, 7.0, hour) - smoothstep(17.0, 18.25, hour)
	out["daylight"] = clampf(daylight, 0.0, 1.0)
	out["night"] = clampf(1.0 - smoothstep(5.0, 6.2, hour) + smoothstep(18.0, 19.2, hour), 0.0, 1.0)
	out["golden"] = maxf(_bump(16.4, 17.3, 18.1, hour), 0.6 * _bump(6.0, 6.7, 7.6, hour))
	out["unit_fill"] = 0.65 * (1.0 - out["daylight"])
	out["sun_owns_shadows"] = hour >= 5.667 and hour < 18.25
	return out


## Sun elevation (degrees) over the day: 50-55 deg through the working day (bible §1.5), low and
## long at dawn / dusk (12-20 deg).
static func sun_elevation(hour: float) -> float:
	if hour < 5.5 or hour > 18.5:
		return 12.0
	if hour < 8.0:
		return lerpf(12.0, 52.0, smoothstep(5.6, 8.0, hour))
	if hour > 16.0:
		return lerpf(52.0, 12.0, smoothstep(16.0, 18.4, hour))
	return 52.0 + 3.0 * sin((hour - 8.0) / 8.0 * PI)
