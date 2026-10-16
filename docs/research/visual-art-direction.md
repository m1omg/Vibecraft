# Visual & Art Direction Reference: WC3-feel RTS (Godot 4.7)

Research date: 2026-10-16. Scope: the visual language of Warcraft III Classic (2002) and Reforged (2020), WC3 camera, scale and UI conventions, what makes Freecraft/Stratagus-style clones and cheap indie RTS look generic, modern stylized strategy games worth borrowing from, a reference-image list, and a concrete style plan for AI-generated assets (Krea image models feeding image-to-3D generators, no rigging) in Godot.

**Fact-check pass (2026-10-16):**

- **Verified against primary or reputable sources:**
  - Camera defaults, from the `Blizzard.j` constants.
  - Zoom patch notes for 1.33.0, 1.35.0 and 1.36.1.
  - `war3map.w3e` formulas and tileset codes.
  - Player-color RGB values.
  - Upkeep tiers.
  - Didier quotes (Game Informer, Eurogamer via Blizzplanet, Parka Blogs, Wikipedia; retired Nov 2023).
  - Smithy-post quotes and the Jaina 700 to 15k polygon counts.
  - Rumble color and upper-third rules.
  - Godot 4.6 Compatibility SSAO, render modes and tonemappers.
  - Battle Aces cancellation (23 May 2025).
  - The GDC Orphea talk (Lana Bachynski, GDC 2019).
- **Corrected:**
  - Gryphon mount.
  - Frost Wyrm and Dryad wording.
  - Rumble "fussy" quote.
  - Day/night game-hour length.
  - Tileset-limit patch version.
  - Doodad scale semantics.
  - Stormgate and AoM attributions.
  - Stratagus quote.
  - Krea image minimum.
  - Removed a dead Omake Books link.

Conventions: "WC3 units" means World Editor game units (1 terrain tile = 128 units). Anything marked **(unverified)** comes from community memory, inference or a single weak source. Anything marked **(proposal)** is our own recommendation, not a WC3 fact.

---

## 0. TL;DR: the 15 rules that matter most

1. **Read from above first.** Blizzard's own account of WC3 Classic: they began aiming for realism, saw it in-game, and it looked "dumb". They then simplified colors, reduced shading, used flat colors, and made characters "bigger and bulkier so they read from that top-down camera" (Samwise Didier, Game Informer 2018). This is the founding rule of the style.
2. **Exaggerate the top third of every unit.** The RTS camera mostly sees the upper third of a character (Warcraft Rumble art team). Put the identity there: helmet, shoulders, weapon head, banner, roof.
3. **Use one or two major color areas per unit, plus team color.** Rumble rule: most minis have one or two major color areas so players can identify them quickly.
4. **Make silhouettes and shapes oversized and simple.** Didier: "bigger shapes, not as much little dots", and characters "a little bit bigger and over-proportioned". House rules attributed to him: "Bigger is ALWAYS better" and "one-handed weapons should be (at least) as big as two-handed weapons."
5. **Never let size hurt readability.** Reforged first modeled the Frost Wyrm with a "realistic (aka massive) wingspan", but several of them "obscured view of everything beneath them", so the artists had to balance "winged majesty and visual clarity". It also "reduces the focus of the spear" on the Dryad so players can take in the whole unit. In Classic, the Gryphon's mount half was made "much more prominent" to keep the unit unambiguous in battle; Reforged rebalanced it toward the rider.
6. **Paint the lighting into the texture, and keep scene lighting soft.** WC3 Classic textures carry painted light: a top-lit gradient, painted AO and painted metal highlights. Real-time lighting is low-contrast. Avoid PBR gloss: Reforged was criticized because shiny plate made grouped Footmen and Knights "blend together and lose silhouettes".
7. **Keep the environment quieter than the units.** Use lower saturation, a narrower value range and less detail on terrain. Riot's Summoner's Rift update stated this as "clamping value ranges" and "reducing character occlusion".
8. **Use the WC3 camera:** distance 1650, angle of attack 304° (that is, pitch -56°), FOV 70 (likely horizontal at 4:3), far Z 5000. Reforged added an optional zoom-out, with presets up to 2250. See §2 for Godot values.
9. **Compress scale the RTS way.** Buildings are only 2 to 4 tiles wide and a few units tall, and trees tower over units. Heroes are visibly larger than regular units.
10. **Lay out the UI WC3-style, structurally.** Bottom console: minimap (left), portrait plus unit info (center), 4×3 command card (right). Top bar: menus (left), day/night clock (center), gold/lumber/food/upkeep (right). Draw our own ornament; never copy WC3 frame art.
11. **Make terrain painterly, not a grid.** Blend natural tiles in an ordered ladder (cracked dirt, dirt, grassy dirt, grass, thick grass). Use cliff levels of 128 units, ramps, and dense doodad clusters at transitions. Add our twist: a world-space macro-tint plus moving cloud shadows.
12. **Use one lighting model for everything.** Use wrap-Lambert or a 2–3 band soft toon ramp, no specular, roughness 1, metallic 0. Keep the key-to-ambient ratio around 2:1 to 2.5:1. Grade per biome with a 3D LUT. Glow is for emissive VFX only.
13. **Normalize AI assets after generation.** Remap textures to the palette, clamp saturation per asset class, add a world-space vertical gradient in the shader, decimate to budget and match texel density. AI assets that skip this read as an "asset flip".
14. **Never put IP names in prompts** ("Warcraft", "Blizzard", "Samwise", "Lordaeron"). Describe the qualities instead (chunky heroic proportions, hand-painted, top-down 3/4).
15. **Our fresh twist (proposal):** "Storm-lit hand-painted heroic diorama". This means WC3 forms with modern atmosphere: drifting cloud shadows, wind-swayed foliage, golden-hour key light, team-color rim and rune glow, a biome-corruption spread effect, and procedural "toy-like" squash-and-stretch motion that turns the no-rigging limit into a signature.

---

## 1. What defines the look

### 1.1 Warcraft III Classic (2002)

**How the style was found (primary-source quotes, Game Informer 2018 concept-art feature):**
- "The first thing everyone wanted to do was make Warcraft III more realistic." Then: "we saw it in game, and we were like 'Everything looks dumb.'"
- "So we started making the colors simpler, decreasing the shading, adding flat colors."
- "We scaled the characters back up and made them bigger and bulkier so they read from that top-down camera."
- The camera was first tried close and behind the heroes, then "we kept slowly nudging the camera back up". In 3D, artists could no longer touch up individual pixels, so the style had to be simplified further.

**Visual characteristics (observational synthesis, consistent with sources):**

| Trait | What it looks like | Why it works top-down |
|---|---|---|
| Chunky heroic proportions | Head about 1/4 to 1/5 of body height. Hands, forearms, shoulder pads, weapon heads and boots are 1.5–2× realistic size. Legs are short and thick, torsos broad, waists tight. | From 56° down, the camera foreshortens legs and sees head and shoulders, so the mass belongs where the camera looks. |
| Oversized props | Weapons as big as or bigger than the torso (Didier's rule above). Mauls, librams and shoulder pads are signature reads (Reforged kept Paladin "imposing shoulder pads, towering war mauls and bulky librams"). | The weapon is often the only distinguishing shape at about 40 px unit height. |
| Hand-painted diffuse textures | Low-res (community reports say about 256×256 per model) painted in Photoshop. Shading, AO, highlights and metal shine are painted into the color map. There are no normal or spec maps in practice. | Detail is "expressed through textures" on simple geometry, and stays readable under any lighting. |
| Low poly | The community reports about 1,500 triangles as the practical cap for classic models (unverified). Blizzard says Jaina went from about 700 polys (Classic) to 15,000 (Reforged). | Big planar shapes make silhouettes crisp. |
| Saturated, warm-biased palette | Strong hue identity per faction: humans blue/white/gold, orcs red/brown/green skin, undead purple/teal/bone, night elves violet/teal/silver (observational). Terrain is mid-value and less saturated. | Units pop against terrain by both hue and saturation. |
| Team color | Player color fills cloth areas, banners, shoulder trim and roof flags. In-engine it is a solid color shown through alpha-masked texture regions, plus a soft "team glow" under some units (unverified detail). | It identifies ownership instantly even when unit type is unclear. |
| Lighting | Day/night "DNC" light models per tileset. The terrain and unit light emitters are white by day and shift to blue at night (unverified: the cited Hive thread only says modified DNC models make "the nights are darker"). Contrast is low, with painted shading carrying form. Units have soft blob shadows, and buildings have shadow decals (unverified detail). | Even lighting keeps painted textures as authored. Night is readable because it is tinted blue, not darkened to black. |
| VFX | Additive, saturated particle sprites and ribbon trails, chunky and short-lived, with emissive colors (green fel, blue frost, orange fire). | They read through any background. |

**Blizzard art rules (attributed to Didier, via a review of his WoW TCG art book):** "Less is NEVER more", "Bigger is ALWAYS better", "All one-handed weapons should be (at least) as big as two-handed weapons", "If all else fails, add skulls and spikes and paint it red". His retirement note (2023) advised "always draw big shoulder pads" (GameSpot). Wikipedia summarizes his aim as "over-the-top, over-proportioned, and really colorful". In the StarCraft II Eurogamer interview he said that because "all the art … is going to be viewed in the top-down, three-quarter view", they focus on silhouettes from that angle and keep "bigger shapes, not as much little dots".

### 1.2 Warcraft III Reforged (2020): what changed and what to learn

- **Intent:** units slightly "overbuilt" so they are easier to read from above (lead producer Pete Stilwell, Game Informer 2018). Blizzard made several Orc model versions with altered proportions because "a model that worked in third person for WOW will look different in a top-down RTS".
- **Material choice:** "stylized colors and proportions, but realistic flesh, clothing, and metal textures" (Blizzard Orc smithy post). Polygon counts rose about 20× (Jaina 700 to 15k).
- **Readability fixes made during production:** Frost Wyrm's initially "realistic (aka massive)" wingspan was balanced against "visual clarity" because grouped wyrms obscured the battlefield. Less focus on the Dryad's spear so the whole unit reads. Gryphon Rider: Classic's mount was "much more prominent" for clarity; Reforged gave the rider more visible detail. Kel'Thuzad's details added "without detracting from visual legibility". Shaman: "balance the number of bones and other details against the need for an instantly recognizable silhouette".
- **Criticisms (lessons for us):**
  - The art leaned toward realism and a cinematic look. Forum posters reacting to the 2018 pre-release screenshots complained of "unnecessary realism". The Hive recap of Blizzard's Q&A says the team moved from a "more cartoony look" to "a grittier look". The Windows Central article could not be read to confirm its part.
  - Glossy armor made grouped units merge and shift color with reflections (Blizzard forums).
  - Environments were called "hazy and gray" and desaturated, while other screenshots were called too bright.
  - Blizzard acknowledged that colors and shading differed from the original and promised a patch (PC Games Insider).
  - Original Tauren read better because they were darker and recognizable from a distance.
- **Takeaway:** realistic materials plus WC3 proportions make an uncanny middle. **Stay painterly.** If we want "grit", paint it in (chips, scratches as color strokes) rather than simulate it with PBR.

### 1.3 Why this reads well top-down (design principles)

1. **Upper-third identity.** The camera sees the head, shoulders, back and weapon top. Design from a 56° overhead thumbnail first, not a front view (Rumble: "the top-down camera mostly shows the upper third").
2. **Color blocking.** Use 1–2 big local colors plus team color plus 1 accent (metal or skin). Rumble: "Most of our minis have 1-2 major color break-ups", and "We had to make sure there wasn't a lot of material breakups" (art director Jeremy Collins, PocketGamer.biz).
3. **Value grouping.** Keep three value masses per unit: dark (legs and base), mid (body), light (shoulders, head, weapon). A vertical gradient (darker low, lighter high) separates objects from the ground. A Polycount critique recommends vertical gradients so "trees stand out from the ground".
4. **Exaggerated, held poses and broad motion.** Rumble's senior animator: clear silhouettes, exaggerated poses and broad movements help players identify units at a glance.
5. **Environment as stage, not subject.** Riot's Summoner's Rift update put "Clarity and Readability" first and clamped environment value ranges.

### 1.4 Tilesets and how WC3 maps are composed

**Tileset codes in the map format** (HiveWE wiki): A Ashenvale, B Barrens, C Felwood, D Dungeon, F Lordaeron Fall, G Underground, L Lordaeron Summer, N Northrend, Q Village Fall, V Village, W Lordaeron Winter, X Dalaran, Y Cityscape, Z Sunken Ruins, I Icecrown, J Dalaran Ruins, O Outland, K Black Citadel.

**Biome mood per tileset** (observational, from memory of the game; use as mood targets, not facts):

| Tileset | Palette mood | Signature doodads | Our original analog (proposal) |
|---|---|---|---|
| Lordaeron Summer | Fresh green grass, warm brown dirt, gray cobble roads, blue water | Round deciduous trees, fences, haystacks, rocks | "Greenvale": golden-green meadows, ochre roads, mossy standing stones |
| Lordaeron Fall | Orange/ochre foliage, olive grass | Autumn trees, leaf litter | "Emberwood": copper and rust canopy, violet shadows |
| Lordaeron Winter / Northrend | Snow white-blue, dark pines, ice | Pines, icicles, ice cliffs | "Frostmarch": blue-white, teal ice, warm torchlight accents |
| Ashenvale | Deep blue-green dusk forest, violet tints, moss | Giant twisted trees, glowing plants | "Gloamwood": indigo shade, bioluminescent cyan/magenta flora |
| Barrens | Orange-red dust, dry grass, rock mesas | Sparse flat-top trees, bones, spikes | "Sunscar Steppe": terracotta earth, bleached grass, sky-blue contrast |
| Felwood | Sickly green and purple corruption | Dead trees, toxic pools | "Blightmire": our corruption biome (also the spreading effect) |
| Dalaran / Cityscape / Village | Marble, cobble, purple roofs | Lamp posts, crates, carts | Town biomes, used later |
| Sunken Ruins | Teal water, algae, ancient stone | Ruined columns, coral | Later |
| Outland / Black Citadel | Red rock, purple sky, fel green | Spikes, chains, lava | Later |

**Terrain system facts** (HiveWE wiki on `war3map.w3e`, plus Hive tutorials):
- **Grid:** 128 game units per tile. Data is stored per tile corner ("tilepoint"), so a 256×256 map has 257×257 tilepoints.
- **Height:** final ground height = `(ground_height - 8192 + (layer - 2) * 512) / 4`. So **one cliff level = 512/4 = 128 units**, the same as one tile width.
- **Water:** water level = `(water_level - 8192)/4 - 89.6`.
- **Ramps:** a tilepoint flag `0x0010` marks a ramp between two layers.
- **Limits:** 4-bit ground texture index, so 16 ground textures per map. Reforged raised the tileset limit "from 16 to 64": the notes body says Version 2.0.3 (Build 23101), although the forum thread is titled 2.0.4. Up to 15 cliff types, cliff variation 0–7, 5-bit ground variation. Cliff models are a fixed kit selected by the corner height pattern (the count of 94 models is unverified).
- **Tile textures** are 256×256 or 512×256, according to a Hive answer. The answer does not say what the extra half holds; "extra variations" is unverified. They are blended in a fixed per-tileset order, where later textures overlap earlier ones. The exact layout is a 4×4 grid of transition masks plus variations (unverified).
- **Natural blending ladder** (Hive advanced terraining tutorial): "Cracked Dirt -> Dirt -> Grassy Dirt -> Grass -> Thick Grass", ordered in the tileset so transitions are not sharp. Shores use dirt and grassy dirt near water.
- **Doodads:** most Blizzard doodads have an editor minimum scale of 0.80 and maximum of 1.20 (Hive tutorial). These are limits on how far a placed doodad can be scaled, not a confirmed random-scale default. Random rotation and per-variation tinting (RGB 0–255) are unverified. Place rocks, shrubs and a few trees on cliff edges. Place river rushes, rocks, shrubs and lily pads along shores.
- **Fog:** terrain fog with start 0 to avoid a sharp boundary.

**How a WC3 melee map is composed (observational):**
- **Macro:** start locations on mid or high ground, each with gold mine plus tree line. Expansions sit on lower ground. Creep camps sit in pockets near paths. Ramps (usually 2–3 tiles wide) are the choke points between cliff levels. The map edge is dense tree walls or cliffs, never a void.
- **Meso:** roads (cobble or dirt) trace main paths. Grass-to-dirt transitions are wide and ragged, never hard tile edges. Cliffs come in 1–2 level steps with rock clusters at the base. Water sits in low basins with shallow (walkable) and deep bands.
- **Micro:** doodad clusters of 3–7 objects (rock plus shrub plus grass tuft or flower). Fences, ruins and signs hint at a lived-in world. Tree lines are irregular with 2–3 tree variations. Our proposal: ±20% scale jitter, matching the 0.8–1.2 editor scale range.
- **Hierarchy:** units are the most saturated, buildings next, doodads and trees mid, terrain least saturated.

---

## 2. Camera parameters

| Field | WC3 default | Confidence / note | Godot 4.7 equivalent (proposal: 1 m = 64 WC3 units, so 1 tile = 2 m and 1 cliff level = 2 m) |
|---|---|---|---|
| Target distance | **1650** | Verified: `Blizzard.j` constant `bj_CAMERA_DEFAULT_DISTANCE = 1650`; Hive Workshop "standard value of 1650" | 25.8 m from look-at point |
| Angle of attack | **304°** | Verified: `bj_CAMERA_DEFAULT_AOA = 304`; Hive: "304 degrees is the standard game camera AoA". The PCGW tool listing's 300 is wrong. | Camera pitch = 304 - 360 = **-56°** (`rotation_degrees.x = -56`) |
| Field of view | **70** | Verified: `bj_CAMERA_DEFAULT_FOV = 70`. The axis is not documented. | See below |
| Far Z | **5000** (max 10,000) | Verified: `bj_CAMERA_DEFAULT_FARZ = 5000` (`bj_CAMERA_MIN_FARZ = 100`); Hive says the max is 10,000 | `far = 80` m (5000/64 = 78 m) |
| Rotation | 90 (map "north" is screen-up) | Verified: `bj_CAMERA_DEFAULT_ROTATION = 90` | Yaw 0, camera looks toward -Z |
| Roll / Z offset | 0 / 0 | Roll verified (`bj_CAMERA_DEFAULT_ROLL = 0`); Z offset 0 is a Hive example value | |
| Near Z | about 16 (unverified) | | `near = 0.3` m |
| Zoom | Classic: fixed default view (wheel zoom-in only, unverified). Reforged 1.33.0: optional mouse-wheel zoom with "Default zoom and maximum zoom" sliders, Page Up/Down, F5 resets. 1.35.0 added zoom levels **1750, 2100, 2250**. 1.36.1 allows granular values (for example 1933). | Blizzard patch notes | Zoom range **1650 to 2250**, that is 25.8 to 35.2 m. Optional close zoom to about 1200 for screenshots. |

**FOV axis:** with pitch -56° and a vertical FOV of 70°, the bottom frustum edge would tilt past straight down. That is implausible, so 70 is most likely the **horizontal FOV at 4:3** (derived reasoning, unverified). That equals about **55.4° vertical**.

In Godot, use `keep_aspect = KEEP_HEIGHT` with `fov ≈ 55`. Widescreen then reveals more horizontally, which is what Reforged's widescreen does. At 16:9 this gives about 86° horizontal.

**Derived coverage** at 1650 / -56° / 55.4° vertical:
- Camera height about 1368 units (21.4 m), about 923 units (14.4 m) behind the target.
- Visible ground from about 151 to 2541 units ahead of the camera foot, roughly **18–19 tiles deep**.
- About **18 tiles wide** at the screen center, wider at the top (a trapezoid).
- The bottom HUD covers roughly the lower 20–25% of the screen, so the effective playfield is about 14 × 18 tiles.

Use this to size base layouts and sight radii. For example, a Footman's 1400 day sight is about 11 tiles. The warcraft.wiki.gg page lists 140/80, which appears to be in tens.

**Day/night** (Liquipedia, via search; the page could not be fetched to re-check): a full cycle is 480 s (240 s day, 240 s night). Dawn is at 06:00 and dusk at 18:00. That makes each game hour **20 s** (480 / 24). An earlier draft said 40 s; that contradicts the 480 s cycle. A Liquipedia excerpt quoted in `gameplay-mechanics.md` also says "40 real seconds" (unverified, unreconciled). Sight is lower at night. The in-game indicator has 8 ticks per day or night phase (classic.battle.net).

**Godot camera rig (proposal):**

```
CameraRig (Node3D, at look-at point on ground; pan with edge-scroll / WASD / middle-drag; clamp to map bounds minus margin)
 └─ Pivot (rotation_degrees.x = -56)
     └─ Camera3D (position.z = +distance, i.e. 25.8 m; fov 55, KEEP_HEIGHT; near 0.3, far 80)
```

- Zoom lerps the distance between 25.8 and 35.2 m.
- Optionally drift the pitch from -56° at default zoom to -60° at max zoom, so the far horizon does not leak.
- Keep perspective. WC3 is not orthographic, and the trapezoid view plus parallax is part of the feel.
- The minimap must draw the camera trapezoid, not a rectangle.

---

## 3. Scale and UI conventions

### 3.1 Scale

**Known facts:**
- 1 tile = 128 units, and 1 cliff level = 128 units.
- Pathing is evaluated on a finer grid. The smallest editor cell is 32×32 (Hive pathing thread, community-observed).
- Unit collision size behaves like a radius. Collision 0–15 occupies 1×1 cell, 16–31 occupies 2×2, 32–47 occupies 3×3, and 48–63 occupies 4×4 (Hive thread, community-tested).
- The Footman's collision size is 31 (warcraft.wiki.gg, Liquipedia).
- "Selection scale" (not collision) controls the green selection circle.
- Most Blizzard doodads allow an editor scale of 0.8–1.2.

**Size relationships to reproduce:**
- Building footprints: farm about 2×2 tiles, barracks about 3×3, town hall about 4×4 (unverified; from memory of WC3 placement grids). Tree footprint about 1 tile.
- Heights (unverified, observational):

| Thing | Height |
|---|---|
| Worker | ~0.6 tile |
| Infantry | ~0.8 tile |
| Hero | ~1.0–1.2 tiles, scaled about 1.1–1.3× a regular unit |
| Large melee (ogre or tauren class) | ~1.3–1.6 tiles |
| Giants / siege | ~2+ tiles |
| Trees | ~2.5–3.5 tiles, tall canopies that partly hide units behind them |
| Small building (farm) | ~1.5 tiles |
| Town hall | ~3–4 tiles |

**Proposal for our game** (1 m = 64 u, so 1 tile = 2 m):

| Class | Footprint | Visual height | Selection ring radius | Tri budget | Texture |
|---|---|---|---|---|---|
| Worker | r 0.35 m | 1.2 m | 0.45 m | 1.5–3k | 512² |
| Infantry | r 0.45 m | 1.6–1.8 m | 0.55 m | 2–4k | 512² |
| Hero | r 0.55 m | 2.0–2.3 m (1.25× infantry) | 0.75 m, plus hero glow ring | 4–8k | 1024² |
| Large unit / monster | r 0.8–1.2 m | 2.5–4 m | 1.0–1.4 m | 4–8k | 1024² |
| Small building | 4×4 m (2×2 tiles) | 3 m | footprint-fitted square or circle | 3–6k | 1024² |
| Main hall | 8×8 m (4×4 tiles) | 7–8 m | | 6–12k | 2048² |
| Tree | ~2×2 m | 5–7 m | n/a | 0.5–1.5k, plus 2 LODs | 512² atlas |
| Rocks / doodads | varies | ≤ 1.5 m | n/a | 100–800 | shared 1024² atlas |

**Rules:**
- Buildings must be **compressed**. A barracks is not realistically sized; it is about 2.5× infantry height.
- Every unit gets a **ground ring, team-colored rim and ground shadow** so it never floats.
- Selection-ring colors (WC3 convention, unverified exact hues): own units green, allies and neutral yellow, enemies red. Pulse on hover.
- Health bars appear above units on Alt or always. Fill shifts green to yellow to red. Casters get a blue mana bar.

### 3.2 UI layout (structural only)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│[Quests][Menu][Allies][Log]      ( day/night clock + orb )   Gold  Lumber  Food x/y  Upkeep │  <- top bar (thin, ornamented)
│[Hero1]                                                                          │
│[Hero2]  hero portrait buttons (left edge) w/ HP+mana bars, level badge          │
│[Hero3]                                                                          │
│                                                                                 │
│                          (3D playfield)                                         │
│[Idle worker]                                                                    │
├──────────┬──────────┬───────────────────────────────┬─────────────┬────────────┤
│ MINIMAP  │ 3D       │ Unit info: name, level/XP,     │ Inventory   │ COMMAND    │
│ (square) │ animated │ dmg/armor/attr icons; or group │ 2×3 (heroes)│ CARD 4×3   │
│ + 5 btns │ portrait │ grid of selected units; or     │             │ (12 slots, │
│ (ping,   │ HP/mana  │ build/train queue with         │             │ hotkeyed)  │
│ terrain, │ under it │ progress bar                   │             │            │
│ colors,  │          │                                │             │            │
│ creeps,  │          │                                │             │            │
│ formation)│         │                                │             │            │
└──────────┴──────────┴───────────────────────────────┴─────────────┴────────────┘
```

- **Command card:** 12 slots, indices 0–11 bottom-right (JASS origin frames). The conventional placement puts standard orders (Move, Stop, Hold, Attack, Patrol) in the top rows and abilities and build/train buttons in the lower rows. Heroes get a "learn skill" sub-menu (unverified exact slots).
- **Top bar:** day/night clock in the center. Upkeep text sits beside food. Upkeep tiers (verified, classic.battle.net, current/TFT-era values): 0–50 food none (100% income), 51–80 low (70% gold income), 81–100 high (40%). In RoC the tiers were 0–40, 41–70 and 71–90 (unverified).
- **Reforged:** decoupled UI elements so the game renders beneath the console, and kept the 12-button card.
- **Our version (proposal):**
  - Keep the structure because it is a genre convention.
  - Make the frame **thinner and more transparent**, using our own ornament motif. For example, carved wood with brass rivets for one faction, or slate and bone for another.
  - Allow the 3D world to show beneath the side panels.
  - Use a live 3D portrait viewport (a SubViewport with a close camera on the head).
  - Use original icons: painted, bold central silhouette, 64×64 to 128×128, with a beveled frame.

---

## 4. Contrast: why Freecraft/Stratagus looks generic, and what makes indie RTS look cheap

### 4.1 Freecraft/Stratagus/Wargus

**What it was:**
- A Linux Warcraft II clone (ALE Clone 1998, renamed Freecraft 1999).
- Blizzard sent a cease-and-desist in 2003. The project became Stratagus (engine) plus Wargus (needs original WC2 data).
- Stratagus is "a 2D engine based on cross-platform open-source libraries", and "Animations are created from a set of .png pictures" (Wikipedia). The C&D letter arrived in June 2003.

**Why it reads as generic or dated** (analysis):
- Square tile grid with visible tile repetition and right-angle coastlines.
- Small fixed-angle sprites with few animation frames.
- Units are tiny relative to the screen, so silhouettes are indistinct.
- Flat, uniform lighting with no atmosphere.
- Muted, "programmer art" palettes in non-Wargus games such as Bos Wars.
- A 1990s side-panel UI that takes a third of the screen.
- No hero focus and no VFX spectacle.
- It copies WC2's surface without WC3's 3D chunkiness, camera drama or painterly richness.

**Avoid:**
- Orthographic flat top-down.
- Grid-aligned tile edges.
- Small unit scale.
- Generic medieval brown/gray.
- Side-panel UI.
- Sprite-sheet stiffness.

### 4.2 Pitfalls that make an indie RTS look cheap

| Pitfall | Symptom | Fix |
|---|---|---|
| Flat lighting | Everything at one value. No form, no time of day. | Wrap-lit key light with painted gradients. Per-biome grading. Cloud shadows. Day/night tint. |
| PBR-realism mismatch | Glossy metal next to painted wood, or photo-sourced textures ("bumpy PBR, not hand-painted", Polycount critique). | One shading model, specular off, painted highlights only. |
| Noisy textures | High-frequency AI or photo noise, grunge overlays. At distance it becomes mush and kills silhouettes. | Median filter or posterize, palette remap, then paint big gradients. Detail frequency ≤ 1/32 of texture width. |
| Tiny, unreadable units | Units below about 30 px tall at default zoom. | Infantry ≥ 40–50 px at 1080p default zoom. Exaggerate the upper third. |
| Inconsistent texel density / style | Some assets crisp, some blurry. Mixed outline styles ("asset store look"). | A style guide before generation, fixed texel density, the same shader, the same LUT. |
| Generic medieval | Brown/gray soldiers, no faction shape language. | Faction shape and hue identity (§7.2). Saturated accents. Myth-flavored silhouettes. |
| Over-cluttered environments | SpellForce 3's dense levels were praised but called "a slog" in places. | Leave lanes clear. Doodads cluster at edges and transitions only. |
| Weightless units | Floating, sliding, no contact shadow. | Blob or real shadow, ground ring, dust puffs on steps and impacts, hit-pause on heavy hits. |
| Weak VFX | Thin, low-alpha particles. | Chunky additive sprites with HDR emissive above 1.0 so they bloom, short lifetimes, screen-shake for big spells. |
| Desaturated grading | "Hazy and gray" (Reforged critique). | Saturation 1.05–1.15 with a warm key. Push shadows toward blue/violet rather than black. |

---

## 5. Modern stylized strategy games to study (for a fresh twist)

| Game | Visual idea to borrow | Caution / note |
|---|---|---|
| **Warcraft Rumble** (Blizzard) | Toy-miniature conceit. 1–2 major color areas per unit. The upper third carries identity. Saturated, welcoming colors. Clean concept, blockout, sculpt and paint pipeline. | Mobile-scale simplification. Our units need a bit more painted texture richness. |
| **Heroes of the Storm** (Blizzard) | The modern renderer version of the Warcraft look. GDC talk "Bringing Orphea to Heroes of the Storm" covers silhouettes and balancing franchise styles, "gameplay first". | MOBA scale (fewer units). |
| **Stormgate** (Frost Giant, ex-WC3/SC2 devs) | Each faction gets its own unified look (art director Jesse Brophy's art reveal). A GamingBolt reviewer said the simple, colorful style gives "a clarity to even the most chaotic battles". (An earlier draft attributed "purpose, appeal, performance" criteria to Brophy; this is unverified.) | A cautionary tale: GamingBolt called the art "divisive". Fans said the graphics "looked a bit more cartoon-like" and wanted something more StarCraft-like. Frost Giant brought in a StarCraft II art director and moved to a "grittier" look (GamesBeat). **Grounded painterly beats plastic cartoony.** |
| **Battle Aces** (Uncapped, cancelled May 2025) | Colorful, charismatic robot units with ultra-clear battles. | Readability alone did not save it, so pair clarity with identity and tone. |
| **Northgard** (Shiro) | Crisp units on richly textured terrain, an "original Warcraft with modern assets" vibe. Territory zones with painted borders. Seasonal winter overlay on terrain. | Units are small. We keep WC3's bigger unit scale. |
| **Age of Mythology: Retold** | Big myth monsters with huge silhouettes. God-power spectacle ("more God powers exploding across the map", Xbox Wire). An earlier draft quoted monsters as "designed for viewing from high above"; that phrase is not in the cited Xbox Wire or Pure Xbox pages (unverified). | Semi-realistic materials. Keep ours painterly. |
| **Songs of Conquest** | Stylized assets lit by modern dynamic light, water reflections and particles. Each campaign setting has its own palette. | Players report busy visuals at zoom. Keep terrain quiet. |
| **Tiny Glade** | Procedural structures that self-assemble (walls, fences, roofs adapt). Soft, warm light. Cozy diorama feel. | Not combat. Borrow only the procedural fences and walls and the light softness. |
| **Bad North** | Radical minimalism ("Minimalism is the thread that runs through just about everything"). Diorama islands, muted soft palette, units as tiny banners and silhouettes. Readable even by sound. | Too minimal for WC3 feel. Borrow the restraint on terrain and unit banners. |
| **Thronefall** | Minimalist low-poly flat colors that keep chaotic night waves readable. Strong day/night phase contrast. | Borrow the night readability: lit units on a darkened world. |
| **SpellForce 3** | Rich, dense, lived-in level dressing. Dramatic lighting in a hero-plus-army RTS. | Clutter hurts movement and readability. Earlier SpellForce games were "very closely modelled after" Warcraft. |
| **Against the Storm** | Weather and storm cycles that re-grade the whole scene. Charming stylized settlers. | Borrow weather-driven grading presets (rain, storm, clear). |
| **Dungeons 4** | Two contrasting worlds (bright overworld vs dark corrupted domain). Corruption visibly transforms terrain. | Borrow a "blight spread" terrain transformation as an animated shader effect. |
| **Diplomacy is Not an Option** | Huge unit counts readable through flat colors and formation shapes. | Small units, so the lesson is for mass scenes only. |
| **The Settlers: New Allies** | Bright, clean, colorful 3D RTS. | Generic-looking result. Shows that bright plus clean without strong shapes and identity reads bland. |
| **League of Legends** (Summoner's Rift update) | "Clarity and Readability" first. Clamp value ranges, reduce occlusion, make each map area recognizable at a glance. | MOBA, but the clarity rules transfer directly. |

("Rogue Spirit" was not researched; it is not clearly a strategy reference.)

---

## 6. Reference images and galleries (annotated)

Blizzard CDN images come from the official "Tales from the Smithy" Reforged posts. Subjects are inferred from the article sections they appear in. Compare each with your memory of the Classic model: what got bigger, what got simpler, and where team color sits.

| # | Link | What to look at |
|---|---|---|
| 1 | [Arthas (Paladin)](https://bnetcmsus-a.akamaihd.net/cms/page_media/SJCTI8FPRT1J1579635414669.jpg) | Giant shoulder pads, maul head bigger than the head, blue/gold faction palette |
| 2 | [Jaina (Archmage)](https://bnetcmsus-a.akamaihd.net/cms/page_media/V1VDW8BX9LFI1579635420298.jpg) | Caster silhouette: staff plus cloak mass. Blizzard: about 700 to 15k polys |
| 3 | [Muradin (Mountain King)](https://bnetcmsus-a.akamaihd.net/cms/page_media/QAIZ55DS0JJV1579635429027.jpg) | Dwarf proportions: huge beard, hands and hammer, short legs |
| 4 | [Kael'thas (Blood Mage)](https://bnetcmsus-a.akamaihd.net/cms/page_media/R4V61X03MLEI1579635422930.jpg) | Slender build still reads through oversized shoulder pieces and orbs |
| 5 | [Sorceress](https://bnetcmsus-a.akamaihd.net/cms/page_media/ONPE5OUYFL4U1579635411119.jpg) | Emblem on cloak as faction ID, cloth as team-color carrier |
| 6 | [Mortar Team](https://bnetcmsus-a.akamaihd.net/cms/page_media/QKPHDGE6A5QG1579635425943.jpg) | Multi-figure unit composition and a prop-heavy silhouette |
| 7 | [Gryphon Rider](https://bnetcmsus-a.akamaihd.net/cms/page_media/71SYW3J4GTIP1579635417322.jpg) | Classic made the mount "much more prominent" for clarity. Reforged gives the rider more detail and the mount less dominance. |
| 8 | [Illidan (Demon Hunter)](https://bnetcmsus-a.akamaihd.net/cms/page_media/39/39Q99JC5MXXH1575589778948.jpg) | Emissive tattoo channels, wing and glaive silhouette |
| 9 | [Keeper / Cenarius](https://bnetcmsus-a.akamaihd.net/cms/page_media/yq/YQ873P0EP10Y1575589659623.jpg) | Antlers and claw hand made more defined for top-down read |
| 10 | [Maiev (Warden)](https://bnetcmsus-a.akamaihd.net/cms/page_media/t9/T9KWJL7BPJ3G1575589804112.jpg) | Crescent back piece and bladed cape as ID shapes visible from above |
| 11 | [Archer](https://bnetcmsus-a.akamaihd.net/cms/page_media/ib/IB3NYFUYPGLP1575589601098.jpg) | Bow redesigned to a clear recurve, ranged-unit read |
| 12 | [Dryad](https://bnetcmsus-a.akamaihd.net/cms/page_media/oq/OQ2DMT6STUJI1575589746916.jpg) | Less focus on the spear, so the body stays visible. Recolored to fawn: Blizzard called the original's grayish-purple "almost undead in nature". |
| 13 | [Druid of the Claw](https://bnetcmsus-a.akamaihd.net/cms/page_media/w2/W2TOFS3XST0D1575589714958.jpg) | Bulky creature mass, fur color blocking |
| 14 | [Mountain Giant](https://bnetcmsus-a.akamaihd.net/cms/page_media/6r/6R57HJKPRCBM1575589830605.jpg) | Shoulder crystals as top-down identifiers |
| 15 | [Arthas (Death Knight)](https://bnetcmsus-a.akamaihd.net/cms/page_media/mb/MBX05RZQ6TZ21579022880906.jpg) | Same hero, new faction palette (teal/ice), recognizable by shapes |
| 16 | [Dreadlords](https://bnetcmsus-a.akamaihd.net/cms/page_media/om/OM16652BEJRC1579023022681.jpg) | Variants of one silhouette differentiated by color |
| 17 | [Kel'Thuzad (Lich)](https://bnetcmsus-a.akamaihd.net/cms/page_media/ah/AHUQVW1Z27XO1579023141732.jpg) | Detail added "without detracting from visual legibility" |
| 18 | [Anub'arak (Crypt Lord)](https://bnetcmsus-a.akamaihd.net/cms/page_media/ck/CK3ASK589D3B1579023329296.jpg) | Insectoid, wide low silhouette |
| 19 | [Meat Wagon](https://bnetcmsus-a.akamaihd.net/cms/page_media/75/75CCSTHVKM6T1579023364236.jpg) | Siege vehicle read: chunky wheels, a payload visible from above |
| 20 | [Crypt Fiend](https://bnetcmsus-a.akamaihd.net/cms/page_media/41/411VLH8US81Z1579023397707.jpg) | Spider-legged silhouette, legs as primary read |
| 21 | [Frost Wyrm](https://bnetcmsus-a.akamaihd.net/cms/page_media/w3/W30LCO6V1F9C1579023425339.jpg) | A "realistic (aka massive)" wingspan was balanced for clarity because flyers must not hide the battlefield |
| 22 | [Samuro (Blademaster)](https://bnetcmsus-a.akamaihd.net/cms/page_media/CGF8NH7UQ8PS1579713521493.jpg) | Hero variants share a recognizable silhouette |
| 23 | [Drek'Thar (Far Seer)](https://bnetcmsus-a.akamaihd.net/cms/page_media/PSAPBRGAIVJ91579713516017.jpg) | Wolf-mount hero, fur and bone accents |
| 24 | [Cairne (Tauren Chieftain)](https://bnetcmsus-a.akamaihd.net/cms/page_media/M7ZMBZB3ZL6Q1579713513267.jpg) | Totem as giant weapon, horn silhouette |
| 25 | [Vol'jin / Rokhan (Shadow Hunter)](https://bnetcmsus-a.akamaihd.net/cms/page_media/3QJBAW6MLP571579713529751.jpg) | Mask and tusk shapes, lanky troll proportions |
| 26 | [Grunt](https://bnetcmsus-a.akamaihd.net/cms/page_media/DAK88JHWU29Q1579713518817.jpg) | "Stylized colors and proportions, realistic textures" (Reforged's middle). Compare to our painterly target |
| 27 | [Shaman](https://bnetcmsus-a.akamaihd.net/cms/page_media/8USHK1JAMBGI1579713526925.jpg) | Bone-detail budget vs silhouette |
| 28 | [GI concept: Hellscream](https://gameinformer.com/sites/default/files/styles/content_header_l/public/2018/11/13/91fee89a/hellscream.jpg.webp) | Original WC3-era Didier/Metzen concept: line weight, exaggeration |
| 29 | [GI concept: Thrall face](https://gameinformer.com/sites/default/files/styles/body_default/public/2018/11/13/e6fecb61/thrall_face.jpg.webp) | Facial exaggeration for portrait art |
| 30 | [GI concept: dwarven mortar team](https://gameinformer.com/sites/default/files/styles/body_default/public/2018/11/13/fc3a3858/dwarven_mortar_team.jpg.webp) | Didier's original Mortar concept: chunky prop design |
| 31 | [GI concept: assassin/swordmaster](https://gameinformer.com/sites/default/files/styles/body_default/public/2018/11/13/db35afe2/assassin_swordmaster.jpg.webp) | Early hero exploration |
| 32 | [GI concept: elf heads](https://gameinformer.com/sites/default/files/styles/body_default/public/2018/11/13/34229e17/elf_heads.jpg.webp) | Head-shape language for a faction |
| 33 | [GI concept: Night Elf Demon Hunter](https://gameinformer.com/sites/default/files/styles/body_default/public/2018/11/13/80fb63d4/nightelf_demonhunter.jpg.webp) | Original vs final silhouette |
| 34 | [Rumble: Gargoyle pipeline stages](https://bnetcmsus-a.akamaihd.net/cms/content_entry_media/WGV9M5AU70LF1676998534922.png) | Concept, block-out, sculpt, final textures, in-game. Copy this pipeline for AI assets |
| 35 | [Rumble: Gargoyle in five poses](https://bnetcmsus-a.akamaihd.net/cms/content_entry_media/7RFPS6G8F95G1676998534782.png) | Strong poses and silhouettes at mini scale |
| 36 | [AoM Retold key art](https://xboxwire.thesourcemediaassets.com/sites/2/2024/08/AoMR_Wallpaper_Xbox-Console_1920x1080_RGB-8ed7260786989e730fb3.jpg) | Myth-monster scale and color drama |
| 37 | [Game Informer WC3 concept gallery (page)](https://www.gameinformer.com/index.php/2018/11/14/explore-warcraft-iiis-origins-in-this-rare-concept-art-gallery) | Full article plus Didier quotes on simplifying for top-down |
| 38 | [Game Informer: How Blizzard has reforged WC3](https://gameinformer.com/2018/11/02/how-blizzard-has-reforged-warcraft-iii) | Side-by-side sketches, "overbuilt" units |
| 39 | [Game Informer 2020: Reforged vs original](https://www.gameinformer.com/interview/2020/01/28/what-makes-warcraft-iii-reforged-different-from-the-original) | Screenshots of the reworked maps |
| 40 | [Netzwelt Reforged screenshot gallery](https://www.netzwelt.de/galerie/23629-warcraft-3-reforged.html) | Reforged in-game terrain, cliffs, tree walls, UI |
| 41 | [Worthplaying 2002 "golden" WC3 screens](https://worthplaying.com/article/2002/6/23/news/4404-warcraft-iii-reign-of-chaos-golden-screens/) | Classic 2002 in-game look: tile blending, doodads, HUD |
| 42 | [Neowin: high-res WC3 beta screenshots](https://www.neowin.net/news/high-res-warcraft-3-screenshots/) | Classic-era screenshots |
| 43 | [Macworld: "Blizzard: Warcraft III coming to Mac OS X" (May 2001)](https://www.macworld.com/article/161365/war3.html) | A news item, not a gallery. It references E3-era screenshots of the Windows build. Low value. |
| 44 | [Warcraft wiki: box art](https://warcraft.wiki.gg/wiki/Box_art) | Key-art composition per race (painted, saturated) |
| 45 | [Sebastian Wagner: Stormgate Human Vanguard (ArtStation)](https://sebastian-wagner.artstation.com/projects/6Lay80) | Building concept sheets for an RTS faction (barracks, hangar, mech bay). Unverified: ArtStation blocks automated fetching. |
| 46 | [Normalweird: WoW tileset textures (ArtStation)](https://normalweird.artstation.com/projects/98JqqW) | Blizzard-style tileable hand-painted ground textures (WoW: Midnight). Target for terrain tiles. Unverified: ArtStation blocks automated fetching. |
| 47 | [ArtStation Magazine: Heroes of the Storm 2.0 Art Blast](https://magazine.artstation.com/2017/05/blizzard-entertainment-heroes-storm-art-blast/) | Modern Blizzard-stylized environments, characters and UI |
| 48 | [ArtStation Magazine: WoW Dungeon Environment Art Blast](https://magazine.artstation.com/2018/09/blizzard-entertainment-world-warcraft-art-blast-dungeon-environment-art/) | Hand-painted environment modules, color keys |
| 49 | [Polycount: "Show your hand-painted stuff"](https://polycount.com/discussion/125954/show-your-hand-painted-stuff-pls/p53) | Low-poly hand-painted props and characters, texture technique |
| 50 | [OpenGameArt: hand-painted stone texture (WoW-style)](https://opengameart.org/content/hand-painted-stone-texture) | Tileable painted stone (OGA-BY 3.0). Style and stroke scale reference |
| 51 | [Stormgate media kit](https://playstormgate.com/media-kit) | Official screenshots and concept art (box/Drive downloads) |
| 52 | [Tiny Glade on Steam](https://store.steampowered.com/app/2198150/Tiny_Glade/) | Procedural walls and fences, soft cozy light |
| 53 | [Hive Terraining Contest 15 results](https://www.hiveworkshop.com/threads/terraining-contest-15-results.249166) | Community WC3-engine terrain art: mood through tiles plus doodads plus fog |
| 54 | [Hive advanced terraining tutorial](https://www.hiveworkshop.com/threads/advanced-terraining-tutorial.203428) | Tile ladder, shore dressing, fog setup |
| 55 | [GDC Vault: Bringing Orphea to HotS](https://gdcvault.com/play/1025744/contactUs) | Silhouette techniques and franchise-style balancing |
| 56 | [Brütal: The Art of Samwise (Abrams)](https://www.abramsbooks.com/product/brutal_9781419747755/) | The Didier style bible (book) |
| 57 | The Art of Northgard (artbook; the earlier Omake Books link returns 404 and was removed) | Stylized Norse RTS concept work |
| 58 | [Songs of Conquest digital artbook](https://store.epicgames.com/p/songs-of-conquest--digital-artbook) | Per-biome palettes in a stylized strategy game |

---

## 7. Recommendations: a cohesive AI-generated style in Godot

### 7.1 Direction statement (proposal)

**"Storm-lit Heroic Diorama".** Warcraft III's chunky, hand-painted, saturated heroic fantasy, shown as a living painted diorama:

- **Forms:** WC3/Didier rules. Oversized upper body, hands, weapons and shoulders. Big simple shapes, 1–2 color masses plus team color.
- **Surfaces:** painterly albedo with baked soft top-light, painted AO and painted metal highlights. No PBR gloss, no photo detail.
- **Light (our twist):**
  - Warm golden-hour key with cool violet-blue shadows.
  - Large **drifting cloud shadows** across the map (a scrolling noise texture multiplied into the light). This is cheap, alive, and absent in WC3.
  - **Wind sway** on trees and grass via vertex shader.
  - **Team-color rim light** on units, and a **rune or emissive accent** that glows in team color at night.
- **Living world:** a corruption/blight biome that animates outward over terrain (shader-driven blend mask). Day/night re-grades the world blue and lights torches and windows on buildings.
- **Motion signature (fits the no-rigging constraint):** "toy-soldier" procedural animation.
  - Hop and bob walk, lean into movement, squash and stretch on attack.
  - The weapon is a separate mesh pivoting on a hand socket, with a dust puff on landing.
  - Big monsters use segmented parts (head, jaw, wings) on pivots.
- **Faction differentiation (proposal for two starter factions):**
  - Faction A, "Hearth Wardens" (stalwart folk): rounded, stout, shield-wall shapes. Warm wood, brass, cream and slate-blue. Team color on tabards, banners and roof tiles.
  - Faction B, "Thornborn" (wild or fey or beast tribe): angular, spiky, asymmetric. Bone, moss green, rust red and teal glow. Team color on war-paint cloth, feathers and hide banners.

### 7.2 Palette and value targets (proposal)

**Global value and saturation budget** (HSV, measured on albedo):

| Asset class | Value range | Max saturation | Notes |
|---|---|---|---|
| Terrain ground | 30–65% | 45% | Low local contrast. Macro variation only. |
| Cliffs / rocks | 25–60% | 30% | Cool neutral. Lighter top edges (painted rim). |
| Trees / foliage | 25–70% | 60% | Vertical gradient: dark trunk base, light canopy top |
| Buildings | 20–85% | 65% | Roofs carry team color or faction hue |
| Units | 10–95% | 85% | Highest contrast in the scene |
| Team-color areas | 50–90% | 90%+ | Must survive night grading |
| VFX | Emissive, HDR >1.0 | n/a | The only things that bloom |

**Biome palettes (starting hex values, tune in engine):**

| Biome | Grass (main / thick) | Dirt / cracked | Road | Rock / cliff | Shallow / deep water | Sky / fog |
|---|---|---|---|---|---|---|
| Greenvale (summer) | #6E9A3E / #4F7A2E | #8C6B45 / #A88C60 | #9A8F7C | #7D766A / #5E574E | #4FA3A0 / #22566E | #CFE3F0 / #B8CCD8 |
| Emberwood (fall) | #8E8A3C / #6E6A2C | #7E5A3A / #9C7A52 | #8F8270 | #75695C / #564B42 | #4A8C8C / #234A5E | #F2D3A8 / #D9B48E |
| Frostmarch (winter) | snow #E6EEF5 / #C9D6E3 | frozen dirt #6F6A66 | #8E8C88 | #6C7889 / #4C5666 | ice #9ED4E8 / #2F5F80 | #DCE8F5 / #C2D2E6 |
| Gloamwood (dusk forest) | #3F6B5A / #2E5248 | #5A4A50 / #6E5E64 | #6A6470 | #4E5566 / #383D4C | #3E8FA8 / #1C3C5A | #6E6AA8 / #4A4E80 |
| Sunscar (savanna) | #B49A55 / #96803F | #B0603A / #C98A5A | #C2A57A | #A4664A / #7A4A36 | #5AA6A0 / #2A6670 | #F5D9A6 / #E8C08C |
| Blightmire (corruption) | #5E6E3A / #4A3E5A | #4A3A40 / #5C4A50 | n/a | #4A4450 / #2E2A34 | toxic #7FBF3F / #3A2E4A | #7A8A5A / #4E4A5E |

**Team colors** (WC3's 12 for reference: Red 255,3,3; Blue 0,66,255; Teal 28,230,185; Purple 84,0,129; Yellow 255,252,0; Orange 254,138,14; Green 32,192,0; Pink 229,91,176; Gray 149,150,151; Light Blue 126,191,241; Dark Green 16,98,70; Brown 78,42,3).

Use our own tuned set. Hue spacing must survive night grading and red/green color-blindness, and each color needs a light and a dark ramp. Proposal:
- Crimson #D8232A
- Royal Blue #2A62FF
- Teal #1FC7B0
- Violet #7A2FD0
- Gold #F2C619
- Orange #FF8A1E
- Emerald #2EAE3A
- Rose #E2559F
- Slate #8C96A0
- Sky #7FC4F5
- Forest #1E6B4A
- Umber #6B3E1A

### 7.3 Krea prompt kit

**Global style suffix** (append to every concept or texture prompt):
> stylized hand-painted fantasy strategy game art, chunky heroic proportions, oversized hands shoulders and weapon, big simple readable shapes, bold silhouette, saturated harmonious colors, soft painted gradients, gentle top light painted into the colors, painterly brush texture, clean color blocking with 1-2 main colors, game-ready asset, plain neutral light-gray background

**Negative or avoid terms** (where the model supports negatives; otherwise phrase as "no …"):
> photorealistic, realistic proportions, glossy PBR reflections, chrome, specular highlights, film grain, noise, grunge overlay, tiny intricate details, thin limbs, anime, chibi, pixel art, harsh cast shadows, dramatic rim light, depth of field, text, watermark, logo

Never include "Warcraft", "Blizzard", "Samwise", "Azeroth" or WC3 unit names.

**Prompt templates:**

1. **Unit concept for image-to-3D** (Tripo, Hunyuan3D, TRELLIS, Meshy, Rodin):
   > full body [UNIT], standing A-pose, front three-quarter view, centered, entire figure visible including feet, [faction palette], solid magenta (#FF00FF) cloth on tabard and shoulder trim [team-color key], weapon held clear of the body, evenly lit flat albedo, no cast shadows, + style suffix

   - Exaggerate by about 1.3× beyond the final target, because 3D generators thin small parts.
   - Generate the weapon separately ("isolated [weapon], side view") so it can be its own pivoting mesh.
2. **Building concept:**
   > [BUILDING] for a fantasy strategy game, compact chunky proportions, oversized roof with [team-color key magenta] roof tiles and banner, viewed from 45 degree high three-quarter angle, isolated on plain background, + style suffix
3. **Tileable terrain texture:**
   > seamless tileable hand-painted ground texture, top-down orthographic, [short meadow grass with small clover clumps], soft painterly strokes, low contrast, mid value, even flat lighting, no perspective, no objects casting shadows, 1024x1024

   Make one per tile in the ladder: cracked dirt, dirt, grassy dirt, grass, thick grass, road, rock, snow.
4. **Cliff / rock texture:**
   > seamless tileable hand-painted rock cliff face texture, chunky stylized stone blocks with lighter top edges and darker crevices, cool gray [biome tint], painterly, flat even light
5. **Ability / unit icon:**
   > square fantasy game ability icon, [subject], bold single central silhouette, painted, strong value contrast, glowing [color] accent, dark vignette edges, no text
6. **Portrait (for the 3D-portrait fallback or loading art):**
   > bust portrait of [character], exaggerated heroic features, big jaw/brow [as fits], painted, warm key light, cool shadow, plain background

**Cohesion levers:**
- **Train a Krea style (LoRA)** on 10–30 curated, uniformly lit images of our approved look. The Krea user guide sets a minimum of 3 images, says "Larger datasets (10-30 images) improve the model's ability to generalize", and advises "uniform lighting, color balance, and resolution". The Krea developer tutorial calls 5 images the "minimum viable" and recommends 10–30. Use that style code for every 2D generation.
- Keep a single moodboard.
- Lock seeds per asset family.
- Generate all units of a faction in one batch session with the same suffix.

### 7.4 Post-processing pipeline for AI assets (proposal, scripted in Python)

1. **Texture cleanup** (Pillow/NumPy/OpenCV):
   - Median or bilateral filter to kill AI micro-noise.
   - Optional k-means palette reduction (12–24 colors) then re-blur.
   - **Palette remap** toward the biome or faction palette via a 3D LUT.
   - Clamp saturation and value per asset class (§7.2).
2. **Team-color mask:** key out the magenta (#FF00FF ± hue 15°, sat > 0.5) region into a mask, using a separate grayscale map or the albedo alpha. Replace it with a luminance-preserving gray so the shader can tint it.
3. **Lighting de-bake check:** if the 3D generator baked a strong directional shadow, neutralize it. Low-frequency luminance flattening (divide by a heavily blurred copy, re-multiply by the target gradient) keeps painted AO while removing directional light.
4. **Mesh** (Blender headless or `trimesh`/`pymeshlab`):
   - Decimate to the tri budget (§3.1).
   - Normalize scale by bounding-box height to class height.
   - Set the origin at the feet center, facing -Z.
   - Split the weapon or parts for procedural animation.
   - Generate LOD1 at 50% and LOD2 at 20%.
5. **Texel density:** units about 256 px/m, buildings about 128–160 px/m, terrain about 128 px/m (one 256-px tile texture per 2 m tile; proposal). Re-bake or resize to match.
6. **Validation render:** auto-render each asset from the game camera (-56°, 25.8 m) at 1080p. Then check:
   - (a) Silhouette test: a black fill must be identifiable.
   - (b) Grayscale test: there must be 3 value masses.
   - (c) Size test: infantry ≥ 40 px tall.
   - (d) Side by side with approved "golden" assets.

### 7.5 Godot 4.7 lighting and rendering recipe (proposal, starting values)

**Renderer:**
- Ship on **Forward+**.
- Keep the look working on **Compatibility**. This is required for headless or software-rendered CI in our GPU-less container, and Compatibility gained a simplified SSAO in 4.6.
- Avoid SDFGI, VoxelGI and volumetric fog. The painted textures already carry GI.

**Material** (one shared `ShaderMaterial` uber-shader for units, buildings and doodads):

```glsl
shader_type spatial;
render_mode diffuse_lambert_wrap, specular_disabled; // or custom light() toon ramp below
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D team_mask : hint_default_black;
uniform vec4 team_color : source_color = vec4(0.85,0.14,0.16,1.0);
uniform float vgrad_strength = 0.25;   // world-space vertical gradient (darker feet, lighter top)
uniform float vgrad_height = 2.0;      // metres over which gradient runs (per asset class)
uniform vec4 rim_color : source_color; // set = team_color * 0.6 for units, sky tint for doodads
uniform float rim_power = 3.0;
varying float h;
void vertex(){ h = (MODEL_MATRIX * vec4(VERTEX,1.0)).y - MODEL_MATRIX[3].y; }
void fragment(){
  vec3 c = texture(albedo_tex, UV).rgb;
  float m = texture(team_mask, UV).r;
  c = mix(c, c * team_color.rgb * 1.6, m);                     // luminance-preserving tint
  c *= mix(1.0 - vgrad_strength, 1.0 + vgrad_strength*0.4, clamp(h / vgrad_height, 0.0, 1.0));
  ALBEDO = c; ROUGHNESS = 1.0; METALLIC = 0.0;
  float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), rim_power);
  EMISSION = rim_color.rgb * rim * 0.35;
}
```

For a softer, banded "painted" ramp, replace `diffuse_lambert_wrap` with a `light()` function: `DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * texture(ramp, vec2(dot(NORMAL,LIGHT)*0.5+0.5, 0.5)).r / PI;`. Use a 2–3 step ramp with soft edges (0.08–0.15 width). Avoid hard 1-bit cel. Ready-made references: godotshaders.com "Flexible Toon Shader (Godot 4)".

**Lights:**
- **Sun (DirectionalLight3D):**
  - Elevation 50–55°. Azimuth from the camera-left and slightly toward the camera (screen lower-left), so camera-facing sides are lit and shadows fall up-right, visible behind units.
  - Day color #FFF0D8, energy 1.0–1.15.
  - Shadows on, PSSM 2 splits, max distance 60–80 m, `shadow_opacity` 0.55–0.7 (painted AO already darkens). Light `angular_distance` 1–2° for soft edges.
- **Ambient:** `ambient_light_source = Color` (or Sky), color #9DB3D6 (cool), energy 0.45–0.6. Target a **key:ambient ≈ 2:1 to 2.5:1**, which is WC3-like flat-ish lighting.
- **Night:** sun becomes moon #8EA6FF at energy 0.35–0.45, ambient #3B4A80 at 0.45. Point lights on torches and windows (OmniLight3D, no shadows, range 4–8 m, #FFB060). Units keep the team-color rim, so they stay readable (Thronefall lesson).
- **Cloud shadows (signature):** project a tiling noise texture (scale about 40–60 m, scroll about 1 m/s with wind) as a multiply term on direct light. Implement either via `light()` (sample by world XZ) or as a large `Decal`/terrain-shader term. Strength 0.25–0.35.

**Environment:**
- **Tonemap:** **Linear** or **Reinhard** (white about 1.5) so painted albedo hues stay as authored. AgX and ACES shift or desaturate saturated painted colors, so use them only if a test proves otherwise. Exposure 1.0.
- **Adjustments:** saturation 1.05–1.12, contrast 1.0–1.05. **Color correction:** a per-biome **3D LUT** (17³ or 33³, imported as Texture3D) for each biome and time of day, lerped during the day/night transition.
- **Glow:** enabled, HDR threshold 1.0–1.2, intensity 0.6–0.9, Additive or Softlight blend. Only emissive VFX, runes and torches exceed 1.0.
- **Fog:** depth fog matching the biome sky color, beginning about 32 m and ending about 90 m from camera. That only hazes the top of the screen, adding atmospheric depth to the trapezoid. Sun scatter 0.1–0.2 at dawn and dusk. Height fog only in Gloamwood and Blightmire basins.
- **SSAO:** Forward+ radius 1.0–1.5 m, intensity 1.0–1.5 (subtle contact grounding). In Compatibility, use the simplified version or off.
- **Anti-aliasing:** MSAA 4× (Forward+) plus FXAA fallback. Silhouette crispness matters more than texture sharpness. Mipmaps with anisotropic 4–8× on terrain.

**Terrain shader:**
- Splat blend of up to 8 layers per biome, ordered like WC3's ladder.
- Blend masks get painted-noise edges (a world-space noise texture perturbs the blend threshold), so transitions look brushed rather than tile-aligned.
- Triplanar mapping on cliff faces.
- **World-space macro tint** (very low frequency noise, 30–60 m period, ±6% value, ±4° hue) to kill tiling.
- Vertex-color AO at cliff bases and under trees.
- A blight/corruption mask channel that animates outward.

**Fog-of-war rendering:** unexplored areas are near-black (#0A0C12). Explored-but-not-visible areas are desaturated and darkened (value ×0.55, saturation ×0.4, slight blue). Use soft edges blurred over about 1 tile. Never pure black for explored areas.

**Shadows for units in Compatibility:** a fallback blob-shadow `Decal` or a flat quad with a radial gradient (opacity 0.45). WC3 itself used blob shadow images for units.

### 7.6 IP guardrails for the art (brief)

- Copy the **qualities** (proportions, painterly technique, camera, layout structure), never the **expressions**:
  - No WC3 unit designs, names, icons, UI frame art, faction emblems or terrain textures.
  - No "Warcraft" or "Blizzard" in prompts or filenames.
- Colors, camera numbers and a bottom-console layout are genre conventions and functional choices.
- Make every faction's silhouette set original: draw thumbnails and check they don't map one-to-one to WC3 units (e.g., avoid "green orc grunt with axe and shoulder spikes").

---

## Sources

- [Blizzard.j via lep/jassdoc (bj_CAMERA_DEFAULT_DISTANCE 1650, AOA 304, FOV 70, FARZ 5000, ROTATION 90, ROLL 0)](https://raw.githubusercontent.com/lep/jassdoc/master/Blizzard.j)
- [JassBot: bj_CAMERA_DEFAULT_FOV = 70](https://lep.duckdns.org/jassbot/doc/bj_CAMERA_DEFAULT_FOV)
- [Hive Workshop: Cameras (default distance 1650, AoA 304, FarZ max 10,000)](https://www.hiveworkshop.com/threads/cameras.160369/)
- [PCGamingWiki: Advanced Camera Control (via search snippet; the page returned 403. Its AoA of 300 conflicts with Blizzard.j's 304)](https://community.pcgamingwiki.com/files/file/1145-advanced-camera-control/)
- [Blizzard: Warcraft III Reforged Patch 1.33.0 (camera zoom options)](https://news.blizzard.com/en-us/article/23816417/warcraft-iii-reforged-patch-1-33-0-now-live)
- [Blizzard: Warcraft III Reforged Patch 1.35.0 (zoom levels 1750/2100/2250)](https://news.blizzard.com/en-gb/article/23896791/warcraft-iii-reforged-patch-1-35-0-now-live)
- [Blizzard: Patch notes 1.36.1 (granular zoom)](https://news.blizzard.com/en-us/article/23987390/warcraft-iii-reforged-patch-notes-version-1-36-1)
- [HiveWE wiki: war3map.w3e terrain format (tile 128, height formulas, tileset codes)](https://github.com/stijnherfst/HiveWE/wiki/war3map.w3e-Terrain)
- [Hive Workshop wiki: War3map.w3e – Terrain](https://wiki.hiveworkshop.com/index.php/War3map.w3e_-_Terrain)
- [Blizzard forums: Reforged patch notes thread (tileset limit 16 to 64; the post body says 2.0.3 Build 23101)](https://us.forums.blizzard.com/en/warcraft3/t/warcraft-iii-reforged-patch-notes-version-204/36567/4)
- [Hive Workshop: Advanced terraining tutorial](https://www.hiveworkshop.com/threads/advanced-terraining-tutorial.203428)
- [Hive Workshop: How to use a custom terrain texture (256×256 vs 512×256)](https://www.hiveworkshop.com/threads/how-to-use-a-custom-terrain-texture.214600)
- [Hive Workshop: Pathing collision size values into real values](https://www.hiveworkshop.com/threads/pathing-collision-size-values-into-real-values.271205)
- [Hive Workshop: Let's make a pathing tutorial (WIP)](https://www.hiveworkshop.com/threads/wip-lets-make-a-pathing-tutorial.307864/)
- [Hive Workshop: DNC lighting / brightness thread (does not confirm the white-day/blue-night claim)](https://www.hiveworkshop.com/threads/is-there-anyway-i-can-change-in-game-lighting-brightness-without-fog.304188)
- [Hive Workshop: WC3 editor player colors reference (links to an external sheet; the RGB values are verified via w3ts instead)](https://www.hiveworkshop.com/threads/wc3-editor-player-colors-reference.306608)
- [w3ts color utilities (player color RGB values)](https://cdn.jsdelivr.net/npm/w3ts@3.0.2/utils/color.lua)
- [JassBot: BlzGetOriginFrame (command button indices 0–11)](https://lep.duckdns.org/jassbot/doc/BlzGetOriginFrame)
- [Blizzard forums: UI bottom bar customization (Reforged UI decoupled, 12-icon card)](https://us.forums.blizzard.com/en/warcraft3/t/ui-bottom-bar-customization/1080)
- [Hive Workshop wiki: UI Frames](https://wiki.hiveworkshop.com/index.php/UI_Frames)
- [Liquipedia: Daytime (via search)](https://liquipedia.net/warcraft/Daytime)
- [classic.battle.net: Upkeep](https://classic.battle.net/war3/basics/upkeep.shtml)
- [warcraft.wiki.gg: Footman (WC3)](https://warcraft.wiki.gg/wiki/Footman_(Warcraft_III))
- [warcraft.wiki.gg: Mercenary Camp (tileset list cross-check)](https://warcraft.wiki.gg/wiki/Mercenary_camp)
- [Game Informer: Explore Warcraft III's origins in this rare concept art gallery (Didier quotes)](https://www.gameinformer.com/index.php/2018/11/14/explore-warcraft-iiis-origins-in-this-rare-concept-art-gallery)
- [Game Informer: How Blizzard has reforged Warcraft III](https://gameinformer.com/2018/11/02/how-blizzard-has-reforged-warcraft-iii)
- [Game Informer: What makes Warcraft III Reforged different](https://www.gameinformer.com/interview/2020/01/28/what-makes-warcraft-iii-reforged-different-from-the-original)
- [Blizzard: Tales from the Smithy – Reforging the Humans](https://news.blizzard.com/en-us/article/23150108/tales-from-the-smithy-reforging-the-humans)
- [Blizzard: Tales from the Smithy – Reforging the Orcs](https://news.blizzard.com/warcraft3/23150109/)
- [Blizzard: Tales from the Smithy – Reforging the Undead](https://news.blizzard.com/en-gb/article/23150110/tales-from-the-smithy-reforging-the-undead)
- [Blizzard: Tales from the Smithy – Reforging the Night Elves](https://news.blizzard.com/en-gb/article/23150111/tales-from-the-smithy-reforging-the-night-elves)
- [Blizzard: Inside Warcraft Rumble – Creating a Mini](https://news.blizzard.com/en-gb/article/23899627/inside-warcraft-rumble-creating-a-mini)
- [Blizzard: Warcraft Rumble developer interview (Carin Huurnink)](https://news.blizzard.com/en-us/article/23923489/developer-interview-sit-down-with-senior-animator-carin-huurnink)
- [Pocket Tactics: Warcraft Rumble interview](https://www.pockettactics.com/warcraft-rumble/interview)
- [PocketGamer.biz: Translating the Warcraft aesthetic to mobile](https://www.pocketgamer.biz/news/78734/translating-the-warcraft-aesthetic-to-mobile-arclight-rumble/)
- [Blizzplanet: Eurogamer interviews Samwise Didier](https://www.blizzplanet.com/blog/comments/eurogamer_interviews_samwise_didier)
- [Parka Blogs: review of WoW TCG art book (Didier's rules)](https://www.parkablogs.com/comment/10560)
- [Wikipedia: Samwise Didier](https://en.wikipedia.org/wiki/Samwise_Didier)
- [GameSpot: Didier retires after 32 years](https://gamespot.com/articles/blizzard-art-director-who-invented-the-name-warcraft-retires-after-32-years/1100-6519117/)
- [Abrams: Brütal – The Art of Samwise](https://www.abramsbooks.com/product/brutal_9781419747755/)
- [Wikipedia: Warcraft III: Reforged](https://en.wikipedia.org/wiki/Warcraft_III:_Reforged)
- [Blizzard forums: Artstyle raises concerns (Reforged)](https://us.forums.blizzard.com/en/warcraft3/t/artstyle-raises-concerns/473)
- [Windows Central: Does Reforged deserve the lowest Metacritic score?](https://www.windowscentral.com/warcraft-iii-reforged-really-bad)
- [PC Games Insider: Blizzard addresses Reforged criticism](https://www.pcgamesinsider.biz/news/70432/blizzard-has-addressed-warcraft-3-reforged-criticism/)
- [Hive Workshop: Reforged recap (community Q&A summary)](https://www.hiveworkshop.com/threads/reforged-recap-the-future-of-warcraft-part-ii.316817)
- [Mein-MMO: WoW's stylized art decision after 20 years](https://mein-mmo.de/en/the-best-decision-in-wow-can-still-be-seen-after-20-years,1229840)
- [Wikipedia: Stratagus](https://en.wikipedia.org/wiki/Stratagus)
- [warcraft.wiki.gg: Stratagus](https://warcraft.wiki.gg/wiki/Stratagus)
- [Phoronix: Wargus – Open-Source Warcraft II on Linux](https://www.phoronix.com/news/MTAzMzk)
- [bugnet.io: How to avoid the asset store look](https://bugnet.io/blog/how-to-avoid-the-asset-store-look)
- [Wayline: Developer checklist – fixing asset pack art clashes](https://www.wayline.io/blog/developer-checklist-fixing-asset-pack-art-clashes)
- [Polycount: critique recommending vertical gradients / hand-painted vs PBR](https://polycount.com/discussion/comment/2797595/)
- [Polycount: low-poly WC3 modding (1,500 tris, colorful textures)](https://polycount.com/discussion/comment/886533)
- [Polycount: Show your hand-painted stuff](https://polycount.com/discussion/125954/show-your-hand-painted-stuff-pls/p53)
- [Surrender at 20: Updating Summoner's Rift dev blog](https://www.surrenderat20.net/2014/06/update-to-summoners-rift-headed-to-pbe.html)
- [Destructoid: Riot details Summoner's Rift update](https://www.destructoid.com/?p=147859)
- [GDC Vault: Bringing Orphea to Heroes of the Storm](https://gdcvault.com/play/1025744/contactUs)
- [ArtStation Magazine: Heroes of the Storm 2.0 Art Blast](https://magazine.artstation.com/2017/05/blizzard-entertainment-heroes-storm-art-blast/)
- [ArtStation Magazine: WoW Dungeon Environment Art Blast](https://magazine.artstation.com/2018/09/blizzard-entertainment-world-warcraft-art-blast-dungeon-environment-art/)
- [Stormgate: Developer update – the road ahead for campaign](https://playstormgate.com/news/stormgate-developer-update-the-road-ahead-for-campaign)
- [GamesBeat: Stormgate campaign with a more StarCraft-like look](https://gamesbeat.com/stormgate-campaign-one-ashes-of-earth-debuts-august-5-with-a-more-starcraft-like-look/)
- [GamingBolt: Stormgate early access review](https://gamingbolt.com/stormgate-early-access-review-the-return-of-the-rts)
- [Devtrackers: Stormgate technology and art reveal](https://devtrackers.gg/stormgate/p/d63517a6-stormgate-technology-and-art-reveal-video)
- [Stormgate media kit](https://playstormgate.com/media-kit)
- [ArtStation: Sebastian Wagner – Stormgate Human Vanguard](https://sebastian-wagner.artstation.com/projects/6Lay80)
- [PC Gamer: Battle Aces hands-on](https://www.pcgamer.com/games/rts/battle-aces-deckbuilding-rts-hands-on-preview/)
- [Gematsu: Battle Aces canceled](https://www.gematsu.com/2025/05/battle-aces-canceled)
- [Checkpoint Gaming: Northgard review](https://checkpointgaming.net/reviews/2018/03/northgard-review/)
- [Xbox Wire: Beyond a Remake – Age of Mythology: Retold](https://news.xbox.com/en-us/2024/08/20/beyond-a-remake-how-age-of-mythology-retold-revives-and-retools-a-beloved-classic/)
- [Pure Xbox: AoM Retold interview](https://purexbox.com/features/interview-age-of-mythology-retold-a-reimagined-classic-makes-its-grand-arrival-on-xbox-and-pc)
- [God is a Geek: Songs of Conquest review](https://www.godisageek.com/reviews/songs-of-conquest-review/)
- [Epic Games Store: Songs of Conquest digital artbook](https://store.epicgames.com/p/songs-of-conquest--digital-artbook)
- [Steam: Tiny Glade](https://store.steampowered.com/app/2198150/Tiny_Glade/)
- [PocketGamer.biz: Indie spotlight – Plausible Concept on Bad North](https://www.pocketgamer.biz/interview/68638/indie-spotlight-plausible-concept-on-bad-north/)
- [Gaming Audio News: Bad North developers on readability](https://gamingaudionews.com/2018/04/26/bad-norths-developers-talk-about-inspiration-behind-audio-and-gameplay/)
- [PCGamesN: Thronefall full launch](https://www.pcgamesn.com/thronefall/steam-full-launch)
- [Kotaku: Thronefall](https://kotaku.com/thronefall-islanders-tower-defense-strategy-steam-pc-1850701534)
- [KeenGamer: SpellForce 3 review](https://www.keengamer.com/articles/reviews/spellforce-3-review/)
- [Wccftech: SpellForce 3 review](https://wccftech.com/review/spellforce-3/amp/)
- [Geardiary: Against the Storm review](https://geardiary.com/2022/12/08/against-the-storm-review-excited-to-see-more/)
- [Godot docs: Spatial shader reference (render modes, light())](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html)
- [Godot docs: Environment and post-processing (tonemap, fog, LUT, glow, SSAO per renderer)](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)
- [godotshaders.com: Flexible Toon Shader (Godot 4)](https://godotshaders.com/shader/flexible-toon-shader-godot-4/)
- [Krea docs: Train an image style (LoRA)](https://docs.krea.ai/developers/tutorials/train-image-style)
- [Krea docs: Training (user guide)](https://www.krea.ai/docs/user-guide/features/training)
- [Netzwelt: Warcraft 3 Reforged gallery](https://www.netzwelt.de/galerie/23629-warcraft-3-reforged.html)
- [Worthplaying: WC3 golden screens (2002)](https://worthplaying.com/article/2002/6/23/news/4404-warcraft-iii-reign-of-chaos-golden-screens/)
- [Neowin: High-res Warcraft 3 screenshots](https://www.neowin.net/news/high-res-warcraft-3-screenshots/)
- [Macworld: Blizzard: Warcraft III coming to Mac OS X (2001)](https://www.macworld.com/article/161365/war3.html)
- [warcraft.wiki.gg: Box art](https://warcraft.wiki.gg/wiki/Box_art)
- [OpenGameArt: Hand painted stone texture](https://opengameart.org/content/hand-painted-stone-texture)
- [Hive Workshop: Terraining Contest 15 results](https://www.hiveworkshop.com/threads/terraining-contest-15-results.249166)
- [ArtStation: Normalweird – WoW tileset textures](https://normalweird.artstation.com/projects/98JqqW)
