extends AbilityEffect
## Effect `summon` (ability effect; owner agent C unless noted). Spawns `count` units of `unit`
## (lifetime seconds -> Unit.lifetime_ticks) around the target point or the caster. Hail-Swifts,
## Grand Bombard, Scatter-Crows.


func cast(ctx: CastContext) -> bool:
	var centre := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	var n := int(ctx.value("count", 1))
	for i in n:
		var a := TAU * i / maxf(n, 1)
		var off := Vector3(cos(a), 0.0, sin(a)) * float(ctx.value("spawn_radius", 1.5)) if n > 1 else Vector3.ZERO
		var s := ctx.world.spawn_unit(str(ctx.value("unit", "")), ctx.caster.player_id, centre + off, ctx.caster.facing)
		if s != null:
			s.lifetime_ticks = roundi(float(ctx.value("lifetime", 30.0)) * World.TICK_RATE)
	return true
