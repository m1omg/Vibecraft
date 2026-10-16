# Vibecraft asset tools

Offline tools that turn AI-generated art (Tripo / Meshy / Hunyuan GLBs, 1024 px PNGs) into
game-ready assets for the Godot 4.7 project, plus a visual QA renderer. Nothing here calls a
paid generation API.

| Tool | Interpreter | What it does |
|---|---|---|
| `process_model.py` | bpy | GLB → one mesh (+armature), cleanup, decimate, recentre, scale, face −Z, textures ≤1024, stable names, team mask, GLB |
| `merge_anims.py` | bpy | several single-clip GLBs of one rigged character → one GLB with clips `idle walk attack death …` |
| `retarget_anims.py` | bpy | copy clips between rigs with the same bone names but different proportions (rotation-only) |
| `texture_tools.py` | python3 | `seamless`, `tile-preview`, `seam-score`, `resize`, `array`, `atlas`, `icon`, `palette-match` |
| `render_preview.py` | python3 + Godot | load a GLB through `GLTFDocument` (load check + JSON report) and render a labelled contact sheet |
| `vc_bpy.py` | (library) | shared Blender helpers: import/export, actions/NLA, retarget math |
| `preview/` | Godot | tiny separate Godot project used by `render_preview.py` (`inspect.gd`, `turntable.gd`) |
| `tests/` | bpy / bash | synthetic rigged characters and props, retarget checker, `run_all.sh` end-to-end test |

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
$PY tools/process_model.py raw/footman_idle.glb -o build/footman_base.glb --name footman \
    --target-tris 6000 --height 1.8 --symmetry x --team-mask 300 --team-desaturate
# 2. all clips onto that base, straight from the raw files
$PY tools/merge_anims.py -o assets/models/footman.glb --base build/footman_base.glb \
    --clip idle=raw/footman_idle.glb --clip walk=raw/footman_walk.glb \
    --clip attack=raw/footman_attack.glb --clip death=raw/footman_death.glb
cp build/footman_base_team.png assets/models/footman_team.png   # optional texel mask
python3 tools/render_preview.py assets/models/footman.glb -o /tmp/footman_sheet.png
```
`merge_anims` copies bone-local keys verbatim when the clip's skeleton matches the base
(always true for files of one character; `process_model`'s scale/turn doesn't change bone-local
rests) and rescales hip translation by the bone-length ratio, so it doesn't matter that the base
was rescaled. If a clip file's rest pose differs by more than `--rest-tolerance` degrees it is
retargeted instead (warning). `--clip NAME=FILE:ACTION` picks one action when a file has several.

### Share clips between two rigged characters (same bone names, different proportions)
```bash
$PY tools/retarget_anims.py --source assets/models/footman.glb --target build/dwarf_base.glb \
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
python3 tools/texture_tools.py icon raw/footman_concept.png -o assets/icons/footman \
    --frame "#b08d3c" --disabled        # footman_128.png footman_64.png (+ _dis variants)
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

## Known limitations
* No normal-map baking from the high-poly: low-poly models keep the original texture/UVs only
  (fine down to ~2–3k tris for AI props; very aggressive targets lose silhouette detail).
* Decimation is Blender's quadric collapse: no explicit UV-distortion metric, no LODs (run twice
  with different `--target-tris` for LODs). Shape keys are removed when decimating.
* Retarget assumes both rigs share a rest pose (T vs A pose is not corrected), no IK (feet can
  slide/penetrate when leg proportions differ a lot), only hips translation is transferred.
* Facing is never guessed: check the red arrow on the contact sheet.
* Team colour is hue-keyed from the base colour (it can't tell the team hue from the same hue
  elsewhere) and the material split is per face, so team areas narrower than a triangle or two
  get lost at low tri counts (check the blue areas on the sheet; lower `--team-threshold` to grow
  them). The texel mask PNG is not embedded in the GLB.
* glTF carries no loop flags (set loop modes in code); object-level (non-armature) animation and
  morph-target animation are dropped by `process_model`.
* Vertex-colour-only models (some Hunyuan/Tripo outputs) pass through untested.
* `seamless` cross-fades; strongly structured textures (bricks, tiles) can show ghosting in the
  blend band — use a smaller `--blend` or fix by hand.
