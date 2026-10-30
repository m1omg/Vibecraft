extends AbilityEffect
## Effect `garrison_enter` (ability effect; owner agent C unless noted). Card command of Roll the
## Felt: issues an ENTER order on the target Home Yurt (orders/enter.gd). Owner: agent A.


func cast(ctx: CastContext) -> bool:
	var yurt := ctx.target_unit
	if yurt == null:
		yurt = ctx.world.construction.free_garrison_near(ctx.caster)
	if yurt == null or not ctx.world.construction.can_enter(ctx.caster, yurt):
		return false
	ctx.caster.issue_order(Order.make(Order.Type.ENTER, yurt.pos, yurt.id))
	return true
