class_name Projectile
extends Node3D
## A missile simulated in the fixed tick: it homes on its target's current hit point along a
## parabolic arc (peak = arc x flight distance) and, on arrival, Combat applies the base damage
## rolled at launch. If the target dies first the missile lands where it last was, harmlessly.
## The Node3D transform is written once per tick so physics interpolation smooths the flight;
## on arrival the transform is committed at the impact point and the node lives one more tick
## (`landed`), so the interpolated missile visibly finishes its flight into the target.

const HIT_EPS := 0.05

static var _meshes: Dictionary = {}

var world: World
var source_id: int = 0
var source_player: int = 0
var target_id: int = 0
var damage: float = 0.0          ## rolled base damage (before type/armor)
var attack_type: String = ""
var speed: float = 15.0
var arc: float = 0.0
var pos: Vector3 = Vector3.ZERO
var prev_pos: Vector3 = Vector3.ZERO
var hit_target: bool = false
var landed: bool = false          ## arrived last tick; Combat frees it on the next one

var _start_y: float = 0.0
var _aim: Vector3 = Vector3.ZERO  ## last known impact point
var _flat: Vector2 = Vector2.ZERO
var _travelled: float = 0.0


func setup(w: World, src: Unit, target: Unit, base_damage: float) -> void:
	world = w
	name = "Projectile"
	source_id = src.id
	source_player = src.player_id
	target_id = target.id
	damage = base_damage
	attack_type = src.attack_type
	speed = float(src.projectile.get("speed", 15.0))
	arc = float(src.projectile.get("arc", 0.0))
	_aim = target.hit_point()
	pos = src.launch_point(target.pos)
	prev_pos = pos
	_start_y = pos.y
	_flat = Vector2(pos.x, pos.z)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_ON
	if w.visuals:
		_add_visual(str(src.projectile.get("model", "arrow")))
	_commit(_aim - pos)


## Advances one tick; true when the flight is over (`hit_target`: landed on a live target).
func sim_tick(dt: float) -> bool:
	prev_pos = pos
	var t := world.get_unit(target_id)
	var target_alive := t != null and t.alive
	if target_alive:
		_aim = t.hit_point()
	var to := Vector2(_aim.x - _flat.x, _aim.z - _flat.y)
	var remaining := to.length()
	var step := speed * dt
	if remaining <= step + HIT_EPS:
		var last_dir := _aim - pos
		pos = _aim
		_commit(last_dir)
		hit_target = target_alive
		landed = true
		return true
	_flat += to / remaining * step
	_travelled += step
	remaining -= step
	var total := _travelled + remaining
	var k := _travelled / total
	var y := lerpf(_start_y, _aim.y, k) + arc * total * 4.0 * k * (1.0 - k)
	var np := Vector3(_flat.x, y, _flat.y)
	var dir := np - pos
	pos = np
	_commit(dir)
	return false


func _commit(dir: Vector3) -> void:
	var b := basis
	if dir.length_squared() > 1e-8:
		var n := dir.normalized()
		var up := Vector3.UP if absf(n.y) < 0.99 else Vector3.RIGHT
		b = Basis.looking_at(n, up)
	transform = Transform3D(b, pos)


func _add_visual(model: String) -> void:
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	mi.mesh = _mesh(model)
	mi.material_override = UnitView.placeholder_material()
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)


## Procedural missile meshes by the projectile `model` id (pointing down -Z, looking_at forward):
## arrows and javelins are shafts with a head and fletching, bullets a lead ball, bombard balls an
## iron ball, clay pots a lidded terracotta pot, bolts and pellets small coloured orbs. Visual only.
static func _mesh(model: String) -> Mesh:
	if _meshes.has(model):
		return _meshes[model]
	var parts: Array = []
	match model:
		"bombard_ball":
			parts = [{"mesh": ProcMesh.sphere(0.13, 10, 6), "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.17, 0.17, 0.19)}]
		"bullet":
			parts = [{"mesh": ProcMesh.sphere(0.05, 6, 4), "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.35, 0.35, 0.38)}]
		"clay_pot":
			parts = [
				{"mesh": ProcMesh.sphere(0.13, 10, 6), "xform": ProcMesh.at(Vector3.ZERO, Vector3(1.0, 0.9, 1.0)), "color": Color(0.66, 0.42, 0.22)},
				{"mesh": ProcMesh.cylinder(0.06, 0.07, 0.07, 8), "xform": ProcMesh.at(Vector3(0, 0.12, 0)), "color": Color(0.55, 0.34, 0.18)},
				{"mesh": ProcMesh.cylinder(0.075, 0.075, 0.025, 8), "xform": ProcMesh.at(Vector3(0, 0.165, 0)), "color": Color(0.85, 0.62, 0.2)},
			]
		"coal_lump":
			parts = [{"mesh": ProcMesh.sphere(0.09, 6, 4), "xform": ProcMesh.at(Vector3.ZERO, Vector3(1.2, 0.8, 1.0)), "color": Color(0.12, 0.1, 0.09)}]
		"arcane_bolt":
			parts = [{"mesh": ProcMesh.sphere(0.1, 8, 5), "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.72, 0.95, 0.62)}]
		"ice_pellet":
			parts = [{"mesh": ProcMesh.sphere(0.08, 8, 5), "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.78, 0.9, 1.0)}]
		_:
			var length := 1.25 if model == "javelin" else 0.9
			var shaft := BoxMesh.new()
			shaft.size = Vector3(0.07, 0.07, length)
			var tip := BoxMesh.new()
			tip.size = Vector3(0.13, 0.13, 0.18)
			var fletch := BoxMesh.new()
			fletch.size = Vector3(0.22, 0.03, 0.18)
			parts = [
				{"mesh": shaft, "xform": ProcMesh.at(Vector3.ZERO), "color": Color(0.55, 0.40, 0.24)},
				{"mesh": tip, "xform": ProcMesh.at(Vector3(0, 0, -length * 0.55), Vector3.ONE, PI * 0.25), "color": Color(0.85, 0.87, 0.9)},
			]
			if model != "javelin":
				parts.append({"mesh": fletch, "xform": ProcMesh.at(Vector3(0, 0, 0.38)), "color": Color(0.95, 0.95, 0.9)})
	var m := ProcMesh.merge(parts)
	_meshes[model] = m
	return m
