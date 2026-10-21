extends SceneTree
## The base-building HUD in the real game view (slice scenario): the build ghost on a valid spot
## and over the hall (refused), the hall's card with a queue and a locked upgrade's tooltip, and
## the build page short of gold (hatched buttons, shortfall tooltip, error line).
## Untyped on purpose: a -s script compiles before the autoloads exist.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/base_hud.gd
## Saves tests/output/hud_{place_valid,place_blocked,hall_queue,short_of_gold}.png.

const OUT_DIR := "res://tests/output/"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	load("res://src/main.gd").call("start_match", self, "slice")
	await _frames(3)
	var main: Node = current_scene
	var world: Node = main.get("world")
	world.set("auto_tick", false)
	var camera: Camera3D = main.get("camera")
	camera.set("edge_pan_enabled", false)
	var sel: Node = main.get("selection")
	var commands: Node = main.get("commands")
	var hud: Node = main.get("hud")
	for i in 6:
		world.call("step")
	var hods: Array = []
	var hall: Node = null
	for u: Node in world.get("unit_list"):
		if int(u.get("player_id")) == 0 and str(u.get("def_id")) == "kingdom_hodman":
			hods.append(u)
		if int(u.get("player_id")) == 0 and str(u.get("def_id")) == "kingdom_moot_hall":
			hall = u
	var hall_pos: Vector3 = hall.get("pos")
	sel.call("select_units", hods)
	commands.call("set_page", "build_basic")
	commands.call("begin_placement", "kingdom_croft")
	var ghost: Node = commands.get("placement")
	var spot := _free_spot(world, camera, hud, hall_pos)
	ghost.set("screen_override", camera.unproject_position(spot))
	await _frames(20)
	print("ghost valid=%s reason=%s" % [ghost.get("valid"), ghost.get("reason")])
	await _shot("hud_place_valid.png")
	ghost.set("screen_override", camera.unproject_position(hall_pos + Vector3(2.0, 0, 1.0)))
	await _frames(20)
	print("ghost over the hall valid=%s reason=%s" % [ghost.get("valid"), ghost.get("reason")])
	await _shot("hud_place_blocked.png")
	commands.call("cancel_targeting")
	sel.call("select_units", [hall])
	for i in 3:
		commands.call("activate_card", 0)
	for i in 30 * 4:
		world.call("step")
	await _frames(3)
	var card: Control = hud.get("card")
	var tip: Control = hud.get("tooltip")
	var b: Control = (card.get("buttons") as Array)[1]
	tip.call("hover", b, hud.call("card_tooltip", card.call("entry", 1)), card.get_global_rect())
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(4)
	await _shot("hud_hall_queue.png")
	tip.call("unhover", b)
	tip.set("_leave_t0", float(tip.get("_leave_t0")) - 1.0)
	world.call("player", 0).set("gold", 60)
	sel.call("select_units", [hods[0]])
	commands.call("set_page", "build_basic")
	await _frames(3)
	var croft: Control = (card.get("buttons") as Array)[1]
	tip.call("hover", croft, hud.call("card_tooltip", card.call("entry", 1)), card.get_global_rect())
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(2)
	commands.call("activate_card", 1)    # refused: error line, counter shake, shortfall ghost
	await _frames(1)
	await _shot("hud_short_of_gold.png")
	quit(0)


func _free_spot(world: Node, camera: Camera3D, hud: Node, around: Vector3) -> Vector3:
	var vp := root.get_viewport().get_visible_rect().size
	var con: Object = world.get("construction")
	for r in range(7, 30, 2):
		for k in 16:
			var a := TAU * k / 16.0
			var p := around + Vector3(cos(a), 0, sin(a)) * float(r)
			var s := camera.unproject_position(p)
			if s.x < 100 or s.y < 100 or s.x > vp.x - 100 or bool(hud.call("covers", s)):
				continue
			var spot: Dictionary = con.call("can_place", 0, "kingdom_croft", p)
			if spot["ok"]:
				return spot["pos"]
	return around + Vector3(8, 0, 0)


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
