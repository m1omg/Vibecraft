class_name Selection
extends Control
## Full-screen overlay handling unit selection for the local player: click, drag box,
## shift add/remove, ctrl+click / double-click select-all-of-type on screen, control groups
## (ctrl+N set, shift+N add, N recall, double-tap N centres camera), Tab / Shift+Tab subgroups,
## F1–F3 heroes (double-tap centres) and Backspace own halls (rules §18.3).
## The selection is kept in subgroup priority order (rules §18.3): heroes first (training
## order), then by food cost (highest first), then by type; the 12-unit cap applies after that
## order, so a box over a large army keeps its heroes. Picking is screen-space against
## interpolated unit positions (no physics bodies needed).

const BOX_FILL := Color(0.3, 1.0, 0.35, 0.10)
const BOX_LINE := Color(0.4, 1.0, 0.45, 0.9)

var world: World
var camera: RtsCamera
var player_id: int = 0
var selected: Array[Unit] = []
var groups: Array = []                 ## 10 x Array[Unit]
var subgroup: int = 0                  ## index into subgroup_defs()
var enabled: bool = true               ## CommandInput disables while targeting

var _pressing: bool = false
var _dragging: bool = false
var _press_pos: Vector2 = Vector2.ZERO
var _skip_release: bool = false
var _last_group: int = -1
var _last_group_ms: int = 0
var _last_hero: int = -1
var _last_hero_ms: int = 0
var _hall_cursor: int = -1              ## unit id of the hall Backspace selected last


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	groups.resize(10)
	for i in 10:
		groups[i] = []
	Events.unit_died.connect(_on_unit_died)


func setup(w: World, cam: RtsCamera, pid: int) -> void:
	world = w
	camera = cam
	player_id = pid


# --- public API ----------------------------------------------------------------------------

func select_units(units: Array, add: bool = false) -> void:
	var next: Array[Unit] = []
	if add:
		next = selected.duplicate()
	var fresh: Array[Unit] = []
	for u: Unit in units:
		if u != null and u.alive and not next.has(u) and not fresh.has(u):
			fresh.append(u)
	fresh.sort_custom(priority_before)
	for u in fresh:
		if next.size() < Settings.max_selection:
			next.append(u)
	_set_selection(next)


## Subgroup priority (rules §18.3): heroes first in training order, then food cost (highest
## first), then type, then spawn order.
static func priority_before(a: Unit, b: Unit) -> bool:
	if a.is_hero != b.is_hero:
		return a.is_hero
	if a.is_hero:
		return a.id < b.id
	var fa := food_cost(a)
	var fb := food_cost(b)
	if fa != fb:
		return fa > fb
	if a.def_id != b.def_id:
		return a.def_id < b.def_id
	return a.id < b.id


static func food_cost(u: Unit) -> int:
	return int((u.def.get("cost", {}) as Dictionary).get("food", 0))


func clear() -> void:
	_set_selection([])


func selected_ids(own_only: bool = true) -> Array:
	var ids: Array = []
	for u in selected:
		if u.alive and (not own_only or u.player_id == player_id):
			ids.append(u.id)
	return ids


## Distinct def ids in the selection in subgroup priority order (the selection is kept sorted;
## Tab / Shift+Tab cycle through them, the first, a hero when there is one, starts active).
func subgroup_defs() -> Array[String]:
	var out: Array[String] = []
	for u in selected:
		if not out.has(u.def_id):
			out.append(u.def_id)
	return out


func active_subgroup_def() -> String:
	var defs := subgroup_defs()
	return defs[subgroup % defs.size()] if not defs.is_empty() else ""


## Unit under a screen position (closest projected centre within its projected radius).
func pick_unit(screen_pos: Vector2) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in world.unit_list:
		if not u.alive:
			continue
		var c := _screen_centre(u)
		if c.x == INF:
			continue
		var r := _screen_radius(u)
		var d := c.distance_to(screen_pos)
		if d <= r and d / r < best_d:
			best_d = d / r
			best = u
	return best


# --- input ---------------------------------------------------------------------------------

## Presses arrive here only when no HUD control took them (HUD panels stop the mouse).
func _unhandled_input(event: InputEvent) -> void:
	if world == null:
		return
	if event is InputEventMouseButton and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		_mouse_button(event as InputEventMouseButton)
	elif event is InputEventKey and event.pressed and not event.echo:
		_key(event as InputEventKey)


## Once a press started in the world, drag motion and the release are taken before the GUI so a
## box that ends over the HUD still completes.
func _input(event: InputEvent) -> void:
	if world == null or not _pressing:
		return
	if event is InputEventMouseMotion:
		if not _dragging and _press_pos.distance_to(event.position) > Settings.drag_threshold_px:
			_dragging = true
		if _dragging:
			queue_redraw()
	elif event is InputEventMouseButton and not event.pressed \
			and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		_mouse_button(event as InputEventMouseButton)


func _mouse_button(mb: InputEventMouseButton) -> void:
	if mb.pressed:
		if not enabled:
			return
		_pressing = true
		_dragging = false
		_press_pos = mb.position
		_skip_release = false
		if mb.double_click:
			var u := pick_unit(mb.position)
			if u != null:
				_select_same_type_on_screen(u)
				_skip_release = true
		get_viewport().set_input_as_handled()
		return
	if not _pressing:
		return
	_pressing = false
	if _dragging:
		_dragging = false
		queue_redraw()
		_box_select(Rect2(_press_pos, mb.position - _press_pos).abs(), mb.shift_pressed)
	elif not _skip_release:
		_click_select(mb.position, mb.shift_pressed, mb.ctrl_pressed)
	get_viewport().set_input_as_handled()


func _key(k: InputEventKey) -> void:
	for n in 10:
		if k.is_action_pressed("group_%d" % n):
			if k.ctrl_pressed:
				groups[n] = _own(selected)
			elif k.shift_pressed:
				var g: Array = groups[n]
				for u in _own(selected):
					if not g.has(u) and g.size() < Settings.max_selection:
						g.append(u)
			else:
				_recall_group(n)
			get_viewport().set_input_as_handled()
			return
	if k.is_action_pressed("subgroup_next") and not selected.is_empty():
		var n := maxi(subgroup_defs().size(), 1)
		subgroup = posmod(subgroup + (-1 if k.shift_pressed else 1), n)
		Events.selection_changed.emit(selected)
		get_viewport().set_input_as_handled()
		return
	for n in 3:
		if k.is_action_pressed("select_hero_%d" % (n + 1)):
			select_hero(n)
			get_viewport().set_input_as_handled()
			return
	if k.is_action_pressed("cycle_halls"):
		cycle_halls()
		get_viewport().set_input_as_handled()


## Own living heroes in training order (F1–F3).
func own_heroes() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.is_hero and u.player_id == player_id:
			out.append(u)
	out.sort_custom(func(a: Unit, b: Unit) -> bool: return a.id < b.id)
	return out


## F1–F3: selects the n-th hero (0-based); pressing the same key again within the double-click
## time centres the camera on it. Returns false when there is no such hero.
func select_hero(n: int) -> bool:
	var heroes := own_heroes()
	if n < 0 or n >= heroes.size():
		return false
	var h := heroes[n]
	var now := Time.get_ticks_msec()
	if _last_hero == n and now - _last_hero_ms < Settings.double_click_ms and selected.size() == 1 \
			and selected[0] == h:
		camera.jump_to(h.pos)
	_last_hero = n
	_last_hero_ms = now
	_set_selection([h])
	return true


## Backspace: selects the next own hall (town_hall flag; finished or not) and centres the
## camera on it. Returns the hall, or null when the player has none.
func cycle_halls() -> Unit:
	var halls: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.has_flag("town_hall"):
			halls.append(u)
	if halls.is_empty():
		return null
	var next := halls[0]
	for i in halls.size():
		if halls[i].id == _hall_cursor:
			next = halls[(i + 1) % halls.size()]
			break
	_hall_cursor = next.id
	_set_selection([next])
	camera.jump_to(next.pos)
	return next


func _recall_group(n: int) -> void:
	var g: Array = groups[n]
	var alive: Array = g.filter(func(u: Unit) -> bool: return is_instance_valid(u) and u.alive)
	if alive.is_empty():
		return
	var now := Time.get_ticks_msec()
	if _last_group == n and now - _last_group_ms < Settings.double_click_ms:
		var c := Vector3.ZERO
		for u: Unit in alive:
			c += u.pos
		camera.jump_to(c / alive.size())
	_last_group = n
	_last_group_ms = now
	select_units(alive)


# --- selection rules -----------------------------------------------------------------------

func _click_select(pos: Vector2, shift: bool, ctrl: bool) -> void:
	var u := pick_unit(pos)
	if u == null:
		if not shift:
			clear()
		return
	if ctrl:
		_select_same_type_on_screen(u)
		return
	if shift and u.player_id == player_id and _all_own(selected):
		var next := selected.duplicate()
		if next.has(u):
			next.erase(u)
		elif next.size() < Settings.max_selection:
			next.append(u)
		_set_selection(next)
		return
	_set_selection([u])


func _box_select(rect: Rect2, shift: bool) -> void:
	var own_units: Array[Unit] = []
	var own_buildings: Array[Unit] = []
	var others: Array[Unit] = []
	for u in world.unit_list:
		if not u.alive or u.is_resource:
			continue
		var c := _screen_centre(u)
		if c.x == INF or not rect.has_point(c):
			continue
		if u.player_id != player_id:
			others.append(u)
		elif u.is_building:
			own_buildings.append(u)
		else:
			own_units.append(u)
	var pick: Array = own_units if not own_units.is_empty() else own_buildings
	if pick.is_empty() and not shift and not others.is_empty():
		pick = [others[0]]
	if pick.is_empty():
		if not shift:
			clear()
		return
	select_units(pick, shift and _all_own(selected))


func _select_same_type_on_screen(u: Unit) -> void:
	if u.player_id != player_id:
		_set_selection([u])
		return
	var view := get_viewport().get_visible_rect()
	var same: Array[Unit] = [u]
	for o in world.unit_list:
		if o != u and o.alive and o.player_id == player_id and o.def_id == u.def_id:
			var c := _screen_centre(o)
			if c.x != INF and view.has_point(c):
				same.append(o)
	select_units(same)


func _set_selection(units: Array) -> void:
	var sorted: Array[Unit] = []
	for u: Unit in units:
		if not sorted.has(u):
			sorted.append(u)
	sorted.sort_custom(priority_before)
	var next: Array[Unit] = []
	for u in sorted:
		if next.size() < Settings.max_selection:
			next.append(u)
	selected = next
	subgroup = 0
	Events.selection_changed.emit(selected)


func _own(units: Array) -> Array:
	return units.filter(func(u: Unit) -> bool: return u.player_id == player_id)


func _all_own(units: Array) -> bool:
	for u: Unit in units:
		if u.player_id != player_id:
			return false
	return true


func _on_unit_died(u: Node, _killer: Node) -> void:
	for n in 10:
		(groups[n] as Array).erase(u)
	if selected.has(u):
		var next := selected.duplicate()
		next.erase(u)
		_set_selection(next)


# --- projection helpers --------------------------------------------------------------------

func _screen_centre(u: Unit) -> Vector2:
	var p := u.display_pos() + Vector3(0, _unit_height(u) * 0.5, 0)
	if camera.is_position_behind(p):
		return Vector2(INF, INF)
	return camera.unproject_position(p)


func _screen_radius(u: Unit) -> float:
	var r := u.radius
	if u.footprint.size != Vector2i.ZERO:
		r = maxf(u.footprint.size.x, u.footprint.size.y) * Grid.CELL * 0.5
	var p := u.display_pos() + Vector3(0, _unit_height(u) * 0.5, 0)
	var edge := camera.unproject_position(p + camera.global_basis.x * maxf(r, _unit_height(u) * 0.45))
	return maxf(edge.distance_to(camera.unproject_position(p)), 12.0)


func _unit_height(u: Unit) -> float:
	return float(u.def.get("height", 1.5)) * float(u.def.get("scale", 1.0))


func _draw() -> void:
	if not _dragging:
		return
	var rect := Rect2(_press_pos, get_local_mouse_position() - _press_pos).abs()
	draw_rect(rect, BOX_FILL, true)
	draw_rect(rect, BOX_LINE, false, 1.5)
