#!/usr/bin/env python3
"""ext_shared.py: writing helpers for the shared pieces (the menu theme "Two Roads" and its score-screen bed),
kept out of the shared toolkit files. Additive: it only imports score.py and palette.py and never changes them.

  mel(track, at, "r:1 D4:.5 E4:.5 F4:.5 G4:1.5:m | A4:2:gu", vel=80)   a melody as text; returns the end beat
  mel_len("D4:.5 E4:1.5")                                             its length in beats
  arp(track, at, beats, ["D3", "A3", "F4"], "0 1 2 1", step=.5)        a broken-chord figure (dulcimer, lute)
  line(track, at, [("D2", 4), ("F2", 2), (None, 2)], vel=70)           a plain line of (pitch | None, beats)
  two_string(pan=-0.26, gain_db=-1.0)                                  the two-string as both shared pieces voice it

Melody tokens are PITCH:DUR[:FLAGS], separated by spaces; "|" bar lines are for the reader and ignored.
  PITCH  a note name (D4, F#3, Bb4), or r / - for a rest
  DUR    beats as a decimal or a fraction (.5, 1.5, 1/3)
  FLAGS  one ornament code: gu / gd grace note from above / below, m mordent, lm lower mordent, t turn, tr trill,
         s / sd bend up / down into the note, ro roll; and marks: ! accent (x1.15), ? soft (x0.8),
         _ tenuto, . staccato, ^ marcato, o let ring, l legato, n normal.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import palette as P  # noqa: E402
from score import _contour, n  # noqa: E402

# The two-string in the shared pieces sits in the tenor (D3-A3), where the GM cello patch under it is heavy in its
# fundamental (130-180 Hz). A real two-string fiddle is nasal there: cut the patch's low body, lift the 800 Hz nose.
TWO_STRING_SHARED_EQ = list(P.TWO_STRING.eq) + [("peak", 155, -7.0, 1.2), ("peak", 800, 2.5, 1.0)]


def two_string(**kw):
    """The shared pieces' two-string (palette TWO_STRING with the tenor EQ above); keywords as Instrument.variant."""
    return P.TWO_STRING.variant(eq=TWO_STRING_SHARED_EQ, **kw)

_ORN = {"gu": "grace_up", "gd": "grace_down", "lm": "lmordent", "m": "mordent", "tr": "trill", "t": "turn",
        "sd": "slide_down", "s": "slide", "ro": "roll"}
_ART = {"_": "tenuto", ".": "staccato", "^": "marcato", "o": "ring", "l": "legato", "n": "normal"}


def _beats(s: str) -> float:
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def parse(spec: str):
    """Melody text -> [(pitch | None, beats, ornament | None, articulation | None, velocity factor)]."""
    out = []
    for tok in spec.split():
        if tok == "|":
            continue
        parts = tok.split(":")
        pitch = None if parts[0] in ("r", "-") else n(parts[0])
        dur = _beats(parts[1])
        orn, art, vf = None, None, 1.0
        flags = parts[2] if len(parts) > 2 else ""
        for code in ("gu", "gd", "lm", "tr", "sd", "ro", "m", "t", "s"):   # longest codes first
            if code in flags:
                orn = _ORN[code]
                flags = flags.replace(code, "", 1)
                break
        for ch in flags:
            if ch == "!":
                vf *= 1.15
            elif ch == "?":
                vf *= 0.8
            elif ch in _ART:
                art = _ART[ch]
            else:
                raise ValueError(f"mel: unknown flag {ch!r} in {tok!r}")
        out.append((pitch, dur, orn, art, vf))
    return out


def mel(track, at, spec, vel=80, art="legato", dyn=None, tr=0, **kw) -> float:
    """Play melody text from beat `at`; dyn shapes the phrase (score.Track.play), tr transposes (semitones),
    extra keywords go to every note. Returns the beat after the last token."""
    toks = parse(spec)
    k = sum(1 for t in toks if t[0] is not None)
    contour = _contour(dyn, k)
    b, i = float(at), 0
    for pitch, dur, orn, a, vf in toks:
        if pitch is not None:
            track.note(b, pitch + tr, dur, vel * vf * contour[i], a or art, orn, **kw)
            i += 1
        b += dur
    return b


def mel_len(spec: str) -> float:
    return sum(t[1] for t in parse(spec))


def arp(track, at, beats, pitches, figure="0 1 2 1", step=0.5, ring=1.6, vel=60, dyn=None, accent=1.12,
        skip=(), art=None) -> float:
    """A broken-chord figure over `beats`: `figure` lists indices into `pitches` (cycled), one per `step`.
    The first stroke of every figure cycle is accented; `skip` lists stroke numbers left out (space)."""
    ps = [n(p) for p in pitches]
    fig = [int(x) for x in figure.split()] if isinstance(figure, str) else list(figure)
    count = int(round(beats / step))
    contour = _contour(dyn, count)
    for i in range(count):
        if i in skip:
            continue
        v = vel * contour[i] * (accent if i % len(fig) == 0 else 1.0)
        track.note(at + i * step, ps[fig[i % len(fig)]], step * ring, v, art)
    return at + beats


def line(track, at, items, vel=70, art="legato", dyn=None, **kw) -> float:
    """A plain line of (pitch | None, beats) pairs (bass lines, long horn notes)."""
    k = sum(1 for p, _ in items if p is not None)
    contour = _contour(dyn, k)
    b, i = float(at), 0
    for pitch, dur in items:
        if pitch is not None:
            track.note(b, pitch, dur, vel * contour[i], art, None, **kw)
            i += 1
        b += dur
    return b
