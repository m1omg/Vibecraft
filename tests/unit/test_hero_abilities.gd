extends "res://tests/test_case.gd"
## The 16 hero abilities of the slice (data/abilities.json, src/systems/abilities/effects/*;
## kingdom and clans faction docs §6–§7): each one cast through AbilitySystem.cast_now at its
## first rank (the ultimates at theirs), checking what it does to the units around it.


func _world() -> World:
	var w := make_world(flat_map(48, 48))
	w.player(0).faction = "kingdom"
	w.player(1).faction = "clans"
	return w


func _hero(w: World, def_id: String, pid: int, at: Vector3, learn: String) -> Unit:
	var h := w.spawn_unit(def_id, pid, at)
	w.heroes.add_xp(h, 2000.0)          # level 6: every rank 1 and the ultimate
	w.heroes.learn(h, learn)
	h.mana = h.max_mana
	h.acquire_range = 0.0             # nobody fights on their own: only the ability acts
	return h


func _unit(w: World, def_id: String, pid: int, at: Vector3) -> Unit:
	var u := w.spawn_unit(def_id, pid, at)
	u.set_base_stats({"hp_regen": 0.0})
	u.acquire_range = 0.0
	return u


func _steps(w: World, n: int) -> void:
	for i in n:
		w.step()


func test_linden_balm_heals_the_target_and_splashes() -> void:
	var w := _world()
	var m := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), "kingdom_linden_balm")
	var a := _unit(w, "kingdom_pavisier", 0, Vector3(24, 0, 20))
	var b := _unit(w, "kingdom_pavisier", 0, Vector3(25.5, 0, 20))
	a.hp = 100.0
	b.hp = 100.0
	assert_true(w.abilities.cast_now(m, "kingdom_linden_balm", a), "cast")
	assert_near(a.hp, 250.0, 0.01, "150 to the target")
	assert_near(b.hp, 137.5, 0.01, "a quarter to an ally within 2.5 m")
	m.hp = 300.0
	m.cooldowns.clear()
	w.abilities.cast_now(m, "kingdom_linden_balm", m)
	assert_near(m.hp, 375.0, 0.01, "half on herself")


func test_brace_the_wheel_taunts_nearby_enemies() -> void:
	var w := _world()
	var m := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), "kingdom_brace_the_wheel")
	var near := _unit(w, "clans_grappler", 1, Vector3(23, 0, 20))
	var far := _unit(w, "clans_grappler", 1, Vector3(30, 0, 20))
	var hero := _unit(w, "clans_hero_uncut", 1, Vector3(20, 0, 23))
	var armor := m.armor
	w.abilities.cast_now(m, "kingdom_brace_the_wheel")
	assert_true(w.buffs.has_buff(near, "buff_taunted"), "an enemy within 4 m is taunted")
	assert_true(near.current != null and near.current.type == Order.Type.ATTACK and near.current.target_id == m.id, "and attacks her")
	assert_false(w.buffs.has_buff(far, "buff_taunted"), "not one beyond 4 m")
	assert_false(w.buffs.has_buff(hero, "buff_taunted"), "never a hero")
	assert_near(m.armor, armor + 4.0, 0.01, "she braces: +4 armour")


func test_the_wagon_ring_holds_the_line_then_heals() -> void:
	var w := _world()
	var m := _hero(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 20), "kingdom_the_wagon_ring")
	var a := _unit(w, "kingdom_pavisier", 0, Vector3(28, 0, 20))
	w.abilities.cast_now(m, "kingdom_the_wagon_ring")
	a.take_damage(99999.0, null)
	assert_true(a.alive and is_equal_approx(a.hp, 1.0), "nobody in the ring drops below 1 HP")
	_steps(w, 7 * 30 + 2)
	assert_false(w.buffs.has_buff(a, "buff_wagon_ring"), "it ends after 7 s")
	assert_near(a.hp, 1.0 + 0.15 * a.max_hp, 0.5, "and heals 15 % of max HP")


func test_naphtha_flask_bursts_and_the_ground_burns() -> void:
	var w := _world()
	var f := _hero(w, "kingdom_firewright", 0, Vector3(20, 0, 20), "kingdom_naphtha_flask")
	var e := _unit(w, "clans_grappler", 1, Vector3(27, 0, 20))
	var hp := e.hp
	w.abilities.cast_now(f, "kingdom_naphtha_flask", null, Vector3(27, 0, 20))
	var burst := hp - e.hp
	assert_true(burst > 40.0, "the burst hits (%.1f)" % burst)
	assert_eq(w.abilities.ground_effects().size(), 1, "the ground burns")
	_steps(w, 31)
	assert_true(hp - e.hp > burst + 8.0, "the burning ground deals damage each second")


func test_fuse_mark_explodes_or_is_defused() -> void:
	var w := _world()
	var f := _hero(w, "kingdom_firewright", 0, Vector3(20, 0, 20), "kingdom_fuse_mark")
	var t := _unit(w, "clans_grappler", 1, Vector3(25, 0, 20))
	var n := _unit(w, "clans_grappler", 1, Vector3(26.5, 0, 20))
	w.abilities.cast_now(f, "kingdom_fuse_mark", t)
	assert_true(w.buffs.has_buff(t, "buff_fuse_mark"), "marked")
	var hp_t := t.hp
	var hp_n := n.hp
	_steps(w, 4 * 30 + 1)
	assert_true(hp_t - t.hp > 60.0, "it goes off after 4 s")
	assert_near(hp_n - n.hp, (hp_t - t.hp) * 0.5, 1.0, "half to a neighbour within 2.5 m")
	f.cooldowns.clear()
	f.mana = f.max_mana
	w.abilities.cast_now(f, "kingdom_fuse_mark", t)
	w.buffs.dispel(t, "all", 0)
	var before := t.hp
	_steps(w, 4 * 30 + 1)
	assert_near(t.hp, before, 0.01, "a dispel defuses it")


func test_incendiary_wadding_sets_targets_burning() -> void:
	var w := _world()
	var f := _hero(w, "kingdom_firewright", 0, Vector3(20, 0, 20), "kingdom_incendiary_wadding")
	var gun := _unit(w, "kingdom_hookgunner", 0, Vector3(22, 0, 20))
	var pav := _unit(w, "kingdom_pavisier", 0, Vector3(20, 0, 22))
	var e := _unit(w, "clans_grappler", 1, Vector3(30, 0, 20))
	_steps(w, 16)
	assert_true(w.buffs.has_buff(gun, "buff_incendiary_wadding"), "ranged allies carry the wadding")
	assert_false(w.buffs.has_buff(pav, "buff_incendiary_wadding"), "melee ones do not")
	w.combat.fire(gun, e)
	assert_true(w.buffs.has_buff(e, "buff_wadding_burn"), "the shot sets the target burning")
	assert_near(float(w.buffs.get_buff(e, "buff_wadding_burn")["values"]["dps"]), 3.0, 0.01, "at rank 1's 3 a second")


func test_grand_bombard_and_hail_swifts_are_timed_summons() -> void:
	var w := _world()
	var f := _hero(w, "kingdom_firewright", 0, Vector3(20, 0, 20), "kingdom_grand_bombard")
	w.abilities.cast_now(f, "kingdom_grand_bombard", null, Vector3(24, 0, 20))
	var gb: Array = w.units_of_player(0).filter(func(u: Unit) -> bool: return u.def_id == "kingdom_summon_grand_bombard")
	assert_eq(gb.size(), 1, "the Grand Bombard is hauled in")
	assert_eq((gb[0] as Unit).lifetime_ticks, 25 * 30, "for 25 s")
	var s := _hero(w, "clans_hero_skymirror", 1, Vector3(30, 0, 30), "clans_hail_swifts")
	w.abilities.cast_now(s, "clans_hail_swifts")
	var swifts: Array = w.units_of_player(1).filter(func(u: Unit) -> bool: return u.def_id == "clans_summon_hail_swift_1")
	assert_eq(swifts.size(), 2, "two hail-swifts at rank 1")
	assert_true((swifts[0] as Unit).is_summoned and (swifts[0] as Unit).lifetime_ticks == 45 * 30, "summoned for 45 s")


func test_dust_veil_hides_and_the_opener_pays() -> void:
	var w := _world()
	var u := _hero(w, "clans_hero_uncut", 1, Vector3(20, 0, 20), "clans_dust_veil")
	var e := _unit(w, "kingdom_pavisier", 0, Vector3(21.2, 0, 20))
	w.abilities.cast_now(u, "clans_dust_veil")
	assert_false(w.fog.can_see(0, u), "the enemy cannot see her")
	assert_eq(e.find_target(8.0), null, "nor pick her as a target")
	assert_true(u.speed > 5.0, "and she moves faster")
	var hp := e.hp
	w.combat.fire(u, e)
	assert_false(w.buffs.has_buff(u, "buff_dust_veil"), "her attack ends the veil")
	assert_true(hp - e.hp > 60.0, "with bonus damage (%.1f)" % (hp - e.hp))
	assert_true(w.buffs.has_buff(e, "buff_dust_veil_slow"), "and slows the target")
	assert_true(w.fog.can_see(0, u), "she is seen again")


func test_braid_lash_pulls_and_roots() -> void:
	var w := _world()
	var u := _hero(w, "clans_hero_uncut", 1, Vector3(20, 0, 20), "clans_braid_lash")
	var e := _unit(w, "kingdom_pavisier", 0, Vector3(25, 0, 20))
	var d0 := Grid.flat_dist(u.pos, e.pos)
	w.abilities.cast_now(u, "clans_braid_lash", e)
	assert_near(Grid.flat_dist(u.pos, e.pos), d0 - 3.0, 0.05, "dragged 3 m closer")
	assert_true(e.rooted, "and rooted")
	assert_eq(int(w.buffs.get_buff(e, "buff_rooted")["remaining"]), 30, "for 1 s")
	var h := _unit(w, "kingdom_wheel_marshal", 0, Vector3(20, 0, 26))
	u.cooldowns.clear()
	u.mana = u.max_mana
	w.abilities.cast_now(u, "clans_braid_lash", h)
	assert_near(Grid.flat_dist(u.pos, h.pos), 4.5, 0.05, "a hero only 1.5 m")
	assert_eq(int(w.buffs.get_buff(h, "buff_rooted")["remaining"]), 23, "rooted 0.75 s (22.5 ticks, rounded)")


func test_clean_cut_crits_and_hastes() -> void:
	var w := _world()
	var u := w.spawn_unit("clans_hero_uncut", 1, Vector3(20, 0, 20))
	var e := _unit(w, "kingdom_pavisier", 0, Vector3(21, 0, 20))
	w.buffs.apply(u, "buff_clean_cut", u, {"chance": 1.0, "crit_multiplier": 3.0, "haste_buff": "buff_clean_cut_haste"}, -1.0)
	w.combat.fire(u, e)
	assert_true(w.combat.last_crit, "a clean cut")
	assert_true(w.buffs.has_buff(u, "buff_clean_cut_haste"), "lends her speed")


func test_through_the_tall_grass_cleaves_a_line() -> void:
	var w := _world()
	var u := _hero(w, "clans_hero_uncut", 1, Vector3(20, 0, 20), "clans_through_the_tall_grass")
	var t := _unit(w, "kingdom_pavisier", 0, Vector3(21.2, 0, 20))
	var behind := _unit(w, "kingdom_pavisier", 0, Vector3(25, 0, 20))
	var aside := _unit(w, "kingdom_pavisier", 0, Vector3(23, 0, 24))
	var cd := u.cooldown_ticks
	w.abilities.cast_now(u, "clans_through_the_tall_grass")
	assert_lt(float(u.cooldown_ticks), float(cd), "40 % faster attacks")
	var hp_b := behind.hp
	var hp_a := aside.hp
	w.combat.fire(u, t)
	assert_true(hp_b - behind.hp > 10.0, "the blow cuts through the line behind the target")
	assert_near(aside.hp, hp_a, 0.01, "not beside it")


func test_sunglint_blinds_a_cone_and_night_changes_it() -> void:
	var w := _world()
	var s := _hero(w, "clans_hero_skymirror", 1, Vector3(20, 0, 20), "clans_sunglint")
	var front := _unit(w, "kingdom_pavisier", 0, Vector3(25, 0, 20))
	var back := _unit(w, "kingdom_pavisier", 0, Vector3(15, 0, 20))
	var hp := front.hp
	w.abilities.cast_now(s, "clans_sunglint", null, Vector3(26, 0, 20))
	var day_dmg := hp - front.hp
	assert_true(day_dmg > 30.0, "damage in the cone")
	assert_true(w.buffs.has_buff(front, "buff_sunglint_blind"), "and the glare")
	assert_near(float(front.mod_totals.get("miss_chance", 0.0)), 0.35, 0.001, "35 % misses")
	assert_false(w.buffs.has_buff(back, "buff_sunglint_blind"), "nothing behind him")
	w.time = DayNight.DAY_LENGTH * (22.0 - DayNight.START_HOUR) / 24.0
	assert_true(DayNight.is_night_at(w.time), "night")
	var other := _unit(w, "kingdom_pavisier", 0, Vector3(25, 0, 21))
	s.cooldowns.clear()
	s.mana = s.max_mana
	var hp2 := other.hp
	w.abilities.cast_now(s, "clans_sunglint", null, Vector3(26, 0, 20))
	assert_near(hp2 - other.hp, day_dmg * 0.5, 0.5, "half the damage at night")
	assert_eq(int(w.buffs.get_buff(other, "buff_sunglint_blind")["remaining"]), 5 * 30, "the glare 2 s longer")


func test_bronze_window_reveals_and_detects_at_rank_three() -> void:
	var w := _world()
	w.fog.enabled = true
	var s := _hero(w, "clans_hero_skymirror", 1, Vector3(10, 0, 10), "clans_bronze_window")
	var spot := Vector3(70, 0, 70)
	var e := _unit(w, "kingdom_pavisier", 0, spot)
	w.step()
	assert_false(w.fog.can_see(1, e), "far away in the fog")
	w.abilities.cast_now(s, "clans_bronze_window", null, spot)
	w.step()
	assert_true(w.fog.can_see(1, e), "the window shows it")
	w.buffs.apply(e, "buff_invisible", null, {}, 30.0)
	assert_false(w.fog.can_see(1, e), "an invisible unit stays hidden at rank 1")
	w.heroes.add_xp(s, 2000.0)
	w.heroes.learn(s, "clans_bronze_window")
	w.heroes.learn(s, "clans_bronze_window")
	s.cooldowns.clear()
	s.mana = s.max_mana
	w.abilities.cast_now(s, "clans_bronze_window", null, spot)
	assert_true(w.fog.can_see(1, e), "rank 3 shows invisible units")


func test_swallowed_sun_darkens_enemies_and_speeds_allies() -> void:
	var w := _world()
	var s := _hero(w, "clans_hero_skymirror", 1, Vector3(20, 0, 20), "clans_swallowed_sun")
	var e := _unit(w, "kingdom_pavisier", 0, Vector3(30, 0, 20))
	var ally := _unit(w, "clans_grappler", 1, Vector3(28, 0, 22))
	var speed := ally.speed
	w.abilities.cast_now(s, "clans_swallowed_sun", null, Vector3(30, 0, 20))
	_steps(w, 1)
	assert_near(e.sight, 3.0, 0.01, "enemies inside see 3 m")
	assert_near(float(e.mod_totals.get("miss_chance", 0.0)), 0.4, 0.001, "and miss 40 %")
	assert_near(ally.speed, speed * 1.15, 0.01, "friends move 15 % faster")
	_steps(w, 12 * 30 + 2 * 30 + 16)
	assert_false(w.buffs.has_buff(e, "buff_swallowed_sun_enemy"), "it ends after 12 s and the linger")
