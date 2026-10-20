class_name PauseMenu
extends CanvasLayer
## F10 game menu (placeholder for juice HUD-11): Resume, Restart, Quit to Main Menu, Quit to
## Desktop over a dimmed, paused world. Main shows it while the tree is paused; it processes while
## paused (process mode ALWAYS). Esc resumes as well. Visual / UI only.

signal resume_pressed
signal restart_pressed
signal menu_pressed

var buttons: Dictionary = {}         ## "resume" | "restart" | "menu" | "quit" -> Button


func _ready() -> void:
	layer = 5
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.add_child(UiStyle.dimmer(0.5))
	var box := UiStyle.centred_panel(root)
	box.add_child(UiStyle.label(Defs.text("pause_title"), 34, UiStyle.TEXT_GOLD))
	box.add_child(HSeparator.new())
	for entry: Array in [["resume", "pause_resume"], ["restart", "pause_restart"],
			["menu", "pause_quit_menu"], ["quit", "pause_quit_desktop"]]:
		var b := UiStyle.button(Defs.text(entry[1]))
		b.name = str(entry[0]).capitalize()
		box.add_child(b)
		buttons[entry[0]] = b
	(buttons["resume"] as Button).pressed.connect(func() -> void: resume_pressed.emit())
	(buttons["restart"] as Button).pressed.connect(func() -> void: restart_pressed.emit())
	(buttons["menu"] as Button).pressed.connect(func() -> void: menu_pressed.emit())
	(buttons["quit"] as Button).pressed.connect(func() -> void: get_tree().quit())


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("cancel"):
		resume_pressed.emit()
		get_viewport().set_input_as_handled()
