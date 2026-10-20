// Shared render helpers for every Vibecraft surface shader (units, structures, foliage, terrain):
// the per-frame material uniforms written by RenderAtmos and cheap value noise / cloud shadows.
// Guarded so a shader may include it more than once.
#ifndef VC_RENDER_COMMON
#define VC_RENDER_COMMON

uniform float fx_time = 0.0;                 // seconds, advanced with real delta (render clock)
uniform vec4 unit_fill = vec4(0.55, 0.62, 1.0, 0.0);   // rgb fill colour, a = amount (night)
uniform float glow_energy = 1.0;             // GLOW / LAMP surfaces (night raises it)
uniform float cloud_strength = 0.3;
uniform vec2 cloud_offset = vec2(0.0);       // metres scrolled (integrated on the render clock)

float vc_hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vc_vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(vc_hash12(i), vc_hash12(i + vec2(1.0, 0.0)), u.x),
		mix(vc_hash12(i + vec2(0.0, 1.0)), vc_hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}

// Drifting cloud shadow factor (1 = sunlit, 1 - strength = under a cloud). World-space, so units,
// structures, trees and the terrain darken together.
float vc_cloud(vec2 xz) {
	vec2 p = (xz + cloud_offset) * 0.022;
	float n = vc_vnoise(p) * 0.6 + vc_vnoise(p * 2.3 + 7.1) * 0.3 + vc_vnoise(p * 5.1 + 3.3) * 0.1;
	return 1.0 - cloud_strength * smoothstep(0.48, 0.66, n);
}

float vc_luma(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

vec3 vc_saturate(vec3 c, float s) {
	return mix(vec3(vc_luma(c)), c, s);
}

#endif
