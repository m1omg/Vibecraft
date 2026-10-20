class_name ParticlePool
extends Node3D
## The VFX pool manager (juice bible §4.1): pooled one-shot burst emitters per kind
## (data/fx_particles.json). GPUParticles3D on Forward+; CPUParticles3D on the Compatibility
## renderer (or when `force_cpu` / the `--cpu-particles` user arg is set). No node is created
## per effect: every emitter is built once at setup and re-aimed, re-tinted and restarted.
## Refresh-rate independence: emitters simulate at a fixed 60 fps with interpolation, so a
## burst looks the same at 30, 60 or 144 Hz. Pool rules:
##   - a burst takes a free emitter of its kind, else the oldest one past 50 % of its life;
##     a younger one is never popped: the burst is rejected (`stats.rejected`) unless its
##     importance is >= 3 (heroes, crits, deaths), which evicts the oldest (`stats.evicted`);
##   - at most `FeelConstants.spawn_budget_per_frame` particles start per frame; over budget,
##     optional bursts (importance < 2) are dropped (`stats.over_budget`).
## Visual only: never reads World.rng, never writes sim state.

const DATA_PATH := "res://data/fx_particles.json"
const FIXED_FPS := 60

var use_cpu: bool = false
var kinds: Dictionary = {}                 ## kind -> spec Dictionary
var stats: Dictionary = {"bursts": 0, "rejected": 0, "evicted": 0, "over_budget": 0}
var _pools: Dictionary = {}                ## kind -> Array of emitter records
var _frame_spent: int = 0
var _frame: int = -1


class Emitter:
	var node: Node3D
	var material: Resource                 ## ParticleProcessMaterial (GPU) or null (CPU)
	var t0: float = -1000.0
	var life: float = 0.5


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF


## Builds every pool. `cpu`: -1 auto (Compatibility -> CPU), 0 GPU, 1 CPU.
func setup(cpu: int = -1) -> void:
	if cpu < 0:
		use_cpu = RenderingServer.get_current_rendering_method() == "gl_compatibility" \
			or OS.get_cmdline_user_args().has("--cpu-particles")
	else:
		use_cpu = cpu == 1
	kinds = _load_kinds()
	for k: String in kinds:
		_build_pool(k, kinds[k])


static func _load_kinds() -> Dictionary:
	var f := FileAccess.open(DATA_PATH, FileAccess.READ)
	if f == null:
		push_warning("ParticlePool: %s missing" % DATA_PATH)
		return {}
	var d: Variant = JSON.parse_string(f.get_as_text())
	var out: Dictionary = {}
	if d is Dictionary:
		for k: String in d:
			if not k.begins_with("_") and d[k] is Dictionary:
				out[k] = d[k]
	return out


func has_kind(kind: String) -> bool:
	return _pools.has(kind)


func pool_size(kind: String) -> int:
	return (_pools.get(kind, []) as Array).size()


## Emitters of `kind` still showing particles at `now`.
func active_count(kind: String, now: float = FxClock.fx_now) -> int:
	var n := 0
	for e: Emitter in _pools.get(kind, []):
		if now - e.t0 < e.life:
			n += 1
	return n


## One burst. `dir`: main direction (normalised inside); `count_mult` scales the particle count
## (tier thinning, weapon multiplier); `tint` multiplies the kind's colour. Returns false when
## the burst was rejected or dropped.
func burst(kind: String, pos: Vector3, dir: Vector3 = Vector3.UP, count_mult: float = 1.0,
		importance: int = 1, tint: Color = Color.WHITE) -> bool:
	var pool: Array = _pools.get(kind, [])
	if pool.is_empty():
		return false
	var spec: Dictionary = kinds[kind]
	var amount_max := int(spec.get("amount", 4))
	var count := clampi(roundi(amount_max * count_mult), 1, amount_max)
	var f := Engine.get_process_frames()
	if f != _frame:
		_frame = f
		_frame_spent = 0
	if importance < 2 and _frame_spent + count > FeelConstants.c().spawn_budget_per_frame:
		stats["over_budget"] += 1
		return false
	var now := FxClock.fx_now
	var pick: Emitter = null
	var oldest: Emitter = null
	for e: Emitter in pool:
		if now - e.t0 >= e.life:
			pick = e
			break
		if oldest == null or e.t0 < oldest.t0:
			oldest = e
	if pick == null:
		if importance >= 3 or now - oldest.t0 >= oldest.life * 0.5:
			pick = oldest
			stats["evicted"] += 1
		else:
			stats["rejected"] += 1
			return false
	_frame_spent += count
	stats["bursts"] += 1
	pick.t0 = now
	_fire(pick, spec, pos, dir, count, tint)
	return true


func _fire(e: Emitter, spec: Dictionary, pos: Vector3, dir: Vector3, count: int, tint: Color) -> void:
	var y := dir.normalized() if dir.length_squared() > 1e-6 else Vector3.UP
	var x := y.cross(Vector3.FORWARD if absf(y.dot(Vector3.FORWARD)) < 0.95 else Vector3.RIGHT).normalized()
	var z := x.cross(y).normalized()
	var xf := Transform3D(Basis(x, y, z), pos)
	if e.node.is_inside_tree():
		e.node.global_transform = xf
	else:
		e.node.transform = xf
	var col := Color.WHITE * tint
	col.a = tint.a
	if use_cpu:
		var c := e.node as CPUParticles3D
		if c.amount != count:
			c.amount = count
		c.color = col
		c.restart()
	else:
		var g := e.node as GPUParticles3D
		g.amount_ratio = float(count) / float(maxi(g.amount, 1))
		(e.material as ParticleProcessMaterial).color = col
		g.restart()


func _build_pool(kind: String, spec: Dictionary) -> void:
	var n := int(spec.get("pool", 8))
	var arr: Array = []
	var mesh := _draw_mesh(spec)
	var life_r: Array = spec.get("life", [0.3, 0.4])
	var life_max := float(life_r[1])
	for i in n:
		var e := Emitter.new()
		e.life = life_max
		if use_cpu:
			e.node = _make_cpu(spec, mesh)
		else:
			var g := _make_gpu(spec, mesh)
			e.node = g
			e.material = g.process_material
		e.node.name = "%s_%d" % [kind, i]
		add_child(e.node)
		arr.append(e)
	_pools[kind] = arr


func _make_gpu(spec: Dictionary, mesh: Mesh) -> GPUParticles3D:
	var g := GPUParticles3D.new()
	g.amount = int(spec.get("amount", 4))
	g.one_shot = true
	g.emitting = false
	g.explosiveness = 1.0
	g.fixed_fps = FIXED_FPS
	g.interpolate = true
	g.fract_delta = true
	g.local_coords = false
	g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	g.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	g.visibility_aabb = AABB(Vector3(-4, -4, -4), Vector3(8, 8, 8))
	var life_r: Array = spec.get("life", [0.3, 0.4])
	g.lifetime = maxf(float(life_r[1]), 0.02)
	if bool(spec.get("align", false)):
		g.transform_align = GPUParticles3D.TRANSFORM_ALIGN_Z_BILLBOARD_Y_TO_VELOCITY
	var pm := ParticleProcessMaterial.new()
	pm.lifetime_randomness = clampf(1.0 - float(life_r[0]) / maxf(float(life_r[1]), 0.001), 0.0, 1.0)
	pm.direction = Vector3.UP
	pm.spread = float(spec.get("spread", 30.0))
	var sp: Array = spec.get("speed", [1.0, 2.0])
	pm.initial_velocity_min = float(sp[0])
	pm.initial_velocity_max = float(sp[1])
	pm.gravity = Vector3(0, -float(spec.get("gravity", 9.8)), 0)
	var dmp := float(spec.get("damping", 0.0))
	pm.damping_min = dmp
	pm.damping_max = dmp
	var sz: Array = spec.get("size", [0.1, 0.1])
	pm.scale_min = float(sz[0])
	pm.scale_max = float(sz[1])
	var curve := _size_curve(float(spec.get("size_end", 1.0)))
	var ct := CurveTexture.new()
	ct.curve = curve
	pm.scale_curve = ct
	var ramp := GradientTexture1D.new()
	ramp.gradient = _color_ramp(spec)
	pm.color_ramp = ramp
	if spec.has("color_var"):
		var init := GradientTexture1D.new()
		init.gradient = _initial_ramp(spec)
		pm.color_initial_ramp = init
	var spin := float(spec.get("spin", 0.0))
	if spin > 0.0:
		pm.angular_velocity_min = -rad_to_deg(spin)
		pm.angular_velocity_max = rad_to_deg(spin)
		pm.angle_min = -180.0
		pm.angle_max = 180.0
	g.process_material = pm
	g.draw_pass_1 = mesh
	return g


func _make_cpu(spec: Dictionary, mesh: Mesh) -> CPUParticles3D:
	var c := CPUParticles3D.new()
	c.amount = int(spec.get("amount", 4))
	c.one_shot = true
	c.emitting = false
	c.explosiveness = 1.0
	c.fixed_fps = FIXED_FPS
	c.fract_delta = true
	c.local_coords = false
	c.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	c.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	var life_r: Array = spec.get("life", [0.3, 0.4])
	c.lifetime = maxf(float(life_r[1]), 0.02)
	c.lifetime_randomness = clampf(1.0 - float(life_r[0]) / maxf(float(life_r[1]), 0.001), 0.0, 1.0)
	c.direction = Vector3.UP
	c.spread = float(spec.get("spread", 30.0))
	var sp: Array = spec.get("speed", [1.0, 2.0])
	c.initial_velocity_min = float(sp[0])
	c.initial_velocity_max = float(sp[1])
	c.gravity = Vector3(0, -float(spec.get("gravity", 9.8)), 0)
	var dmp := float(spec.get("damping", 0.0))
	c.damping_min = dmp
	c.damping_max = dmp
	var sz: Array = spec.get("size", [0.1, 0.1])
	c.scale_amount_min = float(sz[0])
	c.scale_amount_max = float(sz[1])
	c.scale_amount_curve = _size_curve(float(spec.get("size_end", 1.0)))
	c.color_ramp = _color_ramp(spec)
	if spec.has("color_var"):
		c.color_initial_ramp = _initial_ramp(spec)
	var spin := float(spec.get("spin", 0.0))
	if spin > 0.0:
		c.angular_velocity_min = -rad_to_deg(spin)
		c.angular_velocity_max = rad_to_deg(spin)
		c.angle_min = -180.0
		c.angle_max = 180.0
	c.mesh = mesh
	return c


static func _size_curve(end_scale: float) -> Curve:
	var curve := Curve.new()
	curve.max_value = maxf(1.0, end_scale)
	curve.add_point(Vector2(0.0, 1.0))
	curve.add_point(Vector2(1.0, end_scale))
	return curve


## Colour over life. With `color_var` the start colour is picked between `color` and
## `color_var` (initial ramp) and the life ramp only fades; otherwise `color` -> `color_end`.
## Non-cutout kinds fade their alpha to 0 at the end; cutout kinds keep alpha and shrink instead.
static func _color_ramp(spec: Dictionary) -> Gradient:
	var cut := str(spec.get("blend", "mix")) == "cutout"
	var c0 := Color(str(spec.get("color", "#FFFFFF")))
	var c1 := Color(str(spec.get("color_end", spec.get("color", "#FFFFFF"))))
	if spec.has("color_var"):
		c0 = Color(1, 1, 1, c0.a)
		c1 = Color(1, 1, 1, c0.a)
	var g := Gradient.new()
	g.set_color(0, c0)
	g.set_color(1, Color(c1.r, c1.g, c1.b, c0.a if cut else 0.0))
	if not cut:
		var mid := c0.lerp(c1, 0.6)
		mid.a = c0.a
		g.add_point(0.6, mid)
	return g


static func _initial_ramp(spec: Dictionary) -> Gradient:
	var g := Gradient.new()
	var a := Color(str(spec.get("color", "#FFFFFF")))
	var b := Color(str(spec.get("color_var", spec.get("color", "#FFFFFF"))))
	a.a = 1.0
	b.a = 1.0
	g.set_color(0, a)
	g.set_color(1, b)
	return g


func _draw_mesh(spec: Dictionary) -> Mesh:
	var q := QuadMesh.new()
	var align := bool(spec.get("align", false)) and not use_cpu
	q.size = Vector2(0.25, 1.0) if align else Vector2(1.0, 1.0)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.disable_receive_shadows = true
	m.albedo_texture = FxTextures.get_tex(str(spec.get("tex", "soft")))
	if not align:
		m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		m.billboard_keep_scale = true
	match str(spec.get("blend", "mix")):
		"add":
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
			var hdr := float(spec.get("hdr", 1.0))
			m.albedo_color = Color(hdr, hdr, hdr, 1.0)
		"cutout":
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
			m.alpha_scissor_threshold = 0.5
		_:
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
			m.render_priority = 1
	q.material = m
	return q
