extends SceneTree
## Scripted battle playtest under a real display: 8 soldiers + 4 archers (player 0) attack-move
## into 10 creeps on an open patch of the test map, inside the real main scene (HUD, camera,
## selection). The sim runs on the normal fixed 30 Hz tick (time_scale 1.5 and more physics
## steps per frame keep the software renderer bearable). Asserts one side wins within 90 sim
## seconds and saves tests/output/battle_1..3.png during the fight. Exit code 1 on failure.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/battle.gd
## Everything is loaded at runtime (autoload names are not visible to -s scripts at compile time).

const OUT_DIR := "res://tests/output/"
const SHOTS: Array[float] = [5.0, 11.0, 19.0]   ## sim seconds after the charge
const SEARCH_FROM := Vector3(88.0, 0.0, 28.0)   ## open field north of the basin (seed 1337)

var main: Node
var world: Node


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	var battle: GDScript = load("res://tests/playtest/battle_setup.gd")
	root.get_node("Defs").call("load_test_defs")
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", "sandbox")   # the generated test map + placeholder dummy_* units
	root.add_child(main)
	await _frames(3)
	world = main.get_node("World")
	var centre: Vector3 = battle.find_open_area(world, SEARCH_FROM)
	if centre == Vector3.INF:
		push_error("battle: no open area found")
		quit(1)
		return
	var sides: Dictionary = battle.spawn(world, centre)
	var camera: Camera3D = main.get_node("Camera")
	camera.set("target_distance", 24.0)
	camera.set("distance", 24.0)
	camera.jump_to(centre + Vector3(-2.0, 0.0, 4.0))
	main.get_node("UI/Selection").select_units(sides["army"])
	await _frames(2)
	Engine.max_physics_steps_per_frame = 40
	Engine.time_scale = 1.5
	var t0: float = world.time
	battle.charge(world, sides["army"], centre)
	var shot := 0
	var result := ""
	while world.time - t0 < battle.TIME_LIMIT_S:
		await process_frame
		_follow(camera, sides)
		if shot < SHOTS.size() and _shot_due(world.time - t0, SHOTS[shot]):
			shot += 1
			await _shot("battle_%d.png" % shot, world.time - t0, sides, battle)
		result = battle.winner(sides)
		if result != "" and shot >= SHOTS.size():
			break
	Engine.time_scale = 1.0
	var army_left: int = battle.alive_count(sides["army"])
	var creeps_left: int = battle.alive_count(sides["creeps"])
	print("battle: winner=%s after %.1f sim s, army %d/%d, creeps %d/%d, fps %d" % [result,
		world.time - t0, army_left, (sides["army"] as Array).size(), creeps_left,
		(sides["creeps"] as Array).size(), Engine.get_frames_per_second()])
	if result == "":
		push_error("battle: no winner within %d sim seconds" % int(battle.TIME_LIMIT_S))
		quit(1)
		return
	quit(0)


## Keeps the camera over the living fighters (visual only).
func _follow(camera: Camera3D, sides: Dictionary) -> void:
	var c := Vector3.ZERO
	var n := 0
	for side: String in ["army", "creeps"]:
		for u: Variant in sides[side]:
			if is_instance_valid(u) and u.alive:
				c += u.pos
				n += 1
	if n == 0:
		return
	var focus: Vector3 = camera.get("focus")
	camera.jump_to(focus.lerp(c / n + Vector3(0.0, 0.0, 3.0), 0.1))


## Waits (up to 2 s) for arrows in flight so the capture shows projectiles too.
func _shot_due(t: float, at: float) -> bool:
	if t < at:
		return false
	return t >= at + 2.0 or not (world.get("combat").get("projectiles") as Array).is_empty()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String, t: float, sides: Dictionary, battle: GDScript) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		print("battle: no framebuffer (headless?), skipped ", file_name)
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved %s at %.1f s (army %d, creeps %d, projectiles %d)" % [path, t,
		battle.alive_count(sides["army"]), battle.alive_count(sides["creeps"]),
		(world.get("combat").get("projectiles") as Array).size()])
