class_name SpatialHash
extends RefCounted
## Uniform bucket grid over the map XZ plane for neighbour queries. Units are kept in buckets
## incrementally (`update` only touches buckets when a unit crosses a bucket border).
## Stores Units by their sim position `pos` and caches the bucket in `hash_bucket`.

const DEFAULT_BUCKET := 4.0

var bucket_size: float = DEFAULT_BUCKET
var cols: int = 1
var rows: int = 1
var count: int = 0
var _buckets: Array[Array] = []


func setup(world_size: Vector2, bucket: float = DEFAULT_BUCKET) -> void:
	bucket_size = bucket
	cols = maxi(1, ceili(world_size.x / bucket))
	rows = maxi(1, ceili(world_size.y / bucket))
	_buckets.clear()
	_buckets.resize(cols * rows)
	for i in _buckets.size():
		_buckets[i] = []
	count = 0


func bucket_of(p: Vector3) -> int:
	var bx := clampi(floori(p.x / bucket_size), 0, cols - 1)
	var bz := clampi(floori(p.z / bucket_size), 0, rows - 1)
	return bz * cols + bx


func insert(u: Unit) -> void:
	var b := bucket_of(u.pos)
	u.hash_bucket = b
	_buckets[b].append(u)
	count += 1


func remove(u: Unit) -> void:
	var b := u.hash_bucket
	if b < 0:
		return
	_buckets[b].erase(u)
	u.hash_bucket = -1
	count -= 1


## Call after changing u.pos.
func update(u: Unit) -> void:
	var b := bucket_of(u.pos)
	var old := u.hash_bucket
	if b == old:
		return
	if old >= 0:
		_buckets[old].erase(u)
	_buckets[b].append(u)
	u.hash_bucket = b


## Appends every object whose centre lies within `r` (XZ distance) of `p` to `out`, which is
## cleared first. Returns `out` so callers can reuse one array and avoid allocations.
func query_radius(p: Vector3, r: float, out: Array = []) -> Array:
	out.clear()
	var r2 := r * r
	var bx0 := clampi(floori((p.x - r) / bucket_size), 0, cols - 1)
	var bx1 := clampi(floori((p.x + r) / bucket_size), 0, cols - 1)
	var bz0 := clampi(floori((p.z - r) / bucket_size), 0, rows - 1)
	var bz1 := clampi(floori((p.z + r) / bucket_size), 0, rows - 1)
	for bz in range(bz0, bz1 + 1):
		for bx in range(bx0, bx1 + 1):
			for u: Unit in _buckets[bz * cols + bx]:
				var up := u.pos
				var dx := up.x - p.x
				var dz := up.z - p.z
				if dx * dx + dz * dz <= r2:
					out.append(u)
	return out


## Objects whose centres lie inside an XZ rectangle (world units).
func query_rect(rect: Rect2, out: Array = []) -> Array:
	out.clear()
	var bx0 := clampi(floori(rect.position.x / bucket_size), 0, cols - 1)
	var bx1 := clampi(floori(rect.end.x / bucket_size), 0, cols - 1)
	var bz0 := clampi(floori(rect.position.y / bucket_size), 0, rows - 1)
	var bz1 := clampi(floori(rect.end.y / bucket_size), 0, rows - 1)
	for bz in range(bz0, bz1 + 1):
		for bx in range(bx0, bx1 + 1):
			for u: Unit in _buckets[bz * cols + bx]:
				var up := u.pos
				if rect.has_point(Vector2(up.x, up.z)):
					out.append(u)
	return out
