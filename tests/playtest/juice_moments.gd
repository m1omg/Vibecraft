extends SceneTree
## Signature-moment beat captures (juice bible §2, §5.4) on the slice map in the real main scene
## (HUD, camera, selection, command input, fx). Runs with a fixed frame time so every capture
## lands on its beat however slow the software renderer is:
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 \
##     --fixed-fps 60 -s tests/playtest/juice_moments.gd [-- --only=sm01,sm05]
## SM-01 (the first command): twelve Pavisiers are box-selected with real mouse events, then a
## right-click on open grass: captures at the box release (+33 ms: rings painting in from the
## drag corner), +300 ms (settled), the right-click (+17 ms: ripple rank 0 pulse and nod, the pin
## dropping), +150 ms (the ripple wave crossing the ranks, the pin landing with dust), +450 ms
## (push-off) and +1500 ms (the column marching).
## SM-05 (first contact and first fall): four Grapplers meet four Pavisiers: captures at the
## wind-up, the contact frame (latched flash, splinters, the clash dust ring, the bar ghost),
## +50 ms (knockback), +400 ms, then the first kill: the death beat, +300 ms (topple), +600 ms
## (body contact dust), +1500 ms (the team colour lowered).
## Saves tests/output/juice_<moment>_<beat>.png and prints the feel trace counters.

const OUT_DIR := "res://tests/output/"
const SliceDefs := preload("res://tests/playtest/slice_defs.gd")
const FPS := 60.0

var main: Node
var world: Node
var camera: Camera3D
var vfx: Node
var only: Array = []
var _hit_frame: int = -1
var _kill_frame: int = -1
var _kill_unit: Object = null


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
	await _frames(2)
	world = main.get_node("World")
	camera = main.get_node("Camera")
	camera.set("edge_pan_enabled", false)
	vfx = world.get_node("Fx/Vfx")
	world.get_node("DayNight").set("fixed_hour", 10.5)
	var m: Object = world.get("map")
	var field := _open_ground(m, Vector3(96, 0, 70))
	if only.is_empty() or only.has("sm01"):
		await _sm01(field)
	if only.is_empty() or only.has("sm05"):
		await _sm05(field + Vector3(0, 0, -6))
	if only.is_empty() or only.has("miss"):
		await _missiles(field + Vector3(0, 0, -6))
	print("juice_moments: fx stats ", vfx.get("particles").get("stats"), " marks live ",
		vfx.get("marks").get("live"), " clashes ", vfx.get("combat").get("clashes"))
	print("juice_moments: audio ", root.get_node("Audio").get("stats"))
	quit(0)


# --- SM-01 -----------------------------------------------------------------------------------

func _sm01(centre: Vector3) -> void:
	var units: Array = []
	for i in 12:
		var row := float(i / 4)
		var col := float(i % 4) - 1.5
		units.append(world.spawn_unit("kingdom_pavisier", 0, centre + Vector3(col * 1.4, 0, row * 1.5 - 1.5), 0.0))
	_look(centre + Vector3(1.5, 0, -2.5), 25.8)
	await _frames(20)
	# the box: from above-left of the block to below-right, with real mouse events
	var a := camera.unproject_position(centre + Vector3(-3.6, 0, -3.4))
	var b := camera.unproject_position(centre + Vector3(3.6, 0, 2.8))
	_mouse(MOUSE_BUTTON_LEFT, a, true)
	await _frames(1)
	for k in range(1, 5):
		_motion(a.lerp(b, k / 4.0))
		await _frames(1)
	await _frames(4)
	_mouse(MOUSE_BUTTON_LEFT, b, false)
	await _frames(2)
	await _capture("sm01_0a_box_release_33ms")
	await _frames(16)
	await _capture("sm01_0b_rings_settled_300ms")
	await _frames(17)
	var goal := centre + Vector3(2.0, 0, -11.0)
	_mouse(MOUSE_BUTTON_RIGHT, camera.unproject_position(goal), true)
	_mouse(MOUSE_BUTTON_RIGHT, camera.unproject_position(goal), false)
	await _frames(1)
	await _capture("sm01_1a_right_click_17ms")
	await _frames(8)
	await _capture("sm01_1b_ripple_wave_150ms")
	await _frames(18)
	await _capture("sm01_1c_push_off_450ms")
	await _frames(63)
	await _capture("sm01_1d_marching_1500ms")
	main.get_node("UI/Selection").call("clear")
	for u: Object in units:
		world.call("remove_unit", u)
	await _frames(4)


# --- SM-05 -----------------------------------------------------------------------------------

func _sm05(centre: Vector3) -> void:
	var pav: Array = []
	var grap: Array = []
	for i in 4:
		pav.append(world.spawn_unit("kingdom_pavisier", 0, centre + Vector3(-1.6, 0, (i - 1.5) * 1.5), -PI * 0.5))
		grap.append(world.spawn_unit("clans_grappler", 1, centre + Vector3(3.2, 0, (i - 1.5) * 1.5), PI * 0.5))
	_look(centre + Vector3(0.8, 0, 1.6), 18.75)
	Events_connect()
	# wait for the first wind-up near contact
	var shot_windup := false
	for f in 600:
		await _frames(1)
		if not shot_windup:
			for g: Object in grap:
				var s: float = g.call("swing_progress")
				if s >= 0.0 and s >= float(g.call("damage_point_ratio")) - 0.12:
					shot_windup = true
					await _capture("sm05_a0_windup")
					break
		if _hit_frame >= 0:
			break
	if _hit_frame < 0:
		push_error("juice_moments: no melee contact")
		return
	await _capture_now("sm05_a1_contact")
	await _frames(3)
	await _capture("sm05_a2_knockback_50ms")
	await _frames(21)
	await _capture("sm05_a3_settled_400ms")
	# the first fall: leave the next Grappler blow lethal for one Pavisier
	var victim: Object = null
	for p: Object in pav:
		if p.get("alive"):
			victim = p
			break
	if victim == null:
		return
	victim.set("hp", 1.0)
	_kill_unit = victim
	for f in 600:
		await _frames(1)
		if _kill_frame >= 0:
			break
	if _kill_frame < 0:
		push_error("juice_moments: no kill")
		return
	await _capture_now("sm05_b0_death_beat")
	await _frames(18)
	await _capture("sm05_b1_topple_300ms")
	await _frames(18)
	await _capture("sm05_b2_body_contact_600ms")
	await _frames(54)
	await _capture("sm05_b3_flag_lowered_1500ms")


# --- missiles (CMB-24/25/26): release tells, trails, sticking ------------------------------------

func _missiles(centre: Vector3) -> void:
	for u: Object in (world.get("unit_list") as Array).duplicate():
		if u.get("player_id") in [0, 1]:
			world.call("remove_unit", u)
	await _frames(2)
	var hold: Array = []
	for i in 3:
		hold.append(world.spawn_unit("kingdom_pavisier", 0, centre + Vector3(-4.0, 0, (i - 1) * 1.6), -PI * 0.5).id)
	for i in 2:
		hold.append(world.spawn_unit("kingdom_hookgunner", 0, centre + Vector3(-6.0, 0, (i - 0.5) * 2.0), -PI * 0.5).id)
	var jav: Array = []
	for i in 3:
		jav.append(world.spawn_unit("clans_javelineer", 1, centre + Vector3(4.5, 0, (i - 1) * 1.8), PI * 0.5).id)
	world.issue({"type": "hold", "player": 0, "units": hold})
	world.issue({"type": "hold", "player": 1, "units": jav})
	_look(centre + Vector3(0.0, 0, 1.6), 18.75)
	var root3: Node = world.get("projectile_root")
	for f in 900:
		await _frames(1)
		if root3.get_child_count() > 0:
			break
	await _capture_now("miss_0_release")
	await _frames(8)
	await _capture("miss_1_flight_150ms")
	for f in 240:
		await _frames(1)
		if int(vfx.get("missiles").get("stuck_count")) >= 2:
			break
	await _capture("miss_2_stuck")
	await _frames(60)
	await _capture("miss_3_volleys_1s")


func Events_connect() -> void:
	var ev := root.get_node("Events")
	ev.connect("unit_damaged", func(u: Object, _a: float, src: Object) -> void:
		if _hit_frame < 0 and src != null and (src.get("projectile") as Dictionary).is_empty():
			_hit_frame = Engine.get_process_frames())
	ev.connect("unit_died", func(u: Object, _k: Object) -> void:
		if _kill_frame < 0 and u == _kill_unit:
			_kill_frame = Engine.get_process_frames())


# --- helpers ---------------------------------------------------------------------------------

func _look(focus: Vector3, dist: float) -> void:
	camera.set("distance", dist)
	camera.set("target_distance", dist)
	camera.call("jump_to", focus)


func _mouse(button: int, pos: Vector2, pressed: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	ev.position = pos
	ev.global_position = pos
	ev.pressed = pressed
	root.push_input(ev, true)


func _motion(pos: Vector2) -> void:
	var ev := InputEventMouseMotion.new()
	ev.position = pos
	ev.global_position = pos
	root.warp_mouse(pos)
	root.push_input(ev, true)


## Closest point to `near` with a 20 x 16 m patch of open, dry, level ground.
func _open_ground(m: Object, near: Vector3) -> Vector3:
	var pathing: Object = world.get("pathing")
	for r in range(0, 60, 2):
		for k in 16:
			var a := TAU * k / 16.0
			var p := near + Vector3(cos(a), 0, sin(a)) * r
			var ok := true
			var h0: float = m.height_at(p.x, p.z)
			for dz in range(-14, 7, 2):
				for dx in range(-8, 9, 2):
					var q := p + Vector3(dx, 0, dz)
					if not pathing.call("is_walkable_world", q) or absf(m.height_at(q.x, q.z) - h0) > 0.25:
						ok = false
						break
				if not ok:
					break
			if ok:
				return p
	return near


## Renders the next frame and saves it.
func _capture(tag: String) -> void:
	await _frames(1)
	await _capture_now(tag)


## Saves the frame being drawn now.
func _capture_now(tag: String) -> void:
	if not only.is_empty() and not (only.has(tag.substr(0, 4)) or only.has(tag)):
		return
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	if img == null:
		return
	var path := ProjectSettings.globalize_path(OUT_DIR + "juice_%s.png" % tag)
	img.save_png(path)
	print("saved %s (frame %d, ui %.3f, fx %.3f, tick %d)" % [path, Engine.get_process_frames(),
		FxClock.ui_now, FxClock.fx_now, world.get("tick_count")])


func _frames(n: int) -> void:
	for i in n:
		await process_frame
