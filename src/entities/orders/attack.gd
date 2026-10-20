extends OrderHandler
## ATTACK on a unit: chases it until it dies (no leash). A unit without a weapon just follows.
## (An ATTACK without a target is turned into ATTACK_MOVE by Unit.issue_order.)


func allows_immobile() -> bool:
	return true


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var t := u.world.get_unit(o.target_id)
	if t == null or not t.alive or t == u:
		u.finish_order()
		return Vector3.ZERO
	if not u.can_attack():
		return u.chase_move(t, dt) if u.is_mobile() else Vector3.ZERO
	return u.fight(t, dt, u.is_mobile())
