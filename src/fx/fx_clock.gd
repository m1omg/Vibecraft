class_name FxClock
extends RefCounted
## The juice clocks (juice bible R1). Visual only: the simulation never reads them.
## - `fx_now`: game-scaled seconds. Freezes while the World is paused and follows game speed, so
##   every effect that shows a sim event (flashes, knockback, impacts, deaths) holds on pause.
## - `ui_now`: unscaled seconds that always run (order marks, selection rings, camera, menus).
## Both are advanced exactly once per process frame by the driver (`Vfx`, process_priority -100,
## process ALWAYS) through `drive()`, or by tests through `advance()` with scripted deltas
## (`manual = true` stops the driver). Every juice curve is a closed-form function of
## (now - t0), so the picture at a given time is the same at 30, 60, 144 or 240 Hz.
## The shader copy is `fx_time` = `shader_time()` (wrapped hourly; pushed by RenderAtmos).

const WRAP := 3600.0
const MAX_DT := 0.25                 ## a hitch never jumps effects further than this

static var fx_now: float = 0.0
static var ui_now: float = 0.0
static var fx_dt: float = 0.0
static var ui_dt: float = 0.0
static var frame: int = 0
static var driven: bool = false      ## true once a driver or a test advanced the clocks
static var manual: bool = false      ## tests: only advance() moves the clocks
static var _driver_frame: int = -1


## Advances both clocks. `dt` is the (game-scaled) process delta; `fx_running` false while the
## World is paused. `time_scale` un-scales the UI clock.
static func advance(dt: float, fx_running: bool = true, time_scale: float = 1.0) -> void:
	dt = clampf(dt, 0.0, MAX_DT)
	ui_dt = dt / maxf(time_scale, 0.0001)
	fx_dt = dt if fx_running else 0.0
	ui_now += ui_dt
	fx_now += fx_dt
	frame += 1
	driven = true


## Driver entry point: advances once per engine process frame however many drivers call it.
static func drive(dt: float, fx_running: bool) -> void:
	if manual:
		return
	var f := Engine.get_process_frames()
	if f == _driver_frame:
		return
	_driver_frame = f
	advance(dt, fx_running, Engine.time_scale)


## fx time as the shaders see it (`fx_time`, wrapped hourly like RenderAtmos.now()).
static func shader_time() -> float:
	return fmod(fx_now, WRAP)


## Back to zero (tests). `keep_driven` keeps RenderAtmos on this clock.
static func reset(start: float = 10.0) -> void:
	fx_now = start
	ui_now = start
	fx_dt = 0.0
	ui_dt = 0.0
	frame = 0
	_driver_frame = -1
