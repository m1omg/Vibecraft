shader_type spatial;
// Vertex-coloured placeholder material shared by every unit (one draw call per unit).
// `flash` is a per-instance uniform driven by UnitView for hit feedback (visual only).

uniform float roughness = 0.75;
uniform vec4 flash_color : source_color = vec4(1.0, 0.93, 0.86, 1.0);
instance uniform float flash = 0.0;

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec3 base = srgb_to_linear(COLOR.rgb);
	ALBEDO = mix(base, flash_color.rgb, flash * 0.5);
	EMISSION = flash_color.rgb * flash * 0.55;
	ROUGHNESS = roughness;
}
