extends AbilityEffect
## Effect `reveal_invisible_area` (item effect; owner agent D). Reveals invisible units within
## `radius` for `duration` (Tailor's Chalk, Tattle-Burrs) via Fog.reveal(detect = true).


func cast(ctx: CastContext) -> bool:
	var p := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	ctx.world.fog.reveal(ctx.caster.player_id, p, float(ctx.value("radius", 9.0)), float(ctx.value("duration", 12.0)), true)
	return true
