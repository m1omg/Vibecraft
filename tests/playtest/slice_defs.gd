extends RefCounted
## Screenshot / playtest helper: registers the slice roster (docs/design/slice-content.json) as unit
## defs for any id data/units.json does not define yet, so visual scripts can place the real
## kingdom and clans models before the gameplay data lands. Never used by the game or the sim
## tests; real data always wins (existing ids are left untouched).

const SLICE := "res://docs/design/slice-content.json"
## Model heights from the art bible §1.3 class table (m), used for health bars / hit points.
const HEIGHTS := {
	"kingdom_hodman": 1.3, "kingdom_flail_levy": 1.3, "kingdom_pavisier": 1.75,
	"kingdom_hookgunner": 1.75, "kingdom_linden_sister": 1.7, "kingdom_wheel_marshal": 2.15,
	"kingdom_firewright": 2.1, "clans_yurtwright": 1.35, "clans_grappler": 2.0,
	"clans_javelineer": 1.8, "clans_gustcaller": 1.8, "clans_hero_uncut": 2.15,
	"clans_hero_skymirror": 2.15,
}


## Returns the ids that were added.
static func register(defs: Node) -> Array[String]:
	var added: Array[String] = []
	var text := FileAccess.get_file_as_string(SLICE)
	var data: Variant = JSON.parse_string(text)
	if not data is Dictionary:
		return added
	var units: Dictionary = defs.get("units")
	for fac: String in ["kingdom", "clans"]:
		var f: Dictionary = data["factions"][fac]
		for sec: String in ["units", "heroes", "buildings"]:
			for e: Dictionary in f.get(sec, []):
				var id: String = e["id"]
				if units.has(id):
					continue
				units[id] = _def(e, sec)
				added.append(id)
	defs.call("_prepare_units")
	return added


static func _def(e: Dictionary, sec: String) -> Dictionary:
	var id: String = e["id"]
	var d := {"name": e.get("name", id), "hp": 500, "radius": 0.45, "armor": 0,
		"armor_type": "medium"}
	if sec == "buildings":
		var fp: Array = e.get("footprint_cells", [12, 12])
		d["kind"] = "building"
		d["footprint"] = [int(fp[0]), int(fp[1])]
		d["radius"] = float(fp[0]) * 0.25
		d["height"] = 6.0 if int(fp[0]) >= 12 else 4.0
		d["hp"] = int(e.get("hp", 1000))
		d["armor_type"] = "fortified"
		d["shape"] = "building"
		return d
	d["kind"] = "unit"
	d["hp"] = int(e.get("hp", e.get("level1", {}).get("hp", 500)))
	d["speed"] = float(e.get("speed_mps", 4.0))
	d["radius"] = float(e.get("radius_m", 0.5 if sec == "heroes" else 0.4))
	d["height"] = HEIGHTS.get(id, 1.8)
	if sec == "heroes":
		d["flags"] = ["hero"]
	var flags: Array = e.get("flags", [])
	if flags.has("worker"):
		d["flags"] = ["worker"]
	var a: Dictionary = e.get("attack", {})
	var cd := float(a.get("cooldown_s", e.get("level1", {}).get("cooldown_s", 1.6)))
	var rng := float(a.get("range_m", e.get("range_m", 0.8)))
	var dmg: Array = a.get("damage", e.get("level1", {}).get("damage", [10, 12]))
	d["attack"] = {"type": "blade", "damage": [int(dmg[0]), int(dmg[1])], "cooldown": cd,
		"range": rng, "damage_point": 0.45, "backswing": 0.45,
		"acquire": 0.0 if flags.has("worker") else maxf(rng + 1.0, 8.0)}
	if rng > 2.0:
		d["attack"]["projectile"] = {"speed": float(a.get("projectile_speed_mps", 18.0)), "arc": 0.12}
		d["attack"]["damage_point"] = 0.35
	return d
