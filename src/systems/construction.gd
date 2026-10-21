class_name Construction
extends SimSystem
## Construction (owner: agent A; rules.md §4.6–§4.8, §8; factions.<id>.max_builders,
## extra_builder_rate, extra_builder_lumber_per_s, build_verb). Stage: production.
## Responsibilities:
##   - placement validation (footprint free, flat, no ramp / water / map edge, hall–mine gap 6.0 m,
##     explored ground, no foreign units inside) for the build ghost and for build orders
##   - build orders: cost check on order, pay on start, sites that start at 10 % HP and rise with
##     progress, per-faction build verbs (kingdom scaffold + Hod Chain extra builders paying
##     lumber; clans one builder), completion (food, drop-off, production switch on), cancel (75 %)
##   - repair (rules §4.8: 1.5 × build time, 30 % cost pro rata, autocast 8 m) for structures and
##     mechanical units
##   - garrison buildings (clans Home Yurt, Roll the Felt / Unload All; sling attack per occupant)
##   - worker defence signatures that live on buildings (Levy Horn and Sound the Gong effects call
##     into here or into Economy; see docs/m2-ownership.md)
## Signals (Events): construction_started(site, builder), construction_cancelled(site),
##   building_completed(site), repair_started(worker, target), placement_rejected(pid, def, reason),
##   garrison_changed(building).
## Called by: orders/build.gd, repair.gd, enter.gd (see their headers), CommandInput / HUD
##   (can_place for the ghost), Production (cancel of a site), AI.

const BUILD_REACH := 1.0
## A builder's hammer / mallet stroke (visual cadence of the work clip; progress is continuous).
const STROKE_TICKS := 22

## site id -> Array[int] of builder ids (the first is the main builder; extra builders join the
## kingdom's Hod Chain). Progress is advanced once per site in sim_tick.
var _builders: Dictionary = {}
## repairer ids -> true (repair_started fires once per job).
var _repairing: Dictionary = {}


func hooks() -> Array[StringName]:
	return [&"died", &"removed"]


func on_unit_died(u: Unit, _killer: Unit) -> void:
	_forget(u)


func on_unit_removed(u: Unit) -> void:
	_forget(u)


func _forget(u: Unit) -> void:
	if _builders.has(u.id):
		_release_builders(u.id)
	for sid: int in _builders:
		(_builders[sid] as Array).erase(u.id)
	_repairing.erase(u.id)


# --- placement -----------------------------------------------------------------------------

## Placement grid cell states (cell_states; the ghost's grid, juice BLD-02).
const CELL_CONTEXT := 0       ## the border around the footprint (drawn for context only)
const CELL_OK := 1
const CELL_BLOCKED := 2       ## pathing (buildings, trees) or a foreign unit
const CELL_TERRAIN := 3       ## not level: ramp, water, cliff step, map edge tile
const CELL_UNEXPLORED := 4
const CELL_RULE := 5          ## a hall within the 6.0 m gap of a Gold Seam
const CELL_OUTSIDE := 6       ## off the map
## Worst cell first -> can_place reason.
const REASON_OF: Array = [[CELL_OUTSIDE, "out_of_bounds"], [CELL_TERRAIN, "not_flat"],
	[CELL_BLOCKED, "blocked"], [CELL_UNEXPLORED, "unexplored"], [CELL_RULE, "too_close_to_mine"]]


## Placement check for `def_id` centred at `pos` (snapped to the footprint grid): every
## footprint cell must be OK (cell_states).
## Returns {ok: bool, reason: String (error key), rect: Rect2i (cells), pos: Vector3 (snapped)}.
func can_place(pid: int, def_id: String, pos: Vector3) -> Dictionary:
	var d := Defs.unit(def_id)
	var out := {"ok": false, "reason": "", "rect": Rect2i(), "pos": pos}
	if d.is_empty() or d.get("kind") != "building" or d.get("upgrade_only", false):
		out["reason"] = "cannot_build"
		return out
	var cs := cell_states(pid, def_id, pos, 0)
	out["rect"] = cs["rect"]
	out["pos"] = cs["pos"]
	var states: PackedByteArray = cs["states"]
	for r: Array in REASON_OF:
		if states.has(int(r[0])):
			out["reason"] = str(r[1])
			return out
	out["ok"] = true
	return out


## The footprint of `def_id` snapped at `pos`, grown by `border` cells, cell by cell (rules §4.6:
## level ground, free of buildings, trees and foreign units, explored, a hall 6.0 m from any
## Gold Seam). Returns {rect: Rect2i (footprint), outer: Rect2i (with the border), pos: Vector3
## (snapped centre), states: PackedByteArray (outer row-major, CELL_*)}. Reads only.
func cell_states(pid: int, def_id: String, pos: Vector3, border: int = 2) -> Dictionary:
	var d := Defs.unit(def_id)
	var fp: Array = d.get("footprint", [1, 1])
	var size := Vector2i(int(fp[0]), int(fp[1]))
	var spot := Grid.snap_to_footprint(pos, size)
	var rect := Grid.footprint_rect(spot, size)
	var outer := rect.grow(border)
	var states := PackedByteArray()
	states.resize(outer.size.x * outer.size.y)
	var m := world.map
	var cells := m.size_cells()
	var t0 := Grid.cell_to_tile(rect.position)
	var lvl := m.level_at_tile(t0.x, t0.y) if rect.position.x >= 0 and rect.position.y >= 0 \
		and rect.position.x < cells.x and rect.position.y < cells.y else -1
	var units := _foreign_units_near(pid, rect)
	var mines: Array[Rect2i] = []
	if (d.get("flags", []) as Array).has("town_hall"):
		for u in world.unit_list:
			if u.has_flag("gold_mine") and u.footprint.size != Vector2i.ZERO:
				mines.append(u.footprint)
	var gap := float(Defs.rule("economy.hall_mine_gap", 6.0))
	var fog := world.fog
	for y in outer.size.y:
		for x in outer.size.x:
			var c := outer.position + Vector2i(x, y)
			var i := y * outer.size.x + x
			if not rect.has_point(c):
				states[i] = CELL_CONTEXT
			elif c.x < 0 or c.y < 0 or c.x >= cells.x or c.y >= cells.y:
				states[i] = CELL_OUTSIDE
			else:
				var t := Grid.cell_to_tile(c)
				var ti := m.idx(t.x, t.y)
				if m.ramp[ti] > 0 or m.water[ti] == 1 or m.is_boundary_tile(t.x, t.y) or m.cliff[ti] != lvl:
					states[i] = CELL_TERRAIN
				elif not world.pathing.is_walkable(c) or _unit_in_cell(units, c):
					states[i] = CELL_BLOCKED
				elif fog != null and not fog.is_explored(pid, Grid.cell_to_world(c)):
					states[i] = CELL_UNEXPLORED
				elif _near_mine(mines, c, gap):
					states[i] = CELL_RULE
				else:
					states[i] = CELL_OK
	return {"rect": rect, "outer": outer, "pos": spot, "states": states}


## Units of another player (or flying units of nobody) near `rect` that can block it, as
## [Vector2 (x, z), half radius]; the builder's own units are pushed out when the site starts
## (rules §4.6).
func _foreign_units_near(pid: int, rect: Rect2i) -> Array:
	var area := Rect2(rect.position.x * Grid.CELL, rect.position.y * Grid.CELL, rect.size.x * Grid.CELL,
		rect.size.y * Grid.CELL)
	var out: Array = []
	for u in world.unit_list:
		if not u.alive or u.hidden or u.is_flying or not u.is_mobile() or u.player_id == pid:
			continue
		var p := Vector2(u.pos.x, u.pos.z)
		if area.grow(u.radius * 0.5).has_point(p):
			out.append([p, u.radius * 0.5])
	return out


static func _unit_in_cell(units: Array, c: Vector2i) -> bool:
	for e: Array in units:
		var r := Rect2(c.x * Grid.CELL, c.y * Grid.CELL, Grid.CELL, Grid.CELL).grow(float(e[1]))
		if r.has_point(e[0]):
			return true
	return false


## True when cell `c` lies within `gap` metres of a Gold Seam footprint.
static func _near_mine(mines: Array[Rect2i], c: Vector2i, gap: float) -> bool:
	for f in mines:
		var dx := maxi(0, maxi(c.x - (f.end.x - 1), f.position.x - c.x) - 1)
		var dz := maxi(0, maxi(c.y - (f.end.y - 1), f.position.y - c.y) - 1)
		if Vector2(dx, dz).length() * Grid.CELL < gap - 1e-3:
			return true
	return false


## BUILD order validation on issue (cost checked at order time, rules §4.6; menus, tier and
## requirements by Tech.can_build).
func can_order_build(worker: Unit, o: Order) -> bool:
	if o.target_id != 0:
		var site := world.get_unit(o.target_id)
		return site != null and site.under_construction and site.player_id == worker.player_id
	if world.tech.can_build(worker.player_id, o.def_id) != "":
		return false
	if not can_place(worker.player_id, o.def_id, o.target_pos)["ok"]:
		return false
	var cost: Dictionary = Defs.unit(o.def_id).get("cost", {})
	return not bool(Defs.rule("economy.build_check_on_order", true)) or world.economy.can_afford(worker.player_id, cost)


## True when the worker touches the planned footprint.
func builder_in_reach(worker: Unit, o: Order) -> bool:
	var d := Defs.unit(o.def_id)
	var fp: Array = d.get("footprint", [1, 1])
	var rect := Grid.footprint_rect(Grid.snap_to_footprint(o.target_pos, Vector2i(int(fp[0]), int(fp[1]))),
		Vector2i(int(fp[0]), int(fp[1])))
	var x0 := rect.position.x * Grid.CELL
	var z0 := rect.position.y * Grid.CELL
	var cx := clampf(worker.pos.x, x0, x0 + rect.size.x * Grid.CELL)
	var cz := clampf(worker.pos.z, z0, z0 + rect.size.y * Grid.CELL)
	return Vector2(worker.pos.x - cx, worker.pos.z - cz).length() - worker.radius <= BUILD_REACH


# --- sites ---------------------------------------------------------------------------------

## The builder arrived: re-check the spot and the cost, pay (rules.economy.build_pay "on_start"),
## push own units out, start the site. Returns the site or null (the order then completes; the
## player hears why).
func on_builder_arrived(worker: Unit, o: Order) -> Unit:
	var pid := worker.player_id
	var spot := can_place(pid, o.def_id, o.target_pos)
	if not spot["ok"]:
		_reject(pid, o.def_id, str(spot["reason"]))
		return null
	var cost: Dictionary = Defs.unit(o.def_id).get("cost", {})
	if not world.economy.can_afford(pid, cost):
		_reject(pid, o.def_id, "need_lumber" if world.economy.can_afford(pid, {"gold": int(cost.get("gold", 0))}) else "need_gold")
		return null
	world.economy.spend(pid, cost)
	var rect: Rect2i = spot["rect"]
	_push_out(pid, rect, worker)
	var site := start_site(pid, o.def_id, spot["pos"], worker.facing)
	if site == null:
		world.economy.refund(pid, cost)
		return null
	_builders[site.id] = [worker.id]
	Events.construction_started.emit(site, worker)
	return site


func _reject(pid: int, def_id: String, reason: String) -> void:
	Events.placement_rejected.emit(pid, def_id, reason)
	Events.notification.emit(pid, "error_" + reason, Defs.text("error_" + reason))


## Own units standing in a new site's footprint step out to the nearest free cell beside it.
func _push_out(pid: int, rect: Rect2i, _builder: Unit) -> void:
	var area := Rect2(rect.position.x * Grid.CELL, rect.position.y * Grid.CELL, rect.size.x * Grid.CELL,
		rect.size.y * Grid.CELL)
	for u in world.unit_list:
		if not u.alive or u.hidden or not u.is_mobile() or u.player_id != pid:
			continue
		if not area.grow(u.radius).has_point(Vector2(u.pos.x, u.pos.z)):
			continue
		var p := world.economy.approach_rect(rect, u.pos, u.radius + 0.1)
		u.teleport(Grid.cell_to_world(world.pathing.nearest_walkable(Grid.world_to_cell(p))))


## Spawns an under-construction site (10 % HP, no food or function until complete).
func start_site(pid: int, def_id: String, pos: Vector3, facing: float = 0.0) -> Unit:
	var site := world.spawn_unit(def_id, pid, pos, facing, {"under_construction": true,
		"hp_fraction": float(Defs.rule("economy.build_start_hp", 0.1))})
	if site != null:
		site.build_progress = 0.0
	return site


func _faction(pid: int) -> Dictionary:
	var p := world.player(pid)
	return Defs.faction(p.faction) if p != null and p.faction != "" else {}


func max_builders(pid: int) -> int:
	return maxi(1, int(_faction(pid).get("max_builders", 1)))


## The builders currently on a site (ids, main builder first).
func builders_of(site: Unit) -> Array:
	return (_builders.get(site.id, []) as Array).duplicate()


## A worker joins a site: the main builder of an abandoned site, or an extra builder while the
## faction allows more (kingdom Hod Chain: up to 3; clans: one builder per site).
func join_site(worker: Unit, site: Unit, _o: Order) -> bool:
	if site == null or not site.alive or not site.under_construction or site.player_id != worker.player_id:
		return false
	var list: Array = _builders.get_or_add(site.id, [])
	if list.has(worker.id):
		return true
	if list.size() >= max_builders(worker.player_id):
		return false
	list.append(worker.id)
	return true


## One tick of building for a worker on its site: it stays, faces the site and strikes; the
## site's progress is advanced by sim_tick. Calls worker.finish_order() when it is not (or no
## longer) a builder of the site.
func build_tick(worker: Unit, site: Unit, _o: Order, dt: float) -> Vector3:
	if not (_builders.get(site.id, []) as Array).has(worker.id):
		if not join_site(worker, site, _o):
			worker.end_work()
			worker.finish_order()
			return Vector3.ZERO
	if worker.edge_distance(site) > BUILD_REACH + 0.5:
		return worker.chase_point(world.economy.approach_point(site, worker), dt)
	worker.stop_moving()
	worker.face(site.pos, dt)
	if worker.anim_hint != "work" or world.tick_count - worker.work_t0 >= worker.work_ticks:
		worker.begin_work(STROKE_TICKS)
	return Vector3.ZERO


## A builder's BUILD order ended (done, replaced, died): it leaves the site.
func on_builder_left(worker: Unit, o: Order) -> void:
	worker.end_work()
	var sid := int(o.data.get("site", o.target_id))
	if _builders.has(sid):
		(_builders[sid] as Array).erase(worker.id)


func sim_tick(w: World, dt: float) -> void:
	if _builders.is_empty():
		return
	var ids: Array = _builders.keys()
	ids.sort()
	for sid: int in ids:
		var site := w.get_unit(sid)
		if site == null or not site.alive or not site.under_construction:
			_builders.erase(sid)
			continue
		var working := _working_builders(site)
		if working <= 0:
			continue
		var fac := _faction(site.player_id)
		var rate := 1.0 + float(fac.get("extra_builder_rate", 0.0)) * (working - 1)
		var time := maxf(float(site.def.get("cost", {}).get("time", 1.0)), 0.1)
		var step := rate * dt / time
		var before := site.build_progress
		site.build_progress = minf(1.0, before + step)
		var gained := site.build_progress - before
		site.hp = minf(site.max_hp, site.hp + site.max_hp * (1.0 - float(Defs.rule("economy.build_start_hp", 0.1))) * gained)
		if site.build_progress >= 1.0:
			complete_site(site)


## Builders in reach this tick; extra builders (beyond the first) pay
## factions.<id>.extra_builder_lumber_per_s and stop counting while the player cannot pay.
func _working_builders(site: Unit) -> int:
	var list: Array = _builders.get(site.id, [])
	var per_s := float(_faction(site.player_id).get("extra_builder_lumber_per_s", 0.0))
	var n := 0
	for wid: int in list:
		var b := world.get_unit(wid)
		if b == null or not b.alive or b.current == null or b.current.type != Order.Type.BUILD:
			continue
		if b.edge_distance(site) > BUILD_REACH + 0.5:
			continue
		if n >= 1 and per_s > 0.0 and not world.economy.pay_fraction(site.player_id, "lumber", per_s * World.DT):
			continue
		n += 1
	return n


## Finishes a site: function, food (World.adjust_food) and building_completed; its builders go
## idle (or on to their queued orders).
func complete_site(site: Unit) -> void:
	if not site.under_construction:
		return
	site.under_construction = false
	site.build_progress = 1.0
	world.adjust_food(site.player_id, 0, int(site.def.get("food_provided", 0)))
	Events.building_completed.emit(site)
	Events.notification.emit(site.player_id, "building_done",
		Defs.text("notice_building_done") % str(site.def.get("name", site.def_id)))
	_release_builders(site.id)


func _release_builders(sid: int) -> void:
	var list: Array = _builders.get(sid, [])
	_builders.erase(sid)
	for wid: int in list:
		var b := world.get_unit(wid)
		if b != null and b.alive and b.current != null and b.current.type == Order.Type.BUILD:
			b.end_work()
			b.finish_order()


## Cancels a site: refunds rules.economy.build_cancel_refund of its cost and removes it.
func cancel_site(site: Unit) -> void:
	if not site.under_construction:
		return
	world.economy.refund(site.player_id, site.def.get("cost", {}), float(Defs.rule("economy.build_cancel_refund", 0.75)))
	Events.construction_cancelled.emit(site)
	_release_builders(site.id)
	world.remove_unit(site)


# --- repair --------------------------------------------------------------------------------

func can_repair(worker: Unit, target: Unit) -> bool:
	return target != null and target.alive and not target.under_construction \
		and world.is_ally(worker.player_id, target.player_id) \
		and (target.is_structure() or target.is_mechanical) and target.hp < target.max_hp


## One tick of repair (rules §4.8): a full repair takes build time × repair_time_factor for one
## repairer and costs repair_cost_factor of the build cost, pro rata to the HP restored, paid
## through the fractional accumulator. Returns false when it stops (full HP, cannot pay).
func repair_tick(worker: Unit, target: Unit, dt: float) -> bool:
	if not can_repair(worker, target):
		worker.end_work()
		return false
	if not _repairing.has(worker.id):
		_repairing[worker.id] = true
		Events.repair_started.emit(worker, target)
	var cost: Dictionary = target.def.get("cost", {})
	var time := maxf(float(cost.get("time", 30.0)), 1.0) * float(Defs.rule("economy.repair_time_factor", 1.5))
	var frac := minf(dt / time, (target.max_hp - target.hp) / target.max_hp)
	var k := float(Defs.rule("economy.repair_cost_factor", 0.3)) * frac
	var eco := world.economy
	if not eco.pay_fraction(worker.player_id, "gold", float(cost.get("gold", 0)) * k):
		worker.end_work()
		return true     # paused: waits for the money (the order stays)
	if not eco.pay_fraction(worker.player_id, "lumber", float(cost.get("lumber", 0)) * k):
		worker.end_work()
		return true
	target.hp = minf(target.max_hp, target.hp + target.max_hp * frac)
	if worker.anim_hint != "work" or world.tick_count - worker.work_t0 >= worker.work_ticks:
		worker.begin_work(STROKE_TICKS)
	return target.hp < target.max_hp


func on_repair_ended(worker: Unit, _o: Order) -> void:
	worker.end_work()
	_repairing.erase(worker.id)


# --- garrison ------------------------------------------------------------------------------

## Slots of a garrison building (buildings.json `garrison`; `garrison_accepts`,
## `garrison_attack` per occupant, `garrison_eject_hp`).
func garrison_slots(b: Unit) -> int:
	return int(b.def.get("garrison", 0))


func can_enter(u: Unit, b: Unit) -> bool:
	return not b.under_construction and b.garrison.size() < garrison_slots(b) \
		and (b.def.get("garrison_accepts", []) as Array).has(u.def_id)


## Puts `u` inside `b` (hidden, untargetable). Stub: false.
func garrison_enter(_u: Unit, _b: Unit) -> bool:
	return false


## Empties a garrison building. Stub.
func garrison_unload(_b: Unit) -> void:
	pass
