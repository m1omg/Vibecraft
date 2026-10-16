extends "res://tests/test_case.gd"

var _map: MapData


func _generated() -> MapData:
	if _map == null:
		_map = MapGenerator.test_map()
	return _map


func test_generated_layout() -> void:
	var m := _generated()
	assert_eq(m.size_tiles(), Vector2i(96, 96))
	assert_eq(m.start_locations.size(), 2, "two start locations")
	assert_eq(m.gold_mines.size(), 2, "one mine per start")
	assert_eq(m.creep_camps.size(), 4, "four creep camps")
	assert_true(m.trees.size() > 1500, "forests placed (%d trees)" % m.trees.size())
	assert_true(m.ramps.size() >= 8, "ramps placed (%d)" % m.ramps.size())
	var levels := {}
	var water := 0
	for i in m.cliff.size():
		levels[m.cliff[i]] = true
		water += m.water[i]
	assert_true(levels.has(0) and levels.has(1) and levels.has(2) and levels.has(3), "levels 0-3 used")
	assert_true(water > 40, "lake present (%d tiles)" % water)


func test_generation_is_deterministic() -> void:
	var a := MapGenerator.test_map(5)
	var b := MapGenerator.test_map(5)
	assert_eq(a.cliff, b.cliff, "cliff layer")
	assert_eq(a.tex, b.tex, "texture layer")
	assert_eq(a.trees, b.trees, "trees")


func test_map_is_point_symmetric() -> void:
	var m := _generated()
	for y in m.height:
		for x in m.width:
			if m.cliff[m.idx(x, y)] != m.cliff[m.idx(95 - x, 95 - y)]:
				fail("cliff asymmetric at %d,%d" % [x, y])
				return
	var s0 := m.start_locations[0]
	var s1 := m.start_locations[1]
	assert_near(s0.x + s1.x, 192.0, 0.01, "starts mirrored")


func test_ramps_connect_levels() -> void:
	var m := _generated()
	for r in m.ramps:
		var rect: Rect2i = r["rect"]
		var dir: Vector2i = r["dir"]
		var low: int = r["low"]
		var centre := Vector3((rect.position.x + rect.size.x * 0.5) * Grid.TILE, 0,
			(rect.position.y + rect.size.y * 0.5) * Grid.TILE)
		var half_len := (rect.size.x if dir.x != 0 else rect.size.y) * Grid.TILE * 0.5
		var d3 := Vector3(dir.x, 0, dir.y)
		var below := centre - d3 * (half_len + 1.0)
		var above := centre + d3 * (half_len + 1.0)
		assert_near(m.height_at_v(below), low * Grid.CLIFF_H, 0.01, "ramp %s low side" % rect)
		assert_near(m.height_at_v(above), (low + 1) * Grid.CLIFF_H, 0.01, "ramp %s high side" % rect)
		assert_near(m.height_at_v(centre), (low + 0.5) * Grid.CLIFF_H, 0.01, "ramp %s mid" % rect)


func test_height_and_walls_on_manual_map() -> void:
	var m := flat_map(8, 8, 0)
	for y in 8:
		for x in range(4, 8):
			m.cliff[m.idx(x, y)] = 1
	m.add_ramp(Rect2i(3, 2, 2, 3), Vector2i(1, 0), 0)
	m.compute_heights()
	assert_near(m.height_at(1.0, 1.0), 0.0, 0.0001, "low ground")
	assert_near(m.height_at(12.0, 1.0), Grid.CLIFF_H, 0.0001, "high ground")
	assert_near(m.height_at(8.0, 6.0), Grid.CLIFF_H * 0.5, 0.0001, "ramp middle")
	assert_true(m.has_wall_x(4, 0), "cliff wall between levels")
	assert_false(m.has_wall_x(3, 3), "no wall at ramp bottom")
	assert_false(m.has_wall_x(5, 3), "no wall at ramp top")
	var blocked := m.compute_blocked_cells()
	var cw := m.width * Grid.CELLS_PER_TILE
	assert_eq(blocked[4 * cw + 15], 1, "cell left of the wall blocked")
	assert_eq(blocked[4 * cw + 16], 1, "cell right of the wall blocked")
	assert_eq(blocked[13 * cw + 16], 0, "ramp interior walkable")


func test_json_roundtrip() -> void:
	var m := _generated()
	var text := JSON.stringify(m.to_dict())
	var back := MapData.from_dict(JSON.parse_string(text))
	assert_eq(back.cliff, m.cliff, "cliff")
	assert_eq(back.tex, m.tex, "tex")
	assert_eq(back.water, m.water, "water")
	assert_eq(back.ramps.size(), m.ramps.size(), "ramps")
	assert_eq(back.trees.size(), m.trees.size(), "trees")
	assert_eq(back.creep_camps.size(), 4, "camps")
	assert_eq(back.corner_h, m.corner_h, "heights rebuilt identically")


func test_start_locations_buildable() -> void:
	var m := _generated()
	var w := make_world(m)
	var hall := Defs.unit("dummy_hall")
	var mine := Defs.unit("gold_mine")
	for s in m.start_locations:
		var r := Grid.footprint_rect(s, Vector2i(hall["footprint"][0], hall["footprint"][1]))
		assert_true(w.pathing.is_rect_free(r), "hall footprint free at %s" % s)
	for g in m.gold_mines:
		var r := Grid.footprint_rect(g, Vector2i(mine["footprint"][0], mine["footprint"][1]))
		assert_true(w.pathing.is_rect_free(r), "mine footprint free at %s" % g)


func test_raycast_hits_ground() -> void:
	var m := _generated()
	var target := m.start_locations[0]
	var origin := target + Vector3(0, 30, 20)
	var hit := m.raycast(origin, target - origin)
	assert_lt(hit.distance_to(target), 0.2, "ray hits the aimed ground point")
	assert_eq(m.raycast(Vector3(10, 10, 10), Vector3.UP), Vector3.INF, "upward ray misses")
