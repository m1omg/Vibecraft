extends "res://tests/test_case.gd"
## Combat orders: attack-move engage + resume, hold position, smart (right-click) resolution,
## chasing with throttled re-paths, leash rules, HUD command card and the scripted battle.

const BattleSetup := preload("res://tests/playtest/battle_setup.gd")


func _order(w: World, units: Array, type: String, extra: Dictionary = {}) -> void:
	var ids: Array = []
	for u: Unit in units:
		ids.append(u.id)
	var cmd := {"type": type, "player": units[0].player_id, "units": ids}
	cmd.merge(extra)
	w.issue(cmd)


func test_attack_move_engages_enemy_then_resumes() -> void:
	var w := make_world()
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 20))
	var victim := w.spawn_unit("dummy_worker", 1, Vector3(30, 0, 24))   # 4 m off the line
	var victim_pos := victim.pos
	var goal := Vector3(52, 0, 20)
	_order(w, [s], "attack_move", {"pos": goal})
	var closest := INF
	var ticks := 0
	for i in 2000:
		w.step()
		ticks += 1
		closest = minf(closest, Grid.flat_dist(s.pos, victim_pos))
		if s.current == null:
			break
	assert_false(victim.alive, "enemy met on the way was killed")
	assert_lt(closest, 1.5, "soldier left its line to fight")
	assert_true(s.current == null, "attack-move completed (%d ticks)" % ticks)
	assert_lt(Grid.flat_dist(s.pos, goal), 0.5, "resumed and reached the destination")


func test_move_ignores_enemies() -> void:
	var w := make_world()
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 20))
	var victim := w.spawn_unit("dummy_worker", 1, Vector3(30, 0, 22))
	_order(w, [s], "move", {"pos": Vector3(52, 0, 20)})
	run_until_idle(w, [s], 900)
	assert_near(victim.hp, victim.max_hp, 0.001, "a plain move never attacks")


func test_hold_attacks_in_range_but_never_chases() -> void:
	var w := make_world()
	var holder := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var bait := w.spawn_unit("dummy_worker", 1, Vector3(25, 0, 20))     # inside acquire, outside range
	_order(w, [holder], "hold")
	w.step()
	var hold_pos := holder.pos
	for i in 120:
		w.step()
	assert_lt(Grid.flat_dist(holder.pos, hold_pos), 0.05, "holding unit did not chase")
	assert_near(bait.hp, bait.max_hp, 0.001, "nothing in range, nothing attacked")
	bait.teleport(hold_pos + Vector3(0.9, 0, 0))
	for i in 90:
		w.step()
	assert_true(bait.hp < bait.max_hp, "enemy inside weapon range is attacked")
	assert_lt(Grid.flat_dist(holder.pos, hold_pos), 0.05, "and the holder stays put")
	bait.teleport(hold_pos + Vector3(5, 0, 0))
	for i in 90:
		w.step()
	assert_lt(Grid.flat_dist(holder.pos, hold_pos), 0.05, "no chase after the enemy stepped away")
	_order(w, [holder], "stop")
	for i in 90:
		w.step()
	assert_true(Grid.flat_dist(holder.pos, hold_pos) > 1.0, "an idle (non-holding) unit does chase")


func test_smart_command_resolution() -> void:
	var w := make_world(flat_map(48, 48))
	var soldier := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var worker := w.spawn_unit("dummy_worker", 0, Vector3(22, 0, 20))
	var ally := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 24))
	var enemy := w.spawn_unit("dummy_soldier", 1, Vector3(70, 0, 70))
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(34, 0, 20))
	var barracks := w.spawn_unit("dummy_barracks", 0, Vector3(20, 0, 40))
	assert_eq(w.resolve_smart(soldier, enemy), Order.Type.ATTACK, "enemy -> attack")
	assert_eq(w.resolve_smart(soldier, null), Order.Type.MOVE, "ground -> move")
	assert_eq(w.resolve_smart(soldier, ally), Order.Type.FOLLOW, "ally -> follow (move with it)")
	assert_eq(w.resolve_smart(worker, mine), Order.Type.GATHER, "worker on resource -> gather")
	assert_eq(w.resolve_smart(soldier, mine), Order.Type.MOVE, "non-worker on resource -> move")
	assert_eq(w.resolve_smart(barracks, null), Order.Type.RALLY, "producing structure -> rally")
	assert_eq(w.resolve_smart(barracks, enemy), Order.Type.RALLY, "rally even onto a unit")
	# through the command path
	_order(w, [soldier], "smart", {"target": enemy.id})
	w.step()
	assert_true(soldier.current != null and soldier.current.type == Order.Type.ATTACK, "smart -> attack order")
	assert_eq(soldier.current.target_id, enemy.id, "attack targets the clicked enemy")
	_order(w, [soldier], "smart", {"pos": Vector3(24, 0, 30)})
	w.step()
	assert_true(soldier.current != null and soldier.current.type == Order.Type.MOVE, "smart ground -> move")
	assert_eq(soldier.current.target_id, 0, "move has no target")
	var rally := Vector3(30, 0, 44)
	_order(w, [barracks], "smart", {"pos": rally})
	w.step()
	assert_eq(barracks.rally_pos, rally, "rally point set")
	assert_true(barracks.current == null, "rally is not a running order")
	var gathered: Array = []
	w.gather_handler = func(wk: Unit, res: Unit) -> void: gathered.append([wk, res])
	_order(w, [worker], "smart", {"target": mine.id})
	w.step()
	assert_true(worker.current != null and worker.current.type == Order.Type.GATHER, "smart -> gather")
	run_until_idle(w, [worker], 300)
	assert_eq(gathered.size(), 1, "economy hook called on arrival")
	if gathered.size() == 1:
		assert_eq(gathered[0][1], mine, "with the clicked mine")
	assert_lt(worker.edge_distance(mine), Unit.GATHER_REACH + 0.01, "worker stands at the mine")


func test_chase_repaths_are_throttled() -> void:
	var w := make_world(flat_map(64, 64))
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var runner := w.spawn_unit("dummy_creep", PlayerState.NEUTRAL_HOSTILE, Vector3(23, 0, 20))
	_order(w, [runner], "move", {"pos": Vector3(100, 0, 60)})
	w.step()
	var q0 := w.pathing.total_queries
	_order(w, [s], "attack", {"target": runner.id})
	for i in 150:
		w.step()
	var queries := w.pathing.total_queries - q0
	assert_true(queries <= 150 / Unit.REPATH_TICKS + 3, "chase path requests throttled (%d)" % queries)
	assert_true(runner.hp < runner.max_hp, "faster attacker caught the moving target")
	assert_true(s.current != null and s.current.type == Order.Type.ATTACK, "explicit attack keeps chasing")


func test_idle_unit_leashes_back_to_guard_position() -> void:
	var w := make_world(flat_map(64, 64))
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 30))
	var start := s.pos
	var runner := w.spawn_unit("dummy_worker", 1, Vector3(26, 0, 30))
	for i in 10:
		w.step()
	assert_eq(s.combat_target_id(), runner.id, "idle soldier auto-acquired the enemy")
	_order(w, [runner], "move", {"pos": Vector3(110, 0, 30)})
	var farthest := 0.0
	for i in 500:
		w.step()
		farthest = maxf(farthest, Grid.flat_dist(s.pos, start))
	assert_true(farthest > 8.0, "chased (%.1f m)" % farthest)
	assert_true(farthest < s.leash_range + 3.0, "gave up at the leash (%.1f m)" % farthest)
	assert_lt(Grid.flat_dist(s.pos, start), 1.0, "walked back to where it stood")
	assert_true(s.current == null and s.combat_target_id() == 0, "idle again")


func test_creeps_wake_together_and_return_to_camp() -> void:
	var w := make_world(flat_map(64, 64))
	var camp: Array = []
	for i in 3:
		camp.append(w.spawn_unit("dummy_creep", PlayerState.NEUTRAL_HOSTILE, Vector3(60, 0, 30 + i * 1.4)))
	var archer := w.spawn_unit("dummy_archer", 0, Vector3(53, 0, 31.4))
	_order(w, [archer], "attack", {"target": camp[1].id})
	for i in 40:
		w.step()
	for c: Unit in camp:
		assert_true(c.combat_target_id() == archer.id, "%s answered the call for help" % c.name)
	_order(w, [archer], "move", {"pos": Vector3(10, 0, 31)})
	for i in 900:
		w.step()
	for c: Unit in camp:
		assert_lt(Grid.flat_dist(c.pos, c._home), 2.5, "%s leashed back to camp" % c.name)
		assert_true(c.combat_target_id() == 0, "%s calm again" % c.name)
	assert_true(archer.alive, "the archer outran the leash")


func test_command_card_button_enters_targeting() -> void:
	Settings.edge_pan_enabled = false
	var main: Node = (load("res://src/main.tscn") as PackedScene).instantiate()
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	var mw: World = main.world
	mw.auto_tick = false
	var sel: Selection = main.selection
	var hud: Hud = main.hud
	var army := mw.units_of_player(0).filter(func(u: Unit) -> bool: return u.is_mobile() and not u.is_worker)
	sel.select_units(army)
	await tree.process_frame
	var card := hud.card
	assert_eq(card.buttons[3].text, "Attack\n[R]", "attack button shows its hotkey")
	assert_false(card.buttons[3].disabled, "enabled with own units selected")
	assert_true(card.buttons[7].disabled, "empty slots disabled")
	var b := card.buttons[3]
	var centre := b.get_global_rect().get_center()
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.position = centre
		ev.global_position = centre
		ev.pressed = pressed
		tree.root.push_input(ev, true)
	assert_eq(main.commands.targeting, "attack_move", "clicking the button enters targeting")
	assert_true(b.button_pressed, "active mode highlighted")
	assert_eq(sel.selected.size(), army.size(), "the click did not reach world selection")
	# a click on the console must not deselect or issue anything either
	main.commands._set_targeting("")
	var panel_point := hud.console.get_global_rect().get_center() + Vector2(0, 40)
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.position = panel_point
		ev.global_position = panel_point
		ev.pressed = pressed
		tree.root.push_input(ev, true)
	assert_eq(sel.selected.size(), army.size(), "HUD click kept the selection")
	assert_true(hud.covers(panel_point), "covers() reports HUD area")
	Settings.edge_pan_enabled = true


func test_hud_shows_selected_unit_stats() -> void:
	var main: Node = (load("res://src/main.tscn") as PackedScene).instantiate()
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	var mw: World = main.world
	mw.auto_tick = false
	var hud: Hud = main.hud
	var p := mw.player(0)
	assert_eq(hud.gold_label.text, "Gold  %d" % p.gold, "gold bound to PlayerState")
	p.gold += 25
	await tree.process_frame
	assert_eq(hud.gold_label.text, "Gold  %d" % p.gold, "gold label follows PlayerState")
	assert_true(hud.food_label.text.begins_with("Food  %d / " % p.food_used), "food shown")
	var archer: Unit = null
	for u in mw.units_of_player(0):
		if u.def_id == "dummy_archer":
			archer = u
			break
	main.selection.select_units([archer])
	await tree.process_frame
	assert_true(hud.name_label.text.contains("Archer"), "name shown")
	assert_true(hud.stats_label.text.contains("Damage  16 - 19  (pierce)"), "damage shown")
	assert_true(hud.stats_label.text.contains("Armor  0  (medium)"), "armor shown")
	main.selection.select_units(mw.units_of_player(0).filter(func(u: Unit) -> bool: return u.is_mobile()))
	await tree.process_frame
	assert_true(hud.grid.visible, "multi-selection grid shown")
	assert_true(hud._icons[1].visible and hud._icons[1].text.length() == 2, "icons carry initials")


func test_scripted_battle_resolves_within_time_limit() -> void:
	var w := make_world(flat_map(64, 48, 1))
	var centre := Vector3(64, 0, 48)
	var sides: Dictionary = BattleSetup.spawn(w, centre)
	BattleSetup.charge(w, sides["army"], centre)
	var limit := int(BattleSetup.TIME_LIMIT_S * World.TICK_RATE)
	var result := ""
	for i in limit:
		w.step()
		result = BattleSetup.winner(sides)
		if result != "":
			break
	print("     battle: %s won after %.1f s (%d soldiers/archers, %d creeps left)" % [result,
		w.time, BattleSetup.alive_count(sides["army"]), BattleSetup.alive_count(sides["creeps"])])
	assert_true(result != "", "one side wins within %d s" % int(BattleSetup.TIME_LIMIT_S))


## Right-clicking an own structure walks there: a FOLLOW on a building never completes, so the
## unit would stay busy forever and never fight back.
func test_smart_on_own_building_is_a_move() -> void:
	var w := make_world(flat_map(48, 48))
	var hall := w.spawn_unit("dummy_hall", 0, Vector3(40, 0, 40))
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 40))
	var ally := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 30))
	assert_eq(w.resolve_smart(s, hall), Order.Type.MOVE, "own building -> move")
	assert_eq(w.resolve_smart(s, ally), Order.Type.FOLLOW, "mobile ally -> follow")
	_order(w, [s], "smart", {"target": hall.id})
	w.step()
	assert_true(s.current != null and s.current.type == Order.Type.MOVE, "a move order")
	var ticks := run_until_idle(w, [s], 300)
	assert_true(s.current == null, "the move completed (%d ticks)" % ticks)
	assert_lt(s.edge_distance(hall), 1.0, "standing at the building")
	var e := w.spawn_unit("dummy_soldier", 1, s.pos + Vector3(-4, 0, 0))
	_order(w, [e], "attack", {"target": s.id})
	for i in 300:
		w.step()
	assert_true(e.hp < e.max_hp, "the idle soldier fought back")


## A follower that is attacked fights back, then resumes following.
func test_follower_fights_back_then_keeps_following() -> void:
	var w := make_world(flat_map(48, 48))
	var leader := w.spawn_unit("dummy_soldier", 0, Vector3(30, 0, 40))
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 40))
	_order(w, [s], "smart", {"target": leader.id})
	for i in 90:
		w.step()
	assert_true(s.current != null and s.current.type == Order.Type.FOLLOW, "following")
	var e := w.spawn_unit("dummy_soldier", 1, s.pos + Vector3(0, 0, -3))
	_order(w, [e], "attack", {"target": s.id})
	for i in 150:
		w.step()
	assert_true(e.hp < e.max_hp, "the follower hit back")
	assert_true(s.current != null and s.current.type == Order.Type.FOLLOW, "still a follow order")
	e.take_damage(e.max_hp * 2.0)
	_order(w, [leader], "move", {"pos": Vector3(70, 0, 70)})
	for i in 360:
		w.step()
	assert_lt(s.edge_distance(leader), 2.5, "back at the leader's side")


## Melee units ignore enemies they cannot walk to: an attack-moving soldier passing an archer
## on an isolated plateau keeps walking (it used to engage, stall at the cliff, give up and
## re-engage on the next arrow until it died).
func test_melee_ignores_unreachable_shooter() -> void:
	var m := flat_map(32, 32)
	for y in range(8, 25):
		for x in range(8, 15):
			m.cliff[m.idx(x, y)] = 1          # plateau without a ramp: x 16..30 m, z 16..50 m
	m.compute_heights()
	var w := make_world(m)
	var archer := w.spawn_unit("dummy_archer", 1, Vector3(28, 0, 33))
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(34, 0, 4))
	var goal := Vector3(34, 0, 62)
	assert_false(w.pathing.same_region(Grid.world_to_cell(s.pos), Grid.world_to_cell(archer.pos)),
		"plateau unreachable")
	_order(w, [s], "attack_move", {"pos": goal})
	var engaged := 0
	for i in 30 * 30:
		w.step()
		if s.combat_target_id() == archer.id:
			engaged += 1
		if s.current == null or not s.alive:
			break
	assert_true(s.alive, "survived the walk")
	assert_true(s.hp < s.max_hp, "it was shot at on the way")
	assert_eq(engaged, 0, "never engaged the unreachable archer")
	assert_lt(Grid.flat_dist(s.pos, goal), 0.5, "reached its goal")


## A target just given up on (unreachable or stuck) is not re-engaged by the next hit.
func test_retaliation_skips_given_up_target() -> void:
	var w := make_world()
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var a := w.spawn_unit("dummy_archer", 1, Vector3(26, 0, 20))
	s._skip_id = a.id
	s._skip_ticks = Unit.SKIP_TICKS
	s._on_attacked(a)
	assert_eq(s.combat_target_id(), 0, "ignored while skipped")
	s._skip_id = 0
	s._on_attacked(a)
	assert_eq(s.combat_target_id(), a.id, "engaged otherwise")


## Structures are acquired by footprint edge distance: a hall's corner reaches further from its
## centre (half-diagonal 3.54 m) than the old fixed query padding allowed.
func test_building_corner_in_range_is_acquired() -> void:
	var w := make_world()
	var hall := w.spawn_unit("dummy_hall", 1, Vector3(30, 0, 30))
	var fp := hall.footprint
	var corner := Vector3(fp.end.x * Grid.CELL, 0, fp.end.y * Grid.CELL)
	var holder := w.spawn_unit("dummy_soldier", 0, corner + Vector3(0.6, 0, 0.6))
	assert_lt(holder.edge_distance(hall), holder.attack_range, "corner within weapon range")
	_order(w, [holder], "hold")
	for i in 120:
		w.step()
	assert_true(hall.hp < hall.max_hp, "hold attacks a building whose corner is in range")
	# an idle unit 7.5 m off the opposite corner (acquire 8 m): centre distance 11.5 m
	var diag := Vector3(1, 0, 1).normalized()
	var near_corner := Vector3(fp.position.x * Grid.CELL, 0, fp.position.y * Grid.CELL)
	var scout := w.spawn_unit("dummy_soldier", 0, near_corner - diag * (7.5 + 0.45))
	assert_near(scout.edge_distance(hall), 7.5, 0.05, "scout 7.5 m from the corner")
	assert_true(scout.find_target(scout.acquire_range) == hall, "idle acquisition sees the corner")
