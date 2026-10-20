extends AbilityEffect
## Effect `reveal_area` (ability effect; owner agent C unless noted). Reveals a circle (`area`) for
## `duration` (detect: invisible units too) through Fog.reveal. Bronze Window, Signal Shell.


func cast(ctx: CastContext) -> bool:
	ctx.world.fog.reveal(ctx.caster.player_id, ctx.target_pos, float(ctx.value("area", 8.0)),
		float(ctx.value("duration", 10.0)), bool(ctx.value("detect", false)))
	return true
