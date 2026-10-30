extends SceneTree
## Fog of war in the real game view (rules §14, src/world/fog.gd): the Playtest battlefield with
## fog on; the opening (the base seen, the rest black or fogged), the edge of vision from the
## base ramp, and the minimap's fog layer.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy \
##     -s tests/playtest/fog_view.gd
## Saves tests/output/fog_{opening,edge,scouted}.png. Exit code 1 when fog is off or the enemy
## base is visible at the start.

const OUT_DIR := "res://tests/output/"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	load("res://src/main.gd").call("start_match", self, "battlefield")
	await _frames(3)
	var main: Node = current_scene
	var world: Node = main.get("world")
	world.set("auto_tick", false)
	var fog: Object = world.get("fog")
	var camera: Camera3D = main.get("camera")
	camera.set("edge_pan_enabled", false)
	var failed := false
	if not bool(fog.get("enabled")):
		push_error("fog_view: fog is off")
		quit(1)
		return
	var enemy_hall: Node = null
	for u: Node in world.get("unit_list"):
		if str(u.get("def_id")) == "clans_shell_hall":
			enemy_hall = u
	if enemy_hall != null and bool(fog.call("shows", 0, enemy_hall)):
		push_error("fog_view: the enemy hall is drawn at the start")
		failed = true
	for i in 6:
		world.call("step")
	await _frames(3)
	await _shot("fog_opening.png")
	# the edge of vision: look past the army towards the map centre
	var centre := Vector3(96, 0, 96)
	var start: Vector3 = camera.get("focus")
	camera.jump_to(start.lerp(centre, 0.45))
	await _frames(3)
	await _shot("fog_edge.png")
	# scout with the heroes towards the centre, then look back at what they left fogged
	var battle: Object = main.get("battle")
	var army: Array = battle.call("members", battle.call("group", "army", 0))
	var heroes: Array = army.filter(func(u: Node) -> bool: return bool(u.get("is_hero")))
	world.call("issue", {"type": "move", "player": 0, "units": heroes.map(func(u: Node) -> int: return int(u.get("id"))),
		"pos": centre})
	for i in 30 * 14:
		world.call("step")
	camera.jump_to((heroes[0] as Node).get("pos"))
	await _frames(3)
	await _shot("fog_scouted.png")
	print("fog_view: stats %s" % [fog.get("last_stats")])
	quit(1 if failed else 0)


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved ", path)
