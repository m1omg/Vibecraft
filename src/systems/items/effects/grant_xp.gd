extends AbilityEffect
## Effect `grant_xp` (item effect; owner agent D). Flat XP (Old Soldier's Tally-Stick): ignores the
## creep factor and the single-hero bonus.


func cast(ctx: CastContext) -> bool:
	ctx.world.heroes.add_xp(ctx.caster, float(ctx.value("xp", 0.0)), true)
	return true
