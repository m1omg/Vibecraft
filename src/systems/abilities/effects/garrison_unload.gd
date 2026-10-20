extends AbilityEffect
## Effect `garrison_unload` (ability effect; owner agent C unless noted). Unload All: empties the
## garrison building (Construction.garrison_unload). Owner: agent A.


func cast(ctx: CastContext) -> bool:
	ctx.world.construction.garrison_unload(ctx.caster)
	return true
