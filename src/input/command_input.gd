class_name CommandInput
extends Node
## Turns right-clicks and command-card hotkeys into command dictionaries for World.issue().
## Right-click = smart command (move / attack / gather / follow resolved by the World;
## right-clicking a unit outside the selection targets it),
## shift = queue. Targeting mode (move/attack/patrol hotkeys) waits for a left-click; right-click
## or Esc cancels. Must sit after Selection in the tree so it sees input first.

signal targeting_changed(mode: String)

## Default command card layout (QWER / ASDF / ZXCV grid slots 0..11).
const CARD: Dictionary = {0: "move", 1: "stop", 2: "hold", 3: "attack_move", 4: "patrol"}
const LABELS: Dictionary = {"move": "Move", "stop": "Stop", "hold": "Hold",
	"attack_move": "Attack", "patrol": "Patrol"}
const TARGETED: Array[String] = ["move", "attack_move", "patrol"]
const MARKER_SHADER := preload("res://src/fx/ring.gdshader")

var world: World
var camera: RtsCamera
var selection: Selection
var player_id: int = 0
var targeting: String = ""


func setup(w: World, cam: RtsCamera, sel: Selection, pid: int) -> void:
	world = w
	camera = cam
	selection = sel
	player_id = pid


func _unhandled_input(event: InputEvent) -> void:
	if world == null:
		return
	if event is InputEventMouseButton and event.pressed:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			if targeting != "":
				_set_targeting("")
			else:
				_smart(mb.position, mb.shift_pressed)
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_LEFT and targeting != "":
			_issue_targeted(targeting, mb.position, mb.shift_pressed)
			if not mb.shift_pressed:
				_set_targeting("")
			get_viewport().set_input_as_handled()
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.is_action_pressed("cancel") and targeting != "":
			_set_targeting("")
			get_viewport().set_input_as_handled()
			return
		for slot: int in CARD:
			if event.is_action_pressed("card_%d" % slot):
				activate_card(slot, (event as InputEventKey).shift_pressed)
				get_viewport().set_input_as_handled()
				return


## Command card slot pressed (hotkey or HUD button): targeted commands enter targeting mode,
## the others are issued at once. Returns false when the slot is empty, nothing is selected or
## the game is paused (no orders while paused; the HUD stays clickable).
func activate_card(slot: int, shift: bool = false) -> bool:
	var cmd: String = CARD.get(slot, "")
	if cmd.is_empty() or selection.selected_ids().is_empty() or not can_process():
		return false
	if TARGETED.has(cmd):
		_set_targeting(cmd)
	else:
		_issue({"type": cmd, "queue": shift})
	return true


## Ground point chosen outside the 3D view (minimap): confirms targeting, else a smart move.
func command_ground(ground: Vector3, shift: bool = false) -> void:
	if selection.selected_ids().is_empty() or not can_process():
		return
	if targeting != "":
		_issue({"type": targeting, "pos": ground, "queue": shift})
		if not shift:
			_set_targeting("")
		return
	_issue({"type": "smart", "pos": ground, "queue": shift})


func cancel_targeting() -> void:
	if targeting != "":
		_set_targeting("")


func _set_targeting(mode: String) -> void:
	targeting = mode
	selection.enabled = mode == ""
	Input.set_default_cursor_shape(Input.CURSOR_CROSS if mode != "" else Input.CURSOR_ARROW)
	targeting_changed.emit(mode)


func _smart(screen_pos: Vector2, shift: bool) -> void:
	if selection.selected_ids().is_empty():
		return
	var target := selection.pick_unit(screen_pos)
	if target != null and not selection.selected.has(target):
		_issue({"type": "smart", "target": target.id, "queue": shift})
		_marker(target.pos, Color(1.0, 0.3, 0.2) if world.is_enemy(player_id, target.player_id) else Color(1, 0.9, 0.3))
		return
	var ground := camera.screen_to_ground(screen_pos)
	if ground == Vector3.INF:
		return
	_issue({"type": "smart", "pos": ground, "queue": shift})
	_marker(ground, Color(0.3, 1.0, 0.35))


func _issue_targeted(cmd: String, screen_pos: Vector2, shift: bool) -> void:
	var target := selection.pick_unit(screen_pos)
	if cmd == "attack_move" and target != null and world.is_enemy(player_id, target.player_id):
		_issue({"type": "attack", "target": target.id, "queue": shift})
		return
	var ground := camera.screen_to_ground(screen_pos)
	if ground == Vector3.INF:
		return
	_issue({"type": cmd, "pos": ground, "queue": shift})
	_marker(ground, Color(1.0, 0.3, 0.2) if cmd == "attack_move" else Color(0.3, 1.0, 0.35))


func _issue(cmd: Dictionary) -> void:
	cmd["player"] = player_id
	cmd["units"] = selection.selected_ids()
	if (cmd["units"] as Array).is_empty():
		return
	world.issue(cmd)
	var first := world.get_unit(cmd["units"][0])
	Audio.play_voice(first, "attack" if cmd["type"] in ["attack", "attack_move"] else "yes")


## Short-lived shrinking ring where an order was given (visual only).
func _marker(p: Vector3, col: Color) -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2(1.6, 1.6)
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = MARKER_SHADER
	mat.set_shader_parameter("inner", 0.7)
	mat.set_shader_parameter("tint", col)
	var mi := MeshInstance3D.new()
	mi.mesh = quad
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	world.add_child(mi)
	mi.global_position = Vector3(p.x, world.map.height_at(p.x, p.z) + 0.08, p.z)
	var tw := mi.create_tween()
	tw.tween_property(mi, "scale", Vector3(0.2, 1.0, 0.2), 0.45).from(Vector3.ONE)
	tw.tween_callback(mi.queue_free)
