class_name Economy
extends SimSystem
## Economy (owner: agent A; rules.md §4, data: factions.json rules.economy + factions.<id>).
## Stage: economy. Responsibilities:
##   - player resources: affordability, spending, refunds, income with upkeep tax (§4.5)
##   - gathering trips: gold (mine occupancy 1, 1.0 s dwell, 10 per trip) and lumber (per-faction
##     trip size and chop interval, tree retargeting, felling), carrying, drop-offs (§4.1–§4.3)
##   - mines: remaining gold, low warning, depletion/collapse
##   - upkeep tier per player from food_used (recomputed every tick, signal on change)
##   - fractional resource accumulators (repair costs, hod-carrier lumber; rules §2.2)
## Signals (Events): resources_changed(pid), income_received(pid, kind, amount, pos),
##   upkeep_changed(pid, tier), cargo_delivered(worker, building, kind, amount),
##   mine_low(mine), mine_depleted(mine), tree_felled(pos) (Doodads).
## Called by: order handlers gather.gd / return_resources.gd (see their headers), Production /
##   Construction / Tech / Shops / Heroes (can_afford, spend, refund), Creeps (add_income
##   "bounty"), Items (add_income "item_sale", grant_gold), AI (read-only queries).
## Cost dictionaries everywhere: {"gold": int, "lumber": int} (other keys ignored here).

var mine_gold: Dictionary = {}       ## mine unit id -> gold left
var _upkeep_tier: Dictionary = {}    ## pid -> tier index
var _frac: Dictionary = {}           ## pid -> {"gold": float, "lumber": float} accumulators


func hooks() -> Array[StringName]:
	return [&"spawned", &"died", &"removed"]


## A worker that dies inside a mine or at its door frees its place.
func on_unit_died(u: Unit, _killer: Unit) -> void:
	_forget_worker(u)


func on_unit_removed(u: Unit) -> void:
	_forget_worker(u)


func _forget_worker(u: Unit) -> void:
	if not u.is_worker:
		return
	for mid: int in _inside.keys():
		if int(_inside[mid]) == u.id:
			_inside.erase(mid)
			_inside_until.erase(mid)
	for mid: int in _door:
		(_door[mid] as Array).erase(u.id)
	_last_gather.erase(u.id)


func on_unit_spawned(u: Unit) -> void:
	if u.has_flag("gold_mine"):
		mine_gold[u.id] = int(u.def.get("gold", Defs.rule("economy.mine_gold_main", 12000)))
		if world.map == null:
			return
		for i in world.map.gold_mines.size():
			if Grid.flat_dist(world.map.gold_mines[i], u.pos) < 0.75:
				mine_gold[u.id] = world.map.mine_gold(i)
				break


func sim_tick(w: World, _dt: float) -> void:
	if not _inside.is_empty():
		var mids: Array = _inside.keys()
		mids.sort()
		for mid: int in mids:
			if w.tick_count >= int(_inside_until.get(mid, 0)):
				_exit_mine(mid)
	for p: PlayerState in w.players:
		if p.is_neutral():
			continue
		var t := tier_for_food(p.food_used)
		if t != int(_upkeep_tier.get(p.id, 0)):
			_upkeep_tier[p.id] = t
			p.upkeep_tier = t
			Events.upkeep_changed.emit(p.id, t)


# --- resources -----------------------------------------------------------------------------

func can_afford(pid: int, cost: Dictionary) -> bool:
	var p := world.player(pid)
	return p != null and p.gold >= int(cost.get("gold", 0)) and p.lumber >= int(cost.get("lumber", 0))


## Pays `cost` if affordable; false (nothing paid) otherwise.
func spend(pid: int, cost: Dictionary) -> bool:
	if not can_afford(pid, cost):
		return false
	var p := world.player(pid)
	p.gold -= int(cost.get("gold", 0))
	p.lumber -= int(cost.get("lumber", 0))
	Events.resources_changed.emit(pid)
	return true


## Returns floor(cost × factor) of each resource (cancel refunds: rules §4.6). Never taxed.
func refund(pid: int, cost: Dictionary, factor: float = 1.0) -> void:
	var p := world.player(pid)
	if p == null:
		return
	p.gold += floori(int(cost.get("gold", 0)) * factor)
	p.lumber += floori(int(cost.get("lumber", 0)) * factor)
	Events.resources_changed.emit(pid)


## Credits income. Gold from a taxed source (rules.economy.upkeep_taxed_income: "mine",
## "bounty", "item_sale", "ability") is floored by the upkeep factor; lumber never is.
## Returns the amount actually credited (what floating text shows).
func add_income(pid: int, kind: String, amount: int, source: String = "mine", pos: Vector3 = Vector3.INF) -> int:
	var p := world.player(pid)
	if p == null or amount <= 0:
		return 0
	var credited := amount
	if kind == "gold" and (Defs.rule("economy.upkeep_taxed_income", []) as Array).has(source):
		credited = floori(amount * upkeep_factor(pid))
	if kind == "gold":
		p.gold += credited
	elif kind == "lumber":
		p.lumber += credited
	Events.income_received.emit(pid, kind, credited, pos)
	Events.resources_changed.emit(pid)
	return credited


## Adds a fractional amount to a player's accumulator and pays whole units from it (repair costs,
## hod-carrier lumber). Returns false when the next whole unit cannot be paid (work pauses).
func pay_fraction(pid: int, kind: String, amount: float) -> bool:
	var acc: Dictionary = _frac.get_or_add(pid, {"gold": 0.0, "lumber": 0.0})
	acc[kind] = float(acc[kind]) + amount
	var whole := floori(float(acc[kind]))
	if whole <= 0:
		return true
	var cost := {kind: whole}
	if not spend(pid, cost):
		acc[kind] = float(acc[kind]) - amount
		return false
	acc[kind] = float(acc[kind]) - whole
	return true


static func tier_for_food(food_used: int) -> int:
	var tier := 0
	for i in Defs.upkeep.size():
		if food_used >= int((Defs.upkeep[i] as Dictionary).get("food", 0)):
			tier = i
	return tier


func upkeep_tier(pid: int) -> int:
	var p := world.player(pid)
	return tier_for_food(p.food_used) if p != null else 0


func upkeep_factor(pid: int) -> float:
	var t := upkeep_tier(pid)
	return float((Defs.upkeep[t] as Dictionary).get("gold_factor", 1.0)) if t < Defs.upkeep.size() else 1.0


# --- gathering (contract with orders/gather.gd and orders/return_resources.gd) ------------
# A gather order walks to its mine or tree (the handler) and then belongs to the economy, which
# drives it through o.data["phase"]:
#   gold:   "queue" (at the mine door, arrival order) -> "inside" (hidden, mine_dwell) ->
#           "to_dropoff" -> deposit -> "back" -> "queue" ...
#   lumber: "chop" (1 lumber per chop_interval until lumber_per_trip) -> "to_dropoff" -> deposit
#           -> "back" (to the tree, or the nearest living one within tree_retarget_radius) ...
# The worker's last gather target is remembered, so Return Cargo goes back to work afterwards.

## A worker chops when its edge is this close to the tree's centre (the trunk fills a 1 m cell).
const TREE_REACH := 0.8

## Gold Seam occupancy: mine id -> worker id inside (absent = free); the economy's tick brings
## the worker out (hidden units do not tick themselves).
var _inside: Dictionary = {}
var _inside_until: Dictionary = {}     ## mine id -> tick the worker inside comes out
## mine id -> Array[int] of worker ids waiting at the door, in arrival order.
var _door: Dictionary = {}
## worker id -> {"mine": id} or {"tree": index} (Return Cargo resumes it).
var _last_gather: Dictionary = {}
## mine ids that already raised their low-gold warning.
var _warned_low: Dictionary = {}


func _mine_dwell_ticks() -> int:
	return maxi(1, roundi(float(Defs.rule("economy.mine_dwell", 1.0)) * World.TICK_RATE))


func _faction_of(u: Unit) -> Dictionary:
	var p := world.player(u.player_id)
	return Defs.faction(p.faction) if p != null and p.faction != "" else {}


func lumber_per_trip(worker: Unit) -> int:
	return int(_faction_of(worker).get("lumber_per_trip", 10))


func chop_ticks(worker: Unit) -> int:
	return maxi(1, roundi(float(_faction_of(worker).get("chop_interval", 0.8)) * World.TICK_RATE))


## A gather order reached its mine / tree: the economy drives it from now on (o.data["phase"]).
## Returns false when there is nothing to gather (the order completes).
func on_gather_reached(worker: Unit, o: Order) -> bool:
	var discard := bool(Defs.rule("economy.switch_resource_discards_load", true))
	if o.data.has("tree"):
		var i := int(o.data["tree"])
		if not world.doodads.tree_alive(i):
			return false
		if worker.carry_gold > 0 and discard:
			worker.carry_gold = 0       # switching resources drops the load (rules §4.3)
		_last_gather[worker.id] = {"tree": i}
		if worker.carry_lumber >= lumber_per_trip(worker):
			o.data["phase"] = "to_dropoff"
			return true
		_begin_chop(worker, o)
		return true
	var mine := world.get_unit(o.target_id)
	if mine == null or not mine.alive or not mine.has_flag("gold_mine") or gold_left(mine) <= 0:
		return false
	if worker.carry_lumber > 0 and discard:
		worker.carry_lumber = 0
	_last_gather[worker.id] = {"mine": mine.id}
	if worker.carry_gold >= int(Defs.rule("economy.gold_per_trip", 10)):
		o.data["phase"] = "to_dropoff"
		return true
	_join_door(worker, mine, o)
	return true


## Drives a gather order once on_gather_reached took it over. Returns the desired velocity.
func gather_tick(worker: Unit, o: Order, dt: float) -> Vector3:
	worker.harvesting = true
	match str(o.data.get("phase", "")):
		"queue":
			return _queue_tick(worker, o)
		"inside":
			return _inside_tick(worker, o)
		"chop":
			return _chop_tick(worker, o, dt)
		"to_dropoff":
			return _dropoff_tick(worker, o, dt)
		"back":
			return _back_tick(worker, o, dt)
	worker.finish_order()
	return Vector3.ZERO


## The gather order ended (finished, replaced, STOP, death): a worker inside its mine comes out
## (empty-handed), its place at the door is given up, and its work animation stops.
func on_gather_order_ended(worker: Unit, o: Order) -> void:
	worker.end_work()
	worker.harvesting = false
	var mid := int(o.data.get("mine", o.target_id))
	_leave_door(worker, mid)
	if int(_inside.get(mid, 0)) == worker.id:
		_inside.erase(mid)
		_inside_until.erase(mid)
		var mine := world.get_unit(mid)
		if worker.hidden:
			world.set_hidden(worker, false)
			if mine != null:
				worker.teleport(_door_point(mine, worker, worker.pos))
	o.data.erase("phase")


# --- gold -------------------------------------------------------------------------------------

func _join_door(worker: Unit, mine: Unit, o: Order) -> void:
	o.data["mine"] = mine.id
	o.data["phase"] = "queue"
	var q: Array = _door.get_or_add(mine.id, [])
	if not q.has(worker.id):
		q.append(worker.id)
	worker.stop_moving()


func _leave_door(worker: Unit, mine_id: int) -> void:
	var q: Array = _door.get(mine_id, [])
	q.erase(worker.id)


## Waiting at the door: the first in line enters as soon as the mine is free.
func _queue_tick(worker: Unit, o: Order) -> Vector3:
	var mine := world.get_unit(int(o.data.get("mine", 0)))
	if mine == null or not mine.alive or gold_left(mine) <= 0:
		worker.finish_order()
		return Vector3.ZERO
	var q: Array = _door.get(mine.id, [])
	if _inside.has(mine.id) or q.is_empty() or int(q[0]) != worker.id:
		return Vector3.ZERO
	q.pop_front()
	_inside[mine.id] = worker.id
	_inside_until[mine.id] = world.tick_count + _mine_dwell_ticks()
	o.data["phase"] = "inside"
	world.set_hidden(worker, true)
	return Vector3.ZERO


## Hidden units do not tick: the economy's tick brings miners out (_exit_mine).
func _inside_tick(_worker: Unit, _o: Order) -> Vector3:
	return Vector3.ZERO


## After mine_dwell the worker inside comes out of the door towards its drop-off with up to 10 gold.
func _exit_mine(mid: int) -> void:
	var worker := world.get_unit(int(_inside[mid]))
	_inside.erase(mid)
	_inside_until.erase(mid)
	if worker == null or not worker.alive:
		return
	var o := worker.current
	var mine := world.get_unit(mid)
	var taken := 0
	if mine != null and mine.alive:
		taken = mini(int(Defs.rule("economy.gold_per_trip", 10)), gold_left(mine))
		mine_gold[mine.id] = gold_left(mine) - taken
	worker.carry_gold = taken
	world.set_hidden(worker, false)
	var drop := find_dropoff(worker) if taken > 0 else null
	if mine != null:
		worker.teleport(_door_point(mine, worker, drop.pos if drop != null else worker.pos))
	if mine != null:
		_after_mining(mine)
	if o == null or o.type != Order.Type.GATHER:
		return
	if taken <= 0:
		worker.finish_order()
		return
	o.data["phase"] = "to_dropoff"


## Low warning (once per mine) and depletion: the seam collapses, its footprint opens, waiting
## workers go idle.
func _after_mining(mine: Unit) -> void:
	var left := gold_left(mine)
	var low := int(Defs.rule("economy.mine_low_warning", 1500))
	if left <= low and left > 0 and not _warned_low.has(mine.id):
		_warned_low[mine.id] = true
		Events.mine_low.emit(mine)
		for pid in _miners_of(mine):
			Events.notification.emit(pid, "mine_low", Defs.text("notice_mine_low"))
	if left <= 0:
		_deplete(mine)


func _deplete(mine: Unit) -> void:
	if not mine.is_resource:
		return
	mine.is_resource = false
	if mine.footprint.size != Vector2i.ZERO:
		world.pathing.set_footprint_rect(mine.footprint, false)
	Events.mine_depleted.emit(mine)
	for pid in _miners_of(mine):
		Events.notification.emit(pid, "mine_depleted", Defs.text("notice_mine_depleted"))
	_door.erase(mine.id)


func _miners_of(mine: Unit) -> Array[int]:
	var out: Array[int] = []
	for wid: int in _last_gather:
		if int((_last_gather[wid] as Dictionary).get("mine", 0)) == mine.id:
			var w := world.get_unit(wid)
			if w != null and not out.has(w.player_id):
				out.append(w.player_id)
	return out


# --- lumber -----------------------------------------------------------------------------------

func _begin_chop(worker: Unit, o: Order) -> void:
	o.data["phase"] = "chop"
	worker.stop_moving()
	worker.begin_work(chop_ticks(worker))


func _chop_tick(worker: Unit, o: Order, dt: float) -> Vector3:
	var i := int(o.data.get("tree", -1))
	if not world.doodads.tree_alive(i):
		var next := retarget_tree(worker, o)
		worker.end_work()
		if next < 0:
			worker.finish_order()
			return Vector3.ZERO
		o.data["tree"] = next
		_last_gather[worker.id] = {"tree": next}
		o.data["phase"] = "back"
		return Vector3.ZERO
	worker.face(world.doodads.tree_pos(i), dt)
	if worker.anim_hint != "work":
		worker.begin_work(chop_ticks(worker))
	if world.tick_count - worker.work_t0 < worker.work_ticks:
		return Vector3.ZERO
	worker.carry_lumber += world.doodads.harvest(i, 1)
	if worker.carry_lumber >= lumber_per_trip(worker):
		worker.end_work()
		o.data["phase"] = "to_dropoff"
	else:
		worker.begin_work(chop_ticks(worker))
	return Vector3.ZERO


# --- trips ------------------------------------------------------------------------------------

func _dropoff_tick(worker: Unit, o: Order, dt: float) -> Vector3:
	var b := world.get_unit(int(o.data.get("dropoff", 0)))
	if b == null or not accepts_cargo(b, worker):
		b = find_dropoff(worker)
		if b == null:
			worker.finish_order()      # nowhere to deliver: the worker waits with its cargo
			return Vector3.ZERO
		o.data["dropoff"] = b.id
	if worker.edge_distance(b) <= float(Defs.rule("economy.dropoff_reach", 0.6)):
		worker.stop_moving()
		deposit(worker, b)
		o.data.erase("dropoff")
		o.data["phase"] = "back"
		return Vector3.ZERO
	return worker.chase_point(approach_point(b, worker), dt)


## Back to the mine (or the tree) after a delivery.
func _back_tick(worker: Unit, o: Order, dt: float) -> Vector3:
	var reach := float(Defs.rule("economy.gather_reach", Unit.GATHER_REACH))
	if o.data.has("tree"):
		var i := int(o.data["tree"])
		if not world.doodads.tree_alive(i):
			i = retarget_tree(worker, o)
			if i < 0:
				worker.finish_order()
				return Vector3.ZERO
			o.data["tree"] = i
			_last_gather[worker.id] = {"tree": i}
		var tp := world.doodads.tree_pos(i)
		if worker.edge_distance_to_point(tp) <= TREE_REACH:
			_begin_chop(worker, o)
			return Vector3.ZERO
		return worker.chase_point(tp, dt)
	var mine := world.get_unit(int(o.data.get("mine", o.target_id)))
	if mine == null or not mine.alive or not mine.is_resource or gold_left(mine) <= 0:
		worker.finish_order()
		return Vector3.ZERO
	if worker.edge_distance(mine) <= reach:
		_join_door(worker, mine, o)
		return Vector3.ZERO
	return worker.chase_point(approach_point(mine, worker), dt)


## The point just outside building `b`'s footprint nearest `worker` (so a walk to a building
## ends on the side it came from, not wherever the footprint's centre snaps to).
func approach_point(b: Unit, worker: Unit) -> Vector3:
	return approach_from(b, worker.pos, worker.radius)


## approach_point for a position and a body radius: the footprint point nearest `from`, pushed
## out towards `from` by the body radius + 0.05 m (corners included), so the worker stops touching
## the footprint (rules §4.1: delivery on touching; the walk sets the mine cycle).
func approach_from(b: Unit, from: Vector3, body_radius: float) -> Vector3:
	if b.footprint.size == Vector2i.ZERO:
		return b.pos
	var r := b.footprint
	var pad := body_radius + 0.05
	var x0 := r.position.x * Grid.CELL
	var z0 := r.position.y * Grid.CELL
	var x1 := r.end.x * Grid.CELL
	var z1 := r.end.y * Grid.CELL
	var near := Vector3(clampf(from.x, x0, x1), 0.0, clampf(from.z, z0, z1))
	var out := Vector3(from.x - near.x, 0.0, from.z - near.z)
	var p: Vector3
	if out.length_squared() > 1e-6:
		p = near + out.normalized() * pad
	else:
		# inside the footprint: out through the nearest side
		var d := [from.x - x0, x1 - from.x, from.z - z0, z1 - from.z]
		match d.find(d.min()):
			0: p = Vector3(x0 - pad, 0.0, from.z)
			1: p = Vector3(x1 + pad, 0.0, from.z)
			2: p = Vector3(from.x, 0.0, z0 - pad)
			_: p = Vector3(from.x, 0.0, z1 + pad)
	p.y = world.map.height_at(p.x, p.z)
	return p


## Where a worker leaving mine `mine` appears: the door side facing `toward`, on a walkable cell.
func _door_point(mine: Unit, worker: Unit, toward: Vector3) -> Vector3:
	var p := approach_from(mine, toward, worker.radius)
	var c := world.pathing.nearest_walkable(Grid.world_to_cell(p))
	var out := Grid.cell_to_world(c)
	out.y = world.map.height_at(out.x, out.z)
	return out


## Return Cargo delivered: the worker goes back to what it gathered before (when nothing else is
## queued). Called by orders/return_resources.gd after a deposit.
func resume_gather(worker: Unit) -> void:
	if not worker.orders.is_empty() or not _last_gather.has(worker.id):
		return
	var last: Dictionary = _last_gather[worker.id]
	var cmd := {"type": "gather", "player": worker.player_id, "units": [worker.id]}
	if last.has("tree"):
		var i := int(last["tree"])
		if not world.doodads.tree_alive(i):
			return
		cmd["pos"] = world.doodads.tree_pos(i)
		cmd["data"] = {"tree": i}
	else:
		var mine := world.get_unit(int(last["mine"]))
		if mine == null or not mine.alive or not mine.is_resource:
			return
		cmd["target"] = mine.id
	world.issue(cmd)


## The last gather target of a worker ({"mine": id} / {"tree": index}, {} when none).
func last_gather(worker: Unit) -> Dictionary:
	return _last_gather.get(worker.id, {})


## Gold Seam occupancy (tests, juice): the worker id inside, 0 when free.
func miner_inside(mine: Unit) -> int:
	return int(_inside.get(mine.id, 0))


func door_queue(mine: Unit) -> Array:
	return _door.get(mine.id, [])


## Nearest living tree within rules.economy.tree_retarget_radius of the order's last tree
## (ties by tree index), or -1.
func retarget_tree(worker: Unit, o: Order) -> int:
	var from := worker.pos
	if o.data.has("tree"):
		from = world.doodads.tree_pos(int(o.data["tree"]))
	return world.doodads.nearest_tree(from, float(Defs.rule("economy.tree_retarget_radius", 8.0)))


## "gold", "lumber" or "" for what the worker carries.
static func carry_kind(worker: Unit) -> String:
	if worker.carry_gold > 0:
		return "gold"
	if worker.carry_lumber > 0:
		return "lumber"
	return ""


## True when `b` is a finished own drop-off for what `worker` carries (halls take both; lumber
## buildings take lumber).
func accepts_cargo(b: Unit, worker: Unit) -> bool:
	if b == null or not b.alive or b.under_construction or b.player_id != worker.player_id:
		return false
	var kind := carry_kind(worker)
	return kind != "" and b.has_flag("dropoff_" + kind)


## Nearest finished own drop-off for the worker's cargo (by straight distance; ties by id).
func find_dropoff(worker: Unit) -> Unit:
	var best: Unit = null
	var best_d := INF
	for b in world.unit_list:
		if not accepts_cargo(b, worker):
			continue
		var d := worker.edge_distance(b)
		if d < best_d or (d == best_d and best != null and b.id < best.id):
			best_d = d
			best = b
	return best


## Delivers the worker's cargo into its owner's stock (gold taxed as "mine", lumber untaxed).
func deposit(worker: Unit, building: Unit) -> void:
	if worker.carry_gold > 0:
		var g := worker.carry_gold
		worker.carry_gold = 0
		add_income(worker.player_id, "gold", g, "mine", building.pos)
		Events.cargo_delivered.emit(worker, building, "gold", g)
	if worker.carry_lumber > 0:
		var l := worker.carry_lumber
		worker.carry_lumber = 0
		add_income(worker.player_id, "lumber", l, "lumber", building.pos)
		Events.cargo_delivered.emit(worker, building, "lumber", l)


func gold_left(mine: Unit) -> int:
	return int(mine_gold.get(mine.id, 0))
