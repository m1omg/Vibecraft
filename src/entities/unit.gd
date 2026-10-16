class_name Unit
extends Node3D
## Every game object with an id (units, buildings, mines, critters). Simulation state lives in
## plain fields (`pos`, `facing`, ...) and is advanced only by `sim_tick` from the fixed World
## tick; the Node3D transform is written once per tick so physics interpolation smooths it.
##
## Order state machine (one `current` order + shift queue) with combat behaviour:
## - idle units auto-acquire enemies within `acquire_range`, chase them up to `leash_range` from
##   their guard position and walk back when leashed (creeps always return to their camp);
## - HOLD attacks only what is already in weapon range and never moves;
## - ATTACK chases one target until it dies (no leash);
## - ATTACK_MOVE / PATROL follow their path, engage anything acquired on the way, then resume.
## An attack is a swing: wind-up (damage point) -> hit or projectile -> backswing. The weapon
## cooldown starts with the swing. All timers are integer tick counts (exact, deterministic).

const ARRIVE_EPS := 0.2
const WAYPOINT_EPS := 0.45
const SEPARATION_GAIN := 6.0
const PUSH_GAIN := 7.0
const NEIGHBOUR_PAD := 1.2       ## added to own radius for the neighbour query
const STALL_TICKS_NEAR := 8
const STALL_TICKS_FAR := 45
const MAX_REPATHS := 3
const INVENTORY_SLOTS := 6
const SCAN_TICKS := 5            ## auto-acquire scan interval (staggered by id)
const REPATH_TICKS := 10         ## min ticks between chase path requests
const REPATH_DIST := 1.0         ## target drift (m) that makes a chase path stale
const FACE_TOLERANCE := 0.35     ## rad; a swing starts only when roughly facing the target
const RANGE_BUFFER := 2.5        ## a swing still connects if the target stepped back this far
const CHASE_SLACK := 3.0         ## an acquired target beyond acquire range + this is dropped
const MAX_TARGET_RADIUS := 3.0   ## largest structure half-size; pads acquisition queries
const STRUCTURE_PENALTY := 6.0   ## acquisition prefers units over structures (metres)
const BLOCKED_TICKS := 45        ## chasing without progress this long -> try another target
const SKIP_TICKS := 90           ## how long a given-up target is ignored by acquisition
const HOME_EPS := 1.5            ## creeps further than this from camp walk back when calm
const FOLLOW_DIST := 1.2
const GATHER_REACH := 0.8

static var _scan_buf: Array = []

# identity
var id: int = 0
var def_id: String = ""
var def: Dictionary = {}
var player_id: int = 0
var team: int = 0
var world: World

# stats (from def)
var hp: float = 1.0
var max_hp: float = 1.0
var mana: float = 0.0
var max_mana: float = 0.0
var armor: float = 0.0
var armor_type: String = "unarmored"
var radius: float = 0.4
var speed: float = 0.0
var sight: float = 10.0
var turn_rate: float = 12.0
var is_building: bool = false
var is_hero: bool = false
var is_worker: bool = false
var is_resource: bool = false
var is_flying: bool = false
var is_invulnerable: bool = false
var attack: Dictionary = {}
var abilities: Array = []
var buffs: Array = []
var carry_gold: int = 0
var carry_lumber: int = 0
var hero: Dictionary = {}
var inventory: Array = []

# weapon (from def.attack; timings converted to ticks)
var attack_type: String = ""
var damage_min: int = 0
var damage_max: int = 0
var attack_range: float = 0.0
var acquire_range: float = 0.0   ## 0 = never auto-acquires or retaliates (workers)
var leash_range: float = 14.0
var projectile: Dictionary = {}  ## empty = melee
var cooldown_ticks: int = 1
var damage_point_ticks: int = 0
var backswing_ticks: int = 0

# orders
var orders: Array[Order] = []
var current: Order = null
var rally_pos: Vector3 = Vector3.INF  ## structures that train units
var rally_id: int = 0

# sim state
var pos: Vector3 = Vector3.ZERO
var prev_pos: Vector3 = Vector3.ZERO
var facing: float = 0.0           ## yaw; forward = (-sin, 0, -cos)
var velocity: Vector3 = Vector3.ZERO
var alive: bool = true
var died_tick: int = -1
var holding: bool = false
var hash_bucket: int = -1
var footprint: Rect2i = Rect2i()
var push_accum: Vector3 = Vector3.ZERO
var view: Node3D = null

# movement
var path: PackedVector3Array = PackedVector3Array()
var path_i: int = 0
var _need_path: bool = false
var _arrived: bool = false        ## current path finished (consumed by the order logic)
var _goal: Vector3 = Vector3.ZERO
var _stall: int = 0
var _repaths: int = 0
var _patrol_from: Vector3 = Vector3.ZERO
var _nbuf: Array = []

# combat
var _cooldown: int = 0            ## ticks until the weapon is ready
var _swing: int = -1              ## ticks into the current swing, -1 = not swinging
var _swing_target: int = 0
var _swing_fired: bool = false
var _engage_id: int = 0           ## auto-acquired target (idle / hold / attack-move / patrol)
var _engage_dist: float = 0.0     ## edge distance when engaged (retaliation can start far away)
var _guard_pos: Vector3 = Vector3.ZERO
var _home: Vector3 = Vector3.ZERO
var _returning: bool = false
var _resume: bool = false         ## attack-move must re-path to its goal after a fight
var _repath_cd: int = 0
var _blocked: int = 0
var _skip_id: int = 0
var _skip_ticks: int = 0


func setup(w: World, uid: int, did: String, pid: int, p: Vector3) -> void:
	world = w
	id = uid
	def_id = did
	player_id = pid
	team = w.team_of(pid) if w != null else pid
	name = "%s_%d" % [did, uid]
	def = Defs.unit(did)
	_apply_def()
	pos = p
	if w != null and w.map != null:
		pos.y = w.map.height_at(p.x, p.z)
	prev_pos = pos
	_home = pos
	_guard_pos = pos
	_commit_transform()


func _apply_def() -> void:
	max_hp = float(def.get("hp", 1))
	hp = max_hp
	max_mana = float(def.get("mana", 0))
	mana = max_mana
	armor = float(def.get("armor", 0))
	armor_type = str(def.get("armor_type", "unarmored"))
	radius = float(def.get("radius", 0.4))
	speed = float(def.get("speed", 0.0))
	sight = float(def.get("sight", 10.0))
	turn_rate = float(def.get("turn_rate", 12.0))
	leash_range = float(def.get("leash", 14.0))
	var kind: String = def.get("kind", "unit")
	var f: Array = def.get("flags", [])
	is_building = kind == "building"
	is_resource = kind == "resource"
	is_worker = f.has("worker")
	is_hero = f.has("hero")
	is_flying = f.has("flying")
	is_invulnerable = f.has("invulnerable")
	attack = def.get("attack", {})
	abilities = (def.get("abilities", []) as Array).duplicate()
	inventory.resize(INVENTORY_SLOTS)
	_apply_attack()


func _apply_attack() -> void:
	if attack.is_empty():
		return
	attack_type = str(attack.get("type", "blade"))
	var dmg: Array = attack.get("damage", [0, 0])
	damage_min = int(dmg[0])
	damage_max = int(dmg[1])
	attack_range = float(attack.get("range", 0.5))
	acquire_range = float(attack.get("acquire", 0.0))
	projectile = attack.get("projectile", {})
	cooldown_ticks = maxi(1, _to_ticks(attack.get("cooldown", 1.0)))
	damage_point_ticks = _to_ticks(attack.get("damage_point", 0.4))
	backswing_ticks = _to_ticks(attack.get("backswing", 0.4))


static func _to_ticks(seconds: Variant) -> int:
	return maxi(0, roundi(float(seconds) * World.TICK_RATE))


func is_mobile() -> bool:
	return speed > 0.0 and not is_building and not is_resource


func is_large() -> bool:
	return radius > Pathing.LARGE_RADIUS


func is_idle() -> bool:
	return current == null


func is_creep() -> bool:
	return player_id == PlayerState.NEUTRAL_HOSTILE


func can_attack() -> bool:
	return alive and damage_max > 0


func can_train() -> bool:
	return is_building and not (def.get("trains", []) as Array).is_empty()


## Unit the weapon is busy with (swing or engagement), 0 = none. For UI/AI, read-only.
func combat_target_id() -> int:
	if _swing >= 0:
		return _swing_target
	if current != null and current.type == Order.Type.ATTACK:
		return current.target_id
	return _engage_id


## Interpolated display position (for fx/UI drawn in _process).
func display_pos() -> Vector3:
	return prev_pos.lerp(pos, Engine.get_physics_interpolation_fraction())


func top_height() -> float:
	return float(def.get("height", 1.5)) * float(def.get("scale", 1.0))


## Where projectiles aim and hit text appears.
func hit_point() -> Vector3:
	var k := 0.5 if footprint.size != Vector2i.ZERO else 0.6
	return pos + Vector3(0.0, top_height() * k, 0.0)


func launch_point(toward: Vector3) -> Vector3:
	var d := Vector3(toward.x - pos.x, 0.0, toward.z - pos.z)
	d = d.normalized() if d.length_squared() > 1e-6 else Vector3(-sin(facing), 0.0, -cos(facing))
	return pos + d * radius + Vector3(0.0, top_height() * 0.7, 0.0)


## Distance between this unit's edge and `o`'s edge (footprint rectangle for structures).
func edge_distance(o: Unit) -> float:
	if o.footprint.size != Vector2i.ZERO:
		var x0 := o.footprint.position.x * Grid.CELL
		var z0 := o.footprint.position.y * Grid.CELL
		var cx := clampf(pos.x, x0, x0 + o.footprint.size.x * Grid.CELL)
		var cz := clampf(pos.z, z0, z0 + o.footprint.size.y * Grid.CELL)
		return maxf(Vector2(pos.x - cx, pos.z - cz).length() - radius, 0.0)
	return maxf(Grid.flat_dist(pos, o.pos) - radius - o.radius, 0.0)


## Swing progress 0..1 for animation (-1 when not attacking). Visual only.
func swing_progress() -> float:
	var total := damage_point_ticks + backswing_ticks
	if _swing < 0 or total <= 0:
		return -1.0
	return clampf((_swing + Engine.get_physics_interpolation_fraction()) / total, 0.0, 1.0)


func damage_point_ratio() -> float:
	var total := damage_point_ticks + backswing_ticks
	return float(damage_point_ticks) / total if total > 0 else 0.0


## Seconds since death, interpolated between ticks (visual only).
func dead_time() -> float:
	if died_tick < 0 or world == null:
		return 0.0
	return (world.tick_count - died_tick + Engine.get_physics_interpolation_fraction()) * World.DT


## How long the corpse stays before World removes it.
func decay_ticks() -> int:
	var key := "structure_decay" if footprint.size != Vector2i.ZERO else "corpse_decay"
	return _to_ticks(def.get("decay", Defs.combat_default(key, 8.0)))


# --- orders --------------------------------------------------------------------------------

func issue_order(o: Order, queue: bool = false) -> void:
	if not alive:
		return
	if o.type == Order.Type.RALLY:
		if can_train():
			rally_pos = o.target_pos
			rally_id = o.target_id
			Events.order_issued.emit(self, o)
		return
	if not is_mobile():
		return
	if o.type == Order.Type.ATTACK and o.target_id == 0:
		o.type = Order.Type.ATTACK_MOVE
	if o.type == Order.Type.STOP:
		orders.clear()
		_cancel_swing()
		_returning = false
		_finish_current(false)
		Events.order_issued.emit(self, o)
		return
	if queue and current != null:
		orders.append(o)
	else:
		orders.clear()
		_start(o)
	Events.order_issued.emit(self, o)


func clear_orders() -> void:
	orders.clear()
	_finish_current(false)


func _start(o: Order) -> void:
	if not (o.type == Order.Type.ATTACK and o.target_id == _swing_target):
		_cancel_swing()
	current = o
	holding = false
	_engage_id = 0
	_returning = false
	_resume = false
	_blocked = 0
	_repath_cd = 0
	_stop_moving()
	match o.type:
		Order.Type.HOLD:
			holding = true
		Order.Type.PATROL:
			_patrol_from = pos
			_begin_move(o.target_pos)
		Order.Type.ATTACK, Order.Type.FOLLOW, Order.Type.GATHER:
			pass                      # chase their target unit every tick
		_:
			_begin_move(_order_goal(o))


func _order_goal(o: Order) -> Vector3:
	if o.target_id != 0 and world != null:
		var t := world.get_unit(o.target_id)
		if t != null:
			return t.pos
	return o.target_pos


func _begin_move(goal: Vector3) -> void:
	_goal = goal
	_need_path = true
	_arrived = false
	path.clear()
	path_i = 0
	_stall = 0
	_repaths = 0


func _stop_moving() -> void:
	path.clear()
	path_i = 0
	_need_path = false
	_arrived = false
	_stall = 0


func _on_path_end() -> void:
	path.clear()
	path_i = 0
	_need_path = false
	_arrived = true


func _finish_current(advance: bool = true) -> void:
	current = null
	holding = false
	_engage_id = 0
	_resume = false
	_stop_moving()
	_guard_pos = pos
	if advance and not orders.is_empty():
		_start(orders.pop_front())


# --- simulation ----------------------------------------------------------------------------

func sim_tick(dt: float) -> void:
	prev_pos = pos
	if not alive:
		return
	_tick_timers()
	if not is_mobile():
		return
	var desired := Vector3.ZERO
	if _swing >= 0:
		_advance_swing(dt)
	else:
		desired = _think(dt)
	_steer_and_move(desired, dt)
	_update_stall(desired, dt)
	_commit_transform()


func _tick_timers() -> void:
	if _cooldown > 0:
		_cooldown -= 1
	if _repath_cd > 0:
		_repath_cd -= 1
	if _skip_ticks > 0:
		_skip_ticks -= 1
		if _skip_ticks == 0:
			_skip_id = 0


## Order logic for one tick; returns the desired velocity.
func _think(dt: float) -> Vector3:
	if current == null:
		return _idle(dt)
	match current.type:
		Order.Type.HOLD:
			return _hold(dt)
		Order.Type.ATTACK:
			return _attack_target(dt)
		Order.Type.ATTACK_MOVE, Order.Type.PATROL:
			return _attack_move(dt)
		Order.Type.FOLLOW:
			return _follow(dt)
		Order.Type.GATHER:
			return _gather(dt)
	return _move(dt)


func _move(dt: float) -> Vector3:
	var d := _follow_path(dt)
	if _arrived:
		_finish_current()
	return d


func _idle(dt: float) -> Vector3:
	if _returning:
		var d := _follow_path(dt)
		if _arrived:
			_returning = false
			_stop_moving()
			_guard_pos = pos
		return d
	var t := _engaged()
	if t == null:
		t = _scan(acquire_range)
		if t == null:
			_settle()
			return Vector3.ZERO
		_engage(t)
	if Grid.flat_dist(pos, _guard_pos) > leash_range or _lost(t):
		_give_up(t)
		_return_to(_guard_pos)
		return Vector3.ZERO
	return _fight(t, dt, true)


## Calm idle unit: guard position follows it; creeps walk back to their camp.
func _settle() -> void:
	if is_creep():
		_guard_pos = _home
		if Grid.flat_dist(pos, _home) > HOME_EPS and (world.tick_count + id) % SCAN_TICKS == 0:
			_return_to(_home)
	elif _engage_id == 0:
		_guard_pos = pos


func _hold(dt: float) -> Vector3:
	var t := _engaged()
	if t != null and edge_distance(t) > attack_range:
		_engage_id = 0
		t = null
	if t == null:
		t = _scan(attack_range)
		if t == null:
			return Vector3.ZERO
		_engage_id = t.id
	return _fight(t, dt, false)


func _attack_target(dt: float) -> Vector3:
	var t := world.get_unit(current.target_id)
	if t == null or not t.alive or t == self:
		_finish_current()
		return Vector3.ZERO
	if not can_attack():
		return _chase_move(t, dt)
	return _fight(t, dt, true)


func _attack_move(dt: float) -> Vector3:
	var t := _engaged()
	if t != null and _lost(t):
		_give_up(t)
		t = null
	if t == null:
		t = _scan(acquire_range)
		if t != null:
			_engage(t)
			_resume = true
	if t != null:
		return _fight(t, dt, true)
	if _resume:
		_resume = false
		_begin_move(current.target_pos)
	var d := _follow_path(dt)
	if _arrived:
		if current.type == Order.Type.PATROL:
			var back := _patrol_from
			_patrol_from = current.target_pos
			current.target_pos = back
			_begin_move(back)
		else:
			_finish_current()
	return d


func _follow(dt: float) -> Vector3:
	var t := world.get_unit(current.target_id)
	if t == null or not t.alive:
		_finish_current()
		return Vector3.ZERO
	if edge_distance(t) <= FOLLOW_DIST:
		_stop_moving()
		return Vector3.ZERO
	return _chase_move(t, dt)


## Gather stub until economy.gd exists: walk to the resource, then hand over to
## World.gather_handler (economy hook) and complete.
func _gather(dt: float) -> Vector3:
	var t := world.get_unit(current.target_id)
	if t == null or not t.alive:
		_finish_current()
		return Vector3.ZERO
	if edge_distance(t) <= GATHER_REACH:
		world.on_gather_reached(self, t)
		_finish_current()
		return Vector3.ZERO
	return _chase_move(t, dt)


# --- targeting -----------------------------------------------------------------------------

func is_valid_target(o: Unit) -> bool:
	return o != self and o.alive and not o.is_resource and not o.is_invulnerable \
		and world.is_enemy(player_id, o.player_id)


## Closest valid enemy whose edge is within `r` (units preferred over structures).
func find_target(r: float) -> Unit:
	var best: Unit = null
	var best_score := INF
	world.spatial.query_radius(pos, r + radius + MAX_TARGET_RADIUS, _scan_buf)
	for o: Unit in _scan_buf:
		if o.id == _skip_id or not is_valid_target(o):
			continue
		var d := edge_distance(o)
		if d > r:
			continue
		var score := d + (STRUCTURE_PENALTY if o.footprint.size != Vector2i.ZERO else 0.0)
		if score < best_score or (score == best_score and o.id < best.id):
			best_score = score
			best = o
	_scan_buf.clear()
	return best


## Throttled acquisition (every SCAN_TICKS, staggered by id so scans spread over ticks).
func _scan(r: float) -> Unit:
	if r <= 0.0 or not can_attack() or (world.tick_count + id) % SCAN_TICKS != 0:
		return null
	return find_target(r)


func _engaged() -> Unit:
	if _engage_id == 0:
		return null
	var t := world.get_unit(_engage_id)
	if t == null or not is_valid_target(t):
		_engage_id = 0
		_blocked = 0
		return null
	return t


func _engage(t: Unit) -> void:
	_engage_id = t.id
	_engage_dist = edge_distance(t)
	_blocked = 0
	_repath_cd = 0
	_returning = false
	_stop_moving()


## An auto-acquired target escaped or could not be reached.
func _lost(t: Unit) -> bool:
	return _blocked > BLOCKED_TICKS or edge_distance(t) > maxf(acquire_range, _engage_dist) + CHASE_SLACK


func _give_up(t: Unit) -> void:
	if _blocked > BLOCKED_TICKS:
		_skip_id = t.id
		_skip_ticks = SKIP_TICKS
	_engage_id = 0
	_blocked = 0
	_stop_moving()


func _return_to(p: Vector3) -> void:
	_returning = true
	_begin_move(p)


## Fight back when hit while idle or attack-moving; creeps also wake their camp.
func _on_attacked(src: Unit) -> void:
	if acquire_range <= 0.0 or not can_attack() or not is_valid_target(src) or _engage_id != 0:
		return
	if _returning and is_creep():
		return
	if current != null and current.type != Order.Type.ATTACK_MOVE and current.type != Order.Type.PATROL:
		return
	_engage(src)
	if current != null:
		_resume = true
	if is_creep():
		_call_for_help(src)


func _call_for_help(src: Unit) -> void:
	var r := float(Defs.combat_default("help_radius", 6.0))
	var mates := world.spatial.query_radius(pos, r, [])
	for m: Unit in mates:
		if m != self and m.alive and m.player_id == player_id and m.current == null \
				and m._engage_id == 0 and not m._returning and m.can_attack():
			m._engage(src)


# --- attacking -----------------------------------------------------------------------------

## Attacks `t` when in weapon range (turning to face it first); otherwise chases it if allowed.
func _fight(t: Unit, dt: float, can_chase: bool) -> Vector3:
	if edge_distance(t) <= attack_range:
		_stop_moving()
		_blocked = 0
		if _face(t.pos, dt) and _cooldown == 0:
			_begin_swing(t)
		return Vector3.ZERO
	if not can_chase:
		return Vector3.ZERO
	if velocity.length_squared() < speed * speed * 0.0625:
		_blocked += 1
	else:
		_blocked = maxi(_blocked - 1, 0)
	return _chase_move(t, dt)


## Moves towards a (possibly moving) unit. Paths are re-requested at most every REPATH_TICKS
## and only when the target drifted; at a stale goal the unit steers straight at the target.
func _chase_move(t: Unit, dt: float) -> Vector3:
	var goal := t.pos
	var no_path := path.is_empty() and not _need_path
	if _repath_cd == 0 and (no_path or _arrived or Grid.flat_dist(_goal, goal) > REPATH_DIST):
		_begin_move(goal)
		_repath_cd = REPATH_TICKS
	var d := _follow_path(dt)
	if d == Vector3.ZERO and not _need_path:
		d = _steer_direct(goal, dt)
	return d


func _steer_direct(goal: Vector3, dt: float) -> Vector3:
	var to := Vector3(goal.x - pos.x, 0.0, goal.z - pos.z)
	var l := to.length()
	if l < 0.05:
		return Vector3.ZERO
	return to / l * minf(speed, l / dt)


## Turns towards `p`; true once facing it within FACE_TOLERANCE.
func _face(p: Vector3, dt: float) -> bool:
	var dx := p.x - pos.x
	var dz := p.z - pos.z
	if dx * dx + dz * dz < 1e-6:
		return true
	var want := atan2(-dx, -dz)
	facing = rotate_toward(facing, want, turn_rate * dt)
	return absf(angle_difference(facing, want)) <= FACE_TOLERANCE


func _begin_swing(t: Unit) -> void:
	_swing = 0
	_swing_target = t.id
	_swing_fired = false
	_cooldown = cooldown_ticks
	if damage_point_ticks == 0:
		_release(t)


func _advance_swing(dt: float) -> void:
	var t := world.get_unit(_swing_target)
	var valid := t != null and t.alive
	if valid:
		_face(t.pos, dt)
	_swing += 1
	if not _swing_fired:
		if not valid:
			_cancel_swing()
			return
		if _swing >= damage_point_ticks:
			_release(t)
	if _swing_fired and _swing >= damage_point_ticks + backswing_ticks:
		_swing = -1


## Damage point reached: melee hits now, ranged launches its projectile.
func _release(t: Unit) -> void:
	_swing_fired = true
	if edge_distance(t) <= attack_range + RANGE_BUFFER:
		world.combat.fire(self, t)


## Interrupting a wind-up wastes nothing (the weapon is ready again); a backswing just ends.
func _cancel_swing() -> void:
	if _swing >= 0 and not _swing_fired:
		_cooldown = 0
	_swing = -1
	_swing_fired = false


# --- movement ------------------------------------------------------------------------------

func _follow_path(dt: float) -> Vector3:
	if _arrived:
		return Vector3.ZERO
	if _need_path:
		if not world.pathing.has_budget():
			return Vector3.ZERO
		path = world.pathing.find_path(pos, _goal, is_large())
		path_i = 1
		_need_path = false
		if path.size() < 2:
			_on_path_end()
			return Vector3.ZERO
	if path_i >= path.size():
		_on_path_end()
		return Vector3.ZERO
	var wp := path[path_i]
	var to := Vector2(wp.x - pos.x, wp.z - pos.z)
	var dist := to.length()
	var last := path_i == path.size() - 1
	if last and dist < ARRIVE_EPS:
		_on_path_end()
		return Vector3.ZERO
	if not last and dist < WAYPOINT_EPS:
		path_i += 1
		return _follow_path(dt)
	var spd := speed
	if last:
		spd = minf(speed, dist / dt)
	var dir := to / dist
	return Vector3(dir.x, 0.0, dir.y) * spd


func _steer_and_move(desired: Vector3, dt: float) -> void:
	var moving := desired != Vector3.ZERO
	var sep := Vector3.ZERO
	var nbrs := world.spatial.query_radius(pos, radius + NEIGHBOUR_PAD, _nbuf)
	for n: Unit in nbrs:
		if n == self or not n.alive or n.is_flying != is_flying or not n.is_mobile():
			continue
		var dx := pos.x - n.pos.x
		var dz := pos.z - n.pos.z
		var min_d := radius + n.radius
		var d2 := dx * dx + dz * dz
		if d2 >= min_d * min_d:
			continue
		var d := sqrt(d2)
		var nrm := Vector3(dx / d, 0.0, dz / d) if d > 0.0001 else Vector3(1.0 if id > n.id else -1.0, 0.0, 0.0)
		var overlap := min_d - d
		if moving and _can_push(n):
			n.push_accum -= nrm * overlap
			sep += nrm * overlap * 0.25
		else:
			sep += nrm * overlap
	var vel := desired
	if not holding:
		vel += sep * SEPARATION_GAIN + push_accum * PUSH_GAIN
	push_accum = Vector3.ZERO
	vel = vel.limit_length(speed * 1.25)
	_try_move(vel * dt)
	velocity = (pos - prev_pos) / dt
	velocity.y = 0.0
	if moving:
		_turn_towards(desired, dt)


## Moving units shove idle, calm allies of the same player out of the way (never fighters).
func _can_push(n: Unit) -> bool:
	return n.player_id == player_id and n.current == null and not n.holding \
		and n._engage_id == 0 and n._swing < 0 and not n._returning


func _turn_towards(dir: Vector3, dt: float) -> void:
	var target := atan2(-dir.x, -dir.z)
	facing = rotate_toward(facing, target, turn_rate * dt)


## Moves by `delta` on XZ, sliding along blocked cells. Units standing in a blocked cell
## (spawned inside a footprint, pushed onto a tree edge) may move freely to escape.
func _try_move(delta: Vector3) -> void:
	if delta.length_squared() < 1e-10:
		return
	var p := world.pathing
	var np := Vector3(pos.x + delta.x, 0.0, pos.z + delta.z)
	if not p.is_walkable_world(pos) or p.is_walkable_world(np):
		pos.x = np.x
		pos.z = np.z
	elif p.is_walkable_world(Vector3(np.x, 0.0, pos.z)):
		pos.x = np.x
	elif p.is_walkable_world(Vector3(pos.x, 0.0, np.z)):
		pos.z = np.z
	else:
		return
	var size := world.map.size_world()
	pos.x = clampf(pos.x, 0.0, size.x)
	pos.z = clampf(pos.z, 0.0, size.y)
	pos.y = world.map.height_at(pos.x, pos.z)
	world.spatial.update(self)


func _update_stall(desired: Vector3, dt: float) -> void:
	if desired == Vector3.ZERO or path.is_empty():
		_stall = 0
		return
	var moved := Vector2(pos.x - prev_pos.x, pos.z - prev_pos.z).length()
	if moved < desired.length() * dt * 0.3:
		_stall += 1
	else:
		_stall = maxi(_stall - 1, 0)
	var end := path[path.size() - 1]
	var remaining := Vector2(end.x - pos.x, end.z - pos.z).length()
	var crowd := radius * 4.0 + 1.0
	if remaining < crowd and _stall > STALL_TICKS_NEAR:
		_on_path_end()
	elif _stall > STALL_TICKS_FAR:
		_stall = 0
		if _repaths < MAX_REPATHS:
			_repaths += 1
			_need_path = true
		else:
			_on_path_end()


func _commit_transform() -> void:
	transform = Transform3D(Basis(Vector3.UP, facing), pos)


## Instant relocation without interpolating across the jump.
func teleport(p: Vector3) -> void:
	pos = p
	if world != null and world.map != null:
		pos.y = world.map.height_at(p.x, p.z)
	prev_pos = pos
	if world != null:
		world.spatial.update(self)
	_commit_transform()
	reset_physics_interpolation()


# --- damage & death (damage resolution lives in systems/combat.gd) -------------------------

func take_damage(amount: float, src: Unit = null) -> void:
	if not alive or is_invulnerable:
		return
	hp = maxf(hp - amount, 0.0)
	Events.unit_damaged.emit(self, amount, src)
	if hp <= 0.0:
		die(src)
	elif src != null and src.alive:
		_on_attacked(src)


func die(killer: Unit = null) -> void:
	if not alive:
		return
	alive = false
	orders.clear()
	current = null
	holding = false
	_swing = -1
	_engage_id = 0
	_stop_moving()
	velocity = Vector3.ZERO
	prev_pos = pos
	if world != null:
		died_tick = world.tick_count
		world.mark_dead(self, killer)
