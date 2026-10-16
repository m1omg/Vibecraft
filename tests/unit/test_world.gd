extends "res://tests/test_case.gd"
## World-level contracts: system stages, the player relation table, pause-safe visual
## interpolation and cached per-unit values read every tick.


class Recorder extends Node:
	var entries: Array = []
	var tag: String = ""

	func sim_tick(_w: World, _dt: float) -> void:
		entries.append(tag)


func after_each() -> void:
	tree.paused = false
	cleanup()


func _recorder(entries: Array, tag: String) -> Recorder:
	var r := Recorder.new()
	r.entries = entries
	r.tag = tag
	track(r)
	return r


## Several systems may share a stage (run in registration order) without evicting each other;
## the stages World runs itself are not registration points.
func test_systems_share_stages_in_registration_order() -> void:
	var w := make_world()
	var entries: Array = []
	assert_true(w.register_system(&"ai", _recorder(entries, "ai_a")), "ai accepts a system")
	assert_true(w.register_system(&"ai", _recorder(entries, "ai_b")), "and a second one")
	assert_true(w.register_system(&"projectiles", _recorder(entries, "proj")), "projectiles too")
	assert_true(w.register_system(&"production", _recorder(entries, "prod")), "production too")
	w.step()
	assert_eq(entries, ["prod", "proj", "ai_a", "ai_b"], "stage order, then registration order")
	var proj := w.systems_in(&"projectiles")
	assert_eq(proj.size(), 2, "two projectile-stage systems")
	assert_eq(proj[0], w.combat, "Combat was not evicted and still runs first")
	for stage: StringName in [&"orders", &"units", &"cleanup", &"no_such_stage"]:
		assert_false(World.is_system_stage(stage), "%s is not a registration point" % stage)
	for stage: StringName in World.LATE_STAGES:
		assert_true(World.is_system_stage(stage), "%s accepts systems" % stage)


func test_enemy_table_matches_rules() -> void:
	var w := make_world()
	w.add_player(2, 0)                      # ally of player 0
	assert_true(w.is_enemy(0, 1), "other team")
	assert_false(w.is_enemy(0, 2), "same team")
	assert_false(w.is_enemy(0, 0), "self")
	assert_true(w.is_enemy(0, PlayerState.NEUTRAL_HOSTILE), "creeps attack everyone")
	assert_false(w.is_enemy(PlayerState.NEUTRAL_HOSTILE, PlayerState.NEUTRAL_HOSTILE), "creeps are one side")
	assert_false(w.is_enemy(1, PlayerState.NEUTRAL_PASSIVE), "passive is nobody's enemy")
	var mismatches := 0
	for a in World.MAX_PLAYERS:
		for b in World.MAX_PLAYERS:
			if w.is_enemy(a, b) != w._enemy_rule(a, b):
				mismatches += 1
			if ((w.hostile_mask(a) >> b) & 1 == 1) != w.is_enemy(a, b):
				mismatches += 1
	assert_eq(mismatches, 0, "table, masks and rules agree")


## Visuals read display_pos() every render frame. While paused no ticks run, so it must show
## the last tick's state instead of oscillating with the engine's interpolation fraction.
func test_display_pos_frozen_while_paused() -> void:
	var w := make_world()
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	w.issue({"type": "move", "player": 0, "units": [u.id], "pos": Vector3(40, 0, 10)})
	for i in 6:
		w.step()
	assert_true(u.prev_pos != u.pos, "moving")
	tree.paused = true
	var worst := 0.0
	for i in 4:
		await tree.process_frame
		worst = maxf(worst, u.display_pos().distance_to(u.pos))
	assert_near(w.interpolation_fraction(), 1.0, 1e-6, "fraction frozen at 1 while paused")
	tree.paused = false
	assert_lt(worst, 1e-6, "display position held at the last tick (worst offset %f)" % worst)


## Values read every tick or frame (corpse decay) are computed once.
func test_decay_ticks_cached() -> void:
	var w := make_world()
	var s := w.spawn_unit("dummy_soldier", 0, Vector3(10, 0, 10))
	var hall := w.spawn_unit("dummy_hall", 1, Vector3(30, 0, 30))
	var corpse := roundi(float(Defs.combat_default("corpse_decay", 8.0)) * World.TICK_RATE)
	var ruin := roundi(float(Defs.combat_default("structure_decay", 4.0)) * World.TICK_RATE)
	assert_eq(s.decay_ticks(), corpse, "unit corpse decay from combat defaults")
	assert_eq(hall.decay_ticks(), ruin, "structure decay from combat defaults")
	assert_eq(s._decay_ticks, corpse, "cached")
	assert_near(hall.target_radius, Vector2(10, 10).length() * Grid.CELL * 0.5, 1e-4,
		"structure target radius is the footprint half-diagonal")
	assert_true(Defs.max_target_radius >= hall.target_radius, "Defs pads queries by the largest one")
