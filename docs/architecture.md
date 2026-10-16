# Vibecraft — Engine Architecture (contract)

Godot **4.7.2-stable**, GDScript, **Forward+** renderer (falls back to Compatibility on old GPUs).
This document is the contract every contributor (human or agent) codes against. If you need to
change an interface here, change this file in the same commit.

## 1. Golden rules

1. **Refresh-rate independent.** All gameplay runs in a fixed-step simulation. Nothing gameplay-related
   may depend on frame rate or `_process` delta. Visual-only effects (camera, UI tweens, particles,
   procedural bobbing) use `delta` in `_process`.
2. **Fixed tick:** `physics/common/physics_ticks_per_second = 30`. All simulation logic runs from
   `World._physics_process` → `Sim.tick(dt)` in a deterministic system order (see §4).
   `physics/common/physics_interpolation = true` so `Node3D` transforms written during the tick are
   smoothly interpolated on any monitor (60/144/240 Hz…). The camera and UI are not interpolated
   (they update in `_process`). When teleporting an entity call `reset_physics_interpolation()`.
3. **Data-driven.** Units, buildings, abilities, items, upgrades, factions live in `data/*.json`,
   loaded by the `Defs` autoload. Code never hardcodes a unit stat.
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
`world_to_tile`, `tile_to_world`, `in_bounds_cell`, etc.

## 3. Project layout

```
project.godot
src/
  autoload/     defs.gd (Defs), audio.gd (Audio), settings.gd (Settings), events.gd (Events)
  world/        world.gd (match root), grid.gd, map_data.gd, terrain_builder.gd, terrain.gdshader,
                pathing.gd, spatial_hash.gd, fog.gd, doodads.gd, day_night.gd
  entities/     unit.gd, order.gd, projectile.gd, unit_view.gd (visuals), resource_node logic in unit.gd
  systems/      combat.gd, abilities.gd (+ abilities/*.gd effects), heroes.gd, economy.gd (PlayerState),
                production.gd, creeps.gd, ai/ai_player.gd
  input/        rts_camera.gd, selection.gd, command_input.gd
  ui/           hud.tscn + hud.gd, command_card.gd, minimap.gd, tooltip.gd, theme/
  fx/           vfx.gd (pooled particles, floating text), selection_circle, health_bars
data/           factions.json, units.json, abilities.json, items.json, upgrades.json, maps/*.json
assets/         models/ textures/ icons/ audio/{sfx,voice,music,ambience}/ ui/
tools/          python asset tooling (bpy, image processing), asset manifest
tests/          headless test runner + scripted playtests (screenshots under Xvfb)
docs/           design, research, this file
```

## 4. Simulation core

`World` (`src/world/world.gd`, scene `src/world/world.tscn`) is the match root. It owns systems
as child nodes and runs them in this order every tick (`dt = 1/30`):

1. `orders`  — commands queued by input/AI this tick are applied (`Sim.apply_commands`)
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
`entities:Dictionary(id->Unit)`, `spatial:SpatialHash`, `pathing:Pathing`, `map:MapData`,
`fog:Fog`, and helpers `spawn_unit(def_id, player_id, pos)`, `query_radius(pos, r, filter)`,
`issue(command:Dictionary)`.

Commands are plain dictionaries so input, AI, tests and (later) replays/network share one path:
```
{ "type": "move"|"attack_move"|"attack"|"stop"|"hold"|"patrol"|"smart"|"gather"|"build"|
          "train"|"cancel"|"cast"|"rally"|"research"|"use_item"|"drop_item"|"learn",
  "player": int, "units": [ids], "pos": Vector3?, "target": id?, "def": String?,
  "ability": String?, "slot": int?, "queue": bool }
```

## 5. Entities

`Unit` (`src/entities/unit.gd`, `class_name Unit extends Node3D`) represents **every** game object
with an id: mobile units, heroes, workers, buildings, gold mines, critters. Trees are NOT entities
(they are cells in `Doodads`, see §7) to keep counts low.

Key fields: `id, def_id, def:Dictionary, player_id, team, hp, max_hp, mana, max_mana, armor,
armor_type, radius, speed, sight, flags (is_building, is_hero, is_worker, is_resource, is_flying),
orders:Array[Order], current:Order, attack:Dictionary, abilities:Array, buffs:Array,
carry_gold, carry_lumber, hero:Dictionary (level, xp, str, agi, int, skill_points, ability_ranks),
inventory:Array (6)`.

Signals via `Events` autoload: `unit_spawned(u)`, `unit_died(u, killer)`, `unit_damaged(u, amount, src)`,
`order_issued(u, order)`, `building_completed(u)`, `training_completed(building, unit)`,
`resources_changed(player_id)`, `hero_level_up(u)`, `research_completed(player_id, id)`,
`selection_changed(units)`, `notification(player_id, kind, text)`.

Visuals are a child `UnitView` (`src/entities/unit_view.gd`): loads `assets/models/<model>.glb` if
it exists, otherwise builds a placeholder (capsule/box with team-colour band); applies team colour
(shader param on materials whose name contains `TEAM` or via mask texture); drives animation:
standard clip names **`idle, walk, attack, death, work, cast, birth`**. If a clip is missing it falls
back to procedural motion (bob, lean, lunge, topple+sink). Selection circle and health bar are
rendered by `fx/` systems, not by `UnitView`.

## 6. Movement & pathing

- `Pathing` (`src/world/pathing.gd`) wraps `AStarGrid2D` over the 0.5 m cell grid
  (`DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES`, jumping (JPS) enabled). Blocked cells: cliffs edges,
  water, trees, building footprints. Separate clearance is approximated by inflating obstacles
  by one cell for units with radius > 0.5.
- `find_path(from:Vector3, to:Vector3) -> PackedVector3Array`: snaps unreachable goals to the
  nearest walkable cell, then string-pulls (line-of-sight smoothing on the grid).
- Path requests are budgeted per tick (e.g. max 24 A* queries/tick, others wait a tick).
- Local movement = path following + separation steering from neighbours (via `SpatialHash`),
  allies push idle allies aside (WC3-like), units never overlap buildings. Height `y` sampled
  from `MapData.height_at(x,z)`.
- Buildings call `pathing.set_footprint(cells, blocked)` on placement/death; trees on harvest.

## 7. Map, terrain, doodads

- `MapData` loads `data/maps/<name>.json`: size in tiles, per-tile `tex` index (0..7), per-vertex
  `cliff` level, `ramp` flags, `water`, start locations, gold mines, tree regions, creep camps,
  neutral buildings. Tests can build a `MapData` in code.
- `TerrainBuilder` generates chunked `ArrayMesh` (16×16 tiles per chunk): flat tiles at their
  cliff level height + vertical-ish cliff walls with noise jitter, ramps as slopes; splat weights
  baked into vertex colours/`CUSTOM0` or a splat texture; `terrain.gdshader` blends up to 8
  textures (texture array), cliff walls use a rock texture with triplanar mapping, samples the fog
  texture to darken unexplored/fogged areas.
- `Doodads` stores trees per pathing cell group (one tree = 2×2 cells), renders them via
  `MultiMeshInstance3D` per tree type, handles `harvest(tree, amount)` and removal.
- Water: simple animated plane shader at a fixed level.

## 8. Fog of war

`Fog` keeps per-player `PackedByteArray` grids (0 = unexplored, 1 = explored/fogged, 2 = visible)
at 1 m resolution. Recomputed ~10 Hz from unit sight radii (cliff level blocks sight to higher
levels, trees don't for the slice). Uploads the local player's grid into an `ImageTexture` (L8)
used by terrain/doodad shaders and the minimap. Enemy units outside visible cells are hidden;
enemy buildings once seen leave a "ghost" until re-scouted.

## 9. Players & economy

`PlayerState` (`src/systems/economy.gd`): `id, team, faction, color, is_ai, gold, lumber,
food_used, food_cap, upkeep_tier, tech (Dictionary of completed research/buildings), heroes`.
Upkeep tiers reduce gold per trip (thresholds from `data/factions.json`). Workers gather
gold from mines (fixed amount per trip, max concurrent miners) and lumber from trees, return to
nearest drop-off building.

## 10. Combat, abilities, heroes

- `Combat` resolves damage: `final = base_roll × type_table[attack_type][armor_type] × armor_factor`
  where `armor_factor = 1 - (a*k)/(1+a*k)` for positive armor (k = 0.06), and `2 - 0.94^(-a)`
  for negative. Tables in `data/factions.json → combat`. Attack has damage range, cooldown,
  range, backswing (damage point), projectile def (speed, arc, model) or melee.
- Abilities are data entries with `type` (`target_unit`, `target_point`, `instant`, `passive`,
  `aura`, `autocast`) and an `effect` script id; effect scripts live in `src/systems/abilities/`
  and implement `cast(world, caster, target, rank)`. Cooldowns, mana, range, ranks, hotkeys.
- Heroes: XP table and level cap 10, 3 normal abilities with 3 ranks + 1 ultimate at level 6,
  attributes (STR → hp/regen, AGI → armor/attack speed, INT → mana/regen; primary attr → damage),
  6-slot inventory, revive at altar for gold/time.

## 11. Input, camera, UI

- `RtsCamera`: perspective camera with WC3-like default pitch (~-56°), FOV 45-50 (tuned),
  distance zoom range, edge pan + arrow keys + middle-drag, smooth in `_process` with delta.
- `Selection`: click / drag box / shift-add / ctrl-click same type / double-click same type,
  control groups 0-9 (ctrl+N set, N select, double-tap N centres camera), max 12 per selection,
  subgroup tab cycling.
- `CommandInput`: right-click smart command, hotkeys from command card (grid layout QWER/ASDF/ZXCV),
  targeting mode for abilities (cursor change + left-click to confirm, right-click/Esc cancel),
  shift-queue, build placement ghost (green/red footprint).
- `HUD`: top bar (gold, lumber, food, upkeep label, day/night clock, menu), bottom console:
  minimap (left), portrait (3D SubViewport) + unit stats / multi-select grid (centre),
  command card 4×3 (right), hero portraits (left edge), idle worker button, notifications
  & chat area, tooltips. Original art (no WC3 UI art).

## 12. Audio

`Audio` autoload: pooled `AudioStreamPlayer` (UI, voice) and `AudioStreamPlayer3D` (world SFX),
buses `Master/Music/SFX/Voice/UI/Ambience`, per-sound polyphony caps, voice response cooldowns
(ready/what/yes/attack/annoyed — annoyed after N rapid clicks), music playlist per faction,
day/night ambience beds. Missing files are silently skipped.

## 13. Testing

- `tests/run_tests.gd` (`extends SceneTree`): discovers `tests/unit/test_*.gd`, runs every
  `test_*` method, prints PASS/FAIL, exits with non-zero code on failure.
  Run: `godot --headless --path . -s tests/run_tests.gd`
- `tests/playtest/*.gd`: scripted scenarios (spawn units, issue commands, advance N ticks, assert
  outcomes, optionally save screenshots). Screenshots require a display:
  `xvfb-run -a godot --path . --rendering-driver vulkan -s tests/playtest/<x>.gd` (lavapipe) or
  `--rendering-driver opengl3`.
- Every system PR adds/updates tests. No test is skipped or disabled to get green.
