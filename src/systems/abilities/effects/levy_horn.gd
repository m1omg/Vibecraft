extends AbilityEffect
## Effect `levy_horn` (ability effect; owner agent C unless noted). Hall button: every own Hodman
## within `range` of the hall casts `ability` (Take Up the Flail). Owner: agent A. Stub: no-op.


func cast(ctx: CastContext) -> bool:
	var r := float(ctx.value("range", 22.0))
	var ability := str(ctx.value("ability", "kingdom_take_up_the_flail"))
	for u: Unit in ctx.world.query_radius(ctx.caster.pos, r + ctx.world.max_unit_radius):
		if u.alive and not u.hidden and u.player_id == ctx.caster.player_id and u.abilities.has(ability) \
				and ctx.caster.edge_distance(u) <= r:
			ctx.world.abilities.cast_now(u, ability)
	return true      # the horn sounds (and goes on cooldown) whoever answers it
