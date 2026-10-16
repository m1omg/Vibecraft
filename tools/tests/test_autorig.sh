#!/usr/bin/env bash
# End-to-end test of tools/autorig.py (free local auto-rigger) on real and synthetic meshes.
#
#   tools/tests/test_autorig.sh OUT_DIR
#
# (a) the exact static mesh the paid Meshy rig was made on -> joint error vs that rig
#     (target: mean < 4 cm, max < 8 cm)
# (b) the same character from two other generators (Trellis, Tripo legacy): joint error vs the
#     template rig is only indicative (different meshes), "aligned" removes the horizontal offset
# (c) synthetic bodies with known joints (tests/make_autorig_bodies.py): a hunched 2.1 m brute,
#     a 1.9 m robed caster with a staff, a 1.1 m big-headed worker
# Every output gets the library clips idle/walk/attack/death, is decimated to 4500 tris with a
# team mask (game-ready, faces -Z), and is checked: no unweighted vertices, <= 4 influences,
# 4 clips, clips face forward on average (|mean facing| < 5 deg), a joint error budget per mesh.
# The deformation QA (max vertex displacement / height, edge stretch deformed/rest, edges
# stretched > 2x, foot slide) is printed as a table; contact sheets go to OUT_DIR/sheets.
#
# Env: VC_BPY (bpy python, default /opt/bpyenv/v313/bin/python), RENDER=0 skips contact sheets,
#      VC_KINGDOM (folder with the kingdom_infantry test assets).
# Exit code != 0 when a check fails (all meshes are still processed first).
set -euo pipefail

OUT=${1:?usage: test_autorig.sh OUT_DIR}
PY=${VC_BPY:-/opt/bpyenv/v313/bin/python}
RENDER=${RENDER:-1}
TOOLS=$(cd "$(dirname "$0")/.." && pwd)
K=${VC_KINGDOM:-$TOOLS/../assets_src/characters/kingdom_infantry}
mkdir -p "$OUT"/{bodies,models,sheets,debug,logs}
OUT=$(cd "$OUT" && pwd)
TEMPLATE="$K/rig_walk.glb"
CLIPS=(--clip "idle=$K/rig_idle.glb" --clip "walk=$K/rig_walk.glb"
       --clip "attack=$K/rig_attack_sword.glb" --clip "death=$K/rig_death.glb")
FAILED=0

step() { printf '\n== %s\n' "$*" >&2; }
check() {  # check JSON_FILE PYTHON_EXPR  (d = parsed json)
  python3 - "$1" "$2" <<'EOF' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
ok = eval(sys.argv[2], {"d": d})
print(("PASS " if ok else "FAIL ") + sys.argv[1].rsplit("/", 1)[-1] + ": " + sys.argv[2], file=sys.stderr)
sys.exit(0 if ok else 1)
EOF
}
rig() {  # rig NAME INPUT [autorig args...]
  local name=$1 input=$2; shift 2
  step "autorig $name"
  "$PY" "$TOOLS/autorig.py" "$input" -o "$OUT/models/$name.glb" --template "$TEMPLATE" "${CLIPS[@]}" \
    --target-tris 4500 --team-mask 300:45:0.3 --name "$name" --debug-png "$OUT/debug/$name.png" \
    --keep-rig "$OUT/models/${name}_rig_fullres.glb" "$@" \
    >"$OUT/logs/$name.json" 2>"$OUT/logs/$name.log" || { tail -20 "$OUT/logs/$name.log"; FAILED=1; return; }
  local j="$OUT/logs/$name.json"
  check "$j" "d['qa']['unweighted_verts'] == 0 and d['qa']['max_influences'] <= 4"
  check "$j" "sorted(d['qa']['clips']) == ['attack', 'death', 'idle', 'walk']"
  check "$j" "all(abs(c['mean_facing_deg']) < 5 for c in d['qa']['clips'].values())"
  if [ "$RENDER" != 0 ]; then
    python3 "$TOOLS/render_preview.py" "$OUT/models/$name.glb" -o "$OUT/sheets/$name.png" \
      --fractions 0,0.25,0.5,0.75 --size 256 >"$OUT/logs/${name}_render.json" 2>&1 || { echo "render failed: $name"; FAILED=1; }
  fi
}

step "synthetic bodies (brute / caster / worker) with ground-truth joints"
"$PY" "$TOOLS/tests/make_autorig_bodies.py" --mesh "$K/rig_source_facing_pz.glb" --rig "$TEMPLATE" \
  --out-dir "$OUT/bodies" >"$OUT/logs/bodies.json" 2>"$OUT/logs/bodies.log"

# (a) the paid rig's own mesh: the real accuracy test
rig a_template_mesh "$K/rig_source_facing_pz.glb" --facing +z --reference-rig "$TEMPLATE"
check "$OUT/logs/a_template_mesh.json" "d['joint_error']['mean_cm'] < 4 and d['joint_error']['max_cm'] < 8"
check "$OUT/logs/a_template_mesh.json" "not d['landmarks']['fallback_joints']"

# (b) same character, other generators (already processed: tris ~4k). Trellis faces -Z, the Tripo
#     legacy file actually faces -X (found by --facing auto; checked below)
rig b_trellis "$K/bakeoff_trellis_4k.glb" --facing=-z --height 1.75 --reference-rig "$TEMPLATE"
rig b_tripo_legacy "$K/bakeoff_tripo_legacy_4k.glb" --facing auto --height 1.75 --reference-rig "$TEMPLATE"
check "$OUT/logs/b_tripo_legacy.json" "d['facing_check'].get('applied_turn_deg') == 90.0"
for n in b_trellis b_tripo_legacy; do
  check "$OUT/logs/$n.json" "not d['landmarks']['fallback_joints'] and d['joint_error']['aligned_core_mean_cm'] < 8"
done

# (c) different proportions with ground truth
for n in brute caster worker; do
  h=$(python3 -c "import json;print(json.load(open('$OUT/bodies/${n}_joints.json'))['height'])")
  rig "c_$n" "$OUT/bodies/$n.glb" --facing +z --height "$h" --reference-joints "$OUT/bodies/${n}_joints.json"
done
check "$OUT/logs/c_brute.json" "d['joint_error']['core_mean_cm'] < 5 and d['joint_error']['core_max_cm'] < 12"
check "$OUT/logs/c_caster.json" "d['joint_error']['core_mean_cm'] < 5 and d['joint_error']['core_max_cm'] < 12"
check "$OUT/logs/c_caster.json" "d['landmarks']['features']['legs'] != 'detected'"   # robe -> leg fallback
check "$OUT/logs/c_caster.json" "d['skin']['props']['prop_verts'].get('RightHand', 0) > 20"   # staff on the hand
check "$OUT/logs/c_worker.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 8"

step "summary"
python3 - "$OUT" <<'EOF'
import glob, json, os, sys
out = sys.argv[1]
rows = []
for j in sorted(glob.glob(os.path.join(out, "logs", "*.json"))):
    n = os.path.basename(j)[:-5]
    if n in ("bodies",) or n.endswith("_render"):
        continue
    d = json.load(open(j))
    je = d.get("joint_error") or {}
    lm = d["landmarks"]
    qa = d["qa"]
    print(f"\n### {n}  ({d['height_m']} m, {qa['tris']} tris, {d['seconds']} s)")
    print(f"features: {json.dumps(lm['features'])}")
    print(f"fallback joints: {lm['fallback_joints'] or 'none'};  props: {d['skin'].get('props', {}).get('prop_verts')}")
    if je:
        print(f"joint error cm: mean {je['mean_cm']} max {je['max_cm']} ({je['worst']}) | core mean {je['core_mean_cm']} "
              f"max {je['core_max_cm']} | horizontally aligned core mean {je['aligned_core_mean_cm']} max {je['aligned_core_max_cm']}")
    print(f"skin: unweighted {qa['unweighted_verts']}, max influences {qa['max_influences']}, bones used {qa['groups_used']}")
    print("| clip | max disp/H | stretch max | p99.9 | edges >2x | facing deg | foot slide cm (L/R toe) |")
    print("|---|---|---|---|---|---|---|")
    for c, m in sorted(qa["clips"].items()):
        fs = m["foot_slide_cm"]
        print(f"| {c} | {m['max_disp_ratio']} | {m['stretch_max']} | {m['stretch_p999']} | {m['edges_over_2x']} | "
              f"{m['mean_facing_deg']} | {fs.get('LeftToeBase')}/{fs.get('RightToeBase')} |")
EOF
[ "$RENDER" != 0 ] && echo "sheets: $OUT/sheets/*.png   joint overlays: $OUT/debug/*.png" >&2
if [ "$FAILED" != 0 ]; then echo "SOME CHECKS FAILED" >&2; exit 1; fi
echo "ALL CHECKS PASSED" >&2
