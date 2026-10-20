extends AbilityEffect
## Effect `garrison_enter` (ability effect; owner agent C unless noted). Card command of Roll the
## Felt: issues an ENTER order on the target Home Yurt (orders/enter.gd). Owner: agent A.


func cast(ctx: CastContext) -> bool:
	if ctx.target_unit == null:
		return false
	ctx.world.issue({"type": "enter", "player": ctx.caster.player_id, "units": [ctx.caster.id],
		"target": ctx.target_unit.id})
	return true
