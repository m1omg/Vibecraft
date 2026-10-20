shader_type spatial;
// Decal-substitute ground mark (juice bible §4.4; no Decal node exists anywhere): flat quads
// laid on the terrain (tilted to its normal, lifted a few cm) in one MultiMesh, the shape drawn
// here. Every curve is evaluated on the CPU from (now - t0) and written as instance data, so the
// look is exact at any refresh rate without shader TIME, and identical on Forward+ and
// Compatibility (whose INSTANCE_CUSTOM is half precision: only small values live there).
// INSTANCE COLOR: rgb colour, a = alpha.
// INSTANCE_CUSTOM: r = shape id, g = band thickness (fraction of the radius), b = shape
// parameter (dash / notch count, chevron tip radius, arrow angle), a = dark outline strength.
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix, fog_disabled;

varying vec4 v_custom;

void vertex() {
	v_custom = INSTANCE_CUSTOM;
}

float band(float d, float th, float aa) {
	return smoothstep(1.0 - th - aa, 1.0 - th + aa, d) * (1.0 - smoothstep(1.0 - aa * 2.0, 1.0, d));
}

// chevron pointing at the centre along direction `dir`, tip at radius `r`
float chevron(vec2 p, vec2 dir, float r, float w) {
	vec2 perp = vec2(-dir.y, dir.x);
	float along = dot(p, dir);
	float across = abs(dot(p, perp));
	float s = along - r - across * 0.85;
	return step(0.0, s) * step(s, w) * step(across, 0.30);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float d = length(p);
	float aa = max(fwidth(d) * 1.2, 0.004);
	int shape = int(v_custom.r + 0.5);
	float th = clamp(v_custom.g, 0.02, 1.0);
	float param = v_custom.b;
	float a = 0.0;
	float core = 1.0;
	float ang = atan(p.y, p.x);
	if (shape == 0 || shape == 1 || shape == 2) {
		a = band(d, th, aa);
		core = smoothstep(1.0 - th * 0.78, 1.0 - th * 0.62, d) * (1.0 - smoothstep(1.0 - th * 0.30, 1.0 - th * 0.12, d));
		if (shape == 1) {
			// dashed ring (hover): `param` dashes, 60 % duty
			float k = fract(ang / 6.2831853 * max(param, 1.0) + 0.25);
			a *= smoothstep(0.0, 0.04, k) * (1.0 - smoothstep(0.56, 0.62, k));
		} else if (shape == 2) {
			// notched ring (hostile): `param` gaps of 12 degrees on the diagonals
			float n = max(param, 1.0);
			float k = abs(fract((ang - 0.7853982) / 6.2831853 * n + 0.5) - 0.5) * 6.2831853 / n;
			a *= smoothstep(0.085, 0.115, k);
		}
	} else if (shape == 3) {
		// soft dust ring: no edge line (cosmetic rings are edgeless, bible §4.4)
		float mid = 1.0 - th * 0.5;
		a = smoothstep(1.0 - th, mid, d) * (1.0 - smoothstep(mid, 1.0, d));
		core = 1.0;
	} else if (shape == 4) {
		// four chevrons converging on the centre (attack-move)
		float r = param;
		for (int i = 0; i < 4; i++) {
			float t = 0.7853982 + float(i) * 1.5707963;
			a = max(a, chevron(p, vec2(cos(t), sin(t)), r, 0.16));
		}
		core = 1.0 - 0.3 * step(0.5, a) * step(fract(d * 9.0), 0.2);
	} else if (shape == 5) {
		// crosshair ring + four ticks sliding in to radius `param`
		a = band(d, th, aa);
		float tick = (step(abs(p.x), 0.05) + step(abs(p.y), 0.05)) * step(param, d) * step(d, param + 0.28);
		a = max(a, clamp(tick, 0.0, 1.0));
	} else if (shape == 6) {
		// soft disc (blob shadow, ground glow)
		a = pow(clamp(1.0 - d, 0.0, 1.0), 1.5);
	} else if (shape == 7) {
		// dashed strip along UV.y (waypoint / rally route): `param` dashes
		float k = fract(UV.y * max(param, 1.0));
		float across = abs(UV.x * 2.0 - 1.0);
		a = smoothstep(0.0, 0.08, k) * (1.0 - smoothstep(0.52, 0.6, k)) * (1.0 - smoothstep(0.55, 1.0, across));
		core = 1.0 - 0.5 * smoothstep(0.35, 0.8, across);
	} else if (shape == 8) {
		// two arrowheads chasing each other round the ring (patrol), at angle `param`
		a = band(d, th * 0.5, aa) * 0.55;
		for (int i = 0; i < 2; i++) {
			float t = param + float(i) * 3.1415927;
			vec2 c = vec2(cos(t), sin(t)) * (1.0 - th * 0.5);
			vec2 tang = vec2(-sin(t), cos(t));
			vec2 q = p - c;
			float along = dot(q, tang);
			float across = abs(dot(q, vec2(cos(t), sin(t))));
			a = max(a, step(-0.26, along) * step(along, 0.0) * step(across, -along * 0.9));
		}
	} else {
		a = 1.0 - smoothstep(1.0 - aa * 2.0, 1.0, d);
	}
	vec3 col = COLOR.rgb;
	col = mix(col * mix(1.0, 0.22, v_custom.a), col, core);
	ALBEDO = col;
	ALPHA = clamp(a * COLOR.a, 0.0, 1.0);
}
