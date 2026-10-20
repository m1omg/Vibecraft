shader_type spatial;
// Painted swing smear (CMB-20): a dry-brush stroke along the weapon's arc, drawn on one quad per
// live swing in the swing plane (quad x = the arc's 0° direction, y = its 90° direction).
// INSTANCE_CUSTOM: r = head angle / 180, g = tail angle / 180 (the stroke runs tail -> head, the
// head brightest), b = alpha, a = shape (0 arc, 1 thrust streak). No TIME: the CPU writes the
// reveal and fade each frame from the swing progress and the fx clock.
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix, fog_disabled;

uniform vec4 paint : source_color = vec4(0.96, 0.93, 0.86, 1.0);

varying vec4 v_c;

void vertex() {
	v_c = INSTANCE_CUSTOM;
}

float hash(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	p.y = -p.y;
	float head = v_c.r * 180.0;
	float tail = v_c.g * 180.0;
	float alpha = v_c.b;
	float a = 0.0;
	if (v_c.a < 0.5) {
		float r = length(p);
		float ang = degrees(atan(p.y, p.x));
		float lo = min(head, tail);
		float hi = max(head, tail);
		float span = max(hi - lo, 0.001);
		float k = (ang - tail) / (head - tail + sign(head - tail) * 0.001);   // 0 tail .. 1 head
		float inside = step(lo, ang) * step(ang, hi);
		// band: thick at the head, thinning to the tail; dry-brush streaks across the radius
		float inner = mix(0.9, 0.72, clamp(k, 0.0, 1.0));
		float band = smoothstep(inner - 0.03, inner + 0.03, r) * (1.0 - smoothstep(0.96, 1.0, r));
		float streak = 0.55 + 0.45 * step(0.3, hash(floor(r * 22.0)));
		float lead = 1.0 - smoothstep(0.0, 6.0, abs(ang - head));
		a = inside * band * streak * mix(0.15, 1.0, clamp(k, 0.0, 1.0) * clamp(k, 0.0, 1.0));
		a = max(a, inside * band * lead * 0.6);
	} else {
		// thrust: a tapered streak along +x from tail to head (0..1 of the radius)
		float x = (p.x * 0.5 + 0.5);
		float lo2 = v_c.g;
		float hi2 = v_c.r;
		float k2 = (x - lo2) / max(hi2 - lo2, 0.001);
		float w = 0.1 * clamp(k2, 0.0, 1.0);
		a = step(lo2, x) * step(x, hi2) * (1.0 - smoothstep(w * 0.6, w, abs(p.y))) * mix(0.2, 1.0, clamp(k2, 0.0, 1.0));
	}
	ALBEDO = paint.rgb;
	ALPHA = clamp(a * alpha, 0.0, 1.0);
}
