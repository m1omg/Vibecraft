class_name ProcMesh
## Helpers that merge Godot primitive meshes into one vertex-coloured ArrayMesh surface.
## Used for placeholder art (trees, props) so MultiMesh can draw a whole model in one call.


## parts: Array of {mesh: PrimitiveMesh, xform: Transform3D, color: Color}
static func merge(parts: Array) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	for part: Dictionary in parts:
		var arrays: Array = (part["mesh"] as PrimitiveMesh).get_mesh_arrays()
		var xf: Transform3D = part.get("xform", Transform3D.IDENTITY)
		var col: Color = part.get("color", Color.WHITE)
		var base := verts.size()
		var pv: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var pn: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var nb := xf.basis.inverse().transposed()
		for i in pv.size():
			verts.append(xf * pv[i])
			normals.append((nb * pn[i]).normalized())
			colors.append(col)
		var pi: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for i in pi.size():
			indices.append(base + pi[i])
	var out := []
	out.resize(Mesh.ARRAY_MAX)
	out[Mesh.ARRAY_VERTEX] = verts
	out[Mesh.ARRAY_NORMAL] = normals
	out[Mesh.ARRAY_COLOR] = colors
	out[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, out)
	return mesh


static func cylinder(top_r: float, bottom_r: float, h: float, segments: int = 8) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = top_r
	c.bottom_radius = bottom_r
	c.height = h
	c.radial_segments = segments
	c.rings = 1
	return c


static func sphere(r: float, segments: int = 10, rings: int = 6) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = segments
	s.rings = rings
	return s


static func at(p: Vector3, scale: Vector3 = Vector3.ONE, yaw: float = 0.0) -> Transform3D:
	return Transform3D(Basis(Vector3.UP, yaw).scaled(scale), p)
