extends SceneTree
## Visual integration screenshots: the slice scene (main.tscn, scenario "slice": Wether Downs with
## its Gold Seams and neutral buildings, no start bases or camps) with both factions' real models
## placed near each start — kingdom (Emerald) at the south-west start, clans (Royal Blue) at the
## north-east — at default and close zoom, by day and by night, a ramp facing the camera, plus a
## clash in the middle. Saves tests/output/visual_*.png.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/screenshot_visual.gd [-- --only=day_default,night_close]
## Units the gameplay data does not define yet are registered from slice-content.json for the shot
## only (tests/playtest/slice_defs.gd). Everything is loaded at runtime (autoloads are not visible
## to -s scripts at compile time).

const OUT_DIR := "res://tests/output/"
const SliceDefs := preload("res://tests/playtest/slice_defs.gd")
const KINGDOM_ARMY := ["kingdom_pavisier", "kingdom_pavisier", "kingdom_pavisier", "kingdom_pavisier",
	"kingdom_hookgunner", "kingdom_hookgunner", "kingdom_hookgunner", "kingdom_linden_sister",
	"kingdom_wheel_marshal", "kingdom_firewright"]
const CLANS_ARMY := ["clans_grappler", "clans_grappler", "clans_grappler", "clans_grappler",
	"clans_javelineer", "clans_javelineer", "clans_javelineer", "clans_gustcaller",
	"clans_hero_uncut", "clans_hero_skymirror"]

var main: Node
var world: Node
var camera: Camera3D
var day_night: Node
var only: Array = []
var armies: Array = [[], []]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			only = a.trim_prefix("--only=").split(",")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	SliceDefs.register(root.get_node("Defs"))
	main = (load("res://src/main.tscn") as PackedScene).instantiate()
	main.set("spawn_skirmish", false)
	root.add_child(main)
	await process_frame
	world = main.get_node("World")
	camera = main.get_node("Camera")
	camera.set("edge_pan_enabled", false)
	day_night = world.get_node("DayNight")
	var m: Object = world.get("map")
	_spawn_kingdom(m.start_locations[0], m.gold_mines[0], m)
	_spawn_clans(m.start_locations[1], m.gold_mines[1], m)
	await _frames(3)
	var k_start: Vector3 = m.start_locations[0]
	var c_start: Vector3 = m.start_locations[1]
	var inward0 := _inward(k_start, m)
	# walk part of the kingdom army so walk cycles show
	var walkers: Array = []
	for i in range(0, armies[0].size(), 3):
		walkers.append(armies[0][i].id)
	world.issue({"type": "move", "player": 0, "units": walkers, "pos": k_start + inward0 * 13.0})
	main.get_node("UI/Selection").call("select_units", armies[0].slice(0, 6))

	await _shot("day_default", 10.0, k_start + inward0 * 4.0, 25.8)
	await _shot("day_close", 10.5, k_start + inward0 * 8.5, 18.75)
	await _shot("day_clans", 11.0, c_start + _inward(c_start, m) * 4.0, 25.8)
	await _shot("dusk_default", 17.6, k_start + inward0 * 4.0, 25.8)
	await _shot("night_default", 22.0, k_start + inward0 * 4.0, 25.8)
	await _shot("night_close", 22.5, c_start + _inward(c_start, m) * 8.5, 18.75)
	# cliffs and a ramp that climbs away from the camera (ascending towards -Z)
	var ramp: Dictionary = m.ramps[0]
	for r: Dictionary in m.ramps:
		if r["dir"] == Vector2i(0, -1):
			ramp = r
			break
	var rect: Rect2i = ramp["rect"]
	await _shot("day_cliffs", 14.0, Vector3((rect.position.x + rect.size.x * 0.5) * 2.0, 0,
		(rect.position.y + rect.size.y * 0.5) * 2.0 + 3.0), 25.8)
	# the clash: both armies meet in the middle
	if only.is_empty() or only.has("battle"):
		var mid := _open_ground(m, Vector3(96, 0, 96))
		# fresh armies, idle and within acquisition range: auto-acquire starts the fight
		armies = [[], []]
		_army(0, KINGDOM_ARMY, mid + Vector3(-3.4, 0, 1.2), Vector3(1, 0, 0), Vector3(0, 0, 1), -PI * 0.5)
		_army(1, CLANS_ARMY, mid + Vector3(3.4, 0, -1.2), Vector3(-1, 0, 0), Vector3(0, 0, -1), PI * 0.5)
		main.get_node("UI/Selection").call("select_units", [])
		await _frames(40)
		await _shot("battle", 13.0, mid, 21.0)
	print("ticks simulated: %d" % world.get("tick_count"))
	quit(0)


## Closest point to `near` with a 20 x 12 m patch of open, dry, level ground (spiral search).
func _open_ground(m: Object, near: Vector3) -> Vector3:
	var pathing: Object = world.get("pathing")
	for r in range(0, 60, 2):
		for k in 16:
			var a := TAU * k / 16.0
			var p := near + Vector3(cos(a), 0, sin(a)) * r
			var ok := true
			var h0: float = m.height_at(p.x, p.z)
			for dz in range(-6, 7, 2):
				for dx in range(-10, 11, 2):
					var q := p + Vector3(dx, 0, dz)
					if not pathing.call("is_walkable_world", q) or absf(m.height_at(q.x, q.z) - h0) > 0.2:
						ok = false
						break
				if not ok:
					break
			if ok:
				return p
	return near


func _inward(start: Vector3, m: Object) -> Vector3:
	var size: Vector2 = m.size_world()
	return (Vector3(size.x * 0.5, 0, size.y * 0.5) - start).normalized()


func _spawn_kingdom(start: Vector3, mine: Vector3, m: Object) -> void:
	var inward := _inward(start, m)
	var side := Vector3(-inward.z, 0, inward.x)
	var face := atan2(-inward.x, -inward.z)
	world.spawn_unit("kingdom_moot_hall", 0, start, face)
	world.spawn_unit("kingdom_drill_yard", 0, start + inward * 9.0 + side * 9.0, face)
	world.spawn_unit("kingdom_croft", 0, start - inward * 4.0 + side * 9.0, face)
	world.spawn_unit("kingdom_croft", 0, start - inward * 0.5 + side * 9.5, face)
	world.spawn_unit("kingdom_lookout", 0, start + inward * 12.0 - side * 5.0, face)
	_workers(0, "kingdom_hodman", start, mine)
	_army(0, KINGDOM_ARMY, start + inward * 8.0 - side * 1.0, inward, side, face)


func _spawn_clans(start: Vector3, mine: Vector3, m: Object) -> void:
	var inward := _inward(start, m)
	var side := Vector3(-inward.z, 0, inward.x)
	var face := atan2(-inward.x, -inward.z)
	world.spawn_unit("clans_shell_hall", 1, start, face)
	world.spawn_unit("clans_grapple_yard", 1, start + inward * 9.0 + side * 9.0, face)
	world.spawn_unit("clans_home_yurt", 1, start - inward * 4.0 + side * 9.0, face)
	world.spawn_unit("clans_home_yurt", 1, start - inward * 0.5 + side * 9.5, face)
	world.spawn_unit("clans_bow_mast", 1, start + inward * 12.0 - side * 5.0, face)
	_workers(1, "clans_yurtwright", start, mine)
	_army(1, CLANS_ARMY, start + inward * 8.0 - side * 1.0, inward, side, face)


func _workers(pid: int, def_id: String, start: Vector3, mine: Vector3) -> void:
	var to_mine := (mine - start).normalized()
	var mine_side := Vector3(-to_mine.z, 0, to_mine.x)
	var ids: Array = []
	for i in 5:
		var p := start + to_mine * 5.5 + mine_side * (i - 2) * 1.1
		ids.append(world.spawn_unit(def_id, pid, p, atan2(-to_mine.x, -to_mine.z)).id)
	world.issue({"type": "move", "player": pid, "units": ids.slice(0, 3), "pos": mine - to_mine * 3.5})


func _army(pid: int, defs: Array, centre: Vector3, inward: Vector3, side: Vector3, face: float) -> void:
	for i in defs.size():
		var row := float(i / 4)
		var col := float(i % 4) - 1.5
		var p := centre + side * col * 1.5 - inward * row * 1.6
		var u: Object = world.spawn_unit(defs[i], pid, p, face)
		if u != null:
			armies[pid].append(u)


func _shot(tag: String, hour: float, focus: Vector3, dist: float) -> void:
	if not only.is_empty() and not only.has(tag):
		return
	day_night.set("fixed_hour", hour)
	camera.set("distance", dist)
	camera.set("target_distance", dist)
	camera.call("jump_to", focus)
	await _frames(6)
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := ProjectSettings.globalize_path(OUT_DIR + "visual_%s.png" % tag)
	img.save_png(path)
	print("saved ", path)


func _frames(n: int) -> void:
	for i in n:
		await process_frame
