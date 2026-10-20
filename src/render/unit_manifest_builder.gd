extends SceneTree
## Generates assets/models/units/manifest.json: per rigged unit GLB the clip list and timing the
## views need (visual only, never read by the sim):
##   height_m            model height (AABB)
##   clips               {name: length_s}
##   walk_anim_speed     m/s the in-place walk clip moves the planted foot at playback 1.0
##                       (stride matching: playback = actual speed / walk_anim_speed / model scale).
##                       Taken from tools/autorig.py's QA `stance_speed_mps` when its JSON logs are
##                       given, else measured here from the toe bones the same way.
##   attack_hit_s        clip time of the strike / release (peak weapon-hand speed): UnitView maps
##                       the sim damage point onto it; attack_start_s / attack_end_s bound the
##                       useful part of the clip (motion above 15 % of the peak).
##   cast_hit_s, work_hit_s (+ start / end)   same for cast and work clips
##   death_settle_s      when the body comes to rest (dust-puff hook)
## plus `aliases` {def id -> model} for slice ids whose GLB has another name.
## Run: godot --headless --path . -s src/render/unit_manifest_builder.gd [-- --autorig-logs=DIR]

const UNIT_DIR := "res://assets/models/units/"
const OUT := "res://assets/models/units/manifest.json"
const FPS := 60.0
## Slice def ids whose rigged GLB carries a working name (slice-content.json ids -> GLB basename).
const ALIASES := {
	"kingdom_pavisier": "kingdom_infantry",
	"kingdom_flail_levy": "kingdom_hodman",
	"clans_hero_skymirror": "clans_skymirror",
}


func _initialize() -> void:
	var logs := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--autorig-logs="):
			logs = a.trim_prefix("--autorig-logs=")
	var units := {}
	for f in DirAccess.get_files_at(UNIT_DIR):
		if not f.ends_with(".glb"):
			continue
		var entry := measure(UNIT_DIR + f)
		if entry.is_empty():
			continue
		var id := f.get_basename()
		if not logs.is_empty():
			_merge_autorig(entry, logs.path_join(id + ".json"))
		units[id] = entry
		print("%-24s walk %.3f m/s (%s)  hit %s" % [id, entry.get("walk_anim_speed", 0.0),
			entry.get("walk_anim_speed_source", "-"), entry.get("attack_hit_s", "-")])
	var out := {
		"generator": "src/render/unit_manifest_builder.gd",
		"conventions": {
			"walk_anim_speed": "m/s of the planted foot in the in-place walk clip at playback 1.0 and native model size",
			"hit_s": "clip seconds of the strike / release / work impact (peak weapon-hand speed)",
			"start_end_s": "useful part of a one-shot clip (hand motion above 15 % of its peak)",
			"aliases": "def id -> unit GLB basename when the slice id and the asset name differ",
		},
		"aliases": ALIASES,
		"units": units,
	}
	var file := FileAccess.open(OUT, FileAccess.WRITE)
	file.store_string(JSON.stringify(out, "  ", true) + "\n")
	file.close()
	print("wrote ", ProjectSettings.globalize_path(OUT), " (", units.size(), " units)")
	quit(0)


## Measures one rigged GLB. Static so tests can call it on any model.
static func measure(path: String) -> Dictionary:
	var ps := load(path) as PackedScene
	if ps == null:
		return {}
	var root := ps.instantiate() as Node3D
	var ap := root.find_child("AnimationPlayer", true, false) as AnimationPlayer
	var sk_list := root.find_children("*", "Skeleton3D", true, false)
	if ap == null or sk_list.is_empty():
		root.free()
		return {}
	var sk := sk_list[0] as Skeleton3D
	var aabb := AssetLibrary.mesh_bounds(root)
	var e := {"height_m": snappedf(aabb.size.y, 0.001), "clips": {}}
	var clips: Dictionary = e["clips"]
	for c in ap.get_animation_list():
		clips[str(c)] = snappedf(ap.get_animation(c).length, 0.001)
	if clips.has("walk"):
		var ws := _walk_speed(ap, sk, aabb.size.y)
		if ws > 0.0:
			e["walk_anim_speed"] = snappedf(ws, 0.001)
			e["walk_anim_speed_source"] = "measured"
	for clip: String in ["attack", "cast", "work"]:
		if clips.has(clip):
			var t := _strike_timing(ap, sk, clip)
			e[clip + "_hit_s"] = snappedf(t.x, 0.001)
			e[clip + "_start_s"] = snappedf(t.y, 0.001)
			e[clip + "_end_s"] = snappedf(t.z, 0.001)
	if clips.has("death"):
		e["death_settle_s"] = snappedf(_settle_time(ap, sk, "death"), 0.001)
	root.free()
	return e


## Bone positions (skeleton space) at clip time t, evaluated straight from the clip's
## position / rotation / scale tracks over the rest hierarchy (no mixer or scene tree needed).
static func _pose(ap: AnimationPlayer, sk: Skeleton3D, clip: String, t: float, bones: Array) -> Array:
	var a := ap.get_animation(clip)
	var local: Array[Transform3D] = []
	for i in sk.get_bone_count():
		local.append(sk.get_bone_rest(i))
	for tr in a.get_track_count():
		var path := a.track_get_path(tr)
		var b := sk.find_bone(str(path.get_concatenated_subnames()))
		if b < 0:
			continue
		var xf := local[b]
		match a.track_get_type(tr):
			Animation.TYPE_POSITION_3D:
				xf.origin = a.position_track_interpolate(tr, t)
			Animation.TYPE_ROTATION_3D:
				xf.basis = Basis(a.rotation_track_interpolate(tr, t)).scaled(xf.basis.get_scale())
			Animation.TYPE_SCALE_3D:
				xf.basis = Basis(xf.basis.get_rotation_quaternion()).scaled(a.scale_track_interpolate(tr, t))
		local[b] = xf
	var glob: Array[Transform3D] = []
	glob.resize(sk.get_bone_count())
	for i in sk.get_bone_count():
		var parent := sk.get_bone_parent(i)
		glob[i] = local[i] if parent < 0 else glob[parent] * local[i]
	var out := []
	for b: int in bones:
		out.append(glob[b].origin)
	return out


static func _bone(sk: Skeleton3D, names: Array) -> int:
	for n: String in names:
		var i := sk.find_bone(n)
		if i >= 0:
			return i
	return -1


## Planted-foot speed of the in-place walk: per toe, frames within 2 % H of its low height are
## stance frames; their median horizontal speed is how fast the body must travel.
static func _walk_speed(ap: AnimationPlayer, sk: Skeleton3D, h: float) -> float:
	var toes := [_bone(sk, ["LeftToeBase", "LeftFoot"]), _bone(sk, ["RightToeBase", "RightFoot"])]
	if toes.has(-1):
		return 0.0
	var a := ap.get_animation("walk")
	var n := int(a.length * FPS)
	var tracks := [[], []]
	for i in n + 1:
		var p := _pose(ap, sk, "walk", float(i) / FPS, toes)
		tracks[0].append(p[0])
		tracks[1].append(p[1])
	var speeds: Array[float] = []
	for tr: Array in tracks:
		var ys: Array[float] = []
		for p: Vector3 in tr:
			ys.append(p.y)
		ys.sort()
		var low := ys[int(ys.size() * 0.2)]
		for i in range(1, tr.size()):
			var p0: Vector3 = tr[i - 1]
			var p1: Vector3 = tr[i]
			if p0.y < low + 0.02 * h and p1.y < low + 0.02 * h:
				speeds.append(Vector2(p1.x - p0.x, p1.z - p0.z).length() * FPS)
	if speeds.is_empty():
		return 0.0
	speeds.sort()
	return speeds[speeds.size() / 2]


## (hit, start, end) of a one-shot clip from the faster hand's speed profile.
static func _strike_timing(ap: AnimationPlayer, sk: Skeleton3D, clip: String) -> Vector3:
	var hands := [_bone(sk, ["RightHand"]), _bone(sk, ["LeftHand"])]
	var a := ap.get_animation(clip)
	var n := maxi(int(a.length * FPS), 2)
	var prev := []
	var sp := [PackedFloat32Array(), PackedFloat32Array()]
	for i in n + 1:
		var p := _pose(ap, sk, clip, float(i) / FPS, hands.filter(func(b: int) -> bool: return b >= 0))
		if not prev.is_empty():
			for k in p.size():
				sp[k].append((p[k] - prev[k]).length() * FPS)
		prev = p
	var best := 0
	var peak := 0.0
	var hand := 0
	for k in 2:
		for i in sp[k].size():
			if sp[k][i] > peak:
				peak = sp[k][i]
				best = i
				hand = k
	var s: PackedFloat32Array = sp[hand]
	if peak <= 0.0:
		return Vector3(a.length * 0.5, 0.0, a.length)
	var start := best
	while start > 0 and s[start - 1] > peak * 0.15:
		start -= 1
	var end := best
	while end < s.size() - 1 and s[end + 1] > peak * 0.15:
		end += 1
	return Vector3((best + 1.0) / FPS, start / FPS, minf((end + 1.0) / FPS, a.length))


## Time after which the hips stop moving (< 2 cm/s for the rest of the clip).
static func _settle_time(ap: AnimationPlayer, sk: Skeleton3D, clip: String) -> float:
	var hips := _bone(sk, ["Hips"])
	var a := ap.get_animation(clip)
	if hips < 0:
		return a.length
	var n := int(a.length * FPS)
	var pts := []
	for i in n + 1:
		pts.append(_pose(ap, sk, clip, float(i) / FPS, [hips])[0])
	var settle := a.length
	for i in range(n, 0, -1):
		if ((pts[i] as Vector3) - (pts[i - 1] as Vector3)).length() * FPS > 0.02:
			settle = float(i) / FPS
			break
	return settle


## tools/autorig.py QA: qa.clips.walk.stance_speed_mps {L, R} is the reference stride speed.
static func _merge_autorig(entry: Dictionary, json_path: String) -> void:
	if not FileAccess.file_exists(json_path):
		return
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if not d is Dictionary:
		return
	var walk: Dictionary = (d as Dictionary).get("qa", {}).get("clips", {}).get("walk", {})
	var ss: Dictionary = walk.get("stance_speed_mps", {})
	var vals: Array[float] = []
	for k: String in ss:
		if ss[k] != null and float(ss[k]) > 0.0:
			vals.append(float(ss[k]))
	if vals.is_empty():
		return
	var avg := 0.0
	for v in vals:
		avg += v
	entry["walk_anim_speed_measured"] = entry.get("walk_anim_speed", 0.0)
	entry["walk_anim_speed"] = snappedf(avg / vals.size(), 0.001)
	entry["walk_anim_speed_source"] = "autorig stance_speed_mps"
