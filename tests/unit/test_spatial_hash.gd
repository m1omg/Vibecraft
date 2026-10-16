extends "res://tests/test_case.gd"

var _units: Array[Unit] = []


func after_each() -> void:
	for u in _units:
		u.free()
	_units.clear()
	cleanup()


func _make(n: int, rng: RandomNumberGenerator) -> SpatialHash:
	var h := SpatialHash.new()
	h.setup(Vector2(192, 192))
	for i in n:
		var u := Unit.new()
		u.id = i + 1
		u.pos = Vector3(rng.randf_range(0, 192), 0, rng.randf_range(0, 192))
		_units.append(u)
		h.insert(u)
	return h


func _brute(p: Vector3, r: float) -> Array:
	var out: Array = []
	for u in _units:
		if u.hash_bucket >= 0 and Vector2(u.pos.x - p.x, u.pos.z - p.z).length() <= r:
			out.append(u)
	return out


func _same(a: Array, b: Array) -> bool:
	if a.size() != b.size():
		return false
	for x in a:
		if not b.has(x):
			return false
	return true


func _check_queries(h: SpatialHash, rng: RandomNumberGenerator, label: String) -> void:
	var buf: Array = []
	for i in 60:
		var p := Vector3(rng.randf_range(-5, 197), 0, rng.randf_range(-5, 197))
		var r := rng.randf_range(0.5, 20.0)
		h.query_radius(p, r, buf)
		if not _same(buf, _brute(p, r)):
			fail("%s: query %s r=%f mismatch (%d vs %d)" % [label, p, r, buf.size(), _brute(p, r).size()])
			return


func test_query_matches_brute_force() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var h := _make(300, rng)
	assert_eq(h.count, 300)
	_check_queries(h, rng, "initial")


func test_update_after_moves() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var h := _make(200, rng)
	for u in _units:
		u.pos += Vector3(rng.randf_range(-12, 12), 0, rng.randf_range(-12, 12))
		u.pos = u.pos.clamp(Vector3.ZERO, Vector3(191.9, 0, 191.9))
		h.update(u)
	_check_queries(h, rng, "after move")


func test_remove() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var h := _make(100, rng)
	for i in range(0, 100, 2):
		h.remove(_units[i])
	assert_eq(h.count, 50)
	_check_queries(h, rng, "after remove")


func test_query_rect() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	var h := _make(150, rng)
	var rect := Rect2(40, 50, 30, 20)
	var got := h.query_rect(rect)
	var expected := 0
	for u in _units:
		if rect.has_point(Vector2(u.pos.x, u.pos.z)):
			expected += 1
	assert_eq(got.size(), expected, "rect query count")


func _brute_hostile(p: Vector3, r: float, hostile: int) -> Array:
	var out: Array = []
	for u in _units:
		if u.hash_bucket < 0 or (hostile >> u.player_id) & 1 == 0:
			continue
		if Vector2(u.pos.x - p.x, u.pos.z - p.z).length() <= r + u.target_radius:
			out.append(u)
	return out


## Acquisition query: only hostile players' units, padded per candidate by its target radius;
## player masks stay right through moves and removals.
func test_query_hostile_matches_brute_force() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 21
	var h := SpatialHash.new()
	h.setup(Vector2(192, 192))
	h.max_target_radius = 3.6
	for i in 400:
		var u := Unit.new()
		u.id = i + 1
		u.player_id = rng.randi_range(0, 13)
		u.target_radius = 3.5 if i % 25 == 0 else 0.45
		u.pos = Vector3(rng.randf_range(0, 192), 0, rng.randf_range(0, 192))
		_units.append(u)
		h.insert(u)
	var buf: Array = []
	for round_i in 3:
		for i in 60:
			var p := Vector3(rng.randf_range(-5, 197), 0, rng.randf_range(-5, 197))
			var r := rng.randf_range(0.5, 14.0)
			var hostile := rng.randi() & 0x3FFF
			h.query_hostile(p, r, hostile, buf)
			var want := _brute_hostile(p, r, hostile)
			if not _same(buf, want):
				fail("round %d: hostile query %s r=%f mask %x mismatch (%d vs %d)" % [round_i, p, r,
					hostile, buf.size(), want.size()])
				return
		for k in range(round_i, _units.size(), 3):
			var u := _units[k]
			if u.hash_bucket < 0:
				continue
			if k % 2 == 0:
				h.remove(u)
			else:
				u.pos = (u.pos + Vector3(rng.randf_range(-9, 9), 0, rng.randf_range(-9, 9))).clamp(
					Vector3.ZERO, Vector3(191.9, 0, 191.9))
				h.update(u)
	# masks: a bucket reports exactly the players present
	var bad := 0
	for u in _units:
		if u.hash_bucket >= 0 and (h.players_at(u.pos) >> u.player_id) & 1 == 0:
			bad += 1
	assert_eq(bad, 0, "every stored unit's player is in its bucket mask")
	assert_eq(h.query_hostile(Vector3(96, 0, 96), 200.0, 0, buf).size(), 0, "empty mask finds nothing")
	for u in _units:
		if u.hash_bucket >= 0:
			h.remove(u)
	var left := 0
	for m in h._bucket_mask:
		left |= m
	for m in h._block_mask:
		left |= m
	assert_eq(left, 0, "masks clear once every unit is removed")
