class_name ItemSystem
extends SimSystem
## Items (owner: agent D; rules.md §6.8, neutrals.md §4; data: items.json, rules.items).
## Stage: abilities. Responsibilities:
##   - hero inventories (Unit.inventory: 6 slots of null or {id, charges}); heroes only carry
##     items, food power-ups act on pickup by any unit; full inventory refuses (power-ups excepted)
##   - ground items: entities of def "item_drop" (Unit.is_item, Unit.item_id / item_charges) that
##     never expire; pickup within rules.items.pickup_range, give within give_range, drop
##   - using items: targeting, ranges, charges (merge up to charge_merge_factor × base), shared
##     group cooldowns (rules.items.group_cooldown: heal / mana), unique groups, effect scripts
##     (src/systems/items/effects/<effect>.gd via EffectRegistry), recall channels
##   - permanent item stats: the "items" modifier source of the carrier (stat_bonus params) and
##     attribute bonuses through HeroSystem
##   - drops: camps' items are rolled at match start (CreepSystem) and spawned here on death;
##     dead heroes keep their items
## Signals (Events): item_picked_up(unit, item_id), item_dropped(unit, item_id, pos),
##   item_used(unit, item_id), inventory_changed(unit).
## Called by: orders/use_item.gd, pickup_item.gd, drop_item.gd (see their headers), ShopSystem
##   (give), CreepSystem (spawn_item), HUD (inventory_of, cooldown_left), AI.


func inventory_of(u: Unit) -> Array:
	return u.inventory


func free_slot(u: Unit) -> int:
	for i in u.inventory.size():
		if u.inventory[i] == null:
			return i
	return -1


## Spawns a ground item entity. charges < 0 = the item's base charges.
func spawn_item(item_id: String, pos: Vector3, charges: int = -1) -> Unit:
	var d := Defs.item(item_id)
	if d.is_empty():
		return null
	var e := world.spawn_unit("item_drop", PlayerState.NEUTRAL_PASSIVE, pos)
	if e != null:
		e.item_id = item_id
		e.item_charges = charges if charges >= 0 else int(d.get("charges", 0))
	return e


## Puts an item into a hero's inventory: identical charged purchasables merge into one slot up to
## charge_merge_factor × their base charges (neutrals §4.1), anything else takes the first free
## slot. Returns the slot, or -1 (full / not a hero).
func give(hero: Unit, item_id: String, charges: int = -1) -> int:
	if not hero.is_hero:
		return -1
	var d := Defs.item(item_id)
	var n := charges if charges >= 0 else int(d.get("charges", 0))
	if n > 0 and str(d.get("class", "")) == "purchasable":
		var cap := int(d.get("charges", 1)) * int(Defs.rule("items.charge_merge_factor", 2))
		for i in hero.inventory.size():
			var it: Variant = hero.inventory[i]
			if it != null and str(it["id"]) == item_id and int(it["charges"]) + n <= cap:
				it["charges"] = int(it["charges"]) + n
				Events.inventory_changed.emit(hero)
				return i
	var slot := free_slot(hero)
	if slot < 0:
		return -1
	hero.inventory[slot] = {"id": item_id, "charges": n}
	refresh_carrier(hero)
	Events.inventory_changed.emit(hero)
	return slot


## Permanent items count while carried (rules §6.8: different items add up): their stat params
## become the hero's "items" modifier source, their str / agi / int go to HeroSystem as item
## attributes. Called whenever the inventory changes.
func refresh_carrier(u: Unit) -> void:
	var mods := {}
	var attrs := {"str": 0, "agi": 0, "int": 0}
	for it: Variant in u.inventory:
		if it == null:
			continue
		var d := Defs.item(str(it["id"]))
		if str(d.get("class", "")) != "permanent" and str(d.get("class", "")) != "artifact":
			continue
		var p: Dictionary = d.get("params", {})
		for k: String in p:
			if attrs.has(k):
				attrs[k] = int(attrs[k]) + int(p[k])
			elif p[k] is float or p[k] is int:
				mods[k] = float(mods.get(k, 0.0)) + float(p[k])
	u.set_modifiers(&"items", mods)
	if u.is_hero and not u.hero.is_empty():
		u.hero["item_attr"] = attrs
		world.heroes.apply_attributes(u)


func is_powerup(item_id: String) -> bool:
	return str(Defs.item(item_id).get("class", "")) == "powerup"


## Heroes pick up everything (non-power-ups need a free slot); other units only power-ups whose
## tags are in rules.items.powerup_any_unit (food).
func can_pickup(u: Unit, item_entity: Unit) -> bool:
	if item_entity == null or not item_entity.is_item or u.is_item or u.is_structure():
		return false
	var d := Defs.item(item_entity.item_id)
	if u.is_hero:
		return is_powerup(item_entity.item_id) or free_slot(u) >= 0
	var any: Array = Defs.rule("items.powerup_any_unit", ["food"])
	return is_powerup(item_entity.item_id) and (d.get("tags", []) as Array).any(func(t: Variant) -> bool: return any.has(t))


## Picks the ground item up: power-ups apply at once and vanish; others go into a slot.
func pickup(u: Unit, item_entity: Unit) -> bool:
	if not can_pickup(u, item_entity):
		return false
	var iid := item_entity.item_id
	if is_powerup(iid):
		_run_effect(u, iid, null, u.pos)
	elif give(u, iid, item_entity.item_charges) < 0:
		return false
	world.remove_unit(item_entity)
	Events.item_picked_up.emit(u, iid)
	return true


## Drops slot `slot` at `pos` (items on the ground never expire).
func drop(u: Unit, slot: int, pos: Vector3) -> Unit:
	if slot < 0 or slot >= u.inventory.size() or u.inventory[slot] == null:
		return null
	var it: Dictionary = u.inventory[slot]
	u.inventory[slot] = null
	refresh_carrier(u)
	Events.inventory_changed.emit(u)
	var e := spawn_item(str(it["id"]), pos, int(it.get("charges", -1)))
	Events.item_dropped.emit(u, str(it["id"]), pos)
	return e


## Gives slot `slot` of `from` to another own hero (first free slot).
func transfer(from: Unit, slot: int, to: Unit) -> bool:
	if slot < 0 or slot >= from.inventory.size() or from.inventory[slot] == null or to.player_id != from.player_id:
		return false
	var it: Dictionary = from.inventory[slot]
	if give(to, str(it["id"]), int(it.get("charges", -1))) < 0:
		return false
	from.inventory[slot] = null
	refresh_carrier(from)
	Events.inventory_changed.emit(from)
	return true


func can_use(u: Unit, slot: int) -> bool:
	if slot < 0 or slot >= u.inventory.size() or u.inventory[slot] == null or u.silenced:
		return false
	var d := Defs.item(str(u.inventory[slot]["id"]))
	return str(d.get("class", "")) != "permanent" and cooldown_left(u, slot) <= 0.0


## Use range of the item in `slot` (m); < 0 = no target needed (instant items; a recall's point
## only chooses the hall, minimap clicks included).
func use_range(u: Unit, slot: int) -> float:
	var d := Defs.item(str(u.inventory[slot]["id"])) if slot >= 0 and slot < u.inventory.size() and u.inventory[slot] != null else {}
	if str(d.get("targeting", "instant")) == "instant" or str(d.get("effect", "")) == "recall_to_hall":
		return -1.0
	return float(d.get("range", 0.0))


func cooldown_left(u: Unit, slot: int) -> float:
	if slot < 0 or slot >= u.inventory.size() or u.inventory[slot] == null:
		return 0.0
	var d := Defs.item(str(u.inventory[slot]["id"]))
	var group := str(d.get("cooldown_group", u.inventory[slot]["id"]))
	return maxf(0.0, (int(u.cooldowns.get("item:" + group, 0)) - world.tick_count) * World.DT)


## Uses the item: runs its effect, spends a charge, starts the (group) cooldown. A recall keeps
## the USE_ITEM order through its channel (o.data["phase"], then use_tick) and spends its charge
## only on completion. Returns true to keep the order.
func use(u: Unit, slot: int, target: Unit, pos: Vector3, o: Order = null) -> bool:
	if not can_use(u, slot):
		return false
	var it: Dictionary = u.inventory[slot]
	var iid := str(it["id"])
	var d := Defs.item(iid)
	world.buffs.on_action(u, "item")
	if str(d.get("effect", "")) == "recall_to_hall" and o != null:
		o.data["phase"] = "channel"
		o.data["t"] = 0
		o.data["item"] = iid
		Events.item_used.emit(u, iid)
		return true
	if not _run_effect(u, iid, target, pos):
		return false
	_spend(u, slot, iid)
	return false


## Spends one charge of `slot` (the item leaves at 0) and starts its group cooldown.
func _spend(u: Unit, slot: int, iid: String) -> void:
	var it: Dictionary = u.inventory[slot]
	var d := Defs.item(iid)
	var group := str(d.get("cooldown_group", iid))
	var cd := float((Defs.rule("items.group_cooldown", {}) as Dictionary).get(group, d.get("cooldown", 0.0)))
	u.cooldowns["item:" + group] = world.tick_count + roundi(cd * World.TICK_RATE)
	if int(it.get("charges", 0)) > 0:
		it["charges"] = int(it["charges"]) - 1
		if int(it["charges"]) == 0:
			u.inventory[slot] = null
	if d.get("effect", "") != "recall_to_hall":
		Events.item_used.emit(u, iid)
	Events.inventory_changed.emit(u)


## The recall channel (rules §6.8): after rules.items.recall_channel the hero and up to 23 own
## non-structure units within 9.4 m (nearest first, counted now) appear beside the own finished
## hall nearest the chosen point; with no hall left it fails and keeps the charge. Only the
## owner's order or death ends it (an order cancels and keeps the charge).
func use_tick(u: Unit, o: Order, _dt: float) -> Vector3:
	o.data["t"] = int(o.data.get("t", 0)) + 1
	if int(o.data["t"]) < roundi(float(Defs.rule("items.recall_channel", 5.0)) * World.TICK_RATE):
		return Vector3.ZERO
	var at := o.target_pos if o.target_pos != Vector3.ZERO else u.pos
	var hall: Unit = null
	for b in world.unit_list:
		if b.alive and b.player_id == u.player_id and b.has_flag("town_hall") and not b.under_construction \
				and (hall == null or Grid.flat_dist(b.pos, at) < Grid.flat_dist(hall.pos, at)):
			hall = b
	if hall != null and o.slot >= 0 and o.slot < u.inventory.size() and u.inventory[o.slot] != null:
		var r := float(Defs.rule("items.recall_radius", 9.4))
		var cap := int(Defs.rule("items.recall_max_units", 23))
		var band: Array[Unit] = []
		for m: Unit in world.query_radius(u.pos, r + world.max_unit_radius):
			if m != u and m.alive and m.player_id == u.player_id and m.is_mobile() and not m.hidden \
					and Grid.flat_dist(m.pos, u.pos) <= r:
				band.append(m)
		band.sort_custom(func(a: Unit, b: Unit) -> bool:
			var da := Grid.flat_dist(a.pos, u.pos)
			var db := Grid.flat_dist(b.pos, u.pos)
			return da < db if da != db else a.id < b.id)
		band.resize(mini(band.size(), cap))
		var spot := world.production.spawn_point(hall, hall.rally_pos)
		var moved: Array[Unit] = [u]
		moved.append_array(band)
		for i in moved.size():
			var a := TAU * float(i) / maxf(float(moved.size()), 1.0)
			var ring := 0.0 if i == 0 else 1.2 + 0.4 * float(i / 8)
			if moved[i] != u:
				moved[i].clear_orders()
			moved[i].teleport(spot + Vector3(cos(a), 0.0, sin(a)) * ring)
		_spend(u, o.slot, str(o.data.get("item", "")))
		Events.recall_completed.emit(u, hall, moved.size())
	u.finish_order()
	return Vector3.ZERO


func cancel_use(_u: Unit, o: Order) -> void:
	o.data.erase("phase")


func _run_effect(u: Unit, item_id: String, target: Unit, pos: Vector3) -> bool:
	var d := Defs.item(item_id)
	var eff := EffectRegistry.get_effect(str(d.get("effect", "")))
	if eff == null:
		return false
	return eff.cast(CastContext.make(world, u, item_id, 1, d.get("params", {}), target, pos, "item"))
