class_name FxDefs
extends RefCounted
## Per-entity juice sheets (data/fx_units.json). Visual only: the simulation never reads them.
## `sheet(unit)` merges, in order: `defaults` -> the faction / family grammar -> values derived
## from the def (armor_type -> material, the placeholder `weapon` hint -> weapon class, the
## projectile -> ranged class) -> `units.<def_id>` -> the def's own optional `fx` block. The
## weapon class row (`weapons.<class>`: split / pull / c1 / hit-stop / cone / count / knockback /
## whoosh) is folded in under the unit's own overrides. Cached per def id.

const PATH := "res://data/fx_units.json"

static var _data: Dictionary = {}
static var _cache: Dictionary = {}


static func data() -> Dictionary:
	if _data.is_empty():
		var f := FileAccess.open(PATH, FileAccess.READ)
		if f != null:
			var parsed: Variant = JSON.parse_string(f.get_as_text())
			if parsed is Dictionary:
				_data = parsed
		if _data.is_empty():
			push_warning("FxDefs: %s missing or invalid; using built-in defaults" % PATH)
			_data = {"defaults": {"mass": 1.0, "material": "flesh", "weapon": "slash"}}
	return _data


static func clear_cache() -> void:
	_cache.clear()


## The merged sheet for a unit (Unit or anything with def_id / def / player_id).
static func sheet(u: Object) -> Dictionary:
	var def_id := str(u.get("def_id"))
	if _cache.has(def_id):
		return _cache[def_id]
	var d: Dictionary = u.get("def") if u.get("def") is Dictionary else {}
	var s := sheet_for(def_id, d)
	_cache[def_id] = s
	return s


static func sheet_for(def_id: String, def: Dictionary) -> Dictionary:
	var src := data()
	var out: Dictionary = (src.get("defaults", {}) as Dictionary).duplicate(true)
	var grammar := _grammar_of(def_id, def)
	out["grammar"] = grammar
	out.merge(src.get("grammars", {}).get(grammar, {}), true)
	# derived from the def
	var armor := str(def.get("armor_type", ""))
	var amap: Dictionary = src.get("armor_material", {})
	if amap.has(armor):
		out["material"] = amap[armor]
	var hint := str(def.get("weapon", ""))
	var wmap: Dictionary = src.get("weapon_hint", {})
	if wmap.has(hint):
		out["weapon"] = wmap[hint]
	var atk: Dictionary = def.get("attack", {}) if def.get("attack") is Dictionary else {}
	var proj: Dictionary = atk.get("projectile", {}) if atk.get("projectile") is Dictionary else {}
	if not proj.is_empty():
		var missile := str(proj.get("model", "arrow"))
		out["missile"] = missile
		out["ranged"] = str(src.get("missiles", {}).get(missile, {}).get("ranged", "bow"))
	if def.has("radius"):
		out["mass"] = clampf(float(def["radius"]) / 0.45, 0.5, 3.0)
	var own: Dictionary = src.get("units", {}).get(def_id, {})
	out.merge(own, true)
	if def.get("fx") is Dictionary:
		out.merge(def["fx"], true)
	# weapon class row under the unit's own overrides
	var row: Dictionary = src.get("weapons", {}).get(str(out.get("weapon", "slash")), {})
	for k: String in row:
		if not own.has(k) and not (def.get("fx") is Dictionary and (def["fx"] as Dictionary).has(k)):
			out[k] = row[k]
	if out.has("ranged"):
		var rrow: Dictionary = src.get("ranged", {}).get(str(out["ranged"]), {})
		for k: String in rrow:
			out["ranged_" + k] = rrow[k]
	var c1_off := float(src.get("grammars", {}).get(grammar, {}).get("c1_offset", 0.0))
	if c1_off != 0.0 and not own.has("c1"):
		out["c1"] = maxf(float(out.get("c1", 1.3)) + c1_off, 1.0)
	return out


static func _grammar_of(def_id: String, def: Dictionary) -> String:
	var f := str(def.get("faction", ""))
	if f.is_empty():
		for p: String in ["kingdom", "clans", "creep"]:
			if def_id.begins_with(p + "_"):
				f = p
	if f == "kingdom" or f == "clans" or f == "creep":
		return f
	return "neutral"


## The impact material for a hit coming from `origin` (CMB-18): `material_front` when the origin
## lies inside the victim's frontal arc around its rendered facing, else `material`.
static func hit_material(s: Dictionary, victim_facing: float, victim_pos: Vector3, origin: Vector3) -> String:
	var mf: Variant = s.get("material_front")
	if mf is Dictionary and origin != Vector3.INF:
		var to := Vector2(origin.x - victim_pos.x, origin.z - victim_pos.z)
		if to.length_squared() > 1e-6:
			var fwd := Vector2(-sin(victim_facing), -cos(victim_facing))
			var ang := rad_to_deg(acos(clampf(fwd.dot(to.normalized()), -1.0, 1.0)))
			if ang <= float((mf as Dictionary).get("arc_deg", 60.0)):
				return str((mf as Dictionary).get("material", s.get("material", "flesh")))
	return str(s.get("material", "flesh"))


## Particle bursts for a material: Array of [kind, count].
static func material_bursts(material: String) -> Array:
	var m: Dictionary = data().get("materials", {}).get(material, {})
	if m.is_empty():
		m = data().get("materials", {}).get("flesh", {})
	return m.get("bursts", [])


static func material_sound(material: String) -> String:
	return str(data().get("materials", {}).get(material, {}).get("sound", "flesh"))


static func missile(model: String) -> Dictionary:
	return data().get("missiles", {}).get(model, data().get("missiles", {}).get("arrow", {}))
