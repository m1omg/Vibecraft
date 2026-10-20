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
	return true


## Sells slot `slot` of `hero` to a merchant (shops.json buys_items > 0). Stub: false.
func sell(_pid: int, _shop: Unit, _hero: Unit, _slot: int) -> bool:
	return false


## Uses a service (Fair Exchange, inn revive). Stub: false.
func use_service(_pid: int, _shop: Unit, _service_id: String, _unit: Unit) -> bool:
	return false


## Restock timers (per player). Stub: no restock yet.
func sim_tick(_w: World, _dt: float) -> void:
	pass
