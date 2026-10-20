shader_type spatial;
// Greenvale water (art bible §6.3): the painted water_ripples texture scrolled at two scales and
// directions (~0.05 m/s), shallow #4FA3A0 -> deep #22566E by depth (from the terrain height texture,
// so it needs no depth buffer and works on Compatibility), a soft foam line #E8F0EC at 40 % alpha
// where the water meets the shore, transparency fading in towards the shore, ripple normals for the
// sun glint. Moon tint at night comes from the scene lighting. Fog-of-war hook.

render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

#include "res://src/render/render_common.gdshaderinc"

uniform sampler2D ripple_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D height_tex : filter_linear, repeat_disable;
uniform vec3 shallow_color : source_color = vec3(0.31, 0.64, 0.63);
uniform vec3 deep_color : source_color = vec3(0.133, 0.337, 0.431);
uniform vec3 foam_color : source_color = vec3(0.91, 0.94, 0.925);
uniform float foam_alpha = 0.4;
uniform float water_level = -0.45;
uniform float deep_depth = 1.0;
uniform float ripple_scale = 0.22;           // repeats per metre
uniform float scroll_speed = 0.05;           // m/s
uniform vec2 map_tiles = vec2(96.0, 96.0);
uniform float tile_m = 2.0;
uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying vec3 v_world;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float bed_height(vec2 xz) {
	// height_tex holds one texel per grid vertex: sample texel centres for exact bilinear
	vec2 uv = (xz / tile_m + 0.5) / (map_tiles + 1.0);
	return texture(height_tex, uv).r;
}

void fragment() {
	vec2 xz = v_world.xz;
	float t = TIME * scroll_speed;
	vec2 uv1 = xz * ripple_scale + vec2(t, t * 0.6);
	vec2 uv2 = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * xz * ripple_scale * 1.37 - vec2(t * 0.7, -t * 0.9);
	vec3 r1 = texture(ripple_tex, uv1).rgb;
	vec3 r2 = texture(ripple_tex, uv2).rgb;
	vec3 rip = (r1 + r2) * 0.5;
	float lum = vc_luma(rip);
	// ripple normals from the luminance gradient of the two layers
	float e = 0.04;
	float lx = vc_luma(texture(ripple_tex, uv1 + vec2(e, 0.0)).rgb + texture(ripple_tex, uv2 + vec2(e, 0.0)).rgb) * 0.5;
	float lz = vc_luma(texture(ripple_tex, uv1 + vec2(0.0, e)).rgb + texture(ripple_tex, uv2 + vec2(0.0, e)).rgb) * 0.5;
	vec3 n = normalize(vec3((lum - lx) * 1.6, 1.0, (lum - lz) * 1.6));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	float depth = water_level - bed_height(xz);
	float d = clamp(depth / deep_depth, 0.0, 1.0);
	vec3 col = mix(shallow_color, deep_color, smoothstep(0.0, 1.0, d));
	col *= mix(0.85, 1.25, lum);
	// foam line: a soft band right at the shore, broken up by the ripples
	float foam = (1.0 - smoothstep(0.0, 0.16, depth)) * smoothstep(-0.06, 0.02, depth);
	foam *= smoothstep(0.35, 0.65, lum + vc_vnoise(xz * 3.0 + TIME * 0.3) * 0.4);
	col = mix(col, foam_color, foam * foam_alpha * 2.0);
	if (fog_enabled) {
		float f = texture(fog_tex, xz / map_size_m).r;
		col *= f < 0.5 ? mix(0.0, 0.45, f * 2.0) : mix(0.45, 1.0, (f - 0.5) * 2.0);
	}
	ALBEDO = col;
	ALPHA = clamp(mix(0.55, 0.92, smoothstep(0.0, 0.6, depth)) + foam * 0.3, 0.0, 1.0);
	ROUGHNESS = 0.12;
	METALLIC = 0.0;
	SPECULAR = 0.55;
}
