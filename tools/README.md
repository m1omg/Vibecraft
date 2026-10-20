# Vibecraft asset tools

Offline tools that turn AI-generated art (Tripo / Meshy / Hunyuan GLBs, 1024 px PNGs) into
game-ready assets for the Godot 4.7 project, plus a visual QA renderer. Nothing here calls a
paid generation API.

| Tool | Interpreter | What it does |
|---|---|---|
| `process_model.py` | bpy | GLB → one mesh (+armature), cleanup, decimate, recentre, scale, face −Z, textures ≤1024, stable names, team mask, GLB |
| `merge_anims.py` | bpy | several single-clip GLBs of one rigged character → one GLB with clips `idle walk attack death …` |
| `retarget_anims.py` | bpy | copy clips between rigs with the same bone names but different proportions (rotation-only) |
| `autorig.py` | bpy | **free auto-rig**: static character GLB → template skeleton fitted to the mesh, bone-heat skin, library clips, game-ready GLB + QA |
| `texture_tools.py` | python3 | `seamless`, `tile-preview`, `seam-score`, `resize`, `array`, `atlas`, `icon`, `palette-match` |
| `render_preview.py` | python3 + Godot | load a GLB through `GLTFDocument` (load check + JSON report) and render a labelled contact sheet |
| `kits/doodads.py` | bpy | procedural Greenvale doodads, trees + LODs and neutral structures (see "Procedural doodad kit") |
| `kits/lineup.py` | python3 + Godot | line-up render of the kit at the real RTS camera |
| `kits/buildings.py` | bpy | procedural faction buildings: every [SLICE] kingdom / clans building + the T2 hall add-ons (see "Procedural building kit") |
| `kits/siege.py` | bpy | procedural siege vehicles: the Bombard Wagon and the Sling-Cart as multi-node GLBs (see "Procedural siege kit") |
| `vc_bpy.py` | (library) | shared Blender helpers: import/export, actions/NLA, retarget math |
| `preview/` | Godot | tiny separate Godot project used by `render_preview.py` (`inspect.gd`, `turntable.gd`) |
| `tests/` | bpy / bash | synthetic rigged characters and props, retarget checker, `run_all.sh` end-to-end test, `test_autorig.sh` |
| `assets/check_team_coverage.gd` | Godot (headless) | **team-colour check**: measures every unit model's team share of its visible silhouette from the game camera (software raster of the rest pose, 8 yaws, the shader's mask + magenta key) and fails models outside the art bible §3.1 range (units 10–15 %, workers ≥ 8 %, heroes ≤ 18 %, a team area in the upper third). `-- --write` refreshes `assets/models/units/team_coverage.json` (the game strengthens the team rim of under-covered models from it); see "Team-colour check" |
| `music/` | python3 + fluidsynth + ffmpeg | **composed music**: `score.py` composition API, `synths.py` numpy instruments, `palette.py`, `render.py` stems → mix → master → Ogg (see "Music toolkit") |

`bpy` = Blender as a Python module: `/opt/bpyenv/v313/bin/python` (bpy 5.2 LTS, Pillow, numpy).
The bpy tools also work as `blender -b -P tool.py -- <args>`. Every tool has `--help`, prints a
JSON summary on stdout (logs go to stderr), overwrites its outputs, and gives byte-identical
output for identical inputs and arguments. The bpy build has no Draco/meshopt libraries; the
`ERROR Draco is not available` lines on stderr are harmless (we never compress).

## Conventions (what the game can rely on)

| Thing | Convention |
|---|---|
| Units | 1 unit = 1 m, Y up (Godot) |
| Origin | bottom centre of the bounding box: feet / base on `y = 0`, centred in X/Z |
| **Facing** | **models face −Z** (Godot forward, same as `Node3D.look_at()` and `Unit.facing`, forward = `(-sin f, 0, -cos f)`). Put the GLB under the unit node with no extra rotation. Raw AI models face +Z (glTF convention), so `process_model.py` turns them 180° by default (`--facing +z`). |
| Size | characters by `--height`, buildings by `--width` (largest horizontal extent = footprint) |
| Node names | static: one `MeshInstance3D` named `<name>`; rigged: `Armature/Skeleton3D/<name>` (`--name`, default: output file stem) |
| Materials | `<name>` (or `<name>_0`, `<name>_1` … for several); with `--team-mask`, the team-coloured faces get their own material `<name>_TEAM` |
| Textures | embedded, ≤ `--tex-size` (1024), named `<material>_basecolor`, `_normal`, `_orm`, `_emission`; JPEG q90 for opaque colour maps, PNG for alpha/data maps |
| Team colour | `--team-mask HUE`: faces whose texels have that hue move to material `<name>_TEAM` (same textures); the per-texel mask is also written as `<out>_team.png` (L8, base-colour UVs, 255 = team) for a future shader |
| Clips | one glTF animation per clip, names from `idle walk attack death work cast birth`; start at t = 0; 30 fps sampling |
| Skin | ≤ 4 influences per vertex, normalized (Godot default) |

Game-side notes for `UnitView`:
* glTF has no loop flag, so set `Animation.loop_mode = LOOP_LINEAR` on `idle`, `walk`, `work`
  after loading (GLTFDocument and the editor importer both import clips as non-looping).
* Team colour works with the current `UnitView._apply_team_color()` as is: it multiplies the
  albedo of materials whose name contains `TEAM`, and `process_model --team-mask` puts exactly the
  team faces into `<name>_TEAM`. Use `--team-desaturate` so those texels are grey and the multiply
  gives a clean player colour. The split is per face (at 4–6k tris the edge of a team area follows
  the triangles); for texel-exact edges a shader can use `<model>_team.png`:
  `albedo = mix(albedo, luminance(albedo) * team_color, mask)`. `render_preview.py` tints `TEAM`
  materials blue (`--team-color`) so the split is visible on the sheet.

## Recipes

Set `PY=/opt/bpyenv/v313/bin/python` first.

### Static prop or building
```bash
$PY tools/process_model.py raw/boulder.glb -o assets/models/boulder.glb \
    --target-tris 3000 --height 1.2 --cleanup
$PY tools/process_model.py raw/barracks.glb -o assets/models/barracks.glb \
    --target-tris 8000 --width 4.0 --cleanup          # 8x8 cells = 4 m footprint
python3 tools/render_preview.py assets/models/boulder.glb -o /tmp/boulder_sheet.png
```
If the sheet shows the wrong side at the red arrow, rerun with `--facing=-x`, `--facing x+`,
`--facing=-z` (input already faces −Z) or a free `--yaw DEG` (CCW seen from above, applied after
`--facing`).

### Rigged character from Meshy (one clip per file)
```bash
# 1. the mesh: decimate/scale/turn the rig once (any of the files; animation is dropped later)
$PY tools/process_model.py raw/soldier_idle.glb -o build/soldier_base.glb --name soldier \
    --target-tris 6000 --height 1.8 --symmetry x --team-mask 300 --team-desaturate
# 2. all clips onto that base, straight from the raw files
$PY tools/merge_anims.py -o assets/models/soldier.glb --base build/soldier_base.glb \
    --clip idle=raw/soldier_idle.glb --clip walk=raw/soldier_walk.glb \
    --clip attack=raw/soldier_attack.glb --clip death=raw/soldier_death.glb
cp build/soldier_base_team.png assets/models/soldier_team.png   # optional texel mask
python3 tools/render_preview.py assets/models/soldier.glb -o /tmp/soldier_sheet.png
```
`merge_anims` copies bone-local keys verbatim when the clip's skeleton matches the base
(always true for files of one character; `process_model`'s scale/turn doesn't change bone-local
rests) and rescales hip translation by the bone-length ratio, so it doesn't matter that the base
was rescaled. If a clip file's rest pose differs by more than `--rest-tolerance` degrees it is
retargeted instead (warning). `--clip NAME=FILE:ACTION` picks one action when a file has several.

### Share clips between two rigged characters (same bone names, different proportions)
```bash
$PY tools/retarget_anims.py --source assets/models/soldier.glb --target build/dwarf_base.glb \
    -o assets/models/dwarf.glb --clip attack --clip death=death --hips-mode vertical
```
Rotation-only, world-space: each matched bone gets the source bone's world rotation relative to
its rest pose (so bone-axis conventions don't matter); unmatched target bones follow their parent.
Only hip translation is kept (`vertical` default; `full` for clips that travel, e.g. falling back
in `death`; `none`), scaled by the leg-length ratio. A facing difference between the rigs is
detected from `Left*`/`Right*` bones and removed. `mixamorig:`-style prefixes/case are ignored;
`--map TGT=SRC` adds explicit pairs.

### Unrigged character
Just `process_model.py`; the game falls back to procedural motion (bob, lean, lunge, topple).

### Terrain textures
```bash
python3 tools/texture_tools.py seamless raw/grass.png raw/dirt.png raw/rock.png \
    --out-dir build/terrain --preview                  # *_tile2x2.jpg to eyeball
python3 tools/texture_tools.py palette-match build/terrain/dirt.png build/terrain/rock.png \
    --ref build/terrain/grass.png --out-dir build/terrain_matched --strength 0.4
python3 tools/texture_tools.py array build/terrain/grass.png build/terrain_matched/dirt.png \
    build/terrain_matched/rock.png -o assets/textures/terrain_array.png --size 1024 --godot-import
```
`seamless` (default `crossfade`): the outer `--blend` (12.5 %) of each edge is cross-faded into
the opposite edge with variance-preserving blending (no soft band, no mirror symmetry) and the
result is resampled back to the input size. `--flatten auto` (default) first removes large
lighting gradients/vignettes (score `unevenness` > 0.08), which otherwise show as a grid even
without seams. `--method mirror` is the classic 4-quadrant mirror (always seamless, visibly
symmetric). The JSON reports `seam` scores before/after: wrap-around difference ÷ neighbouring
difference, ~1.0 = invisible, > 1.5 = visible. `seam-score` and `tile-preview` work on any image.

`array` stacks layers top-to-bottom (layer *i* = input *i*); `--godot-import` writes the
`.png.import` (`importer="2d_array_texture"`, `slices/vertical=N`) so the editor imports a
`CompressedTexture2DArray` (verified: 3 layers, mipmaps). `atlas` builds a grid + JSON of pixel
rects and UVs (`--padding` edge-extends cells against mip bleeding).

### Icons
```bash
python3 tools/texture_tools.py icon raw/soldier_concept.png -o assets/icons/soldier \
    --frame "#b08d3c" --disabled        # soldier_128.png soldier_64.png (+ _dis variants)
```
`--crop auto` trims the uniform background (or alpha) and centres the subject with `--pad`;
`center`, `none` or `x,y,w,h` are alternatives; `--zoom` tightens/loosens. The frame is a
bevelled border (light top-left, dark bottom-right, dark outlines) at `--bevel` × size.

### Visual QA of any GLB
```bash
python3 tools/render_preview.py model.glb -o sheet.png [--fractions 0,0.5,1] [--clips idle,walk]
python3 tools/render_preview.py --info-only assets/models/*.glb   # headless load check only
```
Row 1: RTS camera (56° pitch, from the model's front), front, side, back ¾, and an in-game 256 px
crop taken with the real RTS camera (pitch 56°, FOV 47°, 26 m, 1920×1080) at true pixel size.
Next rows: every clip at the given fractions of its length. A 1.8 m capsule stands next to the
model, ground lines are 1 m (dark lines every 2 m = terrain TILE), the red arrow points along
−Z (where the model must face). Under the hood: `xvfb-run godot --rendering-driver vulkan
--path tools/preview -s turntable.gd` (lavapipe ICD set automatically) renders frames, Pillow
composes the sheet. Exit code 1 if Godot fails to load the file or prints `ERROR` lines.
~15 s per model with software Vulkan.

## Procedural doodad kit (`tools/kits/`)

Greenvale doodads and neutral structures built entirely in bpy (no paid API calls), from the repo's painted
swatches, terrain textures and foliage cards plus procedurally painted textures. Deterministic: re-running
gives byte-identical GLBs and manifest.

```bash
$PY tools/kits/doodads.py                          # all 47 assets + assets/models/doodads/manifest.json (~3 min)
$PY tools/kits/doodads.py --only "tree_*,gold_mine" # subset (prefix* allowed); --list shows the ids
$PY tools/kits/doodads.py --check                  # rebuild to a temp dir, list stale outputs (exit 1 if any)
python3 tools/kits/lineup.py                        # tests/output/doodads_lineup.png (vignette, neutrals, forest
                                                    # lanes, LOD A/B, Gold Seam at 4 yaws, catalogue)
```

| File | What |
|---|---|
| `kits/doodads.py` | asset builders, registry, manifest writer (CLI above) |
| `kits/doodads_lib.py` | parts (sweep / lathe / slab / box / blob / card / ribbon), painted textures, AO + vertex-colour bake, deterministic GLB writer |
| `kits/foliage_sway.gdshader` | reference shader for `SWAY` materials (wind sway, AO, alpha scissor); the preview and lineup use it |
| `kits/lineup.gd`, `kits/lineup.py` | line-up renderer: real RtsCamera (pitch 56, FOV 45), DayNight day light, painted terrain splat, labelled catalogue |

Outputs: `assets/models/doodads/<id>.glb` (trees + `_lod1`, rocks, walls, hedge, fence, props, creep-camp kit),
`assets/models/neutral/<id>.glb` (`gold_mine`, `gold_mine_collapsed`, `neutral_weighstall`, `neutral_hale_spring`).
The manifest lists per asset: size, tris, suggested blocked footprint in cells, sight blocking, sway, materials,
texel density, LODs, animated nodes (with pivots) and extras (smoke / lantern / adit points).

What the game can rely on, and what its loader should do:
* **Vertex colours** (plain import already correct): every material, foliage included, carries painted AO /
  base darkening / moss in `COLOR_0` RGB (A = 1), tagged with glTF extras `vc_vertex_color: "multiply"`. Godot
  4.7's glTF importer sets `vertex_color_use_as_albedo` on every material except the one used by a mesh's first
  primitive, so every kit mesh starts with a hidden 1 mm dummy triangle (same material as its first real
  primitive): a plain `GLTFDocument` load shows the AO on every surface (checked on all assets). The game loader
  should still set `vertex_color_use_as_albedo = true` explicitly on every material whose meta `extras`
  says `multiply` (as `render_preview.py` / turntable.gd and `lineup.gd` do), so it never depends on that quirk.
* **Foliage** (`*_SWAY`): alpha scissor (MASK), double sided; sway weight in `TEXCOORD_1.x` (UV2.x: 0 at the
  trunk base / stem root, 1 at the canopy edge / blade tip, small values on bark), per-cluster phase in
  `TEXCOORD_2.x` (Godot `CUSTOM0.x`). A plain material renders them right but static; `kits/foliage_sway.gdshader`
  (or the tree MultiMesh shader built from it) adds the wind.
* **UV2** on every vertex: x = sway weight (0 on rigid props), y = normalized height 0..1 → build / collapse
  reveal: `discard` where `UV2.y > progress` (no extra construction meshes).
* **Atlas materials** (Gold Seam, Weighstall, Hale Spring, collapsed seam, milestone): one texture made of tiled
  cells (bands, tiles, decals); the writer cuts triangles on each cell's repeat lines and maps every piece into
  its cell (16 px wrap padding), so tiled swatches keep ~128-160 px/m inside one material. Per-cell densities are
  in the material extras `cells_px_per_m` and in the manifest.
* **Emissive tags**: `gold_mine_rock_GLOW` (only the gold seam / vein texels emit, factor 0: pulse when a worker
  enters), `*_timber_LAMP` (only the lantern glass emits, factor 0: night), `_EMBER` (camp vents and fire beds),
  `_GLYPH` (cup-and-ring marks, night only).
* **Facing**: fronts face −Z like units; the default camera sits on +Z, so spawn neutral buildings with
  facing = PI for the door-toward-camera look. The Gold Seam is finished cliff with the gold band on all four
  sides (src/main.gd spawns it facing the hall, so any side may face the camera). No TEAM materials: neutrals
  never carry team colour (bible §3.1).
* **Footprints**: the manifest's `footprint_cells` is the sim footprint and equals the mesh width (bible §1.3):
  Gold Seam and Weighstall 12×12 (6 m), Hale Spring 8×8 (4 m, `blocks_pathing: false`: the pool is walkable).
* **Trees**: crowns ~3-3.6 m across on the 1 m tree grid (map_generator fills every free tree cell), so a 2 m
  lane cut along the view reads; LOD1 reuses LOD0's cards (switch beyond ~60 m), LOD2 is a Y-billboard impostor.

`$PY tools/kits/doodads.py --check` rebuilds everything into a temp dir and lists every GLB / the manifest that
differs from the files on disk (exit 1 if any is stale): run it before committing kit outputs. After a rebuild,
let Godot reimport (`godot --headless --path . --import`) so the tracked `*.import` / extracted textures match.

## Procedural building kit (`tools/kits/buildings.py`)

Every [SLICE] building of `kingdom` and `clans` except the two AI-modelled halls, built in bpy from shared
modules (half-timber walls with rubble plinths and jetties; gable, half-hip, hip, pyramid and mono-pitch roofs
with 4-8 cm ridge sag, wandering ridges and eaves, oak bargeboards and team ridge tiles; crow-stepped gables,
smooth ribbed onion domes, chimneys, scout-tower frames, doors, shuttered windows, pennants, banners, wheels
and wagons; felt yurts on stadium or round plans with lattice band, rolled skirt, crown rings / round smoke
vents, tortoise-shell domes, carved masts with felt streamers, standing stones with square glyph decals, gong
frames, ring fences, kilns, urns, sun-mirror posts, a recurve bow on a swivel, lattice galleries) and a ground
apron under every building. No paid API. Deterministic (byte-identical GLBs, sheets and manifest on re-run;
~1 min for all 19).

```bash
$PY tools/kits/buildings.py                                  # all -> assets/models/buildings/<id>.glb + textures/ + manifest.json
$PY tools/kits/buildings.py --only kingdom_croft,clans_tea_tent
$PY tools/kits/buildings.py --coverage --silhouettes tests/output/buildings_silhouettes.png \
    --sheets tests/output/buildings --lineup tests/output/buildings_lineup.png
$PY tools/kits/buildings.py --no-build --lineup out.png      # re-render the line-ups of the GLBs on disk
python3 tools/kits/hall_team_desat.py assets/models/buildings/kingdom_moot_hall.glb assets/models/buildings/clans_shell_hall.glb
```

`--lineup X.png` writes three images: `X.png` (catalogue of every building beside the AI halls at native 8 m,
kingdom Emerald / clans Royal Blue, the slice default of art bible 2.4), `X_game.png` (the real game camera:
pitch 56, FOV 45, 28 m, 1920x1080, over a T2 base of each faction with slice units) and `X_crimson.png` (the
same catalogue in Crimson, the readability stress test only). `--silhouettes` renders the 128 px flat-black
silhouettes of bible 4.1 and prints the most similar pair per faction; `--coverage` writes the visible TEAM
fraction into the manifest (both ignore everything lower than 12 cm: the apron, rugs and kerbs).

| File | What |
|---|---|
| `kits/buildings.py` | kit modules, the 19 building generators, manifest, CLI, line-up / game-camera / coverage / silhouette drivers |
| `kits/buildings_lib.py` | swatch tiling (crossfade or pattern-period crop), procedural paint (iron, smooth bronze, brick, straw, wattle, stone, glyphs, log rings, leaves, palette, team cloth, windows, embers), parts (prism with gridded CDT caps, lathe incl. stadium plans, sweep, plate, blob), refinement, smooth-noise jitter, ray-cast AO bake, shared sheets with UV cuts on tile lines, deterministic GLB writer |
| `kits/buildings_lineup.gd` | line-up renderer (meadow ground, RTS pitch, per-faction team colours, label anchors) |
| `kits/buildings_teammask.gd` | flat TEAM / non-TEAM masks from the RTS pitch (coverage numbers, silhouettes) |
| `kits/build_reveal.gdshader` | the construction reveal (see below) |
| `kits/hall_team_desat.py` | greys the magenta TEAM texels of an already-processed AI hall GLB in place (geometry untouched) |

Conventions:
* **Size** (art bible 1.3, decided 2026-10-19; footprint = faction-doc cells x 0.5 m = sim footprint): supply
  8x8 cells (4 m, 3-3.5 m tall: Croft, Home Yurt), production / altar / shop / research 12x12 (6 m, 5-6 m;
  altar and shops 4.5-5.5 m), towers 4x4 (2 m, 6-8 m), halls 16x16 (8 m; the T2 add-ons live in the AI hall's
  space). Doors stay ~2 m (kingdom) / ~1.5 m (yurts), props stay at unit scale, swatch periods stay fixed in
  metres. Ground-level geometry stays inside the footprint; eaves, pennants and the bow may reach ~0.3 m out,
  streamers further (`outside_footprint_m` in the manifest).
* **Ground apron**: every building stands on an irregular rounded-square apron covering its footprint, top
  1.5 cm above y = 0 with a skirt down to -0.2 m (terrain bumps never open a gap; the only geometry below 0):
  packed earth with a timber kerb and cobbled paths (kingdom), trampled earth with a drystone curb and felt rugs
  (clans). Props stand on it in clusters; nothing smaller than ~0.3 m stands alone.
* **Origin and facing**: origin at the footprint centre on the ground, door on -Z like units. The RTS camera
  sits on +Z, so `UnitView` draws structures at a fixed world yaw of PI whatever the sim facing (the door always
  faces the camera).
* **Materials**: one mesh, up to three materials that reference shared external sheets in
  `assets/models/buildings/textures/` (one texture per faction in VRAM): `<id>` (opaque faction atlas,
  `<faction>_buildings_atlas.jpg`, tileable swatches at 144 px/m; pattern periods matched to the AI halls: roof
  courses ~0.3 m, rubble stones 0.4-0.7 m; saturation <= 65 %), `<id>_GLOW` (windows, forge / kiln / crown
  glow, `buildings_glow.png`; shipped with emissiveFactor 0 so nothing glows at noon, extras `emissive_night`
  is the value to set at 17:45, bible 1.5) and `<id>_TEAM` (light grey cloth, `buildings_team.png`; UnitView
  multiplies albedo_color). Team colour sits on pennants (>= 1.2 m), banners, shutters, awnings, felt bands,
  streamers and the ridge-tile band only (never on hips or roofs), each area with neutral piping cut into the
  atlas (ivory kingdom, bronze clans). `COLOR_0` = painted AO (tagged `vc_vertex_color: "multiply"` like the
  doodad kit); the primitives are ordered GLOW, atlas, TEAM because Godot 4.7's glTF import never sets
  `vertex_color_use_as_albedo` on a mesh's first primitive (buildings without GLOW start with a hidden 1 mm
  dummy triangle), so stock import already shows the AO.

Construction (no `_construction` meshes): `kits/build_reveal.gdshader` reveals the finished mesh bottom-up.
Its height comes from the vertex (`VERTEX.y / model_height`, set `model_height` to the manifest's `height_m`, or
the AABB height for the AI halls), so it works on every building and on hall upgrades with no extra vertex
data; a hash value-noise ragged edge glows ember while it rises. Kingdom "scaffold-raised": `two_pass = false`.
Clans "Raising": `two_pass = true` and `TEXCOORD_1.x` (UV2.x) = build layer: 0 (lattice, masts, stone) rises over
progress 0..0.6, 1 (felt walls and domes, team bands) over 0.4..1.0. UV2.y also stores the normalized height.

T2 hall upgrades are add-ons in the AI hall's model space (8 m): `kingdom_walled_burg` (a ring of Bombard-sized
burgundy wagons with team side boards, two flanking the door and one down each side; stone corner buttresses;
four banner poles; a taller smooth dark-bronze onion with seven ribs and a team ring, lifted on a drum over the
T1 turret so the stepped gable stays clear; 12.1 m <= +15 %) and `clans_banner_shell` (lattice gallery, two
shell-domed kiosks, four felt-banner masts, a second gong; 6.5 m). Parent them with the same transform as
`kingdom_moot_hall.glb` / `clans_shell_hall.glb` and show both.

Known limits: `mathutils.noise.noise_vector()` is clock-seeded per process (use scalar `noise()` or call
`noise.seed_set()` for deterministic jitter); bmesh `bevel` emits vertices in a run-dependent order (the kit
chamfers by sweeping a profile and the writer sorts vertices and triangles canonically).

## Procedural siege kit (`tools/kits/siege.py`)

The wheeled siege units (slice-plan 2.5 D1 / D2) built from the building kit's parts, swatches and shared
sheets, so they share the faction atlas and the TEAM sheet in VRAM (image URIs `../buildings/textures/...`).

```bash
$PY tools/kits/siege.py                                   # assets/models/vehicles/<id>.glb (~10 s each)
$PY tools/kits/siege.py --only clans_sling_cart --out-dir /tmp/x
python3 tools/render_preview.py assets/models/vehicles/kingdom_bombard_wagon.glb -o sheet.png --team-color "#2EAE3A"
godot --headless --path . -s tools/assets/check_team_coverage.gd -- --only=kingdom_bombard_wagon
```

* **Bombard Wagon** (2.55 m, 1.65 m tall, ~5.3k tris): a plank cart on two big iron-shod spoked wheels with
  team-painted felloes, team side boards, a fat warm-bronze bombard on a timber cradle with a team canvas
  hood over the breech, a push bar and two crew in kettle hats with team plumes (team coverage 11.9 %).
* **Sling-Cart** (2.46 m, arm tip 2.8 m, ~3.8k tris): a low lattice cart, a tall throwing arm on an A-frame
  with a team rope-wrap and a team felt sling hanging at rest (a traction engine: haul ropes from the short
  end, no counterweight box), a team felt hood over the clay-pot rack, a team felt blanket, two Tormai crew in
  teal coats and felt caps with team bands (10.9 %). No spikes, skulls or hide (slice-plan D2 art rules).
* **Nodes** (`buildings_lib.export_glb_nodes`): the body, `Wheel_L/R` (pivot on the axle), `Barrel` (pivot on
  the trunnions) or `Arm` (pivot on the A-frame), `Crew_A/B` (hips) and `Crew_*_Leg_L/R` (hip joints); every
  node's origin is its pivot and its glTF extras carry its role (`radius_m`, `recoil_m`). AO is baked over all
  nodes in the rest pose. The game animates them procedurally (`src/fx/vehicle_rig.gd`).
* The model is centred on its length (the unit's circle and picking sit on its position); the front faces
  -Z; deterministic like the building kit.

## Free auto-rig

`autorig.py` replaces paid auto-rigging (Higgsfield `3d_rigging`, 8 credits per rig; Meshy) for
humanoids: it fits the 24-bone skeleton of an existing paid rig (the *template*) to any static
character mesh, skins it on the CPU and puts the library clips on it. 0 credits, ~10 s per unit.
The paid clip library (`assets_src/characters/kingdom_infantry/rig_*.glb`: idle, walk,
attack_sword, death, cast, heavy_swing, throw) is reused for every new character.

```bash
K=assets_src/characters/kingdom_infantry
$PY tools/autorig.py raw/new_unit.glb -o assets/models/units/new_unit.glb \
    --template $K/rig_walk.glb --height 1.75 \
    --clip idle=$K/rig_idle.glb --clip walk=$K/rig_walk.glb \
    --clip attack=$K/rig_attack_sword.glb --clip death=$K/rig_death.glb \
    --target-tris 4500 --team-mask 300:45:0.3 --name new_unit \
    --debug-png build/new_unit_joints.png --keep-rig build/new_unit_rig.glb
python3 tools/render_preview.py assets/models/units/new_unit.glb -o build/new_unit_sheet.png \
    --fractions 0,0.25,0.5,0.75
```
The input's facing is detected from the feet (toes point forward; raw Tripo files face +X and are
turned automatically). `--facing` sets it explicitly (raw Tripo: `+x`; glTF / Meshy: `+z`;
`process_model` output: `-z`); when the feet contradict a given facing by ≥ 45° with confidence ≥ 0.9
the run stops (exit 2) unless `--force`. Robed bodies hide the feet: the input is then assumed to face
+Z with a warning, so pass `--facing` for them. The output is game-ready (faces −Z, decimated, team
material, ≤ 4 normalized influences, clips named after `--clip`); `--raw` stops after the full-res
+Z-facing rig instead. The JSON on stdout has every number below.

**Exit codes**: 0 ok (read `warnings` and `landmarks.fallback_joints` anyway); 2 stopped before
rigging (facing contradicted by the feet, nothing written); 3 output written but flagged in
`errors`: a limb more than 40° off the template's rest pose (T-pose / arms raised / bad landmarks)
or bone heat failed at every voxel size (envelope weights). `--force` turns errors into warnings.

How it works:
1. **Normalise**: import, bake transforms, join, weld; turn to face +Z, feet on 0, `--height`.
2. **Landmarks** on a solid voxelisation (H/160): horizontal slices of the *core* (≥ 2–3 voxels
   inside the surface, so blades, shield plates, capes and brims drop out) give
   * the crotch: two leg sections tracked up from the floor until they merge. A section that grows
     (knee armour, a skirt brushing the knees, a hand on the thigh) does not end the track; legs that
     separate again after merging were thighs touching; a merge much wider than the two legs is a
     skirt/robe hem (legs then fall back);
   * the shoulder top: the widest torso+arms section, searched above crotch + 0.35 H (≤ 0.70 H),
     then up to where the width collapses to the neck (hands or a two-handed prop joined to the hips
     make a wider section at hand height, which used to drag the whole trunk down);
   * the head top on the head axis (plumes ignored), the soles, and the arm sections tracked down
     from the armpit to the fist (thin or flat sections lose to round thick ones, so a shield or a
     sword is not taken for the arm; pieces of an arm pressed against the body are chained; tracks
     that start at hand height or far above the expected armpit are rejected).

   These levels are checked against the template's proportions (`KNOT_LIMITS`: shoulder top / H
   ±20 %, trunk (shoulder − crotch) / H ±20 %, crotch / H 0.6–1.3× (short-legged workers are 0.75×),
   shoulder − armpit 0.7–1.35×, head top / H). A failed level is replaced by the template proportion
   and listed in `landmarks.level_fallbacks` (ratios in `level_ratios_vs_template`); the trunk joints
   in the affected height range get `fallback:height(<level>)`. When the legs merged only after a
   section grew and the trunk is > 8 % off, the crotch height comes from the template's trunk
   proportion (leg geometry kept). Every template joint is expressed relative to these features
   **on the template's own skinned mesh** (height between feature levels, fraction across the local
   torso/leg section, fraction along the arm path) and looked up at the same relative place on the
   target. Missing features (robes hide the legs, arms fused to the body) fall back to template
   proportions scaled per region; `landmarks.joints.<bone>.source` says which (`torso-section`,
   `arm-path`, `leg-axis`, `leg-section`, `footprint`, `head-frame`, `fallback:*`),
   `landmarks.fallback_joints` lists the fallbacks. `--joints FILE.json` overrides single joints by
   hand (`{bone: [x, y, z]}`, glTF axes of the +Z-facing model); `--debug-png` draws the joints on
   front/side projections.
3. **Armature**: exactly the template's bone names, parents and rest orientations (rolls); only the
   heads move, so the clips map 1:1.
4. **Skin**: voxel-remeshed watertight proxy (`--voxel` 0.8 % of H) → Blender automatic weights
   (bone heat) on a helper armature with joint-to-joint bones; when bone heat finds no solution it
   is retried at 1.125×, 1.25×, 0.875× the voxel size (`skin.heat_attempts`); envelope weights only if
   all fail (`skin.method_effective`, an error unless `--weights envelope`) → Data Transfer (nearest
   face, interpolated) to the real mesh → held props bound 100 % to one hand: thin or disconnected
   geometry touching only a hand/forearm (swords, shields), and **long thin pieces** (staffs,
   spears, polearms: span > 0.3 H, ≥ 6× longer than thick), as separate mesh islands or as collinear
   voxel pieces split by the hands, even when they cross the body; bound to the hand with clearly
   more contact, a two-handed grip to the hand nearest the prop's centre (a tie: the right hand,
   the weapon hand of the library clips); a long island that touches no hand (a spear on the back)
   goes rigidly to its dominant bone. Never into the other hand's region → clean < 0.01, limit 4,
   normalise. Nearest-bone-segment weights fill anything bone heat left out.
5. **Clips** (`--clip NAME=FILE[:ACTION]`, any rig with the template's bone names): the
   `retarget_anims` math (rotation-only, world space), then
   * **facing**: the clip's mean yaw is removed with a constant yaw of the root, measured on the
     torso (hips+shoulders axis; idle, walk, death, heavy, throw) or the **head** (where the character
     looks; attack, cast: their fighting stance turns the torso 26–46° while the head looks ahead;
     falls back to torso when the head direction is inconsistent over the clip). `--face-ref
     NAME=torso|head|none`, `facing_fix.reference` in the JSON;
   * **hips**: in place (`vertical`) for walk/run (the game moves the unit), `full` for death and for
     clips whose source hips end where they start (attack, cast, idle: the lunge keeps the planted
     foot fixed instead of sliding it back), else `vertical` (heavy, throw end 8–13 cm away: no pop
     when repeated). `--hips-mode NAME=MODE`, `hips_mode_why` in the JSON;
   * **feet**: two-bone IK makes the ankles follow the source ankles scaled by the leg ratio, then
     raises the ankle so the linear-blend-skinned foot never sinks below the floor and, in
     walk/run, clears it by at least max(2.5 cm, 1.5 % H) at the top of each step (short legs scale
     the source step down to nothing). `--no-ground` / `--no-foot-ik` turn this off.
6. **Game-ready** via `process_model.py` (`--target-tris`, `--team-mask`, `--team-desaturate`,
   `--tex-size`, `--pm-arg`).
7. **QA** on the written GLB: `qa.unweighted_verts`, `qa.max_influences`, `qa.long_prop_islands`,
   and per clip `max_disp_ratio`, `stretch_max` (max edge length deformed/rest; `stretch_flag`
   above 2), `stretch_p999`, `edges_over_2x`; `facing_deg` {torso, head, feet} (`mean_facing_deg` =
   torso), three independent directions so a fix on one can be checked with another;
   `planted_toe_slide_cm` (largest toe travel within one stance phase; stance = toe within 2 % H of
   its 20th-percentile height, plus, in a treadmill walk, moving like the median low frame: the real
   slide in in-place clips, the stride in `walk`) and `stance_speed_mps` (walk: the speed the unit
   must move at for the feet not to slide — use it for the unit's move speed / animation speed);
   `foot_low_cm` {L, R: [lowest, highest]} lowest skinned foot point per frame vs the floor (every
   frame); `lowest_point_cm` (any vertex: props reach through the floor); `prop_rigidity_cm` (largest
   non-rigid deformation of a long prop island, Kabsch residual). Per clip in `clips[]`:
   `source_planted_toe_slide_cm` (the library clip's own slide, scaled to this body). With
   `--reference-rig RIG.glb` or `--reference-joints J.json` also `joint_error` (cm per bone, mean,
   max, `aligned_*` after removing a horizontal offset). `landmarks.rest_pose_diff_deg` is the
   angle of each limb vs the template's rest pose (warning above 25°, error above 40°).
   `--qa-only RIGGED.glb` prints the clip metrics of any rigged GLB, e.g. a paid rig as a baseline.

Results (`tools/tests/test_autorig.sh`, all at 4500 tris with the 4 library clips; joint error =
core joints (no end markers), cm; stretch = max edge stretch, edges > 2× in brackets; walk feet =
lowest skinned foot point over the walk / smallest per-foot step height, cm; attack slide = planted
toe slide L/R vs the source clip's (scaled), cm):

| Test mesh | Joint error mean / max | Level / joint fallbacks | idle | walk | attack | death | walk feet | attack slide | prop rigid |
|---|---|---|---|---|---|---|---|---|---|
| **paid Higgsfield rig** (shipped `kingdom_infantry.glb`) | – | – | 2.97 (9) | 2.44 (4) | 6.98 (71) | 6.77 (114) | −3.8 / 4.7 | 7.5 / 15.2 | – |
| (a) `rig_source_facing_pz.glb` (the mesh the paid rig was made on) | 1.24 / 5.74 | none | 1.98 (0) | 1.90 (0) | 4.30 (20) | 5.63 (48) | −0.6 / 4.5 | 8.3 / 16.8 (src 7.5 / 15.7) | – |
| (a2) raw `model_tripo_h31.glb`, no `--facing` (detected +X), 7 clips | 1.24 / 5.74 | none | 1.98 (0) | 1.90 (0) | 4.30 (20) | 5.63 (48) | −0.6 / 4.5 | 8.3 / 16.8 | – |
| (b) `bakeoff_trellis_4k.glb` (other generator, vs template rig*) | 6.63 / 14.96 | none | 2.19 (4) | 1.72 (0) | 3.25 (26) | 4.63 (72) | −0.4 / 4.2 | 9.0 / 16.9 | – |
| (b) `bakeoff_tripo_legacy_4k.glb` (detected −X)* | aligned 4.98 / 13.69 | none | 2.48 (6) | 2.10 (2) | 3.88 (34) | 3.42 (97) | 0.0 / 5.0 | 9.8 / 14.4 | – |
| (c) brute 2.1 m: 1.3× wide, legs 0.85×, hunched 25° | 3.26 / 8.91 | none | 2.91 (4) | 2.71 (4) | 6.98 (18) | 5.87 (43) | −0.4 / 3.3 | 10.7 / 21.4 (src 9.8 / 20.5) | – |
| (c) caster 1.9 m: 0.82× slim, closed robe, staff | 1.40 / 4.18 | legs (robe): 10 joints | 4.25 (11) | 4.69 (8) | 13.6 (57) | 20.0 (117) | −0.2 / 5.2 | 8.5 / 11.1 | 0.0 |
| (c) worker 1.1 m: legs 0.75×, head 1.35× | 1.64 / 5.21 | none | 2.08 (1) | 1.76 (0) | 3.19 (12) | 3.56 (41) | −0.2 / 2.6 | 5.2 / 10.4 | – |
| (c) hero 2.1 m with a long cape | 1.74 / 7.92 | none | 3.15 (10) | 3.67 (2) | 3.89 (39) | 4.33 (66) | −0.9 / 5.7 | 10.0 / 21.0 | – |
| (d) arms 12° closer, hands on the thighs | 1.84 / 6.36 | none | 3.93 (31) | 4.05 (42) | 8.98 (78) | 12.9 (104) | −0.5 / 4.2 | 8.3 / 16.7 | – |
| (d) 2.2 cm staff through both fists | 1.20 / 5.40 | none | 2.00 (0) | 1.81 (0) | 3.91 (28) | 5.07 (60) | −0.6 / 4.5 | 8.3 / 16.8 | 0.0 |
| (d) polearm diagonally across the chest | 2.07 / 6.20 | none | 2.10 (2) | 1.67 (0) | 2.93 (25) | 3.69 (58) | −0.8 / 4.5 | 8.3 / 16.8 | 0.0 |
| (d) knee armour 1.3× (thighs touch; heat retried 0.008 → 0.009 H) | 1.58 / 6.24 | crotch from trunk: 6 joints | 2.42 (4) | 1.86 (0) | 4.25 (18) | 5.50 (65) | −1.0 / 4.4 | 8.3 / 16.7 | – |
| (d) squat 1.2 m: legs 0.6×, 1.35× wide | 2.90 / 6.46 | none | 2.70 (6) | 2.39 (2) | 3.88 (20) | 3.60 (55) | −0.1 / 2.6 | 6.1 / 12.6 (src 6.3 / 11.7) | – |

Facing (every mesh): idle and walk torso 0 ± 1°, walk head −2°, walk feet −6 to −10°; attack head
0° (paid unit −1.4°, same library clip without a fix) with the torso at −26° (paid −27°).
Stance speed in walk: 0.69–0.71 m/s at 1.75 m (paid 0.71–0.73), 0.37 m/s for the 1.1 m worker.

\* (b) are different meshes of the same character, so their error vs the template rig is only
indicative. (a) uses the template's own mesh, which is also the calibration mesh: it shows the fit
reproduces the paid joints (trunk exact, hands within 6 cm), while (b)–(d) test how it
generalises. The (c) and (d) bodies are deformations (or, for "arms 12° closer", a re-posing of the
paid rig's own skinned mesh) with the same transform applied to the paid joints
(`tests/make_autorig_bodies.py`), so their joint error is exact. Before these fixes "arms 12°
closer" put the trunk 40 cm too low (mean error 23.9 cm, stretch 14–45×) and the two-handed staff
50 cm too low; the knee armour body fell back to envelope weights; long props bent by up to 1 m.
No mesh has unweighted vertices or more than 4 influences. The caster's stretch comes from the robe
hem spanning both legs and from robe geometry fused with the hand that holds the staff; the
arms-in body's from the elbows pressed into the waist (the voxel proxy fuses them).

Known limitations:
* Humanoid template only (names/hierarchy like the Meshy 24-bone rig: `Hips … LeftUpLeg …
  LeftForeArm/LeftHand …`); the template must include its skinned mesh (it calibrates the landmarks).
* Expects an A-pose-like input. Arms pressed against the body are found as long as part of the arm
  is separate (12° closer: fine); arms fused along their whole length (20° closer) fall back to
  template A-pose arms (listed in `fallback_joints`, exit 0), and contact areas (elbow on the waist,
  hand on the thigh) are fused in the voxel proxy, so they tear in clips. A T-pose whose arm tracks
  fail falls back the same way and is only an error when a fitted limb is > 40° off.
* The feature-level checks catch gross errors (≥ 20–30 % off the template's proportions). Smaller
  errors pass: the knee armour body's thighs merge 10 cm below the crotch, which is only corrected
  because the leg section grew first and the trunk came out 14 % long.
* Robes and long skirts: the legs are not visible, so leg joints are template proportions scaled
  to the height and torso (accurate only when the legs under the robe have template-like
  proportions); the robe hem is weighted to both legs and stretches between them in wide-stance
  frames. Capes and coat tails follow the thighs they hang behind, so they shear at the hem in
  `walk` (no cloth bones in the template). Open skirts with visible legs are fine.
* Held props are rigid with one hand, so a sword or staff tip can go through the floor when the clip
  puts the hand near the ground (`death`, `heavy`: `lowest_point_cm` −20 to −110 cm for a long
  staff), and a two-handed prop goes with one hand (the right): the other hand leaves it during
  the clip (the library clips are one-handed). Long props fused into the hand mesh (same island)
  are rigid only outside the body volume. Geometry fused between a hand and the thigh/robe tears.
* The facing fix removes the clip's *mean* yaw of its reference. A clip that really should end
  turned (a spin) is straightened on average too (`--no-face-fix`, `--face-ref NAME=none`).
* Foot IK follows the source ankles' path and keeps the foot orientation; the ground clamp only
  raises feet (the toe angle is not adapted to very different foot sizes, so big feet on short legs
  roll more: their planted-toe slide scales with the foot, not the leg).

## process_model.py reference
```
process_model.py IN.glb -o OUT.glb [--target-tris N] [--cleanup] [--merge-dist M] [--min-island F]
    [--symmetry x] [--smooth-angle DEG] [--height H | --width W | --scale S] [--facing +z|-z|+x|-x]
    [--yaw DEG] [--no-recenter] [--tex-size 1024] [--tex-format auto|png|jpeg] [--jpeg-quality 90]
    [--drop-maps normal,orm,emission,occlusion] [--name NAME]
    [--team-mask HUE[:TOL[:SATMIN]]] [--team-desaturate] [--clip-name NAME] [--rename-clip OLD=NEW]
    [--no-anims] [--json FILE] [--no-verify]
```
Steps: bake all node transforms into the data (armature too — rest bones are transformed and pose
location keys rescaled, so animations stay valid; props parented to a bone become a full-weight
skin group) → join meshes → weld co-located vertices (UV seams survive as per-corner UVs, which
stops the decimator from opening cracks along seams) → `--cleanup`: dissolve degenerates, delete
loose verts/edges and islands smaller than `--min-island` × model diagonal → quadric collapse
decimation to `--target-tris` (±2 %; on rigged meshes the armature modifier is disabled and the
decimator runs on the bind pose, interpolating vertex groups) → limit to 4 normalized
influences → recentre/scale/turn → smooth shading split at `--smooth-angle` → textures → export.

Verification in the JSON: `skin.before/after` (unweighted verts, groups used, max influences),
`skin.groups_lost`, `skin.posed_bounds_deviation_frac_of_height` (skinned bounds at the middle of
every clip before vs after decimation; warns above 0.03), and `verify` (the written GLB is
re-imported: meshes, tris, actions, images).

`--team-mask 300` = magenta (hue in degrees, tolerance 25°, saturation ≥ 0.35 by default). Ask the
generator for a flat, saturated, unused colour on the team-coloured parts. A face becomes a team
face when the mean mask value at its corners and centre exceeds `--team-threshold` (0.5); the JSON
reports `texel_coverage`, `team_faces` and `team_face_fraction`.

## Music toolkit (`tools/music/`)

The game's music is composed in Python and rendered offline, with no paid generation. A piece is a module in
`tools/music/pieces/` whose `build()` returns a `score.Piece` (modal harmony, our motifs with transforms, sections,
articulations, ornaments, drum grids, CC11 phrasing, seeded humanisation). `render.py` renders one stem per track
(FluidSynth with the MIT-licensed FluidR3_GM soundfont, or the numpy gong, bell, hurdy-gurdy, jaw harp, chant,
frame drum and claps of `synths.py`), mixes them with ffmpeg (EQ, pan, a generated room via `afir`, bus
compression), masters to -16 LUFS / -1 dBTP and writes Ogg Vorbis q6 48 kHz. It also writes a spectrogram, a piano
roll and a JSON report of the checks:

```bash
python3 tools/music/render.py tools/music/pieces/style_kingdom.py                    # style test
python3 tools/music/render.py PIECE.py --out assets/audio/music/clans_1.ogg --length-check
python3 tools/music/render.py PIECE.py --out assets/audio/music/menu.ogg --loop --xfade 3
python3 tools/music/render.py PIECE.py --out assets/audio/music/opening_clans.ogg --trim 2.4
bash tools/music/test_determinism.sh       # byte-identical MIDI, stems and Ogg across two clean renders
```

The tuned band per faction lives in `tools/music/palette.py` (`gain_db` = dB relative to the melody). The full
guide is `tools/music/README.md`.

## Tests
```bash
tools/tests/run_all.sh /tmp/vc_tooltest [sample.glb] [grass.png dirt.png ...]   # RENDER=0 skips sheets
```
Builds two synthetic Meshy-like characters (`tests/make_test_rigs.py`: 1.8 m human and 1.2 m
dwarf with 0.01 armature-object scale, bone-heat weights, cylindrical UVs with a seam, 2048 px
texture, an unskinned sword parented to the hand bone, one "Take 001" clip per file), PBR and FBX-style multi-object props from the sample
(`tests/make_test_props.py`), then runs every tool and asserts on the JSON: decimation targets,
skin survival, clip lists, retarget accuracy (`tests/check_retarget.py`, evaluated by Blender:
0.000° joint-direction error, hip offset ratio = leg ratio), seam scores, palette stats, icon
crop, and that every GLB loads in Godot without errors. ~75 s with rendering.

```bash
tools/tests/test_autorig.sh /tmp/vc_autorig       # RENDER=0 skips sheets; ~4 min with rendering
```
Free auto-rig end to end (see *Free auto-rig*): the paid rig's own mesh (joint error vs the paid
rig, mean < 4 cm, max < 8 cm), the raw Tripo file with all 7 library clips and no `--facing`, the
same file with a wrong `--facing` (must exit 2), two other generators' meshes of the same
character, four synthetic bodies (brute, robed caster with staff, worker, hero with cape) and five
QA failure modes (arms 12° closer, two-handed staff, diagonal polearm, knee armour, squat), all
with exact ground-truth joints (`tests/make_autorig_bodies.py`). Per mesh it checks: exit 0 and
bone heat succeeded, skin stats, clip lists, joint error budgets, facing (each clip's own reference
< 5°; walk also by head < 10° and feet < 15°; attack's head within 10° of the paid unit's), feet
(walk/idle never more than 1.5 cm into the floor, every walk step ≥ 2 cm), attack planted-toe slide
≤ 1.3× the source clip's + 1 cm, long-prop rigidity (< 1 cm) and the robe/knee fallbacks. It prints
the QA table next to the shipped paid-rig unit and writes contact sheets (`sheets/`, plus the hero
from behind) and joint overlays (`debug/`).

## Known limitations
* No normal-map baking from the high-poly: low-poly models keep the original texture/UVs only
  (fine down to ~2–3k tris for AI props; very aggressive targets lose silhouette detail).
* Decimation is Blender's quadric collapse: no explicit UV-distortion metric, no LODs (run twice
  with different `--target-tris` for LODs). Shape keys are removed when decimating.
* Retarget assumes both rigs share a rest pose (T vs A pose is not corrected), no IK (feet can
  slide/penetrate when leg proportions differ a lot), only hips translation is transferred.
* `process_model` never guesses the facing: check the red arrow on the contact sheet
  (`autorig` detects it from the feet unless `--facing` is given).
* Team colour is hue-keyed from the base colour (it can't tell the team hue from the same hue
  elsewhere) and the material split is per face, so team areas narrower than a triangle or two
  get lost at low tri counts (check the blue areas on the sheet; lower `--team-threshold` to grow
  them). The texel mask PNG is not embedded in the GLB.
* glTF carries no loop flags (set loop modes in code); object-level (non-armature) animation and
  morph-target animation are dropped by `process_model`.
* Vertex-colour-only models (some Hunyuan/Tripo outputs) pass through untested.
* `seamless` cross-fades; strongly structured textures (bricks, tiles) can show ghosting in the
  blend band — use a smaller `--blend` or fix by hand.

## Team-colour check

```
godot --headless --path . -s tools/assets/check_team_coverage.gd            # report, exit 1 on failures
godot --headless --path . -s tools/assets/check_team_coverage.gd -- --write # + team_coverage.json
godot --headless --path . -s tools/assets/check_team_coverage.gd -- --only=kingdom_infantry
```

`tools/assets/team_coverage.gd` rasterises each rigged unit GLB in its rest pose from the RTS
camera pitch (−56°, orthographic, eight yaws, depth-tested, 160 px) and evaluates the unit
shader's team weight per visible pixel (`<model>_team.png` through smoothstep(0.45, 0.8), plus the
magenta key on the albedo). It prints the silhouette share (`coverage`), the share in the upper
third of the model height (`upper`) and the plain mask texel share (`texel`), and fails a model
outside the art bible §3.1 range: 10–15 % for units, 8–15 % for workers, 10–18 % for heroes, and at
least 0.5 % of the silhouette in the upper third. Rerun it with `--write` after replacing a model
or its mask: `test_visual.gd::test_team_coverage_check` fails when `team_coverage.json` misses a
model or is out of date. Until a failing model is repainted, the game compensates for a low share
with a stronger, brighter and wider team rim (architecture §7, `AssetLibrary.team_deficit`).
