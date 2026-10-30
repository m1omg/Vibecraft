class_name HeroFx
extends Node
## Hero juice, Playtest 3's P0 subset (juice HER-01, HER-03, HER-04, HER-06, HER-07); owned by
## Vfx. Visual and audio only.
##   - the sigils under every visible hero (HeroSigils) and the XP motes (XpMotes);
##   - level-up (times from the event): the sigil winds up (0–70 ms) and lights its new segment
##     at 250 ms, when the new level's numeral rises; a standing emblem (the sigil face) rises
##     behind the hero to face the camera from 250 ms, holds, and slams flat at 820 ms with a flash ring, a dust
##     ring, a warm flash on the hero, the faction's level-up cue and the level's ladder bell
##     (each level one step up a pentatonic ladder); it fades by 1150 ms;
##   - a hero falls: its sigil swells and fades (HeroSigils), the owner hears the hero-down sting;
##   - a revive completes: a soft ring at the hero's feet, a flash ring, a warm flash and the
##     revive swell.
## Handlers only enqueue (Vfx's rule); the queue drains in `_process`. Off-screen events skip
## their world part through Vfx.allow; the owner's stings play anyway.

const EMBLEM_R := 0.8
const RISE_AT := 0.25
const STAND_S := 0.2
const SLAM_AT := 0.82
const SLAM_S := 0.1
const END_AT := 1.15
const WARM := Color(1.0, 0.86, 0.55)
const DUST := Color(0.72, 0.64, 0.5)

var vfx: Vfx
var world: World
var sigils: HeroSigils
var motes: XpMotes
## Beats played, by kind (level, slam, died, revived, xp): tests and the feel trace read it.
var counts: Dictionary = {}
var _queue: Array = []
var _links: Array = []
var _emblems: Array = []          ## [MeshInstance3D, Unit, fx t0, level, slammed, numeral shown]
var _quad: QuadMesh
var _mat: ShaderMaterial


func setup(v: Vfx, w: World) -> void:
	vfx = v
	world = w
	sigils = HeroSigils.new()
	sigils.name = "HeroSigils"
	add_child(sigils)
	sigils.setup(v, w)
	motes = XpMotes.new()
	motes.name = "XpMotes"
	add_child(motes)
	motes.arrived.connect(sigils.xp_arrived)
	_quad = QuadMesh.new()
	var side := 2.0 * HeroSigils.SHADER_HALF * EMBLEM_R / HeroSigils.BAND_OUT   # band edge at EMBLEM_R
	_quad.size = Vector2(side, side)
	_mat = ShaderMaterial.new()
	_mat.shader = HeroSigils.SHADER
	_mat.render_priority = 5
	_link(Events.hero_level_up, func(u: Node) -> void: _queue.append(["level", u]))
	_link(Events.hero_xp_gained, func(h: Node, amount: float, from: Vector3, levels: int) -> void:
		_queue.append(["xp", h, amount, from, levels]))
	_link(Events.hero_died, func(u: Node) -> void: _queue.append(["died", u]))
	_link(Events.hero_revived, func(u: Node) -> void: _queue.append(["revived", u]))


func _link(sig: Signal, cb: Callable) -> void:
	sig.connect(cb)
	_links.append([sig, cb])


func _exit_tree() -> void:
	for pair: Array in _links:
		var sig: Signal = pair[0]
		if sig.is_connected(pair[1]):
			sig.disconnect(pair[1])
	_links.clear()


func _count(kind: String) -> void:
	counts[kind] = int(counts.get(kind, 0)) + 1
	vfx.trace("HER." + kind, 0)


func _process(_delta: float) -> void:
	if world == null or not is_instance_valid(world):
		return
	if not _queue.is_empty():
		var q := _queue
		_queue = []
		for rec: Array in q:
			if is_instance_valid(rec[1]):
				_play(rec)
	_update_emblems()


func _play(rec: Array) -> void:
	var u: Unit = rec[1]
	match str(rec[0]):
		"level":
			_level_up(u)
		"xp":
			if vfx.allow(rec[3]) or vfx.allow(u.pos):
				_count("xp")
				motes.launch(u, float(rec[2]), rec[3], int(rec[4]))
		"died":
			_count("died")
			if u.player_id == world.local_player_id:
				Audio.play_2d("hero_down", {"volume_db": -2.0})
			elif vfx.allow(u.pos):
				Audio.play_3d("hero_down", u.pos, {"priority": 80})
		"revived":
			_revived(u)


func _ground(p: Vector3) -> Vector3:
	return Vector3(p.x, world.map.height_at(p.x, p.z), p.z)


## HER-04: the ceremony (sigil wind-up now; the emblem and numeral from 250 ms; the slam at 820 ms).
func _level_up(u: Unit) -> void:
	sigils.level_up(u)
	if not vfx.allow(u.pos, 3):
		return
	_count("level")
	var node := MeshInstance3D.new()
	node.mesh = _quad
	node.material_override = _mat
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	node.visible = false
	add_child(node)
	node.set_instance_shader_parameter("team", world.player_color(u.player_id))
	_emblems.append([node, u, FxClock.fx_now, int(u.hero.get("level", u.level)), false, false])


## The emblem (HER-04 placement): born flat at the hero's feet, it rises to 1.3 m, 0.35 m behind
## the hero, and tilts to face the camera exactly (out_back), shrinking from r 1.05 to 0.8 m, so
## it reads as a full circle that frames the hero; it lights its new segment, holds, then slams
## back down flat and fades.
func _update_emblems() -> void:
	var now := FxClock.fx_now
	var cam := get_viewport().get_camera_3d()
	var i := _emblems.size() - 1
	while i >= 0:
		var e: Array = _emblems[i]
		var node: MeshInstance3D = e[0]
		var u: Unit = e[1]
		var age := now - float(e[2])
		if age >= END_AT or not is_instance_valid(u):
			node.queue_free()
			_emblems.remove_at(i)
			i -= 1
			continue
		i -= 1
		node.visible = age >= RISE_AT
		if not node.visible:
			continue
		if not bool(e[5]):
			e[5] = true
			vfx.popups.show_value(PopupText.Style.LEVEL, int(e[3]), u.display_pos() + Vector3(0, u.top_height() + 0.5, 0), u)
		var stand := 0.0
		if age < RISE_AT + STAND_S:
			stand = Juice.out_back((age - RISE_AT) / STAND_S, 1.6)
		elif age < SLAM_AT:
			stand = 1.0
		elif age < SLAM_AT + SLAM_S:
			stand = 1.0 - Juice.in_cubic((age - SLAM_AT) / SLAM_S)
		if age >= SLAM_AT and not bool(e[4]):
			e[4] = true
			_slam(u, int(e[3]))
		var facing := cam.global_transform.basis if cam != null else Basis.IDENTITY
		var x := facing.x
		x.y = 0.0
		x = x.normalized() if x.length() > 0.01 else Vector3.RIGHT
		var flat := Basis(x, Vector3.UP.cross(x), Vector3.UP)
		var standing := Basis(x, facing.y, facing.z).orthonormalized()
		var q := Quaternion(flat).slerp(Quaternion(standing), clampf(stand, 0.0, 1.15))
		var k := clampf(stand, 0.0, 1.0)
		var away := Vector3(-facing.z.x, 0.0, -facing.z.z)
		away = away.normalized() if away.length() > 0.01 else Vector3.FORWARD
		var foot := _ground(u.display_pos())
		var r := lerpf(HeroSigils.BAND_OUT / EMBLEM_R, 1.0, k)
		var alpha := 1.0 if age < SLAM_AT + SLAM_S else 1.0 - (age - SLAM_AT - SLAM_S) / (END_AT - SLAM_AT - SLAM_S)
		node.transform = Transform3D(Basis(q).scaled(Vector3(r, r, r)),
			foot + Vector3(0, lerpf(0.05, 1.3, k), 0) + away * 0.35 * k)
		var face := 1.0 if u.def_id.begins_with("clans_") else 0.0
		var lit := float(e[3]) - (1.0 if age < RISE_AT + STAND_S * 0.75 else 0.0)
		node.set_instance_shader_parameter("sig_a", Vector4(lit, face, 0.0, clampf(alpha, 0.0, 1.0)))
		node.set_instance_shader_parameter("sig_b", Vector4(0.0, 0.0, 1.0, 1.0))


## The slam: rings, a flash on the hero, the faction cue and the level's ladder bell.
func _slam(u: Unit, level: int) -> void:
	_count("slam")
	var c := _ground(u.display_pos())
	vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, 0.8, 2.4, Color(WARM, 0.6), 0.5, 0.0, 0.0, null, false)
	vfx.marks.add(GroundMarks.Kind.DUST_RING, c, 0.6, 1.8, Color(DUST, 0.5), 0.7, 0.0, 0.0, null, false)
	var view := u.view as UnitView
	if view != null:
		view.flash(0.5, WARM, 0.3)
	var faction := "clans" if u.def_id.begins_with("clans_") else "kingdom"
	Audio.play_3d("hero_level_" + faction, c, {"priority": 85, "no_cut_ms": 1000})
	Audio.play_3d("hero_bell_%s_l%d" % [faction, clampi(level, 2, 10)], c, {"priority": 80})


## HER-07: the hero is back.
func _revived(u: Unit) -> void:
	if not vfx.allow(u.pos, 2):
		return
	_count("revived")
	var c := _ground(u.pos)
	vfx.marks.add(GroundMarks.Kind.RIPPLE, c, 0.5, 1.6, Color(WARM, 0.35), 0.4, 0.0, 0.0, null, false)
	vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, 0.9, 2.0, Color(WARM, 0.5), 0.6, 0.1, 0.0, null, false)
	var view := u.view as UnitView
	if view != null:
		view.flash(0.6, WARM, 0.4)
	Audio.play_3d("hero_revive", c, {"priority": 80})
