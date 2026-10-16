class_name DayNight
extends Node3D
## Day/night cycle driven by simulation time (so it matches gameplay-relevant `is_day()`),
## rendered smoothly in _process using the physics interpolation fraction. Visual only.

const DAY_LENGTH := 480.0      ## sim seconds for a full 24 h cycle
const START_HOUR := 8.0
const DAWN := 6.0
const DUSK := 18.0

## Optional override for screenshots/debug; < 0 means follow sim time.
@export var fixed_hour: float = -1.0

var world: World
var sun: DirectionalLight3D
var env: WorldEnvironment

const DAY_SUN := Color(1.0, 0.95, 0.85)
const DUSK_SUN := Color(1.0, 0.62, 0.38)
const NIGHT_SUN := Color(0.45, 0.55, 0.85)
const DAY_AMBIENT := Color(0.62, 0.66, 0.72)
const NIGHT_AMBIENT := Color(0.22, 0.27, 0.42)


func setup(w: World) -> void:
	world = w
	sun = get_node_or_null("Sun") as DirectionalLight3D
	env = get_node_or_null("Env") as WorldEnvironment
	if sun == null:
		sun = DirectionalLight3D.new()
		sun.name = "Sun"
		add_child(sun)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	sun.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	if env == null:
		env = WorldEnvironment.new()
		env.name = "Env"
		env.environment = _make_environment()
		add_child(env)
	_apply(current_hour())


## Hour of day from sim time (deterministic; gameplay may query is_day()).
static func hour_at(sim_time: float) -> float:
	return fposmod(START_HOUR + sim_time / DAY_LENGTH * 24.0, 24.0)


func current_hour() -> float:
	if fixed_hour >= 0.0:
		return fixed_hour
	if world == null:
		return START_HOUR
	return hour_at(world.time + Engine.get_physics_interpolation_fraction() * World.DT)


func is_day() -> bool:
	var h := hour_at(world.time) if world != null else START_HOUR
	return h >= DAWN and h < DUSK


func _process(_delta: float) -> void:
	if world != null:
		_apply(current_hour())


func _apply(hour: float) -> void:
	# daylight 0..1 with soft dawn/dusk transitions
	var day := smoothstep(DAWN - 0.75, DAWN + 0.75, hour) * (1.0 - smoothstep(DUSK - 0.75, DUSK + 0.75, hour))
	var dusk_amt := maxf(1.0 - absf(hour - DAWN) / 1.5, 1.0 - absf(hour - DUSK) / 1.5)
	dusk_amt = clampf(dusk_amt, 0.0, 1.0)
	var sun_col := NIGHT_SUN.lerp(DAY_SUN, day).lerp(DUSK_SUN, dusk_amt * 0.6)
	sun.light_color = sun_col
	sun.light_energy = lerpf(0.35, 1.1, day)
	# sun sweeps east -> west during the day; the night "moon" light stays high and cool
	var t := clampf((hour - DAWN) / (DUSK - DAWN), 0.0, 1.0)
	var elevation := lerpf(55.0, 70.0, 1.0 - day) if day < 0.5 else 25.0 + 40.0 * sin(t * PI)
	var azimuth := lerpf(-120.0, 120.0, t) - 30.0
	sun.rotation = Vector3(deg_to_rad(-elevation), deg_to_rad(azimuth), 0.0)
	if env != null and env.environment != null:
		env.environment.ambient_light_color = NIGHT_AMBIENT.lerp(DAY_AMBIENT, day)
		env.environment.ambient_light_energy = lerpf(0.55, 0.75, day)


static func _make_environment() -> Environment:
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.05, 0.06, 0.08)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = DAY_AMBIENT
	e.ambient_light_energy = 0.75
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.tonemap_exposure = 1.0
	return e
