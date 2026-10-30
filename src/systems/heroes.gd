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
##   - death bookkeeping (PlayerState.heroes keeps dead heroes' ids; `_dead` keeps their
##     records), altar revive (cost/time formulas; a Production queue entry of kind "revive")
##     and inn revive (instant, 50 % HP, 0 mana; with the shops)
## Signals (Events): hero_level_up(u), xp_gained(u, amount), ability_learned(u, ability, rank),
##   hero_died(u), hero_revived(u).
## Commands handled: "revive" {units: [altar or inn], target: hero record index / unit id}.
## Called by: orders/learn.gd (can_learn, learn), AbilitySystem (rank_of), ItemSystem
##   (add_attributes, add_xp, retrain), Production (can_acquire / hero slots), HUD, AI.

var _dead: Dictionary = {}   ## dead hero's unit id -> {def_id, player, hero, inventory, cooldowns, autocast, died_tick}


func hooks() -> Array[StringName]:
	return [&"spawned", &"died"]


func on_unit_spawned(u: Unit) -> void:
	if not u.is_hero or not u.hero.is_empty():
		return
	var hid := str(u.def.get("hero_id", u.def_id))
	u.hero = {"hero_id": hid, "level": 1, "xp": 0.0,
		"skill_points": int(Defs.rule("heroes.skill_points_start", 1)), "ranks": {},
		"attr_bonus": {"str": 0, "agi": 0, "int": 0}, "proper_name": _pick_name(u, hid)}
	var p := world.player(u.player_id)
	if p != null and not p.heroes.has(u.id):
		p.heroes.append(u.id)
	apply_attributes(u)


## A proper name from the hero's list (rules §6.1), picked by the match seed and the unit id so
## the shared random stream is not consumed.
func _pick_name(u: Unit, hid: String) -> String:
	var names: Array = Defs.heroes.get(hid, {}).get("proper_names", [])
	if names.is_empty():
		return ""
	return str(names[absi(hash([world.rng.seed, u.id])) % names.size()])


## "Title: Name" (rules §6.1); a name that already starts with the title ("Firewright Vit
## Sootwick") stands alone; the title alone when the hero has no proper name.
static func display_name(u: Unit) -> String:
	return title_and_name(u.hero if not u.hero.is_empty() else {"hero_id": u.def_id})


static func title_and_name(hero: Dictionary) -> String:
	var d: Dictionary = Defs.heroes.get(str(hero.get("hero_id", "")), {})
	var title := str(d.get("title", d.get("name", hero.get("hero_id", ""))))
	var proper := str(hero.get("proper_name", ""))
	if proper == "":
		return title
	return proper if proper.begins_with(title + " ") else "%s: %s" % [title, proper]


## Kill XP (rules §6.3–§6.4) and the dead hero's record for revival.
func on_unit_died(u: Unit, killer: Unit) -> void:
	if u.is_hero:
		_dead[u.id] = {"def_id": u.def_id, "player": u.player_id, "hero": u.hero.duplicate(true),
			"inventory": u.inventory.duplicate(true), "cooldowns": u.cooldowns.duplicate(),
			"autocast": u.autocast.duplicate(), "died_tick": world.tick_count}
		Events.hero_died.emit(u)
		Events.notification.emit(u.player_id, "hero_died", Defs.text("notice_hero_died") % display_name(u))
	award_kill_xp(u, killer)


## Base XP a kill of `victim` is worth before sharing (rules §6.3): the unit or hero table by the
## victim's level, 50 % for summons; structures only when they attack; critters nothing.
func kill_xp_base(victim: Unit) -> float:
	if victim.has_flag("critter") or victim.is_item or victim.is_resource:
		return 0.0
	if victim.is_structure() and victim.damage_max <= 0:
		return 0.0
	var table: Array = Defs.rule("xp.hero_kill" if victim.is_hero else "xp.unit_kill", [])
	if table.is_empty():
		return 0.0
	var base := float(table[clampi(victim.level, 1, table.size()) - 1])
	if victim.is_summoned:
		base *= float(Defs.rule("xp.summon_factor", 0.5))
	return base


## Heroes of `pid` that share a kill of `victim`: alive, below the level cap, within
## xp.share_radius edge to edge (rules §6.4), in acquisition order.
func eligible_heroes(pid: int, victim: Unit) -> Array[Unit]:
	var out: Array[Unit] = []
	var p := world.player(pid)
	if p == null:
		return out
	var cap := int(Defs.rule("heroes.level_cap", 10))
	var r := float(Defs.rule("xp.share_radius", 18.75))
	var anywhere := str(Defs.rule("xp.no_hero_in_range", "lost")) == "all_heroes"
	var far: Array[Unit] = []
	for hid: int in p.heroes:
		var h := world.get_unit(hid)
		if h == null or not h.alive or level_of(h) >= cap:
			continue
		if h.edge_distance(victim) <= r:
			out.append(h)
		elif anywhere:
			far.append(h)
	return out if not out.is_empty() else far


## The receiving hero's creep factor (rules §6.3): 80 / 70 / 60 / 50 % at levels 1–4, then 0.
func creep_factor(h: Unit) -> float:
	var f: Array = Defs.rule("xp.creep_factor", [1.0])
	return float(f[clampi(level_of(h), 1, f.size()) - 1])


## +15 % at tier 2, +30 % at tier 3 for a player who owns exactly one hero, alive or dead
## (rules §6.4 step 5; never on flat XP).
func single_hero_bonus(pid: int) -> float:
	var p := world.player(pid)
	if p == null or p.heroes.size() != 1:
		return 0.0
	var b: Array = Defs.rule("xp.single_hero_bonus", [0.0])
	return float(b[clampi(world.tech.tier(pid), 1, b.size()) - 1])


## Splits a kill's XP among the killer's owner's eligible heroes (rules §6.4). Nothing for a
## structure's killing blow, a deny, a neutral killer or with no hero in range (the XP is lost).
## XP is a float: shares and factors are never rounded.
func award_kill_xp(victim: Unit, killer: Unit) -> void:
	if killer == null or killer.is_structure():
		return
	var pid := killer.player_id
	var p := world.player(pid)
	if p == null or p.is_neutral() or not world.is_enemy(pid, victim.player_id):
		return
	var base := kill_xp_base(victim)
	if base <= 0.0:
		return
	var hs := eligible_heroes(pid, victim)
	if hs.is_empty():
		return
	var share := base / hs.size()
	var bonus := 1.0 + single_hero_bonus(pid)
	var creep := victim.player_id == PlayerState.NEUTRAL_HOSTILE
	for h in hs:
		var amount := share * bonus * (creep_factor(h) if creep else 1.0)
		var lv := level_of(h)
		add_xp(h, amount)
		if amount > 0.0:
			Events.hero_xp_gained.emit(h, amount, victim.pos, level_of(h) - lv)


## XP ratio within the hero's current level (1 at the cap): the hero bar and the sigil's arc.
static func xp_ratio(hero: Dictionary) -> float:
	var lv := int(hero.get("level", 1))
	if lv >= int(Defs.rule("heroes.level_cap", 10)):
		return 1.0
	var lo := Defs.xp_for_level(lv)
	var hi := Defs.xp_for_level(lv + 1)
	return clampf((float(hero.get("xp", 0.0)) - lo) / maxf(hi - lo, 1.0), 0.0, 1.0)


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


## Hero level that rank `rank` of `ability_id` needs (rules §6.5): normal ranks 1 / 3 / 5, the
## ultimate 6.
static func required_level(ability_id: String, rank: int) -> int:
	if Defs.ability(ability_id).get("ultimate", false):
		return int(Defs.rule("heroes.ultimate_level", 6))
	var gates: Array = Defs.rule("heroes.rank_levels", [1, 3, 5])
	return int(gates[clampi(rank, 1, gates.size()) - 1])


## Can `u` put a point into `ability_id` now (point available, in its kit, rank gate)?
func can_learn(u: Unit, ability_id: String) -> bool:
	if not u.is_hero or int(u.hero.get("skill_points", 0)) <= 0:
		return false
	if not (u.def.get("hero_abilities", []) as Array).has(ability_id):
		return false
	var next := rank_of(u, ability_id) + 1
	if next > Defs.ability_levels(ability_id):
		return false
	return level_of(u) >= required_level(ability_id, next)


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


## Dead heroes of `pid` awaiting revival (unit ids, acquisition order).
func dead_heroes(pid: int) -> Array[int]:
	var out: Array[int] = []
	var p := world.player(pid)
	if p == null:
		return out
	for hid: int in p.heroes:
		if _dead.has(hid):
			out.append(hid)
	return out


## The record kept for dead hero `hid` ({} when it is not dead).
func dead_record(hid: int) -> Dictionary:
	return _dead.get(hid, {})


## Altar revive (rules §6.7): gold `floor(cost_gold × (0.40 + 0.10 × (L − 1)))` up to 550, time
## `train_time × L × 0.65` s up to min(110, 2 × train_time), 5 food. Percentages are summed in
## whole hundredths so the gold never suffers float error.
func revive_cost(hid: int) -> Dictionary:
	var rec := dead_record(hid)
	if rec.is_empty():
		return {}
	var r: Dictionary = Defs.rule("heroes.revive", {})
	var cost: Dictionary = Defs.unit(str(rec["def_id"])).get("cost", {})
	var lv := int((rec["hero"] as Dictionary).get("level", 1))
	var pct := roundi(float(r.get("gold_base", 0.4)) * 100.0) + roundi(float(r.get("gold_per_level", 0.1)) * 100.0) * (lv - 1)
	var gold := mini(int(cost.get("gold", 425)) * pct / 100, int(r.get("gold_max", 550)))
	var train := float(cost.get("time", Defs.rule("heroes.train_time", 55.0)))
	var t := minf(train * lv * float(r.get("time_factor", 0.65)),
		minf(float(r.get("time_max", 110.0)), float(r.get("time_max_train_factor", 2.0)) * train))
	return {"gold": gold, "lumber": 0, "food": int(cost.get("food", 5)), "time": t}


## "" when `building` can start reviving dead hero `hid`, else an error key (cannot_train,
## busy, queue_full, need_gold).
func can_revive(building: Unit, hid: int) -> String:
	var rec := dead_record(hid)
	if rec.is_empty() or int(rec["player"]) != building.player_id or building.under_construction:
		return "cannot_train"
	if not (building.def.get("trains", []) as Array).has(str(rec["def_id"])):
		return "cannot_train"
	if world.production.is_reviving(hid) or world.production.is_upgrading(building):
		return "busy"
	if world.production.queue_of(building).size() >= int(Defs.rule("economy.production_queue", 7)):
		return "queue_full"
	var p := world.player(building.player_id)
	if p == null or p.gold < int(revive_cost(hid).get("gold", 0)):
		return "need_gold"
	return ""


## The revive finished at `building`: the hero returns beside it with its level, XP, skills,
## items and running cooldowns, full HP and min(max mana, 100) mana (rules §6.7), takes its old
## place in the acquisition order and walks to the rally point.
func complete_revive(building: Unit, hid: int) -> Unit:
	var rec := dead_record(hid)
	if rec.is_empty():
		return null
	var u := world.spawn_unit(str(rec["def_id"]), building.player_id,
		world.production.spawn_point(building, building.rally_pos), 0.0, {"food_reserved": true})
	if u == null:
		return null
	_dead.erase(hid)
	u.hero = (rec["hero"] as Dictionary).duplicate(true)
	u.inventory = (rec["inventory"] as Array).duplicate(true)
	u.cooldowns = (rec["cooldowns"] as Dictionary).duplicate()
	u.autocast = (rec["autocast"] as Dictionary).duplicate()
	apply_attributes(u)
	var r: Dictionary = Defs.rule("heroes.revive", {})
	u.hp = u.max_hp * float(r.get("hp", 1.0))
	u.mana = minf(u.max_mana, float(r.get("mana_flat", 100)))
	var p := world.player(u.player_id)
	if p != null:
		p.heroes.erase(u.id)
		var i := p.heroes.find(hid)
		if i >= 0:
			p.heroes[i] = u.id
		else:
			p.heroes.append(u.id)
	Events.hero_revived.emit(u)
	Events.notification.emit(u.player_id, "hero_revived", Defs.text("notice_hero_revived") % display_name(u))
	return u


## "revive" {units: [altar], hero: dead hero's unit id}: queues the revive at the first altar
## that can take it (paid now, like training).
func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
	if str(cmd.get("type", "")) != "revive":
		return false
	var hid := int(cmd.get("hero", 0))
	var err := "cannot_train"
	for b in units:
		err = can_revive(b, hid)
		if err == "":
			return world.production.queue_revive(b, hid, revive_cost(hid))
	if not units.is_empty() and err != "":
		Events.notification.emit(units[0].player_id, "error_" + err, Defs.text("error_" + err))
	return false
