#!/usr/bin/env bash
# test_determinism.sh: render the two style tests twice from scratch (no stem cache) and require
# byte-identical MIDI, stems (every track) and Ogg masters. Headless: python3, fluidsynth and ffmpeg only.
#
#   bash tools/music/test_determinism.sh            # both style tests
#   bash tools/music/test_determinism.sh --help
#   PIECES="tools/music/pieces/style_clans.py" bash tools/music/test_determinism.sh
#
# Exit 0 when every hash matches, 1 otherwise. Work files go to tests/output/music/determinism/ (git-ignored).
set -euo pipefail
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PIECES="${PIECES:-tools/music/pieces/style_kingdom.py tools/music/pieces/style_clans.py}"
OUT="tests/output/music/determinism"
rm -rf "$OUT"
mkdir -p "$OUT"
status=0
for piece in $PIECES; do
  name="$(basename "$piece" .py)"
  for run in a b; do
    python3 tools/music/render.py "$piece" --no-cache --no-png --no-levels \
      --work "$OUT/$run/$name" --out "$OUT/$run/$name.ogg" > "$OUT/$run-$name.json"
  done
  if python3 - "$OUT/a-$name.json" "$OUT/b-$name.json" <<'EOF'
import json, sys
a = json.load(open(sys.argv[1]))["hashes"]
b = json.load(open(sys.argv[2]))["hashes"]
bad = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
print(f"  {len(a)} hashes compared (midi, {sum(1 for k in a if k.startswith('stem:'))} stems, ogg)")
for k in bad:
    print(f"  DIFF {k}: {a.get(k)} != {b.get(k)}")
sys.exit(1 if bad else 0)
EOF
  then
    echo "PASS $name"
  else
    echo "FAIL $name"
    status=1
  fi
done
exit $status
