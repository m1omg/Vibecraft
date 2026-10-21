shader_type spatial;
render_mode unshaded, cull_back, depth_draw_never, blend_mix, shadows_disabled, fog_disabled;
// Build ghost, pass 2 of 3 (juice BLD-01 "surveyor's sketch", not a hologram): paper at low alpha
// (0.3: the bible's 0.18 read too faint at the 28 m camera)
// with grain, 45° screen-space hatching where the sun does not reach (N·L < 0.2), a second
// crossing hatch over every face when the spot is refused (shape-coded, not only red), and line
// boil: the hatch jumps by ±1 px 8 times a second (`boil` = floor(ui seconds × 8), so the
// look is the same at any refresh rate).

uniform vec4 paper : source_color = vec4(0.93, 0.89, 0.80, 0.3);
uniform vec4 ink : source_color = vec4(0.17, 0.13, 0.09, 0.85);
uniform vec3 sun_to = vec3(0.35, 0.8, 0.45);
uniform float boil = 0.0;
uniform float refused = 0.0;
uniform float hatch_px = 6.0;

varying vec3 world_normal;

float hash11(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void vertex() {
	world_normal = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;
}

void fragment() {
	vec2 px = FRAGCOORD.xy + (vec2(hash11(boil), hash11(boil + 7.31)) - 0.5) * 2.0;
	float ndl = dot(normalize(world_normal), normalize(sun_to));
	float shade = 1.0 - smoothstep(0.1, 0.2, ndl);
	float a = step(0.7, fract((px.x + px.y) / hatch_px)) * shade;
	float b = step(0.7, fract((px.x - px.y) / hatch_px)) * refused;
	float h = max(a, b);
	float grain = hash11(floor(px.x) * 0.371 + floor(px.y) * 1.137) * 0.05;
	ALBEDO = mix(paper.rgb - grain, ink.rgb, h);
	ALPHA = mix(paper.a, ink.a * 0.6, h);
}
