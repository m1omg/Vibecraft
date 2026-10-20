class_name MenuBackdrop
extends Control
## Main-menu backdrop drawn procedurally (no asset): a dusk sky, a low sun, layered chalk-downland
## ridges with hedge lines, and two distant hall silhouettes with banners in the slice colours
## (kingdom Emerald, clans Royal Blue). The clouds and banners drift slowly with real time.
## Visual only.

const SKY_TOP := Color("#1d2440")
const SKY_MID := Color("#6a4f6e")
const SKY_LOW := Color("#e8a35c")
const SUN := Color("#ffd48a")
const RIDGES: Array[Color] = [Color("#6d6a78"), Color("#4c5a52"), Color("#344536"), Color("#223024"),
	Color("#141d16")]
const KINGDOM := Color("#2EAE3A")
const CLANS := Color("#285DE6")

var _t: float = 0.0
var _sky_tex: GradientTexture2D


func _ready() -> void:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.62, 0.9, 1.0])
	g.colors = PackedColorArray([SKY_TOP, SKY_MID, SKY_LOW, SKY_LOW])
	_sky_tex = GradientTexture2D.new()
	_sky_tex.gradient = g
	_sky_tex.width = 4
	_sky_tex.height = 256
	_sky_tex.fill_from = Vector2(0, 0)
	_sky_tex.fill_to = Vector2(0, 1)


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	var s := size
	if s.x <= 0.0 or s.y <= 0.0:
		return
	_sky(s)
	draw_circle(Vector2(s.x * 0.68, s.y * 0.56), s.y * 0.07, SUN)
	draw_circle(Vector2(s.x * 0.68, s.y * 0.56), s.y * 0.1, Color(SUN, 0.18))
	for i in 5:
		var y := s.y * (0.6 + i * 0.075)
		_ridge(s, y, 0.035 * s.y / (1.0 + i * 0.3), 1.3 + i * 0.7, float(i) * 1.7, RIDGES[i])
		if i == 2:
			_hall(Vector2(s.x * 0.2, _ridge_y(s, s.x * 0.2, y, 0.035 * s.y / 1.6, 2.7, 3.4)), s.y * 0.05, KINGDOM)
			_hall(Vector2(s.x * 0.83, _ridge_y(s, s.x * 0.83, y, 0.035 * s.y / 1.6, 2.7, 3.4)), s.y * 0.045, CLANS, true)
	for k in 4:
		var cx := fposmod(s.x * (0.15 + k * 0.27) + _t * (6.0 + k * 2.0), s.x * 1.2) - s.x * 0.1
		var cy := s.y * (0.16 + 0.07 * (k % 2))
		for j in 4:
			draw_circle(Vector2(cx + j * s.y * 0.035, cy + sin(j * 1.7) * 6.0), s.y * (0.025 + 0.008 * (j % 2)),
				Color(1.0, 0.85, 0.75, 0.10))


func _sky(s: Vector2) -> void:
	draw_texture_rect(_sky_tex, Rect2(0.0, 0.0, s.x, s.y * 0.72), false)
	draw_rect(Rect2(0.0, s.y * 0.72 - 1.0, s.x, s.y * 0.28 + 1.0), SKY_LOW)


func _ridge_y(s: Vector2, x: float, base: float, amp: float, freq: float, phase: float) -> float:
	var u := x / s.x
	return base - amp * (sin(u * TAU * freq * 0.5 + phase) + 0.45 * sin(u * TAU * freq * 1.3 + phase * 2.1))


func _ridge(s: Vector2, base: float, amp: float, freq: float, phase: float, col: Color) -> void:
	var pts := PackedVector2Array()
	var steps := 64
	for i in steps + 1:
		var x := s.x * i / steps
		pts.append(Vector2(x, _ridge_y(s, x, base, amp, freq, phase)))
	pts.append(Vector2(s.x, s.y))
	pts.append(Vector2(0.0, s.y))
	draw_colored_polygon(pts, col)
	# hedgerows: short clumps of bushes running down from the crest
	var hedge := col.darkened(0.3)
	for i in range(3, steps - 2, 9):
		var x0 := s.x * i / steps
		var y0 := _ridge_y(s, x0, base, amp, freq, phase)
		var r := 2.5 + amp * 0.08
		for k in 7:
			var p := Vector2(x0 + k * r * 1.3 + sin(k * 2.3 + i) * r * 0.4, y0 + 3.0 + k * r * 0.9)
			draw_circle(p, r * (1.0 + 0.25 * sin(k * 1.9 + i)), hedge)


## A tiny hall silhouette: gabled block (kingdom) or a dome (clans), with a waving pennant.
func _hall(at: Vector2, h: float, banner: Color, dome: bool = false) -> void:
	var dark := Color("#0f1610")
	if dome:
		draw_circle(at + Vector2(0, -h * 0.35), h * 0.6, dark)
		draw_rect(Rect2(at.x - h * 0.6, at.y - h * 0.35, h * 1.2, h * 0.4), dark)
	else:
		draw_rect(Rect2(at.x - h * 0.55, at.y - h * 0.6, h * 1.1, h * 0.65), dark)
		draw_colored_polygon(PackedVector2Array([at + Vector2(-h * 0.7, -h * 0.55),
			at + Vector2(0, -h * 1.25), at + Vector2(h * 0.7, -h * 0.55)]), dark)
	var mast := at + Vector2(h * 0.15, -h * (1.25 if not dome else 0.95))
	draw_line(mast, mast + Vector2(0, -h * 0.7), dark, 2.0)
	var wave := sin(_t * 2.2 + at.x) * h * 0.06
	draw_colored_polygon(PackedVector2Array([mast + Vector2(0, -h * 0.7),
		mast + Vector2(h * 0.55, -h * 0.6 + wave), mast + Vector2(0, -h * 0.45)]), banner)
