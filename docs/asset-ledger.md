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
| 23 | 2026-10-17 | Krea | Hall image-to-3D, 2 × TRELLIS v1 tex 2048: moot hall f94c3854-3da3-4dc1-9111-e18142779ce2 (seed 1180), shell hall af8d88a7-0e47-466e-a7c1-259003f3973b (seed 1280) | ~30 CU (est.) | pending |

**Bake-off conclusion (2026-10-16):** characters and anything that turns → Higgsfield Tripo H3.1 (9 cr) + Higgsfield
rigging (8 cr). Static buildings/props → Krea TRELLIS v1 (~15 CU) is acceptable when the back is never seen; otherwise
Higgsfield Tripo H3.1. All other Krea 3D models cost 148–222 CU each — banned.

**Balances after log:** Krea 1529.63 CU · Higgsfield 225.25 cr (verified 2026-10-16 16:49)
