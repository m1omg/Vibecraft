extends Node
## The Audio director (juice bible §4.6; UCA-F3, AUD-01..04). Every request runs the gates in
## order and silently no-ops when a sound file is missing, so the game runs with zero audio.
##   - families: a sample family (assets/audio/sfx/manifest.json: id -> files) is picked with no
##     back-to-back repeat; variation pitch comes from a stateless hash (`seed`), never double
##     jitter; per-family voice cap and minimum start spacing (data/sfx_events.json `families`);
##   - layered events: `event(id, pos, ctx)` maps one game event to its layers (family
##     templates filled from ctx, conditions, computed pitch, onset alignment so the transient
##     lands on the event frame, bus, no-cut window); fx code never names samples for an event;
##   - pools: `one_shot_pool` (24) 3D voices that steal the lowest priority, oldest first, never
##     inside a no-cut window; `ui_pool` 2D voices (UI, order ticks); one ack voice (Acks bus);
##     one Sub voice (a 140 Hz low-pass thump instead of a camera shake);
##   - gates: missing asset -> no-op; cull beyond `cull_distance_m` × (camera distance / 28) from
##     the listener focus; family spacing and cap; event total cap; priority stealing;
##   - acks (AUD-03): 2D on the input frame, one at a time; What ≤ 1 per 400 ms, Yes / Attack
##     ≤ 1 per 1000 ms, an order or selection tick when debounced or while the What still
##     speaks; annoyed after 5 clicks in 2.5 s (its punchline is never cut);
##     `voice_started(unit, category, length)` (length 0 when the line is missing) drives the
##     body ack (CMB-13) and the speaker's ring shimmer;
##   - the selection "What" plays on `Events.selection_changed` when the local player picked new
##     units (or clicked the same ones again), never when a death prunes the selection;
##   - the listener sits at the camera's ground focus (AUD-04, `follow_camera`);
##   - the duck arbiter (AUD-01): keyed ducks per bus (with an optional attack ramp), the
##     deepest wins, Music ≤ 8 dB down;
##   - variation (UCA-F3, R20): every take is a stateless-hash pick that never repeats the last
##     take; SFX get a small hashed volume (±`vol_var_db`, 1.5 dB) and pitch (±`pitch_var`, 3 %)
##     variation unless the event computes the pitch (no double jitter) or the family is
##     `pitch_locked`; voice lines vary in volume only (±1 dB, pitch 1.0);
##   - aliases (data/sfx_events.json `aliases`): a family with no recording yet borrows a
##     recorded one (sw_chop -> sw_slash) until its own takes exist;
##   - music (MUS-01 subset, assets/audio/music/manifest.json): `match_started(faction)` plays
##     the faction's opening cue on the Music bus; no in-game rotation yet (no tracks exist);
##     `match_ended` (SEQ-02 audio) fades the music over 1.2 s, ducks SFX −10 dB and Ambience
##     −6 dB over 1.2 s, and plays a victory / defeat stinger at 600 ms when one exists;
##   - UI: `ui_click()` (buttons, command card), `deny(kind)` (error / disabled, the Deny
##     player, never dropped by the UI pool) in the local faction's material.
## Timing uses `now()` (wall clock, or `clock_override` in tests). Audio never touches sim state.

signal voice_started(unit: Node, category: String, length: float)

## [bus, send]. The original five stay top-level; Combat / World / Sub feed SFX, Acks feeds Voice.
const BUSES: Array = [["Music", "Master"], ["SFX", "Master"], ["Voice", "Master"], ["UI", "Master"],
	["Ambience", "Master"], ["Combat", "SFX"], ["World", "SFX"], ["Sub", "SFX"], ["Acks", "Voice"]]
const SEARCH_DIRS: Dictionary = {
	"ui": "res://assets/audio/sfx/ui/",
	"sfx": "res://assets/audio/sfx/",
	"voice": "res://assets/audio/voice/",
}
const EXTENSIONS: Array[String] = [".ogg", ".wav", ".mp3"]
const SFX_MANIFEST := "res://assets/audio/sfx/manifest.json"
const VOICE_MANIFEST := "res://assets/audio/voice/manifest.json"
const EVENTS_PATH := "res://data/sfx_events.json"
const MUSIC_MANIFEST := "res://assets/audio/music/manifest.json"
const MUSIC_DUCK_MAX_DB := 8.0
const NO_END := -1000

## Tests: a fixed time in seconds (>= 0) replaces the wall clock.
var clock_override: float = -1.0
var stats: Dictionary = {}
var listener_focus: Vector3 = Vector3.INF
var listener_distance: float = 28.0
var last_ack_category: String = ""
## The local player's faction ("kingdom" | "clans"): UI clicks, denies and order ticks of the
## menus use its material. Set by match_started().
var ui_faction: String = "kingdom"
var local_player: int = 0
## The music cue now playing ("" = none).
var music_id: String = ""

var _families: Dictionary = {}           ## family -> PackedStringArray of paths
var _meta: Dictionary = {}               ## family -> {onset_ms, peak_ms, bus, cap, spacing_ms}
var _meta_default: Dictionary = {"onset_ms": 0, "peak_ms": 120, "bus": "SFX", "cap": 4, "spacing_ms": 60}
var _events: Dictionary = {}
var _speakers: Dictionary = {}           ## def_id -> {category: PackedStringArray}
var _stream_cache: Dictionary = {}       ## path or kind:id -> AudioStream or null (missing)
var _last_pick: Dictionary = {}          ## family -> last variant index
var _pick_seq: Dictionary = {}           ## family -> picks so far (hash sequence)
var _last_start: Dictionary = {}         ## family -> now() of the last start
var _world: Array[Voice] = []
var _ui: Array[AudioStreamPlayer] = []
var _next_ui: int = 0
var _ack: AudioStreamPlayer
var _ack_end: float = -100.0
var _ack_protect_until: float = -1.0
var _sub: AudioStreamPlayer
var _listener: AudioListener3D
var _last_what: float = -100.0
var _last_yes: float = -100.0
var _last_tick: float = -100.0
var _clicks: Array[float] = []
var _annoyed_step: int = 0
var _selection: Array = []
var _input_frame: int = -100
var _ducks: Dictionary = {}              ## key -> [bus, db, t0, attack_s]
var _aliases: Dictionary = {}            ## family -> stand-in family (data/sfx_events.json)
var _music_tracks: Dictionary = {}       ## cue id -> PackedStringArray of takes
var _music: AudioStreamPlayer
var _music_fade: Vector4 = Vector4(0, 0, -100, 0)   ## from_db, to_db, t0, length_s
var _deny: AudioStreamPlayer
var _pending_cue: Array = []             ## [cue id, now() to start]
var _end_winner: int = NO_END            ## match_ended seen in the tick, handled in _process
var _warned: Dictionary = {}


class Voice:
	var player: AudioStreamPlayer3D
	var family: String = ""
	var event_id: String = ""
	var priority: int = 0
	var t_start: float = -100.0
	var t_end: float = -100.0          ## now() when the sample has played out
	var no_cut_until: float = -100.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	reset_stats()
	_ensure_buses()
	_load_tables()
	var fc := FeelConstants.c()
	for i in fc.ui_pool:
		var p := AudioStreamPlayer.new()
		p.bus = "UI"
		add_child(p)
		_ui.append(p)
	_ack = AudioStreamPlayer.new()
	_ack.bus = "Acks"
	add_child(_ack)
	_sub = AudioStreamPlayer.new()
	_sub.bus = "Sub"
	add_child(_sub)
	_deny = AudioStreamPlayer.new()
	_deny.bus = "UI"
	add_child(_deny)
	_music = AudioStreamPlayer.new()
	_music.name = "Music"
	_music.bus = "Music"
	add_child(_music)
	for i in fc.one_shot_pool:
		var v := Voice.new()
		v.player = AudioStreamPlayer3D.new()
		v.player.bus = "Combat"
		v.player.max_distance = 80.0
		v.player.unit_size = 14.0
		v.player.doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_DISABLED
		add_child(v.player)
		_world.append(v)
	_listener = AudioListener3D.new()
	_listener.name = "Listener"
	add_child(_listener)
	if not Events.selection_changed.is_connected(_on_selection_changed):
		Events.selection_changed.connect(_on_selection_changed)
	if not Events.match_ended.is_connected(_on_match_ended):
		Events.match_ended.connect(_on_match_ended)


func now() -> float:
	return clock_override if clock_override >= 0.0 else Time.get_ticks_msec() / 1000.0


func reset_stats() -> void:
	stats = {"played": 0, "missing": 0, "culled": 0, "capped": 0, "spaced": 0, "stolen": 0,
		"rejected": 0, "ticks": 0, "acks": 0, "debounced": 0}


## Tests: forget debounce / spacing history and stop every voice.
func reset_state() -> void:
	_last_start.clear()
	_last_what = -100.0
	_last_yes = -100.0
	_last_tick = -100.0
	_clicks.clear()
	_ack_protect_until = -1.0
	last_ack_category = ""
	_selection = []
	for v in _world:
		v.player.stop()
		v.family = ""
		v.event_id = ""
		v.t_end = -100.0
		v.no_cut_until = -100.0
	if _ack != null:
		_ack.stop()
	_ack_end = -100.0
	_pending_cue = []
	_end_winner = NO_END
	stop_music(0.0)
	_ducks.clear()
	_apply_ducks()
	reset_stats()


# --- tables --------------------------------------------------------------------------------------

func _load_tables() -> void:
	var sfx: Variant = _read_json(SFX_MANIFEST)
	if sfx is Dictionary:
		for fam: String in sfx:
			if sfx[fam] is Array:
				_families[fam] = PackedStringArray(sfx[fam])
	var ev: Variant = _read_json(EVENTS_PATH)
	if ev is Dictionary:
		_events = ev.get("events", {})
		_meta = ev.get("families", {})
		_meta_default.merge(ev.get("defaults", {}), true)
		_aliases = ev.get("aliases", {})
	var mu: Variant = _read_json(MUSIC_MANIFEST)
	if mu is Dictionary:
		for cue: String in mu:
			var e: Variant = mu[cue]
			if e is Dictionary and (e as Dictionary).has("file"):
				_music_tracks[cue] = PackedStringArray([str(e["file"])])
			elif e is Dictionary and (e as Dictionary).get("files") is Array:
				_music_tracks[cue] = PackedStringArray(e["files"])
			elif e is Array:
				_music_tracks[cue] = PackedStringArray(e)
	var vo: Variant = _read_json(VOICE_MANIFEST)
	if vo is Dictionary and vo.get("speakers") is Dictionary:
		for sp: String in vo["speakers"]:
			var e: Dictionary = vo["speakers"][sp]
			var cats: Dictionary = {}
			for c: String in e.get("categories", {}):
				cats[c] = PackedStringArray(e["categories"][c])
			for did: Variant in e.get("def_ids", []):
				_speakers[str(did)] = cats


static func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	var f := FileAccess.open(path, FileAccess.READ)
	return JSON.parse_string(f.get_as_text()) if f != null else null


func has_event(id: String) -> bool:
	return _events.has(id)


func has_family(family: String) -> bool:
	if _families.has(family):
		return true
	if _find_stream("sfx", family) != null or _find_stream("ui", family) != null:
		return true
	var alias := str(_aliases.get(family, ""))
	return not alias.is_empty() and alias != family and _families.has(alias)


## The family whose takes actually play: itself when recorded, else its alias.
func resolve_alias(family: String) -> String:
	if _families.has(family):
		return family
	var alias := str(_aliases.get(family, ""))
	return alias if not alias.is_empty() and _families.has(alias) else family


## Every take path the manifests list: {"sfx": [...], "voice": [...], "music": [...]}.
func manifest_paths() -> Dictionary:
	var out := {"sfx": [], "voice": [], "music": []}
	for fam: String in _families:
		for p: String in _families[fam]:
			if not (out["sfx"] as Array).has(p):
				out["sfx"].append(p)
	for did: String in _speakers:
		for c: String in _speakers[did]:
			for p: String in _speakers[did][c]:
				if not (out["voice"] as Array).has(p):
					out["voice"].append(p)
	for cue: String in _music_tracks:
		for p: String in _music_tracks[cue]:
			out["music"].append(p)
	return out


## Hashed variation of the n-th pick of a family: Vector2(pitch factor, volume dB). Pitch stays
## 1.0 for `pitch_locked` families and when the caller computed the pitch (no double jitter).
func variation(family: String, seq: int, pitch_given: bool = false) -> Vector2:
	var meta := family_meta(family)
	var pv := 0.0
	if not pitch_given and not bool(meta.get("pitch_locked", false)):
		pv = float(meta.get("pitch_var", 0.03)) * Juice.hash11(seq, family.hash(), 41)
	var vv := float(meta.get("vol_var_db", 1.5)) * Juice.hash11(seq, family.hash(), 43)
	return Vector2(1.0 + pv, vv)


func family_meta(family: String) -> Dictionary:
	var m: Dictionary = _meta_default.duplicate()
	m.merge(_meta.get(family, _meta.get(resolve_alias(family), {})), true)
	return m


## Seconds from the start of a family's samples to their loudest moment (whooshes start at
## contact − peak so the peak lands on contact).
func peak_s(family: String) -> float:
	return float(family_meta(family).get("peak_ms", 120)) / 1000.0


func onset_s(family: String) -> float:
	return float(family_meta(family).get("onset_ms", 0)) / 1000.0


## The next variant of a family (no back-to-back repeat; stateless hash sequence). Legacy ids
## (a bare file under assets/audio/sfx or sfx/ui) resolve as one-file families.
func pick_stream(family: String) -> AudioStream:
	family = resolve_alias(family)
	var files: PackedStringArray = _families.get(family, PackedStringArray())
	if files.is_empty():
		var legacy := _find_stream("sfx", family)
		if legacy == null:
			legacy = _find_stream("ui", family)
		if legacy == null:
			_missing(family)
		return legacy
	var idx := _pick_index(family, files.size(), 5)
	var s := _load(files[idx])
	if s == null:
		_missing(family)
	return s


## Variant index: hash of the pick sequence, never the previous index again (n > 1).
func _pick_index(key: String, n: int, salt: int) -> int:
	var seq := int(_pick_seq.get(key, 0))
	_pick_seq[key] = seq + 1
	if n <= 1:
		_last_pick[key] = 0
		return 0
	var last := int(_last_pick.get(key, -1))
	var span := n - 1 if last >= 0 else n
	var idx := mini(int(Juice.hash01(seq, key.hash(), salt) * span), span - 1)
	if last >= 0 and idx >= last:
		idx += 1
	_last_pick[key] = idx
	return idx


func _load(path: String) -> AudioStream:
	if _stream_cache.has(path):
		return _stream_cache[path]
	var s: AudioStream = null
	if ResourceLoader.exists(path):
		s = load(path) as AudioStream
	_stream_cache[path] = s
	return s


func _missing(family: String) -> void:
	stats["missing"] += 1
	if not _warned.has(family):
		_warned[family] = true
		print_verbose("Audio: no samples for '%s' (silent)" % family)


# --- one-shots ------------------------------------------------------------------------------------

## A 3D one-shot. opts: priority (int, 50), volume_db, pitch, from (s into the sample), bus,
## no_cut_ms, cap / spacing_ms (override the family's). Returns true when it started.
func play_3d(id: String, pos: Vector3, opts: Dictionary = {}) -> bool:
	if not has_family(id):
		_missing(id)
		return false
	var meta := family_meta(id)
	if listener_focus != Vector3.INF:
		var cull := FeelConstants.c().cull_distance_m * maxf(listener_distance / 28.0, 0.5)
		if Vector2(pos.x - listener_focus.x, pos.z - listener_focus.z).length() > cull:
			stats["culled"] += 1
			return false
	var t := now()
	var spacing := float(opts.get("spacing_ms", meta.get("spacing_ms", 60))) / 1000.0
	if t - float(_last_start.get(id, -100.0)) < spacing:
		stats["spaced"] += 1
		return false
	var cap := int(opts.get("cap", meta.get("cap", 4)))
	if playing_count(id) >= cap:
		stats["capped"] += 1
		return false
	var priority := int(opts.get("priority", 50))
	var voice := _allocate(priority, t)
	if voice == null:
		stats["rejected"] += 1
		return false
	var stream := pick_stream(id)
	if stream == null:
		return false
	var p := voice.player
	var vary := variation(id, int(_pick_seq.get(resolve_alias(id), 0)), opts.has("pitch"))
	p.stop()
	p.stream = stream
	p.bus = str(opts.get("bus", meta.get("bus", "SFX")))
	p.volume_db = float(opts.get("volume_db", 0.0)) + vary.y
	p.pitch_scale = clampf(float(opts.get("pitch", 1.0)) * vary.x, 0.5, 2.0)
	if p.is_inside_tree():
		p.global_position = pos
	else:
		p.position = pos
	var from := maxf(float(opts.get("from", 0.0)), 0.0)
	p.play(from)
	voice.t_end = t + _remaining(stream, from, p.pitch_scale)
	voice.family = id
	voice.event_id = str(opts.get("event", ""))
	voice.priority = priority
	voice.t_start = t
	voice.no_cut_until = t + float(opts.get("no_cut_ms", 0.0)) / 1000.0
	_last_start[id] = t
	stats["played"] += 1
	return true


## Voices of a family (or, with `by_event`, of an event) currently sounding.
func playing_count(id: String, by_event: bool = false) -> int:
	var n := 0
	for v in _world:
		if _sounding(v) and (v.event_id == id if by_event else v.family == id):
			n += 1
	return n


## A voice counts as sounding until its sample has played out (voice accounting runs on
## `now()`, so caps and stealing behave the same with any audio driver and in tests).
func _sounding(v: Voice) -> bool:
	return now() < v.t_end


static func _remaining(stream: AudioStream, from: float, pitch: float) -> float:
	var length := stream.get_length() if stream != null else 0.0
	if length <= 0.0:
		length = 0.5
	return maxf(length - from, 0.05) / maxf(pitch, 0.1)


## A free 3D voice, else steal the lowest priority (oldest first) that is not protected and
## not above `priority`. null = rejected.
func _allocate(priority: int, t: float) -> Voice:
	var best: Voice = null
	for v in _world:
		if not _sounding(v):
			return v
		if v.priority > priority or t < v.no_cut_until:
			continue
		if best == null or v.priority < best.priority or (v.priority == best.priority and v.t_start < best.t_start):
			best = v
	if best != null:
		stats["stolen"] += 1
	return best


## A 2D one-shot (UI bus by default): order ticks, selection ticks, UI clicks. Starts on the
## calling frame. opts: volume_db, pitch, bus, spacing_ms.
func play_2d(id: String, opts: Dictionary = {}) -> bool:
	if not has_family(id):
		_missing(id)
		return false
	var meta := family_meta(id)
	var t := now()
	var spacing := float(opts.get("spacing_ms", meta.get("spacing_ms", 40))) / 1000.0
	if t - float(_last_start.get(id, -100.0)) < spacing:
		stats["spaced"] += 1
		return false
	var stream := pick_stream(id)
	if stream == null or _ui.is_empty():
		return false
	var p: AudioStreamPlayer = opts.get("player", null) if opts.get("player", null) is AudioStreamPlayer else null
	if p == null:
		p = _ui[_next_ui]
		_next_ui = (_next_ui + 1) % _ui.size()
	var vary := variation(id, int(_pick_seq.get(resolve_alias(id), 0)), opts.has("pitch"))
	p.stop()
	p.stream = stream
	p.bus = str(opts.get("bus", "UI"))
	p.volume_db = float(opts.get("volume_db", 0.0)) + vary.y
	p.pitch_scale = clampf(float(opts.get("pitch", 1.0)) * vary.x, 0.5, 2.0)
	p.play()
	_last_start[id] = t
	stats["played"] += 1
	return true


## Legacy facade: a UI sound by family or file id.
func play_ui(id: String) -> void:
	play_2d(id)


## A button press (menus, pause menu, end banner, command card) in the local faction's material.
func ui_click() -> bool:
	return play_2d("ui_click_%s" % ui_faction, {"volume_db": -8.0, "spacing_ms": 30})


## A denied request: kind "error" (an invalid target or order) or "disabled" (an unavailable
## button). Plays on the dedicated Deny player, ≤ 1 per 150 ms.
func deny(kind: String = "error") -> bool:
	var fam := "ui_%s_%s" % ["disabled" if kind == "disabled" else "error", ui_faction]
	return play_2d(fam, {"volume_db": -6.0, "spacing_ms": 150, "player": _deny})


## A Sub thump (AUD-02 low end): ≤ 1 per 250 ms, instead of a camera shake.
func thump(gain_db: float = -8.0) -> bool:
	var t := now()
	if t - float(_last_start.get("_sub", -100.0)) < 0.25:
		return false
	if not has_family("hit_sub"):
		return false
	var s := pick_stream("hit_sub")
	if s == null or _sub == null:
		return false
	_sub.stream = s
	_sub.volume_db = gain_db
	_sub.play()
	_last_start["_sub"] = t
	stats["played"] += 1
	return true


# --- layered events -------------------------------------------------------------------------------

## Plays a layered event from data/sfx_events.json at `pos`. ctx keys fill the family templates
## ({material}, {weight}, {faction}, {hit_sfx}...) and the conditions (kill, clash, mass,
## armoured); ctx.seed drives the pitch jitter. Returns the number of layers that started.
func event(id: String, pos: Vector3, ctx: Dictionary = {}) -> int:
	var spec: Dictionary = _events.get(id, {})
	if spec.is_empty():
		_missing("event:" + id)
		return 0
	if playing_count(id, true) >= int(spec.get("total_cap", 99)):
		stats["capped"] += 1
		return 0
	var started := 0
	var layers: Array = spec.get("layers", [])
	var seed_v := int(ctx.get("seed", 0))
	for li in layers.size():
		var layer: Dictionary = layers[li]
		if layer.has("when") and not cond(str(layer["when"]), ctx):
			continue
		var family := _resolve_family(layer.get("family", ""), ctx)
		if family.is_empty():
			continue
		var meta := family_meta(family)
		var opts := {
			"event": id,
			"priority": int(layer.get("priority", spec.get("priority", 50))),
			"volume_db": float(layer.get("gain_db", 0.0)),
			"bus": str(layer.get("bus", spec.get("bus", meta.get("bus", "SFX")))),
			"no_cut_ms": float(layer.get("no_cut_ms", 0.0)),
			"pitch": layer_pitch(layer.get("pitch", {}), ctx, seed_v, li),
		}
		match str(layer.get("align", "start")):
			"onset":
				opts["from"] = maxf(float(meta.get("onset_ms", 0)) / 1000.0 - 0.01, 0.0)
			"peak":
				opts["from"] = float(meta.get("peak_ms", 0)) / 1000.0
		if ctx.has("from"):
			opts["from"] = float(ctx["from"])
		var ok := false
		if str(opts["bus"]) == "Sub":
			ok = thump(float(opts["volume_db"]))
		elif bool(spec.get("2d", false)):
			ok = play_2d(family, opts)
		else:
			ok = play_3d(family, pos, opts)
		if ok:
			started += 1
	return started


## Layer pitch: base + per_mass × (mass − 1), clamped, times a stateless jitter (±jitter).
static func layer_pitch(p: Variant, ctx: Dictionary, seed_v: int, salt: int) -> float:
	if not p is Dictionary:
		return 1.0
	var d: Dictionary = p
	var pitch := float(d.get("base", 1.0)) + float(d.get("per_mass", 0.0)) * (float(ctx.get("mass", 1.0)) - 1.0)
	if d.get("clamp") is Array and (d["clamp"] as Array).size() == 2:
		pitch = clampf(pitch, float(d["clamp"][0]), float(d["clamp"][1]))
	var j := float(d.get("jitter", 0.0))
	if j > 0.0:
		pitch *= 1.0 + j * Juice.hash11(seed_v, salt, 31)
	return pitch


## First existing family of a template (or a list of templates) filled from ctx.
func _resolve_family(f: Variant, ctx: Dictionary) -> String:
	var list: Array = f if f is Array else [f]
	for tpl: Variant in list:
		var s := str(tpl)
		for k: String in ctx:
			s = s.replace("{" + k + "}", str(ctx[k]))
		if s.contains("{") or s.is_empty() or s.begins_with("_") or s.ends_with("_"):
			continue
		if has_family(s):
			return s
	if not list.is_empty():
		_missing(str(list[0]))
	return ""


## Layer conditions: "key" (truthy), "!key", "key>=n", "key<=n", "key>n", "key<n".
static func cond(expr: String, ctx: Dictionary) -> bool:
	for op: String in [">=", "<=", ">", "<"]:
		var i := expr.find(op)
		if i > 0:
			var a := float(ctx.get(expr.substr(0, i).strip_edges(), 0.0))
			var b := float(expr.substr(i + op.length()).strip_edges())
			match op:
				">=":
					return a >= b
				"<=":
					return a <= b
				">":
					return a > b
				_:
					return a < b
	if expr.begins_with("!"):
		return not bool(ctx.get(expr.substr(1), false))
	return bool(ctx.get(expr, false))


# --- acks (AUD-03) --------------------------------------------------------------------------------

## category: ready | what | yes | attack | annoyed. 2D on the calling (input) frame, one ack at a
## time. Debounced requests play the order or selection tick instead. Returns true when a line
## started.
func play_voice(unit: Node, category: String) -> bool:
	if unit == null or not is_instance_valid(unit):
		return false
	var fc := FeelConstants.c()
	var t := now()
	var faction := _faction(unit)
	match category:
		"what":
			_clicks.append(t)
			while not _clicks.is_empty() and t - _clicks[0] > fc.annoyed_window_ms / 1000.0:
				_clicks.pop_front()
			if _clicks.size() >= fc.annoyed_clicks and _has_line(unit, "annoyed"):
				category = "annoyed"
				_clicks.clear()
			elif t - _last_what < fc.what_gap_ms / 1000.0:
				stats["debounced"] += 1
				_tick("ui_select_%s_single" % faction, -18.0)
				return false
		"yes", "attack":
			var speaking := is_ack_playing() and last_ack_category in ["what", "annoyed"]
			if t - _last_yes < fc.yes_gap_ms / 1000.0 or speaking:
				stats["debounced"] += 1
				_order_tick(faction, category)
				return false
	if is_ack_playing() and t < _ack_protect_until:
		_order_tick(faction, category)
		return false
	if category == "what" or category == "annoyed":
		_last_what = t
	elif category == "yes" or category == "attack":
		_last_yes = t
	last_ack_category = category
	var stream := _voice_stream(unit, category)
	if stream == null:
		# no line recorded: the body still acknowledges (length 0) and a tick answers the ear
		if category == "what":
			_tick("ui_select_%s_single" % faction, -18.0)
		else:
			_order_tick(faction, category)
		voice_started.emit(unit, category, 0.0)
		return false
	_ack.stop()
	_ack.stream = stream
	_ack.volume_db = Juice.hash11(stats["acks"], str(unit.get("def_id")).hash(), 47)   # ±1 dB, pitch 1.0
	_ack.play()
	var length := stream.get_length()
	_ack_end = t + maxf(length, 0.05)
	_ack_protect_until = t + length if category == "annoyed" else -1.0
	stats["acks"] += 1
	voice_started.emit(unit, category, length)
	return true


## The move / attack order tick ("tuk", UI −20 dB, ≤ 1 per 60 ms).
func order_tick(unit: Node, category: String = "yes") -> void:
	if unit != null and is_instance_valid(unit):
		_order_tick(_faction(unit), category)


func _order_tick(faction: String, category: String) -> void:
	var kind := "move"
	if category == "attack":
		kind = "attack"
	elif category == "patrol":
		kind = "patrol"
	_tick("ui_order_%s_%s" % [faction, kind], -20.0)


func is_ack_playing() -> bool:
	return now() < _ack_end


func _tick(family: String, gain_db: float) -> void:
	var t := now()
	if t - _last_tick < FeelConstants.c().order_tick_gap_ms / 1000.0:
		return
	if play_2d(family, {"volume_db": gain_db, "spacing_ms": 0}):
		_last_tick = t
		stats["ticks"] += 1


func _has_line(unit: Node, category: String) -> bool:
	var cats: Dictionary = _speakers.get(str(unit.get("def_id")), {})
	return not (cats.get(category, PackedStringArray()) as PackedStringArray).is_empty()


func _voice_stream(unit: Node, category: String) -> AudioStream:
	var did := str(unit.get("def_id"))
	var cats: Dictionary = _speakers.get(did, {})
	var files: PackedStringArray = cats.get(category, PackedStringArray())
	if files.is_empty() and category == "annoyed":
		files = cats.get("what", PackedStringArray())
	if files.is_empty() and category == "attack":
		files = cats.get("yes", PackedStringArray())
	if files.is_empty():
		# legacy layout: assets/audio/voice/<def_id>/<category>.ogg
		return _find_stream("voice", "%s/%s" % [did, category])
	var idx := 0
	if category == "annoyed":
		idx = _annoyed_step % files.size()
		_annoyed_step += 1
	else:
		idx = _pick_index("vo:" + did + ":" + category, files.size(), 9)
	return _load(files[idx])


static func _faction(unit: Node) -> String:
	var d: Variant = unit.get("def")
	var f := str((d as Dictionary).get("faction", "")) if d is Dictionary else ""
	if f.is_empty():
		f = "clans" if str(unit.get("def_id")).begins_with("clans_") else "kingdom"
	return f if f == "clans" else "kingdom"


## The selection "What" (SM-01): the local player's own new pick speaks (a hero first, else the
## first unit); re-clicking the same selection speaks again (and escalates to annoyed); a
## selection shrinking because a unit died, or a tab cycle, stays quiet.
func _on_selection_changed(units: Array) -> void:
	var prev := _selection
	_selection = units.duplicate()
	if units.is_empty():
		return
	var fresh := false
	for u: Variant in units:
		if not prev.has(u):
			fresh = true
			break
	var clicked := Engine.get_process_frames() - _input_frame <= 1
	if not fresh and not (clicked and units.size() == prev.size()):
		return
	var speaker: Node = null
	for u: Variant in units:
		if not is_instance_valid(u):
			continue
		var n := u as Node
		var w: Variant = n.get("world")
		if w == null or int(n.get("player_id")) != int((w as Object).get("local_player_id")):
			continue
		if bool(n.get("is_building")):
			continue
		if speaker == null or (bool(n.get("is_hero")) and not bool(speaker.get("is_hero"))):
			speaker = n
	if speaker != null:
		play_voice(speaker, "what")


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		_input_frame = Engine.get_process_frames()
	elif event is InputEventKey and event.is_pressed():
		_input_frame = Engine.get_process_frames()


# --- listener and mix (AUD-01, AUD-04) ------------------------------------------------------------

## AUD-04: the listener sits at the camera's ground focus with the camera's orientation, so
## sounds pan by screen position and fall off from the middle of the view.
func follow_camera(cam: Camera3D, focus: Vector3, distance: float) -> void:
	listener_focus = focus
	listener_distance = distance
	if _listener == null or cam == null or not _listener.is_inside_tree() or not cam.is_inside_tree():
		return
	if _listener.get_viewport() != cam.get_viewport():
		return
	_listener.global_transform = Transform3D(cam.global_basis, focus + Vector3.UP * 2.0)
	if not _listener.is_current():
		_listener.make_current()


## AUD-01: a keyed duck on a bus; the deepest duck per bus wins (Music never below −8 dB in
## play, `uncapped` lifts the cap for the end sequence). `attack_ms` ramps it in linearly on
## now() (refresh-rate independent). `release(key)` lifts it.
func duck(key: StringName, bus: String, db: float, attack_ms: float = 0.0) -> void:
	_ducks[key] = [bus, absf(db), now(), maxf(attack_ms, 0.0) / 1000.0]
	_apply_ducks()


func release(key: StringName) -> void:
	_ducks.erase(key)
	_apply_ducks()


func duck_db(bus: String) -> float:
	var deepest := 0.0
	var t := now()
	for k: StringName in _ducks:
		var d: Array = _ducks[k]
		if str(d[0]) == bus:
			var depth := float(d[1])
			if d.size() > 3 and float(d[3]) > 0.0:
				depth *= clampf((t - float(d[2])) / float(d[3]), 0.0, 1.0)
			deepest = maxf(deepest, depth)
	if bus == "Music":
		deepest = minf(deepest, MUSIC_DUCK_MAX_DB)
	return -deepest


func _apply_ducks() -> void:
	for b: Array in BUSES:
		var idx := AudioServer.get_bus_index(str(b[0]))
		if idx >= 0:
			AudioServer.set_bus_volume_db(idx, duck_db(str(b[0])))


# --- music (MUS-01 subset) and the end sequence's audio (SEQ-02) -------------------------------

## A match begins for the local player (Main, after the boot): the UI material follows the
## local faction, end-sequence ducks are lifted and the faction's opening cue plays
## (`opening_<faction>`; silent when that faction has none yet).
func match_started(faction: String, player_id: int = 0) -> void:
	ui_faction = faction if faction == "clans" else "kingdom"
	local_player = player_id
	_pending_cue = []
	_end_winner = NO_END
	for k: StringName in [&"end_sfx", &"end_ambience"]:
		_ducks.erase(k)
	_apply_ducks()
	play_music("opening_%s" % faction)


func has_music(cue: String) -> bool:
	return not (_music_tracks.get(cue, PackedStringArray()) as PackedStringArray).is_empty()


## Starts a music cue (a take picked like a family) on the Music bus. Returns false when the
## cue has no recording (silent).
func play_music(cue: String, volume_db: float = -2.0) -> bool:
	var takes: PackedStringArray = _music_tracks.get(cue, PackedStringArray())
	if takes.is_empty() or _music == null:
		_missing("music:" + cue)
		return false
	var s := _load(takes[_pick_index("mu:" + cue, takes.size(), 13)])
	if s == null:
		_missing("music:" + cue)
		return false
	_music.stop()
	_music.stream = s
	_music.volume_db = volume_db
	_music_fade = Vector4(volume_db, volume_db, -100.0, 0.0)
	_music.play()
	music_id = cue
	stats["played"] += 1
	return true


## Fades the music out over `fade_s` (0 = stop now).
func stop_music(fade_s: float = 1.2) -> void:
	if _music == null:
		return
	if fade_s <= 0.0 or not _music.playing:
		_music.stop()
		music_id = ""
		return
	_music_fade = Vector4(_music.volume_db, -60.0, now(), fade_s)


func is_music_playing() -> bool:
	return _music != null and _music.playing and not music_id.is_empty()


## SEQ-02 (audio, P0): music out over 1.2 s, SFX −10 dB and Ambience −6 dB over 1.2 s, the
## local result's stinger at 600 ms when recorded (`victory_<faction>` / `defeat_<faction>`).
## The signal fires inside the sim tick: it only records the result; `_process` acts on it.
func _on_match_ended(winner: int, _reason: String) -> void:
	_end_winner = winner


func _begin_end_sequence(winner: int) -> void:
	stop_music(1.2)
	duck(&"end_sfx", "SFX", 10.0, 1200.0)
	duck(&"end_ambience", "Ambience", 6.0, 1200.0)
	var won := winner == local_player
	_pending_cue = [("victory_" if won else "defeat_") + ui_faction, now() + 0.6]


func _process(_delta: float) -> void:
	var t := now()
	if _end_winner != NO_END:
		var w := _end_winner
		_end_winner = NO_END
		_begin_end_sequence(w)
	if _music_fade.w > 0.0 and _music != null:
		var k := clampf((t - _music_fade.z) / _music_fade.w, 0.0, 1.0)
		_music.volume_db = lerpf(_music_fade.x, _music_fade.y, Juice.in_quad(k))
		if k >= 1.0:
			_music.stop()
			music_id = ""
			_music_fade.w = 0.0
	if not _pending_cue.is_empty() and t >= float(_pending_cue[1]):
		var cue := str(_pending_cue[0])
		_pending_cue = []
		if has_music(cue):
			_music_fade.w = 0.0
			play_music(cue, 0.0)
	for k: StringName in _ducks:
		var d: Array = _ducks[k]
		if d.size() > 3 and float(d[3]) > 0.0 and t - float(d[2]) <= float(d[3]) + 0.1:
			_apply_ducks()
			break


# --- legacy file lookup ---------------------------------------------------------------------------

func _find_stream(kind: String, id: String) -> AudioStream:
	var key := kind + ":" + id
	if _stream_cache.has(key):
		return _stream_cache[key]
	var found: AudioStream = null
	for ext in EXTENSIONS:
		var path: String = SEARCH_DIRS[kind] + id + ext
		if ResourceLoader.exists(path):
			found = load(path) as AudioStream
			break
	_stream_cache[key] = found
	return found


func _ensure_buses() -> void:
	for b: Array in BUSES:
		var bus_name := str(b[0])
		if AudioServer.get_bus_index(bus_name) != -1:
			continue
		AudioServer.add_bus()
		AudioServer.set_bus_name(AudioServer.bus_count - 1, bus_name)
	for b: Array in BUSES:
		var idx := AudioServer.get_bus_index(str(b[0]))
		if idx > 0:
			AudioServer.set_bus_send(idx, str(b[1]))
	var sub := AudioServer.get_bus_index("Sub")
	if sub > 0 and AudioServer.get_bus_effect_count(sub) == 0:
		var lp := AudioEffectLowPassFilter.new()
		lp.cutoff_hz = 140.0
		AudioServer.add_bus_effect(sub, lp)
