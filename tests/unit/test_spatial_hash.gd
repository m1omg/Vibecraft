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
