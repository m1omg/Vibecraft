class_name BuffSystem
extends SimSystem
## Buffs (owner: agent C; rules.md §9, §10, §11; data: buffs.json, rules.status). Stage: abilities.
## Responsibilities:
##   - buff records on Unit.buffs: {id, source_id, source_player, remaining (ticks, -1 = until
##     removed), rank, values}; same buff again refreshes (stronger rank wins), different buffs stack
##   - pushing the summed modifiers / statuses of a unit's buffs into Unit.set_modifiers("buffs")
##   - periodic effects (DoTs / HoTs every rules.status.dot_interval), breaks_on (damage,
##     attack, cast), on_expire effects (Fuse Mark explosion, Wagon Ring heal)
##   - auras (re-applied every aura_refresh, linger aura_linger, same aura: highest rank)
##   - dispel (all / selective, summon damage), hero control durations (×0.5 unless
##     hero_duration), Hardy creeps, spell immunity, invisibility and detection hooks with Fog
##   - natural regeneration (rules §9: organic 0.25 HP/s, casters 0.65 mana/s, heroes from
##     attributes; Unit.hp_regen / mana_regen) and the Hale Spring aura
## Signals (Events): buff_applied(unit, id), buff_removed(unit, id), dispelled(unit, count).
## Called by: effect scripts (apply, remove, has_buff, set_aura, dispel_area), ItemSystem,
##   CreepSystem (sleep, returning), Combat (damage_taken_pct via Unit.mod_totals), HUD.

var _units: Dictionary = {}   ## unit id -> true for units with buffs (iteration in id order)


func hooks() -> Array[StringName]:
	return [&"died", &"removed", &"damaged"]


## Damage breaks buffs with breaks_on "damage" (Salt Tea) and wakes sleepers (wake_on_damage).
func on_unit_damaged(u: Unit, _amount: float, _src: Unit) -> void:
	if u.buffs.is_empty():
		return
	var gone := false
	var i := u.buffs.size() - 1
	while i >= 0:
		var d := Defs.buff(str(u.buffs[i]["id"]))
		if (d.get("breaks_on", []) as Array).has("damage") or d.get("wake_on_damage", false):
			Events.buff_removed.emit(u, str(u.buffs[i]["id"]))
			u.buffs.remove_at(i)
			gone = true
		i -= 1
	if gone:
		_push_modifiers(u)


## The unit attacks (Combat.fire, `base` = the attack's damage): on-attack riders apply their
## buff to the target (Incendiary Wadding's burn: dps and duration from the carrying buff's
## burn_dps / burn_duration) or cleave a line behind it (Through the Tall Grass: `factor` × base
## to every enemy in a length × width strip, never the target, structures only when allowed);
## buffs that break on attack end (invisibility) and pay their `bonus_damage` into this attack and
## their opener slow on the target (Dust Veil). Returns the extra damage.
func on_attack(attacker: Unit, target: Unit, base: float = 0.0) -> float:
	if attacker.buffs.is_empty():
		return 0.0
	var extra := 0.0
	var gone := false
	for b: Dictionary in attacker.buffs.duplicate():
		var d := Defs.buff(str(b["id"]))
		var v: Dictionary = b.get("values", {})
		var rider: Dictionary = d.get("on_attack", {})
		if rider.has("apply_buff") and target != null and target.alive:
			var rv := {"dps": v.get("burn_dps", 0.0), "duration": v.get("burn_duration", 3.0)}
			apply(target, str(rider["apply_buff"]), attacker, rv)
		if rider.has("line_cleave") and target != null:
			_cleave(attacker, target, base, rider["line_cleave"])
		if (d.get("breaks_on", []) as Array).has("attack"):
			extra += float(v.get("bonus_damage", (d.get("on_break_attack", {}) as Dictionary).get("bonus_damage", 0.0)))
			var slow := str(v.get("opener_slow_buff", ""))
			if slow != "" and target != null and target.alive:
				apply(target, slow, attacker)
			attacker.buffs.erase(b)
			Events.buff_removed.emit(attacker, str(b["id"]))
			gone = true
	if gone:
		_push_modifiers(attacker)
	return extra


func _cleave(attacker: Unit, target: Unit, base: float, c: Dictionary) -> void:
	var dir := Vector2(target.pos.x - attacker.pos.x, target.pos.z - attacker.pos.z)
	if dir.length() < 0.01:
		return
	dir = dir.normalized()
	var length := float(c.get("length", 8.0))
	var half := float(c.get("width", 2.0)) * 0.5
	var mid := attacker.pos + Vector3(dir.x, 0.0, dir.y) * length * 0.5
	for u: Unit in world.query_radius(mid, length * 0.5 + half + world.max_unit_radius):
		if u == target or not u.alive or u.hidden or not attacker.is_valid_target(u):
			continue
		if u.is_structure() and not c.get("structures", false):
			continue
		var v := Vector2(u.pos.x - attacker.pos.x, u.pos.z - attacker.pos.z)
		var along := v.dot(dir)
		if along < 0.0 or along > length or absf(v.cross(dir)) > half + u.radius:
			continue
		world.combat.hit(attacker, u, base * float(c.get("factor", 1.0)), attacker.attack_type)


## A crit landed: a crit buff with a `haste_buff` (Clean Cut) hastes its carrier.
func on_crit(attacker: Unit) -> void:
	for b: Dictionary in attacker.buffs:
		var haste := str((b.get("values", {}) as Dictionary).get("haste_buff", ""))
		if haste != "" and Defs.buff(str(b["id"])).has("crit"):
			apply(attacker, haste, attacker)
			return


## The unit casts ("cast") or uses an item ("item"): buffs that break on it end.
func on_action(u: Unit, action: String) -> void:
	var gone := false
	var i := u.buffs.size() - 1
	while i >= 0:
		if (Defs.buff(str(u.buffs[i]["id"])).get("breaks_on", []) as Array).has(action):
			Events.buff_removed.emit(u, str(u.buffs[i]["id"]))
			u.buffs.remove_at(i)
			gone = true
		i -= 1
	if gone:
		_push_modifiers(u)


## Death ends every buff (rules §10.1); a buff that explodes on expiry goes off now (Fuse Mark).
func on_unit_died(u: Unit, _killer: Unit) -> void:
	_units.erase(u.id)
	for b: Dictionary in u.buffs.duplicate():
		if str((Defs.buff(str(b["id"])).get("on_expire", {}) as Dictionary).get("effect", "")) == "explode":
			_expired(u, b)


func on_unit_removed(u: Unit) -> void:
	_units.erase(u.id)


## Applies (or refreshes) `buff_id` on `target`. `values` override the buff def (duration,
## hero_duration, modifier keys, rank); `duration` < 0 with no duration anywhere = until removed.
## The same buff again refreshes it; a stronger (or equal) rank replaces the values, a weaker one
## only keeps it from running out (rules §10.1, §10.3 same aura: highest rank). Returns the record.
func apply(target: Unit, buff_id: String, source: Unit = null, values: Dictionary = {},
		duration: float = -2.0) -> Dictionary:
	var d := Defs.buff(buff_id)
	if d.is_empty() or target == null or not target.alive:
		return {}
	var secs := duration
	if secs <= -2.0:
		secs = float(values.get("duration", d.get("duration", -1.0)))
		if target.is_hero or target.has_flag("hardy"):
			if values.has("hero_duration") or d.has("hero_duration"):
				secs = float(values.get("hero_duration", d.get("hero_duration", secs)))
			elif d.has("hero_factor") and secs > 0.0:
				secs *= float(d["hero_factor"])
	var ticks := roundi(secs * World.TICK_RATE) if secs > 0.0 else -1
	var rec := get_buff(target, buff_id)
	var rank := int(values.get("rank", 1))
	if rec.is_empty():
		rec = {"id": buff_id, "source_id": source.id if source != null else 0,
			"source_player": source.player_id if source != null else -1, "remaining": ticks,
			"total_ticks": ticks, "rank": rank, "values": values}
		target.buffs.append(rec)
		Events.buff_applied.emit(target, buff_id)
	elif rank >= int(rec["rank"]):
		rec["remaining"] = ticks
		rec["total_ticks"] = ticks
		rec["rank"] = rank
		rec["values"] = values
		rec["source_id"] = source.id if source != null else 0
	elif ticks > int(rec["remaining"]) and int(rec["remaining"]) >= 0:
		rec["remaining"] = ticks       # a weaker copy never replaces, but keeps it from running out
	_units[target.id] = true
	_push_modifiers(target)
	if (d.get("status", []) as Array).has("taunt") and source != null and source.alive:
		# taunt (rules §10.2): the victim drops what it was doing and attacks the taunter
		target.clear_orders()
		target.issue_order(Order.make(Order.Type.ATTACK, source.pos, source.id))
	return rec


func remove(target: Unit, buff_id: String) -> bool:
	for i in target.buffs.size():
		if str(target.buffs[i]["id"]) == buff_id:
			target.buffs.remove_at(i)
			Events.buff_removed.emit(target, buff_id)
			_push_modifiers(target)
			return true
	return false


func has_buff(target: Unit, buff_id: String) -> bool:
	return not get_buff(target, buff_id).is_empty()


func get_buff(target: Unit, buff_id: String) -> Dictionary:
	for b: Dictionary in target.buffs:
		if str(b["id"]) == buff_id:
			return b
	return {}


## Removes dispellable buffs (rules §10.4). mode "all" or "selective" (only enemy positives and
## ally negatives relative to `by_player`). Returns how many were removed.
func dispel(target: Unit, mode: String = "all", by_player: int = -1) -> int:
	var n := 0
	var enemy := by_player >= 0 and world.is_enemy(by_player, target.player_id)
	var i := target.buffs.size() - 1
	while i >= 0:
		var id := str(target.buffs[i]["id"])
		var d := Defs.buff(id)
		var wanted := bool(d.get("dispellable", false))
		if wanted and mode == "selective":
			var positive := str(d.get("polarity", "")) == "positive"
			wanted = positive == enemy
		if wanted:
			target.buffs.remove_at(i)
			Events.buff_removed.emit(target, id)
			n += 1
		i -= 1
	if n > 0:
		_push_modifiers(target)
		Events.dispelled.emit(target, n)
	return n


func dispel_area(pos: Vector3, radius: float, mode: String = "all", by_player: int = -1) -> int:
	var n := 0
	for u: Unit in world.query_radius(pos, radius):
		n += dispel(u, mode, by_player)
	return n


## Registers / refreshes an aura emitted by `emitter` (ability id + rank). Stub: no-op.
func set_aura(_emitter: Unit, _ability_id: String, _rank: int) -> void:
	pass


func sim_tick(w: World, dt: float) -> void:
	_regenerate(w, dt)
	for uid: int in _units.keys():
		var u := w.get_unit(uid)
		if u == null or not u.alive:
			_units.erase(uid)
			continue
		var changed := false
		var i := u.buffs.size() - 1
		while i >= 0:
			if i >= u.buffs.size():
				i = u.buffs.size() - 1     # a periodic tick removed buffs (a death or a dispel)
				continue
			var b: Dictionary = u.buffs[i]
			_periodic(u, b)
			if not u.alive:
				break
			if int(b["remaining"]) > 0:
				b["remaining"] = int(b["remaining"]) - 1
				if int(b["remaining"]) == 0:
					u.buffs.erase(b)
					Events.buff_removed.emit(u, str(b["id"]))
					_expired(u, b)
					changed = true
			i -= 1
		if changed and u.alive:
			_push_modifiers(u)
		if u.buffs.is_empty():
			_units.erase(uid)


## Natural regeneration (rules §9): rate × DT per tick up to the maximum, living units only.
func _regenerate(w: World, dt: float) -> void:
	for u in w.unit_list:
		if not u.alive:
			continue
		if u.hp_regen > 0.0 and u.hp < u.max_hp:
			u.hp = minf(u.max_hp, u.hp + u.hp_regen * dt)
		if u.mana_regen > 0.0 and u.mana < u.max_mana:
			u.mana = minf(u.max_mana, u.mana + u.mana_regen * dt)


## Periodic effects (rules §10.1): every tick_interval (rules.status.dot_interval, 1 s) a DoT
## deals dps × interval of its damage type (the buff's values may set `dps`), a HoT heals
## heal_total (or restores mana_total) spread over the buff's duration.
func _periodic(u: Unit, b: Dictionary) -> void:
	var d := Defs.buff(str(b["id"]))
	var p: Dictionary = d.get("periodic", {})
	if p.is_empty():
		return
	var v: Dictionary = b.get("values", {})
	var every := maxi(1, roundi(float(v.get("tick_interval", Defs.rule("status.dot_interval", 1.0))) * World.TICK_RATE))
	b["pt"] = int(b.get("pt", 0)) + 1
	if int(b["pt"]) < every:
		return
	b["pt"] = 0
	var secs := every * World.DT
	var dps := float(v.get("dps", p.get("dps", 0.0)))
	if dps > 0.0:
		var f := float(d.get("structure_factor", 1.0)) if u.is_structure() else 1.0
		world.combat.hit(world.get_unit(int(b["source_id"])), u, dps * secs * f, str(p.get("damage_type", "spell")))
	var total := float(b.get("total_ticks", 0))
	if total <= 0.0:
		return
	var heal := float(v.get("heal_total", p.get("heal_total", 0.0)))
	if heal > 0.0:
		u.heal(heal * every / total)
	var mana := float(v.get("mana_total", p.get("mana_total", 0.0)))
	if mana > 0.0:
		u.mana = minf(u.max_mana, u.mana + mana * every / total)


## A timed buff ran out: on_expire heals (heal_max_hp_pct) or hands over to the effect script of
## the ability that applied it (`buff_expired`, e.g. Fuse Mark's explosion).
func _expired(u: Unit, b: Dictionary) -> void:
	var oe: Dictionary = Defs.buff(str(b["id"])).get("on_expire", {})
	if oe.is_empty():
		return
	var pct := float((b.get("values", {}) as Dictionary).get("end_heal_max_hp_pct", oe.get("heal_max_hp_pct", 0.0)))
	if pct > 0.0:
		u.heal(u.max_hp * pct)
	var ability := str((b.get("values", {}) as Dictionary).get("source_ability", ""))
	if oe.has("effect") and ability != "":
		var eff := EffectRegistry.get_effect(str(Defs.ability(ability).get("effect", "")))
		if eff != null:
			eff.buff_expired(world, u, b)


## Sums the modifiers and statuses of every buff on `u` into its "buffs" modifier source.
func _push_modifiers(u: Unit) -> void:
	var mods := {}
	var statuses: Array = []
	for b: Dictionary in u.buffs:
		var d := Defs.buff(str(b["id"]))
		var m: Dictionary = (d.get("modifiers", {}) as Dictionary).duplicate()
		var v: Dictionary = b.get("values", {})
		for k: String in m.keys():
			if v.has(k) and not (m[k] is Dictionary):
				m[k] = v[k]
		for k: String in m:
			if m[k] is Dictionary:
				var acc: Dictionary = mods.get_or_add(k, {})
				for kk: String in m[k]:
					acc[kk] = float(acc.get(kk, 0.0)) + float(m[k][kk])
			elif Unit.MAX_STACK_KEYS.has(k):
				mods[k] = maxf(float(mods.get(k, 0.0)), float(m[k]))
			else:
				mods[k] = float(mods.get(k, 0.0)) + float(m[k])
		if d.has("crit"):
			var c: Dictionary = (d["crit"] as Dictionary).duplicate()
			c["chance"] = float(v.get("chance", c.get("chance", 0.0)))
			c["multiplier"] = float(v.get("crit_multiplier", c.get("multiplier", 1.0)))
			if float(c["multiplier"]) > float((mods.get("crit", {}) as Dictionary).get("multiplier", 0.0)):
				mods["crit"] = c
		for s: Variant in d.get("status", []):
			if not statuses.has(s):
				statuses.append(s)
	if not statuses.is_empty():
		mods["status"] = statuses
	u.set_modifiers(&"buffs", mods)
