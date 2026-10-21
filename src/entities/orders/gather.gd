extends OrderHandler
## GATHER (owner: economy agent A). Walks to the resource (a gold mine unit, or a tree when
## o.data["tree"] holds a tree index) and hands the trip over to the economy:
##   Economy.on_gather_reached(worker, order) -> bool   true = economy drives the order from now
##       on (it sets o.data["phase"]); false = the order completes.
##   Economy.gather_tick(worker, order, dt) -> Vector3   every tick while o.data has "phase"
##       (mine dwell, chopping, walking to the drop-off and back are economy's business).
## The legacy World.gather_handler hook (tests) still wins when it is set. A mine is approached
## on its near side (Economy.approach_point).


func can_start(u: Unit, o: Order) -> bool:
	if not u.can_gather():
		return false
	if o.data.has("tree"):
		return u.world.doodads.tree_alive(int(o.data["tree"]))
	var t := u.world.get_unit(o.target_id)
	return t != null and t.is_resource


func enter(_u: Unit, o: Order) -> void:
	o.data.erase("phase")


func exit(u: Unit, o: Order) -> void:
	u.world.economy.on_gather_order_ended(u, o)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var eco := u.world.economy
	if o.data.has("phase"):
		return eco.gather_tick(u, o, dt)
	var reach := float(Defs.rule("economy.gather_reach", Unit.GATHER_REACH))
	if o.data.has("tree"):
		var i := int(o.data["tree"])
		if not u.world.doodads.tree_alive(i):
			var next := eco.retarget_tree(u, o)
			if next < 0:
				u.finish_order()
				return Vector3.ZERO
			i = next
			o.data["tree"] = i
		var tp := u.world.doodads.tree_pos(i)
		if u.edge_distance_to_point(tp) <= Economy.TREE_REACH:
			u.stop_moving()
			if not eco.on_gather_reached(u, o):
				u.finish_order()
			return Vector3.ZERO
		return u.chase_point(tp, dt)
	var t := u.world.get_unit(o.target_id)
	if t == null or not t.alive:
		u.finish_order()
		return Vector3.ZERO
	if u.edge_distance(t) <= reach:
		u.stop_moving()
		if u.world.gather_handler.is_valid():
			u.world.on_gather_reached(u, t)
			u.finish_order()
		elif not eco.on_gather_reached(u, o):
			u.finish_order()
		return Vector3.ZERO
	return u.chase_point(eco.approach_point(t, u), dt)
