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
const SPELL_TICKS := 15        ## the creep spell AI thinks twice a second

var _camps: Dictionary = {}    ## camp instance id -> {template, pos, members: Array[int], cleared, aggro, sleeps}
var _drops: Dictionary = {}    ## carrier creep id -> item id (rolled at match start, neutrals §1.8)
var _last_fight: Dictionary = {}   ## camp id -> sim time of the last damage a member dealt or took
var _asleep: Dictionary = {}   ## camp id -> true while its members sleep


func hooks() -> Array[StringName]:
	return [&"spawned", &"died", &"damaged"]


## A member hit or hitting keeps its camp fighting (the give-up timer) and wakes it.
func on_unit_damaged(u: Unit, _amount: float, src: Unit) -> void:
	if u.camp_id != "":
		_last_fight[u.camp_id] = world.time
		if _asleep.get(u.camp_id, false):
			wake_camp(u.camp_id)
	if src != null and src.camp_id != "":
		_last_fight[src.camp_id] = world.time


## A building started within guard_build_radius of a sleeping camp wakes it (rules §15.3).
func on_unit_spawned(u: Unit) -> void:
	if not u.is_structure() or u.player_id >= PlayerState.NEUTRAL_HOSTILE or _asleep.is_empty():
		return
	var r := float(Defs.rule("creeps.guard_build_radius", 12.0))
	for cid: String in _asleep.keys():
		if Grid.flat_dist(u.pos, (_camps[cid] as Dictionary)["pos"]) <= r:
			wake_camp(cid)


## A creep falls: bounty to the killer's owner (rules §15.5: taxed like mined gold, none for
## summons or neutral killers), its drop on the ground, an on-death ground effect (Loose Straw).
func on_unit_died(u: Unit, killer: Unit) -> void:
	if u.camp_id == "" and not u.is_creep():
		return
	if killer != null and not u.is_summoned and killer.player_id < PlayerState.NEUTRAL_HOSTILE:
		var got := world.economy.add_income(killer.player_id, "gold", bounty_for(u), "bounty")
		if got > 0:
			Events.bounty_paid.emit(killer.player_id, got, u.pos)
	if _drops.has(u.id):
		world.items.spawn_item(str(_drops[u.id]), u.pos)
		_drops.erase(u.id)
	for aid: Variant in u.abilities:
		var g := str(Defs.ability_rank(str(aid), 1).get("on_death_ground_effect", ""))
		if g != "":
			var gd := Defs.ground_effect(g)
			world.abilities.add_ground_effect(g, u, u.pos, float(gd.get("radius", 2.0)), float(gd.get("duration", 4.0)))


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
				u.leash_range = float(Defs.rule("creeps.leash", 18.75))
				members.append(u.id)
				n += 1
		_camps[cid] = {"template": str(c.get("template", "")), "pos": centre, "members": members,
			"cleared": false, "aggro": false,
			"sleeps": str(c.get("sleeps_override", tmpl.get("sleeps_override", tmpl.get("sleeps", "night"))))}
		_roll_drops(cid, tmpl.get("drops", {}), members)
	return n


## Drops (neutrals §1.8), rolled now with the seeded sim RNG: Drop B goes to the camp's
## highest-level creep, Drop A to its lowest (ties: the first in order; summons never carry);
## each item is picked from its pool (items of the listed classes at the drop's level), or the
## drop's fixed `item`.
func _roll_drops(cid: String, drops: Dictionary, members: Array[int]) -> void:
	if drops.is_empty() or members.is_empty():
		return
	var hi := members[0]
	var lo := members[0]
	for uid in members:
		var u := world.get_unit(uid)
		if u.level > world.get_unit(hi).level:
			hi = uid
		if u.level < world.get_unit(lo).level:
			lo = uid
	for slot: String in ["B", "A"]:
		if not drops.has(slot):
			continue
		var spec: Dictionary = drops[slot]
		var item := str(spec.get("item", ""))
		if item == "":
			var pool: Array = []
			for iid: String in Defs.items:
				var d: Dictionary = Defs.items[iid]
				if (spec.get("class", []) as Array).has(str(d.get("class", ""))) and int(d.get("level", 0)) == int(spec.get("level", 1)):
					pool.append(iid)
			pool.sort()
			if pool.is_empty():
				continue
			item = str(pool[world.rng.randi_range(0, pool.size() - 1)])
		var carrier := hi if slot == "B" or not drops.has("B") else lo
		if _drops.has(carrier):
			carrier = lo if carrier == hi else hi
		_drops[carrier] = item


## The item a creep will drop ("" when none).
func drop_of(u: Unit) -> String:
	return str(_drops.get(u.id, ""))


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
	return {"template": c["template"], "pos": c["pos"], "alive": alive.size(),
		"asleep": bool(_asleep.get(camp_id, false)), "cleared": alive.is_empty(),
		"colour": str((Defs.camps.get(str(c["template"]), {}) as Dictionary).get("colour", ""))}


func is_asleep(u: Unit) -> bool:
	return u.status.has("sleep")


## Puts a calm camp to sleep (buff_sleeping on every member: as stunned, wakes on damage).
func sleep_camp(camp_id: String) -> void:
	_asleep[camp_id] = true
	for m in camp_members(camp_id):
		world.buffs.apply(m, "buff_sleeping", null, {}, -1.0)
	Events.camp_slept.emit(camp_id)


func wake_camp(camp_id: String) -> void:
	if not _asleep.has(camp_id):
		return
	_asleep.erase(camp_id)
	for m in camp_members(camp_id):
		world.buffs.remove(m, "buff_sleeping")
	Events.camp_woke.emit(camp_id)


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


## A purchase / service at `building` wakes sleeping camps with a member within
## rules.creeps.wake_trade_radius of its footprint edge (rules §15.3).
func wake_near(building: Unit) -> void:
	var r := float(Defs.rule("creeps.wake_trade_radius", 10.0))
	for cid: String in _asleep.keys():
		for m in camp_members(cid):
			if building.edge_distance(m) <= r:
				wake_camp(cid)
				break


## Camp bookkeeping (rules §15.1–§15.3): a pulled camp calms down once no member is fighting
## (the next pull emits camp_aggro again); a camp that neither dealt nor took damage for
## give_up_time walks home; every return is invulnerable and ends with a full heal; camps sleep
## on their schedule (night by default) once home and calm, each camp 0–6 s after dusk (a
## seeded stagger), and wake at dawn the same way; the creep spell AI casts for pulled camps; a
## camp whose members are all dead is cleared once (camp_cleared).
func sim_tick(w: World, _dt: float) -> void:
	var night := DayNight.is_night_at(w.time)
	for cid: String in _camps:
		var c: Dictionary = _camps[cid]
		if bool(c["cleared"]):
			continue
		var alive := camp_members(cid)
		if alive.is_empty():
			c["cleared"] = true
			c["aggro"] = false
			_asleep.erase(cid)
			Events.camp_cleared.emit(cid)
			continue
		var fighting := alive.any(func(m: Unit) -> bool: return m.engage_id != 0 or m.current != null)
		if bool(c.get("aggro", false)):
			if not fighting:
				c["aggro"] = false
			elif w.time - float(_last_fight.get(cid, w.time)) > float(Defs.rule("creeps.give_up_time", 10.0)):
				for m in alive:
					m.engage_id = 0
					m.clear_orders()
					m.return_to(m.home_pos())
				c["aggro"] = false
			elif w.tick_count % SPELL_TICKS == 0:
				_creep_spells(alive)
		for m in alive:
			var shielded := w.buffs.has_buff(m, "buff_returning")
			if m.returning and not shielded:
				w.buffs.apply(m, "buff_returning", null, {}, -1.0)
			elif shielded and not m.returning:
				w.buffs.remove(m, "buff_returning")
				m.hp = m.max_hp
				m.mana = m.max_mana
		_schedule_sleep(w, cid, c, alive, night, fighting)


## Sleep schedules: "night" camps sleep from dusk, "day" camps by day, "never" never; each camp
## falls asleep / wakes stagger seconds after the boundary, a stagger seeded by the match seed
## and the camp id (no draw from the shared stream).
func _schedule_sleep(w: World, cid: String, c: Dictionary, alive: Array[Unit], night: bool, fighting: bool) -> void:
	var sched := str(c.get("sleeps", "night"))
	if sched == "never":
		return
	var want := night if sched == "night" else not night
	var hour := DayNight.hour_at(w.time)
	var since := fposmod(hour - (DayNight.DUSK if night else DayNight.DAWN), 24.0) * DayNight.DAY_LENGTH / 24.0
	var stagger := float(Defs.rule("creeps.sleep_stagger", 6.0)) * float(absi(hash([w.rng.seed, cid])) % 1000) / 1000.0
	var asleep := bool(_asleep.get(cid, false))
	if want and not asleep and since >= stagger and not fighting and not bool(c.get("aggro", false)):
		if alive.all(func(m: Unit) -> bool: return not m.returning and Grid.flat_dist(m.pos, m.home_pos()) <= Unit.HOME_EPS):
			sleep_camp(cid)
	elif not want and asleep and since >= stagger:
		wake_camp(cid)


## The creep spell AI (neutrals §1.7, through SpellAi): each awake member of a pulled camp casts
## one ready ability: summons and camp buffs when pulled, blasts on 2+ enemies or a hero, ground
## effects on the biggest cluster, heals on the most hurt camp-mate below 60 % (itself last),
## roots and silences on heroes first.
func _creep_spells(alive: Array[Unit]) -> void:
	for m in alive:
		if m.stunned or m.returning or (m.current != null and m.current.type == Order.Type.CAST):
			continue
		for aid: Variant in m.abilities:
			var id := str(aid)
			if world.abilities.cast_error(m, id, null, false) != "":
				continue
			var pick := SpellAi.pick(world, m, id, alive)
			if pick.is_empty():
				continue
			var cmd := {"type": "cast", "player": m.player_id, "units": [m.id], "ability": id}
			cmd.merge(pick)
			world.issue(cmd)
			break
