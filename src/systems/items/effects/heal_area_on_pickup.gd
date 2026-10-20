extends AbilityEffect
## Effect `heal_area_on_pickup` (item effect; owner agent D). Power-up: own organic units within
## `radius` restore `amount` HP (Wild Strawberries; any unit picks it up). Stub: the picker only.


func cast(ctx: CastContext) -> bool:
	ctx.caster.heal(float(ctx.value("amount", 0.0)))
	return true
