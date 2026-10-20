extends AbilityEffect
## Effect `vision_flare` (item effect; owner agent D). Vision (no detection) at a point within
## `range` for `duration` (Firefly Jar).


func cast(ctx: CastContext) -> bool:
	ctx.world.fog.reveal(ctx.caster.player_id, ctx.target_pos, float(ctx.value("sight", 10.0)),
		float(ctx.value("duration", 20.0)), false)
	return true
