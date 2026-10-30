class_name ShopSystem
extends SimSystem
## Shops (owner: agent D; rules.md §16, neutrals.md §5; data: shops.json, rules.neutral).
## Stage: economy. Responsibilities:
##   - per-player stock and restock timers for every shop building (faction shops, Weighstall)
##     with on-sale-from times and hall-tier gates
##   - buying (an own hero within rules.neutral.use_range = 7.0 m of the footprint edge; the
##     item goes to the selected hero in range, else the nearest hero with a free slot, else it
##     drops at that hero's feet), selling (50 % of value, charged items pro rata, taxed)
##   - services: the Fair Exchange (shared 120 s cooldown, from 3:00), inn revive (with
##     HeroSystem), later hires; any own unit in range may use them
##   - waking sleeping camps on a purchase / service within 10 m (with CreepSystem)
## Signals (Events): item_bought(pid, shop, item_id, hero), item_sold(pid, shop, item_id),
##   stock_changed(pid, shop), service_used(pid, shop, service_id).
## Commands handled: "buy" {units: [hero], target: shop, def: item}, "sell" {units: [hero],
##   target: shop, slot}, "service" {units: [unit], target: shop, def: service id}.
## Called by: HUD (stock_of, can_buy for the shop card), AI.

var _stock: Dictionary = {}    ## "pid:shop_id" -> {item: {count, restock_ticks}}
var _service_ready: Dictionary = {}   ## "pid:cooldown group" -> tick the service is ready again


func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
	var shop := world.get_unit(int(cmd.get("target", 0)))
	if shop == null:
		return false
	var pid := int(cmd.get("player", -1))
	match str(cmd.get("type", "")):
		"buy":
			return buy(pid, shop, str(cmd.get("def", "")), units[0] if not units.is_empty() else null)
		"sell":
			return not units.is_empty() and sell(pid, shop, units[0], int(cmd.get("slot", -1)))
		"service":
			if str(cmd.get("def", "")) == "neutral_inn_revive":
				return revive_at_inn(pid, shop, int(cmd.get("hero", 0)))
			return use_service(pid, shop, str(cmd.get("def", "")), units[0] if not units.is_empty() else null)
	return false


## Edge distance from `u` to the shop footprint is within rules.neutral.use_range.
func in_use_range(u: Unit, shop: Unit) -> bool:
	return u.edge_distance(shop) <= float(Defs.rule("neutral.use_range", 7.0))


## Stock rows of `shop` for player `pid`: [{item, count, max, available (bool), hotkey}].
func stock_of(pid: int, shop: Unit) -> Array:
	var out: Array = []
	var st := _player_stock(pid, shop)
	var tiered := str(Defs.shop(shop.def_id).get("owner", "")) == "faction"
	for row: Dictionary in Defs.shop(shop.def_id).get("stock", []):
		var iid := str(row["item"])
		var ok := world.time >= float(row.get("from", 0))
		if tiered:
			ok = ok and world.tech.tier(pid) >= int(row.get("tier", 1))
		out.append({"item": iid, "count": int(st[iid]["count"]), "max": int(row["max"]),
			"available": ok, "hotkey": str(row.get("hotkey", ""))})
	return out


func _player_stock(pid: int, shop: Unit) -> Dictionary:
	var key := "%d:%d" % [pid, shop.id]
	if not _stock.has(key):
		var st := {}
		for row: Dictionary in Defs.shop(shop.def_id).get("stock", []):
			st[str(row["item"])] = {"count": int(row["max"]), "restock_ticks": 0}
		_stock[key] = st
	return _stock[key]


## "" when `pid` can buy `item_id` at `shop` now, else an error key.
func can_buy(pid: int, shop: Unit, item_id: String, hero: Unit = null) -> String:
	var row: Dictionary = {}
	for r: Dictionary in stock_of(pid, shop):
		if r["item"] == item_id:
			row = r
	if row.is_empty():
		return "not_sold"
	if not row["available"]:
		return "not_yet"
	if int(row["count"]) <= 0:
		return "sold_out"
	if bool(Defs.rule("neutral.buy_needs_hero", true)) and (hero == null or not hero.is_hero or not in_use_range(hero, shop)):
		return "need_hero"
	if not world.economy.can_afford(pid, Defs.item(item_id).get("price", {})):
		return "need_gold"
	return ""


func buy(pid: int, shop: Unit, item_id: String, hero: Unit = null) -> bool:
	if can_buy(pid, shop, item_id, hero) != "":
		return false
	world.economy.spend(pid, Defs.item(item_id).get("price", {}))
	var st := _player_stock(pid, shop)
	st[item_id]["count"] = int(st[item_id]["count"]) - 1
	if world.items.give(hero, item_id) < 0:
		world.items.spawn_item(item_id, hero.pos)
	Events.item_bought.emit(pid, shop, item_id, hero)
	Events.stock_changed.emit(pid, shop)
	if world.creeps != null and shop.player_id >= PlayerState.NEUTRAL_HOSTILE:
		world.creeps.wake_near(shop)
	return true


## Sells slot `slot` of `hero` to a merchant that buys items (shops.json buys_items: the share of
## the item's value paid). True when sold.
func sell(pid: int, shop: Unit, hero: Unit, slot: int) -> bool:
	var factor := float(Defs.shop(shop.def_id).get("buys_items", 0.0))
	if factor <= 0.0 or hero == null or not hero.is_hero or not in_use_range(hero, shop):
		return false
	if slot < 0 or slot >= hero.inventory.size() or hero.inventory[slot] == null:
		return false
	var iid := str(hero.inventory[slot]["id"])
	hero.inventory[slot] = null
	world.items.refresh_carrier(hero)
	Events.inventory_changed.emit(hero)
	world.economy.add_income(pid, "gold", floori(float(Defs.item(iid).get("value", 0)) * factor), "item_sale")
	return true


## "" when `pid` can use service `service_id` at `shop` now, else an error key.
func can_use_service(pid: int, shop: Unit, service_id: String, unit: Unit = null) -> String:
	if not (Defs.shop(shop.def_id).get("services", []) as Array).has(service_id):
		return "not_sold"
	var sv: Dictionary = Defs.services.get(service_id, {})
	if world.time < float(sv.get("from", 0.0)):
		return "not_yet"
	if bool(sv.get("needs_hero", false)) and (unit == null or not unit.is_hero or not in_use_range(unit, shop)):
		return "need_hero"
	if world.tick_count < int(_service_ready.get("%d:%s" % [pid, sv.get("cooldown_group", service_id)], 0)):
		return "busy"
	if str(sv.get("kind", "")) == "trade" and not world.economy.can_afford(pid, sv.get("give", {})):
		return "need_gold" if (sv.get("give", {}) as Dictionary).has("gold") else "need_lumber"
	return ""


## Uses a service: a Fair Exchange trade (pays `give`, receives `get`, taxed like income when
## the service says so, then its shared cooldown) or an inn revive (`unit` carries the dead
## hero's id in its place: see revive_at_inn). True when it happened.
func use_service(pid: int, shop: Unit, service_id: String, unit: Unit) -> bool:
	if can_use_service(pid, shop, service_id, unit) != "":
		return false
	var sv: Dictionary = Defs.services.get(service_id, {})
	if str(sv.get("kind", "")) == "trade":
		world.economy.spend(pid, sv.get("give", {}))
		var got: Dictionary = sv.get("get", {})
		for k: String in got:
			var src := "trade" if bool(sv.get("taxed_by_upkeep", false)) else "untaxed"
			world.economy.add_income(pid, k, int(got[k]), src)
		_service_ready["%d:%s" % [pid, sv.get("cooldown_group", service_id)]] = \
			world.tick_count + roundi(float(sv.get("cooldown", 0.0)) * World.TICK_RATE)
		if world.creeps != null:
			world.creeps.wake_near(shop)
		return true
	return false


## Inn revive (rules §6.7): instant, at the inn, for gold and lumber by the hero's level, with
## 50 % HP and no mana. True when the hero is back.
func revive_at_inn(pid: int, inn: Unit, hid: int) -> bool:
	if not (Defs.shop(inn.def_id).get("services", []) as Array).has("neutral_inn_revive"):
		return false
	var cost := world.heroes.inn_revive_cost(hid)
	var rec := world.heroes.dead_record(hid)
	if cost.is_empty() or int(rec.get("player", -1)) != pid or not world.economy.can_afford(pid, cost):
		return false
	var p := world.player(pid)
	var cap := mini(p.food_cap, int(Defs.rule("economy.food_cap", 100)))
	if p.food_used + int(Defs.unit(str(rec["def_id"])).get("cost", {}).get("food", 5)) > cap:
		return false
	world.economy.spend(pid, cost)
	var h := world.heroes.complete_revive(inn, hid, true)
	if world.creeps != null:
		world.creeps.wake_near(inn)
	return h != null


## Restock (shops.json `restock` s per item, per player): one item back each period while short.
func sim_tick(_w: World, _dt: float) -> void:
	for key: String in _stock:
		var shop := world.get_unit(int(key.get_slice(":", 1)))
		if shop == null:
			continue
		var rows := {}
		for r: Dictionary in Defs.shop(shop.def_id).get("stock", []):
			rows[str(r["item"])] = r
		var st: Dictionary = _stock[key]
		for iid: String in st:
			var row: Dictionary = rows.get(iid, {})
			if row.is_empty() or int(st[iid]["count"]) >= int(row["max"]):
				st[iid]["restock_ticks"] = 0
				continue
			st[iid]["restock_ticks"] = int(st[iid]["restock_ticks"]) + 1
			if int(st[iid]["restock_ticks"]) >= roundi(float(row.get("restock", 60.0)) * World.TICK_RATE):
				st[iid]["restock_ticks"] = 0
				st[iid]["count"] = int(st[iid]["count"]) + 1
				Events.stock_changed.emit(int(key.get_slice(":", 0)), shop)


## Seconds until the next restock of `item_id` at `shop` for `pid` (0 when full).
func restock_left(pid: int, shop: Unit, item_id: String) -> float:
	var st := _player_stock(pid, shop)
	for r: Dictionary in Defs.shop(shop.def_id).get("stock", []):
		if str(r["item"]) == item_id and int(st[item_id]["count"]) < int(r["max"]):
			return maxf(0.0, float(r.get("restock", 60.0)) - int(st[item_id]["restock_ticks"]) * World.DT)
	return 0.0
