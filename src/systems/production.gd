class_name Production
extends SimSystem
## Production (owner: agent B; rules.md §4.4, §4.6, §18.6). Stage: production.
## Responsibilities:
##   - per-building queues (rules.economy.production_queue = 7: 1 active + 6 waiting) shared by
##     unit training, research, hall / tower upgrades and hero revives; shift = 5 at once
##   - paying on queue, 100 % refund on cancel, food reserved when an item starts (stalls
##     "need supply" while short), hero slot / token rules for altars (with HeroSystem)
##   - spawning trained units at the footprint edge toward the rally point; rally on ground,
##     unit (follow) or resource (workers gather)
## Queue entry: {kind: "unit"|"research"|"upgrade"|"revive", id, ticks, total, cost, food,
##   started: bool}. Commands handled (World.SYSTEM_COMMANDS): "train" {units: [building],
##   def, queue}, "cancel" {units: [building], slot: index (-1 = last)}, "research" {units:
##   [building], def: upgrade id (building upgrades too)}.
## Signals (Events): training_started(building, id), training_completed(building, unit),
##   queue_changed(building), production_stalled(building, reason).
## Called by: HUD (queue_of, progress), AI (train/research), Tech (requirements), HeroSystem.

var _queues: Dictionary = {}     ## building id -> Array[Dictionary]


func hooks() -> Array[StringName]:
	return [&"died", &"removed"]


func on_unit_died(u: Unit, _killer: Unit) -> void:
	_queues.erase(u.id)


func on_unit_removed(u: Unit) -> void:
	_queues.erase(u.id)


func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
	var t := str(cmd.get("type", ""))
	var ok := false
	for b in units:
		match t:
			"train":
				var n := int(Defs.rule("economy.shift_train_count", 5)) if cmd.get("queue", false) else 1
				ok = train(b, str(cmd.get("def", "")), n) > 0 or ok
			"cancel":
				if b.under_construction:
					world.construction.cancel_site(b)
					ok = true
				else:
					ok = cancel(b, int(cmd.get("slot", -1))) or ok
			"research":
				ok = queue_research(b, str(cmd.get("def", ""))) or ok
	return ok


func queue_of(building: Unit) -> Array:
	return _queues.get(building.id, [])


## "" when `building` can queue `def_id` now, else an error key (need_gold, need_lumber,
## queue_full, cannot_train, requirements).
func can_train(building: Unit, def_id: String) -> String:
	if building.under_construction or not (building.def.get("trains", []) as Array).has(def_id):
		return "cannot_train"
	if queue_of(building).size() >= int(Defs.rule("economy.production_queue", 7)):
		return "queue_full"
	if not world.tech.requirements_met(building.player_id, def_id):
		return "requirements"
	if not world.economy.can_afford(building.player_id, Defs.unit(def_id).get("cost", {})):
		return "need_gold"
	return ""


## Queues up to `count` units (paid now). Returns how many were queued.
func train(building: Unit, def_id: String, count: int = 1) -> int:
	var n := 0
	for i in count:
		if can_train(building, def_id) != "":
			break
		var d := Defs.unit(def_id)
		var cost: Dictionary = d.get("cost", {})
		world.economy.spend(building.player_id, cost)
		_queues.get_or_add(building.id, []).append({"kind": "unit", "id": def_id, "ticks": 0,
			"total": maxi(1, roundi(float(cost.get("time", 1)) * World.TICK_RATE)), "cost": cost,
			"food": int(cost.get("food", 0)), "started": false})
		n += 1
	if n > 0:
		Events.queue_changed.emit(building)
	return n


## Queues a research level or a building upgrade (Tech decides validity). Stub: false.
func queue_research(_building: Unit, _upgrade_id: String) -> bool:
	return false


## Cancels queue entry `index` (-1 = last) with a full refund. True when something was removed.
func cancel(building: Unit, index: int = -1) -> bool:
	var q: Array = queue_of(building)
	if q.is_empty():
		return false
	var i := q.size() - 1 if index < 0 or index >= q.size() else index
	var e: Dictionary = q[i]
	q.remove_at(i)
	world.economy.refund(building.player_id, e.get("cost", {}), float(Defs.rule("economy.train_cancel_refund", 1.0)))
	if e.get("started", false) and int(e.get("food", 0)) > 0:
		world.adjust_food(building.player_id, -int(e["food"]), 0)
	Events.queue_changed.emit(building)
	return true


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
			if e["kind"] == "unit" and int(e["food"]) > 0:
				var p := w.player(b.player_id)
				var cap := mini(p.food_cap, int(Defs.rule("economy.food_cap", 100)))
				if p.food_used + int(e["food"]) > cap:
					continue
				w.adjust_food(b.player_id, int(e["food"]), 0)
			e["started"] = true
			Events.training_started.emit(b, str(e["id"]))
		e["ticks"] = int(e["ticks"]) + 1
		if int(e["ticks"]) < int(e["total"]):
			continue
		q.pop_front()
		Events.queue_changed.emit(b)
		if e["kind"] == "unit":
			var u := w.spawn_unit(str(e["id"]), b.player_id, spawn_point(b, b.rally_pos), 0.0,
				{"food_reserved": true})
			if u != null:
				Events.training_completed.emit(b, u)
				_send_to_rally(b, u)


func _send_to_rally(b: Unit, u: Unit) -> void:
	if b.rally_pos == Vector3.INF and b.rally_id == 0:
		return
	var cmd := {"type": "smart", "player": u.player_id, "units": [u.id]}
	if b.rally_id != 0 and world.get_unit(b.rally_id) != null:
		cmd["target"] = b.rally_id
	cmd["pos"] = b.rally_pos if b.rally_pos != Vector3.INF else u.pos
	world.issue(cmd)
