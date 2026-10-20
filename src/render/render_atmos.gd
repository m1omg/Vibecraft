class_name RenderAtmos
extends RefCounted
## Render clock and shared per-frame material uniforms (visual only; nothing here touches the sim).
## - `now()`: the fx clock (FxClock.fx_now, wrapped hourly) used for latched effects: a hit flash
##   stores its start time once and the shader evaluates the curve, so it is exact at any refresh
##   rate (juice bible R25). The shader-side copy (`fx_time`) is pushed once per frame by `update()`.
## - cloud shadows drift with the wind on the same real clock (bible §1.5: about 1 m/s).
## DayNight calls `update()` every frame; materials register through AssetLibrary.shader_materials
## or `register()` (terrain, water, trees).

const WRAP := 3600.0
const CLOUD_WIND := Vector2(0.85, 0.45)    ## m/s

static var cloud_offset := Vector2.ZERO
static var cloud_strength := 0.3
static var glow_energy := 1.0
static var unit_fill := Color(0.55, 0.62, 1.0, 0.0)
static var _extra: Array[ShaderMaterial] = []


## The fx clock as the shaders see it: FxClock (game-scaled, frozen on pause, driven once per
## frame by Vfx) once a driver runs, else real time (tools and scenes without a World).
static func now() -> float:
	if FxClock.driven:
		return FxClock.shader_time()
	return fmod(Time.get_ticks_usec() / 1000000.0, WRAP)


static func register(m: ShaderMaterial) -> void:
	if m != null and not _extra.has(m):
		_extra.append(m)


static func unregister(m: ShaderMaterial) -> void:
	_extra.erase(m)


## Advances the drifting clouds by real `delta` and pushes the shared uniforms.
static func update(delta: float) -> void:
	cloud_offset += CLOUD_WIND * delta
	if cloud_offset.length_squared() > 1.0e8:
		cloud_offset = Vector2.ZERO
	var t := now()
	for list: Array in [AssetLibrary.shader_materials, _extra]:
		for m: ShaderMaterial in list:
			if not is_instance_valid(m):
				continue
			m.set_shader_parameter(&"fx_time", t)
			m.set_shader_parameter(&"cloud_offset", cloud_offset)
			m.set_shader_parameter(&"cloud_strength", cloud_strength)
			m.set_shader_parameter(&"glow_energy", glow_energy)
			m.set_shader_parameter(&"unit_fill", unit_fill)
