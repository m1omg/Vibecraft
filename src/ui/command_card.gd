class_name CommandCard
extends GridContainer
## 4x3 command buttons laid out like the grid hotkeys (Q W E R / A S D F / Z X C V). A button
## calls CommandInput.activate_card exactly like its hotkey, so targeted commands enter the same
## targeting mode; the button of the active targeting mode is shown pressed.

const SLOTS := 12
const BUTTON_SIZE := Vector2(66, 54)

var commands: CommandInput
var selection: Selection
var buttons: Array[Button] = []


func _ready() -> void:
	columns = 4
	add_theme_constant_override("h_separation", 4)
	add_theme_constant_override("v_separation", 4)
	for i in SLOTS:
		var b := Button.new()
		b.name = "Slot%d" % i
		b.custom_minimum_size = BUTTON_SIZE
		b.focus_mode = Control.FOCUS_NONE
		b.toggle_mode = true
		b.clip_text = true
		b.add_theme_font_size_override("font_size", 13)
		b.pressed.connect(_on_pressed.bind(i))
		add_child(b)
		buttons.append(b)


func setup(cmd: CommandInput, sel: Selection) -> void:
	commands = cmd
	selection = sel
	cmd.targeting_changed.connect(_on_targeting_changed)
	Events.selection_changed.connect(_on_selection_changed)
	refresh()


func _on_targeting_changed(_mode: String) -> void:
	refresh()


func _on_selection_changed(_units: Array) -> void:
	refresh()


## Hotkey text of a card slot from the input map under the active preset (e.g. "A" or "R").
static func hotkey_label(slot: int) -> String:
	var action := CommandInput.hotkey_action(slot)
	if action.is_empty() or not InputMap.has_action(action):
		return ""
	for ev in InputMap.action_get_events(action):
		if ev is InputEventKey:
			var k := ev as InputEventKey
			return OS.get_keycode_string(k.physical_keycode if k.physical_keycode != KEY_NONE else k.keycode)
	return ""


func refresh() -> void:
	var active := commands != null and commands.has_orderable()
	for i in SLOTS:
		var b := buttons[i]
		var cmd: String = CommandInput.CARD.get(i, "")
		var shown := active and not cmd.is_empty()
		b.disabled = not shown
		b.text = "%s\n[%s]" % [CommandInput.LABELS.get(cmd, cmd), hotkey_label(i)] if shown else ""
		b.tooltip_text = b.text.replace("\n", " ")
		b.set_pressed_no_signal(shown and commands.targeting == cmd)


## A press clicks; a press that cannot act (paused, nothing orderable) plays the disabled deny.
func _on_pressed(slot: int) -> void:
	if commands != null:
		if commands.activate_card(slot, Input.is_key_pressed(KEY_SHIFT)):
			Audio.ui_click()
		else:
			Audio.deny("disabled")
	refresh()
