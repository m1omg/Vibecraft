#!/usr/bin/env python3
"""Build SFX takes by layering CC0 source files and small procedural layers (no generation cost).

Recipes live in tools/audio/layered_recipes.json:

  {"id": "fall_light", "group": "combat", "source": "cc0",
   "takes": [ {"layers": [ {"src": "kenney/impact-sounds/impactSoft_heavy_000.ogg", "gain_db": 0},
                            {"src": "kenney/rpg-audio/cloth1.ogg", "offset_ms": 15, "gain_db": -6, "hp": 300} ]},
              ... ]}

Layer keys (all optional except one of src / synth):
  src        path under assets_src/audio/cc0/ (CC0 files only; keep the pack's License.txt beside them)
  synth      a procedural layer: "thump" (pitched-down sine kick: f0, f1, decay), "rumble" (low-passed noise: dur, lp,
             decay), "bowl" (inharmonic bronze partials: f0, decay, choke_ms), "tick" (short filtered click: f, decay),
             "noise" (band noise burst: dur, lp, hp, decay)
  pitch      playback-rate factor (resampling: 0.8 = lower and longer)
  gain_db    layer gain
  offset_ms  start time of the layer in the take
  start_ms / len_ms   crop the source before pitching
  lp / hp    2nd-order Butterworth-magnitude low-pass / high-pass (zero phase, applied in the frequency domain)
  fade_ms    fade-out applied to the layer end (default 10)
  reverse    true reverses the layer
Take keys: layers, plus optional "lp"/"hp" on the whole take and "seed" for the synth noise.
The mix is trimmed of trailing silence (-60 dB), faded (5 / 20 ms), peak-normalised to -1 dBFS and written as
16-bit 44.1 kHz mono WAV to assets/audio/sfx/<group>/<id>_<nn>.wav.

  build_layered_sfx.py               build every recipe
  build_layered_sfx.py fall_light    build one
  build_layered_sfx.py --list
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import split_takes as st  # noqa: E402

SR = st.SR
CC0 = os.path.join(REPO, "assets_src", "audio", "cc0")


def bw(y, lp=0.0, hp=0.0, order=2):
    if not lp and not hp:
        return y
    n = len(y)
    pad = 2048
    yp = np.concatenate([y, np.zeros(pad)])
    Y = np.fft.rfft(yp)
    f = np.fft.rfftfreq(len(yp), 1.0 / SR)
    g = np.ones_like(f)
    if lp:
        g *= 1.0 / np.sqrt(1.0 + (f / lp) ** (2 * order))
    if hp:
        with np.errstate(divide="ignore"):
            g *= 1.0 / np.sqrt(1.0 + (hp / np.maximum(f, 1e-6)) ** (2 * order))
    return np.fft.irfft(Y * g, len(yp))[:n]


def resample(y, rate):
    if rate == 1.0:
        return y
    n = int(len(y) / rate)
    t = np.arange(n) * rate
    return np.interp(t, np.arange(len(y)), y)


def synth(kind, p, rng):
    if kind == "thump":
        dur = p.get("dur", 0.35)
        t = np.arange(int(dur * SR)) / SR
        f0, f1, dec = p.get("f0", 70.0), p.get("f1", 38.0), p.get("decay", 0.12)
        f = f1 + (f0 - f1) * np.exp(-t / 0.04)
        ph = 2 * np.pi * np.cumsum(f) / SR
        y = np.sin(ph) * np.exp(-t / dec)
        y += 0.15 * np.sin(2 * ph) * np.exp(-t / (dec * 0.5))
        att = int(0.003 * SR)
        y[:att] *= np.linspace(0, 1, att)
        return y
    if kind == "rumble":
        dur = p.get("dur", 0.9)
        t = np.arange(int(dur * SR)) / SR
        y = rng.standard_normal(len(t))
        y = bw(y, lp=p.get("lp", 120.0), order=4)
        y /= np.abs(y).max() + 1e-9
        att = p.get("attack", 0.01)
        env = np.minimum(1.0, t / att) * np.exp(-t / p.get("decay", 0.3))
        return y * env
    if kind == "bowl":
        dur = p.get("dur", 0.6)
        t = np.arange(int(dur * SR)) / SR
        f0 = p.get("f0", 196.0)
        y = np.zeros_like(t)
        for ratio, amp, dk in ((1.0, 1.0, 1.0), (2.76, 0.5, 0.6), (5.40, 0.25, 0.35), (8.93, 0.1, 0.2)):
            y += amp * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.28)) * np.exp(-t / (p.get("decay", 0.8) * dk))
        att = int(0.004 * SR)
        y[:att] *= np.linspace(0, 1, att)
        ch = p.get("choke_ms")
        if ch:
            k = int(ch * SR / 1000)
            if k < len(y):
                m = int(0.03 * SR)
                y[k:k + m] *= np.linspace(1, 0, len(y[k:k + m])) ** 2
                y[k + m:] = 0
        return y
    if kind == "tick":
        dur = p.get("dur", 0.05)
        t = np.arange(int(dur * SR)) / SR
        y = rng.standard_normal(len(t)) * np.exp(-t / p.get("decay", 0.004))
        y += 0.6 * np.sin(2 * np.pi * p.get("f", 3000.0) * t) * np.exp(-t / (p.get("decay", 0.004) * 2))
        return bw(y, hp=p.get("hp", 800.0), lp=p.get("lp", 0.0))
    if kind == "noise":
        dur = p.get("dur", 0.2)
        t = np.arange(int(dur * SR)) / SR
        y = rng.standard_normal(len(t))
        y = bw(y, lp=p.get("lp", 0.0), hp=p.get("hp", 0.0))
        att = p.get("attack", 0.005)
        return y * np.minimum(1.0, t / att) * np.exp(-t / p.get("decay", 0.05))
    raise ValueError("unknown synth %r" % kind)


_cache = {}


def load_src(rel):
    if rel not in _cache:
        path = os.path.join(CC0, rel)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        _cache[rel] = st.decode(path)
    return _cache[rel]


def render_layer(L, rng):
    if "src" in L:
        y = load_src(L["src"]).copy()
        s = int(L.get("start_ms", 0) * SR / 1000)
        y = y[s:]
        if L.get("len_ms"):
            y = y[: int(L["len_ms"] * SR / 1000)]
    else:
        y = synth(L["synth"], L, rng)
    if L.get("reverse"):
        y = y[::-1].copy()
    y = resample(y, L.get("pitch", 1.0))
    y = bw(y, lp=L.get("lp", 0.0), hp=L.get("hp", 0.0))
    fo = int(L.get("fade_ms", 10) * SR / 1000)
    if 0 < fo < len(y):
        y[-fo:] *= np.linspace(1, 0, fo)
    pk = np.abs(y).max()
    if pk > 0:
        y = y / pk
    return y * 10 ** (L.get("gain_db", 0.0) / 20.0)


def render_take(T, seed):
    rng = np.random.default_rng(T.get("seed", seed))
    parts = []
    for L in T["layers"]:
        y = render_layer(L, rng)
        off = int(L.get("offset_ms", 0) * SR / 1000)
        parts.append((off, y))
    n = max(off + len(y) for off, y in parts)
    mix = np.zeros(n)
    for off, y in parts:
        mix[off:off + len(y)] += y
    mix = bw(mix, lp=T.get("lp", 0.0), hp=T.get("hp", 0.0))
    # trim trailing silence below -60 dB of the peak
    env = st.envelope(mix, 220)
    thr = env.max() * 10 ** (-60 / 20)
    last = np.flatnonzero(env > thr)
    if len(last):
        mix = mix[: min(n, (last[-1] + 1) * 220 + int(0.01 * SR))]
    if T.get("max_ms"):
        mix = mix[: int(T["max_ms"] * SR / 1000)]
    mix = st.fade(mix - mix.mean(), 3.0, T.get("fade_out_ms", 20.0))
    pk = np.abs(mix).max()
    if pk > 0:
        mix *= 10 ** (-1.0 / 20) / pk
    return mix


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--recipes", default=os.path.join(HERE, "layered_recipes.json"))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    recs = json.load(open(a.recipes))["recipes"]
    if a.list:
        for r in recs:
            print("%-28s %-8s %-6s %d takes" % (r["id"], r["group"], r.get("source", ""), len(r["takes"])))
        return
    for r in recs:
        if a.ids and r["id"] not in a.ids:
            continue
        out = os.path.join(REPO, "assets", "audio", "sfx", r["group"])
        for i, T in enumerate(r["takes"]):
            y = render_take(T, seed=hash(r["id"]) % 100000 + i if False else 1000 + i)
            fn = os.path.join(out, "%s_%02d.wav" % (r["id"], i + 1))
            st.write_wav(fn, y)
            m = st.metrics(y, 220)
            print("%s dur %.3f cen %5d" % (os.path.relpath(fn, REPO), m["dur"], m["centroid_hz"]))


if __name__ == "__main__":
    main()
