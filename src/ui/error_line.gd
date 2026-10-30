class_name ErrorLine
extends Label
## The error line (juice HUD-06): one line at the playfield's bottom centre, 28 px above the
## console, in DENIAL red (#FF5A4A) with a dark outline. In: scale 1.12 → 1.0 and α 0 → 1 over
## 90 ms (a landing, no overshoot); held 1.8 s; out over 350 ms. The same message again while
## it shows restarts the hold and shakes it (6 px, 280 ms), never stacking; a different one
## replaces it with a 60 ms cross-fade. Real time (closed form), UI only.

const IN_S := 0.09
const HOLD_S := 1.8
const OUT_S := 0.35
const SWAP_S := 0.06
const SHAKE_PX := 6.0
const SHAKE_S := 0.28
const COLOR := Color("#FF5A4A")
const OUTLINE := Color("#2A0A06")

var _t0 := -100.0                  ## when the current message landed
var _shake_t0 := -100.0
var _swap_t0 := -100.0
var _base_x := 0.0


func _init() -> void:
	name = "ErrorLine"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_theme_font_size_override("font_size", 18)
	add_theme_color_override("font_color", COLOR)
	add_theme_color_override("font_outline_color", OUTLINE)
	add_theme_constant_override("outline_size", 4)
	visible = false


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


func show_error(msg: String) -> void:
	if msg.is_empty():
		return
	var t := now()
	if visible and msg == text and t - _t0 < IN_S + HOLD_S + OUT_S:
		_t0 = t - IN_S          # hold again, no new landing
		_shake_t0 = t
		return
	if visible and t - _t0 < IN_S + HOLD_S + OUT_S:
		_swap_t0 = t
	text = msg
	_t0 = t
	visible = true


## Hides the line at once.
func clear() -> void:
	visible = false
	_t0 = -100.0


func _process(_delta: float) -> void:
	if not visible:
		return
	var age := now() - _t0
	if age >= IN_S + HOLD_S + OUT_S:
		visible = false
		return
	var a := 1.0
	var s := 1.0
	if age < IN_S:
		var u := Juice.out_quad(age / IN_S)
		a = u
		s = lerpf(1.12, 1.0, u)
	elif age > IN_S + HOLD_S:
		a = 1.0 - (age - IN_S - HOLD_S) / OUT_S
	var swap := now() - _swap_t0
	if swap < SWAP_S:
		a *= swap / SWAP_S
	modulate.a = clampf(a, 0.0, 1.0)
	pivot_offset = size * 0.5
	scale = Vector2(s, s)
	var shake := now() - _shake_t0
	position.x = _base_x + (JuiceCurves.shake(shake, SHAKE_PX, 0.08, SHAKE_S) if shake < SHAKE_S else 0.0)


## The resting x (the HUD lays the line out; the shake offsets from it).
func set_base_x(x: float) -> void:
	_base_x = x
