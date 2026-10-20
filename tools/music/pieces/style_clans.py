#!/usr/bin/env python3
"""Style test, clans (40 s): proves the clans band sound before the real pieces are written.

D Dorian, 92 BPM, 4/4 with the drums on a 12-step (triplet) grid: the galloping 6/8 feel over the 4/4 line.
Struck and bowed bronze gongs, the raspy two-string fiddle on the Gong-Ring motif (slides, graces), a plucked
long-necked lute answering it, jaw-harp pulses, deep and hand frame drums, long low bronze horns calling and
answering, the wordless overtone chant, claps and stamps.

Form (14 bars): intro (bowed gong, chant drone, jaw harp) | A: fiddle calls the Gong-Ring, the lute answers
with its inversion, half cadence on A | B: struck gong, horns and chant swell, claps on the 4/4 backbeat against
the gallop, the fiddle sequence climbs and resolves | outro: the drums thin to a heartbeat, the motif
augmented, the held second resolves to D under a last gong.
Render: python3 tools/music/render.py tools/music/pieces/style_clans.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from score import Mode, Motif, Piece, gong_ring  # noqa: E402


def build():
    p = Piece("style_clans", seed=11, bpm=92, meter=(4, 4), key="D", mode="dorian")
    p.mix = P.MIX_CLANS
    p.kind, p.tail_s, p.length_range = "track", 5.5, (36.0, 47.0)
    m = p.mode                                    # degree 0 = D4
    low = Mode("D", "dorian", octave=2)

    gong = p.track("gong", P.GONG)
    gsm = p.track("gong_small", P.GONG_SMALL)
    chant = p.track("chant", P.CHANT)
    jaw = p.track("jaw_harp", P.JAW_HARP)
    fid = p.track("two_string", P.TWO_STRING)
    lute = p.track("lute", P.LUTE)
    hrn1 = p.track("horn_call", P.BRONZE_HORNS)
    hrn2 = p.track("horn_answer", P.BRONZE_HORNS.variant(pan=0.45))
    deep = p.track("deep_drum", P.DEEP_DRUM)
    hand = p.track("hand_drum", P.HAND_DRUM)
    claps = p.track("claps", P.CLAPS)

    intro = p.section("intro", 2)
    a = p.section("A", 4)
    b = p.section("B", 4)
    out = p.section("outro", 4)
    p.breathe(b.start, beats=1.0, depth=0.04)
    p.rit(out.b(2), out.b(4), to=0.82)

    # ---- intro: the gong is bowed, the chant drone and the jaw harp wake up
    gong.note(intro.b(0), "D2", 7.0, vel=66, stroke="bowed")
    chant.note(intro.b(0, 2), "D2", 30, vel=80, vowels=["u", "o", "u", "o", "a", "o"],
               overtones=[None, 8, 9, 8, 12, 9])
    chant.curve(intro.b(0, 2), intro.b(2), 30, 78)
    chant.curve(a.start, a.end, 78, 72)
    chant.curve(b.start, b.b(3), 72, 118)
    chant.curve(b.b(3), out.b(3), 118, 50)
    chant.note(b.start, "A2", 16, vel=70, vowels=["o", "a", "o"], overtones=[None, 9, 8])
    ks = [4, 6, 6, 8, 6, 4, 4, 6, 9, 8, 6, 4]          # jaw-harp overtones: D A A D A D | D A E D A D
    for bar in range(1, 12):
        b0 = p.bar(bar)
        for i in range(12):
            if i % 3 == 1 and bar < 6:
                continue                                    # long-short gallop: leave the middle triplet out
            v = 86 if i % 6 == 0 else (64 if i % 3 == 0 else 50)
            if bar >= 10:
                v *= 0.75
            jaw.note(b0 + i / 3.0, "D3", 1 / 3.0, vel=v, k=ks[(i + bar * 5) % 12])

    # ---- harmony: Dm | Dm | C | Am || Dm | G | C | Dm || Dm | C | Dm | Dm
    chords = {2: 0, 3: 0, 4: 6, 5: 4, 6: 0, 7: 3, 8: 6, 9: 0, 10: 0, 11: 6, 12: 0, 13: 0}
    for bar, deg in chords.items():
        b0 = p.bar(bar)
        root = low.pitch(deg if deg < 5 else deg - 7) + 12      # lute register: D3, C3, A3, G3
        fifth = root + 7
        if bar <= 9:                                             # plucked open fifths in the gallop
            for i, (step, pc, v) in enumerate([(0, root, 84), (2, fifth, 58), (3, root + 12, 70),
                                               (6, root, 76), (8, fifth, 56), (9, fifth + 5, 64)]):
                lute.note(b0 + step / 3.0, pc, 0.66, vel=v * (0.8 if bar < 6 else 1.05))
        elif bar < 13:
            lute.note(b0, root, 2, vel=60)
            lute.note(b0 + 2, fifth, 2, vel=50)

    # ---- A: the fiddle calls the Gong-Ring; the lute answers with its inversion (call and response)
    call = gong_ring().ornament(2, "slide").ornament(3, "grace_up")
    fid.play(call, a.b(0), art="legato", vel=82, dyn="arch")
    fid.swell(a.b(0), a.b(2), 80, 110, peak=0.55)
    answer = gong_ring().invert(0).transpose(4).rhythm([0.5, 0.5, 1.0, 1.5, 0.5])     # rising answer to A
    lute.play(answer, a.b(2), octave=0, vel=88)
    lute.play(answer.fragment(0, 3).transpose(-1), a.b(3), octave=0, vel=78)
    fid.play(Motif([4, 3, 1, 4], [1.0, 0.5, 0.5, 2.0], orns=[None, "mordent", None, "slide"]), a.b(3),
             art="legato", vel=76)                                         # half cadence on A

    # ---- B: struck gong, horns call and answer, claps on the 4/4 backbeat against the gallop
    gong.note(b.b(0), "D2", 1, vel=110)
    hrn1.notes_seq(b.b(0, 1), ["A2", "D2"], [3.0, 5.0], vel=78, art="legato")
    hrn2.notes_seq(b.b(2, 1), ["G2", "D2"], [3.0, 4.5], vel=74, art="legato")
    hrn1.swell(b.b(0, 1), b.b(2), 50, 112, peak=0.5)
    hrn2.swell(b.b(2, 1), b.b(4), 50, 108, peak=0.5)
    seq = gong_ring().fragment(0, 3)                                 # the falling cell, sequenced upward
    bb = fid.play(seq.transpose(3).ornament(0, "grace_up"), b.b(0, 1), art="legato", vel=88)
    bb = fid.play(seq.transpose(4).ornament(2, "slide"), bb, art="legato", vel=92)
    fid.play(Motif([7, 6, 4, 5, 4, 3, 1, 0], [0.5, 0.5, 1.0, 1.0, 1.5, 0.5, 1.0, 2.0],
                   orns=[None, None, "slide", "mordent", None, None, "slide", None]), b.b(2), art="legato",
             vel=94, dyn="dim")
    fid.curve(b.b(0), b.b(2), 96, 122)
    fid.curve(b.b(2), b.b(4), 122, 96)
    for bar in range(6, 10):
        b0 = p.bar(bar)
        claps.hit(b0 + 1, "clap", vel=86)
        claps.hit(b0 + 3, "clap", vel=96)
        claps.hit(b0, "stamp", vel=80)
        claps.hit(b0 + 2, "stamp", vel=66)
        if bar == 9:
            claps.hit(b0 + 3.5, "clap", vel=70)
    gsm.note(a.b(3, 3), "A3", 1, vel=70)
    gsm.note(b.b(1, 2), "A3", 1, vel=80)
    gsm.note(b.b(3, 2), "A3", 1, vel=86)

    # ---- outro: heartbeat drums, the motif augmented, the held second resolving under the last gong
    gong.note(out.b(0), "D2", 1, vel=96)
    slow = gong_ring().augment(1.5).ornament(3, "slide")
    fid.play(slow.fragment(0, 4), out.b(0, 1), art="legato", vel=74)
    fid.note(out.b(3, 2), "E4", 1.0, vel=64, art="legato", orn="mordent")
    fid.note(out.b(3, 3), "D4", 4.0, vel=62, art="legato", orn="slide")
    fid.curve(out.b(0), out.b(4, 3), 100, 55)
    gong.note(out.b(2), "D2", 8.0, vel=70, stroke="bowed")
    gong.note(out.b(3, 3), "D2", 1, vel=80)
    hrn1.notes_seq(out.b(1), ["D2"], [8.0], vel=62, art="legato")
    hrn1.swell(out.b(1), out.b(3), 40, 96, peak=0.4)

    # ---- drums: 12 steps a bar = triplet eighths, the gallop
    deep.pattern(intro.b(1, 2), 1, {"dum": "......X.....".replace("X", "x")}, vel=70)
    deep.pattern(a.start, 4, {"dum": "X.....x.....", "tek": "...x.o...x.o"}, vel=72)
    hand.pattern(a.start, 4, {"tek": "..g..g..g..g", "slap": "........x..."}, vel=60)
    deep.pattern(b.start, 4, {"dum": "X..x..X..x..", "tek": ".x.o.x.x.o.x"}, vel=102)
    hand.pattern(b.start, 4, {"tek": "gxggxggxggxg", "slap": "...x.....x.."}, vel=78)
    deep.pattern(out.start, 2, {"dum": "x.....x.....", "tek": "........g..."}, vel=72)
    deep.pattern(out.b(2), 1, {"dum": "x..........."}, vel=60)
    deep.roll(b.b(3, 3), 1.0, "tek", vel0=40, vel1=96, rate=1 / 6.0)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
