## Team-colour coverage masks for tools/kits/buildings.py (run inside tools/preview):
##
##   xvfb-run -a godot --rendering-driver vulkan --path tools/preview \
##       -s /abs/path/tools/kits/buildings_teammask.gd -- --spec masks.json
##
## masks.json: {"size": 512, "pitch": 56, "fov": 30,
##   "shots": [{"glbs": ["/abs/a.glb", ...], "out": "/abs/a_0.png", "yaw": 0, "target": [x, y, z], "distance": d}]}
## Each shot renders the model alone from the RTS pitch with unshaded flat colours: TEAM materials
## red, everything else green, background black. buildings.py counts the pixels (visible team
## fraction of the silhouette, art bible 3.1).
extends SceneTree

var spec := {}


func _initialize() -> void:
	var a := OS.get_cmdline_user_args()
	var path := ""
	for i in a.size():
		if a[i] == "--spec" and i + 1 < a.size():
			path = a[i + 1]
	var f := FileAccess.open(path, FileAccess.READ)
	spec = JSON.parse_string(f.get_as_text())
	f.close()
	_run()


func _flat(col: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = col
	return m


func _paint(n: Node, team: Material, other: Material) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			var is_team := mat != null and mat.resource_name.contains("TEAM")
			mi.set_surface_override_material(s, team if is_team else other)
	for c in n.get_children():
		_paint(c, team, other)


func _run() -> void:
	await process_frame
	var size := int(spec.get("size", 512))
	var vp := SubViewport.new()
	vp.size = Vector2i(size, size)
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)
	var world := Node3D.new()
	vp.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var cam := Camera3D.new()
	cam.fov = float(spec.get("fov", 30.0))
	cam.near = 0.05
	cam.far = 500.0
	vp.add_child(cam)
	cam.current = true
	var team := _flat(Color(1, 0, 0))
	var other := _flat(Color(0, 1, 0))
	var pitch := deg_to_rad(float(spec.get("pitch", 56.0)))
	for shot in spec["shots"]:
		var node := Node3D.new()
		world.add_child(node)
		for g in shot.get("glbs", [shot["glb"]]):
			var doc := GLTFDocument.new()
			var st := GLTFState.new()
			if doc.append_from_file(str(g), st) != OK:
				printerr("failed to load ", g)
				continue
			node.add_child(doc.generate_scene(st))
		_paint(node, team, other)
		var t: Array = shot["target"]
		var target := Vector3(t[0], t[1], t[2])
		var yaw := deg_to_rad(float(shot.get("yaw", 0.0)))
		var off := Basis(Vector3.UP, yaw) * Vector3(0.0, sin(pitch), -cos(pitch)) * float(shot["distance"])
		cam.look_at_from_position(target + off, target, Vector3.UP)
		for i in 3:
			await process_frame
		await RenderingServer.frame_post_draw
		vp.get_texture().get_image().save_png(str(shot["out"]))
		world.remove_child(node)
		node.queue_free()
	print("VC_MASKS_OK")
	quit(0)
