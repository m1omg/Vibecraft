extends SceneTree
## The Bombard Wagon in the real game view (tools/kits/siege.py model, src/fx/vehicle_rig.gd):
## the Playtest 1 battlefield, the camera close on the kingdom's wagon; it rolls forward (wheels
## turn, the crew walk), then fires at a Tormai Grappler placed in range (the barrel recoils).
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/siege_wagon.gd
## Then the Tormai Sling-Cart fires at a Pavisier (the throwing arm whips forward on the release).
## Saves tests/output/siege_wagon_{rest,rolling,recoil}.png and siege_sling_{rest,release}.png. Exit
## code 1 when a cart has no vehicle rig, the wheels did not turn, the barrel did not recoil or the
## arm did not swing.

const OUT_DIR := "res://tests/output/"

var failed := false


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	var main: Node = load("res://src/main.gd").call("start_match", self, "battlefield")
	await _frames(3)
	main = current_scene
	var world: Node = main.get("world")
	world.set("auto_tick", false)
	var camera: Camera3D = main.get("camera")
	camera.set("edge_pan_enabled", false)
	var wagon: Node = null
	for u: Node in world.get("unit_list"):
		if str(u.get("def_id")) == "kingdom_bombard_wagon" and int(u.get("player_id")) == 0:
			wagon = u
			break
	if wagon == null:
		push_error("siege_wagon: no Bombard Wagon in the scenario")
		quit(1)
		return
	var view: Node = wagon.get("view")
	var rig: Object = view.get("vehicle")
	if rig == null:
		push_error("siege_wagon: the wagon has no vehicle rig (model %s)" % view.get("model_path"))
		quit(1)
		return
	camera.set("target_distance", 18.75)
	camera.set("distance", 18.75)
	camera.jump_to(wagon.get("pos"))
	await _frames(4)
	await _shot("siege_wagon_rest.png")
	# roll forward: the wheels turn and the crew walk
	var fwd := Vector3(-sin(float(wagon.get("facing"))), 0.0, -cos(float(wagon.get("facing"))))
	var goal: Vector3 = wagon.get("pos") + Vector3(6.0, 0.0, -6.0)
	world.call("issue", {"type": "move", "player": 0, "units": [wagon.get("id")], "pos": goal})
	var wheel: Node3D = rig.get("wheels")[0]
	for i in 36:
		world.call("step")
		camera.jump_to(wagon.get("pos"))
		await process_frame
	print("siege_wagon: rolled %.2f m, wheel angle %.2f rad" % [float(rig.get("distance")), wheel.rotation.x])
	if absf(wheel.rotation.x) < 0.5:
		push_error("siege_wagon: the wheels did not turn")
		failed = true
	await _shot("siege_wagon_rolling.png")
	for i in 60:
		world.call("step")
	# fire at a Tormai Grappler in range: the barrel recoils on the shot
	var p: Vector3 = wagon.get("pos")
	fwd = Vector3(-sin(float(wagon.get("facing"))), 0.0, -cos(float(wagon.get("facing"))))
	var foe: Node = world.call("spawn_unit", "clans_grappler", 1, p + fwd * 11.0)
	world.call("issue", {"type": "attack", "player": 0, "units": [wagon.get("id")], "target": foe.get("id")})
	var barrel: Node3D = rig.get("barrel")
	var rest: Vector3 = rig.get("barrel_rest")
	var kicked := false
	for i in 30 * 6:
		world.call("step")
		camera.jump_to(wagon.get("pos") + fwd * 3.0)
		await process_frame
		if barrel.position.distance_to(rest) > 0.1:
			kicked = true
			break
	print("siege_wagon: recoil %.3f m" % barrel.position.distance_to(rest))
	if not kicked:
		push_error("siege_wagon: the barrel did not recoil")
		failed = true
	await _shot("siege_wagon_recoil.png")
	# the Tormai Sling-Cart: at rest, then the release
	var cart: Node = null
	for u: Node in world.get("unit_list"):
		if str(u.get("def_id")) == "clans_sling_cart" and bool(u.get("alive")):
			cart = u
			break
	if cart == null or cart.get("view").get("vehicle") == null:
		push_error("siege_wagon: no Sling-Cart with a vehicle rig")
		quit(1)
		return
	var crig: Object = cart.get("view").get("vehicle")
	camera.jump_to(cart.get("pos"))
	await _frames(3)
	await _shot("siege_sling_rest.png")
	var cf := Vector3(-sin(float(cart.get("facing"))), 0.0, -cos(float(cart.get("facing"))))
	var mark: Node = world.call("spawn_unit", "kingdom_pavisier", 0, (cart.get("pos") as Vector3) + cf * 11.0)
	world.call("issue", {"type": "attack", "player": 1, "units": [cart.get("id")], "target": mark.get("id")})
	var arm: Node3D = crig.get("arm")
	var swung := false
	for i in 30 * 6:
		world.call("step")
		camera.jump_to(cart.get("pos"))
		await process_frame
		if arm.rotation.x < -0.6:
			swung = true
			break
	print("siege_wagon: sling arm %.2f rad" % arm.rotation.x)
	if not swung:
		push_error("siege_wagon: the throwing arm did not swing")
		failed = true
	await _shot("siege_sling_release.png")
	quit(1 if failed else 0)


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		print("siege_wagon: no framebuffer (headless?), skipped ", file_name)
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + file_name)
	img.save_png(path)
	print("saved ", path)
