shader_type spatial;
// Placeholder water: animated two-scale ripple normals, depth-ish tint, soft transparency.

render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 shallow_color : source_color = vec3(0.16, 0.42, 0.48);
uniform vec3 deep_color : source_color = vec3(0.05, 0.18, 0.30);
uniform float alpha = 0.78;
uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying vec3 world_pos;

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x),
		mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}

float ripples(vec2 p) {
	return vnoise(p * 0.8 + vec2(TIME * 0.25, TIME * 0.12)) * 0.6
		+ vnoise(p * 2.1 - vec2(TIME * 0.18, -TIME * 0.3)) * 0.4;
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_pos.xz;
	float e = 0.15;
	float h = ripples(p);
	float hx = ripples(p + vec2(e, 0.0));
	float hz = ripples(p + vec2(0.0, e));
	vec3 n = normalize(vec3((h - hx) * 1.2, 1.0, (h - hz) * 1.2));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	vec3 col = mix(deep_color, shallow_color, 0.35 + 0.4 * h);
	if (fog_enabled) {
		float f = texture(fog_tex, p / map_size_m).r;
		col *= f < 0.5 ? mix(0.0, 0.45, f * 2.0) : mix(0.45, 1.0, (f - 0.5) * 2.0);
	}
	ALBEDO = col;
	ALPHA = alpha;
	ROUGHNESS = 0.08;
	METALLIC = 0.0;
	SPECULAR = 0.6;
}
