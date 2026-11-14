extends SceneTree
## Renders one icon source per building (art bible §5.5 T9 "Kingdom / Clans unit or building": the
## building in its upper-third read) from the game's own view: a UnitView of the building, so the
## model, its add-ons (upgraded halls), the painterly structure shader, the team cloth and the
## placeholder of a model-less building all match what the player sees. Team cloth in the
## faction's first preferred colour (PlayerState.colour_for), neutrals white.
## Untyped on purpose: a -s script compiles before the autoloads exist.
## Run (software Vulkan):
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" \
##     godot --path . --rendering-driver vulkan --audio-driver Dummy -s tools/assets/render_building_icons.gd
## Writes assets_src/icons/buildings/renders/<id>.png (512 px, transparent background); then
## `python3 tools/assets/icon_sheets.py buildings` composites the 128 px game icons.

const OUT_DIR := "res://assets_src/icons/buildings/renders/"
const SIZE := 512
## Camera: in front of the door (+Z), a little to the left, looking down like a raised eye.
const PITCH_DEG := 24.0
const YAW_DEG := -28.0
const FOV := 26.0
const FILL := 0.9                ## share of the frame the building's bounds take


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var defs: Object = root.get_node("Defs")
	var only: Array = OS.get_cmdline_user_args()
	var vp := SubViewport.new()
	vp.size = Vector2i(SIZE, SIZE)
	vp.transparent_bg = true
	vp.msaa_3d = Viewport.MSAA_4X
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.78, 0.74, 0.68)
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.05
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)
	var key := DirectionalLight3D.new()
	key.light_energy = 1.35
	key.light_color = Color(1.0, 0.94, 0.84)
	key.rotation_degrees = Vector3(-48.0, -35.0, 0.0)       # from the upper left, in front
	vp.add_child(key)
	var fill := DirectionalLight3D.new()
	fill.light_energy = 0.35
	fill.light_color = Color(0.7, 0.8, 1.0)
	fill.rotation_degrees = Vector3(-20.0, 140.0, 0.0)      # cool back light for the silhouette
	vp.add_child(fill)
	var cam := Camera3D.new()
	cam.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF   # moved every frame, not per tick
	cam.fov = FOV
	cam.near = 0.1
	cam.far = 400.0
	vp.add_child(cam)
	cam.current = true
	var unit_script: Script = load("res://src/entities/unit.gd")
	var view_script: Script = load("res://src/entities/unit_view.gd")
	var ps: Script = load("res://src/systems/player_state.gd")
	var colours := {"kingdom": ps.call("colour_for", "kingdom", []), "clans": ps.call("colour_for", "clans", [])}
	var ids: Array = []
	for id: String in (defs.get("units") as Dictionary):
		var d: Dictionary = defs.call("unit", id)
		if str(d.get("kind", "")) in ["building", "resource"] and (only.is_empty() or only.has(id)):
			ids.append(id)
	ids.sort()
	for id: String in ids:
		var d: Dictionary = defs.call("unit", id)
		var u: Node3D = unit_script.new()
		u.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		var faction := str(d.get("faction", ""))
		var pid := 0 if colours.has(faction) else 13
		u.call("setup", null, 1, id, pid, Vector3.ZERO)
		var v: Node3D = view_script.new()
		u.add_child(v)
		vp.add_child(u)
		v.call("setup", u)
		u.process_mode = Node.PROCESS_MODE_DISABLED
		var tc: Color = colours.get(faction, Color.WHITE)
		v.call("_set_param", &"team_color", tc, true)
		v.call("_set_param", &"rim_col", Color(0, 0, 0, 0), true)
		v.call("_set_param", &"rim_boost", 0.0, true)
		for m: Variant in load("res://src/render/asset_library.gd").get("shader_materials"):
			(m as ShaderMaterial).set_shader_parameter(&"cloud_strength", 0.0)
		await process_frame
		var box := _bounds(u)
		if box.size == Vector3.ZERO:
			push_warning("no geometry for " + id)
			u.queue_free()
			continue
		_frame(cam, box)
		for i in 3:
			await process_frame
		await RenderingServer.frame_post_draw
		var img := vp.get_texture().get_image()
		var path := ProjectSettings.globalize_path(OUT_DIR + id + ".png")
		img.save_png(path)
		print("rendered ", id, " -> ", path)
		vp.remove_child(u)
		u.free()
	quit(0)


func _bounds(n: Node) -> AABB:
	var out := AABB()
	var first := true
	for g: Node in n.find_children("*", "GeometryInstance3D", true, false):
		var gi := g as GeometryInstance3D
		if gi == null or not gi.is_visible_in_tree():
			continue
		var b := gi.global_transform * gi.get_aabb()
		if b.size.length() < 0.001:
			continue
		out = b if first else out.merge(b)
		first = false
	return out


## Aims the camera at the box (a touch above its middle) and backs off until its corners fit
## (icon_sheets.py crops to the opaque pixels and centres them afterwards).
func _frame(cam: Camera3D, box: AABB) -> void:
	var dir := Vector3(sin(deg_to_rad(YAW_DEG)) * cos(deg_to_rad(PITCH_DEG)), sin(deg_to_rad(PITCH_DEG)),
		cos(deg_to_rad(YAW_DEG)) * cos(deg_to_rad(PITCH_DEG))).normalized()
	var aim := box.get_center() + Vector3(0, box.size.y * 0.06, 0)
	var dist := box.size.length() * 0.5 / sin(deg_to_rad(FOV * 0.5))
	cam.look_at_from_position(aim + dir * dist, aim, Vector3.UP)
	for step in 200:                                # back off until it fits...
		if _fits(cam, box):
			break
		dist /= 0.97
		cam.look_at_from_position(aim + dir * dist, aim, Vector3.UP)
	for step in 60:                                 # ...then close in while it still does
		cam.look_at_from_position(aim + dir * dist * 0.98, aim, Vector3.UP)
		if not _fits(cam, box):
			break
		dist *= 0.98
	cam.look_at_from_position(aim + dir * dist, aim, Vector3.UP)


func _projected(cam: Camera3D, box: AABB) -> Rect2:
	var r := Rect2()
	for i in 8:
		var p := cam.unproject_position(box.get_endpoint(i))
		r = Rect2(p, Vector2.ZERO) if i == 0 else r.expand(p)
	return r


func _fits(cam: Camera3D, box: AABB) -> bool:
	var r := _projected(cam, box)
	var margin := SIZE * (1.0 - FILL) * 0.5
	return r.position.x >= margin and r.position.y >= margin and r.end.x <= SIZE - margin and r.end.y <= SIZE - margin
