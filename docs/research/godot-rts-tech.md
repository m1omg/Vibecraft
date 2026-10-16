# Technical approaches for a WC3-like 3D RTS in Godot 4.7

Scope: how to build the Vibecraft engine layer (simulation, pathing, terrain, fog, selection, camera, HUD, tests,
animation) in **Godot 4.7.2-stable** with GDScript, in a CPU-only Linux container. This document is the technical
companion to `docs/architecture.md`. Where it disagrees with the architecture, it says so and explains why
(see §0, "Changes proposed to architecture.md").

How this was researched:
- Sources are official Godot release pages and docs, plus GitHub repos, fetched directly.
- Every API name was checked against the **local engine**. `godot --doctool` dumped the 4.7.2 class reference (810
  classes), and every class, method, property and enum named here exists in 4.7.2.
- The numbers in §12 come from **benchmarks run in this container** (4 threads, llvmpipe software GPU, Godot 4.7.2).
- The shared web-search budget was already used up when this task started. No WebSearch call succeeded, so every
  source was fetched from a known URL. Items marked **(unverified)** come from memory or community lore and should be
  confirmed before anyone relies on them.

---

## 0. TL;DR: decisions and recommendations

| Area | Recommendation | Why (short) |
|---|---|---|
| Sim loop | Keep the 30 Hz `_physics_process` sim with `physics/common/physics_interpolation = true`. Camera and UI run in `_process`, and the camera node gets `PHYSICS_INTERPOLATION_MODE_OFF`. | Refresh-rate independent. Interpolation is built in. 30 Hz leaves 33 ms per tick. |
| Unit storage | Keep one `Unit` node per entity (≤ ~400 entities), with hot loops over **typed arrays / Packed*Arrays** and a spatial hash. Trees, projectiles-in-bulk and decor stay out of the node tree (MultiMesh). | In headless mode, writing 300 node transforms costs **0.1 ms/tick**. Separation steering for 300 units costs **0.83 ms/tick** in GDScript. Nodes are not the bottleneck; pathfinding is. |
| Pathfinding | A **grid** (`AStarGrid2D`, 0.5 m cells = WC3's 32 gu pathing cell) with **custom separation steering**. Do **not** use NavigationServer3D, navmesh, or RVO `NavigationAgent3D`. | Matches WC3's cell-based pathing and build grid. Building placement or tree felling becomes an O(cells) update instead of a 51–211 ms navmesh rebake. RVO "has no information from navigation meshes". |
| A* settings | Turn **`jumping_enabled` (JPS) off**, which reverses architecture §6. Add **connected-component labels** so unreachable goals are never searched. Run **one A* per group**. Set a **per-tick path budget** (about 6 ms). Use a coarse 2 m grid for long paths. | Measured on 384² cells with a long wall **plus scattered obstacles** (600 random 4×4 blocks): JPS averages **~100 ms/path versus ~17–18 ms** without it; with forest clumps + wall, JPS was **365 ms vs 23 ms** (fact-check re-run). On a clean map (wall only, no clutter) JPS is ~12× *faster* (1.4 vs 17 ms), so the slowdown is specific to detours through cluttered terrain, which is exactly what WC3-style maps with forests look like. A solid goal with `allow_partial_path` costs **45–70 ms**. |
| Terrain | Per-corner (WC3-style) data: cliff level, height, texture id, ramp and water flags. Build **chunked `ArrayMesh`** directly from Packed arrays (19 ms for a 96×96-tile map; `SurfaceTool` takes 45 ms). Use **corner-mask tile blending** in the shader, not soft splat blending. | The crisp, hand-painted tile transitions are part of WC3's look, and generic splatmaps look "Unity-asset-store". |
| Trees | `MultiMeshInstance3D` per tree type **per 16×16-tile chunk** with a set `custom_aabb`. Sway runs in the vertex shader, and per-instance custom data holds phase, chop-shake and variant. | A MultiMesh is culled as one object, so chunking is needed for culling. |
| Fog of war | A CPU grid (1 m) updated at **~4 Hz** (WC3 updates every 0.4 s) with incremental re-stamping. Upload it as an RG8 `ImageTexture` (0.004 ms). Terrain, doodad and minimap shaders sample it. Enemy units are hidden on the CPU. | Portable to every renderer. Stamping 300 units takes 4.3 ms in GDScript. `DrawableTexture2D` GPU blits cost 67 ms on Compatibility/llvmpipe. |
| Selection | **Screen-space picking** (`Camera3D.unproject_position`) with no physics bodies. Draw selection rings **inside the terrain shader** from a small data texture, or as flat ring quads. **Health bars as a 2D overlay** drawn in one `Control._draw()`. | `Decal` is "not supported" in Compatibility. WC3 bars are constant pixel size. |
| Camera | Rig = focus `Node3D` on the ground + child `Camera3D` at pitch **−56°**, distance **~26 m** (WC3 default 1650 gu ÷ 64), narrow zoom range, rotation locked. Edge pan + arrow keys + middle-drag, exponentially smoothed. | Matches WC3 defaults from `Blizzard.j`. |
| HUD | One `CanvasLayer` + `Theme`. Bottom console: minimap (CPU-baked image + fog shader), portrait (`SubViewport` with `own_world_3d`, low update rate), info panel, **4×3 `GridContainer` command card** with grid hotkeys (QWER/ASDF/ZXCV by `physical_keycode`), custom tooltips via `_make_custom_tooltip`. | Godot 4.6/4.7 added `pivot_offset_ratio`, `offset_transform_*` and RichTextLabel font-relative images, which suit animated buttons and cost icons in tooltips. |
| Tests | Keep the dependency-free `SceneTree` runner. Optionally add **GUT 9.7.1** (the GUT build for Godot 4.7) or **gdUnit4 v6.2.x** (supports 4.7). Drive UI playtests with `Input.parse_input_event`, which is verified to reach `Button`, `_input` and `_unhandled_input` in headless mode. Take screenshots under `xvfb-run` with **`--rendering-driver vulkan` (lavapipe), which is faster than opengl3 here**, plus `--fixed-fps 30`. | All verified in this container. |
| Animation | Primary: **offline auto-rig in Blender `bpy`** (Blender **5.2.2 LTS** is installed at `/opt/bpyenv/v313`) with bone-heat weights, an envelope fallback, procedural keyed clips per archetype, exported as GLB. Fallback: **runtime skinning in GDScript** (prototype verified: `ArrayMesh` + `ARRAY_BONES/ARRAY_WEIGHTS` + `Skeleton3D` + `Skin`). Always layered: procedural whole-body motion + vertex-shader sway. | No rigging service is available. Bone heat in bpy gives the best weights, and the runtime path covers stragglers. |

### Changes proposed to `docs/architecture.md`

1. §6: **set `jumping_enabled = false`** on `AStarGrid2D`. JPS was **~6× slower** (and ~16× slower with forest clumps)
   on detours through cluttered terrain (benchmark in §12). Note: on an uncluttered map JPS is much *faster*, so this is
   a trade-off tuned for tree-filled WC3-style maps; re-benchmark on real maps. The docs also say JPS "disables the
   consideration of weight scaling".
2. §6: add **connected-component region ids** to `Pathing`. Before calling A*, snap the goal to the nearest walkable cell
   **in the unit's component**. Never call `get_id_path(..., allow_partial_path=true)` on an unreachable or solid goal.
   The docs warn that when `allow_partial_path` is true and the goal is solid, the search "may take an unusually long
   time to finish"; it measured 70 ms here (46 ms in a fact-check re-run).
3. §6: add a **coarse 2 m tile-level A*** (96² cells, 0.75 ms per cross-map path) for long paths. Refine with the
   0.5 m grid only near the unit, or on the corridor. Plan **one path per group** plus formation offsets.
4. §11/§fx: selection circles **must not depend on `Decal`**, because the architecture names Compatibility as the
   fallback renderer.
5. §13: screenshot runs should use `--audio-driver Dummy --fixed-fps 30`. Run `godot --headless --path . --import`
   once on a fresh checkout before tests.

---

## 1. Godot 4.5 → 4.7: what matters for an RTS

Confirmed on the official release pages unless marked otherwise.

| Version | Feature | RTS relevance | Renderer note |
|---|---|---|---|
| 4.5 | **Stencil buffer** (`BaseMaterial3D.stencil_mode`: Disabled / Outline / X-ray / Custom; `stencil_flags` Read/Write/Write-on-depth-fail, `stencil_compare`, `stencil_reference`) | **X-ray silhouettes** of units behind buildings and trees (SC2-style, optional), and outline on hover. The presets need a `next_pass`; the docs recommend `GeometryInstance3D.material_overlay`. | Compatibility support unverified. |
| 4.5 | **Shader baker** (precompiles shaders at export, ~20× faster load on Metal/D3D12 in the TPS demo) | Shorter first-load and fewer hitches in shipped builds. Not relevant in the container. | Export-time |
| 4.5 | **SMAA 1x** (`rendering/anti_aliasing/quality/screen_space_aa`) | Cleaner unit edges than FXAA. | Forward+/Mobile only ("Not supported" on Compatibility) |
| 4.5 | **Async navigation region processing**, separate 2D nav server | Only relevant if NavigationServer is used, which we do not recommend. | — |
| 4.5 | **3D physics interpolation moved to SceneTree** (user API unchanged) | Our fixed-tick sim relies on it. | all |
| 4.5 | `BoneConstraint3D`, `AimModifier3D`, `CopyTransformModifier3D`, `ConvertTransformModifier3D` | Turret and head aiming at targets, and weapon attachment. | all |
| 4.5 | GDScript **abstract classes**, **variadic args** | Abstract `AbilityEffect` and `Order` bases. | — |
| 4.5 | `FoldableContainer`, recursive mouse/focus disable, AccessKit screen reader | Menus and tech-tree panels. Disable a whole command card subtree at once. | — |
| 4.6 | **Jolt is the default 3D physics** for new projects | Irrelevant to gameplay because we use no physics bodies. Keep physics only for optional terrain ray picking. | — |
| 4.6 | **New IK framework**: `IKModifier3D`, `TwoBoneIK3D`, `FABRIK3D`, `CCDIK3D`, `JacobianIK3D`, `SplineIK3D` (all present in 4.7.2) | Foot planting on slopes and ramps (optional polish), arms reaching to a gold mine. | all |
| 4.6 | SSR overhaul, glow before tonemapping, AgX params, octahedral reflection probes | Visual polish on Forward+. | Forward+ |
| 4.6 | **ObjectDB snapshots/diffing**, **Tracy/Perfetto/Instruments** profiling of GDScript | Finding leaks (dead units not freed) and profiling `Sim.tick`. | — |
| 4.6 | `Control.pivot_offset_ratio`, separate mouse/keyboard focus | HUD buttons scale around their centre, and clicks don't show focus rings. | — |
| 4.6 | Unique Node IDs, delta-encoded patch PCKs | Robust scene refactors. | — |
| 4.7 | **`DrawableTexture2D`** (`setup`, `blit_rect`, `blit_rect_multi` with material) | GPU-side texture drawing (fog, minimap, blight). **Measured:** 300 blits take 1.9 ms submit on Vulkan/lavapipe but **67.6 ms on opengl3**, so CPU fog is preferred. | both work |
| 4.7 | `Control.offset_transform_*` (visual translate/rotate/scale that survives containers) | "Press" animation and wiggle on command buttons inside a `GridContainer`. | — |
| 4.7 | **RichTextLabel font-relative images** | Gold, lumber and food icons inline in tooltips, scaling with font size. | — |
| 4.7 | `PopupMenu` search, `TextureRect` AtlasTexture tiling, `Tween.tween_await()` | UI and scripted sequences (intro cinematics, tutorial). | — |
| 4.7 | **`AreaLight3D`**, per-pass environment UBOs (faster), nearest-neighbour 3D scaling, HDR output (Linux Wayland too) | Nice to have. `AreaLight3D` could light glowing building windows (cost unknown on llvmpipe). The class docs say area lights are "more demanding on the GPU" than omni/spot and suggest reserving them for cinematics or high-end targets. | `AreaLight3D`: all renderers, but "limited support" on Mobile/Compatibility; on Compatibility it **cannot cast shadows** and light textures are unsupported |
| 4.7 | Keyboard/mouse **device IDs**, virtual joystick node, "ignore gamepad when unfocused" | Not needed. | — |
| 4.7 | MeshLibrary editor, Vertex Snap, Path3D collider snapping | Editor-only; we generate maps in code. | — |

Renderer comparison, from the official "Renderers" page:

- **Compatibility lacks:** Decals, SSR, volumetric fog, FXAA, SMAA, TAA, Compositor effects and the screen-space
  roughness limiter.
- **Compatibility has:** SSAO, glow and MSAA 3D.
- **Compatibility light limits:** 8 OmniLights and 8 SpotLights per mesh (the page says these "can be increased"),
  and 2 reflection probes per mesh. Mobile: 8 omni + 8 spot per mesh (256 per view), 8 reflection probes per mesh.
- **MultiMesh colors and custom data** are "packed into 16 bits in the Compatibility rendering method" (this is from
  the `MultiMesh` class reference, not the Renderers page).

**Design rule:** every gameplay-critical visual (selection, fog, rings, placement ghost) must work in Compatibility.
Forward+-only features (SMAA, Decal-based blight, SSR water, volumetric fog) can only be optional polish.

---

## 2. Simulation architecture

### 2.1 Fixed timestep, decoupled rendering

The pattern Godot already provides:

- `physics/common/physics_ticks_per_second = 30`. Default is 60 (verified in the 4.7.2 `ProjectSettings`). The
  physics-interpolation docs list low tick rates (10–30) as "Better CPU performance" but "Add some delay to input".
- `physics/common/physics_interpolation = true`, which is off by default.
- All gameplay runs in `World._physics_process(delta)` → `Sim.tick(1.0/30.0)`. Use the constant, not `delta`, so a tick
  is always exactly 1/30 s.
- `physics/common/max_physics_steps_per_frame = 8` (default) caps catch-up. Under heavy load (the container renders at
  ~2–3 FPS), the sim **slows down** instead of spiralling. That is acceptable in single-player. For tests, use
  `--fixed-fps 30`, so each rendered frame is exactly one tick (deterministic and non-real-time).
- **Interpolation:**
  - Every `Node3D` whose transform the sim writes is interpolated automatically, 1–2 ticks behind.
  - At 30 Hz the delay is 33–66 ms, which is acceptable for an RTS. WC3 itself has noticeable command latency
    (unverified).
- **Teleports:** after a blink, spawn, or unit leaving a building, set the transform and then call
  `Node.reset_physics_interpolation()`. For a moving start such as a projectile, also set the next tick's transform
  immediately, as the docs advise, to avoid "streaking".
- **Camera:** it moves in `_process` and must not be interpolated. Set
  `physics_interpolation_mode = PHYSICS_INTERPOLATION_MODE_OFF`.
- **2D overlays** (health bars, floating text) are computed in `_process` from
  `Node3D.get_global_transform_interpolated()`, so they line up with the interpolated mesh.
- **MultiMesh:** the sim updates `MultiMesh` data (projectile swarms, tree shake) with
  `MultiMesh.set_buffer_interpolated(curr, prev)` or `physics_interpolation_quality`, and resets with
  `reset_instance_physics_interpolation(i)`.
- **Animation:** set `AnimationMixer.callback_mode_process = ANIMATION_CALLBACK_MODE_PROCESS_IDLE`, so clips advance
  with render frames. Clip *choice* (walk/attack/death) is made in the sim, and playback speed is set from sim speed.
- **Testing tip from the docs:** temporarily set ticks to 10 to expose anything that isn't interpolated.

**Determinism.** Determinism is wanted for replays, desync-free lockstep later, and reproducible tests.

- Commands are plain dictionaries applied at the start of a tick (already in the architecture).
- Every random number comes from a sim-owned `RandomNumberGenerator` with an explicit `seed`.
- Iterate entities in **id order**, keeping `Dictionary` insertion order. Never iterate physics results or
  `get_nodes_in_group` for gameplay.
- Never use `_process` delta, `Time`, or `randf()` in sim code.
- Godot `float` is 64-bit in GDScript, but `Vector3` is 32-bit. Cross-machine float determinism is not guaranteed
  (unverified for lockstep). Same-machine replays are deterministic if the rules above hold.
- **Test:** run the same scenario twice and assert the per-100-tick state hashes are equal.

### 2.2 Data-oriented vs node-per-unit

- **Entity count target:** 2 players × (≤100 food ≈ 40–60 units + 15–25 buildings) + creeps + mines ≈ **150–300
  entities**. A *Unit node per entity* is fine at that scale:
  - Measured headless: 300 `Node3D` (+ `MeshInstance3D` child) position/rotation writes = **0.10 ms/tick**.
  - Real cost will be higher with rendering active, through RenderingServer sync (unverified magnitude).
- **The hot loops need data-oriented discipline:**
  - Typed GDScript (`var x: float`, `Array[Unit]`), `PackedVector2Array`/`PackedFloat32Array`/`PackedInt32Array` for
    neighbour lists, and per-system loops (`for u in units: u.sim_tick(dt)`) instead of 300 `_physics_process`
    callbacks.
  - **No per-tick allocations** in inner loops: an array literal like `for nb in [a, b, c, d]` allocates every
    iteration. One unoptimized flood fill was 3–4× slower because of this.
  - Spatial hash rebuilt or updated once per tick (2 m buckets).
  - **Target acquisition** (auto-acquire range ~ 6–9 m) **throttled to every 3–6 ticks per unit**, staggered by
    `id % N`.
  - **AI** thinks every 0.5 s (already in the architecture).
  - **Fog** at ~4 Hz, staggered.
- **Measured budget:** separation + seek for 300 units over a 2 m spatial hash = **0.83 ms/tick** in GDScript.
  Budget left at 30 Hz for everything else: about 25 ms before rendering. The real risk is **pathfinding spikes**
  (§3) and **rendering on llvmpipe** (§12), not unit logic.
- **When to move to C++/GDExtension:** only if profiling shows `Sim.tick` above ~10 ms with 300 units. The likely
  candidates are flow fields and fog line-of-sight. Godot 4.6's GDExtension JSON interface makes bindings easier,
  but this is not needed for the slice.

---

## 3. Pathfinding and movement

### 3.1 How WC3 does it (for reference)

- **Grid sizes:** terrain tile = **128 gu**, pathing cell = **32 gu** (4×4 pathing cells per tile). The pathing
  map is a separate grid with walk/fly/build flags. Our mapping is 1 m = 64 gu, so a tile is 2 m and a pathing cell
  is 0.5 m.
- **Collision size → occupied cells**, from Hive Workshop testing:

  | Collision size | Cells occupied |
  |---|---|
  | 0–15 | 1×1 |
  | 16–31 | 2×2 |
  | 32–47 | 3×3 |
  | 48+ | 4×4 (default cap, reportedly configurable) |

  Collision size acts like a radius. Attack range is measured between collision edges. Most units are about
  35–37 (forum claim).
- **Buildings** stamp hand-painted **pathing textures** on the 32 gu grid. Build placement uses the same grid.
- **Groups:** formation movement at the slowest unit's speed on open ground (§7.5 of `gameplay-mechanics.md`).
  Units shove idle allies aside and queue at chokepoints. This "units bump and re-path" texture is part of the
  feel, not a fluid crowd sim.
- **Terrain file:** `war3map.w3e` stores one record per terrain point. The cited spec says "Repeat for each tile in
  height*width"; reading these as tile *corners* (tilepoints, map size + 1) is community convention and is not stated
  on that page (unverified there). Each record has:
  - ground height (`short`);
  - water height plus a boundary flag (`0x4000`);
  - a 6-bit texture id (64 textures in format v12) plus flags;
  - ground and cliff variation;
  - **cliff texture + 4-bit layer height**.

  This is consistent with the corner-based model we copy in §4.

### 3.2 Options evaluated

| | A: NavigationServer3D + navmesh + `NavigationAgent3D` RVO | B: Grid A* (`AStarGrid2D`) + custom steering (**recommended**) | C: Flow fields (BFS/Dijkstra integration field) |
|---|---|---|---|
| Building placed / tree felled | Rebake: **51 ms (cell 0.5) to 211 ms (cell 0.25)** for the full 192×192 m map, measured synchronously. Async (`bake_from_source_geometry_data_async`) and chunking (`filter_baking_aabb`, `border_size`) help but add complexity. Parsing from the SceneTree must happen on the main thread. Parsing visual meshes stalls the GPU, so parse procedural arrays or collision shapes. | `fill_solid_region(rect, true)`: O(footprint), microseconds, no `update()` needed. | Invalidate the cached fields that cross the changed cells. |
| Unit sizes | One navmesh per `agent_radius`, so 2–3 bakes. | Inflated copies of the grid per size class, or a clearance map. | Per size class. |
| Path query cost | C++ polygon A*, fast (not benchmarked here). | Short (≤20 m): **0.02–0.1 ms**. Cross-map on 384²: **6 ms open, 18 ms with detours** (worst 33). On a 96² coarse grid: **0.75 ms**. | One field per goal: **3.7 ms (96²), 14.6 ms (192²), 61 ms (384²)** in GDScript. Then free for unlimited units. |
| Avoidance | RVO is "in its own space and has no information from navigation meshes or physics collision". It can push units into buildings unless obstacles are added. It needs `target_position`, and "clinical" head-on cases fail. Results arrive by `velocity_computed` callback from the server, which is hard to make deterministic. | Custom separation + ally-push + stuck/repath: deterministic, tunable to WC3 shoving. | Same as B. |
| Matches WC3 build grid | No (separate grid needed anyway) | **Yes, same grid** | Yes |
| Reference implementation | `godot-open-rts` (MIT) does exactly this: one `NavigationAgent3D` per unit (`Movement` trait, avoidance on), with per-unit overrides of `max_neighbors = 40` (Worker, Tank, Drone, Helicopter) and `time_horizon_agents = 3.0` (Worker, Tank only), and an async rebake when a structure's `MovementObstacle` changes. | — | — |

**Recommendation: B, plus selective C.**

1. **Grid:** `AStarGrid2D`, `region = Rect2i(0, 0, 384, 384)`, `cell_size = Vector2(0.5, 0.5)`,
   `diagonal_mode = DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES` (no corner cutting),
   `default_estimate_heuristic = default_compute_heuristic = HEURISTIC_OCTILE`, **`jumping_enabled = false`**.
   - `update()` takes 7.5 ms once at load and clears all solidity, so call it before stamping.
   - Use `fill_solid_region` / `set_point_solid` for stamps. Costs such as shallow water or blight can go in
     `set_point_weight_scale`, which only works with JPS off.
2. **Size classes:** small (≤0.5 m radius) uses the base grid. Medium and large use grids eroded by 1 or 2 cells.
   Memory is trivial (147k cells each). Keep them in sync on every stamp.
3. **Reachability:**
   - Maintain a **component id per cell** for each size class: a full flood fill at load, recomputed for the affected
     region (or fully, throttled) after building placement or death and tree removal.
   - On an order, if the goal cell is solid or in another component, **spiral-search** to the nearest walkable cell
     in the unit's component (WC3 behaviour: units walk to the closest reachable point).
   - Then call `get_id_path(from, to, false)`.
4. **Hierarchy:** for distances > ~30 m, run A* on a **coarse 96² grid** (a 2 m tile is solid if ≥50% of its cells
   are, plus a connectivity check), then refine the first ~20 m on the fine grid, and refine again as the unit
   advances. The worst case falls from ~33 ms to ~2 ms.
5. **Groups:**
   - One path for the group (from the centroid, or from the unit nearest the goal).
   - Each unit gets a **formation offset** (slot grid around the goal, rotated to the travel direction) and only a
     short local A* to join the shared path.
   - WC3 moves the group at the slowest unit's speed when in formation.
6. **Budget:** queue path requests and process them until **~6 ms/tick**; the rest wait for the next tick. A
   one-tick delay (33 ms) is invisible because the unit turns toward the goal immediately.
7. **String pulling:** after A*, drop intermediate cells while there is grid line-of-sight (Bresenham over the
   size-class grid), which yields WC3-like straight segments.
8. **Local steering, every tick:**
   - seek next waypoint (arrive radius 0.3 m);
   - **separation** from neighbours within `r_i + r_j + 0.1` (spatial hash);
   - **ally push:** a moving unit pushes idle allies with a "make way" nudge, and buildings and enemies never
     yield;
   - **stuck detection:** if progress < 0.1 m over 1 s, re-path with neighbouring units temporarily treated as
     blocked, up to 3 attempts, then give up (WC3 units also give up).
   - Speed capping and turn rate (WC3 units turn before moving; turn rate around 0.5–0.6 rad/tick, unverified)
     are a big part of the "weight" of WC3 units.
9. **Flow fields (optional):** for the AI "attack-wave" or attack-move of ≥16 units to one point, compute a field on
   the **coarse 96² grid** (3.7 ms) once and let every unit follow it. Cache by goal tile. Not needed for the slice.
10. **Flying units:** ignore the walk grid. Use straight lines + separation, with a separate flyer layer bounded by
    map edges.

---

## 4. Terrain: WC3-style cliffs, ramps, tile blending, trees, water

### 4.1 Data model (per corner, like `war3map.w3e`)

`(tiles_x+1) × (tiles_z+1)` corner arrays, as Packed*Arrays:

- `height: PackedFloat32Array`: small undulation, ±1 m.
- `cliff: PackedByteArray`: level 0–3; WC3 has 4 bits.
- `tex: PackedByteArray`: 0–7 texture id.
- `flags`: ramp, water, blight, unbuildable, boundary.

Each cliff level is **128 gu = 2.0 m** in WC3, which is a level height of 128 gu (gameplay-mechanics §8). The
architecture uses 1.75 m; either works, and 2.0 m matches the tile size, which makes cliffs read as cubes.

### 4.2 Mesh generation (GDScript, chunked)

- **Chunks:** 16×16 tiles (32×32 m), one `MeshInstance3D` per chunk, for culling and partial rebuilds (blight
  spread, terrain deformation). A 96×96-tile slice has 36 chunks.
- **Build path:** fill `PackedVector3Array`/`PackedVector2Array`/`PackedInt32Array` directly, then call
  `ArrayMesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)`.
  - **Measured:** a full 96×96-tile flat-shaded surface (36,864 vertices) in **19 ms**. The same through
    `SurfaceTool` + `generate_normals()` + `index()` took **45 ms**. Prefer arrays.
  - Compute smooth normals yourself from the height grid with central differences.
- **Flat tiles:** a tile whose 4 corners share a cliff level is a quad at `level*CLIFF_H + height`.
- **Cliffs:** for tiles with mixed levels, use a **marching-squares case** on (corner ≥ high level), 16 cases × level
  pairs:
  - Emit the top surface for the high corners and the bottom surface for the low corners.
  - Emit a **wall strip** along the iso-line.
  - Subdivide walls (3–4 rows), push vertices along the wall normal with 3D value noise (±0.25 m), and add a slight
    overhang lip at the top edge. WC3 cliffs are chunky, rounded, rocky blobs, not vertical planes.
  - WC3 itself uses pre-modelled cliff meshes per corner-height combination, chosen by a 4-letter key and with
    variations (unverified, from memory). Procedural marching squares + noise gets the same silhouette without
    authoring 50+ pieces. Krea can supply the rock *texture*.
- **Ramps:**
  - A ramp tile pair (2 tiles long, perpendicular to the cliff edge) interpolates linearly between the two levels.
  - Cells on a ramp are walkable.
  - Cliff edge cells (the wall's footprint, ≈ one 0.5 m cell on either side of the iso-line) are **unwalkable and
    unbuildable** in the pathing grid.
- **Data textures for shaders:**
  - `tex_ids`: R8, `(N+1)²`, `FILTER_NEAREST`.
  - `heightmap`: RF, used by water depth and ring projection.
  - `fog`: RG8 (§5).
  - All are uploaded via `Image.create_from_data` + `ImageTexture.create_from_image` and updated with
    `ImageTexture.update()`.

### 4.3 Texture blending: avoid the "generic splat" look

WC3's ground reads as **hand-painted tiles with crisp, organic borders**:

- Each texture has a set of transition pieces for the 16 corner combinations.
- Textures are layered in **tileset priority order**, with higher-priority textures drawn over lower ones.

This is from memory: the corner model is confirmed by the `.w3e` format, but the atlas layout is unverified.

Shader recipe, which works in all renderers:

1. In `fragment()`, find the tile (`floor(world.xz / TILE)`) and fetch the 4 corner texture ids from `tex_ids` with
   `texelFetch`.
2. For each of up to 8 layers in priority order (loop over the *distinct* ids among the 4 corners, max 4), build a
   4-bit corner mask (which corners equal this id).
3. Sample a **transition-mask atlas** (16 cells, 4×4, grayscale) at `mask_index` using the tile-local UV.
   - The atlas is generated once in GDScript or Python with noise-eroded edges.
   - Alternatively, Krea can generate "hand-painted grass edge" alpha shapes.
   - Threshold with `smoothstep(0.45, 0.55, m)` for crisp edges.
4. Composite: `col = mix(col, layer_albedo[id], mask)`.
   - Albedo comes from a `Texture2DArray` (`sampler2DArray`, one slice per ground type, world-space UV at ~1 repeat
     per 4 m).
   - Use 2–4 variants per type, picked by a hash of the tile coordinate. WC3 tiles have random variations.
5. **Cliff walls** (`abs(NORMAL.y) < 0.6`): triplanar rock texture with a darkened bottom.
6. **Macro variation:** a low-frequency noise tint (±8% value) to break tiling.
7. Multiply by fog (§5). Add selection rings (§6.2).

Option B, the conventional approach, is a splatmap (RGBA weights per corner, bilinear). It is softer and cheaper to
write, but it is the look the user asked us to avoid. Keep it only as a fallback.

### 4.4 Trees and doodads

- **Instancing:** one `MultiMeshInstance3D` per (tree type × chunk).
  - `transform_format = TRANSFORM_3D`.
  - Set `use_colors`/`use_custom_data` **before** `instance_count`; the docs say "only when instance_count is 0".
  - Set `custom_aabb` to the chunk bounds plus tree height. The docs warn that far-apart instances always render,
    and that runtime AABB computation is costly.
  - Per-instance `INSTANCE_CUSTOM` = (sway phase, chop-shake start time, variant index, team/blight tint).
- **Removal** (tree felled): swap the last instance into the removed slot and decrement `visible_instance_count`, or
  set a zero-scale transform. Then `pathing.set_footprint(cells, false)`. A WC3 tree blocks a 2×2 cell area (1 m²)
  in our architecture (WC3 value unverified).
- **Vertex shader:** sway by `VERTEX.y / height` (so the trunk base is static), wind gust noise, and a short damped
  shake when chopped. Sample fog so trees in unexplored areas are black (WC3 hides doodads under the black mask but
  shows them under grey fog).
- **Measured:** `set_instance_transform` ×300 = 0.033 ms. Writing the whole `buffer` (12 floats per instance for
  TRANSFORM_3D) = 0.10 ms for 300.

### 4.5 Water

- **Mesh:** a plane (or per-region mesh) at the water level, sitting on a terrain basin.
- **Depth:** precompute a water-depth texture on the CPU (`water_level - terrain_height`, clamped). This is portable,
  where depth-texture tricks differ per renderer.
- **Shader:**
  - colour ramp shallow teal → deep blue by depth;
  - **shore foam** where depth < 0.25 m (animated noise);
  - two scrolling normal maps;
  - alpha 0.75–0.9, fresnel highlight;
  - small vertex waves (amplitude 0.03 m).
- **Pathing:** deep water is unwalkable for ground units and walkable for flyers and naval units (later). Shallow
  water is walkable with an optional `weight_scale`. Note that weight scales are ignored if JPS is on.

---

## 5. Fog of war

### 5.1 Model (WC3 rules)

- **Three states:**
  - black mask: never explored;
  - fog: explored, showing last-seen buildings;
  - visible.
- **Update rate:** WC3 updates every **0.4 s** on a **128 gu (2 m)** grid. We use 1 m for smoother edges and update
  at **~4 Hz**.
- **Line of sight:**
  - Cliffs block sight upward: a unit sees cells whose cliff level is ≤ its own.
  - Trees block sight.
  - Flyers ignore occluders.
- **Attack reveal:** attacking reveals the attacker briefly.

### 5.2 CPU grid algorithm (GDScript)

- **Per player:**
  - `vis_count: PackedInt32Array` (number of sources seeing each cell);
  - `explored: PackedByteArray`;
  - a cached per-unit "last stamped cell + radius".
- **Precompute disc offset tables** per sight radius (integer metres, e.g. 8–16 m), plus **ray tables** for
  occlusion. Each disc cell records the cells on its Bresenham line from the centre.
- **Each fog update:**
  - For units that **changed cell or radius** (day/night changes radius), un-stamp the old disc (`vis_count -= 1`)
    and stamp the new one (`+= 1`, `explored = 1`).
  - Static buildings stamp once.
  - Cost scales with *moving* units, not all units.
  - **Measured full re-stamp: 300 units, r = 12 m, 192² grid = 4.3 ms** in GDScript without LOS. Incremental is far
    less.
- **Occlusion:**
  - A cell is visible if `cliff[cell] <= cliff[unit_cell]` and no ray cell before it is a tree or higher cliff.
  - Shadow-casting is the faster option if LOS cost hurts.
  - Doing LOS for every cell is ~5–10× the stamp cost (estimate). It is affordable at 4 Hz with per-update
    staggering (half the players' units per tick).
- **Upload:**
  - Pack the local player's view to RG8: R = visible (0/255), G = explored (0/255).
  - `Image.set_data(...)` then `ImageTexture.update(img)`: **measured 0.004 ms** for 192².
  - Same texture for terrain, doodads, water, minimap and health-bar culling.

### 5.3 Rendering the fog

- **Terrain, tree and water shaders** sample the fog texture with **linear filtering** at `world.xz / map_size`:
  - `f = mix(0.0, mix(0.42, 1.0, vis), explored)`.
  - Unexplored is pure black. Fog is ~40% brightness, slightly desaturated and blue-shifted (WC3 fog is a cool grey;
    art decision).
  - Soften edges with a 3×3 blur on the CPU, or by sampling 4 taps in the shader.
- **Temporal smoothing:** a 4 Hz update would pop. Keep the **previous and current** fog textures and lerp in the
  shader by `fog_t = clamp(time_since_update / 0.25, 0, 1)`, a uniform set each frame.
- **Units:** enemy and neutral `UnitView.visible = (vis_count[cell] > 0)` for the local player, evaluated on the CPU
  every fog update.
  - **Buildings** leave a **ghost** (frozen copy, greyed) when they become fogged, until re-scouted.
  - **Projectiles and effects** in fogged cells are hidden too. Hidden enemies also produce no sounds.
- **Avoid** a full-screen overlay quad with screen-space reconstruction, or a 2D `SubViewport` of circles (what
  `godot-open-rts` does: `FogViewport` + `DynamicCircle2D` per unit). The CPU grid is cheaper here, deterministic,
  and the same data drives gameplay (targeting, AI cheating rules).

### 5.4 Minimap

- **Base image:** bake once at map load on the CPU: per-pixel average colour of the tile's ground texture
  (precomputed per texture), cliff edges darkened, water blue, trees dark green dots. Use 256² or the map size.
  - Don't render a second orthographic `SubViewport` camera: on llvmpipe each extra 3D view costs about a full
    frame (~300 ms).
- **Dynamic layer:** every 0.25 s, redraw unit dots (player colours, 2×2 px; buildings 4×4) into an `Image`, or draw
  them in `Control._draw()` directly (cheaper: no texture upload).
- **Display:** a `TextureRect` with a shader that multiplies by the same fog texture (black mask / fog grey). WC3 also
  shows creep camps as coloured dots on the minimap (green/orange/red by difficulty).
- **Camera frustum:** in `_draw()`, cast the 4 screen corners with `Camera3D.project_ray_origin/project_ray_normal`,
  intersect them with `Plane(Vector3.UP, focus_height)` (`Plane.intersects_ray`), map to minimap space, and draw a
  white trapezoid.
- **Input:** left-click or drag moves the camera focus. Right-click issues a smart order at that world point.
  **Pings** are expanding circles drawn for 2 s.

---

## 6. Selection, rings, health bars

### 6.1 Picking without physics

- **Click:** for candidate entities from the spatial hash near the ground point under the cursor:
  - project `p = cam.unproject_position(u.position + Vector3(0, u.height*0.5, 0))`;
  - skip if `cam.is_position_behind(...)`;
  - pick the smallest `distance(p, mouse)` under `pick_px = max(12, radius_m * px_per_m * 1.2)`.
  - Tie-break: own units > allied > enemy > neutral; living > dead.
  - This needs no `CollisionObject3D` on units, keeping Jolt and physics out of the sim entirely.
- **Ground point under cursor:** `origin = cam.project_ray_origin(m)`, `dir = cam.project_ray_normal(m)`.
  1. Intersect with `Plane(Vector3.UP, 0)`.
  2. **Refine** against the heightfield: march along the ray in 1 m steps from the plane hit backwards to the highest
     cliff level, then do a 5-step bisection.
  - Cheap and exact enough. Optional alternative: a single `HeightMapShape3D` static body for physics raycasts.
- **Drag box:**
  - `Rect2(press_pos, current - press_pos).abs()`, drawn as a 1 px green rectangle in a HUD `Control._draw()`. WC3's
    box is a thin green line.
  - On release, select own **non-building** units whose projected centre is inside. If none, select own buildings;
    if none, nothing.
  - **Max 12** (WC3), ordered by type priority (heroes first, then by unit type), with subgroup cycling on Tab.
- **Modifiers:**
  - **Shift**: add/remove.
  - **Ctrl+click** or **double-click**: all own units of that type **on screen**.
  - Control groups: Ctrl+N assigns, N selects, double-tap N centres the camera.
- **Input routing:** world clicks in `_unhandled_input`, so GUI `Control`s with `mouse_filter = STOP` consume
  clicks first. Verified: an injected click on a `Button` triggered `pressed` and did not reach
  `_unhandled_input`.

### 6.2 Selection circles

`Decal` is unavailable on Compatibility, and on Mobile it is limited to 8 decals per mesh, so do not use it. Options:

1. **Terrain-shader rings (recommended).**
   - Keep an `Image` of up to 128 rings (RGBAF: x, z, radius, packed colour/style) uploaded as a texture each frame
     (selected + hovered + targeting preview).
   - The terrain fragment shader loops over rings in the current *tile bucket*. A uniform grid of ring indices, or a
     simple loop of ≤32 if the count is small.
   - Draw an anti-aliased annulus: `1 - smoothstep(w-aa, w+aa, abs(d - r))`.
   - It conforms perfectly to slopes and cliffs, needs no z-fighting fixes, and works on all renderers.
   - Colours (WC3 convention): **green = own, yellow = neutral/ally, red = enemy** (unverified exact tints).
   - Hover = thinner and dimmer. Buildings get large rings.
2. **Flat ring quads** (`MultiMeshInstance3D`, unshaded, alpha, `render_priority` +1, lifted 0.05 m). Simpler, but
   they clip into slopes.
3. **Stencil "Outline" preset** on the unit mesh for hover (4.5+), as an extra cue on Forward+.

**Order feedback:**

- A short **ground ping** at the move target: a green shrinking ring for move, red for attack. Use a MultiMesh pool
  of quads with a tiny animated shader.
- **Rally point flag**.
- **Building placement ghost:** a translucent model plus per-cell green/red quads, from the same `Pathing`
  build-flags. This is a pure grid query, which is a big win of the grid approach.

### 6.3 Health and mana bars

- **Recommended:** one `HealthBarLayer extends Control` in the HUD `CanvasLayer`. In `_draw()` (`queue_redraw()`
  every frame), for each visible unit that is **selected, hovered, or all if Alt is held** (WC3 binding), project the
  unit's head (`get_global_transform_interpolated().origin + Vector3(0, height + 0.3, 0)`).
  - Draw a black-bordered bar, **constant pixel size** (~40×4 px units, 70×5 heroes and buildings).
  - Fill colour by HP fraction (green > 66% > yellow > 33% > red), plus a blue mana bar for casters.
  - 300 `draw_rect` calls are trivial, crisp at any zoom, and avoid 3D z-sorting artefacts.
- **Alternative:** billboard quads in a `MultiMeshInstance3D` (one draw, custom data = hp, mana, team). They scale
  with distance, which is the SC2 look, not WC3.
- **Floating combat text:** gold "+N" over the mine on return, red crit numbers. Use `Label` pool or `_draw()` text
  with fade (0.8–1.0 s) and rise (40 px).

---

## 7. Camera

**WC3 defaults** (`Blizzard.j` camera constants, via `gameplay-mechanics.md`):

- distance **1650 gu** (= **25.8 m**);
- angle of attack **304°** (= **56° down**);
- FOV **70°**;
- far Z **5000 gu** (78 m).

**FOV conversion:** whether WC3's 70° is horizontal or vertical is unverified. If it is horizontal at 4:3, the
vertical FOV is `2·atan(tan(35°)·0.75)` = **55.4°**. Godot's `Camera3D.fov` is vertical with the default
`keep_aspect = KEEP_HEIGHT`. **Start at 50–55° vertical** and tune against reference screenshots.

**Rig:**

```
CameraRig (Node3D, at focus point on the ground, y = smoothed terrain height)
  └─ Camera3D (local position = (0, d·sin(56°), d·cos(56°)), rotation_degrees.x = -56,
               physics_interpolation_mode = PHYSICS_INTERPOLATION_MODE_OFF, far = 120)
```

- **Zoom:** wheel changes `target_distance` within **[18, 32] m**. WC3 limits zoom tightly, and the camera never goes
  top-down. Optionally pitch flattens slightly when zoomed in (−56° → −50°), a common modern touch; keep it subtle.
- **Smoothing:** `d = lerp(d, target_d, 1.0 - exp(-12.0 * delta))`. Same for focus position. Frame-rate independent
  by construction.
- **Pan:**
  - **Edge pan** when the mouse is within **~8 px** of the window edge (WC3-like; unverified exact value). Use
    `Input.mouse_mode = Input.MOUSE_MODE_CONFINED` in windowed mode so edge pan works.
  - **Arrow keys**, and **middle-mouse drag** (grab-the-ground: keep the world point under the cursor fixed).
  - Speed ∝ distance: `pan_speed = 1.1 * d` m/s (tune).
  - Clamp focus to playable bounds minus a margin.
- **Rotation:** locked by default. WC3 lets Insert/Delete rotate (see `gameplay-mechanics.md` §9). Implement it as a
  temporary yaw that eases back to 0 on release (unverified that WC3 snaps back). It is an accessibility nicety, not
  core.
- **Jumps:**
  - **Space** → last alert or event location.
  - **F1–F3** → select hero (double-tap centres).
  - **Backspace** → main hall (WC3 conventions; Backspace unverified).
- **Height follow:** sample `MapData.height_at` at 5 points around the focus, average, and low-pass (`k = 6`). This
  avoids bobbing over cliffs.
- **Audio listener:** an `AudioListener3D` at the focus point + 6 m (per `audio-direction.md`).

---

## 8. UI (HUD) architecture

```
HUD (CanvasLayer, layer=10)  theme = res://src/ui/theme/vibecraft_theme.tres
  Root (Control, full rect, mouse_filter=IGNORE)
    TopBar (HBoxContainer): gold / lumber / food (used/cap) / upkeep label / day-night clock / menu buttons
    HealthBarLayer (Control, IGNORE)                    ← §6.3
    SelectionBoxLayer (Control, IGNORE)                 ← drag rectangle
    HeroPortraits (VBoxContainer, left edge, F1–F3)
    Notifications (VBoxContainer of RichTextLabel, fade out)
    Console (bottom, ~24–28% of screen height; NinePatchRect frame art + MarginContainer)
      HBoxContainer
        Minimap (Control + TextureRect + shader)     ← §5.4
        PortraitPanel (SubViewportContainer → SubViewport(own_world_3d=true, 128×128,
                        render_target_update_mode=UPDATE_WHEN_VISIBLE) with the unit model idling)
        InfoPanel: single-unit stats (name, level/XP, attack/armor with tooltips, hp/mana text)
                   OR multi-select grid (GridContainer of 12 small icon buttons with mini hp bars)
        CommandCard (GridContainer, columns=4, 3 rows → 12 TextureButton slots, ~56–64 px)
    Tooltip (custom; see below)
```

- **Command card:**
  - Data-driven per selection: the abilities, train and build lists come from `Defs`, and the "active subgroup"
    decides which card shows.
  - Each slot shows: icon, hotkey letter (corner), cooldown sweep, autocast border, disabled/greyed state, and cost
    check (red text in the tooltip if unaffordable).
  - **Hotkeys:** offer **grid layout (QWER/ASDF/ZXCV)** by default, matched on `InputEventKey.physical_keycode` so
    AZERTY and QWERTZ work. Keep per-ability mnemonic keys as an option (WC3 classic).
  - Universal positions (WC3): Move, Stop, Hold, Attack, Patrol in the top row; build/train menus open a sub-card
    with a Cancel slot at bottom-right (Esc).
- **Cooldown sweep:** `TextureProgressBar` with `fill_mode = FILL_COUNTER_CLOCKWISE` over the icon, or a small
  `canvas_item` shader (angle test). Both work in Compatibility.
- **Tooltips:**
  - Override `_make_custom_tooltip(for_text)` on the slot to return a `PanelContainer` with a `RichTextLabel` (BBCode).
  - Inline cost icons use `[img]`. Godot 4.7 makes images font-relative, so icons scale with text.
  - Show: title + hotkey, cost (gold/lumber/food/mana), cooldown, description, requirements in red.
  - Set `gui/timers/tooltip_delay_sec` (default 0.5) to ≈ 0.2–0.3 s; RTS tooltips must be snappy.
- **Animation:** `pivot_offset_ratio = Vector2(0.5, 0.5)` (4.6) + `offset_transform_scale` (4.7) for the press
  "squash" without fighting the `GridContainer` layout. Use Tweens.
- **Theme:**
  - One `Theme` resource: `StyleBoxTexture` panels using generated ornate frame art (original motifs only; no WC3 UI
    art), fonts (an original serif or blackletter-ish title font plus a readable body font), and Button states.
  - Keep colours in Theme constants so faction skins swap the theme.
- **Portrait on llvmpipe:** a 3D `SubViewport` is expensive. Use 128×128 and `UPDATE_WHEN_VISIBLE`. In
  `Settings.low_spec`, fall back to a static 2D portrait icon or a manual update at ~8 Hz with
  `UPDATE_ONCE`.

---

## 9. Open-source references (Godot)

| Project | License | Godot | What to learn | Caveats |
|---|---|---|---|---|
| [lampe-games/godot-open-rts](https://github.com/lampe-games/godot-open-rts) | **MIT** (© 2023 Lampe Games) | 4.3 (`config/features` "4.3", Forward Plus); 4.0–4.2 on branches | `source/match/`: `TerrainNavigation.gd` (terrain geometry parsed once with `parse_source_geometry_data` and cached; each rebake re-parses the rest of the scene, merges the cached terrain, then calls `bake_from_source_geometry_data_async`; `filter_baking_aabb` fixes the bake height), `FogOfWar.gd` (2D `SubViewport` circles → screen overlay shaders `simple_fog_of_war`/`detailed_fog_of_war.gdshader`), `hud/Minimap.gd` (`MinimapViewport`), `RectangularSelection3D`, `DoubleClickUnitSelectionHandler`, `UnitGroupSelectionHandler`, units as traits (`Movement` = `NavigationAgent3D` with `avoidance_enabled = true` and trait default `max_neighbors = 1`; unit scenes override to `max_neighbors = 40`, and Worker/Tank also set `time_horizon_agents = 3.0`), actions (`Moving`, `CollectingResourcesSequentially`, `Constructing`), AI vs AI. About 1.1k stars. | It uses the navmesh/RVO approach we argue against for a WC3 feel. Its fog is renderer-heavy. It is a sci-fi tower-defence-like scale, but its code structure (traits, actions, handlers) is a good template, and MIT allows reuse with attribution. |
| [uheartbeast/godot-fow-tutorial](https://github.com/uheartbeast/godot-fow-tutorial) | MIT (© 2020 Heartbeast Studios) | Godot 3 era (2D) | Two-layer explored/visible idea (with the video tutorial listed in `video-references.md` F18). | 2D and old API; concept only. |
| Nanotech Gamedev "RTS from scratch in Godot 4.5+" video series (links in `docs/research/video-references.md` F1, F2, F6, F12, F14, F16, F19) | videos | 4.5+ | Screen-space box selection, shader HP bars, **RTS without physics or NavigationAgents**, **grid fog without physics**, minimap shader. These are close to our recommended approach. | Videos only; repo licences not checked (unverified). |

Licence hygiene: copying MIT code is fine with the licence notice kept (add `THIRD_PARTY_NOTICES.md`). Do not copy
`godot-open-rts` assets without checking per-asset credits (it credits Kenney's Space Kit, CC0, unverified).

---

## 10. Headless testing and automated playtests

### 10.1 Layers

1. **Logic/unit tests (no rendering):**
   `godot --headless --path . -s tests/run_tests.gd` (already in the architecture).
   - `--headless` = `--display-driver headless --audio-driver Dummy`.
   - Build `MapData` in code and call `Sim.tick` directly in a loop. Ticking manually makes this fast and
     independent of `--fixed-fps`.
   - Run `godot --headless --path . --import` once on a fresh clone, so `.glb`/`.png` are imported before
     `load()`.
2. **Framework options** (MIT, both support 4.7):
   - **GUT 9.7.1** for Godot 4.7.x (godot_4_7 branch). CLI:
     `godot --headless -s addons/gut/gut_cmdln.gd --path . -gdir=res://tests/unit -ginclude_subdirs -gprefix=test_ -glog=1 -gexit -gjunit_xml_file=res://tests/results.xml`
     (the GUT docs accept both `-gopt=value` and `-gopt value`; `=` is required only to pass an empty value. The
     docs' own example is `godot -d -s --path "$PWD" addons/gut/gut_cmdln.gd`; exit code 0 if all tests pass, 1 if
     any fail).
   - **gdUnit4 v6.2.x** supports 4.7/4.7.1, and master v7.0.0 targets 4.7+. It has a scene runner with input
     simulation and a CI command-line tool.
   - **Recommendation:** keep the in-house runner (zero dependency, already specced). Add GUT only if we want JUnit
     XML for CI.
3. **Scripted playtests (sim level):** spawn units, `world.issue({...})`, advance N ticks, assert outcomes. Examples:
   - a footman reaches a point within T s;
   - 5 workers mine X gold in 60 s;
   - an AI expands by 4:00;
   - **determinism hash** equality across two runs;
   - **perf budget**: average `Sim.tick` < 8 ms with 300 units (measure with `Time.get_ticks_usec()`).
4. **UI-level playtests (input injection):**
   - `Input.parse_input_event(ev)` with `InputEventMouseButton`/`InputEventMouseMotion` (set `position` and
     `global_position`) and `InputEventKey` (`keycode`/`physical_keycode`, `pressed`).
   - **Verified headless in 4.7.2:** the click reached a `Button` (`pressed` fired), and other events reached
     `_input` and `_unhandled_input`.
   - The docs say it "has no influence on the operating system". `Input.warp_mouse` moves the cursor on desktop
     only (unverified under Xvfb).
   - For edge-pan tests, call the camera's `_edge_pan(mouse_pos)` directly.
   - Space events across frames: `await get_tree().process_frame` between press, drag and release.
5. **Visual capture (needs a display):**
   - Command:
     `xvfb-run -a -s "-screen 0 1280x720x24" godot --path . --audio-driver Dummy --rendering-driver vulkan --rendering-method forward_plus --resolution 1280x720 --fixed-fps 30 -s tests/playtest/<x>.gd`
   - After `await RenderingServer.frame_post_draw`, call
     `get_viewport().get_texture().get_image().save_png("user://shots/<name>.png")`.
   - **Measured here:**

     | Driver / renderer | Frame time (300 instances, directional shadows, 720p) |
     |---|---|
     | Vulkan Forward+ (lavapipe) | **360 ms** |
     | Vulkan Mobile | **293 ms** |
     | OpenGL3 Compatibility | **496 ms** |

     So use Vulkan for captures, and run one Compatibility capture per CI run to check the fallback (no decals,
     SMAA or FXAA there).
   - **Video:** Movie Maker mode `--write-movie out/clip.png` (PNG sequence + WAV) or `.avi` (MJPEG), with
     `--fixed-fps 30 --quit-after N`.
     - Recording is non-real-time, so llvmpipe produces smooth clips; it just takes longer.
     - OGV recording works only in editor builds.
     - Encode with ffmpeg afterwards.
   - **Assertions on images:** coarse checks only (not all black, mean luminance range, team-colour pixels present
     in the expected screen region). Avoid pixel-exact golden images: software rasterisation and driver updates will
     make them flaky.

---

## 11. Animation for unrigged AI-generated meshes

The generators output static GLBs, and there is no rigging service. Options, with Godot API names:

### (a) Procedural rigid-body motion (whole mesh or a few separable parts)

- **Mechanism:** transform the model root (or `UnitView` child) per frame:
  - **walk:** vertical bob `|sin(phase)|·0.06 m` + roll ±3°, phase advanced by distance travelled / stride (so feet
    don't "skate" visually);
  - **idle:** breathe scale-Y 1±0.015 at 0.3 Hz;
  - **attack:** wind-up lean back 8° over the backswing, lunge forward 0.25 m + pitch 12° at the damage point,
    recover;
  - **cast:** rise 0.1 m + glow;
  - **death:** topple 90° about the side axis over 0.5 s, then sink 1.5 m over 3 s (WC3 corpses decay);
  - **birth/construction:** buildings rise from the ground with dust; units fade/scale in.
- **Juice on top:** hit flash via `material_overlay` (white, 0.08 s), recoil 0.05 m.
- **Cost and use:** near zero, works everywhere. Looks "toy-like" for humanoids, but is **ideal for buildings,
  siege, flyers, critters, and as the universal fallback**, which is already in the architecture §5.
- **Splitting meshes into parts** (by connected components or cutting planes) can give separate weapon, head or wheel
  parts. AI meshes are usually one fused shell, so this rarely works without remeshing.

### (b) Skeleton3D + skin weights (rigging)

- **Offline in Blender `bpy` (recommended primary).**
  - The container already has **Blender 5.2.2 LTS as a Python module** (`/opt/bpyenv/v313/bin/python`), and
    `tools/tests/make_test_rigs.py` already uses `bpy.ops.object.parent_set(type="ARMATURE_AUTO")` (bone-heat
    weights).
  - Pipeline per model:
    1. Normalize the transform (feet at 0, face +Z, height by class).
    2. Classify the archetype (biped / quadruped / flyer / serpent / blob) from bounds aspect ratios plus a tag in
       the asset manifest.
    3. Place a **template armature** scaled to the bounds (biped ≈ 15–20 bones: hips 0.50H, spine 0.62H, chest 0.74H,
       neck 0.86H, head 0.92H, shoulders ±0.17W at 0.80H, elbows, hands, thighs ±0.09W, knees 0.27H, feet).
       Refine joint positions by slicing the mesh at those heights and taking cross-section centroids.
    4. **Bone heat** (`ARMATURE_AUTO`).
    5. If it fails ("Bone Heat Weighting: failed to find a solution", common on non-manifold AI meshes; message text
       unverified), **voxel-remesh a proxy** (watertight), heat-weight the proxy, then use a **Data Transfer**
       modifier (nearest face interpolated) to copy weights back to the original mesh. The last resort is
       **envelope weights** (`ARMATURE_ENVELOPE`).
    6. Normalize to 4 influences.
    7. Author **procedural keyed clips** (`idle, walk, attack, death, work, cast, birth`) per archetype template with
       Python keyframes. The same clip library applies to every model of that archetype.
    8. Export GLB (one glTF animation per action; the existing `vc_bpy.py` convention).
  - **Prompting tip** to make rigging succeed: generate the concept image in **A-pose/T-pose, arms away from body,
    legs apart, no cape touching the legs**, then image → 3D. Fused limbs are the main failure cause.
- **Runtime in GDScript (fallback, prototype verified in 4.7.2).**
  - Take the mesh arrays (`mesh.surface_get_arrays(i)`).
  - Build a `Skeleton3D`: `add_bone(name)`, `set_bone_parent`, `set_bone_rest`, `reset_bone_poses()`.
  - Compute weights. Envelope = distance to each bone *segment* (capsule), falloff `w = max(0, 1 - d/r)^2`; keep the
    top 4 and normalize. Write `arrays[Mesh.ARRAY_BONES]` (`PackedInt32Array`, 4 per vertex) and
    `arrays[Mesh.ARRAY_WEIGHTS]` (`PackedFloat32Array`, 4 per vertex); 8 influences need
    `Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS`.
  - Rebuild with `ArrayMesh.add_surface_from_arrays`.
  - Set `MeshInstance3D.skeleton` (NodePath) and `MeshInstance3D.skin = skeleton.create_skin_from_rest_transforms()`.
  - Animate with an `Animation`: `add_track(Animation.TYPE_ROTATION_3D)`, `track_set_path(t, "Skeleton3D:spine")`,
    `rotation_track_insert_key(t, time, Quaternion)`. Put it in an `AnimationLibrary`, add it to an
    `AnimationPlayer` (`add_animation_library`), then `play`.
  - **Verified here:** a 3-bone spine on an unrigged cylinder bends correctly when rendered with Vulkan/lavapipe.
  - **Costs:**
    - Weight computation is O(verts × bones): for 5k verts × 18 bones ≈ 90k distance evaluations, ~50–100 ms in
      GDScript (estimate). Do it at import time and cache as a `.tres`/`.res` via `ResourceSaver.save`, not per
      spawn.
    - Envelope weights are worse than heat weights at armpits and crotch. Acceptable for chunky WC3-style
      silhouettes at RTS camera distance.
- **Procedural bone animation at runtime:** subclass **`SkeletonModifier3D`** and override `_process_modification()`
  (or `_process_modification_with_delta`) to add procedural layers on top of clips:
  - head look toward the target (`LookAtModifier3D` exists in 4.7.2);
  - spine twist toward the attack target;
  - foot planting on slopes with **`TwoBoneIK3D`** (4.6);
  - turret aim with **`AimModifier3D`** (4.5).
- **Animation speed:** scale walk playback by `current_speed / stride_speed`, as WC3 does with its walk animations.
  Use `AnimationTree` + `BlendSpace1D` only if needed; `AnimationPlayer.speed_scale` is enough.
- **Performance at 300 units:**
  - Keep bones ≤ 20.
  - Disable animation processing for off-screen units (`VisibleOnScreenNotifier3D` → `AnimationMixer.active = false`).
  - Keep `callback_mode_process = ANIMATION_CALLBACK_MODE_PROCESS_IDLE`.
  - Skinning cost on llvmpipe is unmeasured (unverified); benchmark 300 skinned 3k-tri units before committing to
    skinning everything. Fall back to (a) or (c) for crowds and critters.

### (c) Vertex-shader animation

- **Procedural deform in `vertex()`.** Sway by height for trees, banners, capes and tails:
  `VERTEX.x += sin(TIME*f + INSTANCE_CUSTOM.r*6.28 + VERTEX.y) * amp * smoothstep(y0, y1, VERTEX.y)`. Idle breathing
  works the same way.
  - Works with **MultiMesh** (per-instance phase via `INSTANCE_CUSTOM`) and every renderer.
  - Cheapest way to make the world feel alive (WC3 maps are full of idly animated doodads).
- **Segment ("rigid-part") shader skinning:**
  - Offline, cluster vertices into parts (e.g. by the bpy weights' dominant bone), and store part id + pivot in
    `CUSTOM0` (`Mesh.ARRAY_CUSTOM0` with `ARRAY_CUSTOM_RGBA_FLOAT`).
  - The shader rotates each part around its pivot by per-instance params.
  - Good for golems, constructs and mechanical units; enables MultiMesh crowds.
- **Vertex Animation Textures (VAT):** bake skinned clips (from (b)) into a texture (frames × vertices, RGBA16F
  positions), and play by sampling at `VERTEX_ID`/UV2-indexed texels.
  - Gives **animated units in a MultiMesh** with no skeleton CPU cost.
  - Best for many identical creeps and critters.
  - Pipeline complexity is high and textures grow with vertex count. Defer until profiling demands it.

**Recommended stack:** (b) offline bpy rig + procedural clips for all units and heroes → (b) runtime skin as fallback
→ (a) layered on everything (hit flash, recoil, death sink, building construction) → (c) sway for doodads, trees,
banners and critters. Keep the clip-name contract (`idle, walk, attack, death, work, cast, birth`) so `UnitView`
doesn't care where a clip came from.

---

## 12. Benchmarks measured in this container (Godot 4.7.2, 4 CPU threads, llvmpipe)

| Test | Result |
|---|---|
| `AStarGrid2D` 384×384 `update()` | 7.5 ms |
| Cross-map path, 384², open field + 600 random 4×4 blocks | 6.1 ms avg (worst 16.6); **JPS** 3.5 ms avg |
| Cross-map path, 384², long wall forcing a detour **plus the 600 random 4×4 blocks** | **18.0 ms avg (worst 32.7)**; **JPS 102 ms avg (worst 219)**. Fact-check re-run: 16.9 vs 99.9 ms (same setup); wall only, no clutter: 17.3 vs **1.4 ms (JPS faster)**; 25 forest clumps + wall: 23 vs **365 ms** |
| Cross-map path, 192² (1 m cells) with wall | 3.8 ms (JPS 13.2) |
| Cross-map path, 96² (2 m cells) with wall | **0.75 ms** (JPS 1.8) |
| Short paths ≤ 20 m, 384² | 0.02–0.11 ms |
| Unreachable (solid) goal, `allow_partial_path = true`, 384² | **70 ms** (fact-check re-run: 46 ms) |
| GDScript BFS integration field (flow field) | 3.7 ms (96²), 14.6 ms (192²), 61 ms (384²) |
| GDScript connected-components labelling (naive) | 9.6 ms (96²), 40 ms (192²), 211 ms (384²); can be optimized ~3× by removing per-iteration array allocation |
| Separation + seek steering, 300 units, spatial hash | **0.83 ms/tick** |
| Fog stamp, 300 units, r = 12 m, 192² grid (no LOS) | 4.3 ms |
| `Image.set_data` + `ImageTexture.update`, 192² L8 | 0.004 ms |
| Navmesh bake 192×192 m, 100 boxes, `cell_size` 0.25 / 0.5 | 211 ms / 51 ms (sync; parse warning about visual meshes) |
| Terrain mesh 96×96 tiles via Packed arrays / via SurfaceTool | 19 ms / 45 ms |
| 300 Node3D transform writes (headless) / MultiMesh 300 `set_instance_transform` / full `buffer` write | 0.10 / 0.033 / 0.10 ms per tick |
| `DrawableTexture2D` 300 `blit_rect` (CPU submit) | opengl3 **67.6 ms**, vulkan 1.9 ms |
| Render 1280×720, 300 MultiMesh capsules + shadowed sun + 1 decal | Compatibility/opengl3 496 ms, Forward+/vulkan 360 ms, Mobile/vulkan 293 ms per frame |
| Runtime skinning prototype (3 bones, envelope weights, keyed rotation) | Renders correctly (Vulkan) |
| `Input.parse_input_event` headless | Click reached `Button.pressed`; RMB and key reached `_input` + `_unhandled_input` |

**Implication:** live play in this container runs at 2–3 FPS. All interactive tuning (camera feel, animation timing)
must happen on a real GPU or through recorded `--write-movie` clips. Keep visual budgets modest for low-end
machines:

- 1 directional shadow (or blob shadows for units);
- ≤ 3k triangles per unit, ≤ 10k per building;
- ≤ 2 material passes per unit.

---

## 13. Open questions / unverified

- Whether WC3's 70° FOV is horizontal or vertical. Tune visually.
- WC3 edge-pan margin, turn rates, exact selection-circle tints, cliff piece system, tree pathing footprint, and the
  ground-tile transition atlas layout. All are from memory.
- Stencil preset support in the Compatibility renderer.
- Skinning cost for 300 skinned units on llvmpipe (benchmark before scaling up).
- Whether `Input.warp_mouse` works under Xvfb for edge-pan tests.
- Navigation and other changes in 4.6/4.7 not covered by the release pages (the 4.6 and 4.7 pages did not mention
  navigation).

---

## Fact-check log (2026-10-16)

An adversarial pass re-checked the load-bearing claims against the live pages, the local 4.7.2 engine and a fresh
shallow clone of `godot-open-rts`. WebSearch was unavailable (budget exhausted), so all checks used direct fetches.

- **Confirmed:** 4.5/4.6/4.7 feature rows (stencil presets, shader baker "20×" TPS demo on Metal/D3D12, SMAA, 3D
  interpolation moved to SceneTree, abstract/variadic GDScript, Jolt default, IK node names, `pivot_offset_ratio`,
  GDExtension JSON, `DrawableTexture2D`, `offset_transform_*`, font-relative RTL images, `Tween.tween_await`). Also
  confirmed: every listed class exists in 4.7.2; the Compatibility rows (no Decals/FXAA/SMAA/TAA/SSR/volumetric
  fog, SSAO and glow supported); Mobile at 8 decals per mesh; the `AStarGrid2D` doc quotes; the RVO avoidance quotes;
  Movie Maker OGV recording being editor-only; GUT 9.7.1 for 4.7.x on the `godot_4_7` branch; gdUnit4 v6.2.x and
  master v7.0.0 supporting 4.7/4.7.1; `Blizzard.j` camera constants 1650/304/70/5000; the w3e v12 bit layout; the
  Hive collision-size table; the Hive vision guide (0.4 s fog update on 128×128 gu cells); godot-open-rts being MIT
  © 2023 Lampe Games, Godot 4.3 with about 1.1k stars; godot-fow-tutorial being MIT © 2020 Heartbeast Studios
  (Godot 3 `config_version=4`); `--headless` = `--display-driver headless --audio-driver Dummy`; Blender
  5.2.2 LTS in bpy; Godot 4.7.2.stable.
- **Corrected:**
  - The JPS slowdown applies only when a detour passes through cluttered terrain. On clean maps, JPS is faster.
  - `AreaLight3D` is not Forward+-only.
  - Compatibility allows 8 omni + 8 spot lights per mesh, not "8 lights".
  - The MultiMesh 16-bit note comes from the class reference, not the Renderers page.
  - The godot-open-rts avoidance values are per-unit overrides, not the `Movement` trait defaults, and its rebake
    flow was described inaccurately.
  - The physics-tick quote was not verbatim.
  - The w3e "corner" reading is not stated on the cited spec page.
  - The GUT `=` advice was overstated.

---

## Sources

Godot official:
- [Godot 4.7 release page](https://godotengine.org/releases/4.7/)
- [Godot 4.6 release page](https://godotengine.org/releases/4.6/)
- [Godot 4.5 release page](https://godotengine.org/releases/4.5/)
- [Physics interpolation: introduction](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html)
- [Using physics interpolation](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/using_physics_interpolation.html)
- [Using NavigationAgents (avoidance caveats)](https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_using_navigationagents.html)
- [Using NavigationObstacles](https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_using_navigationobstacles.html)
- [Using navigation meshes (runtime baking)](https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_using_navigationmeshes.html)
- [AStarGrid2D class reference](https://docs.godotengine.org/en/stable/classes/class_astargrid2d.html)
- [MultiMesh class reference](https://docs.godotengine.org/en/stable/classes/class_multimesh.html)
- [Decal class reference (not supported in Compatibility)](https://docs.godotengine.org/en/stable/classes/class_decal.html)
- [AreaLight3D class reference (renderer limits, GPU cost)](https://docs.godotengine.org/en/latest/classes/class_arealight3d.html)
- [Overview of renderers (feature comparison)](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)
- [BaseMaterial3D class reference (stencil)](https://docs.godotengine.org/en/stable/classes/class_basematerial3d.html)
- [Input class reference (parse_input_event, warp_mouse)](https://docs.godotengine.org/en/stable/classes/class_input.html)
- [Creating movies (Movie Maker mode)](https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html)
- Local: Godot 4.7.2 `godot --doctool` class reference dump and `godot --help` (API names and CLI flags verified in-container)

Projects and tools:
- [lampe-games/godot-open-rts (MIT)](https://github.com/lampe-games/godot-open-rts); also shallow-cloned and read: `source/match/TerrainNavigation.gd`, `FogOfWar.gd`, `units/traits/Movement.tscn`
- [uheartbeast/godot-fow-tutorial (MIT)](https://github.com/uheartbeast/godot-fow-tutorial)
- [bitwes/Gut (version table: GUT 9.7.1 for Godot 4.7)](https://github.com/bitwes/Gut)
- [GUT command-line docs](https://gut.readthedocs.io/en/latest/Command-Line.html)
- [MikeSchulze/gdUnit4 (compatibility table)](https://github.com/MikeSchulze/gdUnit4)

WC3 technical references:
- [WC3MapSpecification (README)](https://github.com/ChiefOfGxBxL/WC3MapSpecification)
- [WC3MapSpecification: Terrain `war3map.w3e` v12](https://github.com/ChiefOfGxBxL/WC3MapSpecification/blob/master/Terrain/12.md)
- [Hive Workshop: pathing collision size values into real values](https://www.hiveworkshop.com/threads/pathing-collision-size-values-into-real-values.271205)
- [Hive Workshop: Vision guide (fog updates every 0.4 s, 128×128 cells, occluder height 230)](https://www.hiveworkshop.com/threads/vision-guide.290769/)
- [Blizzard.j via lep/jassdoc (camera defaults; cited by gameplay-mechanics.md)](https://raw.githubusercontent.com/lep/jassdoc/master/Blizzard.j)
- Sibling research in this repo: `docs/research/gameplay-mechanics.md` (WC3 grid, fog and camera numbers), `docs/research/video-references.md` (Godot RTS tutorial videos F1–F20), `docs/research/audio-direction.md` (listener placement)
