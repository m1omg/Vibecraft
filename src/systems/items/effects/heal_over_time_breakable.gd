extends AbilityEffect
## Effect `heal_over_time_breakable` (item effect; owner agent D). Heal over time that stops on
## damage (Salt Tea: buff buff_tea_heal, amount, duration).


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.apply(ctx.caster, str(ctx.value("buff", "buff_tea_heal")), ctx.caster, ctx.values)
	return true
