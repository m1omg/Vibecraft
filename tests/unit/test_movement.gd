extends "res://tests/test_case.gd"


func _move(w: World, units: Array, pos: Vector3, queue: bool = false, type: String = "move") -> void:
	var ids: Array = []
	for u: Unit in units:
		ids.append(u.id)
	w.issue({"type": type, "player": units[0].player_id, "units": ids, "pos": pos, "queue": queue})


func test_unit_arrives_within_expected_ticks() -> void:
	var w := make_world()
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var goal := Vector3(40, 0, 30)
	_move(w, [u], goal)
	var expected := Grid.flat_dist(u.pos, goal) / u.speed * World.TICK_RATE
	var ticks := run_until_idle(w, [u], 1000)
	if w.tick_count == 0:
		fail("never ticked")
	assert_lt(Grid.flat_dist(u.pos, goal), 0.3, "arrived at goal")
	assert_lt(float(ticks), expected * 1.15 + 10.0, "arrival time (expected ~%d ticks)" % int(expected))
	assert_near(u.pos.y, w.map.height_at(u.pos.x, u.pos.z), 0.001, "y follows terrain")


func _simulate(frames_per_tick: Array) -> Dictionary:
	var w := make_world(null, not frames_per_tick.is_empty())
	var a := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var b := w.spawn_unit("dummy_archer", 0, Vector3(11, 0, 10))
	var c := w.spawn_unit("dummy_worker", 0, Vector3(10, 0, 11.2))
	_move(w, [a, b, c], Vector3(45, 0, 38))
	return {"world": w, "units": [a, b, c], "frames": frames_per_tick}


## The same command sequence must produce identical results no matter how many render frames
## (and of what length) happen between fixed ticks: the sim is stepped only by World.step().
func test_refresh_rate_independence() -> void:
	var tight := _simulate([])
	var w1: World = tight["world"]
	for i in 150:
		w1.step()
	var paced := _simulate([0, 1, 3, 5, 2])
	var w2: World = paced["world"]
	var pattern: Array = paced["frames"]
	var deltas := [1.0 / 30.0, 1.0 / 60.0, 1.0 / 144.0, 1.0 / 240.0, 0.05]
	var frames := 0
	for i in 150:
		w2.step()
		for f in int(pattern[i % pattern.size()]):
			for u: Unit in paced["units"]:
				if u.view != null:
					u.view._process(deltas[f % deltas.size()])
			await tree.process_frame
			frames += 1
	assert_true(frames > 100, "render frames happened between ticks (%d)" % frames)
	assert_eq(w1.tick_count, w2.tick_count, "same tick count")
	for i in 3:
		var p1: Vector3 = tight["units"][i].pos
		var p2: Vector3 = paced["units"][i].pos
		assert_eq(p1, p2, "unit %d position identical" % i)
		assert_eq(tight["units"][i].facing, paced["units"][i].facing, "unit %d facing identical" % i)


## World only advances in _physics_process (fixed 30 Hz), never in _process.
func test_world_ticks_only_on_physics_frames() -> void:
	var w := make_world()
	w.auto_tick = true
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	_move(w, [u], Vector3(30, 0, 10))
	var phys := [0]
	var count := func() -> void: phys[0] += 1
	tree.physics_frame.connect(count)
	var start := w.tick_count
	for i in 20:
		await tree.process_frame
	tree.physics_frame.disconnect(count)
	assert_eq(w.tick_count - start, phys[0], "one sim tick per physics frame")
	assert_eq(Engine.physics_ticks_per_second, 30, "project runs the fixed tick at 30 Hz")
	w.auto_tick = false


func test_shift_queue() -> void:
	var w := make_world()
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var a := Vector3(25, 0, 10)
	var b := Vector3(25, 0, 30)
	_move(w, [u], a)
	_move(w, [u], b, true)
	w.step()
	assert_eq(u.orders.size(), 1, "second order queued")
	var closest_a := INF
	for t in 600:
		w.step()
		closest_a = minf(closest_a, Grid.flat_dist(u.pos, a))
		if u.current == null:
			break
	assert_lt(closest_a, 0.3, "visited first waypoint")
	assert_lt(Grid.flat_dist(u.pos, b), 0.3, "ended at queued waypoint")


func test_stop_and_hold() -> void:
	var w := make_world()
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	_move(w, [u], Vector3(40, 0, 10))
	for i in 20:
		w.step()
	w.issue({"type": "stop", "player": 0, "units": [u.id]})
	w.step()
	var p := u.pos
	for i in 30:
		w.step()
	assert_true(u.current == null, "stop clears orders")
	assert_lt(Grid.flat_dist(u.pos, p), 0.01, "stopped unit stays")
	# hold: a walker passing through must not shove the holder
	w.issue({"type": "hold", "player": 0, "units": [u.id]})
	var walker := w.spawn_unit("dummy_soldier", 0, u.pos + Vector3(-6, 0, 0))
	w.step()
	var hold_pos := u.pos
	_move(w, [walker], u.pos + Vector3(6, 0, 0))
	for i in 200:
		w.step()
	assert_lt(Grid.flat_dist(u.pos, hold_pos), 0.05, "holding unit not pushed")
	assert_true(u.holding, "still holding")


func test_idle_ally_is_pushed_aside() -> void:
	var w := make_world()
	var idle := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var walker := w.spawn_unit("dummy_soldier", 0, Vector3(14, 0, 20))
	var goal := Vector3(26, 0, 20)
	_move(w, [walker], goal)
	run_until_idle(w, [walker], 400)
	assert_lt(Grid.flat_dist(walker.pos, goal), 0.5, "walker got through")
	assert_true(Grid.flat_dist(idle.pos, Vector3(20, 0, 20)) > 0.2, "idle ally was pushed aside")


func test_patrol_loops() -> void:
	var w := make_world()
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var start := u.pos
	var far := Vector3(22, 0, 10)
	_move(w, [u], far, false, "patrol")
	var reached_far := false
	var returned := false
	for t in 600:
		w.step()
		if Grid.flat_dist(u.pos, far) < 0.3:
			reached_far = true
		if reached_far and Grid.flat_dist(u.pos, start) < 0.3:
			returned = true
	assert_true(reached_far and returned, "patrol went out and came back")
	assert_true(u.current != null and u.current.type == Order.Type.PATROL, "patrol continues")


@warning_ignore("integer_division")
func test_group_move_spreads_without_overlap() -> void:
	var w := make_world()
	var units: Array = []
	for i in 12:
		units.append(w.spawn_unit("dummy_soldier", 0, Vector3(10 + (i % 4) * 1.2, 0, 10 + (i / 4) * 1.2)))
	var goal := Vector3(45, 0, 40)
	_move(w, units, goal)
	var ticks := run_until_idle(w, units, 900)
	assert_lt(float(ticks), 900.0, "group settled")
	var centre := Vector3.ZERO
	for u: Unit in units:
		centre += u.pos
	centre /= units.size()
	assert_lt(Grid.flat_dist(centre, goal), 2.5, "group centred on goal")
	var worst := INF
	for i in units.size():
		for j in range(i + 1, units.size()):
			var a: Unit = units[i]
			var b: Unit = units[j]
			worst = minf(worst, Grid.flat_dist(a.pos, b.pos) / (a.radius + b.radius))
	assert_true(worst > 0.8, "units do not overlap (worst ratio %f)" % worst)


func test_units_walk_around_buildings() -> void:
	var w := make_world()
	var hall := w.spawn_unit("dummy_hall", 0, Vector3(30, 0, 20))
	var u := w.spawn_unit("dummy_worker", 0, Vector3(20, 0, 20))
	var goal := Vector3(40, 0, 20)
	_move(w, [u], goal)
	var inside := false
	for t in 600:
		w.step()
		if hall.footprint.has_point(Grid.world_to_cell(u.pos)):
			inside = true
		if u.current == null:
			break
	assert_false(inside, "never entered the footprint")
	assert_lt(Grid.flat_dist(u.pos, goal), 0.3, "arrived behind the building")


func test_enemy_units_cannot_be_commanded() -> void:
	var w := make_world()
	var enemy := w.spawn_unit("dummy_soldier", 1, Vector3(10, 0, 10))
	w.issue({"type": "move", "player": 0, "units": [enemy.id], "pos": Vector3(30, 0, 10)})
	w.step()
	assert_true(enemy.current == null, "command for foreign unit ignored")


func test_200_units_tick_cost() -> void:
	var w := make_world(flat_map(96, 96, 1))
	var rng := RandomNumberGenerator.new()
	rng.seed = 99
	var units: Array = []
	for i in 200:
		var p := Vector3(rng.randf_range(10, 182), 0, rng.randf_range(10, 182))
		units.append(w.spawn_unit("dummy_soldier" if i % 3 else "dummy_worker", i % 2, p))
	for i in 200:
		var u: Unit = units[i]
		w.issue({"type": "move", "player": u.player_id, "units": [u.id],
			"pos": Vector3(rng.randf_range(10, 182), 0, rng.randf_range(10, 182))})
	var t0 := Time.get_ticks_usec()
	for i in 90:
		w.step()
	var per_tick := (Time.get_ticks_usec() - t0) / 90.0 / 1000.0
	print("     200 units: %.2f ms per tick (budget %.1f ms)" % [per_tick, 1000.0 / 30.0])
	assert_lt(per_tick, 1000.0 / 30.0, "200 moving units fit in one 30 Hz tick")
