extends AbilityEffect
## Effect `levy_release` (ability effect; owner agent C unless noted). Hall button: every Flail Levy
## of the player lays down its flail. Owner: agent A. Stub: no-op.


func cast(ctx: CastContext) -> bool:
	var n := 0
	for u in ctx.world.unit_list.duplicate():
		if u.alive and u.player_id == ctx.caster.player_id and ctx.world.abilities.is_levy(u):
			n += 1 if ctx.world.abilities.revert_levy(u) else 0
	return n > 0
