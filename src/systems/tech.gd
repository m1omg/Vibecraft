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


var _tiers: Dictionary = {}       ## pid -> last announced tier


func hooks() -> Array[StringName]:
	return [&"spawned"]


func on_unit_spawned(u: Unit) -> void:
	apply_unit_upgrades(u)


## The player's tier follows its finished halls (a hall finishing, upgrading or falling):
## tier_changed when it moves (checked twice a second).
func sim_tick(w: World, _dt: float) -> void:
	if w.tick_count % 15 != 0:
		return
	for p: PlayerState in w.players:
		if p.is_neutral():
			continue
		var t := tier(p.id)
		if t != int(_tiers.get(p.id, -1)):
			var first := not _tiers.has(p.id)
			_tiers[p.id] = t
			p.tier = t
			if not first:
				Events.tier_changed.emit(p.id, t)


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
## re-applies the player's upgrades to its units.
func complete_research(pid: int, upgrade_id: String) -> void:
	var p := world.player(pid)
	if p == null:
		return
	p.upgrades[upgrade_id] = int(p.upgrades.get(upgrade_id, 0)) + 1
	for u in world.unit_list:
		if u.player_id == pid and u.alive:
			apply_unit_upgrades(u)
	Events.research_completed.emit(pid, upgrade_id)


## Called by Production when a building upgrade finishes (rules §5.1): the building becomes its
## upgrade in place (HP fraction, footprint and orders kept), the new tier's food replaces the
## old, research effects are re-applied, and the tier is announced at once.
func complete_building_upgrade(b: Unit, upgrade_id: String) -> void:
	var up := Defs.upgrade(upgrade_id)
	var to := str(up.get("to", upgrade_id))
	if not b.alive or Defs.unit(to).is_empty():
		return
	var old_food := int(b.def.get("food_provided", 0))
	var from := b.def_id
	b.transform_to(to)
	var new_food := int(b.def.get("food_provided", 0))
	if new_food != old_food and not b.under_construction:
		world.adjust_food(b.player_id, 0, new_food - old_food)
	apply_unit_upgrades(b)
	var p := world.player(b.player_id)
	if p != null:
		p.upgrades[upgrade_id] = 1
		var t := tier(b.player_id)
		if t != int(_tiers.get(b.player_id, -1)):
			_tiers[b.player_id] = t
			p.tier = t
			Events.tier_changed.emit(b.player_id, t)
	Events.research_completed.emit(b.player_id, upgrade_id)
	Events.building_upgraded.emit(b, from)
	Events.notification.emit(b.player_id, "upgrade_done", Defs.text("notice_upgrade_done") % str(b.def.get("name", to)))


## True when ability `ability_id` needs no research or `pid` has researched its `unlock`.
func ability_unlocked(pid: int, ability_id: String) -> bool:
	var unlock := str(Defs.ability(ability_id).get("unlock", ""))
	return unlock == "" or research_level(pid, unlock) > 0


## Pushes the player's research effects onto `u` as the "tech" modifier source (rules §5.4):
## `upgrade_damage` (the def's `upgrade_damage` per level, default 10 % of its average damage,
## at least 1), `armor` (amount per level), `range` (`value` = the new range, or `amount` per
## level), `unit_bonus` (hp, damage, mana per level),
## `building_bonus` (armor, hp_pct for the faction's structures). `unlock_ability` and `splash`
## are read where they apply (Tech.ability_unlocked, Combat).
func apply_unit_upgrades(u: Unit) -> void:
	var p := world.player(u.player_id)
	if p == null or p.upgrades.is_empty():
		return
	var mods := {}
	for uid: String in p.upgrades:
		var lv := int(p.upgrades[uid])
		if lv <= 0:
			continue
		for e: Dictionary in Defs.upgrade(uid).get("effects", []):
			var t := str(e.get("type", ""))
			if t == "building_bonus":
				if u.is_building and str(e.get("faction", u.def.get("faction", ""))) == str(u.def.get("faction", "")):
					_add(mods, "armor", float(e.get("armor", 0.0)) * lv)
					_add(mods, "max_hp_pct", float(e.get("hp_pct", 0.0)) * lv)
				continue
			if not (e.get("units", []) as Array).has(u.def_id):
				continue
			match t:
				"upgrade_damage":
					_add(mods, "damage", upgrade_damage_of(u) * lv)
				"armor":
					_add(mods, "armor", float(e.get("amount", 2.0)) * lv)
				"range":
					if e.has("value"):     # a new absolute range (Drawn Barrels 7.0 -> 9.0 m)
						_add(mods, "range", float(e["value"]) - float((u.def.get("attack", {}) as Dictionary).get("range", 0.0)))
					else:
						_add(mods, "range", float(e.get("amount", 0.0)) * lv)
				"unit_bonus":
					_add(mods, "max_hp", float(e.get("hp", 0.0)) * lv)
					_add(mods, "damage", float(e.get("damage", 0.0)) * lv)
					_add(mods, "max_mana", float(e.get("mana", 0.0)) * lv)
	if not mods.is_empty() or not u.modifiers(&"tech").is_empty():
		u.set_modifiers(&"tech", mods)


static func _add(mods: Dictionary, k: String, v: float) -> void:
	if v != 0.0:
		mods[k] = float(mods.get(k, 0.0)) + v


## Damage a unit gains per weapon level: its def's `upgrade_damage`, else 10 % of its average
## damage, rounded, at least 1 (rules §5.4).
static func upgrade_damage_of(u: Unit) -> float:
	if u.def.has("upgrade_damage"):
		return float(u.def["upgrade_damage"])
	var dmg: Array = (u.def.get("attack", {}) as Dictionary).get("damage", [0, 0])
	return maxf(1.0, roundf((float(dmg[0]) + float(dmg[1])) * 0.5 * 0.1))
