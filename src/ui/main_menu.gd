class_name MainMenu
extends Control
## The game's first screen (project main scene): title over a painted downland at dusk (drawn
## procedurally), and the modes available in this build: "Battlefield Sandbox" (Playtest 1) and
## "Quit". Later milestones add more modes. Starting a mode shows a loading line for two frames,
## then Main.start_match swaps in the match. UI only. The menu theme plays while it is up.

const SCENARIO := "battlefield"

var buttons: Dictionary = {}         ## "battlefield" | "quit" -> Button
var status: Label
var _starting: bool = false


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	get_tree().paused = false
	Audio.menu_entered()   # the menu theme loops (MUS-01)
	var backdrop := MenuBackdrop.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(backdrop)
	var column := VBoxContainer.new()
	column.set_anchors_preset(Control.PRESET_CENTER_TOP)
	column.anchor_left = 0.5
	column.anchor_right = 0.5
	column.offset_left = -260.0
	column.offset_right = 260.0
	column.offset_top = 90.0
	column.add_theme_constant_override("separation", 14)
	add_child(column)
	var title := UiStyle.label(Defs.text("menu_title").to_upper(), 84, UiStyle.TEXT_GOLD)
	title.add_theme_color_override("font_outline_color", Color(0.12, 0.08, 0.05))
	title.add_theme_constant_override("outline_size", 10)
	column.add_child(title)
	column.add_child(UiStyle.label(Defs.text("menu_subtitle"), 20, UiStyle.TEXT))
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 40)
	column.add_child(gap)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", UiStyle.panel_box())
	column.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	panel.add_child(box)
	var start := UiStyle.button(Defs.text("menu_battlefield"), 24, 420.0)
	start.name = "Battlefield"
	box.add_child(start)
	var hint := UiStyle.label(Defs.text("menu_battlefield_hint"), 15, UiStyle.TEXT_DIM)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size = Vector2(420, 0)
	box.add_child(hint)
	box.add_child(HSeparator.new())
	var quit := UiStyle.button(Defs.text("menu_quit"), 22, 420.0)
	quit.name = "Quit"
	box.add_child(quit)
	status = UiStyle.label("", 20, UiStyle.TEXT_GOLD)
	column.add_child(status)
	buttons = {"battlefield": start, "quit": quit}
	start.pressed.connect(start_battlefield)
	quit.pressed.connect(func() -> void: get_tree().quit())
	var footer := UiStyle.label("Playtest build  -  F10 in game opens the menu", 14, UiStyle.TEXT_DIM)
	footer.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	footer.offset_top = -34.0
	footer.offset_bottom = -10.0
	add_child(footer)


## "Battlefield Sandbox": loading line, then the match replaces this scene.
func start_battlefield() -> void:
	if _starting:
		return
	_starting = true
	for b: Button in buttons.values():
		b.disabled = true
	status.text = Defs.text("menu_loading")
	await get_tree().process_frame
	await get_tree().process_frame
	Main.start_match(get_tree(), SCENARIO)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo \
			and (event as InputEventKey).keycode in [KEY_ENTER, KEY_KP_ENTER]:
		start_battlefield()
		get_viewport().set_input_as_handled()
