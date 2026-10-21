class_name SpatialHash
extends RefCounted
## Uniform bucket grid over the map XZ plane for neighbour queries. Units are kept in buckets
## incrementally (`update` only touches buckets when a unit crosses a bucket border).
## Stores Units by their sim position `pos` and caches the bucket in `hash_bucket`.
##
## Buckets are small (2 m) so crowd/separation queries touch few candidates. Each bucket, and
## each BLOCK x BLOCK group of buckets, also keeps a bitmask of the players that have units in
## it, so `query_hostile` (target acquisition) skips whole areas holding no enemy: a scan costs
## what the nearby enemies cost, not what the surrounding friendly crowd costs.
## A unit's `player_id` must not change while it is inserted (remove, change, insert).

const DEFAULT_BUCKET := 2.0
const BLOCK := 4                 ## buckets per block side for the coarse player masks
const MAX_PLAYERS := 16          ## player ids 0..15 (masks are int bitfields)

var bucket_size: float = DEFAULT_BUCKET
var cols: int = 1
var rows: int = 1
var count: int = 0
## Largest `Unit.target_radius` that can be stored; pads `query_hostile` bucket ranges.
var max_target_radius: float = 1.0
var _bcols: int = 1
var _buckets: Array[Array] = []
var _bucket_mask := PackedInt32Array()   ## bit p: player p has units in the bucket
var _bucket_n := PackedInt32Array()      ## bucket * MAX_PLAYERS + player -> unit count
var _block_mask := PackedInt32Array()
var _block_n := PackedInt32Array()


@warning_ignore("integer_division")
func setup(world_size: Vector2, bucket: float = DEFAULT_BUCKET) -> void:
	bucket_size = bucket
	cols = maxi(1, ceili(world_size.x / bucket))
	rows = maxi(1, ceili(world_size.y / bucket))
	_buckets.clear()
	_buckets.resize(cols * rows)
	for i in _buckets.size():
		_buckets[i] = []
	_bcols = (cols + BLOCK - 1) / BLOCK
	var blocks := _bcols * ((rows + BLOCK - 1) / BLOCK)
	_bucket_mask = PackedInt32Array()
	_bucket_mask.resize(cols * rows)
	_bucket_n = PackedInt32Array()
	_bucket_n.resize(cols * rows * MAX_PLAYERS)
	_block_mask = PackedInt32Array()
	_block_mask.resize(blocks)
	_block_n = PackedInt32Array()
	_block_n.resize(blocks * MAX_PLAYERS)
	count = 0


func bucket_of(p: Vector3) -> int:
	var bx := clampi(floori(p.x / bucket_size), 0, cols - 1)
	var bz := clampi(floori(p.z / bucket_size), 0, rows - 1)
	return bz * cols + bx


func insert(u: Unit) -> void:
	assert(u.player_id >= 0 and u.player_id < MAX_PLAYERS, "player id out of range")
	var b := bucket_of(u.pos)
	u.hash_bucket = b
	_add(u, b)
	count += 1


func remove(u: Unit) -> void:
	var b := u.hash_bucket
	if b < 0:
		return
	_take(u, b)
	u.hash_bucket = -1
	count -= 1


## Call after changing u.pos. Moves an entry between buckets only: a unit that is not in the
## hash (hidden in a mine or a garrison, removed) stays out; insert() alone adds.
func update(u: Unit) -> void:
	var b := bucket_of(u.pos)
	var old := u.hash_bucket
	if b == old or old < 0:
		return
	_take(u, old)
	_add(u, b)
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


## Units of the players in the bitmask `hostile` (bit = player id) that may have their edge
## within `r` of `p`: centre distance <= r + u.target_radius (footprint half-diagonal for
## structures, radius otherwise). Pass r = range + own radius. Blocks and buckets without any
## such player are skipped without looking at their units. Fills and returns `out`.
@warning_ignore("integer_division")
func query_hostile(p: Vector3, r: float, hostile: int, out: Array) -> Array:
	out.clear()
	if hostile == 0:
		return out
	var reach := r + max_target_radius
	var bx0 := clampi(floori((p.x - reach) / bucket_size), 0, cols - 1)
	var bx1 := clampi(floori((p.x + reach) / bucket_size), 0, cols - 1)
	var bz0 := clampi(floori((p.z - reach) / bucket_size), 0, rows - 1)
	var bz1 := clampi(floori((p.z + reach) / bucket_size), 0, rows - 1)
	for kz in range(bz0 / BLOCK, bz1 / BLOCK + 1):
		for kx in range(bx0 / BLOCK, bx1 / BLOCK + 1):
			if _block_mask[kz * _bcols + kx] & hostile == 0:
				continue
			for bz in range(maxi(bz0, kz * BLOCK), mini(bz1, kz * BLOCK + BLOCK - 1) + 1):
				for bx in range(maxi(bx0, kx * BLOCK), mini(bx1, kx * BLOCK + BLOCK - 1) + 1):
					var b := bz * cols + bx
					if _bucket_mask[b] & hostile == 0:
						continue
					for u: Unit in _buckets[b]:
						if (hostile >> u.player_id) & 1 == 0:
							continue
						var up := u.pos
						var dx := up.x - p.x
						var dz := up.z - p.z
						var rr := r + u.target_radius
						if dx * dx + dz * dz <= rr * rr:
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


## Bitmask of the players with units in the bucket containing `p` (tests, debugging).
func players_at(p: Vector3) -> int:
	return _bucket_mask[bucket_of(p)]


@warning_ignore("integer_division")
func _block_of(b: int) -> int:
	return (b / cols) / BLOCK * _bcols + (b % cols) / BLOCK


func _add(u: Unit, b: int) -> void:
	_buckets[b].append(u)
	var bit := 1 << u.player_id
	var k := b * MAX_PLAYERS + u.player_id
	_bucket_n[k] += 1
	_bucket_mask[b] |= bit
	var blk := _block_of(b)
	_block_n[blk * MAX_PLAYERS + u.player_id] += 1
	_block_mask[blk] |= bit


func _take(u: Unit, b: int) -> void:
	_buckets[b].erase(u)
	var k := b * MAX_PLAYERS + u.player_id
	_bucket_n[k] -= 1
	if _bucket_n[k] == 0:
		_bucket_mask[b] &= ~(1 << u.player_id)
	var blk := _block_of(b)
	var kb := blk * MAX_PLAYERS + u.player_id
	_block_n[kb] -= 1
	if _block_n[kb] == 0:
		_block_mask[blk] &= ~(1 << u.player_id)
