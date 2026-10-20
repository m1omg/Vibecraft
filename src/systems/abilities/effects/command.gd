extends AbilityEffect
## Effect `command` (ability effect; owner agent C unless noted). Plain card commands (cmd_move,
## cmd_gather, ...): the HUD issues params.order as a command dictionary; casting one does nothing.


func cast(_ctx: CastContext) -> bool:
	return true
