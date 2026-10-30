class_name AbilityFx
extends Node
## Ability juice, Playtest 3's P0 subset (juice ABL-01, ABL-03, ABL-05, ULT-01; the eight-school
## colours of heroes-abilities-vfx §5 reduced to one tint per ability); owned by Vfx. Visual and
## audio only.
##   - a cast starts: a soft ring in the ability's tint at the caster's feet and the cast swell;
##   - an ability goes off (Events.ability_cast): its look from LOOKS: a flash ring of its area at
##     the target point (or the caster), a burst of its particles, a flash on the targets, its
##     sound;
##   - heals rise as green numbers (Events.unit_healed); Fuse Mark's blast (Events.ability_burst);
##   - lasting ground effects are drawn every frame from the sim's records: burning ground, the
##     swallowed sun, smoke and straw as tinted discs with a pulsing edge; the local team's Bronze
##     Window reveals as a dashed ring; a Fuse Mark ticks as a red ring under its target;
##   - the local player's invisible units are drawn half-transparent (UnitView).
## Handlers only enqueue; the queue drains in `_process`. Every curve is closed-form on the fx
## clock.

## ability id -> [tint, particles, sound, area key or metres, flash targets]
const LOOKS: Dictionary = {
	"kingdom_linden_balm": [Color(0.55, 1.0, 0.55), "heal_mote", "ab_heal", 2.5, true],
	"kingdom_brace_the_wheel": [Color(1.0, 0.8, 0.45), "dust_clash", "ab_brace", "area", false],
	"kingdom_the_wagon_ring": [Color(1.0, 0.85, 0.4), "star_soft", "ab_ring", "area", false],
	"kingdom_naphtha_flask": [Color(1.0, 0.5, 0.2), "ember", "ab_fire", "area", false],
	"kingdom_fuse_mark": [Color(1.0, 0.35, 0.25), "ember", "ab_cast", 0.8, true],
	"kingdom_grand_bombard": [Color(0.9, 0.75, 0.5), "dust_land", "ab_summon", 2.0, false],
	"clans_dust_veil": [Color(0.85, 0.75, 0.55), "dust_veil", "ab_veil", 1.5, false],
	"clans_braid_lash": [Color(0.9, 0.7, 0.4), "dust_clash", "ab_lash", 0.8, true],
	"clans_through_the_tall_grass": [Color(0.75, 0.95, 0.5), "chaff", "ab_brace", 2.5, true],
	"clans_sunglint": [Color(1.0, 0.95, 0.75), "glint", "ab_glint", "range", false],
	"clans_bronze_window": [Color(0.95, 0.75, 0.4), "glint", "ab_window", "area", false],
	"clans_hail_swifts": [Color(0.8, 0.9, 1.0), "dust_land", "ab_summon", 2.0, false],
	"clans_swallowed_sun": [Color(0.35, 0.3, 0.5), "shadow_puff", "ab_dark", "area", false],
}
const GROUND_TINT: Dictionary = {
	"naphtha_fire": Color(1.0, 0.42, 0.1, 0.58), "swallowed_sun": Color(0.07, 0.05, 0.13, 0.62),
	"smoke_pot": Color(0.6, 0.6, 0.6, 0.4), "loose_straw": Color(0.85, 0.75, 0.4, 0.35),
	"hail_patch": Color(0.8, 0.9, 1.0, 0.35),
}

var vfx: Vfx
var world: World
## Beats played, by kind (cast, ability id, heal, burst): tests and the feel trace read it.
var counts: Dictionary = {}
var _queue: Array = []
var _links: Array = []
var _ember_beat: Dictionary = {}     ## ground effect handle -> the last ember beat played


func setup(v: Vfx, w: World) -> void:
	vfx = v
	world = w
	_link(Events.cast_started, func(c: Node, id: String) -> void: _queue.append(["cast", c, id]))
	_link(Events.ability_cast, func(c: Node, id: String, _r: int, t: Node, p: Vector3) -> void:
		_queue.append(["ability", c, id, t, p]))
	_link(Events.unit_healed, func(u: Node, amount: float, _s: Node) -> void: _queue.append(["heal", u, amount]))
	_link(Events.ability_burst, func(id: String, p: Vector3, r: float) -> void: _queue.append(["burst", null, id, p, r]))


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
	vfx.trace("ABL." + kind, 0)


func _process(_delta: float) -> void:
	if world == null or not is_instance_valid(world):
		return
	if not _queue.is_empty():
		var q := _queue
		_queue = []
		for rec: Array in q:
			if rec[1] == null or is_instance_valid(rec[1]):
				_play(rec)
	_draw_lasting()


func _ground(p: Vector3) -> Vector3:
	return Vector3(p.x, world.map.height_at(p.x, p.z), p.z)


func _play(rec: Array) -> void:
	match str(rec[0]):
		"cast":
			var c: Unit = rec[1]
			if vfx.allow(c.pos):
				_count("cast")
				var look: Array = LOOKS.get(str(rec[2]), [Color(0.9, 0.85, 0.7)])
				vfx.marks.add(GroundMarks.Kind.RIPPLE, _ground(c.pos), 0.5, 1.3, Color(look[0], 0.5), 0.35, 0.0, 0.0, c, false)
				Audio.play_3d("ab_cast", c.pos, {"volume_db": -6.0})
		"ability":
			_ability(rec[1], str(rec[2]), rec[3] as Unit if rec[3] != null and is_instance_valid(rec[3]) else null, rec[4])
		"heal":
			var u: Unit = rec[1]
			if u.player_id == world.local_player_id or vfx.allow(u.pos):
				_count("heal")
				vfx.popups.show_value(PopupText.Style.HEAL, roundi(float(rec[2])), u.display_pos() + Vector3(0, u.top_height(), 0), u, u.id)
		"burst":
			var p: Vector3 = rec[3]
			if vfx.allow(p, 2):
				_count("burst")
				var c := _ground(p)
				vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, 0.6, maxf(float(rec[4]), 1.0) * 1.2, Color(1.0, 0.5, 0.2, 0.7), 0.45, 0.0, 0.0, null, false)
				vfx.particles.burst("ember", c + Vector3(0, 0.8, 0), Vector3.UP, 2.0, 2, Color(1.0, 0.6, 0.25))
				vfx.particles.burst("smoke_puff", c + Vector3(0, 0.6, 0), Vector3.UP, 1.5, 1)
				Audio.play_3d("bombard_hit", c, {"priority": 70})


## An ability went off: its ring, particles, target flashes and sound.
func _ability(caster: Unit, id: String, target: Unit, pos: Vector3) -> void:
	var look: Array = LOOKS.get(id, [])
	if look.is_empty():
		return
	var centre := target.pos if target != null else (pos if pos != Vector3.ZERO else caster.pos)
	if not vfx.allow(centre, 2):
		return
	_count(id)
	var tint: Color = look[0]
	var v := Defs.ability_rank(id, maxi(1, world.abilities.rank_of(caster, id)))
	var r: float = float(v.get(str(look[3]), 3.0)) if look[3] is String else float(look[3])
	if id == "clans_sunglint":
		centre = caster.pos + (pos - caster.pos).normalized() * minf(r, Grid.flat_dist(caster.pos, pos)) * 0.6 \
			if Grid.flat_dist(caster.pos, pos) > 0.1 else caster.pos
		r *= 0.6
	var c := _ground(centre)
	vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, r * 0.6, r, Color(tint, 0.65), 0.5, 0.0, 0.0, null, false)
	vfx.marks.add(GroundMarks.Kind.RIPPLE, c, r * 0.2, r * 0.9, Color(tint, 0.35), 0.6, 0.08, 0.0, null, false)
	vfx.particles.burst(str(look[1]), c + Vector3(0, 0.7, 0), Vector3.UP, clampf(r / 2.0, 1.0, 3.0), 2, tint)
	if bool(look[4]) and target != null and target.view != null:
		(target.view as UnitView).flash(0.6, tint, 0.3)
	if id == "clans_braid_lash" and target != null:
		vfx.particles.burst("dust_clash", _ground(caster.pos) + Vector3(0, 0.6, 0), Vector3.UP, 1.0, 1, tint)
	if caster.view != null:
		(caster.view as UnitView).flash(0.35, tint, 0.25)
	Audio.play_3d(str(look[2]), c, {"priority": 75})


## Lasting ground effects, reveals and fuse marks, drawn as frame marks from the sim's records.
func _draw_lasting() -> void:
	var now := FxClock.fx_now
	for g: Dictionary in world.abilities.ground_effects():
		var tint: Color = GROUND_TINT.get(str(g["id"]), Color(1, 1, 1, 0.3))
		var p: Vector3 = g["pos"]
		if not vfx.allow(p, 3) and str(g["id"]) != "swallowed_sun":
			continue
		var r := float(g["radius"])
		var left := int(g["ticks"]) * World.DT
		var fade := clampf(left / 0.5, 0.0, 1.0)
		var pulse := 0.85 + 0.15 * sin(TAU * now * (2.0 if str(g["id"]) == "naphtha_fire" else 0.5) + float(g["handle"]))
		var xf := vfx.marks.ground_xf(p, r, int(g["handle"]))
		vfx.marks.add_frame(xf, GroundMarks.Shape.DISC, Color(tint, tint.a * fade * pulse), 1.0, 0.0)
		vfx.marks.add_frame(xf, GroundMarks.Shape.SOFT_RING, Color(tint.lightened(0.3), 0.5 * fade), 0.12, 0.0)
		if str(g["id"]) == "naphtha_fire":
			# flames lick up from the burning ground: an ember burst at a hashed spot 6 times a second
			var beat := floori(now * 6.0)
			if beat != int(_ember_beat.get(int(g["handle"]), -1)):
				_ember_beat[int(g["handle"])] = beat
				var a := TAU * Juice.hash01(int(g["handle"]), beat, 5)
				var d := r * sqrt(Juice.hash01(int(g["handle"]), beat, 9))
				vfx.particles.burst("ember", _ground(p + Vector3(cos(a) * d, 0.0, sin(a) * d)) + Vector3(0, 0.2, 0),
					Vector3.UP, 0.5, 1, Color(1.0, 0.55, 0.2))
	var pid := world.local_player_id
	for rv: Dictionary in world.fog.reveals() if world.fog != null else []:
		if not world.is_ally(pid, int(rv["pid"])):
			continue
		var xf2 := vfx.marks.ground_xf(rv["pos"], float(rv["radius"]), int(rv["handle"]))
		vfx.marks.add_frame(xf2, GroundMarks.Shape.RING_DASHED, Color(0.95, 0.75, 0.4, 0.6), 0.04, 0.0)
	for u in world.unit_list:
		if u.alive and not u.buffs.is_empty() and world.buffs.has_buff(u, "buff_fuse_mark") and vfx.allow(u.pos):
			var k := 0.5 + 0.5 * sin(TAU * now * 3.0)
			vfx.marks.add_frame(vfx.marks.ground_xf(u.display_pos(), 0.9, u.id), GroundMarks.Shape.RING,
				Color(1.0, 0.3, 0.2, 0.5 + 0.4 * k), 0.12, 0.0)
