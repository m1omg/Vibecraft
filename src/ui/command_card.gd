class_name CommandCard
extends GridContainer
## 4x3 command buttons laid out like the grid hotkeys (Q W E R / A S D F / Z X C V), showing
## CommandInput.current_card() (CardModel: unit orders, worker commands and build pages, building
## train / research / upgrade / rally / cancel). A button calls CommandInput.activate_card exactly
## like its hotkey, so targeted commands enter the same targeting mode; the button of the active
## targeting mode (or of the building being placed) shows pressed. Buttons act on the mouse
## press, not the release (juice bible §1.2 rule 1). Refreshed on selection, page and targeting
## changes and 10 times a second (costs, queues, requirements; HUD-05 polls at 10 Hz). A refused
## press or hotkey shakes its button (CommandInput.denied). Hover feeds the HUD tooltip.

signal entry_hovered(button: CardButton)
signal entry_unhovered(button: CardButton)

const SLOTS := 12
const BUTTON_SIZE := Vector2(66, 54)
const REFRESH_S := 0.1

var commands: CommandInput
var selection: Selection
var buttons: Array[CardButton] = []
## The entries shown (CardModel.Entry or null per slot).
var entries: Array = []
var _since := 0.0


func _ready() -> void:
	columns = 4
	add_theme_constant_override("h_separation", 4)
	add_theme_constant_override("v_separation", 4)
	entries.resize(SLOTS)
	for i in SLOTS:
		var holder := Control.new()
		holder.name = "Slot%d" % i
		holder.custom_minimum_size = BUTTON_SIZE
		holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(holder)
		var b := CardButton.new()
		b.name = "Button"
		b.slot = i
		b.toggle_mode = true
		b.set_anchors_preset(Control.PRESET_FULL_RECT)
		b.pressed.connect(_on_pressed.bind(i))
		b.hovered.connect(func(btn: CardButton) -> void: entry_hovered.emit(btn))
		b.unhovered.connect(func(btn: CardButton) -> void: entry_unhovered.emit(btn))
		holder.add_child(b)
		buttons.append(b)


func setup(cmd: CommandInput, sel: Selection) -> void:
	commands = cmd
	selection = sel
	cmd.targeting_changed.connect(func(_m: String) -> void: refresh())
	cmd.page_changed.connect(func(_p: String) -> void: refresh())
	cmd.denied.connect(_on_denied)
	Events.selection_changed.connect(_on_selection_changed)
	refresh()


func _exit_tree() -> void:
	if Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.disconnect(_on_selection_changed)


func _on_selection_changed(_units: Array) -> void:
	refresh()


func _process(delta: float) -> void:
	_since += delta
	if _since >= REFRESH_S:
		_since = 0.0
		refresh()


## Hotkey text of a unit-order slot from the input map under the active preset (e.g. "A" or "R").
static func hotkey_label(slot: int) -> String:
	return CardModel.action_letter(CommandInput.hotkey_action(slot))


func refresh() -> void:
	entries = commands.current_card() if commands != null and commands.world != null else []
	entries.resize(SLOTS)
	for i in SLOTS:
		var e: CardModel.Entry = entries[i]
		var b := buttons[i]
		b.show_entry(e, CardModel.display_key(e))
		var armed := e != null and commands != null and (
			(e.targeted and commands.targeting == e.id)
			or (e.kind == "build" and commands.targeting == "place" and commands.placing == e.id))
		b.set_pressed_no_signal(armed)


## The entry shown in `slot` (null when empty).
func entry(slot: int) -> CardModel.Entry:
	return entries[slot] if slot >= 0 and slot < entries.size() else null


## A press clicks; a press that cannot act (paused, empty slot) plays the disabled deny; a
## refused entry is answered by CommandInput (deny, error line, `denied` -> shake).
func _on_pressed(slot: int) -> void:
	if commands != null:
		if commands.activate_card(slot, Input.is_key_pressed(KEY_SHIFT)):
			Audio.ui_click()
		elif entry(slot) == null or not commands.can_process():
			Audio.deny("disabled")
	refresh()


func _on_denied(_reason: String, _short: Dictionary, slot: int) -> void:
	if slot >= 0 and slot < buttons.size():
		buttons[slot].deny()
