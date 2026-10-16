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
| Higgsfield | tripo_h3_1_image_to_3d | 9 cr (quoted) |
| Higgsfield | hunyuan3d_v3_image_to_3d LowPoly | 14 cr (quoted) |
| Higgsfield | image_to_3d (Meshy) textured | 30 cr (quoted) |
| Higgsfield | image_to_3d textured + rig + 1 animation | 38 cr (quoted) |
| Higgsfield | 3d_rigging + 1 animation (existing GLB) | 8 cr (quoted) |

## Spend log

| # | Date | Service | What | Cost | Result |
|---|---|---|---|---|---|
| 1 | 2026-10-16 | Krea | Grass texture probe (Krea 2 Medium) | 9 CU | OK, usable |
| 2 | 2026-10-16 | Krea | Pine tree text-to-3D probe (Tripo H3.1) | 148.15 CU | Charged, but the MCP call timed out (sync mode) and the job id was lost — result not retrievable via API |
| 3 | 2026-10-16 | Krea | Boulder text-to-3D probe (Hunyuan 3.1 Rapid) | 0 | Provider 504, not charged |
| 4 | 2026-10-16 | Krea | Boulder text-to-3D probe (Hunyuan 3.1 Rapid, retry) | 166.67 CU | OK, 50k faces / 4K texture |
| 5 | 2026-10-16 | Krea | Sword-on-shield SFX probe (Seed Audio) | 4.63 CU | OK |
| 6 | 2026-10-16 | Higgsfield | Dirt texture (gpt_image_2_5) | 0.25 cr | OK, very good |

**Balances after log:** Krea 1766.67 CU · Higgsfield 269.75 cr
