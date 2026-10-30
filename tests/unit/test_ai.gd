extends "res://tests/test_case.gd"
## The build-order opponent (src/systems/ai/ai_player.gd, rules §19, factions.<id>.ai_opening)
## in the real skirmish against an idle player 0, and the skirmish end rules
## (src/systems/match_rules.gd, rules §17.1, §14.4): defeat with no structures, victory for the
## last team, the cripple countdown and reveal.

var main: Node
var world: World


func _boot(factions: Array[String] = ["kingdom", "clans"]) -> void:
	Settings.edge_pan_enabled = false
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", "slice")
	main.set("player_factions", factions)
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	world = main.world
	world.auto_tick = false


func after_each() -> void:
	Settings.edge_pan_enabled = true
	cleanup()


func _own(pid: int, def_id: String) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == pid and u.def_id == def_id:
			out.append(u)
	return out


## The Tormai computer: altar, a Grapple Yard and its hero inside the opening's times, busy
## workers all along, supply ahead, then a push that wins against an idle base.
func test_clans_ai_opening_push_and_victory() -> void:
	await _boot()
	var ai: AiPlayer = world.ai_players[0]
	var ended: Array = []
	var cb := func(winner: int, reason: String) -> void: ended.append([winner, reason])
	Events.match_ended.connect(cb)
	var idle_since: Dictionary = {}
	var longest_idle := 0.0
	var supply_blocked := 0.0
	var push_at := -1.0
	var checked_3min := false
	for t in 30 * 60 * 11:
		world.step()
		if world.tick_count == 30 * 180:
			checked_3min = true
			assert_eq(_own(1, "clans_naming_stones").size(), 1, "the Naming Stones by 3:00")
			assert_eq(_own(1, "clans_grapple_yard").size(), 1, "a Grapple Yard by 3:00")
			assert_eq(_own(1, "clans_hero_uncut").size(), 1, "the first hero by 3:00")
			assert_true(ai._workers().size() >= 10, "ten workers by 3:00 (%d)" % ai._workers().size())
		if t % 15 != 0:
			continue
		for u in ai._workers():
			if u.current == null and u.orders.is_empty() and not u.hidden:
				if not idle_since.has(u.id):
					idle_since[u.id] = world.time
				longest_idle = maxf(longest_idle, world.time - float(idle_since[u.id]))
			else:
				idle_since.erase(u.id)
		var p := world.player(1)
		if p.food_used >= p.food_cap and p.food_cap < 100:
			supply_blocked += 0.5
		if push_at < 0.0 and ai.state == "push":
			push_at = world.time
		if not ended.is_empty():
			break
	Events.match_ended.disconnect(cb)
	assert_true(checked_3min, "the 3:00 checkpoint ran")
	assert_lt(longest_idle, 20.0, "no worker idles 20 s (longest %.1f s)" % longest_idle)
	assert_lt(supply_blocked, 30.0, "supply kept ahead (blocked %.1f s)" % supply_blocked)
	assert_true(push_at > 0.0 and push_at < 9.5 * 60.0, "the push leaves before 9:30 (%.0f s)" % push_at)
	assert_eq(ended.size(), 1, "the match ended once")
	if not ended.is_empty():
		assert_eq(ended[0][0], 1, "the computer won against an idle base")
		assert_true(world.player(0).defeated, "player 0 defeated")
	assert_eq(world.units_of_player(0).filter(func(u: Unit) -> bool: return u.alive).size(), 0,
		"the defeated player's units are gone")


## The Brennmark computer reaches its push even though its workers and the 50-food upkeep cap
## leave less than the rules' 40 army food (the threshold adapts).
func test_kingdom_ai_reaches_its_push() -> void:
	await _boot(["clans", "kingdom"] as Array[String])
	var ai: AiPlayer = world.ai_players[0]
	for t in 30 * 60 * 9:
		world.step()
		if ai.state == "push":
			break
	assert_eq(ai.state, "push", "pushing by 9:00 (%.0f s)" % world.time)
	assert_true(_own(1, "kingdom_oath_hall").size() == 1 and _own(1, "kingdom_drill_yard").size() == 1,
		"the opening's buildings stand")
	assert_eq(world.tech.tier(1), 2, "the Walled Burg is up")
	assert_true(AiPlayer._food(ai._army()) >= ai.attack_threshold(), "with its army")


func test_defeat_victory_and_cripple_reveal() -> void:
	await _boot()
	var rules: MatchRules = main.match_rules
	var notes: Array = []
	var cb := func(pid: int, kind: String, _t: String) -> void: notes.append([pid, kind])
	Events.notification.connect(cb)
	var ended: Array = []
	var ecb := func(winner: int, _reason: String) -> void: ended.append(winner)
	Events.match_ended.connect(ecb)
	# the cripple: player 0 loses its hall but keeps a Croft
	var croft := world.construction.start_site(0, "kingdom_croft", world.map.start_locations[0] + Vector3(0, 0, -12))
	assert_true(croft != null, "a site counts as a structure")
	var hall: Unit = _own(0, "kingdom_moot_hall")[0]
	hall.take_damage(99999.0, null)
	for i in 30:
		world.step()
	assert_true(notes.has([0, "cripple_started"]), "the countdown starts and the player is told")
	main._process(0.0)
	assert_true(main.objective.visible and (main.objective.text.contains("2:00") or main.objective.text.contains("1:59")),
		"the objective line counts down (%s)" % main.objective.text)
	assert_false(world.player(0).defeated, "a site keeps the player in the match")
	var enemy_sees := func() -> bool: return world.fog.can_see(1, croft)
	assert_false(enemy_sees.call(), "the enemy cannot see the croft yet")
	for i in 30 * 121:
		world.step()
	assert_true(notes.has([0, "cripple_revealed"]), "revealed after 120 s")
	assert_true(enemy_sees.call(), "the enemy now sees our structures")
	main._process(0.0)
	assert_eq(main.objective.text, Defs.text("objective_cripple_revealed"), "and the line says so")
	assert_true(ended.is_empty(), "the match goes on")
	# defeat: the last structure falls
	croft.take_damage(99999.0, null)
	for i in 30:
		world.step()
	Events.notification.disconnect(cb)
	Events.match_ended.disconnect(ecb)
	assert_true(world.player(0).defeated, "no structure left: defeated")
	assert_eq(ended, [1], "the other side wins, once")
	assert_eq(rules.result.get("winner", -2), 1, "recorded")


## The menu's Skirmish setup: the faction and difficulty toggles persist in Settings and the
## match starts with them (the computer takes the other faction).
func test_menu_skirmish_setup_starts_the_match() -> void:
	var keep_faction := Settings.skirmish_faction
	var keep_diff := Settings.ai_difficulty
	Settings.skirmish_faction = "kingdom"
	Settings.ai_difficulty = "normal"
	Settings.edge_pan_enabled = false
	var menu: MainMenu = (load("res://src/ui/main_menu.tscn") as PackedScene).instantiate()
	tree.root.add_child(menu)
	tree.current_scene = menu
	await tree.process_frame
	var faction := menu.buttons["faction"] as Button
	var level := menu.buttons["difficulty"] as Button
	assert_eq(faction.text, Defs.text("menu_play_as") % "Brennmark", "plays Brennmark by default")
	faction.pressed.emit()
	assert_eq(Settings.skirmish_faction, "clans", "the toggle switches to the Tormai")
	assert_eq(faction.text, Defs.text("menu_play_as") % "the Tormai", "and says so")
	level.pressed.emit()
	assert_eq(Settings.ai_difficulty, "hard", "Normal -> Hard")
	menu.start_skirmish()
	for i in 6:
		await tree.process_frame
	var m: Node = tree.current_scene
	assert_true(m is Main, "the skirmish replaced the menu")
	if m is Main:
		track(m)
		(m.world as World).auto_tick = false
		assert_eq(m.scenario, "slice", "the skirmish scenario")
		assert_eq(m.world.player(0).faction, "clans", "we play the Tormai")
		assert_eq(m.world.player(1).faction, "kingdom", "the computer plays Brennmark")
		assert_eq((m.world.ai_players[0] as AiPlayer).difficulty, "hard", "at the chosen difficulty")
		assert_true(m.match_rules != null, "with the end rules")
	tree.current_scene = null
	Settings.skirmish_faction = keep_faction
	Settings.ai_difficulty = keep_diff
	Settings.save_settings()
