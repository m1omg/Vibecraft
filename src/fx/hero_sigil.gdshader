shader_type spatial;
// Hero sigil (juice HER-01, Playtest 3 subset): a ring under every living hero, cut into 10 arc
// segments that light with the hero's level (the gaps close at level 10), an always-lit
// team-colour ownership line and the faction face inside: the kingdom's Ember Wheel (team-colour
// segments, six ivory spokes that ratchet, a bronze hub) or the Tormai Gong (bronze segments, a
// team-colour felt stripe on the outer edge, two swaying winds). The own hero's XP arc runs
// just outside the band. Also drawn on the standing level-up emblem (HER-04). Every value comes
// per frame from closed-form curves on the CPU (no TIME): the same look at any refresh rate.
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix, fog_disabled;

const float HALF = 1.2;            // metres from the quad's centre to its edge
const float BAND_IN = 0.82;
const float BAND_OUT = 1.05;
const vec3 INK = vec3(0.102, 0.071, 0.039);
const vec3 IVORY = vec3(0.929, 0.886, 0.784);
const vec3 WIND = vec3(0.914, 0.867, 0.749);
const vec3 BRONZE = vec3(0.659, 0.455, 0.227);
const vec3 BRONZE_LIT = vec3(0.851, 0.647, 0.369);
const vec3 HUB = vec3(0.941, 0.541, 0.165);
const vec3 XP = vec3(1.0, 0.914, 0.659);

instance uniform vec4 sig_a = vec4(1.0, 0.0, 0.0, 1.0);   // level shown, face (0 wheel, 1 gong), theta (rad), alpha
instance uniform vec4 sig_b = vec4(0.0, 0.0, 1.0, 1.0);   // XP ratio, XP arc alpha, scale, value
instance uniform vec4 team : source_color = vec4(1.0);

float band(float r, float a, float b, float aa) {
	return smoothstep(a - aa, a + aa, r) * (1.0 - smoothstep(b - aa, b + aa, r));
}

vec4 over(vec4 dst, vec3 c, float a) {
	float oa = a + dst.a * (1.0 - a);
	vec3 rgb = oa > 0.0001 ? (c * a + dst.rgb * dst.a * (1.0 - a)) / oa : vec3(0.0);
	return vec4(rgb, oa);
}

void fragment() {
	vec2 p = (UV * 2.0 - 1.0) * HALF / max(sig_b.z, 0.01);
	float r = length(p);
	float aa = max(fwidth(r), 0.004) * 1.2;
	float ang = atan(p.x, -p.y);                 // from screen-up, clockwise
	if (ang < 0.0) {
		ang += TAU;
	}
	float level = sig_a.x;
	bool gong = sig_a.y > 0.5;
	float theta = sig_a.z;
	float value = sig_b.w;
	vec3 tc = team.rgb;
	float tv = max(max(tc.r, tc.g), tc.b);
	tc *= tv < 0.6 ? 0.6 / max(tv, 0.01) : 1.0;   // segments keep a value of at least 60 %

	vec4 acc = vec4(0.0);
	acc = over(acc, INK, 0.12 * (1.0 - smoothstep(BAND_IN - aa, BAND_IN + aa, r)));
	if (gong) {
		for (int k = 0; k < 2; k++) {
			float s = ang - theta - float(k) * 3.14159265;
			s = mod(s, TAU) / TAU;
			float target = 0.22 + 0.52 * s;
			float w = band(r, 0.2, 0.76, aa) * (1.0 - smoothstep(0.022, 0.022 + aa * 1.5, abs(r - target)));
			acc = over(acc, WIND, 0.3 * w);
		}
	} else {
		float sa = mod(ang - theta, TAU / 6.0);
		float sd = min(sa, TAU / 6.0 - sa) * r;
		float spoke = band(r, 0.18, 0.80, aa) * (1.0 - smoothstep(0.03, 0.03 + aa * 1.5, sd));
		acc = over(acc, IVORY, 0.35 * spoke);
		acc = over(acc, HUB * (0.8 + 0.2 * value), 0.9 * (1.0 - smoothstep(0.13 - aa, 0.13 + aa, r)));
	}
	// the band: an ink outline under ten segments, lit by level
	acc = over(acc, INK, 0.8 * band(r, BAND_IN - 0.03, BAND_OUT + 0.03, aa));
	float seg_w = TAU / 10.0;
	float seg = floor(ang / seg_w);
	float within = ang - seg * seg_w;
	float gap = level >= 9.5 ? 1.0 : smoothstep(radians(2.0) * r - aa, radians(2.0) * r + aa, min(within, seg_w - within) * r);
	float lit = seg < level - 0.5 ? 1.0 : 0.3;
	vec3 seg_col = gong ? (lit > 0.5 ? BRONZE_LIT : BRONZE * 0.3) : tc * lit;
	acc = over(acc, seg_col * value, band(r, BAND_IN, BAND_OUT, aa) * gap);
	// ownership: the kingdom's inner rim, the Tormai felt stripe on the outer edge
	float own = gong ? band(r, BAND_OUT - 0.05, BAND_OUT, aa) : band(r, BAND_IN, BAND_IN + 0.05, aa);
	acc = over(acc, tc * value, own);
	// the XP arc (own heroes): from screen-up, clockwise, length = XP ratio
	float xp_arc = band(r, BAND_OUT + 0.035, BAND_OUT + 0.1, aa) * step(ang, sig_b.x * TAU);
	acc = over(acc, XP, 0.85 * sig_b.y * xp_arc);
	ALBEDO = acc.rgb;
	ALPHA = acc.a * sig_a.w;
}
