shader_type spatial;
// Placeholder tree material: vertex colour (merged primitives) x instance tint, gentle wind
// sway (visual only, render TIME), fog-of-war darkening hook shared with the terrain.

render_mode diffuse_burley, specular_schlick_ggx;

uniform float wind_strength = 0.05;
uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying vec3 world_pos;
varying float local_h;

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	float phase = TIME * 1.3 + origin.x * 0.37 + origin.z * 0.23;
	local_h = VERTEX.y;
	float bend = max(VERTEX.y - 1.0, 0.0);
	VERTEX.x += sin(phase) * wind_strength * bend * bend * 0.3;
	VERTEX.z += cos(phase * 0.8) * wind_strength * bend * bend * 0.15;
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float fog_factor(vec2 xz) {
	float f = texture(fog_tex, xz / map_size_m).r;
	return f < 0.5 ? mix(0.0, 0.45, f * 2.0) : mix(0.45, 1.0, (f - 0.5) * 2.0);
}

void fragment() {
	vec3 col = COLOR.rgb;
	// cheap fake AO: darker near the ground and inside the canopy
	col *= mix(0.6, 1.05, clamp(local_h / 3.5, 0.0, 1.0));
	if (fog_enabled) {
		col *= fog_factor(world_pos.xz);
	}
	ALBEDO = pow(col, vec3(2.2));   // vertex colours are authored in sRGB
	ROUGHNESS = 0.9;
	SPECULAR = 0.15;
}
