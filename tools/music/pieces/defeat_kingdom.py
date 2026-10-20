#!/usr/bin/env python3
"""Defeat, kingdom (assets/audio/music/defeat_kingdom.ogg). D minor (Aeolian), 60 BPM, 12.0 s end-screen stinger.

Composer's note. A slow hurdy-gurdy drone on D and A rises out of nothing; at beat 1 the lone fiddle plays the
Wheel upside down and slowed (A-G-F falling to a held E: the climb of the kingdom's motif turned into a descent),
then tries once more (F to E) and stops on E, the second degree, over the D-A drone: it never reaches D. A muffled
frame-drum heartbeat slows under it (lub-dub pairs drifting further apart, then a single stroke), and the drone
and fiddle fade into silence, so the score bed can come in under the decay.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import mel  # noqa: E402
from score import Piece  # noqa: E402


def build():
    p = Piece("defeat_kingdom", seed=5505, bpm=60, meter=(4, 4), key="D", mode="aeolian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 0.82, (11.8, 12.2)
    p.out = "assets/audio/music/defeat_kingdom.ogg"

    hurdy = p.track("hurdy", P.HURDY.variant(gain_db=-6.0, synth_params=dict(P.HURDY.synth_params, buzz=0.2)))
    fid = p.track("fiddle", P.FIDDLE.variant(vibrato=dict(P.BOW_VIB, depth=0.1, delay=0.4), reverb=0.32))
    fd = p.track("heartbeat", P.FRAME_DRUM.variant(name="heartbeat", gain_db=-4.0, eq=[("hp", 40), ("lp", 1800)],
                                                   synth_params={"size": 0.85, "skin": 0.5, "ring": 0.9}))
    p.section("drone + falling phrase", 2)
    p.section("fade", 1)
    p.rit(6.0, 11.0, to=0.9)

    hurdy.drone(0.0, 11.0, ["D2", "A2"], vel=80)
    hurdy.curve(0.0, 2.0, 10, 96)
    hurdy.curve(2.0, 6.0, 96, 84)
    hurdy.curve(6.0, 11.0, 84, 0, "lin")

    # the Wheel inverted and slowed (A-G-F-E), then one more try (F-E) that stops short of D
    mel(fid, 1.0, "A4:1.5:gd G4:1 F4:1 E4:2.5 | F4:.75:s E4:3.25", vel=82, dyn="dim")
    fid.curve(1.0, 3.0, 70, 104)
    fid.curve(3.0, 6.0, 104, 86)
    fid.curve(6.0, 7.0, 86, 96)
    fid.curve(7.0, 11.0, 96, 10, "lin")

    for t, v in ((0.5, 70), (0.82, 52), (2.6, 66), (2.95, 48), (4.8, 60), (5.2, 44), (7.4, 52), (7.85, 38),
                 (10.0, 40)):
        fd.hit(t, "mute", vel=v)
    p.set_end(11.0)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
