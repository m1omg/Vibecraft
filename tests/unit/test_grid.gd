extends "res://tests/test_case.gd"


func test_cell_roundtrip() -> void:
	for c: Vector2i in [Vector2i(0, 0), Vector2i(5, 7), Vector2i(383, 383), Vector2i(120, 3)]:
		assert_eq(Grid.world_to_cell(Grid.cell_to_world(c)), c, "cell roundtrip")


func test_cell_centre() -> void:
	assert_eq(Grid.cell_to_world(Vector2i(0, 0)), Vector3(0.25, 0.0, 0.25))
	assert_eq(Grid.world_to_cell(Vector3(0.49, 3.0, 0.51)), Vector2i(0, 1))
	assert_eq(Grid.world_to_cell(Vector3(-0.1, 0.0, 0.0)), Vector2i(-1, 0), "floors negatives")


func test_tile_helpers() -> void:
	assert_eq(Grid.world_to_tile(Vector3(3.9, 0, 4.1)), Vector2i(1, 2))
	assert_eq(Grid.tile_to_world(Vector2i(1, 2)), Vector3(3.0, 0.0, 5.0))
	assert_eq(Grid.tile_to_cell(Vector2i(3, 2)), Vector2i(12, 8))
	assert_eq(Grid.cell_to_tile(Vector2i(13, 9)), Vector2i(3, 2))
	assert_eq(Grid.cell_to_tile(Vector2i(-1, 0)), Vector2i(-1, 0))
	assert_eq(Grid.CELLS_PER_TILE, int(Grid.TILE / Grid.CELL))


func test_bounds() -> void:
	var size := Vector2i(384, 384)
	assert_true(Grid.in_bounds_cell(Vector2i(0, 0), size))
	assert_true(Grid.in_bounds_cell(Vector2i(383, 383), size))
	assert_false(Grid.in_bounds_cell(Vector2i(384, 0), size))
	assert_false(Grid.in_bounds_cell(Vector2i(0, -1), size))
	assert_true(Grid.in_bounds_tile(Vector2i(95, 95), Vector2i(96, 96)))
	assert_false(Grid.in_bounds_tile(Vector2i(96, 95), Vector2i(96, 96)))


func test_footprint_rect() -> void:
	var r := Grid.footprint_rect(Vector3(10.0, 0.0, 10.0), Vector2i(4, 4))
	assert_eq(r, Rect2i(18, 18, 4, 4), "even footprint centred on cell corner")
	assert_eq(Grid.rect_center_world(r), Vector3(10.0, 0.0, 10.0))
	var odd := Grid.footprint_rect(Vector3(10.25, 0.0, 10.25), Vector2i(3, 3))
	assert_eq(odd, Rect2i(19, 19, 3, 3), "odd footprint centred on cell centre")
	assert_eq(Grid.rect_cells(Rect2i(0, 0, 2, 3)).size(), 6)
	var snapped := Grid.snap_to_footprint(Vector3(10.1, 2.0, 9.8), Vector2i(10, 10))
	assert_eq(snapped, Vector3(10.0, 2.0, 10.0), "snap keeps y")
