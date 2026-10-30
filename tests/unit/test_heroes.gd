extends "res://tests/test_case.gd"
## Heroes (src/systems/heroes.gd; rules §6.1–§6.7): kill XP by the victim's level, shared evenly
## among the killer's heroes in range, the creep factor and the single-hero bonus, no XP for a
## deny, a tower's blow or with no hero in range; level-up keeps the missing HP and grants a skill
## point; rank gates; proper names; death keeps the record and the slot; the altar revive (cost,
## time, food, cancel) brings the hero back with its level, skills and cooldowns.


func _world(faction: String = "kingdom") -> World:
	var w := make_world(flat_map(48, 48))
	var p := w.player(0)
	p.faction = faction
	p.gold = 5000
	p.lumber = 5000
	w.player(1).faction = "clans"
	return w


func _kill(w: World, victim: Unit, killer: Unit) -> void:
	victim.take_damage(999999.0, killer)
	w.step()


func _creep(w: World, def_id: String, at: Vector3) -> Unit:
	return w.spawn_unit(def_id, PlayerState.NEUTRAL_HOSTILE, at)


func test_kill_xp_by_level_and_the_worked_example() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	assert_eq(w.heroes.level_of(hero), 1, "starts at level 1")
	assert_eq(int(hero.hero["skill_points"]), 1, "with one skill point")
	# a green camp: two level-2 and two level-1 creeps = (40 + 40 + 25 + 25) x 0.8 = 104 XP
	for def_id: String in ["creep_sootcoat_coal_lobber", "creep_sootcoat_coal_lobber",
			"creep_sootcoat_cutpurse", "creep_sootcoat_cutpurse"]:
		_kill(w, _creep(w, def_id, Vector3(24, 0, 20)), hero)
	assert_near(float(hero.hero["xp"]), 104.0, 0.0001, "rules §6.4 worked example")
	var hostile := w.spawn_unit("clans_hero_uncut", 1, Vector3(23, 0, 20))
	_kill(w, hostile, hero)
	assert_near(float(hero.hero["xp"]), 204.0, 0.0001, "an enemy level-1 hero is worth 100")
	assert_eq(w.heroes.level_of(hero), 2, "200 XP reaches level 2")


func test_sharing_range_deny_and_tower_kills() -> void:
	var w := _world()
	var a := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var b := w.spawn_unit("kingdom_firewright", 0, Vector3(22, 0, 20))
	_kill(w, _creep(w, "creep_sootcoat_cutpurse", Vector3(21, 0, 22)), a)
	assert_near(float(a.hero["xp"]), 10.0, 0.0001, "25 split between 2 heroes x 0.8 = 10 each")
	assert_near(float(b.hero["xp"]), 10.0, 0.0001, "the other hero gets the same share")
	b.teleport(Vector3(44, 0, 44))
	_kill(w, _creep(w, "creep_sootcoat_cutpurse", Vector3(21, 0, 22)), a)
	assert_near(float(a.hero["xp"]), 30.0, 0.0001, "a hero out of range takes no share")
	assert_near(float(b.hero["xp"]), 10.0, 0.0001, "and gets nothing")
	a.teleport(Vector3(44, 0, 40))
	var soldier := w.spawn_unit("kingdom_pavisier", 0, Vector3(10, 0, 10))
	_kill(w, _creep(w, "creep_sootcoat_cutpurse", Vector3(10, 0, 12)), soldier)
	assert_near(float(a.hero["xp"]) + float(b.hero["xp"]), 40.0, 0.0001, "no hero in range: the XP is lost")
	var own := w.spawn_unit("kingdom_pavisier", 0, Vector3(44, 0, 42))
	_kill(w, own, a)
	assert_near(float(a.hero["xp"]), 30.0, 0.0001, "a deny gives nothing")
	var tower := w.spawn_unit("kingdom_moot_hall", 0, Vector3(36, 0, 36))
	_kill(w, w.spawn_unit("clans_hero_uncut", 1, Vector3(43, 0, 41)), tower)
	assert_near(float(a.hero["xp"]), 30.0, 0.0001, "a structure's killing blow gives nothing")


func test_creep_factor_and_single_hero_bonus() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	w.heroes.add_xp(hero, 1400.0)
	assert_eq(w.heroes.level_of(hero), 5, "level 5")
	_kill(w, _creep(w, "creep_sootcoat_collier", Vector3(22, 0, 20)), hero)
	assert_near(float(hero.hero["xp"]), 1400.0, 0.0001, "creeps give nothing from level 5")
	w.spawn_unit("kingdom_walled_burg", 0, Vector3(36, 0, 36))
	assert_eq(w.tech.tier(0), 2, "tier 2")
	assert_near(w.heroes.single_hero_bonus(0), 0.15, 0.0001, "one hero at tier 2: +15 %")
	_kill(w, w.spawn_unit("clans_hero_uncut", 1, Vector3(22, 0, 20)), hero)
	assert_near(float(hero.hero["xp"]), 1400.0 + 115.0, 0.0001, "100 x 1.15 for a level-1 hero")
	w.heroes.add_xp(hero, 1000.0, true)
	assert_near(float(hero.hero["xp"]), 2515.0, 0.0001, "flat XP takes no bonus")
	w.spawn_unit("kingdom_firewright", 0, Vector3(40, 0, 10))
	assert_near(w.heroes.single_hero_bonus(0), 0.0, 0.0001, "two heroes: no bonus")


func test_level_up_keeps_missing_hp_and_caps_at_ten() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	assert_near(hero.max_hp, 675.0, 0.01, "level-1 HP (kingdom §6.2)")
	hero.take_damage(100.0, null)
	var levels: Array[int] = []
	Events.hero_level_up.connect(func(u: Node) -> void: levels.append(int(u.hero["level"])))
	w.heroes.add_xp(hero, 500.0)
	assert_eq(levels, [2, 3] as Array[int], "two level-ups in order")
	assert_eq(int(hero.hero["skill_points"]), 3, "+1 point per level")
	assert_near(hero.max_hp - hero.hp, 100.0, 0.01, "the missing HP is kept")
	assert_near(hero.max_hp, 100.0 + 25.0 * floorf(23.0 + 2.6 * 2.0), 0.01, "max HP from STR")
	w.heroes.add_xp(hero, 99999.0)
	assert_eq(w.heroes.level_of(hero), 10, "the cap is level 10")
	var xp := float(hero.hero["xp"])
	w.heroes.add_xp(hero, 50.0)
	assert_near(float(hero.hero["xp"]), xp, 0.0001, "no XP at level 10")
	assert_near(hero.max_hp, 1250.0, 0.01, "rules §6.6 check: 1250 HP at level 10")


func test_rank_gates_through_the_learn_command() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var kit: Array = hero.def["hero_abilities"]
	var ult := ""
	for a: Variant in kit:
		if Defs.ability(str(a)).get("ultimate", false):
			ult = str(a)
	var first := str(kit[0])
	assert_false(w.heroes.can_learn(hero, ult), "the ultimate needs level 6")
	w.issue({"type": "learn", "player": 0, "units": [hero.id], "ability": first})
	w.step()
	assert_eq(w.heroes.rank_of(hero, first), 1, "rank 1 at level 1")
	assert_eq(int(hero.hero["skill_points"]), 0, "the point is spent")
	w.heroes.add_xp(hero, 200.0)
	assert_false(w.heroes.can_learn(hero, first), "rank 2 needs level 3")
	assert_true(w.heroes.can_learn(hero, str(kit[1])), "another ability's rank 1 is open")
	w.heroes.add_xp(hero, 300.0)
	assert_true(w.heroes.can_learn(hero, first), "rank 2 at level 3")
	w.heroes.add_xp(hero, 1500.0)
	assert_eq(w.heroes.level_of(hero), 6, "level 6")
	assert_true(w.heroes.can_learn(hero, ult), "the ultimate opens at level 6")


func test_proper_name_and_title() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var names: Array = Defs.hero("kingdom_wheel_marshal")["proper_names"]
	assert_true(names.has(hero.hero["proper_name"]), "a name from the list")
	assert_true(HeroSystem.display_name(hero).begins_with("Wheel Marshal: "), "Title: Name")


func test_death_keeps_the_slot_and_the_altar_revives() -> void:
	var w := _world()
	var altar := w.spawn_unit("kingdom_oath_hall", 0, Vector3(30, 0, 30))
	w.spawn_unit("kingdom_moot_hall", 0, Vector3(12, 0, 36))
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	w.heroes.add_xp(hero, 500.0)
	var first := str(hero.def["hero_abilities"][0])
	w.heroes.learn(hero, first)
	hero.cooldowns["probe"] = w.tick_count + 9000
	var old_id := hero.id
	_kill(w, hero, w.spawn_unit("clans_hero_uncut", 1, Vector3(21, 0, 20)))
	assert_eq(w.heroes.dead_heroes(0), [old_id] as Array[int], "the dead hero waits for revival")
	assert_false(w.production.can_acquire_hero(0, "kingdom_wheel_marshal"), "its type stays taken")
	assert_eq(w.production.can_train(altar, "kingdom_firewright"), "hero_limit", "and its slot at tier 1")
	var cost := w.heroes.revive_cost(old_id)
	assert_eq(int(cost["gold"]), 255, "level 3 revive: 255 gold (rules §6.7)")
	assert_near(float(cost["time"]), 107.25, 0.0001, "and 107.25 s")
	var gold := w.player(0).gold
	w.issue({"type": "revive", "player": 0, "units": [altar.id], "hero": old_id})
	w.step()
	assert_eq(w.player(0).gold, gold - 255, "paid on queue")
	assert_true(w.production.is_reviving(old_id), "queued at the altar")
	assert_eq(w.heroes.can_revive(altar, old_id), "busy", "only once")
	assert_eq(w.player(0).food_used, 5, "5 food reserved as it starts")
	var t0 := w.time
	while w.heroes.dead_record(old_id).size() > 0 and w.time - t0 < 120.0:
		w.step()
	assert_near(w.time - t0, 107.25, 0.1, "back after the revive time")
	var back: Unit = w.get_unit(w.player(0).heroes[0])
	assert_true(back != null and back.alive and back.def_id == "kingdom_wheel_marshal", "the hero is back")
	assert_eq(w.player(0).heroes.size(), 1, "in its old place")
	assert_eq(w.heroes.level_of(back), 3, "level kept")
	assert_eq(w.heroes.rank_of(back, first), 1, "skills kept")
	assert_eq(int(back.cooldowns.get("probe", 0)), int(hero.cooldowns["probe"]), "cooldowns keep running")
	assert_near(back.hp, back.max_hp, 0.01, "full HP")
	assert_near(back.mana, minf(back.max_mana, 100.0), 0.01, "mana min(max, 100)")
	assert_eq(w.player(0).food_used, 5, "the hero's food")


func test_revive_table_and_cancel() -> void:
	var w := _world()
	var altar := w.spawn_unit("kingdom_oath_hall", 0, Vector3(30, 0, 30))
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var hid := hero.id
	_kill(w, hero, w.spawn_unit("clans_hero_uncut", 1, Vector3(21, 0, 20)))
	assert_eq(int(w.heroes.revive_cost(hid)["gold"]), 170, "level 1: 170 gold")
	assert_near(float(w.heroes.revive_cost(hid)["time"]), 35.75, 0.0001, "and 35.75 s")
	(w.heroes.dead_record(hid)["hero"] as Dictionary)["level"] = 10
	assert_eq(int(w.heroes.revive_cost(hid)["gold"]), 550, "level 10: capped at 550")
	assert_near(float(w.heroes.revive_cost(hid)["time"]), 110.0, 0.0001, "and 110 s")
	var gold := w.player(0).gold
	w.issue({"type": "revive", "player": 0, "units": [altar.id], "hero": hid})
	w.step()
	w.issue({"type": "cancel", "player": 0, "units": [altar.id], "slot": 0})
	w.step()
	assert_eq(w.player(0).gold, gold, "a cancelled revive refunds in full")
	assert_false(w.production.is_reviving(hid), "and stops")
	assert_eq(w.player(0).food_used, 0, "food released")
