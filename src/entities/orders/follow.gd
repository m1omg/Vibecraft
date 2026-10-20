extends OrderHandler
## FOLLOW: keeps within Unit.FOLLOW_DIST of a mobile ally. A follower that is hit fights back
## (Unit._on_attacked), then resumes following.


func accepts_retaliation(_u: Unit, _o: Order) -> bool:
	return true


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var t := u.world.get_unit(o.target_id)
	if t == null or not t.alive:
		u.finish_order()
		return Vector3.ZERO
	var e := u.engaged()
	if e != null:
		if not u.is_lost(e):
			return u.fight(e, dt, true)
		u.give_up(e)
	if u.edge_distance(t) <= Unit.FOLLOW_DIST:
		u.stop_moving()
		return Vector3.ZERO
	return u.chase_move(t, dt)
