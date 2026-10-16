shader_type spatial;
// Selection ring on a flat quad (instance colour = relation colour).
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix;

uniform float inner = 0.80;
uniform float outer = 0.97;
uniform vec4 tint : source_color = vec4(1.0);   // used by single-mesh markers

void fragment() {
	vec2 uv = UV * 2.0 - 1.0;
	float d = length(uv);
	float aa = fwidth(d) * 1.5;
	float ring = smoothstep(inner - aa, inner + aa, d) * (1.0 - smoothstep(outer - aa, outer + aa, d));
	// darker outline helps on bright terrain
	float core = smoothstep(inner + 0.02, inner + 0.05, d) * (1.0 - smoothstep(outer - 0.05, outer - 0.02, d));
	ALBEDO = COLOR.rgb * tint.rgb * mix(0.35, 1.0, core);
	ALPHA = ring * COLOR.a * tint.a;
}
