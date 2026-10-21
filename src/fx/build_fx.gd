class_name BuildFx
extends Node
## Economy and building juice, Playtest 2's P0 subset (juice ECO-04, ECO-08, ECO-11, ECO-16,
## BLD-04, BLD-08, BLD-09, BLD-12, BLD-14, BLD-16, BLD-20). Visual and audio only; owned by Vfx.
##   - a site starts: a dust ring the size of the footprint, dust at its corners, the stamp thud;
##   - every builder's or chopper's stroke lands on the work clip's contact (Unit.work_progress
##     crossing Unit.work_point_ratio, the same at any refresh rate): sawdust and the kingdom
##     hammer or the clans mallet; splinters and the axe thunk at the tree;
##   - a building completes: a warm flash on it, a ring, rising stars, the topping-out chime and,
##     for the local player's supply, "+N" food rising off it;
##   - a hall upgrade completes: a bigger flash, two rings, more stars, the raising chord;
##   - a tree falls: splinters, dust and the thud; a load is delivered: coins or logs;
##   - a structure falls: dust and smoke across the footprint, a ring and the cave-in;
##   - the local player's unit leaves the door: a dust puff and its Ready line; their research
##     completes: a chime.
## Handlers only enqueue (Vfx's rule: nothing plays inside the fixed tick); the queue drains in
## `_process`. Off-screen and fogged events are skipped through Vfx.allow.

const DUST := Color(0.72, 0.64, 0.5)
const WARM := Color(1.0, 0.86, 0.55)
const FLASH := Color(1.0, 0.93, 0.75)
const TREE_FALL_FROM_S := 0.55    ## the fall sample starts late: the stump is already there

var vfx: Vfx
var world: World
## Beats played, by kind (stamp, stroke, chop, complete, tier, tree, cargo, collapse, ready):
## tests and the feel trace read it.
var counts: Dictionary = {}
var _queue: Array = []
var _struck: Dictionary = {}      ## unit id -> work_t0 of the stroke already struck
var _links: Array = []


func setup(v: Vfx, w: World) -> void:
	vfx = v
	world = w
	_link(Events.construction_started, func(site: Node, _b: Node) -> void: _queue.append(["stamp", site]))
	_link(Events.building_completed, func(site: Node) -> void: _queue.append(["complete", site]))
	_link(Events.building_upgraded, func(b: Node, _from: String) -> void: _queue.append(["tier", b]))
	_link(Events.tree_felled, func(pos: Vector3) -> void: _queue.append(["tree", pos]))
	_link(Events.cargo_delivered, func(_w: Node, b: Node, kind: String, _n: int) -> void: _queue.append(["cargo", b, kind]))
	_link(Events.unit_died, func(u: Node, _k: Node) -> void:
		if (u as Unit) != null and (u as Unit).is_building:
			_queue.append(["collapse", u]))
	_link(Events.training_completed, func(_b: Node, u: Node) -> void: _queue.append(["ready", u]))
	_link(Events.research_completed, func(pid: int, _id: String) -> void: _queue.append(["research", pid]))


func _link(sig: Signal, cb: Callable) -> void:
	sig.connect(cb)
	_links.append([sig, cb])


func _exit_tree() -> void:
	for pair: Array in _links:
		var sig: Signal = pair[0]
		if sig.is_connected(pair[1]):
			sig.disconnect(pair[1])
	_links.clear()


func _process(_delta: float) -> void:
	if world == null or not is_instance_valid(world):
		return
	if not _queue.is_empty():
		var q := _queue
		_queue = []
		for rec: Array in q:
			_play(rec)
	_strokes()


func _play(rec: Array) -> void:
	match str(rec[0]):
		"stamp":
			if is_instance_valid(rec[1]):
				_stamp(rec[1])
		"complete":
			if is_instance_valid(rec[1]):
				_complete(rec[1], false)
		"tier":
			if is_instance_valid(rec[1]):
				_complete(rec[1], true)
		"tree":
			_tree(rec[1])
		"cargo":
			if is_instance_valid(rec[1]):
				_cargo(rec[1], str(rec[2]))
		"collapse":
			if is_instance_valid(rec[1]):
				_collapse(rec[1])
		"ready":
			if is_instance_valid(rec[1]):
				_ready_unit(rec[1])
		"research":
			if int(rec[1]) == world.local_player_id:
				Audio.play_2d("ui_research_done", {"volume_db": -4.0})


func _count(kind: String) -> void:
	counts[kind] = int(counts.get(kind, 0)) + 1
	vfx.trace("BLD." + kind, 0)


## Footprint half-size in metres (a 1 m minimum).
static func half_size(u: Unit) -> Vector2:
	return Vector2(maxf(u.footprint.size.x * Grid.CELL * 0.5, 0.5), maxf(u.footprint.size.y * Grid.CELL * 0.5, 0.5))


func _ground(p: Vector3) -> Vector3:
	return Vector3(p.x, world.map.height_at(p.x, p.z), p.z)


## BLD-04: the site is staked out.
func _stamp(site: Unit) -> void:
	var c := _ground(site.pos)
	if not vfx.allow(c):
		return
	_count("stamp")
	var h := half_size(site)
	var r := maxf(h.x, h.y)
	vfx.marks.add(GroundMarks.Kind.DUST_RING, c, r * 0.7, r * 1.35, Color(DUST, 0.5), 0.7, 0.0, 0.0, null, false)
	for corner: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
		vfx.particles.burst("dust_land", _ground(c + Vector3(corner.x * h.x, 0, corner.y * h.y)) + Vector3(0, 0.1, 0),
			Vector3.UP, 0.8, 2)
	Audio.play_3d("bld_stamp", c, {"priority": 60})


## BLD-08 / ECO-08: strokes land on the work clip's contact frame.
func _strokes() -> void:
	for u in world.unit_list:
		if u.anim_hint != "work" or u.hidden or not u.alive or u.current == null:
			continue
		var p := u.work_progress()
		if p < u.work_point_ratio() or int(_struck.get(u.id, -1)) == u.work_t0:
			continue
		_struck[u.id] = u.work_t0
		var o := u.current
		match o.type:
			Order.Type.BUILD, Order.Type.REPAIR:
				_hammer(u)
			Order.Type.GATHER:
				if o.target_id == 0:
					_chop(u, o)


func _contact(u: Unit, reach: float) -> Vector3:
	var fwd := Vector3(-sin(u.facing), 0.0, -cos(u.facing))
	return u.display_pos() + fwd * (u.radius + reach) + Vector3(0, 0.45, 0)


func _hammer(u: Unit) -> void:
	var at := _contact(u, 0.35)
	if not vfx.allow(at):
		return
	_count("stroke")
	var clans := ViewHooks.faction_of(u) == "clans"
	vfx.particles.burst("chaff" if clans else "sawdust", at, Vector3.UP, 0.5, 1)
	Audio.play_3d("bld_mallet" if clans else "bld_hammer", at, {"priority": 30, "volume_db": -3.0})


func _chop(u: Unit, o: Order) -> void:
	var tree := int(o.data.get("tree", -1))
	var at := world.doodads.tree_pos(tree) + Vector3(0, 0.8, 0) if tree >= 0 else _contact(u, 0.4)
	if not vfx.allow(at):
		return
	_count("chop")
	var from_u := (u.display_pos() - at)
	from_u.y = 0.0
	vfx.particles.burst("splinter", at, (from_u.normalized() + Vector3.UP * 0.6).normalized(), 0.5, 1)
	Audio.play_3d("eco_chop", at, {"priority": 30, "volume_db": -3.0})


## BLD-09 / BLD-20 / ECO-16: done (or raised a tier).
func _complete(b: Unit, tier_up: bool) -> void:
	var c := _ground(b.pos)
	var top := c + Vector3(0, b.top_height(), 0)
	if b.player_id == world.local_player_id and int(b.def.get("food_provided", 0)) > 0 and not tier_up:
		vfx.popups.show_value(PopupText.Style.FOOD, int(b.def.get("food_provided", 0)), top + Vector3(0, 0.6, 0))
	if not vfx.allow(c, 3):
		return
	_count("tier" if tier_up else "complete")
	var view := b.view as UnitView
	if view != null:
		view.flash(0.85 if tier_up else 0.6, FLASH, 0.6 if tier_up else 0.35)
	var h := half_size(b)
	var r := maxf(h.x, h.y)
	vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, r * 0.9, r * 1.6, Color(WARM, 0.55), 0.8, 0.0, 0.0, null, false)
	if tier_up:
		vfx.marks.add(GroundMarks.Kind.FLASH_RING, c, r * 1.2, r * 2.2, Color(WARM, 0.4), 1.1, 0.15, 0.0, null, false)
	for i in (5 if tier_up else 3):
		var a := TAU * float(i) / (5.0 if tier_up else 3.0)
		vfx.particles.burst("star_soft", top + Vector3(cos(a) * r * 0.5, 0.0, sin(a) * r * 0.5), Vector3.UP, 1.0, 2, WARM)
	Audio.play_3d("bld_tier_up" if tier_up else "bld_complete", c, {"priority": 70, "no_cut_ms": 600})


## ECO-11: the tree is down (the stump is already drawn by Doodads).
func _tree(pos: Vector3) -> void:
	var c := _ground(pos)
	if not vfx.allow(c):
		return
	_count("tree")
	vfx.particles.burst("splinter", c + Vector3(0, 1.2, 0), Vector3.UP, 1.0, 2)
	vfx.particles.burst("dust_land", c + Vector3(0, 0.1, 0), Vector3.UP, 1.0, 2)
	vfx.marks.add(GroundMarks.Kind.DUST_RING, c, 0.4, 1.8, Color(DUST, 0.45), 0.6, 0.0, 0.0, null, false)
	Audio.play_3d("eco_tree_fall", c, {"priority": 45, "from": TREE_FALL_FROM_S})


## ECO-04: the load lands (coins at the hall, logs on the pile); the income popup is CombatText's.
func _cargo(b: Unit, kind: String) -> void:
	var c := _ground(b.pos)
	if not vfx.allow(c):
		return
	_count("cargo")
	Audio.play_3d("eco_coin" if kind == "gold" else "eco_lumber_drop", c, {"priority": 35, "volume_db": -4.0})


## BLD-16: the cave-in.
func _collapse(b: Unit) -> void:
	var c := _ground(b.pos)
	if not vfx.allow(c):
		return
	_count("collapse")
	var h := half_size(b)
	var r := maxf(h.x, h.y)
	for i in 6:
		var a := TAU * float(i) / 6.0
		var p := c + Vector3(cos(a) * h.x * 0.7, 0.4, sin(a) * h.y * 0.7)
		vfx.particles.burst("dust_stone" if i % 2 == 0 else "smoke_puff", p, Vector3.UP, 1.0, 3)
	vfx.particles.burst("splinter", c + Vector3(0, 1.5, 0), Vector3.UP, 1.0, 3)
	vfx.marks.add(GroundMarks.Kind.DUST_RING, c, r * 0.8, r * 1.9, Color(DUST, 0.6), 1.2, 0.0, 0.0, null, false)
	Audio.play_3d("bld_collapse", c, {"priority": 80, "no_cut_ms": 800})


## BLD-12: out of the door (the local player's units say Ready).
func _ready_unit(u: Unit) -> void:
	if not u.alive:
		return
	_count("ready")
	var at := _ground(u.pos) + Vector3(0, 0.1, 0)
	if vfx.allow(at):
		vfx.particles.burst("dust_step", at, Vector3.UP, 1.0, 1)
	if u.player_id == world.local_player_id:
		Audio.play_voice(u, "ready")
