extends "res://tests/test_case.gd"
## Visual integration (src/render/, UnitView, TerrainBuilder, Doodads, DayNight): model
## resolution, the unit manifest, clip mapping (stride matching, hit frame on the damage point,
## death hold), instance uniforms, footprint scaling, terrain tile data, tree LOD promotion,
## time-of-day keys, camera profile, and that views never change sim outcomes.

const TEST_DEFS := {
	"test_glb_infantry": {"name": "T Infantry", "kind": "unit", "model": "units/kingdom_infantry",
		"hp": 400, "radius": 0.45, "speed": 4.0, "height": 1.75, "armor_type": "heavy",
		"attack": {"type": "blade", "damage": [11, 14], "cooldown": 1.35, "range": 0.8,
			"damage_point": 0.45, "backswing": 0.45, "acquire": 8.0}},
	"test_glb_croft": {"name": "T Croft", "kind": "building", "model": "buildings/kingdom_croft",
		"hp": 500, "radius": 2.0, "footprint": [8, 8], "height": 3.5, "armor_type": "fortified"},
	"clans_hero_skymirror": {"name": "T Skymirror", "kind": "unit", "hp": 500, "radius": 0.5,
		"speed": 4.7, "height": 2.15, "flags": ["hero"], "armor_type": "hero"},
}
var _added: Array[String] = []
var _hits: Array = []


func before_each() -> void:
	for id: String in TEST_DEFS:
		if not Defs.units.has(id):
			Defs.units[id] = (TEST_DEFS[id] as Dictionary).duplicate(true)
			_added.append(id)
	Defs._prepare_units()


func after_each() -> void:
	cleanup()
	for id in _added:
		Defs.units.erase(id)
	_added.clear()
	Defs._prepare_units()


func _visual_world(m: MapData = null, seed_value: int = 1) -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(m if m != null else flat_map(), seed_value)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


# --- asset resolution and manifest ---------------------------------------------------------

func test_model_path_resolution() -> void:
	assert_eq(AssetLibrary.model_path({"model": "units/kingdom_infantry"}, "x"),
		"res://assets/models/units/kingdom_infantry.glb", "explicit model key")
	assert_eq(AssetLibrary.model_path({}, "kingdom_pavisier"),
		"res://assets/models/units/kingdom_infantry.glb", "manifest alias")
	assert_eq(AssetLibrary.model_path({}, "kingdom_moot_hall"),
		"res://assets/models/buildings/kingdom_moot_hall.glb", "fallback by def id in buildings/")
	assert_eq(AssetLibrary.model_path({}, "gold_mine"),
		"res://assets/models/neutral/gold_mine.glb", "fallback by def id in neutral/")
	assert_eq(AssetLibrary.model_path({}, "dummy_soldier"), "", "no asset -> placeholder")
	assert_eq(AssetLibrary.model_path({"model": "units/does_not_exist"}, "dummy_worker"), "",
		"missing model and no fallback -> placeholder")


func test_unit_manifest_covers_every_rigged_unit() -> void:
	var units: Dictionary = AssetLibrary.unit_manifest().get("units", {})
	var n := 0
	for f in DirAccess.get_files_at("res://assets/models/units/"):
		if not f.ends_with(".glb"):
			continue
		n += 1
		var id := f.get_basename()
		assert_true(units.has(id), "manifest entry for %s" % id)
		if not units.has(id):
			continue
		var e: Dictionary = units[id]
		var clips: Dictionary = e["clips"]
		assert_true(float(e.get("walk_anim_speed", 0.0)) > 0.2, "%s stride speed" % id)
		assert_true(clips.has("idle") and clips.has("walk") and clips.has("death"), "%s core clips" % id)
		var info := AssetLibrary.model_info("res://assets/models/units/" + f)
		for c: String in clips:
			assert_true((info["clips"] as Array).has(c), "%s clip %s exists in the GLB" % [id, c])
		for c: String in ["attack", "cast", "work"]:
			if clips.has(c):
				var hit := float(e[c + "_hit_s"])
				assert_true(float(e[c + "_start_s"]) <= hit and hit <= float(e[c + "_end_s"]),
					"%s %s start <= hit <= end" % [id, c])
				assert_true(hit > 0.0 and hit < float(clips[c]), "%s %s hit inside the clip" % [id, c])
	assert_true(n >= 12, "slice units present (%d)" % n)


## The builder's own toe-bone measurement agrees with autorig's stance speed (within 10 %).
func test_manifest_builder_measures_stride() -> void:
	var builder: GDScript = load("res://src/render/unit_manifest_builder.gd")
	var m: Dictionary = builder.call("measure", "res://assets/models/units/kingdom_infantry.glb")
	var e := AssetLibrary.unit_entry("res://assets/models/units/kingdom_infantry.glb")
	assert_near(float(m["walk_anim_speed"]), float(e["walk_anim_speed"]), float(e["walk_anim_speed"]) * 0.1,
		"measured stride")
	assert_near(float(m["attack_hit_s"]), float(e["attack_hit_s"]), 0.05, "measured hit frame")


# --- UnitView with rigged GLBs -------------------------------------------------------------

func test_unit_view_loads_glb_and_maps_clips() -> void:
	var w := _visual_world()
	var u := w.spawn_unit("test_glb_infantry", 0, Vector3(20, 0, 20))
	var v := u.view as UnitView
	assert_true(v.model != null, "GLB model instanced")
	assert_true(v.animation_player() != null, "has an AnimationPlayer")
	for s in ["idle", "walk", "attack", "death"]:
		assert_true(v.available_states().has(s), "clip state %s" % s)
	var ap := v.animation_player()
	assert_eq(ap.get_animation("idle").loop_mode, Animation.LOOP_LINEAR, "idle loops")
	assert_eq(ap.get_animation("walk").loop_mode, Animation.LOOP_LINEAR, "walk loops")
	assert_eq(ap.get_animation("death").loop_mode, Animation.LOOP_NONE, "death plays once")
	assert_eq(ap.callback_mode_process, AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL,
		"driven manually with real delta")
	# every converted surface uses the painterly unit shader
	var shaded := 0
	for mi: MeshInstance3D in v.model.find_children("*", "MeshInstance3D", true, false):
		for s in mi.mesh.get_surface_count():
			var mat := mi.get_surface_override_material(s) as ShaderMaterial
			if mat != null and mat.shader == AssetLibrary.UNIT_SHADER:
				shaded += 1
	assert_true(shaded >= 2, "unit surfaces converted (%d)" % shaded)


func test_walk_playback_matches_stride() -> void:
	var w := _visual_world()
	var u := w.spawn_unit("test_glb_infantry", 0, Vector3(20, 0, 20))
	var v := u.view as UnitView
	var stride := float(AssetLibrary.unit_entry(v.model_path)["walk_anim_speed"])
	assert_near(v.walk_rate(4.0), 4.0 / stride, 0.001, "rate = speed / stride")
	assert_near(v.walk_rate(2.0) * 2.0, v.walk_rate(4.0), 0.001, "linear in speed")
	# walking in the sim switches the view to the walk clip
	w.issue({"type": "move", "player": 0, "units": [u.id], "pos": Vector3(40, 0, 20)})
	for i in 20:
		w.step()
		v._process(1.0 / 60.0)
	assert_eq(v.anim_state, "walk", "walk clip while moving")


func test_attack_hit_frame_lands_on_damage_point() -> void:
	var w := _visual_world()
	var u := w.spawn_unit("test_glb_infantry", 0, Vector3(20, 0, 20))
	var v := u.view as UnitView
	var e := AssetLibrary.unit_entry(v.model_path)
	var hit := float(e["attack_hit_s"])
	var total := (u.damage_point_ticks + u.backswing_ticks) * World.DT
	var dp := u.damage_point_ratio()
	assert_near(v.strike_clip_time("attack", dp, dp, total), hit, 0.0001, "damage point -> hit frame")
	var prev := -1.0
	for k in 21:
		var t := v.strike_clip_time("attack", k / 20.0, dp, total)
		assert_true(t >= prev, "clip time is monotonic in swing progress")
		prev = t
	var windup := hit - v.strike_clip_time("attack", 0.0, dp, total)
	assert_true(windup / (dp * total) <= UnitView.MAX_WINDUP_SPEED + 0.001, "wind-up never too fast")
	# in a real fight: during the swing the view shows the attack clip inside its window
	var foe := w.spawn_unit("test_glb_infantry", 1, Vector3(21.0, 0, 20))
	var seen := false
	for i in 120:
		w.step()
		v._process(1.0 / 60.0)
		if u.swing_progress() >= 0.0:
			assert_eq(v.anim_state, "attack", "attack clip during the swing")
			seen = true
			break
	assert_true(seen and foe != null, "a swing happened")


func test_death_plays_once_holds_and_ebbs_team_colour() -> void:
	var w := _visual_world()
	var u := w.spawn_unit("test_glb_infantry", 0, Vector3(20, 0, 20))
	var v := u.view as UnitView
	u.take_damage(99999.0, null)
	for i in 3:
		w.step()
	var length := v.animation_player().get_animation("death").length
	for i in 150:
		w.step()
		v._process(1.0 / 30.0)
	assert_eq(v.anim_state, "death", "death clip")
	assert_near(v.current_clip_time(), length, 0.02, "holds the last frame")
	assert_near(float(v.instance_param(&"team_sat")), 0.2, 0.001, "team colour ebbed")


func test_instance_uniforms_team_rim_and_latched_flash() -> void:
	var w := _visual_world()
	w.player(0).color = Color("#2EAE3A")
	var u := w.spawn_unit("test_glb_infantry", 0, Vector3(20, 0, 20))
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(40, 0, 40))
	var v := u.view as UnitView
	assert_eq(v.instance_param(&"team_color"), Color("#2EAE3A"), "team colour slot")
	var rim: Color = v.instance_param(&"rim_col")
	assert_near(rim.g, Color("#2EAE3A").g * 0.6, 0.001, "rim = team colour x 0.6")
	assert_eq((mine.view as UnitView).instance_param(&"team_color"), Color.WHITE, "neutrals carry no team colour")
	v.set_selected(true)
	assert_true(float(v.instance_param(&"rim_boost")) > 0.0, "selection boosts the rim")
	v.set_selected(false)
	assert_eq(float(v.instance_param(&"rim_boost")), 0.0, "deselect clears it")
	v.flash(0.5)
	var f: Vector4 = v.instance_param(&"flash")
	assert_near(f.x, RenderAtmos.now(), 0.5, "flash latched at the fx clock")
	assert_eq(f.y, 0.5, "strength")
	v.flash(0.3)
	assert_eq((v.instance_param(&"flash") as Vector4).y, 0.5, "a re-hit inside the window keeps the max")


func test_structures_scale_to_data_footprint() -> void:
	var w := _visual_world()
	var b := w.spawn_unit("test_glb_croft", 0, Vector3(20, 0, 20))
	var v := b.view as UnitView
	assert_true(v.model != null, "kit building instanced")
	var ab := AssetLibrary.mesh_bounds(v.model)
	var width := maxf(ab.size.x, ab.size.z) * v.model_scale
	assert_near(width, 4.0, 0.25, "an 8x8-cell footprint is 4 m wide")
	assert_eq(v.instance_param(&"variant_a"), null, "no construction param before the first frame")
	v._process(0.016)
	assert_eq((v.instance_param(&"variant_a") as Vector4).x, 1.0, "complete structures are fully revealed")


## Data model hooks (data/SCHEMA.md): an upgraded hall draws its T1 model plus `model_addons` in
## the hall's model space; `model_fit: none` keeps the def scale; a Gold Seam swaps to
## `model_depleted` when Events.mine_depleted names it.
func test_structure_addons_fit_and_depleted_model() -> void:
	var w := _visual_world()
	w.add_player(PlayerState.NEUTRAL_PASSIVE, PlayerState.NEUTRAL_PASSIVE)
	var burg := w.spawn_unit("kingdom_walled_burg", 0, Vector3(20, 0, 20))
	var bv := burg.view as UnitView
	assert_true(bv.model_path.ends_with("kingdom_moot_hall.glb"), "upgraded hall keeps the hall model")
	var addon := bv.model.get_node_or_null("Addon") if bv.model != null else null
	assert_true(addon != null, "and draws its add-on as a child (shares the hall's scale)")
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(40, 0, 20))
	assert_near(bv.model_scale, (hall.view as UnitView).model_scale, 0.0001, "same fit as the T1 hall")
	Defs.units["test_glb_croft"]["model_fit"] = "none"
	Defs.units["test_glb_croft"]["model_scale"] = 1.5
	var raw := w.spawn_unit("test_glb_croft", 0, Vector3(20, 0, 40))
	assert_near((raw.view as UnitView).model_scale, 1.5, 0.0001, "model_fit none keeps the def scale")
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(40, 0, 40))
	var mv := mine.view as UnitView
	assert_true(mv.model_path.ends_with("gold_mine.glb"), "full seam model")
	Events.mine_depleted.emit(mine)
	assert_true(mv.model_path.ends_with("gold_mine_collapsed.glb"), "collapsed once depleted")
	assert_true(mv.model != null and mv.model.is_inside_tree(), "the collapsed model is shown")
	assert_eq(mv.instance_param(&"team_color"), Color.WHITE, "instance uniforms re-applied")


# --- terrain, trees, lighting --------------------------------------------------------------

func test_terrain_tile_data_and_connectivity() -> void:
	var m := flat_map(16, 16, 1)
	for y in 16:
		for x in range(8, 16):
			m.cliff[m.idx(x, y)] = 2
	m.add_ramp(Rect2i(6, 7, 2, 2), Vector2i(1, 0), 1)
	m.compute_heights()
	var w := _visual_world(m)
	var t := w.terrain
	assert_eq(t.ladder_at(2, 2), TerrainTextures.MEADOW, "legacy grass -> meadow")
	assert_eq(t.ladder_at(6, 7), TerrainTextures.DIRT, "ramps are painted dirt")
	var img := t.tile_info.get_image()
	var bits := img.get_pixel(7, 2).g8
	assert_eq(bits & 1, 0, "no blending across the wall at x = 8")
	assert_eq((bits >> 1) & 1, 1, "open to the west")
	assert_true(t.chunks.size() > 0 and t.material.get_shader_parameter("ground_tex") is Texture2DArray,
		"ladder Texture2DArray bound")
	var arr := TerrainTextures.ladder_array()
	assert_eq(arr.get_layers(), 7, "7-tile ladder")
	assert_true(arr.has_mipmaps(), "mipmapped")
	t.paint_tiles(Rect2i(1, 1, 2, 2), TerrainTextures.ROAD)
	assert_eq(t.ladder_at(1, 1), TerrainTextures.ROAD, "runtime repaint (building pads)")


func test_tree_lod_promotion_and_stumps() -> void:
	var m := flat_map(16, 16, 0)
	for y in range(10, 13):
		for x in range(10, 13):
			m.trees.append(Vector2i(x, y))
			m.tree_types.append(0)
	var w := _visual_world(m)
	var d := w.doodads
	var centre: int = d._index[Vector2i(11, 11)]
	assert_true(d.is_enclosed(centre), "the centre tree is enclosed")
	assert_true(d.tree_mesh_kind(centre).ends_with("|lod"), "enclosed trees use LOD1")
	var edge: int = d._index[Vector2i(10, 11)]
	assert_true(d.tree_mesh_kind(edge).ends_with("|full"), "edge trees use the full mesh")
	d.remove_tree(edge)
	assert_eq(d.tree_mesh_kind(edge), "", "felled tree hidden")
	assert_true(d.tree_mesh_kind(centre).ends_with("|full"), "exposed neighbour promoted to the full mesh")
	assert_true(d.materials.size() >= 2, "foliage + bark materials")


func test_time_of_day_keys() -> void:
	var noon := TimeOfDay.sample(12.0)
	assert_near(noon["sun_energy"], 1.12, 0.001, "noon sun energy")
	assert_eq((noon["ambient"] as Color).to_html(false), "a6bad8", "noon ambient")
	var mid := TimeOfDay.sample(0.0)
	assert_near(mid["moon_energy"], 0.38, 0.001, "midnight moon")
	assert_eq(mid["sun_energy"], 0.0, "no sun at midnight")
	assert_false(mid["sun_owns_shadows"], "the moon owns the shadows at night")
	assert_true(noon["sun_owns_shadows"], "the sun owns them by day")
	var prev := TimeOfDay.sample(0.0)
	for k in range(1, 481):
		var s := TimeOfDay.sample(k * 0.05)
		assert_lt(absf(float(s["sun_energy"]) - float(prev["sun_energy"])), 0.2, "sun energy glides at %.2f h" % (k * 0.05))
		assert_lt(absf(float(s["ambient_energy"]) - float(prev["ambient_energy"])), 0.1, "ambient glides")
		prev = s
	for h in [10.0, 13.0, 15.0]:
		var el := TimeOfDay.sun_elevation(h)
		assert_true(el >= 50.0 and el <= 55.0, "day sun 50-55 deg (%.1f at %.0f h)" % [el, h])


func test_day_night_applies_keys() -> void:
	var w := _visual_world()
	var dn := w.day_night
	dn.fixed_hour = 22.0
	dn._process(0.016)
	assert_false(dn.sun.visible, "no sun at night")
	assert_true(dn.moon.visible and dn.moon.shadow_enabled, "moon lit and casting")
	assert_eq(dn.moon.light_color, TimeOfDay.MOON, "moon #8EA6FF")
	dn.fixed_hour = 12.0
	dn._process(0.016)
	assert_true(dn.sun.visible and dn.sun.shadow_enabled, "sun by day")
	var e := dn.env.environment
	assert_eq(e.tonemap_mode, Environment.TONE_MAPPER_REINHARDT, "Reinhard")
	assert_eq(e.fog_mode, Environment.FOG_MODE_DEPTH, "depth fog")
	assert_near(e.fog_depth_begin, 32.0, 0.01, "fog from 32 m")
	assert_near(e.fog_depth_end, 90.0, 0.01, "to 90 m")
	assert_true(e.adjustment_color_correction is Texture3D, "grading LUT")
	var fwd := -dn.sun.global_basis.z
	assert_true(fwd.x > 0.0 and fwd.z < 0.0, "sun shines from screen lower-left")
	assert_near(rad_to_deg(asin(-fwd.y)), TimeOfDay.sun_elevation(12.0), 0.5, "sun elevation")


func test_render_profile_camera_defaults() -> void:
	var cam: RtsCamera = load("res://src/input/rts_camera.gd").new()
	tree.root.add_child(cam)
	track(cam)
	RenderProfile.apply_camera(cam)
	assert_eq(cam.fov, 55.0, "FOV 55 vertical")
	assert_eq(cam.keep_aspect, Camera3D.KEEP_HEIGHT, "KEEP_HEIGHT")
	assert_eq(cam.pitch_deg, -56.0, "pitch")
	assert_near(cam.default_distance, 25.8, 0.001, "default distance")
	assert_near(cam.min_distance, 18.75, 0.001, "zoom in")
	assert_near(cam.max_distance, 35.2, 0.001, "zoom out")


func test_color_grade_keeps_night_readable() -> void:
	var lut := ColorGrade.lut(1.0, 0.0)
	assert_eq(lut.get_width(), ColorGrade.N, "17^3 LUT")
	var black := ColorGrade.grade(Color.BLACK, 1.0, 0.0)
	assert_true(black.b > 0.02, "night floor is lifted, never black")
	var mid := ColorGrade.grade(Color(0.5, 0.5, 0.5), 1.0, 0.0)
	assert_true(mid.b > mid.r, "night is blue")


# --- views never change the sim ------------------------------------------------------------

func _record_hit(u: Node, amount: float, src: Node) -> void:
	_hits.append([u.get("world").tick_count, u.get("id"), amount, src.get("id") if src != null else 0])


func _glb_brawl(visual: bool, frames: Array) -> Array:
	_hits.clear()
	var w := _visual_world() if visual else make_world()
	for i in 3:
		w.spawn_unit("test_glb_infantry", 0, Vector3(14, 0, 18 + i * 1.2))
		w.spawn_unit("test_glb_infantry", 1, Vector3(20, 0, 18 + i * 1.2))
	var ids: Array = []
	for u in w.unit_list:
		if u.player_id == 0:
			ids.append(u.id)
	w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": Vector3(24, 0, 19)})
	for i in 300:
		w.step()
		if visual:
			for f in int(frames[i % frames.size()]):
				await tree.process_frame
	return _hits.duplicate(true)


func test_glb_views_do_not_change_sim_outcomes() -> void:
	Events.unit_damaged.connect(_record_hit)
	var headless: Array = await _glb_brawl(false, [])
	var rendered: Array = await _glb_brawl(true, [0, 2, 1, 3])
	Events.unit_damaged.disconnect(_record_hit)
	assert_true(headless.size() > 10, "a fight happened (%d hits)" % headless.size())
	assert_eq(rendered, headless, "identical hits with GLB views at uneven frame pacing")
