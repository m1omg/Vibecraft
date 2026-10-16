## Render QA frames of a GLB (used by tools/render_preview.py, which also builds the labelled
## contact sheet). Needs a real renderer, e.g. under Xvfb with lavapipe:
##
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a godot \
##       --rendering-driver vulkan --path tools/preview -s turntable.gd -- \
##       --glb model.glb --out-dir /tmp/frames [--size 384] [--fractions 0,0.5] [--clips all]
##
## Writes <out-dir>/NN_<label>.png for 4 static views (rts, front, side, back34), an in-game
## scale crop (real RTS camera: pitch 56, FOV 47, 26 m away, 1920x1080 -> 256 px crop), and
## frames of every animation clip at the requested fractions of its length, plus meta.json.
## Scene: neutral sky, sun with shadows, ground grid (1 m lines, darker 2 m TILE lines),
## a 1.8 m reference capsule and a red arrow on the ground pointing to -Z (model forward).
## Materials whose name contains TEAM are tinted with --team-color (default blue) like UnitView.
extends SceneTree

## [label, camera yaw relative to the model's front (deg, CCW from above), pitch (deg)]
const VIEWS := [
	["rts", 0.0, 56.0],
	["front", 0.0, 6.0],
	["side", -90.0, 6.0],
	["back34", -145.0, 25.0],
]
const ANIM_VIEW := [35.0, 20.0]

var o := {
	"glb": "", "out_dir": "", "size": 384, "fractions": "0,0.5", "clips": "all", "fov": 30.0,
	"game_dist": 26.0, "game_fov": 47.0, "game_pitch": 56.0, "no_ingame": false, "team_color": "#2f6bff",
}
var vp: SubViewport
var cam: Camera3D
var world: Node3D
var model: Node3D
var capsule: MeshInstance3D
var shot_idx := 0
var meta := {"views": [], "clips": [], "ingame": null, "errors": []}


func _initialize() -> void:
	_parse_args()
	_run()


func _parse_args() -> void:
	var a := OS.get_cmdline_user_args()
	var i := 0
	while i < a.size():
		var k: String = a[i].trim_prefix("--").replace("-", "_")
		if k == "no_ingame":
			o[k] = true
			i += 1
			continue
		if i + 1 < a.size() and o.has(k):
			var v: String = a[i + 1]
			o[k] = v.to_float() if typeof(o[k]) == TYPE_FLOAT else (v.to_int() if typeof(o[k]) == TYPE_INT else v)
		i += 2


func _run() -> void:
	await process_frame
	if o.glb == "" or o.out_dir == "":
		printerr("usage: -- --glb FILE --out-dir DIR [--size N] [--fractions 0,0.5] [--clips all|a,b]")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(o.out_dir)
	_build_stage()
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	var err := doc.append_from_file(o.glb, st)
	if err != OK:
		printerr("failed to load %s: %s" % [o.glb, error_string(err)])
		quit(1)
		return
	model = doc.generate_scene(st)
	world.add_child(model)
	meta["team_surfaces"] = _tint_team(model, Color(o.team_color))
	await process_frame
	var ab := _model_aabb()
	meta["aabb_pos"] = [ab.position.x, ab.position.y, ab.position.z]
	meta["aabb_size"] = [ab.size.x, ab.size.y, ab.size.z]
	_place_props(ab)

	# --- static views (model at rest / first frame of nothing)
	var ap := _find_anim_player()
	var cap_ab := AABB(capsule.position - Vector3(0.3, 0.9, 0.3), Vector3(0.6, 1.8, 0.6))
	var frame_ab := ab.merge(cap_ab)
	for v in VIEWS:
		_frame_camera(frame_ab, v[1], v[2], o.fov)
		await _shot(v[0], "view")

	# --- in-game scale crop
	if not o.no_ingame:
		await _ingame(ab)

	# --- animation clips
	if ap != null:
		capsule.visible = false
		var wanted: PackedStringArray = [] if o.clips == "all" else o.clips.split(",")
		var fr: Array = []
		for f in o.fractions.split(","):
			fr.append(clampf(f.to_float(), 0.0, 1.0))
		for an in ap.get_animation_list():
			if not wanted.is_empty() and not wanted.has(str(an)):
				continue
			var anim := ap.get_animation(an)
			var clip := {"name": str(an), "length": anim.length, "frames": []}
			ap.play(an, -1, 0.0)
			var cab := await _clip_aabb(ap, anim.length, ab)
			for f in fr:
				var t: float = anim.length * f
				if f >= 1.0:
					t = maxf(anim.length - 0.001, 0.0)
				ap.seek(t, true)
				_frame_camera(cab, ANIM_VIEW[0], ANIM_VIEW[1], o.fov)
				var file := await _shot("%s_%d" % [an, int(round(f * 100))], "clip")
				clip.frames.append({"file": file, "fraction": f, "time": t})
			meta.clips.append(clip)
		ap.stop()
	var fa := FileAccess.open(o.out_dir.path_join("meta.json"), FileAccess.WRITE)
	fa.store_string(JSON.stringify(meta, "  "))
	fa.close()
	print("VC_FRAMES:" + o.out_dir)
	quit(0)


func _build_stage() -> void:
	vp = SubViewport.new()
	vp.size = Vector2i(o.size, o.size)
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.msaa_3d = Viewport.MSAA_4X
	vp.positional_shadow_atlas_size = 2048
	root.add_child(vp)
	world = Node3D.new()
	vp.add_child(world)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.30, 0.34, 0.40)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.78, 0.80, 0.88)
	env.ambient_light_energy = 0.5
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_energy = 1.15
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	world.add_child(sun)
	sun.look_at_from_position(Vector3(-4.0, 7.0, -5.0), Vector3.ZERO, Vector3.UP)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(400, 400)
	ground.mesh = pm
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode cull_disabled;
varying vec3 wp;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
float grid(vec2 p) {
	vec2 g = abs(fract(p - 0.5) - 0.5) / max(fwidth(p), vec2(1e-4));
	return 1.0 - min(min(g.x, g.y), 1.0);
}
void fragment() {
	vec3 c = vec3(0.20, 0.215, 0.19);
	c = mix(c, vec3(0.19, 0.21, 0.19), grid(wp.xz) * 0.8);
	c = mix(c, vec3(0.10, 0.11, 0.10), grid(wp.xz * 0.5));
	ALBEDO = c;
	ROUGHNESS = 1.0;
}
"""
	var mat := ShaderMaterial.new()
	mat.shader = sh
	ground.material_override = mat
	world.add_child(ground)

	capsule = MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = 0.3
	cm.height = 1.8
	capsule.mesh = cm
	var cmat := StandardMaterial3D.new()
	cmat.albedo_color = Color(0.55, 0.62, 0.78)
	cmat.roughness = 0.7
	capsule.material_override = cmat
	world.add_child(capsule)

	cam = Camera3D.new()
	cam.fov = o.fov
	cam.near = 0.02
	cam.far = 600.0
	vp.add_child(cam)
	cam.current = true


func _place_props(ab: AABB) -> void:
	# capsule beside the model, diagonally back-left so no view is occluded
	capsule.position = Vector3(ab.position.x - 0.6, 0.9, ab.end.z + 0.35)
	# arrow on the ground in front of the model, pointing to -Z (model forward)
	var L := clampf(maxf(ab.size.x, ab.size.z) * 0.35, 0.25, 2.0)
	var z0 := ab.position.z - 0.08
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_normal(Vector3.UP)
	var cx := ab.get_center().x
	st.add_vertex(Vector3(cx - L * 0.3, 0.01, z0))
	st.add_vertex(Vector3(cx + L * 0.3, 0.01, z0))
	st.add_vertex(Vector3(cx, 0.01, z0 - L))
	var arrow := MeshInstance3D.new()
	arrow.mesh = st.commit()
	var am := StandardMaterial3D.new()
	am.albedo_color = Color(0.9, 0.15, 0.1)
	am.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	am.cull_mode = BaseMaterial3D.CULL_DISABLED
	arrow.material_override = am
	world.add_child(arrow)


## Like UnitView: materials whose name contains TEAM get the player colour (albedo multiply).
func _tint_team(n: Node, col: Color) -> int:
	var count := 0
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.mesh != null:
			for s in mi.mesh.get_surface_count():
				var mat := mi.mesh.surface_get_material(s)
				if mat != null and mat.resource_name.contains("TEAM") and mat is StandardMaterial3D:
					var m2 := (mat as StandardMaterial3D).duplicate() as StandardMaterial3D
					m2.albedo_color = col
					mi.set_surface_override_material(s, m2)
					count += 1
	for c in n.get_children():
		count += _tint_team(c, col)
	return count


func _find_anim_player() -> AnimationPlayer:
	var found := model.find_children("*", "AnimationPlayer", true, false)
	return found[0] as AnimationPlayer if found.size() > 0 else null


func _model_aabb() -> AABB:
	var ab := AABB()
	var first := true
	for n in model.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if mi.mesh == null:
			continue
		var xf := mi.global_transform
		var skel := mi.get_node_or_null(mi.skeleton) as Skeleton3D
		if mi.skin != null and skel != null and mi.skin.get_bind_count() > 0:
			var bone := mi.skin.get_bind_bone(0)
			if bone < 0:
				bone = skel.find_bone(mi.skin.get_bind_name(0))
			xf = skel.global_transform * skel.get_bone_global_rest(bone) * mi.skin.get_bind_pose(0)
		var b := xf * mi.get_aabb()
		ab = b if first else ab.merge(b)
		first = false
	if first:
		ab = AABB(Vector3(-0.5, 0, -0.5), Vector3.ONE)
	return ab


## Bounds of the skeleton over a clip (bone origins + margin), for framing animation frames.
func _clip_aabb(ap: AnimationPlayer, length: float, rest: AABB) -> AABB:
	var skels := model.find_children("*", "Skeleton3D", true, false)
	if skels.is_empty():
		return rest
	var sk := skels[0] as Skeleton3D
	var ab := AABB()
	var first := true
	for i in 9:
		ap.seek(length * i / 8.0, true)
		await process_frame
		for b in sk.get_bone_count():
			var p := sk.global_transform * sk.get_bone_global_pose(b).origin
			if first:
				ab = AABB(p, Vector3.ZERO)
				first = false
			else:
				ab = ab.expand(p)
	var m := maxf(rest.size.y, maxf(rest.size.x, rest.size.z)) * 0.15
	ab = ab.grow(m)
	ab = ab.expand(Vector3(ab.position.x, 0.0, ab.position.z))
	return ab


func _frame_camera(ab: AABB, yaw_deg: float, pitch_deg: float, fov: float) -> void:
	var c := ab.get_center()
	var r := maxf(ab.size.length() * 0.5, 0.05)
	var dist := r / sin(deg_to_rad(fov) * 0.5) * 1.02
	var fwd := Basis(Vector3.UP, deg_to_rad(yaw_deg)) * Vector3(0, 0, -1)
	var p := deg_to_rad(pitch_deg)
	var dir := (fwd * cos(p) + Vector3.UP * sin(p)).normalized()
	cam.fov = fov
	cam.position = c + dir * dist
	cam.look_at(c, Vector3.UP if pitch_deg < 89.0 else Vector3(0, 0, -1))
	var sun := world.find_children("*", "DirectionalLight3D", false, false)
	if sun.size() > 0:
		(sun[0] as DirectionalLight3D).directional_shadow_max_distance = dist * 2.5


func _shot(label: String, kind: String) -> String:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	var file := "%02d_%s.png" % [shot_idx, label.validate_filename()]
	shot_idx += 1
	img.save_png(o.out_dir.path_join(file))
	if kind == "view":
		meta.views.append({"file": file, "label": label})
	return file


func _ingame(ab: AABB) -> void:
	var saved := vp.size
	vp.size = Vector2i(1920, 1080)
	var c := Vector3(ab.get_center().x, 0.0, ab.get_center().z)
	var p := deg_to_rad(o.game_pitch)
	cam.fov = o.game_fov
	cam.position = c + (Vector3(0, 0, -1) * cos(p) + Vector3.UP * sin(p)) * o.game_dist
	cam.look_at(c, Vector3.UP)
	var sun := world.find_children("*", "DirectionalLight3D", false, false)
	if sun.size() > 0:
		(sun[0] as DirectionalLight3D).directional_shadow_max_distance = o.game_dist * 2.0
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	var sp := cam.unproject_position(ab.get_center())
	var half := 128
	var x0 := clampi(int(sp.x) - half, 0, img.get_width() - 2 * half)
	var y0 := clampi(int(sp.y) - half, 0, img.get_height() - 2 * half)
	var crop := img.get_region(Rect2i(x0, y0, 2 * half, 2 * half))
	var file := "%02d_ingame.png" % shot_idx
	shot_idx += 1
	crop.save_png(o.out_dir.path_join(file))
	meta.ingame = {"file": file, "dist": o.game_dist, "fov": o.game_fov, "pitch": o.game_pitch}
	vp.size = saved
