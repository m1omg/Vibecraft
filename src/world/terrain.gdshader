shader_type spatial;
// Greenvale terrain (art bible §6.1, research README §2): the 7-tile ladder (Texture2DArray, slices in
// draw order 0 scree .. 6 thick meadow) blended WC3-style with an ordered 16-case CORNER MASK, not
// soft splats. The corners are the tile centres around the fragment (dual grid of `tile_info`); for
// every ladder slot present, in draw order, the 4-bit mask "corner slot >= L" is interpolated over
// the dual cell and thresholded at 0.5 against world-space noise (amplitude 0.35 tile, ~1.7 cycles
// per tile), so later tiles overlap earlier ones with brushed, never tile-aligned edges and a
// painted dark rim. Corners across a cliff wall (connectivity bits in tile_info.g) take the
// fragment's own slot, so ground never bleeds over a wall.
// Anti-repetition: world-space UVs, two rotated samples mixed by noise, macro tint (45 m period).
// Cliff walls (UV2.x = 1): triplanar limestone, dark foot, lighter mossy painted lip (UV2.y = height
// fraction up the wall). Tile tops: COLOR.r cliff-foot AO, COLOR.g cliff-top lip.
// Water margin: wet band (-25 % value within ~0.35 m above the water line), tinted lake bed.
// Lighting: wrap-Lambert key with drifting cloud shadows (render_common). Fog-of-war hook.

render_mode cull_back, specular_disabled;

#include "res://src/render/render_common.gdshaderinc"

uniform sampler2DArray ground_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tile_info : filter_nearest, repeat_disable;
uniform sampler2D cliff_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec2 map_tiles = vec2(96.0, 96.0);
uniform float tile_m = 2.0;
uniform float ground_uv_scale = 0.16;        // repeats per metre (1024 px over ~6 m)
uniform float cliff_uv_scale = 0.28;
uniform float edge_noise_amp = 0.35;         // in tile units (bible §6.1)
uniform float edge_noise_freq = 0.85;        // cycles per metre (~1.7 per 2 m tile)
uniform float edge_width = 0.045;
uniform float edge_rim = 0.16;               // painted darker rim just inside an overlapping tile
uniform float macro_period = 45.0;
uniform float ground_saturation = 0.84;     // terrain stays the quietest layer (bible §1.4: <= 45 %)
uniform float water_level = -0.45;
uniform sampler2D fog_tex : hint_default_white, filter_linear;
uniform bool fog_enabled = false;
uniform vec2 map_size_m = vec2(192.0, 192.0);

varying vec3 v_world;
varying vec3 v_wnormal;
varying float v_ao;
varying float v_lip;
varying float v_wall;
varying float v_wall_h;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_wnormal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_ao = COLOR.r;
	v_lip = COLOR.g;
	v_wall = UV2.x;
	v_wall_h = UV2.y;
}

ivec2 clamp_tile(ivec2 t) {
	return clamp(t, ivec2(0), ivec2(map_tiles) - ivec2(1));
}

ivec2 tile_data(ivec2 t) {
	vec4 d = texelFetch(tile_info, clamp_tile(t), 0);
	return ivec2(int(d.r * 255.0 + 0.5), int(d.g * 255.0 + 0.5));
}

int bit_for(ivec2 d) {
	if (d.y == 0) {
		return d.x > 0 ? 0 : 1;
	}
	if (d.x == 0) {
		return d.y > 0 ? 2 : 3;
	}
	if (d.y > 0) {
		return d.x > 0 ? 4 : 5;
	}
	return d.x > 0 ? 6 : 7;
}

vec3 ground(int id, vec2 xz) {
	vec2 uv = xz * ground_uv_scale;
	float layer = float(id);
	vec3 a = texture(ground_tex, vec3(uv, layer)).rgb;
	// rotated (37 deg), rescaled second sample mixed in by low-frequency noise: hides the repeat
	vec2 uv2 = mat2(vec2(0.799, 0.602), vec2(-0.602, 0.799)) * uv * 0.83 + vec2(0.37, 0.61);
	vec3 b = texture(ground_tex, vec3(uv2, layer)).rgb;
	float m = smoothstep(0.3, 0.7, vc_vnoise(xz * 0.13 + layer * 3.7));
	return mix(a, b, m);
}

float edge_noise(vec2 xz, float salt) {
	vec2 p = xz * edge_noise_freq + vec2(salt * 17.31, salt * 5.77);
	return vc_vnoise(p) * 0.62 + vc_vnoise(p * 2.37 + 3.1) * 0.28 + vc_vnoise(p * 5.3 + 9.2) * 0.1 - 0.5;
}

vec3 cliff_color(vec3 p, vec3 n) {
	vec3 bw = pow(abs(n), vec3(4.0));
	bw /= (bw.x + bw.y + bw.z);
	vec3 cx = texture(cliff_tex, vec2(p.z, -p.y) * cliff_uv_scale).rgb;
	vec3 cy = texture(cliff_tex, p.xz * cliff_uv_scale).rgb;
	vec3 cz = texture(cliff_tex, vec2(p.x, -p.y) * cliff_uv_scale).rgb;
	return cx * bw.x + cy * bw.y + cz * bw.z;
}

void fragment() {
	vec2 xz = v_world.xz;
	vec3 col;
	if (v_wall > 0.5) {
		col = cliff_color(v_world, v_wnormal);
		// dark foot, lighter painted lip with a little moss on the top course (bible §6.2)
		col *= mix(0.6, 1.0, smoothstep(0.0, 0.4, v_wall_h));
		float lip = smoothstep(0.78, 0.97, v_wall_h);
		col = mix(col, col * 1.22 + vec3(0.015, 0.02, 0.0), lip);
		col = mix(col, vec3(0.30, 0.38, 0.17), smoothstep(0.93, 1.0, v_wall_h) * 0.55);
		col *= mix(0.9, 1.05, vc_vnoise(v_world.xz * 0.7 + v_world.y * 0.9));
	} else {
		vec2 p = xz / tile_m - 0.5;
		ivec2 c0 = ivec2(floor(p));
		vec2 f = fract(p);
		ivec2 own = clamp_tile(ivec2(floor(xz / tile_m)));
		ivec2 od = tile_data(own);
		int ids[4];
		ivec2 offs[4] = ivec2[4](ivec2(0, 0), ivec2(1, 0), ivec2(0, 1), ivec2(1, 1));
		for (int i = 0; i < 4; i++) {
			ivec2 t = c0 + offs[i];
			ivec2 d = t - own;
			if (d == ivec2(0)) {
				ids[i] = od.x;
			} else {
				bool linked = ((od.y >> bit_for(d)) & 1) == 1;
				ids[i] = linked ? tile_data(t).x : od.x;
			}
		}
		int lo = min(min(ids[0], ids[1]), min(ids[2], ids[3]));
		int hi = max(max(ids[0], ids[1]), max(ids[2], ids[3]));
		col = ground(lo, xz);
		for (int l = lo + 1; l <= hi; l++) {
			if (ids[0] != l && ids[1] != l && ids[2] != l && ids[3] != l) {
				continue;
			}
			float w00 = ids[0] >= l ? 1.0 : 0.0;
			float w10 = ids[1] >= l ? 1.0 : 0.0;
			float w01 = ids[2] >= l ? 1.0 : 0.0;
			float w11 = ids[3] >= l ? 1.0 : 0.0;
			float fld = mix(mix(w00, w10, f.x), mix(w01, w11, f.x), f.y);
			float a = fld + edge_noise(xz, float(l)) * 2.0 * edge_noise_amp;
			float m = smoothstep(0.5 - edge_width, 0.5 + edge_width, a);
			if (m > 0.001) {
				vec3 g = ground(l, xz);
				g *= mix(1.0 - edge_rim, 1.0, smoothstep(0.5, 0.5 + 0.16, a));
				col = mix(col, g, m);
			}
		}
		col *= v_ao;
		col = mix(col, col * 1.14 + vec3(0.012, 0.012, 0.0), v_lip * 0.7);
		// macro tint: +-6 % value, slight warm / cool hue drift (bible §6.1)
		float mt = vc_vnoise(xz / macro_period) * 0.7 + vc_vnoise(xz / (macro_period * 0.37) + 4.0) * 0.3;
		col *= mix(vec3(0.93, 0.95, 0.97), vec3(1.06, 1.05, 0.99), mt);
		col = vc_saturate(col, ground_saturation);
	}
	// shore: wet band above the water line, tinted bed below it (bible §6.3)
	float h = v_world.y;
	float wet = smoothstep(water_level + 0.38, water_level + 0.04, h);
	col *= 1.0 - 0.25 * wet;
	float under = smoothstep(water_level, water_level - 0.7, h);
	col = mix(col, col * vec3(0.55, 0.72, 0.74), under);
	if (fog_enabled) {
		float fw = texture(fog_tex, xz / map_size_m).r;
		col *= fw < 0.5 ? mix(0.0, 0.45, fw * 2.0) : mix(0.45, 1.0, (fw - 0.5) * 2.0);
	}
	ALBEDO = col;
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float w = clamp((ndl + 0.2) / 1.2, 0.0, 1.0);
	DIFFUSE_LIGHT += w * ATTENUATION * LIGHT_COLOR / PI * vc_cloud(v_world.xz);
}
