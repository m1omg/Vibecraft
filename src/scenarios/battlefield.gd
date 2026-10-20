class_name BattlefieldScenario
extends SimSystem
## Scripted match set-up and opponent for Playtest 1, "Battlefield sandbox" (data:
## scenarios.json, data/SCHEMA.md §15; docs/architecture.md §4 "Scenarios"). Main boots it for
## `scenario = "battlefield"`. Stage: ai (registered by setup_match).
## Responsibilities:
##   - setup_match(): the scenario's players (colours, start resources), Gold Seams and neutral
##     buildings come from Main; this adds every player's finished structures (snapped to the
##     nearest legal, free spot), unit groups in rows facing `face`, heroes raised to
##     `hero_level`, and the listed creep camps
##   - the opponent of every player whose control is "scenario_ai": `guard` groups hold their
##     post and attack-move at enemy units that come within `defend_radius` of their post or
##     an own structure, then regroup; a `wave` group waits like a guard group, attack-moves at
##     the enemy hall after `attack_after` seconds and then keeps hunting the nearest enemy
##     entity; idle group mates join a member that is fighting (within `assist_radius`);
##     `workers` idle (no economy in this playtest)
##   - victory "annihilation": a player with no living unit or structure is defeated
##     (PlayerState.defeated); when one side is left `result` is set and `ended` +
##     Events.match_ended are emitted once
## It issues only command dictionaries through World.issue, like a player, and uses no clock or
## random stream, so a match replays identically.
## Signals: ended(winner) (also Events.match_ended), Events.notification(pid, "wave", text) and
##   Events.alert_raised(pid, pos) when the wave starts marching.
## Called by: Main (setup_match, wave_eta, camera_start), the HUD objective line, tests.

signal ended(winner: int)

const ROLE_ARMY := "army"
const ROLE_GUARD := "guard"
const ROLE_WAVE := "wave"
const ROLE_WORKERS := "workers"
const AI_CONTROL := "scenario_ai"
const POST_EPS := 4.0                ## an idle guard further than this from its slot walks back

var scenario_id: String = ""
var def: Dictionary = {}
## One record per spawned group: {id, role, player, ai, units: Array[int], slots: Array[Vector3],
## post: Vector3, attack_tick: int (-1 = never), launched: bool, quiet_since: int}
var groups: Array[Dictionary] = []
var structures: Array[int] = []      ## ids of the structures this scenario placed
var result: Dictionary = {}          ## {} while playing; then {winner, losers, tick, time}
var _think_ticks: int = 15
var _next_think: int = 0
var _buf: Array = []


## Spawns the scenario's structures, groups and camps on an already set up World whose players
## exist (Main adds them), and registers this system for the `ai` stage.
func setup_match(w: World, id: String) -> void:
	setup(w)
	scenario_id = id
	def = Defs.scenario(id)
	_think_ticks = maxi(1, roundi(float(def.get("think_interval", 0.5)) * World.TICK_RATE))
	for p: Dictionary in def.get("players", []):
		for s: Dictionary in p.get("structures", []):
			_place_structure(int(p["slot"]), s)
	for p: Dictionary in def.get("players", []):
		for g: Dictionary in p.get("groups", []):
			_spawn_group(p, g)
	var camps: Array = def.get("camps", [])
	if not camps.is_empty():
		w.creeps.spawn_camps(w.map, camps)
	w.register_system(&"ai", self)


# --- set-up --------------------------------------------------------------------------------

## A finished structure at the nearest spot (spiral search out to snap_radius) where
## Construction.can_place accepts it and a 1-cell margin around it is free.
func _place_structure(pid: int, s: Dictionary) -> Unit:
	var def_id := str(s["def"])
	var want := _xz(s["pos"])
	var spot := _free_spot(pid, def_id, want, float(def.get("snap_radius", 12.0)))
	if spot == Vector3.INF:
		push_warning("Battlefield: no room for %s near %s" % [def_id, want])
		return null
	var centre := world.map.size_world() * 0.5
	var inward := Vector3(centre.x, 0.0, centre.y) - spot
	var face := deg_to_rad(float(s["facing"])) if s.has("facing") else atan2(-inward.x, -inward.z)
	var u := world.spawn_unit(def_id, pid, spot, face)
	if u != null:
		structures.append(u.id)
	return u


func _free_spot(pid: int, def_id: String, want: Vector3, max_r: float) -> Vector3:
	var step := Grid.CELL
	var rings := ceili(max_r / step)
	for ring in rings + 1:
		var n := maxi(1, ring * 8)
		for k in n:
			var a := TAU * k / n
			var p := want + Vector3(cos(a), 0.0, sin(a)) * ring * step
			if _spot_ok(pid, def_id, p):
				return world.construction.can_place(pid, def_id, p)["pos"]
	return Vector3.INF


func _spot_ok(pid: int, def_id: String, p: Vector3) -> bool:
	var r: Dictionary = world.construction.can_place(pid, def_id, p)
	return r["ok"] and world.pathing.is_rect_free((r["rect"] as Rect2i).grow(1))


func _spawn_group(p: Dictionary, g: Dictionary) -> void:
	var pid := int(p["slot"])
	var ids: Array[String] = []
	for pair: Array in g.get("units", []):
		for i in int(pair[1]):
			ids.append(str(pair[0]))
	var centre := _xz(g["pos"])
	var fwd := _xz(g.get("face", g["pos"])) - centre
	fwd = fwd.normalized() if fwd.length() > 0.01 else Vector3(0, 0, -1)
	var slots := formation(centre, fwd, ids.size(), int(g.get("row", 6)),
		float(g.get("spacing", def.get("formation_spacing", 1.5))))
	var rec := {"id": str(g.get("id", "")), "role": str(g.get("role", ROLE_ARMY)), "player": pid,
		"ai": str(p.get("control", "")) == AI_CONTROL, "units": [] as Array[int],
		"slots": [] as Array[Vector3], "post": centre, "attack_tick": -1, "launched": false,
		"quiet_since": 0, "target": str(g.get("target", "hall"))}
	if g.has("attack_after"):
		rec["attack_tick"] = roundi(float(g["attack_after"]) * World.TICK_RATE)
	var face := atan2(-fwd.x, -fwd.z)
	for i in ids.size():
		var u := world.spawn_unit(ids[i], pid, slots[i], face)
		if u == null:
			continue
		if u.is_hero:
			_raise_hero(u, int(def.get("hero_level", 1)))
		(rec["units"] as Array[int]).append(u.id)
		(rec["slots"] as Array[Vector3]).append(u.pos)
	groups.append(rec)


## Rows of `row` units centred on `centre`, the first row in front (towards `fwd`), `spacing`
## metres apart. Returns one position per unit, in order.
static func formation(centre: Vector3, fwd: Vector3, n: int, row: int, spacing: float) -> Array[Vector3]:
	var out: Array[Vector3] = []
	row = maxi(row, 1)
	var side := Vector3(-fwd.z, 0.0, fwd.x)
	var rows := ceili(float(n) / row)
	for i in n:
		@warning_ignore("integer_division")
		var r := i / row
		var k := i % row
		var in_row := mini(row, n - r * row)
		var across := (k - (in_row - 1) * 0.5) * spacing
		var back := (r - (rows - 1) * 0.5) * spacing
		out.append(centre + side * across - fwd * back)
	return out


## Puts a freshly spawned hero at `level` (XP, skill points and stats as if it had earned it).
func _raise_hero(u: Unit, level: int) -> void:
	if level <= 1 or world.heroes == null or u.hero.is_empty():
		return
	level = mini(level, int(Defs.rule("heroes.level_cap", 10)))
	u.hero["level"] = level
	u.hero["xp"] = Defs.xp_for_level(level)
	u.hero["skill_points"] = int(u.hero.get("skill_points", 0)) + (level - 1) \
		* int(Defs.rule("heroes.skill_points_per_level", 1))
	world.heroes.apply_attributes(u)
	u.hp = u.max_hp
	u.mana = u.max_mana


static func _xz(a: Variant) -> Vector3:
	var arr: Array = a
	return Vector3(float(arr[0]), 0.0, float(arr[1]))


# --- queries (HUD, Main, tests) --------------------------------------------------------------

func group(id: String, pid: int = -1) -> Dictionary:
	for g in groups:
		if g["id"] == id and (pid < 0 or g["player"] == pid):
			return g
	return {}


## Living units of a group record.
func members(g: Dictionary) -> Array[Unit]:
	var out: Array[Unit] = []
	for uid: int in g.get("units", []):
		var u := world.get_unit(uid)
		if u != null and u.alive:
			out.append(u)
	return out


## Sim seconds until the first wave that has not marched yet starts (-1 when none is left).
func wave_eta() -> float:
	for g in groups:
		if g["role"] == ROLE_WAVE and not g["launched"] and int(g["attack_tick"]) >= 0 and not members(g).is_empty():
			return maxf(0.0, (int(g["attack_tick"]) - world.tick_count) * World.DT)
	return -1.0


func wave_marching() -> bool:
	for g in groups:
		if g["role"] == ROLE_WAVE and g["launched"] and not members(g).is_empty():
			return true
	return false


## Where the camera starts for `pid`: its first structure (the hall), else its first group.
func camera_start(pid: int) -> Vector3:
	for sid in structures:
		var s := world.get_unit(sid)
		if s != null and s.player_id == pid:
			return s.pos
	for g in groups:
		if g["player"] == pid:
			return g["post"]
	return world.map.size_world().x * 0.5 * Vector3(1, 0, 1)


## Living units and structures (no items, no resources) a player still owns.
func entity_count(pid: int) -> int:
	var n := 0
	for u in world.unit_list:
		if u.alive and u.player_id == pid and not u.is_item and not u.is_resource:
			n += 1
	return n


func is_over() -> bool:
	return not result.is_empty()


# --- simulation ------------------------------------------------------------------------------

func sim_tick(w: World, _dt: float) -> void:
	if not result.is_empty() or w.tick_count < _next_think:
		return
	_next_think = w.tick_count + _think_ticks
	_check_victory()
	if not result.is_empty():
		return
	for g in groups:
		if not g["ai"]:
			continue
		match str(g["role"]):
			ROLE_GUARD:
				_guard(g)
			ROLE_WAVE:
				_wave(g)


## Annihilation: a scenario player with nothing left is defeated; the match ends when at most
## one player still stands.
func _check_victory() -> void:
	var standing: Array[int] = []
	var losers: Array[int] = []
	for p: Dictionary in def.get("players", []):
		var pid := int(p["slot"])
		if entity_count(pid) > 0:
			standing.append(pid)
		else:
			losers.append(pid)
			var ps := world.player(pid)
			if ps != null:
				ps.defeated = true
	if standing.size() > 1:
		return
	var winner := standing[0] if standing.size() == 1 else -1
	result = {"winner": winner, "losers": losers, "tick": world.tick_count, "time": world.time}
	ended.emit(winner)
	Events.match_ended.emit(winner, str(def.get("victory", "annihilation")))


func _guard(g: Dictionary) -> void:
	var units := members(g)
	if units.is_empty():
		return
	var pid := int(g["player"])
	if _assist(units):
		g["quiet_since"] = world.tick_count
		return
	var intruder := _intruder(pid, g["post"])
	if intruder != null:
		g["quiet_since"] = world.tick_count
		_attack_move(pid, _idle(units, true), intruder.pos)
		return
	if (world.tick_count - int(g["quiet_since"])) * World.DT < float(def.get("regroup_after", 6.0)):
		return
	_regroup(g, units)


func _wave(g: Dictionary) -> void:
	var units := members(g)
	if units.is_empty():
		return
	var pid := int(g["player"])
	if not g["launched"]:
		if int(g["attack_tick"]) < 0 or world.tick_count < int(g["attack_tick"]):
			_guard(g)
			return
		g["launched"] = true
		var goal := _wave_goal(pid, g, _centre(units))
		if goal != Vector3.INF:
			_attack_move(pid, units, goal)
		_announce(pid, _centre(units))
		return
	# marching: idle members hunt the nearest enemy entity
	var idle := _idle(units, false)
	if idle.is_empty():
		return
	var t := _nearest_enemy(pid, _centre(idle), false)
	if t != null:
		_attack_move(pid, idle, t.pos)


## Every other scenario player hears that the wave marches; Space jumps to it.
func _announce(pid: int, at: Vector3) -> void:
	for p: Dictionary in def.get("players", []):
		var other := int(p["slot"])
		if other != pid and world.is_enemy(pid, other):
			Events.notification.emit(other, "wave", Defs.text("notify_warband_marching"))
			Events.alert_raised.emit(other, at)


## The wave's first goal: the target enemy's hall (its first scenario structure), else the
## nearest enemy entity.
func _wave_goal(pid: int, g: Dictionary, from: Vector3) -> Vector3:
	if g["target"] == "hall":
		for sid in structures:
			var s := world.get_unit(sid)
			if s != null and s.alive and world.is_enemy(pid, s.player_id):
				return s.pos
	var t := _nearest_enemy(pid, from, false)
	return t.pos if t != null else Vector3.INF


## Idle members join the fight of a member that has a target (within assist_radius of it).
## Returns true when any member is fighting.
func _assist(units: Array[Unit]) -> bool:
	var fighting: Unit = null
	var target: Unit = null
	for u in units:
		var tid := u.combat_target_id()
		var t := world.get_unit(tid) if tid != 0 else null
		if t != null and t.alive:
			fighting = u
			target = t
			break
	if fighting == null:
		return false
	var r := float(def.get("assist_radius", 14.0))
	var idle: Array[Unit] = []
	for u in _idle(units, true):
		if u != fighting and Grid.flat_dist(u.pos, fighting.pos) <= r:
			idle.append(u)
	_attack_move(int(fighting.player_id), idle, target.pos)
	return true


## Closest mobile enemy-player unit (creeps ignored) within defend_radius of `post` or of one of
## the player's structures.
func _intruder(pid: int, post: Vector3) -> Unit:
	var r := float(def.get("defend_radius", 24.0))
	var anchors: Array[Vector3] = [post]
	for sid in structures:
		var s := world.get_unit(sid)
		if s != null and s.alive and s.player_id == pid:
			anchors.append(s.pos)
	var best: Unit = null
	var best_d := INF
	for u in world.unit_list:
		if not u.alive or not u.is_mobile() or u.hidden or u.player_id >= PlayerState.NEUTRAL_HOSTILE \
				or not world.is_enemy(pid, u.player_id):
			continue
		for a in anchors:
			var d := Grid.flat_dist(u.pos, a)
			if d <= r:
				var dp := Grid.flat_dist(u.pos, post)
				if dp < best_d:
					best_d = dp
					best = u
				break
	return best


## Nearest living entity of an enemy player (creeps and neutrals ignored; structures included
## unless `mobile_only`).
func _nearest_enemy(pid: int, from: Vector3, mobile_only: bool) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in world.unit_list:
		if not u.alive or u.hidden or u.is_item or u.is_resource or u.player_id >= PlayerState.NEUTRAL_HOSTILE:
			continue
		if not world.is_enemy(pid, u.player_id) or (mobile_only and not u.is_mobile()):
			continue
		var d := Grid.flat_dist(u.pos, from)
		if d < best_d:
			best_d = d
			best = u
	return best


## Idle guards walk back to their formation slots (one move per unit, no shared path needed).
func _regroup(g: Dictionary, units: Array[Unit]) -> void:
	var slots: Array = g["slots"]
	var ids: Array = g["units"]
	for u in _idle(units, false):
		var i := ids.find(u.id)
		var slot: Vector3 = slots[i] if i >= 0 and i < slots.size() else g["post"]
		if Grid.flat_dist(u.pos, slot) > POST_EPS:
			world.issue({"type": "move", "player": u.player_id, "units": [u.id], "pos": slot})


## Members without an order and not fighting. `include_moving` also counts members walking back
## to their post (a plain move), so a threat can redirect them.
func _idle(units: Array[Unit], include_moving: bool) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in units:
		if u.engage_id != 0 or u.combat_target_id() != 0:
			continue
		if u.current == null or (include_moving and u.current.type == Order.Type.MOVE):
			out.append(u)
	return out


func _attack_move(pid: int, units: Array[Unit], goal: Vector3) -> void:
	if units.is_empty():
		return
	var ids: Array = []
	for u in units:
		ids.append(u.id)
	world.issue({"type": "attack_move", "player": pid, "units": ids, "pos": goal})


static func _centre(units: Array[Unit]) -> Vector3:
	var c := Vector3.ZERO
	for u in units:
		c += u.pos
	return c / maxf(units.size(), 1.0)
