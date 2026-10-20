extends AbilityEffect
## Effect `mana_instant` (item effect; owner agent D). Restores `amount` mana at once (Sage's
## Tincture, Overnight Steep, Bluebell Cordial, Mint Sprig).


func cast(ctx: CastContext) -> bool:
	var u := ctx.caster
	u.mana = minf(u.max_mana, u.mana + float(ctx.value("amount", 0.0)))
	return true
