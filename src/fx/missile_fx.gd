class_name MissileFx
extends Node3D
## Missiles in flight and after (juice bible §3.5: CMB-24 release tells, CMB-25 sticking,
## CMB-26 flight). Reads the projectile root (World/Projectiles) — the sim's own nodes — and never
## writes them:
##   - launch: the child_entered_tree signal only records the missile; the next frame shows the
##     release tell (hook-gun muzzle star HDR 3 + smoke ring);
##   - flight: one trail ribbon per live missile (a MultiMesh of camera-facing quads, 1 draw)
##     from its interpolated position back along its flight, length = speed x trail_s capped at
##     trail_max_m and at the distance flown, so every refresh rate draws the same trail;
##   - landing (seen while `landed`, or on exit if a slow frame skipped it): an arrow or javelin
##     sticks — in the victim at chest height, 55 % embedded, following its interpolated
##     transform (≤ 1 per unit), or in the ground at its flight pitch (25-60°), 35 % embedded,
##     wobbling (ω 37.7, ζ 0.18) — for `stuck_life_s`, then sinks; bullets puff dirt and clods;
##     bolts burst; siege shells throw dust and clods and add the whitelisted camera trauma;
##   - stuck missiles live in a ring of `stuck_cap` (one MultiMesh): the oldest is reused.

const TRAIL_SHADER := preload("res://src/fx/trail.gdshader")
const TRAIL_CAP := 128
const ARROW_LEN := 0.9
const JAVELIN_LEN := 1.6

var world: World
var vfx: Vfx
var trails: MultiMeshInstance3D
var stuck: MultiMeshInstance3D
var launched: int = 0
var landed_count: int = 0
var stuck_count: int = 0

var _tracked: Dictionary = {}           ## instance id -> Track
var _stuck: Array[Stuck] = []
var _next_stuck: int = 0
var _trail_buf := PackedFloat32Array()
var _stuck_buf := PackedFloat32Array()


class Track:
	var node: Projectile
	var start: Vector3
	var model: String = "arrow"
	var handled: bool = false
	var told: bool = false
	var speed: float = 15.0


class Stuck:
	var owner: Unit = null
	var local := Transform3D.IDENTITY   ## relative to the owner's interpolated transform
	var world_xf := Transform3D.IDENTITY
	var t0: float = -1000.0
	var life: float = 0.0
	var ground: bool = false
	var wobble_axis := Vector3.RIGHT
	var length: float = ARROW_LEN
	var end_t: float = -1.0              ## owner died: shrink from here


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	trails = MultiMeshInstance3D.new()
	trails.name = "Trails"
	trails.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	trails.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	var tm := ShaderMaterial.new()
	tm.shader = TRAIL_SHADER
	trails.multimesh = MultiMesh.new()
	trails.multimesh.transform_format = MultiMesh.TRANSFORM_3D
	trails.multimesh.use_colors = true
	trails.multimesh.mesh = q
	trails.multimesh.instance_count = TRAIL_CAP
	trails.multimesh.visible_instance_count = 0
	trails.material_override = tm
	add_child(trails)
	_trail_buf.resize(TRAIL_CAP * 16)
	stuck = MultiMeshInstance3D.new()
	stuck.name = "Stuck"
	stuck.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	stuck.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	stuck.multimesh = MultiMesh.new()
	stuck.multimesh.transform_format = MultiMesh.TRANSFORM_3D
	stuck.multimesh.mesh = _arrow_mesh()
	stuck.material_override = UnitView.placeholder_material()
	add_child(stuck)


func setup(w: World, v: Vfx) -> void:
	world = w
	vfx = v
	var cap := FeelConstants.c().stuck_cap
	stuck.multimesh.instance_count = cap
	stuck.multimesh.visible_instance_count = 0
	_stuck_buf.resize(cap * 12)
	_stuck.clear()
	for i in cap:
		_stuck.append(Stuck.new())
	var s := w.map.size_world()
	var aabb := AABB(Vector3(-5, -10, -5), Vector3(s.x + 10, 60, s.y + 10))
	trails.multimesh.custom_aabb = aabb
	stuck.multimesh.custom_aabb = aabb
	trails.custom_aabb = aabb
	stuck.custom_aabb = aabb
	var root := w.projectile_root
	if root != null:
		if not root.child_entered_tree.is_connected(_on_enter):
			root.child_entered_tree.connect(_on_enter)
		if not root.child_exiting_tree.is_connected(_on_exit):
			root.child_exiting_tree.connect(_on_exit)


func stuck_live(now: float = FxClock.fx_now) -> int:
	var n := 0
	for s in _stuck:
		if now - s.t0 < s.life:
			n += 1
	return n


func tracked_count() -> int:
	return _tracked.size()


# --- projectile root signals: record only ---------------------------------------------------------

func _on_enter(n: Node) -> void:
	var p := n as Projectile
	if p == null:
		return
	var t := Track.new()
	t.node = p
	t.start = p.pos
	t.speed = p.speed
	var src := world.get_unit(p.source_id) if world != null else null
	if src != null:
		t.model = str(src.projectile.get("model", "arrow"))
	_tracked[p.get_instance_id()] = t
	launched += 1


func _on_exit(n: Node) -> void:
	var id := n.get_instance_id()
	var t: Track = _tracked.get(id)
	if t == null:
		return
	if not t.handled and is_instance_valid(t.node):
		_land(t)
	_tracked.erase(id)


# --- per frame -----------------------------------------------------------------------------------

func _process(_delta: float) -> void:
	if world == null:
		return
	var cam := get_viewport().get_camera_3d()
	var n := 0
	for id: int in _tracked.keys():
		var t: Track = _tracked[id]
		if not is_instance_valid(t.node):
			_tracked.erase(id)
			continue
		if not t.told:
			t.told = true
			_release_tell(t)
		if t.node.landed:
			if not t.handled:
				_land(t)
			continue
		if cam != null and n < TRAIL_CAP:
			if _write_trail(n, t, cam):
				n += 1
	trails.multimesh.visible_instance_count = n
	if n > 0:
		trails.multimesh.buffer = _trail_buf
	_update_stuck()


func _release_tell(t: Track) -> void:
	if not vfx.allow(t.start):
		return
	var launch := str(FxDefs.missile(t.model).get("launch_sfx", ""))
	if not launch.is_empty():
		Audio.event("missile_release", t.start, {"launch_sfx": launch, "seed": t.node.source_id * 13 + world.tick_count})
	if t.model != "bullet":
		return
	var dir := (t.node.pos - t.node.prev_pos)
	if dir.length_squared() < 1e-6:
		dir = Vector3.FORWARD
	vfx.particles.burst("muzzle", t.start, dir.normalized(), 1.0, 2)
	vfx.particles.burst("smoke_puff", t.start, dir.normalized(), 1.0, 1)
	vfx.trace("CMB-24.release", t.node.source_id)


## Trail quad: head at the missile's interpolated position, tail back along the flight.
func _write_trail(i: int, t: Track, cam: Camera3D) -> bool:
	var spec := FxDefs.missile(t.model)
	var head := t.node.get_global_transform_interpolated().origin
	var vel := (t.node.pos - t.node.prev_pos) / World.DT
	if vel.length_squared() < 1e-4:
		return false
	var flown := head.distance_to(t.start)
	var length := minf(minf(vel.length() * FeelConstants.c().trail_s, FeelConstants.c().trail_max_m), flown)
	if length < 0.05:
		return false
	var axis := -vel.normalized() * length
	var mid := head + axis * 0.5
	var view := (cam.global_position - mid).normalized()
	var side := axis.cross(view)
	if side.length_squared() < 1e-8:
		return false
	side = side.normalized() * float(spec.get("trail_w", 0.05))
	var nrm := side.cross(axis).normalized()
	var o := i * 16
	# basis columns: x = side (quad width), y = -axis (UV.y = 1 at the head), z = normal
	var ya := -axis
	_trail_buf[o + 0] = side.x
	_trail_buf[o + 1] = ya.x
	_trail_buf[o + 2] = nrm.x
	_trail_buf[o + 3] = mid.x
	_trail_buf[o + 4] = side.y
	_trail_buf[o + 5] = ya.y
	_trail_buf[o + 6] = nrm.y
	_trail_buf[o + 7] = mid.y
	_trail_buf[o + 8] = side.z
	_trail_buf[o + 9] = ya.z
	_trail_buf[o + 10] = nrm.z
	_trail_buf[o + 11] = mid.z
	var c: Array = spec.get("trail", [1, 1, 1, 0.5])
	var hdr := float(spec.get("hdr", 1.0))
	_trail_buf[o + 12] = float(c[0]) * hdr
	_trail_buf[o + 13] = float(c[1]) * hdr
	_trail_buf[o + 14] = float(c[2]) * hdr
	_trail_buf[o + 15] = float(c[3])
	return true


func _land(t: Track) -> void:
	t.handled = true
	landed_count += 1
	var p := t.node
	var pos := p.pos
	var dir := p.pos - p.prev_pos
	if dir.length_squared() < 1e-6:
		dir = pos - t.start
	dir = dir.normalized() if dir.length_squared() > 1e-6 else Vector3.DOWN
	var target := world.get_unit(p.target_id)
	var hit := p.hit_target and target != null
	var spec := FxDefs.missile(t.model)
	var ranged := str(spec.get("ranged", "bow"))
	var sticks := bool(FxDefs.data().get("ranged", {}).get(ranged, {}).get("sticks", false))
	vfx.trace("CMB-25.land", p.target_id)
	if not vfx.allow(pos, 1):
		return
	match ranged:
		"siege":
			var g := Vector3(pos.x, world.map.height_at(pos.x, pos.z), pos.z)
			vfx.particles.burst("dust_land", g + Vector3(0, 0.1, 0), Vector3.UP, 1.0, 2)
			vfx.particles.burst("clod", g + Vector3(0, 0.1, 0), Vector3.UP, 1.0, 2)
			vfx.marks.add(GroundMarks.Kind.DUST_RING, g, 0.4, 1.6, Color(CombatFx.DUST, 0.45), 0.35,
				0.0, 0.0, null, false)
			var cj := CameraJuice.current
			if cj != null:
				cj.add_trauma(&"combat", 0.35 if t.model == "bombard_ball" else 0.25, g)
			Audio.event("siege_impact", g, {"hit_sfx": str(spec.get("hit_sfx", "")), "seed": p.source_id})
			return
		"bolt", "coal":
			vfx.particles.burst("bolt_burst" if ranged == "bolt" else "spark", pos, -dir, 0.8, 1)
			if ranged == "coal":
				vfx.particles.burst("soot_puff", pos, Vector3.UP, 1.0, 1)
			Audio.event("bolt_impact", pos, {"hit_sfx": str(spec.get("hit_sfx", "")), "seed": p.source_id})
			return
	if hit:
		var vs := FxDefs.sheet(target)
		var mat := FxDefs.hit_material(vs, target.facing, target.display_pos(), t.start)
		vfx.combat.impact_burst(mat, pos, (-dir + Vector3.UP * 0.4).normalized(),
			float(FxDefs.data().get("ranged", {}).get(ranged, {}).get("count", 0.7)) * vfx.tier_mult(), 1)
		Audio.event("missile_hit", pos, {"material": FxDefs.material_sound(mat), "hit_sfx": str(spec.get("hit_sfx", "")),
			"kill": not target.alive, "seed": p.source_id * 17 + world.tick_count})
		if sticks:
			_stick_in_unit(target, pos, dir, t.model)
	else:
		var gy := world.map.height_at(pos.x, pos.z)
		var g2 := Vector3(pos.x, gy, pos.z)
		vfx.particles.burst("clod", g2 + Vector3(0, 0.05, 0), (Vector3.UP - dir * 0.3).normalized(), 0.7, 0)
		vfx.particles.burst("dust_step", g2 + Vector3(0, 0.05, 0), Vector3.UP, 0.8, 0)
		if sticks:
			_stick_in_ground(g2, dir, t.model)
			Audio.event("missile_stick", g2, {"hit_sfx": str(spec.get("hit_sfx", "")), "seed": p.source_id})


func _stick_slot() -> Stuck:
	var now := FxClock.fx_now
	for s in _stuck:
		if now - s.t0 >= s.life:
			return s
	var s2 := _stuck[_next_stuck]
	_next_stuck = (_next_stuck + 1) % _stuck.size()
	return s2


func _stick_in_unit(u: Unit, pos: Vector3, dir: Vector3, model: String) -> void:
	if u.is_building or not is_instance_valid(u):
		return
	var now := FxClock.fx_now
	# ≤ 1 per unit: the new one replaces the old
	for o in _stuck:
		if o.owner == u and now - o.t0 < o.life:
			o.life = now - o.t0 + 0.12
			o.end_t = now
	var s := _stick_slot()
	var len := JAVELIN_LEN if model == "javelin" else ARROW_LEN
	var p := u.display_pos()
	var flat := Vector3(dir.x, 0.0, dir.z)
	flat = flat.normalized() if flat.length_squared() > 1e-6 else Vector3.FORWARD
	var d := (flat + Vector3(0, clampf(dir.y, -0.5, 0.2), 0)).normalized()
	var surface := Vector3(p.x, p.y + u.top_height() * 0.55, p.z) - flat * u.radius * 0.8
	var centre := surface + d * (0.55 - 0.5) * len
	var xf := Transform3D(Basis.looking_at(d, Vector3.UP if absf(d.y) < 0.99 else Vector3.RIGHT).scaled(Vector3.ONE * (len / ARROW_LEN)), centre)
	s.owner = u
	s.ground = false
	s.local = u.get_global_transform_interpolated().affine_inverse() * xf
	s.t0 = now
	s.life = 3.0
	s.end_t = -1.0
	s.length = len
	stuck_count += 1


func _stick_in_ground(g: Vector3, dir: Vector3, model: String) -> void:
	var s := _stick_slot()
	var len := JAVELIN_LEN if model == "javelin" else ARROW_LEN
	var flat := Vector3(dir.x, 0.0, dir.z)
	flat = flat.normalized() if flat.length_squared() > 1e-6 else Vector3.FORWARD
	var pitch := clampf(asin(clampf(-dir.y, -1.0, 1.0)), deg_to_rad(25.0), deg_to_rad(60.0))
	var d := (flat * cos(pitch) + Vector3.DOWN * sin(pitch)).normalized()
	var centre := g + d * (0.35 - 0.5) * len
	s.owner = null
	s.ground = true
	s.world_xf = Transform3D(Basis.looking_at(d, Vector3.UP).scaled(Vector3.ONE * (len / ARROW_LEN)), centre)
	s.wobble_axis = flat.cross(Vector3.UP).normalized()
	s.t0 = FxClock.fx_now
	s.life = FeelConstants.c().stuck_life_s + FeelConstants.c().stuck_sink_s
	s.end_t = -1.0
	s.length = len
	stuck_count += 1


func _update_stuck() -> void:
	var now := FxClock.fx_now
	var fc := FeelConstants.c()
	var n := 0
	for s in _stuck:
		var age := now - s.t0
		if age >= s.life or age < 0.0:
			continue
		var xf: Transform3D
		var shrink := 1.0
		if s.ground:
			# the shaft wobbles about the point where it enters the ground (35 % embedded)
			var wob := deg_to_rad(10.0) * Juice.spring(1.0, 0.0, 37.7, 0.18, age).x
			var d := -s.world_xf.basis.z.normalized()
			var pivot := s.world_xf.origin + d * (0.15 * s.length)
			var rot := Basis(s.wobble_axis, wob)
			xf = s.world_xf
			xf.basis = rot * xf.basis
			xf.origin = pivot + rot * (s.world_xf.origin - pivot)
			var sink_start := fc.stuck_life_s
			if age > sink_start:
				var k := Juice.window(age, sink_start, fc.stuck_sink_s)
				xf.origin += (-s.world_xf.basis.z.normalized()) * k * s.length * 0.6
				shrink = 1.0 - k * 0.3
		else:
			if s.owner == null or not is_instance_valid(s.owner):
				s.life = 0.0
				continue
			if not s.owner.alive and s.end_t < 0.0:
				s.end_t = now
				s.life = age + 0.12
			xf = s.owner.get_global_transform_interpolated() * s.local
			if s.end_t >= 0.0:
				shrink = 1.0 - Juice.window(now, s.end_t, 0.12)
			elif age > s.life - 0.2:
				shrink = 1.0 - Juice.window(age, s.life - 0.2, 0.2)
		xf.basis = xf.basis.scaled(Vector3.ONE * maxf(shrink, 0.001))
		var o := n * 12
		var b := xf.basis
		_stuck_buf[o + 0] = b.x.x
		_stuck_buf[o + 1] = b.y.x
		_stuck_buf[o + 2] = b.z.x
		_stuck_buf[o + 3] = xf.origin.x
		_stuck_buf[o + 4] = b.x.y
		_stuck_buf[o + 5] = b.y.y
		_stuck_buf[o + 6] = b.z.y
		_stuck_buf[o + 7] = xf.origin.y
		_stuck_buf[o + 8] = b.x.z
		_stuck_buf[o + 9] = b.y.z
		_stuck_buf[o + 10] = b.z.z
		_stuck_buf[o + 11] = xf.origin.z
		n += 1
	stuck.multimesh.visible_instance_count = n
	if n > 0:
		stuck.multimesh.buffer = _stuck_buf


## A placeholder arrow pointing down -Z (shaft, iron head, fletching), vertex coloured.
static func _arrow_mesh() -> Mesh:
	var shaft := BoxMesh.new()
	shaft.size = Vector3(0.035, 0.035, ARROW_LEN)
	var tip := BoxMesh.new()
	tip.size = Vector3(0.07, 0.07, 0.12)
	var fletch := BoxMesh.new()
	fletch.size = Vector3(0.16, 0.02, 0.16)
	var fletch2 := BoxMesh.new()
	fletch2.size = Vector3(0.02, 0.16, 0.16)
	return ProcMesh.merge([
		{"mesh": shaft, "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.55, 0.40, 0.24)},
		{"mesh": tip, "xform": ProcMesh.at(Vector3(0, 0, -ARROW_LEN * 0.5)), "color": Color(0.62, 0.63, 0.66)},
		{"mesh": fletch, "xform": ProcMesh.at(Vector3(0, 0, ARROW_LEN * 0.42)), "color": Color(0.93, 0.92, 0.86)},
		{"mesh": fletch2, "xform": ProcMesh.at(Vector3(0, 0, ARROW_LEN * 0.42)), "color": Color(0.93, 0.92, 0.86)},
	])
