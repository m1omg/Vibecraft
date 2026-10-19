## Line-up renderer for tools/kits/buildings.py (run inside tools/preview):
##
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a godot --rendering-driver vulkan \
##       --path tools/preview -s /abs/path/tools/kits/buildings_lineup.gd -- --spec layout.json
##
## layout.json: {"out": "frame.png", "anchors": "anchors.json", "size": [W, H], "pitch": 56, "fov": 22,
##   "target": [x, y, z], "distance": D, "ground": "/abs/gv_meadow.png",
##   "items": [{"glb": "/abs/a.glb", "pos": [x, y, z], "yaw": deg, "scale": s, "team": "#rrggbb", "clip": "idle"}],
##   "labels": [{"label": "text", "sub": "small text", "world": [x, y, z]}]}
## Models face -Z; the camera looks at their fronts from -Z (high three-quarter, like the "rts"
## cell of render_preview.py). Materials whose name contains TEAM get the item's team colour the
## way UnitView does (albedo_color). Writes the frame and the screen position of each item's label
## anchor (a point in front of its footprint).
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


func _run() -> void:
	await process_frame
	var size: Array = spec.get("size", [2400, 1400])
	var vp := SubViewport.new()
	vp.size = Vector2i(int(size[0]), int(size[1]))
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.msaa_3d = Viewport.MSAA_4X
	vp.positional_shadow_atlas_size = 4096
	root.add_child(vp)
	var world := Node3D.new()
	vp.add_child(world)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.36, 0.42, 0.50)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#9DB3D6")
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_color = Color("#FFF0D8")
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 220.0
	world.add_child(sun)
	# key light from the screen's lower left, elevation ~52 deg (art bible 1.5)
	sun.rotation = Vector3(deg_to_rad(-52.0), deg_to_rad(-150.0), 0.0)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(600, 600)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.roughness = 1.0
	var gpath: String = spec.get("ground", "")
	if gpath != "" and FileAccess.file_exists(gpath):
		var img := Image.load_from_file(gpath)
		img.generate_mipmaps()
		gm.albedo_texture = ImageTexture.create_from_image(img)
		gm.uv1_triplanar = true
		gm.uv1_world_triplanar = true
		gm.uv1_scale = Vector3(0.25, 0.25, 0.25)
		gm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	else:
		gm.albedo_color = Color(0.36, 0.45, 0.26)
	ground.material_override = gm
	world.add_child(ground)

	for it in spec["items"]:
		var doc := GLTFDocument.new()
		var st := GLTFState.new()
		if doc.append_from_file(str(it["glb"]), st) != OK:
			printerr("failed to load ", it["glb"])
			continue
		var node := doc.generate_scene(st)
		var holder := Node3D.new()
		world.add_child(holder)
		holder.add_child(node)
		var p: Array = it.get("pos", [0, 0, 0])
		holder.position = Vector3(p[0], p[1], p[2])
		holder.rotation.y = deg_to_rad(float(it.get("yaw", 0.0)))
		var s := float(it.get("scale", 1.0))
		holder.scale = Vector3(s, s, s)
		if it.has("team"):
			_tint(node, Color(str(it["team"])))
		var ap := node.find_child("AnimationPlayer", true, false) as AnimationPlayer
		if ap != null:
			var clip := str(it.get("clip", "idle"))
			if ap.has_animation(clip):
				ap.play(clip)
				ap.seek(0.3, true)
				ap.pause()

	var cam := Camera3D.new()
	cam.fov = float(spec.get("fov", 22.0))
	cam.near = 0.5
	cam.far = 1000.0
	vp.add_child(cam)
	var tgt: Array = spec.get("target", [0, 0, 0])
	var target := Vector3(tgt[0], tgt[1], tgt[2])
	var pitch := deg_to_rad(float(spec.get("pitch", 56.0)))
	var dist := float(spec.get("distance", 80.0))
	# camera on the -Z side (in front of the -Z facing models), looking towards +Z and down
	var offset := Vector3(0.0, sin(pitch), -cos(pitch)) * dist
	cam.look_at_from_position(target + offset, target, Vector3.UP)
	cam.current = true
	for i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	var img2 := vp.get_texture().get_image()
	img2.save_png(str(spec["out"]))
	var out_anchors := []
	for an in spec.get("labels", []):
		var w: Array = an["world"]
		var sp := cam.unproject_position(Vector3(w[0], w[1], w[2]))
		out_anchors.append({"label": an["label"], "sub": an["sub"], "x": sp.x, "y": sp.y})
	var fa := FileAccess.open(str(spec["anchors"]), FileAccess.WRITE)
	fa.store_string(JSON.stringify(out_anchors))
	fa.close()
	print("VC_LINEUP_OK")
	quit(0)


func _tint(n: Node, col: Color) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			if mat != null and mat.resource_name.contains("TEAM") and mat is StandardMaterial3D:
				var m2 := (mat as StandardMaterial3D).duplicate() as StandardMaterial3D
				m2.albedo_color = col
				mi.set_surface_override_material(s, m2)
	for c in n.get_children():
		_tint(c, col)
