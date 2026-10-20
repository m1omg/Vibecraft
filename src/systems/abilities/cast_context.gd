class_name CastContext
extends RefCounted
## Everything an AbilityEffect needs for one cast (or one item use).

var world: World
var caster: Unit
var id: String = ""               ## ability id, or item id when source == "item"
var source: String = "ability"    ## "ability" | "item" | "passive" | "aura"
var rank: int = 1
## Resolved numbers for this rank (Defs.ability_rank: mana, cooldown, range, area, duration, ...
## plus the ability's params and rank overrides; items: the item's params).
var values: Dictionary = {}
var target_unit: Unit = null
var target_pos: Vector3 = Vector3.ZERO
var targets: Dictionary = {}      ## the def's `targets` filter (relation / require / exclude)


static func make(w: World, c: Unit, ability_or_item: String, rank_value: int, vals: Dictionary,
		target: Unit = null, pos: Vector3 = Vector3.ZERO, src: String = "ability") -> CastContext:
	var ctx := CastContext.new()
	ctx.world = w
	ctx.caster = c
	ctx.id = ability_or_item
	ctx.rank = rank_value
	ctx.values = vals
	ctx.target_unit = target
	ctx.target_pos = target.pos if target != null and pos == Vector3.ZERO else pos
	ctx.source = src
	var d: Dictionary = Defs.abilities.get(ability_or_item, {}) if src != "item" else Defs.items.get(ability_or_item, {})
	ctx.targets = d.get("targets", {})
	return ctx


func value(key: String, fallback: Variant = 0.0) -> Variant:
	return values.get(key, fallback)


## Does `u` pass the targets filter (rules §10.7 flags)? relation: self, self_player, ally,
## enemy, neutral (any match); require: every listed flag; require_any: one of them; exclude:
## none of them. Empty filter: enemies for damage, allies otherwise — effects decide.
func allows(u: Unit) -> bool:
	var rel: Array = targets.get("relation", [])
	if not rel.is_empty():
		var ok := false
		for r: String in rel:
			match r:
				"self":
					ok = ok or u == caster
				"self_player":
					ok = ok or u.player_id == caster.player_id
				"ally":
					ok = ok or (u != caster and world.is_ally(caster.player_id, u.player_id))
				"enemy":
					ok = ok or world.is_enemy(caster.player_id, u.player_id)
				"neutral":
					ok = ok or u.player_id >= PlayerState.NEUTRAL_HOSTILE
		if not ok:
			return false
	if targets.get("exclude_self", false) and u == caster:
		return false
	for f: String in targets.get("require", []):
		if not _has(u, f):
			return false
	var any: Array = targets.get("require_any", [])
	if not any.is_empty() and not any.any(func(f: String) -> bool: return _has(u, f)):
		return false
	for f: String in targets.get("exclude", []):
		if _has(u, f):
			return false
	return true


static func _has(u: Unit, f: String) -> bool:
	match f:
		"structure":
			return u.is_structure()
		"hero":
			return u.is_hero
		"ranged":
			return not u.projectile.is_empty()
		"melee":
			return u.projectile.is_empty() and u.can_attack()
		"ground":
			return not u.is_flying
		"air":
			return u.is_flying
	return u.has_flag(f)
