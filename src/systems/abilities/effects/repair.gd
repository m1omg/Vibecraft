extends AbilityEffect
## Effect `repair` (ability effect; owner agent C unless noted). Card command of Repair / Mend:
## issues a REPAIR order on the target (orders/repair.gd); autocast (8 m) is AbilitySystem's. Owner:
## agent A.


func cast(ctx: CastContext) -> bool:
	if ctx.target_unit == null:
		return false
	ctx.world.issue({"type": "repair", "player": ctx.caster.player_id, "units": [ctx.caster.id],
		"target": ctx.target_unit.id})
	return true
