extends AbilityEffect
## Effect `area_damage` (ability effect; owner agent C unless noted). Spell damage to every unit
## passing the targets filter in a circle (or a cone: shape, cone_angle) at the target point
## (damage, area, structure_factor; then optional buff / ground_effect). Naphtha Flask, Sunglint,
## Ley Pulse. Stub: circle only, no buff or ground effect.


func cast(ctx: CastContext) -> bool:
	var r := float(ctx.value("area", ctx.value("range", 0.0)))
	var centre := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	for u in units_in_area(ctx, centre, r):
		ctx.world.combat.hit(ctx.caster, u, float(ctx.value("damage", 0.0)), str(ctx.value("damage_type", "spell")))
	return true
