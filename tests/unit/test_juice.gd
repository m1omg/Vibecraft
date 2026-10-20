extends "res://tests/test_case.gd"
## Juice maths core (src/fx/juice.gd, juice_curves.gd, feel_constants.gd, fx_defs.gd): exact
## springs, the shared anticipation curve, stateless hashes, the frequency cap, legal feel ranges.


## Fine Euler-free reference: RK4 at 1 kHz.
func _rk4_spring(x: float, v: float, omega: float, zeta: float, t: float) -> Vector2:
	var h := 0.001
	var n := roundi(t / h)
	for i in n:
		var f := func(px: float, pv: float) -> Vector2:
			return Vector2(pv, -omega * omega * px - 2.0 * zeta * omega * pv)
		var k1: Vector2 = f.call(x, v)
		var k2: Vector2 = f.call(x + k1.x * h * 0.5, v + k1.y * h * 0.5)
		var k3: Vector2 = f.call(x + k2.x * h * 0.5, v + k2.y * h * 0.5)
		var k4: Vector2 = f.call(x + k3.x * h, v + k3.y * h)
		x += (k1.x + 2.0 * k2.x + 2.0 * k3.x + k4.x) * h / 6.0
		v += (k1.y + 2.0 * k2.y + 2.0 * k3.y + k4.y) * h / 6.0
	return Vector2(x, v)


func test_spring_is_exact_in_every_branch() -> void:
	for zeta: float in [0.2, 0.52, 1.0, 1.6]:
		var ref := _rk4_spring(0.3, 2.0, 18.0, zeta, 0.25)
		var one := Juice.spring(0.3, 2.0, 18.0, zeta, 0.25)
		assert_near(one.x, ref.x, 1e-4, "zeta %.2f position" % zeta)
		assert_near(one.y, ref.y, 1e-3, "zeta %.2f velocity" % zeta)


func test_spring_is_refresh_rate_independent() -> void:
	# stepping at 30, 60, 144 and 240 Hz (and a jittered sequence) lands on the same state
	var expected := Juice.spring(0.0, 4.0, 21.9, 0.52, 0.5)
	for seq: Array in [[1.0 / 30.0], [1.0 / 60.0], [1.0 / 144.0], [1.0 / 240.0], [0.011, 0.023, 0.0167, 0.031]]:
		var s := Vector2(0.0, 4.0)
		var t := 0.0
		var i := 0
		while t < 0.5 - 1e-9:
			var dt := minf(float(seq[i % seq.size()]), 0.5 - t)
			s = Juice.spring(s.x, s.y, 21.9, 0.52, dt)
			t += dt
			i += 1
		assert_near(s.x, expected.x, 1e-5, "same position at 0.5 s for %s" % str(seq))


func test_kick_for_peak_hits_its_amplitude() -> void:
	for row: Array in [[26.8, 0.48], [21.9, 0.52], [17.9, 0.56]]:
		var w: float = row[0]
		var z: float = row[1]
		var v0 := Juice.kick_for_peak(0.11, w, z)
		var tp := Juice.peak_time(w, z)
		assert_near(Juice.spring(0.0, v0, w, z, tp).x, 0.11, 1e-4, "peak = A for ω %.1f" % w)
	# the Pavisier spring peaks at ~55 ms (combat §4.8)
	assert_near(Juice.peak_time(21.9, 0.52) * 1000.0, 55.0, 3.0, "Pavisier knockback peak time")


func test_spring_track_follows_a_ramp_exactly() -> void:
	var s := Vector2(0.0, 0.0)
	var t := 0.0
	var dt := 1.0 / 30.0
	for i in 60:
		s = Juice.spring_track(s.x, s.y, t, t + dt, 12.0, 0.7, dt)
		t += dt
	var fine := Vector2(0.0, 0.0)
	var tf := 0.0
	var df := 1.0 / 600.0
	for i in 1200:
		fine = Juice.spring_track(fine.x, fine.y, tf, tf + df, 12.0, 0.7, df)
		tf += df
	assert_near(s.x, fine.x, 1e-4, "first-order hold is exact for ramps at any step")


func test_anticipation_curve_lands_on_contact() -> void:
	for dp: float in [0.3, 0.5, 0.72]:
		assert_eq(Juice.anticipate(dp, dp, 0.05, 0.72, 0.0, -0.45, 1.6), 1.0, "P(contact) == 1")
		assert_lt(Juice.anticipate(dp - 0.001, dp, 0.05, 0.72, 0.0, -0.45, 1.6), 1.0, "P < 1 before contact")
		assert_eq(Juice.anticipate(dp + 0.04, dp, 0.05, 0.72, 0.0, -0.45, 1.6), 1.0, "hit-stop holds the pose")
	assert_near(Juice.anticipate(0.36, 0.5, 0.0, 0.72, 0.0, -0.45, 1.6), -0.45, 1e-3, "loaded pose at the split")
	assert_eq(Juice.anticipate(0.4, 0.5, 0.0, 0.5, 0.3, -0.3, 1.3), -0.3, "the hang holds the load")
	assert_near(Juice.anticipate(1.0, 0.5, 0.05, 0.6, 0.0, -0.3, 1.3), 0.0, 1e-6, "recovered at the end")


func test_strike_phase_maps_contact_to_the_strike_frame() -> void:
	for dp: float in [0.25, 0.5, 0.7]:
		assert_eq(Juice.strike_phase(dp, dp, 0.06, 0.6), dp, "contact on the clip's hit frame")
		assert_lt(Juice.strike_phase(dp * 0.99, dp, 0.06, 0.6), dp, "before it")
		assert_eq(Juice.strike_phase(dp + 0.05, dp, 0.06, 0.6), dp, "held for the hit-stop")
		assert_near(Juice.strike_phase(1.0, dp, 0.06, 0.6), 1.0, 1e-6, "clip ends with the backswing")
	var prev := -1.0
	for i in 101:
		var p := Juice.strike_phase(i / 100.0, 0.5, 0.06, 0.6)
		assert_true(p >= prev - 1e-6, "monotonic")
		prev = p


func test_easings_and_back_overshoot() -> void:
	var fns: Array[Callable] = [Juice.out_quad, Juice.in_quad, Juice.out_cubic, Juice.in_cubic,
		Juice.in_out_sine, Juice.in_out_cubic, Juice.out_quart, Juice.out_quint, Juice.out_bounce]
	for f in fns:
		assert_near(f.call(0.0), 0.0, 1e-6, "%s(0)" % f.get_method())
		assert_near(f.call(1.0), 1.0, 1e-6, "%s(1)" % f.get_method())
	var peak := 0.0
	for i in 1001:
		peak = maxf(peak, Juice.out_back(i / 1000.0, 1.1))
	assert_near(peak, 1.045, 0.006, "TIMBER_SNAP overshoot ≈ 4.5 %")
	assert_near(Juice.ring(5.0, 14.0, 0.35), 1.0, 1e-4, "FELT_BOB settles to 1")
	assert_eq(Juice.ring(0.0, 28.0, 0.12), 0.0, "BRONZE_RING starts from rest")


func test_hash_and_noise_are_stateless() -> void:
	assert_eq(Juice.hash01(42, 3, 7), Juice.hash01(42, 3, 7), "same input, same value")
	var lo := 1.0
	var hi := 0.0
	var sum := 0.0
	for i in 2000:
		var h := Juice.hash01(i, 1, 2)
		lo = minf(lo, h)
		hi = maxf(hi, h)
		sum += h
	assert_true(lo >= 0.0 and hi < 1.0, "hash in [0, 1)")
	assert_near(sum / 2000.0, 0.5, 0.03, "roughly uniform")
	for i in 200:
		var n := Juice.vnoise(7, i * 0.013, 12.0)
		assert_true(n >= -1.0 and n <= 1.0, "noise in [-1, 1]")


func test_accumulate_counts_the_same_at_any_rate() -> void:
	for dt: float in [1.0 / 30.0, 1.0 / 60.0, 1.0 / 144.0, 0.0123]:
		var acc := 0.0
		var count := 0
		var t := 0.0
		while t < 2.0 - 1e-9:
			var step := minf(dt, 2.0 - t)
			var r := Juice.accumulate(acc, step, 0.05)
			acc = r.x
			count += int(r.y)
			t += step
		assert_true(count == 40 or count == 39, "40 spawns in 2 s at %.4f s steps (got %d)" % [dt, count])


func test_latched_peaks_start_at_the_peak() -> void:
	assert_eq(Juice.latched(0.0, 1.0, 0.07), 1.0, "first frame is the peak")
	assert_eq(JuiceCurves.flare(0.0), 1.0, "flare latched")
	assert_eq(Juice.latched(0.08, 1.0, 0.07), 0.0, "gone after its window")


func test_curve_tokens_respect_the_frequency_cap() -> void:
	var cap := FeelConstants.c().freq_cap_hz
	for k: String in JuiceCurves.FREQ_HZ:
		assert_true(float(JuiceCurves.FREQ_HZ[k]) <= cap, "%s at %.1f Hz <= %.0f Hz" % [k, JuiceCurves.FREQ_HZ[k], cap])
	assert_near(JuiceCurves.pop_in(0.0), 0.8, 1e-6, "pop starts at 0.80")
	assert_near(JuiceCurves.pop_in(0.07), 1.06, 1e-6, "pop peaks at 1.06 at 70 ms")
	assert_near(JuiceCurves.pop_in(0.16), 1.0, 1e-6, "settled at 160 ms")


func test_feel_constants_are_in_their_legal_ranges() -> void:
	var fc := FeelConstants.c()
	assert_true(fc != null, "feel constants loaded")
	assert_eq(fc.validate(), PackedStringArray(), "default feel constants are legal")
	assert_true(ResourceLoader.exists(FeelConstants.DEFAULT_PATH), "data/feel/feel_default.tres exists")
	var bad := FeelConstants.new()
	bad.trauma_cap_total = 0.9
	assert_true(bad.validate().size() > 0, "an illegal value is reported")


func test_fx_sheets_merge_data_and_defs() -> void:
	FxDefs.clear_cache()
	var pav := FxDefs.sheet_for("kingdom_pavisier", Defs.unit("kingdom_pavisier"))
	assert_eq(float(pav["mass"]), 1.2, "Pavisier mass")
	assert_eq(str(pav["material"]), "metal", "Pavisier body material")
	assert_eq(str(pav["weapon"]), "slash", "falchion")
	assert_eq(float(pav["hit_stop_ms"]), 45.0, "slash hit-stop from the weapon table")
	assert_eq(str(pav["grammar"]), "kingdom", "kingdom grammar")
	var grap := FxDefs.sheet_for("clans_grappler", Defs.unit("clans_grappler"))
	assert_eq(str(grap["weapon"]), "blunt", "mace")
	assert_eq(float(grap["pull"]), -0.45, "blunt pull")
	assert_near(float(grap["c1"]), 1.5, 1e-6, "Tormai recover c1 −0.1")
	# frontal arc: hits from the front strike the pavise (wood), from behind the body (metal)
	var front := FxDefs.hit_material(pav, 0.0, Vector3.ZERO, Vector3(0, 0, -2))
	var back := FxDefs.hit_material(pav, 0.0, Vector3.ZERO, Vector3(0, 0, 2))
	assert_eq(front, "wood", "frontal hit on the pavise")
	assert_eq(back, "metal", "hit from behind")
	var unknown := FxDefs.sheet_for("no_such_unit", {"armor_type": "heavy", "weapon": "club", "radius": 0.45})
	assert_eq(str(unknown["material"]), "metal", "armor type derives the material")
	assert_eq(str(unknown["weapon"]), "blunt", "weapon hint derives the class")
	assert_true(FxDefs.material_bursts("wood").size() > 0, "every material has bursts")


func test_fx_clock_freezes_fx_time_on_pause() -> void:
	var was_manual := FxClock.manual
	FxClock.manual = true
	FxClock.reset(5.0)
	FxClock.advance(0.1, true)
	FxClock.advance(0.1, false)
	assert_near(FxClock.fx_now, 5.1, 1e-6, "fx time stops while paused")
	assert_near(FxClock.ui_now, 5.2, 1e-6, "ui time keeps running")
	FxClock.advance(0.1, true, 0.5)
	assert_near(FxClock.ui_now, 5.4, 1e-6, "ui time is unscaled by game speed")
	assert_near(FxClock.fx_now, 5.2, 1e-6, "fx time follows game speed")
	FxClock.manual = was_manual
