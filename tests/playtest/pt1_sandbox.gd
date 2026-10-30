extends SceneTree
## Playtest 1 screenshots: the main menu, the battlefield opening (own army selected), the
## war-band fight at the player's base, the F10 pause menu and the victory banner. Boots through
## the real menu -> Main.start_match path. The sim is stepped by hand between captures (the
## software renderer runs at ~2 fps), so every capture shows a real sim moment.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy \
##     -s tests/playtest/pt1_sandbox.gd
## Saves tests/output/pt1_{menu,opening,fight,pause,end}.png. Exit code 1 when the fight never
## happens or the banner does not show. Everything is loaded at runtime (autoload names are not
## visible to -s scripts at compile time).

const OUT_DIR := "res://tests/output/"

var main: Node
var world: Node
var battle: Object
var camera: Camera3D


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	var menu: Node = (load("res://src/ui/main_menu.tscn") as PackedScene).instantiate()
	root.add_child(menu)
	current_scene = menu
	await _frames(3)
	await _shot("pt1_menu.png")
	menu.call("start_battlefield")
	for i in 30:
		await process_frame
		if current_scene != null and current_scene != menu and current_scene.get("battle") != null:
			break
	main = current_scene
	if main == null or main.get("battle") == null:
		push_error("pt1: the battlefield did not start")
		quit(1)
		return
	world = main.get("world")
	world.set("auto_tick", false)
	battle = main.get("battle")
	camera = main.get("camera")
	camera.set("edge_pan_enabled", false)
	# opening: the army selected, camera on the base
	var army: Array = battle.call("members", battle.call("group", "army", 0))
	main.get("selection").call("select_units", army)
	camera.jump_to((army[0] as Node3D).get("pos") + Vector3(-5.0, 0.0, 6.0))
	await _frames(4)
	await _shot("pt1_opening.png")
	# fast-forward (no rendering) until the war-band meets the army
	var met := false
	while float(world.get("time")) < 170.0:
		world.call("step")
		if _clash_centre() != Vector3.INF and float(world.get("time")) > 95.0:
			met = true
			break
	if not met:
		push_error("pt1: the war-band never reached the army")
		quit(1)
		return
	# a few seconds of fight, rendered: 2 ticks per frame, a little closer in
	camera.set("target_distance", 21.0)
	for i in 75:
		world.call("step")
		world.call("step")
		var c := _clash_centre()
		if c != Vector3.INF:
			camera.jump_to((camera.get("focus") as Vector3).lerp(c + Vector3(0.0, 0.0, 3.0), 0.25))
		await process_frame
	main.get("selection").call("select_units", battle.call("members", battle.call("group", "army", 0)))
	await _frames(2)
	await _shot("pt1_fight.png")
	print("pt1: fight at %.1f s, kingdom %d, tormai %d, projectiles %d" % [world.get("time"),
		battle.call("entity_count", 0), battle.call("entity_count", 1),
		(world.get("combat").get("projectiles") as Array).size()])
	# pause menu
	root.get_node("Events").emit_signal("menu_requested")
	await _frames(3)
	await _shot("pt1_pause.png")
	main.get("pause_menu").emit_signal("resume_pressed")
	await _frames(2)
	# finish the war-band, then raze the Tormai base: victory banner
	for i in 2700:
		world.call("step")
		if (battle.call("members", battle.call("group", "warband", 1)) as Array).is_empty():
			break
	for u: Node in world.call("units_of_player", 1):
		u.call("take_damage", float(u.get("hp")) + 1.0, null)
	for i in 20:
		world.call("step")
	camera.set("target_distance", 25.8)
	camera.jump_to(battle.call("camera_start", 0))
	await _frames(2)
	var banner: Node = main.get("end_banner")
	banner.call("finish_fade")
	await _frames(3)
	if not banner.get("visible"):
		push_error("pt1: no end banner")
		quit(1)
		return
	await _shot("pt1_end.png")
	print("pt1: result ", battle.get("result"))
	quit(0)


## Midpoint of the closest pair of fighting kingdom / war-band units (INF when none fights).
func _clash_centre() -> Vector3:
	var wave: Array = battle.call("members", battle.call("group", "warband", 1))
	var best := Vector3.INF
	var best_d := INF
	for u: Node in wave:
		var tid: int = u.call("combat_target_id")
		if tid == 0:
			continue
		var t: Node = world.call("get_unit", tid)
		if t == null or int(t.get("player_id")) != 0:
			continue
		var d: float = (u.get("pos") as Vector3).distance_to(t.get("pos"))
		if d < best_d:
			best_d = d
			best = ((u.get("pos") as Vector3) + (t.get("pos") as Vector3)) * 0.5
	return best


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		print("pt1: no framebuffer (headless?), skipped ", file_name)
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved ", path)
