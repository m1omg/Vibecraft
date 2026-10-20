extends AbilityEffect
## Effect `apply_buff` (ability effect; owner agent C unless noted). Applies `buff` to the target
## (the caster for self abilities) with this rank's values as overrides (duration, hero_duration,
## modifiers). Fuse Mark, Dust Veil, Through the Tall Grass, Wind at Your Back, Ley Tether.


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit if ctx.target_unit != null else ctx.caster
	var b := str(ctx.value("buff", ""))
	if b == "":
		return false
	ctx.world.buffs.apply(t, b, ctx.caster, ctx.values)
	return true
