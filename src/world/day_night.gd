class_name DayNight
extends Node3D
## Day/night cycle driven by simulation time (so it matches gameplay-relevant `is_day()`),
## rendered smoothly in _process using the physics interpolation fraction. Visual only.
## Lighting and grade follow the Greenvale keys (TimeOfDay, juice world doc §5.1, art bible §1.5):
## a warm sun at 50-55 deg from screen lower-left by day, a cool moon (#8EA6FF) at night with the
## shadow hand-over while both are faint, coloured ambient at ~2:1 key:ambient, Reinhard tonemap,
## per-hour saturation / contrast plus a procedural grading LUT (ColorGrade), depth fog 32-90 m in
## the key's fog colour, glow above HDR 1.0 (only VFX and lit windows bloom), drifting cloud
## shadows, the night unit fill and window / lamp glow through the shared material uniforms
## (RenderAtmos, advanced every frame with real delta).

const DAY_LENGTH := 480.0      ## sim seconds for a full 24 h cycle
const START_HOUR := 8.0
const DAWN := 6.0
const DUSK := 18.0
const SUN_FROM := Vector3(-0.72, 0.0, 0.69)    ## horizontal direction the sun shines from (screen lower-left)
const MOON_FROM := Vector3(0.55, 0.0, 0.83)
const MOON_ELEVATION := 58.0

## Optional override for screenshots/debug; < 0 means follow sim time.
@export var fixed_hour: float = -1.0

var world: World
var sun: DirectionalLight3D
var moon: DirectionalLight3D
var env: WorldEnvironment
var state: Dictionary = {}     ## last TimeOfDay sample applied
var _lut_key := Vector2(-1.0, -1.0)


func setup(w: World) -> void:
	world = w
	sun = get_node_or_null("Sun") as DirectionalLight3D
	env = get_node_or_null("Env") as WorldEnvironment
	if sun == null:
		sun = DirectionalLight3D.new()
		sun.name = "Sun"
		add_child(sun)
	moon = get_node_or_null("Moon") as DirectionalLight3D
	if moon == null:
		moon = DirectionalLight3D.new()
		moon.name = "Moon"
		add_child(moon)
	for l: DirectionalLight3D in [sun, moon]:
		l.shadow_enabled = true
		l.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
		l.directional_shadow_max_distance = RenderProfile.SHADOW_DISTANCE
		l.directional_shadow_split_1 = 0.35
		l.directional_shadow_blend_splits = true
		l.shadow_blur = 1.6
		l.shadow_bias = 0.04
		l.shadow_normal_bias = 1.2
		l.light_specular = 0.25
		l.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	moon.light_color = TimeOfDay.MOON
	if env == null:
		env = WorldEnvironment.new()
		env.name = "Env"
		env.environment = make_environment()
		add_child(env)
	RenderProfile.apply_rendering()
	_apply(current_hour())


## Hour of day from sim time (deterministic; gameplay may query is_day()).
static func hour_at(sim_time: float) -> float:
	return fposmod(START_HOUR + sim_time / DAY_LENGTH * 24.0, 24.0)


func current_hour() -> float:
	if fixed_hour >= 0.0:
		return fixed_hour
	if world == null:
		return START_HOUR
	return hour_at(world.time + world.interpolation_fraction() * World.DT)


func is_day() -> bool:
	var h := hour_at(world.time) if world != null else START_HOUR
	return h >= DAWN and h < DUSK


func _process(delta: float) -> void:
	RenderAtmos.update(delta)
	if world != null:
		_apply(current_hour())


func _apply(hour: float) -> void:
	var s := TimeOfDay.sample(hour)
	state = s
	# sun: warm key from screen lower-left, drifting a little over the day
	var t := clampf((hour - DAWN) / (DUSK - DAWN), 0.0, 1.0)
	var sun_from := SUN_FROM.rotated(Vector3.UP, deg_to_rad(lerpf(18.0, -18.0, t)))
	_aim(sun, sun_from, TimeOfDay.sun_elevation(hour))
	_aim(moon, MOON_FROM, MOON_ELEVATION)
	sun.light_color = s["sun_color"]
	sun.light_energy = s["sun_energy"]
	sun.visible = s["sun_energy"] > 0.001
	moon.light_energy = s["moon_energy"]
	moon.visible = s["moon_energy"] > 0.001
	var sun_shadows: bool = s["sun_owns_shadows"]
	sun.shadow_enabled = sun_shadows
	moon.shadow_enabled = not sun_shadows
	var owner_light := sun if sun_shadows else moon
	owner_light.shadow_opacity = clampf(float(s["shadow_alpha"]) * 1.3, 0.0, 1.0)
	# shared material uniforms
	RenderAtmos.cloud_strength = s["cloud_strength"]
	RenderAtmos.unit_fill = Color(0.55, 0.64, 1.0, s["unit_fill"])
	RenderAtmos.glow_energy = lerpf(0.0, 2.4, smoothstep(0.15, 0.85, s["night"])) \
		+ 1.2 * float(s["golden"]) * (1.0 - float(s["daylight"]))
	if env != null and env.environment != null:
		var e := env.environment
		e.ambient_light_color = s["ambient"]
		e.ambient_light_energy = s["ambient_energy"]
		e.fog_light_color = s["fog_color"]
		e.background_color = (s["fog_color"] as Color).darkened(0.25)
		e.adjustment_saturation = s["saturation"]
		e.adjustment_contrast = s["contrast"]
		e.glow_intensity = s["glow"]
		# the keys are tuned for a readable night (never black): lift exposure as the night deepens
		e.tonemap_exposure = lerpf(1.08, 1.4, float(s["night"]))
		var key := Vector2(roundf(float(s["night"]) * 20.0), roundf(float(s["golden"]) * 10.0))
		if key != _lut_key:
			_lut_key = key
			e.adjustment_color_correction = ColorGrade.lut(s["night"], s["golden"])


## Points a directional light so it shines from `from` (horizontal) at `elevation_deg`.
static func _aim(l: DirectionalLight3D, from: Vector3, elevation_deg: float) -> void:
	var el := deg_to_rad(elevation_deg)
	var to_light := (from.normalized() * cos(el) + Vector3.UP * sin(el)).normalized()
	var fwd := -to_light
	var up := Vector3.UP if absf(fwd.y) < 0.99 else Vector3.FORWARD
	l.basis = Basis.looking_at(fwd, up)


static func make_environment() -> Environment:
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color("#9FB3C4")
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color("#9DB3D6")
	e.ambient_light_energy = 0.55
	e.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	e.tonemap_mode = Environment.TONE_MAPPER_REINHARDT
	e.tonemap_white = 1.5
	e.tonemap_exposure = 1.08
	e.fog_enabled = true
	e.fog_mode = Environment.FOG_MODE_DEPTH
	e.fog_depth_begin = RenderProfile.FOG_BEGIN
	e.fog_depth_end = RenderProfile.FOG_END
	e.fog_depth_curve = 1.6
	e.fog_density = 0.55
	e.fog_light_color = Color("#CFE3F0")
	e.fog_light_energy = 1.0
	e.fog_sun_scatter = 0.0
	e.fog_aerial_perspective = 0.0
	e.glow_enabled = true
	e.glow_hdr_threshold = 1.1
	e.glow_intensity = 0.7
	e.glow_bloom = 0.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	e.adjustment_enabled = true
	e.adjustment_brightness = 1.0
	e.adjustment_contrast = 1.02
	e.adjustment_saturation = 1.08
	return e
