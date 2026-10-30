extends AbilityEffect
## Effect `apply_buff` (ability effect; owner agent C unless noted). Applies `buff` to the target
## (the caster for self abilities) with this rank's values as overrides (duration, hero_duration,
## modifiers). Fuse Mark, Dust Veil, Through the Tall Grass, Wind at Your Back, Ley Tether.


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit if ctx.target_unit != null else ctx.caster
	var b := str(ctx.value("buff", ""))
	if b == "":
		return false
	var vals := ctx.values.duplicate()
	vals["source_ability"] = ctx.id
	vals["rank"] = ctx.rank
	ctx.world.buffs.apply(t, b, ctx.caster, vals)
	return true


## Fuse Mark's explosion (on_expire "explode", also when the marked unit dies): the rank's damage
## to the unit (×structure_factor on buildings) and splash_factor of it within splash_radius.
func buff_expired(world: World, unit: Unit, rec: Dictionary) -> void:
	var v: Dictionary = rec.get("values", {})
	var src := world.get_unit(int(rec.get("source_id", 0)))
	var dmg := float(v.get("damage", 0.0))
	var kind := str(v.get("damage_type", "spell"))
	var at := unit.pos
	Events.ability_burst.emit(str(v.get("source_ability", "")), at, float(v.get("splash_radius", 0.0)))
	if unit.alive:
		world.combat.hit(src, unit, dmg * (float(v.get("structure_factor", 1.0)) if unit.is_structure() else 1.0), kind)
	var r := float(v.get("splash_radius", 0.0))
	if r <= 0.0:
		return
	for u: Unit in world.query_radius(at, r + world.max_unit_radius):
		if u == unit or not u.alive or u.hidden or Grid.flat_dist(u.pos, at) - u.radius > r:
			continue
		if int(rec.get("source_player", -1)) >= 0 and not world.is_enemy(int(rec["source_player"]), u.player_id):
			continue
		var f := float(v.get("structure_factor", 1.0)) if u.is_structure() else 1.0
		world.combat.hit(src, u, dmg * float(v.get("splash_factor", 0.0)) * f, kind)
