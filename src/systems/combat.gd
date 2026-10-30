class_name Combat
extends Node
## Damage resolution and the projectile stage (docs/architecture.md §10; rules §7.4).
##   attack = roll(min..max, flat bonuses included) x (1 + damage_pct) x crit
##   final  = attack x types[attack_type][armor_type] x armor_factor(armor) x (1 + damage_taken_pct)
## with armor_factor = 1 - a*k / (1 + a*k) for a >= 0 and 2 - 0.94^(-a) below zero (skipped for
## Spell damage); the table and k live in data/factions.json -> combat. Crits and misses are
## proc rolls (pseudo-random distribution per unit and source, rules §2.3); the attacker's
## miss_chance (blindness) makes an attack deal nothing (Events.attack_missed). Rolls use
## World.rng (seeded) and are only drawn when a chance exists, so a fight replays identically.
## Owned by World and registered for the `projectiles` stage.

const _NONE: Dictionary = {}         ## shared read-only default (no allocation per lookup)

var world: World
var projectiles: Array[Projectile] = []
var _last_alert: Dictionary = {}     ## player id -> sim time of the last "under attack" alert
var _prd: Dictionary = {}            ## "unit id:source" -> PRD failure counter N
var last_crit: bool = false          ## the latest fire() crit (the combat text reads it)


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


## A proc roll for `u` from `source` at nominal chance `p` (rules §2.3): pseudo-random
## distribution (chance min(1, C × N), N counting failures since the last success) unless
## combat.proc_mode is "random". Draws from World.rng only when 0 < p < 1.
func proc(u: Unit, source: String, p: float) -> bool:
	if p <= 0.0:
		return false
	if p >= 1.0:
		return true
	var r := world.rng.randf()
	if str(Defs.combat.get("proc_mode", "prd")) != "prd":
		return r < p
	var key := "%d:%s" % [u.id, source]
	var n := int(_prd.get(key, 1))
	if r < minf(1.0, Defs.prd_c(p) * n):
		_prd[key] = 1
		return true
	_prd[key] = n + 1
	return false


## Called by an attacker at its damage point: the attack's damage (roll, percent bonuses, crit;
## rules §7.4 steps 1–3), the attacker's buffs answer (breaks_on attack, on-attack riders), a
## miss roll; then melee hits immediately and ranged launches a projectile carrying the damage.
func fire(attacker: Unit, target: Unit) -> void:
	var base := roll_damage(attacker)
	var t := attacker.mod_totals
	base *= 1.0 + float(t.get("damage_pct", 0.0)) / 100.0
	last_crit = false
	var crit: Dictionary = t.get("crit", _NONE)
	if not crit.is_empty() and proc(attacker, "crit", float(crit.get("chance", 0.0))):
		base *= float(crit.get("multiplier", 1.0))
		last_crit = true
		if world.buffs != null:
			world.buffs.on_crit(attacker)
	if world.buffs != null:
		base += world.buffs.on_attack(attacker, target, base)
	if proc(attacker, "miss", float(t.get("miss_chance", 0.0))):
		Events.attack_missed.emit(attacker, target)
		return
	if world.abilities != null:
		world.abilities.on_attack(attacker, target)
	if attacker.projectile.is_empty():
		hit(attacker, target, base, attacker.attack_type)
	else:
		launch(attacker, target, base)


## Applies the type and armour multipliers (armour skipped for Spell; Hardy creeps take Spell
## as heroes) and the target's damage-taken modifiers, then deals the damage (rules §7.4 steps
## 4–7). Returns the final amount.
func hit(src: Unit, target: Unit, base: float, attack_type: String) -> float:
	if target == null or not target.alive or target.is_invulnerable:
		return 0.0
	var armor_type := target.armor_type
	if attack_type == "spell" and target.status.has("hardy"):
		armor_type = "hero"
	var dmg := base * type_multiplier(attack_type, armor_type)
	if attack_type != "spell":
		dmg *= armor_factor(target.armor)
	var taken: Dictionary = target.mod_totals.get("damage_taken_pct", _NONE)
	if not taken.is_empty():
		dmg *= maxf(0.0, 1.0 + (float(taken.get(attack_type, 0.0)) + float(taken.get("all", 0.0))) / 100.0)
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
	Events.notification.emit(pid, "under_attack", Defs.text("notify_under_attack"))


## Attack Ground (rules §7.9; owner: agent B): fire an artillery shell at a point (splash only,
## trees included, no reveal). Stub: does nothing until artillery lands.
func fire_at_point(_attacker: Unit, _point: Vector3) -> void:
	pass
