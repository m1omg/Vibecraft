extends "res://tests/test_case.gd"
## Fog of war (src/world/fog.gd, rules §14): vision radius and the explored / fogged / visible
## states, cliffs block upward sight, trees occlude and a felled tree opens the view, allies share
## vision, units do not acquire what they cannot see, structures are remembered as ghosts, night
## sight, timed and attack reveals, counts never drift, and the cost of a busy update.


func _fog_world(m: MapData = null) -> World:
	var w := make_world(m if m != null else flat_map(48, 48))
	w.fog.enabled = true
	return w


func test_sight_radius_and_states() -> void:
	var w := _fog_world()
	var u := w.spawn_unit("kingdom_pavisier", 0, Vector3(30.5, 0, 30.5))
	w.fog.update_now(w)
	assert_eq(w.fog.state_at(0, Vector3(30.5, 0, 30.5 + 20.0)), Fog.VISIBLE, "21.9 m day sight: 20 m away is seen")
	assert_eq(w.fog.state_at(0, Vector3(30.5, 0, 30.5 + 23.5)), Fog.UNEXPLORED, "beyond the sight: black mask")
	assert_eq(w.fog.state_at(1, Vector3(30.5, 0, 30.5)), Fog.UNEXPLORED, "the other team sees nothing of it")
	assert_eq(w.fog.state_at(PlayerState.NEUTRAL_HOSTILE, Vector3(80, 0, 80)), Fog.VISIBLE, "neutrals have no fog")
	u.teleport(Vector3(70.5, 0, 70.5))
	w.fog.update_now(w)
	assert_eq(w.fog.state_at(0, Vector3(30.5, 0, 30.5)), Fog.FOGGED, "left behind: explored but fogged")
	assert_eq(w.fog.state_at(0, Vector3(70.5, 0, 70.5)), Fog.VISIBLE, "seen where it stands")
	var tex := w.fog.grid(0)
	var c := w.fog.cell_of(Vector3(30.5, 0, 30.5))
	assert_eq(tex[c.y * w.fog.size.x + c.x], 128, "texture byte 128 = fogged")
	c = w.fog.cell_of(Vector3(70.5, 0, 70.5))
	assert_eq(tex[c.y * w.fog.size.x + c.x], 255, "255 = visible")
	assert_eq(tex[0], 0, "0 = unexplored")


func test_cliffs_block_upward_sight() -> void:
	var m := flat_map(48, 48, 0)
	for ty in 48:
		for tx in range(24, 48):
			m.cliff[m.idx(tx, ty)] = 1
	m.compute_heights()
	var w := _fog_world(m)
	var low := w.spawn_unit("kingdom_pavisier", 0, Vector3(40.5, 0, 40.5))
	var high := w.spawn_unit("kingdom_pavisier", 1, Vector3(56.5, 0, 40.5))
	w.fog.update_now(w)
	assert_false(w.fog.is_visible(0, Vector3(52.5, 0, 40.5)), "the low unit cannot see up the cliff")
	assert_true(w.fog.is_visible(0, Vector3(44.5, 0, 40.5)), "it sees its own level")
	assert_true(w.fog.is_visible(1, Vector3(40.5, 0, 40.5)), "the high unit sees down")
	assert_true(w.fog.can_see(1, low), "high ground spots the low unit")
	assert_false(w.fog.can_see(0, high), "the low unit does not spot the high one")


func test_trees_occlude_and_felled_trees_open_the_view() -> void:
	var m := flat_map(48, 48)
	for y in range(20, 60):
		m.trees.append(Vector2i(40, y))
		m.tree_types.append(0)
	var w := _fog_world(m)
	w.spawn_unit("kingdom_pavisier", 0, Vector3(30.5, 0, 40.5))
	w.fog.update_now(w)
	assert_true(w.fog.is_visible(0, Vector3(40.5, 0, 40.5)), "the tree itself is seen")
	assert_false(w.fog.is_visible(0, Vector3(46.5, 0, 40.5)), "cells behind the tree line are not")
	var i := w.doodads.tree_at_cell(Vector2i(80, 80))
	assert_true(i >= 0, "tree at 40, 40")
	w.doodads.remove_tree(i)
	w.fog.update_now(w)
	assert_true(w.fog.is_visible(0, Vector3(46.5, 0, 40.5)), "a felled tree opens the line behind it")


func test_allies_share_vision_and_acquisition_needs_sight() -> void:
	var w := _fog_world()
	w.add_player(2, 0)   # player 2 on player 0's team
	w.spawn_unit("kingdom_pavisier", 2, Vector3(80.5, 0, 80.5))
	var guard := w.spawn_unit("kingdom_hookgunner", 0, Vector3(20.5, 0, 20.5))
	var foe := w.spawn_unit("clans_grappler", 1, Vector3(20.5, 0, 34.5))
	w.fog.update_now(w)
	assert_true(w.fog.is_visible(0, Vector3(80.5, 0, 80.5)), "allied vision is shared")
	assert_true(w.fog.can_see(0, foe), "the foe at 14 m is in the hookgunner's sight")
	assert_true(guard.find_target(15.0) == foe, "and can be acquired")
	foe.teleport(Vector3(20.5, 0, 50.5))
	w.fog.update_now(w)
	assert_false(w.fog.can_see(0, foe), "30 m away: hidden")
	assert_true(guard.find_target(40.0) == null, "nothing acquired in the fog")
	assert_true(w.fog.can_see(1, foe), "everyone sees their own units")


func test_structures_are_remembered_as_ghosts() -> void:
	var w := _fog_world()
	var hall := w.spawn_unit("clans_shell_hall", 1, Vector3(70, 0, 70))
	var scout := w.spawn_unit("kingdom_pavisier", 0, Vector3(70, 0, 52))
	var raider := w.spawn_unit("clans_grappler", 1, Vector3(80, 0, 70))
	assert_false(w.fog.shows(0, hall), "never seen: not drawn")
	w.fog.update_now(w)
	assert_true(w.fog.shows(0, hall) and w.fog.can_see(0, hall), "seen now")
	scout.teleport(Vector3(10, 0, 10))
	w.fog.update_now(w)
	assert_false(w.fog.can_see(0, hall), "out of sight")
	assert_true(w.fog.shows(0, hall), "but its ghost stays drawn")
	assert_false(w.fog.shows(0, raider), "mobile enemies leave no ghost")


func test_night_sight_and_transition() -> void:
	var w := _fog_world()
	var u := w.spawn_unit("kingdom_pavisier", 0, Vector3(48.5, 0, 48.5))
	w.fog.update_now(w)
	assert_true(w.fog.is_visible(0, Vector3(48.5, 0, 48.5 + 18.0)), "18 m away by day")
	# 18:00 is 200 s after the 08:00 start; the sight changes over 3.2 s
	assert_near(Fog.night_factor(199.0), 0.0, 1e-6, "day before dusk")
	assert_near(Fog.night_factor(201.6), 0.5, 0.01, "half way 1.6 s after dusk")
	assert_near(Fog.night_factor(204.0), 1.0, 1e-6, "night")
	assert_near(Fog.night_factor(200.0 + 240.0 + 1.6), 0.5, 0.01, "half way back after dawn")
	w.time = 210.0
	w.fog.update_now(w)
	assert_false(w.fog.is_visible(0, Vector3(48.5, 0, 48.5 + 18.0)), "12.5 m night sight")
	assert_true(w.fog.is_visible(0, Vector3(48.5, 0, 48.5 + 11.0)), "11 m still seen at night")
	assert_true(u != null, "unit")


func test_reveals_and_attack_reveal() -> void:
	var w := _fog_world()
	w.spawn_unit("kingdom_pavisier", 0, Vector3(10.5, 0, 10.5))
	w.fog.update_now(w)
	var spot := Vector3(70.5, 0, 70.5)
	assert_false(w.fog.is_visible(0, spot), "far away: not seen")
	w.fog.reveal(0, spot, 8.0, 1.0)
	assert_true(w.fog.is_visible(0, spot), "a reveal shows the area at once")
	for i in 31:
		w.step()
	assert_false(w.fog.is_visible(0, spot), "and expires after 1 s")
	assert_eq(w.fog.state_at(0, spot), Fog.FOGGED, "leaving it explored")
	# an attacker the victim's owner cannot see is revealed for 1 s
	var victim := w.spawn_unit("kingdom_pavisier", 0, Vector3(40.5, 0, 40.5))
	var archer := w.spawn_unit("clans_javelineer", 1, Vector3(40.5, 0, 40.5 + 30.0))
	w.fog.update_now(w)
	assert_false(w.fog.can_see(0, archer), "the javelineer starts unseen")
	victim.take_damage(5.0, archer)
	assert_true(w.fog.can_see(0, archer), "hitting from the fog reveals the attacker")


func test_counts_never_drift() -> void:
	var w := _fog_world()
	var units: Array[Unit] = []
	for i in 12:
		units.append(w.spawn_unit("kingdom_pavisier", 0, Vector3(10.5 + i * 6.0, 0, 20.5)))
	for step in 8:
		for i in units.size():
			units[i].teleport(Vector3(10.5 + i * 6.0, 0, 20.5 + step * 4.3))
		w.fog.update_now(w)
	for u in units:
		u.die(null)
	w.step()
	var g: Variant = w.fog._teams[0]
	var sum := 0
	for c in g.counts:
		sum += c
	assert_eq(sum, 0, "every stamp was taken back when the units died")
	assert_eq(w.fog.state_at(0, Vector3(10.5, 0, 20.5)), Fog.FOGGED, "the ground stays explored")


## 2 × 125 units marching at 4.2 m/s for 2 s: the rolling, budgeted re-stamps keep every tick
## cheap and no unit's vision lags more than two cells.
func test_update_cost_with_250_moving_units() -> void:
	var w := _fog_world(flat_map(96, 96))
	var units: Array[Unit] = []
	for i in 250:
		var pid := i % 2
		var row := i / 2
		var x := 20.5 + (row % 25) * 1.5
		var z := 30.5 + (row / 25) * 1.5 + (110.0 if pid == 1 else 0.0)
		units.append(w.spawn_unit("kingdom_pavisier", pid, Vector3(x, 0, z)))
	w.fog.update_now(w)
	var times: Array[float] = []
	var lag := 0.0
	for tick in 60:
		for u in units:
			var dz := 0.14 if u.player_id == 0 else -0.14    # 4.2 m/s
			u.teleport(u.pos + Vector3(0.0, 0.0, dz))
		var t0 := Time.get_ticks_usec()
		w.fog.sim_tick(w, World.DT)
		times.append((Time.get_ticks_usec() - t0) / 1000.0)
	# how far behind its unit's cell does the slowest stamp lag (the budget defers re-stamps)
	for u in units:
		var s: Variant = w.fog._sources.get(u.id)
		var c := w.fog.cell_of(u.pos)
		lag = maxf(lag, Vector2(s.key.x - c.x, s.key.y - c.y).length() * w.fog.cell_m)
	times.sort()
	var avg := 0.0
	for t in times:
		avg += t
	avg /= times.size()
	var slow := machine_slowdown()
	print("    fog per tick: avg %.2f ms, worst %.2f ms (slowdown %.2f), stamp lag %.1f m, last %s" % [avg,
		times[-1], slow, lag, w.fog.last_stats])
	assert_true(avg < 5.0 * slow, "average tick %.1f ms" % avg)
	assert_true(times[-1] < 9.0 * slow, "worst tick %.1f ms" % times[-1])
	assert_true(lag <= 4.0, "no stamp lags more than 2 cells behind its unit (%.1f m)" % lag)
