# Juice Spec: Economy & Buildings

*Domain doc of the Vibecraft juice bible. Scope: the gold loop, the lumber loop, workers, HUD resource feedback, building placement, construction, production and research, building damage/destruction/repair, supply and upkeep, mine depletion. Inputs: `docs/research/visual-art-direction.md`, `audio-direction.md`, `video-references.md` (moments M6, M7, M8, M11), `godot-rts-tech.md`, `docs/architecture.md`. Sibling docs in `docs/design/juice/` own combat, heroes and spell VFX, world and day/night, and UI, camera and audio systems. Where this doc touches their systems it names the hook and leaves the system to them.*

Conventions:
- Durations are in ms. Easing names are Godot's (`TRANS_BACK/EASE_OUT` is written BACK/OUT).
- Colours are sRGB hex. "HDR x" means the emission multiplier, and only values above 1.0 bloom.
- "Own" means the local player, or the observed player in observer mode.
- Faction content is not locked yet, so construction styles are given per **archetype**:
  - **Stalwart**: human-like. The visual doc's "Hearth Wardens".
  - **Warband**: orc-like.
  - **Gravebound**: undead-like.
  - **Grove**: elf-like. The "Thornborn" may end up as Warband or Grove.

---

## 1. Feel goals

A base should feel like a **busy workshop you can read at a glance and by ear**:
- Every worker trip ends in a small, crisp "ka-ching" that you hear more than see.
- Every building is a short ceremony: it is stamped, staked, raised and flagged.
- Damage writes itself onto the walls.
- The economy has a **rhythm** (chops, hammer taps, deposit chimes). An experienced player can tell how healthy the base is without looking at it.

Most of this layer is **information in costume**. Each flourish also answers a question:
- Is that worker carrying anything?
- Is this mine saturated?
- How far along is that barracks?
- Is my blacksmith idle?
- How much is upkeep costing me?

The art is WC3-chunky and hand-painted. Coins are fat discs, chips tumble, dust is painted cotton and never photographic, and fire is stylised flame tongues. Only VFX bloom.

**Five rules for this domain:**
1. **Ceremony scales with rarity.**
   - Deposits happen about every second, so they get about 300 ms of micro-juice.
   - A building completes about once a minute, so it gets a 1 s ceremony.
   - A hall falls about once a game, so it gets a 3 s set piece.
   - Repeated events get shorter, never longer.
2. **Never wait for the juice.** The sim never pauses, delays or re-times anything for an animation. Flourishes run alongside gameplay and can be cut off at any frame.
3. **Readable in a fight.** Economy effects shrink first when combat is busy (§2.6). Nothing covers units, team colour, selection rings or health bars.
4. **Every material has its own sound and motion.** Coins glint and jingle, wood tumbles and knocks, stone thuds and crumbles. No generic sparkle.
5. **Fog-honest.** An effect plays only if the local player could see or hear its source (§2.1).

---

## 2. Shared foundations (read before implementing any row)

### 2.1 Hard rules

**Visual-only and refresh-rate independent**
- All juice lives in `_process(delta)` or in shaders driven by the global `fx_time`.
- Nothing in juice writes `Unit` sim fields, `PlayerState`, `Pathing` or `World.rng`, or emits gameplay events.
- Motion is a **closed-form function of the effect's age**, built from the `JuiceCurves` functions in §2.4. So 30, 60, 144 and 240 Hz show identical poses at the same wall time.
- Springs are the only exception. They integrate in fixed 1/120 s substeps taken from accumulated delta (at most 8 per frame).

**Randomness**
- Use the visual RNG on `Vfx` (`_jitter`), or hash noise seeded from (entity id, tick, salt).
- Never use `World.rng`. Deterministic hashes keep the look stable: a burning barracks always burns from the same windows.

**Clocks**
- `Vfx._process` sets `RenderingServer.global_shader_parameter_set("fx_time", t)`. `t` is real time accumulated while the tree is not paused. Register it once with `global_shader_parameter_add("fx_time", GLOBAL_VAR_TYPE_FLOAT, 0.0)`.
- Fx nodes use `PROCESS_MODE_PAUSABLE`. HUD tweens may run while paused.

**Sim reads**
- Read `display_pos()` and `display_build_progress()`, which are prev→cur values lerped by `Engine.get_physics_interpolation_fraction()`.
- Never read raw tick-quantised values for motion.

**Fog gate**
- World-space effects and 3D sounds for an entity play only when its cell is visible to the local player (`Fog` grid value 2).
- The only exceptions are effects on the player's own entities that the HUD reports anyway: advisor lines, minimap pings and the HUD itself.
- An enemy chopping in the fog makes no chips and no sound.

**Physics interpolation**
- Fx `MultiMeshInstance3D`s and pooled props set `physics_interpolation_mode = OFF`.
- Rig-local offsets (squash, spawn offset, jitter) go on `UnitView.body` or `rig`, never on the `Unit` node.

**Renderer**
- No `Decal` nodes: they are not supported on Compatibility. Ground effects are terrain-conforming meshes (§2.3).
- `OmniLight3D` is used only from the 6-light pool, only on Forward+ and only at night.
- At startup, check `RenderingServer.get_current_rendering_method()`. Compatibility drops the light pool and the heat effects.

### 2.2 Sim → view contract (what economy and production must expose)

`economy.gd` and `production.gd` do not exist yet. Juice needs the following hooks. They are cheap and deterministic, and several are useful to the HUD and AI too. **Changes to `Events` and `Unit` must also update `docs/architecture.md` §5 in the same commit**, per the contract.

| Hook | Kind | Emitted / maintained by | Notes |
|---|---|---|---|
| `resource_delivered(worker, dropoff, kind: String, gross: int, net: int)` | signal | economy | `kind` = `gold`/`lumber`. `net` is after upkeep. Non-carrying archetypes pass the mine as `dropoff`. |
| `mine_entered(worker, mine)` / `mine_exited(worker, mine)` | signal | economy | Emitted on the tick the worker is hidden or shown. |
| `resource_stage_changed(node, stage: int)` | signal | economy | Mine stages: 0 rich, 1 low (≤ 1,500), 2 critical (≤ 300), 3 depleted. |
| `tree_harvested(tree_index: int, worker, amount: int, left: int)` | signal | economy / `Doodads.harvest` | One per chop hit. |
| `tree_toppled(tree_index: int, pos: Vector3, away: Vector3)` | signal | `Doodads.remove_tree` | Emitted next to the existing `tree_felled(pos)`. `away` = unit vector from the felling worker to the tree. |
| `construction_started(building, builder)`, `construction_cancelled(building)` | signals | production | The existing `building_completed(u)` stays. |
| `research_finished(building, id: String)` | signal | production | Emitted alongside the existing `research_completed(player_id, id)`. |
| `upkeep_changed(player_id, old_tier, new_tier)` | signal | economy | `PlayerState.upkeep_tier` already exists. |
| `notification(pid, kind, text)` kinds | existing signal | economy / production / input | `no_gold`, `no_lumber`, `no_food`, `cant_build`, `cant_place`, `mine_low`, `mine_collapsed`, `research_done`, `building_done`. |
| `Unit.build_progress`, `prev_build_progress`, `display_build_progress()` | fields | production | 0..1. |
| `Unit.resource_left`, `resource_max` | fields | economy | Mines (from def `gold`); trees keep `Doodads.lumber`. |
| `Unit.miners_assigned` | field | economy | Per mine, counting only workers of the mine's current user. |
| `Unit.work_progress()` | reader | unit / economy | 0..1 inside the current chop, mine or repair cycle. The strike lands at the wrap. Same pattern as `swing_progress()`. |
| `Unit.is_producing()`, `queue_progress()`, `stalled_for_food` | readers | production | |
| `Unit.rally_pos`, `rally_id` | fields | already in §4 | Juice detects changes by comparing. |
| `PlayerState.food_pending` | field | production | Sum of `food_provided` of own structures under construction. |
| def `fx` block (visual hints) | data | `data/units.json` | `{"door":[x,y,z], "chimney":[[x,y,z]], "fire_points":[[...]], "flag":[x,y,z], "material":"timber", "construction":"scaffold", "windows":true, "select_sfx":"bell"}`. Missing hints are derived from the footprint: door at the front (-Z) centre, chimney at a roof hash point. |

### 2.3 FX building blocks (new files under `src/fx/`)

**`ballistic_fx.gd` + `ballistic.gdshader` (BallisticFx): closed-form burst bits** (coins, chips, leaves, sparks, debris chunks, motes)
- One `MultiMesh` ring buffer per kind: COIN 192, CHIP 256, LEAF 128, SPARK 192, CHUNK 96, MOTE 256.
  - `custom_aabb` covers the whole map.
  - `use_colors` and `use_custom_data` are set before `instance_count`.
- Spawning writes one instance (transform, colour, custom data); the oldest slot is overwritten.
- **There is no per-frame CPU work.** The vertex shader (`skip_vertex_transform`) computes position from the spawn data and `fx_time`:
  - the ballistic arc;
  - a closed-form first ground contact (`t_land = (vy + sqrt(vy² + 2g(y0 − ground_y))) / g`);
  - one damped bounce, then rest;
  - collapse to size 0 when `age > life`.
- Packing:
  - transform origin = spawn position;
  - basis.x = v0;
  - basis.y = (size, life, ground_y);
  - basis.z = (spin, gravity, **spawn_time**).
  - Spawn time stays in the full-precision transform, because custom data may be packed at reduced precision on some backends (verify on Compatibility).
  - `INSTANCE_CUSTOM` = (restitution, kind, seed, emission).
- LEAF uses flutter (constant fall speed plus sinusoidal sway). SPARK stretches along its velocity in view space. CHUNK uses mesh variants.
- Works identically on Forward+ and Compatibility. Cost: about 6 draw calls total, about 3 µs CPU per spawn.

```glsl
// ballistic.gdshader (core; billboard and spin omitted)
shader_type spatial;
render_mode skip_vertex_transform, unshaded, shadows_disabled, cull_disabled;
global uniform float fx_time;
void vertex() {
	vec3 p0 = MODEL_MATRIX[3].xyz;  vec3 v0 = MODEL_MATRIX[0].xyz;
	float size = MODEL_MATRIX[1].x, life = MODEL_MATRIX[1].y, ground = MODEL_MATRIX[1].z;
	float g = MODEL_MATRIX[2].y, t0 = MODEL_MATRIX[2].z, rest = INSTANCE_CUSTOM.x;
	float age = fx_time - t0;
	vec3 p = p0 + v0 * age - vec3(0.0, 0.5 * g * age * age, 0.0);
	float tl = (v0.y + sqrt(max(v0.y * v0.y + 2.0 * g * (p0.y - ground), 0.0))) / g;
	if (age > tl) {                                    // one bounce, then rest
		vec3 pl = p0 + v0 * tl - vec3(0.0, 0.5 * g * tl * tl, 0.0);
		vec3 v1 = vec3(v0.x * 0.5, (g * tl - v0.y) * rest, v0.z * 0.5);
		float a = min(age - tl, 2.0 * v1.y / g);
		p = pl + v1 * a - vec3(0.0, 0.5 * g * a * a, 0.0);
	}
	float alive = step(0.0, age) * step(age, life);
	VERTEX = (VIEW_MATRIX * vec4(p + VERTEX * size * alive, 1.0)).xyz;
	NORMAL = normalize((VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
}
```

**`stream_fx.gd` + `stream.gdshader` (StreamFx): looped, closed-form soft sprites** (chimney smoke, fire, embers, steam, rune motes) **and one-shot puffs** (dust rings, plumes)
- A stream is K instances with phases `i/K`:
  - `age = mod(fx_time − t0 + phase·life, life)`;
  - the loop index `floor(...)` seeds the jitter;
  - `t_stop` in the transform lets in-flight puffs finish, so stopping needs no CPU work.
- Puffs have drag-limited closed-form rise, size growth and an alpha curve.
- Sprites are painted, hand-made textures with 3 value bands. Smoke and dust use alpha blend; fire, embers and sparks use additive blend.
- About 768 instances in total, 3 materials.
- GPUParticles3D (with `CPUParticles3D.convert_from_particles()` on Compatibility) is allowed only for later P2 polish (trails, sub-emitters). The P0/P1 path is this shader so both renderers look the same.

**`ground_fx.gd` + `ground_fx.gdshader` (GroundFx): terrain-conforming ground layers**
- Footprint grids, stamp and shockwave rings, packed earth, rubble patches, sawdust rings, dashed chalk and route strips.
- Mesh: an `ArrayMesh` cached per size, with vertex heights from `MapData.height_at` + 0.03 m.
  - A 24×24-cell grid has at most 625 vertices and rebuilds in under 0.2 ms.
  - Flat-ground rings around buildings use a flat quad at base height + 0.05 m.
- Material: one shader with a `mode` uniform; age-driven modes use `fx_time`.
- Render settings: `render_priority` below units, `depth_draw_never`, `shadows_disabled`.

**Other new files**

| File | Contents |
|---|---|
| `economy_fx.gd` | Listens to the economy signals. Runs mine, deposit and tree effects; owns the 16-slot economy popup pool (Label3D + Sprite3D icon). |
| `building_fx.gd` | Construction, production, damage, destruction and repair state machines; light pool; rally/stake markers. |
| `juice_curves.gd` (`class_name JuiceCurves`) | Pure static functions of age in ms (§2.4). Unit-tested. |
| `juice_palette.gd` (`class_name JuicePalette`) | Colour tokens (§2.5). |
| `fx_budget.gd` | Caps, LOD, juice level, combat intensity, fog gate (§2.6). |
| `src/input/build_placement.gd` | Placement ghost (BLD-01..04). Owned by `CommandInput`. |
| `src/ui/resource_counter.gd` | Odometer counter (ECO-13). |
| `src/ui/upkeep_ruler.gd` | Upkeep ruler (ECO-15). |
| `src/ui/toast.gd` | Completion toasts (BLD-14). |

**`Audio` additions** (in `src/autoload/audio.gd`, following the audio doc §3.5 and §6.6):
- `play_3d(id, pos, opts := {pitch, volume_db, priority, bus, spacing_ms})`
- `loop_3d(key, id, pos, volume_db)` and `stop_loop(key, fade_ms)`
- Buses `World`, `UI`, `Acks` and `Alerts` as in that doc. Per-id caps and spacing are enforced there, not in fx code.

**`UnitView` additions**
- A structure branch `_animate_structure(delta)` for squash, settle, jitter, damage uniforms and collapse. Today `_process` returns early for buildings.
- `spawn_offset` (BLD-12), a `Props` node (ECO-03) and `flash(strength, color)`.
- Off-screen views skip procedural animation (camera frustum test at 4 Hz).

### 2.4 Motion vocabulary (`JuiceCurves`, all f(age))

| Name | Definition | Used by |
|---|---|---|
| POP_IN | scale 0.55→1.12 in 90 ms (BACK/OUT), →1.0 in 110 ms (SINE/IN_OUT) | popups, sack appear, stakes |
| RECEIVE | Y 1→0.985 in 70 ms (QUAD/OUT), →1.0 in 160 ms (BACK/OUT); XZ = 1/√Y; pivot at base | drop-offs; mine gulp uses depth 0.965 |
| SETTLE | Y 1→1.05 (90 ms QUAD/OUT) → 0.975 (120 ms SINE/IN_OUT) → 1.0 (170 ms BACK/OUT); XZ = 1/√Y; pivot at base | completion |
| PUNCH | `offset_transform_scale` 1→1.14 (70 ms QUAD/OUT) → 1.0 (180 ms BACK/OUT); repeats within 250 ms use 1.06 | HUD counters |
| SHAKE | x = A·sin(2π·t/P)·(1 − t/T). HUD: A 6 px, P 80 ms, T 280 ms. World: A 0.12 m | denial |
| RISE_FADE | POP_IN; y += H·(1 − (1 − t/D)³); α = 1 until 0.6·D, then 1 − ((t − 0.6D)/0.4D)². Default H 1.1 m, D 1,000 ms | popups |
| FLARE | energy idle→peak linearly in 60 ms, → idle over 400 ms (EXPO/OUT) | door glows |
| FLUTTER_SPIKE | flag flutter amplitude × k, decaying to × 1 with e^(−3t/s) | flags, pennants |

Rules:
- On 3D, the only Tweens allowed are short scene-level sequences that are not per particle.
- Prefer evaluating these functions on accumulated age.
- HUD `Control`s may use `create_tween()`. Set `offset_transform_visual_only = true` so a punch never reflows the layout.
- BACK overshoot is Godot's default (1.70158) unless a row says otherwise.

### 2.5 Palette tokens (`JuicePalette`)

| Token | Hex | Token | Hex |
|---|---|---|---|
| GOLD_TEXT / outline | #FFD23F / #4A2E00 | COIN body / rim | #F2B632 / #FFE58A (glint HDR 1.8) |
| LUMBER_TEXT / outline | #9BE36A / #1E3A12 | WOOD_CHIP bark / inner | #6B4423 / #E9CF9B |
| FOOD_TEXT / outline | #FFF1CF / #4A3420 | TAX_TEXT / outline | #A9B1BA / #22262B |
| VALID / INVALID / UNAFFORDABLE | #46E07A / #FF4B3E / #9AA0A6 | BLUEPRINT (ghost, ink) | #F3E6C4 |
| DUST (biome-tinted through the LUT) | #CDB892 (Frostmarch #E6EEF5) | SMOKE light / dark | #6E6862 / #3E3935 (burning #2E2A27) |
| FIRE core / mid / edge | #FFE08A HDR 2.5 / #FF8A2A HDR 1.8 / #C2341A | EMBER | #FFB04A HDR 3.0 |
| SPARK (hammer) | #FFD27A HDR 2.2 | REPAIR mote / STEAM | #F6FFB8 HDR 1.4 / #E8F0F5 |
| DOOR_GLOW / WINDOW | #FFB347 / #FFB86B HDR 1.4 | UPKEEP none / low / high | #7FD86A / #FFC145 / #FF5A48 |
| MINE_LOW ping | #FFB13B | DENIAL flash | #FF5A4A |

**Team colour is reserved for ownership:** flags, pennants, stakes, rally flags and building trim. Never use it for generic particles.

### 2.6 Density governor and readability (`FxBudget`)

**Juice levels** (`Settings.juice_level`):

| Level | What it includes |
|---|---|
| 0 Competitive | Only informative effects: ghost and grid, popups, mine stages, damage states, upkeep/supply UI, denial, completion ping. No squash, gags, chimes, leaves or lights. |
| 1 Default | Everything in this doc except the cinematic extras. |
| 2 Cinematic | Fire lights by day too, ×1.5 debris and plume counts, Lamplighter cascade. |

Per-feature toggles: `eco_popups`, `saturation_lanterns`, `ledger_chime`, `building_gags`.

**Combat intensity** = number of `unit_damaged` events with an on-screen victim in the last 1,000 ms. At **25 or more → battle mode**:
- economy chips and coins ×0.5;
- no tax-bite sound;
- popups only for own drop-offs;
- building hit chips ×0.5;
- route-line α ×0.6;
- idle bubbles hidden.

Battle mode never reduces placement feedback, damage-state fire (it is state information) or construction progress, and destruction plumes keep at least 50% of their count.

**Caps:**

| Item | Cap |
|---|---|
| Economy popups | 6 on screen (oldest killed with a 150 ms fade) |
| Ballistic kinds | ring buffers as in §2.3 |
| Smoke columns | 24 |
| Fires | 12 |
| Fire lights | 6 |
| Construction sound beds | 3 |
| Hammer voices | 6 |
| Chop voices | 4 |
| Mine interior loops | 2 |
| Fire loops | 3 |

**Distance LOD:** spawn world juice only if the source is inside the camera frustum (`Camera3D.is_position_in_frustum`, with a 2 m margin) and within 40 m of the focus point. Off-screen events update HUD state only.

**Readability rules:**
1. Draw order: ground fx < units < smoke/dust < sparks/coins < popups < health bars and selection rings (`no_depth_test`, highest `render_priority`).
2. Smoke and dust stay at α ≤ 0.5 and fade above 4 m over the source.
3. Plumes use **donut emission**: they spawn on a ring around the footprint, and the centre gets at most 6 puffs at α 0.25. Units standing in ruins stay visible.
4. Fire and smoke emitters stay inside the footprint × 0.8.
5. Gold and lumber differ by **glyph and motion**, not hue alone. Valid and invalid differ by **hatching**. Upkeep tiers differ by a **notched-coin icon**. All three are safe for red-green colour blindness.
6. Popups are unshaded and ignore night grading.

---

## 3. Feature table

Columns: ID · Feature · Trigger · Exact spec · Godot implementation · Perf · Priority (P0 = vertical-slice must-have).

### 3.1 Gold loop

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-01 | **Mine gulp & spit** | `mine_entered` / `mine_exited`; mine on screen | **Gulp (enter):** mine body RECEIVE at depth 0.965 (80 / 110 / 150 ms) · door-glow FLARE idle → 2.4. Idle glow is 0.7 while occupied and 0.15 when empty (#FFB347). · 4 lintel dust motes (fall 0.4 m, 500 ms) · 3 star glints at the door (HDR 1.8, 160 ms).<br>**Spit (exit):** inverse squash 1→1.02→0.99→1.0 (same timings) · door FLARE peak 1.8 · the worker POPs 0.85→1.08→1.0 over 200 ms · dust-off: body roll ±6°, 2 cycles in 260 ms, plus 6 shoulder motes · the gold sack appears with POP_IN.<br>**Rate limit:** 1 squash per mine per 250 ms; extra events only flare the door.<br>**Sound:** enter = short timber creak (World −14 dB, prio 30); exit = door thump + sack jingle (−12 dB). Interior: while at least 1 worker is inside and the mine is within 30 m of the listener, a muffled pick loop (a clink every 380–620 ms, `attenuation_filter_cutoff_hz` 1,800, −16 dB). | `economy_fx.gd`; mine `UnitView` structure branch gets `squash(curve)`; door glow = child quad with `glow.gdshader` (instance uniform `energy`) at `fx.door`; motes and glints via BallisticFx; interior via `Audio.loop_3d` | ~10 µs per event; +1 small draw per mine; ≤ 2 loops | P0 (interior loop P1) |
| ECO-02 | **Saturation lanterns** | 4 Hz poll of `mine.miners_assigned` vs def `max_workers` (local player's usage) | Row of 5 lantern pips on the mine lintel: Ø 0.16 m, 0.26 m apart, tilted 30° toward the camera.<br>Lit = #FFC94A HDR 1.6; a pip lights with a 70 ms POP. Unlit = #3A2E22.<br>**Oversaturated** (assigned > max): all pips flicker #FF7A3A at 4 Hz (50% duty) and a small "+N" (24 px) sits beside them.<br>α 1.0 when a worker, hall or this mine is selected or hovered; α 0.55 otherwise. Fade to 0 during collapse. Own usage only; never shown for enemy usage. | one quad per mine, `pips.gdshader` (instance uniforms `lit`, `cap`, `over`); `economy_fx` poll | 1 draw per mine | P1 |
| ECO-03 | **Worker tool & cargo props, laden walk** | order type change; `carry_gold` / `carry_lumber` > 0 | **Tool swap:** pick for the mine, axe for trees, hammer or the archetype tool for build/repair. Old tool scales to 0 in 80 ms; new tool 0→1.15→1.0 (80 + 60 ms, BACK/OUT) with a 180° flip about the hand axis.<br>**Gold sack:** squat 0.28 m sack (#B98B4E cloth, #F2B632 coin peeking) on the back at (0, 0.62·h, +0.18 m).<br>**Logs:** N = ceil(carry_lumber / 10), clamped to 1–3 logs (Ø 0.12 m × 0.7 m, bark #6B4423, cut ends #E9CF9B) on the shoulder at 25°. **The bundle grows with lumber upgrades.**<br>**Secondary motion:** cargo hangs on a spring driven by body acceleration (sack k 90 s⁻², damping 12 s⁻¹; logs k 60), clamped to 0.08 m / 6°, in fixed 1/120 s substeps.<br>**Laden walk:** bob ×1.2, stride frequency ×0.95, extra forward lean 4°. The sim speed does not change.<br>**Glint:** every 1.2–2.2 s, a star on the sack for 140 ms (HDR 1.8), only within 30 m of the camera focus. | `unit_view.gd` `Props` node under `body` (or `BoneAttachment3D` `hand_r` / `back` on rigged GLBs); props from `assets/models/props/`, with ProcMesh fallbacks; per-view RNG seeded from the unit id | +1–2 draws per carrier (shared meshes; move cargo to a MultiMesh layer if more than 60 carriers are on screen); ~3 µs per worker | P0 (tool swap P1) |
| ECO-04 | **Deposit moment (gold & lumber) + ledger chime** | `resource_delivered`; drop-off on screen; own | **Toss:** the cargo prop detaches and flies a 220 ms parabola (apex +0.6 m, 1 spin) to the drop-off `fx.door`, then vanishes in a pop of 3 coins / 2 chips. The worker leaves on its own sim schedule.<br>**Receiver:** the drop-off plays RECEIVE (≤ 1 per 300 ms per building).<br>**Burst:** gold = 6 COIN (up 2.5–3.5 m/s, lateral 0.6–1.2, g 14, restitution 0.35, life 450–650 ms, one 60 ms glint frame each); lumber = 4 CHIP + 1 LEAF.<br>**Popup:** "+net" Label3D + 0.22 m icon sprite (coin or log) at door + (0, 0.4·height + 0.6 m, 0). Gold: font 44, GOLD_TEXT, outline 10. Lumber: font 40, LUMBER_TEXT, lateral sway 0.08 m at 2.2 Hz. Curve RISE_FADE.<br>**Merge:** same player, kind and drop-off within 350 ms → sum the values with a 120 ms digit roll and re-POP (1→1.1→1).<br>**Sound:** gold = sack jingle (World −10 dB, prio 30, ≤ 2/s per player) + **ledger note**: a soft bell at −16 dB whose pitch walks the major pentatonic (0, 2, 4, 7, 9, 12 semitones) one step per deposit and resets after 2.5 s without deposits. Lumber = log clack (−11 dB) + a woody note one octave lower (−18 dB). On-screen deposits only.<br>**Non-carrying archetypes:** the same popup and burst at the mine crown, with no toss. | `economy_fx.gd`; popup pool in the `vfx.gd` style (closed-form RISE_FADE, pooled Label3D + Sprite3D, `no_depth_test`, `render_priority` 20); BallisticFx; `Audio.play_3d(..., {pitch})` | ~20 µs per deposit; 0 per-frame cost for coins; ≤ 6 popups | P0 (ledger chime P1) |
| ECO-05 | **Tax bite** | `resource_delivered` with net < gross | 150 ms after "+7" pops, a "−3" (font 32, TAX_TEXT, outline 8) peels off its right edge, falls 0.5 m (QUAD/IN, 500 ms) and fades. A grey coin chip (#8C8C8C) drops beside it and crumbles into 3 motes on landing.<br>Sound: dull coin-on-stone tick (World −20 dB), only for the first 3 bites per 10 s.<br>Merged popups carry the merged tax. For 6 s after entering a taxed tier (ECO-15), every deposit shows its bite. Shown at all juice levels (it is information); the sound is off at level 0. | economy popup pool child label; BallisticFx chip | negligible | P1 |
| ECO-06 | **Mine depletion stages & low warning** | `resource_stage_changed`; `resource_left / resource_max` | **Vein:** placeholder nuggets visible = ceil(8·frac^0.7). GLB vein material: `vein_glow` = 0.4 + 0.6·frac, saturation ×(0.4 + 0.6·frac).<br>**Low (≤ 1,500):** shared crack overlay (BLD-15) at 35% · lintel dust trickle (3 motes every 2.5–4 s) · timber creak every 6–10 s (World −18 dB, on screen only).<br>**On entering low, once:** amber minimap ping (#FFB13B, 3 rings over 1,500 ms) · advisor line (Alerts, once per mine) · HUD notification · lanterns blink 2×.<br>**Critical (≤ 300):** the lintel sags 3° (500 ms, SINE/IN_OUT); each worker exit drops 2 pebbles. | `economy_fx`; mine view uniforms; `Minimap.ping(pos, color, rings)` hook (UI doc) | negligible | P0 for warning + ping; P1 for vein visuals |
| ECO-07 | **Mine collapse** | stage 3 (depleted) | **0 ms:** timber snap + deep crack; door glow → 0 in 200 ms.<br>**0–600 ms:** lintel beams rotate 18° and drop 0.4 m (QUAD/IN); the mound shudders ±0.06 m at 18 Hz, decaying.<br>**300–1,400 ms:** the mound sinks to 70% height (CUBIC/IN_OUT) with Y-squash 0.7.<br>**300 ms:** donut dust plume, 28 puffs (ring r 2.2–3.2 m, rise 1.5 m/s, size 1.6→3.2 m, life 1.8–2.6 s, α 0.5→0) + 10 CHUNK rocks.<br>Workers inside pop out with a stumble (roll 25° and back, 400 ms, 4 motes).<br>Afterwards the mine is permanently "spent": entrance boarded in an X, grey vein.<br>**Sound:** crack (World −4 dB, prio 70) + 1.8 s rock-slide rumble (−6 dB) + settling pebbles (−14 dB). Advisor line + grey minimap ping. | mine collapse state in the `UnitView` structure branch (local age); StreamFx + BallisticFx | one-off; ~38 sprites for 2.6 s | P1 |

### 3.2 Lumber loop

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-08 | **Chop strike sync, chips & thunk** | swing pose from `work_progress()` (strike at the wrap); chips and sound on `tree_harvested` | **Swing:** wind-up 0→0.55 (QUAD/OUT; body pitched back 10°, tool −70°), strike 0.55→0.62 (CUBIC/IN), recoil 0.62→1.0 (BACK/OUT).<br>**Visual hit-stop:** the worker's rig only holds the strike pose for 50 ms; the sim keeps running.<br>**Chips:** 3–5 CHIP (60% bark / 40% inner wood), 0.05–0.09 m, thrown away from the worker in a 70° cone (2–3 m/s, up 1.5–2.5), g 12, 1 bounce, life 500–700 ms.<br>**Sound:** axe "tok" (World −12 dB, prio 30, ≤ 4 per id, ≥ 80 ms apart; pitch from ECO-10) + leaf rustle on 30% of chops (−20 dB). With more than 6 choppers on screen, only the 4 nearest the screen centre are audible; all of them still throw chips. | `unit_view.gd` (`work` clip or procedural); `economy_fx` handles `tree_harvested`; BallisticFx | ~10 µs per chop; 20–40 chops/s in a big base | P0 |
| ECO-09 | **Tree shudder & leaf drop** | `tree_harvested` | **Vertex shader:** rotation about the base, away from the chopper: θ(t) = 0.05 rad · e^(−9t) · sin(2π·11·t), weighted (h/H)^1.5. t = `fx_time` − `INSTANCE_CUSTOM.r` (hit time).<br>**Leaves:** 2–4 LEAF quads (0.12 m; #5E9E3A / #84B94A × the tree's instance tint) from 60–90% of canopy height. Fall 0.8 m/s with 0.35 m flutter at 1.2 Hz, spin, life 1.6–2.4 s, fade over the last 400 ms. Pines shed 1–2 darker needles (#2E5A2A). | `doodads.gd`: set `mm.use_custom_data = true` before `instance_count`; `INSTANCE_CUSTOM` = (hit_time, away_angle, lean, hollowness); extend `tree.gdshader`; LEAF via BallisticFx | one `set_instance_custom_data` per chop | P0 (leaves P1) |
| ECO-10 | **Tree hollowing & lean telegraph** | `tree_harvested` (`left / lumber_max`) | **Pitch:** chop pitch = per-tree hash base (0.92–1.08) × 2^(s/12), with s = 4·(1 − frac)^1.3. **The tree rings hollower as it empties.** At frac ≤ 0.1, add a creak layer (−10 dB relative).<br>**Lean:** 6° · smoothstep(0.55, 1.0, 1 − frac), away from the latest chopper. It is written per chop; steps of ≤ 0.6° are invisible.<br>**Canopy:** desaturates 10% below frac 0.25. | same as ECO-09; `Audio.play_3d(..., {pitch})` | negligible | P1 |
| ECO-11 | **Tree topple, fade & stump** | `tree_toppled(index, pos, away)` | **0–180 ms hesitation:** tip to 4° (SINE/OUT) + creak.<br>**180–1,080 ms fall:** angle = 4° + 86°·((t − 180)/900)^2.2 about a pivot 0.15 m off the trunk base, toward the fall.<br>**1,080 ms impact:** bounce 90→84→90° (220 ms, BACK/OUT) · 14 LEAF along the canopy line · 10 dust puffs along the trunk (0.5→1.2 m, 700 ms) · crash.<br>**1,080–3,600 ms:** rest.<br>**3,600–4,800 ms:** noise dissolve (edge #E9CF9B) + sink 0.3 m.<br>**Stump**, added at topple start: r 0.22 m, h 0.35 m, ringed top #D9B98A, random yaw, ±4° tilt, permanent. Plus a sawdust ring (GroundFx, α 0.4, fades over 20 s).<br>The tree falls away from the chopper (hashed direction if there is none).<br>**Sound:** creak (World −14 dB) → whoosh (−16) → leafy crash and thud (−8, prio 40). | `doodads.gd` hides the instance (existing zero-scale). `FallingTreePool`: 6 `MeshInstance3D`s that share the tree meshes and `tree.gdshader` with instance uniforms `fall_angle` and `dissolve`, animated in `_process`. Stumps = 1 MultiMesh (cap 4,096, map-wide AABB). | ≤ 6 extra draws while trees fall; stumps 1 draw | P0 (dissolve + sawdust P1) |

### 3.3 Workers

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-12 | **Idle worker fidgets & idle button** | `is_idle()` for ≥ 4 s | **Fidget** picked by hash(id, idle count), repeating every 5–9 s:<br>• lean on tool (8° tilt, 2.5 s);<br>• look around (two ±30° yaw glances over 1.6 s);<br>• stretch-yawn (Y 1→1.08→1 over 1.2 s).<br>**After 20 s:** sits (body −35% height over 400 ms, BACK/OUT) and stays down. On a new order: hop up (POP 0.9→1.06→1 + 4 motes).<br>**"…" thought bubble** after 8 s: 0.4 m, α 0.75, bob 0.05 m at 1 Hz, 250 ms fade-in. Own workers only; at most 8 on screen (nearest the centre).<br>**HUD idle-worker button** (UI doc owns the widget): bounce when the count rises (`offset_transform_scale` 1→1.18→1, 260 ms, BACK/OUT) + soft tok (UI −14 dB, ≤ 1 per 3 s). Slow glow pulse (2 s period) once a worker has idled ≥ 30 s. α 0.35 when the count is 0. | `UnitView` idle sub-state (visual only); shared Sprite3D bubble pool; `Hud.set_idle_workers(n)` | ~2 µs per idle worker | P1 (button bounce P0) |

### 3.4 HUD economy feedback

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| ECO-13 | **Resource odometers** | `resources_changed(local)`; HUD compares target vs shown value | **Rolling digits:** shown → target over clamp(120 + 6·abs(Δ), 150, 450) ms, QUART/OUT. A change mid-roll retargets from the current shown value; no restart flicker.<br>**Gain:** PUNCH + text flash #FFF4C2 (120 ms) + the icon glints for 1 frame.<br>**Spend:** digits roll down + flash #FF9A7A (160 ms) + a 4 px drop (`offset_transform_position.y` 0→4→0 over 200 ms).<br>**Spend ≥ 200:** 2–3 coin or log icons tumble out of the counter (UI-space, 400 ms). | `src/ui/resource_counter.gd` (icon + Label; Tweens; `offset_transform_visual_only`); replaces the plain labels in `hud.gd` | negligible | P0 |
| ECO-14 | **Denial feedback** | `notification` kinds `no_gold`, `no_lumber`, `no_food`, `cant_build`, `cant_place` | **HUD:** the matching counter does SHAKE (HUD) with text DENIAL_FLASH for 280 ms. The pressed command-card button gets the same shake + a red overlay (α 0.45, fading over 300 ms). The cursor shows a red slash badge for 300 ms.<br>**While placing:** the ghost does SHAKE (world, 0.12 m) and flashes INVALID.<br>**Sound:** faction error cue (UI −10 dB) + advisor line (Alerts; 1.5 s cooldown per kind, as in the audio doc). | `hud.gd`, `command_card.gd`, `build_placement.gd`; `JuiceCurves.shake` | negligible | P0 |
| ECO-15 | **Upkeep ruler & tier flip** | `upkeep_changed`; food changes | **Ruler:** 120×4 px bar under the food counter. Fill = food_used / `food_max`. Ticks at the `Defs.upkeep` thresholds (51, 81). Segment colours UPKEEP none / low / high; track #1B1F24. Within 4 food of the next threshold, that tick pulses (α 0.5↔1.0 at 1.5 Hz).<br>**Tier icon:** a coin with 0, 1 or 2 bites taken out (shape-coded).<br>**Tier change:** label card flip (`scale.x` 1→0 in 110 ms SINE/IN, swap text and colour, 0→1 in 130 ms BACK/OUT) + white ruler flash (150 ms).<br>**Sound** (UI −10 dB): worse = two notes falling a minor third; better = rising a major third.<br>Advisor line at most once per 60 s per tier. Opens the 6 s ECO-05 teach window. | `src/ui/upkeep_ruler.gd` (`_draw()`); `hud.gd` | negligible | P0 (ruler P1) |
| ECO-16 | **Supply cap & pending supply** | food_used == food_cap; `PlayerState.food_pending`; `no_food`; a supply building completes | **Capped:** food text amber #FFB347 with a 1 px underline pulsing at 1 Hz.<br>**Pending:** " (+N)" after the cap, in #8E96A0 italic, breathing α 0.6↔1. The tooltip lists ETAs.<br>**Completion:** world popup "+6" with a hearth icon (FOOD_TEXT, RISE_FADE, D 1,200 ms) over the building; the HUD cap rolls up with a warm flash (#FFE7A8).<br>**Stalled production:** a building whose queue waits for food shows a floating food icon with a red slash (0.35 m, own only, 1.2 Hz pulse) above its door until it unblocks. | `hud.gd`; `economy_fx` popup; `building_fx` stalled icon (`stalled_for_food`) | negligible | P0 (pending + stalled icon P1) |

### 3.5 Building placement

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-01 | **Blueprint ghost & glide-snap** | build button → placement mode | **Ghost:** the building mesh drawn with `ghost.gdshader` (unshaded, depth test on, `depth_draw_never`).<br>• Body α 0.28 + fresnel rim (power 2.5) α 0.65.<br>• Horizontal ink lines every 0.25 m, scrolling up at 0.4 m/s, α 0.18.<br>• Colours: valid BLUEPRINT, invalid #FF6B5E, unaffordable #9AA0A6.<br>• Breathing α ×(0.85 + 0.15·sin(2π·1.6t)); 3 Hz when invalid.<br>**Glide:** target = `Grid.snap_to_footprint(cursor ground)`. Shown position p += (target − p)·(1 − e^(−28·delta)), about a 36 ms time constant: it glides, then clicks. Each cell change gives a 60 ms 1.5% Y-tick. Hovers 0.08 m up over a soft shadow quad (α 0.25).<br>**Sound** (≥ 120 ms apart): becoming valid = wooden tock (UI −18 dB); becoming invalid = muffled thud (−20 dB). | `src/input/build_placement.gd`, `src/fx/ghost.gdshader`; placeholders reuse their merged mesh | 1–2 draws; ~0.05 ms on cell change | P0 |
| BLD-02 | **Footprint grid & blocker callouts** | placement mode; cell change | **Grid:** terrain-conforming mesh of the footprint cells + a 2-cell context border. Squares are inset 0.04 m with a 0.03 m dark outline.<br>• Valid: VALID α 0.35.<br>• Blocked: INVALID α 0.5 + 45° hatch (stripe 0.06 m, period 0.16 m).<br>• Context cells: white α 0.12. Unexplored cells: black hatch.<br>**Blockers:**<br>• units inside the footprint → red ring via a SelectionCircles "blocker" list, pulsing at 3 Hz;<br>• trees → instance colour lerps to #FF6B5E, pulsing;<br>• archetype ground rules (e.g., wrong ground type) → violet hatch #8E5BFF.<br>A one-line reason under the cursor ("Blocked by trees", 14 px), shown after 600 ms so it does not flicker. | `GroundFx.footprint_grid(rect)` (ArrayMesh + 24×24 L8 state texture); `ground_fx.gdshader` mode GRID | < 0.2 ms per rebuild; 1 draw | P0 |
| BLD-03 | **Hall–mine chalk line** | placing a `town_hall` def; nearest mine within 24 m | **Line:** dashed chalk strip (0.12 m wide; dash 0.4 m / gap 0.25 m; scrolls toward the mine at 0.8 m/s; #E8E2D0 α 0.6) from the ghost's footprint edge to the mine's.<br>**Sweet spot:** in the optimal band (edge gap in [min_legal, min_legal + 1.0 m], data `factions.json → economy.hall_mine_sweet`), the line turns GOLD_TEXT, widens to 0.18 m and shows a coin glint at its midpoint. A soft click (UI −16 dB) plays once on entering the band.<br>**No magnetic snap**: the cursor stays in control. | GroundFx strip mode; `build_placement.gd` | 1 draw | P1 |
| BLD-04 | **Placement stamp & surveyor stakes** | valid placement click (build order issued) | **Stamp:** ghost Y 1→0.9 (70 ms QUAD/OUT) → 1.0 (130 ms BACK/OUT), then fades over 180 ms. An ink ring grows from 0.9× to 1.25× the footprint half-diagonal over 380 ms (α 0.55→0, BLUEPRINT). Sound: mallet on paper (UI −12 dB) + the builder's Yes ack.<br>**Stakes** (owner and allies): 4 corner stakes (0.5 m), a rope outline and a team-colour pennant on the front-left stake (flutter). They drop in from +0.8 m, 40 ms apart, each with a 2-frame squash. Shift-queued sites show their queue number on the pennant (Label3D, 24 px).<br>On foundation start, the stakes pop out (scale → 0, 120 ms). On cancel, they topple 80° (250 ms) and fade. | `build_placement.gd`; GroundFx ring; `SiteMarkers` MultiMesh in `building_fx.gd` | 2 draws total | P0 stamp / P1 stakes |

### 3.6 Construction

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-05 | **Foundation drop** | `construction_started` | **Packed earth:** ground layer (footprint × 1.12, #6E5A44 α 0.6, noisy edge) fades in over 300 ms.<br>**Slab:** pops y −0.3 → +0.04 → 0 over 260 ms (BACK/OUT, overshoot 1.6).<br>**Dust ring:** 18 puffs on the footprint perimeter (outward 1.5–2.5 m/s, up 0.4, 0.6→1.4 m, life 700–900 ms, DUST α 0.55→0).<br>Any rubble patch underneath fades out (500 ms).<br>**Sound:** deep wooden thoomp + gravel scatter (World −8 dB, prio 40).<br>Gravebound and Grove variants: see §4. | `building_fx.gd`; GroundFx; StreamFx one-shot puffs | one-off | P0 |
| BLD-06 | **Rising reveal & milestone beats** | every frame while under construction; milestones at 25 / 50 / 75% | p = `display_build_progress()`. clip_y = base_y + 1.05·height·p.<br>**Shader:**<br>• discard above clip_y + wobble (world-xz noise, ±0.12 m, scale 1.3) so the edge looks like courses being laid, not a scanline;<br>• a 0.18 m emissive edge band in the archetype accent (Stalwart #FFE2A8 × 1.3);<br>• back faces exposed by the cut shade #2A2420;<br>• **above the edge, a silhouette preview** of the finished building (next_pass: unshaded fresnel BLUEPRINT α 0.10 + ink lines α 0.08).<br>**Milestones:** edge energy ×2 for 160 ms + 6 dust motes along the edge + creak/thunk (World −16 dB).<br>HP bar and selection ring are untouched. | Placeholders: add `instance uniform float clip_y = 1e6;` and the edge logic to `unit_placeholder.gdshader` (no material swap). GLBs: swap to a `building_build.gdshader` variant at start (copy `albedo_texture`) and restore on completion. | 1 extra pass per site; trivial ALU | P0 |
| BLD-07 | **Construction verb props** | construction state; def `fx.construction` | **Stalwart scaffold:**<br>• poles at the corners and every 2 m, ledgers every 1.2 m, braces on 2 faces;<br>• timber #B08550 with rope #D8C49A; poles 0.08 m thick;<br>• the scaffold top follows clip_y + 0.8 m (SINE/OUT);<br>• kept sparse so at least 70% of the wall area stays visible (progress must stay readable).<br>Other archetypes: §4. | `ScaffoldBuilder` caches one ArrayMesh per footprint size; pooled per-site `MeshInstance3D`s (12) | 1 draw per site | P0 Stalwart, P1 others |
| BLD-08 | **Builder rhythm, sparks & work song** | builders on BUILD or REPAIR, in range | **Beat:** global visual beat of 112 BPM (535.7 ms) from `fx_time`. Builder k of n at a site (sorted by unit id) is offset by k/n of a beat, so 2 builders play eighths and 3 play triplets.<br>**Swing:** curves as in ECO-08, strike at 0.62 of the beat.<br>**Strike:** 3–5 SPARK (0.05×0.25 m, SPARK colour, 50° up-cone, 2.5–4 m/s, g 9, life 180–320 ms) on stone or metal sites; 2 CHIP on timber. The scaffold does a micro-jiggle (Y 0.995, 90 ms).<br>**Sound:** mallet tok (World −14 dB). Pitch = site base (hash: −2, 0 or +2 semitones) + the builder's note from the major pentatonic [0, 4, 7, 9, 2][k mod 5], alternating with the note two steps up. At most 3 builders audible per site and 6 hammer voices total.<br>**Bed:** one construction loop per on-screen site (−18 dB, cap 3), faded over 400 ms at completion.<br>**Repair:** beat period ×1.25. | `UnitView` work animation driven by `FxClock.beat_phase(offset)`; `building_fx` sparks and loops | ~5 µs per strike | P0 (interleave / work song P1) |
| BLD-09 | **Completion flourish** | `building_completed` | **0 ms:** last strike, all builders together (+3 dB) · edge flash ×2.5 · clip off.<br>**0–350 ms:** scaffold poles rotate 70° outward (QUAD/IN) and dissolve (archetype variants: §4).<br>**0–380 ms:** SETTLE.<br>**80 ms:** dust ring, 24 puffs (perimeter, outward 2–3 m/s, 0.8→1.8 m, 900 ms, α 0.5, none over the roof).<br>**80–530 ms:** **ground shockwave ring** from 0.95× the half-diagonal to +3 m (thickness 0.35→0.1 m, α 0.45→0, CUBIC/OUT, archetype accent). It is world-space, with **no camera shake**.<br>**150–750 ms:** the team banner slides from 15% to 100% of the pole (BACK/OUT, overshoot 1.2), then FLUTTER_SPIKE ×2.2 over 1,500 ms.<br>**200 ms:** windows on (400 ms) at night; 15% inner glow by day.<br>**Sound:**<br>• settle thump + creak (World −6 dB, prio 70);<br>• owner fanfare (UI 2D −6 dB, 1.2–1.5 s). The same def completing again within 20 s uses the 0.6 s short variant;<br>• the worker's Job-done line (Acks). If the site is off screen, the advisor's "building finished" line plays instead, plus a minimap blip (3 rings, 1,200 ms).<br>**Unlocks:** newly enabled command-card buttons get a diagonal glint sweep (450 ms, ×2, 300 ms apart) the first time they appear within 20 s.<br>The building is usable on the completion tick; nothing waits. | `building_fx.gd` sequence (closed-form on age); GroundFx ring; StreamFx; `command_card.gd` glint | one-off; ~30 sprites for 0.9 s | P0 (unlock glint P1) |
| BLD-10 | **Cancel / un-build** | `construction_cancelled` | The clip reverses from p to 0 over 450 ms (CUBIC/IN). The scaffold folds inward. 12 dust puffs. Refund popups rise from the site (gold, then lumber 150 ms later). Sound: falling 3-note chime (World −14 dB) + clatter. | `building_fx.gd` | one-off | P2 |

### 3.7 Production & research

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-11 | **Busy-ness tells** | `is_producing()` / `queue_progress()`, polled at 4 Hz | **While producing:**<br>• a chimney smoke puff every 900 ms (0.5→1.6 m, rise 0.9 m/s, life 2.2 s, #8A847C α 0.35; research tints 20% toward the archetype accent);<br>• forges spit 3 SPARK every 700 ms;<br>• mill wheels and bellows animate (GLB `work` clip or shader rotation);<br>• door glow 0.6.<br>**Anticipation:** over the last 10% of a unit's training, the door glow ramps 0.6→1.6.<br>**Idle:** cold chimney, door 0.15, nothing moves. **An idle production building looks still.** Stopping is graceful: in-flight puffs finish. | `building_fx`; StreamFx looped instances per chimney (`t_stop`); def `fx.chimney`, `fx.forge` | ≤ 24 chimneys × 3 looped sprites | P1 |
| BLD-12 | **Door exit & Ready** | `training_completed(building, unit)` | Door FLARE (peak 2.2 → 0.6, 300 ms) + 4 dust motes.<br>The new unit's view offset = door point − `unit.pos` (horizontal; only if ≤ 4 m). It decays to 0 over 280 ms (CUBIC/OUT) with the walk animation forced on, so **the unit trots out of the door**. Scale POP 0.85→1.06→1 (220 ms).<br>Ready line (Acks). With a rally set, the BLD-13 route line flashes once (400 ms).<br>Picking still uses the sim `display_pos()`. | `UnitView.spawn_offset` (rig-local); `building_fx` | negligible | P0 |
| BLD-13 | **Rally flag & route line** | `rally_pos` / `rally_id` change on an own building; building selected | **Flag:** 1.4 m pole with a team-colour pennant (vertex flutter). It drops from +1.6 m in 180 ms (QUAD/IN), lands with a Y squash 0.8→1.0 (160 ms BACK/OUT) and kicks up 5 dirt motes. Plant thunk (UI −14 dB).<br>**Rally on a mine or tree:** the pennant becomes an emblem plaque (pick or axe), and the line tints GOLD_TEXT or LUMBER_TEXT.<br>**Rally on a unit:** a small flag rides 2.2 m above it.<br>**Route line** while the building is selected: straight dashed ground strip from the door to the flag (dash 0.35 m / gap 0.25 m, scrolling toward the flag at 1.4 m/s, α 0.55, team colour lightened 30%). Owner only. | `RallyMarkers` (pooled flags) in `building_fx.gd`; GroundFx strip | 1–2 draws | P0 |
| BLD-14 | **Research complete & upgrade ripple** | `research_finished(building, id)` | **HUD:**<br>• the command-card icon gets a white overlay (α 0.8→0, 300 ms) + a 450 ms glint sweep;<br>• a toast "<upgrade> complete" slides in above the left of the console (from −40 px and α 0, 280 ms BACK/OUT), holds 3,000 ms, slides out in 220 ms. At most 3 stacked;<br>• advisor line (Alerts; completions within 1 s merge).<br>**World:** a spark fountain at the building (16 SPARK, archetype accent HDR 2.0, 700 ms) + chime (World −10 dB).<br>**Upgrade ripple:** a wave travels out from the building at 25 m/s. Each affected own unit on screen (upgrade def `affects`; ≤ 40 units, ≥ 15 ms apart) glints as the wave passes it: `flash(0.45, GOLD)` + a sparkle at the weapon (attack upgrades) or chest (armour upgrades). The first 6 glints tick softly (−22 dB), rising 1 semitone each. | `src/ui/toast.gd`; `building_fx` ripple scheduler; `UnitView.flash(strength, color)` | ≤ 40 flashes | P0 (ripple P1) |

### 3.8 Damage, destruction, repair

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-15 | **Hit feedback & damage states** | `unit_damaged` on structures; HP thresholds with hysteresis (enter < 66% / < 33%, leave > 69% / > 36%) | **Hits:**<br>• chips from the footprint face toward the attacker: 3 for melee, 2 for missiles. Material colour: stone #8C8478, timber #7A5634, hide #8A6A4A, bone #D8CCB0, living #5E7A3A;<br>• 2 dust motes; flash 0.35;<br>• position jitter ±0.025 m for 100 ms, only if the hit is ≥ 2% of max HP;<br>• ≤ 1 burst per building per 120 ms;<br>• hits ≥ 4% of max HP add a heavy-thud layer (World −10 dB).<br>**State 1 (< 66%):**<br>• world-space voronoi cracks that grow with damage (threshold remaps HP 0.66→0.33);<br>• soot darkening toward the roof (×0.7);<br>• one smoke column at a hashed roof point: a puff every 450 ms, 0.6→2.0 m, rise 1.1 m/s, life 2.4 s, SMOKE dark→light, α 0.42, fading above roof + 3.5 m.<br>**State 2 (< 33%):**<br>• fires at 2 hashed `fire_points` (3 on halls): 10 painted flame sprites each (life 450–700 ms, 0.5→0.2 m, rise 1.6 m/s, FIRE ramp core → mid → edge → 0);<br>• 6–10 embers (0.04 m, EMBER, spiralling up, life 1.2–1.8 s);<br>• smoke rate ×2, colour #2E2A27;<br>• crackle loop (World −16 dB, the 3 nearest only).<br>**Night, Forward+:** pooled `OmniLight3D` (pool of 6; no shadows; range 6 m; #FF8A3A; energy 1.1 + 0.25·noise(7t)) on the burning buildings nearest the screen centre. Compatibility uses an emissive lower-wall glow instead.<br>All emission points are deterministic, so a burning building looks the same every time. | `building_fx` state machine; `instance uniform float damage` on the placeholder and building shaders; StreamFx looped smoke, fire and embers; light pool | per burning building: ~16 looped sprites, ≤ 1 loop, 0–1 light | P0 (lights P1) |
| BLD-16 | **Destruction collapse & rubble** | structure `unit_died` | **0 ms:** flash 1.0 (120 ms) · crack + low boom (World −4 dB, prio 70). The player's own hall also raises a 2D alert.<br>**0–150 ms:** shudder ±0.05 m at 20 Hz.<br>**150 ms → end of decay:** the existing k² sink + tilt, plus an XZ bulge 1→1.08.<br>**150 ms debris:** 8–12 CHUNK (halls 14), 0.18–0.45 m, out 3–6 m/s, up 3–5 m/s, g 18, 1 bounce (restitution 0.3), rest 1.5 s, then sink 0.3 m over 800 ms. Landings feed a patter layer (≤ 4 audible).<br>**150 ms donut dust plume:** 32 puffs (halls 44) on a ring at 0.8–1.2× the half-diagonal, rise 1.2–2.0 m/s, 1.2→3.6 m, life 2.2–3.4 s, α 0.5→0. Only 6 centre puffs at α 0.25. A burning building adds 10 fire puffs + 20 embers.<br>**Fallen banner:** the team banner topples last (1,200 ms after the sink starts) and lies on the rubble.<br>**Rubble** at corpse removal: a terrain-conforming patch (procedural stones and planks; scorched centre if it burned), fade-in 300 ms, + 4–6 rubble rocks. It lasts 90 s and fades over 4 s, or fades in 500 ms when a new foundation overlaps it. Cap 24 patches (oldest first).<br>**Visual only:** rubble never blocks pathing or placement.<br>**Sound:** crack (−4) + 1.5–2 s rumble (−6) + patter (−14) + settling creak (−16). | the `UnitView._animate_death` structure branch, extended; `building_fx`; BallisticFx; StreamFx; GroundFx rubble mode + rubble MultiMesh | one-off: ~60 sprites for 3.4 s; rubble 1 draw per patch + 1 shared | P0 (fallen banner P2) |
| BLD-17 | **Repair** | a worker on REPAIR on an own damaged building | Hammer rhythm (BLD-08) at 1.25× the beat period. Each strike: 2 SPARK + 3 repair motes (REPAIR mote colour, 0.06 m, rise 0.8 m/s, life 700 ms) from the work point.<br>Damage visuals follow HP continuously: cracks recede and smoke thins.<br>**Back above 33%:** fires snuff out (shrink to 0 over 400 ms) + steam (6 puffs, STEAM α 0.5, rise 1.8 m/s, 900 ms) + hiss (World −12 dB).<br>**Back above 66%:** the last smoke column thins out over 1,500 ms.<br>**HP bar:** a repair shimmer (white band sweeping left→right every 900 ms). | `building_fx`; a flag channel in `health_bar.gdshader` custom data (HealthBars owner) | negligible | P1 |

### 3.9 Building personality

| ID | Feature | Trigger | Exact spec | Implementation | Perf | Pri |
|---|---|---|---|---|---|---|
| BLD-18 | **Select voice, pulse & gags** | an own building becomes the primary selection | **Voice:** one-shot per building type (UI 2D, 0.6–1.2 s; original sounds per faction, e.g., hall bell, forge anvil ring, barracks shield-bang + call, mill saw rasp). ≤ 1 per 400 ms per building.<br>**Pulse:** `flash(0.28, #FFF3D6)` (60 ms up, 160 ms decay QUAD/OUT) + Y squash 1→0.985→1 (180 ms).<br>**Gags:** clicking the same building 6 times within 3 s plays a unique original gag. Examples: a goose bursts out of the farm door, honks, waddles 1.5 m and vanishes in a puff; the forge belches a smoke ring. Each gag at most once per 60 s; it obeys the "annoyed lines" toggle. | selection hook in `building_fx`; audio ids `bld_<def>_select` and `bld_<def>_gag` | negligible | P0 voice + pulse / P2 gags |
| BLD-19 | **Lamplighter cascade** | the visual hour crosses dusk or dawn | **Dusk:** own and allied building windows light in order of distance from the owner's main hall. Delay = 150 ms + 25 ms per m (cap 4,000 ms). Each ignites with a flicker (on 60 ms, off 40 ms, on) and holds at WINDOW HDR 1.4.<br>**Dawn:** they go out in reverse order.<br>Other players' buildings use hashed delays of 0–2,000 ms. Burning buildings' windows flicker irregularly.<br>Optional soft lantern tink on the first 3 only. | `building_fx` schedules a per-building `windows` instance uniform; GLB window materials flagged `WINDOW` | negligible | P2 |

---

## 4. Construction verbs per archetype

Each archetype gets its own construction **verb** (video-references M8). All four share BLD-05, 06, 08 and 09. This table defines what differs.

| Archetype | Verb | Reveal | Edge / accent | Props & particles | Work sound bed | Completion variant | Builder |
|---|---|---|---|---|---|---|---|
| **Stalwart** | Build from outside | clip rise (BLD-06) | #FFE2A8 (fresh timber and plaster) | timber scaffold (BLD-07); sparks on stone, chips on timber; sawdust | mallets on pegs, hand saw, plank drops; 112 BPM hammer grid | scaffold falls outward; three anvil taps + bronze hand-bell | stands outside and hammers; extra builders interleave (work song) |
| **Warband** | Lash it together from inside | clip rise behind a pole-and-hide frame that is visible from 0% | #FF9A4A (torch-lit lashing) | 6–8 leaning poles with team-colour rags at the tips; hide tarps with vertex flutter cover the unbuilt part; door dust on every drum thump | hide drum at 84 BPM, rope creaks, effort grunts | tarps drop, poles snap upright (120 ms BACK/OUT), war-horn blast + drum roll | hidden inside; the building "breathes" (scale ±1% at 1.4 Hz) so the player can see work is happening |
| **Gravebound** | Summon from a rune circle | the whole building rises from below (translate), clipped at ground level | rune #A8FF5E, core #8E5BFF | ground rune circle (r = 1.1× half-diagonal, rotating 8°/s, emissive HDR 1.4); rising motes 12/s (life 1.2 s); ground cracks spread with progress | low wordless choir hum, bone rattles, slow sub swell | the circle contracts into the base (300 ms), flash, a ghostly exhale ring | casts, then walks away (sim); a thin tether line from builder to circle fades over 1 s |
| **Grove** | Grow from roots | roots creep in (0–20%), then XZ unfurls 0.6→1 + clip | #C8FF7A (leaf gold) | 5–7 tapered root tendrils from the footprint edges; leaf flutter 6/s; pollen motes | creaking wood growth, soft wooden chimes, breath | canopy shiver, petal burst (20 LEAF in petal tints), low flute swell | a consumed builder spirals into the centre (600 ms, light trail); otherwise tends from beside the building |

Mine claims for non-carrying archetypes (a Gravebound "bound" mine, a Grove "rooted" mine) reuse each archetype's verb as an overlay on the mine (P2). Their deposits play at the mine (ECO-04).

---

## 5. Audio layer recipes (economy & buildings)

These follow the audio doc's buses and priorities (§3.5). All 3D sounds respect the fog gate (§2.1). Variation:
- SFX use `AudioStreamRandomizer` with `random_pitch` 1.06 and ±1.5 dB, unless a row sets pitch explicitly.
- Voices have no pitch variation.

| Event | Layers (level, bus) | Positional | Prio | Caps / spacing |
|---|---|---|---|---|
| Mine enter / exit | timber creak −14 / door thump + sack jingle −12 (World) | 3D | 30 | 1 per mine per 250 ms |
| Mine interior | muffled pick clinks −16 (World, low-passed at 1.8 kHz) | 3D loop | 20 | 2 loops |
| Gold deposit | sack jingle −10 + ledger note −16 (pentatonic walk) (World) | 3D | 30 | ≤ 2/s per player |
| Lumber deposit | log clack −11 + low woody note −18 (World) | 3D | 30 | ≤ 2/s per player |
| Tax bite | dull coin tick −20 (World) | 3D | 20 | first 3 per 10 s |
| Chop | axe tok −12 (pitch = tree hash × hollowing) + 30% leaf rustle −20 (World) | 3D | 30 | 4 per id, ≥ 80 ms apart; 4 nearest choppers |
| Tree fall | creak −14 → whoosh −16 → crash/thud −8 (World) | 3D | 40 | 2 concurrent |
| Ghost valid / invalid | wooden tock −18 / muffled thud −20 (UI) | 2D | 85 | ≥ 120 ms apart |
| Placement stamp | mallet on paper −12 (UI) + builder Yes (Acks) | 2D | 90 | – |
| Foundation | thoomp + gravel −8 (World) | 3D | 40 | – |
| Hammer strike | mallet tok −14, pitched work song (World) | 3D | 30 | 3 per site, 6 total |
| Construction bed | per-archetype loop −18 (World) | 3D loop | 30 | 3 loops |
| Milestone | creak/thunk −16 (World) | 3D | 30 | – |
| Completion | settle thump + creak −6 (World) + fanfare −6 (UI, owner) + Job-done line (Acks) | 3D + 2D | 70 | short variant for repeats within 20 s |
| Unit exits | door creak −14 (World) + Ready (Acks) | 3D + 2D | 90 | ack rules from the audio doc |
| Rally plant | thunk −14 (UI) | 2D | 85 | – |
| Research done | chime −10 (World) + toast swish −16 (UI) + advisor (Alerts) | 3D + 2D | 70 | merge within 1 s |
| Building hit (extra) | heavy thud −10 for hits ≥ 4% max HP (World); base impact from the combat matrix | 3D | 60 | 1 per building per 120 ms |
| Burning | fire crackle loop −16 (World) | 3D loop | 20 | 3 nearest |
| Destruction | crack −4 + rumble −6 + patter −14 + settling creak −16 (World) | 3D | 70 | patter ≤ 4 |
| Repair | mallet −14; snuff hiss −12 (World) | 3D | 30 | as hammer |
| Denial | faction error −10 (UI) + advisor (Alerts) | 2D | 85 | 1.5 s per kind |
| Upkeep change | two-note ledger interval −10 (UI) + advisor (Alerts) | 2D | 85 | advisor once per 60 s per tier |
| Building select | per-type one-shot −6 (UI) | 2D | 70 | ≤ 1 per 400 ms per building |
| Mine low / collapse | creak −18 (World) / crack −4 + slide −6 (World) + advisor (Alerts) + ping | 3D + 2D | 95 (alert) | once per mine |

**IP:**
- No WC3 audio or lines. "Job's done" and "Work complete" are banned.
- Job-done and advisor lines come from the audio doc's original scripts (e.g., "Built to last. Mostly.", "Ledger's short on gold.").
- Completion fanfares and the ledger bell use our own motifs.

---

## 6. Our own twist (what WC3 did not have)

Each item makes a hidden economy number readable or gives the base more character. None changes an outcome.

1. **Saturation lanterns (ECO-02).** Mine saturation is shown on the mine itself: five pips, plus an orange flicker when oversaturated. WC3 players learn "5 per mine" from guides; ours see it.
2. **Tax bite (ECO-05).** Upkeep becomes visible: the taxed share of each trip peels off the popup and crumbles away. Liquipedia notes that WC3's floating gold text never shows the upkeep reduction. Ours makes "High Upkeep is meant to be punishing" something the player sees on every trip.
3. **Ledger chime (ECO-04).** Deposits walk a pentatonic scale, so a healthy economy plays a little tune and a stalled one goes quiet. The player hears income.
4. **Tree hollowing (ECO-10).** Chops ring higher and the tree leans as its lumber runs out. A player can hear a tree is about to fall and pre-position workers.
5. **Log bundles show the lumber upgrade (ECO-03).** One, two or three logs on the shoulder: the upgrade is visible in the field.
6. **Upkeep ruler (ECO-15).** Upkeep thresholds sit on a ruler under the food counter. The next tick pulses when you are within 4 food, so the threshold is visible before you cross it.
7. **Pending supply and stalled-for-food icons (ECO-16).** "(+6)" tells you relief is coming. A crossed-out food icon over a barracks door explains why its queue stopped.
8. **Hall–mine chalk line (BLD-03).** Optimal expansion placement is taught by the game, without snapping the cursor.
9. **Surveyor stakes with queue numbers (BLD-04).** Pending and shift-queued build sites are visible to you and your allies before the worker arrives.
10. **Silhouette preview above the build edge (BLD-06).** You can see what is being built, and how far along it is, at a glance and without clicking. Spectators get this too.
11. **Work song (BLD-08).** Multiple builders lock into an interleaved rhythm on a shared beat. Power-building (WC3's Human mechanic) sounds as fast as it is.
12. **Busy-ness tells (BLD-11).** Chimneys smoke and forges spark only while working. A cold chimney is an idle building, which makes macro mistakes visible from the playfield.
13. **Upgrade ripple (BLD-14).** An upgrade travels out from the forge through your army, showing exactly which units got it.
14. **Fallen banner and rubble memory (BLD-16).** The flag falls last and lies on the ruins for 90 s, so the battlefield remembers what stood there.
15. **Building gags (BLD-18).** WC3's "pissed" clicks were a unit feature; we extend the personality layer to buildings.
16. **Lamplighter cascade (BLD-19).** At dusk the town lights up house by house, outward from the hall.
17. **Donut plumes (BLD-16, ECO-07).** Plumes spawn as a ring with a thin centre, so big set pieces never hide the units fighting in the ruins.
18. **Tool swap (ECO-03).** Pick, axe or hammer in hand shows each worker's job without clicking.
19. **GPU closed-form particles (§2.3).** Coins, chips and debris cost zero CPU per frame and are refresh-rate independent by construction. This lets us afford the juice at 300 units.

---

## 7. Anti-patterns (do not ship these)

**Feel**
- **Mobile coin showers.** No coins flying to the HUD on every deposit, and no slot-machine counters. A small burst plus one popup is the ceiling. HUD coins appear only for spends of 200 or more.
- **Number soup.** Twelve workers must not produce twelve "+10"s a second. Always merge (350 ms window), cap at 6, and show only on-screen own deposits.
- **Screen shake for economy or building events.** RTS precision clicks need a stable camera, and 300 units of shake is nauseating. Use world-space shockwaves, building squash and HUD micro-shakes instead.
- **Long ceremonies on frequent events.** A 5 s fanfare on the tenth farm is too much. Repeats get the 0.6 s short variant. Deposits stay under 1 s, popup included.
- **Generic sparkle.** Gold glitter on everything means nothing reads. Each material has its own particle, motion and sound (rule 4).
- **Fanfare without information.** If an effect answers no player question and is not rare, cut it or move it to juice level 2.

**Gameplay safety**
- **The sim waiting on the juice.** Delaying a deposit until the sack lands, a building's availability until the flourish ends, or a unit's spawn until the door animation finishes changes timing. This is forbidden.
- **Juice writing sim state.** No `Unit.pos` offsets (use the rig), no `World.rng`, no gameplay signals from fx code. Keep tween references in views or fx, never on `Unit`.
- **Fog leaks.** No chips, chop sounds, smoke or construction sounds from entities the local player cannot see. Saturation lanterns never show enemy usage.

**Engine**
- **Frame-counted or `_physics_process` visuals.** These break the 30 / 60 / 144 / 240 Hz rule. Use age-based curves and fixed-substep springs.
- **Node churn.** No `Node.new()` or `create_tween()` per particle or per deposit. Pool everything. Spawns are slot writes.
- **Per-unit or per-building `OmniLight3D`s and always-on `GPUParticles3D`.** Use the 6-light pool, looped closed-form streams and one-shot puffs.
- **`Decal` nodes.** They are unsupported on Compatibility. Use GroundFx meshes.
- **Physics bodies for debris.** Use closed-form arcs.

**Readability**
- **Smoke or fire covering units.** Emitters stay inside the footprint × 0.8, α ≤ 0.5, fade above 4 m, donut plumes. No full-screen dust.
- **Hidden progress.** Scaffolds or tarps too dense to see the reveal edge break readability; keep at least 70% of the wall visible.
- **Red/green-only signals.** Always add hatching, glyphs or notches.
- **Random fire positions per frame.** Use hashed, stable emission points.
- **Infinite accumulation.** Rubble and stumps have caps and lifetimes. Stumps are permanent but share one MultiMesh.

**IP**
- **Copying WC3 specifics.** No WC3 lines ("Job's done", "Work complete"), building select sounds, level-up or completion motifs, gold-mine or scaffold model designs, or "+N" bounty font styling. Generic conventions are fine: popups, scaffolds, sacks, falling trees.

---

## 8. Verification

| Check | How | Pass criterion |
|---|---|---|
| Juice never changes outcomes | `tests/unit/test_juice_determinism.gd`. An economy scenario (5 miners, 3 choppers, 1 barracks built, 4 units trained, a building burned to 20% and repaired, one tree felled) runs 3,600 ticks twice: `World.visuals = false`, then visuals on with juice level 2, driving `_process` with randomly varied deltas (1/30–1/240 s). | Per-tick hash of player gold, lumber and food, unit positions and build progress is identical. |
| Refresh-rate independence | Evaluate `JuiceCurves`, popup RISE_FADE and the CPU mirror of the ballistic formula at the same wall times, accumulated with 30 steps of 1/30 s vs 240 steps of 1/240 s. Springs: compare after 1.0 s. | Curves exact; springs within 1 mm. |
| Caps hold | `tests/unit/test_fx_budget.gd`: 200 `resource_delivered` events in one frame, 60 `tree_harvested`, 30 simultaneous completions. | Popups ≤ 6, ring buffers never grow, Audio per-id and total caps respected, no errors logged. |
| Fog honesty | Enemy worker chopping in fog. | 0 chips spawned, 0 chop sounds. |
| Look | `tests/playtest/economy_juice.gd` screenshots (lavapipe and opengl3): ghost valid and invalid, 50% construction (Stalwart), completion at T+200 ms, burning (< 33%) by day and by night, collapse at T+600 ms, rubble, mine low. | Art review against §2.5 and the readability rules. Health bars visible in every capture. |
| Perf (real GPU) | `tests/playtest/bench_econ_fx.gd`: 300 units incl. 40 workers, 12 burning buildings, 3 construction sites, a hall destroyed mid-run. | Economy and building juice add ≤ 0.6 ms CPU per frame on average, ≤ 1.2 ms at peak, and ≤ 20 draw calls. 60 fps held on the mid-range target. |

---

## 9. Open questions

1. **Hall–mine optimal band** (`economy.hall_mine_sweet`) depends on the final gather timings. Tune it once `economy.gd` exists.
2. **Archetype mapping.** Which archetype the Thornborn (or a renamed faction) uses decides which non-Stalwart verb becomes P0.
3. **MultiMesh custom-data precision on Compatibility** (§2.3) is unverified. The packing keeps time-critical floats in the transform either way. Confirm with a 2-hour `fx_time` soak.
4. **Gold popups for veterans.** Should `eco_popups` default off at juice level 0, leaving only the tax bite? Decide by playtest with experienced RTS players.
5. **Saturation lanterns for allies.** Show allied usage of a shared mine in the ally colour? Default: own usage only.
6. **Art for painted sprites** (dust, smoke, flame flipbook, crack mask, rubble) is needed from the asset pipeline. Until then, procedural shader fallbacks keep the rule "runs without art".
