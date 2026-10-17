#!/usr/bin/env bash
# End-to-end test of tools/autorig.py (free local auto-rigger) on real and synthetic meshes.
#
#   tools/tests/test_autorig.sh OUT_DIR
#
# (a) the exact static mesh the paid Meshy rig was made on -> joint error vs that rig
#     (target: mean < 4 cm, max < 8 cm). NB the landmark coefficients are calibrated on this very
#     mesh (the template's skinned mesh), so (a) checks the fit is reproducible; (b) to (d) are the
#     generalisation tests.
# (a2) the raw Tripo file of that mesh (faces +X, 1 m tall) with all 7 library clips and NO --facing
#     (detected from the feet); (a3) the same file with a wrong --facing must stop with exit code 2
# (b) the same character from two other generators (Trellis, Tripo legacy): joint error vs the
#     template rig is only indicative (different meshes), "aligned" removes the horizontal offset
# (c) synthetic bodies with known joints (tests/make_autorig_bodies.py): a hunched 2.1 m brute,
#     a 1.9 m robed caster with a staff, a 1.1 m big-headed worker, a 2.1 m hero with a cape
# (d) the failure modes found in QA, with known joints: arms 12 deg closer to the body (hands on
#     the thighs), a two-handed staff through both fists, a diagonal polearm across the chest,
#     bulky knee armour (thighs touch below the crotch; bone heat fails at the default voxel size),
#     a 1.2 m squat body with 0.6x legs
# Every output gets the library clips idle/walk/attack/death, is decimated to 4500 tris with a
# team mask (game-ready, faces -Z), and is checked: exit code 0 (no errors), bone heat succeeded,
# no unweighted vertices, <= 4 influences, the clips, a joint error budget per mesh, and per clip:
#   * facing: the reference the fix used (torso for idle/walk/death, head for attack) is within
#     5 deg, and walk is also checked with the independent head and feet directions; attack's head
#     direction is compared with the shipped paid unit's (raw library clip, no fix)
#   * feet: in walk and idle the skinned feet never sink more than 1.5 cm into the floor, and in
#     walk each foot lifts at least 2 cm
#   * attack planted-toe slide <= 1.3 x the source clip's (scaled by the leg ratio) + 1 cm
#   * long held props (staff, polearm) stay rigid: Kabsch residual < 1 cm in every clip
# The deformation QA (edge stretch deformed/rest, edges stretched > 2x, facing, toe slide, stance
# speed, foot height range, prop rigidity) is printed as a table next to the same metrics of the
# shipped paid-rig unit (assets/models/units/kingdom_infantry.glb, if present); contact sheets go
# to OUT_DIR/sheets, joint overlays to OUT_DIR/debug.
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
PAID="$TOOLS/../assets/models/units/kingdom_infantry.glb"
FAILED=0

step() { printf '\n== %s\n' "$*" >&2; }
check() {  # check JSON_FILE PYTHON_EXPR  (d = parsed json, p = paid baseline json or None)
  python3 - "$1" "$2" "$OUT/logs/paid_baseline.json" <<'EOF' || FAILED=1
import json, os, sys
d = json.load(open(sys.argv[1]))
p = json.load(open(sys.argv[3])) if os.path.exists(sys.argv[3]) else None
ok = eval(sys.argv[2], {"d": d, "p": p})
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
  check "$j" "not d['errors'] and d['skin']['method_effective'] == 'heat'"
  check "$j" "d['qa']['unweighted_verts'] == 0 and d['qa']['max_influences'] <= 4"
  check "$j" "{'attack', 'death', 'idle', 'walk'} <= set(d['qa']['clips'])"
  # facing: the fix's own reference, and walk with two independent directions
  check "$j" "all(abs(d['qa']['clips'][c['name']]['facing_deg'][c['facing_fix']['reference']]) < 5 for c in d['clips'])"
  check "$j" "abs(d['qa']['clips']['walk']['facing_deg']['head']) < 10 and abs(d['qa']['clips']['walk']['facing_deg']['feet']) < 15"
  check "$j" "p is None or abs(d['qa']['clips']['attack']['facing_deg']['head'] - p['qa']['clips']['attack']['facing_deg']['head']) < 10"
  # feet: no sinking in walk/idle, a visible step in walk
  check "$j" "all(v[0] >= -1.5 for c in ('walk', 'idle') for v in d['qa']['clips'][c]['foot_low_cm'].values())"
  check "$j" "all(v[1] >= 2.0 for v in d['qa']['clips']['walk']['foot_low_cm'].values())"
  # attack: planted feet don't slide much more than in the source clip
  check "$j" "all(d['qa']['clips']['attack']['planted_toe_slide_cm'][s] <= 1.3 * v + 1.0 for c in d['clips'] if c['name'] == 'attack' for s, v in c['source_planted_toe_slide_cm'].items())"
  if [ "$RENDER" != 0 ]; then
    python3 "$TOOLS/render_preview.py" "$OUT/models/$name.glb" -o "$OUT/sheets/$name.png" \
      --fractions 0,0.25,0.5,0.75 --size 256 >"$OUT/logs/${name}_render.json" 2>&1 || { echo "render failed: $name"; FAILED=1; }
  fi
}

# reference: the same QA on the shipped unit rigged by the paid service (same decimation/team mask)
if [ -f "$PAID" ]; then
  step "paid-rig baseline (QA only)"
  "$PY" "$TOOLS/autorig.py" --qa-only "$PAID" >"$OUT/logs/paid_baseline.json" 2>"$OUT/logs/paid_baseline.log" || FAILED=1
fi

step "synthetic bodies with ground-truth joints"
"$PY" "$TOOLS/tests/make_autorig_bodies.py" --mesh "$K/rig_source_facing_pz.glb" --rig "$TEMPLATE" \
  --out-dir "$OUT/bodies" --variants brute,caster,worker,hero,armsin12,staff2h,polearm,knees,squat \
  >"$OUT/logs/bodies.json" 2>"$OUT/logs/bodies.log"

# (a) the paid rig's own mesh: the real accuracy test
rig a_template_mesh "$K/rig_source_facing_pz.glb" --facing +z --reference-rig "$TEMPLATE"
check "$OUT/logs/a_template_mesh.json" "d['joint_error']['mean_cm'] < 4 and d['joint_error']['max_cm'] < 8"
check "$OUT/logs/a_template_mesh.json" "not d['landmarks']['fallback_joints'] and not d['landmarks']['level_fallbacks']"

# (a2) raw generator output: faces +X (no --facing: found from the feet), arbitrary scale, every clip
rig a2_raw_tripo "$K/model_tripo_h31.glb" --height 1.75 --reference-rig "$TEMPLATE" \
  --clip "cast=$K/rig_cast.glb" --clip "heavy=$K/rig_heavy_swing.glb" --clip "throw=$K/rig_throw.glb"
check "$OUT/logs/a2_raw_tripo.json" "d['facing_check'].get('applied_turn_deg') == -90.0"
check "$OUT/logs/a2_raw_tripo.json" "d['joint_error']['mean_cm'] < 4 and d['joint_error']['max_cm'] < 8"
check "$OUT/logs/a2_raw_tripo.json" "len(d['qa']['clips']) == 7"

# (a3) a wrong --facing (the feet disagree with full confidence) stops the run: exit code 2
step "autorig a3_wrong_facing (must fail)"
set +e
"$PY" "$TOOLS/autorig.py" "$K/model_tripo_h31.glb" -o "$OUT/models/a3_wrong_facing.glb" --template "$TEMPLATE" \
  --facing +z --height 1.75 >"$OUT/logs/a3_wrong_facing.json" 2>"$OUT/logs/a3_wrong_facing.log"
ec=$?
set -e
if [ "$ec" != 2 ] || [ -e "$OUT/models/a3_wrong_facing.glb" ]; then
  echo "FAIL a3_wrong_facing: exit code $ec (expected 2) or an output was written" >&2; FAILED=1
else echo "PASS a3_wrong_facing: exit code 2, no output" >&2; fi
check "$OUT/logs/a3_wrong_facing.json" "len(d['errors']) == 1 and 'facing' in d['errors'][0]"

# (b) same character, other generators (already processed: tris ~4k). Trellis faces -Z, the Tripo
#     legacy file actually faces -X (found from the feet; checked below)
rig b_trellis "$K/bakeoff_trellis_4k.glb" --facing=-z --height 1.75 --reference-rig "$TEMPLATE"
rig b_tripo_legacy "$K/bakeoff_tripo_legacy_4k.glb" --height 1.75 --reference-rig "$TEMPLATE"
check "$OUT/logs/b_tripo_legacy.json" "d['facing_check'].get('applied_turn_deg') == 90.0"
for n in b_trellis b_tripo_legacy; do
  check "$OUT/logs/$n.json" "not d['landmarks']['fallback_joints'] and d['joint_error']['aligned_core_mean_cm'] < 8"
done

# (c) different proportions with ground truth
for n in brute caster worker hero; do
  h=$(python3 -c "import json;print(json.load(open('$OUT/bodies/${n}_joints.json'))['height'])")
  rig "c_$n" "$OUT/bodies/$n.glb" --facing +z --height "$h" --reference-joints "$OUT/bodies/${n}_joints.json"
done
check "$OUT/logs/c_brute.json" "d['joint_error']['core_mean_cm'] < 5 and d['joint_error']['core_max_cm'] < 12"
check "$OUT/logs/c_caster.json" "d['joint_error']['core_mean_cm'] < 5 and d['joint_error']['core_max_cm'] < 12"
check "$OUT/logs/c_caster.json" "d['landmarks']['features']['legs'] != 'detected'"   # robe -> leg fallback
check "$OUT/logs/c_caster.json" "d['qa']['long_prop_islands'] == 1 and all(c['prop_rigidity_cm'] < 1 for c in d['qa']['clips'].values())"
check "$OUT/logs/c_worker.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 8"
check "$OUT/logs/c_hero.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 10"
if [ "$RENDER" != 0 ]; then   # the cape is behind: render a copy turned 180 deg (arrow then points backwards)
  "$PY" "$TOOLS/process_model.py" "$OUT/models/c_hero.glb" -o "$OUT/models/c_hero_turned.glb" --facing +z \
    --name c_hero_turned >/dev/null 2>&1 &&
  python3 "$TOOLS/render_preview.py" "$OUT/models/c_hero_turned.glb" -o "$OUT/sheets/c_hero_back.png" \
    --fractions 0,0.25,0.5,0.75 --size 256 --no-ingame >/dev/null 2>&1 || { echo "render failed: c_hero_back"; FAILED=1; }
fi

# (d) the QA failure modes, with ground truth
for n in armsin12 staff2h polearm knees squat; do
  h=$(python3 -c "import json;print(json.load(open('$OUT/bodies/${n}_joints.json'))['height'])")
  rig "d_$n" "$OUT/bodies/$n.glb" --height "$h" --reference-joints "$OUT/bodies/${n}_joints.json"
done
# hands on the thighs / a staff through both fists: the trunk must not collapse to hand height
for n in d_armsin12 d_staff2h; do
  check "$OUT/logs/$n.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 10"
  check "$OUT/logs/$n.json" "abs(d['landmarks']['features']['shoulder_top_y'] - d['landmarks']['template_features']['shoulder_top_y']) < 0.05"
done
# long props: one rigid piece with one hand (two-handed: the right hand), in every clip
for n in d_staff2h d_polearm; do
  check "$OUT/logs/$n.json" "d['qa']['long_prop_islands'] == 1 and all(c['prop_rigidity_cm'] < 1 for c in d['qa']['clips'].values())"
  check "$OUT/logs/$n.json" "[i['prop_of'] for i in d['skin']['props']['islands'] if i.get('long_prop')] == ['R']"
done
check "$OUT/logs/d_staff2h.json" "[i['two_handed'] for i in d['skin']['props']['islands'] if i.get('long_prop')] == [True]"
check "$OUT/logs/d_polearm.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 8"
# knee armour: crotch not taken at the knees/thighs; the retry finds a voxel size where bone heat works
check "$OUT/logs/d_knees.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 8"
check "$OUT/logs/d_knees.json" "d['landmarks']['features']['legs'] == 'detected'"
# short legs: steps still lift the feet (checked for every mesh in rig()), joints
check "$OUT/logs/d_squat.json" "d['joint_error']['core_mean_cm'] < 4 and d['joint_error']['core_max_cm'] < 8"

step "summary"
python3 - "$OUT" <<'EOF'
import glob, json, os, sys
out = sys.argv[1]
for j in sorted(glob.glob(os.path.join(out, "logs", "*.json"))):
    n = os.path.basename(j)[:-5]
    if n in ("bodies", "a3_wrong_facing") or n.endswith("_render"):
        continue
    d = json.load(open(j))
    je = d.get("joint_error") or {}
    qa = d["qa"]
    if "landmarks" not in d:      # --qa-only reference
        print(f"\n### {n}  (paid rig, {qa['tris']} tris)")
    else:
        lm = d["landmarks"]
        sk = d["skin"]
        print(f"\n### {n}  ({d['height_m']} m, {qa['tris']} tris, {d['seconds']} s)")
        print(f"features: {json.dumps(lm['features'])}")
        print(f"level fallbacks: {lm['level_fallbacks'] or 'none'}; fallback joints: {lm['fallback_joints'] or 'none'}")
        print(f"skin: {sk['method_effective']} (attempts {[a['voxel_frac'] for a in sk.get('heat_attempts', [])]}); "
              f"props {sk.get('props', {}).get('prop_verts')}; long props "
              f"{[(i['prop_of'], i['two_handed']) for i in sk.get('props', {}).get('islands') or [] if i.get('long_prop')]}")
        print("clips: " + "; ".join(f"{c['name']} hips {c['hips_mode']}, facing ref "
                                     f"{c.get('facing_fix', {}).get('reference')}" for c in d["clips"]))
    if je:
        print(f"joint error cm: mean {je['mean_cm']} max {je['max_cm']} ({je['worst']}) | core mean {je['core_mean_cm']} "
              f"max {je['core_max_cm']} | horizontally aligned core mean {je['aligned_core_mean_cm']} max {je['aligned_core_max_cm']}")
    print(f"skin: unweighted {qa['unweighted_verts']}, max influences {qa['max_influences']}, bones used {qa['groups_used']}")
    print("| clip | stretch max | edges >2x | facing torso/head/feet deg | planted toe slide cm L/R | stance speed m/s L/R | foot low..high cm L / R | prop rigidity cm |")
    print("|---|---|---|---|---|---|---|---|")
    for c, m in sorted(qa["clips"].items()):
        ps, sp, fl, fd = m["planted_toe_slide_cm"], m["stance_speed_mps"], m["foot_low_cm"], m["facing_deg"]
        fls = " / ".join(f"{v[0]}..{v[1]}" for v in fl.values())
        print(f"| {c} | {m['stretch_max']} | {m['edges_over_2x']} | {fd['torso']}/{fd['head']}/{fd['feet']} | "
              f"{ps.get('L')}/{ps.get('R')} | {sp.get('L')}/{sp.get('R')} | {fls} | {m['prop_rigidity_cm']} |")
EOF
[ "$RENDER" != 0 ] && echo "sheets: $OUT/sheets/*.png   joint overlays: $OUT/debug/*.png" >&2
if [ "$FAILED" != 0 ]; then echo "SOME CHECKS FAILED" >&2; exit 1; fi
echo "ALL CHECKS PASSED" >&2
