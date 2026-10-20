class_name ColorGrade
extends RefCounted
## Procedural per-biome colour grading LUTs (research README §2: "a 3D LUT per biome"; art bible
## §1.5: Greenvale day / night LUTs, never black). A 17^3 ImageTexture3D for
## Environment.adjustment_color_correction, rebuilt only when the blend moves noticeably.
## Day: warm highlights, faintly cool shadows, a gentle S-curve. Night: blue mids and shadows with
## a lifted floor (readable, never black). Golden hour: warmer highlights.

const N := 17

static var _cache: Dictionary = {}


## night 0..1, golden 0..1 (quantised so dusk reuses a handful of LUTs).
static func lut(night: float, golden: float) -> ImageTexture3D:
	var qn := roundf(clampf(night, 0.0, 1.0) * 20.0) / 20.0
	var qg := roundf(clampf(golden, 0.0, 1.0) * 10.0) / 10.0
	var key := "%.2f|%.1f" % [qn, qg]
	if _cache.has(key):
		return _cache[key]
	var images: Array[Image] = []
	for b in N:
		var img := Image.create(N, N, false, Image.FORMAT_RGB8)
		for g in N:
			for r in N:
				var c := Color(float(r) / (N - 1), float(g) / (N - 1), float(b) / (N - 1))
				img.set_pixel(r, g, grade(c, qn, qg))
		images.append(img)
	var tex := ImageTexture3D.new()
	tex.create(Image.FORMAT_RGB8, N, N, N, false, images)
	_cache[key] = tex
	return tex


## The grade itself (display-referred colour in, graded colour out).
static func grade(c: Color, night: float, golden: float) -> Color:
	var v := Vector3(c.r, c.g, c.b)
	var l := v.dot(Vector3(0.2126, 0.7152, 0.0722))
	# day: split toning, warm highlights / cool shadows, soft S-curve
	var warm := Vector3(1.035, 1.0, 0.95)
	var cool := Vector3(0.96, 0.99, 1.05)
	var day := v * cool.lerp(warm, smoothstep(0.15, 0.85, l))
	day = day.lerp(_s_curve(day), 0.35)
	# golden hour: extra warmth in the upper mids
	var gold := day * Vector3(1.06, 1.0, 0.88)
	day = day.lerp(gold, golden * smoothstep(0.25, 0.9, l))
	# night: blue-shifted, lifted floor, highlights keep their hue (team colours survive)
	var blue := Vector3(0.80, 0.90, 1.18)
	var nv := v * blue + Vector3(0.012, 0.018, 0.04)
	nv = nv.lerp(v, smoothstep(0.65, 1.0, l) * 0.5)
	var o := day.lerp(nv, night)
	return Color(clampf(o.x, 0.0, 1.0), clampf(o.y, 0.0, 1.0), clampf(o.z, 0.0, 1.0))


static func _s_curve(v: Vector3) -> Vector3:
	return Vector3(_s(v.x), _s(v.y), _s(v.z))


static func _s(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x) * 0.5 + x * 0.5
