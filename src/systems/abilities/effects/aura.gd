extends AbilityEffect
## Effect `aura` (ability effect; owner agent C unless noted). Passive aura: the buffs system
## re-applies `buff` to units in `area` every rules.status.aura_refresh while the emitter lives
## (BuffSystem.set_aura). Measured Cadence, Incendiary Wadding, Old Ward.


func cast(ctx: CastContext) -> bool:
	ctx.world.buffs.set_aura(ctx.caster, ctx.id, ctx.rank)
	return true
