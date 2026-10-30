extends SceneTree
## Boots the main scene under a real display and saves screenshots to tests/output/:
##   overview_default.png  - default gameplay camera at player 0's base (units selected, some walking)
##   overview_zoomed_out.png - high, zoomed-out view over the middle of the map
##   overview_enemy_base.png - default camera over player 1's base
##   overview_cliffs.png  - default camera at a plateau ramp (cliff walls, ramp)
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy \
##     -s tests/playtest/screenshot_overview.gd
## Everything is loaded at runtime (autoload names are not visible to -s scripts at compile time).

const OUT_DIR := "res://tests/output/"

var main: Node


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	await _frames(5)
	var world: Node = main.get_node("World")
	var camera: Camera3D = main.get_node("Camera")
	var selection: Node = main.get_node("UI/Selection")
	# select player 0's army and walk half of it towards the map centre
	var army: Array = []
	for u in world.get("unit_list"):
		if u.player_id == 0 and not u.is_building and not u.is_worker:
			army.append(u)
	selection.select_units(army)
	var walkers: Array = []
	for i in range(0, army.size(), 2):
		walkers.append(army[i].id)
	var start: Vector3 = world.map.start_locations[0]
	world.issue({"type": "move", "player": 0, "units": walkers, "pos": start + Vector3(14, 0, -10)})
	await _frames(45)
	await _shot("overview_default.png")

	camera.set("pitch_deg", -62.0)
	camera.set("max_distance", 200.0)
	camera.set("distance", 175.0)
	camera.set("target_distance", 175.0)
	camera.jump_to(Vector3(96, 0, 112))
	await _frames(10)
	await _shot("overview_zoomed_out.png")

	camera.set("pitch_deg", -56.0)
	camera.set("distance", 28.0)
	camera.set("target_distance", 28.0)
	camera.jump_to(world.map.start_locations[1] + Vector3(0, 0, 2))
	var enemies: Array = []
	for u in world.get("unit_list"):
		if u.player_id == 1 and not u.is_building:
			enemies.append(u)
	selection.select_units([enemies[0]])
	await _frames(10)
	await _shot("overview_enemy_base.png")
	# cliffs + ramp: south ramp of the north-west plateau (walls face the camera there)
	var m: Object = world.map
	var ramp: Dictionary = m.ramps[6]
	var rect: Rect2i = ramp["rect"]
	camera.jump_to(Vector3((rect.position.x + rect.size.x * 0.5) * 2.0, 0, (rect.position.y + rect.size.y * 0.5) * 2.0 + 3.0))
	selection.select_units([])
	await _frames(10)
	await _shot("overview_cliffs.png")
	print("ticks simulated: %d, fps %d" % [world.tick_count, Engine.get_frames_per_second()])
	quit(0)


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved ", path, " ", img.get_size())
