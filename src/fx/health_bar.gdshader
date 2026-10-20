shader_type spatial;
// Billboard health bar (CMB-29). INSTANCE_CUSTOM: r = hp ratio, g = width (m), b = height (m),
// a = mana ratio. INSTANCE COLOR: r = damage ghost ratio (>= hp: the trailing segment the bar
// just lost, #FFE3A0), g = border flash 0..1 (latched 70 ms, white), b = hover / select
// highlight 0..1. No TIME: every curve is evaluated on the CPU from the fx clock.
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, shadows_disabled;

varying float fill;
varying vec2 size_m;
varying vec3 extra;

void vertex() {
	fill = INSTANCE_CUSTOM.r;
	size_m = INSTANCE_CUSTOM.gb;
	extra = COLOR.rgb;
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 right = INV_VIEW_MATRIX[0].xyz;
	vec3 up = INV_VIEW_MATRIX[1].xyz;
	vec3 world_v = origin + right * VERTEX.x * size_m.x + up * VERTEX.y * size_m.y;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(world_v, 1.0);
}

void fragment() {
	vec2 uv = UV;
	// border ~0.03 m regardless of bar size
	vec2 b = vec2(0.03) / size_m;
	bool edge = uv.x < b.x || uv.x > 1.0 - b.x || uv.y < b.y || uv.y > 1.0 - b.y;
	float ghost = max(extra.r, fill);
	vec3 hp_col = fill > 0.5 ? mix(vec3(1.0, 0.85, 0.1), vec3(0.15, 0.9, 0.2), (fill - 0.5) * 2.0)
		: mix(vec3(0.95, 0.12, 0.08), vec3(1.0, 0.85, 0.1), fill * 2.0);
	vec3 col = vec3(0.06, 0.06, 0.06);
	if (uv.x <= fill) {
		col = hp_col;
	} else if (uv.x <= ghost) {
		col = vec3(1.0, 0.89, 0.627);   // #FFE3A0 damage ghost
	}
	col *= 0.8 + 0.25 * (1.0 - uv.y);
	vec3 border = mix(vec3(0.0), vec3(0.32, 0.30, 0.26), extra.b);
	border = mix(border, vec3(1.0), clamp(extra.g, 0.0, 1.0));
	ALBEDO = edge ? border : col;
	ALPHA = 1.0;
}
