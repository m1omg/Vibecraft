extends OrderHandler
## USE_ITEM (owner: items agent D). o.slot = inventory slot, o.target_id / o.target_pos = target
## for targeted items. Approaches ItemSystem.use_range(hero, slot) (< 0 = no target needed),
## then ItemSystem.use(hero, slot, target_unit, target_pos) and completes. Recall channels are
## the items system's (it may keep the order via o.data["phase"] + ItemSystem.use_tick).


func can_start(u: Unit, o: Order) -> bool:
	return u.world.items.can_use(u, o.slot)


func exit(u: Unit, o: Order) -> void:
	u.world.items.cancel_use(u, o)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var items := u.world.items
	if o.data.has("phase"):
		return items.use_tick(u, o, dt)
	var target := u.world.get_unit(o.target_id) if o.target_id != 0 else null
	var r := items.use_range(u, o.slot)
	var dist := 0.0
	if target != null:
		dist = u.edge_distance(target)
	elif o.target_pos != Vector3.ZERO:
		dist = u.edge_distance_to_point(o.target_pos)
	if r < 0.0 or dist <= r:
		u.stop_moving()
		if not items.use(u, o.slot, target, o.target_pos, o):
			u.finish_order()
		return Vector3.ZERO
	return u.chase_move(target, dt) if target != null else u.chase_point(o.target_pos, dt)
