extends Node
## Loads every data/*.json definition table, fills defaults and validates fields and cross
## references. Gameplay code reads stats only through these accessors (no hardcoded unit stats).
## Every field is documented in data/SCHEMA.md; the loading contract is docs/architecture.md §1/§3.
##
## Tables (all Dictionary id -> def unless noted):
##   units      every entity def: units.json + buildings.json + one derived def per hero (+ test defs)
##   buildings  the structure subset of `units` (kind building / resource)
##   heroes     heroes.json "heroes" (raw hero data: attributes, growth, kit)
##   abilities, buffs, ground_effects, items, upgrades, shops, services, camps, factions, doodads
##   combat, upkeep (Array), team_colours (Array), rules (deep merge of every file's "rules" block),
##   strings (data/strings/en.json)
## Files may carry a top-level "rules" block; Defs deep-merges them into `rules` (a key defined in
## two files is a validation error). Keys starting with "_" are comments and are skipped.

const DATA_DIR := "res://data/"
const TEST_DEFS_FILE := "test_defs.json"
const STRINGS_FILE := "strings/en.json"
const UNIT_KINDS: Array[String] = ["unit", "building", "resource", "item"]
const ABILITY_TYPES: Array[String] = ["target_unit", "target_point", "target_unit_or_point", "instant",
	"passive", "aura", "toggle", "command"]
const ITEM_CLASSES: Array[String] = ["purchasable", "powerup", "permanent", "charged", "artifact"]
const UPGRADE_KINDS: Array[String] = ["research", "building_upgrade"]
const BUFF_POLARITIES: Array[String] = ["positive", "negative", "neutral"]
const BUFF_KINDS: Array[String] = ["magic", "physical", "aura", "ultimate", "passive", "item"]
## Fixed letters of every mobile unit's card (Move, Stop, Hold, Attack, Patrol; rules §18.4).
const UNIT_CARD_KEYS: Array[String] = ["M", "S", "H", "A", "P"]
const HERO_LEARN_KEY := "O"
const RALLY_KEY := "R"
## Rank-independent ability fields that ability_rank() copies into the resolved rank dict.
const ABILITY_RANK_FIELDS: Array[String] = ["mana", "cooldown", "range", "area", "duration",
	"cast_point", "cast_backswing", "channel"]

## Applied to every entity def before validation so code can index fields without has() checks.
const UNIT_DEFAULTS: Dictionary = {
	"mana": 0, "armor": 0, "armor_type": "unarmored", "speed": 0.0, "turn_rate": -1.0,
	"sight": 10.0, "sight_night": -1.0, "height": 1.5, "shape": "humanoid", "model": "", "flags": [],
	"abilities": [], "attack": {}, "cost": {}, "footprint": [0, 0], "trains": [], "research": [],
	"upgrades_to": [], "requires": [], "food_provided": 0, "weapon": "none", "roof": "pyramid",
	"scale": 1.0, "class": "", "faction": "", "level": -1, "hp_regen": -1.0, "mana_regen": -1.0,
	"mana_start": -1.0, "model_fit": "", "blocks_pathing": true, "hotkey": "",
}

var units: Dictionary = {}
var buildings: Dictionary = {}
var heroes: Dictionary = {}
var abilities: Dictionary = {}
var buffs: Dictionary = {}
var ground_effects: Dictionary = {}
var items: Dictionary = {}
var upgrades: Dictionary = {}
var shops: Dictionary = {}
var services: Dictionary = {}
var camps: Dictionary = {}
var doodads: Dictionary = {}
var factions: Dictionary = {}
var combat: Dictionary = {}
var upkeep: Array = []
var team_colours: Array = []
var rules: Dictionary = {}
var strings: Dictionary = {}
var errors: Array[String] = []
## True once load_test_defs() merged data/test_defs.json (tests and the sandbox scenario only).
var test_defs_loaded: bool = false
## Largest acquisition target radius over all unit defs: footprint half-diagonal for
## structures, radius for units. Pads target queries (see `target_radius`).
var max_target_radius: float = 0.0
## Largest radius of a mobile unit def (separation neighbour queries need no more padding).
var max_unit_radius: float = 0.0
var _combat_defaults: Dictionary = {}
var _warned: Dictionary = {}
var _rank_cache: Dictionary = {}
var _trained_at: Dictionary = {}     ## unit id -> [building ids]
var _researched_at: Dictionary = {}  ## upgrade id -> [building ids]
var _rule_owner: Dictionary = {}     ## rules leaf path -> file that defined it
var _prd: Dictionary = {}


func _ready() -> void:
	reload()


## Merges data/test_defs.json (the dummy_* placeholder defs) into the tables. Called by the test
## runner and the sandbox scenario; gameplay data never references test ids.
func load_test_defs() -> void:
	if test_defs_loaded:
		return
	test_defs_loaded = true
	reload()


func reload() -> void:
	errors.clear()
	_warned.clear()
	_rank_cache.clear()
	_rule_owner.clear()
	rules = {}
	var fac := _load_file("factions.json")
	_take_rules(fac, "factions.json")
	factions = _section(fac, "factions")
	combat = fac.get("combat", {})
	upkeep = fac.get("upkeep", [])
	team_colours = fac.get("team_colours", [])
	_combat_defaults = combat.get("defaults", {})
	var unit_table := _table(_load_file("units.json"))
	var building_table := _table(_load_file("buildings.json"))
	var hero_file := _load_file("heroes.json")
	_take_rules(hero_file, "heroes.json")
	heroes = _section(hero_file, "heroes")
	abilities = _table(_load_file("abilities.json"))
	var buff_file := _load_file("buffs.json")
	_take_rules(buff_file, "buffs.json")
	buffs = _section(buff_file, "buffs")
	ground_effects = _section(buff_file, "ground_effects")
	var item_file := _load_file("items.json")
	_take_rules(item_file, "items.json")
	items = _section(item_file, "items")
	upgrades = _table(_load_file("upgrades.json"))
	var shop_file := _load_file("shops.json")
	_take_rules(shop_file, "shops.json")
	shops = _section(shop_file, "shops")
	services = _section(shop_file, "services")
	var camp_file := _load_file("creep_camps.json")
	_take_rules(camp_file, "creep_camps.json")
	camps = _section(camp_file, "camps")
	doodads = _table(_load_file("doodads.json"))
	strings = _table(_load_file(STRINGS_FILE))
	if test_defs_loaded:
		var t := _load_file(TEST_DEFS_FILE)
		for key: String in ["units", "abilities", "items", "upgrades", "factions"]:
			var dst: Dictionary = {"units": unit_table, "abilities": abilities, "items": items,
				"upgrades": upgrades, "factions": factions}[key]
			var src: Dictionary = t.get(key, {})
			for id: String in src:
				if dst.has(id):
					errors.append("test def '%s' collides with a real %s id" % [id, key])
				dst[id] = src[id]
	units = {}
	buildings = {}
	for id: String in unit_table:
		units[id] = unit_table[id]
	for id: String in building_table:
		if units.has(id):
			errors.append("id '%s' is defined in units.json and buildings.json" % id)
		units[id] = building_table[id]
		buildings[id] = building_table[id]
	for id: String in heroes:
		if units.has(id):
			errors.append("hero id '%s' collides with a unit or building id" % id)
		units[id] = _hero_unit_def(id, heroes[id])
	_prepare_units()
	_index_production()
	_validate_abilities()
	_validate_buffs()
	_validate_items()
	_validate_upgrades()
	_validate_heroes()
	_validate_shops()
	_validate_camps()
	_validate_factions()
	_validate_simple(doodads, "doodad", ["name", "lumber", "shape"])
	_validate_cards()
	for e in errors:
		push_error("Defs: " + e)


# --- accessors -----------------------------------------------------------------------------

func unit(id: String) -> Dictionary:
	return _lookup(units, id, "unit")


func building(id: String) -> Dictionary:
	return _lookup(buildings, id, "building")


func hero(id: String) -> Dictionary:
	return _lookup(heroes, id, "hero")


func ability(id: String) -> Dictionary:
	return _lookup(abilities, id, "ability")


func buff(id: String) -> Dictionary:
	return _lookup(buffs, id, "buff")


func ground_effect(id: String) -> Dictionary:
	return _lookup(ground_effects, id, "ground effect")


func item(id: String) -> Dictionary:
	return _lookup(items, id, "item")


func upgrade(id: String) -> Dictionary:
	return _lookup(upgrades, id, "upgrade")


func shop(id: String) -> Dictionary:
	return _lookup(shops, id, "shop")


func service(id: String) -> Dictionary:
	return _lookup(services, id, "service")


func camp(id: String) -> Dictionary:
	return _lookup(camps, id, "camp")


func doodad(id: String) -> Dictionary:
	return _lookup(doodads, id, "doodad")


func faction(id: String) -> Dictionary:
	return _lookup(factions, id, "faction")


func has_unit(id: String) -> bool:
	return units.has(id)


func unit_ids() -> Array:
	return units.keys()


## Combat tuning value from factions.json → combat.defaults.
func combat_default(key: String, fallback: Variant) -> Variant:
	return _combat_defaults.get(key, fallback)


## Global rule by dotted path, e.g. `Defs.rule("economy.gold_per_trip", 10)` (rules.md §20).
func rule(path: String, fallback: Variant = null) -> Variant:
	var cur: Variant = rules
	for part in path.split("."):
		if cur is Dictionary and (cur as Dictionary).has(part):
			cur = cur[part]
		else:
			return fallback
	return cur


## UI text for a string key (data/strings/en.json); the key itself when missing.
func text(key: String) -> String:
	return str(strings.get(key, key))


## Ability values for one rank (1-based): the top-level fields (mana, cooldown, range, area,
## duration, cast_point, cast_backswing, channel), then `params`, then `ranks[rank - 1]` on top.
## Cached; treat the result as read-only.
func ability_rank(id: String, rank: int = 1) -> Dictionary:
	var key := "%s#%d" % [id, rank]
	if _rank_cache.has(key):
		return _rank_cache[key]
	var a := ability(id)
	if a.is_empty():
		return {}
	var out := {}
	for f: String in ABILITY_RANK_FIELDS:
		if a.has(f):
			out[f] = a[f]
	if not out.has("cast_point"):
		out["cast_point"] = combat_default("cast_point", 0.3)
	if not out.has("cast_backswing"):
		out["cast_backswing"] = combat_default("cast_backswing", 0.5)
	out.merge(a.get("params", {}), true)
	var ranks: Array = a.get("ranks", [])
	if not ranks.is_empty():
		out.merge(ranks[clampi(rank, 1, ranks.size()) - 1], true)
	out["rank"] = rank
	out["id"] = id
	_rank_cache[key] = out
	return out


## Number of ranks an ability can be learned to (heroes 3, ultimates 1, others 1).
func ability_levels(id: String) -> int:
	var a := ability(id)
	return maxi(1, int(a.get("levels", (a.get("ranks", [{}]) as Array).size())))


## One research / upgrade level (1-based): {cost, time, requires_tier}.
func upgrade_level(id: String, level: int = 1) -> Dictionary:
	var lv: Array = upgrade(id).get("levels", [])
	if lv.is_empty():
		return {}
	return lv[clampi(level, 1, lv.size()) - 1]


## Buildings whose card trains `unit_id` (heroes included).
func trained_at(unit_id: String) -> Array:
	return _trained_at.get(unit_id, [])


## Buildings whose card researches `upgrade_id` (building upgrades: the `from` building).
func researched_at(upgrade_id: String) -> Array:
	return _researched_at.get(upgrade_id, [])


## Hero attributes and derived stats at `level` (rules §6.6). `bonus` adds flat attribute points
## ({str, agi, int}, from items and power-ups). Returns {str, agi, int, hp, mana, armor,
## damage_min, damage_max, cooldown, hp_regen, mana_regen, primary}. The single formula the
## heroes system uses.
func hero_stats(hero_id: String, level: int = 1, bonus: Dictionary = {}) -> Dictionary:
	var h: Dictionary = heroes.get(hero_id, {})
	if h.is_empty():
		return {}
	var r: Dictionary = rules.get("heroes", {})
	var attrs: Dictionary = h.get("attributes", {})
	var out := {"primary": str(h.get("primary", "str"))}
	for k: String in ["str", "agi", "int"]:
		var ag: Array = attrs.get(k, [0, 0])
		out[k] = floori(float(ag[0]) + float(ag[1]) * (level - 1)) + int(bonus.get(k, 0))
	var s: int = out["str"]
	var a: int = out["agi"]
	var i: int = out["int"]
	var p: int = out[out["primary"]]
	var bd: Array = h.get("base_damage", [1, 1])
	out["hp"] = float(r.get("base_hp", 100)) + float(r.get("str_hp", 25)) * s
	out["mana"] = float(r.get("int_mana", 15)) * i
	out["armor"] = float(h.get("base_armor", 0)) + float(r.get("agi_armor", 0.3)) * a
	out["damage_min"] = int(bd[0]) + int(r.get("primary_damage", 1)) * p
	out["damage_max"] = int(bd[1]) + int(r.get("primary_damage", 1)) * p
	out["cooldown"] = float(h.get("base_cooldown", 2.0)) / (1.0 + float(r.get("agi_attack_speed", 0.02)) * a)
	out["hp_regen"] = float(r.get("base_hp_regen", 0.25)) + float(r.get("str_hp_regen", 0.05)) * s
	out["mana_regen"] = float(r.get("base_mana_regen", 0.01)) + float(r.get("int_mana_regen", 0.05)) * i
	return out


## Total XP needed to reach `level` (rules §6.2).
func xp_for_level(level: int) -> float:
	var t: Array = rule("heroes.xp_levels", [0])
	return float(t[clampi(level, 1, t.size()) - 1])


## Hero level for an XP total (capped at rules.heroes.level_cap).
func level_for_xp(xp: float) -> int:
	var t: Array = rule("heroes.xp_levels", [0])
	var lv := 1
	for i in t.size():
		if xp >= float(t[i]):
			lv = i + 1
	return mini(lv, int(rule("heroes.level_cap", t.size())))


## Pseudo-random-distribution constant C for a nominal proc chance p (rules §2.3): the chance on
## the N-th try is min(1, C × N). 60-step bisection, cached.
func prd_c(p: float) -> float:
	if p <= 0.0:
		return 0.0
	if p >= 1.0:
		return 1.0
	var key := snappedf(p, 0.0001)
	if _prd.has(key):
		return _prd[key]
	var lo := 0.0
	var hi := p
	for step in 60:
		var mid := (lo + hi) * 0.5
		if _prd_rate(mid) < p:
			lo = mid
		else:
			hi = mid
	_prd[key] = (lo + hi) * 0.5
	return _prd[key]


static func _prd_rate(c: float) -> float:
	# long-run success rate of PRD with constant c: 1 / E[tries]
	var expected := 0.0
	var survive := 1.0
	var n := 1
	while survive > 1e-12 and n < 10000:
		var pn := minf(1.0, c * n)
		expected += n * survive * pn
		survive *= 1.0 - pn
		n += 1
	return 1.0 / expected if expected > 0.0 else 0.0


## Every effect id referenced by abilities and items (the effect registry must resolve them).
func effect_ids() -> Array:
	var out: Array = []
	for t: Dictionary in [abilities, items]:
		for id: String in t:
			var e := str((t[id] as Dictionary).get("effect", ""))
			if e != "" and not out.has(e):
				out.append(e)
	out.sort()
	return out


## How far a unit's centre can be from the nearest point of its body: the footprint
## half-diagonal for structures (edge distances are measured to the footprint rectangle),
## the radius otherwise.
static func target_radius(d: Dictionary) -> float:
	if d.get("kind", "unit") != "unit":
		var fp: Array = d.get("footprint", [0, 0])
		if fp.size() == 2:
			return Vector2(float(fp[0]), float(fp[1])).length() * Grid.CELL * 0.5
	return float(d.get("radius", 0.0))


static func load_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	var text_data := FileAccess.get_file_as_string(path)
	var json := JSON.new()
	if json.parse(text_data) != OK:
		push_error("JSON parse error in %s line %d: %s" % [path, json.get_error_line(),
			json.get_error_message()])
		return null
	return json.data


# --- loading -------------------------------------------------------------------------------

func _load_file(file_name: String) -> Dictionary:
	var data: Variant = load_json(DATA_DIR + file_name)
	if data == null:
		errors.append("missing or invalid %s" % file_name)
		return {}
	if not data is Dictionary:
		errors.append("%s must contain a JSON object" % file_name)
		return {}
	return data


## A flat id -> def table without comment keys.
func _table(d: Dictionary) -> Dictionary:
	var out := {}
	for k: String in d:
		if not k.begins_with("_") and d[k] is Dictionary:
			out[k] = d[k]
	return out


func _section(d: Dictionary, key: String) -> Dictionary:
	return _table(d.get(key, {}))


func _take_rules(d: Dictionary, file_name: String) -> void:
	var r: Variant = d.get("rules", {})
	if r is Dictionary:
		_merge_rules(rules, r, "", file_name)


func _merge_rules(dst: Dictionary, src: Dictionary, prefix: String, file_name: String) -> void:
	for k: String in src:
		var path := prefix + k
		if src[k] is Dictionary and dst.get(k) is Dictionary:
			_merge_rules(dst[k], src[k], path + ".", file_name)
		elif src[k] is Dictionary and not dst.has(k):
			dst[k] = {}
			_merge_rules(dst[k], src[k], path + ".", file_name)
		else:
			if dst.has(k):
				errors.append("rule '%s' defined in %s and %s" % [path, _rule_owner.get(path, "?"), file_name])
			dst[k] = src[k]
			_rule_owner[path] = file_name


func _lookup(table: Dictionary, id: String, kind: String) -> Dictionary:
	if table.has(id):
		return table[id]
	var key := kind + ":" + id
	if not _warned.has(key):
		_warned[key] = true
		push_warning("Defs: unknown %s '%s'" % [kind, id])
	return {}


## Unit def for a hero at level 1, derived from its attributes (rules §6.6).
func _hero_unit_def(id: String, h: Dictionary) -> Dictionary:
	var r: Dictionary = rules.get("heroes", {})
	var st := hero_stats(id, 1)
	var sight: Array = r.get("sight", [28.1, 12.5])
	var attack := {"type": str(h.get("attack_type", "heroic")),
		"damage": [st.get("damage_min", 1), st.get("damage_max", 1)],
		"cooldown": st.get("cooldown", 2.0), "range": float(h.get("range", 1.0)),
		"targets": h.get("targets", ["ground"]), "acquire": float(r.get("acquire", 9.4))}
	if h.has("projectile"):
		attack["projectile"] = h["projectile"]
	return {
		"name": str(h.get("name", id)), "kind": "unit", "faction": str(h.get("faction", "")),
		"class": str(h.get("class", "hero_melee")), "level": 1, "hero_id": id,
		"flags": ["ground", "organic", "hero"], "hp": st.get("hp", 100.0), "mana": st.get("mana", 0.0),
		"mana_start": st.get("mana", 0.0), "armor": st.get("armor", 0.0),
		"armor_type": str(h.get("armor_type", "hero")), "radius": float(r.get("radius", 0.55)),
		"speed": float(h.get("speed", 4.5)), "sight": float(sight[0]), "sight_night": float(sight[1]),
		"height": float(h.get("height", 2.2)), "shape": "humanoid", "weapon": str(h.get("weapon", "sword")),
		"model": str(h.get("model", "")), "hotkey": str(h.get("hotkey", "")),
		"cost": h.get("cost", {}), "abilities": [], "hero_abilities": h.get("abilities", []),
		"hp_regen": st.get("hp_regen", 0.25), "mana_regen": st.get("mana_regen", 0.0), "attack": attack,
	}


func _prepare_units() -> void:
	max_target_radius = 0.0
	max_unit_radius = 0.0
	for id: String in units:
		var d: Dictionary = units[id]
		for k: String in UNIT_DEFAULTS:
			if not d.has(k):
				d[k] = UNIT_DEFAULTS[k].duplicate() if UNIT_DEFAULTS[k] is Array else UNIT_DEFAULTS[k]
		d["id"] = id
		_prepare_derived(d)
		_prepare_attack(d)
		_validate_unit(id, d)
		max_target_radius = maxf(max_target_radius, target_radius(d))
		if d.get("kind") == "unit":
			max_unit_radius = maxf(max_unit_radius, float(d.get("radius", 0.0)))


## Fills values whose default depends on the def: class turn rate, night sight, XP level, regen,
## start mana and the model fit (rules §4.4, §7.5, §9, §14.2).
func _prepare_derived(d: Dictionary) -> void:
	var timing: Dictionary = (combat.get("class_timings", {}) as Dictionary).get(str(d["class"]), {})
	var flags: Array = d["flags"]
	var structure: bool = d.get("kind") != "unit"
	if float(d["turn_rate"]) < 0.0:
		d["turn_rate"] = float(timing.get("turn_rate", combat_default("turn_rate", 12.0)))
	if float(d["sight_night"]) < 0.0:
		var key := "structure" if structure else ("worker" if flags.has("worker") else "unit")
		var pair: Array = rule("vision." + key, [d["sight"], d["sight"]])
		d["sight_night"] = minf(float(d["sight"]), float(pair[1]))
	if int(d["level"]) < 0:
		d["level"] = 0 if structure else int((d["cost"] as Dictionary).get("food", 1))
	if float(d["hp_regen"]) < 0.0:
		var organic := not structure and not flags.has("mechanical") and not flags.has("construct")
		d["hp_regen"] = float(rule("regen.organic_hp", 0.25)) if organic else 0.0
	if float(d["mana_regen"]) < 0.0:
		d["mana_regen"] = float(rule("regen.caster_mana", 0.65)) if float(d["mana"]) > 0.0 else 0.0
	if float(d["mana_start"]) < 0.0:
		d["mana_start"] = minf(float(d["mana"]), float(rule("regen.start_mana", 75)))
	if str(d["model_fit"]) == "":
		d["model_fit"] = "footprint" if structure and str(d["model"]) != "" else "none"


## Fills attack timing defaults so the sim can index them directly. `acquire` is the auto-acquire
## radius (0 = never auto-acquires or retaliates, e.g. workers); it never falls below the range.
func _prepare_attack(d: Dictionary) -> void:
	if not d.has("leash"):
		d["leash"] = combat_default("leash", 14.0)
	var a: Dictionary = d["attack"]
	if a.is_empty():
		return
	var timing: Dictionary = (combat.get("class_timings", {}) as Dictionary).get(str(d.get("class", "")), {})
	for k: String in ["damage_point", "backswing"]:
		if not a.has(k):
			a[k] = timing.get(k, combat_default(k, 0.4))
	if not a.has("projectile"):
		a["projectile"] = {}
	if not a.has("range"):
		a["range"] = 0.5
	if not a.has("targets"):
		a["targets"] = ["ground"]
	if not a.has("kind"):
		a["kind"] = combat_default("weapon_kind", "missile") if not (a["projectile"] as Dictionary).is_empty() else "melee"
	var acq := float(a.get("acquire", combat_default("acquire", 8.0)))
	var floor_r := float(a["range"]) + (0.0 if d.get("kind") != "unit" else 1.0)
	a["acquire"] = maxf(acq, floor_r) if acq > 0.0 else 0.0


func _index_production() -> void:
	_trained_at.clear()
	_researched_at.clear()
	for bid: String in units:
		var d: Dictionary = units[bid]
		for t: Variant in d.get("trains", []):
			_trained_at.get_or_add(str(t), []).append(bid)
		for r: Variant in d.get("research", []):
			_researched_at.get_or_add(str(r), []).append(bid)
		for r: Variant in d.get("upgrades_to", []):
			_researched_at.get_or_add(str(r), []).append(bid)


# --- validation ----------------------------------------------------------------------------

func _validate_unit(id: String, d: Dictionary) -> void:
	for field in ["name", "kind", "hp", "radius"]:
		if not d.has(field):
			errors.append("unit '%s' missing required field '%s'" % [id, field])
	if d.has("kind") and not UNIT_KINDS.has(d["kind"]):
		errors.append("unit '%s' has invalid kind '%s'" % [id, d["kind"]])
	if float(d.get("hp", 0)) <= 0.0:
		errors.append("unit '%s' hp must be > 0" % id)
	if float(d.get("radius", 0)) <= 0.0:
		errors.append("unit '%s' radius must be > 0" % id)
	var flags: Array = d.get("flags", [])
	if d.get("kind") == "unit" and float(d.get("speed", 0.0)) <= 0.0 and not flags.has("immobile"):
		errors.append("unit '%s' is mobile but speed <= 0 (flag 'immobile' for stationary summons)" % id)
	if d.get("kind") in ["building", "resource"]:
		var fp: Array = d.get("footprint", [0, 0])
		if fp.size() != 2 or int(fp[0]) <= 0 or int(fp[1]) <= 0:
			errors.append("structure '%s' needs footprint [w, h] in pathing cells" % id)
	_validate_combat(id, d)
	for a: Variant in d.get("abilities", []):
		if not abilities.has(str(a)):
			errors.append("unit '%s' references unknown ability '%s'" % [id, a])
	for a: Variant in d.get("hero_abilities", []):
		if not abilities.has(str(a)):
			errors.append("hero '%s' references unknown ability '%s'" % [id, a])
	for t: Variant in d.get("trains", []):
		if not units.has(str(t)):
			errors.append("unit '%s' trains unknown unit '%s'" % [id, t])
	for r: Variant in d.get("research", []):
		if not upgrades.has(str(r)):
			errors.append("building '%s' researches unknown upgrade '%s'" % [id, r])
	for r: Variant in d.get("upgrades_to", []):
		if not upgrades.has(str(r)) or not units.has(str(r)):
			errors.append("building '%s' upgrades to '%s', which needs an upgrades.json entry and a building def" % [id, r])
	for r: Variant in d.get("requires", []):
		if not units.has(str(r)) and not upgrades.has(str(r)):
			errors.append("unit '%s' requires unknown id '%s'" % [id, r])
	if d.has("upgrade_of") and not units.has(str(d["upgrade_of"])):
		errors.append("building '%s' upgrade_of unknown '%s'" % [id, d["upgrade_of"]])
	if d.has("transform_of") and not units.has(str(d["transform_of"])):
		errors.append("unit '%s' transform_of unknown '%s'" % [id, d["transform_of"]])


func _validate_combat(id: String, d: Dictionary) -> void:
	var armor_types: Array = combat.get("armor_types", [])
	if not armor_types.is_empty() and not armor_types.has(d.get("armor_type")):
		errors.append("unit '%s' has unknown armor_type '%s'" % [id, d.get("armor_type")])
	var a: Dictionary = d.get("attack", {})
	if a.is_empty():
		return
	var attack_types: Array = combat.get("attack_types", [])
	if not attack_types.is_empty() and not attack_types.has(a.get("type")):
		errors.append("unit '%s' has unknown attack type '%s'" % [id, a.get("type")])
	var dmg: Variant = a.get("damage")
	if not dmg is Array or (dmg as Array).size() != 2 or float(dmg[0]) > float(dmg[1]):
		errors.append("unit '%s' attack damage must be [min, max]" % id)
	if float(a.get("cooldown", 0)) <= 0.0:
		errors.append("unit '%s' attack cooldown must be > 0" % id)
	var p: Dictionary = a.get("projectile", {})
	if not p.is_empty() and float(p.get("speed", 0)) <= 0.0:
		errors.append("unit '%s' projectile speed must be > 0" % id)
	for t: Variant in a.get("targets", ["ground"]):
		if not ["ground", "air"].has(t):
			errors.append("unit '%s' attack targets must be ground/air, got '%s'" % [id, t])
	if a.get("kind", "") == "artillery" and not a.has("splash"):
		errors.append("unit '%s' artillery weapon needs splash (rules §7.7)" % id)


func _validate_abilities() -> void:
	for id: String in abilities:
		var d: Dictionary = abilities[id]
		for field in ["name", "type", "effect"]:
			if not d.has(field):
				errors.append("ability '%s' missing required field '%s'" % [id, field])
		if d.has("type") and not ABILITY_TYPES.has(d["type"]):
			errors.append("ability '%s' has invalid type '%s'" % [id, d["type"]])
		var ranks: Variant = d.get("ranks", [])
		if not ranks is Array:
			errors.append("ability '%s' ranks must be an array" % id)
		elif d.has("levels") and not (ranks as Array).is_empty() and (ranks as Array).size() != int(d["levels"]):
			errors.append("ability '%s' has %d ranks but levels %d" % [id, (ranks as Array).size(), d["levels"]])
		if d.has("unlock") and not upgrades.has(str(d["unlock"])):
			errors.append("ability '%s' unlocked by unknown upgrade '%s'" % [id, d["unlock"]])
		for r in ([{}] if (ranks as Array).is_empty() else ranks):
			var res := (d.get("params", {}) as Dictionary).duplicate()
			res.merge(r, true)
			for key: String in ["buff", "self_buff", "taunt_buff", "root_buff", "slow_buff", "burn_buff",
					"haste_buff", "cover_buff", "opener_slow_buff", "on_splash_buff"]:
				if res.has(key) and not buffs.has(str(res[key])):
					errors.append("ability '%s' references unknown buff '%s'" % [id, res[key]])
			for key: String in ["ground_effect", "on_death_ground_effect"]:
				if res.has(key) and not ground_effects.has(str(res[key])):
					errors.append("ability '%s' references unknown ground effect '%s'" % [id, res[key]])
			for key: String in ["unit", "into"]:
				if res.has(key) and not units.has(str(res[key])):
					errors.append("ability '%s' references unknown unit '%s'" % [id, res[key]])
			if res.has("ability") and not abilities.has(str(res["ability"])):
				errors.append("ability '%s' references unknown ability '%s'" % [id, res["ability"]])


func _validate_buffs() -> void:
	for id: String in buffs:
		var d: Dictionary = buffs[id]
		for field in ["name", "polarity", "kind", "dispellable"]:
			if not d.has(field):
				errors.append("buff '%s' missing required field '%s'" % [id, field])
		if d.has("polarity") and not BUFF_POLARITIES.has(d["polarity"]):
			errors.append("buff '%s' has invalid polarity '%s'" % [id, d["polarity"]])
		if d.has("kind") and not BUFF_KINDS.has(d["kind"]):
			errors.append("buff '%s' has invalid kind '%s'" % [id, d["kind"]])
		var oa: Dictionary = d.get("on_attack", {})
		if oa.has("apply_buff") and not buffs.has(str(oa["apply_buff"])):
			errors.append("buff '%s' applies unknown buff '%s'" % [id, oa["apply_buff"]])
	for id: String in ground_effects:
		var g: Dictionary = ground_effects[id]
		for key: String in ["buff", "enemy_buff", "ally_buff"]:
			if g.has(key) and not buffs.has(str(g[key])):
				errors.append("ground effect '%s' references unknown buff '%s'" % [id, g[key]])


func _validate_items() -> void:
	for id: String in items:
		var d: Dictionary = items[id]
		for field in ["name", "class", "level", "effect"]:
			if not d.has(field):
				errors.append("item '%s' missing required field '%s'" % [id, field])
		if d.has("class") and not ITEM_CLASSES.has(d["class"]):
			errors.append("item '%s' has invalid class '%s'" % [id, d["class"]])
		if d.get("class") == "purchasable" and not d.has("price"):
			errors.append("purchasable item '%s' needs a price" % id)
		var p: Dictionary = d.get("params", {})
		if p.has("buff") and not buffs.has(str(p["buff"])):
			errors.append("item '%s' references unknown buff '%s'" % [id, p["buff"]])
		if p.has("building") and not units.has(str(p["building"])):
			errors.append("item '%s' places unknown building '%s'" % [id, p["building"]])


func _validate_upgrades() -> void:
	for id: String in upgrades:
		var d: Dictionary = upgrades[id]
		for field in ["name", "kind", "levels"]:
			if not d.has(field):
				errors.append("upgrade '%s' missing required field '%s'" % [id, field])
		if d.has("kind") and not UPGRADE_KINDS.has(d["kind"]):
			errors.append("upgrade '%s' has invalid kind '%s'" % [id, d["kind"]])
		var lv: Variant = d.get("levels", [])
		if not lv is Array or (lv as Array).is_empty():
			errors.append("upgrade '%s' needs at least one level" % id)
		else:
			for l: Variant in lv:
				if not (l is Dictionary and (l as Dictionary).has("cost") and (l as Dictionary).has("time")):
					errors.append("upgrade '%s' level needs cost and time" % id)
		if d.get("kind") == "research":
			if d.has("building") and not units.has(str(d["building"])):
				errors.append("research '%s' at unknown building '%s'" % [id, d["building"]])
			for e: Dictionary in d.get("effects", []):
				for u: Variant in e.get("units", []):
					if not units.has(str(u)):
						errors.append("research '%s' affects unknown unit '%s'" % [id, u])
				if e.has("ability") and not abilities.has(str(e["ability"])):
					errors.append("research '%s' unlocks unknown ability '%s'" % [id, e["ability"]])
		elif d.get("kind") == "building_upgrade":
			var to := str(d.get("to", ""))
			if not units.has(to) or not units.has(str(d.get("from", ""))):
				errors.append("building upgrade '%s' needs existing from/to buildings" % id)
			elif str(units[to].get("upgrade_of", "")) != str(d.get("from", "")):
				errors.append("building upgrade '%s': %s.upgrade_of must be '%s'" % [id, to, d.get("from")])
		for r: Variant in d.get("requires", []):
			if not units.has(str(r)) and not upgrades.has(str(r)):
				errors.append("upgrade '%s' requires unknown id '%s'" % [id, r])


func _validate_heroes() -> void:
	for id: String in heroes:
		var h: Dictionary = heroes[id]
		for field in ["name", "faction", "primary", "attributes", "base_damage", "base_cooldown", "abilities"]:
			if not h.has(field):
				errors.append("hero '%s' missing required field '%s'" % [id, field])
		if not ["str", "agi", "int"].has(h.get("primary")):
			errors.append("hero '%s' primary must be str/agi/int" % id)
		var kit: Array = h.get("abilities", [])
		var ults := 0
		for aid: Variant in kit:
			var a: Dictionary = abilities.get(str(aid), {})
			if a.get("ultimate", false):
				ults += 1
		if kit.size() != 4 or ults != 1:
			errors.append("hero '%s' needs 3 abilities + 1 ultimate (rules §6.5)" % id)


func _validate_shops() -> void:
	for id: String in shops:
		if not units.has(id):
			errors.append("shop '%s' is not a building id" % id)
		var s: Dictionary = shops[id]
		for row: Dictionary in s.get("stock", []):
			if not items.has(str(row.get("item", ""))):
				errors.append("shop '%s' sells unknown item '%s'" % [id, row.get("item")])
		for sv: Variant in s.get("services", []):
			if not services.has(str(sv)):
				errors.append("shop '%s' offers unknown service '%s'" % [id, sv])


func _validate_camps() -> void:
	var unit_xp: Array = rule("xp.unit_kill", [])
	for id: String in camps:
		var c: Dictionary = camps[id]
		var levels := 0
		var xp := 0
		for pair: Array in c.get("creeps", []):
			var cid := str(pair[0])
			if not units.has(cid):
				errors.append("camp '%s' uses unknown creep '%s'" % [id, cid])
				continue
			var lv := int(units[cid].get("level", 1))
			levels += lv * int(pair[1])
			if not unit_xp.is_empty():
				xp += int(unit_xp[clampi(lv, 1, unit_xp.size()) - 1]) * int(pair[1])
		if c.has("total_level") and int(c["total_level"]) != levels:
			errors.append("camp '%s' total_level %s but creeps add up to %d" % [id, c["total_level"], levels])
		if c.has("raw_xp") and not unit_xp.is_empty() and int(c["raw_xp"]) != xp:
			errors.append("camp '%s' raw_xp %s but creeps give %d" % [id, c["raw_xp"], xp])
		for slot: String in c.get("drops", {}):
			for cls: Variant in c["drops"][slot].get("class", []):
				if not ITEM_CLASSES.has(str(cls)):
					errors.append("camp '%s' drop %s has unknown item class '%s'" % [id, slot, cls])


func _validate_factions() -> void:
	for id: String in factions:
		var f: Dictionary = factions[id]
		if not f.has("name"):
			errors.append("faction '%s' missing required field 'name'" % id)
		for key: String in ["worker", "hall", "altar", "supply", "shop"]:
			if f.has(key) and not units.has(str(f[key])):
				errors.append("faction '%s' %s '%s' unknown" % [id, key, f[key]])
		for key: String in ["build_basic", "build_advanced", "heroes", "lumber_drop"]:
			for b: Variant in f.get(key, []):
				if not units.has(str(b)) and not (key == "lumber_drop" or key == "hall_tiers"):
					errors.append("faction '%s' %s lists unknown '%s'" % [id, key, b])
		for u: String in f.get("start_units", {}):
			if not units.has(u):
				errors.append("faction '%s' start unit '%s' unknown" % [id, u])
		if f.has("recall_item") and not items.has(str(f["recall_item"])):
			errors.append("faction '%s' recall item '%s' unknown" % [id, f["recall_item"]])


func _validate_simple(table: Dictionary, kind: String, required: Array) -> void:
	for id: String in table:
		for field: String in required:
			if not (table[id] as Dictionary).has(field):
				errors.append("%s '%s' missing required field '%s'" % [kind, id, field])


## Classic hotkeys must be unique per command card (rules §18.4): unit cards (fixed M S H A P,
## O for heroes, then the ability letters) and building cards (train, research, upgrade, ability
## and rally buttons).
func _validate_cards() -> void:
	for id: String in units:
		var d: Dictionary = units[id]
		var keys: Dictionary = {}
		if d.get("kind") == "unit" and float(d.get("speed", 0.0)) > 0.0:
			for k: String in UNIT_CARD_KEYS:
				keys[k] = "command"
		if (d.get("flags", []) as Array).has("hero"):
			keys[HERO_LEARN_KEY] = "learn"
			for aid: Variant in d.get("hero_abilities", []):
				_card_key(id, keys, str(abilities.get(str(aid), {}).get("hotkey", "")), str(aid))
		for aid: Variant in d.get("abilities", []):
			var a: Dictionary = abilities.get(str(aid), {})
			if a.get("type") != "passive":
				_card_key(id, keys, str(a.get("hotkey", "")), str(aid))
		if d.get("kind") != "unit":
			if d.get("rally", false):
				keys[RALLY_KEY] = "rally"
			for t: Variant in d.get("trains", []):
				_card_key(id, keys, str(units.get(str(t), {}).get("hotkey", "")), str(t))
			for r: Variant in d.get("research", []) + d.get("upgrades_to", []):
				_card_key(id, keys, str(upgrades.get(str(r), {}).get("hotkey", "")), str(r))
	for sid: String in shops:
		var keys: Dictionary = {}
		for row: Dictionary in shops[sid].get("stock", []):
			_card_key(sid + " (shop card)", keys, str(row.get("hotkey", "")), str(row.get("item", "")))
		for sv: Variant in shops[sid].get("services", []):
			_card_key(sid + " (shop card)", keys, str(services.get(str(sv), {}).get("hotkey", "")), str(sv))
	for fid: String in factions:
		for menu: String in ["build_basic", "build_advanced"]:
			var keys: Dictionary = {}
			for b: Variant in factions[fid].get(menu, []):
				_card_key("%s %s" % [fid, menu], keys, str(units.get(str(b), {}).get("hotkey", "")), str(b))


func _card_key(card: String, keys: Dictionary, key: String, owner: String) -> void:
	if key == "":
		return
	if keys.has(key):
		errors.append("card '%s': hotkey %s used by %s and %s" % [card, key, keys[key], owner])
	else:
		keys[key] = owner
