extends "res://tests/test_case.gd"
## Playtest 1, the Battlefield sandbox (data/scenarios.json "battlefield", src/scenarios/
## battlefield.gd, main.gd scenario "battlefield"): set-up from data, the scripted Tormai guard
## and war-band, 3 sim-minutes in the real main scene (wave, combat resolves, no script errors),
## annihilation victory / defeat with the end banner, the main menu and the pause menu Restart.

const SCENARIO := "battlefield"
const BUSY_TICKS := 5400             ## 3 sim-minutes

var _ended: Array = []


## Headless world (no visuals) on the scenario's map with the scenario's players and set-up.
func _headless() -> Array:
	var sc := Defs.scenario(SCENARIO)
	var m := MapData.load_json("res://data/maps/%s.json" % str(sc["map"]))
	var w := World.new()
	w.auto_tick = false
	w.visuals = false
	tree.root.add_child(w)
	track(w)
	w.setup(m, 1337)
	BattlefieldScenario.add_players(w, SCENARIO)
	var b := BattlefieldScenario.new()
	w.systems_root.add_child(b)
	b.setup_match(w, SCENARIO)
	return [w, b]


func _count(w: World, pid: int, def_id: String) -> int:
	var n := 0
	for u in w.unit_list:
		if u.alive and u.player_id == pid and u.def_id == def_id:
			n += 1
	return n


func _main() -> Node:
	Settings.edge_pan_enabled = false
	var main: Node = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", SCENARIO)
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	(main.world as World).auto_tick = false
	return main


func after_each() -> void:
	Settings.edge_pan_enabled = true
	tree.paused = false
	if Events.match_ended.is_connected(_on_ended):
		Events.match_ended.disconnect(_on_ended)
	_ended.clear()
	cleanup()


func _on_ended(winner: int, reason: String) -> void:
	_ended.append([winner, reason])


## Every group and structure of the data is on the map, structures on legal ground without
## overlapping, heroes at the scenario level, and only the listed camps.
func test_setup_follows_the_data() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	var sc := Defs.scenario(SCENARIO)
	for p: Dictionary in sc["players"]:
		var pid := int(p["slot"])
		var want := {}
		for s: Dictionary in p["structures"]:
			want[s["def"]] = int(want.get(s["def"], 0)) + 1
		for g: Dictionary in p["groups"]:
			for pair: Array in g["units"]:
				want[pair[0]] = int(want.get(pair[0], 0)) + int(pair[1])
		for def_id: String in want:
			assert_eq(_count(w, pid, def_id), int(want[def_id]), "player %d %s" % [pid, def_id])
		assert_eq(w.player(pid).faction, str(p["faction"]), "faction of slot %d" % pid)
	# the roster the playtest brief asks for
	assert_eq(_count(w, 0, "kingdom_pavisier"), 6, "6 Pavisiers")
	assert_eq(_count(w, 0, "kingdom_hookgunner"), 4, "4 Hookgunners")
	assert_eq(_count(w, 0, "kingdom_linden_sister"), 2, "2 Linden Sisters")
	assert_eq(_count(w, 0, "kingdom_bombard_wagon"), 1, "1 Bombard Wagon")
	assert_eq(_count(w, 0, "kingdom_wheel_marshal") + _count(w, 0, "kingdom_firewright"), 2, "both heroes")
	assert_eq(_count(w, 0, "kingdom_hodman"), 5, "5 Hodmen")
	var rects: Array[Rect2i] = []
	for sid in b.structures:
		var s := w.get_unit(sid)
		assert_true(s != null and s.alive and not s.under_construction, "structure finished")
		for other in rects:
			assert_false(other.intersects(s.footprint), "%s overlaps another structure" % s.def_id)
		rects.append(s.footprint)
		assert_lt(Grid.flat_dist(s.pos, Vector3.ZERO), 1000.0)
	var listed_structures := 0
	for p: Dictionary in sc["players"]:
		listed_structures += (p["structures"] as Array).size()
	assert_eq(rects.size(), listed_structures, "every listed structure placed")
	for pid in 2:
		var ps := w.player(pid)
		assert_true(ps.food_used <= ps.food_cap, "player %d army fits its supply (%d / %d)" % [pid, ps.food_used, ps.food_cap])
	for u in w.unit_list:
		if u.is_hero:
			assert_eq(u.level, int(sc["hero_level"]), "%s level" % u.def_id)
			assert_eq(u.hp, u.max_hp, "%s at full HP" % u.def_id)
			assert_true(u.max_hp > float(Defs.unit(u.def_id)["hp"]), "%s stronger than level 1" % u.def_id)
		if u.is_mobile() and u.player_id < PlayerState.NEUTRAL_HOSTILE:
			assert_true(w.pathing.is_walkable_world(u.pos, u.is_large()) or w.pathing.is_walkable_world(u.pos),
				"%s stands on walkable ground" % u.def_id)
	var camps: Array = w.creeps.camps().keys()
	camps.sort()
	var listed: Array = (sc["camps"] as Array).duplicate()
	listed.sort()
	assert_eq(camps, listed, "only the listed creep camps")
	assert_true(b.entity_count(PlayerState.NEUTRAL_HOSTILE) > 0, "creeps spawned")
	assert_true(w.player(1).is_ai and w.ai_players.is_empty(), "the scenario plays the Tormai, no AiPlayer")
	assert_near(b.wave_eta(), float(sc["players"][1]["groups"][1]["attack_after"]), 0.05, "wave timer")


## Before the timer the war-band waits; at attack_after it attack-moves at the player's hall and
## the player is told (notification + Space alert).
func test_wave_marches_after_the_timer() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	var notes: Array = []
	var cb := func(pid: int, kind: String, _text: String) -> void: notes.append([pid, kind])
	Events.notification.connect(cb)
	var wave := b.group("warband", 1)
	var start := BattlefieldScenario._centre(b.members(wave))
	var attack_tick := int(wave["attack_tick"])
	while w.tick_count < attack_tick - 1:
		w.step()
	assert_false(wave["launched"], "still waiting one tick before the timer")
	assert_lt(Grid.flat_dist(BattlefieldScenario._centre(b.members(wave)), start), 1.0, "the war-band holds its spot")
	for i in 20:
		w.step()
	Events.notification.disconnect(cb)
	assert_true(wave["launched"], "launched at the timer")
	assert_true(notes.has([0, "wave"]), "the player is warned")
	for u in b.members(wave):
		assert_true(u.current != null and u.current.type == Order.Type.ATTACK_MOVE, "%s attack-moving" % u.def_id)
		var hall := w.get_unit(b.structures[0])
		assert_lt(Grid.flat_dist(u.current.target_pos, hall.pos), 6.0, "heading for the hall")


## Player units that walk up to the Tormai base are met by the guard group.
func test_guards_defend_their_base() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	var guard := b.group("guard", 1)
	var post: Vector3 = guard["post"]
	var army: Array[Unit] = b.members(b.group("army", 0))
	var raider: Unit = army[0]
	raider.teleport(post + Vector3(-14.0, 0.0, 10.0))
	w.issue({"type": "hold", "player": 0, "units": [raider.id]})
	for i in 30:
		w.step()
	var responding := 0
	for u in b.members(guard):
		if u.current != null and u.current.type == Order.Type.ATTACK_MOVE or u.combat_target_id() == raider.id:
			responding += 1
	assert_eq(responding, b.members(guard).size(), "every guard answers the intruder")
	for i in 600:
		w.step()
		if not raider.alive:
			break
	assert_false(raider.alive, "the lone raider is cut down")
	for i in 900:
		w.step()
	for u in b.members(guard):
		var i := (guard["units"] as Array).find(u.id)
		assert_lt(Grid.flat_dist(u.pos, guard["slots"][i]), BattlefieldScenario.POST_EPS + 1.5, "%s back at its post" % u.def_id)


## Creep camps fight back: hit one creep and its camp mates join in.
func test_creeps_fight_back() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	var camp_id := str((Defs.scenario(SCENARIO)["camps"] as Array)[1])
	var creeps := w.creeps.camp_members(camp_id)
	assert_true(creeps.size() >= 3, "camp %s spawned" % camp_id)
	var gunner: Unit = null
	for u in b.members(b.group("army", 0)):
		if u.def_id == "kingdom_hookgunner":
			gunner = u
			break
	gunner.teleport(creeps[0].pos + Vector3(0.0, 0.0, -7.5))
	w.issue({"type": "attack", "player": 0, "units": [gunner.id], "target": creeps[0].id})
	var engaged := 0
	for i in 150:
		w.step()
	for c in creeps:
		if c.alive and c.combat_target_id() == gunner.id:
			engaged += 1
	assert_true(engaged >= 2, "the camp answers together (%d engaged)" % engaged)
	assert_lt(gunner.hp, gunner.max_hp, "the creeps hit back")


## A player reduced to buildings and workers cannot fight back (no production here): the Tormai
## guards leave their post and go to finish it.
func test_guards_hunt_a_defenceless_player() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	for u in w.units_of_player(0):
		if u.is_mobile() and not u.is_worker:
			u.take_damage(u.hp + 1.0)
	for i in 30:
		w.step()
	var guard := b.group("guard", 1)
	var hall := w.get_unit(b.structures[0])
	for u in b.members(guard):
		assert_true(u.current != null and u.current.type == Order.Type.ATTACK_MOVE, "%s on the hunt" % u.def_id)
		assert_lt(Grid.flat_dist(u.current.target_pos, hall.pos), 40.0, "%s heads for the Brennish base" % u.def_id)


## Losing everything is a defeat: the result names the Tormai and the match ends once.
func test_annihilation_defeat() -> void:
	var r := _headless()
	var w: World = r[0]
	var b: BattlefieldScenario = r[1]
	Events.match_ended.connect(_on_ended)
	for u in w.units_of_player(0):
		u.take_damage(u.hp + 1.0)
	for i in 20:
		w.step()
	assert_true(b.is_over(), "decided")
	assert_eq(int(b.result["winner"]), 1, "the Tormai win")
	assert_true(w.player(0).defeated, "player 0 defeated")
	assert_eq(_ended.size(), 1, "match_ended once")
	assert_eq(_ended[0], [1, "annihilation"], "winner and reason")


## The task's headless check: the real main scene (HUD, views, fx), 3 sim-minutes with the
## war-band attack, no script errors (the runner fails on any), and the fight resolves: the
## war-band is wiped out at the player's base, both sides lost units, the player's hall stands.
## Then the remaining Tormai are destroyed: victory banner with Play again.
func test_three_minutes_of_battle_then_victory() -> void:
	var main: Node = await _main()
	var w: World = main.world
	var b: BattlefieldScenario = main.battle
	assert_true(b != null, "battlefield scenario booted")
	assert_true(main.objective.visible, "objective line shown")
	var wave := b.group("warband", 1)
	var p0_start := b.entity_count(0)
	var p1_start := b.entity_count(1)
	# the card offers unit orders for units, not for a building alone
	var sel: Selection = main.selection
	var card: CommandCard = main.hud.card
	sel.select_units([w.get_unit(b.structures[0])])
	assert_true(card.buttons[0].disabled and card.buttons[3].disabled, "no unit orders for the hall")
	sel.select_units(b.members(b.group("army", 0)))
	assert_false(card.buttons[3].disabled, "unit orders for the army")
	assert_eq(card.buttons[3].text, "Attack\n[A]", "Attack shows its key")
	var camera: RtsCamera = main.camera
	var spaced := false
	for i in BUSY_TICKS:
		w.step()
		if i % 60 == 0:
			await tree.process_frame        # views, HUD and fx run their _process too
		if not spaced and wave["launched"]:
			spaced = true
			await tree.process_frame
			camera.jump_to(Vector3(96, 0, 96))
			var ev := InputEventKey.new()
			ev.physical_keycode = KEY_SPACE
			ev.keycode = KEY_SPACE
			ev.pressed = true
			tree.root.push_input(ev, true)
			ev = ev.duplicate()
			ev.pressed = false
			tree.root.push_input(ev, true)
			assert_lt(Grid.flat_dist(camera.focus, BattlefieldScenario._centre(b.members(wave))), 8.0,
				"Space jumps to the war-band alert")
			assert_eq(main.hud.notice.text, Defs.text("notify_warband_marching"), "the HUD shows the warning")
	assert_true(wave["launched"], "the war-band marched")
	assert_eq(b.members(wave).size(), 0, "the war-band was destroyed within 3 minutes")
	assert_lt(b.entity_count(1), p1_start, "the Tormai lost units")
	assert_lt(b.entity_count(0), p0_start, "the war-band drew blood before it fell")
	var hall := w.get_unit(b.structures[0])
	assert_true(hall != null and hall.alive, "the player's hall still stands")
	assert_false(b.is_over(), "not decided yet: the Tormai base stands")
	assert_true(main.losses.get(1, 0) >= 8, "the HUD tallies the losses")
	# raze the rest: victory
	for u in w.units_of_player(1):
		u.take_damage(u.hp + 1.0, null)
	for i in 20:
		w.step()
	await tree.process_frame
	assert_true(b.is_over(), "decided")
	assert_eq(int(b.result["winner"]), 0, "Brennmark wins")
	var banner: EndBanner = main.end_banner
	assert_true(banner.visible, "end banner shown")
	assert_eq(banner.kind, "victory", "victory banner")
	assert_eq(banner.title.text, Defs.text("end_victory"))
	assert_true(banner.play_again.visible and not banner.play_again.disabled, "Play again offered")
	banner.finish_fade()
	await tree.process_frame
	# F10 does nothing over the banner
	Events.menu_requested.emit()
	assert_false(tree.paused, "no pause menu over the end banner")


## The main menu's "Battlefield Sandbox" swaps in the match; the pause menu's Restart swaps in
## a fresh one.
func test_menu_starts_the_battlefield_and_restart_reloads() -> void:
	Settings.edge_pan_enabled = false
	var menu: Node = (load("res://src/ui/main_menu.tscn") as PackedScene).instantiate()
	tree.root.add_child(menu)
	tree.current_scene = menu
	await tree.process_frame
	assert_true((menu as MainMenu).buttons.has("battlefield"), "Battlefield Sandbox button")
	assert_eq(((menu as MainMenu).buttons["battlefield"] as Button).text, Defs.text("menu_battlefield"))
	assert_true((menu as MainMenu).buttons.has("quit"), "Quit button")
	(menu as MainMenu).start_battlefield()
	for i in 6:
		await tree.process_frame
	var main: Node = tree.current_scene
	assert_true(main is Main, "the match replaced the menu")
	if not main is Main:
		return
	track(main)
	assert_false(is_instance_valid(menu), "menu freed")
	assert_eq(main.scenario, SCENARIO, "battlefield scenario")
	(main.world as World).auto_tick = false
	Events.menu_requested.emit()
	assert_true(tree.paused and main.pause_menu.visible, "F10 / menu button opens the pause menu")
	(main.pause_menu.buttons["restart"] as Button).pressed.emit()
	for i in 4:
		await tree.process_frame
	assert_false(tree.paused, "restart unpauses")
	var fresh: Node = tree.current_scene
	assert_true(fresh is Main and fresh != main, "a fresh match")
	if fresh is Main:
		track(fresh)
		(fresh.world as World).auto_tick = false
		assert_eq(fresh.scenario, SCENARIO, "same scenario")
		assert_lt(fresh.world.tick_count, 60, "from the start (a few physics ticks at most)")
		assert_true(fresh.battle != null and fresh.battle.wave_eta() > 85.0, "the wave timer restarted")
	tree.current_scene = null
