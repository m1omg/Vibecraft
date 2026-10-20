#!/usr/bin/env python3
"""Defeat, clans (assets/audio/music/defeat_clans.ogg). D Dorian, 60 BPM, 12.0 s end-screen stinger.

Composer's note. A bowed gong swells out of nothing on D and the overtone drone rises under it like wind (vowels
u-o-u, one far whistle on the octave), with a little real wind above. At 2 s a single low bronze horn plays the
Gong-Ring slowly and falls (A-G-D), lifts to the held second E... and stops short: the E is cut off after a beat and
never resolves to D. One soft frame-drum beat answers the silence where the D should have been; the gong rings
on, the drone thins to breath and fades into silence, so the score bed can come in under the decay.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from score import Piece  # noqa: E402

LENGTH_S = 12.0


def build():
    p = Piece("defeat_clans", seed=7707, bpm=60, meter=(4, 4), key="D", mode="dorian", drift_ms=4.0)
    p.mix = P.MIX_CLANS
    p.kind = "track"
    p.out = "assets/audio/music/defeat_clans.ogg"

    gong = p.track("gong", P.GONG.variant(gain_db=-6.0))
    horn = p.track("horn", P.BRONZE_HORNS.variant(gain_db=-5.5, pan=-0.15, reverb=0.6, lag_ms=0.0,
                                                   eq=[("hp", 45), ("lp", 2000), ("lowshelf", 150, 1.0)]))
    chant = p.track("chant", P.CHANT.variant(gain_db=-6.0, synth_params=dict(P.CHANT.synth_params, breath=0.12)))
    wind = p.track("wind", E.WIND.variant(gain_db=-14.0))
    drum = p.track("deep_drum", P.DEEP_DRUM.variant(gain_db=-6.0))
    p.section("swell and fall", 2)
    p.section("silence", 1)

    gong.note(0.0, "D2", 5.0, vel=86, stroke="bowed")
    gong.note(8.7, "A2", 2.2, vel=44, stroke="bowed", decay=5.0)               # after the stop: the ring-on
    chant.note(0.3, "D2", 10.6, vel=80, vowels=["u", "o", "u", "u"], overtones=[None, 8, None, None])
    chant.curve(0.3, 3.5, 30, 96)
    chant.curve(3.5, 8.0, 96, 82)
    chant.curve(8.0, 8.6, 82, 58)                                                   # let the stop be heard
    chant.curve(8.6, 11.0, 58, 18)
    wind.note(0.5, 60, 10.0, vel=86, fc=420, fc_to=760, whistle=0.3)
    # the horn: A - G - D, the held second E ... cut short, no D
    for beat, pitch, dur, v in ((2.0, "A2", 1.5, 84), (3.5, "G2", 1.5, 78), (5.0, "D2", 2.2, 80),
                                (7.2, "E2", 1.15, 76)):
        horn.note(beat, pitch, dur, vel=v, art="legato" if pitch != "E2" else "tenuto",
                  orn="slide" if pitch == "E2" else None)
    horn.curve(2.0, 2.4, 50, 104)
    horn.curve(2.4, 7.0, 104, 92)
    horn.curve(7.2, 7.6, 70, 100)
    horn.curve(7.6, 8.35, 100, 84)
    drum.hit(8.5, "doum", 66)
    p.set_end(10.5)
    p.tail_s = round(LENGTH_S - p.seconds(10.5), 3)
    p.length_range = (LENGTH_S - 0.2, LENGTH_S + 0.2)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
