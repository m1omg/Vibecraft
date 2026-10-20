class_name Combat
extends Node
## Damage resolution and the projectile stage (docs/architecture.md §10).
##   final = roll(min..max) x types[attack_type][armor_type] x armor_factor(armor)
## with armor_factor = 1 - a*k / (1 + a*k) for a >= 0 and 2 - 0.94^(-a) below zero; the table
## and k live in data/factions.json -> combat. Rolls use World.rng (seeded), so a fight replays
## identically. Owned by World and registered for the `projectiles` stage.

const _NONE: Dictionary = {}         ## shared read-only default (no allocation per lookup)

var world: World
var projectiles: Array[Projectile] = []
var _last_alert: Dictionary = {}     ## player id -> sim time of the last "under attack" alert


func setup(w: World) -> void:
	world = w
	name = "Combat"


static func type_multiplier(attack_type: String, armor_type: String) -> float:
	var row: Dictionary = (Defs.combat.get("types", _NONE) as Dictionary).get(attack_type, _NONE)
	return float(row.get(armor_type, 1.0))


static func armor_factor(armor_value: float) -> float:
	if armor_value >= 0.0:
		var ak := armor_value * float(Defs.combat.get("armor_k", 0.06))
		return 1.0 - ak / (1.0 + ak)
	return 2.0 - pow(0.94, -armor_value)


static func compute_damage(base: float, attack_type: String, armor_type: String, armor_value: float) -> float:
	return base * type_multiplier(attack_type, armor_type) * armor_factor(armor_value)


func roll_damage(attacker: Unit) -> float:
	return float(world.rng.randi_range(attacker.damage_min, attacker.damage_max))


## Called by an attacker at its damage point: melee hits immediately, ranged launches a
## projectile carrying the rolled base damage.
func fire(attacker: Unit, target: Unit) -> void:
	var base := roll_damage(attacker)
	if attacker.projectile.is_empty():
		hit(attacker, target, base, attacker.attack_type)
	else:
		launch(attacker, target, base)


## Applies type/armor modifiers and deals the damage. Returns the final amount.
func hit(src: Unit, target: Unit, base: float, attack_type: String) -> float:
	if target == null or not target.alive or target.is_invulnerable:
		return 0.0
	var dmg := compute_damage(base, attack_type, target.armor_type, target.armor)
	_maybe_alert(target, src)
	target.take_damage(dmg, src)
	return dmg


func launch(src: Unit, target: Unit, base: float) -> Projectile:
	var p := Projectile.new()
	p.setup(world, src, target, base)
	projectiles.append(p)
	world.projectile_root.add_child(p)
	p.reset_physics_interpolation()
	return p


## Advances missiles; damage lands on the arrival tick. A landed missile is freed one tick
## later, after its final (impact point) transform has been rendered.
func sim_tick(_w: World, dt: float) -> void:
	var keep := 0
	for i in projectiles.size():
		var p := projectiles[i]
		if p.landed:
			p.queue_free()
			continue
		if p.sim_tick(dt) and p.hit_target:
			hit(world.get_unit(p.source_id), world.get_unit(p.target_id), p.damage, p.attack_type)
		projectiles[keep] = p
		keep += 1
	projectiles.resize(keep)


## "Under attack" alert for the victim's owner (space bar target), throttled in sim time.
func _maybe_alert(target: Unit, src: Unit) -> void:
	if src == null or target.player_id >= PlayerState.NEUTRAL_HOSTILE:
		return
	if not world.is_enemy(target.player_id, src.player_id):
		return
	var pid := target.player_id
	var interval := float(Defs.rule("alerts.advisor_cooldown", Defs.combat_default("alert_interval", 8.0)))
	if _last_alert.has(pid) and world.time - float(_last_alert[pid]) < interval:
		return
	_last_alert[pid] = world.time
	Events.alert_raised.emit(pid, target.pos)
	Events.notification.emit(pid, "under_attack", "Steel is drawn against us!")
