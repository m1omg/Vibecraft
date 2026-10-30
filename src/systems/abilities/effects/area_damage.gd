extends AbilityEffect
## Effect `area_damage` (ability effect; owner agent C unless noted). Spell damage to every unit
## passing the targets filter in a circle (or a cone: shape, cone_angle) at the target point
## (damage, area, structure_factor; then optional buff / ground_effect). Naphtha Flask, Sunglint,
## Ley Pulse. Stub: circle only, no buff or ground effect.


func cast(ctx: CastContext) -> bool:
	var centre := ctx.target_pos if ctx.target_pos != Vector3.ZERO else ctx.caster.pos
	var r := float(ctx.value("area", ctx.value("range", 0.0)))
	var night := DayNight.is_night_at(ctx.world.time)
	var dmg := float(ctx.value("damage", 0.0)) * (float(ctx.value("night_damage_factor", 1.0)) if night else 1.0)
	var victims: Array[Unit] = []
	if str(ctx.value("shape", "circle")) == "cone":
		victims = units_in_cone(ctx, ctx.caster.pos, centre, float(ctx.value("range", r)), float(ctx.value("cone_angle", 50.0)))
	else:
		victims = units_in_area(ctx, centre, r)
	var buff := str(ctx.value("buff", ""))
	for u in victims:
		var f := float(ctx.value("structure_factor", 1.0)) if u.is_structure() else 1.0
		ctx.world.combat.hit(ctx.caster, u, dmg * f, str(ctx.value("damage_type", "spell")))
		if buff != "" and u.alive:
			var vals := ctx.values.duplicate()
			if night:
				vals["duration"] = float(vals.get("duration", 0.0)) + float(ctx.value("night_extra_duration", 0.0))
				vals["hero_duration"] = float(vals.get("hero_duration", vals["duration"])) + float(ctx.value("night_extra_hero_duration", 0.0))
			ctx.world.buffs.apply(u, buff, ctx.caster, vals)
	var ground := str(ctx.value("ground_effect", ""))
	if ground != "":
		ctx.world.abilities.add_ground_effect(ground, ctx.caster, centre, r,
			float(ctx.value("ground_duration", 5.0)), ctx.values)
	return true


## Units the filter allows inside a cone from `from` toward `to`, `length` long and `angle_deg`
## wide (Sunglint), by id.
static func units_in_cone(ctx: CastContext, from: Vector3, to: Vector3, length: float, angle_deg: float) -> Array[Unit]:
	var out: Array[Unit] = []
	var dir := Vector2(to.x - from.x, to.z - from.z)
	if dir.length() < 0.01:
		dir = Vector2(-sin(ctx.caster.facing), -cos(ctx.caster.facing))
	dir = dir.normalized()
	var half := deg_to_rad(angle_deg) * 0.5
	for u in units_in_area(ctx, from, length):
		var v := Vector2(u.pos.x - from.x, u.pos.z - from.z)
		if v.length() <= u.radius or absf(dir.angle_to(v)) <= half:
			out.append(u)
	return out
