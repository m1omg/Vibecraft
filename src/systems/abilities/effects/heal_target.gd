extends AbilityEffect
## Effect `heal_target` (ability effect; owner agent C unless noted). Heals the target unit (amount;
## self_factor when the caster targets itself; splash_radius / splash_factor heal allies around it).
## Linden Balm, Herb Poultice, Pine-Tar Dressing, Re-Stuff.


func cast(ctx: CastContext) -> bool:
	var t := ctx.target_unit if ctx.target_unit != null else ctx.caster
	var amount := float(ctx.value("amount", 0.0))
	_heal(ctx, t, amount * (float(ctx.value("self_factor", 1.0)) if t == ctx.caster else 1.0))
	var r := float(ctx.value("splash_radius", 0.0))
	if r > 0.0:
		for u in units_in_area(ctx, t.pos, r):
			if u != t:
				_heal(ctx, u, amount * float(ctx.value("splash_factor", 0.0)))
	return true


## Heals and tells the view (the heal number and the bloom), never more than missing HP.
static func _heal(ctx: CastContext, u: Unit, amount: float) -> void:
	var got := u.heal(amount)
	if got > 0.0:
		Events.unit_healed.emit(u, got, ctx.caster)
