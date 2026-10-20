extends OrderHandler
## STOP never becomes current: Unit.issue_order clears the queue, cancels a wind-up and ends the
## current order. This handler only exists so every Order.Type resolves.


func can_start(_u: Unit, _o: Order) -> bool:
	return true


func allows_immobile() -> bool:
	return true


func tick(u: Unit, _o: Order, _dt: float) -> Vector3:
	u.finish_order()
	return Vector3.ZERO
