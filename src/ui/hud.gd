class_name Hud
extends CanvasLayer
## Stub HUD (docs/architecture.md §11). Top bar bound to the local PlayerState (gold, lumber,
## food, upkeep, day clock, menu). Bottom console: minimap, portrait, selected-unit stats or a
## multi-selection icon grid, and the 4x3 command card. The bar and console stop mouse events,
## so clicks on the HUD never reach world selection or commands. Reads sim state, never writes it.

const MAX_ICONS := 24
const ICON_SIZE := Vector2(46, 46)
const HP_GOOD := Color(0.25, 0.85, 0.3)
const HP_LOW := Color(0.95, 0.25, 0.2)

var world: World
var selection: Selection
var commands: CommandInput
var camera: RtsCamera
var player_id: int = 0

var _units: Array = []
var _icons: Array[Button] = []
var _icon_styles: Array[StyleBoxFlat] = []
var _icon_bars: Array[ColorRect] = []

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


func setup(w: World, sel: Selection, cmd: CommandInput, cam: RtsCamera, pid: int) -> void:
	world = w
	selection = sel
	commands = cmd
	camera = cam
	player_id = pid
	minimap.setup(w, cam, cmd)
	card.setup(cmd, sel)
	menu_button.pressed.connect(_on_menu_pressed)
	Events.selection_changed.connect(_on_selection_changed)
	_refresh_top()


## True when a screen position lies on a HUD panel (world input is blocked there).
func covers(screen_pos: Vector2) -> bool:
	return top_bar.get_global_rect().has_point(screen_pos) or console.get_global_rect().has_point(screen_pos)


func _process(_delta: float) -> void:
	if world == null:
		return
	_refresh_top()
	_refresh_info()


# --- top bar -------------------------------------------------------------------------------

func _refresh_top() -> void:
	var p := world.player(player_id)
	if p == null:
		return
	_set_text(gold_label, "Gold  %d" % p.gold)
	_set_text(lumber_label, "Lumber  %d" % p.lumber)
	var cap := mini(p.food_cap, int(Defs.combat_default("food_max", 100)))
	_set_text(food_label, "Food  %d / %d" % [p.food_used, cap])
	_set_text(upkeep_label, upkeep_text(p.food_used))
	var hour := DayNight.hour_at(world.time)
	var phase := "Day" if hour >= DayNight.DAWN and hour < DayNight.DUSK else "Night"
	_set_text(clock_label, "%s  %02d:%02d" % [phase, int(hour), int(fmod(hour, 1.0) * 60.0)])


static func upkeep_text(food_used: int) -> String:
	var label := ""
	for tier: Dictionary in Defs.upkeep:
		if food_used >= int(tier.get("food", 0)):
			label = str(tier.get("label", ""))
	return label


func _on_menu_pressed() -> void:
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
	if _units.is_empty():
		return
	if _units.size() == 1:
		if is_instance_valid(_units[0]):
			_set_text(stats_label, unit_stats(_units[0] as Unit))
		return
	for i in mini(_units.size(), MAX_ICONS):
		if is_instance_valid(_units[i]):
			var u: Unit = _units[i]
			_set_bar(i, u.hp / u.max_hp)


func _title(u: Unit) -> String:
	var t := str(u.def.get("name", u.def_id))
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
