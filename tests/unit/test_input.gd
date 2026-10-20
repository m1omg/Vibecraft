extends "res://tests/test_case.gd"
## Drives the real main scene with synthetic input events (headless): box select, right-click
## move, control groups, ctrl-click / double-click select-same-type, shift-click add/remove,
## targeting via the command card and the camera controls (arrows, wheel, middle-drag).

var main: Node
var world: World
var camera: RtsCamera
var sel: Selection


func before_each() -> void:
	Settings.edge_pan_enabled = false
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", "sandbox")   # placeholder test map + dummy_* units
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	world = main.world
	world.auto_tick = false
	camera = main.camera
	sel = main.selection


func after_each() -> void:
	Settings.edge_pan_enabled = true
	Settings.hotkey_preset = ""
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
	_key(KEY_P)
	assert_eq(commands.targeting, "patrol", "P enters patrol targeting (Classic)")
	_key(KEY_ESCAPE)
	assert_eq(commands.targeting, "", "Esc cancels targeting")
	_key(KEY_P)
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
	_key(KEY_A)
	assert_eq(commands.targeting, "attack_move", "targeting before the pause")
	assert_false(sel.enabled, "selection off while targeting")
	_key(KEY_F10)
	assert_true(tree.paused, "F10 pauses")
	assert_true(main.pause_menu.visible, "the pause menu shows")
	assert_eq(commands.targeting, "", "pausing cancelled targeting")
	assert_true(sel.enabled, "selection enabled again")
	assert_false(commands.activate_card(3), "the command card does nothing while paused")
	assert_eq(commands.targeting, "", "no targeting entered while paused")
	_key(KEY_F10)
	assert_false(tree.paused, "F10 again unpauses")
	assert_false(main.pause_menu.visible, "pause menu hidden")
	assert_true(commands.activate_card(3), "commands work again")
	commands.cancel_targeting()


## Classic preset (rules §18.4, the default): M move, S stop, H hold, A attack(-move), P patrol.
## A-click on the ground is an attack-move, on an enemy an attack; S stops, H holds.
func test_classic_hotkeys_issue_orders() -> void:
	var army := _army()
	sel.select_units(army)
	var commands: CommandInput = main.commands
	assert_eq(Settings.active_hotkey_preset(), "classic", "data default")
	_key(KEY_M)
	assert_eq(commands.targeting, "move", "M enters move targeting")
	_key(KEY_ESCAPE)
	_key(KEY_A)
	assert_eq(commands.targeting, "attack_move", "A enters attack targeting")
	var p := world.map.start_locations[0] + Vector3(8, 0, -12)
	p.y = world.map.height_at(p.x, p.z)
	_mouse(MOUSE_BUTTON_LEFT, camera.unproject_position(p), true)
	_mouse(MOUSE_BUTTON_LEFT, camera.unproject_position(p), false)
	world.step()
	for u in army:
		assert_true(u.current != null and u.current.type == Order.Type.ATTACK_MOVE, "%s attack-moving" % u.name)
	_key(KEY_H)
	world.step()
	for u in army:
		assert_true(u.current != null and u.current.type == Order.Type.HOLD, "%s holding" % u.name)
	_key(KEY_S)
	world.step()
	for u in army:
		assert_true(u.current == null, "%s stopped" % u.name)
	assert_eq(CommandCard.hotkey_label(3), "A", "card shows the Classic key")


## The Grid preset maps the card by position (Q W E R / A S D F): A is patrol there.
func test_grid_preset_hotkeys() -> void:
	Settings.hotkey_preset = "grid"
	sel.select_units(_army())
	var commands: CommandInput = main.commands
	_key(KEY_R)
	assert_eq(commands.targeting, "attack_move", "R = slot 3 (Attack) in the Grid preset")
	_key(KEY_ESCAPE)
	_key(KEY_A)
	assert_eq(commands.targeting, "patrol", "A = slot 4 (Patrol) in the Grid preset")
	commands.cancel_targeting()
	assert_eq(CommandCard.hotkey_label(3), "R", "card shows the Grid key")


## Double-click selects every own unit of that type on screen; shift+click adds a unit to the
## selection and shift+click on a selected unit removes it.
func test_double_click_and_shift_click() -> void:
	var army := _army()
	var soldiers := army.filter(func(u: Unit) -> bool: return u.def_id == "dummy_soldier")
	var others := army.filter(func(u: Unit) -> bool: return u.def_id != "dummy_soldier")
	assert_lt(1, soldiers.size(), "several soldiers to double-click")
	assert_lt(0, others.size(), "a unit of another type")
	var soldier: Unit = soldiers[0]
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), true, {"double": true})
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), false)
	assert_eq(sel.selected.size(), soldiers.size(), "double-click selects all soldiers on screen")
	for u in sel.selected:
		assert_eq(u.def_id, "dummy_soldier", "only the double-clicked type")
	sel.clear()
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), true)
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), false)
	var other: Unit = others[0]
	_mouse(MOUSE_BUTTON_LEFT, _screen(other), true, {"shift": true})
	_mouse(MOUSE_BUTTON_LEFT, _screen(other), false, {"shift": true})
	assert_eq(sel.selected.size(), 2, "shift+click adds")
	assert_true(sel.selected.has(soldier) and sel.selected.has(other), "both units selected")
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), true, {"shift": true})
	_mouse(MOUSE_BUTTON_LEFT, _screen(soldier), false, {"shift": true})
	assert_eq(sel.selected.size(), 1, "shift+click on a selected unit removes it")
	assert_true(sel.selected.has(other), "the other unit stays selected")


## Camera controls: arrow keys pan (refresh-rate independent: the same real time pans the same
## distance at 60 and 240 fps), the wheel zooms within the limits, middle-drag grabs the ground.
func test_camera_arrows_wheel_and_middle_drag() -> void:
	var start := world.map.start_locations[0]
	camera.jump_to(start + Vector3(10, 0, -10))
	camera.distance = camera.target_distance
	var f0 := camera.focus
	Input.action_press("cam_right")
	for i in 15:
		camera._process(1.0 / 60.0)
	var f60 := camera.focus
	camera.jump_to(f0)
	for i in 60:
		camera._process(1.0 / 240.0)
	var f240 := camera.focus
	Input.action_release("cam_right")
	assert_lt(1.0, f60.x - f0.x, "right arrow pans east")
	assert_lt(absf(f60.x - f240.x), 0.05, "pan distance does not depend on the frame rate")
	assert_lt(absf(f60.z - f0.z), 0.01, "no drift on the other axis")
	camera.jump_to(f0)
	var centre := tree.root.get_visible_rect().size * 0.5
	var d0 := camera.target_distance
	_mouse(MOUSE_BUTTON_WHEEL_UP, centre, true)
	_mouse(MOUSE_BUTTON_WHEEL_UP, centre, false)
	assert_lt(camera.target_distance, d0, "wheel up zooms in")
	for i in 50:
		_mouse(MOUSE_BUTTON_WHEEL_UP, centre, true)
		_mouse(MOUSE_BUTTON_WHEEL_UP, centre, false)
	assert_eq(camera.target_distance, camera.min_distance, "zoom stops at the near limit")
	for i in 50:
		_mouse(MOUSE_BUTTON_WHEEL_DOWN, centre, true)
		_mouse(MOUSE_BUTTON_WHEEL_DOWN, centre, false)
	assert_eq(camera.target_distance, camera.max_distance, "zoom stops at the far limit")
	camera.jump_to(f0)
	_mouse(MOUSE_BUTTON_MIDDLE, centre, true)
	_motion(centre + Vector2(-120, 0), Vector2(-120, 0))
	_mouse(MOUSE_BUTTON_MIDDLE, centre + Vector2(-120, 0), false)
	assert_lt(1.0, camera.focus.x - f0.x, "dragging the ground left moves the view east")
	var f1 := camera.focus
	_motion(centre, Vector2(120, 0))
	assert_eq(camera.focus, f1, "releasing the middle button ends the drag")


## Rules §18.1 (test_minimap_orders): with an order armed (A / M / P), a minimap left-click
## issues that order at the matching world point, without a camera jump, and disarms it; Shift
## queues it and keeps it armed. A right-click on the minimap cancels an armed order. With no
## order armed, a left-click still jumps the camera.
func test_minimap_orders() -> void:
	var army := _army()
	var commands: CommandInput = main.commands
	var mm: Minimap = main.hud.minimap
	assert_lt(10.0, mm.size.x, "the minimap is laid out")
	var origin := mm.get_global_rect().position
	var k := mm._scale()
	var start := world.map.start_locations[0]
	var cases: Array = [[KEY_A, "attack_move", Order.Type.ATTACK_MOVE, Vector3(10, 0, -16)],
		[KEY_M, "move", Order.Type.MOVE, Vector3(-6, 0, -14)],
		[KEY_P, "patrol", Order.Type.PATROL, Vector3(14, 0, -6)]]
	for c: Array in cases:
		sel.select_units(army)
		camera.jump_to(start)
		var f0 := camera.focus
		_key(c[0])
		assert_eq(commands.targeting, c[1], "%s armed" % c[1])
		var p: Vector3 = start + c[3]
		var at := origin + Vector2(p.x * k.x, p.z * k.y)
		_mouse(MOUSE_BUTTON_LEFT, at, true)
		_mouse(MOUSE_BUTTON_LEFT, at, false)
		assert_eq(commands.targeting, "", "%s: the minimap click confirms and disarms" % c[1])
		assert_lt(Grid.flat_dist(camera.focus, f0), 0.01, "%s: no camera jump" % c[1])
		world.step()
		var centre := Vector3.ZERO
		for u in army:
			assert_true(u.current != null and u.current.type == c[2], "%s: %s ordered" % [c[1], u.name])
			centre += u.current.target_pos if u.current != null else Vector3.ZERO
		centre /= army.size()
		assert_lt(Grid.flat_dist(centre, p), 3.0, "%s: issued at the minimap point" % c[1])
		_key(KEY_S)
		world.step()
	# Shift queues and keeps the order armed
	sel.select_units(army)
	_key(KEY_M)
	var p1 := start + Vector3(6, 0, -10)
	var p2 := start + Vector3(-8, 0, -16)
	for p in [p1, p2]:
		var at := origin + Vector2(p.x * k.x, p.z * k.y)
		_mouse(MOUSE_BUTTON_LEFT, at, true, {"shift": true})
		_mouse(MOUSE_BUTTON_LEFT, at, false, {"shift": true})
		assert_eq(commands.targeting, "move", "Shift keeps the move armed")
	world.step()
	for u in army:
		assert_true(u.current != null and u.current.type == Order.Type.MOVE, "%s moving" % u.name)
		assert_eq(u.orders.size(), 1, "%s has the second point queued" % u.name)
	# right-click on the minimap cancels the armed order and issues nothing
	var far := origin + Vector2((start.x + 20.0) * k.x, (start.z - 20.0) * k.y)
	_mouse(MOUSE_BUTTON_RIGHT, far, true)
	_mouse(MOUSE_BUTTON_RIGHT, far, false)
	assert_eq(commands.targeting, "", "right-click cancels the armed order")
	world.step()
	for u in army:
		assert_eq(u.orders.size(), 1, "%s: nothing new queued by the cancelling right-click" % u.name)
	# nothing armed: a left-click jumps the camera
	camera.jump_to(start)
	var q := start + Vector3(20, 0, -20)
	var at_q := origin + Vector2(q.x * k.x, q.z * k.y)
	_mouse(MOUSE_BUTTON_LEFT, at_q, true)
	_mouse(MOUSE_BUTTON_LEFT, at_q, false)
	assert_lt(Grid.flat_dist(camera.focus, q), 2.0, "a plain minimap left-click jumps the camera")


func _spawn_near(def_id: String, n: int, at: Vector3) -> Array[Unit]:
	var out: Array[Unit] = []
	for i in n:
		var p := at + Vector3(float(i % 4) * 1.2, 0.0, float(i / 4) * 1.2)
		out.append(world.spawn_unit(def_id, 0, p, 0.0))
	return out


## Rules §18.3: the selection is ordered heroes first, then by food cost, then by type; the
## 12-unit cap applies after that order (a hero spawned last is never dropped) and the first
## subgroup (the hero) is active. Tab cycles forward, Shift+Tab backwards.
func test_selection_order_heroes_first() -> void:
	var at := world.map.start_locations[0] + Vector3(6, 0, -8)
	var crowd := _spawn_near("kingdom_pavisier", 10, at)
	crowd.append_array(_spawn_near("kingdom_hookgunner", 3, at + Vector3(0, 0, 4)))
	var hero: Unit = world.spawn_unit("kingdom_wheel_marshal", 0, at + Vector3(-2, 0, 0), 0.0)
	crowd.append(hero)
	sel.select_units(crowd)
	assert_eq(sel.selected.size(), 12, "the cap")
	assert_eq(sel.selected[0], hero, "the hero leads the selection")
	assert_eq(sel.subgroup_defs(), ["kingdom_wheel_marshal", "kingdom_hookgunner", "kingdom_pavisier"] as Array[String],
		"subgroups: hero, then food 3, then food 2")
	assert_eq(sel.active_subgroup_def(), "kingdom_wheel_marshal", "the hero's subgroup is active")
	for i in range(1, 4):
		assert_eq(sel.selected[i].def_id, "kingdom_hookgunner", "hookgunners after the hero")
	_key(KEY_TAB)
	assert_eq(sel.active_subgroup_def(), "kingdom_hookgunner", "Tab moves to the next subgroup")
	_key(KEY_TAB, {"shift": true})
	assert_eq(sel.active_subgroup_def(), "kingdom_wheel_marshal", "Shift+Tab moves back")
	_key(KEY_TAB, {"shift": true})
	assert_eq(sel.active_subgroup_def(), "kingdom_pavisier", "Shift+Tab wraps to the last subgroup")
	# a box over the same crowd keeps the hero too
	sel.clear()
	camera.jump_to(at)
	camera._process(0.016)
	var box := _box_around(crowd)
	_mouse(MOUSE_BUTTON_LEFT, box.position, true)
	_motion(box.position + Vector2(20, 20), Vector2(20, 20))
	_motion(box.end, box.end - box.position)
	_mouse(MOUSE_BUTTON_LEFT, box.end, false)
	assert_eq(sel.selected.size(), 12, "box: the cap")
	assert_true(sel.selected.has(hero), "box: the hero is kept")
	assert_eq(sel.selected[0], hero, "box: the hero leads")


## Rules §18.3: F1–F3 select the heroes in training order (double-tap centres the camera),
## Backspace cycles the own halls and centres on each; PgUp / PgDn zoom (§18.1).
func test_hero_hall_and_zoom_keys() -> void:
	var at := world.map.start_locations[0] + Vector3(10, 0, -12)
	var h1: Unit = world.spawn_unit("kingdom_wheel_marshal", 0, at, 0.0)
	var h2: Unit = world.spawn_unit("kingdom_firewright", 0, at + Vector3(3, 0, 0), 0.0)
	var other := _army()[0]
	sel.select_units([other])
	_key(KEY_F2)
	assert_eq(sel.selected, [h2] as Array[Unit], "F2 selects the second hero")
	_key(KEY_F3)
	assert_eq(sel.selected, [h2] as Array[Unit], "F3 without a third hero changes nothing")
	camera.jump_to(at + Vector3(40, 0, 40))
	_key(KEY_F1)
	assert_eq(sel.selected, [h1] as Array[Unit], "F1 selects the first hero")
	assert_lt(5.0, Grid.flat_dist(camera.focus, h1.pos), "a single tap does not move the camera")
	_key(KEY_F1)
	assert_lt(Grid.flat_dist(camera.focus, h1.pos), 0.5, "a double-tap centres on the hero")
	var halls: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == 0 and u.has_flag("town_hall"):
			halls.append(u)
	assert_lt(0, halls.size(), "the sandbox base has a hall")
	camera.jump_to(at + Vector3(40, 0, 40))
	_key(KEY_BACKSPACE)
	assert_eq(sel.selected, [halls[0]] as Array[Unit], "Backspace selects the hall")
	assert_lt(Grid.flat_dist(camera.focus, halls[0].pos), 0.5, "and centres on it")
	_key(KEY_BACKSPACE)
	assert_eq(sel.selected[0], halls[1 % halls.size()], "Backspace again cycles to the next hall")
	var d0 := camera.target_distance
	_key(KEY_PAGEUP)
	assert_lt(camera.target_distance, d0, "PgUp zooms in")
	_key(KEY_PAGEDOWN)
	_key(KEY_PAGEDOWN)
	assert_lt(d0, camera.target_distance, "PgDn zooms out")
