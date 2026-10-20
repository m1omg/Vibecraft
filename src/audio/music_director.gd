class_name MusicDirector
extends Node
## The music director (juice MUS-01 P0, SEQ-01 / SEQ-02 audio; tools/music/README.md "In the
## game"). A child of the Audio autoload (process ALWAYS, so it keeps running while the tree is
## paused). Track lists come from assets/audio/music/manifest.json (`kind`, `faction`, `loop`,
## `xfade_to_score_s`). Every request no-ops silently when a piece is missing.
##   - MENU: the menu theme loops; from silence it fades in over 0.75 s (the loop's head
##     carries its crossfaded tail, so the fade belongs here, never in the file); from other
##     music it crossfades.
##   - LOADING: whatever plays fades out over 1.5 s while the match loads.
##   - GAME: the opening cue (2.4 s, on the Alerts bus at -4 dB) at match start, then the local
##     faction's in-game tracks from a shuffle bag (no repeat until all have played, never the
##     last one twice in a row across bags), the first 6 s after the match starts with a 2 s
##     fade-in, then 20-40 s of silence between tracks. A track is chosen only when the previous
##     one has ended; tracks never loop and never switch for battle.
##   - END: the game music fades out over 1.2 s; at 0.6 s the local result's stinger plays
##     unfaded; at the stinger's `xfade_to_score_s` the score bed enters with a 2 s equal-power
##     crossfade and loops until the player leaves.
## Two decks carry the crossfades; fades are equal-power curves in linear amplitude. Timing is
## `Audio.now()` (the wall clock, or the tests' pinned clock): nothing depends on the frame rate.
## Picks use the director's own RNG, never the sim's.

enum State { SILENT, MENU, LOADING, GAME, END }

const MANIFEST := "res://assets/audio/music/manifest.json"
const MENU_FADE_IN_S := 0.75
const MENU_XFADE_S := 1.0
const LOADING_FADE_S := 1.5
const FIRST_TRACK_S := 6.0
const TRACK_FADE_IN_S := 2.0
const GAP_MIN_S := 20.0
const GAP_MAX_S := 40.0
const END_FADE_S := 1.2
const STINGER_AT_S := 0.6
const SCORE_XFADE_S := 2.0
const SCORE_XFADE_DEFAULT_S := 9.5
const OPENING_DB := -4.0
const SILENT_DB := -80.0

var state: State = State.SILENT
## The cue now heard most recently started ("" = none): the opening cue, a track, a stinger...
var current: String = ""
var faction: String = ""
## Seconds of silence chosen for the gap now running (tests read it).
var last_gap_s: float = 0.0
var rng := RandomNumberGenerator.new()

var _entries: Dictionary = {}            ## cue id -> manifest entry
var _decks: Array[Deck] = []
var _cue_player: AudioStreamPlayer       ## the opening cue (Alerts bus)
var _bag: Array[String] = []
var _last_track: String = ""
var _next_track_at: float = -1.0         ## now() when the next in-game track starts (-1 = none)
var _track_deck: Deck = null             ## the deck playing the in-game track
var _stinger_at: float = -1.0
var _stinger: String = ""
var _score_at: float = -1.0
var _stinger_deck: Deck = null


class Deck:
	var player: AudioStreamPlayer
	var cue: String = ""
	var t_start: float = -100.0
	var length: float = 0.0              ## stream length (0 = unknown); loops never end
	var loop: bool = false
	var gain_db: float = 0.0             ## the level the piece settles at
	var fade_from: float = 0.0           ## linear amplitude
	var fade_to: float = 1.0
	var fade_t0: float = -100.0
	var fade_len: float = 0.0
	var stop_after_fade: bool = false

	func amp_at(t: float) -> float:
		if fade_len <= 0.0:
			return fade_to
		var k := clampf((t - fade_t0) / fade_len, 0.0, 1.0)
		# equal-power: a fade-in rises on sin, a fade-out falls on cos
		if fade_to >= fade_from:
			return lerpf(fade_from, fade_to, sin(k * PI * 0.5))
		return lerpf(fade_to, fade_from, cos(k * PI * 0.5))

	func fade_done(t: float) -> bool:
		return fade_len <= 0.0 or t >= fade_t0 + fade_len

	func busy() -> bool:
		return cue != ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	rng.seed = Time.get_ticks_usec() ^ 0x5eed
	for i in 2:
		var d := Deck.new()
		d.player = AudioStreamPlayer.new()
		d.player.name = "Deck%d" % i
		d.player.bus = "Music"
		add_child(d.player)
		_decks.append(d)
	_cue_player = AudioStreamPlayer.new()
	_cue_player.name = "Cue"
	_cue_player.bus = "Alerts"
	add_child(_cue_player)
	_load_manifest()


func _load_manifest() -> void:
	if not FileAccess.file_exists(MANIFEST):
		return
	var f := FileAccess.open(MANIFEST, FileAccess.READ)
	var mu: Variant = JSON.parse_string(f.get_as_text()) if f != null else null
	if mu is Dictionary:
		for cue: String in mu:
			if mu[cue] is Dictionary:
				_entries[cue] = mu[cue]


func now() -> float:
	return Audio.now()


func has(cue: String) -> bool:
	return _entries.has(cue) and ResourceLoader.exists(str(_entries[cue].get("file", "")))


## The in-game tracks of `fid` (manifest kind "ingame"), sorted by id.
func tracks_of(fid: String) -> Array[String]:
	var out: Array[String] = []
	for cue: String in _entries:
		var e: Dictionary = _entries[cue]
		if str(e.get("kind", "")) == "ingame" and str(e.get("faction", "")) == fid and has(cue):
			out.append(cue)
	out.sort()
	return out


func is_playing() -> bool:
	for d in _decks:
		if d.busy():
			return true
	return _cue_player != null and _cue_player.playing


## Seconds until the next in-game track starts (-1 when none is scheduled).
func next_track_in() -> float:
	return _next_track_at - now() if _next_track_at >= 0.0 else -1.0


func track_deck_cue() -> String:
	return _track_deck.cue if _track_deck != null else ""


# --- states ---------------------------------------------------------------------------------

## The main menu is up: the menu theme loops (fades in from silence, crossfades from other music).
func enter_menu() -> void:
	_cancel_schedules()
	state = State.MENU
	for d in _decks:
		if d.cue == "menu" and not (d.stop_after_fade and d.fade_to <= 0.0):
			return   # already looping (or fading in)
	var cold := not _any_deck_audible()
	_fade_out_all(MENU_XFADE_S)
	_start("menu", MENU_FADE_IN_S if cold else MENU_XFADE_S, 0.0)


## A match is loading: everything fades out over 1.5 s.
func enter_loading() -> void:
	_cancel_schedules()
	state = State.LOADING
	_fade_out_all(LOADING_FADE_S)


## A match begins for the local player: the faction's opening cue now, its first track after
## FIRST_TRACK_S. An unknown faction gets silence.
func enter_game(fid: String) -> void:
	_cancel_schedules()
	if state != State.LOADING:
		_fade_out_all(LOADING_FADE_S)
	state = State.GAME
	faction = fid
	_bag.clear()
	_last_track = ""
	var cue := "opening_%s" % fid
	if has(cue):
		var s := Audio.load_stream(str(_entries[cue]["file"]))
		if s != null:
			_cue_player.stop()
			_cue_player.stream = s
			_cue_player.volume_db = OPENING_DB
			_cue_player.play()
			current = cue
	if not tracks_of(fid).is_empty():
		_next_track_at = now() + FIRST_TRACK_S


## The match ended (SEQ-02): music out over 1.2 s, the stinger at 0.6 s, then the score bed.
func enter_end(won: bool, fid: String) -> void:
	_cancel_schedules()
	state = State.END
	_fade_out_all(END_FADE_S)
	_stinger = ("victory_" if won else "defeat_") + fid
	_stinger_at = now() + STINGER_AT_S


## Plays `cue` now on a free deck with no fade (tests, scripted moments). False when missing.
func play_now(cue: String, gain_db: float = 0.0) -> bool:
	if not has(cue):
		return false
	_fade_out_all(0.0)
	return _start(cue, 0.0, gain_db) != null


## Fades everything out over `fade_s` (0 = stop now) and forgets pending tracks.
func stop(fade_s: float) -> void:
	_cancel_schedules()
	state = State.SILENT
	_fade_out_all(fade_s)
	if fade_s <= 0.0 and _cue_player != null:
		_cue_player.stop()
	if fade_s <= 0.0:
		current = ""


func _cancel_schedules() -> void:
	_next_track_at = -1.0
	_stinger_at = -1.0
	_score_at = -1.0
	_stinger_deck = null


# --- decks ----------------------------------------------------------------------------------

func _any_deck_audible() -> bool:
	var t := now()
	for d in _decks:
		if d.busy() and d.amp_at(t) > 0.05:
			return true
	return false


func _fade_out_all(fade_s: float) -> void:
	var t := now()
	for d in _decks:
		if not d.busy():
			continue
		if fade_s <= 0.0:
			_release(d)
			continue
		if d.stop_after_fade and d.fade_to <= 0.0:
			continue   # already fading out
		d.fade_from = d.amp_at(t)
		d.fade_to = 0.0
		d.fade_t0 = t
		d.fade_len = fade_s
		d.stop_after_fade = true


func _release(d: Deck) -> void:
	d.player.stop()
	d.player.stream = null
	d.cue = ""
	d.stop_after_fade = false
	d.fade_len = 0.0
	if _track_deck == d:
		_track_deck = null


## The deck for a new piece: an idle one, else the quieter (it is cut).
func _free_deck() -> Deck:
	var t := now()
	var best: Deck = null
	for d in _decks:
		if not d.busy():
			return d
		if best == null or d.amp_at(t) < best.amp_at(t):
			best = d
	_release(best)
	return best


func _start(cue: String, fade_in_s: float, gain_db: float) -> Deck:
	if not has(cue):
		Audio.note_missing("music:" + cue)
		return null
	var s := Audio.load_stream(str(_entries[cue]["file"]))
	if s == null:
		Audio.note_missing("music:" + cue)
		return null
	var d := _free_deck()
	var t := now()
	d.cue = cue
	d.t_start = t
	d.loop = bool(_entries[cue].get("loop", false))
	d.length = s.get_length()
	d.gain_db = gain_db
	d.fade_from = 0.0 if fade_in_s > 0.0 else 1.0
	d.fade_to = 1.0
	d.fade_t0 = t
	d.fade_len = fade_in_s
	d.stop_after_fade = false
	d.player.stream = s
	d.player.volume_db = _db(d, t)
	d.player.play()
	current = cue
	Audio.stats["played"] += 1
	return d


func _db(d: Deck, t: float) -> float:
	var a := d.amp_at(t)
	return SILENT_DB if a <= 0.0001 else d.gain_db + linear_to_db(a)


# --- the game rotation ----------------------------------------------------------------------

## Next track from the shuffle bag (refilled when empty; never the last track twice in a row).
func next_from_bag() -> String:
	if _bag.is_empty():
		_bag = tracks_of(faction)
		for i in range(_bag.size() - 1, 0, -1):
			var j := rng.randi_range(0, i)
			var tmp := _bag[i]
			_bag[i] = _bag[j]
			_bag[j] = tmp
		if _bag.size() > 1 and _bag[0] == _last_track:
			var tmp := _bag[0]
			_bag[0] = _bag[_bag.size() - 1]
			_bag[_bag.size() - 1] = tmp
	if _bag.is_empty():
		return ""
	var cue: String = _bag.pop_front()
	_last_track = cue
	return cue


func _start_next_track() -> void:
	_next_track_at = -1.0
	var cue := next_from_bag()
	if cue == "":
		return
	_track_deck = _start(cue, TRACK_FADE_IN_S, 0.0)


## Called once per frame by Audio._process (and by tests with a pinned clock).
func update() -> void:
	var t := now()
	for d in _decks:
		if not d.busy():
			continue
		if d.stop_after_fade and d.fade_done(t):
			_release(d)
			continue
		d.player.volume_db = _db(d, t)
		if not d.loop and d.length > 0.0 and t >= d.t_start + d.length:
			var was_track := d == _track_deck
			_release(d)
			if was_track and state == State.GAME:
				last_gap_s = rng.randf_range(GAP_MIN_S, GAP_MAX_S)
				_next_track_at = t + last_gap_s
	if state == State.GAME and _next_track_at >= 0.0 and t >= _next_track_at:
		_start_next_track()
	if state == State.END:
		if _stinger_at >= 0.0 and t >= _stinger_at:
			_stinger_at = -1.0
			_stinger_deck = _start(_stinger, 0.0, 0.0)
			var at := float(_entries.get(_stinger, {}).get("xfade_to_score_s", SCORE_XFADE_DEFAULT_S))
			if has("score"):
				_score_at = t + at
		if _score_at >= 0.0 and t >= _score_at:
			_score_at = -1.0
			if _stinger_deck != null and _stinger_deck.busy():
				var sd := _stinger_deck
				sd.fade_from = sd.amp_at(t)
				sd.fade_to = 0.0
				sd.fade_t0 = t
				sd.fade_len = SCORE_XFADE_S
				sd.stop_after_fade = true
			_start("score", SCORE_XFADE_S, 0.0)
			_stinger_deck = null
	if current != "" and not is_playing():
		current = ""
