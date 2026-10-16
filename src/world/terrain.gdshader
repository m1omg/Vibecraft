shader_type spatial;
// Terrain: up to 8 splat layers (weights in COLOR = layers 0-3, CUSTOM0 = layers 4-7) with
// height-based noise blending, triplanar rock on cliff walls (UV2.x = 1), fog-of-war hook.
// Layers are procedural colour+noise placeholders until `use_layer_textures` is enabled with a
// Texture2DArray (one slice per layer, same order):
//   0 grass, 1 dark grass, 2 dirt, 3 rough dirt, 4 rock, 5 sand, 6 dry grass, 7 paved

render_mode diffuse_burley, specular_schlick_ggx, cull_back;

uniform sampler2DArray layer_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_layer_textures = false;
uniform float layer_uv_scale = 0.25;          // texture repeats per metre
uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_rock_texture = false;
uniform float rock_uv_scale = 0.3;
uniform float blend_sharpness = 0.25;

uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying vec3 world_pos;
varying vec3 world_normal;
varying vec4 w_lo;
varying vec4 w_hi;
varying float rock_flag;

const vec3 LAYER_COLOR[8] = vec3[8](
	vec3(0.34, 0.44, 0.19),   // grass
	vec3(0.23, 0.33, 0.15),   // dark grass
	vec3(0.45, 0.34, 0.21),   // dirt
	vec3(0.38, 0.32, 0.25),   // rough dirt
	vec3(0.43, 0.41, 0.38),   // rock
	vec3(0.71, 0.63, 0.45),   // sand
	vec3(0.50, 0.46, 0.25),   // dry grass
	vec3(0.55, 0.52, 0.47)    // paved
);
const float LAYER_FREQ[8] = float[8](0.35, 0.45, 0.6, 0.9, 0.7, 0.8, 0.4, 0.5);
const float LAYER_CONTRAST[8] = float[8](0.25, 0.3, 0.3, 0.45, 0.35, 0.18, 0.3, 0.2);

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

float fbm(vec2 p) {
	float v = 0.0;
	float amp = 0.5;
	for (int i = 0; i < 4; i++) {
		v += amp * vnoise(p);
		p = p * 2.03 + vec2(17.1, 9.7);
		amp *= 0.5;
	}
	return v;
}

// Paving stones: running-bond rows of irregular slabs with soft grout.
float paving(vec2 p) {
	p.x += step(1.0, mod(floor(p.y), 2.0)) * 0.5;
	p += (vec2(vnoise(p * 3.0), vnoise(p * 3.0 + 7.0)) - 0.5) * 0.08;
	vec2 cell = floor(p);
	vec2 f = fract(p);
	float d = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
	float stone = 0.88 + 0.22 * hash12(cell);
	return mix(0.72, stone, smoothstep(0.02, 0.08, d));
}

vec3 layer_color(int i, vec2 xz) {
	if (use_layer_textures) {
		return texture(layer_albedo, vec3(xz * layer_uv_scale, float(i))).rgb;
	}
	float n = fbm(xz * LAYER_FREQ[i] + float(i) * 13.7);
	float speck = vnoise(xz * 6.0 + float(i) * 3.1);
	vec3 c = LAYER_COLOR[i] * (1.0 - LAYER_CONTRAST[i] + 2.0 * LAYER_CONTRAST[i] * n);
	c *= 0.92 + 0.16 * speck;
	if (i == 7) {
		c *= paving(xz * vec2(0.8, 1.1));
	}
	return c;
}

vec3 rock_color(vec3 p, vec3 n) {
	vec3 bw = pow(abs(n), vec3(4.0));
	bw /= (bw.x + bw.y + bw.z);
	if (use_rock_texture) {
		vec3 cx = texture(rock_albedo, p.zy * rock_uv_scale).rgb;
		vec3 cy = texture(rock_albedo, p.xz * rock_uv_scale).rgb;
		vec3 cz = texture(rock_albedo, p.xy * rock_uv_scale).rgb;
		return cx * bw.x + cy * bw.y + cz * bw.z;
	}
	// procedural strata: horizontal bands warped by noise, per projection plane
	float sx = fbm(p.zy * vec2(0.8, 2.2));
	float sy = fbm(p.xz * 0.9);
	float sz = fbm(p.xy * vec2(0.8, 2.2));
	float s = sx * bw.x + sy * bw.y + sz * bw.z;
	float band = 0.5 + 0.5 * sin(p.y * 5.0 + s * 6.0);
	vec3 base = mix(vec3(0.30, 0.27, 0.24), vec3(0.50, 0.46, 0.40), s);
	return base * (0.8 + 0.25 * band);
}

float fog_factor(vec2 xz) {
	float f = texture(fog_tex, xz / map_size_m).r;
	return f < 0.5 ? mix(0.0, 0.45, f * 2.0) : mix(0.45, 1.0, (f - 0.5) * 2.0);
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	w_lo = COLOR;
	w_hi = CUSTOM0;
	rock_flag = UV2.x;
}

void fragment() {
	vec2 xz = world_pos.xz;
	float w[8] = float[8](w_lo.r, w_lo.g, w_lo.b, w_lo.a, w_hi.r, w_hi.g, w_hi.b, w_hi.a);
	// height blend: each layer gets a noise "height", the tallest weighted layers win with a
	// soft transition band, giving organic borders instead of bilinear smears.
	float hmax = 0.0;
	float hv[8];
	for (int i = 0; i < 8; i++) {
		hv[i] = w[i] > 0.001 ? w[i] + 0.55 * fbm(xz * 0.55 + float(i) * 7.3) : -1.0;
		hmax = max(hmax, hv[i]);
	}
	vec3 col = vec3(0.0);
	float total = 0.0;
	for (int i = 0; i < 8; i++) {
		float b = max(hv[i] - hmax + blend_sharpness, 0.0);
		if (b > 0.0) {
			col += layer_color(i, xz) * b;
			total += b;
		}
	}
	col /= max(total, 0.0001);

	float steep = smoothstep(0.82, 0.6, world_normal.y);
	float rock = max(rock_flag, steep);
	if (rock > 0.001) {
		col = mix(col, rock_color(world_pos, world_normal), rock);
	}
	// darken the base of walls slightly (fake ambient occlusion)
	col *= 1.0 - 0.18 * rock_flag * (1.0 - clamp(fract(world_pos.y / 1.75) * 2.0, 0.0, 1.0));

	if (fog_enabled) {
		col *= fog_factor(xz);
	}
	// palette and procedural colours are authored in sRGB; lighting works in linear space
	ALBEDO = use_layer_textures ? col : pow(col, vec3(2.2));
	ROUGHNESS = mix(0.92, 0.8, rock);
	SPECULAR = 0.25;
}
