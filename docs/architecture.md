# Vibecraft — Engine Architecture (contract)

Godot **4.7.2-stable**, GDScript, **Forward+** renderer (falls back to Compatibility on old GPUs).
This document is the contract every contributor (human or agent) codes against. If you need to
change an interface here, change this file in the same commit.

## 1. Golden rules

1. **Refresh-rate independent.** All gameplay runs in a fixed-step simulation. Nothing gameplay-related
   may depend on frame rate or `_process` delta. Visual-only effects (camera, UI tweens, particles,
   procedural bobbing) use `delta` in `_process`.
2. **Fixed tick:** `physics/common/physics_ticks_per_second = 30`. All simulation logic runs from
   `World._physics_process` → `World.step()` in a deterministic system order (see §4); `step()`
   always advances by the constant `World.DT = 1/30` and never reads frame delta, so tests call it
   directly. `physics/common/physics_interpolation = true` so `Node3D` transforms written during
   the tick are smoothly interpolated on any monitor (60/144/240 Hz…). The camera and UI are not
   interpolated (they update in `_process`). When teleporting an entity call
   `reset_physics_interpolation()` (`Unit.teleport()` does). Nodes animated per render frame
   (UnitView `Rig`, fx MultiMeshes) set `physics_interpolation_mode = OFF`; Godot's scene-tree
   interpolation still carries them along with their interpolated parent. Fx drawn in `_process`
   use `Unit.display_pos()` (= `prev_pos.lerp(pos, World.interpolation_fraction())`; the
   fraction is the engine's physics interpolation fraction, frozen at 1 while the World is
   paused so nothing oscillates between the last two ticks).
   Determinism: sim code never uses wall-clock time, `randf()` without the world RNG, or
   unordered iteration (path budgets are query counts and cell costs, not milliseconds).
3. **Data-driven.** Every gameplay number lives in `data/*.json`, split per domain:
   `factions.json` (factions, global `rules`, `combat`, `upkeep`, `team_colours`), `units.json`,
   `buildings.json`, `heroes.json`, `abilities.json`, `buffs.json` (+ ground effects),
   `items.json`, `upgrades.json`, `shops.json` (+ services), `creep_camps.json`, `doodads.json`,
   `strings/en.json`, `maps/<name>.json`. **Every field is documented in `data/SCHEMA.md`.**
   The `Defs` autoload loads, fills defaults (`UNIT_DEFAULTS`, class timings, night sight,
   regen), validates fields and cross references (errors collected in `Defs.errors`; tests fail
   on any) and serves: `Defs.unit(id)` (every entity: units, buildings and one derived level-1
   def per hero), `building`, `hero`, `ability`, `buff`, `ground_effect`, `item`, `upgrade`,
   `shop`, `service`, `camp`, `doodad`, `faction` (empty + one warning when unknown),
   `Defs.rule("economy.gold_per_trip", fallback)` (the deep merge of every file's `rules`
   block; a leaf defined twice is an error), `Defs.text(key)` (UI strings), `ability_rank(id,
   rank)`, `upgrade_level(id, level)`, `hero_stats(id, level, bonus)` (the one hero formula),
   `xp_for_level`, `level_for_xp`, `prd_c(p)`, `trained_at`, `researched_at`, `effect_ids()`,
   `Defs.combat`, `Defs.upkeep`, `Defs.team_colours`. Code never hardcodes a stat.
   Entity defs require `name, kind (unit|building|resource|item), hp, radius` (+ `speed` > 0
   for mobile units unless flag `immobile`, `footprint [w, h]` in cells for structures);
   visual hints live in the def (`shape`, `weapon`, `roof`, `height`, `scale`, `model`,
   `model_fit`). Content is the slice (`slice-content.json`): kingdom/clans/creep/neutral ids.
   Engine-level tests use placeholder `dummy_*` defs from `data/test_defs.json`, merged only by
   `Defs.load_test_defs()` (test runner, sandbox scenario).
4. **Runs without art.** Every visual has a procedural placeholder fallback, so the game is always
   playable even if a model/texture/sound is missing. Missing assets log a warning once.
5. **Testable headless.** Every system can be exercised from `tests/` with `godot --headless`.
6. **Original IP only.** No names, art, audio, text or UI art from Warcraft or any Blizzard product.

## 2. Units of measure & world layout

| Thing | Value |
|---|---|
| World units | 1 Godot unit = 1 metre, **Y up**, map lies on the XZ plane, origin = map corner (0,0) |
| Terrain tile | `TILE = 2.0` m (terrain vertex grid, texture painting, cliff placement) |
| Pathing cell | `CELL = 0.5` m (4×4 cells per tile) |
| Cliff level height | `CLIFF_H = 1.75` m per level (levels 0..3), ramps span 2 tiles |
| Slice map | 96 × 96 tiles = 192 × 192 m (384 × 384 pathing cells) |
| Fog grid | 1 m resolution (192 × 192) |
| Typical unit radius | worker 0.35, infantry 0.45, large 0.7–1.0 m |
| Typical speeds | slow 3.0, normal 4.2, fast 5.5 m/s |
| Building footprints | in pathing cells: halls 16×16 (8 m), production / tech / shops 12×12, supply 8×8, towers 4×4, gold seam 12×12 |

Grid helpers live in `src/world/grid.gd` (`class_name Grid`, static funcs):
`world_to_cell(Vector3)->Vector2i`, `cell_to_world(Vector2i)->Vector3` (cell centre, y=0),
`world_to_tile`, `tile_to_world` (tile centre), `tile_corner_to_world`, `cell_to_tile`,
`tile_to_cell`, `in_bounds_cell`, `in_bounds_tile`, `footprint_rect(center, size)->Rect2i`
(even sizes centre on a cell corner, odd sizes on a cell centre), `snap_to_footprint`,
`rect_center_world`, `rect_cells`, `flat_dist`.

Player ids: humans/AI 0..11, `PlayerState.NEUTRAL_HOSTILE = 12` (creeps, enemy of everyone),
`PlayerState.NEUTRAL_PASSIVE = 13` (gold mines, critters; enemy of no one).

## 3. Project layout

```
project.godot
src/
  autoload/     defs.gd (Defs), audio.gd (Audio), settings.gd (Settings), events.gd (Events)
  main.tscn + main.gd   (class `Main`) boots a match: scenario "slice" (data/maps/slice.json,
                both factions, start halls + workers, mines, neutral buildings, creep camps, AI
                seat), "battlefield" (Playtest 1: data/scenarios.json run by
                scenarios/battlefield.gd, see §4 "Scenarios") or "sandbox" (generated test map
                with dummy defs; engine playtests). Every path applies the view setup
                (RenderProfile camera + ViewHooks); `spawn_skirmish = false` skips start bases and
                creep camps (screenshot / showcase scripts). The project's main scene is
                `ui/main_menu.tscn`; `Main.start_match(tree, scenario)` swaps the current scene
                for a fresh match (menu, Restart, Play again), `Main.quit_to_menu(tree)` goes back
                to the menu
  scenarios/    battlefield.gd (BattlefieldScenario: scripted set-up, opponent and victory check)
  world/        world.gd + world.tscn (match root), grid.gd, map_data.gd, map_generator.gd,
                terrain_builder.gd, terrain.gdshader, water.gdshader, tree.gdshader (legacy
                card-tree shader, unused since the kit trees: they use render/foliage.gdshader),
                pathing.gd, group_path.gd, spatial_hash.gd, fog.gd, doodads.gd, day_night.gd
  entities/     unit.gd, order.gd, orders/ (one OrderHandler per order type), projectile.gd,
                unit_view.gd (visuals) + unit_placeholder.gdshader
  systems/      sim_system.gd (SimSystem base), player_state.gd (PlayerState), combat.gd,
                economy.gd, construction.gd, production.gd, tech.gd, heroes.gd, abilities.gd
                (+ abilities/: effect.gd, cast_context.gd, registry.gd, effects/*.gd), buffs.gd,
                items.gd (+ items/effects/*.gd), shops.gd, creeps.gd, ai/ai_player.gd
  input/        rts_camera.gd, selection.gd, command_input.gd
  ui/           hud.tscn + hud.gd, command_card.gd, minimap.gd, tooltip.gd, theme/,
                main_menu.tscn + main_menu.gd + menu_backdrop.gd (title screen), pause_menu.gd
                (F10), end_banner.gd (victory / defeat), ui_style.gd (shared panel / button look)
  render/       visual-only rendering layer: asset_library.gd (model resolution, shared painterly
                materials, manifests), unit.gdshader / structure.gdshader / foliage.gdshader +
                unit_uniforms.gdshaderinc (fixed instance-uniform slots) + render_common.gdshaderinc,
                render_atmos.gd (fx clock, shared per-frame uniforms), time_of_day.gd (Greenvale keys),
                color_grade.gd (grading LUTs), render_profile.gd (camera constants),
                terrain_textures.gd (ladder Texture2DArray), view_hooks.gd (selection rim, pads),
                unit_manifest_builder.gd (generates assets/models/units/manifest.json)
  fx/           the juice runtime (juice bible §4; visual only): fx_clock.gd (FxClock: fx / ui
                clocks, tick anchor), juice.gd + juice_curves.gd (easings, exact springs, the
                anticipation curve, material tokens), feel_constants.gd (FeelConstants resource,
                data/feel/feel_default.tres), fx_defs.gd (per-unit fx sheets, data/fx_units.json),
                vfx.gd (Vfx router: event queue, governor, allow(), trace), particle_pool.gd
                (GPU/CPU burst pools, data/fx_particles.json), ground_marks.gd + ground_mark.gdshader
                (decal-substitute ground quads), popup_text.gd + combat_text.gd (the only world
                text + its policy), material_flash.gd, combat_fx.gd (impacts, clash, deaths),
                missile_fx.gd + trail.gdshader (release tells, trails, stuck missiles),
                body_juice.gd (unit body composer), order_markers.gd (CMB-08..11, rally flag),
                camera_juice.gd (CAM-05 trauma + kick), selection_circles.gd (rings, hover),
                health_bars.gd + health_bar.gdshader (ghost bar), fx_textures.gd, proc_mesh.gd,
                vehicle_rig.gd (procedural motion of multi-node siege models)
data/           see data/SCHEMA.md: factions, units, buildings, heroes, abilities, buffs, items,
                upgrades, shops, creep_camps, doodads, scenarios (.json), strings/en.json,
                maps/*.json, test_defs.json (tests only)
assets/         models/{units,vehicles,buildings,neutral,doodads}/ textures/ icons/
                audio/{sfx,voice,music,ambience}/ ui/
tools/          python asset tooling (bpy, image processing), asset manifest,
                maps/build_slice_map.py (writes data/maps/slice.json from the sketch + brief),
                ip/check_banned_terms.py, ip/check_value_echo.py,
                gen_input_map.gd (regenerates project.godot [input] from Settings.default_actions())
tests/          headless test runner (tests/unit), scripted playtests + screenshots (tests/playtest)
docs/           design, research, this file
```

## 4. Simulation core

`World` (`src/world/world.gd`, scene `src/world/world.tscn`) is the match root. It owns systems
as child nodes and runs them in this order every tick (`dt = 1/30`). A system is any node with
`sim_tick(world: World, dt: float)` registered with `world.register_system(stage, node)`
(stages are the names below); `World.step()` runs `orders`, `units` and `cleanup` itself, so
those three are rejected (`push_error`, returns false), as are unknown names
(`World.is_system_stage(stage)`). Several systems may share a stage: they run in registration
order (`systems_in(stage)` lists them; `Combat` is the first `projectiles` system).
Scene children: `Terrain` (TerrainBuilder), `Doodads`, `Units` (unit container), `DayNight`
(`Sun` light + environment), `Fx` (`SelectionCircles`, `HealthBars`), `Systems`.
`World.visuals = false` skips terrain/fx/views (headless tests); `World.auto_tick = false`
lets tests drive `step()` manually.

1. `orders`  — commands queued by input/AI since the last tick are applied (`World._apply_commands`)
2. `production` — `construction` (sites, repair, garrisons), `production` (queues), `tech` (tiers, research effects)
3. `units` — each `Unit.sim_tick(dt)`: summon lifetime, stun / root, the current order's handler, movement (pathing+steering), attacks
4. `projectiles` — `combat` (first), projectiles
5. `abilities` — `abilities` (casts, cooldowns, ground effects), `buffs` (durations, DoTs, auras, regen), `items` (use, recall channels)
6. `economy` — `economy` (income, upkeep tier), `heroes` (XP, revive), `shops` (stock, restock)
7. `creeps` — `creeps` (camps, leash, sleep, bounty)
8. `ai` — one `AiPlayer` per AI seat (throttled to `rules.ai.<difficulty>.think_interval`)
9. `fog` — `fog` (visibility recompute, throttled to `rules.vision.fog_update`)
10. `cleanup` — dead entity removal (`died` hooks, then `unit_died`), removed units freed

The gameplay systems are `SimSystem`s (`src/systems/sim_system.gd`: `setup(world)`,
`sim_tick(world, dt)`, `hooks()`, `on_unit_spawned/died/removed/damaged`, `handle_command`).
`World.SYSTEM_STAGES` lists them as `[property, stage, script]`; `World.setup` installs each as
a child of `Systems`, stores it in the typed property (`world.economy`, `world.construction`,
`world.production`, `world.tech`, `world.heroes`, `world.abilities`, `world.buffs`,
`world.items`, `world.shops`, `world.creeps`, `world.fog`) and registers it for its stage in
that order. A system returns the hook names it wants from `hooks()` (`&"spawned"`, `&"died"`,
`&"removed"`, `&"damaged"`); World calls them after `spawn_unit`, in cleanup, from
`remove_unit` and from `Unit.take_damage`. Each system file starts with its owner,
responsibilities, signals, commands and callers; `docs/m2-ownership.md` maps owners and the
cross-system call contracts.

`World` exposes: `tick_count:int`, `time:float` (sim seconds), `players:Array[PlayerState]`,
`entities:Dictionary(id->Unit)`, `unit_list:Array[Unit]` (stable spawn order — iterate this),
`spatial:SpatialHash`, `pathing:Pathing`, `map:MapData`, the systems above, `ai_players`,
`local_player_id`, `rng` (seeded), and helpers `setup(map, seed)`, `step()`,
`add_player(id, team, faction, ai = false, difficulty = "normal")` (an AI seat gets an
`AiPlayer` registered in the `ai` stage),
`player(id)`, `team_of`, `is_enemy` (O(1): a player x player table rebuilt by `add_player`;
call `refresh_relations()` after changing a team), `hostile_mask(pid)` (bitmask of the player
ids `pid` fights; player ids are 0..15), `is_ally`, `player_color`,
`interpolation_fraction()` (visual only, see §1), `max_unit_radius` (from Defs),
`spawn_unit(def_id, player_id, pos, facing=0, opts={})` (structures snap to their footprint and
block pathing unless `blocks_pathing` is false; mobile units snap to the nearest walkable cell;
`opts`: `under_construction`, `hp_fraction`, `food_reserved`), `remove_unit(u)` (out of the
sim without dying: picked-up items, transforms; `removed` hooks), `set_hidden(u, hide)` (in a
mine or garrison: out of the spatial hash, keeps its orders), `adjust_food(pid, used, cap)`,
`notify_damaged(u, amount, src)`, `get_unit(id)`, `units_of_player`,
`query_radius(pos, r, filter:Callable, out:Array)`, `issue(command:Dictionary)`,
`mark_dead(unit, killer)`, `raycast_ground(origin, dir)`, `resolve_smart(unit, target)`,
`combat:Combat` (child of `Systems`, registered for the `projectiles` stage),
`projectile_root` (`Projectiles` node), `gather_handler:Callable(worker, resource)` (legacy
test hook: when set it wins over `Economy.on_gather_reached`) and `corpse_count()`.
Death: `Unit.die()` marks the unit; `cleanup` takes it out of the sim (spatial hash, `entities`,
`unit_list`), frees its footprint, releases its food, runs the `died` hooks and emits
`unit_died`. The node stays as a
corpse (UnitView plays topple + sink) for `Unit.decay_ticks()` (`combat.defaults.corpse_decay`
8 s, `structure_decay` 4 s, or a def `decay`), then `cleanup` frees it. Corpse removal is sim
time, so it is identical on every machine. `spawn_unit`/`cleanup` also keep
`PlayerState.food_used` (unit `cost.food`; not for `food_from_source` transforms, not twice for
units Production already reserved) and `food_cap` (`food_provided`, only once a site is
finished) up to date.

Commands are plain dictionaries so input, AI, tests and (later) replays/network share one path:
```
{ "type": <unit order name> | <system command name>,
  "player": int, "units": [ids], "pos": Vector3?, "target": id?, "def": String?,
  "ability": String?, "slot": int?, "tree": int?, "data": Dictionary?, "queue": bool }
```
Commands are applied at the start of the next tick. Only units owned by `player` obey. A
command whose `target` died before it applied falls back to its `pos`, or is dropped.

- **Unit orders** (`Order.TYPE_NAMES`): `move, stop, hold, patrol, attack_move, attack, smart,
  follow, gather, return` / `return_resources, build, repair, cast, learn, use_item,
  pickup_item, drop_item, give_item` (a drop onto an own hero), `attack_ground, enter, rally`.
  `def` → `Order.def_id` (building to place), `ability` → `Order.ability`, `slot` →
  `Order.slot` (inventory slot), `data` is copied into `Order.data`. A `cast` given to a
  structure goes to `AbilitySystem.handle_command` instead (building abilities).
- **System commands** (`World.SYSTEM_COMMANDS`, never unit orders): `train`, `cancel`,
  `research` → `Production`; `buy`, `sell`, `service` → `ShopSystem`; `revive` →
  `HeroSystem`; `autocast` → `AbilitySystem`. World calls `system.handle_command(cmd, units)`
  with the command's living units owned by `player`.
- **Smart** (right-click) is resolved **per unit** by `World.resolve_smart(u, target)`:
  structures that train units → `rally` (sets `rally_pos`/`rally_id`, never becomes a running
  order); ground item → `pickup_item` (`ItemSystem.can_pickup`); resource → `gather` for
  workers; enemy → `attack` (`follow` if the unit has no weapon); own construction site →
  `build` (help build); own drop-off while carrying → `return_resources`; own garrison with
  room → `enter`; damaged allied structure / mechanical unit for a worker with a repair
  ability → `repair`; mobile ally → `follow`; anything else → `move` (a follow on a building
  never ends). On the ground `resolve_smart_point(u, tree)`: rally for producers, `gather` for
  workers when a living tree lies within `TREE_CLICK_RADIUS` (1.2 m) of the click (the tree
  index goes into `Order.data.tree`), else `move`. `attack` without a target is an
  `attack_move`.
Group moves keep a compact group's formation (offsets from the group centre when its spread is
< 8 m); otherwise everyone heads for the point and separation spreads them. A formation order
also carries the group's slowest member speed (`Order.march_speed` → `Unit.march_speed`, rules
§7.10): every member keeps to it until it engages or the order ends, so the group arrives as a
group. Every ground move / attack-move / patrol given to 2+ units carries one `GroupPath`
(`Order.group_path`) so the group shares its path searches (§6). An idle unit moved only by
shoves and separation (allies walking through) steps back to where it stood once nobody has
pushed it for 0.5 s, if it ended up 0.75-4 m away and the spot is free
(`Unit.SHOVE_*`).

### Scenarios

A scripted match set-up is data (`data/scenarios.json`, `Defs.scenario(id)`, SCHEMA §15) run by
a `SimSystem` in `src/scenarios/`. `BattlefieldScenario` (Playtest 1, Main scenario
"battlefield"): `add_players(world, id)` (static: players with colours and start resources,
the two neutral players, local player 0), then Main spawns the map's Gold Seams and neutral
buildings, then `setup_match(world, id)` places every finished structure (nearest legal free
spot), the unit groups in rows, heroes at `hero_level`, the listed creep camps, and registers
the scenario for the `ai` stage. Each think (`think_interval`) it checks the annihilation
victory (`result`, `PlayerState.defeated`, `ended(winner)` + `Events.match_ended`) and plays
every `scenario_ai` player's groups: guards hold, defend (`defend_radius`), assist and regroup;
the wave attack-moves at the enemy hall after `attack_after` s (with a notification and an
alert, so Space jumps to it) and then hunts; when the enemy has no fighting unit left every
group hunts. It issues only command dictionaries and uses no clock or RNG (deterministic).
Queries: `group(id, pid)`, `members(g)`, `wave_eta()`, `wave_marching()`, `camera_start(pid)`,
`entity_count(pid)`, `is_over()`.

## 5. Entities

`Unit` (`src/entities/unit.gd`, `class_name Unit extends Node3D`) represents **every** game object
with an id: mobile units, heroes, workers, buildings, gold mines, critters. Trees are NOT entities
(they are cells in `Doodads`, see §7) to keep counts low.

Key fields: `id, def_id, def:Dictionary, player_id, team, hp, max_hp, mana, max_mana, armor,
armor_type, radius, speed, sight, flags (is_building, is_hero, is_worker, is_resource, is_flying),
orders:Array[Order], current:Order, attack:Dictionary, abilities:Array, buffs:Array,
carry_gold, carry_lumber, hero:Dictionary (HeroSystem: hero_id, level, xp, skill_points, ranks,
attr_bonus, proper_name), inventory:Array (6), level, is_item / item_id / item_charges (ground
items), is_summoned, is_mechanical, lifetime_ticks, camp_id, under_construction,
build_progress, garrison, hidden, autocast, cooldowns, status, mod_totals, hp_regen,
mana_regen, sight_night`.
**Stat pipeline**: live stats = base stats (from the def, `set_base_stats` for heroes and
transforms) + every modifier source. A system owns one source and replaces it whole with
`set_modifiers(source, mods)` (`&"tech"`, `&"hero"`, `&"items"`, `&"buffs"`...; `{}` removes
it); `recompute_stats()` sums them (`max_hp`, `max_hp_pct`, `max_mana`, `armor`, `damage`,
`damage_pct`, `attack_speed_pct`, `move_speed`, `move_speed_pct`, `range`, `sight`,
`hp_regen`, `mana_regen`, `miss_chance` / `evasion` (max wins), `crit`, `damage_taken_pct`,
`status` lists). Missing HP/mana are kept when the maximum grows; speed and attack speed are
clamped by `combat.move_speed_clamp` / `attack_speed_clamp`. Statuses (`Unit.STATUS_FLAGS`:
`stun, root, silence, disarm, invulnerable, cannot_die, hidden, invisible, sleep, taunt,
ignore_slows, no_displace`) set `stunned`, `rooted`, `silenced`, `disarmed`, `cannot_die`
(damage stops at 1 HP), `is_invulnerable`; a stunned or sleeping unit does not act, a rooted
one does not move. Nothing else writes stats.
Sim state (written only in `sim_tick`): `pos:Vector3` (authoritative position; the Node3D
transform is a copy written once per tick), `prev_pos`, `facing` (yaw, forward = -Z rotated),
`target_radius` (centre-to-edge reach for target queries: footprint half-diagonal for
structures, else `radius`; `Defs.max_target_radius` is the largest over all defs),
`velocity` (actual displacement / dt), `holding`, `footprint:Rect2i` (structures),
`hash_bucket` (SpatialHash), `path`, `died_tick`. Weapon fields (from `def.attack`, timings
converted to integer ticks): `attack_type, damage_min, damage_max, attack_range,
acquire_range, leash_range, projectile, cooldown_ticks, damage_point_ticks, backswing_ticks`.
Helpers: `issue_order(order, queue)`, `clear_orders()`, `teleport(p)`, `take_damage(amount,
src)`, `die(killer)`, `display_pos()`, `is_mobile()`, `is_large()` (radius > 0.5 → inflated
pathing grid), `can_attack()`, `can_train()`, `is_creep()`, `edge_distance(other)` (edge to
edge; footprint rectangle for structures — all ranges are measured this way),
`find_target(r)`, `is_valid_target(o)`, `combat_target_id()`, `hit_point()`, and visual-only
readers `swing_progress()`, `damage_point_ratio()`, `dead_time()`.
`Order` (`src/entities/order.gd`): `type:Order.Type`, `target_pos`, `target_id` (0 = none),
`def_id`, `ability`, `slot`, `data` (per-order state; a system driving the order sets
`data.phase`), `group_path`; `Order.make(type, pos, target)`, `Order.type_from_string(s)`.
New types are appended to the enum (never reordered).
**Order handlers** (`src/entities/orders/`): each `Order.Type` has one stateless
`OrderHandler` (`OrderHandlers.of(type)`, `OrderHandlers.idle()` for a unit without orders):
`can_start(u, o)` (refuse at issue time), `enter(u, o)`, `tick(u, o, dt) -> Vector3` (desired
velocity; `u.finish_order()` completes), `exit(u, o)` (always called when the order ends or is
replaced), `accepts_retaliation(u, o)`, `is_instant()` + `apply_instant(u, o)` (learn: runs
without interrupting the current order), `allows_immobile()` (towers, immobile summons).
Handlers use the public Unit API (`order_goal, begin_move, stop_moving, follow_path,
chase_move, chase_point, steer_direct, face, scan, engage, engaged, fight, give_up, is_lost,
return_to, settle, home_pos, set_home, cancel_swing, edge_distance_to_point, heal`).
Implemented: `idle` (acquire, retaliate, guard return; stationary towers fire from place),
`move`, `stop`, `hold`, `attack`, `attack_move`, `patrol`, `follow`. Hand-off handlers (walk,
then call the owning system; their file headers state the contract): `gather` and
`return_resources` (Economy), `build`, `repair`, `enter` (Construction), `cast`
(AbilitySystem), `learn` (HeroSystem), `use_item`, `pickup_item`, `drop_item` (ItemSystem),
`attack_ground` (`Combat.fire_at_point`). Shift-queues hold at most `rules.controls.shift_queue_max` (32) orders.
Order behaviour: MOVE follows its path and completes on arrival (or when stalled next to a
crowded goal) and ignores enemies; STOP clears the queue (and cancels a wind-up); HOLD never
completes, cannot be pushed and attacks only enemies already in weapon range, never moving;
ATTACK chases its target until it dies (no leash); ATTACK_MOVE follows its path, engages
anything acquired on the way and re-paths to its goal after each fight; PATROL is an
attack-move that ping-pongs forever; FOLLOW keeps within 1.2 m of a mobile ally (and fights
back when hit, then resumes); shift-queued orders start when the current one completes.
Combat behaviour (all in `Unit.sim_tick`, integer tick timers):
- **Acquisition**: idle, attack-moving and patrolling units scan every `SCAN_TICKS` (5, staggered
  by id) for the closest valid enemy within `acquire_range` (structures get a 6 m penalty so
  units are preferred; ties by id). `acquire = 0` (workers) never auto-acquires or retaliates.
  The scan uses `SpatialHash.query_hostile` (only buckets holding hostile players are looked
  at), so its cost follows the nearby enemies, not the friendly crowd. Melee units skip targets
  they cannot walk to (`Pathing.can_reach`: region labels of the target's cell or footprint
  ring), unless already in weapon range; ranged units may shoot across cliffs and water.
- **Retaliation**: an idle, attack-moving, patrolling or following unit that is hit engages the
  attacker (a follower resumes following afterwards); not a target it just gave up on, and for
  melee units not one it cannot reach. **The camp acts as one** (rules §15.1): when a creep
  auto-acquires a target or is hit (even while it is already fighting), `CreepSystem.alert_camp`
  makes every awake, idle member of its `camp_id` that can reach the target engage it (other
  camps never join; `camp_aggro` once per pull, the camp calms when nobody fights). A creep
  without a camp wakes idle creeps within `help_radius` (6 m).
- **Chasing**: path requests at most every `REPATH_TICKS` (10) and only when the target drifted
  more than 1 m from the last goal; at a stale goal the unit steers straight at the target. A
  target within `DIRECT_CHASE` (5 m) and in plain sight (`line_of_walk`) is chased without a
  path query (most of a melee). Path queries remain subject to the per-tick budget.
- **Leash**: auto-acquired fights are dropped when the unit gets `leash` (def, default 14 m;
  creeps 18.75 m) from its guard position, when the target escapes beyond
  `max(acquire, distance at engagement) + 3 m`, or after ~1.5 s without chase progress (that
  target is then ignored for 3 s). Idle units walk back to their guard position (creeps to
  their camp, ignoring hits on the way); attack-move resumes its path.
- **Attack swing**: in range and facing the target (±0.35 rad, turning at `turn_rate`), the unit
  starts a swing and its cooldown at once; at `damage_point` melee damage is dealt (or the
  projectile launched) if the target is still within `range + 2.5 m` (range buffer); the
  backswing follows. A new order before the damage point cancels the swing and refunds the
  cooldown; during the backswing it just ends it. Units do not move while swinging.

Signals via `Events` autoload: `unit_spawned(u)`, `unit_died(u, killer)`, `unit_damaged(u, amount, src)`,
`order_issued(u, order)`, `building_completed(u)`, `training_completed(building, unit)`,
`resources_changed(player_id)`, `hero_level_up(u)`, `research_completed(player_id, id)`,
`selection_changed(units)`, `notification(player_id, kind, text)`, plus `alert_raised(player_id,
pos)` (space bar jumps the camera to the latest; `Combat` raises it, with an "under_attack"
notification, when a player's unit is hit by an enemy, at most every `alert_interval` 8 s),
`tree_felled(pos)`, `command_issued(command)`, `menu_requested` (F10) and
`match_ended(winner, reason)` (the match is decided: winning player id or -1, e.g.
"annihilation"; juice SEQ-02 listens), plus one block of
signals per M2 system (economy, construction, production, tech, heroes, abilities, buffs,
items, shops, creeps, fog; listed by owner in `docs/m2-ownership.md` §6 and documented in each
system's header). Signals are emitted immediately; deaths are deferred to `cleanup`.

Visuals are a child `UnitView` (`src/entities/unit_view.gd`; visual only, reads sim state, never
writes it). Model: `AssetLibrary.model_path(def, def_id)` = the def's `model` (`"units/<name>"`, a bare
name or a res:// path), else the unit manifest alias for the def id (`kingdom_pavisier` →
`kingdom_infantry`), else `assets/models/{units,buildings,neutral}/<def_id>.glb`, else a placeholder from
the def's `shape` hint (`humanoid` capsule + head + team band; `building` box + roof + banner; `mine`
mound with nuggets; merged into one vertex-coloured mesh per (def, team colour)). Units render at
native GLB size × `def.model_scale` (default `def.scale`); **structures are scaled uniformly to their
data footprint** (footprint metres / the building manifest's `footprint_m` or the model AABB;
`model_fit: "none"` keeps `model_scale` / `scale`). Upgraded halls point `model` at the T1 hall and
list their add-on in `model_addons` (data/SCHEMA.md): each add-on is parented in the hall's model
space (a building-manifest `addon_of` entry loaded directly is likewise parented with its T1 hall).
A def with `model_depleted` (Gold Seam) swaps to that model on `Events.mine_depleted`. Every
imported material is converted once
(cached per source material) to the shared painterly shaders in `src/render/`: `unit.gdshader`
(wrap-Lambert + soft two-band key, no specular, model-space value gradient, team colour from the
`<model>_team.png` texel mask + magenta key or a grey `TEAM` surface multiplied, team-colour rim
(units 0.35, heroes 0.55, team colour × 0.6; a model whose measured team share of its silhouette,
`assets/models/units/team_coverage.json` from `tools/assets/check_team_coverage.gd`, is below the
art bible's 10 % gets up to 0.8, × 0.95 and a wider rim (`AssetLibrary.team_deficit`), a stopgap
until its mask is repainted), energy-conserving latched hit flash, corpse team-colour ebb, night unit fill), `structure.gdshader`
(same + vertex AO, `GLOW/LAMP/EMBER/GLYPH` emission × `glow_energy`, construction reveal) and
`foliage.gdshader` (`SWAY` surfaces). Per-instance values are **instance uniforms in a fixed slot
map** (`src/render/unit_uniforms.gdshaderinc`, juice bible R4: 0 `flash` (t0 on the fx clock,
strength, duration), 1 `flash_tint`, 2 `rim_boost`, 3 `team_sat`, 4 `sat_front`, 5–6 hero status,
7 `rim_col`, 8–10 economy props, 11 `variant_a` (structures: x = build progress), 12 reserved,
13 `team_color`), written only when they change. Hooks: `flash(strength, tint, duration, hold)`
(through `MaterialFlash`; slot 0 w = hold s), `set_selected()` / `set_hovered()` (rim boost;
`ViewHooks` forwards `selection_changed`, `SelectionCircles` the hover), `set_rim_pulse(v)`
(target flash), `juice: BodyJuice` (the body composer, writes `rig` once per frame), optional
sim publishers read by duck typing: `build_progress` (0..1), `anim_hint` ("work" / "cast") with
`work_progress()` / `cast_progress()` (+ `*_point_ratio()`, `*_time()`).
Animation (rigged GLBs, `AnimationPlayer` in manual mode, advanced every frame with real delta):
clips **`idle, walk, attack, death, work, cast`** with fallbacks (attack ← work ← cast; idle ← walk);
`idle/walk/work/run` loop (LOOP_LINEAR), others play once; 0.15 s crossfades. Walk playback = actual
speed / `walk_anim_speed` × model scale (stride matching, from `assets/models/units/manifest.json`).
Attack / cast / work clips are **positioned from the sim swing progress**: `[0, damage point]` maps
to `[start_s, hit_s]` and the backswing to `[hit_s, end_s]` (manifest `attack_hit_s` = peak
weapon-hand speed; the wind-up start is pulled in so it never plays faster than 3× or slower than
0.6×), so the strike frame lands exactly on the sim damage point at any frame rate. Death plays once
from `dead_time()` and holds; the team colour ebbs from 0.7 s over 1.4 s (feet to head) and the body
sinks over the last 1.5 s before removal. Off-screen rigs skip skeleton work (frustum sphere test) and
loops catch up when seen. **Vehicles** (`assets/models/vehicles/`, built by `tools/kits/siege.py`:
the Bombard Wagon, the Sling-Cart) have no skeleton: their moving parts are child nodes at their
pivots (`Wheel_*`, `Barrel`, `Arm`, `Crew_*`, `Crew_*_Leg_*`) and `VehicleRig` (`src/fx/vehicle_rig.gd`,
`UnitView.vehicle`) animates them: wheels roll by the distance the display position travels along
the facing (the same at any frame rate), the crew's legs swing and bodies bob on that phase, the
barrel's recoil latches on the fx clock at the sim's damage point (40 ms back, 0.12 s hold, 0.8 s out
to battery) and the throwing arm cocks, whips to the release on the damage point and settles.
Other models without clips fall back to procedural motion (bob/lean, lunge or
draw peaking at the damage point, topple + sink; structures sink and tilt).
`src/render/unit_manifest_builder.gd` regenerates the unit manifest (clip lengths, stride speed from
`tools/autorig.py`'s QA `stance_speed_mps` when its logs are given, else measured from the toe bones;
strike / cast / work hit frames; death settle time). Selection circle and health bar are rendered by
`fx/` systems, not by `UnitView`.
`Projectile` (`src/entities/projectile.gd`, `Node3D` under `World/Projectiles`): simulated in
the `projectiles` stage; homes on its target's current `hit_point()` along a parabola whose peak
is `arc × flight distance`, carries the base damage rolled at launch, and on arrival `Combat`
applies it (a projectile whose target died lands harmlessly). Its transform is written once per
tick (physics interpolated); on arrival it is committed at the impact point and the node stays
one more tick (`landed`) so the interpolated arrow visibly reaches the target before `Combat`
frees it. Visuals are procedural meshes per projectile `model` id (arrow, javelin, bullet, iron
bombard ball, lidded clay pot, coal lump, arcane bolt, ice pellet).

## 6. Movement & pathing

- `Pathing` (`src/world/pathing.gd`) wraps `AStarGrid2D` over the 0.5 m cell grid
  (`DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES`, octile heuristic). Blocked cells: cliff edges (one cell
  each side of a wall), water, the map border ring, trees, building footprints (reference
  counted). Clearance for units with radius > 0.5 uses a second grid with obstacles inflated by
  one cell (`large = true` on queries).
- **JPS is disabled** (deviation from the first draft): on the 384×384 slice Godot's JPS took
  10–25 ms per cross-map query and ignores weights. Instead every cell's weight scale is 0.66,
  i.e. weighted A* (heuristic ×1.5): ~0.5–1.5 ms per cross-map query, path length within ~1 %
  after string pulling.
- Connected-component labels (both grids) make unreachable goals cheap: `find_path` snaps a
  blocked or unreachable goal to the closest walkable cell reachable from the start (ring
  search, 48 m), instead of letting A* exhaust the grid. Merges (tree cut, building removed)
  relabel immediately. A new obstacle only triggers a relabel when the walkable cells around it
  cannot reach each other inside a small window (buildings in the open never do); that relabel
  runs incrementally in `begin_tick()` (6k cells/tick ≈ 3–4 ms, ~3 s for the slice). Until it
  finishes, labels may claim two split areas are connected; queries stay correct, just slower.
  Cells that become solid while it runs are cleared in the job's arrays too (they replace the
  live labels at the end), so a solid cell never carries a region label.
- `find_path(from:Vector3, to:Vector3, large:=false) -> PackedVector3Array` (y = 0; callers
  sample height), then string-pulls over corner points with `line_of_walk(a, b)` (grid
  traversal of the centre line plus two lines offset by 0.3 m; the pull advances on the centre
  ray and confirms the chosen segment with the side rays). Also: `is_walkable(cell)`,
  `is_walkable_world(pos)`, `nearest_walkable(cell)`, `closest_reachable(start, cell)`,
  `same_region(a, b)`, `can_reach(from_cell, rect)` (melee target filter), `set_tree(cell,
  present)`, `set_footprint(cells, blocked)`, `set_footprint_rect(rect, blocked)`,
  `is_rect_free(rect)`.
- Path requests are budgeted per tick by count **and cost** (deterministic, no clocks):
  `begin_tick()` resets; a query is charged `QUERY_BASE_COST` (16) + its path length in cells
  (estimated from the octile distance by `can_query(from, to)` before it runs, the real length
  after). `can_query` admits a query while the estimate fits in `cost_budget` (default 2000
  cells ≈ 5–6 ms, i.e. ~6 cross-map queries of ~300 cells) and fewer than
  `max_queries_per_tick` (24) ran; the first query of a tick always runs. Units that miss out
  retry next tick. 24 short chase re-paths (~30 cells each) fit easily; a burst of long
  queries spreads over a few ticks instead of spiking one.
- `GroupPath` (`src/world/group_path.gd`): one per group command. The first unit to need a
  path queries it and offers it as a base; others whose formation slot starts within 12 m of a
  base derive theirs with line checks (charged 0.2 per checked cell): the base waypoints
  shifted by their formation offset, each waypoint taking the full, half or no offset (the
  first that is in straight walking reach, backtracking to narrow the previous waypoint when
  none is, at most 4 checks per waypoint), so a group marches on parallel lanes and narrows
  only at chokepoints; else the base waypoints themselves, joined at one of the first 3 in
  straight reach. Units that fit neither query
  their own path (a new base, max 16). Only an order's first path uses it; re-paths after
  fights or stalls are ordinary queries. Measured: 250 units ordered across the slice = 4 A*
  queries, all paths assigned within 2 ticks.
- `SpatialHash` (`src/world/spatial_hash.gd`): 2 m buckets over the map, units stored by `pos`
  with incremental `update(u)`; `query_radius(p, r, out)` / `query_rect(rect, out)` fill a
  caller-owned array (no per-query allocation). Each bucket and each 4×4-bucket block keeps a
  bitmask of the players present, so `query_hostile(p, r, mask, out)` (acquisition) skips
  areas without enemies; it returns units whose centre is within `r + u.target_radius`.
  `player_id` must not change while a unit is inserted.
- Local movement = path following + separation steering from overlapping neighbours (query
  radius = own radius + the largest unit radius), allies push idle allies aside (WC3-like; same
  player, idle, not holding), units never enter blocked cells (slide along them) and never
  step diagonally between two blocked cells that only touch at a corner (the A* diagonal rule,
  so they cannot reach pockets the pathfinder and labels treat as closed). Height `y` sampled
  from `MapData.height_at(x,z)`.
  Measured (headless, 4-core Xeon 2.1 GHz, `tests/unit/test_perf.gd`): 250 units packed at
  1.1 m, idle ≈ 2 ms avg / 2 ms worst tick, attack-moving ≈ 4 / 9 ms; 250 units ordered across
  the slice in one command ≈ 4 / 13 ms (the order's path burst); 2 × 125 approach and clash ≈ 5 /
  10 ms; 200 units brawling ≈ 3.5 / 10 ms (before the review fixes the review harness
  measured 12 / 21, 17 / 32, 18 / 37 and 12 / 29 ms for comparable scenarios). Tests assert
  avg < 12 ms and worst tick < 20 ms (tick budget 33 ms; the rest is reserved for fog, AI,
  abilities, economy).
- Buildings call `pathing.set_footprint(cells, blocked)` on placement/death; trees on harvest.

## 7. Map, terrain, doodads

- `MapData` loads `data/maps/<name>.json` (format: `data/SCHEMA.md` §12): size in tiles, per-tile
  `tex` index (0..7), per-tile `cliff` level (deviation from "per-vertex": per-tile levels give
  clean vertical walls between tiles), `water`, `boundary` (unpathable, unbuildable edge tiles;
  `is_boundary_tile`), an explicit `ramps` list (`rect` in tiles, ascending `dir`, `low` level; a ramp
  is 2 tiles long and rises exactly one level), start locations, gold mines, `trees`
  (`[x, z, type]` on the 1 m tree grid), creep camps (`{id, template, side, pos, creeps,
  facing, layout?}`), neutral buildings (`{def, pos, facing}`) and an authored `meta` block
  (starts, expansions, `gold_amounts` → `mine_gold(i)`, creep route, lanes, landmarks,
  critters, ramp names) kept verbatim. Layers serialize as one digit string per row. `compute_heights()` derives 4 corner heights per tile (flat, ramp slope,
  or sunken lake bed); `height_at(x, z)` is the bilinear surface and matches the mesh exactly.
  Also `has_wall_x/z`, `compute_blocked_cells()`, `raycast(origin, dir)`, `to_dict/from_dict`,
  `load_json/save_json`. Tests can build a `MapData` in code.
- **The slice map** `data/maps/slice.json` ("Wether Downs", 96 × 96 tiles, mirror-symmetric
  across the x = z diagonal) is generated by `tools/maps/build_slice_map.py` from
  `data/maps/wether_downs_sketch.txt` and `docs/design/slice-plan.md` (cliff levels by flood
  fill, the exact ramp table, flattened hall/seam pads with the 6 m hall–seam gap, cleared camp
  areas, tree walls as checkerboard pairs so they are impassable): 2 starts, 5 gold seams, 16
  camps, 3 neutral buildings, 12 ramps, ~5100 trees. Never hand-edit it; rerun the tool.
  `tests/unit/test_slice_map.gd` checks symmetry, pads, reachability and the sleep mix.
- `MapGenerator.test_map(seed)` (`src/world/map_generator.gd`) builds the deterministic,
  point-symmetric 96×96 test slice: level-1 base, level-0 basin with a lake, two level-2 plateaus
  with a level-3 hill each, 10 ramps, forest border + noise clusters + a lumber line behind each
  base, 2 starts with gold mines, 4 creep camps (sandbox scenario and engine tests).
- `TerrainBuilder` generates chunked `ArrayMesh` (16×16 tiles per chunk): tile tops (2×2
  subdivided) at their corner heights + vertical cliff walls with noise bulges (seams stay exact),
  ramps as slopes; `UV2 = (1, height fraction up the wall)` marks cliff walls; tile-top `COLOR.r` =
  cliff-foot AO, `COLOR.g` = cliff-top lip. Ground look: the Greenvale 7-tile ladder
  (`TerrainTextures.ladder_array()`, a `Texture2DArray` in draw order 0 `gv_scree`, 1 `gv_cracked`,
  2 `gv_dirt`, 3 `gv_road`, 4 `gv_grassy_dirt`, 5 `gv_meadow`, 6 `gv_thick_meadow`) blended with an
  **ordered 16-case corner mask** on the dual grid of tile centres: per present slot L (in draw
  order) the 4-bit mask "corner slot ≥ L" is interpolated and thresholded against world-space noise
  (0.35 tile amplitude, ~1.7 cycles per tile) with a painted rim — no soft splats. Per-tile data in
  `tile_info` (RGBA8, nearest): R = ladder slot, G = 8 connectivity bits (no blending across a
  wall). `MapData.tex` legacy indices map to the ladder through `LEGACY_TO_LADDER` (maps authored
  in ladder order set `tex_set = "gv_ladder"`); ramps paint `gv_dirt`, cliff feet get a `gv_scree`
  band. `paint_tiles(rect, slot)` repaints at runtime (building pads via `ViewHooks`). World-space UVs
  (~6 m per repeat), two rotated samples + 45 m macro tint; walls are triplanar `cliff_limestone`
  (warped, two scales, dark foot, mossy lighter lip); wet band and tinted bed at the water line.
  Fog hook: `fog_tex` (L8: 0 unexplored, 0.5 fogged, 1 visible), `fog_enabled`, `map_size_m`
  — shared by the foliage and water shaders; `TerrainBuilder.set_fog_texture(tex)`.
- `Doodads` stores trees on a 1 m tree grid (one tree = 2×2 cells), lumber per tree from
  `data/doodads.json`, handles `harvest(tree, amount)`, `remove_tree`, `tree_at_cell`,
  `nearest_tree`; depleted trees free their cells and emit `tree_felled`. Visuals: the doodad kit's
  hill oak / linden / hazel GLBs (species picked per tree by hash from the map tree type; card-cluster
  trees from `assets/textures/foliage` when missing), canopy-fitted to the 1 m grid, one MultiMesh
  per (species, LOD, 32 m chunk); enclosed trees use LOD1 and are promoted to the full mesh when a
  neighbour falls; a stump replaces a felled tree; instance hue/value jitter in `INSTANCE_CUSTOM`
  (instance colours white: Compatibility multiplies COLOR by them). Plus a deterministic,
  non-blocking decor scatter (tufts, wildflowers, scree rocks, reeds, lily pads, mushrooms) cleared
  under building footprints (`clear_decor`). Wind sway in `foliage.gdshader` (COLOR.r weight).
- Water: `water_ripples` scrolled at two scales, shallow/deep by depth read from a terrain height
  texture (no depth buffer, Compatibility-safe), foam line at the shore, ripple-normal glint.
- Lighting (`DayNight`, visual only): `TimeOfDay` keys (juice world §5.1) drive a sun (50–55° from
  screen lower-left by day, low at dawn/dusk) and a moon (#8EA6FF) with the shadow hand-over,
  coloured ambient, Reinhard (white 1.5), depth fog 32–90 m in the key colour, glow above HDR 1.1,
  per-hour saturation/contrast + a procedural grading LUT (`ColorGrade`), and through `RenderAtmos`
  the shared uniforms: fx clock, drifting cloud shadows, night unit fill, window/lamp glow.

## 8. Fog of war

`Fog` (`src/world/fog.gd`, stage `fog`; rules §14). Off until `enabled` is set: Main turns it on
for the slice and battlefield scenarios when `rules.vision.fog_of_war` is true (engine tests keep
"everything visible"). Queries: `Fog.state_at(pid, pos) -> UNEXPLORED | FOGGED | VISIBLE`,
`is_visible(pid, pos)`, `is_explored(pid, pos)`, `can_see(pid, unit)` (the cell under its centre,
any footprint / body cell for structures and units over 0.7 m; own and allied units always),
`shows(pid, unit)` (what the view draws: visible units plus structures the team has seen, their
ghosts), `seen_structure`, `reveal(pid, pos, radius, duration, detect) -> handle` (timed, ignores
occluders, expires in the sim), `reveals()`, `grid(pid)` (L8 bytes), `texture(pid)` (an
`ImageTexture`, L8: 0 unexplored, 128 fogged, 255 visible), `night_factor(t)`, `update_now(world)`.
Neutral players have no fog.
Model: one grid per team (allies share vision) at `rules.vision.fog_cell` **2 m** (96 × 96 on the
slice; the classic game's resolution; 1 m cost 4× per re-stamp in GDScript). Per cell: a count of
the sight sources seeing it, an explored flag and the texture byte, kept current as counts change.
Every living, not-hidden unit of a non-neutral player is a source; it is stamped into its team's
counts and remembers the cells it marked, and is re-stamped only when its cell, sight radius (day /
night, 3.2 s transition) or eye level changes; dying or leaving the sim unstamps it at once. Line
of sight uses precomputed ray stamps (each offset knows its parent one step nearer the viewer): a
cell is seen when its parent passes sight and its terrain level (height / CLIFF_H, ramps fractional)
is not above the eye; it passes sight when its occluder top (terrain, or a tree's base level +
`tree_occluder_levels`) is not above the eye. Flyers and reveals ignore occluders. A felled tree
lowers its cell and re-stamps the sources that reach it. Attack reveal: an attacker the victim's
owner cannot see is revealed for 1 s in 1.5 m. Each tick walks `unit_list` from a cursor and
re-stamps changed sources within a third of `STAMP_BUDGET` (24k cells per 0.1 s), so a full sweep
takes `fog_update` (3 ticks) and the cost never lands on one tick (250 units marching: ≈3 ms per
tick, `test_fog`); at the end of a sweep the structure memory updates, the texture uploads and
`Events.fog_updated(local pid)` fires. Deterministic (unit_list order, no clocks).
Consumers: `Unit.find_target` never acquires what its player cannot see; UnitView hides itself
when `shows` is false; picking, box select, hover and health bars skip hidden views; Selection
drops fogged foreign units; `Vfx.allow` culls effects in the fog; `Construction.can_place` needs
explored ground; the terrain, water, trees and decor shaders read the texture
(`World.set_fog_texture`; black mask unexplored, 0.45 brightness fogged); the minimap draws a baked
map image under a fog layer, static neutral markers (Gold Seams, neutral buildings, camp pips) even
on the black mask, and only the dots the player may see.
Not yet: invisibility / detection, the cripple reveal (§14.4), ghosts of structures destroyed out
of sight (they vanish), fog-gated sounds.

## 9. Players & economy

`PlayerState` (`src/systems/player_state.gd`): `id, team, faction, color, is_ai, gold, lumber,
food_used, food_cap, upkeep_tier, tier, tech, upgrades (id -> level), heroes, hero_tokens,
recall_grants, defeated`; `PlayerState.COLORS` is the art-bible team palette and
`colour_for(faction, taken)` picks a faction's preferred free colour.
`Economy` (`src/systems/economy.gd`, stage `economy`): `can_afford / spend / refund(pid, cost,
factor)`, `add_income(pid, kind, amount, source, pos) -> credited` (gold from taxed sources is
floored by the upkeep factor: tiers from `data/factions.json → upkeep`, 0–50 food 100 %,
51–80 70 %, 81–100 40 %; lumber never taxed), `pay_fraction`, `upkeep_tier / upkeep_factor`
(tracked every tick, `Events.upkeep_changed`), gather hand-offs for the `gather` /
`return_resources` handlers, `find_dropoff`, `deposit`, `gold_left(mine)`.
`Construction` (stage `production`): `can_place(pid, def, pos) -> {ok, reason, rect, pos}`
(flat, free, in bounds, explored, hall–mine gap), build / repair / garrison hand-offs.
`Production`: per-building queues (`train`, `cancel` with refund, food reserved when an item
starts, spawn at the footprint edge toward the rally point). `Tech`: tier, research levels,
requirements, ability unlocks. Each file's header documents the full contract.

## 10. Combat, abilities, heroes

- `Combat` (`src/systems/combat.gd`) resolves damage:
  `final = base_roll × types[attack_type][armor_type] × armor_factor` where
  `armor_factor = 1 - (a*k)/(1+a*k)` for armor ≥ 0 (k = `armor_k` 0.06) and `2 - 0.94^(-a)`
  below zero (type multiplier first, then armor). `base_roll` is an integer in
  `[damage_min, damage_max]` drawn from `World.rng` (seeded) — the only randomness in combat, so a
  fight replays identically for a seed regardless of frame rate (tested with visuals on).
  Static helpers `type_multiplier`, `armor_factor`, `compute_damage`; `fire(attacker, target)`
  (melee hit or `launch`), `hit(src, target, base, type)`; owns `projectiles`.
- `data/factions.json → combat` (rules.md §20.3): `armor_k`, `attack_types` (original names:
  `blade, pierce, siege, arcane, heroic, raw, spell`), `armor_types` (`light, medium, heavy,
  fortified, hero, unarmored, adamant`), the full `types` table, clamps, `defaults`
  (`acquire`, `leash`, `damage_point`, `backswing`, `turn_rate`, `cast_point`,
  `cast_backswing`, `corpse_decay`, `remains_decay`, `structure_decay`, `help_radius`,
  `weapon_kind`, `alert_interval`) and `class_timings.<class>` (turn rate, damage point,
  backswing per unit class). Defs validates every unit's `armor_type` and attack `type`
  against these lists. Combat extensions (splash, artillery `min_range`, attack ground via
  `Combat.fire_at_point(attacker, point)`, damage/taken modifiers from `Unit.mod_totals`) are
  agent B's (`docs/m2-ownership.md`).
- Unit `attack` def: `{"type", "damage": [min, max], "cooldown" (s, measured from swing start),
  "range" (m, edge to edge), "damage_point" (s), "backswing" (s), "acquire" (m; 0 = never
  auto-acquire; raised to at least range + 1), "projectile": {"speed", "arc", "model"} (absent or
  empty = melee)}`; unit-level `leash` (m) and optional `decay` (s).
- Abilities are data entries (`data/abilities.json`, `data/SCHEMA.md` §4) with `type`
  (`target_unit`, `target_point`, `target_unit_or_point`, `instant`, `passive`, `aura`,
  `toggle`, `command`) and an `effect` id. `EffectRegistry.get_effect(id)` loads
  `src/systems/abilities/effects/<id>.gd` or `src/systems/items/effects/<id>.gd` (every id in
  data must resolve; tested); effects extend `AbilityEffect` and implement
  `cast(ctx: CastContext) -> bool` (`ctx.world, caster, id, source, rank, values,
  target_unit, target_pos, targets`,
  `ctx.value(key, fallback)`, `ctx.allows(unit)` for the ability's target filter).
  `AbilitySystem` runs casts (`CAST` orders hand over through `can_order_cast`, `cast_range`,
  `begin_cast`, `cast_tick`, `cancel_cast`; structures cast through the `cast` command),
  cooldowns (`Unit.cooldowns`), autocast and ground effects; `BuffSystem` owns `Unit.buffs`
  and pushes their modifiers as the `buffs` source. Per-rank numbers: `Defs.ability_rank(id,
  rank)`.
- Heroes (`HeroSystem`, `data/heroes.json`): XP table and level cap 10, 3 normal abilities with
  3 ranks (hero levels 1/3/5) + 1 ultimate at level 6, attributes (STR → hp/regen, AGI →
  armor/attack speed, INT → mana/regen; primary attr → damage) through `Defs.hero_stats`, the
  derived level-1 unit def, 6-slot inventory (`ItemSystem`), revive at altar or inn.
- Items (`ItemSystem`), shops (`ShopSystem`, per-player stock, `buy` / `sell` / `service`
  commands) and creeps (`CreepSystem.spawn_camps(map, only = [])`: camp templates from
  `creep_camps.json`, ring layout, guard positions, bounty) follow the same pattern; their
  headers document the API.
- `AiPlayer` (`src/systems/ai/ai_player.gd`): one per AI seat, throttled `think()`, tuning from
  `rules.ai.<difficulty>`, its own RNG; it issues only player commands.

## 11. Input, camera, UI

- Input actions (project.godot `[input]`, generated from `Settings.default_actions()` by
  `tools/gen_input_map.gd`; `Settings` re-adds any missing at runtime): `cam_left/right/up/down`
  (arrow keys), `cam_zoom_in/out` (wheel, PgUp / PgDn), `cam_drag` (middle mouse), `select`
  (LMB), `command` (RMB), `queue_modifier` (shift), `cancel` (Esc), `menu` (F10), `jump_alert`
  (space), `subgroup_next` (tab; with shift it cycles back), `select_hero_1..3` (F1–F3),
  `cycle_halls` (Backspace), `group_0..9` (digit keys; ctrl/shift read from event modifiers),
  `card_0..11` (command card grid Q W E R / A S D F / Z X C V, row-major).
- `RtsCamera` (`extends Camera3D`): looks at a ground `focus` point from `distance` along a fixed
  pitch (-56°; `main.gd` applies `RenderProfile`: FOV 55° vertical `KEEP_HEIGHT`, distance
  18.75–35.2 m, default 25.8 m, near 0.3 / far 120 m — research README §1), wheel zoom, arrow
  keys + screen-edge pan (speed scales with zoom; `Settings.edge_pan_*`; only after the mouse has
  moved inside a focused window) + middle-drag "grab the ground", clamped to the map; ground
  height followed smoothly. API: `setup(world, start)`, `jump_to(pos)` (instant),
  `zoom_notch(step)`, `screen_to_ground(px)`, `pitch_for(d)`, `pan_velocity`, `edge_dir`.
  Runs in `_process` with delta (process ALWAYS), physics interpolation off. Juice (CAM-01/03/
  05/06), exact for any frame time: the pan velocity approaches the input exponentially (crisp
  start `pan_accel_k`, firm stop `pan_stop_k`) and the focus integrates it in closed form
  (`pan_step`); edge pan waits `edge_dwell_ms`; a wheel notch lands 15 % on its own frame then
  eases (`zoom_k`); the pitch couples to the distance (exactly −56° at the default); pushing past
  an end stop kicks a small spring. `juice: CameraJuice` (also `CameraJuice.current`) adds the
  whitelisted trauma shake and directional kick through `h_offset` / `v_offset` and a roll, so
  picking through `project_ray_*` sees the shaken view. `_apply()` calls
  `Audio.follow_camera()` (the listener at the ground focus).
- `Selection` (`extends Control`, full-screen overlay, mouse filter ignore, draws the drag box):
  click / drag box (own mobile units preferred over own buildings over one foreign unit) /
  shift-add/remove / ctrl-click or double-click = all own units of that type on screen, control
  groups 0-9 (ctrl+N set, shift+N add, N select, double-tap N centres camera), max 12 per
  selection (`Settings.max_selection`). The selection is kept in subgroup priority order
  (`Selection.priority_before`, rules §18.3: heroes first in training order, then food cost
  descending, then def id) and the cap applies after sorting, so heroes are never dropped; the
  first subgroup starts active; tab / shift+tab cycle `active_subgroup_def()`. F1–F3
  (`select_hero(n)`, own heroes by unit id; double-tap centres) and Backspace (`cycle_halls()`,
  own `town_hall` structures, selects and centres). Picking is
  screen-space against interpolated unit positions (`pick_unit(screen_pos)`), no physics bodies.
  Emits `Events.selection_changed`.
  The press must land in the world (HUD panels stop it); once pressing, drag motion and the
  release are read in `_input`, before the GUI, so a box that ends over the HUD still completes.
- Pause: F10 (`menu`) is handled by the HUD, which keeps processing while the tree is paused
  (Main and World do not), so the same key unpauses; `Main._toggle_pause` pauses the tree, shows
  the `PauseMenu` (`src/ui/pause_menu.gd`, process ALWAYS: Resume (F10 / Esc), Restart, Quit to
  Main Menu, Quit to Desktop; placeholder for juice HUD-11) and cancels a pending targeting mode.
  No pause over the end banner. `CommandInput` is pausable: no orders are given while paused
  (`activate_card`/`command_ground` refuse).
- `CommandInput` (`Node`, placed after `Selection` so it sees input first): right-click smart
  command (ground → move, unit → smart target), shift-queue. Card (rules §18.4): slot 0 Move,
  1 Stop, 2 Hold, 3 Attack (attack-move on the ground, attack on an enemy), 4 Patrol, shown only
  when an own mobile unit is selected (`has_orderable()`). **Hotkey presets**
  (`Settings.active_hotkey_preset()`: `Settings.hotkey_preset`, else
  `rules.controls.hotkey_preset`): **Classic** (default) uses the mnemonic actions `cmd_move` M,
  `cmd_stop` S, `cmd_hold` H, `cmd_attack` A, `cmd_patrol` P ("A-click" attack-move); **Grid**
  uses `card_0..11` by position (Q W E R / A S D F / Z X C V). `CommandInput.hotkey_action(slot)`
  names the action of a slot under the active preset (the card's hotkey label reads it).
  Targeted commands enter targeting mode (cross cursor, left-click confirms, right-click/Esc
  cancels; attack-move confirmed on an enemy becomes an attack); shows a short order marker
  ring. `activate_card(slot, shift)` is shared by hotkeys and HUD buttons; `command_ground(pos,
  shift)` serves the minimap. Later: ability targeting and the build placement ghost
  (green/red footprint).
- **Juice runtime** (`src/fx/`, juice bible §4; visual only, never writes sim state, never reads
  `World.rng`; tests: `test_juice*.gd`). Rules: gameplay only in the 30 Hz tick, every juice
  curve a closed-form function of time (exact springs, `Juice.damp`, latched peaks, stateless
  hashes, ≤ 12 Hz patterns, no shader `TIME`), so the picture is the same at any refresh rate.
  - Clocks: `FxClock.fx_now` (game-scaled, frozen while the World is paused) and `ui_now`
    (unscaled, always runs), advanced once per frame by `Vfx` (process priority −100, process
    ALWAYS). `FxClock.tick_age` = `World.interpolation_fraction() × DT`; juice anchored to a sim
    event back-dates to `FxClock.tick_time()` (knockback, gait crossings, bank, bar ghost);
    latched effects (≤ 60 ms) start at their peak on the first frame instead. Shaders read the
    fx clock as the `fx_time` uniform (`RenderAtmos.update`).
  - `Vfx` (`World/Fx/Vfx`, static `Vfx.instance`): subscribes to `Events` (`unit_damaged`,
    `unit_died`, `command_issued`, `selection_changed`, `bounty_paid`, `income_received`) and
    `Audio.voice_started`; handlers only enqueue (≤ `queue_records` 512), `_process` drains at the
    top of the frame and routes to `CombatFx`, `CombatText`, `OrderMarkers`, body composers. It
    owns `particles: ParticlePool`, `marks: GroundMarks`, `popups: PopupText`, `orders`,
    `missiles: MissileFx`, the density governor (`tier`, `tier_mult()`), `allow(pos, importance)`
    (fog, 2 m frustum margin, distance from the camera focus), `trace(tag, id)` (`--feel-trace`)
    and `signal battle_started(pos)` (CMB-36 first-contact clash).
  - `ParticlePool`: pre-built one-shot emitters per kind (`data/fx_particles.json`),
    `GPUParticles3D` on Forward+, `CPUParticles3D` on Compatibility (or `--cpu-particles`), fixed
    60 fps simulation; a busy kind never pops an emitter younger than 50 % of its life (importance
    ≥ 3 evicts), ≤ `spawn_budget_per_frame` particles per frame for optional bursts.
    `burst(kind, pos, dir, count_mult, importance, tint)`.
  - `GroundMarks` (one MultiMesh, cap 192, `ground_mark.gdshader`): the decal substitute (no
    `Decal` node anywhere): ripples, dust rings, chevrons, crosshairs, patrol arrows, target
    blinks, dashed lines; `add(kind, pos, r0, r1, color, life, t_offset, param, follow,
    ui_clock)`, `add_frame(xf, shape, ...)` for one frame. Shapes are coded (solid own, notched
    hostile, dashed hover / creep).
  - `PopupText` (pooled 2D labels on a CanvasLayer, fixed px size) is the **only** world text
    (no `Label3D`); `CombatText` decides what to print: *Minimal* by default (crits, heals ≥ 10,
    the local player's bounty and income), never a number on every hit, never XP; merges by key
    within 250 ms.
  - `MaterialFlash.hit / death_beat / structure_hit` write `UnitView.flash(strength, tint,
    duration, hold)` once per event (the shader evaluates the latched curve); `UnitView.juice`
    (`BodyJuice`, mobile units) composes lean / push-off / stop plant / bank / nods / acks /
    knockback / tremble into one write of `rig.transform` per frame, remaps skinned strikes so
    the contact frame lands on the damage tick with a visual hit-stop (`Juice.strike_phase`),
    starts the whoosh so its peak lands on contact, drops step dust on stride plants, and calls
    `Vfx.body_landed` on death contact.
  - `CombatFx`: victim flash, mass-scaled knockback away from the origin, material × weapon
    bursts at the contact (frontal-arc material, e.g. the Pavisier's pavise is wood), blunt
    ground rings, the first-contact clash, layered sounds through `Audio.event`. `MissileFx`
    watches `World/Projectiles` (read only): release tells, one trail ribbon per missile, arrows
    and javelins that stick in units or the ground (ring of `stuck_cap`), siege impacts with the
    whitelisted camera trauma.
  - `OrderMarkers` (from `command_issued`, local player): move ripple + pin, attack-move
    chevrons, patrol arrows, attack-ground crosshair, target blink + rim pulse, the order ripple
    through the selection (`SelectionCircles.pulse`, `BodyJuice.nod`, 28 ms per rank), spam taps,
    ≤ 8 live markers, shift waypoint lines, rally flags. `CommandInput._marker` defers to it.
  - `SelectionCircles` (one MultiMesh, ground-mark shader): rings that pop in and paint in from
    the drag corner, deselect ghosts, order pulses, the speaker shimmer, and hover (SEL-02: the
    unit under the cursor gets a dashed ring, `UnitView.set_hovered`, its bar; `hovered`).
    `HealthBars` (one MultiMesh, billboard shader): exact value, the damage ghost (holds 400 ms,
    closed-form drain), a latched 70 ms border flash, hovered / selected bars always drawn.
  - Feel numbers: global ones in `FeelConstants.c()` (`data/feel/feel_default.tres`, `validate()`
    asserts the legal ranges), per-unit ones in the fx sheet (`FxDefs.sheet(u)`,
    `data/fx_units.json` + an optional def `fx` block). No literals in fx code.
- `HUD` (`src/ui/hud.tscn` + `hud.gd`, class `Hud`, its own `CanvasLayer` layer 2, process
  always): top bar (gold, lumber, food used/cap, upkeep label, day/night clock, menu button →
  `menu_requested`) bound to the local `PlayerState`; bottom console (206 px of the 900 px
  reference height): `Minimap` (`minimap.gd`; placeholder: unit dots, camera box, left-click
  jumps, right-click = smart command; with an order armed, left-click issues it at that point
  through `CommandInput.command_ground` (Shift queues and keeps it armed) and right-click
  cancels it, rules §18.1, `test_minimap_orders`), portrait panel (placeholder: type colour + initials;
  later a 3D SubViewport), selected-unit name + HP/mana/damage/range/cooldown/armor/speed text,
  multi-selection grid (coloured squares with initials + HP strip; click selects that unit,
  shift-click removes it) and `CommandCard` (`command_card.gd`, 4×3 buttons with label +
  hotkey, active targeting mode shown pressed). The bar and console have mouse filter STOP so
  HUD clicks never reach world selection/commands; buttons never take keyboard focus.
  `Hud.covers(screen_pos)` reports HUD areas. A notification line above the console shows the
  local player's `Events.notification` text for 4.5 s (under attack, the war-band marching;
  placeholder for juice NTF-*). The selected hero's title carries its level. Still to come: hero
  portraits (left edge), idle worker button, chat area, tooltips, real art (original, no WC3 UI
  art).
- Scenario UI (Main, battlefield only): an objective line under the top bar (goal + war-band
  countdown) and the `EndBanner` (`src/ui/end_banner.gd`: Victory / Defeat / Stalemate, battle
  time, losses per side, Play again / Main Menu; fades in 1.2 s after `ended`, blocks world
  input; placeholder for juice SEQ-02, which will also halt World stepping).

## 12. Audio

`Audio` autoload (`src/autoload/audio.gd`, the director of juice bible §4.6; process ALWAYS).
Buses `Master` → `Music`, `SFX` (→ `Combat`, `World`, `Sub` with a 140 Hz low-pass), `Voice`
(→ `Acks`), `UI`, `Ambience`. Sample **families** come from `assets/audio/sfx/manifest.json`
(id → files; a variant is picked by a stateless hash with no back-to-back repeat); voices from
`assets/audio/voice/manifest.json` (speaker → def_ids, category → files); legacy single files
`assets/audio/sfx/ui/<id>`, `assets/audio/sfx/<id>`, `assets/audio/voice/<def_id>/<category>`
(`.ogg/.wav/.mp3`) still resolve. **Every request no-ops silently when the asset is missing.**
`data/sfx_events.json`: `families` (measured onset / peak ms, bus, per-family cap, spacing) and
`events` (a game event → layers: family templates filled from ctx such as
`hit_{material}_{weight}`, conditions `kill` / `!armoured` / `mass>=2.5`, computed pitch with a
hashed jitter, onset alignment so the transient lands on the event frame, no-cut windows).
API: `event(id, pos, ctx) -> int` (layers started), `play_3d(id, pos, opts)` (priority,
volume_db, pitch, from, bus, no_cut_ms, cap, spacing_ms), `play_2d(id, opts)`, `play_ui(id)`,
`thump(db)`, `play_voice(unit, category)` (ready / what / yes / attack / annoyed: 2D on the
input frame, one ack at a time, What ≤ 1 per 400 ms, Yes / Attack ≤ 1 per 1000 ms, an order or
selection tick when debounced, annoyed after 5 clicks in 2.5 s), `order_tick(unit, category)`,
`signal voice_started(unit, category, length)` (length 0 when the line is missing),
`peak_s(family)`, `onset_s(family)`, `follow_camera(cam, focus, distance)` (listener; also the
cull centre: beyond `cull_distance_m` × distance / 28 nothing starts), `duck(key, bus, db)` /
`release(key)` (deepest duck per bus wins; Music ≤ 8 dB down; `duck(key, bus, db, attack_ms)`
ramps in linearly on `now()`). Pools: `one_shot_pool` 3D voices
(steal the lowest priority, oldest first, never inside a no-cut window), `ui_pool` 2D voices, a
`Deny` player. Voice accounting runs on `now()` (wall clock; tests set `clock_override`). The
selection "What" plays on `Events.selection_changed` when the local player picked new units or
re-clicked the same ones (never when a death prunes the selection); orders ask
`CommandInput.ack_category(cmd)` (Attack for attack, attack-move and a right-click on an enemy,
else Yes). **Variation:** every SFX start gets a hashed volume (±`vol_var_db`, 1.5 dB) and pitch
(±`pitch_var`, 3 %) offset (`variation(family, seq, pitch_given)`), no pitch offset when the
event computed the pitch or the family is `pitch_locked`; voice lines vary ±1 dB, pitch 1.0.
**Aliases** (`sfx_events.json` `aliases`): an unrecorded family plays a recorded stand-in
(`sw_chop` → `sw_slash`) until its own takes exist. **UI:** `ui_click()` (every `UiStyle.button`,
the HUD menu button, command-card presses) and `deny(kind)` (error: an untargetable A-click;
disabled: a command-card press that cannot act) in `ui_faction`'s material.
**Bus levels** (juice ui-camera-audio §5.1, `BUS_DEFAULT_DB`): Music −12, Ambience −16, UI −8,
Combat −5, World −9, Sub −6, Alerts +1 (→ Voice) dB; ducks are added on top and written every
frame only on a change, so a ramp's final value lands at any frame rate. **Filter arbiter**
(AUD-01): Music and Ambience carry an always-on low-pass resting at 20.5 kHz; `filter(key, bus,
hz, ramp_ms)` / `unfilter(key)`, the lowest request wins, ramped in log-frequency on `now()`.
**Pause** (`set_paused`, from `Main._toggle_pause`): Music −6 dB, Ambience −10 dB and a 1.2 kHz
low-pass over 300 ms; the 3D one-shot players are PAUSABLE so world sounds pause with the tree.
**Music** (MUS-01 P0, `MusicDirector`, `src/audio/music_director.gd`, a child of Audio driven by
`Audio._process` → `update()`): pieces from `assets/audio/music/manifest.json` (`kind`,
`faction`, `loop`, `xfade_to_score_s`), two decks with equal-power fades on `now()`, its own RNG.
`menu_entered()` (MainMenu) loops `menu` (0.75 s fade-in from silence, else a 1 s crossfade);
`match_loading()` (`Main.start_match`) fades everything out over 1.5 s; `match_started(faction,
player_id)` (Main, after the boot) sets `ui_faction` / `local_player`, lifts the end and pause
ducks, plays `opening_<faction>` on the Alerts bus at −4 dB and starts the rotation: the
faction's `ingame` tracks from a shuffle bag (all play before any repeats, never the same twice
in a row), the first 6 s after the match starts with a 2 s fade-in, then 20–40 s of silence
after each track ends (tracks never loop or switch for battle). `play_music(cue)` /
`stop_music(fade_s)` / `music_id` / `is_music_playing()` stay for scripts and tests. **End
(SEQ-02 audio):** `Events.match_ended` is only recorded in the tick; `_process` then fades the
music over 1.2 s, ducks SFX −10 dB and Ambience −6 dB over 1.2 s, plays `victory_` /
`defeat_<faction>` at 600 ms, and at the stinger's `xfade_to_score_s` the `score` bed enters
with a 2 s crossfade and loops until the player leaves (the menu crossfades it out).
`manifest_paths()` lists every take (`tests/unit/test_audio.gd` loads them all). Night pool,
night filter, hero motifs, rally stems and ambience beds: later.

## 13. Testing

- `tests/run_tests.gd` (`extends SceneTree`): discovers `tests/unit/test_*.gd`, runs every
  `test_*` method (coroutines allowed), prints PASS/FAIL, exits with non-zero code on failure.
  A test also fails if any engine/script error is logged while it runs (custom `Logger`).
  Suites extend `res://tests/test_case.gd` (asserts, `make_world()` headless world with manual
  ticking, `flat_map()`, `run_until_idle()`, `track(node)` auto-free).
  Run: `godot --headless --path . --import` once, then
  `godot --headless --path . -s tests/run_tests.gd [-- --filter=test_pathing]`.
  Note: autoload names (`Defs`, `Events`…) are not visible to a `-s` script at compile time, so
  runner/playtest scripts load everything with `load()` at runtime.
- Input tests push synthetic events with `get_tree().root.push_input(ev, true)` (local coords).
- `tests/playtest/*.gd`: scripted scenarios (spawn units, issue commands, advance N ticks, assert
  outcomes, optionally save screenshots to `tests/output/`, git-ignored). Screenshots need a
  display: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0
  1600x900x24" godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution
  1280x720 -s tests/playtest/screenshot_overview.gd` (lavapipe) or `--rendering-driver opengl3`.
- `tests/unit/test_perf.gd`: worst-case tick cost with 250 units (dense blob idle and
  attack-moving, a cross-map group order on the generated map, 2 × 125 armies clashing); every
  tick is timed and both the average and the worst tick are asserted (`assert_tick_cost`).
  Wall-clock asserts use `best_tick_samples`: each scenario runs 2–3 times (the sim is
  deterministic, so the work is identical), the fastest time per tick is kept and scaled by
  `machine_slowdown()` (a fixed GDScript workload against the reference machine), so host
  noise on shared VMs does not fail the build while a real spike still does.
- Test data: the runner calls `Defs.load_test_defs()` first, so engine-level suites may use the
  `dummy_*` defs of `data/test_defs.json`; gameplay suites use real slice ids.
  `test_data.gd` (no `Defs.errors`, slice counts, hero level-1 stats, footprints, rules merge,
  test-def isolation), `test_commands.gd` (every command route reaches its system or handler
  — spies replace systems — and smart right-click for every target kind), `test_systems.gd`
  (stage registration, hooks, effect registry coverage, AI install, Fog stub, Economy tax and
  refund, the stat pipeline, towers firing in place), `test_slice_map.gd` (map contract).
- `tests/unit/test_battlefield.gd`: Playtest 1 — set-up from `scenarios.json`, the war-band
  timer, guards defending and hunting, creeps fighting back, defeat, 3 sim-minutes in the real
  main scene (wave, combat resolves, Space to the alert, no script errors) then the victory
  banner, the main menu starting the match and the pause menu's Restart.
  `tests/playtest/pt1_sandbox.gd` saves `tests/output/pt1_{menu,opening,fight,pause,end}.png`
  through the real menu path.
- `tests/playtest/battle.gd`: 8 soldiers + 4 archers attack-move into 10 creeps on an open
  patch of the test map inside the real main scene (`main.scenario = "sandbox"`) (HUD visible); asserts a winner within 90 sim
  s and saves `tests/output/battle_1..3.png`. The same setup (`battle_setup.gd`) runs headless
  in `test_orders.gd`.
- Every system PR adds/updates tests. No test is skipped or disabled to get green.
