# AI asset pipeline: Krea (image, 3D, audio) → Blender (bpy) → Godot 4.7

*Research date: 2026-10-16. Scope: how to turn Krea generations into game-ready, rigged, consistent RTS assets on our GPU-less Linux container, and how to import them into Godot 4.7.*

**How this was researched.** The shared web-search budget for this run was already used up when this task started (0 searches available). Everything below comes from other sources:

- Direct fetches of official docs: Krea, Meshy, Hyper3D/Rodin, Tripo SDK, Blender, Godot, PyMeshLab, trimesh, and GitHub READMEs.
- Krea's live model schemas (`list_models`, `get_model_schema`) and its public OpenAPI spec, which has per-model USD prices.
- The PyPI JSON API.
- **Benchmarks run in this container** with bpy 5.2.2, Godot 4.7.2, trimesh and pymeshlab.

Anything I could not confirm is marked **(unverified)**. Model-quality claims about the five 3D generators come from vendor descriptions, not independent comparisons. Treat them as hypotheses for the bake-off in §2.6.

Related docs:

- `visual-art-direction.md` §3.1 (scale and tri budgets), §7.3 (prompt kit), §7.4 (post-processing).
- `audio-direction.md` §4 (Krea audio endpoints).
- `docs/asset-ledger.md` (measured costs).
- `tools/process_model.py` (existing GLB normaliser).

---

## 0. TL;DR

1. **Budget is the binding constraint, not quality.** We have 1,766.67 Krea compute units (CU), all purchased CU; plan CU is 0 (`get_balance`, 2026-10-16).
   - One job on a *flagship* Krea 3D model (Tripo H3.1, Hunyuan3D 3.1, TRELLIS 2) costs 148–300 CU, so that is **about 6–11 flagship models in total**.
   - **Correction (fact-check):** Krea also lists cheaper "Medium"-quality legacy 3D models: **Tripo (legacy) 8 CU, TRELLIS (v1) 10 CU, Hunyuan3D-2.1 25 CU** ([Krea 3D doc](https://www.krea.ai/docs/3-d.md)). All three are exposed through the MCP/API (`tripo/tripo`, `microsoft/trellis`, `tencent/hunyuan3d-2.1` in `list_models`). At 8–10 CU each that is roughly 170–220 models, so include them in the bake-off (§2.6) before concluding that 3D is limited to a handful of assets. The CU price over OAuth MCP is assumed equal to the web-app price (unverified).
   - One Krea 2 Medium image costs 9 CU, so that is **about 196 images**.
   - Spend flagship 3D generations only on characters and signature buildings. Revisit this if the 8–10 CU legacy models pass the bake-off. Make doodads (trees, rocks, fences, crates) and modular building parts procedurally in bpy.
   - Iterate in 2D at 9 CU per image, then commit one 3D job per approved concept.
2. **The cheapest 3D on Krea's USD API is far below CU pricing for some models.** Prices from the OpenAPI spec:
   - TRELLIS (v1, `microsoft/trellis`): **$0.02** per request. This is the cheapest 3D endpoint (fact-check correction: the original draft named Rodin 2.5 Fast as the cheapest).
   - Rodin 2.5 Fast: **$0.10** per request.
   - Hunyuan3D 3.1 Rapid: $0.225.
   - Tripo (legacy, `tripo/tripo`): $0.30.
   - Rodin 2.5: $0.40.

   The minimum API top-up is $5. That is a cheap budget multiplier, **but it is the user's decision**. Tripo H3.1, Hunyuan3D 3.1 Pro, Hunyuan3D-2.1, TRELLIS 2 and Meshy 7 have no published fixed price.
3. **Ask the generator for a low face count up front** where Krea allows it:
   - Tripo H3.1 `face_limit`: 1,000–2,000,000.
   - Meshy 7 `target_polycount`: 100–300,000.
   - Hunyuan3D 3.1 Pro `face_count`: minimum 40,000.
   - TRELLIS 2 `decimation_target`: minimum 100,000.
   - Rodin 2.5 on Krea has no polycount control.

   After generation, always run `tools/process_model.py` (Blender Decimate) to reach the final budget. **Do not use trimesh for decimation: it drops UVs and textures** (tested).
4. **Input image rules for image-to-3D:**
   - One object, centred, whole figure visible.
   - Plain light-grey background. Never magenta, because magenta is our team-colour key.
   - Even flat light, no cast shadows. Meshy notes that shadows cause black patches.
   - Near-orthographic view.
   - Characters in **A-pose**, with visible gaps between the legs and between the arms and the torso.
   - Weapons held clear of the body, or generated separately.
   - For the hand-painted look, **keep PBR off** (`enable_pbr: false`) so the painted light stays in the albedo.
5. **Auto-rigging works on CPU with what we already have.** bpy 5.2.2 runs on Python 3.13 at `/opt/bpyenv/v313`, and Rigify is bundled.
   - Benchmark: bone-heat weights failed on a "triangle soup" AI-style mesh, leaving 172,768 of 172,768 vertices unweighted.
   - With a voxel-remeshed proxy plus a Data Transfer of the weights back, **0 vertices were unweighted, in about 1 s total**.
   - Use template skeletons with fixed bone names, and keyframe animations procedurally per body type.
6. **Neural auto-riggers are not viable here.**
   - UniRig needs CUDA with at least 8 GB VRAM.
   - RigNet needs CUDA 10/11, an old PyTorch, and is GPL-3.
   - MagicArticulate and Puppeteer need CUDA plus flash-attn.
   - Mixamo has no public API (unverified; its FAQ returned 403 to our fetch).
7. **Style consistency comes from a fixed stack:**
   - Krea 2 Medium (9 CU).
   - Plus `image_style_references` (up to 10, strength 0–1, default 0.5) or one `moodboard`.
   - Plus a fixed prompt suffix, `creativity: "raw"`, and a fixed seed per asset family.

   Trained styles (LoRA) can only use Flux/Qwen/Z-Image/Wan base models, not Krea 2.
8. **Batch 2D work in grids.** One 1K image can be a 2×2 sheet: 4 icons, or 4 terrain variants at 512 px each. That gives about 4× more assets per CU.
   - Make terrain tileable in Python. The offset-and-blend method in §4.3 dropped the wrap-seam ratio from 22.2 to 1.22 in a test, where 1.0 means seamless.
   - Frame icons programmatically at 128 px (§4.4).
9. **Godot import settings:**
   - Godot 4.7.2 supports **neither Draco nor meshopt glTF compression** (checked via `GLTFDocument.get_supported_gltf_extensions()`). Always re-export through Blender.
   - Units: no import LODs (the docs warn LODs can break skinned meshes), tangents off (no normal maps), backface culling on.
   - Buildings and doodads: keep import LODs on.
   - Reimport headless with `godot --headless --import`.
10. **pymeshlab decimation silently fails to load in this container** because `libOpenGL.so.0` is missing (the package is `libopengl0`, unverified). Prefer Blender Decimate.

---

## 1. Budget reality

### 1.1 Measured and published costs

| Item | Krea CU (web/MCP) | Krea API USD (OpenAPI `x-krea-pricing`) | Source |
|---|---|---|---|
| Krea 2 Medium image (1K) | 9 (measured) | $0.030 plain · $0.035 with style refs · $0.040 with moodboard | ledger; OpenAPI |
| Krea 2 Medium Turbo | n/a | $0.015 / $0.0175 / $0.020 | OpenAPI |
| Krea 2 Large | n/a | $0.060 / $0.065 / $0.070 | OpenAPI |
| Flux.1 Dev (best for LoRAs) | 5 (unverified: the model overview lists "Flux.1 Krea" at 5, not Flux.1 Dev) | $0.007 | OpenAPI |
| Recraft V4.1 Flash | 5 | $0.007 | model overview; OpenAPI |
| Qwen Image 2.1 (transparent) | ~30 | $0.04 | model overview; OpenAPI |
| GPT Image 2.5 Flare (transparent) | ~75 | not published (variable) | model overview |
| Nano Banana 2 | ~45 | $0.08 / $0.12 / $0.16 (1K/2K/4K) | model overview; OpenAPI |
| Nano Banana 2.1 | n/a | $0.03 / $0.0505 / $0.0755 | OpenAPI |
| Nano Banana Pro | ~110 (1K/2K), ~155 (4K) | $0.15 (1K/2K), $0.30 (4K) | NB Pro page; OpenAPI |
| Ideogram 4.5 Precise (masked edit) | ~150 (4.5) | $0.008 (very low) to $0.22 (high) | model overview; OpenAPI |
| **Tripo H3.1** (text-to-3D, textured) | **148.15 (measured)** | not published | ledger |
| **Hunyuan3D 3.1 Rapid** | **166.67 (measured)**: 50k faces, 4K texture | **$0.225** | ledger; OpenAPI |
| Hunyuan3D 3.1 Pro | ~300 | not published | Krea 3D doc |
| TRELLIS 2 | ~250 | not published | Krea 3D doc |
| **TRELLIS (v1)** ("Medium" quality) | **10** | **$0.02** | Krea 3D doc; OpenAPI |
| **Tripo (legacy)** ("Medium" quality) | **8** | $0.30 | Krea 3D doc; OpenAPI |
| Hunyuan3D-2.1 ("Medium" quality) | 25 | not published | Krea 3D doc |
| Hunyuan3D-2 / 2mini-Turbo | 10 / 7 | not on the API | Krea 3D doc (web app only; absent from `list_models`) |
| Meshy 7 | unknown | not published | — |
| Rodin 2.5 | unknown | **$0.40** | OpenAPI |
| Rodin 2.5 Fast ("quick iteration on shapes") | unknown | **$0.10** | OpenAPI |
| Seed Audio SFX (~2.5 s) | 4.63 (measured) | see audio-direction.md | ledger |

**Plans.** Basic costs $9/month for 5,000 CU/month, which is about $0.0018 per CU. Pro costs $35/month for 20,000 CU ([Krea pricing](https://www.krea.ai/pricing)). Fact-check note: the Basic $9 / 5,000 CU figure appears only in the pricing page's structured data, not in the visible plan cards (Free, Pro, Max, Business). The visible cards show Pro at $21/month billed annually ($35 monthly), and Max at 60,000 CU, while the structured data says Max is $70 for 40,000 CU. Treat the plan numbers as approximate. The account is on "Individual Basic" (5,000 monthly CU), but the current balance is purchased CU only. Packs last 90 days, and individual-plan CU does not roll over ([CU guide](https://www.krea.ai/docs/user-guide/help-and-support/compute-units.md)).

**API balance.** The API balance is separate, in USD:

- Top-ups: $10, $25, $50 or $100 presets, or a custom amount from $5 to $10,000.
- Failed and cancelled jobs are not billed.
- An empty balance returns HTTP 402.

Source: [Krea API billing](https://www.krea.ai/docs/developers/api-keys-and-billing.md). Token-based MCP connections bill this USD balance. OAuth MCP connections bill CU.

### 1.2 Suggested split of the 1,766 CU (proposal)

| Bucket | CU | Buys |
|---|---|---|
| 3D: 5 hero/key characters + 1 signature building (Tripo H3.1 at about 148 CU) | ~890 | 6 models |
| 2D: style anchors, unit concepts, terrain, icons, UI (Krea 2 Medium, 9 CU) | ~450 | ~50 images, or about 200 icons/tiles using 2×2 grids |
| Audio (see audio-direction.md) | ~300 | ~60 SFX at 4.63 CU each, plus a few voice lines |
| Reserve for retries | ~125 | — |

If the user adds a $5–10 API balance, use it for TRELLIS v1 ($0.02), Rodin 2.5 Fast ($0.10) and Hunyuan3D 3.1 Rapid ($0.225) jobs. That turns 3D from about 6 models into dozens, or hundreds with TRELLIS v1.

Even without an API balance, the legacy CU models (Tripo 8 CU, TRELLIS v1 10 CU) could cover rank-and-file units and props if they pass the bake-off. That would free most of the 890 CU 3D bucket above.

**Always submit 3D jobs async and log the job id first.** Ledger entry #2 lost a paid 148 CU Tripo result to a synchronous timeout.

---

## 2. Image-to-3D for game-ready assets

### 2.1 What Krea actually exposes, per model

From `get_model_schema` on 2026-10-16. All of these take `prompt`, `input_mode` (image/text), `generate_texture` and `image_urls`. All except Hunyuan3D 3.1 Rapid also take `seed`; Rapid has no `seed` parameter (fact-check, OpenAPI).

`list_models` (3d) returns **10** models, not just the ones in the table below. The extra three are `tripo/tripo` (legacy Tripo, 8 CU / $0.30), `microsoft/trellis` (TRELLIS v1, 10 CU / $0.02, with a `texture_size` parameter) and `tencent/hunyuan3d-2.1` (25 CU). None of them has a polycount control.

| Model (Krea id) | Extra controls on Krea | Polycount control | Vendor positioning |
|---|---|---|---|
| Tripo H3.1 (`tripo/h3.1`) | — | `face_limit` 1,000–2,000,000 | "sharp geometry from text or image at low cost" |
| Hunyuan3D 3.1 Pro (`tencent/hunyuan3d-3.1-pro`) | `enable_pbr`; **multi-view inputs**: `back_`, `left_`, `right_`, `top_`, `bottom_`, `left_front_`, `right_front_image_url` | `face_count` **40,000**–1,500,000 | "high-fidelity… adjustable face count for cleaner meshes" |
| Hunyuan3D 3.1 Rapid (`…-rapid`) | none | none (measured 50k faces, 4K texture) | "fast, inexpensive tier" |
| TRELLIS 2 (`microsoft/trellis-2`) | `resolution` 512/1024/1536; `texture_size` 1024/2048/4096 | `decimation_target` **100,000**–2,000,000 | "native 3D generative model" |
| Meshy V7 (`meshy/meshy-7`) | `enable_pbr` | `target_polycount` 100–300,000 | "production-ready meshes… clean topology and PBR-quality textures" |
| Rodin V2.5 (`hyper3d/rodin-2.5`) and Fast | up to **5** images in `image_urls` | none on Krea | "detailed, well-structured meshes with PBR materials" |

**Upstream facts** (the vendors' own APIs; Krea wraps only some of these):

- **TRELLIS.2.** A 4B-parameter model with MIT licence ([GitHub](https://github.com/microsoft/TRELLIS.2)).
  - It uses an "O-Voxel" sparse structure for "complex topology, sharp features" and PBR materials: base colour, roughness, metallic and opacity.
  - Resolutions are 512³, 1024³ and 1536³, taking about 3 s, 17 s and 60 s on an H100.
  - The reference export decimates to 1,000,000 faces with a 4096 texture. GLB alpha exports as OPAQUE, so transparency must be re-wired manually. Self-hosting needs at least a 24 GB GPU.
- **Meshy API** ([image-to-3d](https://docs.meshy.ai/en/api/image-to-3d)):
  - `target_polycount` defaults to 30,000 and applies when `should_remesh` is true. For Meshy 6/7, `should_remesh` **defaults to false**, so the Krea wrapper's behaviour is unverified.
  - `topology` can be quad or triangle.
  - `pose_mode` can be `a-pose` or `t-pose`.
  - `enable_pbr` adds metallic, roughness and normal maps.
  - Outputs: glb, obj, fbx, stl, usdz, plus 3mf when it is requested explicitly.
  - "Smart Topology" models: meshy-t2 targets 100–15,000 faces (default 4,000); meshy-t2.5 targets up to 30,000. These are not on Krea.
  - `meshy-7` is deprecated in favour of `meshy-7.1`.
  - Pricing: 20–35 Meshy credits per image-to-3D for meshy-7.1 and meshy-6 (5–20 for meshy-6-lite and the t2/t2.5 models); auto-rig 5 credits; animation 3 credits per action, up to 10 actions per request ([Meshy pricing](https://docs.meshy.ai/en/api/pricing)).
- **Rodin Gen-2.5 API** ([spec](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)):
  - 1–5 images; the first one drives the material.
  - Tiers: `Gen-2.5-Extreme-Low` through `Extreme-High`.
  - `mesh_mode` Raw/Quad.
  - "Fast mode" applies when `quality_override ≤ 20000`, with Raw GLB output.
  - Textures run from 2K (default) up to 12K.
- **Tripo API** ([SDK docs](https://github.com/VAST-AI-Research/tripo-python-sdk/blob/master/docs/API.md)):
  - Model versions include `v3.1-20260211`, `v3.0-20250812`, `P1-20260311` and `P2-20260801`. H3.1 most likely corresponds to v3.1 (unverified).
  - Options: `face_limit`, `texture`, `pbr` (default True), `texture_quality` standard/detailed, `smart_low_poly`, `quad`.
  - Tripo also sells `rig_model` (biped and other types; mixamo/unity/vrm specs) and `retarget_animation`. **These are not exposed through Krea.**
- **Hunyuan3D open-source** (2.0/2.1) needs 6–29 GB VRAM ([2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1), [2.0](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)). It is not runnable here. Krea also hosts Hunyuan3D-2.1 (25 CU, "Medium" quality).

### 2.2 Input image checklist

Sources: Meshy's own guide ([Meshy webapp guide](https://docs.meshy.ai/en/webapp/image-to-3d)), Krea's 3D guide ("clear image… clearly separated from the background… good lighting"), and our art direction. The tips apply to all generators, because they all reconstruct hidden sides from the visible pixels.

- **Exactly one object.** Meshy says multi-object photos produce "one distorted mesh". Crop to a single item.
- **Centred, fills about 80–90% of the frame, nothing cropped.** Feet, weapon tip and banner top must all be visible.
- **At least 512×512.** Meshy recommends "resolution ≥ 512×512" (a recommendation, not a hard minimum). Krea 2 Medium's 1K output is fine.
- **Simple background.**
  - Use light neutral grey (#C8C8C8 to #D8D8D8) for characters, so white highlights still separate.
  - Never use magenta: it is the team-colour key in visual-art-direction §7.3.
  - A transparent cutout is the cleanest input. Qwen Image 2.1 (~30 CU) or GPT Image 2.5 Flare (~75 CU) can produce one directly. For bodies, Krea 2 Medium on grey at 9 CU is usually enough.
- **Even, flat lighting; no cast shadows, no dark rims.** Meshy's troubleshooting table lists "Black patches on model surface" with the cause "Input image has shadows or dark areas".
  - For our hand-painted look, a *soft painted top-light* in the colours is wanted, because WC3-style art paints light into the texture. Hard shadows on the ground or across the body are not.
- **Near-orthographic** ("orthographic, no perspective distortion, telephoto"). Meshy recommends near-orthographic or telephoto shots to avoid proportion distortion.
- **Characters: A-pose, front three-quarter (about 15–30° yaw) at slight elevation.** Meshy: "For best results with Animate (auto-rig + animation presets), set the pose to T-pose or A-pose."
  - Keep **clear gaps** between the legs (at least 5% of height) and between the arms and the torso. These gaps keep a voxel rig proxy from fusing the limbs (§3.3).
  - Hold the weapon out from the body, or generate it separately as "isolated [weapon], side view" and attach it to a hand bone.
- **Exaggerate thin parts by about 1.3×** (art doc §7.3). Generators thin out spears, staffs, ears and horns. Anything under about 2% of height may vanish or come out as a blob after decimation (unverified rule of thumb).
- **Buildings: three-quarter view from about 35–45° elevation.** This matches the gameplay camera (about -56° pitch, art doc §7.4), so the faces players actually see get the best texture.
  - With a WC3-style fixed-yaw camera, the back of a building is rarely seen. A single image is enough, and the generator's guessed back side is acceptable (design inference).
- **Multi-view only for heroes.** Hunyuan3D 3.1 Pro accepts back/left/right/etc. views, and Rodin up to 5 images. Meshy recommends front, side, back and 3/4 views under the same lighting.
  - Producing consistent extra views needs an identity-preserving model: Nano Banana Pro takes up to 4 references at ~110 CU, and GPT Image 2.5 takes up to 10 `image_urls` at ~75 CU. That is too expensive for rank-and-file units.

### 2.3 Which generator for which asset (proposal; verify with the bake-off in §2.6)

| Asset class | First choice | Why | Settings |
|---|---|---|---|
| Infantry, workers, monsters | **Tripo H3.1** | Lowest measured CU (148), direct `face_limit` so less decimation damage, marketed for sharp geometry | `face_limit` 8,000–12,000 → decimate to 2–4k (heroes 4–8k) |
| Same, if Tripo silhouettes disappoint | Meshy 7 | Direct `target_polycount`, `enable_pbr: false`, clean topology claim | `target_polycount` 8,000–10,000 (remesh behaviour unverified) |
| Heroes (multi-view) | Hunyuan3D 3.1 Pro | Only Krea model with named-view inputs | `face_count` 40,000 (minimum), `enable_pbr: false`, → decimate to 6–8k |
| Signature buildings (crisp edges) | TRELLIS 2 or Hunyuan3D 3.1 Pro | "sharp features" (TRELLIS) or face-count control | TRELLIS: `resolution` 1024, `texture_size` 2048, `decimation_target` 100,000 → decimate to 6–15k |
| Fast shape exploration (if API USD balance exists) | TRELLIS v1 ($0.02) or Rodin 2.5 Fast ($0.10) | TRELLIS v1 is the cheapest per request; Rodin Fast is the cheapest current-generation model | Use for blockouts, then re-run the winner on a better model |
| Rank-and-file units and props, CU only (if they pass the bake-off) | Tripo legacy (8 CU) or TRELLIS v1 (10 CU) | About 15–18× cheaper than Tripo H3.1; Krea rates them "Medium" quality | No polycount control, so always decimate with `process_model.py` |
| Trees, rocks, fences, crates, walls, modular roofs | **No AI 3D**: procedural bpy plus AI 2D textures | Thousands of instances; simple chunky shapes; 0 CU for geometry | 0.5–1.5k tris trees, 100–800 props (art doc §3.1) |

**Hand-painted look.** Every one of these models projects the input image onto the mesh and in-paints the hidden sides. The *style* therefore comes mostly from the input image.

- Turn **PBR off** where possible (Hunyuan Pro and Meshy). We render with roughness 1, metallic 0 and our own toon/wrap shader (art doc §7.5). PBR de-lighting would also strip the painted light out of the albedo (inference).
- Keep only the base colour.
- Re-paint or "de-noise" the albedo in post (art doc §7.4: median filter, palette remap).

### 2.4 Polygon and texture budgets

Use the budgets in **visual-art-direction.md §3.1**:

| Class | Tris | Texture |
|---|---|---|
| Worker | 1.5–3k | 512² |
| Infantry | 2–4k | 512² |
| Hero | 4–8k | 1024² |
| Large unit | 4–8k | 1024² |
| Small building | 3–6k | 1024² |
| Main hall | 6–12k | 2048² |
| Tree | 0.5–1.5k | — |
| Props | 100–800 | — |

This task's brief allows up to 8k for units and 5–20k for buildings. Treat those as hard ceilings, not targets: an RTS draws 100+ units at once.

Skinned units: at most **4 bone influences per vertex**. This matches Godot's "4 Influences (Compatible)" skin import mode, which the docs say is "compatible with all renderers"; "All Influences" allows up to 8 ([Godot import configuration](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/import_configuration.html)). Fact-check note: that option belongs to Godot's direct `.blend` importer. For GLB files we enforce the limit ourselves at export (§3.3, `vertex_group_limit_total`).

### 2.5 Decimation recipe (Blender, headless)

`tools/process_model.py` already does the following:

1. Join all meshes.
2. Weld co-located vertices, so UV seams survive as per-corner UVs.
3. Clean up (`--cleanup`: loose geometry, degenerate faces, small islands).
4. Decimate with **Collapse** (quadric) to `--target-tris`.
5. Normalise scale and origin, and face the model to -Z.
6. Smooth by angle.
7. Downscale and embed textures.
8. Build an optional team-colour mask.
9. Export GLB without Draco or meshopt.

Additions recommended by this research:

- **Two-stage reduction for 40k–1M inputs.** First decimate to about 4× the target, then clean islands again, then decimate to the target. Big single-step collapses are where spikes and holes appear (practice, unverified). PyMeshLab notes that optimal placement "can fail (creating bad spikes) in case of very flat areas" ([PyMeshLab filters](https://pymeshlab.readthedocs.io/en/latest/filter_list.html)).
- **Dilate UV islands before downscaling textures.** AI atlases are fragmented into many small islands. Downscaling 4K to 512 bleeds the background colour into the seams. Either:
  - re-bake with a margin of about 8 px in Blender, or
  - dilate colour outward from the island mask (iterative max-filter on alpha) before the Lanczos resize (practice).
- **Enable backface culling on every material before export.** Blender exports materials with culling disabled by default, so Godot sets cull mode to Disabled ([Godot formats doc](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html)). Use `mat.use_backface_culling = True`.

Tool comparison (tested here, 2026-10-16):

| Tool | Result |
|---|---|
| **Blender Decimate (bpy 5.2.2)** | Keeps UVs and vertex groups; already in our tooling. **Use this.** |
| trimesh 5.1.1 `simplify_quadric_decimation` (wraps `fast-simplification` 0.2.0) | Very fast: 81,920 → 4,000 faces in 0.11 s. **But it drops UVs and texture** (`visual.kind=None` after the call). Fine for collision or navmesh proxies only. API: `face_count=` or `percent=`, `aggression` 0–10 ([trimesh docs](https://trimesh.org/trimesh.base.html)). |
| pymeshlab 2025.7.post1 `meshing_decimation_quadric_edge_collapse_with_texture` | Has UV-preserving options: `targetfacenum`, `qualitythr` 0.3, `extratcoordw`, `preserveboundary`, `preservenormal`, `optimalplacement`, `planarquadric`. **In this container the meshing plugin fails to load** (`libfilter_meshing.so: libOpenGL.so.0 => not found`), so the filter does not exist at runtime. The fix would be the system package `libopengl0` (unverified). |

### 2.6 Bake-off protocol (cheap; run before committing the budget)

1. Make one A-pose infantry concept and one building concept with Krea 2 Medium (2 × 9 CU).
2. Generate the infantry with Tripo H3.1 (`face_limit` 10,000) and the building with Tripo H3.1 (`face_limit` 20,000). Also run both concepts through the cheap legacy models, Tripo (8 CU) and TRELLIS v1 (10 CU), which adds about 36 CU. If an API USD balance exists, also run Rodin 2.5 Fast and Hunyuan 3.1 Rapid.
3. Process both with `process_model.py` to final budgets.
4. Render from the game camera at 1080p. Score with the checks from art doc §7.4:
   - silhouette readable at about 40 px tall;
   - three value masses in greyscale;
   - texture fidelity on visible faces;
   - artefacts such as holes, fused limbs, baked shadows;
   - CU spent.
5. Only switch generators if Tripo fails the silhouette or fused-limb test.

---

## 3. Auto-rigging without paid services (Linux, no GPU)

### 3.1 Blender options

| Option | Python | Linux wheel/binary | Notes |
|---|---|---|---|
| **`pip install bpy==5.2.2`** (current, Blender 5.2 LTS) | **3.13 only** (`requires_python ==3.13.*`) | `manylinux_2_28_x86_64`, 402 MB | **Installed and working** at `/opt/bpyenv/v313`. Bundled add-ons include `rigify` and `io_scene_gltf2` (checked with `addon_utils`). |
| bpy 5.1.x | 3.13 | manylinux_2_28 | |
| bpy 5.0.x | 3.11 | manylinux_2_28 | |
| bpy 4.5.x LTS (4.5.14, 2026-09-15) | 3.11 | manylinux_2_28 | Pick this if a dependency forces Python 3.11. |
| bpy 4.2.x LTS (4.2.23) | 3.11 | manylinux_2_28 | |
| Blender CLI tarball (`blender -b -P script.py`) | bundled | [download.blender.org/release](https://download.blender.org/release/): Blender5.2 (2026-09-15), 4.5, 5.1, 5.0 | Same features; useful if a subprocess or `--threads` control is needed. |

The version-to-ABI mapping comes from the [PyPI JSON](https://pypi.org/pypi/bpy/json) (wheel tags). Our container has glibc 2.39, so it satisfies `manylinux_2_28`.

bpy-as-module caveats ([Blender docs](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html)):

- It starts with the default cube scene. Use `read_factory_settings(use_empty=True)`.
- It behaves as if `--factory-startup` were passed.
- No crash logs are written.
- Only one .blend file can be open per process. Use `multiprocessing` for parallel jobs.
- `--threads` and `--log` are not available.
- Import `mathutils`, `bmesh` and similar modules *after* `bpy`.

### 3.2 Bone heat ("With Automatic Weights") robustness: measured

The Blender manual says automatic weights compute influence "based on the distance from those vertices to a particular bone ('bone heat' algorithm)". It also warns this "can often lead to armatures which do not deform child objects in ways you would want" ([manual](https://docs.blender.org/manual/en/latest/animation/armatures/skinning/parenting.html)).

**Benchmark** (bpy 5.2.2, 4 CPU cores, no GPU):

- A 1.8 m humanoid built from 10 intersecting closed shells (about 57k tris), plus an open zero-thickness cape and 40 tiny floating islands.
- A 15-bone biped.
- The "soup" variant splits every edge, mimicking AI GLBs that duplicate vertices at every UV seam.

| Mesh | Direct bone heat | Voxel proxy (0.015 m) → heat → Data Transfer |
|---|---|---|
| Closed intersecting shells (28k verts) | 1.46 s, **0** unweighted | remesh 0.30 s + heat 0.52 s + transfer 0.08 s, **0** unweighted |
| Plus open cape and tiny islands (29k verts) | 1.52 s, **396 unweighted** | 0.27 + 0.65 + 0.08 s, **0 unweighted** |
| Same as triangle soup (173k verts) | 0.69 s, **172,768 / 172,768 unweighted**, with "Bone Heat Weighting: failed to find solution for one or more bones" | 0.29 + 0.67 + 0.39 s, **0 unweighted** |

**Conclusion.** Never run bone heat directly on an AI mesh. Bind a voxel proxy and transfer the weights back.

The Remesh modifier's Voxel mode "uses an OpenVDB to generate a new manifold mesh… preserve the mesh's original volume". It has "Remove Disconnected", and the input "should have some thickness" ([manual](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html)).

**Choosing the voxel size.** It must be at most about one third of the smallest gap that has to stay open (legs, armpits). About **0.8% of model height** works: 0.015 m on a 1.8 m figure produced a 14k-vertex proxy.

### 3.3 Recommended rigging pipeline (most robust on our box)

1. **Normalise** the mesh with `process_model.py`: scale, feet at y=0, face -Z, decimate. Rig *after* decimation so the weights are computed on the shipped mesh.
2. **Pick a template skeleton per body type**: biped, quadruped, flyer, siege/rigid. Use fixed bone names, matching `vc_bpy.STANDARD_CLIPS` conventions.
   - Keep the templates small: about 15–25 deform bones for a biped. WC3-scale units are only about 40–80 px tall on screen.
   - **Rigify is available, but its generated rigs carry ORG/MCH/DEF control layers meant for hand animation.** Export only DEF bones ("Export Deformation Bones Only" in the glTF exporter; Godot's formats page warns that exporting non-deforming bones can cause incorrect shading with blend shapes).
   - A hand-built template made in code (as in `tools/tests/make_test_rigs.py`) is simpler for procedural animation.
3. **Fit the joints automatically from the mesh**, using the A-pose and the normalised bounds:
   - crotch: the lowest height where a horizontal slice splits into two leg islands;
   - shoulders and hands: the extreme |x| of the arm islands;
   - neck: the narrowest slice above the shoulders;
   - knees and elbows: at fixed ratios.

   Allow a per-asset JSON override for joint positions, which is a cheap manual fix. (Heuristic; unverified on real outputs.)
4. **Voxel proxy, then automatic weights, then Data Transfer to the real mesh.** Then limit to 4 influences, clean weights below 0.01, and normalise:

```python
# bpy 5.2 — tested up to the transfer step (see §3.2); cleanup ops are standard Blender operators
def bind_with_voxel_proxy(mesh, arm, voxel=0.015):
    proxy = mesh.copy(); proxy.data = mesh.data.copy(); bpy.context.collection.objects.link(proxy)
    rm = proxy.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = voxel
    bpy.ops.object.select_all(action="DESELECT"); proxy.select_set(True)
    bpy.context.view_layer.objects.active = proxy; bpy.ops.object.modifier_apply(modifier="vox")
    proxy.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")            # bone heat on a clean manifold
    for b in arm.data.bones:
        if b.use_deform: mesh.vertex_groups.new(name=b.name)
    dt = mesh.modifiers.new("dt", "DATA_TRANSFER"); dt.object = proxy
    dt.use_vert_data = True; dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"; dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.select_all(action="DESELECT"); mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh; bpy.ops.object.modifier_apply(modifier="dt")
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.01)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    mod = mesh.modifiers.new("Armature", "ARMATURE"); mod.object = arm; mesh.parent = arm
    bpy.data.objects.remove(proxy)
```

5. **Validate automatically.** Check for:
   - zero unweighted vertices;
   - posed-bounds sanity (already in `process_model.py`);
   - a contact sheet of 4 test poses rendered at the game camera.
6. **Animations: procedural keyframes in bpy per template.** Clips: idle, walk, attack, death, work, cast, birth (`vc_bpy.STANDARD_CLIPS`).
   - Share one clip set across every unit of a body type, the way WC3 reused animation sets (design inference).
   - Vary per unit through timing, amplitude and weapon arc parameters.
   - Export one glTF animation per action.
7. **Rigid fallback** for siege engines, golems and anything the fitter cannot handle: assign each vertex weight 1.0 to its nearest bone (segment animation, no blending).
   - Buildings and trees get **vertex-shader animation** in Godot instead of rigs: wind sway, construction "rise" with a clip plane, idle bob.

### 3.4 Neural auto-riggers: why not here

| Project | What it does | Hardware / dependencies | Licence | Runs on our CPU box? |
|---|---|---|---|---|
| [UniRig](https://github.com/VAST-AI-Research/UniRig) (Tsinghua + Tripo, SIGGRAPH'25) | Transformer skeleton plus skinning for humans, animals and objects; input obj/fbx/glb/vrm; output FBX, merged to GLB | "CUDA-enabled GPU with at least 8GB VRAM"; spconv, torch_scatter/cluster, flash_attn ("high chance" of install errors); Python 3.11, torch ≥ 2.3.1 | MIT | **No** (CPU not documented; CUDA-only dependencies) |
| [RigNet](https://github.com/zhan-xu/RigNet) (SIGGRAPH 2020) | Joints, hierarchy, skinning; needs 1K–5K-vertex remeshed OBJ; outputs `_rig.txt`; FBX via **Maya** | CUDA 10/11.3, Python 3.7, torch 1.12, torch-geometric 1.7.2, open3d 0.9.0, g++ < 10 | **GPL-3.0** | **No** (dated stack; GPL) |
| [MagicArticulate](https://github.com/Seed3D/MagicArticulate) (CVPR 2025) | Autoregressive skeleton generation (Articulation-XL2.0, 48k+ models) | 4.6 GB VRAM, 1–2 s per inference; torch 2.1.1 CUDA 11.8, flash-attn 2.6.3 | Apache-2.0 | **No** (flash-attn) |
| [Puppeteer](https://github.com/Seed3D/Puppeteer) (NeurIPS 2025, released 2025-09-04) | Skeleton, skinning, then video-guided animation | CUDA 11.8 torch 2.1.1, flash-attn 2.6.3, pytorch3d, bpy 4.2.0 for FBX | Apache-2.0 | **No** |

flash-attn is a CUDA kernel library, so CPU inference is not an option without code surgery. This is a widely known property and was not re-verified here.

UniRig (MIT) is the one to try **if a GPU box ever becomes available**: rent a GPU, run it batch-wise, and import the GLBs here.

**Paid or manual fallbacks.** Do not use these without the user's go-ahead.

- Meshy API auto-rig: 5 credits plus 3 per animation.
- Tripo `rig_model` with a `mixamo` spec.
- Mixamo: humanoids only, manual upload, no public API (unverified: Adobe's FAQ returned 403 to our fetch).
- Higgsfield rigging: has 0 credits.

---

## 4. Consistent style across hundreds of generations

### 4.1 Levers the Krea API actually gives us

All from model schemas, 2026-10-16.

| Model | Consistency controls | Notes |
|---|---|---|
| **Krea 2 Medium** (9 CU / $0.03) | `seed`; `image_style_references` (≤10, strength 0–1, default 0.5); `moodboards` (1, strength default 0.23 in schema); `styles` (LoRA ids, −2…2); `creativity` raw/low/medium/high (schema default `low`); sliders `intensity`, `complexity`, `movement` −100…100; img2img `image_url` + `strength` (default 0.99) | **Only 1K resolution.** Krea says Medium is "strongest on: illustration, anime, painting, and other expressive or artistic styles". Use `creativity:"raw"`, which the docs call "best for tightly art-directed prompts" ([Krea 2 overview](https://www.krea.ai/docs/developers/krea-2/overview.md)). The prose docs give `medium` as the creativity default, while the schema says `low`, so always pass it explicitly. Moodboards are made in the web app; the docs suggest starting strength about 0.35, range −0.5…1.5 ([moodboards](https://www.krea.ai/docs/developers/krea-2/moodboards.md)). Style refs: start about 0.6; make multiple refs sum to about 1.0 ([style transfer](https://www.krea.ai/docs/developers/krea-2/style-transfer.md)). That page allows −2…2 per reference, while the Krea 2 Medium schema clamps to 0–1, so stay inside 0–1. |
| Flux.1 Dev (5 CU, unverified / $0.007) | `seed` (the schema default is randomised: `get_model_schema` showed 627054708, but the OpenAPI spec shows 4113097998, so always pass a seed), `steps`, `guidance_scale` (default 3), `styles` (LoRA), `style_images`, `image_style_references`, img2img; 512–2368 px | "Best for LoRAs". The base model for a **trained** style. |
| Qwen Image 2.1 (~30 CU / $0.04) | `seed` (default 1337), `style_images` (≤3, −2…2), **`background: transparent`**, 512–2048 px | Transparent cutouts for UI pieces and sprites. |
| GPT Image 2.5 Flare (~75 CU) | `image_urls` (≤10 refs), **`background: transparent`**, `quality` low…max, 1K/2K/4K | Best instruction-following for UI frames with exact layout (vendor claim). |
| Nano Banana Pro (~110 CU / $0.15) | `image_urls` (up to 4 refs per Krea docs), 1K/2K/4K | Identity-preserving edits and turnarounds; good text rendering ([NB Pro](https://www.krea.ai/docs/user-guide/features/nano-banana-pro.md)). Expensive. |

**Trained style (LoRA)** ([Krea training tutorial](https://www.krea.ai/docs/developers/tutorials/train-image-style.md)):

- Base models: `flux_dev` (default), `flux_schnell`, `qwen`, `z-image`, `wan22`. **Krea 2 is not trainable.**
- Dataset: 10–30 images recommended (5 minimum), at least 1024², consistent style, no watermarks.
- Steps: 500–800 for 15–30 images; learning rate 3e-4 by default. Training takes 5–15 minutes.
- Inference strength: start at 0.8.
- Training cost is not documented (unverified).

**Recommendation.** Do not train first. Lock the look with Krea 2 Medium plus 3–5 **style anchor images**. These are our own best approved generations: one unit, one building, one terrain tile, one icon. Pass them as `image_style_references` (for example 0.35 + 0.35 + 0.3).

Train a Flux LoRA only if drift appears after about 50 assets. Flux generations then cost only 5 CU, so a LoRA pays for itself in volume.

**Fixed recipe per asset family.** Keep a JSON file in `tools/` (proposal) holding:

```text
prompt = <subject clause> + <family clause> + GLOBAL_STYLE_SUFFIX (art doc §7.3)
model = krea/krea-2/medium, creativity = "raw", aspect_ratio fixed per family,
image_style_references = [anchor_unit 0.35, anchor_building 0.35, anchor_palette 0.3],
seed = family_seed (+ i for variants)
```

Log every generation's full request and job id in the ledger, so a good result can be reproduced or varied by seed.

**Palette discipline happens in post, not in the prompt.** Remap generated images toward the faction and biome palette with a 3D LUT and clamp saturation and value per asset class (art doc §7.4). This is what makes 200 images from 4 models look like one game.

### 4.2 Concept art and turnaround sheets

- **Faction lineup sheet:** one Krea 2 Medium 16:9 image per faction, "character lineup of [5 units], same scale, A-pose, plain grey background". This gives the faction a shared silhouette language and palette. Crops of it become that faction's style anchors.
- **Per-unit concept:** 1:1 or 3:4, A-pose, front three-quarter (§2.2). This image *is* the image-to-3D input. No separate "concept vs. model sheet" step is needed.
- **Hero turnarounds** (multi-view for Hunyuan Pro): feed the approved front image to Nano Banana Pro or GPT Image 2.5 as a reference. Ask for "same character, exact same design, orthographic left side view, A-pose, plain grey background", once per needed view. Budget about 3 × 75–110 CU per hero, so only do this for heroes.

### 4.3 Seamless and tileable terrain textures

**Prompt** (from art doc §7.3, plus additions):

> seamless tileable hand-painted ground texture, top-down orthographic, [short meadow grass with small clover clumps], soft painterly strokes, low contrast, mid value, even flat lighting, no perspective, no horizon, no shadows from objects, uniform density edge to edge, no central focal object, + style suffix

- Generate **2×2 variant grids** ("four separate square swatches of … in a 2x2 grid with thin gaps"). One 9-CU image then yields 4 tiles at 512 px each.
  - At 2 m per tile and 128 px/m (art doc §7.4), a 256–512 px tile is enough.
  - The grid layout is unverified for every model. Fall back to one tile per image.
- Never trust "seamless" in a prompt: **always post-process.**

**Post-process: offset-and-blend.** Tested on a synthetic non-tileable 512² texture: the wrap-seam ratio went from **22.19 to 1.22** (1.0 means as seamless as the interior):

```python
import numpy as np
from PIL import Image

def make_tileable(img, blend=0.25):
    a = np.asarray(img.convert("RGB"), np.float32); h, w, _ = a.shape
    s = np.roll(a, (h // 2, w // 2), axis=(0, 1))          # wrapped copy: borders now continuous
    def ramp(n):
        b = max(1, int(n * blend)); r = np.ones(n, np.float32)
        t = np.linspace(0, 1, b, dtype=np.float32); t = t * t * (3 - 2 * t)
        r[:b] = t; r[-b:] = t[::-1]; return r
    m = np.minimum.outer(ramp(h), ramp(w))[..., None]        # 1 in centre, 0 at borders
    return Image.fromarray(np.clip(a * m + s * (1 - m) + .5, 0, 255).astype(np.uint8))
```

Notes:

- Blending can cause ghosting or doubled features in the blend band, and some contrast loss there.
  - Keep `blend` at 0.15–0.25.
  - Generate low-contrast, high-frequency, focal-point-free content.
  - Re-apply a light unsharp mask afterwards.
- **Higher-quality alternative** (costs CU):
  1. `np.roll` the image by half, so the seams form a cross in the middle.
  2. Repaint only a cross-shaped mask band (about 10% width) with a masked inpaint model. On Krea that is Ideogram 4.5 Precise, which "supports optional masks", at $0.008–0.22 per request.

  The image borders are untouched, so the result tiles exactly. Unmasked edit models (Nano Banana, Kontext) regenerate the whole image and can break the wrap.
- In Godot, hide repetition in the terrain shader instead of making bigger textures:
  - world-space UVs plus a low-frequency macro-variation noise multiply;
  - 2–3 rotated or offset samples blended by noise ("texture bombing", standard technique).

### 4.4 128×128 icons with consistent frames

- **Never let the model draw the frame.** Frames drift in thickness and ornament between generations. Generate only the subject:
  > square fantasy game ability icon, [subject], bold single central silhouette filling 70% of the square, painted, strong value contrast, glowing [colour] accent, simple dark vignette background, no border, no frame, no text
- **Grid trick:** prompt a "2x2 grid of four separate icons" at 1:1 1K. That gives 4 icons per 9 CU, each at about 512 px before downscaling (unverified per model; fall back to 1 per image).
- **Post-process** (tested on a synthetic sheet; produces correct 128×128 RGBA output):
  1. Split the grid.
  2. Trim 6% gutters.
  3. Fit to 116×116 with Lanczos and apply unsharp mask (r=1, 80%).
  4. Paste onto black.
  5. Alpha-composite **one shared hand-made 128×128 frame PNG** (opaque 6 px border, transparent centre).
  6. Derive the **disabled** variant (greyscale × 0.55 brightness), plus hover and pressed variants, procedurally.

```python
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
def make_icon(art, frame, icon=128, inner=116):
    art = ImageOps.fit(art.convert("RGB"), (inner, inner), Image.LANCZOS)
    art = art.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=2))
    out = Image.new("RGBA", (icon, icon), (0, 0, 0, 255)); o = (icon - inner) // 2
    out.paste(art, (o, o)); out.alpha_composite(frame.convert("RGBA")); return out
def disabled(icon):
    return ImageEnhance.Brightness(ImageOps.grayscale(icon.convert("RGB")).convert("RGBA")).enhance(0.55)
```

- Godot import for icons: **Lossless, no mipmaps** (the 2D default). Detect 3D would switch textures to VRAM Compressed with mipmaps, which suits 3D, not UI ([Godot image import](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html)).
- Make the frame family (normal, hero, autocast or passive variants) once, by hand or by script, as original art. Do not imitate Blizzard's gold-and-stone chrome (video-references §IP).

### 4.5 UI frame art (9-slice)

1. **Generate** one ornate panel per style with **GPT Image 2.5 Flare** (`background: "transparent"`, ~75 CU) or **Qwen Image 2.1** (`background: "transparent"`, ~30 CU, plus ≤3 style images). Prompt:
   > flat front-on orthographic UI panel frame for a fantasy strategy game, rectangular, perfectly symmetric, ornate carved [wood/bronze/stone] border of uniform thickness, empty plain dark centre, no text, no perspective, transparent background
2. **Enforce symmetry in post.** Mirror the left half onto the right and the top half onto the bottom. This guarantees four identical corners and straight edges.
3. **Cut the margins.** Measure the border thickness (for example 48 px at 1K) and set Godot `NinePatchRect.patch_margin_left/top/right/bottom` (or `StyleBoxTexture` texture margins) to it.
   - `axis_stretch_horizontal/vertical`: STRETCH (0), TILE (1) or TILE_FIT (2).
   - **TILE and TILE_FIT require a seamless centre and edges** ([NinePatchRect](https://docs.godotengine.org/en/stable/classes/class_ninepatchrect.html)). For TILE, run a 1-D version of §4.3 on the edge strips.
   - `draw_center = false` gives border-only frames.
4. Downscale to the target UI scale (for example 2× the logical size for HiDPI). Import as Lossless.

---

## 5. Krea image model guide for our tasks

| Task | Model | Why (vendor and Krea docs) | Cost |
|---|---|---|---|
| Unit and building concepts (image-to-3D inputs), terrain, icons, concept sheets | **Krea 2 Medium** | "Best for expressive illustrations"; style refs, moodboards and LoRAs; cheapest quality option | 9 CU / $0.03–0.04 |
| Bulk drafts, LoRA-styled volume | Flux.1 Dev | "Best for LoRAs", cheapest | 5 CU / $0.007 |
| Transparent sprites and UI parts | Qwen Image 2.1 | "Transparent assets and identity-safe edits" | ~30 CU / $0.04 |
| Precise UI layouts, transparent cut-outs, multi-reference | GPT Image 2.5 Flare | "transparent background support", ≤10 refs, 1K–4K | ~75 CU |
| Identity-consistent turnarounds and edits | Nano Banana Pro (or Nano Banana 2.1 at $0.03 for 1K, untested) | Up to 4 refs, strong editing and consistency | ~110 CU / $0.15 |
| Masked seam repair, inpainting | Ideogram 4.5 Precise | Masks plus reference images, preserves resolution | $0.008–0.22 |
| Fast graphic or flat design iteration | Recraft V4.1 Flash | "fast tier for raster art, illustration" | 5 CU / $0.007 |
| Logos or text on banners (avoid; we render text in Godot) | Qwen Image 3 / Ideogram | Text rendering | — |

---

## 6. Post-processing toolchain (pip, Linux)

From the PyPI JSON API on 2026-10-16. Tests were run in a scratch venv on Python 3.13.

| Package | Latest | Py 3.13 wheel | Use | Caveats seen here |
|---|---|---|---|---|
| bpy | 5.2.2 | yes (3.13 only) | Everything mesh, rig and animation; GLB in and out (reads Draco on import) | 402 MB wheel; already installed |
| trimesh | 5.1.1 | pure Python | Inspection, bounds, collision hulls, quick stats | Decimation drops UVs (tested) |
| fast-simplification | 0.2.0 | yes (manylinux_2_28) | Backend for trimesh decimation | Geometry only |
| pymeshlab | 2025.7.post1 | yes (manylinux_2_35) | Remeshing and repair filters | **Meshing filters do not load without `libOpenGL.so.0`** |
| pygltflib | 1.16.5 | pure Python | Read and patch GLB JSON: check `extensionsRequired`, rename materials, strip extras | — |
| Pillow 12.3 + numpy | — | yes | All 2D post (§4) | — |
| open3d | 0.20.0 | yes (manylinux_2_35) | Optional point and mesh utilities | Large; not needed |
| meshoptimizer (PyPI) | 0.2.30a0 | sdist only (alpha) | — | Avoid; Godot already uses meshoptimizer internally for LODs |

---

## 7. Godot 4.7 import settings for our GLBs

**glTF extension support.** In Godot 4.7.2 (`GLTFDocument.get_supported_gltf_extensions()`, run in this container), the supported extensions are:

`EXT_texture_webp`, `GODOT_single_root`, `KHR_animation_pointer`, `KHR_lights_punctual`, `KHR_materials_emissive_strength`, `KHR_materials_pbrSpecularGlossiness`, `KHR_materials_unlit`, `KHR_node_visibility`, `KHR_texture_basisu`, `KHR_texture_transform`, `OMI_collider`, `OMI_physics_body`, `OMI_physics_shape`.

- **No `KHR_draco_mesh_compression`, no `EXT_meshopt_compression`, no `KHR_mesh_quantization`.** If an AI GLB lists one of these in `extensionsRequired`, it must go through Blender first (pygltflib can detect this).
- WebP textures, which TRELLIS can emit, are fine.

**Recommended `.import` values** (option names from [ResourceImporterScene](https://docs.godotengine.org/en/stable/classes/class_resourceimporterscene.html)):

| Option | Units (skinned) | Buildings / doodads | Why |
|---|---|---|---|
| `nodes/root_scale` | 1.0 | 1.0 | `process_model.py` already bakes 1 unit = 1 m |
| `nodes/apply_root_scale` | true | true | Default |
| `meshes/generate_lods` | **false** | **true** | Docs: LOD generation "may occasionally introduce rendering issues (especially in skinned meshes)". Units are already 2–8k. Buildings and trees gain from meshoptimizer LODs ([Mesh LOD](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)). |
| `meshes/create_shadow_meshes` | true | true | Default; welds vertices for cheaper shadow passes |
| `meshes/ensure_tangents` | **false** | **false** | No normal maps in the hand-painted style; smaller files and faster import |
| `meshes/force_disable_compression` | false | false | Compression is on by default. Set true only if normals or UVs look blocky. |
| `meshes/light_baking` | Disabled/Dynamic | Static Lightmaps only if we bake | We rely on painted lighting |
| `skins/use_named_skins` | true | — | Default; robust bone binding |
| `animation/fps` | 30 | — | Docs: "not much benefit in going above 30 FPS" |
| `animation/trimming`, `remove_immutable_tracks` | true, true | — | Smaller clips |
| `import_script/path` | `res://tools/import/unit_post_import.gd` (proposal) | same | Swap in the shared team-colour `ShaderMaterial` for materials named `*_TEAM`; set `lod_bias`; assign collision |
| glTF "Embedded Texture Handling" | **Extract Textures** | Extract Textures | Docs: gives "smaller file sizes and more control over import options" (VRAM compression, mipmaps). Embed as Basis Universal is the alternative. |

**Textures.**

- 3D textures: **VRAM Compressed with mipmaps** (what Detect 3D switches to), with anisotropic filtering in the material.
- UI and icons: Lossless without mipmaps.
- Terrain: VRAM Compressed, repeat enabled.

**LOD tuning.**

- The project setting `rendering/mesh_lod/lod_change/threshold_pixels` defaults to 1 px ("perceptually lossless"). Raise it to 2–4 for the zoomed-out RTS view if we are vertex-bound.
- Per-node `lod_bias`: above 1 means later and higher quality; below 1 means sooner.
- LOD selection uses the AABB point closest to the camera. All instances in one `MultiMeshInstance3D` share one LOD level, so split forests into several MultiMesh chunks.

**Headless reimport in CI.** Godot 4.7.2 has `--import` ("Starts the editor, waits for any resources to be imported, and then quits"). Combine it with `--headless`.

---

## 8. End-to-end pipeline (proposal)

| # | Step | Tool | Output | Cost |
|---|---|---|---|---|
| 1 | Approve 3–5 style anchors (unit, building, terrain, icon) | Krea 2 Medium | `assets/_refs/anchor_*.png` | ~5 × 9 CU |
| 2 | Concept per asset: A-pose 3/4 view on grey (units), 35–45° view (buildings) | Krea 2 Medium + style refs + fixed suffix + seed | `assets/_src/<id>/concept.png` | 9 CU each |
| 3 | Approve by silhouette and greyscale check (art doc §7.4) | Pillow script | pass/fail | 0 |
| 4 | Image-to-3D, **async**, log job id | Tripo H3.1 `face_limit` 10k (default choice) | raw GLB | ~148 CU |
| 5 | Normalise, clean, decimate, texture downscale with dilation, team mask, backface culling | `process_model.py` (bpy 5.2.2) | game GLB | 0 |
| 6 | Rig: template skeleton, landmark fit, voxel proxy, bone heat, Data Transfer, limit 4 | new `rig_model.py` (bpy) | rigged GLB | 0 |
| 7 | Animate: procedural clips per template, merged into the GLB | `merge_anims.py` / new `anim_*.py` | GLB with 7 clips | 0 |
| 8 | Validate: unweighted = 0, posed bounds, contact-sheet render at game camera | bpy (Workbench/Eevee CPU) or Godot headless | PNG sheet | 0 |
| 9 | Import with the `.import` presets above; `godot --headless --import` | Godot 4.7.2 | `.scn` | 0 |
| 10 | Doodads: procedural bpy geometry plus Krea textures; terrain tiles via §4.3; icons via §4.4; UI via §4.5 | bpy + Pillow | assets | 9 CU per sheet |

---

## 9. Open questions and unverified items

- Krea CU prices for Meshy 7, Rodin 2.5 and GPT Image 2.5 Flare, and USD prices for Tripo H3.1, Hunyuan 3.1 Pro, TRELLIS 2, Meshy 7 and Flare. A single probe job, or the Krea app's cost preview, would settle each.
- Whether Krea's Meshy 7 wrapper honours `target_polycount` (Meshy upstream needs `should_remesh: true`).
- Whether Tripo H3.1's `face_limit` counts triangles or quads in the output.
- The quality ranking of the 3D generators for *stylized* inputs. There are no independent sources this run; use the bake-off in §2.6.
- Mixamo API status (Adobe FAQ fetch returned 403).
- Rigify's manual page moved (404 at the old URL). The add-on is confirmed present in bpy 5.2.2.
- Whether one 1K Krea 2 Medium image reliably yields a clean 2×2 grid.
- Whether the legacy 3D models (Tripo 8 CU, TRELLIS v1 10 CU, Hunyuan3D-2.1 25 CU) cost the same CU over OAuth MCP as in the web app, and whether their "Medium" quality survives decimation to 2–4k tris for stylized units.
- Which Tripo version backs the legacy `tripo/tripo` endpoint (unverified).

### 9.1 Fact-check log (2026-10-16)

An adversarial pass checked the load-bearing claims against the live sources. Web search was unavailable (budget exhausted), so checks used direct fetches, the Krea OpenAPI spec, Krea `list_models`, the PyPI JSON API and Godot 4.7.2 run in this container.

**Verified:**

- Krea USD prices: Krea 2 Medium/Turbo/Large, Flux.1 Dev, Qwen 2.1, Recraft, Nano Banana 2/2.1/Pro, Ideogram 4.5 Precise, Rodin 2.5 and Fast, Hunyuan 3.1 Rapid.
- Krea API billing: presets, $5–$10,000 custom top-up, failed jobs not billed, HTTP 402, token vs OAuth MCP billing.
- 90-day compute packs, and no rollover on individual plans.
- 3D schema limits: `face_limit` 1,000–2,000,000; `face_count` ≥ 40,000; `decimation_target` ≥ 100,000; `target_polycount` 100–300,000; Rodin ≤ 5 images.
- TRELLIS.2: 4B parameters, MIT, 3/17/60 s on an H100, ≥ 24 GB, 1M-face / 4096 export defaults, OPAQUE alpha.
- Meshy: should_remesh default false for Meshy 6/7, meshy-7 deprecated in favour of 7.1, t2/t2.5 ranges, 5-credit auto-rig, 3 credits per animation.
- Rodin Gen-2.5: tiers, Raw/Quad, fast mode at `quality_override` ≤ 20000, 2K–12K textures.
- Tripo SDK model versions and `rig_model` specs.
- UniRig, RigNet, MagicArticulate and Puppeteer hardware, versions, licences and venues.
- Hunyuan3D 2/2.1 VRAM: 6–29 GB.
- bpy: wheel tags, Python ABIs and release dates. Blender 5.2 and 4.5 are both current LTS.
- bpy-as-module caveats.
- Blender manual quotes on bone heat and Remesh.
- PyMeshLab "bad spikes" quote; trimesh `simplify_quadric_decimation` signature.
- Package versions: trimesh 5.1.1, pymeshlab 2025.7.post1, pygltflib 1.16.5, open3d 0.20.0, meshoptimizer 0.2.30a0, Pillow 12.3.0.
- Godot docs: LOD skinned-mesh warning, 1 px threshold, MultiMesh shared LOD, animation FPS quote, Extract Textures quote, culling and deform-bones warnings, NinePatchRect enums, Detect 3D behaviour, and the `--import` text.
- The Godot 4.7.2 glTF extension list, re-run here.

**Corrected:**

- Omitted cheap 3D models: Tripo legacy, TRELLIS v1 and Hunyuan3D-2.1.
- "Cheapest 3D = Rodin Fast": TRELLIS v1 at $0.02 is cheaper.
- "All six take `seed`": Rapid has no seed.
- Flux seed "fixed default": it is randomised.
- Flux.1 Dev 5 CU attribution: now unverified.
- Krea 2 creativity default conflict, and the style-ref strength ranges.
- Meshy quote wording, the 512 px recommendation, and the 3mf output.
- Meshy credit range.
- Basic-plan price: it is in structured data only.
- 4 Influences: a `.blend` importer option.

**Still unverified:** Mixamo API status (could not search).

---

## Sources

**Krea (docs, API and live schemas)**
- [Krea docs index (llms.txt)](https://www.krea.ai/docs/llms.txt)
- [Krea API keys and billing](https://www.krea.ai/docs/developers/api-keys-and-billing.md)
- [Krea compute units guide](https://www.krea.ai/docs/user-guide/help-and-support/compute-units.md)
- [Krea model overview (credit costs)](https://www.krea.ai/docs/user-guide/features/model-overview.md)
- [Krea 3D utilities](https://www.krea.ai/docs/user-guide/features/3d.md)
- [Krea 3D generation](https://www.krea.ai/docs/3-d.md)
- [Krea API feature page (USD prices)](https://www.krea.ai/features/api)
- [Krea pricing (plans)](https://www.krea.ai/pricing)
- [Krea 2 API overview](https://www.krea.ai/docs/developers/krea-2/overview.md)
- [Krea 2 moodboards](https://www.krea.ai/docs/developers/krea-2/moodboards.md)
- [Krea 2 style transfer](https://www.krea.ai/docs/developers/krea-2/style-transfer.md)
- [Krea: train a custom style](https://www.krea.ai/docs/developers/tutorials/train-image-style.md)
- [Krea: Nano Banana Pro](https://www.krea.ai/docs/user-guide/features/nano-banana-pro.md)
- Krea API reference pages:
  - [Tripo H3.1](https://www.krea.ai/docs/api-reference/3d/tripo-h31.md)
  - [Hunyuan3D 3.1 Pro](https://www.krea.ai/docs/api-reference/3d/hunyuan3d-31-pro.md)
  - [Hunyuan3D 3.1 Rapid](https://www.krea.ai/docs/api-reference/3d/hunyuan3d-31-rapid.md)
  - [TRELLIS 2](https://www.krea.ai/docs/api-reference/3d/trellis-2.md)
  - [Meshy V7](https://www.krea.ai/docs/api-reference/3d/meshy-v7.md)
  - [Rodin V2.5](https://www.krea.ai/docs/api-reference/3d/rodin-v25.md)
  - [GPT Image 2.5 Flare](https://www.krea.ai/docs/api-reference/image/gpt-image-25-flare.md)
  - [Qwen Image 2.1](https://www.krea.ai/docs/api-reference/image/qwen-image-21.md)
- [Krea OpenAPI spec (x-krea-pricing)](https://api.krea.ai/openapi.json)
- Krea MCP `list_models`, `get_model_schema` and `get_balance` (live, 2026-10-16)

**3D generator vendors**
- [Meshy API: Image to 3D](https://docs.meshy.ai/en/api/image-to-3d)
- [Meshy API pricing](https://docs.meshy.ai/en/api/pricing)
- [Meshy web app: Image to 3D best practices](https://docs.meshy.ai/en/webapp/image-to-3d)
- [Tripo Python SDK](https://github.com/VAST-AI-Research/tripo-python-sdk)
- [Tripo SDK API reference](https://github.com/VAST-AI-Research/tripo-python-sdk/blob/master/docs/API.md)
- [Hyper3D Rodin docs](https://docs.hyper3d.ai/)
- [Rodin Gen-2.5 API spec](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)
- [Microsoft TRELLIS.2](https://github.com/microsoft/TRELLIS.2)
- [Tencent Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- [Tencent Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)

**Rigging**
- [UniRig](https://github.com/VAST-AI-Research/UniRig)
- [RigNet](https://github.com/zhan-xu/RigNet)
- [MagicArticulate](https://github.com/Seed3D/MagicArticulate)
- [Puppeteer](https://github.com/Seed3D/Puppeteer)
- [Blender manual: Armature Deform Parent (automatic weights)](https://docs.blender.org/manual/en/latest/animation/armatures/skinning/parenting.html)
- [Blender manual: Remesh modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html)
- [Blender as a Python module](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html)
- [Blender release downloads](https://download.blender.org/release/)
- [Blender LTS releases](https://www.blender.org/download/lts/)
- [PyPI: bpy (JSON API)](https://pypi.org/pypi/bpy/json)

**Mesh and image tools**
- [PyMeshLab filter list](https://pymeshlab.readthedocs.io/en/latest/filter_list.html)
- [trimesh.base docs](https://trimesh.org/trimesh.base.html)
- PyPI JSON for:
  - [pymeshlab](https://pypi.org/pypi/pymeshlab/json)
  - [trimesh](https://pypi.org/pypi/trimesh/json)
  - [fast-simplification](https://pypi.org/pypi/fast-simplification/json)
  - [pygltflib](https://pypi.org/pypi/pygltflib/json)
  - [open3d](https://pypi.org/pypi/open3d/json)
  - [meshoptimizer](https://pypi.org/pypi/meshoptimizer/json)

**Godot**
- [ResourceImporterScene](https://docs.godotengine.org/en/stable/classes/class_resourceimporterscene.html)
- [Import configuration](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/import_configuration.html)
- [Available 3D formats](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html)
- [Mesh LOD](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)
- [Importing images](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html)
- [NinePatchRect](https://docs.godotengine.org/en/stable/classes/class_ninepatchrect.html)

**Project-internal**
- `docs/asset-ledger.md` (measured CU)
- `docs/research/visual-art-direction.md` §3.1, §7.3–7.5
- `docs/research/audio-direction.md` §4
- `tools/process_model.py`
- `tools/vc_bpy.py`
- `tools/tests/make_test_rigs.py`

**Empirical tests run for this doc** (2026-10-16, this container): bpy 5.2.2 bone-heat vs voxel-proxy benchmark; trimesh and fast-simplification UV check; pymeshlab plugin load; Godot 4.7.2 glTF extension list and `--import` flag; tileable-texture seam metric; icon-sheet cutter.
