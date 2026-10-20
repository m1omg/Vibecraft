extends AbilityEffect
## Effect `heal_target` (ability effect; owner agent C unless noted). Heals the target unit (amount;
## self_factor when the caster targets itself; splash_radius / splash_factor heal allies around it).
## Linden Balm, Herb Poultice, Pine-Tar Dressing, Re-Stuff.


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit if ctx.target_unit != null else ctx.caster
	var amount := float(ctx.value("amount", 0.0))
	if t == ctx.caster:
		amount *= float(ctx.value("self_factor", 1.0))
	t.heal(amount)
	return true
