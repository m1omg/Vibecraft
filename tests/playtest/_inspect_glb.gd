extends SceneTree

func _init() -> void:
	var paths: Array[String] = []
	for dir in ["res://assets/models/units/", "res://assets/models/buildings/", "res://assets/models/neutral/"]:
		for f in DirAccess.get_files_at(dir):
			if f.ends_with(".glb"):
				paths.append(dir + f)
	for extra in ["res://assets/models/doodads/tree_hill_oak.glb", "res://assets/models/doodads/tree_linden.glb", "res://assets/models/doodads/tree_hazel.glb", "res://assets/models/doodads/tree_hill_oak_lod2.glb", "res://assets/models/doodads/tree_stump.glb", "res://assets/models/doodads/rock_boulder_large.glb", "res://assets/models/doodads/grass_tuft.glb"]:
		paths.append(extra)
	for p in paths:
		var ps := load(p) as PackedScene
		if ps == null:
			print(p, " LOAD FAIL")
			continue
		var n := ps.instantiate()
		var info := []
		var aabb := AABB()
		var first := true
		var mats := []
		var tris := 0
		var fmt := []
		for mi: MeshInstance3D in n.find_children("*", "MeshInstance3D", true, false):
			var m := mi.mesh
			var xf := _global(mi)
			var b := xf * m.get_aabb()
			aabb = b if first else aabb.merge(b)
			first = false
			for s in m.get_surface_count():
				var mat := m.surface_get_material(s)
				mats.append("%s(%s)" % [mat.resource_name if mat else "null", mat.get_class() if mat else ""])
				var arr := m.surface_get_arrays(s)
				tris += (arr[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3 if arr[Mesh.ARRAY_INDEX] != null else 0
				fmt.append("col=%s uv2=%s" % [arr[Mesh.ARRAY_COLOR] != null, arr[Mesh.ARRAY_TEX_UV2] != null])
		var ap := n.find_child("AnimationPlayer", true, false) as AnimationPlayer
		var anims := []
		if ap != null:
			for a in ap.get_animation_list():
				var an := ap.get_animation(a)
				anims.append("%s:%.2fs/loop%d" % [a, an.length, an.loop_mode])
		var sk := n.find_children("*", "Skeleton3D", true, false)
		print(p.get_file(), " aabb=", aabb, " tris=", tris, " mats=", mats, " fmt=", fmt.slice(0, 3), " anims=", anims, " skel=", sk.size(), " root=", n.get_class())
		n.free()
	quit()

func _global(n: Node) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var c := n
	while c != null and c is Node3D:
		xf = (c as Node3D).transform * xf
		c = c.get_parent()
	return xf
