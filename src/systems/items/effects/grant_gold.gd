extends AbilityEffect
## Effect `grant_gold` (item effect; owner agent D). +gold to the owner, taxed by upkeep like other
## ability income (Dropped Purse).


func cast(ctx: CastContext) -> bool:
	ctx.world.economy.add_income(ctx.caster.player_id, "gold", int(ctx.value("gold", 0)), "ability", ctx.caster.pos)
	return true
