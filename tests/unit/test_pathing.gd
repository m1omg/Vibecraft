extends "res://tests/test_case.gd"


func _pathing(m: MapData = null) -> Pathing:
	var p := Pathing.new()
	p.setup(m if m != null else flat_map(32, 32))
	return p


func _path_len(path: PackedVector3Array) -> float:
	var total := 0.0
	for i in range(1, path.size()):
		total += Grid.flat_dist(path[i - 1], path[i])
	return total


func _path_is_walkable(p: Pathing, path: PackedVector3Array, large: bool = false) -> bool:
	for i in range(1, path.size()):
		var a := path[i - 1]
		var b := path[i]
		var steps := ceili(Grid.flat_dist(a, b) / 0.1)
		for s in steps + 1:
			if not p.is_walkable_world(a.lerp(b, float(s) / steps), large):
				return false
	return true


func test_straight_path_when_clear() -> void:
	var p := _pathing()
	var path := p.find_path(Vector3(5, 0, 5), Vector3(40, 0, 30))
	assert_eq(path.size(), 2, "open field path is a single segment")
	assert_near(Grid.flat_dist(path[path.size() - 1], Vector3(40, 0, 30)), 0.0, 0.01, "ends at goal")


func test_path_around_obstacle() -> void:
	var p := _pathing()
	p.set_footprint_rect(Rect2i(40, 10, 4, 90), true)   # wall x 20..22 m, z 5..50 m
	var from := Vector3(10, 0, 30)
	var to := Vector3(40, 0, 30)
	var path := p.find_path(from, to)
	assert_true(path.size() >= 3, "path bends around the wall (got %d points)" % path.size())
	assert_near(Grid.flat_dist(path[path.size() - 1], to), 0.0, 0.01, "reaches goal")
	assert_true(_path_is_walkable(p, path), "every segment is walkable")
	assert_true(_path_len(path) > Grid.flat_dist(from, to) + 10.0, "detour is longer than direct")
	var max_z := 0.0
	for q in path:
		max_z = maxf(max_z, q.z)
	assert_true(max_z >= 50.0, "goes around the wall end (max z %f)" % max_z)


func test_unreachable_goal_inside_closed_ring() -> void:
	var p := _pathing()
	# 1-cell thick closed ring around cells (60..69, 60..69)
	p.set_footprint_rect(Rect2i(59, 59, 12, 1), true)
	p.set_footprint_rect(Rect2i(59, 70, 12, 1), true)
	p.set_footprint_rect(Rect2i(59, 60, 1, 10), true)
	p.set_footprint_rect(Rect2i(70, 60, 1, 10), true)
	var goal := Grid.cell_to_world(Vector2i(65, 65))
	assert_true(p.is_walkable_world(goal), "goal cell itself is walkable")
	var path := p.find_path(Vector3(5, 0, 5), goal)
	assert_true(path.size() >= 2, "partial path returned")
	var end := path[path.size() - 1]
	assert_true(p.is_walkable_world(end), "partial path ends on a walkable cell")
	assert_lt(Grid.flat_dist(end, goal), 4.5, "ends next to the ring, closest to the goal")
	var ec := Grid.world_to_cell(end)
	assert_false(ec.x >= 60 and ec.x < 70 and ec.y >= 60 and ec.y < 70, "does not enter the ring")


func test_blocked_goal_snaps_to_nearest_walkable() -> void:
	var p := _pathing()
	var r := Rect2i(40, 40, 10, 10)
	p.set_footprint_rect(r, true)
	var centre := Grid.rect_center_world(r)
	var path := p.find_path(Vector3(5, 0, 22.5), centre)
	assert_true(path.size() >= 2, "path found")
	var end := path[path.size() - 1]
	assert_true(p.is_walkable_world(end), "end is walkable")
	assert_lt(Grid.flat_dist(end, centre), 3.2, "snapped to the footprint edge")


func test_footprint_blocking_and_release() -> void:
	var p := _pathing()
	var r := Rect2i(30, 0, 6, 128)   # full-height wall except border is already blocked
	var cells := Grid.rect_cells(r)
	p.set_footprint(cells, true)
	assert_false(p.is_walkable(Vector2i(32, 50)), "footprint cell blocked")
	var path := p.find_path(Vector3(5, 0, 30), Vector3(40, 0, 30))
	assert_true(path.size() >= 2, "partial path exists")
	assert_lt(Grid.flat_dist(path[path.size() - 1], Vector3(14.75, 0, 30)), 1.0, "stops at the wall")
	# overlapping footprint is reference counted
	p.set_footprint_rect(Rect2i(30, 40, 2, 2), true)
	p.set_footprint(cells, false)
	assert_false(p.is_walkable(Vector2i(30, 40)), "overlapping footprint still blocks")
	assert_true(p.is_walkable(Vector2i(32, 50)), "released cell walkable")
	path = p.find_path(Vector3(5, 0, 30), Vector3(40, 0, 30))
	assert_eq(path.size(), 2, "straight again after release")


func test_large_units_avoid_narrow_gaps() -> void:
	var p := _pathing()
	# wall at x cells 60..61 with a 2-cell (1 m) gap at y 50..51
	p.set_footprint_rect(Rect2i(60, 1, 2, 49), true)
	p.set_footprint_rect(Rect2i(60, 52, 2, 75), true)
	var from := Vector3(20, 0, 25.5)
	var to := Vector3(40, 0, 25.5)
	var small := p.find_path(from, to, false)
	var large := p.find_path(from, to, true)
	assert_lt(Grid.flat_dist(small[small.size() - 1], to), 0.1, "small unit reaches goal")
	assert_lt(_path_len(small), 22.0, "small unit uses the gap")
	assert_true(Grid.flat_dist(large[large.size() - 1], to) > 1.0, "large unit cannot pass the gap")


func test_query_budget() -> void:
	var p := _pathing()
	p.max_queries_per_tick = 3
	p.begin_tick()
	for i in 3:
		assert_true(p.has_budget(), "budget left before query %d" % i)
		p.find_path(Vector3(5, 0, 5), Vector3(10, 0, 10))
	assert_false(p.has_budget(), "budget exhausted")
	p.begin_tick()
	assert_true(p.has_budget(), "budget resets each tick")


func test_line_of_walk() -> void:
	var p := _pathing()
	p.set_footprint_rect(Rect2i(40, 40, 4, 4), true)
	assert_false(p.line_of_walk(Vector3(15, 0, 21), Vector3(30, 0, 21)), "blocked line")
	assert_true(p.line_of_walk(Vector3(15, 0, 30), Vector3(30, 0, 30)), "clear line")


func test_generated_map_starts_connected() -> void:
	var m := MapGenerator.test_map()
	var w := make_world(m)
	var s0 := m.start_locations[0] + Vector3(0, 0, -8)
	var s1 := m.start_locations[1] + Vector3(0, 0, 8)
	var path := w.pathing.find_path(s0, s1)
	assert_true(path.size() >= 2, "path between starts")
	assert_lt(Grid.flat_dist(path[path.size() - 1], s1), 1.0, "start locations are connected")
	var large := w.pathing.find_path(s0, s1, true)
	assert_lt(Grid.flat_dist(large[large.size() - 1], s1), 1.0, "connected for large units too")
	for i in 4:
		var camp: Vector3 = m.creep_camps[i]["pos"]
		var to_camp := w.pathing.find_path(s0, camp)
		assert_lt(Grid.flat_dist(to_camp[to_camp.size() - 1], camp), 2.0, "camp %d reachable" % i)


func test_regions_split_and_merge() -> void:
	var p := _pathing()
	var a := Vector2i(20, 64)
	var b := Vector2i(100, 64)
	assert_true(p.same_region(a, b), "open field is one region")
	# a full-height wall splits the map; labels catch up within a few ticks
	p.set_footprint_rect(Rect2i(60, 0, 2, 128), true)
	assert_true(p._labels_dirty, "a wall across the map may split: relabel scheduled")
	for i in 30:
		p.begin_tick()
	assert_false(p.same_region(a, b), "wall splits regions")
	var path := p.find_path(Grid.cell_to_world(a), Grid.cell_to_world(b))
	assert_lt(Grid.flat_dist(path[path.size() - 1], Vector3(29.75, 0, 32.25)), 0.6, "snaps to the wall")
	# opening a 1-cell-wide hole merges immediately
	p.set_footprint_rect(Rect2i(60, 64, 2, 2), false)
	assert_true(p.same_region(a, b), "opening merges regions")
	assert_false(p.same_region(a, b, true), "too narrow for large units")
	p.set_footprint_rect(Rect2i(60, 62, 2, 6), false)
	assert_true(p.same_region(a, b, true), "wide opening merges the large grid too")


func test_unreachable_query_is_cheap() -> void:
	var m := MapGenerator.test_map()
	var w := make_world(m)
	var s0 := m.start_locations[0] + Vector3(0, 0, -8)
	var t := Time.get_ticks_usec()
	var corner := w.pathing.find_path(s0, Vector3(1, 0, 1))
	var ms := (Time.get_ticks_usec() - t) / 1000.0
	assert_true(corner.size() >= 2, "path towards the forested corner")
	assert_lt(ms, 25.0, "unreachable goal resolved quickly (%.1f ms)" % ms)
	t = Time.get_ticks_usec()
	var s1 := m.start_locations[1] + Vector3(0, 0, 8)
	for i in 10:
		w.pathing.find_path(s0, s1)
	ms = (Time.get_ticks_usec() - t) / 10000.0
	print("     cross-map path: %.2f ms" % ms)
	assert_lt(ms, 8.0, "cross-map path cost")


func test_relabel_only_when_a_split_is_possible() -> void:
	var m := MapGenerator.test_map()
	var w := make_world(m)
	var p := w.pathing
	var r := Grid.footprint_rect(m.start_locations[0] + Vector3(12, 0, -12), Vector2i(8, 8))
	assert_true(p.is_rect_free(r), "test site is free")
	p.set_footprint_rect(r, true)
	assert_false(p._labels_dirty, "building in the open cannot split a region: no relabel")
	# force a full background relabel and measure its per-tick cost
	p._labels_dirty = true
	var ticks := 0
	var worst := 0.0
	while ticks < 300:
		var t := Time.get_ticks_usec()
		p.begin_tick()
		worst = maxf(worst, (Time.get_ticks_usec() - t) / 1000.0)
		ticks += 1
		if p._job.is_empty() and not p._labels_dirty:
			break
	print("     full relabel: %d ticks, worst %.2f ms/tick" % [ticks, worst])
	assert_lt(float(ticks), 150.0, "relabel finishes within ~5 s of sim time")
	assert_lt(worst, 8.0, "relabel step stays bounded")
	var s0 := Grid.world_to_cell(m.start_locations[0] + Vector3(0, 0, -8))
	var s1 := Grid.world_to_cell(m.start_locations[1] + Vector3(0, 0, 8))
	assert_true(p.same_region(s0, s1), "labels still correct after relabel")
