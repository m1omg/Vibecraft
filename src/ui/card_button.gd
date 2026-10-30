class_name CardButton
extends Button
## One command-card button (juice HUD-01, HUD-05) or production-queue slot (HUD-09): the entry's
## label, a hotkey chip in the top-left corner and its availability drawn over the face:
##   - missing requirement: desaturated and dimmed, with a bronze lock top-right;
##   - unaffordable: full colour under a diagonal hatch, with the short resource's glyph
##     bottom-left (coin = gold, log = lumber); when it becomes affordable the hatch wipes away
##     left to right in 220 ms and the glyph shrinks out; becoming unaffordable fades it in;
##   - capped (queue full, hero limit): grey with a reason chip; busy: grey;
##   - a refused press: a 4 px horizontal shake and a red flash fading over 300 ms (ECO-14);
##   - queue slots: a progress bar along the bottom edge.
## Acts on the press, not the release (juice §1.2 rule 1). Real-time curves in closed form (the
## same at any refresh rate). Drawing only: CommandCard / QueuePanel decide what it shows.

signal hovered(button: CardButton)
signal unhovered(button: CardButton)

const SHAKE_PX := 4.0
const SHAKE_S := 0.24
const FLASH_S := 0.3
const WIPE_S := 0.22
const FADE_IN_S := 0.15
const GLYPH_OUT_S := 0.12
const HATCH := Color(0.078, 0.067, 0.051, 0.28)
const HATCH_PERIOD := 4.0
const FLASH := Color(0.9, 0.12, 0.08, 0.45)
const LOCK := Color(0.66, 0.46, 0.22)
const CHIP_BG := Color(0.04, 0.035, 0.03, 0.85)
const BAR_BG := Color(0.0, 0.0, 0.0, 0.6)
const BAR := Color(0.94, 0.62, 0.22)

var slot: int = -1
var state: int = CardModel.State.READY
var key_text: String = ""
var chip: String = ""              ## capped reason chip
var short_kind: String = ""        ## "gold" / "lumber" while unaffordable
var progress: float = -1.0         ## 0..1 progress bar (queue slots), -1 = none
var badge: String = ""             ## a glyph over the face (a queue slot waiting for food: "food")
var face: Color = Color(0.2, 0.18, 0.15)
var entry: CardModel.Entry         ## what the button shows (null = empty)

var _box: StyleBoxFlat
var _shake_t0 := -10.0
var _flash_t0 := -10.0
var _wipe_t0 := -10.0              ## became affordable: the hatch wipes away
var _fade_t0 := -10.0              ## became unaffordable: the hatch fades in
var _last_short: String = ""


func _init() -> void:
	focus_mode = Control.FOCUS_NONE
	action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS
	autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	clip_text = true
	add_theme_font_size_override("font_size", 12)
	add_theme_color_override("font_disabled_color", Color(0.5, 0.48, 0.44))
	_box = StyleBoxFlat.new()
	_box.bg_color = face
	_box.border_color = Color(0.42, 0.35, 0.24)
	_box.set_border_width_all(1)
	_box.set_corner_radius_all(3)
	_box.content_margin_top = 12.0
	_box.content_margin_left = 3.0
	_box.content_margin_right = 3.0
	var hover := _box.duplicate() as StyleBoxFlat
	hover.border_color = Color(0.9, 0.78, 0.5)
	var down := _box.duplicate() as StyleBoxFlat
	down.border_color = Color(1.0, 0.86, 0.45)
	down.set_border_width_all(2)
	add_theme_stylebox_override("normal", _box)
	add_theme_stylebox_override("hover", hover)
	add_theme_stylebox_override("pressed", down)
	add_theme_stylebox_override("hover_pressed", down)
	add_theme_stylebox_override("disabled", _box)
	add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	mouse_entered.connect(func() -> void: hovered.emit(self))
	mouse_exited.connect(func() -> void: unhovered.emit(self))


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


## Shows card entry `e` (null = an empty, disabled slot).
func show_entry(e: CardModel.Entry, key_label: String) -> void:
	entry = e
	disabled = e == null
	text = e.label if e != null else ""
	key_text = key_label if e != null else ""
	set_state(e.state if e != null else CardModel.State.READY,
		"" if e == null or e.short.is_empty() else ("gold" if e.short.has("gold") else "lumber"),
		_chip_for(e))
	face = Hud.icon_color(e.id).darkened(0.45) if e != null and Defs.units.has(e.id) else Color(0.2, 0.18, 0.15)
	_refresh_face()


static func _chip_for(e: CardModel.Entry) -> String:
	if e == null or e.state != CardModel.State.CAPPED:
		return ""
	return "7/7" if e.reason == "queue_full" else "max"


## Availability state with its transitions (wipe when it becomes affordable, fade when not).
func set_state(s: int, short: String, chip_text: String) -> void:
	var was_short := state == CardModel.State.UNAFFORDABLE
	var is_short := s == CardModel.State.UNAFFORDABLE
	if was_short and not is_short:
		_wipe_t0 = now()
		_last_short = short_kind
	elif is_short and not was_short:
		_fade_t0 = now()
	state = s
	short_kind = short
	chip = chip_text
	_refresh_face()
	queue_redraw()


func _refresh_face() -> void:
	var c := face
	var font := Color(0.95, 0.92, 0.85)
	match state:
		CardModel.State.LOCKED:
			var g := c.get_luminance()
			c = Color(g, g, g).lerp(c, 0.1) * Color(0.5, 0.5, 0.5, 1.0)
			font = Color(0.55, 0.53, 0.5)
		CardModel.State.CAPPED, CardModel.State.BUSY:
			var g2 := c.get_luminance() * 0.8
			c = Color(g2, g2, g2)
			font = Color(0.62, 0.6, 0.56)
	_box.bg_color = c
	add_theme_color_override("font_color", font)
	add_theme_color_override("font_hover_color", font.lightened(0.2))
	add_theme_color_override("font_pressed_color", font.lightened(0.3))


## A refused press: shake and flash red.
func deny() -> void:
	_shake_t0 = now()
	_flash_t0 = now()
	queue_redraw()


func is_animating() -> bool:
	var t := now()
	return t - _shake_t0 < SHAKE_S or t - _flash_t0 < FLASH_S or t - _wipe_t0 < WIPE_S \
		or t - _fade_t0 < FADE_IN_S


func _process(_delta: float) -> void:
	var t := now()
	var dx := 0.0
	if t - _shake_t0 < SHAKE_S:
		dx = JuiceCurves.shake(t - _shake_t0, SHAKE_PX, 0.08, SHAKE_S)
	position.x = dx
	if is_animating():
		queue_redraw()


func _draw() -> void:
	var t := now()
	var r := Rect2(Vector2.ZERO, size)
	# unaffordable: hatch (fading in, or wiping away left to right once affordable)
	var hatch_from := 0.0
	var hatch_alpha := 0.0
	if state == CardModel.State.UNAFFORDABLE:
		hatch_alpha = clampf((t - _fade_t0) / FADE_IN_S, 0.0, 1.0)
	elif t - _wipe_t0 < WIPE_S:
		hatch_alpha = 1.0
		hatch_from = size.x * Juice.out_cubic((t - _wipe_t0) / WIPE_S)
	if hatch_alpha > 0.0:
		_draw_hatch(r, hatch_from, hatch_alpha)
	var glyph := short_kind if state == CardModel.State.UNAFFORDABLE else ""
	var glyph_scale := 1.0
	if glyph == "" and t - _wipe_t0 < GLYPH_OUT_S:
		glyph = _last_short
		glyph_scale = 1.0 - Juice.in_back((t - _wipe_t0) / GLYPH_OUT_S)
	if glyph != "" and glyph_scale > 0.0:
		UiGlyphs.draw(self, glyph, Vector2(9, size.y - 9), 4.5, glyph_scale)
	if state == CardModel.State.LOCKED:
		_draw_lock(Vector2(size.x - 9, 9))
	if badge != "":
		UiGlyphs.draw(self, badge, size * 0.5, 7.0)
	if chip != "":
		_draw_chip(chip, Vector2(size.x - 3, size.y - 3), true)
	if key_text != "":
		_draw_chip(key_text, Vector2(3, 2), false)
	if progress >= 0.0:
		var bar := Rect2(3, size.y - 7, size.x - 6, 4)
		draw_rect(bar, BAR_BG)
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(progress, 0.0, 1.0), bar.size.y)), BAR)
	var fa := FLASH.a * (1.0 - (t - _flash_t0) / FLASH_S)
	if fa > 0.0:
		draw_rect(r, Color(FLASH, fa))


func _draw_hatch(r: Rect2, from_x: float, alpha: float) -> void:
	var col := Color(HATCH, HATCH.a * alpha)
	var x := -r.size.y
	while x < r.size.x:
		var a := Vector2(x, r.size.y)
		var b := Vector2(x + r.size.y, 0.0)
		# clip the stripe to [from_x, width]
		if b.x > from_x:
			if a.x < from_x:
				a = a.lerp(b, (from_x - a.x) / (b.x - a.x))
			if b.x > r.size.x:
				b = a.lerp(b, (r.size.x - a.x) / (b.x - a.x))
			if a.x < r.size.x:
				draw_line(a, b, col, 1.5)
		x += HATCH_PERIOD


func _draw_lock(at: Vector2) -> void:
	draw_arc(at + Vector2(0, -2), 3.0, PI, TAU, 8, LOCK, 1.5)
	draw_rect(Rect2(at + Vector2(-4, -2), Vector2(8, 6)), LOCK)


func _draw_chip(s: String, at: Vector2, right_aligned: bool) -> void:
	var font := get_theme_default_font()
	var fs := 10
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var r := Rect2(at - Vector2(w + 4.0 if right_aligned else 0.0, 11.0 if right_aligned else 0.0), Vector2(w + 4, 11))
	draw_rect(r, CHIP_BG)
	draw_string(font, r.position + Vector2(2, 9), s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1.0, 0.9, 0.62))
