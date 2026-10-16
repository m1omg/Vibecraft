extends RefCounted
## Shared scripted battle: 8 soldiers + 4 archers (player 0) attack-move into 10 creeps (neutral
## hostile). Used headless by tests/unit/test_orders.gd and with screenshots by
## tests/playtest/battle.gd. Loaded at runtime, so it only uses autoloads through the World.

const SOLDIERS := 8
const ARCHERS := 4
const CREEPS := 10
const TIME_LIMIT_S := 90.0
const FACE_EAST := -PI * 0.5      ## yaw whose forward (-sin, 0, -cos) points to +X
const FACE_WEST := PI * 0.5


## Army west of `centre`, creeps east of it (two loose ranks), facing each other.
static func spawn(w: World, centre: Vector3) -> Dictionary:
	var army: Array = []
	for i in SOLDIERS:
		army.append(w.spawn_unit("dummy_soldier", 0, centre + Vector3(-9.0, 0.0, (i - 3.5) * 1.15), FACE_EAST))
	for i in ARCHERS:
		army.append(w.spawn_unit("dummy_archer", 0, centre + Vector3(-11.5, 0.0, (i - 1.5) * 1.4), FACE_EAST))
	var creeps: Array = []
	for i in CREEPS:
		@warning_ignore("integer_division")
		var rank := i / 5
		var p := centre + Vector3(3.0 + rank * 1.7, 0.0, (i % 5 - 2) * 1.5 + rank * 0.6)
		creeps.append(w.spawn_unit("dummy_creep", PlayerState.NEUTRAL_HOSTILE, p, FACE_WEST))
	return {"army": army, "creeps": creeps}


static func charge(w: World, army: Array, centre: Vector3) -> void:
	var ids: Array = []
	for u: Unit in army:
		ids.append(u.id)
	w.issue({"type": "attack_move", "player": 0, "units": ids, "pos": centre + Vector3(8.0, 0.0, 0.0)})


static func alive_count(units: Array) -> int:
	var n := 0
	for u: Variant in units:
		if is_instance_valid(u) and (u as Unit).alive:
			n += 1
	return n


## "army", "creeps" or "" while both sides still stand.
static func winner(sides: Dictionary) -> String:
	var a := alive_count(sides["army"])
	var c := alive_count(sides["creeps"])
	if a > 0 and c == 0:
		return "army"
	if c > 0 and a == 0:
		return "creeps"
	return ""


## Centre of a flat, fully walkable 28 x 16 m box (trees, cliffs and water excluded), searched
## outward from `near`. Returns Vector3.INF when nothing fits.
static func find_open_area(w: World, near: Vector3) -> Vector3:
	var size := w.map.size_world()
	for ring in range(0, 40):
		for k in range(0, maxi(ring * 8, 1)):
			var a := TAU * k / maxf(ring * 8.0, 1.0)
			var c := near + Vector3(cos(a), 0.0, sin(a)) * ring * 4.0
			if c.x < 16.0 or c.z < 10.0 or c.x > size.x - 16.0 or c.z > size.y - 10.0:
				continue
			if _box_open(w, c):
				c.y = w.map.height_at(c.x, c.z)
				return c
	return Vector3.INF


static func _box_open(w: World, c: Vector3) -> bool:
	var h0 := w.map.height_at(c.x, c.z)
	for dz in range(-8, 9):
		for dx in range(-14, 15):
			var p := Vector3(c.x + dx, 0.0, c.z + dz)
			if not w.pathing.is_walkable_world(p) or absf(w.map.height_at(p.x, p.z) - h0) > 0.05:
				return false
	return true
