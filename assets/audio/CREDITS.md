# Audio credits

## Third-party (CC0)

| Pack | Author | Licence | Source | Downloaded |
|---|---|---|---|---|
| Impact Sounds 1.0 | Kenney (www.kenney.nl) | CC0 1.0 (public domain dedication), licence text in `assets_src/audio/cc0/kenney/impact-sounds/License.txt` | https://kenney.nl/assets/impact-sounds (zip sha256 029d734af1582474edf3a694d1b0cebc97c1c152f2f39fa34d4c2bafc5de77f8) | 2026-10-20 |
| RPG Audio 1.0 | Kenney (www.kenney.nl) | CC0 1.0, licence text in `assets_src/audio/cc0/kenney/rpg-audio/License.txt` | https://kenney.nl/assets/rpg-audio (zip sha256 6dbeaf8544da958d8f2adcb4a4a4b76c1ade34a05f8ab9edccd327da7375f38b) | 2026-10-20 |

Credit is not required by CC0; we credit Kenney anyway. The source files actually used are kept in `assets_src/audio/cc0/kenney/`.
No stock sound is used for a signature cue (bible §11 decision 2: level-up, alarms, Levy Horn, gong call, recall channels, revives,
reveal cues, building select sounds); the CC0 layers cover body falls and UI clicks and ticks only, plus layers inside derived
placeholders.

## Third-party (MIT): the soundfont that renders the composed music

| Asset | Author | Licence | Source | Use |
|---|---|---|---|---|
| FluidR3_GM.sf2 (Fluid R3 General MIDI SoundFont) | Frank Wen, with the contributors listed in its README; Copyright © 2000-2002, 2008 Frank Wen, © 2008 Toby Smithe | MIT ("I hereby release Fluid under the MIT license", upstream README, quoted in the Debian/Ubuntu package's copyright file) | Ubuntu package `fluid-soundfont-gm` 3.1, `/usr/share/sounds/sf2/FluidR3_GM.sf2` (sha256 74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0) | The sampled instruments (fiddles, viola, cello, contrabass, dulcimer, plucked lutes, bagpipe, shanai, horns, timpani, percussion) of the composed music, rendered offline by FluidSynth 2.3 (LGPL, a tool only). The soundfont itself is not shipped |

## Generated (ours)

All other SFX are generated with Krea `bytedance/seed-audio-1.0` (prompts: `tools/audio/sfx_jobs.json` via
`tools/audio/sfx_prompts.py`, job ids in `docs/ledger-pending/audio-sfx.md`), then split, trimmed, faded and normalised by
`tools/audio/split_takes.py`. Music: **composed by the project** in Python with `tools/music` (13 pieces: Kingdom 1-3, Clans 1-3, the menu theme,
the end-screen bed, both victory and both defeat stingers and the clans opening cue). Each piece is a source file in
`tools/music/pieces/` that regenerates its MIDI and stems byte for byte from a fixed seed; the instruments are the
FluidR3_GM soundfont above plus numpy synths of our own (gongs, hurdy-gurdy, jaw harp, overtone chant, frame drums,
claps). Melodies are built from our own motifs (bible §10.2). The list, sources and hashes are in
`assets/audio/music/manifest.json`. The one exception is the kingdom opening cue (`opening_kingdom.ogg`), generated
with Krea `elevenlabs/music-v2.5` (prompt verbatim from the art-and-audio bible §10.3, `tools/audio/music_jobs.json`)
and post-processed by `tools/audio/post_music.py`; paid music generation is banned since that probe.

## Layered, procedural and derived files

Built by `tools/audio/build_layered_sfx.py` from `tools/audio/layered_recipes.json` (written by `gen_layered_recipes.py`).
`cc0` = CC0 layers (plus small procedural layers); `procedural` = synthesised in numpy; `derived` = re-pitched, cropped or layered
from our own generated takes (sometimes with CC0 layers). The derived `sw_pierce` and `vox_death_clans` are placeholders until their
own Seed Audio jobs are run.

| Id | Group | Kind | Sources |
|---|---|---|---|
| `fall_light` | combat | cc0 | Kenney CC0: `impact-sounds/impactPunch_medium_000.ogg`, `impact-sounds/impactPunch_medium_001.ogg`, `impact-sounds/impactPunch_medium_004.ogg`, `impact-sounds/impactSoft_heavy_000.ogg`, `impact-sounds/impactSoft_heavy_001.ogg`, `impact-sounds/impactSoft_heavy_002.ogg`, `rpg-audio/cloth1.ogg`, `rpg-audio/cloth2.ogg`, `rpg-audio/cloth3.ogg` |
| `fall_armoured` | combat | cc0 | Kenney CC0: `impact-sounds/impactMetal_light_000.ogg`, `impact-sounds/impactMetal_light_002.ogg`, `impact-sounds/impactMetal_light_004.ogg`, `impact-sounds/impactPlate_light_001.ogg`, `impact-sounds/impactPlate_light_003.ogg`, `impact-sounds/impactPlate_light_004.ogg`, `impact-sounds/impactPlate_medium_000.ogg`, `impact-sounds/impactPlate_medium_002.ogg`, `impact-sounds/impactPlate_medium_004.ogg`, `impact-sounds/impactPunch_heavy_000.ogg`, `impact-sounds/impactPunch_heavy_003.ogg`, `impact-sounds/impactPunch_heavy_004.ogg`, `impact-sounds/impactSoft_heavy_000.ogg`, `impact-sounds/impactSoft_heavy_003.ogg`, `impact-sounds/impactSoft_heavy_004.ogg` |
| `fall_huge` | combat | cc0 | Kenney CC0: `impact-sounds/impactPlank_medium_001.ogg`, `impact-sounds/impactPlank_medium_002.ogg`, `impact-sounds/impactPlank_medium_003.ogg`, `impact-sounds/impactPunch_heavy_001.ogg`, `impact-sounds/impactPunch_heavy_002.ogg`, `impact-sounds/impactPunch_heavy_003.ogg`, `impact-sounds/impactSoft_heavy_001.ogg`, `impact-sounds/impactSoft_heavy_002.ogg`, `impact-sounds/impactSoft_heavy_003.ogg`, `impact-sounds/impactWood_heavy_000.ogg`, `impact-sounds/impactWood_heavy_002.ogg`, `impact-sounds/impactWood_heavy_004.ogg`; procedural layers |
| `hit_sub` | combat | procedural | procedural layers |
| `ui_click_kingdom` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_001.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_003.ogg`, `impact-sounds/impactWood_light_004.ogg`; procedural layers |
| `ui_click_clans` | ui | cc0 | Kenney CC0: `impact-sounds/impactMetal_light_000.ogg`, `impact-sounds/impactMetal_light_001.ogg`, `impact-sounds/impactMetal_light_002.ogg`, `impact-sounds/impactMetal_light_003.ogg`, `impact-sounds/impactMetal_light_004.ogg`, `impact-sounds/impactPunch_medium_000.ogg`, `impact-sounds/impactPunch_medium_001.ogg`, `impact-sounds/impactPunch_medium_002.ogg`, `impact-sounds/impactPunch_medium_003.ogg`, `impact-sounds/impactPunch_medium_004.ogg`, `impact-sounds/impactSoft_medium_000.ogg`, `impact-sounds/impactSoft_medium_001.ogg`, `impact-sounds/impactSoft_medium_002.ogg`, `impact-sounds/impactSoft_medium_003.ogg`, `impact-sounds/impactSoft_medium_004.ogg` |
| `ui_disabled_kingdom` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_medium_000.ogg`, `impact-sounds/impactWood_medium_002.ogg`, `impact-sounds/impactWood_medium_004.ogg` |
| `ui_disabled_clans` | ui | cc0 | Kenney CC0: `impact-sounds/impactPunch_medium_001.ogg`, `impact-sounds/impactPunch_medium_003.ogg`, `impact-sounds/impactPunch_medium_004.ogg`, `impact-sounds/impactSoft_medium_001.ogg`, `impact-sounds/impactSoft_medium_003.ogg`, `impact-sounds/impactSoft_medium_004.ogg` |
| `ui_error_kingdom` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_medium_000.ogg`, `impact-sounds/impactWood_medium_001.ogg`, `impact-sounds/impactWood_medium_002.ogg`, `impact-sounds/impactWood_medium_003.ogg`, `impact-sounds/impactWood_medium_004.ogg` |
| `ui_error_clans` | ui | cc0 | Kenney CC0: `impact-sounds/impactPunch_medium_000.ogg`, `impact-sounds/impactPunch_medium_001.ogg`, `impact-sounds/impactPunch_medium_002.ogg`, `impact-sounds/impactPunch_medium_003.ogg`, `impact-sounds/impactSoft_heavy_000.ogg`, `impact-sounds/impactSoft_heavy_001.ogg`, `impact-sounds/impactSoft_heavy_002.ogg`, `impact-sounds/impactSoft_heavy_003.ogg`; procedural layers |
| `ui_order_kingdom` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_001.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_003.ogg`, `impact-sounds/impactWood_light_004.ogg`, `rpg-audio/bookFlip2.ogg`, `rpg-audio/bookFlip3.ogg`; procedural layers |
| `ui_order_clans` | ui | cc0 | Kenney CC0: `impact-sounds/impactMetal_light_001.ogg`, `impact-sounds/impactMetal_light_003.ogg`, `impact-sounds/impactPunch_medium_000.ogg`, `impact-sounds/impactPunch_medium_001.ogg`, `impact-sounds/impactPunch_medium_002.ogg`, `impact-sounds/impactPunch_medium_003.ogg`, `impact-sounds/impactPunch_medium_004.ogg`, `impact-sounds/impactSoft_medium_000.ogg`, `impact-sounds/impactSoft_medium_001.ogg`, `impact-sounds/impactSoft_medium_002.ogg`, `impact-sounds/impactSoft_medium_003.ogg`, `impact-sounds/impactSoft_medium_004.ogg`, `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_001.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_003.ogg`, `impact-sounds/impactWood_light_004.ogg`; procedural layers |
| `ui_select_kingdom` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_001.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_003.ogg`, `impact-sounds/impactWood_light_004.ogg` |
| `ui_select_clans` | ui | cc0 | Kenney CC0: `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_001.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_003.ogg`, `impact-sounds/impactWood_light_004.ogg`; procedural layers |
| `hero_xp_kingdom` | heroes | cc0 | Kenney CC0: `impact-sounds/impactWood_light_000.ogg`, `impact-sounds/impactWood_light_002.ogg`, `impact-sounds/impactWood_light_004.ogg`; procedural layers |
| `hero_xp_clans` | heroes | procedural | procedural layers |
| `hero_level_kingdom` | heroes | procedural | Kenney CC0: `impact-sounds/impactMetal_light_000.ogg`, `impact-sounds/impactMetal_light_002.ogg`, `impact-sounds/impactPlate_light_001.ogg`, `impact-sounds/impactPlate_light_003.ogg`; procedural layers |
| `hero_level_clans` | heroes | procedural | procedural layers |
| `hero_bell_kingdom_l2` … `_l10` | heroes | procedural | procedural layers |
| `hero_bell_clans_l2` … `_l10` | heroes | procedural | procedural layers |
| `hero_down` | heroes | procedural | Kenney CC0: `impact-sounds/impactSoft_heavy_000.ogg`, `impact-sounds/impactSoft_heavy_002.ogg`; procedural layers |
| `hero_revive` | heroes | procedural | procedural layers |
| `bullet_hit` | ranged | derived | Kenney CC0: `impact-sounds/impactSoft_medium_002.ogg`; own generated takes: `combat/hit_flesh_l_02.wav`, `combat/hit_metal_l_01.wav`, `combat/hit_wood_l_03.wav`; procedural layers |
| `javelin_hit` | ranged | derived | Kenney CC0: `impact-sounds/impactPunch_medium_002.ogg`, `impact-sounds/impactSoft_heavy_001.ogg`, `impact-sounds/impactWood_medium_001.ogg`; own generated takes: `combat/hit_flesh_l_03.wav`, `combat/hit_metal_l_02.wav`, `combat/hit_wood_l_01.wav`, `combat/hit_wood_l_02.wav`; procedural layers |
| `hit_wood_h` | combat | derived | Kenney CC0: `impact-sounds/impactPlank_medium_000.ogg`, `impact-sounds/impactPlank_medium_002.ogg`, `impact-sounds/impactPlank_medium_003.ogg`, `impact-sounds/impactPlank_medium_004.ogg`, `impact-sounds/impactWood_heavy_000.ogg`, `impact-sounds/impactWood_heavy_001.ogg`, `impact-sounds/impactWood_heavy_002.ogg`, `impact-sounds/impactWood_heavy_004.ogg`; own generated takes: `combat/hit_wood_l_01.wav`, `combat/hit_wood_l_02.wav`, `combat/hit_wood_l_03.wav` |
| `claypot_hit` | ranged | derived | Kenney CC0: `impact-sounds/impactGlass_heavy_000.ogg`, `impact-sounds/impactGlass_heavy_001.ogg`, `impact-sounds/impactGlass_heavy_002.ogg`, `impact-sounds/impactGlass_heavy_004.ogg`, `impact-sounds/impactSoft_heavy_000.ogg`, `impact-sounds/impactSoft_heavy_002.ogg`, `impact-sounds/impactSoft_heavy_003.ogg`, `impact-sounds/impactSoft_heavy_004.ogg`; own generated takes: `ranged/bombard_hit_01.wav`, `ranged/bombard_hit_03.wav`, `ranged/bombard_hit_04.wav`, `ranged/bombard_hit_05.wav`; procedural layers |
| `sw_pierce` | combat | derived | own generated takes: `combat/sw_slash_01.wav`, `combat/sw_slash_03.wav`, `combat/sw_slash_04.wav` |
| `vox_death_clans` | combat | derived | own generated takes: `combat/vox_death_kingdom_01.wav`, `combat/vox_death_kingdom_02.wav`, `combat/vox_death_kingdom_03.wav` |
