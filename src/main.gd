class_name Main
extends Node3D
## Boots a skirmish.
## scenario "slice" (default): Wether Downs (data/maps/<rules.match.map>.json), Brennmark (player 0,
##   local) vs the Tormai (player 1, AI): each starts with its T1 hall, 5 idle workers between the
##   hall and the main Gold Seam, 500 gold / 150 lumber (rules §3.2); Gold Seams, neutral buildings
##   and creep camps from the map. Falls back to the sandbox when the map file is missing.
## scenario "battlefield": Playtest 1, the Battlefield sandbox (data/scenarios.json "battlefield",
##   src/scenarios/battlefield.gd): the slice map with both factions' static bases, two armies,
##   three creep camps, a scripted Tormai opponent and an annihilation victory with an end banner.
## scenario "sandbox": the generated test map with the placeholder dummy_* defs (hall, barracks,
##   workers, a few soldiers / archers each side) used by the input / HUD tests and the battle
##   playtest. Set `scenario` before adding the scene to the tree.
## The game starts in the main menu (src/ui/main_menu.tscn); `Main.start_match(tree, scenario)`
## swaps the current scene for a fresh match (menu buttons, pause-menu Restart, Play again).

const MAIN_SCENE := "res://src/main.tscn"
const MENU_SCENE := "res://src/ui/main_menu.tscn"

@export_enum("slice", "sandbox", "battlefield") var scenario: String = "slice"
@export var map_seed: int = 1337
@export var player_factions: Array[String] = ["kingdom", "clans"]
## false: only the map (with its Gold Seams and neutral buildings), lighting and camera are set up;
## no start bases or creep camps (screenshot / showcase scripts place units).
@export var spawn_skirmish: bool = true
## Sandbox slot colours (art bible §2.4: kingdom Emerald vs clans Royal Blue, never the reference
## pairing of blue against red). The slice picks the same pair from factions.<id>.colour_prefs.
const SLOT_COLORS: Array[Color] = [Color("#2EAE3A"), Color("#285DE6")]

@onready var world: World = $World
@onready var camera: RtsCamera = $Camera
@onready var selection: Selection = $UI/Selection
@onready var commands: CommandInput = $CommandInput
@onready var hud: Hud = $HUD
@onready var info: Label = $UI/Info
@onready var objective: Label = $UI/Objective

## The Playtest 1 scenario (scenario "battlefield"), else null.
var battle: BattlefieldScenario = null
var pause_menu: PauseMenu
var end_banner: EndBanner
## Deaths per player id since the match started (end-banner tallies; visual only).
var losses: Dictionary = {}


## Replaces the current scene with a fresh match of `scenario_name` (unpauses the tree). The
## old scene is freed by the SceneTree at the end of the frame.
static func start_match(tree: SceneTree, scenario_name: String) -> Node:
	var m: Node = (load(MAIN_SCENE) as PackedScene).instantiate()
	m.set("scenario", scenario_name)
	tree.paused = false
	tree.change_scene_to_node(m)
	return m


## Back to the main menu (unpauses the tree).
static func quit_to_menu(tree: SceneTree) -> void:
	Audio.stop_music(0.5)
	tree.paused = false
	tree.change_scene_to_file(MENU_SCENE)


func _ready() -> void:
	var map: MapData = null
	if scenario == "slice" or scenario == "battlefield":
		var map_name := str(Defs.rule("match.map", "slice"))
		if scenario == "battlefield":
			map_name = str(Defs.scenario(scenario).get("map", map_name))
		var path := "res://data/maps/%s.json" % map_name
		if FileAccess.file_exists(path):
			map = MapData.load_json(path)
	if map != null and scenario == "battlefield":
		_boot_battlefield(map)
	elif map != null:
		_boot_slice(map)
	else:
		_boot_sandbox()
	selection.setup(world, camera, 0)
	commands.setup(world, camera, selection, 0)
	hud.setup(world, selection, commands, camera, 0)
	pause_menu = PauseMenu.new()
	pause_menu.name = "PauseMenu"
	add_child(pause_menu)
	pause_menu.resume_pressed.connect(_toggle_pause)
	pause_menu.restart_pressed.connect(func() -> void: Main.start_match(get_tree(), scenario))
	pause_menu.menu_pressed.connect(func() -> void: Main.quit_to_menu(get_tree()))
	end_banner = EndBanner.new()
	end_banner.name = "EndBanner"
	add_child(end_banner)
	end_banner.play_again_pressed.connect(func() -> void: Main.start_match(get_tree(), scenario))
	end_banner.menu_pressed.connect(func() -> void: Main.quit_to_menu(get_tree()))
	Events.menu_requested.connect(_toggle_pause)
	Events.unit_died.connect(_on_unit_died)
	objective.visible = battle != null
	var lp := world.player(world.local_player_id)
	Audio.match_started(lp.faction if lp != null else "", world.local_player_id)   # opening cue


func _boot_slice(map: MapData) -> void:
	world.setup(map, map_seed)
	_setup_view()
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
	_spawn_map_neutrals(map)
	if spawn_skirmish:
		for pid in 2:
			_spawn_start(pid, map.start_locations[pid], map.gold_mines[pid], map)
		world.creeps.spawn_camps(map)
	camera.setup(world, map.start_locations[0] + Vector3(0, 0, -4))


## Playtest 1: players and map neutrals here, everything else from the scenario data.
func _boot_battlefield(map: MapData) -> void:
	world.setup(map, map_seed)
	_setup_view()
	BattlefieldScenario.add_players(world, scenario)
	world.local_player_id = 0
	_spawn_map_neutrals(map)
	battle = BattlefieldScenario.new()
	battle.name = "Scenario"
	world.systems_root.add_child(battle)
	battle.setup_match(world, scenario)
	battle.ended.connect(_on_match_ended)
	camera.setup(world, battle.camera_start(0))


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


## The map's Gold Seams (facing their nearest hall site) and neutral buildings.
func _spawn_map_neutrals(map: MapData) -> void:
	for i in map.gold_mines.size():
		var g := map.gold_mines[i]
		var hall := _nearest_hall_site(map, g)
		world.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, g, atan2(-(hall.x - g.x), -(hall.z - g.z)))
	for nb: Dictionary in map.neutral_buildings:
		world.spawn_unit(str(nb["def"]), PlayerState.NEUTRAL_PASSIVE, nb["pos"], deg_to_rad(float(nb.get("facing", 0.0))))


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
	_setup_view()
	for p: PlayerState in [world.add_player(0, 0, "placeholder_a", false),
			world.add_player(1, 1, "placeholder_b", true)]:
		var fac := Defs.faction(p.faction)
		p.gold = int(fac.get("start_gold", 0))
		p.lumber = int(fac.get("start_lumber", 0))
		p.color = SLOT_COLORS[p.id]
	world.add_player(PlayerState.NEUTRAL_HOSTILE, PlayerState.NEUTRAL_HOSTILE)
	world.add_player(PlayerState.NEUTRAL_PASSIVE, PlayerState.NEUTRAL_PASSIVE)
	world.local_player_id = 0
	if spawn_skirmish:
		for pid in 2:
			_spawn_sandbox_base(pid, map.start_locations[pid], map.gold_mines[pid], map)
		world.creeps.spawn_camps(map)
	camera.setup(world, map.start_locations[0] + Vector3(0, 0, -4))


## Environment setup: camera constants (RenderProfile, research README §1) and the view hooks
## (selection rim highlight, building pads). Lighting and grade live in DayNight.
func _setup_view() -> void:
	RenderProfile.apply_camera(camera)
	var hooks := ViewHooks.new()
	hooks.name = "ViewHooks"
	world.add_child(hooks)
	hooks.setup(world)


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
	if end_banner != null and end_banner.visible:
		return
	get_tree().paused = not get_tree().paused
	pause_menu.visible = get_tree().paused
	if get_tree().paused:
		commands.cancel_targeting()


func _on_unit_died(u: Node, _killer: Node) -> void:
	var unit := u as Unit
	if unit != null and unit.world == world:
		losses[unit.player_id] = int(losses.get(unit.player_id, 0)) + 1


## The scenario decided the match: the end banner (the world keeps running behind it).
func _on_match_ended(winner: int) -> void:
	commands.cancel_targeting()
	hud.clear_notice()
	var lp := world.local_player_id
	var kind := "draw" if winner < 0 else ("victory" if winner == lp else "defeat")
	var enemy_losses := 0
	for pid: int in losses:
		if pid != lp and pid < PlayerState.NEUTRAL_HOSTILE:
			enemy_losses += int(losses[pid])
	end_banner.show_result(kind, world.time, int(losses.get(lp, 0)), enemy_losses)


func _process(_delta: float) -> void:
	if battle != null:
		_set_objective()
	var hour := DayNight.hour_at(world.time)
	info.text = "FPS %d | tick %d | units %d | %02d:%02d | selected %d" % [
		Engine.get_frames_per_second(), world.tick_count, world.unit_list.size(),
		int(hour), int(fmod(hour, 1.0) * 60.0), selection.selected.size()]


func _set_objective() -> void:
	var t := Defs.text("objective_battlefield")
	var eta := battle.wave_eta()
	if eta >= 0.0:
		var secs := ceili(eta)
		@warning_ignore("integer_division")
		t += "\n" + Defs.text("objective_wave_in") % [secs / 60, secs % 60]
	elif battle.wave_marching():
		t += "\n" + Defs.text("objective_wave_out")
	if objective.text != t:
		objective.text = t
