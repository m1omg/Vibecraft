class_name Tech
extends SimSystem
## Tech (owner: agent B; rules.md §5, data: upgrades.json, buildings.json requires/tier).
## Stage: production. Responsibilities:
##   - the player's tier: highest tier among their finished halls (factions.<id>.hall_tiers),
##     kept on PlayerState.tier; hero slots follow it (HeroSystem reads it)
##   - live requirement checks for units, buildings, research and hall upgrades (requires:
##     building ids or upgrade ids; research levels' requires_tier); losing them greys buttons,
##     items already in production finish
##   - research levels per player (PlayerState.upgrades: id -> level) and their effects on
##     units: upgrade_damage, armor, range, unit_bonus, splash, building_bonus, unlock_ability
##     — pushed onto every affected unit as the "tech" modifier source (Unit.set_modifiers) and
##     re-applied to new units on spawn
##   - building upgrades (hall tiers, Lookout -> Gun Tower): swap the def in place keeping HP %
##     and footprint (rules §5.1), food/tier on completion
##   - combat extensions owned by the same agent: Combat splash / artillery / attack ground /
##     min range / targets G-A / damage_pct + damage_taken_pct (see docs/m2-ownership.md)
## Signals (Events): research_started(pid, id, building), research_completed(pid, id),
##   tier_changed(pid, tier).
## Called by: Production (can_research, requirements_met, complete_research), HUD (missing
##   requirements for tooltips), AbilitySystem (ability_unlocked), AI.


func hooks() -> Array[StringName]:
	return [&"spawned"]


func on_unit_spawned(u: Unit) -> void:
	apply_unit_upgrades(u)


## Highest tier among the player's finished halls (0 = none).
func tier(pid: int) -> int:
	var p := world.player(pid)
	var tiers: Array = Defs.faction(p.faction).get("hall_tiers", []) if p != null and p.faction != "" else []
	var best := 0
	for u in world.unit_list:
		if u.player_id == pid and not u.under_construction and u.has_flag("town_hall"):
			var i := tiers.find(u.def_id)
			best = maxi(best, i + 1 if i >= 0 else int(u.def.get("tier", 1)))
	return best


## Research level reached by `pid` (0 = not researched).
func research_level(pid: int, upgrade_id: String) -> int:
	var p := world.player(pid)
	return int(p.upgrades.get(upgrade_id, 0)) if p != null else 0


## Ids in def `id`'s `requires` that `pid` does not have yet (finished building of that id —
## a higher hall tier counts for a lower one — or a researched upgrade).
func missing_requirements(pid: int, id: String) -> Array:
	var d: Dictionary = Defs.units.get(id, Defs.upgrades.get(id, {}))
	var out: Array = []
	for r: Variant in d.get("requires", []):
		var rid := str(r)
		if Defs.upgrades.has(rid) and not Defs.units.has(rid):
			if research_level(pid, rid) <= 0:
				out.append(rid)
		elif not _owns_finished(pid, rid):
			out.append(rid)
	return out


func requirements_met(pid: int, id: String) -> bool:
	return missing_requirements(pid, id).is_empty()


func _owns_finished(pid: int, def_id: String) -> bool:
	var p := world.player(pid)
	var tiers: Array = Defs.faction(p.faction).get("hall_tiers", []) if p != null and p.faction != "" else []
	var want := tiers.find(def_id)
	for u in world.unit_list:
		if u.player_id != pid or u.under_construction:
			continue
		if u.def_id == def_id:
			return true
		if want >= 0 and tiers.find(u.def_id) > want:
			return true
	return false


## "" when `pid` can start the next level of `upgrade_id` at `building`, else an error key.
func can_research(pid: int, upgrade_id: String, building: Unit = null) -> String:
	var up := Defs.upgrade(upgrade_id)
	if up.is_empty():
		return "unknown"
	var next := research_level(pid, upgrade_id) + 1
	if next > (up.get("levels", []) as Array).size():
		return "maxed"
	if building != null and not Defs.researched_at(upgrade_id).has(building.def_id):
		return "wrong_building"
	if int(Defs.upgrade_level(upgrade_id, next).get("requires_tier", 1)) > tier(pid):
		return "tier"
	if not requirements_met(pid, upgrade_id):
		return "requirements"
	return ""


## Called by Production when a research level finishes: records it, emits research_completed and
## re-applies upgrades to the player's units. Stub: records + signal (effects not applied yet).
func complete_research(pid: int, upgrade_id: String) -> void:
	var p := world.player(pid)
	if p == null:
		return
	p.upgrades[upgrade_id] = int(p.upgrades.get(upgrade_id, 0)) + 1
	Events.research_completed.emit(pid, upgrade_id)


## True when ability `ability_id` needs no research or `pid` has researched its `unlock`.
func ability_unlocked(pid: int, ability_id: String) -> bool:
	var unlock := str(Defs.ability(ability_id).get("unlock", ""))
	return unlock == "" or research_level(pid, unlock) > 0


## Pushes the player's research effects onto `u` (modifier source "tech"). Stub: nothing.
func apply_unit_upgrades(_u: Unit) -> void:
	pass
