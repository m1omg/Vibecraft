extends AbilityEffect
## Effect `taunt_area` (ability effect; owner agent C unless noted). Taunts enemy non-heroes in
## `area` for `duration` (taunt_buff) and gives the caster self_buff (armor) for self_duration.
## Brace the Wheel.


func cast(ctx: CastContext) -> bool:
	for u in units_in_area(ctx, ctx.caster.pos, float(ctx.value("area", 4.0))):
		ctx.world.buffs.apply(u, str(ctx.value("taunt_buff", "buff_taunted")), ctx.caster, ctx.values)
	var sb := str(ctx.value("self_buff", ""))
	if sb != "":
		ctx.world.buffs.apply(ctx.caster, sb, ctx.caster,
			{"duration": ctx.value("self_duration", 6.0), "armor": ctx.value("armor", 0)})
	return true
