extends Node
## Loads every data/*.json definition table, fills defaults and validates required fields.
## Gameplay code reads stats only through these accessors (no hardcoded unit stats).

const DATA_DIR := "res://data/"
const UNIT_KINDS: Array[String] = ["unit", "building", "resource"]
const ABILITY_TYPES: Array[String] = ["target_unit", "target_point", "instant", "passive",
	"aura", "autocast"]

## Applied to every unit def before validation so code can index fields without has() checks.
const UNIT_DEFAULTS: Dictionary = {
	"mana": 0, "armor": 0, "armor_type": "none", "speed": 0.0, "turn_rate": 12.0,
	"sight": 10.0, "height": 1.5, "shape": "humanoid", "model": "", "flags": [],
	"abilities": [], "attack": {}, "cost": {}, "footprint": [0, 0], "trains": [],
	"food_provided": 0, "weapon": "none", "roof": "pyramid", "scale": 1.0,
}

var units: Dictionary = {}
var abilities: Dictionary = {}
var items: Dictionary = {}
var upgrades: Dictionary = {}
var doodads: Dictionary = {}
var factions: Dictionary = {}
var combat: Dictionary = {}
var upkeep: Array = []
var errors: Array[String] = []
var _warned: Dictionary = {}


func _ready() -> void:
	reload()


func reload() -> void:
	errors.clear()
	units = _load_table("units.json")
	abilities = _load_table("abilities.json")
	items = _load_table("items.json")
	upgrades = _load_table("upgrades.json")
	doodads = _load_table("doodads.json")
	var fac := _load_table("factions.json")
	factions = fac.get("factions", {})
	combat = fac.get("combat", {})
	upkeep = fac.get("upkeep", [])
	_prepare_units()
	_validate_abilities()
	_validate_simple(doodads, "doodad", ["name", "lumber", "shape"])
	_validate_simple(factions, "faction", ["name"])
	for e in errors:
		push_error("Defs: " + e)


func unit(id: String) -> Dictionary:
	return _get(units, id, "unit")


func ability(id: String) -> Dictionary:
	return _get(abilities, id, "ability")


func item(id: String) -> Dictionary:
	return _get(items, id, "item")


func upgrade(id: String) -> Dictionary:
	return _get(upgrades, id, "upgrade")


func doodad(id: String) -> Dictionary:
	return _get(doodads, id, "doodad")


func faction(id: String) -> Dictionary:
	return _get(factions, id, "faction")


func has_unit(id: String) -> bool:
	return units.has(id)


func unit_ids() -> Array:
	return units.keys()


static func load_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	var text := FileAccess.get_file_as_string(path)
	var json := JSON.new()
	if json.parse(text) != OK:
		push_error("JSON parse error in %s line %d: %s" % [path, json.get_error_line(),
			json.get_error_message()])
		return null
	return json.data


func _load_table(file_name: String) -> Dictionary:
	var data: Variant = load_json(DATA_DIR + file_name)
	if data == null:
		errors.append("missing or invalid %s" % file_name)
		return {}
	if not data is Dictionary:
		errors.append("%s must contain a JSON object" % file_name)
		return {}
	return data


func _get(table: Dictionary, id: String, kind: String) -> Dictionary:
	if table.has(id):
		return table[id]
	var key := kind + ":" + id
	if not _warned.has(key):
		_warned[key] = true
		push_warning("Defs: unknown %s '%s'" % [kind, id])
	return {}


func _prepare_units() -> void:
	for id: String in units:
		var d: Dictionary = units[id]
		for k: String in UNIT_DEFAULTS:
			if not d.has(k):
				d[k] = UNIT_DEFAULTS[k].duplicate() if UNIT_DEFAULTS[k] is Array else UNIT_DEFAULTS[k]
		d["id"] = id
		_validate_unit(id, d)


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
	if d.get("kind") == "unit" and float(d["speed"]) <= 0.0:
		errors.append("unit '%s' is mobile but speed <= 0" % id)
	if d.get("kind") != "unit":
		var fp: Array = d["footprint"]
		if fp.size() != 2 or int(fp[0]) <= 0 or int(fp[1]) <= 0:
			errors.append("structure '%s' needs footprint [w, h] in pathing cells" % id)
	for a: String in d["abilities"]:
		if not abilities.has(a):
			errors.append("unit '%s' references unknown ability '%s'" % [id, a])
	for t: String in d["trains"]:
		if not units.has(t):
			errors.append("unit '%s' trains unknown unit '%s'" % [id, t])


func _validate_abilities() -> void:
	for id: String in abilities:
		var d: Dictionary = abilities[id]
		for field in ["name", "type", "effect"]:
			if not d.has(field):
				errors.append("ability '%s' missing required field '%s'" % [id, field])
		if d.has("type") and not ABILITY_TYPES.has(d["type"]):
			errors.append("ability '%s' has invalid type '%s'" % [id, d["type"]])


func _validate_simple(table: Dictionary, kind: String, required: Array) -> void:
	for id: String in table:
		for field: String in required:
			if not (table[id] as Dictionary).has(field):
				errors.append("%s '%s' missing required field '%s'" % [kind, id, field])
