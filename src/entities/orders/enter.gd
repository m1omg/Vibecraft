extends OrderHandler
## ENTER a garrison building (clans Home Yurt, Roll the Felt; owner: construction agent A).
## Walks to an own finished building with the `garrison` flag and calls
## Construction.garrison_enter(unit, building) on touching it, then completes (an entered unit
## is hidden by World.set_hidden until unloaded).


func can_start(u: Unit, o: Order) -> bool:
	var b := u.world.get_unit(o.target_id)
	return b != null and b.player_id == u.player_id and b.has_flag("garrison") \
		and u.world.construction.can_enter(u, b)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var b := u.world.get_unit(o.target_id)
	if b == null or not b.alive:
		u.finish_order()
		return Vector3.ZERO
	if u.edge_distance(b) <= 0.8:
		u.stop_moving()
		u.world.construction.garrison_enter(u, b)
		u.finish_order()
		return Vector3.ZERO
	return u.chase_move(b, dt)
