shader_type spatial;
// Painterly structure shader (buildings, halls, towers, neutral buildings): the unit shader's
// wrap lighting and team colour, painted vertex AO (COLOR multiply), emissive GLOW / LAMP / EMBER
// surfaces scaled by `glow_energy` (raised at night), the rim at half strength (bible §3.1 rule 9)
// and the construction reveal (economy juice: scaffold-raised / clans "Raising"):
//   build progress = instance slot 11 (.x); 1 = complete (no discard path taken).
//   reveal height  = UV2.y (normalized, written by the building kit) or model-space Y / model_height.
//   UV2.x = build layer (0 frame / lattice, 1 covering): covering rises after the frame.

render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_disabled;

#include "res://src/render/unit_uniforms.gdshaderinc"

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform sampler2D team_mask : filter_linear_mipmap, hint_default_black;
uniform int team_mode = 0;               // 0 none, 1 multiply (grey TEAM cloth), 2 mask / magenta key
uniform bool vertex_color_multiply = false;
uniform bool use_uv2_height = false;
uniform bool two_pass_reveal = false;    // clans: lattice first, felt over it
uniform float model_height = 6.0;
uniform vec4 emission_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform sampler2D emission_tex : source_color, hint_default_white;
uniform float emission_scale = 0.0;      // > 0 on GLOW / LAMP / EMBER / GLYPH surfaces
uniform float alpha_cut = 0.0;
uniform float wrap = 0.5;
uniform vec4 reveal_edge : source_color = vec4(1.0, 0.75, 0.42, 1.0);

varying float v_reveal;
varying float v_layer;
varying float v_height;
varying vec3 v_world;

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void vertex() {
	v_height = VERTEX.y;
	v_reveal = use_uv2_height ? UV2.y : clamp(VERTEX.y / max(model_height, 0.01), 0.0, 1.0);
	v_layer = use_uv2_height ? UV2.x : 0.0;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float progress = variant_a.x;
	float edge_glow = 0.0;
	if (progress < 0.999) {
		float p = progress;
		if (two_pass_reveal) {
			p = mix(progress / 0.6, (progress - 0.4) / 0.6, step(0.5, v_layer));
		}
		p = clamp(p, 0.0, 1.0);
		float n = vc_vnoise(v_world.xz * 3.1 + v_world.y * 1.7) - 0.5;
		float cut = p + 0.03 * n;
		if (v_reveal > cut) {
			discard;
		}
		edge_glow = smoothstep(cut - 0.035, cut, v_reveal);
	}
	vec4 tex = texture(albedo_tex, UV);
	vec3 albedo = tex.rgb;
	if (vertex_color_multiply) {
		albedo *= COLOR.rgb;
	}
	float team = 0.0;
	if (team_mode == 1) {
		team = 1.0;
		albedo *= team_color.rgb * 1.1;
	} else if (team_mode == 2) {
		float m = smoothstep(0.45, 0.8, texture(team_mask, UV).r);
		float key = smoothstep(0.18, 0.36, min(albedo.r, albedo.b) - albedo.g) * step(abs(albedo.r - albedo.b), 0.3);
		team = max(m, key);
		float shade = clamp(max(max(albedo.r, albedo.g), albedo.b) * 1.25, 0.25, 1.1);
		albedo = mix(albedo, team_color.rgb * shade, team);
	}
	if (team > 0.0) {
		albedo = mix(albedo, vc_saturate(albedo, team_sat), team);
	}
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float rim = pow(1.0 - ndv, 3.0);
	vec3 emission = rim_col.rgb * rim * min(rim_col.a * 0.5 + rim_boost, 0.6);
	if (emission_scale > 0.0) {
		emission += emission_color.rgb * texture(emission_tex, UV).rgb * emission_scale * glow_energy;
	}
	vec4 fl = vc_flash_curve();
	if (fl.a > 0.0) {
		// structures: a value dip, never a white flash (CMB-17 structures note)
		albedo *= 1.0 - 0.15 * fl.a;
	}
	emission += reveal_edge.rgb * edge_glow * 0.6;
	if (!FRONT_FACING) {
		// inside faces (seen through the construction cut, or the back of a banner): a dark,
		// warm interior so a half-built shell reads solid
		albedo *= progress < 0.999 ? 0.28 : 0.75;
		NORMAL = -NORMAL;
		emission *= 0.0;
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
	float band = smoothstep(0.25, 0.75, w);
	DIFFUSE_LIGHT += mix(w, band, 0.4) * ATTENUATION * LIGHT_COLOR / PI * vc_cloud(v_world.xz);
}
