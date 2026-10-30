class_name HeroBar
extends VBoxContainer
## The hero bar (rules §6.5; juice HER-03, HER-04, HER-05, HER-06 P0 HUD parts): the local
## player's heroes in acquisition order (the F1–F3 order), top left under the top bar. Each
## button shows the hero's initials until portrait art exists (art bible §11), a level badge, HP
## and mana bars and the XP bar, which pours toward the real value; a "+N" pip while skill points
## are unspent (it pops when one arrives); the button flips on a level-up and lands with the new
## number. A dead hero is greyed out and shows its revive timer once queued. Click selects (F1–F3
## behaviour: again within the double-click time centres the camera). Reads sim state only;
## animation runs on real time, UI only.

signal hover_changed(button: Control, on: bool)

const MAX := 3
const FACE := Vector2(60, 60)
const XP_K := 6.0              ## XP pour: exponential approach rate (1/s), exact for any frame time
const FLIP_S := 0.3            ## level-up flip (HER-04 portrait flip, within the 350 ms ceremony)
const PIP_S := 0.25            ## "+N" pip pop (HER-05)
const HP_GOOD := Color(0.25, 0.85, 0.3)
const HP_LOW := Color(0.95, 0.25, 0.2)
const MANA := Color(0.3, 0.55, 1.0)
const XP := Color(1.0, 0.8, 0.35)
const PIP := Color(1.0, 0.84, 0.36)

var world: World
var selection: Selection
var player_id: int = 0
var slots: Array[Slot] = []


## One hero button.
class Slot:
	extends Button
	var index: int = 0
	var hero_id: int = 0             ## the id kept in PlayerState.heroes (dead or alive)
	var alive: bool = true
	var label_text: String = ""
	var face: Color = Color(0.3, 0.25, 0.2)
	var level: int = 1
	var points: int = 0
	var hp: float = 1.0
	var mana: float = -1.0           ## ratio; < 0 = no mana
	var xp: float = 0.0              ## shown XP ratio within the level (pours toward xp_target)
	var xp_target: float = 0.0
	var revive_left: float = -1.0    ## seconds; < 0 = not queued
	var selected: bool = false
	var flip_t0: float = -10.0
	var pip_t0: float = -10.0

	func _init(i: int) -> void:
		index = i
		name = "Hero%d" % (i + 1)
		custom_minimum_size = Vector2(HeroBar.FACE.x, HeroBar.FACE.y + 18.0)
		focus_mode = Control.FOCUS_NONE
		flat = true
		for st in ["normal", "hover", "pressed", "disabled", "focus"]:
			add_theme_stylebox_override(st, StyleBoxEmpty.new())

	func _draw() -> void:
		var f := HeroBar.FACE
		var fr := Rect2(Vector2.ZERO, f)
		var base := face if alive else Color(0.2, 0.2, 0.2)
		draw_rect(fr.grow(2.0), Color(1.0, 0.86, 0.5) if selected else Color(0.56, 0.46, 0.3))
		draw_rect(fr, base.darkened(0.35))
		draw_rect(Rect2(Vector2(3, 3), f - Vector2(6, 6)), base.darkened(0.1))
		var font := get_theme_default_font()
		var tw := font.get_string_size(label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x
		draw_string(font, Vector2((f.x - tw) * 0.5, f.y * 0.5 + 9.0), label_text, HORIZONTAL_ALIGNMENT_LEFT,
			-1, 24, Color(0.95, 0.9, 0.78) if alive else Color(0.6, 0.6, 0.6))
		var lv := str(level)
		var lw := font.get_string_size(lv, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
		draw_rect(Rect2(Vector2(0, f.y - 17), Vector2(lw + 8, 17)), Color(0.05, 0.04, 0.03, 0.92))
		draw_string(font, Vector2(4, f.y - 4), lv, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1.0, 0.9, 0.62))
		if not alive:
			var t := Defs.text("hero_dead") if revive_left < 0.0 else "%d:%02d" % [ceili(revive_left) / 60, ceili(revive_left) % 60]
			var dw := font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
			draw_rect(Rect2(Vector2((f.x - dw) * 0.5 - 4, 4), Vector2(dw + 8, 18)), Color(0, 0, 0, 0.75))
			draw_string(font, Vector2((f.x - dw) * 0.5, 18), t, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.95, 0.9, 0.78))
		elif points > 0:
			var age := HeroBar.now() - pip_t0
			var pop := 1.0 + (0.35 * sin(PI * age / HeroBar.PIP_S) if age < HeroBar.PIP_S else 0.0)
			var c := Vector2(f.x - 9, 9)
			draw_circle(c, 11.0 * pop, Color(0.1, 0.07, 0.03))
			draw_circle(c, 9.5 * pop, HeroBar.PIP)
			var pt := "+%d" % points
			var pw := font.get_string_size(pt, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
			draw_string(font, c + Vector2(-pw * 0.5, 5), pt, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.15, 0.1, 0.03))
		var y := f.y + 4.0
		_bar(y, 6.0, hp if alive else 0.0, HeroBar.HP_LOW.lerp(HeroBar.HP_GOOD, clampf(hp, 0.0, 1.0)))
		y += 8.0
		if mana >= 0.0:
			_bar(y, 4.0, mana if alive else 0.0, HeroBar.MANA)
		y += 6.0
		_bar(y, 3.0, xp, HeroBar.XP)

	func _bar(y: float, h: float, ratio: float, c: Color) -> void:
		var w := HeroBar.FACE.x
		draw_rect(Rect2(0, y, w, h), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(0, y, w * clampf(ratio, 0.0, 1.0), h), c)


func _init() -> void:
	name = "HeroBar"
	add_theme_constant_override("separation", 8)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in MAX:
		var s := Slot.new(i)
		s.visible = false
		s.pressed.connect(_on_pressed.bind(i))
		s.mouse_entered.connect(func() -> void: hover_changed.emit(s, true))
		s.mouse_exited.connect(func() -> void: hover_changed.emit(s, false))
		add_child(s)
		slots.append(s)


func setup(w: World, sel: Selection, pid: int) -> void:
	world = w
	selection = sel
	player_id = pid
	Events.hero_level_up.connect(_on_level_up)
	Events.ability_learned.connect(func(_h: Node, _a: String, _r: int) -> void: _refresh(0.0))
	_refresh(0.0)


func _exit_tree() -> void:
	if Events.hero_level_up.is_connected(_on_level_up):
		Events.hero_level_up.disconnect(_on_level_up)


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


func _on_level_up(u: Node) -> void:
	for s in slots:
		if s.visible and s.hero_id == (u as Unit).id:
			s.flip_t0 = now()
			s.xp = 0.0


func _process(delta: float) -> void:
	_refresh(delta)


func _refresh(delta: float) -> void:
	if world == null:
		return
	var p := world.player(player_id)
	var ids: Array = p.heroes if p != null else []
	var t := now()
	for i in MAX:
		var s := slots[i]
		s.visible = i < ids.size()
		if not s.visible:
			continue
		var hid := int(ids[i])
		var u := world.get_unit(hid)
		var hero: Dictionary = u.hero if u != null and u.alive else world.heroes.dead_record(hid).get("hero", {})
		s.hero_id = hid
		s.alive = u != null and u.alive
		var def_id := u.def_id if u != null else str(world.heroes.dead_record(hid).get("def_id", ""))
		s.label_text = Hud.initials(Defs.unit(def_id))
		s.face = Hud.icon_color(def_id)
		var lv := int(hero.get("level", 1))
		var age := t - s.flip_t0
		if age >= FLIP_S * 0.5 or age < 0.0:
			s.level = lv                # the number lands at the flip's midpoint
		var pts := int(hero.get("skill_points", 0))
		if pts > s.points:
			s.pip_t0 = t
		s.points = pts
		s.hp = u.hp / maxf(u.max_hp, 1.0) if s.alive else 0.0
		s.mana = u.mana / u.max_mana if s.alive and u.max_mana > 0.0 else (0.0 if not s.alive else -1.0)
		s.xp_target = HeroSystem.xp_ratio(hero)
		s.xp += (s.xp_target - s.xp) * (1.0 - exp(-XP_K * delta)) if delta > 0.0 else s.xp_target - s.xp
		s.revive_left = world.production.revive_left(hid) if not s.alive else -1.0
		s.selected = s.alive and selection != null and selection.selected.has(u)
		s.pivot_offset = Vector2(FACE.x * 0.5, FACE.y * 0.5)
		s.scale = Vector2(absf(cos(PI * age / FLIP_S)) if age < FLIP_S and age >= 0.0 else 1.0, 1.0)
		s.queue_redraw()


## Tooltip content for slot `i`: "Title: Name", level and XP, unspent points, or the revive state.
func tooltip_for(i: int) -> Dictionary:
	if world == null or i < 0 or i >= MAX or not slots[i].visible:
		return {}
	var hid := slots[i].hero_id
	var u := world.get_unit(hid)
	var lines: Array[String] = []
	var title := ""
	if u != null and u.alive:
		title = HeroSystem.display_name(u)
		var lv := int(u.hero.get("level", 1))
		if lv >= int(Defs.rule("heroes.level_cap", 10)):
			lines.append(Defs.text("hero_level_max") % lv)
		else:
			lines.append(Defs.text("hero_level_xp") % [lv, floori(float(u.hero.get("xp", 0.0))), roundi(Defs.xp_for_level(lv + 1))])
		var pts := int(u.hero.get("skill_points", 0))
		if pts > 0:
			lines.append(Defs.text("hero_points") % pts)
	else:
		var rec := world.heroes.dead_record(hid)
		var hero: Dictionary = rec.get("hero", {})
		title = HeroSystem.title_and_name(hero)
		lines.append(Defs.text("hero_fallen") % int(hero.get("level", 1)))
		var left := world.production.revive_left(hid)
		lines.append(Defs.text("hero_reviving") % [ceili(left) / 60, ceili(left) % 60] if left >= 0.0 else Defs.text("hero_revive_hint"))
	return {"title": title, "key": "F%d" % (i + 1), "lines": lines}


func _on_pressed(i: int) -> void:
	if selection != null and selection.select_hero(i):
		Audio.ui_click()
	else:
		Audio.deny("disabled")
