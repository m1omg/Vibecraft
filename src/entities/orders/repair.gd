extends OrderHandler
## REPAIR (owner: construction agent A; rules §4.8). Chases an own/allied damaged structure or
## mechanical unit, then calls Construction.repair_tick(worker, target, dt) every tick in reach;
## it returns false when repair cannot continue (full HP, no money, invalid). Completes then.


func can_start(u: Unit, o: Order) -> bool:
	var t := u.world.get_unit(o.target_id)
	return t != null and u.repair_ability() != "" and u.world.construction.can_repair(u, t)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var t := u.world.get_unit(o.target_id)
	if t == null or not t.alive or t.hp >= t.max_hp:
		u.finish_order()
		return Vector3.ZERO
	if u.edge_distance(t) <= 0.8:
		u.stop_moving()
		u.face(t.pos, dt)
		if not u.world.construction.repair_tick(u, t, dt):
			u.finish_order()
		return Vector3.ZERO
	return u.chase_move(t, dt)


func exit(u: Unit, o: Order) -> void:
	u.world.construction.on_repair_ended(u, o)
