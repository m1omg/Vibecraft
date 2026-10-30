extends "res://tests/test_case.gd"
## The hero HUD on the real match scene (slice, Brennmark): the hero card (Learn while points
## are unspent, the abilities locked until learned), the Learn page (letters, rank gates, Back,
## the last point returning to the main card), the hero bar (slots in acquisition order, "+N",
## click and F1 select, the fallen state, tooltips) and the altar's Revive button.

var main: Node
var world: World
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
	sel = main.selection
	commands = main.commands
	hud = main.hud
	world.player(0).gold = 5000
	world.player(0).lumber = 5000


func after_each() -> void:
	Settings.edge_pan_enabled = true
	Settings.hotkey_preset = ""
	cleanup()


func _key(key: Key) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.keycode = key
		ev.pressed = pressed
		tree.root.push_input(ev, true)


func _hall() -> Unit:
	for u in world.unit_list:
		if u.player_id == 0 and u.def_id == "kingdom_moot_hall":
			return u
	return null


func _hero(def_id: String = "kingdom_wheel_marshal") -> Unit:
	return world.spawn_unit(def_id, 0, _hall().pos + Vector3(8, 0, 6))


func _entry(slot: int) -> CardModel.Entry:
	return commands.current_card()[slot]


func test_hero_card_and_the_learn_page() -> void:
	var hero := _hero()
	sel.select_units([hero])
	var learn := _entry(CardModel.LEARN_SLOT)
	assert_true(learn != null and learn.kind == "page" and learn.id == CardModel.PAGE_LEARN, "Learn in slot 7")
	assert_eq(learn.key, "O", "on O (Classic)")
	var balm := _entry(CardModel.ABILITY_ROW)
	assert_eq(balm.id, "kingdom_linden_balm", "ability 1 on the bottom row")
	assert_eq(balm.state, CardModel.State.LOCKED, "locked until learned")
	assert_eq(int(balm.cost.get("mana", 0)), 80, "with its mana cost")
	_key(KEY_O)
	assert_eq(commands.page, CardModel.PAGE_LEARN, "O opens the Learn page")
	var ult := _entry(CardModel.ABILITY_ROW + 3)
	assert_eq(ult.kind, "learn", "the ultimate's learn button")
	assert_eq(ult.state, CardModel.State.LOCKED, "locked below level 6")
	assert_true(ult.missing.has(Defs.text("tip_hero_level") % 6), "it names the level")
	assert_eq(_entry(CardModel.ABILITY_ROW).state, CardModel.State.READY, "rank 1 of Linden Balm is open")
	assert_eq(_entry(CardModel.LEARN_SLOT).kind, "back", "Back sits where Learn was")
	_key(KEY_L)
	world.step()
	assert_eq(world.heroes.rank_of(hero, "kingdom_linden_balm"), 1, "L learned Linden Balm")
	assert_eq(commands.page, CardModel.PAGE_MAIN, "the last point returns to the main card")
	assert_eq(_entry(CardModel.ABILITY_ROW).state, CardModel.State.READY, "learned: ready")
	assert_eq(_entry(CardModel.LEARN_SLOT), null, "no Learn without points")
	world.heroes.add_xp(hero, 500.0)
	assert_true(_entry(CardModel.LEARN_SLOT) != null, "Learn is back after level-ups")
	_key(KEY_O)
	_key(KEY_ESCAPE)
	assert_eq(commands.page, CardModel.PAGE_MAIN, "Esc leaves the Learn page")
	var tip := hud.card_tooltip(_entry(CardModel.ABILITY_ROW))
	assert_true(str(tip.get("lines", [])).contains(Defs.text("tip_rank") % [1, 3]), "the tooltip shows the rank")


func _click(pos: Vector2) -> void:
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.position = pos
		ev.global_position = pos
		ev.pressed = pressed
		tree.root.push_input(ev, true)


func test_casting_from_the_card() -> void:
	var hero := _hero()
	world.heroes.learn(hero, "kingdom_linden_balm")
	hero.mana = hero.max_mana
	var soldier: Unit = null
	for u in world.unit_list:
		if u.player_id == 0 and u.def_id == "kingdom_hodman":
			soldier = u
			break
	soldier.take_damage(100.0, null)
	sel.select_units([hero])
	assert_eq(_entry(CardModel.ABILITY_ROW).state, CardModel.State.READY, "a learned ability is ready")
	assert_true(_entry(CardModel.ABILITY_ROW).targeted, "Linden Balm needs a target")
	_key(KEY_L)
	assert_eq(commands.targeting, CommandInput.ABILITY_PREFIX + "kingdom_linden_balm", "L arms the cast")
	var hp := soldier.hp
	_click(main.camera.unproject_position(soldier.pos + Vector3(0, 0.8, 0)))
	assert_eq(commands.targeting, "", "the target accepted")
	for i in 60:
		world.step()
	assert_true(soldier.hp > hp + 50.0, "the Hodman was healed")
	var e := _entry(CardModel.ABILITY_ROW)
	assert_eq(e.state, CardModel.State.BUSY, "the button waits for its cooldown")
	assert_true(e.cooldown_left > 3.0 and is_equal_approx(e.cooldown_total, 7.0), "with the sweep's numbers")
	hero.mana = 5.0
	for i in 240:
		world.step()
	hero.mana = 5.0
	assert_eq(_entry(CardModel.ABILITY_ROW).state, CardModel.State.UNAFFORDABLE, "short of mana")
	assert_eq(int(_entry(CardModel.ABILITY_ROW).short.get("mana", 0)), 75, "by 75")


func test_hero_bar_slots_select_and_fallen() -> void:
	var a := _hero()
	var b := _hero("kingdom_firewright")
	var bar := hud.hero_bar
	bar._refresh(0.0)
	assert_true(bar.slots[0].visible and bar.slots[1].visible and not bar.slots[2].visible, "two hero buttons")
	assert_eq(bar.slots[0].hero_id, a.id, "acquisition order")
	assert_eq(bar.slots[0].points, 1, "the +1 pip")
	assert_true(str(bar.tooltip_for(0).get("title", "")).begins_with("Wheel Marshal: "), "Title: Name")
	bar.slots[1].pressed.emit()
	assert_eq(sel.selected, [b] as Array[Unit], "a click selects the hero")
	_key(KEY_F1)
	assert_eq(sel.selected, [a] as Array[Unit], "F1 selects the first hero")
	a.take_damage(999999.0, world.spawn_unit("clans_hero_uncut", 1, a.pos + Vector3(1, 0, 0)))
	world.step()
	bar._refresh(0.0)
	assert_false(bar.slots[0].alive, "the fallen hero greys out")
	assert_eq(bar.slots[0].revive_left, -1.0, "no revive queued yet")
	assert_false(sel.select_hero(0), "a fallen hero cannot be selected")
	assert_true(str(bar.tooltip_for(0).get("lines", [])).contains(Defs.text("hero_revive_hint")), "the tooltip says where to revive")


func test_altar_revive_button() -> void:
	var altar := world.spawn_unit("kingdom_oath_hall", 0, _hall().pos + Vector3(-14, 0, 8))
	var hero := _hero()
	var hid := hero.id
	hero.take_damage(999999.0, world.spawn_unit("clans_hero_uncut", 1, hero.pos + Vector3(1, 0, 0)))
	world.step()
	sel.select_units([altar])
	var e := _entry(0)
	assert_eq(e.kind, "revive", "the dead hero's train button becomes Revive")
	assert_eq(e.uid, hid, "for that hero")
	assert_eq(int(e.cost["gold"]), 170, "at the level-1 price")
	assert_eq(e.state, CardModel.State.READY, "affordable")
	var gold := world.player(0).gold
	_key(KEY_M)
	world.step()
	assert_eq(world.player(0).gold, gold - 170, "M started the revive")
	assert_true(world.production.is_reviving(hid), "queued")
	assert_eq(_entry(0).state, CardModel.State.BUSY, "once")
	hud.hero_bar._refresh(0.0)
	assert_true(hud.hero_bar.slots[0].revive_left > 0.0, "the hero bar shows the timer")
	hud.queue_panel.refresh(altar)
	assert_true(str(hud.queue_panel.tooltip_for(0).get("title", "")).begins_with("Revive "), "the queue says Revive")
