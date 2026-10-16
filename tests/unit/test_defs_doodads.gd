extends "res://tests/test_case.gd"


func test_defs_load_without_errors() -> void:
	assert_eq(Defs.errors.size(), 0, "validation errors: %s" % str(Defs.errors))
	for id in ["dummy_worker", "dummy_soldier", "dummy_archer", "dummy_hall", "dummy_barracks", "gold_mine"]:
		assert_true(Defs.has_unit(id), "def %s present" % id)
	var w := Defs.unit("dummy_worker")
	assert_true(float(w["hp"]) > 0.0, "worker hp")
	assert_true((w["flags"] as Array).has("worker"), "worker flag")
	assert_true(Defs.unit("dummy_soldier").has("turn_rate"), "defaults filled")
	assert_false(Defs.ability("dummy_bolt").is_empty(), "ability lookup")
	assert_false(Defs.doodad("tree_pine").is_empty(), "doodad lookup")


func test_defs_validation_catches_bad_defs() -> void:
	var before := Defs.errors.size()
	Defs._validate_unit("broken", {"kind": "unit", "hp": 0, "radius": 0.4, "speed": 0.0,
		"footprint": [0, 0], "abilities": ["nope"], "trains": []})
	var added := Defs.errors.size() - before
	Defs.errors.resize(before)
	assert_true(added >= 3, "missing name, bad hp, zero speed, unknown ability reported (%d)" % added)


func test_tree_harvest_and_removal_updates_pathing() -> void:
	var m := flat_map(16, 16)
	m.trees.append(Vector2i(10, 10))
	m.tree_types.append(0)
	m.trees.append(Vector2i(12, 10))
	m.tree_types.append(1)
	var w := make_world(m)
	var d := w.doodads
	assert_eq(d.alive_count, 2)
	var cell := Vector2i(20, 20)
	assert_eq(d.tree_at_cell(cell), 0, "tree found by cell")
	assert_false(w.pathing.is_walkable(cell), "tree blocks its cells")
	assert_false(w.pathing.is_walkable(Vector2i(21, 21)), "tree covers 2x2 cells")
	assert_eq(d.nearest_tree(Vector3(12.0, 0, 10.4), 3.0), 1, "nearest tree")
	var felled := [0]
	var on_felled := func(_p: Vector3) -> void: felled[0] += 1
	Events.tree_felled.connect(on_felled)
	assert_eq(d.harvest(0, 10), 10, "harvest takes requested lumber")
	assert_eq(d.lumber[0], 40)
	assert_eq(d.harvest(0, 100), 40, "harvest capped by remaining lumber")
	Events.tree_felled.disconnect(on_felled)
	assert_eq(felled[0], 1, "tree_felled emitted")
	assert_eq(d.alive_count, 1)
	assert_eq(d.tree_at_cell(cell), -1, "depleted tree gone")
	assert_true(w.pathing.is_walkable(cell) and w.pathing.is_walkable(Vector2i(21, 21)), "cells freed")
	assert_eq(d.harvest(0, 5), 0, "nothing left")
