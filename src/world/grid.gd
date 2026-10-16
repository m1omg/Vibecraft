class_name Grid
## World / tile / pathing-cell coordinate helpers. Map origin is the (0,0) corner, Y up,
## map on the XZ plane. Cell = 0.5 m pathing cell, tile = 2 m terrain tile.

const TILE := 2.0
const CELL := 0.5
const CELLS_PER_TILE := 4
const CLIFF_H := 1.75
const MAX_CLIFF_LEVEL := 3


static func world_to_cell(p: Vector3) -> Vector2i:
	return Vector2i(floori(p.x / CELL), floori(p.z / CELL))


## Cell centre at y = 0.
static func cell_to_world(c: Vector2i) -> Vector3:
	return Vector3((c.x + 0.5) * CELL, 0.0, (c.y + 0.5) * CELL)


static func world_to_tile(p: Vector3) -> Vector2i:
	return Vector2i(floori(p.x / TILE), floori(p.z / TILE))


## Tile centre at y = 0.
static func tile_to_world(t: Vector2i) -> Vector3:
	return Vector3((t.x + 0.5) * TILE, 0.0, (t.y + 0.5) * TILE)


static func tile_corner_to_world(t: Vector2i) -> Vector3:
	return Vector3(t.x * TILE, 0.0, t.y * TILE)


static func cell_to_tile(c: Vector2i) -> Vector2i:
	return Vector2i(floori(float(c.x) / CELLS_PER_TILE), floori(float(c.y) / CELLS_PER_TILE))


## Top-left cell of a tile.
static func tile_to_cell(t: Vector2i) -> Vector2i:
	return t * CELLS_PER_TILE


static func in_bounds_cell(c: Vector2i, size_cells: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < size_cells.x and c.y < size_cells.y


static func in_bounds_tile(t: Vector2i, size_tiles: Vector2i) -> bool:
	return t.x >= 0 and t.y >= 0 and t.x < size_tiles.x and t.y < size_tiles.y


## Cell rect covered by a footprint of `size` cells centred on `center`. Even sizes snap the
## centre to a cell corner, odd sizes to a cell centre (keeps buildings grid aligned).
static func footprint_rect(center: Vector3, size: Vector2i) -> Rect2i:
	var origin := Vector2i(roundi(center.x / CELL - size.x * 0.5), roundi(center.z / CELL - size.y * 0.5))
	return Rect2i(origin, size)


## World-space centre of a footprint rect (y = 0).
static func rect_center_world(r: Rect2i) -> Vector3:
	return Vector3((r.position.x + r.size.x * 0.5) * CELL, 0.0, (r.position.y + r.size.y * 0.5) * CELL)


static func snap_to_footprint(center: Vector3, size: Vector2i) -> Vector3:
	var c := rect_center_world(footprint_rect(center, size))
	c.y = center.y
	return c


static func rect_cells(r: Rect2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for y in range(r.position.y, r.end.y):
		for x in range(r.position.x, r.end.x):
			out.append(Vector2i(x, y))
	return out


static func flat_dist(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()
