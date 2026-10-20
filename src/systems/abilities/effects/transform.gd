extends AbilityEffect
## Effect `transform` (ability effect; owner agent C unless noted). Turns the caster into `into` for
## `duration` (Take Up the Flail) or back (revert: Lay Down the Flail). Owner: agent A (worker
## defence). Stub: no-op until a World.transform_unit exists.


func cast(_ctx: CastContext) -> bool:
	return true
