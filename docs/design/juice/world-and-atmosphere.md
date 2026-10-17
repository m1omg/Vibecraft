# Juice spec: World & Atmosphere

*Domain doc of the Vibecraft juice bible. Revision 2, 2026-10-17 (revision 1: 2026-10-16). Status: design spec, ready to implement; rows that depend on another doc name the request in §12.*
*Covers:*
- *day and night: sun and moon, grading, the nightfall tide, stingers and the dusk/dawn beat sheet, lights of dusk, night readability, the sleeping body of creep camps, fireflies and moths, dawn dew;*
- *sky on the ground and weather: cloud shadows, the one wind with lag and recoil, drizzle and rain, mist, gust-borne seeds, canopy dapple, the distant storm;*
- *foliage and ground cover, water by body size, the life layer (the slice critter cast, flights and bird shadows, the aftermath);*
- *fog-of-war rendering, settlement and memory (house smoke, cloth, desire paths, the persistence ledger), faction base life;*
- *the places of Wether Downs, world ambience audio and the living minimap.*

*Out of scope (owned by sibling docs, referenced by id):*
- *Chopping, tree shudder and tree fall: ECO-08..11. Nest trees and the Croft's stork: ECO-29 (this doc flies them, WLD-23).*
- *Production chimneys, building fire, collapse and rubble, the lamplighter cascade: BLD-11, BLD-15, BLD-16, BLD-19.*
- *Footstep dust and the per-stride shallow-water ring: CMB-04. Creep "notice": CMB-06. Corpses and the scar map: CMB-30..32.*
- *Creep family sleep props, the wake startle, "!" / "‼", camp roar, leash and cleared: heroes CRP-01..04. The Firefly Jar: heroes ITM-03 (it uses WLD-08's anchored variant).*
- *Spells, hero events, the HUD day clock (HUD-07), minimap pips and pings, the battle and march beds (`mix_beds.gd`), the duck arbiter, camera shake and the bus layout: UI doc.*

**Inputs:**
- `docs/research/visual-art-direction.md`: "storm-lit heroic diorama", cloud shadows, wind sway, night tinted blue (never black), fog values, VFX are the only things that bloom.
- `docs/research/audio-direction.md`: beds, sweeteners, buses and caps (§3.5, §6.3).
- `docs/research/video-references.md`: M3 day/night (WC3's ≈ 3 s light change; the 3.2 s sight ease), M4 sleeping creeps, B7.
- `docs/research/godot-rts-tech.md` and `docs/architecture.md`: 30 Hz sim, the 480 s cycle (20 s per game hour), 1 m `Fog` grid, `CHUNK_TILES` 16, no `Decal`, Compatibility limits.
- **Canon this revision is bound to:** `neutrals.md` §1.2 (camp bands and shield pips), §1.5 (sleep schedules, "never letters"), §5.3 and §5.8 (Weighstall, Hale Spring), §6 (critters); `slice-plan.md` §1.4, §1.9, §1.12 and E13; `art-and-audio-bible.md` §1.5, §6.3, §7.5, §9.7, §9.8; `rules.md` §13 (sight changes over 3.2 s); `tools/ip/banned_terms.txt`.

**Shared plumbing with siblings.**
- **Clocks:** `fx_time` (= `Vfx.now`, economy §2.1, combat §2) for cosmetic oscillators; **`sim_time`** (heroes HVF-7: (tick + lead) × DT, frozen on pause, never steps back) for everything tied to the sim. **`hour` = `DayNight.hour_at(sim_time)`** (§2).
- Particle systems reused: FxSprites (combat FND-2), BallisticFx, StreamFx and GroundFx (economy §2.3). PopupText is not used here.
- Governor reused: combat FND-3 tiers and brawl clusters, economy `FxBudget`.
- This doc owns the shared **LightBudget** (WLD-F4) and **WorldMemory** (WLD-31).

---

## 1. Feel goals

Vibecraft's world is **one particular painted place, Wether Downs, that keeps time, breathes with one wind, remembers what happened, and never lies**.

WC3 made its maps feel alive with a few cheap conventions: a blue night tint, a sound at dusk, sleeping creeps, a critter to click. We keep the conventions and add three things:
1. **Coherence.** One clock and one wind drive every blade of grass, flag, smoke column, waterwheel paddle and ambient sound. A gust front visibly bends the grass first, then the trees half a second later, which spring past rest and settle. The world moves as one organism with inertia, not a hundred unrelated sine loops.
2. **Place.** The Weighstall's brass pans tip in the wind, the Muddy Lantern's sign creaks, the Charcoal Clamps seep smoke from their turf seams, the Hale Spring's wheel turns, and the Standing Ring hums louder at night. Each landmark has its own wind response, its own dusk and its own night.
3. **Information.** Golden light says night is coming. Snore rings count a camp's tier. Motion means you can see it; stillness means you only remember it. Dew trails show who walked the meadow at dawn.

All of it is **cheap by construction**. Closed-form shaders and a handful of packed textures stand in for hundreds of lights, particles and nodes, so it survives 300 units and a software renderer.

**Pillars**
1. **The ground is our sky.** At −56° pitch the camera never sees the sky, so sky events are painted onto the ground: cloud shadows, gust sheen rolling through grass, cat's paws racing over ponds, the nightfall tide, rain rings, bird shadows. Nothing is spent where the camera cannot look.
2. **One clock, one wind, with inertia.** Everything samples `hour`, `fx_time`, `sim_time` and the same world-space wind field. Each layer reads that field with its own lag and recoil (WLD-10).
3. **If it moves, you can see it.** In live vision the world animates. Remembered (fogged) areas are still, faded and sketched. Unexplored areas are a drifting sea of cloud.
4. **Telegraph, never obscure.** Atmosphere announces changes early (golden hour, a violet pre-dawn, sleep glyphs) and never covers what matters:
   - mist stays below the knees and under every ring;
   - rain is a whisper;
   - at midnight, units keep ≥ 60% of their noon luma on screen (measured, §9).
5. **Honest to the fog.** No critter, bird, footpath, light, sound or felled tree reacts to something the local player cannot see. There is one sanctioned exception, the sim-driven Sparrow Roost flush (§2).
6. **Cheap by construction.** The whole domain fits in ≤ 0.6 ms CPU and ≤ 15 added draw calls (§9). Its main tools:
   - textures act as lights (the lantern map);
   - motion is closed-form, and every scroll is integrated on the sim clock;
   - grass, particles and mist live in camera-local wrap volumes;
   - critter logic runs on 14 hand-placed animals.

---

## 2. Ground rules (bind every row below)

**Clocks and determinism**
- **`hour` = `DayNight.hour_at(sim_time)`.** It pauses with the game, follows game speed, never steps back on resume, and uses the same mapping as the sim's `is_day()`. `DayNight.current_hour()` switches to it (today it adds `world.interpolation_fraction()`, which reads 1.0 while paused; request §12).
- **`fx_time`** drives cosmetic oscillators: flicker, flutter, sway phases, blink.
- **The rate rule:** never multiply `fx_time`, `sim_time` or `hour` by a value that changes over time.
  - A wave whose frequency depends on wind gains a t·df/dt term, and a scroll whose speed or direction drifts gains a t·d′ term. Both grow without bound over a match (revision 1 measured gust fronts sliding sideways at 490 m/s by minute 30, and flags flapping above 100 Hz).
  - **Oscillators:** use fixed frequencies; let wind change only amplitudes or crossfade weights (WLD-29).
  - **Scrolls:** Atmos integrates one offset per layer **on the sim clock**: `ofs += d(t)·v(t)·DT` per tick, wrapped modulo the layer's texture period, plus the lead fraction for display (WLD-F1). This is deterministic, follows pause and game speed, matches replays, ignores refresh rate, and keeps float precision bounded.
- **Never use the shader built-in `TIME`.** It runs while paused and wraps at `rendering/limits/time/time_rollover_secs`. Today's `tree.gdshader` and `water.gdshader` use it; WLD-F2 replaces it.
- **Closed form only.** Every animated value is f(`hour`, `fx_time`, `sim_time`, the scroll offsets, an event t0).
  - CPU smoothing uses `Juice.damp()` (combat FND-1) only for UI-like gains.
  - **Wind direction is closed form** (smooth noise of sim time), so nothing world-wide is damped.
  - Critters move along timed segments whose t0 snaps to the 10 Hz Life tick.
  - No Tween ever touches world state.
- **Everything runs in `_process`.** Per-tick integration is a catch-up loop inside `_process`, keyed to `world.tick_count`; nothing runs in `_physics_process`.
- **Read-only.** Atmosphere never calls `World.rng`, never writes sim state and never delays a sim event. The weather schedule and visual randomness use their own `RandomNumberGenerator`, seeded from hash(map name, match seed, salt).

**Node policy**
- `World/Atmos` and `World/Life` set `physics_interpolation_mode = PHYSICS_INTERPOLATION_MODE_OFF`; children inherit it. A node moved in `_process` with interpolation on renders up to 0.15 m behind at 10 m/s (spike, 4.7.2).
- Wrap volumes (grass, air, rain, mist) are **static** `MultiMeshInstance3D`s. They read the snapped box origin from the globals `atm_cam_box` and `atm_grass_box`, so no node moves per frame.
- Every vertex-animated MultiMesh sets `custom_aabb` = map bounds × (−2 m … 25 m).
- **All atmosphere geometry sets `cast_shadow = SHADOW_CASTING_SETTING_OFF`.**

**Fog honesty (three rules and one exception)**
1. Nothing here reacts to a unit the local player cannot currently see, unless it is the player's own unit.
2. Nothing animates in explored-but-not-visible areas (the stillness rule, WLD-27).
3. No world memory (wear, dew trails, felled trees, stains, lantern pools, grass clearings, reveal rims) is created from an event the local player did not see.
- **The one exception: the Sparrow Roost flush** (neutrals §6, SLICE+). It is a deterministic sim trigger (any player's ground unit within 4 m). Its flight and sound are drawn for **every player who has the roost's area explored**: above the fog, never in the black mask. It reveals by design and equally for all players. Nothing else in this doc may do this.

**Readability limits (hard caps, verified in §9)**

| Layer | Limit |
|---|---|
| Night | **Metric:** Rec.709 luma of the final sRGB pixels. **Units-layer mask** ≥ 0.60 × the 12:00 value; **world** (explored, non-unit pixels) 0.35–0.45 × noon. Tested at **00:30, 18:15 and 05:40**. Team-colour chroma ≥ 70% of noon. Nothing pure black outside unexplored areas. |
| Cloud shadows | Multiply ≤ 0.32 on ground and props, ≤ 0.19 on units (units take 0.6×). Rings, bars and markers are never multiplied (composite order, WLD-F2). |
| Mist | Height-following grid at ≤ 0.35 m and ≤ 0.75 m above the local lowland floor. α ≤ 0.30 / 0.18. Covers feet, never torsos. **Drawn under every ring, zone and marker** (render priority 5). |
| Rain | Streak α ≤ 0.16 before width compensation, length ≤ 0.6 m, ≤ 900 on screen, screen width 1.25 px. α ×0.6 in Brawl. No lens rain. |
| Air | Ambient firefly core 0.04 m at HDR ≤ 1.3 (the Firefly Jar keeps HDR 2.0, WLD-08). ≤ 64 ambient fireflies, ≤ 96 seeds, ≤ 24 moths on screen. ×0.3 inside the brawl radius. |
| Critters | Toy scale 0.3–0.6 m tall. Saturation ≤ 40% (accents ≤ 10% of the silhouette up to 70%). Never team-coloured. **Selectable** (info panel, click gags; neutrals §6) but never attackable and never in a box selection. Selection ring ivory #E6D8B8, never a relation colour. Not drawn in fog. |
| Birds | Flight altitude ≥ 6 m. ≤ 18 px at default zoom (kites ≤ 30 px, storks ≤ 36 px). Ground shadows α ≤ 0.25. |
| Bloom | Only flames, embers, ignition sparks, fireflies, dew and water glints exceed HDR 1.0. Glints are capped at 1.3 and ≤ 2% of their surface's pixels. Terrain, foliage, water bodies, mist, clouds and lantern pools stay ≤ 1.0. |
| Lantern pools | Add at most +0.45 × albedo. Warm light may shift any of the 12 team colours by ≤ 8° hue. |
| Ground cover | Tufts ≤ 0.38 m (×1.5 in the far LOD, still ≤ 0.57 m and only beyond 45 m). No grass on paved roads, known footprints, water or the 0.5 m cliff-edge band. |
| Fog states | Differ by value and texture (grain), never by hue alone. |
| Colour-blind safety | Camp tier = **snore-ring count** (1 / 2 / 3), not only colour. Wear = value change, not only hue. |

**Legibility floor** (adopts heroes §2.6; default camera 28 m, FOV 45°, pitch −56°, 1080p: ≈ 46 px/m for ground width, ≈ 26 px/m for upright height, × 0.61 at max zoom 46 m). Sizes clamp in the shader: `size = max(size_m, min_px / px_per_m(view_depth))`.
- **Any motion must move ≥ 1.5 px at 28 m:** ≥ 0.035 m sideways, ≥ 0.06 m vertically. Otherwise it becomes a value change (±6% or more) or is cut.
- **Minimum sizes:** sleep glyph 10 px; snore ring 6 px at birth; firefly core 2 px (plus halo); moth 2 px; seed 2 px; bird 4 px; rain streak width 1.25 px; anything carrying a gag uses toy scale (≥ 0.3 m).
- Revision 1 rows cut or converted by this rule are listed in the critique log (#A10).

**Renderer tiers**

| Thing | Forward+ | Compatibility | Container (lavapipe / opengl3) |
|---|---|---|---|
| House-light `OmniLight3D` pool | 4, inside the 12-light LightBudget | off; the lantern map carries the look. **LightBudget capped at 8 total and ≤ 8 per terrain chunk** | off |
| Shader tier `atm_quality` | High | Low (forced) | Low (tests), High for look captures |
| Grading saturation and contrast | `Environment` adjustments | `Environment` adjustments (spike, 4.7.2: identical; the `atm_grade` fallback is deleted) | as renderer |
| `light_angular_distance` (soft long shadows) | High only | 0 + `soft_shadow_filter_quality` | 0 |
| Soft mist intersections | heightmap fade (no depth texture) | same | same |
| MultiMesh custom data | float | 16-bit, so absolute times live in the instance transform (combat FND-2) | same |

**Sim → view hooks this doc needs.** Whoever lands a hook updates `docs/architecture.md` in the same commit.

| Hook | Kind | Owner | Used by |
|---|---|---|---|
| `Unit.sleeping`, `Unit.camp_id`, `Unit.sleep_schedule` (`night` / `day` / `never`); `Events.creep_sleep_changed(u, asleep: bool, reason: StringName)`, reason ∈ `dusk`, `dawn`, `damage`, `build`, `trade`, `spell`. The sim staggers sleep 0–6 s per creep and wakes a camp in one tick (neutrals §1.5). | field + signal | `creeps.gd` | WLD-07, heroes CRP-01..02 |
| `creeps.gd` sets the sim facing toward the camp's `fire_point` (or centre) when a creep falls asleep (proposal; the visual fallback clamps to CMB-05's ±20°) | sim | `creeps.gd` | WLD-07 |
| `MapData.creep_camps[i]`: `total_level`, `family`, `centre`, `fire_point`, `leader_id` | data | map | WLD-07, 34 |
| `MapData.props`: `[{def, pos, yaw, parts}]`, non-blocking decor (§4.10 lists the slice set) | data | map | WLD-05, 21, 33, 40–48 |
| `MapData.landmarks`: `[{kind, pos, parts}]` for the places of §4.10 (`weighstall`, `inn`, `spring`, `ring`, `clamp`, `patch`, `crow_field`, `seam`, `fold`, `pond`) | data | map | WLD-32, 33, 40–48 |
| `MapData.water` value **2 = shallow, walkable** (bed at water_level − 0.35 m). **Required for the Hale Spring pool** (neutrals §5.8, slice-plan E13, P0). Other fords stay open (§11). | data + pathing | map + `pathing.gd` | WLD-20, 42 |
| `MapData.sun_axis`: unit XZ vector from sunrise to sunset; default (1, 0), which is screen-left → screen-right at camera yaw 0 | data | map | WLD-01, 03 |
| `Fog`: grids stored as **display bytes** (0 / 128 / 255), so an upload is a straight `Image.set_data()`; `upload_time` (sim seconds), `period`, `flip`; `Fog.is_visible(pid, cell)`; the list of newly explored cells per upload | fields + reader | `fog.gd` | WLD-25, 26 and every fog gate |
| `Doodads.remembered_felled`: a tree felled outside the local player's vision stays drawn until its cell is seen | field | `doodads.gd` | WLD-27, 31, 34 |
| Def `fx` hints (economy §2.2 block): `lamps`, `windows`, **`smoke_point`**, `chimney`, `cloth`, **`lamp`** (hero lantern: bone, offset, tint, flicker), optional `eaves` | data | `units.json` | WLD-05, 06, 11, 28, 29 |
| `hit_landed`, the intensity I and per-frame **brawl clusters** (≤ 8) (combat FND-3, FND-4); **`Vfx.battle_started(pos)`** (CMB-36) | reader + signal | `vfx.gd` | WLD-08, 21, 23, 24 |
| `sim_time`, `FxRead.lead()`, UnitPosTex (heroes HVF-7); `terrain_h` and `terrain_corners` (heroes HVF-2) | globals + include | heroes | everything time- or ground-bound |
| `Events.roost_flushed(roost_id, pos)` (SLICE+) | signal | `creeps.gd` / neutrals | WLD-23 |

**Notation:** as the siblings use it.
- Durations are ms at 1× game speed. Game hours are hh:mm; 1 game hour = 20 s. "T0" is the dusk or dawn event (18:00:00 or 06:00:00).
- Colours are sRGB hex. "HDR n" means emission multiplier n. Easings are the `Juice` Penner set (`out_back(k)` = overshoot k).
- w = local wind 0..1.2 and g = local gust 0..1 (WLD-10). ★ = our own twist (§7).

---

## 3. Foundations (build first)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-F1 | **Atmos director: clocks, scroll integration, globals, monitors** | every frame (`_process`, PAUSABLE) | **Reads:** `sim_time`, `fx_time`, `hour`, weather (F3), the FND-3 governor, the camera (focus, distance, footprint).<br>**Scroll integration (the rate rule):** a catch-up loop over sim ticks: `while _tick < world.tick_count: ofs[L] = wrap(ofs[L] + d(t)·v_L(t)·DT, P_L)`. Layers and world periods P:<br>• gust 48 m;<br>• cloud 56 m;<br>• mist 32 m;<br>• fog-edge brush 4.8 m;<br>• water strokes A 6 m and B 4 m;<br>• cloud sea A 38 m and B 22 m.<br>Display offset = ofs + d·v·`FxRead.lead()`·DT, published two vec2 per vec4 (`atm_scroll_a..d`).<br>**Writes globals once per frame (≈ 40 calls):**<br>• `atm_day`, `atm_sun`, `atm_moon`, `atm_fill`;<br>• `atm_wind` (xy downwind, z base, w gust speed);<br>• `atm_scroll_a..d`, `atm_cloud`, `atm_weather` (wetness, rain, mist, first drops);<br>• `atm_front`, `atm_front_t` (WLD-03), `atm_fog_blend`, `atm_axis`;<br>• `atm_brawl`, `atm_rim`, `atm_shock_0..3`, `atm_carry_0..5`, `atm_jar_0..1`;<br>• `atm_cam_box`, `atm_grass_box`, `atm_quality`, `atm_moon_phase`.<br>**Signals:** `dusk_began`, `dawn_began`, `front_started(kind)`, `weather_changed(old, new)`, `rain_ended`.<br>**API:** `hour()`, `night()`, `wind_at(xz)`, `gust_at(xz, tau := 0)`, `visible_at(pos)`, `shock(pos, strength)`, `water_splash(pos, size)`, `puddle_at(pos)`, `add_light(id, pos, kind, owner)`, `remove_light(id)`. (`bind()` is gone: all atmosphere textures are global samplers.)<br>**Monitors** (`Performance.add_custom_monitor`): `atmos/cpu_ms`, `atmos/draws`, `grass/instances`, `life/active`, `audio/world_voices`, `lantern/uploads_per_s`. | New `src/world/atmos.gd` (`class_name Atmos`, node `World/Atmos`, created only when `World.visuals`; physics interpolation OFF). Globals are declared in `project.godot [shader_globals]`, so shaders compile in the editor and headless. Spike 4.7.2: global `sampler2D` works on gl_compatibility and Forward+, in vertex stages too, and picks up in-place `ImageTexture.update()`. | ≤ 0.06 ms/frame | P0 |
| WLD-F2 | **Shared world shader include and quality tier** | compile time | One include (sketch below) provides wind with lag and recoil, cloud shadow, asymmetric smoothed fog, memory grade, the tide, the night gate and lanterns. Terrain, trees, water, grass, props, buildings, mist and units all use it, so a gust, a cloud or the tide hits everything identically. It replaces the copies of `fog_factor()` in today's shaders.<br>**Global samplers** (packed; ≤ 7 atmosphere samplers per material):<br>• `atm_noise_tex` RGBA8 256², repeat: R gust fronts, G flicker, B brush edge, A painted cloud mask;<br>• `atm_detail_tex` RGBA8 256², repeat: R paper grain, G mist noise, B foam strokes, A leaf-gap speckle;<br>• `atm_ripple_tex` RGBA8 128², repeat, mipmapped: RG ripple normal, B time offset, A ring mask;<br>• `atm_fog_a` and `atm_fog_b` (L8 display bytes);<br>• `atm_lantern_tex` RGBA8 at 1 m: RGB = warm light / 2, A = canopy proximity (static);<br>• `atm_world_tex` RGBA8 at 1 m: R wear, G shore distance (clamp(sd, −4, 16) + 4)/20, B reveal stamp, A dew trail;<br>• `atm_height_tex` RG8: R height (h + 1.5 m)/7 m, G lowland floor height;<br>• `atm_ground_tex` RGBA8: RGB baked ground albedo, A grass density × (1 − known footprints);<br>• `atm_scar_tex` (combat CMB-32, RG8 at 0.5 m).<br>**Per material:** terrain 7 + scar; water 7 + its stroke normals; grass 6 + `terrain_corners`; trees 4; mist 5; units 2. Asserted by `test_shader_compile` (§9).<br>**Quality tier:** `global uniform int atm_quality` with uniform-coherent branches. **Low:**<br>• drops ripples (wetness stays), recoil (κ = 0), paper grain, hatching, sun breaks, canopy dapple and the cloud-sea parallax;<br>• shore and lapping use one term;<br>• the cloud sea samples the cloud mask once (High twice); no fbm anywhere.<br>**Terrain fragment order:** layers → wetness, wear, scar → `atm_memory_grade` → cloud shadow, dapple, tide, lanterns → **rings (`eco_rings`) last**, so no atmospheric term ever multiplies a ring. | `src/world/shaders/world_common.gdshaderinc`, plus `foliage.gdshaderinc` (WLD-14) and `cloth.gdshaderinc` (WLD-29), via `#include`. | ≈ 40 ALU + 5–7 samples per terrain fragment (High); ≈ 22 ALU + 4 samples (Low) | P0 |
| WLD-F3 | **Wind and weather state** | match start (schedule); every frame (evaluate) | **Schedule:** a list of (sim start time, state) pairs (§6), built at match start from hash(map name, match seed, "weather") with its own RNG and evaluated from `sim_time`. Every player, observer and replay sees the same sky.<br>**Wind direction (closed form):** d(t) = rotate(prevailing, 25°·n₁(t / 90 s)), where n₁ is a cubic-Hermite value noise of sim time over hashed knots. Its turn rate is ≤ 0.45°/s. No damping.<br>**Base strength b(t) and gust speed v_g = 4 + 4·b m/s:** per state, with 10 s smoothstep transitions. Cloud scroll speed = 0.3·v_g (1.3–1.9 m/s).<br>**Noise texture:** 256², seamless. R = gust fronts (simplex, 3 octaves, stretched 2:1 across the wind). Kept as an `Image` for the CPU mirror.<br>**CPU mirror** `gust_at(xz, tau)`: the exact shader formula (bilinear with wrap) on the published offset. | `src/world/weather.gd` (state machine + schedule) inside Atmos. `FastNoiseLite.get_seamless_image()` until the painted textures exist. | ≤ 0.02 ms/frame | P0 |
| WLD-F4 | **Lanterns: light without lights; the LightBudget** | light added or removed; nightly gating | **Lantern map:** RGBA8 at 1 m per texel (192² on the slice). RGB = warm light / 2, clamped at 2.0; sampled with a 4 × 4 ordered dither of ±1/255 against banding in the (1 − x²)² falloff.<br>• Each source splats into a float accumulation buffer kept in a `PackedFloat32Array`. Changed bytes are re-quantised in place into a `PackedByteArray` mirror, then `Image.set_data()` + `ImageTexture.update()` (147 KB; there is no sub-rect upload in 4.7.2). Changes coalesce to ≤ 4 uploads/s.<br>• Terrain, trees, props and buildings add albedo × L; units sample L at their origin (WLD-06).<br>• Gated per fragment by `atm_night_gate()` (the tide) and flickered by the noise G channel.<br>• **Honesty:** only sources the local player knows contribute: own, allied, neutral props, and enemy structures seen or remembered. **On fog-over, an enemy or neutral structure's fire splats become one dim, steady ghost splat** (#FF8A3A, r 4 m, 0.3, no flicker; economy §2.1).<br>**Carried lights:** 6 globals `atm_carry_n` (x, z, radius, intensity) for hero lanterns (WLD-06).<br>**Real lights (Forward+ only):** the **house-light pool**, 4 `OmniLight3D` (no shadows; range = pool radius × 1.1; energy 1.2) bound to the lit sources nearest the focus. Selection uses heroes' buckets (§2.4 there: 2 m buckets at 4 Hz with 2 m hysteresis, on-screen first) with 300 ms energy crossfades.<br>**LightBudget (shared):** ≤ 12 `OmniLight3D` on screen (Compatibility: 8 in total and ≤ 8 whose range touches any one terrain chunk; the rest fall back to their ground-glow sprites). Priority: spell > impact (combat FND-3) > fire (BLD-15) > house light. The lowest class gives up lights first. | New `src/world/lanterns.gd` and `src/fx/light_budget.gd`. `impact_lights.gd` and `building_fx.gd` are clients. | ≈ 0.1 ms per change; at runtime 1 sample per fragment | P0 map / P1 pool + budget |
| WLD-F5 | **Atmosphere governor: presets, zoom, speed, auto-degrade** | settings change; every frame | **Presets** Low, Medium, High (§9) and juice level 0.<br>**`reduce_motion`:** no tide band (staggered ignition), no grass sheen, no shock rings, firefly waves off, cloud drift ×0.5, no storm flashes.<br>**`weather_visuals`:** Full; Light (no streaks, mist ×0.5); Off (always Clear).<br>**Brawl awareness:** air, fireflies and critters thin inside FND-3's brawl clusters.<br>**Fog gate:** `visible_at(pos)` reads the local player's `Fog` grid; every CPU-side spawn calls it.<br>**Zoom awareness:** wrap boxes are centred on the centroid of the camera's ground footprint and sized from it (the footprint is ≈ 45 × 30 m at 28 m and ≈ 2.7× that area at 46 m). Visible counts = base × clamp(footprint area / area at 28 m, 1, 1.6), and α fades over each box's outer 3 m.<br>**Nearest-to-focus selections** (flames, house lights, carried lights, smoke columns, emitters, moths, tramplers): heroes' bucket rule, with 300 ms fades when a source gains or loses its slot. No per-frame sort.<br>**Game speed ≥ 4×** (replays, fast-forward):<br>• the tide becomes staggered ignition; stingers, sweeteners and whooshes are skipped;<br>• critters hold home poses and flights are skipped (sim-triggered roost flushes become a 0.5 s fade);<br>• fireflies glow steadily at 0.5; snore rings are capped at 1 per 0.5 s real time per camp;<br>• wear and dew polls stay on sim ticks, so replays reproduce identical paths.<br>**Auto-degrade:** when the 2 s mean frame time > 18.5 ms for 3 s, step atmosphere-only items down one notch (grass spacing ×1.25, air ×0.5, rain ×0.5, mist upper layer off, tramplers 24 → 12). Recover after 10 s under 15 ms; never below Low; logged once. Off in tests.<br>**Renderer:** detected at start (`RenderingServer.get_current_rendering_method()`). Compatibility forces Low. | In `atmos.gd`. New `Settings` keys: `atmo_quality`, `weather_visuals`, `reduce_motion`, `world_memory`. | negligible | P0 |
| WLD-F6 | **Biome data and derived world maps** | map load | **`data/biomes.json`:** palette (art doc §7.2), grading offsets, prevailing wind, weather weights, critter table, ambience set, flower palette, grass colours and density, air kinds.<br>**Derived at load** (≤ 150 ms on the slice):<br>• the shore distance field (BFS over 1 m cells, ≈ 40 ms) and water bodies (flood fill; each body's span decides pond or lake mode, WLD-18);<br>• lowland floor height (6 m min-filter of terrain height, blurred 3 m);<br>• canopy proximity (1 under canopies, 0 at 4 m out);<br>• baked ground albedo and grass density (grass layers, minus paved, rock, water, tree cells and the cliff band);<br>• CPU lists: perches, shore points, the ambience zone grid (8 m cells), lit sources, landmark emitters. | `src/world/world_maps.gd`; `Defs.biome(id)`. | load only | P0 |

**WLD-F2 sketch (load-bearing; colours are in sRGB space before the final `pow(2.2)`, as `terrain.gdshader` does today):**

```glsl
// src/world/shaders/world_common.gdshaderinc   (revision 2)
global uniform float fx_time;        // Vfx.now: cosmetic oscillators, always × a CONSTANT rate
global uniform float sim_time;       // heroes HVF-7: (tick + lead) × DT
global uniform vec4 atm_day;         // x daylight, y night, z golden, w blue hour
global uniform vec4 atm_wind;        // xy downwind unit vector (closed form), z base 0..1, w current gust speed m/s
global uniform vec4 atm_scroll_a;    // xy gust offset (mod 48 m), zw cloud offset (mod 56 m): integrated on the sim clock
global uniform vec4 atm_scroll_b;    // xy mist offset (mod 32 m), zw fog-edge brush offset (mod 4.8 m)
global uniform vec4 atm_cloud;       // x scale m, y coverage, z strength, w sun-break gain
global uniform vec4 atm_fog_blend;   // x upload sim_time, y period s, z 1 = B is current
global uniform vec4 atm_front;       // x front position s (m along sun_axis), y kind (+1 dusk, -1 dawn, 0 idle), z side fade, w idle gate
global uniform vec4 atm_axis;        // xy sun_axis (sunrise -> sunset), zw map size m
global uniform int atm_quality;      // 0 Low, 1 Medium, 2 High

global uniform sampler2D atm_noise_tex : filter_linear_mipmap, repeat_enable;  // R gust, G flicker, B brush edge, A cloud mask
global uniform sampler2D atm_fog_a : filter_linear;                           // display bytes: 0 unexplored, .5 fogged, 1 visible
global uniform sampler2D atm_fog_b : filter_linear;
global uniform sampler2D atm_lantern_tex : filter_linear;                     // RGB warm light / 2, A canopy proximity

float atm_gust(vec2 xz) {
	return smoothstep(0.55, 0.85, texture(atm_noise_tex, (xz - atm_scroll_a.xy) / 48.0).r);
}
// The gust that was here tau seconds ago is now tau·v downwind. Current velocity × constant tau: bounded error, no growth.
float atm_gust_lag(vec2 xz, float tau) { return atm_gust(xz + atm_wind.xy * atm_wind.w * tau); }
// Lag + recoil (WLD-10): r = g(t - tau) + kappa·[g(t - tau) - g(t - tau - 0.4 s)]
float atm_drive(vec2 xz, float tau, float kappa) {
	float a = atm_gust_lag(xz, tau);
	return atm_quality == 0 ? a : a + kappa * (a - atm_gust_lag(xz, tau + 0.4));
}
float atm_wind_at(vec2 xz, float tau, float kappa) {
	float breath = 0.75 + 0.25 * sin(fx_time * 0.7 + dot(xz, vec2(0.05, 0.03)));   // fixed 0.7 rad/s
	return clamp(atm_wind.z * breath + 0.6 * atm_drive(xz, tau, kappa), 0.0, 1.2);
}
float atm_cloud_shadow(vec2 xz) {
	float n = texture(atm_noise_tex, (xz - atm_scroll_a.zw) / atm_cloud.x).a;
	float c = atm_cloud.y;
	return smoothstep(1.0 - c - 0.12, 1.0 - c + 0.12, n) * atm_cloud.z;
}
float atm_fog(vec2 xz) {                       // WLD-25: concealment lands at once, reveal eases
	vec2 uv = xz / atm_axis.zw;
	float a = texture(atm_fog_a, uv).r, b = texture(atm_fog_b, uv).r;
	float cur = atm_fog_blend.z > 0.5 ? b : a, prev = atm_fog_blend.z > 0.5 ? a : b;
	float k = smoothstep(0.0, 1.0, (sim_time - atm_fog_blend.x) / atm_fog_blend.y);
	return min(cur, mix(prev, cur, k));
}
float atm_front_u(vec2 xz) { return atm_front.x - dot(xz, atm_axis.xy); }   // > 0: the front has passed here
float atm_night_gate(vec2 xz) {                // 6 m = 0.4 s at 15 m/s
	if (atm_front.y == 0.0) { return atm_front.w; }
	float passed = smoothstep(-3.0, 3.0, atm_front_u(xz));
	return atm_front.y > 0.0 ? passed : 1.0 - passed;
}
vec3 atm_tide(vec3 col, vec2 xz) {             // WLD-03: 4 m lead, 6 m core, 4 m tail, 30 m trailing side
	if (atm_front.y == 0.0) { return col; }
	float u = atm_front_u(xz);
	float ink = smoothstep(-7.0, -3.0, u) - smoothstep(3.0, 7.0, u);
	float side = smoothstep(3.0, 33.0, u) * atm_front.z;
	if (atm_front.y > 0.0) {                   // dusk: #4C5698 multiply at 22 %, night side -10 % value
		col *= mix(vec3(1.0), vec3(0.298, 0.337, 0.596), 0.22 * ink);
		return col * (1.0 - 0.10 * side);
	}
	col = 1.0 - (1.0 - col) * (1.0 - vec3(1.0, 0.824, 0.627) * 0.18 * ink);   // dawn: #FFD2A0 screen at 18 %
	return col * (1.0 + 0.06 * side);
}
vec3 atm_lantern(vec2 xz, vec2 frag_px) {
	vec3 l = texture(atm_lantern_tex, xz / atm_axis.zw).rgb * 2.0 + (atm_bayer4(frag_px) - 0.5) * (2.0 / 255.0);
	float flick = 0.88 + 0.12 * texture(atm_noise_tex, xz * 0.04 + fract(vec2(fx_time * 1.7, fx_time * 1.1))).g;
	return max(l, vec3(0.0)) * flick * atm_night_gate(xz);
}
vec3 atm_memory_grade(vec3 col, float f, float edge_noise, float paper) {   // WLD-25..27
	float v = f + (edge_noise - 0.5) * 0.18;
	float explored = smoothstep(0.14, 0.34, v), visible = smoothstep(0.64, 0.82, v);
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 fogged = mix(vec3(lum), col, 0.4) * mix(0.55, 0.45, atm_day.y) * mix(vec3(1.0), vec3(0.616, 0.702, 0.839), 0.15)
		* (atm_quality == 0 ? 1.0 : 1.0 + (paper - 0.5) * 0.12);           // #9DB3D6 at 15 %, paper grain ±6 %
	vec3 seen = mix(fogged, col, visible) * (1.0 - 0.08 * (1.0 - smoothstep(0.82, 0.98, v)) * visible);
	return mix(vec3(0.039, 0.047, 0.071), seen, explored);   // #0A0C12; WLD-26 adds the cloud sea here
}
```

The CPU side must match exactly, because audio (WLD-10), smoke and seeds read it:

```gdscript
# atmos.gd: scroll integration on the sim clock. Never fx_time × a changing rate.
func _integrate_scroll() -> void:
	while _tick < world.tick_count:
		var t := _tick * World.DT
		var d := weather.wind_dir(t)                    # closed form of sim time
		var vg := weather.gust_speed(t)
		_ofs[GUST] = _wrap(_ofs[GUST] + d * vg * World.DT, 48.0)
		_ofs[CLOUD] = _wrap(_ofs[CLOUD] + d * 0.3 * vg * World.DT, 56.0)
		# ... mist 32 m, edge 4.8 m, water 6 m / 4 m, sea 38 m / 22 m
		_tick += 1

# CPU mirror of atm_gust_lag(). Change both or neither.
func gust_at(xz: Vector2, tau := 0.0) -> float:
	var p := xz + wind_dir * gust_speed * tau
	return smoothstep(0.55, 0.85, _bilinear_wrap_r(_noise_img, (p - _display_ofs[GUST]) / 48.0))
```

---

## 4. Feature table

### 4.1 Day and night

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-01 | **Sun and moon: two lights, one shadow owner** | every frame (`hour`) | **Sun (light energy from the §5 keys, 05:20–18:40):**<br>• elevation e = max(22°, 24° + 40°·sin(π(h − 6)/12)): 64° at noon. The 22° floor keeps long shadows ≤ 2.5× unit height, so they never sweep across neighbouring rings (the bible's 12–20° dusk sun is amended, §12);<br>• yaw relative to the camera yaw y = −55° + 110°·(h − 6)/12. Shadows fall up-right in the morning, straight up-screen at noon and up-left in the evening: always within 55° of screen-up, never toward the camera. At 08:00 (match start) e = 44°, y = −37°: the art doc's lower-left key.<br>**Moon (17:40–06:20):** e = 42° + 10°·sin(π·n), y = −40° + 80°·n, where n = fraction of the moon's arc.<br>**No twilight dip:** the two lights overlap (17:40–18:40 and 05:20–06:20) and **only the shadow owner swaps**, at 18:15 and 05:40, when both shadow opacities are 0. The illuminance proxy never falls below 95% of midnight (§5.1).<br>**Shadows:** max distance 60 m, PSSM 2 splits. `light_angular_distance` (High only): sun 1.2° at noon → 2.5° at e = 24°, moon 1.5°. At 1× the direction moves ≤ 0.46°/s; shadow-edge swimming from the rotating sun is checked in `bench_atmos` (§9) before any PCSS is added. | `src/world/day_night.gd` becomes the director, with a second `DirectionalLight3D` "Moon" (interpolation OFF). It keeps `hour_at`, `is_day` and `fixed_hour`. It replaces today's −150°..+90° azimuth (which lets shadows fall toward the camera) and the FILMIC default. | ≈ 6 µs | P0 |
| WLD-02 | **Time-of-day grading, the golden-hour telegraph, nights that differ ★** | every frame (`hour`, weather) | The keys in §5 are interpolated with smoothstep between neighbours (wrapping at 24 h).<br>**Outputs:** sun and moon colour and energy; ambient colour and energy; depth-fog colour (begin 32 m, end 90 m); `adjustment_saturation` and `adjustment_contrast`; glow; `atm_day`, `atm_fill`, cloud strength, water colours, emissive gates.<br>**Golden-hour telegraph: 16:30–18:00** (30 s at 1×, matching HUD-07's rim): the key warms (#FFC98A, saturation 1.12) and shadows stretch. It is the "night is coming" read, 30 s before most camps fall asleep.<br>**Pre-dawn telegraph:** 04:30–05:40, a violet lift (ambient #45508A → #6A6496).<br>**Per-night variation (§5.4):** the sunset key depends on the day's weather, and the moon phase advances every night.<br>**Weather multipliers:**<br>• Overcast: energy ×0.75, saturation ×0.92, shadow α ×0.55.<br>• Drizzle and Rain: energy ×0.65, ambient ×1.08, saturation ×0.9, fog begin 26 m.<br>• Mist: fog begin 22 m, fog colour toward #DDE4EA.<br>• Distant storm: contrast +0.04, sun breaks ×1.8 (WLD-36).<br>**Biome offsets** from `biomes.json`. | Keys are a Resource (`data/time_of_day/greenvale.tres`) evaluated in `day_night.gd` and written to the `Environment` (spike 4.7.2: `adjustment_saturation` behaves the same on Compatibility; the in-material fallback is deleted). The 3D LUT stays static per biome. | ≈ 15 µs | P0 / P1 per-night variation |
| WLD-03 | **Nightfall tide and first light ★** | the front locks and sweeps around T0 (18:00:00 dusk, 06:00:00 dawn) | **A front you can watch:** a straight edge perpendicular to `sun_axis`, moving sunrise → sunset at a **fixed 15 m/s** on every map. It crosses the default view (≈ 41 m) in ≈ 2.7 s, matching WC3's ≈ 3 s light change and the 3.2 s sight ease; the 192 m slice takes ≈ 13 s end to end.<br>**Anchored to the player's view (sim time):** with s = dot(xz, sun_axis), the front tracks s_f = s_focus + v·(t − T0) while it is still off the map, clamped to s_min − 4 m (no visible motion while it waits). It **locks** when it reaches the east edge, then advances at v. If the camera does not move after the lock, **the core passes the camera focus exactly at T0**. Pause and game speed follow because t is `sim_time`.<br>**Dusk profile** (u = metres behind the core centre):<br>• 4 m soft lead;<br>• 6 m core: multiply #4C5698 at 22%, on terrain, water, trees and props, never on units, rings or bars;<br>• 30 m trailing night side: value −10% toward the night key, faded out over 18:15–18:30 as the global grade catches up.<br>Behind the core, lantern pools gate on (6 m = 0.4 s at each point), and each light source **ignites as the core passes it** (+ hashed 0–250 ms, WLD-05).<br>**Dawn:** mirrored, with a warm first-light core (#FFD2A0 screen at 18%) with a +6% value day side. Flames die as it passes: 250 ms shrink plus one smoke puff, for the 8 sources nearest the focus.<br>**Honesty:** the tide moves light, never vision. Fog and sight belong to the sim (WLD-25). On screen, the sweep falls within ±1.4 s of T0 at default zoom (±2.3 s at max zoom), inside the sim's 3.2 s sight ease.<br>**Sound:** none of its own; the stinger carries it (WLD-04, §5.3).<br>**Reduce motion, juice 0, speed ≥ 4×:** no band; ignitions at T0 + hashed 0–2,000 ms. | `atm_front` = (s_f, kind, side fade, idle gate) and `atm_front_t` = (s_entry, t_entry, v, T0), computed in Atmos from `sim_time`. `atm_tide()` and `atm_night_gate()` in the include. The minimap draws the same s_f(t) (WLD-34). | free (2 uniforms, ≈ 8 ALU) | P1 |
| WLD-04 | **Dusk and dawn stingers on one downbeat** | scheduled from `sim_time` so the downbeat lands on T0 | **Dusk, `st_dusk`** (bible §9.7, 5 s): a lone curlew call, crickets fading in, a soft low bronze hum that sinks away. The **hum onset is the downbeat**, 1.8 s into the file, so the stream starts at T0 − 1.8 s × game speed.<br>**Dawn, `st_dawn`** (5 s): a blackbird begins, an airy rising shimmer, **one low bronze bowl tone as the downbeat**, 2.0 s into the file.<br>**The downbeat lands with** the tide core at the focus, the HUD-07 clock clunk's tick, MUS-01's night-filter centre and the bed crossfade's midpoint. Everything else is staggered after it (§5.3), so nothing turns to mush on one frame.<br>**Not a gameplay alert:** no horns (the kingdom's Levy Horn, ECO-21, is a two-note low wooden horn), no gong strikes or rolls (the clans alarm), no bells. Acceptance: a 3-listener A/B against the Levy Horn, the gong roll and the CRP-04 stingers, with no confusions.<br>**Mix:** 2D on the Ambience bus, −10 dBFS peak, +6 dB over the beds, ducked by Voice like the beds; −4 dB when music is playing. Skipped at game speed ≥ 4×. The players are PAUSABLE.<br>**Beds:** day and night loops crossfade (equal power) over 8 s centred on T0.<br>**IP and convention:** no wolf howl at dusk, no rooster at dawn, **no owl as a night signature** (bible §9.7). | `ambience.gd` (WLD-32) schedules them. `AudioStreamPlayer` (non-positional). Assets `assets/audio/ambience/st_dusk.ogg` and `st_dawn.ogg`. | 1 voice for 5 s | P0 |
| WLD-05 | **Lights of dusk: lamps, torches, fires, windows** | ignition as the tide core passes (WLD-03); out at first light | **Slice sources** (map props and def hints):<br>• torch posts (2.2 m) and lamp posts (2.6 m) at the basin ramps and the inn;<br>• the Weighstall lantern, the Muddy Lantern's sign lantern, the Gold Seams' two hook lanterns;<br>• the Sootcoat clamp fires (campfires), windows (`fx.windows`), def `fx.lamps` (hall gate torches, the tower brazier).<br>**Strike (ignite):**<br>• 3 SPARK (#FFD27A HDR 2.2, up 1.2 m/s, life 300 ms), CPU-spawned only for the 8 sources nearest the focus (buckets);<br>• emission 0 → 1.0 (60 ms) → 0.2 (40 ms) → 1.2 (80 ms) → 1.0 (200 ms `out_quad`);<br>• flame sprites grow 0 → full over 300 ms `out_back(1.6)`;<br>• a "fwump" (World −20 dB) for the 2 sources nearest the focus, ≥ 120 ms apart.<br>**Flames** (StreamFx `fire`):<br>• torch: 6 sprites, 0.18 → 0.06 m, life 380–520 ms, rise 1.0 m/s;<br>• brazier: 10 sprites at 0.30 m; campfire: 14 sprites + 4 embers;<br>• colours: core #FFE08A HDR 2.5 → mid #FF8A2A HDR 1.8 → edge #C2341A;<br>• flames lean downwind and flicker 1.5× harder when the local g > 0.6.<br>**Flicker** (fixed rates; n = hashed noise): torch 0.86 + 0.10·n(7.3t) + 0.04·n(17t); lamp (glass) 0.95 + 0.05·n(3t); brazier 0.80 + 0.20·n(9t).<br>**Pools** (radius / intensity / colour): torch 4.5 m / 0.9 / #FFB060; brazier 6 m / 1.1 / #FFA050; campfire 7 m / 1.2 / #FF9A48; lamp 5 m / 0.8 / #FFC680; window 2.5 m / 0.4 / #FFB86B.<br>**By day:** everything is unlit except clamp fires (60% sprites, no pool).<br>**Rain:** torches sputter (emission dips to 0.7 for 80–160 ms at 1–2 Hz, hashed); clamp fires steam 2 puffs/s (#E8F0F5 α 0.25). | **Props are MultiMesh doodads, so per-instance uniforms cannot work** (a MultiMeshInstance3D's instance uniform applies to every instance; spike). `prop.gdshader` computes `lit` in closed form, `atm_ignite(origin)`: t_pass = t_entry + (dot(origin.xz, sun_axis) − s_entry)/v; lit = strike envelope(sim_time − t_pass − 0.25 s·hash(origin)); sputter = hashed noise × rain. **Clamp-fire banking** uses `INSTANCE_CUSTOM.r` (0..1, safe at 16-bit), written on sleep changes.<br>**Buildings** (one MeshInstance3D each) take `lit` from economy's `anim_b.z` through `StructureUniforms`. Own windows follow BLD-19 when juice level 2 runs it.<br>Flames are StreamFx streams (economy §2.3). | sprites only for the ≤ 24 lit sources nearest the focus (buckets); the rest emissive-only; pools free | P0 emissive + pools / P1 strike, sputter |
| WLD-06 | **Night readability: unit fill, team lift, moon rim, the hero lantern ★** | `atm_fill`, `atm_day.y` | **Unit fill (`night_lift`):** unit.gdshader adds EMISSION += ALBEDO × #A9B8E8 × fill × (0.35 + 0.65·max(N·V, 0)), with fill = 0.65 × (1 − daylight) (§5.2). Buildings take 0.5×. This is a light "from behind the camera" without a light: identical on every renderer and free of light cost. Tune range 0.5–0.8 by the §9 luma test. (Alternative: an unshadowed `DirectionalLight3D` with `light_cull_mask` = units layer; rejected because Compatibility support is unverified.)<br>**Team lift:** + team colour × 0.18 × night on team-mask areas (under combat's 0.6 unit-emission cap).<br>**Moon rim:** `rim_color` lerps from team colour × 0.6 by day to #8EA6FF × 0.45 at night (× the moon-phase factor, §5.4); `rim_power` 3 → 2.5.<br>**Lantern response:** units sample the lantern map at their origin (vertex stage) and add albedo × L × 0.5 as emission, clamped ≤ 0.6. A soldier walking past a brazier is lit warm.<br>**The hero lantern ★ (diegetic, replaces the sourceless pool):** a 0.12 m lantern prop (≥ 6 px) at def `fx.lamp` (belt or staff), struck alight at 18:30 + hashed 0–600 ms with WLD-05's strike curve and snuffed at 05:30 (250 ms shrink + a puff). It swings on an FND-6 pendulum (ω 7 rad/s, ζ 0.15, ±25°) driven by hero acceleration. **The carried light's centre follows the lantern**, so the pool (r 3.2 m, intensity 0.5) sways ≈ ±0.15 m as the hero walks and stops. Tint and flicker per hero from `fx.lamp`: default #FFE2B0 at 3 Hz ±5% (glass); **Firewright #FFB46B at 7 Hz ±10%** `vnoise`. Visible heroes only; up to 6 carried lights (buckets). | `unit.gdshader` (combat) includes `world_common`; placeholders flag team-band vertices in vertex alpha. Lantern prop: one 24-instance MultiMesh (interpolation OFF, positioned from UnitPosTex + the pendulum). Carried lights = the 6 `atm_carry_n` globals. | ≈ 6 ALU per unit fragment; 6 distance tests per terrain fragment | P0 fill + lift + rim / P1 lantern response + hero lantern |
| WLD-07 | **Sleeping camps: the sleeping body, by family ★** | `creep_sleep_changed(u, asleep, reason)` per creep; schedules `night` / `day` / `never` | **Every visual starts on the creep's own signal**, which already carries the sim's 0–6 s stagger. No extra hash. The full per-family table is **4.1a** below.<br>**Sleep glyph (one shared atlas cell; heroes STS-06, economy ECO-12 and UI SEL-02 reuse it):** a **closed-eye glyph, never letters** (neutrals §1.5, bible §8). One per sleeping camp, on the camp leader's head slot (heroes §2.6 head-glyph anchor, above the health bar), 0.36 m, ≥ 10 px, ivory #EDE6D2 with a 2 px ink outline #2A1A0E. Its α breathes 0.80 ↔ 1.0 with the camp's exhale (a value change, no scale). It fades in over 300 ms when the leader sleeps.<br>**Snore rings carry the tier ★:** one exhale per camp every 2.4 s, from a round-robin sleeper:<br>• **1, 2 or 3 soft rings per exhale** by the camp's total level band (1–9 / 10–19 / 20+, neutrals §1.2), 160 ms apart;<br>• each ring grows 0.12 → 0.30 m (≥ 6 px at birth), rises 0.6 m over 1.8 s `out_sine` and drifts 0.3·w m downwind; α 0 → 0.7 (200 ms) → 0 (last 600 ms);<br>• fill #EDE6D2 α 0.35, 2 px outline in the band hex: green #5FBF4A, amber #E8A93A, red #D9483B.<br>Health bars draw above them (render priority 100), so a ring never hides a bar.<br>**Wake:** a woken signal (`damage`, `build`, `trade`, `spell`) makes the glyph crumble into 3 chalk dashes over 120 ms, called by CRP-02, which owns the startle, the "‼" and the 0–90 ms body stagger. A scheduled wake (`dawn` for night sleepers, `dusk` for day sleepers) fades the glyph over 400 ms and plays the family's rise (4.1a).<br>**Facing:** the sim faces sleepers toward the fire or camp centre (hook §2). Without that hook, the visual turn clamps to CMB-05's ±20° body offset.<br>**Minimap:** while a visible camp sleeps, its shield pip drops to 60% value with a 4 px closed-eye overlay (the UI draws pips; WLD-34 supplies the state).<br>**Fog:** glyphs, rings and sleep sounds only for camps visible to the local player. | Composer layer `sleep` in UnitView (FND-1). New `src/world/camp_fx.gd`: the glyph is an FxSprites head-layer kind, rings an FxSprites soft ring kind, loops via `Audio.loop_3d` in the world pool (WLD-33). Glyph and ring sizes use the legibility clamp. | ≤ 3 sprites per camp per 2.4 s; ≤ 2 loops | P0 pose, glyph, rings, minimap state / P1 per-family idles, sounds, clamp-fire banking |
| WLD-08 | **Night air: fireflies that fall into step, a firefly wake, moths at the lamps ★** | 19:00–05:00; Clear, Breezy or Overcast | **Ambient fireflies (they yield to the Firefly Jar):**<br>• core 0.04 m (≥ 2 px) #E8F07A at **HDR 1.3**; halo ≤ 0.15 m #B8E05A α 0.3, additive; hover 0.4–1.6 m;<br>• mask: shore distance ≤ 6 m around the ponds and the spring dell, plus meadow edges (grass density ≥ 0.5) within 15 m of water. Density 0.06/m² of mask: ≈ 18 per pond and ≈ 36 in the dell, ≤ 64 on screen;<br>• drift: a Lissajous path around a home point, (0.6 sin(0.37t + a), 0.25 sin(0.53t + b), 0.6 sin(0.29t + c)) m;<br>• blink: a 280 ms cosine pulse at period P = 2.2 s for every firefly; randomness is in phase and in blink amplitude (±25%), never in period.<br>**Synchrony (drift-free):** φ = Ωt + φᵢ + s(h)·wrap_π(ψᵢ − φᵢ), where:<br>• Ω = 2π / 2.2 s;<br>• ψᵢ = −k·dot(home, sun_axis), k = Ω / 20 m/s, a constant per match;<br>• s ramps from 0 at 19:00 to 0.85 at 01:00 (smoothstep).<br>Because the phase difference is wrapped, the ramp changes the blink rate by < 1%. Early in the night they blink at random; by midnight the blinks roll across the field in slow waves.<br>**Disturbance:** inside a brawl cluster, or within 12 m of a shock < 6 s old, they scatter 1.5 m outward, desync (s → 0) and fade to 40% over 600 ms, recovering over 8 s.<br>**Firefly wake ★:** within 1.5 m of a trample capsule (WLD-16), fireflies rise 0.6 m and brighten 1.5× along the capsule's 0.6 s tail, so an army marching through a meadow at night kicks up a wake of light.<br>**The Firefly Jar (heroes ITM-03):** the `AIR_ANCHORED` variant (home = instance origin, no wrap) keeps #D8FF6A at HDR 2.0 plus a 0.3 m owner-colour halo and the converge-then-wander motion. **Ambient fireflies within 12 m of an active jar disc fade out over 600 ms** (`atm_jar_0..1`). Tested ΔE ≥ 20 (§9).<br>**Moths at lit sources:** 2–3 moths around each of the 8 lit sources nearest the focus. Each is 0.05 m (≥ 2 px), #E8DCC0 α 0.8, soft (not additive) and lit by the pool (value × (0.6 + 0.6·L)). Closed-form orbits: r 0.3–0.5 m, period 1.1–1.7 s, vertical bob 0.15 m at 2.3 Hz, value flicker ±15% at 7 Hz (no wing flip, which aliases at 30 fps). Night only.<br>Off in rain, in fog (stillness), at juice 0 and at speed ≥ 4× (steady glow). | `src/world/air_fx.gd` + `air.gdshader`: **one** static MultiMesh shared with WLD-13's seeds (≤ 128 fireflies + 96 seeds + 24 moths; kind per instance range). Homes come from `atm_cam_box` + fract(seed) × box size, so the field is fixed in world space with zero CPU per frame. Trample arrays and `moth_src[8]` are material uniforms written by Atmos. | 1 draw, ≤ 248 quads | P1 / P2 moths |

**Table 4.1a: the sleeping body by family** (slice camps from neutrals §1.5 and §3.6)

| Family | Schedule (slice camps) | Settle (on the creep's signal) | While asleep | Sound (camp-state slot, WLD-33) | Rings rise from | Scheduled rise |
|---|---|---|---|---|---|---|
| **Sootcoats** | `night`: Charcoal Clamp ×2, Collier's Hut ×2, Smugglers' Den | Sit down facing the banked clamp fire: 900 ms `in_out_sine` (pose `sit`; placeholders sy 0.72, pitch −6°) | **Chin nod** every 9–15 s (hashed per creep): head pitch 0 → 18° over 2.5 s `in_sine`, then a jerk back over 90 ms `out_back(2.0)` (placeholders: body pitch 6°). Hood smoke from CRP-01. The clamp fire banks: sprites ×0.4, pool ×0.5 (`INSTANCE_CUSTOM.r` = 0.4). | `cv_sootcoat_sleep` (bible §9.8), one loop per camp, World −22 dB | the hood | Stand up (700 ms `out_cubic`), stretch (sy 1.06 for 600 ms), one cough puff (SOOT, 0.15 → 0.4 m) |
| **Tattiebogles** | `night` (override): Turnip Patch ×2; `day`: Crow Field (settles at dawn, rises at dusk) | **`slump`** on their poles in 3 held poses at 12 Hz (250 ms, no in-betweens): body pitch 14°, head roll 20°, arms dropped. CRP-01's crows land on the heads. | **No breathing.** Posed on twos; only coat cloth moves (WLD-29). A faint pole creak (−26 dB) when the local g > 0.6, ≤ 1 per 5 s per camp. | the creak above; awake by day the camp plays straw rustle and crows | the perched crow, which dozes too (head tucked) | Rise in the same 3 held poses reversed while CRP-01's crows lift off |
| **Cairnwakes** | `never`: Drystone Fold ×2, Standing Ring | — | — (CRP-01's lichen glow at night) | the Ring's `lp_standing_ring` hum; Folds a quieter gravel shift (WLD-43, 47) | — | — |

### 4.2 Sky on the ground, and weather

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-09 | **Cloud shadows and sun breaks** | always; strength from key and weather | **Mask:** the painted cloud mask (noise A) at a world scale of 56 m, scrolled by the integrated cloud offset (1.3–1.9 m/s).<br>**Coverage c:** Clear 0.25, Breezy 0.35, Overcast 0.70, Drizzle 0.80, Rain 0.85, Mist 0.45, Distant storm 0.75.<br>**Shadow** = smoothstep(1 − c − 0.12, 1 − c + 0.12, n) × strength (§5: 0.32 at noon, 0.12 at night). It multiplies direct light only: ground and props × (1 − shadow); units × (1 − 0.6·shadow).<br>**Sun breaks:** when c > 0.6, gaps where n < 0.25 get +10% value tinted #FFF0D0, so warm patches roam across an overcast map (High and Medium).<br>**Fog:** strength ×0.3 in fogged areas (WLD-27). The minimap uses the same function at 6% (WLD-34); HUD-07 samples it at the focus. | `atm_cloud_shadow()` in the include. **Preferred:** multiply directional `DIFFUSE_LIGHT` inside the shared painterly `light()` through a fragment-written varying. **Fallback:** ALBEDO × (1 − shadow × key_share), key_share = key / (key + ambient) from the director (≈ 0.65 by day). The spike decides (§11). | 1 sample per fragment | P0 |
| WLD-10 | **One wind with inertia: fronts you can see and hear ★** | always | **Field:** w = b·(0.75 + 0.25 sin(0.7t + xz·(0.05, 0.03))) + 0.6·r, with g = smoothstep(0.55, 0.85, noise R at (xz − ofs_gust)/48 m) and v_g = 4 + 4·b m/s.<br>**Base b by weather state** (§6): Clear 0.25, Breezy 0.55, Overcast 0.35, Drizzle 0.40, Rain 0.50, Mist 0.10, Distant storm 0.60.<br>**Lag and recoil per layer:** r = g(t − τ) + κ·[g(t − τ) − g(t − τ − Δ)], Δ = 0.4 s, where g(t − τ) is sampled τ·v_g downwind (include sketch).<br>• τ: grass 0, cloth 0.05 s, bushes and reeds 0.12 s, canopy 0.30 s, trunk 0.55 s;<br>• κ: grass 0.2, cloth 0.15, trees 0.35;<br>• smoke keeps integrating the wind over its age (WLD-28).<br>A passing front reads as **bend, spring past rest, settle**, with trees visibly trailing the grass by a third of a second. Low quality drops the recoil term.<br>**What reads:**<br>1. grass bends 8° + 22°·w downwind, tips lightening +12% toward sheen #D8E2A0, so a pale band rolls across the meadow;<br>2. trees follow (WLD-14), then cloth (WLD-29), then smoke (WLD-28);<br>3. on ponds, cat's paws race across the water (WLD-18).<br>**Heard:** Atmos samples g at the focus with the CPU mirror. On a rising edge whose peak exceeds 0.75, at least 12 s after the last one, a gust "whoosh" 3D source starts 10 m upwind of the focus and travels downwind at v_g for 1.8 s (World −18 dB; 4 no-repeat variants at ±1.5 semitones). Near forest, the leaf layer gains +6 dB × g. | Noise texture + `atm_wind` + `atm_scroll_a`; `foliage.gdshaderinc` per layer; CPU mirror `Atmos.gust_at(xz, tau)`. The whoosh is one pooled `AudioStreamPlayer3D` under World/Atmos (interpolation OFF), moved in `_process`. | GPU: 2 gust samples per layer; CPU 4 samples per frame | P0 field, lag, grass, trees, cloth / P1 recoil, sheen, whoosh |
| WLD-11 | **Drizzle and rain: first drops, a whisper, an ending** | weather Drizzle or Rain | **Onset:**<br>• **first drops** (8 s, as cloud cover passes 0.7): dark 0.08 m spots (albedo ×0.8) appear on dirt and road layers, hashed in the ripple texture's cells, ≈ 1 per m² every 4 s; sparse large rings on water (1 cell in 4, ×2 size);<br>• then streaks ramp in over 15 s (`in_quad`).<br>**Streaks** (camera-local box from the footprint, 18 m tall; one MultiMesh, two fixed-speed sets crossfaded by count and α):<br>• drizzle: 3 m/s, 0.12 m streaks, #C8D4E0 α 0.10; rain: 6 m/s, 0.35 m, α 0.16;<br>• count (High / Low): drizzle 450 / 220, rain 900 / 400 (rain also keeps 50% of the drizzle set as fine drops);<br>• slant dx = 0.35·w × fall height; velocity-aligned billboards **widened in clip space to 1.25 px**, with α × (true width / drawn width).<br>**Ground rings:** one sample of the mipmapped ripple texture (RG normal, B time offset, A mask) on terrain and water: no procedural cells, no aliasing. A ring every 1.4 s (drizzle) or 0.7 s (rain) per cell; water rings 1.5×.<br>**Wetness** rises over 40 s and dries over 90 s. Terrain: albedo ×0.82, saturation +6%, roughness 0.92 → 0.40, specular 0.25 → 0.45 (a painted sheen). Trees and roofs ×0.9.<br>**Puddles (P2):** where low-frequency noise > 0.62 **and** (wear > 0.25 or dirt): albedo ×0.6, roughness 0.15, rings ×2. They grow with wetness. **Puddles collect on trodden paths.** Units crossing a puddle (`Atmos.puddle_at`, the CPU mirror) splash (a WLD-20 ring + 3 droplets) and leave **muddy prints** (2 per stride, cutout ground prints #4A3A2A α 0.5, fading over 6 s).<br>**Ending:** streaks fade over 6 s (`out_quad`). Eaves drip for 30 s: 1 drop per 1.2 s per roof corner (`fx.eaves`, default footprint corners at 0.75 × def height), ≤ 24 alive. **After rain:** by day, a 3 s burst of `swt_birds` (3 layered phrases); steam curls rise from wet roofs where sun breaks or clear sky meet wetness > 0.3 (1 per 1.5 s per roof, #E8F0F5 α 0.2, 0.3 → 0.9 m, rise 0.4 m/s, life 2.4 s, ≤ 12 roofs nearest the focus).<br>**Knock-on effects:** wet cloth hangs heavy (WLD-29), torches sputter (WLD-05), fireflies off, hares crouch, geese swim and preen (4.5a).<br>**Sound:** drizzle bed −28 dB, rain bed −20 dB, mixed by zone (leaves, water, roofs).<br>**Brawl:** streak α ×0.6. | `src/world/weather_fx.gd` + `rain.gdshader`: one static MultiMesh (even ids drizzle-speed, odd ids rain-speed); fall = fract(fx_time·speed / 18 m + seed) at a **constant** speed per set. Ripples and wetness come from `atm_weather` in the terrain and water shaders. | 1 draw, ≤ 900 quads; 1 sample for ripples | P1 streaks, wetness, rings, onset, ending / P2 puddles, prints, steam |
| WLD-12 | **Morning mist and rolling fog banks** | 04:30–07:30 on **50% of dawns** (seeded per dawn index) and on **every dawn after Drizzle or Rain** in the previous 6 game hours; weather Mist | **Grid, not planes:** one 64 × 64 m camera-local mesh of 32 × 32 quads (2 m), carrying both layers through a per-vertex layer flag. The vertex shader sets y = **lowland floor height** (height G) + 0.35 m (lower layer) or + 0.75 m (upper layer), so mist sits in every basin of a multi-level map and never floats more than its height above the local floor.<br>• Density = mist noise (detail G) at (xz − ofs_mist)/32 m × lowland-ness (smoothstep(0.6, 0.2, h − floor)) × coverage.<br>• α = density × 0.30 (lower) / 0.18 (upper). Soft contact: α × smoothstep(0, 0.35, y − terrain_h(xz)).<br>**Colour:** the fog key lightened 30% (day #E8EEF2, dawn #F2D2C2, night #4A5680). Unshaded.<br>**Order:** `render_priority` 5, between water (0) and contact blobs (10), so every blob, GroundZone, ring and marker draws over it. Terrain-composited rings (`eco_rings`) are cut out: α × (1 − 0.85·ring_mask(xz)).<br>**Dawn burn-off:** coverage 0.6 at 05:00, patches by 06:30, gone at 07:30. The threshold rises, so mist breaks up rather than fading uniformly.<br>**Fog bank** (Mist weather, 1–2 per state): a 50 m band with 15 m smoothstep edges at coverage 0.9, crossing the lowlands at ≈ 2 m/s.<br>**Sound:** inside mist, bird sweeteners −50%; the settlement bed gets a low-pass. | `src/world/mist_fx.gd` + `mist.gdshader`: a static mesh reading `atm_cam_box`; `atm_height_tex` gives the floor and the soft fade; `eco_rings_mask()` from economy's include. | 1 transparent draw; fill only over lowlands | P1 dawn mist / P2 fog banks |
| WLD-13 | **Gust-borne seeds and canopy dapple** (replaces always-on motes and light shafts) | seeds: a gust front over meadow; dapple: by day at forest edges | **Seeds ride the gust fronts ★:** seed instances live in the gust pattern's own frame (position = lattice point + ofs_gust), so they travel exactly at gust speed. A seed shows only:<br>• while the gust value there exceeds 0.6;<br>• where the ground 2 s upwind is meadow (grass density ≥ 0.5), i.e., where a front picked it up.<br>Lift 0.3–1.2 m × smoothstep(0.6, 0.8, g); 0.05 m (≥ 2 px) #F4F0E2 α 0.5; they sink and fade as the front's tail passes (≈ 6 s). Each crossing front lifts ≈ 20–40 seeds; ≤ 96 on screen. **The seeds are a gust visualiser, not confetti.** Emberwood (later) swaps in falling leaves.<br>**Canopy dapple:** on ground within 4 m of a canopy (lantern A), direct light is multiplied by a 2 m painted leaf-gap speckle (detail A): +12% value in the gaps. The speckle's UV is offset by 0.15 m × the canopy drive r(τ = 0.30 s), so the gaps shimmer when a gust passes. It costs 1 sample inside the cloud-shadow term (High and Medium; off on Low). | `air_fx.gd` (shared MultiMesh with WLD-08); dapple in the include's direct-light term. | 0 extra draws; ≤ 96 quads | P1 seeds / P1 dapple |
| WLD-36 | **Distant storm: "storm-lit" ★** (the art direction's signature) | weather Distant storm (§6) | **Off-map lightning:** the sun-break patches flash +20% value in 2 pulses (60 ms, gap 80 ms, 90 ms), cool #E8EEFF, at most 1 per 12 s, from a bearing chosen at state start (the storm sits off one map edge).<br>**Thunder** follows after distance / 343 m/s (distance hashed 2–6 km off-map, so 6–17 s): a low rumble at −18 dB on the Ambience bus, panned toward the storm's bearing.<br>**The grade:** contrast +0.04, cloud strength ×1.15, sun breaks ×1.8. Dark cloud shadows with roaming bright patches is the "storm-lit heroic diorama".<br>**Photosensitivity:** ≤ 3 flashes/s at any time, ≤ 20% value step, never full-screen; off under `reduce_motion` and juice 0. | `weather.gd` schedules flashes from its RNG in sim time; a global `atm_flash` multiplies the sun-break term; thunder via `ambience.gd`. | free | P2 |

### 4.3 Foliage and ground cover

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-14 | **Tree sway with hierarchy, inertia and memory** | always | Replaces today's sway, which runs on render `TIME` with one phase pattern everywhere.<br>**Trunk** (drive r at τ 0.55 s, κ 0.35): lean downwind (0.9° + 2.2°·w)·(y/H)², plus an oscillation of 0.6°·(0.3 + w)·sin(2π·(0.35/scale)·t + φ), where the frequency is constant per tree and φ comes from a hash of the instance origin.<br>**Branches** (drive at τ 0.30 s): canopy vertices offset (0.06 + 0.10·w) m·(r/R) at 1.1 Hz, phase per vertex from hash(round(local pos / 0.5 m)).<br>**Leaf flutter:** a ±6% value flicker on canopy fragments by leaf-clump hash at 4–6 Hz, scaled by (0.3 + g). High adds a 0.04 m vertex flutter.<br>**Added on top:** chop shudder (ECO-09) and shock lean (WLD-17).<br>**Stillness:** amplitudes × the visible mask at the instance origin (eased by the fog blend). A fogged forest stands still (WLD-27).<br>**Other plants:** bushes ×0.6 amplitude, ×1.4 frequency, τ 0.12 s; reeds and cattails lean 6° + 14°·w with phase per stem, τ 0.12 s (a 1 m reed tip moves 0.10–0.35 m). | `tree.gdshader` + `foliage.gdshaderinc` (`atm_sway(vertex, origin, H, params)`). One MultiMesh per chunk (tech §4.4). Weights come from height and radial distance, so AI-generated GLBs need no vertex-colour masks. | ≈ 30 ALU + 4 samples per vertex | P0 |
| WLD-15 | **Grass: a world-anchored wrap lattice ★, flowers that keep hours** | every frame (camera); footprints; wear; hour | **No chunks, no build.** Two static MultiMeshes of 3-crossed-quad tufts form toroidal lattices that follow the camera. A world cell always maps to the same instance while it is in the box, and its tuft comes from a hash of the world cell, so panning never pops. The CPU writes 1 global per frame.<br>• **Lattice A (near):** spacing s = 0.674 m (High: 2.2 tufts/m²), box 60 × 34 m (4,450 instances), centred on the near part of the footprint.<br>• **Lattice B (far):** spacing 2s, so its cells are exactly A's even-even cells; box 96 × 52 m (2,700 instances). Its tufts are ×1.5 (coverage 56%). It draws only when ground beyond 43 m is on screen (camera distance > 29 m); otherwise `visible_instance_count` = 0.<br>• **Handoff:** A draws a tuft when its ray distance r < 45 m and it lies inside A's box. Near the boundary (41–45 m, or A's last 3 m), A's even-even tufts grow to 1.5× while the others shrink to 0. B draws the even-even tufts at 1.5× everywhere else, so **exactly one lattice draws each tuft**, with no gap and no double.<br>• **Zoom-scaled fade:** scale and scissor ramp to 0 between 1.25·d_cam + 4 m and 1.5·d_cam + 4 m: 39–46 m at the default 28 m, 61.5–73 m at max zoom 46 m. Zooming out no longer melts the meadow.<br>• **Far field:** the terrain multiplies the 2 m leaf-gap speckle, inverted, as a grass tint (+8% value toward #8DAE60) by grass density × smoothstep(d_cam, 1.5·d_cam + 4 m, r), so the far field never reads as bare dirt.<br>**Tufts:** 0.28–0.38 m tall, 0.35 m wide, from a painted atlas (4 grass + 4 flower variants), alpha scissor 0.5. Root colour = baked ground albedo (ground RGB); tips ×1.1 lighter (Greenvale #6E9A3E, thick #4F7A2E).<br>**Density:** a tuft exists if hash(cell) < density/2.2, with a smooth shrink near the threshold. Density = 2.2 / 1.4 / 0.7 per m² (High / Med / Low) × ground A (grass weight, minus known footprints) × (1 − wear).<br>**Flowers:** where the low-frequency noise (detail G at 24 m) > 0.72, 30% of tufts become flowers (Greenvale #F2E86B, #F4F1E8, #C792EA; saturation ≤ 60%).<br>**Flowers keep hours ★:** heads close from 18:30, staggered by hash over 12 s; each head takes 1.8 s `in_out_sine` (petal scale 1 → 0.6, value ×0.8). They reopen from 06:15 the same way. P2: "sunbell" heads turn toward the sun. | `src/world/grass.gd` + `grass.gdshader`: lattice coordinates from `INSTANCE_ID` and `atm_grass_box`; height from heroes' `terrain_h`; samples ground, world, noise and fog. Interpolation OFF, cast_shadow OFF, map-sized `custom_aabb`. Battlefield-bloom tufts are a separate 384-instance MultiMesh (WLD-31). | High ≤ 7.2k instances / ≈ 86k vertices (typically 3–4.5k tufts drawn); Med ≈ 4.6k; Low ≈ 2.3k; 2 draws + 2 depth-prepass draws (Forward+); 0 ms build | P0 lattice, density, fade / P1 flowers keep hours / P2 sun-tracking |
| WLD-16 | **Trample, wakes and the order press** | units on screen; move orders | **Tramplers:** up to 24 capsules (8 on Low), picked by buckets in this order: heroes, selected, large, then moving units nearest the focus. On-screen only. On Low, tufts beyond 25 m from the focus skip the trample tests (a coherent branch).<br>Each capsule runs from the unit's `display_pos()` back along its velocity for 0.6 s of travel (≤ 1.8 m), radius = unit radius + 0.25 m.<br>**Bend** per tuft vertex: away from the capsule axis by 0.18 m·f·(y/H) and down by 0.08 m·f, where f = 1 − smoothstep(0.6r, r, distance). Strength is 1 at the head and falls linearly to 0 at the tail, so the grass springs back behind a walking unit: a visible wake. Standing units flatten a ring under their feet.<br>**The order press ★:** slot 23 is reserved for the newest move-order marker (CMB-08): a 0.6 m ring stamp, strength 1 → 0 over 400 ms `out_quad`, so a right-click visibly presses the grass where the order lands. | Material uniform arrays on the grass and air materials: `vec4 trample_a[24]` (x, z, radius, strength), `vec4 trample_b[24]` (tail dx, dz). Filled each frame from the bucket list (no sort). | 24 capsule tests per vertex (8 on Low); CPU ≤ 0.04 ms | P1 |
| WLD-17 | **The world flinches: shock rings ★** | `Atmos.shock(pos, strength)`, only if pos is visible | **Callers:**<br>• heavy footfalls 0.12 (mass ≥ 3, ≤ 1 per 700 ms per unit; CMB-04);<br>• **building placement 0.15** (`construction_started`: grass bows outward from the footprint edges and critters within 20 m spook);<br>• clay pot 0.35 and Brace the Wheel 0.35; powder siege 0.5;<br>• the Bombard crate 0.6; hero ultimates 0.6–1.0; building collapse 0.8 (halls 1.0); the Wagon Ring 0.8.<br>**Ring:** front speed 14 m/s, max radius 6 + 10·strength m, life 2.5 s.<br>**Grass:** at the front, flattened outward by 35°·strength·e^(−(r − 14t)²/1.28)·e^(−t/0.9), with tips lightened +15% × min(1, 3·strength), so even a footfall reads as a pale ripple. Behind the front it springs back with a damped wobble (ω = 2π·2.2 Hz, ζ = 0.3).<br>**Trees:** lean away by θ = 3.5°·strength·(1 − r/R)·e^(−1.6τ)·sin(2π·1.4τ), where τ = t − r/14, so farther trees flinch later. Canopies within 8 m drop 2–4 LEAF (BallisticFx) when strength ≥ 0.35.<br>**Life:** critters within 20 m flee; perched birds and storks take off at strength ≥ 0.35 (WLD-23, 37); fireflies scatter.<br>**Slots: 4. A new shock evicts the slot with the lowest remaining strength s·e^(−age/0.9) (expired slots count 0), ties to the oldest, and only if the new shock is stronger.** A Drystone Walker's footfall can never evict a fresh siege or ultimate shock. Shocks within 4 m and 150 ms merge (max strength). No camera shake here. | 4 globals `atm_shock_0..3` (x, z, t0 in sim seconds, strength), read by `foliage.gdshaderinc` and `grass.gdshader`. | 4 tests per vertex | P1 |

### 4.4 Water (scaled to the body)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-18 | **Shores by body size; cat's paws on ponds ★** | always, on water | Each body's span is measured at load (WLD-F6). d = shore distance in metres (+ in water, − on land).<br>**Every body (bible §6.3):** the ground within 1 m of the water darkens by 25% in value (the wet band), and a soft foam line #E8F0EC at α 0.4 is broken up by painted strokes (detail B).<br>**Ponds and pools (span < 20 m; the slice's two ponds of r 5 m and the Hale Spring):** no lapping lines, no whitecaps, no fish. Instead, **cat's paws**: where the gust value over the water exceeds 0.5, on the downwind half (dot(xz − centre, d) > −0.3·r), stroke-normal strength rises +60% and value +4%, so you watch each gust front skate across the pond. Strength ∝ w.<br>**Lakes (span ≥ 20 m; later maps):** lapping lines 0.5·smoothstep(0.75, 0.95, sin(6d − 2π·t/2.2 s + 3·noise))·(1 − smoothstep(0.3, 2.2, d)); the wet band advances and retreats 0.25 m with them; whitecaps on deep water when w > 0.6 (α 0.4).<br>**Fog:** amplitudes ×0.1 (still water). | `water.gdshader` and `terrain.gdshader` read d from world G and a per-body uniform (`body_mode`, centre, r). | ≈ 12 ALU per fragment (ponds); ≈ 18 (lakes) | P0 |
| WLD-19 | **Water surface: painted shimmer, glints, time of day, splashes** | always | Replaces today's noise-normal water.<br>**Colour:** Greenvale shallow #4FA3A0 / deep #22566E (the spring #5AA3A0), graded by the key; at night #2E5C7A / #0E2A44. The shallow band (0–2.5 m) comes from the shore distance.<br>**Shimmer:** two painted stroke normal maps scrolled downwind by the integrated water offsets (0.06 and 0.11 m/s), strength 0.35 + 0.4·w.<br>**Glints** (a VFX term): pow(max(n₁·n₂, 0), 18)·(0.4·daylight + 1.0·golden), #FFF3D6, HDR ≤ 1.3, kept under 2% of water pixels. At night: silver moon glints #C9D6FF × 0.6·night × the moon-phase factor.<br>**Rain rings:** the ripple texture ×1.5.<br>**Splashes:** `Atmos.water_splash(pos, size)` for anything landing in water (missed projectiles, debris, falling trees):<br>• a crown of 6 droplets (#D8EEF2, up 1.6–2.4 m/s, life 450 ms);<br>• 2 rings (0.3 → 1.2 m over 900 ms);<br>• a plop (World −16 dB, ≤ 3/s).<br>**Fog:** animation ×0.1, glints off. | `water.gdshader` (with the include; render priority 0). Rings use the FxSprites ring kind on the water plane. Combat and economy call `water_splash()` when a landing point is over water. | ≈ 26 ALU per fragment | P0 colour + shimmer / P1 glints + splashes |
| WLD-20 | **Wading: rings, bow wake, entry splash** | a unit's depth = water_level − height_at(display_pos) > 0.05 m | **Unblocked:** the Hale Spring pool is walkable shallow water (neutrals §5.8, slice-plan E13), and it is the map's night-ambush site, so wading is **P0 there**.<br>**Entry** (depth crosses 0.05 upward): a crown of 6 droplets and a "sploosh" (World −14 dB, ≤ 3/s).<br>**Moving:** CMB-04 already places a ring per stride. Add a bow wake: a ring every 220 ms at pos + 0.3 m ahead, r 0.25 → 1.4 m over 1,100 ms (`out_quad`), α 0.45 → 0, #E3F2F5. Overlapping rings form the V.<br>**Idle in water:** a slow ring every 1.8 s, r 0.2 → 0.9 m.<br>**Group slosh:** one loop, not one per unit, scaled by the on-screen units in water: 1–3 at −22 dB, 4+ at −16 dB (an event slot, WLD-33).<br>**P2 caustics:** a cheap voronoi caustic on the pool bed (×0.15, by day only). | `unit_view.gd` → `Vfx` → FxSprites ring kind. Tier rules as CMB-04: Busy keeps importance ≥ 3; Brawl keeps rings only. | ≤ 5 spawns/s per wading unit | **P0 at the Hale Spring** / P1 other shallows |

### 4.5 Life

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-21 | **Critter system: selectable, honest, never a radar** | always | **Visual-only animals** (neutrals §6): owner `NEUTRAL_PASSIVE`, never blocking, never attacked, no XP, no corpse.<br>**Selection goes through `selection.gd`:** when its unit pick comes back empty, it calls `Life.pick(screen_pos, 14 px)`. A picked critter becomes a single selection with the info panel (UI), an ivory ring (#E6D8B8 α 0.6, 0.5 × body length) and an ivory hover rim (+0.25). It is never in a box selection, never in a group and takes no orders.<br>**Click-spam gag:** `selection.gd` forwards each click on a selected critter to `Life.clicked(id)`. **6 clicks within 3 s** plays the species gag (4.5a), then a 20 s cooldown. Nothing explodes or dies.<br>**States:**<br>• CALM: graze, wander, preen (4.5a);<br>• ALERT: head up and turned to the threat over 300 ms (`in_out_sine`), held while it stays within 1.5 × the startle radius;<br>• FLEE: a threat inside the startle radius (hare 4 m; the goose hisses at 2 m), a visible hit within 6 m, a shock within 20 m or a projectile landing within 6 m;<br>• HIDE: species-specific;<br>• RECOVER: home after 15–25 s with no threat inside 12 m.<br>**Threat = a unit visible to the local player** (or the player's own unit). Critters stand on visible cells only; in fog they are hidden and deselected.<br>**Motion:** closed-form segments (from, to, t0 snapped to the 10 Hz Life tick, duration, gait curve), so poses are exact at any frame rate. Flee targets are validated with `pathing.is_walkable_world` on the same cliff level (geese may also take to their pond).<br>**Anticipation:** no reaction fires cold. The hare's thumps, the goose's 150 ms hiss crouch and a bird's 60 ms dip come first. | `src/world/life.gd` (`class_name Life`, `World/Life`, interpolation OFF), Packed* arrays.<br>**10 Hz, round-robin 4 critters per frame.** Each queries a coarse grid of 4 m cells holding the visible units (rebuilt at 10 Hz in one pass), and tests hits only against FND-3's ≤ 8 per-frame brawl clusters.<br>**One MultiMesh with a species atlas** (hare + goose in one mesh, the other species collapsed per instance). The CPU writes poses for on-screen critters only (≤ 14 per frame). | ≤ 0.03 ms per frame | P1 |
| WLD-22 | **The Wether Downs cast** (table 4.5a) | hand-placed (slice-plan §1.9) | **Exactly the neutrals cast:** 6 Brown Hares (3 per side, west and south field meadows, ≥ 15 m from starts), 4 Grey Geese (2 per pond) and Firefly Drifts over the ponds and the spring dell (WLD-08). That is 10 animals plus the drifts. **The Sparrow Roost is SLICE+** (WLD-23), the hedgehog is *later*. Sheep, frogs, butterflies, fish and ambient songbird perches are **not** on the slice; they need neutrals' sign-off first (§11).<br>**Generated maps:** ≤ 0.4 per 16 × 16-tile chunk of open ground, ≤ 14 per map, none within 15 m of a start. | `data/biomes.json` → `critters`. bpy primitives with painted textures (slice-plan B17); procedural hop and waddle. | included in WLD-21 | P1 |
| WLD-23 | **Flights and sweeping bird shadows ★** | `Flocks.flush(pos, n, kind)`; `roost_flushed`; CRP-01 crow lift-off; a shock ≥ 0.35 near a perched bird | **Callers:** ECO-29 nest-tree first chop (3 songbirds, chirps −20 dB); the Sparrow Roost flush (SLICE+: 12–16 sparrows, `cv_sparrows`, 2.5 s burst, resettling after 30 s; drawn per the §2 exception); CRP-01's crows (heroes own the trigger); kingdom storks (WLD-37); the carrion circle (P2).<br>**Take-off:** a 60 ms anticipation dip (sy 0.85, pitch −15°); members leave over 0–250 ms (staggered) with an 8–9 Hz wing burst for 1.0 s.<br>**Flight:**<br>• a cubic Bézier from perch P0 to a new perch P1 20–45 m away, away from the threat and ≥ 15 m from visible units;<br>• the control points derive from P0, P1, a climb height (8–12 m) and a swirl sign (6 m lateral);<br>• duration = dist(P0, P1) / 7 m/s + 2 s; members orbit the curve at 0.8–1.4 m offsets (hashed);<br>• flap 7–9 Hz while climbing; glide on descent with 2–3 flap bursts;<br>• **landing:** the last 1.2 s `out_cubic`, with a **wing flare** over the final 250 ms (span ×1.3, pitch +30°), then a hop.<br>**Ground shadow:** each bird casts a soft dot below (0.25 m, α 0.25·(1 − h/20 m)). A flock's shadow skims over your army: a free depth cue for a top-down camera.<br>**Carrion circle (P2):** after ≥ 5 visible deaths within 30 s in a 20 m area, 2–3 **red kites** (forked-tail silhouette, 0.6 m) circle at 14–18 m (radius 6–9 m, period 9–12 s). Their 0.9 m soft shadows sweep the field; they glide off-map 45 s after the last death there. Max 1 circle. | `src/world/flocks.gd` + `bird.gdshader`: one MultiMesh (≤ 64 birds) plus one shadow MultiMesh, interpolation OFF, map-sized `custom_aabb`. **Packing (Compatibility-safe):** the transform holds P0, P1, climb height, swirl sign, t0 (sim s), duration, member index and a spare; custom data holds only 0..1 values (wing phase, size jitter). Flight runs in the vertex shader; shadow height from `atm_height_tex`. | 2 draws; ≈ 0 CPU between events | P1 / P2 carrion |
| WLD-24 | **Aftermath: the silence and the first bird ★** | `Vfx.battle_started(pos)` (CMB-36) on screen; then quiet | **Silence:** from `battle_started` within 30 m of the focus, `Audio.duck(&"wld_battle", &"Ambience", −5 (Busy) / −8 (Brawl), 500, −1, 6000)`. It is re-issued when the tier deepens; the arbiter applies the deepest.<br>**Quiet** = intensity I < 2 held for 2.5 s. Then `Audio.unduck(&"wld_battle")`: the beds return over 6 s, and the bird sweeteners stay suppressed for 12 s.<br>**First bird:** only if the fight had ≥ 3 visible deaths. At **quiet + 3.5 s**, after CMB-43's weapons-down wave has finished, one positional call plays at the fight's centroid (World −12 dB): by day a blackbird phrase, at night **a nightjar churr** (never an owl). The first sound after a battle is a living one.<br>**Crows (P2):** 2–4 crows land near fresh corpses 3–8 s after quiet (WLD-23 flight from off-screen). They hop and peck (head bob 4 Hz, 0.04 m) and leave when a unit comes within 4 m or the corpse decays (CMB-31).<br>At most once per area per 60 s. | `ambience.gd`; ducks only through the arbiter (UI AUD-01 is its only writer). Crows from `flocks.gd`. | negligible | P1 silence + first bird / P2 crows |

**Table 4.5a: the slice cast** (neutrals §6; startle radius, speeds and gags are canon)

| species | where and how many | size and colours | idle | startle and flee | click-spam gag (6 clicks / 3 s, 20 s cooldown) | sound | night / rain |
|---|---|---|---|---|---|---|---|
| **Brown Hare** (`critter_brown_hare`) | 6: 3 per side in the west and south field meadows, ≥ 15 m from starts; home = a grass form (no prop) | 0.35 m sitting (0.45 m sat up), 0.4 m long; back #9A7B58, belly #D9C7A6, ear tips #2A221C | graze head-down 2–4 s; hop 0.6 m every 4–9 s (260 ms, 0.12 m apex, landing squash sy 0.85 for 60 ms); sit up 1.5 s with an ear swivel ±25° | startle radius 4 m: ears up (80 ms), **one thump** (the anticipation), then an 8 m bolt at 7 m/s with 2 zig-zag cuts of ±35°; sits up and looks back for 1.2 s | **two hind-foot thumps 120 ms apart** (the anticipation), a 10 m zig-zag bolt at 7 m/s, then a **1.5 s ears-down freeze** (sy 0.8, ears flat over 100 ms) | `cv_hare` (thump ×2 + dash) | crouches still in its form (sy 0.75, ears flat; a startle bolts only 4 m) / crouches |
| **Grey Goose** (`critter_grey_goose`) | 4: 2 per pond (ponds P at (40, 100) and (100, 40)) | 0.6 m tall with the neck up; grey #8E8C86, breast #B8B4AA, bill #E07A3A (accent) | graze the shore; waddle 2.4 m/s with a body roll of ±8° at 2 Hz; swim (bob 0.03 m at 0.5 Hz, a bow ring every 400 ms while moving); preen every 8–14 s | startle radius 2 m: **hisses instead of fleeing** (a 150 ms crouch, then neck stretched low and forward ×1.25, wings half open ×1.2), held while the unit stays within 2 m. Combat within 6 m: flap-runs onto the pond at 3.5 m/s (wings at 6 Hz) and swims to the centre | honks and flaps (span ×1.4 for 400 ms), then **nips the clicking player's nearest visible unit within 8 m every 1.5 s for 6 s**: a 0.25 m lunge (90 ms `out_quad`), a **3-feather puff** (#D8D4CC cutout, 0.08 m, drifting down over 600 ms) and a **honk glyph** (three short ivory sound strokes above the goose, never letters). **Nothing on the unit:** no flash, no HP change, no damage event. Then it struts off (head high, 1.2 m/s). With no unit in range, it honks twice at the camera | `cv_goose` (honk, hiss, flapping charge, smug honk) | sleeps on the water (head tucked, drifting 0.05 m/s downwind within the pond, rocking ±2°) / swims and preens more |
| **Firefly Drift** (`critter_fireflies`) | over the ponds and the spring dell at night (WLD-08) | WLD-08 | WLD-08 | WLD-08 | — | — | night only / off in rain |
| *Sparrow Roost* [SLICE+] | a roost in a tree line | 0.18 m (toy scale), #8A6E50 | — | the **flush is a sim trigger** (any player's ground unit within 4 m): 2.5 s burst via WLD-23, drawn above the fog in explored areas | — | `cv_sparrows` | day only |

### 4.6 Fog of war

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-25 | **Smooth, breathing, honest fog edge** | every frame; fog uploads (≈ 10 Hz) | **Asymmetric temporal smoothing:** `Fog` alternates uploads between L8 textures A and B (display bytes, so each upload is a straight `set_data`). The shader computes f = **min(cur, mix(prev, cur, k))**, k = smoothstep(0, 1, (sim_time − t_upload)/period), with the period measured and clamped to 80–400 ms.<br>• **Concealment lands within one upload** (≤ 100 ms after the sim): the drawn visible area never exceeds the sim's.<br>• **Reveal eases** over the period, so revealed ground grows instead of stepping at the fog rate.<br>**Dusk honesty:** rules §13 already makes sight change over **3.2 s** from the event, so the dark closes in over 3.2 s on screen, as in WC3. The sim must implement it as a 96-tick ease (request §12); visuals never ease slower than the sim.<br>**Painterly edge:** v = f + (n − 0.5)·0.18, where n = the brush-edge noise at (xz − ofs_edge)/4.8 m, drifting 0.05 m/s downwind. Explored = smoothstep(0.14, 0.34, v); visible = smoothstep(0.64, 0.82, v). The edge is a soft brushed wobble that slowly breathes, never a grid.<br>**Inner vignette:** the outer 1.5 m of the visible area darkens 8%.<br>Fogged value: ×0.55 by day, ×0.45 at night (WLD-27). | `fog.gd`: double buffer, display bytes and `atm_fog_blend` (t_upload in sim seconds, period, flip). `atm_fog()` and `atm_memory_grade()` from the include serve terrain, trees, water, grass, props and building ghosts. | 3 samples per fragment | P0 |
| WLD-26 | **A sea of cloud over the unknown, and the cartographer's reveal ★** | unexplored areas; newly explored cells | **Base** #0A0C12.<br>**Two cloud layers:** the painted cloud mask sampled twice, at 38 m and 22 m, each scrolled by its own integrated offset (0.3× and 0.45× cloud speed). High adds **fake parallax** (uv offset = −V.xz / V.y × 6 m and × 11 m), so the clouds slide against the ground as the camera pans. Low: one sample, no parallax. Cloud value = mix(#0A0C12, #222A44, smoothstep(0.45, 0.8, c)·0.7). Sun-side tops get +#2A2F4A by day, silver #1C2238 at night.<br>**Ink rim:** along the explored boundary, a 0.6 m wobbly ink line, #05060A α 0.45, so the known world looks drawn onto a map.<br>**Map skirt:** a 40 m ring mesh around the map with the same shader, so the edge of the world is cloud, never a void.<br>**The cartographer's reveal (P1):** newly explored cells get an arrival stamp, upload time + distance from the nearest new-vision source / 12 m/s, so **the ink rim draws itself along new boundaries at 12 m/s**. Each stamped cell shows a parchment edge (#E9D9B0 α 0.35) and a darker rim for 600 ms after its arrival. A quill-scratch tick (UI −26 dB, ≥ 1.5 s apart) plays only for batches of ≥ 40 new cells. Scouting feels like mapping. | Terrain, tree and water shaders via the include; `TerrainBuilder` adds the skirt. Reveal: the CPU keeps the active cells (≤ a few hundred) and writes stamps into world B as (sim_time × 32) mod 255 + 1, clearing them after 1.5 s; world uploads at ≤ 10 Hz only while cells are active. | ≈ 25 ALU per fragment, only where unexplored | P1 |
| WLD-27 | **The remembered world: still, faded, sketched ★** | explored-but-not-visible areas | **Grade:** saturation ×0.4, value ×0.55 (×0.45 at night), multiply #9DB3D6 at 15%, paper grain ±6% (detail R at 2 m; High and Medium). P2: faint hatching in shadowed parts (4%). Building ghosts get the same grade.<br>**Stillness** (eased by the fog blend):<br>• foliage, grass and cloth amplitudes × the visible mask; water animation ×0.1 (a glassy pond); cloud shadows ×0.3;<br>• hidden: critters, fireflies, seeds, moths, smoke and flame sprites (window emission stays);<br>• rain streaks still fall (weather is "now"), but ground rings stop.<br>**Tree memory:** a tree felled outside your vision stays drawn until you see its cell again, then fades out over 300 ms and leaves a stump. No topple plays (ECO-11 needs a visible fall).<br>The rule players learn without being told: **if it moves, you can see it.** | All via `atm_fog()` and `atm_memory_grade()`. StreamFx and AirFx multiply α by visibility. `doodads.gd` holds `remembered_felled` and listens to fog updates. | 2 ALU + 1 sample | P0 grade + tree memory / P1 stillness, grain |

### 4.7 Settlement and memory

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-28 | **House smoke, and one wind for all smoke** | non-production structures (houses, crofts, neutral buildings) 17:00–08:00 and in rain; clamp fires always | **House smoke** (stream region D, id `house_smoke`, 12 columns × 3 = 36 slots): one column per `smoke_point`. A puff every 1,400 ms, 0.25 → 1.1 m, rise 0.6 m/s, life 3.2 s, α 0.22. Colour #B7B0A6 by day, #6E6A75 at night, with the lowest 0.4 m tinted #FFB86B at 15% (lit from inside).<br>Production buildings never get house smoke, so BLD-11's "cold chimney = idle" stays true.<br>**All smoke** (house smoke, BLD-11, BLD-15 fires, clamp seams, ignition puffs) drifts by wind·age^1.4·0.6 m + g(age)·age·0.4 m, where g is sampled at the puff's spawn point with τ = age. Every column on the map leans the same way and kinks as a gust front passes up through it.<br>Cap: 12 columns nearest the focus (buckets). Hidden in fog. | The StreamFx shader (economy §2.3) gets the wind term from the include. `building_fx.gd` spawns house smoke from def `smoke_point` (default on for supply buildings). | ≤ 36 sprites | P1 |
| WLD-29 | **Cloth: banners, flags, pennants, tents, awnings** | always | **Fixed-frequency waves, wind only weights them:** displacement along the cloth normal = A·u^1.4·[(1 − w)·sin(2π(u/0.9 − 1.4t) + φ) + w·sin(2π(u/0.9 − 3.0t) + φ)], where:<br>• u = distance from the pole (UV.x);<br>• A = 0.06 + 0.10·w + 0.05·r m, with r = the cloth drive (τ 0.05 s, κ 0.15);<br>• φ = a hashed phase per cloth.<br>Low wind droops the tip up to 35°·(1 − w).<br>**Free flags yaw to d(t)**, the closed-form wind direction. Every flag on the map points the same way and turns together.<br>**Wet cloth:** A ×0.7, droop +10°, and the 3.0 Hz weight ×0.8 while wetness > 0.5.<br>**Spikes:** FLUTTER_SPIKE (economy §2.4) and FND-6's per-instance `accel` and `kick` add on top.<br>Team-colour regions keep their hue. Amplitude is capped at 0.25 × cloth length, so flutter never hides the ownership area. Still in fog. | `cloth.gdshaderinc` (`atm_cloth(vertex, uv, pole_axis)`) for building banners, rally flags (BLD-13), unit back-banners, tents, scarecrow coats and the Weighstall awning. GLB cloth materials are named `*CLOTH*` or use a vertex-colour mask. | ≈ 18 ALU per vertex | P0 |
| WLD-30 | **Desire paths: the map remembers where you walked ★** | every 8th sim tick (3.75 Hz), moving units (> 0.5 m/s) visible to the local player | **Wear W** (world R, 1 m cells):<br>• rasterise the segment from the previous poll position (Bresenham), adding +1 once per cell (+2 for heroes and large units), so fast cavalry and wolves leave solid trails, not dotted ones;<br>• +1 to the 4 neighbours on every second poll, so paths are ≈ 1.5 m wide; saturates at 255;<br>• heals −1 per 20 s on cells not walked (1/75 of the texture swept per poll).<br>**Look:** grass layers blend toward a trodden colour (Greenvale #8C7A55), up to 55% at W = 1, with noise-broken edges. Tuft density × (1 − W). Dirt layers get a 6% darker, smoother centre line.<br>**What appears:** the hall–seam trail forms in ≈ 8 minutes of mining; army routes and creep approaches show by mid-game. A finished match leaves its story on the ground.<br>**Honesty:** only units the local player could see add wear. Paved roads are unaffected. Puddles prefer wear (WLD-11). | `src/world/wear.gd`: `PackedByteArray` mirror, changed bytes written in place; world uploads at 1 Hz (147 KB, budgeted). The minimap reads the same texture. | ≤ 0.15 ms per poll; 1 sample per fragment | P1 |
| WLD-31 | **World memory ledger and battlefield bloom** | corpses, rubble, stumps, stains, wear, felled trees | **One persistence policy across domains** (table 4.7a), enforced by `WorldMemory`: lifetime, cap, fade and fog rule per kind. One setting, `world_memory`, scales lifetimes: Short ×0.5, Normal, Long ×2.<br>**Rules:** memory never animates; it never adds hue, only darkens or desaturates; it is created only from events the local player saw; in fog it shows the last seen state.<br>**Battlefield bloom ★ (P2), the one explicit exception to "never adds hue":** when a ground stain expires on grass-weighted terrain (≥ 0.5), 3–6 flower tufts sprout over 1.2 s (scale 0 → 1, `out_back(1.3)`) inside the stain, at saturation ≤ 60%. They stay 4 min, then shrink over 3 s. Cap 64 clusters, ≤ 384 tufts. Old battlefields flower. | `src/fx/world_memory.gd` holds the caps for CMB-32, BLD-16, ECO-11 and economy's logs and litter. Bloom tufts: their own 384-instance MultiMesh (transforms written at spawn only). | bookkeeping only; bloom 1 draw | P1 ledger / P2 bloom |
| WLD-37 | **Faction base life ★** | always, own or seen bases | **Kingdom storks** (on ECO-29's resident storks on `stork_nest` crowns): at dawn, T0 + hashed 1–4 s, each **clatters**: head back 40°, bill flutter at 6 Hz for 1.2 s, with `amb_base_kingdom`'s clatter one-shot (World −20 dB; the nearest visible stork only). On a shock ≥ 0.35 within 20 m, a stork lifts off (WLD-23, an 8 m loop) and returns after 12 s with 3 landing flaps (economy's crown sub-part).<br>**Clans felt and bronze:** felt flags and door flaps use WLD-29. Bronze plate chimes strike when g crosses 0.7, ≤ 1 per 8 s per base (World −24 dB, 3 no-repeat takes).<br>**Tormai bronze mirrors catch moonlight** (bible §2 night row): a moon-facing glint on mirror materials, pow(max(dot(R, L_moon), 0), 40) × night × the moon-phase factor, HDR ≤ 1.3.<br>**The Gustcaller's wind vane:** vane yaw = d(t) + 0.3·g wobble, through an FND-6 spring (ω 6, ζ 0.4); staff ribbons use WLD-29. | Economy crown parts and `building_fx`; FND-6 prop layer for the vane; the mirror glint in the structure shader. | negligible | P1 chimes, mirrors, vane / P2 storks |

**Table 4.7a: the world memory ledger** (lifetimes at `world_memory` = Normal)

| memory | owner row | lifetime | cap | fade | fog rule |
|---|---|---|---|---|---|
| Corpse | CMB-30/31 | 8 s (sim decay) | sim | team-colour ebb, then sink | the sim hides enemies in fog |
| Ground stain | CMB-32 | 90 s | 96 | last 20 s | created only if seen; dimmed in fog |
| Siege scorch | CMB-27/32 | 120 s | 48 | last 30 s | same |
| Pot scuff | CMB-27/32 | 60 s | (scar map) | last 15 s | same |
| Wreck (siege, wagon) | combat | 12 s | 8 | sink 1 s | same |
| Rubble | BLD-16 | 90 s | 24 | 4 s | same |
| Hall rubble | BLD-16 | 300 s | 4 | 4 s | same |
| Leaf litter | ECO-11 | 30 s | 48 | gradual | same |
| Stump | ECO-11 | the whole match | 1,024 (one MultiMesh) | none | same; a felled tree in fog stays drawn until seen (WLD-27) |
| Desire path | WLD-30 | heals −1 per 20 s | texture | gradual | only seen units add wear |
| Dew trail | WLD-35 | until 08:30 | texture | dries 07:30–08:30 | only seen units |
| Grass clearing (footprint) | WLD-15 | while the structure stands or its ghost is known | texture | 300 ms | known structures only |
| Battlefield bloom | WLD-31 | 4 min | 64 clusters / 384 tufts | 3 s shrink | only from seen stains |
| Carrion circle | WLD-23 | until 45 s after the last death there | 1 | glide away | only seen deaths |

### 4.8 Sound of the world

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-32 | **Beds: the hill country and the bases** | 4 Hz, at the listener focus | **Base bed (2D):** `amb_gv_day` / `amb_gv_night` (bible §9.7: skylarks, insects, a far brook / crickets and the occasional nightjar), crossfading equal-power over 8 s centred on T0.<br>**Settlement beds, per faction (P1):** `amb_base_kingdom` (storks clattering on roofs, a far smith, a cart creak, a murmur with no words) and `amb_base_clans` (felt flaps, small bronze plate chimes, a kettle, ribbons). Weight = the own, allied or **seen** structures of that faction within 30 m of the focus (refreshed at 1 Hz, Gaussian over the 8 m zone grid). An enemy base you are looking at sounds like *its* faction.<br>**Weather beds:** wind (−30 dB + 14·g at the focus); drizzle −28 dB and rain −20 dB, mixed by zone (leaves, water, roofs); mist adds no bed but cuts bird sweeteners 50%.<br>**Mix:** gain_dB = lerp(−40, 0, √w), damped at 1.2/s; a bed stops after 3 s below w = 0.03; ≤ 6 beds (UI §5.2).<br>**Zoom:** for every 10 m beyond the default distance, wind +1.5 dB and the settlement beds −1.5 dB.<br>**Combat:** ducking per WLD-24, only through `Audio.duck`. | `src/world/ambience.gd` (world-owned: beds, stingers, emitters, sweeteners and the aftermath trigger). The UI's `src/audio/mix_beds.gd` keeps the battle and march beds. Both play through `Audio`'s pools on the Ambience bus with the Voice sidechain (UI AUD-01). | ≤ 6 streams; CPU ≈ 0.02 ms | P0 base bed / P1 the rest |
| WLD-33 | **Positional emitters, landmark loops first; sweeteners; the world voice pool** | a scheduler every 0.5 s | **World voice pool: 8 voices at priority 20** (6 loops + 2 one-shots; request §12, replacing the audio research's 4). **Loop slots, ranked:**<br>1. landmark loops (§4.10: `lp_spring`, `lp_weighstall`, `lp_standing_ring`, `lp_charcoal`, the inn murmur, `lp_mine_night`): the 2 nearest within 30 m;<br>2. fire crackle: the nearest lit torch, brazier or clamp fire;<br>3. water: the nearest pond or brook (`lp_pond`, `lp_brook`);<br>4. camp state: the nearest visible camp's family loop (4.1a; Sootcoat snores, a Tattiebogle creak, stone hum);<br>5. one spare (wading slosh, the rain-on-roof zone).<br>Re-chosen every 0.5 s by buckets with 2 m hysteresis; swaps crossfade over 400 ms.<br>**One-shot slots:** events (the first bird, the gust whoosh, chimes, honks, thumps, splashes, thunder) and one sweetener.<br>**Stealing order:** first bird and whoosh > landmark loops > crackle > water > camp state > sweetener.<br>**Sweeteners (bible §9.7):** one every **8–25 s**, at a point **within 40 m** of the focus chosen by zone weight (4 rejection tries).<br>• Day: `swt_birds` (songbird phrases, woodpecker, cuckoo), `swt_wind` near forest.<br>• Night: `swt_night` (a distant fox bark, a hedgehog snuffling, a single frog croak); nightjar churrs. **No owls.**<br>• Never the same sample twice in a row (`AudioStreamRandomizer` no-repeat); pitch 1.06; ±2 dB.<br>Static ambience may play in fog (it carries no unit information); creature sounds never follow units. | `ambience.gd` with `Audio.loop_3d` and `play_3d`. The listener sits at the focus + 6 m (audio doc). | ≤ 6 loops + 2 one-shots | P1 |

### 4.9 Minimap

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-34 | **Living minimap** | base baked once; overlay every frame | **Base:** baked once at load at 2 px per tile from the ground albedo: cliff edges darkened 25%, water by depth, trees as dark-green dots. Felled trees (as remembered, WLD-27) **patch only their dirty pixels** (≤ 64 per event); there is no 1 Hz re-bake.<br>**Overlay shader** (under the unit dots), all from the shared globals and textures:<br>• unexplored #07080C with the WLD-26 cloud drift at 4%;<br>• fogged: ×0.6 and desaturated;<br>• night: multiply #7F8CB8 (≤ 20% darker);<br>• cloud shadows at 6%, in sync with the world;<br>• water shimmer: diagonal bands ±4%;<br>• desire paths: 12% toward the trodden colour;<br>• **the tide band crosses the minimap at exactly the same s_f(t) as the world.**<br>**Camp sleep state:** WLD-34 publishes `camp_sleeping(camp_id)` for visible camps. The UI's shield pip (neutrals §1.2) drops to 60% value and shows a 4 px closed-eye overlay.<br>Unit dots, pips, pings and the camera trapezoid (UI doc) are drawn on top and never graded. | `src/ui/minimap.gd`: a `TextureRect` with `minimap_overlay.gdshader` (canvas_item; global uniforms work there). `_draw()` keeps dots and icons. | 1 canvas draw; ≤ 0.05 ms | P1 |

### 4.10 The places of Wether Downs (one row per landmark; slice-plan §1.4 coordinates, P1's side)

Each place answers the same four questions: what moves in the one wind, what lights at dusk, what it sounds like and how gusts change that, and what it is at night. All motion follows WLD-10's lag rule (props τ 0.30 s, κ 0.35 unless stated) and the legibility floor. Pendulums are FND-6 springs driven by the drive r, never free sines.

| id | place | moves in the one wind | lights at dusk | loop and gust response | night state | implementation | prio |
|---|---|---|---|---|---|---|---|
| WLD-40 | **Weighstall** (96, 96) | The cream-and-sage awning (WLD-29, A ×1.2). The 7 m brass balance's pans tip slowly: a pendulum (ω 1.6 rad/s, ζ 0.08, ±4°, so the pan rims move ≈ 0.25 m) driven by r; buying swings them hard (heroes ITM-05 drives `Beam`, `PanL`, `PanR`). The dozing Rundling ball breathes (scale ±6%, 3.2 s). | The stall lantern #FFB86B (lamp pool 4 m), struck by the tide | `lp_weighstall` (chain creak, awning flap, chime) at −24 dB + 6 dB·g; **one wind-chime strike when g crosses 0.7** (≤ 1 per 8 s) | The Smugglers' Den sleeps at the four corners (4.1a), the lantern burns, the pans still tip | Economy part tags; a stall prop; the landmark emitter | P1 |
| WLD-41 | **The Muddy Lantern** (coaching inn, (106, 106); when placed) | The hanging lantern sign swings on a gust pendulum (ω 2.4 rad/s, ζ 0.12, ±12°); house smoke from its `smoke_point` | Windows (lantern pools) and the sign lantern, struck by the tide | A creak when g crosses 0.6 (≤ 1 per 6 s); 19:00–05:00 a **warm murmur, no words**, at −24 dB within 25 m | The one warm-lit building in the basin; its pool lights the road | Inn parts `Door`, `Sign` (heroes HER-07 request); a landmark emitter | P1 |
| WLD-42 | **Hale Spring set piece** (40, 40), the dell of r 14 m (E13) | **Flume:** a 0.3 m water sheet along the hollow-log flume (the prop's `Flume` path), a stroke texture scrolling at a constant 0.8 m/s, α 0.85, #5AA3A0 → foam #E8F0EC at the lip; **4 droplets/s at the outfall** (#D8EEF2, 400 ms, ballistic) making 0.1 → 0.4 m rings on the pool. **Waterwheel at 6 rpm** (0.628 rad/s × fx_time, constant), 8 paddles, **one drip per paddle at the top of its arc** (0.8/s, falling 0.6 m). Reeds sway (WLD-14). By day **warm sparkles** rise off the water (6/s, #FFF1C8 HDR 1.2, 0.4 m over 1.2 s, ≤ 12 alive). The pool is pond mode with cat's paws (WLD-18). | No lamps: moon glints on the flume sheet and the pool | **`lp_spring` at the wheel** (−20 dB, the top-ranked landmark emitter); the dell's ramps carry it | **The night-ambush site:** the Crow Field is awake (CRP-01); fireflies over the pool and dell; wading rings and bow wakes from anyone crossing (WLD-20, **P0**) | Spring prop parts `Flume`, `Wheel`, `Outfall`; 1 draw for the water sheets (flume and the seams' sluices share it); FxSprites | **P0** |
| WLD-43 | **Standing Ring** (158, 158) | The tree ring 14–19 m out (WLD-14); the stones stand still | Nothing lit. At night the standing stones' carved cup-and-ring marks glow in step with CRP-01's Cairnwake lichen glow (#E8E29A, emission 0.4, breathing ±0.1 at 0.25 Hz) | `lp_standing_ring` (low hum, gravel shifting) at −24 dB by day, **swelling +6 dB at night** over the 8 s bed crossfade; it dips −2 dB at gust peaks (the wind masks it) | Golden hour throws long stone shadows across the ring floor (WLD-01); at night the ring glows and hums, and it never sleeps | Prop emission keyed to `atm_day.y`; a landmark emitter | P1 |
| WLD-44 | **Charcoal Clamps** (60, 176) and **Collier's Hut** | **Low, wide smoke seeping from the turf seams:** 8 seam points, one StreamFx puff per 600 ms per seam (0.6 → 2.4 m, rise 0.25 m/s, α 0.16, life 6 s), wind term ×1.5, so it flattens into a low downwind sheet readable as a landmark silhouette at 46 m. α ×0.5 in Busy, ×0.25 in Brawl. The Collier's Hut adds house smoke from its chimney. | **Ember seams** #E07A2A on the mound (emissive cracks: HDR 1.2 at night, 0.4 by day, flicker 0.85 + 0.15·n(3t)); the clamp fire; the hut's window | `lp_charcoal` at the mound (−22 dB); crackle +3 dB·g | Sootcoats asleep around the banked fire (4.1a); seams glow; smoke turns #6E6A75 | Stream region (economy budget, 8 × 10 = 80 sprites per clamp, the 2 nearest clamps only); prop emission | P1 |
| WLD-45 | **Turnip Patch** (32, 124) and **Crow Field** (around the spring) | Turnip leaves sway (bush parameters); scarecrow coats (cloth); **hay strands lifted off the crow-picked haystack**: 6–10 straw cut-outs (0.25 m, #C9A85A) when g crosses 0.6 (≤ 1 per 6 s per stack), carried 3–6 m downwind and settling over 2 s | The turnip-lantern heads (CRP-01, #FFC46B, through drilled holes, never a face) | Straw rustle and crow caws while the field is awake; rustle +4 dB·g; the pole creak while it sleeps (4.1a) | The Turnip Patch slumps with a crow on each head; the Crow Field gets up and walks | Haystack prop point; FxSprites cutout | P1 |
| WLD-46 | **Gold Seams** (main (18, 166), natural (80, 176)) | The windlass bucket rope swings (ω 2.0 rad/s, ζ 0.1, ±6°); the sluice runs a 0.15 m water sheet with 2 droplets/s at its foot | **Two hook lanterns** (#FFB86B, 3 m pools) that swing on pendulums (ω 3.0 rad/s, ζ 0.15, ±10°); their pools sway with them | A windlass creak when g crosses 0.7 (≤ 1 per 8 s); **`lp_mine_night`** (lantern hiss, slow drips) 19:00–05:00 | Lanterns burn; the adit mouth is a warm dark | Seam parts (economy); shares WLD-42's water-sheet draw | P1 lanterns, sluice / P2 `lp_mine_night` |
| WLD-47 | **Drystone Folds** (88, 172) | Grass in the wall gaps (tuft density ×1.3 along wall bases); **a wattle hurdle propped in the fold gap rocks ±3° and knocks against the wall** when g crosses 0.7 (a wood knock at −24 dB, ≤ 1 per 6 s) | Nothing; the awake Cairnwakes' marks glow at night (CRP-01) | A quiet gravel-shift hum (`lp_standing_ring` at −30 dB, low-passed) when visible | An empty fold: no sheep, the stones keep it, awake and glowing | Hurdle prop on the bush-sway path | P2 |
| WLD-48 | **The ponds** (40, 100), r 5 m | Reeds sway; **cat's paws** race across the downwind half (WLD-18); the geese (4.5a) | Moon glints; fireflies (WLD-08) | `lp_pond` (−24 dB); honks as event one-shots | Geese asleep on the water, fireflies along the shore | Pond mode water; the critter MultiMesh | P1 |

---

## 5. Time of day

### 5.1 Keys (Greenvale; other biomes apply offsets)

| key | name | sun colour | sun energy | moon energy | ambient | amb. energy | depth-fog colour | saturation | contrast | shadow α (owner) | cloud strength | glow |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00:00 | Midnight | — | 0 | 0.38 | #3B4A80 | 0.50 | #1E2648 | 0.94 | 1.04 | 0.32 (moon) | 0.12 | 0.85 |
| 04:30 | Pre-dawn telegraph | — | 0 | 0.36 | #45508A | 0.53 | #2A3156 | 0.96 | 1.03 | 0.28 (moon) | 0.12 | 0.85 |
| 05:20 | Sun wakes | #FFA88A | 0 | 0.30 | #5A5A92 | 0.60 | #5A5A86 | 0.98 | 1.02 | 0.10 (moon) | 0.11 | 0.82 |
| 05:40 | Dawn swap | #FFA88A | 0.24 | 0.20 | #6A6496 | 0.62 | #8C7FA8 | 1.00 | 1.02 | 0.00 (swap → sun) | 0.10 | 0.80 |
| 06:20 | Moon sets | #FFB38A | 0.60 | 0 | #8E8AB8 | 0.56 | #D8A898 | 1.06 | 1.03 | 0.40 (sun) | 0.20 | 0.76 |
| 06:30 | Dawn | #FFB38A | 0.72 | 0 | #8E8AB8 | 0.55 | #E8B7A0 | 1.08 | 1.03 | 0.45 | 0.22 | 0.75 |
| 08:00 | Morning (match start) | #FFE7C4 | 1.00 | 0 | #9DB3D6 | 0.55 | #CFE3F0 | 1.08 | 1.02 | 0.60 | 0.30 | 0.70 |
| 12:00 | Noon | #FFF4E2 | 1.12 | 0 | #A6BAD8 | 0.58 | #D6E6F2 | 1.06 | 1.02 | 0.62 | 0.32 | 0.70 |
| 16:30 | Golden telegraph | #FFC98A | 1.05 | 0 | #9C9CC8 | 0.52 | #F2D3A8 | 1.12 | 1.05 | 0.66 | 0.30 | 0.72 |
| 17:40 | Sunset (Clear variant, §5.4) | #FF9A5C | 0.72 | 0.06 | #8A7FB4 | 0.54 | #E89A7A | 1.12 | 1.05 | 0.50 | 0.26 | 0.75 |
| 18:15 | Dusk swap (blue hour) | #FF8A5C | 0.24 | 0.24 | #4E5A9A | 0.68 | #3A4478 | 1.00 | 1.03 | 0.00 (swap → moon) | 0.12 | 0.80 |
| 18:40 | Sun gone | — | 0 | 0.32 | #45528E | 0.66 | #2A3360 | 0.96 | 1.04 | 0.20 (moon) | 0.12 | 0.82 |
| 19:30 | Night | — | 0 | 0.38 | #3B4A80 | 0.55 | #1E2648 | 0.94 | 1.04 | 0.32 (moon) | 0.12 | 0.85 |

Moon colour #8EA6FF throughout. Tonemap Linear or Reinhard (white ≈ 1.5); re-tune if it changes.

**Why these numbers (the night has no dip).** Illuminance proxy E(h) = Y(sun)·e_sun·sin(el_sun) + Y(moon)·e_moon·sin(el_moon) + Y(ambient)·e_amb, with Y = linear Rec.709 luminance:
- noon ≈ 1.20; midnight ≈ 0.157, which displays at ≈ 40% of noon (world target 35–45%);
- **the lowest point anywhere in the night is ≈ 0.151 (19:07), 96% of midnight.** Revision 1's 18:15 key fell to ≈ 0.063, darker than midnight, during the tide and the ignitions;
- with the unit fill (WLD-06), units display at ≥ 0.60 of noon at every hour (lowest ≈ 0.603 at 17:20; 0.61 at 00:30; 0.63 at 18:15; 0.64 at 05:40).

These are estimates; the §9 capture test is the authority, and the fill's 0.65 is the tuning knob.

### 5.2 Derived channels

bump(a, b, c) = smoothstep(a, b, h) × (1 − smoothstep(b, c, h)).

| channel | definition |
|---|---|
| daylight | smoothstep(5.7, 7.0, h) − smoothstep(17.0, 18.25, h) |
| night | clamp(1 − smoothstep(5.0, 6.2, h) + smoothstep(18.0, 19.2, h), 0, 1) |
| golden | max(bump(16.4, 17.3, 18.1), 0.6 × bump(6.0, 6.7, 7.6)) |
| blue hour | max(bump(17.9, 18.25, 18.8), bump(5.2, 5.6, 6.0)) |
| unit fill (`atm_fill.a`) | 0.65 × (1 − daylight) |
| shadow owner | sun for 05:40 ≤ h < 18:15, otherwise moon; the swap happens only while both opacities < 0.02 |
| dew | bump(5.67, 6.5, 8.0) (WLD-35) |

### 5.3 The dusk and dawn beat sheet (cross-doc; T0 = 18:00:00 or 06:00:00 = the tide core at the focus)

Times are game-time ms at 1× relative to T0 (they scale with game speed). **One downbeat, then a cascade:** the four downbeat elements coincide on purpose, and everything else is staggered after them.

**Dusk**

| t (ms) | beat | owner |
|---|---|---|
| −30,000 (16:30) | golden-hour telegraph begins; the HUD clock's golden rim glows | WLD-02, HUD-07 |
| −13,000 … −300 | the tide front locks at the map's east edge (the time depends on where the focus is) | WLD-03 |
| −4,000 | bed crossfade starts (8 s, equal power); MUS-01's low-pass sweep starts (8 s) | WLD-32, MUS-01 |
| −1,800 | `st_dusk` starts: the curlew | WLD-04 |
| −1,400 | the tide core enters the left edge of the default view; lamps and torches strike as it passes | WLD-03, 05 |
| −90 | the HUD clock's inner ring starts its 30° clunk | HUD-07 |
| **0** | **Downbeat:** the bronze hum onset; the core at the focus; the clunk's tick; MUS-01's filter at mid-sweep; the beds at equal power. The sim flips `is_day()`, starts the 3.2 s sight ease and reaches the camps' sleep times | WLD-04, 03, HUD-07, MUS-01, sim |
| +150 … +4,000 | BLD-19's window cascade (P2; otherwise windows strike with the tide) | BLD-19 |
| +400 … +3,400 | POR-02's portrait lantern lerp (3 s) | POR-02 |
| 0 … +6,000 | night camps settle one by one on their own signals (4.1a); the Crow Field rises and CRP-01's crows lift off | WLD-07, CRP-01 |
| +1,400 | the core leaves the right edge of the default view | WLD-03 |
| +3,200 | the sight ease is complete; the stinger ends | sim, WLD-04 |
| +5,000 (18:15) | the moon takes the shadows; the night-side term fades out over 18:15–18:30 | WLD-01, 03 |
| +10,000 (18:30) | heroes strike their lanterns (hashed 0–600 ms); flowers begin to close (12 s stagger) | WLD-06, 15 |
| +20,000 (19:00) | fireflies and moths appear; the inn murmur begins | WLD-08, 41 |

**Dawn**

| t (ms) | beat | owner |
|---|---|---|
| −30,000 (04:30) | pre-dawn violet lift; mist rolls in (50% of dawns, or after rain) | WLD-02, 12 |
| −10,000 (05:30) | heroes snuff their lanterns; fireflies are already gone (05:00) | WLD-06, 08 |
| −6,700 (05:40) | the sun takes the shadows; dew begins | WLD-01, 35 |
| −4,000 | bed crossfade and MUS-01's filter return start | WLD-32, MUS-01 |
| −2,000 | `st_dawn` starts: the blackbird | WLD-04 |
| **0** | **Downbeat:** the bronze bowl tone; the first-light core at the focus; the clunk; the filter centre; equal-power beds. The sim flips to day | as dusk |
| 0 … +6,000 | night camps rise (4.1a); the Crow Field slumps and CRP-01's crows land back over 1.5 s; flames die as the core passes them | WLD-07, CRP-01, 03 |
| +1,000 … +4,000 | kingdom storks clatter (hashed per stork) | WLD-37 |
| +5,000 (06:15) | flowers begin to reopen; the day-side term fades | WLD-15, 03 |
| +50,000 (08:30) | dew trails are dry and cleared | WLD-35 |

### 5.4 Per-night variation ★ (so dusk N never looks like dusk N + 1)

- **Sunset by the day's weather.** The 17:40 key uses the state with the most sim time between 12:00 and 17:40 that day (from the schedule, so it is deterministic):
  - Clear or Breezy: sun #FF8A50, saturation 1.15 (a rich sunset);
  - Overcast, Drizzle, Rain or Mist: #E8A890, saturation 1.02, energy ×0.85 (pale);
  - Distant storm: #FF9A5C, contrast 1.08, with the storm's sun breaks.
- **Moon phase.** It advances one eighth each night, from a seeded start: phase p_n = (n + seed) mod 8, illumination i = (1 − cos(2π·p_n/8))/2.
  - The moon *light* never changes (the readability floor holds on a new moon).
  - Moon glints on water (WLD-19), moon rims (WLD-06) and Tormai mirror glints (WLD-37) scale by 0.85 + 0.30·i (±15%).
  - `atm_moon_phase` is published for the HUD day clock's crescent (HUD-07's crescent hand; the bible's Horizon Ribbon token).

### 5.5 Dew (row WLD-35)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-35 | **Dawn dew and dew trails ★** | 05:40–08:00 (the dew channel) | **Dew:** grass tips (top 30% of each tuft) carry a capped water glint, pow(spark, 24) × dew × (1 − trail), #F4FAFF, **HDR ≤ 1.3, ≤ 2% of grass pixels**. The terrain's grass layers get a faint +4% sheen.<br>**Dew trails:** seen units walking through grass (the WLD-30 poll, Bresenham) write world A = 255. Trails are darker (×0.94), sheen-less, and knock the dew off tufts. They dry between 07:30 and 08:30 (shader), and the CPU clears A once at 08:30 (one upload). **Morning scouting routes read honestly on the ground**, then vanish. | `grass.gdshader` and terrain; `wear.gd` writes A during 05:40–08:30. | 1 sample (already bound) | P1 |

---

## 6. Weather states (Greenvale)

| state | weight | duration | wind base | gust speed (m/s) | cloud cover | wetness target | streaks | mist | notes |
|---|---|---|---|---|---|---|---|---|---|
| Clear | 0.40 | 150–300 s | 0.25 | 5.0 | 0.25 | 0 | none | 0 | always for the first 180 s of a match |
| Breezy | 0.22 | 120–240 s | 0.55 | 6.2 | 0.35 | 0 | none | 0 | whooshes ≥ 12 s apart; flags stand out |
| Overcast | 0.12 | 120–240 s | 0.35 | 5.4 | 0.70 | 0 | none | 0 | sun breaks roam (WLD-09) |
| Drizzle | 0.12 | 90–180 s | 0.40 | 5.6 | 0.80 | 0.7 | drizzle (3 m/s) | 0 | first drops 8 s before streaks |
| Rain | 0.04 | 60–120 s | 0.50 | 6.0 | 0.85 | 1.0 | rain (6 m/s) | 0 | only after Overcast or Drizzle |
| Mist | 0.06 | 120–200 s | 0.10 | 4.4 | 0.45 | 0.2 | none | 0.9 | may only start between 02:00 and 07:00 |
| Distant storm | 0.04 | 90–150 s | 0.60 | 6.4 | 0.75 | 0 | none | 0 | only after Overcast; off-map flashes and thunder (WLD-36) |

**Rules:**
- No state repeats twice in a row, except Clear.
- Transitions: wind 10 s, clouds 25 s, wetness rising 40 s and drying 90 s, mist 20 s. All are smoothsteps of sim time.
- The schedule comes from its own seeded RNG, indexed by sim time (F3). Every client, observer and replay sees identical weather.
- **Weather is visual only.** Sight, speed and combat never change.

---

## 7. Our own twists (what WC3 did not have)

Each twist either reports a real game fact or gives the world a body. None of them changes an outcome.

1. **Nightfall tide and first light (WLD-03).** Night sweeps across the battlefield as a soft ink front at 15 m/s, lighting lamps as it passes. It crosses your view in about three seconds, with its core on your focus at the exact moment of dusk, and the minimap shows the same front.
2. **One downbeat (§5.3).** The stinger's bronze hum, the tide core, the clock's clunk and the music's night filter land together, and everything else cascades after them.
3. **Golden hour as a telegraph (WLD-02).** Thirty seconds of warm, long-shadowed light announce dusk.
4. **Nights that differ (§5.4).** Sunsets follow the day's weather, and the moon waxes and wanes across a match.
5. **Lit units on a darkened world (WLD-06).** A view-facing fill, without a single light node, keeps units at ≥ 60% of noon while the world sits at about 40%.
6. **The hero's lantern (WLD-06).** At night heroes carry a real little lantern that swings as they walk, and the pool of light sways with it.
7. **The lantern map (WLD-F4, 05).** Hundreds of lamps, fires and windows light the ground and the units walking past them for the price of one texture.
8. **Snore rings count the camp's tier (WLD-07).** One, two or three rings per exhale, outlined in the camp's band colour, and readable by count.
9. **Sleepers sleep like themselves (4.1a).** Sootcoats nod off around their banked fire and jerk awake; scarecrows slump on their poles in stop-motion with a dozing crow on each head; the stones never sleep.
10. **Wind with inertia (WLD-10).** Grass bends first, trees follow a third of a second later, spring past rest and settle. Flags agree on the direction everywhere.
11. **Cat's paws (WLD-18).** Each gust front skates across the ponds you are looking at.
12. **Seeds ride the gusts (WLD-13).** Meadow seeds lift only where a front passes, so the gust itself becomes visible.
13. **Fireflies fall into step (WLD-08).** They blink at random at dusk and synchronise into rolling waves by midnight; a fight breaks the spell, and a marching army kicks up a wake of light.
14. **Moths at the lamps (WLD-08).** Night air life belongs to the light.
15. **The world flinches (WLD-17).** Big impacts flatten a ring of grass that races outward, trees lean away in a delayed wave, and storks take off.
16. **Commands press the world (WLD-16, 17).** A move order presses the grass where it lands; a new foundation bows the grass outward and sends the hares running.
17. **Dew trails (WLD-35).** Who walked the meadow at dawn is written in the dew until mid-morning.
18. **Desire paths (WLD-30).** Mining trails and army routes wear into the grass over the match.
19. **Puddles on trodden paths, muddy prints (WLD-11).** Rain collects where armies walked, and splashing through leaves prints.
20. **Bird shadows and the kites (WLD-23).** Flock shadows skim over armies; after a slaughter, red kites circle and their shadows sweep the field.
21. **Aftermath (WLD-24).** After a battle the world holds its breath, the soldiers lower their weapons, and then a single bird calls from where it happened.
22. **The cartographer's reveal (WLD-26).** New ground is inked onto the map as you scout, under a sea of drifting cloud with parallax.
23. **If it moves, you can see it (WLD-27).** Remembered areas are still, faded and paper-grained; trees felled out of sight stay standing in memory.
24. **Battlefield bloom (WLD-31).** Where stains fade, flowers come up.
25. **Storm-lit (WLD-36).** A storm off the map flashes through the cloud gaps, and the thunder arrives late, from its bearing.
26. **A place, not a meadow (§4.10).** The balance pans tip in the wind, the inn sign creaks, the waterwheel drips from every paddle, the clamps seep smoke, the Standing Ring hums louder at night, and a hurdle knocks against the fold wall.
27. **The ground is the sky (pillar 1).** Every sky event lands on the ground, where a camera that never sees the horizon actually looks.

---

## 8. Anti-patterns (rejected in review)

**Honesty and gameplay**
1. **The world as a radar.** Critters fleeing, birds taking off, footpaths or dew trails forming, trees vanishing, grass clearing, lantern pools appearing or sounds playing because of something the local player cannot see. Every reaction goes through `visible_at()`. **The only exception is the sim-driven Sparrow Roost flush**, drawn equally for every player who has the area explored.
2. **Weather that changes play.** No sight, speed or accuracy changes from rain, mist or storm.
3. **Atmosphere writing sim state or using `World.rng`.**
4. **Atmospheric cues that sound like gameplay alerts.** No horns (the Levy Horn), no gong strikes or rolls (the clans alarm), no bells in stingers or ambience.

**Readability**
5. **Darkness as difficulty.** Pitch-black nights, heavy vignettes, "realistic" moonlight, or a twilight darker than midnight.
6. **Weather that hides the game.** Rain sheets, fog walls, full-screen haze, mist over rings.
7. **Lens fakery.** Raindrops on the "lens", chromatic aberration, film grain, lens flares, tilt-shift.
8. **Bloom on the environment.** Glowing grass, water or mist; god rays. Only flames, sparks, fireflies and capped glints bloom.
9. **Critters that read as units.** Team colours, relation-coloured rings, unit-sized animals or commands on wildlife.
10. **Clutter in lanes.** Grass on roads or footprints, tall tufts that hide feet, flower confetti across the whole map.
11. **Sub-pixel juice.** Motion under 1.5 px at the default camera (0.01 m chew bobs, 0.015 m leaf flutter, 0.012 m rain): it costs ALU and reads as noise or nothing. Make it a value change, make it toy-sized, or cut it.

**Feel**
12. **The screensaver forest.** Every tree swaying in phase, uniform sine wind, or every layer bending in the same frame with no lag or recoil.
13. **Day/night as a dimmer switch,** or as a scanline: a single global lerp, or a band that crosses the screen in a second.
14. **Shadows that flip or face the camera.**
15. **Ceremony every dusk.** Stingers over 5 s, screen flashes, banners, or the same mist every dawn.
16. **Wallpaper ambience.** Loops shorter than 45 s, audible seams, the same bird call twice in a row, gust whooshes every 6 s, ambience that ignores the camera.
17. **The generic pastoral cast.** Sheep, rabbits, frogs, songbirds, butterflies and fish scattered at density over any map; a click-spam sheep gag (WC3's signature). Our cast is the canon's: hares, geese, fireflies and, later, the roost.
18. **Generic AI-slop atmosphere.** Stock rain sheets, uniform blue filters, glitter motes, one easing curve, and props (torch, brazier, lamp post) that belong to no place. Every row here ties its motion to a physical idea and every landmark gets its own life (§4.10).
19. **Letters over sleepers.** No "z" or "Zzz" anywhere; the closed eye and snore rings carry sleep.

**Engine**
20. **Rate × time.** `fx_time` or `hour` multiplied by a wind- or weather-dependent rate, in a scroll or a wave. Integrate scrolls on the sim clock; use fixed frequencies.
21. **Shader `TIME`.** It ignores pause and wraps every hour.
22. **A node per thing,** or a node moved in `_process` under physics interpolation. Use the lantern map, StreamFx, MultiMesh and static wrap volumes with global origins.
23. **Instance uniforms on MultiMesh props.** They apply to every instance; compute per-prop state in closed form from the origin.
24. **Lazy builds and per-pixel GDScript loops.** No chunk built on first sight, no `set_pixel` re-bake at 1 Hz; patch dirty bytes in mirrors.
25. **`Decal`s and depth-texture tricks** that break Compatibility.

**IP**
26. **WC3 signatures.** No wolf howl at dusk, no rooster at dawn, no owl as a night signature, no WC3 ambience loops, tileset textures, weather sprites or critter designs, no exploding critter, no click-spam sheep. Generic conventions are fine: blue nights, critters, shoreline foam.
27. **Banned terms in ids.** No `hearth`, `wisp` or any other term in `tools/ip/banned_terms.txt` in a stream region, def hint, prop, light class or audio id (house smoke, `smoke_point`, house-light pool, hay strands, steam curls).

---

## 9. Budgets, presets and verification

**Budget** (300 units, about 150 on screen, night, drizzle, mid-range GPU at 60 fps)

| Resource | Budget |
|---|---|
| GDScript CPU for the domain (Atmos, scroll integration, Life, Lanterns, wear and dew polls, ambience, minimap feed) | ≤ 0.6 ms average, ≤ 1.0 ms peak (excluding load) |
| Draw calls added | **≤ 15:** grass 2 (B only above 29 m zoom) + 2 depth-prepass draws for the alpha-scissor grass (Forward+); air 1 (fireflies, seeds, moths); rain 1; mist 1; critters 1; birds 1 + bird shadows 1; hero lanterns 1; map skirt 1; water sheets 1 (flume and sluices); bloom 1 (P2). The Firefly Jar's draw is counted by heroes. **All atmosphere geometry casts no shadows: 0 shadow-pass draws.** |
| Grass | High ≤ 7.2k instances / ≈ 86k vertices; Medium ≈ 4.6k; Low ≈ 2.3k; 0 ms build |
| Transparent overdraw | mist 2 layers over lowlands; rain ≤ 900 streaks at 1.25 px |
| Samplers | ≤ 7 atmosphere samplers per material (terrain 7 + combat's scar map) |
| Texture uploads | fog: one 36 KB L8 per upload at the fog rate (unchanged); lantern 147 KB per change, ≤ 4/s; world 147 KB at 1 Hz (≤ 10 Hz while reveal cells are active); ground 147 KB per footprint change; minimap ≤ 64 dirty pixels per felled tree |
| Lights | Forward+: 4 house-light `OmniLight3D` inside the 12-light LightBudget. Compatibility: LightBudget ≤ 8 in total and ≤ 8 per terrain chunk; house lights off |
| Audio | ≤ 6 beds + 1 stinger (2D); the world pool of 8 at priority 20 (6 loops, 2 one-shots) |
| Load | ≤ 150 ms for derived maps |

**Quality presets**

| Item | Low (Compatibility, container) | Medium | High | Juice level 0 (competitive) |
|---|---|---|---|---|
| Shader tier (`atm_quality`) | Low | Medium | High | as preset |
| Grass density / tramplers | 0.7 per m² / 8 (none beyond 25 m) | 1.4 / 16 | 2.2 / 24 | 1.4 / 8 |
| Fireflies / seeds / moths | 32 / 48 / 0 | 64 / 96 / 12 | 64 / 96 / 24 | off / off / off |
| Rain streaks (drizzle / rain) | 220 / 400 | 350 / 650 | 450 / 900 | off (wetness and rings stay) |
| Mist | lower layer only | both | both | α ×0.5 |
| House-light `OmniLight3D` | 0 | 2 | 4 | 0 |
| Critters | all 14, reactions on | all | all | all; click gags off |
| Flights | ≤ 32 birds | ≤ 48 | ≤ 64 | sim-triggered only (the roost flush is information) |
| Shock rings | grass only | full | full | off |
| Tide band | on | on | on | off (staggered ignition) |
| Cloud shadow strength | ×1 | ×1 | ×1 | ×0.6 |
| Places (§4.10) motion and loops | on | on | on | on, no hay strands or sparkles |
| Desire paths, dew trails, sleep glyphs and rings, fog smoothing, tree memory | on | on | on | on (they are information) |

**Verification** (add with the implementation; no test may be skipped)

1. **`tests/unit/test_atmos_determinism.gd`:** `battle_setup` plus 30 s of mining, with Atmos on at High, a forced Drizzle → Mist schedule, critters on and injected critter clicks; then the same with `World.visuals = false`. The per-second (id, pos, hp) hashes and the final `world.rng.state` must be identical.
2. **`tests/unit/test_time_of_day.gd`:** evaluate the director every 0.001 h over 24 h.
   - No output jumps more than 2% per step, except the light direction while its shadow α < 0.02.
   - The shadow direction stays within 55° of screen-up whenever shadow α > 0.05; the owner swaps only while both opacities are < 0.02.
   - **E_world(h) ≥ 0.95 × E_world(00:00)** for every h in the night (§5.1).
   - The director's day/night agrees with `DayNight.is_day()`; `hour` never steps back across a pause and resume.
3. **`tests/unit/test_atmos_scroll.gd` (new):** 30 minutes of sim time with a forced schedule through every state and wind turn.
   - Each published offset's per-second displacement equals d(t)·v(t) within 1e-3 m/s at every tick (no t·d′ term); offsets stay inside their periods.
   - The cloth crossfade's frequencies stay in [1.4, 3.0] Hz.
   - The firefly blink rate stays within ±1% of 1/2.2 s at every hour.
4. **`tests/unit/test_atmos_framerate.gd`:** drive `_process` with dt sequences at 30, 60, 144 and 240 Hz and with jittered dt, up to the same sim time.
   - Wind direction and scroll offsets are identical (closed form and tick-integrated).
   - Ambience gains and carried-light intensities agree within **2e-3**; critter poses are identical (t0 snapped to the 10 Hz tick).
5. **`tests/unit/test_world_fog_honesty.gd`:** an enemy army walks through a meadow with hares, a goose pond, a nest tree and a sleeping camp, all inside the local player's fog, at 06:00 (dew). It also chops a tree and builds a farm. Expected:
   - 0 critter state changes, 0 flights, 0 glyphs, 0 rings and 0 shocks;
   - 0 changed wear and dew texels; the felled tree is still drawn; no footprint clearing and no lantern change until the player sees the area;
   - **exception:** a Sparrow Roost flush (SLICE+) in an explored area is drawn, and in an unexplored one it is not.
6. **`tests/playtest/atmos_tour.gd`** (lavapipe and opengl3): screenshots at 06:15, 08:00, 12:00, 17:10, 18:00 (core mid-screen), 21:00 and 00:30, for Clear, Overcast, Drizzle and Mist.
   - **Night readability at 00:30, 18:15 and 05:40:** Rec.709 luma of final sRGB pixels; the units-layer mask comes from a second, units-only render. Units ≥ 0.60 × the 12:00 capture; the world 0.35–0.45 ×.
   - Team chroma on the 12 colours ≥ 0.7 of noon; hue shift under a maximal lantern pool ≤ 8°.
   - **Fireflies:** ambient core vs Firefly Jar core side by side at 00:30, CIEDE2000 ΔE ≥ 20.
   - **Rings in Mist:** selection-ring and Levy-ring contrast ≥ 90% of the Clear capture.
   - **Zoom:** meadow grass coverage at 46 m ≥ 50% of the 28 m capture (no bald zoom-out); no visible seam at the lattice handoff (diff across r = 45 m below the noise floor).
7. **`tests/playtest/bench_atmos.gd`** (real GPU): 300 units at 00:30 in drizzle, 40 light sources, 14 critters, 3 flights and 2 shocks/s.
   - Domain CPU within budget; 60 fps; draw calls rise by ≤ 15.
   - Shadow-edge swimming captured at 17:00 (rotating sun): if visible, raise `soft_shadow_filter_quality` or the atlas size before adding PCSS.
   - A 2-hour soak: offsets bounded, no stepping in sway, fireflies or cloth.
8. **`tests/unit/test_shader_compile.gd`** (shared with economy): every atmosphere shader compiles on headless, opengl3 and lavapipe at all three `atm_quality` tiers; per-material sampler counts are at or below §3's list.
9. **Ids:** `python3 tools/ip/check_banned_terms.py data assets` passes after the world's ids are seeded (`house_smoke`, `smoke_point`, audio ids, prop ids).
10. **Legibility lint:** a static check reads the motion and size constants of §2's floor and fails any below its minimum.

**Files touched (checklist)**
- **New in `src/world/`:** `atmos.gd`, `weather.gd`, `lanterns.gd`, `world_maps.gd`, `grass.gd`, `life.gd`, `flocks.gd`, `air_fx.gd`, `mist_fx.gd`, `weather_fx.gd`, `wear.gd`, `camp_fx.gd`, `ambience.gd`.
- **New shaders in `src/world/shaders/`:** `world_common.gdshaderinc`, `foliage.gdshaderinc`, `cloth.gdshaderinc`, `grass.gdshader`, `air.gdshader` (+ `AIR_ANCHORED`), `rain.gdshader`, `mist.gdshader`, `bird.gdshader`, `critter.gdshader`, `prop.gdshader`, `water_sheet.gdshader`.
- **New elsewhere:** `src/fx/light_budget.gd`, `src/fx/world_memory.gd`; `src/ui/minimap_overlay.gdshader`; `data/biomes.json`, `data/time_of_day/greenvale.tres`.
- **Changed:** `day_night.gd` (director, Moon light, `hour` from `sim_time`); `terrain.gdshader`, `tree.gdshader`, `water.gdshader`; `terrain_builder.gd` (skirt); `doodads.gd` (tree memory); `fog.gd` (display bytes, double buffer, new-cell list, 3.2 s sight ease); `world.gd` (Atmos and Life nodes); `minimap.gd`; `selection.gd` (critter pick and clicks); `unit.gdshader` (include, `night_lift`); `map_data.gd` (props, landmarks, shallow water, camp fields, `sun_axis`); `creeps.gd` (sleep hooks, facing); `events.gd`, `settings.gd`, `project.godot` (`[shader_globals]`); `docs/architecture.md` §5, §7 and §8 in the same commit as the hooks.

---

## 10. Assets this doc needs (all original; procedural fallbacks keep "runs without art")

**Textures (packed per WLD-F2):**
- `atm_noise_tex` RGBA 256²: gust fronts, flicker, brush edge, the painted cloud mask;
- `atm_detail_tex` RGBA 256²: paper grain, mist noise, foam strokes, leaf-gap speckle;
- `atm_ripple_tex` RGBA 128² (rain rings, mipmapped);
- water stroke normals (two maps in one RGBA 256²), the flume stroke strip 64 × 256;
- grass and flower tuft atlas 1024² (4 + 4 variants);
- FxSprites cells: the closed-eye glyph, the snore ring, the honk glyph, a feather, a straw strand, a muddy print, chalk dashes (shared with CRP-02);
- rain streak 16 × 64.

Until these exist, `FastNoiseLite` seamless images stand in.

**Audio** (bible §9.7–9.8 ids, Seed Audio or CC0):
- beds and stingers: `amb_gv_day`, `amb_gv_night`, `st_dawn`, `st_dusk`, `amb_base_kingdom`, `amb_base_clans`;
- landmark loops: `lp_spring`, `lp_brook`, `lp_pond`, `lp_charcoal`, `lp_weighstall`, `lp_standing_ring`, `lp_mine_night`;
- sweeteners: `swt_birds`, `swt_wind`, `swt_night`;
- creeps and critters: `cv_sootcoat_sleep`, `cv_hare`, `cv_goose`, `cv_sparrows` (SLICE+);
- **world additions requested for the bible (§12):** `amb_rain_leaves`, `amb_rain_roofs`, `amb_rain_water`; `swt_gust_whoosh` ×4; `sfx_ignite_fwump` ×3; `sfx_water_plop` ×3; `lp_wading`; `lp_inn_murmur` (no words); `sfx_chime` ×3 (Weighstall and clans plates); `sfx_creak` ×4 (inn sign, windlass, scarecrow pole, hurdle knock); `sfx_stork_clatter` ×2; `sfx_thunder_far` ×3; `ui_quill_scratch` ×2; `swt_nightjar` ×2 and `swt_blackbird` ×2 (the first bird).

No WC3 audio, no wolf howl, no rooster, no owl signature, no horns or gongs in atmospheric cues.

---

## 11. Open questions

**Closed in revision 2:**
- *Compatibility `Environment` adjustments:* supported (spike 4.7.2); the `atm_grade` fallback is deleted.
- *Shallow water:* the Hale Spring pool is canonically walkable (neutrals §5.8, E13), so WLD-20 is P0 there.
- *Sleep glyph shape (heroes open question 7):* the closed-eye glyph plus tier-counted snore rings (WLD-07). The heroes doc should mark it closed (§12).

**Still open:**
1. **Cloud shadow route.** Can the shared `light()` read a fragment-written varying in 4.7.2 at acceptable cost on llvmpipe, or do we use the albedo fallback? A 1-day spike.
2. **Other fords** (`MapData.water` = 2 outside the spring) need gameplay and pathing sign-off and a test-map edit.
3. **Weather in competitive play.** Juice level 0 keeps wind, clouds and wetness and drops streaks and mist. Confirm with experienced players.
4. **More wildlife.** Sheep, frogs, butterflies, songbird perches or fish need neutrals' sign-off and must respect its density cap (≤ 14 per map).
5. **Slice-plan vs neutrals camp list.** Slice-plan §1.8 lists 9 camps with the Turnip Patch sleeping by day; neutrals §1.5 and §3.6 list 11 with the Collier's Hut and the Turnip Patch sleeping at night. This doc follows neutrals; the slice-plan table needs updating.
6. **The 22° dusk sun floor** versus the bible's 12–20° (§12 request): 22° keeps shadows ≤ 2.5× unit height.
7. **Window timing:** the bible lights windows at 17:45; this doc lights them with the tide at T0 (BLD-19 when it runs). The bible owner confirms.
8. **Day length.** This doc assumes 20 s per game hour (rules §13). Every beat is keyed in game time and scales; the stingers' sync offsets are in seconds and must be re-checked by ear if the cycle changes.
9. **`sun_axis` per map.** Map makers may rotate it; the up-screen shadow rule and the tide direction must both be kept.

---

## 12. Cross-doc contracts and requests

**Ownership**

| System | Owner | Users |
|---|---|---|
| Sleeping creep body (settle, per-family idles, the closed-eye glyph, snore rings, sleep sounds, clamp-fire banking) | world WLD-07 | heroes STS-06 (glyph), economy ECO-12 (glyph + 1 ring for napping workers), UI SEL-02 (glyph) |
| Creep family sleep props, startle, "!" / "‼", roar, leash, cleared | heroes CRP-01..04 | WLD-07 calls nothing; it reacts to the same signal |
| Hero lantern and carried lights | world WLD-06 | heroes def `fx.lamp` (tint, flicker) |
| `air.gdshader` and its `AIR_ANCHORED` variant | world WLD-08 | heroes ITM-03 (Firefly Jar) |
| LightBudget | world WLD-F4 | combat `impact_lights.gd`, economy `building_fx.gd` |
| WorldMemory ledger | world WLD-31 | combat CMB-30..32, economy BLD-16, ECO-11 |
| Flights (`Flocks.flush`) | world WLD-23 | economy ECO-29 (nest trees, storks), heroes CRP-01 (crows), neutrals' Sparrow Roost |
| Area beds, stingers, emitters, sweeteners, the aftermath trigger (`ambience.gd`) | world WLD-04, 24, 32, 33 | UI `mix_beds.gd` keeps the battle and march beds; the duck arbiter is UI AUD-01's |
| Minimap base and overlay | world WLD-34 | UI draws pips (including the sleeping state), pings and the trapezoid |
| Shock rings | world WLD-17 | combat (footfalls, siege, pots), economy (collapse, placement), heroes (Brace, crate, Wagon Ring, ultimates) |

**Requests to sibling docs** (each sibling applies them in its next revision):
- **Architecture:** `DayNight.current_hour()` = `hour_at(sim_time)`; `Fog` stores display bytes and exposes the new-cell list; the `[shader_globals]` list of §3, including the global samplers; the hooks of §2.
- **Rules and the sim (`fog.gd`, `creeps.gd`):** implement rules §13's 3.2 s sight change as a 96-tick ease from 18:00 and 06:00; set the sim facing toward the fire or camp centre at sleep; expose `Unit.sleep_schedule` and the camp fields.
- **Neutrals:** sign-off for any wildlife beyond the canon (§11.4); the `roost_flushed` signal when the Sparrow Roost lands.
- **Heroes:**
  - mark open question 7 closed (the closed-eye glyph and snore rings);
  - STS-06 spawns the closed-eye glyph (and, for slept units, a single uncoloured ring per 1.8 s);
  - CRP-02 calls `camp_fx.crumble(camp_id)` on a woken signal;
  - the Firefly Jar uses `AIR_ANCHORED` and publishes its disc to `atm_jar_0..1`;
  - add `fx.lamp` (bone, offset, tint, flicker) to the hero defs (Firewright #FFB46B, 7 Hz ±10%);
  - add to §2.7's render order: mist 5, bird shadows 11, air soft 38, rain 46, air additive 61.
- **Combat:** `scar_map.gd` registers `atm_scar_tex` as a global sampler (no `Atmos.bind`); the WorldMemory rows for pot scuffs and wrecks are merged (4.7a); shock eviction by remaining strength is adopted (WLD-17).
- **Economy:** this doc adopts `smoke_point`, `house_smoke` (region D, 36 slots), the steady ghost splat on fog-over, `lit` = `anim_b.z`, the `eco_rings` include (composited last; mist cuts it out), and the hall rubble, leaf litter and stump rows. ECO-12's napping glyph becomes the closed-eye glyph plus one ring. ECO-29's stork exposes its crown sub-part so WLD-37 can clatter and lift it. The construction rows (BLD-07 family) call `Atmos.shock(pos, 0.15)` on `construction_started`.
- **UI, camera and audio:**
  - set priority 20's "world caps" to the world pool of 8 (6 loops, 2 one-shots; the audio research's 4 is superseded) with WLD-33's stealing order;
  - WLD-24 ducks through `Audio.duck(&"wld_battle", &"Ambience", −5 / −8, 500, −1, 6000)` and `unduck`;
  - HUD-07's clunk starts at T0 − 90 ms so its tick lands on the downbeat (not on "the second note");
  - the crescent follows `atm_moon_phase`;
  - critter selection: ivory ring and rim, the info panel, no box selection;
  - the sleeping-camp pip state (WLD-34).
- **Art and audio bible:**
  - §1.5: dusk sun elevation 22° (readability), windows lit with the tide at 18:00;
  - §9.7: add the world audio ids of §10;
  - add the closed-eye glyph and snore ring to the glyph list (§7.8).
- **Slice plan:** update §1.8 to neutrals' 11 camps and schedules (§11.5).

---

## Critique log

### Revision 2 (2026-10-17): two reviews applied

**Verdicts.** Review A (canon and feel) found strong systems but called the doc "not ready to implement": it was written against a generic meadow instead of the project's canon, and several juice rows would have felt lifeless on screen. Review B (engine) found the approach sound and engine-aware, with one systemic blocker in the include (rate × time) and a set of majors on interpolation, MultiMesh uniforms, mist, grass and tiers. Every blocker and major is applied below, and the strongest missing features from both reviews are added.

**Review A: canon, feel and game design**

| # | sev | issue | resolution |
|---|---|---|---|
| A1 | blocker | Invented critter cast (sheep, rabbits, frogs, songbirds, butterflies, fish) at 80–100 density; never selectable; poke; a click-spam sheep gag | 4.5a rebuilt from neutrals §6: 6 hares, 4 geese, fireflies; Sparrow Roost SLICE+. Selectable through `selection.gd` with the info panel; 6 clicks / 3 s / 20 s cooldown; the hare's 2 thumps, 10 m bolt and 1.5 s freeze; the goose hisses at 2 m and nips cosmetically with a 3-feather puff and a honk glyph. Sheep, frogs, butterflies and fish cut (§11.4). The roost flush is the sanctioned fog exception (§2, anti-pattern 1, test 5). |
| A2 | blocker | Stacked "z" letters, a 1–3 difficulty scale, wrong hexes, a glyph under 10 px | WLD-07: one closed-eye glyph cell (≥ 10 px, head slot); tier as 1/2/3 snore rings per exhale (0.12 → 0.30 m, 0.6 m over 1.8 s `out_sine`, downwind), outlined in neutrals' band hexes, from `total_level`. Minimap pip at 60% value with a 4 px closed eye. Heroes OQ7 marked closed here; the heroes edit is requested (§12), not made, because that doc has a concurrent revision in progress. |
| A3 | blocker | Dusk horn duplicates the Levy Horn; owls; 3 s cap | WLD-04 adopts `st_dusk` and `st_dawn` (5 s); the hum or bowl onset is the downbeat on T0 with the core, the clunk and the filter (§5.3); the night first bird is a nightjar churr; no owls; cap 5 s; anti-pattern 4 bans horns, gongs and bells in atmospheric cues. |
| A4 | blocker | `hearth` and `wisp` in ids | Renamed throughout: `smoke_point`, house smoke / `house_smoke` (region D, 36 slots), house-light pool; the missing-feature "hay wisps" became "hay strands" and after-rain wisps became steam curls. Anti-pattern 27. |
| A5 | major | Heroes signal and contracts not merged | `creep_sleep_changed(u, asleep, reason)` with the six reasons; wake bullets and the chain deleted (CRP-02 owns them); `slump` added; schedule column; no extra hash; the facing hook, or a ±20° clamp. |
| A6 | major | One generic sleeper for all families | Table 4.1a: Sootcoat chin nods (18° over 2.5 s `in_sine`, 90 ms `out_back(2.0)` jerk); Tattiebogles slump on twos with no breathing and a −26 dB creak; Cairnwakes none; per-family camp sounds. |
| A7 | major | Night numbers don't close; untested 18:15 dip | Unit `night_lift` fill (#A9B8E8, 0.65 × (1 − daylight)); two overlapping lights with only the shadow owner swapping; keys re-tuned so the night never falls below 96% of midnight; the metric (Rec.709 luma of final sRGB pixels, units mask); targets units ≥ 60%, world 35–45%; tests at 00:30, 18:15 and 05:40. |
| A8 | major | The tide was a 1 s scanline, world-relative, with no front | WLD-03: a fixed 15 m/s; anchored so the core passes the focus at T0 in sim time; 4 m lead, 6 m core, 30 m night side; s = dot(xz, sun_axis); core term in the sketch; the same s_f(t) on the minimap. |
| A9 | major | Sight snap versus "the dark closing in" | Rules §13 already specifies a 3.2 s sight change; the sim implementation is requested (96 ticks). WLD-25 is asymmetric: concealment at once (min), reveal eased. |
| A10 | major | Sub-pixel juice | §2 legibility floor (heroes §2.6 clamp; ≥ 1.5 px rule). Leaf flutter became a ±6% value flicker (0.04 m vertex on High); chew and lily-pad bobs cut with their species; awake breathing left to CMB-05; branch offset raised to 0.06 + 0.10·w; rain at 1.25 px with α compensation; glyph ≥ 10 px; gag critters at toy scale. |
| A11 | major | No inertia or overshoot in foliage | WLD-10's lag and recoil per layer (τ, κ, Δ = 0.4 s), in the include and in `gust_at(xz, tau)`; smoke integrates over its age. |
| A12 | major | Grass melted on zoom-out | Zoom-scaled fade (1.25·d + 4 → 1.5·d + 4 m); far LOD beyond 45 m; a terrain grass tint. Implemented on the new lattice (B8). Deviation: 1 in 4 at ×1.5 instead of 1 in 3 at ×1.35, so the far lattice is an exact sub-lattice and the handoff is seamless. |
| A13 | major | Lake-scale water on 5 m ponds; the spring ignored; bible shore values | Body-size modes (WLD-18); ponds get cat's paws and the bible's 25% / 1 m wet band and #E8F0EC α 0.4 foam; WLD-20 unblocked and P0 at the spring; WLD-42 specifies the flume sheet, 6 rpm wheel, paddle drips and `lp_spring`. |
| A14 | major | Ambient fireflies camouflage the Firefly Jar | Ambient fireflies at #E8F07A HDR 1.3, core 0.04 m, halo ≤ 0.15 m; the jar keeps #D8FF6A HDR 2.0 with an owner halo; ambient fade near an active jar; mask limited to the ponds, the dell and nearby meadow edges; ΔE ≥ 20 test. |
| A15 | major | Generic pastoral, not Wether Downs | §4.10, one row per landmark (WLD-40..48); per-faction settlement beds; WLD-33 ranks landmark loops first. |
| A16 | major | Cross-doc requests not merged | Shock eviction by strength and the full caller list; ledger rows (hall rubble, leaf litter, stumps 1,024, pot scuff, wreck); `atm_scar_tex`; the ghost splat; `Flocks.flush`; `AIR_ANCHORED`; `fx.lamp`; `Audio.duck` only; `Vfx.battle_started`; `ambience.gd` vs `mix_beds.gd` ownership; §12 added. |
| A17 | minor | Sourceless hero lamp | A diegetic 0.12 m lantern on an FND-6 pendulum (ω 7, ζ 0.15, ±25°); the pool follows it (WLD-06). |
| A18 | minor | Easing and anticipation | Sheep topple removed with the sheep; hare thumps, goose hiss crouch, bird 60 ms dip and 250 ms wing flare; flowers 1.8 s `in_out_sine` per head; flames `out_back(1.6)` over 300 ms. |
| A19 | minor | Rain physics and onset | Drizzle 3 m/s / 0.12 m, rain 6 m/s / 0.35 m; 15 s `in_quad` ramp after cloud cover passes 0.7; 8 s of first drops; 6 s `out_quad` ending; 30 s of eaves drips. |
| A20 | minor | Repetition | Mist on 50% of dawns (always after rain); whooshes ≥ 12 s apart, peaks > 0.75, 4 no-repeat variants at ±1.5 st; sweeteners 8–25 s within 40 m (bible); per-night variation (§5.4). |
| A21 | minor | Confetti motes; invisible shafts | Seeds only on gust fronts over meadow (a gust visualiser); shafts replaced by canopy dapple inside the cloud-shadow term. |
| A22 | minor | Draw-call sum did not match | Re-totalled honestly: ≤ 15 including the depth prepass. |
| A23 | minor | Aftermath trigger could never fire | Quiet = I < 2 for 2.5 s with ≥ 3 visible deaths; the silence starts from `Vfx.battle_started`; the first bird at quiet + 3.5 s, after CMB-43. |
| A24 | minor | Timing and naming mismatches | Golden hour 16:30–18:00 (HUD-07); windows with the tide (bible request, §11.7); the 22° floor kept with its reason (§11.6); "HUD orb" replaced by the HUD day clock and Horizon Ribbon; bloom written as the explicit exception (≤ 60% saturation, ≤ 384 tufts); WLD-10's base list matches §6. |

**Review A: missing features added**

| feature | where |
|---|---|
| Wether Downs places table | §4.10, WLD-40..48 |
| Dawn dew and dew trails ★ | WLD-35 (§5.5) |
| Firefly wake ★ | WLD-08 |
| Moths at lit sources | WLD-08 |
| Per-night variation ★ (moon phase, sunset by weather) | §5.4, WLD-02 |
| Distant storm, "storm-lit" | WLD-36, §6 |
| After-rain moments (steam curls, drips, birdsong burst) | WLD-11 |
| Puddle interaction (splashes, muddy prints) | WLD-11 (P2) |
| Commands press the world (order press, placement shock 0.15) | WLD-16, WLD-17 |
| Cartographer's reveal raised to P1 ★ | WLD-26 |
| Dusk and dawn beat sheet | §5.3 |
| Faction base life (storks, chimes, mirrors, the vane) | WLD-37 |
| Diegetic hero lantern | WLD-06 |
| Hale Spring set piece (P0) | WLD-42 |

**Review B: engine and performance**

| # | sev | issue | resolution |
|---|---|---|---|
| B1 | blocker | Scroll offsets as velocity × `fx_time` with drifting direction and speed | CPU-integrated offsets per layer on the sim clock, wrapped per texture period, published as `atm_scroll_a..d`; `gust_at` reads the same; the rate rule in §2; `test_atmos_scroll`. |
| B2 | blocker | Cloth frequency × time; rain speed lerp | WLD-29: two fixed waves (1.4 and 3.0 Hz) crossfaded by w, with hashed phase; rain as two fixed-speed sets crossfaded by count and α. |
| B3 | major | Firefly phase-mixing drift | One Ω for all; randomness in phase and amplitude; a constant d_wave = sun_axis; the phase difference wrapped to (−π, π], so the ramp changes the rate by < 1%. |
| B4 | major | Interpolation lag; meaningless AABBs | Node policy (§2): interpolation OFF on Atmos and Life, static volumes with global origins, map-sized `custom_aabb`, `cast_shadow` OFF everywhere. |
| B5 | major | Instance uniforms on MultiMesh props | `atm_ignite(origin)` in `prop.gdshader` from `atm_front_t`; `INSTANCE_CUSTOM.r` for clamp-fire banking; instance uniforms only on buildings (`anim_b.z`); CPU sparks for the 8 nearest only. |
| B6 | major | Flat mist planes on a multi-level map; order flips with water | A height-following 2 m grid on the lowland floor channel (height G); render priority 5; both layers in one mesh. |
| B7 | major | Mist veils rings; terrain composite order | Mist at priority 5 under every ground-draped layer; `eco_rings` cut out of the mist and composited last in the terrain; ring-contrast assertion in Mist. |
| B8 | major | Grass submitted 3× the budget; 50–100 ms lazy-build hitches | Replaced chunks with two world-anchored wrap lattices (≤ 7.2k instances at High, 2 draws, 0 ms build, 1 global per frame). Deviation from the suggested 16 m chunks: those would have needed 12–40 draws at our zoom range; the lattice also delivers A12's zoom LOD for free. Low skips trample tests beyond 25 m. |
| B9 | major | No shader-level quality tier | `atm_quality` with uniform-coherent branches; the Low list in WLD-F2; the cloud sea samples the painted mask (no fbm). |
| B10 | minor | ~10 samplers per material | Packed global samplers; ≤ 7 per material; asserted in `test_shader_compile`. |
| B11 | minor | `Atmos.bind` easy to miss | Deleted; global `sampler2D` (spike-confirmed on both renderers). |
| B12 | minor | `atm_grade` fallback | Deleted; open question closed. |
| B13 | minor | Upload claims and minimap re-bake | Wear's 147 KB at 1 Hz budgeted; PackedByteArray mirrors + `set_data`; fog as display bytes; minimap patches dirty pixels only, with everything else in the overlay shader. |
| B14 | minor | Lantern banding | light / 2 (clamp 2) plus a ±1/255 ordered dither. |
| B15 | minor | PCSS and sun rotation | Angular distance on High only; shadow-swimming capture in `bench_atmos` before any PCSS. |
| B16 | minor | 8-light limit on Compatibility | LightBudget capped at 8 in total and ≤ 8 per terrain chunk. |
| B17 | minor | ~12 world voices against a cap of 4 | A world pool of 8 (6 loops, 2 one-shots) with an explicit stealing order; request to the UI owner. |
| B18 | minor | Life CPU underestimated | Round-robin 4 per frame, a 4 m visible-unit cell grid, brawl clusters; 14 critters in total. |
| B19 | minor | No hysteresis on nearest-to-focus picks | Heroes' bucket rule (2 m, 4 Hz, 2 m hysteresis, on-screen first, 300 ms fades) for every such selection. |
| B20 | minor | Aliasing rain and procedural rings | 1.25 px clip-space streaks with α compensation; a mipmapped ripple texture, one sample. |
| B21 | minor | Tide lags the sim flip; `xz.x`; band width | `dot(xz, sun_axis)`; gate width 6 m = 0.4 s × 15 m/s. Deviation: B asked for a 17:42–18:00 sweep that leads the flip, while A asked for the core to pass the focus at T0. We follow A: the tide moves light, never vision, and its on-screen pass (±1.4 s) sits inside the sim's 3.2 s sight ease. |
| B22 | minor | Flaky framerate test | Closed-form wind direction; t0 snapped to the 10 Hz tick; 2e-3 tolerance. |
| B23 | minor | Draw-call total and shadow passes | Restated at ≤ 15 with the prepass; cast_shadow OFF; mist layers merged; fireflies, seeds and moths in one MultiMesh. |
| B24 | minor | Bird packing on Compatibility | P0, P1, climb height and swirl sign in the transform; 0..1 values only in custom data. |
| B25 | minor | Dotted desire paths | Bresenham from the previous poll position, once per cell; polls on sim ticks. |
| B26 | minor | Wrap boxes missed the view trapezoid | Boxes centred on the footprint centroid, sized from it, with a 3 m edge fade (WLD-F5). |

**Review B: missing features added:** CPU-integrated scroll and phase on the sim clock (WLD-F1, §2); the shader tier (WLD-F2); the node policy (§2); runtime monitors and frame-time auto-degrade (WLD-F1, F5); zoom-aware LOD (WLD-F5, WLD-15); the hysteresis rule (WLD-F5); the Compatibility LightBudget cap (WLD-F4); the world voice pool (WLD-33); behaviour at 4–8× game speed (WLD-F5); the lowland floor channel and the ring mask for mist (WLD-12).

**Not done, and why:** the heroes doc was not edited to close its open question 7, because it has an uncommitted concurrent revision. The request is in §12.
