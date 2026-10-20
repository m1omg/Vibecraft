shader_type spatial;
// Missile trail ribbon (CMB-24/26): one camera-facing quad per live missile, head at UV.y = 1.
// The CPU writes the segment each frame from the missile's interpolated position (closed form
// in its flight, no TIME). INSTANCE COLOR: rgb (HDR allowed: only VFX bloom), a = alpha.
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_add, fog_disabled;

void fragment() {
	float along = UV.y;
	float across = abs(UV.x * 2.0 - 1.0);
	float a = pow(along, 1.6) * (1.0 - smoothstep(0.25, 1.0, across));
	ALBEDO = COLOR.rgb;
	ALPHA = clamp(a * COLOR.a, 0.0, 1.0);
}
