class_name QueuePanel
extends HBoxContainer
## The selected building's production queue (juice HUD-09 P0; rules §4.6: 1 active + 6
## waiting): 7 slots, the first 48 px and the rest 40 px. The first carries a progress bar read
## from the sim and its time left; when it waits for food it greys with the loaf glyph (the bar
## stops, honestly). Clicking any slot cancels it with a full refund
## (CommandInput.cancel_queue_slot). Hover feeds the HUD tooltip ("Hodman · 0:12 left · click to
## cancel"). Reads sim state only.

signal slot_hovered(button: CardButton)
signal slot_unhovered(button: CardButton)

const SLOTS := 7
const FIRST := Vector2(48, 48)
const REST := Vector2(40, 40)

var commands: CommandInput
var building: Unit
var buttons: Array[CardButton] = []
## The queue entries shown (Production queue dictionaries).
var items: Array = []
var time_label: Label


func _ready() -> void:
	add_theme_constant_override("separation", 4)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in SLOTS:
		var holder := Control.new()
		holder.custom_minimum_size = FIRST if i == 0 else REST
		holder.size_flags_vertical = Control.SIZE_SHRINK_END
		holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(holder)
		var b := CardButton.new()
		b.slot = i
		b.set_anchors_preset(Control.PRESET_FULL_RECT)
		b.add_theme_font_size_override("font_size", 10)
		b.pressed.connect(_on_pressed.bind(i))
		b.hovered.connect(func(btn: CardButton) -> void: slot_hovered.emit(btn))
		b.unhovered.connect(func(btn: CardButton) -> void: slot_unhovered.emit(btn))
		holder.add_child(b)
		buttons.append(b)
	time_label = UiStyle.label("", 13, UiStyle.TEXT_DIM, HORIZONTAL_ALIGNMENT_LEFT)
	time_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	add_child(time_label)


## Shows `b`'s queue (null or an empty queue hides the panel).
func refresh(b: Unit) -> void:
	building = b
	var w := commands.world if commands != null else null
	items = w.production.queue_of(b).duplicate() if w != null and b != null and is_instance_valid(b) else []
	visible = not items.is_empty()
	if not visible:
		return
	for i in SLOTS:
		var btn := buttons[i]
		var holder := btn.get_parent() as Control
		holder.visible = i < items.size()
		if i >= items.size():
			continue
		var e: Dictionary = items[i]
		var id := str(e["id"])
		btn.text = Hud.initials({"name": CardModel.display_name(id)})
		btn.face = Hud.icon_color(id).darkened(0.45) if Defs.units.has(id) else Color(0.25, 0.2, 0.14)
		var stalled := i == 0 and not bool(e.get("started", false))
		btn.set_state(CardModel.State.BUSY if stalled else CardModel.State.READY, "", "")
		btn.badge = "food" if stalled else ""
		btn.progress = w.production.progress_of(b) if i == 0 else -1.0
		btn.queue_redraw()
	var head: Dictionary = items[0]
	if not bool(head.get("started", false)):
		time_label.text = Defs.text("queue_stalled")
	else:
		time_label.text = Defs.text("time_left") % _mmss(left_s(head))


## Seconds left on queue entry `e`.
static func left_s(e: Dictionary) -> float:
	return maxf(0.0, float(int(e["total"]) - int(e["ticks"])) * World.DT)


static func _mmss(s: float) -> Array:
	var whole := ceili(s)
	return [whole / 60, whole % 60]


## Tooltip content for slot `i`.
func tooltip_for(i: int) -> Dictionary:
	if i < 0 or i >= items.size():
		return {}
	var e: Dictionary = items[i]
	var title := CardModel.display_name(str(e["id"]))
	if e["kind"] == "revive":
		title = Defs.text("revive_hero") % title
	var line := ""
	if i == 0 and not bool(e.get("started", false)):
		line = Defs.text("queue_waiting") % title
	elif i == 0:
		line = Defs.text("queue_slot") % ([title] + _mmss(left_s(e)))
	else:
		line = Defs.text("queue_waiting") % title
	return {"title": title, "lines": [line]}


func _on_pressed(i: int) -> void:
	if commands != null and building != null and i < items.size():
		commands.cancel_queue_slot(building, i)
		Audio.ui_click()

