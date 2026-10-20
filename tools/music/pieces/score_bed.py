#!/usr/bin/env python3
"""End-screen bed, "Two Roads (score)" (assets/audio/music/score.ogg). D Dorian, 72 BPM, 6/8, a 75 s loop.

Composer's note. Form (bars of 6/8): intro 1-4 | dialogue I 5-14 | interlude 15-19 | dialogue II 20-27 | settle 28-30.
The menu theme's two roads, slowed into a tired, swaying 6/8 over a frame-drum heartbeat (lub-dub on each dotted
quarter). Dialogue I is one period traded between the fiddles: the kingdom fiddle climbs the Wheel from a pickup
(D-E-F, G, held A), the clans' two-string takes the A and falls with the Gong-Ring but stops open on its held E
(bar 9); the fiddle climbs the Wheel again on G to the high D and the two-string closes the period with the menu's
cadence line (D-C-G, A-G-F-E, D). The interlude drops the drone: the dulcimer plays the Wheel's head in sequence
(C-D-E-F, D-E-F-G) and the lute answers with the Gong-Ring's head (G-F-C, E-D-A) over a bass F-E-G-A, then sings
the held second B resolving to A. Dialogue II swaps the roads: the two-string climbs the Wheel, the fiddle answers
with the Gong-Ring in stretto over its held A, and the two lines meet on one D (bar 23, a held unison: the clans
slide into it, the kingdom steps into it); they close in parallel sixths, the two-string's E a suspension over the
fiddle's last D. The settle is drone, a last gong and the dulcimer's E-D; the fiddle answers it softly with the
Gong-Ring's fall (A-G-D), and that D fades across the loop seam, so the drone-only stretch stays short on every cycle.
Render: python3 tools/music/render.py tools/music/pieces/score_bed.py --length-check
(The module is score_bed.py so it never shadows the toolkit's score.py; the piece is still named "score".)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_shared import arp, line, mel, two_string  # noqa: E402
from score import Piece  # noqa: E402

HB1 = {"doum": "x...........", "dum": "..o........."}          # one lub-dub per bar (slow heart)
HB2 = {"doum": "x.....x.....", "dum": "..o.....o..."}          # one per dotted quarter


def build():
    p = Piece("score", seed=1175, bpm=72, meter=(6, 8), key="D", mode="dorian")
    p.mix = {k: dict(v) for k, v in P.MIX_SHARED.items()}
    p.kind, p.tail_s, p.xfade_s = "loop", 6.0, 3.0
    p.length_range = (73.0, 77.0)
    p.out = "assets/audio/music/score.ogg"

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    # kingdom on the right, clans on the left, drone, gong, cello and heartbeat in the middle
    hurdy = p.track("hurdy", P.HURDY.variant(gain_db=-8.0, pan=0.0))
    gong = p.track("gong", P.GONG.variant(pan=0.0, gain_db=-6.0))
    gsm = p.track("gong_small", P.GONG_SMALL.variant(pan=-0.4, gain_db=-12.0))
    fid = p.track("fiddle", P.FIDDLE.variant(pan=0.26, vibrato=dict(P.BOW_VIB, depth=0.12, delay=0.3)))
    two = p.track("two_string", two_string(pan=-0.26, gain_db=1.5))   # nasal, not boomy, in the tenor
    dul = p.track("dulcimer", P.DULCIMER.variant(pan=0.38, gain_db=-3.5))
    lute = p.track("lute", P.LUTE.variant(pan=-0.36, gain_db=-4.0))
    vc = p.track("cello", P.CELLO.variant(pan=-0.04, gain_db=-5.5))
    fd = p.track("frame_drum", P.FRAME_DRUM.variant(pan=0.08, gain_db=-8.0))

    p.section("intro (drone + gong)", 4)
    p.section("dialogue I", 10)
    p.section("interlude (dulcimer + lute)", 5)
    p.section("dialogue II (the roads meet)", 8)
    p.section("settle (drone)", 3)

    p.breathe(B(9, 1.5), beats=1.0, depth=0.04)          # the open half close before the second climb
    p.breathe(B(15), beats=1.5, depth=0.06)              # end of dialogue I
    p.set_tempo(B(15), 69)                               # the interlude a little slower
    p.ramp(B(19, 1.5), B(20), 69, 72)                    # the two-string's pickup brings the pulse back
    p.breathe(B(23, 1.5), beats=1.0, depth=0.04)
    p.fermata(B(23, 1.5), beats=1.5, stretch=1.3)        # the meeting unison is held a little
    p.rit(B(26), B(28), to=0.88)                         # the last cadence

    def ring(bar, beat, pitches, beats, vel, strum=0.015):
        dul.chord(B(bar, beat), pitches, beats, vel=vel, strum=strum, art="ring")

    # ======================================================================= the floor: drone and heartbeat
    hurdy.drone(B(1), B(15, 0.6), ["D2", "A2"], vel=76)
    hurdy.drone(B(20), B(31) + 8.0, ["D2", "A2"], vel=76)          # home again; rings past the loop point
    hurdy.expr(B(1), 70)
    hurdy.curve(B(5), B(10), 70, 76)
    hurdy.curve(B(10), B(14), 76, 80)
    hurdy.curve(B(14, 1.5), B(15, 0.6), 80, 30)                     # the crank slows: the drone gives way
    hurdy.curve(B(20), B(20, 1.5), 40, 74)                          # and starts again
    hurdy.curve(B(21), B(26), 74, 80)
    hurdy.curve(B(27), B(30), 80, 70)                               # back to the intro's level at the seam
    fd.pattern(B(3), 1, HB1, vel=30)
    fd.pattern(B(4), 1, HB1, vel=36)
    fd.pattern(B(5), 5, HB2, vel=40)
    fd.pattern(B(10), 5, HB2, vel=45)
    fd.pattern(B(15), 5, HB1, vel=34)                               # the interlude: a slower heart
    fd.pattern(B(20), 4, HB2, vel=44)
    fd.pattern(B(24), 3, HB2, vel=50)
    fd.pattern(B(27), 1, HB1, vel=44)
    fd.pattern(B(28), 1, HB1, vel=36)
    fd.pattern(B(29), 1, {"doum": "x..........."}, vel=28)

    # ======================================================================= intro (1-4): a low gong blooms
    gong.note(B(1), "D2", 7.0, vel=56, stroke="bowed")

    # ======================================================================= dialogue I (5-14)
    # the kingdom climbs the Wheel from a pickup: D-E-F, G, the long A
    mel(fid, B(4, 1.5), "D4:.5 E4:.5 F4:.5 G4:1.5:m A4:5", vel=70, dyn="cresc")
    fid.swell(B(4, 1.5), B(7, 0.5), 56, 100, peak=0.55)
    # the clans take the A and fall (Gong-Ring), but stop open on the held E
    mel(two, B(7), "A3:1 G3:.5 D3:1.5 E3:4.5:s", vel=74, dyn="arch")
    two.swell(B(7), B(9, 1.5), 62, 98, peak=0.55)
    gsm.note(B(7), "A3", 1, vel=44)
    ring(7, 0, ["D4", "A4"], 1.5, 44)
    ring(7, 1.5, ["F4", "D5"], 1.5, 40)
    ring(8, 0, ["C4", "G4"], 1.5, 44)
    ring(8, 1.5, ["E5"], 1.5, 40)
    ring(9, 0, ["E4", "B4"], 1.5, 42)
    # the kingdom climbs again, on G (the Dorian IV and its B natural), to the high D
    mel(fid, B(9, 1.5), "G4:.5 A4:.5 B4:.5 C5:1.5 D5:5:gu", vel=76, dyn="cresc")
    fid.swell(B(9, 1.5), B(12, 0.5), 60, 108, peak=0.5)
    ring(10, 0, ["G3", "D4"], 1.5, 46)
    ring(10, 1.5, ["B4"], 1.5, 42)
    ring(11, 0, ["E4", "B4"], 1.5, 44)
    ring(11, 1.5, ["G4"], 1.5, 40)
    # the clans close the period with the menu's cadence line: D-C-G, A-G-F-E, D
    mel(two, B(12), "D4:1 C4:.5 G3:1.5 A3:1:s G3:.5 F3:.5 E3:1 D3:4:sd", vel=78, dyn="arch")
    two.swell(B(12), B(15, 1.0), 60, 106, peak=0.4)
    ring(12, 0, ["C4", "G4"], 1.5, 44)
    ring(12, 1.5, ["E5"], 1.5, 40)
    ring(13, 0, ["A3", "E4"], 1.5, 42)
    ring(13, 1.5, ["C5"], 1.5, 38)
    ring(14, 0, ["D4", "A4", "E5"], 3.0, 44, strum=0.03)            # Dsus2: neither major nor minor
    line(vc, B(10), [("G2", 3), ("E2", 3), ("C3", 3), ("A2", 3), ("D2", 3)], vel=60)
    vc.swell(B(10), B(15), 46, 90, peak=0.45)

    # ======================================================================= interlude (15-19): no drone
    # the dulcimer sings the Wheel's head in sequence, the lute answers with the Gong-Ring's head
    line(vc, B(15), [("F2", 3), ("E2", 3), ("G2", 3), ("A2", 6)], vel=62)
    for bar in (15, 16, 17):                                        # the bow breathes once per bar
        vc.swell(B(bar), B(bar + 1), 58, 84, peak=0.45)
    vc.swell(B(18), B(20), 58, 90, peak=0.6)
    # the dulcimer's inner figure keeps the 6/8 flowing under both voices (soft eighths, ringing)
    for bar, ch in ((15, ["F3", "C4", "A4"]), (16, ["E3", "C4", "G4"]), (17, ["G3", "D4", "B4"]),
                    (18, ["A3", "E4", "C5"]), (19, ["A3", "E4", "G4"])):
        arp(dul, B(bar, 0.5), 2.5, ch, "1 2 0 1 2", step=0.5, ring=2.2, vel=30, dyn="arch", accent=1.0)
    gsm.note(B(18), "A3", 6.0, vel=38, stroke="bowed")             # a small gong swells into the return
    ring(15, 0, ["F3", "C4"], 2.5, 44)
    mel(dul, B(15), "C5:.5 D5:.5 E5:.5 F5:2.5:o", vel=54, art="ring", dyn="cresc")
    dul.note(B(15, 1.5), "A4", 1.5, vel=38, art="ring")
    mel(lute, B(16), "G3:1 F3:.5 C3:2:o", vel=66, dyn="dim", art=None)
    ring(16, 1.5, ["E4", "G4"], 1.5, 36, strum=0.02)
    ring(17, 0, ["G3", "D4"], 2.5, 44)
    mel(dul, B(17), "D5:.5 E5:.5 F5:.5 G5:2.5:o", vel=56, art="ring", dyn="cresc")
    dul.note(B(17, 1.5), "B4", 1.5, vel=38, art="ring")
    mel(lute, B(18), "E4:1 D4:.5 A3:2:o", vel=68, dyn="dim", art=None)
    ring(18, 1.5, ["C5", "E5"], 1.5, 36, strum=0.02)
    mel(lute, B(19), "B3:1:s A3:2:o", vel=60, art=None)               # the held second resolving
    ring(19, 0, ["E4", "G4", "D5"], 3.0, 36, strum=0.03)

    # ======================================================================= dialogue II (20-27)
    gong.note(B(20), "D2", 1, vel=46)
    # the clans climb the Wheel now (pickup in bar 19) and hold its A
    mel(two, B(19, 1.5), "D3:.5 E3:.5 F3:.5 G3:1.5 A3:6:s", vel=74, dyn="cresc")
    two.swell(B(19, 1.5), B(22, 1.5), 58, 102, peak=0.45)
    ring(20, 0, ["A4", "D5"], 1.5, 42)
    ring(20, 1.5, ["F5"], 1.5, 38)
    # the kingdom answers with the clans' fall, in stretto over the held A, and holds the second (E)
    mel(fid, B(21), "A4:1:gu G4:.5 D4:1.5 E4:4.5 D4:1.5", vel=70, dyn="arch")
    fid.swell(B(21), B(23, 1.5), 58, 100, peak=0.5)
    fid.curve(B(23, 1.5), B(24), 92, 86)
    gsm.note(B(21), "D4", 1, vel=40)
    ring(21, 1.5, ["D5", "F5"], 1.5, 38)
    # under the fiddle's E the two-string climbs the Wheel on G, sliding into the meeting D (bar 23)
    mel(two, B(22, 1.5), "G3:.5 A3:.5 B3:.5 C4:1.5 D4:3:s", vel=76, dyn="cresc")
    two.swell(B(22, 1.5), B(24, 1.5), 66, 104, peak=0.6)
    ring(22, 0, ["G4", "C5"], 1.5, 40)
    ring(22, 1.5, ["E5"], 1.5, 36)
    ring(23, 0, ["G4", "C5"], 1.5, 40)
    line(vc, B(22), [("C3", 4.5), ("D3", 1.5), ("G2", 1.5), ("C3", 1.5), ("G2", 3), ("A2", 3), ("A2", 1.5),
                     ("D2", 4.5)], vel=58)
    vc.swell(B(22), B(25, 1.5), 50, 92, peak=0.7)
    vc.curve(B(26), B(28, 2), 88, 44)
    # together: the fiddle sings the menu's consequent, the two-string falls under it in sixths
    mel(fid, B(24), "G4:.5 A4:.5 B4:.5 C5:1.5 | D5:1:gu C5:.5 G4:1.5 | A4:1 G4:.5 F4:.5 E4:1:m | D4:4",
        vel=78, dyn="arch")
    fid.swell(B(24), B(27), 80, 112, peak=0.4)
    fid.curve(B(27), B(28, 1.0), 92, 46)
    mel(two, B(24, 1.5), "C4:1.5 | B3:1 A3:.5 G3:1.5 | C4:1 B3:.5 A3:.5 E3:2.5 D3:6:sd", vel=70, dyn="arch")
    two.swell(B(24, 1.5), B(27, 1.5), 82, 100, peak=0.5)
    two.curve(B(27, 1.5), B(28, 1.5), 92, 70)
    two.curve(B(28, 1.5), B(29, 1.5), 70, 36)                       # the last D fades under the dulcimer's E-D
    ring(24, 0, ["D5", "G5"], 1.5, 38)
    ring(24, 1.5, ["E5", "G5"], 1.5, 36)
    ring(25, 1.5, ["B4", "D5"], 1.5, 38)
    ring(26, 0, ["C5", "E5"], 1.5, 38)
    ring(26, 1.5, ["C5"], 1.5, 34)
    ring(27, 0, ["A4", "E5"], 1.5, 40)
    ring(27, 1.5, ["D5"], 3.0, 36)

    # ======================================================================= settle (28-30): drone and gong
    gong.note(B(28), "D2", 1, vel=60, decay=11.0)
    mel(dul, B(29), "E5:1.5 D5:4:o", vel=40, art="ring")            # the held second, resolving, once more
    # and the fiddle answers it with the Gong-Ring's fall (A-G-D), its D fading across the loop seam
    mel(fid, B(30), "A4:1 G4:.5 D4:4", vel=50, dyn="dim")
    fid.swell(B(30), B(31, 1.5), 40, 76, peak=0.3)
    p.set_end(B(31))
    return p


if __name__ == "__main__":
    print(build().compile().summary())
