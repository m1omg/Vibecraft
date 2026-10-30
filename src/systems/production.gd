class_name Production
extends SimSystem
## Production (owner: agent B; rules.md §4.4, §4.6, §5.1, §6.1, §18.6). Stage: production.
## Responsibilities:
##   - per-building queues (rules.economy.production_queue = 7: 1 active + 6 waiting) shared by
##     unit training, research and building upgrades; shift = 5 at once
##   - paying on queue, 100 % refund on cancel, food reserved when a unit starts (stalls "need
##     supply" while short, advisory at most every rules.economy.supply_stall_advisory s)
##   - heroes at the altar: hero slots by tier, one of each type, the first hero free (token)
##   - research levels (one of each line at a time per player) -> Tech.complete_research
##   - building upgrades (hall tiers, Lookout -> Gun Tower): queued behind units in training;
##     while one runs nothing else can be queued at that building; on completion Tech
##     transforms the building in place
##   - spawning trained units at the footprint edge toward the rally point; rally on ground,
##     unit (follow) or resource (workers gather)
## Queue entry: {kind: "unit"|"research"|"upgrade"|"revive", id, ticks, total, cost, food,
##   started: bool, token: bool (free first hero), level (research), hero (revive: the dead
##   hero's unit id; HeroSystem prices it and brings the hero back)}. Commands handled (World.SYSTEM_COMMANDS):
##   "train" {units: [building], def, queue}, "cancel" {units: [building], slot: index (-1 =
##   last)}, "research" {units: [building], def: upgrade id (building upgrades too)}.
## Signals (Events): training_started(building, id), training_completed(building, unit),
##   queue_changed(building), production_stalled(building, reason), research_started(pid, id,
##   building).
## Called by: HUD (queue_of, can_train, can_queue_research, progress), AI (train/research),
##   Tech (requirements), HeroSystem.

var _queues: Dictionary = {}     ## building id -> Array[Dictionary]
var _stall_said: Dictionary = {} ## pid -> sim time of the last "need supply" advisory


func hooks() -> Array[StringName]:
	return [&"died", &"removed"]


## A building that dies or leaves loses its queue: what was paid is lost (rules §4.6), food
## reserved by the item in progress is released, a hero token comes back.
func on_unit_died(u: Unit, _killer: Unit) -> void:
	_drop_queue(u)


func on_unit_removed(u: Unit) -> void:
	_drop_queue(u)


func _drop_queue(u: Unit) -> void:
	for e: Dictionary in _queues.get(u.id, []):
		if e.get("started", false) and int(e.get("food", 0)) > 0:
			world.adjust_food(u.player_id, -int(e["food"]), 0)
		if e.get("token", false):
			var p := world.player(u.player_id)
			if p != null:
				p.hero_tokens += 1
	_queues.erase(u.id)


func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
	var t := str(cmd.get("type", ""))
	var ok := false
	for b in units:
		match t:
			"train":
				var n := int(Defs.rule("economy.shift_train_count", 5)) if cmd.get("queue", false) else 1
				var def_id := str(cmd.get("def", ""))
				var got := train(b, def_id, n)
				if got == 0:
					_explain(b.player_id, can_train(b, def_id), def_id)
				ok = got > 0 or ok
			"cancel":
				if b.under_construction:
					world.construction.cancel_site(b)
					ok = true
				else:
					ok = cancel(b, int(cmd.get("slot", -1))) or ok
			"research":
				var uid := str(cmd.get("def", ""))
				if queue_research(b, uid):
					ok = true
				else:
					_explain(b.player_id, can_queue_research(b, uid), uid)
	return ok


## Tells the player why a train / research request was refused (once per command).
func _explain(pid: int, reason: String, id: String) -> void:
	if reason.is_empty():
		return
	var text := Defs.text("error_" + reason)
	if reason == "requirements":
		var miss: Array = world.tech.missing_requirements(pid, id)
		var names: Array[String] = []
		for m: Variant in miss:
			names.append(str(Defs.unit(str(m)).get("name", Defs.upgrade(str(m)).get("name", m))))
		text = text % ", ".join(names) if text.contains("%s") else text
	Events.notification.emit(pid, "error_" + reason, text)


func queue_of(building: Unit) -> Array:
	return _queues.get(building.id, [])


## True while `building` runs a building upgrade (nothing else can be queued there).
func is_upgrading(building: Unit) -> bool:
	for e: Dictionary in queue_of(building):
		if e["kind"] == "upgrade":
			return true
	return false


## The cost `pid` pays to queue unit `def_id` (heroes: free while a hero token is left).
func unit_cost(pid: int, def_id: String) -> Dictionary:
	var d := Defs.unit(def_id)
	var cost: Dictionary = d.get("cost", {})
	if (d.get("flags", []) as Array).has("hero"):
		var p := world.player(pid)
		if p != null and p.hero_tokens > 0:
			return {"gold": 0, "lumber": 0, "food": cost.get("food", 5), "time": cost.get("time", 55)}
	return cost


## "" when `building` can queue `def_id` now, else an error key (need_gold, need_lumber,
## queue_full, cannot_train, requirements, busy, hero_limit).
func can_train(building: Unit, def_id: String) -> String:
	if building.under_construction or not (building.def.get("trains", []) as Array).has(def_id):
		return "cannot_train"
	if is_upgrading(building):
		return "busy"
	if queue_of(building).size() >= int(Defs.rule("economy.production_queue", 7)):
		return "queue_full"
	var pid := building.player_id
	if not world.tech.requirements_met(pid, def_id):
		return "requirements"
	if (Defs.unit(def_id).get("flags", []) as Array).has("hero") and not can_acquire_hero(pid, def_id):
		return "hero_limit"
	return _afford(pid, unit_cost(pid, def_id))


func _afford(pid: int, cost: Dictionary) -> String:
	var p := world.player(pid)
	if p == null:
		return "cannot_train"
	if p.gold < int(cost.get("gold", 0)):
		return "need_gold"
	if p.lumber < int(cost.get("lumber", 0)):
		return "need_lumber"
	return ""


## Heroes (rules §6.1): one of each type, as many as the tier's slots (living, dead awaiting
## revival and in training all count).
func can_acquire_hero(pid: int, hero_id: String) -> bool:
	var count := 0
	for u in world.unit_list:
		if u.player_id == pid and u.is_hero:
			count += 1
			if u.def_id == hero_id:
				return false
	var p := world.player(pid)
	if p != null:
		for hid: int in p.heroes:
			var h := world.get_unit(hid)
			if h == null or not h.alive:
				count += 1    # dead heroes keep their slot (and their type) until revived
				if str(world.heroes.dead_record(hid).get("def_id", "")) == hero_id:
					return false
	for bid: int in _queues:
		var b := world.get_unit(bid)
		if b == null or b.player_id != pid:
			continue
		for e: Dictionary in _queues[bid]:
			if e["kind"] == "unit" and (Defs.unit(str(e["id"])).get("flags", []) as Array).has("hero"):
				count += 1
				if str(e["id"]) == hero_id:
					return false
	return count < world.heroes.hero_slots(pid)


## Queues up to `count` units (paid now). Returns how many were queued.
func train(building: Unit, def_id: String, count: int = 1) -> int:
	var n := 0
	for i in count:
		if can_train(building, def_id) != "":
			break
		var pid := building.player_id
		var cost := unit_cost(pid, def_id)
		var token := (Defs.unit(def_id).get("flags", []) as Array).has("hero") and world.player(pid).hero_tokens > 0
		world.economy.spend(pid, cost)
		if token:
			world.player(pid).hero_tokens -= 1
		_queues.get_or_add(building.id, []).append({"kind": "unit", "id": def_id, "ticks": 0,
			"total": maxi(1, roundi(float(cost.get("time", 1)) * World.TICK_RATE)), "cost": cost,
			"food": int(cost.get("food", 0)), "started": false, "token": token})
		n += 1
	if n > 0:
		Events.queue_changed.emit(building)
	return n


## Queues the revive of dead hero `hid` at `building` for `cost` (HeroSystem.revive_cost; paid
## now, food reserved when it starts, like training). True when queued.
func queue_revive(building: Unit, hid: int, cost: Dictionary) -> bool:
	if cost.is_empty():
		return false
	world.economy.spend(building.player_id, cost)
	_queues.get_or_add(building.id, []).append({"kind": "revive",
		"id": str(world.heroes.dead_record(hid).get("def_id", "")), "hero": hid, "ticks": 0,
		"total": maxi(1, roundi(float(cost.get("time", 1)) * World.TICK_RATE)), "cost": cost,
		"food": int(cost.get("food", 0)), "started": false})
	Events.queue_changed.emit(building)
	return true


## Seconds until dead hero `hid` is back: the time left once its revive runs, the full time
## while it waits in a queue; -1 when no revive is queued.
func revive_left(hid: int) -> float:
	for bid: int in _queues:
		for e: Dictionary in _queues[bid]:
			if e["kind"] == "revive" and int(e.get("hero", 0)) == hid:
				return maxf(0.0, float(int(e["total"]) - int(e["ticks"])) * World.DT)
	return -1.0


## True while dead hero `hid` is queued for revival anywhere.
func is_reviving(hid: int) -> bool:
	for bid: int in _queues:
		for e: Dictionary in _queues[bid]:
			if e["kind"] == "revive" and int(e.get("hero", 0)) == hid:
				return true
	return false


## "" when `building` can queue the next level of `upgrade_id` (research or building upgrade),
## else an error key.
func can_queue_research(building: Unit, upgrade_id: String) -> String:
	var up := Defs.upgrade(upgrade_id)
	if up.is_empty() or building.under_construction:
		return "cannot_train"
	if is_upgrading(building):
		return "busy"
	if queue_of(building).size() >= int(Defs.rule("economy.production_queue", 7)):
		return "queue_full"
	var pid := building.player_id
	if str(up.get("kind", "")) == "building_upgrade":
		if str(up.get("from", "")) != building.def_id:
			return "cannot_train"
		var lv0 := Defs.upgrade_level(upgrade_id, 1)
		if int(lv0.get("requires_tier", 1)) > world.tech.tier(pid):
			return "tier"
		if not world.tech.requirements_met(pid, upgrade_id):
			return "requirements"
		return _afford(pid, lv0.get("cost", {}))
	var err := world.tech.can_research(pid, upgrade_id, building)
	if err != "":
		return err
	if _researching(pid, upgrade_id):
		return "busy"
	var lv := Defs.upgrade_level(upgrade_id, world.tech.research_level(pid, upgrade_id) + 1)
	return _afford(pid, lv.get("cost", {}))


func _researching(pid: int, upgrade_id: String) -> bool:
	for bid: int in _queues:
		var b := world.get_unit(bid)
		if b == null or b.player_id != pid:
			continue
		for e: Dictionary in _queues[bid]:
			if e["kind"] == "research" and str(e["id"]) == upgrade_id:
				return true
	return false


## Queues a research level or a building upgrade (paid now). True when queued.
func queue_research(building: Unit, upgrade_id: String) -> bool:
	if can_queue_research(building, upgrade_id) != "":
		return false
	var pid := building.player_id
	var up := Defs.upgrade(upgrade_id)
	var upgrade := str(up.get("kind", "")) == "building_upgrade"
	var level := 1 if upgrade else world.tech.research_level(pid, upgrade_id) + 1
	var lv := Defs.upgrade_level(upgrade_id, level)
	var cost: Dictionary = lv.get("cost", {})
	world.economy.spend(pid, cost)
	_queues.get_or_add(building.id, []).append({"kind": "upgrade" if upgrade else "research",
		"id": upgrade_id, "ticks": 0, "total": maxi(1, roundi(float(lv.get("time", 1)) * World.TICK_RATE)),
		"cost": cost, "food": 0, "started": false, "level": level})
	Events.research_started.emit(pid, upgrade_id, building)
	Events.queue_changed.emit(building)
	return true


## Cancels queue entry `index` (-1 = last) with a full refund. True when something was removed.
func cancel(building: Unit, index: int = -1) -> bool:
	var q: Array = queue_of(building)
	if q.is_empty():
		return false
	var i := q.size() - 1 if index < 0 or index >= q.size() else index
	var e: Dictionary = q[i]
	q.remove_at(i)
	var factor_key := "economy.train_cancel_refund" if e["kind"] in ["unit", "revive"] else "economy.research_cancel_refund"
	world.economy.refund(building.player_id, e.get("cost", {}), float(Defs.rule(factor_key, 1.0)))
	if e.get("started", false) and int(e.get("food", 0)) > 0:
		world.adjust_food(building.player_id, -int(e["food"]), 0)
	if e.get("token", false):
		world.player(building.player_id).hero_tokens += 1
	Events.queue_changed.emit(building)
	return true


## Progress 0..1 of the queue head (0 when idle).
func progress_of(building: Unit) -> float:
	var q := queue_of(building)
	if q.is_empty():
		return 0.0
	var e: Dictionary = q[0]
	return clampf(float(e["ticks"]) / maxf(float(e["total"]), 1.0), 0.0, 1.0)


## Where a unit trained by `building` appears: the footprint edge cell nearest `toward`.
func spawn_point(building: Unit, toward: Vector3) -> Vector3:
	var r := building.footprint
	var x0 := r.position.x * Grid.CELL - 0.6
	var z0 := r.position.y * Grid.CELL - 0.6
	var x1 := r.end.x * Grid.CELL + 0.6
	var z1 := r.end.y * Grid.CELL + 0.6
	var t := toward if toward != Vector3.INF else Vector3(world.map.size_world().x * 0.5, 0.0, world.map.size_world().y * 0.5)
	var p := Vector3(clampf(t.x, x0, x1), 0.0, clampf(t.z, z0, z1))
	if p.x > x0 and p.x < x1 and p.z > z0 and p.z < z1:
		p.z = z1
	return p


func sim_tick(w: World, _dt: float) -> void:
	for bid: int in _queues.keys():
		var b := w.get_unit(bid)
		var q: Array = _queues[bid]
		if b == null or q.is_empty():
			continue
		var e: Dictionary = q[0]
		if not e["started"]:
			if e["kind"] in ["unit", "revive"] and int(e["food"]) > 0:
				var p := w.player(b.player_id)
				var cap := mini(p.food_cap, int(Defs.rule("economy.food_cap", 100)))
				if p.food_used + int(e["food"]) > cap:
					_stalled(w, b)
					continue
				w.adjust_food(b.player_id, int(e["food"]), 0)
			e["started"] = true
			if e["kind"] == "unit":
				Events.training_started.emit(b, str(e["id"]))
		e["ticks"] = int(e["ticks"]) + 1
		if int(e["ticks"]) < int(e["total"]):
			continue
		q.pop_front()
		Events.queue_changed.emit(b)
		match str(e["kind"]):
			"unit":
				var u := w.spawn_unit(str(e["id"]), b.player_id, spawn_point(b, b.rally_pos), 0.0,
					{"food_reserved": true})
				if u != null:
					Events.training_completed.emit(b, u)
					_send_to_rally(b, u)
			"research":
				w.tech.complete_research(b.player_id, str(e["id"]))
				Events.notification.emit(b.player_id, "research_done",
					Defs.text("notice_research_done") % str(Defs.upgrade(str(e["id"])).get("name", e["id"])))
			"upgrade":
				w.tech.complete_building_upgrade(b, str(e["id"]))
			"revive":
				var h := w.heroes.complete_revive(b, int(e["hero"]))
				if h != null:
					_send_to_rally(b, h)


## The queue head waits for food: production_stalled and, at most every supply_stall_advisory
## seconds per player, the "need supply" notice.
func _stalled(w: World, b: Unit) -> void:
	var gap := float(Defs.rule("economy.supply_stall_advisory", 8.0))
	if w.time - float(_stall_said.get(b.player_id, -1000.0)) < gap:
		return
	_stall_said[b.player_id] = w.time
	Events.production_stalled.emit(b, "food")
	Events.notification.emit(b.player_id, "supply_stalled", Defs.text("notice_supply_stalled"))


func _send_to_rally(b: Unit, u: Unit) -> void:
	if b.rally_pos == Vector3.INF and b.rally_id == 0:
		return
	var cmd := {"type": "smart", "player": u.player_id, "units": [u.id]}
	if b.rally_id != 0 and world.get_unit(b.rally_id) != null:
		cmd["target"] = b.rally_id
	cmd["pos"] = b.rally_pos if b.rally_pos != Vector3.INF else u.pos
	world.issue(cmd)   # a rally on a tree sends workers to chop it (World finds the tree)
