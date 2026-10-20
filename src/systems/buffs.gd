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
	return [&"died", &"removed"]


func on_unit_died(u: Unit, _killer: Unit) -> void:
	_units.erase(u.id)


func on_unit_removed(u: Unit) -> void:
	_units.erase(u.id)


## Applies (or refreshes) `buff_id` on `target`. `values` override the buff def (duration,
## hero_duration, modifier keys); `duration` < 0 with no duration anywhere = until removed.
## Returns the record.
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
			"rank": rank, "values": values}
		target.buffs.append(rec)
		Events.buff_applied.emit(target, buff_id)
	else:
		rec["remaining"] = ticks
		if rank >= int(rec["rank"]):
			rec["rank"] = rank
			rec["values"] = values
	_units[target.id] = true
	_push_modifiers(target)
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


## Removes dispellable buffs (rules §10.4). mode "all" or "selective" (enemy positives and ally
## negatives relative to `by_player`). Returns how many were removed. Stub: "all" only.
func dispel(target: Unit, _mode: String = "all", _by_player: int = -1) -> int:
	var n := 0
	var i := target.buffs.size() - 1
	while i >= 0:
		var id := str(target.buffs[i]["id"])
		if bool(Defs.buff(id).get("dispellable", false)):
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


func sim_tick(w: World, _dt: float) -> void:
	for uid: int in _units.keys():
		var u := w.get_unit(uid)
		if u == null:
			_units.erase(uid)
			continue
		var changed := false
		var i := u.buffs.size() - 1
		while i >= 0:
			var b: Dictionary = u.buffs[i]
			if int(b["remaining"]) > 0:
				b["remaining"] = int(b["remaining"]) - 1
				if int(b["remaining"]) == 0:
					u.buffs.remove_at(i)
					Events.buff_removed.emit(u, str(b["id"]))
					changed = true
			i -= 1
		if changed:
			_push_modifiers(u)
		if u.buffs.is_empty():
			_units.erase(uid)


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
		for s: Variant in d.get("status", []):
			if not statuses.has(s):
				statuses.append(s)
	if not statuses.is_empty():
		mods["status"] = statuses
	u.set_modifiers(&"buffs", mods)
