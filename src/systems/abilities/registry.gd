class_name EffectRegistry
extends RefCounted
## Effect id -> shared AbilityEffect instance. Looks the script up by file name:
## src/systems/abilities/effects/<id>.gd (ability effects, agent C) first, then
## src/systems/items/effects/<id>.gd (item effects, agent D). Every effect id referenced by
## data (Defs.effect_ids()) must resolve; tests/unit/test_systems.gd checks it.

const DIRS: Array[String] = ["res://src/systems/abilities/effects/", "res://src/systems/items/effects/"]

static var _cache: Dictionary = {}


static func path_of(effect_id: String) -> String:
	for d in DIRS:
		var p := d + effect_id + ".gd"
		if ResourceLoader.exists(p):
			return p
	return ""


static func has_effect(effect_id: String) -> bool:
	return path_of(effect_id) != ""


## The effect instance, or null (with one warning) when no script exists.
static func get_effect(effect_id: String) -> AbilityEffect:
	if _cache.has(effect_id):
		return _cache[effect_id]
	var p := path_of(effect_id)
	var e: AbilityEffect = null
	if p != "":
		e = (load(p) as GDScript).new()
	else:
		push_warning("EffectRegistry: no script for effect '%s'" % effect_id)
	_cache[effect_id] = e
	return e
