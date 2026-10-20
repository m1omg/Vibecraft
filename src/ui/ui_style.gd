class_name UiStyle
extends RefCounted
## Shared look for the menus built in code (main menu, pause menu, end banner): the HUD's walnut
## panels with a brass rim and warm ivory text (placeholder until the faction skins, juice
## HUD-01 / HUD-11). Visual only.

const PANEL_BG := Color(0.09, 0.08, 0.07, 0.96)
const PANEL_RIM := Color(0.56, 0.46, 0.3, 1.0)
const BUTTON_BG := Color(0.17, 0.14, 0.105, 1.0)
const BUTTON_HOVER := Color(0.27, 0.21, 0.14, 1.0)
const BUTTON_PRESSED := Color(0.11, 0.09, 0.07, 1.0)
const TEXT := Color(0.95, 0.9, 0.78, 1.0)
const TEXT_GOLD := Color(1.0, 0.86, 0.5, 1.0)
const TEXT_DIM := Color(0.72, 0.66, 0.55, 1.0)
const VICTORY := Color(0.48, 0.12, 0.18, 0.96)     ## kingdom burgundy band
const DEFEAT := Color(0.24, 0.25, 0.27, 0.96)      ## slate band


static func panel_box(bg: Color = PANEL_BG, rim: Color = PANEL_RIM, rim_px: int = 2) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = rim
	sb.set_border_width_all(rim_px)
	sb.set_corner_radius_all(4)
	sb.set_content_margin_all(18)
	sb.shadow_color = Color(0, 0, 0, 0.55)
	sb.shadow_size = 10
	return sb


static func button(text: String, font_size: int = 20, min_width: float = 300.0) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(min_width, font_size * 2.3)
	b.add_theme_font_size_override("font_size", font_size)
	b.pressed.connect(func() -> void: Audio.ui_click())   # UI click in the local faction's material
	for state: String in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(state, TEXT if state == "font_color" else TEXT_GOLD)
	b.add_theme_color_override("font_disabled_color", TEXT_DIM.darkened(0.3))
	var styles := {"normal": BUTTON_BG, "hover": BUTTON_HOVER, "pressed": BUTTON_PRESSED,
		"disabled": BUTTON_BG.darkened(0.3), "focus": BUTTON_HOVER}
	for state: String in styles:
		var sb := panel_box(styles[state], PANEL_RIM if state != "hover" else TEXT_GOLD, 1)
		sb.set_content_margin_all(8)
		sb.shadow_size = 0
		if state == "focus":
			sb.draw_center = false
		b.add_theme_stylebox_override(state, sb)
	return b


static func label(text: String, font_size: int, color: Color = TEXT, align := HORIZONTAL_ALIGNMENT_CENTER) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	return l


## Full-screen dimmer that eats mouse input (modal backdrop).
static func dimmer(alpha: float = 0.55) -> ColorRect:
	var c := ColorRect.new()
	c.color = Color(0.02, 0.02, 0.03, alpha)
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_STOP
	return c


## A centred vertical box inside a rimmed panel.
static func centred_panel(parent: Control, separation: int = 12) -> VBoxContainer:
	var centre := CenterContainer.new()
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	centre.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(centre)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", panel_box())
	centre.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", separation)
	panel.add_child(box)
	return box
