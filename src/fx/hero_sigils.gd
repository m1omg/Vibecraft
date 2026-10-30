class_name HeroSigils
extends Node3D
## Hero sigils (juice HER-01, Playtest 3 subset; shader `hero_sigil.gdshader`): one ground ring
## per living hero the local player can see, at its interpolated position and tilted to the
## terrain. The band shows the level (lit segments; the new one lights 250 ms into the level-up
## ceremony, after a 70 ms wind-up that contracts and dims the ring). The kingdom wheel ratchets
## 30° per stride of travel (a 60 ms snap, a 4° overshoot and recoil) and one notch when its hero
## is selected; the Tormai winds sway with a 3.6 s breath. The own hero's XP arc shows while it
## is selected and for 3 s after XP arrives. On death the ring swells and fades over 0.4 s.
## Visual only; every curve is closed-form on the fx clock.

const SHADER := preload("res://src/fx/hero_sigil.gdshader")
const SHADER_HALF := 1.2         ## the shader's HALF: metres from the quad's centre to its edge
const BAND_OUT := 1.05           ## the shader's BAND_OUT
const STRIDE := 0.9              ## metres of travel per ratchet notch
const NOTCH := PI / 6.0          ## 30°
const SNAP_S := 0.06
const RECOIL_S := 0.05
const OVERSHOOT := 1.133         ## 4° past the 30° notch
const SWAY := 0.14               ## ±8° wind sway (rad)
const BREATH_S := 3.6
const XP_SHOW_S := 3.0
const XP_FADE_S := 0.3
const WIND_UP_S := 0.07
const LEVEL_LIGHT_S := 0.25      ## the new segment lights here (HER-04.ratchet)
const SHATTER_S := 0.4

var world: World
var vfx: Vfx
var items: Dictionary = {}       ## unit id -> Item
var _quad: QuadMesh
var _mat: ShaderMaterial


class Item:
	var unit: Unit
	var node: MeshInstance3D
	var dist: float = 0.0
	var last: Vector3 = Vector3.INF
	var theta: float = 0.0       ## wheel angle after the last finished notch
	var notching: bool = false
	var notch_t0: float = -10.0
	var notch_dir: float = 1.0
	var side: float = 1.0
	var xp_t0: float = -10.0
	var level_t0: float = -10.0
	var dead_t0: float = -1.0


func setup(v: Vfx, w: World) -> void:
	vfx = v
	world = w
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	_quad = QuadMesh.new()
	_quad.size = Vector2(2.0, 2.0)
	_quad.orientation = PlaneMesh.FACE_Y
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	_mat.render_priority = 2
	Events.selection_changed.connect(_on_selection_changed)


func _exit_tree() -> void:
	if Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.disconnect(_on_selection_changed)


## The level-up ceremony starts (HeroFx): wind-up, then the new segment at 250 ms.
func level_up(u: Unit) -> void:
	var it: Item = items.get(u.id)
	if it != null:
		it.level_t0 = FxClock.fx_now


## XP arrived (HeroFx, when the motes land): the own hero's arc shows for a while.
func xp_arrived(u: Unit) -> void:
	var it: Item = items.get(u.id)
	if it != null:
		it.xp_t0 = FxClock.fx_now


func _on_selection_changed(units: Array) -> void:
	for u: Variant in units:
		var it: Item = items.get((u as Unit).id) if u is Unit else null
		if it != null and it.unit.player_id == world.local_player_id:
			_notch(it, 1.0)              # it answers the click


func _notch(it: Item, dir: float) -> void:
	if it.notching:
		it.theta += NOTCH * it.notch_dir      # finish the running notch at once
	it.notching = true
	it.notch_t0 = FxClock.fx_now
	it.notch_dir = dir


static func snap(age: float) -> float:
	if age < SNAP_S:
		return Juice.in_cubic(age / SNAP_S) * OVERSHOOT
	if age < SNAP_S + RECOIL_S:
		return lerpf(OVERSHOOT, 1.0, Juice.out_quad((age - SNAP_S) / RECOIL_S))
	return 1.0


func _process(_delta: float) -> void:
	if world == null or not is_instance_valid(world):
		return
	var now := FxClock.fx_now
	var seen := {}
	for u in world.unit_list:
		if u.is_hero and u.alive:
			seen[u.id] = true
			if not items.has(u.id):
				items[u.id] = _make(u)
	for id: int in items.keys():
		var it: Item = items[id]
		if not is_instance_valid(it.unit):
			it.node.queue_free()
			items.erase(id)
			continue
		if not seen.has(id) and it.dead_t0 < 0.0:
			it.dead_t0 = now
		if it.dead_t0 >= 0.0 and now - it.dead_t0 >= SHATTER_S:
			it.node.queue_free()
			items.erase(id)
			continue
		_update(it, now)


func _make(u: Unit) -> Item:
	var it := Item.new()
	it.unit = u
	it.node = MeshInstance3D.new()
	it.node.mesh = _quad
	it.node.material_override = _mat
	it.node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	it.node.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(it.node)
	it.node.set_instance_shader_parameter("team", world.player_color(u.player_id))
	it.node.set_instance_shader_parameter("sig_a", Vector4(1, _face(u), 0, 1))
	return it


static func _face(u: Unit) -> float:
	return 1.0 if str(u.def.get("faction", "")) == "clans" or u.def_id.begins_with("clans_") else 0.0


func _update(it: Item, now: float) -> void:
	var u := it.unit
	var view := u.view as Node3D
	it.node.visible = view == null or view.is_visible_in_tree()
	if not it.node.visible:
		return
	var p := u.display_pos()
	if it.last != Vector3.INF and it.dead_t0 < 0.0:
		var step := Vector2(p.x - it.last.x, p.z - it.last.z)
		it.dist += step.length()
		var cam := get_viewport().get_camera_3d()
		if cam != null and step.length() > 0.0005:
			var right := cam.global_transform.basis.x
			var lateral := step.dot(Vector2(right.x, right.z))
			if absf(lateral) > 0.2 * FxClock.fx_dt and signf(lateral) != it.side:
				it.side = signf(lateral)
		if it.dist >= STRIDE:
			it.dist = fmod(it.dist, STRIDE)
			_notch(it, it.side)
	it.last = p
	var age := now - it.notch_t0
	if it.notching and age >= SNAP_S + RECOIL_S:
		it.theta = fmod(it.theta + NOTCH * it.notch_dir, TAU)
		it.notching = false
	var face := _face(u)
	var theta := it.theta + (NOTCH * it.notch_dir * snap(age) if it.notching else 0.0)
	if face > 0.5:
		theta = SWAY * sin(TAU * now / BREATH_S + float(u.id))
	var scale := 1.0 + 0.02 * sin(TAU * now / BREATH_S + float(u.id) * 0.7)
	var value := 1.0
	var level := float(u.hero.get("level", u.level))
	var la := now - it.level_t0
	if la >= 0.0 and la < LEVEL_LIGHT_S:
		level -= 1.0                      # the new segment lights at 250 ms
		if la < WIND_UP_S:
			var k := Juice.in_quad(la / WIND_UP_S)
			scale *= 1.0 - 0.1 * k
			value = 1.0 - 0.4 * k
		else:
			var k := Juice.out_back((la - WIND_UP_S) / (LEVEL_LIGHT_S - WIND_UP_S))
			scale *= 0.9 + 0.1 * k
			value = 0.6 + 0.4 * clampf(k, 0.0, 1.0)
	var alpha := 1.0
	if it.dead_t0 >= 0.0:
		var d := clampf((now - it.dead_t0) / SHATTER_S, 0.0, 1.0)
		scale *= 1.0 + 0.15 * Juice.out_cubic(d)
		alpha = 1.0 - d
	var xp_a := 0.0
	if u.player_id == world.local_player_id and it.dead_t0 < 0.0:
		var since := now - it.xp_t0
		if vfx != null and vfx.selected.has(u):
			xp_a = 1.0
		elif since < XP_SHOW_S:
			xp_a = clampf((XP_SHOW_S - since) / XP_FADE_S, 0.0, 1.0)
	it.node.transform = vfx.marks.ground_xf(p, SHADER_HALF, u.id)
	it.node.set_instance_shader_parameter("sig_a", Vector4(level, face, theta, alpha))
	it.node.set_instance_shader_parameter("sig_b", Vector4(HeroSystem.xp_ratio(u.hero), xp_a, scale, value))
