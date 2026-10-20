class_name RtsCamera
extends Camera3D
## Classic RTS camera: fixed pitch looking down at a ground focus point, wheel zoom along the
## view ray, arrow-key / screen-edge / middle-drag panning, clamped to the map. Runs entirely
## in _process with real delta (visual only, not physics-interpolated). Juice (bible §3.14,
## UCA-F2, CAM-01/03/05/06), every term exact for any frame time, so it feels the same at 30,
## 60 or 144 Hz:
##   - pan (CAM-01): the velocity approaches the input velocity exponentially (crisp start,
##     k = `pan_accel_k`; firm stop, k = `pan_stop_k`, under 150 ms) and the focus integrates
##     that curve exactly over each frame; soft bounds stop the velocity into the map edge;
##   - edge pan (CAM-06): the cursor must rest at the edge `edge_dwell_ms` before it pans, then
##     accelerates like the keys; it releases when the window loses focus;
##   - zoom (CAM-03): a wheel notch moves 15 % of the way on its own frame, then the distance
##     eases exactly (k = `zoom_k`); the pitch couples to the distance (flatter close in,
##     steeper far out; `pitch_for(d)`), and zooming past an end stop kicks a small spring;
##   - CameraJuice (CAM-05) adds the whitelisted shake and directional kick through
##     h_offset / v_offset and a roll, so picking through `project_ray_*` sees the shaken view;
##   - the audio listener follows the ground focus (AUD-04).

@export var pitch_deg: float = -56.0
@export var yaw_deg: float = 0.0
@export var min_distance: float = 14.0
@export var max_distance: float = 46.0
@export var default_distance: float = 28.0
@export var base_pan_speed: float = 28.0    ## m/s at default distance
@export var zoom_smoothing: float = 10.0    ## legacy; the zoom eases at FeelConstants.zoom_k
@export var map_margin: float = 6.0

var world: World
var focus: Vector3 = Vector3.ZERO           ## ground point under the screen centre
var distance: float = 28.0
var target_distance: float = 28.0
var edge_pan_enabled: bool = true           ## per-camera switch (screenshots disable it)
var juice: CameraJuice
var pan_velocity := Vector2.ZERO            ## m/s on the ground plane (x, z)
var edge_dir := Vector2.ZERO                ## the edge the cursor is panning (CUR-02 arrow)

var _ground_y: float = 0.0
var _dragging: bool = false
var _mouse_seen: bool = false
var _last_alert: Vector3 = Vector3.INF
var _edge_time: float = 0.0
var _kick_x: float = 0.0                    ## zoom end-stop spring (metres along the view)
var _kick_v: float = 0.0


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	process_mode = Node.PROCESS_MODE_ALWAYS
	fov = 45.0
	near = 0.5
	far = 400.0
	juice = CameraJuice.new(self)
	CameraJuice.current = juice
	Events.alert_raised.connect(_on_alert)


func _exit_tree() -> void:
	if CameraJuice.current == juice:
		CameraJuice.current = null


func setup(w: World, start: Vector3) -> void:
	world = w
	distance = default_distance
	target_distance = default_distance
	pan_velocity = Vector2.ZERO
	jump_to(start)


func jump_to(p: Vector3) -> void:
	focus = Vector3(p.x, 0.0, p.z)
	if world != null:
		focus = world.map.clamp_to_map(focus, map_margin)
		_ground_y = world.map.height_at(focus.x, focus.z)
	_apply()


func _process(delta: float) -> void:
	if world == null:
		return
	var dt := clampf(delta, 0.0, 0.25)
	var fc := FeelConstants.c()
	var input := _key_pan() * Settings.key_pan_speed + _edge_pan(dt) * Settings.edge_pan_speed
	if input.length() > 1.0 and Settings.key_pan_speed <= 1.0 and Settings.edge_pan_speed <= 1.0:
		input = input.normalized()
	var speed := base_pan_speed * (distance / default_distance)
	var yaw := Basis(Vector3.UP, deg_to_rad(yaw_deg))
	var w3 := yaw * Vector3(input.x, 0.0, input.y) * speed
	var target_v := Vector2(w3.x, w3.z)
	var k := fc.pan_accel_k if target_v.length_squared() > 1e-6 else fc.pan_stop_k
	var step := pan_step(pan_velocity, target_v, k, dt)
	focus += Vector3(step.x, 0.0, step.y)
	pan_velocity = pan_velocity_after(pan_velocity, target_v, k, dt)
	if pan_velocity.length_squared() < 1e-4 and target_v == Vector2.ZERO:
		pan_velocity = Vector2.ZERO
	var clamped := world.map.clamp_to_map(focus, map_margin)
	if not is_equal_approx(clamped.x, focus.x):
		pan_velocity.x = 0.0
	if not is_equal_approx(clamped.z, focus.z):
		pan_velocity.y = 0.0
	focus = clamped
	distance = Juice.damp(distance, target_distance, fc.zoom_k, dt)
	var ks := Juice.spring(_kick_x, _kick_v, fc.zoom_kick_omega, 0.45, dt)
	_kick_x = ks.x
	_kick_v = ks.y
	_ground_y = Juice.damp(_ground_y, world.map.height_at(focus.x, focus.z), 5.0, dt)
	if juice != null:
		juice.precision = Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)
		juice.evaluate(FxClock.ui_now if FxClock.driven else Time.get_ticks_msec() / 1000.0, distance)
	_apply()


## Exact displacement over `dt` of a velocity approaching `target` as v(t) = target +
## (v0 − target)·e^(−k t): identical whatever the frame split.
static func pan_step(v0: Vector2, target: Vector2, k: float, dt: float) -> Vector2:
	if k <= 0.0:
		return v0 * dt
	return target * dt + (v0 - target) * (1.0 - exp(-k * dt)) / k


static func pan_velocity_after(v0: Vector2, target: Vector2, k: float, dt: float) -> Vector2:
	return target + (v0 - target) * exp(-k * dt)


## Pitch coupled to the zoom distance (CAM-03): flatter close in, steeper far out; exactly
## `pitch_deg` at the default distance.
func pitch_for(d: float) -> float:
	var fc := FeelConstants.c()
	var x := d - default_distance
	return pitch_deg + fc.pitch_slope * x + fc.pitch_curve * x * x * signf(-x)


func _apply() -> void:
	var pitch := deg_to_rad(-pitch_for(distance))
	var d := distance + _kick_x
	var offset := Basis(Vector3.UP, deg_to_rad(yaw_deg)) * Vector3(0.0, sin(pitch), cos(pitch)) * d
	var target := Vector3(focus.x, _ground_y, focus.z)
	look_at_from_position(target + offset, target, Vector3.UP)
	if juice != null:
		h_offset = juice.shake_offset.x + juice.kick_offset.x
		v_offset = juice.shake_offset.y + juice.kick_offset.y
		if juice.shake_roll != 0.0:
			rotate_object_local(Vector3.BACK, juice.shake_roll)
	Audio.follow_camera(self, target, distance)


func _key_pan() -> Vector2:
	return Vector2(
		Input.get_action_strength("cam_right") - Input.get_action_strength("cam_left"),
		Input.get_action_strength("cam_down") - Input.get_action_strength("cam_up"))


## Edge pan with a short dwell (CAM-06): the cursor must rest on the edge `edge_dwell_ms`.
func _edge_pan(dt: float) -> Vector2:
	edge_dir = Vector2.ZERO
	if not (edge_pan_enabled and Settings.edge_pan_enabled and _mouse_seen) or _dragging:
		_edge_time = 0.0
		return Vector2.ZERO
	if not get_window().has_focus():
		_edge_time = 0.0
		return Vector2.ZERO
	var vp := get_viewport()
	var m := vp.get_mouse_position()
	var size := vp.get_visible_rect().size
	if m.x < 0 or m.y < 0 or m.x > size.x or m.y > size.y:
		_edge_time = 0.0
		return Vector2.ZERO
	var e := float(Settings.edge_pan_margin_px)
	var v := Vector2.ZERO
	if m.x <= e:
		v.x = -1.0
	elif m.x >= size.x - e - 1.0:
		v.x = 1.0
	if m.y <= e:
		v.y = -1.0
	elif m.y >= size.y - e - 1.0:
		v.y = 1.0
	if v == Vector2.ZERO:
		_edge_time = 0.0
		return Vector2.ZERO
	_edge_time += dt
	edge_dir = v
	if _edge_time < FeelConstants.c().edge_dwell_ms / 1000.0:
		return Vector2.ZERO
	return v


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse_seen = true
		if _dragging:
			_drag_by((event as InputEventMouseMotion).relative)
		return
	if event.is_action_pressed("cam_zoom_in"):
		zoom_notch(-Settings.zoom_step)
	elif event.is_action_pressed("cam_zoom_out"):
		zoom_notch(Settings.zoom_step)
	elif event.is_action_pressed("cam_drag"):
		_dragging = true
		pan_velocity = Vector2.ZERO
	elif event.is_action_released("cam_drag"):
		_dragging = false
	elif event.is_action_pressed("jump_alert") and _last_alert != Vector3.INF:
		jump_to(_last_alert)
	else:
		return
	get_viewport().set_input_as_handled()


## One wheel notch (CAM-03): 15 % of the step lands on this frame, the rest eases in; pushing
## past an end stop kicks the distance spring instead.
func zoom_notch(step: float) -> void:
	var want := target_distance + step
	var clamped := clampf(want, min_distance, max_distance)
	if not is_equal_approx(want, clamped) and is_equal_approx(target_distance, clamped):
		_kick_v += Juice.kick_for_peak(0.025 * distance, FeelConstants.c().zoom_kick_omega, 0.45) * signf(step)
		return
	target_distance = clamped
	distance = lerpf(distance, target_distance, 0.15)
	_apply()


## Grab-the-ground drag: the map moves with the cursor.
func _drag_by(rel: Vector2) -> void:
	var px_to_m := 2.0 * distance * tan(deg_to_rad(fov) * 0.5) / get_viewport().get_visible_rect().size.y
	var yaw := Basis(Vector3.UP, deg_to_rad(yaw_deg))
	var ground_scale := 1.0 / sin(deg_to_rad(-pitch_for(distance)))
	focus -= yaw * Vector3(rel.x * px_to_m, 0.0, rel.y * px_to_m * ground_scale) * Settings.drag_pan_speed


func _on_alert(player_id: int, pos: Vector3) -> void:
	if world != null and player_id == world.local_player_id:
		_last_alert = pos


## World point on the terrain under a screen position (Vector3.INF when off-map). The rays come
## from the rendered (shaken) transform, so clicks land on what is on screen.
func screen_to_ground(screen_pos: Vector2) -> Vector3:
	if world == null:
		return Vector3.INF
	return world.map.raycast(project_ray_origin(screen_pos), project_ray_normal(screen_pos))
