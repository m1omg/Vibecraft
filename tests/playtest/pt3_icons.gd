extends SceneTree
## Icons in the real game view (slice scenario): the Hodman's build page, the hall's portrait with
## the Walled Burg upgrade in its queue, a hero's inventory and the Weighstall's stock.
## Untyped on purpose: a -s script compiles before the autoloads exist.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy -s tests/playtest/pt3_icons.gd
## Saves tests/output/icons_{build_page,hall_queue,inventory,shop}.png.

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
	p.set("gold", 5000)
	p.set("lumber", 5000)
	var hall: Node = null
	var hod: Node = null
	for u: Node in world.get("unit_list"):
		if int(u.get("player_id")) == 0 and str(u.get("def_id")) == "kingdom_moot_hall":
			hall = u
		if int(u.get("player_id")) == 0 and str(u.get("def_id")) == "kingdom_hodman" and hod == null:
			hod = u
	var hall_pos: Vector3 = hall.get("pos")
	var tip: Control = hud.get("tooltip")
	var card: Control = hud.get("card")
	# 1. the build page with a tooltip
	sel.call("select_units", [hod])
	camera.call("jump_to", hod.get("pos"))
	commands.call("set_page", "build_basic")
	await _frames(4)
	var b: Control = (card.get("buttons") as Array)[2]
	tip.call("hover", b, hud.call("card_tooltip", card.call("entry", 2)), card.get_global_rect())
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(4)
	await _shot("icons_build_page.png")
	tip.call("unhover", b)
	tip.set("_leave_t0", float(tip.get("_leave_t0")) - 1.0)
	# 2. the hall: its portrait and the Walled Burg upgrade in the queue
	world.call("spawn_unit", "kingdom_oath_hall", 0, hall_pos + Vector3(-14, 0, 9))
	world.call("issue", {"type": "research", "player": 0, "units": [hall.get("id")], "def": "kingdom_walled_burg"})
	for i in 30 * 4:
		world.call("step")
	sel.call("select_units", [hall])
	camera.call("jump_to", hall_pos)
	await _frames(4)
	await _shot("icons_hall_queue.png")
	# 3. a hero's inventory
	var hero: Node = world.call("spawn_unit", "kingdom_wheel_marshal", 0, hall_pos + Vector3(8, 0, 7))
	var items: Object = world.get("items")
	for iid: String in ["item_tin_gorget", "item_kingdom_linden_salve", "item_rosehip_draught", "item_firefly_jar", "item_fox_fur_mantle"]:
		items.call("give", hero, iid)
	sel.call("select_units", [hero])
	camera.call("jump_to", hero.get("pos"))
	await _frames(4)
	var inv: Control = hud.get("inventory")
	var ib: Control = (inv.get("buttons") as Array)[3]
	tip.call("hover", ib, inv.call("tooltip_for", 3), card.get_global_rect())
	tip.set("_hover_t0", float(tip.get("_hover_t0")) - 1.0)
	await _frames(4)
	await _shot("icons_inventory.png")
	tip.call("unhover", ib)
	tip.set("_leave_t0", float(tip.get("_leave_t0")) - 1.0)
	# 4. the Weighstall's stock, the hero beside it
	var shop: Node = null
	for u: Node in world.get("unit_list"):
		if str(u.get("def_id")) == "neutral_weighstall":
			shop = u
	if shop != null:
		hero.call("teleport", shop.get("pos") + Vector3(5, 0, 2))
		camera.call("jump_to", shop.get("pos"))
		for i in 3:
			world.call("step")
		sel.call("select_units", [shop])
		await _frames(6)
		await _shot("icons_shop.png")
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
