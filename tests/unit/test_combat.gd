extends "res://tests/test_case.gd"
## Combat maths and timing: type table, armor formula, swing timing (damage point, cooldown,
## cancel), projectiles, death/corpse cleanup, seeded determinism and the cost of a big brawl.

var _hits: Array = []


func _record_hit(u: Node, amount: float, src: Node) -> void:
	var w: World = (u as Unit).world
	_hits.append([w.tick_count, (u as Unit).id, amount, (src as Unit).id if src != null else 0])


func before_each() -> void:
	_hits.clear()
	Events.unit_damaged.connect(_record_hit)


func after_each() -> void:
	Events.unit_damaged.disconnect(_record_hit)
	cleanup()


func _attack(w: World, attacker: Unit, target: Unit) -> void:
	w.issue({"type": "attack", "player": attacker.player_id, "units": [attacker.id], "target": target.id})


## World with a given RNG seed (make_world always seeds 1).
func _seeded_world(seed_value: int, m: MapData = null) -> World:
	var w := World.new()
	w.auto_tick = false
	w.visuals = false
	tree.root.add_child(w)
	track(w)
	w.setup(m if m != null else flat_map(), seed_value)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


func test_type_table_multipliers() -> void:
	assert_near(Combat.type_multiplier("blade", "medium"), 1.5, 1e-6, "blade vs medium")
	assert_near(Combat.type_multiplier("blade", "fortified"), 0.7, 1e-6, "blade vs fortified")
	assert_near(Combat.type_multiplier("pierce", "light"), 2.0, 1e-6, "pierce vs light")
	assert_near(Combat.type_multiplier("pierce", "fortified"), 0.35, 1e-6, "pierce vs fortified")
	assert_near(Combat.type_multiplier("pierce", "unarmored"), 1.5, 1e-6, "pierce vs unarmored")
	assert_near(Combat.type_multiplier("siege", "fortified"), 1.5, 1e-6, "siege vs fortified")
	assert_near(Combat.type_multiplier("arcane", "heavy"), 2.0, 1e-6, "arcane vs heavy")
	assert_near(Combat.type_multiplier("hero", "fortified"), 0.5, 1e-6, "hero vs fortified")
	var attack_types: Array = Defs.combat["attack_types"]
	var armor_types: Array = Defs.combat["armor_types"]
	assert_true(attack_types.has("chaos") and armor_types.has("unarmored"), "original type names")
	for at: String in attack_types:
		var row: Dictionary = Defs.combat["types"][at]
		for ar: String in armor_types:
			assert_true(row.has(ar), "table defines %s vs %s" % [at, ar])
	for ar: String in armor_types:
		assert_near(Combat.type_multiplier("chaos", ar), 1.0, 1e-6, "chaos ignores armor type")
	# order of operations: type multiplier, then armor reduction
	assert_near(Combat.compute_damage(20.0, "pierce", "light", 0.0), 40.0, 1e-4, "20 pierce vs light")
	assert_near(Combat.compute_damage(20.0, "blade", "heavy", 5.0), 20.0 * (1.0 - 0.3 / 1.3), 1e-4,
		"20 blade vs 5 heavy armor")


func test_armor_formula_positive_and_negative() -> void:
	assert_near(Combat.armor_factor(0.0), 1.0, 1e-6, "no armor")
	assert_near(1.0 - Combat.armor_factor(1.0), 0.0566, 1e-3, "armor 1 reduces ~5.7 %")
	assert_near(1.0 - Combat.armor_factor(5.0), 0.2308, 1e-3, "armor 5 reduces ~23 %")
	assert_near(1.0 - Combat.armor_factor(10.0), 0.375, 1e-4, "armor 10 reduces 37.5 %")
	assert_near(Combat.armor_factor(-10.0), 2.0 - pow(0.94, 10.0), 1e-6, "negative armor formula")
	assert_near(Combat.armor_factor(-10.0), 1.4614, 1e-3, "armor -10 takes ~46 % more")
	var prev := INF
	for a in range(-20, 31):
		var f := Combat.armor_factor(float(a))
		assert_true(f < prev, "factor decreases with armor (a=%d)" % a)
		prev = f
	assert_near(Combat.armor_factor(-0.0001), Combat.armor_factor(0.0), 1e-3, "continuous at zero")


## The swing starts the tick the order applies; damage lands exactly damage_point ticks later
## and the next swing starts cooldown ticks after the previous one.
func test_damage_point_and_cooldown_timing() -> void:
	var w := make_world()
	var a := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var victim := w.spawn_unit("dummy_worker", 1, Vector3(10, 0, 9.0))   # straight ahead (-Z)
	_attack(w, a, victim)
	for i in 100:
		w.step()
	assert_true(_hits.size() >= 3, "three swings landed (%d)" % _hits.size())
	if _hits.size() < 3:
		return
	var start := 1
	assert_eq(_hits[0][0], start + a.damage_point_ticks, "first hit at the damage point")
	assert_eq(_hits[1][0], start + a.cooldown_ticks + a.damage_point_ticks, "second hit one cooldown later")
	assert_eq(_hits[2][0], start + 2 * a.cooldown_ticks + a.damage_point_ticks, "third hit")
	for h: Array in _hits:
		var amount: float = h[2]
		assert_true(amount >= 11.0 * 1.5 - 1e-4 and amount <= 14.0 * 1.5 + 1e-4,
			"blade vs medium within roll range (%f)" % amount)
	assert_near(victim.hp, victim.max_hp - (_hits[0][2] + _hits[1][2] + _hits[2][2]), 1e-3, "hp bookkeeping")


func test_interrupt_before_damage_point_cancels_swing() -> void:
	var w := make_world()
	var a := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var victim := w.spawn_unit("dummy_worker", 1, Vector3(10, 0, 9.0))
	_attack(w, a, victim)
	for i in a.damage_point_ticks - 3:
		w.step()
	assert_true(a.swing_progress() >= 0.0, "swinging")
	w.issue({"type": "stop", "player": 0, "units": [a.id]})
	w.issue({"type": "hold", "player": 0, "units": [a.id]})
	w.step()
	var hold_tick := w.tick_count
	for i in 3:
		w.step()
	assert_eq(_hits.size(), 0, "no damage from the cancelled wind-up")
	# hold re-acquires the adjacent enemy; the cooldown was refunded so it swings right away
	for i in 60:
		w.step()
		if not _hits.is_empty():
			break
	assert_eq(_hits.size(), 1, "attacks again after the cancel")
	if not _hits.is_empty():
		assert_true(_hits[0][0] - hold_tick <= a.damage_point_ticks + Unit.SCAN_TICKS,
			"no cooldown penalty after a cancelled swing (%d ticks)" % (_hits[0][0] - hold_tick))


func test_ranged_attack_launches_homing_projectile() -> void:
	var w := make_world()
	var archer := w.spawn_unit("dummy_archer", 0, Vector3(10, 0, 12))
	var victim := w.spawn_unit("dummy_worker", 1, Vector3(10, 0, 6))
	_attack(w, archer, victim)
	var launched_at := -1
	var peak := -INF
	var start_y := 0.0
	for i in 60:
		w.step()
		if launched_at < 0 and w.combat.projectiles.size() > 0:
			launched_at = w.tick_count
			start_y = w.combat.projectiles[0].pos.y
		if w.combat.projectiles.size() > 0:
			peak = maxf(peak, w.combat.projectiles[0].pos.y)
		if not _hits.is_empty():
			break
	assert_eq(launched_at, 1 + archer.damage_point_ticks, "projectile released at the damage point")
	assert_eq(_hits.size(), 1, "projectile hit")
	if _hits.is_empty():
		return
	var dist := Grid.flat_dist(archer.pos, victim.pos)
	var flight := float(_hits[0][0] - launched_at)
	var expected := dist / float(archer.projectile["speed"]) * World.TICK_RATE
	assert_near(flight, expected, 2.0, "flight time matches speed")
	assert_true(peak > start_y + 0.1, "projectile arcs (peak %.2f vs launch %.2f)" % [peak, start_y])
	assert_eq(w.combat.projectiles.size(), 0, "projectile removed on impact")
	assert_eq(_hits[0][3], archer.id, "damage credited to the archer")


func test_projectile_follows_moving_target() -> void:
	var w := make_world()
	var archer := w.spawn_unit("dummy_archer", 0, Vector3(10, 0, 20))
	var runner := w.spawn_unit("dummy_worker", 1, Vector3(17, 0, 20))
	_attack(w, archer, runner)
	for i in 30:
		w.step()
		if not w.combat.projectiles.is_empty():
			break
	assert_eq(w.combat.projectiles.size(), 1, "in flight (archer turned, then released)")
	w.issue({"type": "move", "player": 1, "units": [runner.id], "pos": Vector3(17, 0, 30)})
	for i in 40:
		w.step()
		if not _hits.is_empty():
			break
	assert_eq(_hits.size(), 1, "homing projectile still hits the moving target")


func test_death_frees_footprint_and_corpse_decays() -> void:
	var w := make_world()
	var died: Array = []
	var on_died := func(u: Node, _k: Node) -> void: died.append(u)
	Events.unit_died.connect(on_died)
	var hall := w.spawn_unit("dummy_hall", 1, Vector3(20, 0, 20))
	var cell := Grid.world_to_cell(hall.pos)
	assert_false(w.pathing.is_walkable(cell), "footprint blocks pathing")
	assert_eq(w.player(1).food_cap, 12, "hall provides food")
	hall.take_damage(hall.max_hp + 1.0)
	assert_false(hall.alive, "dead at 0 hp")
	assert_true(w.get_unit(hall.id) != null, "removal deferred to cleanup")
	w.step()
	Events.unit_died.disconnect(on_died)
	assert_eq(died.size(), 1, "unit_died emitted once")
	assert_true(w.get_unit(hall.id) == null, "out of the id table")
	assert_false(w.unit_list.has(hall), "out of the unit list")
	assert_true(w.pathing.is_walkable(cell), "footprint freed")
	assert_eq(w.player(1).food_cap, 0, "food released")
	assert_eq(w.corpse_count(), 1, "corpse kept for the death animation")
	for i in hall.decay_ticks():
		w.step()
	assert_eq(w.corpse_count(), 0, "corpse removed after decay")


func test_killing_blow_and_retargeting() -> void:
	var w := make_world()
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var a := w.spawn_unit("dummy_worker", 1, Vector3(20, 0, 19))
	var b := w.spawn_unit("dummy_worker", 1, Vector3(22.5, 0, 20))
	for i in 1400:
		w.step()
		if not a.alive and not b.alive:
			break
	assert_false(a.alive, "idle soldier auto-acquired and killed the first worker")
	assert_false(b.alive, "then acquired the next one")


## Full visual world (world.tscn: terrain, unit views, Vfx, projectile meshes), manual ticks.
func _visual_world(seed_value: int) -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(flat_map(), seed_value)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


func _brawl_log(seed_value: int, visual_frames: Array = []) -> Array:
	_hits.clear()
	var w := _visual_world(seed_value) if not visual_frames.is_empty() else _seeded_world(seed_value)
	var army: Array = []
	for i in 3:
		army.append(w.spawn_unit("dummy_soldier", 0, Vector3(14, 0, 18 + i * 1.2)))
	for i in 2:
		army.append(w.spawn_unit("dummy_archer", 0, Vector3(11, 0, 18.5 + i * 1.3)))
	for i in 4:
		w.spawn_unit("dummy_creep", PlayerState.NEUTRAL_HOSTILE, Vector3(24, 0, 17.5 + i * 1.4))
	var ids: Array = army.map(func(u: Unit) -> int: return u.id)
	w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": Vector3(30, 0, 19)})
	for i in 450:
		w.step()
		if not visual_frames.is_empty():
			for f in int(visual_frames[i % visual_frames.size()]):
				await tree.process_frame
	var out := _hits.duplicate(true)
	return out


func test_seeded_damage_rolls_are_deterministic() -> void:
	var a: Array = await _brawl_log(42)
	var b: Array = await _brawl_log(42)
	var c: Array = await _brawl_log(7)
	assert_true(a.size() > 20, "a real fight happened (%d hits)" % a.size())
	assert_eq(a, b, "same seed, same hits (tick, victim, amount, source)")
	assert_true(a != c, "a different seed rolls different damage")


## The same fight with views, Vfx (floating text, flashes) and projectile meshes running and
## 0-3 render frames between ticks must produce exactly the headless result.
func test_combat_is_refresh_rate_independent() -> void:
	var headless: Array = await _brawl_log(42)
	var rendered: Array = await _brawl_log(42, [0, 2, 1, 3])
	assert_true(headless.size() > 20, "fight happened")
	assert_eq(rendered, headless, "identical hits with visuals and uneven frame pacing")


@warning_ignore("integer_division")
func test_200_unit_brawl_tick_cost() -> void:
	var w := make_world(flat_map(64, 64, 0))
	var sides: Array = [[], []]
	for i in 200:
		var row := (i % 100) / 10
		var col := i % 10
		var side := i / 100
		var x := 40.0 + side * 28.0 + row * 1.2
		var u := w.spawn_unit("dummy_soldier" if col % 3 else "dummy_archer", side, Vector3(x, 0, 52 + col * 1.2))
		sides[side].append(u.id)
	w.issue({"type": "attack_move", "player": 0, "units": sides[0], "pos": Vector3(90, 0, 58)})
	w.issue({"type": "attack_move", "player": 1, "units": sides[1], "pos": Vector3(30, 0, 58)})
	for i in 60:
		w.step()
	var t0 := Time.get_ticks_usec()
	for i in 150:
		w.step()
	var per_tick := (Time.get_ticks_usec() - t0) / 150.0 / 1000.0
	print("     200-unit brawl: %.2f ms per tick, %d hits, %d dead" % [per_tick, _hits.size(), w.corpse_count()])
	assert_true(_hits.size() > 100, "armies engaged (%d hits)" % _hits.size())
	assert_lt(per_tick, 1000.0 / 30.0, "200 fighting units fit in one 30 Hz tick")
