class_name CombatText
extends RefCounted
## Combat-text policy (CMB-28, juice bible §4.5): decides WHAT is printed; PopupText decides how.
## *Minimal* (the default, R24) shows only what a veteran reads at a glance:
##   - crits "N!" (an unusual hit: final damage well above the attacker's best normal roll
##     against this armour; the sim's own crit flag replaces this inference when the FND-4
##     `hit_landed` event lands);
##   - heals >= `FeelConstants.heal_min` ("+N" green);
##   - bounty "+N" with a coin, for the local player only;
##   - income "+N" gold / lumber at the drop-off, for the local player only (economy popups
##     are on at every juice level);
## and never a number on every hit, never XP. *Detailed* also prints hits dealt or taken by the
## local player's selected units; *Off* prints nothing but bounty and income.

enum Mode { OFF, MINIMAL, DETAILED }

const CRIT_RATIO := 1.45
const CRIT_KEY := 1 << 24
const HEAL_KEY := 2 << 24
const INCOME_KEY := 3 << 24

static var mode: int = Mode.MINIMAL

var popups: PopupText
var world: World
var selected: Array = []


func _init(p: PopupText, w: World) -> void:
	popups = p
	world = w


## A unit took damage (drained from Events.unit_damaged).
func on_damage(u: Unit, amount: float, src: Unit) -> void:
	if popups == null or u == null:
		return
	if is_crit(u, amount, src) and mode != Mode.OFF:
		popups.show_value(PopupText.Style.CRIT, maxi(roundi(amount), 1), u.hit_point(), u,
			CRIT_KEY + u.id, FeelConstants.c().text_merge_ms / 1000.0)
		return
	if mode == Mode.DETAILED and (selected.has(u) or selected.has(src)):
		popups.show_value(PopupText.Style.NORMAL, maxi(roundi(amount), 1), u.hit_point(), u,
			u.id, FeelConstants.c().text_merge_ms / 1000.0)


func on_heal(u: Unit, amount: float) -> void:
	if popups == null or mode == Mode.OFF or amount < FeelConstants.c().heal_min:
		return
	popups.show_value(PopupText.Style.HEAL, roundi(amount), u.hit_point(), u, HEAL_KEY + u.id,
		FeelConstants.c().text_merge_ms / 1000.0)


func on_bounty(player_id: int, amount: int, pos: Vector3) -> void:
	if popups == null or world == null or player_id != world.local_player_id or amount <= 0:
		return
	popups.show_value(PopupText.Style.GOLD, amount, pos + Vector3(0, 1.6, 0))


func on_income(player_id: int, kind: String, amount: int, pos: Vector3) -> void:
	if popups == null or world == null or player_id != world.local_player_id or amount <= 0:
		return
	if pos == Vector3.INF:
		return
	var style := PopupText.Style.LUMBER if kind == "lumber" else PopupText.Style.GOLD
	var key := INCOME_KEY + (Grid.world_to_cell(pos).x * 977 + Grid.world_to_cell(pos).y) % 65536 * 4 + (1 if kind == "lumber" else 0)
	popups.show_value(style, amount, pos + Vector3(0, 2.2, 0), null, key, 0.35)


## Inference until the sim publishes its crit flag: a melee or missile hit whose final damage
## is at least CRIT_RATIO x the attacker's best normal roll against this target's armour.
static func is_crit(u: Unit, amount: float, src: Unit) -> bool:
	if src == null or not is_instance_valid(src) or src.damage_max <= 0:
		return false
	if src.combat_target_id() != u.id:
		return false   # spells, auras and burns are not weapon hits
	var best := Combat.compute_damage(float(src.damage_max), src.attack_type, u.armor_type, u.armor)
	return amount >= best * CRIT_RATIO and amount - best >= 2.0
