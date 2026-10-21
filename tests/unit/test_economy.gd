extends "res://tests/test_case.gd"
## The economy (src/systems/economy.gd, rules §4): the gold loop saturates at five workers on a
## seam 6 m from the hall (9–11 gold/s, a sixth adds < 0.5), one worker inside a seam at a time,
## lumber trips of the faction's size, felled trees and retargeting, the upkeep tax on mined
## gold, switching resources drops the load, Return Cargo goes back to work, and a seam runs dry.


## Moot Hall with a Gold Seam 6.0 m east of it (edge to edge), a tree line north of the hall.
func _base(w: World, pid: int = 0, faction: String = "kingdom") -> Dictionary:
	w.player(pid).faction = faction
	var hall_id := str(Defs.faction(faction)["hall"])
	var hall := w.spawn_unit(hall_id, pid, Vector3(30, 0, 50))
	var hx1 := hall.footprint.end.x * Grid.CELL
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(hx1 + 6.0 + 3.0, 0, 50))
	return {"hall": hall, "mine": mine}


func _gap(hall: Unit, mine: Unit) -> float:
	return (mine.footprint.position.x - hall.footprint.end.x) * Grid.CELL


func _workers(w: World, n: int, pid: int = 0, def_id: String = "kingdom_hodman", at := Vector3(36, 0, 46)) -> Array[Unit]:
	var out: Array[Unit] = []
	for i in n:
		out.append(w.spawn_unit(def_id, pid, at + Vector3(i * 0.9, 0, 0)))
	return out


func _mine_with(w: World, workers: Array[Unit], mine: Unit) -> void:
	for u in workers:
		w.issue({"type": "gather", "player": u.player_id, "units": [u.id], "target": mine.id})


## Gold per second over `seconds` after a warm-up.
func _gold_rate(w: World, pid: int, warm: float, seconds: float) -> float:
	for i in roundi(warm * 30.0):
		w.step()
	var g0 := w.player(pid).gold
	for i in roundi(seconds * 30.0):
		w.step()
	return (w.player(pid).gold - g0) / seconds


func test_five_workers_saturate_a_seam() -> void:
	var w := make_world(flat_map(48, 48))
	var b := _base(w)
	assert_near(_gap(b["hall"], b["mine"]), 6.0, 0.01, "the hall–seam gap is 6 m")
	var five := _workers(w, 5)
	_mine_with(w, five, b["mine"])
	var rate := _gold_rate(w, 0, 20.0, 120.0)
	assert_true(rate >= 9.0 and rate <= 11.0, "5 workers: %.2f gold/s (9–11)" % rate)
	var w6 := make_world(flat_map(48, 48))
	var b6 := _base(w6)
	var six := _workers(w6, 6)
	_mine_with(w6, six, b6["mine"])
	var rate6 := _gold_rate(w6, 0, 20.0, 120.0)
	assert_true(rate6 - rate < 0.5, "a sixth worker adds %.2f gold/s (< 0.5)" % (rate6 - rate))
	var w4 := make_world(flat_map(48, 48))
	var b4 := _base(w4)
	_mine_with(w4, _workers(w4, 4), b4["mine"])
	var rate4 := _gold_rate(w4, 0, 20.0, 60.0)
	assert_true(rate4 < rate - 0.5, "4 workers mine less (%.2f)" % rate4)


func test_one_worker_inside_and_the_door_queue() -> void:
	var w := make_world(flat_map(48, 48))
	var b := _base(w)
	var mine: Unit = b["mine"]
	var two := _workers(w, 2, 0, "kingdom_hodman", mine.pos + Vector3(-4.0, 0, -0.5))
	_mine_with(w, two, mine)
	var both_waited := false
	var max_inside := 0
	for i in 30 * 6:
		w.step()
		var inside := 0
		for u in two:
			if u.hidden:
				inside += 1
		max_inside = maxi(max_inside, inside)
		if w.economy.door_queue(mine).size() == 1 and w.economy.miner_inside(mine) != 0:
			both_waited = true
	assert_eq(max_inside, 1, "never two workers inside a seam")
	assert_true(both_waited, "the second worker waited at the door while the first was inside")
	assert_true(w.player(0).gold > 0, "gold arrived")


func test_lumber_trips_felling_and_retarget() -> void:
	var m := flat_map(48, 48)
	for y in range(40, 44):
		m.trees.append(Vector2i(30, y))
		m.tree_types.append(0)
	var w := make_world(m)
	var b := _base(w)
	var hall: Unit = b["hall"]
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30.5, 0, 45.0))
	var i := w.doodads.tree_at_cell(Vector2i(60, 86))   # tree (30, 43)
	assert_true(i >= 0, "a tree to chop")
	w.issue({"type": "gather", "player": 0, "units": [hod.id], "pos": w.doodads.tree_pos(i), "data": {"tree": i}})
	var l0 := w.player(0).lumber
	var first_trip := -1.0
	for t in 30 * 40:
		w.step()
		if first_trip < 0.0 and w.player(0).lumber > l0:
			first_trip = w.time
	assert_true(first_trip > 0.0, "a lumber trip was delivered")
	assert_eq((w.player(0).lumber - l0) % 10, 0, "kingdom trips carry 10 lumber")
	assert_true(hod.anim_hint == "work" or hod.current != null, "still working")
	# chop the line down: felled trees retarget the next one within 8 m
	for t in 30 * 120:
		w.step()
	var felled := 0
	for k in w.doodads.trees.size():
		if not w.doodads.tree_alive(k):
			felled += 1
	assert_true(felled >= 2, "trees were felled (%d) and the worker moved on" % felled)
	assert_eq(w.player(0).lumber - l0 + hod.carry_lumber, felled * 50 + _partial(w),
		"every lumber cut was delivered or is carried")
	assert_true(hall != null, "hall")


## Lumber taken from trees still standing (the one being chopped).
func _partial(w: World) -> int:
	var n := 0
	for k in w.doodads.trees.size():
		if w.doodads.tree_alive(k):
			n += 50 - w.doodads.lumber[k]
	return n


func test_clans_trips_are_fifteen() -> void:
	var m := flat_map(48, 48)
	m.trees.append(Vector2i(30, 42))
	m.tree_types.append(0)
	var w := make_world(m)
	_base(w, 0, "clans")
	var yw := w.spawn_unit("clans_yurtwright", 0, Vector3(30.5, 0, 45.0))
	var i := w.doodads.tree_at_cell(Vector2i(60, 84))
	w.issue({"type": "gather", "player": 0, "units": [yw.id], "pos": w.doodads.tree_pos(i), "data": {"tree": i}})
	var l0 := w.player(0).lumber
	for t in 30 * 30:
		w.step()
		if w.player(0).lumber > l0:
			break
	assert_eq(w.player(0).lumber - l0, 15, "a clans trip carries 15 lumber")


func test_upkeep_taxes_mined_gold_not_lumber() -> void:
	var w := make_world(flat_map(48, 48))
	var b := _base(w)
	var hod := _workers(w, 1)[0]
	w.player(0).food_used = 60   # Upkeep 30 %
	w.step()
	var g0 := w.player(0).gold
	hod.carry_gold = 10
	w.economy.deposit(hod, b["hall"])
	assert_eq(w.player(0).gold - g0, 7, "a 10-gold trip yields 7 at 60 food")
	var l0 := w.player(0).lumber
	hod.carry_lumber = 10
	w.economy.deposit(hod, b["hall"])
	assert_eq(w.player(0).lumber - l0, 10, "lumber is never taxed")
	w.player(0).food_used = 90
	w.step()
	g0 = w.player(0).gold
	hod.carry_gold = 10
	w.economy.deposit(hod, b["hall"])
	assert_eq(w.player(0).gold - g0, 4, "and 4 at 90 food")


func test_switching_resources_drops_the_load_and_return_cargo_resumes() -> void:
	var m := flat_map(48, 48)
	m.trees.append(Vector2i(30, 41))
	m.tree_types.append(0)
	var w := make_world(m)
	var b := _base(w)
	var mine: Unit = b["mine"]
	var hod := _workers(w, 1)[0]
	_mine_with(w, [hod], mine)
	for t in 30 * 4:
		w.step()
		if hod.carry_gold > 0:
			break
	assert_eq(hod.carry_gold, 10, "came out of the seam with 10 gold")
	var i := w.doodads.tree_at_cell(Vector2i(60, 82))
	w.issue({"type": "gather", "player": 0, "units": [hod.id], "pos": w.doodads.tree_pos(i), "data": {"tree": i}})
	for t in 30 * 8:
		w.step()
		if hod.anim_hint == "work":
			break
	assert_eq(hod.carry_gold, 0, "starting to chop dropped the gold (rules §4.3)")
	# Return Cargo, then back to the tree
	for t in 30 * 3:
		w.step()
	assert_true(hod.carry_lumber > 0, "chopping")
	w.issue({"type": "return", "player": 0, "units": [hod.id]})
	var delivered := false
	for t in 30 * 20:
		w.step()
		if hod.carry_lumber == 0:
			delivered = true
		if delivered and hod.current != null and hod.current.type == Order.Type.GATHER:
			break
	assert_true(delivered, "the cargo was delivered")
	assert_true(hod.current != null and hod.current.type == Order.Type.GATHER, "and the worker went back to the tree")


func test_a_seam_runs_dry() -> void:
	var w := make_world(flat_map(48, 48))
	var b := _base(w)
	var mine: Unit = b["mine"]
	w.economy.mine_gold[mine.id] = 1520
	var low := []
	var dry := []
	var on_low := func(m: Node) -> void: low.append(m)
	var on_dry := func(m: Node) -> void: dry.append(m)
	Events.mine_low.connect(on_low)
	Events.mine_depleted.connect(on_dry)
	var five := _workers(w, 5)
	var g0 := w.player(0).gold
	_mine_with(w, five, mine)
	for t in 30 * 200:
		w.step()
		if not dry.is_empty():
			break
	Events.mine_low.disconnect(on_low)
	Events.mine_depleted.disconnect(on_dry)
	assert_eq(low.size(), 1, "one low-gold warning")
	assert_eq(dry.size(), 1, "the seam ran dry")
	assert_eq(w.economy.gold_left(mine), 0, "no gold left")
	assert_false(mine.is_resource, "nothing to gather any more")
	for t in 30 * 10:
		w.step()
	var busy := 0
	for u in five:
		if u.current != null and u.current.type == Order.Type.GATHER and not u.hidden:
			busy += 1
	assert_eq(busy, 0, "the miners went idle")
	assert_eq(w.player(0).gold - g0, 1520, "every last coin was delivered")
