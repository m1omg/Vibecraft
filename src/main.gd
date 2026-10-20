extends Node3D
## Boots a skirmish.
## scenario "slice" (default): Wether Downs (data/maps/<rules.match.map>.json), Brennmark (player 0,
##   local) vs the Tormai (player 1, AI): each starts with its T1 hall, 5 idle workers between the
##   hall and the main Gold Seam, 500 gold / 150 lumber (rules §3.2); Gold Seams, neutral buildings
##   and creep camps from the map. Falls back to the sandbox when the map file is missing.
## scenario "sandbox": the generated test map with the placeholder dummy_* defs (hall, barracks,
##   workers, a few soldiers / archers each side) used by the input / HUD tests and the battle
##   playtest. Set `scenario` before adding the scene to the tree.

@export_enum("slice", "sandbox") var scenario: String = "slice"
@export var map_seed: int = 1337
@export var player_factions: Array[String] = ["kingdom", "clans"]

@onready var world: World = $World
@onready var camera: RtsCamera = $Camera
@onready var selection: Selection = $UI/Selection
@onready var commands: CommandInput = $CommandInput
@onready var hud: Hud = $HUD
@onready var info: Label = $UI/Info
@onready var pause_label: Label = $UI/Paused


func _ready() -> void:
	var map: MapData = null
	if scenario == "slice":
		var path := "res://data/maps/%s.json" % str(Defs.rule("match.map", "slice"))
		if FileAccess.file_exists(path):
			map = MapData.load_json(path)
	if map != null:
		_boot_slice(map)
	else:
		_boot_sandbox()
	selection.setup(world, camera, 0)
	commands.setup(world, camera, selection, 0)
	hud.setup(world, selection, commands, camera, 0)
	Events.menu_requested.connect(_toggle_pause)


func _boot_slice(map: MapData) -> void:
	world.setup(map, map_seed)
	var taken: Array = []
	for pid in 2:
		var fid := player_factions[pid]
		var p := world.add_player(pid, pid, fid, pid == 1)
		p.color = PlayerState.colour_for(fid, taken)
		taken.append(p.color)
		var fac := Defs.faction(fid)
		p.gold = int(fac.get("start_gold", 0))
		p.lumber = int(fac.get("start_lumber", 0))
	world.add_player(PlayerState.NEUTRAL_HOSTILE, PlayerState.NEUTRAL_HOSTILE)
	world.add_player(PlayerState.NEUTRAL_PASSIVE, PlayerState.NEUTRAL_PASSIVE)
	world.local_player_id = 0
	for i in map.gold_mines.size():
		var g := map.gold_mines[i]
		var hall := _nearest_hall_site(map, g)
		world.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, g, atan2(-(hall.x - g.x), -(hall.z - g.z)))
	for nb: Dictionary in map.neutral_buildings:
		world.spawn_unit(str(nb["def"]), PlayerState.NEUTRAL_PASSIVE, nb["pos"], deg_to_rad(float(nb.get("facing", 0.0))))
	for pid in 2:
		_spawn_start(pid, map.start_locations[pid], map.gold_mines[pid], map)
	world.creeps.spawn_camps(map)
	camera.setup(world, map.start_locations[0] + Vector3(0, 0, -4))


## Start base (rules §3.2): the faction's T1 hall and its start units (workers) on a 1 m spacing
## across the hall–seam gap, idle.
func _spawn_start(pid: int, start: Vector3, mine: Vector3, map: MapData) -> void:
	var fac := Defs.faction(world.player(pid).faction)
	var centre := Vector3(map.size_world().x * 0.5, 0.0, map.size_world().y * 0.5)
	var inward := (centre - start).normalized()
	world.spawn_unit(str(fac.get("hall", "")), pid, start, atan2(-inward.x, -inward.z))
	var to_mine := (mine - start)
	to_mine.y = 0.0
	var gap_mid := start + to_mine.normalized() * (to_mine.length() * 0.5)
	var side := Vector3(-to_mine.normalized().z, 0.0, to_mine.normalized().x)
	var spacing := float(Defs.rule("match.start_worker_spacing", 1.0))
	var start_units: Dictionary = fac.get("start_units", {})
	for unit_id: String in start_units:
		var n := int(start_units[unit_id])
		for i in n:
			var p := gap_mid + side * (i - (n - 1) * 0.5) * spacing
			world.spawn_unit(unit_id, pid, p, atan2(-to_mine.x, -to_mine.z))


func _nearest_hall_site(map: MapData, g: Vector3) -> Vector3:
	var best := g + Vector3(0, 0, 1)
	var best_d := INF
	var sites: Array[Vector3] = []
	sites.append_array(map.start_locations)
	for e: Dictionary in map.meta.get("expansions", []):
		var a: Array = e["hall"]
		sites.append(Vector3(a[0], a[1], a[2]))
	for s in sites:
		var d := Grid.flat_dist(s, g)
		if d < best_d:
			best_d = d
			best = s
	return best


func _boot_sandbox() -> void:
	Defs.load_test_defs()   # the sandbox uses the placeholder dummy_* defs
	var map := MapGenerator.test_map(map_seed)
	world.setup(map, map_seed)
	for p: PlayerState in [world.add_player(0, 0, "placeholder_a", false),
			world.add_player(1, 1, "placeholder_b", true)]:
		var fac := Defs.faction(p.faction)
		p.gold = int(fac.get("start_gold", 0))
		p.lumber = int(fac.get("start_lumber", 0))
	world.add_player(PlayerState.NEUTRAL_HOSTILE, PlayerState.NEUTRAL_HOSTILE)
	world.add_player(PlayerState.NEUTRAL_PASSIVE, PlayerState.NEUTRAL_PASSIVE)
	world.local_player_id = 0
	for pid in 2:
		_spawn_sandbox_base(pid, map.start_locations[pid], map.gold_mines[pid], map)
	world.creeps.spawn_camps(map)
	camera.setup(world, map.start_locations[0] + Vector3(0, 0, -4))


func _spawn_sandbox_base(pid: int, start: Vector3, mine: Vector3, map: MapData) -> void:
	var centre := Vector3(map.size_world().x * 0.5, 0.0, map.size_world().y * 0.5)
	var inward := (centre - start).normalized()
	var side := Vector3(-inward.z, 0.0, inward.x)
	var face := atan2(-inward.x, -inward.z)
	var to_hall := start - mine
	world.spawn_unit("dummy_mine", PlayerState.NEUTRAL_PASSIVE, mine, atan2(-to_hall.x, -to_hall.z))
	world.spawn_unit("dummy_hall", pid, start, face)
	world.spawn_unit("dummy_barracks", pid, start + inward * 7.0 + side * 8.0, face)
	var to_mine := (mine - start).normalized()
	var mine_side := Vector3(-to_mine.z, 0.0, to_mine.x)
	for i in 5:
		var p := start + to_mine * 5.0 + mine_side * (i - 2) * 1.0
		world.spawn_unit("dummy_worker", pid, p, atan2(-to_mine.x, -to_mine.z))
	for i in 5:
		var def := "dummy_archer" if i >= 3 else "dummy_soldier"
		var row := 6.0 if i < 3 else 7.4
		var p := start + inward * row + side * ((i % 3) - 1) * 1.3 - side * 3.0
		world.spawn_unit(def, pid, p, face)


## F10 / HUD menu button (Events.menu_requested). Pausing cancels a pending targeting mode:
## CommandInput stops receiving clicks while paused, so it could not be confirmed or cancelled.
func _toggle_pause() -> void:
	get_tree().paused = not get_tree().paused
	pause_label.visible = get_tree().paused
	if get_tree().paused:
		commands.cancel_targeting()


func _process(_delta: float) -> void:
	var hour := DayNight.hour_at(world.time)
	info.text = "FPS %d | tick %d | units %d | %02d:%02d | selected %d" % [
		Engine.get_frames_per_second(), world.tick_count, world.unit_list.size(),
		int(hour), int(fmod(hour, 1.0) * 60.0), selection.selected.size()]
