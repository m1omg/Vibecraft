extends "res://tests/test_case.gd"
## Worst-case tick cost (headless, 250 units). Every tick is timed and both the average and the
## single worst tick are asserted, so a one-tick spike (a path burst after a group order, a crowd
## of scanning units) fails the test. Each scenario runs a few times and the per-tick fastest
## time, scaled to the reference machine, is checked (`best_tick_samples`), so host noise does
## not fail the build. A tick is 33.3 ms; MAX_TICK_MS leaves room for systems that do not exist
## yet (fog, AI, abilities, economy). Deterministic work counters are asserted too.

const BattleSetup := preload("res://tests/playtest/battle_setup.gd")
const AVG_TICK_MS := 12.0
const MAX_TICK_MS := 20.0

var _last: World = null           ## world of the latest scenario build


@warning_ignore("integer_division")
func _blob(w: World, centre: Vector3, n: int, spacing: float, pid: int) -> Array:
	var ids: Array = []
	for i in n:
		var p := centre + Vector3((i % 20 - 9.5) * spacing, 0, (i / 20 - n / 40.0) * spacing)
		ids.append(w.spawn_unit("dummy_archer" if i % 3 == 0 else "dummy_soldier", pid, p).id)
	return ids


func _dense_blob(attack_move: bool) -> World:
	var w := make_world(flat_map(96, 96, 0))
	var ids := _blob(w, Vector3(70, 0, 86), 250, 1.1, 0)
	for i in 10:
		w.step()
	if attack_move:
		w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": Vector3(150, 0, 90)})
	_last = w
	return w


## One army packed at 1.1 m spacing with no enemy near: acquisition scans must not pay for the
## friendly crowd around them (idle and attack-moving units scan every 5 ticks).
func test_dense_blob_idle_and_attack_move() -> void:
	var idle := best_tick_samples(_dense_blob.bind(false), 150)
	assert_tick_cost(idle, "250-unit blob, idle", AVG_TICK_MS, MAX_TICK_MS)
	var moving := best_tick_samples(_dense_blob.bind(true), 150)
	assert_tick_cost(moving, "250-unit blob, attack-move", AVG_TICK_MS, MAX_TICK_MS)
	var hostile := 0
	var buf: Array = []
	for u in _last.unit_list:
		hostile += _last.spatial.query_hostile(u.pos, 9.0 + u.radius, _last.hostile_mask(u.player_id), buf).size()
	assert_eq(hostile, 0, "scans see no candidates in a one-player crowd")


func _cross_map_order() -> World:
	var m := MapGenerator.test_map()
	var w := make_world(m)
	var s0: Vector3 = m.start_locations[0]
	var s1: Vector3 = m.start_locations[1]
	var a0 := BattleSetup.find_open_area(w, s0 + (s1 - s0) * 0.15)
	var a1 := BattleSetup.find_open_area(w, s1 + (s0 - s1) * 0.15)
	assert_true(a0 != Vector3.INF and a1 != Vector3.INF, "open areas found")
	var ids := _blob(w, a0, 250, 1.2, 0)
	for i in 5:
		w.step()
	w.set_meta("q0", w.pathing.total_queries)
	w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": a1})
	_last = w
	return w


## 250 units ordered across the generated map in one command: the path work of the order is
## spread by the cost budget and shared through the group path, so no tick spikes.
func test_cross_map_group_order_on_generated_map() -> void:
	var samples := best_tick_samples(_cross_map_order, 90)
	var w := _last
	var waiting := 0
	for u in w.unit_list:
		if u._need_path:
			waiting += 1
	var queries: int = w.pathing.total_queries - int(w.get_meta("q0"))
	print("     cross-map order: %d A* queries for %d units, %d still waiting after 3 s" % [
		queries, w.unit_list.size(), waiting])
	assert_eq(waiting, 0, "every unit got its path")
	assert_lt(float(queries), 60.0, "the group shared its path searches")
	assert_tick_cost(samples, "250-unit cross-map order", AVG_TICK_MS, MAX_TICK_MS)


var _hits := 0


func _count_hit(_u: Node, _a: float, _s: Node) -> void:
	_hits += 1


func _clash() -> World:
	var w := make_world(flat_map(96, 96, 0))
	var c := Vector3(96, 0, 96)
	var west := _blob(w, c + Vector3(-18, 0, 0), 125, 1.2, 0)
	var east := _blob(w, c + Vector3(18, 0, 0), 125, 1.2, 1)
	w.issue({"type": "attack_move", "player": 0, "units": west, "pos": c + Vector3(40, 0, 0)})
	w.issue({"type": "attack_move", "player": 1, "units": east, "pos": c - Vector3(40, 0, 0)})
	_hits = 0
	return w


## Two armies of 125 attack-moving into each other: the approach (everyone scanning, chase
## re-paths) and the first seconds of melee.
func test_two_armies_approach_and_clash() -> void:
	Events.unit_damaged.connect(_count_hit)
	var samples := best_tick_samples(_clash, 180)
	Events.unit_damaged.disconnect(_count_hit)
	assert_true(_hits > 100, "the armies met (%d hits)" % _hits)
	assert_tick_cost(samples, "2 x 125 approach and clash", AVG_TICK_MS, MAX_TICK_MS)
