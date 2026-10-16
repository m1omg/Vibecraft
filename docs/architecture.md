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
   use `Unit.display_pos()` (= `prev_pos.lerp(pos, Engine.get_physics_interpolation_fraction())`).
   Determinism: sim code never uses wall-clock time, `randf()` without the world RNG, or
   unordered iteration (path budgets are counts, not milliseconds).
3. **Data-driven.** Units, buildings, abilities, items, upgrades, factions live in `data/*.json`,
   loaded by the `Defs` autoload. Code never hardcodes a unit stat. `Defs.unit(id)`,
   `ability(id)`, `item(id)`, `upgrade(id)`, `doodad(id)`, `faction(id)` return the def dictionary
   (empty + one warning when unknown); `Defs.combat`, `Defs.upkeep`, `Defs.errors`. Unit defs
   require `name, kind (unit|building|resource), hp, radius` (+ `speed` > 0 for units,
   `footprint [w, h]` in cells for structures); defaults are filled in (`UNIT_DEFAULTS`), and
   visual hints live in the def too (`shape`, `weapon`, `roof`, `height`, `scale`, `model`).
   Content is not decided yet: data uses neutral placeholder ids (`dummy_worker`, `dummy_hall`,
   `gold_mine`…).
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
| Building footprints | in pathing cells, e.g. hall 10×10, barracks 8×8, farm 4×4, tower 4×4 |

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
  main.tscn + main.gd   boots a skirmish on the generated test map (camera, selection, input)
  world/        world.gd + world.tscn (match root), grid.gd, map_data.gd, map_generator.gd,
                terrain_builder.gd, terrain.gdshader, water.gdshader, tree.gdshader,
                pathing.gd, spatial_hash.gd, fog.gd, doodads.gd, day_night.gd
  entities/     unit.gd, order.gd, projectile.gd, unit_view.gd (visuals) + unit_placeholder.gdshader,
                resource_node logic in unit.gd
  systems/      player_state.gd (PlayerState), combat.gd, abilities.gd (+ abilities/*.gd effects),
                heroes.gd, economy.gd, production.gd, creeps.gd, ai/ai_player.gd
  input/        rts_camera.gd, selection.gd, command_input.gd
  ui/           hud.tscn + hud.gd, command_card.gd, minimap.gd, tooltip.gd, theme/
  fx/           vfx.gd (floating combat text, hit flashes; later pooled particles),
                selection_circles.gd + ring.gdshader,
                health_bars.gd + health_bar.gdshader, proc_mesh.gd (placeholder mesh helpers)
data/           factions.json, units.json, abilities.json, items.json, upgrades.json, maps/*.json
assets/         models/ textures/ icons/ audio/{sfx,voice,music,ambience}/ ui/
tools/          python asset tooling (bpy, image processing), asset manifest,
                gen_input_map.gd (regenerates project.godot [input] from Settings.default_actions())
tests/          headless test runner (tests/unit), scripted playtests + screenshots (tests/playtest)
docs/           design, research, this file
```

## 4. Simulation core

`World` (`src/world/world.gd`, scene `src/world/world.tscn`) is the match root. It owns systems
as child nodes and runs them in this order every tick (`dt = 1/30`). A system is any node with
`sim_tick(world: World, dt: float)` registered with `world.register_system(stage, node)`
(stages are the names below); `World.step()` runs `orders`, `units` and `cleanup` itself.
Scene children: `Terrain` (TerrainBuilder), `Doodads`, `Units` (unit container), `DayNight`
(`Sun` light + environment), `Fx` (`SelectionCircles`, `HealthBars`), `Systems`.
`World.visuals = false` skips terrain/fx/views (headless tests); `World.auto_tick = false`
lets tests drive `step()` manually.

1. `orders`  — commands queued by input/AI since the last tick are applied (`World._apply_commands`)
2. `production` — training queues, construction progress, research
3. `units` — each `Unit.sim_tick(dt)`: order state machine, movement (pathing+steering), attacks
4. `projectiles`
5. `abilities` — buffs/debuffs/auras/DoTs tick
6. `economy` — income, upkeep
7. `creeps` — camp leash/sleep/respawn
8. `ai` — AI players think (throttled, e.g. every 0.5 s)
9. `fog` — visibility recompute (throttled to ~10 Hz)
10. `cleanup` — dead entity removal, events flushed

`World` exposes: `tick_count:int`, `time:float` (sim seconds), `players:Array[PlayerState]`,
`entities:Dictionary(id->Unit)`, `unit_list:Array[Unit]` (stable spawn order — iterate this),
`spatial:SpatialHash`, `pathing:Pathing`, `map:MapData`, `fog:Fog`, `local_player_id`, `rng`
(seeded), and helpers `setup(map, seed)`, `step()`, `add_player(id, team, faction, ai)`,
`player(id)`, `team_of`, `is_enemy`, `is_ally`, `player_color`,
`spawn_unit(def_id, player_id, pos, facing=0)` (structures snap to their footprint and block
pathing; mobile units snap to the nearest walkable cell), `get_unit(id)`, `units_of_player`,
`query_radius(pos, r, filter:Callable, out:Array)`, `issue(command:Dictionary)`,
`mark_dead(unit, killer)`, `raycast_ground(origin, dir)`, `resolve_smart(unit, target)`,
`combat:Combat` (child of `Systems`, registered for the `projectiles` stage),
`projectile_root` (`Projectiles` node), `gather_handler:Callable(worker, resource)` (economy
hook called when a GATHER order reaches its resource; unset = the order just completes) and
`corpse_count()`.
Death: `Unit.die()` marks the unit; `cleanup` takes it out of the sim (spatial hash, `entities`,
`unit_list`), frees its footprint, releases its food and emits `unit_died`. The node stays as a
corpse (UnitView plays topple + sink) for `Unit.decay_ticks()` (`combat.defaults.corpse_decay`
8 s, `structure_decay` 4 s, or a def `decay`), then `cleanup` frees it. Corpse removal is sim
time, so it is identical on every machine. `spawn_unit`/`cleanup` also keep
`PlayerState.food_used` (unit `cost.food`) and `food_cap` (`food_provided`) up to date.

Commands are plain dictionaries so input, AI, tests and (later) replays/network share one path:
```
{ "type": "move"|"attack_move"|"attack"|"stop"|"hold"|"patrol"|"smart"|"gather"|"build"|
          "train"|"cancel"|"cast"|"rally"|"research"|"use_item"|"drop_item"|"learn",
  "player": int, "units": [ids], "pos": Vector3?, "target": id?, "def": String?,
  "ability": String?, "slot": int?, "queue": bool }
```
Commands are applied at the start of the next tick. Only units owned by `player` obey. A
command whose `target` died before it applied falls back to its `pos`, or is dropped. Unit
order types today: `move, stop, hold, patrol, attack_move, attack, smart, gather, build, cast,
rally, follow` (`follow` added for right-clicking an ally). `smart` is resolved **per unit**
by `World.resolve_smart(u, target)`: structures that train units → `rally` (sets
`rally_pos`/`rally_id`, never becomes a running order); no target → `move`; resource →
`gather` for workers, `move` for others; enemy → `attack` (`follow` if the unit has no weapon);
ally → `follow`. `attack` without a target is an `attack_move`. `gather` walks to the resource
and calls `World.gather_handler` (stub until economy.gd); build/cast still just move to their
target. Building/hero commands (`train, cancel, research, use_item, drop_item, learn`) are
rejected with a warning until production/heroes exist.
Group moves keep a compact group's formation (offsets from the group centre when its spread is
< 8 m); otherwise everyone heads for the point and separation spreads them.

## 5. Entities

`Unit` (`src/entities/unit.gd`, `class_name Unit extends Node3D`) represents **every** game object
with an id: mobile units, heroes, workers, buildings, gold mines, critters. Trees are NOT entities
(they are cells in `Doodads`, see §7) to keep counts low.

Key fields: `id, def_id, def:Dictionary, player_id, team, hp, max_hp, mana, max_mana, armor,
armor_type, radius, speed, sight, flags (is_building, is_hero, is_worker, is_resource, is_flying),
orders:Array[Order], current:Order, attack:Dictionary, abilities:Array, buffs:Array,
carry_gold, carry_lumber, hero:Dictionary (level, xp, str, agi, int, skill_points, ability_ranks),
inventory:Array (6)`.
Sim state (written only in `sim_tick`): `pos:Vector3` (authoritative position; the Node3D
transform is a copy written once per tick), `prev_pos`, `facing` (yaw, forward = -Z rotated),
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
`def_id`, `ability`, `data`; `Order.make(type, pos, target)`, `Order.type_from_string(s)`.
Order behaviour: MOVE follows its path and completes on arrival (or when stalled next to a
crowded goal) and ignores enemies; STOP clears the queue (and cancels a wind-up); HOLD never
completes, cannot be pushed and attacks only enemies already in weapon range, never moving;
ATTACK chases its target until it dies (no leash); ATTACK_MOVE follows its path, engages
anything acquired on the way and re-paths to its goal after each fight; PATROL is an
attack-move that ping-pongs forever; FOLLOW keeps within 1.2 m of an ally; shift-queued orders
start when the current one completes.
Combat behaviour (all in `Unit.sim_tick`, integer tick timers):
- **Acquisition**: idle, attack-moving and patrolling units scan every `SCAN_TICKS` (5, staggered
  by id) for the closest valid enemy within `acquire_range` (structures get a 6 m penalty so
  units are preferred; ties by id). `acquire = 0` (workers) never auto-acquires or retaliates.
- **Retaliation**: an idle or attack-moving unit that is hit engages the attacker; creeps also
  wake idle camp mates within `help_radius` (6 m).
- **Chasing**: path requests at most every `REPATH_TICKS` (10) and only when the target drifted
  more than 1 m from the last goal; at a stale goal the unit steers straight at the target.
  Path queries remain subject to the per-tick budget.
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
`tree_felled(pos)`, `command_issued(command)` and `menu_requested` (F10). Signals are emitted
immediately; deaths are deferred to `cleanup`.

Visuals are a child `UnitView` (`src/entities/unit_view.gd`): loads `assets/models/<model>.glb` if
it exists, otherwise builds a placeholder from the def's `shape` hint (`humanoid` capsule + head +
team-colour band and shoulders with a `weapon` prop; `building` box + `roof` pyramid/gable +
team band and banner; `mine` rock mound with gold nuggets). Placeholder parts are merged into one
vertex-coloured mesh cached per (def, team colour), so each unit is one draw call. Applies team colour
(shader param on materials whose name contains `TEAM` or via mask texture); drives animation:
standard clip names **`idle, walk, attack, death, work, cast, birth`**. If a clip is missing it falls
back to procedural motion: walk bob/lean, attack lunge (melee) or draw (ranged) peaking at the
damage point, death topple (0.55 s) then sink during the last 2.5 s before removal (structures
sink and tilt). Placeholders use `unit_placeholder.gdshader` (sRGB vertex colours + per-instance
`flash` uniform for hit flashes, so all units still share one material). Selection circle and
health bar are rendered by `fx/` systems, not by `UnitView`.
`Projectile` (`src/entities/projectile.gd`, `Node3D` under `World/Projectiles`): simulated in
the `projectiles` stage; homes on its target's current `hit_point()` along a parabola whose peak
is `arc × flight distance`, carries the base damage rolled at launch, and on arrival `Combat`
applies it (a projectile whose target died lands harmlessly). Its transform is written once per
tick (physics interpolated); visuals are a placeholder arrow mesh.

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
  blocked or unreachable goal to the closest cell reachable from the start (ring search, 48 m),
  instead of letting A* exhaust the grid. Merges (tree cut, building removed) relabel
  immediately. A new obstacle only triggers a relabel when the walkable cells around it cannot
  reach each other inside a small window (buildings in the open never do); that relabel runs
  incrementally in `begin_tick()` (6k cells/tick ≈ 3–4 ms, ~3 s for the slice). Until it
  finishes, labels may claim two split areas are connected; queries stay correct, just slower.
- `find_path(from:Vector3, to:Vector3, large:=false) -> PackedVector3Array` (y = 0; callers
  sample height), then string-pulls over corner points with `line_of_walk(a, b)` (grid
  traversal of the centre line plus two lines offset by 0.3 m). Also: `is_walkable(cell)`,
  `is_walkable_world(pos)`, `nearest_walkable(cell)`, `closest_reachable(start, cell)`,
  `same_region(a, b)`, `set_tree(cell, present)`, `set_footprint(cells, blocked)`,
  `set_footprint_rect(rect, blocked)`, `is_rect_free(rect)`.
- Path requests are budgeted per tick by count (deterministic): `begin_tick()` resets,
  `has_budget()` (default 24 queries/tick); units that miss out retry next tick.
- `SpatialHash` (`src/world/spatial_hash.gd`): 4 m buckets over the map, units stored by `pos`
  with incremental `update(u)`; `query_radius(p, r, out)` / `query_rect(rect, out)` fill a
  caller-owned array (no per-query allocation).
- Local movement = path following + separation steering from neighbours (via `SpatialHash`),
  allies push idle allies aside (WC3-like; same player, idle, not holding), units never enter
  blocked cells (slide along them). Height `y` sampled from `MapData.height_at(x,z)`.
  Measured: 200 moving units ≈ 3–4 ms per tick headless (budget 33 ms).
- Buildings call `pathing.set_footprint(cells, blocked)` on placement/death; trees on harvest.

## 7. Map, terrain, doodads

- `MapData` loads `data/maps/<name>.json`: size in tiles, per-tile `tex` index (0..7), per-tile
  `cliff` level (deviation from "per-vertex": per-tile levels give clean vertical walls between
  tiles), `water`, an explicit `ramps` list (`rect` in tiles, ascending `dir`, `low` level; a ramp
  is 2 tiles long and rises exactly one level), start locations, gold mines, `trees`
  (`[x, z, type]` on the 1 m tree grid), creep camps, neutral buildings. Layers serialize as one
  digit string per row. `compute_heights()` derives 4 corner heights per tile (flat, ramp slope,
  or sunken lake bed); `height_at(x, z)` is the bilinear surface and matches the mesh exactly.
  Also `has_wall_x/z`, `compute_blocked_cells()`, `raycast(origin, dir)`, `to_dict/from_dict`,
  `load_json/save_json`. Tests can build a `MapData` in code.
- `MapGenerator.test_map(seed)` (`src/world/map_generator.gd`) builds the deterministic,
  point-symmetric 96×96 test slice: level-1 base, level-0 basin with a lake, two level-2 plateaus
  with a level-3 hill each, 10 ramps, forest border + noise clusters + a lumber line behind each
  base, 2 starts with gold mines, 4 creep camps.
- `TerrainBuilder` generates chunked `ArrayMesh` (16×16 tiles per chunk): tile tops (2×2
  subdivided) at their corner heights + vertical cliff walls with noise bulges (seams stay exact),
  ramps as slopes; splat weights for layers 0–3 in `COLOR` and 4–7 in `CUSTOM0` (averaged across
  tiles sharing a vertex at the same height), `UV2.x = 1` marks cliff walls. `terrain.gdshader`
  blends up to 8 layers with noise height-blending. Layers are procedural colour+noise
  placeholders until `use_layer_textures` is set with a `Texture2DArray` in `layer_albedo`
  (slices: 0 grass, 1 dark grass, 2 dirt, 3 rough dirt, 4 rock, 5 sand, 6 dry grass, 7 paved);
  walls use triplanar rock (`rock_albedo` + `use_rock_texture`, procedural strata otherwise).
  Fog hook: `fog_tex` (L8: 0 unexplored, 0.5 fogged, 1 visible), `fog_enabled`, `map_size_m`
  — shared by the tree and water shaders; `TerrainBuilder.set_fog_texture(tex)`.
- `Doodads` stores trees on a 1 m tree grid (one tree = 2×2 cells), lumber per tree from
  `data/doodads.json`, renders them via one `MultiMeshInstance3D` per tree type (placeholder
  cone/cylinder pine and sphere-canopy tree, wind sway in the shader), handles
  `harvest(tree, amount)`, `remove_tree`, `tree_at_cell`, `nearest_tree`; depleted trees free their
  cells and emit `tree_felled`.
- Water: simple animated plane shader at a fixed level.

## 8. Fog of war

`Fog` keeps per-player `PackedByteArray` grids (0 = unexplored, 1 = explored/fogged, 2 = visible)
at 1 m resolution. Recomputed ~10 Hz from unit sight radii (cliff level blocks sight to higher
levels, trees don't for the slice). Uploads the local player's grid into an `ImageTexture` (L8)
used by terrain/doodad shaders and the minimap. Enemy units outside visible cells are hidden;
enemy buildings once seen leave a "ghost" until re-scouted.

## 9. Players & economy

`PlayerState` (`src/systems/player_state.gd`; the economy system lives in `economy.gd`):
`id, team, faction, color, is_ai, gold, lumber,
food_used, food_cap, upkeep_tier, tech (Dictionary of completed research/buildings), heroes`.
Upkeep tiers reduce gold per trip (thresholds from `data/factions.json`). Workers gather
gold from mines (fixed amount per trip, max concurrent miners) and lumber from trees, return to
nearest drop-off building.

## 10. Combat, abilities, heroes

- `Combat` (`src/systems/combat.gd`) resolves damage:
  `final = base_roll × types[attack_type][armor_type] × armor_factor` where
  `armor_factor = 1 - (a*k)/(1+a*k)` for armor ≥ 0 (k = `armor_k` 0.06) and `2 - 0.94^(-a)`
  below zero (type multiplier first, then armor). `base_roll` is an integer in
  `[damage_min, damage_max]` drawn from `World.rng` (seeded) — the only randomness in combat, so a
  fight replays identically for a seed regardless of frame rate (tested with visuals on).
  Static helpers `type_multiplier`, `armor_factor`, `compute_damage`; `fire(attacker, target)`
  (melee hit or `launch`), `hit(src, target, base, type)`; owns `projectiles`.
- `data/factions.json → combat`: `armor_k`, `attack_types` (original names: `blade, pierce,
  siege, arcane, hero, chaos, spell`), `armor_types` (`light, medium, heavy, fortified, hero,
  unarmored`), the full `types` table, and `defaults` (`acquire`, `leash`, `damage_point`,
  `backswing`, `corpse_decay`, `structure_decay`, `help_radius`, `alert_interval`, `food_max`).
  Defs validates every unit's `armor_type` and attack `type` against these lists.
- Unit `attack` def: `{"type", "damage": [min, max], "cooldown" (s, measured from swing start),
  "range" (m, edge to edge), "damage_point" (s), "backswing" (s), "acquire" (m; 0 = never
  auto-acquire; raised to at least range + 1), "projectile": {"speed", "arc", "model"} (absent or
  empty = melee)}`; unit-level `leash` (m) and optional `decay` (s).
- Abilities are data entries with `type` (`target_unit`, `target_point`, `instant`, `passive`,
  `aura`, `autocast`) and an `effect` script id; effect scripts live in `src/systems/abilities/`
  and implement `cast(world, caster, target, rank)`. Cooldowns, mana, range, ranks, hotkeys.
- Heroes: XP table and level cap 10, 3 normal abilities with 3 ranks + 1 ultimate at level 6,
  attributes (STR → hp/regen, AGI → armor/attack speed, INT → mana/regen; primary attr → damage),
  6-slot inventory, revive at altar for gold/time.

## 11. Input, camera, UI

- Input actions (project.godot `[input]`, generated from `Settings.default_actions()` by
  `tools/gen_input_map.gd`; `Settings` re-adds any missing at runtime): `cam_left/right/up/down`
  (arrow keys), `cam_zoom_in/out` (wheel), `cam_drag` (middle mouse), `select` (LMB), `command`
  (RMB), `queue_modifier` (shift), `cancel` (Esc), `menu` (F10), `jump_alert` (space),
  `subgroup_next` (tab), `group_0..9` (digit keys; ctrl/shift read from event modifiers),
  `card_0..11` (command card grid Q W E R / A S D F / Z X C V, row-major).
- `RtsCamera` (`extends Camera3D`): looks at a ground `focus` point from `distance` along a fixed
  pitch (default -56°, FOV 45°, distance 14–46 m, default 28 m), wheel zoom (smoothed), arrow
  keys + screen-edge pan (speed scales with zoom; `Settings.edge_pan_*`; only after the mouse has
  moved inside a focused window) + middle-drag "grab the ground", clamped to the map; ground
  height followed smoothly. API: `setup(world, start)`, `jump_to(pos)`, `screen_to_ground(px)`.
  Runs in `_process` with delta, physics interpolation off.
- `Selection` (`extends Control`, full-screen overlay, mouse filter ignore, draws the drag box):
  click / drag box (own mobile units preferred over own buildings over one foreign unit) /
  shift-add/remove / ctrl-click or double-click = all own units of that type on screen, control
  groups 0-9 (ctrl+N set, shift+N add, N select, double-tap N centres camera), max 12 per
  selection (`Settings.max_selection`), tab cycles `active_subgroup_def()`. Picking is
  screen-space against interpolated unit positions (`pick_unit(screen_pos)`), no physics bodies.
  Emits `Events.selection_changed`.
  The press must land in the world (HUD panels stop it); once pressing, drag motion and the
  release are read in `_input`, before the GUI, so a box that ends over the HUD still completes.
- `CommandInput` (`Node`, placed after `Selection` so it sees input first): right-click smart
  command (ground → move, unit → smart target), shift-queue, default card hotkeys Q move,
  W stop, E hold, R attack-move, A patrol; targeted commands enter targeting mode (cross cursor,
  left-click confirms, right-click/Esc cancels; attack-move confirmed on an enemy becomes an
  attack); shows a short order marker ring. `activate_card(slot, shift)` is shared by hotkeys and
  HUD buttons; `command_ground(pos, shift)` serves the minimap. Later: ability targeting and the
  build placement ghost (green/red footprint).
- Fx: `SelectionCircles` (one MultiMesh of flat rings tilted to the terrain normal; green own,
  red enemy/hostile, yellow neutral/allied) and `HealthBars` (one MultiMesh of camera-facing bars,
  billboarding + fill in the shader, custom data = hp ratio / size), both rebuilt each render
  frame from `display_pos()` into a reused float buffer.
- `Vfx` (`src/fx/vfx.gd`, `World/Fx/Vfx`): listens to `unit_damaged`; pooled Label3D floating
  damage numbers (rise + fade, red for the local player's losses) and `UnitView.flash()`. Visual
  only, `_process` + delta, own jitter RNG (never `World.rng`).
- `HUD` (`src/ui/hud.tscn` + `hud.gd`, class `Hud`, its own `CanvasLayer` layer 2, process
  always): top bar (gold, lumber, food used/cap, upkeep label, day/night clock, menu button →
  `menu_requested`) bound to the local `PlayerState`; bottom console (206 px of the 900 px
  reference height): `Minimap` (`minimap.gd`; placeholder: unit dots, camera box, left-click
  jumps, right-click = smart command), portrait panel (placeholder: type colour + initials;
  later a 3D SubViewport), selected-unit name + HP/mana/damage/range/cooldown/armor/speed text,
  multi-selection grid (coloured squares with initials + HP strip; click selects that unit,
  shift-click removes it) and `CommandCard` (`command_card.gd`, 4×3 buttons with label +
  hotkey, active targeting mode shown pressed). The bar and console have mouse filter STOP so
  HUD clicks never reach world selection/commands; buttons never take keyboard focus.
  `Hud.covers(screen_pos)` reports HUD areas. Still to come: hero portraits (left edge), idle
  worker button, notifications & chat area, tooltips, real art (original, no WC3 UI art).

## 12. Audio

`Audio` autoload: pooled `AudioStreamPlayer` (UI, voice) and `AudioStreamPlayer3D` (world SFX),
buses `Master/Music/SFX/Voice/UI/Ambience`, per-sound polyphony caps, voice response cooldowns
(ready/what/yes/attack/annoyed — annoyed after N rapid clicks), music playlist per faction,
day/night ambience beds. Missing files are silently skipped. API: `play_ui(id)`,
`play_3d(id, pos)`, `play_voice(unit, category)`; files are looked up as
`assets/audio/sfx/ui/<id>`, `assets/audio/sfx/<id>`, `assets/audio/voice/<def_id>/<category>`
with `.ogg/.wav/.mp3`.

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
- `tests/playtest/battle.gd`: 8 soldiers + 4 archers attack-move into 10 creeps on an open
  patch of the test map inside the real main scene (HUD visible); asserts a winner within 90 sim
  s and saves `tests/output/battle_1..3.png`. The same setup (`battle_setup.gd`) runs headless
  in `test_orders.gd`.
- Every system PR adds/updates tests. No test is skipped or disabled to get green.
