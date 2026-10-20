#!/usr/bin/env python3
"""Opening cue, clans (match start, juice SEQ-01): a 10 s flourish, of which the game uses the first 2.4 s
(trimmed with a 300 ms fade). D Dorian, 120 BPM.

0.0 s: the big gong is struck with a slow high-partial bloom, and a second, bowed gong on D swells under the stroke
to a peak at about 1.5 s, so the bronze grows through the cue instead of only decaying; two small gongs (A3, D5)
add the bright shimmer of the bloom, the deep frame drum marks the onset, the two-string drone gives the open D-A
floor. The two horns sit either side of the centre, the lower one lifted to match the upper, with their bronze
edge opened up (a 3 kHz lift, low-pass at 8 kHz); the small gongs and the master presence add air.
0.0-1.5 s: twin bronze horns in
octaves bend up into A (the rising start) and call the Gong-Ring at speed: A-G-D, then the held E that comes to
rest on D at 1.5 s, inside the cue (the kingdom cue rises five notes; this one falls and settles). 1.0 s: the
overtone chant swells in under the resting D. After 2.4 s (not used in game): the horns hold the octave D while the
gong blooms and decays, a soft second gong at 5 s, natural decay to 10 s.
Render: python3 tools/music/render.py tools/music/pieces/opening_clans.py --out assets/audio/music/opening_clans.ogg
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from score import Motif, Piece  # noqa: E402


def build():
    p = Piece("opening_clans", seed=404, bpm=120, meter=(4, 4), key="D", mode="dorian", drift_ms=3.0)
    p.mix = {k: dict(v) for k, v in P.MIX_CLANS.items()}
    p.mix["master"]["presence"] = (4500, 5.0, 0.8)
    p.kind, p.trim_s, p.trim_fade_s, p.tail_s = "cue", 2.4, 0.3, 1.0
    p.set_end(20.0)                                                   # the full flourish is 10 s

    gong = p.track("gong", P.GONG.variant(synth_params=dict(P.GONG.synth_params, bloom=0.9, decay=10.0),
                                          gain_db=-1.0))
    bowed = p.track("gong_bowed", P.GONG.variant(name="gong_bowed", gain_db=-1.0, pan=-0.05, synth_params=dict(
        P.GONG.synth_params, bloom=0.8, decay=8.0, identity=3), color=(230, 170, 50)))   # the swelling bloom
    gsm = p.track("gong_small", P.GONG_SMALL.variant(gain_db=0.0, eq=[("hp", 80), ("highshelf", 4000, 4.0)],
                                                      synth_params=dict(P.GONG_SMALL.synth_params, bloom=0.85,
                                                                        bright=1.0, decay=6.0)))  # the shimmer
    # the horns lead here: closer and with their bronze edge (the in-game tracks keep them far and dark)
    horn_eq = [("hp", 60), ("peak", 1250, 2.5, 1.0), ("peak", 3000, 4.0, 0.9), ("highshelf", 5000, 3.0), ("lp", 8000)]
    hrn1 = p.track("horn_high", P.BRONZE_HORNS.variant(gain_db=-3.0, pan=-0.12, reverb=0.45, lag_ms=0.0,
                                                        timing_ms=3, lo=33, hi=64, eq=horn_eq))
    hrn2 = p.track("horn_low", P.BRONZE_HORNS.variant(gain_db=2.0, pan=0.2, reverb=0.5, lag_ms=6.0,
                                                       timing_ms=3, color=(220, 160, 90), eq=horn_eq))
    drone = p.track("two_string_low", E.TWO_STRING_LOW.variant(gain_db=-13.0))
    chant = p.track("chant", P.CHANT.variant(gain_db=-10.0))
    drum = p.track("deep_drum", P.DEEP_DRUM.variant(gain_db=-9.0))

    # the call: a rising bend into A, then the Gong-Ring at speed, resting on D at beat 3 (1.5 s)
    call = Motif([4, 3, 0, 1, 0], [0.5, 0.5, 1.0, 1.0, 13.0], vels=[1.08, 0.96, 1.0, 1.02, 0.94],
                 orns=["slide_from", None, None, "slide", None], name="gong_ring_fast")
    hrn1.play(call, 0.0, octave=-1, vel=96, art="legato")            # A3 G3 D3 E3 D3
    hrn2.play(call, 0.0, octave=-2, vel=90, art="legato")            # an octave below
    for h, hi in ((hrn1, 118), (hrn2, 110)):
        h.curve(0.0, 0.15, 70, hi)
        h.curve(3.0, 4.6, hi, hi - 10)
        h.curve(4.6, 17.0, hi - 10, 30)
    gong.note(0.0, "D2", 1.0, vel=112)
    bowed.note(0.0, "D2", 4.6, vel=104, stroke="bowed")                # swells through the cue (bow ends at 2.3 s)
    gsm.note(0.0, "A3", 1.0, vel=96)
    gsm.note(0.02, "D5", 1.0, vel=74)
    drum.hit(0.0, "dum", 118)
    drum.hit(3.0, "doum", 70)
    drone.drone(0.0, 14.0, ["D2", "A2"], vel=82)
    drone.curve(0.0, 0.3, 60, 100)
    drone.curve(4.0, 14.0, 100, 30)
    chant.note(2.0, "D2", 12.0, vel=84, vowels=["o", "a", "o"], overtones=[None, 12, 8])
    chant.curve(2.0, 3.2, 40, 110)
    chant.curve(6.0, 14.0, 110, 30)
    gong.note(10.0, "D2", 1.0, vel=70)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
