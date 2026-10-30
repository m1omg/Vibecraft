extends "res://tests/test_case.gd"
## Hero juice (src/fx/hero_fx.gd, hero_sigils.gd, xp_motes.gd; juice HER-01, HER-03, HER-04,
## HER-06, HER-07) in a visual world on a manual fx clock: a sigil under every hero showing its
## level, the new segment lighting 250 ms into a level-up; XP motes that land before the
## level-up they cause; the emblem's slam at 820 ms with its sounds; the fallen hero's sigil
## fading out; the revive beat. Visual and audio only.

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
	w.add_player(0, 0, "kingdom")
	w.local_player_id = 0
	w.add_player(1, 1, "clans")
	return w


func _frame(fx: HeroFx, dt: float = World.DT) -> void:
	FxClock.advance(dt, true)
	fx._process(dt)
	fx.sigils._process(dt)
	fx.motes._process(dt)


func _run(fx: HeroFx, seconds: float) -> void:
	var t := 0.0
	while t < seconds:
		_frame(fx)
		t += World.DT


func test_sigils_show_the_level_and_light_the_new_segment_late() -> void:
	var w := _visual_world()
	var fx := (w.get_node("Fx/Vfx") as Vfx).heroes
	var marshal := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var uncut := w.spawn_unit("clans_hero_uncut", 1, Vector3(30, 0, 20))
	_frame(fx)
	assert_eq(fx.sigils.items.size(), 2, "a sigil under each hero")
	var it: HeroSigils.Item = fx.sigils.items[marshal.id]
	assert_eq((it.node.get_instance_shader_parameter("sig_a") as Vector4).x, 1.0, "level 1 lights one segment")
	assert_eq((fx.sigils.items[uncut.id].node.get_instance_shader_parameter("sig_a") as Vector4).y, 1.0, "the Tormai gong face")
	w.heroes.add_xp(marshal, 200.0)
	_frame(fx)
	assert_eq((it.node.get_instance_shader_parameter("sig_a") as Vector4).x, 1.0, "the new segment waits for the ceremony")
	_run(fx, 0.3)
	assert_eq((it.node.get_instance_shader_parameter("sig_a") as Vector4).x, 2.0, "and lights at 250 ms")


func test_xp_motes_land_before_the_level_up_and_the_slam() -> void:
	var w := _visual_world()
	var fx := (w.get_node("Fx/Vfx") as Vfx).heroes
	var marshal := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var landed: Array = []
	fx.motes.arrived.connect(func(h: Unit) -> void: landed.append(FxClock.fx_now))
	w.heroes.add_xp(marshal, 150.0)
	var creep := w.spawn_unit("creep_sootcoat_kiln_master", PlayerState.NEUTRAL_HOSTILE, Vector3(23, 0, 20))
	creep.take_damage(999999.0, marshal)
	w.step()
	var t0 := FxClock.fx_now
	_frame(fx)
	assert_eq(int(fx.counts.get("xp", 0)), 1, "the kill sends XP motes")
	assert_eq(fx.motes.motes.size(), 6, "115 x 0.8 = 92 XP: six motes")
	_run(fx, 0.5)
	assert_eq(landed.size(), 1, "they land")
	assert_lt(float(landed[0]) - t0, 0.25, "straight in when they cross a level, before the 250 ms beat")
	assert_eq(int(fx.counts.get("level", 0)), 1, "the level-up ceremony")
	assert_eq(int(fx.counts.get("slam", 0)), 0, "no slam yet")
	_run(fx, 0.5)
	assert_eq(int(fx.counts.get("slam", 0)), 1, "the emblem slams at 820 ms")
	assert_true(Audio.has_family("hero_level_kingdom") and Audio.has_family("hero_bell_kingdom_l2"),
		"with the level cue and the ladder bell")
	_run(fx, 0.5)
	assert_eq(fx._emblems.size(), 0, "the emblem is gone by 1150 ms")


func test_fallen_sigil_fades_and_the_revive_beat() -> void:
	var w := _visual_world()
	var fx := (w.get_node("Fx/Vfx") as Vfx).heroes
	var altar := w.spawn_unit("kingdom_oath_hall", 0, Vector3(34, 0, 34))
	w.spawn_unit("kingdom_moot_hall", 0, Vector3(10, 0, 36))
	var marshal := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	_frame(fx)
	var hid := marshal.id
	marshal.take_damage(999999.0, null)
	w.step()
	_frame(fx)
	assert_eq(int(fx.counts.get("died", 0)), 1, "the hero-down beat")
	assert_true(fx.sigils.items.has(hid), "the sigil fades out")
	_run(fx, 0.5)
	assert_false(fx.sigils.items.has(hid), "and is gone after 0.4 s")
	assert_true(Audio.has_family("hero_down") and Audio.has_family("hero_revive"), "both stings exist")
	w.player(0).gold = 1000
	w.issue({"type": "revive", "player": 0, "units": [altar.id], "hero": hid})
	while w.heroes.dead_record(hid).size() > 0 and w.time < 60.0:
		w.step()
	_frame(fx)
	assert_eq(int(fx.counts.get("revived", 0)), 1, "the revive beat")
	_frame(fx)
	assert_eq(fx.sigils.items.size(), 1, "the revived hero has its sigil")
