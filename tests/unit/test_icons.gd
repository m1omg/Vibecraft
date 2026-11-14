extends "res://tests/test_case.gd"
## Game icons (IconLibrary; art bible §5.5 T9): every item, building and shop service has one at
## 128 px with mipmaps, and the HUD shows them: the command card (build page, shop stock), the
## inventory, the production queue, the portrait and the selection grid.

var main: Node
var world: World
var sel: Selection
var commands: CommandInput
var hud: Hud


func _setup_main() -> void:
	Settings.edge_pan_enabled = false
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("scenario", "slice")
	tree.root.add_child(main)
	track(main)
	await tree.process_frame
	world = main.world
	world.auto_tick = false
	sel = main.selection
	commands = main.commands
	hud = main.hud
	world.player(0).gold = 5000
	world.player(0).lumber = 5000


func after_each() -> void:
	Settings.edge_pan_enabled = true
	cleanup()


func test_every_item_building_and_service_has_an_icon() -> void:
	var missing: Array[String] = []
	for id: String in Defs.items:
		if not id.begins_with("dummy_") and not IconLibrary.has(id):      # dummy_: data/test_defs.json
			missing.append(id)
	for id: String in Defs.unit_ids():
		var kind := str(Defs.unit(id).get("kind", ""))
		if (kind == "building" or kind == "resource") and not id.begins_with("dummy_") and not IconLibrary.has(id):
			missing.append(id)
	for shop_id: String in Defs.shops:
		for s: Variant in Defs.shop(shop_id).get("services", []):
			if not IconLibrary.has(str(s)):
				missing.append(str(s))
	assert_eq(missing, [] as Array[String], "every item, building and service has an icon")
	assert_eq(IconLibrary.texture("kingdom_hodman"), null, "units keep their coloured face for now")


func test_icons_are_128_px_with_mipmaps_and_a_grey_copy() -> void:
	for id: String in ["item_rosehip_draught", "kingdom_moot_hall", "neutral_fair_exchange_gold"]:
		var tex := IconLibrary.texture(id)
		assert_eq(Vector2i(tex.get_size()), Vector2i(128, 128), id + " is 128 px")
		assert_true(tex.get_image().has_mipmaps(), id + " has mipmaps (drawn at 40-60 px)")
	var grey := IconLibrary.grey("item_rosehip_draught")
	var c := grey.get_image().get_pixel(64, 64)
	assert_true(absf(c.r - c.g) < 0.02 and absf(c.g - c.b) < 0.02, "the grey copy has no colour")
	assert_eq(IconLibrary.grey("item_rosehip_draught"), grey, "made once")
	assert_eq(IconLibrary.texture("neutral_inn_revive"), IconLibrary.texture("neutral_coaching_inn"), "the inn's revive borrows the inn")


func test_the_hud_shows_icons() -> void:
	await _setup_main()
	var hall: Unit = null
	for u in world.unit_list:
		if u.player_id == 0 and u.def_id == "kingdom_moot_hall":
			hall = u
	# the portrait and the queue: a hall upgrading to the Walled Burg
	sel.select_units([hall])
	await tree.process_frame
	assert_true(hud.portrait_icon.texture != null and hud.portrait_label.text == "", "the hall's icon in the portrait")
	world.spawn_unit("kingdom_oath_hall", 0, hall.pos + Vector3(-14, 0, 9))
	world.issue({"type": "research", "player": 0, "units": [hall.id], "def": "kingdom_walled_burg"})
	world.step()
	hud.queue_panel.refresh(hall)
	assert_true(hud.queue_panel.visible, "the upgrade is queued")
	var q: CardButton = hud.queue_panel.buttons[0]
	assert_eq(q.icon_tex, IconLibrary.texture("kingdom_walled_burg"), "the upgrade's icon in the queue")
	assert_eq(q.text, "", "without initials")
	# the inventory and a shop card
	var hero := world.spawn_unit("kingdom_wheel_marshal", 0, hall.pos + Vector3(8, 0, 6))
	for i in hero.inventory.size():
		hero.inventory[i] = null
	world.items.give(hero, "item_tin_gorget")
	sel.select_units([hero])
	await tree.process_frame
	hud.inventory._refresh()
	var slot: CardButton = hud.inventory.buttons[0]
	assert_eq(slot.icon_tex, IconLibrary.texture("item_tin_gorget"), "the item's icon in its slot")
	assert_eq(slot.text, "", "no label over it")
	assert_eq(hud.inventory.buttons[1].icon_tex, null, "an empty slot stays empty")
	var shop := world.spawn_unit("neutral_weighstall", PlayerState.NEUTRAL_PASSIVE, hall.pos + Vector3(20, 0, -10))
	hero.teleport(shop.pos + Vector3(5, 0, 0))
	sel.select_units([shop])
	await tree.process_frame
	var b0: CardButton = hud.card.buttons[0]
	assert_eq(b0.icon_tex, IconLibrary.texture("item_rosehip_draught"), "the shop's stock as icons")
	# the selection grid
	var crofts: Array[Unit] = []
	for i in 2:
		crofts.append(world.spawn_unit("kingdom_croft", 0, hall.pos + Vector3(-20 + i * 6, 0, -12)))
	sel.select_units(crofts)
	await tree.process_frame
	var grid_btn: Button = hud.get("_icons")[0]
	assert_eq(grid_btn.icon, IconLibrary.texture("kingdom_croft"), "the selection grid shows the icon")
	assert_eq(grid_btn.text, "", "without initials")
