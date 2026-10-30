shader_type spatial;
// XP motes (juice HER-03, Playtest 3 subset): camera-facing sprites drawn here, no texture.
// custom.x: 0 = the kingdom's ivory spoke-chip (a wedge with a warm halo), 1 = the Tormai bronze
// fleck (a six-point glint). The colour's alpha fades a mote; custom.y is its glow.
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix, fog_disabled;

varying vec4 custom;

void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0),
		vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	custom = INSTANCE_CUSTOM;
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	float aa = max(fwidth(r), 0.01);
	float core;
	if (custom.x < 0.5) {
		// a wedge pointing up: |x| shrinks toward the tip
		float w = 0.42 * (0.85 - p.y) / 1.7;
		core = (1.0 - smoothstep(w - aa, w + aa, abs(p.x))) * step(-0.85, p.y) * step(p.y, 0.85);
	} else {
		float ang = atan(p.y, p.x);
		float star = 0.22 + 0.5 * pow(abs(cos(ang * 3.0)), 8.0);
		core = 1.0 - smoothstep(star - aa, star + aa, r);
	}
	float halo = (1.0 - smoothstep(0.0, 1.0, r)) * 0.55 * custom.y;
	vec3 halo_col = custom.x < 0.5 ? vec3(1.0, 0.914, 0.659) : vec3(1.0, 0.8, 0.5);
	ALBEDO = mix(halo_col, COLOR.rgb, core);
	ALPHA = clamp(max(core, halo), 0.0, 1.0) * COLOR.a;
}
