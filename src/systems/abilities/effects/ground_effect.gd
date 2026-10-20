extends AbilityEffect
## Effect `ground_effect` (ability effect; owner agent C unless noted). Creates a ground effect
## (buffs.json ground_effects id `ground_effect`) at the target point for `duration`
## (AbilitySystem.add_ground_effect). Swallowed Sun, Smoke Pot.


func cast(ctx: CastContext) -> bool:
	var centre := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	ctx.world.abilities.add_ground_effect(str(ctx.value("ground_effect", "")), ctx.caster, centre,
		float(ctx.value("area", 3.0)), float(ctx.value("duration", 5.0)), ctx.values)
	return true
