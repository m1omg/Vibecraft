class_name RenderProfile
extends RefCounted
## Camera and renderer defaults for the RTS view (research README §1, art bible §1.2). Visual only.
## The camera rig keeps its own behaviour (src/input/rts_camera.gd); these are the numbers it is
## configured with by main.gd.

const PITCH_DEG := -56.0             ## the reference RTS camera angle of attack (research README §1)
const FOV_DEG := 55.0                ## vertical, KEEP_HEIGHT
const DEFAULT_DISTANCE := 25.8       ## 1650 gu
const MIN_DISTANCE := 18.75          ## 1200 gu
const MAX_DISTANCE := 35.2           ## 2250 gu
const NEAR := 0.3
const FAR := 120.0
const FOG_BEGIN := 32.0              ## depth fog, art bible §1.2
const FOG_END := 90.0
const SHADOW_DISTANCE := 70.0


## Applies the camera constants to an RtsCamera (or any Camera3D) before its setup().
static func apply_camera(cam: Camera3D) -> void:
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.fov = FOV_DEG
	cam.near = NEAR
	cam.far = FAR
	for p: Array in [["pitch_deg", PITCH_DEG], ["default_distance", DEFAULT_DISTANCE],
			["min_distance", MIN_DISTANCE], ["max_distance", MAX_DISTANCE],
			["distance", DEFAULT_DISTANCE], ["target_distance", DEFAULT_DISTANCE]]:
		if p[0] in cam:
			cam.set(p[0], p[1])


## Renderer-wide quality switches that must hold on Forward+ and Compatibility.
static func apply_rendering() -> void:
	RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW)
	RenderingServer.directional_shadow_atlas_set_size(4096, true)
