class_name RtsCamera
extends Camera3D
## WC3-style RTS camera: fixed pitch looking down at a ground focus point, wheel zoom along the
## view ray, arrow-key / screen-edge / middle-drag panning, clamped to the map. Runs entirely
## in _process with delta (visual only, not physics-interpolated).

@export var pitch_deg: float = -56.0
@export var yaw_deg: float = 0.0
@export var min_distance: float = 14.0
@export var max_distance: float = 46.0
@export var default_distance: float = 28.0
@export var base_pan_speed: float = 28.0    ## m/s at default distance
@export var zoom_smoothing: float = 10.0
@export var map_margin: float = 6.0

var world: World
var focus: Vector3 = Vector3.ZERO           ## ground point under the screen centre
var distance: float = 28.0
var target_distance: float = 28.0
var edge_pan_enabled: bool = true           ## per-camera switch (screenshots disable it)

var _ground_y: float = 0.0
var _dragging: bool = false
var _mouse_seen: bool = false
var _last_alert: Vector3 = Vector3.INF


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	fov = 45.0
	near = 0.5
	far = 400.0
	Events.alert_raised.connect(_on_alert)


func setup(w: World, start: Vector3) -> void:
	world = w
	distance = default_distance
	target_distance = default_distance
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
	var pan := _key_pan() * Settings.key_pan_speed + _edge_pan() * Settings.edge_pan_speed
	if pan != Vector2.ZERO:
		var speed := base_pan_speed * (distance / default_distance)
		var yaw := Basis(Vector3.UP, deg_to_rad(yaw_deg))
		focus += yaw * Vector3(pan.x, 0.0, pan.y) * speed * delta
	focus = world.map.clamp_to_map(focus, map_margin)
	distance = lerpf(distance, target_distance, 1.0 - exp(-zoom_smoothing * delta))
	_ground_y = lerpf(_ground_y, world.map.height_at(focus.x, focus.z), 1.0 - exp(-5.0 * delta))
	_apply()


func _apply() -> void:
	var pitch := deg_to_rad(-pitch_deg)
	var offset := Basis(Vector3.UP, deg_to_rad(yaw_deg)) * Vector3(0.0, sin(pitch), cos(pitch)) * distance
	var target := Vector3(focus.x, _ground_y, focus.z)
	look_at_from_position(target + offset, target, Vector3.UP)


func _key_pan() -> Vector2:
	return Vector2(
		Input.get_action_strength("cam_right") - Input.get_action_strength("cam_left"),
		Input.get_action_strength("cam_down") - Input.get_action_strength("cam_up"))


func _edge_pan() -> Vector2:
	if not (edge_pan_enabled and Settings.edge_pan_enabled and _mouse_seen) or _dragging:
		return Vector2.ZERO
	if not get_window().has_focus():
		return Vector2.ZERO
	var vp := get_viewport()
	var m := vp.get_mouse_position()
	var size := vp.get_visible_rect().size
	if m.x < 0 or m.y < 0 or m.x > size.x or m.y > size.y:
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
	return v


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse_seen = true
		if _dragging:
			_drag_by((event as InputEventMouseMotion).relative)
		return
	if event.is_action_pressed("cam_zoom_in"):
		target_distance = clampf(target_distance - Settings.zoom_step, min_distance, max_distance)
	elif event.is_action_pressed("cam_zoom_out"):
		target_distance = clampf(target_distance + Settings.zoom_step, min_distance, max_distance)
	elif event.is_action_pressed("cam_drag"):
		_dragging = true
	elif event.is_action_released("cam_drag"):
		_dragging = false
	elif event.is_action_pressed("jump_alert") and _last_alert != Vector3.INF:
		jump_to(_last_alert)
	else:
		return
	get_viewport().set_input_as_handled()


## Grab-the-ground drag: the map moves with the cursor.
func _drag_by(rel: Vector2) -> void:
	var px_to_m := 2.0 * distance * tan(deg_to_rad(fov) * 0.5) / get_viewport().get_visible_rect().size.y
	var yaw := Basis(Vector3.UP, deg_to_rad(yaw_deg))
	var ground_scale := 1.0 / sin(deg_to_rad(-pitch_deg))
	focus -= yaw * Vector3(rel.x * px_to_m, 0.0, rel.y * px_to_m * ground_scale) * Settings.drag_pan_speed


func _on_alert(player_id: int, pos: Vector3) -> void:
	if world != null and player_id == world.local_player_id:
		_last_alert = pos


## World point on the terrain under a screen position (Vector3.INF when off-map).
func screen_to_ground(screen_pos: Vector2) -> Vector3:
	if world == null:
		return Vector3.INF
	return world.map.raycast(project_ray_origin(screen_pos), project_ray_normal(screen_pos))
