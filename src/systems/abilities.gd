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

const AURA_TICKS := 15                ## auras re-apply every 0.5 s (rules §10.3)

var _ground: Array[Dictionary] = []   ## {handle, id, owner_id, player, pos, radius, ticks, values}
var _next_handle: int = 1
var _casting: Dictionary = {}         ## unit id -> true while a CAST order is in its wind-up or channel
var _passives: Dictionary = {}        ## unit id -> {ability id: rank} of the passive buffs it carries


func hooks() -> Array[StringName]:
	return [&"died", &"removed"]


func on_unit_died(u: Unit, _killer: Unit) -> void:
	_casting.erase(u.id)
	_passives.erase(u.id)


func on_unit_removed(u: Unit) -> void:
	_casting.erase(u.id)
	_passives.erase(u.id)


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


## "" when `u` can start casting `ability_id` now (on `target` for unit-target abilities unless
## `need_target` is false, as for the card), else an error key: cannot_cast, not_learned,
## silenced, cooldown, need_mana, bad_target.
func cast_error(u: Unit, ability_id: String, target: Unit = null, need_target: bool = true) -> String:
	var a := Defs.ability(ability_id)
	if a.is_empty() or ["passive", "aura", "command"].has(str(a.get("type", ""))):
		return "cannot_cast"
	if rank_of(u, ability_id) <= 0:
		return "not_learned"
	if u.silenced or u.stunned:
		return "silenced"
	if not is_ready(u, ability_id):
		return "cooldown"
	if u.mana < float(values_for(u, ability_id).get("mana", 0.0)):
		return "need_mana"
	if need_target and str(a.get("type", "")) == "target_unit" and not target_ok(u, ability_id, target):
		return "bad_target"
	return ""


## Seconds of `ability_id`'s full cooldown at `u`'s rank (the card's sweep length).
func cooldown_total(u: Unit, ability_id: String) -> float:
	return float(values_for(u, ability_id).get("cooldown", 0.0))


## CAST order validation on issue.
func can_order_cast(u: Unit, o: Order) -> bool:
	var target := world.get_unit(o.target_id) if o.target_id != 0 else null
	return cast_error(u, o.ability, target) == ""


## Can `caster` aim `ability_id` at `t`? The def's `targets` filter (CastContext.allows), living
## and visible, never an invulnerable enemy or (unless the ability pierces) a spell-immune one.
func target_ok(caster: Unit, ability_id: String, t: Unit) -> bool:
	if t == null or not t.alive or t.hidden or t.is_item or t.is_resource:
		return false
	var ctx := CastContext.make(world, caster, ability_id, 1, {}, t)
	if not ctx.allows(t):
		return false
	if world.is_enemy(caster.player_id, t.player_id):
		if t.is_invulnerable:
			return false
		if t.has_flag("spell_immune") and not Defs.ability(ability_id).get("pierces_immunity", false):
			return false
	return true


## Cast range in metres; < 0 means anywhere (no approach): instant abilities and range -1.
func cast_range(u: Unit, ability_id: String) -> float:
	var a := Defs.ability(ability_id)
	if str(a.get("type", "")) == "instant" or str(a.get("type", "")) == "toggle":
		return -1.0
	return float(values_for(u, ability_id).get("range", 0.0))


## The caster is in range and facing: the wind-up starts (rules §6.5). The cast point (the
## ability's cast_point, default 0.3 s) passes before anything is spent; then mana and cooldown
## are spent and the effect runs; a channel (`channel` s) follows, then the backswing (default
## 0.5 s), which any new order cuts short. Returns true while the order keeps running
## (o.data["phase"]: point, channel, backswing).
func begin_cast(u: Unit, o: Order) -> bool:
	var v := values_for(u, o.ability)
	o.data["phase"] = "point"
	o.data["t"] = 0
	o.data["point"] = roundi(float(v.get("cast_point", 0.3)) * World.TICK_RATE)
	o.data["back"] = roundi(float(v.get("cast_backswing", Defs.combat_default("cast_backswing", 0.5))) * World.TICK_RATE)
	o.data["channel"] = roundi(float(v.get("channel", 0.0)) * World.TICK_RATE)
	_casting[u.id] = true
	u.anim_hint = "cast"
	Events.cast_started.emit(u, o.ability)
	if int(o.data["point"]) <= 0:
		return _release(u, o)
	return true


func cast_tick(u: Unit, o: Order, _dt: float) -> Vector3:
	o.data["t"] = int(o.data["t"]) + 1
	match str(o.data.get("phase", "")):
		"point":
			if int(o.data["t"]) >= int(o.data["point"]) and not _release(u, o):
				u.finish_order()
		"channel":
			var eff := EffectRegistry.get_effect(str(Defs.ability(o.ability).get("effect", "")))
			var keep := eff != null and eff.channel_tick(_context(u, o))
			if not keep or int(o.data["t"]) >= int(o.data["channel"]):
				if eff != null:
					eff.channel_end(_context(u, o), false)
				_casting.erase(u.id)
				o.data["phase"] = "backswing"
				o.data["t"] = 0
		"backswing":
			if int(o.data["t"]) >= int(o.data["back"]):
				u.finish_order()
	return Vector3.ZERO


## The cast point: the target must still be valid, then cast_now spends and runs the effect.
func _release(u: Unit, o: Order) -> bool:
	var target := world.get_unit(o.target_id) if o.target_id != 0 else null
	if o.target_id != 0 and not target_ok(u, o.ability, target):
		return false
	if not cast_now(u, o.ability, target, o.target_pos):
		return false
	o.data["t"] = 0
	if int(o.data["channel"]) > 0:
		o.data["phase"] = "channel"
	else:
		o.data["phase"] = "backswing"
		_casting.erase(u.id)
	return true


func _context(u: Unit, o: Order) -> CastContext:
	var rank := maxi(1, rank_of(u, o.ability))
	var target := world.get_unit(o.target_id) if o.target_id != 0 else null
	return CastContext.make(world, u, o.ability, rank, Defs.ability_rank(o.ability, rank), target, o.target_pos)


## The CAST order ended (a new order, a stun, death). Before the cast point nothing was spent
## (rules §6.5); a channel stops (its effect's channel_end); a backswing just ends.
func cancel_cast(u: Unit, o: Order) -> void:
	_casting.erase(u.id)
	if u.anim_hint == "cast":
		u.anim_hint = ""
	match str(o.data.get("phase", "")):
		"point":
			Events.cast_cancelled.emit(u, o.ability)
		"channel":
			var eff := EffectRegistry.get_effect(str(Defs.ability(o.ability).get("effect", "")))
			if eff != null:
				eff.channel_end(_context(u, o), true)
			Events.cast_cancelled.emit(u, o.ability)
	o.data.erase("phase")


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
	world.buffs.on_action(caster, "cast")
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


func sim_tick(w: World, _dt: float) -> void:
	# a stun or silence cancels a wind-up or channel (rules §6.5, §10.2); queued orders go on
	for uid: int in _casting.keys():
		var u := w.get_unit(uid)
		if u == null or not u.alive:
			_casting.erase(uid)
		elif (u.stunned or u.silenced) and u.current != null and u.current.type == Order.Type.CAST:
			u.finish_order()
	if w.tick_count % AURA_TICKS == 0:
		_emit_auras(w)
	var i := _ground.size() - 1
	while i >= 0:
		_ground[i]["ticks"] = int(_ground[i]["ticks"]) - 1
		if int(_ground[i]["ticks"]) <= 0:
			_ground.remove_at(i)
		i -= 1


## Every living unit with a learned aura re-applies its buff to the units its filter allows within
## the aura's area, lasting the linger time (rules §10.3: 0.5 s refresh, 2 s linger, the same
## aura from two emitters keeps the highest rank, auras ignore fog). Passives (Clean Cut) are
## permanent buffs carrying their rank's values, re-applied when the rank changes.
func _emit_auras(w: World) -> void:
	var linger := float(Defs.rule("status.aura_linger", 2.0))
	for u in w.unit_list:
		if not u.alive or not u.is_hero or u.hidden:
			continue
		for aid: Variant in u.def.get("hero_abilities", []):
			var a := Defs.ability(str(aid))
			var kind := str(a.get("type", ""))
			if kind != "aura" and kind != "passive":
				continue
			var rank := rank_of(u, str(aid))
			if rank <= 0:
				continue
			var v := Defs.ability_rank(str(aid), rank)
			var buff := str(v.get("buff", ""))
			if buff == "":
				continue
			var vals := v.duplicate()
			vals["rank"] = rank
			vals["source_ability"] = str(aid)
			if kind == "passive":
				if int((_passives.get(u.id, {}) as Dictionary).get(str(aid), 0)) != rank:
					(_passives.get_or_add(u.id, {}) as Dictionary)[str(aid)] = rank
					w.buffs.apply(u, buff, u, vals, -1.0)
				continue
			var ctx := CastContext.make(w, u, str(aid), rank, v)
			for t in AbilityEffect.units_in_area(ctx, u.pos, float(v.get("area", 9.0))):
				w.buffs.apply(t, buff, u, vals, linger)


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
