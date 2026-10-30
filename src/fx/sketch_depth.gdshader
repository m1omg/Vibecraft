shader_type spatial;
render_mode unshaded, cull_back, depth_draw_always, blend_mix, shadows_disabled, fog_disabled;
// Build ghost, pass 1 of 3 (juice BLD-01): depth only, so the sketch fill and the ink hull that
// follow (next_pass) draw the nearest surface alone and the roof never shows through the walls.

void fragment() {
	ALBEDO = vec3(0.0);
	ALPHA = 0.0;
}
