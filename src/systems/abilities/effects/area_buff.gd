extends AbilityEffect
## Effect `area_buff` (ability effect; owner agent C unless noted). Applies `buff` to every unit in
## `area` around the target point (else the caster) that passes the targets filter. The Wagon Ring,
## Stoke the Coals, Choking Fumes.


func cast(ctx: CastContext) -> bool:
	var centre := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	var b := str(ctx.value("buff", ""))
	for u in units_in_area(ctx, centre, float(ctx.value("area", 0.0))):
		ctx.world.buffs.apply(u, b, ctx.caster, ctx.values)
	return true
