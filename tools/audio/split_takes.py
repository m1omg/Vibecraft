#!/usr/bin/env python3
"""Split a multi-variant SFX generation into separate takes, measure them, and export the good ones.

Pipeline (art-and-audio bible 9.1 "Post"):
  1. decode the raw file (any format ffmpeg reads) to 44.1 kHz mono float;
  2. find takes: a 5 ms RMS envelope, a threshold relative to the loudest frame (--thresh-db),
     gaps shorter than --min-silence are bridged (so "tuk-tuk" stays one take);
  3. measure each take: duration, peak, clipped-sample ratio, RMS, crest factor, spectral centroid,
     spectral flatness, in-take silence ratio and a pitch-periodicity score (speech and music are
     strongly periodic for long stretches; most impacts and whooshes are not);
  4. flag outliers (too short, too long, clipped, centroid far from the job median, very periodic and long);
  5. export the kept takes: trim, 5 ms fade-in / 20 ms fade-out (configurable), peak -1 dBFS,
     16-bit WAV 44.1 kHz mono, named <out>/<id>_<nn>.wav (nn from 01).

Examples:
  split_takes.py raw.mp3 --id hit_metal_l --out assets/audio/sfx/combat --expect 4 --dur 0.5
  split_takes.py raw.mp3 --id ui_order_kingdom --out assets/audio/sfx/ui --names move,move,attack,attack,patrol,patrol,ability,ability
  split_takes.py raw.mp3 --id sw_slash --out ... --dry-run --spectrogram /tmp/sw_slash.png
  split_takes.py raw.mp3 --id x --out ... --keep 1,2,4        (export only these takes, 1-based, after detection)

With --names the takes are named <id>_<name>_<nn>.wav in order (a kit set: one name per detected take).
The script prints a JSON report (one row per take with its metrics and flags) to stdout, or to --report.
"""
import argparse
import json
import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100


def decode(path, sr=SR, channels=1):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", str(channels), "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    if channels > 1:
        x = x.reshape(-1, channels)
    return x


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).round().astype("<i2")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def db(v):
    return 20.0 * np.log10(max(float(v), 1e-12))


def envelope(x, hop):
    n = len(x) // hop
    if n == 0:
        return np.zeros(1)
    fr = x[: n * hop].reshape(n, hop)
    return np.sqrt((fr ** 2).mean(axis=1) + 1e-20)


def find_takes(x, hop, thresh_db, tail_db, min_silence, min_len, pre_ms, post_ms):
    env = envelope(x, hop)
    env_db = 20 * np.log10(env)
    top = env_db.max()
    on = env_db > top + thresh_db
    # bridge short gaps
    gap = int(round(min_silence * SR / hop))
    idx = np.flatnonzero(on)
    if len(idx) == 0:
        return [], env_db, top
    segs = []
    s = idx[0]
    p = idx[0]
    for i in idx[1:]:
        if i - p > gap:
            segs.append((s, p))
            s = i
        p = i
    segs.append((s, p))
    out = []
    tail_thr = top + tail_db
    for a, b in segs:
        # extend the tail while the envelope stays above the (lower) tail threshold
        e = b
        while e + 1 < len(env_db) and env_db[e + 1] > tail_thr:
            e += 1
        # extend the attack backwards a little the same way
        s0 = a
        while s0 - 1 >= 0 and env_db[s0 - 1] > tail_thr and (a - s0) * hop < 0.03 * SR:
            s0 -= 1
        start = max(0, s0 * hop - int(pre_ms * SR / 1000))
        end = min(len(x), (e + 1) * hop + int(post_ms * SR / 1000))
        if (end - start) / SR >= min_len:
            out.append([start, end])
    # merge overlaps created by the tails
    merged = []
    for seg in out:
        if merged and seg[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], seg[1])
        else:
            merged.append(seg)
    return merged, env_db, top


def highpass(y, fc):
    """Zero-phase FFT high-pass (brick-wall with a short cosine ramp); good enough for analysis."""
    n = len(y)
    Y = np.fft.rfft(y)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.clip((f - fc * 0.7) / (fc * 0.3), 0, 1)
    return np.fft.irfft(Y * g, n)


def flat_tops(y, level=0.98, run=3):
    """Number of runs of >= run consecutive samples stuck at the same value above level: real clipping,
    unlike the brief overshoots above 0 dBFS an mp3 decoder produces from a limited master."""
    a = np.abs(y) > level
    same = np.abs(np.diff(y)) < 1e-5
    m = a[1:] & same
    count = 0
    k = 0
    for v in m:
        if v:
            k += 1
            if k == run - 1:
                count += 1
        else:
            k = 0
    return count


def periodicity(y):
    """Fraction of 40 ms frames (above 150 Hz) with a strong autocorrelation peak in 150-1000 Hz:
    voiced speech, sung or played notes. Low booms and rumbles are removed by the high-pass first."""
    fl = int(0.04 * SR)
    if len(y) < fl:
        return 0.0
    y = highpass(y, 150.0)
    lo, hi = SR // 1000, SR // 150
    lo, hi = SR // 1000, SR // 80
    hits = 0
    total = 0
    for i in range(0, len(y) - fl, fl // 2):
        f = y[i:i + fl]
        if np.sqrt((f ** 2).mean()) < 1e-3:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[fl - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        total += 1
        if ac[lo:hi].max() > 0.6:
            hits += 1
    return hits / total if total else 0.0


def metrics(y, hop):
    dur = len(y) / SR
    peak = np.abs(y).max() if len(y) else 0.0
    clip = flat_tops(y)
    rms = np.sqrt((y ** 2).mean()) if len(y) else 0.0
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) + 1e-12
    freqs = np.fft.rfftfreq(len(y), 1.0 / SR)
    centroid = float((spec * freqs).sum() / spec.sum())
    flat = float(np.exp(np.log(spec).mean()) / spec.mean())
    env = envelope(y, hop)
    env_db = 20 * np.log10(env)
    sil = float((env_db < env_db.max() - 40).mean()) if len(env_db) else 0.0
    return {
        "dur": round(dur, 3),
        "peak_db": round(db(peak), 2),
        "clip": int(clip),
        "rms_db": round(db(rms), 2),
        "crest_db": round(db(peak) - db(rms), 2),
        "centroid_hz": round(centroid),
        "flatness": round(flat, 4),
        "silence": round(sil, 3),
        "periodic": round(periodicity(y), 3),
    }


def fade(y, fin_ms, fout_ms):
    y = y.copy()
    a = min(len(y), int(fin_ms * SR / 1000))
    b = min(len(y), int(fout_ms * SR / 1000))
    if a > 0:
        y[:a] *= np.linspace(0, 1, a)
    if b > 0:
        y[-b:] *= np.linspace(1, 0, b) ** 2
    return y


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="raw generation (mp3, wav, ...)")
    ap.add_argument("--id", required=True, help="sound id (file stem)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--expect", type=int, default=0, help="expected number of takes (report only)")
    ap.add_argument("--dur", type=float, default=0.0, help="expected take length in s (flags takes > 3x this, and > dur + 1.5 s)")
    ap.add_argument("--max-len", type=float, default=0.0, help="hard maximum take length (s); longer takes are flagged")
    ap.add_argument("--min-len", type=float, default=0.04, help="drop detections shorter than this (s)")
    ap.add_argument("--thresh-db", type=float, default=-35.0, help="onset threshold relative to the loudest 5 ms frame")
    ap.add_argument("--tail-db", type=float, default=-50.0, help="tail threshold relative to the loudest frame")
    ap.add_argument("--min-silence", type=float, default=0.25, help="gaps shorter than this stay inside one take (s)")
    ap.add_argument("--pre-ms", type=float, default=8.0)
    ap.add_argument("--post-ms", type=float, default=30.0)
    ap.add_argument("--fade-in-ms", type=float, default=5.0)
    ap.add_argument("--fade-out-ms", type=float, default=20.0)
    ap.add_argument("--peak-db", type=float, default=-1.0, help="peak normalisation target (dBFS)")
    ap.add_argument("--max-out", type=float, default=0.0, help="truncate exported takes to this length (s), with the fade-out")
    ap.add_argument("--keep", default="", help="comma list of 1-based take numbers to export (default: all unflagged)")
    ap.add_argument("--reject", default="", help="comma list of 1-based take numbers never to export")
    ap.add_argument("--keep-flagged", action="store_true", help="export flagged takes too")
    ap.add_argument("--names", default="", help="comma list, one sub-name per detected take (kit sets)")
    ap.add_argument("--start", type=int, default=1, help="first nn index")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default="", help="write the JSON report here")
    ap.add_argument("--spectrogram", default="", help="write a spectrogram PNG of the raw file here")
    a = ap.parse_args()

    x = decode(a.src)
    hop = int(0.005 * SR)
    segs, env_db, top = find_takes(x, hop, a.thresh_db, a.tail_db, a.min_silence, a.min_len, a.pre_ms, a.post_ms)
    rows = []
    for i, (s, e) in enumerate(segs):
        y = x[s:e]
        m = metrics(y, hop)
        m["take"] = i + 1
        m["start"] = round(s / SR, 3)
        m["end"] = round(e / SR, 3)
        rows.append(m)
    if rows:
        med_c = float(np.median([r["centroid_hz"] for r in rows]))
        med_d = float(np.median([r["dur"] for r in rows]))
    for r in rows:
        flags = []
        if r["clip"] >= 3:
            flags.append("clipped")
        if a.max_len and r["dur"] > a.max_len:
            flags.append("too_long")
        elif a.dur and r["dur"] > max(3 * a.dur, a.dur + 1.5):
            flags.append("too_long")
        if len(rows) >= 3 and (r["centroid_hz"] > 2.2 * med_c or r["centroid_hz"] < med_c / 2.2):
            flags.append("centroid_outlier")
        if len(rows) >= 3 and r["dur"] < med_d / 3.0:
            flags.append("short_outlier")
        if r["periodic"] > 0.6 and r["dur"] > 0.6:
            flags.append("tonal_or_voice")
        if r["peak_db"] < db(10 ** (top / 20)) - 30:
            flags.append("very_quiet")
        r["flags"] = flags

    keep = {int(k) for k in a.keep.split(",") if k.strip()}
    rej = {int(k) for k in a.reject.split(",") if k.strip()}
    names = [n.strip() for n in a.names.split(",")] if a.names else []
    if names and len(names) != len(rows):
        print("WARNING: %d names for %d takes; kit names not applied" % (len(names), len(rows)), file=sys.stderr)
        names = []
    counters = {}
    exported = []
    for r, (s, e) in zip(rows, segs):
        t = r["take"]
        ok = (t in keep) if keep else (not r["flags"] or a.keep_flagged)
        if t in rej:
            ok = False
        r["export"] = ok
        if not ok:
            continue
        stem = a.id
        if names:
            stem = "%s_%s" % (a.id, names[t - 1])
        n = counters.get(stem, a.start - 1) + 1
        counters[stem] = n
        fn = os.path.join(a.out, "%s_%02d.wav" % (stem, n))
        r["file"] = fn
        exported.append(fn)
        if a.dry_run:
            continue
        y = x[s:e].copy()
        y -= y.mean()
        if a.max_out and len(y) > a.max_out * SR:
            y = y[: int(a.max_out * SR)]
        y = fade(y, a.fade_in_ms, a.fade_out_ms)
        pk = np.abs(y).max()
        if pk > 0:
            y *= (10 ** (a.peak_db / 20.0)) / pk
        write_wav(fn, y)
    rep = {"src": a.src, "id": a.id, "raw_dur": round(len(x) / SR, 3), "raw_peak_db": round(db(np.abs(x).max()), 2),
           "detected": len(rows), "expected": a.expect, "exported": len(exported), "takes": rows}
    if a.spectrogram:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-lavfi",
                        "showspectrumpic=s=1200x400:legend=1:scale=log:fscale=log", a.spectrogram], check=False)
    s = json.dumps(rep, indent=1)
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        with open(a.report, "w") as f:
            f.write(s + "\n")
    # compact table to stderr, full JSON to stdout
    print("%s: raw %.2f s, %d takes (expected %d), %d exported" % (a.id, rep["raw_dur"], len(rows), a.expect, len(exported)),
          file=sys.stderr)
    for r in rows:
        print("  #%d %6.3f-%6.3f dur %.3f pk %6.1f rms %6.1f cen %5d flat %.3f per %.2f %s%s" % (
            r["take"], r["start"], r["end"], r["dur"], r["peak_db"], r["rms_db"], r["centroid_hz"], r["flatness"],
            r["periodic"], ",".join(r["flags"]), "" if r["export"] else "  [not exported]"), file=sys.stderr)
    if not a.report:
        print(s)


if __name__ == "__main__":
    main()
