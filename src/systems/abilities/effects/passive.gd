extends AbilityEffect
## Effect `passive` (ability effect; owner agent C unless noted). Learned / innate passive: gives
## the caster its permanent passive `buff` (Clean Cut, Braced Shot, Shove, Stuffed, Settle, Hardy
## ...). Trigger logic (crits, every-Nth-hit, stillness) lives in the buffs / combat code that reads
## the buff.


func cast(ctx: CastContext) -> bool:
	var b := str(ctx.value("buff", ""))
	if b != "":
		ctx.world.buffs.apply(ctx.caster, b, ctx.caster, ctx.values, -1.0)
	return true
