extends "res://tests/test_case.gd"
## Drives the real main scene with synthetic input events (headless): box select, right-click
## move, control groups, ctrl-click select-same-type and targeting via the command card.

var main: Node
var world: World
var camera: RtsCamera
var sel: Selection


func before_each() -> void:
	Settings.edge_pan_enabled = false
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	world = main.world
	world.auto_tick = false
	camera = main.camera
	sel = main.selection


func after_each() -> void:
	Settings.edge_pan_enabled = true
	tree.paused = false
	cleanup()


func _mouse(button: MouseButton, pos: Vector2, pressed: bool, mods: Dictionary = {}) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	ev.position = pos
	ev.global_position = pos
	ev.pressed = pressed
	ev.double_click = mods.get("double", false)
	ev.shift_pressed = mods.get("shift", false)
	ev.ctrl_pressed = mods.get("ctrl", false)
	tree.root.push_input(ev, true)


func _motion(pos: Vector2, rel: Vector2) -> void:
	var ev := InputEventMouseMotion.new()
	ev.position = pos
	ev.global_position = pos
	ev.relative = rel
	tree.root.push_input(ev, true)


func _key(key: Key, mods: Dictionary = {}) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.keycode = key
		ev.pressed = pressed
		ev.ctrl_pressed = mods.get("ctrl", false)
		ev.shift_pressed = mods.get("shift", false)
		tree.root.push_input(ev, true)


func _army() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.player_id == 0 and u.is_mobile() and not u.is_worker:
			out.append(u)
	return out


func _screen(u: Unit) -> Vector2:
	return camera.unproject_position(u.pos + Vector3(0, 0.8, 0))


func _box_around(units: Array) -> Rect2:
	var r := Rect2(_screen(units[0]), Vector2.ZERO)
	for u: Unit in units:
		r = r.expand(_screen(u))
	return r.grow(14.0)


func test_box_select_then_right_click_move() -> void:
	var army := _army()
	assert_eq(army.size(), 5, "starting army")
	var box := _box_around(army)
	_mouse(MOUSE_BUTTON_LEFT, box.position, true)
	_motion(box.position + Vector2(20, 20), Vector2(20, 20))
	_motion(box.end, box.end - box.position)
	_mouse(MOUSE_BUTTON_LEFT, box.end, false)
	for u in army:
		assert_true(sel.selected.has(u), "%s selected by box" % u.name)
	for u in sel.selected:
		assert_eq(u.player_id, 0, "only own units")
		assert_false(u.is_building, "buildings excluded when units are in the box")
	var goal := world.map.start_locations[0] + Vector3(12, 0, -14)
	goal.y = world.map.height_at(goal.x, goal.z)
	_mouse(MOUSE_BUTTON_RIGHT, camera.unproject_position(goal), true)
	_mouse(MOUSE_BUTTON_RIGHT, camera.unproject_position(goal), false)
	run_until_idle(world, army, 600)
	var centre := Vector3.ZERO
	for u in army:
		centre += u.pos
	centre /= army.size()
	assert_lt(Grid.flat_dist(centre, goal), 3.0, "army moved to the right-clicked point")


func test_click_ctrl_click_and_control_groups() -> void:
	var army := _army()
	var soldier: Unit = null
	for u in army:
		if u.def_id == "dummy_soldier":
			soldier = u
			break
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), true)
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), false)
	assert_eq(sel.selected.size(), 1, "single click selects one unit")
	assert_true(sel.selected.has(soldier), "the clicked unit")
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), true, {"ctrl": true})
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), false, {"ctrl": true})
	var soldiers := army.filter(func(u: Unit) -> bool: return u.def_id == "dummy_soldier")
	assert_eq(sel.selected.size(), soldiers.size(), "ctrl+click selects all soldiers on screen")
	_key(KEY_1, {"ctrl": true})
	sel.clear()
	assert_eq(sel.selected.size(), 0)
	_key(KEY_1)
	assert_eq(sel.selected.size(), soldiers.size(), "group 1 recalled")
	camera.jump_to(Vector3(96, 0, 96))
	_key(KEY_1)
	var c := Vector3.ZERO
	for u: Unit in soldiers:
		c += u.pos
	c /= soldiers.size()
	assert_lt(Grid.flat_dist(camera.focus, c), 1.0, "double-tap centres the camera on the group")


func test_patrol_hotkey_and_cancel() -> void:
	var army := _army()
	sel.select_units(army)
	var commands: CommandInput = main.commands
	_key(KEY_A)
	assert_eq(commands.targeting, "patrol", "A enters patrol targeting")
	_key(KEY_ESCAPE)
	assert_eq(commands.targeting, "", "Esc cancels targeting")
	_key(KEY_A)
	var p := world.map.start_locations[0] + Vector3(8, 0, -12)
	p.y = world.map.height_at(p.x, p.z)
	_mouse(MOUSE_BUTTON_LEFT, camera.unproject_position(p), true)
	_mouse(MOUSE_BUTTON_LEFT, camera.unproject_position(p), false)
	assert_eq(commands.targeting, "", "left click confirms target")
	assert_eq(sel.selected.size(), army.size(), "confirming a target keeps the selection")
	world.step()
	for u in army:
		assert_true(u.current != null and u.current.type == Order.Type.PATROL, "%s patrolling" % u.name)


func test_enemy_click_selects_but_cannot_command() -> void:
	var enemy: Unit = null
	for u in world.unit_list:
		if u.player_id == 1 and u.is_mobile():
			enemy = u
			break
	camera.jump_to(enemy.pos)
	camera._process(0.016)
	_mouse(MOUSE_BUTTON_LEFT, _screen(enemy), true)
	_mouse(MOUSE_BUTTON_LEFT, _screen(enemy), false)
	assert_true(sel.selected.has(enemy), "enemy can be selected for inspection")
	var before := enemy.pos
	var goal := enemy.pos + Vector3(5, 0, 5)
	_mouse(MOUSE_BUTTON_RIGHT, camera.unproject_position(goal), true)
	for i in 30:
		world.step()
	assert_lt(Grid.flat_dist(enemy.pos, before), 0.01, "enemy unit ignores our commands")


## F10 pauses and unpauses: the HUD handles it and keeps processing while the tree is paused.
## Pausing cancels a pending targeting mode (CommandInput gets no clicks while paused, so it
## could be neither confirmed nor cancelled) and the command card issues nothing while paused.
func test_f10_toggles_pause_and_cancels_targeting() -> void:
	var commands: CommandInput = main.commands
	sel.select_units(_army())
	_key(KEY_R)
	assert_eq(commands.targeting, "attack_move", "targeting before the pause")
	assert_false(sel.enabled, "selection off while targeting")
	_key(KEY_F10)
	assert_true(tree.paused, "F10 pauses")
	assert_eq(commands.targeting, "", "pausing cancelled targeting")
	assert_true(sel.enabled, "selection enabled again")
	assert_false(commands.activate_card(3), "the command card does nothing while paused")
	assert_eq(commands.targeting, "", "no targeting entered while paused")
	_key(KEY_F10)
	assert_false(tree.paused, "F10 again unpauses")
	assert_true(main.pause_label.visible == false, "pause label hidden")
	assert_true(commands.activate_card(3), "commands work again")
	commands.cancel_targeting()
