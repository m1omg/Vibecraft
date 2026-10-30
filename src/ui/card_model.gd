class_name CardModel
extends RefCounted
## The 4 × 3 command card as data (rules §18.4, juice HUD-05): which entry sits in which slot for
## the active subgroup, its Classic letter, its cost and whether it can be used now. CommandCard
## draws it and CommandInput activates it (button or hotkey); both rebuild it from sim state and
## never write that state.
## Unit card: Move, Stop, Hold, Attack, Patrol; workers add Build (B), Build Advanced (V), Gather
## (G), Return Cargo (C, while carrying) and Repair. Build pages list the faction's build_basic /
## build_advanced in data order, with Back (Esc) in slot 11. Building card: train, research and
## building upgrades in data order (a fully researched line leaves its slot empty), Rally in
## slot 7, Cancel (Esc) in slot 11 while something is queued; a site shows Cancel only.
## Heroes: Learn (O) in slot 7 while skill points are unspent, opening the Learn page (the four
## abilities at their bottom-row places with the same letters, Back in slot 7); the main card
## shows the abilities on the bottom row by rank, locked until learned. An altar shows Revive in
## place of a dead hero's train button.
## Faction signatures (Levy Horn, Sound the Gong, the worker transforms) join the card when their
## effects exist.

enum State { READY, UNAFFORDABLE, LOCKED, CAPPED, BUSY }

const SLOTS := 12
const PAGE_MAIN := "main"
const PAGE_BASIC := "build_basic"
const PAGE_ADVANCED := "build_advanced"
const PAGE_LEARN := "learn"
const RALLY_SLOT := 7
const LEARN_SLOT := 7
const ABILITY_ROW := 8           ## abilities.json `slot` 0..3 -> the bottom row (rules §18.4)
const CANCEL_SLOT := 11
## Unit orders: slot, order, command ability (its name, its letter and the Classic action).
const ORDERS: Array = [[0, "move", "cmd_move"], [1, "stop", "cmd_stop"], [2, "hold", "cmd_hold"],
	[3, "attack_move", "cmd_attack"], [4, "patrol", "cmd_patrol"]]
const TARGETED: Array[String] = ["move", "attack_move", "patrol", "gather", "repair", "rally"]
## Slots a building's train / research / upgrade buttons take, in data order.
const BUILDING_SLOTS: Array[int] = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10]
## Error key (Production, Tech) -> availability state.
const STATE_OF: Dictionary = {"": State.READY, "need_gold": State.UNAFFORDABLE,
	"need_lumber": State.UNAFFORDABLE, "requirements": State.LOCKED, "tier": State.LOCKED,
	"cannot_build": State.LOCKED, "cannot_train": State.LOCKED, "queue_full": State.CAPPED,
	"hero_limit": State.CAPPED, "busy": State.BUSY, "not_learned": State.LOCKED,
	"hero_level": State.LOCKED, "max_rank": State.CAPPED, "cooldown": State.BUSY,
	"need_mana": State.UNAFFORDABLE, "silenced": State.LOCKED, "cannot_cast": State.LOCKED}


## One card button.
class Entry:
	extends RefCounted
	var slot: int = -1
	var kind: String = ""            ## order, page, build, train, research, upgrade, rally, cancel,
	                                 ## back, ability, learn, revive
	var id: String = ""              ## the order, page, def or upgrade id
	var label: String = ""
	var key: String = ""             ## Classic letter ("Esc" for Cancel and Back)
	var action: String = ""          ## Classic input action (unit orders; rebindable)
	var targeted: bool = false
	var state: int = State.READY
	var reason: String = ""          ## error key when not READY (Defs.text("error_" + reason))
	var cost: Dictionary = {}        ## gold, lumber, food, time
	var short: Dictionary = {}       ## gold / lumber -> how much is missing
	var level: int = 0               ## research: the level a press starts; ability: its rank; learn:
	                                 ## the rank a press learns; revive: the hero's level
	var levels: int = 0              ## research: how many levels the line has; abilities: ranks
	var uid: int = 0                 ## revive: the dead hero's unit id
	var cooldown_left: float = 0.0   ## abilities: seconds of cooldown left (the sweep)
	var cooldown_total: float = 0.0  ## abilities: the full cooldown in seconds
	var passive: bool = false        ## passive and aura abilities: shown, never pressed
	var missing: Array[String] = []  ## names of what is missing (LOCKED)
	var hero: bool = false

	func usable() -> bool:
		return state == State.READY

	## What a tooltip or a button redraw depends on (rebuilt only when this changes).
	func signature() -> String:
		return "%s|%s|%d|%s|%s|%s|%d|%d" % [kind, id, state, reason, str(cost), str(short), level,
			ceili(cooldown_left)]


## The card for `units` (own units of the active subgroup, lead first) on `page`: SLOTS entries,
## null where a slot is empty.
static func build(w: World, pid: int, units: Array[Unit], page: String = PAGE_MAIN) -> Array:
	var card: Array = []
	card.resize(SLOTS)
	if w == null or units.is_empty():
		return card
	var lead := units[0]
	if lead.player_id != pid:
		if lead.is_structure() and Defs.shops.has(lead.def_id) and lead.player_id >= PlayerState.NEUTRAL_HOSTILE:
			_shop_card(w, pid, lead, card)     # neutral shops serve whoever brings a hero
		return card
	if lead.is_mobile():
		if lead.is_hero and page == PAGE_LEARN:
			_learn_page(w, lead, card)
		elif lead.is_worker and page != PAGE_MAIN and page != PAGE_LEARN:
			_build_page(w, pid, page, card)
		else:
			_unit_card(w, lead, card)
	elif lead.is_building:
		_building_card(w, pid, lead, card)
	return card


static func _entry(slot: int, kind: String, id: String) -> Entry:
	var e := Entry.new()
	e.slot = slot
	e.kind = kind
	e.id = id
	e.targeted = TARGETED.has(id)
	return e


## A card command named by its command ability (label and letter from abilities.json).
static func _command(slot: int, kind: String, id: String, ability_id: String) -> Entry:
	var e := _entry(slot, kind, id)
	var ab: Dictionary = Defs.abilities.get(ability_id, {})
	e.label = str(ab.get("name", id))
	e.key = str(ab.get("hotkey", ""))
	return e


static func _unit_card(w: World, lead: Unit, card: Array) -> void:
	for o: Array in ORDERS:
		var e := _command(int(o[0]), "order", str(o[1]), str(o[2]))
		e.action = str(o[2])
		e.key = action_letter(e.action, e.key)
		card[e.slot] = e
	if lead.is_hero:
		_hero_card(w, lead, card)
		return
	if not lead.is_worker:
		_unit_abilities(w, lead, card)
		return
	if lead.abilities.has("cmd_build_basic"):
		card[5] = _command(5, "page", PAGE_BASIC, "cmd_build_basic")
	if lead.abilities.has("cmd_build_advanced"):
		card[6] = _command(6, "page", PAGE_ADVANCED, "cmd_build_advanced")
	if lead.can_gather():
		card[7] = _command(7, "order", "gather", "cmd_gather")
		if Economy.carry_kind(lead) != "":
			card[8] = _command(8, "order", "return", "cmd_return_cargo")
	var rep := lead.repair_ability()
	if rep != "":
		card[9] = _command(9, "order", "repair", rep)
	_unit_abilities(w, lead, card)


## A unit's own abilities (the faction signatures: Take Up / Lay Down the Flail, Roll the Felt)
## in the free slots of the bottom row, right to left.
static func _unit_abilities(w: World, u: Unit, card: Array) -> void:
	for aid: Variant in u.abilities:
		var id := str(aid)
		if id.begins_with("cmd_") or id == u.repair_ability():
			continue
		var t := str(Defs.ability(id).get("type", ""))
		if t == "passive" or t == "aura" or _has_entry(card, id):
			continue
		for slot: int in [11, 10, 9, 8]:
			if card[slot] == null:
				card[slot] = _own_ability_entry(w, u, id, slot)
				break


## A building's own abilities (Levy Horn, Lay Down Flails, Sound the Gong / All Clear, Unload
## All) in the free building slots.
static func _building_abilities(w: World, b: Unit, card: Array) -> void:
	for aid: Variant in b.abilities:
		var id := str(aid)
		if id.begins_with("cmd_") or _has_entry(card, id):
			continue
		for slot: int in BUILDING_SLOTS:
			if card[slot] == null:
				card[slot] = _own_ability_entry(w, b, id, slot)
				break


static func _has_entry(card: Array, id: String) -> bool:
	for e: Variant in card:
		if e != null and (e as Entry).id == id:
			return true
	return false


static func _own_ability_entry(w: World, u: Unit, id: String, slot: int) -> Entry:
	var ab := Defs.ability(id)
	var e := _entry(slot, "ability", id)
	e.label = str(ab.get("name", id))
	e.key = str(ab.get("hotkey", ""))
	var t := str(ab.get("type", ""))
	e.targeted = t == "target_unit" or t == "target_point"
	if t == "toggle" and id == "clans_sound_the_gong" and w.construction.gong_sounding(u.player_id):
		e.label = str(ab.get("params", {}).get("toggle_name", e.label))
	if t == "command":
		return e
	var err := w.abilities.cast_error(u, id, null, false)
	if err == "cannot_cast" and t == "toggle":
		err = ""
	e.reason = err
	e.state = int(STATE_OF.get(err, State.LOCKED)) if err != "" else State.READY
	e.cooldown_left = w.abilities.cooldown_left(u, id)
	e.cooldown_total = w.abilities.cooldown_total(u, id)
	return e


## The hero's Learn button (while skill points are unspent) and its abilities on the bottom row.
static func _hero_card(w: World, hero: Unit, card: Array) -> void:
	if int(hero.hero.get("skill_points", 0)) > 0:
		card[LEARN_SLOT] = _command(LEARN_SLOT, "page", PAGE_LEARN, "cmd_learn")
	for aid: Variant in hero.def.get("hero_abilities", []):
		var e := _ability_entry(w, hero, str(aid), "ability")
		if e != null:
			card[e.slot] = e


## The Learn page: each ability at its bottom-row place (same letters), Back in slot 7.
static func _learn_page(w: World, hero: Unit, card: Array) -> void:
	for aid: Variant in hero.def.get("hero_abilities", []):
		var e := _ability_entry(w, hero, str(aid), "learn")
		if e != null:
			card[e.slot] = e
	var back := _entry(LEARN_SLOT, "back", "back")
	back.label = Defs.text("card_back")
	back.key = "Esc"
	card[LEARN_SLOT] = back


## A hero ability button: "ability" (its rank; locked until learned) or "learn" (the rank a
## press learns; locked below the rank's hero level, capped at the last rank).
static func _ability_entry(w: World, hero: Unit, aid: String, kind: String) -> Entry:
	var ab := Defs.ability(aid)
	var slot := ABILITY_ROW + int(ab.get("slot", 0))
	if ab.is_empty() or slot < ABILITY_ROW or slot >= SLOTS:
		return null
	var e := _entry(slot, kind, aid)
	e.label = str(ab.get("name", aid))
	e.key = str(ab.get("hotkey", ""))
	e.levels = Defs.ability_levels(aid)
	var rank := w.heroes.rank_of(hero, aid)
	var mana := int(Defs.ability_rank(aid, maxi(rank, 1)).get("mana", 0))
	if mana > 0:
		e.cost["mana"] = mana
	if kind == "ability":
		e.level = rank
		var ab_type := str(ab.get("type", ""))
		e.passive = ab_type == "passive" or ab_type == "aura"
		e.targeted = ab_type == "target_unit" or ab_type == "target_point"
		var err := "not_learned" if rank <= 0 else ("" if e.passive else w.abilities.cast_error(hero, aid, null, false))
		e.reason = err
		e.state = int(STATE_OF.get(err, State.LOCKED)) if err != "" else State.READY
		if err == "need_mana":
			e.short["mana"] = ceili(float(mana) - hero.mana)
		if rank > 0 and not e.passive:
			e.cooldown_left = w.abilities.cooldown_left(hero, aid)
			e.cooldown_total = w.abilities.cooldown_total(hero, aid)
		return e
	e.level = rank + 1
	var err := ""
	if rank >= e.levels:
		err = "max_rank"
	elif not w.heroes.can_learn(hero, aid):
		err = "hero_level"
		e.missing.append(Defs.text("tip_hero_level") % HeroSystem.required_level(aid, rank + 1))
	e.reason = err
	e.state = int(STATE_OF.get(err, State.READY))
	return e


## The dead hero of type `def_id` waiting for revival (its unit id), 0 when none.
static func _dead_hero_of(w: World, pid: int, def_id: String) -> int:
	for hid in w.heroes.dead_heroes(pid):
		if str(w.heroes.dead_record(hid).get("def_id", "")) == def_id:
			return hid
	return 0


static func _revive_entry(w: World, pid: int, b: Unit, hid: int, slot: int) -> Entry:
	var rec := w.heroes.dead_record(hid)
	var did := str(rec.get("def_id", ""))
	var d := Defs.unit(did)
	var e := _entry(slot, "revive", did)
	e.uid = hid
	e.hero = true
	e.label = Defs.text("revive_hero") % str(d.get("name", did))
	e.key = str(d.get("hotkey", ""))
	e.level = int((rec.get("hero", {}) as Dictionary).get("level", 1))
	e.cost = w.heroes.revive_cost(hid).duplicate()
	_shortfall(w, pid, e)
	_set_state(w, pid, e, w.heroes.can_revive(b, hid), 1)
	return e


static func _build_page(w: World, pid: int, page: String, card: Array) -> void:
	var p := w.player(pid)
	var ids: Array = Defs.faction(p.faction).get(page, []) if p != null and p.faction != "" else []
	for i in mini(ids.size(), CANCEL_SLOT):
		var did := str(ids[i])
		var d := Defs.unit(did)
		var e := _entry(i, "build", did)
		e.label = str(d.get("name", did))
		e.key = str(d.get("hotkey", ""))
		e.cost = (d.get("cost", {}) as Dictionary).duplicate()
		var err := w.tech.can_build(pid, did)
		_shortfall(w, pid, e)
		if err == "":
			err = "need_gold" if e.short.has("gold") else ("need_lumber" if e.short.has("lumber") else "")
		_set_state(w, pid, e, err, int(d.get("tier", 1)))
		card[e.slot] = e
	var back := _entry(CANCEL_SLOT, "back", "back")
	back.label = Defs.text("card_back")
	back.key = "Esc"
	card[CANCEL_SLOT] = back


static func _building_card(w: World, pid: int, b: Unit, card: Array) -> void:
	if b.under_construction:
		card[CANCEL_SLOT] = _cancel_entry(true)
		return
	var n := 0
	for did: Variant in b.def.get("trains", []):
		if n < BUILDING_SLOTS.size():
			var dead := _dead_hero_of(w, pid, str(did))
			card[BUILDING_SLOTS[n]] = _revive_entry(w, pid, b, dead, BUILDING_SLOTS[n]) if dead != 0 \
				else _train_entry(w, pid, b, str(did), BUILDING_SLOTS[n])
		n += 1
	for uid: Variant in b.def.get("research", []):
		if n < BUILDING_SLOTS.size():
			card[BUILDING_SLOTS[n]] = _research_entry(w, pid, b, str(uid), BUILDING_SLOTS[n], "research")
		n += 1
	for uid: Variant in b.def.get("upgrades_to", []):
		if n < BUILDING_SLOTS.size():
			card[BUILDING_SLOTS[n]] = _research_entry(w, pid, b, str(uid), BUILDING_SLOTS[n], "upgrade")
		n += 1
	if Defs.shops.has(b.def_id):
		_shop_card(w, pid, b, card)
		return
	if b.def.get("rally", false):
		card[RALLY_SLOT] = _command(RALLY_SLOT, "rally", "rally", "cmd_rally")
	_building_abilities(w, b, card)
	if not w.production.queue_of(b).is_empty():
		card[CANCEL_SLOT] = _cancel_entry(false)


## A shop's card (rules §16, neutrals §5): its stock in data order (price, how many are left,
## locked until available, capped when sold out, "need a hero" while no own hero stands within
## use range), then its services (Fair Exchange trades) and, at an inn, one Revive per dead
## hero. The buyer is the nearest own hero in range (`buyer_for`).
static func _shop_card(w: World, pid: int, shop: Unit, card: Array) -> void:
	var hero := buyer_for(w, pid, shop)
	var n := 0
	for row: Dictionary in w.shops.stock_of(pid, shop):
		if n >= BUILDING_SLOTS.size():
			break
		var iid := str(row["item"])
		var e := _entry(BUILDING_SLOTS[n], "buy", iid)
		e.label = str(Defs.item(iid).get("name", iid))
		e.key = str(row.get("hotkey", ""))
		e.cost = (Defs.item(iid).get("price", {}) as Dictionary).duplicate()
		e.level = int(row["count"])
		e.levels = int(row["max"])
		_shortfall(w, pid, e)
		var err := w.shops.can_buy(pid, shop, iid, hero)
		e.reason = err
		e.state = int(STATE_OF.get(err, State.LOCKED)) if err != "" else State.READY
		if err == "sold_out":
			e.state = State.CAPPED
		elif err == "need_hero" and e.short.is_empty():
			e.state = State.LOCKED
		card[e.slot] = e
		n += 1
	for sid: Variant in Defs.shop(shop.def_id).get("services", []):
		var sv: Dictionary = Defs.services.get(str(sid), {})
		if str(sv.get("kind", "")) == "inn_revive":
			for hid in w.heroes.dead_heroes(pid):
				if n >= BUILDING_SLOTS.size():
					break
				var rec := w.heroes.dead_record(hid)
				var e2 := _entry(BUILDING_SLOTS[n], "inn_revive", str(rec["def_id"]))
				e2.uid = hid
				e2.hero = true
				e2.label = Defs.text("revive_hero") % display_name(str(rec["def_id"]))
				var keys: Array = sv.get("hotkeys", [])
				e2.key = str(keys[mini(n, keys.size() - 1)]) if not keys.is_empty() else ""
				e2.cost = w.heroes.inn_revive_cost(hid).duplicate()
				e2.level = int((rec["hero"] as Dictionary).get("level", 1))
				_shortfall(w, pid, e2)
				e2.state = State.UNAFFORDABLE if not e2.short.is_empty() else State.READY
				card[e2.slot] = e2
				n += 1
			continue
		if n >= BUILDING_SLOTS.size():
			break
		var e3 := _entry(BUILDING_SLOTS[n], "service", str(sid))
		e3.label = str(sv.get("name", sid))
		e3.key = str(sv.get("hotkey", ""))
		e3.cost = (sv.get("give", {}) as Dictionary).duplicate()
		_shortfall(w, pid, e3)
		var err3 := w.shops.can_use_service(pid, shop, str(sid), hero)
		e3.reason = err3
		e3.state = int(STATE_OF.get(err3, State.LOCKED)) if err3 != "" else State.READY
		card[e3.slot] = e3
		n += 1


## The own hero that buys at `shop`: the nearest one within the shop's use range (null: none).
static func buyer_for(w: World, pid: int, shop: Unit) -> Unit:
	var best: Unit = null
	var p := w.player(pid)
	for hid: Variant in p.heroes if p != null else []:
		var h := w.get_unit(int(hid))
		if h != null and h.alive and w.shops.in_use_range(h, shop) \
				and (best == null or h.edge_distance(shop) < best.edge_distance(shop)):
			best = h
	return best


static func _cancel_entry(site: bool) -> Entry:
	var e := _entry(CANCEL_SLOT, "cancel", "site" if site else "queue")
	e.label = Defs.text("card_cancel")
	e.key = "Esc"
	return e


static func _train_entry(w: World, pid: int, b: Unit, did: String, slot: int) -> Entry:
	var d := Defs.unit(did)
	var e := _entry(slot, "train", did)
	e.label = str(d.get("name", did))
	e.key = str(d.get("hotkey", ""))
	e.hero = (d.get("flags", []) as Array).has("hero")
	e.cost = w.production.unit_cost(pid, did).duplicate()
	_shortfall(w, pid, e)
	_set_state(w, pid, e, w.production.can_train(b, did), 1)
	return e


## A research level or a building upgrade; null once a research line is complete.
static func _research_entry(w: World, pid: int, b: Unit, uid: String, slot: int, kind: String) -> Entry:
	var up := Defs.upgrade(uid)
	if up.is_empty():
		return null
	var e := _entry(slot, kind, uid)
	e.levels = (up.get("levels", []) as Array).size()
	e.level = 1 if kind == "upgrade" else w.tech.research_level(pid, uid) + 1
	if e.level > e.levels:
		return null
	e.label = str(up.get("name", uid))
	e.key = str(up.get("hotkey", ""))
	var lv := Defs.upgrade_level(uid, e.level)
	e.cost = (lv.get("cost", {}) as Dictionary).duplicate()
	e.cost["time"] = lv.get("time", 0)
	_shortfall(w, pid, e)
	_set_state(w, pid, e, w.production.can_queue_research(b, uid), int(lv.get("requires_tier", 1)))
	return e


## Fills `e.short` with what the player lacks for `e.cost` (gold, lumber).
static func _shortfall(w: World, pid: int, e: Entry) -> void:
	var p := w.player(pid)
	if p == null:
		return
	var g := int(e.cost.get("gold", 0)) - p.gold
	var l := int(e.cost.get("lumber", 0)) - p.lumber
	if g > 0:
		e.short["gold"] = g
	if l > 0:
		e.short["lumber"] = l


## State from an error key; LOCKED entries list what is missing (`need_tier`: the hall tier the
## entry asks for).
static func _set_state(w: World, pid: int, e: Entry, err: String, need_tier: int) -> void:
	e.reason = err
	e.state = int(STATE_OF.get(err, State.LOCKED))
	if err == "tier":
		var hall := tier_hall(w, pid, need_tier)
		if hall != "":
			e.missing.append(display_name(hall))
	elif err == "requirements":
		for m: Variant in w.tech.missing_requirements(pid, e.id):
			e.missing.append(display_name(str(m)))


## The faction's hall at `tier` (factions.<id>.hall_tiers), "" when unknown.
static func tier_hall(w: World, pid: int, tier: int) -> String:
	var p := w.player(pid)
	var tiers: Array = Defs.faction(p.faction).get("hall_tiers", []) if p != null and p.faction != "" else []
	return str(tiers[tier - 1]) if tier >= 1 and tier <= tiers.size() else ""


## Display name of a unit, building or upgrade id.
static func display_name(id: String) -> String:
	if Defs.units.has(id):
		return str(Defs.units[id].get("name", id))
	return str(Defs.upgrades.get(id, {}).get("name", id))


## The letter bound to an input action ("" when none), else `fallback`.
static func action_letter(action: String, fallback: String = "") -> String:
	if InputMap.has_action(action):
		for ev in InputMap.action_get_events(action):
			if ev is InputEventKey:
				var k := ev as InputEventKey
				return OS.get_keycode_string(k.physical_keycode if k.physical_keycode != KEY_NONE else k.keycode)
	return fallback


## The key shown on a button under the active preset: Grid by position, Classic by letter.
static func display_key(e: Entry) -> String:
	if e == null:
		return ""
	if e.key == "Esc" or Settings.active_hotkey_preset() != "grid":
		return e.key
	return action_letter("card_%d" % e.slot, e.key)


# --- tooltip text --------------------------------------------------------------------------

## Description lines for an entry's tooltip (names and numbers from data, wording from
## data/strings; juice HUD-02).
static func describe(w: World, pid: int, e: Entry) -> Array[String]:
	var out: Array[String] = []
	match e.kind:
		"order", "page", "rally", "back":
			_add_text(out, "tip_" + e.id)
		"cancel":
			_add_text(out, "tip_cancel_" + e.id)
		"build":
			out.append_array(_building_lines(Defs.unit(e.id)))
		"train":
			out.append_array(_unit_lines(Defs.unit(e.id)))
			if e.hero and int(e.cost.get("gold", 0)) == 0:
				_add_text(out, "tip_first_hero_free")
		"research":
			out.append(upgrade_summary(e.id))
			if e.levels > 1:
				out.append(Defs.text("tip_level") % [e.level, e.levels])
		"upgrade":
			out.append_array(_upgrade_lines(e.id))
		"ability", "learn":
			out.append_array(ability_lines(e.id, maxi(e.level, 1)))
			if e.passive and e.kind == "ability":
				_add_text(out, "tip_passive")
			if e.kind == "learn":
				out.append(Defs.text("tip_learn_rank") % [e.level, e.levels])
			elif e.level > 0:
				out.append(Defs.text("tip_rank") % [e.level, e.levels])
			else:
				_add_text(out, "tip_not_learned")
		"revive":
			out.append(Defs.text("tip_revive") % e.level)
		"inn_revive":
			out.append(Defs.text("tip_inn_revive") % e.level)
		"buy":
			out.append_array(item_lines(e.id))
			out.append(Defs.text("tip_stock") % [e.level, e.levels])
			if e.reason == "need_hero":
				out.append(Defs.text("error_need_hero"))
		"service":
			var sv: Dictionary = Defs.services.get(e.id, {})
			var get_: Dictionary = sv.get("get", {})
			for k: String in get_:
				out.append(Defs.text("tip_service_get") % [int(get_[k]), k])
	return out


## What an item does, from its data: the stat bonuses of a permanent item, what a consumable
## restores or grants, its cooldown group.
static func item_lines(iid: String) -> Array[String]:
	var out: Array[String] = []
	var d := Defs.item(iid)
	var key := "item_" + iid.trim_prefix("item_")
	if Defs.strings.has("desc_" + key):
		out.append(Defs.text("desc_" + key))
	var p: Dictionary = d.get("params", {})
	for k: String in p:
		if Defs.strings.has("stat_" + k) and (p[k] is float or p[k] is int):
			out.append(Defs.text("stat_" + k) % _num(float(p[k])))
	if str(d.get("effect", "")) == "recall_to_hall":
		_add_text(out, "tip_recall")
	return out


## An ability's tooltip lines at `rank`: its description (data/strings `ability_<id>`, filled
## with the rank's numbers when it has placeholders) and its cooldown, range and area.
static func ability_lines(aid: String, rank: int) -> Array[String]:
	var out: Array[String] = []
	var v := Defs.ability_rank(aid, rank)
	var key := "ability_" + aid
	if Defs.strings.has(key):
		var shown := {}
		for k: String in v:
			shown[k] = _num(float(v[k])) if v[k] is float or v[k] is int else v[k]
		out.append(Defs.text(key).format(shown))
	var parts: Array[String] = []
	if float(v.get("cooldown", 0.0)) > 0.0:
		parts.append(Defs.text("tip_cooldown") % _num(float(v["cooldown"])))
	if float(v.get("range", 0.0)) > 0.0:
		parts.append(Defs.text("tip_range") % _num(float(v["range"])))
	if float(v.get("area", 0.0)) > 0.0:
		parts.append(Defs.text("tip_area") % _num(float(v["area"])))
	if not parts.is_empty():
		out.append("  ·  ".join(parts))
	return out


## A number for a tooltip: whole numbers without decimals, others with up to two.
static func _num(x: float) -> String:
	return str(roundi(x)) if is_equal_approx(x, roundf(x)) else String.num(x, 2)


static func _add_text(out: Array[String], key: String) -> void:
	if Defs.strings.has(key):
		out.append(Defs.text(key))


static func _building_lines(d: Dictionary) -> Array[String]:
	var out: Array[String] = []
	var food := int(d.get("food_provided", 0))
	if food > 0:
		out.append(Defs.text("tip_gives_food") % food)
	var flags: Array = d.get("flags", [])
	if flags.has("dropoff_gold"):
		out.append(Defs.text("tip_dropoff_both"))
	elif flags.has("dropoff_lumber"):
		out.append(Defs.text("tip_dropoff_lumber"))
	var trains: Array[String] = []
	for t: Variant in d.get("trains", []):
		trains.append(display_name(str(t)))
	if not trains.is_empty():
		out.append(Defs.text("tip_trains") % ", ".join(trains))
	var atk: Dictionary = d.get("attack", {})
	if not atk.is_empty():
		out.append(_attack_line(atk))
	out.append(Defs.text("tip_hp_armor") % [int(d.get("hp", 0)), int(d.get("armor", 0)), str(d.get("armor_type", "fortified")).capitalize()])
	return out


## A building upgrade: the tier it reaches, the food it adds, a weapon it gains, its new HP.
static func _upgrade_lines(uid: String) -> Array[String]:
	var out: Array[String] = []
	var up := Defs.upgrade(uid)
	var from := Defs.unit(str(up.get("from", "")))
	var to := Defs.unit(str(up.get("to", uid)))
	for ef: Dictionary in up.get("effects", []):
		if str(ef.get("type", "")) == "hall_tier":
			out.append(Defs.text("tip_hall_tier") % int(ef.get("tier", 2)))
	var more := int(to.get("food_provided", 0)) - int(from.get("food_provided", 0))
	if more > 0:
		out.append(Defs.text("tip_more_food") % more)
	var atk: Dictionary = to.get("attack", {})
	if not atk.is_empty() and (from.get("attack", {}) as Dictionary).is_empty():
		out.append(_attack_line(atk))
	out.append(Defs.text("tip_hp_armor") % [int(to.get("hp", 0)), int(to.get("armor", 0)), str(to.get("armor_type", "fortified")).capitalize()])
	return out


static func _unit_lines(d: Dictionary) -> Array[String]:
	var out: Array[String] = []
	if (d.get("flags", []) as Array).has("worker"):
		_add_text(out, "tip_worker")
	var atk: Dictionary = d.get("attack", {})
	if not atk.is_empty():
		out.append(_attack_line(atk))
	out.append(Defs.text("tip_hp_armor") % [int(d.get("hp", 0)), int(d.get("armor", 0)), str(d.get("armor_type", "")).capitalize()])
	return out


static func _attack_line(atk: Dictionary) -> String:
	var dmg: Array = atk.get("damage", [0, 0])
	return Defs.text("tip_attack") % [str(atk.get("type", "")).capitalize(), int(dmg[0]), int(dmg[1]),
		float(atk.get("range", 0.0))]


## One line on what a research does: data `summary`, except weapon lines, whose numbers come from
## each unit's `upgrade_damage` (rules §5.4).
static func upgrade_summary(uid: String) -> String:
	var up := Defs.upgrade(uid)
	for ef: Dictionary in up.get("effects", []):
		if str(ef.get("type", "")) != "upgrade_damage":
			continue
		var parts: Array[String] = []
		for u: Variant in ef.get("units", []):
			parts.append("%s +%d" % [display_name(str(u)), int(Tech.upgrade_damage_for(Defs.unit(str(u))))])
		return Defs.text("tip_upgrade_damage") % ", ".join(parts)
	return str(up.get("summary", ""))
