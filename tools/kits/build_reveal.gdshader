// Construction reveal for every building mesh: the procedural kit (tools/kits/buildings.py) and the
// AI-modelled halls alike (they have no UV2 / COLOR_0, so the height comes from the vertex itself).
//
// Use while a structure is being built (or a hall is upgrading): give the building's surfaces this
// ShaderMaterial (copy albedo_tex / emission_tex from the imported material, albedo_color = the team
// colour on the TEAM surface, white elsewhere), set model_height from the manifest's height_m (or the
// mesh AABB height for the AI halls) and drive `progress` 0 -> 1; swap the imported materials back at 1.
//
//   kingdom "scaffold-raised": two_pass = false, the walls rise bottom-up behind a ragged ember edge
//   clans "Raising":           two_pass = true, UV2.x = 0 (lattice, masts, stone) rises over progress
//                              0..0.6, UV2.x = 1 (felt, roofs, team bands) over 0.4..1.0
//
// Normalized height = object-space VERTEX.y / model_height (0 at the ground, 1 at the top), so no
// per-vertex data is needed; the kit's UV2.y holds the same value for tools that want it.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert_wrap, specular_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 albedo_color : source_color = vec4(1.0);
uniform bool use_vertex_color = true;          // kit meshes: COLOR_0 = painted AO (multiply)
uniform sampler2D emission_tex : source_color, hint_default_black, filter_linear_mipmap;
uniform vec3 emission = vec3(0.0);             // GLOW surfaces: the day/night emissive factor
uniform float progress : hint_range(0.0, 1.0) = 1.0;
uniform float model_height = 6.0;              // metres
uniform bool two_pass = false;
uniform float band = 0.05;                     // ragged edge width (fraction of the height)
uniform vec3 edge_color : source_color = vec3(1.0, 0.62, 0.25);
uniform float edge_energy = 1.4;

varying vec3 obj_pos;
varying float layer;

// Value noise from an integer hash (Godot's shading language has no built-in noise).
float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = hash12(i);
	float b = hash12(i + vec2(1.0, 0.0));
	float c = hash12(i + vec2(0.0, 1.0));
	float d = hash12(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

void vertex() {
	obj_pos = VERTEX;
	layer = UV2.x;
}

void fragment() {
	float h = clamp(obj_pos.y / max(model_height, 0.01), 0.0, 1.0);
	float p = progress;
	if (two_pass) {
		p = layer < 0.5 ? progress / 0.6 : (progress - 0.4) / 0.6;
	}
	p = clamp(p, 0.0, 1.0);
	float n = vnoise(obj_pos.xz * 2.5 + vec2(obj_pos.y * 1.3)) - 0.5;
	// cut height: below -band at p = 0 (nothing shows), above 1 + band at p = 1 (all shows)
	float cut = mix(-band, 1.0 + band, p) + n * band;
	if (h > cut) {
		discard;
	}
	vec4 a = texture(albedo_tex, UV) * albedo_color;
	if (use_vertex_color) {
		a.rgb *= COLOR.rgb;
	}
	ALBEDO = a.rgb;
	ROUGHNESS = 1.0;
	float edge = p < 1.0 ? 1.0 - smoothstep(0.0, band, cut - h) : 0.0;
	EMISSION = texture(emission_tex, UV).rgb * emission + edge_color * edge * edge_energy;
}
