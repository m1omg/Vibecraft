extends AbilityEffect
## Effect `sound_the_gong` (ability effect; owner agent C unless noted). Hall toggle: Yurtwrights
## within `range` run to free Home Yurt slots; All Clear sends them back. Owner: agent A. Stub:
## no-op.


func cast(ctx: CastContext) -> bool:
	return ctx.world.construction.sound_the_gong(ctx.caster, float(ctx.value("range", 30.0)))
