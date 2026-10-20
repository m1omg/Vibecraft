#!/usr/bin/env python3
"""ext_clans.py: extras for the clans (Tormai) pieces, kept out of the shared toolkit files.

Importing this module registers one more numpy instrument in synths.SYNTHS, so render.py can render it:
  wind       steppe wind: noise shaped frame by frame (STFT overlap-add) through a broad band plus a narrow,
             gliding "whistle" resonance; each note is one gust (a swell over the note length, gust flutter on
             top). Note keywords: fc (centre Hz, default 650), fc_to (glide target), whistle (0..1), q.

Instruments (palette conventions: gain_db = dB relative to the melody; trim_db is calibration, leave it):
  WIND             the wind bed for the windswept passages (far under the band)
  TWO_STRING_LOW   the two-string fiddle as the drone / bass voice: polyphonic (double stops), no vibrato, a
                   darker EQ; the faction's floor instead of a kingdom contrabass
  LUTE_SOFT        the lute for ringing background chords

Helpers:
  M("4:1~gu 3:1 0:2 | 1:8/3~s 0:4/3")   compact motif writing: DEG:DUR tokens, `|` is a bar line (checked to
                                         `bar` beats when given), r = rest, DEG may end in # or b (alteration),
                                         ~ORN = gu gd m lm t tr s sd (grace up/down, mordent, lower mordent,
                                         turn, trill, slide, slide down), ! accent, ? soft.
  plain(motif)                           the motif without ornaments (for a doubling voice)
  jaw(track, piece, bar0, bars, ks, grid, vel, fade)  jaw-harp pulses on a 12-step bar grid
  gallop_fifths(track, beat, root, vel, shape)  the lute's open-fifth gallop figure for one 4/4 bar
  riff(track, beat, chord, vel, density)  the lute's running sixteenth riff over a drone string (A Dorian table)
"""
from __future__ import annotations

import math
import os
import sys
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import palette as P  # noqa: E402
import synths  # noqa: E402
from score import Instrument, Motif  # noqa: E402

EXT_VERSION = 2   # part of the wind synth params, so render.py's stem cache sees code changes here


# --------------------------------------------------------------------------------------------- wind synth
class Wind(synths.Synth):
    defaults = {"level": 0.5, "whistle": 0.35, "q": 14.0, "frame": 2048, "hop": 512, "v": EXT_VERSION}

    def render(self, note, rng):
        sr = self.sr
        p = self.p
        dur = max(0.4, note.t1 - note.t0)
        rel = min(2.5, 0.35 * dur + 0.4)
        n = int((dur + rel) * sr)
        N, H = int(p["frame"]), int(p["hop"])
        frames = n // H + 2
        vel = min(1.0, note.mvel / 127.0)
        fc0 = float(note.kw.get("fc", 650.0))
        fc1 = float(note.kw.get("fc_to", fc0 * 1.6))
        whistle = float(note.kw.get("whistle", p["whistle"]))
        q = float(note.kw.get("q", p["q"]))
        tf = (np.arange(frames) * H) / sr
        # the whistle centre glides fc0 -> fc1 -> back, with slow wander; the gust envelope swells and flutters
        x = np.clip(tf / dur, 0, 1)
        arc = np.sin(np.pi * x) ** 0.8
        wander = 2 ** (0.35 * synths.smooth_noise(rng, frames, 0.6, sr=sr / H))
        fc = fc0 * (fc1 / fc0) ** arc * wander
        gust = 0.65 + 0.35 * synths.smooth_noise(rng, frames, 1.1, sr=sr / H)
        env = np.where(tf <= dur, arc, np.exp(-(tf - dur) / max(0.15, rel / 3)) * arc[np.argmin(np.abs(tf - dur))])
        env = np.clip(env * np.clip(gust, 0.2, 1.4), 0, None)
        f = np.fft.rfftfreq(N, 1.0 / sr)
        win = np.hanning(N)
        out = np.zeros((frames * H + N, 2))
        broad = synths.bandpass(900.0, 0.55)(f) * synths.highpass(160.0, 2)(f) * synths.lowpass(5200.0, 2)(f)
        for ch in range(2):
            noise = rng.normal(0.0, 1.0, frames * H + N)
            for k in range(frames):
                s = k * H
                seg = noise[s:s + N] * win
                X = np.fft.rfft(seg)
                c = fc[k] * (1.0 + (0.035 if ch else -0.035))
                peak = 1.0 / np.sqrt(1.0 + (q * (np.maximum(f, 1.0) / c - c / np.maximum(f, 1.0))) ** 2)
                resp = (1.0 - whistle) * broad + whistle * 2.2 * peak
                out[s:s + N, ch] += np.fft.irfft(X * resp, N) * win * env[k]
        out = out[:n] * p["level"] * 0.05 * (0.45 + 0.55 * vel)
        return int(round(note.t0 * sr)), out


synths.SYNTHS.setdefault("wind", Wind)

# --------------------------------------------------------------------------------------------- instruments
WIND = Instrument("wind", synth="wind", program=0, gain_db=-16.0, trim_db=20.6, pan=0.0, width=1.0, reverb=0.35,
                  eq=[("hp", 180), ("peak", 2300, -3.0, 1.0), ("lp", 6000)],
                  synth_params={"level": 0.5, "whistle": 0.35, "q": 14.0, "v": EXT_VERSION},
                  timing_ms=0, accent=0, color=(150, 160, 175))
TWO_STRING_LOW = P.TWO_STRING.variant(
    name="two_string_low", mono=False, vibrato=None, gain_db=-8.0, pan=-0.14, width=0.6, reverb=0.24, drive=0.3,
    eq=[("hp", 45), ("peak", 1300, 0.5, 1.2), ("peak", 2600, -3.0, 1.0), ("highshelf", 5000, -4.0)],
    lo=36, hi=62, timing_ms=6, accent=2, color=(170, 100, 50))
LUTE_SOFT = P.LUTE.variant(name="lute_soft", gain_db=-8.0, reverb=0.3)


# --------------------------------------------------------------------------------------------- writing helpers
_ORN = {"gu": "grace_up", "gd": "grace_down", "m": "mordent", "lm": "lmordent", "t": "turn", "tr": "trill",
        "s": "slide", "sd": "slide_down"}


def M(spec: str, bar: float | None = None, name: str = "") -> Motif:
    """Compact motif: "4:1~gu 3:1 0:2 | 1:8/3~s 0:4/3". See the module doc."""
    degs, durs, vels, orns, alts = [], [], [], [], []
    acc = Fraction(0)
    for tok in spec.replace("|", " | ").split():
        if tok == "|":
            if bar is not None and acc % Fraction(bar).limit_denominator(64) != 0:
                raise ValueError(f"M(): bar line after {float(acc):g} beats in {spec!r}")
            continue
        v = 1.0
        while tok and tok[-1] in "!?":
            v *= 1.15 if tok[-1] == "!" else 0.85
            tok = tok[:-1]
        orn = None
        if "~" in tok:
            tok, o = tok.split("~")
            orn = _ORN[o]
        d, dur = tok.split(":")
        alt = 0
        while d and d[-1] in "#b" and d not in ("r",):
            alt += 1 if d[-1] == "#" else -1
            d = d[:-1]
        fr = Fraction(dur)
        acc += fr
        degs.append(None if d == "r" else int(d))
        durs.append(float(fr))
        vels.append(v)
        orns.append(orn)
        alts.append(alt)
    if bar is not None and acc % Fraction(bar).limit_denominator(64) != 0:
        raise ValueError(f"M(): total {float(acc):g} beats is not whole bars in {spec!r}")
    return Motif(degs, durs, vels=vels, alts=alts, orns=orns, name=name)


def plain(m: Motif) -> Motif:
    """The same motif without ornaments (a doubling voice plays plainer)."""
    out = Motif._from(m.notes, m.name, m.offset)
    for x in out.notes:
        x.orn = None
    return out


def jaw(track, piece, start_bar, bars, ks, grid="x.xx.xx.xx.x", vel=80, fade=None, pitch="D3"):
    """Jaw-harp pulses: `grid` is one bar of steps (12 in 4/4 = the triplet gallop, 16 = sixteenths; any
    length divides the bar; X accent, x hit, o soft, g ghost); ks cycles the harmonic numbers per hit.
    fade=(v0, v1) scales velocity across the bars. pitch only labels the note (the synth's fundamental is a
    parameter; k picks the harmonic)."""
    f = {"X": 1.2, "x": 1.0, "o": 0.72, "g": 0.5}
    g = grid.replace(" ", "")
    i = 0
    for b in range(bars):
        b0 = piece.bar(start_bar + b)
        step = 1 / 3.0 if len(g) == 12 and piece.bar_len(start_bar + b) == 4.0 else \
            piece.bar_len(start_bar + b) / len(g)
        sc = 1.0 if fade is None else fade[0] + (fade[1] - fade[0]) * (b / max(1, bars - 1))
        for j, ch in enumerate(g):
            if ch in f:
                track.note(b0 + j * step, pitch, step, vel=vel * f[ch] * sc, k=ks[i % len(ks)])
                i += 1


def gallop_fifths(track, beat, root, vel=80, shape="canter"):
    """One 4/4 bar of the lute's open-fifth gallop on the 12-step grid. root: MIDI pitch."""
    fifth, octv = root + 7, root + 12
    figs = {
        # (step, pitch, velocity factor, length in beats)
        "canter": [(0, root, 1.0, 0.9), (2, fifth, 0.62, 0.5), (3, octv, 0.78, 0.6), (5, fifth, 0.6, 0.5),
                   (6, root, 0.92, 0.9), (8, fifth, 0.6, 0.5), (9, octv, 0.74, 0.6), (11, fifth, 0.58, 0.4)],
        "sparse": [(0, root, 1.0, 1.6), (3, fifth, 0.6, 1.0), (6, octv, 0.75, 1.4), (9, fifth, 0.55, 1.0)],
        "roll": [(0, root, 1.0, 0.5), (1, fifth, 0.55, 0.4), (2, octv, 0.7, 0.4), (3, fifth, 0.6, 0.4),
                 (4, octv + 2, 0.55, 0.4), (5, octv, 0.62, 0.4), (6, root, 0.9, 0.5), (7, fifth, 0.55, 0.4),
                 (8, octv, 0.68, 0.4), (9, fifth, 0.6, 0.4), (10, octv + 2, 0.55, 0.4), (11, octv, 0.6, 0.4)],
    }
    for step, pc, vf, ln in figs[shape]:
        track.note(beat + step / 3.0, pc, ln, vel=vel * vf)


# the long-necked lute's running riff: a drone string (A3) on the galloping sixteenths, the bass fifth on the
# downbeat, two melodic peaks and a falling turn; per chord: (bass, fifth, peak1, peak2, turn of three)
RIFF_A = {
    "Am": (45, 52, 64, 62, (60, 59, 57)), "D": (50, 57, 66, 64, (66, 64, 62)), "G": (55, 62, 62, 59, (60, 59, 57)),
    "Em": (52, 59, 67, 64, (62, 60, 59)), "C": (48, 55, 64, 67, (64, 62, 60)), "Bm": (47, 54, 62, 66, (64, 62, 59)),
}


def riff(track, beat, chord, vel=78, density="full", drone=57, table=None):
    """One 4/4 bar of the lute riff on the 16th grid. density: full (gallop: x.xx per beat), sparse (bass and
    peaks only), eighths (the slowed outro form)."""
    bass, fifth, p1, p2, turn = (table or RIFF_A)[chord]
    ev = {"full": [(0, "B"), (2, "d"), (3, "d"), (4, "p1"), (6, "d"), (7, "d"), (8, "p2"), (10, "d"), (11, "d"),
                   (12, "t0"), (13, "t1"), (14, "t2")],
          "sparse": [(0, "B"), (4, "p1"), (8, "p2"), (12, "t0"), (14, "t2")],
          "eighths": [(0, "B"), (2, "d"), (4, "p1"), (6, "d"), (8, "p2"), (10, "d"), (12, "t0"), (14, "t2")]}[density]
    for step, kind in ev:
        t = beat + step / 4.0
        if kind == "B":
            track.chord(t, [bass, fifth], 0.9 if density != "full" else 0.5, vel=vel, strum=0.012)
        elif kind == "d":
            track.note(t, drone, 0.3, vel=vel * (0.5 if step % 4 == 3 else 0.58))
        elif kind in ("p1", "p2"):
            track.note(t, p1 if kind == "p1" else p2, 0.6 if density == "full" else 1.0, vel=vel * 0.9)
        else:
            track.note(t, turn[int(kind[1])], 0.35 if kind != "t2" else 0.6, vel=vel * (0.8 if kind != "t2" else 0.85))


def bars_of(piece, bar0, chords):
    """Absolute (beat, value) for a list of per-bar values starting at bar0."""
    return [(piece.bar(bar0 + i), v) for i, v in enumerate(chords)]


def sec_to_db(x):
    return 20 * math.log10(max(1e-12, x))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", metavar="OUT.wav", help="render one wind gust to a float WAV")
    a = ap.parse_args()
    if a.demo:
        from types import SimpleNamespace as NS
        import render
        y = synths.render_track("wind", WIND.synth_params, [NS(t0=0.2, t1=6.0, pitch=60, mvel=90, kw={}),
                                                            NS(t0=5.0, t1=9.0, pitch=60, mvel=70,
                                                               kw={"fc": 1100, "fc_to": 600})],
                                int(12 * synths.SR), track="demo")
        render.write_wav(a.demo, y)
        print(a.demo, round(sec_to_db(float(np.sqrt((y.astype(float) ** 2).mean()))), 1), "dB rms")
    else:
        ap.print_help()
