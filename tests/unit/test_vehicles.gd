extends "res://tests/test_case.gd"
## Siege vehicles (tools/kits/siege.py models, src/fx/vehicle_rig.gd; visual only): the Bombard
## Wagon and the Sling-Cart resolve to their multi-node models, the rig finds every moving part,
## wheels roll by the distance travelled whatever the frame rate, the barrel's recoil latches on
## the sim's damage point, and the throwing arm follows the swing.

const WAGON := "res://assets/models/vehicles/kingdom_bombard_wagon.glb"
const CART := "res://assets/models/vehicles/clans_sling_cart.glb"


func after_each() -> void:
	super.after_each()
	FxClock.manual = false


func _rig(path: String) -> Array:
	var model := AssetLibrary.instantiate(path, "unit")
	track(model)
	return [model, VehicleRig.find(model)]


func test_siege_models_resolve_and_rig() -> void:
	assert_eq(AssetLibrary.model_path(Defs.unit("kingdom_bombard_wagon"), "kingdom_bombard_wagon"), WAGON,
		"the Bombard Wagon resolves to its vehicle model")
	assert_eq(AssetLibrary.model_path(Defs.unit("clans_sling_cart"), "clans_sling_cart"), CART,
		"the Sling-Cart resolves to its vehicle model")
	for path: String in [WAGON, CART]:
		var r: VehicleRig = _rig(path)[1]
		assert_true(r != null, "%s has a vehicle rig" % path)
		assert_eq(r.wheels.size(), 2, "two wheels")
		assert_eq(r.legs.size(), 4, "two crew, two legs each")
		assert_eq(r.crews.size(), 2, "two crew bodies")
		for w: float in r.wheel_r:
			assert_near(w, 0.5, 0.03, "wheel radius from the node extras")
	var wagon: VehicleRig = _rig(WAGON)[1]
	assert_true(wagon.barrel != null and wagon.arm == null, "the wagon has a barrel")
	assert_near(wagon.recoil_m, 0.2, 0.001, "recoil travel from the node extras")
	var cart: VehicleRig = _rig(CART)[1]
	assert_true(cart.arm != null and cart.barrel == null, "the cart has a throwing arm")
	var mi := AssetLibrary.instantiate(WAGON, "unit")
	track(mi)
	var team := 0
	for m: MeshInstance3D in mi.find_children("*", "MeshInstance3D", true, false):
		for s in m.mesh.get_surface_count():
			var mat := m.get_surface_override_material(s) as ShaderMaterial
			if mat != null and int(mat.get_shader_parameter("team_mode")) == 1:
				team += 1
	assert_true(team > 0, "the kit's TEAM cloth becomes team colour (team_mode 1)")


## The wheels turn by distance / radius: 30 or 144 updates over the same 4 m give the same angle.
func test_wheels_roll_the_same_at_any_frame_rate() -> void:
	var w := make_world()
	var u := w.spawn_unit("kingdom_bombard_wagon", 0, Vector3(20, 0, 20))
	u.facing = 0.0
	var angles: Array[float] = []
	for frames: int in [30, 144, 7]:
		var r: VehicleRig = _rig(WAGON)[1]
		var start := Vector3(20, 0, 20)
		for i in frames + 1:
			var p := start + Vector3(0, 0, -4.0) * (float(i) / frames)   # forward is -Z at facing 0
			u.prev_pos = p
			u.pos = p
			r.update(u, 1.0, 1.0 / frames)
		angles.append(r.wheels[0].rotation.x)
		assert_near(r.distance, 4.0, 1e-4, "%d frames: 4 m forward" % frames)
	assert_near(angles[0], -4.0 / 0.52, 0.02, "the wheel turned distance / radius (rolling forward)")
	assert_near(angles[1], angles[0], 1e-4, "same angle at 144 fps as at 30 fps")
	assert_near(angles[2], angles[0], 1e-4, "same angle at 7 fps")
	var r2: VehicleRig = _rig(WAGON)[1]
	u.prev_pos = Vector3(20, 0, 20)
	u.pos = u.prev_pos
	r2.update(u, 1.0, 0.016)
	u.prev_pos = Vector3(80, 0, 80)
	u.pos = u.prev_pos
	r2.update(u, 1.0, 0.016)
	assert_eq(r2.distance, 0.0, "a teleport does not spin the wheels")


func test_recoil_latches_on_the_damage_point() -> void:
	FxClock.manual = true
	FxClock.reset(50.0)
	var w := make_world()
	var wagon := w.spawn_unit("kingdom_bombard_wagon", 0, Vector3(20, 0, 30))
	var foe := w.spawn_unit("clans_grappler", 1, Vector3(20, 0, 19))
	var r: VehicleRig = _rig(WAGON)[1]
	w.issue({"type": "attack", "player": 0, "units": [wagon.id], "target": foe.id})
	var fired_tick := -1
	for i in 30 * 8:
		w.step()
		FxClock.advance(World.DT)
		r.update(wagon, 0.0, World.DT)
		if r.fired_at >= 0.0:
			fired_tick = i
			break
	assert_true(fired_tick >= 0, "the shot latched the recoil")
	assert_true(wagon.swing_progress() >= wagon.damage_point_ratio(), "on the damage point")
	var rest: Vector3 = r.barrel_rest
	var age := FxClock.fx_now - r.fired_at
	assert_true(age >= 0.0 and age <= World.DT + 1e-4, "the kick is back-dated to the damage point (%f s)" % age)
	assert_near(r.barrel.position.distance_to(rest), 0.2 * VehicleRig.recoil_at(age), 1e-4,
		"the barrel is where the closed-form curve puts it")
	FxClock.advance(0.06)
	r.update(wagon, 0.0, 0.06)
	assert_near(r.barrel.position.distance_to(rest), 0.2, 0.001, "slammed back 0.2 m within 60 ms")
	assert_true(r.barrel.rotation.x > 0.05, "the muzzle kicks up")
	for i in 40:
		w.step()
		FxClock.advance(World.DT)
		r.update(wagon, 0.0, World.DT)
	assert_true(r.barrel.position.distance_to(rest) < 0.001, "back in battery after ~1.4 s (%f)" % r.barrel.position.distance_to(rest))
	assert_eq(VehicleRig.recoil_at(-0.1), 0.0, "nothing before the shot")
	assert_near(VehicleRig.recoil_at(0.02), 0.5, 1e-6, "half way back at 20 ms")
	assert_eq(VehicleRig.recoil_at(0.1), 1.0, "held")
	assert_eq(VehicleRig.recoil_at(2.0), 0.0, "returned")


func test_throwing_arm_follows_the_swing() -> void:
	var dp := 0.6
	assert_eq(VehicleRig.arm_pose(0.0, dp), 0.0, "upright at the start of the swing")
	assert_near(VehicleRig.arm_pose(dp * 0.7, dp), VehicleRig.ARM_COCK_RAD, 1e-6, "cocked back")
	assert_near(VehicleRig.arm_pose(dp - 1e-5, dp), VehicleRig.ARM_RELEASE_RAD, 1e-3, "released on the damage point")
	assert_near(VehicleRig.arm_pose(1.0, dp), 0.0, 1e-6, "settled at the end of the backswing")
	var prev := VehicleRig.arm_pose(dp * 0.7, dp)
	for i in range(1, 11):
		var a := VehicleRig.arm_pose(dp * 0.7 + (dp * 0.3 - 1e-4) * i / 10.0, dp)
		assert_true(a < prev, "the whip only moves forward (%d)" % i)
		prev = a
