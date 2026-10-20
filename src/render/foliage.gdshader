shader_type spatial;
// Greenvale foliage and tree bark (kit conventions, tools/kits/foliage_sway.gdshader):
//   leaves (SWAY): COLOR.r sway weight, COLOR.g painted AO, COLOR.b cluster phase; alpha cutout.
//   bark: COLOR.rgb painted AO (multiply), UV2.x sway weight (the trunk bends a little).
// Wind sway in the vertex shader on the render clock (TIME): visual only (bible §6.4: 0.5 Hz, a few
// cm at the crown). MultiMesh instances carry their hue / value jitter in INSTANCE_CUSTOM.rgb
// (instance colours stay off so COLOR keeps the kit's sway / AO / phase channels).
// Wrap-lit like units, cloud shadows and the fog-of-war hook shared with the terrain.

render_mode cull_disabled, specular_disabled, depth_draw_opaque;

#include "res://src/render/render_common.gdshaderinc"

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform bool is_leaves = true;
uniform bool multimesh = false;       // INSTANCE_CUSTOM is valid only on MultiMesh
uniform float alpha_cutoff : hint_range(0.0, 1.0) = 0.42;
uniform float sway_amp = 0.06;
uniform float sway_freq = 0.5;
uniform vec3 wind_dir = vec3(1.0, 0.0, 0.35);
uniform float flutter = 0.012;
uniform float wrap = 0.6;
uniform vec3 canopy_top : source_color = vec3(1.08, 1.08, 0.94);
uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying float v_ao;
varying float v_h;
varying vec3 v_world;
varying vec3 v_tint;

void vertex() {
	float w = is_leaves ? COLOR.r : UV2.x;
	float phase = is_leaves ? COLOR.b : 0.0;
	vec3 origin = MODEL_MATRIX[3].xyz;
	float ph = phase * 6.2831853 + origin.x * 0.37 + origin.z * 0.23;
	float t = TIME * sway_freq * 6.2831853;
	float gust = sin(t + ph) * 0.75 + sin(t * 2.37 + ph * 1.7) * 0.25;
	// slow travelling gust front across the map
	gust *= 0.7 + 0.3 * sin(TIME * 0.21 + origin.x * 0.05 + origin.z * 0.02);
	vec3 wd = normalize(inverse(mat3(MODEL_MATRIX)) * normalize(wind_dir));
	VERTEX += wd * gust * sway_amp * w * w;
	VERTEX.y -= abs(gust) * sway_amp * 0.15 * w * w;
	if (is_leaves) {
		VERTEX += vec3(sin(TIME * 7.1 + ph * 3.0 + VERTEX.y), 0.0, cos(TIME * 6.3 + ph * 2.0 + VERTEX.x)) * flutter * w;
	}
	v_ao = is_leaves ? COLOR.g : 1.0;
	v_h = UV2.y;
	vec3 inst = multimesh ? INSTANCE_CUSTOM.rgb : vec3(1.0);
	// a renderer that drops MultiMesh custom data hands us zeros: fall back to no jitter
	if (dot(inst, inst) < 0.01) {
		inst = vec3(1.0);
	}
	v_tint = is_leaves ? inst : mix(vec3(1.0), inst, 0.4) * COLOR.rgb;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec4 tx = texture(albedo_tex, UV);
	vec3 col = tx.rgb * v_tint * v_ao;
	if (is_leaves) {
		// sunlit crown top, darker interior (bible §6.4: interior -> sunlit top)
		col *= mix(vec3(0.82, 0.86, 0.80), canopy_top, smoothstep(0.35, 1.0, v_h));
	} else {
		col *= mix(0.75, 1.0, smoothstep(0.0, 0.4, v_h));
	}
	if (fog_enabled) {
		float f = texture(fog_tex, v_world.xz / map_size_m).r;
		col *= f < 0.5 ? mix(0.0, 0.45, f * 2.0) : mix(0.45, 1.0, (f - 0.5) * 2.0);
	}
	ALBEDO = col;
	if (is_leaves) {
		ALPHA = tx.a;
		ALPHA_SCISSOR_THRESHOLD = alpha_cutoff;
		if (!FRONT_FACING) {
			NORMAL = -NORMAL;
		}
	}
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float w = clamp((ndl + wrap) / (1.0 + wrap), 0.0, 1.0);
	DIFFUSE_LIGHT += w * ATTENUATION * LIGHT_COLOR / PI * vc_cloud(v_world.xz);
}
