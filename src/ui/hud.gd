class_name Hud
extends CanvasLayer
## The HUD (docs/architecture.md §11). Top bar bound to the local PlayerState (gold, lumber,
## food, upkeep, day clock, menu): food turns amber at the cap, the upkeep label takes its tier's
## colour, and a refused cost shakes its counter with the shortfall dropping out under it
## (juice ECO-14, ECO-16, HUD-06). Bottom console: minimap, portrait, the selection panel
## (stats, a multi-selection icon grid, a site's construction progress, a building's production
## queue: QueuePanel) and the 4x3 command card (CommandCard). Around it: the idle-worker button
## (IdleWorkerButton), the error line (ErrorLine; error_* notifications), the notice line (other
## notifications) and the one docked tooltip (HudTooltip). The bar and console stop mouse
## events, so clicks on the HUD never reach world selection or commands. Reads sim state, never
## writes it; commands go through CommandInput.

const MAX_ICONS := 24
const ICON_SIZE := Vector2(46, 46)
const HP_GOOD := Color(0.25, 0.85, 0.3)
const HP_LOW := Color(0.95, 0.25, 0.2)
const NOTICE_S := 4.5                ## how long a notification line stays (real time)
const NOTICE_FADE_S := 0.8
const TIP_REFRESH_S := 0.1           ## the tooltip re-checks costs 10 times a second (HUD-02)
const COUNTER_SHAKE_PX := 5.0        ## ECO-14: the short counter shakes at ~10 Hz for 300 ms
const COUNTER_SHAKE_S := 0.3
const GHOST_DROP_S := 0.22           ## HUD-06 shortfall ghost: drop, hold, fade
const GHOST_HOLD_S := 0.9
const GHOST_FADE_S := 0.3
const FOOD_CAPPED := Color("#FFB347")
const UPKEEP_COLORS: Array[Color] = [Color(0.55, 0.85, 0.45), Color(1.0, 0.8, 0.35), Color(1.0, 0.42, 0.32)]
const FOOD_COLOR := Color(0.95, 0.75, 0.6)

var world: World
var selection: Selection
var commands: CommandInput
var camera: RtsCamera
var player_id: int = 0

var _units: Array = []
var _icons: Array[Button] = []
var _icon_styles: Array[StyleBoxFlat] = []
var _icon_bars: Array[ColorRect] = []
var _notice_t: float = -1.0
## Notification line above the console (Events.notification for the local player: "under attack",
## the war-band marching...). Placeholder for juice NTF-*. Errors go to `error_line`.
var notice: Label
var error_line: ErrorLine
var tooltip: HudTooltip
var queue_panel: QueuePanel
var idle_button: IdleWorkerButton
## A site's construction progress: label and bar (selection panel).
var progress_row: HBoxContainer
var progress_label: Label
var progress_bar: ProgressBar
var _tip_since := 0.0
var _counter_box: Dictionary = {}    ## "gold" / "lumber" / "food" -> MarginContainer
var _shake_t0: Dictionary = {}       ## kind -> real time of the last shake
var _ghosts: Dictionary = {}         ## kind -> Label (the shortfall ghost)
var _ghost_t0: Dictionary = {}       ## kind -> real time the ghost dropped
var _food_capped_t := 0.0
## ECO-13 odometers: kind -> [from, to, t0, dur] (shown = from..to on QUART/OUT over dur).
var _odo: Dictionary = {}
var _odo_fx: Dictionary = {}         ## kind -> [t0, colour, length, punch scale, drop px]
## ECO-15: the shown upkeep tier and when it last flipped.
var _upkeep_shown := -1
var _upkeep_prev := 0
var _upkeep_flip_t0 := -10.0
var _upkeep_label_text := ""

@onready var gold_label: Label = %Gold
@onready var lumber_label: Label = %Lumber
@onready var food_label: Label = %Food
@onready var upkeep_label: Label = %Upkeep
@onready var clock_label: Label = %Clock
@onready var menu_button: Button = %MenuButton
@onready var minimap: Minimap = %Minimap
@onready var portrait: PanelContainer = %Portrait
@onready var portrait_label: Label = %PortraitLabel
@onready var name_label: Label = %UnitName
@onready var stats_label: Label = %UnitStats
@onready var grid: GridContainer = %SelectionGrid
@onready var card: CommandCard = %CommandCard
@onready var top_bar: Control = $Root/TopBar
@onready var console: Control = $Root/Console


func _ready() -> void:
	for i in MAX_ICONS:
		_make_icon(i)
	_show_selection([])
	notice = Label.new()
	notice.name = "Notice"
	notice.mouse_filter = Control.MOUSE_FILTER_IGNORE
	notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notice.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	notice.anchor_left = 0.0
	notice.anchor_right = 1.0
	notice.offset_top = -250.0
	notice.offset_bottom = -220.0
	notice.add_theme_font_size_override("font_size", 20)
	notice.add_theme_color_override("font_color", Color(1.0, 0.82, 0.5))
	notice.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	notice.add_theme_constant_override("shadow_offset_x", 2)
	notice.add_theme_constant_override("shadow_offset_y", 2)
	notice.visible = false
	notice.offset_top = -296.0
	notice.offset_bottom = -266.0
	$Root.add_child(notice)
	error_line = ErrorLine.new()
	error_line.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	error_line.offset_top = -262.0
	error_line.offset_bottom = -234.0
	$Root.add_child(error_line)
	var box: VBoxContainer = $Root/Console/Layout/Info/Box
	progress_row = HBoxContainer.new()
	progress_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	progress_row.add_theme_constant_override("separation", 10)
	progress_label = UiStyle.label("", 14, UiStyle.TEXT, HORIZONTAL_ALIGNMENT_LEFT)
	progress_row.add_child(progress_label)
	progress_bar = ProgressBar.new()
	progress_bar.show_percentage = false
	progress_bar.custom_minimum_size = Vector2(180, 10)
	progress_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	progress_bar.max_value = 1.0
	progress_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(0.94, 0.62, 0.22)
	var back := StyleBoxFlat.new()
	back.bg_color = Color(0, 0, 0, 0.6)
	progress_bar.add_theme_stylebox_override("fill", fill)
	progress_bar.add_theme_stylebox_override("background", back)
	progress_row.add_child(progress_bar)
	progress_row.visible = false
	box.add_child(progress_row)
	queue_panel = QueuePanel.new()
	queue_panel.name = "Queue"
	queue_panel.visible = false
	box.add_child(queue_panel)
	idle_button = IdleWorkerButton.new()
	idle_button.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	idle_button.offset_left = 8.0
	idle_button.offset_right = 8.0 + IdleWorkerButton.SIZE.x
	idle_button.offset_top = -206.0 - 8.0 - IdleWorkerButton.SIZE.y
	idle_button.offset_bottom = -206.0 - 8.0
	$Root.add_child(idle_button)
	for kind: String in ["gold", "lumber", "food"]:
		_wrap_counter(kind)
	tooltip = HudTooltip.new()
	$Root.add_child(tooltip)


func setup(w: World, sel: Selection, cmd: CommandInput, cam: RtsCamera, pid: int) -> void:
	world = w
	selection = sel
	commands = cmd
	camera = cam
	player_id = pid
	minimap.setup(w, cam, cmd)
	card.setup(cmd, sel)
	queue_panel.commands = cmd
	idle_button.setup(w, sel, cam, pid)
	menu_button.pressed.connect(_on_menu_pressed)
	Events.selection_changed.connect(_on_selection_changed)
	Events.notification.connect(_on_notification)
	cmd.denied.connect(_on_denied)
	card.entry_hovered.connect(func(b: CardButton) -> void:
		tooltip.hover(b, card_tooltip(b.entry), card.get_global_rect()))
	card.entry_unhovered.connect(func(b: CardButton) -> void: tooltip.unhover(b))
	queue_panel.slot_hovered.connect(func(b: CardButton) -> void:
		tooltip.hover(b, queue_panel.tooltip_for(b.slot), b.get_global_rect()))
	queue_panel.slot_unhovered.connect(func(b: CardButton) -> void: tooltip.unhover(b))
	idle_button.hover_changed.connect(func(b: IdleWorkerButton, on: bool) -> void:
		if on:
			tooltip.hover(b, b.tooltip_content(), b.get_global_rect())
		else:
			tooltip.unhover(b))
	_refresh_top()


func _exit_tree() -> void:
	for pair: Array in [[Events.selection_changed, _on_selection_changed], [Events.notification, _on_notification]]:
		var sig: Signal = pair[0]
		if sig.is_connected(pair[1]):
			sig.disconnect(pair[1])


## True when a screen position lies on a HUD panel (world input is blocked there).
func covers(screen_pos: Vector2) -> bool:
	return top_bar.get_global_rect().has_point(screen_pos) or console.get_global_rect().has_point(screen_pos) \
		or (idle_button != null and idle_button.get_global_rect().has_point(screen_pos))


var _notices_muted: bool = false


func _process(delta: float) -> void:
	if world == null:
		return
	_refresh_top()
	_refresh_info()
	_animate_counters()
	_tip_since += delta
	if _tip_since >= TIP_REFRESH_S:
		_tip_since = 0.0
		_refresh_tooltip()
	if _notice_t >= 0.0:
		_notice_t += delta
		notice.modulate.a = clampf((NOTICE_S - _notice_t) / NOTICE_FADE_S, 0.0, 1.0)
		if _notice_t >= NOTICE_S:
			_notice_t = -1.0
			notice.visible = false


## Shows a notification for the local player (latest wins): refusals (error_*) on the error line,
## everything else on the notice line.
func _on_notification(pid: int, kind: String, text: String) -> void:
	if pid != player_id or text.is_empty() or _notices_muted:
		return
	if kind.begins_with("error_"):
		error_line.show_error(text)
		return
	notice.text = text
	notice.visible = true
	notice.modulate.a = 1.0
	_notice_t = 0.0


## Hides the notification line at once and for the rest of the match (the end banner owns the
## screen, SEQ-02 UI exit).
func clear_notice() -> void:
	_notice_t = -1.0
	notice.visible = false
	error_line.clear()
	_notices_muted = true


# --- top bar -------------------------------------------------------------------------------

func _refresh_top() -> void:
	var p := world.player(player_id)
	if p == null:
		return
	_odometer("gold", p.gold, gold_label, "Gold  %d", Color(1, 0.86, 0.35))
	_odometer("lumber", p.lumber, lumber_label, "Lumber  %d", Color(0.62, 0.9, 0.45))
	var cap := mini(p.food_cap, int(Defs.rule("economy.food_cap", 100)))
	_set_text(food_label, "Food  %d / %d" % [p.food_used, cap])
	var capped := p.food_used >= cap
	food_label.add_theme_color_override("font_color", FOOD_CAPPED if capped else FOOD_COLOR)
	_upkeep(upkeep_tier(p.food_used), p.food_used)
	var hour := DayNight.hour_at(world.time)
	var phase := "Day" if hour >= DayNight.DAWN and hour < DayNight.DUSK else "Night"
	_set_text(clock_label, "%s  %02d:%02d" % [phase, int(hour), int(fmod(hour, 1.0) * 60.0)])


## Index of the upkeep tier at `food_used` (0 = none).
static func upkeep_tier(food_used: int) -> int:
	var t := 0
	for i in Defs.upkeep.size():
		if food_used >= int((Defs.upkeep[i] as Dictionary).get("food", 0)):
			t = i
	return t


## ECO-13: the counter rolls to the sim value (dur 150–450 ms by the size of the change); an
## unusual gain (more than 20) punches and flashes warm, a spend flashes coral and dips 4 px.
## Retargeting starts from the shown value, so a stream of deposits never flickers.
func _odometer(kind: String, value: int, label: Label, fmt: String, base: Color) -> void:
	var now := HudTooltip.now()
	var o: Array = _odo.get(kind, [float(value), float(value), now, 0.15])
	var shown := _odo_value(o, now)
	if int(o[1]) != value:
		var delta := value - int(o[1])
		o = [shown, float(value), now, clampf(0.12 + 0.006 * absf(delta), 0.15, 0.45)]
		if delta > 20:
			var st := clampf((delta - 20.0) / 180.0, 0.0, 1.0)
			_odo_fx[kind] = [now, Color("#FFF4C2"), 0.12, 1.04 + 0.12 * st, 0.0]
		elif delta < 0 and not _draining(kind):
			_odo_fx[kind] = [now, Color("#FF9A7A"), 0.16, 1.0, 4.0]
	_odo[kind] = o
	_set_text(label, fmt % roundi(_odo_value(o, now)))
	var fx: Array = _odo_fx.get(kind, [])
	var age := now - float(fx[0]) if not fx.is_empty() else 10.0
	var col := base
	var sc := 1.0
	var dip := 0
	if age < 0.25:
		col = (fx[1] as Color).lerp(base, clampf(age / float(fx[2]), 0.0, 1.0))
		sc = 1.0 + (float(fx[3]) - 1.0) * sin(PI * clampf(age / 0.18, 0.0, 1.0))
		dip = roundi(float(fx[4]) * sin(PI * clampf(age / 0.2, 0.0, 1.0)))
	label.add_theme_color_override("font_color", col)
	label.pivot_offset = label.size * 0.5
	label.scale = Vector2(sc, sc)
	var box: MarginContainer = _counter_box.get(kind)
	if box != null and box.get_theme_constant("margin_top") != dip:
		box.add_theme_constant_override("margin_top", dip)
		box.add_theme_constant_override("margin_bottom", -dip)


static func _odo_value(o: Array, now: float) -> float:
	return lerpf(float(o[0]), float(o[1]), Juice.out_quart((now - float(o[2])) / maxf(float(o[3]), 0.001)))


## Continuous drains (the Hod Chain's carriers, repairs) roll the digits without the spend flash.
func _draining(kind: String) -> bool:
	if kind != "lumber" and kind != "gold":
		return false
	for u in world.unit_list:
		if u.player_id == player_id and u.is_worker and u.current != null \
				and (u.current.type == Order.Type.REPAIR or u.current.type == Order.Type.BUILD) and u.anim_hint == "work":
			return true
	return false


## ECO-15: the upkeep label flips like a card when the tier changes (scale.x 1 → 0 in 110 ms,
## the new text and colour, 0 → 1 in 130 ms), then pulses for 3 s; a rise is announced.
func _upkeep(tier: int, food_used: int) -> void:
	var now := HudTooltip.now()
	if _upkeep_shown < 0:
		_upkeep_shown = tier
		_upkeep_label_text = upkeep_text(food_used)
	elif tier != _upkeep_shown:
		if tier > _upkeep_shown:
			Events.notification.emit(player_id, "upkeep_up", Defs.text("notice_upkeep_up") % upkeep_text(food_used))
		_upkeep_prev = _upkeep_shown
		_upkeep_shown = tier
		_upkeep_flip_t0 = now
	var age := now - _upkeep_flip_t0
	var sx := 1.0
	if age < 0.11:
		sx = 1.0 - Juice.in_quad(age / 0.11)
	elif age < 0.24:
		_upkeep_label_text = upkeep_text(food_used)
		sx = Juice.out_back((age - 0.11) / 0.13)
	else:
		_upkeep_label_text = upkeep_text(food_used)
	_set_text(upkeep_label, _upkeep_label_text)
	upkeep_label.pivot_offset = upkeep_label.size * 0.5
	upkeep_label.scale = Vector2(maxf(sx, 0.0), 1.0)
	var a := 1.0
	if age >= 0.24 and age < 3.24:
		a = 0.8 + 0.2 * cos(TAU * 1.5 * (age - 0.24))
	var col: Color = UPKEEP_COLORS[clampi(_upkeep_shown if age >= 0.11 else _upkeep_prev, 0, UPKEEP_COLORS.size() - 1)]
	upkeep_label.add_theme_color_override("font_color", Color(col, a))


static func upkeep_text(food_used: int) -> String:
	var label := ""
	for tier: Dictionary in Defs.upkeep:
		if food_used >= int(tier.get("food", 0)):
			label = Defs.text(str(tier.get("label", "")))
	return label


func _on_menu_pressed() -> void:
	Audio.ui_click()
	Events.menu_requested.emit()


## F10 lives here, not in Main: the HUD processes while the game is paused (Main does not), so
## the same key that pauses also unpauses.
func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("menu"):
		Events.menu_requested.emit()
		get_viewport().set_input_as_handled()


# --- selection panel -----------------------------------------------------------------------

func _on_selection_changed(units: Array) -> void:
	_show_selection(units)


func _show_selection(units: Array) -> void:
	_units = units.duplicate()
	grid.visible = _units.size() > 1
	stats_label.visible = _units.size() <= 1
	if _units.is_empty():
		name_label.text = ""
		stats_label.text = ""
		portrait_label.text = ""
		_set_portrait_color(Color(0.05, 0.05, 0.05, 0.9))
		_layout_icons()
		return
	var lead: Unit = _units[0]
	if selection != null and _units.size() > 1:
		var sub := selection.active_subgroup_def()
		for u: Unit in _units:
			if u.def_id == sub:
				lead = u
				break
	portrait_label.text = initials(lead.def)
	_set_portrait_color(icon_color(lead.def_id).darkened(0.35))
	name_label.text = _title(lead) if _units.size() == 1 else "%d units selected" % _units.size()
	_layout_icons()
	_refresh_info()


func _refresh_info() -> void:
	var lead: Unit = _units[0] if _units.size() == 1 and is_instance_valid(_units[0]) else null
	_refresh_building(lead)
	if _units.is_empty():
		return
	if _units.size() == 1:
		if lead != null:
			var t := unit_stats(lead)
			var extra := cargo_line(lead, world)
			if extra != "":
				t += "\n" + extra
			_set_text(stats_label, t)
		return
	for i in mini(_units.size(), MAX_ICONS):
		if is_instance_valid(_units[i]):
			var u: Unit = _units[i]
			_set_bar(i, u.hp / u.max_hp)


func _title(u: Unit) -> String:
	var t := str(u.def.get("name", u.def_id))
	if u.is_hero:
		t += "  -  Level %d hero" % u.level
	if world != null and u.player_id != player_id:
		if u.player_id == PlayerState.NEUTRAL_HOSTILE:
			t += "  (hostile)"
		elif u.player_id == PlayerState.NEUTRAL_PASSIVE:
			t += "  (neutral)"
		else:
			t += "  (player %d)" % (u.player_id + 1)
	return t


static func unit_stats(u: Unit) -> String:
	var lines: Array[String] = ["HP  %d / %d" % [ceili(u.hp), roundi(u.max_hp)]]
	if u.max_mana > 0.0:
		lines.append("Mana  %d / %d" % [floori(u.mana), roundi(u.max_mana)])
	if u.damage_max > 0:
		lines.append("Damage  %d - %d  (%s)" % [u.damage_min, u.damage_max, u.attack_type])
		lines.append("Range  %.1f m    Cooldown  %.2f s" % [u.attack_range, u.cooldown_ticks * World.DT])
	lines.append("Armor  %d  (%s)" % [roundi(u.armor), u.armor_type])
	if u.speed > 0.0:
		lines.append("Speed  %.1f m/s" % u.speed)
	return "\n".join(lines)


## A worker's load or a Gold Seam's gold ("" for others).
static func cargo_line(u: Unit, w: World) -> String:
	if u.carry_gold > 0:
		return Defs.text("info_carrying_gold") % u.carry_gold
	if u.carry_lumber > 0:
		return Defs.text("info_carrying_lumber") % u.carry_lumber
	if u.has_flag("gold_mine") and w != null and w.economy != null:
		return Defs.text("info_gold_left") % w.economy.gold_left(u)
	return ""


## The selection panel's building rows for an own single building: a site's construction
## progress, a production queue (QueuePanel).
func _refresh_building(b: Unit) -> void:
	var own := b != null and b.alive and b.player_id == player_id and b.is_building
	var site := own and b.under_construction
	progress_row.visible = site
	if site:
		_set_text(progress_label, Defs.text("site_progress") % floori(b.build_progress * 100.0))
		progress_bar.value = b.build_progress
	queue_panel.refresh(b if own and not site else null)


# --- tooltip, denial -----------------------------------------------------------------------

## Tooltip content for a card entry (HUD-02): title and hotkey, cost with shortfalls, the
## description lines and what is missing.
func card_tooltip(e: CardModel.Entry) -> Dictionary:
	if e == null:
		return {}
	var reqs: Array[String] = []
	if not e.missing.is_empty():
		reqs.append(Defs.text("tip_requires") % ", ".join(e.missing))
	elif e.state == CardModel.State.CAPPED or e.state == CardModel.State.BUSY or e.state == CardModel.State.LOCKED:
		if Defs.strings.has("error_" + e.reason):
			reqs.append(Defs.text("error_" + e.reason))
	return {"title": e.label, "key": CardModel.display_key(e), "cost": e.cost, "short": e.short,
		"lines": CardModel.describe(world, player_id, e), "requires": reqs}


## Live tooltip: re-reads the hovered card entry (costs, availability) or queue slot.
func _refresh_tooltip() -> void:
	var t := tooltip.target
	if t == null:
		return
	if t is CardButton and (t as CardButton).get_parent().get_parent() == card:
		var b := t as CardButton
		tooltip.set_content(card_tooltip(card.entry(b.slot)))
	elif t is CardButton:
		tooltip.set_content(queue_panel.tooltip_for((t as CardButton).slot))
	elif t == idle_button:
		tooltip.set_content(idle_button.tooltip_content())


## A refused press or click (CommandInput.denied): the short counters shake and their
## shortfall drops out under them (ECO-14, HUD-06); a supply refusal shakes the food counter.
func _on_denied(reason: String, short: Dictionary, _slot: int) -> void:
	var now := HudTooltip.now()
	for kind: String in short:
		_shake_t0[kind] = now
		_ghost_t0[kind] = now
		(_ghosts[kind] as Label).text = "-%d" % int(short[kind])
	if reason == "need_food":
		_shake_t0["food"] = now


## Puts a top-bar counter in a margin box so it can shake without moving its neighbours, and
## gives it a shortfall ghost label.
func _wrap_counter(kind: String) -> void:
	var l: Label = {"gold": gold_label, "lumber": lumber_label, "food": food_label}[kind]
	var row := l.get_parent()
	var at := l.get_index()
	var m := MarginContainer.new()
	m.name = "%sBox" % kind.capitalize()
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.add_theme_constant_override("margin_left", int(COUNTER_SHAKE_PX))
	m.add_theme_constant_override("margin_right", int(COUNTER_SHAKE_PX))
	row.remove_child(l)
	m.add_child(l)
	row.add_child(m)
	row.move_child(m, at)
	_counter_box[kind] = m
	var g := UiStyle.label("", 13, Color("#FF6A5A"), HORIZONTAL_ALIGNMENT_LEFT)
	g.visible = false
	g.mouse_filter = Control.MOUSE_FILTER_IGNORE
	$Root.add_child(g)
	_ghosts[kind] = g


func _animate_counters() -> void:
	var now := HudTooltip.now()
	for kind: String in _counter_box:
		var m: MarginContainer = _counter_box[kind]
		var age := now - float(_shake_t0.get(kind, -10.0))
		var dx := roundi(JuiceCurves.shake(age, COUNTER_SHAKE_PX, 0.1, COUNTER_SHAKE_S)) if age < COUNTER_SHAKE_S else 0
		var base := int(COUNTER_SHAKE_PX)
		if m.get_theme_constant("margin_left") != base + dx:
			m.add_theme_constant_override("margin_left", base + dx)
			m.add_theme_constant_override("margin_right", base - dx)
	for kind: String in _ghosts:
		var g: Label = _ghosts[kind]
		var age := now - float(_ghost_t0.get(kind, -10.0))
		var life := GHOST_DROP_S + GHOST_HOLD_S + GHOST_FADE_S
		g.visible = age < life
		if not g.visible:
			continue
		var r := (_counter_box[kind] as Control).get_global_rect()
		var drop := 14.0 * Juice.out_quad(clampf(age / GHOST_DROP_S, 0.0, 1.0))
		g.global_position = Vector2(r.position.x + float(COUNTER_SHAKE_PX), r.end.y - 4.0 + drop)
		var fade := (age - GHOST_DROP_S - GHOST_HOLD_S) / GHOST_FADE_S
		g.modulate.a = 1.0 - clampf(fade, 0.0, 1.0)


static func initials(d: Dictionary) -> String:
	var words := str(d.get("name", "?")).split(" ", false)
	return words[words.size() - 1].substr(0, 2) if not words.is_empty() else "?"


## Placeholder icon colour per unit type: the def's `icon_color` if set, otherwise a hue
## spread by golden ratio over the sorted def ids (stable, and neighbours never look alike).
static func icon_color(def_id: String) -> Color:
	var d := Defs.unit(def_id)
	if d.has("icon_color"):
		return Color(str(d["icon_color"]))
	var ids: Array = Defs.unit_ids()
	ids.sort()
	return Color.from_hsv(fposmod(ids.find(def_id) * 0.618034 + 0.08, 1.0), 0.5, 0.62)


# --- icons ---------------------------------------------------------------------------------

func _make_icon(i: int) -> void:
	var b := Button.new()
	b.name = "Icon%d" % i
	b.custom_minimum_size = ICON_SIZE
	b.focus_mode = Control.FOCUS_NONE
	b.action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS   # like the card: acts on the press
	b.add_theme_font_size_override("font_size", 15)
	var sb := StyleBoxFlat.new()
	sb.border_color = Color(0, 0, 0, 0.8)
	sb.set_border_width_all(1)
	for state in ["normal", "hover", "pressed"]:
		b.add_theme_stylebox_override(state, sb)
	var bar := ColorRect.new()
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.anchor_top = 1.0
	bar.anchor_bottom = 1.0
	bar.offset_top = -5.0
	bar.offset_left = 2.0
	bar.offset_bottom = -2.0
	b.add_child(bar)
	b.pressed.connect(_on_icon_pressed.bind(i))
	grid.add_child(b)
	_icons.append(b)
	_icon_styles.append(sb)
	_icon_bars.append(bar)


func _layout_icons() -> void:
	for i in MAX_ICONS:
		var b := _icons[i]
		b.visible = i < _units.size() and _units.size() > 1 and is_instance_valid(_units[i])
		if not b.visible:
			continue
		var u: Unit = _units[i]
		b.text = initials(u.def)
		_icon_styles[i].bg_color = icon_color(u.def_id)
		_set_bar(i, u.hp / u.max_hp)


func _set_bar(i: int, ratio: float) -> void:
	var bar := _icon_bars[i]
	bar.anchor_right = clampf(ratio, 0.0, 1.0)
	bar.offset_right = -2.0 if ratio >= 1.0 else 0.0
	bar.color = HP_LOW.lerp(HP_GOOD, ratio)


func _on_icon_pressed(i: int) -> void:
	if selection == null or i >= _units.size() or not is_instance_valid(_units[i]):
		return
	var u: Unit = _units[i]
	if Input.is_key_pressed(KEY_SHIFT):
		var rest := _units.filter(func(o: Variant) -> bool: return o != u and is_instance_valid(o))
		selection.select_units(rest)
	else:
		selection.select_units([u])


func _set_portrait_color(c: Color) -> void:
	var sb := portrait.get_theme_stylebox("panel") as StyleBoxFlat
	if sb != null:
		sb.bg_color = c


func _set_text(l: Label, t: String) -> void:
	if l.text != t:
		l.text = t
