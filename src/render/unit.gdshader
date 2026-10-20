shader_type spatial;
// Painterly uber-shader for GLB units, heroes, creeps (art bible §1.1 rule 9, juice bible §4.3):
// wrap-Lambert key light with a soft two-band ramp, no specular, painted albedo with a model-space
// vertical value gradient, team colour (texel mask + magenta key, or a grey TEAM surface multiplied),
// a team-colour rim, the energy-conserving latched hit flash and the corpse team-colour ebb.
// Instance uniforms: unit_uniforms.gdshaderinc (fixed slot map). Placeholders use the same maths
// with `use_vertex_color` (sRGB vertex colours, no texture).

render_mode blend_mix, depth_draw_opaque, cull_back, specular_disabled;

#include "res://src/render/unit_uniforms.gdshaderinc"

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable, hint_default_white;
uniform sampler2D team_mask : filter_linear_mipmap, hint_default_black;
uniform int team_mode = 0;              // 0 none, 1 multiply albedo (grey TEAM cloth), 2 mask / magenta key
uniform bool use_vertex_color = false;  // placeholders: sRGB vertex colours are the albedo
uniform bool vertex_color_multiply = false;
uniform float gradient_height = 1.8;    // model-space metres of the dark-feet -> light-head gradient
uniform vec2 gradient_range = vec2(0.86, 1.1);
uniform float wrap = 0.55;
uniform float band_softness = 0.28;
uniform float shadow_floor = 0.0;
uniform float rim_power = 2.2;
uniform float alpha_cut = 0.0;

varying float v_height;
varying vec3 v_world;

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void vertex() {
	v_height = VERTEX.y;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec4 tex = texture(albedo_tex, UV);
	vec3 albedo = tex.rgb;
	if (use_vertex_color) {
		albedo = srgb_to_linear(COLOR.rgb);
	} else if (vertex_color_multiply) {
		albedo *= COLOR.rgb;
	}
	// team colour
	float team = 0.0;
	vec3 team_rgb = team_color.rgb;
	if (team_mode == 1) {
		team = 1.0;
		albedo = albedo * team_rgb * 1.15;
	} else if (team_mode == 2) {
		float m = smoothstep(0.45, 0.8, texture(team_mask, UV).r);
		// magenta key catches texels the mask missed (hue ~300 deg, saturated)
		float key = smoothstep(0.18, 0.36, min(albedo.r, albedo.b) - albedo.g) * step(abs(albedo.r - albedo.b), 0.3);
		team = max(m, key);
		float shade = clamp(max(max(albedo.r, albedo.g), albedo.b) * 1.25, 0.25, 1.1);
		albedo = mix(albedo, team_rgb * shade, team);
	}
	if (team > 0.0) {
		float k = sat_front < 0.0 ? 0.0 : smoothstep(sat_front - 0.15, sat_front + 0.15, v_height);
		float s = mix(team_sat, 1.0, k);
		albedo = mix(albedo, vc_saturate(albedo, s) * mix(0.85, 1.0, s), team);
	}
	// painted top-lit value gradient (silhouettes separate by value, bible §1.6)
	albedo *= mix(gradient_range.x, gradient_range.y, smoothstep(0.0, gradient_height, v_height));
	// rim: team colour, always on (bible §3.1 rule 9); boosted by hover / select
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float rim = pow(1.0 - ndv, rim_power);
	float rim_s = min(rim_col.a + rim_boost, 0.9);
	vec3 emission = rim_col.rgb * rim * rim_s;
	// night unit fill keeps units >= 60 % of noon (world doc §5.1)
	emission += albedo * unit_fill.rgb * unit_fill.a * 0.35;
	// energy-conserving latched flash (CMB-17)
	vec4 fl = vc_flash_curve();
	if (fl.a > 0.0) {
		float f = fl.a * (0.3 + 0.7 * (1.0 - ndv) * (1.0 - ndv));
		albedo *= 1.0 - 0.6 * f;
		emission += fl.rgb * 0.45 * f;
	}
	ALBEDO = albedo;
	EMISSION = emission;
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
	if (alpha_cut > 0.0) {
		ALPHA = tex.a;
		ALPHA_SCISSOR_THRESHOLD = alpha_cut;
	}
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float w = clamp((ndl + wrap) / (1.0 + wrap), 0.0, 1.0);
	// soft two-band ramp blended with the plain wrap term: painted, never cel-hard
	float band = smoothstep(0.5 - band_softness, 0.5 + band_softness, w);
	float d = mix(w, band, 0.45);
	float shadow = max(ATTENUATION, shadow_floor);
	DIFFUSE_LIGHT += d * shadow * LIGHT_COLOR / PI * vc_cloud(v_world.xz);
}
