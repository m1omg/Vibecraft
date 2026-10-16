class_name UnitView
extends Node3D
## Visual representation of a Unit. Loads assets/models/<model>.glb when present, otherwise
## builds a procedural placeholder from the def's `shape` hint (humanoid / building / mine).
## Animation is visual only: it reads sim state but never writes it. The animated `rig` has
## physics interpolation OFF so its per-frame local motion composes with the parent Unit's
## interpolated transform. Procedural fallbacks: walk bob, attack lunge (melee) / draw (ranged)
## timed by `Unit.swing_progress()`, hit flash, and death topple + sink timed by sim ticks.

const SKIN := Color(0.85, 0.68, 0.52)
const DARK := Color(0.16, 0.13, 0.11)
const WOOD := Color(0.42, 0.29, 0.17)
const STEEL := Color(0.70, 0.72, 0.76)
const GOLD := Color(0.98, 0.78, 0.22)
const PLACEHOLDER_SHADER := preload("res://src/entities/unit_placeholder.gdshader")
const TOPPLE_TIME := 0.55
const SINK_TIME := 2.5
const FLASH_DECAY := 6.0
const BODY_COLORS: Dictionary = {
	"tool": Color(0.55, 0.42, 0.28), "sword": Color(0.52, 0.55, 0.60),
	"bow": Color(0.30, 0.44, 0.25), "club": Color(0.42, 0.34, 0.27), "none": Color(0.5, 0.5, 0.5),
}

static var _meshes: Dictionary = {}       ## primitive part cache
static var _merged: Dictionary = {}       ## "def|colour" -> merged placeholder mesh
static var _vc_material: ShaderMaterial
static var _warned_models: Dictionary = {}
static var _parts: Array = []

var unit: Unit
var rig: Node3D
var body: Node3D
var height: float = 1.5
var _t: float = 0.0
var _move: float = 0.0
var _anim: AnimationPlayer
var _anim_state: String = ""
var _mesh: GeometryInstance3D
var _flash: float = 0.0
var _fall_dir: float = 1.0


func setup(u: Unit) -> void:
	unit = u
	name = "View"
	rig = Node3D.new()
	rig.name = "Rig"
	rig.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(rig)
	body = Node3D.new()
	body.name = "Body"
	rig.add_child(body)
	var d := u.def
	height = float(d.get("height", 1.5)) * float(d.get("scale", 1.0))
	_t = float(u.id) * 1.37
	_fall_dir = 1.0 if u.id % 2 == 0 else -1.0
	if not _try_load_model(str(d.get("model", ""))):
		_add_placeholder(d)


## Brief bright tint when hit (called by Vfx on `unit_damaged`).
func flash() -> void:
	_flash = 1.0


func team_color() -> Color:
	return unit.world.player_color(unit.player_id) if unit.world != null else Color.WHITE


func _process(delta: float) -> void:
	if unit == null:
		return
	if not unit.alive:
		_animate_death()
		return
	_update_flash(delta)
	if unit.is_building or unit.is_resource:
		return
	_t += delta
	var target := 0.0
	if unit.speed > 0.0:
		target = clampf(unit.velocity.length() / unit.speed, 0.0, 1.0)
	_move = move_toward(_move, target, delta * 6.0)
	var swing := unit.swing_progress()
	if _anim != null:
		_play("attack" if swing >= 0.0 else ("walk" if _move > 0.3 else "idle"))
		return
	var stride := _t * 9.0
	var bob := absf(sin(stride)) * 0.07 * height * _move
	var breathe := 1.0 + 0.025 * sin(_t * 2.2) * (1.0 - _move)
	body.position = Vector3(0.0, bob, 0.0)
	body.scale = Vector3(1.0, breathe, 1.0)
	body.rotation = Vector3(-0.14 * _move, 0.0, sin(stride) * 0.05 * _move)
	if swing >= 0.0:
		_animate_swing(swing)


## Strike curve peaks at the damage point: melee lunges forward, ranged leans back to draw.
func _animate_swing(swing: float) -> void:
	var dp := maxf(unit.damage_point_ratio(), 0.05)
	var s := smoothstep(0.0, dp, swing) if swing < dp else 1.0 - smoothstep(dp, 1.0, swing)
	if unit.projectile.is_empty():
		body.rotation.x = -0.5 * s
		body.position.z = -0.22 * s * height
	else:
		body.rotation.x = 0.16 * s
		body.position.z = 0.05 * s * height


func _update_flash(delta: float) -> void:
	if _flash <= 0.0 or _mesh == null:
		return
	_flash = maxf(_flash - delta * FLASH_DECAY, 0.0)
	_mesh.set_instance_shader_parameter("flash", _flash)


## Units topple over then sink before the World frees the corpse; structures sink and tilt.
func _animate_death() -> void:
	if _flash > 0.0 and _mesh != null:
		_flash = 0.0
		_mesh.set_instance_shader_parameter("flash", 0.0)
	var t := unit.dead_time()
	var decay := unit.decay_ticks() * World.DT
	var sink := clampf((t - (decay - SINK_TIME)) / SINK_TIME, 0.0, 1.0)
	if unit.is_building or unit.is_resource:
		var k := clampf(t / decay, 0.0, 1.0)
		body.position = Vector3(0.0, -height * 1.15 * k * k, 0.0)
		body.rotation = Vector3(0.04 * k, 0.0, 0.06 * k * _fall_dir)
		return
	if _anim != null:
		_play("death")
		body.position.y = -sink * height * 0.6
		return
	var f := clampf(t / TOPPLE_TIME, 0.0, 1.0)
	var fall := f * f * (3.0 - 2.0 * f)
	body.scale = Vector3.ONE
	body.rotation = Vector3(PI * 0.5 * fall, 0.0, 0.25 * fall * _fall_dir)
	body.position = Vector3(0.0, 0.14 * height * fall - sink * height * 0.5, 0.0)


func _play(clip: String) -> void:
	if clip == _anim_state or not _anim.has_animation(clip):
		return
	_anim_state = clip
	_anim.play(clip, 0.2)


# --- asset models --------------------------------------------------------------------------

func _try_load_model(model: String) -> bool:
	if model.is_empty():
		return false
	var path := "res://assets/models/%s.glb" % model
	if not ResourceLoader.exists(path):
		if not _warned_models.has(model):
			_warned_models[model] = true
			push_warning("UnitView: model '%s' missing, using placeholder" % path)
		return false
	var scene := load(path) as PackedScene
	if scene == null:
		return false
	var inst := scene.instantiate()
	body.add_child(inst)
	_anim = inst.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _anim != null:
		_play("idle")
	_apply_team_color(inst)
	return true


## Materials whose resource name contains "TEAM" get the player colour.
func _apply_team_color(n: Node) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			if mat != null and mat.resource_name.contains("TEAM") and mat is StandardMaterial3D:
				var m2 := (mat as StandardMaterial3D).duplicate() as StandardMaterial3D
				m2.albedo_color = team_color()
				mi.set_surface_override_material(s, m2)
	for c in n.get_children():
		_apply_team_color(c)


# --- placeholder builders ------------------------------------------------------------------

## Placeholder parts are merged into one vertex-coloured mesh per (def, team colour) and
## shared by every unit of that kind: one draw call per unit instead of ~10.
func _add_placeholder(d: Dictionary) -> void:
	var key := "%s|%s" % [unit.def_id, team_color().to_html()]
	if not _merged.has(key):
		_parts.clear()
		match str(d.get("shape", "humanoid")):
			"building":
				_build_building(d)
			"mine":
				_build_mine(d)
			_:
				_build_humanoid(d)
		_merged[key] = ProcMesh.merge(_parts)
		_parts.clear()
	var mi := MeshInstance3D.new()
	mi.name = "Placeholder"
	mi.mesh = _merged[key]
	mi.material_override = placeholder_material()
	body.add_child(mi)
	_mesh = mi


func _build_humanoid(d: Dictionary) -> void:
	var s := float(d.get("scale", 1.0))
	var h := height
	var r := float(d.get("radius", 0.4)) * s
	var weapon := str(d.get("weapon", "none"))
	var body_col: Color = BODY_COLORS.get(weapon, BODY_COLORS["none"])
	var tc := team_color()
	var torso_h := h * 0.58
	_part(_capsule(r * 0.62, torso_h), body_col, Vector3(0, h * 0.12 + torso_h * 0.5, 0))
	_part(_sphere(h * 0.12), SKIN, Vector3(0, h * 0.83, 0))
	_part(_cyl(r * 0.66, r * 0.66, h * 0.09), tc, Vector3(0, h * 0.5, 0))
	for side in [-1.0, 1.0]:
		_part(_box(Vector3(r * 0.3, h * 0.12, r * 0.45)), DARK, Vector3(side * r * 0.28, h * 0.06, -r * 0.08))
		_part(_sphere(r * 0.24), tc, Vector3(side * r * 0.62, h * 0.66, 0))
	match weapon:
		"sword":
			_part(_box(Vector3(0.07, 0.07, h * 0.5)), STEEL, Vector3(r * 0.85, h * 0.42, -h * 0.2))
			_part(_box(Vector3(0.08, h * 0.38, h * 0.3)), tc, Vector3(-r * 0.85, h * 0.45, -0.05))
		"bow":
			_part(_cyl(0.025, 0.025, h * 0.75), WOOD, Vector3(-r * 0.8, h * 0.52, -0.1))
			_part(_box(Vector3(0.18, 0.18, 0.4)), WOOD, Vector3(r * 0.4, h * 0.62, r * 0.6))
		"tool":
			_part(_cyl(0.03, 0.03, h * 0.55), WOOD, Vector3(r * 0.8, h * 0.4, -0.05))
			_part(_box(Vector3(0.28, 0.08, 0.08)), STEEL, Vector3(r * 0.8, h * 0.66, -0.05))
		"club":
			_part(_cyl(0.11, 0.05, h * 0.55), WOOD, Vector3(r * 0.85, h * 0.45, -0.1))


func _build_building(d: Dictionary) -> void:
	var fp: Array = d.get("footprint", [8, 8])
	var w := float(fp[0]) * Grid.CELL * 0.9
	var depth := float(fp[1]) * Grid.CELL * 0.9
	var h := height
	var wall := Color(0.64, 0.57, 0.46)
	var roof := Color(0.38, 0.22, 0.16)
	var tc := team_color()
	# foundation reaches below the lowest footprint corner so slopes never show a gap
	_part(_box(Vector3(w * 1.06, 0.8, depth * 1.06)), Color(0.45, 0.43, 0.40), Vector3(0, -0.2, 0))
	var base_h := h * 0.55
	_part(_box(Vector3(w, base_h, depth)), wall, Vector3(0, base_h * 0.5, 0))
	_part(_box(Vector3(w * 1.02, base_h * 0.12, depth * 1.02)), tc, Vector3(0, base_h * 0.86, 0))
	_part(_box(Vector3(w * 0.28, base_h * 0.6, 0.12)), DARK, Vector3(0, base_h * 0.3, -depth * 0.5 - 0.02))
	if str(d.get("roof", "pyramid")) == "gable":
		var prism := _cached("prism:%.2f:%.2f:%.2f" % [w, h, depth], func() -> Mesh:
			var p := PrismMesh.new()
			p.size = Vector3(w * 1.1, h * 0.45, depth * 1.05)
			return p)
		_part(prism, roof, Vector3(0, base_h + h * 0.225, 0))
	else:
		var pyr := _cached("pyr:%.2f:%.2f" % [w, h], func() -> Mesh:
			var c := CylinderMesh.new()
			c.top_radius = 0.0
			c.bottom_radius = maxf(w, depth) * 0.78
			c.height = h * 0.5
			c.radial_segments = 4
			c.rings = 1
			return c)
		_part(pyr, roof, Vector3(0, base_h + h * 0.25, 0), PI * 0.25)
	# banner pole with team flag
	_part(_cyl(0.05, 0.05, h * 0.6), WOOD, Vector3(w * 0.38, base_h + h * 0.3, depth * 0.38))
	_part(_box(Vector3(0.04, h * 0.18, h * 0.28)), tc, Vector3(w * 0.38, base_h + h * 0.48, depth * 0.38 - h * 0.14))


func _build_mine(d: Dictionary) -> void:
	var fp: Array = d.get("footprint", [8, 8])
	var w := float(fp[0]) * Grid.CELL
	var h := height
	var rock := Color(0.42, 0.38, 0.34)
	var mound := _cached("mound:%.2f:%.2f" % [w, h], func() -> Mesh:
		var s := SphereMesh.new()
		s.radius = w * 0.5
		s.height = h * 2.0
		s.radial_segments = 10
		s.rings = 6
		return s)
	_part(mound, rock, Vector3(0, 0.0, 0))
	_part(_box(Vector3(w * 0.36, h * 0.55, 0.5)), DARK, Vector3(0, h * 0.3, -w * 0.38))
	_part(_box(Vector3(0.14, h * 0.62, 0.16)), WOOD, Vector3(-w * 0.2, h * 0.31, -w * 0.42))
	_part(_box(Vector3(0.14, h * 0.62, 0.16)), WOOD, Vector3(w * 0.2, h * 0.31, -w * 0.42))
	_part(_box(Vector3(w * 0.48, 0.14, 0.18)), WOOD, Vector3(0, h * 0.62, -w * 0.42))
	# gold nuggets sit on the mound surface (ellipsoid radii w/2, h, w/2)
	for k in 8:
		var a := -PI * 0.5 + (k - 3.5) * 0.42
		var elev := 0.35 + 0.12 * float(k % 3)
		var dir := Vector3(cos(a) * cos(elev), sin(elev), sin(a) * cos(elev))
		_part(_sphere(0.2 + 0.06 * float(k % 2)), GOLD, dir * Vector3(w * 0.5, h, w * 0.5) * 0.98)


# --- mesh / material helpers ---------------------------------------------------------------

func _part(mesh: Mesh, col: Color, p: Vector3, yaw: float = 0.0) -> void:
	_parts.append({"mesh": mesh, "xform": ProcMesh.at(p, Vector3.ONE, yaw), "color": col})


## Shared vertex-colour material (sRGB vertex colours, per-instance hit flash).
static func placeholder_material() -> ShaderMaterial:
	if _vc_material == null:
		_vc_material = ShaderMaterial.new()
		_vc_material.shader = PLACEHOLDER_SHADER
	return _vc_material


static func _cached(key: String, ctor: Callable) -> Mesh:
	if not _meshes.has(key):
		_meshes[key] = ctor.call()
	return _meshes[key]


static func _capsule(r: float, h: float) -> Mesh:
	return _cached("cap:%.3f:%.3f" % [r, h], func() -> Mesh:
		var c := CapsuleMesh.new()
		c.radius = r
		c.height = maxf(h, r * 2.0)
		c.radial_segments = 12
		c.rings = 4
		return c)


static func _sphere(r: float) -> Mesh:
	return _cached("sph:%.3f" % r, func() -> Mesh: return ProcMesh.sphere(r, 10, 6))


static func _cyl(top: float, bottom: float, h: float) -> Mesh:
	return _cached("cyl:%.3f:%.3f:%.3f" % [top, bottom, h], func() -> Mesh:
		return ProcMesh.cylinder(top, bottom, h, 10))


static func _box(size: Vector3) -> Mesh:
	return _cached("box:%s" % size, func() -> Mesh:
		var b := BoxMesh.new()
		b.size = size
		return b)
