extends AbilityEffect
## Effect `grant_attribute` (item effect; owner agent D). Permanent attribute points (str / agi /
## int) for the hero (power-ups).


func cast(ctx: CastContext) -> bool:
	var u := ctx.caster
	if not u.is_hero:
		return false
	var bonus: Dictionary = u.hero.get_or_add("attr_bonus", {"str": 0, "agi": 0, "int": 0})
	for k: String in ["str", "agi", "int"]:
		bonus[k] = int(bonus.get(k, 0)) + int(ctx.value(k, 0))
	ctx.world.heroes.apply_attributes(u)
	return true
