class_name EndBanner
extends CanvasLayer
## End-of-match banner (placeholder for juice SEQ-02): a band across the screen with "Victory",
## "Defeat" or "Stalemate", one line of flavour, the battle time and the losses on each side, and
## "Play again" / "Main Menu". It fades in shortly after the result (real time), dims the world
## and blocks world input. Visual / UI only.

signal play_again_pressed
signal menu_pressed

const DELAY_S := 1.2
const FADE_S := 0.35

var kind: String = ""                ## "victory" | "defeat" | "draw"
var title: Label
var line: Label
var stats: Label
var play_again: Button
var main_menu: Button
var _band: PanelContainer
var _root: Control
var _t: float = -1.0


func _ready() -> void:
	layer = 6
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_root.add_child(UiStyle.dimmer(0.4))
	var centre := CenterContainer.new()
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	centre.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(centre)
	_band = PanelContainer.new()
	_band.custom_minimum_size = Vector2(760, 0)
	centre.add_child(_band)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	_band.add_child(box)
	title = UiStyle.label("", 68, UiStyle.TEXT)
	title.add_theme_color_override("font_outline_color", Color(0.08, 0.07, 0.05))
	title.add_theme_constant_override("outline_size", 8)
	box.add_child(title)
	line = UiStyle.label("", 20, UiStyle.TEXT)
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(line)
	stats = UiStyle.label("", 17, UiStyle.TEXT_GOLD)
	box.add_child(stats)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 18)
	box.add_child(row)
	play_again = UiStyle.button(Defs.text("end_play_again"), 20, 220.0)
	play_again.name = "PlayAgain"
	main_menu = UiStyle.button(Defs.text("end_main_menu"), 20, 220.0)
	main_menu.name = "MainMenu"
	row.add_child(play_again)
	row.add_child(main_menu)
	play_again.pressed.connect(func() -> void: play_again_pressed.emit())
	main_menu.pressed.connect(func() -> void: menu_pressed.emit())


## Shows the result after DELAY_S. `time_s` = sim seconds played; losses of each side.
func show_result(result_kind: String, time_s: float, own_losses: int, enemy_losses: int) -> void:
	kind = result_kind
	var key := {"victory": "end_victory", "defeat": "end_defeat"}.get(kind, "end_draw") as String
	title.text = Defs.text(key)
	line.text = Defs.text(key + "_line")
	var secs := roundi(time_s)
	@warning_ignore("integer_division")
	stats.text = "Battle time %d:%02d    Units lost %d    Foes felled %d" % [secs / 60, secs % 60,
		own_losses, enemy_losses]
	var band_col: Color = UiStyle.VICTORY if kind == "victory" else UiStyle.DEFEAT
	_band.add_theme_stylebox_override("panel", UiStyle.panel_box(band_col, UiStyle.TEXT_GOLD, 3))
	visible = true
	_root.modulate.a = 0.0
	_t = 0.0


## Shows the banner at once (tests, screenshots).
func finish_fade() -> void:
	if _t >= 0.0:
		_t = DELAY_S + FADE_S


func _process(delta: float) -> void:
	if _t < 0.0:
		return
	_t += delta
	_root.modulate.a = clampf((_t - DELAY_S) / FADE_S, 0.0, 1.0)
	if _t >= DELAY_S + FADE_S:
		_t = -1.0
		_root.modulate.a = 1.0
