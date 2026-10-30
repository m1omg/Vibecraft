class_name Vfx
extends Node3D
## The fx runtime and router (juice bible §4.1; `World/Fx/Vfx`). It is not a particle system:
##   - drives the juice clocks once per frame (FxClock.drive; process_priority -100, process
##     ALWAYS, so fx time freezes while the World is paused and ui time keeps running);
##   - subscribes to the Events bus and the projectile root; handlers only ENQUEUE a record
##     (≤ FeelConstants.queue_records), the queue is drained at the top of `_process`, so
##     nothing spawns, flashes or plays inside the fixed tick;
##   - routes records to its modules: CombatFx (impacts, flashes, knockback, deaths, clash),
##     CombatText -> PopupText (the only world text), OrderMarkers (marks, ripple, rally,
##     waypoints), MissileFx (trails, stuck missiles), BuildFx (economy and building beats),
##     the ParticlePool and GroundMarks
##     primitives, and the body composers' acks;
##   - runs the density governor (Calm / Busy / Brawl from the on-screen hit rate, FND-3) and
##     `allow()` (frustum + 2 m, distance from the camera focus, local fog);
##   - `trace(tag, id)` records feel beats for QA when `--feel-trace` is on (bible §5.1);
##   - emits `battle_started(pos)` on a first-contact clash (CMB-36).
## Visual only: never reads World.rng, never writes sim state; juice never changes outcomes
## (tests/unit/test_juice_determinism.gd).

signal battle_started(pos: Vector3)

enum Ev { DAMAGE, DEATH, COMMAND, BOUNTY, INCOME, VOICE }
enum Tier { CALM, BUSY, BRAWL }

static var instance: Vfx

var world: World
var particles: ParticlePool
var marks: GroundMarks
var popups: PopupText
var text: CombatText
var combat: CombatFx
var orders: OrderMarkers
var missiles: MissileFx
var smears: Smears
var circles: SelectionCircles
var bars: HealthBars
var build: BuildFx
var selected: Array = []                 ## the local selection (Events.selection_changed)
var tier: int = Tier.CALM
var intensity: float = 0.0
var hits_this_frame: int = 0
var dropped_records: int = 0
var drained: int = 0
var trace_on: bool = false
var trace_log: Array = []

var _queue: Array = []
var _trace_path: String = ""


func _ready() -> void:
	process_priority = -100
	process_mode = Node.PROCESS_MODE_ALWAYS
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	instance = self
	for a in OS.get_cmdline_user_args():
		if a == "--feel-trace" or a.begins_with("--feel-trace="):
			trace_on = true
			_trace_path = a.trim_prefix("--feel-trace=") if a.contains("=") else ""
	particles = ParticlePool.new()
	particles.name = "Particles"
	particles.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(particles)
	marks = GroundMarks.new()
	marks.name = "GroundMarks"
	add_child(marks)
	popups = PopupText.new()
	popups.name = "PopupText"
	add_child(popups)
	orders = OrderMarkers.new()
	orders.name = "OrderMarkers"
	add_child(orders)
	missiles = MissileFx.new()
	missiles.name = "MissileFx"
	missiles.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(missiles)
	smears = Smears.new()
	smears.name = "Smears"
	add_child(smears)
	build = BuildFx.new()
	build.name = "BuildFx"
	add_child(build)


func setup(w: World) -> void:
	world = w
	instance = self
	particles.setup()
	marks.setup(w)
	popups.setup(w)
	text = CombatText.new(popups, w)
	combat = CombatFx.new(self)
	circles = get_node_or_null("../SelectionCircles") as SelectionCircles
	bars = get_node_or_null("../HealthBars") as HealthBars
	orders.setup(w, self)
	missiles.setup(w, self)
	smears.setup(w)
	build.setup(self, w)
	_connect(Events.unit_damaged, _on_unit_damaged)
	_connect(Events.unit_died, _on_unit_died)
	_connect(Events.command_issued, _on_command)
	_connect(Events.bounty_paid, _on_bounty)
	_connect(Events.income_received, _on_income)
	_connect(Events.selection_changed, _on_selection)
	if Audio.has_signal("voice_started"):
		_connect(Audio.voice_started, _on_voice)


func _connect(sig: Signal, cb: Callable) -> void:
	if not sig.is_connected(cb):
		sig.connect(cb)


func _exit_tree() -> void:
	for pair: Array in [[Events.unit_damaged, _on_unit_damaged], [Events.unit_died, _on_unit_died],
			[Events.command_issued, _on_command], [Events.bounty_paid, _on_bounty],
			[Events.income_received, _on_income], [Events.selection_changed, _on_selection]]:
		var sig: Signal = pair[0]
		if sig.is_connected(pair[1]):
			sig.disconnect(pair[1])
	if Audio.has_signal("voice_started") and Audio.voice_started.is_connected(_on_voice):
		Audio.voice_started.disconnect(_on_voice)
	if instance == self:
		instance = null
	if trace_on and not _trace_path.is_empty():
		_write_trace()


# --- event handlers: enqueue only --------------------------------------------------------------

func _enqueue(rec: Array) -> void:
	if _queue.size() >= FeelConstants.c().queue_records:
		dropped_records += 1
		return
	_queue.append(rec)


func _on_unit_damaged(u: Node, amount: float, src: Node) -> void:
	var unit := u as Unit
	if unit == null or unit.world != world:
		return
	_enqueue([Ev.DAMAGE, unit, amount, src])


func _on_unit_died(u: Node, killer: Node) -> void:
	var unit := u as Unit
	if unit == null or unit.world != world:
		return
	_enqueue([Ev.DEATH, unit, killer])


func _on_command(cmd: Dictionary) -> void:
	if world == null or int(cmd.get("player", -1)) != world.local_player_id:
		return
	_enqueue([Ev.COMMAND, cmd])


func _on_bounty(player_id: int, amount: int, pos: Vector3) -> void:
	_enqueue([Ev.BOUNTY, player_id, amount, pos])


func _on_income(player_id: int, kind: String, amount: int, pos: Vector3) -> void:
	_enqueue([Ev.INCOME, player_id, kind, amount, pos])


func _on_voice(unit: Node, category: String, length: float) -> void:
	var u := unit as Unit
	if u != null and u.world == world:
		_enqueue([Ev.VOICE, u, category, length])


func _on_selection(units: Array) -> void:
	selected = units.duplicate()
	if text != null:
		text.selected = selected


# --- per frame -----------------------------------------------------------------------------------

func _process(delta: float) -> void:
	var running := world != null and is_instance_valid(world) and world.can_process()
	FxClock.drive(delta, running)
	if world == null:
		return
	if not FxClock.manual:
		FxClock.tick_age = world.interpolation_fraction() * World.DT if running else 0.0
	hits_this_frame = 0
	_drain()
	_update_governor(FxClock.fx_dt)


func _drain() -> void:
	if _queue.is_empty():
		return
	var q := _queue
	_queue = []
	for rec: Array in q:
		drained += 1
		match int(rec[0]):
			Ev.DAMAGE:
				if is_instance_valid(rec[1]):
					combat.on_damage(rec[1], float(rec[2]), rec[3] if is_instance_valid(rec[3]) else null)
			Ev.DEATH:
				if is_instance_valid(rec[1]):
					combat.on_death(rec[1], rec[2] if is_instance_valid(rec[2]) else null)
			Ev.COMMAND:
				orders.on_command(rec[1])
			Ev.BOUNTY:
				text.on_bounty(int(rec[1]), int(rec[2]), rec[3])
			Ev.INCOME:
				text.on_income(int(rec[1]), str(rec[2]), int(rec[3]), rec[4])
			Ev.VOICE:
				_voice(rec[1], str(rec[2]), float(rec[3]))


func _voice(u: Unit, category: String, length: float) -> void:
	if not is_instance_valid(u):
		return
	var v := u.view as UnitView
	if v != null and v.juice != null:
		v.juice.ack(0 if category in ["what", "annoyed"] else 1)
	if circles != null:
		circles.shimmer(u, length)
	trace("CMB-13.ack", u.id)


## FND-3: exponential-kernel rate of on-screen hits (τ 0.5 s) with hysteresis.
func _update_governor(dt: float) -> void:
	var fc := FeelConstants.c()
	if dt > 0.0:
		intensity = intensity * exp(-dt / 0.5) + hits_this_frame / 0.5
	elif hits_this_frame > 0:
		intensity += hits_this_frame / 0.5
	match tier:
		Tier.CALM:
			if intensity >= fc.brawl_enter:
				tier = Tier.BRAWL
			elif intensity >= fc.busy_enter:
				tier = Tier.BUSY
		Tier.BUSY:
			if intensity >= fc.brawl_enter:
				tier = Tier.BRAWL
			elif intensity < fc.busy_exit:
				tier = Tier.CALM
		Tier.BRAWL:
			if intensity < fc.brawl_exit:
				tier = Tier.BUSY if intensity >= fc.busy_exit else Tier.CALM


## Spark multiplier for the current tier (Calm 1.0, Busy 0.6, Brawl 0.35).
func tier_mult() -> float:
	var fc := FeelConstants.c()
	match tier:
		Tier.BUSY:
			return fc.spark_mult_busy
		Tier.BRAWL:
			return fc.spark_mult_brawl
	return fc.spark_mult_calm


## May a cosmetic effect be drawn at `pos`? (inside the camera frustum with a 2 m margin, within
## `far_m` of the camera focus, visible to the local player). Information effects (flashes,
## rings, bars, deaths) never ask.
func allow(pos: Vector3, importance: int = 1) -> bool:
	if world == null:
		return false
	if world.fog != null and not world.fog.is_visible(world.local_player_id, pos):
		return false
	var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
	if cam == null:
		return true
	var f: Variant = cam.get("focus")
	var focus: Vector3 = f if f is Vector3 else cam.global_position
	if Vector2(pos.x - focus.x, pos.z - focus.z).length() > FeelConstants.c().far_m and importance < 3:
		return false
	for p in cam.get_frustum():
		if p.distance_to(pos) > 2.0:
			return false
	return true


## Feel trace (bible §5.1): {frame, ui_now, fx_now, sim_tick, tag, id}. No-op unless traced.
func trace(tag: String, entity_id: int = -1) -> void:
	if not trace_on:
		return
	trace_log.append({"frame": FxClock.frame, "ui_now": FxClock.ui_now, "fx_now": FxClock.fx_now,
		"sim_tick": world.tick_count if world != null else -1, "tag": tag, "id": entity_id})


func _write_trace() -> void:
	var f := FileAccess.open(_trace_path, FileAccess.WRITE)
	if f == null:
		return
	for r: Dictionary in trace_log:
		f.store_line(JSON.stringify(r))


## Body contact after a death fall (BodyJuice.compose_dead).
func body_landed(u: Unit, pos: Vector3) -> void:
	if combat != null:
		combat.on_body_landed(u, pos)
