extends "res://tests/test_case.gd"
## The faction worker defences (abilities.json kingdom_levy_horn, kingdom_take_up_the_flail,
## kingdom_lay_down_*, clans_sound_the_gong, clans_roll_the_felt, clans_unload_all; Home Yurt
## garrison): the Levy Horn arms the Hodmen near the hall as Flail Levies with their cargo, they
## lay the flails down (by hand, when the horn's time is up, or after straying) and resume their jobs;
## the gong sends Yurtwrights into the Home Yurts, whose slings shoot per occupant, All Clear and
## a badly hit yurt let them out.


func _world() -> World:
	var w := make_world(flat_map(64, 64))
	w.player(0).faction = "kingdom"
	w.player(1).faction = "clans"
	return w


func test_levy_horn_arms_hodmen_and_they_go_back_to_work() -> void:
	var w := _world()
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(30, 0, 30))
	var near := w.spawn_unit("kingdom_hodman", 0, Vector3(38, 0, 30))
	var far := w.spawn_unit("kingdom_hodman", 0, Vector3(80, 0, 30))
	near.carry_gold = 10
	w.issue({"type": "cast", "player": 0, "units": [hall.id], "ability": "kingdom_levy_horn"})
	w.step()
	assert_eq(near.def_id, "kingdom_flail_levy", "a Hodman by the hall takes up the flail")
	assert_eq(near.carry_gold, 10, "keeping its gold")
	assert_eq(far.def_id, "kingdom_hodman", "one beyond 22 m does not")
	assert_true(near.damage_max > 5, "the levy fights")
	assert_false(w.abilities.is_ready(hall, "kingdom_levy_horn"), "the horn waits 60 s")
	w.issue({"type": "cast", "player": 0, "units": [hall.id], "ability": "kingdom_lay_down_flails_all"})
	w.step()
	assert_eq(near.def_id, "kingdom_hodman", "Lay Down Flails sends it back")
	assert_false(w.abilities.is_ready(near, "kingdom_take_up_the_flail"), "locked out for a while")


func test_levies_drop_the_flail_on_time_and_when_they_stray() -> void:
	var w := _world()
	w.spawn_unit("kingdom_moot_hall", 0, Vector3(30, 0, 30))
	var a := w.spawn_unit("kingdom_hodman", 0, Vector3(38, 0, 30))
	var b := w.spawn_unit("kingdom_hodman", 0, Vector3(38, 0, 34))
	assert_true(w.abilities.cast_now(a, "kingdom_take_up_the_flail"), "a takes up")
	assert_true(w.abilities.cast_now(b, "kingdom_take_up_the_flail"), "b takes up")
	b.teleport(Vector3(80, 0, 30))
	for i in 6 * 30:
		w.step()
	assert_eq(b.def_id, "kingdom_hodman", "more than 30 m from every hall for 5 s: back to a Hodman")
	assert_eq(a.def_id, "kingdom_flail_levy", "a is still armed")
	for i in 35 * 30:
		w.step()
	assert_eq(a.def_id, "kingdom_hodman", "after 40 s the levy ends")


func test_the_gong_fills_the_yurts_and_their_slings_shoot() -> void:
	var w := _world()
	var hall := w.spawn_unit("clans_shell_hall", 1, Vector3(30, 0, 30))
	var yurt := w.spawn_unit("clans_home_yurt", 1, Vector3(40, 0, 30))
	var workers: Array[Unit] = []
	for i in 4:
		workers.append(w.spawn_unit("clans_yurtwright", 1, Vector3(32 + i, 0, 38)))
	w.issue({"type": "cast", "player": 1, "units": [hall.id], "ability": "clans_sound_the_gong"})
	for i in 10 * 30:
		w.step()
	assert_eq(yurt.garrison.size(), 3, "three slots, three Yurtwrights inside")
	assert_eq(workers.filter(func(u: Unit) -> bool: return u.hidden).size(), 3, "hidden in the yurt")
	assert_true(yurt.damage_max >= 3 * 13, "three slings (%d)" % yurt.damage_max)
	var foe := w.spawn_unit("kingdom_pavisier", 0, Vector3(46, 0, 30))
	var hp := foe.hp
	for i in 4 * 30:
		w.step()
	assert_lt(foe.hp, hp, "the yurt shoots")
	w.issue({"type": "cast", "player": 1, "units": [hall.id], "ability": "clans_sound_the_gong"})
	w.step()
	assert_eq(yurt.garrison.size(), 0, "All Clear empties it")
	assert_true(workers.all(func(u: Unit) -> bool: return not u.hidden), "everyone out")
	assert_eq(yurt.damage_max, 0, "and the slings stop")


func test_a_badly_hit_yurt_throws_its_occupants_out() -> void:
	var w := _world()
	var yurt := w.spawn_unit("clans_home_yurt", 1, Vector3(40, 0, 30))
	var u := w.spawn_unit("clans_yurtwright", 1, Vector3(44, 0, 30))
	assert_true(w.construction.garrison_enter(u, yurt), "in")
	yurt.take_damage(yurt.max_hp * 0.6, null)
	assert_eq(yurt.garrison.size(), 0, "below half HP: out")
	assert_false(u.hidden, "visible again")
