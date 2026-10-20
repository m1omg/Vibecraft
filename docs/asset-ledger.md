# Asset generation ledger

Budget policy (agreed with the user):
- **Balance both services; neither is limited to one asset type.**
- **Higgsfield** credits are prioritised for what only Higgsfield can do — **3D models, auto-rigging
  and animation clips** — but its cheap images (gpt_image_2_5, 0.25 cr) are also used for terrain
  textures and for character/building reference art that feeds image-to-3D.
- **Krea** compute units cover concept art, icons, UI art and other 2D work, plus **all audio**
  (SFX via Seed Audio, voices via ElevenLabs TTS, music via ElevenLabs Music).
- Krea 3D is not used: measured 148–167 CU per model and the meshes are ~50k faces.
- 3D jobs are always submitted **async** so a tool timeout can never lose a paid result.
- Keep a reserve on both services for fixes/retries.

## Measured unit costs

| Service | Model | Cost |
|---|---|---|
| Krea | Krea 2 Medium image (1K) | 9 CU |
| Krea | Seed Audio 1.0 SFX (~2.5 s) | 4.63 CU |
| Krea | Tripo H3.1 text-to-3D (textured) | 148.15 CU |
| Krea | Hunyuan3D 3.1 Rapid text-to-3D | 166.67 CU (failed attempt: not charged) |
| Higgsfield | gpt_image_2_5 image | 0.25 cr |
| Higgsfield | tripo_h3_1_image_to_3d | 9 cr (verified) |
| Higgsfield | hunyuan3d_v3_image_to_3d LowPoly | 14 cr (quoted) |
| Higgsfield | image_to_3d (Meshy) textured | 30 cr (quoted) |
| Higgsfield | image_to_3d textured + rig + 1 animation | 38 cr (quoted) |
| Higgsfield | 3d_rigging + 1 animation (existing GLB) | 8 cr (verified) |
| Krea | TRELLIS v1 image-to-3D | 14.81 CU (verified) |
| Krea | Tripo legacy image-to-3D | 222.22 CU (verified — banned) |
| Krea | ElevenLabs TTS (eleven_v4) | 2/27 CU ≈ 0.074 CU per prompt character, tags and spaces included (verified 2026-10-20) |
| Krea | Seed Audio 1.0 | ≈ 1.83 CU per second of OUTPUT; the model picks the length (4–9.5 s per job) (verified 2026-10-20) |
| Krea | ElevenLabs Music v2.5 | ≈ 444 CU for a 10 s request (verified 2026-10-20 — **banned**; preflight returns no quote) |

## Spend log

| # | Date | Service | What | Cost | Result |
|---|---|---|---|---|---|
| 1 | 2026-10-16 | Krea | Grass texture probe (Krea 2 Medium) | 9 CU | OK, usable |
| 2 | 2026-10-16 | Krea | Pine tree text-to-3D probe (Tripo H3.1) | 148.15 CU | Charged, but the MCP call timed out (sync mode) and the job id was lost — result not retrievable via API |
| 3 | 2026-10-16 | Krea | Boulder text-to-3D probe (Hunyuan 3.1 Rapid) | 0 | Provider 504, not charged |
| 4 | 2026-10-16 | Krea | Boulder text-to-3D probe (Hunyuan 3.1 Rapid, retry) | 166.67 CU | OK, 50k faces / 4K texture |
| 5 | 2026-10-16 | Krea | Sword-on-shield SFX probe (Seed Audio) | 4.63 CU | OK |
| 6 | 2026-10-16 | Higgsfield | Dirt texture (gpt_image_2_5) | 0.25 cr | OK, very good |
| 7 | 2026-10-16 | Higgsfield | Kingdom infantry concept, A-pose, for 3D bake-off (gpt_image_2_5, job 8f55e5cc-2a91-46c7-acef-f88a2e70b4b2) | 0.25 cr | OK, very good |
| 8 | 2026-10-16 | Krea | Bake-off: infantry image-to-3D, Tripo legacy `tripo/tripo` seed 1101 (job 4103e829-0adf-44ff-ba8a-6dc7e99845a5) | **222.22 CU** | OK quality (≈ H3.1), 482k tris, faces +X. **Not 8 CU as the research doc assumed — never use Krea Tripo again** |
| 9 | 2026-10-16 | Krea | Bake-off: infantry image-to-3D, TRELLIS v1 `microsoft/trellis` seed 1101 tex 1024 (job e500c6b3-e5a5-4ad3-9af3-68e379dea1c4) | 14.81 CU | Usable front, sides/back textured nearly black. OK for static buildings/props seen from the front |
| 10 | 2026-10-16 | Higgsfield | Bake-off: infantry image-to-3D, `tripo_h3_1_image_to_3d` face_limit 12000 (job 06a02b40-1355-4bea-aaf7-085d56a461b5) | 9 cr | **Winner**: 11.4k tris, painted all round, faces +X (`--facing +x`), great at 4k tris |
| 11 | 2026-10-16 | Higgsfield | Rig soldier (H3.1 GLB re-oriented to +Z, uploaded to Krea assets) + walk clip 30 `3d_rigging` (job 1258c48a-04ea-4948-8f7b-037074b9973c) | 8 cr | OK: 24-bone humanoid (Hips/Spine/Left*/Right*), clip Casual_Walk 4.13 s, 100% weighted. Contains a stray "Icosphere" helper mesh — strip it |
| 12 | 2026-10-16 | Higgsfield | Library clip on soldier rig: Idle (0) (job c6373721-4964-41ac-ae52-129cbc2abf4c) | 8 cr | OK (in place, 4.0 s); body yaw drifts off the unit facing — normalise clip yaw |
| 13 | 2026-10-16 | Higgsfield | Library clip on soldier rig: Right_Hand_Sword_Slash (219) (job f4f33f9d-cdb4-44af-9fd5-5b486f74f2f8) | 8 cr | OK (1.5 s, in place) |
| 14 | 2026-10-16 | Higgsfield | Library clip on soldier rig: Dead (8) (job acc356bf-34e1-4499-a9f5-5972b476c8bc) | 8 cr | OK (2.97 s) |

| 15 | 2026-10-16 | Higgsfield | Greenvale terrain + materials, 13 × gpt_image_2_5 (art bible T5–T8): gv_scree 8c9ef1ec, gv_cracked 9016da95, gv_grassy_dirt 48002468, water_ripples ce8b2084, gv_dirt 6e219d05, gv_road 49908061, gv_meadow 224a7af7, gv_thick_meadow a2db424c, cliff_limestone 769d321f, cliff_earthbank ab177c7f, foliage_oak_cards 8782d25e, foliage_linden_cards 8cc6aba2, bark_oak 9494d147 | 3.25 cr | All approved. Made seamless with `texture_tools.py seamless` (seam scores 2–3.9 → 0.72–0.91). Foliage keyed from #0000FF. 8 first-attempt submissions were rate-limited (429) and never created — not charged |

| 16 | 2026-10-16 | Higgsfield | Library clip on soldier rig: mage_soell_cast (129) for casters (job cd75b0a3-1cc6-4f62-9b74-cfaa038a749e) | 8 cr | OK → assets_src/characters/kingdom_infantry/rig_cast.glb |
| 17 | 2026-10-16 | Higgsfield | Library clip on soldier rig: Heavy_Hammer_Swing (128) for brutes + worker chop/build (job daee7371-22ee-4511-a306-c3d1efbc4290) | 8 cr | OK → rig_heavy_swing.glb |
| 18 | 2026-10-16 | Higgsfield | Library clip on soldier rig: Over_Shoulder_Throw (421) for javelins (job 2d5a1bae-ec34-41c1-b466-5584dc31ccbf) | 8 cr | OK → rig_throw.glb |

| 19 | 2026-10-17 | Higgsfield | Slice character concepts, 11 × gpt_image_2_5 (art bible T1/T2, front view): kingdom_hodman 14cde04c, kingdom_hookgunner cf3c4b37, kingdom_linden_sister 7469fa91, kingdom_wheel_marshal cc855464, kingdom_firewright b0e02346, clans_yurtwright 470c4f54, clans_grappler 640c3376, clans_javelineer 4fa0b77c, clans_gustcaller d56c881c, clans_hero_uncut 14b57291, clans_skymirror c36b23f0 | 2.75 cr | All approved (assets_src/characters/*/concept.png) |
| 20 | 2026-10-17 | Higgsfield | Slice character image-to-3D, 11 × tripo_h3_1_image_to_3d face_limit 12000: hodman ff290282, hookgunner 3bed1f66, linden_sister bfe46a5c, wheel_marshal 9087ca80, firewright 10cc020f, yurtwright f9a84f73, grappler 39864df3, javelineer 7f069bd3, gustcaller 2158bceb, uncut 3328ec7b, skymirror 0cf13a61 | 99 cr | All 11 completed → assets_src/characters/*/model_tripo_h31.glb (raw, faces +X) |

| 21 | 2026-10-17 | Higgsfield | Building material swatches, 14 × gpt_image_2_5 (art bible T5): kingdom_lime_plaster b7cbfa5d, kingdom_dark_oak_beam 9ec18388, kingdom_burgundy_roof_tiles a9f7ac6a, kingdom_rubble_stone 08219f3f, kingdom_bronze_scale_roof b3a38686, kingdom_painted_planks efb26111, clans_teal_felt b9096ece, clans_saffron_felt 1bb763bb, clans_lattice_wood bc780062, clans_tortoise_shell 0ece60ab, clans_polished_bronze 4d2fdda8, neutral_gold_vein_rock 581b9e83, neutral_drystone c1b90119, neutral_mine_timber eb052838 | 3.5 cr | All approved (assets_src/textures/materials). 2 first-attempt submissions rate-limited, not created |
| 22 | 2026-10-17 | Higgsfield | Hall concepts, 2 × gpt_image_2_5 (art bible T4): kingdom_moot_hall f5ea16a8, clans_shell_hall 5b28e08f | 0.5 cr | Approved |
| 23 | 2026-10-17 | Krea | Hall image-to-3D, 2 × TRELLIS v1 tex 2048: moot hall f94c3854-3da3-4dc1-9111-e18142779ce2 (seed 1180), shell hall af8d88a7-0e47-466e-a7c1-259003f3973b (seed 1280) | 29.63 CU | Fronts good, sides/back black → rejected for buildings (kept in assets_src/buildings/*/model_trellis.glb). TRELLIS only for small one-sided props from now on |

| 24 | 2026-10-17 | Higgsfield | Hall image-to-3D redo, 2 × tripo_h3_1_image_to_3d face_limit 20000: moot hall 30c30deb-665f-44b3-99d0-0d7a97a0f8fb, shell hall 18634ede-cb91-4aa3-a6ef-6b58c290c8cb | 18 cr | Approved: textured all round; moot hall needs --yaw 90 (door to camera) → assets/models/buildings/ |

**Bake-off conclusion (2026-10-16):** characters and anything that turns → Higgsfield Tripo H3.1 (9 cr) + Higgsfield
rigging (8 cr). Static buildings/props → Krea TRELLIS v1 (~15 CU) is acceptable when the back is never seen; otherwise
Higgsfield Tripo H3.1. All other Krea 3D models cost 148–222 CU each — banned.

**Balances after log:** Krea 1529.63 CU · Higgsfield 225.25 cr (verified 2026-10-16 16:49)

## 2026-10-20 audio pass (branch audio/p0)

Krea 1419.61 CU before → **719.98 CU after** (verified with get_balance). Spent ≈ 699.6 CU: SFX ≈ 162 CU (15 Seed Audio jobs), voice ≈ 93 CU (20 TTS jobs, 5 speakers), music **≈ 444 CU for one 10 s probe** (ElevenLabs Music v2.5 — far above the 130 CU cap the agent was given, because the price was unknown and preflight returned no quote). **Music through Krea is banned from now on**; music will come from CC0/procedural sources or a cheaper service. The voice agent was stopped by a usage limit after tier a for the hodman, yurtwright, pavisier, grappler and hookgunner (the rest of the cast is scripted in docs/design/voice-lines.md, not yet generated). Generic SFX also use Kenney CC0 packs (assets/audio/CREDITS.md).

Higgsfield: 77.35 cr (verified 2026-10-20).

### audio-sfx (SFX and music, branch audio/p0)

All rows dated 2026-10-20, Krea workspace (Individual Basic plan). Caps for this agent: 170 CU SFX + 130 CU music.
Full prompts for every job are in `tools/audio/sfx_jobs.json` and `tools/audio/music_jobs.json` (wrapper + clause, built by
`tools/audio/sfx_prompts.py`). Costs are the preflight quote, cross-checked against `get_balance` where noted.

Balance at start: 1419.61 CU (2026-10-20, before any job of this agent).

| Service | What | Job id | Cost | Result |
|---|---|---|---|---|
| Krea Seed Audio 1.0 | PROBE `hit_metal_l` (O, 4 × 0.5 s) | bfdff9a3-5a6f-4025-bab3-c3ff3052ff9a | 9.26 CU (balance 1419.61 → 1410.35; preflight gives no quote) | OK: 5.07 s output, 3 clean takes (asked for 4), ~1.3 s gaps; kept 3 |
| Krea Seed Audio 1.0 | `hit_metal_h` (O, 4 × 0.6 s) | a11b57c3-ebdc-4afb-b43d-89bfa3b6be31 | 10.00 CU (balance 1410.35 → 1400.35) | OK: 5.46 s output, 3 takes (asked for 4); kept 3. **Pricing: Seed Audio bills per second of output, ≈ 1.83–1.84 CU/s** (9.26 CU for 5.07 s, 10.00 CU for 5.46 s; the old 4.63 CU was a ≈ 2.5 s clip) |
| Krea Seed Audio 1.0 | `sw_slash` (O, 6 × 0.3 s) | cd1d3289-78ce-44ed-936f-9a764d02d060 | 9.82 CU (pair delta 21.07 CU, 1400.35 → 1379.28, split by output length 5.36 s / 6.14 s) | OK: 4 takes (asked for 6), kept 4 |
| Krea Seed Audio 1.0 | `sw_blunt` (O, 6 × 0.35 s) | e24545e2-8a68-4a7f-9c6f-19795fb99236 | 11.26 CU (see the row above) | OK: 4 takes (asked for 6), low noise floor between takes, kept 4 |
| Krea Seed Audio 1.0 | `hit_flesh_l` (O, 4 × 0.4 s) | fe53254d-c99d-46e7-8162-18ab2ca0ead4 | 7.57 CU (pair delta 16.82 CU, 1379.28 → 1362.46, split by length 4.15 s / 5.07 s) | OK: 4 takes, kept 4 |
| Krea Seed Audio 1.0 | `hit_flesh_h` (O, 4 × 0.5 s) | 6a0b8a42-ce34-4a0d-962a-b3ebdd9ab7dc | 9.24 CU (see the row above) | OK: 3 takes (asked for 4), noisy low bed between takes; kept 3, cut to 0.85 s with a 120 ms fade |
| Krea Seed Audio 1.0 | `hit_wood_l` (O, 4 × 0.4 s) | 3942d6cf-fcad-42fc-9dd2-0d88aaa3333b | 8.51 CU (pair delta 22.37 CU, 1362.46 → 1340.09, split by length 4.65 s / 7.58 s) | OK: 3 takes (asked for 4), kept 3 (take 3 is short, 0.25 s, cut by the end of the file) |
| Krea Seed Audio 1.0 | `vox_death_kingdom` (V, 6 sounds) | 72a3b395-a367-44c9-99be-7af7dbbc4f05 | 13.86 CU (see the row above) | WEAK: 7.6 s, only one loud event (an "oof" into a cut-off cry, SNR 38 dB), the rest quiet breaths at SNR 13–22 dB. Kept 3 (the cry, a moan, an exhale); rejected 2 near-silent breaths. No words visible in the spectrogram (not verified by ear) |
| Krea Seed Audio 1.0 | `hookgun_fire` (O, 4 × 1.6 s) | c693eb25-74e0-42ed-98b1-e923e7e85d18 | 17.37 CU (pair delta 42.07 CU, 1340.09 → 1298.02, minus the audio-vo probe 8.96 CU = 33.11 CU, split by length 9.46 s / 8.57 s) | OK: 4 shots with long smoke tails; kept 4, cut to ≤ 1.8 s with a 250 ms fade |
| Krea Seed Audio 1.0 | `bombard_fire` (O, 3 × 2.0 s) | 87cce160-e4d4-46f0-aa22-bb7c67a64c1b | 15.74 CU (see the row above) | OK: 3 booms (take 3 cut short by the end of the file, kept as a 1.0 s variant with a 300 ms fade); kept 3 |
| Krea Seed Audio 1.0 | `javelin_throw` (O, 4 × 0.5 s) | 703958d8-bc5d-4bfa-9c20-fff22521976c | 8.37 CU (pair delta 21.30 CU, 1298.02 → 1276.72, split by length 4.57 s / 7.05 s) | OK: 3 takes (asked for 4), kept 3 |
| Krea Seed Audio 1.0 | `bombard_hit` (O, 4 × 1.0 s) | 68fe935c-021e-4da1-8738-916732a25fb5 | 12.92 CU (see the row above) | OK: 5 impacts, two pairs overlapping (split by hand at 1.19 s and 5.47 s); kept 5, ≤ 1.3 s, 150 ms fade |
| Krea Seed Audio 1.0 | `slingcart_throw` (O, 3 × 1.2 s) | 331290c8-95da-4b26-8c84-5ed13ca58e4e | 11.26 CU (balance 1276.72 → 1265.46; 6.14 s) | OK: 3 takes (creak, arm whip, thump), kept 3 |
| Krea Seed Audio 1.0 | `gust_bolt` (O, 4 × 0.6 s) | d0698ba7-6fc2-4526-86ca-7a6725d6b4ab | 9.07 CU (balance 1265.46 → 1256.39; 4.96 s) | USABLE: 3 soft dusty swishes (asked for 4), generated very quiet (peak −35 dBFS) and falling rather than rising in pitch, no clear impact puff; kept 3, normalised (+34 dB). Candidate for a re-roll |
| Krea Seed Audio 1.0 | `atk_herb_mote` (O, 4 × 0.3 s) | 9ca5758a-b2c0-4537-a379-cbc7d934853a | 7.74 CU (4.26 s at the measured ≈ 1.833 CU/s; it ran together with the music probe, see the next row) | OK: 3 soft leafy thuds (asked for 4), kept 3 |
| Krea ElevenLabs Music v2.5 | PROBE music: Opening cue, kingdom (10 000 ms, force_instrumental) | 17222d0d-0ed8-41af-91ce-99ebcdb923a4 | **≈ 444.44 CU** (balance 1256.39 → 804.21 = 452.18 CU for this job and `atk_herb_mote`; no other job was logged by either audio agent in that window; preflight had returned no quote) | OK musically (bell strike, rising figure, held chord; 10.03 s, 48 kHz stereo) → `assets/audio/music/opening_kingdom.ogg` (2.4 s, 300 ms fade, −16 LUFS). **STOP: ElevenLabs Music v2.5 through Krea costs ≈ 44 CU per second of music (or a flat ≈ 444 CU per job). All further music was cancelled** |

**Totals for this agent (2026-10-20):** SFX 161.99 CU (15 Seed Audio jobs; cap 170) + music 444.44 CU (1 probe; cap 130) =
**≈ 606.44 CU, over the 300 CU agent cap by ≈ 306 CU because of the single music probe**. Balance after the last job: 804.21 CU.
No paid job was submitted after the music charge was seen.

**Measured prices (2026-10-20):**
- Seed Audio 1.0: billed per second of OUTPUT, ≈ 1.83–1.84 CU/s (9 jobs measured alone or in pairs: 9.26 CU / 5.07 s, 10.00 / 5.46,
  9.07 / 4.96, 11.26 / 6.14 ...). The model picks the length itself (4.1–9.5 s here) and ignores "about half a second of silence"
  (gaps were 0.6–1.6 s) and usually returns one take fewer than asked. Effective cost ≈ 2.5–3.5 CU per usable take.
- ElevenLabs Music v2.5: ≈ 444.44 CU (= 12 000/27) for a 10 s request with `music_length_ms` 10 000. Preflight returns
  `compute_units: null`. At that rate a 210 s track would cost thousands of CU; the bible §11 music plan is unaffordable on Krea.

**Free sources used instead of paid jobs** (see `assets/audio/CREDITS.md`): Kenney CC0 packs "Impact Sounds" and "RPG Audio"
(downloaded 2026-10-20 from kenney.nl, licence files in `assets_src/audio/cc0/kenney/`), procedural layers, and variants derived from
our own generated takes. Recipes: `tools/audio/gen_layered_recipes.py` → `layered_recipes.json` → `build_layered_sfx.py`.

### audio-vo (unit and hero voices, advisors; branch audio/p0)

All rows dated 2026-10-20, Krea workspace (Individual Basic plan), service `elevenlabs/tts` with `model_id: eleven_v4`.
Hard cap for this agent: **300 CU**. Pricing measured with free preflights on 2026-10-20: **exactly 2/27 CU (0.0741) per
prompt character**, newlines, spaces and bracket tags included, no per-job base fee (20 chars = 1.4815 CU, 30 = 2.2222, 59 = 4.3704).
The Krea balance is shared with the audio-sfx agent, so costs below are the exact per-character quote of each prompt; the balance
deltas are cross-checks only. Full prompts for every job: `tools/prompts/vo/vo_jobs.json`. Scripts: `docs/design/voice-lines.md`.

Balance at start: 1419.61 CU (2026-10-20, before any job of this agent).

| Service | What | Job id | Cost | Result |
|---|---|---|---|---|
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier probe: hodman what (what_01, what_02, what_03, what_04; voice N2lVS1w4EtoT3dr4eOWO; 121 chars); PROBE: separators [long pause] / [pause] / blank line; 121 chars | 10192392-602c-4eb3-817d-d2a712c8db67 | 8.96 CU | split 4/4 correct (ASR-checked); what_01 1.39 s, what_03 1.38 s, what_04 1.11 s shipped; what_02 "Thirty years. One Agnes." 2.4 s REJECTED (over 1.4 s at atempo 1.15) |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman ready (ready_01; voice N2lVS1w4EtoT3dr4eOWO; 46 chars) | d6370497-b848-4e5a-a331-4d2a6e91c154 | 3.41 CU | ready_01: ok 3.27s atempo 1.073 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman yes (yes_01, yes_02, yes_03; voice N2lVS1w4EtoT3dr4eOWO; 63 chars) | b168f192-e1ea-41bc-bdf8-6b2944db9788 | 4.67 CU | yes_01: ok 1.17s; yes_02: ok 1.388s atempo 1.08; yes_03: ok 1.376s atempo 1.095 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman attack (attack_01, attack_02; voice N2lVS1w4EtoT3dr4eOWO; 55 chars) | 0331ca24-9cc0-49bf-97e0-cae7bbb518e0 | 4.07 CU | attack_01: ok 1.44s; attack_02: ok 1.46s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright ready (ready_01; voice pqHfZKP75CvOlQylNhV4; 49 chars) | 1e67798d-77b7-42d5-bfb6-65b0cd369094 | 3.63 CU | ready_01: ok 3.25s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright what (what_01, what_02, what_03; voice pqHfZKP75CvOlQylNhV4; 66 chars) | f4c8da98-261d-4b63-9e7d-415421fe35a6 | 4.89 CU | what_01: ok 1.08s; what_02: ok 1.06s; what_03: ok 1.27s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright yes (yes_01, yes_02, yes_03; voice pqHfZKP75CvOlQylNhV4; 55 chars) | ad890167-5fa9-4bb5-9894-939146e0b62c | 4.07 CU | yes_01: ok 0.74s; yes_02: ok 1.15s; yes_03: ok 0.86s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright attack (attack_01, attack_02; voice pqHfZKP75CvOlQylNhV4; 58 chars) | 6a490962-db4f-4f15-b7d9-598ef845a1ca | 4.30 CU | attack_01: ok 1.42s; attack_02: REJECTED 2.003s atempo 1.15 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier ready (ready_01; voice TX3LPaxmHKxFdv7VOQHJ; 50 chars) | 74175336-c9ca-483b-9f22-7cde578e9b79 | 3.70 CU | ready_01: ok 2.72s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier what (what_01, what_02, what_04; voice TX3LPaxmHKxFdv7VOQHJ; 65 chars) | 102d1a07-d580-41f8-816c-f32b6bd96fbd | 4.81 CU | what_01: ok 0.75s; what_02: ok 1.17s; what_04: ok 0.86s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier yes (yes_01, yes_02, yes_04; voice TX3LPaxmHKxFdv7VOQHJ; 69 chars) | a479d3ac-7474-4b0c-81c7-fd9e3b90de9f | 5.11 CU | yes_01: ok 1.389s atempo 1.095; yes_02: ok 1.15s; yes_04: ok 0.72s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier attack (attack_01, attack_02; voice TX3LPaxmHKxFdv7VOQHJ; 52 chars) | e6d66f57-8dfb-4169-a8fb-7e98f51fbcee | 3.85 CU | attack_01: ok 1.58s atempo 1.11; attack_02: ok 0.91s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: grappler ready (ready_01; voice pNInz6obpgDQGcFmaJgB; 34 chars) | da473175-ec6f-4134-8d22-dd8b20c9416d | 2.52 CU | ready_01: ok 2.24s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: grappler what (what_01, what_02, what_03; voice pNInz6obpgDQGcFmaJgB; 86 chars) | 4aa0d813-0d02-4b4d-b5a7-2854fab67ad4 | 6.37 CU | re-split at speech-recognition cuts 1.44,3.83: what_01: ok 1.3s; what_02: REJECTED 1.813s atempo 1.15; what_03: ok 1.3s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: grappler yes (yes_01, yes_02, yes_03; voice pNInz6obpgDQGcFmaJgB; 58 chars) | 76e796e2-a1c6-4b0c-abbd-0ea5698dd014 | 4.30 CU | re-split at speech-recognition cuts 2.04,3.87: yes_01: ok 1.31s; yes_02: ok 1.396s atempo 1.066; yes_03: ok 0.89s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: grappler attack (attack_01, attack_02; voice pNInz6obpgDQGcFmaJgB; 49 chars) | f14ef8b2-d364-4e20-8266-1e7fbacb7b87 | 3.63 CU | attack_01: ok 1.584s atempo 1.11; attack_02: ok 1.01s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hookgunner ready (ready_01; voice SOYHLrjzK2X1ezoPC6cr; 50 chars) | 9a87de51-79ee-40a9-a51f-9b4f28f09e1d | 3.70 CU | ready_01: ok 2.94s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hookgunner what (what_01, what_02, what_03; voice SOYHLrjzK2X1ezoPC6cr; 67 chars) | e447b161-e28f-4d5a-af40-493e41d1c864 | 4.96 CU | what_01: ok 0.84s; what_02: ok 1.391s atempo 1.124; what_03: ok 1.16s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hookgunner yes (yes_01, yes_02, yes_03; voice SOYHLrjzK2X1ezoPC6cr; 69 chars) | b885f560-47e8-42cf-96f0-c4d1280c9270 | 5.11 CU | SUSPECT SPLIT (line lengths do not follow the text; run vo_asr_split.py): yes_01: ok 0.9s; yes_02: REJECTED 1.74s atempo 1.15; yes_03: ok 1.2s |
