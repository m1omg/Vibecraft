extends OrderHandler
## LEARN (owner: heroes agent C): instant. Spends a skill point on o.ability through
## HeroSystem.learn(hero, ability_id); never interrupts the hero's current order.


func is_instant() -> bool:
	return true


func can_start(u: Unit, o: Order) -> bool:
	return u.is_hero and u.world.heroes.can_learn(u, o.ability)


func apply_instant(u: Unit, o: Order) -> void:
	u.world.heroes.learn(u, o.ability)
