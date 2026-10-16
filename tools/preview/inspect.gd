## Load one or more GLB files with GLTFDocument (exactly like a runtime load) and print a
## JSON report: meshes, triangle counts, materials/textures, skeleton, animations, bounds.
##
##   godot --headless --path tools/preview -s inspect.gd -- a.glb [b.glb ...]
##
## Output: a single line `VC_JSON:{...}` on stdout. Exit code 1 if any file failed to load.
extends SceneTree


func _initialize() -> void:
	var files := OS.get_cmdline_user_args()
	var reports: Array = []
	var failed := false
	for path in files:
		var rep := inspect(path)
		if rep.has("error"):
			failed = true
		reports.append(rep)
	print("VC_JSON:" + JSON.stringify({"files": reports}))
	quit(1 if failed else 0)


func inspect(path: String) -> Dictionary:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(path, state)
	if err != OK:
		return {"path": path, "error": "append_from_file failed: %s" % error_string(err)}
	var scene: Node = doc.generate_scene(state)
	if scene == null:
		return {"path": path, "error": "generate_scene returned null"}
	var rep := {"path": path, "nodes": 0, "meshes": [], "skeletons": [], "animations": [],
			"materials": [], "textures": []}
	var aabb := AABB()
	var have_aabb := false
	var mats := {}
	var stack: Array[Node] = [scene]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		rep.nodes += 1
		for c in n.get_children():
			stack.append(c)
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			var mesh := mi.mesh
			if mesh == null:
				continue
			var tris := 0
			var verts := 0
			for s in mesh.get_surface_count():
				var arrays := mesh.surface_get_arrays(s)
				var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				var pos: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				verts += pos.size()
				tris += (idx.size() if idx.size() > 0 else pos.size()) / 3
				var mat := mi.get_active_material(s)
				if mat != null and not mats.has(mat):
					mats[mat] = true
					var md := {"name": mat.resource_name, "class": mat.get_class()}
					if mat is BaseMaterial3D:
						var bm := mat as BaseMaterial3D
						for slot in [["albedo", BaseMaterial3D.TEXTURE_ALBEDO],
								["normal", BaseMaterial3D.TEXTURE_NORMAL],
								["roughness", BaseMaterial3D.TEXTURE_ROUGHNESS],
								["metallic", BaseMaterial3D.TEXTURE_METALLIC],
								["emission", BaseMaterial3D.TEXTURE_EMISSION],
								["ao", BaseMaterial3D.TEXTURE_AMBIENT_OCCLUSION]]:
							var tex := bm.get_texture(slot[1])
							if tex != null:
								md[slot[0] + "_tex"] = [tex.get_width(), tex.get_height()]
						md["transparency"] = bm.transparency
						md["albedo_color"] = bm.albedo_color.to_html()
						md["metallic"] = bm.metallic
						md["roughness"] = bm.roughness
					rep.materials.append(md)
			var skinned := mi.skin != null
			rep.meshes.append({"node": str(scene.get_path_to(mi)), "surfaces": mesh.get_surface_count(),
					"verts": verts, "tris": tris, "skinned": skinned})
			var gb := _mesh_to_scene(mi, scene) * mi.get_aabb()
			aabb = gb if not have_aabb else aabb.merge(gb)
			have_aabb = true
		elif n is Skeleton3D:
			var sk := n as Skeleton3D
			var names: Array = []
			for b in sk.get_bone_count():
				names.append(sk.get_bone_name(b))
			rep.skeletons.append({"node": str(scene.get_path_to(sk)), "bones": sk.get_bone_count(),
					"bone_names": names})
		elif n is AnimationPlayer:
			var ap := n as AnimationPlayer
			for an in ap.get_animation_list():
				var a := ap.get_animation(an)
				rep.animations.append({"name": str(an), "length": snappedf(a.length, 0.0001),
						"tracks": a.get_track_count(), "loop_mode": a.loop_mode})
	for t in state.get_images():
		if t != null:
			rep.textures.append({"name": t.resource_name, "size": [t.get_width(), t.get_height()]})
	rep["tris_total"] = 0
	for m in rep.meshes:
		rep.tris_total += m.tris
	if have_aabb:
		rep["aabb_pos"] = [snappedf(aabb.position.x, 0.0001), snappedf(aabb.position.y, 0.0001),
				snappedf(aabb.position.z, 0.0001)]
		rep["aabb_size"] = [snappedf(aabb.size.x, 0.0001), snappedf(aabb.size.y, 0.0001),
				snappedf(aabb.size.z, 0.0001)]
	scene.free()
	return rep


## Rest-pose transform from mesh space to scene space. For skinned meshes the
## MeshInstance3D transform is irrelevant: vertices go through bind pose + bone rest.
func _mesh_to_scene(mi: MeshInstance3D, top: Node) -> Transform3D:
	var skel := mi.get_node_or_null(mi.skeleton) as Skeleton3D
	if mi.skin != null and skel != null and mi.skin.get_bind_count() > 0:
		var skin := mi.skin
		var bone := skin.get_bind_bone(0)
		if bone < 0:
			bone = skel.find_bone(skin.get_bind_name(0))
		return _xform_to(skel, top) * skel.get_bone_global_rest(bone) * skin.get_bind_pose(0)
	return _xform_to(mi, top)


## Transform of `n` relative to `top` (nodes are not inside the tree here).
func _xform_to(n: Node3D, top: Node) -> Transform3D:
	var t := Transform3D.IDENTITY
	var cur: Node = n
	while cur != null and cur != top:
		if cur is Node3D:
			t = (cur as Node3D).transform * t
		cur = cur.get_parent()
	if top is Node3D:
		t = (top as Node3D).transform * t
	return t
