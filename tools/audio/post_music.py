#!/usr/bin/env python3
"""Post-process a generated music file (art-and-audio bible 10.4) into the game's Ogg Vorbis.

  post_music.py RAW OUT.ogg --kind track|loop|opening [--lufs -16] [--cue-s 2.4] [--cue-fade-ms 300] [--xfade-s 3]

  track    trim leading silence and the tail (last sound above -50 dB of the peak, + 0.4 s, 1.5 s fade-out),
           loudness-normalise to about -16 LUFS integrated (two-pass ffmpeg loudnorm, true peak -1.5 dBTP),
           Ogg Vorbis stereo 48 kHz -q:a 6 (the game's music format; the raw generation is resampled).
  loop     as track, then the last --xfade-s seconds are crossfaded into the start so the file loops
           seamlessly (the menu and score beds).
  opening  trim leading silence, keep the first --cue-s seconds (2.4 s), --cue-fade-ms fade-out (300 ms),
           normalise the same way (short-term gating makes the integrated value approximate for 2.4 s).

Prints a JSON line with the final duration and the measured loudness.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

SR = 48000


def decode_stereo(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64).reshape(-1, 2)


def write_f32(path, x):
    x.astype("<f4").tofile(path)


def loudnorm_measure(path, lufs, tp):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        "loudnorm=I=%s:TP=%s:LRA=11:print_format=json" % (lufs, tp), "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True)
    txt = p.stderr
    j = txt[txt.rfind("{"): txt.rfind("}") + 1]
    return json.loads(j)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--kind", choices=["track", "loop", "opening"], required=True)
    ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--tp", type=float, default=-1.5)
    ap.add_argument("--cue-s", type=float, default=2.4)
    ap.add_argument("--cue-fade-ms", type=float, default=300.0)
    ap.add_argument("--xfade-s", type=float, default=3.0)
    ap.add_argument("--tail-db", type=float, default=-50.0)
    ap.add_argument("--quality", default="6")
    a = ap.parse_args()

    x = decode_stereo(a.src)
    mono = np.abs(x).max(axis=1)
    peak = mono.max()
    hop = SR // 100
    n = len(mono) // hop
    env = mono[: n * hop].reshape(n, hop).max(axis=1)
    on = np.flatnonzero(env > peak * 10 ** (-60 / 20))
    start = max(0, on[0] * hop - int(0.02 * SR)) if len(on) else 0
    if a.kind == "opening":
        y = x[start: start + int(a.cue_s * SR)].copy()
        f = int(a.cue_fade_ms * SR / 1000)
        y[-f:] *= np.linspace(1, 0, f)[:, None]
    else:
        tail = np.flatnonzero(env > peak * 10 ** (a.tail_db / 20))
        end = min(len(x), (tail[-1] + 1) * hop + int(0.4 * SR)) if len(tail) else len(x)
        y = x[start:end].copy()
        f = min(len(y) // 4, int(1.5 * SR))
        y[-f:] *= (np.linspace(1, 0, f) ** 2)[:, None]
        fi = int(0.01 * SR)
        y[:fi] *= np.linspace(0, 1, fi)[:, None]
        if a.kind == "loop":
            c = int(a.xfade_s * SR)
            # undo the fade-out for the loop: rebuild from the untouched source
            y = x[start:end].copy()
            head, body = y[:c].copy(), y[: len(y) - c].copy()
            tailseg = y[len(y) - c:]
            t = np.linspace(0, 1, c)[:, None]
            body[:c] = head * np.sqrt(t) + tailseg * np.sqrt(1 - t)
            y = body
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "x.f32")
        write_f32(raw, y)
        inp = ["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw]
        wav = os.path.join(td, "x.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + inp + ["-c:a", "pcm_f32le", wav], check=True)
        m = loudnorm_measure(wav, a.lufs, a.tp)
        gain = a.lufs - float(m["input_i"])
        # linear gain only (keeps dynamics); then cap the true peak at TP with a gentle limiter
        af = "volume=%.3fdB,alimiter=limit=%.4f:attack=5:release=60:level=disabled" % (gain, 10 ** (a.tp / 20))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", af, "-ar", str(SR), "-ac", "2",
                        "-c:a", "libvorbis", "-q:a", a.quality, a.out], check=True)
        m2 = loudnorm_measure(a.out, a.lufs, a.tp)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.out],
                               stdout=subprocess.PIPE, text=True).stdout.strip())
    print(json.dumps({"out": a.out, "kind": a.kind, "duration_s": round(dur, 2), "raw_s": round(len(x) / SR, 2),
                      "lufs_in": float(m["input_i"]), "gain_db": round(gain, 2), "lufs_out": float(m2["input_i"]),
                      "tp_out": float(m2["input_tp"])}))


if __name__ == "__main__":
    main()
