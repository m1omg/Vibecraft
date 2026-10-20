#!/usr/bin/env python3
"""Menu, "Two Roads" (assets/audio/music/menu.ogg). D Dorian, 80 BPM, 4/4, a 105 s loop (main menu, lobby, loading).

Composer's note. Form (bars): intro 1-2 | dialogue 3-10 | theme A 11-18 | A' climax 19-26 | release 27-32 | return 33-35.
Dialogue: the kingdom fiddle (right) climbs the Wheel D-E-F-G-A and the clans' raspy two-string (left) takes that A
and falls with the Gong-Ring (A-G-D, held E to D) over a small gong; the exchange is sequenced onto G, the Dorian IV.
Theme A fuses both motifs into one 4+4 period (the Wheel turns straight into the Gong-Ring, half close on A; the
consequent climbs the Wheel on G to the high D and closes with the Wheel in retrograde) over the two-string's counter,
the Gong-Ring augmented, whose held E is a suspension on the final D. Arc: drone and gong, frame drum (7), dulcimer
(11), long bronze horns (15); A' lifts the theme an octave over the viola, horns take the Gong-Ring in the bass, the
chant whistles A-D-E-D, triplet gallop against the straight groove, timpani roll and big gong at bar 23 (high D at
about 1:09). The release swaps the roads (two-string climbs, fiddle falls, then both at once, crossing); the return
thins to drone and a gong whose ring crosses the loop seam into the opening bloom.
Render: python3 tools/music/render.py tools/music/pieces/menu.py --length-check
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_shared import arp, line, mel  # noqa: E402
from score import Piece, gong_ring, wheel  # noqa: E402

# the theme, one bar per string (T1..T8); the A' form is an octave up with ornaments
THEME = ["r:1 D4:.5 E4:.5 F4:.5 G4:1.5", "A4:2 G4:1 D4:1", "E4:3 F4:.5 G4:.5", "A4:4",
         "r:1 G4:.5 A4:.5 B4:.5 C5:1.5", "D5:2 C5:1 G4:1", "A4:2 G4:1 F4:.5 E4:.5", "D4:4"]
THEME_HI = ["r:1 D5:.5 E5:.5 F5:.5 G5:1.5:m", "A5:2:gu G5:1 D5:1", "E5:3 F5:.5 G5:.5", "A5:4",
            "r:1 G5:.5 A5:.5 B5:.5 C6:1.5", "D6:2.5:gu C6:.5 G5:1", "A5:2:s G5:1 F5:.5 E5:.5", "D5:4"]
# the two-string's counter-line: the Gong-Ring augmented x2 (antecedent), then a falling line into the Gong-Ring
COUNTER = ["A3:2 G3:2 D3:3 E3:6:s D3:3",
           "D4:2 C4:2 B3:2 G3:2 A3:1 G3:1 D3:1.5 E3:3:s D3:1.5"]
# dulcimer voicings per theme bar (root, fifth, octave, third or colour)
DUL = [["D4", "A4", "D5", "F5"], ["F4", "C5", "F5", "A5"], ["C4", "G4", "C5", "E5"], ["A3", "E4", "A4", "C5"],
       ["G3", "D4", "G4", "B4"], ["B3", "D4", "G4", "B4"], ["A3", "E4", "G4", "C5"], ["D4", "A4", "D5", "E5"]]


def build():
    p = Piece("menu", seed=1105, bpm=80, meter=(4, 4), key="D", mode="dorian")
    p.mix = {k: dict(v) for k, v in P.MIX_SHARED.items()}
    p.kind, p.tail_s, p.xfade_s = "loop", 6.0, 3.0
    p.length_range = (103.0, 107.0)
    p.out = "assets/audio/music/menu.ogg"

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    # kingdom on the right, clans on the left, the drone and the big gong in the middle
    hurdy = p.track("hurdy", P.HURDY.variant(gain_db=-9.0, pan=0.0))
    gong = p.track("gong", P.GONG.variant(pan=0.0))
    gsm = p.track("gong_small", P.GONG_SMALL.variant(pan=-0.4, gain_db=-11.0))
    fid = p.track("fiddle", P.FIDDLE.variant(pan=0.26, vibrato=dict(P.BOW_VIB, depth=0.14)))
    two = p.track("two_string", P.TWO_STRING.variant(pan=-0.26, gain_db=-1.0))
    vla = p.track("viola", P.VIOLA.variant(pan=0.38, gain_db=-5.0))
    vc = p.track("cello", P.CELLO.variant(pan=-0.06, gain_db=-5.0))
    dul = p.track("dulcimer", P.DULCIMER.variant(pan=0.42, gain_db=-6.0))
    hornL = p.track("horn_left", P.BRONZE_HORNS.variant(name="bronze_horn_left", pan=-0.55, gain_db=-8.5))
    hornR = p.track("horn_right", P.BRONZE_HORNS.variant(name="bronze_horn_right", pan=0.5, gain_db=-10.0,
                                                          reverb=0.75, color=(220, 165, 95)))
    chant = p.track("chant", P.CHANT.variant(gain_db=-11.0))
    fd = p.track("frame_drum", P.FRAME_DRUM.variant(pan=0.16, gain_db=-6.0))
    hand = p.track("hand_drum", P.HAND_DRUM.variant(pan=-0.32, gain_db=-10.0))
    deep = p.track("deep_drum", P.DEEP_DRUM.variant(pan=-0.04, gain_db=-7.0))
    timp = p.track("timpani", P.TIMPANI.variant(gain_db=-8.0))

    p.section("intro", 2)
    p.section("dialogue", 8)
    p.section("theme A", 8)
    p.section("theme A' (climax)", 8)
    p.section("release (roads swap)", 6)
    p.section("return (drone + gong)", 3)

    for bar in (7, 11, 15, 19, 31):
        p.breathe(B(bar), beats=1.0, depth=0.05)
    p.ramp(B(19), B(23), 80, 82)
    p.ramp(B(25), B(27), 82, 77)
    p.ramp(B(27), B(28), 77, 80)
    p.breathe(B(33), beats=2.0, depth=0.06)

    # ======================================================================= the floor: hurdy-gurdy drone
    # one held D-A drone from the first beat past the loop point, so the seam crossfades drone into drone
    hurdy.drone(B(1), B(36) + 10.0, ["D2", "A2"], vel=78)
    hurdy.drone(B(19), B(27, 2), ["D3"], vel=60)                         # the octave fills in for the climax
    hurdy.expr(B(1), 74)
    hurdy.curve(B(3), B(11), 74, 80)
    hurdy.curve(B(11), B(19), 80, 84)
    hurdy.curve(B(19), B(23), 84, 94)
    hurdy.curve(B(25), B(27, 2), 94, 82)
    hurdy.curve(B(27, 2), B(33), 82, 74)
    for bar in range(23, 27):                                            # trompette coups: the kingdom's dance
        for beat, v in ((1, 64), (3, 70)):
            hurdy.note(B(bar, beat), "D3", 0.35, vel=v + (6 if bar == 23 else 0), stroke="buzz")

    # ======================================================================= intro (1-2): the gong blooms
    gong.note(B(1), "D2", 6.0, vel=60, stroke="bowed")

    # ======================================================================= dialogue (3-10)
    # unit 1: the fiddle climbs the Wheel to A; the two-string takes that A and falls (Gong-Ring) over a small gong
    w1 = fid.play(wheel().displace(1.0).hold_last(0.5), B(3), vel=70, art="legato", dyn="cresc")
    fid.swell(B(3, 1), w1, 58, 98, peak=0.7)
    two.play(gong_ring().ornament(3, "slide"), B(4, 2), octave=-1, vel=76, art="legato", dyn="arch")
    two.swell(B(4, 2), B(6, 2), 70, 104, peak=0.5)
    gsm.note(B(4, 2), "A3", 1, vel=52)
    # unit 2: the same exchange on G (the Dorian IV, its B natural is the hopeful turn), harmony enters
    w2 = fid.play(wheel().transpose(3).displace(1.0).hold_last(0.5).ornament(3, "mordent"), B(7), vel=74,
                  art="legato", dyn="cresc")
    fid.swell(B(7, 1), w2, 62, 104, peak=0.7)
    two.play(gong_ring().transpose(3).ornament(3, "slide"), B(8, 2), octave=-1, vel=80, art="legato", dyn="arch")
    two.swell(B(8, 2), B(10, 2), 72, 108, peak=0.5)
    gsm.note(B(8, 2), "D4", 1, vel=56)
    line(vc, B(7), [("G2", 4), ("G2", 2), ("C3", 2), ("F2", 4), ("A2", 4)], vel=62)
    vc.curve(B(7), B(8), 40, 84)
    vc.swell(B(8), B(11), 80, 96, peak=0.6)
    fd.pattern(B(7), 3, "x.......o.......", vel=46, drum="dum")
    fd.pattern(B(10), 1, {"dum": "x.......o.......", "tek": "............g.o."}, vel=52)

    # ======================================================================= theme A (11-18)
    b = B(11)
    for i, s in enumerate(THEME):
        b = mel(fid, b, s, vel=78 + (4 if i in (5, 6) else 0), dyn="arch" if i % 2 == 0 else None)
    fid.swell(B(11), B(13), 74, 106, peak=0.6)
    fid.swell(B(13), B(15), 80, 102, peak=0.35)
    fid.swell(B(15), B(17), 84, 114, peak=0.6)
    fid.curve(B(17), B(19), 106, 78)
    mel(two, B(11), COUNTER[0], vel=68, dyn="arch")
    mel(two, B(15), COUNTER[1], vel=72, dyn="arch")
    two.curve(B(11), B(15), 74, 92)
    two.swell(B(15), B(19), 84, 100, peak=0.7)
    line(vc, B(11), [("D3", 4), ("F2", 4), ("C3", 4), ("A2", 4), ("G2", 4), ("B2", 4), ("C3", 2), ("A2", 2),
                     ("D3", 4)], vel=66)
    vc.curve(B(11), B(19), 82, 94)
    for i in range(8):
        arp(dul, B(11 + i), 4.0, DUL[i], "0 1 2 1 3 1 2 1", step=0.5, ring=1.7, vel=48 + 2 * (i // 4),
            dyn="arch")
    hornL.note(B(15), "G2", 8.0, vel=66, art="legato")                   # the long bronze horns arrive
    hornL.swell(B(15), B(17), 30, 92, peak=0.55)
    hornR.notes_seq(B(17), ["A2", "D2"], [4.0, 4.0], vel=62, art="legato")
    hornR.swell(B(17), B(19), 30, 86, peak=0.5)
    fd.pattern(B(11), 8, {"dum": "x.....o.x.......|x.....o.x...o...",
                          "tek": "....o.......o..g|....o.......o.g."}, vel=60)
    fd.roll(B(18, 3), 1.0, "tek", vel0=30, vel1=62, rate=1 / 6.0, accent_end=False)
    gong.note(B(11), "D2", 1, vel=64)

    # ======================================================================= theme A' (19-26): the climax
    b = B(19)
    for i, s in enumerate(THEME_HI):
        b = mel(fid, b, s, vel=86 + (6 if i in (4, 5) else 0), dyn="arch" if i % 2 == 0 else None)
    fid.swell(B(19), B(21), 84, 110, peak=0.6)
    fid.swell(B(21), B(23), 90, 118, peak=0.85)
    fid.swell(B(23), B(25), 104, 124, peak=0.45)
    fid.curve(B(25), B(27), 116, 72)
    vla.double(fid, B(19), B(27), interval=-12, vel=0.82)                # the old octave underneath
    vla.swell(B(19), B(23), 80, 108, peak=0.9)
    vla.curve(B(23), B(27), 108, 70)
    mel(two, B(19), COUNTER[0].replace("A3:2", "A3:2:gu"), vel=76, dyn="arch")
    mel(two, B(23), COUNTER[1], vel=84, dyn="arch")
    two.curve(B(19), B(23), 84, 104)
    two.swell(B(23), B(27), 104, 116, peak=0.4)
    # bass in half notes; the horns: pedal and build (19-22), then the Gong-Ring counter in the bass (23-26)
    line(vc, B(19), [("D2", 2), ("A2", 2), ("F2", 2), ("C3", 2), ("C3", 2), ("G2", 2), ("A2", 2), ("E2", 2),
                     ("G2", 2), ("D3", 2), ("B2", 2), ("G2", 2), ("C3", 2), ("A2", 2), ("D2", 4)], vel=74)
    vc.curve(B(19), B(23), 90, 104)
    vc.curve(B(25), B(27), 104, 76)
    line(hornL, B(19), [("D2", 8), ("E2", 4), ("A2", 4)], vel=70)
    hornL.swell(B(19), B(21), 40, 96, peak=0.6)
    hornL.swell(B(21), B(22), 50, 96, peak=0.5)
    hornL.curve(B(22), B(23), 60, 112)
    mel(hornL, B(23), "D3:2 C3:2 B2:2 G2:2 A2:1 G2:1 D2:1.5 E2:3 D2:1.5", vel=80, dyn="arch")
    hornL.swell(B(23), B(27), 100, 118, peak=0.45)
    line(hornR, B(21), [("G2", 4), ("A2", 4), ("G2", 4), ("B2", 4), ("C3", 2), ("A2", 2), ("D2", 6)], vel=68)
    hornR.swell(B(21), B(23), 36, 100, peak=0.95)
    hornR.swell(B(23), B(27, 2), 92, 112, peak=0.4)
    chant.note(B(21), "D2", 24.5, vel=78, vowels=["u", "o", "a", "o", "a", "o", "u"],
               overtones=[None, None, 12, 8, 9, 8, None])                # whistles A, D, E, D: the Gong-Ring's bones
    chant.curve(B(21), B(23), 30, 96)
    chant.curve(B(25), B(27, 2), 96, 40)
    for i in range(8):
        v = 56 + 3 * i if i < 4 else 70 - 2 * (i - 4)
        fig = "0 1 2 1 3 1 2 1" if i < 4 else "0 2 1 3 2 3 1 3"
        arp(dul, B(19 + i), 4.0, DUL[i], fig, step=0.5, ring=1.6, vel=v, dyn="arch")
    dul.tremolo(B(23), 2.0, "C5", rate=0.125, vel=46, dyn="arch")        # shimmer under the high C and D
    dul.tremolo(B(24), 2.5, "D5", rate=0.125, vel=50, dyn="dim")
    # drums: the kingdom's straight groove against the clans' triplet gallop
    fd.pattern(B(19), 4, {"dum": "x.....o.x.....o.|x.....o.x..o.o..",
                          "tek": "..g.o..g..g.o.g.|..g.o..g..g.o.gg"}, vel=68)
    fd.pattern(B(23), 4, {"dum": "X.....o.x.....o.|x.....o.x..o.o..",
                          "tek": "..g.o..g..g.o.g.|..g.o..gg.g.o.gg"}, vel=76)
    hand.pattern(B(21), 2, {"tek": "..x..g..x..g"}, vel=52)
    hand.pattern(B(23), 4, {"tek": "g.xg.xg.xg.x", "slap": "........o...|............"}, vel=62)
    deep.pattern(B(19), 4, {"dum": "x.......x.......|x.......x...o..."}, vel=62)
    deep.pattern(B(23), 3, {"dum": "X.......x.......|x.......x...o..."}, vel=76)
    deep.hit(B(26), "doum", vel=70)
    timp.roll(B(22, 1), 3.0, "D2", vel0=24, vel1=92, rate=0.125, accent_end=True)
    timp.hit(B(25), "A2", vel=58)
    timp.hit(B(26), "D2", vel=64)
    gong.note(B(19), "D2", 1, vel=80)
    gong.note(B(23), "D2", 1, vel=108)
    gsm.note(B(21), "A3", 1, vel=58)
    gsm.note(B(25), "D4", 1, vel=64)

    # ======================================================================= release (27-32): the roads swap
    w3 = two.play(wheel().displace(1.0).hold_last(0.5), B(27), octave=-1, vel=74, art="legato", dyn="cresc")
    two.swell(B(27, 1), w3, 64, 100, peak=0.7)
    fid.play(gong_ring().ornament(0, "grace_up"), B(28, 2), vel=70, art="legato", dyn="arch")
    fid.swell(B(28, 2), B(30, 2), 62, 96, peak=0.5)
    gsm.note(B(28, 2), "A3", 1, vel=48)
    line(vc, B(27), [("D2", 8), ("C3", 4), ("D2", 4)], vel=58)
    vc.curve(B(27), B(31), 82, 50)
    for i, ch in enumerate([DUL[0], DUL[1], DUL[2], DUL[0]]):
        arp(dul, B(27 + i), 4.0, ch, "0 2 1 3", step=1.0, ring=2.6, vel=44 - 2 * i, skip=(3,) if i == 3 else ())
    fd.pattern(B(27), 2, "x.......o.......|x...............", vel=44, drum="dum")
    # both at once, crossing: the fiddle falls (Gong-Ring), the two-string climbs (Wheel); clans end on A, kingdom on D
    fid.play(gong_ring(), B(31), vel=66, art="legato", dyn="dim")
    fid.swell(B(31), B(33), 60, 88, peak=0.35)
    two.play(wheel().displace(1.0).hold_last(2.0), B(31), octave=-1, vel=70, art="legato", dyn="arch")
    two.swell(B(31, 1), B(33), 60, 90, peak=0.45)
    gsm.note(B(31), "D4", 1, vel=44)

    # ======================================================================= return (33-35): drone and gong
    gong.note(B(33), "D2", 1, vel=70, decay=11.0)
    mel(dul, B(34, 1), "D5:.5 E5:.5 F5:2.5:o", vel=40, art=None)          # the Wheel's head, left hanging
    p.set_end(B(36))
    return p


if __name__ == "__main__":
    print(build().compile().summary())
