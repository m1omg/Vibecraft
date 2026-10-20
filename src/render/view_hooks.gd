class_name ViewHooks
extends Node
## Event-driven glue between gameplay events and views (visual only, never touches sim state):
## - selection highlight: `Events.selection_changed` -> UnitView.set_selected (team rim boost);
## - building pads (art bible §6.1): a structure spawn repaints the terrain tiles under and around
##   its footprint (kingdom gv_dirt with a gv_road apron at the door, clans gv_grassy_dirt) and
##   clears decor (tufts, flowers) from the footprint.

const PAD_MARGIN_TILES := 1

var world: World
var _selected: Array = []


func setup(w: World) -> void:
	world = w
	if not Events.selection_changed.is_connected(_on_selection):
		Events.selection_changed.connect(_on_selection)
	if not Events.unit_spawned.is_connected(_on_spawned):
		Events.unit_spawned.connect(_on_spawned)


func _exit_tree() -> void:
	if Events.selection_changed.is_connected(_on_selection):
		Events.selection_changed.disconnect(_on_selection)
	if Events.unit_spawned.is_connected(_on_spawned):
		Events.unit_spawned.disconnect(_on_spawned)


func _on_selection(units: Array) -> void:
	for u: Variant in _selected:
		if is_instance_valid(u) and (u as Unit).view is UnitView:
			((u as Unit).view as UnitView).set_selected(false)
	_selected = units.duplicate()
	for u: Variant in _selected:
		if is_instance_valid(u) and (u as Unit).view is UnitView:
			((u as Unit).view as UnitView).set_selected(true)


func _on_spawned(n: Node) -> void:
	var u := n as Unit
	if u == null or u.world != world or not u.is_building or u.footprint.size == Vector2i.ZERO:
		return
	var faction := faction_of(u)
	if faction.is_empty():
		return
	var r := u.footprint
	var t0 := Grid.cell_to_tile(r.position) - Vector2i.ONE * PAD_MARGIN_TILES
	var t1 := Grid.cell_to_tile(r.end - Vector2i.ONE) + Vector2i.ONE * (PAD_MARGIN_TILES + 1)
	var pad := Rect2i(t0, t1 - t0)
	if world.terrain != null:
		if faction == "kingdom":
			world.terrain.paint_tiles(pad, TerrainTextures.DIRT)
			# flagstone apron in front of the door (fronts face -Z in model space)
			var fwd := Vector3(-sin(u.facing), 0.0, -cos(u.facing))
			var half := Vector2(r.size) * Grid.CELL * 0.5
			var door := u.pos + fwd * (maxf(half.x, half.y) + 1.0)
			var dt := Grid.world_to_tile(door)
			world.terrain.paint_tiles(Rect2i(dt - Vector2i.ONE, Vector2i(2, 2)), TerrainTextures.ROAD)
		else:
			world.terrain.paint_tiles(pad, TerrainTextures.GRASSY_DIRT)
	if world.doodads != null:
		var x0 := r.position.x * Grid.CELL - 0.6
		var z0 := r.position.y * Grid.CELL - 0.6
		world.doodads.clear_decor(Rect2(x0, z0, r.size.x * Grid.CELL + 1.2, r.size.y * Grid.CELL + 1.2))


## "kingdom" / "clans" / "" from the def (`faction`) or the def id prefix.
static func faction_of(u: Unit) -> String:
	var f := str(u.def.get("faction", ""))
	if f.is_empty():
		for p: String in ["kingdom", "clans"]:
			if u.def_id.begins_with(p + "_"):
				f = p
	return f
