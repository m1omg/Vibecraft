extends "res://src/entities/orders/attack_move.gd"
## PATROL: an attack-move that ping-pongs forever between where it was given and its point.


func enter(u: Unit, o: Order) -> void:
	u.patrol_from = u.pos
	u.begin_move(o.target_pos)


func _on_arrived(u: Unit, o: Order) -> void:
	var back := u.patrol_from
	u.patrol_from = o.target_pos
	o.target_pos = back
	u.begin_move(back)
