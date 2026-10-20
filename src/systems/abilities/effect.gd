class_name AbilityEffect
extends RefCounted
## Base class of every ability / item effect script (owner: abilities agent C for
## src/systems/abilities/effects/, items agent D for src/systems/items/effects/).
##
## One stateless instance per effect id (EffectRegistry caches them); everything an effect
## needs arrives in the CastContext. An effect runs inside the fixed tick (never _process) and
## may only change the sim through World / system APIs (combat.hit, buffs.apply, heal, spawn_unit,
## economy.add_income ...). Persistent results (buffs, ground effects, summons) are owned by the
## system that stores them, never by the effect object. Visual juice listens to
## Events.ability_cast / buff_applied / ... and never runs from here.
##
## The `effect` field of an abilities.json / items.json entry names the script file:
## res://src/systems/abilities/effects/<effect>.gd, then res://src/systems/items/effects/<effect>.gd.


## Applies the effect. Returns false when it could not happen (the caller then refunds the
## mana / charge and keeps the cooldown ready).
func cast(_ctx: CastContext) -> bool:
	return true


## Helpers shared by effects -------------------------------------------------------------------

## Units within `r` of `p` that pass the ability's `targets` filter for `caster`.
static func units_in_area(ctx: CastContext, p: Vector3, r: float) -> Array[Unit]:
	var out: Array[Unit] = []
	var raw: Array = ctx.world.query_radius(p, r + ctx.world.max_unit_radius)
	for u: Unit in raw:
		if u.alive and not u.hidden and Grid.flat_dist(u.pos, p) - u.radius <= r and ctx.allows(u):
			out.append(u)
	out.sort_custom(func(a: Unit, b: Unit) -> bool: return a.id < b.id)
	return out
