class_name CreepSystem
extends SimSystem
## Creeps (owner: agent D; rules.md §15, neutrals.md §1–§3; data: creep_camps.json,
## rules.creeps, map camps). Stage: creeps. Responsibilities:
##   - spawning camps from the map (template creeps, `layout` or the default ring: highest level
##     in the centre, the rest on a 2.5 m ring), camp ids on creeps (Unit.camp_id), guard
##     positions (Unit.set_home)
##   - the camp acting as one (aggro / help), camp vs guard mode (buildings started within 12 m),
##     acquire overrides, unreachable attackers, give-up timer, invulnerable full-heal return,
##     tower retreat (rules §15.1–§15.2)
##   - sleep schedules (night / day / never, sleeps_override, seeded 0–6 s stagger; buff_sleeping),
##     waking rules (damage, building, trades near a camp)
##   - bounty (4 × level + 2 + rand(0–4), taxed via Economy.add_income "bounty") and XP hand-off
##     (HeroSystem awards XP), drops rolled at match start with world.rng and spawned on death
##     (ItemSystem.spawn_item)
##   - critters (rng_critter stream) and the Hale Spring aura hand-off (BuffSystem)
## Signals (Events): camp_aggro(camp_id), camp_cleared(camp_id), camp_slept(camp_id),
##   camp_woke(camp_id), bounty_paid(pid, amount, pos).
## Called by: Main / match setup (spawn_camps), Shops (wake_near), Construction (on building
##   started near guard camps), AI (camp_state), HUD / minimap (camps(), camp_state).

const RING := 2.5

var _camps: Dictionary = {}    ## camp instance id -> {template, pos, members: Array[int], cleared, aggro}


## Spawns every camp of `map` (owner NEUTRAL_HOSTILE). Map camps without a template (test maps)
## spawn their `creeps` list on the ring. `only` (camp instance ids) limits it to those camps
## (scripted scenarios); empty = all. Returns the number of creeps spawned.
func spawn_camps(map: MapData, only: Array = []) -> int:
	var n := 0
	for i in map.creep_camps.size():
		var c: Dictionary = map.creep_camps[i]
		var cid := str(c.get("id", "camp_%d" % i))
		if not only.is_empty() and not only.has(cid):
			continue
		var centre: Vector3 = c["pos"]
		var creeps: Array = c.get("creeps", [])
		var tmpl := Defs.camps.get(str(c.get("template", "")), {}) as Dictionary
		var layout: Array = c.get("layout", tmpl.get("layout", []))
		var order := _layout_order(creeps)
		var members: Array[int] = []
		for k in creeps.size():
			var idx: int = order[k]
			var p := centre
			var face := 0.0
			if k < layout.size():
				var l: Array = layout[k]
				p = centre + Vector3(float(l[0]), 0.0, float(l[1]))
				face = deg_to_rad(float(l[2]))
			elif k > 0:
				var a := TAU * (k - 1) / maxf(creeps.size() - 1, 1)
				p = centre + Vector3(cos(a), 0.0, sin(a)) * RING
				face = a
			var u := world.spawn_unit(str(creeps[idx]), PlayerState.NEUTRAL_HOSTILE, p, face)
			if u != null:
				u.camp_id = cid
				u.set_home(u.pos)
				members.append(u.id)
				n += 1
		_camps[cid] = {"template": str(c.get("template", "")), "pos": centre, "members": members,
			"cleared": false, "aggro": false}
	return n


## Creep order for a layout: highest level first (ties in template order; neutrals §1.9).
func _layout_order(creeps: Array) -> Array:
	var idx: Array = range(creeps.size())
	idx.sort_custom(func(a: int, b: int) -> bool:
		var la := int(Defs.unit(str(creeps[a])).get("level", 1))
		var lb := int(Defs.unit(str(creeps[b])).get("level", 1))
		return la > lb or (la == lb and a < b))
	return idx


func camps() -> Dictionary:
	return _camps


func camp_members(camp_id: String) -> Array[Unit]:
	var out: Array[Unit] = []
	for uid: int in (_camps.get(camp_id, {}) as Dictionary).get("members", []):
		var u := world.get_unit(uid)
		if u != null and u.alive:
			out.append(u)
	return out


## {template, pos, alive, asleep, cleared, colour}.
func camp_state(camp_id: String) -> Dictionary:
	var c: Dictionary = _camps.get(camp_id, {})
	if c.is_empty():
		return {}
	var alive := camp_members(camp_id)
	return {"template": c["template"], "pos": c["pos"], "alive": alive.size(), "asleep": false,
		"cleared": alive.is_empty(), "colour": str((Defs.camps.get(str(c["template"]), {}) as Dictionary).get("colour", ""))}


func is_asleep(_u: Unit) -> bool:
	return false


## Rules §15.1 "the camp acts as one": a member of `camp_id` acquired `target` or was hit by
## it, so every awake, idle member engages it (busy members keep their target; other camps
## never join). Called by Unit (acquire / _on_attacked) inside the units stage, in unit order,
## so it is deterministic. Emits camp_aggro the first time a calm camp is pulled. Returns the
## number of members that engaged.
func alert_camp(camp_id: String, target: Unit) -> int:
	var c: Dictionary = _camps.get(camp_id, {})
	if c.is_empty() or target == null or not target.alive:
		return 0
	if not bool(c.get("aggro", false)):
		c["aggro"] = true
		Events.camp_aggro.emit(camp_id)
	var n := 0
	for m in camp_members(camp_id):
		if not is_asleep(m) and m.answer_call(target):
			n += 1
	return n


## Bounty for killing creep `u` (rules §15.5); draws from world.rng.
func bounty_for(u: Unit) -> int:
	var b: Dictionary = Defs.rule("creeps.bounty", {"per_level": 4, "base": 2, "rand": 4})
	return int(b["per_level"]) * u.level + int(b["base"]) + world.rng.randi_range(0, int(b["rand"]))


## A purchase / service at `building` wakes sleeping camps within rules.creeps.wake_trade_radius.
## Stub: no sleep yet.
func wake_near(_building: Unit) -> void:
	pass


## Camp bookkeeping: a pulled camp calms down once no member is fighting (the next pull emits
## camp_aggro again) and a camp whose members are all dead is cleared once (camp_cleared).
## Not in yet: sleep schedules and the give-up timer (Unit's idle behaviour leashes creeps and
## walks them home).
func sim_tick(_w: World, _dt: float) -> void:
	for cid: String in _camps:
		var c: Dictionary = _camps[cid]
		if bool(c["cleared"]):
			continue
		var alive := camp_members(cid)
		if alive.is_empty():
			c["cleared"] = true
			c["aggro"] = false
			Events.camp_cleared.emit(cid)
			continue
		if bool(c.get("aggro", false)) and alive.all(func(m: Unit) -> bool: return m.engage_id == 0):
			c["aggro"] = false
