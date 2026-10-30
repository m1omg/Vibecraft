extends AbilityEffect
## Effect `transform` (ability effect; owner agent C unless noted). Turns the caster into `into` for
## `duration` (Take Up the Flail) or back (revert: Lay Down the Flail). Owner: agent A (worker
## defence). Stub: no-op until a World.transform_unit exists.


func cast(ctx: CastContext) -> bool:
	if bool(ctx.value("revert", false)):
		return ctx.world.abilities.revert_levy(ctx.caster)
	return ctx.world.abilities.take_up(ctx.caster, str(ctx.value("into", "")), ctx.values)
