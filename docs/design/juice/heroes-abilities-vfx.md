# Juice Spec: Heroes, Abilities, Creeps & the VFX Language

*Domain doc of the Vibecraft juice bible. Date: 2026-10-16. Status: design spec, ready to implement.*

**Covers:**
- hero presence, XP, level-up, hero death and revive;
- the spell VFX language (eight schools);
- cast and targeting feedback;
- buffs, debuffs and crowd-control tells;
- invisibility and summons;
- items, loot, consumables and recall;
- creep camps (sleep, wake, aggro, leash, cleared);
- ultimates.

**Out of scope (owned by sibling docs):**
- **Combat doc** (`combat-and-units.md`): swings, hits, generic death, combat text, health bars, creep "notice" (CMB-06) and hero swagger (CMB-34).
- **Economy doc** (`economy-and-buildings.md`): construction and building fire.
- **World doc:** day/night ambience beds and dusk/dawn stingers.
- **UI, camera and audio doc:** HUD frames and fonts, the camera shaker, the mixer.

This doc **owns** the items the combat doc hands over (§"Cross-doc contracts" there): hero glow, level-up, revive, hero death and spell particles. It also owns creep-camp feel, as assigned by the juice-bible brief.

**Inputs:**
- `docs/research/visual-art-direction.md`: VFX are the only things that bloom; chunky painterly; "toy-soldier" motion.
- `docs/research/audio-direction.md`: buses, priorities, our own level-up cue (§4.4 prompt 15).
- `docs/research/video-references.md` §G: M1 level-up, M2 hero death, M4 sleeping creeps, M12 aura feet, M15 item drops.
- `docs/research/gameplay-mechanics.md`: §4 heroes, §5 creeps, §10 items, §13.6 slice creeps.
- `docs/research/godot-rts-tech.md`: no `Decal`; Compatibility limits.
- `docs/architecture.md`: 30 Hz sim, physics interpolation, `display_pos()`.
- `docs/design/factions/kingdom.md` §6, §7.4 and `clans.md` §6, §9: slice heroes, altars, recall items.

**Slice content this doc animates:**
- **Kingdom heroes:** Wheel Marshal and Firewright; altar **Oath Hall**; recall item **Homeward Horn**.
- **Clans heroes:** Long-Braid and Skymirror; altar **Naming Stones**; recall item **Homeward Felt**.
- **Creeps:** Briar Hound, Moss Shaman, Bog Lurker, Cave Brute, Hill Ogre-kin, Ancient Rootwarden (never sleeps).
- **Neutral:** the central Merchant.

**Conventions (same as the siblings):**
- Durations are ms at 1× game speed. Distances are metres; `h` is the unit's height.
- Colours are sRGB hex. "HDR n" is an emission multiplier; only n > 1.0 blooms.
- Easings are the Penner functions in `Juice` (combat FND-1): `out_quad`, `in_quad`, `out_cubic`, `in_cubic`, `in_out_sine`, `out_back(c1)`, `out_bounce`. When no c1 is given, `out_back` uses c1 = 1.70158.
- Named curves POP_IN, RISE_FADE, FLARE and SHAKE are the economy doc's `JuiceCurves` (§2.4).
- "Own" means the local player, or the observed player in observer mode.
- **★** marks a twist WC3 did not have.

---

## 1. Feel goals

Heroes are the protagonists of every match, so this layer is about **attention and truth**. The targets:
- You can find your hero in a 60-unit melee in under half a second.
- You can read what a spell will do *before* it lands and exactly *where* it lands.
- Every milestone (a level, an item, a cleared camp) feels like a small party that never takes a frame of control away from you.

Spells speak **one visual language**. There are eight schools, each with its own palette, **shape** and **rhythm**. Every spell follows the same three beats:
1. an anticipation that exactly fills the sim's cast point;
2. a release on the effect tick;
3. a linger that shows what is still in effect.

We keep WC3's conventions (hero glow, level-up pillar, sleeping creeps, glinting loot) and make each one **carry information**:
- the hero ring becomes a character sheet;
- timers live on the battlefield instead of in bars;
- every area effect is drawn exactly as big as it is.

The texture is the diorama's: painted petals, felt, bronze glints, gunpowder smoke and chalk lines. It is never neon, never glitter, never "magic sparkles" in general.

**Five rules for this domain:**

1. **Truthful.** The visual footprint equals the gameplay footprint (±2 %). Release visuals land on the sim's effect tick. Every timer is drawn from a sim reader, never from a local clock.
2. **Telegraph, then pay off.** Each school has its own wind-up rhythm, and that rhythm finishes exactly at release. An opponent can learn when to dodge, and a caster feels the snap.
3. **Ceremony scales with rarity.** Approximate frequencies and lengths:

   | Event | Happens about | Ceremony length |
   |---|---|---|
   | XP gain | every few seconds | ≤ 0.7 s |
   | Potion | a few times per game | 0.5 s |
   | Item pickup | a few times per game | 0.6 s |
   | Level-up | 9 times per game | 1.5 s |
   | Camp cleared | 5–7 times per game | 1.6 s |
   | Ultimate | 2–5 times per game | a 7–25 s set piece (Grand Bombard is the 25 s one) |

   Nothing frequent is long.
4. **Readable in the brawl.** Danger is never throttled: zone edges, CC glyphs and timers always draw at full strength. Cosmetic lingers are the first thing cut. Units, team colour, health bars and selection rings always draw on top of spell effects.
5. **Fair.** Juice never leaks information the game hides:
   - fogged or invisible units;
   - enemy cooldowns and XP progress;
   - your altar's location;
   - which creep carries the item.

   It also never shows anything that did not happen.

---

## 2. Shared foundations (read before implementing any row)

### 2.1 Ground rules

**These inherit everything in combat §2 and economy §2.1:**
- The sim is authoritative at 30 Hz. Juice only reads sim state.
- No `World.rng`, no `Engine.time_scale`, no sim delay.
- Motion is a closed-form function of age, or uses the closed-form spring.
- No `Decal` nodes.
- Pool everything.
- Fog is honoured: `Vfx.allow(kind, pos, importance)` gates every spawn.

**Additions for this domain:**

1. **Two clocks** (combat §2):
   - World effects use `Vfx.now`, which is also uploaded as the global shader uniform `fx_time`.
   - HUD feedback uses `Vfx.ui_now`.

   Spell anticipation does not use either clock. It uses **sim progress readers** (`cast_progress()`, `channel_progress()`, `buff_remaining()`, `life_ratio()`, `revive_progress()`), interpolated with the physics fraction.
2. **Cast sync.** The release visual spawns in the frame that processes `ability_released`, which is the tick the sim applies the effect. Anticipation must reach 1.0 on that frame. If anticipation would finish early, it holds at full charge. It never releases early.
3. **Truthful radii.** Every reticle, zone, splash ring and aura ring uses the radius in the ability def, measured to the outer edge of the edge line. Only vertical elements (pillars, smoke, curtains) may extend past the radius, and only upward. A unit test enforces this (§10).
4. **Info honesty (in addition to fog):**
   - Invisible-to-local units are treated as fogged: no sprites, labels, sounds or XP motes, and no level-up.
   - Enemy XP progress and enemy ultimate readiness are never drawn.
   - Enemy soul sparks never fly toward their altar.
   - Creep item carriers are never marked.
   - Previews query exactly what the sim will query.
5. **Physics interpolation.** Sigils, glyphs, motes and rigs are `physics_interpolation_mode = OFF` and positioned from `display_pos()`. Teleports use `reset_physics_interpolation()`; `Unit.teleport()` already does this.
6. **Heroes have importance 3** (combat FND-3), so hero events are never throttled by the density governor.

### 2.2 Sim → view contract (what `abilities.gd`, `heroes.gd`, `creeps.gd` and items must expose)

None of these systems exist yet. Juice needs the hooks below. They are cheap and deterministic, and the HUD, the AI and replays need most of them anyway.

**Contract rule:** a change to `Events` or `Unit` also updates `docs/architecture.md` §5 and §10 **in the same commit**.

**Signals:**

| Hook | Emitted by | Notes |
|---|---|---|
| `ability_cast_started(caster, ability_id: String, rank: int, target_id: int, target_pos: Vector3, cast_point_s: float)` | abilities | On the tick the cast point begins, after the caster has turned to face. |
| `ability_released(caster, ability_id, rank, target_id, target_pos)` | abilities | On the tick the effect applies or the missile launches. |
| `ability_cast_cancelled(caster, ability_id, reason: String)` | abilities | `reason`: `stunned`, `ordered`, `target_lost` or `silenced`. |
| `channel_started(caster, ability_id, duration_s)` / `channel_ended(caster, ability_id, completed: bool)` | abilities, items | Used by recall, cast times and channels. |
| `buff_applied(unit, buff_id, source, duration_s, rank)` / `buff_refreshed(...)` / `buff_removed(unit, buff_id, reason)` | abilities | `reason`: `expired`, `dispelled`, `died` or `broken` (broken by damage, e.g. Salt Tea). |
| `zone_created(zone_id: int, ability_id, owner_player, pos, radius, duration_s)` / `zone_ended(zone_id)` | abilities | Every ground effect that has gameplay. |
| `lethal_prevented(unit, amount)` | combat | The Wagon Ring's 1-HP clamp. |
| `hero_xp_gained(hero, amount: int, src_pos: Vector3, factor: float, shared_with: int)` | heroes | `factor` is the creep XP factor; 0 triggers the fizzle (HER-03). |
| `hero_level_up(u)` → **extend to** `hero_level_up(u, new_level: int, levels_gained: int)` | heroes | Already declared in `events.gd`; this adds two arguments. |
| `skill_learned(hero, ability_id, rank)` | heroes | |
| `hero_died(hero, killer)` | heroes | Emitted alongside `unit_died`. |
| `hero_revive_started(altar, hero, duration_s)` / `hero_revived(hero, altar)` | production / heroes | |
| `summon_spawned(summon, owner, life_s)` | abilities | Expiry arrives through `unit_died` with `killer == null` and `summon_expired = true`. |
| `item_dropped(item, item_id, from_pos: Vector3, from_unit)` | heroes, creeps | A ground item is an entity: a `Unit` of kind `item`, like gold mines. See open question 7. |
| `item_picked(hero, item_id, slot)` / `item_used(hero, item_id, slot, charges_left)` / `item_pickup_failed(hero, item, reason)` | heroes | |
| `unit_teleported(u, from: Vector3, to: Vector3, kind: String)` | `Unit.teleport()` | `kind`: `recall` or `blink`. |
| `creep_sleep_changed(u, asleep: bool, reason: String)` | creeps | `reason`: `dusk`, `dawn`, `damage`, `build` or `spell`. |
| `camp_aggro(camp_id, leader, target)` / `camp_leash(camp_id)` / `camp_cleared(camp_id, player_id, gold, xp, pos)` | creeps | |

**Readers:**

| Reader | Notes |
|---|---|
| `Unit.cast_progress()` | 0..1 inside the cast point, or −1. Interpolated the way `display_pos()` is. |
| `channel_progress()`, `buff_remaining(id)`, `buff_view_list()` | |
| `is_invisible()`, `invis_alpha()` | `invis_alpha()` is the sim fade, 0..1. |
| `is_detected_by(player)` | |
| `life_ratio()` | Summons. |
| `xp_ratio()` | Progress to the next level, 0..1. |
| `cooldown_ratio(ability_id)` | |
| `revive_progress()` | On altars. |
| `recall_candidates()` | The units that would travel if recall completed now. |
| `camp_id`, `is_asleep` | |
| `ultimate_ready()` | Own and allied heroes only; checks cooldown and mana. |

**Def `fx` blocks.** Validated by `Defs`; unknown keys warn once.

- **Ability:**
  ```json
  "fx": {"school": "ember", "recipe": "naphtha_flask", "reticle": "circle",
         "preview": "burn_ring", "timer": "none", "ultimate": false,
         "cast_point": 0.3}
  ```
  `cast_point` is in seconds. **Abilities need a sim `cast_point`.** The default is 0.3 s and ultimates default to 0.5 s; see open question 3.
- **Hero:**
  ```json
  "fx": {"sigil": "ember_wheel", "flourish": "wheel_spin",
         "death_edge": "#FFB46B", "prop_hand": [0.32, 1.55, -0.2]}
  ```
- **Altar:**
  ```json
  "fx": {"altar": "wheel" | "mirrors", "parts": ["FloorWheel"] | ["Mirror1", ...]}
  ```
- **Item:**
  ```json
  "fx": {"bundle": "satchel" | "crate" | "tome" | "casket", "tier": "A" | "B" | "C" | "D"}
  ```
- **Creep:**
  ```json
  "fx": {"family": "hound", "never_sleeps": false}
  ```
- **Map camps:**
  ```json
  "camps": [{"id": 3, "dressing": {"standard": [x, y, z], "fire": [x, y, z]}}]
  ```

### 2.3 FX building blocks (new files; everything else reuses siblings)

**Reused:**

| Piece | Source | Used here for |
|---|---|---|
| `Juice` (springs, `damp`, easings) | combat FND-1 | |
| FxSprites (stateless additive and alpha sprite pool) | combat FND-2 | One-shot motes, sparks, petals, feathers, shards |
| Governor (tiers and `Vfx.allow`) | combat FND-3 | |
| `ImpactLights` | combat FND-3 | |
| StreamFx (looped closed-form flames, steam, smoke) | economy §2.3 | |
| BallisticFx closed-form arc | economy §2.3 | Loot bounces and coins |

**New:**

| File | Contents |
|---|---|
| `src/fx/spell_fx.gd` (`SpellFx`) | Recipe player (HVF-1). One record per active cast/zone/rig; 24 records; 16 pooled rig nodes. |
| `data/fx_recipes.json`, `data/fx_schools.json` | Recipes per ability and item; school tokens (§5). Loaded by `Defs`. |
| `src/fx/ground_zones.gd` + `ground_zone.gdshader` | Terrain-draped reticles, zones, edges, timer arcs, aura radius rings and cast glyphs (HVF-2). |
| `src/fx/status_fx.gd` + `status_glyph.gdshader` | Feet, body and head status layers (HVF-3). |
| `src/fx/hero_sigils.gd` + `hero_sigil.gdshader` | Hero sigil MultiMesh (HER-01). |
| `src/fx/hero_fx.gd` | Level-up, death and revive sequences (HER-04, HER-06, HER-07). |
| `src/fx/xp_motes.gd` | Homing XP motes (HER-03). |
| `src/fx/beams.gd` + `beam.gdshader` | Pillars, shafts, line beams, loot rays and curtains. A MultiMesh of a capped cylinder plus a cross-quad variant. |
| `src/fx/loot_fx.gd` | Ground items, drop bounce, rarity rays, pickup hop (ITM-01, ITM-02). |
| `src/fx/creep_fx.gd` | Camp state visuals (CRP-01 to CRP-04). |
| `src/fx/screen_tint.gd` | Ultimate vignette (ULT-01). |
| `src/input/ability_targeting.gd` | Reticles, range rings and previews (ABL-02 to ABL-04). Owned by `CommandInput`. |
| `src/ui/hero_bar.gd` | Left-edge hero buttons: level badge flip, XP pour, revive sweep, skill pip. The UI doc owns the frame art. |

**Changed:**

| File | Change |
|---|---|
| `src/entities/unit.gdshader` (combat doc) | Status instance uniforms (HVF-4). |
| `unit_view.gd` | Composer layers `cast` and `status`, flourish props, death/revive branch for heroes. |
| `vfx.gd` | Routes the new signals. |
| `hud.gd` / `command_card.gd` | HER-05. |
| `audio.gd` | Voice categories `levelup`, `ability_<id>`, `need_mana`, `pack_full`; plus `duck(bus, db, ms)`. |
| `impact_lights.gd` | Priorities, highest first: **ultimate 5**, **level-up/revive 4**, hero spell 3, siege 2, crit 1. |

### 2.4 Density, juice levels and caps for this domain

**Juice levels** (`Settings.juice_level`, shared with the siblings):

| Level | This domain |
|---|---|
| 0 Competitive | **Keep:** sigil base and level notches; reticles and range rings; zone edges and fills; every status glyph and timer; invisibility and detection; level-up ring, numeral, cue and portrait flip (pillar shortened to 600 ms); death and revive core; loot drop and rarity rays; camp "!", Zs and stinger.<br>**Drop:** flourishes, XP motes (the HUD pour stays), screen tints, music duck, nightcaps, yawn wave, camp dressing, tome page flutter, soul spark. |
| 1 Default | Everything in this doc except the cinematic extras. |
| 2 Cinematic | Level-up pillar ×1.3 and its light also by day; petals, dust and feathers ×1.5; ultimate tint α 0.10; a night light for each own hero (pool permitting). |

**Tier rules.** Calm, Busy and Brawl are defined in combat FND-3.

**Never throttled:**
- reticles, previews, zone edges and fills;
- head glyphs, stun stars and every diegetic timer;
- level-up, death and revive;
- invisibility visuals;
- loot rays;
- the ultimate frame.

**Busy:**
- linger particles ×0.6;
- feet glyphs α ×0.8, except on selected units and heroes;
- at most 3 XP motes per hero per kill;
- flourishes off.

**Brawl:**
- linger particles ×0.35;
- feet glyphs at α 0.15, except auras from selected units and from heroes;
- 1 XP mote per hero per kill;
- burn licks only on the 24 burning units nearest the camera focus;
- at most 2 Zs per sleeper.

**Caps:**

| Item | Cap |
|---|---|
| Live spell records | 24 |
| Rig nodes | 16 |
| Ground zones and reticles | 96 instances |
| Sigils | 16 |
| Feet glyphs | 256 |
| Head glyphs | 512 instances, shared by glyphs and stun-star sub-instances (6 per stunned unit). Head glyphs are never throttled. If the cap is ever exceeded, heroes and the units nearest the camera focus keep theirs. |
| XP motes | 32 |
| Ground items | 64 |
| Label3D (numerals, stamps, nameplates) | 6 |
| Screen tints | 1 |
| Spell loops | 3 nearest |
| Snore loops | 2 nearest |

### 2.5 Palette tokens (extends `JuicePalette`; school colours are in §5)

| Token | Hex | Token | Hex |
|---|---|---|---|
| SIGIL_IVORY (kingdom spokes) | #EDE2C8 | SIGIL_BRONZE (clans band / highlight) | #A8743A / #D9A55E |
| LEVEL_PIP on / off | #FFE6A0 (emission 0.9) / #3A2E22 | ULT_GEM lit | #FFF1C2 (emission 1.0; sparkle HDR 1.8) |
| XP mote / XP pour new / XP bar | #FFE9A8 HDR 1.6 / #FFF6DE / #E8B84A | LEVEL ring kingdom / clans | #FFC46B / #FFD27A |
| PILLAR core / edge | #FFF0C8 HDR 2.4 / #FFC46B | NUMERAL fill / outline | #FFE6A0 / #3A2400 |
| DEATH_EDGE kingdom / clans | #FFB46B HDR 1.8 / #C8D4E8 HDR 1.6 | GLYPH_CREAM / outline (Zs, "…") | #F3E6C4 / #2A2014 |
| ALERT_BANG ("!" / "‼") / outline | #FF5A3A / #2A0A04 | STUN_STAR / outline | #FFF1B0 / #3A2400 |
| PREVIEW_ENEMY / PREVIEW_ALLY / INVALID | #FF6A4A / #7CFF8A / #9AA0A6 | REGEN_MOTE ("+") | #9BE36A |
| LOOT A–B / C / D | #FFF6DE / #FFD27A / #FF9FC8 | STR / AGI / INT | #FF7A4A / #6AE07A / #4FA8FF |

- **Team colour is reserved for ownership:** the sigil band and the recall carpet trim. It is never used for spell particles.
- **Allegiance is coded by edge shape** (ABL-06): smooth for own and allied, notched for hostile, dashed for creeps. Colour is secondary.

### 2.6 Size and legibility reference

Default camera: 28 m distance, vertical FOV 45°, pitch −56°, 1080p.

| What | Pixels per metre |
|---|---|
| Billboards and ground width | ≈ 46 |
| Ground depth | ≈ 39 |
| Upright height | ≈ 26 |
| Anything at max zoom-out (46 m) | × 0.61 |

**Minimum on-screen sizes**, clamped in the shaders with `size = max(size_m, min_px / px_per_m(view_depth))`:

| Element | Minimum |
|---|---|
| Head glyph | 18 px |
| Stun star | 8 px |
| Z | 7 px |
| XP mote | 5 px (plus its HDR halo) |
| Loot bundle | 16 px |
| Edge lines | 2 px |

Heroes are 2.0–2.3 m tall, about 55–60 px of standing height.

---

## 3. Foundations (build first, all P0)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| HVF-1 | **SpellFx recipe player** | ability, buff, zone, item and summon signals | **A recipe has three phases:**<br>• **Anticipation** (glyph, orb, pose, telegraph, riser). Driven by `cast_progress()`.<br>• **Release** (bursts, beam, ring, light, sound). Spawned on `ability_released`.<br>• **Linger** (zone or status visuals, tail, scorch). Driven by `Vfx.now` age or sim readers.<br>**Example:** `{"school":"ember","anticipation":{"telegraph":"fuse","orb":true},"release":{"burst":"ember_splash","radius":"def","ring":true,"light":3},"linger":{"zone":"ember_fire","scorch":true}}`.<br>**Missing data:** a missing recipe falls back to the school default. A missing school falls back to neutral white with the Orrery shapes. The game always runs without art. | `src/fx/spell_fx.gd`:<br>• 24 records in a ring buffer;<br>• rigs are pooled `Node3D` + `MeshInstance3D` / `MultiMeshInstance3D` for unique meshes (wagon wheels, crate, eclipse disc, grass);<br>• transients go through FxSprites, StreamFx, GroundZones, Beams and StatusFx.<br>Recipes load into `Defs.fx_recipe(id)`. | ~15 µs per event; ~2 µs/frame per live rig (≤ 16) | P0 |
| HVF-2 | **Terrain height texture + GroundZones** | map build; any ground-draped effect | **Bake:** `terrain_height`, an `Image.FORMAT_RH` texture at 1 m texels (193 × 193 for the slice), from `MapData.height_at`. It becomes a global shader uniform (`GLOBAL_VAR_TYPE_SAMPLER2D`) next to `map_size_m`. RH filters linearly in GLES3. Cliffs smear over 1 m, which is fine for overlays.<br>**GroundZones:** one MultiMesh of a 32 × 32-quad grid patch (unit square). The instance transform holds centre, scale (2r, or length × width for lines) and yaw. The vertex shader samples `terrain_height` and adds 0.04 m.<br>**Fragment modes** (from custom data): `CIRCLE`, `DONUT`, `RECT`, `CONE`, `FILL_<school>`, `EDGE_SMOOTH`, `EDGE_NOTCHED`, `EDGE_DASHED`, `TIMER_ARC`, `FUSE_RING`, `GLYPH` (sampled from the school glyph `Texture2DArray`) and `GLOAM_DARK`.<br>**Render:** `depth_draw_never`, depth test on with a 0.02 bias, no shadows, `render_priority` below units and above terrain.<br>An 11 m radius drapes at 0.69 m per cell, which is enough. | `TerrainBuilder` bakes the texture; `src/fx/ground_zones.gd` + `ground_zone.gdshader`. Identical on Forward+ and Compatibility (no Decals, no screen reads). | 1 draw for all zones and reticles; ≤ 96 instances; ~0.02 ms/frame | P0 |
| HVF-3 | **StatusFx: three layers** | `buff_*` signals; per frame for units with statuses | Rules in STS-01.<br>**Feet:** flat quads tilted to the terrain normal (as `SelectionCircles`), from a 4 × 4 glyph atlas.<br>**Head:** billboards at the unit top + 0.35 m, offset up 6 px in screen space, so they sit above the health bar; min-px clamp from §2.6.<br>**Body:** per-unit uniforms (HVF-4) plus StreamFx or FxSprites streams, at most 3 per unit.<br>A per-unit view state (dictionary id → state) is touched only while the unit has a status. | `src/fx/status_fx.gd` (feet MultiMesh 256, head MultiMesh 512 including star sub-instances) + `status_glyph.gdshader` (atlas, per-instance frame, progress and spin in `INSTANCE_CUSTOM`). | 2 draws; ~1 µs per affected unit/frame | P0 |
| HVF-4 | **Unit shader status uniforms** | status, death, revive, summon, invisibility | Packed per-instance uniforms on `src/entities/unit.gdshader`, the same mechanism as today's `flash`. Godot allows ≤ 16 instance uniforms per shader; we add 4 vec4s next to `flash`:<br>• `status_a` = (frost height 0..1, char 0..1, dust film 0..1, summon rim 0..1);<br>• `status_b` = (dissolve 0..1, dissolve direction +1 feet-up / −1 top-down, invis 0..1, detected 0/1);<br>• `status_col` = dissolve edge rgb + HDR;<br>• `status_rim` = rim colour override rgb + strength.<br>**Dissolve:** height-normalised threshold + hash 3D noise, with a 0.06 m emissive edge band. No texture is needed.<br>**Invis:** Bayer 4 × 4 ordered-dither `discard`, which stays in the opaque pipeline (no sorting). Coverage = 1 − 0.65·invis.<br>**Forward+ only:** a `next_pass` shimmer with `hint_screen_texture`, applied to own invisible units only.<br>**Frost:** world-height mask mixing rime #DFF3FF + sparkle.<br>**Char:** multiply 0.85 with ember speckles. | `unit.gdshader` (shared with the combat doc); `UnitView.set_status(key, value)` writes only on change. | ≈ 0 when unused; 1 extra pass only for own invisible units on Forward+ | P0 |
| HVF-5 | **School kit and tokens** | data | `data/fx_schools.json` holds the §5 table:<br>• palette (core, mid, edge, dark, HDR);<br>• glyph layer and feet/head atlas frames;<br>• FxSprites frames;<br>• telegraph mode;<br>• envelope (release ms, linger ms);<br>• sound ids (riser, release, tail);<br>• squint partner.<br>**Painted art:** 8 cast glyphs (512² `Texture2DArray`), a 16-frame school sprite atlas (petal, flame tongue, shard, leaf, wind streak, ink wisp, pebble, orbit dot, feather, cog, chalk dash, page, felt fluff, hail chip, spare × 2) and a 4 × 4 head/feet glyph atlas (§4.3).<br>**Fallbacks:** procedural SDF glyphs, generated in-shader, so the game runs without art. | `School` static helper in `src/fx/school.gd`; art under `assets/fx/` (asset pipeline). | — | P0 |

---

## 4. Feature table

Columns: id · feature · trigger · exact spec · Godot implementation · perf cost · priority (P0 = vertical-slice must-have).

### 4.1 Hero presence and progression

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| HER-01 | **Hero sigil: rolling wheel or struck gong, with level notches, XP arc and ult gem ★** | Always, for every living hero of every player (fog-gated) | **Geometry:** a terrain-tilted ring under the hero. The band runs r 0.82–1.05 m × hero `scale`, outside the 0.75 m selection ring so both read. Inner disc to 0.82 m at α 0.12. Draws below rings and units.<br>**Kingdom face, the "Ember Wheel":** six ivory spokes (#EDE2C8, α 0.35) from r 0.18 to 0.80; a bronze hub flame (#F08A2A, emission 0.8, flicker ±10 % at 7 Hz); the band in team colour at value ≥ 60 % with a 1 px ivory outline.<br>**Clans face, the "Gong":** a bronze band (#A8743A, highlight #D9A55E) with a 0.03 m team-colour felt stripe; two S-curve "twin winds" (#E9DDBF, α 0.3) inside.<br>**Motion:**<br>• The wheel's spokes turn with travel: θ += 0.35·Δd / 0.9 rad, where Δd is this frame's `display_pos` distance. Moving screen-right turns them clockwise. Idle drift is 0.05 rad/s.<br>• The gong rings at every foot plant (CMB-04 event): a ripple r 0.82→1.25 m, α 0.5→0, 450 ms `out_quad`. Its winds turn at 0.6 rad/s idle and 2.4 rad/s moving.<br>• Both breathe α 0.9↔1.0 at 0.5 Hz (CMB-34).<br>**Level notches:** 10 pips on the band at r 0.935 m, Ø 0.07 m, starting at screen-up and running clockwise. Lit count = level (LEVEL_PIP on/off). At level 10 the band gains a solid outer hairline. Enemies see notches too: level is public, as in WC3.<br>**XP arc (own heroes only):** r 1.08–1.12 m, from screen-up clockwise, length = `xp_ratio()`, #FFE9A8 α 0.8. Shown while the hero is selected or hovered, while Alt is held, and for 3 s after any XP gain (300 ms fade).<br>**Ult gem (own and allied only):** a 0.09 m diamond at screen-up, outside the band. Dark #3A2E22 before level 6. Afterwards it is lit (#FFF1C2) while `ultimate_ready()`, with a 120 ms HDR 1.8 sparkle every 4 s; α 0.4 while on cooldown.<br>**Night:** band emission ×1.25, staying ≤ 1.0. Sigils never bloom except inside HER-04.<br>**Own invisible hero:** the band turns dashed at α 0.5. Enemies see nothing. | New `src/fx/hero_sigils.gd`: a MultiMesh of ≤ 16, rebuilt per frame from `display_pos` like `SelectionCircles`.<br>`hero_sigil.gdshader` uses a `Texture2DArray` (wheel, gong, neutral) with procedural SDF fallbacks.<br>`INSTANCE_CUSTOM` = (level, xp_ratio or −1, spin θ, flags: gem state, reform, dashed, faction layer). | 1 draw; ≤ 16 instances; ~4 µs/frame | P0 (base, notches) / P1 (spin, gong ripples, XP arc, gem) |
| HER-02 | **Hero presence and signature flourish** | Always; the CMB-34 flourish slot | **Scale and weight:** hero defs keep `height` 2.0–2.3 m (≈ 1.3× infantry, art doc §3.1). Contact blob r 0.9 m at α 0.5 (units: 0.6 m). Rim emission 0.45 (units 0.35; cap 0.6, so nothing on a unit blooms).<br>**Nameplate** on hover or Alt: "Hedvika · 4" above the health bar. Label3D `fixed_size` 14 px, #F3E6C4, 4 px outline #120A04; the level sits in a 16 px faction badge. Fades in over 120 ms and out over 200 ms. Enemy heroes get the same plate.<br>**Signature flourish:** when idle ≥ 8 s with no enemy within 20 m, every 10–16 s. It shares CMB-34's token so two heroes never flourish in sync.<br>• **Wheel Marshal** spins the wheel-shield on her forearm (prop 360° about its axle in 900 ms, `out_back(1.3)`), then plants it: body dip sy 0.97 for 80 ms, bronze "tunk".<br>• **Firewright** blows on his match-cord: head pitch −6° for 300 ms, an ember flare at the cord tip (0.08 m, HDR 2.0, 300 ms) and 2 smoke wisps. **At night the cord tip keeps a 0.6-emission glow: he carries his own light.**<br>• **Long-Braid** whirls her braid once around her (the bronze weight orbits at r 0.7 m in 600 ms, `in_out_sine`) and catches it; sash flutter spike ×2.<br>• **Skymirror** breathes on his visor mirror (white fog patch α 0.4, 300 ms), then polishes it: a glint star sweeps across (HDR 1.8, 140 ms).<br>• **No separate prop in the GLB:** spin the placeholder weapon prop instead.<br>**Sound:** one quiet foley per flourish (World −20 dB, on screen only). | `unit_view.gd` composer layer `idle` with hero parameters from def `fx.flourish`.<br>Props hang under `body`, or under a `BoneAttachment3D` on rigged GLBs.<br>FxSprites for the flare, fog and glint. | trivial; ≤ 3 sprites per flourish | P1 |
| HER-03 | **XP trickle: motes fly to the heroes who earned them ★** | `hero_xp_gained(hero, amount, src_pos, factor, shared_with)` | **Motes:** per receiving hero, n = clamp(round(amount / 15), 1, 6). Each is 0.12 m with a white core inside a #FFE9A8 halo, HDR 1.6. They launch from the kill point at 1.0 m height, staggered 40 ms apart.<br>**Path:** a quadratic Bézier from the source to the hero's chest (`display_pos` + 0.6·h). The control point is the midpoint + 2.0 m up + ±1.0 m sideways (alternating). The end point is re-read each frame, so motes home on a moving hero. Flight takes 450–700 ms (hashed); t is eased `in_out_sine`; size goes 1→0.7 on arrival.<br>**Arrival:**<br>• the sigil XP arc eases to the new ratio (`damp` 10/s);<br>• a ring pulse r 0.9→1.15 m over 200 ms;<br>• a glass tick (UI −26 dB), for the selected hero only, ≤ 4/s.<br>**Shared XP is shown truthfully:** the motes split between the heroes that actually shared it.<br>**Creep-cap fizzle ★:** when `factor` = 0 (a hero at level ≥ 5 killing creeps), one grey mote (#9AA0A6) rises 0.6 m from the corpse and pops into 3 dots over 500 ms, with a dull tick (−22 dB). This happens only the first 3 times per hero per match, then never again: it teaches the rule and gets out of the way.<br>**HUD "pour":** the hero's XP bar (info panel and left-edge button) shows the new segment as #FFF6DE, extending from the old value to the new one in 300 ms (`out_quad`), then cooling to #E8B84A over 600 ms.<br>**Info honesty:** motes toward an enemy hero draw only if both the kill point and that hero are visible to the local player. Off-screen kills update only the HUD. | New `src/fx/xp_motes.gd`: a 32-slot MultiMesh written per frame (homing is not closed-form, and 32 transforms are trivial). XP for the same hero within 300 ms joins the flight in progress (cap 6 per hero). The HUD part lives in `hero_bar.gd`. | ≤ 32 instances; ~6 µs/frame while active | P0 (HUD pour) / P1 (motes, fizzle) |
| HER-04 | **Level-up moment, in the world and on the portrait ★** | `hero_level_up(u, new_level, levels_gained)` | Times are from the event. Anyone who can see the hero sees this.<br>**Body:** 0–60 ms squash to sy 0.92; 60–180 ms stretch to 1.12 (`out_back`); 180–400 ms back to 1.0 (`in_out_sine`).<br>**Ring burst (0 ms):** a shock ring r 0.6→3.2 m in 500 ms (`out_cubic`), α 0.9→0.<br>• Kingdom: ember-gold #FFC46B with 6 spoke-shaped rays.<br>• Clans: sun-glint #FFD27A with two echo rings at +80 and +160 ms.<br>The sigil flares to HDR 2.2 and settles over 900 ms. The new level's notch lights with a POP (0→1.4→1.0, 160 ms).<br>**Pillar (60–1100 ms):** a cylinder, r 0.6→0.9 m, 9 m tall, with a painted dry-brush streak texture scrolling up at 5 m/s. Core #FFF0C8 HDR 2.4, edge #FFC46B. α in over 80 ms, hold to 380 ms, out by 1100 ms (`in_quad`). Three motes spiral up it at 1.5 rev/s. The top 2 m fade to 0, so the pillar never slices the screen edge.<br>**Sparks (120 ms):** 18 additive motes burst up at 2–4 m/s and fall (gravity 6); life 700–900 ms.<br>**Numeral (200 ms):** the new level inside a faction badge (wheel or gong disc) above the bar. Label3D numeral `fixed_size` 34 px, #FFE6A0 with a 6 px #3A2400 outline; badge Sprite3D 46 px. Stamp: scale 1.6→1.0 in 120 ms (`in_quad`), hold, then rise 0.5 m and fade between 1100 and 1500 ms. **No words**: a numeral and an up-chevron only (no localisation, no WC3 wording).<br>**Bars:** the HP and mana bars widen to the new max with a 400 ms gold border flash (the CMB-29 bar).<br>**Light (Forward+):** pool light at priority 4, #FFD9A0, energy 3.0→0 over 900 ms, range 6 m.<br>**Portrait (HUD):**<br>• the level badge coin-flips: scale.x 1→0 in 140 ms (`in_quad`), swap the number, 0→1 in 140 ms (`out_back`);<br>• a diagonal gloss bar sweeps across the frame in 400 ms;<br>• the 3D portrait gets a vertical light wipe (a gradient overlay, 500 ms);<br>• the left-edge hero button gets the same flip and sweep.<br>**Sound:** our signature cue (audio doc §4.4 #15: harp run, golden bell, choir "ah"; 1.4 s). 2D for the owner and allies (Alerts −4 dB, priority 100); 3D for everyone else (−8 dB). The hero's level-up line (Acks) follows at +600 ms.<br>**Multi-level** (`levels_gained` > 1, e.g. from an XP tome): one pillar only; the numeral counts up one step per 120 ms with a tick; the cue is pitched +2 semitones per extra level, up to +4.<br>**Level 6 (ultimate unlocked):** the pillar is 1.5× taller, with a lower brass swell under the cue. The sigil gains its gem with a lock-in (scale 1.3→1.0, 300 ms, `out_back`). | `hero_fx.gd`; Beams (pillar); GroundZones (ring); FxSprites; a 2-slot Label3D/Sprite3D pool; `hero_bar.gd`; `ImpactLights`. | ≈ 30 sprites + 1 beam + 1 ring for 1.5 s; rare | P0 (ring, pillar, numeral, cue, portrait flip) / P1 (multi-level, level 6, light) |
| HER-05 | **Skill points, learning, ready and denial** | Unspent skill point; `skill_learned`; cooldown ends; cast refused | **Unspent point:** a "+N" pip (POP_IN) on the hero's left-edge button, bobbing ±3 px at 0.5 Hz. The command card's Learn button gets a gloss sweep every 3 s until the point is spent. There is no world effect, so nothing leaks to enemies.<br>**Learn:**<br>• the ability icon drops into its slot from −24 px (180 ms, `out_bounce`);<br>• the rank pips under it light one by one (each a 90 ms POP, 40 ms apart);<br>• the hero plays a 400 ms "taste" of that school: the cast glyph at r 0.6 m and α 0.5, without the orb;<br>• sound: a page turn (UI −12 dB) plus the school's release one-shot (−14 dB).<br>**Ready:** when a selected hero's ability comes off cooldown, the icon gets a 250 ms gloss sweep and a tick (UI −20 dB). When the ultimate is ready, the sigil gem also lights (HER-01) and a deeper chime plays (UI −14 dB), at most once per 20 s.<br>**Denial:**<br>• **Not enough mana:** the button shakes (SHAKE HUD: A 6 px, P 80 ms, T 280 ms), the mana bar flashes #FFFFFF→#4FA8FF over 200 ms, a dull fizz plays (UI −16 dB), and the hero's own "need mana" line plays at most once per 8 s (Acks).<br>• **On cooldown:** the same shake, and the cooldown sweep flashes white once.<br>• **Invalid target:** the reticle shakes (world A 0.12 m) and greys for 300 ms (ABL-02). | `command_card.gd`, `hero_bar.gd`, `hud.gd`; SpellFx for the taste. | HUD tweens only | P0 (denial, learn, "+N" pip) / P1 (ready sweeps, taste) |
| HER-06 | **Hero death: kneel, dissolve, soul spark, broken sigil** | `hero_died(hero, killer)`. Heroes leave no corpse, so this replaces CMB-30/31 for heroes. | **0–60 ms:** the CMB-30 death-beat freeze.<br>**60–410 ms:** kneel: pitch 25° forward, sy 0.85 (`out_cubic`). The weapon prop drops 0.6 m, bounces once, and stays until the dissolve ends.<br>**0 ms:** the sigil cracks into 6 segments that slide out 0.25 m and fade over 400 ms.<br>**300–1500 ms:** dissolve from the feet up (`dissolve` 0→1, `in_out_sine`) with a 0.06 m noise edge: kingdom #FFB46B HDR 1.8, clans #C8D4E8 HDR 1.6. Two motes per 50 ms rise from the edge at 1.2 m/s (life 700 ms).<br>**1500 ms, soul spark ★:** a 0.18 m star (HDR 2.5) rises from the chest to h + 1.5 m (400 ms, `out_quad`) and hangs for 200 ms.<br>• **Own hero:** the spark then streaks toward its altar at 30 m/s with a 1.2 m tail. If the altar is on screen, it lands there with a ring flash.<br>• **Enemy hero:** the spark only fades upward, so it never reveals where the enemy altar is.<br>**Global feedback:**<br>• the hero's death vocal plus a faction "hero down" sting (Alerts, 2D for the owner and allies, priority 100);<br>• the killer's side hears a short "enemy hero down" sting (2D, −6 dB);<br>• minimap ping: 3 rings, white then team colour, over 1500 ms;<br>• banner via `notification(pid, "hero_down", text)`, in faction voice: kingdom "The Oath Hall mourns: Dame Hedvika is down." · clans "Ilaya's braid is cut." Never a reworded WC3 line (ip-safety §2.2).<br>**Portrait:** desaturates over 300 ms; a crack overlay draws in over 200 ms; the revive cost and time appear on the altar's card. | `hero_fx.gd`; unit shader `dissolve` (HVF-4); FxSprites; `hero_bar.gd`; `Minimap.ping` (UI doc). | ≈ 50 sprites over 1.5 s; rare | P0 (dissolve, sigil crack, sound, ping, portrait) / P1 (soul spark) |
| HER-07 | **Revive at the altar: the altar is the progress bar ★** | `hero_revive_started(altar, hero, duration)`; `revive_progress()`; `hero_revived(hero, altar)` | **While a hero is dead:**<br>• Oath Hall: the hub flame on its floor wheel gutters (emission pulses 0.3↔0.6 at 0.4 Hz).<br>• Naming Stones: one mirror goes dark per dead hero.<br>**During revive** (p = progress):<br>• Oath Hall: the floor wheel turns at 0.2 + 2.0·p rad/s. At p = 0.25, 0.5 and 0.75 a spark shower runs along the rim (12 SPARK, HDR 2.2) with a smith's "tonk" (World −14 dB).<br>• Naming Stones: the 6 mirrors light in turn at p = k/6 (FLARE to HDR 1.6). Each casts a thin beam to the centre, which stays at α 0.4.<br>• HUD: the greyscale portrait refills with a radial sweep equal to p and shows the seconds left.<br>**Completion (`hero_revived`):**<br>• 0 ms: a ring burst at the spawn point, r 0.5→2.5 m over 400 ms.<br>• 0–300 ms: a pillar grows from the ground to 8 m (`out_cubic`); it is gone by 900 ms.<br>• 0–400 ms: the hero materialises top-down (`dissolve` 1→0, HER-06 edge colour). **The hero is targetable from the first frame and fully opaque by 400 ms.**<br>• 400 ms: landing squash (sy 0.9→1.06→1.0 over 60/120/160 ms) with a dust ring. The sigil segments fly in from 1.5 m and lock (300 ms, `out_back`, a click at −16 dB). The hero's Ready line plays (audio doc: revive = Ready). The portrait colour floods bottom-to-top in 400 ms, with a frame flash.<br>**Sound:** a rising swell (Alerts, 2D for the owner, −6 dB, priority 100). | `hero_fx.gd`; the altar `UnitView` structure branch (economy §2.3 `_animate_structure`) driven by def `fx.altar`; Beams; GroundZones. | ≤ 40 sprites; altar idle ≈ 1 µs | P0 (completion, portrait sweep) / P1 (altar dressing) |

### 4.2 Abilities: cast, target, impact

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| ABL-01 | **Spell grammar: anticipation exactly fills the cast point ★** | `ability_cast_started` → `cast_progress()` → `ability_released` / `ability_cast_cancelled` | **Phase lock:** anticipation runs on c = `cast_progress()` (sim, interpolated). The release flash spawns in the frame that processes `ability_released`, which is the tick the sim applies the effect. Nothing waits on the visuals.<br>**Anticipation kit (every spell):**<br>• **Cast glyph** under the caster: the school glyph (§5), r 0.9 m, α 0→0.7 (`out_quad` over c), rotating 30°/s, draped on the terrain.<br>• **Charge orb** at the hand or staff tip (def `fx.prop_hand`; fallback 0.85·h, in front): 0.10→0.35 m and HDR 1.2→2.5 (`in_quad` over c), in the school's core/mid colours.<br>• **Pose:** lean back 7° and rise 0.08 m over c (`in_out_sine`). On release, snap forward 10° (`out_back(1.3)`, 120 ms) and settle over 250 ms. A rigged `cast` clip is seeked so its baked `cast_release` marker lands at c = 1, the same method as CMB-16.<br>• **School telegraph rhythm** (§5): converge, fuse, 3 steps, grow, spin-up, implode, wind-up or ring alignment. Each finishes exactly at c = 1, so opponents can learn when the spell will fire.<br>• **Faction dialect:** kingdom casters add 2 bronze sparks per 200 ms; clans casters add a mirror glint every 250 ms.<br>**Short cast points:** below 150 ms there is no build-up. A 60 ms "flick" (orb pop + glyph flash) plays on the release frame, never before it.<br>**Sound:** the school riser starts at `max(0, riser_len − cast_point)` into the file (`AudioStreamPlayer3D.play(from_position)`), so its peak lands on release. The release hit plays at release.<br>**Cancel:** the glyph shatters into 6 motes and fades in 150 ms; the orb implodes; a fizz plays (−18 dB). The sim decides any refund; the visual is the same either way.<br>**Fog:** enemy anticipation shows only while the caster is visible. A missile or zone that enters vision appears when it does. | `spell_fx.gd` (HVF-1); `Unit.cast_progress()`; `unit_view.gd` composer layer `cast`; GroundZones `GLYPH`; the orb is one FxSprites slot rewritten per frame. | ≈ 15 µs per cast; ≤ 12 live casts | P0 |
| ABL-02 | **Targeting reticles: truthful, terrain-draped, shape-coded** | Targeting mode for point or area abilities; hovering a no-target AoE button (or holding its hotkey with the "quick-cast preview" setting) | **Shapes.** Every radius and width is the gameplay value, measured to the outer edge (±2 %).<br>• **Circle** (Naphtha Flask 3 m, Far Mirror 10/14/18 m, Swallowed Sun 9 m): edge line 0.08 m (≥ 2 px) in school mid; fill α 0.12; the school glyph at 35 % of the radius, rotating 20°/s.<br>• **Donut** (a minimum range, e.g. the Grand Bombard's fire band 3–17 m): the forbidden centre is hatched grey #9AA0A6 at 45°.<br>• **Line** (Sunglint 11 × 1.6 m; later Burning Lens 12 × 1.5 m): a rectangle from the caster's edge, with chevrons scrolling forward at 3 m/s.<br>• **Cone** (later Threshing Sweep, 5 m and 90°): a wedge with 3 arc ticks.<br>• **Self-centred** (Brace the Wheel 4/5/6 m, the Wagon Ring 11 m): the radius around the caster, edge only, α 0.5.<br>• **Unit target:** hovering a valid target snaps a lock ring onto it (r = its selection radius × 1.15; scale 1.25→1.0 in 100 ms, `out_back`) with 4 inward notches rotating 45°/s. An invalid target (e.g. Linden Balm on a mechanical unit) gets a grey slashed ring, and the tooltip gives the reason.<br>**Validity:** valid areas use the school colour. Invalid ground is grey with 45° hatching, which is colour-blind safe.<br>**Feel:** the reticle follows the cursor with no smoothing (precision). Its glyph lags behind with `damp` 25/s, for weight. On confirm the reticle stamps (scale 1.06→1.0, 90 ms), and its edge stays 250 ms as the order marker (CMB-08 family). | New `src/input/ability_targeting.gd`, owned by `CommandInput`; GroundZones `CIRCLE` / `DONUT` / `RECT` / `CONE`; terrain height texture (HVF-2). | 1–2 instances; < 0.05 ms | P0 |
| ABL-03 | **Range ring, walk-to ghost, queued casts** | Targeting mode | **Range ring:** a dashed ring around the caster at range + caster radius (edge-to-edge semantics). 24 dashes, α 0.5, school mid, rotating 6°/s.<br>**Out of range:** the reticle drops to α 0.6. A dashed walk-to line runs from the caster to the point where it will stop and cast (where the straight path meets the range ring), with 3 chevrons sliding along it at 2 m/s. The slice does not need path-correct lines.<br>**Shift-queued casts:** each queued target gets a small numbered school glyph (1, 2, 3; 0.5 m), linked by the CMB-11 waypoint lines. | `ability_targeting.gd`; GroundZones `EDGE_DASHED`; the CMB-11 line renderer. | trivial | P0 (range ring) / P1 (walk-to line, queue glyphs) |
| ABL-04 | **Outcome preview: show the result before the click ★** | Targeting hover; updates when the cursor moves ≥ 0.25 m or the target changes | **Affected units** inside the reticle, counting only valid target types:<br>• enemies: a 2-blink outline pulse (#FF6A4A) and a notched under-ring;<br>• allies who will be helped: a soft green under-ring (#7CFF8A, α 0.35);<br>• immune units: a grey slashed ring.<br>**Per-ability previews:**<br>• **Linden Balm:** the CMB-29 heal-preview segment on the target's bar (capped at its missing HP), plus the 2.5 m splash ring around the target.<br>• **Braid Lash:** a dashed arrow from the target, 3 m toward Long-Braid (1.5 m for heroes), ending in a ghost footprint.<br>• **Fuse Mark:** the 2.5 m blast ring around the hovered target.<br>• **Grand Bombard:** its 3 m and 17 m fire-range rings around the placement point.<br>• **Homeward Horn / Felt:** the 6 m pickup ring, and a "will travel" feet glyph on each unit that would go (ITM-04).<br>• **Bowl Over** (later): a translucent pot silhouette over the target.<br>**Honesty:** previews run the same sim query the cast will run (`World.query_radius` with the ability's filter). Hidden units are never highlighted. | `ability_targeting.gd` queries ≤ 60 units per hover update. StatusFx feet layer for the under-rings; Beams and GroundZones for arrows and rings. | ≈ 0.05 ms per update | P1 |
| ABL-05 | **Spell missiles and beams** | `ability_released` with a missile (sim `Projectile`) or an instant line | **Missiles** are sim projectiles; the visuals hang off them (their `model` and `fx.trail`). Trails are emitted by accumulated age, not per frame: spawn k = floor(age / interval) − already_spawned, so 30 Hz and 240 Hz leave the same trail.<br>**Trails by school:**<br>• **Ember** (Naphtha Flask): a clay flask tumbling at 2 rev/s with a fuse spark at its neck (HDR 2.2); a smoke puff every 45 ms (#6E6862, α 0.4, 0.15→0.4 m, 600 ms) and a spark every 90 ms.<br>• **Hearth:** a petal ribbon (2 petals per 60 ms, falling 0.4 m/s, 800 ms).<br>• **Gale** (Skymirror's glint bolt, Hail-Hawk shots): a 0.6 m white streak and 1 dust mote per 80 ms.<br>• **Gloam:** ink wisps that sink.<br>• **Stone:** a tumbling rock with dust.<br>• **Rime:** shard sparkle.<br>• **Orrery:** 2 dots orbiting the missile at 0.15 m, 6 rev/s.<br>**Instant lines** (Sunglint, later Burning Lens): a beam strip from the hand to the line's end, cylindrically billboarded. The bright core (#FFFFFF HDR 2.5) is 30 % of the width; the full gameplay width shows at α 0.35 in school mid. Life 180 ms (in over 30 ms, out over 150 ms `out_quad`). The ground keeps a scorch strip **of the exact gameplay width** for 1.2 s (α 0.3→0).<br>**Impact:** the school's release burst (§5) at the impact point, sized to the effect radius. A single-target burst stays within 1.5× the target's ring radius. | `spell_fx.gd`; `projectile.gd` visual children (combat doc); Beams (`beam.gdshader`); FxSprites. | ≤ 40 sprites per missile flight; a beam is 1 instance | P0 |
| ABL-06 | **Ground zones: truthful radii, allegiance edges, danger first ★** | `zone_created(...)` / `zone_ended` | **Truthful radius:** the edge sits at the gameplay radius (±2 %), checked by a test (§10). Only vertical elements (rising smoke, columns) go past it.<br>**Edge** (0.12 m, school mid, α 0.85), coded by allegiance to the local player:<br>• **smooth** for own and allied zones;<br>• **notched** (24 inward teeth, 0.10 m deep) for hostile zones;<br>• **dashed** (16 dashes) for creep zones.<br>The shape carries the allegiance, so it survives colour blindness.<br>**Fill:** α ≤ 0.35, with the school pattern in the shader: ember flowing flame noise; gloam darkening; hearth drifting petal shadows; gale swirl streaks; stone cracks; verdant grass flecks; rime frost crystals; orrery rotating ticks.<br>**Vertical layer:** school emitters sit on a donut inside the edge (economy rule 3), so units in the zone stay visible. Naphtha fire: 10 flame tongues (StreamFx, 0.3–0.5 m) on a ring at 0.6–0.9 r, plus 4 inside; 2 embers per second.<br>**Expiry warning:** the edge blinks twice (2 Hz) during the last 1000 ms; then the fill fades over 400 ms.<br>**Danger first:** Busy and Brawl cut the cosmetic emitters to ×0.5 and ×0.25. Edges and fills are **never** throttled.<br>**Sound:** a zone loop (Spells −14 dB, the 3 nearest). | New `src/fx/ground_zones.gd` (HVF-2) modes `FILL_*` and `EDGE_*`; StreamFx for fire; `Audio.loop_3d`. | 1 draw for all zones; ≤ 14 stream instances per fire zone | P0 |
| ABL-07 | **Diegetic timers instead of cast bars ★** | Any effect lasting ≥ 2 s that matters to either player; any delayed or channelled effect | **No floating cast bars.** Remaining time is drawn on the thing itself:<br>• **Fuse Mark (4 s):** a glowing cord loops the target at its ring radius. A spark (0.1 m, HDR 2.4) runs once around it in exactly 4 s, leaving the cord burnt black behind it; the hiss rises 2 semitones over the fuse. If the target dies early, the cord snaps and the blast plays at once where it fell.<br>• **Channels and cast times** (Homeward Horn, Homeward Felt, later Grandmother's Tale at 1 s): an arc at the caster's feet (r = the sigil band) fills clockwise with `channel_progress()`.<br>• **Grand Bombard** (25 s): a fuse ring around its base (ULT-03).<br>• **Elsewhere:** stun stars fall away and root coils unwind (STS-03); the summon life ring (SUM-01); Brace the Wheel's shield rim cools (§6); zone edges blink (ABL-06); the eclipse corona thins (ULT-05); the Tall Grass ring thins (ULT-04).<br>**Rule:** timers are drawn from sim readers (`buff_remaining`, `channel_progress`, `life_ratio`), never from a local clock, so they cannot drift from the truth. Effects shorter than 2 s need no timer. | GroundZones `TIMER_ARC` and `FUSE_RING`; StatusFx; SpellFx. | trivial | P0 (Fuse Mark, channel arc, bombard fuse) / P1 (the rest) |

### 4.3 Buffs, debuffs and status

The head and feet glyph atlas (4 × 4) has these frames:

| Row | Frames |
|---|---|
| 1 | stun star, z, !, ‼ |
| 2 | …, eye, sun-star, moon-star |
| 3 | padlock, lens crosshair, iron hook, plus |
| 4 | wheel spokes, flame ring, steam curl, clock ticks |

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| STS-01 | **Status grammar: feet = buffs, body = afflictions, head = control** | `buff_applied` / `buff_refreshed` / `buff_removed`; per frame for units with statuses | **Three layers:**<br>• **Feet:** beneficial auras and buffs, as glyphs inside the selection-ring radius × 0.85, α ≤ 0.4.<br>• **Body:** harmful states that change how the unit performs (burn, frost, slow, char, blind film), as unit-shader overlays plus up to 3 attached sprite streams.<br>• **Head:** control states, one glyph slot at the unit top + 0.35 m (above the health bar, + 6 px), 0.45 m and never under 18 px.<br>**Head priority** (only one shows; ties go to the longest remaining): hex > stun > sleep > root > blind > taunted > marked > detected-eye.<br>**Caps per unit:**<br>• 1 feet glyph (the strongest aura); each extra aura adds a 0.04 m pip, max 3;<br>• 2 body overlays;<br>• 1 head glyph.<br>**Apply:** a POP (0→1.2→1.0 over 90/80 ms) plus the status's sound. **Remove:** a 150 ms fade; a dispel instead bursts into 6 motes.<br>**HUD:** the info panel lists every buff as an icon with a radial duration sweep. Buffs get a smooth #46E07A border; debuffs get a notched #FF4B3E border (shape-coded).<br>**Public facts:** statuses show on any visible unit, as in WC3. Hidden and enemy-invisible units emit nothing. | New `src/fx/status_fx.gd` (HVF-3): feet MultiMesh (256) and head MultiMesh (512); the body layer is the unit shader (HVF-4). | 2 draws; ~1 µs per affected unit/frame | P0 |
| STS-02 | **Auras and weapon-borne buffs ★** | Aura buffs; attack, move and armour modifiers | **Aura feet glyphs** (α 0.3, rotating 15°/s):<br>• Steady Ranks: 6 ivory spokes (#EDE2C8);<br>• Incendiary Wadding: a ring of 8 flame tongues (#FF8A2A);<br>• Feast-Warmth (later): steam curls;<br>• Lucid Hours (later): clock ticks.<br>**Steady Ranks honesty:** below 40 % HP, where the regen doubles, the spokes turn 3× faster and brighten to α 0.45. A green "+" mote rises from a healing unit every 1.2 s while it is missing HP.<br>**Source radius:** a dashed aura ring (α 0.18) around the source hero, only while that hero is selected or Alt is held.<br>**Flyers:** no feet glyph (they are in the air). Two motes orbit their ground shadow instead. This mirrors WC3 M12, where flyers do not display auras.<br>**Weapon-borne tells ★:** buffs that change attacks show on the weapon or missile, not as icons.<br>• **Incendiary Wadding** lights allied ranged missiles: a flaming tip (HDR 1.8) and an ember trail (1 per 60 ms). Their hits ignite (STS-05).<br>• **Attack-speed buffs** tint the swing smear (CMB-20) and add 2 speed lines.<br>• **Move-speed buffs** leave a heel dust streak per stride (Keen Edge's crit sprint; allies inside Swallowed Sun).<br>• **Armour buffs** give the shield or body an iron-red rim (Brace the Wheel).<br>**Scale:** 100 units under an aura is 100 feet instances in 1 draw. | `status_fx.gd`; projectile visual children; `unit_view.gd` smear-tint hook; FxSprites. | 1 draw; ≤ 0.1 ms at 100 auras | P0 (feet glyphs) / P1 (weapon-borne tells, flyer motes) |
| STS-03 | **Stun stars that fall away, root coils that unwind ★** | Stun or root buff | **Stun:** chunky painted 5-point stars (0.2 m, ≥ 8 px; fill #FFF1B0, outline #3A2400, emission 1.2) orbit the head at r 0.32 m × unit scale, h + 0.15 m, 4.2 rad/s. The orbit plane wobbles ±15° at 1.3 Hz.<br>• **Count:** n = clamp(ceil(remaining × 2), 1, 6), **one star per half-second left**.<br>• **As the stun runs out, stars drop off one at a time:** each falls 0.4 m (gravity 9), spins and fades over 200 ms.<br>• **Body:** head droop (pitch 10°), sway ±6° at 0.8 Hz.<br>• **Sound on apply:** a dull bonk and a 3-note descending tin chime (Combat −12 dB, 4 per id).<br>• **Sources:** Cave Brute's stun-on-hit (slice); Hurled Chain and Cauldron Ring (later).<br>**Root:** a coil wraps the feet (r = ring radius × 0.9, 0.25 m tall, 3 turns). Braid Lash's coil is saffron braided cord (#E0A030); creep roots are vines (#3F8A3A).<br>• The coil's height shrinks with `buff_remaining`.<br>• On expiry it springs loose: 2 strands flick out over 150 ms.<br>• Sound: a rope cinch (−12 dB). | StatusFx head layer (each star is a sub-instance); the coil is one mesh in a MultiMesh with a `progress` custom value. | ≤ 7 instances per stunned unit | P0 |
| STS-04 | **Slow, frost and chaff: the body shows it is heavier** | Slow buffs | **Honest motion:** stride frequency already follows the real (slowed) sim speed. A "heavy" layer adds: bob amplitude ×0.7 and lean +3°.<br>**Each slow wears its cause's material:**<br>• **Frost slows** (Rime school; later content): rime creeps up the body from the feet to 40 % of height over 300 ms (unit shader `frost`, #DFF3FF with sparkle). A mist breath puff every 1.6 s (#E8F0F5, 0.3→0.6 m, 700 ms). A frost ring at each foot plant. On removal the rime shatters into 6 shards (200 ms, a tink at −16 dB).<br>• **Dust Veil's ambush slow** (slice): an ochre dust film (#C9A46A) with grains falling from the body.<br>• **Chaff and Grain's attack-speed slow** (later): grey husks clinging to the weapon smear.<br>**Never** a generic blue tint for every slow: the material says why the unit is slow. | Unit shader (HVF-4); StatusFx; FxSprites. | negligible | P0 (dust slow) / P1 (frost, chaff) |
| STS-05 | **Burning, blind and mark** | Burn DoT, blind, damage mark | **Burn:**<br>• 3 flame licks at hashed body points (shoulders, back): 0.25 m tongues, StreamFx with 3 instances each;<br>• 1 ember per 200 ms;<br>• char multiply 0.85 on the lower body;<br>• a refresh plays FLARE on the licks (burns do not stack visually);<br>• the end is a 400 ms smoke puff;<br>• Incendiary Wadding's burn uses 2 licks, because it is the weaker burn.<br>**Blind (Sunglint):** a 6-point mirror star sticks over the eyes (head slot `blind`, #FFD27A HDR 1.6, pulsing at 1.5 Hz). Missed attacks show CMB-23's whiff. **Moonglint variant:** silver #C8D4E8, slower pulse at 0.8 Hz.<br>**Mark (Burning Lens, later):** a lens-crosshair glyph (#FF7AC8) at the lowest head priority. The extra damage taken shows through CMB-19's "solid" tell. | StatusFx; StreamFx. | ≤ 9 stream instances per burning unit. At most 24 burning units are drawn on screen; beyond that, licks show on the 24 nearest the camera focus. | P0 |
| STS-06 | **Sleep (Zs and nightcaps) and polymorph** | Sleep buff (spell, or creep night sleep); hex | **Zs (shared with creeps):** painted lowercase "z" glyphs rise from the head:<br>• one per 900 ± 150 ms, with a per-unit phase;<br>• each rises 0.6 m over 1800 ms with a 0.08 m sine drift, growing 0.14→0.30 m (≥ 7 px);<br>• cream #F3E6C4 with a #2A2014 outline; α in over 200 ms, out over the last 500 ms;<br>• at most 3 alive per unit.<br>Body: slumped (pitch 12°, sy 0.94), breathing sy ±0.04 at 0.25 Hz.<br>**Nightcap ★ (Grandmother's Tale, later):** spell-slept units also get a knitted felt nightcap (saffron and teal stripes, #E0A030 / #2F7E7E), popping in 0→1.2→1.0 over 200 ms. When damage wakes them, the cap flies off (0.6 m arc, spin, 400 ms fade). Drowsy heroes get a slower Z (one per 1.8 s) and no cap.<br>**Polymorph (Marmot Curse, later):** 12 felt-fluff puffs (#E9DDBF) hide the mesh swap; the marmot squeaks when hit. During its last 1000 ms it shivers (x jitter 0.02 m at 20 Hz), then pops back with a reverse puff. | StatusFx head layer; a prop MultiMesh for caps (48); mesh swap in `unit_view.gd`. | ≤ 3 glyphs per sleeper | P0 (Zs) / P2 (nightcap, polymorph; their heroes are not in the slice) |
| STS-07 | **Invisibility shimmer, fade and detection** | `buff_applied(invisible)`; `invis_alpha()`; detection | **Fade:** follows the sim fade time exactly (Dust Veil 0.6 s): `invis` 0→1, `in_out_sine`.<br>**Own and allied view:** ordered dither (Bayer 4 × 4 `discard`) down to 35 % coverage, a 0.5 team-colour rim, and on Forward+ only a refractive shimmer pass (screen UV offset ×0.004 by noise flowing at 0.3 Hz). The selection ring turns dashed, the health bar drops to α 0.6, and there is no footstep dust.<br>**Enemy view:** nothing. No dust, sprites, sounds, XP motes or status glyphs.<br>**Detected** (Far Mirror rank 3, Hail-Hawks rank 3, Chalk of Seeing, Hawk Feather): the enemy invisible unit shows as a **"chalk ghost"**: 60 % dither, a dashed outline in the detector's colour (chalk #F3E6C4 for items, school mid for spells), and an eye glyph flash (head layer, 600 ms) on the frame it is revealed.<br>**Break** (an attack or cast): the fade reverses at sim speed. Dust Veil adds a 12-puff dust bloom, and its bonus hit pops like a crit (CMB-22 hold, ring and sparks; the "N!" number appears only if it really was a crit). | Unit shader `invis` and `detected` (HVF-4); `status_fx.gd`. The fog gate in `Vfx.allow` treats units invisible to the local player as not visible. | 1 extra pass on Forward+, for own invisible units only | P0 |

### 4.4 Summons

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| SUM-01 | **Summons: arrive, count down, unmake** | `summon_spawned(summon, owner, life_s)`; `life_ratio()`; expiry or death | **The summon is real from its first frame.** An arrival never hides it, delays it or makes it look untargetable.<br>**Arrivals:**<br>• **Hail-Hawks:** a glint star flashes 8 m above Skymirror (HDR 2.4, 120 ms). Each hawk dives from it to its spawn point in 350 ms (`in_quad`, so it is high and fast at first) and flares its wings (sy 0.85→1.1→1.0). Burst: 6 feathers and 4 hail chips. Sound: a hawk cry and a wind snap (Spells −8 dB).<br>• **Clockwork Halberdier** (later): 5 parts fly in from 2 m and lock with clicks (300 ms); its eye lamp lights.<br>• **Grand Bombard:** see ULT-03.<br>**Life ring:** a thin arc at the feet (r = selection radius × 1.1, 0.04 m wide), draining clockwise with `life_ratio()`; school mid, α 0.6. Flyers carry the ring on their ground shadow. Summons also get a school-coloured rim of 0.3 (`summon rim`).<br>**Last 5 s:** the ring blinks at 2 Hz and the summon dithers between 100 % and 85 % coverage at 2 Hz. This is an honest expiry warning.<br>**Unmake** (expiry or death): no corpse. A 400 ms dissolve into school motes:<br>• hawks burst into 10 feathers, 6 hail chips and 2 glints;<br>• the halberdier breaks into 8 cogs (CHUNK);<br>• the bombard becomes smoke and planks (ULT-03).<br>The rank-3 halberdier's death burst is a separate gameplay effect and gets its own zone ring. Sound: a poof (Spells −14 dB). | `spell_fx.gd`; StatusFx (life ring); unit shader `dissolve` and `summon_rim`; FxSprites. | ≤ 24 sprites per arrival | P0 |

### 4.5 Items, loot, consumables and recall

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| ITM-01 | **Loot: bouncing drop, bundle, rarity rays ★** | `item_dropped(item, item_id, from_pos, from_unit)` | **Bundles by item class** (our own shapes; no treasure chest), 0.45 m (≈ 21 px):<br>• permanent: a buckled leather satchel;<br>• charged: a small crate of corked bottles;<br>• power-up: a rune-tome floating 0.3 m up, bobbing 0.08 m at 0.6 Hz and turning 20°/s;<br>• artifact (L7+): a lacquered casket.<br>**Drop from a creep:** the bundle launches from the carrier's chest (0.6·h), away from the killer: horizontal 1.8–2.4 m/s, up 3.2 m/s, gravity 14, one turn in the air. Then 2 bounces (restitution 0.45, then 0.25), a settle roll of ±8° decaying over 300 ms, and a landing dust puff. **The arc ends exactly on the sim item's position.** If someone picks the item up mid-bounce, cut straight to ITM-02.<br>**Rarity is coded by shape first:**<br>• Tier A (L1): a star glint every 2.5–3.5 s (HDR 1.8, 140 ms).<br>• Tier B (L2–3): adds a 1.2 m vertical beam with 1 ray.<br>• Tier C (L4–6): a 2.5 m beam with 3 rays and 2 orbiting motes.<br>• Tier D (L7+): a 4 m beam with a 5-ray crown and a slow pulse.<br>Colours are secondary: A/B cream #FFF6DE, C gold #FFD27A, D rose-gold #FF9FC8. Beam cores are 0.12 m at α ≤ 0.35, so nothing behind them is hidden. The beam rises from 0 to full height in 220 ms (`out_back`) after the item lands.<br>**Chime:** pentatonic by tier: A E5, B G5, C B5 with a shimmer, D E6 plus a 3-note "find" stinger at −8 dB. 3D, World −10 dB, priority 70.<br>**Hover:** the item name (UI 14 px) and a level badge. | New `src/fx/loot_fx.gd`. Ground items are entities with a light `UnitView` branch. Bounce via a BallisticFx-style closed-form arc (economy §2.3); rays via Beams. | 1 draw for all beams; ≤ 30 ground items typical | P0 (drop, bundle, beam) / P1 (tier D crown, hover label) |
| ITM-02 | **Pickup, inventory pop, power-up absorb, full pack** | `item_picked(hero, item_id, slot)`; power-up consumed; `item_pickup_failed(hero, item, "full")` | **Pickup:**<br>• the hero dips (pitch 8°, sy 0.97, 80 ms);<br>• the bundle hops into the hero's chest (apex 0.6 m, 200 ms, scale 1→0.4);<br>• 6 sparkles at the chest (HDR 1.6, 300 ms);<br>• sound: a pouch rustle plus a class clink (buckle, bottle or chime) at −10 dB; 2D for the owner, 3D for everyone else.<br>**HUD:** the slot icon pops (0→1.15→1.0 over 90/110 ms), the slot frame flashes cream for 150 ms, and one gloss sweep passes over it. If the hero is not selected, its left-edge button shows a bag-pip pulse.<br>**Power-ups (tomes):**<br>• the tome opens in the air (two halves rotate 70° in 300 ms) and 4 page sprites flutter out;<br>• the attribute glyph (our own: a fist for STR, a feather for AGI, an eye for INT) spirals into the hero in 400 ms;<br>• a label reads "+1 STR" in STR #FF7A4A, AGI #6AE07A or INT #4FA8FF; an XP tome reads "+100 XP" in #FFE9A8 and sends real XP motes (HER-03);<br>• the HP or mana bar widens with a shimmer.<br>**Full pack:** the bundle hops 0.3 m and drops back with a thunk. The inventory frame shakes (SHAKE HUD), and the hero says a "pack's full" line (our own wording) at most once per 5 s. | `loot_fx.gd`; `hud.gd` inventory; FxSprites. | negligible | P0 (pickup, slot pop, tome) / P1 (full-pack bounce) |
| ITM-03 | **Consumables and wards** | `item_used(hero, item_id, slot, charges_left)` | **Instant heal (Linden Salve, +250 HP):** a tin opens (lid flips over 120 ms); 8 linden petals and a cream-green spiral (2 turns, 500 ms) rise from the feet. The CMB-28 heal number and CMB-29 heal segment show. Sound: a tin pop and a soft chime (−12 dB).<br>**Instant mana (Sage's Tincture, +150):** 3 drops (#4FA8FF) fall from a dropper above the head; the mana bar refills with a shimmer. Sound: a plip and a glassy tone.<br>**Heals over time that break on damage (Salt Tea, Brick-Tea Shavings):** 3 steam wisps curl at the feet for the whole duration (StreamFx; the mana version is blue-tinted). The bar shows the heal still to come as a pale preview segment that shrinks as it ticks. **If damage breaks it:** the steam snaps off, a hiss and a cup-crack tick play, and the preview segment flashes red and vanishes, so the player learns why the heal stopped.<br>**Wards:**<br>• Tin Watchman unfolds in 300 ms (3 parts), ticks quietly (own only, −26 dB) and lights an eye lamp.<br>• Hawk Feather plants with a quiver (spring ω 20, ζ 0.3).<br>• Both show their vision ring only in the placement preview and while selected.<br>**Chalk of Seeing:** the hero draws a chalk circle clockwise in 400 ms at exactly 9 m (dashed, chalk #F3E6C4). It lasts 15 s, with the ABL-06 blink at the end. Revealed units become chalk ghosts (STS-07).<br>**Charges:** the slot's charge number coin-flips over 200 ms. Using the last charge crumbles the icon into 4 pieces (300 ms). | `spell_fx.gd` item recipes; StatusFx; `hud.gd`. | negligible | P0 (salve, tincture, tea, charges) / P1 (wards, chalk) |
| ITM-04 | **Recall: Homeward Horn and Homeward Felt** | `channel_started` (3 s); `unit_teleported(u, from, to, "recall")`; cancel | **Pickup ring:** exactly 6 m around the hero, dashed, in faction colour. Each unit inside that will travel gets a "will travel" feet glyph (kingdom: a small wheel; clans: a felt swirl), updated live from the sim's `recall_candidates()`. For the clans this is the first 11 units by the sim's rule.<br>**Kingdom horn:** the hero raises the horn. Three horn blasts sound at 0, 1 and 2 s (3D, −6 dB). Anyone in range hears them, which is an honest warning. Each blast sends a sound-wave ring out from r 0.5 to 6 m in 600 ms. The feet arc (ABL-07) fills.<br>**Clans felt:** a felt carpet (1.2 × 2 m, saffron and teal, with a team-colour trim) unrolls at the feet in 400 ms. Twin-wind swirls spin up from 1 to 4 rev/s over 3 s, and a whirl sound swells.<br>**Destination:** a matching ring appears at the hall's arrival point from the first frame, visible to anyone who can see it. It pulses in sync with the horn blasts or the swirl.<br>**Departure (the teleport tick):** each unit leaves an afterimage at its old spot. The afterimage squashes (sy 1.25, XZ 0.7), then a vertical light streak (HDR 2.0) shoots up in 250 ms.<br>**Arrival (the same frame):** streaks drop in and the units pop (sy 1.2→0.9→1.0 over 60/120/160 ms) with dust rings.<br>**No unit is ever drawn in two places as "real":** the afterimage is a 250 ms ghost sprite, not the unit.<br>**Sound:** a departure whoosh rising (3D, −8 dB); an arrival thump and chime (3D at the hall, −8 dB; plus 2D at −12 dB for the owner). The owner's minimap draws a 600 ms streak from departure to arrival.<br>**Cancel:** the ring shatters into dashes and the horn sputters (or the felt flops). | `spell_fx.gd`; GroundZones; FxSprites; `Minimap` hook. | ≤ 12 streaks; rare | P0 |

### 4.6 Creep camps

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CRP-01 | **Camp life and the night cycle: yawn wave, sleep, never-sleepers, dawn stretch ★** | Camp state; `creep_sleep_changed(u, asleep, reason)` at dusk and dawn | **Day:** creeps hold CMB-05's guard ring. If the map dresses the camp with a fire, it burns with 4 flame tongues and smoke.<br>**Dusk yawn wave:** every creep starts on the sim's sleep tick; only a 0–600 ms visual offset per creep (hashed from its id) separates them.<br>1. Yawn: head up −15°, sy 1.06 over 300 ms; hold 300 ms.<br>2. **Circle once like a dog:** yaw 360° in 900 ms as 4 step-turns. Creeps with radius > 0.7 m skip this.<br>3. Settle: sy 0.85, roll 10°, pitch 8° over 400 ms (`out_cubic`).<br>Zs start 400 ms in. Only one yawn per camp is audible (−20 dB). The fire burns down to coals: 4 tongues become 1, with an ember glow (#FF7A3A, emission 0.6).<br>**Night:** Zs (STS-06) and breathing. A snore loop per camp (World −24 dB), only for the 2 camps nearest the listener.<br>**Never-sleepers** (Ancient Rootwarden; later golems): no Zs. Their eyes glow (two 0.06 m sprites, #FFE08A, emission 1.0, with a 120 ms blink every 4–7 s), and the head scans ±25° with a 6 s period. **Players can see which creep is still awake.**<br>**Dawn:** on the wake tick each creep stretches (sy 1.08, pitch −10°, 500 ms), shakes off (roll ±6°, 2 cycles in 300 ms) and stands back into the guard ring. The fire rekindles from 1 to 4 tongues over 800 ms. Per-creep offsets are again 0–600 ms. | New `src/fx/creep_fx.gd` (camp state by camp id); composer layers on creep `UnitView`s; StatusFx; StreamFx (fire). | ≤ 8 µs per visible camp; ≤ 2 snore loops | P0 (sleep pose, Zs) / P1 (yawn wave, dog circle, never-sleeper eyes, fire) / P2 (dawn stretch) |
| CRP-02 | **Wake-up startle, "!" and the camp roar** | `creep_sleep_changed(u, false, "damage" or "build")`; a creep acquires a target; `camp_aggro(camp_id, leader, target)` | **Startle** (the whole camp in the same frame, no stagger, because the sim wakes them together):<br>• the Zs pop, each bursting into 3 motes over 120 ms;<br>• a hop of 0.25 m × scale over 160 ms (up `out_quad`, down `in_quad`) with a landing squash (sy 0.92, 60 ms);<br>• the head snaps to the aggressor (CMB-06 look-at, top priority).<br>**Glyph:** a "!" over the head: 0→1.3 in 90 ms (`out_back`), →1.0 in 80 ms, hold 700 ms, fade 200 ms. Fill #FF5A3A, outline #2A0A04. **A creep woken from sleep shows "‼"** (two bangs), so "you woke them" reads differently from "they noticed you".<br>**Camp roar** (once per engagement): the leader (highest level; ties go to the lower id) rears up: head −20°, sy 1.08 over 250 ms. A shock ring spreads from the leader to the help radius (r 0→6 m, truthful) in 300 ms, α 0.4→0, warm red-orange #FF6A4A with a **dashed** edge (the creep code, ABL-06).<br>**Sound:** the family's roar (World −6 dB, priority 60, once per camp per 10 s), plus at most 2 short barks from camp mates. | `creep_fx.gd`; StatusFx head layer; GroundZones ring. | negligible | P0 |
| CRP-03 | **Leash give-up: "…", a grumble and a healing walk home** | `camp_leash(camp_id)`; creeps returning (invulnerable and regenerating, per the sim) | **Give-up beat:** each returning creep shows "…" (three dots appearing 120 ms apart; hold 900 ms; fade 200 ms; cream #F3E6C4), shakes its head (yaw ±12°, 2 cycles in 400 ms) and huffs (2 dust puffs at the snout). Sound: a grumble (World −14 dB, once per camp).<br>**Walk home:** an invulnerability shimmer (85 % dither and a pale green rim, #9BE36A at 0.3). While HP is below max, a green "+" mote rises every 400 ms (one at a time), and the bar fills. **The player can see that chasing them is pointless.**<br>**Arrival:** by day they settle back into the guard ring. At night they lie down again only if the sim puts them back to sleep (with the CRP-01 dog circle). | `creep_fx.gd`; unit shader dither and rim; StatusFx. | negligible | P1 |
| CRP-04 | **Camp cleared: stinger, summary stamp, the camp goes quiet ★** | `camp_cleared(camp_id, player_id, gold, xp, pos)` on the last kill | **Stinger:** a 1.6 s faction motif, 2D for the clearing player only (UI −8 dB, priority 70). Kingdom: a hand-bell, a rising horn third and a snare tap. Clans: a gong tap, a double frame-drum hit and a bone-flute trill. It never reuses the level-up motif.<br>**Summary stamp** (on screen only), at the camp centre + 2.4 m:<br>• "+46" with a coin glyph (#FFD34D), Label3D `fixed_size` 24 px;<br>• "+180" with an XP glyph (#FFE9A8), 20 px: the total for the player's own heroes.<br>It stamps in (scale 1.6→1.0 in 120 ms, `in_quad`) with a ground ring tap (r 0→5 m over 500 ms, soft gold #FFE6A0, α 0.4→0: "this ground is safe now"). It holds 1.4 s, then RISE_FADE. Per-creep bounty numbers (CMB-28) still play; the stamp is their sum.<br>**The camp goes quiet:** its standard or totem (map dressing) topples (80° in 500 ms, `in_quad`, dust on contact). The campfire puffs one smoke ring and goes out. The snore and fire loops stop.<br>**Minimap:** emits the event; the UI doc turns the camp marker into a hollow ring with a check notch (600 ms crossfade).<br>**Bounty coins:** every creep death spurts 3–6 COIN sprites from the corpse (economy §2.3; up 2.5–3.5 m/s) under CMB-28's "+N". | `creep_fx.gd`; a 2-slot Label3D pool; GroundZones; `Audio.play_ui`; map `camps[].dressing`. | trivial; rare | P0 (stinger, stamp) / P1 (dressing topple, coins) |

### 4.7 Ultimates

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| ULT-01 | **Ultimate frame: tint, stinger, sky marker, restraint** | `ability_cast_started` / `ability_released` for an ability with `fx.ultimate = true` | **Screen tint (owner only):** a vignette in the school's mid colour. α 0.08 at the screen edges and 0 inside 55 % of the screen radius (`smoothstep(0.55, 1.0, r)`). It draws on a CanvasLayer below the HUD.<br>• Timing: in over the cast point (or 150 ms), hold through release + 600 ms, out over 1200 ms.<br>• One tint at a time: the latest wins, with a 200 ms crossfade.<br>• **The centre of the playfield is never coloured.**<br>**Sound:**<br>• the owner hears the ultimate stinger in 2D (Alerts −6 dB, priority 95), and the Music bus ducks −4 dB for 1.5 s;<br>• everyone else who can see the caster hears it in 3D (−4 dB): an honest warning that an ultimate is coming.<br>**Sky marker:** every ultimate has one vertical element that reads at max zoom (a pillar, a ring of wheels, a dome, an eclipse disc), ≤ 9 m tall and α ≤ 0.5.<br>**Camera:** own ultimates with a slam (the Wagon Ring rising, the bombard crate landing) request 0.15 trauma from the camera doc, only within 20 m of the camera focus. Never for enemy ultimates, never for routine spells.<br>**Light:** pool priority 5 (Forward+).<br>**Truth:** the gameplay edge (ABL-06) is drawn for the whole duration. Interior fills stay at α ≤ 0.35. Units always render above the effect.<br>**Juice level 0:** no tint and no music duck. The stinger, edge and sky marker stay. | New `src/fx/screen_tint.gd`: a `ColorRect` with a vignette `canvas_item` shader, `mouse_filter` ignore, on CanvasLayer 1 (the HUD is layer 2). `Audio.duck(bus, db, ms)` (audio doc); a trauma request to the camera doc. | 1 cheap full-screen pass while active | P0 (tint, stinger, edge) / P1 (music duck, trauma) |
| ULT-02 | **The Wagon Ring (Wheel Marshal)** | Cast: 175 mana, 11 m, 7 s | **Anticipation:** she raises the wheel-shield overhead (pitch −20°, rise 0.1 m). An ivory chalk ring grows from her sigil out to 11 m over the cast point.<br>**Release:**<br>• 12 ghostly wagon wheels (Ø 1.6 m, translucent ivory α 0.45, rim #FFB46B HDR 1.6) burst up on the circumference in 250 ms (`out_back`): one every 30°, upright and tangent to the circle, with a wooden creak-thump.<br>• The wheels then roll slowly around the ring at 12°/s around its centre. Each wheel spins at ω = v / r, so it truly rolls.<br>• The fill is an ivory wash at α 0.12.<br>• Allies affected by the sim (those inside at cast) get an iron padlock feet glyph.<br>**Lethal block ★** (`lethal_prevented(unit)`):<br>• a clang spark burst on the unit (8 SPARK, HDR 2.2);<br>• the nearest wheel flashes (HDR 2.0, 120 ms);<br>• the unit's health bar shows an iron lock notch at 1 HP for as long as the ring lasts;<br>• a clang (Spells −8 dB, ≤ 4/s).<br>**Timer:** the wheels fade from α 0.45 to 0.25 over the last 1.5 s, and the edge blinks (ABL-06).<br>**End:** the wheels topple inward and dissolve into ivory dust over 500 ms. A heal ripple runs inward to each affected unit over 300 ms (+15 % of max HP; CMB-28 heal numbers).<br>**Tint:** ember-ivory #FFC46B. **Sound:** a rolling-wheel rumble loop (3D, −10 dB, 7 s) and a chain rattle; at the end, a thunk and a bell. | `spell_fx.gd` rig: a 12-instance MultiMesh of the wheel mesh (procedural fallback: a torus and 6 boxes); GroundZones; StatusFx. | 1 draw + the ring; ~10 µs/frame for 7 s | P0 |
| ULT-03 | **Grand Bombard (Firewright)** | Cast at a point within 6 m; a 25 s summon | **Anticipation (honest telegraph):**<br>• he strikes the linstock: 2 sparks per 100 ms;<br>• the placement reticle shows the 3 m and 17 m fire rings (ABL-04);<br>• a bronze-banded crate falls onto the point on a closed-form path from 6 m during the last min(400 ms, cast point), **landing exactly at c = 1**;<br>• its shadow grows under it from the start of the cast (CMB-27 style), and a whistle rises (riser aligned to land on release).<br>**Release:**<br>• the crate bursts: 10 planks (CHUNK), 4 bronze bands and a smoke ring of 10 puffs;<br>• the bombard (the Bombard Wagon mesh at 1.3×) **is there from this frame** and rises out of the crate (sy 0.8→1.08→1.0 over 250 ms);<br>• a fuse ring lies around its base (r 1.6 m), and a spark travels it once over 25 s. It is the same grammar as Fuse Mark: **a fuse is time**.<br>**Each shot:**<br>• CMB-27's launch at ×1.3: a muzzle flash (#FFC46B, HDR 3, 0.8 m, 80 ms) and a 10-sprite smoke ring;<br>• a 0.3 m recoil slide back, returning over 400 ms (a body offset only);<br>• the shell shadow and whistle (CMB-27);<br>• at impact, both splash rings flash for 300 ms at their exact radii: 1.25 m full damage (brighter) and 2.5 m half damage (dimmer).<br>**Expiry:** the crew packs up: a harmless puff of smoke and 6 planks. No shock ring and no flash, because it deals no damage and must not look as if it does.<br>**Tint:** ember #FF8A2A. **Sound:** the crate's whistle during anticipation; a crash and creak; each shot's boom (CMB-27 family, +2 dB); an expiry pop. | Rig: a crate mesh (procedural box fallback); GroundZones `FUSE_RING`; FxSprites; CMB-27 hooks. | ~30 sprites per shot, 1 shot per 2.4 s | P0 |
| ULT-04 | **Through the Tall Grass (Long-Braid)** | Cast: a 10 s self-buff | **Release:**<br>• steppe grass shoots up around her: a ring of 40 blades at r 1.2 m, 0.6 m tall, #C9B46A → #8E7A3A, rising 0→1 in 200 ms (`out_back`);<br>• the ring follows her for 10 s, the blades leaning away from her velocity (spring ω 12, ζ 0.4);<br>• a saffron wind ribbon spirals around her (2 turns, 0.9 rev/s), and her coat flare spikes.<br>**Each attack:**<br>• a crescent dust-slash sweeps exactly the 6 m × 1.5 m line behind the target (a truthful rectangle), drawn as a painted ochre crescent smear (#C9A46A, with a sun-glint edge #FFD27A HDR 1.8) that travels outward in 120 ms and fades over 300 ms;<br>• every unit hit in the line gets a small slash spark (CMB-18 slash, ×0.6);<br>• crits in the line use CMB-22's punch.<br>**Timer:** the grass ring thins from 40 blades to 10 over the 10 s (an honest countdown) and lies down at the end (200 ms).<br>**Tint:** saffron #E0A030. **Sound:** a wind gust swell and a rising bowed drone (a 10 s loop, 3D −12 dB); each line slash is a "shhk" plus a grass swish (≤ 4/s). | Rig: a 40-instance grass MultiMesh; the smear quad pool from the combat doc. | 1–2 draws; ~6 µs/frame | P0 |
| ULT-05 | **Swallowed Sun (Skymirror)** | Cast at a point within 12 m: a 9 m radius for 12 s | **Anticipation:** he raises the staff-mirror, and a reflected sunbeam climbs from the mirror to the sky above the target (a thin beam, HDR 2.0, growing with c).<br>**Release:**<br>• 7 m above the centre, an eclipse appears: a black disc (Ø 2.4 m) with a silver corona (#C8D4E8, HDR 1.6), scaling 0→1 in 400 ms (`out_back`);<br>• the ground within 9 m darkens toward night (multiply 0.45, shifted toward #3B4A80), with a truthful edge;<br>• a soft curtain rises from the edge (a cylinder, α 0.25 at the ground fading to 0 at 3 m), so the boundary reads from any angle;<br>• the sim blocks enemy vision of the area; visually, enemies see the dark dome and the disc.<br>**Inside:** enemy units get a faint grey eye-fog film (the blind visual, for their 40 % miss chance). Allied units leave heel dust streaks (+15 % move speed).<br>**Timer:** the corona thins from a full ring to a thin rim over 12 s (an honest countdown), and the edge blinks in the last second.<br>**End:** the corona flares (HDR 2.5, 150 ms), then light floods back from the centre outward in 600 ms.<br>**Tint:** gloam ink-silver. **Sound:**<br>• listeners inside the dome hear a low drone, and their ambience ducks −8 dB;<br>• a "crickets at noon" chirp bed (−18 dB);<br>• the end is a bright bell ping. | Rig: disc and corona quads (Beams); GroundZones `GLOAM_DARK`; a curtain cylinder. | 3 draws; trivial CPU | P0 |

---

## 5. The VFX language: eight schools

The brief names eight classic schools. Each gets an in-world identity, a palette, a **shape signature**, a **telegraph rhythm** (ABL-01) and a **sound signature**. A school must be recognisable by **shape and motion alone**: test it with a greyscale, colour-blind-simulated capture (§10).

| School (data id) | In-world flavour | Core / mid / edge / dark | Shape signature | Telegraph rhythm (ends exactly at release) | Release | Linger | Sound: riser → hit → tail | Slice users |
|---|---|---|---|---|---|---|---|---|
| Holy → **Hearth** (`hearth`) | Warmth, blessing, linden blossom. **Never god-beams from the sky.** | #FFF6DE HDR 2.0 / #FFC46B / #E89A7A / petals #F3E7A6 (alpha) | 6-petal rosette; soft discs; petals that **fall** | **Converge:** motes drift inward from 1.2 m and brighten (`in_quad`) | Soft bloom pop: scale 0.6→1.0 `out_back(1.3)`, 120 ms | Petals drift down, 1.2–1.8 s | Hand-bell shimmer → warm bell + air whoomph → chime tail | Linden Balm, Steady Ranks, Sunglint (day) |
| Fire → **Ember** (`ember`) | Gunpowder, naphtha, match-cord | #FFE08A HDR 2.5 / #FF8A2A HDR 1.8 / #C2341A / smoke #3E3935 | Teardrop tongues that lick **up**; sparks; smoke rings | **Fuse:** a spark hisses along; 18 Hz flicker jitter | Hard pop (`out_expo`, 80 ms), whoomp | Embers rise; zones burn 1.5–6 s; scorch (CMB-32) | Match strike / fuse hiss → whoomp + crackle burst → crackle loop | Naphtha Flask, Fuse Mark, Incendiary Wadding, Grand Bombard |
| Frost → **Rime** (`rime`) | Hoarfrost, glacier glass | #F4FBFF HDR 2.0 / #9ED4E8 / #3F7FBF / mist #E8F0F5 | Hexagonal facets; straight cracks; shards; **static and angular** | **Stop-motion crystallise:** 3 hard steps at ⅓, ⅔ and 1 of the cast point | Shatter: 8–12 shards radial at 4–6 m/s, 250 ms | Rime fades over 2 s (`in_quad`) | Ice-tension creak → glassy shatter → tinkling settle | Later content (e.g. a winter creep family) |
| Nature → **Verdant** (`verdant`) | Moss, roots, growth | #F6FFB8 HDR 1.6 / #8FD14F / #3F8A3A / petal #F7C6D9 | Spirals, leaves and vines **growing up** from the ground | **Grow:** tendrils rise from the ground (`out_quad`) and sway | Unfurl (`out_back`) | Leaves fall and sway, 1.5 s | Wood creak + rustle swell → soft woody thoonk + flute breath → rustle | Moss Shaman heal, Linden Salve |
| Storm → **Gale** (`gale`) | Wind, dust devils, **sun-lightning** (yellow-white, never blue) | #FFFFFF HDR 2.2 / #CFE4F2 / dust #C9A46A / dust shadow #B7956A | S-curve ribbons, speed streaks, triple swirl. Lightning variant: jagged #FFFFFF / #FFF27A | **Spin-up:** swirl speed ramps from 1 to 6 rev/s (`in_cubic`). Lightning has no build-up: a 60 ms double flash | Snap: streaks for 150 ms | A short swirl, 400–600 ms; fast decay | Wind swell → whip-crack gust → swirl tail. Lightning: crackle + thump | Dust Veil, Braid Lash, Hail-Hawks, Tall Grass |
| Shadow → **Gloam** (`gloam`) | Eclipse, moon, ink. Darkens instead of glowing | rim #C8D4E8 HDR 1.4 / ink #2A2244 (alpha, darkens) / #8F7BD6 / ink smoke #14111F | Crescents, eclipse discs, **inward** tendrils, negative space | **Implode:** motes are pulled in from 2 m (`in_cubic`) and local light dims | Dark pulse (darken for 120 ms), then a silver rim flash | Ink smoke sinks, 1.5 s | Inhale (reverse swell) → low thoom + air suck → whisper drone | Moonglint (night), Swallowed Sun |
| Earth → **Stone** (`stone`) | Rock, bronze, the ground itself | sparks #FFD9A0 HDR 1.6 / #A8865E / #5E4B3A / dust #B9AE9C | Blocks, radial cracks, shock rings, pebbles | **Wind-up:** the body sinks, and the ground micro-trembles (0.01 m at 25 Hz) | Slam: ring `out_cubic` over 250 ms + 6–10 chunks | Dust settles, 1–1.5 s | Low rumble → thud + crack → pebble patter | Brace the Wheel, Cave Brute stun |
| Arcane → **Orrery** (`orrery`) | Clockwork, lenses, star-charts | #FFFFFF HDR 2.2 / rose #FF7AC8 HDR 1.5 / brass #C99A45 | Concentric rings, clock ticks, orbiting dots, lens flares; **perfect geometry** | **Alignment:** 3 rings turn at 1×, −1.6× and 2.3× and **lock into alignment exactly at release** | Ting-flash: the rings expand 1→1.4 in 150 ms | Ticks fade over 800 ms | Accelerating clock ticks + glass harmonica → bright "ting" chord → ringing harmonics | Far Mirror |

**Language rules**

1. **Squint pairs are split by motion.** Hearth and Ember share warm hues: Hearth **falls** (petals) while Ember **rises** (tongues and embers), and Hearth is pale while Ember is saturated with dark smoke. Rime and Gale share cool whites: Rime is **static and angular** while Gale is **fast and curved**. Gloam is the only school that **darkens**.
2. **Value structure:** cores are ≥ 85 % value, and edges and fills are ≤ 50 %. Gloam inverts this, with a dark core and a light rim. HDR above 1 is allowed only on cores, sparks and flashes, never on fills or edges.
3. **Everything must read without bloom.** Bloom is a bonus. HDR may clamp on Compatibility (open question 6), so shape and value carry the meaning.
4. **Faction dialects** decorate any school a hero casts. Kingdom: bronze sparks, gunpowder smoke and folk-painted chunkiness. Clans: six-point mirror glints, ochre dust, silver smoke and felt fluff. Clans magic stays warm glints, dust and silver smoke (clans §2.2: no blue lightning, no fel green, no teal glow). Kingdom has no glowing holy light (kingdom §2.3); its "holy" is Hearth.
5. **Day/night can change a spell's school ★.** Sunglint is Hearth by day and Moonglint is Gloam by night, so the clock change is visible in the spell itself.
6. **Size:** release bursts match the effect radius. A single-target burst stays within 1.5× the target's ring radius. Spectacle goes **up** (pillars, curtains, discs), not out.
7. **IP:** do not reproduce WC3's signature spell looks: a golden beam from the sky onto a heal target, a swirling blue portal vortex, falling ice shards over an area, blue zigzag chain lightning, a pillar of fire from the sky, a spinning thrown hammer that stuns, a dust-ring stomp that slows, fel-green fire or a purple-black blight carpet. Generic conventions (stun stars, Zs, a level-up pillar, an "!") are fine, drawn with our shapes, timing and sounds.

---

## 6. Slice ability sheet

All anticipation runs over the sim cast point (ABL-01). The table defaults (§2.2) are 0.3 s for normal abilities and 0.5 s for ultimates, except where stated. Sound columns read riser → release → linger.

| Ability (hero) | School | Anticipation | Release (on the effect tick) | Linger / timer | Sound | Notes |
|---|---|---|---|---|---|---|
| **Linden Balm** (Wheel Marshal; unit, 8 m; heal + 2.5 m splash at 25 %) | Hearth | She presses her palm to the bronze hub of her wheel-shield; linden blossoms (#F6E7A0 petals, #9DBF5A bracts) **converge** on her hand. | A gust of 12 petals streaks from her hand to the target (a 150 ms ribbon; the heal has already landed). A rosette blooms at the target (0.6→1.4 m, `out_back(1.3)`, 120 ms). A petal ring at exactly 2.5 m washes over the splash-healed allies. CMB-28 heal numbers. | Petals drift down for 1.5 s. | Wind chime → warm bell + breathy whoomph → leaf rustle | No glowing hand and no beam from the sky (IP). |
| **Brace the Wheel** (self; taunt 4/5/6 m; +armour for 6 s) | Stone | She lifts the wheel-shield high, the body sinks (sy 0.94) and the ground micro-trembles. | She slams the rim into the ground: an iron shock ring at the exact radius (`out_cubic`, 250 ms), 8 bronze sparks and dust. Each taunted enemy's head snaps to her, and a thin iron tether flickers from it to her for 300 ms. | Her shield rim glows iron-red (#FF7A3A, HDR 1.3) for the 6 s armour buff and **cools over the last 1.5 s** (a diegetic timer). Taunted units show the iron-hook head glyph for the taunt's duration. | Low rumble → anvil-and-rim clang + thud → pebble patter; her taunt bark | Tethers are one-shot (300 ms), not permanent lines. |
| **Steady Ranks** (aura, 9 m) | Hearth | — | — | Feet spokes (STS-02); spokes turn faster below 40 % HP. | — | |
| **The Wagon Ring** (ultimate) | Hearth + Stone | See ULT-02. | | | | |
| **Naphtha Flask** (Firewright; point, 10 m; r 3 m; burns 6 s) | Ember | He shakes a clay flask and lights its fuse from the linstock; the hiss **intensifies toward release**. | The flask is lobbed (sim projectile; ABL-05 trail). On impact: 8 clay shards and a black splash of exactly 3 m that ignites at once (flame tongues 0→1 in 120 ms). | A burning zone for 6 s (ABL-06; notched edges for hostile viewers). Afterwards a scorch mark for 90 s (CMB-32). | Fuse hiss → clay smash + whoomp → crackle loop (6 s) | |
| **Fuse Mark** (unit or building, 8 m; 4 s; blast 2.5 m) | Ember | He pinches the match-cord; sparks spit. | A glowing cord whips from him to the target and loops it (ABL-07). On a building, the cord wraps the footprint. | The spark runs for 4 s. Then the blast: a flash, a smoke ring, a blast ring at exactly 2.5 m, 10 sparks and debris matching the target's material. | Whip snap → hiss rising over 4 s → boom | If the target dies first, the cord snaps and the blast plays at once where it fell. |
| **Incendiary Wadding** (aura) | Ember | — | — | Flame feet glyph; flaming allied missiles; burning victims (STS-02, STS-05). | Ignite tick on burn apply (−14 dB, ≤ 4/s) | The weapon-borne tell is the main read. |
| **Grand Bombard** (ultimate) | Ember | See ULT-03. | | | | |
| **Dust Veil** (Long-Braid; self; invisible) | Gale | She spins her braid; a dust devil **spins up**. | A 2.2 m dust devil swallows her (an ochre #C9A46A spiral ribbon and 20 grains) while she fades over 0.6 s (STS-07). | The devil drifts **in place** for 1 s and collapses. **It never follows her.** | Wind swell → gust → swirl tail. The whoosh as she fades is heard by her own side only. | Her ambush hit: STS-07 break + the STS-04 dust slow. |
| **Braid Lash** (unit, 5.5 m; pull 3 m; root) | Gale | The braid whirls twice above her head (spin-up). | The braid snaps out to the target as a stretched ribbon (120 ms) with a crack flash at its tip. The target is yanked by the sim, leaving a skid dust trail. Root coil (STS-03). | The coil unwinds over the root's duration. | Whoosh → whip crack + bronze weight clang → skid | ABL-04 shows the pull arrow before the click. |
| **Keen Edge** (passive crit) | — | — | On a crit: CMB-22, plus a saffron glint running along her sabre (HDR 1.8, 120 ms). | Heel dust streaks for 1.5 s (the honest +25 % move-speed buff). | CMB crit sweetener + a sabre "shing" | |
| **Through the Tall Grass** (ultimate) | Gale | See ULT-04. | | | | |
| **Sunglint / Moonglint** (Skymirror; line 11 × 1.6 m; blind; cast point 0.4 s) | Hearth by day / Gloam by night ★ | He tilts the staff-mirror; a hot spot grows on it (star HDR 1.2→2.4); a faint aim glint flickers along the line. Both are honest telegraphs of a real 0.4 s cast. | A beam (ABL-05). Day: core #FFFFFF, mid #FFD27A. Night: core #EEF3FF, mid #C8D4E8, at a softer HDR 1.6. A ground strip of the exact width: scorch by day, a silver frost sheen by night. | Blind glyphs on the targets (STS-05). | Glass-harmonica riser → bright "tsiing" (day) or hollow "voom" (night) → shimmer tail | |
| **Far Mirror** (reveal anywhere; 10/14/18 m; 8 s) | Orrery | He polishes and lifts the mirror; the rings align. | At the target, a bronze mirror disc (Ø 1.8 m) appears 4 m up, facing down and turning slowly. A dashed silver reveal ring at the exact radius is drawn **for the caster's team only**: it shows their own vision. The disc is visible to anyone who can see that spot. | At rank 3, detected units become chalk ghosts (STS-07). At the end, the mirror tilts away and fades with a glint. | Ticking riser → "ting" chord → ringing harmonics | |
| **Hail-Hawks** (summon) | Gale | Glint above him. | See SUM-01. | Life rings on their shadows. | Hawk cry + wind snap | |
| **Swallowed Sun** (ultimate) | Gloam | See ULT-05. | | | | |
| *Creep:* **Moss Shaman heal** | Verdant | Moss tendrils **grow** up its staff. | A leaf burst and a green spiral on the target. | Leaves fall for 1 s. | Wood creak → soft thoonk → rustle | |
| *Creep:* **Cave Brute stun-on-hit** | Stone | — (proc) | A ground knock (r 0.8 m) and STS-03 stars. | Stars fall away. | Rock thud + bonk | |
| *Creep:* **Ancient Rootwarden** (never sleeps; Pure damage) | Verdant | — | Root-vine flicks on its impacts. | — | Deep wood groan | Its night eyes (CRP-01) teach "this one is awake". |

**Later heroes** (school assignments only, so their art is planned):
- Orrery Sage: Burning Lens (Orrery + Ember scorch), Clockwork Halberdier (Orrery), Lucid Hours (Orrery feet ticks), Hour of Return (Orrery: ghost markers at each unit's marked spot and a clock-hand sweep as its timer).
- Flail Hetman: Hurled Chain (Stone), Threshing Sweep (Stone cone), Wagon-Breaker Charge (Stone line with a dust wake).
- Cauldron-Father: Bowl Over (Stone/bronze, with a pot-silhouette preview), Cauldron Ring (Stone, drawn as **gong standing-wave rings, not a dust stomp**), Feast-Warmth (Hearth steam), Under My Roof (Hearth: a translucent felt roof spans the area; a thread from each covered ally to him flashes when damage is redirected).
- Omen-Mother: Milk Blessing (Hearth, with a visible bounce path), Marmot Curse (Verdant felt fluff), Knucklebone Omen (Orrery: tumbling bones land face-up and the omen glyph appears over her head), Grandmother's Tale (Gloam lullaby + nightcaps).

---

## 7. Audio layer recipes (heroes, abilities, creeps)

Buses and priorities follow `audio-direction.md` §3.5. Every 3D sound obeys the fog and invisibility gate (§2.1). SFX use `AudioStreamRandomizer` with `random_pitch` 1.06 and ±1.5 dB; voices get no pitch variation.

| Event | Layers (level, bus) | 2D / 3D | Priority | Caps / spacing |
|---|---|---|---|---|
| Spell anticipation | School riser −10 (Spells), started at an offset so its peak lands on release | 3D | 80 | 1 per caster; skipped for cast points < 150 ms |
| Spell release | School hit + ability sweetener −4 (Spells) | 3D | 80 | 6 total; same id ≥ 50 ms apart |
| Zone / linger loop | Zone loop −14 (Spells) | 3D loop | 30 | 3 nearest |
| Cast cancelled | Fizz −18 (Spells) | 3D | 40 | – |
| Hero ability voice | The hero's line for that ability (Acks), on order acceptance, not on release | 2D | 90 | 30 % chance if the same ability was voiced within 20 s |
| Ultimate | Stinger −6 (Alerts) for the owner + Music duck −4 dB / 1.5 s; stinger −4 (Spells) for others who see the caster | 2D + 3D | 95 | 1 per cast |
| Level-up | Signature cue −4 (Alerts) for the owner and allies; −8 3D for others; the hero's level-up line (Acks) at +600 ms | 2D + 3D | 100 | 2 concurrent; multi-level pitches up |
| XP arrival | Glass tick −26 (UI), selected hero only | 2D | 20 | ≤ 4/s |
| XP fizzle | Dull tick −22 (UI) | 2D | 20 | First 3 per hero per match |
| Skill learned | Page turn −12 + school release −14 (UI) | 2D | 85 | – |
| Ability ready | Gloss tick −20; ultimate-ready chime −14 (UI) | 2D | 70 | Ultimate chime once per 20 s |
| Mana / cooldown denial | Fizz −16 (UI) + "need mana" line (Acks) | 2D | 85 | Line once per 8 s; fizz ≥ 1.5 s apart |
| Hero death | Hero death vocal (Voice) + faction "hero down" sting −2 (Alerts); "enemy hero down" sting −6 for the killer's side | 2D (owner, allies, killer side) / 3D (others) | 100 | – |
| Soul spark | Rising whistle −16 (Spells) | 3D | 40 | – |
| Revive milestones | Smith "tonk" or mirror ting −14 (World) | 3D | 30 | – |
| Revive complete | Rising swell −6 (Alerts) + Ready line (Acks) | 2D owner | 100 | – |
| Stun apply | Bonk + descending 3-note tin chime −12 (Combat) | 3D | 60 | 4 per id |
| Root / blind / burn apply | Rope cinch −12 / glint "ting" −14 / ignite tick −14 (Combat) | 3D | 60 | 4 per id, ≥ 80 ms apart |
| Invisibility fade | Whoosh −14 (Spells) | 2D own only | 60 | – |
| Detection reveal | Chalk scratch or mirror ting −12 (Spells) | 2D for the detector's owner | 70 | 1 per 2 s |
| Summon arrive / expire | Per summon −8 / poof −14 (Spells) | 3D | 70 / 40 | – |
| Item drop | Pentatonic chime by tier −10; tier D adds a find stinger −8 (World) | 3D | 70 | – |
| Item pickup | Pouch + class clink −10 (World or UI) | 2D owner / 3D others | 70 | – |
| Tome | Page flutter −10 + attribute chime −12 | 2D owner | 70 | – |
| Potion / tea | Tin pop or plip + chime −12; tea break: hiss + cup crack −12 | 3D (2D own) | 60 | – |
| Recall | Kingdom: 3 horn blasts −6. Clans: felt whirl swell −8. Then departure whoosh −8 and arrival thump + chime −8 | 3D (+2D own arrival −12) | 80 | – |
| Creep yawn / snore | Yawn −20 (1 per camp) / snore loop −24 (World) | 3D | 20 | Snores: 2 camps nearest |
| Creep startle | Yelp or grunt −14 (World) | 3D | 50 | 2 per camp |
| Camp roar | Leader roar −6 (Combat) | 3D | 60 | 1 per camp per 10 s |
| Leash give-up | Grumble −14 (World) | 3D | 30 | 1 per camp |
| Camp cleared | Faction stinger −8 (UI), clearing player only | 2D | 70 | – |

**IP:** our own level-up, camp, revive and ultimate motifs only. No WC3 sounds, lines or motifs (audio §8). Banner lines and hero lines come from the faction writers' original scripts.

---

## 8. Our own twist (what WC3 did not have)

Each twist makes a hidden number readable or gives a moment character. None of them changes an outcome.

1. **The hero sigil is a character sheet (HER-01).** The kingdom wheel turns as the hero walks; the clans gong ripples with every footstep. Ten notches show the level, an arc shows XP (own heroes only) and a gem shows that the ultimate is ready (own and allied only). WC3's hero glow was a plain ring.
2. **XP that flies honestly (HER-03).** Motes travel from the kill to each hero that actually shared the XP. At level 5 and above, creep kills fizzle a grey mote three times and then stop, so the world teaches the creep XP cap.
3. **Cast-point sync with a telegraph per school (ABL-01, §5).** Each school has its own rhythm that ends exactly on the effect tick: fuse, converge, stop-motion steps, spin-up, implosion, wind-up or ring alignment. A whole match's worth of "when does it fire?" becomes readable.
4. **Diegetic timers instead of cast bars (ABL-07).**
   - A fuse cord burns around the Fuse Mark target.
   - Stun stars fall away, one per half-second.
   - Root coils unwind.
   - Summon life rings drain.
   - The bombard sits on a 25 s fuse.
   - Brace the Wheel's shield rim cools.
   - The eclipse corona thins, and the Tall Grass ring thins.

   Every duration can be read on the battlefield.
5. **Truthful radii and allegiance edges (ABL-02, ABL-06).** Every area is drawn exactly as big as it is. Edges are smooth for friends, notched for enemies and dashed for creeps, so allegiance reads without colour.
6. **Outcome previews (ABL-04).** The heal-preview segment, the Braid Lash pull arrow, the Fuse Mark blast ring, the bombard's range rings and the recall travellers all show before you click.
7. **Weapon-borne buffs (STS-02).** Incendiary Wadding visibly sets your javelins and bolts alight. Attack and move buffs show on swings and heels, not as icons over heads.
8. **The altar is the progress bar (HER-07).** The Oath Hall floor wheel spins faster as the revive progresses; the Naming Stones mirrors light one by one.
9. **Soul spark (HER-06).** A dead hero's spark streaks home to its altar, on your side only, so the enemy altar is never revealed.
10. **Hearth, not holy (§5).** Our holy magic is warmth and linden blossom that falls, not god-beams. It is original, IP-safe and fits the diorama.
11. **Sun-lightning (§5).** Storm magic is yellow-white with ochre dust, never blue.
12. **Day/night changes a spell's school (§5).** Sunglint by day and Moonglint by night look and sound different, so the clock shows up in the spell itself.
13. **Faction-voiced banners (HER-06).** "Ilaya's braid is cut." The duelist's lore pays off when she falls.
14. **The yawn wave, the dog circle and the never-sleeper's eyes (CRP-01).** Camps go to sleep like animals. The one creep that stays awake is visible at a glance.
15. **"‼" versus "!" (CRP-02).** Waking a camp reads differently from being noticed by one.
16. **The ellipsis give-up (CRP-03).** Leashing creeps say "…", grumble and visibly heal on the way home, so you know the chase is over.
17. **Camp-cleared stamp (CRP-04).** One merged "+gold · +XP" stamp and a short faction stinger per camp, instead of number soup.
18. **Shape-coded loot (ITM-01).** Rays and crowns (0, 1, 3 or 5) mark rarity before colour does, so loot reads for colour-blind players. Bundles have their own silhouettes per item class.
19. **Interruptible tea that shows it broke (ITM-03).** The steam snaps off and the pending-heal segment flashes away when damage breaks it.
20. **Nightcaps (STS-06).** Spell-sleep pops a knitted cap on the sleeper, and it flies off when the sleeper wakes. The Zs carry the information; the cap carries the character.
21. **Signature hero flourishes (HER-02).** Each hero has one idle gesture of its own. The Firewright's match-cord stays lit at night, so he carries his own light.

---

## 9. Anti-patterns (rejected in review)

**Feel**
1. **The generic pillar.** The same gold column for level-up, revive, heal and buff. The pillar belongs to level-up and revive only; heals and buffs use their school shapes.
2. **Glow rings under everything.** Only heroes get a sigil. Buffs live at the feet as small glyphs, not as full rings.
3. **Rainbow and glitter magic.** Each school has one palette, one shape family and one rhythm. Do not mix schools inside one spell except for the documented pairs: the Wagon Ring is Hearth + Stone; Burning Lens is Orrery + Ember.
4. **Buff icon stacks over heads** (MMO clutter). Allow one head glyph at most; buffs go to the feet; the complete list lives in the HUD.
5. **Cast bars over units.** Use diegetic timers and the feet arc for channels.
6. **XP number spam.** WC3 never printed "+25 XP" on every kill, and neither do we. Motes and the bar carry XP; numbers appear only for tomes and the camp stamp.
7. **Long ceremonies on frequent events.** Potions stay under 0.6 s, pickups under 0.7 s, XP under 0.8 s.
8. **Screen shake for spells.** Allowed only as the capped trauma request for own slam ultimates near the camera focus.
9. **Full-screen flashes, white-outs, or tints that cover the centre of the playfield.** The ultimate vignette stays outside 55 % of the screen radius and under α 0.08.

**Truth and fairness**
10. **Spell visuals bigger than their hitbox,** or fills that bleed past the edge. A test enforces this.
11. **Releasing early.** A flash or sound that lands before the sim applies the effect, or anticipation that ends before the cast point does.
12. **Local-clock timers** that drift from the sim (stars, fuses, rings). Always read sim readers.
13. **Information leaks:**
    - motes, sparks or sounds from fogged or invisible units;
    - XP arcs or ult gems on enemy heroes;
    - soul sparks pointing at enemy altars;
    - marking which creep carries the item;
    - previews that highlight hidden units.
14. **Lying effects.** An expiring bombard that looks like it exploded; a summon that looks untargetable during its arrival; a revived hero that looks absent while already targetable.

**Readability**
15. **Effects over units, team colour, rings or health bars.** Fills stay at α ≤ 0.35, emitters sit on donuts and units render on top.
16. **Colour-only coding.** Allegiance, rarity, buff/debuff borders and validity always have a shape or hatching code.
17. **Throttling danger.** Cutting zone edges, CC glyphs or timers in a big fight. Cut cosmetic lingers instead.
18. **Bloom on units or sigils.** Unit and sigil emission stays ≤ 1.0, except inside the level-up flare.

**Engine**
19. **Per-effect nodes:** a `GPUParticles3D` per spell, an `OmniLight3D` per hero, a `Tween` per mote, or `Node.new()` per cast. Pool everything; transients are slot writes.
20. **`Decal` nodes** for reticles or zones. They are unsupported on Compatibility; use GroundZones.
21. **Frame-counted visuals,** `lerp(a, b, k)` per frame, or trails spawned per frame. Use age-based curves, `damp` and accumulated-time emission.
22. **Juice writing sim state,** reading `World.rng`, or emitting gameplay signals from fx code.

**IP**
23. **Copying WC3 specifics:** see §5 rule 7. Also no WC3 level-up model or sound, no "has fallen" banner wording, and no WC3 item-chest model or icons.

---

## 10. Budget and verification

**Budget** (300 units, about 150 on screen, Brawl tier, 4 heroes casting, mid-range GPU at 60 fps):

| Resource | Budget for this domain |
|---|---|
| GDScript CPU (sigils, XP motes, status, spell rigs, creep fx, targeting, hero bar) | ≤ 0.8 ms/frame on average; ≤ 1.5 ms at peak |
| Draw calls added | ≤ 17: sigils 1, GroundZones 1, feet glyphs 1, head glyphs 1, root coils 1, Beams 1 (pillars, beams and loot rays), XP motes 1, ground items ≤ 4 (one per bundle mesh), ultimate rigs ≤ 4, screen tint 1, prop caps 1 |
| Sprites | Shares FxSprites' 2560 slots; this domain uses ≤ 600 at peak |
| Label3D | ≤ 6 |
| Lights | Shared `ImpactLights` pool, with the priorities in §2.3; none on Compatibility |
| GPUParticles3D | 0 at P0/P1. P2 polish may use a pool of 8 spell emitters (Forward+), converted with `CPUParticles3D.convert_from_particles()` at 50 % amount on Compatibility |
| Audio | Spells: ≤ 6 one-shots and ≤ 3 loops (audio §3.5) |

**Verification.** Add these with the implementation; no test may be skipped.

| Check | How | Pass criterion |
|---|---|---|
| Juice never changes outcomes | `tests/unit/test_juice_determinism.gd`, extended. Scenario: 4 heroes cast every slice ability; 2 camps are cleared; a hero dies and is revived; items drop, are picked up and are used; a recall completes. Run 3600 ticks headless with `World.visuals = false`, then again with juice level 2 and `_process` deltas jittered between 1/30 and 1/240 s. | The per-tick hash of HP, mana, positions, XP, levels, inventories and buffs is identical in both runs. |
| Cast sync | `tests/unit/test_spell_sync.gd`: for each slice ability, log the frame where SpellFx spawns its release and the tick of `ability_released`. | The release spawns in the same frame that processes the signal. `cast_progress()` is 1.0 ± 0.02 at release and never reaches 1 before it. |
| Truthful radii | `tests/unit/test_truthful_radii.gd`: compare every GroundZones reticle, zone and ring instance against its ability def. | Radius and width within ±2 %. No fill sample outside the edge. |
| Diegetic timers | `tests/unit/test_diegetic_timers.gd`: sample every tick. | Stun star count = ceil(remaining × 2). Fuse spark angle = 2π × elapsed / 4 s ± 1°. Life ring = `life_ratio()` ± 0.01. |
| Refresh-rate independence | Feed 30, 60, 144 and 240 Hz deltas over the same wall time. | XP mote paths match to 1 mm for the same hero path. Sigil spin depends only on distance travelled. Star drop times match to 1 ms. Trail sprite counts are identical. |
| Information honesty | An enemy invisible hero levels up, gains XP and casts inside vision. An enemy hero dies in vision. | Invisible hero: 0 sprites, labels and sounds. The enemy soul spark has no horizontal velocity. The enemy XP arc and gem are never drawn. No preview highlights a hidden unit. |
| Caps | 12 heroes level up in the same frame; 100 units stunned (700 head instances, so the overflow rule runs); 40 burning; 30 items drop at once; 6 zones overlap. | Every cap in §2.4 holds. On head-glyph overflow, every hero and the units nearest the focus keep their glyphs. Ring buffers never grow; no errors are logged. |
| Look | `tests/playtest/hero_juice.gd`, captured on lavapipe and opengl3:<br>• level-up at +300 ms;<br>• the Wagon Ring with 2 lethal blocks;<br>• Swallowed Sun by day and by night;<br>• a Naphtha zone as own vs hostile (smooth vs notched);<br>• a creep stunned with 6 stars;<br>• a sleeping camp at night with the Rootwarden's eyes;<br>• loot tiers A–D side by side;<br>• Oath Hall revive at p = 0.5. | Art review against §5 and §2.5. Health bars and selection rings are visible in every capture. |
| Colour-blind read | Run the look captures through deuteranopia and protanopia simulation shaders. | Zone allegiance, loot tiers, buff/debuff borders, validity and the 8 schools are still told apart by shape. |
| Performance (real GPU) | `tests/playtest/bench_hero_fx.gd`: a 150 vs 150 brawl, 4 heroes casting with cooldowns zeroed, 3 zones, 60 burning units, a camp waking. | §10 budget holds; 60 fps on the mid-range target. |

---

## 11. Open questions

1. **Sprite systems.** The combat doc defines FxSprites (one-shot) and the economy doc defines BallisticFx and StreamFx. This doc uses FxSprites for one-shots, StreamFx for loops and its own GroundZones for draping. **Recommendation:** merge into one `fx_sprites` with a looped stream mode before implementation starts.
2. **Light pool.** The combat doc has 4 impact lights and the economy doc 6 fire lights; this doc adds priorities. **Recommendation:** merge them into one `LightPool` of 8, prioritised ultimate > level-up/revive > hero spell > siege > fire > crit.
3. **Cast points.** The faction docs give only Sunglint (0.4 s) and Grandmother's Tale (1 s). **Proposal:** 0.3 s default and 0.5 s for ultimates, tuned in playtest. Telegraph readability depends on these values.
4. **Item carriers.** WC3 does not mark which creep carries the drop, and neither do we. Confirm with the design lead.
5. **Ultimate readiness for allies only.** Is that right in team games? Enemies never see it.
6. **HDR on Compatibility.** Check whether emission above 1.0 survives the Compatibility 3D buffer. The design already requires everything to read without bloom.
7. **Ground items as entities.** Should they be `Unit` kind `item` (as assumed here) or a separate light store in `heroes.gd`? This is an architecture decision; it affects fog-gating and picking.
8. **Banner wording.** Final hero-down and pack-full lines go through the faction writers and the IP check (ip-safety §2.2).
9. **Recall afterimages.** These need `Unit.teleport()` to emit `unit_teleported(u, from, to, kind)`. Confirm when `heroes.gd` lands.
10. **Swallowed Sun for the enemy player.** The dark dome and disc versus how the fog renderer draws a vision-blocked area: confirm with the world and fog owners so the two do not double-darken.
11. **Rime has no slice user.** Keep its kit in data so later creeps or heroes slot in. Should one slice creep (e.g. Bog Lurker) get a frost slow to prove the school early? It would be a design change, so it needs the design lead.
