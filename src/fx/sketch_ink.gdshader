shader_type spatial;
render_mode unshaded, cull_front, depth_draw_never, blend_mix, shadows_disabled, fog_disabled, world_vertex_coords;
// Build ghost, pass 3 of 3 (juice BLD-01): the ink outline from an inverted hull. Back faces are
// pushed out along the normal by `width` metres (0.05; the bible's 0.03 drew 1 px lines) at a 28 m view distance (scaled with distance,
// so the line keeps its screen weight), with the same 8-steps-a-second boil as the hatching.

uniform vec4 ink : source_color = vec4(0.17, 0.13, 0.09, 0.85);
uniform float width = 0.05;
uniform float boil = 0.0;

void vertex() {
	float d = length(CAMERA_POSITION_WORLD - VERTEX);
	float j = fract(sin(boil * 3.71 + VERTEX.x * 1.31 + VERTEX.z * 2.17) * 4375.85) - 0.5;
	VERTEX += normalize(NORMAL) * width * (d / 28.0) * (1.0 + j * 0.3);
}

void fragment() {
	ALBEDO = ink.rgb;
	ALPHA = ink.a;
}
