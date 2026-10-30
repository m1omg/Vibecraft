extends "res://tests/test_case.gd"
## Construction (src/systems/construction.gd, rules §4.6–§4.8): a build order checks the cost at
## order time and pays on arrival, the site starts at 10 % HP and rises with progress, the finished
## building gives its food and the builder goes idle; placement rules; the kingdom's Hod Chain
## (1 / 1.4 / 1.8 ×, extra builders pay 5 lumber per 10 s) against the clans' single builder;
## cancel refunds 75 %; an abandoned site waits; repair at 1.5 × build time for 30 % of the cost.


func _world(faction: String = "kingdom", gold: int = 2000, lumber: int = 2000) -> World:
	var w := make_world(flat_map(48, 48))
	var p := w.player(0)
	p.faction = faction
	p.gold = gold
	p.lumber = lumber
	return w


func _build(w: World, worker: Unit, def_id: String, at: Vector3, queue: bool = false) -> void:
	w.issue({"type": "build", "player": worker.player_id, "units": [worker.id], "def": def_id, "pos": at, "queue": queue})


func _site_of(w: World, def_id: String) -> Unit:
	for u in w.unit_list:
		if u.def_id == def_id and u.alive:
			return u
	return null


func test_a_croft_from_order_to_food() -> void:
	var w := _world()
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 30))
	var g0 := w.player(0).gold
	var l0 := w.player(0).lumber
	_build(w, hod, "kingdom_croft", Vector3(40, 0, 30))
	w.step()
	assert_true(hod.current != null and hod.current.type == Order.Type.BUILD, "the worker heads for the spot")
	assert_eq(w.player(0).gold, g0, "nothing is paid before the builder arrives")
	var site: Unit = null
	for i in 30 * 6:
		w.step()
		site = _site_of(w, "kingdom_croft")
		if site != null:
			break
	assert_true(site != null and site.under_construction, "the site started")
	assert_eq(w.player(0).gold, g0 - 95, "paid on arrival (95 gold)")
	assert_eq(w.player(0).lumber, l0 - 20, "and 20 lumber")
	assert_near(site.hp / site.max_hp, 0.1, 0.02, "the site starts at 10 % HP")
	var cap0 := w.player(0).food_cap
	var t0 := w.time
	var mid_checked := false
	while site.under_construction and w.time - t0 < 60.0:
		w.step()
		if not mid_checked and site.build_progress >= 0.5:
			mid_checked = true
			assert_near(site.hp / site.max_hp, 0.55, 0.03, "half built: 55 % HP")
	assert_false(site.under_construction, "finished")
	assert_near(w.time - t0, 38.0, 0.5, "in the Croft's 38 s build time")
	assert_eq(w.player(0).food_cap - cap0, 7, "+7 food on completion")
	assert_near(site.hp, site.max_hp, 0.01, "full HP")
	w.step()
	assert_true(hod.current == null, "the builder goes idle (rules §4.3)")


func test_cost_checked_at_order_and_placement_rules() -> void:
	var w := _world("kingdom", 50, 50)
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 30))
	_build(w, hod, "kingdom_croft", Vector3(40, 0, 30))
	w.step()
	assert_true(hod.current == null, "an unaffordable placement is refused at once")
	w.player(0).gold = 1000
	w.player(0).lumber = 1000
	var con := w.construction
	assert_true(con.can_place(0, "kingdom_croft", Vector3(40, 0, 30))["ok"], "open ground is fine")
	assert_eq(con.can_place(0, "kingdom_croft", Vector3(1, 0, 1))["reason"], "out_of_bounds", "off the map")
	var foe := w.spawn_unit("clans_grappler", 1, Vector3(40, 0, 30))
	assert_eq(con.can_place(0, "kingdom_croft", Vector3(40, 0, 30))["reason"], "blocked", "an enemy unit blocks the spot")
	foe.teleport(Vector3(70, 0, 70))
	var own := w.spawn_unit("kingdom_pavisier", 0, Vector3(40.2, 0, 30.2))
	assert_true(con.can_place(0, "kingdom_croft", Vector3(40, 0, 30))["ok"], "own units do not block")
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(20, 0, 60))
	var near := Vector3(mine.footprint.end.x * Grid.CELL + 4.0 + 4.0, 0, 60)
	assert_eq(con.can_place(0, "kingdom_moot_hall", near)["reason"], "too_close_to_mine", "a hall keeps 6 m from a seam")
	_build(w, hod, "kingdom_croft", Vector3(40, 0, 30))
	for i in 30 * 6:
		w.step()
		if _site_of(w, "kingdom_croft") != null:
			break
	var site := _site_of(w, "kingdom_croft")
	assert_true(site != null, "built over our own unit")
	var area := Rect2(site.footprint.position.x * Grid.CELL, site.footprint.position.y * Grid.CELL,
		site.footprint.size.x * Grid.CELL, site.footprint.size.y * Grid.CELL)
	assert_false(area.has_point(Vector2(own.pos.x, own.pos.z)), "our unit stepped out of the footprint")


## Build time with n kingdom builders: 1 / 1.4 / 1.8 × the rate; extra builders pay lumber.
func _hod_chain_time(n: int) -> Array:
	var w := _world()
	var hods: Array[Unit] = []
	for i in n:
		hods.append(w.spawn_unit("kingdom_hodman", 0, Vector3(30 + i, 0, 30)))
	_build(w, hods[0], "kingdom_croft", Vector3(36, 0, 30))
	var site: Unit = null
	for i in 30 * 6:
		w.step()
		site = _site_of(w, "kingdom_croft")
		if site != null:
			break
	for i in range(1, n):
		w.issue({"type": "smart", "player": 0, "units": [hods[i].id], "target": site.id})
	var l0 := w.player(0).lumber
	var t0 := w.time
	while site.under_construction and w.time - t0 < 80.0:
		w.step()
	return [w.time - t0, l0 - w.player(0).lumber]


func test_hod_chain_speeds_up_kingdom_sites() -> void:
	var one: Array = _hod_chain_time(1)
	var two: Array = _hod_chain_time(2)
	var three: Array = _hod_chain_time(3)
	assert_near(float(one[0]), 38.0, 0.6, "one Hodman: 38 s")
	assert_near(38.0 / float(two[0]), 1.4, 0.06, "two: 1.4 × (%.1f s)" % float(two[0]))
	assert_near(38.0 / float(three[0]), 1.8, 0.08, "three: 1.8 × (%.1f s)" % float(three[0]))
	assert_near(float(two[1]), float(two[0]) * 0.5, 2.0, "a hod carrier pays 5 lumber per 10 s (%d)" % int(two[1]))
	assert_near(float(three[1]), float(three[0]) * 1.0, 3.0, "two carriers pay twice that (%d)" % int(three[1]))
	assert_eq(int(one[1]), 0, "a lone builder pays nothing extra")


func test_clans_build_with_one_yurtwright() -> void:
	var w := _world("clans")
	var a := w.spawn_unit("clans_yurtwright", 0, Vector3(30, 0, 30))
	var b := w.spawn_unit("clans_yurtwright", 0, Vector3(31, 0, 30))
	_build(w, a, "clans_home_yurt", Vector3(36, 0, 30))
	var site: Unit = null
	for i in 30 * 6:
		w.step()
		site = _site_of(w, "clans_home_yurt")
		if site != null:
			break
	w.issue({"type": "smart", "player": 0, "units": [b.id], "target": site.id})
	var t0 := w.time
	while site.under_construction and w.time - t0 < 80.0:
		w.step()
	assert_near(w.time - t0, 45.0, 0.6, "a second Yurtwright adds nothing (45 s)")


func test_cancel_refunds_and_abandoned_sites_wait() -> void:
	var w := _world()
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 30))
	_build(w, hod, "kingdom_drill_yard", Vector3(40, 0, 30))
	var site: Unit = null
	for i in 30 * 8:
		w.step()
		site = _site_of(w, "kingdom_drill_yard")
		if site != null:
			break
	assert_true(site != null, "the Drill Yard site started")
	w.issue({"type": "stop", "player": 0, "units": [hod.id]})
	for i in 30 * 5:
		w.step()
	var p0 := site.build_progress
	for i in 30 * 5:
		w.step()
	assert_eq(site.build_progress, p0, "an abandoned site waits")
	var other := w.spawn_unit("kingdom_hodman", 0, Vector3(34, 0, 34))
	w.issue({"type": "smart", "player": 0, "units": [other.id], "target": site.id})
	for i in 30 * 6:
		w.step()
	assert_true(site.build_progress > p0, "another Hodman picks it up")
	var g0 := w.player(0).gold
	var l0 := w.player(0).lumber
	w.issue({"type": "cancel", "player": 0, "units": [site.id]})
	w.step()
	assert_false(site.alive, "cancelled")
	assert_eq(w.player(0).gold - g0, floori(160 * 0.75), "75 % of the gold back")
	assert_eq(w.player(0).lumber - l0, floori(55 * 0.75), "75 % of the lumber back")
	assert_true(w.pathing.is_rect_free(site.footprint), "the footprint is open again")
	w.step()
	assert_true(other.current == null, "its builder goes idle")


func test_repair_rate_and_cost() -> void:
	var w := _world()
	var croft := w.spawn_unit("kingdom_croft", 0, Vector3(40, 0, 30))
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(36, 0, 30))
	croft.hp = croft.max_hp * 0.5
	var g0 := w.player(0).gold
	var l0 := w.player(0).lumber
	w.issue({"type": "repair", "player": 0, "units": [hod.id], "target": croft.id})
	var t_start := -1.0
	for i in 30 * 60:
		w.step()
		if t_start < 0.0 and croft.hp > croft.max_hp * 0.5 + 0.01:
			t_start = w.time
		if croft.hp >= croft.max_hp:
			break
	assert_near(croft.hp, croft.max_hp, 0.01, "repaired to full")
	assert_near(w.time - t_start, 38.0 * 1.5 * 0.5, 1.0, "half the HP in half of 1.5 × the build time")
	assert_near(g0 - w.player(0).gold, 95 * 0.3 * 0.5, 1.01, "30 % of the gold, pro rata")
	assert_near(l0 - w.player(0).lumber, 20 * 0.3 * 0.5, 1.01, "30 % of the lumber, pro rata")
	w.step()
	assert_true(hod.current == null, "done")
	croft.hp = croft.max_hp * 0.5
	w.player(0).gold = 0
	w.issue({"type": "repair", "player": 0, "units": [hod.id], "target": croft.id})
	for i in 30 * 5:
		w.step()
	# the fractional accumulator lets less than one whole gold of repair through before it pauses
	var credit := croft.max_hp / (95.0 * 0.3)
	assert_true(croft.hp <= croft.max_hp * 0.5 + credit + 0.5, "no gold: the repair waits (%.1f HP)" % croft.hp)
	assert_true(hod.current != null and hod.current.type == Order.Type.REPAIR, "the worker waits on site")


## A selected site that is cancelled (World.remove_unit) drops out of the selection and the
## control groups at once (Events.unit_removed), before it is freed.
func test_cancelled_site_leaves_the_selection() -> void:
	var w := _world()
	var sel := Selection.new()
	track(sel)
	tree.root.add_child(sel)
	sel.setup(w, null, 0)
	var site := w.construction.start_site(0, "kingdom_croft", Vector3(40, 0, 30))
	sel.select_units([site])
	sel.groups[1] = [site]
	w.issue({"type": "cancel", "player": 0, "units": [site.id]})
	w.step()
	assert_true(sel.selected.is_empty(), "the cancelled site left the selection")
	assert_true((sel.groups[1] as Array).is_empty(), "and its control group")
