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
	return [&"spawned"]


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

## A gather order reached its mine / tree. Return true to take the order over (set
## o.data["phase"]; gather_tick then runs every tick). Stub: false (the order completes).
func on_gather_reached(_worker: Unit, _o: Order) -> bool:
	return false


## Drives a gather order once on_gather_reached took it over. Returns the desired velocity.
func gather_tick(worker: Unit, _o: Order, _dt: float) -> Vector3:
	worker.finish_order()
	return Vector3.ZERO


## The gather order ended (finished, replaced, STOP, death): release mine occupancy.
func on_gather_order_ended(_worker: Unit, _o: Order) -> void:
	pass


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
