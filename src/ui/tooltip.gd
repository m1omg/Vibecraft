class_name HudTooltip
extends PanelContainer
## The HUD's one tooltip (juice HUD-02; not Godot's built-in tooltip). It shows after a 250 ms
## dwell over a card button, queue slot or HUD element; within 500 ms of the last one closing the
## next shows at once (sweeping the card reads like flipping pages); it hides 80 ms after the
## pointer leaves. Docked, never following the cursor: above the command card's top-right corner
## (right-aligned, 8 px gap, never over the card), above other console elements.
## Content: a title with a hotkey chip; a cost row (gold, lumber, food, time) where an
## unaffordable value is red with its shortfall, "125 (-35)"; description lines; requirement
## lines in red. The HUD re-sends the content 10 times a second and the panel is rebuilt only
## when it changes; a cost that becomes affordable flashes warm for 150 ms. Motion: α 0→1 and
## y +4→0 px over 90 ms. Real time, UI only.

const DWELL_S := 0.25
const WARM_S := 0.5
const HIDE_S := 0.08
const IN_S := 0.09
const FLASH_S := 0.15
const GAP := 8.0
const WIDTH := 300.0
const RED := Color("#FF6A5A")
const IVORY := Color(0.95, 0.92, 0.85)
const FLASH := Color("#FFF4C2")
const COST_KINDS: Array[String] = ["gold", "lumber", "food", "time"]

## The control the tooltip belongs to (null = none).
var target: Control
## The content now shown or pending.
var content: Dictionary = {}

var _dock: Rect2
var _hover_t0 := -10.0
var _leave_t0 := -10.0
var _closed_t := -10.0
var _shown_t0 := -10.0
var _sig: String = ""
var _title: Label
var _key: Label
var _cost_row: HBoxContainer
var _cost: Dictionary = {}          ## kind -> [HBoxContainer, Label]
var _flash_t0: Dictionary = {}      ## kind -> real time the value became affordable
var _was_short: Dictionary = {}
var _body: RichTextLabel


func _init() -> void:
	name = "Tooltip"
	visible = false
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	top_level = true
	var sb := UiStyle.panel_box(Color(0.07, 0.06, 0.05, 0.96), UiStyle.PANEL_RIM, 1)
	sb.set_content_margin_all(10)
	sb.shadow_size = 6
	add_theme_stylebox_override("panel", sb)
	custom_minimum_size = Vector2(WIDTH, 0)
	var box := VBoxContainer.new()
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_theme_constant_override("separation", 4)
	add_child(box)
	var head := HBoxContainer.new()
	head.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(head)
	_title = UiStyle.label("", 17, UiStyle.TEXT_GOLD, HORIZONTAL_ALIGNMENT_LEFT)
	_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(_title)
	_key = UiStyle.label("", 13, Color(1.0, 0.9, 0.62), HORIZONTAL_ALIGNMENT_RIGHT)
	head.add_child(_key)
	_cost_row = HBoxContainer.new()
	_cost_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_cost_row.add_theme_constant_override("separation", 12)
	box.add_child(_cost_row)
	for k in COST_KINDS:
		var cell := HBoxContainer.new()
		cell.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_theme_constant_override("separation", 3)
		cell.add_child(UiGlyphs.Icon.new(k, 14.0))
		var l := UiStyle.label("", 14, IVORY, HORIZONTAL_ALIGNMENT_LEFT)
		cell.add_child(l)
		_cost_row.add_child(cell)
		_cost[k] = [cell, l]
	_body = RichTextLabel.new()
	_body.bbcode_enabled = true
	_body.fit_content = true
	_body.scroll_active = false
	_body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_body.custom_minimum_size = Vector2(WIDTH - 20.0, 0)
	_body.add_theme_font_size_override("normal_font_size", 14)
	_body.add_theme_color_override("default_color", IVORY)
	box.add_child(_body)


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


## The pointer entered `c`: show `c_content` docked above `dock` (global rect) after the dwell,
## or at once inside the warm window.
func hover(c: Control, c_content: Dictionary, dock: Rect2) -> void:
	target = c
	_dock = dock
	_leave_t0 = -10.0
	set_content(c_content)
	if visible or now() - _closed_t < WARM_S:
		_hover_t0 = now() - DWELL_S
	else:
		_hover_t0 = now()


## The pointer left `c`.
func unhover(c: Control) -> void:
	if c == target:
		_leave_t0 = now()


func set_content(c: Dictionary) -> void:
	content = c
	var sig := str(c)
	if sig == _sig:
		return
	_sig = sig
	_rebuild()


func is_shown() -> bool:
	return visible


func _rebuild() -> void:
	_title.text = str(content.get("title", ""))
	var key := str(content.get("key", ""))
	_key.text = "[%s]" % key if key != "" else ""
	var cost: Dictionary = content.get("cost", {})
	var short: Dictionary = content.get("short", {})
	var any := false
	for k in COST_KINDS:
		var cell: HBoxContainer = _cost[k][0]
		var l: Label = _cost[k][1]
		var v := int(cost.get(k, 0))
		cell.visible = v > 0
		any = any or v > 0
		if v <= 0:
			continue
		var miss := int(short.get(k, 0))
		l.text = ("%d s" % v if k == "time" else str(v)) + ("  (-%d)" % miss if miss > 0 else "")
		if bool(_was_short.get(k, false)) and miss <= 0:
			_flash_t0[k] = now()
		_was_short[k] = miss > 0
		l.add_theme_color_override("font_color", RED if miss > 0 else IVORY)
	_cost_row.visible = any
	var lines: Array[String] = []
	for line: Variant in content.get("lines", []):
		lines.append(str(line))
	for req: Variant in content.get("requires", []):
		lines.append("[color=#FF6A5A]%s[/color]" % str(req))
	_body.text = "\n".join(lines)
	_body.visible = not lines.is_empty()
	reset_size()


func _process(_delta: float) -> void:
	var t := now()
	if target != null and not is_instance_valid(target):
		target = null
	var want := target != null and t - _hover_t0 >= DWELL_S and (_leave_t0 < 0.0 or t - _leave_t0 < HIDE_S)
	if target != null and _leave_t0 >= 0.0 and t - _leave_t0 >= HIDE_S:
		target = null
		want = false
	if want and not visible:
		visible = true
		_shown_t0 = t
		reset_size()
	elif not want and visible:
		visible = false
		_closed_t = t
	if not visible:
		return
	var u := clampf((t - _shown_t0) / IN_S, 0.0, 1.0)
	modulate.a = Juice.out_quad(u)
	var at := Vector2(_dock.end.x - size.x, _dock.position.y - GAP - size.y)
	var vp := get_viewport_rect().size
	at.x = clampf(at.x, 4.0, maxf(4.0, vp.x - size.x - 4.0))
	at.y = maxf(at.y, 4.0)
	global_position = at + Vector2(0.0, 4.0 * (1.0 - Juice.out_quad(u)))
	for k: String in _flash_t0.keys():
		var a := t - float(_flash_t0[k])
		var l: Label = _cost[k][1]
		if a >= FLASH_S:
			_flash_t0.erase(k)
			l.add_theme_color_override("font_color", IVORY)
		else:
			l.add_theme_color_override("font_color", FLASH.lerp(IVORY, a / FLASH_S))
