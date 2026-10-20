#!/usr/bin/env python3
"""Split a batched TTS voice take into lines, post-process each line and export Ogg Vorbis (art bible 8.11).

One ElevenLabs request reads several lines of one speaker and one category, separated by pauses. This tool:
  1. decodes the raw download (mp3, wav, ...) to 44.1 kHz mono float;
  2. finds the pauses: a 10 ms RMS envelope, frames below --noise-db (dBFS, default -40) are silent, and silent
     runs of at least --min-sil seconds (default 0.35) are candidate cut points. With --expect N the N-1 LONGEST
     internal pauses are used, so a short breath inside a line ("Mm? Mind the mortar.") never splits it; the
     report gives the margin between the shortest pause used and the longest pause left inside a line;
  3. trims each line (40 ms kept before the first and 90 ms after the last voiced frame) and, with --max-gap,
     shortens every pause inside the line to that length (acks: 0.15 s), cut mid-pause with a 10 ms crossfade;
  4. applies the speaker's post-chain (--post, an ffmpeg filter string), with --tail seconds of padding for
     reverbs, then trims the tail again;
  5. applies a 5 ms fade-in and a 20 ms fade-out, measures integrated loudness (ffmpeg ebur128) and gains the
     line to --lufs (default -18 LUFS) with a -1 dBFS sample-peak ceiling (alimiter);
  6. checks the final duration against --max-s: when over, re-runs from step 4 with a pitch-preserving atempo
     of up to --max-tempo (default 1.15); when still over, the line is REJECTED (not exported);
  7. exports Ogg Vorbis mono (-q:a 5 by default) as <out-dir>/<name>.ogg.

Usage examples:
  vo_split.py raw.mp3 --expect 4 --names what_01,what_02,what_03,what_04 --out-dir assets/audio/voice/kingdom/hodman \
      --max-s 1.4 --post "rubberband=pitch=0.97:formant=preserved,equalizer=f=250:t=q:w=1:g=2"
  vo_split.py raw.mp3 --expect 4 --analyse            (print the pause map only; nothing is written)

Prints a JSON report (one row per line: start, end, raw and final seconds, tempo, LUFS, peak, status) to stdout
or to --report. Exit code 0 when every expected line was found; 2 when the split count does not match --expect.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 44100
HOP = 441  # 10 ms


def decode(path, sr=SR):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).round().astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def env_db(x):
    n = len(x) // HOP
    if n == 0:
        return np.full(1, -120.0)
    fr = x[: n * HOP].reshape(n, HOP)
    return 10 * np.log10((fr ** 2).mean(axis=1) + 1e-14)


def silent_runs(edb, noise_db):
    """Return [(start_frame, end_frame_exclusive)] of frames below noise_db."""
    sil = edb < noise_db
    runs = []
    i = 0
    n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def analyse(x, noise_db, min_sil, expect=None):
    edb = env_db(x)
    voiced = np.flatnonzero(edb >= noise_db)
    if len(voiced) == 0:
        return {"segments": [], "pauses": [], "used": [], "margin": None, "edb": edb}
    first, last = voiced[0], voiced[-1]
    internal = [(a, b) for (a, b) in silent_runs(edb, noise_db) if a > first and b <= last]
    pauses = sorted(internal, key=lambda r: r[1] - r[0], reverse=True)
    if expect:
        used = pauses[: max(0, expect - 1)]
    else:
        used = [r for r in pauses if (r[1] - r[0]) * HOP / SR >= min_sil]
    left = [r for r in pauses if r not in used]
    used_sorted = sorted(used)
    cuts = [first] + [((a + b) // 2) for (a, b) in used_sorted] + [last + 1]
    segments = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
    shortest_used = min(((b - a) * HOP / SR for a, b in used), default=None)
    longest_left = max(((b - a) * HOP / SR for a, b in left), default=0.0)
    return {
        "segments": segments,
        "pauses": [((a * HOP) / SR, (b - a) * HOP / SR) for a, b in sorted(internal)],
        "used": [((a * HOP) / SR, (b - a) * HOP / SR) for a, b in used_sorted],
        "shortest_used_s": shortest_used,
        "longest_left_s": longest_left,
        "edb": edb,
    }


def trim(x, noise_db, pre=0.04, post=0.09):
    edb = env_db(x)
    v = np.flatnonzero(edb >= noise_db)
    if len(v) == 0:
        return x[:0]
    a = max(0, v[0] * HOP - int(pre * SR))
    b = min(len(x), (v[-1] + 1) * HOP + int(post * SR))
    return x[a:b]


def tighten(x, noise_db, max_gap):
    """Shorten every internal pause (frames below noise_db) longer than max_gap seconds to max_gap.

    Acks must land inside 1.4 s (art bible 8.2); a TTS read of "Thirty years. One Agnes." can hold a 0.45 s breath
    between the sentences. The cut is made in the middle of the pause with a 10 ms crossfade, so the breath edges stay.
    """
    if not max_gap or len(x) == 0:
        return x
    edb = env_db(x)
    runs = [(a, b) for (a, b) in silent_runs(edb, noise_db) if a > 0 and b < len(edb)]
    keep = int(max_gap / (HOP / SR))
    out = []
    pos = 0
    xf = int(0.010 * SR)
    for a, b in runs:
        if b - a <= keep:
            continue
        mid_a = (a + keep // 2) * HOP
        mid_b = (b - (keep - keep // 2)) * HOP
        out.append(x[pos:mid_a])
        pos = mid_b
    out.append(x[pos:])
    if len(out) == 1:
        return x
    y = out[0]
    for seg in out[1:]:
        n = min(xf, len(y), len(seg))
        if n > 0:
            ramp = np.linspace(0.0, 1.0, n)
            y = np.concatenate([y[:-n], y[-n:] * (1 - ramp) + seg[:n] * ramp, seg[n:]])
        else:
            y = np.concatenate([y, seg])
    return y


def ffmpeg_filter(x, filt):
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.wav")
        dst = os.path.join(td, "out.wav")
        write_wav(src, x)
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-af", filt, "-ac", "1", "-ar", str(SR), dst]
        subprocess.run(cmd, check=True)
        return decode(dst)


def loudness(x):
    """Integrated loudness (LUFS) via ffmpeg ebur128; falls back to RMS dBFS - 0.7 for very short clips."""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.wav")
        # ebur128 needs >= 400 ms; pad short clips with silence is wrong (gating), so loop them instead.
        y = x if len(x) >= int(0.5 * SR) else np.tile(x, int(np.ceil(0.5 * SR / max(1, len(x)))) )
        write_wav(src, y)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                           stderr=subprocess.PIPE, text=True)
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if m:
            val = float(m[-1])
            if val > -69.0:
                return val
    rms = np.sqrt(np.mean(x ** 2) + 1e-14)
    return 20 * np.log10(rms) - 0.7


def fades(x, fin=0.005, fout=0.020):
    y = x.copy()
    a = min(len(y), int(fin * SR))
    b = min(len(y), int(fout * SR))
    if a > 0:
        y[:a] *= np.linspace(0.0, 1.0, a)
    if b > 0:
        y[-b:] *= np.linspace(1.0, 0.0, b)
    return y


def process_line(x, post, tail, noise_db, tempo, lufs, max_tempo):
    filt = []
    if tempo and abs(tempo - 1.0) > 1e-3:
        filt.append(f"atempo={tempo:.4f}")
    if tail > 0:
        filt.append(f"apad=pad_dur={tail}")
    if post:
        filt.append(post)
    y = ffmpeg_filter(x, ",".join(filt)) if filt else x
    y = trim(y, min(noise_db, -50.0), pre=0.0, post=0.06) if (tail > 0 or post) else y
    y = fades(y)
    l = loudness(y)
    g = lufs - l
    y = y * (10 ** (g / 20))
    return y, l


def export_ogg(x, path, quality):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.wav")
        # 32-bit float wav so the gain stage cannot clip before the limiter
        y = x.astype(np.float32)
        with open(src, "wb") as f:
            import struct
            data = y.tobytes()
            f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
            f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, 1, SR, SR * 4, 4, 32))
            f.write(b"data" + struct.pack("<I", len(data)) + data)
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-af", "alimiter=limit=0.891:attack=2:release=30:level=disabled",
               "-ac", "1", "-ar", str(SR), "-c:a", "libvorbis", "-q:a", str(quality), path]
        subprocess.run(cmd, check=True)


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       stdout=subprocess.PIPE, text=True, check=True)
    return float(r.stdout.strip())


def run(raw, names=None, expect=None, out_dir=None, max_s=None, post="", tail=0.0, lufs=-18.0, noise_db=-40.0,
        min_sil=0.35, max_tempo=1.15, quality=5, analyse_only=False, keep=None, max_gap=None):
    x = decode(raw)
    if expect is None and names:
        expect = len(names)
    an = analyse(x, noise_db, min_sil, expect)
    segs = an["segments"]
    report = {
        "raw": raw,
        "raw_s": round(len(x) / SR, 3),
        "expect": expect,
        "found": len(segs),
        "pauses": [(round(t, 2), round(d, 2)) for t, d in an["pauses"]],
        "shortest_pause_used_s": None if an.get("shortest_used_s") is None else round(an["shortest_used_s"], 2),
        "longest_pause_left_s": round(an.get("longest_left_s") or 0.0, 2),
        "lines": [],
    }
    if analyse_only or not out_dir:
        for i, (a, b) in enumerate(segs):
            seg = trim(x[a * HOP: b * HOP], noise_db)
            report["lines"].append({"n": i + 1, "start": round(a * HOP / SR, 2), "raw_s": round(len(seg) / SR, 3)})
        return report
    for i, (a, b) in enumerate(segs):
        name = names[i] if names and i < len(names) else f"line_{i + 1:02d}"
        row = {"n": i + 1, "name": name, "start": round(a * HOP / SR, 2)}
        if keep and (i + 1) not in keep:
            row["status"] = "skipped"
            report["lines"].append(row)
            continue
        seg = trim(x[a * HOP: b * HOP], noise_db)
        row["raw_s"] = round(len(seg) / SR, 3)
        if max_gap:
            seg = tighten(seg, noise_db, max_gap)
            row["tight_s"] = round(len(seg) / SR, 3)
        tempo = 1.0
        y, l = process_line(seg, post, tail, noise_db, tempo, lufs, max_tempo)
        dur = len(y) / SR
        if max_s and dur > max_s:
            need = dur / max_s * 1.01
            if need <= max_tempo:
                tempo = need
                y, l = process_line(seg, post, tail, noise_db, tempo, lufs, max_tempo)
                dur = len(y) / SR
        row.update({"tempo": round(tempo, 3), "final_s": round(dur, 3), "lufs_in": round(l, 1),
                    "peak_dbfs": round(20 * np.log10(np.max(np.abs(y)) + 1e-12), 1)})
        if max_s and dur > max_s:
            row["status"] = f"REJECTED (over {max_s} s at atempo {max_tempo})"
        else:
            path = os.path.join(out_dir, name + ".ogg")
            export_ogg(y, path, quality)
            row["file"] = path
            row["ogg_s"] = round(probe_duration(path), 3)
            row["status"] = "ok"
        report["lines"].append(row)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="raw TTS download (any format ffmpeg reads)")
    ap.add_argument("--expect", type=int, help="number of lines read in the batch (uses the N-1 longest pauses)")
    ap.add_argument("--names", help="comma-separated output names, in reading order (implies --expect)")
    ap.add_argument("--out-dir", help="where the .ogg files go")
    ap.add_argument("--max-s", type=float, help="category cap in seconds (art bible 8.2)")
    ap.add_argument("--post", default="", help="ffmpeg filter string: the speaker's post-chain")
    ap.add_argument("--tail", type=float, default=0.0, help="seconds of padding before the post-chain (reverb tails)")
    ap.add_argument("--lufs", type=float, default=-18.0)
    ap.add_argument("--noise-db", type=float, default=-40.0)
    ap.add_argument("--min-sil", type=float, default=0.35)
    ap.add_argument("--max-tempo", type=float, default=1.15)
    ap.add_argument("--max-gap", type=float, help="shorten internal pauses longer than this (seconds) inside a line")
    ap.add_argument("--quality", type=int, default=5, help="libvorbis -q:a")
    ap.add_argument("--keep", help="comma-separated 1-based line numbers to export (others skipped)")
    ap.add_argument("--analyse", action="store_true", help="print the pause map only")
    ap.add_argument("--report", help="write the JSON report here instead of stdout")
    a = ap.parse_args(argv)
    names = a.names.split(",") if a.names else None
    keep = {int(k) for k in a.keep.split(",")} if a.keep else None
    rep = run(a.raw, names, a.expect, a.out_dir, a.max_s, a.post, a.tail, a.lufs, a.noise_db, a.min_sil, a.max_tempo,
              a.quality, a.analyse, keep, a.max_gap)
    txt = json.dumps(rep, indent=1)
    if a.report:
        with open(a.report, "w") as f:
            f.write(txt + "\n")
    else:
        print(txt)
    exp = a.expect or (len(names) if names else None)
    return 2 if exp and rep["found"] != exp else 0


if __name__ == "__main__":
    sys.exit(main())
