class_name PopupText
extends CanvasLayer
## The only in-world text system (juice bible §4.5, Appendix A R2; no Label3D anywhere).
## Pooled 2D labels on a CanvasLayer under the HUD, placed each frame at the projected anchor
## (a unit's interpolated bar top, or a world point), so text is pixel-exact and keeps a fixed
## screen size at any zoom (heights are px at 1080p, scaled with the viewport). What to show is
## decided by the policy (`CombatText`, *Minimal* by default); this decides how:
##   - styles: crit "N!" (pop 0 -> 1.45 -> 1.0, held, gone by 1 s), heal, gold / lumber with an
##     icon (deposit look: pop 0.55 -> 1.12 -> 1.0, rise 40 px, fade from 60 % of the life),
##     miss, mana;
##   - merge: the same key inside the window adds into the live label (value += n, a 1.12 bump
##     over 60 ms, life extended to at least 0.5 s);
##   - lanes: a second popup on the same anchor within 300 ms starts 22 px higher;
##   - pool: `FeelConstants.popup_cap` labels built once; when all are busy the oldest is reused.
## Motion is closed form on the fx clock (RISE_FADE), so it is the same at any refresh rate.

enum Style { CRIT, HEAL, GOLD, LUMBER, MISS, MANA, NORMAL, FOOD, LEVEL }

const STYLES: Dictionary = {
	Style.CRIT: {"px": 30, "fill": "#FF4433", "outline": "#2A0A04", "life": 1.0, "rise": 18.0, "suffix": "!"},
	Style.HEAL: {"px": 18, "fill": "#7CFF8A", "outline": "#0E2A12", "life": 1.0, "rise": 40.0, "prefix": "+"},
	Style.GOLD: {"px": 20, "fill": "#FFD34D", "outline": "#4A2E00", "life": 1.0, "rise": 40.0, "prefix": "+", "icon": "coin"},
	Style.LUMBER: {"px": 18, "fill": "#8EDB6A", "outline": "#1E3A12", "life": 1.0, "rise": 40.0, "prefix": "+"},
	Style.MISS: {"px": 16, "fill": "#D8D2C8", "outline": "#1A1712", "life": 0.8, "rise": 24.0},
	Style.MANA: {"px": 16, "fill": "#4FA8FF", "outline": "#0A1A33", "life": 1.0, "rise": 40.0, "prefix": "+"},
	Style.FOOD: {"px": 20, "fill": "#FFC98A", "outline": "#3A2108", "life": 1.2, "rise": 40.0, "prefix": "+"},
	Style.NORMAL: {"px": 16, "fill": "#F2EEE6", "outline": "#120A04", "life": 0.9, "rise": 36.0},
	Style.LEVEL: {"px": 34, "fill": "#FFE9A8", "outline": "#3A2108", "life": 1.1, "rise": 26.0},
}
const LANE_PX := 22.0
const LANE_WINDOW := 0.3
const ANCHOR_PX := 10.0

var camera: Camera3D
var world: World
var spawned: int = 0
var merged: int = 0

var _items: Array[Item] = []
var _font: Font


class Item:
	var root: HBoxContainer
	var label: Label
	var icon: TextureRect
	var settings: LabelSettings
	var style: int = 0
	var t0: float = -1000.0
	var life: float = 0.0
	var bump_t0: float = -1000.0
	var anchor: Unit = null
	var pos: Vector3 = Vector3.ZERO
	var value: int = 0
	var key: int = -1
	var lane: int = 0
	var text_override: String = ""

	func alive(now: float) -> bool:
		return now - t0 < life


func _ready() -> void:
	layer = 1
	var base: Font = ThemeDB.fallback_font
	var fv := FontVariation.new()
	fv.base_font = base
	fv.variation_embolden = 0.9
	_font = fv
	for i in FeelConstants.c().popup_cap:
		_items.append(_make_item())


func setup(w: World, cam: Camera3D = null) -> void:
	world = w
	camera = cam


func _make_item() -> Item:
	var it := Item.new()
	it.root = HBoxContainer.new()
	it.root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	it.root.add_theme_constant_override("separation", 3)
	it.root.visible = false
	it.root.alignment = BoxContainer.ALIGNMENT_CENTER
	it.icon = TextureRect.new()
	it.icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	it.icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	it.icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	it.icon.visible = false
	it.label = Label.new()
	it.label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	it.settings = LabelSettings.new()
	it.settings.font = _font
	it.label.label_settings = it.settings
	it.root.add_child(it.icon)
	it.root.add_child(it.label)
	add_child(it.root)
	return it


## Shows (or merges into) a popup. `key` >= 0 merges with a live popup of the same key inside
## `merge_window` seconds. Returns the item (tests read its value).
func show_value(style: int, value: int, pos: Vector3, anchor: Unit = null, key: int = -1,
		merge_window: float = 0.25, text_override: String = "") -> Item:
	var now := FxClock.fx_now
	if key >= 0:
		for it in _items:
			if it.key == key and it.style == style and it.alive(now) and now - it.t0 <= merge_window + it.life:
				if now - it.t0 <= merge_window or now - it.bump_t0 <= merge_window:
					it.value += value
					it.bump_t0 = now
					it.life = maxf(it.life, now - it.t0 + 0.5)
					_set_text(it)
					merged += 1
					return it
	var it := _take(now)
	var spec: Dictionary = STYLES.get(style, STYLES[Style.NORMAL])
	it.style = style
	it.t0 = now
	it.bump_t0 = -1000.0
	it.life = float(spec["life"])
	it.anchor = anchor
	it.pos = pos
	it.value = value
	it.key = key
	it.text_override = text_override
	it.lane = 0
	if anchor != null:
		for o in _items:
			if o != it and o.anchor == anchor and o.alive(now) and now - o.t0 < LANE_WINDOW:
				it.lane = (o.lane + 1) % 2
	var px := _px(float(spec["px"]))
	it.settings.font_size = int(px)
	it.settings.font_color = Color(str(spec["fill"]))
	it.settings.outline_color = Color(str(spec["outline"]))
	it.settings.outline_size = maxi(4, int(px * 0.3))
	it.settings.shadow_color = Color(0, 0, 0, 0.35)
	it.settings.shadow_offset = Vector2(0, maxf(1.0, px * 0.06))
	it.settings.shadow_size = 0
	var has_icon := str(spec.get("icon", "")) == "coin"
	it.icon.visible = has_icon
	if has_icon:
		it.icon.texture = FxTextures.coin_icon()
		it.icon.custom_minimum_size = Vector2(px * 0.9, px * 0.9)
	_set_text(it)
	it.root.visible = false
	spawned += 1
	return it


func live_count() -> int:
	var now := FxClock.fx_now
	var n := 0
	for it in _items:
		if it.alive(now):
			n += 1
	return n


func capacity() -> int:
	return _items.size()


func _take(now: float) -> Item:
	var oldest: Item = _items[0]
	for it in _items:
		if not it.alive(now):
			return it
		if it.t0 < oldest.t0:
			oldest = it
	return oldest


func _set_text(it: Item) -> void:
	var spec: Dictionary = STYLES.get(it.style, STYLES[Style.NORMAL])
	if not it.text_override.is_empty():
		it.label.text = it.text_override
	else:
		it.label.text = "%s%d%s" % [spec.get("prefix", ""), it.value, spec.get("suffix", "")]
	it.root.reset_size()


func _px(px_1080: float) -> float:
	return maxf(px_1080 * _vs(), FeelConstants.c().text_min_px)


## Viewport height / 1080 (sizes and offsets are specified at 1080p).
func _vs() -> float:
	if is_inside_tree():
		return get_viewport().get_visible_rect().size.y / 1080.0
	return 1.0


## Closed-form look of a popup at `age`: (scale, alpha, rise px).
static func look(style: int, age: float, life: float, bump_age: float) -> Vector3:
	var spec: Dictionary = STYLES.get(style, STYLES[Style.NORMAL])
	var s := 1.0
	var a := 1.0
	if style == Style.CRIT:
		s = JuiceCurves.crit_pop(age)
		a = 1.0 - Juice.window(age, life * 0.7, life * 0.3)
	else:
		if age < 0.09:
			s = lerpf(0.55, 1.12, Juice.out_quad(age / 0.09))
		else:
			s = lerpf(1.12, 1.0, Juice.in_out_sine((age - 0.09) / 0.11))
		a = JuiceCurves.rise_fade(age, life, 0.4).y
	s *= JuiceCurves.punch(bump_age, 0.12, 0.06)
	var rise := float(spec["rise"]) * Juice.out_cubic(clampf(age / maxf(life, 0.01), 0.0, 1.0))
	return Vector3(s, a, rise)


func _process(_delta: float) -> void:
	var cam := camera if camera != null and is_instance_valid(camera) else get_viewport().get_camera_3d()
	var now := FxClock.fx_now
	var vs := _vs()
	for it in _items:
		if not it.alive(now):
			if it.root.visible:
				it.root.visible = false
				it.anchor = null
			continue
		if cam == null:
			it.root.visible = false
			continue
		var p := it.pos
		if it.anchor != null and is_instance_valid(it.anchor):
			var u := it.anchor
			p = u.display_pos() + Vector3(0.0, u.top_height() + 0.75, 0.0)
		if cam.is_position_behind(p):
			it.root.visible = false
			continue
		var lk := look(it.style, now - it.t0, it.life, now - it.bump_t0)
		var sp := cam.unproject_position(p)
		var size := it.root.get_combined_minimum_size()
		it.root.size = size
		it.root.pivot_offset = size * 0.5
		it.root.position = sp - Vector2(size.x * 0.5, size.y) \
			- Vector2(0.0, (ANCHOR_PX + lk.z + it.lane * LANE_PX) * vs)
		it.root.scale = Vector2.ONE * lk.x
		it.root.modulate = Color(1, 1, 1, lk.y)
		it.root.visible = lk.y > 0.01 and lk.x > 0.01
