## Line-up / vignette renderer for the procedural doodad kit (driven by tools/kits/lineup.py).
##
##   xvfb-run -a godot --rendering-driver vulkan --path tools/preview -s <abs>/tools/kits/lineup.gd -- \
##       --scene scene.json --out-dir DIR
##
## scene.json: {"size": [w, h], "ground": {...}, "water": [...], "objects": [...], "shots": [...]}
##   ground  {"textures": [base, l1, l2, l3, l4], "splat": png (RGBA weights of l1..l4), "rect": [x0, z0, x1, z1],
##            "tile_m": 4.0}
##   water   [{"center": [x, z], "radius": r, "y": 0.03, "texture": png}]
##   objects [{"glb": path, "pos": [x, y, z], "yaw": deg, "scale": s, "label": text}]
##   shots   [{"name": n, "focus": [x, z], "distance": m, "pitch": 56, "fov": 45, "yaw": 0}]
## The camera sits like RtsCamera (src/input/rts_camera.gd): on the +Z side of the focus, looking
## toward -Z, pitch 56 deg, vertical FOV 45. Light and ambient follow DayNight's day values. SWAY
## materials get tools/kits/foliage_sway.gdshader (static), TEAM materials the --team colour.
## Writes <out-dir>/<shot>.png and <out-dir>/labels.json (screen positions of every object label).
extends SceneTree

var o := {"scene": "", "out_dir": "", "team": "#2f6bff"}
var vp: SubViewport
var cam: Camera3D
var world: Node3D
var sway_shader: Shader
var placed: Array = []


func _initialize() -> void:
	var a := OS.get_cmdline_user_args()
	var i := 0
	while i + 1 < a.size():
		var k: String = a[i].trim_prefix("--").replace("-", "_")
		if o.has(k):
			o[k] = a[i + 1]
		i += 2
	_run()


func _run() -> void:
	await process_frame
	var sc: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(o.scene))
	DirAccess.make_dir_recursive_absolute(o.out_dir)
	var size: Array = sc.get("size", [1920, 1080])
	vp = SubViewport.new()
	vp.size = Vector2i(int(size[0]), int(size[1]))
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.msaa_3d = Viewport.MSAA_4X
	root.add_child(vp)
	world = Node3D.new()
	vp.add_child(world)
	var shp := (o.scene as String).get_base_dir().path_join("../../tools/kits/foliage_sway.gdshader")
	var kit_dir: String = sc.get("kit_dir", "")
	if kit_dir != "":
		shp = kit_dir.path_join("foliage_sway.gdshader")
	sway_shader = Shader.new()
	sway_shader.code = FileAccess.get_file_as_string(shp)
	_build_env()
	if sc.has("ground"):
		_build_ground(sc.ground)
	for w in sc.get("water", []):
		_build_water(w)
	for ob in sc.get("objects", []):
		_place(ob)
	cam = Camera3D.new()
	cam.near = 0.5
	cam.far = 400.0
	vp.add_child(cam)
	cam.current = true
	await process_frame
	var labels := {}
	for s in sc.get("shots", []):
		var pitch := deg_to_rad(float(s.get("pitch", 56.0)))
		var dist := float(s.get("distance", 28.0))
		var yaw := deg_to_rad(float(s.get("yaw", 0.0)))
		var f: Array = s.focus
		var target := Vector3(float(f[0]), 0.0, float(f[1]))
		cam.fov = float(s.get("fov", 45.0))
		var off := Basis(Vector3.UP, yaw) * Vector3(0.0, sin(pitch), cos(pitch)) * dist
		cam.look_at_from_position(target + off, target, Vector3.UP)
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var img := vp.get_texture().get_image()
		img.save_png(o.out_dir.path_join(str(s.name) + ".png"))
		var ls: Array = []
		for p in placed:
			var top: Vector3 = p.top
			if cam.is_position_behind(top):
				continue
			var sp := cam.unproject_position(top)
			var bp := cam.unproject_position(p.base)
			if sp.x < -50 or sp.y < -50 or sp.x > vp.size.x + 50 or sp.y > vp.size.y + 50:
				continue
			ls.append({"label": p.label, "x": sp.x, "y": sp.y, "bx": bp.x, "by": bp.y})
		labels[str(s.name)] = ls
	var fa := FileAccess.open(o.out_dir.path_join("labels.json"), FileAccess.WRITE)
	fa.store_string(JSON.stringify(labels, " "))
	fa.close()
	print("VC_LINEUP:" + o.out_dir)
	quit(0)


func _build_env() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.55, 0.66, 0.78)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.66, 0.72)     # DayNight.DAY_AMBIENT
	env.ambient_light_energy = 0.75
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.0
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.08                      # bible §1.5 day grade 1.05-1.12
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.95, 0.85)              # DayNight.DAY_SUN
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 70.0
	sun.shadow_blur = 1.5
	world.add_child(sun)
	# elevation 52 deg, from screen lower-left (camera sits at +Z looking -Z)
	var e := deg_to_rad(52.0)
	var d := Vector3(-0.72, 0.0, 0.69).normalized() * cos(e) + Vector3.UP * sin(e)
	sun.look_at_from_position(d * 10.0, Vector3.ZERO, Vector3.UP)


func _tex(path: String) -> Texture2D:
	var img := Image.load_from_file(path)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _build_ground(g: Dictionary) -> void:
	var rect: Array = g.rect
	var w := float(rect[2]) - float(rect[0])
	var h := float(rect[3]) - float(rect[1])
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(w + 200.0, h + 200.0)
	mi.mesh = pm
	mi.position = Vector3((float(rect[0]) + float(rect[2])) * 0.5, 0.0, (float(rect[1]) + float(rect[3])) * 0.5)
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode diffuse_lambert_wrap, specular_disabled;
uniform sampler2D t0 : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D t1 : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D t2 : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D t3 : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D t4 : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D splat : filter_linear;
uniform vec4 rect;
uniform float tile_m = 4.0;
varying vec3 wp;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { return vnoise(p) * 0.6 + vnoise(p * 2.13 + 7.1) * 0.3 + vnoise(p * 4.7 + 3.3) * 0.1; }
void fragment() {
	vec2 uv = wp.xz / tile_m;
	vec2 suv = (wp.xz - rect.xy) / (rect.zw - rect.xy);
	vec4 w = texture(splat, suv);
	float n = fbm(wp.xz * 0.85) - 0.5;
	vec3 c = texture(t0, uv).rgb;
	c = mix(c, texture(t1, uv * 0.97 + 0.31).rgb, smoothstep(0.47, 0.53, w.r + n * 0.5));
	c = mix(c, texture(t2, uv + 0.17).rgb, smoothstep(0.47, 0.53, w.g + n * 0.5));
	c = mix(c, texture(t3, uv + 0.53).rgb, smoothstep(0.47, 0.53, w.b + n * 0.5));
	c = mix(c, texture(t4, uv + 0.71).rgb, smoothstep(0.47, 0.53, w.a + n * 0.5));
	c *= 0.94 + 0.12 * fbm(wp.xz * 0.05);
	ALBEDO = c;
	ROUGHNESS = 1.0;
}
"""
	var m := ShaderMaterial.new()
	m.shader = sh
	var texs: Array = g.textures
	for i in texs.size():
		m.set_shader_parameter("t%d" % i, _tex(texs[i]))
	var splat_img := Image.load_from_file(g.splat)
	m.set_shader_parameter("splat", ImageTexture.create_from_image(splat_img))
	m.set_shader_parameter("rect", Vector4(float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])))
	m.set_shader_parameter("tile_m", float(g.get("tile_m", 4.0)))
	mi.material_override = m
	world.add_child(mi)


func _build_water(w: Dictionary) -> void:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	var r := float(w.radius)
	cm.top_radius = r
	cm.bottom_radius = r
	cm.height = 0.02
	cm.radial_segments = 48
	mi.mesh = cm
	var c: Array = w.center
	mi.position = Vector3(float(c[0]), float(w.get("y", 0.03)) - 0.01, float(c[1]))
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode diffuse_lambert_wrap;
uniform sampler2D tex : source_color, repeat_enable, filter_linear_mipmap;
uniform vec3 deep : source_color = vec3(0.24, 0.52, 0.52);
varying vec3 wp;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	vec3 t = texture(tex, wp.xz / 4.0).rgb;
	ALBEDO = deep * (0.7 + 0.4 * t);
	ROUGHNESS = 0.45;
	SPECULAR = 0.25;
}
"""
	var m := ShaderMaterial.new()
	m.shader = sh
	if w.has("texture"):
		m.set_shader_parameter("tex", _tex(w.texture))
	mi.material_override = m
	world.add_child(mi)


func _place(ob: Dictionary) -> void:
	var path: String = ob.glb
	if not FileAccess.file_exists(path):
		printerr("missing " + path)
		return
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	if doc.append_from_file(path, st) != OK:
		printerr("failed " + path)
		return
	var n := doc.generate_scene(st) as Node3D
	var p: Array = ob.get("pos", [0, 0, 0])
	n.position = Vector3(float(p[0]), float(p[1]), float(p[2]))
	n.rotation.y = deg_to_rad(float(ob.get("yaw", 0.0)))
	var s := float(ob.get("scale", 1.0))
	n.scale = Vector3(s, s, s)
	world.add_child(n)
	_fix_materials(n)
	var ab := _aabb(n)
	if ob.has("label"):
		placed.append({"label": ob.label, "top": Vector3(ab.get_center().x, ab.end.y, ab.get_center().z),
				"base": Vector3(ab.get_center().x, 0.0, ab.get_center().z + minf(ab.size.z * 0.5, 1.2))})


func _fix_materials(n: Node) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.mesh != null:
			for s in mi.mesh.get_surface_count():
				var mat := mi.mesh.surface_get_material(s)
				if mat == null or not (mat is StandardMaterial3D):
					continue
				var sm := mat as StandardMaterial3D
				var vc = (sm.get_meta("extras", {}) as Dictionary).get("vc_vertex_color", "")
				if vc == "multiply":
					var m3 := sm.duplicate() as StandardMaterial3D
					m3.vertex_color_use_as_albedo = true
					mi.set_surface_override_material(s, m3)
				elif sm.resource_name.contains("SWAY"):
					var fm := ShaderMaterial.new()
					fm.shader = sway_shader
					fm.set_shader_parameter("albedo_tex", sm.albedo_texture)
					fm.set_shader_parameter("alpha_cutoff", sm.alpha_scissor_threshold)
					fm.set_shader_parameter("sway_amp", 0.0)
					fm.set_shader_parameter("flutter", 0.0)
					mi.set_surface_override_material(s, fm)
				elif sm.resource_name.contains("TEAM"):
					var m2 := sm.duplicate() as StandardMaterial3D
					m2.albedo_color = Color(o.team)
					mi.set_surface_override_material(s, m2)
	for c in n.get_children():
		_fix_materials(c)


func _aabb(root_node: Node3D) -> AABB:
	var ab := AABB()
	var first := true
	for c in root_node.find_children("*", "MeshInstance3D", true, false):
		var mi := c as MeshInstance3D
		if mi.mesh == null:
			continue
		var b := mi.global_transform * mi.get_aabb()
		ab = b if first else ab.merge(b)
		first = false
	if first:
		ab = AABB(root_node.global_position, Vector3.ONE)
	return ab
