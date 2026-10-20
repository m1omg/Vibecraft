extends "res://tests/test_case.gd"
## The M2 system contract: every system installed and registered in its documented stage, the
## effect registry covers every effect id in data, World hooks, the AI install, the Fog stub,
## Economy rules that are already real (upkeep tax, refunds) and the Unit stat pipeline.


func test_systems_installed_in_their_stages() -> void:
	var w := make_world()
	var expected := {&"construction": &"production", &"production": &"production", &"tech": &"production",
		&"abilities": &"abilities", &"buffs": &"abilities", &"items": &"abilities",
		&"economy": &"economy", &"heroes": &"economy", &"shops": &"economy",
		&"creeps": &"creeps", &"fog": &"fog"}
	for prop: StringName in expected:
		var sys: Variant = w.get(prop)
		assert_true(sys is SimSystem, "world.%s is installed" % prop)
		assert_true(w.systems_in(expected[prop]).has(sys), "%s runs in stage %s" % [prop, expected[prop]])
	assert_eq(w.systems_in(&"projectiles")[0], w.combat, "Combat still first in projectiles")
	var order: Array = []
	for row: Array in World.SYSTEM_STAGES:
		order.append(row[0])
	assert_eq(order.size(), 11, "documented system list")
	for cmd: String in World.SYSTEM_COMMANDS:
		assert_true(w.get(World.SYSTEM_COMMANDS[cmd]) is SimSystem, "command %s has a system" % cmd)
		assert_eq(Order.type_from_string(cmd), -1, "%s is not also a unit order" % cmd)
	for i in 5:
		w.step()
	assert_true(w.tick_count == 5, "stub systems tick without errors")


func test_ai_player_installed_for_ai_seats() -> void:
	var w := make_world()
	assert_true(w.ai_players.is_empty(), "no AI for human seats")
	w.add_player(2, 1, "clans", true, "hard")
	assert_eq(w.ai_players.size(), 1, "AI seat gets a brain")
	var ai := w.ai_players[0]
	assert_eq(ai.player_id, 2, "for that player")
	assert_true(w.systems_in(&"ai").has(ai), "registered in the ai stage")
	assert_near(float(ai.tuning().get("think_interval", 0.0)), 0.5, 1e-6, "rules.ai.hard tuning")
	for i in 30:
		w.step()


func test_every_effect_id_resolves_to_a_script() -> void:
	var ids := Defs.effect_ids()
	assert_true(ids.size() >= 30, "abilities and items reference their effects (%d)" % ids.size())
	for id: String in ids:
		assert_true(EffectRegistry.has_effect(id), "effect script for '%s'" % id)
		var e := EffectRegistry.get_effect(id)
		assert_true(e is AbilityEffect, "'%s' extends AbilityEffect" % id)


func test_world_hooks_reach_systems() -> void:
	var w := make_world()
	var hero := w.spawn_unit("clans_hero_skymirror", 0, Vector3(10, 0, 10))
	assert_false(hero.hero.is_empty(), "spawned hook initialised the hero")
	assert_eq(w.player(0).heroes, [hero.id], "and recorded it")
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(30, 0, 30))
	assert_eq(w.economy.gold_left(mine), 12000, "spawned hook gave the seam its gold")
	var hall := w.spawn_unit("clans_shell_hall", 0, Vector3(40, 0, 10))
	w.player(0).gold = 500
	assert_eq(w.production.train(hall, "clans_yurtwright"), 1, "queued")
	hall.die(null)
	w.step()
	assert_true(w.production.queue_of(hall).is_empty(), "died hook cleared the queue")


func test_fog_stub_contract() -> void:
	var w := make_world()
	assert_true(w.fog.is_visible(0, Vector3(5, 0, 5)), "stub: everything visible")
	assert_true(w.fog.is_explored(1, Vector3(5, 0, 5)), "and explored")
	var h := w.fog.reveal(0, Vector3(5, 0, 5), 8.0, 1.0, true)
	assert_true(h > 0, "reveal returns a handle")
	assert_eq(w.fog.reveals().size(), 1, "reveal recorded")
	for i in 31:
		w.step()
	assert_eq(w.fog.reveals().size(), 0, "and expires on time")


func test_economy_income_tax_and_refund() -> void:
	var w := make_world()
	var p := w.player(0)
	p.gold = 0
	p.food_used = 60
	assert_eq(w.economy.upkeep_tier(0), 1, "51-80 food: tier 1")
	assert_eq(w.economy.add_income(0, "gold", 10, "mine"), 7, "70 % kept, floored")
	assert_eq(w.economy.add_income(0, "lumber", 10, "lumber"), 10, "lumber never taxed")
	p.food_used = 90
	assert_eq(w.economy.add_income(0, "gold", 10, "bounty"), 4, "bounty taxed at 40 %")
	assert_eq(p.gold, 11, "credited")
	assert_true(w.economy.spend(0, {"gold": 11}), "spend")
	assert_false(w.economy.spend(0, {"gold": 1}), "cannot overspend")
	w.economy.refund(0, {"gold": 100, "lumber": 40}, 0.75)
	assert_eq(p.gold, 75, "75 % refund floored")
	assert_eq(p.lumber, 40, "lumber refund")
	w.step()
	assert_eq(p.upkeep_tier, 2, "upkeep tier tracked every tick")


func test_unit_modifier_pipeline_and_statuses() -> void:
	var w := make_world()
	var u := w.spawn_unit("kingdom_pavisier", 0, Vector3(10, 0, 10))
	var base_cd := u.cooldown_ticks
	u.set_modifiers(&"tech", {"armor": 2, "damage": 2, "max_hp": 60})
	assert_near(u.armor, 4.0, 1e-6, "armour +2")
	assert_eq(u.damage_min, 14, "flat damage on min")
	assert_eq(u.damage_max, 16, "and max")
	assert_near(u.max_hp, 500.0, 1e-6, "max HP +60")
	assert_near(u.hp, 500.0, 1e-6, "missing HP kept at 0 when the maximum grows")
	u.set_modifiers(&"buffs", {"attack_speed_pct": 30, "move_speed_pct": -40})
	assert_lt(float(u.cooldown_ticks), float(base_cd), "attack speed shortens the cooldown")
	assert_near(u.speed, maxf(2.34, 4.1 * 0.6), 1e-4, "slow applied, clamped at the floor")
	u.set_modifiers(&"buffs", {"status": ["stun"]})
	assert_true(u.stunned, "stun status")
	w.issue({"type": "move", "player": 0, "units": [u.id], "pos": Vector3(30, 0, 10)})
	var start := u.pos
	for i in 20:
		w.step()
	assert_lt(Grid.flat_dist(u.pos, start), 0.01, "a stunned unit does not move")
	u.set_modifiers(&"buffs", {"status": ["cannot_die"]})
	u.take_damage(10000.0, null)
	assert_true(u.alive and u.hp >= 1.0, "cannot_die keeps 1 HP (The Wagon Ring)")
	u.set_modifiers(&"buffs", {})
	assert_false(u.stunned or u.cannot_die, "statuses cleared with their source")
	var b := w.buffs.apply(u, "buff_wind_at_your_back", u, {})
	assert_false(b.is_empty(), "buff applied")
	assert_near(u.speed, 4.1 * 1.2, 1e-4, "buff modifiers reach the unit")
	for i in 40 * World.TICK_RATE + 1:
		w.buffs.sim_tick(w, World.DT)
	assert_false(w.buffs.has_buff(u, "buff_wind_at_your_back"), "expires after its 40 s")
	assert_near(u.speed, 4.1, 1e-4, "and its modifiers go")


func test_towers_shoot_from_place() -> void:
	var w := make_world()
	var tower := w.spawn_unit("clans_bow_mast", 0, Vector3(20, 0, 20))
	var enemy := w.spawn_unit("kingdom_pavisier", 1, Vector3(26, 0, 20))
	var hp := enemy.hp
	var spot := tower.pos
	var yaw := tower.facing
	for i in 90:
		w.step()
	assert_lt(enemy.hp, hp, "a tower acquires and shoots without moving")
	assert_eq(tower.pos, spot, "and never moves")
	assert_eq(tower.facing, yaw, "or rotates")
