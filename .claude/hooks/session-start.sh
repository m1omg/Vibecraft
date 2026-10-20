#!/bin/bash
# Installs the Vibecraft toolchain for Claude Code cloud sessions:
# Godot 4.7.2 (editor/runtime), Blender bpy (asset tooling), lavapipe Vulkan + Xvfb (screenshots),
# FluidSynth + FluidR3_GM soundfont + mido (music toolkit).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

GODOT_VERSION="4.7.2-stable"
GODOT_DIR="/opt/godot"
GODOT_BIN="$GODOT_DIR/Godot_v${GODOT_VERSION}_linux.x86_64"
BPY_ENV="/opt/bpyenv/v313"

# --- Godot -------------------------------------------------------------------
if [ ! -x "$GODOT_BIN" ]; then
  mkdir -p "$GODOT_DIR"
  curl -sSL --retry 4 --retry-delay 2 -o "$GODOT_DIR/godot.zip" \
    "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}/Godot_v${GODOT_VERSION}_linux.x86_64.zip"
  unzip -oq "$GODOT_DIR/godot.zip" -d "$GODOT_DIR"
  rm -f "$GODOT_DIR/godot.zip"
fi
ln -sf "$GODOT_BIN" /usr/local/bin/godot

# --- Software Vulkan (lavapipe) + virtual display for screenshots -------------
if [ ! -f /usr/share/vulkan/icd.d/lvp_icd.json ] || ! command -v xvfb-run >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y -q mesa-vulkan-drivers libvulkan1 xvfb >/dev/null 2>&1 \
    || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q mesa-vulkan-drivers libvulkan1 xvfb >/dev/null; }
fi

# --- Blender as a Python module (mesh cleanup, rigging, GLB export) -----------
if ! "$BPY_ENV/bin/python" -c "import bpy, PIL, numpy" >/dev/null 2>&1; then
  command -v uv >/dev/null 2>&1 || pip install -q uv
  mkdir -p "$(dirname "$BPY_ENV")"
  [ -x "$BPY_ENV/bin/python" ] || uv venv -q --python 3.13 "$BPY_ENV"
  uv pip install -q --python "$BPY_ENV/bin/python" "bpy>=5.2,<5.3" pillow numpy
fi

echo "export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json" >> "${CLAUDE_ENV_FILE:-/dev/null}"
echo "export BLENDER_PY=$BPY_ENV/bin/python" >> "${CLAUDE_ENV_FILE:-/dev/null}"

# --- Music toolkit (tools/music): FluidSynth, the FluidR3_GM soundfont, mido ---
# Not needed by the game or its tests, so a failure here never blocks the session.
if ! command -v fluidsynth >/dev/null 2>&1 || [ ! -f /usr/share/sounds/sf2/FluidR3_GM.sf2 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y -q fluidsynth fluid-soundfont-gm >/dev/null 2>&1 \
    || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q fluidsynth fluid-soundfont-gm >/dev/null 2>&1; } \
    || echo "session-start: fluidsynth / fluid-soundfont-gm not installed (tools/music cannot render)" >&2
fi
if ! python3 -c "import mido, numpy, PIL" >/dev/null 2>&1; then
  pip install -q mido numpy pillow >/dev/null 2>&1 \
    || pip install -q --break-system-packages mido numpy pillow >/dev/null 2>&1 \
    || echo "session-start: mido not installed (tools/music cannot write MIDI)" >&2
fi

# --- Import the Godot project so headless tests can run immediately -----------
if [ -f "$CLAUDE_PROJECT_DIR/project.godot" ]; then
  timeout 600 godot --headless --path "$CLAUDE_PROJECT_DIR" --import >/dev/null 2>&1 || true
fi
