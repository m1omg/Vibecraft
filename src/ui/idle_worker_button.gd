class_name IdleWorkerButton
extends Button
## The idle-worker button (juice NTF-05 P0; rules §18.3): at the left end of the console's top
## edge, above the minimap's top-left corner, 52 × 52 px. The faction worker's initials with a
## count badge; faded to α 0.35 with nobody idle; a bounce when the count rises. Click, F8 or
## ` (backtick): select the next idle worker, longest idle first, round robin; the camera jumps
## there and the worker answers. Ctrl+click or Ctrl+F8: every idle worker. Tooltip: "3 idle
## workers · longest 0:42". Polled 4 times a second; reads sim state only (idle = an own living
## worker with no order, not inside a mine or a building).

signal hover_changed(button: IdleWorkerButton, on: bool)

const POLL_S := 0.25
const BOUNCE_S := 0.3
const SIZE := Vector2(52, 52)

var world: World
var selection: Selection
var camera: RtsCamera
var player_id: int = 0
## Idle workers, longest idle first.
var idle: Array[Unit] = []
var _since: Dictionary = {}        ## unit id -> world.time it went idle
var _visited: Array[int] = []      ## ids already picked in this round
var _poll := 10.0
var _bounce_t0 := -10.0
var _box: StyleBoxFlat


func _init() -> void:
	name = "IdleWorker"
	custom_minimum_size = SIZE
	size = SIZE
	focus_mode = Control.FOCUS_NONE
	action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS
	add_theme_font_size_override("font_size", 18)
	_box = StyleBoxFlat.new()
	_box.bg_color = Color(0.16, 0.13, 0.1, 0.95)
	_box.border_color = Color(0.56, 0.46, 0.3)
	_box.set_border_width_all(2)
	_box.set_corner_radius_all(4)
	for st in ["normal", "hover", "pressed", "disabled"]:
		add_theme_stylebox_override(st, _box)
	add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	pressed.connect(_on_pressed)
	mouse_entered.connect(func() -> void: hover_changed.emit(self, true))
	mouse_exited.connect(func() -> void: hover_changed.emit(self, false))


func setup(w: World, sel: Selection, cam: RtsCamera, pid: int) -> void:
	world = w
	selection = sel
	camera = cam
	player_id = pid
	var p := w.player(pid)
	var worker := str(Defs.faction(p.faction).get("worker", "")) if p != null and p.faction != "" else ""
	text = Hud.initials(Defs.unit(worker)) if worker != "" else "W"
	refresh()


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


func count() -> int:
	return idle.size()


## Re-reads the idle workers (also on its own 4 times a second).
func refresh() -> void:
	if world == null:
		return
	var before := idle.size()
	var seen := {}
	var list: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.is_worker and not u.hidden \
				and u.current == null and u.orders.is_empty():
			list.append(u)
			seen[u.id] = true
			if not _since.has(u.id):
				_since[u.id] = world.time
	for id: int in _since.keys():
		if not seen.has(id):
			_since.erase(id)
	list.sort_custom(func(a: Unit, b: Unit) -> bool:
		var ta := float(_since[a.id])
		var tb := float(_since[b.id])
		return ta < tb if ta != tb else a.id < b.id)
	idle = list
	if idle.size() > before:
		_bounce_t0 = now()
	modulate.a = 1.0 if not idle.is_empty() else 0.35
	queue_redraw()


## Seconds the longest-idle worker has been idle.
func longest_s() -> float:
	return world.time - float(_since[idle[0].id]) if not idle.is_empty() else 0.0


## Selects the next idle worker (longest idle first, round robin) and jumps the camera to it;
## `all` selects every idle worker. Returns what was selected.
func select_next(all: bool = false) -> Array[Unit]:
	refresh()
	var out: Array[Unit] = []
	if idle.is_empty():
		return out
	if all:
		out = idle.duplicate()
	else:
		var pick: Unit = null
		for u in idle:
			if not _visited.has(u.id):
				pick = u
				break
		if pick == null:
			_visited.clear()
			pick = idle[0]
		_visited.append(pick.id)
		out = [pick]
	selection.select_units(out)
	if camera != null:
		camera.jump_to(out[0].pos)
	Audio.play_voice(out[0], "what")
	return out


func tooltip_content() -> Dictionary:
	var s := ceili(longest_s())
	var line := Defs.text("idle_workers_none")
	if idle.size() == 1:
		line = Defs.text("idle_worker_one") % [s / 60, s % 60]
	elif idle.size() > 1:
		line = Defs.text("idle_workers") % [idle.size(), s / 60, s % 60]
	return {"title": line, "key": CardModel.action_letter("idle_worker")}


func _on_pressed() -> void:
	if select_next(Input.is_key_pressed(KEY_CTRL)).is_empty():
		Audio.deny("disabled")
	else:
		Audio.ui_click()


func _unhandled_input(event: InputEvent) -> void:
	if world == null or not (event is InputEventKey) or not event.pressed or event.echo:
		return
	if event.is_action_pressed("idle_worker"):
		select_next((event as InputEventKey).ctrl_pressed)
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	_poll += delta
	if _poll >= POLL_S:
		_poll = 0.0
		refresh()
	var age := now() - _bounce_t0
	pivot_offset = size * 0.5
	var b := 1.0 + (0.12 * sin(PI * age / BOUNCE_S) if age < BOUNCE_S else 0.0)
	scale = Vector2(b, b)


func _draw() -> void:
	if idle.is_empty():
		return
	var s := str(idle.size())
	var font := get_theme_default_font()
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
	var r := Rect2(size - Vector2(w + 8, 18), Vector2(w + 6, 16))
	draw_rect(r, Color(0.05, 0.04, 0.03, 0.9))
	draw_string(font, r.position + Vector2(3, 13), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1.0, 0.9, 0.62))
