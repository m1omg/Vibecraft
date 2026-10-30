class_name AiPlayer
extends SimSystem
## Computer opponent for one player (owner: agent H; rules.md §19, data: rules.ai.<difficulty>,
## factions.<id>.ai_opening from the faction build orders kingdom.md §10 / clans.md §10).
## Stage: ai. World installs one per AI player (World.add_player(..., ai = true)).
## Playtest 2 scope: a build-order opponent. Every think_interval it
##   - keeps its workers busy: rules.ai gold_workers on the main Gold Seam, the rest on the
##     nearest tree line; trains workers up to the opening's `workers`;
##   - keeps supply ahead (a supply building when free food < supply_buffer_food + 3, counting
##     sites and builders on their way);
##   - follows the opening's `steps` in order (build, hero, research, hall upgrade, `army` = start
##     army production), each when due (`at` + build_slack) and affordable, reserving the next
##     step's cost; a step that cannot start for other reasons (requirements, a hero slot) for
##     45 s is skipped; built steps re-issue when a builder fails;
##   - trains the opening's `army` mix (weights) once `army` is on, one item queued per
##     building, within the upkeep cap (upkeep_cap_before_push / _after_push);
##   - musters the army in front of its hall, defends when its units near the hall take damage,
##     pushes at `attack_food` army food (the opening's, else rules.ai; at most what the upkeep
##     cap before the push leaves beside the workers) with attack-moves on the
##     nearest enemy structure it has seen (else the enemy start) and retreats below
##     army_retreat_hp of the push's starting HP.
## Playtest 3 adds the heroes (rules §19): skill points spent at once from the hero's
## `skill_build`; abilities cast in fights through SpellAi (area on 2+ targets, heals below 60 %);
## a heal item drunk below 40 % HP; dead heroes revived at the altar as soon as gold and food
## allow; creeping along the map's `creep_route` (own-side camp copies, camps up to `max_camp`
## and at most `camp_level_ratio` × the group's levels), the group going home to heal when a
## hero drops below `hero_retreat_hp`, drops picked up after each camp; and the worker defence
## (`use_signature`): Levy Horn / Sound the Gong when 3+ enemy combat units (6+ food) close on
## its workers, released 10 s after none remain.
## It issues ONLY player command dictionaries (World.issue), sees only through its own fog and
## obeys every rule; its random choices use its own stream `rng` (seeded from the match seed ^
## 0xA1, rules §2.3). Shops, the recall item and expansions come with Playtest 4.
## Signals: none (it acts through commands; debug overlays read `state`).

const STEP_SKIP_S := 45.0
const THREAT_RANGE := 35.0
const THREAT_HOLD_S := 10.0
const PUSH_REISSUE_S := 5.0

var player_id: int = -1
var difficulty: String = "normal"
var rng := RandomNumberGenerator.new()
var state: String = "build_up"    ## build_up | army | defend | push
## Commands issued (tests, debug).
var issued: int = 0

var _next_think: int = 0
var _opening: Dictionary = {}
var _army_on: bool = false
var _skipped: Dictionary = {}       ## step index -> true
var _blocked_since: Dictionary = {} ## step index -> world.time it first waited for non-resource reasons
var _budget: Dictionary = {}        ## spendable gold / lumber this think (after reserves)
var _hall: Unit
var _mine: Unit
var _lumber_at := Vector3.INF
var _muster := Vector3.INF
var _enemy_start := Vector3.INF
var _known: Dictionary = {}         ## enemy structure id -> last seen position
var _threat_pos := Vector3.INF
var _threat_t := -100.0
var _push_hp0 := 0.0
var _last_push_cmd := -100.0
var _rallied: Dictionary = {}       ## building id -> true
var _actions: Array[int] = []       ## ticks of recent commands (APM cap)
var _route: Array = []              ## camp ids in creep order (resolved once)
var _creep_camp: String = ""        ## the camp being cleared
var _signature_on := false
var _danger_t := -100.0             ## last time enemies closed on the workers


func setup_player(w: World, pid: int, diff: String = "normal") -> void:
	setup(w)
	player_id = pid
	difficulty = diff
	rng.seed = int(w.rng.seed) ^ 0xA1 ^ (pid * 7919)
	if not Events.unit_damaged.is_connected(_on_damaged):
		Events.unit_damaged.connect(_on_damaged)


func _exit_tree() -> void:
	if Events.unit_damaged.is_connected(_on_damaged):
		Events.unit_damaged.disconnect(_on_damaged)


## Tuning row for this difficulty (rules.ai.<difficulty>).
func tuning() -> Dictionary:
	return Defs.rule("ai." + difficulty, {})


func sim_tick(w: World, _dt: float) -> void:
	if w.tick_count < _next_think:
		return
	_next_think = w.tick_count + maxi(1, roundi(float(tuning().get("think_interval", 0.5)) * World.TICK_RATE))
	think()


## One decision step.
func think() -> void:
	var p := world.player(player_id)
	if p == null or p.defeated or p.faction == "":
		return
	if _opening.is_empty():
		_opening = Defs.faction(p.faction).get("ai_opening", {})
		if _opening.is_empty():
			return        # no script for this faction (the sandbox's placeholder sides): stay passive
	if not _refresh_base(p):
		return
	_budget = {"gold": p.gold, "lumber": p.lumber}
	_assign_workers()
	_supply(p)
	_build_order()
	_train_workers()
	_train_army(p)
	_hero_care()
	_command_army()
	if state in ["creep", "push", "defend"]:
		_cast_in_fights(_army())
	if bool(tuning().get("use_signature", false)):
		_signature()


# --- base ----------------------------------------------------------------------------------

## Main hall, Gold Seam, tree line, muster point and the enemy start. False without a hall.
func _refresh_base(p: PlayerState) -> bool:
	if _hall == null or not is_instance_valid(_hall) or not _hall.alive:
		_hall = null
		for u in world.unit_list:
			if u.alive and u.player_id == player_id and u.has_flag("town_hall") and not u.under_construction:
				_hall = u
				break
		if _hall == null:
			return false
		_mine = null
		_lumber_at = Vector3.INF
		var centre := Vector3(world.map.size_world().x * 0.5, 0.0, world.map.size_world().y * 0.5)
		var out := (centre - _hall.pos)
		out.y = 0.0
		_muster = _walkable(_hall.pos + out.normalized() * 12.0)
		var far := -1.0
		for s in world.map.start_locations:
			var d := Grid.flat_dist(s, _hall.pos)
			if d > far:
				far = d
				_enemy_start = s
	if _mine == null or not is_instance_valid(_mine) or not _mine.alive or not _mine.is_resource:
		_mine = null
		var best := 30.0
		for u in world.unit_list:
			if u.alive and u.has_flag("gold_mine") and u.is_resource:
				var d := Grid.flat_dist(u.pos, _hall.pos)
				if d < best:
					best = d
					_mine = u
	if _lumber_at == Vector3.INF or world.doodads.nearest_tree(_lumber_at, 6.0) < 0:
		_lumber_at = _find_tree_line()
	return p != null


func _walkable(p: Vector3) -> Vector3:
	var c := world.pathing.nearest_walkable(Grid.world_to_cell(world.map.clamp_to_map(p, 1.0)))
	return Grid.cell_to_world(c)


## The living tree nearest the hall (beyond the hall's own clearing), INF when none.
func _find_tree_line() -> Vector3:
	var best := INF
	var at := Vector3.INF
	for i in world.doodads.trees.size():
		if not world.doodads.tree_alive(i):
			continue
		var tp := world.doodads.tree_pos(i)
		var d := Grid.flat_dist(tp, _hall.pos)
		if d < best and d > 6.0:
			best = d
			at = tp
	return at


# --- workers -------------------------------------------------------------------------------

func _workers() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.is_worker:
			out.append(u)
	return out


## Idle workers go to gold up to rules.ai gold_workers, the rest to lumber.
func _assign_workers() -> void:
	var gold_n := 0
	var idle: Array[Unit] = []
	for u in _workers():
		if u.hidden:
			gold_n += 1
			continue
		var o := u.current
		if o == null and u.orders.is_empty():
			idle.append(u)
		elif o != null and o.type == Order.Type.GATHER and o.target_id != 0:
			gold_n += 1
	var gold_target := int(tuning().get("gold_workers", 5))
	for u in idle:
		if gold_n < gold_target and _mine != null:
			_issue({"type": "gather", "units": [u.id], "target": _mine.id})
			gold_n += 1
		elif _lumber_at != Vector3.INF:
			var i := world.doodads.nearest_tree(_lumber_at, 6.0)
			if i >= 0:
				_issue({"type": "gather", "units": [u.id], "pos": world.doodads.tree_pos(i)})


## Workers wanted now: the opening's count, capped at gold + lumber workers for the tier
## (rules.ai gold_workers, lumber_workers [T1, T2]) plus two builders.
func worker_target() -> int:
	var t := clampi(world.tech.tier(player_id), 1, 2)
	var lumber: Array = tuning().get("lumber_workers", [4, 7])
	var need := int(tuning().get("gold_workers", 5)) + int(lumber[mini(t, lumber.size()) - 1]) + 2
	return mini(int(_opening.get("workers", 12)), need)


func _train_workers() -> void:
	var p := world.player(player_id)
	var worker := str(Defs.faction(p.faction).get("worker", ""))
	var count := _workers().size() + _queued(worker)
	var target := worker_target()
	if count >= target:
		return
	for b in _own_buildings():
		if not b.has_flag("town_hall") or b.under_construction or world.production.is_upgrading(b):
			continue
		if world.production.queue_of(b).size() >= 2 or world.production.can_train(b, worker) != "":
			continue
		var cost := world.production.unit_cost(player_id, worker)
		if not _affordable(cost):
			return
		_issue({"type": "train", "units": [b.id], "def": worker})
		_spend(cost)
		count += 1
		if count >= target:
			return


# --- supply and the opening ------------------------------------------------------------------

## A supply building when free food (with sites and builders on their way) runs short.
func _supply(p: PlayerState) -> void:
	var cap_max := int(Defs.rule("economy.food_cap", 100))
	if p.food_cap >= cap_max:
		return
	var pending := 0
	for b in _own_buildings():
		if b.under_construction:
			pending += int(b.def.get("food_provided", 0))
	for u in _workers():
		if u.current != null and u.current.type == Order.Type.BUILD and u.current.target_id == 0:
			pending += int(Defs.unit(u.current.def_id).get("food_provided", 0))
	var need := int(tuning().get("supply_buffer_food", 5)) + 3
	if p.food_cap + pending - p.food_used >= need:
		return
	_try_build(str(Defs.faction(p.faction).get("supply", "")), "hall")


## Works through the opening's steps in order (one new action per think).
func _build_order() -> void:
	var steps: Array = _opening.get("steps", [])
	var slack := float(tuning().get("build_slack", 0.0))
	var wanted: Dictionary = {}       ## def -> how many of it the steps so far ask for
	for i in steps.size():
		var s: Dictionary = steps[i]
		if _skipped.has(i):
			continue
		if s.has("build"):
			var d := str(s["build"])
			wanted[d] = int(wanted.get(d, 0)) + 1
		if _step_done(s, wanted):
			_blocked_since.erase(i)
			continue
		if world.time < float(s.get("at", 0.0)) + slack:
			return
		var why := _try_step(s)
		if why == "":
			_blocked_since.erase(i)
			return
		if why == "money":
			return        # wait for it (its cost is reserved)
		if not _blocked_since.has(i):
			_blocked_since[i] = world.time
		if world.time - float(_blocked_since[i]) >= STEP_SKIP_S:
			_skipped[i] = true
			continue
		return


## True when a step's goal is met or under way.
func _step_done(s: Dictionary, wanted: Dictionary) -> bool:
	if s.has("build"):
		var d := str(s["build"])
		return _count_def(d) + _builders_for(d) >= int(wanted[d])
	if s.has("hero"):
		var h := str(s["hero"])
		return _count_def(h) + _queued(h) > 0
	if s.has("research"):
		var r := str(s["research"])
		return world.tech.research_level(player_id, r) > 0 or _researching(r)
	if s.has("upgrade"):
		var up := Defs.upgrade(str(s["upgrade"]))
		if _count_def(str(up.get("to", ""))) > 0:
			return true
		for b in _own_buildings():
			if b.def_id == str(up.get("from", "")) and world.production.is_upgrading(b):
				return true
		return false
	if s.has("army"):
		return _army_on
	return true


## Tries a due step: "" = done, "money" = waiting for gold / lumber (reserved), else why not.
func _try_step(s: Dictionary) -> String:
	if s.has("build"):
		return _try_build(str(s["build"]), str(s.get("near", "hall")))
	if s.has("hero"):
		return _try_train(str(s["hero"]))
	if s.has("research") or s.has("upgrade"):
		var id := str(s.get("research", s.get("upgrade", "")))
		var why := "cannot"
		for b in _own_buildings():
			var err := world.production.can_queue_research(b, id)
			if err == "need_gold" or err == "need_lumber" or err == "":
				var lv := Defs.upgrade_level(id, world.tech.research_level(player_id, id) + 1)
				var cost: Dictionary = lv.get("cost", {})
				if not _affordable(cost):
					_spend(cost)
					return "money"
				_issue({"type": "research", "units": [b.id], "def": id})
				_spend(cost)
				return ""
			why = err
		return why
	if s.has("army"):
		_army_on = true
		state = "army"
		return ""
	return "unknown"


## Trains `def_id` at the first own building that can ("" done, "money" reserved, else why).
func _try_train(def_id: String) -> String:
	var why := "no_building"
	for b in _own_buildings():
		if not (b.def.get("trains", []) as Array).has(def_id):
			continue
		var err := world.production.can_train(b, def_id)
		if err == "" or err == "need_gold" or err == "need_lumber":
			var cost := world.production.unit_cost(player_id, def_id)
			if not _affordable(cost):
				_spend(cost)
				return "money"
			_issue({"type": "train", "units": [b.id], "def": def_id})
			_spend(cost)
			return ""
		why = err
	return why


## Sends a worker to build `def_id` near the hall or the tree line ("" ordered, "money"
## reserved, else why not).
func _try_build(def_id: String, near: String) -> String:
	if def_id.is_empty():
		return "unknown"
	var err := world.tech.can_build(player_id, def_id)
	if err != "":
		return err
	var cost: Dictionary = Defs.unit(def_id).get("cost", {})
	if not _affordable(cost):
		_spend(cost)
		return "money"
	var at := _hall.pos
	if near == "trees" and _lumber_at != Vector3.INF:
		var back := _hall.pos - _lumber_at
		back.y = 0.0
		at = _lumber_at + back.normalized() * 5.0
	var spot := _site_for(def_id, at)
	if spot == Vector3.INF:
		return "no_site"
	var builder := _builder_near(spot)
	if builder == null:
		return "no_builder"
	_issue({"type": "build", "units": [builder.id], "def": def_id, "pos": spot})
	_spend(cost)
	return ""


## A valid spot for `def_id` on rings around `around`: out of the hall–seam mining lane and
## with a 1 m walkable margin all round, so paths stay open.
func _site_for(def_id: String, around: Vector3) -> Vector3:
	var fp: Array = Defs.unit(def_id).get("footprint", [8, 8])
	var half := maxf(float(fp[0]), float(fp[1])) * Grid.CELL * 0.5
	var hall_half := float(_hall.footprint.size.x) * Grid.CELL * 0.5
	var r0 := hall_half + half + 2.0 if around == _hall.pos else half + 1.0
	var a0 := rng.randf() * TAU
	for ring in 14:
		var r := r0 + ring * 2.0
		var n := 10 + ring * 3
		for k in n:
			var a := a0 + TAU * float(k) / float(n)
			var p := around + Vector3(cos(a), 0.0, sin(a)) * r
			if _in_mining_lane(p, half):
				continue
			var spot := world.construction.can_place(player_id, def_id, p)
			if not spot["ok"]:
				continue
			var rect: Rect2i = spot["rect"]
			if not world.pathing.is_rect_free(rect.grow(2)):
				continue
			return spot["pos"]
	return Vector3.INF


func _in_mining_lane(p: Vector3, half: float) -> bool:
	if _mine == null:
		return false
	var a := Vector2(_hall.pos.x, _hall.pos.z)
	var b := Vector2(_mine.pos.x, _mine.pos.z)
	var q := Geometry2D.get_closest_point_to_segment(Vector2(p.x, p.z), a, b)
	return q.distance_to(Vector2(p.x, p.z)) < half + 4.0


## The worker to build at `spot`: an idle or lumber worker first (nearest), a miner last.
func _builder_near(spot: Vector3) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in _workers():
		if u.hidden:
			continue
		var o := u.current
		var cost := Grid.flat_dist(u.pos, spot)
		if o != null and o.type == Order.Type.BUILD:
			continue
		if o != null and o.type == Order.Type.GATHER and o.target_id != 0:
			cost += 1000.0     # keep the miners mining
		if cost < best_d:
			best_d = cost
			best = u
	return best


# --- army ----------------------------------------------------------------------------------

func _army() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.is_mobile() and not u.is_worker and not u.hidden:
			out.append(u)
	return out


## Army food that starts a push: the opening's `attack_food` (else rules.ai), but never more than
## the upkeep cap before the push leaves room for beside the workers (or it would never come).
func attack_threshold() -> int:
	var want := int(_opening.get("attack_food", tuning().get("attack_food", 40)))
	var room := int(tuning().get("upkeep_cap_before_push", 50)) - _food(_workers())
	return maxi(1, mini(want, room))


static func _food(units: Array[Unit]) -> int:
	var n := 0
	for u in units:
		n += int((u.def.get("cost", {}) as Dictionary).get("food", 0))
	return n


## One unit queued per production building, the opening's mix by weight, inside the upkeep cap.
func _train_army(p: PlayerState) -> void:
	if not _army_on:
		return
	var cap := int(tuning().get("upkeep_cap_after_push" if state == "push" else "upkeep_cap_before_push", 50))
	var mix: Array = _opening.get("army", [])
	var counts: Dictionary = {}
	for u in _army():
		counts[u.def_id] = int(counts.get(u.def_id, 0)) + 1
	for b in _own_buildings():
		if b.under_construction or b.has_flag("town_hall") or world.production.is_upgrading(b):
			continue
		if not world.production.queue_of(b).is_empty():
			continue
		var pick := ""
		var best := INF
		for m: Array in mix:
			var id := str(m[0])
			if not (b.def.get("trains", []) as Array).has(id):
				continue
			var err := world.production.can_train(b, id)
			if err != "" and err != "need_gold" and err != "need_lumber":
				continue
			var ratio := float(int(counts.get(id, 0)) + _queued(id)) / maxf(float(m[1]), 0.01)
			if ratio < best:
				best = ratio
				pick = id
		if pick == "":
			continue
		var cost := world.production.unit_cost(player_id, pick)
		if p.food_used + int(cost.get("food", 0)) > cap or not _affordable(cost):
			continue
		_issue({"type": "train", "units": [b.id], "def": pick})
		_spend(cost)
		counts[pick] = int(counts.get(pick, 0)) + 1


func _command_army() -> void:
	var army := _army()
	for b in _own_buildings():
		if b.can_train() and not _rallied.has(b.id) and not b.has_flag("town_hall"):
			_rallied[b.id] = true
			_issue({"type": "rally", "units": [b.id], "pos": _muster})
	_remember_enemies()
	if army.is_empty():
		if state == "push" or state == "defend":
			state = "army" if _army_on else "build_up"
		return
	var threat := world.time - _threat_t < THREAT_HOLD_S
	match state:
		"creep":
			if threat:
				state = "defend"
				_creep_camp = ""
				_last_push_cmd = world.time
				_issue({"type": "attack_move", "units": _ids(army), "pos": _threat_pos})
				return
			if _army_on and _food(army) >= attack_threshold():
				state = "army"           # the push takes over on the next think
				_creep_camp = ""
				return
			var low := false
			for h in _heroes():
				low = low or h.hp < h.max_hp * float(tuning().get("hero_retreat_hp", 0.35))
			var st := world.creeps.camp_state(_creep_camp)
			if low:
				state = "army"
				_creep_camp = ""
				_issue({"type": "move", "units": _ids(army), "pos": _muster})
				return
			if st.is_empty() or bool(st["cleared"]):
				if not st.is_empty():
					_loot(st["pos"])
				state = "army"
				_creep_camp = ""
				return
			if world.time - _last_push_cmd >= PUSH_REISSUE_S:
				_last_push_cmd = world.time
				var idle := army.filter(func(u: Unit) -> bool: return u.current == null)
				if not idle.is_empty():
					_issue({"type": "attack_move", "units": _ids(idle), "pos": st["pos"]}, false)
		"push":
			var hp := 0.0
			for u in army:
				hp += u.hp
			if hp < _push_hp0 * float(tuning().get("army_retreat_hp", 0.0)):
				state = "army"
				_issue({"type": "move", "units": _ids(army), "pos": _muster})
				return
			if world.time - _last_push_cmd >= PUSH_REISSUE_S:
				_last_push_cmd = world.time
				var idle := army.filter(func(u: Unit) -> bool: return u.current == null)
				if not idle.is_empty():
					_issue({"type": "attack_move", "units": _ids(idle), "pos": _push_target(army)}, false)
		"defend":
			if not threat:
				state = "army" if _army_on else "build_up"
				_issue({"type": "move", "units": _ids(army), "pos": _muster})
			elif world.time - _last_push_cmd >= PUSH_REISSUE_S * 0.5:
				_last_push_cmd = world.time
				_issue({"type": "attack_move", "units": _ids(army), "pos": _threat_pos}, false)
		_:
			if threat:
				state = "defend"
				_last_push_cmd = world.time
				_issue({"type": "attack_move", "units": _ids(army), "pos": _threat_pos})
				return
			if _army_on and _food(army) >= attack_threshold() and world.time >= float(tuning().get("attack_not_before", 0.0)):
				state = "push"
				_push_hp0 = 0.0
				for u in army:
					_push_hp0 += u.max_hp
				_last_push_cmd = world.time
				_issue({"type": "attack_move", "units": _ids(army), "pos": _push_target(army)})
				return
			var camp := _next_camp(army)
			if camp != "":
				state = "creep"
				_creep_camp = camp
				_last_push_cmd = world.time
				_issue({"type": "attack_move", "units": _ids(army), "pos": world.creeps.camp_state(camp)["pos"]})
				return
			var strays: Array = []
			for u in army:
				if u.current == null and Grid.flat_dist(u.pos, _muster) > 8.0:
					strays.append(u.id)
			if not strays.is_empty():
				_issue({"type": "move", "units": strays, "pos": _muster}, false)


# --- heroes, creeping, worker defence (Playtest 3) ------------------------------------------

func _heroes() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.is_hero and u.player_id == player_id:
			out.append(u)
	return out


## Skill points from the hero's skill_build, heal items when hurt, revives.
func _hero_care() -> void:
	for h in _heroes():
		if int(h.hero.get("skill_points", 0)) > 0:
			_learn(h)
		if h.hp < h.max_hp * 0.4:
			_drink(h)
	_revive()


func _learn(h: Unit) -> void:
	var planned := {}
	for aid: Variant in Defs.hero(str(h.hero.get("hero_id", h.def_id))).get("skill_build", []):
		var id := str(aid)
		planned[id] = int(planned.get(id, 0)) + 1
		if int(planned[id]) > world.heroes.rank_of(h, id) and world.heroes.can_learn(h, id):
			_issue({"type": "learn", "units": [h.id], "ability": id})
			return
	for aid: Variant in h.def.get("hero_abilities", []):
		if world.heroes.can_learn(h, str(aid)):
			_issue({"type": "learn", "units": [h.id], "ability": str(aid)})
			return


func _drink(h: Unit) -> void:
	for slot in h.inventory.size():
		var it: Variant = h.inventory[slot]
		if it != null and str(Defs.item(str(it["id"])).get("effect", "")).begins_with("heal") \
				and world.items.can_use(h, slot):
			_issue({"type": "use_item", "units": [h.id], "slot": slot})
			return


func _revive() -> void:
	for hid in world.heroes.dead_heroes(player_id):
		if world.production.is_reviving(hid):
			continue
		var cost := world.heroes.revive_cost(hid)
		if not _affordable(cost):
			return
		for b in _own_buildings():
			if world.heroes.can_revive(b, hid) == "":
				_issue({"type": "revive", "units": [b.id], "hero": hid})
				_spend(cost)
				return


## Heroes cast what SpellAi picks for the fight around them, one cast each per think.
func _cast_in_fights(army: Array[Unit]) -> void:
	for h in _heroes():
		if h.current != null and h.current.type == Order.Type.CAST:
			continue
		for aid: Variant in h.def.get("hero_abilities", []):
			var id := str(aid)
			if world.abilities.cast_error(h, id, null, false) != "":
				continue
			var pick := SpellAi.pick(world, h, id, army)
			if pick.is_empty():
				continue
			var cmd := {"type": "cast", "units": [h.id], "ability": id}
			cmd.merge(pick)
			_issue(cmd)
			break


## The map's creep route for the first hero (map meta creep_route.hero_1), each template id
## resolved to this player's copy (the nearer `<id>_p1` / `<id>_p2`) or the shared camp.
func _route_camps() -> Array:
	if not _route.is_empty() or world.creeps == null:
		return _route
	var meta: Dictionary = world.map.meta if world.map.meta is Dictionary else {}
	var r: Dictionary = meta.get("creep_route", {})
	var camps := world.creeps.camps()
	for tid: Variant in r.get("hero_1", []):
		var id := str(tid)
		if camps.has(id):
			_route.append(id)
			continue
		var best := ""
		for suffix: String in ["_p1", "_p2"]:
			if camps.has(id + suffix) and (best == "" or Grid.flat_dist((camps[id + suffix] as Dictionary)["pos"], _hall.pos)
					< Grid.flat_dist((camps[best] as Dictionary)["pos"], _hall.pos)):
				best = id + suffix
		if best != "":
			_route.append(best)
	if _route.is_empty():
		var ids: Array = camps.keys()
		ids.sort_custom(func(a: String, b: String) -> bool:
			return Grid.flat_dist((camps[a] as Dictionary)["pos"], _hall.pos) < Grid.flat_dist((camps[b] as Dictionary)["pos"], _hall.pos))
		_route = ids
	return _route


## The next camp to creep: the first on the route still standing, of a colour up to max_camp
## and no stronger than camp_level_ratio × the group's levels; "" when none (or no healthy hero).
func _next_camp(army: Array[Unit]) -> String:
	var heroes := _heroes()
	if heroes.is_empty() or not heroes.all(func(h: Unit) -> bool: return h.hp >= h.max_hp * 0.8):
		return ""
	var group := 0
	for u in army:
		group += maxi(1, u.level)
	var colours := ["green", "amber", "red"]
	var max_c := colours.find(str(tuning().get("max_camp", "green")))
	var ratio := float(tuning().get("camp_level_ratio", 1.0))
	for cid: Variant in _route_camps():
		var st := world.creeps.camp_state(str(cid))
		if st.is_empty() or bool(st["cleared"]):
			continue
		if colours.find(str(st["colour"])) > max_c:
			continue
		var lv := 0
		for m in world.creeps.camp_members(str(cid)):
			lv += maxi(1, m.level)
		if float(lv) <= ratio * float(group):
			return str(cid)
	return ""


## After a camp: the first hero with room picks up what dropped there.
func _loot(at: Vector3) -> void:
	for u in world.unit_list:
		if u.alive and u.is_item and Grid.flat_dist(u.pos, at) <= 12.0:
			for h in _heroes():
				if world.items.can_pickup(h, u):
					_issue({"type": "smart", "units": [h.id], "target": u.id}, false)
					return


## The worker defence (rules §19): Levy Horn or Sound the Gong when 3+ enemy combat units (6+
## food) are within 18 m of its workers; Lay Down Flails or All Clear 10 s after none remain.
func _signature() -> void:
	if _hall == null or not _hall.alive:
		return
	var near := 0
	var food := 0
	var workers := _workers()
	for u in world.unit_list:
		if not u.alive or u.is_worker or not u.is_mobile() or not world.is_enemy(player_id, u.player_id) \
				or u.player_id >= PlayerState.NEUTRAL_HOSTILE:
			continue
		if world.fog != null and not world.fog.can_see(player_id, u):
			continue
		for wk in workers:
			if Grid.flat_dist(wk.pos, u.pos) <= 18.0:
				near += 1
				food += int((u.def.get("cost", {}) as Dictionary).get("food", 0))
				break
	if near >= 3 and food >= 6:
		_danger_t = world.time
		if not _signature_on:
			var call := "kingdom_levy_horn" if _hall.abilities.has("kingdom_levy_horn") else "clans_sound_the_gong"
			if _hall.abilities.has(call) and world.abilities.is_ready(_hall, call):
				_signature_on = true
				_issue({"type": "cast", "units": [_hall.id], "ability": call})
	elif _signature_on and world.time - _danger_t >= 10.0:
		_signature_on = false
		var release := "kingdom_lay_down_flails_all" if _hall.abilities.has("kingdom_lay_down_flails_all") else "clans_sound_the_gong"
		if _hall.abilities.has(release):
			_issue({"type": "cast", "units": [_hall.id], "ability": release})


## Enemy structures the AI can see now are remembered (its own fog only).
func _remember_enemies() -> void:
	for id: int in _known.keys():
		var u := world.get_unit(id)
		if u == null or not u.alive:
			_known.erase(id)
	for u in world.unit_list:
		if u.alive and u.is_building and world.is_enemy(player_id, u.player_id) \
				and u.player_id < PlayerState.NEUTRAL_HOSTILE \
				and (world.fog == null or world.fog.can_see(player_id, u)):
			_known[u.id] = u.pos


## The nearest remembered enemy structure to the army, else the enemy start.
func _push_target(army: Array[Unit]) -> Vector3:
	var c := Vector3.ZERO
	for u in army:
		c += u.pos
	c /= float(army.size())
	var best := INF
	var at := _enemy_start
	for id: int in _known:
		var d := Grid.flat_dist(_known[id], c)
		if d < best:
			best = d
			at = _known[id]
	return at


func _on_damaged(u: Node, _amount: float, src: Node) -> void:
	var v := u as Unit
	var s := src as Unit
	if v == null or s == null or v.world != world or v.player_id != player_id or _hall == null:
		return
	if not world.is_enemy(player_id, s.player_id) or Grid.flat_dist(v.pos, _hall.pos) > THREAT_RANGE:
		return
	_threat_pos = v.pos
	_threat_t = world.time


# --- helpers -------------------------------------------------------------------------------

func _own_buildings() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.is_building:
			out.append(u)
	return out


func _count_def(def_id: String) -> int:
	var n := 0
	for u in world.unit_list:
		if u.alive and u.player_id == player_id and u.def_id == def_id:
			n += 1
	return n


## Workers on their way to start a `def_id` site.
func _builders_for(def_id: String) -> int:
	var n := 0
	for u in _workers():
		for o: Order in [u.current] + u.orders:
			if o != null and o.type == Order.Type.BUILD and o.target_id == 0 and o.def_id == def_id:
				n += 1
	return n


## Units of `def_id` in this player's production queues.
func _queued(def_id: String) -> int:
	var n := 0
	for b in _own_buildings():
		for e: Dictionary in world.production.queue_of(b):
			if str(e["id"]) == def_id:
				n += 1
	return n


func _researching(upgrade_id: String) -> bool:
	return _queued(upgrade_id) > 0


func _affordable(cost: Dictionary) -> bool:
	return int(_budget.get("gold", 0)) >= int(cost.get("gold", 0)) \
		and int(_budget.get("lumber", 0)) >= int(cost.get("lumber", 0))


## Takes `cost` out of this think's budget (spent or reserved).
func _spend(cost: Dictionary) -> void:
	_budget["gold"] = int(_budget.get("gold", 0)) - int(cost.get("gold", 0))
	_budget["lumber"] = int(_budget.get("lumber", 0)) - int(cost.get("lumber", 0))


static func _ids(units: Array) -> Array:
	var out: Array = []
	for u: Unit in units:
		out.append(u.id)
	return out


## Issues a player command; non-essential ones are dropped above the APM cap.
func _issue(cmd: Dictionary, essential: bool = true) -> void:
	var window := 60 * World.TICK_RATE
	while not _actions.is_empty() and world.tick_count - _actions[0] > window:
		_actions.pop_front()
	if not essential and _actions.size() >= int(tuning().get("apm_cap", 90)):
		return
	_actions.append(world.tick_count)
	cmd["player"] = player_id
	world.issue(cmd)
	issued += 1
