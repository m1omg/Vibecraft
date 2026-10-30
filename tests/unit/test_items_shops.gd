extends "res://tests/test_case.gd"
## Items and shops (src/systems/items.gd, shops.gd; rules §6.8, §16, neutrals §4–§5): permanent
## items count while carried, identical consumables merge their charges, the recall channel
## takes the hero and its band home, the first hero brings the recall item, shops sell to a hero
## in range and restock, the Fair Exchange trades on its cooldown, the inn revives at once.


func _world() -> World:
	var w := make_world(flat_map(64, 64))
	w.player(0).faction = "kingdom"
	w.player(0).gold = 5000
	w.player(0).lumber = 5000
	w.player(0).recall_grants = 0
	return w


func _hero(w: World, at: Vector3) -> Unit:
	var h := w.spawn_unit("kingdom_wheel_marshal", 0, at)
	h.set_base_stats({"hp_regen": 0.0, "mana_regen": 0.0})
	return h


func test_permanent_items_count_while_carried() -> void:
	var w := _world()
	var h := _hero(w, Vector3(20, 0, 20))
	var armor := h.armor
	var hp := h.max_hp
	w.items.give(h, "item_tin_gorget")
	assert_near(h.armor, armor + 2.0, 0.01, "the gorget: +2 armour")
	w.items.give(h, "item_plow_horse_brass")
	assert_near(h.max_hp, hp + 75.0, 0.01, "+3 STR: +75 max HP")
	w.items.drop(h, 0, h.pos)
	assert_near(h.armor, armor, 0.01, "dropped: the armour goes")


func test_consumables_merge_their_charges() -> void:
	var w := _world()
	var h := _hero(w, Vector3(20, 0, 20))
	assert_eq(w.items.give(h, "item_kingdom_linden_salve"), 0, "slot 0")
	assert_eq(w.items.give(h, "item_kingdom_linden_salve"), 0, "the second merges into it")
	assert_eq(int(h.inventory[0]["charges"]), 2, "two charges")
	assert_eq(w.items.give(h, "item_kingdom_linden_salve"), 1, "the cap is twice the base: a new slot")


func test_the_first_hero_brings_the_recall_item() -> void:
	var w := _world()
	w.player(0).recall_grants = 1
	var a := _hero(w, Vector3(20, 0, 20))
	var b := w.spawn_unit("kingdom_firewright", 0, Vector3(24, 0, 20))
	assert_eq(str(a.inventory[0]["id"]) if a.inventory[0] != null else "", "item_way_home_horn", "the first hero carries the horn")
	assert_true(b.inventory.all(func(s: Variant) -> bool: return s == null), "the second does not")


func test_recall_takes_the_band_home_after_five_seconds() -> void:
	var w := _world()
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(20, 0, 20))
	var h := _hero(w, Vector3(90, 0, 90))
	var mate := w.spawn_unit("kingdom_pavisier", 0, Vector3(93, 0, 90))
	var far := w.spawn_unit("kingdom_pavisier", 0, Vector3(110, 0, 90))
	w.items.give(h, "item_way_home_horn")
	w.issue({"type": "use_item", "player": 0, "units": [h.id], "slot": 0, "pos": Vector3(22, 0, 22)})
	w.step()
	w.issue({"type": "stop", "player": 0, "units": [h.id]})
	w.step()
	assert_true(h.inventory[0] != null, "an order in the channel keeps the charge")
	w.issue({"type": "use_item", "player": 0, "units": [h.id], "slot": 0, "pos": Vector3(22, 0, 22)})
	for i in 30 * 5 + 3:
		w.step()
	assert_lt(Grid.flat_dist(h.pos, hall.pos), 12.0, "the hero is home")
	assert_lt(Grid.flat_dist(mate.pos, hall.pos), 12.0, "with the unit beside it")
	assert_true(Grid.flat_dist(far.pos, hall.pos) > 50.0, "not the one beyond 9.4 m")
	assert_true(h.inventory[0] == null, "the charge is spent")


func test_shops_sell_to_a_hero_in_range_and_restock() -> void:
	var w := _world()
	var shop := w.spawn_unit("neutral_weighstall", PlayerState.NEUTRAL_PASSIVE, Vector3(40, 0, 40))
	var h := _hero(w, Vector3(60, 0, 60))
	assert_eq(w.shops.can_buy(0, shop, "item_rosehip_draught", h), "need_hero", "too far")
	h.teleport(Vector3(46, 0, 40))
	var gold := w.player(0).gold
	w.issue({"type": "buy", "player": 0, "units": [h.id], "target": shop.id, "def": "item_rosehip_draught"})
	w.step()
	assert_eq(w.player(0).gold, gold - 160, "paid 160")
	assert_eq(str(h.inventory[0]["id"]), "item_rosehip_draught", "in the bag")
	for i in 2:
		w.shops.buy(0, shop, "item_rosehip_draught", h)
	assert_eq(w.shops.can_buy(0, shop, "item_rosehip_draught", h), "sold_out", "three in stock, then sold out")
	for i in 45 * 30 + 2:
		w.step()
	assert_eq(w.shops.can_buy(0, shop, "item_rosehip_draught", h), "", "one back after 45 s")


func test_fair_exchange_and_the_inn_revive() -> void:
	var w := _world()
	var shop := w.spawn_unit("neutral_weighstall", PlayerState.NEUTRAL_PASSIVE, Vector3(40, 0, 40))
	var h := _hero(w, Vector3(46, 0, 40))
	assert_eq(w.shops.can_use_service(0, shop, "neutral_fair_exchange_gold", h), "not_yet", "from 3 minutes on")
	for i in 181 * 30:
		w.step()
	var lumber := w.player(0).lumber
	assert_true(w.shops.use_service(0, shop, "neutral_fair_exchange_gold", h), "trade")
	assert_eq(w.player(0).lumber, lumber + 60, "100 gold for 60 lumber")
	assert_eq(w.shops.can_use_service(0, shop, "neutral_fair_exchange_gold", h), "busy", "then its cooldown")
	var inn := w.spawn_unit("neutral_coaching_inn", PlayerState.NEUTRAL_PASSIVE, Vector3(20, 0, 50))
	w.spawn_unit("kingdom_moot_hall", 0, Vector3(10, 0, 10))
	var hid := h.id
	h.take_damage(999999.0, null)
	w.step()
	assert_eq(w.heroes.inn_revive_cost(hid), {"gold": 340, "lumber": 80}, "level 1 at the inn: 340 / 80")
	var gold := w.player(0).gold
	w.issue({"type": "service", "player": 0, "units": [], "target": inn.id, "def": "neutral_inn_revive", "hero": hid})
	w.step()
	var back: Unit = w.get_unit(w.player(0).heroes[0])
	assert_true(back != null and back.alive, "back at once")
	assert_lt(Grid.flat_dist(back.pos, inn.pos), 10.0, "at the inn")
	assert_near(back.hp, back.max_hp * 0.5, 1.0, "with half its health")
	assert_near(back.mana, 0.0, 0.1, "and no mana (one tick of regeneration)")
	assert_eq(w.player(0).gold, gold - 340, "paid")
