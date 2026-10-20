#!/usr/bin/env python3
"""manifest.py: write assets/audio/music/manifest.json, the game's music list, from the files on disk.

  python3 tools/music/manifest.py            # rebuild the manifest (builds every piece's MIDI, measures every Ogg)
  python3 tools/music/manifest.py --check    # exit 1 when the manifest on disk differs from a rebuild

One entry per piece, keyed by its id:
  id, title, file (res:// path), faction (kingdom | clans | shared), kind (ingame | menu | score | victory | defeat
  | opening), loop (bool: menu and score only), duration (s, decoded), source (the piece module under
  tools/music/pieces/, or "ai" with the job id for the one generated cue), key_tempo, seed, midi_sha256 (the MIDI
  rebuilt from the source now), ogg_sha256, integrated_lufs / true_peak_dbtp / loudness_range_lu (ffmpeg loudnorm
  on the Ogg), format, listening_check (bible 10.1); victory and defeat stingers also get xfade_to_score_s, where the
  2 s crossfade into the score bed starts (the stinger's natural decay: its 100 ms level last within 20 dB of its
  loudest, but never later than 2 s before its end).
How the game plays them (faction rotation with 20-40 s gaps, loops, stinger into the score bed, opening cue): the
juice doc's MUS-* rows and tools/music/README.md "In the game".
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MUSIC = os.path.join(ROOT, "assets", "audio", "music")
OUT = os.path.join(MUSIC, "manifest.json")
JOBS = os.path.join(ROOT, "tools", "audio", "music_jobs.json")

# id, module (tools/music/pieces/<module>.py, None = generated), title, faction, kind, key and tempo
PIECES = [
    ("kingdom_1", "kingdom_1", 'Kingdom 1, "Market-Day Muster"', "kingdom", "ingame", "D Mixolydian, 92 BPM, 4/4"),
    ("kingdom_2", "kingdom_2", 'Kingdom 2, "Boards and Thunder"', "kingdom", "ingame",
     "G Dorian, 100 BPM, 4/4 (3+3+2)"),
    ("kingdom_3", "kingdom_3", 'Kingdom 3, "Linden Curfew"', "kingdom", "ingame", "A Dorian, 84 BPM, 3/4"),
    ("clans_1", "clans_1", 'Clans 1, "Herd Road"', "clans", "ingame", "D Dorian, 92 BPM, 4/4 (12-step drum grid)"),
    ("clans_2", "clans_2", 'Clans 2, "The Gong-Ring Gathers"', "clans", "ingame", "E Mixolydian, 84 BPM, 6/4"),
    ("clans_3", "clans_3", 'Clans 3, "Long Grass Gallop"', "clans", "ingame",
     "A Dorian, 100 BPM, 4/4 (outro slows to 72)"),
    ("menu", "menu", 'Menu, "Two Roads"', "shared", "menu", "D Dorian, 80 BPM, 4/4"),
    ("score", "score_bed", 'End-screen bed, "Two Roads (score)"', "shared", "score", "D Dorian, 72 BPM, 6/8"),
    ("victory_kingdom", "victory_kingdom", "Victory, kingdom", "kingdom", "victory", "D major, 96 BPM"),
    ("victory_clans", "victory_clans", "Victory, clans", "clans", "victory", "D Mixolydian, 88 BPM"),
    ("defeat_kingdom", "defeat_kingdom", "Defeat, kingdom", "kingdom", "defeat", "D minor (Aeolian), 60 BPM"),
    ("defeat_clans", "defeat_clans", "Defeat, clans", "clans", "defeat", "D Dorian, 60 BPM"),
    ("opening_kingdom", None, "Opening cue, kingdom", "kingdom", "opening", "D major"),
    ("opening_clans", "opening_clans", "Opening cue, clans", "clans", "opening", "D Dorian, 120 BPM"),
]
LOOPS = {"menu", "score"}
GENERATOR = ("composed in Python (tools/music: score.py, render.py); FluidSynth 2.3 with FluidR3_GM (MIT) and numpy "
             "synths; no paid generation")
LISTENING = "pending: bible 10.1 two-reviewer listening check before release"


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def loudness(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        "loudnorm=I=-16:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    j = json.loads(m.group(0))
    return round(float(j["input_i"]), 2), round(float(j["input_tp"]), 2), round(float(j["input_lra"]), 1)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels",
                        "-of", "json", path], stdout=subprocess.PIPE, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    return s, len(raw) // 2 / int(s["sample_rate"])


def decay_point(path, below_db=20.0, xfade_s=2.0):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", "48000", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    import numpy as np
    x = np.frombuffer(raw, dtype="<f4").astype(np.float64).reshape(-1, 2)
    w = 4800
    n = len(x) // w
    lv = 10 * np.log10((x[:n * w] ** 2).mean(1).reshape(n, w).mean(1) + 1e-20)
    last = (np.flatnonzero(lv > lv.max() - below_db)[-1] + 1) * w / 48000
    return round(min(last, len(x) / 48000 - xfade_s), 1)


def midi_sha(module):
    import render  # noqa: E402  (numpy, mido)
    piece, _ = render.load_piece(os.path.join(HERE, "pieces", module + ".py"))
    piece.compile()
    with tempfile.TemporaryDirectory() as td:
        mid = os.path.join(td, "x.mid")
        piece.write_midi(mid)
        return piece.seed, sha_file(mid)


def ai_job(pid):
    for j in json.load(open(JOBS))["jobs"]:
        if j["id"] == pid and j.get("result"):
            return j
    raise SystemExit(f"{pid}: no result in {os.path.relpath(JOBS, ROOT)}")


def build():
    out = {}
    for pid, module, title, faction, kind, key_tempo in PIECES:
        path = os.path.join(MUSIC, pid + ".ogg")
        if not os.path.exists(path):
            raise SystemExit(f"missing {os.path.relpath(path, ROOT)}")
        stream, dur = probe(path)
        lufs, tp, lra = loudness(path)
        e = {"id": pid, "title": title, "file": f"res://assets/audio/music/{pid}.ogg", "faction": faction,
             "kind": kind, "loop": pid in LOOPS, "duration": round(dur, 3)}
        if kind in ("victory", "defeat"):
            e["xfade_to_score_s"] = decay_point(path)
        if module:
            seed, msha = midi_sha(module)
            e.update(source=f"tools/music/pieces/{module}.py", generator=GENERATOR, key_tempo=key_tempo, seed=seed,
                     midi_sha256=msha)
        else:
            j = ai_job(pid)
            e.update(source="ai", job_id=j["result"]["job_id"], key_tempo=key_tempo,
                     generator=("ElevenLabs Music v2.5 through Krea, one 10 s probe (444 CU; paid music generation is "
                                "banned since), prompt bible 10.3, trimmed to 2.4 s by tools/audio/post_music.py"),
                     raw=j["result"].get("raw"))
        e.update(ogg_sha256=sha_file(path), integrated_lufs=lufs, true_peak_dbtp=tp, loudness_range_lu=lra,
                 format="Ogg Vorbis q6, %d kHz %s" % (int(stream["sample_rate"]) // 1000,
                                                      "stereo" if stream["channels"] == 2 else "mono"),
                 listening_check=LISTENING)
        out[pid] = e
    return out


def dump(m):
    return json.dumps(m, indent=1, ensure_ascii=False) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    m = build()
    if "--check" in argv:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        ok = cur == dump(m)
        print("music manifest up to date" if ok else "music manifest differs from a rebuild")
        return 0 if ok else 1
    with open(OUT, "w") as f:
        f.write(dump(m))
    print("music manifest: %d pieces -> %s" % (len(m), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
