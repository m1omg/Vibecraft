extends "res://tests/test_case.gd"
## The data contract (data/SCHEMA.md): every table loads and validates, the slice roster of
## docs/design/slice-content.json is fully present, derived hero stats match the faction docs,
## ability ranks resolve, rules merge from several files, and Defs validation catches mistakes.

const SLICE_CONTENT := "res://docs/design/slice-content.json"


func test_tables_load_without_validation_errors() -> void:
	assert_eq(Defs.errors.size(), 0, "validation errors: %s" % str(Defs.errors))
	assert_eq(Defs.factions.has("kingdom") and Defs.factions.has("clans"), true, "both slice factions")
	assert_true(Defs.abilities.size() >= 60, "abilities (%d)" % Defs.abilities.size())
	assert_true(Defs.items.size() >= 45, "items (%d)" % Defs.items.size())
	assert_true(Defs.buffs.size() >= 40, "buffs (%d)" % Defs.buffs.size())
	assert_eq(Defs.heroes.size(), 4, "four slice heroes")
	assert_eq(Defs.camps.size(), 10, "ten camp templates")
	assert_true(Defs.shops.has("neutral_weighstall") and Defs.shops.has("kingdom_curio_cabinet")
		and Defs.shops.has("clans_tea_tent"), "shops")
	assert_eq(int(Defs.rule("economy.gold_per_trip", 0)), 10, "rules from factions.json")
	assert_eq(int(Defs.rule("heroes.level_cap", 0)), 10, "rules from heroes.json")
	assert_near(float(Defs.rule("items.recall_channel", 0.0)), 5.0, 1e-6, "rules from items.json")
	assert_near(float(Defs.rule("creeps.leash", 0.0)), 18.75, 1e-6, "rules from creep_camps.json")
	assert_near(float(Defs.rule("neutral.use_range", 0.0)), 7.0, 1e-6, "rules from shops.json")
	assert_eq(str(Defs.rule("status.same_buff", "")), "refresh", "rules from buffs.json")
	assert_eq(Defs.rule("no.such.rule", 42), 42, "fallback")
	assert_eq(Defs.text("upkeep_tier_2"), "Upkeep 60 %", "string table")
	assert_eq(Defs.text("missing_key"), "missing_key", "missing string falls back to its key")


func test_slice_content_roster_is_in_data() -> void:
	var sc: Dictionary = Defs.load_json(SLICE_CONTENT)
	assert_false(sc.is_empty(), "slice-content.json readable")
	var missing: Array = []
	for fid: String in ["kingdom", "clans"]:
		var f: Dictionary = sc["factions"][fid]
		for key: String in ["units", "buildings"]:
			for e: Dictionary in f[key]:
				if not Defs.has_unit(str(e["id"])):
					missing.append(e["id"])
		for e: Dictionary in f["heroes"]:
			if not Defs.heroes.has(str(e["id"])):
				missing.append(e["id"])
			for a: Dictionary in e["abilities"]:
				if not Defs.abilities.has(str(a["id"])):
					missing.append(a["id"])
		for e: Dictionary in f["research"]:
			if not Defs.upgrades.has(str(e["id"])):
				missing.append(e["id"])
		for e: Dictionary in f["unit_abilities"]:
			if not Defs.abilities.has(str(e["id"])):
				missing.append(e["id"])
		for e: Dictionary in f["shop_items"]:
			if not Defs.items.has(str(e["id"])):
				missing.append(e["id"])
	var n: Dictionary = sc["neutrals"]
	for e: Dictionary in n["creeps"]:
		if not Defs.has_unit(str(e["id"])):
			missing.append(e["id"])
	for a: Variant in n["creep_abilities"]:
		if not Defs.abilities.has(str(a)):
			missing.append(a)
	for e: Dictionary in n["camps"]:
		if not Defs.camps.has(str(e["id"])):
			missing.append(e["id"])
	for b: Dictionary in n["buildings"]:
		if not Defs.has_unit(str(b["id"])):
			missing.append(b["id"])
	for sec: String in ["weighstall", "power_ups", "permanent", "charged"]:
		for e: Dictionary in n["items"][sec]:
			if not Defs.items.has(str(e["id"])):
				missing.append(e["id"])
	for c: Variant in sc["commands_common"]:
		if not Defs.abilities.has(str(c)):
			missing.append(c)
	assert_eq(missing, [], "every slice id has a def")


func test_slice_stats_match_slice_content() -> void:
	var sc: Dictionary = Defs.load_json(SLICE_CONTENT)
	for fid: String in ["kingdom", "clans"]:
		for e: Dictionary in sc["factions"][fid]["units"]:
			var d := Defs.unit(str(e["id"]))
			assert_near(float(d["hp"]), float(e["hp"]), 1e-6, "%s hp" % e["id"])
			assert_near(float(d["speed"]), float(e["speed_mps"]), 1e-6, "%s speed" % e["id"])
			assert_eq(d["attack"]["damage"], e["attack"]["damage"], "%s damage" % e["id"])
			assert_near(float(d["attack"]["range"]), float(e["attack"]["range_m"]), 1e-6, "%s range" % e["id"])
			assert_eq(int(d["cost"].get("gold", -1)), int(e["cost"]["gold"]), "%s gold" % e["id"])
		for e: Dictionary in sc["factions"][fid]["buildings"]:
			var d := Defs.unit(str(e["id"]))
			assert_near(float(d["hp"]), float(e["hp"]), 1e-6, "%s hp" % e["id"])
			assert_eq(d["footprint"], e["footprint_cells"], "%s footprint" % e["id"])
			assert_eq(int(d.get("food_provided", 0)), int(e.get("food_provided", 0)), "%s food" % e["id"])
	for e: Dictionary in sc["neutrals"]["creeps"]:
		var d := Defs.unit(str(e["id"]))
		assert_eq(int(d["level"]), int(e["level"]), "%s level" % e["id"])
		assert_eq(str(d["attack"]["type"]), str(e["attack"]["type"]), "%s attack type" % e["id"])
	var fp: Dictionary = sc["match"]["footprint_cells"]
	assert_eq(Defs.unit("kingdom_moot_hall")["footprint"], fp["hall"], "hall 16 x 16 cells")
	assert_eq(Defs.unit("clans_grapple_yard")["footprint"], fp["production_altar_shop_research"], "production 12 x 12")
	assert_eq(Defs.unit("kingdom_croft")["footprint"], fp["supply"], "supply 8 x 8")
	assert_eq(Defs.unit("clans_bow_mast")["footprint"], fp["tower"], "tower 4 x 4")
	assert_eq(Defs.unit("gold_mine")["footprint"], [12.0, 12.0], "Gold Seam 12 x 12")


## kingdom.md §6.2 and clans.md §6.1 derived tables (HP / mana / armour / damage / cooldown).
func test_hero_stats_match_faction_doc_tables() -> void:
	var rows := {
		"kingdom_wheel_marshal": [[1, 675, 240, 4.6, 24, 30, 1.77], [5, 925, 330, 6.1, 34, 40, 1.64], [10, 1250, 465, 8.2, 47, 53, 1.49]],
		"kingdom_firewright": [[1, 500, 315, 2.6, 24, 30, 1.77], [5, 675, 495, 3.8, 36, 42, 1.67], [10, 900, 720, 5.3, 51, 57, 1.55]],
		"clans_hero_uncut": [[1, 575, 210, 4.6, 24, 33, 1.39], [5, 775, 300, 6.7, 31, 40, 1.27], [10, 1025, 405, 9.7, 41, 50, 1.12]],
		"clans_hero_skymirror": [[1, 500, 330, 2.2, 23, 31, 1.80], [5, 650, 495, 3.4, 34, 42, 1.69], [10, 875, 720, 4.9, 49, 57, 1.58]],
	}
	for hid: String in rows:
		for r: Array in rows[hid]:
			var st := Defs.hero_stats(hid, int(r[0]))
			var tag := "%s level %d" % [hid, r[0]]
			assert_near(float(st["hp"]), float(r[1]), 0.01, tag + " hp")
			assert_near(float(st["mana"]), float(r[2]), 0.01, tag + " mana")
			assert_near(float(st["armor"]), float(r[3]), 0.051, tag + " armour")
			assert_eq(int(st["damage_min"]), int(r[4]), tag + " damage min")
			assert_eq(int(st["damage_max"]), int(r[5]), tag + " damage max")
			assert_near(float(st["cooldown"]), float(r[6]), 0.006, tag + " cooldown")
		var d := Defs.unit(hid)
		assert_true((d["flags"] as Array).has("hero"), "%s unit def is a hero" % hid)
		assert_eq((d["hero_abilities"] as Array).size(), 4, "%s kit" % hid)
		assert_near(float(d["sight"]), 28.1, 1e-6, "%s hero sight" % hid)
	assert_near(Defs.xp_for_level(5), 1400.0, 1e-6, "XP table")
	assert_eq(Defs.level_for_xp(499.0), 2, "level from XP")
	assert_eq(Defs.level_for_xp(99999.0), 10, "capped at 10")


func test_ability_ranks_resolve() -> void:
	var r1 := Defs.ability_rank("clans_braid_lash", 1)
	var r3 := Defs.ability_rank("clans_braid_lash", 3)
	assert_near(float(r1["mana"]), 70.0, 1e-6, "shared mana")
	assert_near(float(r1["cooldown"]), 14.0, 1e-6, "rank 1 cooldown")
	assert_near(float(r3["cooldown"]), 10.0, 1e-6, "rank 3 cooldown")
	assert_near(float(r3["damage"]), 110.0, 1e-6, "rank 3 damage")
	assert_near(float(r1["pull"]), 3.0, 1e-6, "params merged")
	assert_near(float(r1["cast_point"]), 0.3, 1e-6, "default cast point")
	assert_near(float(Defs.ability_rank("clans_sunglint", 1)["cast_point"]), 0.4, 1e-6, "ability cast point")
	assert_eq(Defs.ability_levels("kingdom_the_wagon_ring"), 1, "ultimate has one rank")
	assert_eq(Defs.ability_levels("kingdom_naphtha_flask"), 3, "normal hero ability has three")
	var bw := Defs.ability_rank("clans_bronze_window", 2)
	assert_near(float(bw["mana"]), 50.0, 1e-6, "per-rank mana")
	assert_near(float(bw["area"]), 14.0, 1e-6, "per-rank area")
	for id: String in Defs.abilities:
		var a: Dictionary = Defs.abilities[id]
		if a.get("owner", "") == "hero":
			assert_true(a.has("hotkey") and a.has("slot"), "%s has a mnemonic hotkey and slot" % id)


func test_upgrades_research_and_building_upgrades() -> void:
	var tb := Defs.upgrade("kingdom_tempered_blades")
	assert_eq((tb["levels"] as Array).size(), 2, "slice weapon lines have 2 levels")
	assert_eq(int(Defs.upgrade_level("kingdom_tempered_blades", 2)["requires_tier"]), 2, "level 2 needs T2")
	var wb := Defs.upgrade("kingdom_walled_burg")
	assert_eq(str(wb["kind"]), "building_upgrade", "hall tier is a building upgrade")
	assert_eq(str(Defs.unit("kingdom_walled_burg")["upgrade_of"]), "kingdom_moot_hall", "of the Moot Hall")
	assert_eq(Defs.researched_at("kingdom_walled_burg"), ["kingdom_moot_hall"], "started at the hall")
	assert_eq(Defs.researched_at("clans_up_melee"), ["clans_casting_pit"], "research building index")
	assert_eq(Defs.trained_at("clans_sling_cart"), ["clans_grapple_yard"], "trained-at index")
	assert_eq(Defs.trained_at("kingdom_firewright"), ["kingdom_oath_hall"], "heroes at the altar")


func test_prd_constants_match_rules() -> void:
	for pair: Array in [[0.05, 0.00380], [0.1, 0.01475], [0.2, 0.05570], [0.25, 0.08474], [0.4, 0.20155]]:
		assert_near(Defs.prd_c(float(pair[0])), float(pair[1]), 0.00002, "PRD C for %s" % pair[0])


func test_validation_catches_broken_data() -> void:
	var before := Defs.errors.size()
	Defs._card_key("test card", {"Q": "a"}, "Q", "b")
	assert_eq(Defs.errors.size(), before + 1, "duplicate hotkey on a card")
	Defs._validate_unit("broken_building", {"name": "x", "kind": "building", "hp": 10, "radius": 1.0,
		"footprint": [0, 0], "abilities": [], "trains": ["nope"], "requires": ["nothing_here"]})
	assert_true(Defs.errors.size() >= before + 4, "footprint, unknown trains and requires reported")
	var saved := Defs.camps.duplicate(true)
	Defs.camps["camp_bad"] = {"creeps": [["creep_sootcoat_cutpurse", 2]], "total_level": 5, "raw_xp": 1}
	var n := Defs.errors.size()
	Defs._validate_camps()
	assert_true(Defs.errors.size() >= n + 2, "camp level and XP sums checked")
	Defs.camps = saved
	Defs.errors.resize(before)
