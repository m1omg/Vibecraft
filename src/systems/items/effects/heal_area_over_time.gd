extends AbilityEffect
## Effect `heal_area_over_time` (item effect; owner agent D). Own + allied organic units within
## `radius` (0 = the user) heal `amount` over `duration`, never broken by damage (Picnic Hamper,
## Honeycomb Wedge). Stub: the user only.


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.apply(ctx.caster, str(ctx.value("buff", "buff_heal_over_time")), ctx.caster, ctx.values)
	return true
