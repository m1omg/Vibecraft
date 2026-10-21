extends OrderHandler
## BUILD (owner: construction agent A). o.def_id = building def, o.target_pos = placement point
## (o.target_id = an existing own site to help build). Walks to the site, then:
##   Construction.can_order_build(worker, order) -> bool     on issue (cost checked at order time)
##   Construction.on_builder_arrived(worker, order) -> Unit  new site (pays, spawns it) or null
##   Construction.join_site(worker, site, order) -> bool      extra builders (Hod Chain)
##   Construction.build_tick(worker, site, order, dt) -> Vector3   every tick while building;
##       construction calls worker.finish_order() when the site completes or is cancelled.
## A worker sent to help on an existing site walks to its near side.


func can_start(u: Unit, o: Order) -> bool:
	return u.is_worker and u.world.construction.can_order_build(u, o)


func enter(_u: Unit, o: Order) -> void:
	o.data.erase("site")


func exit(u: Unit, o: Order) -> void:
	u.world.construction.on_builder_left(u, o)


func tick(u: Unit, o: Order, dt: float) -> Vector3:
	var con := u.world.construction
	if o.data.has("site"):
		var site := u.world.get_unit(int(o.data["site"]))
		if site == null or not site.alive or not site.under_construction:
			u.finish_order()
			return Vector3.ZERO
		return con.build_tick(u, site, o, dt)
	if o.target_id != 0:
		var s := u.world.get_unit(o.target_id)
		if s == null or not s.alive or not s.under_construction:
			u.finish_order()
			return Vector3.ZERO
		if u.edge_distance(s) <= 1.0:
			u.stop_moving()
			if con.join_site(u, s, o):
				o.data["site"] = s.id
			else:
				u.finish_order()
			return Vector3.ZERO
		return u.chase_point(u.world.economy.approach_point(s, u), dt)
	if con.builder_in_reach(u, o):
		u.stop_moving()
		var site := con.on_builder_arrived(u, o)
		if site != null:
			o.data["site"] = site.id
		else:
			u.finish_order()
		return Vector3.ZERO
	return u.chase_point(o.target_pos, dt)
