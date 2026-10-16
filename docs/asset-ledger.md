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

**Bake-off conclusion (2026-10-16):** characters and anything that turns → Higgsfield Tripo H3.1 (9 cr) + Higgsfield
rigging (8 cr). Static buildings/props → Krea TRELLIS v1 (~15 CU) is acceptable when the back is never seen; otherwise
Higgsfield Tripo H3.1. All other Krea 3D models cost 148–222 CU each — banned.

**Balances after log:** Krea 1529.63 CU · Higgsfield 228.5 cr (verified 2026-10-16 14:45)
