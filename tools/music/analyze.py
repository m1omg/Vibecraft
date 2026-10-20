#!/usr/bin/env python3
"""analyze.py: measure and draw a rendered piece (used by render.py; also a standalone CLI).

  python3 tools/music/analyze.py FILE.ogg [--loop] [--png OUT_spectrogram.png] [--json]

Measurements:
  loudness     integrated LUFS, loudness range (LU) and true peak (dBTP) from ffmpeg ebur128 (peak=true)
  duration     seconds (decoded sample count / rate)
  bands        share of energy per band (sub <60, low 60-250, lowmid 250-1k, voice 1k-3k, presence 3-6k,
               air >6k), to check warmth versus muddiness and the unit-voice gap
  arc          short-term loudness (3 s windows, K-weighted) min / median / max: the dynamic arc
  gaps         spans quieter than -40 dB below the median for more than 2 s (empty spans)
  seam (loop)  across the loop point: RMS step (dB), 1/3-octave spectral distance (dB) compared with the
               median distance between neighbouring windows inside the piece, and the sample jump
Pictures: spectrogram (ffmpeg showspectrumpic, log frequency) and the piano roll (score data, see
pianoroll()).
"""
from __future__ import annotations

import json
import math
import re
import subprocess

import numpy as np

SR = 48000


def decode(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64).reshape(-1, 2)


def ebur128(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True)
    txt = p.stderr[p.stderr.rfind("Summary:"):]

    def g(key):
        m = re.search(key + r":\s+(-?[\d.]+|-inf)", txt)
        return float(m.group(1)) if m and m.group(1) != "-inf" else float("-inf")
    return {"lufs": g("I"), "lra": g("LRA"), "true_peak_db": g("Peak")}


def band_shares(x, sr=SR):
    m = x.mean(1)
    n = 1 << int(math.floor(math.log2(min(len(m), sr * 8))))
    # average power spectrum over up to 24 windows spread across the file
    starts = np.linspace(0, max(0, len(m) - n), num=min(24, max(1, len(m) // n))).astype(int)
    P = np.zeros(n // 2 + 1)
    w = np.hanning(n)
    for s in starts:
        P += np.abs(np.fft.rfft(m[s:s + n] * w)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / sr)
    edges = [("sub", 0, 60), ("low", 60, 250), ("lowmid", 250, 1000), ("voice", 1000, 3000),
             ("presence", 3000, 6000), ("air", 6000, sr / 2)]
    tot = P.sum() + 1e-20
    return {k: round(float(P[(f >= a) & (f < b)].sum() / tot), 3) for k, a, b in edges}


def kweight(x, sr=SR):
    """Approximate ITU-R BS.1770 K-weighting (high-pass near 60 Hz + a +4 dB shelf above 2 kHz), zero phase."""
    n = len(x)
    N = 1 << int(math.ceil(math.log2(max(n, 16))))
    f = np.fft.rfftfreq(N, 1.0 / sr)
    hp = 1.0 / np.sqrt(1.0 + (60.0 / np.maximum(f, 1e-3)) ** 4)
    shelf = 1.0 + (10 ** (4.0 / 20) - 1.0) / (1.0 + (1500.0 / np.maximum(f, 1e-3)) ** 2)
    X = np.fft.rfft(x, N, axis=0) * (hp * shelf)[:, None]
    return np.fft.irfft(X, N, axis=0)[:n]


def short_term(x, sr=SR, win=3.0, hop=1.0):
    m = (kweight(x) ** 2).mean(1)
    out = []
    for s in range(0, max(1, len(m) - int(win * sr) + 1), int(hop * sr)):
        e = m[s:s + int(win * sr)].mean()
        out.append(10 * math.log10(e + 1e-20))
    return np.array(out)


def third_octave(seg, sr=SR):
    n = len(seg)
    S = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1.0 / sr)
    cs = [100 * 2 ** (k / 3) for k in range(0, 21)]  # 100 Hz .. 10 kHz
    out = []
    for c in cs:
        a, b = c / 2 ** (1 / 6), c * 2 ** (1 / 6)
        out.append(10 * math.log10(S[(f >= a) & (f < b)].sum() + 1e-20))
    return np.array(out)


def seam(x, sr=SR, w=0.5):
    """Loop seam metrics: the end of the file played into its start."""
    k = int(w * sr)
    a, b = x[-k:].mean(1), x[:k].mean(1)
    ra = math.sqrt(np.mean(a ** 2)) + 1e-12
    rb = math.sqrt(np.mean(b ** 2)) + 1e-12
    d_seam = float(np.mean(np.abs(third_octave(a) - third_octave(b))))
    m = x.mean(1)
    dists = []
    for s in range(k, len(m) - k, max(k, len(m) // 60)):
        dists.append(np.mean(np.abs(third_octave(m[s - k:s]) - third_octave(m[s:s + k]))))
    med = float(np.median(dists)) if dists else 1.0
    local = math.sqrt(np.mean(np.concatenate([a[-480:], b[:480]]) ** 2)) + 1e-12
    jump = float(np.max(np.abs(x[0] - x[-1])))
    return {"rms_step_db": round(20 * math.log10(rb / ra), 2), "spec_dist_db": round(d_seam, 2),
            "interior_median_db": round(med, 2), "spec_ratio": round(d_seam / max(med, 1e-6), 2),
            "jump_rel_db": round(20 * math.log10(jump / local + 1e-12), 1)}


def gaps(st, thresh_db=40.0, min_len=2):
    if len(st) == 0:
        return []
    med = float(np.median(st))
    quiet = st < med - thresh_db
    out, run = [], 0
    for i, q in enumerate(quiet):
        run = run + 1 if q else 0
        if run == min_len:
            out.append(i - min_len + 1)
    return out


def measure(path, loop=False):
    x = decode(path)
    r = ebur128(path)
    r["duration_s"] = round(len(x) / SR, 3)
    r["sample_peak_db"] = round(20 * math.log10(np.max(np.abs(x)) + 1e-12), 2)
    r["bands"] = band_shares(x)
    st = short_term(x)
    if len(st):
        r["arc_db"] = {"min": round(float(st.min()), 1), "median": round(float(np.median(st)), 1),
                       "max": round(float(st.max()), 1)}
        r["quiet_spans_s"] = gaps(st)
    if loop:
        r["seam"] = seam(x)
    return r


def spectrogram(path, png, title=""):
    vf = ("showspectrumpic=s=1800x560:legend=1:fscale=log:scale=log:color=intensity:mode=combined:"
          "start=30:stop=16000")
    if title:
        vf += ",drawtext=text='%s':x=110:y=6:fontcolor=white:fontsize=18" % title.replace("'", "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-lavfi", vf, png], check=True)
    return png


def pianoroll(piece, png, audio=None, marks=None, width=1800, height=760):
    """Draw the compiled score: one colour per track, section lines, loudness lane from `audio` (n, 2)."""
    from PIL import Image, ImageDraw
    tracks = list(piece.tracks.values())
    dur = max([piece.duration_s] + [c.t1 for t in tracks for c in t.compiled["notes"]]) + 1.0
    if audio is not None:
        dur = max(dur, len(audio) / SR)
    left, right, top = 150, 20, 30
    lane = 120
    roll_h = height - top - lane - 50
    im = Image.new("RGB", (width, height), (18, 18, 22))
    d = ImageDraw.Draw(im)
    pitches = [c.pitch for t in tracks for c in t.compiled["notes"]] or [60]
    lo, hi = max(0, min(pitches) - 2), min(127, max(pitches) + 2)
    sx = (width - left - right) / dur

    def X(t):
        return left + t * sx

    def Y(p):
        return top + roll_h - (p - lo + 1) / (hi - lo + 1) * roll_h
    for p in range(lo, hi + 1):
        if p % 12 == 0:
            d.line([(left, Y(p)), (width - right, Y(p))], fill=(45, 45, 52))
            d.text((left - 34, Y(p) - 12), f"C{p // 12 - 1}", fill=(120, 120, 130))
    for s in range(0, int(dur) + 1, 10):
        d.line([(X(s), top), (X(s), top + roll_h)], fill=(32, 32, 38))
        d.text((X(s) + 2, top + roll_h + 4), f"{s}s", fill=(120, 120, 130))
    for s in piece.sections:
        t = piece.seconds(s.start)
        d.line([(X(t), 4), (X(t), height - 30)], fill=(200, 200, 210))
        d.text((X(t) + 3, 6), s.name, fill=(230, 230, 240))
    for (t, txt) in (marks or []):
        d.line([(X(t), top), (X(t), height - 30)], fill=(220, 60, 60))
        d.text((X(t) + 3, top + roll_h - 14), txt, fill=(240, 90, 90))
    palette_cols = [(232, 176, 64), (110, 190, 230), (220, 90, 70), (160, 100, 200), (150, 220, 90),
                    (240, 120, 160), (90, 160, 240), (200, 200, 200), (250, 230, 120), (120, 160, 120)]
    for i, t in enumerate(tracks):
        col = t.inst.color or palette_cols[i % len(palette_cols)]
        hgt = max(2, roll_h / (hi - lo + 1) * 0.8)
        for c in t.compiled["notes"]:
            y = Y(c.pitch)
            a = 0.35 + 0.65 * min(1.0, c.mvel / 127.0)
            fill = tuple(int(v * a) for v in col)
            d.rectangle([X(c.t0), y - hgt, max(X(c.t0) + 1, X(c.t1)), y], fill=fill)
        d.rectangle([8, top + 4 + i * 18, 20, top + 16 + i * 18], fill=col)
        d.text((24, top + 3 + i * 18), t.name[:18], fill=(220, 220, 225))
    # loudness lane
    y0 = height - 30 - lane
    d.rectangle([left, y0, width - right, height - 30], outline=(60, 60, 70))
    d.text((8, y0 + 4), "loudness", fill=(200, 200, 205))
    d.text((8, y0 + 20), "(0.4 s, K-weighted dB)", fill=(140, 140, 150))
    if audio is not None and len(audio):
        m = (kweight(audio) ** 2).mean(1)
        hop = int(0.1 * SR)
        win = int(0.4 * SR)
        vals = []
        for s in range(0, max(1, len(m) - win), hop):
            vals.append(10 * math.log10(m[s:s + win].mean() + 1e-20))
        vals = np.array(vals)
        floor, ceil = -60.0, 0.0
        pts = []
        for k, v in enumerate(vals):
            t = (k * hop + win / 2) / SR
            yy = y0 + lane - (min(max(v, floor), ceil) - floor) / (ceil - floor) * lane
            pts.append((X(t), yy))
        for db in (-12, -24, -36, -48):
            yy = y0 + lane - (db - floor) / (ceil - floor) * lane
            d.line([(left, yy), (width - right, yy)], fill=(40, 40, 48))
            d.text((left - 30, yy - 6), str(db), fill=(110, 110, 120))
        if len(pts) > 1:
            d.line(pts, fill=(120, 220, 140), width=2)
    d.text((left, height - 22), f"{piece.name}  {piece.mode!r}  seed {piece.seed}  {dur:.1f} s", fill=(200, 200, 205))
    im.save(png)
    return png


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--loop", action="store_true", help="also measure the loop seam (end -> start)")
    ap.add_argument("--png", help="write a spectrogram PNG here")
    a = ap.parse_args()
    res = measure(a.file, loop=a.loop)
    if a.png:
        spectrogram(a.file, a.png)
        res["spectrogram"] = a.png
    print(json.dumps(res, indent=1))
