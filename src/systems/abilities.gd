class_name AbilitySystem
extends SimSystem
## Abilities (owner: agent C; rules.md §6.5, §10; data: abilities.json, buffs.json ground_effects).
## Stage: abilities. Responsibilities:
##   - who can cast what: hero ranks (HeroSystem.rank_of), unit abilities unlocked by research
##     (Tech.ability_unlocked), mana, cooldowns (Unit.cooldowns: id -> ready tick), silence
##   - the cast sequence driven from orders/cast.gd: cast point (mana and cooldown spent at the
##     cast point), effect, backswing; channels; cancel rules (rules §6.5)
##   - effect scripts (EffectRegistry: src/systems/abilities/effects/<effect>.gd) with a
##     CastContext; smart casting (one caster of a subgroup), autocast (Herb Poultice, Wind at
##     Your Back, Repair / Mend), creep spell AI (neutrals §1.7, with CreepSystem)
##   - building abilities cast without an order (Levy Horn, Sound the Gong, Unload All)
##   - ground effects (Naphtha fire, Smoke Pot, Swallowed Sun, Loose Straw, hail patches)
## Signals (Events): ability_cast(caster, id, rank, target_unit, target_pos),
##   cast_started(caster, id), cast_cancelled(caster, id), autocast_changed(unit, id, on),
##   ground_effect_added(handle, id, pos, radius).
## Commands handled: "autocast" {units, ability, on}, "cast" for structures {units: [building],
##   ability, target?, pos?} (mobile casters get a CAST order instead).
## Called by: orders/cast.gd (can_order_cast, cast_range, begin_cast, cast_tick, cancel_cast),
##   HUD (is_ready, cooldown_left, rank_of for the card), AI, ItemSystem (shared execute).

var _ground: Array[Dictionary] = []   ## {handle, id, owner_id, player, pos, radius, ticks, values}
var _next_handle: int = 1


## Rank of `ability_id` for `u`: hero rank, or 1 for an unlocked unit / building ability, else 0.
func rank_of(u: Unit, ability_id: String) -> int:
	if u.is_hero and (u.def.get("hero_abilities", []) as Array).has(ability_id):
		return world.heroes.rank_of(u, ability_id)
	if u.abilities.has(ability_id) and world.tech.ability_unlocked(u.player_id, ability_id):
		return 1
	return 0


## Resolved numbers of the caster's current rank (Defs.ability_rank).
func values_for(u: Unit, ability_id: String) -> Dictionary:
	return Defs.ability_rank(ability_id, maxi(1, rank_of(u, ability_id)))


func is_ready(u: Unit, ability_id: String) -> bool:
	return world.tick_count >= int(u.cooldowns.get(ability_id, 0))


func cooldown_left(u: Unit, ability_id: String) -> float:
	return maxf(0.0, (int(u.cooldowns.get(ability_id, 0)) - world.tick_count) * World.DT)


## CAST order validation on issue.
func can_order_cast(u: Unit, o: Order) -> bool:
	var a := Defs.ability(o.ability)
	if a.is_empty() or ["passive", "aura", "command"].has(str(a.get("type", ""))):
		return false
	if rank_of(u, o.ability) <= 0 or u.silenced or not is_ready(u, o.ability):
		return false
	return u.mana >= float(values_for(u, o.ability).get("mana", 0.0))


## Cast range in metres; < 0 means anywhere (no approach): instant abilities and range -1.
func cast_range(u: Unit, ability_id: String) -> float:
	var a := Defs.ability(ability_id)
	if str(a.get("type", "")) == "instant" or str(a.get("type", "")) == "toggle":
		return -1.0
	return float(values_for(u, ability_id).get("range", 0.0))


## The caster is in range and facing: start the cast. Return true to keep the order (set
## o.data["phase"], then cast_tick runs each tick). Stub: casts at once and returns false.
func begin_cast(u: Unit, o: Order) -> bool:
	var target := world.get_unit(o.target_id) if o.target_id != 0 else null
	cast_now(u, o.ability, target, o.target_pos)
	return false


func cast_tick(u: Unit, _o: Order, _dt: float) -> Vector3:
	u.finish_order()
	return Vector3.ZERO


## The CAST order ended before or during its cast (rules §6.5: before the cast point nothing is
## spent). Stub: nothing to undo.
func cancel_cast(_u: Unit, _o: Order) -> void:
	pass


## Spends mana, starts the cooldown and runs the effect now. False (nothing spent) when the
## caster cannot cast it.
func cast_now(caster: Unit, ability_id: String, target: Unit = null, pos: Vector3 = Vector3.ZERO) -> bool:
	var rank := rank_of(caster, ability_id)
	if rank <= 0 or not is_ready(caster, ability_id):
		return false
	var v := Defs.ability_rank(ability_id, rank)
	var mana_cost := float(v.get("mana", 0.0))
	if caster.mana < mana_cost:
		return false
	if not execute(caster, ability_id, rank, target, pos):
		return false
	caster.mana -= mana_cost
	caster.cooldowns[ability_id] = world.tick_count + roundi(float(v.get("cooldown", 0.0)) * World.TICK_RATE)
	return true


## Runs the ability's effect script. Returns the effect's result.
func execute(caster: Unit, ability_id: String, rank: int, target: Unit = null, pos: Vector3 = Vector3.ZERO) -> bool:
	var a := Defs.ability(ability_id)
	var eff := EffectRegistry.get_effect(str(a.get("effect", "")))
	if eff == null:
		return false
	var ctx := CastContext.make(world, caster, ability_id, rank, Defs.ability_rank(ability_id, rank), target, pos)
	var ok := eff.cast(ctx)
	if ok:
		Events.ability_cast.emit(caster, ability_id, rank, target, ctx.target_pos)
	return ok


func set_autocast(u: Unit, ability_id: String, on: bool) -> void:
	if not Defs.ability(ability_id).has("autocast"):
		return
	u.autocast[ability_id] = on
	Events.autocast_changed.emit(u, ability_id, on)


func is_autocast(u: Unit, ability_id: String) -> bool:
	return bool(u.autocast.get(ability_id, (Defs.ability(ability_id).get("autocast", {}) as Dictionary).get("default", false)))


## Adds a ground effect; returns its handle. Ticking (DoTs, aura buffs, vision) is this system's.
func add_ground_effect(effect_id: String, owner: Unit, pos: Vector3, radius: float, duration: float,
		values: Dictionary = {}) -> int:
	var h := _next_handle
	_next_handle += 1
	_ground.append({"handle": h, "id": effect_id, "owner_id": owner.id if owner != null else 0,
		"player": owner.player_id if owner != null else -1, "pos": pos, "radius": radius,
		"ticks": maxi(1, roundi(duration * World.TICK_RATE)), "values": values})
	Events.ground_effect_added.emit(h, effect_id, pos, radius)
	return h


func ground_effects() -> Array[Dictionary]:
	return _ground


func sim_tick(_w: World, _dt: float) -> void:
	var i := _ground.size() - 1
	while i >= 0:
		_ground[i]["ticks"] = int(_ground[i]["ticks"]) - 1
		if int(_ground[i]["ticks"]) <= 0:
			_ground.remove_at(i)
		i -= 1


func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
	var ability_id := str(cmd.get("ability", ""))
	match str(cmd.get("type", "")):
		"autocast":
			for u in units:
				set_autocast(u, ability_id, bool(cmd.get("on", true)))
			return true
		"cast":
			var ok := false
			var target := world.get_unit(int(cmd.get("target", 0)))
			for u in units:
				ok = cast_now(u, ability_id, target, cmd.get("pos", Vector3.ZERO)) or ok
			return ok
	return false
