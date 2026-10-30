class_name SpellAi
extends RefCounted
## When and where a computer-run unit casts (rules §19 "Abilities": area on 2+ targets, heals
## below 60 % HP; neutrals §1.7 for creeps). Shared by the creep spell AI and AiPlayer's heroes.
## `pick` returns the extra command fields for a CAST ({"target": id}, {"pos": point},
## {"self": true}) or {} when the ability should wait. Reads sim state only, through the caster's
## eyes (invisible enemies are not seen). Static, no state, no randomness.

const HEAL_BELOW := 0.6
const FIGHT_RADIUS := 12.0


static func pick(world: World, caster: Unit, ability_id: String, friends: Array[Unit]) -> Dictionary:
	var a := Defs.ability(ability_id)
	var kind := str(a.get("type", ""))
	var effect := str(a.get("effect", ""))
	if kind in ["passive", "aura", "command", "toggle"] or effect in ["reveal_area", "transform", "levy_horn", "levy_release"]:
		return {}
	var v := world.abilities.values_for(caster, ability_id)
	var reach := float(v.get("range", 0.0))
	var area := float(v.get("area", 0.0))
	var foes := _foes(world, caster, maxf(maxf(reach, area), FIGHT_RADIUS) + area)
	match effect:
		"heal_target":
			var hurt := _most_hurt(caster, friends, reach)
			return {"target": hurt.id} if hurt != null else {}
		"taunt_area":
			return {"self": true} if _count_within(caster, foes, area) >= 2 else {}
		"area_buff":
			if kind == "instant":
				if foes.is_empty():
					return {}
				var low := 0
				for f in friends:
					if f.alive and caster.edge_distance(f) <= area and f.hp < f.max_hp * 0.45:
						low += 2 if f.is_hero else 1
				var ult := bool(a.get("ultimate", false))
				return {"self": true} if not ult or low >= 2 else {}
			var t := _hero_or_nearest(caster, foes, reach)
			return {"target": t.id} if t != null and _count_near(t, foes, area) >= 1 else {}
		"area_damage", "ground_effect":
			if kind == "instant":
				var n := _count_within(caster, foes, area)
				return {"self": true} if n >= 2 or _hero_within(caster, foes, area) else {}
			var need := 4 if bool(a.get("ultimate", false)) else 2
			var spot := _best_cluster(caster, foes, reach, maxf(area, 3.0), need)
			return {"pos": spot} if spot != Vector3.INF else {}
		"apply_buff":
			if kind == "target_unit":
				var t := _hero_or_nearest(caster, foes, reach, true)
				return {"target": t.id} if t != null else {}
			if ability_id == "clans_dust_veil":
				return {"self": true} if caster.hp < caster.max_hp * 0.35 and not foes.is_empty() else {}
			return {"self": true} if _count_within(caster, foes, 6.0) >= 3 or _hero_within(caster, foes, 6.0) else {}
		"damage_target":
			var t := _hero_or_nearest(caster, foes, reach)
			return {"target": t.id} if t != null else {}
		"summon":
			if foes.is_empty():
				return {}
			if kind == "target_point":
				var aim := caster.pos.lerp(foes[0].pos, 0.4)
				return {"pos": aim}
			return {"self": true}
	return {}


## Enemies `caster` can see and fight within `r` (no structures), nearest first.
static func _foes(world: World, caster: Unit, r: float) -> Array[Unit]:
	var out: Array[Unit] = []
	for u: Unit in world.query_radius(caster.pos, r + world.max_unit_radius):
		if caster.is_valid_target(u) and not u.is_structure() and caster.edge_distance(u) <= r:
			out.append(u)
	out.sort_custom(func(x: Unit, y: Unit) -> bool:
		var dx := caster.edge_distance(x)
		var dy := caster.edge_distance(y)
		return dx < dy if dx != dy else x.id < y.id)
	return out


static func _count_within(caster: Unit, foes: Array[Unit], r: float) -> int:
	var n := 0
	for f in foes:
		if caster.edge_distance(f) <= r:
			n += 1
	return n


static func _count_near(t: Unit, foes: Array[Unit], r: float) -> int:
	var n := 0
	for f in foes:
		if f != t and Grid.flat_dist(f.pos, t.pos) <= r:
			n += 1
	return n


static func _hero_within(caster: Unit, foes: Array[Unit], r: float) -> bool:
	for f in foes:
		if f.is_hero and caster.edge_distance(f) <= r:
			return true
	return false


## An enemy hero in reach first, else (`toughest`) the healthiest enemy, else the nearest.
static func _hero_or_nearest(caster: Unit, foes: Array[Unit], reach: float, toughest: bool = false) -> Unit:
	var best: Unit = null
	for f in foes:
		if caster.edge_distance(f) > reach:
			continue
		if f.is_hero:
			return f
		if best == null or (toughest and f.hp > best.hp):
			best = f
	return best


## The friend in reach most in need of a heal (below 60 %), the caster itself last.
static func _most_hurt(caster: Unit, friends: Array[Unit], reach: float) -> Unit:
	var best: Unit = null
	for f in friends:
		if not f.alive or f.is_structure() or f.is_mechanical or f.hp >= f.max_hp * HEAL_BELOW:
			continue
		if f != caster and caster.edge_distance(f) > reach:
			continue
		if best == null or best == caster or (f != caster and f.hp / f.max_hp < best.hp / best.max_hp):
			best = f
	return best


## The point (an enemy's position) in reach with the most enemies within `r` around it, heroes
## counted twice; INF unless it scores at least `need`.
static func _best_cluster(caster: Unit, foes: Array[Unit], reach: float, r: float, need: int) -> Vector3:
	var best := Vector3.INF
	var best_score := need - 1
	for f in foes:
		if caster.edge_distance(f) > reach + r * 0.5:
			continue
		var score := 0
		for g in foes:
			if Grid.flat_dist(f.pos, g.pos) <= r:
				score += 2 if g.is_hero else 1
		if score > best_score:
			best_score = score
			best = f.pos
	return best
