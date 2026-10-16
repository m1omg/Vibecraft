class_name World
extends Node3D
## Match root and fixed-step simulation driver. Gameplay advances only in `step()`, called once
## per physics tick (30 Hz) or manually by tests. Stage order is fixed (docs/architecture.md §4).

const TICK_RATE := 30
const DT := 1.0 / TICK_RATE
const STAGES: Array[StringName] = [&"orders", &"production", &"units", &"projectiles",
	&"abilities", &"economy", &"creeps", &"ai", &"fog", &"cleanup"]
## Stages World runs itself; systems cannot register for them.
const OWN_STAGES: Array[StringName] = [&"orders", &"units", &"cleanup"]
## Stages run after the units, in this order.
const LATE_STAGES: Array[StringName] = [&"projectiles", &"abilities", &"economy", &"creeps", &"ai",
	&"fog"]
const MAX_PLAYERS := SpatialHash.MAX_PLAYERS
const FORMATION_MAX_SPREAD := 8.0
const SPAWN_SNAP_CELLS := 16

@export var auto_tick: bool = true   ## false: tests call step() themselves
@export var visuals: bool = true     ## false: no meshes, views or fx (headless tests)

var tick_count: int = 0
var time: float = 0.0
var players: Array[PlayerState] = []
var entities: Dictionary = {}        ## id -> Unit
var unit_list: Array[Unit] = []      ## stable iteration order (spawn order)
var spatial: SpatialHash
var pathing: Pathing
var map: MapData
var fog: Node = null                 ## Fog system (added with the systems milestone)
var combat: Combat                   ## damage resolution + projectiles (stage `projectiles`)
## Largest mobile unit radius (from Defs): pads separation neighbour queries.
var max_unit_radius: float = 1.0
var local_player_id: int = 0
var rng := RandomNumberGenerator.new()
## Economy hook: Callable(worker: Unit, resource: Unit) run when a GATHER order reaches its
## resource. Until economy.gd exists nothing is attached and the order simply completes.
var gather_handler: Callable = Callable()

var _next_id: int = 1
var _pending: Array[Dictionary] = []
var _dead: Array = []                ## [Unit, killer]
var _corpses: Array[Unit] = []       ## dead, out of the sim, removed after their decay time
var _systems: Dictionary = {}        ## stage -> Array[Node] (sim_tick(world, dt)), registration order
var _hostile := PackedInt32Array()   ## player id -> bitmask of the player ids it is an enemy of

@onready var units_root: Node3D = _child_or_new("Units", Node3D) as Node3D
@onready var projectile_root: Node3D = _child_or_new("Projectiles", Node3D) as Node3D
@onready var systems_root: Node = _child_or_new("Systems", Node)
@onready var doodads: Doodads = _child_or_new("Doodads", Doodads) as Doodads
@onready var terrain: TerrainBuilder = get_node_or_null("Terrain") as TerrainBuilder
@onready var day_night: DayNight = get_node_or_null("DayNight") as DayNight


func _init() -> void:
	refresh_relations()
	for stage in STAGES:
		if is_system_stage(stage):
			_systems[stage] = [] as Array[Node]


func setup(m: MapData, seed_value: int = 1) -> void:
	map = m
	rng.seed = seed_value
	pathing = Pathing.new()
	pathing.setup(map)
	spatial = SpatialHash.new()
	spatial.setup(map.size_world())
	spatial.max_target_radius = Defs.max_target_radius
	max_unit_radius = Defs.max_unit_radius
	doodads.setup(self, map)
	combat = Combat.new()
	combat.setup(self)
	systems_root.add_child(combat)
	register_system(&"projectiles", combat)
	if visuals:
		if terrain != null:
			terrain.build(map)
		if day_night != null:
			day_night.setup(self)
		for fx_name: String in ["Fx/SelectionCircles", "Fx/HealthBars", "Fx/Vfx"]:
			var fx := get_node_or_null(fx_name)
			if fx != null:
				fx.setup(self)
	else:
		for n: String in ["Terrain", "DayNight", "Fx"]:
			var node := get_node_or_null(n)
			if node != null:
				node.queue_free()
		terrain = null
		day_night = null
	if Engine.physics_ticks_per_second != TICK_RATE:
		push_warning("World: physics_ticks_per_second is %d, expected %d" % [
			Engine.physics_ticks_per_second, TICK_RATE])


func _physics_process(_delta: float) -> void:
	if auto_tick and map != null:
		step()


## One fixed simulation tick. Never depends on render frame timing.
func step() -> void:
	tick_count += 1
	time = tick_count * DT
	pathing.begin_tick()
	_apply_commands()
	_run_stage(&"production")
	var n := unit_list.size()
	for i in n:
		unit_list[i].sim_tick(DT)
	for stage: StringName in LATE_STAGES:
		_run_stage(stage)
	_cleanup()


## Adds a system (a node with `sim_tick(world, dt)`) to a stage. Several systems may share a
## stage; they run in registration order. `orders`, `units` and `cleanup` are run by World
## itself and are rejected, as are unknown stages. Returns false when rejected.
func register_system(stage: StringName, system: Node) -> bool:
	if not is_system_stage(stage):
		push_error("World: systems cannot register for stage '%s'" % stage)
		return false
	var list: Array[Node] = _systems[stage]
	if not list.has(system):
		list.append(system)
	return true


static func is_system_stage(stage: StringName) -> bool:
	return STAGES.has(stage) and not OWN_STAGES.has(stage)


## Systems registered for a stage, in run order (a copy).
func systems_in(stage: StringName) -> Array[Node]:
	var out: Array[Node] = []
	if _systems.has(stage):
		out.assign(_systems[stage])
	return out


func _run_stage(stage: StringName) -> void:
	for s: Node in _systems[stage]:
		s.sim_tick(self, DT)


## Fraction of the current tick interval for visuals drawn in _process (the engine's physics
## interpolation fraction). Frozen at 1 while the World is paused: no ticks run then, so the
## last tick's state is shown instead of oscillating between the last two ticks.
func interpolation_fraction() -> float:
	if is_inside_tree() and not can_process():
		return 1.0
	return Engine.get_physics_interpolation_fraction()


# --- players -------------------------------------------------------------------------------

func add_player(pid: int, team_id: int, faction: String = "", ai: bool = false) -> PlayerState:
	assert(pid >= 0 and pid < MAX_PLAYERS, "player id out of range")
	var p := PlayerState.make(pid, team_id, faction, ai)
	players.append(p)
	refresh_relations()
	return p


func player(pid: int) -> PlayerState:
	for p in players:
		if p.id == pid:
			return p
	return null


func team_of(pid: int) -> int:
	var p := player(pid)
	return p.team if p != null else pid


func player_color(pid: int) -> Color:
	var p := player(pid)
	return p.color if p != null else PlayerState.COLORS[pid % PlayerState.COLORS.size()]


## O(1): reads the relation table (see refresh_relations).
func is_enemy(a: int, b: int) -> bool:
	if a < 0 or b < 0 or a >= MAX_PLAYERS or b >= MAX_PLAYERS:
		return _enemy_rule(a, b)
	return (_hostile[a] >> b) & 1 == 1


## Bitmask of the player ids `pid` is an enemy of (bit b set = enemy of player b).
func hostile_mask(pid: int) -> int:
	return _hostile[pid] if pid >= 0 and pid < MAX_PLAYERS else 0


func _enemy_rule(a: int, b: int) -> bool:
	if a == b or a == PlayerState.NEUTRAL_PASSIVE or b == PlayerState.NEUTRAL_PASSIVE:
		return false
	if a == PlayerState.NEUTRAL_HOSTILE or b == PlayerState.NEUTRAL_HOSTILE:
		return true
	return team_of(a) != team_of(b)


## Rebuilds the player x player enemy table. Called by add_player; call it again after changing
## a PlayerState.team.
func refresh_relations() -> void:
	_hostile.resize(MAX_PLAYERS)
	for a in MAX_PLAYERS:
		var m := 0
		for b in MAX_PLAYERS:
			if _enemy_rule(a, b):
				m |= 1 << b
		_hostile[a] = m


func is_ally(a: int, b: int) -> bool:
	return a == b or (not is_enemy(a, b) and team_of(a) == team_of(b))


# --- entities ------------------------------------------------------------------------------

func spawn_unit(def_id: String, pid: int, p: Vector3, facing: float = 0.0) -> Unit:
	var d := Defs.unit(def_id)
	if d.is_empty():
		return null
	var u := Unit.new()
	var spot := p
	if d["kind"] != "unit":
		var fp: Array = d["footprint"]
		var size := Vector2i(int(fp[0]), int(fp[1]))
		spot = Grid.snap_to_footprint(p, size)
		u.footprint = Grid.footprint_rect(spot, size)
	else:
		var c := pathing.nearest_walkable(Grid.world_to_cell(p), false, SPAWN_SNAP_CELLS)
		if c.x >= 0 and c != Grid.world_to_cell(p):
			spot = Grid.cell_to_world(c)
	u.facing = facing
	u.setup(self, _next_id, def_id, pid, spot)
	_next_id += 1
	if u.footprint.size != Vector2i.ZERO:
		pathing.set_footprint_rect(u.footprint, true)
	_count_food(u, 1)
	entities[u.id] = u
	unit_list.append(u)
	spatial.insert(u)
	units_root.add_child(u)
	u.reset_physics_interpolation()
	if visuals:
		var v := UnitView.new()
		u.add_child(v)
		v.setup(u)
		u.view = v
	Events.unit_spawned.emit(u)
	return u


func get_unit(uid: int) -> Unit:
	return entities.get(uid)


func units_of_player(pid: int) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in unit_list:
		if u.player_id == pid and u.alive:
			out.append(u)
	return out


## Units within r of p (XZ). `filter` is an optional Callable(Unit) -> bool.
func query_radius(p: Vector3, r: float, filter: Callable = Callable(), out: Array = []) -> Array:
	spatial.query_radius(p, r, out)
	if filter.is_valid():
		var i := out.size() - 1
		while i >= 0:
			if not filter.call(out[i]):
				out.remove_at(i)
			i -= 1
	return out


func mark_dead(u: Unit, killer: Unit) -> void:
	_dead.append([u, killer])


## Dead units leave the simulation here (end of tick): out of the spatial hash, id table and
## unit list, footprint freed, food released, `unit_died` emitted. The node stays as a corpse
## (UnitView plays topple + sink) until `Unit.decay_ticks()` have passed, then it is freed.
func _cleanup() -> void:
	if not _dead.is_empty():
		var dead := _dead
		_dead = []
		for pair: Array in dead:
			_remove_dead(pair[0], pair[1])
	var i := _corpses.size() - 1
	while i >= 0:
		var c := _corpses[i]
		if tick_count - c.died_tick >= c.decay_ticks():
			_corpses.remove_at(i)
			c.queue_free()
		i -= 1


func _remove_dead(u: Unit, killer: Unit) -> void:
	spatial.remove(u)
	entities.erase(u.id)
	unit_list.erase(u)
	if u.footprint.size != Vector2i.ZERO:
		pathing.set_footprint_rect(u.footprint, false)
	_count_food(u, -1)
	Events.unit_died.emit(u, killer)
	_corpses.append(u)


func corpse_count() -> int:
	return _corpses.size()


## Food bookkeeping on spawn (+1) and removal (-1); the economy system will own the rest.
func _count_food(u: Unit, sign_value: int) -> void:
	var p := player(u.player_id)
	if p == null:
		return
	var used := int((u.def.get("cost", {}) as Dictionary).get("food", 0)) if u.is_mobile() else 0
	var provided := int(u.def.get("food_provided", 0))
	if used == 0 and provided == 0:
		return
	p.food_used += sign_value * used
	p.food_cap += sign_value * provided
	Events.resources_changed.emit(p.id)


## Economy hook for GATHER orders (see `gather_handler`).
func on_gather_reached(worker: Unit, resource: Unit) -> void:
	if gather_handler.is_valid():
		gather_handler.call(worker, resource)


# --- commands ------------------------------------------------------------------------------

## Queues a command dictionary (see docs/architecture.md §4). Applied at the start of the
## next tick, so input, AI, tests and replays share one deterministic path.
func issue(command: Dictionary) -> void:
	_pending.append(command)
	Events.command_issued.emit(command)


func _apply_commands() -> void:
	if _pending.is_empty():
		return
	var cmds := _pending
	_pending = []
	for cmd in cmds:
		_apply_command(cmd)


func _apply_command(cmd: Dictionary) -> void:
	var t: int = Order.type_from_string(str(cmd.get("type", "")))
	if t < 0:
		push_warning("World: unknown command type '%s'" % cmd.get("type"))
		return
	var us := _command_units(cmd)
	if us.is_empty():
		return
	var target: int = int(cmd.get("target", 0))
	var target_unit := get_unit(target)
	if target != 0 and (target_unit == null or not target_unit.alive):
		if not cmd.has("pos"):
			return                      # the target died before the command was applied
		target = 0
		target_unit = null
	var pos: Vector3 = cmd.get("pos", target_unit.pos if target_unit != null else Vector3.ZERO)
	var queue: bool = cmd.get("queue", false)
	var offsets: Array[Vector3] = []
	if target == 0 and t in [Order.Type.MOVE, Order.Type.ATTACK_MOVE, Order.Type.PATROL, Order.Type.SMART]:
		offsets = _formation_offsets(us, pos)
	var group: GroupPath = GroupPath.new() if us.size() > 1 else null
	for i in us.size():
		var u := us[i]
		var ut := t as Order.Type
		var tid := target
		if t == Order.Type.SMART:
			ut = resolve_smart(u, target_unit)
			if ut == Order.Type.MOVE:
				tid = 0
		var goal := pos
		if not offsets.is_empty() and ut != Order.Type.RALLY:
			goal = map.clamp_to_map(pos + offsets[i], 0.5)
		var o := Order.make(ut, goal, tid)
		if tid == 0 and ut in [Order.Type.MOVE, Order.Type.ATTACK_MOVE, Order.Type.PATROL]:
			o.group_path = group
		o.def_id = str(cmd.get("def", ""))
		o.ability = str(cmd.get("ability", ""))
		u.issue_order(o, queue)


func _command_units(cmd: Dictionary) -> Array[Unit]:
	var pid := int(cmd.get("player", -1))
	var out: Array[Unit] = []
	for uid: Variant in cmd.get("units", []):
		var u := get_unit(int(uid))
		if u != null and u.alive and u.player_id == pid:
			out.append(u)
	return out


## Right-click resolution for one unit: producing structures set their rally point; enemies
## are attacked (followed by units without a weapon); workers gather resources (others walk
## there); mobile allies are followed; allied structures and the ground are a move (a FOLLOW
## on a building would never complete).
func resolve_smart(u: Unit, target: Unit) -> Order.Type:
	if u.can_train():
		return Order.Type.RALLY
	if target == null or target == u:
		return Order.Type.MOVE
	if target.is_resource:
		return Order.Type.GATHER if u.is_worker else Order.Type.MOVE
	if is_enemy(u.player_id, target.player_id):
		return Order.Type.ATTACK if u.can_attack() else Order.Type.FOLLOW
	return Order.Type.FOLLOW if target.is_mobile() else Order.Type.MOVE


## Keeps a compact group's shape (classic RTS style) instead of funnelling everyone into one point.
func _formation_offsets(us: Array[Unit], target: Vector3) -> Array[Vector3]:
	var out: Array[Vector3] = []
	if us.size() < 2 or not us[0].is_mobile():
		return out
	var c := Vector3.ZERO
	for u in us:
		c += u.pos
	c /= us.size()
	var spread := 0.0
	for u in us:
		spread = maxf(spread, Grid.flat_dist(u.pos, c))
	if spread > FORMATION_MAX_SPREAD or Grid.flat_dist(c, target) < spread * 2.0:
		return out
	for u in us:
		var off := u.pos - c
		off.y = 0.0
		out.append(off)
	return out


# --- helpers -------------------------------------------------------------------------------

func raycast_ground(origin: Vector3, dir: Vector3) -> Vector3:
	return map.raycast(origin, dir)


## Hooks the local player's fog texture (L8: 0 unexplored, 0.5 fogged, 1 visible) into the
## terrain, water and tree shaders. Pass null to disable fog rendering.
func set_fog_texture(tex: Texture2D) -> void:
	if terrain != null:
		terrain.set_fog_texture(tex)
	doodads.set_fog_texture(tex)


func _child_or_new(child_name: String, type: Variant) -> Node:
	var n := get_node_or_null(child_name)
	if n == null:
		n = type.new()
		n.name = child_name
		add_child(n)
	return n
