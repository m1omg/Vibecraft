# Juice spec: World & Atmosphere

*Domain doc of the Vibecraft juice bible. Date: 2026-10-16. Status: design spec, ready to implement.*
*Covers: day and night (sun and moon, grading, the nightfall tide, stingers, lights at dusk, night readability, sleeping creep camps, fireflies), sky-on-the-ground and weather (cloud shadows, wind and gusts, drizzle and rain, mist and fog banks, light shafts and the air layer), foliage and ground cover, water, the life layer (critters, flocks, aftermath), fog-of-war rendering, settlement and memory (hearth smoke, cloth, desire paths, the persistence policy for corpses and rubble), world ambience audio and the living minimap.*
*Out of scope (owned by sibling docs, referenced by id):*
- *Chopping, tree shudder and tree fall: ECO-08..11.*
- *Production chimneys, building fire, collapse and rubble, the lamplighter cascade: BLD-11, BLD-15, BLD-16, BLD-19.*
- *Footstep dust and the per-stride shallow-water ring: CMB-04.*
- *Creep "notice": CMB-06.*
- *Corpses and ground stains: CMB-30..32.*
- *Spells, hero events, the HUD clock orb, minimap pings, camera shake and the bus layout: other docs.*

Inputs:
- `docs/research/visual-art-direction.md`: "storm-lit heroic diorama", cloud shadows, wind sway, night tinted blue (never black), fog-of-war values, and the rule that VFX are the only things that bloom.
- `docs/research/audio-direction.md`: day and night beds per tileset, dusk and dawn sounds, sweeteners, buses and caps (§3.5, §6.3).
- `docs/research/video-references.md`: M3 day/night, M4 sleeping creeps, B7 transition timing.
- `docs/research/godot-rts-tech.md`: no `Decal`, MultiMesh per chunk, CPU fog grid, Compatibility limits.
- `docs/architecture.md`: 30 Hz sim, `DayNight.hour_at()`, the 480 s cycle (20 s per game hour), `Fog` grid, `Doodads`, `TerrainBuilder` fog hooks.

**Shared plumbing with siblings.**
- Clock: `fx_time` (economy §2.1) and `Vfx.now` (combat §2) are **the same value**. It is frozen while paused and scaled by game speed. This doc uses it unchanged.
- Particle systems reused: FxSprites (combat FND-2), BallisticFx, StreamFx and GroundFx (economy §2.3).
- Governor reused: the density governor and tiers (combat FND-3) and `FxBudget` (economy §2.6).
- Lights: this doc adds the shared **LightBudget** (WLD-F4), which arbitrates the light pools of all three docs.

---

## 1. Feel goals

Vibecraft's world is a **painted diorama that keeps time, breathes with one wind, remembers what happened, and never lies**.

WC3 made its maps feel alive with a few cheap conventions: a blue night tint, a sound at dusk, sleeping creeps, a sheep to click. We keep those and add **coherence**. One clock and one wind drive every blade of grass, flag, smoke column, firefly and ambient sound, so the world moves as one organism instead of a hundred unrelated loops. That coherence is what separates hand-made juice from generic shader wiggle.

Atmosphere is also **information**:
- Golden light says night is coming.
- A sleeping camp shows how hard it is by the shape of its snore glyphs.
- Motion means you can see it; stillness means you only remember it.

All of it is **cheap by construction**: closed-form shaders and a handful of textures stand in for hundreds of lights, particles and nodes. It survives 300 units and a software renderer.

**Pillars**
1. **The ground is our sky.** At −56° pitch the camera never sees the sky, so sky events are painted onto the ground: cloud shadows, gust sheen rolling through grass, the nightfall tide, rain rings, the shadows of birds. Nothing is spent where the camera cannot look.
2. **One clock, one wind.** Everything samples `hour`, `fx_time` and the same world-space wind field. A gust front visibly bends grass, then trees, then flags, then smoke, in the order it reaches them.
3. **If it moves, you can see it.** In live vision the world animates. Remembered (fogged) areas are still, faded and sketched. Unexplored areas are a drifting sea of cloud. Fog of war becomes a felt texture, not a black overlay.
4. **Telegraph, never obscure.** Atmosphere announces changes early: golden hour, a violet pre-dawn, sleep glyphs. It never covers what matters:
   - mist stays below the knees;
   - rain is a whisper;
   - at midnight units keep ≥ 60% of their noon brightness.
5. **Honest to the fog.** No critter, bird, footpath, light, sound or felled tree reacts to something the local player cannot see. The world is never a radar.
6. **Cheap by construction.** The whole domain fits in ≤ 0.6 ms CPU and ≤ 18 added draw calls. Its main tools:
   - textures act as lights (the lantern map);
   - motion is closed-form;
   - particles live in camera-local wrap volumes;
   - critter logic runs only near the camera.

---

## 2. Ground rules (bind every row below)

**Clocks and determinism**
- **`hour`** = `DayNight.current_hour()`. It is sim time plus the physics interpolation fraction, so it pauses with the game, follows game speed, and uses the same mapping as the sim's `is_day()`. Visuals never disagree with sight ranges. Everything time-of-day uses `hour`.
- **`fx_time`** drives wind, water, sway, particles and critter segments.
- **Never use the shader built-in `TIME`.** It keeps running while the game is paused, and it wraps at `rendering/limits/time/time_rollover_secs` (3600 s by default), which pops every sway phase once an hour. Today's `tree.gdshader` and `water.gdshader` use `TIME`; WLD-F2 replaces it.
- **Closed form only.** Every animated value is f(`hour`, `fx_time`, event t0).
  - CPU smoothing uses `Juice.damp()` (combat FND-1).
  - Critters move along timed segments, not Euler steps.
  - No Tween ever touches world state.
- **Read-only.** Atmosphere never calls `World.rng`, never writes sim state and never delays a sim event. Weather schedules and critter placement use their own `RandomNumberGenerator`, seeded from hash(map name, match seed, salt).

**Fog honesty (three rules)**
1. Nothing here reacts to a unit the local player cannot currently see, unless it is the player's own unit.
2. Nothing animates in explored-but-not-visible areas (the stillness rule, WLD-27).
3. No world memory (wear, felled trees, stains, lantern pools, grass clearings) is created from an event the local player did not see.

**Readability limits (hard caps, verified in §9)**

| Layer | Limit |
|---|---|
| Night | Unit pixels' mean luminance at 00:00 ≥ 60% of 12:00. Team-colour chroma ≥ 70% of noon. Nothing pure black outside unexplored areas. |
| Cloud shadows | Multiply ≤ 0.32 on ground and props, ≤ 0.19 on units (units take 0.6×). Rings, bars and markers are unshaded and unaffected. |
| Mist | Planes only up to 1.0 m above the ground. α ≤ 0.30 (lower plane) and ≤ 0.18 (upper). Covers feet, never torsos. |
| Rain | Streak α ≤ 0.16, length ≤ 0.6 m, ≤ 900 on screen; α ×0.6 in Brawl tier. No screen-space (lens) rain. |
| Air motes, fireflies | Core ≤ 0.06 m. ≤ 160 fireflies and ≤ 512 motes on screen. ×0.3 inside the brawl radius. |
| Critters | ≤ 0.6 m tall, saturation ≤ 40%, never team-coloured, never selectable, no hover ring. Not drawn in fog. |
| Birds | Flight altitude ≥ 6 m. ≤ 18 px at default zoom. Ground shadows α ≤ 0.25. |
| Light shafts | α ≤ 0.10, HDR ≤ 1.0, ≤ 6 on screen. |
| Bloom | Only flames, embers, ignition sparks, fireflies and water glints exceed HDR 1.0. Water glints are capped at 1.3 and ≤ 2% of water pixels. Terrain, foliage, the water body, mist, clouds and lantern pools stay ≤ 1.0. |
| Lantern pools | Add at most +0.45 × albedo. Warm light may shift any of the 12 team colours by ≤ 8° hue. |
| Ground cover | Tufts ≤ 0.38 m, so infantry legs stay readable. No grass on paved roads, building footprints, water or the 0.5 m cliff-edge band. |
| Fog states | Differ by value and texture (grain), never by hue alone. |
| Colour-blind safety | Camp tier = glyph count, not only colour. Wear = value change, not only hue. |

**Renderer tiers**

| Thing | Forward+ | Compatibility | Container (lavapipe / opengl3) |
|---|---|---|---|
| Hearth `OmniLight3D` pool | 4 (inside the 12-light LightBudget) | off; the lantern map carries the look | off |
| Grading saturation and contrast | `Environment` adjustments | `Environment` if supported, else the in-material `atm_grade` fallback (spike) | as renderer |
| Soft mist intersections | heightmap fade (no depth texture) | same | same |
| MultiMesh custom data | float | 16-bit, so all times live in the instance transform (as FND-2) | same |
| Default quality | High | Low (forced) | Low (tests), High for look captures |

**Sim → view hooks this doc needs.** Whoever lands a hook updates `docs/architecture.md` in the same commit.

| Hook | Kind | Owner | Used by |
|---|---|---|---|
| `Unit.sleeping`, `Unit.camp_id`, `Events.creep_sleep_changed(unit, asleep: bool, cause: String)`; cause ∈ dusk, dawn, attacked, disturbed | field + signal | `creeps.gd` | WLD-07 |
| `MapData.creep_camps[i].difficulty` (1–3) | data | map | WLD-07, 34 |
| `MapData.props`: `[{def, pos, yaw}]`, non-blocking decor (torch, brazier, lamp post, campfire, burrow, lily pad, fence, banner) | data | map | WLD-05, 21, 33 |
| `MapData.water` value **2 = shallow ford** (walkable, bed at water_level − 0.35 m) | data + pathing | map + `pathing.gd` (gameplay sign-off) | WLD-20 |
| `MapData.sun_axis` (default (1, 0): east = −X = screen-left) | data | map | WLD-01, 03 |
| `Fog` double buffer: `upload_time`, `period`, `flip`; `Fog.is_visible(pid, cell)` | fields + reader | `fog.gd` | WLD-25 and every fog gate |
| `Doodads.remembered_felled`: a tree felled outside the local player's vision stays drawn until its cell is seen | field | `doodads.gd` | WLD-27, 31, 34 |
| Def `fx` hints: `lamps`, `windows`, `hearth`, `chimney`, `cloth` | data | `units.json` (economy §2.2 block) | WLD-05, 28, 29 |
| Combat intensity and `hit_landed` (combat FND-3, FND-4) | reader + signal | `vfx.gd` | WLD-08, 21, 23, 24 |

**Notation:** as the siblings use it.
- Durations are ms at 1× game speed. Game hours are written hh:mm; 1 game hour = 20 s.
- Colours are sRGB hex. "HDR n" means emission multiplier n.
- Easings are the `Juice` Penner set.
- w = local wind 0..1 and g = local gust 0..1 (WLD-10).
- ★ = our own twist (§7).

---

## 3. Foundations (build first)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-F1 | **Atmos director, clocks and global parameters** | every frame (`_process`, PAUSABLE) | **Reads:** `hour` (DayNight), `fx_time` (Vfx), weather (F3), the combat governor (FND-3).<br>**Writes global shader parameters once per frame:**<br>• `atm_day` (x daylight, y night, z golden, w blue hour);<br>• `atm_sun` (xyz light direction, w elevation);<br>• `atm_wind` (xy downwind, z base strength, w gust speed);<br>• `atm_cloud`, `atm_weather` (wetness, rain, mist, puddles), `atm_front` (WLD-03), `atm_fog_blend`;<br>• `atm_brawl` (x, z, radius, intensity), `atm_grade`, `atm_rim`;<br>• `atm_shock_0..3`, `atm_carry_0..5`;<br>• `atm_map_size` (written once).<br>**Signals:** `dusk_began`, `dawn_began`, `front_started(kind)`, `weather_changed(old, new)`. The HUD orb (UI doc) listens.<br>**API:** `hour()`, `night()`, `wind_at(xz)`, `gust_at(xz)`, `visible_at(pos)`, `shock(pos, strength)`, `water_splash(pos, size)`, `add_light(id, pos, kind, owner)`, `remove_light(id)`, `bind(material)`. | New `src/world/atmos.gd` (`class_name Atmos`, node `World/Atmos`, created only when `World.visuals`). Globals are declared in `project.godot [shader_globals]` so shaders compile in the editor and headless. About 24 `RenderingServer.global_shader_parameter_set` calls per frame. | ≤ 0.05 ms/frame | P0 |
| WLD-F2 | **Shared world shader include** | compile time | One include (sketch below) provides wind, gust, cloud shadow, smoothed fog, memory grade, the night gate, lanterns and shocks. Terrain, trees, water, grass, props, buildings and units all use it, so a gust, a cloud or the nightfall band hits everything identically. It replaces the copies of `fog_factor()` in today's terrain, tree and water shaders. | `src/world/shaders/world_common.gdshaderinc`, plus `foliage.gdshaderinc` (WLD-14) and `cloth.gdshaderinc` (WLD-29), via `#include`. **Samplers are per-material uniforms** bound once by `Atmos.bind(mat)`. Their images update in place, and the fog A/B choice is a global flip, so texture references never change and no material is touched per frame. | about 40 ALU + 4–6 samples per terrain fragment | P0 |
| WLD-F3 | **Wind and weather state** | match start (schedule); every frame (evaluate) | **Schedule:** a list of (sim start time, state) pairs (table §6), built at match start from hash(map name, match seed, "weather") with its own RNG. It is evaluated from `world.time`, so every player, observer and replay sees the same sky.<br>**Wind direction:** drifts ±25° around the biome's prevailing direction, from smooth 1D noise of sim time (period 60–120 s).<br>**Wind values:** base strength and gust speed come from the state, with 10 s transitions.<br>**Gust texture:** 128², seamless. R = gust fronts (simplex, 3 octaves, stretched 2:1 across the wind), G = flicker noise, B = flutter noise. Generated at boot and kept as an `Image` for the CPU mirror.<br>**CPU mirror** `gust_at(xz)`: the exact shader formula, bilinear with wrap. | `src/world/weather.gd` (state machine + schedule) inside Atmos. `FastNoiseLite.get_seamless_image()`. | ≤ 0.02 ms/frame | P0 |
| WLD-F4 | **Lanterns: light without lights** | light added or removed; nightly gating | **Lantern map:** RGBA8 at 1 m per texel (192² on the slice); RGB = warm light / 4.<br>• Each source splats (1 − x²)² falloff over its radius into a float accumulation buffer. Only the changed rect is re-quantised, then one `ImageTexture.update()` (147 KB).<br>• Terrain, trees, props and buildings add albedo × L; units sample L at their origin (WLD-06).<br>• Gated by `atm_night_gate()` (night and the nightfall band) and flickered by the gust texture's G channel.<br>• **Honesty:** only sources the local player knows contribute: own, allied, neutral props, and enemy structures seen or remembered as ghosts.<br>**Carried lights:** 6 globals for moving warm lights (hero lamps).<br>**Real lights (Forward+ only):** 4 `OmniLight3D` (no shadows; range = pool radius × 1.1; energy 1.2). They bind at 4 Hz to the lit sources nearest the focus, with 250 ms energy crossfades on reassignment.<br>**LightBudget (shared):** ≤ 12 `OmniLight3D` on screen in total. Priority: spell > impact (combat FND-3, 4) > fire (BLD-15, 6) > hearth (4). The lowest class gives up lights first. | New `src/world/lanterns.gd` and `src/fx/light_budget.gd`. `impact_lights.gd` and `building_fx.gd` request lights through the budget. On Compatibility the hearth pool is off. | about 0.1 ms per change; at runtime 1 sample per fragment | P0 map / P1 pool + budget |
| WLD-F5 | **Atmosphere governor** | settings change; every frame | **Presets** Low, Medium and High (§9), plus juice level 0 rules.<br>**`reduce_motion`:** no nightfall band, no grass sheen, no shock rings, firefly waves off, cloud drift ×0.5.<br>**`weather_visuals`:** Full; Light (no streaks, mist ×0.5); Off (always Clear).<br>**Brawl awareness:** `atm_brawl` = centroid and radius of on-screen hits over the last 1 s (combat FND-3). Air motes, fireflies and critters thin out inside it.<br>**Fog gate:** `visible_at(pos)` reads the local player's `Fog` grid (value 2). Every CPU-side spawn in this doc calls it.<br>**Renderer:** detected at start (`RenderingServer.get_current_rendering_method()`). Compatibility forces Low grass and turns the hearth pool off. | In `atmos.gd`. New `Settings` keys: `atmo_quality`, `weather_visuals`, `reduce_motion`, `world_memory`. | negligible | P0 |
| WLD-F6 | **Biome data and derived world maps** | map load | **`data/biomes.json`:** palette (art doc §7.2), grading offsets, prevailing wind, weather weights, critter table, ambience set, flower palette, grass colours and density, air kinds.<br>**Derived at load** (≤ 150 ms on the slice):<br>• `atm_world_tex` RGBA8 at 1 m: R = wear (runtime); G = shore signed distance ±4 m (BFS); B = lowland mask (lowest local cliff level or within 10 m of water, blurred 3 m); A = meadow mask (grass weight ≥ 0.5, ≥ 4 m from trees and roads).<br>• `atm_height_tex` R8 = (h + 1.5 m)/7 m (2.7 cm steps), for mist and bird shadows.<br>• `atm_mask_tex` R8 = footprints of **known** structures (updated on `set_footprint` and ghost changes).<br>• CPU lists: perches, shore points, forest-edge shaft candidates, burrows, and the ambience zone grid (8 m cells). | `src/world/world_maps.gd`; `Defs.biome(id)`. | load only | P0 |

**WLD-F2 sketch (load-bearing; colours are in sRGB space before the final `pow(2.2)`, as `terrain.gdshader` does today):**

```glsl
// src/world/shaders/world_common.gdshaderinc
global uniform float fx_time;          // = Vfx.now: frozen while paused, follows game speed
global uniform vec4 atm_day;           // x daylight, y night, z golden, w blue hour (0..1)
global uniform vec4 atm_wind;          // xy downwind unit vector (world XZ), z base 0..1, w gust front speed m/s
global uniform vec4 atm_cloud;         // x scale m, y coverage, z strength, w drift m/s
global uniform vec4 atm_fog_blend;     // x upload time (fx_time), y period s, z 0 = A current / 1 = B current
global uniform vec4 atm_front;         // x band position m along sun_axis, y width m, z +1 dusk / -1 dawn / 0 idle, w gate when idle
global uniform vec2 atm_map_size;      // metres

uniform sampler2D atm_gust_tex : filter_linear_mipmap, repeat_enable;  // R fronts, G flicker, B flutter
uniform sampler2D atm_cloud_tex : filter_linear_mipmap, repeat_enable; // painted cloud mask
uniform sampler2D atm_fog_a : filter_linear;                            // L8: 0 unexplored, .5 fogged, 1 visible
uniform sampler2D atm_fog_b : filter_linear;
uniform sampler2D atm_lantern_tex : filter_linear;                      // RGB = warm light / 4
uniform sampler2D atm_world_tex : filter_linear;                        // R wear, G shore SDF, B lowland, A meadow

float atm_gust(vec2 xz) {
	vec2 uv = (xz - atm_wind.xy * atm_wind.w * fx_time) / 48.0;
	return smoothstep(0.55, 0.85, texture(atm_gust_tex, uv).r);
}

float atm_wind_at(vec2 xz) {
	float base = atm_wind.z * (0.75 + 0.25 * sin(fx_time * 0.7 + dot(xz, vec2(0.05, 0.03))));
	return clamp(base + 0.6 * atm_gust(xz), 0.0, 1.0);
}

float atm_cloud_shadow(vec2 xz) {
	float n = texture(atm_cloud_tex, (xz - atm_wind.xy * atm_cloud.w * fx_time) / atm_cloud.x).r;
	float c = atm_cloud.y;
	return smoothstep(1.0 - c - 0.12, 1.0 - c + 0.12, n) * atm_cloud.z;
}

float atm_fog(vec2 xz) {                       // temporally smoothed fog state 0..1 (WLD-25)
	vec2 uv = xz / atm_map_size;
	float a = texture(atm_fog_a, uv).r;
	float b = texture(atm_fog_b, uv).r;
	float k = smoothstep(0.0, 1.0, (fx_time - atm_fog_blend.x) / atm_fog_blend.y);
	return atm_fog_blend.z < 0.5 ? mix(b, a, k) : mix(a, b, k);
}

float atm_night_gate(vec2 xz) {                // lanterns on/off, swept by the nightfall band (WLD-03)
	if (atm_front.z == 0.0) { return atm_front.w; }
	float passed = 1.0 - smoothstep(-0.5, 0.5, (xz.x - atm_front.x) / atm_front.y);
	return atm_front.z > 0.0 ? passed : 1.0 - passed;
}

vec3 atm_lantern(vec2 xz) {                    // + 6 unrolled atm_carry_n terms in the full version
	vec3 l = texture(atm_lantern_tex, xz / atm_map_size).rgb * 4.0;
	float flick = 0.88 + 0.12 * texture(atm_gust_tex, xz * 0.04 + vec2(fx_time * 1.7, fx_time * 1.1)).g;
	return l * flick * atm_night_gate(xz);
}

vec3 atm_memory_grade(vec3 col, float f, float edge_noise) {   // WLD-25..27
	float v = f + (edge_noise - 0.5) * 0.18;
	float explored = smoothstep(0.14, 0.34, v);
	float visible = smoothstep(0.64, 0.82, v);
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 fogged = mix(vec3(lum), col, 0.4) * mix(0.55, 0.45, atm_day.y)
		* mix(vec3(1.0), vec3(0.616, 0.702, 0.839), 0.15);       // #9DB3D6 at 15 %
	vec3 seen = mix(fogged, col, visible) * (1.0 - 0.08 * (1.0 - smoothstep(0.82, 0.98, v)) * visible);
	return mix(vec3(0.039, 0.047, 0.071), seen, explored);      // #0A0C12; WLD-26 adds the cloud sea here
}
```

The CPU mirror must match the shader exactly, because audio (WLD-10) and smoke drift read it:

```gdscript
# atmos.gd: CPU mirror of atm_gust(). Change both or neither.
func gust_at(xz: Vector2) -> float:
	var uv := (xz - wind_dir * gust_speed * Vfx.now) / 48.0
	return smoothstep(0.55, 0.85, _bilinear_wrap_r(_gust_img, uv))
```

---

## 4. Feature table

### 4.1 Day and night

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-01 | **Sun and moon arc, blue-hour swap** | every frame (`hour`) | **Sun (05:40–18:15):**<br>• elevation e = max(22°, 24° + 40°·sin(π(h − 6)/12)): 24° at 06:00 and 18:00, 64° at noon;<br>• yaw, relative to the camera yaw, y = −55° + 110°·(h − 6)/12.<br>Shadows therefore fall up-right in the morning, straight up-screen at noon and up-left in the evening. They are always within 55° of screen-up: never toward the camera, never across a unit's own ring. A 1.6 m infantry shadow is 3.6 m long at 24° and 0.8 m at noon. At 08:00 (match start) e = 44° and y = −37°, matching the art doc's lower-left key.<br>**Moon (18:15–05:40):** e = 32° + 18°·sin(π·n), y = −40° + 80°·n, where n = fraction of the night.<br>**Swap:** the light direction jumps only at the swap keys (18:15 and 05:40), where energy is 0.06 and `shadow_opacity` is 0 (§5). The jump is therefore invisible. The moon ramps to 0.38 by 19:30.<br>`light_angular_distance`: 1.2° at noon → 2.5° at e = 24°, so long shadows are soft.<br>Shadows: max distance 60 m, PSSM 2 splits.<br>At 1× the direction moves ≤ 0.46°/s, so shadows creep and never pop. | `src/world/day_night.gd` becomes the time-of-day director. It keeps `hour_at`, `is_day`, `current_hour` and `fixed_hour`. It replaces today's −150°..+90° azimuth (which lets shadows fall toward the camera) and the FILMIC default; the tonemap follows the art doc. | about 5 µs | P0 |
| WLD-02 | **Time-of-day grading and the golden-hour telegraph** | every frame (`hour`, weather) | The 10 keys in §5 are interpolated with smoothstep between neighbours (wrapping at 24 h).<br>**Outputs:**<br>• light colour and energy; ambient colour and energy;<br>• depth-fog colour (begin 32 m, end 90 m, per the art doc);<br>• `adjustment_saturation` and `adjustment_contrast`; glow intensity;<br>• `atm_day`, cloud strength, water colours, emissive gates.<br>**Golden-hour telegraph:** 16:30–17:50 (27 s at 1×) the key warms (#FFC98A, saturation 1.12) and shadows stretch. This is the player's "night is coming" read, 30 s before camps fall asleep.<br>**Pre-dawn telegraph:** 04:30–05:40, a violet lift (ambient #45508A → #6A6496).<br>**Weather multipliers:**<br>• Overcast: energy ×0.75, saturation ×0.92, shadow α ×0.55.<br>• Drizzle and Rain: energy ×0.65, ambient ×1.08, saturation ×0.9, fog begin 26 m.<br>• Mist: fog begin 22 m, fog colour toward #DDE4EA.<br>**Biome offsets** from `biomes.json` (e.g., Gloamwood ambient ×0.9, hue +6°). | Keys are a Resource (`data/time_of_day/greenvale.tres`) evaluated in `day_night.gd` and written to the `Environment`.<br>If Compatibility lacks `Environment` adjustments (spike), the include applies `atm_grade` (tint rgb, saturation) in-material.<br>The 3D LUT stays static per biome. We do not blend per-hour LUTs: parametric keys give the same range for free. | about 15 µs | P0 |
| WLD-03 | **Nightfall tide and first light ★** | `hour` crosses 18:00 (dusk) and 05:48 (dawn) | **Front:** a straight edge perpendicular to `sun_axis`, travelling east → west (screen-left → right): s = −20 m + (map width + 40 m)·(h − h0)/0.3 h. That is 6 s at 1×; it crosses a default screen in about 1.2 s. Night rises in the east and chases the sun west.<br>**Dusk band:** a 10 m ink wash, multiply #4C5698 at 22% at its core with smoothstep edges. It is drawn on terrain, water, trees and props, never on units, rings or bars.<br>• Behind the band, lantern pools gate on (400 ms fade at each point).<br>• Every light source **ignites as the band core passes it** (+ hashed 0–250 ms, WLD-05).<br>**Dawn band:** a warm "first light" line, #FFD2A0 screen-blended at 18%. Flames die as it passes: 250 ms shrink plus one smoke puff, for the 8 sources nearest the focus.<br>**Sound:** none of its own; the stinger (WLD-04) carries it.<br>**Reduce motion / juice 0:** no band; ignitions use hashed 0–2,000 ms delays. | `atm_front` global, computed from `hour` (so pause and game speed follow the sim). `atm_night_gate()` in the include. The minimap draws the same band (WLD-34). | free (1 uniform, 1 smoothstep) | P1 |
| WLD-04 | **Dusk and dawn stingers, bed crossfade** | `hour` 17:52 (dusk), 05:52 (dawn) | **Dusk, "lowing horn" (original):** a long wooden horn, two notes falling a fourth (D3 → A2), 2.4 s. It starts 2.67 s early so the second note lands on 18:00. A nightjar-like churr tail (1.2 s) is layered at +0.6 s.<br>**Dawn, "chorus":** a 2.8 s rising swell of three songbirds, with one soft high bell strike exactly on 06:00.<br>**Mix:** both are 2D on the Ambience bus at +6 dB over the beds (−10 dBFS peak), ducked by Voice like the beds. If music is playing, the stinger drops 4 dB. Skipped at game speed ≥ 4× (replays).<br>**Beds:** day and night loops crossfade (equal power) over 8 s centred on 18:00 and 06:00.<br>**IP:** never a wolf howl at dusk or a rooster at dawn. Both are WC3-associated cues. | `ambience.gd` (WLD-32) schedules them from `hour`. `AudioStreamPlayer` (non-positional). Assets `assets/audio/ambience/stinger_dusk.ogg` and `stinger_dawn.ogg`. | 1 voice for 3 s | P0 |
| WLD-05 | **Lights of dusk: torches, braziers, lamps, campfires, windows** | ignition when the band passes (WLD-03) or when created at night; out at first light | **Sources:** map props (torch post 2.2 m, brazier 1.0 m, lamp post 2.6 m, campfire); building points from def `fx.lamps` (hall gate 2 torches, tower brazier); windows (`fx.windows`).<br>**Strike (ignite):**<br>• 3 SPARK (#FFD27A HDR 2.2, up 1.2 m/s, life 300 ms);<br>• emission 0 → 1.0 (60 ms) → 0.2 (40 ms) → 1.2 (80 ms) → 1.0 (200 ms `out_quad`);<br>• flame sprites ramp from 0 to full over 300 ms;<br>• a "fwump" (World −20 dB), only for the 2 sources nearest the focus, ≥ 120 ms apart.<br>**Flames** (StreamFx `fire`):<br>• torch: 6 sprites, 0.18 → 0.06 m, life 380–520 ms, rise 1.0 m/s;<br>• brazier: 10 sprites at 0.30 m;<br>• campfire: 14 sprites + 4 embers;<br>• colours: FIRE core #FFE08A HDR 2.5 → mid #FF8A2A HDR 1.8 → edge #C2341A;<br>• flames lean downwind and flicker 1.5× harder when the local g > 0.6.<br>**Flicker** (emission and pool; n = hashed noise):<br>• torch 0.86 + 0.10·n(7.3t) + 0.04·n(17t);<br>• lamp (glass) 0.95 + 0.05·n(3t);<br>• brazier 0.80 + 0.20·n(9t).<br>**Pools** (radius / intensity / colour):<br>• torch 4.5 m / 0.9 / #FFB060;<br>• brazier 6 m / 1.1 / #FFA050;<br>• campfire 7 m / 1.2 / #FF9A48;<br>• lamp 5 m / 0.8 / #FFC680;<br>• window 2.5 m / 0.4 / #FFB86B.<br>**By day:** everything is unlit except campfires (60% sprites, no pool).<br>**Rain:** torches sputter (emission dips to 0.7 for 80–160 ms at 1–2 Hz, hashed); campfires steam 2 puffs/s (#E8F0F5 α 0.25). | `lanterns.gd` (F4) owns the sources. Flames are StreamFx streams (economy §2.3). Emission is `instance uniform float lit` on prop and building materials, on GLB materials named `*FLAME*` or `*WINDOW*`. When juice level 2 runs BLD-19 (lamplighter cascade), own windows follow BLD-19 instead of the band. | sprites only for the ≤ 24 lit sources nearest the focus; the rest are emissive-only. Pools cost nothing at runtime | P0 emissive + pools / P1 strike, sputter |
| WLD-06 | **Night readability lift and the hero lamp ★** | `atm_day.y` (night) | **Team-colour lift:** the unit and building shader adds emission team colour × 0.18 × night on team-mask areas. This stays under combat's 0.6 unit-emission rule.<br>**Moon rim:** `rim_color` (art doc uber-shader) lerps from team colour × 0.6 by day to #8EA6FF × 0.45 at night, and `rim_power` from 3 to 2.5, so silhouettes separate from the dark ground.<br>**Lantern response:** units sample the lantern map at their origin (vertex stage) and add albedo × L × 0.5 as emission, clamped ≤ 0.6. A soldier walking past a brazier is lit warm.<br>**Hero lamp:** every hero visible to the local player carries a soft pool (r 3.2 m, intensity 0.5, #FFE2B0) from 18:30 to 05:30, fading over 1.5 s. Heroes are findable at night by light as well as by ring. Up to 6 carried lights, nearest the focus first.<br>**Targets** (tested in §9): night luminance ≥ 60% of noon; team chroma ≥ 70%. | `unit.gdshader` (combat) includes `world_common`. Placeholders flag team-band vertices in vertex alpha.<br>Carried lights = the 6 `atm_carry_n` globals (x, z, radius, intensity). Atmos picks them at 10 Hz and damps intensity at rate 4/s. | +1 vertex sample per unit; 6 distance tests per terrain fragment | P0 lift + rim / P1 lantern response + lamp |
| WLD-07 | **Sleeping camps ★** | `creep_sleep_changed(unit, asleep, cause)` | **Falling asleep** (dusk; each creep offset by hash 0–4 s):<br>• yawn: sy 1 → 1.08 over 500 ms (`out_quad`), then → 0.92 over 400 ms;<br>• turn to face the camp centre (600 ms `in_out_sine`);<br>• settle (700 ms `out_cubic`): either lie (pitch −10°, y −0.08 h) or curl (sy 0.86).<br>**Asleep:** breathing period 3.6 s (2.8 s awake), amplitude 3% (1.5% awake). CMB-06 "creep notice" is suppressed.<br>**Glyphs:**<br>• One glyph per camp every 2.4 s, from a sleeper chosen round-robin, on its exhale.<br>• A painted "z", cream #EDE6D2, with a 2 px outline in the camp's difficulty colour (easy #6FCF6A, medium #F2B33D, hard #E5533D).<br>• **Stacked 1, 2 or 3 z's by difficulty**, so the tier also reads by shape.<br>• Motion: rise 0.9 m over 2,200 ms (`out_sine`), drift 0.3 m downwind, scale 0.14 → 0.26 m, α 0 → 0.85 (300 ms) → 0 (last 600 ms), wobble ±8° at 0.7 Hz.<br>• Unshaded; ignores night grading.<br>**Campfire** (if any) drops to embers: sprites ×0.4, pool ×0.5.<br>**Snore:** one positional loop per camp (not per creep), only the 2 camps nearest the focus, World −22 dB, amplitude-modulated in sync with the glyph exhale.<br>**Wake when attacked or disturbed:**<br>• startle hop 0.22 m (160 ms `out_quad`), upright snap (120 ms), 3 painted startle strokes above the head (300 ms), growl;<br>• campmates follow in a chain 150–450 ms apart (hashed), so a pulled camp reads as an alarm spreading.<br>**Wake at dawn:** stretch (sy 1.06, 600 ms), then a shake (roll ±6°, 3 cycles in 500 ms).<br>**Fog:** glyphs, snores and wakes only for camps visible to the local player. | Sim hooks in `creeps.gd` (§2). The `sleep` layer goes in the UnitView composer (FND-1). New `src/world/camp_fx.gd`: glyphs as an FxSprites alpha kind using the spare atlas slot; snores via `Audio.loop_3d`. | ≤ 1 sprite per camp per 2.4 s; 2 loops | P0 pose, breathing, glyphs, wake / P1 snore, chain, campfire dim |
| WLD-08 | **Fireflies that fall into step ★** | night 19:00–05:00, weather Clear, Breezy or Overcast; meadow, forest-edge and shore masks | **Look:** core 0.05 m #D8FF6A HDR 2.0, halo 0.22 m #9CFF3A α 0.35, additive. Hover height 0.4–2.0 m. Density 0.06/m² on masked ground, ≤ 160 on screen.<br>**Drift:** a Lissajous path around a home point: (0.6 sin(0.37t + a), 0.25 sin(0.53t + b), 0.6 sin(0.29t + c)) m.<br>**Blink:** a 280 ms cosine pulse per period P = 2.2 s ± 15%.<br>**Synchrony:** phase φ = mix(φᵢ + ωᵢt, Ωt − k·(home · wind_dir), s), where:<br>• s ramps from 0 at 19:00 to 0.85 at 01:00 (smoothstep);<br>• Ω = 2π / 2.2 s;<br>• k = Ω / 20 m/s.<br>Early in the night they blink at random. By midnight the blinks roll across the field in slow waves.<br>**Disturbance:** inside `atm_brawl`, or within 12 m of a shock less than 6 s old, they scatter 1.5 m outward, desync (s → 0) and fade to 40% over 600 ms. They recover over 8 s.<br>Off in rain, in fog (stillness) and at juice 0. | `src/world/air_fx.gd` + `air.gdshader`. One camera-local wrap volume (40 × 40 × 3 m) as a MultiMesh of 256 instances. Home = snapped box origin + fract(seed) × box, so the field stays fixed in world space with zero CPU per frame. Masked by `atm_world_tex.a` and `atm_fog()`. All motion in the vertex shader from `fx_time` and `hour`. | 1 draw, ≤ 256 quads; 1 uniform per frame | P1 |

### 4.2 Sky on the ground, and weather

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-09 | **Cloud shadows and sun breaks** | always; strength from key and weather | **Mask:** a tileable painted cloud mask (256²) at a world scale of 56 m. It drifts with the wind at 0.6 × wind speed (1.2–2.4 m/s).<br>**Coverage c:** Clear 0.25, Breezy 0.35, Overcast 0.70, Drizzle 0.80.<br>**Shadow** = smoothstep(1 − c − 0.12, 1 − c + 0.12, n) × strength (§5: 0.32 at noon, 0.12 at night). It multiplies direct light only: ground and props × (1 − shadow); units × (1 − 0.6·shadow).<br>**Sun breaks:** when c > 0.6, gaps where n < 0.25 get +10% value tinted #FFF0D0, so warm patches roam across an overcast map.<br>**Fog:** in fogged areas strength ×0.3 (WLD-27).<br>The minimap uses the same function at 6% (WLD-34). | `atm_cloud_shadow()` in the include.<br>**Preferred:** multiply directional `DIFFUSE_LIGHT` inside the shared painterly `light()` (art doc §7.5), passing the shadow through a fragment-written varying.<br>**Fallback** (if 4.7.2 cannot pass it, or it costs too much): ALBEDO × (1 − shadow × key_share), where key_share = key / (key + ambient) from the director (≈ 0.65 by day). The spike decides. | 1 sample per fragment | P0 |
| WLD-10 | **One wind: gust fronts you can see and hear ★** | always | **Field:** w = base·(0.75 + 0.25 sin(0.7t + xz·(0.05, 0.03))) + 0.6·g, where g = smoothstep(0.55, 0.85, gust_tex.r((xz − d·v_g·t)/48 m)).<br>• Gust fronts travel at v_g = 4 + 4·base m/s, fast enough to watch them move.<br>• Base by weather: calm 0.15, Clear 0.25, Breezy 0.55, Drizzle 0.40, Mist 0.10.<br>**Direction** d drifts (F3). Everything that points downwind follows it.<br>**What reads:** inside one front, things move in order of position because they sample the same field:<br>1. grass bends first (8° + 22°·w downwind; tips lighten +12% toward sheen #D8E2A0, so a pale band rolls across meadows like wind over wheat);<br>2. then trees (WLD-14);<br>3. then flags (WLD-29);<br>4. then smoke (WLD-28).<br>**Heard:** Atmos samples g at the focus with the CPU mirror. On a rising edge above 0.6 (≥ 6 s apart), a gust "whoosh" 3D source starts 10 m upwind of the focus and travels downwind at v_g for 1.8 s (World −18 dB, randomizer of 4). You hear the gust cross the field you are looking at. Near forest, the leaf-rustle layer gains +6 dB × g (WLD-33). | F3 gust texture + `atm_wind`; CPU mirror `Atmos.gust_at()`. The whoosh is one pooled `AudioStreamPlayer3D` moved in `_process`. | GPU free; CPU 4 samples per frame | P0 field, grass, trees, flags / P1 sheen, whoosh |
| WLD-11 | **Drizzle and rain: the ground tells you** | weather Drizzle or Rain | **Streaks:** a camera-local box 48 × 48 × 18 m.<br>• Count (High / Low): drizzle 450 / 220, rain 900 / 400.<br>• Length 0.3 m (drizzle) / 0.55 m (rain); width 0.012 m; #C8D4E0 at α 0.10 / 0.16.<br>• Fall 8 / 12 m/s, slanted by wind (dx = 0.35·w·fall). Velocity-aligned billboards.<br>**Ground rings:** procedural ripple cells (0.6 m) on terrain and water. Each cell spawns a ring, radius 0 → 0.28 m over 600 ms, α 0.35 → 0, once per 1.4 s (drizzle) or 0.7 s (rain), with hashed phase. Water rings are 1.5× bigger.<br>**Wetness** rises over 40 s and dries over 90 s after the rain ends. Terrain: albedo ×0.82, saturation +6%, roughness 0.92 → 0.40, specular 0.25 → 0.45 (a painted sheen, not a mirror). Trees and roofs ×0.9.<br>**Puddles (P2):** where low-frequency noise > 0.62 **and** (wear > 0.25 or the ground is dirt): a darker patch (albedo ×0.6, roughness 0.15, rings at 2× density). They grow with wetness and shrink as it dries (the threshold animates). **Puddles collect on trodden paths.**<br>**Knock-on effects:**<br>• wet cloth hangs heavy (WLD-29);<br>• torches sputter (WLD-05);<br>• fireflies off;<br>• rabbits and butterflies hide, frogs croak more, birds roost (WLD-22).<br>**Sound:** drizzle bed −28 dB, rain bed −20 dB, mixed by zone: on leaves (forest weight), on water, on roofs (settlement).<br>**Brawl:** streak α ×0.6. | `src/world/weather_fx.gd` + `rain.gdshader`: a MultiMesh whose box origin snaps to 1 m; fall is `fract()` in the vertex shader. Ripples and wetness come from `atm_weather` in the terrain and water shaders. | 1 draw, ≤ 900 quads; about 20 ALU per fragment for ripples | P1 streaks, wetness, rings / P2 puddles |
| WLD-12 | **Morning mist and rolling fog banks** | every dawn 04:30–07:30 (light); weather Mist | **Planes:** two horizontal planes, 64 × 64 m, camera-local and snapped to 1 m, at local lowland height + 0.35 m and + 0.75 m.<br>• Density = fbm((xz − 0.5·w·d·t)/16 m) × lowland mask (`atm_world_tex.b`) × coverage.<br>• α = density × 0.30 (lower plane) / 0.18 (upper).<br>• **Soft contact:** α × smoothstep(0, 0.35, plane_y − terrain_h(xz)). Mist pools in basins and never shows a hard intersection, with no depth texture needed.<br>**Colour:** the fog key lightened 30% (day #E8EEF2, dawn #F2D2C2, night #4A5680). Unshaded. Drawn after opaque, so it covers feet and never torsos.<br>**Dawn burn-off:** coverage 0.6 at 05:00, patches by 06:30, gone at 07:30. The threshold rises, so the mist breaks up rather than fading uniformly.<br>**Fog bank** (Mist weather, 1–2 per state): a 50 m band with 15 m smoothstep edges at coverage 0.9, crossing the lowlands at wind speed (≈ 2 m/s, about 90 s).<br>**Sound:** inside mist, birdsong sweeteners −50%; the settlement layer gets a low-pass. | `src/world/mist_fx.gd` + `mist.gdshader`. `atm_height_tex` gives the soft fade. | 2 transparent quads; fill rate only over lowlands | P1 dawn mist / P2 fog banks |
| WLD-13 | **Light shafts and the air layer** | shafts: 06:00–08:00 and 16:00–18:00, Clear or Breezy; air layer: always | **Shafts:** up to 6, at precomputed forest-edge cells (canopy on the sun side, open ground opposite), nearest the focus.<br>• Each is one quad, billboarded around its own axis, from the canopy top (5 m) to the ground, aligned to `atm_sun`.<br>• Width 1.2–2.0 m; painted vertical gradient; additive #FFE2A8, α 0.08 at the top → 0 at the ground; HDR ≤ 1.0 (no bloom).<br>• Fade 4 s by hour. Each holds 8 dust motes (0.03 m, #FFF1C8 α 0.6, drifting 0.1 m/s).<br>**Air layer** (the same kind of wrap volume as WLD-08, 48 × 48 × 8 m), kind by biome and hour:<br>• Greenvale by day: seed fluff (0.04 m, #F4F0E2 α 0.5, carried at 0.8·w, sinking 0.1 m/s), 128 / 256 / 384 by quality.<br>• Emberwood: falling leaves (0.10 m, #C8642A and #E0A040, flutter 1.1 Hz).<br>• Frostmarch: light snow (P2).<br>Hidden in fog; ×0.3 inside the brawl radius. | `air_fx.gd` (shared with WLD-08). Shafts are a 6-slot MultiMesh. | 2 draws, ≤ 512 quads | P1 air / P2 shafts |

### 4.3 Foliage and ground cover

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-14 | **Tree sway with hierarchy, still in memory** | always | Replaces today's sway, which runs on render `TIME` with one phase pattern everywhere.<br>**Trunk:** lean downwind (0.9° + 2.2°·w)·(y/H)², plus an oscillation of 0.6°·(0.3 + w)·sin(2π·(0.35/scale)·t + φ), with φ from a hash of the instance origin.<br>**Branches:** canopy vertices offset 0.04 m·w·(r/R) at 1.1 Hz, phase per vertex from hash(round(local pos / 0.5 m)).<br>**Leaf flutter:** canopy vertices 0.015 m·(0.3 + g) at 4–6 Hz.<br>**Added on top:** chop shudder (ECO-09) and shock lean (WLD-17).<br>**Stillness:** all amplitudes × the visible mask at the instance origin (eased over 600 ms). A fogged forest stands still (WLD-27).<br>**Other plants** use the same function with other parameters: bushes ×0.6 amplitude, ×1.4 frequency; reeds and cattails lean 6° + 14°·w, with phase per stem. | `tree.gdshader` + new `foliage.gdshaderinc` (`atm_sway(vertex, origin, H, params)`). One MultiMesh per chunk (tech §4.4). Weights come from height and radial distance, so AI-generated GLBs need no vertex-colour masks. | about 25 ALU per vertex | P0 |
| WLD-15 | **Grass tufts and flower patches** | map load; footprints; wear; time of day | **Tufts:** 3 crossed quads, 0.28–0.38 m tall, 0.35 m wide, from a painted alpha atlas (4 grass + 4 flower variants). Alpha scissor 0.5; shadows off.<br>• Root colour = the terrain colour at that spot (sampled at placement); tips ×1.1 lighter.<br>• Greenvale grass #6E9A3E, thick #4F7A2E.<br>**Density:** 2.2 / 1.4 / 0.7 tufts per m² (High / Med / Low) × grass weight (grass, dark grass and dry-grass layers) × (1 − wear). Zero on paved and rock, water, tree cells, the 0.5 m cliff-edge band and **known** footprints.<br>**Flowers:** low-frequency noise > 0.72 makes a patch, and 30% of tufts in it become flowers in the biome palette (Greenvale #F2E86B, #F4F1E8, #C792EA; saturation ≤ 60%). Size jitter 0.8–1.25, random yaw.<br>**Distance fade:** scale and scissor ramp to 0 between 34 and 42 m from the camera.<br>**Footprints:** the linear-filtered mask shrinks edge tufts instead of popping them.<br>**Flowers keep hours ★:** heads close at night (petal scale 1 → 0.6, value ×0.8), staggered by hash over 12 s from 18:30, and reopen from 06:15. P2: "sunbell" heads turn their yaw toward the sun. | `src/world/grass.gd` + `grass.gdshader`: one MultiMesh per 16 × 16-tile chunk (36 on the slice), built lazily the first time a chunk is in view, with `custom_aabb` per chunk. Footprint mask from `atm_mask_tex`. | ≤ 6k tufts (about 70k vertices) on screen at High; 4–9 draws | P1 / P2 sun-tracking |
| WLD-16 | **Trample and wakes** | units on screen | **Tramplers:** up to 24 per frame (8 on Low), picked in this order: heroes, selected, large, then moving units nearest the focus. On-screen only.<br>Each is a capsule from the unit's `display_pos()` back along its velocity for 0.6 s of travel (≤ 1.8 m), radius = unit radius + 0.25 m.<br>**Bend** per tuft vertex: away from the capsule axis by 0.18 m·f·(y/H) and down by 0.08 m·f, where f = 1 − smoothstep(0.6r, r, distance).<br>Strength is 1 at the head and falls linearly to 0 at the tail, so grass springs back behind a walking unit: a visible wake through a meadow.<br>Standing units flatten a ring under their feet (no tail). | Material uniform arrays on the grass material: `vec4 trample_a[24]` (x, z, radius, strength) and `vec4 trample_b[24]` (tail dx, dz). Filled each frame. | 24 capsule tests per vertex (8 on Low); CPU ≤ 0.04 ms | P1 |
| WLD-17 | **The world flinches: shock rings ★** | `Atmos.shock(pos, strength)`, only if pos is visible. Callers: siege impacts (0.5), building collapse (0.8; halls 1.0), hero ultimates (heroes doc, 0.6–1.0) | **Ring:** front speed 14 m/s, max radius 6 + 10·strength m, life 2.5 s.<br>**Grass:** at the front, flattened outward by 35°·strength·e^(−(r − 14t)²/1.28)·e^(−t/0.9). Behind the front it springs back with a damped wobble (ω = 2π·2.2 Hz, ζ = 0.3). You see a ring of pale, flattened grass race out from the blast.<br>**Trees:** lean away by θ = 3.5°·strength·(1 − r/R)·e^(−1.6τ)·sin(2π·1.4τ), where τ = t − r/14, so farther trees flinch later. Canopies within 8 m drop 2–4 LEAF (BallisticFx).<br>**Life:** critters and birds within 20 m flee or take off (WLD-21, 23); fireflies scatter (WLD-08).<br>**Slots:** 4, LRU. Shocks within 4 m and 150 ms merge (max strength). No camera shake here; the camera doc owns that. | 4 globals `atm_shock_0..3` (x, z, t0, strength), read by `foliage.gdshaderinc` and `grass.gdshader`. | 4 tests per vertex | P1 |

### 4.4 Water

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-18 | **Shoreline foam and the breathing wet line** | always, on water | d = shore signed distance in metres (+ in water, − on land), from `atm_world_tex.g`.<br>**Foam band:** α 0.7·(1 − smoothstep(0, 0.9, d)), broken up by painted stroke noise. Colour #EEF6F2 with a darker edge #9FC9C8.<br>**Lapping lines:** 0.5·smoothstep(0.75, 0.95, sin(6d − 2π·t/2.2 s + 3·noise))·(1 − smoothstep(0.3, 2.2, d)). A foam line rolls in every 2.2 s.<br>**Wet line on land:** terrain within 0.6 m of the water darkens by 20% (multiply #3E3326). The line advances and retreats 0.25 m in step with the lapping period, with a thin bright foam lip at the waterline.<br>**Wind > 0.6:** sparse whitecaps on deep water (α 0.4).<br>**Fog:** amplitudes ×0.1 (still water). | `water.gdshader` and `terrain.gdshader` read d. The BFS runs over 1 m cells at load (about 40 ms on the slice, `world_maps.gd`). | about 15 ALU per fragment | P0 |
| WLD-19 | **Water surface: painted shimmer, glints, time of day, splashes** | always | Replaces today's noise-normal water.<br>**Colour:** biome shallow and deep (Greenvale #4FA3A0 / #22566E) graded by the key; at night #2E5C7A / #0E2A44. The shallow band (0–2.5 m) comes from the shore distance.<br>**Shimmer:** two painted stroke normal maps scrolling downwind at 0.06 and 0.11 m/s, strength 0.35 + 0.4·w.<br>**Glints** (a VFX term): pow(max(n₁·n₂, 0), 18)·(0.4·daylight + 1.0·golden), colour #FFF3D6, HDR ≤ 1.3, kept under 2% of water pixels. At night: silver moon glints #C9D6FF × 0.6·night.<br>**Rain rings:** the WLD-11 cells ×1.5.<br>**Splashes:** `Atmos.water_splash(pos, size)` for anything landing in water (missed projectiles, debris, falling trees, fish):<br>• a crown of 6 droplets (#D8EEF2, up 1.6–2.4 m/s, life 450 ms);<br>• 2 rings (0.3 → 1.2 m over 900 ms);<br>• a plop (World −16 dB, ≤ 3/s).<br>**Fog:** animation ×0.1, glints off. | `water.gdshader` (with the include). Rings use the FxSprites ring kind on the water plane. Combat and economy call `water_splash()` when a landing point is over water (`MapData.is_water_tile`). | about 30 ALU per fragment | P0 colour + shimmer / P1 glints + splashes |
| WLD-20 | **Wading: rings, bow wake, entry splash** | a unit's depth = water_level − height_at(display_pos) > 0.05 m | **Requires shallow fords** (`water` = 2, §2).<br>**Entry** (depth crosses 0.05 upward): a splash crown of 6 droplets and a "sploosh" (World −14 dB, ≤ 3/s).<br>**Moving:** CMB-04 already places a ring per stride. Add a bow wake: a ring every 220 ms at pos + 0.3 m ahead, r 0.25 → 1.4 m over 1,100 ms (`out_quad`), α 0.45 → 0, #E3F2F5. Overlapping rings form the V.<br>**Idle in water:** a slow ring every 1.8 s, r 0.2 → 0.9 m.<br>**Group slosh:** one loop, not one per unit, scaled by the number of on-screen units in water: 1–3 at −22 dB, 4+ at −16 dB.<br>**P2 caustics:** a cheap voronoi caustic on the ford bed (×0.15, by day only). | `unit_view.gd` → `Vfx` → FxSprites ring kind. Tier rules as CMB-04: Busy keeps importance ≥ 3; Brawl keeps rings only. The map hook needs gameplay sign-off. | ≤ 5 spawns/s per wading unit | P1 (blocked on fords) |

### 4.5 Life

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-21 | **Life layer: critters that notice, flee and hide** | always; simulated only near the camera | Visual-only animals. They are not entities: never selectable, never blocking, never dying.<br>**States:**<br>• CALM: idle, graze, micro-wander 0.5–2 m every 3–8 s.<br>• ALERT: head up and turn to the threat over 300 ms (`in_out_sine`), held while a threat is within 9 m.<br>• FLEE, triggered by any of: a threat within 5 m; a visible hit within 14 m; a shock within 20 m; a projectile landing within 6 m. Runs 8–14 m away from the threat, ±35°.<br>• HIDE: species-specific (table 4.5a).<br>• RECOVER: back home after 10–25 s with no threat inside 12 m.<br>**Threat = a unit visible to the local player** (or the player's own unit). Critters stand on visible cells only; in fog they are not drawn. **They are never a radar.**<br>**Motion** = closed-form segments (from, to, t0, duration, gait curve), so poses are exact at any frame rate. Flee targets are validated with `pathing.is_walkable_world` and must be on the same cliff level.<br>**Poke ★:** a left-click that selects nothing tests critters within 18 px. Sheep bleat and hop 0.15 m; rabbits bolt; frogs leap; birds scatter. The selection is unchanged.<br>**Sheep gag:** the 6th poke on the same sheep within 5 s makes it faint stiff-legged:<br>• topple 90° in 180 ms (`out_back`);<br>• hold 2.6 s with two leg twitches;<br>• get up in 400 ms, then shake for 300 ms. | `src/world/life.gd` (`class_name Life`, `World/Life`), with Packed* arrays.<br>10 Hz logic, only for critters inside the camera rect + 12 m (≤ 40). Threat queries use `world.spatial.query_radius` plus the Fog check.<br>One MultiMesh per species; the CPU writes poses for on-screen critters only (≤ 40 writes per frame).<br>`selection.gd` calls `Life.poke(screen_pos)` when its pick comes back empty. | ≤ 0.12 ms per frame | P1 |
| WLD-22 | **The Greenvale cast** (table 4.5a) | placement at load from the biome table (own RNG) | Sheep, rabbits, frogs, songbirds, butterflies and fish. Exact sizes, colours, gaits, hides and sounds are in table 4.5a below.<br>**At night:** sheep lie down and huddle; rabbits and butterflies are gone; frogs are active; songbirds roost.<br>**In rain:** rabbits and butterflies hide; frogs croak twice as often; birds roost. | `data/biomes.json` → `critters`. Placeholders from `ProcMesh`:<br>• rabbit = 2 spheres + ears;<br>• sheep = 5-sphere wool cloud + head;<br>• frog = squashed sphere + eyes;<br>• bird = a 3-tri body + 2 wing tris.<br>GLBs replace them later. | included in WLD-21 | P1 sheep, rabbits, birds, frogs / P2 butterflies, fish |
| WLD-23 | **Startled flocks and sweeping shadows ★** | a threat within 6 m of a perch; a visible hit within 14 m; a shock within 25 m; a poke | **Take-off:** members leave over 0–250 ms (staggered), with an 8–9 Hz wing burst for 1.0 s and one "frrrt" flutter per flock (World −16 dB).<br>**Flight:**<br>• a cubic Bézier from perch P0 to a new perch P1 20–45 m away, chosen away from the threat and ≥ 15 m from visible units;<br>• control points 8–12 m up, with a 6 m lateral swirl;<br>• duration = dist(P0, P1) / 7 m/s + 2 s;<br>• members orbit the curve at 0.8–1.4 m offsets (hashed);<br>• flap 7–9 Hz while climbing; glide on descent with 2–3 flap bursts;<br>• landing: the last 1.2 s `out_cubic`, then a hop.<br>**Ground shadow:** each bird casts a soft dot on the terrain below (0.25 m, α 0.25·(1 − h/20 m)). A flock's shadow skims over your army: a free depth cue for a top-down camera.<br>**Carrion circle (P2):** after ≥ 5 visible deaths within 30 s in a 20 m area, 2–3 large birds circle at 14–18 m (radius 6–9 m, period 9–12 s). Their 0.9 m soft shadows sweep the battlefield. They glide off-map 45 s after the last death there. Max 1 circle. | `src/world/flocks.gd` + `bird.gdshader`: one MultiMesh (≤ 96 birds) plus one shadow MultiMesh. The CPU writes instance data only at take-off and landing (P0, P1, controls, t0, duration, member index). All flight runs in the vertex shader from `fx_time`; shadow height comes from `atm_height_tex`. | 2 draws; about 0 CPU between events | P1 / P2 carrion |
| WLD-24 | **Aftermath: the silence and the first bird ★** | a fight on screen ends: Vfx intensity (FND-3) was Busy or higher with ≥ 3 visible deaths, then stays 0 for 2.5 s | **Silence:** during the fight the Ambience bus sits at −5 dB (Busy) or −8 dB (Brawl), with a 500 ms attack. Afterwards the beds return over 6 s (`in_out_sine`), but the birdsong layer only over 12 s.<br>**First bird:** at +2.5 s, one positional call at the fight's centroid. By day a songbird trill; at night a two-note owl call (3D, World −12 dB). The first sound after a battle is a living one.<br>**Crows (P2):** 2–4 crows land near fresh corpses 3–8 s after the fight ends (WLD-23 flight from off-screen). They hop and peck (head bob 4 Hz) and leave when a unit comes within 4 m or the corpse decays (CMB-31).<br>Never during a fight; at most once per area per 60 s. | `ambience.gd` ducks the bus with `AudioServer.set_bus_volume_db` and `damp`. Crows come from `flocks.gd`. Reads Vfx intensity and death positions. | negligible | P1 silence + first bird / P2 crows |

**Table 4.5a: the Greenvale cast (slice biome)**

| species | where and how many | size and colours | idle | flee and hide | sound | night / rain |
|---|---|---|---|---|---|---|
| Sheep | flocks of 3–5 near farms and neutral fields; 2 flocks on the slice | 0.55 m tall; wool #EDE6D6, face and legs #3A332E | graze head-down 2.5–5 s; chew bob 3 Hz, 0.01 m; step 0.3 m every 4–9 s | trot 3.2 m/s with a 0.06 m bounce at 4 Hz; the flock regroups 2 m apart; no hide (huddle) | bleat sweetener once per 20–40 s per flock (World −20 dB); poke bleats | lie down and huddle / huddle |
| Rabbit | 1 per 600 m² of meadow (cap 24); home = a burrow mound prop (0.4 m) | 0.22 m; #A68B6B, tail #EDE3D0 | nose twitch bursts at 8 Hz; sit up for 1.5 s; hop 2.4 m/s (0.25 m apex, 260 ms per hop, landing squash 0.85 for 60 ms) | 5 m/s zigzag, 3 legs alternating 40°; within 6 m of its burrow it dives in (shrinks into the mound in 180 ms) and reappears after 15–30 s | a rustle on the dive (−26 dB) | gone from 19:00 / hidden |
| Frog | 1 per 15 m of shoreline (cap 16), on shore points and lily pads | 0.10 m; #5E8A3A, belly #C9C27A | throat pulse (scale 1.0 → 1.35 per croak) | 0.8 m leap into water in 300 ms with a splash ring; hides underwater 10–20 s; resurfaces eyes-only for 2 s, then climbs out | night croaks come from real frog positions when visible (WLD-33) | active / croaks ×2 |
| Songbird | flocks of 5–9 on perches (tree-line edges ≥ 12 m from buildings, neutral roofs, fences) and ground feeding spots | 0.12 m; back #6B5A48, breast #C9603A | hop-peck: 0.2 m hops, 4 Hz peck bursts | take-off (WLD-23) | twitters by day | roost; if disturbed, flutter and resettle 2 m away / roost |
| Butterfly | 08:00–17:00, Clear or Breezy, over flower patches only (≤ 24 visible) | 0.08 m span; flower-palette colours | wings scale-x by \|sin(2π·9t)\|; Lissajous path 1.2 m wide at 0.5–1.2 m height | rise 2 m and drift downwind | none | gone / gone |
| Fish | deep water; 1 jump per 25–45 s per visible lake | 0.3 m silhouette #7E8C8A | arc 0.6 m high over 500 ms | n/a | "plip" (World −24 dB) + WLD-19 rings | same / same |
| Lily pads, reeds | props at shores | pads #5E8A3A; reeds #6E7A3E | pads bob 0.01 m and rotate ±3° with ripples; reeds sway (WLD-14) | n/a | none | still in fog |

### 4.6 Fog of war

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-25 | **Smooth, breathing fog edge** | every frame; fog uploads (about 4–10 Hz) | **Temporal smoothing:** `Fog` alternates uploads between textures A and B. The shader blends previous → current over the measured upload period (clamped 80–400 ms): f = mix(prev, cur, smoothstep(0, 1, (fx_time − t_upload)/period)). Revealed areas grow continuously instead of stepping at the fog rate, and the sim's shrinking night sight reads as the dark closing in.<br>**Painterly edge:** v = f + (n − 0.5)·0.18, where n = painted brush-stroke noise at xz / 4.8 m, drifting 0.05 m/s downwind. Explored = smoothstep(0.14, 0.34, v); visible = smoothstep(0.64, 0.82, v). The edge is a soft brushed wobble that slowly breathes, never a grid.<br>**Inner vignette:** the outer 1.5 m of the visible area darkens 8%.<br>Fogged value: ×0.55 by day, ×0.45 at night (WLD-27). | `fog.gd`: double buffer and `atm_fog_blend` (t_upload, period, flip). `atm_fog()` and `atm_memory_grade()` from the include are used by terrain, trees, water, grass, props and building ghosts. | 3 samples per fragment | P0 |
| WLD-26 | **A sea of cloud over the unknown, and the cartographer's reveal** | unexplored areas | **Base** #0A0C12.<br>**Two cloud layers:** fbm at 38 m and 22 m scales, drifting with the wind at 0.3× and 0.45×, with **fake parallax** (uv offset = −V.xz / V.y × 6 m and × 11 m), so the clouds slide against the ground as the camera pans.<br>Cloud value = mix(#0A0C12, #222A44, smoothstep(0.45, 0.8, c)·0.7). Sun-side tops get +#2A2F4A by day, silver #1C2238 at night.<br>**Ink rim:** along the explored boundary, a 0.6 m wobbly ink line, #05060A α 0.45. The known world looks drawn onto a map.<br>**Map skirt:** a 40 m ring mesh around the map uses the same shader, so the edge of the world is cloud, never a void.<br>**Reveal (P2):** cells explored for the first time flash a parchment edge (#E9D9B0 α 0.35) for 600 ms. Implemented as a CPU queue of new cells plus an RG8 "discovered at" texture, cleared after 2 s. | Terrain, tree and water shaders via the include. `TerrainBuilder` adds the skirt mesh. | about 25 ALU per fragment, only where unexplored | P1 / P2 reveal |
| WLD-27 | **The remembered world: still, faded, sketched ★** | explored-but-not-visible areas | **Grade:** saturation ×0.4, value ×0.55 (×0.45 at night), multiply #9DB3D6 at 15%, and paper grain (a tileable 128² painted paper at 2 m, ±6%). P2: faint hatching in shadowed parts (4%). Building ghosts get the same grade.<br>**Stillness, ramped over 600 ms:**<br>• Moves at reduced amplitude: foliage, grass and cloth × the visible mask; water animation ×0.1 (a glassy lake); cloud shadows ×0.3.<br>• Hidden: critters, fireflies, air motes, smoke and flame sprites (window emission stays).<br>• Rain streaks still fall (weather is "now"), but ground rings stop.<br>**Tree memory:** a tree felled outside your vision stays drawn until you see its cell again; then it fades out over 300 ms and leaves a stump. No topple plays (ECO-11 needs a visible fall).<br>The rule players learn without being told: **if it moves, you can see it.** | All via `atm_fog()` and `atm_memory_grade()`. The StreamFx and AirFx shaders multiply α by visibility. `doodads.gd` holds `remembered_felled` and listens to fog updates. | 2 ALU + 1 sample | P0 grade + tree memory / P1 stillness, grain |

### 4.7 Settlement and memory

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-28 | **Hearth smoke, and one wind for all smoke** | non-production structures (farms, houses, neutral buildings) 17:00–08:00 and in rain; creep campfires always | **Hearth wisp:** one column per chimney. A puff every 1,400 ms, 0.25 → 1.1 m, rise 0.6 m/s, life 3.2 s, α 0.22. Colour #B7B0A6 by day, #6E6A75 at night, with the lowest 0.4 m tinted #FFB86B at 15% (lit by the hearth).<br>Production buildings never get hearth smoke, so BLD-11's "cold chimney = idle" stays true.<br>**All smoke** (hearth, BLD-11, BLD-15 fires, campfires, ignition puffs) drifts by wind·age^1.4·0.6 m + g·age·0.4 m. Every column on the map leans the same way and kinks when a gust front passes through it.<br>Cap: 12 hearth columns (nearest the focus). Hidden in fog. | The StreamFx shader (economy §2.3) gets the wind term from the include. `building_fx.gd` spawns hearth streams from def `fx.chimney` when `fx.hearth` is true (the default for supply buildings). | ≤ 12 × 3 sprites | P1 |
| WLD-29 | **Cloth: banners, flags, pennants, tents** | always | **Displacement** along the cloth normal: A·u^1.4·sin(2π(u/0.9 − f·t) + φ), where:<br>• u = distance from the pole (UV.x);<br>• A = 0.06 + 0.10·w (+ 0.05·g) m;<br>• f = 1.4 + 1.6·w Hz.<br>Low wind droops the tip up to 35°·(1 − w).<br>**Free flags yaw downwind** (smoothed by the director's damped wind direction). Every flag on the map points the same way and swings together when the wind turns.<br>**Wet cloth:** A ×0.7, f ×0.8, droop +10° while wetness > 0.5.<br>**Spikes:** FLUTTER_SPIKE (economy §2.4) from rally sets and hits adds on top.<br>Team-colour regions keep their hue. Amplitude is capped at 0.25 × cloth length, so flutter never hides the ownership area. Still in fog. | `cloth.gdshaderinc` (`atm_cloth(vertex, uv, pole_axis)`) is used by building banners, rally flags (CMB-12, BLD-13), unit back-banners and tents. GLB cloth materials are named `*CLOTH*`, or use a vertex-colour mask. | about 15 ALU per vertex | P0 |
| WLD-30 | **Desire paths: the map remembers where you walked ★** | 4 Hz poll of moving units (speed > 0.5 m/s) that are visible to the local player | **Wear W** (R8 at 1 m, `atm_world_tex.r`):<br>• +1 at the unit's cell (+2 for heroes and large units);<br>• +1 to the 4 neighbours on every second poll, so paths are about 1.5 m wide;<br>• saturates at 255;<br>• heals −1 per 20 s on cells not walked (1/80 of the texture swept per poll).<br>**Look:** grass layers blend toward a trodden colour (Greenvale #8C7A55), up to 55% at W = 1, with noise-broken edges. Tuft density ×(1 − W). Dirt layers get a 6% darker, smoother centre line.<br>**What appears:** the hall–mine trail forms in about 8 minutes of mining. Army routes and creep-camp approaches show by mid-game. A finished match leaves its story on the ground.<br>**Honesty:** only units the local player could see at the time add wear, so there are no tracks from unseen armies. Paved roads are unaffected. Puddles prefer wear (WLD-11). | `src/world/wear.gd`. Uploads at 1 Hz (36 KB). The minimap reads it (WLD-34). | ≤ 0.15 ms per poll; 1 sample per fragment | P1 |
| WLD-31 | **World memory ledger and battlefield bloom** | corpse removal, rubble, stumps, stains, wear, felled trees | **One persistence policy across domains** (table 4.7a), enforced by `WorldMemory`: lifetime, cap, fade and fog rule per kind.<br>A single setting, `world_memory`, scales lifetimes: Short ×0.5, Normal, Long ×2.<br>**Rules:** memory never animates; it never adds hue, only darkens or desaturates; it is created only from events the local player saw; in fog it shows the last seen state.<br>**Battlefield bloom ★ (P2):** when a ground stain expires on grass-weighted terrain (≥ 0.5), 3–6 flower tufts sprout over 1.2 s (scale 0 → 1, `out_back` 1.3) inside the stain. They stay 4 min, then shrink over 3 s. Cap 64 clusters. Old battlefields flower. | `src/fx/world_memory.gd` holds the caps and budgets for CMB-32 ground marks, BLD-16 rubble and ECO-11 stumps. Bloom tufts reuse the grass MultiMesh (a reserved block of 384 instances). | bookkeeping only | P1 ledger / P2 bloom |

**Table 4.7a: the world memory ledger** (lifetimes at `world_memory` = Normal)

| memory | owner row | lifetime | cap | fade | fog rule |
|---|---|---|---|---|---|
| Corpse | CMB-30/31 | 8 s (sim decay) | sim | team-colour ebb, then sink | the sim hides enemies in fog |
| Ground stain | CMB-32 | 90 s | 96 | last 20 s | created only if seen; dimmed in fog |
| Siege scorch | CMB-27/32 | 120 s | 48 | last 30 s | same |
| Rubble | BLD-16 | 90 s | 24 | 4 s | same |
| Stump | ECO-11 | the whole match | 4,096 | none | same; a felled tree in fog stays drawn until seen (WLD-27) |
| Desire path | WLD-30 | heals −1 per 20 s | texture | gradual | only seen units add wear |
| Grass clearing (footprint) | WLD-15 | while the structure stands, or while its ghost is known | texture | 300 ms | known structures only |
| Battlefield bloom | WLD-31 | 4 min | 64 | 3 s shrink | only from seen stains |
| Carrion circle | WLD-23 | until 45 s after the last death there | 1 | glide away | only seen deaths |

### 4.8 Sound of the world

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-32 | **Area ambience beds** | 4 Hz, at the listener focus | **Zone map:** 8 m cells, each with 6 layer weights computed from the map at load:<br>• meadow (grass tiles);<br>• forest (tree density / 16);<br>• water (water tiles + shore ≤ 6 m);<br>• highland (cliff level ≥ 2);<br>• settlement (own and allied structures in the cell, refreshed at 1 Hz);<br>• camp (a creep camp within 12 m);<br>• blight, later.<br>Weights are sampled with a 3 × 3 Gaussian around the focus.<br>**Layers:** each has a day loop and a night loop (60–120 s, seamless, −24 LUFS):<br>• meadow: larks, insects, soft wind / crickets;<br>• forest: leaf rustle, woodland birds / distant owls, rustle;<br>• water: lapping, a stream / frogs;<br>• highland: open wind / colder wind;<br>• settlement: a distant life murmur (carts, a dog, hearth crackle) / a quiet murmur and crickets;<br>• camp: low animal breathing and snorts / the snore texture (WLD-07).<br>**Mix:** gain_dB = lerp(−40, 0, √w), damped at rate 1.2/s. At most 4 layers play; a layer stops after 3 s below w = 0.03. Day and night pairs crossfade over 8 s at dawn and dusk (WLD-04).<br>**Zoom:** for every 10 m beyond the default distance, wind +1.5 dB and detail layers −1.5 dB.<br>**Weather layers:** wind (−30 dB + 14·g at the focus); drizzle and rain (WLD-11); mist adds no layer but cuts birdsong 50%.<br>**Combat:** ducking per WLD-24. | `src/world/ambience.gd` (or `Audio` additions per audio doc §6.3). The Ambience bus carries the Voice sidechain (audio doc §3.5). One `AudioStreamPlayer` per active layer (≤ 6 including weather). | ≤ 6 streams; CPU about 0.02 ms | P0 day/night × meadow, forest, water / P1 the rest |
| WLD-33 | **Positional emitters and sweeteners** | a scheduler every 0.5 s | **Emitters** (static props; pooled `AudioStreamPlayer3D`, ≤ 6 loop slots):<br>• shore lapping at the 2 nearest shore points;<br>• crackle at the 2 nearest campfires or braziers;<br>• 1 stream or waterfall;<br>• 1 forest-edge rustle (gain from the gust g).<br>They are re-chosen every 0.5 s within 30 m, and swaps crossfade over 400 ms.<br>**Sweeteners:** a one-shot every 4–12 s at a point 18–35 m from the listener, chosen by the zone weight at that point (4 rejection tries).<br>• Day: lark trill, woodpecker (forest), sheep bleat (near a flock), fish plip (lake).<br>• Night: owl, frog croak (from a real visible frog when one is near), cricket swell.<br>• Never the same sample twice in a row (`AudioStreamRandomizer` no-repeat); pitch 1.06; volume ±2 dB.<br>The gust whoosh (WLD-10) and the first bird (WLD-24) use the same pool.<br>Static ambience may play in fog, since it carries no unit information. Creature sweeteners never follow units. | `ambience.gd` with `Audio.loop_3d` and `play_3d` (economy §2.3 additions). The listener sits at the focus + 6 m (audio doc). | ≤ 6 loops + 1 one-shot | P1 |

### 4.9 Minimap

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| WLD-34 | **Living minimap** | base refreshed at 1 Hz; overlay every frame | **Base:** a baked painted map at 2 px per tile: terrain layer colours, cliff edges darkened 25%, water by depth, trees as dark-green dots. Refreshed at 1 Hz for felled trees (as remembered, WLD-27) and wear.<br>**Overlay shader** (drawn under the unit dots):<br>• unexplored: #07080C with the WLD-26 cloud drift, very faint (4%);<br>• fogged: ×0.6 and desaturated;<br>• night: multiply #7F8CB8 (≤ 20% darker);<br>• cloud shadows at 6%, in sync with the world;<br>• water shimmer: diagonal bands, ±4%;<br>• desire paths: 12% toward the trodden colour;<br>• **the nightfall and first-light band crosses the minimap at the same moment as the world.**<br>**Camps:** at night the camp icon shows a small z-glyph stack (1–3) while the camp sleeps (visible camps only).<br>Unit dots, pings and the camera trapezoid (UI doc) are drawn on top and never graded. | `src/ui/minimap.gd`: a `TextureRect` with `minimap_overlay.gdshader` (canvas_item), which samples the same fog A/B, wear, cloud and front globals. `_draw()` keeps the dots and icons. | 1 canvas draw; ≤ 0.05 ms | P1 |

---

## 5. Time-of-day keys (Greenvale; other biomes apply offsets)

| key (hour) | name | light | energy | ambient | amb. energy | depth-fog colour | saturation | contrast | shadow α | cloud strength | glow |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 00:00 | Midnight | moon #8EA6FF | 0.38 | #3B4A80 | 0.50 | #1E2648 | 0.94 | 1.04 | 0.32 | 0.12 | 0.85 |
| 04:30 | Pre-dawn telegraph | moon #9AAEF5 | 0.32 | #45508A | 0.50 | #2A3156 | 0.96 | 1.03 | 0.28 | 0.12 | 0.85 |
| 05:40 | Dawn swap | #B9A6D8 (moon → sun) | 0.06 | #6A6496 | 0.54 | #8C7FA8 | 1.00 | 1.02 | 0.00 | 0.10 | 0.80 |
| 06:30 | Dawn | sun #FFB38A | 0.72 | #8E8AB8 | 0.55 | #E8B7A0 | 1.08 | 1.03 | 0.45 | 0.22 | 0.75 |
| 08:00 | Morning (match start) | sun #FFE7C4 | 1.00 | #9DB3D6 | 0.55 | #CFE3F0 | 1.08 | 1.02 | 0.60 | 0.30 | 0.70 |
| 12:00 | Noon | sun #FFF4E2 | 1.12 | #A6BAD8 | 0.58 | #D6E6F2 | 1.06 | 1.02 | 0.62 | 0.32 | 0.70 |
| 16:30 | Golden telegraph | sun #FFC98A | 1.05 | #9C9CC8 | 0.52 | #F2D3A8 | 1.12 | 1.05 | 0.66 | 0.30 | 0.72 |
| 17:40 | Sunset | sun #FF9A5C | 0.72 | #8A7FB4 | 0.50 | #E89A7A | 1.12 | 1.05 | 0.50 | 0.26 | 0.75 |
| 18:15 | Dusk swap (blue hour) | #6E78C8 (sun → moon) | 0.06 | #4E5A9A | 0.52 | #3A4478 | 1.00 | 1.03 | 0.00 | 0.12 | 0.80 |
| 19:30 | Night | moon #8EA6FF | 0.38 | #3B4A80 | 0.50 | #1E2648 | 0.94 | 1.04 | 0.32 | 0.12 | 0.85 |

These values sit inside the art doc's ranges: day sun #FFF0D8-ish at 1.0–1.15; ambient #9DB3D6 at 0.45–0.6; moon #8EA6FF at 0.35–0.45; night ambient #3B4A80. Night ambient is raised to 0.50 for readability. The keys are tuned for the art doc's tonemap (Linear or Reinhard, white ≈ 1.5) and must be re-tuned if the tonemap changes.

**Derived `atm_day` channels** (bump(a, b, c) = smoothstep(a, b, h) × (1 − smoothstep(b, c, h))):

| channel | definition |
|---|---|
| daylight | smoothstep(5.7, 7.0, h) − smoothstep(17.0, 18.25, h) |
| night | clamp(1 − smoothstep(5.0, 6.2, h) + smoothstep(18.0, 19.2, h), 0, 1) |
| golden | max(bump(16.3, 17.1, 17.9), 0.6 × bump(6.0, 6.7, 7.6)) |
| blue hour | max(bump(17.9, 18.25, 18.8), bump(5.2, 5.6, 6.0)) |

---

## 6. Weather states (Greenvale)

| state | weight | duration | wind base | gust speed (m/s) | cloud cover | wetness target | streaks | mist | notes |
|---|---|---|---|---|---|---|---|---|---|
| Clear | 0.42 | 150–300 s | 0.25 | 5.0 | 0.25 | 0 | none | 0 | always for the first 180 s of a match |
| Breezy | 0.22 | 120–240 s | 0.55 | 6.2 | 0.35 | 0 | none | 0 | gust whooshes become frequent; flags stand out |
| Overcast | 0.12 | 120–240 s | 0.35 | 5.4 | 0.70 | 0 | none | 0 | sun breaks roam (WLD-09) |
| Drizzle | 0.12 | 90–180 s | 0.40 | 5.6 | 0.80 | 0.7 | drizzle | 0 | |
| Rain (light) | 0.04 | 60–120 s | 0.50 | 6.0 | 0.85 | 1.0 | rain | 0 | only after Overcast or Drizzle |
| Mist | 0.08 | 120–200 s | 0.10 | 4.4 | 0.45 | 0.2 | none | 0.9 | may only start between 02:00 and 07:00 |

**Rules:**
- No state repeats twice in a row, except Clear.
- Transition times: wind 10 s, clouds 25 s, wetness rising 40 s and drying 90 s, mist 20 s.
- The schedule comes from its own seeded RNG and is indexed by sim time (F3). Every client, observer and replay sees identical weather.
- Weather is visual only. Sight, speed and combat never change.

---

## 7. Our own twists (what WC3 did not have)

Each twist either reports a real game fact or gives the world a body. None of them changes an outcome.

1. **Nightfall tide and first light (WLD-03).** Night does not dim like a dial. It sweeps across the battlefield as a soft ink band, east to west, lighting torches as it passes, and the minimap shows the same band at the same moment.
2. **Golden hour as a telegraph (WLD-02).** About 30 s of warm, long-shadowed light announces dusk. Creeping players feel the clock instead of watching it.
3. **The lantern map (WLD-F4, 05, 06).** Hundreds of torches, braziers and windows light the ground *and the units walking past them* for the price of one texture. WC3 nights were a tint; ours are lit.
4. **Hero lamp (WLD-06).** At night, heroes carry a soft pool of light, so they are findable by light as well as by ring.
5. **Sleep glyphs count the camp's tier (WLD-07).** One, two or three stacked z's in the difficulty colour. A sleeping camp tells you how hard it is, readable by shape.
6. **Fireflies fall into step (WLD-08).** They blink at random at dusk and synchronise into rolling waves by midnight. A nearby fight breaks the spell.
7. **One wind, seen and heard (WLD-10).** A gust front bends grass, then trees, then flags, then smoke, in the order it reaches them, and its whoosh crosses the screen at the same speed.
8. **The world flinches (WLD-17).** Big impacts flatten a ring of grass that races outward, and trees lean away in a delayed wave.
9. **Puddles on trodden paths (WLD-11 + 30).** Rain collects where armies and workers walked.
10. **The breathing wet line (WLD-18).** The shoreline's wet sand advances and retreats with the foam.
11. **Poke the wildlife (WLD-21).** WC3's "click it until it reacts" spirit, moved to the world: sheep bleat, rabbits bolt, birds scatter, and the sixth poke makes a sheep faint stiff-legged. (WC3's exploding critter gag is not copied.)
12. **Bird shadows and the carrion circle (WLD-23).** Flock shadows skim over armies, and after a slaughter big birds circle, their shadows sweeping the field.
13. **Aftermath (WLD-24).** After a battle the world holds its breath, then the first sound back is a single bird at the place where it happened.
14. **A sea of cloud with parallax, and an ink rim (WLD-26).** The unknown is a drifting cloud layer that slides against the ground as you pan. The known world looks inked onto a map.
15. **If it moves, you can see it (WLD-27).** Remembered areas are still, faded and paper-grained. Vision becomes a felt texture.
16. **Tree memory (WLD-27).** Trees felled out of your sight stay standing in your memory until you look again. The fog never leaks lumber activity.
17. **Desire paths (WLD-30).** Mining trails and army routes wear into the grass over the match. The ending map tells the story of the game.
18. **Battlefield bloom (WLD-31).** Where stains fade, flowers come up.
19. **Flowers keep hours, flags agree (WLD-15, 29).** Flowers close at night, and every flag on the map points downwind and turns together.
20. **The ground is the sky (pillar 1).** The whole domain is designed for a camera that never sees the horizon. Every sky event lands on the ground, where players actually look.

---

## 8. Anti-patterns (rejected in review)

**Honesty and gameplay**
1. **The world as a radar.** Critters fleeing, birds taking off, footpaths forming, trees vanishing, grass clearing, lantern pools appearing or sounds playing because of something the local player cannot see. Every reaction goes through `visible_at()`.
2. **Weather that changes play.** No sight, speed or accuracy changes from rain or mist. Weather is mood only. If design ever wants gameplay weather, it belongs in the sim and in the gameplay docs.
3. **Atmosphere writing sim state or using `World.rng`.** The weather schedule and critter placement have their own seeded RNG. Critters are visual only.

**Readability**
4. **Darkness as difficulty.** Pitch-black nights, heavy vignettes, "realistic" moonlight. Night is a blue re-grade with lit pools; units keep ≥ 60% of their noon luminance.
5. **Weather that hides the game.** Rain sheets, fog walls, full-screen haze, snow that whites out team colours. Mist stays below 1 m; rain is ≤ 0.16 α.
6. **Lens fakery.** Raindrops or dirt on the "lens", chromatic aberration, film grain, lens flares, or tilt-shift depth of field for the "diorama" look. The camera is not a physical lens, and tilt-shift blurs the screen edges where players scout.
7. **Bloom on the environment.** Glowing grass, water or mist; god rays everywhere. Only flames, sparks, fireflies and capped water glints bloom.
8. **Critters that read as units.** Team colours, unit-sized animals, hover rings or selection cursors on wildlife.
9. **Clutter in lanes.** Grass on roads or footprints, tall tufts that hide feet, flower confetti across the whole map. Ground cover follows the terrain ladder and leaves lanes clean.

**Feel**
10. **The screensaver forest.** Every tree swaying in phase, uniform sine wind, or per-object random wobble with no spatial coherence. Coherence comes from one world-space wind field.
11. **Day/night as a dimmer switch.** A single global lerp of light energy. Ours moves the sun, stretches shadows, warms then cools the grade, and sends a tide across the map.
12. **Shadows that flip or face the camera.** No visible jump at the day/night swap, and no shadows falling down-screen over units.
13. **Ceremony every dusk.** Stingers over 3 s, screen flashes, or banners each nightfall. The tide plus a 2.4 s horn is the ceiling.
14. **Wallpaper ambience.** Loops shorter than 45 s, audible seams, the same bird call twice in a row, hard-panned sweeteners, ambience that ignores where the camera is.
15. **Generic AI-slop atmosphere.** Stock rain sheets, uniform blue night filters, random butterflies everywhere, glitter motes, and one easing curve for everything. Every row here ties its motion to a physical idea: wind load, lapping period, breath, startle.

**Engine**
16. **Shader `TIME`.** It ignores pause and wraps every hour. Use `fx_time` and `hour`.
17. **A node per thing.** One `OmniLight3D` per torch, one `GPUParticles3D` per chimney, one node per critter or blade of grass. Use the lantern map, StreamFx, MultiMesh and wrap volumes.
18. **Per-frame CPU loops over textures in GDScript.** Fog, wear and lantern updates are event-driven or rate-limited, and touch only changed rects.
19. **`Decal`s and depth-texture tricks** that break Compatibility. Use terrain-conforming meshes and the heightmap fade.

**IP**
20. **WC3 signatures.** No wolf howl at dusk, no rooster at dawn, no WC3 ambience loops, tileset textures, weather-effect sprites or critter designs, and no exploding-sheep gag. Generic conventions are fine: blue nights, sleeping-creep z's, critters, shoreline foam.

---

## 9. Budgets, presets and verification

**Budget** (300 units, about 150 on screen, night, drizzle, mid-range GPU at 60 fps)

| Resource | Budget |
|---|---|
| GDScript CPU for the domain (Atmos, Life, Lanterns, wear poll, ambience, minimap feed) | ≤ 0.6 ms average, ≤ 1.0 ms peak (excluding load) |
| Draw calls added | ≤ 18: grass 4–9, air 1, rain 1, mist 2, critters ≤ 5 (one per species), birds 2, shafts 1, skirt 1 |
| Grass on screen | ≤ 6k tufts / about 70k vertices (High) |
| Transparent overdraw | mist ≤ 2 layers, over lowlands only; rain ≤ 900 thin quads; shafts ≤ 6 |
| Texture uploads | fog: unchanged rate, double-buffered; lantern 147 KB per change; wear 36 KB at 1 Hz; minimap ≤ 147 KB at 1 Hz |
| Lights | 4 hearth `OmniLight3D` (Forward+) inside the shared 12-light LightBudget |
| Audio | ≤ 6 bed streams, ≤ 6 positional loops, about 1 one-shot every 4 s |
| Load | ≤ 150 ms for derived maps; grass chunks built lazily |

**Quality presets**

| Item | Low (Compatibility, container) | Medium | High | Juice level 0 (competitive) |
|---|---|---|---|---|
| Grass density / tramplers | 0.7 per m² / 8 | 1.4 / 16 | 2.2 / 24 | 1.4 / 8 |
| Air motes / fireflies | 128 / 96 | 256 / 160 | 384 / 256 | off / off |
| Rain streaks (drizzle / rain) | 220 / 400 | 350 / 650 | 450 / 900 | off (wetness and rings stay) |
| Mist | lower plane only | both | both | α ×0.5 |
| Hearth `OmniLight3D` | 0 | 2 | 4 | 4 |
| Critters simulated / flocks | 12 / 2 | 24 / 4 | 40 / 6 | 24 / 2, no poke gag |
| Light shafts | 0 | 3 | 6 | 0 |
| Shock rings | grass only | full | full | off |
| Nightfall band | on | on | on | off (staggered ignition) |
| Cloud shadow strength | ×1 | ×1 | ×1 | ×0.6 |
| Desire paths, sleep glyphs, fog smoothing, tree memory | on | on | on | on (they are information) |

**Verification** (add with the implementation; no test may be skipped)

1. **`tests/unit/test_atmos_determinism.gd`**
   - Run `battle_setup` plus 30 s of mining, with Atmos on at High, a forced Drizzle → Mist schedule, critters on and injected pokes.
   - Run the same scenario with `World.visuals = false`.
   - The per-second (id, pos, hp) hashes must be identical, and so must `world.rng.state` at the end.
2. **`tests/unit/test_time_of_day.gd`:** evaluate the director every 0.001 h over 24 h.
   - No output jumps more than 2% per step, except the light direction while shadow α < 0.02.
   - The shadow direction stays within 55° of screen-up whenever shadow α > 0.05.
   - The director's day/night agrees with `DayNight.is_day()`.
3. **`tests/unit/test_atmos_framerate.gd`:** drive Atmos `_process` with dt sequences at 30, 60, 144 and 240 Hz and with jittered dt, up to the same `fx_time`.
   - Damped wind direction, ambience gains and carried-light intensities must agree within 1e-4.
   - Critter segment poses must be identical.
4. **`tests/unit/test_world_fog_honesty.gd`:** an enemy army walks through a meadow with rabbits, a bird perch and a sleeping camp, all inside the local player's fog. It also chops a tree and builds a farm. Expected:
   - 0 critter state changes, 0 take-offs, 0 glyphs and 0 shocks;
   - 0 changed wear texels;
   - the felled tree is still drawn;
   - no footprint clearing and no lantern change until the player sees the area.
5. **`tests/playtest/atmos_tour.gd`** (lavapipe and opengl3): screenshots at 06:15, 08:00, 12:00, 17:10, 18:02 (band mid-screen), 21:00 and 00:30, and for Clear, Overcast, Drizzle and Mist.
   - A units-only luminance pass (camera cull mask = units layer, black environment) at 12:00 and 00:30 automatically asserts a ratio ≥ 0.6.
   - Team-colour chroma on the 12 colours is ≥ 0.7 of noon, and their hue shift under a max lantern pool is ≤ 8°.
6. **`tests/playtest/bench_atmos.gd`** (real GPU): 300 units at 00:30 in drizzle, 40 light sources, 30 critters, 3 flocks and 2 shocks/s.
   - Domain CPU stays within budget, frame time stays at 60 fps, and draw calls rise by ≤ 18.
   - A 2-hour soak checks `fx_time` precision (sway and fireflies show no stepping).

**Files touched (checklist)**
- **New in `src/world/`:** `atmos.gd`, `weather.gd`, `lanterns.gd`, `world_maps.gd`, `grass.gd`, `life.gd`, `flocks.gd`, `air_fx.gd`, `mist_fx.gd`, `weather_fx.gd`, `wear.gd`, `camp_fx.gd`, `ambience.gd`.
- **New shaders in `src/world/shaders/`:** `world_common.gdshaderinc`, `foliage.gdshaderinc`, `cloth.gdshaderinc`, `grass.gdshader`, `air.gdshader`, `rain.gdshader`, `mist.gdshader`, `bird.gdshader`, `critter.gdshader`, `prop.gdshader`.
- **New elsewhere:**
  - `src/fx/light_budget.gd` and `src/fx/world_memory.gd`;
  - `src/ui/minimap_overlay.gdshader`;
  - `data/biomes.json` and `data/time_of_day/greenvale.tres`.
- **Changed:**
  - `day_night.gd` (becomes the director);
  - `terrain.gdshader`, `tree.gdshader`, `water.gdshader`;
  - `terrain_builder.gd` (skirt mesh, binds);
  - `doodads.gd` (tree memory, binds);
  - `fog.gd` (double buffer);
  - `world.gd` (Atmos and Life nodes);
  - `minimap.gd`, `selection.gd` (poke);
  - `unit.gdshader` (include);
  - `map_data.gd` (props, fords, camp difficulty, `sun_axis`);
  - `creeps.gd` (sleep hooks);
  - `events.gd`, `settings.gd`, `project.godot` (`[shader_globals]`);
  - `docs/architecture.md` §5, §7 and §8, in the same commit as the hooks.

---

## 10. Assets this doc needs (all original; procedural fallbacks keep "runs without art")

**Textures:**
- painted cloud mask, 256², tileable;
- brush-stroke edge noise, 256²;
- paper grain, 128²;
- grass and flower tuft atlas, 1024² (4 + 4 variants);
- sleep glyph and startle strokes (the FxSprites spare atlas slot);
- 2 water stroke normal maps, 256²;
- foam strokes, 256²;
- light-shaft gradient, 64 × 256;
- rain streak, 16 × 64.

Until these exist, procedural noise stands in: `FastNoiseLite` seamless images.

**Audio** (Seed Audio or CC0, per audio doc §4–5):
- beds: 6 layers × day and night (12 loops, 60–120 s), plus 3 rain beds;
- stingers: dusk horn and dawn chorus;
- one-shots, about 30: lark ×4, woodpecker ×2, owl ×3, frog ×4, sheep ×4, fish plip ×2, gust whoosh ×4, ignition fwump ×3, bird flutter ×3, splash and plop ×3;
- loops: shore lap, crackle, stream, leaf rustle, snore, wading slosh.

No WC3 audio, no wolf howl and no rooster.

---

## 11. Open questions

1. **Shallow fords** (`MapData.water` = 2). They need gameplay and pathing sign-off and a test-map edit. WLD-20 stays dark until then.
2. **Cloud shadow route.** Can the shared `light()` read a fragment-written varying in 4.7.2 at acceptable cost on llvmpipe, or do we use the albedo fallback? This is a 1-day spike.
3. **Compatibility `Environment` adjustments** (saturation, contrast): supported or not? The in-material `atm_grade` fallback is specified either way.
4. **Weather in competitive play.** The proposal is that juice level 0 keeps wind, clouds and wetness but drops streaks and mist. Confirm with experienced players.
5. **Killable critters.** WC3's critters were real units. Ours are visual only for the slice. Revisit after the slice if map makers want critters as sim entities.
6. **Day length.** This doc assumes 20 s per game hour (the 480 s cycle). The research notes an unreconciled "40 s" figure. If design changes it, the keys are hour-based and scale automatically, but the 6 s tide and the 2.67 s stinger lead are defined in game hours and should be re-checked by ear.
7. **`sun_axis` per map.** Should map makers set east, or is it fixed screen-left? The default is screen-left. Rotating it would also rotate the shadow arc, so the up-screen rule must be kept.
