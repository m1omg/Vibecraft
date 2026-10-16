#!/usr/bin/env bash
# End-to-end test of the Vibecraft asset tools. Everything is written under OUT_DIR.
#
#   tools/tests/run_all.sh OUT_DIR [SAMPLE.glb] [TEXTURE.png ...]
#
# SAMPLE.glb   optional textured AI model (e.g. a Tripo boulder) - also used to build PBR /
#              multi-object variants; TEXTURE.png  optional terrain textures for the image tools
#              (synthetic noise textures are used when none are given).
# Env: VC_BPY (bpy python, default /opt/bpyenv/v313/bin/python), RENDER=0 to skip contact sheets.
# Exit code != 0 on the first failed check.
set -euo pipefail

OUT=${1:?usage: run_all.sh OUT_DIR [SAMPLE.glb] [TEXTURE.png ...]}
SAMPLE=${2:-}
shift $(( $# >= 2 ? 2 : $# ))
TEXS=("$@")
PY=${VC_BPY:-/opt/bpyenv/v313/bin/python}
RENDER=${RENDER:-1}
TOOLS=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$OUT"/{rigs,props,models,sheets,tex,icons,logs}
OUT=$(cd "$OUT" && pwd)

step() { printf '\n== %s\n' "$*" >&2; }
# check JSON_FILE PYTHON_EXPR  (d = parsed json); prints the expression value, fails if falsy
check() {
  python3 - "$1" "$2" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
ok = eval(sys.argv[2], {"d": d})
print(("PASS " if ok else "FAIL ") + sys.argv[2], file=sys.stderr)
sys.exit(0 if ok else 1)
EOF
}
bpy() { local log="$OUT/logs/$1.log" json="$OUT/logs/$1.json"; shift; "$PY" "$@" >"$json" 2>"$log" || { tail -20 "$log"; exit 1; }; }

step "synthetic rigged characters"
bpy rigs "$TOOLS/tests/make_test_rigs.py" --out-dir "$OUT/rigs"
check "$OUT/logs/rigs.json" "all(r['weights']['weighted_fraction'] == 1.0 for r in d['rigs'])"

step "process_model: rigged rest mesh -> 5000 tris, 1.8 m, symmetric decimation"
bpy pm_lod "$TOOLS/process_model.py" "$OUT/rigs/char_a_rest.glb" -o "$OUT/models/char_a_lod.glb" \
  --target-tris 5000 --height 1.8 --symmetry x
check "$OUT/logs/pm_lod.json" "abs(d['tris_after'] - 5000) <= 100 and abs(d['dims_godot_m'][1] - 1.8) < 1e-3"
check "$OUT/logs/pm_lod.json" "d['skin']['after']['weighted_fraction'] == 1.0 and not d['skin']['groups_lost']"
check "$OUT/logs/pm_lod.json" "d['bounds_min_godot'][1] == 0.0"

step "process_model: rigged + animated + team mask"
bpy pm_attack "$TOOLS/process_model.py" "$OUT/rigs/char_a_attack.glb" -o "$OUT/models/char_a_attack.glb" \
  --target-tris 4000 --height 1.8 --clip-name attack --team-mask 300 --team-desaturate
check "$OUT/logs/pm_attack.json" "max(d['skin']['posed_bounds_deviation_frac_of_height'].values()) < 0.01"
check "$OUT/logs/pm_attack.json" "[a['name'] for a in d['actions']] == ['attack'] and d['verify']['actions'] == ['attack']"
check "$OUT/logs/pm_attack.json" "d['team_mask']['texel_coverage'] > 0.01 and d['team_mask']['team_faces'] > 10 and d['materials'] == ['char_a_attack', 'char_a_attack_TEAM']"

step "merge_anims: 4 single-clip files onto the processed base"
bpy merge "$TOOLS/merge_anims.py" -o "$OUT/models/char_a_merged.glb" --base "$OUT/models/char_a_lod.glb" \
  --clip idle="$OUT/rigs/char_a_idle.glb" --clip walk="$OUT/rigs/char_a_walk.glb" \
  --clip attack="$OUT/rigs/char_a_attack.glb" --clip death="$OUT/rigs/char_a_death.glb"
check "$OUT/logs/merge.json" "d['verify']['ok'] and sorted(d['verify']['actions']) == ['attack', 'death', 'idle', 'walk']"
check "$OUT/logs/merge.json" "all(c['method'] == 'copy' for c in d['clips'])"

step "process_model on a multi-clip file (re-decimate keeps every clip and the skin)"
bpy pm_merged "$TOOLS/process_model.py" "$OUT/models/char_a_merged.glb" -o "$OUT/models/char_a_low.glb" \
  --target-tris 2500 --height 1.8 --facing=-z
check "$OUT/logs/pm_merged.json" "len(d['actions']) == 4 and max(d['skin']['posed_bounds_deviation_frac_of_height'].values()) < 0.02"

step "retarget_anims: human clips -> dwarf (different proportions, 0.01 armature scale, opposite facing)"
bpy retarget "$TOOLS/retarget_anims.py" --source "$OUT/models/char_a_merged.glb" \
  --target "$OUT/rigs/char_b_rest.glb" -o "$OUT/models/char_b_retargeted.glb" --drop-target-anims
check "$OUT/logs/retarget.json" "d['verify']['ok'] and len(d['clips']) == 4"
bpy retarget_check "$TOOLS/tests/check_retarget.py" --source "$OUT/models/char_a_merged.glb" \
  --result "$OUT/models/char_b_retargeted.glb" --clips idle,walk,attack,death --max-err 0.5
check "$OUT/logs/retarget_check.json" "d['ok'] and all(abs(c['hips_dz_ratio'] - d['leg_ratio']) < 0.01 for c in d['clips'].values() if c['hips_dz_ratio'])"

if [[ -n "$SAMPLE" ]]; then
  step "process_model: sample AI model"
  bpy pm_sample "$TOOLS/process_model.py" "$SAMPLE" -o "$OUT/models/sample.glb" --target-tris 3000 \
    --height 1.2 --cleanup
  check "$OUT/logs/pm_sample.json" "d['tris_after'] <= 3060 and abs(d['dims_godot_m'][1] - 1.2) < 1e-3 and all(max(t['size_after']) <= 1024 for t in d['textures'])"
  bpy props "$TOOLS/tests/make_test_props.py" --src "$SAMPLE" --out-dir "$OUT/props"
  bpy pm_pbr "$TOOLS/process_model.py" "$OUT/props/pbr_prop.glb" -o "$OUT/models/pbr_prop.glb" \
    --target-tris 2500 --height 1.0
  check "$OUT/logs/pm_pbr.json" "sorted(t['role'] for t in d['textures']) == ['basecolor', 'emission', 'normal', 'orm']"
  bpy pm_multi "$TOOLS/process_model.py" "$OUT/props/multi_prop.glb" -o "$OUT/models/multi_prop.glb" \
    --target-tris 4000 --width 2.0 --facing x+ --cleanup
  check "$OUT/logs/pm_multi.json" "d['materials'] == ['multi_prop_0', 'multi_prop_1'] and abs(max(d['dims_godot_m'][0], d['dims_godot_m'][2]) - 2.0) < 1e-3"
fi

step "texture_tools"
if [[ ${#TEXS[@]} -eq 0 ]]; then
  python3 - "$OUT/tex" <<'EOF'
import sys, numpy as np
from PIL import Image
rng = np.random.default_rng(7)
for name, col in (("noise_a", (90, 140, 60)), ("noise_b", (140, 100, 60))):
    base = rng.random((32, 32)).astype(np.float32)
    big = np.asarray(Image.fromarray((base * 255).astype(np.uint8)).resize((1024, 1024), Image.BICUBIC), np.float32) / 255
    yy = np.linspace(0.75, 1.15, 1024)[:, None]  # lighting gradient -> not tileable
    img = np.clip(np.array(col, np.float32) * (0.6 + 0.6 * big[..., None]) * yy[..., None], 0, 255)
    Image.fromarray(img.astype(np.uint8)).save(f"{sys.argv[1]}/{name}.png")
EOF
  TEXS=("$OUT/tex/noise_a.png" "$OUT/tex/noise_b.png")
fi
python3 "$TOOLS/texture_tools.py" seamless "${TEXS[@]}" --out-dir "$OUT/tex/seamless" --preview > "$OUT/logs/seamless.json"
check "$OUT/logs/seamless.json" "all(e['after']['seam']['x'] < 1.5 and e['after']['seam']['y'] < 1.5 for e in d['seamless'])"
python3 "$TOOLS/texture_tools.py" palette-match "${TEXS[1]:-${TEXS[0]}}" --ref "${TEXS[0]}" -o "$OUT/tex/matched.png" --strength 1.0 > "$OUT/logs/palette.json"
check "$OUT/logs/palette.json" "all(abs(a - b) < 1.0 for a, b in zip(d['palette_match'][0]['lab_after']['mean'], d['palette_match'][0]['lab_reference']['mean']))"
python3 "$TOOLS/texture_tools.py" array "$OUT"/tex/seamless/*.png -o "$OUT/tex/terrain_array.png" --size 512 --godot-import > "$OUT/logs/array.json"
check "$OUT/logs/array.json" "d['array']['layer_size'] == [512, 512] and d['array']['import_file'].endswith('.import')"
python3 - "$OUT/icons/subject.png" <<'EOF'
import sys
from PIL import Image, ImageDraw
im = Image.new("RGB", (1024, 1024), (230, 222, 205))
d = ImageDraw.Draw(im)
d.ellipse((200, 380, 560, 760), fill=(150, 60, 40)); d.rectangle((330, 250, 430, 420), fill=(90, 90, 110))
im.save(sys.argv[1])
EOF
python3 "$TOOLS/texture_tools.py" icon "$OUT/icons/subject.png" -o "$OUT/icons/subject" --frame "#b08d3c" --disabled > "$OUT/logs/icon.json"
check "$OUT/logs/icon.json" "len(d['icon']['files']) == 4 and d['icon']['crop']['auto_bbox'][0] > 150"
python3 "$TOOLS/texture_tools.py" atlas "$OUT"/icons/subject_64.png "$OUT"/icons/subject_64_dis.png -o "$OUT/icons/atlas.png" --padding 2 > "$OUT/logs/atlas.json"
check "$OUT/logs/atlas.json" "d['atlas']['size'] == [136, 68]"

step "Godot: every GLB loads through GLTFDocument without errors"
python3 "$TOOLS/render_preview.py" --info-only "$OUT"/models/*.glb > "$OUT/logs/godot_info.json"
check "$OUT/logs/godot_info.json" "d['ok'] and not d['load_errors']"
check "$OUT/logs/godot_info.json" "[a['name'] for a in next(f for f in d['files'] if f['glb'].endswith('char_a_merged.glb'))['godot']['animations']] == ['attack', 'death', 'idle', 'walk']"

if [[ "$RENDER" == "1" ]]; then
  step "contact sheets (Xvfb + Vulkan)"
  python3 "$TOOLS/render_preview.py" "$OUT/models/char_a_merged.glb" "$OUT/models/char_b_retargeted.glb" \
    -o "$OUT/sheets" > "$OUT/logs/sheets.json"
  check "$OUT/logs/sheets.json" "d['ok'] and all(f.get('sheet') for f in d['files'])"
fi
printf '\nALL CHECKS PASSED  (outputs in %s)\n' "$OUT" >&2
