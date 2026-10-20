extends OrderHandler
## HOLD: never completes, cannot be pushed, attacks only enemies already in weapon range and
## never moves.


func enter(u: Unit, _o: Order) -> void:
	u.holding = true


func allows_immobile() -> bool:
	return true


func tick(u: Unit, _o: Order, dt: float) -> Vector3:
	var t := u.engaged()
	if t != null and u.edge_distance(t) > u.attack_range:
		u.engage_id = 0
		t = null
	if t == null:
		t = u.scan(u.attack_range)
		if t == null:
			return Vector3.ZERO
		u.engage_id = t.id
	return u.fight(t, dt, false)
