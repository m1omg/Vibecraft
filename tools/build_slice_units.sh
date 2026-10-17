#!/bin/bash
# Rebuild every slice character from assets_src with the free auto-rigger.
# Usage: tools/build_slice_units.sh [unit_id ...]   (default: all)
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${BLENDER_PY:-/opt/bpyenv/v313/bin/python}
L=assets_src/characters/kingdom_infantry
OUT=assets/models/units
LOG=${LOG_DIR:-/tmp/vibecraft_unit_logs}
mkdir -p "$OUT" "$LOG"
IDLE=$L/rig_idle.glb; WALK=$L/rig_walk.glb; DEATH=$L/rig_death.glb
SWORD=$L/rig_attack_sword.glb; HEAVY=$L/rig_heavy_swing.glb; THROW=$L/rig_throw.glb; CAST=$L/rig_cast.glb

# unit_id | source mesh | height m | extra clips
UNITS=(
  "kingdom_infantry|$L/model_tripo_h31.glb|1.75|attack=$SWORD"
  "kingdom_hodman|assets_src/characters/kingdom_hodman/model_tripo_h31.glb|1.3|attack=$HEAVY work=$HEAVY"
  "kingdom_hookgunner|assets_src/characters/kingdom_hookgunner/model_tripo_h31.glb|1.75|attack=$THROW"
  "kingdom_linden_sister|assets_src/characters/kingdom_linden_sister/model_tripo_h31.glb|1.7|attack=$CAST cast=$CAST"
  "kingdom_wheel_marshal|assets_src/characters/kingdom_wheel_marshal/model_tripo_h31.glb|2.15|attack=$HEAVY cast=$CAST"
  "kingdom_firewright|assets_src/characters/kingdom_firewright/model_tripo_h31.glb|2.1|attack=$THROW cast=$CAST"
  "clans_yurtwright|assets_src/characters/clans_yurtwright/model_tripo_h31.glb|1.35|attack=$HEAVY work=$HEAVY"
  "clans_grappler|assets_src/characters/clans_grappler/model_tripo_h31.glb|2.0|attack=$HEAVY"
  "clans_javelineer|assets_src/characters/clans_javelineer/model_tripo_h31.glb|1.8|attack=$THROW"
  "clans_gustcaller|assets_src/characters/clans_gustcaller/model_tripo_h31.glb|1.8|attack=$CAST cast=$CAST"
  "clans_hero_uncut|assets_src/characters/clans_hero_uncut/model_tripo_h31.glb|2.15|attack=$SWORD cast=$CAST"
  "clans_skymirror|assets_src/characters/clans_skymirror/model_tripo_h31.glb|2.15|attack=$CAST cast=$CAST"
)
want=" $* "
fail=0
for row in "${UNITS[@]}"; do
  IFS='|' read -r id src h extra <<<"$row"
  [[ $# -gt 0 && "$want" != *" $id "* ]] && continue
  args=(--clip idle=$IDLE --clip walk=$WALK --clip death=$DEATH)
  for c in $extra; do args+=(--clip "$c"); done
  if "$PY" tools/autorig.py "$src" -o "$OUT/$id.glb" --template "$WALK" --facing +x --height "$h" \
      "${args[@]}" --target-tris 4500 --team-mask 300:45:0.3 --name "$id" ${FORCE:+--force} >"$LOG/$id.json" 2>"$LOG/$id.err"; then
    echo "OK   $id"
  else
    echo "FAIL $id (exit $?, see $LOG/$id.err)"; fail=1
  fi
done
exit $fail

# Signature buildings (static): Tripo H3.1 raw files face +X; the Moot Hall needs an extra 90 deg yaw so the door faces the camera.
if [[ $# -eq 0 || "$want" == *" buildings "* ]]; then
  mkdir -p assets/models/buildings
  "$PY" tools/process_model.py assets_src/buildings/kingdom_moot_hall/model_tripo_h31.glb -o assets/models/buildings/kingdom_moot_hall.glb \
    --target-tris 12000 --width 8 --facing +x --yaw 90 --team-mask 300:45:0.3 --name kingdom_moot_hall >"$LOG/kingdom_moot_hall.json" 2>&1 && echo "OK   kingdom_moot_hall"
  "$PY" tools/process_model.py assets_src/buildings/clans_shell_hall/model_tripo_h31.glb -o assets/models/buildings/clans_shell_hall.glb \
    --target-tris 12000 --width 8 --facing +x --team-mask 300:45:0.3 --name clans_shell_hall >"$LOG/clans_shell_hall.json" 2>&1 && echo "OK   clans_shell_hall"
fi
