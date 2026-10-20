extends SceneTree
## Playtest 1 QA-fix screenshots (the PT1 QA pass): the real default opening (camera between the
## hall and the army, the army box-selected with the hero leading the selection), the two heroes
## walking into the turnip-patch camp with the whole camp fighting back, the war-band marching
## as a group, and the army sent across the map with A + a minimap click. The sim is stepped by
## hand between captures (the software renderer runs at ~2 fps).
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/pt1_fixes.gd
## Saves tests/output/pt1_fix_{opening,creeps,warband,minimap}.png. Exit code 1 when a check
## fails (the camp does not answer as one, the A + minimap order is not issued).

const OUT_DIR := "res://tests/output/"

var main: Node
var world: Node
var battle: Object
var camera: Camera3D
var failed := false


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	var menu: Node = (load("res://src/ui/main_menu.tscn") as PackedScene).instantiate()
	root.add_child(menu)
	current_scene = menu
	await _frames(2)
	menu.call("start_battlefield")
	for i in 30:
		await process_frame
		if current_scene != null and current_scene != menu and current_scene.get("battle") != null:
			break
	main = current_scene
	world = main.get("world")
	world.set("auto_tick", false)
	battle = main.get("battle")
	camera = main.get("camera")
	camera.set("edge_pan_enabled", false)
	var sel: Node = main.get("selection")
	var army: Array = battle.call("members", battle.call("group", "army", 0))
	# 1. the default opening, untouched camera; the army selected (heroes lead, 12 cap)
	sel.call("select_units", army)
	await _frames(4)
	var first: Node = (sel.get("selected") as Array)[0]
	print("pt1_fix: opening focus %s, first selected %s, active subgroup %s" % [camera.get("focus"),
		first.get("def_id"), sel.call("active_subgroup_def")])
	if not bool(first.get("is_hero")):
		push_error("pt1_fix: the selection does not start with a hero")
		failed = true
	await _shot("pt1_fix_opening.png")
	# 2. the heroes walk (move, not attack) into the turnip patch: the whole camp answers
	var heroes: Array = army.filter(func(u: Node) -> bool: return bool(u.get("is_hero")))
	var camp_id := str((root.get_node("Defs").call("scenario", "battlefield")["camps"] as Array)[1])
	var creeps: Array = world.get("creeps").call("camp_members", camp_id)
	var centre: Vector3 = world.get("creeps").call("camps")[camp_id]["pos"]
	world.call("issue", {"type": "move", "player": 0, "units": heroes.map(func(u: Node) -> int: return int(u.get("id"))),
		"pos": centre})
	var all_in := -1.0
	for i in 30 * 40:
		world.call("step")
		var n := 0
		for c: Node in creeps:
			if bool(c.get("alive")) and int(c.call("combat_target_id")) != 0:
				n += 1
		if n == creeps.size():
			all_in = float(world.get("time"))
			break
	print("pt1_fix: every member of %s engaged at %.1f s" % [camp_id, all_in])
	if all_in < 0.0:
		push_error("pt1_fix: the camp did not answer as one")
		failed = true
	for i in 20:
		world.call("step")
	sel.call("select_units", heroes)
	var mid := Vector3.ZERO
	for h: Node in heroes:
		mid += h.get("pos")
	mid /= maxf(heroes.size(), 1)
	camera.set("target_distance", 18.75)
	camera.set("distance", 18.75)
	camera.jump_to(mid + Vector3(0.0, 0.0, 1.0))
	await _frames(6)
	await _shot("pt1_fix_creeps.png")
	# 3. the war-band marching at the player's base as a group (formation pace)
	var wave: Array = battle.call("members", battle.call("group", "warband", 1))
	while float(world.get("time")) < 112.0:
		world.call("step")
	var c3 := Vector3.ZERO
	for u: Node in wave:
		c3 += u.get("pos")
	c3 /= maxf(wave.size(), 1)
	var spread := 0.0
	for u: Node in wave:
		spread = maxf(spread, (u.get("pos") as Vector3).distance_to(c3))
	print("pt1_fix: war-band at %.1f s, centre %s, spread %.1f m" % [world.get("time"), c3, spread])
	sel.call("clear")
	camera.set("target_distance", 25.8)
	camera.jump_to(c3)
	await _frames(4)
	await _shot("pt1_fix_warband.png")
	# 4. A + minimap left-click sends the army at the Tormai base (no camera jump)
	camera.jump_to(battle.call("camera_start", 0))
	var rest: Array = army.filter(func(u: Node) -> bool: return bool(u.get("alive")) and not bool(u.get("is_hero")))
	sel.call("select_units", rest)
	await _frames(2)
	var mm: Control = main.get("hud").get("minimap")
	var target := Vector3(150.0, 0.0, 60.0)
	var k: Vector2 = mm.call("_scale")
	var at: Vector2 = mm.get_global_rect().position + Vector2(target.x * k.x, target.z * k.y)
	var f0: Vector3 = camera.get("focus")
	_key(KEY_A)
	_click(at)
	await _frames(1)
	world.call("step")
	var ok := 0
	for u: Node in sel.get("selected"):
		var cur: Object = u.get("current")
		if cur != null and int(cur.get("type")) == 5:   # Order.Type.ATTACK_MOVE
			ok += 1
	var moved: float = (camera.get("focus") as Vector3).distance_to(f0)
	print("pt1_fix: A + minimap click: %d / %d attack-moving, camera moved %.2f m, targeting '%s'" % [ok,
		(sel.get("selected") as Array).size(), moved, main.get("commands").get("targeting")])
	if ok == 0 or moved > 0.5:
		push_error("pt1_fix: A + minimap click did not issue the order")
		failed = true
	for i in 90:
		world.call("step")
	await _frames(3)
	await _shot("pt1_fix_minimap.png")
	quit(1 if failed else 0)


func _key(key: Key) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.keycode = key
		ev.pressed = pressed
		root.push_input(ev, true)


func _click(at: Vector2) -> void:
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.position = at
		ev.global_position = at
		ev.pressed = pressed
		root.push_input(ev, true)


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		print("pt1_fix: no framebuffer (headless?), skipped ", file_name)
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved ", path)
