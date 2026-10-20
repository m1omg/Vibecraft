#!/usr/bin/env python3
"""Victory, clans (assets/audio/music/victory_clans.ogg). D Mixolydian, 12.0 s end-screen stinger.

Composer's note. Beats 0-4: the frame drums gallop on the triplet grid and accelerate (88 -> 124 BPM), stamps and
claps pile in, a roll. Beat 4: one huge bronze gong strike, heard on its own for half a beat (the drum and the
claps under it, the horns not yet in), and the tempo broadens to 100 BPM: the high two-string fiddle and two long
bronze horns an octave below it play a broad rising phrase, the Gong-Ring turned upside down (D-E-A, then G-A and
the Mixolydian flat seventh C bending up to the high D), the lower horn in fifths and sixths under it; the fiddle
carries the line, the horns colour it; the claps keep the backbeat. Beat 11:
the arrival, on a held D major chord (horns D and F#, the two-string drone D-A, the high two-string on A, the
overtone chant on D, the fiddle on the high D) inside the bloom of a second gong stroke, small gongs shimmering;
everything rings out
naturally so the score bed can cross-fade in under the decay.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from ext_clans import M  # noqa: E402
from score import Piece  # noqa: E402

LENGTH_S = 12.0


def build():
    p = Piece("victory_clans", seed=6606, bpm=88, meter=(4, 4), key="D", mode="mixolydian")
    p.mix = P.MIX_CLANS
    p.kind = "track"
    p.out = "assets/audio/music/victory_clans.ogg"
    p.ramp(0.0, 4.0, 88, 124)
    p.set_tempo(4.0, 100)

    gong = p.track("gong", P.GONG.variant(gain_db=2.0))
    bloom = p.track("gong_bloom", P.GONG.variant(name="gong_bloom", gain_db=-6.0, pan=-0.2, synth_params=dict(
        P.GONG.synth_params, bloom=0.95, bright=0.75, decay=12.0), color=(240, 210, 90)))
    gsm = p.track("gong_small", P.GONG_SMALL.variant(gain_db=-7.0))
    # the horns lead (closer than in the in-game tracks); their swelling CC11 sits far above the palette's
    # calibration line, hence the low gains
    hrn1 = p.track("horn_high", P.BRONZE_HORNS.variant(gain_db=-14.0, pan=-0.25, reverb=0.5, lag_ms=4.0,
                                                        eq=[("hp", 60), ("lp", 3600)]))
    hrn2 = p.track("horn_low", P.BRONZE_HORNS.variant(gain_db=-17.0, pan=0.3, reverb=0.55, lag_ms=8.0,
                                                       eq=[("hp", 50), ("lp", 3000)], color=(220, 160, 90)))
    fhi = p.track("two_string_high", P.TWO_STRING_HI.variant(gain_db=-3.5))      # carries the phrase
    drone = p.track("two_string_low", E.TWO_STRING_LOW.variant(gain_db=-10.0))
    chant = p.track("chant", P.CHANT.variant(gain_db=-9.0))
    deep = p.track("deep_drum", P.DEEP_DRUM.variant(gain_db=-3.0))
    hand = p.track("hand_drum", P.HAND_DRUM.variant(gain_db=-6.0))
    claps = p.track("claps", P.CLAPS.variant(gain_db=-6.0))
    p.section("gallop", 1)
    p.section("horn phrase", 2)
    p.section("held chord", 2)

    # ---- beats 0-4: the accelerating gallop
    # the gallop on the triplet grid, crescendo with the accelerando
    deep_g = "D.tD.tD.tDtt"                     # D = dum, t = rim
    hand_g = "x.xx.xx.xx.x"
    for j in range(12):
        v = 74 + 40 * j / 11.0
        t = j / 3.0
        if deep_g[j] == "D":
            deep.hit(t, "dum", v * (1.12 if j % 6 == 0 else 1.0))
        elif deep_g[j] == "t":
            deep.hit(t, "tek", v * 0.7)
        if hand_g[j] == "x":
            hand.hit(t, "tek", v * (0.95 if j % 3 == 0 else 0.7))
    hand.roll(3.0, 1.0, "tek", vel0=60, vel1=110, rate=1 / 6.0, accent_end=False)
    for b, v in ((0, 84), (1, 74), (2, 90), (3, 84)):
        claps.hit(b, "stamp", v)
    for b in (1.0, 2 + 2 / 3, 3.0, 3 + 1 / 3, 3 + 2 / 3):
        claps.hit(b, "clap", 80 + 10 * (b > 2.5))
    # ---- beat 4: one huge gong, the broad rising phrase
    gong.note(4.0, "D2", 1.0, vel=127, decay=14.0)
    deep.hit(4.0, "dum", 90)
    claps.hit(4.0, "clap", 90)
    claps.hit(4.0, "stamp", 90)
    # the phrase starts half a beat after the strike, so the gong is heard alone
    phrase = M("0:1/2 1:1 4:2 | 3:1 4:1 6:1~s 7:9", name="gong_ring_inverted_rising")
    under = M("-3:3/2 0:2 | -1:3 2:9")
    fhi.play(phrase, 4.5, vel=96, art="legato")                         # D4 E4 A4 | G4 A4 C5 D5: carries the line
    hrn1.play(phrase, 4.5, octave=-1, vel=96, art="legato")             # D3 E3 A3 | G3 A3 C4 D4
    hrn2.play(under, 4.5, octave=-1, vel=90, art="legato")              # A2 D3 | C3 F#3
    fhi.curve(4.5, 4.8, 64, 104)
    fhi.curve(4.8, 11.0, 104, 116)
    fhi.curve(11.0, 14.0, 116, 104)
    fhi.curve(14.0, 20.0, 104, 30)
    hrn1.curve(4.5, 4.8, 76, 106)
    hrn1.curve(4.8, 11.0, 106, 118)
    hrn1.curve(11.0, 14.0, 118, 106)
    hrn1.curve(14.0, 20.0, 106, 40)
    hrn2.curve(4.5, 4.8, 72, 100)
    hrn2.curve(4.8, 11.0, 100, 112)
    hrn2.curve(11.0, 14.0, 112, 100)
    hrn2.curve(14.0, 20.0, 100, 36)
    for bar in (1, 2):
        b0 = p.bar(bar)
        deep.hit(b0 + (0 if bar == 2 else 2), "dum", 96)
        deep.hit(b0 + 2 if bar == 2 else b0 + 3.5, "doum", 76)
        claps.hit(b0 + 1, "clap", 88)
        claps.hit(b0 + 3, "clap", 94)
    deep.roll(10.0, 1.0, "tek", vel0=40, vel1=110, rate=1 / 6.0, accent_end=False)
    hand.roll(10.0, 1.0, "tek", vel0=36, vel1=96, rate=1 / 9.0, accent_end=False)
    # ---- beat 11: the held D major chord inside the gong's bloom
    deep.hit(11.0, "dum", 120)
    claps.hit(11.0, "clap", 104)
    claps.hit(11.0, "stamp", 100)
    bloom.note(11.0, "D3", 1.0, vel=110)
    gsm.note(11.0, "A3", 1.0, vel=90)
    gsm.note(11.02, "D5", 1.0, vel=72)
    gsm.note(13.0, "A4", 1.0, vel=58)
    drone.drone(4.5, 20.0, ["D2", "A2"], vel=80)
    drone.curve(4.5, 5.5, 60, 96)
    drone.curve(11.0, 20.0, 104, 34)
    chant.note(9.0, "D2", 11.0, vel=86, vowels=["o", "a", "a"], overtones=[None, 12, 10])
    chant.curve(9.0, 11.5, 40, 112)
    chant.curve(11.5, 20.0, 112, 30)
    p.set_end(17.0)                                                  # the chord rings on through the tail
    p.tail_s = round(LENGTH_S - p.seconds(17.0), 3)
    p.length_range = (LENGTH_S - 0.2, LENGTH_S + 0.2)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
