extends "res://tests/test_case.gd"
## Production and tech (src/systems/production.gd, tech.gd; rules §4.4, §4.6, §5, §6.1):
## training pays on queue and reserves food on start, waits for supply with a notice, cancels with
## a full refund; heroes (first one free, slots by tier, one of each type); research applies its
## effects to living and new units; the hall upgrade transforms the hall in place (HP fraction,
## food, tier); building bonuses; the Lookout becomes a Gun Tower; rally points send units on.


func _world(faction: String = "kingdom") -> World:
	var w := make_world(flat_map(48, 48))
	var p := w.player(0)
	p.faction = faction
	p.gold = 5000
	p.lumber = 5000
	p.hero_tokens = 1
	return w


func _spawn(w: World, def_id: String, at: Vector3) -> Unit:
	return w.spawn_unit(def_id, 0, at)


func _until(w: World, cond: Callable, max_s: float) -> float:
	var t0 := w.time
	while not cond.call() and w.time - t0 < max_s:
		w.step()
	return w.time - t0


func test_training_pays_reserves_food_and_cancels() -> void:
	var w := _world()
	var hall := _spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	assert_eq(w.player(0).food_cap, 12, "the hall gives 12 food")
	var g0 := w.player(0).gold
	w.issue({"type": "train", "player": 0, "units": [hall.id], "def": "kingdom_hodman"})
	w.step()
	assert_eq(w.player(0).gold, g0 - 70, "paid on queue")
	assert_eq(w.player(0).food_used, 1, "food reserved as training starts")
	assert_eq(w.production.queue_of(hall).size(), 1, "queued")
	w.issue({"type": "train", "player": 0, "units": [hall.id], "def": "kingdom_hodman", "queue": true})
	w.step()
	assert_eq(w.production.queue_of(hall).size(), 6, "shift queues five more")
	w.issue({"type": "train", "player": 0, "units": [hall.id], "def": "kingdom_hodman", "queue": true})
	w.step()
	assert_eq(w.production.queue_of(hall).size(), 7, "the queue holds seven")
	assert_eq(w.production.can_train(hall, "kingdom_hodman"), "queue_full", "and no more")
	var g1 := w.player(0).gold
	w.issue({"type": "cancel", "player": 0, "units": [hall.id], "slot": 0})
	w.step()
	assert_eq(w.player(0).gold, g1 + 70, "cancel refunds 100 %")
	assert_eq(w.production.queue_of(hall).size(), 6, "one fewer")
	var hods_before := w.units_of_player(0).size()
	_until(w, func() -> bool: return w.units_of_player(0).size() > hods_before, 20.0)
	assert_eq(w.units_of_player(0).size(), hods_before + 1, "a Hodman walked out after 15 s")


func test_training_waits_for_supply() -> void:
	var w := _world()
	var hall := _spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	w.player(0).food_used = 12
	var notes: Array = []
	var cb := func(pid: int, kind: String, _t: String) -> void:
		if pid == 0:
			notes.append(kind)
	Events.notification.connect(cb)
	w.issue({"type": "train", "player": 0, "units": [hall.id], "def": "kingdom_hodman"})
	for i in 30 * 3:
		w.step()
	Events.notification.disconnect(cb)
	assert_false(w.production.queue_of(hall)[0]["started"], "the head waits for food")
	assert_true(notes.has("supply_stalled"), "and the player is told")
	assert_eq(notes.count("supply_stalled"), 1, "once per 8 s")
	w.player(0).food_used = 11
	w.step()
	assert_true(w.production.queue_of(hall)[0]["started"], "food freed: it starts")


func test_heroes_first_free_slots_and_unique() -> void:
	var w := _world()
	_spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	var altar := _spawn(w, "kingdom_oath_hall", Vector3(50, 0, 30))
	var g0 := w.player(0).gold
	w.issue({"type": "train", "player": 0, "units": [altar.id], "def": "kingdom_wheel_marshal"})
	w.step()
	assert_eq(w.player(0).gold, g0, "the first hero is free (token)")
	assert_eq(w.player(0).hero_tokens, 0, "token used")
	assert_eq(w.production.can_train(altar, "kingdom_firewright"), "hero_limit", "one hero slot at tier 1")
	w.issue({"type": "cancel", "player": 0, "units": [altar.id]})
	w.step()
	assert_eq(w.player(0).hero_tokens, 1, "cancel returns the token")
	w.issue({"type": "train", "player": 0, "units": [altar.id], "def": "kingdom_wheel_marshal"})
	w.step()
	var took := _until(w, func() -> bool: return w.production.queue_of(altar).is_empty(), 60.0)
	assert_near(took, 55.0, 0.2, "a hero takes 55 s")
	var hero: Unit = null
	for u in w.unit_list:
		if u.is_hero:
			hero = u
	assert_true(hero != null and hero.def_id == "kingdom_wheel_marshal", "the Wheel Marshal answered the call")
	assert_eq(w.production.can_train(altar, "kingdom_wheel_marshal"), "hero_limit", "never two of a type")


func test_research_applies_to_living_and_new_units() -> void:
	var w := _world()
	_spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	var foundry := _spawn(w, "kingdom_foundry", Vector3(50, 0, 30))
	var pav := _spawn(w, "kingdom_pavisier", Vector3(40, 0, 50))
	var base_max := pav.damage_max
	var g0 := w.player(0).gold
	w.issue({"type": "research", "player": 0, "units": [foundry.id], "def": "kingdom_tempered_blades"})
	w.step()
	assert_eq(w.player(0).gold, g0 - 110, "level 1 paid on queue")
	assert_eq(w.production.can_queue_research(foundry, "kingdom_tempered_blades"), "busy", "one level at a time")
	var took := _until(w, func() -> bool: return w.tech.research_level(0, "kingdom_tempered_blades") >= 1, 70.0)
	assert_near(took, 60.0, 0.2, "60 s")
	assert_eq(pav.damage_max, base_max + 2, "the living Pavisier hits 2 harder")
	var fresh := _spawn(w, "kingdom_pavisier", Vector3(42, 0, 50))
	assert_eq(fresh.damage_max, base_max + 2, "and so does a new one")
	assert_eq(w.production.can_queue_research(foundry, "kingdom_tempered_blades"), "tier", "level 2 needs tier 2")
	var hg := _spawn(w, "kingdom_hookgunner", Vector3(44, 0, 50))
	w.tech.complete_research(0, "kingdom_drawn_barrels")
	assert_near(hg.attack_range, 9.0, 0.001, "Drawn Barrels: range 7.0 -> 9.0 m")


func test_hall_upgrade_transforms_in_place() -> void:
	var w := _world()
	var hall := _spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	w.step()
	assert_eq(w.tech.tier(0), 1, "tier 1")
	assert_eq(w.production.can_queue_research(hall, "kingdom_walled_burg"), "requirements", "needs an Oath Hall")
	_spawn(w, "kingdom_oath_hall", Vector3(50, 0, 30))
	hall.hp = hall.max_hp * 0.5
	var tiers: Array = []
	var cb := func(pid: int, t: int) -> void:
		if pid == 0:
			tiers.append(t)
	Events.tier_changed.connect(cb)
	w.issue({"type": "research", "player": 0, "units": [hall.id], "def": "kingdom_walled_burg"})
	w.step()
	assert_true(w.production.is_upgrading(hall), "upgrading")
	assert_eq(w.production.can_train(hall, "kingdom_hodman"), "busy", "nothing else while it runs")
	assert_eq(w.tech.tier(0), 1, "still a tier-1 hall meanwhile")
	var took := _until(w, func() -> bool: return hall.def_id == "kingdom_walled_burg", 140.0)
	Events.tier_changed.disconnect(cb)
	assert_near(took, 130.0, 0.2, "130 s")
	assert_near(hall.hp / hall.max_hp, 0.5, 0.01, "the HP fraction is kept")
	assert_eq(hall.max_hp, 2050.0, "the Walled Burg's HP")
	assert_eq(w.player(0).food_cap, 14, "food 12 -> 14")
	assert_eq(w.tech.tier(0), 2, "tier 2")
	assert_eq(tiers, [2], "tier_changed once")
	assert_true(w.economy.accepts_cargo(hall, _carrier(w)), "still a drop-off")


func _carrier(w: World) -> Unit:
	var h := _spawn(w, "kingdom_hodman", Vector3(36, 0, 40))
	h.carry_gold = 10
	return h


func test_building_bonus_and_tower_upgrade() -> void:
	var w := _world()
	_spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	var croft := _spawn(w, "kingdom_croft", Vector3(50, 0, 30))
	var a0 := croft.armor
	var hp0 := croft.max_hp
	w.tech.complete_research(0, "kingdom_lime_mortar")
	assert_eq(croft.armor, a0 + 2, "Lime Mortar: +2 armour")
	assert_near(croft.max_hp, hp0 * 1.15, 0.5, "and +15 % HP")
	_spawn(w, "kingdom_timber_yard", Vector3(60, 0, 50))
	var tower := _spawn(w, "kingdom_lookout", Vector3(40, 0, 60))
	w.issue({"type": "research", "player": 0, "units": [tower.id], "def": "kingdom_gun_tower"})
	_until(w, func() -> bool: return tower.def_id == "kingdom_gun_tower", 40.0)
	assert_eq(tower.def_id, "kingdom_gun_tower", "the Lookout became a Gun Tower")
	assert_true(tower.can_attack(), "and it shoots")


func test_rally_sends_workers_to_the_mine() -> void:
	var w := _world()
	var hall := _spawn(w, "kingdom_moot_hall", Vector3(30, 0, 30))
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(46, 0, 30))
	w.issue({"type": "smart", "player": 0, "units": [hall.id], "target": mine.id})
	w.step()
	assert_eq(hall.rally_id, mine.id, "the rally is on the seam")
	w.issue({"type": "train", "player": 0, "units": [hall.id], "def": "kingdom_hodman"})
	_until(w, func() -> bool: return _first(w, "kingdom_hodman") != null, 20.0)
	var hod := _first(w, "kingdom_hodman")
	w.step()
	w.step()
	assert_true(hod != null and hod.current != null and hod.current.type == Order.Type.GATHER, "the new Hodman goes mining")


func _first(w: World, def_id: String) -> Unit:
	for u in w.unit_list:
		if u.def_id == def_id:
			return u
	return null
