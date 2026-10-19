shader_type spatial;
// Reference shader for the procedural Greenvale foliage (tools/kits/doodads.py): every material whose
// name contains "SWAY" (tree canopies, hedges, reeds, flower and grass cards). It is also what
// tools/render_preview.py and tools/kits/lineup.gd apply to SWAY materials, so the QA renders match.
//
// Vertex data written by doodads.py on SWAY materials:
//   COLOR.r  sway weight: 0 at the trunk base / stem root -> 1 at the canopy edge / blade tip
//   COLOR.g  painted ambient occlusion (multiply into the albedo, linear)
//   COLOR.b  per-cluster phase 0..1 (de-synchronises gusts between leaf clumps)
//   UV2.x    sway weight again (also present on the rigid bark parts of a tree: trunk bends a little)
//   UV2.y    normalized height (0 at the ground, 1 at the top of the asset)
// The albedo texture has straight alpha (cutout, glTF alphaMode MASK) and colour padded into the
// transparent texels, so mipmaps never fringe.
// Bible §6.4: crown sway 0.5 Hz, ~3 cm at the crown; per-instance hue jitter is `tint`.

render_mode cull_disabled, diffuse_lambert_wrap, specular_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec4 tint : source_color = vec4(1.0);
uniform float alpha_cutoff : hint_range(0.0, 1.0) = 0.5;
uniform float sway_amp = 0.05;            // metres of crown travel at weight 1
uniform float sway_freq = 0.5;            // Hz
uniform vec3 wind_dir = vec3(1.0, 0.0, 0.35);
uniform float flutter = 0.012;            // small fast leaf flutter, metres

varying float v_ao;

void vertex() {
	float w = COLOR.r;
	vec3 origin = MODEL_MATRIX[3].xyz;
	float ph = COLOR.b * 6.2831853 + origin.x * 0.37 + origin.z * 0.23;
	float t = TIME * sway_freq * 6.2831853;
	float gust = sin(t + ph) * 0.75 + sin(t * 2.37 + ph * 1.7) * 0.25;
	vec3 wd = normalize(inverse(mat3(MODEL_MATRIX)) * normalize(wind_dir));
	VERTEX += wd * gust * sway_amp * w * w;
	VERTEX.y -= abs(gust) * sway_amp * 0.15 * w * w;
	VERTEX += vec3(sin(TIME * 7.1 + ph * 3.0 + VERTEX.y), 0.0, cos(TIME * 6.3 + ph * 2.0 + VERTEX.x)) * flutter * w;
	v_ao = COLOR.g;
}

void fragment() {
	vec4 tx = texture(albedo_tex, UV);
	ALBEDO = tx.rgb * tint.rgb * v_ao;
	ALPHA = tx.a;
	ALPHA_SCISSOR_THRESHOLD = alpha_cutoff;
	// cards carry soft "canopy sphere" normals: keep the same normal on the back face
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	ROUGHNESS = 1.0;
}
