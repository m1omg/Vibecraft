extends AbilityEffect
## Effect `damage_target` (ability effect; owner agent C unless noted). Spell damage to one unit
## (damage, damage_type; Braid Lash adds pull / root_buff).


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit
	if t == null or not t.alive:
		return false
	ctx.world.combat.hit(ctx.caster, t, float(ctx.value("damage", 0.0)), str(ctx.value("damage_type", "spell")))
	return true
