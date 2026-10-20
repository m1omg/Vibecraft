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


# --- placement -----------------------------------------------------------------------------

## Placement check for `def_id` centred at `pos` (snapped to the footprint grid).
## Returns {ok: bool, reason: String (error key), rect: Rect2i (cells), pos: Vector3 (snapped)}.
func can_place(pid: int, def_id: String, pos: Vector3) -> Dictionary:
	var d := Defs.unit(def_id)
	var out := {"ok": false, "reason": "", "rect": Rect2i(), "pos": pos}
	if d.is_empty() or d.get("kind") != "building" or d.get("upgrade_only", false):
		out["reason"] = "cannot_build"
		return out
	var fp: Array = d["footprint"]
	var size := Vector2i(int(fp[0]), int(fp[1]))
	var spot := Grid.snap_to_footprint(pos, size)
	var rect := Grid.footprint_rect(spot, size)
	out["rect"] = rect
	out["pos"] = spot
	var m := world.map
	if rect.position.x < 0 or rect.position.y < 0 or rect.end.x > m.size_cells().x or rect.end.y > m.size_cells().y:
		out["reason"] = "out_of_bounds"
		return out
	var t0 := Grid.cell_to_tile(rect.position)
	var t1 := Grid.cell_to_tile(rect.end - Vector2i.ONE)
	var lvl := m.level_at_tile(t0.x, t0.y)
	for ty in range(t0.y, t1.y + 1):
		for tx in range(t0.x, t1.x + 1):
			var i := m.idx(tx, ty)
			if m.ramp[i] > 0 or m.water[i] == 1 or m.is_boundary_tile(tx, ty) or m.cliff[i] != lvl:
				out["reason"] = "not_flat"
				return out
	if not world.pathing.is_rect_free(rect):
		out["reason"] = "blocked"
		return out
	if world.fog != null and not world.fog.is_explored(pid, spot):
		out["reason"] = "unexplored"
		return out
	if (d.get("flags", []) as Array).has("town_hall") and _too_close_to_mine(rect):
		out["reason"] = "too_close_to_mine"
		return out
	out["ok"] = true
	return out


func _too_close_to_mine(rect: Rect2i) -> bool:
	var gap := float(Defs.rule("economy.hall_mine_gap", 6.0))
	for u in world.unit_list:
		if u.has_flag("gold_mine") and u.footprint.size != Vector2i.ZERO:
			var dx := maxi(0, maxi(rect.position.x - u.footprint.end.x, u.footprint.position.x - rect.end.x))
			var dz := maxi(0, maxi(rect.position.y - u.footprint.end.y, u.footprint.position.y - rect.end.y))
			if Vector2(dx, dz).length() * Grid.CELL < gap - 1e-3:
				return true
	return false


## BUILD order validation on issue (cost checked at order time, rules §4.6).
func can_order_build(worker: Unit, o: Order) -> bool:
	if o.target_id != 0:
		var site := world.get_unit(o.target_id)
		return site != null and site.under_construction and site.player_id == worker.player_id
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

## The builder arrived: re-check, pay (rules.economy.build_pay "on_start"), push own units out,
## start the site. Returns the site or null (the order then completes). Stub: null.
func on_builder_arrived(_worker: Unit, _o: Order) -> Unit:
	return null


## Spawns an under-construction site (10 % HP, no food or function until complete).
func start_site(pid: int, def_id: String, pos: Vector3, facing: float = 0.0) -> Unit:
	var site := world.spawn_unit(def_id, pid, pos, facing, {"under_construction": true,
		"hp_fraction": float(Defs.rule("economy.build_start_hp", 0.1))})
	if site != null:
		Events.construction_started.emit(site, null)
	return site


## An extra builder joins a site (kingdom Hod Chain). Stub: false.
func join_site(_worker: Unit, _site: Unit, _o: Order) -> bool:
	return false


## One tick of building; the worker stays put. Calls worker.finish_order() when done. Stub.
func build_tick(worker: Unit, _site: Unit, _o: Order, _dt: float) -> Vector3:
	worker.finish_order()
	return Vector3.ZERO


## A builder's BUILD order ended (done, replaced, died).
func on_builder_left(_worker: Unit, _o: Order) -> void:
	pass


## Finishes a site: function, food (World.adjust_food) and building_completed.
func complete_site(site: Unit) -> void:
	if not site.under_construction:
		return
	site.under_construction = false
	site.build_progress = 1.0
	world.adjust_food(site.player_id, 0, int(site.def.get("food_provided", 0)))
	Events.building_completed.emit(site)


## Cancels a site: refunds rules.economy.build_cancel_refund of its cost and removes it.
func cancel_site(site: Unit) -> void:
	if not site.under_construction:
		return
	world.economy.refund(site.player_id, site.def.get("cost", {}), float(Defs.rule("economy.build_cancel_refund", 0.75)))
	Events.construction_cancelled.emit(site)
	world.remove_unit(site)


# --- repair --------------------------------------------------------------------------------

func can_repair(worker: Unit, target: Unit) -> bool:
	return target != null and target.alive and not target.under_construction \
		and world.is_ally(worker.player_id, target.player_id) \
		and (target.is_structure() or target.is_mechanical) and target.hp < target.max_hp


## One tick of repair (rules §4.8). Returns false when repair stops. Stub: false.
func repair_tick(_worker: Unit, _target: Unit, _dt: float) -> bool:
	return false


func on_repair_ended(_worker: Unit, _o: Order) -> void:
	pass


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
