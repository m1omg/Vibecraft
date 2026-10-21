extends Node
## User settings (camera feel, UI options) persisted in user://settings.cfg.
## Also owns the default input map so project.godot and runtime fallback share one source.

signal changed

const SAVE_PATH := "user://settings.cfg"

# Camera
var edge_pan_enabled: bool = true
var edge_pan_margin_px: int = 4
var edge_pan_speed: float = 1.0      ## multiplier on the base pan speed
var key_pan_speed: float = 1.0       ## multiplier for arrow-key panning
var drag_pan_speed: float = 1.0      ## multiplier for middle-mouse drag
var zoom_step: float = 3.0           ## metres per wheel notch

# Selection / input
var double_click_ms: int = 350       ## also used for control-group double-tap
var max_selection: int = 12
var drag_threshold_px: float = 6.0

# UI
var always_show_health_bars: bool = true
## Command hotkeys (rules §18.4): "classic" (Move M, Stop S, Hold H, Attack A, Patrol P) or
## "grid" (the 4 x 3 card on Q W E R / A S D F / Z X C V); "" = rules.controls.hotkey_preset.
var hotkey_preset: String = ""

# Skirmish setup (main menu)
var skirmish_faction: String = "kingdom"   ## the local player's faction; the computer plays the other
var ai_difficulty: String = "normal"       ## rules.ai.<difficulty>: easy, normal, hard

const _PERSISTED: Array[String] = [
	"edge_pan_enabled", "edge_pan_margin_px", "edge_pan_speed", "key_pan_speed",
	"drag_pan_speed", "zoom_step", "double_click_ms", "always_show_health_bars", "hotkey_preset",
	"skirmish_faction", "ai_difficulty",
]

## action name -> Array of input descriptors. Descriptor: {"key": Key} or {"mouse": MouseButton}.
## Control groups use plain digit keys; ctrl/shift are read from the event modifiers.
## `cmd_*` are the Classic preset's mnemonic order keys, `card_*` the Grid preset's slots.
static func default_actions() -> Dictionary:
	var a: Dictionary = {
		"cam_left": [{"key": KEY_LEFT}],
		"cam_right": [{"key": KEY_RIGHT}],
		"cam_up": [{"key": KEY_UP}],
		"cam_down": [{"key": KEY_DOWN}],
		"cam_zoom_in": [{"mouse": MOUSE_BUTTON_WHEEL_UP}, {"key": KEY_PAGEUP}],
		"cam_zoom_out": [{"mouse": MOUSE_BUTTON_WHEEL_DOWN}, {"key": KEY_PAGEDOWN}],
		"cam_drag": [{"mouse": MOUSE_BUTTON_MIDDLE}],
		"select": [{"mouse": MOUSE_BUTTON_LEFT}],
		"command": [{"mouse": MOUSE_BUTTON_RIGHT}],
		"queue_modifier": [{"key": KEY_SHIFT}],
		"cancel": [{"key": KEY_ESCAPE}],
		"menu": [{"key": KEY_F10}],
		"jump_alert": [{"key": KEY_SPACE}],
		"subgroup_next": [{"key": KEY_TAB}],     # Shift+Tab cycles backwards (Selection)
		"cycle_halls": [{"key": KEY_BACKSPACE}],
		"idle_worker": [{"key": KEY_F8}, {"key": KEY_QUOTELEFT}],   # Ctrl selects every idle worker
		"select_hero_1": [{"key": KEY_F1}],
		"select_hero_2": [{"key": KEY_F2}],
		"select_hero_3": [{"key": KEY_F3}],
	}
	for i in 10:
		a["group_%d" % i] = [{"key": KEY_0 + i}]
	var grid: Array[Key] = [KEY_Q, KEY_W, KEY_E, KEY_R, KEY_A, KEY_S, KEY_D, KEY_F,
		KEY_Z, KEY_X, KEY_C, KEY_V]
	for i in grid.size():
		a["card_%d" % i] = [{"key": grid[i]}]
	var classic: Dictionary = {"cmd_move": KEY_M, "cmd_stop": KEY_S, "cmd_hold": KEY_H,
		"cmd_attack": KEY_A, "cmd_patrol": KEY_P}
	for action: String in classic:
		a[action] = [{"key": classic[action]}]
	return a


## The active hotkey preset: the user's choice, else the data default (rules §18.4).
func active_hotkey_preset() -> String:
	if hotkey_preset == "classic" or hotkey_preset == "grid":
		return hotkey_preset
	return str(Defs.rule("controls.hotkey_preset", "classic"))


static func make_event(desc: Dictionary) -> InputEvent:
	if desc.has("key"):
		var k := InputEventKey.new()
		k.device = -1
		k.physical_keycode = desc["key"]
		return k
	var m := InputEventMouseButton.new()
	m.device = -1
	m.button_index = desc["mouse"]
	return m


func _ready() -> void:
	ensure_input_actions()
	load_settings()


## Adds any default action missing from the InputMap (e.g. when project.godot was edited by hand).
func ensure_input_actions() -> void:
	var defaults := default_actions()
	for action: String in defaults:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for desc: Dictionary in defaults[action]:
			InputMap.action_add_event(action, make_event(desc))


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return
	for key in _PERSISTED:
		if cfg.has_section_key("settings", key):
			set(key, cfg.get_value("settings", key))
	changed.emit()


func save_settings() -> void:
	var cfg := ConfigFile.new()
	for key in _PERSISTED:
		cfg.set_value("settings", key, get(key))
	cfg.save(SAVE_PATH)
	changed.emit()
