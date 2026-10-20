class_name UnitView
extends Node3D
## Visual representation of a Unit (visual only: reads sim state, never writes it).
## Model: AssetLibrary.model_path(def) — the def's `model`, a manifest alias or
## assets/models/{units,buildings,neutral}/<def_id>.glb — else a procedural placeholder from the
## def's `shape` hint (humanoid / building / mine). Structures are scaled to their data footprint.
## Animation (rigged GLBs): clips idle / walk / attack / death / cast / work with fallbacks, driven
## manually every frame with real delta (refresh-rate independent):
##   - 0.15 s crossfades between states;
##   - walk playback = actual speed / the clip's stride speed (assets/models/units/manifest.json
##     `walk_anim_speed`), so feet do not slide;
##   - attack / cast / work clips are *positioned* from the sim's swing progress, so the clip's
##     strike frame (`attack_hit_s`) lands exactly on the sim damage point;
##   - death plays once from the sim death time and holds; the team colour ebbs and the body sinks
##     before the World frees the corpse.
## Materials are the shared painterly shaders (src/render/); per-instance values (team colour,
## rim, latched flash, construction progress, corpse ebb) are instance uniforms in the fixed slot
## map of src/render/unit_uniforms.gdshaderinc, written only when they change.
## The `rig` node has physics interpolation OFF so per-frame local motion composes with the parent
## Unit's interpolated transform.

const SKIN := Color(0.85, 0.68, 0.52)
const DARK := Color(0.16, 0.13, 0.11)
const WOOD := Color(0.42, 0.29, 0.17)
const STEEL := Color(0.70, 0.72, 0.76)
const GOLD := Color(0.98, 0.78, 0.22)
const PLACEHOLDER_SHADER := preload("res://src/entities/unit_placeholder.gdshader")
const UNIT_SHADER := preload("res://src/render/unit.gdshader")
const TOPPLE_TIME := 0.55
const SINK_TIME := 1.5
const BLEND := 0.15
const MAX_WINDUP_SPEED := 3.0    ## a wind-up never plays faster than this (starts later instead)
const MIN_WINDUP_SPEED := 0.6
const DEFAULT_STRIDE := 0.7      ## m/s for a 1.75 m model when the manifest has no entry
const RIM_UNIT := 0.35
const RIM_HERO := 0.55
const RIM_CAP := 0.6
const SELECT_BOOST := 0.2
const HOVER_BOOST := 0.12
const FLASH_END := Color(1.0, 0.353, 0.282)   ## #FF5A48
const BODY_COLORS: Dictionary = {
	"tool": Color(0.55, 0.42, 0.28), "sword": Color(0.52, 0.55, 0.60),
	"bow": Color(0.30, 0.44, 0.25), "club": Color(0.42, 0.34, 0.27), "none": Color(0.5, 0.5, 0.5),
}
## Logical state -> clips to try, in order.
const CLIP_FALLBACKS: Dictionary = {
	"idle": ["idle", "stand", "walk"],
	"walk": ["walk", "run", "idle"],
	"attack": ["attack", "work", "cast"],
	"cast": ["cast", "attack"],
	"work": ["work", "attack"],
	"death": ["death"],
}

static var _meshes: Dictionary = {}       ## primitive part cache
static var _merged: Dictionary = {}       ## "def|colour" -> merged placeholder mesh
static var _vc_material: ShaderMaterial
static var _placeholder_unit_mat: ShaderMaterial
static var _parts: Array = []
static var _frustum: Array[Plane] = []    ## camera frustum, refreshed once per frame
static var _frustum_frame: int = -1

var unit: Unit
var rig: Node3D
var body: Node3D
var model: Node3D                         ## instanced GLB (null for placeholders)
var model_path: String = ""
var model_scale: float = 1.0
var height: float = 1.5
var is_structure: bool = false
var anim_state: String = ""               ## logical state currently shown
var selected: bool = false
var hovered: bool = false
var _t: float = 0.0
var _move: float = 0.0
var _anim: AnimationPlayer
var _clips: Dictionary = {}               ## logical state -> clip name present in the model
var _entry: Dictionary = {}               ## unit manifest entry
var _clip: String = ""                    ## clip currently playing
var _geoms: Array[GeometryInstance3D] = []
var _params: Dictionary = {}              ## last value written per instance uniform
var _mesh: GeometryInstance3D             ## placeholder mesh
var _fall_dir: float = 1.0
var _driven_t: float = -1.0
var _skipped: float = 0.0                 ## animation time owed while off-screen


func setup(u: Unit) -> void:
	unit = u
	name = "View"
	rig = Node3D.new()
	rig.name = "Rig"
	rig.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(rig)
	body = Node3D.new()
	body.name = "Body"
	rig.add_child(body)
	var d := u.def
	is_structure = u.is_building or u.is_resource
	height = float(d.get("height", 1.5)) * float(d.get("scale", 1.0))
	_t = float(u.id) * 1.37
	_fall_dir = 1.0 if u.id % 2 == 0 else -1.0
	model_path = AssetLibrary.model_path(d, u.def_id)
	if model_path.is_empty() or not _load_model(model_path):
		model_path = ""
		_add_placeholder(d)
	_init_instance_params()


# --- public hooks --------------------------------------------------------------------------

## Latched hit flash (CMB-17): written once, the shader evaluates the curve on the fx clock.
## Called by Vfx on `unit_damaged`.
func flash(strength: float = 1.0, tint: Color = FLASH_END, duration: float = -1.0) -> void:
	var dur := duration if duration > 0.0 else (0.1 if unit != null and unit.is_hero else 0.08)
	var cur: Vector4 = _params.get(&"flash", Vector4(-100.0, 0.0, 0.08, 0.0))
	var now := RenderAtmos.now()
	# a re-hit inside the window takes the max strength
	if now - cur.x < cur.z:
		strength = maxf(strength, cur.y)
	_set_param(&"flash", Vector4(now, clampf(strength, 0.0, 1.0), dur, 0.0))
	_set_param(&"flash_tint", tint)


## Selection highlight hook (rim boost; never shares a look with hits).
func set_selected(on: bool) -> void:
	selected = on
	_update_rim()


func set_hovered(on: bool) -> void:
	hovered = on
	_update_rim()


func team_color() -> Color:
	return unit.world.player_color(unit.player_id) if unit.world != null else Color.WHITE


## Logical clip names this model can play (idle, walk, ...), for tests and tools.
func available_states() -> Array:
	return _clips.keys()


func animation_player() -> AnimationPlayer:
	return _anim


func current_clip() -> String:
	return _clip


func current_clip_time() -> float:
	return _anim.current_animation_position if _anim != null and _anim.has_animation(_clip) else 0.0


## Walk playback rate for a ground speed (m/s): stride matching.
func walk_rate(speed_mps: float) -> float:
	var stride := float(_entry.get("walk_anim_speed", DEFAULT_STRIDE * model_height() / 1.75))
	stride = maxf(stride * model_scale, 0.05)
	return clampf(speed_mps / stride, 0.25, 8.0)


func model_height() -> float:
	if model_path.is_empty():
		return height
	return float(_entry.get("height_m", AssetLibrary.model_info(model_path).get("height", height)))


## Clip time that the swing progress maps to: [0, dp] -> [start, hit], [dp, 1] -> [hit, end].
## `total_s` is the swing duration in seconds (damage point + backswing). The wind-up start is
## pulled in so it never plays faster than MAX_WINDUP_SPEED or slower than MIN_WINDUP_SPEED.
func strike_clip_time(state: String, progress: float, dp: float, total_s: float) -> float:
	var clip: String = _clips.get(state, "")
	if clip.is_empty() or _anim == null:
		return 0.0
	var length := _anim.get_animation(clip).length
	var key := clip if _entry.has(clip + "_hit_s") else state
	var hit := float(_entry.get(key + "_hit_s", length * 0.5))
	var start := float(_entry.get(key + "_start_s", 0.0))
	var end := float(_entry.get(key + "_end_s", length))
	dp = clampf(dp, 0.02, 0.98)
	var wind_s := maxf(dp * total_s, 0.01)
	start = clampf(start, hit - MAX_WINDUP_SPEED * wind_s, hit - MIN_WINDUP_SPEED * wind_s)
	start = maxf(start, 0.0)
	end = clampf(end, minf(hit + 0.05, length), length)
	if progress <= dp:
		return lerpf(start, hit, progress / dp)
	return lerpf(hit, end, (progress - dp) / (1.0 - dp))


## The strike frame time of a state's clip (manifest `<clip>_hit_s`, else half the clip).
func strike_hit_time(state: String) -> float:
	var clip: String = _clips.get(state, "")
	if clip.is_empty() or _anim == null:
		return 0.0
	var length := _anim.get_animation(clip).length
	return float(_entry.get(clip + "_hit_s", _entry.get(state + "_hit_s", length * 0.5)))


# --- per frame -----------------------------------------------------------------------------

func _process(delta: float) -> void:
	if unit == null:
		return
	if is_structure:
		_update_structure()
		if not unit.alive:
			_animate_structure_death()
		return
	if not unit.alive:
		_animate_death(delta)
		return
	_t += delta
	var target := 0.0
	var spd := unit.velocity.length()
	if unit.speed > 0.0:
		target = clampf(spd / unit.speed, 0.0, 1.0)
	_move = move_toward(_move, target, delta * 6.0)
	var swing := unit.swing_progress()
	if _anim != null:
		# off-screen rigs skip the skeleton work; looping clips catch up when seen again
		if not on_screen():
			_skipped = minf(_skipped + delta, 4.0)
			return
		_drive_clips(delta + _skipped, swing, spd)
		_skipped = 0.0
		return
	_procedural_motion(swing)


func _drive_clips(delta: float, swing: float, spd: float) -> void:
	var hint := _hint()
	if swing >= 0.0 and _clips.has("attack"):
		var total := (unit.damage_point_ticks + unit.backswing_ticks) * World.DT
		_drive("attack", strike_clip_time("attack", swing, unit.damage_point_ratio(), total), delta)
		return
	if hint == "cast" and _clips.has("cast"):
		var cp := _progress("cast_progress")
		if cp >= 0.0:
			_drive("cast", strike_clip_time("cast", cp, _ratio("cast_point_ratio", 0.5), _ratio("cast_time", 1.0)), delta)
			return
	if hint == "work" and _clips.has("work"):
		var wp := _progress("work_progress")
		if wp >= 0.0:
			_drive("work", strike_clip_time("work", wp, _ratio("work_point_ratio", 0.6), _ratio("work_time", 1.0)), delta)
		else:
			_loop("work", 1.0, delta)
		return
	if _move > 0.3 and spd > 0.05 and _clips.has("walk"):
		_loop("walk", walk_rate(spd), delta)
	elif _clips.has("idle"):
		_loop("idle", 1.0, delta)


## Bounding-sphere test against the current camera's frustum (true without a camera, e.g. tests).
func on_screen() -> bool:
	var frame := Engine.get_process_frames()
	if frame != _frustum_frame:
		_frustum_frame = frame
		var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
		_frustum.assign(cam.get_frustum() if cam != null else [])
	if _frustum.is_empty():
		return true
	var r := maxf(height, 1.0)
	var c := global_position + Vector3(0.0, r * 0.5, 0.0)
	for p in _frustum:
		if p.distance_to(c) > r:
			return false
	return true


## Optional animation hint published by sim systems ("work", "cast"); never required.
func _hint() -> String:
	var h: Variant = unit.get("anim_hint")
	return str(h) if h != null else ""


func _progress(method: String) -> float:
	return float(unit.call(method)) if unit.has_method(method) else -1.0


func _ratio(method: String, fallback: float) -> float:
	return float(unit.call(method)) if unit.has_method(method) else fallback


## Looping clip advanced by real delta x rate (crossfaded on entry).
func _loop(state: String, rate: float, delta: float) -> void:
	_enter(state)
	_driven_t = -1.0
	_anim.advance(delta * rate)


## One-shot clip positioned at clip time `t` (the blend still advances by real delta).
func _drive(state: String, t: float, delta: float) -> void:
	var restarted := _enter(state)
	if not restarted and _driven_t >= 0.0 and t < _driven_t - 0.1:
		# a new swing started straight after the last one: restart the clip
		_anim.stop(true)
		_anim.play(_clip, BLEND)
	_driven_t = t
	var step := minf(delta, t)
	_anim.seek(t - step, false)
	_anim.advance(step)


## Switches to a logical state's clip with a crossfade. Returns true when it changed.
func _enter(state: String) -> bool:
	if anim_state == state:
		return false
	anim_state = state
	_clip = _clips.get(state, "")
	if _clip.is_empty():
		return false
	_anim.play(_clip, BLEND)
	return true


func _procedural_motion(swing: float) -> void:
	var stride := _t * 9.0
	var bob := absf(sin(stride)) * 0.07 * height * _move
	var breathe := 1.0 + 0.025 * sin(_t * 2.2) * (1.0 - _move)
	body.position = Vector3(0.0, bob, 0.0)
	body.scale = Vector3(1.0, breathe, 1.0)
	body.rotation = Vector3(-0.14 * _move, 0.0, sin(stride) * 0.05 * _move)
	if swing >= 0.0:
		_animate_swing(swing)


## Strike curve peaks at the damage point: melee lunges forward, ranged leans back to draw.
func _animate_swing(swing: float) -> void:
	var dp := maxf(unit.damage_point_ratio(), 0.05)
	var s := smoothstep(0.0, dp, swing) if swing < dp else 1.0 - smoothstep(dp, 1.0, swing)
	if unit.projectile.is_empty():
		body.rotation.x = -0.5 * s
		body.position.z = -0.22 * s * height
	else:
		body.rotation.x = 0.16 * s
		body.position.z = 0.05 * s * height


## Death clip from the sim death time (plays once, holds the last frame), corpse team-colour ebb
## (CMB-31: from 0.7 s over 1.4 s, feet to head) and the sink before the World frees the corpse.
func _animate_death(delta: float) -> void:
	var t := unit.dead_time()
	var decay := unit.decay_ticks() * World.DT
	var sink := clampf((t - (decay - SINK_TIME)) / SINK_TIME, 0.0, 1.0)
	var ebb := clampf((t - 0.7) / 1.4, 0.0, 1.0)
	var top := model_height() * model_scale + 0.2
	_set_param(&"team_sat", lerpf(1.0, 0.2, ebb))
	_set_param(&"sat_front", -1.0 if ebb <= 0.0 else top * (0.5 - 0.5 * cos(PI * ebb)))
	_set_param(&"rim_col", Color(0, 0, 0, 0))
	if _anim != null and _clips.has("death"):
		var length := _anim.get_animation(_clips["death"]).length
		_drive("death", minf(t * 1.15, length), delta)
		body.position.y = -sink * height * 0.6
		return
	var f := clampf(t / TOPPLE_TIME, 0.0, 1.0)
	var fall := f * f * (3.0 - 2.0 * f)
	body.scale = Vector3.ONE
	body.rotation = Vector3(PI * 0.5 * fall, 0.0, 0.25 * fall * _fall_dir)
	body.position = Vector3(0.0, 0.14 * height * fall - sink * height * 0.5, 0.0)


func _animate_structure_death() -> void:
	var t := unit.dead_time()
	var decay := unit.decay_ticks() * World.DT
	var k := clampf(t / decay, 0.0, 1.0)
	body.position = Vector3(0.0, -height * 1.15 * k * k, 0.0)
	body.rotation = Vector3(0.04 * k, 0.0, 0.06 * k * _fall_dir)


## Construction reveal: `build_progress` (0..1) when the sim publishes it, 1 otherwise.
func _update_structure() -> void:
	var bp: Variant = unit.get("build_progress")
	var p := clampf(float(bp), 0.0, 1.0) if bp != null else 1.0
	_set_param(&"variant_a", Vector4(p, 0.0, 0.0, 0.0))


# --- instance uniforms ---------------------------------------------------------------------

func _init_instance_params() -> void:
	var neutral := unit.player_id >= PlayerState.NEUTRAL_HOSTILE
	_set_param(&"team_color", Color.WHITE if neutral else team_color(), true)
	_set_param(&"team_sat", 1.0, true)
	_set_param(&"sat_front", -1.0, true)
	_update_rim(true)


func _update_rim(force: bool = false) -> void:
	if unit == null:
		return
	var neutral := unit.player_id >= PlayerState.NEUTRAL_HOSTILE
	var tc := team_color()
	var base := 0.0 if neutral else (RIM_HERO if unit.is_hero else RIM_UNIT)
	var rc := Color(0.5, 0.5, 0.46, 0.0) if neutral else Color(tc.r * 0.6, tc.g * 0.6, tc.b * 0.6, base)
	_set_param(&"rim_col", rc, force)
	var boost := (SELECT_BOOST if selected else 0.0) + (HOVER_BOOST if hovered else 0.0)
	boost = minf(boost, maxf(RIM_CAP - base, 0.0) + SELECT_BOOST)
	_set_param(&"rim_boost", boost, force)


func _set_param(p: StringName, v: Variant, force: bool = false) -> void:
	if not force and _params.has(p) and _params[p] == v:
		return
	_params[p] = v
	for g in _geoms:
		g.set_instance_shader_parameter(p, v)


func instance_param(p: StringName) -> Variant:
	return _params.get(p)


# --- asset models --------------------------------------------------------------------------

func _load_model(path: String) -> bool:
	var inst := AssetLibrary.instantiate(path, "structure" if is_structure else "unit")
	if inst == null:
		return false
	model = inst
	model.name = "Model"
	if is_structure:
		model_scale = _structure_scale(path)
		var addon_of := str(AssetLibrary.building_entry(path).get("addon_of", ""))
		if not addon_of.is_empty():
			# T2 hall upgrades are add-ons in the T1 hall's model space: show both
			var base_path := AssetLibrary.model_path({}, addon_of)
			var base := AssetLibrary.instantiate(base_path, "structure") if not base_path.is_empty() else null
			if base != null:
				base.name = "Base"
				model.add_child(base)
	else:
		_entry = AssetLibrary.unit_entry(path)
		model_scale = float(unit.def.get("model_scale", unit.def.get("scale", 1.0)))
	model.scale = Vector3.ONE * model_scale
	body.add_child(model)
	for g: GeometryInstance3D in model.find_children("*", "GeometryInstance3D", true, false):
		_geoms.append(g)
	_configure_structure_materials(path)
	_anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _anim != null:
		_anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		for state: String in CLIP_FALLBACKS:
			for c: String in CLIP_FALLBACKS[state]:
				if _anim.has_animation(c):
					_clips[state] = c
					break
		if _clips.has("idle"):
			_enter("idle")
			_anim.advance(fmod(_t, 2.0))   # desync idles
	return true


## Uniform scale that fits a structure model to its data footprint (sim footprint = mesh width).
func _structure_scale(path: String) -> float:
	var fp: Array = unit.def.get("footprint", [0, 0])
	var fp_m := maxf(float(fp[0]), float(fp[1])) * Grid.CELL
	if fp_m <= 0.0:
		return float(unit.def.get("scale", 1.0))
	var entry := AssetLibrary.building_entry(path)
	var model_fp := 0.0
	if entry.has("footprint_m"):
		var f: Array = entry["footprint_m"]
		model_fp = maxf(float(f[0]), float(f[1]))
	if entry.has("addon_of"):
		model_fp = 8.0   # add-ons live in the 8 m hall's model space
	if model_fp <= 0.0:
		var ab: AABB = AssetLibrary.model_info(path)["aabb"]
		model_fp = maxf(ab.size.x, ab.size.z)
	return fp_m / maxf(model_fp, 0.1)


## Kit buildings reveal by their normalized-height UV2; AI-modelled halls by model-space Y.
func _configure_structure_materials(path: String) -> void:
	if not is_structure:
		return
	var h: float = AssetLibrary.model_info(path).get("height", height)
	for g in _geoms:
		var mi := g as MeshInstance3D
		if mi == null or mi.mesh == null:
			continue
		for s in mi.mesh.get_surface_count():
			var m := mi.get_surface_override_material(s) as ShaderMaterial
			if m == null or m.shader != AssetLibrary.STRUCTURE_SHADER:
				continue
			var has_uv2: bool = (mi.mesh.surface_get_format(s) & Mesh.ARRAY_FORMAT_TEX_UV2) != 0
			m.set_shader_parameter("use_uv2_height", has_uv2)
			m.set_shader_parameter("two_pass_reveal", has_uv2 and unit.def_id.begins_with("clans"))
			m.set_shader_parameter("model_height", h)


# --- placeholder builders ------------------------------------------------------------------

## Placeholder parts are merged into one vertex-coloured mesh per (def, team colour) and
## shared by every unit of that kind: one draw call per unit instead of ~10.
func _add_placeholder(d: Dictionary) -> void:
	var key := "%s|%s" % [unit.def_id, team_color().to_html()]
	if not _merged.has(key):
		_parts.clear()
		match str(d.get("shape", "humanoid")):
			"building":
				_build_building(d)
			"mine":
				_build_mine(d)
			_:
				_build_humanoid(d)
		_merged[key] = ProcMesh.merge(_parts)
		_parts.clear()
	var mi := MeshInstance3D.new()
	mi.name = "Placeholder"
	mi.mesh = _merged[key]
	mi.material_override = placeholder_unit_material()
	body.add_child(mi)
	_mesh = mi
	_geoms.append(mi)


func _build_humanoid(d: Dictionary) -> void:
	var s := float(d.get("scale", 1.0))
	var h := height
	var r := float(d.get("radius", 0.4)) * s
	var weapon := str(d.get("weapon", "none"))
	var body_col: Color = BODY_COLORS.get(weapon, BODY_COLORS["none"])
	var tc := team_color()
	var torso_h := h * 0.58
	_part(_capsule(r * 0.62, torso_h), body_col, Vector3(0, h * 0.12 + torso_h * 0.5, 0))
	_part(_sphere(h * 0.12), SKIN, Vector3(0, h * 0.83, 0))
	_part(_cyl(r * 0.66, r * 0.66, h * 0.09), tc, Vector3(0, h * 0.5, 0))
	for side in [-1.0, 1.0]:
		_part(_box(Vector3(r * 0.3, h * 0.12, r * 0.45)), DARK, Vector3(side * r * 0.28, h * 0.06, -r * 0.08))
		_part(_sphere(r * 0.24), tc, Vector3(side * r * 0.62, h * 0.66, 0))
	match weapon:
		"sword":
			_part(_box(Vector3(0.07, 0.07, h * 0.5)), STEEL, Vector3(r * 0.85, h * 0.42, -h * 0.2))
			_part(_box(Vector3(0.08, h * 0.38, h * 0.3)), tc, Vector3(-r * 0.85, h * 0.45, -0.05))
		"bow":
			_part(_cyl(0.025, 0.025, h * 0.75), WOOD, Vector3(-r * 0.8, h * 0.52, -0.1))
			_part(_box(Vector3(0.18, 0.18, 0.4)), WOOD, Vector3(r * 0.4, h * 0.62, r * 0.6))
		"tool":
			_part(_cyl(0.03, 0.03, h * 0.55), WOOD, Vector3(r * 0.8, h * 0.4, -0.05))
			_part(_box(Vector3(0.28, 0.08, 0.08)), STEEL, Vector3(r * 0.8, h * 0.66, -0.05))
		"club":
			_part(_cyl(0.11, 0.05, h * 0.55), WOOD, Vector3(r * 0.85, h * 0.45, -0.1))


func _build_building(d: Dictionary) -> void:
	var fp: Array = d.get("footprint", [8, 8])
	var w := float(fp[0]) * Grid.CELL * 0.9
	var depth := float(fp[1]) * Grid.CELL * 0.9
	var h := height
	var wall := Color(0.64, 0.57, 0.46)
	var roof := Color(0.38, 0.22, 0.16)
	var tc := team_color()
	# foundation reaches below the lowest footprint corner so slopes never show a gap
	_part(_box(Vector3(w * 1.06, 0.8, depth * 1.06)), Color(0.45, 0.43, 0.40), Vector3(0, -0.2, 0))
	var base_h := h * 0.55
	_part(_box(Vector3(w, base_h, depth)), wall, Vector3(0, base_h * 0.5, 0))
	_part(_box(Vector3(w * 1.02, base_h * 0.12, depth * 1.02)), tc, Vector3(0, base_h * 0.86, 0))
	_part(_box(Vector3(w * 0.28, base_h * 0.6, 0.12)), DARK, Vector3(0, base_h * 0.3, -depth * 0.5 - 0.02))
	if str(d.get("roof", "pyramid")) == "gable":
		var prism := _cached("prism:%.2f:%.2f:%.2f" % [w, h, depth], func() -> Mesh:
			var p := PrismMesh.new()
			p.size = Vector3(w * 1.1, h * 0.45, depth * 1.05)
			return p)
		_part(prism, roof, Vector3(0, base_h + h * 0.225, 0))
	else:
		var pyr := _cached("pyr:%.2f:%.2f" % [w, h], func() -> Mesh:
			var c := CylinderMesh.new()
			c.top_radius = 0.0
			c.bottom_radius = maxf(w, depth) * 0.78
			c.height = h * 0.5
			c.radial_segments = 4
			c.rings = 1
			return c)
		_part(pyr, roof, Vector3(0, base_h + h * 0.25, 0), PI * 0.25)
	# banner pole with team flag
	_part(_cyl(0.05, 0.05, h * 0.6), WOOD, Vector3(w * 0.38, base_h + h * 0.3, depth * 0.38))
	_part(_box(Vector3(0.04, h * 0.18, h * 0.28)), tc, Vector3(w * 0.38, base_h + h * 0.48, depth * 0.38 - h * 0.14))


func _build_mine(d: Dictionary) -> void:
	var fp: Array = d.get("footprint", [8, 8])
	var w := float(fp[0]) * Grid.CELL
	var h := height
	var rock := Color(0.42, 0.38, 0.34)
	var mound := _cached("mound:%.2f:%.2f" % [w, h], func() -> Mesh:
		var s := SphereMesh.new()
		s.radius = w * 0.5
		s.height = h * 2.0
		s.radial_segments = 10
		s.rings = 6
		return s)
	_part(mound, rock, Vector3(0, 0.0, 0))
	_part(_box(Vector3(w * 0.36, h * 0.55, 0.5)), DARK, Vector3(0, h * 0.3, -w * 0.38))
	_part(_box(Vector3(0.14, h * 0.62, 0.16)), WOOD, Vector3(-w * 0.2, h * 0.31, -w * 0.42))
	_part(_box(Vector3(0.14, h * 0.62, 0.16)), WOOD, Vector3(w * 0.2, h * 0.31, -w * 0.42))
	_part(_box(Vector3(w * 0.48, 0.14, 0.18)), WOOD, Vector3(0, h * 0.62, -w * 0.42))
	# gold nuggets sit on the mound surface (ellipsoid radii w/2, h, w/2)
	for k in 8:
		var a := -PI * 0.5 + (k - 3.5) * 0.42
		var elev := 0.35 + 0.12 * float(k % 3)
		var dir := Vector3(cos(a) * cos(elev), sin(elev), sin(a) * cos(elev))
		_part(_sphere(0.2 + 0.06 * float(k % 2)), GOLD, dir * Vector3(w * 0.5, h, w * 0.5) * 0.98)


# --- mesh / material helpers ---------------------------------------------------------------

func _part(mesh: Mesh, col: Color, p: Vector3, yaw: float = 0.0) -> void:
	_parts.append({"mesh": mesh, "xform": ProcMesh.at(p, Vector3.ONE, yaw), "color": col})


## Legacy vertex-colour material (kept for projectile placeholders).
static func placeholder_material() -> ShaderMaterial:
	if _vc_material == null:
		_vc_material = ShaderMaterial.new()
		_vc_material.shader = PLACEHOLDER_SHADER
	return _vc_material


## Placeholder units use the painterly unit shader with sRGB vertex colours, so they get the
## same lighting, rim and latched flash as GLB units.
static func placeholder_unit_material() -> ShaderMaterial:
	if _placeholder_unit_mat == null:
		_placeholder_unit_mat = ShaderMaterial.new()
		_placeholder_unit_mat.shader = UNIT_SHADER
		_placeholder_unit_mat.set_shader_parameter("use_vertex_color", true)
		_placeholder_unit_mat.set_shader_parameter("gradient_height", 1.6)
		AssetLibrary.shader_materials.append(_placeholder_unit_mat)
	return _placeholder_unit_mat


static func _cached(key: String, ctor: Callable) -> Mesh:
	if not _meshes.has(key):
		_meshes[key] = ctor.call()
	return _meshes[key]


static func _capsule(r: float, h: float) -> Mesh:
	return _cached("cap:%.3f:%.3f" % [r, h], func() -> Mesh:
		var c := CapsuleMesh.new()
		c.radius = r
		c.height = maxf(h, r * 2.0)
		c.radial_segments = 12
		c.rings = 4
		return c)


static func _sphere(r: float) -> Mesh:
	return _cached("sph:%.3f" % r, func() -> Mesh: return ProcMesh.sphere(r, 10, 6))


static func _cyl(top: float, bottom: float, h: float) -> Mesh:
	return _cached("cyl:%.3f:%.3f:%.3f" % [top, bottom, h], func() -> Mesh:
		return ProcMesh.cylinder(top, bottom, h, 10))


static func _box(size: Vector3) -> Mesh:
	return _cached("box:%s" % size, func() -> Mesh:
		var b := BoxMesh.new()
		b.size = size
		return b)
