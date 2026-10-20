extends SceneTree
## Asset check: team-colour coverage of every rigged unit model against the art bible §3.1
## (rules 1 and 2), measured from the game camera by tools/assets/team_coverage.gd.
##   godot --headless --path . -s tools/assets/check_team_coverage.gd [-- --write] [--only=a,b]
## Prints one row per model (silhouette coverage, upper-third share, plain texel share, limits)
## and exits 1 when any model is outside its range: units 10–15 %, workers 8–15 %, heroes
## 10–18 %, and some team colour in the upper third. --write also stores the measurements in
## assets/models/units/team_coverage.json, which UnitView reads to strengthen the team rim of
## under-covered models until their masks are repainted (a stopgap, see tools/README.md).
## Models are classified through Defs (hero defs, the "worker" flag); everything is loaded at
## runtime because autoload names are not visible to -s scripts at compile time.

const UNIT_DIR := "res://assets/models/units/"
const OUT := "res://assets/models/units/team_coverage.json"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	await process_frame
	var write := false
	var only: Array = []
	for a in OS.get_cmdline_user_args():
		if a == "--write":
			write = true
		elif a.begins_with("--only="):
			only = Array(a.trim_prefix("--only=").split(","))
	var tc: GDScript = load("res://tools/assets/team_coverage.gd")
	var kinds := _kinds(root.get_node("Defs"))
	var models := {}
	var failed := 0
	print("%-24s %-6s %9s %8s %8s  %s" % ["model", "kind", "coverage", "upper", "texel", "verdict"])
	var files := Array(DirAccess.get_files_at(UNIT_DIR))
	files.sort()
	for f: String in files:
		if not f.ends_with(".glb"):
			continue
		var id := f.get_basename()
		if not only.is_empty() and not only.has(id):
			continue
		var m: Dictionary = tc.call("measure_model", UNIT_DIR + f)
		if m.is_empty():
			continue
		var kind := str(kinds.get(id, "unit"))
		var v: Dictionary = tc.call("verdict", m, kind)
		var lim: Vector2 = tc.call("limits", kind)
		if not v["ok"]:
			failed += 1
		print("%-24s %-6s %8.1f%% %7.2f%% %7.1f%%  %s" % [id, kind, m["coverage"] * 100.0,
			m["upper"] * 100.0, m["texel"] * 100.0,
			"ok" if v["ok"] else "FAIL: " + ", ".join(v["problems"])])
		models[id] = {"kind": kind, "coverage": snappedf(m["coverage"], 0.0001),
			"upper_third": snappedf(m["upper"], 0.0001), "texel": snappedf(m["texel"], 0.0001),
			"min": lim.x, "max": lim.y, "ok": v["ok"]}
	if write:
		var out := {"generator": "tools/assets/check_team_coverage.gd",
			"_doc": "Team-colour share of each unit model's visible silhouette from the game camera (art bible §3.1). Visual only: UnitView strengthens the team rim of models below their minimum.",
			"models": models}
		var file := FileAccess.open(OUT, FileAccess.WRITE)
		file.store_string(JSON.stringify(out, "  ", true) + "\n")
		file.close()
		print("wrote ", ProjectSettings.globalize_path(OUT))
	print("%d model(s) outside the bible's team-colour range" % failed if failed > 0 else "every model within the bible's team-colour range")
	quit(1 if failed > 0 else 0)


## Model basename -> "hero" / "worker" / "unit" from the unit and hero defs.
func _kinds(defs: Node) -> Dictionary:
	var out := {}
	var aliases: Dictionary = {}
	var mf := FileAccess.get_file_as_string(UNIT_DIR + "manifest.json")
	if not mf.is_empty():
		aliases = (JSON.parse_string(mf) as Dictionary).get("aliases", {})
	for table: Dictionary in [defs.get("units"), defs.get("heroes")]:
		for id: String in table:
			var d: Dictionary = table[id]
			var model := str(d.get("model", "")).get_file()
			if model.is_empty():
				model = str(aliases.get(id, id))
			var kind := "unit"
			if table == defs.get("heroes") or (d.get("flags", []) as Array).has("hero"):
				kind = "hero"
			elif (d.get("flags", []) as Array).has("worker"):
				kind = "worker"
			if not out.has(model) or kind == "worker":
				out[model] = kind
	return out
