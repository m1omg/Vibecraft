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
	assert_false(Audio.has_music("opening_clans"), "no clans cue yet")
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
	assert_eq(Audio.music_id, "", "the music has faded out")
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
