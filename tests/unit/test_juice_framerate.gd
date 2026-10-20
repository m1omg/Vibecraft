extends "res://tests/test_case.gd"
## Refresh-rate independence of the juice (juice bible rule 3, §5.2): the same events seen
## through different frame-time sequences (30, 60, 144 Hz and an uneven pacing) give the same
## picture at the same time. Every sequence lands on the sim tick boundaries (as real frames
## see a tick's result on the first frame after it), so the states are compared there.
## Covers the body composer (gait hysteresis, push-off, stop plant, banking, nods, knockback),
## the health-bar damage ghost, camera pan and zoom easing, the camera shake and kick, the order
## pin, selection pop-in and pulse, popups and ground marks.

const SEQUENCES: Dictionary = {
	"30hz": [1.0 / 30.0],
	"60hz": [1.0 / 60.0, 1.0 / 60.0],
	"144hz": [1.0 / 144.0, 1.0 / 144.0, 1.0 / 144.0, 1.0 / 144.0, 1.0 / 30.0 - 4.0 / 144.0],
	"uneven": [0.004, 0.021, 1.0 / 30.0 - 0.025],
}
const TEST_DEF := {"name": "T Juice Foot", "kind": "unit", "hp": 400, "radius": 0.45,
	"speed": 4.0, "height": 1.75, "armor_type": "heavy", "faction": "kingdom",
	"attack": {"type": "blade", "damage": [11, 14], "cooldown": 1.35, "range": 0.8,
		"damage_point": 0.45, "backswing": 0.45, "acquire": 8.0}}

var _was_manual := false


func before_each() -> void:
	if not Defs.units.has("test_juice_foot"):
		Defs.units["test_juice_foot"] = TEST_DEF.duplicate(true)
		Defs._prepare_units()
	FxDefs.clear_cache()
	_was_manual = FxClock.manual
	FxClock.manual = true


func after_each() -> void:
	cleanup()
	Defs.units.erase("test_juice_foot")
	Defs._prepare_units()
	FxDefs.clear_cache()
	FxClock.manual = _was_manual


func _visual_world() -> World:
	var w: World = (load("res://src/world/world.tscn") as PackedScene).instantiate()
	w.auto_tick = false
	w.visuals = true
	tree.root.add_child(w)
	track(w)
	w.setup(flat_map(), 1)
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


## Runs `ticks` sim ticks, each split into the frame times of `seq`; `on_tick(k)` sets the sim
## state at tick k (before its frames), `on_frame()` composes, `sample(k)` reads after tick k's
## frames. Returns the samples.
func _drive(seq: Array, ticks: int, on_tick: Callable, on_frame: Callable, sample: Callable) -> Array:
	FxClock.reset(10.0)
	var out: Array = []
	for k in ticks:
		FxClock.tick_age = 0.0
		on_tick.call(k)
		var within := 0.0
		for dt: float in seq:
			FxClock.advance(dt, true)
			within += dt
			FxClock.tick_age = within      # what Vfx writes from the interpolation fraction
			on_frame.call(dt)
		out.append(sample.call(k))
	FxClock.tick_age = 0.0
	return out


func _assert_same(runs: Dictionary, eps: float, what: String) -> void:
	var ref: Array = runs["30hz"]
	for name: String in runs:
		var r: Array = runs[name]
		for k in ref.size():
			var a: Variant = ref[k]
			var b: Variant = r[k]
			var d := 0.0
			if a is Transform3D:
				var ta: Transform3D = a
				var tb: Transform3D = b
				d = maxf((ta.origin - tb.origin).length(), (ta.basis.x - tb.basis.x).length())
				d = maxf(d, maxf((ta.basis.y - tb.basis.y).length(), (ta.basis.z - tb.basis.z).length()))
			elif a is Vector2:
				d = ((a as Vector2) - (b as Vector2)).length()
			elif a is Vector3:
				d = ((a as Vector3) - (b as Vector3)).length()
			else:
				d = absf(float(a) - float(b))
			if d > eps:
				fail("%s differs at tick %d between 30hz and %s: %s vs %s" % [what, k, name, str(a), str(b)])
				return


# --- the body composer --------------------------------------------------------------------------

func test_body_juice_is_refresh_rate_independent() -> void:
	var runs: Dictionary = {}
	var facts: Dictionary = {}
	for name: String in SEQUENCES:
		var w := _visual_world()
		var u := w.spawn_unit("test_juice_foot", 0, Vector3(20, 0, 20))
		var v := u.view as UnitView
		var j: BodyJuice = v.juice
		assert_true(j != null, "mobile units get a body composer")
		var script := func(k: int) -> void:
			w.tick_count = k + 1
			# walk from tick 5 (with a turn from tick 20), stop at tick 40; hit at 50; nod at 55
			if k == 5:
				u.velocity = Vector3(0, 0, -4.0)
			if k >= 20 and k < 30:
				u.facing += 0.08
			if k == 40:
				u.velocity = Vector3.ZERO
			if k == 50:
				j.knock(u.pos + Vector3(1.0, 0, 0), 30.0, u.max_hp, 0.11)
			if k == 55:
				j.nod(FxClock.ui_now)
		var compose := func(dt: float) -> void:
			j.compose(dt)
		var sample := func(_k: int) -> Transform3D:
			return v.rig.transform
		runs[name] = _drive(SEQUENCES[name], 75, script, compose, sample)
		facts[name] = j.gait
		w.free()
	_assert_same(runs, 2e-3, "rig transform")
	var walking: Transform3D = (runs["30hz"] as Array)[30]
	assert_true(walking.basis.z.y < -0.02 or walking.basis.z.y > 0.02 or absf(walking.basis.y.z) > 0.02,
		"the walking body leans (%s)" % str(walking.basis))
	var knocked: Transform3D = (runs["30hz"] as Array)[51]
	assert_true(knocked.origin.length() > 0.01, "the hit knocks the body back (%s)" % str(knocked.origin))
	var settled: Transform3D = (runs["30hz"] as Array)[74]
	assert_lt(settled.origin.length(), 0.01, "the knockback settles")


# --- health-bar ghost -----------------------------------------------------------------------------

func test_health_ghost_is_refresh_rate_independent() -> void:
	var runs: Dictionary = {}
	for name: String in SEQUENCES:
		var bars := HealthBars.new()
		track(bars)
		var hp := [1.0]
		var script := func(k: int) -> void:
			if k == 3:
				hp[0] = 0.7
			if k == 9:
				hp[0] = 0.55
			if k == 40:
				hp[0] = 0.6
		var frame := func(_dt: float) -> void:
			bars.ghost_for(1, hp[0], FxClock.fx_now)
		var sample := func(_k: int) -> float:
			return bars.ghost_for(1, hp[0], FxClock.fx_now)
		runs[name] = _drive(SEQUENCES[name], 60, script, frame, sample)
	_assert_same(runs, 1e-5, "ghost ratio")
	var r: Array = runs["30hz"]
	assert_near(float(r[10]), 1.0, 1e-5, "the ghost holds the lost segment")
	assert_near(float(r[9 + 10]), 1.0, 1e-5, "it holds 400 ms after the latest hit")
	assert_lt(float(r[30]), 0.9, "then drains")
	assert_near(float(r[59]), 0.6, 1e-4, "and meets the bar")


func test_ghost_drain_is_closed_form() -> void:
	# the gap after t seconds equals the gap after t/2 then t/2 more: no frame-step error
	var d0 := 0.4
	var a := HealthBars.ghost_gap(d0, 0.3)
	var half := HealthBars.ghost_gap(d0, 0.15)
	assert_near(HealthBars.ghost_gap(half, 0.15), a, 1e-5, "drain composes exactly")
	assert_true(HealthBars.ghost_gap(0.02, 1.0) == 0.0, "never slower than 0.25 bar/s")


# --- camera ---------------------------------------------------------------------------------------

func test_camera_pan_and_zoom_are_refresh_rate_independent() -> void:
	var runs: Dictionary = {}
	for name: String in SEQUENCES:
		var st := {"pos": Vector2.ZERO, "v": Vector2.ZERO, "target": Vector2.ZERO, "d": 25.8, "td": 25.8}
		var fc := FeelConstants.c()
		var script := func(k: int) -> void:
			if k == 2:
				st["target"] = Vector2(28.0, 0.0)
				st["td"] = 18.75
			if k == 20:
				st["target"] = Vector2.ZERO
		var frame := func(dt: float) -> void:
			var tv: Vector2 = st["target"]
			var kk := fc.pan_accel_k if tv != Vector2.ZERO else fc.pan_stop_k
			st["pos"] = (st["pos"] as Vector2) + RtsCamera.pan_step(st["v"], tv, kk, dt)
			st["v"] = RtsCamera.pan_velocity_after(st["v"], tv, kk, dt)
			st["d"] = Juice.damp(st["d"], st["td"], fc.zoom_k, dt)
		var sample := func(_k: int) -> Vector3:
			var p: Vector2 = st["pos"]
			return Vector3(p.x, p.y, st["d"])
		runs[name] = _drive(SEQUENCES[name], 40, script, frame, sample)
	_assert_same(runs, 1e-4, "camera focus / distance")
	var r: Array = runs["30hz"]
	# a firm stop: within 150 ms of release the camera moves less than 2 % of the cruise speed
	var p20: Vector3 = r[24]
	var p21: Vector3 = r[25]
	assert_lt((p21 - p20).length() / World.DT, 28.0 * 0.06, "the pan stops within 150 ms")


func test_camera_shake_and_kick_are_refresh_rate_independent() -> void:
	var runs: Dictionary = {}
	for name: String in SEQUENCES:
		var cj := CameraJuice.new(null)
		var script := func(k: int) -> void:
			if k == 3:
				cj.add_trauma(&"combat", 0.35, Vector3.ZERO)
		var frame := func(_dt: float) -> void:
			cj.evaluate(FxClock.ui_now, 25.8)
		var sample := func(_k: int) -> Vector3:
			cj.evaluate(FxClock.ui_now, 25.8)
			return Vector3(cj.shake_offset.x, cj.shake_offset.y, cj.shake_roll)
		runs[name] = _drive(SEQUENCES[name], 30, script, frame, sample)
	_assert_same(runs, 1e-6, "camera shake")
	assert_true(((runs["30hz"] as Array)[5] as Vector3).length() > 0.0, "the whitelisted shake moves the view")
	assert_near(((runs["30hz"] as Array)[29] as Vector3).length(), 0.0, 1e-6, "τ decays to rest")


# --- marks, rings, popups -------------------------------------------------------------------------

func test_ui_curves_are_closed_form_in_time() -> void:
	# pin, ring pop-in, pulse, popup look and ground marks depend on age only: sampling the same
	# ages after different frame splits gives identical values, and the bible beats hold
	var drop := FeelConstants.c().pin_drop_ms / 1000.0
	assert_near(OrderMarkers.pin_look(0.0).x, 0.9, 1e-4, "the pin starts 0.9 m up")
	assert_near(OrderMarkers.pin_look(drop).x, 0.15, 1e-4, "and lands at +0.15 m on 160 ms")
	assert_true(OrderMarkers.pin_look(0.7).y <= 0.0, "gone after hold + shrink")
	var lk := SelectionCircles.pop_look(0.07)
	assert_near(lk.x, FeelConstants.c().sel_pop_peak, 1e-4, "ring pops to 1.06 at 70 ms")
	assert_near(SelectionCircles.pop_look(0.16).x, 1.0, 1e-4, "and settles to 1.0 by 160 ms")
	assert_near(SelectionCircles.pop_look(0.0).y, 0.0, 1e-4, "alpha starts at 0")
	assert_near(SelectionCircles.pulse_look(0.06).x, FeelConstants.c().pulse_scale, 1e-4, "pulse peaks ×1.22 at 60 ms")
	var crit := PopupText.look(PopupText.Style.CRIT, 0.09, 1.0, -1.0)
	assert_near(crit.x, 1.45, 1e-3, "crit pops to 1.45 at 90 ms")
	assert_true(PopupText.look(PopupText.Style.GOLD, 0.999, 1.0, -1.0).y < 0.05, "popups fade by 1 s")
	assert_near(GroundMarks.target_blink_alpha(0.1), 0.0, 1e-6, "target blink: off at 100 ms")
	assert_near(GroundMarks.target_blink_alpha(0.2), 1.0, 1e-6, "on again at 200 ms")


func test_ground_marks_follow_the_clock_not_the_frames() -> void:
	var runs: Dictionary = {}
	for name: String in SEQUENCES:
		var w := _visual_world()
		var marks: GroundMarks = (w.get_node("Fx/Vfx") as Vfx).marks
		var script := func(k: int) -> void:
			if k == 1:
				marks.add(GroundMarks.Kind.RIPPLE, Vector3(10, 0, 10), 0.25, 1.9, Color.GREEN, 0.42, 0.07)
		var frame := func(_dt: float) -> void:
			marks._process(0.0)
		var sample := func(_k: int) -> Vector2:
			if marks.live == 0:
				return Vector2(-1, -1)
			var st := marks.eval_mark(0, FxClock.ui_now)
			return Vector2(st[1], st[3])
		runs[name] = _drive(SEQUENCES[name], 20, script, frame, sample)
		w.free()
	_assert_same(runs, 1e-5, "ripple radius / alpha")


func test_smear_reaches_the_tip_on_contact() -> void:
	# CMB-20: hidden before 85 % of the wind-up, the head on the end of the arc at the damage
	# point, then a fade of 80 + 20·mass ms that never outlives 140 ms
	var dp := 0.5
	assert_true(Smears.look(0.40, dp, -1.0, 120.0, -15.0, 0.1).z <= 0.0, "no smear early in the wind-up")
	var mid := Smears.look(0.45, dp, -1.0, 120.0, -15.0, 0.1)
	assert_true(mid.z > 0.0 and mid.x < 120.0 and mid.x > -15.0, "revealing during the snap")
	assert_near(Smears.look(0.4999, dp, -1.0, 120.0, -15.0, 0.1).x, -15.0, 0.5, "the head reaches the tip at contact")
	var after := Smears.look(0.6, dp, 0.05, 120.0, -15.0, 0.1)
	assert_near(after.x, -15.0, 1e-4, "after contact the head stays on the tip")
	assert_true(after.y < 120.0 and after.z < 0.85, "the tail catches up and fades")
	assert_true(Smears.look(0.7, dp, 0.1, 120.0, -15.0, 0.1).z <= 0.0, "gone after the fade")
