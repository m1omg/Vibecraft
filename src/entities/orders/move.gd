extends OrderHandler
## MOVE: follows its path and completes on arrival (or when stalled next to a crowded goal);
## ignores enemies (architecture §5).


func enter(u: Unit, o: Order) -> void:
	u.begin_move(u.order_goal(o))


func tick(u: Unit, _o: Order, dt: float) -> Vector3:
	var d := u.follow_path(dt)
	if u.arrived:
		u.finish_order()
	return d
