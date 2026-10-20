extends AbilityEffect
## Effect `heal_instant` (item effect; owner agent D). Restores `amount` HP at once (Linden Salve,
## Kettle-Bottom Tea, Rosehip Draught).


func cast(ctx: CastContext) -> bool:
	ctx.caster.heal(float(ctx.value("amount", 0.0)))
	return true
