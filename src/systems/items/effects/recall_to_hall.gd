extends AbilityEffect
## Effect `recall_to_hall` (item effect; owner agent D). Recall (rules §6.8, rules.items.recall_*):
## 5 s channel, then the hero and up to 23 own units within 9.4 m appear beside the own finished
## hall nearest the target point. Stub: no-op.


func cast(_ctx: CastContext) -> bool:
	return true
