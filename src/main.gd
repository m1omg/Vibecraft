extends Node3D
## Boots a skirmish on the generated test slice: player 0 (local human) vs player 1, each with
## a hall, barracks, 5 workers and a few soldiers/archers; neutral mines and creep camps.

@export var map_seed: int = 1337

@onready var world: World = $World
@onready var camera: RtsCamera = $Camera
@onready var selection: Selection = $UI/Selection
@onready var commands: CommandInput = $CommandInput
@onready var hud: Hud = $HUD
@onready var info: Label = $UI/Info
@onready var pause_label: Label = $UI/Paused


func _ready() -> void:
	Defs.load_test_defs()   # the sandbox still uses the placeholder dummy_* defs
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
		_spawn_base(pid, map.start_locations[pid], map.gold_mines[pid], map)
	_spawn_camps(map)
	camera.setup(world, map.start_locations[0] + Vector3(0, 0, -4))
	selection.setup(world, camera, 0)
	commands.setup(world, camera, selection, 0)
	hud.setup(world, selection, commands, camera, 0)
	Events.menu_requested.connect(_toggle_pause)


func _spawn_base(pid: int, start: Vector3, mine: Vector3, map: MapData) -> void:
	var centre := Vector3(map.size_world().x * 0.5, 0.0, map.size_world().y * 0.5)
	var inward := (centre - start).normalized()
	var side := Vector3(-inward.z, 0.0, inward.x)
	var face := atan2(-inward.x, -inward.z)
	var to_hall := start - mine
	world.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, mine, atan2(-to_hall.x, -to_hall.z))
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


func _spawn_camps(map: MapData) -> void:
	for camp in map.creep_camps:
		var c: Vector3 = camp["pos"]
		var creeps: Array = camp["creeps"]
		for i in creeps.size():
			var a := TAU * i / creeps.size()
			world.spawn_unit(creeps[i], PlayerState.NEUTRAL_HOSTILE, c + Vector3(cos(a), 0, sin(a)) * 1.4, a)


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
