extends "res://tests/test_case.gd"
## Every command route (docs/architecture.md §4): unit orders and their handlers, the extended
## smart right-click resolution (rules §18.2) and the building / player commands World routes to
## systems (World.SYSTEM_COMMANDS). Uses real slice defs plus the dummy_* test defs.


class ConstructionSpy extends Construction:
	var arrived: Array = []

	func on_builder_arrived(worker: Unit, o: Order) -> Unit:
		arrived.append([worker.id, o.def_id])
		return null


class ProductionSpy extends Production:
	var researched: Array = []

	func queue_research(building: Unit, upgrade_id: String) -> bool:
		researched.append([building.id, upgrade_id])
		return true


class ShopSpy extends ShopSystem:
	var calls: Array = []

	func sell(pid: int, _shop: Unit, _hero: Unit, slot: int) -> bool:
		calls.append(["sell", pid, slot])
		return true

	func use_service(pid: int, _shop: Unit, service_id: String, _unit: Unit) -> bool:
		calls.append(["service", pid, service_id])
		return true


class HeroSpy extends HeroSystem:
	var revives: Array = []

	func handle_command(cmd: Dictionary, units: Array[Unit]) -> bool:
		revives.append([str(cmd.get("type")), units.size()])
		return true


func _world() -> World:
	var w := make_world(flat_map(48, 48, 0))
	for p in w.players:
		p.gold = 5000
		p.lumber = 5000
	return w


func _cmd(w: World, type: String, units: Array, extra: Dictionary = {}) -> void:
	var ids: Array = []
	for u: Unit in units:
		ids.append(u.id)
	var c := {"type": type, "player": units[0].player_id, "units": ids}
	c.merge(extra)
	w.issue(c)


func _current(u: Unit) -> int:
	return u.current.type if u.current != null else -1


func test_basic_unit_orders_route_to_their_handlers() -> void:
	var w := _world()
	var s := w.spawn_unit("kingdom_pavisier", 0, Vector3(20, 0, 20))
	var e := w.spawn_unit("clans_grappler", 1, Vector3(40, 0, 40))
	var ally := w.spawn_unit("kingdom_pavisier", 0, Vector3(22, 0, 20))
	var cases := [["move", {"pos": Vector3(30, 0, 20)}, Order.Type.MOVE],
		["attack_move", {"pos": Vector3(30, 0, 30)}, Order.Type.ATTACK_MOVE],
		["attack", {"target": e.id}, Order.Type.ATTACK],
		["attack", {"pos": Vector3(25, 0, 25)}, Order.Type.ATTACK_MOVE],
		["patrol", {"pos": Vector3(26, 0, 20)}, Order.Type.PATROL],
		["hold", {}, Order.Type.HOLD],
		["follow", {"target": ally.id}, Order.Type.FOLLOW]]
	for c: Array in cases:
		_cmd(w, c[0], [s], c[1])
		w.step()
		assert_eq(_current(s), c[2], "%s routes to %s" % [c[0], Order.Type.keys()[c[2]]])
		assert_true(OrderHandlers.of(s.current.type) != null, "handler for %s" % c[0])
	_cmd(w, "stop", [s])
	w.step()
	assert_true(s.current == null and s.orders.is_empty(), "stop clears everything")
	for t in Order.Type.values():
		assert_true(OrderHandlers.of(t) is OrderHandler, "every order type has a handler (%s)" % Order.Type.keys()[t])


func test_gather_routes_for_mines_and_trees() -> void:
	var m := flat_map(48, 48, 0)
	m.trees.append(Vector2i(30, 10))
	m.tree_types.append(1)
	var w := make_world(m)
	var mine := w.spawn_unit("gold_mine", PlayerState.NEUTRAL_PASSIVE, Vector3(10, 0, 30))
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(20, 0, 30))
	var pav := w.spawn_unit("kingdom_pavisier", 0, Vector3(22, 0, 30))
	assert_eq(w.resolve_smart(hod, mine), Order.Type.GATHER, "worker on a mine -> gather")
	assert_eq(w.resolve_smart(pav, mine), Order.Type.MOVE, "soldier on a mine -> move")
	assert_eq(w.economy.gold_left(mine), 12000, "economy tracks the seam's gold")
	_cmd(w, "gather", [hod], {"target": mine.id})
	w.step()
	assert_eq(_current(hod), Order.Type.GATHER, "explicit gather on a mine")
	_cmd(w, "smart", [hod, pav], {"pos": Vector3(30.5, 0, 10.5)})
	w.step()
	assert_eq(_current(hod), Order.Type.GATHER, "worker right-clicking a tree gathers")
	assert_eq(int(hod.current.data.get("tree", -1)), 0, "with that tree")
	assert_eq(_current(pav), Order.Type.MOVE, "a soldier just walks there")
	_cmd(w, "gather", [hod], {"pos": Vector3(30.5, 0, 10.5)})
	w.step()
	assert_eq(int(hod.current.data.get("tree", -1)), 0, "gather at a point picks the tree")
	run_until_idle(w, [hod], 600)
	assert_true(hod.current == null, "stub gather completes on arrival")
	assert_lt(Grid.flat_dist(hod.pos, w.doodads.tree_pos(0)), 2.0, "after walking to the tree")


func test_return_cargo_route_delivers() -> void:
	var w := _world()
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(20, 0, 20))
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(32, 0, 20))
	var gold := w.player(0).gold
	hod.carry_gold = 10
	assert_eq(w.resolve_smart(hod, hall), Order.Type.RETURN_RESOURCES, "carrying worker on own hall -> return")
	_cmd(w, "smart", [hod], {"target": hall.id})
	w.step()
	assert_eq(_current(hod), Order.Type.RETURN_RESOURCES, "smart -> return order")
	run_until_idle(w, [hod], 300)
	assert_eq(hod.carry_gold, 0, "cargo delivered")
	assert_eq(w.player(0).gold, gold + 10, "into the player's stock (no upkeep at 1 food)")
	_cmd(w, "return", [hod])
	w.step()
	assert_true(hod.current == null, "nothing to return: the order ends at once")


func test_build_and_help_build_routes() -> void:
	var w := _world()
	var spy := ConstructionSpy.new()
	track(spy)
	spy.setup(w)
	var real := w.construction
	w.construction = spy
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(10, 0, 10))
	_cmd(w, "build", [hod], {"def": "kingdom_croft", "pos": Vector3(20, 0, 20)})
	w.step()
	assert_eq(_current(hod), Order.Type.BUILD, "build order accepted")
	run_until_idle(w, [hod], 300)
	assert_eq(spy.arrived, [[hod.id, "kingdom_croft"]], "construction notified on arrival")
	_cmd(w, "build", [hod], {"def": "kingdom_walled_burg", "pos": Vector3(30, 0, 30)})
	w.step()
	assert_true(hod.current == null, "upgrade-only buildings cannot be built")
	var pav := w.spawn_unit("kingdom_pavisier", 0, Vector3(12, 0, 10))
	_cmd(w, "build", [pav], {"def": "kingdom_croft", "pos": Vector3(30, 0, 30)})
	w.step()
	assert_true(pav.current == null, "only workers build")
	w.construction = real
	var site := real.start_site(0, "kingdom_croft", Vector3(30, 0, 30))
	assert_true(site.under_construction, "site under construction")
	assert_near(site.hp, site.max_hp * 0.1, 0.01, "sites start at 10 % HP")
	assert_eq(w.player(0).food_cap, 0, "no food before completion")
	assert_eq(w.resolve_smart(hod, site), Order.Type.BUILD, "worker on own site -> help build")
	assert_eq(w.resolve_smart(pav, site), Order.Type.MOVE, "soldier on own site -> move")
	real.complete_site(site)
	assert_eq(w.player(0).food_cap, 7, "the croft provides food once complete")


func test_repair_route() -> void:
	var w := _world()
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(20, 0, 20))
	var hod := w.spawn_unit("kingdom_hodman", 0, Vector3(30, 0, 20))
	var pav := w.spawn_unit("kingdom_pavisier", 0, Vector3(31, 0, 21))
	var cart := w.spawn_unit("kingdom_bombard_wagon", 0, Vector3(32, 0, 30))
	assert_eq(w.resolve_smart(hod, hall), Order.Type.MOVE, "undamaged hall -> move")
	hall.hp -= 200.0
	cart.hp -= 50.0
	assert_eq(w.resolve_smart(hod, hall), Order.Type.REPAIR, "worker on own damaged building -> repair")
	assert_eq(w.resolve_smart(hod, cart), Order.Type.REPAIR, "and on a damaged mechanical unit")
	assert_eq(w.resolve_smart(pav, hall), Order.Type.MOVE, "soldier -> move")
	assert_eq(w.resolve_smart(hod, pav), Order.Type.FOLLOW, "organic ally -> follow, never repair")
	_cmd(w, "repair", [hod], {"target": hall.id})
	w.step()
	assert_eq(_current(hod), Order.Type.REPAIR, "explicit repair")


func test_enter_garrison_route() -> void:
	var w := _world()
	var yurt := w.spawn_unit("clans_home_yurt", 0, Vector3(20, 0, 20))
	var yw := w.spawn_unit("clans_yurtwright", 0, Vector3(26, 0, 20))
	assert_eq(w.resolve_smart(yw, yurt), Order.Type.ENTER, "Yurtwright on own Home Yurt with a slot -> enter")
	_cmd(w, "smart", [yw], {"target": yurt.id})
	w.step()
	assert_eq(_current(yw), Order.Type.ENTER, "enter order")
	yurt.garrison.assign([101, 102, 103])
	assert_eq(w.resolve_smart(yw, yurt), Order.Type.MOVE, "a full yurt falls back")


func test_learn_and_cast_routes() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 20))
	var ally := w.spawn_unit("kingdom_pavisier", 0, Vector3(24, 0, 20))
	for u: Unit in [hero, ally]:
		u.set_base_stats({"hp_regen": 0.0, "mana_regen": 0.0})   # exact numbers: no regeneration
	assert_eq(int(hero.hero.get("skill_points", 0)), 1, "a new hero has one skill point")
	assert_near(hero.max_hp, 675.0, 0.01, "level-1 stats from attributes")
	_cmd(w, "move", [hero], {"pos": Vector3(21, 0, 26)})
	_cmd(w, "learn", [hero], {"ability": "kingdom_linden_balm"})
	w.step()
	assert_eq(w.heroes.rank_of(hero, "kingdom_linden_balm"), 1, "learn is instant")
	assert_eq(_current(hero), Order.Type.MOVE, "and does not interrupt the current order")
	_cmd(w, "learn", [hero], {"ability": "kingdom_the_wagon_ring"})
	w.step()
	assert_eq(w.heroes.rank_of(hero, "kingdom_the_wagon_ring"), 0, "no point / ultimate gated at level 6")
	ally.hp -= 200.0
	var before := ally.hp
	_cmd(w, "cast", [hero], {"ability": "kingdom_linden_balm", "target": ally.id})
	w.step()
	assert_eq(_current(hero), Order.Type.CAST, "cast order")
	run_until_idle(w, [hero], 200)
	assert_near(ally.hp, before + 150.0, 0.01, "Linden Balm rank 1 heals 150")
	assert_near(hero.mana, hero.max_mana - 80.0, 0.01, "mana spent")
	assert_true(not w.abilities.is_ready(hero, "kingdom_linden_balm"), "cooldown running")
	_cmd(w, "cast", [hero], {"ability": "kingdom_linden_balm", "target": ally.id})
	w.step()
	assert_true(hero.current == null, "a cast on cooldown is refused")
	_cmd(w, "cast", [ally], {"ability": "kingdom_linden_balm", "target": hero.id})
	w.step()
	assert_true(ally.current == null, "units cannot cast abilities they lack")


func test_item_routes_pickup_use_drop_give() -> void:
	var w := _world()
	var hero := w.spawn_unit("kingdom_firewright", 0, Vector3(20, 0, 20))
	var hero2 := w.spawn_unit("kingdom_wheel_marshal", 0, Vector3(20, 0, 26))
	hero.set_base_stats({"hp_regen": 0.0, "mana_regen": 0.0})   # exact numbers: no regeneration
	var pav := w.spawn_unit("kingdom_pavisier", 0, Vector3(23, 0, 20))
	var potion := w.items.spawn_item("item_rosehip_draught", Vector3(26, 0, 20))
	var berries := w.items.spawn_item("item_wild_strawberries", Vector3(26, 0, 23))
	assert_true(potion.is_item and potion.item_id == "item_rosehip_draught", "ground item entity")
	assert_eq(w.resolve_smart(hero, potion), Order.Type.PICKUP_ITEM, "hero on an item -> pick up")
	assert_eq(w.resolve_smart(pav, potion), Order.Type.MOVE, "non-hero on an item -> move")
	assert_eq(w.resolve_smart(pav, berries), Order.Type.PICKUP_ITEM, "any unit picks up food power-ups")
	_cmd(w, "smart", [hero], {"target": potion.id})
	run_until_idle(w, [hero], 300)
	assert_true(hero.inventory[0] != null and hero.inventory[0]["id"] == "item_rosehip_draught", "in slot 0")
	assert_false(is_instance_valid(potion) and w.get_unit(potion.id) != null, "ground entity removed")
	hero.hp -= 300.0
	var hp := hero.hp
	_cmd(w, "use_item", [hero], {"slot": 0})
	run_until_idle(w, [hero], 30)
	assert_near(hero.hp, hp + 260.0, 0.1, "Rosehip Draught restores 260 HP (plus a tick of regeneration)")
	assert_true(hero.inventory[0] == null, "single charge used up")
	w.items.give(hero, "item_tin_gorget")
	_cmd(w, "give_item", [hero], {"slot": 0, "target": hero2.id})
	run_until_idle(w, [hero], 300)
	assert_true(hero.inventory[0] == null and hero2.inventory[0] != null, "given to the other hero")
	_cmd(w, "drop_item", [hero2], {"slot": 0, "pos": Vector3(30, 0, 30)})
	run_until_idle(w, [hero2], 400)
	assert_true(hero2.inventory[0] == null, "dropped")
	var dropped := 0
	for u in w.unit_list:
		if u.is_item and u.item_id == "item_tin_gorget":
			dropped += 1
	assert_eq(dropped, 1, "lies on the ground")


func test_attack_ground_route() -> void:
	var w := _world()
	var cart := w.spawn_unit("kingdom_bombard_wagon", 0, Vector3(10, 0, 10))
	var pav := w.spawn_unit("kingdom_pavisier", 0, Vector3(12, 0, 10))
	_cmd(w, "attack_ground", [cart, pav], {"pos": Vector3(40, 0, 10)})
	w.step()
	assert_eq(_current(cart), Order.Type.ATTACK_GROUND, "siege accepts attack ground")
	assert_true(pav.current == null, "units without can_attack_ground refuse it")
	for i in 240:
		w.step()
	assert_true(cart.edge_distance_to_point(Vector3(40, 0, 10)) <= cart.attack_range + 0.5, "walked into range")
	assert_eq(_current(cart), Order.Type.ATTACK_GROUND, "keeps firing until ordered otherwise")


func test_building_commands_route_to_systems() -> void:
	var w := _world()
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(20, 0, 20))
	var p := w.player(0)
	var gold := p.gold
	_cmd(w, "train", [hall], {"def": "kingdom_hodman"})
	w.step()
	assert_eq(w.production.queue_of(hall).size(), 1, "train -> production queue")
	assert_eq(p.gold, gold - 70, "paid on queue")
	_cmd(w, "cancel", [hall], {"slot": 0})
	w.step()
	assert_eq(w.production.queue_of(hall).size(), 0, "cancel -> removed")
	assert_eq(p.gold, gold, "refunded")
	_cmd(w, "train", [hall], {"def": "kingdom_hodman"})
	_cmd(w, "smart", [hall], {"pos": Vector3(20, 0, 34)})
	for i in 15 * World.TICK_RATE + 2:
		w.step()
	var hods := w.units_of_player(0).filter(func(u: Unit) -> bool: return u.def_id == "kingdom_hodman")
	assert_eq(hods.size(), 1, "trained after its 15 s")
	assert_eq(p.food_used, 1, "its food counted once")
	_cmd(w, "train", [hall], {"def": "kingdom_pavisier"})
	w.step()
	assert_eq(w.production.queue_of(hall).size(), 0, "the hall cannot train a Pavisier")
	var spy := ProductionSpy.new()
	track(spy)
	spy.setup(w)
	w.production = spy
	_cmd(w, "research", [hall], {"def": "kingdom_walled_burg"})
	w.step()
	assert_eq(spy.researched, [[hall.id, "kingdom_walled_burg"]], "research -> production")


func test_shop_and_service_commands_route_to_shops() -> void:
	var w := _world()
	w.add_player(PlayerState.NEUTRAL_PASSIVE, PlayerState.NEUTRAL_PASSIVE)
	var stall := w.spawn_unit("neutral_weighstall", PlayerState.NEUTRAL_PASSIVE, Vector3(20, 0, 20))
	var hero := w.spawn_unit("clans_hero_uncut", 0, Vector3(26, 0, 20))
	var far_hero := w.spawn_unit("clans_hero_skymirror", 0, Vector3(40, 0, 40))
	var gold := w.player(0).gold
	_cmd(w, "buy", [far_hero], {"target": stall.id, "def": "item_rosehip_draught"})
	w.step()
	assert_eq(w.player(0).gold, gold, "a hero out of use range cannot buy")
	_cmd(w, "buy", [hero], {"target": stall.id, "def": "item_rosehip_draught"})
	w.step()
	assert_eq(w.player(0).gold, gold - 160, "buy -> shops (paid)")
	assert_true(hero.inventory[0] != null and hero.inventory[0]["id"] == "item_rosehip_draught", "item to the hero")
	assert_eq(w.resolve_smart(hero, stall), Order.Type.MOVE, "right-clicking a shop walks to it")
	var spy := ShopSpy.new()
	track(spy)
	spy.setup(w)
	w.shops = spy
	_cmd(w, "sell", [hero], {"target": stall.id, "slot": 0})
	_cmd(w, "service", [hero], {"target": stall.id, "def": "neutral_fair_exchange_gold"})
	w.step()
	assert_eq(spy.calls, [["sell", 0, 0], ["service", 0, "neutral_fair_exchange_gold"]], "sell and service routed")


func test_revive_autocast_and_building_cast_routes() -> void:
	var w := _world()
	var altar := w.spawn_unit("kingdom_oath_hall", 0, Vector3(20, 0, 20))
	var hall := w.spawn_unit("kingdom_moot_hall", 0, Vector3(36, 0, 20))
	var sister := w.spawn_unit("kingdom_linden_sister", 0, Vector3(30, 0, 34))
	var spy := HeroSpy.new()
	track(spy)
	spy.setup(w)
	w.heroes = spy
	_cmd(w, "revive", [altar], {"target": 1})
	w.step()
	assert_eq(spy.revives, [["revive", 1]], "revive -> heroes")
	assert_true(w.abilities.is_autocast(sister, "kingdom_herb_poultice"), "Herb Poultice autocasts by default")
	_cmd(w, "autocast", [sister], {"ability": "kingdom_herb_poultice", "on": false})
	w.step()
	assert_false(w.abilities.is_autocast(sister, "kingdom_herb_poultice"), "autocast -> abilities")
	_cmd(w, "cast", [hall], {"ability": "kingdom_levy_horn"})
	w.step()
	assert_false(w.abilities.is_ready(hall, "kingdom_levy_horn"), "a building ability casts at once (60 s cooldown)")
	assert_eq(w.resolve_smart(altar, null), Order.Type.RALLY, "producing structure -> rally")
	_cmd(w, "smart", [altar], {"pos": Vector3(30, 0, 40)})
	w.step()
	assert_eq(altar.rally_pos, Vector3(30, 0, 40), "rally set")
