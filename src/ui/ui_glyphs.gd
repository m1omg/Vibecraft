class_name UiGlyphs
extends RefCounted
## Small resource glyphs drawn with canvas primitives until the UI icon art exists (art bible
## §11): a coin (gold), a log (lumber), a loaf (food), a clock (time). Shapes, not just colour
## (juice HUD-05), so they read for colour-blind players too. Used by card buttons, the tooltip
## cost row, the queue panel and the top bar.

const GOLD := Color(1.0, 0.83, 0.3)
const LUMBER := Color(0.55, 0.38, 0.2)
const LUMBER_END := Color(0.78, 0.6, 0.38)
const FOOD := Color(0.86, 0.62, 0.36)
const TIME := Color(0.78, 0.8, 0.84)
const OUTLINE := Color(0.1, 0.07, 0.03)


## Draws glyph `kind` centred on `at` on `ci`, `r` px in radius (scale with `s`).
static func draw(ci: CanvasItem, kind: String, at: Vector2, r: float = 5.0, s: float = 1.0) -> void:
	r *= s
	match kind:
		"gold":
			ci.draw_circle(at, r + 1.0 * s, OUTLINE)
			ci.draw_circle(at, r, GOLD)
			ci.draw_circle(at - Vector2(r, r) * 0.25, r * 0.35, GOLD.lightened(0.35))
		"lumber":
			var rr := Rect2(at - Vector2(r * 1.2, r * 0.6), Vector2(r * 2.4, r * 1.2))
			ci.draw_rect(rr.grow(1.0 * s), OUTLINE)
			ci.draw_rect(rr, LUMBER)
			ci.draw_circle(rr.position + Vector2(rr.size.x, rr.size.y * 0.5), r * 0.6, LUMBER_END)
		"food":
			var lr := Rect2(at - Vector2(r * 1.1, r * 0.55), Vector2(r * 2.2, r * 1.1))
			ci.draw_rect(lr.grow(1.0 * s), OUTLINE)
			ci.draw_rect(lr, FOOD)
			ci.draw_circle(at - Vector2(r * 0.4, r * 0.45), r * 0.55, FOOD)
			ci.draw_circle(at + Vector2(r * 0.4, -r * 0.45), r * 0.55, FOOD)
		"time":
			ci.draw_circle(at, r + 1.0 * s, OUTLINE)
			ci.draw_circle(at, r, TIME)
			ci.draw_line(at, at + Vector2(0, -r * 0.7), OUTLINE, 1.2 * s)
			ci.draw_line(at, at + Vector2(r * 0.5, 0), OUTLINE, 1.2 * s)


## A Control that shows one glyph (cost rows, top bar).
class Icon:
	extends Control
	var kind: String = "gold"

	func _init(k: String = "gold", px: float = 14.0) -> void:
		kind = k
		custom_minimum_size = Vector2(px, px)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		UiGlyphs.draw(self, kind, size * 0.5, minf(size.x, size.y) * 0.36)
