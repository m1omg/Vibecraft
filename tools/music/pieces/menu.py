#!/usr/bin/env python3
"""Menu, "Two Roads" (assets/audio/music/menu.ogg). D Dorian, 80 BPM, 4/4, a 105 s loop (main menu, lobby, loading).

Composer's note. Form (bars): intro 1-2 | dialogue 3-10 | theme A 11-18 | A' climax 19-26 | release 27-32 | return 33-35.
Dialogue: the kingdom fiddle (right) climbs the Wheel D-E-F-G-A and the clans' raspy two-string (left) takes that A
and falls with the Gong-Ring (A-G-D, held E to D) over a small gong; the exchange is sequenced onto G, the Dorian IV.
Theme A fuses both motifs into one 4+4 period, and here the clans speak first (Kingdom 1 opens with the Wheel): the
antecedent is the whole Gong-Ring (A-G-D, the held E sliding onto D) answered by the Wheel climbing to a half close on
A; the consequent climbs the Wheel on G to the high D, turns there (D-B-C), holds A to G (the Gong-Ring's held
second on G) and closes with the Wheel in retrograde. Under it the two-string crosses the other way: it climbs the Wheel while the
fiddle falls, falls with the Gong-Ring while the fiddle climbs, then moves in sixths and ends on its held E, a
suspension over the final D. A' lifts the antecedent an octave; the two-string answers with the Gong-Ring inverted,
rising (G-A-D, held C to D). The new peak phrase is the climax: the fiddle re-strikes A over the big gong and
timpani (bar 23), leaps a fourth to the high D (about 1:07) and falls with the Gong-Ring from the top (D-C-G, held
A to G) over a tonic pedal, with far bronze-horn calls (A-D, then D-A) and the chant whistling A-D-E-D. The release
swaps the roads (two-string climbs, fiddle falls, then both at once, crossing). The return keeps a thread: the
two-string's held E to D, the dulcimer's Wheel head (D-E-F, then D-E-F-G, left hanging for the fiddle's next climb)
and the frame-drum heartbeat, which runs on through the loop seam into the gong bloom of the intro.
Low end: the hurdy-gurdy's D2, A2 and D3 are separate strings; the fifth (A2) lifts wherever the bass sits on G or
B, the octave (D3) sounds only in the climax and leaves before the final held second; the horns only call.
Render: python3 tools/music/render.py tools/music/pieces/menu.py --length-check
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_shared import arp, line, mel, two_string  # noqa: E402
from score import Piece, gong_ring, wheel  # noqa: E402

# theme A, one bar per string: the Gong-Ring answered by the Wheel (antecedent); the Wheel on G, a turn at the top
# (D-B-C, so the line does not become Kingdom 1's head), the held A to G and the Wheel in retrograde (consequent)
THEME = ["A4:2 G4:1 D4:1", "E4:2:s D4:2", "r:1 D4:.5 E4:.5 F4:.5 G4:1.5", "A4:4",
         "r:1 G4:.5 A4:.5 B4:.5 C5:1.5", "D5:2 B4:1 C5:1", "A4:2 G4:1 F4:.5 E4:.5", "D4:4"]
# A': the antecedent an octave up, then the peak phrase (re-struck A, the leap to D6, the Gong-Ring from the top)
THEME_HI = ["A5:2:gu G5:1 D5:1:m", "E5:2:s D5:2", "r:1 D5:.5 E5:.5 F5:.5 G5:1.5:m", "A5:4",
            "A5:1:! D6:3:gu", "C6:1 G5:2 F5:.5 G5:.5", "A5:2:s G5:1 F5:.5 E5:.5", "D5:4"]
# the two-string under theme A: the Wheel climbing while the fiddle falls, a breath, the Gong-Ring falling while it
# climbs (re-struck on the downbeat where the fiddle rests), then sixths and the held E over the final D
COUNTER_A = ["r:1 D3:1 E3:1 F3:1 | G3:1.5 A3:1.5 r:1 | A3:1 G3:1 D3:2 | E3:4:s",
             "D3:2 G3:2 | B3:2 D4:1 E4:1 | C4:2 B3:1 A3:1 | E3:2:s D3:2"]
# the two-string under A': the Gong-Ring inverted and rising (G-A-D, held C to D), then up to F under the peak
COUNTER_A2 = ["C4:3 A3:1 | G3:1 A3:1 D4:2 | C4:2.5:s D4:1.5 | E4:2 C4:1 E4:1",
              "F4:4 | E4:3 C4:1 | D4:2 B3:1 A3:1 | E3:2.5:s D3:1.5"]
# dulcimer voicings per bar: theme A (F, Dm without its low D under the held E, C, Am, G, G/B, Am7, Dm) and
# A' (F, Dm, Am7, Am | Dm, C/D, G/D, D5)
DUL_A = [["F4", "C5", "F5", "A5"], ["A3", "A4", "D5", "F5"], ["C4", "G4", "C5", "E5"], ["A3", "E4", "A4", "C5"],
         ["G3", "D4", "G4", "B4"], ["B3", "D4", "G4", "B4"], ["A3", "E4", "G4", "C5"], ["D4", "A4", "D5", "F5"]]
DUL_A2 = [["F4", "A4", "C5", "F5"], ["D4", "F4", "A4", "D5"], ["A3", "E4", "G4", "C5"], ["C4", "E4", "A4", "E5"],
          ["D4", "A4", "D5", "F5"], ["C4", "G4", "C5", "E5"], ["B3", "D4", "G4", "B4"], ["D4", "A4", "D5", "A5"]]
DUL_REL = [["D4", "A4", "D5", "F5"], ["F4", "C5", "F5", "A5"], ["C4", "G4", "C5", "E5"], ["D4", "A4", "D5", "F5"]]
HEART = "x.......o......."                  # the frame-drum heartbeat: one lub-dub per bar


def build():
    p = Piece("menu", seed=1105, bpm=80, meter=(4, 4), key="D", mode="dorian")
    p.mix = {k: dict(v) for k, v in P.MIX_SHARED.items()}
    p.kind, p.tail_s, p.xfade_s = "loop", 6.0, 3.0
    p.length_range = (103.0, 107.0)
    p.out = "assets/audio/music/menu.ogg"

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    # kingdom on the right, clans on the left, the drone and the big gong in the middle
    hurdy = p.track("hurdy", P.HURDY.variant(gain_db=-9.0, pan=0.0))                   # D2 and the trompette
    h5 = p.track("hurdy_fifth", P.HURDY.variant(gain_db=-9.0, pan=0.0))                # A2
    h8 = p.track("hurdy_octave", P.HURDY.variant(gain_db=-9.0, pan=0.0))               # D3 (climax)
    gong = p.track("gong", P.GONG.variant(pan=0.0))
    gsm = p.track("gong_small", P.GONG_SMALL.variant(pan=-0.4, gain_db=-11.0))
    fid = p.track("fiddle", P.FIDDLE.variant(pan=0.26, vibrato=dict(P.BOW_VIB, depth=0.14)))
    two = p.track("two_string", two_string(pan=-0.26, gain_db=-1.0))
    vla = p.track("viola", P.VIOLA.variant(pan=0.38, gain_db=-5.0))
    vc = p.track("cello", P.CELLO.variant(pan=-0.06, gain_db=-5.0))
    dul = p.track("dulcimer", P.DULCIMER.variant(pan=0.42, gain_db=-6.0))
    hornL = p.track("horn_left", P.BRONZE_HORNS.variant(name="bronze_horn_left", pan=-0.55, gain_db=-9.0))
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
    p.section("return (thread + heartbeat)", 3)

    for bar in (7, 11, 15, 19, 31):
        p.breathe(B(bar), beats=1.0, depth=0.05)
    p.ramp(B(19), B(23), 80, 82)
    p.ramp(B(25), B(27), 82, 77)
    p.ramp(B(27), B(28), 77, 80)
    p.breathe(B(33), beats=2.0, depth=0.06)

    # ======================================================================= the floor: hurdy-gurdy strings
    # D2 holds from the first beat past the loop point, so the seam crossfades drone into drone. The fifth (A2)
    # is a separate string that lifts where the bass sits on G or B (bars 7-8, 15-16, 25); the octave (D3) joins
    # for the climax and leaves before the final held second (E3 to D3, bar 26).
    END = B(36) + 10.0
    level = [(B(1), 84), (B(3), 84), (B(11), 86), (B(19), 88), (B(23), 96), (B(25), 96), (B(27, 2), 88),
             (B(31), 85), (B(33), 84), (END, 84)]

    def lvl(beat):
        for (b0, v0), (b1, v1) in zip(level, level[1:]):
            if b0 <= beat <= b1:
                return v0 + (v1 - v0) * (beat - b0) / max(1e-9, b1 - b0)
        return level[-1][1]

    for (b0, v0), (b1, v1) in zip(level, level[1:]):
        hurdy.curve(b0, b1, v0, v1, "lin")
    hurdy.drone(B(1), END, ["D2"], vel=78)
    fifth_on = [(B(1), B(7, 0.25)), (B(9), B(15, 0.25)), (B(17), B(25, 0.25)), (B(26), END)]
    pts = []
    for i, (a, b) in enumerate(fifth_on):
        h5.drone(a, b, ["A2"], vel=76)
        pts += [(a, 24 if i else lvl(a)), (a + 1.0, lvl(a + 1.0)), (b - 1.25, lvl(b - 1.25)),
                (b, 24 if b < END else lvl(b))]
    for (b0, v0), (b1, v1) in zip(pts, pts[1:]):
        h5.curve(b0, b1, v0, v1, "ease")
    h8.drone(B(19), B(26, 0.25), ["D3"], vel=60)
    h8.curve(B(19), B(21), 30, 80)
    h8.curve(B(21), B(23), 80, 90)
    h8.curve(B(23), B(25), 90, 84)
    h8.curve(B(25), B(26, 0.25), 84, 24)
    for bar in range(23, 26):                                            # trompette coups: the kingdom's dance
        for beat, v in ((1, 64), (3, 70)):
            hurdy.note(B(bar, beat), "D3", 0.35, vel=v + (6 if bar == 23 else 0), stroke="buzz")

    # ======================================================================= the heartbeat
    # one lub-dub per bar from the first bar; it also crosses the seam (bars 33-35, then the hit at the loop point)
    fd.pattern(B(1), 2, HEART, vel=40, drum="dum")
    fd.pattern(B(3), 2, HEART, vel=40, drum="dum")
    fd.pattern(B(5), 2, HEART, vel=43, drum="dum")

    # ======================================================================= intro (1-2): the gong blooms
    gong.note(B(1), "D2", 6.0, vel=66, stroke="bowed")

    # ======================================================================= dialogue (3-10)
    # unit 1: the fiddle climbs the Wheel to A; the two-string takes that A and falls (Gong-Ring) over a small gong
    w1 = fid.play(wheel().displace(1.0).hold_last(0.5), B(3), vel=70, art="legato", dyn="cresc")
    fid.swell(B(3, 1), w1, 58, 98, peak=0.7)
    two.play(gong_ring().ornament(3, "slide"), B(4, 2), octave=-1, vel=76, art="legato", dyn="arch")
    two.swell(B(4, 2), B(6, 2), 70, 104, peak=0.5)
    gsm.note(B(4, 2), "A3", 1, vel=52)
    mel(dul, B(6, 2.5), "E5:1 D5:2.5:o", vel=40, art=None)               # the dulcimer echoes the held second
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
    fd.pattern(B(7), 3, HEART, vel=46, drum="dum")
    fd.pattern(B(10), 1, {"dum": HEART, "tek": "............g.o."}, vel=52)

    # ======================================================================= theme A (11-18)
    b = B(11)
    for i, s in enumerate(THEME):
        b = mel(fid, b, s, vel=78 + (4 if i in (5, 6) else 0), dyn="arch" if i % 2 == 0 else None)
    fid.swell(B(11), B(13), 74, 106, peak=0.45)
    fid.swell(B(13), B(15), 80, 104, peak=0.6)
    fid.swell(B(15), B(17), 84, 114, peak=0.6)
    fid.curve(B(17), B(19), 106, 78)
    mel(two, B(11), COUNTER_A[0], vel=68, dyn="cresc")
    mel(two, B(15), COUNTER_A[1], vel=72, dyn="arch")
    two.curve(B(11), B(12, 3), 66, 94)
    two.curve(B(12, 3), B(14), 94, 80)
    two.swell(B(14), B(15, 1), 78, 98, peak=0.45)
    two.swell(B(15, 1), B(19), 80, 100, peak=0.65)
    line(vc, B(11), [("F2", 4), ("D3", 4), ("C3", 2), ("A2", 2), ("A2", 4), ("G2", 4), ("B2", 4), ("A2", 4),
                     ("D2", 4)], vel=66)
    vc.curve(B(11), B(19), 82, 94)
    for i in range(8):
        arp(dul, B(11 + i), 4.0, DUL_A[i], "0 1 2 1 3 1 2 1", step=0.5, ring=1.7, vel=48 + 2 * (i // 4),
            dyn="arch")
    hornL.note(B(15), "G2", 8.0, vel=66, art="legato")                   # the long bronze horns: far calls
    hornL.swell(B(15), B(17), 30, 92, peak=0.55)
    hornR.notes_seq(B(17), ["A2", "D2"], [4.0, 4.0], vel=62, art="legato")
    hornR.swell(B(17), B(19), 30, 86, peak=0.5)
    fd.pattern(B(11), 8, {"dum": "x.....o.x.......|x.....o.x...o...",
                          "tek": "....o.......o..g|....o.......o.g."}, vel=60)
    fd.roll(B(18, 3), 1.0, "tek", vel0=30, vel1=62, rate=1 / 6.0, accent_end=False)
    gong.note(B(11), "D2", 1, vel=64)
    gsm.note(B(11), "A3", 1, vel=54)                                     # the clans speak first

    # ======================================================================= theme A' (19-26): the climax
    b = B(19)
    for i, s in enumerate(THEME_HI):
        b = mel(fid, b, s, vel=86 + (6 if i in (4, 5) else 0), dyn="arch" if i % 2 == 0 else None)
    fid.swell(B(19), B(21), 84, 110, peak=0.6)
    fid.swell(B(21), B(23), 90, 116, peak=0.85)
    fid.swell(B(23), B(25), 106, 124, peak=0.4)
    fid.curve(B(25), B(27), 116, 72)
    vla.double(fid, B(21), B(27), interval=-12, vel=0.8)                 # the old octave underneath, from the climb
    vla.curve(B(21), B(23), 64, 104)
    vla.curve(B(23), B(27), 104, 68)
    mel(two, B(19), COUNTER_A2[0], vel=76, dyn="cresc")
    mel(two, B(23), COUNTER_A2[1], vel=84, dyn="arch")
    two.curve(B(19), B(21), 80, 96)
    two.swell(B(21), B(23), 90, 106, peak=0.5)
    two.swell(B(23), B(25), 100, 118, peak=0.35)
    two.curve(B(25), B(27), 104, 76)
    # bass: whole notes on F, D, A under the antecedent, then a tonic pedal (drone, horns, timpani) under the peak
    line(vc, B(19), [("F2", 4), ("D3", 4), ("A2", 4), ("A2", 2), ("F2", 2)], vel=74)
    vc.curve(B(19), B(23), 88, 104)
    # the horns only call, from far away: A to D under the leap (23), D to A under the held second (25), then both
    # hold D and A under the two-string's last E (26)
    hornL.notes_seq(B(23), ["A2", "D2"], [2.0, 6.0], vel=74, art="legato")
    hornL.swell(B(23), B(25), 30, 98, peak=0.45)
    hornL.note(B(26), "D2", 4.0, vel=66, art="legato")
    hornL.swell(B(26), B(27, 1), 30, 82, peak=0.4)
    hornR.notes_seq(B(25), ["D3", "A2"], [3.0, 5.0], vel=70, art="legato")
    hornR.swell(B(25), B(27), 30, 94, peak=0.45)
    chant.note(B(21), "D2", 24.5, vel=78, vowels=["u", "o", "a", "o", "a", "o", "u"],
               overtones=[None, None, 12, 8, 9, 8, None])                # whistles A, D, E, D: the Gong-Ring's bones
    chant.curve(B(21), B(23), 30, 96)
    chant.curve(B(25), B(27, 2), 96, 40)
    for i in range(8):
        v = 56 + 3 * i if i < 4 else 70 - 2 * (i - 4)
        fig = "0 1 2 1 3 1 2 1" if i < 4 else "0 2 1 3 2 3 1 3"
        arp(dul, B(19 + i), 4.0, DUL_A2[i], fig, step=0.5, ring=1.6, vel=v, dyn="arch")
    dul.tremolo(B(23, 1), 3.0, "D5", rate=0.125, vel=46, dyn="arch")     # shimmer under the high D
    dul.tremolo(B(24), 2.0, "E5", rate=0.125, vel=44, dyn="dim")
    # drums: the kingdom's straight groove against the clans' triplet gallop
    fd.pattern(B(19), 4, {"dum": "x.....o.x.....o.|x.....o.x..o.o..",
                          "tek": "..g.o..g..g.o.g.|..g.o..g..g.o.gg"}, vel=68)
    fd.pattern(B(23), 4, {"dum": "X.....o.x.....o.|x.....o.x..o.o..",
                          "tek": "..g.o..g..g.o.g.|..g.o..gg.g.o.gg"}, vel=76)
    hand.pattern(B(21), 2, {"tek": "..x..g..x..g"}, vel=52)
    hand.pattern(B(23), 4, {"tek": "g.xg.xg.xg.x", "slap": "........o...|............"}, vel=62)
    deep.pattern(B(19), 4, {"dum": "x.......x.......|x.......x...o..."}, vel=62)
    deep.pattern(B(23), 3, {"dum": "X.......x.......|x.......x...o..."}, vel=74)
    deep.hit(B(26), "doum", vel=68)
    timp.roll(B(22, 1), 3.0, "D2", vel0=24, vel1=92, rate=0.125, accent_end=True)
    timp.hit(B(26), "D2", vel=62)
    gong.note(B(19), "D2", 1, vel=80)
    gong.note(B(23), "D2", 1, vel=104)
    gsm.note(B(19), "A3", 1, vel=58)
    gsm.note(B(25), "D4", 1, vel=62)

    # ======================================================================= release (27-32): the roads swap
    w3 = two.play(wheel().displace(1.0).hold_last(0.5), B(27), octave=-1, vel=74, art="legato", dyn="cresc")
    two.swell(B(27, 1), w3, 64, 100, peak=0.7)
    fid.play(gong_ring().ornament(0, "grace_up"), B(28, 2), vel=70, art="legato", dyn="arch")
    fid.swell(B(28, 2), B(30, 2), 62, 96, peak=0.5)
    gsm.note(B(28, 2), "A3", 1, vel=48)
    line(vc, B(27), [("D2", 8), ("C3", 4), ("D2", 4)], vel=58)
    vc.curve(B(27), B(31), 82, 50)
    for i, ch in enumerate(DUL_REL):
        arp(dul, B(27 + i), 4.0, ch, "0 2 1 3", step=1.0, ring=2.6, vel=44 - 2 * i, skip=(3,) if i == 3 else ())
    fd.pattern(B(27), 2, "x.......o.......|x...............", vel=44, drum="dum")
    fd.pattern(B(29), 4, HEART, vel=40, drum="dum")
    # both at once, crossing: the fiddle falls (Gong-Ring), the two-string climbs (Wheel); its A rings into bar 33
    fid.play(gong_ring(), B(31), vel=66, art="legato", dyn="dim")
    fid.swell(B(31), B(33), 60, 88, peak=0.35)
    two.play(wheel().displace(1.0).hold_last(3.5), B(31), octave=-1, vel=70, art="legato", dyn="arch")
    two.swell(B(31, 1), B(33, 1.5), 60, 90, peak=0.4)
    gsm.note(B(31), "D4", 1, vel=44)

    # ======================================================================= return (33-35): a thread, not a gap
    gong.note(B(33), "D2", 1, vel=70, decay=11.0)
    # the two-string's held second once more (E to D), its D fading across the loop seam
    mel(two, B(33, 2.5), "E3:2.5:s D3:9", vel=64, dyn="dim")
    two.curve(B(33, 1.5), B(34, 1), 58, 80)
    two.curve(B(34, 1), B(36, 2), 80, 44)
    gsm.note(B(35), "A3", 1, vel=40)
    # the dulcimer's Wheel head, twice, a step further the second time, left hanging for the fiddle (bar 3)
    mel(dul, B(33, 1), "D5:.5 E5:.5 F5:2.5:o", vel=46, art=None)
    mel(dul, B(34, 1), "D5:.5 E5:.5 F5:.5 G5:2:o", vel=44, art=None)
    fd.pattern(B(33), 3, HEART, vel=40, drum="dum")
    fd.hit(B(36), "dum", vel=34)                                         # the heartbeat across the seam (soft)
    p.set_end(B(36))
    return p


if __name__ == "__main__":
    print(build().compile().summary())
