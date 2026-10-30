class_name InventoryPanel
extends GridContainer
## The hero's six inventory slots (rules §6.8; juice ITM-* P0 subset), between the selection
## panel and the command card, shown while a single hero is selected (own: usable; enemy:
## read-only). Each slot is a CardButton: the item's short name, its numpad key (7 8 / 4 5 / 1 2),
## its charges, the cooldown sweep of its group; permanent items show as passive. Left click or
## the key: use (targeted items arm targeting); right click: arm "move item" (a click on the
## ground drops it, on another own hero gives it). Refreshed 10 times a second from sim state.

signal slot_hovered(button: CardButton)
signal slot_unhovered(button: CardButton)

const KEYS: Array[String] = ["7", "8", "4", "5", "1", "2"]
const SLOT := Vector2(46, 46)
const REFRESH_S := 0.1

var world: World
var commands: CommandInput
var hero: Unit = null
var buttons: Array[CardButton] = []
var _since := 0.0


func _init() -> void:
	name = "Inventory"
	columns = 2
	add_theme_constant_override("h_separation", 4)
	add_theme_constant_override("v_separation", 4)
	mouse_filter = Control.MOUSE_FILTER_STOP
	for i in 6:
		# a holder per slot: CardButton owns its x offset (the deny shake)
		var holder := Control.new()
		holder.custom_minimum_size = SLOT
		holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(holder)
		var b := CardButton.new()
		b.slot = i
		b.custom_minimum_size = SLOT
		b.size = SLOT
		b.add_theme_font_size_override("font_size", 11)
		b.pressed.connect(_on_pressed.bind(i))
		b.gui_input.connect(_on_gui_input.bind(i))
		b.mouse_entered.connect(func() -> void: slot_hovered.emit(b))
		b.mouse_exited.connect(func() -> void: slot_unhovered.emit(b))
		holder.add_child(b)
		buttons.append(b)


func setup(w: World, cmd: CommandInput) -> void:
	world = w
	commands = cmd


## Shows `u`'s inventory (null hides the panel).
func show_hero(u: Unit) -> void:
	hero = u if u != null and u.is_hero else null
	visible = hero != null
	_refresh()


func _process(delta: float) -> void:
	_since += delta
	if _since >= REFRESH_S and visible:
		_since = 0.0
		_refresh()


## The slot's card entry (null when empty).
func entry(i: int) -> CardModel.Entry:
	if hero == null or i >= hero.inventory.size() or hero.inventory[i] == null:
		return null
	var it: Dictionary = hero.inventory[i]
	var iid := str(it["id"])
	var d := Defs.item(iid)
	var e := CardModel.Entry.new()
	e.slot = i
	e.kind = "item"
	e.id = iid
	e.label = short_name(str(d.get("name", iid)))
	e.key = KEYS[i]
	e.level = int(it.get("charges", 0))
	e.passive = str(d.get("class", "")) == "permanent" or str(d.get("class", "")) == "artifact"
	e.targeted = str(d.get("targeting", "instant")) != "instant"
	if world != null and not e.passive:
		e.cooldown_left = world.items.cooldown_left(hero, i)
		var group := str(d.get("cooldown_group", iid))
		e.cooldown_total = float((Defs.rule("items.group_cooldown", {}) as Dictionary).get(group, d.get("cooldown", 0.0)))
		if e.cooldown_left > 0.0:
			e.state = CardModel.State.BUSY
			e.reason = "cooldown"
	return e


## Two short lines from an item name ("Way-Home Horn" -> "Way-Home\nHorn").
static func short_name(n: String) -> String:
	var words := n.split(" ", false)
	if words.size() <= 1:
		return n
	var half := ceili(words.size() / 2.0)
	return " ".join(words.slice(0, half)) + "\n" + " ".join(words.slice(half))


func _refresh() -> void:
	for i in buttons.size():
		var b := buttons[i]
		var e := entry(i)
		b.show_entry(e, e.key if e != null else "")
		b.chip = str(e.level) if e != null and e.level > 0 else ""
		b.disabled = e == null or hero == null or world == null or hero.player_id != world.local_player_id
		b.queue_redraw()


func _on_pressed(i: int) -> void:
	if commands != null and hero != null and not commands.use_item(hero, i):
		Audio.deny("disabled")


func _on_gui_input(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_RIGHT:
		if commands != null and hero != null:
			commands.begin_move_item(hero, i)
		accept_event()


## Tooltip content for slot `i`: name, what it does, charges, the cooldown, how to move it.
func tooltip_for(i: int) -> Dictionary:
	var e := entry(i)
	if e == null:
		return {}
	var lines: Array[String] = CardModel.item_lines(e.id)
	if e.level > 0:
		lines.append(Defs.text("tip_charges") % e.level)
	lines.append(Defs.text("tip_item_move"))
	return {"title": str(Defs.item(e.id).get("name", e.id)), "key": e.key, "lines": lines}
