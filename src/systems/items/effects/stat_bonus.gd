extends AbilityEffect
## Effect `stat_bonus` (item effect; owner agent D). Permanent item: its params (str, agi, int,
## damage, armor, max_hp, hp_regen, mana_regen, attack_speed_pct, move_speed) apply while carried;
## ItemSystem recomputes the hero's items modifier source on pickup and drop. Using it does nothing.


func cast(_ctx: CastContext) -> bool:
	return true
