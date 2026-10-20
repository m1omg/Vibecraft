class_name FeelConstants
extends Resource
## Every global juice tuning number in one place (juice bible §4.8). A number in a juice row
## lives either in the unit's fx sheet (data/fx_units.json, per entity: mass, material, motion)
## or here (global). Designers tune data/feel/feel_default.tres without touching code;
## `validate()` asserts the legal ranges (tests/unit/test_juice.gd).
## Access: `FeelConstants.c()` (loaded once, `reload()` to hot-reload).

const DEFAULT_PATH := "res://data/feel/feel_default.tres"

static var _current: FeelConstants

@export_group("Time")
@export var freq_cap_hz: float = 12.0
@export var motion_freq_target_hz: float = 7.5
@export var latched_peak_ms: float = 60.0

@export_group("Readability")
@export var unit_flash_lum_max: float = 0.95
@export var rim_cap: float = 0.6
@export var cosmetic_ring_r_max_m: float = 1.6
@export var cosmetic_ring_alpha_max: float = 0.35
@export var occlusion_max_ms: float = 80.0
@export var body_offset_max_m: float = 0.20
@export var small_hit_frac: float = 0.02          ## hits under this share of max HP flash at 0.5

@export_group("Density")
@export var busy_enter: float = 14.0
@export var busy_exit: float = 10.0
@export var brawl_enter: float = 36.0
@export var brawl_exit: float = 28.0
@export var spark_mult_calm: float = 1.0
@export var spark_mult_busy: float = 0.6
@export var spark_mult_brawl: float = 0.35
@export var spawn_budget_per_frame: int = 64
@export var queue_records: int = 512
@export var near_m: float = 28.0
@export var far_m: float = 45.0

@export_group("Motion")
@export var juice_g: float = 25.0
@export var ripple_step_ms: float = 28.0
@export var ripple_cap_ms: float = 308.0
@export var nod_min_gap_ms: float = 450.0
@export var ack_min_gap_ms: float = 700.0

@export_group("Locomotion")
@export var walk_enter_ratio: float = 0.35
@export var walk_enter_ms: float = 80.0
@export var idle_enter_ratio: float = 0.12
@export var idle_enter_ms: float = 120.0
@export var pushoff_deg: float = 9.0
@export var pushoff_ms: float = 90.0
@export var cruise_omega: float = 12.0
@export var cruise_zeta: float = 0.5
@export var stop_deg: float = 8.0
@export var stop_ms: float = 70.0
@export var stop_omega: float = 14.0
@export var stop_zeta: float = 0.4
@export var stop_squash: float = 0.94
@export var stop_squash_ms: float = 140.0
@export var bank_k: float = 0.07
@export var bank_max_deg: float = 10.0
@export var bank_omega: float = 10.0
@export var bank_zeta: float = 0.7
@export var yaw_rate_damp: float = 20.0
@export var footstep_dust: bool = true
@export var footstep_dust_max_m: float = 32.0     ## no step dust beyond this from the camera focus

@export_group("Knockback")
@export var knock_max_m: float = 0.18
@export var knock_tilt_per_m: float = 1.2
@export var tremble_m: float = 0.035
@export var tremble_ms: float = 90.0
@export var tremble_hz: float = 12.0
@export var hitstop_hero_bonus_ms: float = 10.0
@export var hitstop_max_frac: float = 0.35
@export var death_beat_ms: float = 60.0

@export_group("Selection and orders")
@export var sel_pop_peak: float = 1.06
@export var sel_pop_in_ms: float = 70.0
@export var sel_pop_settle_ms: float = 90.0
@export var sel_alpha_in_ms: float = 60.0
@export var sel_thick_peak: float = 1.4
@export var sel_thick_ms: float = 160.0
@export var sel_paint_ms_per_10px: float = 4.0
@export var sel_paint_cap_ms: float = 140.0
@export var desel_ms: float = 110.0
@export var pulse_scale: float = 1.22
@export var pulse_up_ms: float = 60.0
@export var pulse_down_ms: float = 120.0
@export var pulse_tint_ms: float = 180.0
@export var hover_alpha: float = 0.45
@export var hover_rim: float = 0.35
@export var ripple_ms: float = 420.0
@export var ripple_stagger_ms: float = 70.0
@export var pin_drop_ms: float = 160.0
@export var pin_hold_ms: float = 450.0
@export var pin_shrink_ms: float = 180.0
@export var marker_pool: int = 8
@export var tap_window_ms: float = 250.0
@export var tap_radius_m: float = 1.5
@export var waypoint_show_ms: float = 1400.0
@export var rally_wobble_deg: float = 9.0

@export_group("Health bars")
@export var ghost_hold_ms: float = 400.0
@export var ghost_damp: float = 7.0
@export var ghost_min_rate: float = 0.25
@export var bar_flash_ms: float = 70.0

@export_group("Camera")
@export var pan_accel_k: float = 16.0
@export var pan_stop_k: float = 22.0
@export var edge_dwell_ms: float = 50.0
@export var zoom_k: float = 14.0
@export var zoom_kick_omega: float = 16.0
@export var zoom_kick_v: float = 1.2              ## end-stop kick v0 = this × distance (m/s)
@export var pitch_slope: float = -0.3626           ## deg per m around the default distance
@export var pitch_curve: float = 0.004712          ## deg per m²
@export var trauma_cap_combat: float = 0.35
@export var trauma_cap_ability: float = 0.5
@export var trauma_cap_cinematic: float = 1.0
@export var trauma_cap_total: float = 0.6
@export var trauma_decay: float = 1.6
@export var shake_hz: float = 14.0
@export var shake_translation_m: float = 0.9
@export var shake_roll_deg: float = 1.2
@export var kick_omega: float = 28.0
@export var kick_zeta: float = 0.32
@export var kick_amp_m: float = 0.5
@export var precision_factor: float = 0.3

@export_group("Audio")
@export var what_gap_ms: float = 400.0
@export var yes_gap_ms: float = 1000.0
@export var annoyed_clicks: int = 5
@export var annoyed_window_ms: float = 2500.0
@export var order_tick_gap_ms: float = 60.0
@export var cull_distance_m: float = 50.0
@export var one_shot_pool: int = 24
@export var ui_pool: int = 8
@export var default_peak_ms: float = 120.0

@export_group("Text")
@export var text_min_px: float = 13.0
@export var text_merge_ms: float = 250.0
@export var heal_min: float = 10.0
@export var popup_life_s: float = 1.0
@export var popup_rise_px: float = 40.0
@export var popup_cap: int = 48

@export_group("Missiles")
@export var stuck_life_s: float = 6.0
@export var stuck_sink_s: float = 0.4
@export var stuck_cap: int = 64
@export var trail_s: float = 0.07
@export var trail_max_m: float = 1.4


## The active constants (data/feel/feel_default.tres, else the code defaults).
static func c() -> FeelConstants:
	if _current == null:
		reload()
	return _current


static func reload(path: String = DEFAULT_PATH) -> void:
	var res: Resource = null
	if ResourceLoader.exists(path):
		res = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE)
	_current = res as FeelConstants if res is FeelConstants else FeelConstants.new()


static func use(fc: FeelConstants) -> void:
	_current = fc


## Range violations (empty = legal), bible §4.8 "legal range" column.
func validate() -> PackedStringArray:
	var out := PackedStringArray()
	if freq_cap_hz > 12.0:
		out.append("freq_cap_hz > 12")
	if motion_freq_target_hz > 7.5:
		out.append("motion_freq_target_hz > 7.5")
	if unit_flash_lum_max > 0.95:
		out.append("unit_flash_lum_max > 0.95")
	if rim_cap > 0.6:
		out.append("rim_cap > 0.6")
	if cosmetic_ring_r_max_m > 1.6 or cosmetic_ring_alpha_max > 0.35:
		out.append("cosmetic rings above 1.6 m / α 0.35")
	if occlusion_max_ms > 80.0:
		out.append("occlusion_max_ms > 80")
	if body_offset_max_m > 0.30:
		out.append("body_offset_max_m > 0.30")
	if trauma_cap_combat > 0.35 or trauma_cap_ability > 0.5 or trauma_cap_total > 0.6 or trauma_cap_cinematic > 1.0:
		out.append("trauma caps above the CAM-05 limits")
	if shake_hz > 15.0:
		out.append("shake_hz > 15")
	if tremble_hz > freq_cap_hz:
		out.append("tremble_hz above the frequency cap")
	if text_min_px < 13.0:
		out.append("text_min_px < 13")
	if ripple_cap_ms > 308.0:
		out.append("ripple_cap_ms > 308")
	if sel_paint_cap_ms > 140.0:
		out.append("sel_paint_cap_ms > 140")
	return out
