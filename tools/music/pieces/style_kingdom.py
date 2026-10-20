#!/usr/bin/env python3
"""Style test, kingdom (40 s): proves the kingdom band sound before the real pieces are written.

D Mixolydian, 92 BPM, 4/4. A village band gone to war: hurdy-gurdy drone with trompette coups, fiddle on the
Wheel motif, viola counter-line, hammered dulcimer, pizzicato bass and cello, frame drum and field snare, two
low horns far away, a soft wordless hum, the small town bell.

Form (14 bars): intro (bell, drone, dulcimer) | A antecedent (Wheel low, half cadence on A) | A consequent
(Wheel an octave up, viola in contrary-motion canon, climb to the top D, the cadence elides into the outro) |
outro (the answer augmented, ritardando, bell). Render: python3 tools/music/render.py tools/music/pieces/style_kingdom.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from score import Mode, Motif, Piece, wheel, wheel_answer  # noqa: E402


def build():
    p = Piece("style_kingdom", seed=7, bpm=92, meter=(4, 4), key="D", mode="mixolydian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 4.5, (36.0, 46.0)
    m = p.mode                                   # degree 0 = D4
    low = Mode("D", "mixolydian", octave=2)       # degree 0 = D2

    bell = p.track("bell", P.BELL)
    hurdy = p.track("hurdy", P.HURDY)
    dul = p.track("dulcimer", P.DULCIMER)
    fid = p.track("fiddle", P.FIDDLE)
    vla = p.track("viola", P.VIOLA)
    vc = p.track("cello", P.CELLO)
    bass = p.track("bass", P.BASS_PIZZ)
    fd = p.track("frame_drum", P.FRAME_DRUM)
    sn = p.track("snare", P.SNARE)
    hrn = p.track("horns", P.HORNS)
    hum = p.track("hum", P.HUM)
    timp = p.track("timpani", P.TIMPANI)

    intro = p.section("intro", 2)
    ant = p.section("A antecedent", 4)
    con = p.section("A consequent", 4)
    out = p.section("outro", 4)
    p.rit(out.b(2), out.b(4), to=0.8)
    p.breathe(con.start, beats=1.0, depth=0.04)

    # ---- bells and drone: the floor of the band
    bell.note(intro.b(0), "D5", 1, vel=100)
    bell.note(out.b(3), "D5", 1, vel=78)
    hurdy.drone(intro.b(0, 1), out.b(4, 3), ["D2", "A2"], vel=86, stroke="drone")
    hurdy.curve(intro.b(0, 1), intro.b(1, 3), 55, 100)
    hurdy.curve(con.b(0), con.b(3), 100, 112)
    hurdy.curve(out.b(0), out.b(2), 104, 84)
    hurdy.curve(out.b(2), out.b(4, 3), 84, 22)
    for bar in range(1, 13):                      # trompette coups: the hurdy-gurdy's rhythm engine
        b0 = p.bar(bar)
        coups = [(1, 92), (3, 84)] if bar < 6 else [(1, 100), (2.5, 70), (3, 92), (3.5, 64)]
        if bar >= 10:
            coups = [(1, 70), (3, 62)]
        for beat, v in coups:
            hurdy.note(b0 + beat, "D3", 0.32, vel=v, stroke="buzz")

    # ---- harmony: D | D | C | Am || D | G | C | D || D | C | G | D
    chords = {1: 0, 2: 0, 3: 0, 4: 6, 5: 4, 6: 0, 7: 3, 8: 6, 9: 0, 10: 0, 11: 6, 12: 3, 13: 0}
    for bar, deg in chords.items():
        b0 = p.bar(bar)
        tones = m.chord(deg, octave=0 if deg < 4 else -1)
        if bar == 1:
            dul.arp(b0, b0 + 4, [tones[0], tones[2], tones[0] + 12, tones[1] + 12], step=0.5, vel=58,
                    order="up", ring=2.0, dyn="cresc")
        elif 2 <= bar <= 9:
            pat = [0, 2, 1, 3, 2, 3, 1, 2] if bar % 2 else [0, 1, 2, 3, 2, 1, 2, 3]
            v = 54 if bar < 6 else 72
            dul.arp(b0, b0 + 4, [tones[0], tones[1], tones[2], tones[0] + 12], step=0.5, vel=v, order=pat,
                    ring=1.6, accent_every=4)
            if bar in (5, 9):                     # a tremolo flourish at the phrase end
                dul.tremolo(b0 + 3, 1.0, tones[2] + 12, rate=0.125, vel=56, dyn="cresc")
        elif bar >= 10:
            if bar < 13:
                dul.arp(b0, b0 + 4, [tones[0], tones[2], tones[1] + 12], step=1.0, vel=50, ring=3.0)
            else:
                dul.chord(b0, [tones[0], tones[1], tones[2], tones[0] + 12], 4, vel=54, strum=0.035, art="ring")
        root = low.pitch(deg if deg < 5 else deg - 7)
        if 2 <= bar <= 9:                         # pizzicato bass: root, fifth, a scale-tone approach
            bv = 0.85 if bar < 6 else 1.0
            bass.note(b0, root, 1, vel=84 * bv)
            bass.note(b0 + 2, root + 7, 1, vel=72 * bv)
            nd = chords.get(bar + 1, 0)
            nxt = low.pitch(nd if nd < 5 else nd - 7)
            appr = low.neighbour(nxt, -1) if low.neighbour(nxt, -1) != root else low.neighbour(nxt, 1)
            bass.note(b0 + 3.5, appr, 0.5, vel=60)
        if bar >= 6:                              # cello arco sustains under the consequent and the outro
            vc.note(b0, root + 12 if root + 12 < 50 else root, 4, vel=70, art="legato")
    vc.curve(con.b(0), con.b(3), 70, 105)
    vc.curve(out.b(0), out.b(4), 100, 60)

    # ---- A antecedent: the Wheel, low and warm; second statement climbs to the mixolydian C, half cadence
    b = fid.play(wheel(), ant.b(0), art="legato", vel=76, dyn="cresc")
    b = fid.play(wheel_answer().ornament(0, "grace_up"), b, art="legato", vel=74)
    b = fid.play(wheel().transpose(2).ornament(3, "mordent"), b, art="legato", vel=80, dyn="cresc")
    fid.play(Motif([7, 4], [1, 2]), b, art="legato", vel=82)          # falling fourth onto A: open
    fid.swell(ant.b(0), ant.b(2), 78, 104)
    fid.swell(ant.b(2), ant.b(4), 84, 112)

    # ---- A consequent: the Wheel an octave up; the viola answers in contrary motion one beat behind
    b = fid.play(wheel().ornament(3, "slide"), con.b(0), octave=1, art="legato", vel=86, dyn="arch")
    fid.play(wheel_answer().ornament(1, "mordent"), b, octave=1, art="legato", vel=84)
    climb = Motif([4, 5, 6, 7], [0.5, 0.5, 0.5, 2.5]).ornament(3, "grace_down").accent(3, 1.15)
    fid.play(climb, con.b(2), octave=1, art="legato", vel=92)
    fid.play(wheel().invert(2), con.b(3), octave=1, art="legato", vel=90, dyn="dim")   # elides into the outro
    fid.curve(con.b(0), con.b(2, 3), 92, 118)
    fid.curve(con.b(2, 3), con.b(4, 1), 118, 96)

    vla.play(wheel().invert(4).displace(1), con.b(0), octave=-1, art="legato", vel=72)   # A3 down to D3
    vla.play(Motif([3, 2, 1], [1, 1, 2]), con.b(1, 2), octave=-1, art="legato", vel=70)
    vla.play(Motif([2, 4, 3, 2, 1, 0], [2, 2, 1, 1, 1, 3]), con.b(2), art="legato", vel=74)
    vla.curve(con.b(0), con.b(3), 80, 104)

    # ---- horns far away: the minor-third call, then the falling fourth
    hrn.notes_seq(ant.b(3), ["A3", "F#3"], [1.5, 2.5], vel=70, art="legato")
    hrn.notes_seq(con.b(3, 1), ["D3", "A2"], [1.0, 3.0], vel=74, art="legato")

    # ---- outro: dulcimer calls a Wheel fragment, the fiddle answers slowly; hum and bell close it
    dul.play(wheel().fragment(0, 3).rhythm([0.5, 0.5, 1.0]), out.b(1, 2), octave=1, vel=60)
    fid.play(wheel_answer().augment(2), out.b(1, 2), art="legato", vel=70)
    fid.note(out.b(3, 2), "A4", 1.5, vel=58, art="legato")
    fid.note(out.b(3, 3.5), "D4", 3.5, vel=60, art="legato")
    fid.curve(out.b(1, 2), out.b(4, 3), 96, 58)
    vla.notes_seq(out.b(1), ["F#4", "E4", "D4", "C4", "D4"], [2, 2, 2, 2, 6], vel=60, art="legato")
    vla.curve(out.b(1), out.b(4, 3), 92, 55)
    hum.note(out.b(1), "D3", 12, vel=70, vowel="m")
    hum.note(out.b(1, 2), "A2", 10, vel=62, vowel="m")
    hum.swell(out.b(1), out.b(4, 3), 50, 112, peak=0.45)

    # ---- drums: frame-drum heartbeat from bar 1, the field snare joins for the consequent
    fd.pattern(intro.b(1), 1, {"dum": "x.......o.......", "tek": "........g...g.g."}, vel=70)
    fd.pattern(ant.start, 4, {"dum": "x.......x.....o.", "tek": "..g.o.g...g.o.g."}, vel=66)
    fd.pattern(con.start, 4, {"dum": "X.......x..o..o.", "tek": "..g.x.g...g.x.gg"}, vel=92)
    fd.pattern(out.start, 2, {"dum": "x...............", "tek": "........g......."}, vel=66)
    fd.hit(out.b(3), "doum", vel=70)
    sn.roll(ant.b(3, 3), 1.0, "snare", vel0=24, vel1=62, rate=0.0625)
    sn.pattern(con.start, 4, "o..g.go.g.go.g.g|o..g.go.g.go.ggr|o..g.go.g.go.g.g|o..g.go.g.gX....", vel=66)
    sn.roll(out.b(3, 2), 1.5, "snare", vel0=18, vel1=40, rate=0.0625, accent_end=False)
    sn.curve(con.start, con.b(2, 2), 88, 110)
    timp.roll(con.b(1, 2), 2.0, "D2", vel0=22, vel1=70, rate=0.125)    # sparingly: into the climb, once
    timp.note(con.b(3), "A1", 2, vel=64)
    timp.note(out.b(3), "D2", 3, vel=50)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
