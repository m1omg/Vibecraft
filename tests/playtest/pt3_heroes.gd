extends SceneTree
## Playtest 3 heroes in the real game view (slice scenario): the hero bar with two heroes (one
## with unspent points, one fallen and reviving), the hero card with its Learn page open and a
## learn tooltip, and the altar's card with the Revive button.
## Untyped on purpose: a -s script compiles before the autoloads exist.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy \
##     -s tests/playtest/pt3_heroes.gd
## Saves tests/output/pt3_{learn_page,altar_revive,level_up}.png.

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
	var p: Object = world.call("player", 0)
	p.set("gold", 3000)
	p.set("lumber", 3000)
	var hall: Node = null
	for u: Node in world.get("unit_list"):
		if int(u.get("player_id")) == 0 and str(u.get("def_id")) == "kingdom_moot_hall":
			hall = u
	var hall_pos: Vector3 = hall.get("pos")
	var altar: Node = world.call("spawn_unit", "kingdom_oath_hall", 0, hall_pos + Vector3(-14, 0, 9))
	var marshal: Node = world.call("spawn_unit", "kingdom_wheel_marshal", 0, hall_pos + Vector3(7, 0, 7))
	var fire: Node = world.call("spawn_unit", "kingdom_firewright", 0, hall_pos + Vector3(9, 0, 5))
	var heroes: Object = world.get("heroes")
	heroes.call("add_xp", marshal, 950.0)
	heroes.call("learn", marshal, "kingdom_linden_balm")
	fire.call("take_damage", 999999.0, null)
	for i in 3:
		world.call("step")
	world.call("issue", {"type": "revive", "player": 0, "units": [altar.get("id")], "hero": fire.get("id")})
	for i in 30 * 5:
		world.call("step")
	sel.call("select_units", [marshal])
	camera.call("jump_to", marshal.get("pos"))
	commands.call("set_page", "learn")
	await _frames(4)
	var card: Control = hud.get("card")
	var tip: Control = hud.get("tooltip")
	var b: Control = (card.get("buttons") as Array)[8]
	tip.call("hover", b, hud.call("card_tooltip", card.call("entry", 8)), card.get_global_rect())
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(4)
	await _shot("pt3_learn_page.png")
	tip.call("unhover", b)
	tip.set("_leave_t0", float(tip.get("_leave_t0")) - 1.0)
	sel.call("select_units", [altar])
	camera.call("jump_to", altar.get("pos"))
	await _frames(4)
	var bar: Control = hud.get("hero_bar")
	var slot: Control = (bar.get("slots") as Array)[1]
	tip.call("hover", slot, bar.call("tooltip_for", 1), slot.get_global_rect(), true)
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(4)
	await _shot("pt3_altar_revive.png")
	tip.call("unhover", slot)
	tip.set("_leave_t0", float(tip.get("_leave_t0")) - 1.0)
	# the level-up ceremony on a manual fx clock: the emblem stands 0.5 s in
	var enemy: Node = world.call("spawn_unit", "clans_hero_skymirror", 1, marshal.get("pos") + Vector3(4, 0, -2))
	sel.call("select_units", [marshal])
	camera.call("jump_to", marshal.get("pos"))
	await _frames(3)
	FxClock.manual = true
	heroes.call("add_xp", marshal, 600.0)
	for i in 16:
		FxClock.advance(1.0 / 30.0, true)
		await process_frame
	print("enemy hero ", enemy.get("def_id"))
	await _shot("pt3_level_up.png")
	FxClock.manual = false
	quit(0)


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
