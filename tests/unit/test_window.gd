extends "res://tests/test_case.gd"
## Fullscreen by default (Settings, HANDOVER §4): the project starts in borderless fullscreen,
## Alt+Enter and F11 toggle fullscreen <-> windowed (the Settings autoload handles it even while
## the tree is paused), and the choice is remembered in user://settings.cfg. DisplayServer window
## calls are skipped headless, so this runs in the headless suite.

var _keep: String


func before_each() -> void:
	_keep = Settings.window_mode


func after_each() -> void:
	Settings.window_mode = _keep
	Settings.save_settings()
	tree.paused = false


func _key(key: Key, alt: bool) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.keycode = key
		ev.alt_pressed = alt
		ev.pressed = pressed
		tree.root.push_input(ev, true)


func _saved_mode() -> String:
	var cfg := ConfigFile.new()
	cfg.load(Settings.SAVE_PATH)
	return str(cfg.get_value("settings", "window_mode", ""))


func test_fullscreen_is_the_default() -> void:
	assert_eq(int(ProjectSettings.get_setting("display/window/size/mode")), DisplayServer.WINDOW_MODE_FULLSCREEN,
		"project.godot starts borderless fullscreen (mode 3)")
	assert_eq(int(ProjectSettings.get_setting("display/window/size/viewport_width")), 1600, "1600 x 900 UI design size")
	assert_eq(str(ProjectSettings.get_setting("display/window/stretch/aspect")), "expand", "wider screens show more map")
	var fresh: Node = (load("res://src/autoload/settings.gd") as GDScript).new()
	assert_eq(str(fresh.get("window_mode")), "fullscreen", "a fresh Settings defaults to fullscreen")
	fresh.free()
	assert_eq(Settings.process_mode, Node.PROCESS_MODE_ALWAYS, "the toggle works while paused")


func test_toggle_flips_and_persists() -> void:
	Settings.window_mode = "fullscreen"
	assert_eq(Settings.toggle_fullscreen(), "windowed", "fullscreen -> windowed")
	assert_eq(_saved_mode(), "windowed", "remembered")
	assert_eq(Settings.toggle_fullscreen(), "fullscreen", "and back")
	assert_eq(_saved_mode(), "fullscreen", "remembered")


func test_alt_enter_and_f11_toggle_even_while_paused() -> void:
	assert_true(InputMap.has_action("toggle_fullscreen"), "the action exists")
	Settings.window_mode = "fullscreen"
	_key(KEY_ENTER, true)
	assert_eq(Settings.window_mode, "windowed", "Alt+Enter toggles")
	_key(KEY_ENTER, false)
	assert_eq(Settings.window_mode, "windowed", "Enter alone does not")
	tree.paused = true
	_key(KEY_F11, false)
	assert_eq(Settings.window_mode, "fullscreen", "F11 toggles while paused")
