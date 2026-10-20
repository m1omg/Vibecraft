extends OrderHandler
## CAST (owner: abilities agent C). o.ability = ability id, o.target_id / o.target_pos = target.
## Approaches to the ability's range (AbilitySystem.cast_range; < 0 = anywhere), faces the
## target, then hands over: AbilitySystem.begin_cast(caster, order) -> bool (true = the system
## runs cast point / channel / backswing via AbilitySystem.cast_tick while o.data has "phase";
## false = done). exit() lets the system cancel a wind-up or channel (rules §6.5).


func can_start(u: Unit, o: Order) -> bool:
	return u.world.abilities.can_order_cast(u, o)


func enter(_u: Unit, o: Order) -> void:
	o.data.erase("phase")


func exit(u: Unit, o: Order) -> void:
	u.world.abilities.cancel_cast(u, o)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var ab := u.world.abilities
	if o.data.has("phase"):
		return ab.cast_tick(u, o, dt)
	var target := u.world.get_unit(o.target_id) if o.target_id != 0 else null
	if o.target_id != 0 and (target == null or not target.alive):
		u.finish_order()
		return Vector3.ZERO
	var r := ab.cast_range(u, o.ability)
	var dist := u.edge_distance(target) if target != null else u.edge_distance_to_point(o.target_pos)
	if r < 0.0 or dist <= r or not u.is_mobile():
		u.stop_moving()
		var aim := target.pos if target != null else o.target_pos
		if (target != null or o.target_pos != Vector3.ZERO) and not u.face(aim, dt):
			return Vector3.ZERO
		if not ab.begin_cast(u, o):
			u.finish_order()
		return Vector3.ZERO
	return u.chase_move(target, dt) if target != null else u.chase_point(o.target_pos, dt)
