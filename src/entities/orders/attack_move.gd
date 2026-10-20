extends OrderHandler
## ATTACK_MOVE: follows its path, engages anything acquired on the way and re-paths to its goal
## after each fight. PATROL (patrol.gd) extends it and ping-pongs instead of completing.


func enter(u: Unit, o: Order) -> void:
	u.begin_move(u.order_goal(o))


func accepts_retaliation(_u: Unit, _o: Order) -> bool:
	return true


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var t := u.engaged()
	if t != null and u.is_lost(t):
		u.give_up(t)
		t = null
	if t == null:
		t = u.scan(u.acquire_range)
		if t != null:
			u.engage(t)
			u.resume_path = true
	if t != null:
		return u.fight(t, dt, true)
	if u.resume_path:
		u.resume_path = false
		u.begin_move(o.target_pos)
	var d := u.follow_path(dt)
	if u.arrived:
		_on_arrived(u, o)
	return d


func _on_arrived(u: Unit, _o: Order) -> void:
	u.finish_order()
