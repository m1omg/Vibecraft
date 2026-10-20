class_name FxTextures
extends RefCounted
## Procedural placeholder sprites for the fx layers (runs without art, architecture rule 4).
## White shapes with alpha; the particle / mark colour comes from vertex colour. Generated once
## and cached. Named painted frames (Appendix B atlases) replace these when they exist under
## assets/fx/<name>.png.

const SIZE := 64
const ART_DIR := "res://assets/fx/"

static var _cache: Dictionary = {}


static func get_tex(tex_name: String) -> Texture2D:
	if _cache.has(tex_name):
		return _cache[tex_name]
	var t: Texture2D = null
	var art := ART_DIR + tex_name + ".png"
	if ResourceLoader.exists(art):
		t = load(art) as Texture2D
	if t == null:
		t = ImageTexture.create_from_image(_make(tex_name))
	_cache[tex_name] = t
	return t


static func _make(tex_name: String) -> Image:
	var img := Image.create(SIZE, SIZE, false, Image.FORMAT_RGBA8)
	var c := (SIZE - 1) * 0.5
	for y in SIZE:
		for x in SIZE:
			var u := (x - c) / c
			var v := (y - c) / c
			var a := _alpha(tex_name, u, v)
			var shade := 1.0
			if tex_name in ["splinter", "chip", "straw", "drop", "coin"]:
				shade = 0.78 + 0.22 * clampf(0.5 - 0.5 * (u * 0.6 + v * 0.8), 0.0, 1.0)
			img.set_pixel(x, y, Color(shade, shade, shade, clampf(a, 0.0, 1.0)))
	return img


static func _alpha(tex_name: String, u: float, v: float) -> float:
	var d := sqrt(u * u + v * v)
	match tex_name:
		"soft":
			var k := clampf(1.0 - d, 0.0, 1.0)
			return k * k * (3.0 - 2.0 * k)
		"puff":
			# lumpy painted puff: soft disc with a few bumps
			var ang := atan2(v, u)
			var r := 0.78 + 0.12 * sin(ang * 3.0 + 0.7) + 0.06 * sin(ang * 5.0 + 2.1)
			var k2 := clampf((r - d) / 0.35, 0.0, 1.0)
			return k2 * (0.75 + 0.25 * (1.0 - d))
		"spark":
			# vertical streak, bright core, tapered ends
			var w := clampf(1.0 - absf(u) / 0.32, 0.0, 1.0)
			var l := clampf(1.0 - absf(v), 0.0, 1.0)
			return pow(w, 1.5) * pow(l, 0.6)
		"star":
			var arms := maxf(clampf(1.0 - absf(u) * 9.0, 0.0, 1.0) * clampf(1.0 - absf(v), 0.0, 1.0),
				clampf(1.0 - absf(v) * 9.0, 0.0, 1.0) * clampf(1.0 - absf(u), 0.0, 1.0))
			var core := clampf(1.0 - d / 0.45, 0.0, 1.0)
			return maxf(arms, core * core)
		"splinter":
			# long thin wedge with pointed ends
			var half := 0.16 * (1.0 - absf(v))
			return 1.0 if absf(u) <= half and absf(v) < 0.95 else 0.0
		"chip":
			var ang2 := atan2(v, u)
			var r2 := 0.62 + 0.18 * sin(ang2 * 2.0 + 1.0) + 0.1 * sin(ang2 * 5.0)
			return 1.0 if d < r2 else 0.0
		"drop":
			var dy := v + 0.15
			var r3 := 0.55 - 0.25 * clampf(-v, 0.0, 1.0)
			return 1.0 if sqrt(u * u + dy * dy) < r3 else 0.0
		"straw":
			return 1.0 if absf(u + v * 0.15) < 0.07 and absf(v) < 0.92 else 0.0
		"ring":
			var band := clampf(1.0 - absf(d - 0.78) / 0.16, 0.0, 1.0)
			return band * band
		"coin":
			if d > 0.9:
				return 0.0
			return 1.0
	return clampf(1.0 - d, 0.0, 1.0)


## A small gold coin with a dark rim for popup text (bounty / deposits).
static func coin_icon() -> Texture2D:
	if _cache.has("_coin_icon"):
		return _cache["_coin_icon"]
	var art := ART_DIR + "coin_icon.png"
	var t: Texture2D = load(art) as Texture2D if ResourceLoader.exists(art) else null
	if t == null:
		var n := 32
		var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
		var c := (n - 1) * 0.5
		for y in n:
			for x in n:
				var d := Vector2(x - c, y - c).length() / c
				var col := Color(0, 0, 0, 0)
				if d <= 1.0:
					col = Color("#4A2E00")
				if d <= 0.82:
					var hl := clampf(0.5 - (x - c + y - c) / (2.0 * c), 0.0, 1.0)
					col = Color("#E8A92A").lerp(Color("#FFE58A"), hl)
				if d <= 0.5 and d >= 0.38:
					col = Color("#C98A1A")
				img.set_pixel(x, y, col)
		t = ImageTexture.create_from_image(img)
	_cache["_coin_icon"] = t
	return t
