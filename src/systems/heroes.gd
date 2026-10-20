class_name HeroSystem
extends SimSystem
## Heroes (owner: agent C; rules.md §6, data: heroes.json). Stage: economy.
## Responsibilities:
##   - hero state on the Unit (`Unit.hero`): {hero_id, level, xp (float), skill_points,
##     ranks: {ability: rank}, attr_bonus: {str, agi, int}, proper_name}
##   - attributes and derived stats (Defs.hero_stats is the one formula) pushed to the unit with
##     Unit.set_base_stats on spawn, level-up and attribute gains
##   - XP: kill XP by victim level, creep factor, summon factor, sharing within 18.75 m, the
##     single-hero bonus, no XP at level 10 (rules §6.3–§6.4); flat-XP power-ups (add_xp flat)
##   - learning (rank gates 1/3/5, ultimate at 6, one point per level), Wiped Slate retrain
##   - hero slots by tier, unique types, the first-hero token and recall-item grant
##   - death bookkeeping (PlayerState.heroes keeps dead heroes for revival), altar revive
##     (cost/time formulas) and inn revive (instant, 50 % HP, 0 mana)
## Signals (Events): hero_level_up(u), xp_gained(u, amount), ability_learned(u, ability, rank),
##   hero_died(u), hero_revived(u).
## Commands handled: "revive" {units: [altar or inn], target: hero record index / unit id}.
## Called by: orders/learn.gd (can_learn, learn), AbilitySystem (rank_of), ItemSystem
##   (add_attributes, add_xp, retrain), Production (can_acquire / hero slots), HUD, AI.


func hooks() -> Array[StringName]:
	return [&"spawned", &"died"]


func on_unit_spawned(u: Unit) -> void:
	if not u.is_hero or not u.hero.is_empty():
		return
	var hid := str(u.def.get("hero_id", u.def_id))
	u.hero = {"hero_id": hid, "level": 1, "xp": 0.0,
		"skill_points": int(Defs.rule("heroes.skill_points_start", 1)), "ranks": {},
		"attr_bonus": {"str": 0, "agi": 0, "int": 0}, "proper_name": ""}
	var p := world.player(u.player_id)
	if p != null and not p.heroes.has(u.id):
		p.heroes.append(u.id)
	apply_attributes(u)


## Kill XP is awarded here (rules §6.3–§6.4). Stub: hero death bookkeeping only.
func on_unit_died(u: Unit, _killer: Unit) -> void:
	if u.is_hero:
		Events.hero_died.emit(u)


func level_of(u: Unit) -> int:
	return int(u.hero.get("level", 1))


func rank_of(u: Unit, ability_id: String) -> int:
	return int((u.hero.get("ranks", {}) as Dictionary).get(ability_id, 0))


## Recomputes the hero's base stats from level + attribute bonuses (Defs.hero_stats).
func apply_attributes(u: Unit) -> void:
	var st := Defs.hero_stats(str(u.hero.get("hero_id", u.def_id)), level_of(u), u.hero.get("attr_bonus", {}))
	if st.is_empty():
		return
	u.level = level_of(u)
	u.set_base_stats({"max_hp": st["hp"], "max_mana": st["mana"], "armor": st["armor"],
		"damage_min": st["damage_min"], "damage_max": st["damage_max"], "cooldown": st["cooldown"],
		"hp_regen": st["hp_regen"], "mana_regen": st["mana_regen"]})


## Adds XP (flat: ignores factors) and levels up (HP/mana rise by the same amount, +1 skill
## point per level, capped at rules.heroes.level_cap).
func add_xp(u: Unit, amount: float, _flat: bool = false) -> void:
	if not u.is_hero or amount <= 0.0:
		return
	var cap := int(Defs.rule("heroes.level_cap", 10))
	if level_of(u) >= cap:
		return
	u.hero["xp"] = float(u.hero.get("xp", 0.0)) + amount
	Events.xp_gained.emit(u, amount)
	var lv := Defs.level_for_xp(float(u.hero["xp"]))
	while level_of(u) < lv:
		u.hero["level"] = level_of(u) + 1
		u.hero["skill_points"] = int(u.hero.get("skill_points", 0)) + int(Defs.rule("heroes.skill_points_per_level", 1))
		apply_attributes(u)
		Events.hero_level_up.emit(u)


## Can `u` put a point into `ability_id` now (point available, in its kit, rank gate)?
func can_learn(u: Unit, ability_id: String) -> bool:
	if not u.is_hero or int(u.hero.get("skill_points", 0)) <= 0:
		return false
	if not (u.def.get("hero_abilities", []) as Array).has(ability_id):
		return false
	var a := Defs.ability(ability_id)
	var next := rank_of(u, ability_id) + 1
	if next > Defs.ability_levels(ability_id):
		return false
	var need := int(Defs.rule("heroes.ultimate_level", 6)) if a.get("ultimate", false) \
		else int((Defs.rule("heroes.rank_levels", [1, 3, 5]) as Array)[mini(next, 3) - 1])
	return level_of(u) >= need


func learn(u: Unit, ability_id: String) -> bool:
	if not can_learn(u, ability_id):
		return false
	var ranks: Dictionary = u.hero.get_or_add("ranks", {})
	ranks[ability_id] = int(ranks.get(ability_id, 0)) + 1
	u.hero["skill_points"] = int(u.hero["skill_points"]) - 1
	Events.ability_learned.emit(u, ability_id, int(ranks[ability_id]))
	return true


## Hero slots the player has at its current tier (rules §6.1).
func hero_slots(pid: int) -> int:
	var slots: Array = Defs.rule("heroes.slots_by_tier", [1, 2, 3])
	var t := clampi(world.tech.tier(pid), 1, slots.size())
	return int(slots[t - 1])


## Revive at an altar / inn. Stub: false.
func handle_command(_cmd: Dictionary, _units: Array[Unit]) -> bool:
	return false
