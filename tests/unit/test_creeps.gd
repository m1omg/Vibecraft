extends "res://tests/test_case.gd"
## Creeps (src/systems/creeps.gd; rules §15, neutrals §1): bounty to the killer's owner, drops
## carried by the right creep, night sleep (staggered, safe scouting, a hit wakes the camp, a
## building nearby wakes it, dawn wakes it), the invulnerable full-heal return after a leash or
## the give-up timer, and the creep spell AI.


func _world() -> World:
	var w := make_world(flat_map(48, 48))
	w.player(0).faction = "kingdom"
	return w


func _camp(w: World, creeps: Array, template: String = "camp_gv_charcoal_clamp", at: Vector3 = Vector3(40, 0, 40)) -> Array[Unit]:
	w.map.creep_camps = [{"id": "c1", "pos": at, "template": template, "creeps": creeps}]
	w.creeps.spawn_camps(w.map)
	return w.creeps.camp_members("c1")


## Sets the sim clock to `hour` (step() derives time from the tick count).
func _at_hour(w: World, hour: float) -> void:
	w.tick_count = roundi(DayNight.DAY_LENGTH * (hour - DayNight.START_HOUR) / 24.0 * World.TICK_RATE)
	w.time = w.tick_count * World.DT


func _night(w: World) -> void:
	_at_hour(w, 19.0)                 # past every stagger


func test_bounty_goes_to_the_killer() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_cutpurse", "creep_sootcoat_coal_lobber"])
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(30, 0, 30))
	var paid: Array = []
	var on_paid := func(pid: int, amount: int, _p: Vector3) -> void: paid.append([pid, amount])
	Events.bounty_paid.connect(on_paid)
	var gold := w.player(0).gold
	var cut: Unit = camp.filter(func(u: Unit) -> bool: return u.level == 1)[0]
	cut.take_damage(99999.0, hero)
	w.step()
	var got := w.player(0).gold - gold
	assert_true(got >= 6 and got <= 10, "4 x level 1 + 2 + 0..4 gold (%d)" % got)
	assert_eq(paid.size(), 1, "the bounty pop")
	assert_eq(int(paid[0][1]), got, "showing what was credited")
	Events.bounty_paid.disconnect(on_paid)


func test_drops_ride_the_highest_level_creep() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_cutpurse", "creep_sootcoat_coal_lobber", "creep_sootcoat_cutpurse"])
	var big: Unit = camp.filter(func(u: Unit) -> bool: return u.level == 2)[0]
	var item := w.creeps.drop_of(big)
	assert_true(item != "", "the level-2 Coal Lobber carries the drop")
	var d := Defs.item(item)
	assert_true(["powerup", "charged"].has(str(d.get("class", ""))) and int(d.get("level", 0)) == 1, "from the camp's pool")
	big.take_damage(99999.0, null)
	w.step()
	var found := w.unit_list.filter(func(u: Unit) -> bool: return u.is_item and u.item_id == item)
	assert_eq(found.size(), 1, "it falls where the carrier died")


func test_camps_sleep_at_night_and_wake() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_cutpurse", "creep_sootcoat_cutpurse"])
	_night(w)
	w.step()
	assert_true(w.creeps.camp_state("c1")["asleep"], "asleep after dusk")
	assert_true(camp[0].stunned, "sleepers do nothing")
	var scout := w.spawn_unit("kingdom_pavisier", 0, camp[0].pos + Vector3(2, 0, 0))
	scout.acquire_range = 6.0
	for i in 30:
		w.step()
	assert_eq(scout.engage_id, 0, "a player unit never picks a sleeping creep")
	camp[0].take_damage(5.0, scout)
	w.step()
	assert_false(w.creeps.camp_state("c1")["asleep"], "a hit wakes the whole camp")
	assert_false(camp[1].stunned, "every member")


func test_dawn_and_building_wake_a_camp() -> void:
	var w := _world()
	_camp(w, ["creep_sootcoat_cutpurse"])
	_night(w)
	w.step()
	assert_true(w.creeps.camp_state("c1")["asleep"], "asleep")
	w.spawn_unit("kingdom_croft", 0, Vector3(46, 0, 40), 0.0, {"under_construction": true})
	assert_false(w.creeps.camp_state("c1")["asleep"], "a building started within 12 m wakes it")
	w.creeps.sleep_camp("c1")
	_at_hour(w, 6.5 + 24.0)
	w.step()
	assert_false(w.creeps.camp_state("c1")["asleep"], "dawn wakes it")


func test_returning_creeps_are_invulnerable_and_heal_at_home() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_collier"])
	var c: Unit = camp[0]
	var home := c.home_pos()
	c.take_damage(200.0, null)
	c.teleport(home + Vector3(-22, 0, 0))
	c.return_to(home)
	w.step()
	assert_true(c.is_invulnerable, "it walks home invulnerable")
	var t := 0
	while c.returning and t < 600:
		w.step()
		t += 1
	w.step()
	assert_false(c.is_invulnerable, "an ordinary target once home")
	assert_near(c.hp, c.max_hp, 0.01, "and fully healed")


func test_the_camp_gives_up_after_ten_quiet_seconds() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_cutpurse", "creep_sootcoat_cutpurse"])
	var bait := w.spawn_unit("kingdom_pavisier", 0, Vector3(30, 0, 40))
	bait.set_base_stats({"hp_regen": 0.0})
	w.creeps.alert_camp("c1", bait)
	bait.teleport(Vector3(4, 0, 4))
	bait.is_invulnerable = true
	for i in 11 * 30:
		w.step()
	assert_true(camp.all(func(u: Unit) -> bool: return u.returning or Grid.flat_dist(u.pos, u.home_pos()) < 2.0),
		"with nothing hit for 10 s the camp walks home")


func test_creep_spell_ai_casts_in_a_fight() -> void:
	var w := _world()
	var camp := _camp(w, ["creep_sootcoat_kiln_master"], "camp_gv_charcoal_clamp")
	var km := camp[0]
	km.mana = km.max_mana
	var a := w.spawn_unit("kingdom_pavisier", 0, km.pos + Vector3(2, 0, 0))
	w.creeps.alert_camp("c1", a)
	var cast: Array = []
	var km_id := km.id
	var on_cast := func(c: Node, id: String, _r: int, _t: Node, _p: Vector3) -> void:
		if is_instance_valid(c) and (c as Unit).id == km_id:
			cast.append(id)
	Events.ability_cast.connect(on_cast)
	for i in 60:
		w.step()
	Events.ability_cast.disconnect(on_cast)
	assert_true(cast.has("creep_stoke_the_coals"), "the Kiln Master stokes the coals when pulled (%s)" % str(cast))
