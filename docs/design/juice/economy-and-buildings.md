# Juice Spec: Economy & Buildings

*Domain doc of the Vibecraft juice bible. Date: 2026-10-16. Status: design spec, **revision 2** (after two critiques; see the Critique log at the end).*
*Scope: the gold loop, the lumber loop, workers and cargo, the two slice worker mechanics (Levy Horn, Sound the Gong / Roll the Felt), HUD resource feedback, building placement, construction, in-place upgrades, production and research, building damage, destruction and repair, supply and upkeep, mine depletion.*

**Inputs:** `docs/research/visual-art-direction.md`, `audio-direction.md`, `video-references.md` (moments M6, M7, M8, M11, M14), `godot-rts-tech.md`, `docs/architecture.md`, `docs/design/rules.md` (§1, §4, §5, §8, §15.5, §18.6), `docs/design/slice-plan.md`, the faction docs `factions/kingdom.md` (§2.5, §3.3, §4, §7) and `factions/clans.md` (§2.4, §2.5, §3.4, §4, §7).

**Sibling docs own, and this doc reuses:** combat FND-1 (closed-form springs, the body composer), FND-2 (FxSprites), FND-3 (density tiers, importance), FND-4 (event queue, `fx` def block) and CMB-28 (bounty text and coin flight); heroes HVF-2 (`terrain_height`, GroundZones); world WLD-F4 (lantern map, LightBudget), WLD-28/29 (smoke wind, cloth), WLD-31 (world memory ledger); UI/audio UCA-F3, AUD-02 (mixer, pools, priorities), MUS-01 (music director), NTF-02/03/05 (pings, feed, idle-worker button). Where this doc touches their systems it names the hook and leaves the system to them.

**Conventions**
- Durations are ms at 1× game speed. Distances are metres. Easings are Godot names (`TRANS_BACK/EASE_OUT` is written BACK/OUT) or the combat doc's `Juice` Penner names.
- Colours are sRGB hex. "HDR x" is an emission multiplier; only values above 1.0 bloom, and only VFX may exceed 1.0.
- "Own" means the local player, or the observed player in observer mode.
- **Factions use their ids.** The slice is `kingdom` (Brennmark) vs `clans` (the Tormai). Construction verbs come from rules §4.7: kingdom *scaffold-raised*, clans *raised felt* ("Raising", clans §2.4). `sylvan` (*woven*) and `deathless` (*unearthed*) are later and live in the §4.2 appendix.
- Readability numbers use the combat doc's default view: 28 m camera distance, FOV 45°, pitch −56°. At 1080p that is ≈ 46 px per metre sideways, ≈ 39 along the ground, ≈ 26 straight up.

---

## 1. Feel goals

A base should feel like a **busy workshop you can read at a glance and by ear**:
- Every worker trip ends in a small, crisp payoff that you hear more than see.
- Every building is a short ceremony: surveyed, staked, laid course by course, topped out, and flagged.
- **Every hammer strike visibly lays something.** Cause and effect are never separated.
- Damage writes itself onto the walls in the building's own material: plaster drops out of a Brennish frame; Tormai felt tears.
- The economy has a **rhythm in the key of the music**: chops, mallet taps and deposit notes lock to the track's tempo and scale. An experienced player can tell how healthy the base is without looking at it.

Most of this layer is **information in costume**. Each flourish answers a question: Is that worker carrying anything? Is this mine saturated? How far along is that barracks, and when will it finish? Is my forge idle? How much is upkeep costing me? Am I floating gold?

The art is chunky and hand-painted. Coins are fat discs, chips tumble, smoke is painted cut-out cotton (never photographic fog), fire is stylised flame tongues, and only VFX bloom.

**Seven rules for this domain:**
1. **Ceremony scales with rarity.** Deposits (about one per second per mine) get under 1 s of micro-juice, popup included, and habituate. A building completes about once a minute: a 1 s ceremony. A hall tiers up once or twice a game: a 1.8 s ceremony. A hall falls about once a game: a 3 s set piece. Repeats get shorter, never longer.
2. **Never wait for the juice.** The sim never pauses, delays or re-times anything. Flourishes run alongside gameplay and can be cut off at any frame. Anticipation is built from **predictions** of sim events and degrades gracefully when a prediction misses.
3. **Readable in a fight.** Economy effects shrink first when combat is busy (§2.8). Nothing covers units, team colour, selection rings or health bars for more than 80 ms.
4. **Every material has its own motion and sound** (§2.5). Timber flexes locally, stone sheds dust and never squashes, felt breathes, shell plates rattle, coins wobble to rest. No "jelly stone", no generic sparkle.
5. **Strikes do the work.** Construction progress is revealed **by** builder strikes (BLD-06), completion is **anticipated** (BLD-24), and a building falls the way it was built, in reverse (BLD-16).
6. **Respect the music.** Every pitched or rhythmic economy sound takes its tempo and scale from the `MusicClock` (§2.7).
7. **Fog-honest.** An effect plays only if the local player could see or hear its source, including looped effects that outlive the moment of sight (§2.1).

---

## 2. Shared foundations (read before implementing any row)

### 2.1 Hard rules

**Visual-only and refresh-rate independent**
- All juice lives in `_process(delta)` or in shaders. Nothing in juice writes `Unit` sim fields, `PlayerState`, `Pathing` or `World.rng`, or emits gameplay events.
- Motion is a **closed-form function of the effect's age**, built from `JuiceCurves` (§2.4), or the combat doc's closed-form springs (FND-1 `Juice.spring`, `Juice.spring_track`). **No Euler integration anywhere.** 30, 60, 144 and 240 Hz show identical poses at the same game time.
- **No periodic visual motion above 12 Hz** (Nyquist at 30 fps is 15 Hz). Shudders chirp **down** from ≤ 12 Hz. `JuiceCurves` declares the frequency of every periodic function, and a test enforces the cap (§9).
- **No frame-counted durations.** The shortest timed element is 50 ms. Curves whose peak lasts ≤ 60 ms start **at** the peak (combat "latched peaks"), so the first rendered frame always shows it.
- **Periodic spawns** (smoke, sawdust, embers) use a time accumulator with back-dated `t0`, never "one per frame".

**Clocks** (owned by combat §2.1, restated)
- `fx_time` = `Vfx.now`: real delta × game speed, frozen while paused, reset at match start. World juice uses it.
- `ui_time` = `Vfx.ui_now`: real, unscaled. Input feedback (the placement ghost, HUD counters, the pitched-audio scheduler) uses it.
- Both are **declared in `project.godot [shader_globals]`** (`fx_time={"type":"float","value":0.0}`, same for `ui_time`, the world doc's `atm_*` and HVF-2's `terrain_height`). `Vfx` only calls `global_shader_parameter_set`. A material that references an undeclared global logs an engine error before registration, which fails `tests/run_tests`.
- `TIME` is banned in juice shaders.

**Timestamps and precision**
- Timestamps live only in full-float slots: the instance transform, or an instance uniform. `INSTANCE_CUSTOM` and `COLOR` are half floats on Compatibility (verified on 4.7.2: 1000.25 reads back as 1000.0).
- **The one sanctioned exception** is a *split* timestamp for real transforms that cannot carry data (trees, ECO-09): `r = floor(t) mod 2048` (an integer, exact in half), `g = fract(t)` (≈ 0.5 ms resolution).

**Event queue** (combat FND-4)
- Sim signal handlers run inside `World.step()`. They only append a compact record (kind, entity ids, position captured from `unit.pos`, values) to `Vfx`'s 512-record ring buffer.
- `economy_fx.gd` and `building_fx.gd` drain it at the top of `_process`. Spawns are stamped with that frame's `fx_time`. **No fx work runs inside the 30 Hz tick.**

**Randomness:** `Juice.hash01(entity id, event seq, salt)` and `Juice.vnoise` only. Never `World.rng`, never `randf()`. A burning barracks always burns from the same windows.

**Sim reads:** `display_pos()`, `display_build_progress()`, `display_upgrade_progress()` (prev→cur lerped by the physics interpolation fraction). Never raw tick values for motion. Juice never reads node global transforms (combat §2.1).

**Body writes:** juice never writes `body.transform` directly. It adds **composer layers** to combat FND-1's composer: `work`, `cargo`, `fidget`, `spawn`, `levy` for workers, and a structure composer (`settle`, `receive`, `hit`, `lean`, `collapse`) for buildings and mines. The composer writes `body.transform` once per frame.

**Fog gate**
- World-space effects and 3D sounds for an entity play only when its cell is visible to the local player (`Fog` value 2) and the entity is not invisible. Exception: own entities' HUD-level feedback (advisor lines, feed lines, the HUD itself).
- **Looped effects re-check.** `building_fx` re-tests every looped emitter on an enemy or neutral structure at the fog upload rate (10 Hz). On fog-over: set `t_stop` on its streams, release its loop voice, and freeze its damage, clip and window uniforms at their last-seen values (the ghost of rules §8). On reveal: restart from the current state.
- **Dependency:** `src/world/fog.gd` does not exist yet. Until it lands, `FxBudget.visible_at()` returns true and the fog tests are skipped with a logged reason.

**Renderer**
- No `Decal` nodes. Ground effects use GroundZones (HVF-2).
- `OmniLight3D` only through the shared LightBudget (world WLD-F4), Forward+ only.
- `cast_shadow = SHADOW_CASTING_SETTING_OFF` on **every** fx geometry, prop and pool in this doc (`shadows_disabled` only stops *receiving*).
- At startup, `RenderingServer.get_current_rendering_method()` selects the Compatibility fallbacks of §2.10.

### 2.2 Sim → view contract (what economy and production must expose)

`economy.gd` and `production.gd` do not exist yet. Juice needs the hooks below; several also serve the HUD and the AI. **Changes to `Events` and `Unit` update `docs/architecture.md` §5 in the same commit.**

| Hook | Kind | Emitted / maintained by | Notes |
|---|---|---|---|
| `resource_delivered(worker, dropoff, kind, gross, net, contact: Vector3)` | signal | economy | `kind` = `gold`/`lumber`. `net` after upkeep. `contact` = the footprint point the worker touched (rules §4.1). |
| `mine_entered(worker, mine)` / `mine_exited(worker, mine)` | signals | economy | On the tick the worker is hidden or shown. |
| `Unit.mine_queue_index` | field | economy | −1, or 0..n for workers waiting at a mine door in arrival order (rules §4.1 occupancy). |
| `resource_stage_changed(node, stage)` | signal | economy | Mine stages: 0 rich, 1 low (≤ 1,500), 2 critical (≤ 300), 3 depleted. |
| `tree_harvested(tree_index, worker, amount, left)` | signal | economy / `Doodads.harvest` | One per chop. |
| `tree_toppled(tree_index, pos, away)` | signal | `Doodads.remove_tree` | Next to the existing `tree_felled(pos)`. `away` = unit vector from the felling worker to the tree. |
| `cargo_dropped(worker, kind, amount, reason)` | signal | economy | `reason` ∈ `switch` (rules §4.3 discard), `death`, `gong` (clans §4.1). Not emitted for kept cargo (levy). |
| `construction_started(building, builder)`, `construction_cancelled(building, refund_gold, refund_lumber)` | signals | production | The existing `building_completed(u)` stays. |
| `build_order_failed(worker, pos, def_id, reason)` | signal | production | Unaffordable on arrival (rules §4.6). |
| `upgrade_started(building, to_def)`, `upgrade_finished(building, from_def)`, `upgrade_cancelled(building)` | signals | production | Hall tiers and tower morphs (rules §5.1, kingdom §7.3). |
| `research_finished(building, id)` | signal | production | Alongside `research_completed(player_id, id)`. |
| `upkeep_changed(player_id, old_tier, new_tier)` | signal | economy | |
| `levy_changed(worker, state)`; `levy_called(hall)` | signals | kingdom ability | state 0 normal, 1 arming (1.5 s), 2 militia, 3 standing down (kingdom §4). |
| `gong_sounded(hall, all_clear: bool)`; `garrison_changed(building, count)` | signals | clans ability | clans §4.1. |
| `bounty_awarded(player_id, pos, gold, lumber, gold_gross)` | signal | combat FND-4 | **Adds `gold_gross`** so the tax bite (ECO-05) can show on bounty. |
| `notification(pid, kind, text)` | existing | economy / production / input | `no_gold`, `no_lumber`, `no_food`, `cant_build`, `cant_place`, `mine_low`, `mine_collapsed`, `research_done`, `building_done`. |
| `Unit.build_progress`, `prev_build_progress`, `display_build_progress()`, `build_rate()` | fields / readers | production | 0..1; `build_rate()` = Δprogress of the last tick ÷ `World.DT` (per second). |
| `Unit.upgrade_progress()`, `display_upgrade_progress()` | readers | production | 0..1 while upgrading in place. |
| `Unit.resource_left`, `resource_max`, `miners_assigned` | fields | economy | Mines; trees keep `Doodads.lumber`. |
| `Unit.work_progress()` | reader | unit / economy | 0..1 inside the current chop, mine or repair cycle. **The strike lands at the wrap.** |
| `Unit.is_producing()`, `queue_progress()`, `research_progress()`, `stalled_for_food` | readers | production | |
| `Unit.rally_pos`, `rally_id` | fields | architecture §4 | Juice detects changes by comparing. |
| `PlayerState.food_pending` | field | production | Sum of `food_provided` of own structures under construction. |
| def `fx` block | data | `data/units.json` | See below. |

**Def `fx` hints for structures** (extends combat FND-4's block; missing hints are derived from the footprint):
`{"material": "timber|stone|felt|shell|mine", "verb": "scaffold|raising|raising_shell", "doors": [[x,y,z], …], "chimney": [[x,y,z]], "forge": [[x,y,z]], "fire_points": [[…]], "flag": [x,y,z], "crown": "onion|stork_nest|chimney_cap|wheel_finial|pennant_mast|crane_jib|gong|none", "course_h": 0.35, "windows": true, "select_sfx": "bld_<def>_select"}`.
Defaults: one door at the front (−Z) centre; chimney at a roof hash point; `course_h` 0.35 (timber, stone) or 0.5 (felt, shell).

### 2.3 FX building blocks

Economy juice adds **no new particle system, no new governor, no new spring code and no new light pool.** It extends the shared ones:

| Block | Owner | What economy adds |
|---|---|---|
| **FxSprites** (stateless shader sprites) | combat FND-2 | Two modes, plus economy sub-ranges with their own cursors (below). The names `BallisticFx` and `StreamFx` that the world and heroes docs use are now **facade functions** on `Vfx`: `Vfx.burst_ballistic(kind, …)` and `Vfx.stream_start(…) / stream_stop(id)`. |
| **GroundZones** (terrain-draped patches) | heroes HVF-2 | Economy modes and an economy sub-range (below). This replaces the old per-size `ArrayMesh` GroundFx. |
| **PopupText** (world glyph layer) | **this doc**, shared with combat CMB-28 | One `MultiMesh` of glyph quads from a numeral/icon atlas; fixed screen size; 1 draw for all popups, queue numbers, idle bubbles and stalled icons (below). |
| **WorkerProps** | this doc | **3 `MultiMesh`es, one per prop group, each a shape-select mesh**: *tools* (pick, axe, adze, mallet, peg-mallet), *cargo* (linen sack, felt bag, log bundle ×3, clans log pair, billet stack), *wear* (straw hat, kettle hat, flail, pipe, lantern, strongbox, coin heap, log pile). Every shape of the group is in the one mesh with its shape id in `UV2.x`; the vertex shader collapses vertices whose id ≠ the instance's shape id (custom data) to a degenerate point. 3 draws whatever the mix (≈ 150 k vertices at 60 workers; on Low quality, props beyond 20 m of focus are hidden). Transforms are written per frame from the composed body and bone poses into one reused `PackedFloat32Array` per group (≈ 2 µs per worker, as `HealthBars` does). Dropped props (a levy's tool and straw hat) are instances at a fixed ground pose. |
| **SiteParts** | this doc | 4 `MultiMesh`es (unit box, unit cylinder, torus, lattice panel quad) for scaffolds, ledgers, braces, ladders, ropes, lattice panels, roof poles, masts, felt rolls and crown hoist ropes. CPU writes only on change or during a short animation. |
| **MineFx** | this doc | One `MultiMesh` of quads for mine door glows, saturation lantern pips and yurt garrison knots (one shader, `mode` in custom data). |
| **Markers** | this doc | 2 `MultiMesh`es: stakes + rope (`SiteMarkers`) and rally flags with cloth flutter (`RallyMarkers`, WLD-29 cloth include). |
| **RubbleProps**, **LogPieces**, **Stumps** | this doc | Rubble stones, planks and fallen banners (1 MultiMesh); felled-log segments (1 MultiMesh, CPU closed form while rolling); stumps chunked per 32 × 32 m tile so they cull (≤ 6 visible chunks at max zoom). |
| **Structure materials** | this doc | `structure.gdshaderinc` shared by the placeholder and GLB shaders; a **build variant**, a **sketch overlay** and a **flash/rim overlay** (below). |
| **Lights** | world WLD-F4 | Fire points splat into the lantern map; real lights only by request from LightBudget (BLD-15). |
| **Audio** | UI/audio UCA-F3, AUD-02 | Loops are **virtual voices** (below). |

**FxSprites economy modes** (packing follows FND-2: basis.x = v0, basis.y = (t0, life, size0), basis.z = (size1, g, drag), origin = p0; `INSTANCE_CUSTOM` r = atlas frame + 16 × flags, g = ground_y, b = spin rad/s, a = seed)
- **Flags** (7 bits; frame + 16 × flags ≤ 2,047, exact in half): bits 0–1 mode (0 plain FND-2, 1 bounce, 2 stream, 3 flutter); bits 2–4 restitution × 0.1 (0–0.7); bit 5 settle (coin wobble at rest); bit 6 erode (alpha-scissor threshold rises 0→0.85 over life).
- **Bounce** (`BallisticFx`): drag 0, gravity `JUICE_G` (§2.4); closed-form first ground contact, one damped bounce (horizontal ×0.5, vertical × restitution), then rest. `g = max(g, 1e-3)` guards the division.
- **Flutter**: constant fall speed plus a sinusoidal sway ≤ 1.5 Hz (leaves, felt scraps, straw).
- **Stream** (`StreamFx`, looped): basis.x is repurposed as (rise_speed, **t_stop**, wind_gain); custom.g = phase ∈ [0, 1). Loop index n = floor((now − t0)/life − phase); age = (now − t0) − (n + phase)·life. **Visible only if n ≥ 0 and the emission time t0 + (n + phase)·life ≤ t_stop**, so a stream never appears fully formed at its start and stops with no CPU work. Drift = `atm_wind` (world WLD-28: one wind for all smoke) × wind_gain. A rate change never re-times a stream: doubling adds a **second stream offset by half an interval**.
- **Look:** chimney smoke and every plume puff whose spawn height is above 1.5 m are **painted cut-outs** in the FxSprites cutout pool (alpha scissor, erode flag, depth write on). They sort correctly, cost the same on Compatibility and read hand-painted. Alpha blend (the soft pool) is kept only for low ground dust rings and steam. Fire tongues, embers, sparks and glints are additive.
- **Atlas:** FND-2's 4 × 4 atlas grows to **8 × 4**. Economy adds: sack, felt bag, log bundle, billet, coin edge-on, felt scrap, plaster chunk, tile shard, rope streak, 3 painted smoke cut-outs, 3 flame tongues, hearth glyph.

**FxSprites sub-ranges requested by economy** (fixed cursors; the combat-owned ranges are never overwritten by economy spawns)

| Pool | One-shot ring | Stream slots (allocated at stream start, freed at t_stop + life) |
|---|---|---|
| cutout | 256 (coins, chips, chunks, sacks, billets, plume cut-outs) | 288 (24 smoke columns × 6, 12 doubled × 6, 24 chimneys × 3) |
| soft | 256 (ground dust rings, steam, low puffs) | – |
| additive | 192 (sparks, glints, motes) | 168 (12 fire points × (8 flames + 6 embers)) |

**Overflow rule:** a one-shot burst first checks its ring's oldest slot. If that slot is younger than 70 % of its life, the burst count is halved (minimum 1). If it is still younger, the burst is skipped. **In-flight sprites never vanish.** Streams that cannot get slots do not start; their building shows smoke at half density (BLD-15).

**GroundZones economy modes** (HVF-2's MultiMesh of a 32 × 32-quad patch; the vertex shader samples `terrain_height` + 0.04 m)
- HVF-2 capacity rises from 96 to **256**: slots 0–95 heroes, 96–255 economy (own cursor). One draw for everything.
- **Column 1 of the instance basis carries data** (t0, life, param), because the patch is flat and its height comes from `terrain_height`. The shader rebuilds the patch from columns 0 and 2 (XZ scale and yaw) and the origin (`skip_vertex_transform`). HVF-2 rows that need no time write (−1, 0, 0). *Coordination with the heroes doc: see §10.*
- Economy modes: `GRID` (placement), `STAMP_RING`, `SHOCK_RING`, `PACKED_EARTH`, `RUBBLE`, `SAWDUST`, `LEAF_LITTER`, `DASH_STRIP` (rally routes, chalk lines; dash UVs in world metres), `RIPPLE_RING` (levy, gong; notched edge).
- The placement grid (BLD-02) samples a `placement_state` L8 texture (32 × 32 cells, created once, updated with `ImageTexture.update()` at the same size, never reallocated).

**PopupText** (`src/fx/popup_text.gd` + `popup_text.gdshader`)
- One `MultiMesh`, 256 glyph instances. Atlas 8 × 4 cells of 64 px: `0–9 + − % ! ? ×`, coin, log, hearth (kingdom food), yurt (clans food), pick, axe, adze, mallet, slash ring, gong, and a 5-spoke wheel with 4 countdown states (4…1 spokes; ECO-21 leash). 31 of 32 cells used. Fill mask in R, baked 3 px outline in G; the shader composes fill = instance colour and outline = the token outline.
- **Fixed screen size:** world size per pixel = 2 · depth / (`PROJECTION_MATRIX[1][1]` · `VIEWPORT_SIZE.y`). Heights are given in px at 1080p and scale with the viewport height.
- Motion is closed-form on `fx_time` (RISE_FADE); the CPU writes glyphs only at spawn, merge and digit-roll steps.
- `no_depth_test`, unshaded, `render_priority` 20 (combat text layer). It is graded by the world's `Environment` like everything 3D; token colours are checked in the night capture (§9).
- **Cap:** at most 6 economy popups on screen; the oldest fades out over 150 ms.
- **Merge and lanes:** one pool for economy and combat text. Merge key = (player, kind, anchor entity). Two popups whose screen boxes overlap by more than 30 % take lanes: the newer one rises from 22 px higher. Maximum 2 lanes per anchor.
- *Combat CMB-28 adopting this layer is a coordination item (§10). Until it does, economy popups use PopupText alone and follow CMB-28's merge rules.*

**Structure materials and part tags**
- **Part tags:** `ProcMesh.merge` writes a part id into `UV2.x` and a sub-index into `UV2.y`: 0 body, 1 banner cloth, 2 lintel, 3 nugget (sub-index k = 0..7), 4 slab / stone ring, 5 door, 6 windows, 7 roof, 8 crown, 9 banner pole, 10 team band, 11 boards (spent mine), 12 skirt (yurt lower felt), 13 shutter. GLBs export the same tags as vertex-colour alpha (id / 16) or as named nodes `Banner`, `Lintel`, `Door`, `Chimney`, `Windows`, `Crown`, `Pole`, `Band`, `Skirt`, `Shutter`. **This is written into the asset-pipeline contract** (`docs/research/ai-asset-pipeline.md` follow-up).
- The vertex stage animates tagged vertices from **instance uniforms**: `banner_raise`, `flutter_amp`, `pole_raise`, `crown_offset` (vec4: xyz offset, w tilt), `lintel` (vec3: sag m, tilt rad, drop m), `nuggets_visible`, `slab_offset`, `door_open`, `door_glow`, `window_on`, `band_sweep`, `skirt_roll`, `damage`, `contact` (vec4: xyz + t0), `contact_amp`. No extra draws; one material.
- **Build variant** `structure_build.gdshader` (and `unit_placeholder_build.gdshader` for placeholders): `cull_disabled`; discard by the course-laid clip (BLD-06); `FRONT_FACING ? lit : #2A2420` for the inside faces the cut exposes; edge band; rafter/lattice modes. **It is swapped into `material_override` on the site's `MeshInstance3D` at `construction_started`, `upgrade_started` and structure death, and the shared material is restored on completion, cancel and when the corpse is freed.** Units never pay for `discard`.
- **GLBs:** the import step replaces GLB materials with project `ShaderMaterial`s (`building.gdshader` with a team mask, and its build variant), so the swap is always between two known materials and keeps normal/ORM maps and team colour. Nothing is copied by hand.
- **Sketch overlay** (`sketch.gdshader`, BLD-01): set as `GeometryInstance3D.material_overlay` on sites (the silhouette preview, BLD-06). Overlays receive the same instance uniforms on both renderers (verified on 4.7.2). 1 extra draw per site, only while building.
- **Flash/rim overlay** (`structure_flash.gdshader`, additive): instance uniforms `flash`, `flash_color`, `rim`, `rim_color`. Attached as `material_overlay` **only while** flash or rim > 0 (hits, select, ripple), so it works on placeholders and GLBs alike and costs nothing at rest. The old shared-uniform `flash_color` path is removed.

**Audio additions** (in `Audio`, UCA-F3)
- `play_3d(id, pos, {pitch, volume_db, priority, bus, spacing_ms, importance})`.
- `loop_3d(key, id, pos, volume_db, priority)` / `stop_loop(key, fade_ms)` are **virtual voices**: a loop that loses its player to stealing keeps its key and playback position and re-acquires a player when one frees. Without this, loops never come back after a burst of one-shots.
- `schedule_3d(id, pos, at_fx_time, opts)`: a ≤ 32-entry list checked each frame, for sounds that land with a flight (ECO-04).
- Per-id caps and spacing are enforced in `Audio`, not in fx code.

**New files**

| File | Contents |
|---|---|
| `src/fx/economy_fx.gd` | Drains economy records; mine, deposit, tree, cargo, levy and gong effects. |
| `src/fx/building_fx.gd` | Construction, upgrade, production, damage, destruction and repair state machines; fog re-checks; light requests. |
| `src/fx/juice_curves.gd` (`JuiceCurves`) | Pure static functions of age (§2.4); declares periodic frequencies. Unit-tested. |
| `src/fx/juice_palette.gd` (`JuicePalette`) | Colour tokens (§2.6). |
| `src/fx/popup_text.gd`, `worker_props.gd`, `site_parts.gd`, `mine_fx.gd`, `markers.gd`, `rubble_props.gd`, `log_pieces.gd`, `stumps.gd` | The blocks above. |
| `src/fx/shaders/structure.gdshaderinc`, `structure_build.gdshader`, `sketch.gdshader`, `structure_flash.gdshader`, `tree_common.gdshaderinc`, `tree_falling.gdshader` | Shaders. `unit_placeholder.gdshader` and `tree.gdshader` include the `.gdshaderinc`s. |
| `src/input/build_placement.gd` | Placement ghost (BLD-01..04). Owned by `CommandInput`. |
| `src/ui/resource_counter.gd`, `upkeep_ruler.gd`, `toast.gd` | HUD widgets (ECO-13, ECO-15, BLD-14). |
| `src/audio/music_clock.gd` | `MusicClock` (§2.7), a child of the music director. |

**`UnitView` additions:** the structure composer; `visual_offset()` (BLD-12); `flash(strength, color)` and `rim(strength, color)` via the overlay; worker prop slots in WorkerProps. Off-screen views skip composition (combat FND-1 frustum test).

### 2.4 Motion vocabulary (`JuiceCurves`, all f(age))

| Name | Definition | Used by |
|---|---|---|
| POP_IN | scale 0.55→1.12 in 90 ms (BACK/OUT), →1.0 in 110 ms (SINE/IN_OUT) | popups, glyphs, props appearing |
| SETTLE | Y 1→1+A (90 ms QUAD/OUT) → 1−A/2 (120 ms SINE/IN_OUT) → 1.0 (170 ms BACK/OUT); XZ = 1/√Y; pivot at base. A by material (§2.5) | completion |
| PUNCH | `offset_transform_scale` 1→S (70 ms QUAD/OUT) → 1.0 (180 ms BACK/OUT). S from the caller | HUD counters |
| SHAKE | x = A·sin(2π·t/100 ms)·(1 − t/T), 10 Hz. HUD: A 6 px, T 300 ms. World: A 0.12 m, T 300 ms | denial |
| RISE_FADE | POP_IN; y += H·(1 − (1 − t/D)³); α = 1 until 0.6·D, then 1 − ((t − 0.6D)/0.4D)². Default H 40 px (PopupText), D 1,000 ms | popups |
| FLARE | energy jumps to peak (latched), → idle over 400 ms (EXPO/OUT) | door glows |
| FLUTTER_SPIKE | cloth amplitude × k, decaying to × 1 with e^(−3t/s) | banners, pennants |
| CHIRP_SHUDDER | x = A·e^(−t/τ)·sin(2π∫f), f falling linearly 12 → 7 Hz over the duration; τ = duration/3 | building and mine shudders |
| SPRING_GLIDE | FND-1 `spring_track`, ω 40 rad/s, ζ 0.72: ≈ 4 % overshoot, settles (2 %) in ≈ 140 ms | placement ghost |
| COIN_SETTLE | tilt 25°·(1 − u)², precession phase 2π(4t + 7t³/(3T²)) (4 → 11 Hz), u = t/T, T 150–250 ms (hash) | coins, fallen gong |

**Gravity:** one `JUICE_G` = **25 m/s²** for every economy arc (coins, chips, chunks, sacks, stakes, rally flags, crowns, gongs). Materials differ by drag, restitution, spin and flutter, never by gravity. Toss times are **derived** from it: a flight of duration T between two points peaks JUICE_G·T²/8 above the chord; a drop of h takes √(2h/JUICE_G).

**Rules:** no Tweens on 3D except short scene-level sequences that are not per particle; prefer age evaluation. HUD controls use the UI doc's `UiJuice` channels (one reused tween per channel) with `offset_transform_visual_only = true`, or closed form. BACK overshoot is 1.70158 unless a row says otherwise.

### 2.5 Material response table (rule 4)

Keyed on def `fx.material`. Amplitudes scale with building height `h` capped at 6 m. **Placeholders** have big flat faces, so vertex-local effects degrade to the door, shutter and mote parts of each row; that is accepted.

| Material | Slice users | RECEIVE (deposit, garrison enter, select at 0.5×) | HIT (hit ≥ 2 % max HP; × clamp(hit/4 %, 0.5, 1.5)) | SETTLE A | Damage look (BLD-15) | Chips |
|---|---|---|---|---|---|---|
| **timber** (half-timber: oak frame, plaster panels) | kingdom Moot Hall, Croft, Drill Yard, Timber Yard, Collegium, Wainwright Yard, Curio Cabinet, Lookout | **Local flex:** vertices within 3 m of `contact` move inward along −N by 0.03·h·w·c(t), w = smoothstep(3 m, 0, dist), c = 70 ms QUAD/OUT in, 160 ms BACK/OUT out. **Door or shutter flap** rotates 12° (80 ms QUAD/OUT, then 220 ms BACK/OUT) | local flex at the hit face, 0.02·h | 5 % | plaster panels drop out (lath shows); hanging shutter < 25 % | plaster #EDE2C8 + timber #7A5634 |
| **stone** | kingdom Walled Burg, Oath Hall, Foundry, Gun Tower; clans Casting Pit, Naming Stones | **No squash.** 4 dust motes shake off the eaves (fall 0.6 m, 500 ms) + door thud | 3 motes + CHIRP_SHUDDER 0.03 m, 200 ms | 2.5 % | voronoi cracks, chipped corners | stone #8C8478 |
| **felt** (yurt domes) | clans Home Yurt, Grapple Yard, Mirror Yurt | **Breathe:** radial XZ 1→1.025, lagging 60 ms behind contact, + a felt ripple travelling up the dome at 3 m/s (0.04 m normal bulge, 0.6 m wide) | ripple from the hit point, 0.05 m | Y 4 % + XZ breathe 3 % | tears open along hashed seams; flaps flutter in `atm_wind` | felt scraps #2F7E7E (flutter mode) |
| **shell** (tortoise shell + lattice) | clans Shell Hall, Banner Shell | **Plate rattle:** each hex plate displaces 0.03 m along N × sin(2π·6t + 2π·hash(plate)) × e^(−t/100 ms), 300 ms | rattle, 0.04 m | 3 % | cracks follow hex seams (plate-edge distance field) | shell #D2B27A |
| **mine** | gold mines | **Only the lintel timbers flex:** `lintel` sag 0→0.04 m (70 ms QUAD/OUT) → 0 (160 ms BACK/OUT) | – | – | – | rock #8C8478 |
| **timber mast** | clans Spear-Mast | mast sway 1.5° (pendulum 1.4 Hz, e^(−t/400 ms)) | sway 2.5° | 2.5 % | split marks along the mast | timber #7A5634 |

### 2.6 Palette tokens (`JuicePalette`; one gold and one lumber token across all juice docs)

| Token | Hex | Token | Hex |
|---|---|---|---|
| GOLD_TEXT / outline | **#FFD34D** / #4A2E00 (same as CMB-28) | LUMBER_TEXT / outline | **#8EDB6A** / #1E3A12 (same as CMB-28) |
| FOOD_TEXT / outline | #FFF1CF / #4A3420 | TAX_TEXT / outline | #A9B1BA / #22262B |
| COIN body / rim | #F2B632 / #FFE58A (glint HDR 1.8) | WOOD_CHIP bark / inner | #6B4423 / #E9CF9B |
| SKETCH paper / ink | #F3E6C4 / #3B2A1A | SKETCH invalid / unaffordable ink | #C0392B / #8A8F96 |
| GRID valid / invalid / unaffordable | #46E07A / #FF4B3E / #9AA0A6 | DUST (biome-tinted via the LUT) | #CDB892 |
| SMOKE light / dark / burning | #6E6862 / #3E3935 / #2E2A27 | STEAM | #E8F0F5 |
| FIRE core / mid / edge | #FFE08A HDR 2.5 / #FF8A2A HDR 1.8 / #C2341A | EMBER | #FFB04A HDR 3.0 |
| SPARK (hammer) | #FFD27A HDR 2.2 | REPAIR mote | #F6FFB8 HDR 1.4 |
| DOOR_GLOW | #FFB347 | WINDOW kingdom / clans | #F08A2A HDR 1.4 (kingdom §2.5) / #FFB86B HDR 1.3 |
| EDGE kingdom / clans | #FFE2A8 × 1.3 (fresh plaster) / #E0A030 × 1.3 (saffron felt) | RIPPLE (upgrade) | #FFF1C2 HDR 1.6 |
| LEVY ivory / burgundy | #EDE2C8 / #7B1E2E (kingdom palette) | GONG bronze | #D9A55E |
| LINDEN (topping-out sprig) | #7E9A4A | LATTICE | #8A4A2A |
| UPKEEP none / low / high | #7FD86A / #FFC145 / #FF5A48 | MINE_LOW ping / DENIAL | #FFB13B / #FF5A4A |

**Team colour is reserved for ownership:** flags, pennants, stakes, rally flags, yurt bands and building trim. Never for generic particles.

### 2.7 `MusicClock` and pitched juice (rule 6)

`MusicClock` (`src/audio/music_clock.gd`, owned by the music director MUS-01; read-only for juice):
- `bpm`, `tonic` (0–11), `mode` (`ionian`, `mixolydian`, `lydian`, `dorian`, `aeolian`, `phrygian`), `is_silent`.
- `beat(t_ui) -> float`: beats since the reference. **Phase-locked** while a track plays: (stream playback position − `first_beat_s`) × bpm / 60. During the 20–40 s gaps it **free-runs** at the last bpm from the last phase.
- `scale() -> PackedInt32Array` and `note(idx) -> int` (semitones above the tonic; idx ≥ 5 adds octaves).
- `data/music.json` gains per-track `bpm`, `tonic`, `mode`, `first_beat_s`. Before the first track: kingdom G mixolydian 88 BPM; clans D dorian 92 BPM (clans §3.4 prompt).

**Scale choice (never clash with the track):**

| Track mode | Pentatonic used by all pitched juice |
|---|---|
| ionian, mixolydian, lydian | major pentatonic {0, 2, 4, 7, 9} |
| dorian, aeolian, phrygian | minor pentatonic {0, 3, 5, 7, 10} |

Faction identity comes from **timbre and motif contour**, not from a fixed scale: kingdom pitched sounds are a soft coin-bell and a woodblock; clans are a small bronze singing-bowl tap and a felt-mallet log drum. Samples are recorded at C5; `pitch_scale` = 2^(semitones/12), with the tonic placed in the octave that keeps `pitch_scale` in [0.75, 1.5].

**Users:** ECO-25 ledger phrases, BLD-08 hammer grid and tap pitches, BLD-14 ripple ticks, ECO-15 upkeep interval, BLD-11 research chuffs. **Pause:** builders freeze with the world; on unpause the next strike re-locks to the music phase.

### 2.8 Density, quality, game speed and readability

**Tiers come from combat FND-3** (Calm / Busy / Brawl, EMA with hysteresis; crossfade of multipliers over 400 ms). Economy reads them; it has no intensity metric of its own.

| Behaviour | Calm | Busy | Brawl |
|---|---|---|---|
| Deposit coins / chips | full | × 0.5 (min 2) | × 0.5 (min 1) |
| Building hit chips | full | × 0.5 | × 0.35 (min 1) |
| Popups | own on-screen deposits | same | own only, merged window 600 ms |
| Tax-bite tick, construction beds | on | **off** | off |
| Idle bubbles and beacons | on | hidden | hidden |
| Smoke α | × 1 | × 0.8 | × 0.6 |
| Route lines | α 0.55 | α 0.4 | α 0.33 |
| **Never reduced** | placement feedback, damage-state fire (state), the construction reveal, completion, denial, upkeep, mine warnings; destruction plumes keep ≥ 50 % | | |

**Juice level** (`Settings.juice_level`, shared):

| Level | Economy content |
|---|---|
| 0 Competitive | Information only: ghost, grid, popups, tax bite (visual), mine stages, damage states, upkeep and supply UI, denial, completion, course-laid reveal, lanterns. No squash, gags, chimes, beacons, leaves or light requests. |
| 1 Default | Everything in this doc except the cinematic extras. |
| 2 Cinematic | Fire light requests by day, debris and plume counts × 1.5, Lamplighter cascade, falling-log rolls. |

`reduce_motion`: no SETTLE or RECEIVE motion (sounds kept), no shudders, banners rise without overshoot. `reduce_flash`: hit flash × 0.5, glints HDR ≤ 1.5, lantern over-flicker becomes steady orange. Per-feature toggles: `eco_popups`, `saturation_lanterns`, `ledger_chime`, `building_gags`.

**Quality presets** (world WLD-F5 Low / Medium / High, separate from the information-oriented juice level):

| | Low (and llvmpipe) | Medium | High |
|---|---|---|---|
| Spawn-count multiplier | × 0.5 | × 0.75 | × 1 |
| Fire light requests | 0 | 0 | ≤ 2 at night (≤ 4 at juice level 2) |
| Falling-tree pool | 3 | 6 | 6 |
| Stream density | every 2nd column skipped | full | full |
| Site sketch overlays | nearest 1 | nearest 2 | nearest 3 |

**LOD:** spawn world juice only if the source passes a test against `Camera3D.get_frustum()` planes with a 2 m margin (there is no margin parameter on `is_position_in_frustum`). Spawn counts are scaled by clamp(28 / d, 0.5, 1), d = camera-to-source distance. Off-screen events update HUD state only.

**Game speed:** world-anchored durations and lifetimes run on `fx_time` (they follow game speed). **Rate limits, merge windows, audio spacing and caps run on `ui_time`** (they protect eyes and ears, so they hold per real second). Above 2× speed (replays, later) economy juice drops to level 0 and pitched audio stops.

**Readability rules**
1. **Render priority** follows the project table in combat §2.2. Economy rows: GroundZones economy modes 1; selection and blocker rings 2; ghost and sketch overlays 3; cutout sprites opaque pass; soft sprites 4; additive sprites and flash/rim overlays 6; health bars 10 (`no_depth_test`); PopupText 20 (`no_depth_test`). Every fx material sets it explicitly.
2. Smoke stays at α ≤ 0.5 and fades out above the roof + 3.5 m. Emitters stay inside the footprint × 0.8.
3. Plumes use **donut emission**: a ring around the footprint, with at most 6 centre puffs at α 0.25, so units fighting in ruins stay visible.
4. Gold and lumber differ by glyph and motion, not hue alone. Valid and invalid differ by hatching. Upkeep tiers use a notched-coin icon. All are safe for red-green colour blindness.
5. No whole-building luminance oscillation above 2.5 Hz (BLD-15 flash gate).

### 2.9 Fx-node inventory (economy-owned; every node here has `cast_shadow` OFF and `physics_interpolation_mode` OFF)

| Node | Type | Capacity | render_priority | Blend / depth | Compatibility |
|---|---|---|---|---|---|
| FxSprites economy sub-ranges | slots in FND-2's MultiMeshes | §2.3 table | opaque / 4 / 6 | cutout scissor + depth write / mix / add | same; HDR halo sprites per combat §2.4 |
| GroundZones economy range | slots 96–255 of HVF-2 | 160 | 1 | mix, depth test, no write | same |
| PopupText | MultiMesh | 256 glyphs | 20 | mix, `no_depth_test` | same |
| WorkerProps | 3 shape-select MultiMeshes (tools, cargo, wear) | 128 each | opaque | opaque | same |
| SiteParts | 4 MultiMeshes | 512 box, 128 cylinder, 16 torus, 64 lattice | opaque (lattice: scissor) | opaque | same |
| MineFx | MultiMesh | 128 | opaque (emissive) | opaque | same |
| SiteMarkers / RallyMarkers | 2 MultiMeshes | 64 / 24 | opaque | opaque | same |
| RubbleProps | MultiMesh | 384 | opaque | opaque | same |
| LogPieces | MultiMesh | 24 | opaque (erode scissor) | opaque | same |
| Stumps | 1 MultiMesh per 32 × 32 m tile (36) | 256 per tile | opaque | opaque | same |
| FallingTreePool | 6 `MeshInstance3D` (3 on Low quality) | 6 | opaque | opaque | same |
| TrophyCards | 2 `MeshInstance3D` | 2 | 6 | mix + HDR glint | glint halo sprite |
| Placement ghost | 1 `MeshInstance3D`, 2 passes | 1 | 3 | depth-only pass, then sketch | same |
| Site build / overlay materials | per site, swapped | – | opaque / 3 | – | same |
| Flash/rim overlay | per flashing building | ≤ 4 at once | 6 | add | same |

### 2.10 Compatibility fallbacks (by feature id; anything not listed is identical)

| Feature | Forward+ | Compatibility (`opengl3`) |
|---|---|---|
| BLD-15 fire light | lantern map + ≤ 2–4 LightBudget lights at night (High) | lantern map only (identical look by day) |
| ECO-09 tree hit time | split timestamp (exact on both) | same, verified by the 3,000 s test (§9) |
| All glints, embers, sparks | HDR + bloom | + baked halo sprite (2× size, α 0.35), combat §2.4 |
| BLD-06 sketch overlay, BLD-01 ghost | as specified | as specified (no screen reads used) |
| ECO-24 night-shift pools | lantern map | lantern map |
| P2 polish (GPU particles, trails) | `GPUParticles3D` allowed | `CPUParticles3D.convert_from_particles()` or off |
| Shader warm-up | at map load | at map load (mandatory: Compatibility compiles on first use) |

---

## 3. Feature table

Columns: ID · Feature · Trigger · Exact spec · Implementation · Perf · Priority (P0 = vertical-slice must-have). IDs from revision 1 are kept; new rows have new numbers.

### 3.1 Gold loop

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-01 | **Mine gulp & spit** | `mine_entered` / `mine_exited`; mine visible | **Gulp (enter):** mine material RECEIVE (lintel only: `lintel` sag 0→0.04 m in 70 ms QUAD/OUT, back in 160 ms BACK/OUT) · door glow FLARE to 2.4, idle 0.7 while occupied, 0.15 empty (DOOR_GLOW) · 4 lintel dust motes (fall 0.4 m, 500 ms) · 3 star glints at the door (HDR 1.8, latched, 160 ms).<br>**Spit (exit):** lintel sag 0.025 m, same timings · door FLARE 1.8 · the worker POPs 0.85→1.08→1.0 over 200 ms · dust-off: body roll ±6°, 2 cycles in 260 ms (7.7 Hz) + 6 shoulder motes · the sack appears with POP_IN.<br>**Rate limit:** 1 lintel flex per mine per 250 ms (`ui_time`); extra events only flare the door.<br>**Sound:** enter = timber creak (World −14 dB, prio 30). **Exit = door thump + effort huff + sack "flump"** (−12 dB). **No coin sounds here**; coins are saved for the deposit.<br>**Interior loop:** a muffled pick loop (clink every 380–620 ms baked in; the muffle is **baked into the asset** at authoring, LP 1.8 kHz, because `attenuation_filter_cutoff_hz` does not muffle near the camera). Starts on the first `mine_entered` within 30 m of the listener; **held 3 s after the last exit**, then fades over 400 ms, so 1-inside-at-a-time mining never toggles it. −16 dB, prio 30. | `economy_fx`; mine part tags (lintel, door); MineFx door glow; FxSprites motes and glints; `Audio.loop_3d` (virtual) | ~10 µs per event; ≤ 1 loop | P0 (interior loop P1) |
| ECO-02 | **Saturation lanterns** | 4 Hz poll of `miners_assigned` vs def `max_workers` (local player's usage) | 5 lantern pips on the lintel: Ø 0.16 m, 0.26 m apart, tilted 30° toward the camera. Lit #FFC94A HDR 1.6, lighting with a 70 ms POP; unlit #3A2E22.<br>**Oversaturated** (assigned > max): all pips flicker #FF7A3A at 3 Hz (50 % duty; steady under `reduce_flash`) and a PopupText "+N" (16 px) sits beside them.<br>α 1.0 when a worker, a hall or this mine is selected or hovered; 0.55 otherwise. Fade to 0 during collapse. **Own usage only.** | MineFx quads (mode PIPS; `lit`, `cap`, `over` in custom data) | 0 extra draws | P1 |
| ECO-17 | **Mine door queue** | `mine_queue_index` changes; mine visible | Waiting workers stand in their sim queue spots facing the door.<br>**Advance:** when a worker's index decreases, it hops: lift 0.12 m and sy 1.06 over 150 ms (SINE/OUT then QUAD/IN), timed with the sim step.<br>**Impatience:** after 1.5 s waiting, a foot tap (toe lift 0.05 m at 2 Hz, body bob 0.02 m) and a head tilt 10° toward the door. With 2 or more waiting, the last in line also sighs (−22 dB, ≤ 1 per mine per 8 s, own only).<br>An in-world oversaturation tell that complements ECO-02. | `cargo`/`fidget` composer layers; `economy_fx` | ~1 µs per waiting worker | P1 |
| ECO-06 | **Mine depletion stages & low warning** | `resource_stage_changed`; `resource_left / resource_max` | **Vein:** `nuggets_visible` = ceil(8·frac^0.7) (part tag 3, sub-index k hides nugget k). GLB vein material: `vein_glow` 0.4 + 0.6·frac, saturation × (0.4 + 0.6·frac).<br>**Low (≤ 1,500):** stone crack overlay at 35 % · lintel dust trickle (3 motes every 2.5–4 s) · timber creak every 6–10 s (World −18 dB, visible only).<br>**On entering low, once:** NTF-02 ping kind *mine low* (amber diamond pip) · advisor line (Alerts, once per mine) · feed line · lanterns blink 2×.<br>**Critical (≤ 300):** `lintel` holds at 0.06 m sag and 3° tilt (500 ms SINE/IN_OUT); each worker exit drops 2 pebbles (bounce kind). | `economy_fx`; part-tag uniforms; `Minimap.ping` | negligible | P0 warning + ping / P1 vein |
| ECO-07 | **Mine collapse** | stage 3 | **0 ms:** timber snap + deep crack; door glow → 0 in 200 ms.<br>**0–600 ms:** lintel beams rotate 18° and drop 0.4 m (QUAD/IN; `lintel` tilt and drop on part tag 2); the mound CHIRP_SHUDDERs 0.06 m (12 → 7 Hz).<br>**300–1,400 ms:** collapse layer: mound sinks to 70 % height (CUBIC/IN_OUT) with sy 0.7.<br>**300 ms:** donut plume, 28 puffs (ring r 2.2–3.2 m; below 1.5 m soft, above cutout with erode; rise 1.5 m/s, 1.6→3.2 m, life 1.8–2.6 s, α 0.5→0) + 10 rock chunks (bounce, restitution 0.3).<br>Workers inside pop out with a stumble (roll 25° and back, 400 ms, 4 motes).<br>**Afterwards:** "spent" state: part tag 11 boards the entrance in an X; vein grey.<br>**Sound:** crack (World −4 dB, prio 70) + 1.8 s rock-slide rumble (−6) + settling pebbles (−14). Advisor + grey ping. | structure composer collapse layer; FxSprites | one-off; ~38 sprites for 2.6 s | P1 |

### 3.2 Workers and cargo

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-03 | **Tools, cargo, laden walk, log stack & hoist** | order type change; `carry_gold` / `carry_lumber`; chop state | **Tool swap:** kingdom pick / axe / mallet; clans pick / **bronze adze** (clans avoid axe silhouettes) / peg-mallet. Old tool scales to 0 in 80 ms; new tool 0→1.15→1.0 (80 + 60 ms, BACK/OUT) with a 180° flip about the hand axis.<br>**Gold sack:** kingdom linen sack (#B98B4E, coin #F2B632 peeking), clans felt bag (#2F7E7E, saffron tie #E0A030); 0.28 m, on the back at (0, 0.62·h, +0.18 m).<br>**Lumber while chopping:** the load is **not** on the shoulder. Split billets (0.3 m, bark #6B4423, ends #E9CF9B) stack at the feet, 1 per 3 lumber, max 7.<br>**Hoist beat** when the worker leaves the tree (trip full or Return Cargo): 160 ms crouch (sy 0.9, QUAD/OUT) then 180 ms lift (BACK/OUT) as the billets snap to the shoulder bundle. It overlaps the first steps home (anticipation for the walk).<br>**Bundles:** kingdom 1 / 2 / 3 logs for 10 / 15 / 20 per trip (Bow Saws, Felling Crews; both *later* per kingdom §4, so the slice shows 1): **the upgrade is visible in the field**. Clans: 2 thicker strapped logs (15).<br>**Secondary motion:** FND-1 closed-form spring per cargo, fed an impulse −0.9·Δ`unit.velocity` (body-local) on each tick change. Sack ω 9.5 rad/s, ζ 0.6; logs ω 7.7, ζ 0.5; clamped to 0.08 m / 6°.<br>**Laden walk** (`cargo` layer): bob × 1.2, stride frequency × 0.95, forward lean +4°. The sim speed is unchanged.<br>**Glint:** computed in the prop shader: a highlight sweep every 1.2–2.2 s (seeded per instance, 140 ms, HDR 1.8), only within 30 m of focus. It follows the worker; nothing is spawned. | WorkerProps; `cargo` composer layer; bone anchors from `get_bone_global_pose()` once per worker per frame | ~2 µs per worker; 3 draws total | P0 (tool swap P1) |
| ECO-04 | **Deposit moment (gold & lumber)** | `resource_delivered`; drop-off visible | **Pre-wind (anticipation):** when a carrying worker whose move goal is its drop-off is within 0.9 m of the footprint edge (≈ 300 ms at 3 m/s), the cargo spring target shifts back (sack −0.10 m, logs −8° pitch) and the body leans back 4° (200 ms SINE/OUT).<br>**Event frame:** the HUD target updates **now** (ECO-13). The prop slot hides on this frame; a SACK / LOG cut-out sprite takes over at the prop's pose.<br>**Target:** the `contact` point inset 0.3 m, at y = ground + clamp(0.35·height, 0.8, 1.4 m). The door is used instead only if it is within 2 m of `contact`.<br>**Flight:** T = clamp(dist / 6 m/s, 120, 220) ms; v0 solved for landing at T under JUICE_G, so the arc peaks JUICE_G·T²/8 (≤ 0.15 m) above the chord; 1 spin.<br>**At landing (event + T): eye and ear meet on the impact.** Receiver material RECEIVE (§2.5) at the landing point, ≤ 1 per 300 ms per building · burst: gold 6 COIN (bounce + settle flags; up 2.5–3.5 m/s, lateral 0.6–1.2, restitution 0.35, life 450–650 ms, a 60 ms latched glint at apex; COIN_SETTLE at rest: **coins land face-up and wobble down**); lumber 4 CHIP + 1 LEAF · popup "+net" (PopupText, gold 20 px with coin glyph; lumber 18 px with log glyph and 0.08 m sway at 1.2 Hz) · counter bump only if unusual (ECO-13) · sound: gold = sack flump + coin jingle (World −10 dB, prio 30, ≤ 2/s per player) + the first coin's **settle tinkle** (3 ticks at 90 / 60 / 40 ms, baked); lumber = log clack (−11 dB) · ledger note (ECO-25).<br>**Merge:** same player, kind and drop-off within 350 ms → sum with a 120 ms digit roll and re-POP 1→1.1→1.<br>**Enemy deposits** (visible): toss, burst and sound, no popup. | `economy_fx`; FxSprites bounce/settle; PopupText; `Audio.schedule_3d` | ~20 µs per deposit; 0 per-frame | P0 (pre-wind, settle tinkle P1) |
| ECO-05 | **Tax bite** | `resource_delivered` with net < gross; `bounty_awarded` with gold < gold_gross | 150 ms after "+7" pops, a "−3" (PopupText 14 px, TAX_TEXT) peels off its right edge, falls 40 px (QUAD/IN, 500 ms) and fades. A grey coin chip (#8C8C8C) drops beside it and crumbles into 3 motes on landing.<br>**Also on bounty popups** (CMB-28 shows the taxed amount; rules §15.5): the same peel under the "+N".<br>Sound: dull coin-on-stone tick (World −20 dB, prio 20), first 3 bites per 10 s, off in Busy/Brawl.<br>Merged popups carry the merged tax. For 6 s after entering a taxed tier (ECO-15), every deposit shows its bite. Visual at all juice levels (information); sound off at level 0. | PopupText child glyphs; FxSprites chip | negligible | P1 |
| ECO-18 | **Cargo loss & spill** | `cargo_dropped(worker, kind, amount, reason)`; visible | **switch** (rules §4.3 discard): the sack drops from the back to the feet (JUICE_G, 0.62·h drop ≈ 260 ms) with a **sad plop** (World −16 dB); its coins shrink and desaturate to grey over 400 ms; lumber billets roll apart 0.3 m and fade over 600 ms. A grey "−10" glyph (14 px, own only) sinks 20 px.<br>**death** (a loaded worker killed): the sack bursts, 4 coins roll 0.4–0.8 m (bounce, restitution 0.25) and fade over 1.5 s; logs scatter as 3 billets. Visible to anyone who sees it: a harasser sees the economic damage.<br>**gong** (clans worker drops its load to run): plop at the feet, no glyph.<br>Kept cargo (kingdom levy) shows nothing. | `economy_fx`; FxSprites; PopupText | negligible | P1 |
| ECO-12 | **Idle workers: faction beacons** | `is_idle()` ≥ 4 s | **Fidgets** (hash-picked, every 5–9 s, `fidget` layer): lean on tool (8°, 2.5 s); look around (two ±30° glances over 1.6 s).<br>**Faction beacon after 8 s** (readable at max zoom; own workers only, ≤ 8 on screen, nearest the centre):<br>• **kingdom Hodman** lights a clay pipe: a 3-puff smoke curl every 2.4 s (cutout puffs, α 0.35, 0.15→0.5 m, rise 0.5 m/s). Idlers are spotted across a base by their pipe smoke.<br>• **clans Yurtwright** sits cross-legged (body −35 % over 400 ms, BACK/OUT) and twangs a jaw harp: −22 dB, the nearest idle worker on screen only, ≤ 1 per 12 s.<br>**Bubble:** the last job's glyph (pick, axe/adze, mallet) + "?" (PopupText 18 px, α 0.75, bob 0.05 m at 1 Hz, 250 ms fade-in). It replaces a generic "…".<br>**Night:** idle workers nap and emit the WLD-07 sleep glyph (one z).<br>**After 20 s:** kingdom workers sit too. **New order:** hop up (POP 0.9→1.06→1 + 4 motes); the pipe is pocketed (80 ms).<br>**HUD idle button** (NTF-05 owns the widget; this motion is canonical): bounce 1→1.18→1 (260 ms BACK/OUT) when the count rises + soft tok (UI −14 dB, ≤ 1 per 3 s); glow pulse (2 s period) once a worker has idled ≥ 30 s; α 0.35 at count 0. | `fidget` layer; WorkerProps pipe; PopupText; FxSprites stream (pipe smoke, 3 slots) | ~2 µs per idle worker | P1 (button bounce P0) |

### 3.3 Lumber loop

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-08 | **Chop swing, chips & thunk** | swing pose from `work_progress()` w (strike at the wrap); chips and sound on `tree_harvested` | **Axe/adze swing ≠ hammer tap.** A big diagonal swing (tool travels ±70° about a 35° tilted axis): recoil 0→0.25 (BACK/OUT) · rest 0.25→0.40 · wind-up 0.40→0.80 (QUAD/OUT, body pitched back 10°) · **hang at the top 0.80→0.91** (≈ 90 ms at kingdom's 0.8 s chop) · strike 0.91→1.0 (CUBIC/IN). Contact at the wrap.<br>**Visual hit-stop:** the rig holds the contact pose 50 ms; the sim keeps running.<br>**Chips:** 3–5 CHIP (60 % bark / 40 % inner), 0.05–0.09 m, thrown away from the worker in a 70° cone (2–3 m/s, up 1.5–2.5), JUICE_G, restitution 0.3, life 500–700 ms.<br>**Sound:** "tok" (World −12 dB, prio 30, ≤ 4 per id, ≥ 80 ms apart; pitch ECO-10) + leaf rustle on 30 % (−20 dB). Beyond 6 choppers on screen only the 4 nearest the centre are audible; all throw chips. | `work` composer layer; `economy_fx`; FxSprites | ~10 µs per chop; 20–40 chops/s in a big base | P0 |
| ECO-09 | **Tree shudder & leaf drop** | `tree_harvested` | **Shudder** (vertex shader, rotation about the base, away from the chopper): θ = 0.06 rad · e^(−6t) · sin(2π·5.5·t), weighted (h/H)^1.5. **The canopy lags the trunk by 40 ms** (vertices above 0.4·H use t − 0.04): follow-through.<br>**Hit time encoding** (Compatibility half floats): `INSTANCE_CUSTOM.r` = floor(t) mod 2048, `.g` = fract(t); age = mod(fx_time, 2048) − (r + g), +2048 if < −1024; drawn only for 0 ≤ age < 0.8 s, age clamped ≥ 0. `.b` = away angle, `.a` = lean; hollowness goes to `COLOR.a` (the tree shader uses only `COLOR.rgb`). A CPU list resets `r` to −4096 one second after each hit, so nothing replays when `fx_time` passes a multiple of 2,048 s.<br>**Leaves:** 2–4 LEAF (flutter; 0.12 m; #5E9E3A / #84B94A × tint) from 60–90 % of canopy height, fall 0.8 m/s, sway 0.35 m at 1.2 Hz, life 1.6–2.4 s. Pines shed 1–2 needles (#2E5A2A). | `doodads.gd`: `use_custom_data` before `instance_count`; `tree_common.gdshaderinc`; FxSprites flutter | one `set_instance_custom_data` per chop | P0 (leaves P1) |
| ECO-10 | **Tree hollowing & lean telegraph** | `tree_harvested` (`left / lumber_max`) | **Pitch:** per-tree hash (0.92–1.08) × 2^(s/12), s = 4·(1 − frac)^1.3. **The tree rings hollower as it empties.** At frac ≤ 0.1, a creak layer (−10 dB relative).<br>**Lean:** 6° · smoothstep(0.55, 1.0, 1 − frac), away from the latest chopper. Steps ≤ 0.6° are invisible.<br>**Canopy** desaturates 10 % below frac 0.25. | same as ECO-09 | negligible | P1 |
| ECO-19 | **Chop notch** | `tree_harvested` | A wedge painted into the trunk on the chopper's side (from `.b`), height band 0.45 m → 0.55 + 0.25·(1 − frac) m, angular half-width 10° + 35°·(1 − frac). Inside: inner wood #E9CF9B; a 0.02 m dark rim #3A2414. **Depletion is visible as well as audible.** | fragment code in `tree_common.gdshaderinc` (trunk vertices tagged by vertex colour) | ALU only | P2 |
| ECO-20 | **"Timber!" beat** | `tree_toppled` (visible) | During the 180 ms hesitation (ECO-11): the chopper steps back 0.2 m (the composer's 0.20 m body-offset cap), leans back 10° and looks up (head pitch −20°). Own workers within 4 m of the fall line flinch: sy 0.92 + 6° away, 200 ms. A short "Hup!" (kingdom) or "Hai!" (clans) from the chopper (World −16 dB, ≤ 1 per 10 s per player). | `work` + `fidget` layers | negligible | P1 |
| ECO-11 | **Tree topple, logs & stump** | `tree_toppled(index, pos, away)` | **Fall direction:** score 8 compass directions. Walk a 5 m ray in 0.5 m steps against `Doodads.tree_at_cell` and structure footprints; the count stops at the first standing trunk or footprint. A direction is valid if it has ≥ 6 free steps (3 m: the trunk never crosses a standing trunk). Score = free steps + 2 if within 60° of `away`; ties by hash.<br>**No valid direction → crumple:** the trunk telescopes into the stump over 600 ms (Y scale 1→0.15, QUAD/IN) with a 14-leaf canopy burst and a creak-crunch.<br>**Fall:** 0–180 ms hesitation (tip to 4°, SINE/OUT, creak) · 180–1,080 ms angle = 4° + 86°·((t − 180)/900)^2.2 about a pivot 0.15 m off the base · 1,080 ms impact: bounce 90→84→90° (220 ms BACK/OUT), 14 LEAF along the canopy line, 10 low dust puffs along the trunk, crash.<br>**Logs:** at 1,300 ms the trunk is replaced by **3 log segments** (hashed lengths summing to the trunk length) that roll ≤ 0.4 m downhill (terrain gradient from `terrain_height`), stopping within 500 ms (roll angle = distance / radius, closed form).<br>**Canopy → leaf litter:** a GroundZones `LEAF_LITTER` patch under the fallen canopy, α 0.6 → 0 over 30 s.<br>**Exit:** at 6 s the logs sink 0.25 m and erode (alpha scissor) over 1,200 ms. No noise dissolve, no sinking tree.<br>**Stump**, added at topple start: r 0.22 m, h 0.35 m, ringed top #D9B98A, random yaw, ±4° tilt, permanent (world memory ledger). Sawdust ring (GroundZones `SAWDUST`, α 0.4, 20 s).<br>**Sound:** creak (World −14 dB) → whoosh (−16) → leafy crash and thud (−8, prio 40). | `doodads.gd` hides the instance (existing zero scale). **FallingTreePool:** 6 `MeshInstance3D` with `tree_falling.gdshader` (shares `tree_common.gdshaderinc`; instance uniforms `tint`, `fall_angle`, `fall_axis`); **copies the instance transform and colour** on topple so size, yaw and tint never pop. **Overflow** past the pool: the MultiMesh instance itself shrink-sinks over 400 ms via per-frame `set_instance_transform`, up to 16 extra trees, then hides. LogPieces; Stumps chunks | ≤ 6 draws while trees fall; logs 1 draw | P0 (logs, litter P1) |

### 3.4 Worker mechanics of the slice

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-21 | **Levy Horn (kingdom)** | `levy_called(hall)`; `levy_changed(worker, state)` | **Horn:** two-note low wooden horn (kingdom §3.3, our own interval): owner 2D (Alerts −4 dB, prio 95); 3D at the hall for other players who see it (World −6, prio 70).<br>**Truthful ripple:** a GroundZones `RIPPLE_RING` from the hall's footprint edge to **exactly 22 m** (the rule radius) over 700 ms (CUBIC/OUT), LEVY ivory with 6 burgundy notches, edge 0.15 m, α 0.5 → 0. As the front passes each affected Hodman it turns its head to the hall and nods (120 ms).<br>**Levy flag:** a burgundy flag (kingdom §4) runs up the hall's pole in 600 ms (BACK/OUT). **It is the diegetic timer:** it lowers linearly over the 40 s. At 35 s it flutters × 2 and one short horn note plays (owner, UI −14).<br>**Arming (state 1, exactly 1.5 s, in place):** 0–250 ms the tool is tossed over the shoulder (a 250 ms closed-form arc, then it lies on the ground as a WorkerProps instance) · 250–700 ms the straw hat flips off (it lies on the ground the same way) and a kettle hat drops on from +0.6 m (JUICE_G ≈ 220 ms) with a 100 ms sy 0.92 squash · 700–1,350 ms the flail unslings and swings once overhead (chain rattle, −14 dB) · 1,350–1,500 ms stamp (sy 0.92→1.04→1). One "Ready" bark per levy (Acks).<br>**Stand down (state 3):** the lying straw hat hops back to the head (300 ms arc), the kettle hat pops off, the flail slings, the tool is picked up (1.0 s total), 4 motes; one "Back to it" line. Work resumes on the sim's schedule.<br>**Per-worker "Take Up the Flail":** the same arming, with a one-note toot from the worker (World −16) instead of the hall horn and ripple. A Hodman inside the mine when the horn sounds plays the mine spit (ECO-01), then arms.<br>**Leash** (kingdom §4: > 30 m from every hall for 5 s): a 5-spoke wheel glyph (PopupText 20 px, LEVY ivory) appears over the levy and loses one spoke per second; at 0 it stands down. **Stand Down (all):** every levy stands down with a hashed 0–300 ms stagger, so it reads as a ripple, not a switch. | `levy` composer layer; WorkerProps *wear* (straw hat, kettle hat, flail) and dropped-prop instances; GroundZones; part tag 9 + a second banner instance | ~3 µs per arming worker | P0 (flag timer P1) |
| ECO-22 | **Sound the Gong / Roll the Felt (clans)** | `gong_sounded(hall, all_clear)`; `garrison_changed(yurt, n)` | **Gong:** the hall's gong prop swings as a damped pendulum (8°, 1.1 Hz, e^(−t/0.7 s)); boom: owner 2D (Alerts −4 dB, prio 95), 3D for other players who see it (World −6, prio 70).<br>**Truthful ripple:** `RIPPLE_RING` to **exactly 30 m** over 900 ms, GONG bronze, 8 notches, α 0.5 → 0. Yurtwrights hit by the front drop their load (ECO-18 `gong`), startle-hop (lift 0.15 m, 160 ms) and run (sim).<br>**Roll the Felt:** 4 felt-knot pips on the yurt's door flap (MineFx mode KNOTS: lit saffron #E0A030, unlit #3A2E22) fill as workers enter. On the first entry the **skirt rolls up**: `skirt_roll` 0 → 1.1 m over 500 ms (BACK/OUT end), a felt-roll torus riding the edge, revealing the lattice (LATTICE). Each garrisoned worker adds a **whirling sling** in one of 4 lattice gaps (SiteParts cord + stone rotating about the gap axis at 2.5 Hz, r 0.35 m). On each of the yurt's sling attacks, that sling snaps forward (80 ms) as combat's projectile leaves.<br>**All Clear:** a softer double gong tap (−10 dB), the skirt rolls down (600 ms), workers pop out with a 150 ms hop, staggered 120 ms.<br>**Yurt destroyed with workers inside:** they pop out with a stumble (roll 25°, 400 ms) + dust. | `economy_fx`; part tag 12 (skirt); MineFx; SiteParts; GroundZones | negligible | P0 (slings P1) |
| ECO-24 | **Night shift lanterns** | 18:00–06:00 game hour; construction sites with builders; trees with choppers | Adds **lantern-map sources** (world WLD-F4; no light nodes): a site lantern (r 3 m, #FFB86B, 0.6) hung on the scaffold or mast while ≥ 1 builder is present; a ground lantern (r 2.5 m, 0.5) at a tree while ≥ 1 own or allied worker chops it. Removed 2 s after the last worker leaves (no churn). A lantern prop (WorkerProps) sits at the stump or hangs on the scaffold. Enemy sources only while visible. Updates batched to ≤ 4 per second. **The night base reads as busy.** | `building_fx`/`economy_fx` → `Lanterns.add/remove` | ≤ 4 rect updates/s | P2 |

### 3.5 HUD economy feedback

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-13 | **Resource odometers (habituated)** | `resources_changed(local)` | **Rolling digits** (closed form in `_process`, no tween per deposit): store `from`, `to`, `t0`, `dur`; shown = lerp by QUART/OUT over dur = clamp(120 + 6·abs(Δ), 150, 450) ms (`ui_time`). A retarget sets from = shown, t0 = now: no restart flicker. The target equals the sim value on the event frame.<br>**Routine gains** (Δ ≤ 2 trips of that resource): digits roll only. No punch, no flash. The icon glints (50 ms, latched) on every 5th deposit.<br>**Unusual gains:** strength s = clamp((Δ − 20) / 180, 0, 1); PUNCH S = 1.04 + 0.12·s; text flash #FFF4C2 (120 ms) only when s > 0.<br>**One API:** `ResourceCounter.bump(strength, color)`. CMB-28's coin arrival calls `bump(0.5, GOLD_TEXT)`; deposits call it with s at sack landing.<br>**Spend:** digits roll down + flash #FF9A7A (160 ms) + a 4 px drop (`offset_transform_position.y` 0→4→0, 200 ms). **Spend ≥ 200:** 2–3 coin or log icons tumble out (UI space, 400 ms).<br>**Continuous drains** (Hod Chain carriers, repair; rules §4.8) roll the digits only, never flash or drop. While any drain is active, a small down-chevron sits beside that resource's icon (α 0.8, breathing at 1 Hz); its tooltip names the sources.<br>**Income baseline** r̄ = EMA of income over 10 s per resource; feeds ECO-23 and ECO-25. | `src/ui/resource_counter.gd`; `UiJuice` `pop` channel for the rare punch | negligible | P0 |
| ECO-14 | **Denial feedback** | `notification` `no_gold`, `no_lumber`, `no_food`, `cant_build`, `cant_place` | The matching counter SHAKEs (HUD, 10 Hz, 300 ms) with text DENIAL. The pressed card button gets the same shake + a red overlay (α 0.45 → 0 over 300 ms). Cursor red slash badge 300 ms. **While placing:** the ghost SHAKEs (world, 0.12 m) and inks INVALID. **Sound:** faction error cue (UI −10 dB; kingdom double board knock, clans "hm-mm" + felt thud) + advisor (Alerts; 1.5 s per kind). | `hud.gd`, `command_card.gd`, `build_placement.gd` | negligible | P0 |
| ECO-15 | **Upkeep ruler & tier flip** | `upkeep_changed`; food changes | **Ruler:** 120 × 4 px under the food counter. Fill = food_used / food cap. Ticks at 51 and 81 (`Defs.upkeep`). Segments UPKEEP none / low / high; track #1B1F24. Within 4 food of the next threshold, that tick pulses (α 0.5↔1.0, 1.5 Hz).<br>**Label** uses the rules §4.5 wording: "Upkeep 0 %" / "Upkeep 30 %" / "Upkeep 60 %", with the notched-coin icon (0, 1 or 2 bites).<br>**Tier change:** card flip (`scale.x` 1→0 in 110 ms SINE/IN, swap text and colour, 0→1 in 130 ms BACK/OUT), **then the label pulses α 0.6↔1 at 1.5 Hz for 3 s** (rules §4.5 "flashes for 3 s").<br>**Sound** (UI −10 dB, pitched from `MusicClock`): worse = scale index 2 → 0; better = 0 → 2. Advisor ≤ once per 60 s per tier. Opens the 6 s ECO-05 teach window. | `src/ui/upkeep_ruler.gd` (`_draw()`); `hud.gd` | negligible | P0 (ruler P1) |
| ECO-16 | **Supply cap & pending supply** | food_used == cap; `food_pending`; `no_food`; a supply building completes | **Capped:** food text amber #FFB347 with a 1 px underline pulsing at 1 Hz.<br>**Pending:** " (+N)" in #8E96A0 italic, breathing α 0.6↔1; tooltip lists ETAs.<br>**Completion:** PopupText "+7" with the hearth glyph (Croft) or "+10" with the yurt glyph (Home Yurt; hall tiers per rules §4.4), 20 px FOOD_TEXT, RISE_FADE D 1,200 ms; the HUD cap rolls up with a warm flash (#FFE7A8).<br>**Stalled production:** a persistent PopupText food glyph with a red slash ring (0.35 m equivalent, 22 px, own only, α pulse 1.2 Hz) above the door until it unblocks. | `hud.gd`; PopupText | negligible | P0 (pending + stalled P1) |
| ECO-23 | **Floating-bank tell** | own gold ≥ 800 for 20 s (exit < 600 for 5 s); lumber ≥ 600 for 20 s | **Strongbox:** a small chest prop beside the main hall's door (owner's view only; opponents never see it) overflows in 3 stages at 800 / 1,200 / 2,000 gold: a coin heap grows (POP 200 ms per stage). Lumber: a log pile beside it.<br>**Sound:** while floating, the deposit jingle gains a coin-pile layer (−18 dB). The game nudges a player to spend, the way experienced players mock floating gold. | WorkerProps *wear* instances (strongbox, coin-heap and log-pile shapes); `economy_fx` | negligible | P2 |
| ECO-25 | **Ledger phrase engine** | each own on-screen deposit (at sack landing) | **Phrases, not a scale walk.** Each faction has 4 composed motifs (indices into the `MusicClock` pentatonic; 5 = octave): kingdom calm K1 [0 1 2 1 0], K2 [2 1 0 1 2 0]; bright K3 [0 2 3 4 3 5], K4 [2 3 5 4 5 6 5]. Clans calm C1 [0 0 2 1 0], C2 [3 2 1 2 0]; bright C3 [0 2 3 2 3 4 5], C4 [5 4 3 4 5 7 5].<br>Each deposit plays the next note. A finished phrase is followed by **one silent deposit**, then a new motif (hash-picked).<br>**Income in the sound:** motif weights are calm 0.7 / bright 0.3; at ≥ 8 deposits per 10 s, bright 0.7, and each note adds a fifth above at −24 dB. A booming economy sounds fuller; a stalled one goes quiet.<br>**Spacing:** ≤ 1 note per 300 ms per resource (`ui_time`); extra deposits in the window do not advance the phrase.<br>**Habituation:** −1.5 dB per continuous minute of deposits, from −16 dB to a floor of −26 dB. Reset after 20 s without deposits or a camera jump to the base.<br>**Lumber** keeps its own phrase pointer one octave lower in the faction's wood timbre. | `economy_fx`; `MusicClock`; `Audio.play_3d(…, {pitch})` | negligible | P1 |

### 3.6 Building placement

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-01 | **Surveyor's sketch ghost & spring glide** | build button → placement mode | **Surveyor's sketch shader** (not a hologram), on `ui_time`:<br>• fill SKETCH paper α 0.18 with paper grain (the world doc's 128² paper texture);<br>• outline where N·V < 0.35, SKETCH ink α 0.85;<br>• 45° screen-space hatching, period 6 px, only where N·L < 0.2 (`atm_sun`): the painted shadow becomes hatching;<br>• **line boil:** hatch and outline offsets jump by hash(floor(ui_time·8)) at ±1 px, 8 steps per second (refresh-rate independent by construction).<br>**States:** invalid = red ink #C0392B with a **doubled cross-hatch** (shape-coded); unaffordable = grey ink #8A8F96 + a coin-slash glyph (PopupText) at the cursor.<br>**Passes:** a depth-only first pass (`depth_draw_always`, ALPHA 0), the sketch in `next_pass` (the ghost material is dedicated, so `next_pass` is safe). The roof never shows through the walls.<br>**Glide:** target = `Grid.snap_to_footprint(cursor ground)`; position follows SPRING_GLIDE (ω 40, ζ 0.72: ≈ 4 % overshoot, settled in ≈ 140 ms). **It lands with a clunk.** Each cell change gives a 4 % Y-tick over 90 ms. Hovers 0.08 m up over a soft shadow (GroundZones, α 0.25).<br>**Sound:** "tock" (wooden, UI −18 dB) only when the valid state has been stable for 80 ms, ≤ 4/s. **The invalid thud never plays during a drag**; it plays only on a click attempt (ECO-14). | `build_placement.gd`; `sketch.gdshader`; placeholders reuse their merged mesh | 2 draws while placing; ~0.05 ms per cell change | P0 |
| BLD-02 | **Footprint grid & blocker callouts** | placement mode; cell change | **Grid:** GroundZones `GRID` over the footprint + a 2-cell context border. Squares inset 0.04 m, 0.03 m dark outline.<br>• Valid: GRID valid α 0.35. • Blocked: GRID invalid α 0.5 + 45° hatch (stripe 0.06 m, period 0.16 m). • Context: white α 0.12. • Unexplored: black hatch.<br>**Blockers (fog-honest):**<br>• units the local player **currently sees** (fog 2, not invisible) inside the footprint → a red ring (SelectionCircles "blocker" list), pulsing at 3 Hz;<br>• units not seen → the cell hatch only, with the generic reason "Blocked";<br>• trees → instance colour lerps to #FF6B5E, pulsing;<br>• faction ground rules → violet hatch #8E5BFF.<br>A one-line reason under the cursor (14 px) after 600 ms of stability. | GroundZones + `placement_state` texture | < 0.1 ms per update; 0 extra draws | P0 |
| BLD-03 | **Hall–mine chalk line** | placing a hall; nearest **explored** mine (fog ≥ 1) within 24 m | `DASH_STRIP` (0.12 m wide; dash 0.4 / gap 0.25 m; scrolls toward the mine at 0.8 m/s; #E8E2D0 α 0.6) from the ghost's footprint edge to the mine's.<br>**Sweet spot:** in the band [6.0 m gap (rules §3.3), +1.0 m] (`factions.json → economy.hall_mine_sweet`) the line turns GOLD_TEXT, widens to 0.18 m and shows a coin glint at its midpoint. A soft click (UI −16 dB) once on entering the band. **No magnetic snap.** | GroundZones; `build_placement.gd` | 0 extra draws | P1 |
| BLD-04 | **Stamp, surveyor stakes & failed arrival** | valid placement click; `construction_started`; `build_order_failed` | **Stamp:** ghost Y 1→0.9 (70 ms QUAD/OUT) → 1.0 (130 ms BACK/OUT), then fades over 180 ms; GroundZones `STAMP_RING` grows from 0.9× to 1.25× the footprint half-diagonal over 380 ms (α 0.55→0, SKETCH ink). Sound: mallet on paper (UI −12 dB) + the builder's Yes ack.<br>**Stakes** (owner and allies): 4 corner stakes (0.5 m), a rope outline and a team-colour pennant on the front-left stake. They drop from +0.8 m (JUICE_G ≈ 253 ms), 40 ms apart, each with a **70 ms** squash (Y 0.8→1.0, BACK/OUT). Shift-queued sites show their queue number (PopupText 16 px) on the pennant.<br>**Foundation start:** stakes pop out (scale → 0, 120 ms).<br>**Failed on arrival** (unaffordable): stakes wobble ±8° at 6 Hz for 300 ms, then topple 80° (250 ms) and fade; the worker shrugs (sy 1→1.05→1, 300 ms) at the site. The advisor line comes from rules §4.6. | `build_placement.gd`; SiteMarkers | 1 draw | P0 stamp / P1 stakes, fail |

### 3.7 Construction (shared by every verb)

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-05 | **Foundation** | `construction_started` | **Packed earth:** GroundZones `PACKED_EARTH` (footprint × 1.12, #6E5A44 α 0.6, noisy edge) fades in over 300 ms. Rubble underneath fades out (500 ms).<br>**Kingdom:** the slab (part tag 4) pops y −0.3 → +0.04 → 0 over 260 ms (BACK/OUT, overshoot 1.6).<br>**Clans:** the stone ring sets stone by stone (BLD-07C).<br>**Dust ring:** 18 soft puffs on the perimeter (outward 1.5–2.5 m/s, up 0.4, 0.6→1.4 m, 700–900 ms, DUST α 0.55→0).<br>**Sound:** deep wooden thoomp + gravel scatter (World −8 dB, prio 40). | `building_fx`; GroundZones; FxSprites | one-off | P0 |
| BLD-06 | **Course-laid reveal & silhouette preview** | every frame while under construction or upgrading; builder strikes | **Courses:** the build shader reveals the mesh in horizontal courses of `course_h` (kingdom 0.35 m ≈ 9 px tall at default zoom; clans felt 0.5 m). K = ceil(1.05·height / course_h). Within a course, the reveal runs **around the perimeter** (angle about the footprint centre, starting at the first builder's side): fragment unit u = course index + angular fraction; visible if u < P·K.<br>**Strikes lay the work:** P (the shown progress) is **latched at each builder strike** to the current `display_build_progress()`. The newly revealed span is the **fresh strip**: its top edge appears 0.08 m high and lowers into place over 110 ms (QUAD/IN), then a 60 ms BACK/OUT settle; it flashes ×1.6 edge energy for 80 ms (latched); 2 dust motes puff at its centre.<br>**Lag guard:** P never trails the raw progress by more than 1/K (one course). If it would, or if no strikes are coming (builder dead, clans Menders only, an upgrade), P catches up linearly over 300 ms.<br>**Edge band:** fragments within 0.06 m of the visible boundary glow in the faction EDGE colour.<br>**Inside faces:** `cull_disabled`; `FRONT_FACING` false → #2A2420.<br>**Milestones are structural** (verb rows): kingdom 50 % rafters, 75 % bare banner pole, 90–93 % crown; clans 0–25 % lattice, 25–45 % poles, 45–90 % felt, 90 % bands.<br>**Silhouette preview:** the sketch shader (BLD-01) as `material_overlay` at α 0.5, discarding wherever the real mesh is revealed. You can see what is being built and how far along it is without clicking. Spectators see it too.<br>HP bar and selection ring are untouched. | build-variant swap (§2.3); instance uniforms `build_p`, `fresh_lo`, `fresh_hi`, `fresh_t0`, `course_h`, `courses`, `perim_offset`, `build_mode`; sketch overlay | 1 extra draw per site; ALU only | P0 |
| BLD-08 | **Builder rhythm, sparks & work song** | builders on BUILD or REPAIR, in range; `MusicClock` | **Grid:** the hammer grid is the track's beat (`MusicClock.beat`), × 1.5 (quarter-note triplets) when the BPM is below 90. It free-runs at the last BPM during silence.<br>**Density matches build rate.** Kingdom **Hod Chain** (kingdom §4: 1 builder + up to 2 hod carriers, 1 / 1.4 / 1.8× rate): the builder taps every grid beat; carriers add **hod deliveries** on the off-beat ("and"): 1 carrier every 2 beats, 2 carriers alternating every beat. Strike density 1 : 1.5 : 2. Each delivery counts as a strike (it latches P and lays a strip) with a hod-dump clatter (World −16 dB). *If rules §4.3's older "3 builders, +60 % each" row stands instead, extra builders tap on the same off-beat slots; the density is the same.* Clans: 1 builder, quarters; Menders add no strikes (BLD-07C).<br>**Hammer pose ≠ chop pose:** a short wrist tap, 40° amplitude: wind-up 120 ms before the grid point (QUAD/OUT), contact on the point, recoil 150 ms (BACK/OUT).<br>**Each contact is a strike** (BLD-06): it latches P and lays the fresh strip.<br>**Strike particles:** 3–5 SPARK (0.05 × 0.25 m streaks, 50° up-cone, 2.5–4 m/s, JUICE_G, life 180–320 ms) on stone courses; 2 CHIP + 2 sawdust MOTE (#E9CF9B) on timber; a felt "puff" (2 soft motes) on felt.<br>**Sound:** mallet tok (World −14 dB). Pitch = site base (hash: −2, 0, +2 semitones) + the builder's scale degree (`MusicClock.note`), alternating with two degrees up. ≤ 3 builders audible per site, 6 hammer voices total.<br>**Bed:** one construction loop per on-screen site (−18 dB), **at most 2** (§5), off in Busy/Brawl, faded over 400 ms at completion.<br>**Repair:** strikes every 1.5 grid beats (still phase-locked). | `work` composer layer; `building_fx`; `MusicClock` | ~5 µs per strike | P0 (pitch/work song P1) |
| BLD-24 | **Completion anticipation & topping-out** | predicted completion; P crossing 0.95 | **Prediction:** t_done = (1 − p) / `build_rate()` from the last two ticks, re-evaluated every frame.<br>**t_done − 1,200 ms: accelerando.** The site's beat warps from 1.0× to 1.5× tempo over 600 ms (it leaves the music phase-lock; it re-locks after completion). Edge energy ramps 1.3 → 2.2 (QUAD/IN). A scaffold or lattice creak (World −16 dB).<br>**At 95 %: topping-out** (real time, 600 ms rope pull): kingdom hoists a **linden sprig** (LINDEN; a wreath on halls) up a rope line to the ridge apex, and the builders look up (head pitch −20°, 400 ms) with a small "Hoo!" (World −14 dB). Clans hoist the gong onto its frame at the door; it swings 2× and rests. The sprig stays on the roof for 90 s after completion, then wilts (desaturates over 10 s) and pops off.<br>**t_done − 510 ms: shared wind-up.** Every builder raises its tool to 120° over 450 ms (SINE/OUT) and hangs (hod carriers lift their hods overhead); the strike (60 ms, CUBIC/IN) starts at t_done − 60 ms, **so the final blow lands on the completion tick.** If the event is late, the contact pose holds (≤ 150 ms) until it arrives.<br>**Miss:** if the prediction is off by more than 150 ms (builder killed, cancel, rate change), the wind-up aborts (tools back to rest over 200 ms) and BLD-09 plays on the event alone.<br>**Stages never wait:** a stage overtaken by the next completes in 120 ms. | `building_fx` predictor; SiteParts rope + crown; `work` layer | negligible | P0 (topping-out P1) |
| BLD-09 | **Completion flourish** | `building_completed` | **0 ms:** final contact (BLD-24) · edge flash × 2.5 (latched) · the last strip closes in 80 ms · the verb's completion beat (BLD-07K scaffold collapse / BLD-07C gong strike).<br>**0–380 ms:** SETTLE with the material's A (§2.5); felt adds the radial breathe.<br>**60 ms:** dust ring, 24 soft puffs (perimeter, outward 2–3 m/s, 0.8→1.8 m, 900 ms, α 0.5, none over the roof).<br>**60–510 ms: ground shockwave** (GroundZones `SHOCK_RING`) from 0.95× the half-diagonal to +3 m (thickness 0.35→0.1 m, α 0.45→0, CUBIC/OUT, faction EDGE). **No camera shake.**<br>**150–750 ms:** the team banner runs up the pole (`banner_raise` 0.15→1, BACK/OUT 1.2), then FLUTTER_SPIKE × 2.2 over 1,500 ms.<br>**200 ms:** `window_on` ramps over 400 ms at night (WINDOW); 15 % inner glow by day.<br>**Sound:** verb completion (World −6 dB, prio 70) + the owner's faction complete cue (UI −6: kingdom hand-planed wood stroke; clans soft gong swell; 1.2–1.5 s; the same def again within 20 s uses a 0.6 s short variant) + the builder's job-done line (Acks).<br>**Off screen:** the advisor's "building finished" line + a clickable feed line (NTF-03). **No minimap ping** (NTF-02: completions never ping).<br>**Unlocks:** newly enabled command-card buttons get a diagonal glint sweep (450 ms, × 2, 300 ms apart) the first time they appear within 20 s.<br>The building is usable on the completion tick; nothing waits. Restores the shared material. | `building_fx` sequence (closed form on age); GroundZones; FxSprites; `command_card.gd` | one-off; ~30 sprites for 0.9 s | P0 (unlock glint P1) |
| BLD-10 | **Cancel / un-build** | `construction_cancelled(building, refund_gold, refund_lumber)` | P reverses to 0 over 450 ms (CUBIC/IN), course by course. Scaffold or lattice folds inward (300 ms). 12 dust puffs.<br>**Refund popups** rise from the site (gold, then lumber 150 ms later), each "+N" with a **"−25 %"** peel (the ECO-05 bite: rules §4.6 refund only 75 %). Upgrade cancels refund 100 %: no peel.<br>Sound: falling 3-note figure on scale indices 4 → 2 → 0 (World −14 dB) + clatter. | `building_fx`; PopupText | one-off | **P1** |

### 3.8 Construction verbs of the slice (full rows; both P0)

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-07K | **Scaffold-raised (kingdom)** | `construction_started`, progress, completion; def `fx.verb` = scaffold | **Scaffold erection** (real time from `construction_started`, independent of progress): poles (0.08 m, #B08550) at the corners and every 2 m (Croft 8, Drill Yard 16), each rising scale.y 0→1 over 240 ms (BACK/OUT), staggered 60 ms clockwise from the builder's side, to a first lift of 2.4 m · ledgers (0.06 m) at 1.2 and 2.4 m snap on (scale.x 0→1, 120 ms) at 400–1,000 ms · 2 braces, **only on the two faces away from the camera** · a ladder on the builder's side · rope lashings #D8C49A. 4 wood knocks (World −18 dB, 80 ms apart). **At least 70 % of the camera-side wall stays visible.**<br>**Lifts:** when the course front passes the scaffold top − 0.6 m, the poles extend 1.2 m (240 ms BACK/OUT, 40 ms stagger) and one ledger level snaps on; 2 knocks.<br>**Courses:** 0.35 m. The lowest 1.2 m of stone-floored defs (Walled Burg, Oath Hall, Foundry) throw sparks; above, chips + sawdust.<br>**Builder (1 Hodman):** BLD-08 taps at the wall. **Hod carriers (0–2, the Hod Chain):** a loop at the ladder foot timed to their off-beat deliveries: stoop and load (sy 0.92, 250 ms), lift the hod overhead and hand it up (hands +0.3 m, 200 ms BACK/OUT), a clatter of tiles or lime at the course front (2 chunks + 2 motes), lower (200 ms). The carriers' lumber cost shows as a counter drain (ECO-13). **Out of lumber:** the carrier sets the hod down and shrugs (sy 1→1.05→1, 300 ms), then stands.<br>**50 %: rafters.** Above the course front, the roof part shows a rafter skeleton (dark oak #5A3A22, 0.08 m every 0.6 m), popping in over 200 ms with a creak-thunk (World −16).<br>**75 %: bare banner pole** rises from the roof (`pole_raise` 0→1, 300 ms BACK/OUT). No cloth until completion.<br>**90 %: the crown is slung** 1.5 m above its seat (POP_IN), swaying ±6° at 0.9 Hz (e^(−t/1.2 s)). Crowns (def `fx.crown`): onion dome + Ember Wheel finial on the hall and towers; stork nest on the Croft; chimney cap on the Foundry; iron wheel finial on the Oath Hall; pennant mast on the Drill Yard; crane jib on the Wainwright Yard; log-hoist A-frame on the Timber Yard; lantern cupola on the Collegium; painted sign bracket on the Curio Cabinet. **93 %:** lowered onto its seat over 500 ms (SINE/IN_OUT) + clunk (World −14) + 6 motes. **95 %:** topping-out sprig (BLD-24).<br>**Completion beat: scaffold collapse.** Ledgers drop 0.28 m (0–150 ms, JUICE_G); poles topple outward 80° about their bases (100–450 ms, QUAD/IN); on landing (450 ms) a **dust fwump**: 20 soft puffs on the 1.3× footprint perimeter, outward 1.5 m/s, 0.6→1.6 m, 700 ms, α 0.5, ≤ 0.8 m high; pieces erode (alpha scissor) over 400 ms from 500 ms. Sound: timber clatter (World −8) + "fwump" (World −6; kingdom §3.3's complete signature).<br>**Repair variant:** a ladder leans against the damaged face (pops in 200 ms); no scaffold. | SiteParts; part tags 7, 8, 9; build shader rafter mode | ≤ 60 SiteParts instances per site; 0 extra draws | P0 |
| BLD-07C | **Raising (clans)** | same; def `fx.verb` = raising / raising_shell | **Stone ring** (replaces the slab pop): 8 stones (yurts) or 12 (Shell Hall) drop from +0.5 m (JUICE_G ≈ 200 ms), 50 ms apart clockwise from the builder, each with a 70 ms squash and a dull stone tok (World −16 dB, ≤ 4 audible).<br>**0–25 %: lattice.** 12 lattice panels (16 on the Shell Hall; LATTICE, alpha-scissor diamond lattice, 360°/12 arcs) unfold scale.y 0.1→1 over 180 ms (BACK/OUT) as P crosses 0.25·(j+1)/12, clockwise, each with a wood clack (World −16, ≥ 80 ms apart).<br>**25–45 %: poles.** At 25 % the crown ring (Ø 0.18 × dome Ø) pops onto a prop pole (POP_IN). 8 roof poles swing from lying radially outward (0°) to their final pitch, 220 ms (QUAD/OUT) each, at P = 0.25 + 0.2·(k+1)/8, each with a thunk (World −16). The builder's pose switches to "push the pole up" (hands raised 0.25 m) on each thunk.<br>**45–90 %: felt.** The dome mesh reveals by courses (0.5 m) over the lattice; the lattice panels hide below the felt clip. A **felt-roll torus** (#2F7E7E) rides the clip edge: major radius = the dome radius at the clip; minor radius r = 0.22·√(1 − u) m, u = (P − 0.45)/0.45. Each strike bumps r × 1.15 for 60 ms.<br>**90–100 %: team bands wrap.** `band_sweep` 0 → 360° in 600 ms (real time from crossing 90 %), starting at the door, with a felt "fwip" (World −18).<br>**Shell Hall** (`raising_shell`): 16 lattice panels; 4 masts swing up instead of poles (rope creak); at 45–90 % the shell's **hex plates are fitted bottom-up** (plate order by height, then angle; each fresh plate flashes × 1.6 for 80 ms and drops 0.08 m into place); felt hangings and bands at 90 %.<br>**Builder (1 Yurtwright):** peg-mallet taps (BLD-08) at the lattice.<br>**Menders** (other Yurtwrights mending the site, clans §4): **they tie ropes, they do not hammer.** A two-handed rope pull every 2 beats on the off-beat (pitch back 8°, 300 ms) + a rope streak sprite from hands to the clip edge (0.03 m, life 400 ms) + rope creak (World −22, ≤ 2 audible per site).<br>**95 %:** the gong is hoisted (BLD-24).<br>**Completion beat:** the builder strikes the gong on the completion tick (the BLD-24 wind-up targets the gong) → gong swell (World −6, prio 70). The dome breathes (felt SETTLE). Lattice, pole and roll props hide on the same frame. 16 ochre motes (#C9A46A) puff from the smoke-ring. | SiteParts (lattice, cylinder, torus); part tags 4, 10; build shader felt/lattice/plate modes | ≤ 40 instances per site; 0 extra draws | P0 |

### 3.9 Upgrades in place

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-20 | **Hall tier-up** (kingdom Moot Hall → Walled Burg; clans Shell Hall → Banner Shell; T3 later) | `upgrade_started`, `display_upgrade_progress()`, `upgrade_finished`, `upgrade_cancelled` | **Upgrading tell (the whole 130 s):** kingdom: the BLD-07K scaffold erects around the standing hall (same 1,200 ms); clans: 4 masts swing up around the shell with ropes to its rim. **The door shuts** (`door_open` → 0 over 300 ms + latch clunk; kingdom adds a timber bar across it; clans tie the door felt): the hall cannot train (rules §4.6). `door_glow` 0.<br>**Reveal through the old:** the T2 mesh is drawn with the build variant and the course-laid reveal from the base; the T1 mesh is clipped **from below** by the same boundary, so a swap line climbs the hall with the EDGE band on it. Strikes come from 2 hashed points on the course front on the music grid (sparks / chips, quieter: −18 dB).<br>**Crown last:** at 90 % the T2 crown (kingdom taller onion dome; clans the second gong and furled tall banners) is slung and lowered at 93 % (BLD-07K timings). Topping-out at 95 %.<br>**Ceremony (1.8 s; rare, rule 1):** BLD-09 plus: scaffold collapse or masts lean out and lower (500 ms) · a **tier shockwave** to +8 m (700 ms) · kingdom: the town bell peals 3× (300 ms apart); clans: the old and new gongs strike alternately 3× · banners: kingdom swallow-tail pennants unfurl on every roof point in sequence (100 ms apart); clans' tall felt banners drop open top-down (500 ms) · owner tier fanfare (UI −4 dB, 2.5 s, faction motif, prio 90).<br>**HUD** (UI doc owns the widgets): the tier pip stamps "II" (scale 1.6→1.0 in 220 ms BACK/OUT + a 24 px ink-splat ring, α 0.6→0 over 400 ms); the newly unlocked hero slot pulses 3× at 1.5 Hz with a glint sweep; unlock glints (BLD-09).<br>**Cancel:** the swap line descends over 450 ms; refund popups (100 %, no peel). | `building_fx`; two `MeshInstance3D`s during the upgrade; SiteParts | 1 extra draw during the upgrade | P0 (ceremony extras P1) |
| BLD-21 | **Tower morph** (kingdom Lookout → Gun Tower) | same signals | The same swap-line reveal over 35 s (scaffold only on the two far faces). **Completion:** the 0.6 s short ceremony; the two hook-gun crew pop up behind the parapet (POP_IN, 120 ms apart) and salute (pitch −8°, 300 ms); sound: hook-gun cock + latch (World −8). | as BLD-20 | negligible | P1 |
| BLD-22 | **Expansion founding** | a second (or later) own hall completes | 1.2 s after its fanfare, the **main hall answers**: kingdom town bell once, clans gong once (owner 2D, UI −10 dB). A `DASH_STRIP` chalk line between the two halls flashes once: a dash pulse travels from the main to the new hall at 60 m/s, α 0.6 → 0 over its 1.2 s life. Feed line "New hall raised". Own halls only. | `building_fx`; GroundZones | negligible | P2 |

### 3.10 Production & research

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-11 | **Busy-ness tells & research anticipation** | `is_producing()`, `queue_progress()`, `research_progress()` at 4 Hz | **While producing:** a chimney stream (cut-out puffs every 900 ms, 0.5→1.6 m, rise 0.9 m/s, life 2.2 s, #8A847C α 0.35; research tints 20 % toward the faction EDGE) · forges (`fx.forge`) spit 3 SPARK every 700 ms · bellows/wheels animate · `door_glow` 0.6.<br>**Training anticipation:** over the last 10 % of a unit, `door_glow` ramps 0.6→1.6.<br>**Research anticipation:** over the last 10 %, forge sparks double (every 350 ms) and the chimney **chuffs on the beat** (one extra one-shot puff per `MusicClock` beat).<br>**Idle:** cold chimney, door 0.15, nothing moves. **An idle production building looks still.** Stopping sets `t_stop`: in-flight puffs finish. | `building_fx`; FxSprites streams | ≤ 24 chimneys × 3 slots | P1 |
| BLD-12 | **Door exit & Ready** | `training_completed(building, unit)` | **Door choice:** the def door nearest the sim spawn point (rules §8: the footprint edge nearest the rally). Door FLARE (peak 2.2 → 0.6, 300 ms) + 4 dust motes.<br>**Walk-out (only if the door is ≤ 1.2 m from the spawn point):** `visual_offset` = door − spawn, decaying with smoothstep over T = clamp(2,500·d / v, 150, 600) ms (d in m, v = move speed in m/s), so the body's displayed speed peaks at ≤ 1.6× its walk speed. **Its slowest motion comes first: it emerges.** The first 120 ms add a "push through" squash (XZ 1.08, Y 0.94). Walk animation forced on.<br>**HealthBars, SelectionCircles and `Selection.pick_unit` add `UnitView.visual_offset()` while it is non-zero**, so the ring, bar and picking stay on the body.<br>**Door farther than 1.2 m:** no offset; FLARE + POP 0.85→1.06→1 (220 ms) + dust only.<br>Ready line (Acks). With a rally, the BLD-13 route line flashes once (400 ms). | `spawn` composer layer; `UnitView.visual_offset()`; the 3 readers | negligible | P0 |
| BLD-13 | **Rally flag & route line** | `rally_pos` / `rally_id` change on an own building; building selected | **Flag:** 1.4 m pole with a team-colour pennant (WLD-29 cloth). **Thrown down:** starts +1.2 m with v0 −4 m/s under JUICE_G, landing at 189 ms; Y squash 0.8→1.0 (160 ms BACK/OUT); 5 dirt motes; plant thunk (UI −14 dB).<br>**On a mine or tree:** the pennant becomes a plaque (pick or axe/adze glyph); the line tints GOLD_TEXT or LUMBER_TEXT.<br>**On a unit:** a small flag rides 2.2 m above it.<br>**Route line** while selected: `DASH_STRIP` from the door to the flag (dash 0.35 / gap 0.25 m, scrolling toward the flag at 1.4 m/s, α per §2.8, team colour lightened 30 %). Owner only. Alt shows every own flag (rules §18.6). | RallyMarkers; GroundZones | 1 draw | P0 |
| BLD-14 | **Research trophy & upgrade ripple** | `research_finished(building, id)` | **HUD:** the card icon gets a white overlay (α 0.8→0, 300 ms) + a 450 ms glint sweep; a toast "<upgrade> complete" slides in above the left of the console (from −40 px and α 0, 280 ms BACK/OUT), holds 3,000 ms, slides out 220 ms (≤ 3 stacked; NTF-03); advisor (Alerts; completions within 1 s merge).<br>**World trophy:** the upgrade's icon as a painted 3D card (0.8 m) POPs from the roof top, rises 1.2 m over 700 ms (CUBIC/OUT) while doing one Y-flip; at the 90° (edge-on) moment it catches a latched HDR 1.8 glint. Then it shrinks into a point 0.4 m lower over 200 ms, **which is the ripple's origin**. It says *which* upgrade finished.<br>**Ripple:** a wave travels out at 25 m/s. Each affected own unit on screen (def `affects`; ≤ 40 units, ≥ 15 ms apart) gets combat's rim flash (CMB-17) at 0.45 in RIPPLE + an additive glint at the weapon (attack) or chest (armour) bone. The first 6 glints tick (−22 dB) **stepping up the `MusicClock` scale** (indices 0–5).<br>**Sound:** chime (World −10 dB). | `toast.gd`; TrophyCards; `building_fx` ripple scheduler | ≤ 40 flashes; 1 draw | P0 (trophy, ripple P1) |

### 3.11 Damage, destruction, repair

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-15 | **Hit feedback & damage states** | `unit_damaged` on structures; HP thresholds with +3 % hysteresis | **Hits:** chips from the face toward the attacker (3 melee, 2 missile; material colour §2.5) + 2 dust motes + the material HIT motion (§2.5); ≤ 1 burst per building per 120 ms; hits ≥ 4 % max HP add a heavy thud (World −10 dB).<br>**Flash gate (no strobe):** hits accumulate heat H += 0.12 × (hit / 1 % max HP). A flash may **start at most every 400 ms** (2.5 Hz); it shows S = min(0.6, H accumulated since the last flash), latched, decaying over 300 ms (QUAD/OUT); H resets. Under heavy attack a building pulses at ≤ 2.5 Hz with strength ∝ damage. `reduce_flash` × 0.5. Via the flash overlay; at most 4 buildings flash at once (nearest the screen centre), the rest show chips only.<br>**States** (per material, §2.5):<br>**S1 < 75 %:** damage look begins (`damage` remaps HP 0.75 → 0.25): kingdom timber: plaster panels drop out by hashed panel id thresholded on HP, showing lath (#8A6A48 stripes; placeholders use a 1.2 × 1.0 m object-space panel grid); stone: voronoi cracks; felt: tears open along hashed seams; shell: cracks along hex seams. Soot toward the roof (× 0.7). One smoke stream at a hashed roof point: a cut-out puff every 450 ms, 0.6→2.0 m, rise 1.1 m/s, life 2.4 s, SMOKE dark→light, α 0.42.<br>**S2 < 50 % (rules §8 "Burning"):** fire at 2 hashed `fire_points` (3 on halls): 8 flame tongues each (life 450–700 ms, 0.5→0.2 m, rise 1.6 m/s, FIRE core→mid→edge→0) + 6 embers (spiral up, life 1.2–1.8 s); smoke × 2 (a second stream offset half an interval), #2E2A27. Felt tear flaps flutter in the wind (`atm_wind`).<br>**S3 < 25 %:** a third fire point; kingdom: one shutter (part tag 13) hangs on one hinge, a pendulum at 1.2 Hz, 8°, re-excited by hits ≥ 2 %.<br>**Fire budget:** 12 fire points total, assigned to the burning buildings nearest the screen centre (≈ 5 buildings). The rest show smoke + their lantern glow.<br>**Light:** each fire point splats a warm source (#FF8A3A, r 6 m, 0.8) into the lantern map (WLD-F4), flickered in the sampling shaders from `fx_time` + hash; the texture updates only when a fire starts or stops. Identical on both renderers. Real `OmniLight3D`s only by LightBudget request (class *fire*): ≤ 2 at night at juice level 1 (≤ 4 at level 2, also by day), Forward+ High only, re-ranked at 2 Hz with 250 ms energy fades.<br>**Crackle:** **one** fire bed loop at the nearest visible burning building (World −16, prio 20).<br>**Fog:** §2.1 loop re-check: on fog-over, streams stop and `damage` freezes at the last-seen value. | `building_fx` state machine; `damage` instance uniform; FxSprites streams; LightBudget | per burning building ≤ 3 × 14 slots; 1 loop total | P0 (lights P1) |
| BLD-23 | **Last legs** | HP < 10 % (exit > 13 %) | The structure composer's `lean` layer tilts it 1.5° away from the last attacker (600 ms SINE/IN_OUT; ≈ 5 px at the roof of a 7 m building) · a structural creak every 1.6–2.4 s (World −16 dB) · each hit sheds 1 extra CHUNK (bounce, restitution 0.3). **A kill-confirm telegraph for attackers.** | structure composer; FxSprites | negligible | P1 |
| BLD-16 | **Destruction (shared skeleton)** | structure `unit_died` | **Capture at the event** (the record): footprint, position, last attack direction, burning flag, faction verb, crown kind.<br>**0 ms:** flash 1.0 (latched, 120 ms) · crack + low boom (World −4 dB, prio 70); own hall: 2D alert (NTF-01).<br>**0–250 ms:** CHIRP_SHUDDER 0.08 m (12 → 7 Hz).<br>**150–1,050 ms: it falls the way it was built, in reverse.** The build variant is swapped back in and P descends from 1 to 0.15, roof to base, course by course (QUAD/IN), emitting CHUNK at the clip edge (6 per 0.5 m of descent; plaster/tile/timber, stone, felt scraps or shell plates by material) with the donut plume trailing it. **1,050–1,250 ms:** the last 15 % bursts outward (XZ 1→1.12, 200 ms) and flattens.<br>**150 ms: plume:** 32 puffs (halls 44) on a ring at 0.8–1.2× the half-diagonal; below 1.5 m soft, above cut-out with erode; rise 1.2–2.0 m/s, 1.2→3.6 m, life 2.2–3.4 s, α 0.5→0; ≤ 6 centre puffs at α 0.25. A burning building adds 10 flame puffs + 20 embers.<br>**Verb-specific beats:** BLD-16K / BLD-16C.<br>**1,600 ms: the banner falls** (1,600 ms after the event; JUICE_G) and lies on the rubble.<br>**Rubble:** spawned from the captured record at died_tick + `decay_ticks()` (rules §8: 4 s), cross-fading in from 3,400 ms: GroundZones `RUBBLE` (scorched centre if it burned) + 4–6 RubbleProps stones and planks + the fallen banner. It lasts 90 s (halls **300 s**, cap 4) and fades over 4 s, or fades in 500 ms under a new foundation. Cap 24 (oldest first). Visual only.<br>**Sound:** crack (−4) + 1.5–2 s rumble (−6) + patter (−14, ≤ 4 voices) + settling creak (−16). | the structure branch of `_animate_death` → build-variant reverse; `building_fx`; FxSprites; GroundZones; RubbleProps | one-off ~60 sprites for 3.4 s; rubble 0 extra draws | P0 (banner P1) |
| BLD-16K | **Kingdom destruction beats** | as BLD-16 | Chunks: plaster #EDE2C8, tile shards #7B1E2E, timber #5A3A22. **The crown goes last:** it is excluded from the reverse clip and sinks with the descending roof edge; at 600 ms it tips off the edge, falls under JUICE_G, lands, and **rolls 1.5 m** away from the last attacker (roll angle = distance / radius) with a bronze clang and a COIN_SETTLE wobble when it stops. Other crowns: the stork nest bursts into straw and the stork flaps away (2 s, 8 m); the chimney cap thunks.<br>**Hall:** the town bell's last note, **cracked** (pitch × 0.960, −0.7 semitone; owner 2D −6 dB; others 3D −8) at 900 ms. | as BLD-16 | – | P0 (stork P2) |
| BLD-16C | **Clans destruction beats** | as BLD-16 | Replaces the shared reverse clip. **150–650 ms, the felt tears away:** 8 felt flaps (flutter mode, 0.6 m) fling outward and flutter down over 1.2–1.6 s while the felt layer reverse-clips, exposing the lattice. **650–1,050 ms, the lattice folds flat:** collapse layer sy 1→0.08 (BACK/IN) in a dust burst. **The gong falls last** at 1,100 ms (its frame is excluded from the clip): drops from its frame (JUICE_G), clangs, and **wobbles 3× like a spinning coin settling** (COIN_SETTLE, T 900 ms, precession 3 → 9 Hz) with a bronze ring-out.<br>**Shell Hall:** the shell cracks along its hex seams; 6 plates slide off as chunks; the shell drops 0.5 m.<br>**Hall:** the gong's last note, cracked (−0.7 semitone; owner 2D −6). | as BLD-16 | – | P0 |
| BLD-17 | **Repair** | a worker repairing an own damaged building | **Kingdom Hodman:** BLD-08 taps every 1.5 grid beats; each strike: 2 SPARK + 3 repair motes (REPAIR, 0.06 m, rise 0.8 m/s, life 700 ms) from the work point. **Clans Yurtwright *Mend*:** rope pulls (BLD-07C Menders) and felt patches slapped on (a felt-scrap cut-out sticks for 600 ms).<br>**Damage follows HP continuously.** A plaster panel or felt seam that closes again appears in a **fresh-patch** tint (#F4ECD8 plaster, #3A9090 felt) that fades to normal over 20 s: the building remembers its repair.<br>**Back above 50 %:** fires snuff (shrink to 0 over 400 ms) + steam (6 soft puffs, STEAM α 0.5, rise 1.8 m/s, 900 ms) + hiss (World −12 dB). **Back above 75 %:** the smoke stream's `t_stop` is set; it thins naturally.<br>**HP bar:** a repair shimmer (a white band sweeping left→right every 900 ms). | `building_fx`; **HealthBars switches on `use_colors`** (20 floats per instance) and carries flags in `COLOR` (half precision is fine for flags), coordinated with the UI doc | negligible | P1 |

### 3.12 Building personality

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-18 | **Select voice, rim pulse & gags** | an own building becomes the primary selection | **Voice** (UI 2D, 0.6–1.2 s, ≤ 1 per 400 ms per building). Kingdom: Moot Hall / Walled Burg oak door latch + gavel double knock + moot murmur · Croft goose honk + straw rustle · Oath Hall iron-wheel ratchet + low oath hum · Drill Yard two boot stamps + "Hup!" · Foundry hammer on the anvil horn + bellows wheeze · Wainwright Yard spoke rattle + mallet · Timber Yard two-man saw rasp + log thump · Collegium page turn + soft hummed chord + leaf rustle · Curio Cabinet drawer slide + a tiny music-box ting · Lookout spyglass click + wind · Gun Tower hook-gun cock + slow-match hiss. Clans: Shell Hall soft gong tap + felt flap · Home Yurt door-flap rustle + kettle bubble · Grapple Yard wrestlers' slap + "Hoo!" · Casting Pit pour hiss + ladle clank · Naming Stones small mirror chimes + hum · Mirror Yurt 3 mirror tings · Spear-Mast wind in the tassels + javelin rattle.<br>**Pulse on a separate channel from hits:** a fresnel **rim** in team colour lightened 40 % (60 ms up, 200 ms down) via the overlay's `rim` + the material RECEIVE at 0.5×. Never the albedo flash that hits use.<br>**Gags** (6 clicks within 3 s; ≤ 1 per 60 s per building; obeys the "annoyed lines" toggle; each ≤ 1.5 s; all P2):<br>• Moot Hall: the stork on the turret clacks its bill and resettles (1.2 s). Walled Burg: a wagon in the ring rolls 0.5 m, a Hodman's head pops up and ducks (1.3 s).<br>• Croft: a goose bursts out of the door, honks, waddles 1.5 m and vanishes in a puff (1.5 s).<br>• Oath Hall: the wheel finial spins 2 turns with a ratchet (1.0 s).<br>• Drill Yard: a straw dummy spins once after a thwack and wobbles (1.2 s).<br>• Foundry: belches a smoke ring that drifts 2 m and pops into a wheel shape (1.5 s).<br>• Wainwright Yard: a wheel rolls off the rack, circles and falls over like a coin (COIN_SETTLE, 1.5 s).<br>• Timber Yard: the top log rolls off the stack, bumps the saw-horse and stops (1.2 s).<br>• Collegium: a flutter of paper notes escapes a window and is sucked back in (1.4 s).<br>• Curio Cabinet: a brass bird pops out of a drawer, whistles two notes and retracts (1.2 s).<br>• Lookout: the spyglass glints at the camera twice, "Hm?" (0.8 s). Gun Tower: a hook-gun pokes over the parapet, a slow-match puff, a cough (1.2 s).<br>• Shell Hall: **the tortoise's head slowly emerges, blinks and retracts** (1.5 s; lore check, §10).<br>• Home Yurt: the skirt flaps open and a sleepy head pokes out and yawns (1.4 s).<br>• Grapple Yard: the grapple sack swings a full loop over its beam and thuds (1.2 s).<br>• Casting Pit: the kiln burps a ring of sparks; a ladle clangs into the pit (1.2 s).<br>• Naming Stones: one carved face's mirror winks (0.8 s, tiny tink).<br>• Mirror Yurt: the mirrors flash the camera in a wave (1.5 s; HDR 1.5; halved under `reduce_flash`).<br>• Spear-Mast: the thrower twirls a javelin, fumbles, catches it at the last moment (1.4 s). | selection hook in `building_fx`; audio ids `bld_<def>_select`, `bld_<def>_gag`; gag props as SiteParts/FxSprites | negligible | P0 voice + rim / P2 gags |
| BLD-19 | **Lamplighter cascade** | the visual hour crosses dusk or dawn | **Dusk:** own and allied windows light in order of distance from the owner's main hall: delay = 150 ms + 25 ms per m (cap 4,000 ms). Each ignites with a flicker (on 60 ms, off 50 ms, on) and holds at WINDOW. **Dawn:** out in reverse order. Other players' buildings: hashed delays 0–2,000 ms. Burning buildings' windows flicker irregularly (`vnoise`, ≤ 8 Hz). Optional lantern tink on the first 3. | `building_fx` schedules `window_on` | negligible | P2 |

---

## 4. Construction verbs

### 4.1 Slice summary (detail in BLD-07K / BLD-07C and BLD-16K / BLD-16C)

| Faction | Verb (rules §4.7) | Builders | Reveal | Edge | Structural milestones | Completion beat | Destruction |
|---|---|---|---|---|---|---|---|
| `kingdom` | scaffold-raised | 1 Hodman + up to 2 hod carriers (Hod Chain, +40 % each) | courses 0.35 m, perimeter sweep | #FFE2A8 | scaffold erect · 50 % rafters · 75 % bare pole · 90–93 % crown hoisted · 95 % linden sprig | scaffold collapse + dust "fwump"; hand-planed wood stroke (owner) | reverse courses; crown topples and rolls; cracked bell (hall) |
| `clans` | raised felt ("Raising") | 1 Yurtwright; others Mend (ropes) | stone ring · lattice · poles · felt courses 0.5 m · bands | #E0A030 | 0–25 % lattice · 25–45 % poles · 45–90 % felt roll · 90 % bands · 95 % gong hoisted | the builder strikes the gong; dome breathes; soft gong swell (owner) | felt tears, lattice folds flat, gong falls last and wobbles; cracked gong (hall) |

### 4.2 Appendix: later factions (not slice; specify fully when they are scheduled)

| Faction | Verb | Sketch |
|---|---|---|
| `sylvan` | woven | A withy lattice frame rises, then bark shingles flake on bottom-up (sylvan §A, `build_progress` shader). Builders: 1 Tapster + 1 assisting (+50 %). Reuses BLD-07C's lattice panels with a withy texture and the shell-plate mode for shingles. |
| `deathless` | unearthed | The ground splits and the building rises from below as the Sexton digs; the reveal runs **top-down from a sunken start** (deathless §B). Up to 2 Sextons (+50 %). Reuses the course-laid clip with an inverted direction and a GroundZones crack mode. |

---

## 5. Audio layer recipes (economy & buildings)

These follow the UI/audio doc's buses, priorities and caps (§5.1–§5.2 there). All 3D sounds respect the fog gate. SFX use `AudioStreamRandomizer` (pitch 1.06, ±1.5 dB) unless a row sets pitch; pitched rows take their notes from `MusicClock` (§2.7).

**Loop budget: at most 4 economy loops at once**, inside the audio doc's caps: 2 construction beds + 1 mine interior (work loops, prio 30, cap 3) and 1 fire bed (prio 20, inside the world loop cap). All are virtual voices (§2.3). Construction beds are off in Busy and Brawl.

| Event | Layers (level, bus) | Positional | Prio | Caps / spacing |
|---|---|---|---|---|
| Mine enter / exit | creak −14 / door thump + effort huff + sack flump −12 (World) | 3D | 30 | 1 per mine per 250 ms |
| Mine interior | baked-muffled pick loop −16 (World) | 3D loop | 30 | 1; held 3 s after the last exit |
| Gold deposit (at landing) | sack flump + coin jingle −10; settle tinkle; ledger note −16 → −26 (World) | 3D | 30 | ≤ 2/s per player; note ≤ 1 per 300 ms |
| Lumber deposit (at landing) | log clack −11 + wood ledger note (World) | 3D | 30 | same |
| Tax bite | coin tick −20 (World) | 3D | 20 | first 3 per 10 s; off in Busy/Brawl |
| Cargo loss | sad plop −16 (World) | 3D | 30 | 1 per worker |
| Chop | tok −12 (pitch ECO-10) + 30 % rustle −20 (World) | 3D | 30 | 4 per id, ≥ 80 ms; 4 nearest choppers |
| Tree fall | creak −14 → whoosh −16 → crash −8 (World) | 3D | 40 | 2 concurrent |
| Ghost valid | tock −18 (UI) | 2D | 85 | stable 80 ms, ≤ 4/s; **no invalid thud during drags** |
| Placement stamp | mallet on paper −12 (UI) + Yes (Acks) | 2D | 90 | – |
| Foundation / stone ring | thoomp + gravel −8 / stone toks −16 (World) | 3D | 40 | ≤ 4 toks |
| Hammer strike | mallet tok −14, pitched, on the music grid (World) | 3D | 30 | 3 per site, 6 total |
| Menders | rope creak −22 (World) | 3D | 30 | 2 per site |
| Construction bed | per-faction loop −18 (World) | 3D loop | 30 | **2**; off in Busy/Brawl |
| Milestones | creak/thunk −16; crown clunk −14; "Hoo!" −14 (World) | 3D | 30 | – |
| Completion | verb beat −6 (World) + faction complete cue −6 (UI, owner) + job-done (Acks) | 3D + 2D | 70 | short variant within 20 s |
| Tier-up | completion + bell ×3 / gongs ×3 + tier fanfare −4 (UI, owner) | 3D + 2D | 90 | – |
| Levy horn / gong | horn or gong −4 (Alerts, owner 2D) / −6 (World, others) | 2D + 3D | 95 / 70 | per call |
| Unit exits | door creak −14 (World) + Ready (Acks) | 3D + 2D | 90 | ack rules |
| Rally plant | thunk −14 (UI) | 2D | 85 | – |
| Research done | chime −10 (World) + toast swish −16 (UI) + advisor | 3D + 2D | 70 | merge within 1 s; ripple ticks −22 |
| Building hit (extra) | heavy thud −10 for hits ≥ 4 % (World) | 3D | 60 | 1 per building per 120 ms |
| Burning | fire crackle bed −16 (World) | 3D loop | 20 | **1** (nearest visible) |
| Last legs | creak −16 (World) | 3D | 30 | 1 per 1.6–2.4 s per building |
| Destruction | crack −4 + rumble −6 + patter −14 + creak −16; cracked bell/gong (hall) | 3D (+2D owner) | 70 | patter ≤ 4 |
| Repair | mallet −14 / rope creak −22; snuff hiss −12 (World) | 3D | 30 | as hammer |
| Denial | faction error −10 (UI) + advisor (Alerts) | 2D | 85 | 1.5 s per kind |
| Upkeep change | two scale notes −10 (UI) + advisor | 2D | 85 | advisor ≤ 1 per 60 s per tier |
| Building select | per-type one-shot −6 (UI) | 2D | 70 | ≤ 1 per 400 ms per building |
| Mine low / collapse | creak −18 / crack −4 + slide −6 (World) + advisor + ping | 3D + 2D | 95 (alert) | once per mine |

**IP:** no WC3 audio or lines; "Job's done" and "Work complete" are banned. Job-done and advisor lines come from the faction docs' original scripts. Fanfares, ledger motifs, the levy horn interval and the gong cues are our own.

---

## 6. Our own twist (what WC3 did not have)

Each item makes a hidden number readable or gives the base character. None changes an outcome.

1. **Course-laid construction (BLD-06, 08).** Every hammer strike or hod delivery visibly lays the next strip of wall. A full Hod Chain *looks* twice as busy as a lone builder, and the reveal can never drift from the work.
2. **Completion you can feel coming (BLD-24).** An accelerando, a topping-out sprig or a hoisted gong, and a shared wind-up whose final blow lands exactly on the completion tick.
3. **The economy plays in the key of the music (§2.7, ECO-25).** Mallets lock to the track's tempo; deposits play composed phrases in its scale; a booming economy sounds fuller and a stalled one goes quiet.
4. **Saturation lanterns and the impatient queue (ECO-02, ECO-17).** "Five per mine" is shown on the mine, and the sixth worker taps its foot at the door.
5. **Tax bite on every trip and every bounty (ECO-05).** Upkeep is something the player watches peel off their income.
6. **Trees tell you they are about to fall (ECO-10, 19, 20).** The chop rings hollower, a notch deepens, the trunk leans, and the chopper looks up before it goes.
7. **The lumber upgrade is visible in the field (ECO-03).** One, two or three logs; billets stack at the feet and are hoisted for the walk home.
8. **Surveyor's sketch ghost (BLD-01).** Placement looks like boiling ink on parchment, not a hologram: hatching where the sun would shade, red cross-hatch when blocked.
9. **Silhouette preview over the site (BLD-06).** Anyone can see what is being built and how far along it is, at a glance.
10. **Busy-ness tells and research anticipation (BLD-11).** Cold chimneys are idle buildings; a research about to finish chuffs on the beat.
11. **Research trophy and upgrade ripple (BLD-14).** The finished upgrade's icon flips over the forge, then a wave shows exactly which units got it.
12. **Truthful worker-mechanic ripples (ECO-21, 22).** The levy horn's ring stops at exactly 22 m and the gong's at 30 m; the levy flag is the 40 s timer.
13. **Buildings fall the way they were built (BLD-16).** Brennish halls unbuild course by course and their onion dome rolls away; Tormai felt tears, the lattice folds, and the gong falls last and wobbles like a coin.
14. **Damage in the building's own material (BLD-15, §2.5).** Plaster drops out of oak frames, felt tears and flutters, shell plates crack along their seams; repaired patches stay fresh for 20 s.
15. **Last legs (BLD-23).** A building at 10 % leans away from its attacker and creaks: a kill-confirm telegraph.
16. **Faction idle beacons (ECO-12).** Idle Hodmen light pipes, so you can find them by smoke; idle Yurtwrights twang jaw harps.
17. **Floating-bank strongbox (ECO-23).** Unspent gold piles up visibly beside your hall, nudging you to spend.
18. **Coins settle like real coins (ECO-04).** Face-up, wobbling faster and faster to rest, with a tiny accelerating tinkle.
19. **Fallen banner and long hall rubble (BLD-16).** The flag falls last and lies on the ruins; a fallen hall's rubble stays 5 minutes.
20. **Building gags for every slice building (BLD-18)** and the **Lamplighter cascade (BLD-19).**
21. **Donut plumes and painted cut-out smoke (§2.3, BLD-16).** Set pieces never hide the fight in the ruins, and smoke reads hand-painted.
22. **Stateless GPU particles and stateless audio phrasing.** Coins, chips, debris and streams cost zero CPU per frame and are refresh-rate independent by construction.

---

## 7. Anti-patterns (do not ship these)

**Feel**
- **Mobile coin showers and slot-machine counters.** No HUD coins on every deposit; routine deposits never punch the counter (ECO-13). A small burst and one popup is the ceiling.
- **Number soup.** Merge (350 ms), cap, lanes, and own on-screen deposits only.
- **Disconnected work.** A continuous scanline that rises while builders hammer at nothing. Every strike must lay something (BLD-06).
- **Stock AI-clone effects:** fresnel-and-scanline hologram ghosts; noise-dissolve exits; sink-into-the-ground collapses; "…" thought bubbles; generic spark fountains; uniform jelly squash on stone, felt and timber.
- **Screen shake for economy or building events.** Use world-space rings, material motion and HUD micro-shakes.
- **Long ceremonies on frequent events.** Repeats get short variants.
- **Off-key and off-tempo juice.** Pitched or rhythmic sounds that ignore `MusicClock`; chromatic steps; endless looping arpeggios.
- **Fanfare without information.** If an effect answers no question and is not rare, cut it or move it to level 2.

**Gameplay safety**
- **The sim waiting on the juice.** No delayed deposits, spawns or availability. Anticipation uses predictions that may miss.
- **Juice writing sim state**, or writing `body.transform` outside the composer.
- **Fog leaks:** blocker rings on unseen units, chalk lines to unexplored mines, smoke or fire still running on a fogged enemy building, enemy saturation shown.

**Engine**
- **Frame-counted visuals, periodic motion above 12 Hz, Euler springs, `TIME` in shaders.**
- **Timestamps in half-float slots** (`INSTANCE_CUSTOM`, `COLOR`), except the split encoding.
- **Node churn:** no `Node.new()` or `create_tween()` per particle or per deposit; no Label3D per popup.
- **Per-entity draws:** props, popups or ground patches as separate nodes; any fx node casting shadows.
- **A second particle system, governor, spring library or light pool.** Extend the shared ones.
- **Per-building `OmniLight3D`s, `Decal` nodes, physics bodies for debris.**
- **Alpha-blended smoke columns in one MultiMesh** (they sort inside-out). Use painted cut-outs.

**Readability**
- **Strobing buildings** (> 2.5 Hz whole-building flashes) and the same channel for "selected" and "hit".
- **Smoke or fire covering units**; emitters outside footprint × 0.8; dense scaffolds hiding the reveal.
- **Red/green-only signals.** Always add hatching, glyphs or notches.
- **Infinite accumulation.** Rubble, logs, leaf litter and stumps have caps and lifetimes (WLD-31).

**IP**
- **Copying WC3 specifics:** lines, select sounds, level-up or completion motifs, gold-mine or scaffold model designs, "+N" font styling. **Faction cliché:** no hide tarps, bone poles, war horns or drums of the WC3 Orc look for the clans (clans §2.5); no blue roofs or gold trim for the kingdom (kingdom §2.5).

---

## 8. Budget sheet (bench: 300 units, 60 workers on screen, 12 burning buildings, 3 sites, 1 hall destroyed mid-run)

| Resource | Typical | Worst case | Budget |
|---|---|---|---|
| CPU (economy + building juice, main thread) | 0.3 ms | 0.9 ms (hall collapse frame) | ≤ 0.6 avg / ≤ 1.2 peak |
| Draw calls added (incl. shadow passes; fx cast none) | ≈ 18: props 3, SiteParts 4, sketch overlay 1, MineFx 1, markers 2, PopupText 1, RubbleProps 1, LogPieces 1, stumps 4 | ≈ 35: props 3, SiteParts 4, sketch overlays 3, flash overlays 4, MineFx 1, markers 2, PopupText 1, RubbleProps 1, LogPieces 1, stumps 6, falling trees 6, trophy 1, ghost 2 | ≤ 40 |
| FxSprites economy one-shot slots live | ~150 | cutout 256, soft 256, additive 192 (overflow rule) | sub-ranges §2.3 |
| Stream slots | ~200 | 288 cutout + 168 additive | fixed |
| GroundZones economy instances | ~30 | 160 | 160 |
| PopupText glyphs | ~30 | 256 | 256 |
| Loops | 2 | 4 | 4 |
| One-shot 3D voices (economy share) | ~5 | 10 of 24 | AUD-02 stealing |
| Lights | 0 | 2 (4 at level 2) via LightBudget | LightBudget |

**Debug overlay** (`F9` "fx stats", dev builds; the same numbers are logged by the bench every second): live slots per FxSprites kind and sub-range, overflow halvings and skips, GroundZones and PopupText counts, loops and voices in use (and stolen), light requests granted, draw calls from `RenderingServer.get_rendering_info(RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)`, current tier.

---

## 9. Verification

| Check | How | Pass criterion |
|---|---|---|
| Juice never changes outcomes | `tests/unit/test_juice_determinism.gd`: an economy scenario (5 miners, 3 choppers, a Drill Yard built with a full Hod Chain (1 builder + 2 carriers), a hall tier-up, a levy call, a gong call, 4 units trained, a building burned to 20 % and repaired, one tree felled) runs 3,600 ticks twice: `World.visuals = false`, then visuals on at juice level 2. Fx nodes have `set_process(false)`; the test calls `_process(dt)` itself with dt sequences from 1/30 to 1/240 s plus ±30 % jitter. | Per-tick hash of gold, lumber, food, unit positions, build and upgrade progress identical. |
| Refresh-rate independence | Evaluate `JuiceCurves`, RISE_FADE, COIN_SETTLE, the CPU mirror of the bounce and stream formulas, the course-laid latch and the cargo spring at the same times, accumulated with 30 steps of 1/30 s vs 240 steps of 1/240 s. | Curves exact; springs within 1 mm. |
| **12 Hz cap** | Every periodic `JuiceCurves` function declares its frequency; the test asserts ≤ 12 Hz and samples each at 1 kHz, counting zero crossings. | All ≤ 24 crossings per second. |
| Caps hold | `tests/unit/test_fx_budget.gd`: 200 `resource_delivered` in one frame, 60 `tree_harvested`, 30 completions, 14 burning buildings. | Popups ≤ 6 economy popups; sub-ranges never exceed capacity; **no in-flight slot overwritten**; fire points ≤ 12; loops ≤ 4; no errors logged. |
| **Compatibility precision** | `opengl3` run: write a tree hit at `fx_time` = 3,000 s; render 0.2 s later. | The trunk tip pose matches the Forward+ reference within 0.5°. |
| **Material swap restore** | Start a site, then complete; start another, then cancel; destroy a third mid-build. | `material_override` is the shared material again (or freed with the corpse); `material_overlay` null. |
| Fog honesty | Enemy worker chopping in fog; placement over a fogged enemy unit; a hall placed near an unexplored mine; an enemy building burning, then fogged. | 0 chips, 0 chop sounds; no blocker ring; no chalk line; **0 live stream slots and 0 loops** for the fogged building within 100 ms. |
| Look | `tests/playtest/economy_juice.gd` screenshots (llvmpipe and opengl3): ghost valid / invalid / unaffordable, kingdom site at 30 % and 92 %, clans site at 20 % and 60 %, completion at +200 ms, tier-up at 50 %, burning (< 50 %) by day and night, collapse at +600 ms (both factions), rubble, mine low, levy ripple, gong ripple with a rolled felt skirt. | Art review against §2.5, §2.6 and the readability rules; health bars visible in every capture; popups legible in the night capture. |
| Perf (real GPU) | `tests/playtest/bench_econ_fx.gd` (§8 scenario). Draws measured as the delta of `RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME` with economy juice off vs on. | §8 budgets; 60 fps on the mid-range target. |

---

## 10. Open questions and coordination items

1. **Spawn side (rules owner).** Rules §8 spawns trained units at the footprint edge nearest the rally. Proposal: spawn on the door side when the rally is within ±90° of a door, so BLD-12's walk-out plays more often. Juice works either way.
2. **GroundZones column-1 data convention and capacity 256** need the heroes doc owner's agreement (HVF-2).
3. **FxSprites sub-ranges and the 8 × 4 atlas** need the combat doc owner's agreement (FND-2).
4. **PopupText for combat text.** Should CMB-28 move from Label3D to the shared glyph layer (one draw for all text)? Economy uses it either way.
5. **`bounty_awarded` gains `gold_gross`** (FND-4) for the tax bite on bounty.
6. **World memory ledger:** add a "Hall rubble | BLD-16 | 300 s | 4 | 4 s | same" row and "Leaf litter | ECO-11 | 30 s | 48 | gradual" to WLD-31.
7. **HealthBars `use_colors`** for the repair shimmer flag (UI doc).
8. **Kingdom builders:** rules §4.3 still lists "up to 3, +60 % each"; kingdom §4 now specifies the Hod Chain (+40 % per carrier, 5 lumber per 10 s). BLD-07K/BLD-08 follow kingdom §4 and work for either.
9. **Menders on sites:** clans §4 lets Yurtwrights Mend during construction; rules §4.8 says repair applies to complete buildings only. The visuals (BLD-07C) work for either ruling.
10. **Shell Hall gag (BLD-18):** a living tortoise under the hall is a lore choice; confirm with the clans lore (§1.3) or swap for the mirror-wink gag.
11. **Music metadata:** every track in `data/music.json` must carry `bpm`, `tonic`, `mode` and `first_beat_s`; the generator prompts already state key and BPM (clans §3.4).
12. **Hall–mine optimal band** (`economy.hall_mine_sweet`): tune once gather timings exist.
13. **Gold popups for veterans:** should `eco_popups` default off at juice level 0, leaving only the tax bite? Decide by playtest.
14. **Allied saturation lanterns** in the ally colour? Default: own usage only.
15. **Art needed:** painted cut-out smoke (3), flame tongues (3), crack and seam masks, lattice texture, panel/lath mask, rubble meshes, prop meshes (15 kinds), glyph atlas, trophy-card frame. Until then, procedural fallbacks keep "runs without art".

---

## Critique log

Revision 2 applies every blocker and major item from both critiques, the strongest missing features, and the minor fixes. Critic A reviewed feel and design fit; critic B reviewed engine feasibility.

| # | Severity | Critique | Resolution |
|---|---|---|---|
| A1 | blocker | Stale archetypes (Stalwart/Warband/…); Warband is the banned WC3-Orc cliché; verbs contradict rules §4.7; second slice verb unimplementable; stale "+6" and "hall bell" | Re-keyed to `kingdom`/`clans`. Full P0 rows **BLD-07K** (scaffold-raised; scaffold collapse + dust fwump; hand-planed wood stroke) and **BLD-07C** (Raising: stone ring, 12 lattice panels at 180 ms, 8 poles at 220 ms, felt roll r = 0.22√(1−u), bands in 600 ms, gong strike, dome breathe; Menders tie ropes). Builder counts per the faction docs: kingdom §4 **Hod Chain** (1 builder + up to 2 hod carriers, +40 % each; this revises the older "3 builders, +60 %" row the critique cited from rules §4.3) and clans §4 (1 builder + Menders). Sylvan/deathless moved to the §4.2 appendix. Food popups +7 / +10; select voices enumerated per slice building. |
| A2 | major | Hologram ghost; exponential glide never clicks; 1.5 % tick invisible | **BLD-01** surveyor's sketch (parchment fill, ink fresnel step, sun-shadow hatching, 8 fps line boil, cross-hatched invalid, coin-slash unaffordable); SPRING_GLIDE ω 40 / ζ 0.72 (≈ 4 % overshoot); 4 % tick over 90 ms; depth-only first pass. |
| A3 | major | Strikes never lay anything; continuous scanline; milestones invisible | **BLD-06** course-laid reveal latched by strikes, fresh strip drop + flash, lag guard; structural milestones in the verb rows. |
| A4 | major | No completion anticipation; research gets none | **BLD-24** predictor, accelerando, topping-out, shared wind-up landing on the tick, 150 ms miss fallback; **BLD-11** research anticipation. |
| A5 | major | Door exit at ~43 m/s, fastest first | **BLD-12** offset ≤ 1.2 m, smoothstep over clamp(2.5·d/v, 150, 600) ms (peak ≤ 1.6× walk speed), push-through squash, POP-only beyond 1.2 m. |
| A6 | major | Deposit toss through the hall; unclear timing | **ECO-04** targets the `contact` point (door only within 2 m), T = clamp(d/6, 120, 220) ms, arc from JUICE_G; HUD on the event, punch/burst/popup/sound at landing; pre-wind added. |
| A7 | major | Counter throbs all match; two different bumps | **ECO-13** habituation (routine deposits roll only; 50 ms glint every 5th), strength formula, one `bump(strength, color)` API used by CMB-28. |
| A8 | major | Four tonal systems with no key or tempo | **§2.7 MusicClock**: bpm, tonic, mode, phase lock and free-run; scale from the track mode; hammer grid = track BPM (×1.5 below 90); density 1 : 1.33 : 2. |
| A9 | major | Ledger chime undefined at saturation; no income encoding | **ECO-25** phrase engine: 4 composed motifs per faction, phrase rests, income weighting + fifth layer, habituation to −26 dB, ≤ 1 note per 300 ms. |
| A10 | major | Jelly stone; uniform squash | **§2.5 material response table** (timber local flex + door flap, stone motes only, felt breathe + ripple, shell plate rattle, mine lintel only; SETTLE by material). |
| A11 | major | Strobing hits; select = hit channel; glass cracks on every material | **BLD-15** heat accumulator with a 2.5 Hz flash gate; select moved to the rim channel (BLD-18); per-material damage (plaster panels/lath, felt seams, shell hex seams, stone voronoi). |
| A12 | major | Generic sink collapse; no hall set piece; no faction destruction | **BLD-16** reverse course-laying with edge chunks and outward burst; **BLD-16K** dome topples and rolls 1.5 m; **BLD-16C** felt flaps, lattice folds, gong falls last and wobbles; cracked bell/gong, banner fall, 300 s hall rubble. |
| A13 | major | Trees clip into the forest; noise dissolve | **ECO-11** 8-direction free-cell scoring (never crossing a trunk), crumple fallback, 3 rolling log segments, leaf-litter patch, erosion exit at 6 s. |
| A14 | major | Logs on the shoulder while chopping; wrong bundle formula | **ECO-03** billets at the feet, hoist beat, bundles 1/2/3 (kingdom) and 2 strapped (clans); **ECO-08** axe swing with a 90 ms hang vs BLD-08's 40° wrist tap. |
| A15 | major | Frame counts and > 12 Hz shudders | 50 ms glint, 70 ms stake squash, 12 Hz rule and test, tree 5.5 Hz with 40 ms canopy lag, mine and buildings CHIRP_SHUDDER 12 → 7 Hz. |
| A16 | major | Popups sized by zoom; mismatched tokens; no bite on bounty | **PopupText** fixed screen size (gold 20, lumber 18, tax 14, food 20 px); GOLD_TEXT #FFD34D and LUMBER_TEXT #8EDB6A shared with CMB-28; ECO-05 on bounty. |
| A17 | major | Unsorted alpha smoke columns | Painted cut-out smoke with erosion above 1.5 m; alpha blend only for ground dust (§2.3). |
| A18 | minor | Double jingle; choppy interior loop; 3 timings for 2 segments | ECO-01 exit = thump + effort huff + flump; loop held 3 s; lintel 70 / 160 ms. |
| A19 | minor | Generic "…" idle bubble | ECO-12 faction beacons (pipe smoke, jaw harp), last-job glyph + "?", night naps. |
| A20 | minor | Generic research fountain; undefined GOLD token; chromatic ticks | BLD-14 trophy card, RIPPLE token, scale-stepped ticks. |
| A21 | minor | Governor without hysteresis; LOD radius cuts corners | FND-3 tiers with hysteresis and crossfade; frustum-only LOD with count scaling (§2.8). |
| A22 | minor | Inconsistent gravities; 99 m/s² toss | JUICE_G = 25; durations derived (sagitta JUICE_G·T²/8, drop √(2h/g)); rally flag thrown down (189 ms). |
| A23 | minor | Ring buffers pop in-flight bits | Economy sub-ranges + 70 % halve/skip rule; tested. |
| A24 | minor | Cancel at P2; no failed-arrival state | BLD-10 P1 with a "−25 %" peel; BLD-04 failed-arrival wobble, topple and shrug. |
| A25 | minor | Upkeep label vs rules §4.5 | ECO-15 uses "Upkeep 0/30/60 %" and pulses for 3 s. |
| A26 | minor | Gags not enumerable | BLD-18 lists one gag per slice building with durations. |
| A27 | minor | Valid/invalid sound machine gun | BLD-01: tock after 80 ms stability, ≤ 4/s; invalid thud only on click. |
| A-missing | – | Hall tier-up, morphs, Levy Horn, Gong/Felt, cargo loss, mine queue, chop notch, Timber! beat, topping-out, floating bank, coin settle, expansion founding, last legs, faction destruction, research anticipation, night shift | BLD-20, BLD-21, ECO-21, ECO-22, ECO-18, ECO-17, ECO-19, ECO-20, BLD-24, ECO-23, COIN_SETTLE (ECO-04), BLD-22, BLD-23, BLD-16K/C, BLD-11, ECO-24. |
| B1 | blocker | One shared placeholder material: next_pass and cull mode leak to every unit; GLB swap drops maps and team colour | Per-site `material_override` swap to a dedicated build variant (`cull_disabled`, shared `.gdshaderinc`), restored on completion/cancel/corpse free; silhouette via `material_overlay`; GLB import replaces materials with known project shaders (§2.3). |
| B2 | major | Tree hit time in half-float custom data | Split timestamp (integer seconds mod 2048 + fraction), wrap handling, age clamp, −4096 reset; away/lean in b/a, hollowness in `COLOR.a`; Compatibility test at 3,000 s. |
| B3 | major | GroundFx meshes cached per size are wrong and one draw each | Rebuilt on HVF-2 GroundZones: one MultiMesh, `terrain_height` in the vertex shader, time in the basis, economy sub-range; placement state texture updated in place. |
| B4 | major | 150–300 draws vs a ≤ 20 claim | Shape-select MultiMeshes for props (3 draws for every prop), shared MultiMeshes for markers, mine fx, site parts, rubble and glyphs; shadows off; worst case ≈ 35 against a measured budget of ≤ 40 including shadow passes (§8). |
| B5 | major | Duplicated sprite system, governor, Euler springs, light pool, direct body writes | FxSprites modes (BallisticFx/StreamFx are facades), FND-3 tiers, FND-1 closed-form springs with velocity impulses, LightBudget requests, composer layers. |
| B6 | major | Merged placeholder mesh: banner, slab, lintel, nuggets cannot move | `UV2` part tags + instance uniforms; GLB named-node / vertex-alpha convention written into the asset contract. |
| B7 | major | Door-exit offset leaves bars, rings and picking behind | ≤ 1.2 m offset; `UnitView.visual_offset()` read by HealthBars, SelectionCircles and `pick_unit`; spawn-side proposal in §10. |
| B8 | major | Fog leaks (blocker rings, chalk line, looped smoke/fire) | Visible-only blocker rings; explored mines only; 10 Hz loop re-check freezing last-seen state; tests. |
| B9 | major | 8 persistent loops vs audio caps; non-muffled interior | ≤ 4 economy loops as virtual voices; beds off in Busy/Brawl; muffle baked into the asset. |
| B10 | minor | Shadow casting on fx MultiMeshes; uncullable stumps | `cast_shadow` OFF everywhere (§2.1, §2.9); stumps chunked per 32 m tile. |
| B11 | minor | Contradictory draw order | Adopted the project render-priority table (combat §2.2) and listed economy rows (§2.8). |
| B12 | minor | Stream capacity, start pop, re-time pop, sorting, NaN | Fixed stream sub-pools (12 fire points), emission-time mask, half-interval second stream, cut-outs, `max(g, 1e-3)`. |
| B13 | minor | Popping fire lights outside LightBudget | Lantern-map splats (both renderers) + ≤ 2/4 LightBudget lights re-ranked at 2 Hz with 250 ms fades. |
| B14 | minor | World-size Label3D; grading claim false; 3 draws each | PopupText glyph layer, fixed screen size, honestly graded (night capture check), 1 draw. |
| B15 | minor | `fx_time` registration error | Declared in `project.godot [shader_globals]`. |
| B16 | minor | Frame-counted glint/squash; jitter without a generator | 50 ms glint, 70 ms squash; jitter replaced by material HIT motion and CHIRP_SHUDDER (≤ 12 Hz). |
| B17 | minor | Tween per deposit | Closed-form odometer; tweens only for rare punches via `UiJuice`. |
| B18 | minor | Detached sack glint; per-deposit node churn | Glint in the prop shader; SACK/LOG cut-out sprite in the pool; prop slot hidden on the same frame. |
| B19 | minor | Falling trees lose tint/scale; dissolve taxes all trees; overflow undefined | `tree_falling.gdshader` + copied transform and colour; no dissolve (erosion only on logs); overflow shrink-sinks up to 16 instances. |
| B20 | minor | No free health-bar channel; flash only on placeholders | HealthBars `use_colors` flags; flash/rim as an additive `material_overlay` attached only while active. |
| B21 | minor | Fx work inside the sim tick | Event records drained at the top of `_process` (§2.1). |
| B22 | minor | No corpse-removal event; no frustum margin parameter; ghost overdraw | Rubble from the captured `unit_died` record at decay end; `get_frustum()` planes with 2 m; depth-only ghost pass. |
| B23 | minor | Untestable deltas; missing tests | Manual `_process(dt)` with `set_process(false)`; Compatibility, material-restore, fog-over and draw-count tests (§9). |
| B-missing | – | Node inventory, Compatibility column, budget sheet, event queue, part-tag convention, game speed, quality scale, debug overlay, fog dependency, popup merge with CMB-28 | §2.9, §2.10, §8, §2.1, §2.3, §2.8 (game speed, quality presets), §8 overlay, §2.1 fog note, PopupText merge and lanes. |
