class_name Minimap
extends Control
## Placeholder minimap: map backdrop, unit dots in player colours and the camera focus box.
## Left click/drag jumps the camera; right click issues a smart command at that ground point.
## With an order armed (A / M / P), a left click issues that order at the map point instead
## (Shift queues it and keeps the order armed) and a right click cancels it (rules §18.1).
## The terrain image and fog layer arrive with the fog-of-war milestone. Visual only.

const BACKDROP := Color(0.13, 0.19, 0.12)
const BORDER := Color(0.55, 0.50, 0.38)
const VIEW_BOX := Color(1, 1, 1, 0.8)

var world: World
var camera: RtsCamera
var commands: CommandInput
var _dragging: bool = false


func setup(w: World, cam: RtsCamera, cmd: CommandInput) -> void:
	world = w
	camera = cam
	commands = cmd
	mouse_filter = Control.MOUSE_FILTER_STOP


func _process(_delta: float) -> void:
	if world != null and is_visible_in_tree():
		queue_redraw()


func _scale() -> Vector2:
	var s := world.map.size_world()
	return Vector2(size.x / s.x, size.y / s.y)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BACKDROP)
	if world == null:
		return
	var k := _scale()
	for u in world.unit_list:
		if not u.alive:
			continue
		var r := 1.5
		if u.footprint.size != Vector2i.ZERO:
			r = maxf(u.footprint.size.x * Grid.CELL * k.x * 0.5, 2.5)
		var c := Color(0.95, 0.85, 0.3) if u.is_resource else world.player_color(u.player_id)
		var p := Vector2(u.pos.x, u.pos.z) * k
		draw_rect(Rect2(p - Vector2(r, r), Vector2(r, r) * 2.0), c)
	if camera != null:
		var half := Vector2(camera.distance * 0.75, camera.distance * 0.45) * k
		var f := Vector2(camera.focus.x, camera.focus.z) * k
		draw_rect(Rect2(f - half, half * 2.0), VIEW_BOX, false, 1.0)
	draw_rect(Rect2(Vector2.ZERO, size), BORDER, false, 2.0)


func _to_world(local: Vector2) -> Vector3:
	var k := _scale()
	var p := Vector3(clampf(local.x, 0.0, size.x) / k.x, 0.0, clampf(local.y, 0.0, size.y) / k.y)
	p.y = world.map.height_at(p.x, p.z)
	return p


func _gui_input(event: InputEvent) -> void:
	if world == null:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed and commands != null and commands.targeting != "":
				# an armed order (A / M / P) lands on that map point; Shift queues it and keeps
				# the targeting armed (rules §18.1). No camera jump, no drag.
				commands.command_ground(_to_world(mb.position), mb.shift_pressed)
				_dragging = false
				accept_event()
				return
			_dragging = mb.pressed
			if mb.pressed and camera != null:
				camera.jump_to(_to_world(mb.position))
		elif mb.button_index == MOUSE_BUTTON_RIGHT and mb.pressed and commands != null:
			if commands.targeting != "":
				commands.cancel_targeting()     # as in the 3D view: right-click cancels targeting
			else:
				commands.command_ground(_to_world(mb.position), mb.shift_pressed)
		accept_event()
	elif event is InputEventMouseMotion and _dragging and camera != null:
		camera.jump_to(_to_world((event as InputEventMouseMotion).position))
		accept_event()
