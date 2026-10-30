class_name CommandInput
extends Node
## Turns right-clicks, the command card and its hotkeys into command dictionaries for World.issue()
## (rules §18). Right-click = smart command (move / attack / gather / follow / rally resolved by
## the World; right-clicking a unit outside the selection targets it), shift = queue.
## The card is CardModel's for the active subgroup and `page` (the worker's build pages). Targeted
## entries (move, attack, patrol, gather, repair, rally) wait for a left-click; a building entry
## enters placement ("place", the BuildPlacement ghost); right-click or Esc cancels. Esc on a
## build page goes back, otherwise it presses the card's Cancel. Hotkeys follow the active preset
## (Settings.active_hotkey_preset(), rules §18.4): Classic = the entry's letter (unit orders
## through the rebindable `cmd_*` actions: M move, S stop, H hold, A attack, P patrol; "A-click"
## = attack-move, or attack on an enemy), Grid = `card_0..11` by position.
## Refused presses and clicks never reach the sim: the deny sound plays, `denied` fires (the HUD
## shakes the button and the counter) and the error line explains (Events.notification error_*).
## Must sit after Selection in the tree so it sees input first.

signal targeting_changed(mode: String)
signal page_changed(page: String)
## A refused press or click: error key, shortfall {gold, lumber} and the card slot (-1 = none).
signal denied(reason: String, short: Dictionary, slot: int)

## Unit orders by card slot and their Classic actions (CommandCard.hotkey_label).
const CARD: Dictionary = {0: "move", 1: "stop", 2: "hold", 3: "attack_move", 4: "patrol"}
const CLASSIC_ACTIONS: Dictionary = {"move": "cmd_move", "stop": "cmd_stop", "hold": "cmd_hold",
	"attack_move": "cmd_attack", "patrol": "cmd_patrol"}
## Refusals that are a locked or capped button (the dull "disabled" deny); the rest are errors.
const DISABLED_REASONS: Array[String] = ["requirements", "tier", "cannot_build", "cannot_train",
	"queue_full", "hero_limit", "busy", "maxed"]
const MARKER_SHADER := preload("res://src/fx/ring.gdshader")

var world: World
var camera: RtsCamera
var selection: Selection
var player_id: int = 0
## "", a targeted order (move, attack_move, patrol, gather, repair, rally) or "place".
var targeting: String = ""
var page: String = CardModel.PAGE_MAIN
const ABILITY_PREFIX := "ability:"   ## targeting mode of a unit or point ability: "ability:<id>"
const ITEM_PREFIX := "item:"         ## a targeted item: "item:<slot>"
const MOVE_ITEM_PREFIX := "moveitem:"   ## moving an item: "moveitem:<slot>" (ground drops, a hero gets it)
var item_hero: Unit = null           ## the hero whose item targeting is armed
## The building def being placed while targeting == "place".
var placing: String = ""
## The placement ghost (visual only), made on first use.
var placement: BuildPlacement
var _place_worker: int = 0           ## the worker Shift-placed buildings queue on


func setup(w: World, cam: RtsCamera, sel: Selection, pid: int) -> void:
	world = w
	camera = cam
	selection = sel
	player_id = pid
	if not Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.connect(_on_selection_changed)


func _exit_tree() -> void:
	if Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.disconnect(_on_selection_changed)


func _unhandled_input(event: InputEvent) -> void:
	if world == null:
		return
	if event is InputEventMouseButton and event.pressed:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			if targeting != "":
				_set_targeting("")
			else:
				_smart(mb.position, mb.shift_pressed)
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_LEFT and targeting != "":
			# a denied click (off the map, an untargetable unit, a blocked spot) keeps the mode, as
			# in the reference: the player retries without pressing the hotkey again
			if _issue_targeted(targeting, mb.position, mb.shift_pressed) and not mb.shift_pressed:
				_set_targeting("")
			get_viewport().set_input_as_handled()
	elif event is InputEventKey and event.pressed and not event.echo:
		var k := event as InputEventKey
		if k.is_action_pressed("cancel"):
			if escape():
				get_viewport().set_input_as_handled()
			return
		for i in 6:
			if k.is_action_pressed("item_%d" % (i + 1)):
				var h := selection.hero_in_selection() if selection != null else null
				if h != null:
					use_item(h, i)
					get_viewport().set_input_as_handled()
				return
		var slot := slot_for_key(k)
		if slot >= 0:
			activate_card(slot, k.shift_pressed)
			get_viewport().set_input_as_handled()


## While aiming an area ability, its area rides the cursor as a ground ring (one frame mark per
## frame).
func _process(_delta: float) -> void:
	if not targeting.begins_with(ABILITY_PREFIX) or Vfx.instance == null or camera == null:
		return
	var us := active_units()
	if us.is_empty():
		return
	var area := float(world.abilities.values_for(us[0], targeting.trim_prefix(ABILITY_PREFIX)).get("area", 0.0))
	if area <= 0.0:
		return
	var g := camera.screen_to_ground(get_viewport().get_mouse_position())
	if g != Vector3.INF:
		var marks := Vfx.instance.marks
		marks.add_frame(marks.ground_xf(g, area, 0), GroundMarks.Shape.RING, Color(0.55, 0.8, 1.0, 0.85), 0.05, 0.0)


## Input action that triggers a unit-order slot under the active preset ("" for other slots).
static func hotkey_action(slot: int) -> String:
	if Settings.active_hotkey_preset() == "grid":
		return "card_%d" % slot
	return str(CLASSIC_ACTIONS.get(CARD.get(slot, ""), ""))


# --- the card ------------------------------------------------------------------------------

## Own living units of the active subgroup, lead first (whose card is shown).
func active_units() -> Array[Unit]:
	var out: Array[Unit] = []
	if selection == null:
		return out
	var sub := selection.active_subgroup_def()
	for u in selection.selected:
		if u.alive and u.player_id == player_id and u.def_id == sub:
			out.append(u)
	return out


## The card now (CardModel entries, null for empty slots); a selected neutral shop shows its
## stock to whoever brings a hero.
func current_card() -> Array:
	var us := active_units()
	if us.is_empty():
		var shop := _shop_selected()
		if shop != null:
			us = [shop]
	return CardModel.build(world, player_id, us, page)


func set_page(p: String) -> void:
	if p == page:
		return
	page = p
	page_changed.emit(p)


## The card slot a key press triggers (-1 = none): Grid by position, Classic by letter (unit
## orders by their rebindable actions).
func slot_for_key(k: InputEventKey) -> int:
	var card := current_card()
	var grid := Settings.active_hotkey_preset() == "grid"
	var letter := OS.get_keycode_string(k.keycode if k.keycode != KEY_NONE else k.physical_keycode)
	for i in card.size():
		var e: CardModel.Entry = card[i]
		if e == null or e.key == "Esc":
			continue
		if grid:
			if k.is_action_pressed("card_%d" % i):
				return i
		elif e.action != "":
			if k.is_action_pressed(e.action):
				return i
		elif e.key != "" and e.key == letter:
			return i
	return -1


## Card slot pressed (hotkey or HUD button). Returns false when nothing happened: an empty slot,
## the game paused (no orders while paused; the HUD stays clickable) or a refused entry (then
## the deny plays and `denied` fires).
func activate_card(slot: int, shift: bool = false) -> bool:
	if not can_process() or world == null:
		return false
	var card := current_card()
	var e: CardModel.Entry = card[slot] if slot >= 0 and slot < card.size() else null
	if e == null:
		return false
	if not e.usable():
		_deny(e.reason, e.short, slot, e.missing)
		return false
	match e.kind:
		"order":
			if e.targeted:
				_set_targeting(e.id)
			elif e.id == "return":
				_issue_for(_ids(active_units()), {"type": "return", "queue": shift})
			else:
				_issue({"type": e.id, "queue": shift})
		"page":
			set_page(e.id)
		"back":
			set_page(CardModel.PAGE_MAIN)
		"build":
			begin_placement(e.id)
		"train":
			var b := _least_busy(active_units())
			if b == null:
				return false
			_issue_for([b.id], {"type": "train", "def": e.id, "queue": shift})
		"research", "upgrade":
			for b in active_units():
				if world.production.can_queue_research(b, e.id) == "":
					_issue_for([b.id], {"type": "research", "def": e.id})
					break
		"rally":
			_set_targeting("rally")
		"learn":
			var hero := active_units()[0]
			_issue_for([hero.id], {"type": "learn", "ability": e.id})
			if int(hero.hero.get("skill_points", 0)) <= 1:
				set_page(CardModel.PAGE_MAIN)     # that was the last point
		"revive":
			_issue_for([active_units()[0].id], {"type": "revive", "hero": e.uid})
		"ability":
			return _activate_ability(e, shift)
		"buy":
			var shop := _shop_selected()
			var buyer := CardModel.buyer_for(world, player_id, shop) if shop != null else null
			if buyer == null:
				return false
			_issue_raw({"type": "buy", "player": player_id, "units": [buyer.id], "target": shop.id, "def": e.id})
		"service":
			var shop2 := _shop_selected()
			if shop2 == null:
				return false
			var by := CardModel.buyer_for(world, player_id, shop2)
			_issue_raw({"type": "service", "player": player_id, "units": [by.id] if by != null else [],
				"target": shop2.id, "def": e.id})
		"inn_revive":
			var inn := _shop_selected()
			if inn == null:
				return false
			_issue_raw({"type": "service", "player": player_id, "units": [], "target": inn.id,
				"def": "neutral_inn_revive", "hero": e.uid})
		"cancel":
			var us := active_units()
			if e.id == "site":
				_issue_for(_ids(us), {"type": "cancel"})
			else:
				_issue_for([us[0].id], {"type": "cancel", "slot": -1})
	return true


## An ability button: instant abilities cast at once from the best caster of the subgroup; unit
## and point abilities arm targeting ("ability:<id>"); passives and auras do nothing.
func _activate_ability(e: CardModel.Entry, shift: bool) -> bool:
	if e.passive:
		return false
	if str(Defs.ability(e.id).get("type", "")) == "command":
		# Roll the Felt: every selected Yurtwright heads into the nearest Home Yurt with room
		var any := false
		for u in active_units():
			var yurt := world.construction.free_garrison_near(u)
			if yurt != null:
				_issue_for([u.id], {"type": "enter", "target": yurt.id, "queue": shift})
				any = true
		if not any:
			_deny("cannot_cast")
		return any
	if not e.targeted:
		var caster := _caster_for(e.id, null, Vector3.INF, false)
		if caster == null:
			_deny(world.abilities.cast_error(active_units()[0], e.id, null, false))
			return false
		_issue_for([caster.id], {"type": "cast", "ability": e.id, "queue": shift})
		return true
	_set_targeting(ABILITY_PREFIX + e.id)
	return true


## The selected shop (own faction shop or a neutral one), null when the selection is not one.
func _shop_selected() -> Unit:
	if selection == null or selection.selected.size() != 1:
		return null
	var u: Unit = selection.selected[0]
	return u if u.alive and Defs.shops.has(u.def_id) else null


## Inventory slot pressed (button or numpad): instant items are used at once, targeted ones arm
## targeting ("item:<slot>"; a recall's point picks the hall). False when nothing happened.
func use_item(hero: Unit, slot: int) -> bool:
	if not can_process() or hero == null or hero.player_id != player_id or not hero.alive:
		return false
	if slot < 0 or slot >= hero.inventory.size() or hero.inventory[slot] == null:
		return false
	if not world.items.can_use(hero, slot):
		_deny("cooldown" if world.items.cooldown_left(hero, slot) > 0.0 else "cannot_cast")
		return false
	var d := Defs.item(str(hero.inventory[slot]["id"]))
	if str(d.get("targeting", "instant")) == "instant":
		_issue_raw({"type": "use_item", "player": player_id, "units": [hero.id], "slot": slot})
		return true
	item_hero = hero
	_set_targeting(ITEM_PREFIX + str(slot))
	return true


## Right click on an inventory slot: the next click drops the item on the ground or gives it to
## another own hero.
func begin_move_item(hero: Unit, slot: int) -> void:
	if hero == null or hero.player_id != player_id or slot >= hero.inventory.size() or hero.inventory[slot] == null:
		return
	item_hero = hero
	_set_targeting(MOVE_ITEM_PREFIX + str(slot))


## A targeted item's or a moved item's click.
func _item_click(cmd: String, target: Unit, ground: Vector3, shift: bool) -> bool:
	if item_hero == null or not item_hero.alive:
		return true
	if cmd.begins_with(MOVE_ITEM_PREFIX):
		var slot := int(cmd.trim_prefix(MOVE_ITEM_PREFIX))
		if target != null and target != item_hero and target.is_hero and target.player_id == player_id:
			_issue_raw({"type": "drop_item", "player": player_id, "units": [item_hero.id], "slot": slot, "target": target.id})
			return true
		if ground == Vector3.INF:
			_deny("invalid_target")
			return false
		_issue_raw({"type": "drop_item", "player": player_id, "units": [item_hero.id], "slot": slot, "pos": ground, "queue": shift})
		_marker(ground, Color(1, 0.9, 0.3))
		return true
	var s := int(cmd.trim_prefix(ITEM_PREFIX))
	var cmdd := {"type": "use_item", "player": player_id, "units": [item_hero.id], "slot": s, "queue": shift}
	if target != null and str(Defs.item(str(item_hero.inventory[s]["id"])).get("targeting", "")) == "target_unit":
		cmdd["target"] = target.id
	elif ground != Vector3.INF:
		cmdd["pos"] = ground
	else:
		_deny("invalid_target")
		return false
	_issue_raw(cmdd)
	_marker(ground if ground != Vector3.INF else target.pos, Color(0.5, 0.75, 1.0))
	return true


func _issue_raw(cmd: Dictionary) -> void:
	world.issue(cmd)


## Smart casting: the unit of the active subgroup that can cast `ability_id` now (on `target`),
## nearest to `at`; null when none can.
func _caster_for(ability_id: String, target: Unit, at: Vector3 = Vector3.INF, need_target: bool = true) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in active_units():
		if world.abilities.cast_error(u, ability_id, target, need_target) != "":
			continue
		var d := 0.0 if at == Vector3.INF else Grid.flat_dist(u.pos, at)
		if d < best_d:
			best = u
			best_d = d
	return best


## A targeted ability's click: a unit for unit-target abilities, else the ground point.
func _cast_at(ability_id: String, target: Unit, ground: Vector3, shift: bool) -> bool:
	var us := active_units()
	if us.is_empty():
		return false
	if str(Defs.ability(ability_id).get("type", "")) == "target_unit":
		var caster := _caster_for(ability_id, target, target.pos if target != null else Vector3.INF)
		if caster == null:
			_deny(world.abilities.cast_error(us[0], ability_id, target))
			return false
		_issue_for([caster.id], {"type": "cast", "ability": ability_id, "target": target.id, "queue": shift})
		_marker(target.pos, Color(0.5, 0.75, 1.0))
		return true
	if ground == Vector3.INF:
		_deny("invalid_target")
		return false
	var at := _caster_for(ability_id, null, ground)
	if at == null:
		_deny(world.abilities.cast_error(us[0], ability_id))
		return false
	_issue_for([at.id], {"type": "cast", "ability": ability_id, "pos": ground, "queue": shift})
	_marker(ground, Color(0.5, 0.75, 1.0))
	return true


## Esc: leaves targeting or placement, then a build page, then presses the card's Cancel.
## False when there was nothing to escape.
func escape() -> bool:
	if targeting != "":
		_set_targeting("")
		return true
	if page != CardModel.PAGE_MAIN:
		set_page(CardModel.PAGE_MAIN)
		return true
	var card := current_card()
	if card[CardModel.CANCEL_SLOT] != null:
		return activate_card(CardModel.CANCEL_SLOT)
	return false


## Cancels entry `index` of a building's queue (queue panel click; full refund).
func cancel_queue_slot(building: Unit, index: int) -> void:
	if building != null and can_process():
		_issue_for([building.id], {"type": "cancel", "slot": index})


## The selected building with the shortest queue (ties: selection order), null when none can take
## more (sites, upgrades running).
func _least_busy(units: Array[Unit]) -> Unit:
	var best: Unit = null
	var best_n := 1 << 30
	for b in units:
		if b.under_construction or world.production.is_upgrading(b):
			continue
		var n := world.production.queue_of(b).size()
		if n < best_n:
			best_n = n
			best = b
	return best


# --- targeting -----------------------------------------------------------------------------

## Ground point chosen outside the 3D view (minimap): confirms targeting, else a smart move.
## Placement cannot use the minimap.
func command_ground(ground: Vector3, shift: bool = false) -> void:
	if selection.selected_ids().is_empty() or not can_process():
		return
	if targeting == "place":
		return
	if targeting != "":
		if _issue_ground(targeting, ground, shift) and not shift:
			_set_targeting("")
		return
	_issue({"type": "smart", "pos": ground, "queue": shift})


## True when the selection holds an own mobile unit.
func has_orderable() -> bool:
	if selection == null:
		return false
	for u in selection.selected:
		if u.alive and u.player_id == player_id and u.is_mobile():
			return true
	return false


func cancel_targeting() -> void:
	if targeting != "":
		_set_targeting("")


## Placement mode for building `def_id` (the ghost follows the cursor).
func begin_placement(def_id: String) -> void:
	placing = def_id
	_place_worker = 0
	_set_targeting("place")


func _set_targeting(mode: String) -> void:
	targeting = mode
	if mode != "place":
		placing = ""
	selection.enabled = mode == ""
	Input.set_default_cursor_shape(Input.CURSOR_CROSS if mode != "" and mode != "place" else Input.CURSOR_ARROW)
	if mode == "place":
		if placement == null:
			placement = BuildPlacement.new()
			placement.name = "BuildPlacement"
			world.add_child(placement)
			placement.setup(world, camera, player_id)
		placement.begin(placing)
	elif placement != null:
		placement.end()
	targeting_changed.emit(mode)


func _on_selection_changed(_units: Array) -> void:
	if targeting == "place":
		_set_targeting("")
	set_page(CardModel.PAGE_MAIN)


func _smart(screen_pos: Vector2, shift: bool) -> void:
	if selection.selected_ids().is_empty():
		return
	var target := selection.pick_unit(screen_pos)
	if target != null and not selection.selected.has(target):
		_issue({"type": "smart", "target": target.id, "queue": shift})
		_marker(target.pos, Color(1.0, 0.3, 0.2) if world.is_enemy(player_id, target.player_id) else Color(1, 0.9, 0.3))
		return
	var ground := camera.screen_to_ground(screen_pos)
	if ground == Vector3.INF:
		return
	_issue({"type": "smart", "pos": ground, "queue": shift})
	_marker(ground, Color(0.3, 1.0, 0.35))


## Returns false when the click was denied (the deny sound plays, nothing is issued).
func _issue_targeted(cmd: String, screen_pos: Vector2, shift: bool) -> bool:
	if cmd == "place":
		return _place_at(screen_pos, shift)
	var target := selection.pick_unit(screen_pos)
	if cmd.begins_with(ABILITY_PREFIX):
		return _cast_at(cmd.trim_prefix(ABILITY_PREFIX), target, camera.screen_to_ground(screen_pos), shift)
	if cmd.begins_with(ITEM_PREFIX) or cmd.begins_with(MOVE_ITEM_PREFIX):
		return _item_click(cmd, target, camera.screen_to_ground(screen_pos), shift)
	match cmd:
		"attack_move":
			if target != null and (target.is_invulnerable or target.is_resource or target.is_item):
				_deny("invalid_target")          # "unable to target": Gold Seams, invulnerable units
				return false
			if target != null and world.is_enemy(player_id, target.player_id):
				_issue({"type": "attack", "target": target.id, "queue": shift})
				return true
		"gather":
			if target != null:
				if not target.is_resource:
					_deny("gather_target")
					return false
				_issue_for(_ids(active_units()), {"type": "gather", "target": target.id, "queue": shift})
				_marker(target.pos, Color(1, 0.9, 0.3))
				return true
		"repair":
			var us := active_units()
			if target != null and not us.is_empty() and target.under_construction \
					and target.player_id == player_id:
				_issue_for(_ids(us), {"type": "smart", "target": target.id, "queue": shift})   # help build
				return true
			if target == null or us.is_empty() or not world.construction.can_repair(us[0], target):
				_deny("repair_target")
				return false
			_issue_for(_ids(us), {"type": "repair", "target": target.id, "queue": shift})
			_marker(target.pos, Color(1, 0.9, 0.3))
			return true
		"rally":
			if target != null:
				_issue_for(_ids(active_units()), {"type": "rally", "target": target.id})
				return true
	var ground := camera.screen_to_ground(screen_pos)
	if ground == Vector3.INF:
		_deny("invalid_target")
		return false
	return _issue_ground(cmd, ground, shift)


## A targeted order on a ground point (3D view or minimap). False when denied.
func _issue_ground(cmd: String, ground: Vector3, shift: bool) -> bool:
	if cmd.begins_with(ABILITY_PREFIX):
		return _cast_at(cmd.trim_prefix(ABILITY_PREFIX), null, ground, shift)
	if cmd.begins_with(ITEM_PREFIX) or cmd.begins_with(MOVE_ITEM_PREFIX):
		return _item_click(cmd, null, ground, shift)
	match cmd:
		"gather":
			if world.doodads.nearest_tree(ground, World.TREE_CLICK_RADIUS) < 0:
				_deny("gather_target")
				return false
			_issue_for(_ids(active_units()), {"type": "gather", "pos": ground, "queue": shift})
		"repair":
			_deny("repair_target")
			return false
		"rally":
			_issue_for(_ids(active_units()), {"type": "rally", "pos": ground})
		_:
			_issue({"type": cmd, "pos": ground, "queue": shift})
	_marker(ground, Color(1.0, 0.3, 0.2) if cmd == "attack_move" else Color(0.3, 1.0, 0.35))
	return true


## Placement click: the nearest selected worker (Shift: the same worker again, queued) is sent to
## build at the snapped spot. Refused (kept in placement) when the spot is invalid or the cost
## cannot be met; the ghost shakes.
func _place_at(screen_pos: Vector2, shift: bool) -> bool:
	var ground := camera.screen_to_ground(screen_pos)
	var err := world.tech.can_build(player_id, placing)
	var short := {}
	if err == "":
		var cost: Dictionary = Defs.unit(placing).get("cost", {})
		var p := world.player(player_id)
		if p.gold < int(cost.get("gold", 0)):
			short["gold"] = int(cost.get("gold", 0)) - p.gold
			err = "need_gold"
		if p.lumber < int(cost.get("lumber", 0)):
			short["lumber"] = int(cost.get("lumber", 0)) - p.lumber
			err = "need_lumber" if err == "" else err
	var spot := {}
	if err == "":
		if ground == Vector3.INF:
			err = "cannot_build"
		else:
			spot = world.construction.can_place(player_id, placing, ground)
			if not spot["ok"]:
				err = str(spot["reason"])
	var worker := _builder_for(spot.get("pos", ground), shift) if err == "" else null
	if err == "" and worker == null:
		err = "cannot_build"
	if err != "":
		_deny(err, short)
		if placement != null:
			placement.refuse()
		return false
	_issue_for([worker.id], {"type": "build", "def": placing, "pos": spot["pos"], "queue": shift})
	if placement != null:
		placement.stamp()
	_place_worker = worker.id if shift else 0
	if not shift:
		set_page(CardModel.PAGE_MAIN)
	return true


## The worker that builds at `at`: with Shift the one already chosen this placement, else the
## nearest worker of the active subgroup.
func _builder_for(at: Vector3, shift: bool) -> Unit:
	var us := active_units()
	if shift and _place_worker != 0:
		for u in us:
			if u.id == _place_worker:
				return u
	var best: Unit = null
	var best_d := INF
	for u in us:
		if not u.is_worker:
			continue
		var d := Grid.flat_dist(u.pos, at)
		if d < best_d:
			best_d = d
			best = u
	return best


## A refused press or click: deny sound, `denied` (button and counter shake) and the error line.
func _deny(reason: String, short: Dictionary = {}, slot: int = -1, missing: Array[String] = []) -> void:
	Audio.deny("disabled" if DISABLED_REASONS.has(reason) else "error")
	denied.emit(reason, short, slot)
	var text := Defs.text("error_" + reason) if Defs.strings.has("error_" + reason) else Defs.text("error_cannot_train")
	if text.contains("%s"):
		text = text % ", ".join(missing)
	Events.notification.emit(player_id, "error_" + reason, text)


static func _ids(units: Array[Unit]) -> Array:
	var out: Array = []
	for u in units:
		out.append(u.id)
	return out


func _issue(cmd: Dictionary) -> void:
	_issue_for(selection.selected_ids(), cmd)


func _issue_for(ids: Array, cmd: Dictionary) -> void:
	if ids.is_empty():
		return
	cmd["player"] = player_id
	cmd["units"] = ids
	world.issue(cmd)
	var first := world.get_unit(ids[0])
	if first != null and first.is_mobile():
		Audio.play_voice(first, ack_category(cmd))


## AUD-03: the ack an order asks for: Attack for attack, attack-move and a smart order on an
## enemy; Yes for everything else (move, patrol, stop, hold, follow, build, gather).
func ack_category(cmd: Dictionary) -> String:
	var type := str(cmd.get("type", ""))
	if type in ["attack", "attack_move"]:
		return "attack"
	if type == "smart" and cmd.has("target"):
		var t := world.get_unit(int(cmd["target"]))
		if t != null and world.is_enemy(player_id, t.player_id):
			return "attack"
	return "yes"


## Short-lived shrinking ring where an order was given (visual only). A fallback: when the
## World has its fx runtime, OrderMarkers (src/fx) draws the juiced marks from
## Events.command_issued instead (juice bible CMB-08).
func _marker(p: Vector3, col: Color) -> void:
	if Vfx.instance != null and Vfx.instance.world == world:
		return
	var quad := QuadMesh.new()
	quad.size = Vector2(1.6, 1.6)
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = MARKER_SHADER
	mat.set_shader_parameter("inner", 0.7)
	mat.set_shader_parameter("tint", col)
	var mi := MeshInstance3D.new()
	mi.mesh = quad
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	world.add_child(mi)
	mi.global_position = Vector3(p.x, world.map.height_at(p.x, p.z) + 0.08, p.z)
	var tw := mi.create_tween()
	tw.tween_property(mi, "scale", Vector3(0.2, 1.0, 0.2), 0.45).from(Vector3.ONE)
	tw.tween_callback(mi.queue_free)
