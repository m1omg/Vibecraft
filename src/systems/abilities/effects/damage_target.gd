extends AbilityEffect
## Effect `damage_target` (ability effect; owner agent C unless noted). Spell damage to one unit
## (damage, damage_type; Braid Lash adds pull / root_buff).


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit
	if t == null or not t.alive:
		return false
	ctx.world.combat.hit(ctx.caster, t, float(ctx.value("damage", 0.0)), str(ctx.value("damage_type", "spell")))
	if not t.alive:
		return true
	var pull := float(ctx.value("pull_hero" if t.is_hero else "pull", 0.0))
	if pull > 0.0:
		var to := Vector3(ctx.caster.pos.x - t.pos.x, 0.0, ctx.caster.pos.z - t.pos.z)
		var room := maxf(0.0, to.length() - ctx.caster.radius - t.radius - 0.1)
		var step := minf(pull, room)
		if step > 0.01:
			var dest := t.pos + to.normalized() * step
			if ctx.world.pathing.is_walkable_world(dest, t.is_large()):
				t.teleport(dest)
	var root := str(ctx.value("root_buff", ""))
	if root != "":
		ctx.world.buffs.apply(t, root, ctx.caster, {"duration": ctx.value("root", 1.0),
			"hero_duration": ctx.value("root_hero", ctx.value("root", 1.0))})
	return true
