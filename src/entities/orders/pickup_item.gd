extends OrderHandler
## PICKUP_ITEM (owner: items agent D). Chases a ground item entity (Unit.is_item) to within
## rules.items.pickup_range, then ItemSystem.pickup(unit, item_entity) and completes.


func can_start(u: Unit, o: Order) -> bool:
	var t := u.world.get_unit(o.target_id)
	return t != null and t.is_item and u.world.items.can_pickup(u, t)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var t := u.world.get_unit(o.target_id)
	if t == null or not t.alive or not t.is_item:
		u.finish_order()
		return Vector3.ZERO
	if u.edge_distance(t) <= float(Defs.rule("items.pickup_range", 1.0)):
		u.stop_moving()
		u.world.items.pickup(u, t)
		u.finish_order()
		return Vector3.ZERO
	return u.chase_move(t, dt)
