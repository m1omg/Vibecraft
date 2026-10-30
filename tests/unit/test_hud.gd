extends "res://tests/test_case.gd"
## The base-building HUD on the real match scene (slice: Brennmark's Moot Hall and five Hodmen,
## fog on), driven with synthetic input: the worker card and its build pages (letters, locks and
## Esc), placing a Croft through the ghost (refused spots, the shortfall), the hall's card
## (train, Shift for five, the queue panel, cancel by slot and by Esc, Grid letters), tooltips,
## the idle-worker button (F8, round robin, Ctrl for all), the error line, gather / rally
## targeting, and the placement grid agreeing with Construction.can_place.

var main: Node
var world: World
var camera: RtsCamera
var sel: Selection
var commands: CommandInput
var hud: Hud


func before_each() -> void:
	Settings.edge_pan_enabled = false
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", "slice")
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	world = main.world
	world.auto_tick = false
	camera = main.camera
	sel = main.selection
	commands = main.commands
	hud = main.hud


func after_each() -> void:
	Settings.edge_pan_enabled = true
	Settings.hotkey_preset = ""
	tree.paused = false
	cleanup()


func _key(key: Key, mods: Dictionary = {}) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.keycode = key
		ev.pressed = pressed
		ev.ctrl_pressed = mods.get("ctrl", false)
		ev.shift_pressed = mods.get("shift", false)
		tree.root.push_input(ev, true)


func _click(pos: Vector2, button: MouseButton = MOUSE_BUTTON_LEFT, mods: Dictionary = {}) -> void:
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = button
		ev.position = pos
		ev.global_position = pos
		ev.pressed = pressed
		ev.shift_pressed = mods.get("shift", false)
		tree.root.push_input(ev, true)


func _own(def_id: String) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.player_id == 0 and u.def_id == def_id and u.alive:
			out.append(u)
	return out


func _screen(p: Vector3) -> Vector2:
	return camera.unproject_position(Vector3(p.x, world.map.height_at(p.x, p.z), p.z))


## A valid, on-screen spot for `def_id` near the start (not under the HUD).
func _free_spot(def_id: String) -> Vector3:
	var start := world.map.start_locations[0]
	var vp := main.get_viewport().get_visible_rect().size
	for r in range(6, 30, 2):
		for k in 16:
			var a := TAU * k / 16.0
			var p := start + Vector3(cos(a), 0, sin(a)) * float(r)
			var s := _screen(p)
			if s.x < 60 or s.y < 60 or s.x > vp.x - 60 or s.y > vp.y - 60 or hud.covers(s):
				continue
			var spot := world.construction.can_place(0, def_id, p)
			if spot["ok"]:
				return spot["pos"]
	return Vector3.INF


func _card_ids() -> Array:
	var out: Array = []
	for e: Variant in commands.current_card():
		out.append((e as CardModel.Entry).id if e != null else "")
	return out


func test_worker_card_and_build_pages() -> void:
	var hod: Unit = _own("kingdom_hodman")[0]
	sel.select_units([hod])
	var card := commands.current_card()
	var ids := _card_ids()
	assert_eq(ids.slice(0, 5), ["move", "stop", "hold", "attack_move", "patrol"], "unit orders on the top row and a half")
	assert_eq((card[5] as CardModel.Entry).id, "build_basic", "Build in slot 5")
	assert_eq((card[5] as CardModel.Entry).key, "B", "on B")
	assert_eq((card[6] as CardModel.Entry).key, "V", "Build Advanced on V")
	assert_eq((card[7] as CardModel.Entry).id, "gather", "Gather on G")
	assert_eq(card[8], null, "no Return Cargo with empty hands")
	assert_eq((card[9] as CardModel.Entry).id, "repair", "Repair on R")
	hod.carry_gold = 10
	assert_eq((commands.current_card()[8] as CardModel.Entry).id, "return", "Return Cargo while carrying")
	hod.carry_gold = 0
	_key(KEY_B)
	assert_eq(commands.page, CardModel.PAGE_BASIC, "B opens the build page")
	ids = _card_ids()
	assert_eq(ids.slice(0, 7), ["kingdom_moot_hall", "kingdom_croft", "kingdom_oath_hall", "kingdom_drill_yard",
		"kingdom_timber_yard", "kingdom_foundry", "kingdom_lookout"], "the faction's basic buildings in data order")
	var lookout: CardModel.Entry = commands.current_card()[6]
	assert_eq(lookout.state, CardModel.State.LOCKED, "the Lookout waits for a Timber Yard")
	assert_eq(lookout.missing, ["Timber Yard"] as Array[String], "and says so")
	assert_eq((commands.current_card()[11] as CardModel.Entry).kind, "back", "Back in slot 11")
	await tree.process_frame
	assert_eq(hud.card.buttons[1].text, "Croft", "the card shows the page")
	_key(KEY_ESCAPE)
	assert_eq(commands.page, CardModel.PAGE_MAIN, "Esc goes back")
	_key(KEY_V)
	var adv: CardModel.Entry = commands.current_card()[0]
	assert_eq(adv.id, "kingdom_collegium", "the advanced page")
	assert_eq(adv.reason, "tier", "the Collegium needs tier 2")
	assert_eq(adv.missing, ["Walled Burg"] as Array[String], "named by the hall it needs")
	_key(KEY_G)
	assert_eq(commands.targeting, "", "G (the locked Collegium) does not start placing")
	sel.select_units([])
	assert_eq(commands.page, CardModel.PAGE_MAIN, "a new selection resets the page")


func test_place_a_croft_with_the_ghost() -> void:
	var hods := _own("kingdom_hodman")
	sel.select_units(hods)
	var spot := _free_spot("kingdom_croft")
	assert_true(spot != Vector3.INF, "an open spot near the hall")
	_key(KEY_B)
	_key(KEY_C)
	assert_eq(commands.targeting, "place", "C enters placement")
	assert_eq(commands.placing, "kingdom_croft", "for a Croft")
	var ghost := commands.placement
	ghost.screen_override = _screen(spot)
	await tree.process_frame
	await tree.process_frame
	assert_true(ghost.visible and ghost.valid, "the ghost is valid there (%s)" % ghost.reason)
	assert_near(Grid.flat_dist(ghost.spot, spot), 0.0, 0.01, "snapped to the footprint grid")
	# a refused spot: on top of the hall
	var errors: Array = []
	var cb := func(pid: int, kind: String, _t: String) -> void:
		if pid == 0:
			errors.append(kind)
	Events.notification.connect(cb)
	var hall: Unit = _own("kingdom_moot_hall")[0]
	_click(_screen(hall.pos))
	assert_eq(commands.targeting, "place", "a refused click keeps placing")
	assert_true(errors.has("error_blocked"), "and explains (%s)" % str(errors))
	var nearest: Unit = null
	for h in hods:
		if nearest == null or Grid.flat_dist(h.pos, spot) < Grid.flat_dist(nearest.pos, spot):
			nearest = h
	_click(_screen(spot))
	Events.notification.disconnect(cb)
	assert_eq(commands.targeting, "", "placed")
	assert_eq(commands.page, CardModel.PAGE_MAIN, "back to the worker's card")
	world.step()
	assert_true(nearest.current != null and nearest.current.type == Order.Type.BUILD, "the nearest Hodman goes to build")
	assert_eq(nearest.current.def_id if nearest.current != null else "", "kingdom_croft", "a Croft")
	var others := 0
	for h in hods:
		if h != nearest and h.current != null and h.current.type == Order.Type.BUILD:
			others += 1
	assert_eq(others, 0, "only one builder")
	await tree.process_frame
	assert_false(ghost.visible, "the ghost is gone")


func test_unaffordable_building_is_refused_with_the_shortfall() -> void:
	sel.select_units([_own("kingdom_hodman")[0]])
	world.player(0).gold = 40
	var got: Array = []
	commands.denied.connect(func(reason: String, short: Dictionary, slot: int) -> void:
		got.append([reason, short, slot]))
	_key(KEY_B)
	_key(KEY_C)
	assert_eq(commands.targeting, "", "no placement without the gold")
	assert_eq(got.size(), 1, "denied once")
	assert_eq(got[0][0], "need_gold", "short of gold")
	assert_eq(got[0][1], {"gold": 55}, "by 55 (95 - 40)")
	assert_eq(got[0][2], 1, "the Croft's button")
	await tree.process_frame
	assert_true(hud.error_line.visible, "the error line shows")
	assert_eq(hud.error_line.text, Defs.text("error_need_gold"), "with the reason")
	await tree.process_frame
	var ghost: Label = hud._ghosts["gold"]
	assert_true(ghost.visible, "the shortfall drops out under the gold counter")
	assert_eq(ghost.text, "-55", "exactly what is missing")


func test_hall_card_train_queue_and_cancel() -> void:
	var hall: Unit = _own("kingdom_moot_hall")[0]
	sel.select_units([hall])
	var card := commands.current_card()
	assert_eq((card[0] as CardModel.Entry).id, "kingdom_hodman", "Hodman in slot 0")
	assert_eq((card[0] as CardModel.Entry).key, "H", "on H")
	var up: CardModel.Entry = card[1]
	assert_eq(up.kind, "upgrade", "the hall upgrade next")
	assert_eq(up.state, CardModel.State.LOCKED, "locked")
	assert_eq(up.missing, ["Oath Hall"] as Array[String], "until there is an Oath Hall")
	assert_eq((card[7] as CardModel.Entry).kind, "rally", "Rally in slot 7")
	assert_eq(card[11], null, "no Cancel with an empty queue")
	var g0 := world.player(0).gold
	_key(KEY_H)
	world.step()
	assert_eq(world.production.queue_of(hall).size(), 1, "H trains a Hodman")
	assert_eq(world.player(0).gold, g0 - 70, "paid")
	_key(KEY_H, {"shift": true})
	world.step()
	assert_eq(world.production.queue_of(hall).size(), 6, "Shift+H queues five more")
	for i in 30:
		world.step()
	await tree.process_frame
	var qp := hud.queue_panel
	assert_true(qp.visible, "the queue panel shows")
	assert_eq(qp.items.size(), 6, "with six slots")
	assert_true(qp.buttons[0].progress > 0.05, "the head's progress bar moves (%.2f)" % qp.buttons[0].progress)
	assert_eq((commands.current_card()[11] as CardModel.Entry).kind, "cancel", "Cancel while something is queued")
	var g1 := world.player(0).gold
	qp.buttons[2].pressed.emit()
	world.step()
	assert_eq(world.production.queue_of(hall).size(), 5, "clicking a slot cancels it")
	assert_eq(world.player(0).gold, g1 + 70, "with a full refund")
	_key(KEY_ESCAPE)
	world.step()
	assert_eq(world.production.queue_of(hall).size(), 4, "Esc cancels the last")
	Settings.hotkey_preset = "grid"
	_key(KEY_Q)
	world.step()
	assert_eq(world.production.queue_of(hall).size(), 5, "Grid: Q is slot 0")


func test_tooltips_cost_shortfall_and_requirements() -> void:
	sel.select_units([_own("kingdom_hodman")[0]])
	world.player(0).gold = 60
	_key(KEY_B)
	var croft: CardModel.Entry = commands.current_card()[1]
	var tip := hud.card_tooltip(croft)
	assert_eq(tip["title"], "Croft", "title")
	assert_eq(tip["key"], "C", "hotkey chip")
	assert_eq(int(tip["cost"]["gold"]), 95, "gold cost")
	assert_eq(int(tip["cost"]["time"]), 38, "build time")
	assert_eq(int(tip["short"]["gold"]), 35, "short by 35")
	assert_true((tip["lines"] as Array).has(Defs.text("tip_gives_food") % 7), "gives 7 food")
	var lookout: CardModel.Entry = commands.current_card()[6]
	tip = hud.card_tooltip(lookout)
	assert_eq(tip["requires"], [Defs.text("tip_requires") % "Timber Yard"], "requirement line")
	# the panel itself: shown after the dwell, docked above the card's top-right corner
	var b := hud.card.buttons[1]
	hud.tooltip.hover(b, tip, hud.card.get_global_rect())
	hud.tooltip._hover_t0 -= 1.0
	await tree.process_frame
	await tree.process_frame
	assert_true(hud.tooltip.visible, "shown after the dwell")
	var r := hud.tooltip.get_global_rect()
	assert_lt(r.end.y, hud.card.get_global_rect().position.y + 0.5, "above the card")
	hud.tooltip.unhover(b)
	hud.tooltip._leave_t0 -= 1.0
	await tree.process_frame
	assert_false(hud.tooltip.visible, "hidden after leaving")


func test_idle_worker_button() -> void:
	var btn := hud.idle_button
	btn.refresh()
	assert_eq(btn.count(), 5, "five idle Hodmen at the start")
	_key(KEY_F8)
	assert_eq(sel.selected.size(), 1, "F8 selects one")
	var first: Unit = sel.selected[0]
	assert_lt(Grid.flat_dist(camera.focus, first.pos), 0.5, "and the camera jumps to it")
	_key(KEY_QUOTELEFT)
	assert_true(sel.selected[0] != first, "` picks the next one")
	_key(KEY_F8, {"ctrl": true})
	assert_eq(sel.selected.size(), 5, "Ctrl+F8 selects every idle worker")
	var mine := world.unit_list.filter(func(u: Unit) -> bool: return u.has_flag("gold_mine"))
	mine.sort_custom(func(a: Unit, b: Unit) -> bool:
		return Grid.flat_dist(a.pos, first.pos) < Grid.flat_dist(b.pos, first.pos))
	world.issue({"type": "gather", "player": 0, "units": [first.id], "target": mine[0].id})
	world.step()
	btn.refresh()
	assert_eq(btn.count(), 4, "a worker with an order is not idle")


func test_gather_and_rally_targeting() -> void:
	var hod: Unit = _own("kingdom_hodman")[0]
	var mine: Unit = null
	for u in world.unit_list:
		if u.has_flag("gold_mine") and (mine == null or Grid.flat_dist(u.pos, hod.pos) < Grid.flat_dist(mine.pos, hod.pos)):
			mine = u
	sel.select_units([hod])
	_key(KEY_G)
	assert_eq(commands.targeting, "gather", "G arms Gather")
	var hall: Unit = _own("kingdom_moot_hall")[0]
	_click(_screen(hall.pos))
	assert_eq(commands.targeting, "gather", "a hall is no resource: refused, still armed")
	_click(_screen(mine.pos + Vector3(0, 1.0, 0)))
	assert_eq(commands.targeting, "", "the seam accepted")
	world.step()
	assert_true(hod.current != null and hod.current.type == Order.Type.GATHER, "gathering")
	sel.select_units([hall])
	_key(KEY_R)
	assert_eq(commands.targeting, "rally", "R arms Rally")
	var spot := hall.pos + Vector3(0, 0, -9)
	_click(_screen(spot))
	world.step()
	assert_lt(Grid.flat_dist(hall.rally_pos, spot), 1.0, "the rally point is set")


func test_cell_states_agree_with_can_place() -> void:
	var start := world.map.start_locations[0]
	var con := world.construction
	var checked := 0
	for x in range(-24, 25, 3):
		for z in range(-24, 25, 3):
			for def_id: String in ["kingdom_croft", "kingdom_moot_hall", "kingdom_lookout"]:
				var p := start + Vector3(x, 0, z)
				var ok: bool = con.can_place(0, def_id, p)["ok"]
				var cs := con.cell_states(0, def_id, p, 2)
				var rect: Rect2i = cs["rect"]
				var outer: Rect2i = cs["outer"]
				var all_ok := true
				for y in rect.size.y:
					for xx in rect.size.x:
						var c := rect.position + Vector2i(xx, y) - outer.position
						if (cs["states"] as PackedByteArray)[c.y * outer.size.x + c.x] != Construction.CELL_OK:
							all_ok = false
				if ok != all_ok:
					fail("%s at %s: can_place %s, cells %s" % [def_id, p, ok, all_ok])
				checked += 1
	assert_true(checked > 500, "checked %d spots" % checked)
