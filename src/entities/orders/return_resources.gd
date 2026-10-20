extends OrderHandler
## RETURN_RESOURCES / "Return Cargo" (owner: economy agent A). Walks the carried gold or lumber
## to a drop-off (o.target_id, else Economy.find_dropoff) and calls Economy.deposit on touching
## its footprint. Completes afterwards (economy re-issues the previous gather order itself when
## the real trip logic lands). Workers carrying nothing complete at once.


func can_start(u: Unit, _o: Order) -> bool:
	return u.can_gather()


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	if u.carry_gold <= 0 and u.carry_lumber <= 0:
		u.finish_order()
		return Vector3.ZERO
	var eco := u.world.economy
	var b := u.world.get_unit(o.target_id) if o.target_id != 0 else null
	if b == null or not b.alive or b.under_construction or not eco.accepts_cargo(b, u):
		b = eco.find_dropoff(u)
		if b == null:
			u.finish_order()
			return Vector3.ZERO
		o.target_id = b.id
	if u.edge_distance(b) <= float(Defs.rule("economy.dropoff_reach", 0.6)):
		u.stop_moving()
		eco.deposit(u, b)
		u.finish_order()
		return Vector3.ZERO
	return u.chase_move(b, dt)
