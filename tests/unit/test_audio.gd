extends "res://tests/test_case.gd"
## The Audio director against the real manifests (assets/audio/{sfx,voice,music}/manifest.json):
## every listed take loads, takes never repeat back to back, the variation stays small and is a
## stateless hash, missing ids and speakers stay silent, aliases stand in for unrecorded
## families, the opening cue plays at match start, the end sequence ducks over 1.2 s, UI clicks
## and denies play in the local faction's material, and orders ask for the right ack.
## Runs with the Dummy audio driver (timing is Audio.now(), pinned by clock_override).

const VOICED: Array[String] = ["kingdom_hodman", "kingdom_flail_levy", "kingdom_pavisier",
	"kingdom_hookgunner", "clans_yurtwright", "clans_grappler"]


func after_each() -> void:
	super.after_each()
	Audio.clock_override = -1.0
	Audio.listener_focus = Vector3.INF
	Audio.reset_state()
	Audio.ui_faction = "kingdom"
	Audio.local_player = 0


static func _json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	return JSON.parse_string(f.get_as_text()) if f != null else null


## Every path in the three manifest files (read straight from disk, so an entry the director
## would skip still fails here) exists, imports and loads as a non-empty AudioStream.
func test_every_manifest_path_loads() -> void:
	var paths: Array = []
	var sfx: Variant = _json(Audio.SFX_MANIFEST)
	assert_true(sfx is Dictionary and not (sfx as Dictionary).is_empty(), "the SFX manifest parses")
	for fam: String in sfx:
		for p: Variant in sfx[fam]:
			paths.append(str(p))
	var vo: Variant = _json(Audio.VOICE_MANIFEST)
	assert_true(vo is Dictionary and (vo as Dictionary).get("speakers") is Dictionary, "the voice manifest parses")
	for sp: String in vo["speakers"]:
		var cats: Dictionary = vo["speakers"][sp].get("categories", {})
		for c: String in cats:
			for p: Variant in cats[c]:
				paths.append(str(p))
	var mu: Variant = _json(Audio.MUSIC_MANIFEST)
	assert_true(mu is Dictionary and (mu as Dictionary).has("opening_kingdom"), "the music manifest lists the kingdom opening cue")
	for cue: String in mu:
		paths.append(str(mu[cue]["file"]))
	assert_true(paths.size() > 100, "the manifests list the P0 set (%d takes)" % paths.size())
	var bad: Array = []
	for p: String in paths:
		var s := load(p) as AudioStream if ResourceLoader.exists(p) else null
		if s == null or s.get_length() <= 0.0:
			bad.append(p)
	assert_eq(bad, [], "takes that do not load")
	var listed: Dictionary = Audio.manifest_paths()
	assert_eq((listed["sfx"] as Array).size() + (listed["voice"] as Array).size() + (listed["music"] as Array).size(),
		_unique(paths).size(), "the director knows every take")


static func _unique(a: Array) -> Array:
	var seen := {}
	for x: Variant in a:
		seen[x] = true
	return seen.keys()


func test_voiced_units_have_what_yes_and_attack() -> void:
	for did in VOICED:
		assert_true(Audio._speakers.has(did), "%s has a speaker" % did)
		var cats: Dictionary = Audio._speakers.get(did, {})
		for cat: String in ["what", "yes", "attack"]:
			var n := (cats.get(cat, PackedStringArray()) as PackedStringArray).size()
			# Attack falls back to Yes for speakers that have no attack takes yet
			assert_true(n > 0 or (cat == "attack" and (cats.get("yes", PackedStringArray()) as PackedStringArray).size() > 0),
				"%s speaks %s" % [did, cat])


func test_takes_never_repeat_back_to_back() -> void:
	for fam: String in ["hit_flesh_l", "sw_slash", "bombard_hit", "ui_click_kingdom", "vox_death_clans"]:
		var last: AudioStream = null
		var seen := {}
		for i in 60:
			var s := Audio.pick_stream(fam)
			assert_true(s != null, "%s has takes" % fam)
			assert_true(s != last, "%s pick %d repeats the previous take" % [fam, i])
			last = s
			seen[s] = true
		assert_eq(seen.size(), (Audio._families[fam] as PackedStringArray).size(), "%s uses every take" % fam)
	var w := make_world()
	var u := w.spawn_unit("kingdom_pavisier", 0, Vector3(10, 0, 10))
	var prev: AudioStream = null
	for i in 12:
		Audio.clock_override = 1000.0 + i * 2.0
		assert_true(Audio.play_voice(u, "yes"), "Yes %d plays" % i)
		assert_true(Audio._ack.stream != prev, "voice take %d repeats the previous one" % i)
		prev = Audio._ack.stream


func test_variation_is_small_and_stateless() -> void:
	for seq in 200:
		var v: Vector2 = Audio.variation("hit_flesh_l", seq)
		assert_true(absf(v.x - 1.0) <= 0.0301 and absf(v.y) <= 1.501, "variation %d in range (%s)" % [seq, v])
		assert_eq(v, Audio.variation("hit_flesh_l", seq), "variation %d is a hash" % seq)
		assert_eq(Audio.variation("hit_flesh_l", seq, true).x, 1.0, "a computed pitch gets no second jitter")
	var spread := 0.0
	for seq in 50:
		spread = maxf(spread, absf(Audio.variation("sw_blunt", seq).x - 1.0))
	assert_true(spread > 0.01, "the pitch does vary (%f)" % spread)
	Audio.clock_override = 50.0
	assert_true(Audio.play_3d("hit_wood_l", Vector3.ZERO), "a 3D one-shot plays")
	var p: AudioStreamPlayer3D = null
	for v: Variant in Audio._world:
		if v.family == "hit_wood_l":
			p = v.player
	assert_true(p != null and absf(p.volume_db) <= 1.501 and absf(p.pitch_scale - 1.0) <= 0.0301,
		"the voice carries the variation")


func test_missing_ids_and_speakers_stay_silent() -> void:
	Audio.clock_override = 70.0
	assert_false(Audio.play_2d("ui_no_such_click"), "a missing UI id is silent")
	assert_false(Audio.has_family("sw_magic"), "sw_magic has no takes and no alias")
	assert_eq(Audio.event("whoosh", Vector3.ZERO, {"family": "sw_magic", "seed": 1}), 0, "its whoosh is silent")
	var w := make_world()
	var jav := w.spawn_unit("clans_javelineer", 1, Vector3(12, 0, 12))
	var lengths: Array = []
	var cb := func(_u: Node, _c: String, length: float) -> void:
		lengths.append(length)
	Audio.voice_started.connect(cb)
	var acks := int(Audio.stats["acks"])
	assert_false(Audio.play_voice(jav, "what"), "an unvoiced speaker says nothing")
	Audio.voice_started.disconnect(cb)
	assert_eq(int(Audio.stats["acks"]), acks, "no line started")
	assert_eq(lengths, [0.0], "the body still acknowledges (length 0)")
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(14, 0, 12))
	Audio.clock_override = 80.0
	for i in 6:
		Audio.clock_override = 80.0 + i * 0.45
		Audio.play_voice(hod, "what")
	assert_true(Audio.last_ack_category != "annoyed", "annoyed only plays when recorded")


func test_alias_stands_in_for_unrecorded_family() -> void:
	assert_false(Audio._families.has("sw_chop"), "sw_chop is not recorded yet")
	assert_true(Audio.has_family("sw_chop"), "but it resolves through its alias")
	assert_eq(Audio.resolve_alias("sw_chop"), "sw_slash", "alias")
	assert_eq(Audio.resolve_alias("sw_blunt"), "sw_blunt", "recorded families resolve to themselves")
	assert_near(Audio.peak_s("sw_chop"), Audio.peak_s("sw_slash"), 1e-6, "the alias's measured peak times the whoosh")
	Audio.clock_override = 90.0
	assert_eq(Audio.event("whoosh", Vector3.ZERO, {"family": "sw_chop", "seed": 2}), 1, "a chop whooshes")


func test_opening_cue_at_match_start_and_end_sequence() -> void:
	Audio.clock_override = 100.0
	Audio.match_started("kingdom", 0)
	assert_eq(Audio.music_id, "opening_kingdom", "the kingdom opening cue plays at match start")
	assert_eq(Audio.ui_faction, "kingdom", "the UI material follows the local faction")
	Audio.match_started("clans", 1)
	assert_eq(Audio.ui_faction, "clans", "clans UI material")
	assert_true(Audio.has_music("opening_clans"), "the clans opening cue is recorded")
	assert_eq(Audio.music_id, "opening_clans", "the clans opening cue plays at match start")
	Audio.match_started("kingdom", 0)
	# the end: the signal arrives inside the tick and only records; _process ducks over 1.2 s
	Events.match_ended.emit(0, "annihilation")
	assert_eq(Audio.duck_db("SFX"), 0.0, "nothing changes inside the tick")
	Audio._process(0.0)
	assert_near(Audio.duck_db("SFX"), 0.0, 0.01, "the duck starts at 0 dB")
	Audio.clock_override = 100.6
	assert_near(Audio.duck_db("SFX"), -5.0, 0.01, "half way at 600 ms")
	assert_near(Audio.duck_db("Ambience"), -3.0, 0.01, "ambience half way")
	Audio._process(0.0)
	Audio.clock_override = 101.3
	Audio._process(0.0)
	assert_near(Audio.duck_db("SFX"), -10.0, 0.01, "SFX −10 dB after 1.2 s")
	assert_eq(Audio.music_id, "victory_kingdom", "the music faded out and the victory stinger followed at 600 ms")
	assert_near(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("SFX")), -10.0, 0.01, "the bus follows")
	Audio.match_started("kingdom", 0)
	assert_eq(Audio.duck_db("SFX"), 0.0, "a new match lifts the end ducks")


func test_ui_click_and_deny_use_the_local_material() -> void:
	Audio.clock_override = 200.0
	Audio.ui_faction = "clans"
	var played := int(Audio.stats["played"])
	assert_true(Audio.ui_click(), "a clans click")
	assert_true(Audio.deny("error"), "an error deny")
	assert_eq(Audio._deny.stream != null, true, "on the Deny player")
	Audio.clock_override = 200.05
	assert_false(Audio.deny("error"), "denies are spaced 150 ms")
	assert_true(Audio.deny("disabled"), "the disabled deny is its own family")
	assert_eq(int(Audio.stats["played"]), played + 3, "three sounds started")
	Audio.ui_faction = "kingdom"
	Audio.clock_override = 201.0
	assert_true(Audio.ui_click(), "a kingdom click")


func test_orders_ask_for_the_right_ack() -> void:
	var w := make_world()
	var own := w.spawn_unit("kingdom_pavisier", 0, Vector3(10, 0, 10))
	var foe := w.spawn_unit("clans_grappler", 1, Vector3(14, 0, 10))
	var pal := w.spawn_unit("kingdom_hodman", 0, Vector3(10, 0, 14))
	var ci := CommandInput.new()
	track(ci)
	ci.world = w
	ci.player_id = 0
	assert_eq(ci.ack_category({"type": "smart", "target": foe.id}), "attack", "right-click on an enemy -> Attack")
	assert_eq(ci.ack_category({"type": "smart", "target": pal.id}), "yes", "right-click on a friend -> Yes")
	assert_eq(ci.ack_category({"type": "smart", "pos": Vector3(3, 0, 3)}), "yes", "right-click on the ground -> Yes")
	assert_eq(ci.ack_category({"type": "attack_move", "pos": Vector3(3, 0, 3)}), "attack", "attack-move -> Attack")
	assert_eq(ci.ack_category({"type": "attack", "target": foe.id}), "attack", "attack -> Attack")
	assert_eq(ci.ack_category({"type": "patrol", "pos": Vector3(3, 0, 3)}), "yes", "patrol -> Yes")
	assert_true(own != null, "own unit")


# --- music director (MUS-01 P0) ---------------------------------------------------------------

func _deck_of(cue: String) -> Variant:
	for d: Variant in Audio.music._decks:
		if d.cue == cue:
			return d
	return null


func test_bus_levels_follow_the_mix_table() -> void:
	Audio.reset_state()
	for bus: String in Audio.BUS_DEFAULT_DB:
		var idx := AudioServer.get_bus_index(bus)
		assert_true(idx > 0, "bus %s exists" % bus)
		assert_near(AudioServer.get_bus_volume_db(idx), float(Audio.BUS_DEFAULT_DB[bus]), 0.01, "%s rests at its §5.1 level" % bus)
	assert_eq(AudioServer.get_bus_send(AudioServer.get_bus_index("Alerts")), &"Voice", "Alerts feeds Voice")
	assert_near(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Voice")), 0.0, 0.01, "Voice stays at 0 dB")


func test_menu_theme_fades_in_from_silence_and_keeps_looping() -> void:
	Audio.clock_override = 300.0
	Audio.menu_entered()
	assert_eq(Audio.music_id, "menu", "the menu theme starts")
	var d: Variant = _deck_of("menu")
	assert_true(d != null and d.loop, "on a deck, looping")
	assert_true(d.player.volume_db <= -60.0, "from silence")
	Audio.clock_override = 300.375
	Audio._process(0.0)
	assert_near(d.player.volume_db, linear_to_db(sin(0.25 * PI)), 0.05, "half way through the 0.75 s fade (equal power)")
	Audio.clock_override = 300.8
	Audio._process(0.0)
	assert_near(d.player.volume_db, 0.0, 0.01, "full level after 0.75 s")
	Audio.menu_entered()
	assert_eq(_deck_of("menu"), d, "entering the menu again keeps the theme going (no restart)")
	Audio.clock_override = 300.8 + 400.0
	Audio._process(0.0)
	assert_eq(Audio.music_id, "menu", "a loop never ends by itself")


func test_menu_fades_out_while_a_match_loads_then_the_rotation_runs() -> void:
	Audio.music.rng.seed = 7
	Audio.clock_override = 500.0
	Audio.menu_entered()
	Audio.clock_override = 501.0
	Audio._process(0.0)
	Audio.match_loading()
	Audio.clock_override = 501.75
	Audio._process(0.0)
	var d: Variant = _deck_of("menu")
	assert_true(d != null and d.player.volume_db < -1.0 and d.player.volume_db > -60.0, "the menu theme is fading out")
	Audio.match_started("kingdom", 0)
	assert_eq(Audio.music_id, "opening_kingdom", "the opening cue plays at once")
	assert_eq(Audio.music._cue_player.bus, &"Alerts", "on the Alerts bus")
	assert_near(Audio.music._cue_player.volume_db, -4.0, 0.01, "at -4 dB")
	Audio.clock_override = 502.6
	Audio._process(0.0)
	assert_eq(_deck_of("menu"), null, "the menu theme is gone 1.5 s after loading began")
	assert_near(Audio.music.next_track_in(), 501.75 + 6.0 - 502.6, 0.01, "the first track waits 6 s from the match start")
	Audio.clock_override = 507.76
	Audio._process(0.0)
	var first: String = Audio.music.track_deck_cue()
	assert_true(first in ["kingdom_1", "kingdom_2", "kingdom_3"], "a kingdom track starts (%s)" % first)
	var td: Variant = _deck_of(first)
	assert_true(td.player.volume_db < -10.0, "it fades in")
	Audio.clock_override = 509.8
	Audio._process(0.0)
	assert_near(td.player.volume_db, 0.0, 0.01, "full level after the 2 s fade-in")
	assert_false(td.loop, "in-game tracks never loop")
	var played: Array = [first]
	var t: float = td.t_start + td.length + 0.01
	for i in 5:
		Audio.clock_override = t
		Audio._process(0.0)
		assert_eq(Audio.music.track_deck_cue(), "", "track %d ended: silence" % i)
		var gap: float = Audio.music.last_gap_s
		assert_true(gap >= 20.0 and gap <= 40.0, "a 20-40 s gap (%.1f)" % gap)
		Audio.clock_override = t + gap - 0.05
		Audio._process(0.0)
		assert_eq(Audio.music.track_deck_cue(), "", "still silent just before the gap ends")
		Audio.clock_override = t + gap + 0.01
		Audio._process(0.0)
		var cue: String = Audio.music.track_deck_cue()
		assert_true(cue.begins_with("kingdom_"), "the next kingdom track (%s)" % cue)
		assert_true(cue != played[played.size() - 1], "never the same track twice in a row")
		played.append(cue)
		var nd: Variant = _deck_of(cue)
		t = nd.t_start + nd.length + 0.01
	var first_three := {}
	for c: String in played.slice(0, 3):
		first_three[c] = true
	assert_eq(first_three.size(), 3, "the shuffle bag plays all three before repeating (%s)" % [played])


func test_clans_rotation_uses_clans_tracks() -> void:
	Audio.clock_override = 700.0
	Audio.match_started("clans", 1)
	assert_eq(Audio.music_id, "opening_clans", "the clans opening cue")
	Audio.clock_override = 706.01
	Audio._process(0.0)
	assert_true(Audio.music.track_deck_cue().begins_with("clans_"), "a clans track follows")
	assert_eq(Audio.music.tracks_of("clans").size(), 3, "three clans tracks")


func test_stinger_hands_over_to_the_looping_score_bed() -> void:
	Audio.clock_override = 900.0
	Audio.match_started("clans", 1)
	Audio.clock_override = 906.5
	Audio._process(0.0)
	var track: String = Audio.music.track_deck_cue()
	assert_true(track != "", "a track plays when the match ends")
	Events.match_ended.emit(0, "annihilation")   # player 1 (local) lost
	Audio._process(0.0)
	Audio.clock_override = 907.1
	Audio._process(0.0)
	assert_eq(Audio.music_id, "defeat_clans", "the defeat stinger at 600 ms")
	var td: Variant = _deck_of(track)
	assert_true(td != null and td.player.volume_db < -1.0, "the track is fading out under it")
	Audio.clock_override = 907.75
	Audio._process(0.0)
	assert_eq(_deck_of(track), null, "the track is gone after 1.2 s")
	var at := float(Audio.music._entries["defeat_clans"]["xfade_to_score_s"])
	Audio.clock_override = 907.1 + at - 0.01
	Audio._process(0.0)
	assert_eq(_deck_of("score"), null, "the score waits for the stinger's crossfade point")
	Audio.clock_override = 907.1 + at + 0.01
	Audio._process(0.0)
	var sd: Variant = _deck_of("score")
	assert_true(sd != null and sd.loop, "the score bed enters and loops")
	Audio.clock_override = 907.1 + at + 1.0
	Audio._process(0.0)
	var st: Variant = _deck_of("defeat_clans")
	assert_true(st != null, "the stinger rings on under the crossfade")
	assert_near(db_to_linear(sd.player.volume_db) ** 2 + db_to_linear(st.player.volume_db) ** 2, 1.0, 0.03,
		"an equal-power crossfade")
	Audio.clock_override = 907.1 + at + 2.1
	Audio._process(0.0)
	assert_eq(_deck_of("defeat_clans"), null, "the stinger is out after 2 s")
	Audio.clock_override = 907.1 + at + 300.0
	Audio._process(0.0)
	assert_eq(Audio.music_id, "score", "the score loops until the player leaves")
	Audio.menu_entered()
	Audio.clock_override = 907.1 + at + 301.1
	Audio._process(0.0)
	assert_eq(Audio.music_id, "menu", "back in the menu the theme takes over")
	assert_eq(_deck_of("score"), null, "the score crossfaded out")


func test_pause_muffles_and_ducks_the_music() -> void:
	Audio.clock_override = 1100.0
	Audio.set_paused(true)
	Audio.clock_override = 1100.15
	Audio._process(0.0)
	assert_near(Audio.duck_db("Music"), -3.0, 0.01, "half the -6 dB duck after 150 ms")
	var mid := Audio.filter_hz("Music")
	assert_true(mid < 20500.0 and mid > 1200.0, "the low-pass is closing (%f)" % mid)
	assert_near(mid, sqrt(20500.0 * 1200.0), 1.0, "in log-frequency")
	Audio.clock_override = 1100.4
	Audio._process(0.0)
	assert_near(Audio.duck_db("Music"), -6.0, 0.01, "Music -6 dB")
	assert_near(Audio.duck_db("Ambience"), -10.0, 0.01, "Ambience -10 dB")
	assert_near(Audio.filter_hz("Music"), 1200.0, 0.5, "muffled at 1.2 kHz")
	assert_near(Audio._bus_lowpass("Music").cutoff_hz, 1200.0, 1.0, "the bus filter follows")
	assert_near(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Music")), -18.0, 0.01, "the Music bus rests 6 dB lower")
	Audio.set_paused(false)
	Audio.clock_override = 1100.8
	Audio._process(0.0)
	assert_near(Audio.duck_db("Music"), 0.0, 0.01, "unpaused: no duck")
	assert_near(Audio.filter_hz("Music"), 20500.0, 1.0, "the filter reopens over 300 ms")
	assert_eq(Audio._world[0].player.process_mode, Node.PROCESS_MODE_PAUSABLE, "3D one-shots pause with the tree")
