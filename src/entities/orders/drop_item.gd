extends OrderHandler
## DROP_ITEM / give (owner: items agent D). o.slot = inventory slot. With o.target_id = an own
## hero: walk within rules.items.give_range and ItemSystem.transfer(from, slot, to); otherwise
## walk to o.target_pos and ItemSystem.drop(hero, slot, pos). Completes afterwards.


func can_start(u: Unit, o: Order) -> bool:
	return o.slot >= 0 and o.slot < u.inventory.size() and u.inventory[o.slot] != null


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var items := u.world.items
	var reach := float(Defs.rule("items.give_range", 1.5))
	if o.target_id != 0:
		var to := u.world.get_unit(o.target_id)
		if to == null or not to.alive:
			u.finish_order()
			return Vector3.ZERO
		if u.edge_distance(to) <= reach:
			u.stop_moving()
			items.transfer(u, o.slot, to)
			u.finish_order()
			return Vector3.ZERO
		return u.chase_move(to, dt)
	if u.edge_distance_to_point(o.target_pos) <= reach:
		u.stop_moving()
		items.drop(u, o.slot, o.target_pos)
		u.finish_order()
		return Vector3.ZERO
	return u.chase_point(o.target_pos, dt)
