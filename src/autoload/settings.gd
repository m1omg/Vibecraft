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

const _PERSISTED: Array[String] = [
	"edge_pan_enabled", "edge_pan_margin_px", "edge_pan_speed", "key_pan_speed",
	"drag_pan_speed", "zoom_step", "double_click_ms", "always_show_health_bars",
]

## action name -> Array of input descriptors. Descriptor: {"key": Key} or {"mouse": MouseButton}.
## Control groups use plain digit keys; ctrl/shift are read from the event modifiers.
static func default_actions() -> Dictionary:
	var a: Dictionary = {
		"cam_left": [{"key": KEY_LEFT}],
		"cam_right": [{"key": KEY_RIGHT}],
		"cam_up": [{"key": KEY_UP}],
		"cam_down": [{"key": KEY_DOWN}],
		"cam_zoom_in": [{"mouse": MOUSE_BUTTON_WHEEL_UP}],
		"cam_zoom_out": [{"mouse": MOUSE_BUTTON_WHEEL_DOWN}],
		"cam_drag": [{"mouse": MOUSE_BUTTON_MIDDLE}],
		"select": [{"mouse": MOUSE_BUTTON_LEFT}],
		"command": [{"mouse": MOUSE_BUTTON_RIGHT}],
		"queue_modifier": [{"key": KEY_SHIFT}],
		"cancel": [{"key": KEY_ESCAPE}],
		"menu": [{"key": KEY_F10}],
		"jump_alert": [{"key": KEY_SPACE}],
		"subgroup_next": [{"key": KEY_TAB}],
	}
	for i in 10:
		a["group_%d" % i] = [{"key": KEY_0 + i}]
	var grid: Array[Key] = [KEY_Q, KEY_W, KEY_E, KEY_R, KEY_A, KEY_S, KEY_D, KEY_F,
		KEY_Z, KEY_X, KEY_C, KEY_V]
	for i in grid.size():
		a["card_%d" % i] = [{"key": grid[i]}]
	return a


static func make_event(desc: Dictionary) -> InputEvent:
	if desc.has("key"):
		var k := InputEventKey.new()
		k.physical_keycode = desc["key"]
		return k
	var m := InputEventMouseButton.new()
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
