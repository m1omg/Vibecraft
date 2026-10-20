#!/usr/bin/env python3
"""The README's minimal example: four bars of the Wheel over a hurdy-gurdy drone (render it to try the toolkit)."""
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # noqa: E401,E702
import palette as P  # noqa: E402
from score import Piece, wheel, wheel_answer  # noqa: E402


def build():
    p = Piece("example_minimal", seed=3, bpm=92, key="D", mode="mixolydian")
    p.mix, p.tail_s = P.MIX_KINGDOM, 4.0
    fid, hg, dul, fd = (p.track("fiddle", P.FIDDLE), p.track("hurdy", P.HURDY),
                        p.track("dulcimer", P.DULCIMER), p.track("drum", P.FRAME_DRUM))
    a = p.section("A", 4)
    hg.drone(a.start, a.end, ["D2", "A2"], vel=86)
    b = fid.play(wheel(), a.b(0), art="legato", dyn="cresc")
    fid.play(wheel_answer().ornament(0, "grace_up"), b, art="legato")
    fid.play(wheel().transpose(2).ornament(3, "mordent"), a.b(2), art="legato")
    for bar, deg in enumerate([0, 0, 6, 0]):
        dul.arp(a.b(bar), a.b(bar + 1), p.mode.chord(deg, octave=-1 if deg > 4 else 0), step=0.5, ring=1.6)
    fd.pattern(a.start, 4, {"dum": "x.......x.....o.", "tek": "..g.o.g...g.o.g."}, vel=76)
    fid.swell(a.b(0), a.b(4), 80, 112)
    p.breathe(a.end, beats=1.0)
    return p
