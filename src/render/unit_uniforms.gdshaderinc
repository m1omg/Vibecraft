// Fixed per-instance uniform map shared by every unit / structure material variant
// (juice bible Appendix A, R4). A variant set through set_surface_override_material or an
// overlay in material_overlay reads the same slots, so UnitView writes each value once.
//
//   0  flash       (t0 fx_time s, strength 0..1, duration s, hold s)  latched hit flash (R25)
//   1  flash_tint  rgb = tint the flash fades to (default #FF5A48)
//   2  rim_boost   extra team-rim strength: hover / select / kill-confirm (cap 0.6)
//   3  team_sat    team-colour saturation (1 live, 0.2 after the corpse ebb)
//   4  sat_front   height (m, model space) below which team_sat applies; < 0 = everywhere
//   5  status_a    hero status overlay A (reserved)
//   6  status_t    hero status overlay timing (reserved)
//   7  rim_col     rgb team rim colour (team colour x 0.6 by default), a = rim base strength
//   8  prop_sel    economy prop selector (reserved)
//   9  prop_aux    economy prop aux (reserved)
//  10  prop_anim   economy prop animation (reserved)
//  11  variant 1   structures: x = build progress 0..1 (1 = complete)
//  12  variant 2   (DISSOLVE / DITHER variants, reserved)
//  13  team_color  rgb player colour, a = 1
// Material (shared) uniforms written once per frame by RenderAtmos: fx_time, unit_fill,
// glow_energy, cloud_* (see render_atmos.gd).

instance uniform vec4 flash : instance_index(0) = vec4(-100.0, 0.0, 0.08, 0.0);
instance uniform vec4 flash_tint : instance_index(1) = vec4(1.0, 0.353, 0.282, 1.0);
instance uniform float rim_boost : instance_index(2) = 0.0;
instance uniform float team_sat : instance_index(3) = 1.0;
instance uniform float sat_front : instance_index(4) = -1.0;
instance uniform vec4 rim_col : instance_index(7) = vec4(0.0, 0.0, 0.0, 0.35);
instance uniform vec4 variant_a : instance_index(11) = vec4(1.0, 0.0, 0.0, 0.0);
instance uniform vec4 team_color : instance_index(13) = vec4(1.0, 1.0, 1.0, 1.0);

#include "res://src/render/render_common.gdshaderinc"

const vec3 FLASH_PEAK = vec3(1.0, 0.965, 0.925);   // #FFF6EC

// Latched flash curve: the hold (flash.w seconds; 0 = the default 30 ms) at full strength in
// the peak tint, then out_quad to 0 while the tint slides to flash_tint. Returns vec4(tint, f).
// The death beat holds 60 ms (MaterialFlash.death_beat).
vec4 vc_flash_curve() {
	float age = fx_time - flash.x;
	float hold = flash.w > 0.0 ? flash.w : 0.03;
	float dur = max(flash.z, hold + 0.01);
	if (age < 0.0 || age > dur || flash.y <= 0.0) {
		return vec4(0.0);
	}
	float k = clamp((age - hold) / (dur - hold), 0.0, 1.0);
	float f = 1.0 - k * (2.0 - k);   // 1 - out_quad(k)
	return vec4(mix(FLASH_PEAK, flash_tint.rgb, k), f * flash.y);
}

