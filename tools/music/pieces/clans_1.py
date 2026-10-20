#!/usr/bin/env python3
"""Clans 1, "Herd Road" (in-game rotation, about 3:30). D Dorian, 92 BPM, 4/4 with the drums on a 12-step grid
(the galloping 6/8-over-4/4 canter). Proud, windswept and warm: the households on the long road.

Form (78 bars). Intro 1-8: a bowed gong blooms; the overtone chant traces the Gong-Ring's outline (A, E, D) in its
whistle; jaw-harp pulses thicken from halves to the gallop; a two-string drone and a fiddle pickup. A 9-24: the
two-string fiddle states the theme over the canter, built on the Gong-Ring (bars 9-10, falling A-G-D in a
long-short-long rhythm, held E resolving to D), answered by a zig-zag rise (D-E-G-F-A, bar 11): an 8-bar period
(half cadence on A in bar 12, sequence up a fourth in 13-14, cadence in 16); second period 17-24: the fiddle climbs
to the Dorian B and E, the lute answers with the motif diminished (19-20). B 25-40: off the drone onto a moving
bass (F C G Am); the high fiddle sings the motif INVERTED and augmented (A-B-E, held D), the tenor fiddle answers
with the motif in the gaps, two bronze horns call and answer in falling fifths and rising fourths, the chant swells
with them (kept under the horns); claps and stamps on the 4/4 backbeat against the triplet hand drum in 33-40;
climax on A5 in bar 38, carried by a bowed gong on A and the two-string drone swelling under two short horn calls;
the held E5 of bar 40 resolves to D at bar 41 (the motif's held second at the scale of the form). Interlude 41-48:
wind, bowed gong, the lute in fragments of the motif, the tenor fiddle plays the motif in RETROGRADE, rising to A,
the note the theme starts on. A' 49-68: the theme in octaves (fiddle and two-string) with full percussion; second
period as a three-way dialogue; 65-68 a stretto: the motif enters in canon a bar apart at three pitch levels over
an A pedal that swells in the bowed gong and the drone while the horns only call short. Outro 69-78: the gong lands
on D, the motif augmented x1.5 in the tenor, the lute and a far fiddle echo, the drums thin to a heartbeat,
ritardando, the open D fifth tapers away and a last struck gong on the final beat rings out as the tail.
Orchestration arc (voices): about 4 -> 9 -> 12 -> 7 -> 15 -> 8.
Render: python3 tools/music/render.py tools/music/pieces/clans_1.py --out assets/audio/music/clans_1.ogg --length-check
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from ext_clans import M, plain  # noqa: E402
from score import Piece, gong_ring  # noqa: E402

D2, A2 = "D2", "A2"


def build():
    p = Piece("clans_1", seed=101, bpm=92, meter=(4, 4), key="D", mode="dorian")
    p.mix = {k: dict(v) for k, v in P.MIX_CLANS.items()}
    p.mix["master"]["lowshelf"] = (110, -1.5)                    # the drones and the deep drum share the low end
    p.kind, p.tail_s, p.length_range = "track", 4.5, (200.0, 220.0)

    gong = p.track("gong", P.GONG)
    gsm = p.track("gong_small", P.GONG_SMALL)
    chant = p.track("chant", P.CHANT)
    wind = p.track("wind", E.WIND)
    jaw = p.track("jaw_harp", P.JAW_HARP)
    fid = p.track("two_string", P.TWO_STRING)                       # theme (A), tenor counter-lines (B, outro)
    fhi = p.track("two_string_high", P.TWO_STRING_HI.variant(pan=0.2))  # B melody, A' theme on top
    flo = p.track("two_string_low", E.TWO_STRING_LOW.variant(gain_db=-12.0))  # drone and bass
    lute = p.track("lute", P.LUTE)                                   # the canter / chords
    lead = p.track("lute_lead", P.LUTE.variant(gain_db=-1.0, pan=-0.28, color=(90, 240, 210)))  # answers
    hrn1 = p.track("horn_call", P.BRONZE_HORNS)
    hrn2 = p.track("horn_answer", P.BRONZE_HORNS.variant(pan=0.45))
    deep = p.track("deep_drum", P.DEEP_DRUM.variant(gain_db=-5.0, synth_params=dict(P.DEEP_DRUM.synth_params,
                                                                                    ring=0.95)))
    hand = p.track("hand_drum", P.HAND_DRUM)
    claps = p.track("claps", P.CLAPS)

    intro = p.section("intro", 8)
    A = p.section("A", 16)
    B = p.section("B", 16)
    I = p.section("interlude", 8)
    A2s = p.section("A'", 20)
    out = p.section("outro", 10)

    # ---------------------------------------------------------------- tempo: breaths at period ends
    for s, bar in ((A, 8), (A, 16), (B, 8), (A2s, 8), (A2s, 16)):
        p.breathe(s.b(bar), beats=1.0, depth=0.035)
    p.breathe(B.b(16), beats=2.0, depth=0.06)
    p.breathe(I.b(8), beats=2.0, depth=0.05)
    p.rit(out.b(6), out.b(10), to=0.8)

    # ================================================================= INTRO (bars 1-8)
    gong.note(intro.b(0), D2, 10.0, vel=72, stroke="bowed")
    gsm.note(intro.b(4), "A3", 1, vel=58)
    gong.note(intro.b(5, 2), D2, 6.0, vel=60, stroke="bowed")
    wind.note(intro.b(0), 60, 13.0, vel=84, fc=520, fc_to=950)
    wind.note(intro.b(3), 60, 15.0, vel=72, fc=850, fc_to=1400, whistle=0.45)
    chant.note(intro.b(1), D2, 26.5, vel=78, vowels=["u", "o", "u", "o", "a", "o"],
               overtones=[None, 12, 9, 8, 9, 8])
    chant.curve(intro.b(1), intro.b(3), 40, 92)
    chant.curve(intro.b(6), intro.b(7, 3), 92, 55)
    ks = [4, 6, 4, 6, 8, 6, 9, 8]
    E.jaw(jaw, p, intro.bar0 + 2, 2, ks, grid="x.....o.....", vel=70, fade=(0.7, 0.9))
    E.jaw(jaw, p, intro.bar0 + 4, 2, ks, grid="x..o..x..o..", vel=72)
    E.jaw(jaw, p, intro.bar0 + 6, 2, ks, grid="x.xo.xx.xo.x", vel=74, fade=(0.9, 1.05))
    lute.chord(intro.b(4), ["D3", "A3", "D4"], 4.0, vel=54, strum=0.03, art="ring")
    lute.chord(intro.b(6), ["D3", "A3", "D4"], 4.0, vel=60, strum=0.03, art="ring")
    E.gallop_fifths(lute, intro.b(7), 50, vel=56, shape="sparse")
    flo.drone(intro.b(5), A.b(0, 2), [D2, A2], vel=72)
    flo.curve(intro.b(5), intro.b(8), 25, 88)
    hand.pattern(intro.b(6), 2, {"doum": "x.....o.....", "tek": "...g.....g.."}, vel=56)
    deep.roll(intro.b(7, 2), 2.0, "tek", vel0=26, vel1=84, rate=1 / 6.0, accent_end=False)
    fid.play(M("0:1~s 1:2/3 2:1/3"), intro.b(7, 2), vel=66, art="legato")
    fid.curve(intro.b(7, 2), intro.b(8), 70, 100)

    # ================================================================= A (bars 9-24): the theme
    # the head long-short-long (A held, G short, D), the answer zig-zags up (D E G F A) to the half cadence
    per1 = M("4:3/2~gu 3:1/2 0:2 | 1:8/3~s 0:4/3 | 0:2/3 1:1/3 3:1 2:1 4:1 | 5:1~m 4:2 6:1 |"
             "7:3/2~gu 6:1/2 3:2 | 4:8/3~s 3:4/3 | 4:1 2:2/3 1:1/3 0:1 1:1 | 0:3~lm r:1", bar=4, name="theme_a")
    per2a = M("4:2/3 6:1/3 5:1 7:2~s | 8:1~m 7:1 4:2", bar=4)
    per2b = M("3:1 4:2/3 5:1/3 6:2 | 7:1 6:2/3 5:1/3 4:2 | 4:1 3:1 0:1 1:1~s | 0:4~lm", bar=4)
    lute_ans = M("7:2/3 6:1/3 4:2/3 3:1/3 0:2 | 1:2/3 -1:1/3 1:1~gu 0:2", bar=4)      # the motif diminished
    fid.play(per1, A.b(0), vel=84, art="legato", dyn="arch")
    fid.play(per2a, A.b(8), vel=90, art="legato", dyn="cresc")
    lead.play(lute_ans, A.b(10), vel=90, dyn="arch")
    fid.play(per2b, A.b(12), vel=90, art="legato", dyn="dim")
    fid.curve(A.b(0), A.b(4), 100, 108)
    fid.curve(A.b(4), A.b(8), 108, 96)
    fid.curve(A.b(8), A.b(10), 98, 118)
    fid.curve(A.b(10), A.b(12), 118, 96)
    fid.curve(A.b(12), A.b(14), 100, 116)
    fid.curve(A.b(14), A.b(16), 116, 92)
    # lute: the open-fifth canter (rests while it answers in bars 19-20)
    roots_a = ["D3", "D3", "C3", "A2", "G3", "F3", "A2", "D3", "G3", "A2", None, None, "G3", "A2", "G3", "D3"]
    for i, r in enumerate(roots_a):
        if r:
            E.gallop_fifths(lute, A.b(i), _n(r), vel=64 if i < 8 else 70, shape="canter" if i < 8 else "sparse")
    # drone: D2 under everything, the upper string follows the harmony (A, G on C/G bars, F on F)
    flo.drone(A.b(0, 2), B.b(0), D2, vel=74)
    for i, u in enumerate(["A2", "A2", "G2", "A2", "G2", "F2", "A2", "A2",
                           "G2", "A2", "A2", "G2", "G2", "A2", "G2", "A2"]):
        flo.note(A.b(i), u, 4.1, vel=66, art="tenuto")
    flo.curve(A.b(0), A.b(8), 88, 84)
    flo.curve(A.b(8), A.b(16), 84, 92)
    # jaw harp keeps the gallop under period 1, thins under period 2
    E.jaw(jaw, p, A.bar0, 8, ks, grid="x.xo.xx.xo.x", vel=62)
    E.jaw(jaw, p, A.bar0 + 8, 4, ks, grid="x..o..x..o..", vel=54, fade=(1.0, 0.6))
    # drums: DUM . . doum . tek | DUM . . doum . tek  (the canter), the hand drum on the "short" triplets
    deep.hit(A.b(0), "dum", 118)
    deep.pattern(A.b(0), 8, {"dum": "......x.....|X.....x.....|X.....x.....|X.....x.....",
                             "doum": "...o.....o..|...o.....o..|...o.....o..|...o........",
                             "tek": ".....g.....g|.....g.....g|.....g.....g|......g.gxgx"}, vel=88)
    deep.pattern(A.b(8), 8, {"dum": "X.....x.....", "doum": "...o.....o..",
                             "tek": ".....g.....g|.....g.....g|.....g.....g|......g.gxgx"}, vel=94)
    hand.pattern(A.b(0), 8, {"tek": "..x..g..x..g"}, vel=60)
    hand.pattern(A.b(8), 8, {"tek": "g.x.gxg.x.gx", "slap": "........x...|............"}, vel=64)
    gong.note(A.b(0), D2, 1, vel=108)
    gsm.note(A.b(3, 0), "A3", 1, vel=64)
    gsm.note(A.b(7, 2), "A3", 1, vel=58)
    gong.note(A.b(8), D2, 1, vel=84)
    gsm.note(A.b(11, 2), "A3", 1, vel=62)
    gsm.note(A.b(15, 2), "A3", 1, vel=70)
    hrn2.notes_seq(A.b(6), ["A2", "D2"], [3.0, 5.0], vel=70, art="legato")       # one far call under the cadence
    hrn2.swell(A.b(6), A.b(8), 40, 100, peak=0.45)
    hrn1.notes_seq(A.b(13), ["E2", "A2"], [3.0, 5.0], vel=68, art="legato")
    hrn1.swell(A.b(13), A.b(15), 40, 96, peak=0.45)

    # ================================================================= B (bars 25-40): horns and chant swell
    hi1 = M("4:2 5:2 | 8:4~s | 7:3 6:1 | 7:4 | 8:2/3 9:1/3 10:2 9:1 | 8:2 7:2 | 7:1 8:1 4:2~s | 4:4", bar=4,
            name="theme_b_inverted")
    hi2 = M("9:2 8:2 | 7:2 6:1 5:1 | 4:3 5:1 | 4:2 6:1 7:1 | 9:3 10:1 | 11:4~s | 10:2/3 9:1/3 8:1 7:2 | 8:4",
            bar=4)
    fhi.play(hi1, B.b(0), vel=86, art="legato", dyn="arch")
    fhi.play(hi2, B.b(8), vel=92, art="legato", dyn="arch")
    fhi.curve(B.b(0), B.b(1), 60, 100)
    fhi.swell(B.b(1), B.b(8), 96, 116, peak=0.55)
    fhi.curve(B.b(8), B.b(13), 98, 124, shape="ease")
    fhi.curve(B.b(13), B.b(16), 124, 104)
    fhi.curve(B.b(16), I.b(1, 2), 104, 40)
    fhi.note(I.b(0), "D5", 6.0, vel=72, art="slide")               # the held E resolves to D
    # tenor fiddle: the motif in the gaps of the high line (call and response), contrary motion
    ten1 = M("r:4 | 4:3/2 3:1/2 0:2 | 1:3~s 0:1 | -2:2/3 -1:1/3 0:1 2:2 | r:4 | 3:2 5:2 | 4:2 3:1 2:1 | 1:4~s",
             bar=4)
    ten2 = M("r:4 | -1:2 0:1 1:1 | 3:2 2:1 1:1 | 0:4 | 2:2 4:2 | 4:3/2~gu 3:1/2 0:2 | 1:3~s 0:1 | -1:2 -3:2",
             bar=4)
    fid.play(ten1, B.b(0), octave=-1, vel=78, art="legato")
    fid.play(ten2, B.b(8), octave=-1, vel=84, art="legato")
    fid.curve(B.b(0), B.b(8), 88, 100)
    fid.curve(B.b(8), B.b(15), 100, 114)
    fid.curve(B.b(15), B.b(16), 114, 90)
    # moving bass in open fifths (double stops)
    bass_b = ["F2", "F2", "C3", "C3", "G2", "G2", "A2", "A2", "F2", "C3", "G2", "D2", "F2", "C3", "A2", "A2"]
    for i, r in enumerate(bass_b):
        root = _n(r)
        flo.chord(B.b(i), [root, root + 7], 4.1, vel=72 if i < 8 else 80, art="tenuto")
    flo.curve(B.b(0), B.b(8), 80, 92)
    flo.curve(B.b(8), B.b(14), 92, 104)
    flo.curve(B.b(14), B.b(15, 3), 104, 124)
    flo.curve(B.b(15, 3), B.b(16), 124, 90)
    # horns: two-note calls, falling fifths answered by rising fourths; overlapping in the second phrase
    calls = [(hrn1, 0, ["C3", "F2"], [3, 5]), (hrn2, 2, ["G2", "C3"], [3, 5]), (hrn1, 4, ["D3", "G2"], [3, 5]),
             (hrn2, 6, ["E2", "A2"], [3, 5]), (hrn1, 8, ["C3", "F2"], [2, 6]), (hrn2, 9, ["G2", "C3"], [2, 6]),
             (hrn1, 10, ["D3", "G2"], [2, 6]), (hrn2, 11, ["A2", "D2"], [2, 6]), (hrn1, 12, ["C3", "F2"], [3, 5]),
             (hrn2, 13, ["G2", "C3"], [3, 5])]
    for h, bar, ps, ds in calls:
        h.notes_seq(B.b(bar), ps, ds, vel=74 + (6 if bar >= 8 else 0), art="legato")
        h.swell(B.b(bar), B.b(bar, sum(ds)), 42, 112 if bar >= 8 else 104, peak=0.42)
    # the climax (bars 39-40): two short calls that end before the bar line; the bowed gong and the drone swell
    hrn1.notes_seq(B.b(14), ["E3", "A2"], [1.5, 2.0], vel=80, art="legato")
    hrn2.notes_seq(B.b(15), ["A2", "E2"], [1.5, 2.0], vel=76, art="legato")
    hrn1.swell(B.b(14), B.b(14, 3.5), 44, 102, peak=0.4)
    hrn2.swell(B.b(15), B.b(15, 3.5), 40, 96, peak=0.4)
    # the chant swells with the horns, on the bass roots, its whistle on chord tones
    ch_b = [(0, "F2", 8, ["o", "a", "o"], [None, 8, 6]), (2, "C3", 8, ["o", "a", "o"], [None, 6, 8]),
            (4, "G2", 8, ["o", "a", "e"], [None, 8, 9]), (6, "A2", 8, ["a", "o", "u"], [None, 9, 8]),
            (8, "F2", 4, ["o", "a"], [None, 8]), (9, "C3", 4, ["o", "a"], [None, 6]),
            (10, "G2", 4, ["a", "o"], [8, 9]), (11, "D2", 4, ["o", "a"], [None, 12]),
            (12, "F2", 8, ["o", "a", "a"], [None, 10, 12]), (14, "A2", 8, ["a", "o", "u"], [12, 9, 8])]
    for bar, pc, beats, vw, ot in ch_b:
        chant.note(B.b(bar), pc, beats + 0.3, vel=84, vowels=vw, overtones=ot)
    chant.curve(B.b(0), B.b(1), 30, 70)
    chant.curve(B.b(1), B.b(7), 70, 104)
    chant.curve(B.b(7), B.b(8), 104, 82)
    chant.curve(B.b(8), B.b(14), 82, 108)
    chant.curve(B.b(14), B.b(16), 108, 70)
    # lute: rolling triplet arpeggios (phrase 1), the canter (phrase 2)
    for i, r in enumerate(["F3", "F3", "C3", "C3", "G3", "G3", "A2", "A2"]):
        E.gallop_fifths(lute, B.b(i), _n(r), vel=62, shape="sparse")
    for i, r in enumerate(["F3", "C3", "G3", "D3", "F3", "C3", "A2", "A2"]):
        E.gallop_fifths(lute, B.b(8 + i), _n(r), vel=70, shape="canter" if i < 6 else "roll")
    # drums: broad (beats 1 and 3), the hand drum rolls the triplets; claps and stamps on the backbeat in 33-40
    deep.pattern(B.b(0), 8, {"dum": "X.....x....."}, vel=86)
    deep.pattern(B.b(8), 8, {"dum": "X.....x.....", "doum": "...o.....o..",
                             "tek": "............|............|............|......g.gxgx"}, vel=96)
    hand.pattern(B.b(0), 8, {"tek": "g.xg.xg.xg.x"}, vel=56)
    hand.pattern(B.b(8), 8, {"tek": "g.xg.xg.xg.x", "slap": ".........x..|............"}, vel=66)
    for i in range(8):
        b0 = B.b(8 + i)
        claps.hit(b0, "stamp", 84)
        claps.hit(b0 + 2, "stamp", 70)
        claps.hit(b0 + 1, "clap", 82 + 2 * i)
        claps.hit(b0 + 3, "clap", 90 + 2 * i)
        if i in (3, 7):
            claps.hit(b0 + 3 + 1 / 3, "clap", 66)
            claps.hit(b0 + 3 + 2 / 3, "clap", 74)
    gong.note(B.b(0), D2, 1, vel=98)
    gong.note(B.b(8), D2, 1, vel=104)
    for bar, beat, v in ((3, 3, 62), (7, 2, 66), (11, 3, 70), (13, 2, 74)):
        gsm.note(B.b(bar, beat), "A3", 1, vel=v)
    gong.note(B.b(13, 2), A2, 10.0, vel=96, stroke="bowed")                       # the climax swell

    # ================================================================= INTERLUDE (bars 41-48): wind
    wind.note(I.b(0), 60, 12.0, vel=96, fc=600, fc_to=1250, whistle=0.45)
    wind.note(I.b(2, 2), 60, 14.0, vel=88, fc=950, fc_to=520, whistle=0.4)
    wind.note(I.b(5), 60, 13.0, vel=80, fc=700, fc_to=1100, whistle=0.35)
    gong.note(I.b(0, 1), D2, 9.0, vel=66, stroke="bowed")
    gsm.note(I.b(4), "A3", 1, vel=48)
    chant.note(I.b(0, 2), D2, 29.0, vel=70, vowels=["u", "o", "u", "o", "u"], overtones=[None, 8, 9, 8, None])
    chant.curve(I.b(0), I.b(1), 70, 50)
    chant.curve(I.b(1), I.b(5), 50, 76)
    chant.curve(I.b(5), I.b(8), 76, 40)
    lead.play(M("r:4 | 4:3/2 3:1/2 r:2 | r:1 4:2/3 3:1/3 0:2 | r:4 | 7:3/2~gu 6:1/2 3:2 | 4:3 3:1 | r:4 | r:4",
                bar=4),
              I.b(0), vel=72, dyn="dim")
    fid.play(M("0:3/2 1:3~s 0:3/2 3:1 4:5~s"), I.b(5), octave=-1, vel=70, art="legato")
    fid.curve(I.b(5), I.b(7), 60, 100)
    fid.curve(I.b(7), I.b(8), 100, 84)
    flo.drone(I.b(0), I.b(8), [D2, A2], vel=66)
    flo.curve(I.b(0), I.b(4), 70, 58)
    flo.curve(I.b(4), I.b(8), 58, 84)
    for bar in (0, 2, 4, 6):
        deep.hit(I.b(bar), "doum", 58 if bar < 6 else 66)
    jaw.note(I.b(2), "D3", 1 / 3, vel=56, k=4)
    jaw.note(I.b(2, 2), "D3", 1 / 3, vel=46, k=6)
    jaw.note(I.b(6), "D3", 1 / 3, vel=58, k=4)
    jaw.note(I.b(6, 2), "D3", 1 / 3, vel=50, k=8)
    hand.roll(I.b(7, 1), 3.0, "tek", vel0=20, vel1=82, rate=1 / 6.0, accent_end=False)
    deep.roll(I.b(7, 3), 1.0, "tek", vel0=40, vel1=90, rate=1 / 6.0, accent_end=False)

    # ================================================================= A' (bars 49-68): the theme, full
    fhi.play(per1, A2s.b(0), vel=88, art="legato", dyn="arch")
    fid.play(plain(per1), A2s.b(0), octave=-1, vel=80, art="legato")                 # octave below, plainer
    fhi.curve(A2s.b(0), A2s.b(4), 104, 116)
    fhi.curve(A2s.b(4), A2s.b(8), 116, 100)
    fid.curve(A2s.b(0), A2s.b(8), 96, 104)
    # second period: a three-way dialogue
    fhi.play(per2a, A2s.b(8), vel=94, art="legato", dyn="cresc")
    lead.play(lute_ans, A2s.b(10), vel=96, dyn="arch")
    fid.play(M("r:4 | 0:2/3 1:1/3 2:1 3:1 4:1~s"), A2s.b(10), octave=-1, vel=84, art="legato")
    fhi.play(per2b, A2s.b(12), vel=94, art="legato", dyn="arch")
    fid.play(plain(per2b), A2s.b(12), octave=-1, vel=82, art="legato")
    fhi.curve(A2s.b(8), A2s.b(10), 102, 122)
    fhi.curve(A2s.b(10), A2s.b(12), 122, 104)
    fhi.curve(A2s.b(12), A2s.b(16), 106, 120)
    fid.curve(A2s.b(8), A2s.b(16), 100, 112)
    # stretto (bars 65-68): the motif in canon a bar apart at three levels, over an A pedal
    gr = gong_ring(rhythm=(1.5, 0.5, 2.0, 8 / 3, 4 / 3))
    fhi.play(gr.transpose(3).ornament(0, "grace_up").ornament(3, "slide"), A2s.b(16), vel=100, art="legato")
    lead.play(gr.transpose(-3), A2s.b(17), vel=96)
    fid.play(gr.transpose(-3).ornament(3, "slide"), A2s.b(18), octave=-1, vel=92, art="legato")
    fhi.play(M("8:1~m 7:1 4:2~s | 4:4"), A2s.b(18), vel=98, art="legato")
    fhi.curve(A2s.b(16), A2s.b(18), 116, 124)
    fhi.curve(A2s.b(18), A2s.b(20), 124, 100)
    fid.curve(A2s.b(16), A2s.b(20), 108, 120)
    # lute canter (per1, and around the dialogue), then the canon voice
    roots_a2 = ["D3", "D3", "C3", "A2", "G3", "F3", "A2", "D3", "G3", "A2", None, None, "G3", "A2", "G3", "D3",
                None, None, None, "A2"]
    for i, r in enumerate(roots_a2):
        if r:
            E.gallop_fifths(lute, A2s.b(i), _n(r), vel=80, shape="canter" if i < 8 else "roll")
    # drone, then a moving bass, then the A pedal
    flo.drone(A2s.b(0), A2s.b(8), D2, vel=76)
    for i, u in enumerate(["A2", "A2", "G2", "A2", "G2", "F2", "A2", "A2"]):
        flo.note(A2s.b(i), u, 4.1, vel=70, art="tenuto")
    for i, r in enumerate(["G2", "A2", "D2", "C3", "G2", "A2", "G2", "D2"]):
        root = _n(r)
        flo.chord(A2s.b(8 + i), [root, root + 7], 4.1, vel=80, art="tenuto")
    flo.chord(A2s.b(16), ["D2", "A2"], 8.1, vel=82, art="tenuto")
    flo.chord(A2s.b(18), ["A2", "E3"], 8.2, vel=86, art="tenuto")
    flo.curve(A2s.b(0), A2s.b(16), 92, 104)
    flo.curve(A2s.b(16), A2s.b(18), 104, 108)
    flo.curve(A2s.b(18), A2s.b(19, 3), 108, 127)                               # the pedal swells, not the horns
    flo.curve(A2s.b(19, 3), A2s.b(20), 127, 112)
    # horns: sustained swells under the period ends, then the pedal
    hrn1.notes_seq(A2s.b(6), ["A2", "D2"], [3.0, 5.0], vel=76, art="legato")
    hrn1.swell(A2s.b(6), A2s.b(8), 40, 108, peak=0.45)
    hrn2.notes_seq(A2s.b(12), ["G2", "C3"], [3.0, 5.0], vel=76, art="legato")
    hrn2.swell(A2s.b(12), A2s.b(14), 40, 104, peak=0.45)
    hrn1.notes_seq(A2s.b(14), ["E3", "A2"], [3.0, 5.0], vel=78, art="legato")
    hrn1.swell(A2s.b(14), A2s.b(16), 40, 108, peak=0.45)
    hrn1.notes_seq(A2s.b(18), ["E3", "A2"], [1.5, 2.0], vel=82, art="legato")      # short calls over the pedal
    hrn2.notes_seq(A2s.b(19), ["A2", "E2"], [1.5, 2.0], vel=78, art="legato")
    hrn1.swell(A2s.b(18), A2s.b(18, 3.5), 44, 104, peak=0.4)
    hrn2.swell(A2s.b(19), A2s.b(19, 3.5), 40, 98, peak=0.4)
    # chant: out for period 1, swells into the stretto and the pedal
    chant.note(A2s.b(8), D2, 16.3, vel=78, vowels=["o", "a", "o", "a"], overtones=[None, 8, 9, 12])
    chant.note(A2s.b(12), "G2", 8.3, vel=78, vowels=["o", "a"], overtones=[None, 8])
    chant.note(A2s.b(14), D2, 8.3, vel=80, vowels=["a", "o"], overtones=[12, 9])
    chant.note(A2s.b(16), D2, 8.3, vel=84, vowels=["o", "a"], overtones=[None, 12])
    chant.note(A2s.b(18), A2, 8.5, vel=90, vowels=["o", "a", "a"], overtones=[None, 8, 12])
    chant.curve(A2s.b(8), A2s.b(9), 30, 80)
    chant.curve(A2s.b(9), A2s.b(16), 80, 100)
    chant.curve(A2s.b(16), A2s.b(19, 2), 100, 110)
    chant.curve(A2s.b(19, 2), A2s.b(20), 110, 96)
    E.jaw(jaw, p, A2s.bar0, 16, ks, grid="x.xo.xx.xo.x", vel=66)
    E.jaw(jaw, p, A2s.bar0 + 16, 4, ks, grid="xgxxgxxgxxgx", vel=64, fade=(1.0, 1.2))
    # drums: full
    deep.hit(A2s.b(0), "dum", 122)
    deep.pattern(A2s.b(0), 16, {"dum": "......X.....|X.....X.....|X.....X.....|X.....X.....",
                                "doum": "...o.....o..",
                                "tek": "..g..x..g..x|..g..x..g..x|..g..x..g..x|..g..xg.gxgx"}, vel=100)
    deep.pattern(A2s.b(16), 4, {"dum": "X..x..X..x..|X..x..X..x..|X..x..X..x..|X..x..X.....",
                                "tek": ".x.o.x.x.o.x|.x.o.x.x.o.x|.x.o.x.x.o.x|........"}, vel=104)
    deep.roll(A2s.b(19, 2), 2.0, "tek", vel0=50, vel1=110, rate=1 / 6.0, accent_end=False)
    hand.pattern(A2s.b(0), 16, {"tek": "f.xg.xg.xg.x", "slap": "........o...|.....o......"}, vel=70)
    hand.pattern(A2s.b(16), 4, {"tek": "gxggxggxggxg"}, vel=74)
    for i in range(20):
        b0 = A2s.b(i)
        claps.hit(b0, "stamp", 90)
        claps.hit(b0 + 2, "stamp", 74)
        if i < 4:
            pass                                                  # stamps only until bar 53
        elif i >= 16:
            for q in (1, 1 + 2 / 3, 3, 3 + 2 / 3):
                claps.hit(b0 + q, "clap", 92 + (i - 16) * 4)
        else:
            claps.hit(b0 + 1, "clap", 86)
            claps.hit(b0 + 3, "clap", 94)
            if i % 4 == 3:
                claps.hit(b0 + 3 + 2 / 3, "clap", 70)
        if i % 2 == 1:
            claps.hit(b0 + 2 + 2 / 3, "slap", 60)
    gong.note(A2s.b(0), D2, 1, vel=114)
    gong.note(A2s.b(8), D2, 1, vel=100)
    gong.note(A2s.b(16), D2, 1, vel=108)
    for bar, beat, v in ((3, 0, 70), (7, 2, 72), (11, 2, 74), (15, 2, 78), (17, 0, 78), (18, 0, 82),
                         (19, 0, 86)):
        gsm.note(A2s.b(bar, beat), "A3", 1, vel=v)
    gong.note(A2s.b(17, 2), A2, 10.0, vel=96, stroke="bowed")                    # the pedal's swell

    # ================================================================= OUTRO (bars 69-78)
    gong.note(out.b(0), D2, 1, vel=116)
    deep.hit(out.b(0), "dum", 118)
    chant.note(out.b(0), D2, 30.0, vel=82, vowels=["a", "o", "u", "u", "m"], overtones=[12, 9, 8, None, None])
    chant.curve(out.b(0), out.b(2), 104, 84)
    chant.curve(out.b(2), out.b(8), 84, 50)
    chant.curve(out.b(8), out.b(10), 50, 30)
    flo.drone(out.b(0), out.b(8), [D2, A2], vel=76)
    flo.curve(out.b(0), out.b(8), 104, 70)
    flo.chord(out.b(8), ["D2", "A2", "D3"], 8.0, vel=74, art="exact")
    flo.curve(out.b(8), out.b(9), 76, 60)
    flo.curve(out.b(9), out.b(10), 60, 20)                                      # the fifth tapers away
    slow = gong_ring(rhythm=(1.5, 0.5, 2.0, 3.0, 1.5)).augment(1.5).ornament(3, "slide").ornament(0, "grace_up")
    fid.play(slow, out.b(1), vel=80, art="legato", dyn="dim")
    fid.curve(out.b(0), out.b(1), 90, 104)
    fid.curve(out.b(1), out.b(4), 104, 80)
    lead.play(M("4:3/2 3:1/2 0:2~gu | r:4"), out.b(4), octave=-1, vel=80)
    lute.chord(out.b(6), ["D3", "A3", "D4"], 6.0, vel=60, strum=0.04, art="ring")
    lute.chord(out.b(8), ["D3", "A3", "D4", "A4"], 8.0, vel=66, strum=0.05, art="ring")
    fhi.play(M("1:3~s 0:5"), out.b(6), vel=64, art="legato")
    fhi.curve(out.b(6), out.b(7), 50, 92)
    fhi.curve(out.b(7), out.b(8, 3), 92, 40)
    hrn1.notes_seq(out.b(4), ["A2", "D2"], [3.0, 9.0], vel=72, art="legato")
    hrn1.swell(out.b(4), out.b(7), 36, 98, peak=0.4)
    E.jaw(jaw, p, out.bar0, 2, ks, grid="x.xo.xx.xo.x", vel=58, fade=(1.0, 0.8))
    E.jaw(jaw, p, out.bar0 + 2, 2, ks, grid="x..o..x..o..", vel=50, fade=(0.9, 0.7))
    E.jaw(jaw, p, out.bar0 + 4, 2, ks, grid="x.....o.....", vel=46, fade=(0.8, 0.6))
    deep.pattern(out.b(0), 4, {"dum": "......x.....|x.....o.....", "doum": "...o........"}, vel=78)
    for bar, v in ((4, 64), (6, 56), (8, 60)):
        deep.hit(out.b(bar), "doum", v)
    hand.pattern(out.b(0), 4, {"tek": "..g..g..g..g|..g.....g..."}, vel=54)
    gsm.note(out.b(3, 2), "A3", 1, vel=54)
    gong.note(out.b(6), D2, 8.0, vel=58, stroke="bowed")
    gong.note(out.b(9), D2, 1, vel=90, decay=11.0)                              # the last gong: its ring is the tail
    return p


def _n(name):
    from score import n
    return n(name)


if __name__ == "__main__":
    print(build().compile().summary())
