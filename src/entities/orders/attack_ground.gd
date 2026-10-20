extends OrderHandler
## ATTACK_GROUND (owner: combat extensions, agent B; rules §7.9). Units with the
## `can_attack_ground` flag walk into weapon range of o.target_pos and fire at the point until
## ordered otherwise (never completes). Combat.fire_at_point(attacker, point) launches the shell;
## until Combat implements artillery the unit holds position in range.


func can_start(u: Unit, _o: Order) -> bool:
	return u.has_flag("can_attack_ground") and u.can_attack()


func allows_immobile() -> bool:
	return true


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	if u.edge_distance_to_point(o.target_pos) > u.attack_range:
		return u.chase_point(o.target_pos, dt) if u.is_mobile() else Vector3.ZERO
	u.stop_moving()
	if u.face(o.target_pos, dt) and u.weapon_cooldown_ticks() == 0:
		u.world.combat.fire_at_point(u, o.target_pos)
	return Vector3.ZERO
