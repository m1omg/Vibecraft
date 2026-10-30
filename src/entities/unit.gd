class_name Unit
extends Node3D
## Every game object with an id (units, heroes, buildings, mines, critters, ground items).
## Simulation state lives in plain fields (`pos`, `facing`, ...) and is advanced only by
## `sim_tick` from the fixed World tick; the Node3D transform is written once per tick so physics
## interpolation smooths it.
##
## Orders: one `current` order + a shift queue. Each order type's per-tick behaviour lives in its
## own stateless handler under src/entities/orders/ (OrderHandlers.of(type); the no-order
## behaviour is orders/idle.gd). This file keeps the shared machinery the handlers drive
## ("handler API" below): path following, steering, acquisition, chasing, the attack swing.
## - idle units auto-acquire enemies within `acquire_range`, chase them up to `leash_range` from
##   their guard position and walk back when leashed (creeps always return to their camp);
## - HOLD attacks only what is already in weapon range and never moves;
## - ATTACK chases one target until it dies (no leash);
## - ATTACK_MOVE / PATROL follow their path, engage anything acquired on the way, then resume.
## An attack is a swing: wind-up (damage point) -> hit or projectile -> backswing. The weapon
## cooldown starts with the swing. All timers are integer tick counts (exact, deterministic).
##
## Stats: base values come from the def; systems add modifiers per source with
## set_modifiers(source, mods) (tech upgrades, hero attributes, items, buffs) and the unit
## recomputes its live stats (recompute_stats). Statuses (stun, root, silence, disarm,
## invulnerable, cannot_die, hidden ...) arrive the same way as mods["status"].

const ARRIVE_EPS := 0.2
const WAYPOINT_EPS := 0.45
const SEPARATION_GAIN := 6.0
const PUSH_GAIN := 7.0
const STALL_TICKS_NEAR := 8
const STALL_TICKS_FAR := 45
const MAX_REPATHS := 3
const INVENTORY_SLOTS := 6
const SCAN_TICKS := 5            ## auto-acquire scan interval (staggered by id)
const REPATH_TICKS := 10         ## min ticks between chase path requests
const REPATH_DIST := 1.0         ## target drift (m) that makes a chase path stale
const DIRECT_CHASE := 5.0        ## a target this close and in plain sight is chased without a path
const FACE_TOLERANCE := 0.35     ## rad; a swing starts only when roughly facing the target
const RANGE_BUFFER := 2.5        ## a swing still connects if the target stepped back this far
const CHASE_SLACK := 3.0         ## an acquired target beyond acquire range + this is dropped
const STRUCTURE_PENALTY := 6.0   ## acquisition prefers units over structures (metres)
const BLOCKED_TICKS := 45        ## chasing without progress this long -> try another target
const SKIP_TICKS := 90           ## how long a given-up target is ignored by acquisition
const HOME_EPS := 1.5            ## creeps further than this from camp walk back when calm
## An idle unit shoved aside by a passing ally steps back to where it stood once nobody has
## pushed it for SHOVE_SETTLE_TICKS, if it ended up between SHOVE_RETURN_EPS and
## SHOVE_RETURN_MAX away and the spot is still free (the genre's "move aside, then step back":
## a formation keeps its slots). A unit bulldozed further than that stays where it ended up.
const SHOVE_SETTLE_TICKS := 15
const SHOVE_RETURN_EPS := 0.75
const SHOVE_RETURN_MAX := 4.0
const FOLLOW_DIST := 1.2
const GATHER_REACH := 0.8
## Modifier keys whose totals take the largest value instead of the sum (rules §7.4).
const MAX_STACK_KEYS: Array[String] = ["miss_chance", "evasion"]
const STATUS_FLAGS: Array[String] = ["stun", "root", "silence", "disarm", "invulnerable",
	"cannot_die", "hidden", "invisible", "sleep", "taunt", "ignore_slows", "no_displace"]

static var _scan_buf: Array = []
static var _help_buf: Array = []

# identity
var id: int = 0
var def_id: String = ""
var def: Dictionary = {}
var player_id: int = 0
var team: int = 0
var world: World

# stats (from def, then modifiers)
var hp: float = 1.0
var max_hp: float = 1.0
var mana: float = 0.0
var max_mana: float = 0.0
var hp_regen: float = 0.0        ## HP/s (applied by the buffs system; rules §9)
var mana_regen: float = 0.0
var armor: float = 0.0
var armor_type: String = "unarmored"
var radius: float = 0.4
## Centre-to-edge reach for target queries: footprint half-diagonal for structures, else radius.
var target_radius: float = 0.4
var speed: float = 0.0
var sight: float = 10.0          ## day sight (m)
var sight_night: float = 10.0
var turn_rate: float = 12.0
var level: int = 1               ## XP / bounty level (rules §4.4); heroes: their hero level
var is_building: bool = false
var is_hero: bool = false
var is_worker: bool = false
var is_resource: bool = false
var is_flying: bool = false
var is_invulnerable: bool = false
var is_item: bool = false        ## a ground item entity (ItemSystem.spawn_item)
var is_summoned: bool = false
var is_mechanical: bool = false
var attack: Dictionary = {}
var abilities: Array = []
var buffs: Array = []            ## buff records (BuffSystem): {id, source, remaining, rank, data}
var carry_gold: int = 0
var carry_lumber: int = 0
## Hero state (HeroSystem): {hero_id, level, xp, skill_points, ranks: {ability: rank},
## attr_bonus: {str, agi, int}}. Empty for non-heroes.
var hero: Dictionary = {}
## 6 slots (heroes only): null or {"id": item id, "charges": int}. ItemSystem owns the contents.
var inventory: Array = []
var item_id: String = ""         ## ground items: the item this entity carries
var item_charges: int = -1
var camp_id: String = ""         ## creeps: their camp instance id (CreepSystem)
var under_construction: bool = false   ## Construction: site still building (no food, no function)
var build_progress: float = 1.0  ## 0..1 while under construction
var garrison: Array[int] = []    ## unit ids inside (garrison buildings)
var hidden: bool = false         ## out of the spatial hash (in a mine, garrisoned); World.set_hidden
## Work animation published by Economy (chopping) and Construction (building, repairing) for the
## view (visual readers work_progress / work_point_ratio / work_time); "" when not working.
var anim_hint: String = ""
var work_t0: int = -1            ## tick the current work stroke started
var work_ticks: int = 0          ## stroke length in ticks
## Economy: a worker on a gather trip; harvesting workers pass through each other (as in the
## classic game), so a busy mine lane never jams.
var harvesting: bool = false
var lifetime_ticks: int = -1     ## summons: ticks left (-1 = permanent)
var autocast: Dictionary = {}    ## ability id -> bool (AbilitySystem)
var cooldowns: Dictionary = {}   ## ability / item group id -> tick when ready (AbilitySystem, ItemSystem)

# statuses (from modifier sources, see recompute_stats)
var stunned: bool = false
var rooted: bool = false
var silenced: bool = false
var disarmed: bool = false
var cannot_die: bool = false
var status: Dictionary = {}      ## every active status flag -> true
## Summed modifiers of every source after recompute_stats (combat reads damage_pct,
## damage_taken_pct, miss_chance, evasion, crit, ...).
var mod_totals: Dictionary = {}

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
var _shoved_from: Vector3 = Vector3.INF   ## where an idle unit stood before allies shoved it
var _shoved_tick: int = -1
var view: Node3D = null

# movement (handler API reads `arrived`)
var path: PackedVector3Array = PackedVector3Array()
var path_i: int = 0
var arrived: bool = false         ## current path finished (consumed by the order logic)
var _need_path: bool = false
var _goal: Vector3 = Vector3.ZERO
var _stall: int = 0
var _repaths: int = 0
var _nbuf: Array = []
var _group: GroupPath = null      ## shared path of the current order (first path request only)
var _group_try: bool = false      ## a matching base may still be derived from
var _decay_ticks: int = -1        ## cached corpse lifetime (see decay_ticks)

# combat / order state shared with the handlers
var engage_id: int = 0            ## auto-acquired target (idle / hold / attack-move / patrol)
var engage_dist: float = 0.0      ## edge distance when engaged (retaliation can start far away)
var guard_pos: Vector3 = Vector3.ZERO
var returning: bool = false       ## walking back to the guard position after a leash
var resume_path: bool = false     ## attack-move must re-path to its goal after a fight
var march_speed: float = 0.0      ## formation speed cap of the current order (0 = none, rules §7.10)
var patrol_from: Vector3 = Vector3.ZERO
var blocked_ticks: int = 0
var _home: Vector3 = Vector3.ZERO
var _cooldown: int = 0            ## ticks until the weapon is ready
var _swing: int = -1              ## ticks into the current swing, -1 = not swinging
var _swing_target: int = 0
var _swing_fired: bool = false
var _repath_cd: int = 0
var _skip_id: int = 0
var _skip_ticks: int = 0
var _base: Dictionary = {}        ## stats before modifiers (def values; heroes: set_base_stats)
var _mods: Dictionary = {}        ## source -> modifier dictionary


func setup(w: World, uid: int, did: String, pid: int, p: Vector3) -> void:
	world = w
	id = uid
	def_id = did
	player_id = pid
	team = w.team_of(pid) if w != null else pid
	name = "%s_%d" % [did, uid]
	def = Defs.unit(did)
	_apply_def()
	target_radius = Vector2(footprint.size).length() * Grid.CELL * 0.5 \
		if footprint.size != Vector2i.ZERO else radius
	pos = p
	if w != null and w.map != null:
		pos.y = w.map.height_at(p.x, p.z)
	prev_pos = pos
	_home = pos
	guard_pos = pos
	_commit_transform()


func _apply_def() -> void:
	max_hp = float(def.get("hp", 1))
	hp = max_hp
	max_mana = float(def.get("mana", 0))
	mana = minf(max_mana, float(def.get("mana_start", max_mana))) if float(def.get("mana_start", -1.0)) >= 0.0 \
		else max_mana
	hp_regen = maxf(0.0, float(def.get("hp_regen", 0.0)))
	mana_regen = maxf(0.0, float(def.get("mana_regen", 0.0)))
	armor = float(def.get("armor", 0))
	armor_type = str(def.get("armor_type", "unarmored"))
	radius = float(def.get("radius", 0.4))
	speed = float(def.get("speed", 0.0))
	sight = float(def.get("sight", 10.0))
	sight_night = float(def.get("sight_night", sight))
	if sight_night < 0.0:
		sight_night = sight
	turn_rate = float(def.get("turn_rate", 12.0))
	leash_range = float(def.get("leash", 14.0))
	level = maxi(0, int(def.get("level", 1)))
	var kind: String = def.get("kind", "unit")
	var f: Array = def.get("flags", [])
	is_building = kind == "building"
	is_resource = kind == "resource"
	is_item = kind == "item"
	is_worker = f.has("worker")
	is_hero = f.has("hero")
	is_flying = f.has("flying") or f.has("air")
	is_invulnerable = f.has("invulnerable")
	is_summoned = f.has("summoned")
	is_mechanical = f.has("mechanical")
	attack = def.get("attack", {})
	abilities = (def.get("abilities", []) as Array).duplicate()
	inventory.resize(INVENTORY_SLOTS)
	_apply_attack()
	_base = {"max_hp": max_hp, "max_mana": max_mana, "armor": armor, "speed": speed, "sight": sight,
		"sight_night": sight_night, "damage_min": damage_min, "damage_max": damage_max,
		"attack_range": attack_range, "cooldown": float(attack.get("cooldown", 1.0)),
		"damage_point": float(attack.get("damage_point", 0.4)), "backswing": float(attack.get("backswing", 0.4)),
		"hp_regen": hp_regen, "mana_regen": mana_regen}


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


func is_structure() -> bool:
	return footprint.size != Vector2i.ZERO


func is_large() -> bool:
	return radius > Pathing.LARGE_RADIUS


func is_idle() -> bool:
	return current == null


func is_creep() -> bool:
	return player_id == PlayerState.NEUTRAL_HOSTILE


func can_attack() -> bool:
	return alive and damage_max > 0 and not disarmed


func can_train() -> bool:
	return is_building and not under_construction and not (def.get("trains", []) as Array).is_empty()


## Workers that gather (their card carries Gather).
func can_gather() -> bool:
	return is_worker and abilities.has("cmd_gather")


## Id of this unit's repair ability (an ability with effect "repair"), "" when it cannot repair.
func repair_ability() -> String:
	for a: Variant in abilities:
		if str(Defs.abilities.get(str(a), {}).get("effect", "")) == "repair":
			return str(a)
	return ""


func has_flag(flag: String) -> bool:
	return (def.get("flags", []) as Array).has(flag)


## Unit the weapon is busy with (swing or engagement), 0 = none. For UI/AI, read-only.
func combat_target_id() -> int:
	if _swing >= 0:
		return _swing_target
	if current != null and current.type == Order.Type.ATTACK:
		return current.target_id
	return engage_id


## Interpolated display position (for fx/UI drawn in _process).
func display_pos() -> Vector3:
	return prev_pos.lerp(pos, _frac())


## Tick interpolation fraction for visuals (frozen at 1 while the World is paused).
func _frac() -> float:
	return world.interpolation_fraction() if world != null else Engine.get_physics_interpolation_fraction()


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


## Distance from this unit's edge to a ground point.
func edge_distance_to_point(p: Vector3) -> float:
	return maxf(Grid.flat_dist(pos, p) - radius, 0.0)


## Swing progress 0..1 for animation (-1 when not attacking). Visual only.
func swing_progress() -> float:
	var total := damage_point_ticks + backswing_ticks
	if _swing < 0 or total <= 0:
		return -1.0
	return clampf((_swing + _frac()) / total, 0.0, 1.0)


func damage_point_ratio() -> float:
	var total := damage_point_ticks + backswing_ticks
	return float(damage_point_ticks) / total if total > 0 else 0.0


func is_swinging() -> bool:
	return _swing >= 0


## Progress 0..1 of the current work stroke (chop, hammer), interpolated between ticks; -1 when
## the unit is not working. Visual only (UnitView positions the work clip from it).
func work_progress() -> float:
	if anim_hint != "work" or work_t0 < 0 or work_ticks <= 0 or world == null:
		return -1.0
	return clampf((world.tick_count - work_t0 + _frac()) / float(work_ticks), 0.0, 1.0)


## Where the stroke lands within it (the chop or hammer contact at the end of the stroke).
func work_point_ratio() -> float:
	return 0.92


func work_time() -> float:
	return work_ticks * World.DT


## Starts (or restarts) a work stroke of `ticks` (Economy, Construction).
func begin_work(ticks: int) -> void:
	anim_hint = "work"
	work_t0 = world.tick_count if world != null else 0
	work_ticks = maxi(ticks, 1)


func end_work() -> void:
	anim_hint = ""
	work_t0 = -1


## Seconds since death, interpolated between ticks (visual only).
func dead_time() -> float:
	if died_tick < 0 or world == null:
		return 0.0
	return (world.tick_count - died_tick + _frac()) * World.DT


## How long the corpse stays before World removes it (computed once; read every tick).
func decay_ticks() -> int:
	if _decay_ticks < 0:
		var key := "structure_decay" if footprint.size != Vector2i.ZERO else "corpse_decay"
		var seconds: Variant = def["decay"] if def.has("decay") else Defs.combat_default(key, 8.0)
		_decay_ticks = _to_ticks(seconds)
	return _decay_ticks


# --- stats & modifiers ---------------------------------------------------------------------

## Replaces one source's modifiers and recomputes the live stats. `source` is the owning
## system's key ("tech", "hero", "items", "buffs", ...); an empty dict removes the source.
## Keys (all optional, additive across sources unless noted): max_hp, max_hp_pct, max_mana,
## armor, damage (flat, min and max), damage_pct, attack_speed_pct, move_speed (flat m/s),
## move_speed_pct, range, sight, hp_regen, mana_regen, miss_chance / evasion (max wins),
## crit ({chance, multiplier}, max multiplier wins), damage_taken_pct ({attack type: pct}),
## status (Array of STATUS_FLAGS).
func set_modifiers(source: StringName, mods: Dictionary) -> void:
	if mods.is_empty():
		_mods.erase(source)
	else:
		_mods[source] = mods
	recompute_stats()


func modifiers(source: StringName) -> Dictionary:
	return _mods.get(source, {})


## Tech building upgrades (rules §5.1: Moot Hall -> Walled Burg, Lookout -> Gun Tower): becomes
## `did` in place, keeping its HP fraction, footprint, orders and modifier sources.
func transform_to(did: String) -> void:
	var hp_frac := hp / maxf(max_hp, 0.001)
	def_id = did
	def = Defs.unit(did)
	name = "%s_%d" % [did, id]
	var fp := footprint
	_apply_def()
	footprint = fp
	recompute_stats()
	hp = clampf(hp_frac * max_hp, 1.0, max_hp)


## Overwrites base stats (keys of `_base`: max_hp, max_mana, armor, speed, sight, sight_night,
## damage_min, damage_max, attack_range, cooldown, damage_point, backswing, hp_regen,
## mana_regen). Used by HeroSystem on level-up and by transforms; then recomputes.
func set_base_stats(stats: Dictionary) -> void:
	_base.merge(stats, true)
	recompute_stats()


func base_stat(key: String, fallback: Variant = 0.0) -> Variant:
	return _base.get(key, fallback)


## Live stats = base + every modifier source. Missing HP/mana are kept when the maximum grows
## (rules §6.2 level-up rule); speed is clamped to combat.move_speed_clamp for mobile units and
## attack timings are divided by the attack-speed factor (clamped, rules §7.5).
func recompute_stats() -> void:
	var t := {}
	var st := {}
	for src: StringName in _mods:
		var m: Dictionary = _mods[src]
		for k: String in m:
			var v: Variant = m[k]
			if k == "status":
				for s: Variant in v:
					st[str(s)] = true
			elif k == "damage_taken_pct":
				var dt: Dictionary = t.get_or_add(k, {})
				for at: String in v:
					dt[at] = float(dt.get(at, 0.0)) + float(v[at])
			elif k == "crit":
				var c: Dictionary = t.get("crit", {})
				if float((v as Dictionary).get("multiplier", 0.0)) > float(c.get("multiplier", 0.0)):
					t["crit"] = v
			elif MAX_STACK_KEYS.has(k):
				t[k] = maxf(float(t.get(k, 0.0)), float(v))
			elif v is float or v is int:
				t[k] = float(t.get(k, 0.0)) + float(v)
	mod_totals = t
	status = st
	var old_max_hp := max_hp
	var old_max_mana := max_mana
	max_hp = maxf(1.0, (float(_base["max_hp"]) + float(t.get("max_hp", 0.0))) * (1.0 + float(t.get("max_hp_pct", 0.0)) / 100.0))
	max_mana = maxf(0.0, float(_base["max_mana"]) + float(t.get("max_mana", 0.0)))
	if max_hp > old_max_hp:
		hp += max_hp - old_max_hp
	hp = minf(hp, max_hp)
	if max_mana > old_max_mana:
		mana += max_mana - old_max_mana
	mana = minf(mana, max_mana)
	armor = float(_base["armor"]) + float(t.get("armor", 0.0))
	hp_regen = float(_base["hp_regen"]) + float(t.get("hp_regen", 0.0))
	mana_regen = float(_base["mana_regen"]) + float(t.get("mana_regen", 0.0))
	sight = float(_base["sight"]) + float(t.get("sight", 0.0))
	sight_night = float(_base["sight_night"]) + float(t.get("sight", 0.0))
	if t.has("sight_override"):          # Swallowed Sun: sight cut to a few metres
		sight = minf(sight, float(t["sight_override"]))
		sight_night = minf(sight_night, float(t["sight_override"]))
	var base_speed := float(_base["speed"])
	if base_speed > 0.0 and not is_building:
		var slow := float(t.get("move_speed_pct", 0.0))
		if st.has("ignore_slows"):
			slow = maxf(slow, 0.0)
		var spd_clamp: Array = Defs.combat.get("move_speed_clamp", [0.0, 100.0])
		speed = clampf((base_speed + float(t.get("move_speed", 0.0))) * (1.0 + slow / 100.0),
			float(spd_clamp[0]), float(spd_clamp[1]))
	if not attack.is_empty():
		var flat := int(t.get("damage", 0.0))
		damage_min = int(_base["damage_min"]) + flat
		damage_max = int(_base["damage_max"]) + flat
		attack_range = float(_base["attack_range"]) + float(t.get("range", 0.0))
		var asc: Array = Defs.combat.get("attack_speed_clamp", [0.2, 5.0])
		var factor := clampf(1.0 + float(t.get("attack_speed_pct", 0.0)) / 100.0, float(asc[0]), float(asc[1]))
		cooldown_ticks = maxi(1, _to_ticks(float(_base["cooldown"]) / factor))
		damage_point_ticks = _to_ticks(float(_base["damage_point"]) / factor)
		backswing_ticks = _to_ticks(float(_base["backswing"]) / factor)
	stunned = st.has("stun") or st.has("sleep")
	rooted = st.has("root")
	silenced = st.has("silence")
	disarmed = st.has("disarm")
	cannot_die = st.has("cannot_die")
	is_invulnerable = (def.get("flags", []) as Array).has("invulnerable") or st.has("invulnerable")
	if stunned:
		cancel_swing()


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
	var h := OrderHandlers.of(o.type)
	if h.is_instant():
		if h.can_start(self, o):
			h.apply_instant(self, o)
			Events.order_issued.emit(self, o)
		return
	if not is_mobile() and not (h.allows_immobile() and can_attack() and not is_resource):
		return
	if o.type == Order.Type.ATTACK and o.target_id == 0:
		o.type = Order.Type.ATTACK_MOVE
		h = OrderHandlers.of(o.type)
	if o.type == Order.Type.STOP:
		orders.clear()
		cancel_swing()
		returning = false
		finish_order(false)
		Events.order_issued.emit(self, o)
		return
	if not h.can_start(self, o):
		return
	if queue and current != null:
		var cap := int(Defs.rule("controls.shift_queue_max", 32))
		if orders.size() + 1 >= cap:
			return
		orders.append(o)
	else:
		orders.clear()
		_start(o)
	Events.order_issued.emit(self, o)


func clear_orders() -> void:
	orders.clear()
	finish_order(false)


func _start(o: Order) -> void:
	if not (o.type == Order.Type.ATTACK and o.target_id == _swing_target):
		cancel_swing()
	if current != null:
		var old := current
		current = null
		OrderHandlers.of(old.type).exit(self, old)
	current = o
	holding = false
	engage_id = 0
	returning = false
	resume_path = false
	blocked_ticks = 0
	_repath_cd = 0
	stop_moving()
	_group = o.group_path
	_group_try = _group != null
	march_speed = o.march_speed
	_shoved_from = Vector3.INF
	OrderHandlers.of(o.type).enter(self, o)


# --- handler API (used by src/entities/orders/*.gd) ----------------------------------------

## Where an order heads: its target unit's position when it has one, else its point.
func order_goal(o: Order) -> Vector3:
	if o.target_id != 0 and world != null:
		var t := world.get_unit(o.target_id)
		if t != null:
			return t.pos
	return o.target_pos


## Starts walking to `goal` (path requested on the next follow_path call).
func begin_move(goal: Vector3) -> void:
	_goal = goal
	_need_path = true
	arrived = false
	path.clear()
	path_i = 0
	_stall = 0
	_repaths = 0


func stop_moving() -> void:
	path.clear()
	path_i = 0
	_need_path = false
	arrived = false
	_stall = 0


func _on_path_end() -> void:
	path.clear()
	path_i = 0
	_need_path = false
	arrived = true


## Ends the current order (exit hook, state reset) and starts the next queued one when
## `advance` is true.
func finish_order(advance: bool = true) -> void:
	if current != null:
		var old := current
		current = null
		OrderHandlers.of(old.type).exit(self, old)
	holding = false
	engage_id = 0
	resume_path = false
	march_speed = 0.0
	_group = null
	_group_try = false
	stop_moving()
	guard_pos = pos
	if advance and not orders.is_empty():
		_start(orders.pop_front())


## Walks back to `p` as part of the idle behaviour (leash / creep camp return).
func return_to(p: Vector3) -> void:
	returning = true
	begin_move(p)


# --- simulation ----------------------------------------------------------------------------

func sim_tick(dt: float) -> void:
	prev_pos = pos
	if not alive:
		return
	_tick_timers()
	if lifetime_ticks > 0:
		lifetime_ticks -= 1
		if lifetime_ticks == 0:
			die(null)
			return
	if hidden:
		return
	if not is_mobile():
		# structures and immobile summons with a weapon (towers, the Grand Bombard) shoot in place
		if can_attack() and not under_construction and not stunned:
			if _swing >= 0:
				_advance_swing(dt)
			else:
				_think(dt)
			if not is_building:
				_commit_transform()
		return
	var desired := Vector3.ZERO
	if stunned:
		desired = Vector3.ZERO
	elif _swing >= 0:
		_advance_swing(dt)
	else:
		desired = _think(dt)
		if hidden:
			return        # the order just took it inside (a Gold Seam, a garrison): no step this tick
	if rooted:
		desired = Vector3.ZERO
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
		return OrderHandlers.idle().tick(self, null, dt)
	return OrderHandlers.of(current.type).tick(self, current, dt)


## Calm idle unit: guard position follows it; creeps walk back to their camp; a unit shoved
## aside by allies steps back to its spot (SHOVE_*).
func settle() -> void:
	if is_creep():
		guard_pos = _home
		if Grid.flat_dist(pos, _home) > HOME_EPS and (world.tick_count + id) % SCAN_TICKS == 0:
			return_to(_home)
	elif engage_id == 0:
		guard_pos = pos
		if _shoved_from != Vector3.INF and world.tick_count - _shoved_tick >= SHOVE_SETTLE_TICKS:
			var back := _shoved_from
			_shoved_from = Vector3.INF
			var d := Grid.flat_dist(pos, back)
			if d > SHOVE_RETURN_EPS and d <= SHOVE_RETURN_MAX and _spot_free(back):
				return_to(back)


## No other ground unit overlaps a unit of this radius standing at `p`.
func _spot_free(p: Vector3) -> bool:
	for n: Unit in world.spatial.query_radius(p, radius + world.max_unit_radius, _nbuf):
		if n != self and n.alive and n.is_mobile() and not n.is_flying \
				and Grid.flat_dist(n.pos, p) < radius + n.radius:
			return false
	return world.pathing.is_walkable_world(p, is_large())


## Camp / spawn position creeps return to (CreepSystem may move it).
func home_pos() -> Vector3:
	return _home


func set_home(p: Vector3) -> void:
	_home = p
	guard_pos = p


# --- targeting -----------------------------------------------------------------------------

func is_valid_target(o: Unit) -> bool:
	return o != self and o.alive and not o.is_resource and not o.is_invulnerable and not o.is_item \
		and not o.hidden and world.is_enemy(player_id, o.player_id) \
		and (not o.status.has("invisible") or world.fog == null or world.fog.can_see(player_id, o))


## Closest valid enemy whose edge is within `r` (units preferred over structures, ties by id;
## melee units skip what they cannot walk to). The spatial query only visits buckets that hold
## hostile players, so a scan costs what the nearby enemies cost, not the friendly crowd.
func find_target(r: float) -> Unit:
	var hostile := world.hostile_mask(player_id)
	if hostile == 0:
		return null
	var best: Unit = null
	var best_score := INF
	world.spatial.query_hostile(pos, r + radius, hostile, _scan_buf)
	var fog := world.fog if world.fog != null and world.fog.enabled else null
	for o: Unit in _scan_buf:
		if not o.alive or o.id == _skip_id or o.is_invulnerable or o.is_resource or o.is_item or o.hidden:
			continue
		if fog != null and not fog.can_see(player_id, o):
			continue    # no acquisition of what the player cannot see (rules §14)
		if fog == null and o.status.has("invisible") and world.fog != null and not world.fog.can_see(player_id, o):
			continue    # nor of invisible enemies (rules §11), fog or not
		if o.status.has("sleep"):
			continue    # sleeping creeps are never auto-acquired (rules §15.3: night is safe scouting)
		var d := edge_distance(o)
		if d > r:
			continue
		var score := d + (STRUCTURE_PENALTY if o.footprint.size != Vector2i.ZERO else 0.0)
		if score > best_score or (score == best_score and o.id > best.id):
			continue
		if not _can_reach(o, d):
			continue
		best_score = score
		best = o
	_scan_buf.clear()
	return best


## Melee units only take on what they can walk up to (or already reach): an enemy on an
## unreachable plateau or across water is ignored instead of chased into a wall. Ranged and
## flying units can fight across terrain, so everything counts for them.
func _can_reach(o: Unit, edge: float) -> bool:
	if not projectile.is_empty() or is_flying or edge <= attack_range or not is_mobile():
		return true
	var rect := o.footprint if o.footprint.size != Vector2i.ZERO \
		else Rect2i(Grid.world_to_cell(o.pos), Vector2i.ONE)
	return world.pathing.can_reach(Grid.world_to_cell(pos), rect, is_large())


## Throttled acquisition (every SCAN_TICKS, staggered by id so scans spread over ticks).
func scan(r: float) -> Unit:
	if r <= 0.0 or not can_attack() or (world.tick_count + id) % SCAN_TICKS != 0:
		return null
	return find_target(r)


## The auto-acquired target, or null (also clears an invalid one).
func engaged() -> Unit:
	if engage_id == 0:
		return null
	var t := world.get_unit(engage_id)
	if t == null or not is_valid_target(t):
		engage_id = 0
		blocked_ticks = 0
		return null
	return t


func engage(t: Unit) -> void:
	engage_id = t.id
	engage_dist = edge_distance(t)
	blocked_ticks = 0
	_repath_cd = 0
	returning = false
	march_speed = 0.0               # a fight breaks the formation: full speed from here on
	_group = null
	_group_try = false
	stop_moving()


## An auto-acquired target escaped or could not be reached.
func is_lost(t: Unit) -> bool:
	return blocked_ticks > BLOCKED_TICKS or edge_distance(t) > maxf(acquire_range, engage_dist) + CHASE_SLACK


func give_up(t: Unit) -> void:
	if blocked_ticks > BLOCKED_TICKS:
		_skip_id = t.id
		_skip_ticks = SKIP_TICKS
	engage_id = 0
	blocked_ticks = 0
	stop_moving()


## Fight back when hit while idle or under an order whose handler accepts retaliation
## (attack-move, patrol, follow); creeps also wake their camp. A target just given up on
## (unreachable or stuck) and, for melee units, one they cannot walk to are ignored, so a unit
## under fire from a cliff keeps doing its job.
func _on_attacked(src: Unit) -> void:
	if not is_valid_target(src) or (returning and is_creep()):
		return
	# a creep that is hit wakes its whole camp even while it is busy itself (rules §15.1)
	if is_creep():
		_call_for_help(src)
	if acquire_range <= 0.0 or not can_attack() or engage_id != 0 or src.id == _skip_id:
		return
	if current != null and not OrderHandlers.of(current.type).accepts_retaliation(self, current):
		return
	if not _can_reach(src, edge_distance(src)):
		return
	engage(src)
	if current != null:
		resume_path = true


## Auto-acquired `t` (idle scan): creeps bring their camp along (rules §15.1).
func acquire(t: Unit) -> void:
	engage(t)
	if is_creep():
		_call_for_help(t)


## Rules §15.1 "the camp acts as one": every idle member of this creep's camp engages `src`
## (CreepSystem.alert_camp). A creep without a camp asks idle creeps within help_radius.
func _call_for_help(src: Unit) -> void:
	if not camp_id.is_empty() and world.creeps != null:
		world.creeps.alert_camp(camp_id, src)
		return
	var r := float(Defs.combat_default("help_radius", 6.0))
	world.spatial.query_radius(pos, r, _help_buf)
	for m: Unit in _help_buf:
		if m != self and m.alive and m.player_id == player_id:
			m.answer_call(src)
	_help_buf.clear()


## A camp-mate called for help against `src`: an idle, calm creep that can fight it engages.
## Busy ones (already fighting, returning home, under an order) keep what they are doing.
## Returns true when it engaged.
func answer_call(src: Unit) -> bool:
	if not alive or current != null or engage_id != 0 or returning or not can_attack() \
			or acquire_range <= 0.0 or not is_valid_target(src) or src.id == _skip_id:
		return false
	if not _can_reach(src, edge_distance(src)):
		return false
	engage(src)
	return true


# --- attacking -----------------------------------------------------------------------------

## Attacks `t` when in weapon range (turning to face it first); otherwise chases it if allowed.
func fight(t: Unit, dt: float, can_chase: bool) -> Vector3:
	if edge_distance(t) <= attack_range:
		stop_moving()
		blocked_ticks = 0
		if face(t.pos, dt) and _cooldown == 0:
			_begin_swing(t)
		return Vector3.ZERO
	if not can_chase or not is_mobile():
		return Vector3.ZERO
	if velocity.length_squared() < speed * speed * 0.0625:
		blocked_ticks += 1
	else:
		blocked_ticks = maxi(blocked_ticks - 1, 0)
	return chase_move(t, dt)


## Moves towards a (possibly moving) unit. Paths are re-requested at most every REPATH_TICKS
## and only when the target drifted; at a stale goal the unit steers straight at the target.
## A close target in plain sight (the usual case in a melee) needs no path query at all.
func chase_move(t: Unit, dt: float) -> Vector3:
	return chase_point(t.pos, dt)


## chase_move for a fixed point (gather sites, item pickups, cast targets).
func chase_point(goal: Vector3, dt: float) -> Vector3:
	var no_path := path.is_empty() and not _need_path
	if _repath_cd == 0 and (no_path or arrived or Grid.flat_dist(_goal, goal) > REPATH_DIST):
		_repath_cd = REPATH_TICKS
		if Grid.flat_dist(pos, goal) <= DIRECT_CHASE and world.pathing.line_of_walk(pos, goal, is_large()):
			stop_moving()
			_goal = goal
		else:
			begin_move(goal)
	var d := follow_path(dt)
	if d == Vector3.ZERO and not _need_path:
		d = steer_direct(goal, dt)
	return d


func steer_direct(goal: Vector3, dt: float) -> Vector3:
	var to := Vector3(goal.x - pos.x, 0.0, goal.z - pos.z)
	var l := to.length()
	if l < 0.05:
		return Vector3.ZERO
	return to / l * minf(speed, l / dt)


## Turns towards `p`; true once facing it within FACE_TOLERANCE. Structures never rotate.
func face(p: Vector3, dt: float) -> bool:
	if is_building:
		return true
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
		face(t.pos, dt)
	_swing += 1
	if not _swing_fired:
		if not valid:
			cancel_swing()
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
func cancel_swing() -> void:
	if _swing >= 0 and not _swing_fired:
		_cooldown = 0
	_swing = -1
	_swing_fired = false


## Ticks until the weapon is ready (0 = ready). Read-only for UI/AI.
func weapon_cooldown_ticks() -> int:
	return _cooldown


# --- movement ------------------------------------------------------------------------------

## Follows the current path (requesting it first if needed); returns the desired velocity.
## Sets `arrived` when the path ends.
func follow_path(dt: float) -> Vector3:
	if arrived:
		return Vector3.ZERO
	if _need_path:
		if not _request_path():
			return Vector3.ZERO
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
		return follow_path(dt)
	var spd := speed if march_speed <= 0.0 else minf(speed, march_speed)
	if last:
		spd = minf(spd, dist / dt)
	var dir := to / dist
	return Vector3(dir.x, 0.0, dir.y) * spd


## Fills `path` towards `_goal`: derived from the order's group path when a base fits (cheap
## line checks), otherwise a budgeted query that is then offered to the group as a base.
## False when this tick's path budget is used up (the unit retries next tick).
func _request_path() -> bool:
	var p := world.pathing
	var large := is_large()
	if _group_try and _group != null:
		if not p.has_budget():
			return false
		var b := _group.find_base(pos, _goal, large)
		if b != null:
			_group_try = false
			var shared := _group.derive(p, b, pos, _goal)
			if not shared.is_empty():
				path = shared
				_group = null
				return true
	if not p.can_query(pos, _goal):
		return false
	path = p.find_path(pos, _goal, large)
	if _group != null:
		_group.add_base(path, _goal, large)
		_group = null
		_group_try = false
	return true


## Separation from overlapping neighbours (the query only reaches as far as the largest unit
## radius allows an overlap; the cheap distance test runs before anything else) plus shoving
## idle allies, then the move itself.
func _steer_and_move(desired: Vector3, dt: float) -> void:
	var moving := desired != Vector3.ZERO
	var sep := Vector3.ZERO
	var px := pos.x
	var pz := pos.z
	var nbrs := world.spatial.query_radius(pos, radius + world.max_unit_radius, _nbuf)
	for n: Unit in nbrs:
		if n == self:
			continue
		var np := n.pos
		var dx := px - np.x
		var dz := pz - np.z
		var min_d := radius + n.radius
		var d2 := dx * dx + dz * dz
		if d2 >= min_d * min_d or not n.alive or n.is_flying != is_flying or not n.is_mobile():
			continue
		if harvesting and n.harvesting:
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
	if not holding and not rooted and not stunned:
		vel += sep * SEPARATION_GAIN + push_accum * PUSH_GAIN
	push_accum = Vector3.ZERO
	vel = vel.limit_length(speed * 1.25)
	var before := pos
	_try_move(vel * dt)
	# an idle unit moved only by shoves and separation remembers where it stood (settle())
	if not moving and current == null and not returning and engage_id == 0 and not is_creep() \
			and Grid.flat_dist(before, pos) > 0.001:
		if _shoved_from == Vector3.INF:
			_shoved_from = before
		_shoved_tick = world.tick_count
	velocity = (pos - prev_pos) / dt
	velocity.y = 0.0
	if moving:
		_turn_towards(desired, dt)


## Moving units shove idle, calm allies of the same player out of the way (never fighters).
func _can_push(n: Unit) -> bool:
	return n.player_id == player_id and n.current == null and not n.holding \
		and n.engage_id == 0 and n._swing < 0 and not n.returning


func _turn_towards(dir: Vector3, dt: float) -> void:
	var target := atan2(-dir.x, -dir.z)
	facing = rotate_toward(facing, target, turn_rate * dt)


## Moves by `delta` on XZ, sliding along blocked cells. A diagonal step into a cell that only
## touches the current one at a corner also needs both side cells free (the A* diagonal rule),
## so units never squeeze through gaps the pathfinder and region labels treat as closed.
## Units standing in a blocked cell (spawned inside a footprint, pushed onto a tree edge) may
## move freely to escape.
func _try_move(delta: Vector3) -> void:
	if delta.length_squared() < 1e-10:
		return
	var p := world.pathing
	var np := Vector3(pos.x + delta.x, 0.0, pos.z + delta.z)
	var a := Grid.world_to_cell(pos)
	var b := Grid.world_to_cell(np)
	if a == b or not p.is_walkable(a) or _can_step(p, a, b):
		pos.x = np.x
		pos.z = np.z
	elif p.is_walkable(Vector2i(b.x, a.y)):
		pos.x = np.x
	elif p.is_walkable(Vector2i(a.x, b.y)):
		pos.z = np.z
	else:
		return
	var size := world.map.size_world()
	pos.x = clampf(pos.x, 0.0, size.x)
	pos.z = clampf(pos.z, 0.0, size.y)
	pos.y = world.map.height_at(pos.x, pos.z)
	world.spatial.update(self)


## True when a step from cell `a` to cell `b` (at most one cell on each axis) enters a walkable
## cell without cutting a blocked corner.
static func _can_step(p: Pathing, a: Vector2i, b: Vector2i) -> bool:
	if not p.is_walkable(b):
		return false
	if a.x != b.x and a.y != b.y:
		return p.is_walkable(Vector2i(b.x, a.y)) and p.is_walkable(Vector2i(a.x, b.y))
	return true


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
	hp = maxf(hp - amount, 1.0 if cannot_die else 0.0)
	Events.unit_damaged.emit(self, amount, src)
	if world != null:
		world.notify_damaged(self, amount, src)
	if hp <= 0.0:
		die(src)
	elif src != null and src.alive:
		_on_attacked(src)


## Restores HP (healing is never rounded; capped at max_hp). Returns the amount healed.
func heal(amount: float) -> float:
	if not alive or amount <= 0.0:
		return 0.0
	var before := hp
	hp = minf(max_hp, hp + amount)
	return hp - before


func die(killer: Unit = null) -> void:
	if not alive:
		return
	alive = false
	if current != null:
		var old := current
		current = null
		OrderHandlers.of(old.type).exit(self, old)
	orders.clear()
	current = null
	holding = false
	_swing = -1
	engage_id = 0
	stop_moving()
	velocity = Vector3.ZERO
	prev_pos = pos
	if world != null:
		died_tick = world.tick_count
		world.mark_dead(self, killer)
