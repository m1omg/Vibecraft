extends OrderHandler
## No current order: auto-acquire within `acquire_range`, fight, leash back to the guard
## position (creeps: their camp). Structures and immobile summons with a weapon (towers, the
## Grand Bombard) acquire and shoot in place. Called with o == null.


func tick(u: Unit, _o: Order, dt: float) -> Vector3:
	if not u.is_mobile():
		return _stationary(u, dt)
	if u.returning:
		var d := u.follow_path(dt)
		if u.arrived:
			u.returning = false
			u.stop_moving()
			u.guard_pos = u.pos
		return d
	var t := u.engaged()
	if t == null:
		t = u.scan(u.acquire_range)
		if t == null:
			u.settle()
			return Vector3.ZERO
		u.engage(t)
	if Grid.flat_dist(u.pos, u.guard_pos) > u.leash_range or u.is_lost(t):
		u.give_up(t)
		u.return_to(u.guard_pos)
		return Vector3.ZERO
	return u.fight(t, dt, true)


## Towers: keep the current target while it stays in acquire range, else scan.
func _stationary(u: Unit, dt: float) -> Vector3:
	var t := u.engaged()
	if t != null and u.edge_distance(t) > u.acquire_range:
		u.engage_id = 0
		t = null
	if t == null:
		t = u.scan(u.acquire_range)
		if t == null:
			return Vector3.ZERO
		u.engage_id = t.id
	return u.fight(t, dt, false)
