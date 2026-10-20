extends AbilityEffect
## Effect `toggle_buff` (ability effect; owner agent C unless noted). Toggle stance: adds or removes
## `buff` (Plant Pavise; cast_point is the switch time).


func cast(ctx: CastContext) -> bool:
	var b := str(ctx.value("buff", ""))
	if ctx.world.buffs.has_buff(ctx.caster, b):
		ctx.world.buffs.remove(ctx.caster, b)
	else:
		ctx.world.buffs.apply(ctx.caster, b, ctx.caster, ctx.values, -1.0)
	return true
