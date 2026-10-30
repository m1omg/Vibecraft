shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, depth_test_disabled, blend_mix, shadows_disabled, fog_disabled;
// The build ghost's footprint grid (juice BLD-02): one quad per 0.5 m cell laid on the ground,
// COLOR.r = Construction.CELL_* / 255, UV = the cell's own 0..1. Squares inset 0.04 m with a
// 0.03 m dark outline. Valid green; blocked red with a 45° hatch (stripe 0.06 m, period
// 0.16 m); unexplored black hatch; a ground rule (a hall near a Gold Seam) violet hatch; the
// 2-cell context border faint white. Drawn without depth test (render_priority -1, before the
// ghost's passes) so blocked cells show on top of the building that blocks them.

uniform vec4 ok_col : source_color = vec4(0.32, 0.92, 0.38, 0.35);
uniform vec4 bad_col : source_color = vec4(0.95, 0.24, 0.18, 0.5);
uniform vec4 rule_col : source_color = vec4(0.557, 0.357, 1.0, 0.5);
uniform vec4 dark_col : source_color = vec4(0.02, 0.02, 0.02, 0.6);
uniform vec4 ctx_col : source_color = vec4(1.0, 1.0, 1.0, 0.12);
uniform float cell_m = 0.5;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	int s = int(round(COLOR.r * 255.0));
	vec2 e2 = min(UV, 1.0 - UV) * cell_m;
	float edge = min(e2.x, e2.y);
	if (edge < 0.04) {
		discard;
	}
	float stripe = step(1.0 - 0.06 / 0.16, fract((world_pos.x + world_pos.z) / 0.16));
	vec4 c = ctx_col;
	if (s == 1) {
		c = ok_col;
	} else if (s == 2 || s == 3 || s == 6) {
		c = bad_col;
		c.a = mix(c.a, 0.85, stripe);
	} else if (s == 4) {
		c = dark_col;
		c.a = mix(0.35, 0.8, stripe);
	} else if (s == 5) {
		c = rule_col;
		c.a = mix(c.a, 0.85, stripe);
	}
	if (s != 0 && edge < 0.07) {
		c = vec4(0.05, 0.04, 0.03, max(c.a, 0.55));
	}
	ALBEDO = c.rgb;
	ALPHA = c.a;
}
