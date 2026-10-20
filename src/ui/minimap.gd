class_name Minimap
extends Control
## The minimap (rules §14.1, §18.1; visual only). Layers, bottom to top:
##   - the map: a CPU-baked image, 1 px per metre (ground colour by Greenvale ladder slot, lighter
##     per cliff level, water, ramps, trees), baked once per map;
##   - the local player's fog (rules §14.1): black mask where unexplored, half dark where fogged
##     (a shader over Fog.texture; absent while fog is off);
##   - static neutral markers, drawn even on the black mask (rules.minimap
##     .show_unexplored_neutrals): Gold Seams, neutral buildings and creep-camp pips in the camp's
##     colour until the player has seen the camp cleared;
##   - dots: units in player colours (enemies only while seen; structures as remembered) and
##     the camera's view box.
## Left click/drag jumps the camera; right click issues a smart command at that ground point.
## With an order armed (A / M / P), a left click issues that order at the map point instead
## (Shift queues it and keeps the order armed) and a right click cancels it (rules §18.1).

const BACKDROP := Color(0.13, 0.19, 0.12)
const BORDER := Color(0.55, 0.50, 0.38)
const VIEW_BOX := Color(1, 1, 1, 0.8)
## Average colours of the Greenvale ladder textures (gv_scree .. gv_thick_meadow).
const LADDER_COLOURS: Array[Color] = [Color("#6A674F"), Color("#B98349"), Color("#7B542B"),
	Color("#976F3A"), Color("#69582E"), Color("#72872A"), Color("#476527")]
const LEGACY_TO_LADDER: Array[int] = [5, 6, 2, 1, 0, 4, 4, 3]
const WATER := Color("#2E5A6E")
const TREE := Color("#22401C")
const MINE := Color(0.98, 0.82, 0.25)
const NEUTRAL := Color(0.86, 0.84, 0.78)
const CAMP_COLOURS := {"green": Color("#4CC24C"), "orange": Color("#F0A030"), "red": Color("#E04030")}
const FOG_SHADER := """
shader_type canvas_item;
uniform sampler2D fog_tex : filter_linear;
void fragment() {
	float f = texture(fog_tex, UV).r;
	// 0 unexplored -> black mask, 0.5 fogged -> half dark, 1 visible -> clear
	COLOR = vec4(0.0, 0.0, 0.0, f < 0.5 ? mix(1.0, 0.55, f * 2.0) : mix(0.55, 0.0, (f - 0.5) * 2.0));
}
"""

var world: World
var camera: RtsCamera
var commands: CommandInput
var base: ImageTexture
var fog_layer: TextureRect
var dots: Control
var _dragging: bool = false


func setup(w: World, cam: RtsCamera, cmd: CommandInput) -> void:
	world = w
	camera = cam
	commands = cmd
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = true
	if w != null and w.map != null:
		base = ImageTexture.create_from_image(bake_map(w))
	if fog_layer == null:
		fog_layer = TextureRect.new()
		fog_layer.name = "Fog"
		fog_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
		fog_layer.stretch_mode = TextureRect.STRETCH_SCALE
		fog_layer.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		fog_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var m := ShaderMaterial.new()
		m.shader = Shader.new()
		m.shader.code = FOG_SHADER
		fog_layer.material = m
		fog_layer.visible = false
		add_child(fog_layer)
		dots = Control.new()
		dots.name = "Dots"
		dots.set_anchors_preset(Control.PRESET_FULL_RECT)
		dots.mouse_filter = Control.MOUSE_FILTER_IGNORE
		dots.draw.connect(_draw_dots)
		add_child(dots)
	refresh_fog()


## Points the fog layer at the world's fog texture (call after fog is turned on).
func refresh_fog() -> void:
	if fog_layer == null or world == null or world.fog == null:
		return
	var tex := world.fog.texture(world.local_player_id)
	fog_layer.visible = tex != null
	if tex != null:
		fog_layer.texture = tex
		(fog_layer.material as ShaderMaterial).set_shader_parameter("fog_tex", tex)


## The map image, 1 px per metre: ground colour by ladder slot (lighter per cliff level), ramps,
## water, trees.
static func bake_map(w: World) -> Image:
	var m := w.map
	var sw := m.size_world()
	var img := Image.create(int(sw.x), int(sw.y), false, Image.FORMAT_RGB8)
	var ladder := LEGACY_TO_LADDER
	var ts: Variant = m.get("tex_set")
	if ts != null and str(ts) == "gv_ladder":
		ladder = [0, 1, 2, 3, 4, 5, 6, 6]
	for y in img.get_height():
		for x in img.get_width():
			var tx := floori(x / Grid.TILE)
			var ty := floori(y / Grid.TILE)
			var i := m.idx(tx, ty)
			var c: Color
			if m.water[i] == 1:
				c = WATER
			else:
				c = LADDER_COLOURS[ladder[clampi(m.tex[i], 0, 7)]]
				var lvl := m.height_at(x + 0.5, y + 0.5) / Grid.CLIFF_H
				c = c.lightened(clampf(lvl * 0.09, 0.0, 0.3)) if lvl > 0.0 else c.darkened(clampf(-lvl * 0.2, 0.0, 0.3))
			img.set_pixel(x, y, c)
	for i in w.doodads.trees.size():
		if w.doodads.alive[i] == 1:
			var g: Vector2i = w.doodads.trees[i]
			if g.x >= 0 and g.y >= 0 and g.x < img.get_width() and g.y < img.get_height():
				img.set_pixel(g.x, g.y, TREE)
	return img


func _process(_delta: float) -> void:
	if world != null and is_visible_in_tree():
		queue_redraw()
		if dots != null:
			dots.queue_redraw()


func _scale() -> Vector2:
	var s := world.map.size_world()
	return Vector2(size.x / s.x, size.y / s.y)


func _draw() -> void:
	if base != null:
		draw_texture_rect(base, Rect2(Vector2.ZERO, size), false)
	else:
		draw_rect(Rect2(Vector2.ZERO, size), BACKDROP)


func _draw_dots() -> void:
	if world == null:
		return
	var k := _scale()
	var pid := world.local_player_id
	var fog := world.fog if world.fog != null and world.fog.enabled else null
	# static neutral markers (shown on the black mask too)
	if world.creeps != null:
		var camps: Dictionary = world.creeps.camps()
		for cid: String in camps:
			var st: Dictionary = world.creeps.camp_state(cid)
			var p3: Vector3 = st.get("pos", Vector3.ZERO)
			if bool(st.get("cleared", false)) and (fog == null or fog.is_visible(pid, p3)):
				continue
			var col: Color = CAMP_COLOURS.get(str(st.get("colour", "")), Color(0.9, 0.9, 0.9))
			dots.draw_circle(Vector2(p3.x, p3.z) * k, 2.6, Color(0, 0, 0, 0.8))
			dots.draw_circle(Vector2(p3.x, p3.z) * k, 1.8, col)
	for u in world.unit_list:
		if not u.alive or u.hidden:
			continue
		var neutral_marker := u.is_resource or (u.player_id == PlayerState.NEUTRAL_PASSIVE and u.footprint.size != Vector2i.ZERO)
		if fog != null and not neutral_marker and not fog.shows(pid, u):
			continue
		if u.player_id == PlayerState.NEUTRAL_HOSTILE:
			continue   # creeps show as their camp's pip
		var r := 1.5
		if u.footprint.size != Vector2i.ZERO:
			r = maxf(u.footprint.size.x * Grid.CELL * k.x * 0.5, 2.5)
		var c := MINE if u.is_resource else (NEUTRAL if u.player_id == PlayerState.NEUTRAL_PASSIVE else world.player_color(u.player_id))
		var p := Vector2(u.pos.x, u.pos.z) * k
		dots.draw_rect(Rect2(p - Vector2(r, r), Vector2(r, r) * 2.0), c)
	if camera != null:
		var half := Vector2(camera.distance * 0.75, camera.distance * 0.45) * k
		var f := Vector2(camera.focus.x, camera.focus.z) * k
		dots.draw_rect(Rect2(f - half, half * 2.0), VIEW_BOX, false, 1.0)
	dots.draw_rect(Rect2(Vector2.ZERO, size), BORDER, false, 2.0)


func _to_world(local: Vector2) -> Vector3:
	var k := _scale()
	var p := Vector3(clampf(local.x, 0.0, size.x) / k.x, 0.0, clampf(local.y, 0.0, size.y) / k.y)
	p.y = world.map.height_at(p.x, p.z)
	return p


func _gui_input(event: InputEvent) -> void:
	if world == null:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed and commands != null and commands.targeting != "":
				# an armed order (A / M / P) lands on that map point; Shift queues it and keeps
				# the targeting armed (rules §18.1). No camera jump, no drag.
				commands.command_ground(_to_world(mb.position), mb.shift_pressed)
				_dragging = false
				accept_event()
				return
			_dragging = mb.pressed
			if mb.pressed and camera != null:
				camera.jump_to(_to_world(mb.position))
		elif mb.button_index == MOUSE_BUTTON_RIGHT and mb.pressed and commands != null:
			if commands.targeting != "":
				commands.cancel_targeting()     # as in the 3D view: right-click cancels targeting
			else:
				commands.command_ground(_to_world(mb.position), mb.shift_pressed)
		accept_event()
	elif event is InputEventMouseMotion and _dragging and camera != null:
		camera.jump_to(_to_world((event as InputEventMouseMotion).position))
		accept_event()
