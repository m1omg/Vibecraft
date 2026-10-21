class_name World
extends Node3D
## Match root and fixed-step simulation driver. Gameplay advances only in `step()`, called once
## per physics tick (30 Hz) or manually by tests. Stage order is fixed (docs/architecture.md §4).
## World owns every gameplay system (SYSTEM_STAGES), routes command dictionaries to unit orders
## or to systems (SYSTEM_COMMANDS) and dispatches the unit hooks (SimSystem) in a fixed order.

const TICK_RATE := 30
const DT := 1.0 / TICK_RATE
const STAGES: Array[StringName] = [&"orders", &"production", &"units", &"projectiles",
	&"abilities", &"economy", &"creeps", &"ai", &"fog", &"cleanup"]
## Stages World runs itself; systems cannot register for them.
const OWN_STAGES: Array[StringName] = [&"orders", &"units", &"cleanup"]
## Stages run after the units, in this order.
const LATE_STAGES: Array[StringName] = [&"projectiles", &"abilities", &"economy", &"creeps", &"ai",
	&"fog"]
## Installed systems in installation (= hook and same-stage run) order: [property, stage, script].
const SYSTEM_STAGES: Array = [
	[&"construction", &"production", preload("res://src/systems/construction.gd")],
	[&"production", &"production", preload("res://src/systems/production.gd")],
	[&"tech", &"production", preload("res://src/systems/tech.gd")],
	[&"abilities", &"abilities", preload("res://src/systems/abilities.gd")],
	[&"buffs", &"abilities", preload("res://src/systems/buffs.gd")],
	[&"items", &"abilities", preload("res://src/systems/items.gd")],
	[&"economy", &"economy", preload("res://src/systems/economy.gd")],
	[&"heroes", &"economy", preload("res://src/systems/heroes.gd")],
	[&"shops", &"economy", preload("res://src/systems/shops.gd")],
	[&"creeps", &"creeps", preload("res://src/systems/creeps.gd")],
	[&"fog", &"fog", preload("res://src/world/fog.gd")],
]
## Command types that are not unit orders: World hands them to the named system's
## handle_command(cmd, units) (units = the command's living units owned by cmd.player).
const SYSTEM_COMMANDS: Dictionary = {
	"train": &"production", "cancel": &"production", "research": &"production",
	"buy": &"shops", "sell": &"shops", "service": &"shops",
	"revive": &"heroes", "autocast": &"abilities",
}
const MAX_PLAYERS := SpatialHash.MAX_PLAYERS
const FORMATION_MAX_SPREAD := 8.0
const SPAWN_SNAP_CELLS := 16
const TREE_CLICK_RADIUS := 1.2

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
var combat: Combat                   ## damage resolution + projectiles (stage `projectiles`)
var construction: Construction
var production: Production
var tech: Tech
var abilities: AbilitySystem
var buffs: BuffSystem
var items: ItemSystem
var economy: Economy
var heroes: HeroSystem
var shops: ShopSystem
var creeps: CreepSystem
var fog: Fog
var ai_players: Array[AiPlayer] = []
## Largest mobile unit radius (from Defs): pads separation neighbour queries.
var max_unit_radius: float = 1.0
var local_player_id: int = 0
var rng := RandomNumberGenerator.new()
## Legacy economy hook (tests): Callable(worker: Unit, resource: Unit) run when a GATHER order
## reaches its mine; when set it wins over Economy.on_gather_reached and the order completes.
var gather_handler: Callable = Callable()

var _next_id: int = 1
var _pending: Array[Dictionary] = []
var _dead: Array = []                ## [Unit, killer]
var _corpses: Array[Unit] = []       ## dead, out of the sim, removed after their decay time
var _removed: Array[Unit] = []       ## remove_unit()ed this tick; leave unit_list in cleanup
var _systems: Dictionary = {}        ## stage -> Array[Node] (sim_tick(world, dt)), registration order
var _hostile := PackedInt32Array()   ## player id -> bitmask of the player ids it is an enemy of
var _hooks: Dictionary = {&"spawned": [], &"died": [], &"removed": [], &"damaged": []}

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
	_install_systems()
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


## Creates every gameplay system (SYSTEM_STAGES order), registers it for its stage and collects
## its hooks.
func _install_systems() -> void:
	for row: Array in SYSTEM_STAGES:
		var sys: SimSystem = (row[2] as GDScript).new()
		sys.name = String(row[0]).capitalize().replace(" ", "")
		systems_root.add_child(sys)
		sys.setup(self)
		set(row[0], sys)
		register_system(row[1], sys)
		_add_hooks(sys)


func _add_hooks(sys: SimSystem) -> void:
	for h: StringName in sys.hooks():
		if _hooks.has(h):
			(_hooks[h] as Array).append(sys)


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

## Adds a player. `ai` = true installs an AiPlayer for it (stage `ai`, `difficulty` from
## rules.ai) once the world is set up.
func add_player(pid: int, team_id: int, faction: String = "", ai: bool = false,
		difficulty: String = "normal") -> PlayerState:
	assert(pid >= 0 and pid < MAX_PLAYERS, "player id out of range")
	var p := PlayerState.make(pid, team_id, faction, ai)
	players.append(p)
	refresh_relations()
	if ai and pid < PlayerState.NEUTRAL_HOSTILE and systems_root != null and map != null:
		var brain := AiPlayer.new()
		brain.name = "Ai%d" % pid
		systems_root.add_child(brain)
		brain.setup_player(self, pid, difficulty)
		register_system(&"ai", brain)
		ai_players.append(brain)
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

## Spawns an entity. Structures snap to their footprint and block pathing (unless the def says
## blocks_pathing false); mobile units snap to the nearest walkable cell. `opts`:
##   under_construction: bool   construction site (no food provided until completed)
##   hp_fraction: float          start HP as a fraction of max (sites: rules.economy.build_start_hp)
##   food_reserved: bool         Production already counted the unit's food when training began
func spawn_unit(def_id: String, pid: int, p: Vector3, facing: float = 0.0, opts: Dictionary = {}) -> Unit:
	var d := Defs.unit(def_id)
	if d.is_empty():
		return null
	var u := Unit.new()
	var spot := p
	if d["kind"] != "unit" and d["kind"] != "item":
		var fp: Array = d["footprint"]
		var size := Vector2i(int(fp[0]), int(fp[1]))
		spot = Grid.snap_to_footprint(p, size)
		u.footprint = Grid.footprint_rect(spot, size)
	elif d["kind"] == "unit":
		var c := pathing.nearest_walkable(Grid.world_to_cell(p), false, SPAWN_SNAP_CELLS)
		if c.x >= 0 and c != Grid.world_to_cell(p):
			spot = Grid.cell_to_world(c)
	u.facing = facing
	u.setup(self, _next_id, def_id, pid, spot)
	_next_id += 1
	u.under_construction = bool(opts.get("under_construction", false))
	if u.under_construction:
		u.build_progress = 0.0
	if opts.has("hp_fraction"):
		u.hp = maxf(1.0, u.max_hp * float(opts["hp_fraction"]))
	if u.footprint.size != Vector2i.ZERO and bool(d.get("blocks_pathing", true)):
		pathing.set_footprint_rect(u.footprint, true)
	if not bool(opts.get("food_reserved", false)):
		_count_food(u, 1)
	elif not u.under_construction:
		_count_food(u, 1, false)
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
	for s: SimSystem in _hooks[&"spawned"]:
		s.on_unit_spawned(u)
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


## Takes a living entity out of the sim at once without a death (a picked-up item, a cancelled
## site, a unit replaced by a transform): spatial hash, ids, footprint, food; no corpse, no
## unit_died. It stops ticking at once (alive = false); unit_list drops it and the node is
## freed in this tick's cleanup (safe to call from any stage, the units loop included).
func remove_unit(u: Unit) -> void:
	if not entities.has(u.id):
		return
	u.alive = false
	if not u.hidden:
		spatial.remove(u)
	entities.erase(u.id)
	if u.footprint.size != Vector2i.ZERO and bool(u.def.get("blocks_pathing", true)):
		pathing.set_footprint_rect(u.footprint, false)
	_count_food(u, -1)
	for s: SimSystem in _hooks[&"removed"]:
		s.on_unit_removed(u)
	_removed.append(u)
	u.visible = false
	Events.unit_removed.emit(u)


## Hides a unit inside something (a gold mine, a garrison): out of the spatial hash, so it is
## neither targeted, collided with nor drawn; it keeps its id and orders. Showing it again
## re-inserts it at its position.
func set_hidden(u: Unit, hide: bool) -> void:
	if u.hidden == hide or not u.alive:
		return
	u.hidden = hide
	if hide:
		spatial.remove(u)
	else:
		spatial.insert(u)
		u.reset_physics_interpolation()
	u.visible = not hide


## Food bookkeeping for systems: Production reserves food when training starts (used) and
## Construction adds a finished site's food (cap).
func adjust_food(pid: int, used_delta: int, cap_delta: int) -> void:
	var p := player(pid)
	if p == null or (used_delta == 0 and cap_delta == 0):
		return
	p.food_used += used_delta
	p.food_cap += cap_delta
	Events.resources_changed.emit(pid)


## Called by Unit.take_damage after HP changed (systems' on_unit_damaged hooks).
func notify_damaged(u: Unit, amount: float, src: Unit) -> void:
	for s: SimSystem in _hooks[&"damaged"]:
		s.on_unit_damaged(u, amount, src)


## Dead units leave the simulation here (end of tick): out of the spatial hash, id table and
## unit list, footprint freed, food released, `unit_died` emitted. The node stays as a corpse
## (UnitView plays topple + sink) until `Unit.decay_ticks()` have passed, then it is freed.
func _cleanup() -> void:
	if not _removed.is_empty():
		for u in _removed:
			unit_list.erase(u)
			u.queue_free()
		_removed.clear()
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
	if not u.hidden:
		spatial.remove(u)
	entities.erase(u.id)
	unit_list.erase(u)
	if u.footprint.size != Vector2i.ZERO and bool(u.def.get("blocks_pathing", true)):
		pathing.set_footprint_rect(u.footprint, false)
	_count_food(u, -1)
	for s: SimSystem in _hooks[&"died"]:
		s.on_unit_died(u, killer)
	Events.unit_died.emit(u, killer)
	_corpses.append(u)


func corpse_count() -> int:
	return _corpses.size()


## Food bookkeeping on spawn (+1) and removal (-1): used food for mobile units (heroes
## included), provided food for finished structures. `with_used` false skips the used part
## (Production reserved it already).
func _count_food(u: Unit, sign_value: int, with_used: bool = true) -> void:
	var p := player(u.player_id)
	if p == null:
		return
	var used := int((u.def.get("cost", {}) as Dictionary).get("food", 0)) if u.is_mobile() and with_used else 0
	if u.def.get("food_from_source", false):
		used = 0
	var provided := int(u.def.get("food_provided", 0)) if not u.under_construction else 0
	if used == 0 and provided == 0:
		return
	p.food_used += sign_value * used
	p.food_cap += sign_value * provided
	Events.resources_changed.emit(p.id)


## Legacy economy hook for GATHER orders (see `gather_handler`).
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
	var type_name := str(cmd.get("type", ""))
	if SYSTEM_COMMANDS.has(type_name):
		_apply_system_command(cmd, type_name)
		return
	var t: int = Order.type_from_string(type_name)
	if t < 0:
		push_warning("World: unknown command type '%s'" % cmd.get("type"))
		return
	var us := _command_units(cmd)
	if us.is_empty():
		return
	if t == Order.Type.CAST and not us[0].is_mobile():
		abilities.handle_command(cmd, us)      # building abilities (Levy Horn, Sound the Gong)
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
	var tree := int(cmd.get("tree", -1))
	if tree < 0 and target == 0 and t in [Order.Type.SMART, Order.Type.GATHER] and cmd.has("pos"):
		tree = doodads.nearest_tree(pos, TREE_CLICK_RADIUS)
	var group: GroupPath = GroupPath.new() if us.size() > 1 else null
	# formation (rules §7.10): the group keeps to its slowest member's speed
	var march := 0.0
	if not offsets.is_empty():
		march = INF
		for u in us:
			march = minf(march, u.speed)
	for i in us.size():
		var u := us[i]
		var ut := t as Order.Type
		var tid := target
		if t == Order.Type.SMART:
			ut = resolve_smart(u, target_unit) if target_unit != null else resolve_smart_point(u, tree)
			if ut == Order.Type.MOVE:
				tid = 0
		var goal := pos
		if not offsets.is_empty() and ut != Order.Type.RALLY:
			goal = map.clamp_to_map(pos + offsets[i], 0.5)
		var o := Order.make(ut, goal, tid)
		if tid == 0 and ut in [Order.Type.MOVE, Order.Type.ATTACK_MOVE, Order.Type.PATROL]:
			o.group_path = group
			if not offsets.is_empty():
				o.march_speed = march
		o.def_id = str(cmd.get("def", ""))
		o.ability = str(cmd.get("ability", ""))
		o.slot = int(cmd.get("slot", -1))
		var extra: Variant = cmd.get("data", {})
		if extra is Dictionary:
			o.data = (extra as Dictionary).duplicate()
		if ut == Order.Type.GATHER and tid == 0 and tree >= 0:
			o.data["tree"] = tree
		u.issue_order(o, queue)


## Routes a building / player command to its system (SYSTEM_COMMANDS).
func _apply_system_command(cmd: Dictionary, type_name: String) -> void:
	var sys: SimSystem = get(SYSTEM_COMMANDS[type_name])
	if sys == null:
		return
	sys.handle_command(cmd, _command_units(cmd))


func _command_units(cmd: Dictionary) -> Array[Unit]:
	var pid := int(cmd.get("player", -1))
	var out: Array[Unit] = []
	for uid: Variant in cmd.get("units", []):
		var u := get_unit(int(uid))
		if u != null and u.alive and u.player_id == pid:
			out.append(u)
	return out


## Right-click resolution for one unit (rules §18.2): producing structures set their rally
## point; enemies are attacked (followed by units without a weapon); items are picked up by
## those who may carry them; workers gather resources, return cargo to an own drop-off, help
## build an own site, enter an own garrison with a free slot and repair own damaged buildings or
## mechanical units; mobile allies are followed; everything else (allied or neutral structures,
## shops, the ground) is a move — a FOLLOW on a building would never complete.
func resolve_smart(u: Unit, target: Unit) -> Order.Type:
	if u.can_train():
		return Order.Type.RALLY
	if target == null or target == u:
		return Order.Type.MOVE
	if target.is_item:
		return Order.Type.PICKUP_ITEM if items.can_pickup(u, target) else Order.Type.MOVE
	if target.is_resource:
		return Order.Type.GATHER if u.can_gather() else Order.Type.MOVE
	if is_enemy(u.player_id, target.player_id):
		return Order.Type.ATTACK if u.can_attack() else Order.Type.FOLLOW
	if target.player_id == u.player_id and u.is_worker:
		if target.under_construction:
			return Order.Type.BUILD if construction.can_order_build(u, _site_order(target)) else Order.Type.MOVE
		if u.can_gather() and Economy.carry_kind(u) != "" and economy.accepts_cargo(target, u):
			return Order.Type.RETURN_RESOURCES
		if target.has_flag("garrison") and construction.can_enter(u, target):
			return Order.Type.ENTER
	if is_ally(u.player_id, target.player_id) and u.repair_ability() != "" and construction.can_repair(u, target):
		return Order.Type.REPAIR
	return Order.Type.FOLLOW if target.is_mobile() else Order.Type.MOVE


## Right-click on the ground: rally for producing structures, gather for workers when a living
## tree lies under the click (`tree` index, -1 = none), else move.
func resolve_smart_point(u: Unit, tree: int) -> Order.Type:
	if u.can_train():
		return Order.Type.RALLY
	if tree >= 0 and u.can_gather():
		return Order.Type.GATHER
	return Order.Type.MOVE


static func _site_order(site: Unit) -> Order:
	var o := Order.make(Order.Type.BUILD, site.pos, site.id)
	o.def_id = site.def_id
	return o


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
