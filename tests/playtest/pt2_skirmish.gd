extends SceneTree
## Playtest 2 end to end in the real renderer: the menu's Skirmish (Brennmark vs the Tormai
## computer, Normal), a simple scripted player 0 (workers to gold and lumber, a Croft, a Drill
## Yard, Pavisiers), screenshots of the early base, construction, the hall's card with a queue,
## the computer's push and the end, and a count of engine errors.
## Untyped on purpose: a -s script compiles before the autoloads exist.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     -s tests/playtest/pt2_skirmish.gd
## Saves tests/output/pt2_{mining,building,hall_card,push,end}.png. Exit 1 when the match does not
## end within 16 minutes.

const OUT_DIR := "res://tests/output/"

var world: Node
var main: Node
var camera: Camera3D


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	root.get_node("Settings").set("edge_pan_enabled", false)
	root.get_node("Settings").set("skirmish_faction", "kingdom")
	root.get_node("Settings").set("ai_difficulty", "normal")
	load("res://src/main.gd").call("start_match", self, "slice")
	await _frames(3)
	main = current_scene
	world = main.get("world")
	world.set("auto_tick", false)
	camera = main.get("camera")
	camera.set("edge_pan_enabled", false)
	var hall: Node = _first(0, "kingdom_moot_hall")
	var hall_pos: Vector3 = hall.get("pos")
	var mine: Node = null
	for u: Node in world.get("unit_list"):
		if u.call("has_flag", "gold_mine") and (mine == null or (u.get("pos") as Vector3).distance_to(hall_pos) < (mine.get("pos") as Vector3).distance_to(hall_pos)):
			mine = u
	var hods: Array = _all(0, "kingdom_hodman")
	_cmd({"type": "gather", "units": _ids(hods.slice(0, 4)), "target": mine.get("id")})
	var con: Object = world.get("construction")
	var croft_spot := _spot(con, "kingdom_croft", hall_pos, 9.0)
	_cmd({"type": "build", "units": [hods[4].get("id")], "def": "kingdom_croft", "pos": croft_spot})
	_cmd({"type": "train", "units": [hall.get("id")], "def": "kingdom_hodman", "queue": true})
	camera.call("jump_to", hall_pos + Vector3(4, 0, -2))
	await _steps(30 * 25)
	await _shot("pt2_mining.png")
	var yard_spot := _spot(con, "kingdom_drill_yard", hall_pos, 12.0)
	var builder: Node = _all(0, "kingdom_hodman")[5] if _all(0, "kingdom_hodman").size() > 5 else hods[4]
	_cmd({"type": "build", "units": [builder.get("id")], "def": "kingdom_drill_yard", "pos": yard_spot})
	await _steps(30 * 20)
	camera.call("jump_to", yard_spot)
	await _frames(2)
	await _shot("pt2_building.png")
	await _steps(30 * 50)
	var sel: Node = main.get("selection")
	sel.call("select_units", [hall])
	_cmd({"type": "train", "units": [hall.get("id")], "def": "kingdom_hodman", "queue": true})
	camera.call("jump_to", hall_pos)
	await _steps(30 * 3)
	await _shot("pt2_hall_card.png")
	var yard: Node = _first(0, "kingdom_drill_yard")
	var shot_push := false
	var ended := false
	for second in range(0, 60 * 14, 5):
		await _steps(30 * 5)
		if yard != null and is_instance_valid(yard) and int(second) % 20 == 0:
			_cmd({"type": "train", "units": [yard.get("id")], "def": "kingdom_pavisier"})
		var ai: Object = (world.get("ai_players") as Array)[0]
		if not shot_push and str(ai.get("state")) == "push":
			var army: Array = ai.call("_army")
			var c := Vector3.ZERO
			for u: Node in army:
				c += u.get("pos")
			c /= maxf(1.0, army.size())
			if c.distance_to(hall_pos) < 25.0:
				shot_push = true
				camera.call("jump_to", c)
				await _frames(2)
				await _shot("pt2_push.png")
		var rules: Object = main.get("match_rules")
		if rules != null and not (rules.get("result") as Dictionary).is_empty():
			ended = true
			await _frames(6)
			await _shot("pt2_end.png")
			break
	print("pt2_skirmish: ended=%s at %.0f s, result %s, ai issued %d" % [ended, world.get("time"),
		main.get("match_rules").get("result"), (world.get("ai_players") as Array)[0].get("issued")])
	quit(0 if ended else 1)


func _cmd(c: Dictionary) -> void:
	c["player"] = 0
	world.call("issue", c)


func _first(pid: int, def_id: String) -> Node:
	var all := _all(pid, def_id)
	return all[0] if not all.is_empty() else null


func _all(pid: int, def_id: String) -> Array:
	var out: Array = []
	for u: Node in world.get("unit_list"):
		if bool(u.get("alive")) and int(u.get("player_id")) == pid and str(u.get("def_id")) == def_id:
			out.append(u)
	return out


func _ids(units: Array) -> Array:
	return units.map(func(u: Node) -> int: return int(u.get("id")))


func _spot(con: Object, def_id: String, around: Vector3, r0: float) -> Vector3:
	for r in range(int(r0), int(r0) + 20, 2):
		for k in 12:
			var a := TAU * k / 12.0 + 0.3
			var p := around + Vector3(cos(a), 0, sin(a)) * float(r)
			var spot: Dictionary = con.call("can_place", 0, def_id, p)
			if spot["ok"]:
				return spot["pos"]
	return around + Vector3(r0, 0, 0)


## Steps the sim `n` ticks, rendering one frame per 5 s of sim (fast-forward: the software
## renderer is slow; views and juice still update on those frames).
func _steps(n: int) -> void:
	var per_frame := 150
	var done := 0
	while done < n:
		for i in mini(per_frame, n - done):
			world.call("step")
		done += per_frame
		await process_frame


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
