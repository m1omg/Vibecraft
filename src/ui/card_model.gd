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
## Faction signatures (Levy Horn, Sound the Gong, the worker transforms) join the card when their
## effects exist.

enum State { READY, UNAFFORDABLE, LOCKED, CAPPED, BUSY }

const SLOTS := 12
const PAGE_MAIN := "main"
const PAGE_BASIC := "build_basic"
const PAGE_ADVANCED := "build_advanced"
const RALLY_SLOT := 7
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
	"hero_limit": State.CAPPED, "busy": State.BUSY}


## One card button.
class Entry:
	extends RefCounted
	var slot: int = -1
	var kind: String = ""            ## order, page, build, train, research, upgrade, rally, cancel, back
	var id: String = ""              ## the order, page, def or upgrade id
	var label: String = ""
	var key: String = ""             ## Classic letter ("Esc" for Cancel and Back)
	var action: String = ""          ## Classic input action (unit orders; rebindable)
	var targeted: bool = false
	var state: int = State.READY
	var reason: String = ""          ## error key when not READY (Defs.text("error_" + reason))
	var cost: Dictionary = {}        ## gold, lumber, food, time
	var short: Dictionary = {}       ## gold / lumber -> how much is missing
	var level: int = 0               ## research: the level a press starts
	var levels: int = 0              ## research: how many levels the line has
	var missing: Array[String] = []  ## names of what is missing (LOCKED)
	var hero: bool = false

	func usable() -> bool:
		return state == State.READY

	## What a tooltip or a button redraw depends on (rebuilt only when this changes).
	func signature() -> String:
		return "%s|%s|%d|%s|%s|%s|%d" % [kind, id, state, reason, str(cost), str(short), level]


## The card for `units` (own units of the active subgroup, lead first) on `page`: SLOTS entries,
## null where a slot is empty.
static func build(w: World, pid: int, units: Array[Unit], page: String = PAGE_MAIN) -> Array:
	var card: Array = []
	card.resize(SLOTS)
	if w == null or units.is_empty() or units[0].player_id != pid:
		return card
	var lead := units[0]
	if lead.is_mobile():
		if lead.is_worker and page != PAGE_MAIN:
			_build_page(w, pid, page, card)
		else:
			_unit_card(lead, card)
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


static func _unit_card(lead: Unit, card: Array) -> void:
	for o: Array in ORDERS:
		var e := _command(int(o[0]), "order", str(o[1]), str(o[2]))
		e.action = str(o[2])
		e.key = action_letter(e.action, e.key)
		card[e.slot] = e
	if not lead.is_worker:
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
			card[BUILDING_SLOTS[n]] = _train_entry(w, pid, b, str(did), BUILDING_SLOTS[n])
		n += 1
	for uid: Variant in b.def.get("research", []):
		if n < BUILDING_SLOTS.size():
			card[BUILDING_SLOTS[n]] = _research_entry(w, pid, b, str(uid), BUILDING_SLOTS[n], "research")
		n += 1
	for uid: Variant in b.def.get("upgrades_to", []):
		if n < BUILDING_SLOTS.size():
			card[BUILDING_SLOTS[n]] = _research_entry(w, pid, b, str(uid), BUILDING_SLOTS[n], "upgrade")
		n += 1
	if b.def.get("rally", false):
		card[RALLY_SLOT] = _command(RALLY_SLOT, "rally", "rally", "cmd_rally")
	if not w.production.queue_of(b).is_empty():
		card[CANCEL_SLOT] = _cancel_entry(false)


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
	return out


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
