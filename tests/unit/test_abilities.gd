extends "res://tests/test_case.gd"
## The cast pipeline (src/systems/abilities.gd, orders/cast.gd; rules §6.5, §10): approach to
## range, nothing spent before the cast point, mana and cooldown spent at it, the backswing cut by
## a new order, a stun cancelling the wind-up at no cost, silence and bad targets refused, auras
## and passives from learned ranks; plus regeneration, the damage pipeline and buff rules
## (refresh, highest rank, hero control durations, periodic damage, breaks, dispel).


func _world() -> World:
	var w := make_world(flat_map(48, 48))
	w.player(0).faction = "kingdom"
	w.player(1).faction = "clans"
	return w


func _hero(w: World, def_id: String, pid: int, at: Vector3, learn: Array = []) -> Unit:
	var h := w.spawn_unit(def_id, pid, at)
	w.heroes.add_xp(h, 1400.0)
	for a: Variant in learn:
		w.heroes.learn(h, str(a))
	h.mana = h.max_mana
	return h


func _ticks(w: World, n: int) -> void:
	for i in n:
		w.step()


func test_mana_and_cooldown_are_spent_at_the_cast_point() -> void:
	var w := _world()
	var marshal := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), ["kingdom_linden_balm"])
	var soldier := w.spawn_unit("kingdom_pavisier", 0, Vector3(22, 0, 20))
	soldier.take_damage(200.0, null)
	var mana := marshal.mana
	var hp := soldier.hp
	w.issue({"type": "cast", "player": 0, "units": [marshal.id], "ability": "kingdom_linden_balm", "target": soldier.id})
	var t := 0
	while (marshal.current == null or marshal.current.data.get("phase", "") != "point") and t < 30:
		w.step()
		t += 1
	assert_eq(str(marshal.current.data.get("phase", "")), "point", "it turns to face, then winds up")
	_ticks(w, 4)
	assert_near(marshal.mana, mana, 0.5, "nothing spent before the cast point")
	_ticks(w, 6)
	assert_near(marshal.mana, mana - 80.0, 1.0, "80 mana spent at the 0.3 s cast point")
	assert_true(soldier.hp > hp + 100.0, "the balm healed")
	assert_near(w.abilities.cooldown_left(marshal, "kingdom_linden_balm"), 7.0, 0.4, "the cooldown started")
	assert_eq(w.abilities.cast_error(marshal, "kingdom_linden_balm", soldier), "cooldown", "not again yet")


func test_an_order_or_a_stun_before_the_cast_point_costs_nothing() -> void:
	var w := _world()
	var marshal := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), ["kingdom_linden_balm"])
	var mana := marshal.mana
	w.issue({"type": "cast", "player": 0, "units": [marshal.id], "ability": "kingdom_linden_balm", "target": marshal.id})
	_ticks(w, 3)
	w.issue({"type": "stop", "player": 0, "units": [marshal.id]})
	_ticks(w, 12)
	assert_near(marshal.mana, mana, 1.0, "a new order in the wind-up spends nothing")
	assert_true(w.abilities.is_ready(marshal, "kingdom_linden_balm"), "and keeps the cooldown ready")
	w.issue({"type": "cast", "player": 0, "units": [marshal.id], "ability": "kingdom_linden_balm", "target": marshal.id})
	_ticks(w, 3)
	w.buffs.apply(marshal, "buff_stunned", null, {}, 1.0)
	_ticks(w, 12)
	assert_near(marshal.mana, mana, 1.5, "a stun in the wind-up spends nothing")
	assert_true(marshal.current == null or marshal.current.type != Order.Type.CAST, "and cancels the cast")
	w.buffs.apply(marshal, "buff_silenced", null, {}, 2.0)
	assert_eq(w.abilities.cast_error(marshal, "kingdom_linden_balm", marshal), "silenced", "silence refuses casts")


func test_targets_range_and_learning() -> void:
	var w := _world()
	var marshal := _hero(w, "kingdom_wheel_marshal", 0, Vector3(10, 0, 20))
	var enemy := w.spawn_unit("clans_hero_uncut", 1, Vector3(12, 0, 20))
	assert_eq(w.abilities.cast_error(marshal, "kingdom_linden_balm", marshal), "not_learned", "learn first")
	w.heroes.learn(marshal, "kingdom_linden_balm")
	assert_eq(w.abilities.cast_error(marshal, "kingdom_linden_balm", enemy), "bad_target", "the balm heals allies only")
	w.remove_unit(enemy)              # an enemy chasing the caster would body-block the walk
	var far := w.spawn_unit("kingdom_pavisier", 0, Vector3(40, 0, 20))
	w.issue({"type": "cast", "player": 0, "units": [marshal.id], "ability": "kingdom_linden_balm", "target": far.id})
	w.step()
	var t := 0
	while marshal.current != null and marshal.current.data.get("phase", "") == "" and t < 300:
		w.step()
		t += 1
	assert_lt(marshal.edge_distance(far), 8.05, "the caster walks into range before casting")
	marshal.mana = 10.0
	assert_eq(w.abilities.cast_error(marshal, "kingdom_linden_balm", far), "need_mana", "mana is checked")


func test_backswing_is_cut_by_a_new_order() -> void:
	var w := _world()
	var marshal := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), ["kingdom_linden_balm"])
	w.issue({"type": "cast", "player": 0, "units": [marshal.id], "ability": "kingdom_linden_balm", "target": marshal.id})
	_ticks(w, 11)
	assert_eq(str(marshal.current.data.get("phase", "")), "backswing", "in the backswing")
	w.issue({"type": "move", "player": 0, "units": [marshal.id], "pos": Vector3(30, 0, 20)})
	_ticks(w, 2)
	assert_eq(marshal.current.type, Order.Type.MOVE, "any order cuts the backswing")


func test_auras_reach_allies_and_linger_and_passives_stay() -> void:
	var w := _world()
	var marshal := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), ["kingdom_measured_cadence"])
	var near := w.spawn_unit("kingdom_pavisier", 0, Vector3(25, 0, 20))
	var far := w.spawn_unit("kingdom_pavisier", 0, Vector3(40, 0, 20))
	var foe := w.spawn_unit("clans_hero_uncut", 1, Vector3(24, 0, 22))
	_ticks(w, 16)
	assert_true(w.buffs.has_buff(near, "buff_measured_cadence"), "an ally in the aura gets it")
	assert_true(w.buffs.has_buff(marshal, "buff_measured_cadence"), "so does the emitter")
	assert_false(w.buffs.has_buff(far, "buff_measured_cadence"), "not beyond 9 m")
	assert_false(w.buffs.has_buff(foe, "buff_measured_cadence"), "never an enemy")
	near.teleport(Vector3(44, 0, 30))
	_ticks(w, 45)
	assert_true(w.buffs.has_buff(near, "buff_measured_cadence"), "it lingers 2 s after leaving")
	_ticks(w, 30)
	assert_false(w.buffs.has_buff(near, "buff_measured_cadence"), "then ends")
	var uncut := _hero(w, "clans_hero_uncut", 1, Vector3(30, 0, 40), ["clans_clean_cut"])
	_ticks(w, 16)
	assert_true(w.buffs.has_buff(uncut, "buff_clean_cut"), "a learned passive is a permanent buff")
	assert_near(float((uncut.mod_totals.get("crit", {}) as Dictionary).get("multiplier", 0.0)), 1.6, 0.001, "with its rank's crit")


func test_buff_refresh_rank_hero_duration_and_dispel() -> void:
	var w := _world()
	var hero := w.spawn_unit("clans_hero_uncut", 1, Vector3(20, 0, 20))
	var soldier := w.spawn_unit("kingdom_pavisier", 0, Vector3(24, 0, 20))
	w.buffs.apply(soldier, "buff_rooted", null, {}, 2.0)
	var rec := w.buffs.apply(hero, "buff_rooted", null, {"duration": 2.0})
	assert_eq(int(rec["remaining"]), 30, "control lasts 50 % on heroes")
	w.buffs.apply(soldier, "buff_slowed", null, {"rank": 2, "move_speed_pct": -40}, 3.0)
	w.buffs.apply(soldier, "buff_slowed", null, {"rank": 1, "move_speed_pct": -10}, 3.0)
	assert_near(float(soldier.mod_totals.get("move_speed_pct", 0.0)), -40.0, 0.01, "the stronger rank stays")
	w.buffs.apply(soldier, "buff_brace_the_wheel", null, {}, 5.0)
	var n := w.buffs.dispel(soldier, "selective", 0)
	assert_eq(n, 2, "an own selective dispel removes the ally's negative buffs (root, slow)")
	assert_true(w.buffs.has_buff(soldier, "buff_brace_the_wheel"), "and keeps its positive one")
	assert_eq(w.buffs.dispel(soldier, "selective", 1), 1, "an enemy's selective dispel strips the positive one")


func test_periodic_damage_regeneration_and_blindness() -> void:
	var w := _world()
	var soldier := w.spawn_unit("kingdom_pavisier", 0, Vector3(24, 0, 20))
	soldier.take_damage(100.0, null)
	var hp := soldier.hp
	_ticks(w, 30)
	assert_near(soldier.hp, hp + 0.25, 0.01, "organic units regenerate 0.25 HP/s")
	hp = soldier.hp
	w.buffs.apply(soldier, "buff_ember_burn", null, {}, -2.0)
	_ticks(w, 30)
	assert_lt(soldier.hp, hp - 4.0, "a DoT ticks every second")
	var blind := w.spawn_unit("clans_hero_uncut", 1, Vector3(26, 0, 20))
	w.buffs.apply(blind, "buff_sunglint_blind", null, {"miss_chance": 1.0}, 5.0)
	var misses: Array = []
	var on_miss := func(a: Node, _t: Node) -> void: misses.append(a)
	Events.attack_missed.connect(on_miss)
	var before := soldier.hp
	for i in 3:
		w.combat.fire(blind, soldier)
	Events.attack_missed.disconnect(on_miss)
	assert_eq(misses.size(), 3, "a blinded attacker misses")
	assert_lt(before - soldier.hp, 0.5, "and deals nothing")
