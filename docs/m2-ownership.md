# M2 ownership map and cross-system contracts

M2 is built by 8 agents working in parallel on one branch. Each agent owns a set of files and
implements the documented stub APIs in them. The contract layer (data tables, order handlers,
`SimSystem` stubs with their APIs, World stages, command routing, hooks, signals, tests) is
already in place, so every agent can start at once. Read with:
`docs/architecture.md` (engine contract), `data/SCHEMA.md` (every data field),
`docs/design/rules.md` (numbers and behaviour), the faction docs and `neutrals.md`.

Hard rules for every agent: gameplay only in the fixed 30 Hz tick (`sim_tick`, order handler
`tick`), juice only in `_process`; every number from `Defs`; headless tests for what you build
(`godot --headless --path . -s tests/run_tests.gd`, never skip or disable a test); run
`python3 tools/ip/check_banned_terms.py` before committing; commit only your own files.

## 1. Who owns what

| Agent | Domain | Owns (edit freely) | Tests to add |
|---|---|---|---|
| **A** | Economy + construction | `src/systems/economy.gd`, `src/systems/construction.gd`; order handlers `src/entities/orders/gather.gd`, `return_resources.gd`, `build.gd`, `repair.gd`, `enter.gd`; worker-defence effects `src/systems/abilities/effects/levy_horn.gd`, `levy_release.gd`, `sound_the_gong.gd`, `transform.gd`, `garrison_enter.gd`, `garrison_unload.gd`, `repair.gd`; data entries: `rules.economy`, faction economy fields, `kingdom_take_up_the_flail` / `kingdom_lay_down_*` / `kingdom_levy_*` / `clans_sound_the_gong` / `clans_roll_the_felt` / `clans_unload_all` / `kingdom_repair` / `clans_mend` | `tests/unit/test_economy.gd`, `test_construction.gd` |
| **B** | Production + tech (+ combat extensions) | `src/systems/production.gd`, `src/systems/tech.gd`, `src/entities/orders/attack_ground.gd`; combat extensions inside `src/systems/combat.gd` (splash, artillery `min_range`, `fire_at_point`, ground/air targets, `damage_pct` / `damage_taken_pct` / `miss_chance` from `Unit.mod_totals`, `upgrade_damage`); data: `upgrades.json`, building `trains` / `research` / `upgrades_to` / `requires` | `test_production.gd`, `test_tech.gd`, extend `test_combat.gd` |
| **C** | Heroes + abilities + buffs | `src/systems/heroes.gd`, `src/systems/abilities.gd`, `src/systems/buffs.gd`, `src/systems/abilities/` (`effect.gd`, `cast_context.gd`, `registry.gd`, `effects/*` except agent A's six); order handlers `cast.gd`, `learn.gd`; data: `heroes.json`, `abilities.json` (except A's entries), `buffs.json` | `test_heroes.gd`, `test_abilities.gd`, `test_buffs.gd` |
| **D** | Items + shops + creeps + map | `src/systems/items.gd`, `src/systems/items/effects/*`, `src/systems/shops.gd`, `src/systems/creeps.gd`; order handlers `use_item.gd`, `pickup_item.gd`, `drop_item.gd`; `tools/maps/build_slice_map.py`, `data/maps/*`, map parts of `src/world/map_data.gd` (`meta`, camps, neutral buildings); data: `items.json`, `shops.json`, `creep_camps.json`, creep and critter entries of `units.json`, neutral buildings | `test_items.gd`, `test_shops.gd`, `test_creeps.gd`, keep `test_slice_map.gd` green |
| **E** | Fog + minimap | `src/world/fog.gd`, `src/ui/minimap.gd`; fog uniforms in `terrain.gdshader`, `water.gdshader`, `src/render/foliage.gdshader` (trees; `tree.gdshader` is unused) (`fog_tex`, `fog_enabled`); `rules.vision`, `rules.minimap`, `rules.daynight` sight transition | `test_fog.gd`, `test_minimap.gd` |
| **F** | HUD / UI | `src/ui/hud.gd`, `hud.tscn`, `command_card.gd`, new `src/ui/*` (tooltips, hero portraits, idle-worker button, shop card, build menus, queue display, notifications), `src/input/command_input.gd` (targeting modes for every command, build placement ghost, card activation), `src/input/selection.gd`; `data/strings/en.json` | `test_hud.gd`, extend `test_input.gd` |
| **G** | Juice | `src/fx/*`, `src/entities/unit_view.gd` (models, `model_fit`, `model_addons`, `model_depleted`, animation, construction reveal), the render layer `src/render/*` (AssetLibrary, painterly shaders, instance-uniform slots, TimeOfDay, ColorGrade, RenderProfile, ViewHooks), the visual parts of `src/world/terrain_builder.gd` / `terrain.gdshader` / `water.gdshader` / `doodads.gd` (meshes, decor, sway) / `day_night.gd`, `src/autoload/audio.gd`, camera feel in `src/input/rts_camera.gd` (shake, kicks), new fx scenes / shaders | `test_fx.gd` (headless: no errors, pooling caps), keep `test_visual.gd` green |
| **H** | AI | `src/systems/ai/*` (`ai_player.gd` + new build-order / creep-route / army modules); `rules.ai.*` | `test_ai.gd` (AI vs AI to a result, no cheats) |

Asset kit agents (models under `assets/models/*`, `tools/kits/*`) are separate and keep their
own files; gameplay agents only read model paths from data.

## 2. Shared files (coordinate, keep edits small)

These are the contract. Change them only by **adding**; never rename or change the meaning of
an existing API. If a contract must change, update `docs/architecture.md` / this file / the
affected stub headers in the same commit and keep the existing tests green.

| File | Policy |
|---|---|
| `src/world/world.gd` | Systems, stages, `SYSTEM_COMMANDS`, hooks and `resolve_smart` are in place. Adding a command type: one line in `SYSTEM_COMMANDS` + a test in `test_commands.gd`. Prefer hooks (`on_unit_spawned/died/removed/damaged`) over new World code. |
| `src/entities/unit.gd` | Per-unit state a system needs lives in that system (dictionary keyed by `unit.id`) or in `order.data`. New Unit fields only when the sim loop itself needs them, appended with an owner comment. Stats change only through `set_modifiers(source, mods)` / `set_base_stats`; statuses through modifier `status` lists. |
| `src/entities/order.gd`, `orders/registry.gd`, `orders/order_handler.gd` | Append new `Order.Type`s at the end of the enum (never reorder: replays and tests use the values). |
| Core handlers `idle, move, stop, hold, attack, attack_move, patrol, follow` | Owned by the contract; B may extend `attack.gd` / `idle.gd` for combat extensions, everyone else asks via a hook. |
| `src/autoload/events.gd` | Append signals under your domain's block; never change an existing signature. |
| `src/autoload/defs.gd` | Add validation in your own `_validate_<domain>` and accessors at the end of the accessor block. Keep `Defs.errors` empty. |
| `src/systems/sim_system.gd` | Frozen. |
| `src/main.gd` | Match boot (slice, sandbox, battlefield) and scene switching (`start_match`, `quit_to_menu`). D owns map/creep boot, H the AI seat, F the HUD wiring; small edits only. |
| `src/scenarios/*`, `data/scenarios.json`, `src/ui/{main_menu,menu_backdrop,pause_menu,end_banner,ui_style}.gd` | Playtest scenarios and the menus around them (PT1 Battlefield sandbox). The scripted opponent there is not the AI (agent H): it only issues player commands; juice HUD-11 / SEQ-02 replace the placeholder pause menu and end banner. |
| `data/*.json` | Each agent edits the entries of its domain (table above). Shared tables (`factions.json`, `units.json`, `buildings.json`) are edited entry by entry; cite the source doc section for a changed number. |
| `docs/architecture.md`, `data/SCHEMA.md`, this file | Update the section of your system when its contract changes. |

## 3. Tick order (World stages)

```
orders      World._apply_commands (unit orders → OrderHandlers; system commands → handle_command)
production  construction, production, tech                 (register order in SYSTEM_STAGES)
units       Unit.sim_tick: lifetime, stun / root, current order handler tick, movement, attacks
projectiles combat (first), projectiles
abilities   abilities, buffs, items
economy     economy, heroes, shops
creeps      creeps
ai          one AiPlayer per AI seat (World.add_player(..., ai = true, difficulty))
fog         fog
cleanup     dead units leave the sim (hooks: died), removed units freed (hooks: removed)
```

Hooks: a system returns the names it wants from `hooks()` (`&"spawned"`, `&"died"`,
`&"removed"`, `&"damaged"`); World calls `on_unit_spawned(u)` after spawn,
`on_unit_died(u, killer)` in cleanup (before `Events.unit_died`), `on_unit_removed(u)` for
units taken out without dying (items picked up, transforms), `on_unit_damaged(u, amount, src)`
from `Unit.take_damage`.

## 4. Commands and order routing

All input, AI and tests use `World.issue(cmd)` with the same dictionaries
(`docs/architecture.md` §4). Routing:

| Command `type` | Goes to | Owner |
|---|---|---|
| `move, stop, hold, attack, attack_move, patrol, follow, smart` | unit orders (core handlers) | contract |
| `gather, return` / `return_resources`, `build`, `repair`, `enter` | unit orders → Economy / Construction | A |
| `attack_ground` | unit order → `Combat.fire_at_point` | B |
| `train`, `cancel`, `research` | `Production.handle_command` | B |
| `cast` (mobile) / `learn` | unit orders → AbilitySystem / HeroSystem | C |
| `cast` (structure caster) | `AbilitySystem.handle_command` (Levy Horn, Sound the Gong, Unload All) | C (+A effects) |
| `autocast` | `AbilitySystem.handle_command` | C |
| `revive` | `HeroSystem.handle_command` | C |
| `use_item`, `pickup_item`, `drop_item`, `give_item` | unit orders → ItemSystem | D |
| `buy`, `sell`, `service` | `ShopSystem.handle_command` | D |
| `rally` | sets `rally_pos` / `rally_id` on producing structures | contract (B reads it) |

Smart right-click (`World.resolve_smart(u, target)` / `resolve_smart_point(u, tree)`):
producer → rally; ground item → `pickup_item` (if `ItemSystem.can_pickup`); resource / tree →
`gather` for workers; enemy → `attack` (`follow` without a weapon); own site → `build`
(help, `Construction.can_order_build`); own drop-off with cargo → `return_resources`
(`Economy.accepts_cargo`); own garrison with room → `enter` (`Construction.can_enter`);
damaged allied structure / mechanical unit → `repair` (`Construction.can_repair`); mobile ally
→ `follow`; anything else → `move`. Tree clicks within `World.TREE_CLICK_RADIUS` (1.2 m) set
`order.data.tree`.

Order handler contract (`src/entities/orders/order_handler.gd`): stateless, one instance per
type. `can_start(u, o)` (refuse at issue time), `enter(u, o)` (becomes current), `tick(u, o, dt)
-> Vector3` (desired velocity; call `u.finish_order()` to complete), `exit(u, o)` (always
called when the order ends or is replaced), `accepts_retaliation`, `is_instant` +
`apply_instant` (learn, never interrupt), `allows_immobile` (towers, immobile summons).
Per-order state lives in `o.data`; a system that takes over sets `o.data["phase"]`.

## 5. Cross-system call contracts

Call only the functions listed here across domains (they exist now as stubs with the
documented signature). Results are plain values; no system holds references into another
system's private state.

### A: Economy / Construction (provide)
- `Economy.can_afford(pid, cost) / spend(pid, cost) -> bool / refund(pid, cost, factor)` —
  used by B (queues), D (shops, services), C (revive), A (build, repair).
- `Economy.add_income(pid, kind, amount, source, pos) -> int` (upkeep tax applied for gold
  `source` in `rules.economy.upkeep_taxed_income`; returns the credited amount) — D (bounty,
  item sale, `grant_gold`), A (trips).
- `Economy.pay_fraction(pid, kind, amount) -> bool` (fractional accumulator: repair, Hod Chain).
- `Economy.upkeep_tier(pid) / upkeep_factor(pid)`, `tier_for_food(food)` — F (label), H.
- `Economy.gold_left(mine)`, `find_dropoff(worker)`, `carry_kind(worker)`, `accepts_cargo(b, w)` —
  F (mine tooltip), H.
- Order hand-offs: `on_gather_reached(worker, o) -> bool`, `gather_tick(worker, o, dt) -> Vector3`,
  `on_gather_order_ended(worker, o)`, `retarget_tree(worker, o) -> int`, `deposit(worker, b)`.
- `Construction.can_place(pid, def_id, pos) -> {ok, reason, rect, pos}` — F (ghost), H.
- `Construction.can_order_build(worker, o)`, `on_builder_arrived(worker, o) -> Unit`,
  `join_site`, `build_tick`, `on_builder_left`, `start_site(pid, def, pos, facing) -> Unit`,
  `complete_site(site)` (B calls it for instant test sites only), `cancel_site(site)` — F (cancel
  button), H.
- `Construction.can_repair / repair_tick / on_repair_ended`, `garrison_slots(b)`,
  `can_enter(u, b)`, `garrison_enter(u, b)`, `garrison_unload(b)` — C (Unload All effect), F.
- A calls: `World.spawn_unit(def, pid, pos, facing, {under_construction: true, hp_fraction})`,
  `World.adjust_food`, `World.set_hidden` (mine, garrison), `Tech.requirements_met`,
  `Fog.is_explored` (placement), `CreepSystem.wake_near(building)` (guard camps),
  `Doodads.harvest / tree_alive / nearest_tree`.

### B: Production / Tech / Combat extensions (provide)
- `Production.queue_of(b) -> [{kind, id, ticks, total, cost, food, started}]`,
  `can_train(b, def) -> String` (error key, "" = ok), `train(b, def, count) -> int`,
  `queue_research(b, upgrade) -> bool`, `cancel(b, index) -> bool`, `spawn_point(b, toward)` — F, H.
- `Tech.tier(pid)`, `research_level(pid, id)`, `missing_requirements(pid, id) -> [ids]`,
  `requirements_met(pid, id)`, `can_research(pid, id, b) -> String`, `ability_unlocked(pid,
  ability)`, `complete_research(pid, id)`, `apply_unit_upgrades(u)` (spawn hook) — A, C, D
  (faction shop tiers), F, H.
- `Combat.fire_at_point(attacker, point)` (attack ground), `Combat.hit(src, target, base, type)`,
  `Combat.compute_damage` — C effects deal damage through `Combat.hit` (spell type
  `"spell"`), never by writing `hp`.
- B calls: Economy (pay/refund), `World.adjust_food` (reserve), `World.spawn_unit(...,
  {food_reserved: true})`, `HeroSystem.hero_slots(pid)` (altar), `Unit.set_modifiers(&"tech", mods)`.

### C: Heroes / Abilities / Buffs (provide)
- `HeroSystem.level_of(u)`, `rank_of(u, ability)`, `add_xp(u, amount, flat)`, `can_learn(u,
  ability)`, `learn(u, ability)`, `hero_slots(pid)`, `apply_attributes(u)` — B, D (tomes,
  retrain), F, H. Kill XP is awarded by HeroSystem from its `died` hook.
- `AbilitySystem.rank_of`, `values_for(u, ability)`, `is_ready`, `cooldown_left`,
  `can_order_cast(u, o)`, `cast_range`, `begin_cast(u, o) -> bool`, `cast_tick`, `cancel_cast`,
  `cast_now(caster, ability, target, pos)`, `execute(caster, ability, rank, target, pos)`,
  `set_autocast / is_autocast`, `add_ground_effect(...) -> handle`, `ground_effects()` — D
  (item effects reuse `execute`), F (card cooldowns), H.
- `BuffSystem.apply(target, buff, source, values) -> record`, `remove`, `has_buff`,
  `get_buff`, `dispel(target, mode, by_player) -> int`, `dispel_area(...)`, `set_aura(emitter,
  ability, rank)` — A (Levy transform buff), D (item buffs, creep sleep `buff_sleeping`, Hale
  Spring), E (invisibility / detection reads `Unit.status`), F.
- Effects: `AbilityEffect.cast(ctx: CastContext) -> bool`; `CastContext.make(world, caster,
  id, rank, values, target, pos, src)`, `ctx.value(key, fallback)`, `ctx.allows(unit)`;
  `EffectRegistry.get_effect(id)`. Item effects (D) use the same base class.
- C calls: `Combat.hit`, `World.spawn_unit` (summons, `lifetime_ticks`), `Fog.reveal`,
  `Unit.set_modifiers(&"buffs" | &"hero", mods)`, `Unit.set_base_stats`, Economy (revive cost).

### D: Items / Shops / Creeps / Map (provide)
- `ItemSystem.inventory_of(u)`, `free_slot(u)`, `spawn_item(id, pos, charges) -> Unit`,
  `give(hero, id, charges) -> slot`, `is_powerup`, `can_pickup`, `pickup`, `drop(u, slot, pos)`,
  `transfer(from, slot, to)`, `can_use`, `use_range`, `cooldown_left`, `use(u, slot, target,
  pos, o)`, `use_tick`, `cancel_use` — C (Wiped Slate via heroes), F (inventory panel), H.
- `ShopSystem.in_use_range(u, shop)`, `stock_of(pid, shop) -> [{item, count, max, available,
  hotkey}]`, `can_buy(pid, shop, item, hero) -> String`, `buy`, `sell`, `use_service` — F
  (shop card), H.
- `CreepSystem.spawn_camps(map) -> int`, `camps()`, `camp_members(id)`, `camp_state(id) ->
  {template, pos, alive, asleep, cleared, colour}`, `is_asleep(u)`, `bounty_for(u)`,
  `wake_near(building)` — A, E (minimap camp icons), F, H.
- Map: `MapData.meta` (`starts`, `expansions`, `creep_route`, `lanes`, `landmarks`,
  `critters`, `gold_amounts`), `MapData.mine_gold(i)`, `is_boundary_tile` — A (expansions), E
  (minimap), H (creep route, expansions).
- D calls: Economy (`add_income "bounty"`, spend), HeroSystem (`add_xp`, attributes),
  BuffSystem, `AbilitySystem.execute`, `World.spawn_unit("item_drop", ...)`, `World.remove_unit`.

### E: Fog / Minimap (provide)
- `Fog.state_at(pid, pos) -> UNEXPLORED|FOGGED|VISIBLE`, `is_visible`, `is_explored`,
  `can_see(pid, unit)` (visibility + invisibility/detection), `reveal(pid, pos, radius,
  duration, detect) -> handle`, `reveals()`, `grid(pid)`, `texture(pid)` — every target filter
  (acquisition in Unit, AI, selection of enemies), A (placement), C (reveal effects), F, G
  (hide fx in fog), H (the AI sees only its fog).
- Stub now: everything visible and explored; real fog sets `Fog.enabled`. Agents must already
  call `can_see` / `is_visible` where the rules need it so turning fog on needs no edits.
- Minimap reads: units (`World.unit_list`), `Fog.texture`, `CreepSystem.camps()`, alerts
  (`Events.alert_raised`), and issues commands only through `CommandInput.command_ground`.

### F: HUD / UI (reads only)
- UI never mutates sim state: it reads the query APIs above and issues command dictionaries
  (`World.issue`). Card layout from data (`abilities[*].hotkey`, unit `hotkey`, build menus
  `factions.<id>.build_basic/advanced`, shop `stock[*].hotkey`); `Defs` validates collisions.
- Text: entity `name` fields and `Defs.text(key)` for everything else (no literals in code).
- Signals to listen to: `resources_changed`, `upkeep_changed`, `queue_changed`,
  `training_*`, `research_*`, `tier_changed`, `inventory_changed`, `stock_changed`,
  `ability_learned`, `hero_level_up`, `notification`, `placement_rejected`, `selection_changed`.

### G: Juice (reads only)
- Visual/audio only, in `_process` with `delta`; never reads `World.rng` (own RNG), never
  writes sim state. Driven by `Events` (every signal in `events.gd` is a juice hook: damage,
  deaths, casts, buffs, cargo, construction, level-ups, bounty, item pickups...) and by
  `Unit` readers (`display_pos()`, `swing_progress()`, `build_progress`, `under_construction`,
  `status`, `buffs`).
- `UnitView` owns models (`model`, `model_fit: footprint` scales to the footprint, `model_addons`,
  `model_depleted`), animation clips (`idle, walk, attack, death, work, cast, birth`), the
  construction reveal and placeholder fallbacks.
- Juice ids in data: `abilities[*].fx`, ground effect `fx`, projectile `model`.

### H: AI (consumer)
- Uses only `World.issue` with player-identical commands and the query APIs above (Economy,
  Production, Tech, Construction.can_place, ShopSystem.stock_of, CreepSystem.camp_state,
  HeroSystem, AbilitySystem.is_ready, Fog.can_see). No direct state writes, no cheating
  vision. Tuning from `rules.ai.<difficulty>` (`AiPlayer.tuning()`); random choices from
  `AiPlayer.rng` only.

## 6. Signals by owner (`src/autoload/events.gd`)

- Core: `unit_spawned, unit_died, unit_damaged, order_issued, selection_changed, notification,
  alert_raised, command_issued, menu_requested, tree_felled`.
- A: `resources_changed, income_received, upkeep_changed, cargo_delivered, mine_low,
  mine_depleted, construction_started, construction_cancelled, building_completed,
  repair_started, placement_rejected, garrison_changed`.
- B: `training_started, training_completed, queue_changed, production_stalled,
  research_started, research_completed, tier_changed`.
- C: `hero_level_up, xp_gained, ability_learned, hero_died, hero_revived, ability_cast,
  cast_started, cast_cancelled, autocast_changed, ground_effect_added, buff_applied,
  buff_removed, dispelled`.
- D: `item_picked_up, item_dropped, item_used, inventory_changed, item_bought, item_sold,
  stock_changed, service_used, camp_aggro, camp_cleared, camp_slept, camp_woke, bounty_paid`.
- E: `fog_updated`.

## 7. Test contract

- `tests/unit/test_commands.gd`: every command route reaches its system or handler (spies),
  smart right-click resolution for every target kind. Keep it green when you implement your
  system (replace a stub by the real behaviour; adjust spies, never delete a route test).
- `tests/unit/test_systems.gd`: stage registration, hooks, effect registry coverage, AI
  install, Fog stub contract, Economy tax/refund, stat pipeline, towers.
- `tests/unit/test_data.gd`: `Defs.errors` empty, slice counts, hero level-1 checks, footprints,
  rules merge, test defs isolation. `tests/unit/test_slice_map.gd`: the map contract.
- Use `make_world()` (headless, manual ticks) and real slice defs; `dummy_*` test defs only
  for engine-level tests (pathing, perf, sandbox playtests).
