extends AbilityEffect
## Effect `mana_over_time_breakable` (item effect; owner agent D). Mana over time that stops on
## damage (Brick-Tea Shavings: buff buff_tea_mana).


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.apply(ctx.caster, str(ctx.value("buff", "buff_tea_mana")), ctx.caster, ctx.values)
	return true
