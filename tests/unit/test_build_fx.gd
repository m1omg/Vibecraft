extends "res://tests/test_case.gd"
## Economy and building juice (src/fx/build_fx.gd; juice BLD-04, BLD-08, BLD-09, BLD-16,
## ECO-04, ECO-11, ECO-16) in a visual world: the site stamp, one hammer stroke per work stroke
## on its contact frame, the completion flourish with the food popup, the felled tree, a
## delivery and a cave-in. Visual and audio only: the sim never waits on any of it.

var _was_manual := false


func before_each() -> void:
	_was_manual = FxClock.manual
	FxClock.manual = true
	FxClock.reset(10.0)


func after_each() -> void:
	cleanup()
	FxClock.manual = _was_manual
	Audio.reset_state()


func _visual_world() -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(flat_map(48, 48), 1)
	var p := w.add_player(0, 0, "kingdom")
	p.gold = 2000
	p.lumber = 2000
	w.local_player_id = 0
	w.add_player(1, 1, "clans")
	return w


func _frame(vfx: Vfx) -> void:
	FxClock.advance(World.DT, true)
	vfx.build._process(World.DT)


func test_site_stamp_strokes_and_completion() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 30))
	w.issue({"type": "build", "player": 0, "units": [hod.id], "def": "kingdom_croft", "pos": Vector3(40, 0, 30)})
	var rings := vfx.marks.count_kind(GroundMarks.Kind.DUST_RING)
	var site: Unit = null
	for i in 30 * 8:
		w.step()
		_frame(vfx)
		for u in w.unit_list:
			if u.def_id == "kingdom_croft":
				site = u
		if site != null:
			break
	assert_true(site != null, "the site started")
	assert_eq(int(vfx.build.counts.get("stamp", 0)), 1, "one stamp")
	assert_true(vfx.marks.count_kind(GroundMarks.Kind.DUST_RING) > rings, "its dust ring")
	var flashes := vfx.marks.count_kind(GroundMarks.Kind.FLASH_RING)
	var popups_before := vfx.popups.spawned
	var t0 := w.time
	while site.under_construction and w.time - t0 < 60.0:
		w.step()
		_frame(vfx)
	_frame(vfx)
	var strokes := int(vfx.build.counts.get("stroke", 0))
	var expected := (w.time - t0) / (Construction.STROKE_TICKS * World.DT)
	assert_near(float(strokes), expected, 3.0, "one hammer stroke per work stroke (%d of ~%.0f)" % [strokes, expected])
	assert_eq(int(vfx.build.counts.get("complete", 0)), 1, "the completion flourish")
	assert_true(vfx.marks.count_kind(GroundMarks.Kind.FLASH_RING) > flashes, "its flash ring")
	assert_eq(vfx.popups.spawned - popups_before, 1, "the +7 food popup (ECO-16)")


func test_tree_delivery_and_cave_in() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(24, 0, 24))
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 30))
	Events.tree_felled.emit(Vector3(10, 0, 10))
	Events.cargo_delivered.emit(hod, hall, "gold", 10)
	_frame(vfx)
	assert_eq(int(vfx.build.counts.get("tree", 0)), 1, "the tree falls with splinters and a thud")
	assert_eq(int(vfx.build.counts.get("cargo", 0)), 1, "the coins land")
	var croft := w.spawn_unit("kingdom_croft", 1, Vector3(36, 0, 36))
	croft.take_damage(99999.0, null)
	w.step()
	_frame(vfx)
	assert_eq(int(vfx.build.counts.get("collapse", 0)), 1, "the cave-in")
