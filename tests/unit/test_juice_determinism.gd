extends "res://tests/test_case.gd"
## Juice never changes sim outcomes (juice bible rule 3, §5.2): the same scripted fight run
## headless and with the whole juice runtime (views, body composers, Vfx router, impacts,
## missiles, marks, rings, bars, popups, audio events, selection and order feedback) at uneven
## frame pacing gives identical hits, kills, positions and World.rng state. Juice reads sim
## state only and never draws from World.rng.

var _hits: Array = []
var _deaths: Array = []


func _record_hit(u: Node, amount: float, src: Node) -> void:
	_hits.append([u.get("world").tick_count, u.get("id"), amount, src.get("id") if src != null else 0])


func _record_death(u: Node, killer: Node) -> void:
	_deaths.append([u.get("world").tick_count, u.get("id"), killer.get("id") if killer != null else 0])


func _visual_world() -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(flat_map(), 7)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


func _fight(visual: bool, frames: Array) -> Dictionary:
	_hits.clear()
	_deaths.clear()
	var w := _visual_world() if visual else make_world(null, false)
	if not visual:
		w.rng.seed = 7
	var army: Array = []
	for i in 4:
		army.append(w.spawn_unit("dummy_soldier", 0, Vector3(14, 0, 16 + i * 1.2)))
	for i in 2:
		army.append(w.spawn_unit("dummy_archer", 0, Vector3(12, 0, 17 + i * 1.4)))
	for i in 5:
		w.spawn_unit("dummy_soldier", 1, Vector3(21, 0, 16 + i * 1.1))
	var ids: Array = []
	for u: Unit in army:
		ids.append(u.id)
	if visual:
		Events.selection_changed.emit(army)       # rings pop in, the What line plays
	w.issue({"type": "move", "player": 0, "units": ids, "pos": Vector3(16, 0, 18)})
	for i in 600:
		if i == 20:
			w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": Vector3(26, 0, 18), "queue": false})
		if i == 25:
			w.issue({"type": "move", "player": 0, "units": ids.slice(0, 2), "pos": Vector3(30, 0, 22), "queue": true})
		w.step()
		if visual:
			for f in int(frames[i % frames.size()]):
				await tree.process_frame
	var state: Array = []
	for u: Unit in w.unit_list:
		state.append([u.id, u.alive, snappedf(u.hp, 0.001), u.pos.snapped(Vector3.ONE * 0.0001), snappedf(u.facing, 0.0001)])
	var out := {"hits": _hits.duplicate(true), "deaths": _deaths.duplicate(true), "state": state,
		"rng": w.rng.state, "ticks": w.tick_count}
	if visual:
		Events.selection_changed.emit([])
	return out


func test_juice_does_not_change_sim_outcomes() -> void:
	Events.unit_damaged.connect(_record_hit)
	Events.unit_died.connect(_record_death)
	var headless: Dictionary = await _fight(false, [])
	var juiced: Dictionary = await _fight(true, [0, 2, 1, 3, 1])
	Events.unit_damaged.disconnect(_record_hit)
	Events.unit_died.disconnect(_record_death)
	assert_true((headless["hits"] as Array).size() > 10, "a fight happened (%d hits)" % (headless["hits"] as Array).size())
	assert_true((headless["deaths"] as Array).size() > 0, "someone fell")
	assert_eq(juiced["hits"], headless["hits"], "identical hits with the juice running")
	assert_eq(juiced["deaths"], headless["deaths"], "identical deaths")
	assert_eq(juiced["state"], headless["state"], "identical positions, facings and hp")
	assert_eq(juiced["rng"], headless["rng"], "juice never draws from World.rng")


func test_juice_ran_during_the_fight() -> void:
	# the juiced run really exercised the runtime (not a vacuous pass)
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var a := w.spawn_unit("dummy_soldier", 0, Vector3(14, 0, 16))
	var b := w.spawn_unit("dummy_soldier", 1, Vector3(15.2, 0, 16))
	var drained := vfx.drained
	for i in 90:
		w.step()
		await tree.process_frame
	assert_true(vfx.drained > drained, "the Vfx queue drained combat records (%d)" % (vfx.drained - drained))
	assert_true(not a.alive or not b.alive or a.hp < a.max_hp or b.hp < b.max_hp, "they fought")
	assert_eq(vfx.dropped_records, 0, "no record dropped from the 512-record queue")
