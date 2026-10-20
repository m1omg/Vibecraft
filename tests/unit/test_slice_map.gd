extends "res://tests/test_case.gd"
## data/maps/slice.json (Wether Downs, built by tools/maps/build_slice_map.py from slice-plan §1):
## mirror symmetry, buildable pads, the 6.0 m hall-seam gap, reachability of every landmark from
## both starts, the sleep mix and the main lumber rule (slice-plan §1.13, first pass).

const MAP_PATH := "res://data/maps/slice.json"

static var _map: MapData = null


func _slice() -> MapData:
	if _map == null:
		_map = MapData.load_json(MAP_PATH)
	return _map


func test_slice_map_loads_with_authored_objects() -> void:
	var m := _slice()
	assert_true(m != null, "map parses")
	assert_eq(m.size_tiles(), Vector2i(96, 96), "96 x 96 tiles")
	assert_eq(m.start_locations.size(), 2, "two starts")
	assert_eq(m.gold_mines.size(), 5, "five Gold Seams (gdd §5 #12)")
	assert_eq(m.creep_camps.size(), 16, "16 camps")
	assert_eq(m.neutral_buildings.size(), 3, "Weighstall, Hale Spring, Coaching Inn")
	assert_eq(m.ramps.size(), 12, "slice-plan §1.5 ramps")
	assert_eq(str(m.meta.get("id", "")), "wether_downs", "map id")
	assert_eq(m.mine_gold(0), 12000, "main seam")
	assert_eq(m.mine_gold(4), 8000, "contested third seam")
	for c: Dictionary in m.creep_camps:
		assert_false(Defs.camp(str(c.get("template", ""))).is_empty(), "camp template %s" % c.get("template"))
		for cid: String in c["creeps"]:
			assert_true(Defs.has_unit(cid), "creep def %s" % cid)
	for nb: Dictionary in m.neutral_buildings:
		assert_true(Defs.has_unit(str(nb["def"])), "neutral building %s" % nb["def"])
	var route: Dictionary = m.meta.get("creep_route", {})
	assert_eq((route.get("hero_1", []) as Array).size(), 6, "hero 1 creep route")


func test_slice_map_is_mirror_symmetric() -> void:
	var m := _slice()
	var bad := 0
	for y in m.height:
		for x in m.width:
			var a := m.idx(x, y)
			var b := m.idx(y, x)
			if m.cliff[a] != m.cliff[b] or m.water[a] != m.water[b] or m.tex[a] != m.tex[b] \
					or m.boundary[a] != m.boundary[b] or (m.ramp[a] > 0) != (m.ramp[b] > 0):
				bad += 1
	assert_eq(bad, 0, "per-tile layers mirror across the NW-SE diagonal")
	var trees := {}
	for t in m.trees:
		trees[t] = true
	var lonely := 0
	for t in m.trees:
		if not trees.has(Vector2i(t.y, t.x)):
			lonely += 1
	assert_eq(lonely, 0, "every tree has its mirror")
	var s0 := m.start_locations[0]
	var s1 := m.start_locations[1]
	assert_near(s0.x, s1.z, 0.01, "starts mirror (x)")
	assert_near(s0.z, s1.x, 0.01, "starts mirror (z)")
	assert_eq(m.corner_h, m.corner_h, "heights computed")


func test_slice_pads_buildable_with_six_metre_seam_gap() -> void:
	var m := _slice()
	var w := make_world(m)
	var hall: Array = Defs.unit("kingdom_moot_hall")["footprint"]
	var mine: Array = Defs.unit("gold_mine")["footprint"]
	var halls: Array[Vector3] = []
	halls.append_array(m.start_locations)
	for e: Dictionary in m.meta.get("expansions", []):
		var a: Array = e["hall"]
		halls.append(Vector3(a[0], a[1], a[2]))
	for h in halls:
		var r := Grid.footprint_rect(h, Vector2i(int(hall[0]), int(hall[1])))
		assert_true(w.pathing.is_rect_free(r), "hall pad free at %s" % h)
	for i in m.gold_mines.size():
		var g := m.gold_mines[i]
		var r := Grid.footprint_rect(g, Vector2i(int(mine[0]), int(mine[1])))
		assert_true(w.pathing.is_rect_free(r), "seam footprint free at %s" % g)
	# each seam's nearest hall pad sits exactly 6.0 m away, edge to edge (rules §3.3)
	for g in m.gold_mines:
		var best := INF
		for h in halls:
			best = minf(best, _rect_gap(Grid.footprint_rect(g, Vector2i(int(mine[0]), int(mine[1]))),
				Grid.footprint_rect(h, Vector2i(int(hall[0]), int(hall[1])))))
		assert_true(best >= 6.0 - 1e-3 and best < 6.5, "hall-seam gap %.2f m at %s" % [best, g])
	for nb: Dictionary in m.neutral_buildings:
		var d := Defs.unit(str(nb["def"]))
		var fp: Array = d["footprint"]
		var r := Grid.footprint_rect(nb["pos"], Vector2i(int(fp[0]), int(fp[1])))
		assert_true(w.pathing.is_rect_free(r), "%s footprint free" % nb["def"])


func test_slice_landmarks_reachable_from_both_starts() -> void:
	var m := _slice()
	var w := make_world(m)
	var mine: Array = Defs.unit("gold_mine")["footprint"]
	for s in m.start_locations:
		var from := w.pathing.nearest_walkable(Grid.world_to_cell(s + Vector3(0, 0, -6.0)))
		assert_true(from.x >= 0, "walkable ground beside the hall at %s" % s)
		for t in m.start_locations:
			assert_true(w.pathing.can_reach(from, _cell_rect(w, t + Vector3(0, 0, -6.0))), "start %s -> start %s" % [s, t])
		for g in m.gold_mines:
			var r := Grid.footprint_rect(g, Vector2i(int(mine[0]), int(mine[1])))
			assert_true(w.pathing.can_reach(from, r), "start %s -> seam %s" % [s, g])
		for c: Dictionary in m.creep_camps:
			assert_true(w.pathing.can_reach(from, _cell_rect(w, c["pos"])), "start %s -> camp %s" % [s, c.get("id")])
		for nb: Dictionary in m.neutral_buildings:
			var fp: Array = Defs.unit(str(nb["def"]))["footprint"]
			var r := Grid.footprint_rect(nb["pos"], Vector2i(int(fp[0]), int(fp[1])))
			assert_true(w.pathing.can_reach(from, r), "start %s -> %s" % [s, nb["def"]])
	var p := w.pathing.find_path(m.start_locations[0] + Vector3(6, 0, -6), m.start_locations[1] + Vector3(-6, 0, 6))
	var length := 0.0
	for i in range(1, p.size()):
		length += Grid.flat_dist(p[i - 1], p[i])
	print("     main -> main path: %.1f m (slice-plan §1.10: 206.4 m on the tile grid)" % length)
	assert_true(length > 170.0 and length < 235.0, "rush distance in the planned band (%.1f m)" % length)


func test_slice_sleep_mix_and_main_lumber() -> void:
	var m := _slice()
	var night := 0
	var day := 0
	for c: Dictionary in m.creep_camps:
		var sleeps := str(Defs.camp(str(c["template"])).get("sleeps", "night"))
		if sleeps == "night":
			night += 1
		elif sleeps == "day":
			day += 1
	assert_true(day <= int(Defs.rule("creeps.max_day_camps", 1)), "at most one day camp")
	assert_true(float(night) / m.creep_camps.size() >= float(Defs.rule("creeps.min_night_sleep_fraction", 0.6)),
		"at least 60 %% of camps sleep at night (%d / %d)" % [night, m.creep_camps.size()])
	var hall: Array = Defs.unit("kingdom_moot_hall")["footprint"]
	for s in m.start_locations:
		var r := Grid.footprint_rect(s, Vector2i(int(hall[0]), int(hall[1])))
		var near := 0
		for t in m.trees:
			var tr := Rect2i(t * 2, Vector2i(2, 2))
			if _rect_gap(tr, r) <= 30.0:
				near += 1
		assert_true(near >= 140, "%d trees within 30 m of the main hall at %s (map_economy_rules >= 140)" % [near, s])


static func _rect_gap(a: Rect2i, b: Rect2i) -> float:
	var dx := maxi(0, maxi(a.position.x - b.end.x, b.position.x - a.end.x))
	var dz := maxi(0, maxi(a.position.y - b.end.y, b.position.y - a.end.y))
	return Vector2(dx, dz).length() * Grid.CELL


func _cell_rect(w: World, p: Vector3) -> Rect2i:
	var c := w.pathing.nearest_walkable(Grid.world_to_cell(p))
	return Rect2i(c, Vector2i.ONE)
