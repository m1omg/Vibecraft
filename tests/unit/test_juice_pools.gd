extends "res://tests/test_case.gd"
## Pool limits and policies of the juice runtime (juice bible §4.1, §4.5, §4.6, CMB-08, CMB-28):
## the particle pool never pops a young emitter and keeps the per-frame spawn budget, ground
## marks, popups, order markers and stuck missiles stay inside their pools, the Audio director's
## voice pool steals by priority, keeps family caps and spacing, culls by distance, debounces
## acks and stays silent when a sound is missing, and combat text prints no per-hit numbers.

var _was_manual := false


func before_each() -> void:
	_was_manual = FxClock.manual
	FxClock.manual = true
	FxClock.reset(10.0)


func after_each() -> void:
	cleanup()
	FxClock.manual = _was_manual
	Audio.clock_override = -1.0
	Audio.listener_focus = Vector3.INF
	Audio.reset_state()
	CombatText.mode = CombatText.Mode.MINIMAL


func _visual_world() -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(flat_map(), 1)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


# --- particles --------------------------------------------------------------------------------

func test_particle_pool_rejects_young_emitters_and_evicts_for_importance() -> void:
	var pool := ParticlePool.new()
	tree.root.add_child(pool)
	track(pool)
	pool.setup(1)    # CPUParticles3D: the Compatibility fallback
	assert_true(pool.has_kind("star") and pool.has_kind("spark"), "kinds from data/fx_particles.json")
	assert_true(pool.get_child(0) is CPUParticles3D, "the CPU fallback builds CPUParticles3D")
	var n := pool.pool_size("star")
	for i in n:
		assert_true(pool.burst("star", Vector3(i, 0, 0), Vector3.UP, 1.0, 2), "burst %d fits" % i)
	assert_false(pool.burst("star", Vector3.ZERO, Vector3.UP, 1.0, 2), "a young emitter is never popped")
	assert_eq(int(pool.stats["rejected"]), 1, "the rejection is counted")
	assert_true(pool.burst("star", Vector3.ZERO, Vector3.UP, 1.0, 3), "importance 3 evicts the oldest")
	assert_eq(int(pool.stats["evicted"]), 1, "the eviction is counted")
	var life := float((pool.kinds["star"]["life"] as Array)[1])
	FxClock.advance(life * 0.6)
	assert_true(pool.burst("star", Vector3.ZERO, Vector3.UP, 1.0, 1) or int(pool.stats["over_budget"]) > 0,
		"past 50 % of its life an emitter may be reused")
	assert_true(pool.active_count("star") <= n, "never more live emitters than the pool")


func test_particle_pool_keeps_the_per_frame_spawn_budget() -> void:
	var pool := ParticlePool.new()
	tree.root.add_child(pool)
	track(pool)
	pool.setup(1)
	await tree.process_frame
	var budget := FeelConstants.c().spawn_budget_per_frame
	var per := int(pool.kinds["dust_step"]["amount"])
	var ok := 0
	for i in 40:
		if pool.burst("dust_step", Vector3(i, 0, 0), Vector3.UP, 1.0, 0):
			ok += 1
	assert_true(ok * per <= budget, "optional bursts stop at the budget (%d particles)" % (ok * per))
	assert_true(int(pool.stats["over_budget"]) > 0, "over-budget bursts are dropped and counted")
	assert_true(pool.burst("star", Vector3.ZERO, Vector3.UP, 1.0, 2), "important bursts bypass the budget")


func test_gpu_particles_on_forward_plus() -> void:
	var pool := ParticlePool.new()
	tree.root.add_child(pool)
	track(pool)
	pool.setup(0)
	assert_true(pool.get_child(0) is GPUParticles3D, "Forward+ builds GPUParticles3D")
	var g := pool.get_child(0) as GPUParticles3D
	assert_eq(g.fixed_fps, ParticlePool.FIXED_FPS, "fixed simulation rate: refresh-rate independent")
	assert_true(g.interpolate and g.one_shot, "interpolated one-shot emitters")
	assert_eq(g.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "fx cast no shadows")


# --- marks, popups, markers, missiles -----------------------------------------------------------

func test_ground_marks_cap_and_swap_remove() -> void:
	var marks := GroundMarks.new()
	tree.root.add_child(marks)
	track(marks)
	for i in GroundMarks.CAP + 10:
		marks.add(GroundMarks.Kind.DUST_RING, Vector3(i * 0.1, 0, 0), 0.2, 0.8, Color.WHITE, 0.5)
	assert_eq(marks.live, GroundMarks.CAP, "the mark pool is capped")
	assert_eq(marks.dropped, 10, "the oldest marks yield and are counted")


func test_popup_text_pool_and_merge() -> void:
	var pop := PopupText.new()
	tree.root.add_child(pop)
	track(pop)
	var cap := pop.capacity()
	for i in cap + 20:
		pop.show_value(PopupText.Style.GOLD, 1, Vector3(i, 0, 0))
	assert_eq(pop.live_count(), cap, "never more popups than the pool")
	var a := pop.show_value(PopupText.Style.CRIT, 30, Vector3.ZERO, null, 77, 0.25)
	FxClock.advance(0.1)
	var b := pop.show_value(PopupText.Style.CRIT, 12, Vector3.ZERO, null, 77, 0.25)
	assert_true(a == b, "the same key inside 250 ms merges into one popup")
	assert_eq(b.value, 42, "merged values add")
	for i in 8:
		FxClock.advance(0.2)     # one advance never jumps more than FxClock.MAX_DT
	var c := pop.show_value(PopupText.Style.CRIT, 5, Vector3.ZERO, null, 77, 0.25)
	assert_eq(c.value, 5, "after its life a new popup starts")


func test_order_markers_pool_taps_and_nod_rate() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var u := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var u2 := w.spawn_unit("dummy_soldier", 0, Vector3(21, 0, 20))
	vfx.selected = [u, u2]
	# 8 clicks per second for 3 s, each on a fresh spot
	for i in 24:
		vfx.orders.on_command({"type": "smart", "player": 0, "units": [u.id, u2.id],
			"pos": Vector3(10 + (i % 6) * 3.0, 0, 30 + (i / 6) * 3.0)})
		assert_true(vfx.orders.live_markers() <= FeelConstants.c().marker_pool, "≤ 8 live markers")
		FxClock.advance(0.125)
	assert_true(vfx.orders.nods <= 2 * 7, "≤ 7 nods per unit in 3 s (%d)" % vfx.orders.nods)
	# a re-click within 250 ms and 1.5 m is a tap
	var taps := vfx.orders.taps
	vfx.orders.on_command({"type": "move", "player": 0, "units": [u.id], "pos": Vector3(40, 0, 40)})
	FxClock.advance(0.1)
	vfx.orders.on_command({"type": "move", "player": 0, "units": [u.id], "pos": Vector3(40.5, 0, 40)})
	assert_eq(vfx.orders.taps, taps + 1, "the spam click becomes a tap")
	assert_true(vfx.orders.live_pins() <= OrderMarkers.PIN_CAP, "pins stay in their ring")


func test_order_ripple_ranks_and_target_flash() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var near := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var far := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 26))
	var enemy := w.spawn_unit("dummy_soldier", 1, Vector3(20, 0, 12))
	var t := FxClock.ui_now
	vfx.orders.on_command({"type": "move", "player": 0, "units": [far.id, near.id], "pos": Vector3(20, 0, 14)})
	assert_near(vfx.circles.pulse_start(near), t, 1e-6, "rank 0 (nearest the click) pulses on the input frame")
	assert_near(vfx.circles.pulse_start(far), t + FeelConstants.c().ripple_step_ms / 1000.0, 1e-6,
		"rank 1 follows 28 ms later")
	var before := vfx.marks.count_kind(GroundMarks.Kind.TARGET_BLINK)
	vfx.orders.on_command({"type": "smart", "player": 0, "units": [near.id], "target": enemy.id})
	assert_eq(vfx.marks.count_kind(GroundMarks.Kind.TARGET_BLINK), before + 1, "the target blinks")


func test_stuck_missiles_stay_in_their_ring() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	for i in FeelConstants.c().stuck_cap + 20:
		vfx.missiles._stick_in_ground(Vector3(5 + i * 0.2, 0, 5), Vector3(0.3, -1, 0).normalized(), "javelin")
	assert_eq(vfx.missiles.stuck_live(), FeelConstants.c().stuck_cap, "the stuck ring holds stuck_cap")


# --- combat text policy ---------------------------------------------------------------------------

func test_minimal_text_prints_no_per_hit_numbers() -> void:
	var w := _visual_world()
	var vfx := w.get_node("Fx/Vfx") as Vfx
	var a := w.spawn_unit("dummy_soldier", 0, Vector3(20, 0, 20))
	var b := w.spawn_unit("dummy_soldier", 1, Vector3(21, 0, 20))
	var spawned := vfx.popups.spawned
	for i in 10:
		vfx.text.on_damage(b, float(a.damage_min), a)
	assert_eq(vfx.popups.spawned, spawned, "Minimal: ordinary hits print nothing")
	vfx.text.on_bounty(0, 25, b.pos)
	assert_eq(vfx.popups.spawned, spawned + 1, "a bounty for the local player prints +N")
	vfx.text.on_bounty(1, 25, b.pos)
	assert_eq(vfx.popups.spawned, spawned + 1, "an opponent's bounty is never shown")


func test_no_label3d_anywhere() -> void:
	# PopupText is the only world-text system (bible R2): no Label3D in the sources
	var found: Array[String] = []
	_scan("res://src", found)
	assert_eq(found, [] as Array[String], "Label3D used in")


func _scan(dir: String, found: Array[String]) -> void:
	for f in DirAccess.get_files_at(dir):
		if f.ends_with(".gd"):
			var text := FileAccess.get_file_as_string(dir + "/" + f)
			if text.contains("Label3D.new(") or text.contains("Label3D\""):
				found.append(dir + "/" + f)
	for d in DirAccess.get_directories_at(dir):
		_scan(dir + "/" + d, found)


# --- audio ----------------------------------------------------------------------------------------

func test_audio_is_silent_when_assets_are_missing() -> void:
	Audio.reset_state()
	Audio.clock_override = 100.0
	assert_false(Audio.play_3d("no_such_family", Vector3.ZERO), "a missing family is a no-op")
	assert_eq(Audio.event("no_such_event", Vector3.ZERO), 0, "a missing event plays nothing")
	assert_eq(Audio.event("unit_death", Vector3.ZERO, {"faction": ""}), 0, "an unfillable template plays nothing")
	assert_true(int(Audio.stats["missing"]) >= 2, "missing requests are counted, never errors")


func test_audio_family_caps_spacing_and_cull() -> void:
	Audio.reset_state()
	Audio.clock_override = 200.0
	assert_true(Audio.play_3d("hit_flesh_l", Vector3.ZERO), "first hit plays")
	Audio.clock_override = 200.01
	assert_false(Audio.play_3d("hit_flesh_l", Vector3.ZERO), "a repeat inside the spacing is dropped")
	var cap := int(Audio.family_meta("hit_flesh_l")["cap"])
	for i in cap + 2:
		Audio.clock_override = 200.1 + i * 0.07
		Audio.play_3d("hit_flesh_l", Vector3.ZERO)
	assert_eq(Audio.playing_count("hit_flesh_l"), cap, "the family cap holds")
	assert_true(int(Audio.stats["capped"]) > 0, "capped requests are counted")
	Audio.listener_focus = Vector3.ZERO
	Audio.listener_distance = 28.0
	Audio.clock_override = 210.0
	assert_false(Audio.play_3d("fall_huge", Vector3(200, 0, 0)), "far sounds are culled")
	assert_true(Audio.play_3d("fall_huge", Vector3(5, 0, 0)), "near sounds play")


func test_audio_voice_pool_steals_by_priority() -> void:
	Audio.reset_state()
	Audio.clock_override = 300.0
	var pool := FeelConstants.c().one_shot_pool
	for i in pool:
		assert_true(Audio.play_3d("fall_huge", Vector3.ZERO, {"priority": 30, "cap": 99, "spacing_ms": 0}), "voice %d" % i)
	assert_false(Audio.play_3d("fall_armoured", Vector3.ZERO, {"priority": 20}), "a lower priority is rejected")
	assert_true(Audio.play_3d("fall_armoured", Vector3.ZERO, {"priority": 60}), "a higher priority steals")
	assert_eq(int(Audio.stats["stolen"]), 1, "the steal is counted")
	Audio.reset_state()
	Audio.clock_override = 400.0
	for i in pool:
		Audio.play_3d("fall_huge", Vector3.ZERO, {"priority": 80, "cap": 99, "spacing_ms": 0, "no_cut_ms": 500})
	assert_false(Audio.play_3d("fall_armoured", Vector3.ZERO, {"priority": 90}), "no-cut voices are never stolen")


func test_audio_layered_events_and_pitch() -> void:
	Audio.reset_state()
	Audio.clock_override = 500.0
	assert_true(Audio.has_event("melee_hit"), "data/sfx_events.json is loaded")
	var n := Audio.event("melee_hit", Vector3.ZERO, {"material": "stone", "weight": "l", "mass": 1.0, "seed": 3})
	assert_eq(n, 1, "an unknown material falls back to a recorded family")
	Audio.clock_override = 501.0
	var m := Audio.event("melee_hit", Vector3.ZERO, {"material": "wood", "weight": "h", "mass": 1.8,
		"clash": true, "seed": 4})
	assert_eq(m, 3, "a clash layers the impact with the metal and wood clash layers")
	var p := {"base": 1.08, "per_mass": -0.06, "clamp": [0.85, 1.08], "jitter": 0.05}
	var p1 := Audio.layer_pitch(p, {"mass": 2.0}, 9, 0)
	assert_near(p1, Audio.layer_pitch(p, {"mass": 2.0}, 9, 0), 1e-9, "pitch jitter is a stateless hash")
	assert_true(p1 < 1.08 * 1.05 and p1 > 1.02 * 0.95, "heavier sounds lower (%f)" % p1)
	assert_true(Audio.cond("mass>=2.5", {"mass": 3.0}) and not Audio.cond("!kill", {"kill": true}), "conditions")


func test_audio_ack_debounce_and_order_ticks() -> void:
	Audio.reset_state()
	var w := make_world()
	var u := w.spawn_unit("kingdom_hodman", 0, Vector3(10, 0, 10))
	var lengths: Array = []
	var cb := func(_unit: Node, _cat: String, length: float) -> void:
		lengths.append(length)
	Audio.voice_started.connect(cb)
	Audio.clock_override = 600.0
	assert_true(Audio.play_voice(u, "what"), "the What line plays on the input frame")
	Audio.clock_override = 600.2
	assert_false(Audio.play_voice(u, "what"), "What is debounced inside 400 ms")
	Audio.clock_override = 610.0
	assert_true(Audio.play_voice(u, "yes"), "Yes plays")
	Audio.clock_override = 610.3
	assert_false(Audio.play_voice(u, "yes"), "Yes is debounced inside 1000 ms (an order tick answers)")
	Audio.voice_started.disconnect(cb)
	assert_eq(lengths.size(), 2, "voice_started fires for each line that starts")
	assert_true(float(lengths[0]) > 0.0, "with the line's length")
	assert_true(int(Audio.stats["debounced"]) >= 2, "debounced requests are counted")
