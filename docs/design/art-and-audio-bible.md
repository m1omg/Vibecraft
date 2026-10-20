# Art and Audio Bible: `kingdom`, `clans`, shared and neutral

*Design date: 2026-10-16; revised 2026-10-17 and 2026-10-19 (review rounds 1 and 2, logged at the end). Status: proposal for review. Scope: how the vertical slice (`kingdom` vs `clans` on the Greenvale map,
1v1 vs AI) and the shared and neutral layer look and sound. Later factions (`sylvan`, `deathless`) inherit every global rule here and
add their own palette, clause, frame inlay, voice and music sections.*

**Read with:** `docs/research/ip-safety.md` (§0, §2.2, §2.4, §2.5, §2.8, §3.2), `docs/research/gameplay-mechanics.md` (§11, §13),
`docs/research/README.md`, `docs/research/visual-art-direction.md` (§1.3, §3, §7), `docs/research/audio-direction.md` (§3, §4, §8),
`docs/research/ai-asset-pipeline.md` (§2.2, §4), `docs/design/factions/kingdom.md`, `docs/design/factions/clans.md`,
`docs/design/neutrals.md`, `docs/design/rules.md` (§4.5, §17.3) and the two juice specs in `docs/design/juice/`.

**What this document owns, and what it supersedes**

| Topic | Authority |
|---|---|
| Names, rosters, numbers, lore | The faction docs, `neutrals.md` and `rules.md`. This bible never renames anything |
| How every asset looks (style, palette, team colour, silhouette, prompts, terrain, UI art) | **This bible.** It replaces the faction bullets of visual §7.1 (the two retired working names) and the prompt kit of visual §7.3 for all generation from now on |
| HUD widget art (chassis and inlays, console layout, the day/night indicator, button states and corner layout, portrait plate, glyphs) | **This bible is the single owner** (§7). Juice HUD-04, HUD-07, POR-01, NTF-05 and rules §18.5 describe motion and timing on top of it; where they describe a look that differs, §7 wins and §13 lists the edit |
| How every asset sounds (voice, line counts, SFX list, music) | **This bible.** It replaces the Wardens/Thornborn lines, casting and UI sounds of audio §3.2–§3.4, the level-up prompt (audio §4.4 #15) and the six music prompts (audio §4.5) |
| When an effect or sound fires, its timing, its trigger rules and its mix priority | The juice specs and audio §3.5 (buses, caps). Voice triggers (debounce, annoyed, warcry) are **juice AUD-03 only**. This bible supplies the content they trigger |

**Compliance note.** This document contains no name from the ip-safety §2.1 list, no line or paraphrase from the reference game, and no
artist, composer, studio or voice-actor name. It passes `python3 tools/ip/check_banned_terms.py docs/design/art-and-audio-bible.md`, so
every prompt block can be copied verbatim into `tools/prompts/` (a folder the checker scans). The game we are evoking is called **"the
reference RTS"** throughout. Look-alike risks are described by their visual traits (for example "closed great helm with a kite shield"),
never by name.

---

## 0. At a glance

| Topic | Decision |
|---|---|
| **Global style** | "Storm-lit Heroic Diorama": chunky heroic forms built to be read from a −56° camera, light painted into the colours, quiet terrain, loud units, and only VFX allowed to bloom (§1) |
| **Kingdom look** (Brennmark) | Burgundy and ivory masses, dark bronze and blackened iron accents. Kettle-hat discs, tall pavises, flails, hook-guns, wagons. Half-timber, lime plaster, onion domes, folk-painted wood (§2.1, §4.2) |
| **Clans look** (the Tormai; the UI never says "Clans") | Dark ink-teal and saffron felt, warm polished bronze, ash-grey stone-coloured skin (a warm, near-neutral grey, never blue) with pale hail-speckles, heavy tuskless jaws. Cones and streamers over flat lamellar flaps. Low domes and carved masts (§2.2, §4.3) |
| **Neutral look** | Creeps carry no team colour and use palettes that belong to neither army. Rundling traders in brass, sage and cream (§2.3) |
| **Team colour** | Our own 12 colours in our own order (every one at least ΔE 20 from the reference RTS's player colours), with light and dark ramps, on 10–15 % of each unit's visible silhouette, keyed as pure magenta `#FF00FF` in concept art. Automatic assignment follows a **preferred list per faction** that never hands the kingdom Royal Blue, Cornflower or Gold, or the clans Crimson or Violet (the reference races' trade-dress pairings), nor a faction its readability-conflict colours. The slice default is **kingdom Emerald vs clans Royal Blue**; players may still pick any free colour by hand (§2.4, §3) |
| **Prompts** | One fixed `STYLE_SUFFIX_V1` (a `_V2` without genre words is A/B-tested, §5.2), one fixed clause per faction plus the canonical kingdom emblem clause `EMBLEM_KINGDOM_V1`, one template per asset class (14 classes), and a **positive counter-clause** inside every subject for each look-alike risk. Every image model we use is prompt-only (schemas checked 2026-10-17), so `NEGATIVE_V1` and the `NEG_*` lists are review checklists, never pasted into prompts. 3–5 of our own approved images serve as style anchors, one per faction for units (§5) |
| **Terrain** | A Greenvale ladder of 7 tiles (scree, cracked earth, dirt, cart road, grassy dirt, meadow, thick meadow), drystone cliffs and painted water, all inside the terrain saturation budget (§6) |
| **UI** | The genre layout is kept, including one continuous bottom console; the art is ours. Four translucent plates sit on a low-opacity band that joins them into one strip, on a shared plain dark chassis with faction inlays on the rims only: kingdom carved burgundy-stained oak with dark bronze rivets, clans stitched ink-teal felt over lattice-wood with bronze studs. Autocast is a steady accent bar plus a looped-arrow badge, never marks or lights circling the button (§7) |
| **Day/night indicator** | The **Horizon Ribbon**: a flat horizontal strip of painted hills over which a sun token, then a moon token, travels, with a golden-hour rim, a dusk/dawn clunk and a day tally. Never a sphere, orb, globe or round clock face (§7.5) |
| **Cursor** | A shared arrow family with a small faction ornament on the tail; targeting reticles match the order markers. Never a hand or gauntlet (§7.6) |
| **Fonts** (all SIL OFL) | Alegreya Sans (body and numbers), Alegreya SC (headings), Grenze Gotisch (kingdom display), Philosopher (clans display) (§7.7) |
| **Voices** | Kingdom: deadpan guild tradesfolk in crisp, neutral English. Clans: formal, courteous menace with a throat-hum "Hm-hm" (Ready, Annoyed and advisor lines only). Acks are snappy for every speaker (What and Yes at most 4 words at ≥ 3.0 words/s; Attack at most 4 words at ≥ 2.8); weight comes from pitch and formant, not slowness. No real-world accent imitation. The word "poke" is banned from every line (§8) |
| **Line counts** | Worker 21, infantry or ranged 19 (one standout per faction 21; the Pavisier 20 for its two-way toggle), caster 21, siege crew 17, hero 31, advisor 19. Slice: **371 recorded lines** plus non-verbal death and effort sets (§8.2) |
| **SFX** | 217 Seed Audio jobs specified, 143 of them P0 for the slice: a swing × material combat matrix, per-faction UI, order and construction sets, every slice basic attack, ability, creep cast and item (recalls, wards, reveals, the Signal Shell and power-ups audible to the enemy), the key buildings' select sounds, Greenvale ambience and creep vocals. Our signature level-up cue is bells into a singing bronze bowl (§9) |
| **Music** | 3 tracks per faction, a menu theme, a victory and a defeat stinger per faction that crossfade into a 75 s end-screen bed, and a short match-opening cue per faction, all ElevenLabs Music with `force_instrumental: true`. Kingdom: a village band gone to war. Clans: frame drums, gongs, two-string fiddle and overtone drone (§10) |

**The twelve rules of this bible**

1. **Read from above first.** Design and judge every asset from the game camera (−56° pitch, 25.8 m) at 64 px, not from a front view.
2. **Identity lives in the upper third**: hat, helmet, shoulders, weapon head, roof crown.
3. **Two big colour masses plus team colour** per unit. A third value (metal or skin) for accents only.
4. **Bigger is clearer.** Hands, weapons, hats and shoulders are 1.5–2× realistic; concepts exaggerate a further 1.3× because image-to-3D thins small parts.
5. **Paint the light; never simulate shine.** Roughness 1, metallic 0, specular off, highlights painted into the albedo.
6. **Terrain is the quietest layer, units the loudest, VFX the only thing above HDR 1.0.**
7. **Team colour is for ownership only.** Never use it for spells, particles or generic decoration.
8. **Every faction differs from its nearest reference race on silhouette, palette, material, culture, names and voice** (ip-safety §3.2). This bible's checklists enforce the visual and audio axes.
9. **No banned token anywhere in a generation request**, negative prompts and filenames included (ip-safety §2.8). Describe qualities, never analogies.
10. **Every voice line is ours.** Character comedy only; no pop culture; no reference-game line or paraphrase; no "poke".
11. **Every sound and melody is ours.** No reference-game motif, no "remake", no composer name in a prompt.
12. **Log everything** in `docs/asset-ledger.md`: service, model, job id, full prompt and negative, seed, references, reviewer, squint-test result and the human edits made afterwards.

---

## 1. Global visual style

### 1.1 Direction statement: "Storm-lit Heroic Diorama"

The world is a painted tabletop diorama seen from a high three-quarter camera: chunky, hand-painted, saturated heroic fantasy, with
modern atmosphere that the reference RTS did not have.

| # | Rule | How we apply it |
|---|---|---|
| 1 | **Chunky heroic forms** | Head about 1/4 to 1/5 of body height. Hands, forearms, shoulders, hats, boots and weapon heads 1.5–2× realistic. Short thick legs, broad torsos, tight waists |
| 2 | **Upper-third identity** | Every unit's read is in its top third (§4 lists each one). Kingdom: brim discs. Clans: cones and streamers |
| 3 | **Big simple shapes** | No detail smaller than 1/32 of the texture width. "Bigger shapes, fewer dots" |
| 4 | **Colour blocking** | 1–2 major masses + team colour + 1 accent. Value grouping: dark legs and base, mid body, light head, shoulders and weapon |
| 5 | **Painted light** | A soft top-lit gradient, painted ambient occlusion and painted metal highlights in the albedo. No normal or specular maps on units |
| 6 | **Hierarchy by saturation and value** | §1.4. Terrain ≤ 45 % saturation, units ≤ 85 %, team colour ≥ 90 % |
| 7 | **Atmosphere (our twist)** | Drifting cloud shadows, wind sway on foliage, a team-colour rim light on units, emissive window and rune glow at night |
| 8 | **Toy-soldier motion (our twist)** | Hop-and-bob walks, lean into movement, squash and stretch on attacks; weapons are separate pivoting meshes (juice combat §3–§4) |
| 9 | **Painterly, never PBR** | One shared uber-shader (wrap-Lambert or a soft 2–3 band ramp). Grit is painted (chips, scratches as colour strokes), never simulated |
| 10 | **Readable at night** | Night is tinted blue and lit by windows, torches and team rims. It is never darkened to black |

### 1.2 Camera and readability constants

| Constant | Value | Source |
|---|---|---|
| Pitch / default distance / zoom range | −56° / 25.8 m / 18.75–35.2 m | README §1 |
| Vertical FOV | 55° (`KEEP_HEIGHT`) | README §1 |
| Default view | About 18 × 18 tiles (14 × 18 above the HUD) | README §1 |
| Minimum on-screen height at default zoom, 1080p | Worker ≥ 28 px, infantry ≥ 40 px, hero ≥ 52 px, large unit ≥ 60 px. **Measured** as the screen-space bounding-box height of the rendered unit, from the feet to its topmost pixel including hat and weapon, at screen centre, default zoom, 1080p. (A standing height alone projects at only ≈ 22.5 px/m there: 40.2 px/m × cos 56°.) Verify on the first rendered Pavisier, Hodman and Wheel Marshal; if a bounding box still fails, raise the class minimum heights in §1.3 to worker ≥ 1.3 m, infantry ≥ 1.75 m, hero ≥ 2.3 m | Visual §4.2, scaled by class height |
| Silhouette test size | 64 px flat-black thumbnail rendered from the game camera | ip-safety §3.2 axis 1 |
| Depth fog | Biome sky colour, from 32 m to 90 m | Visual §7.5 |

### 1.3 Scale and budgets (both slice factions and the neutral layer)

1 tile = 2 m; pathing cells are 0.5 m (`architecture.md`). **Buildings are sized by footprint first, then height**, so a building is
never taller than it is wide (towers excepted) and halls dwarf units the way the genre's big halls do (a hall about 3.5× hero height
across, which shapes wall-offs and the "big hall" read).

**Footprint decision (decided 2026-10-19; §13 #10 lists the table edits each owner makes).** **Halls 16×16 cells (8 m)**,
production, altar, shop and research buildings **12×12 (6 m)**, supply **8×8 (4 m)**, towers **4×4 (2 m)**: the reference RTS's
hall : barracks : farm : tower ratio of about 4 : 3 : 2 : 1, which gives the genre's base read (a big hall, farm-sized wall-off
blocks, a mine that dominates its expansion). This matches research README §2 ("Hall (8×8 m footprint)"), the 8 m hall pads that
slice-plan §1.2 reserves, and both slice halls, already processed at `--width 8` (ledger #24). A smaller simulation footprint under these
meshes would let units clip through walls, so **the sim footprint and the mesh width are the same number**. Heights follow
height : width ≈ 0.9–1.0. The 10×10-cell fallback is retired.

| Class | Kingdom | Clans | Neutral | Footprint (cells) | `process_model --width` | Height | Tris | Texture |
|---|---|---|---|---|---|---|---|---|
| Worker | Hodman | Yurtwright (10 % taller people) | — | — | — (`--height`) | 1.2 m / 1.4 m | 1.5–3k | 512² |
| Infantry, ranged, caster | Pavisier, Hookgunner, Linden Sister | Grappler (1.9 m), Javelineer, Gustcaller | Sootcoats, Fieldkeeper (1.7 m) | — | — | 1.6–1.9 m | 2–4k | 512² |
| Hero (1.25× the faction's tallest slice infantry; §4.1 area check) | Wheel Marshal, Firewright | the Uncut, Skymirror (2.35–2.4 m: 1.25 × the 1.9 m Grappler) | Rat-Piper [SLICE+] | — | — | Kingdom 2.1–2.3 m; clans 2.35–2.4 m | 4–8k | 1024² |
| Wheeled siege | Bombard Wagon (2.6 m long) | Sling-Cart (2.4 m long, arm 2.8 m up) | — | — | 2.6 / 2.4 (length) | 1.4–2.8 m | 2–4k (bpy) | 1024² atlas |
| Large creep | — | — | Drystone Walker, Menhir Elder | — | — | 2.4–3.0 m | 1–3k (bpy slabs) | 512² stone |
| Supply | Croft | Home Yurt | — | 8×8 (4 m) | 4 | 3–3.5 m | 2–4k | 1024² |
| Tower (exempt from the ratio) | Lookout → Gun Tower | Bow-Mast | — | 4×4 (2 m) | 2 (base) | 6–8 m | 2–4k | 1024² |
| Production, altar, shop, research | Drill Yard, Timber Yard, Foundry, Oath Hall, Collegium, Wainwright Yard, Curio Cabinet | Grapple Yard, Casting Pit, Naming Stones, Mirror Yurt, Tea Tent | (neutral row below) | 12×12 (6 m) | 6 | 5–6 m (altar and shops 4.5–5.5 m) | 4–8k | 1024²–2048² |
| Hall, by tier | Moot Hall → Walled Burg → Crown Burg (*later*) | Shell Hall → Banner Shell → Sun-Gong Shell (*later*) | — | 16×16 (8 m) | 8 | T1 6.5–7 m; T2 at most +15 %; T3 at most another +15 % (§4.2, §4.3; T2 production rule in §5.5 T4) | 6–12k | 2048² |
| Neutral buildings (sync neutrals §5.1, slice-plan §1.4; §13 #10) | — | — | **Gold Seam ≥ 12×12 (6 m)**, so it reads at least barracks-sized beside an 8 m hall; **Weighstall 12×12** (its 7 m balance beam is exempt from the height ratio); **Coaching Inn 12×12** (half-timber kit in neutral browns); Hiring Fair and Contraption Barn 12×12 (*later*); **Hale Spring 8×8**; Dewstone, Lucky Barrow, Beacon Cairn 4×4; Twin Milestones 2×2 each | as listed | 6 (Seam, stall, inn); 4 (spring) | Seam cliff 3–5 m; stall 4.5–5.5 m; inn 5–6 m; spring ≤ 2 m | 3–8k | 1024² |
| Tree | — | — | Greenvale oak, linden, hazel | as `architecture.md` | — | 5–7 m; **every tree that blocks pathing and sight has its crown top ≥ 4.5 m** (hazel is a 4.5–5 m "tall coppice", §6.4) | 0.5–1.5k + 2 LODs | 512² atlas |
| Doodad | — | — | Rocks, walls, hedges, reeds | — | — | ≤ 1.5 m | 100–800 | shared 1024² atlas |

The T1 hall leaves its **top third of height free** for the tier crowns: T2 may add at most 15 % height and T3 another 15 %, so the
T3 crown (§4.2, §4.3) is the tallest shape in a base.

### 1.4 Value and saturation hierarchy (HSV, measured on albedo after post-processing)

| Asset class | Value | Max saturation | Notes |
|---|---|---|---|
| Terrain ground | 30–65 % | 45 % | Macro variation only. Greenvale meadow may go to 52 % if screenshots read grey (§6.1) |
| Cliffs and rocks | 25–60 % | 30 % | Cool neutral, lighter painted top lip |
| Trees and foliage | 25–70 % | 60 % | Vertical gradient: dark trunk base, light canopy top |
| Buildings | 20–85 % | 65 % | Roofs carry the faction hue |
| Units | 10–95 % | 85 % (faction cloth ≤ 70 %) | Highest contrast in the scene. Kingdom burgundy `#7B1E2E` measures 76 %: the faction LUT clamps it to 70 % |
| Team-colour areas | 50–90 % | 90 %+ | Must survive the night grade |
| UI chrome | 8–60 % | 40 % | Chrome is dark and quiet so icons and numbers lead |
| VFX | Emissive, HDR > 1.0 | n/a | The only things that bloom |

### 1.5 Light, grade and time of day

| Phase (game clock) | Key light | Ambient | Grade | Extras |
|---|---|---|---|---|
| Day (06:30–17:30) | Sun `#FFF0D8`, energy 1.0–1.15, elevation 50–55°, from screen lower-left | `#9DB3D6`, 0.45–0.6 (key:ambient 2:1–2.5:1) | Greenvale day LUT, saturation 1.05–1.12 | Cloud shadows 0.25–0.35, scrolling about 1 m/s |
| Dusk and dawn (±30 game-minutes around 18:00 and 06:00) | Sun `#FFB878`, elevation 12–20° | `#8A86B8`, 0.5 | Lerp between day and night LUTs | Dawn and dusk stingers (§9.7); windows light at 17:45 |
| Night (18:30–05:30) | Moon `#8EA6FF`, energy 0.35–0.45 | `#3B4A80`, 0.45 | Greenvale night LUT (blue, never black) | Windows and torches `#FFB86B` (emissive above 1.0), team rims, clans mirrors catch moonlight, Cairnwake glyphs `#E8E29A`, fireflies, cloud shadows 0.1 |

Tonemap Linear or Reinhard (white about 1.5); glow threshold 1.0–1.2. No SDFGI, VoxelGI or volumetric fog. **Every rule must also hold
on the Compatibility renderer** (README §2).

### 1.6 Surfaces and texel density

- **Units:** about 256 px/m; one 512² atlas per unit (1024² per hero); weapons and big props in their own small atlas so they can pivot.
- **Buildings:** 128–160 px/m. Procedural kit parts share tileable material swatches (§5.5 T5).
- **Terrain:** 128 px/m, so one 512² tile texture covers 4 m (2 × 2 terrain tiles) in world-space UVs (§6).
- **Painted, not simulated:** albedo carries a top-lit gradient (lighter by 10–15 % value at the top of each form), painted AO in creases,
  and painted highlight strokes on metal. Grain and noise are removed in post (§5.7).
- **No ink outlines.** Silhouettes separate through value grouping, the shader's world-space vertical gradient and the team-colour rim.

### 1.7 VFX colour language (spell colours, `fx.spell_color`)

Team colour never appears in generic particles (juice economy §2.5). Each faction's magic has its own hue family, chosen away from the
reference races' signature effects (no fel green, no frost blue, no violet shadow, no blue lightning).

| Token | Hex (HDR multiplier) | Used by |
|---|---|---|
| `K_EMBER` | `#F08A2A` (×1.8–2.5) | Kingdom fire: muzzle flash, fuses, Naphtha Flask, Firewright, night windows |
| `K_LINDEN` | `#DDEFB0` core, `#9DBF5A` edge (×1.4) | Wheel Marshal's Linden Balm; the Linden Sister (Herb Poultice, Linden Wreath). Drifting blossom petals, never light beams |
| `K_CADENCE` | ivory `#EDE2C8`, non-emissive, α 0.35 | Wheel Marshal's Measured Cadence: a flat drum-pulse ring on the ground, one beat every 1.5 s. Never a glow, a halo or light from above |
| `K_WAGON` | burgundy `#7B1E2E` and ivory `#EDE2C8` paint, oak `#5A3A22`, iron `#3D4046`; **non-emissive** | The Wagon Ring: physical painted wagon boards and spoked wheels that slam down into a barricade ring and are carted off in a dust puff when it ends. Never ghostly, translucent or glowing |
| `K_WHEEL_GHOST` | `#F3E6C4` (×1.6) | **Oath Hall revive only** (no ability uses it) |
| `K_SMOKE_RUE` | grey-green smoke `#8E9A7A` with ember flecks `#F08A2A` | Linden Sister's Smoke of Rue: a cracked clay censer and bitter herb smoke rolling outward |
| `C_SUNGLINT` | `#FFD27A` (×2.0–3.0) | Skymirror's Sunglint, mirror flashes, Sun-Gong |
| `C_DUST` | `#C9A46A` (×1.2) | Dust Veil, Wind at Your Back, Through the Tall Grass, Gustcaller bolts |
| `C_MOON` | `#C8D4E8` (×1.6) | Moonglint, Hail-Swifts, Swallowed Sun's rim |
| `N_SOOT` / `N_EMBER` | `#3E3935` / `#E07A2A` | Sootcoat smoke and coals |
| `N_LICHEN` | `#E8E29A` (×1.4) | Cairnwake glyphs, Ley Pulse |
| `N_LANTERN` | `#FFC46B` (×1.6) | Tattiebogle turnip lanterns: light through a few randomly drilled holes, never eyes, a mouth or any face |
| Shared heal / buff / debuff | heal `#B8FFB0`, buff `#FFE3A0`, debuff `#B07AD8` at 0.6 alpha (non-emissive) | Generic status rings only, always paired with an icon so colour is never the only cue |

---

## 2. Palettes

All hex values are **albedo targets** before team colour and before the biome LUT. The post-processing LUT (§5.7) pulls generated images
toward these. Faction docs remain the origin of the core values; this section adds the UI and VFX tokens and fixes small conflicts.

### 2.1 Kingdom (Brennmark)

| Role | Name | Hex | Where |
|---|---|---|---|
| Primary cloth / roof | Burgundy | `#7B1E2E` (LUT-clamped to 70 % saturation) | Hoods, aprons, roof tiles, caparisons |
| Primary light | Ivory linen | `#EDE2C8` | Gambesons, plaster, linen covers, the emblem wheel |
| Ivory shadow | Oat | `#C9B994` | Painted shadow of ivory |
| Metal 1 | Dark bronze | `#6E4A26`, highlight `#B07F3E` | Domes, barrels, buckles, the hub coal of the emblem (no flame shape, kingdom §1.2) |
| Metal 2 | Blackened iron | `#3D4046`, highlight `#7E848C` | Kettle hats, plate, chains, wheel rims |
| Wood | Dark oak | `#5A3A22` | Timber frames, wagons, gunstocks, pavise backs |
| Accent | Straw | `#C9A85A` | Worker hats, thatch, rope, hods |
| Accent (small) | Linden green | `#7E9A4A` | Wreaths and herbs only |
| Accent (VFX) | Ember | `#F08A2A` | Fire, sparks, night windows |
| UI chrome | Stained oak `#3A1E1A`, rail highlight `#6B3A2E`, rivet bronze `#8A5E2E`, iron strap `#2E3034`, folk paint ivory `#E6D8B8` | | §7.2 |

**Forbidden for the kingdom:** blue (except team colour), gold-yellow trim, polished silver, white-and-gold livery, any lion, eagle or
winged-beast heraldry, glowing hands or beams of light.

### 2.2 Clans (Tormai)

| Role | Hex | Where |
|---|---|---|
| Ink teal (primary felt) | `#1E5A60` dark / `#2F7E7E` mid | Coats, yurt walls, banners. Dark and green-leaning, **never violet** |
| Saffron (secondary felt) | `#E0A030`, ochre `#B7772A` | Trim, sashes, door hangings, the emblem disc |
| Warm bronze | `#A8743A`, highlight `#D9A55E` | Helmets, gongs, mirrors, cauldrons, studs |
| Verdigris (sparingly) | `#5FA08E` | Old bronze only |
| Ash-grey skin ("weathered granite") | `#77746F` mid, `#585551` shadow, speckles `#D2CEC6` (hue ≈ 37°, saturation ≤ 8 %) | Tormai skin. A warm, near-neutral grey: never blue, blue-grey or teal. The faction LUT clamps it (§5.7) and prompts never say "blue" (§5.4) |
| Lattice-wood | `#7A4A32`, shadow `#4E2E20` | Yurt lattice, masts, carts |
| Tortoise shell | `#C9A46A` plates, `#8A6A44` seams | Shell Hall |
| Felt cream (accent only) | `#E9DDBF` | Never a large mass |
| Hair | `#1C2230` | |
| UI chrome | Felt teal `#173E42`, stitch saffron `#D49A36`, stud bronze `#A8743A`, ochre-washed lattice `#B7772A` (highlight `#C9A46A`), gong rim `#C68E4C`. Red-brown never appears on UI art | §7.2 |

**Forbidden for the clans:** green, olive, red-brown, blue, blue-grey or teal skin (blue skin plus a thrown-spear unit is the
reference forest-troll read); tusks or fangs; pointed ears; spikes, bones, skulls, horns or fur; red-brown
leather as a main mass; violet or purple anywhere; blue or teal glow; lightning.

### 2.3 Neutral and creeps (Greenvale)

Creeps never carry team colour, and their palettes stay off both slice factions and off the reference races' palettes (neutrals §2.0).

| Family / object | Palette | Emissive (night) |
|---|---|---|
| Sootcoats | Soot `#2E2B29`, oilcloth ochre `#A07A3A`, faded moss `#5E6B3E` | Hood-smoke embers `#E07A2A` |
| Tattiebogles | Straw `#C9A85A`, sacking `#B9A27E`, madder patch `#8E4A3A`, woad patch `#5E6E8A`, undyed `#CDBE9A`, crow black `#1F1E24` | Turnip lanterns `#FFC46B`, the light showing through a few small, randomly drilled holes, never arranged as a face (neutrals §2.1 G2) |
| Cairnwakes | Drystone `#7D766A` / `#5E574E`, lichen `#A8B04E`, moss `#4F7A2E` | Cup-and-ring glyphs `#E8E29A` |
| Rundlings and the Weighstall | Scales `#7A5A3A` edged `#B08A5A`, brass `#B8913A`, awning cream `#E8DCC0` and sage `#7E9A6E` | Stall lantern `#FFB86B` |
| Gold Seam | Gold-veined rock `#8A7A5A` with veins `#D8B048`, timber `#5A4630` | Two lanterns `#FFB86B` |
| Hale Spring | Water `#5AA3A0`, moss ring `#5B7A43`, flume wood `#6A5038` | Warm sparkles by day only |
| Loot bundle (**final values**; juice ITM-01's tokens, adopted) | Oilcloth `#6E6248`, twine `#C9B48A`, red wax seal `#B8322A`. The dark oilcloth (value 43 %) sits below every main Greenvale ground tile (meadow 60 %, dirt 55 %, road 63 %; ΔE 11–34, against 7–25 for the earlier lighter oilcloth), so the parcel reads as a dark block with a light twine cross and a bright seal | Glint every 3 s |
| Power-up ground props (neutrals §1.8, §4.3) | Horseshoe nail iron `#5E6066` with a warm highlight `#9A9A98`; juggling ball undyed `#CDBE9A` and ochre `#A07A3A` patches; riddle knot hemp `#B9A27E` on an oak toggle `#5A4630`; berries `#C2343A` on a leaf `#5F7A43`; purse leather `#7A5A3A`; **Fair-Day Rosette**: a faded prize-ribbon rosette, a pleated undyed-cream `#CDBE9A` ribbon ring round a madder-red `#8E4A3A` centre with two short madder tails; tally-stick hazel `#9A7A52` with dark notches. **No book anywhere among item props** (a book that grants attributes mirrors the reference tome family) | A soft bob and a 1 s glint, so they read apart from the loot bundle |
| Recall items in use | Way-Home Horn (kingdom; renamed 2026-10-19, §13 #26): a small bright brass post-horn `#B8913A`. Way-Home Felt (clans): a rolled ink-teal felt `#1E5A60` with saffron ties `#E0A030`. Homing Pigeon: grey-white pigeon `#B8B8B0` | A rising ring of the faction's colour at the hero's feet during the 5 s channel (`K_EMBER` sparks / `C_DUST` motes; neutral white feathers), visible to the enemy |
| Reveal items in use (never a thrown powder, dust cloud or puff) | **Tailor's Chalk** (kingdom shop): the hero snaps a chalked tailor's line on the ground, which leaves a 9 m ring of chalk dashes `#F2EEE4`; revealed units show white **tacking-stitch outlines** (dashed `#F2EEE4`, 2 px) for the 15 s. **Tattle-Burrs** (Weighstall): dry burdock burrs `#6A5A3A` strung with tiny tin bells `#B8B8B0`; each revealed unit carries two or three burrs and a bell glint while it moves. **Signal Shell** (Bombard Wagon): a flare that hangs over the area, `K_EMBER` core, slow-falling sparks | Chalk and stitches non-emissive; the flare and the bell glint emissive |
| Coaching Inn (*The Muddy Lantern*) | Half-timber kit retinted to neutral browns: plaster `#D9CCAE`, timber `#6A5038`, roof slate `#5E574E` (never burgundy), stable door `#5A4630` | The hanging lantern sign `#FFC46B` and two windows |
| UI chrome (menus, shop, neutral tooltips) | Linen `#D9CCAE`, ash wood `#B8A07A`, pewter `#8E9196`, sage border `#7E9A6E` | |

### 2.4 Team colours

Our own 12 colours **in our own order**. The genre needs a dozen hue-spaced team colours (functional, ip-safety §2.4), but the reference
RTS's lobby set is a fixed list in a fixed order that its players know by heart, so we reuse neither its values nor its order beyond
"red, then blue". Every base colour is at least **ΔE 20** (CIE76) from every reference player colour and meets the 50–90 % value rule
(HSV V) of §1.4. Light and dark ramps are `light = c + (1 − c) × 0.40` and `dark = c × 0.55`. The shader multiplies the masked greyscale
by the ramp (visual §7.5). `tools/ip/value_echo_reference.json` → `team_colours` fails the build if any base drifts within ΔE 15 of a
reference player colour.

| # | Name | Base | Light | Dark | V | Nearest reference player colour (ΔE) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Crimson | `#D8232A` | `#E87B7F` | `#771317` | 85 % | red (27.2) | Kingdom readability skip; clans trade-dress skip |
| 2 | Royal Blue | `#285DE6` | `#7E9EF0` | `#16337F` | 90 % | blue (32.3) | Clans first choice; kingdom trade-dress skip |
| 3 | Gold | `#E6BB17` | `#F0D674` | `#7F670D` | 90 % | yellow (33.8) | Kingdom trade-dress skip; clans readability skip (light ramp) |
| 4 | Emerald | `#2EAE3A` | `#82CE89` | `#196020` | 68 % | green (22.7) | Kingdom first choice |
| 5 | Tangerine | `#E35F18` | `#EE9F74` | `#7D340D` | 89 % | orange (20.7) | Clans readability skip |
| 6 | Violet | `#7A2FD0` | `#AF82E3` | `#431A72` | 82 % | blue (26.3) | Clans trade-dress skip |
| 7 | Cornflower | `#5A92E6` | `#9CBEF0` | `#32507F` | 90 % | light blue (26.5) | Kingdom trade-dress skip |
| 8 | Lime | `#A8D41E` | `#CBE578` | `#5C7510` | 83 % | yellow (30.5) | Replaces a brown: every brown sat within ΔE 14 of the kingdom's dark bronze or oak and the clans' bronze, so it failed the swap test on both factions |
| 9 | Turquoise | `#14B8A6` | `#72D4CA` | `#0B655B` | 72 % | teal (22.7) | Clans readability skip |
| 10 | Coral Rose | `#E0507A` | `#EC96AF` | `#7B2C43` | 88 % | pink (25.9) | Kingdom readability skip; clans trade-dress skip |
| 11 | Pewter | `#B0A6D6` | `#D0CAE6` | `#615B76` | 84 % | light blue (22.8) | Low saturation by nature: gets a 1.3× team-rim boost; clans readability skip |
| 12 | Forest | `#2A8C4A` | `#7FBA92` | `#174D29` | 55 % | dark green (26.4) | Clans readability skip |

Closest pair inside our own set: Crimson and Tangerine (ΔE 26.7); every other pair is ΔE ≥ 27.

**Slot assignment (lobby rule; automatic assignment only).** Each player, in slot order, gets the **first colour on its own faction's
preferred list that no other player holds**. The lists leave out two kinds of colour (the **default-skip set**): the faction's
**readability-conflict** colours and its **trade-dress** colours, the pairings that would reproduce the reference franchise's canonical
look in every default match, dev clip and playtest recording (humans in blue against brute warriors in red; a blue/white/gold kingdom;
teal with violet).

| Faction | Preferred list (automatic) | Default-skip set (never assigned automatically) |
|---|---|---|
| `kingdom` | Emerald, Tangerine, Turquoise, Lime, Violet, Forest, Pewter | Trade dress: Royal Blue, Cornflower, Gold (the "gold-yellow trim" §2.1 forbids). Readability: Crimson, Coral Rose |
| `clans` | Royal Blue, Cornflower, Lime, Emerald | Trade dress: Crimson, Coral Rose (a red-pink streamer still reads as the reference warrior race's red), Violet. Readability: Turquoise, Forest, Gold, Tangerine, Pewter |

Emerald leads the kingdom list because Tangerine sits close to the kingdom's own ember-orange VFX (`K_EMBER`). In the slice (player 1
kingdom, player 2 clans) the default is **kingdom Emerald against clans Royal Blue**: protan and deutan viewers separate that pair
(unlike Crimson against Emerald), and both passed the swap tests below. If every colour on a list is taken (large lobbies only), the
player gets the lowest-numbered free colour and the fixes below apply. **Players may still pick any free colour by hand**, including a
skipped one; manual choice is never blocked. `src/systems/player_state.gd` does not implement this yet (§13 #24).

**Swap test results (§3.4, base colours against the faction masses).** Kingdom: every colour ΔE ≥ 33 (nearest: Gold to straw 33.1, Coral
Rose to burgundy 33.7). Clans: every colour ΔE ≥ 27 (nearest: Turquoise to mid teal 27.2) except **Gold to saffron (19.3)**, which passes with its light
ramp (`#F0D674`, 26.5). Against the new ash-grey skin (`#77746F`, 2026-10-19) every colour is ΔE ≥ 36 (nearest: Pewter 36.3; it was 28.7
against the retired blue-grey). Re-run on rendered units at day and night grade before 3D sign-off.

**Conflicts and fixes** (readability and trade-dress rows both feed the default-skip set; manual picks of any colour stay allowed)

| Faction + team colour | Kind | Risk | Fix |
|---|---|---|---|
| Kingdom + Crimson / Coral Rose | Readability | Team cloth merges with burgundy at night grade | Team areas must be brighter than burgundy (value ≥ 60 %, use the light ramp on the largest panel) and carry a 2–3 px **ivory piping** border painted into the albedo (kingdom §2.2) |
| Clans + Turquoise / Forest | Readability | Team cloth merges with ink-teal felt | Team areas are the **streamer, sash and mantle**, which sit on bronze or skin, not on teal felt; plus bronze piping. Turquoise (value 72 %) and Forest (55 %) stay clear of dark felt (38–49 %) |
| Clans + Gold / Tangerine | Readability | Team merges with saffron and ochre trim | Saffron is trim only (≤ 10 % of the figure); the team panels are larger and use the light ramp |
| Clans + Pewter | Readability | Low-saturation team cloth near grey skin (ΔE 36.3 against the ash-grey skin) | Bronze piping on every team panel that touches skin; the 1.3× rim boost |
| Clans + Violet | Trade dress (default-skip) | Teal-plus-violet is a reference forest-race signature | Never assigned automatically; allowed as a manual pick; **never** used in screenshots, trailers or key art |
| Clans + Crimson | Trade dress (default-skip) | Brute warriors in red against humans in blue is the franchise's canonical pairing | Never assigned automatically; allowed as a manual pick; never in key art |
| Kingdom + Royal Blue / Cornflower / Gold | Trade dress (default-skip) | Blue on the pavise face over ivory linen and dark bronze is the blue/white/gold livery the user ruled out; gold is the forbidden gold-yellow trim | Never assigned automatically; allowed as a manual pick. **Marketing rule:** key art, store screenshots and trailers show the kingdom in Emerald or Tangerine and the clans in Royal Blue (Cornflower as the fallback); never the kingdom in blue or gold, never the clans in Crimson or Violet |
| Any + red/green colour blindness | Accessibility | Crimson vs Emerald; Lime vs Gold | The rim light, minimap shapes and selection rings never rely on hue alone (juice economy §2.6) |

### 2.5 UI palette tokens (shared)

| Token | Hex | Use |
|---|---|---|
| `UI_PLATE` | `#14110E` at 85 % opacity | Console plate fill |
| `UI_TEXT` / `UI_TEXT_DIM` | `#F3E6C4` / `#B9AE96` | Body text |
| `UI_TITLE` | `#FFF1CF` | Tooltip titles |
| `UI_GOLD` / `UI_LUMBER` / `UI_FOOD` | `#FFD23F` / `#9BE36A` / `#FFF1CF` (juice tokens) | Resource numbers |
| `UI_VALID` / `UI_INVALID` | `#46E07A` / `#FF4B3E` | Placement, targeting |
| `UI_UPKEEP` 0 / 30 / 60 % | `#7FD86A` / `#FFC145` / `#FF5A48` | Upkeep label (rules §4.5) |
| `UI_HP` ramp | `#33CC4A` → `#F2CF2E` → `#E8402A` | Health bars (juice combat CMB-29) |
| `UI_MANA` | `#4A8CFF` | Mana bars |
| `UI_XP` | `#E8C25A` | Hero XP bar |
| `UI_COOLDOWN` | `#000000` at 60 % | Cooldown sweep |

---

## 3. Team-colour placement rules

### 3.1 Global rules

1. **Coverage:** team colour fills **10–15 % of the visible silhouette from the game camera** (8 % minimum on workers, 18 % maximum on heroes).
2. **Location:** at least one team area sits in the **upper third** (hat band, plume, streamer, shoulder mantle, roof pennant), so ownership
   reads even when the legs are hidden in a crowd.
3. **Material:** team colour goes on **cloth, felt, enamel or paint**, never on skin, hair, bare metal, wood grain or stone.
4. **Separation:** every team area is bordered by a 2–3 px painted piping in a neutral value (kingdom ivory `#EDE2C8`, clans bronze
   `#A8743A`), so the shader-tinted area never bleeds into a faction colour of similar hue.
5. **Concept key:** in concept images the team areas are **solid pure magenta `#FF00FF`** and magenta appears nowhere else (no pink
   cloth, no purple shadows). The background is never magenta.
6. **Mask extraction** (visual §7.4): pixels with hue 300° ± 15°, saturation > 0.5 and value > 0.35 become the team mask. The albedo there
   is replaced by a luminance-preserving grey (value 0.62 for cloth, 0.55 for enamel), dilated by 2 px, and the mask is stored as a
   separate greyscale map. Any magenta pixel outside the intended areas fails the asset.
7. **Buildings:** team colour on pennants, shutters, bands and hangings only: 6–10 % of the visible area. Roofs keep the faction hue.
8. **Neutrals and creeps:** no team colour at all. Captured neutral objects (Beacon Cairn [SLICE+]) show ownership through a team-coloured
   flame VFX, not their textures.
9. **The team-colour rim light** (`rim_color = team_color × 0.6`, visual §7.5) is always on for units; buildings get it at 50 %.

### 3.2 Kingdom placement

| Asset | Team areas (magenta in concepts) | Upper-third area |
|---|---|---|
| Hodman | Hat band, shoulder sash | Hat band |
| Flail Levy (prop swap) | Kettle-hat plume, shoulder sash | Plume |
| Pavisier | **Pavise face field** (the painted wheel stays ivory), arm sash, kettle-hat plume | Plume, top of the pavise |
| Hookgunner | Kettle-hat plume, arm sash, the barrel's cloth wrap | Plume |
| Linden Sister | Hood lining, apron stripe, collar ribbon | Hood lining |
| Bombard Wagon | Canvas cover stripes, the painted side-board band, wheel-rim paint; crew hat plumes | Cover stripes |
| Wheel Marshal | Cloak, plume, hub enamel of the wheel-shield | Plume, shield hub |
| Firewright | Cloak, chimney-hat band | Hat band |
| Buildings | Swallow-tailed roof pennants, window shutters, the ridge-tile band, the ring under each onion dome | Pennants |

### 3.3 Clans placement

| Asset | Team areas (magenta in concepts) | Upper-third area |
|---|---|---|
| Yurtwright | Felt hat band, back-bundle strap | Hat band |
| Grappler | **Helmet streamer** (long), felt sash | Streamer |
| Javelineer | Hood streamer, sash, javelin bundle wrap | Streamer |
| Gustcaller | Shoulder mantle, streamer ribbons on the staff | Mantle |
| Sling-Cart | Felt sling, rope-wrap on the arm, crew hat bands | Sling |
| The Uncut | Sash, braid ribbon near the bronze weight | Sash |
| Skymirror | Felt shoulder mantle, staff ribbons | Mantle |
| Buildings | The felt band around every dome, banner ribbons, Shell Hall door hangings | Dome band |

### 3.4 Acceptance checks (scripted in `tools/`, run on every concept and final texture)

| Check | Pass condition |
|---|---|
| Magenta coverage | 8–18 % of the figure's non-background pixels; at least one magenta region in the top third of the bounding box |
| Stray magenta | No magenta-hue pixel (saturation > 0.3) more than 3 px outside the intended regions (reviewed on a mask overlay) |
| Team swap test | Render the in-engine unit with all 12 team colours at day and night grade: every colour separates from the faction masses (ΔE ≥ 25 against the nearest faction mass; a conflict-row colour is measured on the ramp its fix prescribes). Albedo baseline in §2.4 |
| Red-team kingdom | Crimson-team Pavisier at night grade is distinguishable from burgundy hood at 64 px (reviewer check) |

---

## 4. Silhouette checklists

### 4.1 Global checklist (every unit, hero and building)

Render a flat-black thumbnail from the game camera at 64 px (units) or 128 px (buildings) and check:

- [ ] The unit's **job** is readable (worker, melee, ranged, caster, siege, hero) without colour.
- [ ] The **faction** is readable without colour: kingdom discs and slabs, clans cones and streamers.
- [ ] The **upper-third read** listed below is present and is the largest single shape.
- [ ] Weapons and big props stand clear of the body (no merged blob) and are at least as big as the torso for heroes.
- [ ] A grey-scale render shows **three value masses** (dark base, mid body, light top).
- [ ] The **job-defining shape** (slab, barrel, flail arc, bundle, staff head) sits in the upper third and **differs per unit**; the
      faction hat may repeat (the kingdom's kettle-hat discs), so two units of one faction side by side differ by that shape, never by
      the hat alone. Worker and caster in particular must part at a glance (worker harass and caster sniping depend on it).
- [ ] **Heroes stand out:** each hero's 64 px flat-black silhouette **area** is ≥ 1.3 × that of the faction's largest slice infantry
      (kingdom: the Pavisier with its pavise; clans: the Grappler).
- [ ] Side by side with its nearest reference-RTS role, a fan would **not** name the reference unit at a glance (ip-safety §2.8 squint test). The reviewer writes the result in the ledger.

### 4.2 Kingdom (Brennmark)

| Asset | Must read as (64 px black) | Must never read as |
|---|---|---|
| Hodman | Wide straw-hat **disc** plus a V-shaped hod on one shoulder | A bare-headed labourer with a pickaxe in a coloured tunic |
| Flail Levy | Kettle-hat disc plus the arc of a swinging flail | A pitchfork militia in caps |
| Pavisier | Kettle-hat disc plus a **tall flat slab** (pavise, 1.1× unit height) | A closed-helm soldier with a kite or heater shield and a broadsword |
| Hookgunner | Kettle-hat disc, a long thin barrel sloped over the shoulder, a forked rest | A short bearded gunner with a backpack and a stubby rifle |
| Linden Sister | Leaf-wreath **ring** on the head, basket hump on the back | A robed priestess with a tall hood and a staff of light |
| Bombard Wagon | A **box on two big spoked wheels** with a fat tube, two small hat discs behind | A mortar on a tripod, or a steam tank |
| Wheel Marshal | A round **wheel-shield disc** with six spokes, a long war-pick, a plume | A hammer-and-book holy knight with huge round shoulder plates |
| Firewright | A tall **chimney-hat column** and a bandolier of round flasks | A slender robed fire mage with floating orbs |
| Moot Hall (T1) | Steep roof, a stepped gable, **one small onion-dome bulb** with a wheel finial; the top third of the height budget left empty (§1.3) | A grey stone hall with a steeple and blue roof |
| Walled Burg (T2) | Adds a stone ground floor, a **ring of parked wagons** as a low wall and a taller dome; at most +15 % height | A castle keep with a curtain wall and a gatehouse |
| Crown Burg (T3, *later*) | Adds a **square clock tower** with a painted astronomical clock face (our own design, kingdom §2.5) and a **double onion dome**, the tallest crown in the base; at most another +15 % | A cathedral spire, a gold-roofed keep or a round clock orb on the roof |
| Croft | Small steep roof, a chimney, a **stork nest** on the ridge | A thatched farm cottage with a windmill |
| Oath Hall | Squat hall with a big iron wheel arch over the door | A temple with a domed altar and columns |
| Drill Yard | A timber longhouse plus a fenced yard with weapon racks and a pavise wall | A stone barracks with a tower |
| Timber Yard | An **open timber shed** over a sawpit (a two-man pit saw on trestles) and a **tall log stack** at one end, built at the tree line | A lumber mill with a big circular saw blade, a waterwheel or a log flume |
| Foundry | A stepped gable plus a tall **brick chimney stack** with a bronze cap | A blacksmith hut with an anvil roof sign |
| Collegium | A **tall narrow guild house** with a little **bell-cote** on the gable and a **walled linden herb garden** at its side | A mage tower, a domed sanctum, floating books or glowing orbs |
| Wainwright Yard | An open shed with a **giant wagon wheel on a pole** | A workshop with gears and a crane arm |
| Curio Cabinet | A **narrow shopfront** whose sign is a giant painted **chest of small drawers** standing on the eaves | A vault with a glowing arcane door, a goblin shack, or a potion-bottle sign |
| Lookout → Gun Tower | A thin timber tower with a roofed platform; T2 adds a parapet and an onion cap | A stone guard tower with arrow slits |

### 4.3 Clans (Tormai)

| Asset | Must read as (64 px black) | Must never read as |
|---|---|---|
| Yurtwright | A tall **peaked felt cone** plus a rectangular lattice bundle on the back | A hunched green worker with a pick and a sack |
| Grappler | A bronze **cone with a long streamer** over a wide flat trapezoid of flaps, plus a mace head | A spiky-shouldered axe warrior with round pauldrons |
| Javelineer | A **broad, stocky** figure with a peaked felt hood over a felt cap, a **vertical bundle of javelins** and a stick arm; small rounded ears and the heavy square jaw | A lean, lanky, hunched, long-armed spear thrower with pointed ears, tusks or a mohawk (squint-test it against the reference RTS's forest-troll spear thrower, not only against a generic orc) |
| Gustcaller | A long robe triangle under a **low rounded felt cap wound with long felt ribbons that stream from its crown**, and the **bronze wind-vane staff head rising ≥ 0.4 m above the head**: the one clans head read with no peak (the tall peaked cone is the Yurtwright's alone) | A wolf-pelted lightning caster; a second tall peaked hat that would match the worker at 64 px |
| Sling-Cart | Two wheels plus a **tall angled throwing arm** with a sling | A rock-hurling catapult made of bones |
| The Uncut | A split coat with a **long braid line trailing to the ground** behind her, ending in a weight; a short straight sabre carried low. **No circular motion in idle or abilities** (clans §2.1, §2.5) | A masked duelist with a topknot and an oversized blade; any spinning figure, whirled braid or dust column |
| Skymirror | A **brow-band mirror pushed up on the forehead** (eyes visible) and a mirror-topped staff | A blind seer riding a wolf; anything covering his eyes at idle |
| Shell Hall (T1) | A low **hex-plated dome** with a gong mast at the door; the top third of the height budget left empty (§1.3) | A spiky hide-and-bone hall with tusks |
| Banner Shell (T2) | Adds **tall felt banners**, a second gong and a lattice gallery; at most +15 % height | A fortress with a palisade of sharpened logs |
| Sun-Gong Shell (T3, *later*) | Crowned with a **giant mirror-gong** on a carved frame above the shell (it flashes at noon; clans §7), the tallest crown in the base; at most another +15 % | A totem pole, a skull-topped spike or a war-drum tower |
| Tea Tent | A **striped saffron and teal yurt** with a big **bronze urn on a tripod** at the door and a few bronze cups on a low table | A potion shop with bottles, a voodoo hut or a hide tent with skulls |
| Home Yurt | A small round dome with a smoke ring and a felt skirt | A burrow mound with spikes |
| Grapple Yard | A round fenced ring beside a long yurt | An arena of skull posts |
| Naming Stones | A ring of rough upright stones carved with hail and wind glyphs, a frame of small gongs beside them; nothing hung on the stones, no faces | A blood altar with spikes |
| Casting Pit | A sunken pit, a cone kiln and stacked logs | A reference-race lumber mill with saw blades |
| Mirror Yurt | A tall dome **ringed by bronze sun-mirrors on tilting posts** (nothing sewn or studded on the felt) | A reference-race caster lodge of skins and skulls |
| Bow-Mast | A tall carved **mast** with a windbreak platform, felt ribbon streamers and a **large recurve bow on a swivel** (prompt it as "laminated recurve bow of wood and bronze", §5.6) | A lookout of lashed logs with skulls; any javelin or spear thrower |

### 4.4 Neutral layer

| Asset | Must read as | Must never read as |
|---|---|---|
| Sootcoats | A **wide conical leather hood** and a rake or billhook | Hooded rogues with daggers and masks |
| Fieldkeeper / Crowherd | Crossed-pole frame, sack head, pitchfork; a crow on the head while asleep | A pumpkin-headed or machine-bodied scarecrow |
| Cairnwakes | **Stacked flat slabs** with visible gaps; menhir head with cup-and-ring marks | A rounded boulder man with a glowing core |
| Weighstall | A **giant brass balance beam** (about 7 m) over a striped stall | A goblin-style shack with rockets |
| Gold Seam | A low, square, **timber-framed adit** cut into a short **layered cliff** with a thin bright quartz-and-gold strata line; a **windlass headframe** on the lip; a spoil heap; a wooden sluice; two night lanterns (neutrals §5.2, §10.2) | A free-standing rock mound with gold nuggets heaped at the door; a mine cart or rails; a haunted or vine-wrapped mine |
| Hale Spring | A spring pool fed by a **log flume with a tiny waterwheel** | A glowing stone fountain |
| Coaching Inn (*The Muddy Lantern*) | Two storeys of half-timber in neutral browns, a **stable arch** with a horse trough, two smoking chimneys and a great **hanging lantern sign** | A thatched tavern with a foaming-mug sign, or the kingdom's burgundy roofs |

### 4.5 Look-alike traps (applies to every new design)

| Trait combination to avoid | Why |
|---|---|
| Blue/white/gold livery + lion emblem + kite shield + steepled stone halls | The reference human kingdom's signature set |
| Green or brown skin + tusks + spiked pauldrons + red-brown leather + hide-and-bone huts | The reference warrior race's signature set |
| Violet-skinned long-eared elves + walking tree buildings + owls + moon pools | The reference forest race's signature set (matters for `sylvan`) |
| Purple-black plague ground + stepped temple towers + spider-men + stitched giants | The reference undead's signature set (matters for `deathless`) |
| Gilded stone-and-metal console with gargoyle or skull corners | The reference HUD frame art |
| A round orb day/night clock, a gauntlet-hand cursor, corner marks or a light circling an autocast button | Reference HUD details (ip-safety §2.4) |
| Crimson or red-and-ivory livery + a gold flame emblem on tabards or banners | A known human military order's look in another game by the same publisher; our coal stays inside the wheel and is never gold (kingdom §1.2) |
| Puffed and slashed sleeves + feathered berets + twin-tailed comet, griffon or double-headed eagle heraldry + hand-gunners and war wagons | A well-known tabletop wargame's imperial human army (the kingdom's nearest trap outside the reference RTS) |
| Onion domes + bear heraldry + fur caps + winged cavalry + ice magic | The same wargame's northern bear-kingdom (onion domes are ours only with the Ember Wheel, burgundy and half-timber) |
| Mongol-styled giant brutes + huge round bellies with gut-plates + meat hooks, cleavers and cooking cauldrons | The same wargame's steppe ogre army (matters for the Tormai and above all the later Thoom and their giant hero, renamed **Kettle-Uncle** so the name no longer points at the cauldron, §13 #26) |

---

## 5. Prompt system

### 5.1 Services, models, seeds and anchors

The budget policy in `docs/asset-ledger.md` decides the service: **Higgsfield** images (0.25 cr) for concept art that feeds image-to-3D
and for terrain and material textures; **Krea** for icons, portraits, UI art, loading art and all audio. Krea 3D is not used.

| Asset class | Template | Service and model | Aspect | Cost each | Seed block | Style anchors |
|---|---|---|---|---|---|---|
| Unit concept (image-to-3D input) | T1 | Higgsfield `gpt_image_2_5` | Portrait 2:3 (or 3:4) | 0.25 cr | kingdom 1101–1149, clans 1201–1249, neutral 1301–1349 | The faction's own unit anchor (`ANCHOR_UNIT_KINGDOM` or `ANCHOR_UNIT_CLANS`); neutral creeps none |
| Hero concept | T2 | Higgsfield `gpt_image_2_5` | Portrait 2:3 | 0.25 cr | kingdom 1110–1119, clans 1210–1219 | The faction's own unit anchor |
| Prop or weapon (separate mesh) | T3 | Higgsfield `gpt_image_2_5` | 1:1 | 0.25 cr | family block + 50 | none |
| Signature building concept | T4 | Higgsfield `gpt_image_2_5`, then Tripo H3.1 (9 cr) | 1:1 | 0.25 cr | kingdom 1180–1199, clans 1280–1299 | The faction's own building anchor |
| Material swatch for bpy kits | T5 | Higgsfield `gpt_image_2_5` | 1:1 | 0.25 cr | 1450–1499 | `ANCHOR_TERRAIN` |
| Terrain tile, cliff face | T6, T7 | Higgsfield `gpt_image_2_5` | 1:1 | 0.25 cr | 1400–1449 | `ANCHOR_TERRAIN`, `ANCHOR_GRASS` |
| Foliage cards, doodad reference | T8 | Higgsfield `gpt_image_2_5`; Qwen Image 2.1 (Krea, transparent, ~30 CU) if keying fails | 1:1 | 0.25 cr | 1460–1479 | `ANCHOR_TERRAIN` |
| Icons (2×2 sheet) | T9 | Krea 2 Medium, `creativity: "raw"` | 1:1, 1K | 9 CU per 4 icons | 1500–1599 | `ANCHOR_ICON` 0.6 + `ANCHOR_NEUTRAL` 0.3 (painting style without armour design) |
| Hero portrait (2D) | T10 | Krea 2 Medium, raw | 1:1 | 9 CU | 1700–1749 | the hero's approved concept 0.5 + `ANCHOR_ICON` 0.3 |
| UI frame part | T11 | Krea 2 Medium on flat black (chroma cut); Qwen Image 2.1 transparent as fallback | 1:1 or 4:1 | 9 / ~30 CU | 1600–1649 | none |
| Loading tableau | T12 | Krea 2 Medium, then a 2× upscale (cost to probe) | 16:9 | 9 CU + upscale | 1800–1849 | `ANCHOR_BUILDING_KINGDOM` 0.2 + `ANCHOR_BUILDING_CLANS` 0.2 + `ANCHOR_GRASS` 0.3 + `ANCHOR_NEUTRAL` 0.3 |
| Emblem (then redrawn as SVG) | T13 | Krea 2 Medium | 1:1 | 9 CU | 1900–1919 | none |
| VFX sprite | T14 | Krea 2 Medium on black | 1:1 | 9 CU | 1950–1999 | none |

**Model capabilities** (input schemas read on 2026-10-17 with Higgsfield `models_explore` and Krea `get_model_schema`; re-check when a
model version changes):

| Model | Negative-prompt field | Seed | Reference images | Consequence |
|---|---|---|---|---|
| Higgsfield `gpt_image_2_5` | **No** | **No** (the seed block is a ledger family id only; it is logged, not sent) | Yes (`image_references`) | Prompt-only: counter-clauses (§5.3) do all the steering; pass the faction anchor as a reference |
| Krea 2 Medium | **No** | Yes | Yes (`image_style_references`, 0–1) | Prompt-only; pass `seed`, `creativity` and the anchor weights explicitly |
| Krea Qwen Image 2.1 | **No** | Yes | Yes (`style_images`, −2 to 2; we use 0–1 only) | Prompt-only |
| Krea Seed Audio, ElevenLabs TTS and Music | **No** | — | — | Prompt-only (§9.1, §8.11, §10.1) |

**Style anchors** (our own approved outputs only; ip-safety §2.7). **A unit anchor carries painting style and the faction's own design
language, so it is never used for the other faction**, and icon and loading art use a neutral anchor that carries no armour design.

| Anchor | Source | Status |
|---|---|---|
| `ANCHOR_UNIT_KINGDOM` | The first **Pavisier** concept that passes §4.2 and the §4.1 squint test: blackened iron kettle hat, quilted ivory gambeson, falchion, a pavise painted with the **full** Ember Wheel (`EMBLEM_KINGDOM_V1`, §5.4: hub coal and crown points, never a bare wheel) | To make (seed 1101) |
| `ANCHOR_UNIT_CLANS` | The Grappler concept (ledger #19, `assets_src/characters/clans_grappler/concept.png`: bronze cone helmet with streamer, laced lamellar flaps, no round shoulder plates), once it passes the §4.1 squint test **and the §5.7 skin check**. It was made with the retired blue-grey skin, so its skin is first recoloured to the §2.2 ash-grey in post (the same skin-band clamp as §5.7); an anchor with blue skin would pull every later Tormai concept back to blue | Candidate |
| `ANCHOR_NEUTRAL` | The first approved neutral prop or Sootcoat concept (the loot bundle or a power-up prop is ideal); until it exists, `ANCHOR_TERRAIN` at 0.2 | To make |
| `ANCHOR_TERRAIN` | Ledger #6: dirt texture (Higgsfield) | Approved |
| `ANCHOR_GRASS` | Ledger #1: grass texture probe (Krea 2 Medium) | Approved ("usable") |
| `ANCHOR_BUILDING_KINGDOM` / `ANCHOR_BUILDING_CLANS` | Ledger #22: Moot Hall concept `f5ea16a8` / Shell Hall concept `5b28e08f` | Approved |
| `ANCHOR_ICON` | The first approved 2×2 icon sheet (kingdom units) | To make |
| *Not an anchor:* ledger #7 | The kingdom infantry bake-off concept (`8f55e5cc…`, `assets_src/characters/kingdom_infantry/`) | **Record of the 3D bake-off only, never a style input.** It breaks §2.1 and §4.2 (polished silver-steel plate, large round steel shoulder plates, a straight double-edged sword with a gilt crossguard, a star-over-tower shield instead of the Ember Wheel). Its rigged model is a placeholder: replace it with a §4.2-compliant Pavisier before any public build |

Krea style-reference weights stay inside 0–1 and sum to about 1.0 (pipeline §4.1). Always pass `seed` (where the model has one) and
`creativity` explicitly. Variants of one asset use `seed + i`. Never use a reference-game image, screenshot or fan asset as any kind of input.

### 5.2 The fixed style suffix

Appended, unchanged, to every image prompt except emblems (T13). It describes qualities, never a studio, game or person.

```
STYLE_SUFFIX_V1 =
stylized hand-painted fantasy strategy game art, painterly brush texture, big simple readable shapes, bold clear silhouette,
saturated harmonious colours, soft painted gradients, gentle top light painted into the colours, painted ambient occlusion,
clean colour blocking with one or two main colours, game-ready asset
```

Form rules that only suit characters (oversized hands, heads and weapons) live in templates T1–T3, not in the suffix, so terrain and UI
prompts are not pulled toward figures. A change to the suffix is a new version (`_V2`) and needs a re-approved anchor set.

**`_V2` test set (genre words out).** No model we use has a negative field, so describing an asset by genre and function ("fantasy
strategy game art", "strategy-game score", "heroic level-up") makes the genre's most heavily represented example an attractor: the
same priming that the `_V2` faction clauses removed for colour names (§5.4). The `_V1` texts below were approved under ip-safety §2.8
and stay the default until the A/B is done. **A/B each pair** (same subject, seed and anchors; for audio, the §10.1 listening check),
keep whichever version passes review, and log both in the ledger.

| Item | `_V1` (current) | `_V2` (candidate) |
|---|---|---|
| Style suffix | "stylized hand-painted fantasy strategy game art, …" | `STYLE_SUFFIX_V2` = "stylized hand-painted tabletop-miniature fantasy art, painterly brush texture, big simple readable shapes, bold clear silhouette, saturated harmonious colours, soft painted gradients, gentle top light painted into the colours, painted ambient occlusion, clean colour blocking with one or two main colours, game-ready asset" |
| Template genre phrases (T4, T6, T8 b, T9, T11, T12) | "strategy-game proportions", "for a strategy game", "fantasy game icons", "for a fantasy strategy game", "strategy game loading screen" | "proportions of a painted tabletop model", "seen from high above", "painted icons", "for an original fantasy world", "loading-screen landscape" |
| Music opening (§10.3) | "Instrumental fantasy strategy-game score …" / "… for an original heroic fantasy strategy game …" | "Instrumental folk-ensemble background score for an original fantasy world …" |
| `ui_levelup` clause (§9.2) | "a bright heroic level-up flourish: three quick ascending small hand-bells … uplifting and magical" | "three quick ascending small hand-bells landing on a warm singing bronze bowl that blooms and shimmers, a soft low felt-mallet drum tap underneath" (instruments only; no "level-up", "heroic" or "magical") |
| SFX wrappers (§9.1) | "stylized fantasy game sound" | "stylized sound effect" |

### 5.3 The fixed negative list and the counter-clauses

Every model we use is **prompt-only** (§5.1). Naming an unwanted feature in a positive prompt often primes it, so `NEGATIVE_V1` and the
`NEG_*` add-ons are **never pasted into a prompt**. They are the reviewer's checklist (§5.7) and they would be passed only to a model
whose schema gains a negative field. The steering happens inside the subject: **every `NEG_*` add-on has a positive counter-clause**
that describes the wanted feature in its place, and the counter-clause is part of every subject of that faction or family (§5.6).

```
NEGATIVE_V1 =
photorealistic, photograph, realistic proportions, glossy PBR reflections, chrome, wet look, specular highlights, film grain,
noise, grunge overlay, tiny intricate details, thin spindly limbs, anime, chibi, pixel art, flat vector style, plastic 3D render,
harsh cast shadows, dramatic rim light, depth of field, motion blur, lens flare, text, letters, numbers, runes, watermark,
signature, logo, frame, border, user interface, multiple subjects, cropped subject, duplicate limbs
```

**Per-class adjustments:** T11 (UI frames) removes `frame, border, user interface`. T6 and T7 add `perspective, horizon, focal object,
objects casting shadows`. T12 removes `multiple subjects`. T9 (icon sheets) removes `multiple subjects`.

**Faction and family add-ons and their counter-clauses**

| Add-on | Review checklist (never in a prompt) | Positive counter-clause (always in the subject) |
|---|---|---|
| `NEG_KINGDOM` | blue cloth, white and gold livery, gold trim, polished silver armour, round steel shoulder plates, straight double-edged broadsword, gilt crossguard, lion, eagle, winged beast emblem, star or tower emblem, kite shield, heater shield, closed great helm, glowing hands, beams of light, grey stone steeple, blue roof; puffed and slashed sleeves, feathered beret, twin-tailed comet, griffon, double-headed eagle, bear emblem, fur cap, winged lancer, axe-blade gun rest, ice magic; a flame emblem on tabards or banners; **a wheel emblem without its hub coal or crown points** (a bare six-spoked wheel on red is a real civic coat of arms, kingdom §1.2) | "matte blackened iron with dark bronze fittings, burgundy wool and quilted ivory linen, quilted shoulder rolls with no plate on the shoulders, an emblem of an ivory six-spoked wagon wheel with a solid round dark-bronze coal with a small ember-orange core at the hub and three pointed, tapered crown points rising from the top of the rim, on a burgundy field (`EMBLEM_KINGDOM_V1`, §5.4), plain close-fitting sleeves, wide-brimmed iron kettle hats or linen hoods" |
| `NEG_CLANS` | tusks, fangs, green skin, olive skin, red-brown skin, **blue skin, blue-grey skin, teal skin**, pointed ears, long ears, lanky, hunched, long arms, mohawk, spikes, spiked shoulder pads, round shoulder pads, fur, bones, skulls, horns, hide tents, axe, red-brown leather straps, war paint, wolves, lightning, violet, purple; huge round belly, belly plate, gut plate, meat hook, cleaver, cooking cauldron | "**small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks**, a broad, upright, thick-set build with heavy shoulders and a flat stomach, **ash-grey stone-coloured skin like weathered granite, with pale hail-speckles**, a cone helmet or a felt hat over plain short or braided hair, rectangular laced lamellar flaps over quilted felt" |
| `NEG_UNCUT` (T2) | spinning, whirling, swirl, whirlwind, dust column, flared skirt circle, curved sword, oversized blade, topknot, mask | "a straight single-edged horse-sabre of normal length carried low, hair in **one** long braid only that trails to the ground and ends in a bronze weight, a split riding coat hanging straight down, standing still and square-on, face uncovered" |
| `NEG_SKYMIRROR` (T2) | blindfold, covered eyes, visor over the eyes, mirror over the face, mirror-hung robe, studded mirrors, fringes, wolf | "**both eyes open and clearly visible**, the round bronze mirror **tilted up on the brow-band above the eyebrows**, a plain coat of bare quilted ink-teal felt with a few bronze studs and nothing hung or sewn on it, the second mirror only on top of the staff" |
| `NEG_GUSTCALLER` | discs, mirrors, tassels or ornaments hung on the robe, wolf pelt, lightning, a tall peaked or pointed hat | "a **plain robe of bare felt** with nothing sewn or hung on it, a **low rounded felt cap wound with long felt ribbons streaming from its crown**, ribbons only on the cap and the staff, the bronze wind-vane staff head rising well above the head" |
| `NEG_SOOTCOAT` | daggers, face masks, purple cloak, red hooded cloak, invisibility | "a wide conical leather hood open at the face, soot on the skin, farm tools (rake, billhook) as weapons" |
| `NEG_TATTIE` | pumpkin, carved grinning face, **any face on the turnip (eyes, mouth, painted or carved)**, **a swappable or detachable head**, machinery, horse | "a sacking face with stitched features, a hollowed turnip lantern pierced with a few small randomly drilled holes and no face, fixed on a short pole, a body of crossed wooden poles and straw" |
| `NEG_RUNDLING` | green skin, big ears, gold hoard, explosives, rockets | "a small pangolin-like body of overlapping umber scales, tiny rounded ears, brass scales and weights" |
| `NEG_CAIRN` | round boulder body, glowing crystal core, lava | "a body of stacked flat drystone slabs with visible gaps, moss in the joints, yellow lichen glyphs" |

**How to use them:**

- Append only `No text, no logo, no watermark, no cast shadows.` to a prompt; that one negative sentence has proved harmless.
- Put the counter-clause in the subject (§5.6 already does), and pass the faction's own anchor as a reference where the model takes one.
- Review the output against `NEGATIVE_V1` and the add-on (§5.7). One hit on a look-alike item rejects the image.
- No field ever contains a reference-game name, an artist name or an "in the style of" phrase (ip-safety §2.8).

### 5.4 Fixed faction clauses

```
KINGDOM_CLAUSE_V2 =
late-medieval town-militia fantasy style, burgundy and ivory as the two main colours with dark bronze and blackened iron as the
third, quilted ivory linen, burgundy wool, dark oak wood, cast dark bronze, matte blackened iron, folk-painted wooden surfaces with
simple hand-painted wheels, flowers and stripes

CLANS_CLAUSE_V3 =
fantasy steppe-nomad style of big grey-skinned humanoids, dark ink-teal and saffron felt as the two main colours with warm
polished bronze as the third, thick quilted felt in big colour blocks, rows of laced rectangular lamellar plates, red-brown
folding lattice-wood, ash-grey stone-coloured skin like weathered granite with pale hail-speckles, small rounded ears close to
the head, very heavy square lower jaw with flat square teeth and no tusks

NEUTRAL_CLAUSE_V1 =
neutral wilderness fantasy style, earthy muted colours that belong to neither army, [FAMILY_PALETTE_WORDS]

EMBLEM_KINGDOM_V1 =
an ivory six-spoked wagon wheel with a solid round dark-bronze coal with a small ember-orange core at the hub and three pointed,
tapered crown points rising from the top of the rim, on a [FIELD] field
```

The `_V2` clauses replaced `_V1` (2026-10-17): the kingdom clause no longer names the colours it avoids (naming them primed them on
prompt-only models; `NEG_KINGDOM` and review cover them), and the clans clause no longer lists "horn" as a material (it primed horned
helmets; the Bow-Mast's bow is described in its own subject) and carries the ear clause. **`CLANS_CLAUSE_V3` replaces `_V2`
(2026-10-19):** the word "blue" is gone from the skin. "Slate blue-grey" was the documented cause of the troll drift (the ledger #19
Javelineer came back lean, blue-skinned and point-eared, the reference forest-troll spear thrower inside the reference warrior faction),
and with no negative field the ear and jaw counter-clauses were fighting a hue the prompt kept asking for. Assets made with earlier
versions keep their ledger entry; new generation uses the current version.

**`EMBLEM_KINGDOM_V1` is the only way a kingdom emblem is prompted** (pavise faces, banners, gable signs, the unit anchor, T13). `[FIELD]`
is `burgundy`, or `solid pure magenta (#FF00FF)` where the field is a team-colour area (the pavise face). A bare ivory six-spoked wheel on
red is the arms of real cities (kingdom §1.2), so the hub coal and the crown points are never dropped. **Decorative folk-painted
wheels** (the kingdom clause's "simple hand-painted wheels", the wagon-plank swatch) are small and repeated in bands with flowers and
stripes, never one lone centred wheel on a burgundy panel; a lone centred wheel is always the full emblem. Plain wheels that are not
ivory on red (iron finials, the bronze cursor tail, the end-cap bosses, the busy cursor) stay plain.

Family palette words: Sootcoats "soot black, faded ochre oilcloth, faded moss green"; Tattiebogles "straw yellow, sacking beige,
faded madder red and woad blue patches"; Rundlings "umber scales, brass, cream and sage stripes"; Cairnwakes "grey drystone, yellow
lichen, green moss". **Never** add a real ethnic, national or religious descriptor to any clause (clans §1.4, kingdom §1.1).

### 5.5 Templates by asset class

Every `[SLOT]` is filled from §5.6 or the faction docs. Text outside the slots is fixed.

**T1. Unit concept (image-to-3D input).** Follows pipeline §2.2: one object, A-pose, gaps between legs and between arms and torso.

```
full body [SUBJECT], [FACTION_CLAUSE], chunky heroic proportions with oversized hands, forearms, boots, headgear and weapon head,
solid pure magenta (#FF00FF) cloth on [TEAM_AREAS] and nowhere else, standing A-pose with the arms held 30 degrees away from the
body and a clear gap between the legs, [WEAPON] held clear of the body, front three-quarter view, near-orthographic camera at chest
height, centered, entire figure visible including the feet with a margin on every side, evenly lit flat albedo, no cast shadows,
no ground shadow, plain flat light-gray background (#D0D0D0), [STYLE_SUFFIX_V1]
```

- Creeps: replace the magenta sentence with `no magenta anywhere`.
- Generate big props (pavise, wheel-shield, hod, sabre) separately with T3 and keep the hand empty or holding a simple grip if the prop
  would cross the body.
- Exaggerate about 1.3× beyond the final read (rule 4).

**T2. Hero concept.** T1 plus one sentence after the subject:

```
heroic stature, broader and taller than a regular soldier, one oversized signature prop: [PROP]
```

Team areas cover 12–18 % (§3.1). Generate the signature prop separately as well when it is a separate mesh.

**T3. Prop or weapon (separate pivoting mesh).**

```
single isolated [PROP], [MATERIALS], oversized chunky game proportions, [VIEW: side view | front view], flat orthographic,
centered, whole object visible with a margin, evenly lit flat albedo, no cast shadows, plain flat light-gray background (#D0D0D0),
[STYLE_SUFFIX_V1]
```

**T4. Signature building concept** (T1 halls only in the slice; every other building is a procedural bpy kit).

**Hall tiers (scouting the enemy hall tells you its tech, so every tier must read).** **T2 = the T1 Tripo GLB plus a bpy add-on kit**
at the same `--width 8` and at most +15 % height (§1.3), costing about 0.5 cr of T5 swatches; no new image-to-3D. Kingdom (Walled
Burg): a stone ground-floor skirt, a ring of 6 parked wagons inside the footprint edge, and a taller dome on a drum. Clans (Banner
Shell): 3 tall felt banners on masts, a second gong frame and a lattice gallery ring. T3 (*later*) adds its crown the same way.
**While upgrading**, the hall shows its faction's construction dressing (kingdom: timber scaffold around the dome; clans: felt wraps
lashed over the shell) and plays `build_loop_<faction>` (§9.5); the dressing drops away with `build_done_<faction>`.

```
[BUILDING], [FACTION_CLAUSE], compact chunky strategy-game proportions, oversized roof and a tall readable crown, solid pure
magenta (#FF00FF) on [TEAM_AREAS] and nowhere else, viewed from a 45 degree high three-quarter angle, the whole building and its
base visible with a margin, evenly lit flat albedo, no cast shadows, isolated on plain flat light-gray background (#D0D0D0),
[STYLE_SUFFIX_V1]
```

**T5. Material swatch for procedural kits** (tileable; plaster, timber, felt, lattice, shell, bronze and so on).

```
seamless tileable hand-painted [MATERIAL] surface texture, seen flat and straight on, [DETAIL], big readable shapes sized for a
game seen from far above, lighter painted top edges and darker painted gaps, even lighting edge to edge, no perspective,
no objects, [STYLE_SUFFIX_V1]
```

**T6. Terrain tile** (§6.1 gives the subject for each of the 7 tiles).

```
seamless tileable hand-painted ground texture for a strategy game, seen straight from above, [TILE_SUBJECT], soft painterly
strokes, low contrast, mid value, muted natural colours, uniform density edge to edge, no central focal object, even flat
lighting, no perspective, no horizon, no cast shadows, [STYLE_SUFFIX_V1]
```

**T7. Cliff face.**

```
seamless tileable hand-painted cliff face texture, seen flat and straight on, [CLIFF_SUBJECT], chunky stylized stone blocks with
lighter painted top edges and darker crevices, cool muted greys, even flat lighting, no perspective, no sky, no ground,
[STYLE_SUFFIX_V1]
```

**T8. Tree foliage cards and doodad reference.**

```
(a) four separate hand-painted [TREE] leaf clumps for a stylized game tree, arranged in a 2x2 grid with wide gaps, each clump a
soft rounded cloud of [LEAF_SHAPE] leaves, darker cool interior and lighter warm sunlit top, chunky simple shapes, isolated on a
plain flat pure blue (#0000FF) background, [STYLE_SUFFIX_V1]

(b) small cluster of [DOODAD] for a strategy game map, chunky simple shapes, [PALETTE_WORDS], viewed from a 45 degree high
three-quarter angle, evenly lit flat albedo, no cast shadows, isolated on plain flat light-gray background (#D0D0D0),
[STYLE_SUFFIX_V1]
```

Blue `#0000FF` is the foliage key because Greenvale leaves contain no blue. Doodads are modelled in bpy from (b); only a hero doodad that
is seen from one side (for example the Gold Seam rock face) may go through TRELLIS (about 15 CU; back not textured).

**T9. Icon sheet (2×2), 128 × 128 final.** The model never draws the frame (pipeline §4.4).

```
2x2 grid of four separate square fantasy game icons with wide dark gaps: 1. [SUBJECT_1], 2. [SUBJECT_2], 3. [SUBJECT_3],
4. [SUBJECT_4]. Each icon: one bold central subject filling 70 percent of its square, lit from the upper left, strong value
contrast, a [ACCENT] glow accent, simple dark [BG_TINT] vignette background, no border, no frame, no text, [STYLE_SUFFIX_V1]
```

Icon rules:

| Icon kind | Subject | `BG_TINT` | `ACCENT` |
|---|---|---|---|
| Kingdom unit or building | The unit's bust or the building's crown, in its upper-third read | burgundy-black `#2A1014` | ember orange |
| Clans unit or building | Same | ink-teal-black `#0E2426` | sun-glint gold |
| Hero ability | The action's object, never a glowing hand or a face shouting | dark of the ability's spell colour (§1.7) | the spell colour |
| Research | The object being improved (blade, barrel, plate, felt, bronze) | iron-black `#1E2024` | bronze |
| Item (neutral) | The item itself on a cloth | umber-black `#241C14` | warm lantern |
| Command (move, stop, hold, attack, patrol, build, build advanced, gather, return cargo, repair, rally, attack ground, learn, cancel or back, unload all) | A simple shared pictogram: a waymark post (move), a closed gate (stop), a stake with a rope ring (hold), crossed blades (attack), a looping footpath (patrol), a mallet and plumb line (build), a mallet and plumb line over a small stepped gable (build advanced), a sack and a log (gather), a sack with a curved arrow back to a doorway (return cargo), a mallet and nails (repair), a pennant on a stake (rally), a stake in a scorched ring (attack ground), an open book with a ribbon marker (learn), a bent arrow turning back (cancel or back), an open door with three small figures stepping out (unload all). **Minimap toggles** (24 px, §7.1): three small figures in a row behind a pennant, filled when on (Formation); a shield pip (Show Camps); a two-tone disc (colour mode, team ↔ relation). 18 pictograms in all | slate-black `#1A1E24` | pale cream |
| Toggle states | Plant Pavise on (the pavise planted, stakes showing) and off (the pavise carried on the back); Roll the Felt (the felt skirt rolled up) | the unit's faction tint | the faction accent |
| Summons and placed units (selection grid) | Grand Bombard (the bronze bombard on its timber platform), Hail-Swift (a packed-hail swift skimming low) | dark of the spell colour | the spell colour |

Never reproduce the composition of a well-known reference icon (ip-safety §2.4). Our rules of thumb: heals show plants, cloth and
cups, never hands; haste shows felt ribbons streaming behind a running hare or a bent grass-head in a gust (never a boot; footwear only
for move-speed items, a convention neutrals §10.2 accepts); stealth shows a low, flat dust puff (never a dust devil or whirl); reveal
shows a mirror, a snapped chalk line or bell-strung burrs, **never a pouch, a thrown powder or a dust puff**; power-ups show their own
prop (§2.3), never a book.

**T10. Hero portrait** (2D bust for the hero buttons, loading plates and tooltips; the console portrait is a live 3D view).

```
bust portrait of [CHARACTER], head and shoulders, three-quarter view facing left, exaggerated heroic features, [FACTION_CLAUSE],
painted, warm key light from the upper left, cool soft shadow side, plain flat dark warm-grey background (#2A2622), no frame,
no text, [STYLE_SUFFIX_V1]
```

**T11. UI frame part** (9-slice source; §7.3 lists the parts).

```
flat front-on orthographic user-interface [PART] for a fantasy strategy game, [UI_CLAUSE], ornament of even thickness along the
edges, perfectly symmetric, empty flat dark centre (#14110E), hand-painted, chunky readable shapes, no text, no letters,
no symbols, no perspective, no drop shadow, isolated on a plain flat pure black background, [STYLE_SUFFIX_V1]
```

`UI_CLAUSE` values are in §7.2.

**T12. Loading tableau.**

```
wide panoramic painted fantasy landscape tableau for a strategy game loading screen, [SCENE], high three-quarter elevated view
like a tabletop diorama, horizon in the upper third, calm darker meadow and road across the lower fifth, no figure closer than
the middle distance, golden late-afternoon light with drifting cloud shadows, [STYLE_SUFFIX_V1]
```

**T13. Emblem** (concept only; the shipped emblem is a hand-made SVG with exact shapes).

```
flat heraldic emblem in at most four flat colours, [EMBLEM], bold simple shapes that read at 24 pixels, thick even outline in
[RIM_COLOUR], centered on a plain flat [FIELD_COLOUR] square, no gradient, no texture, no text, no border
```

Kingdom `[EMBLEM]` = `EMBLEM_KINGDOM_V1` with `[FIELD]` = burgundy (four colours: ivory, dark bronze, ember orange, burgundy).

**T14. VFX sprite** (hand-painted additive sprites; most VFX are procedural per the juice specs).

```
single hand-painted [EFFECT] sprite for a game particle effect, centered, soft painted edges fading to nothing, chunky simple
shapes, bright core and darker rim, on a plain flat pure black background, no other objects, [STYLE_SUFFIX_V1]
```

### 5.6 Subject clause library (slice)

**Kingdom (Brennmark).** `FACTION_CLAUSE = KINGDOM_CLAUSE_V2`; review checklist `NEG_KINGDOM`. Every kingdom subject carries the
`NEG_KINGDOM` counter-clause where it applies (metal is matte blackened iron or dark bronze; every emblem is the full
`EMBLEM_KINGDOM_V1`, §5.4: wheel, hub coal and crown points, never a bare wheel).

| Asset (seed) | T | `SUBJECT` / `BUILDING` / `PROP` | `TEAM_AREAS` | `WEAPON` |
|---|---|---|---|---|
| Pavisier (1101) | T1 | young sturdy human town-militia soldier, wide-brimmed **matte blackened iron** kettle hat with a short plume, quilted ivory linen gambeson with diamond stitching and **quilted shoulder rolls with no plate on the shoulders**, burgundy hood, dark iron arm guards, big boots | the hat plume and an arm sash | a short heavy curved single-edged falchion with a plain dark iron crossguard |
| Hodman (1102) | T1 | stocky older human labourer with a weathered kind face and a short grey beard, a wide flat straw hat whose brim is wider than his shoulders, quilted ivory linen jacket with rolled sleeves, burgundy hood folded on the shoulders, dark oak-brown breeches, big work boots, a V-shaped wooden hod strapped over one shoulder | the hat band and a shoulder sash | a short wooden mallet |
| Hookgunner (1103) | T1 | lean human gunner in his thirties with a soot-smudged face, wide-brimmed matte blackened iron kettle hat with a short plume, quilted ivory gambeson, burgundy sleeves, a coil of smouldering slow-match at the belt, a powder flask | the hat plume, an arm sash and a cloth wrap on the gun barrel | a long thin early hand-cannon with a hook under the barrel, sloped over the shoulder, and a plain forked wooden rest in the other hand |
| Linden Sister (1104) **[SLICE]** | T1 | brisk middle-aged human herbalist woman, a large wreath of heart-shaped linden leaves over a white linen coif, ivory apron over a burgundy wool dress, a wicker basket of herbs on her back, a small clay censer on a cord at her belt | a short shoulder-cape lining, the apron stripe and a collar ribbon | a short staff tied with a bundle of dried linden blossom |
| Wheel Marshal (1110) | T2 | broad tall human woman knight in her forties with a calm stern face, **matte blackened** plate armour with simple fluting and small close-fitting shoulder plates, an ivory surcoat, a sallet helmet with a wide kettle brim; `PROP`: a round wheel-shield made from a six-spoked cart wheel planked between the spokes, with a domed bronze hub boss | the helmet plume, a long cloak and the hub-boss enamel | a long-hafted war-pick |
| Firewright (1111) | T2 | stocky soot-faced human man in his forties with a cheerful grin and no eyebrows, a leather apron over an ivory shirt, a tall felt chimney-shaped hat with a bronze smoke cap, a bandolier of round clay flasks across the chest; `PROP`: the chimney hat | the hat band and a short cloak | a linstock staff with a smouldering match-cord |
| Pavise (1151) | T3, front view | tall flat round-topped rectangular wooden shield with a raised vertical central ridge, the face painted with `EMBLEM_KINGDOM_V1` with `[FIELD]` = solid pure magenta (#FF00FF): a hand-painted ivory six-spoked wagon wheel with a solid round dark-bronze coal with a small ember-orange core at the hub and three pointed, tapered crown points rising from the top of the rim, on a solid pure magenta (#FF00FF) field; dark oak back with blackened iron straps | (face field) | — |
| Flail and kettle hat (1152) | T3, side view | a threshing flail: long ash handle joined by a short iron chain to a thick iron-banded beater; and a wide-brimmed matte blackened iron kettle hat (second image) | — | — |
| Moot Hall (1180) | T4 | a two-storey half-timbered town hall with ivory lime plaster between dark oak frames and diagonal braces, a rubble-stone ground floor, a steep burgundy-red clay tile roof, a stepped gable at the front, one small dark-bronze onion-dome turret topped by an iron six-spoked wheel finial, a wooden arcade at street level, two parked market wagons beside it, a stork nest on the chimney | swallow-tailed roof pennants, the window shutters and the ridge-tile band | — |

The current Pavisier stand-in (the ledger #7 bake-off infantry, built as `kingdom_infantry`) fails this row; generate seed 1101 from this subject and make it
`ANCHOR_UNIT_KINGDOM` once it passes §4.2 (§5.1).

**Clans (Tormai).** `FACTION_CLAUSE = CLANS_CLAUSE_V3`; review checklist `NEG_CLANS`. **Every Tormai subject repeats the same
sentence**, word for word, plus a cone helmet or a felt hat (clans §12.3): *"small rounded ears close to the head, a very heavy square
lower jaw with flat square teeth, no tusks"*. Units also wear a cone helmet, a felt hat or a felt hood; heroes keep their signature
head read instead (the Uncut's braid, Skymirror's brow-mirror) and add their own counter-clause from §5.3.

| Asset (seed) | T | `SUBJECT` / `BUILDING` / `PROP` | `TEAM_AREAS` | `WEAPON` |
|---|---|---|---|---|
| Yurtwright (1201) | T1 | stocky big-jawed humanoid craftsperson with ash-grey stone-coloured skin like weathered granite, with pale hail-speckles on the forearms, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, a tall peaked felt hat with ear-flaps, a quilted ink-teal felt coat with saffron trim, a bundle of red-brown folding lattice-wood strapped on the back | the hat band and the bundle strap | a wooden mallet |
| Grappler (1202) | T1 | huge broad wrestler-warrior with ash-grey stone-coloured skin like weathered granite, with pale hail-speckles on the shoulders, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, a bronze chin-guard, a conical bronze helmet, three rows of saffron-laced rectangular lamellar flaps on the shoulders, a sleeveless deep ink-teal quilted felt coat over a flat stomach, thick bronze wrist-guards | a long helmet streamer and a felt sash | an oversized flanged bronze mace |
| Javelineer (1203) | T1 | **broad, stocky**, upright adult big-jawed humanoid with heavy shoulders and ash-grey stone-coloured skin like weathered granite, with pale hail-speckles, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, a **peaked saffron felt hood whose peak sits over a round felt cap**, a sleeveless ink-teal felt tunic, a quiver-bundle of bronze-weighted javelins on the back | a hood streamer, a sash and the javelin-bundle wrap | a wooden spear-thrower stick in one hand and one javelin in the other |
| Gustcaller (1204) | T1 | older big-jawed humanoid weather-caster with ash-grey stone-coloured skin like weathered granite, with pale hail-speckles, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, **a plain robe of bare saffron felt** with nothing sewn or hung on it, a folding felt fan at the belt, **a low rounded felt cap wound with long felt ribbons that stream from its crown** (no peak, no point) | a felt shoulder mantle and the ribbons on the staff | a tall wind-vane staff whose bronze vane on a pivot rises well above the head (≥ 0.4 m), with felt ribbons tied to the staff; no ribbon or ornament on the robe |
| The Uncut (1210) | T2 | lean fast big-jawed humanoid woman duelist with ash-grey stone-coloured skin like weathered granite, with pale hail-speckles, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, face uncovered, a bronze chin-guard, a split saffron riding coat hanging straight down, **hair in one long braid only** that trails on the ground behind her and ends in a bronze weight, standing still and square-on; `PROP`: the braid. Counter-clause `NEG_UNCUT` (§5.3) | a sash and a ribbon near the braid weight | **a straight single-edged horse-sabre of normal length** carried low |
| Skymirror (1211) | T2 | old broad big-jawed humanoid seer with ash-grey stone-coloured skin like weathered granite, with pale hail-speckles, small rounded ears close to the head, a very heavy square lower jaw with flat square teeth, no tusks, **both eyes open and clearly visible**, the round polished bronze mirror **tilted up on a brow-band above the eyebrows**, a plain coat of bare quilted ink-teal felt with a few bronze studs and nothing hung or sewn on it; `PROP`: a long staff topped by a second round bronze mirror. Counter-clause `NEG_SKYMIRROR` (§5.3) | a felt shoulder mantle and the staff ribbons | the mirror staff |
| Bow-Mast bow (1251) | T3, side view | a large laminated recurve bow of wood and bronze on a swivel mount, a thick waxed string, felt ribbon streamers tied at both tips | — | — |
| Shell Hall (1280) | T4 | a large nomad council hall built beneath a gigantic sun-bleached ancient tortoise-shell dome with big hexagonal plates, deep ink-teal and saffron felt hangings, a carved red-brown lattice-wood doorway, small felt yurts attached around the base, a bronze gong on a wooden frame by the door, carved masts with felt ribbon streamers | the felt band around the dome and the door hangings | — |

**Regenerate before 3D sign-off (the ledger #19 concepts that drifted):** `clans_skymirror` (mirror over the eyes, a robe studded with
mirrors), `clans_javelineer` (pointed ears, lean blue-skinned build) and `clans_gustcaller` (a bronze disc and tassels on the robe;
now also the new cap-and-vane head read, §4.3). Generate each from the row above with `CLANS_CLAUSE_V3` (0.25 cr each), re-run the
§4.1 squint test (the Javelineer against the reference forest-troll spear thrower) and the §5.7 skin check, then redo image-to-3D only
for the ones that pass (Tripo H3.1, 9 cr each; Higgsfield balance 77.5 cr on 2026-10-17). **Every other ledger #19 Tormai concept and
model** (Yurtwright, Grappler, the Uncut) was made with the retired blue-grey skin: recolour its skin to the §2.2 ash-grey with the
§5.7 skin-band clamp (no regeneration, no 3D credits).

**Neutral (Greenvale).** `FACTION_CLAUSE = NEUTRAL_CLAUSE_V1` with the family's palette words; no magenta.

| Asset (seed) | T | `SUBJECT` | Add-on | `WEAPON` |
|---|---|---|---|---|
| Sootcoat base (1301) | T1 | lean human charcoal-burner outlaw with a soot-blackened face and pale rings around the eyes, a wide conical leather hood with a neck flap, a patched oilcloth coat, clay smoke-pots on a bandolier | `NEG_SOOTCOAT` | a long-handled rake |
| Fieldkeeper (1310) | T1 | walking scarecrow made of crossed wooden poles inside a patched coat, a stuffed sacking face with stitched features, straw spilling at the joints, harrow-tine fingers, stiff straight legs | `NEG_TATTIE` | a pitchfork |

**Material swatches for procedural kits (T5)**

| Kit | `MATERIAL` and `DETAIL` |
|---|---|
| Kingdom half-timber | lime plaster: lumpy ivory plaster with soft trowel marks · dark oak beam: dark brown oak with broad grain strokes and peg holes · burgundy clay roof tiles: overlapping curved tiles in burgundy-red with lighter tile edges · rubble stone: rough fieldstones in pale mortar · dark bronze dome sheet: overlapping scale-shaped bronze plates with painted highlights · wagon planks: oak planks with folk-painted ivory wheels and stripes · blackened iron strap: riveted iron bands |
| Kingdom slice extras (kit parts, no T4) | Timber Yard: sawn oak log ends with pale growth rings, sawdust-strewn planks · Collegium: a small bronze bell in a timber bell-cote, a low lime-washed garden wall with linden saplings · Curio Cabinet: a painted chest of small drawers with brass knobs and folk-painted flowers (the sign prop) |
| Clans slice extras | Tea Tent: thick felt in broad saffron and ink-teal vertical stripes · bronze urn: a big round polished bronze urn with a lid and spout on an iron tripod |
| Coaching Inn (neutral browns) | weathered plaster: pale linen-coloured lime plaster · brown timber: mid-brown weathered oak · slate roof: grey stone slates (never burgundy tiles) · lantern sign: a wrought-iron bracket with a big glass lantern |
| Clans yurt and shell | ink-teal felt: thick felt with a few broad saffron stitch lines · saffron felt: thick felt with ink-teal stitches · lattice-wood: red-brown wooden diamond lattice with dark gaps · tortoise shell: big sun-bleached hexagonal shell plates with dark seams · polished bronze: warm bronze with painted streak highlights · carved standing stone: grey stone with shallow carved faces |
| Neutral | gold-veined rock: grey-brown rock with thick gold veins · drystone slabs: stacked flat grey slabs with moss in the gaps · Weighstall awning: cream and sage stripes on canvas · brass: warm brass with painted highlights · timber adit: rough-hewn mine timbers |

### 5.7 Post-processing and acceptance

| Class | Post-processing (scripted; pipeline §6) | Acceptance |
|---|---|---|
| T1–T4 concepts | Check the background (corner pixels within ±10 of `#D0D0D0`), extract the magenta mask (§3.1), median-filter micro-noise, keep the original | §3.4 checks; §4 silhouette checklist on a quick block-out; squint test vs the nearest reference role; palette ΔE: at least 70 % of non-background pixels within ΔE 20 of the faction palette after the LUT. **Tormai skin check:** sample the median of the face and forearm skin; a hue of 180–240° with saturation above 10 % **rejects** the concept |
| 3D textures from Tripo H3.1 | Faction LUT remap, saturation and value clamp per class (§1.4), de-bake strong directional light (visual §7.4 step 3), dilate UV islands, resize to the texel density (§1.6). **Clans skin-band clamp:** pixels with hue 170–250°, saturation 10–30 % and value 25–80 % (the skin band) are pulled to saturation ≤ 10 % and toward the §2.2 ash-grey; ink-teal felt (saturation ≥ 45 %), team colour and hair fall outside the band and are untouched. Where a skin mask is painted on the UV layout, the clamp runs inside it only | Rendered from the game camera at 1080p: silhouette, three value masses, size test (§1.2, bounding-box measure); Tormai skin passes the concept skin check |
| T5–T7 textures | `make_tileable` offset-and-blend (pipeline §4.3, blend 0.15–0.25), LUT, clamp, light unsharp mask | Wrap-seam ratio ≤ 1.3; 3×3 tiling preview shows no visible repeat feature; value and saturation inside §1.4 |
| T8 foliage | Chroma-key `#0000FF` with despill, trim, pack into a 512² atlas | No blue fringe at 2× zoom |
| T9 icons | Split the grid, trim 6 % gutters, fit 116 px Lanczos, unsharp, composite the faction frame, derive disabled, hover and pressed states | Readable at 48 px; no two icons on one card share a dominant shape and hue |
| T10 portraits | Crop to the face box, LUT, 128² and 64² exports | Reads at 64 px as the same character as its 3D model |
| T11 UI parts | Chroma-cut black, mirror left onto right and top onto bottom (pipeline §4.5), measure margins, export 2× | Four identical corners; edges tile without seams if set to TILE |
| T12 loading | Upscale, LUT, lower-fifth darkening gradient for the info band | Text band legible at 1080p; no stray text-like marks |
| T13 emblem | Redraw by hand as SVG (exact geometry), then rasterise | Reads at 16 and 24 px. **Kingdom:** at 24 px the hub coal and the three crown points must read; compare side by side with the civic arms of Mainz, Erfurt and Osnabrück (a bare six-spoked wheel on red), and reject the emblem if it could be taken for them |
| T14 VFX | Convert luminance to alpha, premultiply | Blooms only above HDR 1.0 in engine |

---

## 6. Terrain, cliffs, water, trees and doodads (Greenvale)

Greenvale is the hill country between Brennmark's market towns and the Tormai Herd Road (neutrals §2.1): golden-green meadows, ochre
cart roads, drystone walls, mossy standing stones, hedgerows and ponds.

### 6.1 The tile ladder (7 tiles)

Draw order runs bottom to top: a later tile overlaps an earlier one at a shared corner, so edges look natural (grass creeps over road,
road over dirt). Colours are **albedo targets after the saturation clamp** (terrain ≤ 45 %); the night and day LUTs and the 1.05–1.12
grade saturation bring the meadow back toward the warm golden-green of visual §7.2 on screen.

| Order | Id | Tile | Base / dark / light | Accent | Value | Use | `TILE_SUBJECT` (T6) |
|---|---|---|---|---|---|---|---|
| 0 | `gv_scree` | Mossy scree | `#7D766A` / `#5E574E` / `#9A9284` | moss `#5B7A43`, lichen `#AAB061` | 37–60 % | Cliff bases, rocky knolls, the Standing Ring camp | broken flat grey stones and coarse gravel with green moss and yellow lichen in the cracks |
| 1 | `gv_cracked` | Cracked earth | `#A88C60` / `#7E6544` / `#C2A878` | pebbles `#9A8F7C` | 45–66 % | High dry ground, mine fronts | dry sun-baked ochre-tan earth with a few wide shallow cracks and scattered pebbles |
| 2 | `gv_dirt` | Packed dirt | `#8C6F4D` / `#6E5236` / `#A6845A` | stones `#9A8F7C` | 40–62 % | Worn ground around halls, camps and kingdom building pads | warm brown packed earth with small stones and faint boot and hoof dimples |
| 3 | `gv_road` | Cart road | earth `#A08560`, ruts `#7E6A4C` | flagstones `#9A8F7C` | 45–63 % | Paths between starts, expansions and the Weighstall | ochre packed-earth cart track with two faint wheel ruts and a few sunken flat grey flagstones |
| 4 | `gv_grassy_dirt` | Grassy dirt | `#7E7A45` / `#6A5A3A` / `#8E8A55` | tufts `#799A55` | 40–58 % | Transitions, shores, under trees, clans building pads | brown earth half covered by sparse short grass tufts and tiny clover leaves |
| 5 | `gv_meadow` | Meadow (main ground) | `#799A55` / `#5F7A43` / `#8DAE60` | clover `#6E8E50` | 45–65 % | Default ground | short golden-green meadow grass with small clover clumps and soft directional brush strokes |
| 6 | `gv_thick_meadow` | Thick meadow | `#5B7A43` / `#486236` / `#6E8E50` | wildflowers `#E8DC8A`, `#EDE6D2` (≤ 2 % cover) | 35–55 % | Hollows, forest floors, pond margins | deeper green longer grass in soft clumps with a few tiny pale yellow and white wildflowers |

**Rules**

- **Neighbours:** paint transitions only between ladder neighbours. The painter auto-inserts the step between (thick meadow → meadow →
  grassy dirt → dirt). The road may border any tile below meadow; meadow overlaps road edges.
- **Edges:** the 16-case corner-mask blend (README §2) uses a world-space noise threshold (amplitude 0.35 tile, about 1.7 cycles per
  tile), so transitions look brushed, never tile-aligned. No soft splat blending.
- **Repetition:** world-space UVs (512² per 4 m), 2–3 rotated samples blended by noise, and a macro tint (30–60 m period, ±6 % value,
  ±4° hue). Each tile may ship 2 variants (from a 2×2 grid generation) chosen per tile by hash.
- **Building pads (faction texture at map scale):** kingdom footprints repaint to `gv_dirt` with a ring of `gv_road` flagstones at the
  door; clans footprints repaint to `gv_grassy_dirt` (they trample, they do not pave). Creep camps use `gv_dirt` (Sootcoats), `gv_thick_meadow`
  plus furrows (Tattiebogles) and `gv_scree` (Cairnwakes).
- **Lanes stay clear:** doodads cluster at transitions, cliff tops and shores, never across a path.
- **Optional 8th tile (later):** `gv_mud`, wet pond-margin mud, if shores read dry with the water shader's darkening alone.

### 6.2 Cliffs and ramps

| Item | Rule |
|---|---|
| Height | One level = `CLIFF_H` (architecture 1.75 m; README suggests 2.0 m). Art is authored for 2.0 m and scales down without change |
| Face texture (T7) | `CLIFF_SUBJECT` = "layered pale grey limestone blocks in thick horizontal courses, with a little green moss on the ledges". Colours: top light `#8A8276`, mid `#7D766A`, crevice `#5E574E`, moss `#5B7A43`. Triplanar on the face |
| Second face (T7) | `CLIFF_SUBJECT` = "a steep earth bank with exposed roots, packed brown soil and a few embedded stones", for river banks and low lowland steps |
| Silhouette | Chunky marching-squares walls with noise bulges (`architecture.md`, terrain section); a painted lighter top lip; the face reads as a cube, not a slope |
| Top lip | Meadow or grassy dirt overhangs 0.3 m with grass-tuft cards; 1 in 4 tiles gets a shrub or small rock |
| Base | A one-tile band of `gv_scree` plus 3–7-object rock clusters (§6.4) |
| Ramp | Two tiles wide, painted `gv_road` or `gv_dirt`, edged with low stone kerbs (doodad) |
| Value | Cliffs stay at saturation ≤ 30 % and never get brighter than the meadow on their top |

### 6.3 Water

| Item | Value |
|---|---|
| Shallow (walkable) | `#4FA3A0`, painted ripple texture (T5: "seamless hand-painted shallow water ripples seen from above, soft teal with pale highlights"), scroll 0.05 m/s |
| Deep | `#22566E` |
| Shore | The water shader darkens adjacent ground 25 % in value within 1 m (the "wet band") and draws a soft foam line `#E8F0EC` at 40 % alpha |
| Night | Water takes the moon tint; fireflies (neutrals §6) drift over shallow water |
| Doodads | Reed clumps, lily pads with a few white flowers, a fallen log, flat stepping stones |

### 6.4 Trees and doodads

Trees and doodads are **procedural in bpy** (trunk lathes, leaf-clump cards, slab and boulder primitives) with AI-painted textures
(T5, T8). Only one-sided hero doodads may use TRELLIS.

| Species | Height | Shape (silhouette from the game camera) | Colours | Notes |
|---|---|---|---|---|
| Hill oak | 6–7 m | Broad round canopy of 4–6 clumps | Leaves `#5F7A43` interior → `#8DAE60` sunlit top; trunk `#5A4630` | The default tree-wall species |
| Linden | 6.5 m | Taller rounded cone, heart-shaped leaves | Leaves `#7E9A4A` → `#A6B860`; summer blossom specks `#E8E2A0` | Ties to the kingdom's folklore; mixed into tree lines near kingdom starts |
| Hazel | **4.5–5 m** ("tall coppice") | Many-stemmed coppice grown tall, its crown overlapping its neighbours' | `#6E8E50` | **A harvestable tree like the others**: 50 lumber (rules §4.2), blocks pathing and sight like every tree (rules §14.3), leaves a stump. It fills gaps inside tree lines only, so every tree line stays uniformly harvestable. **Tree-wall rule:** every tree that blocks pathing and sight has its crown top ≥ 4.5 m and a canopy that overlaps its neighbours, because from the −56° camera a low clump among tall crowns reads as a gap, and players read chokes and wall-offs from solid, uniform tree walls. Short shrubs exist only as non-blocking doodads. Decorative hedges are the hawthorn doodad below, kept out of tree lines; they block pathing but not sight |
| Stump (after felling) | 0.4 m | Cut stump with pale rings `#E9CF9B` | | Replaces a felled tree |

Tree-line rules: irregular edges, 2–3 species mixed, ±20 % scale, random yaw, per-instance hue jitter ±3°, crown sway in the vertex
shader (0.5 Hz, 3 cm at the crown). Birch, willow and spruce are **not** used in Greenvale, to keep them free for later biomes and for
`sylvan` motifs.

| Doodad (Greenvale) | Notes |
|---|---|
| Mossy boulders (3 sizes) | Rounded flat-topped stones with moss caps |
| Drystone wall (straight, corner, broken end) | Stacked flat slabs; the Cairnwakes' material, so they feel "of the land" |
| Hawthorn hedgerow segments | Dark green with white blossom specks; good map dividers. Non-harvestable, never placed inside a tree line, blocks pathing but not sight |
| Wattle fence | Woven hazel panels, never picket fences |
| Hay stooks | Small leaning sheaves, not round bales |
| Wildflower clumps | Yellow, white and a little blue (blue only as tiny flowers) |
| Reeds and lily pads | Shores only |
| Mushroom ring | Pale caps in a circle, deep woods only |
| Beehive skeps | Straw domes on a plank, near kingdom-side farms |
| Broken cart | A wrecked market wagon (kitbash of the kingdom wagon parts) |
| Milestones and small cairns | Neutral, along roads |

Clusters are 3–7 objects (a rock, a shrub, two tufts, a flower clump), placed at transitions, cliff tops, shores and camp edges.

---

## 7. UI art direction

### 7.1 Layout: the structure is the genre's, the proportions and art are ours

Kept (functional, ip-safety §2.4): **one bottom console strip** with the minimap at bottom-left, portrait and info in the centre, a 4×3
command card at bottom-right and a 2×3 inventory for heroes; a top bar with menus on the left, the day/night indicator in the centre and
resources on the right; hero buttons down the left edge; an idle-worker button. Fans of the genre read the console as one strip, so we
keep it as one. **Ours:** the strip is a **low-opacity band carrying four translucent plates** with gaps where the band (and faintly
the world) shows through, it is thinner (under 20 % of screen height), and every piece of chrome is original. ip-safety §2.4 frees the
console itself; only the reference frame art is protected, and none of ours resembles it (§7.2, §7.11).

Geometry at 1920 × 1080 (UI scale 1.0; art authored at 2× for HiDPI). **This table is the single source for sizes**; the juice specs
animate these widgets but do not resize them (POR-01 and NTF-05 values are adopted here).

| Element | Size (px) | Position | Notes |
|---|---|---|---|
| Top bar | Full width × 34 | Top | `UI_PLATE` at 85 %; resources on the right: gold, lumber, food used/cap, upkeep label |
| Horizon Ribbon | 260 × 44 | Top centre, hanging 10 px below the bar | §7.5. It sits where the genre's clock sits, but it is a flat strip, not a dial |
| Menu buttons | 4 × (30 × 26) | Top left | Menu, Log, Help, (Allies later) |
| Hero buttons | 64 × 64 + HP bar 6 + mana bar 4 + level badge 22 | Left edge from y = 52, 10 px apart | Up to 3 (§7.9) |
| Idle-worker button | **52 × 52** + count badge (14 px, bottom-right) | **Left end of the console's top edge, above the minimap's top-left corner** (juice NTF-05) | |
| Console band | Full width × 212 (19.6 %) | Bottom | `UI_PLATE` at **40 %** opacity with a 1 px linen top line (`#D9CCAE` at 25 %); joins the plates into one strip. No ornament on the band. **The whole band blocks input** (`MOUSE_FILTER_STOP`, gaps between plates included): the playfield ends at the band's top edge, so the world that shows faintly through the gaps never takes a click (stray orders). The top bar and the Horizon Ribbon block input the same way |
| Minimap plate | 212 × 212 (map 196 × 196) | Bottom-left, on the band | **3 toggles** (24 px) on its right rim (rules §18.7): **Formation** (three small figures in a row behind a pennant; filled when on, the default), **Show Camps** (a shield pip; default on), **Colour mode** (a two-tone disc: team colours ↔ self / ally / enemy; also Alt + A). The 4th slot is reserved for Ally ping (*later*; Alt + click, rules §18.1) |
| Portrait plate | **166 × 196** | Right of the minimap, 8 px gap | **150 × 150 live 3D portrait** (juice POR-01) with its 3 px team-colour inner band; HP and mana bars beneath |
| Info plate | Stretches (minimum 560 wide) | Centre | §7.8: name, level and XP; attack and armour with type glyphs and upgrade pips; for heroes STR / AGI / INT with the primary attribute marked and bonuses in green. **Selection grid** (more than one unit): 2 rows × 6 tiles of 40 px, 4 px gaps, each tile with a 4 px HP bar and, for units with mana, a 3 px mana bar underneath (`UI_HP` ramp, `UI_MANA`). **Build queue** (rules §4.6, 7 slots): one active 48 px icon with a progress bar and the seconds remaining, then 6 waiting 40 px icons; clicking a waiting icon cancels it. **Hall upgrade or research in progress:** its icon with a progress bar and the seconds remaining. **Selected Gold Seam:** "Gold remaining 12,000" with the nugget glyph |
| Inventory plate | 116 × 172 (2 × 3 slots of 50 px) | Right of the info plate | Heroes only; the plate collapses otherwise. Slots follow the §7.4 corner table (numpad chip, charges, cooldown sweep) |
| Command plate | 252 × 196 (4 × 3 buttons of 56 px, 4 px gaps) | Bottom-right | Hotkey chips (§7.4) |
| Tooltip | 340 wide, grows upward | Above the command plate | §7.3 |
| Toasts and alerts | 480 × 64 | Centre-left, above the console | Research complete, upkeep change |

### 7.2 Shared chassis, faction inlays

- **Chassis (every faction):** plain dark plates (`UI_PLATE` `#14110E`, 85 % opacity) with 6 px rounded corners and a 1 px inner linen
  line (`#D9CCAE` at 25 %), sitting on the 40 % console band (§7.1). The chassis and the band carry no ornament, so the HUD never reads
  as one carved slab.
- **Inlays (the faction's identity):** only on plate rims (≤ 14 px), corners, button bezels, the top-bar end caps and the Ribbon's end
  caps. Centres stay plain so icons and numbers lead: **no leather or parchment panel fills and no crest at the console centre**. The
  local player's faction skins the HUD.
- **Motion on the inlays (adopted from juice HUD-07):** the lit-frame highlight band (day `#FFE7B8`, golden hour `#FFC27A`, night
  `#9FB4FF`) and the cloud catch run along the inlay rails and fasteners only; the two night lanterns hang at the outer corners of the
  console band (kingdom: small iron lanterns; clans: small bronze lamps on felt loops).

| Inlay | Rails | Fasteners and corners | Accent band | `UI_CLAUSE` for T11 |
|---|---|---|---|---|
| **Kingdom** | Carved dark oak stained burgundy (`#3A1E1A`, highlight `#6B3A2E`), 10 px, with one shallow carved groove | Domed dark-bronze rivets (`#8A5E2E`) every 48 px; blackened-iron strap brackets at the corners shaped as curved segments of a wagon-wheel rim with two spoke stubs; small six-spoke bronze wheel bosses on the top-bar end caps | A 6 px folk-painted band of small ivory flowers and stripes (`#E6D8B8` on burgundy) along the inner edge, deliberately a little uneven | carved dark oak rails stained burgundy, rounded dark bronze rivets in an even row, blackened iron strap corner brackets shaped like curved segments of a wagon-wheel rim, a thin folk-painted band of small ivory flowers and stripes along the inner edge |
| **Clans** | Stitched ink-teal felt bands (`#173E42`) wrapped over **ochre-washed lattice-wood** (`#B7772A`, highlight `#C9A46A`), whose diamond trellis shows in the gaps between plates. **Red-brown never appears on UI art** (it is the reference warrior race's console colour; slice-plan §2.9 I3) | Rows of small polished bronze studs (`#A8743A`) every 32 px; small round bronze gong discs (`#C68E4C`) hung from felt loops at the corners; small gongs on lattice posts as top-bar end caps | Saffron blanket-stitch (`#D49A36`) along the inner edge | stitched ink-teal felt bands wrapped over ochre-washed diamond lattice-wood, saffron blanket-stitch along the inner edge, rows of small polished bronze studs, small round bronze gong discs at the corners |
| **Neutral** (main menu, shop window, neutral and creep info, loading band) | Pale ash wood (`#B8A07A`) | Small pewter corner clasps (`#8E9196`) | A fine sage-green woven border (`#7E9A6E`) on undyed linen (`#D9CCAE`) | undyed cream linen stretched over pale ash wood, small pewter corner clasps, a fine sage-green woven border |

Never in any inlay: gilded metal, carved stone, gargoyles, skulls, relief faces, spikes, or a slab that spans the whole console.

### 7.3 Frame parts

| Part | Size at 1× (author at 2×) | 9-slice margins | Method |
|---|---|---|---|
| Plate frame (one per inlay) | 256 × 256 | 24 | T11 `[PART]` = "rectangular panel border" |
| Top-bar strip and two end caps | 1024 × 48 strip, 96 × 48 caps | 16 / 48 | T11 "long horizontal top-bar strip with two separate end caps" |
| Minimap housing | 224 × 224 | 14 | T11 "square frame" |
| Portrait housing | 176 × 206 (around the 150 × 150 viewport and its bars) | 14 | T11 "tall rectangular frame" |
| Hero-button frame and level badge | 72 × 96 frame, 26 px badge | — | T11 plus a procedural badge (kingdom: the full Ember Wheel with its hub coal and crown points, the level number on a small burgundy plate under the wheel; clans: a gong disc with the number) |
| Horizon Ribbon housing | 280 × 56 | — | T11 "wide shallow window frame" plus a painted hill strip (T5-style) |
| Command button bezels (normal, hover, pressed, disabled) | 64 × 64 | 8 | **Procedural** (Pillow or a Blender bake from the swatches): bezels need exact pixel edges |
| Icon frames: normal, hero ability (chamfered corners), passive (inset), item (pewter) | 128 × 128, 6 px border | — | Hand-made once per inlay (pipeline §4.4) |
| Ability rank frames (juice HER-05) | 128 × 128 rim variants of the hero-ability frame | — | Hand-made per inlay, shape-coded so rank never relies on colour: **rank 0** (unlearned) a thin dark rim; **rank 1** a plain bronze rim; **rank 2** the rim with two notches at top and bottom; **rank 3** a closed double rim |
| Tooltip box | 64 × 64 | 12 | Procedural: chassis plus a 1 px faction trim line (kingdom bronze `#B07F3E`, clans saffron `#D49A36`, neutral sage `#7E9A6E`) |
| Toast banner | 480 × 64 | 20 | T11 "long narrow banner frame" |
| Main-menu button | 320 × 64 | 20 | T11, neutral inlay |

Budget: 3 inlays × about 6 T11 generations ≈ 18 × 9 CU = **162 CU** (plus retries); everything else is procedural.

### 7.4 Buttons, icon frames and states

**Corner table** (one owner per corner, so no two markers ever collide; it binds the command card, the inventory, shop cards and hero
buttons):

| Place | Marker | Notes |
|---|---|---|
| Top-left | Learnable "+" seal (hero abilities) **or** the charge count (items, 13 px tabular with a 2 px dark outline) | Never both: items have no "+" |
| Top-right | The bronze **lock** glyph (missing requirement, juice HUD-05) **or** the **autocast badge** (a small looped arrow) | Never both: a locked ability cannot be toggled |
| Bottom-left | The **short-resource glyph** (coin, log, loaf, drop; juice HUD-05) | Only while unaffordable |
| Bottom-right | The **hotkey chip**: 18 × 18 px, cream letter (Alegreya Sans Bold 13 px) on `#14110E` at 85 %. Inventory slots show the **numpad digit** (7 / 8 / 4 / 5 / 1 / 2, rules §6.8) in a 14 px chip; the laptop preset shows Alt+1…6 | |
| Bottom-centre | Shop stock count ("2/3", 12 px tabular) on shop cards | Shop cards never autocast |
| Bottom edge | The **autocast bar** (below) | Abilities only |
| Rim | Rank frame (§7.3), hover and pressed rims | |
| Face | Cooldown sweep, disabled greyscale, unaffordable hatch | |

| State or marker | Look |
|---|---|
| Hover / pressed | +10 % brightness and a 1 px light inner rim / 1 px down and 10 % darker (press and release motion: juice HUD-01) |
| Disabled | Greyscale × 0.55 (pipeline §4.4) |
| Unaffordable | Full colour with the juice HUD-05 hatch and the bottom-left short-resource glyph; the short cost turns `UI_INVALID` in the tooltip. Never a full red wash over the icon |
| Cooldown | Clockwise radial sweep (`UI_COOLDOWN`) with the remaining seconds (Alegreya Sans Bold 16 px) centred while ≥ 1 s. **Item slots use the same sweep** (shared cooldown groups, rules §6.8) |
| Autocast capable, off | A 1 px dim rail along the bottom edge (`#14110E` lightened 20 %) |
| **Autocast on** | A **steady 3 px bar in the faction accent** along the bottom edge (kingdom ember `#F08A2A`, clans saffron `#E0A030`) plus the looped-arrow badge top-right. The only motion is a slow **0.5 Hz brightness breath on the badge** (α 0.75↔1.0). **No corner marks, no dots, nothing that travels around the edge** (§7.11) |
| Autocast fires (selected unit) | The bottom bar brightens once along its length, left to right in 300 ms, and the badge pops 1.0→1.15→1.0; at most once per 400 ms. The light stays on the bottom edge |
| Passive | Inset frame, no hotkey chip |
| Learnable skill | The top-left "+" seal pulses (scale 1.0 → 1.08, 1.2 s) |
| Research level | 1–3 pips under the icon; one icon per research line |
| Queue | The active item as a 48 px icon with a progress bar and the seconds remaining; up to 6 waiting items as 40 px icons (rules §4.6: 7 slots); layout in §7.1 |

### 7.5 The Horizon Ribbon (day/night indicator)

A flat, wide window instead of the genre's round clock. It shows *where in the day we are* as a landscape, not as a dial. It replaces
the two faction clock faces in juice HUD-07 (the kingdom 24-hour dial and the clans mirror disc); HUD-07's golden-hour rim, dusk/dawn
clunk and day tally move onto the Ribbon as below. The token position is hour-driven and interpolated (`DayNight.current_hour()`), so
it glides.

| Element | Design |
|---|---|
| Housing | 260 × 44 px window at the top centre, with faction end caps (kingdom: carved oak posts with small bronze wheel bosses; clans: small bronze gongs on lattice posts) |
| Landscape strip | A painted silhouette of low Greenvale hills along the bottom 12 px, with five tiny fence posts marking 06:00, 09:00, 12:00, 15:00 and 18:00 |
| Sun token | A 16 px disc `#FFE7A8` with six short blunt rays. It rises from the left hills at 06:00, arcs to the top at 12:00 and sets into the right hills at 18:00 |
| Moon token | A 14 px pale crescent `#C8D4E8`, rising on the left at 18:00 and setting on the right at 06:00 |
| Sky band | Day: gradient `#CFE3F0` → `#9DB3D6`. Dusk and dawn (±30 game-minutes): a warm band `#F2B36B` crossfading over 3 s with the stinger (§9.7). Night: `#1C2433` with five star pips |
| Creep hint | At night the closed-eye sleep glyph (neutrals §1.5) lights in the right end cap |
| Golden-hour rim | 16:30–18:00 (the last 30 s of day, juice WLD-02): the housing rim glows `#FFC27A`, α 0.35↔0.6 on the HUD ambient clock |
| Dusk/dawn clunk | At 18:00 and 06:00 the end caps act once, on the second note of the dusk or dawn stinger: kingdom, the wheel bosses ratchet one notch with an escapement clunk; clans, the small end-cap gongs are tapped and a felt shutter slides across the sky band (sound `ui_clock_<faction>`, §9.2) |
| Day tally | Each 06:00 the Ribbon records the night survived. Kingdom: a 6 px knife notch cut into the lower housing rim. Clans: a bronze bead drops onto a felt cord hung under the Ribbon. Marks group in fives (four notches crossed by a fifth; five beads knotted) |
| Clock text | Optional "hh:mm" in Alegreya Sans Bold 14 px to the right of the window (setting) |
| Tooltip | "Day. Dusk in m:ss." / "Night. Sight is shorter and most creeps sleep. Dawn in m:ss." |
| **Never** | A sphere, orb, globe or rotating ball; a disc split into sun and moon halves; a round clock face or dial with hands (the kingdom's astronomical clock exists only as architecture on the T3 hall, §4.2) |

### 7.6 Cursor set

Hand-drawn vectors rendered to PNG by script (pixel control at 32 px matters more than painterliness), set as hardware cursors with
`Input.set_custom_mouse_cursor`. **Never a hand, gauntlet, glove or claw.**

| Cursor | Shape | Size and hotspot | Colour |
|---|---|---|---|
| Pointer | An upright arrow with a slightly flared, notched tail. Tail ornament: kingdom a tiny six-spoke bronze wheel; clans a tiny felt tassel with a bronze bead | 32 px (48 px HiDPI); tip at (1, 1) | Kingdom: iron `#3D4046` with a 1 px ivory edge. Clans: bronze `#A8743A` with a cream edge |
| Hover own / enemy / neutral | The pointer plus a small corner bracket under the tip | Same | `#46E07A` / `#FF4B3E` / `#FFC93C` |
| Target (spell or attack) | A ring with four notches, from the order-marker family (juice CMB-08). Red over a valid enemy; grey with a diagonal slash over an invalid target | 48 px; centre | White base |
| Attack-move | The ring with four inward chevrons | 48 px; centre | `#FF5A36` |
| Placement | Hidden; the ghost building shows validity (juice economy §3.5) | — | — |
| Edge scroll | Eight chunky outward chevrons | 32 px | Faction accent outline |
| Busy | Kingdom: a turning spoked wheel. Clans: a swinging gong. 8 frames | 32 px | |
| Drag box | 1 px line with 3 px corner ticks | — | `#46E07A` |

### 7.7 Fonts (all SIL Open Font License 1.1, licence files confirmed in the Google Fonts repository on 2026-10-16)

| Role | Font | Repository dir | Sizes at 1080p | Notes |
|---|---|---|---|---|
| Body, tooltips, resource numbers | **Alegreya Sans** (Regular, Bold, ExtraBold) | `ofl/alegreyasans` | 14–20 px | Humanist and readable small. Use tabular lining figures for resources if the font exposes `tnum`; otherwise right-align in fixed-width labels |
| Headings, unit names, menu buttons | **Alegreya SC** | `ofl/alegreyasc` | 18–32 px | Calligraphic small caps |
| Kingdom display (faction name, banners, loading plate) | **Grenze Gotisch** | `ofl/grenzegotisch` | ≥ 28 px only | Broken-script flavour for a late-medieval Central European kingdom; never for body text |
| Clans display | **Philosopher** (Bold) | `ofl/philosopher` | ≥ 24 px | Soft triangular serifs. No faux "exotic" script fonts |
| Floating combat text | Alegreya Sans ExtraBold | — | 16–22 px, 2 px dark outline | Juice CMB-28 |

Rules: no flared glyphic display serif of the kind long associated with the genre's best-known UI (ip-safety §2.4); licence texts ship
in `assets/fonts/` and are listed in `CREDITS.md`; UI strings use no diacritics (kingdom §1.1).

### 7.8 Glyphs

| Glyph | Design | Colour |
|---|---|---|
| Gold | A faceted nugget (same as the Gold Seam minimap glyph, neutrals §5.2) | `UI_GOLD` |
| Lumber | A split log end with two growth rings | `UI_LUMBER` |
| Food | Kingdom: a round loaf with a scored top. Clans: a steaming stew bowl | `UI_FOOD` |
| Upkeep | The notched coin with the label "Upkeep 0 % / 30 % / 60 %" (rules §4.5) | `UI_UPKEEP` tokens |
| Attack types | Blade: a single-edged blade. Pierce: an arrowhead. Siege: a round shot. Arcane: a four-pointed spark. Heroic: a blade with a star pommel. Raw: a cracked diamond. Spell: a swirl | Cream on dark |
| Armour types | Light: a quilted vest. Medium: a lamellar plate. Heavy: a plate with a brim. Fortified: a squared stone block. Hero: a shield with a star. Unarmored: an empty outline. Adamant: a faceted square boss (*later*; rules §7.1) | Cream on dark |
| Upgrade pips | 0–3 small square pips under the attack and the armour glyph in the info plate, one per finished weapon or armour research level (filled `#F3E6C4`, empty outline) | Cream on dark |
| **Hero attributes** | **STR:** an iron anvil. **AGI:** a leaping hare. **INT:** a lit candle. Shown as "STR 23 +2": base value in `UI_TEXT`, item and aura bonuses in **`#7FD86A`** after a space. The **primary attribute** is drawn at 1.25× with a 2 px underline in the faction accent | Cream on dark |
| Bonus damage and armour | "24–30 +4" and "Armour 5 +2": the base in `UI_TEXT`, bonuses from upgrades, items and auras in `#7FD86A`; reductions in `UI_INVALID` | |
| Minimap camps | Shield-shaped pips with a top notch (neutrals §1.2): green `#5FBF4A`, amber `#E8A93A`, red `#D9483B` | |
| Minimap neutral buildings (neutrals §1.2) | Gold Seam: a faceted nugget. Weighstall: a balance beam with two pans. Hale Spring: a droplet inside a ring. Coaching Inn: a hanging lantern. *Later:* Dewstone, an upright stone with one droplet; Hiring Fair, two crossed tally sticks; Beacon Cairn, a small flame (team-coloured when lit); Lucky Barrow, a cart wheel; Twin Milestones, two short posts joined by a dotted line | Pale ivory with a dark rim |
| Minimap ping | Three expanding rounded squares over 0.8 s, in the pinging player's team colour | |
| Sleep | Closed-eye glyph plus drifting snore puffs, never letters | |
| Hero level badge | Kingdom: the full Ember Wheel (ivory wheel, dark-bronze hub coal with its ember core, three crown points) with the level number on a small burgundy plate under the wheel, so the coal is never covered. Clans: a gong disc with the number | |

### 7.9 Hero buttons and portraits

- **Hero button:** the T10 bust in the hero frame, HP and mana bars, the level badge, a pulsing "+" seal when a skill point is free.
  While dead: desaturated, with a revive ring that fills clockwise and the seconds remaining in the centre.
- **Console portrait:** a **150 × 150** live 3D view (juice POR-01 framing, light and pacing), driven by the voice envelope (juice
  CMB-14), inside a 3 px team-colour inner band. Background plate gradient (POR-01 values, adopted): kingdom `#3A1A14` → `#7B1E2E`;
  clans `#0F2E33` → `#2F7E7E`; neutral `#2A2622` → `#14110E`; each with a soft vignette.

### 7.10 Loading screen, menus and end screen

| Screen | Design |
|---|---|
| Loading | Full-bleed T12 tableau of the map. A lower info band (18 % of the height, neutral inlay at 80 %): the map name in Alegreya SC 40 px; two player plates (faction emblem, player name, team-colour swatch, faction name in its display font); a rotating tip in Alegreya Sans 18 px. Progress is a **road ribbon** along the band on which the local faction's token travels left to right (kingdom: a small wagon; clans: a felt cart). No bar |
| Greenvale tableau `SCENE` | a summer hill country of golden-green meadows and ochre cart roads; on the left, half-timbered houses with burgundy roofs and a small bronze onion dome behind a ring of parked wagons; on the right, low ink-teal and saffron felt domes with carved masts around a great sun-bleached tortoise-shell hall; in the middle distance, a market stall under a giant brass balance beside the road; drystone walls, a pond and hedgerows |
| Main menu | The tableau, 20 % blurred, behind a neutral linen-and-ash column of buttons on the left third. Menu music (§10.3) |
| End screen | Our own score summary (rules §17.1), with the faction stinger crossfading into the "Two Roads (score)" bed (§10.1). Title "Victory" or "Defeat" in the faction display font, with a faction subtitle: kingdom "Every wheel held." / "The boards are down."; clans "The bill is settled." / "We will return, with more tea." |

### 7.11 UI anti-patterns (rejected in review)

- One continuous carved console slab (the plain 40 % band of §7.1 is not a slab: it carries no ornament); leather or parchment panel
  fills or a crest in the console centre; gilded metal, carved stone, gargoyles, skulls or relief faces.
- A round day/night orb, globe or clock dial; a hand or gauntlet cursor.
- **Corner marks, dots or chasing lights around a button**, or any light that circles a button's edge (autocast is the bottom bar and
  the badge, §7.4).
- Reference-style icon bevels, button art, fonts, loading layout or score-screen layout.
- Text baked into any generated image. All text is rendered by Godot.

---

## 8. Voice

### 8.1 Rules

**Writing**

1. **Lengths are budgeted in words and seconds** (§8.2), and the two budgets agree: word cap ÷ minimum rate ≤ the seconds cap for every
   category. Acks must land on the click: **What and Yes ≤ 4 words at ≥ 3.0 words/s** (≤ 1.33 s against the 1.4 s cap); **Attack ≤ 4
   words** and **Warcry ≤ 5**, both at ≥ 2.8 words/s; the short situational lines (`need_mana`, `pack_full`, `ab_q/w/e`,
   `ultimate_shout`) ≤ 4 words; Ready, built, mechanic, level-up and rival ≤ 8; last word ≤ 6; **Annoyed ≤ 16 per line**; all of these
   at ≥ 2.5 words/s; advisor lines ≤ 11 words at ≥ 2.5 words/s. Every speaker obeys these rates. Size, age and weight come from pitch,
   formant and EQ (the post-chains in §8.3–§8.4), never from a slow read. The clans' "*Hm-hm*" is used **only in Ready, Annoyed and
   advisor lines**, never in an ack.
2. **Character comedy only**: trade, guild habits, etiquette, family, weather, food, pride in craft. No film, celebrity, brand, meme or
   pop-culture references (comedy-film gags included); no puns on other games' lines.
3. **Never** use a line from the reference game's quote pages or a paraphrase of one (ip-safety §2.2 lists the most famous). Also avoid:
   - the word **"poke"** (and "poking", "poked") in any line: it is the genre's best-known annoyed-line verb;
   - the "For the [faction]!" warcry pattern;
   - stock military acknowledgements of the kind the reference RTS made famous, broken-English worker grammar, and dialect "me" for
     "my" (the register of the reference RTS's dwarf gunners);
   - **jokes about voting for, electing or doubting the king or the Crown**: a worker doubting the monarch's legitimacy is the reference
     human worker's best-known annoyed joke (itself a comedy-film gag), and the kingdom's elected Wheel Crown makes the trap easy to fall into;
   - on **kingdom completion events** (`built`, the advisor's research and building lines): any "…'s done" and a bare "Done.", and
     the "[build verb] more [supply building]" advisor template (kingdom §3.2 Reeve rules). Our completion lines name the craft instead
     ("Signed, sealed and plastered");
   - any line that contradicts a design rule (no "big ears" for the Tormai, whose ears are small and rounded; no curved blade for the Uncut);
   - **any line that is a reference line with only the address word changed** (chieftain, warchief, master, lord or the reference human worker's contraction of "my lord" swapped for
     Ring-Elder, Reeve or any other title of ours): a one-word swap keeps the reference line's structure, and ip-safety §2.2 bans
     rewordings;
   - for **any wind speaker** (the Gustcaller, the later Sky-Kite): no flatulence or "breaking wind" double entendre, no voices- or
     spirits-are-talking-to-me framing, and no "to the winds" or "winds guide" phrasing (the reference RTS's wind-rider and
     flyer-rider acks and its spirit-caster annoyed bit live there).
4. **Real cultures are inspiration, not costume:** no faux Czech or German accent for the kingdom, no faux Central Asian accent for the
   clans, no real ethnonyms, deities or sacred terms (kingdom §3.1, clans §1.4).
5. **Faction vocabulary.** Kingdom: ledger, fee, guild, journeyman, the boards, the wheel, wagon, mortar, strongbox, the Reeve.
   Clans: guest, tea, felt, stew, the Long Sky, sun-teeth (gold), lattice-wood (lumber), the Stones, the gong, "Hm-hm".
6. **One verbal tic per speaker** (§8.3, §8.4), and every annoyed sequence is a micro-story of exactly the recorded length (§8.2: 5
   lines, 7 for heroes and each faction's standout), played in order, with the **punchline in the last line**.
7. **Crews.** Two bickering voices on the gunpowder-siege slot would repeat the reference RTS's two-gunner double act, so the **Bombard
   Wagon has one speaking voice** (the older gunner) and a non-verbal loader (coughs and grunts as SFX), with no exchanges and no
   shared annoyed story. The Sling-Cart's two brothers **speak in unison** (one shared sentence or a hauling count; slice-plan §2.12,
   decided 2026-10-19): **no line or punchline is split between two voices**, no self-identity confusion (who is who, which side we are
   on), no "you and me" or "synergy"-style partnership lines and no explosion punchlines. Their hook is that they always agree, even
   when wrong. The script reviewer checks their lines against the reference two-gunner team's quote section specifically.
8. **Review gate:** a second person checks each script against the reference quote pages (audio §3.2 links), the shelved concepts in
   `docs/concepts/alternate-concepts.md`, and the other factions' scripts; the ledger records who checked and when. The check includes
   an **exact-match search** of every What, Yes and Attack line (and every short Ready and Warcry line) against all five unit quote pages
   of the reference RTS (the four races and the neutral page) and its hero quote pages: even a common two-word ack that appears there
   is replaced, whatever its legal weight, because the project rule is "if it is on a quote page, do not use it".

**Delivery and playback** (audio §3.5; rules §17.3)

- ElevenLabs TTS through Krea (`elevenlabs/tts`, `model_id: eleven_v4`), **preset voices only**: no cloning, no voice design, no real
  person's voice. **No preset is used by both factions** (casting candidates in §8.3–§8.4 are auditioned with the 5-line probe first).
- Generate every slice line **before 31 Dec 2026** (default voices expire) and archive the raw takes in `assets_src/audio/voice/`.
- **Trigger rules live in juice AUD-03 only** (debounce, annoyed counting and reset, warcry chance and cooldown, ready spacing, punchline
  protection) and in the heroes juice for hero categories. This bible supplies the lines, their order and their length.
- **Ability orders play exactly one line, on the input frame:** the ability line (`ab_q`, `ab_w`, `ab_e` or `ultimate_shout`) if it passes
  its gate (proposed: 50 % chance, 8 s cooldown per hero; the numbers move to AUD-03, §13 #16), otherwise `yes`. Never both, and the
  cast plays no second line.
- `built` (the AUD-03 category, label "Built"; the interim id that paired "job" with "done" is retired and its spellings are banned, because it echoes the reference worker's
  catch-phrase in file names, slice-plan §2.12) plays when that worker completes a building.

### 8.2 Line categories and counts

| Category (file id) | Trigger (owner: juice AUD-03 or heroes juice) | Words @ min rate | Max s | Worker | Infantry / ranged | Caster | Siege crew | Hero | Delivery |
|---|---|---|---|---|---|---|---|---|---|
| Ready (`ready`) | Trained; hero trained or revived | ≤ 8 @ 2.5/s | 3.3 | 1 | 1 | 1 | 1 | 1 | Character introduction |
| What (`what`) | Selected | ≤ 4 @ 3.0/s | 1.4 | 4 | 4 | 4 | 3 | 4 | Attentive, quick |
| Yes (`yes`) | Move or build order; an ability order whose line is gated out | ≤ 4 @ 3.0/s | 1.4 | 4 | 4 | 4 | 3 | 4 | Compliant, flavourful, quick |
| Attack (`attack`) | Attack or attack-move order | ≤ 4 @ 2.8/s | 1.6 | 3 | 3 (**4** for the Javelineer) | 3 | 3 (**4** for the Sling-Cart) | 4 | Short, aggressive |
| Warcry (`warcry`) | AUD-03 | ≤ 5 @ 2.8/s | 2.0 | 1 | 1 | 1 | 1 | 1 | Loudest delivery |
| Annoyed (`annoyed_1..n`) | AUD-03, in order | ≤ 16 per line @ 2.5/s | 7.0 | 5 | 5 (**7** for the faction's standout: Hookgunner, Javelineer) | 5 | 5 | **7** | The comedy beat; punchline last |
| Built (`built`) | That worker completed a building | ≤ 8 @ 2.5/s | 3.3 | 1 | — | — | — | — | Satisfied, names the craft |
| Mechanic (`mech`) | Worker: arm (Levy Horn, Take Up the Flail; Sound the Gong, Roll the Felt) **and** release (Lay Down Flails; All Clear). Pavisier: Plant Pavise **on and off** (2). Hookgunner: the first Braced Shot plant after a move order (≤ 1 per 20 s). Grappler: Shove (≤ 1 per 10 s). Bombard Wagon: the deploy brace (≤ 1 per 20 s). The Javelineer (Throwing-Sticks is a passive) and the Sling-Cart (no deploy) have **no** trigger, so their slot is an extra Attack line | ≤ 8 @ 2.5/s | 3.3 | **2** | 1 (Pavisier **2**, Javelineer 0) | — | 1 (Sling-Cart 0) | — | Situational |
| Need mana (`need_mana`) | Cast refused for mana (heroes HER-05, ≤ 1 per 8 s) | ≤ 4 @ 2.5/s | 1.8 | — | — | 1 | — | 1 | Mildly put out |
| Pack full (`pack_full`) | Pickup refused, inventory full (rules §6.8) | ≤ 4 @ 2.5/s | 1.8 | — | — | — | — | 1 | Wry |
| Ability (`ab_q`, `ab_w`, `ab_e`) | Ability order (gate in §8.1) | ≤ 4 @ 2.5/s | 1.8 | — | — | 2 | — | 3 | One per ability |
| Ultimate (`ultimate_shout`) | Ultimate order (replaces `ab_r`) | ≤ 4 @ 2.5/s | 2.0 | — | — | — | — | 1 | Big |
| Level-up (`levelup_a`, `levelup_6`) | Hero gains a level; level 6 plays `levelup_6`, the "ultimate unlocked" line | ≤ 8 @ 2.5/s | 3.3 | — | — | — | — | 2 | Proud |
| Rival (`rival`) | Enemy hero met or struck (heroes HER-02); generic line | ≤ 8 @ 2.5/s | 3.3 | — | — | — | — | 1 | Taunting, in character |
| Last word (`death_word`) | Hero dies | ≤ 6 @ 2.5/s | 2.5 | — | — | — | — | 1 | Short, never maudlin |
| **Recorded total** | | | | **21** | **19** (standout **21**; Pavisier **20**) | **21** | **17** | **31** | |
| Death (non-verbal) | Unit dies | — | 1.5 | 2 | 2 | 2 | 2 | 2 | Seed Audio vocal sets per faction body type (§9.3), not TTS |
| Effort (non-verbal, `effort`) | Hero heavy swings and casts (heroes juice) | — | 0.6 | — | — | — | — | 2 | Recorded in the hero's TTS batch with `[grunts]` tags |

**Engine names** (heroes juice `audio.gd`): `levelup_5` and `levelup_10` alias to `levelup_a` in the slice (their own lines are
[SLICE+]); `levelup_a` is recorded in 3 takes of the same text. Pair-specific rival lines (one per slice hero for each of the two enemy
slice heroes, 8 in all) are [SLICE+]; until then `rival` plays. `shop_*` are the Rundling shopkeeper's lines (neutrals §5.3);
the faction shops (Curio Cabinet, Tea Tent) have no shopkeeper voice.

**Advisor: 19 lines**, one per trigger in rules §17.3 and per alert category in juice NTF-01 (buildings with their own main-hall line,
units, workers, hero): need gold, need lumber, need supply, hero slot full, cannot build there, **hall attacked**, **other building
attacked**, units attacked, workers attacked, **hero in danger** (below 40 % HP), hero fallen, hero ready (trained or revived), research
finished, hall tier finished, mine low, mine exhausted, upkeep rises, no hall left (cripple countdown started), revealed to the enemy
(cripple revealed).

**Slice totals**

| Kingdom | Lines | Clans | Lines |
|---|---|---|---|
| Hodman (worker; also voices the Flail Levy) | 21 | Yurtwright (worker) | 21 |
| Pavisier (infantry; 2 toggle lines) | 20 | Grappler (infantry) | 19 |
| Hookgunner (ranged; standout, 7 annoyed) | 21 | Javelineer (ranged; standout, 7 annoyed; 4 attack, no mechanic) | 21 |
| Bombard Wagon gunner (siege; one voice, the loader is non-verbal) | 17 | Sling-Cart crew (siege; two voices; 4 attack, no mechanic) | 17 |
| Linden Sister (caster) **[SLICE]** | 21 | Gustcaller (caster) | 21 |
| Wheel Marshal (hero) | 31 | The Uncut (hero) | 31 |
| Firewright (hero) | 31 | Skymirror (hero) | 31 |
| The Reeve (advisor) | 19 | The gong-keeper (advisor) | 19 |
| **Kingdom total** | **181** | **Clans total** | **180** |

Neutral: Rundling shopkeeper 10 (neutrals §5.3). **Slice total: 371 lines.** [SLICE+]: Rat-Piper 31; pair-specific rival lines 8.

### 8.3 Kingdom voices (Brennmark): guild-proud, deadpan tradesfolk

House delivery: **crisp, unplaced neutral English**, unhurried rhythm, dry understatement; colour comes from guild jargon, never an
accent. Post-chains are light; the kingdom sounds like real people in a real town. **The Tempo column (here and in §8.4) is the colour of
Ready, Annoyed and advisor lines (never below 2.5 words/s); every speaker's What and Yes lines obey §8.1 rule 1 (≥ 3.0 words/s), and
Attack and Warcry lines ≥ 2.8 words/s.**

| Speaker | Slice | Read | Timbre and register | Tempo | `eleven_v4` tags | Post-chain (ffmpeg) | Tic | Casting candidate (audition) |
|---|---|---|---|---|---|---|---|---|
| Hodman / Flail Levy | Yes | Man, 55–65 | Warm, slightly rasped mid-low baritone | Unhurried in Ready, Annoyed and built lines (≈ 2.5 words/s); acks ≥ 3.0 words/s; breathless as the Levy | `[wry]`, `[tired]`, `[deadpan]`; Levy `[shouts]`, `[breathless]` | `rubberband=pitch=0.97:formant=preserved`, +2 dB at 250 Hz, −2 dB at 4 kHz | Bills the player by the click; his hod is called Agnes | `N2lVS1w4EtoT3dr4eOWO` |
| Pavisier | Yes | Man, 19–24 | Bright, earnest light baritone | Medium-fast | `[earnest]`, `[proud]`, `[shouts]` | Light compression only | Proud of the wheel he painted on his pavise, badly | `TX3LPaxmHKxFdv7VOQHJ` |
| Hookgunner | Yes | Man, 30s | Loud, clipped, a little hoarse | Medium | `[loud]`, `[confused]` | Band-limit 300 Hz–5 kHz (deafened ears) | Slightly deaf from gunfire: mishears orders | `SOYHLrjzK2X1ezoPC6cr` |
| Bombard Wagon gunner | Yes | Older woman gunner (the only speaking voice; the young loader is non-verbal: coughs and effort grunts in the `vox_*` sets) | Gravelly alto | Medium-fast | `[gruff]`, `[dry]` | Light compression; a faint ringing-ear band-limit 250 Hz–6 kHz | Rates every shot out of ten, never above six | Audition |
| Linden Sister | Yes | Woman, 40s | Warm, brisk alto | Fast | `[brisk]`, `[warm]` | Small room reverb | "Sit. Drink this." | Audition |
| Ironrider | Later | Man, 40s | Smooth, tired baritone | Slow | `[dignified]`, `[offended]` | Light plate reverb | An ex-noble on the League's payroll, quietly offended | Audition |
| Lacewright | Later | Woman, 30s | Quiet, precise mezzo | Slow | `[soft]`, `[precise]` | Close-mic, de-essed | Counts stitches; a little menacing | Audition |
| Assayer | Later | Man, 50s | Fussy, nasal tenor | Fast, clipped | `[fussy]` | Band-limit | Weighs everything: "Seven grains light" | Audition |
| Wall Wagon teamster | Later | Man, 50s | Gruff, affectionate bass | Slow | `[gruff]`, `[gentle]` | — | Talks to his wagon | Audition |
| Netcaster | Later | Woman, 20s | Cheerful, quick | Fast | `[cheerful]` | — | A stork-catcher who loves storks | Audition |
| Stork Rider | Later | Woman, 30s | Warm, quick | Medium | `[warm]` | Stork bill-clatter layered (SFX) | Talks to her stork | Audition |
| Brass Kestrel | Later | — | No voice: clockwork whirr and a two-note whistle (SFX) | | | | | — |
| **Wheel Marshal** | Yes | Woman, 40s | Calm, low alto with weight | Unhurried | `[calm]`, `[resolute]` | +2 dB at 150 Hz, light room reverb | Carter and road metaphors | `XrExE9yKIg1WjnnlVkGX` |
| **Firewright** | Yes | Man, 40s | Husky, smoky tenor | Quick, excitable | `[gleeful]`, `[coughs]` | Gentle soft-clip for smoke-roughness | No eyebrows left; counts fuses lovingly | Audition (not a clans preset) |
| Orrery Sage | Later | Woman, 50s | Clear, measured mezzo | Measured | `[precise]` | Small hall reverb | Always mentions the time | Audition |
| Flail Hetman | Later | Man, 40s | Booming bass-baritone | Slow, big | `[booming]` | +3 dB at 120 Hz | Harvest metaphors | Audition |
| **The Reeve** (advisor) | Yes | Man, 50s | Clipped, dry mid tenor | Brisk | `[dry]`, `[matter-of-fact]` | Band-limit 200 Hz–6 kHz ("speaking tube") | Town official; everything is a line item | Audition (not `onwK4e9ZLuTAKqWW03F9`, which is the clans advisor) |

### 8.4 Clans voices (Tormai): courteous menace

House delivery: **slow, formal, complete sentences in standard English**, never broken grammar and never a real-world accent. A low
throat-hum "*Hm-hm*" before many Ready, Annoyed and advisor lines (never before an ack). Enemies are "guests". They apologise before violence. Big jaws: most voices are pitched down
with shifted formants.

| Speaker | Slice | Read | Timbre and register | Tempo | `eleven_v4` tags | Post-chain | Tic | Casting candidate |
|---|---|---|---|---|---|---|---|---|
| Yurtwright | Yes | Middle-aged | Deep, warm, courteous | Formal and measured in Ready, Annoyed and built lines (≈ 2.5 words/s); acks ≥ 3.0 words/s | `[courteous]`, `[fussy]` | `rubberband=pitch=0.9:formant=shifted`, warm EQ | Counts things ("eleven clicks") | `pqHfZKP75CvOlQylNhV4` (clans §3.3) |
| Grappler | Yes | Adult, huge | Very deep, formal, amused | Weighty but crisp: acks ≥ 3.0 words/s, the size comes from pitch 0.84 and the formant shift | `[very deep]`, `[formal]`, `[amused]` | `rubberband=pitch=0.84:formant=shifted`, +4 dB at 180 Hz, compressor | Wrestling etiquette | `pNInz6obpgDQGcFmaJgB` (clans §3.3) |
| Javelineer | Yes | Young adult woman | Bright, boastful | Quick | `[boastful]`, `[competitive]` | `rubberband=pitch=0.94:formant=shifted` | Quotes distances ("forty paces!") | `cgSgspJ2msm6clMCkdW9` |
| Gustcaller | Yes | Older woman | Breathy, airy alto | Medium, lilting | `[breathy]`, `[gossipy]` | Light chorus + short `aecho` | Gossip about people that she says the wind brought her: "The wind says your cousin still owes me tea." Always petty family and neighbour news; never spirits, omens or voices, never wind-breaking jokes (§8.1 rule 3) | `EXAVITQu4vr4xnSDxMaL` |
| Sling-Cart crew | Yes | Two brothers | One deep and slow, one quicker and higher | **In unison** (both takes mixed together, slight stereo offset) | `[deadpan]` / `[eager]` | `rubberband=pitch=0.9:formant=shifted` on both | They always agree, even when wrong, and count their hauls together ("One, two… loose!"); never a split line, who-is-who confusion, partnership talk or explosion jokes (§8.1 rule 7; lines in slice-plan §2.12 and clans §3.3) | Audition two presets |
| Proven Javelineer | Later | Javelineer voice, older | Same, rougher | Slower | `[proud]` | pitch 0.92 | "Nine battles" | Same as Javelineer |
| Pole-Carver | Later | Middle-aged man | Dry, deadpan mid | Slow | `[deadpan]` | pitch 0.9 | Complains about wood grain | Audition |
| Hill-Listener | Later | Very old | Whispery, interrupted by the slow, rumbling dream-voice of the Sleeping Hills (never an ancestor) | Very slow | `[whispers]` | Octave-down double + chorus; the bronze echo-horn hums under the second voice | Two voices that interrupt each other | Audition |
| Hookbill Rider | Later | Young man | Fast-talking | Fast | `[excited]` | pitch 0.94 | The bird shrieks over line ends (SFX) | Audition |
| Glintback rider | Later | Adult | Sun-dazzled, cheerful | Medium | `[cheerful]` | A bright glint chime layered (no gong: no instrument rides the beast) | Shades his eyes with his hat brim: "Hold still, you're too bright." (no squint jokes) | Audition |
| Sky-Kite | Later | Young woman | Airy, thrilled | Quick | `[excited]` | Wind layer | Whoops | Audition |
| Thoom | Later | Giant | Very deep, long vowels | Very slow | `[slow]`, `[anxious]` | `rubberband=pitch=0.75:formant=shifted`, large room | A long "mmmm"; an anxious host who checks that everyone is warm and has had tea (never food, hunger, dinner or cattle jokes; clans §3.1) | Audition |
| **The Uncut** | Yes | Woman | Low, dry, confident | Clipped | `[low]`, `[dry]`, `[confident]` | `rubberband=pitch=0.9:formant=preserved`, small plate reverb | Keeps a duel tally | `FGY2WhTYpPnrIDTdsKH5` (clans §3.3) |
| **Skymirror** | Yes | Old man | Sonorous, vain, rounded | Slow | `[grand]`, `[vain]` | `rubberband=pitch=0.88:formant=shifted`; light shimmer on mirror-sight lines | Polishes mid-sentence (cloth squeak SFX); narrates tiny far-off things the mirror shows, never fortunes or yes/no answers | `nPczCjzI2devNBz1zQrb` |
| Kettle-Uncle (renamed 2026-10-19, §13 #26) | Later | Giant | Ultra-deep, gentle | Very slow | `[gentle]`, `[warm]` | pitch 0.72, huge room | Calls everyone "little one" | Audition |
| Omen-Mother | Later | Grandmother | Crackly, sly | Quick-witted | `[sly]`, `[amused]` | pitch 0.95, formant shifted | Swirls her tea cup (a small bronze-cup clink SFX); no bones | Audition |
| **The gong-keeper** (advisor) | Yes | Elder | Measured, sonorous mid-low | Measured | `[measured]` | Bronze-plate reverb tail | Announces everything as if striking the gong | `onwK4e9ZLuTAKqWW03F9` (clans §3.3) |

### 8.5 Neutral voices

| Speaker | Delivery | Notes |
|---|---|---|
| Rundling shopkeeper | Small, fussy, precise, polite outrage; `rubberband=pitch=1.12:formant=shifted`, slight nasal EQ | 10 lines in neutrals §5.3. Never the greedy-merchant voice or its well-known catchphrases (neutrals §10.1) |
| Rat-Piper [SLICE+] | Sly showman | 31 lines (the hero standard, §8.2), written with the neutral-hero pass |
| Creeps | Wordless Seed Audio sets (§9.8) | Sootcoats cough and shout "Hup!"; Tattiebogles creak and hiss; Cairnwakes grind and hum |

### 8.6 Example lines: Hodman (kingdom worker)

Five original candidates per category; recording uses the counts in §8.2 (the rest are alternates for review rejections). Every
candidate fits the §8.2 word budget. All are new; "Raised, roofed, and only slightly crooked" is kept from kingdom §3.2.

| Category | Candidates |
|---|---|
| Ready | "Hodman, on the ledger. Agnes, say hello." · "Fresh mortar, fresh blisters. Where's the site?" · "Guild card stamped, hod strapped, back complaining." · "Another day, another wall wants raising." · "Present and paid. Well. Present." |
| What | "Mm? Mind the mortar." · "Thirty years. One Agnes." · "Lime in my ears." · "Wanting a wall, then?" · "Agnes is listening." |
| Yes | "On the ledger." · "Lifting with the knees." · "Agnes and me, then." · "Slow and square." · "Your coin, your wall." |
| Attack (spoken as the Flail Levy) | "This is extra, mind." · "Flail's out, heads down!" · "Like threshing. Only shoutier." · "Hold Agnes. Going in." · "Right. Overtime it is." |
| Warcry | "OFF OUR BOARDS!" · "SWING AND DUCK!" · "EVERY HAND TO THE WHEEL!" · "THRESH 'EM!" · "NOT MY SCAFFOLD, YOU DON'T!" |
| Annoyed (in order; 5 recorded) | 1. "That's a click. I'm writing it down." 2. "Another click. Guild rate's a copper a click." 3. "We're at half a silver. Agnes is impressed." 4. "Agnes says you've got the hands of a pickpocket." 5. "Right. That's a full silver. Agnes is drawing up the invoice. She has lovely handwriting." |
| Built (never "done", §8.1) | "Raised, roofed, and only slightly crooked." · "Signed, sealed and plastered. Somebody check the corners." · "Plumb, level, and paid for. Probably." · "Scaffold's down. Mind the dust." · "Another one for the town ledger." |
| Mechanic (2 recorded: arm, and Lay Down Flails) | (arm) "Horn's blowing! Straw off, iron on!" · "Swapping the hod for the flail." · "Agnes, wait here. I've a flail to swing." · "Levy's up. Who's paying?" · (Lay Down Flails) "Flail's on the hook. Agnes, where were we?" · (Lay Down Flails) "Iron off, straw on. Hello, Agnes." |
| Death (non-verbal set; delivery scripts for the vocal-set job) | A winded "oof" cut off, the hod clattering · a tired sigh, "…off the ledger…" fading · a sharp intake of breath and a wince · a surprised "Agnes—!" cut short · a long exhale while the straw hat rolls away |

### 8.7 Example lines: Pavisier (kingdom line infantry)

| Category | Candidates |
|---|---|
| Ready | "Pavisier ready. The paint's nearly dry." · "Another board for the wall!" · "Kettle hat on, chin strap tight." · "Fresh from drill! Well. From drill." · "I brought the big shield. They're all big." |
| What | "Wall here!" · "Shield's the tall bit." · "Point me somewhere." · "Mind the wet paint." · "Wall's ready." |
| Yes | "Wall moving." · "Boards up, feet forward." · "Step and plant." · "Carrying the wall over." · "Where you point." |
| Attack | "Falchion out!" · "Shield first, sharp second!" · "Push!" · "Wall, forward!" · "Square into them!" |
| Warcry | "HOLD THE BOARDS!" · "BRENNMARK STANDS!" · "EVERY WHEEL A WALL!" · "NOBODY GETS PAST THE PAINT!" · "BRACE! BRACE!" |
| Annoyed (in order; 5 recorded) | 1. "You're knocking on a wall. Walls don't open." 2. "I painted that wheel myself. Took three goes." 3. "The spokes are uneven because the brush was uneven." 4. "My nan says it's the best wheel in Brennmark. She's biased. And short-sighted." 5. "…Fine. I'll repaint it. Happy? No? Me neither." |
| Mechanic (2 recorded: Plant Pavise on, and off) | "Planting!" · "Boards down. Nobody move." · "Pavise set. Shoot all you like." · (off) "Pulling up the stakes." · (off) "Wall's portable again." |
| Death (non-verbal set) | A winded "hff" as the pavise topples flat · a weak, earnest "Tell them… the wheel was… straight…" · a short cry swallowed by the kettle hat's clank · a startled breath and a heavy sit-down thump · a sharp "ah!" with an armour rattle |

### 8.8 Example lines: Yurtwright (clans worker)

| Category | Candidates |
|---|---|
| Ready | "Hm-hm. Twelve poles, one roof. Ready." · "My mallet is warm. My tea, warmer." · "A wright for the household. Show me ground." · "Lattice counted twice. We may begin." · "Felt enough for a family. Here I am." |
| What | "Mallet in hand." · "The wright hears you." · "Roof, or mending?" · "Tell me. Still counting." · "Between two knots. Yes?" |
| Yes | "With care." · "Pole by pole." · "I bring the kettle." · "The kettle can wait." · "Sensible." |
| Attack | "Forgive me. Firmly." · "Mallet first. Apology after." · "Please hold still, guest." · "I also unmend heads." · "A small correction." |
| Warcry | "NOT ON MY FELT!" · "WIPE YOUR FEET, GUESTS!" · "THE DOOR IS THAT WAY!" · "NO MUD IN MY YURT!" · "THAT KETTLE IS NOT YOURS!" |
| Annoyed (in order; 5 recorded) | 1. "Hm. One click is a greeting." 2. "Three clicks is a question. I have answered it." 3. "Seven clicks. In my household, seven clicks means you want stew." 4. "Eleven clicks. There is no custom for eleven. You are inventing customs." 5. "Sit. I will pour. Hold the cup with both hands, where I can see them." |
| Built | "Twelve poles, one roof, no leaks." · "The felt is tied. Bring the cushions." · "Another dome under the Long Sky." · "Raised. Somebody owes me tea." · "Finished. I counted every knot. Twice." |
| Mechanic (2 recorded: Sound the Gong / Roll the Felt, and All Clear) | "The gong! Inside, everyone, inside!" · "Rolling up the felt. Slings ready." · "In through the door, out go the stones." · (All Clear) "All clear? Good. My stew is going cold." · (All Clear) "The guests have left. Rude, but quiet." |
| Death (non-verbal set) | A deep "hhuff" and a soft felt thump · a surprised "Hm?" cut short · a tired sigh and the mallet clattering · a fading "Who… will count…" · a low throat-hum that drops away |

### 8.9 Example lines: Grappler (clans heavy infantry)

Alternates for clans §3.3, which is the source of record since the clans doc's second review; record one annoyed run, not both. Every
line here was re-checked against clans §3.1 (no "clan", no bare interjection on the worker, no sky deity, no sacred number) and against
the Tormai look (small rounded ears: clans §3.3's own What line about big ears must change too, §13 #17), and, since 2026-10-19,
against the address-word-swap rule (§8.1 rule 3: clans §3.3's first Grappler What line changes too, §13 #25).

| Category | Candidates |
|---|---|
| Ready | "Hm-hm. The ring is drawn." · "Grappler. Shoulders loose, jaw ready." · "I bowed to the grass. Now, to you." · "Bring me a guest who likes the ground." · "Braids bound, bronze polished. Who wrestles?" |
| What | "Your grip, Ring-Elder?" · "The Grappler attends." · "Big shoulders, small patience." · "Yes? I was stretching." · "Someone to lift?" |
| Yes | "Slowly. Surely." · "Walking." · "I go." · "Respectfully, yes." · "A fair hold." |
| Attack | "Meet the ground, guest." · "Excuse my grip." · "Pardon. A throw." · "Take hold!" · "Both shoulders, please." |
| Warcry | "INTO THE GRASS!" · "THE RING IS OPEN!" · "BOW, THEN BREAK!" · "THE WHOLE GRASS IS WATCHING!" · "LOW AND STRONG!" |
| Annoyed (in order; 5 recorded) | 1. "You lay a hand on my arm. That is how a bout begins." 2. "Again? Now we have touched shoulders. We are rivals." 3. "A third time. In my household, that is an engagement." 4. "I must ask my mother. She will want to see your grip." 5. "She says no. Too small. I am so sorry." |
| Mechanic (Shove, at most once per 10 s) | "Step back, please." · "Out of the ring!" · "And… away." · "A point to me." · "Stay down, please." |
| Death (non-verbal set) | A huge strained "hnngh" and a ground-shaking thud · a quiet, surprised "…pinned." · a long exhale and the bronze helmet ringing on the ground · a gracious, fading "A fair… throw…" · a startled bellow that drops an octave |

### 8.10 Advisors (19 lines each)

| Trigger (rules §17.3) | The Reeve (kingdom) | The gong-keeper (clans) |
|---|---|---|
| Need gold | "The strongbox is light." | "The purse is thin. More sun-teeth, please." |
| Need lumber | "We're short on timber." | "We are short of lattice-wood." |
| Need supply | "Every croft's full. No room for more hands." | "Every yurt is full. Our guests are sleeping in the rain." |
| Hero slot full | "Every captain's chair is taken." | "Every seat by the fire is taken." |
| Cannot build there | "The ground won't take it there." | "The ground says no." |
| Hall attacked (NTF-01 buildings, main hall) | "Our hall is taking a beating!" | "Someone is striking the Shell!" |
| Other building attacked (NTF-01 buildings) | "They're pulling down our timber!" | "Someone is striking our felt!" |
| Units attacked | "Our people are in a fight!" | "Our kin are fighting!" |
| Workers attacked (ECO-27) | "They're at the Hodmen! Shall I sound the horn?" (ECO-27's line: it teaches the Levy Horn answer) | "They are chasing the wrights. Shall I sound the gong?" (the same lesson for Sound the Gong) |
| Hero in danger (below 40 % HP, NTF-01 hero category) | "Our captain is in trouble out there!" | "A name is wavering. Bring them home." |
| Hero fallen | "A captain is down. The Oath Hall can raise them." | "A name has gone quiet. The Stones will call it back." |
| Hero ready | "A captain stands sworn." | "A name stands up from the Stones." |
| Research finished | "The guild has signed it off." | "The bronze has cooled." |
| Hall tier finished | "The burg is walled." | "The banners are raised." |
| Mine low | "The seam is running thin." | "The sun-teeth are wearing thin." |
| Mine exhausted | "The seam is spent." | "The sun-teeth are gone from this hill." |
| Upkeep rises | "Wages are eating the strongbox." | "Many mouths, small pot. The purse shrinks." |
| No hall left (cripple countdown started) | "We've no hall! Raise one, or the whole valley will know." | "Without a hall the whole steppe will see us. Raise one!" |
| Revealed to the enemy (cripple revealed) | "Every roof we own is on their map now." | "Hm-hm. The whole steppe can see our felt now." |

Kingdom lines for gold, lumber, supply, cannot build, hall attacked, hero ready, research, upkeep and revealed come from kingdom
§3.2, and the workers line from juice ECO-27; clans lines for gold, lumber, supply, cannot build, units attacked, hero fallen, research
and mine low come from clans §3.3. The rest are new. The hall line plays only for the main hall, so a struck Croft or yurt never claims
the hall is under attack. Every advisor line is checked like any other line (§8.1), including the kingdom completion rule ("signed it off", never
"done"). **Optional P1 event lines:** kingdom §3.2 and clans §3.3 also script hero level-up, building finished and idle-queue lines;
they are recorded only if the TTS probe leaves budget (+3 per advisor).

### 8.11 TTS recipe

```json
{"model": "elevenlabs/tts",
 "input": {"model_id": "eleven_v4", "voice_id": "N2lVS1w4EtoT3dr4eOWO",
  "prompt": "[wry, brisk, an older tradesman] Mm? Mind the mortar.\n\n[long pause]\n\n[wry, brisk] Thirty years. One Agnes.\n\n[long pause]\n\n[deadpan, brisk] Lime in my ears.\n\n[long pause]\n\n[dry, brisk] Wanting a wall, then?"}}
```

1. **Batch** one category of one speaker per request (consistent performance, fewer jobs); about 9 requests per speaker. Ack batches
   carry a `[brisk]` tag on every line (§8.1 rule 1).
2. **Split** on silences ≥ 0.35 s (`silencedetect=noise=-40dB:d=0.35`), **trim**, apply the speaker's **post-chain**, 5 ms fade-in and
   20 ms fade-out, **loudness** about −18 LUFS per line. **Measure every trimmed take** against its category's max seconds (§8.2): if it
   is over, apply `atempo` up to 1.15 (pitch-preserving); if it is still over, reject it and regenerate with a `[brisk]` or `[fast]` tag.
   A What or Yes take over 1.4 s never ships, because the AUD-03 debounce would drop the next ack.
3. **Export** Ogg Vorbis mono `-q:a 5` to `assets/audio/voice/<faction>/<speaker>/<category>_<nn>.ogg` (for example
   `assets/audio/voice/clans/yurtwright/annoyed_3.ogg`). Raw takes go to `assets_src/audio/voice/`.
4. **Two takes** of any line that sounds flat; keep the better. Log both jobs in the ledger.
5. **Review:** listen for mispronounced invented names (Brennmark, Tormai, Yurtwright); fix spelling hints in the prompt
   (for example "TOR-my") rather than re-casting.

---

## 9. Sound effects

### 9.1 Rules and the fixed Seed Audio wrappers

- **Model:** Krea `bytedance/seed-audio-1.0` (prompt only, ≤ 2048 characters). Measured cost: 4.63 CU for about 2.5 s (ledger #5).
  Whether the price scales with output length is **unmeasured**: the first multi-variant job is the probe (§11).
- **Every prompt** = one wrapper below + one `[sound: …]`, `[voice: …]` or `[background: …]` clause from the tables. Clauses describe
  material, weight, size and distance. Never a game, studio, film or person's name.
- **No reveal is ever a thrown powder, a dust cloud or a puff**, in sound or picture: a pouch of powder that reveals invisible units
  copies the reference game's reveal item in object, effect and presentation at once (neutrals §10.2). Our reveals are a mirror, a snapped chalk
  line, bell-strung burrs and a hanging flare (§2.3).
- **Silence between variants is 0.6 s** (the audio doc used 1 s): long enough for `silencedetect` at 0.35 s, and less silence to pay
  for if pricing is per second.
- **Post:** split on silence, discard bad takes, trim, 5 ms / 20 ms fades, peak −1 dBFS (one-shots) or −24 LUFS (ambience beds),
  WAV 44.1 kHz mono (Godot imports as QOA); loops crossfaded 0.5–2 s. Names: `assets/audio/sfx/<group>/<id>_<nn>.wav`.
- **Playback** (buses, priorities, caps, fog gate): audio §3.5 and the juice specs. Variation: `AudioStreamRandomizer`, pitch ×1.06,
  ±1.5 dB, never the same take twice in a row.
- **Priority:** **P0** = needed for the slice; **P1** = slice polish (CC0 placeholders allowed); **P2** = later.

```
SFX_ONESHOT_V1 = Sound effect only. No music, no speech, no background ambience. [sound: {CLAUSE}] {N} separate variations, each
about {D} seconds, separated by about half a second of silence. Each variation slightly different in pitch and texture. Dry,
punchy, stylized fantasy game sound, close-miked.

SFX_LOOP_V1 = Sound effect only. No music, no speech, no background. [sound: {CLAUSE}] One continuous take of about {D} seconds
with even density and no sudden events, so it can loop seamlessly.

VOCAL_SET_V1 = Creature sound effects only. No music, no words, no background. [voice: {VOICE}] {LIST}. {N} separate sounds,
separated by about half a second of silence.

AMBIENCE_V1 = Ambient soundscape only. No music, no speech. [background: {CLAUSE}] About {D} seconds, even density for seamless
looping, no sudden loud events.

STINGER_V1 = Sound effect only. No melody, no speech. [sound: {CLAUSE}] One take of about {D} seconds with a natural decay.

SFX_SET_V1 = Sound effects only. No music, no speech, no background. [sound: a set of related small interface sounds] {LIST}, in this
order, each sound made {T} times with slight variation. All separated by about half a second of silence. Dry, close-miked, stylized
fantasy game sounds.
```

Wrapper codes in the tables: **O** one-shot, **L** loop, **V** vocal set, **A** ambience, **S** stinger, **K** kit set (several
distinct small sounds in one job; the list in the clause is numbered and `{T}` is 2 unless the table says otherwise). Kit sets keep the
UI families consistent and cost one job each if Seed Audio bills per job (§11).

### 9.2 UI (2D, UI bus)

The **content** of every cue in the UI juice kit (juice ui-camera-audio §5.3); its spacing, levels and valence tags stay in the juice
spec. Valence rule (juice §5.3): positive cues are consonant, single or rising; alarms are dissonant, fast and falling, and use no
instrument a positive cue uses.

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `ui_click_kingdom` | O | a tiny button press: a soft dry knock on oak wood with a small iron latch tick, very short | 6 × 0.12 | P0 |
| `ui_click_clans` | O | a tiny button press: a small tap on a polished bronze plate damped by thick felt, a soft thump with a short bright tick | 6 × 0.12 | P0 |
| `ui_click_neutral` | O | a tiny button press: a soft tap on linen stretched over a wooden frame with a light paper rustle | 4 × 0.12 | P1 |
| `ui_order_kingdom` | K | 1. a soft wooden "tuk" (move), 2. a "tsk-tak" of wood and a small iron click (attack), 3. two quick wooden "tuk-tuk" taps (patrol), 4. a quick quill flick across paper (ability) | 4 × 2 × 0.15 | P0 |
| `ui_order_clans` | K | 1. a soft felt-damped "puk" (move), 2. a "tsk-tak" with a small bronze click (attack), 3. two quick felt "puk-puk" taps (patrol), 4. a quick wooden bead flicked along a cord (ability) | 4 × 2 × 0.15 | P0 |
| `ui_select_kingdom` | K | 1. one small tally-stick tick, 2. a double tally tick, 3. a bundle of tally sticks clacking together, 4. a single higher tally tick for a rising wave | 4 × 2 × 0.15 | P0 |
| `ui_select_clans` | K | 1. one small wooden bead tick, 2. a double bead tick, 3. a short string of beads rattling, 4. a single higher bead tick for a rising wave | 4 × 2 × 0.15 | P0 |
| `ui_disabled_kingdom` | O | a single muffled knock on a thick wooden board, dull and short | 3 × 0.2 | P0 |
| `ui_disabled_clans` | O | a single soft thud on a thick felt wall, dull and short | 3 × 0.2 | P0 |
| `ui_cooldown_kingdom` | O | one small brass hand-bell tink, bright and clean, very short decay | 3 × 0.4 | P0 |
| `ui_cooldown_clans` | O | one small bronze gong tap with a soft felt mallet, short bright bloom | 3 × 0.5 | P0 |
| `ui_error_kingdom` | O | a dull double knock on thick wooden boards, low, flat and slightly muffled | 4 × 0.3 | P0 |
| `ui_error_clans` | O | a muffled thud on a thick felt wall followed by a low bronze bowl tone choked short by a hand | 4 × 0.35 | P0 |
| `ui_complete_kingdom` | O | a hand plane stroke along a wooden board followed by one warm bronze hand-bell ring with a natural decay | 3 × 1.4 | P0 |
| `ui_complete_clans` | O | a medium bronze gong touched with a soft felt mallet, a warm swelling bloom and a slow decay | 3 × 1.6 | P0 |
| `ui_levelup` (shared signature) | O | a bright heroic level-up flourish: three quick ascending small hand-bells landing on a warm singing bronze bowl that blooms and shimmers, a soft low felt-mallet drum tap underneath, uplifting and magical (**A/B against the instruments-only `_V2` clause in §5.2**; keep the one that passes the listening check) | 3 × 1.4 | P0 |
| `ui_hero_fallen` (global) | O | a single low tolling bronze bell with a long decay over one soft muffled drum beat, solemn | 2 × 2.5 | P0 |
| `ui_ping` | O | a clear bright wooden block tock immediately followed by a small high bell ting, crisp and very distinct | 3 × 0.5 | P0 |
| `ui_alert_kingdom` | K | 1. two small cheap iron tower bells a tritone apart struck alternately, five fast strikes about a tenth of a second apart, falling in pitch, slightly damped and clashing (about 0.75 s); 2. the same bells struck harder, seven faster strikes ending in a hand-bell clang (urgent take, about 0.7 s) | 2 × 2 | P0 |
| `ui_alert_clans` | K | 1. a wooden slit drum with two tongues a minor second apart struck alternately, six fast strikes falling in pitch over a dry seed-pod rattle shake (about 0.8 s); 2. the same tongues, eight faster strikes with the rattle doubled (urgent take) | 2 × 2 | P0 |
| `ui_purchase` | O | a few coins poured into a leather purse, then a light brass balance-pan clink | 3 × 0.7 | P0 |
| `ui_item` (pickup, drop) | O | a small twine-tied oilcloth bundle picked up with a crisp waxed-cloth rustle and a soft twine creak; then the same bundle dropped on grass with a soft thud | 3 + 3 × 0.4 | P0 |
| `ui_place` (valid, invalid) | O | a soft wooden tock; then a muffled dull thud | 3 + 3 × 0.15 | P0 |
| `ui_place_stamp` | O | a wooden mallet driving a stake into soft earth through a sheet of paper, short and satisfying | 3 × 0.35 | P0 |
| `ui_skill_learn` | O | a quill scratching across parchment, ending in a tiny bright bell tick | 3 × 0.6 | P0 |
| `ui_cant_afford` | O | a nearly empty leather purse shaken once, two coins rattling, flat and disappointing | 2 × 0.5 | P1 |
| `ui_sell` | O | a small item set down on a wooden counter, then a few coins counted back into a palm and a brass weight tapped once | 3 × 0.8 | P1 |
| `ui_upkeep` | O | two wooden block notes, the second lower, like a ledger snapping shut | 2 × 0.6 | P1 |
| `ui_rally` | O | a small pennant pole pushed into turf, a short thunk with a flag flutter | 3 × 0.35 | P1 |
| `ui_toast` | O | a quick paper swish of a scroll unrolling | 3 × 0.3 | P1 |
| `ui_card_kingdom` | K | 1. a ledger page flipped over (sub-card open), 2. the same page flipped back (back), 3. a small iron latch click (targeting lock-on), 4. a short ratchet click-clack (autocast on), 5. the same ratchet muted (autocast off) | 5 × 2 × 0.2 | P1 |
| `ui_card_clans` | K | 1. a felt flap lifted (sub-card open), 2. the flap dropped back (back), 3. a wooden bead clicking into a slot (targeting lock-on), 4. a bead click-clack on a cord (autocast on), 5. the same click muted (autocast off) | 5 × 2 × 0.2 | P1 |
| `ui_misc_kingdom` | K | 1. a wax seal pressed onto paper (group assign), 2. a lighter wax seal (group add), 3. a paper slip torn (queue cancel), 4. a tiny quill tick (menu hover), 5. a tally tick (score-screen row) | 5 × 2 × 0.2 | P1 |
| `ui_misc_clans` | K | 1. a felt mallet tap on a small drum (group assign), 2. a lighter tap (group add), 3. a stitch pulled out of felt (queue cancel), 4. a tiny bead tick (menu hover), 5. a bead tick on a cord (score-screen row) | 5 × 2 × 0.2 | P1 |
| `ui_clock_kingdom` | K | 1. a small clockwork escapement clunk with one tick (dusk and dawn on the Horizon Ribbon), 2. a knife cutting one notch into wood (day tally) | 2 × 2 × 0.3 | P1 |
| `ui_clock_clans` | K | 1. a felt shutter sliding with a tiny gong tap (dusk and dawn), 2. a bronze bead dropping onto a cord (day tally) | 2 × 2 × 0.3 | P1 |
| `ui_cripple_kingdom` | K | 1. a candle wick hissing once (countdown tick), 2. two rising notes on a small town bell (averted) | 2 × 2 × 0.6 | P1 |
| `ui_cripple_clans` | K | 1. a bronze bead dropping into a bowl (countdown tick), 2. two rising small gong taps (averted) | 2 × 2 × 0.6 | P1 |
| `ui_feed_kingdom` | K | 1. a parchment slip sliding with a brass tack tick (feed line), 2. a quick page whoosh (long camera glide), 3. the whoosh reversed (return glide) | 3 × 2 × 0.4 | P2 |
| `ui_feed_clans` | K | 1. a felt slip sliding with a thread tick (feed line), 2. a soft felt whoosh (long camera glide), 3. the whoosh reversed (return glide) | 3 × 2 × 0.4 | P2 |
| `ui_menu` (open, close) | O | a heavy book cover opening softly; then closing softly | 2 + 2 × 0.5 | P2 |

**Hover** is silent on the command card and hero buttons (fast sweeps would machine-gun) and ticks only on menu buttons
(`ui_misc_<faction>` #4). The level-up cue is deliberately bells into a bowl (no choir and no harp run), so it is unmistakably ours.
**The alarms share no instrument with any positive cue**: the kingdom alarm uses cheap clashing tower bells, never the warm hand-bell
of `ui_complete_kingdom`, and never a wooden horn (the Levy Horn, §9.5, must stay instantly distinguishable from "under attack"); the
clans alarm is a slit drum, never a gong (the clans' gongs mean the hall, tier-ups and the Sound the Gong call). The match-opening cue
is music (§10.1).

### 9.3 Combat matrix (World and Combat buses)

Melee = **swing layer** (by `fx.weapon`) + **impact layer** (by `fx.material`) + optional **sweetener** (juice combat §4.8, CMB-19, CMB-22).

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `sw_slash` | O | fast close swings of a single-edged curved blade through the air, a short airy whoosh, no impact | 6 × 0.3 | P0 |
| `sw_blunt` | O | heavy swings of a flanged bronze mace and of a threshing flail on a chain, a low whoosh with a faint chain rattle on some takes, no impact | 6 × 0.35 | P0 |
| `sw_pierce` | O | quick thrusts of a war-pick and a pitchfork, a short sharp air cut, no impact (the Wheel Marshal's swing: a slice hero) | 4 × 0.25 | P0 |
| `sw_chop` | O | heavy swings of a billhook and a rake, a thick whoosh, no impact | 4 × 0.35 | P1 |
| `sw_magic` | O | a short magical swish like a gust of warm air with a faint sparkle, no impact | 4 × 0.3 | P1 |
| `hit_metal_l` | O | a blade striking blackened iron plate and bronze lamellar, a sharp clang with a short ring | 4 × 0.5 | P0 |
| `hit_metal_h` | O | a heavy mace slamming into iron plate, a deep metallic crash with a dull ring | 4 × 0.6 | P0 |
| `hit_flesh_l` | O | a blade hitting a body in quilted linen armour, a thick cloth slap with a muted thud, no gore, no voice | 4 × 0.4 | P0 |
| `hit_flesh_h` | O | a heavy blunt blow into a big body wrapped in thick felt, a deep meaty thump, no gore, no voice | 4 × 0.5 | P0 |
| `hit_wood_l` | O | a weapon striking a tall wooden shield, a hollow woody knock | 4 × 0.4 | P0 |
| `hit_wood_h` | O | a heavy blow on wooden planks and a cart side, a splintery crack | 4 × 0.6 | P0 |
| `hit_stone` | O | a weapon hitting a stack of flat stone slabs, a rocky crack and a short gravel crumble | 4 × 0.6 | P0 |
| `hit_straw` | O | a blow into a straw-stuffed scarecrow body, a dry straw crunch and a puff of rustling straw | 4 × 0.4 | P0 |
| `hit_ethereal` | O | a weapon passing through a spectral creature, a cold glassy shimmer and a soft airy thump | 4 × 0.5 | P2 (no spectral target in the slice) |
| `hit_solid` | O | a short bright crack accent like a stick snapping inside a metal bucket, a very short transient | 4 × 0.15 | P1 |
| `hit_glance_tink` | O | a blade glancing off thick armour, a thin high tink with a short scrape | 4 × 0.25 | P1 |
| `hit_glance_thud` | O | a padded dull thud, the blow absorbed | 4 × 0.25 | P1 |
| `hit_crit` | O | a heavy decisive impact accent: a deep thump with a short ringing metallic snap on top | 3 × 0.4 | P1 |
| `fall_light` | O | a body in cloth armour falling onto grass, a soft thud with a cloth rustle | 3 × 0.6 | P0 |
| `fall_armoured` | O | an armoured body falling onto earth with an iron and bronze clatter | 3 × 0.8 | P0 |
| `fall_huge` | O | a huge heavy body falling, a ground-shaking thud with a short rumble | 3 × 1.0 | P0 |
| `vox_death_kingdom` | V | `[voice: ordinary adult townsfolk, men and women]` winded oofs, a sharp intake of breath, two short cut-off cries, a tired sigh, no words | 6 sounds | P0 |
| `vox_death_clans` | V | `[voice: very large deep-chested humanoids with heavy jaws]` deep huffs, a strained bellow, a throat-hum that drops away, a long exhale, no words | 6 sounds | P0 |
| `vox_pain_kingdom` | V | `[voice: ordinary adult townsfolk]` six short pained exhales and hisses, no words | 6 sounds | P1 |
| `vox_pain_clans` | V | `[voice: very large deep-chested humanoids]` six short deep pained huffs, no words | 6 sounds | P1 |
| `battle_bed` | L | a distant dense melee in a meadow: many indistinct weapon clashes, shield knocks and running footsteps, indistinct effort shouts with no words | 12 s | P1 |

Material map for the slice: kingdom infantry and wagons → `metal` (plate, kettle hats) or `wood` (pavise hits from the front); Hodman,
Hookgunner → `flesh` (quilted); Tormai → `flesh` heavy (felt) with `metal` on helmets and lamellar; Tattiebogles → `straw` (an
extension to the juice material set; §13); Cairnwakes → `stone`; Hail-Swifts → `stone` (opaque packed hail, no spirit material). The Wagon Ring's boards and wheels are cosmetic
(they are never hit); its sounds are wood and iron (§9.6).

### 9.4 Ranged, siege and wheels

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `hookgun_fire` | O | an early hand-cannon firing: a deep whump followed by a sharp crack, then a short hissing smoke tail | 4 × 1.6 | P0 |
| `bullet_hit` | O | a small lead ball hitting: a thud into a body, a knock into wood, a ping off iron, a puff into earth | 4 × 0.3 | P0 |
| `guntower_fire` | O | two hand-cannons firing almost together from a timber tower, a double whump-crack with a smoke hiss | 3 × 1.8 | P0 |
| `bombard_fire` | O | a short bronze bombard firing: a big deep boom, a heavy low thump and a rolling smoke hiss | 3 × 2.0 | P0 |
| `shot_whistle` | O | a heavy round shot flying overhead, a descending whistling whoosh | 3 × 1.0 | P1 |
| `bombard_hit` | O | a cannonball landing: a deep earthy thump, dirt and stones spraying, a short rumble | 4 × 1.0 | P0 |
| `javelin_throw` | O | a spear-thrower whipping a javelin away: a quick wooden snap and a fast whoosh | 4 × 0.5 | P0 |
| `javelin_hit` | O | a bronze-tipped javelin hitting: a solid thunk into wood, a thud into a body, a ping off metal, a thud into earth | 4 × 0.4 | P0 |
| `bowmast_fire` | O | a big laminated recurve bow on a swivel atop a tall wooden mast: a rope creak, a deep bowstring twang, then a fast arrow whoosh | 3 × 0.8 | P0 |
| `slingcart_throw` | O | a two-wheeled throwing-arm cart: a rope creak, the wooden arm whipping forward, a heavy thump against the stop beam | 3 × 1.2 | P0 |
| `claypot_hit` | O | a heavy clay pot smashing on the ground: a crash of shards, a dull thump, a puff of dust | 4 × 0.8 | P0 |
| `sling_stones` | O | a leather sling whirling twice and releasing a stone, then the stone cracking against wood | 4 × 0.8 | P0 |
| `gust_bolt` | O | a small magical bolt of whirling dust and wind: a short rising swish, then a soft gritty puff on impact | 4 × 0.6 | P0 |
| `atk_ember_flick` | O | the Firewright's attack: a small clay pellet of embers flicked from a linstock with a hiss, then a soft fiery pop on impact | 4 × 0.4 | P0 |
| `atk_glint` | O | the Skymirror's glint bolt: a short bright metallic zip of reflected light ending in a soft glassy tick | 4 × 0.4 | P0 |
| `atk_herb_mote` | O | the Linden Sister's attack: a soft papery puff and a dull leafy thud (reused pitched down for the Crowherd's attack) | 4 × 0.3 | P0 |
| `cart_roll` | L | a heavy two-wheeled wooden cart rolling slowly on a dirt road: wheel creak, axle squeal, rattling planks | 6 s | P0 |
| `cart_stop` | O | a cart stopping: a brake creak and planks settling | 3 × 0.6 | P1 |

### 9.5 Buildings and economy

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `build_loop_kingdom` | L | steady rhythmic timber construction: wooden mallets driving pegs, a hand saw cutting a plank, ladder creaks, an occasional plank dropped on a pile | 8 s | P0 |
| `build_loop_clans` | L | steady rhythmic raising of a big felt tent: wooden lattice clacking open, poles knocking into a crown ring, ropes creaking tight, big felt sheets flapping, a mallet tapping stakes | 8 s | P0 |
| `build_done_kingdom` | O | a timber scaffold collapsing outward with a dusty wooden clatter and a soft dust whump | 2 × 1.5 | P0 |
| `build_done_clans` | O | a big felt cover pulled tight and tied: a rope cinch, a felt thump, bronze rings clinking | 2 × 1.2 | P0 |
| `destroy_kingdom` | O | a half-timbered building collapsing: heavy timber cracks, plaster slumping, clay roof tiles sliding and shattering, a rumble and debris patter | 2 × 3.0 | P0 |
| `destroy_clans` | O | a large felt tent collapsing: felt tearing, wooden lattice folding flat with a clatter, a dust burst, and a bronze gong falling last with a loud clang | 2 × 3.0 | P0 |
| `bhit_timber` | O | a heavy blow on a timber-and-plaster wall: a thud, a crack, plaster crumbling | 3 × 0.8 | P0 |
| `bhit_felt` | O | a heavy blow on a felt wall over wooden lattice: a muffled thud with a lattice creak | 3 × 0.8 | P0 |
| `bhit_shell` | O | a heavy blow on an enormous ancient tortoise shell: a deep hollow knock | 3 × 0.8 | P1 |
| `burning` | L | a wooden building burning: steady crackling fire, popping timber, a low roar | 8 s | P1 |
| `repair_kingdom` | O | a mallet tapping pegs and a trowel scraping plaster | 4 × 0.4 | P1 |
| `repair_clans` | O | a thick needle punching through felt and a rope pulled tight | 4 × 0.4 | P1 |
| `mine_in_out` | O | a worker entering a timbered mine adit: a frame creak, footsteps on rock, muffled pick clinks inside, a flap thump | 3 × 1.3 | P0 |
| `gold_drop` | O | a small sack of gold nuggets dropped on a wooden counter, a bright jingle and a soft thump | 4 × 0.5 | P0 |
| `chop_axe` (kingdom) | O | single strikes of a felling axe into a living tree trunk, a solid woody tok with a little leaf rustle | 4 × 0.4 | P0 |
| `chop_adze` (clans) | O | single bites of a bronze adze into a tree trunk, a duller woody chock with a faint metallic ring | 4 × 0.4 | P0 |
| `tree_fall` | O | a tree cracking, creaking and falling with a heavy leafy crash | 2 × 2.5 | P0 |
| `lumber_drop` | O | a bundle of split logs dropped on a wooden pile, a clattering clack | 4 × 0.5 | P0 |
| `coins_bounty` | O | a few small coins tumbling onto grass with a bright clink | 3 × 0.4 | P0 |
| `mine_low` (groan, collapse) | O | old mine timbers groaning; then a mine entrance collapsing with a timber crack, a rockslide rumble and dust | 2 × 1.5 + 1 × 3.0 | P1 |
| `levy_horn` | O | a long low wooden horn call of two notes: a long low note, then a shorter note a minor third higher, rough and earthy, outdoors with a short echo | 2 × 2.5 | P0 |
| `levy_arm` | O | a farmer unslinging a threshing flail: a chain rattle, a wooden handle slap, an iron hat clapped onto a head | 3 × 0.8 | P0 |
| `gong_call` | O | a very large bronze gong struck hard once with a huge shimmering bloom, then a fast roll of softer strikes | 2 × 3.0 | P0 |
| `felt_roll` | O | a heavy felt tent skirt rolled up quickly: felt flapping, a rope zip, a wooden lattice rattle | 2 × 1.0 | P0 |

**Building select one-shots** (one job each, 2 variants of about 1.2 s, wrapper O; each building's "voice" when clicked, a core layer of the genre's feedback; 19 jobs: **8 P0** for the halls, altars, barracks and shops, the rest P1):

| Building | Clause | P |
|---|---|---|
| Moot Hall | a heavy oak door opening, one knock of a gavel, an indistinct murmur with no words | P0 |
| Croft | a farmhouse door latch, a few hens clucking, a stork clattering its bill on the roof | P1 |
| Oath Hall | a heavy iron wheel set in a stone floor turned a little with a deep grinding creak, and a low warm bell hum | P0 |
| Drill Yard | rhythmic stamping of boots and two wooden practice poles clacking together | P0 |
| Timber Yard | a two-man pit saw rasping through a log, then a sawn log end thunking onto a stack | P1 |
| Foundry | a bellows whoosh, molten bronze hissing, two hammer strikes on an anvil | P1 |
| Collegium | a stone pestle grinding herbs in a mortar and one small clear bell from a bell-cote | P1 |
| Wainwright Yard | a mallet tapping wheel spokes, an iron tyre clanging into place, an axle creak | P1 |
| Curio Cabinet | a small wooden drawer sliding out, then a tiny brass shop bell over a door | P0 |
| Lookout / Gun Tower | a ladder creak, wind across a timber platform, a slow-match fuse hissing | P1 |
| Shell Hall | a deep bronze gong touched lightly, its hum resonating inside a huge hollow shell, felt hangings flapping | P0 |
| Home Yurt | a felt door flap lifted, a kettle bubbling, a soft lattice creak | P1 |
| Grapple Yard | a heavy body thrown onto packed sand, one small bronze bell, a wooden fence creak | P0 |
| Naming Stones | a frame of small bronze gongs touched by the wind, one after another, over a very low stone hum (nothing hangs on the stones) | P0 |
| Casting Pit | a kiln roaring, a crucible pour with a hiss, charcoal crackling | P1 |
| Mirror Yurt | shimmering mirror chimes and a soft gust of wind | P1 |
| Bow-Mast | a tall wooden mast creaking in the wind, felt ribbons fluttering, a bowstring tapping | P1 |
| Tea Tent | a big bronze urn bubbling, then two small bronze cups clinking together | P0 |
| Coaching Inn | a door latch lifting, a horse snorting in a stable, an indistinct murmur of a crowded room with no words | P1 |

### 9.6 Spells, abilities, items and hero events

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `ab_linden_balm` | O | a gentle healing spell: a soft breeze of rustling leaves and drifting blossoms, a warm low bell chord swelling gently, no voices | 3 × 1.5 | P0 |
| `ab_herb_poultice` | O | a soft papery puff as a herb poultice is pressed on, a little leaf rustle and one faint high chime | 3 × 0.5 | P0 |
| `ab_smoke_of_rue` | O | a clay censer cracked open, bitter herb smoke hissing outward in a rolling cloud, a dry crackle of burning leaves | 2 × 1.4 | P0 |
| `ab_brace_wheel` | O | a heavy wooden cart wheel slammed upright onto the ground, its iron rim ringing, a deep defiant resonant thud | 3 × 1.0 | P0 |
| `ab_wagon_ring` (3 jobs) | O + L + O | painted wooden wagon boards and heavy spoked wheels slamming down into the ground one after another in a ring: a rolling chorus of heavy wooden thuds, iron wheel rims ringing and a chain rattle; then a low steady creak of timbers and chains under strain as a loop; then the boards lifting and clattering away into a cart with a dusty thump | 2 × 2.5; L 7 s; 2 × 1.2 | P0 |
| `ab_naphtha` (2 jobs) | O + L | a clay flask flying and shattering, a liquid splash, then a big soft whoomph of ignition and crackling flames; then burning ground crackling as a loop | 3 × 1.5; L 6 s | P0 |
| `ab_fuse` (2 jobs) | L + O | a fuse lit with a scratch, then sizzling and spitting sparks steadily; then a compact gunpowder explosion with a sharp crack and debris patter | L 4 s; 3 × 1.2 | P0 |
| `ab_wadding_hit` | O | a tiny sizzle and pop as a burning wad catches on cloth | 4 × 0.4 | P1 |
| `ab_grand_bombard` | O | a heavy bronze cannon dropped onto a timber platform: wheels thudding, chains settling (its shots reuse `bombard_fire` pitched down 15 %) | 2 × 1.5 | P0 |
| `ab_plant_pavise` | O | a tall wooden shield planted into earth with a solid stake thunk and boards knocking | 3 × 0.6 | P0 |
| `ab_braced_rest` | O | a wooden forked rest planted into turf with a light thunk | 3 × 0.3 | P1 |
| `ab_dust_veil` | O | a low rush of dust rolling outward along dry grass with a soft sand hiss, then a dry "fwump" as it settles; nothing whirling or rising | 3 × 1.4 | P0 |
| `ab_veil_strike` | O | a sudden strike out of nowhere: a sharp sabre slice with a burst of sand | 3 × 0.6 | P1 |
| `ab_braid_lash` | O | a heavy braided rope whipping out with a crack, a bronze weight hitting with a thunk, a body dragged a short way over grass | 3 × 1.0 | P0 |
| `ab_clean_cut` (the Uncut's critical strike; renamed 2026-10-19, §13 #26) | O | a straight sabre ringing clean and bright after a decisive cut, a shimmering high metallic ring | 3 × 0.6 | P0 |
| `ab_tall_grass` (2 jobs) | O + O | a rushing gust through tall grass rising to a hiss; then long straight slashes through tall grass, fast airy rips | 2 × 1.2; 4 × 0.5 | P0 |
| `ab_sunglint` | O | a blinding flash of sunlight from a polished bronze mirror: a bright shimmering chime swell and a searing high ping | 3 × 1.0 | P0 |
| `ab_moonglint` | O | a cold pale glint of moonlight off a mirror: a glassy soft chime with an airy shiver | 3 × 1.0 | P0 |
| `ab_bronze_window` | O | a polished bronze mirror flipped down over the eyes, rippling like water: a small metal flip, a soft shimmering swell and a distant wind | 2 × 1.5 | P0 |
| `ab_hail_swifts` | O | hailstones pattering on stone and packing together into small birds, then an ice crackle and a wind snap; cold, no bird cry | 2 × 1.8 | P0 |
| `swift_attack` | O | a packed-hail swift skimming low over the grass: a quick wing flick and an icy pellet tick | 4 × 0.4 | P1 |
| `ab_swallowed_sun` (3 jobs) | O + L + O | the daylight being swallowed: a deep inverted swell where all sound is sucked inward into a low hollow drone; then that drone alone as a loop; then light pouring back with a bright airy release | 2 × 2.0; L 10 s; 2 × 1.0 | P0 |
| `ab_wind_back` | O | a quick rising whirl of dusty wind with flapping ribbons | 3 × 1.0 | P0 |
| `ab_unbind` | O | ribbons and threads snapping loose in a strong gust, with a soft dispersing whoosh | 3 × 1.0 | P0 |
| `ab_shove` | O | a heavy wrestler's shove: two bodies colliding with a thick thud and a stumble of feet | 3 × 0.6 | P0 |
| `ab_signal_shell` | O | a short bronze bombard's flat cough, a rising whistling shell, then the crackling pop of a flare that hangs in the air and fizzes; played on the 3D World bus so the enemy hears it (a reveal is a public cue, like the recalls) | 3 × 1.5 | P0 |
| `ab_cadence` | O | Measured Cadence learned or first engaged: a calm low marching drum beat with a soft woody tap on each beat, starting up | 2 × 1.0 | P2 |
| `revive_kingdom` | O | an iron wheel turning in a stone floor, a deep resonant bell, a rising warm whoosh | 2 × 2.0 | P0 |
| `revive_clans` | O | small bronze gongs chiming beside standing stones, a deep gong bloom, a rising breath of wind | 2 × 2.0 | P0 |
| `inn_revive` | O | the instant revive at the Coaching Inn: an inn door swinging open, one bright brass door bell rung hard twice, a warm rising whoosh (distinct from both altar revives) | 2 × 1.5 | P0 |
| `cr_smoke_pot` | O | a clay smoke-pot cracking open and thick smoke billowing out with a hiss | 3 × 1.2 | P0 |
| `cr_fumes` | O | a thick sputtering cloud of acrid fumes erupting with a muffled puff (Choking Fumes silences: the player must hear it) | 2 × 1.2 | P0 |
| `cr_ember_rake` | O | an iron rake scraping and flicking burning embers, a sizzle and crackle (also the Sootcoat Coal-Lobber's hot-coal attack, pitched up) | 3 × 0.6 | P0 |
| `cr_bellows` | O | the Kiln-Master's Stoke the Coals: a big leather bellows wheezing three times over a smoke-pot, coals roaring brighter with a crackle | 2 × 1.2 | P0 |
| `cr_heal_tar` | O | a hot sizzle of sticky pine-tar slapped onto cloth with a wet thwap (Pine-Tar Dressing; reused with a dry straw rustle layered for the Crowherd's Re-Stuff) | 3 × 0.6 | P0 |
| `cr_light_fingers` | O | one small coin flicked off a thumb with a bright tink and caught in a palm | 3 × 0.4 | P0 |
| `cr_scatter_crows` | O | a burst of crows taking off from straw: frantic wing flaps and harsh caws | 2 × 1.5 | P0 |
| `cr_ley_pulse` | O | a deep humming pulse from ancient standing stones: a low resonant thrum spreading outward with a gravel shiver | 2 × 1.5 | P0 |
| `cr_ley_tether` | O | the Menhir Elder's Ley Tether: a taut low string thrum that pins down, then a gravel crunch | 3 × 0.8 | P0 |
| `cr_rockfall` | O | a stone fist hitting: a rocky crack and a heavy thud with gravel | 3 × 0.6 | P1 |
| `cr_settle` | O | stacked stones settling with a slow grind | 2 × 0.6 | P2 |
| `it_drink` | O | a cork pulled with a pop and a quick gulp from a small bottle, a tiny warm chime | 3 × 0.8 | P0 |
| `it_pigeon` | O | the Homing Pigeon: a pigeon cooing through the channel, then a burst of wing flaps and a soft puff of feathers; 3D World bus | 2 × 2.0 | P0 |
| `it_peg` | O | a small wooden peg hammered into the ground with two taps | 3 × 0.4 | P1 |
| `it_recall_horn` (Way-Home Horn) | O | a small bright brass post-horn blowing one long note that rises slowly and swells over five seconds into a soft airy shimmer (distinct from the low wooden Levy Horn); played on the 3D World bus so nearby enemies hear it | 2 × 5.0 | P0 |
| `it_recall_felt` (Way-Home Felt) | L | a rolled felt flapping open in a rising wind over a bronze singing bowl hum that rises in pitch, even density so it loops for the five-second channel; 3D World bus | 5 s | P0 |
| `it_recall_arrive` (shared) | O | a group arriving out of nowhere: a soft rushing whoosh ending in a padded ground thump and a puff of dust | 3 × 0.8 | P0 |
| `it_ward_set` | K | 1. a tiny clockwork figure wound up with three ratchet clicks and set down with a whirr (Tin Watchman), 2. a cold pale pebble set on stone with a glassy tick (Hail-Eye Pebble) | 2 × 2 × 0.4 | P0 |
| `it_chalk_line` (Tailor's Chalk) | O | a taut chalked string plucked and snapped against the ground, a dry thwack, a faint powdery tick and a short string hum | 3 × 0.6 | P0 |
| `it_tattle_burrs` (Tattle-Burrs) | O | a soft toss of a handful of dry burdock burrs scattering through grass with a bright shower of tiny tin bells, then a thin high bell jingle that keeps jingling as it moves away. The jingle tails are cut into `it_burr_jingle` takes that a revealed unit plays, pitched ±, while it moves (≤ 1 per unit per 1.5 s) | 3 × 0.8 | P0 |
| `it_powerup` | O | a power-up picked up: a bright two-note rising chime with a quick paper flutter | 3 × 0.8 | P0 |
| `it_eat` | K | 1. a crisp bite into wax honeycomb and a short chew (Honeycomb Wedge), 2. a fresh sprig snapped and chewed (Mint Sprig) | 2 × 2 × 0.6 | P1 |
| `it_fireflies` | O | the Firefly Jar: a cork pop and a soft rising shimmer of tiny wings | 3 × 1.0 | P1 |
| `it_slate_wipe` | O | a damp cloth wiped once across a slate with a soft squeak (Wiped Slate; `ui_skill_learn` follows) | 3 × 0.6 | P1 |
| `loot_glint` | O | a faint high glint, a tiny soft shimmer that fades, for an item bundle lying on the ground | 3 × 0.4 | P1 |

**Item sound map** (reuse before new jobs; every slice item in neutrals §4 and the two faction shops): drinks (Linden Salve, Sage's
Tincture, Rosehip Draught, Bluebell Cordial, the Tormai teas) → `it_drink`; Honeycomb Wedge and Mint Sprig → `it_eat`; recall
channels → `it_recall_horn` (kingdom), `it_recall_felt` (clans), `it_pigeon` (neutral), each followed by `it_recall_arrive` at the
hall; wards → `it_ward_set` (Tin Watchman, Hail-Eye Pebble) and `it_peg` (Snoop Peg); reveals → `it_chalk_line` (Tailor's Chalk),
`it_tattle_burrs` then `it_burr_jingle` (Tattle-Burrs), `ab_signal_shell` (Signal Shell); Smoke Pellets → `cr_smoke_pot` pitched up;
Firefly Jar → `it_fireflies`; Wiped Slate → `it_slate_wipe` then `ui_skill_learn`; power-ups → `it_powerup`, except the Dropped Purse →
`coins_bounty`; passive items (Hobnails, Stoutheart Weight, the permanents) → `ui_item` on pickup only; the Folded Yurt unfold →
`felt_roll` then `build_done_clans`; the Picnic Hamper → `it_drink` pitched down with a cloth rustle. **A recall channel is a public cue**, as in the genre: its sound plays
on the 3D World bus for every player who can see the hero, together with the ring at the hero's feet (§2.3), so an enemy can punish it.

### 9.7 Ambience (Greenvale)

| Id | W | Clause | N × D (s) | P |
|---|---|---|---|---|
| `amb_gv_day` | A | calm summer hill country at midday: gentle wind through meadow grass, a few distant skylarks and songbirds, a light bee and insect buzz, a faraway brook | 60 s | P0 |
| `amb_gv_night` | A | summer hill country at night: steady crickets, soft wind, the churring of a nightjar now and then, very sparse | 60 s | P0 |
| `st_dawn` | S | dawn arriving over hill country: a blackbird begins to sing, a soft rising airy shimmer, one low bronze bowl tone | 1 × 5 | P0 |
| `st_dusk` | S | dusk falling: a lone curlew call, crickets fading in, a soft low bronze hum that sinks away | 1 × 5 | P0 |
| `lp_spring` | L | a spring pool fed by a wooden flume: trickling water and a tiny creaking waterwheel | 8 s | P0 |
| `swt_birds` | O | separate takes of short songbird phrases, a woodpecker drumming, a cuckoo call | 5 × 2.0 | P1 |
| `swt_wind` | O | a wind gust through leafy trees, rising and falling | 3 × 3.0 | P1 |
| `swt_night` | O | separate takes of a distant fox bark, a hedgehog snuffling, a single frog croak | 4 × 1.5 | P1 |
| `lp_brook` | L | a small brook babbling over stones | 10 s | P1 |
| `lp_pond` | L | a still pond: water lapping, frogs, a few insects | 10 s | P1 |
| `lp_charcoal` | L | a smouldering turf-covered charcoal mound: a soft crackle, steam and smoke hiss | 8 s | P1 |
| `lp_weighstall` | L | a market stall in the wind: the chains of a big brass balance creaking, a canvas awning flapping, a soft wind chime | 8 s | P1 |
| `lp_standing_ring` | L | a ring of ancient standing stones: a very low steady hum with faint gravel shifting | 8 s | P1 |
| `amb_base_kingdom` | A | a small market town heard from its edge: storks clattering their beaks on rooftops, a far-off smith's hammer, a cart creak, an indistinct murmur with no words | 30 s | P1 |
| `amb_base_clans` | A | a felt-tent camp: felt flaps in the wind, distant chimes of small bronze plates, a kettle bubbling, felt ribbons fluttering, an indistinct murmur with no words | 30 s | P1 |
| `lp_mine_night` | L | lanterns hissing at a mine entrance, slow water drips inside | 8 s | P2 |

Day and night beds crossfade over about 8 s, with the stinger on top. Sweeteners play positionally every 8–25 s within 40 m of the
camera focus. **No rooster at dawn, no wolf howl at dusk or night, and no owl as the night signature:** those are the most familiar
dawn and dusk cues of the reference RTS as commonly remembered (unverified, but cheap to avoid).

### 9.8 Creeps and critters

| Id | W | Clause | N | P |
|---|---|---|---|---|
| `cv_sootcoat` | V | `[voice: a hoarse, soot-covered outlaw with a smoky throat]` an aggressive shout of "Hup!", two short effort huffs, a pained cough, a death wheeze that ends in a cough | 5 | P0 |
| `cv_kiln_master` | V | `[voice: a bigger, deeper charcoal-burner boss with a rasping throat]` a bellowed "Hup!", a heavy effort huff, a pained growl, a death groan | 4 | P1 |
| `cv_sootcoat_sleep` | L | several people snoring softly around a smouldering fire, a low crackle | 10 s | P1 |
| `cv_tattie` | V | `[voice: a scarecrow come to life, no throat, all wood and straw]` a stiff creaking rise with a dry hiss, two wooden creak-swings, a sharp straw-rustle hiss, a collapsing heap of sticks and straw | 5 | P0 |
| `cv_crow` | V | `[voice: crows]` an alarmed caw, an attacking caw, a wounded squawk, a falling flutter | 4 | P0 |
| `cv_cairnwake` | V | `[voice: a walking stack of stone slabs, no throat]` a deep rumbling hum rising, two clacking slab efforts, a cracking split, a collapsing heap of stones | 5 | P0 |
| `cv_cairn_steps` | O | heavy flat stone slabs clacking down as footsteps | 4 × 0.4 | P1 |
| `cv_rundling_curl` | O | a small scaly creature curling into a ball: overlapping scales rustling and clicking | 2 × 0.8 | P1 |
| `cv_goose` | V | `[voice: an angry grey goose]` a honk, a hiss, a flapping charge, a smug honk | 4 | P0 |
| `cv_hare` | O | a hare thumping a hind foot twice, then dashing away through grass | 2 × 1.0 | P1 |
| `cv_sparrows` [SLICE+] | O | a flock of sparrows bursting out of a hedge, a rapid wing flutter and chirps | 2 × 2.0 | P2 |

Creep vocal sets map to the juice combat layers: aggro on acquire, effort on swing, pain at 20 % chance with a 1.2 s cooldown per type,
death on topple contact. Sleeping camps play only their snore loop (Sootcoats) or a faint creak (Tattiebogles by day).

### 9.9 Job count

| Group | P0 jobs | P1 jobs | P2 jobs |
|---|---|---|---|
| UI (incl. the order, selection, card and alarm kit sets) | 24 | 14 | 3 |
| Combat (`sw_pierce` now P0) | 16 | 9 | 1 |
| Ranged, siege, wheels (incl. the 3 `atk_*` basic attacks) | 16 | 2 | 0 |
| Buildings and economy (incl. 19 select one-shots, 8 of them P0) | 27 | 16 | 0 |
| Spells, items, hero events, creep casts (incl. recalls, wards, reveals, the Signal Shell, power-ups, inn revive) | 50 | 10 | 2 |
| Ambience | 5 | 10 | 1 |
| Creeps and critters | 5 | 5 | 1 |
| **Total (217 jobs)** | **143** | **66** | **8** |

---

## 10. Music

> **Composed in-house since 2026-10-20.** Paid music generation is banned (ElevenLabs Music through Krea cost about 444 CU
> for 10 s; asset ledger). Every piece except the kingdom opening cue is composed by the project in Python with
> `tools/music` (sources in `tools/music/pieces/`, rendered offline with FluidSynth, the MIT-licensed FluidR3_GM soundfont
> and numpy synths; list, sources and hashes in `assets/audio/music/manifest.json`). The §10.3 prompts remain as the
> musical briefs (key, mode, tempo, instruments, mood, structure); §10.1's lengths, avoid list and listening check, the
> §10.2 motifs (now quoted exactly) and §10.4's loudness and file names still apply.

### 10.1 Plan and rules

| Piece | Length | Use |
|---|---|---|
| Kingdom 1–3 | 3:20–3:40 each | Shuffled in-game rotation for a kingdom player |
| Clans 1–3 | 3:20–3:40 each | Shuffled in-game rotation for a clans player |
| Menu, "Two Roads" | 1:45, loopable | Main menu, lobby and loading screen |
| Victory (kingdom, clans) | 12 s each | End screen stinger |
| Defeat (kingdom, clans) | 12 s each | End screen stinger |
| End-screen bed, "Two Roads (score)" | 75 s, loopable | Under the score screen after either stinger: the stinger crossfades into it over 2 s at its natural decay, and it loops until the player leaves (the genre keeps music under the score screen rather than silence) |
| Match-opening cue (kingdom, clans) | 2.4 s each, trimmed from a 10 s generation | Played once when the match starts (juice §5.3 "Opening cue"): kingdom town bell with a fiddle and hurdy-gurdy flourish, clans gong swell with twin bronze horns |

- **Rotation like the genre, not adaptive bombast:** 20–40 s of silence between tracks, ambience carries the gaps, no battle-music
  switching (audio §3.3). Music bus −12 dB with the Voice side-chain duck.
- **Every prompt:** ElevenLabs Music v2.5 through Krea (`elevenlabs/music-v2.5`), `force_instrumental: true`, an explicit
  `music_length_ms`, genre + instruments + key + tempo + mood + structure + "no lyrics". **Never** a franchise, studio, game,
  composer or performer name.
- **Avoid** (the reference races' colours): full symphonic brass fanfares with big choir (kingdom), taiko with low brass and electric
  guitar (clans), an airy solo female voice with harp and flute as the lead colour (any faction).
- **Listening check:** two reviewers who know the reference soundtrack listen to each piece; any melody that recalls a reference theme
  is regenerated. Wordless hums or chants may be stripped by `force_instrumental`; accept that rather than risk generated words.

### 10.2 Motifs (ours)

- **Kingdom "Wheel" motif:** five notes climbing stepwise from the tonic to the fifth, the last two held (short-short-short-long-long),
  answered by a falling fourth. The Levy Horn's minor-third call (§9.5) is its battlefield echo.
- **Clans "Gong-Ring" motif:** a falling figure fifth-fourth-tonic, then a held second that resolves to the tonic, over a gong stroke.
- AI music cannot be forced to quote a motif; the prompts describe them and the listening check decides. The stingers may later be
  rebuilt by hand from the motifs if the generated ones drift.

### 10.3 Prompts

| Piece | `music_length_ms` | Prompt (`force_instrumental: true`) |
|---|---|---|
| **Kingdom 1, "Market-Day Muster"** | 210000 | Instrumental fantasy strategy-game score for a stubborn, warm-hearted kingdom of craftsmen who defend their towns with wagons and early gunpowder. A Central European village band gone to war, not a symphony orchestra: hurdy-gurdy drone, bright fiddle melody, hammered dulcimer arpeggios, frame drum and a crisp field snare, two low natural horns, a soft wordless male hum far in the background. D Mixolydian, 92 BPM, proud, sturdy and good-humoured with a hint of melancholy. Melody idea: a short five-note figure that climbs step by step and holds its last two notes. Structure: hurdy-gurdy and dulcimer intro (20 seconds), main theme on fiddle, a marching B section where the horns take the melody over the snare, a lighter interlude of dulcimer and plucked fiddle, the full theme again, then a calm outro that resolves on the tonic. Mid-level dynamics, background music that never overwhelms, no lyrics, no big choir, no brass fanfare. |
| **Kingdom 2, "Boards and Thunder"** | 220000 | Instrumental fantasy strategy-game score, the battle-ready side of a town-militia kingdom. Village band instruments only: two field snares in an interlocking march ostinato, a deep frame drum, a bagpipe drone, fiddle double-stops, hammered dulcimer tremolos, two low natural horns calling in short two-note signals, and occasional distant low drum booms like faraway cannon. G Dorian, 100 BPM, determined and gritty but never grim. Structure: snare ostinato and drone intro (15 seconds), a driving A section led by fiddle, a B section of horn calls answered by dulcimer, a tense drum-only bridge, the A section returning fuller, and a firm final cadence on G. Background music, no lyrics, no orchestra, no choir. |
| **Kingdom 3, "Linden Curfew"** (`mus_kingdom_linden_curfew`) | 200000 | Instrumental fantasy strategy-game score for a quiet evening on the walls of a small kingdom town. A soft hurdy-gurdy drone, a lyrical solo fiddle, gentle hammered dulcimer, a low natural horn far away, a very soft frame-drum heartbeat. A Dorian, 84 BPM, warm, reflective and a little homesick. Structure: dulcimer and drone intro (20 seconds), fiddle melody, a B section where the horn answers from far away, a sparse interlude of plucked dulcimer, the melody once more, and a soft ending that resolves on A. Low intensity, no lyrics, no choir, no harp. |
| **Clans 1, "Herd Road"** | 210000 | Instrumental fantasy strategy-game score for proud, courteous nomad households of the open grasslands. Deep frame drums in a galloping 6/8 over 4/4, struck and bowed bronze gongs, a raspy two-string bowed fiddle carrying the melody, jaw harp pulses, long low bronze horns, a swelling wordless deep overtone chant, hand claps and stamps. D Dorian, 92 BPM, proud, windswept and warm. Melody idea: a falling three-note figure that comes to rest after a held note. Structure: gong swell and jaw-harp intro (20 seconds), fiddle theme over galloping drums, a B section where the horns and the chant swell together, a sparse windy interlude, the theme again with full percussion, a resolving outro on D. Background music, no lyrics, no taiko, no electric guitar, no brass section. |
| **Clans 2, "The Gong-Ring Gathers"** | 220000 | Instrumental fantasy strategy-game score for a great council of nomad households gathering around a ring of bronze gongs. Slow, stately and ceremonial: a big frame drum on every second beat, bowed gong swells, two long bronze horns calling and answering across a valley, the two-string bowed fiddle with a slow noble melody, a low wordless overtone drone, hand claps that build in the second half. E Mixolydian, 84 BPM, dignified, warm and faintly humorous. Structure: bowed-gong intro (20 seconds), horn calls, the fiddle melody, a B section where claps and drums build, a quiet drone bridge, the melody with the full ensemble, a resolving close on E with one last gong. Background music, no lyrics, no orchestra. |
| **Clans 3, "Long Grass Gallop"** | 200000 | Instrumental fantasy strategy-game score for a fast ride across endless grassland. Galloping frame drums and stamps at a driving tempo, a jaw-harp rhythm, a plucked long-necked two-string lute, the raspy two-string bowed fiddle in fast runs, bright bronze gong accents, a short burst of deep overtone chant at the climax. A Dorian, 100 BPM, exhilarating and wind-blown. Structure: lute and jaw-harp intro (15 seconds), drums enter, the fiddle theme, a B section with call and response between lute and fiddle, a breathless drum break, the theme at full power, an outro that slows and resolves on A. Background music, no lyrics, no taiko, no electric guitar. |
| **Menu, "Two Roads"** | 105000 | Instrumental main-menu theme for an original heroic fantasy strategy game about a town-militia kingdom and proud nomad households. It begins with a lone hurdy-gurdy drone and one soft bronze gong bloom; then a fiddle states a climbing five-note melody and a raspy two-string fiddle answers with a falling one, two cultures meeting. Frame drums enter, then hammered dulcimer and long bronze horns, building to a broad, warm climax at about 1:10, then thinning back to the hurdy-gurdy drone and a gong so it can loop. D Dorian, 80 BPM, hopeful, grand but intimate, no lyrics, no choir, no orchestra. |
| **Victory, kingdom** | 12000 | Short instrumental victory flourish for a town-militia kingdom: a crisp field-snare roll, two low natural horns and a fiddle playing a bright rising phrase in D major, hammered dulcimer sparkle, a bagpipe drone swelling under the last chord, ending on a strong held tonic chord with a natural decay. About 12 seconds, no vocals. |
| **Victory, clans** | 12000 | Short instrumental victory flourish for proud nomad households: galloping frame drums accelerating, one huge bronze gong strike, long bronze horns playing a broad rising phrase in D Mixolydian, hand claps, ending on a held chord inside the gong's shimmering bloom. About 12 seconds, no vocals. |
| **Defeat, kingdom** | 12000 | Short instrumental defeat cue for a town-militia kingdom: a slow hurdy-gurdy drone, a lone fiddle playing a falling phrase in D minor that does not resolve, a muffled frame-drum heartbeat, fading into silence. About 12 seconds, somber, no vocals. |
| **Defeat, clans** | 12000 | Short instrumental defeat cue for nomad households: a slow bowed gong swell, a low bronze horn phrase that falls and stops short, one soft frame-drum beat, a wind-like low overtone drone fading into silence. About 12 seconds, no vocals. |
| **End-screen bed, "Two Roads (score)"** | 75000 | Instrumental score-screen music for an original heroic fantasy strategy game, calm and reflective after a battle. A soft hurdy-gurdy drone and a low bronze gong bloom; a fiddle and a raspy two-string fiddle trade the climbing and falling phrases of the menu theme slowly, over sparse hammered dulcimer and a quiet frame-drum heartbeat. D Dorian, 72 BPM, warm, a little tired, neither triumphant nor sad, so it fits both victory and defeat. Structure: drone and gong intro (10 seconds), the two fiddles in dialogue, a soft dulcimer interlude, the dialogue once more, and an ending that settles back into the drone so it can loop. Low intensity, no lyrics, no choir, no orchestra. |
| **Opening cue, kingdom** | 10000 | Short instrumental match-opening flourish for a town-militia kingdom: one bright strike of a small town bell, then a quick rising fiddle and hurdy-gurdy figure that climbs five notes and holds, in D major. About 10 seconds with a natural decay; only the first 2.4 seconds are used. No vocals. |
| **Opening cue, clans** | 10000 | Short instrumental match-opening flourish for proud nomad households: a swelling bronze gong bloom with two long bronze horns calling a falling figure that comes to rest, in D Dorian. About 10 seconds with a natural decay; only the first 2.4 seconds are used. No vocals. |

**`_V2` A/B (§5.2).** These prompts open with genre-and-function words ("fantasy strategy-game score", "for an original heroic fantasy
strategy game"). Generate Kingdom 1 and the menu theme a second time with that opening replaced by "Instrumental folk-ensemble
background score for an original fantasy world" (everything after it unchanged), put both versions through the listening check, and
keep the opening that passes for every piece. Log both takes.

### 10.4 Post-processing and import

Trim the tail; master to about −16 LUFS integrated; export Ogg Vorbis stereo `-q:a 6` to `assets/audio/music/<faction>_<n>.ogg`,
`menu.ogg`, `victory_<faction>.ogg`, `defeat_<faction>.ogg`, `score.ogg` and `opening_<faction>.ogg` (trimmed to 2.4 s with a 300 ms
fade; if the model's minimum length is above 10 s, generate the minimum and trim). The menu and score loops are built by crossfading the last 2–4 s into the start;
in-game tracks do not loop (an `AudioStreamPlaylist` with shuffle and the silence gaps). Log every job, including rejected takes.

---

## 11. Production budget and order of work

Balances **verified on 2026-10-17** with Krea `get_balance` and Higgsfield `balance`: Krea **1,500.00 CU**, Higgsfield **77.5 cr**
(the 269.75 cr of the original brief has been spent on concepts, 3D and rigging: ledger #15–#24). Re-check before spending. 3D is
budgeted in the faction docs; this table covers the 2D and audio work owned by this bible, plus the 3D redos this bible asks for.

| Item | Count | Service | Unit cost | Estimate |
|---|---|---|---|---|
| Unit, hero and prop concepts (slice) | Done: 11 concepts (ledger #19). To do: the Pavisier (§5.6), the 3 regenerations with `CLANS_CLAUSE_V3` (§5.6), about 2 tries each, 7 props. The other Tormai concepts get the skin recolour in post (no cost) | Higgsfield | 0.25 cr | ≈ 5 cr |
| Hall concepts | Done (ledger #22) | — | — | 0 |
| Terrain, cliffs, water, swatches, foliage | Done: 13 (ledger #15) + 14 swatches (ledger #21). To do: ≈ 14 (the slice-extra swatches of §5.6, second tile variants, ≈ 4 swatches for the two T2 hall add-on kits, §5.5 T4) | Higgsfield | 0.25 cr | ≈ 3.5 cr |
| Image-to-3D redo: the Pavisier and any regenerated concept that passes the squint test | ≤ 4 | Higgsfield Tripo H3.1 | 9 cr | ≤ 36 cr |
| Icons: 45 items (33 neutral, 5 Curio Cabinet, 7 Tea Tent), ≈ 55 kingdom and ≈ 47 clans (units, heroes, abilities, buildings, research, summons for the selection grid, toggle states), 17 creep abilities | ≈ 164 icons = 41 sheets + 30 % retries ≈ 53 sheets | Krea 2 Medium | 9 CU per sheet | ≈ 477 CU (×4 if grids fail) |
| Command pictograms (18: 15 commands + 3 minimap toggles) | Hand-drawn SVG like the cursors (§5.5 T9 list); no generation | — | — | 0 |
| Hero portraits | 4 × 2 | Krea 2 Medium | 9 CU | 72 CU |
| UI frame parts | ≈ 18 | Krea 2 Medium | 9 CU | 162 CU |
| Loading tableau and upscale | 2 tries | Krea 2 Medium | 9 CU + upscale | ≈ 30 CU |
| Emblem concepts | 2 × 2 | Krea 2 Medium | 9 CU | 36 CU |
| VFX sprites | 6 | Krea 2 Medium | 9 CU | 54 CU |
| **2D and 3D-redo subtotal** | | | | **≈ 45 cr + ≈ 831 CU** |
| SFX P0 | 143 jobs (+20 since 2026-10-17: attacks, creep casts, the Signal Shell, reveals, 8 select sounds) | Seed Audio | 4.63 CU (flat) to about 10 CU (if billed per second) | ≈ 660–1,430 CU |
| Voice | 371 lines in ≈ 150 batched jobs | ElevenLabs TTS | unmeasured | probe |
| Music | ≈ 25 min in 14 pieces | composed in-house with `tools/music` (§10); only the kingdom opening cue came from the one ElevenLabs Music probe (444 CU, already spent) | 0 | **0 CU** |

**The audio budget is the risk** (the slice-plan §2.13–§2.15 envelopes are the spend caps: P0 SFX ≈ 378 CU in 54 grouped jobs, P0 VO 251
lines ≈ 379 CU, P0 music 200 CU; this table is the full content plan, reconciled at synthesis on 2026-10-19): after the 2D work about **670 CU** remain for SFX, voice and music, and P0 SFX alone need ≈ 660 CU
at the flat rate, so the CC0 fallback below is now the expected path for part of the P0 list. Decisions:

1. **Probe first** (one call each, logged): a 5-line TTS batch, a 30 s music clip, and one 4-variant Seed Audio job (to learn whether
   Seed Audio bills per job or per second). Recompute this table before any other audio spend.
2. If audio does not fit, in this order: (a) generate VO and music first (they carry the identity and VO expires on 31 Dec 2026);
   (b) move P1 and P2 SFX, and then the most generic P0 SFX to
   CC0, first `fall_light`, `coins_bounty`, `gold_drop` and `lumber_drop` (they offset the 8 building select sounds promoted to P0),
   then UI clicks and ticks, the other body falls and chop sounds (about 40 jobs in all), to
   **CC0** packs (Kenney Impact Sounds, RPG Audio, Interface Sounds; audio §5) with `CREDITS.md` entries; (c) if Seed Audio bills per
   job, merge more P0 SFX into kit sets (wrapper K, §9.1). Never move the signature cues (level-up, alarms, Levy Horn, gong call,
   recall channels, revives, the reveal cues, the P0 building select sounds) to stock packs.
3. Icons: if 2×2 grids fail, fall back to single Krea icons only for unit, hero and ability icons; research icons become procedural
   pictograms.

**Order of work**

1. Probes (above), the `_V2` A/B of §5.2 on the first concepts and the first music piece, and the style anchors: the Pavisier → `ANCHOR_UNIT_KINGDOM`; the Grappler skin recolour and squint test → `ANCHOR_UNIT_CLANS`; a neutral prop → `ANCHOR_NEUTRAL`; the first kingdom icon sheet → `ANCHOR_ICON` (the hall anchors exist).
2. Slice concepts (T1–T4): the Pavisier and the three regenerations (§5.6), then 3D for those that pass.
3. Terrain ladder, cliffs, water and kit swatches (T5–T7), then trees and doodads (T8).
4. **Voice for all 371 slice lines**, well before 31 Dec 2026.
5. Music (14 pieces).
6. P0 SFX by group: combat → economy and buildings → abilities → UI → ambience → creeps.
7. Icons, portraits, UI frame parts, cursors (hand-made), fonts installed.
8. Loading tableau and end-screen art.
9. Full-game squint review (ip-safety §5.3) on recorded clips, played with the **default** lobby colours (kingdom Emerald, clans Royal
   Blue, §2.4), since the review judges the game as played.

---

## 12. Compliance checklist (ip-safety §2.2, §2.4, §2.5, §2.8)

| Requirement | Where this bible meets it |
|---|---|
| §2.2 No reference-game lines or paraphrases; original advisories and banners | §8.1 rules 3–8: the review gate with an exact-match search against all five unit quote pages and the hero pages, plus named traps (the elected-king joke, dialect "me", "done" on kingdom completions, the supply-building advisor template, the two-gunner double act and its beats, address-word swaps, wind-speaker gags). Every line in §8.6–§8.10 was re-checked against those traps and re-counted against the §8.2 budgets on 2026-10-19 (review log, round 2); the exact-match search against the quote pages is the second reviewer's step (§8.1 rule 8) and is logged in the ledger when done. End-screen subtitles §7.10 are ours |
| §2.2 Annoyed lines allowed as a category, wording ours | §8.2 category table; "poke" banned project-wide (§8.1) |
| §2.1 Every ability, command and asset id has our own name | §9 ids and §2.3 props use current names only (`ab_bronze_window`, `cv_tattie`, `ab_clean_cut`, `it_chalk_line`, `it_tattle_burrs`, the Fair-Day Rosette, the Hiring Fair glyph, Measured Cadence, Lay Down Flails), checked against neutrals §10.1 round 2 on 2026-10-19; retired and reference-derived names (including the round-2 ones: the book power-up, the hired-militia camp, the powder reveal item, the critical-strike, recall-item and giant-hero names) are in `tools/ip/banned_terms.txt`, which also catches them inside snake_case ids |
| §2.4 UI layout free, UI art ours | §7.1 keeps only the functional layout (one console strip, which blocks input); §7.2 shared plain chassis with original inlays; autocast as a bottom bar and badge, never corner marks or a circling light (§7.4); no orb or dial (§7.5); no hand cursor (§7.6); OFL fonts (§7.7); original glyphs (§7.8); team colours in our own values and order, checked by `value_echo_reference.json`, with default-skip sets so no default match reproduces the reference trade-dress pairings (§2.4); icon rules ban the reference compositions we know of (the boot for haste, the pouch or puff for reveal, the book for attributes) (§5.5) |
| §2.5 No rips, motifs, cloned voices or composer names | §8.1 delivery (preset voices only, no cloning); §9.1 and §10.1 prompt rules; our own motifs (§10.2); level-up cue rebuilt as bells and bowl (§9.2); no rooster or wolf cues (§9.7) |
| §2.7 Inputs | §5.1: anchors are our own approved outputs, one per faction, and the non-compliant bake-off concept is excluded; no screenshots, fan assets or reference images in any request |
| §2.8 Prompt hygiene | §5.2–§5.4: fixed suffix and clauses with no banned token; every model is prompt-only, so look-alike risks are steered by positive counter-clauses (§5.3) and the negative lists are review checklists; this file passes the banned-terms checker; descriptions use function and qualities |
| §2.8 Review and ledger | §3.4, §4.1, §5.7 acceptance checks; rule 12 (ledger entry with reviewer, squint result and human edits) |
| §3.2 Distinctness rubric (visual and voice axes) | §2.1–§2.2 palettes (the Tormai skin is a warm ash-grey, never the blue that pulled toward the reference trolls), §4 silhouettes (including the traps from outside the reference RTS, §4.5), §2.1–§2.2 materials, the full Ember Wheel in every emblem prompt (§5.4), §8.3–§8.4 voices; each faction stays clear of its reference race on every axis |

---

## 13. Flags for other docs and open questions

**Edits this bible asks of other docs** (this bible only edits itself and the `tools/ip/` lists; each owner makes the change below)

1. **`kingdom.md` §3.2:** remove "poke" from the Hodman annoyed sequence and the Wheel Marshal's first annoyed line (use §8.6 and, for
   the Marshal, an opener such as "A jostled wheel keeps turning. Mostly."). **Done 2026-10-19** (kingdom §3.2 now uses "click"; the VO lint also bans tap and prod). **Ban jokes about voting for, electing or doubting the
   Crown** in every kingdom script (§8.1 rule 3). Fit the Linden Sister's lines to §8.2 (5 annoyed, word budgets).
2. **Done at synthesis (2026-10-19)** in kingdom §3.3 and §11, clans §3.1 and §12.1, and the slice-plan voice table. **Line totals:** the class standard is now worker 21, infantry or ranged 19 (standout 21; the Pavisier 20 for Plant Pavise on and
   off), caster 21, siege crew 17, hero 31, advisor 19 (+3 optional event lines). Update `kingdom.md` §3.3 and §11 (181 lines, the
   Linden Sister included; the Reeve's 19 include ECO-27's workers line and new hall, other-building and hero-in-danger lines) and
   `clans.md` §12.1 (180 lines; Sling-Cart 17 with 4 attack lines and no mechanic, Javelineer 21 with 4 attack lines and no mechanic,
   Gustcaller 21, advisor 19), `neutrals.md` (shopkeeper 10, already so in §5.3) and the slice-plan voice table (371 lines).
3. **Casting:** audio §4.2 gave the same preset voices to the retired Wardens worker and advisor that `clans.md` now uses for the
   Yurtwright and the gong-keeper. Rule: no preset is shared between factions (§8.1); the kingdom auditions other presets.
4. **Juice combat §4.8:** add a `straw` material (Tattiebogles), or map it to `wood` plus the `hit_straw` impact.
5. **Visual §7.2 team colours** are superseded by §2.4 (new values, new order, Lime instead of a brown); point the visual doc here.
6. **Visual §7.2 Greenvale ground colours** exceed the terrain saturation cap; §6.1 gives clamped targets.
7. **Visual §7.3 and audio §4.4–§4.5:** superseded by §5 (prompts) and §9–§10 (SFX and music prompts) for all new generation.
8. **`architecture.md` `CLIFF_H` 1.75 m** vs the README's 2.0 m: cliff art is authored for 2.0 m (§6.2).
9. **Command icons** are hand-drawn SVG pictograms shared by all factions (§5.5 T9, §11).
10. **Footprints (decided 2026-10-19, §1.3; the 10×10-hall fallback is retired). Done at synthesis (2026-10-19)** in rules §8, kingdom §7.2,
    clans §7, sylvan-and-deathless §A7/§B7, neutrals §5.1/§5.2/§5.8/§9 and slice-plan §1.4; still open: `architecture.md`, the procedural kit
    `tools/kits/buildings.py` (its cells) and the slice-map re-validation. Each owner updates its table so that the sim
    footprint equals the mesh width: **rules §8** (add the class footprints: hall 16×16, production, altar, shop and research 12×12,
    supply 8×8, tower 4×4 cells) and **`architecture.md`** (the example "hall 10×10, barracks 8×8, farm 4×4" becomes "hall 16×16,
    barracks 12×12, farm 8×8, tower 4×4"); **`kingdom.md` §7.2** (Moot Hall, Walled Burg, Crown Burg 10×10 → 16×16; Drill Yard,
    Timber Yard, Collegium, Wainwright Yard, Stork Loft 8×8 → 12×12; Oath Hall, Foundry, Curio Cabinet 6×6 → 12×12; Croft 4×4 → 8×8;
    towers stay 4×4) and §13 Q1 (closed); **`clans.md` §7** (Shell Hall, Banner Shell, Sun-Gong Shell 10×10 → 16×16; Grapple Yard,
    Mirror Yurt, Herd Pen 8×8 → 12×12; Casting Pit, Naming Stones, Tea Tent, Guest Ring 6×6 → 12×12; Home Yurt 4×4 → 8×8; Bow-Mast
    stays 4×4) and its §2.1 scale-table note; **`neutrals.md` §5.1, §5.2 and §9** (Gold Seam 8×8 → at least 12×12, so the mine reads
    at least barracks-sized beside an 8 m hall; Weighstall 8×8 → 12×12; Coaching Inn and Hiring Fair 10×10 → 12×12; Hale Spring
    6×6 → 8×8); **`slice-plan.md` §1.4** (the inn's 5 × 5 m → 6 × 6 m, the seams to 6 m) and a **re-validation on the slice map** of
    the 6.0 m hall–mine gap, the main-ramp chokes, the wall-off widths and the inn's 6.5 m cliff clearance with the new sizes.
    Built kit pieces only change `--width`.
11. **Done at synthesis (2026-10-19).** **`kingdom.md` §6.3 The Wagon Ring:** the VFX text "a ghostly ring of wagon wheels rises" becomes physical painted wagon boards and
    wheels slamming down into a barricade (§1.7 `K_WAGON`, §9.6), so the kit never reads as the reference holy knight's mass
    resurrection. The heroes juice's Wagon Ring visuals follow.
12. **Juice HUD-04:** replace the corner dots and the comet lap with §7.4 (a steady bottom-edge bar and the looped-arrow badge; on fire,
    one sweep along the bottom bar); move the "capable but off" notch from bottom-left (the short-resource corner) to the bottom rail.
13. **Done at synthesis (2026-10-19).** **Rules §18.5 autocast:** "Autocast on: a steady bar in the faction accent along the button's bottom edge plus a looped-arrow badge
    (art bible §7.4). Never corner marks, a gold border or any light that circles the edge."
14. **Juice HUD-07:** the skins follow §7.2 (plain plates, inlays on rims only, no leather or parchment panel fills, no centre crest);
    the clock is the Horizon Ribbon (§7.5), which takes over HUD-07's golden-hour rim, dusk/dawn clunk and day tally. POR-01's
    portrait values and NTF-05's idle-worker button are adopted in §7.1 and need no change.
15. **Juice ui-camera-audio §5.3:** the clans alarm's "dry bone-rattle shake" becomes "dry seed-pod rattle" (bones are a banned clans
    motif); the content of every cue there is now a §9.2 job.
16. **Juice AUD-03 and the heroes `audio.gd` row:** the file id is **`built`** (label "Built"; reversed on 2026-10-19 at synthesis: slice-plan §2.12 wins, because the interim "job" + "done" id echoed a banned catch-phrase in file names, and its three spellings are now banned terms); `levelup_5` and `levelup_10`
    alias to `levelup_a` in the slice; `effort` is a non-verbal set; an ability order plays one line, never `yes` plus the ability
    line, and AUD-03 takes over the ability-line gate (proposed 50 %, 8 s per hero) as a trigger rule (§8.1).
17. **Done at synthesis (2026-10-19).** **`clans.md` §3.3:** the Grappler What line "Hm-hm. Big ears, listening." contradicts the small rounded ears and the no-"Hm-hm"-in-acks
    rule (§8.1); use "Big shoulders, small patience." Check the other clans acks against the §8.2 word budgets.
18. **`clans.md` §7 Bow-Mast:** "horn bow" may stay in lore text, but prompts and sound clauses say "laminated recurve bow of wood and
    bronze" (§4.3, §5.6, §9.4), so no prompt says "horn".
19. **`clans.md` later Thoom, Guest Ring and Kettle-Uncle (the giant hero, renamed in #26):** keep the house-sized vessel a tea kettle (spout, lid, handle) and the
    giants flat-bellied; never a cooking cauldron with meat, a gut-plate, a meat hook or a cleaver (§4.5 steppe-ogre trap).
20. **Done** (B16 and E3 are P0). **`slice-plan.md` B16 and the Collegium row** are P1, but `kingdom.md` §5.2 and §11 put the Linden Sister and the Collegium in the
    slice and the build order trains two Sisters at 7:40: raise both to **P0** (the concept and model already exist, ledger #19–#20).
21. **`neutrals.md` §8.1** budgets item and creep-ability icons on Higgsfield (≈ 12 cr); with 77.5 cr left, they move to the Krea icon
    sheets of §11. Its audio list (sell, bundle glint, inn revive bell) is now `ui_sell`, `loot_glint` and `inn_revive`.
22. **`tools/build_slice_units.sh`** builds `kingdom_infantry` from the ledger #7 bake-off concept, which fails §4.2 (§5.1). It is a
    placeholder: replace it with the §5.6 Pavisier before any public build.
23. **Done at synthesis (2026-10-19).** **`kingdom.md` §3.3 Bombard Wagon crew:** one speaking voice, the loader non-verbal (§8.1 rule 7).
24. **`src/systems/player_state.gd` `COLORS`** is the reference lobby set in the reference order (seven colours within ΔE 15 of it,
    light blue at ΔE 0.8), and `make()` assigns `COLORS[pid % size]`. Checked again on 2026-10-19: neither §2.4's twelve bases nor the
    lobby rule is implemented. Replace the table with §2.4's twelve bases in table order and assign each new player the first free
    colour on its **faction's preferred list** (§2.4: kingdom Emerald, Tangerine, Turquoise, Lime, Violet, Forest, Pewter; clans Royal
    Blue, Cornflower, Lime, Emerald; Coral Rose moved to the clans' trade-dress skip set on 2026-10-19), falling back to the lowest-numbered free colour; a manual lobby pick overrides it.
    Add a test that a default 1v1 gives kingdom Emerald and clans Royal Blue. Until then `python3 tools/ip/check_value_echo.py`
    reports 7 team-colour errors and exits 1, by design.
25. **Done at synthesis (2026-10-19).** **`clans.md` §3.3 Grappler What:** its first What line is a one-word swap of a reference flyer-rider's What line (only the address
    word changed); replace it with "Your grip, Ring-Elder?" (§8.9) and apply §8.1 rule 3's address-word rule to every clans and
    kingdom script.
26. **Renames, adopted at synthesis on 2026-10-19 in every design doc (other-IP echoes; the bible already uses the new names in ids, props and clauses, and the retired forms are on
    `tools/ip/banned_terms.txt`):** the Uncut's critical-strike passive (`clans.md` §6) → **Clean Cut** (`ab_clean_cut`), since the
    old name is a tabletop RPG's spell name with the same function; the recall items (`kingdom.md` §7.4, `clans.md` §9 and every other
    mention) → **Way-Home Horn** and **Way-Home Felt** (low risk, but the old "[home] + object" pattern echoes a known action RPG's
    return-home item); the later Thoom giant hero (`clans.md` §2.1, §3.1, §6) → **Kettle-Uncle** (`clans_hero_kettle_uncle`; lore:
    the Tormai call every Thoom "uncle"), so the name no longer points at the steppe-ogre cauldron trap of §4.5 and #19.
27. **Done at synthesis (2026-10-19).** **`kingdom.md` §7.4 Tailor's Chalk:** add the VFX note of §2.3 (the hero snaps a chalked tailor's line that marks a 9 m ring;
    revealed units show white tacking-stitch outlines; never a thrown powder, dust cloud or puff) and the sound `it_chalk_line` (§9.6).
28. **Juice ITM-01 and ITM-02:** the loot colours (oilcloth `#6E6248`, twine `#C9B48A`, seal `#B8322A`) are now the bible's final
    values (§2.3), so ITM-01 keeps them; replace its retired book power-up prop with the **Fair-Day Rosette** (§2.3), and ITM-02's
    "leafs the book" gesture with the hero pinning the rosette on. The heroes-juice notes N2 and V5 follow.
29. **Juice NTF-01 and AUD-03:** the advisor set is 19 lines (§8.10): hall attacked (main hall only), other building attacked, units,
    workers (ECO-27's horn prompt for the kingdom, a gong prompt for the clans), and **hero in danger** (below 40 % HP). AUD-03 adds the
    `mech` triggers of §8.2 (Plant Pavise on and off; the first Braced Shot plant after a move order, ≤ 1 per 20 s; Shove, ≤ 1 per
    10 s; the Bombard Wagon's deploy brace, ≤ 1 per 20 s) and the new word and rate budgets of §8.1 rule 1.
30. **Done at synthesis (2026-10-19)** (and slice-plan B7–B11). **`clans.md` §2.1 and §6.1 heights:** the Uncut and Skymirror 2.2 m → **2.35–2.4 m** (1.25 × the 1.9 m Grappler; §1.3, §4.1 area
    check). The scale table's "Tormai heroes 2.2–2.3 m" follows.
31. **`neutrals.md` §8.2 prompt rules and §2.1 G2:** the turnip-lantern counter-clause is "pierced with a few small randomly drilled
    holes and no face, fixed on a short pole" (§5.3 `NEG_TATTIE`); the Gold Seam, Weighstall, inn and spring footprints follow #10.
32. **Done in clans §0, §2.1, §2.2, §2.6 and §12.3 at synthesis (2026-10-19)**; the texture clamp on the ledger #19 models stays open. **`clans.md` Tormai skin:** every skin value and prompt becomes the §2.2 ash-grey ("ash-grey stone-coloured skin like weathered
    granite, with pale hail-speckles"; mid `#77746F`), never "slate blue-grey"; the rigged ledger #19 models get the §5.7 skin-band
    clamp on their textures.

**Open questions**

1. Do 2×2 icon and tile grids generate cleanly with Krea 2 Medium and `gpt_image_2_5`? If not, icon cost rises about 4×.
2. Does Seed Audio bill per job or per second? Does ElevenLabs Music keep wordless chant with `force_instrumental: true`?
3. Upscale route and cost for 16:9 loading art (Krea 2 Medium is 1K only).
4. Will burgundy units on the Crimson team (a manual pick only since 2026-10-19) pass the night-grade readability check (§3.4)?
   Verify on the first rendered Pavisier.
5. Does `gpt_image_2_5` honour the `#D0D0D0` background and magenta-only-on-team-cloth instructions reliably? Measure on the first
   five concepts; if not, key the background in post and repaint stray magenta.
6. Is the meadow at saturation 45 % too grey on screen? If so, raise only the meadow clamp to 52 % (§1.4), never the units.
7. Which ElevenLabs preset voices fit the "audition" rows best? Decide with the 5-line probe and record the mapping in the ledger.
8. The livery colours of the tabletop wargame's northern bear-kingdom (§4.5) are unverified; check them before any kingdom key art.
9. What is ElevenLabs Music's minimum length? The 2.4 s opening cues assume a 10 s generation trimmed (§10.4).
10. *Closed 2026-10-19:* footprints are decided (§1.3, §13 #10). Remaining check: the slice-map re-validation in §13 #10.
11. Which `_V2` texts of §5.2 pass the A/B? Until decided, `_V1` stays the default.

---

## Review log (2026-10-17: IP-safety and fidelity reviews)

Retired names are described, not quoted, in this log: the bible is scanned by the banned-terms checker, and they are now on its list.

| # | Severity | Issue | Change |
|---|---|---|---|
| 1 | Major | Hodman annoyed #5 repeated the reference worker's "doubting the elected king" joke (also a comedy-film gag) | Replaced with the ledger payoff "Right. That's a full silver. Agnes is drawing up the invoice. She has lovely handwriting." (§8.6); voting, electing or doubting the Crown added to the §8.1 rule 3 avoid-list; kingdom §3.2 asked to ban it (§13 #1); §12 no longer claims every line was clean without the new checks |
| 2 | Major | The reveal sound id kept the retired "Far-" ability name, which becomes a shipped filename | Renamed `ab_bronze_window` with the brief "a polished bronze mirror flipped down over the eyes, rippling like water" (§9.6); the old name, its snake_case form and the other retired names added to `tools/ip/banned_terms.txt` |
| 3 | Major | The worker-militia release command and its line stacked two reference command names | The project name is already **Lay Down Flails** (rules review; kingdom §4, §5.4, §7.5, rules §19), which removes the reference name, so the bible uses it rather than the suggested "Down Flails"; the "back to the bricks" one-word swap is replaced by "Flail's on the hook. Agnes, where were we?" and "Iron off, straw on. Hello, Agnes."; the three reference command names were already on the banned list |
| 4 | Major | Team colours reused the reference 12 in the reference lobby order, some within ΔE 2–9 | New set and order (§2.4): Crimson, Royal Blue, Gold, Emerald, Tangerine, Violet, Cornflower, Lime, Turquoise, Coral Rose, Pewter, Forest; every base ≥ ΔE 20 from the reference set (Lime replaces a brown that failed the swap test on both factions; Pewter moved to `#B0A6D6` and Forest to `#2A8C4A` to clear skin and the threshold; Royal Blue and Gold lowered to value 90 %); swap test and conflict rows re-run; `team_colours` block and a ΔE check added to `tools/ip/value_echo_reference.json` and `check_value_echo.py`, which also flags the code's colour table (§13 #24) |
| 5 | Major | Autocast state reproduced the reference corner marks and circling motion | Steady 3 px accent bar on the bottom edge plus a looped-arrow badge with a 0.5 Hz breath; firing sweeps the bottom bar only (§7.4); "corner marks or chasing lights around a button" added to §7.11 and §4.5; HUD-04 and rules §18.5 edits listed (§13 #12, #13) |
| 6 | Major | The single unit anchor (ledger #7) breaks the kingdom rules and steered both factions | Ledger #7 is now a bake-off record only, never a style input; `ANCHOR_UNIT_KINGDOM` (a §4.2 Pavisier, to make), `ANCHOR_UNIT_CLANS` (the Grappler, candidate) and `ANCHOR_NEUTRAL` for icons and loading art; anchors never cross factions (§5.1); the shipped placeholder model is flagged (§13 #22) |
| 7 | Major | Negatives never reached prompt-only models, and three clans concepts drifted | Schemas checked: every model we use is prompt-only (§5.1 table); every `NEG_*` add-on now has a positive counter-clause written into the subjects (§5.3, §5.6); Skymirror, Javelineer and Gustcaller marked for regeneration and a fresh squint test before any 3D redo (§5.6) |
| 8 | Major | Only two Tormai subjects carried the ear and jaw spec; the Javelineer read as the reference forest-troll spear thrower | The same ear-jaw-no-tusk sentence is in every Tormai subject and in `CLANS_CLAUSE_V2`; the Javelineer is broad and stocky with a peaked hood over a felt cap; "lanky, hunched, long arms, mohawk" in `NEG_CLANS` with a counter-clause; §4.3 squint target names the spear thrower |
| 9 | Minor | "Hub flame" contradicted the emblem's no-flame coal | "Hub coal" (§2.1); a red-and-ivory-plus-gold-flame trap row in §4.5 |
| 10 | Minor | The clans clause listed "horn"; the kingdom clause named the colours it avoids | `_V2` clauses: no "horn" (the Bow-Mast bow is a "laminated recurve bow of wood and bronze" in its own subject and in `bowmast_fire`); no "no blue, no gold-yellow trim" (§5.4) |
| 11 | Minor | The Uncut's critical-strike sound described a curved sabre | "a straight sabre ringing clean and bright after a decisive cut" (§9.6; the id became `ab_clean_cut` in round 2) |
| 12 | Minor | The linden token still named the retired aura | `K_LINDEN` covers Linden Balm and the Linden Sister only; new `K_CADENCE` drum-pulse ring for Measured Cadence (§1.7); `aura_learn` became `ab_cadence` |
| 13 | Minor | The Wagon Ring used the revive's ghost colour, reading as a mass resurrection | Physical painted boards and wheels (`K_WAGON`, non-emissive), wood and iron sounds with a chain rattle (§9.6); `K_WHEEL_GHOST` is the Oath Hall revive only; the material map no longer calls it ethereal (§9.3); kingdom §6.3 edit listed (§13 #11) |
| 14 | Minor | Two bickering voices on the gunpowder-siege slot | One speaking gunner; the loader is non-verbal (§8.1 rule 7, §8.2, §8.3); the Sling-Cart keeps its two brothers |
| 15 | Minor | Advisor and completion lines sat near the reference templates | Need supply: "Every croft's full. No room for more hands." (kingdom §3.2); research: "The guild has signed it off."; built line: "Signed, sealed and plastered. Somebody check the corners."; "…'s done" and a bare "Done." banned on kingdom completion events (§8.1) |
| 16 | Minor | "Big ears" on the Grappler; dialect "me" for "my" on the Hodman | "Big shoulders, small patience." and "Lime in my ears." (fitted to the 4-word What budget; the TTS recipe sample updated); dialect "me" banned (§8.1); clans §3.3's own line flagged (§13 #17) |
| 17 | Minor | Guardrails covered only one publisher's look-alikes | `NEG_KINGDOM` and `NEG_CLANS` gained the tabletop wargame traits (sleeves, berets, comet, griffon, double eagle, bear, fur caps, winged lancers, gun-rest axes, ice magic; bellies, gut-plates, hooks, cleavers, cooking cauldrons) with counter-clauses; three §4.5 trap rows; the bear-kingdom livery check is an open question; later giants flagged (§13 #19) |
| 18 | Major | Five slice buildings had no art or audio | Timber Yard, Collegium, Curio Cabinet, Tea Tent and Coaching Inn added to §1.3, §4 must/never rows, §5.6 kit swatches, §9.5 select one-shots and §7.8 minimap glyphs (lantern, droplet in a ring, balance beam); `inn_revive` added as P0 (§9.6) |
| 19 | Major | The Linden Sister was [SLICE+], unvoiced, with no ability sounds | Marked [SLICE] (§5.6, §8.2, §8.3; 21 lines); `ab_herb_poultice` and `ab_smoke_of_rue` P0 (§9.6), `K_SMOKE_RUE` token; slice-plan B16 and the Collegium flagged for P0 (§13 #20) |
| 20 | Major | No sound or look for recalls, wards, reveals, power-ups, selling or the loot glint | `it_recall_horn`, `it_recall_felt`, `it_recall_arrive`, `it_ward_set`, `it_reveal_puff` (replaced in round 2 by `it_chalk_line` and `it_tattle_burrs`), `it_powerup` (P0), `ui_sell`, `loot_glint` (P1); recall channels are public 3D cues with a ring at the hero's feet; the channel is 5 s per rules §6.8 (not 3 s); power-up props and recall items added to §2.3; an item sound map added (§9.6) |
| 21 | Major | Ack length caps were unreachable at the stated speech rates | Word and second budgets per category; acks ≥ 2.8 words/s for every speaker with weight from pitch and formant; "Hm-hm" only in Ready, Annoyed and advisor lines (§8.1, §8.2); every example rewritten and checked by script against the budgets; the TTS recipe measures each take and applies `atempo` ≤ 1.15 or rejects it (§8.11) |
| 22 | Major | Annoyed runs were cut short and trigger numbers contradicted AUD-03 | Annoyed 5 per unit, 7 for heroes and one standout per faction (Hookgunner, Javelineer); all trigger numbers deleted from the bible and pointed to AUD-03 (§8.1) |
| 23 | Major | Engine voice categories were unbudgeted | `need_mana`, `pack_full`, `levelup_a` + `levelup_6`, `ultimate_shout` (replaces `ab_r`), `rival`, `effort`; `built` renamed to an interim "job" + "done" id (reversed to `built` at synthesis, 2026-10-19); advisor "revealed to the enemy" line (17 per advisor, +3 optional event lines); totals: worker 21, infantry 19 (standout 21), caster 21, siege 17, hero 31; slice 365 lines (§8.2) |
| 24 | Major | Two incompatible HUD specs | The bible is the single owner of HUD looks (ownership table). Kept the Horizon Ribbon and moved HUD-07's golden-hour rim, clunk and day tally onto it (§7.5); plain chassis with rim inlays, no panel fills or centre crest (§7.2); adopted POR-01's 150 × 150 portrait and gradients and NTF-05's 52 × 52 idle-worker button (§7.1, §7.9); a continuous 40 % console band joins the plates; HUD-04, HUD-07 and rules §18.5 edits listed (§13 #12–#14). Where the IP and fidelity fixes conflicted (the fidelity reviewer proposed adopting the comet border), IP won: no light circles the edge |
| 25 | Major | The UI sound list missed the juice kit, and the alarms clashed with the juice spec and the Levy Horn | ~20 per-faction jobs (order, selection, disabled, cooldown P0; card, misc, clock, cripple P1; feed P2) using a new kit-set wrapper (§9.1); alarms follow the current juice §5.3 structure (kingdom clashing tower bells, clans slit drum with a seed-pod rattle, each with an urgent take), never a horn or gong; menu-only hover ticks; §9.9 and §11 recomputed |
| 26 | Major | The hero info and inventory UI lacked attributes, bonuses, upgrade marks, rank frames and slot markers | STR anvil, AGI hare, INT candle with the primary attribute at 1.25× and underlined; "STR 23 +2" and "24–30 +4" with bonuses in `#7FD86A`; 0–3 upgrade pips (§7.8); rank frames (§7.3); numpad chip, charge count and cooldown sweep on inventory slots (§7.4) |
| 27 | Major | Building heights were fixed while footprints stayed open | Footprint-first table: halls 16×16 cells (8 m), production, altar, shop and research 12×12, supply 8×8, towers 4×4, height ≈ width, `process_model --width` per class, and a 10-cell fallback (§1.3); sign-off requested (§13 #10) |
| 28 | Major | Stale and retired names | The retired creep-family name, aura name and reveal-ability id replaced with Tattiebogles (`NEG_TATTIE`, `cv_tattie`), Measured Cadence (`K_CADENCE`) and `ab_bronze_window`; "a straight horse-sabre"; the retired names and their snake_case forms added to the banned list |
| 29 | Minor | The icon budget undercounted; the pictogram list was incomplete | ≈ 161 generated icons (43 items, ≈ 55 kingdom, ≈ 47 clans, 16 creep abilities) ≈ 53 sheets ≈ 477 CU; the 15 command pictograms are hand-drawn SVG (attack ground, return cargo, build advanced, learn, cancel or back, unload all added), plus toggle states and summon icons (§5.5, §11). Balances re-checked live: Krea 1,500.00 CU, Higgsfield 77.5 cr; the audio remainder is ≈ 670 CU, not ≈ 815 |
| 30 | Minor | Workers had one mechanic line for two events | Worker mechanic = 2 (arm and release) (§8.2, §8.6, §8.8) |
| 31 | Minor | A hero could say `yes` and the ability line together | An ability order plays exactly one line on the input frame (§8.1) |
| 32 | Minor | Button corners collided | One corner table: top-left "+" or charges, top-right lock or autocast badge (mutually exclusive), bottom-left short-resource glyph, bottom-right hotkey or numpad chip, bottom-centre shop stock, bottom edge autocast bar (§7.4) |
| 33 | Minor | Slice default colours contradicted the table order | Slots follow the table; the lobby rule skips a faction's readability-conflict colours, giving the kingdom Royal Blue and the clans Crimson; the "genre-default" claim deleted (§2.4). **Superseded 2026-10-19** (round 2, #1 and #22): per-faction preferred lists with default-skip sets give kingdom Emerald vs clans Royal Blue |
| 34 | Minor | Hazel's harvest and sight rules were undefined | Hazel is a harvestable tree (50 lumber, blocks sight, leaves a stump) inside tree lines; hawthorn hedges are the non-harvestable doodad that does not block sight (§6.4) |
| 35 | Minor | Silence after the 12 s end stingers | A 75 s loopable "Two Roads (score)" bed under the score screen, plus 2.4 s match-opening cues per faction (§10.1, §10.3, §10.4) |
| 36 | Minor | Only T1 and T2 hall reads were defined | T3 rows (Crown Burg: clock tower with our astronomical face and a double onion dome; Sun-Gong Shell: giant mirror-gong crown), the top third of the T1 height reserved, at most +15 % per tier (§1.3, §4.2, §4.3) |

Found while fixing (not raised by the reviewers): the Naming Stones select sound still described mirrors on cords, which the clans
review removed (now small gongs, §9.5); `gpt_image_2_5` exposes no seed, so its seed blocks are ledger ids only (§5.1); the code's
player colour table echoes the reference set (§13 #24).

---

## Review log, round 2 (2026-10-19: IP-safety and fidelity reviews)

Retired names are again described, not quoted (they are on the banned-terms list). Where the two reviews conflicted, IP won and the
closest legal alternative was taken (#21, #24). This bible edits only itself and the `tools/ip/` lists; every edit it needs in another
doc or in code is a §13 item.

| # | Severity | Issue | Change |
|---|---|---|---|
| 1 | Major | The lobby rule gave every default match a blue kingdom against red brutes: the franchise's canonical pairing, and on ivory and bronze the ruled-out blue/white/gold livery, in every clip and playtest | Per-faction **preferred lists** with a **default-skip set** (trade dress: kingdom Royal Blue, Cornflower, Gold; clans Crimson, Violet; plus the readability rows); slice default **kingdom Emerald vs clans Royal Blue**; manual picks stay free; rows reclassified "Trade dress (default-skip)"; marketing rule: kingdom Emerald or Tangerine, clans Royal Blue (§0, §2.4, §11 step 9). Round-1 log #33 marked superseded. `player_state.gd` checked: it implements neither the colours nor the rule, so §13 #24 now specifies the lists and a default-1v1 test |
| 2 | Major | "Slate blue-grey" skin primed the reference troll look on prompt-only models | Ash-grey "weathered granite" skin `#77746F` / `#585551` / `#D2CEC6` (saturation ≤ 8 %); `CLANS_CLAUSE_V3`, the `NEG_CLANS` counter-clause and every §5.6 subject without "blue"; blue, blue-grey and teal skin in `NEG_CLANS` and the forbidden list; a skin-band clamp in the faction LUT (hue 170–250°, saturation 10–30 % → ≤ 10 %; felt and team colour untouched) and a reject rule (skin hue 180–240° above 10 %) in §5.7; the three drifted concepts regenerate with V3, the other Tormai concepts, models and the clans anchor get the clamp; swap test re-run (nearest now Pewter, ΔE 36.3); §13 #32 |
| 3 | Major | The emblem was prompted as a bare ivory wheel on burgundy, a real civic coat of arms | Canonical `EMBLEM_KINGDOM_V1` (hub coal with ember core, three crown points, `[FIELD]`) in `NEG_KINGDOM`, the Pavise (magenta field), `ANCHOR_UNIT_KINGDOM`, banners and T13 (§5.3–§5.6); decorative folk wheels only in repeated bands; T13 "at most four flat colours"; the level badge keeps the coal with the number on a burgundy plate (§7.3, §7.8); "wheel without hub coal or crown points" in `NEG_KINGDOM`; §5.7 compares at 24 px with the arms of Mainz, Erfurt and Osnabrück |
| 4 | Major | Three names retired by neutrals round 2 (the hired-militia camp, the book power-up, the powder reveal item) were still in the glyphs, props and sound map | Hiring Fair glyph (§7.8); Fair-Day Rosette prop and "no book among item props" (§2.3); Tattle-Burrs with its own `it_tattle_burrs` cue (§9.6); the retired forms added to `banned_terms.txt` (the rules review had added two of them the same day); checker re-run on the bible and the default paths: clean; §12 updated |
| 5 | Major | Tailor's Chalk was voiced as thrown chalk or flour: the reference revealing powder's object, effect and look together | `it_reveal_puff` deleted; `it_chalk_line` (P0): a snapped chalk line marking a 9 m ring, revealed units outlined in white tacking stitches (§2.3); §9.1 rule "no thrown powder, dust cloud or puff for any reveal"; reveal icons are a mirror, a chalk line or bell-strung burrs (§5.5); kingdom §7.4 flagged (§13 #27) |
| 6 | Major | A Grappler What line was a reference rider's line with only the address word changed | "Your grip, Ring-Elder?" (§8.9); §13 #25 for clans §3.3; §8.1 rule 3 bans address-word swaps |
| 7 | Minor | Four acks matched or nearly matched quote-page lines | Yurtwright: "The kettle can wait.", "Tell me. Still counting.", "Between two knots. Yes?"; Grappler: "A fair hold."; §8.1 rule 8 adds an exact-match search against all five unit quote pages and the hero pages; §12 says that search is the second reviewer's pending step |
| 8 | Minor | A wind-caster tic of "the wind says…" sat beside the reference spirit-caster's voices bit and the genre's flatulence gags | §8.1 rule 3 bans wind-breaking jokes, voices-or-spirits framing and "to the winds" / "winds guide" phrasing; the tic is now petty gossip about people ("The wind says your cousin still owes me tea.") |
| 9 | Minor | The Sling-Cart brothers carried the reference two-gunner team's comic structure | Rule 7 bans self-identity confusion, partnership lines and explosion punchlines; new hook: a counted argument over whose turn it is to haul the rope; the reviewer checks both brothers against that team's quote section |
| 10 | Minor | Genre-and-function words in the style suffix, the music prompts and the level-up clause act as an attractor | `_V2` test set in §5.2 (`STYLE_SUFFIX_V2` "tabletop-miniature fantasy art", template phrases, music opening "folk-ensemble background score for an original fantasy world", an instruments-only level-up clause, the SFX wrapper); A/B notes in §9.2 and §10.3; §11 step 1; keep what passes, log both |
| 11 | Minor | Other-IP echoes: a tabletop RPG spell name, an action RPG's return-home item pattern, a giant hero named for the cauldron trap | §13 #26 rename requests: **Clean Cut** (`ab_clean_cut`), **Way-Home Horn / Felt**, **Kettle-Uncle**; the bible already uses them (§2.3, §4.5, §8.4, §9.6); retired forms banned |
| 12 | Minor | The turnip-lantern counter-clause would give a carved face | "pierced with a few small randomly drilled holes and no face, fixed on a short pole"; a face on the turnip and a swappable head added to `NEG_TATTIE`; `N_LANTERN` and §2.3 notes; §13 #31 |
| 13 | Minor | "Ribbons around a boot" for haste repeated the reference speed item's icon | Ribbons behind a running hare or a bent grass-head in a gust; footwear only for move-speed items (§5.5) |
| 14 | Major | Footprints were open while art was made at 8 m halls | Closed in favour of §1.3 (hall 16×16, production 12×12, supply 8×8, tower 4×4 cells; the sim footprint equals the mesh width; the fallback retired); a neutral row (Gold Seam ≥ 12×12, Weighstall 12×12, inn 12×12, Hale Spring 8×8); §13 #10 lists every table edit (rules §8, `architecture.md`, kingdom §7.2, clans §7, neutrals §5.1, slice-plan §1.4) and the slice-map re-validation of the 6.0 m mine gap, chokes and wall-offs |
| 15 | Major | Out of date against neutrals round 2 | (a)–(c) as #4; (d) the sound map now covers every slice item: `it_eat` (Honeycomb Wedge, Mint Sprig), `it_fireflies`, `it_slate_wipe` (P1), Smoke Pellets → `cr_smoke_pot` pitched up, Dropped Purse → `coins_bounty`, passives → `ui_item`; (e) 33 neutral items, 17 creep abilities, ≈ 164 icons in 41 sheets; shopkeeper 10 lines |
| 16 | Major | Slice attacks and creep casts had no sound | P0 `atk_ember_flick`, `atk_glint`, `atk_herb_mote` (Crowherd reuse), `ab_signal_shell` (a public 3D cue), `cr_bellows`, `cr_heal_tar` (Re-Stuff reuse), `cr_ley_tether`, `cr_light_fingers`; `cr_ember_rake` P0 for the Coal-Lobber reuse; `sw_pierce` P0; found while fixing: `cr_fumes` P0 (it silences). §9.9: 217 jobs, 143 P0; §11 ≈ 660–1,430 CU |
| 17 | Minor | The minimap toggles did not match the rules | Formation, Show Camps and Colour mode (24 px), the 4th slot reserved for ally ping (§7.1); 3 pictograms, 15 → 18 (§5.5, §11) |
| 18 | Minor | The advisor set did not match NTF-01 | 19 lines: hall attacked (main hall only), other building attacked, hero in danger added; the kingdom workers line is ECO-27's horn prompt, the clans one a gong prompt (§8.10); totals kingdom 181, clans 180, slice 371 with #20 and the shopkeeper (§0, §8.2, §11, §13 #2, #29) |
| 19 | Minor | Word caps at the minimum rates overran the seconds caps | What and Yes ≤ 4 at ≥ 3.0 words/s; Attack ≤ 4 and Warcry ≤ 5 at ≥ 2.8; short situational ≤ 4; Annoyed ≤ 16; everything else ≥ 2.5 words/s (which also fixes the 8-word lines); advisor ≤ 11. Every §8.6–§8.10 candidate re-counted by script: 6 Attack lines and 1 annoyed line shortened, no violation left |
| 20 | Minor | Mechanic lines without triggers; the Pavisier was a line short | Pavisier 2 (20 lines); Hookgunner on the first Braced Shot plant after a move (≤ 1 per 20 s); Bombard Wagon on the deploy brace; Javelineer and Sling-Cart 0, their slot a 4th Attack line (21 and 17 kept); AUD-03 flag (§8.2, §13 #29) |
| 21 | Minor | Repeated hats blurred the worker and the caster | §4.1 rule: the job-defining shape differs per unit, the faction hat may repeat; hero area check added. Gustcaller: a **low rounded felt cap with streaming ribbons** and the vane ≥ 0.4 m above the head (§4.3, §5.3, §5.6). The reviewer's flat-brimmed hat was not taken: at 64 px it would read as the kingdom's brim disc |
| 22 | Minor | Lean Tormai heroes were only 1.16 × the Grappler | The Uncut and Skymirror 2.35–2.4 m (§1.3); §4.1 hero silhouette area ≥ 1.3 × the largest slice infantry; clans sync (§13 #30) |
| 23 | Minor | The on-screen height measure was undefined | Screen-space bounding box, feet to topmost pixel, at screen centre, default zoom, 1080p; verify on the Pavisier, Hodman and Wheel Marshal; fallback class heights (§1.2) |
| 24 | Minor | The lobby rule was silent on taken colours and put the kingdom in blue | Merged into #1: each player takes the first free colour on its own list, then the lowest free one. Royal Blue is left off the kingdom list entirely (IP wins over the suggested third place) |
| 25 | Minor | A 2.5–3.5 m hazel coppice inside tree lines read as a gap from the −56° camera while blocking like a 6–7 m oak | Tree-wall rule: every tree that blocks pathing and sight has its crown top ≥ 4.5 m and a canopy overlapping its neighbours; hazel becomes a 4.5–5 m "tall coppice"; short shrubs only as non-blocking doodads (§1.3, §6.4) |
| 26 | Minor | All building select sounds were P1 | 8 P0 (Moot Hall, Oath Hall, Drill Yard, Curio Cabinet, Shell Hall, Naming Stones, Grapple Yard, Tea Tent; a P column in §9.5); `fall_light`, `coins_bounty`, `gold_drop`, `lumber_drop` lead the §11 CC0 fallback |
| 27 | Minor | Open HUD details | The console band blocks input; selection grid 2 × 6 tiles of 40 px with 4 px HP and 3 px mana bars; queue of one 48 px active icon and 6 waiting 40 px icons; Gold Seam "Gold remaining"; progress bars with seconds for hall upgrades and research (§7.1, §7.4) |
| 28 | Minor | The T2 halls had no production rule or upgrade look | T4 rule: the T1 GLB plus a bpy add-on kit at the same width and ≤ +15 %, ≈ 0.5 cr of swatches each; per-faction add-ons; construction dressing and `build_loop_<faction>` while upgrading (§5.5, §11) |
| 29 | Minor | Loot colours differed from ITM-01; the retired book prop was still in ITM-01; no Adamant glyph | Final loot colours are ITM-01's (`#6E6248`, `#C9B48A`, `#B8322A`): the darker oilcloth separates better from every Greenvale ground tile (§2.3); §13 #28 asks ITM-01 and ITM-02 to swap the book for the rosette; Adamant glyph (§7.8) |

Found while fixing: another review's concurrent sweep had already renamed the powder reveal item in §9.6 and reworded a §9.1 phrase
that matched a newly banned term; `cr_fumes` promoted to P0 (#16); the `NEG_KINGDOM` counter-clause spells the emblem out in full, so it
can be pasted without expansion; the full-game squint review (§11 step 9) is played with the default lobby colours.
