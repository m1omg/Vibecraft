extends AbilityEffect
## Effect `dispel_area` (ability effect; owner agent C unless noted). Dispels buffs in `area`
## (dispel_mode all / selective, rules §10.4) and deals summon_damage to enemy summons; Unbind also
## slows (slow_buff). Smoke of Rue, Unbind. Stub: dispel only.


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.dispel_area(ctx.target_pos, float(ctx.value("area", 3.0)), str(ctx.value("dispel_mode", "all")),
		ctx.caster.player_id)
	return true
