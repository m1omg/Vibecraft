# Vibecraft research: index and decisions

Research date: 2026-10-16. Goal: an original Godot 4.7 RTS with the *feel* of Warcraft III (2002), not the
look of Freecraft/Stratagus clones, and not a copy of WC3. All seven docs were fact-checked on 2026-10-16;
each has its own fact-check log. The shared WebSearch budget ran out, so checks used direct fetches, the local
Godot 4.7.2 engine, Krea's live schemas and in-container benchmarks. Liquipedia was rate-limited, so the
480 s day/night figure rests on its API and search excerpts. Items marked "(unverified)" in a doc stay unverified here.

## Index

| Doc | What it covers | Start with |
|---|---|---|
| [visual-art-direction.md](visual-art-direction.md) | WC3 Classic vs Reforged look, camera constants, scale and HUD layout, why Stratagus looks generic, modern references, 58 annotated images, our style plan, Krea prompt kit, AI post-processing, Godot lighting recipe | §0, §2, §7 |
| [video-references.md](video-references.md) | About 100 oEmbed-verified videos: pro games, campaigns, Reforged comparisons, GDC talks, RTS devlogs, Godot RTS tutorials, 17 "key moments" with timings, measuring protocol | §0, §G |
| [audio-direction.md](audio-direction.md) | WC3 audio anatomy and voice-line counts, our faction voices and music, bus layout and priorities, Krea audio endpoints and prompts, CC0 fallbacks, Godot pooling code | §0, §3, §4, §6 |
| [gameplay-mechanics.md](gameplay-mechanics.md) | Numeric WC3 reference (economy, upkeep, heroes, creeps, day/night, damage matrix, controls), reuse vs copy, **slice rule set** | §11, §13 |
| [godot-rts-tech.md](godot-rts-tech.md) | Engine approaches with benchmarks from this container: sim loop, grid pathing, terrain, fog, picking, camera, HUD, tests, animation | §0, §12 |
| [ai-asset-pipeline.md](ai-asset-pipeline.md) | Krea budget and prices, image-to-3D rules, CPU auto-rigging (benchmarked), style consistency, 2D post-processing, Godot import presets | §0, §2.6, §3.3, §8 |
| [ip-safety.md](ip-safety.md) | Idea vs expression, key cases, banned names and lines, faction distinctness rubric, the "Vibecraft" name risk, checklists | §0, §2, §3.2, §5 |

## Key decisions & recommendations

### 1. Camera
- **Rig:** a ground focus `Node3D` with a child `Camera3D`. Perspective, never orthographic. Yaw locked (Insert/Delete may rotate temporarily).
- **Pitch −56°** (WC3 angle of attack 304°, from `Blizzard.j`). **Default distance 25.8 m** (1650 gu at 1 m = 64 gu).
- **Zoom 18.75–35.2 m** (1200–2250 gu; Reforged presets reach 2250). Optional pitch drift with zoom, at most 4°.
- **FOV 55° vertical** with `KEEP_HEIGHT`. WC3's 70 is most likely horizontal at 4:3, which is 55.4° vertical (unverified; tune between 50° and 55° against footage).
- `near` 0.3 m, `far` 80–120 m. Depth fog from 32 m to 90 m. The default view covers about 18×18 tiles, or about 14×18 above the HUD. Infantry must be at least 40 px tall at 1080p.
- **Feel:** smoothing `1 - exp(-12·dt)`; edge pan within about 8 px, at about 1.1·distance m/s, plus arrows and middle-drag.
  The camera moves in `_process` with no physics interpolation. Space jumps to the last alert, F1–F3 to heroes.
  The minimap draws the camera trapezoid, not a rectangle.

### 2. Art style direction: "Storm-lit Heroic Diorama"
- **Forms (WC3 rules):**
  - Chunky proportions, with identity in the upper third: helmet, shoulders, weapon head, roof.
  - 1–2 main colour masses per unit, plus team colour. Oversized weapons and shoulders.
  - Exaggerate concept art about 1.3×, because image-to-3D thins small parts.
- **Our twist:**
  - Drifting cloud shadows (strength 0.25–0.35) and wind sway on foliage.
  - A team-colour rim light on units, and runes that glow at night.
  - A spreading corruption biome (Blightmire).
  - "Toy-soldier" procedural motion that makes the lack of rigging a signature.
- **Painterly, never PBR:**
  - Light is painted into the albedo. One shared uber-shader: wrap-Lambert or a soft 2–3-band toon ramp, specular off, roughness 1, metallic 0.
  - Reforged's lesson: glossy armour made grouped units merge, and grey grading looked "hazy".
- **Hierarchy:**
  - Terrain is the quietest: value 30–65%, saturation ≤45%.
  - Units are the loudest: saturation ≤85%. Team colour ≥90%.
  - Only VFX goes above HDR 1.0, so only VFX blooms.
- **Lighting:** sun at 50–55° elevation, #FFF0D8; ambient #9DB3D6; key:ambient about 2:1–2.5:1; night moon #8EA6FF at 0.35–0.45.
  Tonemap Linear or Reinhard (not AgX or ACES), with a 3D LUT per biome. No SDFGI, VoxelGI or volumetric fog.
  **The look must hold on the Compatibility renderer.**
- **Terrain:**
  - WC3-style ordered tile ladder: cracked dirt, dirt, grassy dirt, grass, thick grass.
  - Crisp 16-case corner-mask blending, not soft splat maps (soft splats are the generic look).
  - Chunky noisy procedural cliffs and a low-frequency macro tint.
  - First biome: Greenvale. Palettes are in visual §7.2.
- **Scale and budgets** (2 m tile):

  | Class | Height | Tris |
  |---|---|---|
  | Worker | 1.2 m | 1.5–3k |
  | Infantry | 1.6–1.8 m | 2–4k |
  | Hero | 2.0–2.3 m | 4–8k |
  | Hall (8×8 m footprint) | 7–8 m | 6–12k |
  | Tree | 5–7 m | 0.5–1.5k |

- **HUD:**
  - Keep WC3's *structure*: minimap bottom-left, portrait and info centre, 4×3 command card bottom-right, top bar with resources and the day/night clock.
  - Make the frame thinner and translucent, with our own ornament.
- **Fog look:** unexplored #0A0C12. Explored areas at value ×0.55, saturation ×0.4, slightly blue.

### 3. Audio direction
- **Unit voices are the signature.** Categories: Ready, What, Yes, Attack, Warcry, Annoyed, plus Job done and Death.
  - Line counts: about 17–19 per unit, about 26 per hero, about 14 per advisor. That is about 310 lines for two factions.
  - Humour comes from character, never pop culture.
- **Acks** play in 2D, one at a time, with a 0.25 s debounce. Annoyed lines start after 4 clicks within 3 s and play in order.
- **World SFX:**
  - A pool of 24 `AudioStreamPlayer3D`s, with the listener at the camera focus +6 m. Cull beyond 50 m.
  - At most 4 instances per sound id, at least 60–100 ms apart, with priority stealing.
  - Melee = swing layer × material layer, a 5×5 matrix in about 30 files.
  - In big fights, play the 2–3 impacts nearest the screen centre, over a "battle bed" loop.
- **Music:**
  - 3 tracks per faction, 3–4 min each, shuffled, with 20–40 s of silence between. No battle-music switching.
  - Hearth Wardens: chamber folk (hurdy-gurdy, fiddle, horns, bells).
  - Thornborn: frame and log drums, bone flute, throat drone.
- **Ambience:** a day bed and a night bed per biome, crossfaded over about 8 s. Our own dusk and dawn stingers.
- **Buses:** Master, SFX, Voice, Music, Ambience, UI, plus Combat, Spells, World, Acks and Alerts. Music and Ambience compressors are side-chained to Voice and duck 4–6 dB.
- **Generation:**
  - Voices: ElevenLabs TTS through Krea (21 preset voices, `eleven_v4` tags, ffmpeg character chains).
  - SFX and creatures: Seed Audio, prompted "sound effect only, no music, no voice, no background".
  - Music: Music v2.5 with `force_instrumental: true`.
  - **Generate all VO before 31 Dec 2026**, when the default voices expire, and archive the raw takes.
  - Probe costs first: one 5-line TTS batch and one 30 s music clip.
- **Fallbacks:** CC0 only (Kenney, OpenGameArt CC0, Freesound CC0), never CC-BY-NC. Sonniss sounds never go into AI tools or a public repo.
- **Formats:** WAV (QOA) for SFX, Ogg Vorbis for VO, music and ambience.

### 4. Mechanics for the vertical slice (full table: mechanics §13)
- **Shape:** a 12–20 min 1v1 against a scripted AI (§13.7) on a 96×96-tile map (192 m). Two factions, each with 8 units and 2 heroes.
- **Start:** T1 hall, 5 workers, 500 gold / 150 lumber, clock at 08:00. The first dusk falls at 200 s.
- **Economy:**
  - 10 gold per trip, one worker inside a mine at a time for about 1 s, so about 5 workers saturate a mine.
  - Mine 12,000 gold (main) / 8,000 (expansion). Warn at 1,500 with a minimap ping.
  - Lumber 10 per trip (Faction A) or 15 (Faction B); 50 per tree.
- **Food cap 100. Upkeep:** 0–50 food keeps 100% of gold, 51–80 keeps 70%, 81–100 keeps 40%. It applies per gold delivery (rounded down), never to lumber.
- **Heroes:**
  - Hall tier gates hero count: T1 allows 1, T2 allows 2. The first hero is free (5 food) and comes with a Recall Scroll; later ones cost 425 g / 100 l and take 55 s.
  - XP to reach levels 2–10: 200/500/900/1400/2000/2700/3500/4400/5400. Cap 10.
  - 3 abilities × 3 ranks (learned at levels 1/3/5) plus an ultimate at level 6.
  - Creep XP: 80/70/60/50% at levels 1–4, **0% from level 5**.
  - Attributes: STR +25 HP, AGI +0.3 armour and +2% attack speed, INT +15 mana.
  - 6 item slots. Altar revive costs at most 550 g and takes at most 110 s.
- **Combat:**
  - The TFT attack × armour matrix under our own names (Blade, Pierce, Siege, Arcane, Heroic, Pure, Spell).
  - Armour reduction 0.06A/(1+0.06A).
  - Attacks have damage point, backswing and cooldown phases. Moving before the damage point cancels the swing.
  - HP is high relative to damage, so fights last 10–30 s and leave room to micro.
- **Creeps:**
  - Camp colour by total level: green 1–9, orange 10–19, red 20+.
  - Slice layout: 4 green, 2 orange, 1 red.
  - Creeps sleep at night and never respawn. Acquire range 3.9 m. Leash 18.75 m and bounty level×4+rand(0–5) are tuning guesses.
- **Day/night:** a 480 s cycle (240 s day, 240 s night). Sight in metres (day/night): units 21.9/12.5, heroes 28.1/12.5,
  workers 12.5/9.4. Sight changes over about 3 s.
- **Fog:** black mask, fog and visible states. Cliffs block upward sight, and trees block sight.
- **Controls:**
  - Smart right-click; attack-move, Stop, Hold and Patrol; shift-queue (≤32 orders).
  - 10 control groups, Tab subgroups, right-click autocast, rally points, F1–F3, idle-worker key.
  - **Selection cap 12**, matching the 12-slot multi-select grid (24 is a later option).
- **Neutrals:** a central Merchant and a Healing Fountain; about 12 items.
- **Construction:** each faction gets its own construction verb (e.g. scaffold-raised vs grown), shown with a ground-up `build_progress` shader reveal.

### 5. Tech architecture
- **Simulation:** 30 Hz fixed tick in `_physics_process` with physics interpolation on. Deterministic: a seeded sim RNG,
  iteration in id order, and a state-hash test that runs a scenario twice.
- **Entities:**
  - One node per unit (up to about 400 entities), with hot loops over typed and packed arrays.
  - A 2 m spatial hash. Target acquisition every 3–6 ticks, staggered. AI thinks every 0.5 s.
- **Pathing:**
  - `AStarGrid2D` on 0.5 m cells with custom separation steering. No NavigationServer, navmesh or RVO: navmesh rebakes cost 51–211 ms, and RVO ignores the navmesh.
  - JPS off. Connected-component labels so unreachable goals are never searched.
  - One path per group plus formation offsets. A coarse 2 m grid for paths over 30 m. About 6 ms of pathing per tick, plus string pulling.
- **Terrain:**
  - Per-corner data. Chunked `ArrayMesh` (16×16 tiles) built from packed arrays.
  - Marching-squares cliffs with noise. A corner-mask blend shader.
  - Trees as one `MultiMeshInstance3D` per type per chunk, with `custom_aabb` and vertex-shader sway.
- **Fog of war:**
  - A CPU grid at 1 m, updated incrementally at 4–10 Hz, uploaded as an RG8 `ImageTexture` (0.004 ms).
  - The shader lerps between the previous and current textures.
  - Enemies are hidden on the CPU. Fogged buildings leave ghosts.
- **Minimap:** a CPU-baked base image plus unit dots drawn in `_draw()`, with a fog shader. No second 3D camera, which costs about one full frame here.
- **Selection:**
  - Screen-space picking with no physics bodies.
  - Rings drawn in the terrain shader, or as flat ring quads in a MultiMesh. **Never `Decal`**, which Compatibility lacks.
  - Health bars as a constant-pixel 2D overlay.
- **HUD:**
  - One `CanvasLayer` plus a `Theme`.
  - A 4×3 `GridContainer` with QWER/ASDF/ZXCV hotkeys matched on `physical_keycode`.
  - Tooltip delay 0.2–0.3 s. A 128² portrait `SubViewport` set to `UPDATE_WHEN_VISIBLE`.
- **Renderer:** ship Forward+. Every gameplay-critical visual must also work on Compatibility.
- **Tests:**
  - The in-house `SceneTree` runner, with GUT 9.7.1 optional.
  - `Input.parse_input_event` for UI tests; verified headless.
  - Screenshots via `xvfb-run` with the Vulkan driver, plus `--fixed-fps 30 --audio-driver Dummy`. Clips via `--write-movie`.
  - The container renders at 2–3 FPS, so tune game feel from recorded clips or on a GPU.
- **Code reference:** `godot-open-rts` (MIT, Godot 4.3), for its structure only. It uses the navmesh/RVO approach we reject.

### 6. Asset pipeline (including rigging)
- **Budget:** 1,766.67 Krea CU.
  - Krea 2 Medium image: 9 CU.
  - Flagship 3D: 148–300 CU per model. Legacy 3D: Tripo 8 CU, TRELLIS v1 10 CU, Hunyuan3D-2.1 25 CU.
  - **Run the bake-off (pipeline §2.6) before spending on 3D.** Always submit 3D jobs async and log the job id first, because one paid result was lost to a timeout.
- **What gets AI 3D:** characters, heroes and signature buildings only. Trees, rocks, fences, props and modular building parts are procedural in bpy, with AI-made 2D textures.
- **2D consistency:**
  - Krea 2 Medium with 3–5 of our own style anchors as `image_style_references`.
  - A fixed prompt suffix, `creativity: "raw"`, and a fixed seed per asset family. Always pass seed and creativity explicitly.
  - Palette LUT and saturation clamp in post.
  - Train a Flux LoRA only if style drifts after about 50 assets. Krea 2 cannot be trained, which supersedes the visual doc's LoRA-first advice.
- **Concept image rules for image-to-3D:**
  - One object, A-pose, gaps between the legs and between arms and torso, weapon held clear or generated separately.
  - Light-grey background (#C8C8C8–#D8D8D8). Magenta (#FF00FF) appears only on team-colour cloth, never as the background.
  - Flat light, near-orthographic view, PBR off.
- **Mesh processing:**
  - `tools/process_model.py` with Blender Decimate, in two stages for large inputs. Never trimesh, which drops UVs.
  - Dilate UV islands before downscaling textures. Backface culling on.
  - Export GLB without Draco or meshopt; Godot 4.7.2 cannot read either.
- **Rigging (no paid service needed):**
  - bpy 5.2.2 at `/opt/bpyenv/v313`. One template skeleton per body type (biped about 15–25 deform bones), with joints fitted from mesh landmarks.
  - Voxel-remesh a proxy at about 0.8% of height, run bone heat on it, then Data Transfer the weights back and limit to 4 influences. Benchmarked: 0 unweighted vertices in about 1 s on AI "triangle soup", where direct bone heat left every vertex unweighted.
  - Shared procedural clips per body type: idle, walk, attack, death, work, cast, birth.
  - Fallbacks: runtime GDScript skinning, then rigid segments. Always layer procedural root motion on top (bob, lean,
    lunge, topple and sink). Buildings and doodads use vertex-shader animation.
  - Benchmark 300 skinned units on llvmpipe before skinning everything.
- **Godot import:** units get no import LODs and tangents off; buildings and doodads keep LODs. Extract textures:
  VRAM-compressed with mipmaps for 3D, lossless with no mipmaps for icons. CI runs `godot --headless --import`.
- **Ledger:** log every generation in `docs/asset-ledger.md` with the prompt, seed, job id, reviewer, the similarity check, and the human edits made afterwards.

### 7. IP red lines
- **Copy how WC3 plays, never how it looks, sounds or reads.** Mechanics and numbers are free (17 U.S.C. §102(b)). Art, audio, text, UI chrome, icons and maps are not. Redrawn look-alikes still lose: see *Tetris v. Xio* and *Spry Fox*.
- **No Blizzard names** in shipped content, filenames or prompts (list in ip-safety §2.1).
  - Add `tools/ip_banned_terms.txt` plus a CI grep.
  - Rename "footman" in the usage examples of the four `tools/*.py` scripts.
- **No WC3 voice lines or paraphrases** ("Job's done", "Work work", "Zug zug"). Check every script against the wiki quote pages.
- **Never touch WC3 data:** no MPQ/CASC extraction, World Editor, Hive Workshop rips or soundsets. Never use WC3 screenshots as AI inputs, references or moodboards.
- **Prompts** never contain brand, artist, composer or voice-actor names, negative prompts included. Describe qualities instead.
- **Factions** must pass the 6-axis distinctness rubric (at least 4 axes, plus silhouette in every case), with at most one WC3-derived signature mechanic each.
  No lion-on-blue humans, green tusked orcs, purple moon elves with walking trees, or ziggurat undead.
- **HUD:** the layout is free, the art is not. No gauntlet cursor, no copy of the day/night orb, licensed fonts only.
- **Maps** come from our own written brief. Never Lost Temple, Turtle Rock or similar.
- **Name:** "Vibecraft" is an internal codename only, because Blizzard sent Freecraft a C&D in 2003 over the name. The public title must avoid -craft, War-, Star- and -storm, and needs a trademark clearance search plus an attorney review.
- **Review:** every asset gets a side-by-side "squint test". Confirm that plan tiers allow commercial use (ElevenLabs free tier is non-commercial).

### 8. Changes needed in existing docs and code
- `architecture.md` §11: the camera says FOV 45° and 14–46 m (default 28 m). Change it to 55° vertical and 18.75–35.2 m (default 25.8 m).
- `architecture.md`: consider `CLIFF_H` 2.0 m instead of 1.75 m. 2.0 m matches WC3's 128 gu and makes cliffs read as cubes.
- `architecture.md` Fx: health bars are 3D MultiMesh billboards. Prefer the constant-pixel 2D overlay (the WC3 look). The rings are already Decal-free, and JPS is already off.
- **Faction names:** the art and audio docs use "Hearth Wardens" and "Thornborn"; mechanics §13 uses placeholders "Bastion" and "Wildborn". Adopt the art/audio names as working names: Faction A = Hearth Wardens, Faction B = Thornborn.
- `video-references.md` M17 suggests a 70° *vertical* FOV. That is superseded by §1 above.
- `docs/research/feel-metrics.csv` is referenced in video §G but does not exist yet.

## Open questions
1. **Higgsfield credits and 3D policy.** `docs/asset-ledger.md` (13:06) shows 269.75 Higgsfield credits. It quotes rig + 1 animation at 8 credits and image-to-3D at 9, and its policy says "Krea 3D is not used". The research brief assumed 0 Higgsfield credits and plans Krea 3D. Confirm the balance and reconcile before any 3D spend.
2. **3D bake-off:** are the legacy 8–10 CU models good enough for rank-and-file units after decimation to 2–4k tris? Which generator handles stylized inputs best?
3. **Unmeasured costs:** TTS per line, Music per 30 s, and whether multi-variant Seed Audio jobs split cleanly and cost the same.
4. **FOV axis:** is WC3's 70° horizontal or vertical? Settle it by matching footage at 1080p.
5. **Day/night:** a Liquipedia excerpt says "40 real seconds per hour", which contradicts the 480 s cycle. We use 480 s.
6. **Unverified WC3 values to tune by playtest:** XP-share radius (1200 gu), creep leash, bounty, lumber per tree, mine dwell time, damage point and backswing per class, annoyed-click threshold, edge-pan margin.
7. **Selection cap:** 12 (classic, matches the HUD grid) or 24 (reported for Reforged, unverified)?
8. **Performance:** skinning cost for 300 units on llvmpipe, and whether the stencil x-ray works on Compatibility.
9. **Faction distinctness:** Thornborn (bone, moss green, rust red, beast tribe, night regeneration, totems) risks reading as
   WC3 Orc plus Night Elf, and Hearth Wardens' slate-blue and brass sits near Alliance blue and gold. Slice hero kits need
   review too (Arc Bolt resembles Chain Lightning, Pack Call resembles summoned wolves). Run the rubric before concept art.
10. **Public title** and trademark clearance (USPTO, EUIPO, WIPO, stores).
11. **Terms:** which terms govern ElevenLabs output made through Krea, and which Krea plan tier was active per asset. Also check the current form of Steam's AI disclosure.
12. **Reliability:** do 2×2 icon and tile grids generate cleanly? Does the corner-mask transition atlas look painterly enough?
13. **Missing reference:** find a working first-person-view pro game video for HUD study (both search hits were dead).

## Sources
- [Blizzard.j melee and camera constants (lep/jassdoc)](https://raw.githubusercontent.com/lep/jassdoc/master/Blizzard.j)
- [classic.battle.net: Upkeep](https://classic.battle.net/war3/basics/upkeep.shtml) · [Heroes](https://classic.battle.net/war3/basics/heroes.shtml) · [Day/Night](https://classic.battle.net/war3/basics/daynight.shtml) · [Armor and Weapon Types](https://classic.battle.net/war3/basics/armorandweapontypes.shtml) · [Melee map guidelines](https://classic.battle.net/mod/dev/melee.shtml)
- [Liquipedia: Daytime](https://liquipedia.net/warcraft/Daytime) · [Hive Workshop: Vision guide](https://www.hiveworkshop.com/threads/vision-guide.290769/) · [HiveWE: war3map.w3e terrain](https://github.com/stijnherfst/HiveWE/wiki/war3map.w3e-Terrain)
- [Game Informer: WC3 concept art gallery (Didier on top-down readability)](https://www.gameinformer.com/index.php/2018/11/14/explore-warcraft-iiis-origins-in-this-rare-concept-art-gallery) · [Blizzard: Inside Warcraft Rumble – Creating a Mini](https://news.blizzard.com/en-gb/article/23899627/inside-warcraft-rumble-creating-a-mini)
- [Blizzard: Reforged patch 1.35.0 (zoom levels)](https://news.blizzard.com/en-gb/article/23896791/warcraft-iii-reforged-patch-1-35-0-now-live)
- [Warcraft Wiki: Quotes of WC3 / Human Alliance](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance) · [jassbot: CreateSound limits](https://lep.duckdns.org/jassbot/doc/CreateSound) · [Hive: custom music lists (20–40 s gaps)](https://www.hiveworkshop.com/threads/custom-music-lists.294961)
- [Krea API: ElevenLabs TTS](https://www.krea.ai/docs/api-reference/audio/elevenlabs-tts.md) · [Krea API: Seed Audio 1.0](https://www.krea.ai/docs/api-reference/audio/seed-audio-10) · [ElevenLabs: default voices expire 31 Dec 2026](https://elevenlabs.io/docs/it/help-center/product/voices/my-voices/what-are-default-voices.md)
- [Krea 3D generation (legacy model CU)](https://www.krea.ai/docs/3-d.md) · [Krea OpenAPI pricing](https://api.krea.ai/openapi.json) · [Blender manual: Remesh](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html)
- [Godot: Overview of renderers](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html) · [AStarGrid2D](https://docs.godotengine.org/en/stable/classes/class_astargrid2d.html) · [Using NavigationAgents](https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_using_navigationagents.html) · [Decal](https://docs.godotengine.org/en/stable/classes/class_decal.html)
- [lampe-games/godot-open-rts (MIT)](https://github.com/lampe-games/godot-open-rts)
- [17 U.S.C. §102 (Cornell LII)](https://www.law.cornell.edu/uscode/text/17/102) · [Tetris Holding v. Xio](https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc.) · [Spry Fox v. Lolapps](https://en.wikipedia.org/wiki/Spry_Fox,_LLC_v._Lolapps,_Inc.) · [Stratagus (Freecraft C&D)](https://en.wikipedia.org/wiki/Stratagus) · [US Copyright Office AI Part 2](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)
