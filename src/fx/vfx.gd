class_name Vfx
extends Node3D
## Visual-only combat feedback driven by Events; never touches sim state or World.rng.
## - floating combat text: pooled Label3D numbers that rise and fade (red when the local
##   player's units are hurt, pale yellow otherwise);
## - hit flash: tells the victim's UnitView to flash.
## Animated in _process with delta, so it looks the same at any refresh rate.

const POOL := 48
const LIFE := 0.9
const RISE := 1.6
const OWN_HURT := Color(1.0, 0.36, 0.30)
const DEALT := Color(1.0, 0.94, 0.62)

var world: World
var _labels: Array[Label3D] = []
var _age := PackedFloat32Array()
var _next: int = 0
var _jitter := RandomNumberGenerator.new()   ## visual jitter only (never the sim RNG)


func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	_age.resize(POOL)
	for i in POOL:
		var l := Label3D.new()
		l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		l.no_depth_test = true
		l.fixed_size = false
		l.pixel_size = 0.0095
		l.font_size = 48
		l.outline_size = 10
		l.render_priority = 20
		l.outline_render_priority = 19
		l.visible = false
		l.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		add_child(l)
		_labels.append(l)
		_age[i] = LIFE


func setup(w: World) -> void:
	world = w
	if not Events.unit_damaged.is_connected(_on_unit_damaged):
		Events.unit_damaged.connect(_on_unit_damaged)


func active_count() -> int:
	var n := 0
	for l in _labels:
		if l.visible:
			n += 1
	return n


func show_text(p: Vector3, text: String, col: Color) -> void:
	var l := _labels[_next]
	_age[_next] = 0.0
	_next = (_next + 1) % POOL
	l.text = text
	l.position = p
	l.modulate = col
	l.outline_modulate = Color(0, 0, 0, 0.85)
	l.visible = true


func _on_unit_damaged(u: Node, amount: float, _src: Node) -> void:
	var unit := u as Unit
	if unit == null or unit.world != world:
		return
	if unit.view is UnitView:
		(unit.view as UnitView).flash()
	var col := OWN_HURT if unit.player_id == world.local_player_id else DEALT
	var p := unit.pos + Vector3(_jitter.randf_range(-0.45, 0.45),
		unit.top_height() + _jitter.randf_range(0.35, 0.8), _jitter.randf_range(-0.2, 0.2))
	show_text(p, str(maxi(roundi(amount), 1)), col)


func _process(delta: float) -> void:
	for i in POOL:
		var l := _labels[i]
		if not l.visible:
			continue
		_age[i] += delta
		var k := _age[i] / LIFE
		if k >= 1.0:
			l.visible = false
			continue
		l.position.y += RISE * delta * (1.0 - k * 0.6)
		var a := 1.0 - k * k
		l.modulate.a = a
		l.outline_modulate.a = a * 0.85
		l.scale = Vector3.ONE * (1.0 + 0.25 * (1.0 - minf(k * 6.0, 1.0)))
