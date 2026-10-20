extends AbilityEffect
## Effect `self_invisibility` (item effect; owner agent D). Hero invisible for `duration` (Smoke
## Pellets: buff_smoke_pellets).


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.apply(ctx.caster, str(ctx.value("buff", "buff_smoke_pellets")), ctx.caster, ctx.values)
	return true
