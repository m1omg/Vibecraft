#!/usr/bin/env python3
"""Clans 3, "Long Grass Gallop" (in-game rotation, about 3:25). A Dorian, 100 BPM, 4/4 on a straight sixteenth
grid: the running gallop (da-dada) instead of the triplet canter of "Herd Road", with a drum break in 7/8.
Exhilarating and wind-blown: a fast ride across endless grass.

Form (82 bars). Intro 1-6: the long-necked lute alone in its running riff (a drone string on the galloping
sixteenths, two peaks and a falling turn), the jaw harp joins in bar 3, stamps in bar 5. Drums 7-10: the frame
drums enter at full gallop, a half close on E, the fiddle runs up into the theme. A 11-26: the high fiddle states
the theme: the Gong-Ring diminished to eighths (E-D-A, B resolving to A) with a gallop turn, answered by scale runs
to the octave; period 1 ends on the held second resolving to A (bars 17-18), period 2 (19-26, the jaw harp drops
out) sequences a run figure down a step (19, 21) and climbs to B5 (23). B 27-46, the valley and the climb back:
call and response between fiddle and lute over a bare floor (one deep stroke a bar, hand-drum ghost notes, no
stamps, no jaw harp; the lute riff only under the fiddle's calls): two-bar calls (the motif INVERTED, rising)
answered by the lute with the motif upright (27-34), one-bar exchanges (35-38); then the gallop and the stamps come
back for the half-bar exchanges (39-42, breathless), the jaw harp in 41, and both together in octave runs to a
held E and a cut-off (43-46). Break 47-54: hand drum and stamps alone in 7/8 + 4/4 (2+2+3 against the gallop), the
deep drum, claps, jaw harp and bright small gongs join at bar 51 and the break crescendos into A'. A' 55-72: the
theme at full power, the raspy low fiddle an octave under the high one, claps on the backbeat (55-62); then the
lute takes the second period of the theme under a new fiddle descant, over a reharmonised, moving bass
(Bm G Em Am G D Em Am), the drums in half time and then galloping again, a burst of overtone chant and the big gong
at the climax (67-70), a two-bar run to the arrival. Outro 73-82: a ritardando from 100 to 72 BPM, the riff in
eighths, the drums thin to a heartbeat, the motif augmented x2 on the fiddle, the held B resolving to A over the
last gong, which rings out.
Render: python3 tools/music/render.py tools/music/pieces/clans_3.py --out assets/audio/music/clans_3.ogg --length-check
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from ext_clans import M, plain  # noqa: E402
from score import Piece, gong_ring  # noqa: E402

A2, E3 = "A2", "E3"
KS = [4, 6, 4, 8, 6, 4, 9, 8, 4, 6, 4, 12]           # jaw harp on A2: A4 E5 A4 A5 E5 A4 B5 A5 ... (no C#)


def build():
    p = Piece("clans_3", seed=303, bpm=100, meter=(4, 4), key="A", mode="dorian")
    p.mix = {k: dict(v) for k, v in P.MIX_CLANS.items()}
    p.mix["master"]["lowshelf"] = (110, -1.0)
    p.kind, p.tail_s, p.length_range = "track", 4.5, (198.0, 215.0)

    gong = p.track("gong", P.GONG)
    gsm = p.track("gong_small", P.GONG_SMALL)
    chant = p.track("chant", P.CHANT.variant(gain_db=-7.0))
    wind = p.track("wind", E.WIND.variant(gain_db=-17.0))
    jaw = p.track("jaw_harp", P.JAW_HARP.variant(synth_params=dict(P.JAW_HARP.synth_params, fundamental=45),
                                                  gain_db=-11.0))     # under the voice band
    fhi = p.track("two_string_high", P.TWO_STRING_HI.variant(gain_db=0.0, pan=0.16))   # the theme, the runs
    fid = p.track("two_string", P.TWO_STRING.variant(gain_db=-3.0, pan=0.04))            # raspy octave below
    flo = p.track("two_string_low", E.TWO_STRING_LOW.variant(gain_db=-14.0))            # drone
    lute = p.track("lute", P.LUTE.variant(gain_db=-5.5, pan=-0.3))                        # the riff
    lead = p.track("lute_lead", P.LUTE.variant(gain_db=0.0, pan=-0.42, color=(90, 240, 210)))  # answers
    deep = p.track("deep_drum", P.DEEP_DRUM.variant(gain_db=-5.0, synth_params=dict(P.DEEP_DRUM.synth_params,
                                                                                    ring=0.8)))
    hand = p.track("hand_drum", P.HAND_DRUM.variant(gain_db=-7.0))
    claps = p.track("claps", P.CLAPS)

    intro = p.section("intro", 6)
    dr = p.section("drums", 4)
    A = p.section("A", 16)
    B = p.section("B", 20)
    brk = p.section("break", 8, meter=(7, 8))
    for i, m in enumerate([(7, 8), (7, 8), (4, 4), (7, 8), (7, 8), (4, 4), (7, 8), (4, 4)]):
        p.set_meter(brk.bar0 + i, m)
    A2s = p.section("A'", 18, meter=(4, 4))
    out = p.section("outro", 10)

    for s, bar in ((A, 8), (A, 16), (A2s, 8)):
        p.breathe(s.b(bar), beats=0.75, depth=0.03)
    p.breathe(B.b(20), beats=1.5, depth=0.05)
    p.ramp(out.b(2), out.b(9), 100, 72)

    # ================================================================= INTRO (1-6) and DRUMS (7-10)
    ch_intro = ["Am", "Am", "Am", "Am", "G", "Am", "Am", "Am", "G", "Em"]
    for i, c in enumerate(ch_intro):
        E.riff(lute, p.bar(i), c, vel=70 + 2 * i if i < 6 else 84)
    E.jaw(jaw, p, intro.bar0 + 2, 2, KS, grid="x...x.x.x...x.x.", vel=66, fade=(0.8, 1.0), pitch="A2")
    E.jaw(jaw, p, intro.bar0 + 4, 6, KS, grid="x.xxx.xxx.xxx.xx", vel=70, pitch="A2")
    wind.note(intro.b(0), 60, 12.0, vel=80, fc=700, fc_to=1300, whistle=0.4)
    wind.note(intro.b(3), 60, 10.0, vel=70, fc=1100, fc_to=600, whistle=0.35)
    for bar in (4, 5):
        for beat in (0, 2):
            claps.hit(intro.b(bar, beat), "stamp", 64 + 8 * (bar - 4))
    claps.hit(intro.b(5, 3), "stamp", 70)
    claps.hit(intro.b(5, 3.5), "stamp", 76)
    gsm.note(intro.b(3, 0), "E4", 1, vel=60)
    gsm.note(intro.b(5, 2), "A3", 1, vel=66)
    flo.drone(intro.b(4), A.b(0), [A2, E3], vel=66)
    flo.curve(intro.b(4), intro.b(6), 30, 84)
    hand.pattern(intro.b(5), 1, {"tek": "g.ggg.ggg.ggg.gg"}, vel=50)
    deep.roll(intro.b(5, 3), 1.0, "tek", vel0=30, vel1=96, rate=0.125, accent_end=False)
    # drums enter
    gong.note(dr.b(0), "A2", 1, vel=104)
    deep.pattern(dr.b(0), 4, {"dum": "X.......X.......", "doum": "....o.......o...",
                              "tek": "..g...g...g...g.|..g...g...g...g.|..g...g...g...g.|..g...g...gxgxgx"}, vel=96)
    hand.pattern(dr.b(0), 4, {"tek": "X.oox.ooX.oox.oo|X.oox.ooX.oox.oo|X.oox.ooX.oox.oo|X.ooX.ooXoooXrrr"}, vel=70)
    for bar in range(4):
        for beat in (0, 2):
            claps.hit(dr.b(bar, beat), "stamp", 80)
    gsm.note(dr.b(3, 2), "E4", 1, vel=72)
    fhi.play(M("-3:1/4 -2:1/4 -1:1/4 0:1/4 1:1/4 2:1/4 3:1/2"), dr.b(3, 2), vel=74, art="legato", dyn="cresc")
    fhi.curve(dr.b(3, 2), dr.b(4), 80, 108)

    # ================================================================= A (11-26): the theme
    t1 = M("4:1/2 3:1/2 0:1 1:1/2 2:1/4 1:1/4 0:1 |"                      # the motif diminished + a gallop turn
           "4:1/2 3:1/4 4:1/4 5:1/2 6:1/4 5:1/4 7:3/2~s 6:1/2 |"           # rising gallop figures to the octave
           "7:1/2 6:1/2 3:1 4:3/2~s 3:1/2 |"                                # the motif a fourth up
           "2:1/4 1:1/4 0:1/4 -1:1/4 0:1/2 1:1/2 4:2~s |"                   # run down, half close on E
           "4:1/2 3:1/2 0:1 1:1/2 2:1/4 1:1/4 0:1 |"
           "4:1/2 3:1/4 4:1/4 5:1/2 4:1/4 3:1/4 2:1 1:1 |"
           "1:1/2 0:1/4 1:1/4 2:1/2 1:1/4 0:1/4 1:2~s |"                   # the held second ...
           "0:3~m r:1", bar=4, name="theme_1")                             # ... resolves to A
    t2 = M("7:1/4 6:1/4 5:1/4 4:1/4 3:1/4 4:1/4 5:1/4 6:1/4 7:1 4:1 |"
           "8:1/2 7:1/2 4:1 5:3/2~s 4:1/2 |"                                # the motif at the fifth
           "6:1/4 5:1/4 4:1/4 3:1/4 2:1/4 3:1/4 4:1/4 5:1/4 6:1 3:1 |"     # the run sequenced down a step
           "7:1/2 6:1/2 3:1 4:2~s |"
           "2:1/2 3:1/4 4:1/4 5:1/2 6:1/4 7:1/4 8:3/2~s 7:1/2 |"           # the climb to B5
           "7:1/2 6:1/2 4:1 5:1/2 4:1/4 3:1/4 2:1 |"
           "1:1/2 0:1/2 -1:1/2 0:1/2 1:2~s |"
           "0:2~m r:2", bar=4, name="theme_2")
    fhi.play(t1, A.b(0), vel=86, art="legato", dyn="arch")
    fhi.play(t2, A.b(8), vel=92, art="legato", dyn="arch")
    fhi.curve(A.b(0), A.b(4), 104, 112)
    fhi.curve(A.b(4), A.b(8), 112, 100)
    fhi.curve(A.b(8), A.b(12, 2), 104, 122)
    fhi.curve(A.b(12, 2), A.b(16), 122, 98)
    ch_a = ["Am", "D", "G", "Em", "Am", "C", "G", "Am", "D", "Em", "C", "G", "D", "Am", "G", "Am"]
    for i, c in enumerate(ch_a):
        E.riff(lute, A.b(i), c, vel=80 if i < 8 else 84)
    flo.drone(A.b(0), A.b(16), [A2, E3], vel=70)
    flo.curve(A.b(0), A.b(16), 80, 92)
    E.jaw(jaw, p, A.bar0, 8, KS, grid="x.xxx.xxx.xxx.xx", vel=60, pitch="A2")      # (out under the runs, 19-26)
    _gallop(p, deep, hand, claps, A, 0, 16, vel=98, fills=(3, 7, 11, 15))
    gong.note(A.b(0), "A2", 1, vel=108)
    gong.note(A.b(8), "A2", 1, vel=96)
    for bar, beat in ((3, 2), (7, 0), (11, 2), (12, 0), (15, 0)):
        gsm.note(A.b(bar, beat), "E4" if bar % 2 else "A3", 1, vel=70)

    # ================================================================= B (27-46): call and response
    call1 = M("0:1/2 1:1/2 4:1 3:3/2~s 4:1/2 | 5:1/4 4:1/4 3:1/4 2:1/4 1:1/2 2:1/2 4:2~s", bar=4)   # inverted
    ans1 = M("4:1/2 3:1/2 0:1 1:3/2 0:1/2 | -1:1/4 0:1/4 1:1/4 2:1/4 1:1/2 0:1/2 0:2~gu", bar=4)   # upright
    fhi.play(call1, B.b(0), vel=78, art="legato", dyn="cresc")
    lead.play(ans1, B.b(2), vel=66)
    fhi.play(call1.transpose(2), B.b(4), vel=80, art="legato", dyn="cresc")
    lead.play(ans1.transpose(1), B.b(6), vel=68)
    # one-bar exchanges
    fhi.play(M("7:1/4 6:1/4 5:1/4 4:1/4 3:1/2 5:1/2 3:2~s"), B.b(8), vel=82, art="legato")
    lead.play(M("3:1/2 2:1/2 -1:1 0:3/2 -1:1/2"), B.b(9), vel=72)
    fhi.play(M("6:1/4 5:1/4 4:1/4 3:1/4 2:1/2 4:1/2 2:2~s"), B.b(10), vel=84, art="legato")
    lead.play(M("4:1/2 2:1/2 0:1 1:3/2 0:1/2"), B.b(11), vel=76)
    # half-bar exchanges: breathless
    for i, (f, l) in enumerate((("4:1/4 5:1/4 6:1/4 7:1/4 8:1", "4:1/2 3:1/2 1:1"),
                                ("7:1/4 6:1/4 5:1/4 4:1/4 5:1", "3:1/2 2:1/2 0:1"),
                                ("6:1/4 5:1/4 4:1/4 3:1/4 4:1", "2:1/2 1:1/2 -1:1"),
                                ("5:1/4 4:1/4 3:1/4 2:1/4 3:1", "3:1/2 1:1/2 0:1"))):
        fhi.play(M(f), B.b(12 + i), vel=96 + 2 * i, art="legato")
        lead.play(M(l), B.b(12 + i, 2), vel=96 + 2 * i)
    # together, in octaves, to the held E and the cut-off
    run = M("0:1/4 1:1/4 2:1/4 3:1/4 4:1/4 5:1/4 6:1/4 7:1/4 8:1/2 7:1/2 4:1 |"
            "6:1/4 5:1/4 4:1/4 3:1/4 2:1/4 3:1/4 4:1/4 5:1/4 6:1/2 5:1/2 3:1 |"
            "4:1/2 5:1/4 6:1/4 7:1/2 8:1/4 7:1/4 4:1 5:1 |"
            "4:2~s r:2", bar=4, name="unison_run")
    fhi.play(run, B.b(16), vel=100, art="legato", dyn="arch")
    fid.play(plain(run), B.b(16), octave=-1, vel=92, art="legato")
    lead.play(plain(run).fragment(0, 22), B.b(16), octave=-1, vel=92)
    fhi.curve(B.b(0), B.b(8), 72, 86)
    fhi.curve(B.b(8), B.b(12), 86, 100)
    lead.expr(B.b(0), 74)                                                          # the valley: the lute answers softly
    lead.curve(B.b(8), B.b(12), 74, 92)
    lead.expr(B.b(12), 100)
    fhi.curve(B.b(12), B.b(16), 108, 122)
    fhi.curve(B.b(16), B.b(18, 2), 122, 126)
    fhi.curve(B.b(18, 2), B.b(19, 2), 126, 96)
    fid.curve(B.b(16), B.b(19, 2), 104, 118)
    ch_b = ["C", "C", "Am", "Am", "G", "G", "Em", "Em", "D", "D", "C", "C", "Em", "D", "C", "D", "Am", "G", "Em"]
    for i, c in enumerate(ch_b):
        if i in (0, 1, 4, 5):                                                     # under the fiddle's calls only
            E.riff(lute, B.b(i), c, vel=66, density="sparse")
        elif i >= 12:
            E.riff(lute, B.b(i), c, vel=76 if i < 16 else 82, density="full")
    lute.chord(B.b(19), [52, 59, 64], 2.0, vel=86, strum=0.02)                 # the held E: lute rings, stops
    flo.drone(B.b(0), B.b(8), ["C3", "G3"], vel=64)
    flo.drone(B.b(8), B.b(12), ["D3", "A3"], vel=64)
    flo.drone(B.b(12), B.b(16), [A2, E3], vel=66)
    flo.drone(B.b(16), B.b(19, 2), ["E2", "B2"], vel=74)
    flo.curve(B.b(0), B.b(12), 62, 74)
    flo.curve(B.b(12), B.b(16), 74, 90)
    flo.curve(B.b(16), B.b(19, 2), 90, 110)
    E.jaw(jaw, p, B.bar0 + 14, 5, KS, grid="x.xxx.xxx.xxx.xx", vel=60, fade=(0.8, 1.15), pitch="A2")
    # the valley (27-38): one deep stroke a bar, the hand drum's ghost gallop, no stamps; then the climb back
    for k in range(12):
        b0 = B.b(k)
        deep.hit(b0, "dum", 80 if k < 8 else 86)
        if k >= 8:
            deep.hit(b0 + 2, "doum", 58 + 2 * (k - 8))
        hand.pattern(b0, 1, {"tek": "x.gg.ggx.g.gx.g." if k % 4 != 3 else "x.gg.ggx.g.gxrrr"}, vel=50 + k)
    _gallop(p, deep, hand, claps, B, 12, 4, vel=94, fills=(15,), light=True)
    _gallop(p, deep, hand, claps, B, 16, 3, vel=102, fills=(18,))
    deep.hit(B.b(19), "dum", 120)
    deep.hit(B.b(19, 2), "doum", 90)
    claps.hit(B.b(19), "stamp", 104)
    claps.hit(B.b(19), "clap", 100)
    gong.note(B.b(0), "A2", 1, vel=86)
    gong.note(B.b(12), "A2", 1, vel=92)
    gong.note(B.b(16), "A2", 1, vel=104)
    gong.note(B.b(19), "E2", 1, vel=110)
    for bar, beat in ((1, 2), (5, 2), (9, 0), (11, 0), (13, 0), (15, 0), (17, 2), (18, 2)):
        gsm.note(B.b(bar, beat), "E4" if bar % 4 == 1 else "A3", 1, vel=(58 if bar < 12 else 66) + bar)

    # ================================================================= BREAK (47-54): 7/8 against the gallop
    pat78 = {"deep": {"dum": "X...x...X.....", "tek": "..g...g...x.x."},
             "hand": {"tek": "X.xxX.xxX.xX.x"}}
    pat44 = {"deep": {"dum": "X.......X.......", "doum": "....x.......x...", "tek": "..g...g...g.xxxx"},
             "hand": {"tek": "X.xxX.xxX.xxXrrr"}}
    # bars 47-50: hand drum and stamps alone; 51-54: the deep drum, claps, jaw harp and small gongs join,
    # a crescendo into A'
    for i in range(8):
        b0 = brk.b(i)
        bl = p.bar_len(brk.bar0 + i)
        pt = pat78 if bl == 3.5 else pat44
        v = 84 + 4 * i
        if i >= 4:
            deep.pattern(b0, 1, pt["deep"], vel=v)
        hand.pattern(b0, 1, pt["hand"], vel=v * (0.92 if i < 4 else 0.8))
        groups = (0, 1, 2) if bl == 3.5 else (0, 1, 2, 3)
        for g in groups:
            claps.hit(b0 + g, "stamp", (92 if g == 0 else 76) * (0.9 if i < 4 else 1.0))
        if i >= 4:
            if bl == 3.5:
                claps.hit(b0 + 2.5, "clap", 92)
                claps.hit(b0 + 3.0, "clap", 82)
            else:
                claps.hit(b0 + 1, "clap", 90)
                claps.hit(b0 + 3, "clap", 98)
            gsm.note(b0 + (2.5 if bl == 3.5 else 3.0), "E4" if i % 2 else "A3", 1, vel=70 + 2 * i)
    for i in range(4, 8):
        E.jaw(jaw, p, brk.bar0 + i, 1, KS[i % 4:] + KS[:i % 4], vel=62 + 2 * i, pitch="A2",
              grid="X.xxx.xxX.xx.x" if p.bar_len(brk.bar0 + i) == 3.5 else "X.xxx.xxX.xxx.xx")
    flo.drone(brk.b(4), brk.end, [A2, E3], vel=66)
    flo.curve(brk.b(4), brk.end, 60, 96)
    wind.note(brk.b(0), 60, 14.0, vel=64, fc=900, fc_to=1600, whistle=0.35)
    gong.note(brk.b(4), "A2", 1, vel=104)
    deep.roll(brk.b(7, 2), 2.0, "tek", vel0=50, vel1=118, rate=0.125, accent_end=False)
    hand.roll(brk.b(7, 2), 2.0, "tek", vel0=40, vel1=100, rate=1 / 6.0, accent_end=False)

    # ================================================================= A' (55-72): full power
    fhi.play(t1, A2s.b(0), vel=94, art="legato", dyn="arch")
    fid.play(plain(t1), A2s.b(0), octave=-1, vel=86, art="legato")
    # second period (63-70): the lute takes the theme, the fiddle sings a new descant above it, the bass moves
    lead.play(plain(t2), A2s.b(8), octave=-1, vel=100, dyn="arch")
    desc = M("3:3 4:1 | 6:4~s | 5:2 4:2 | 4:2 7:2 | 8:4~s | 7:2 5:2 | 4:2 3:2 | 2:4", bar=4, name="descant")
    fhi.play(desc, A2s.b(8), vel=92, art="legato", dyn="arch")
    fin = M("0:1/4 1:1/4 2:1/4 3:1/4 4:1/4 5:1/4 6:1/4 7:1/4 8:1/2 7:1/2 6:1/2 5:1/2 |"
            "4:1/2 3:1/2 0:1 1:3/2~s 0:1/2", bar=4, name="arrival")
    fhi.play(fin, A2s.b(16), vel=102, art="legato")
    fid.play(plain(fin), A2s.b(16), octave=-1, vel=94, art="legato")
    fhi.curve(A2s.b(0), A2s.b(8), 108, 116)
    fhi.curve(A2s.b(8), A2s.b(9), 84, 104)
    fhi.curve(A2s.b(9), A2s.b(12, 2), 104, 124)
    fhi.curve(A2s.b(12, 2), A2s.b(16), 124, 104)
    fhi.curve(A2s.b(16), A2s.b(18), 116, 104)
    fid.curve(A2s.b(0), A2s.b(8), 104, 116)
    fid.curve(A2s.b(16), A2s.b(18), 112, 104)
    for i, c in enumerate(ch_a[:8]):
        E.riff(lute, A2s.b(i), c, vel=86)
    for i in (16, 17):
        E.riff(lute, A2s.b(i), "Am", vel=86)
    # the bass: the A drone, then the reharmonised second period in moving open fifths, then the drone again
    flo.drone(A2s.b(0), A2s.b(8), [A2, E3], vel=74)
    for i, (r, f5) in enumerate([("B2", "F#3"), ("G2", "D3"), ("E2", "B2"), ("A2", "E3"),
                                 ("G2", "D3"), ("D2", "A2"), ("E2", "B2"), ("A2", "E3")]):
        flo.chord(A2s.b(8 + i), [r, f5], 4.1, vel=78, art="tenuto")
    flo.drone(A2s.b(16), A2s.b(18), [A2, E3], vel=74)
    flo.curve(A2s.b(0), A2s.b(8), 96, 104)
    flo.curve(A2s.b(8), A2s.b(12), 96, 110)
    flo.curve(A2s.b(12), A2s.b(18), 110, 106)
    E.jaw(jaw, p, A2s.bar0, 8, KS, grid="x.xxx.xxx.xxx.xx", vel=66, pitch="A2")
    E.jaw(jaw, p, A2s.bar0 + 16, 2, KS, grid="x.xxx.xxx.xxx.xx", vel=68, pitch="A2")
    _gallop(p, deep, hand, claps, A2s, 0, 8, vel=106, fills=(3, 7), backbeat=True)
    for k in range(8, 12):                                                         # 63-66: half time
        b0 = A2s.b(k)
        deep.pattern(b0, 1, {"dum": "X.......X.......", "tek": "......g.......g." if k < 11 else
                             "......g.....gxgx"}, vel=100)
        hand.pattern(b0, 1, {"tek": "x.ggx.ggx.ggx.gg"}, vel=70)
        claps.hit(b0 + 1, "clap", 86)
        claps.hit(b0 + 3, "clap", 92)
    _gallop(p, deep, hand, claps, A2s, 12, 6, vel=106, fills=(15, 17), backbeat=True)
    # the burst of chant at the climax, on the moving roots (G D E A), its whistle on chord tones
    for bar, pc, beats, vw, ot in ((12, "G2", 4.3, ["a", "o"], [None, 12]), (13, "D2", 4.3, ["o", "a"], [8, 12]),
                                   (14, "E2", 4.3, ["a", "o"], [12, 8]), (15, "A2", 6.5, ["a", "o", "u"], [8, 12, None])):
        chant.note(A2s.b(bar), pc, beats, vel=94, vowels=vw, overtones=ot)
    chant.curve(A2s.b(12), A2s.b(13), 40, 118)
    chant.curve(A2s.b(13), A2s.b(15), 118, 108)
    chant.curve(A2s.b(15), A2s.b(16, 2), 108, 30)
    gong.note(A2s.b(0), "A2", 1, vel=116)
    gong.note(A2s.b(8), "B2", 1, vel=96)
    gong.note(A2s.b(12), "A2", 1, vel=120)
    gong.note(A2s.b(16), "A2", 1, vel=108)
    for bar in range(18):
        if bar % 2 == 1 or bar in (12, 13):
            gsm.note(A2s.b(bar, 2 if bar % 4 == 1 else 0), "E4" if bar % 4 == 3 else "A3", 1, vel=74)

    # ================================================================= OUTRO (73-82): slowing, resolving on A
    gong.note(out.b(0), "A2", 1, vel=110)
    ch_o = ["Am", "G", "Am", "D", "Am", "G", "Em", "Am"]
    for i, c in enumerate(ch_o):
        E.riff(lute, out.b(i), c, vel=80 - 3 * i, density="full" if i < 2 else ("eighths" if i < 6 else "sparse"))
    lute.chord(out.b(8), [45, 52, 57, 64], 8.0, vel=70, strum=0.05, art="ring")
    fhi.play(gong_ring().augment(2).ornament(0, "grace_up").ornament(3, "slide"), out.b(2), vel=84,
             art="legato", dyn="dim")
    fhi.note(out.b(6), "E5", 2.0, vel=66, art="legato", orn="mordent")
    fhi.note(out.b(6, 2), "A4", 9.0, vel=62, art="legato", orn="slide")
    fhi.curve(out.b(2), out.b(6), 108, 92)
    fhi.curve(out.b(6), out.b(9), 92, 50)
    fid.play(M("0:2 -1:2 | 0:4"), out.b(0), octave=-1, vel=80, art="legato")
    fid.play(M("0:4 | -3:4 | 0:8"), out.b(6), octave=-1, vel=66, art="legato")
    fid.curve(out.b(0), out.b(2), 104, 90)
    fid.curve(out.b(6), out.b(8), 80, 56)
    fid.curve(out.b(8), out.b(10), 56, 20)                                      # tapers into the gong's ring
    flo.drone(out.b(0), out.b(10), [A2, E3], vel=72)
    flo.curve(out.b(0), out.b(8), 100, 60)
    flo.curve(out.b(8), out.b(10), 60, 20)
    E.jaw(jaw, p, out.bar0, 2, KS, grid="x.xxx.xxx.xxx.xx", vel=60, fade=(1.0, 0.85), pitch="A2")
    E.jaw(jaw, p, out.bar0 + 2, 3, KS, grid="x.x.x.x.x.x.x.x.", vel=52, fade=(0.9, 0.7), pitch="A2")
    E.jaw(jaw, p, out.bar0 + 5, 2, KS, grid="x...x...x...x...", vel=46, fade=(0.8, 0.6), pitch="A2")
    _gallop(p, deep, hand, claps, out, 0, 2, vel=96)
    deep.pattern(out.b(2), 4, {"dum": "X.......x.......", "doum": "....o.......o..."}, vel=84)
    hand.pattern(out.b(2), 4, {"tek": "x.g.x.g.x.g.x.g.|x...x...x...x..."}, vel=56)
    deep.pattern(out.b(6), 2, {"dum": "x.......o......."}, vel=70)
    deep.hit(out.b(8), "doum", 76)
    wind.note(out.b(4), 60, 16.0, vel=74, fc=600, fc_to=1100, whistle=0.4)
    gsm.note(out.b(5, 0), "E4", 1, vel=58)
    gong.note(out.b(8), "A2", 1, vel=96, decay=12.0)                            # rings out as the tail
    return p


def _gallop(p, deep, hand, claps, sec, bar0, bars, vel=96, fills=(), light=False, backbeat=False):
    """The running gallop: deep drum on 1 and 3 (doum on 2 and 4), the hand drum's da-dada on every beat,
    stamps on 1 and 3 (+ claps on 2 and 4 with backbeat); a fill in the listed bars."""
    for k in range(bars):
        bar = bar0 + k
        b0 = sec.b(bar)
        fill = bar in fills
        deep.pattern(b0, 1, {"dum": "X.......X.......", "doum": "....o.......o...",
                             "tek": "..g...g...gxgxgx" if fill else "..g...g...g...g."}, vel=vel)
        hand.pattern(b0, 1, {"tek": ("X.ooX.ooX.ooXrrr" if fill else "X.oox.ooX.oox.oo") if not light
                             else ("x.ggx.ggx.ggx.gg" if not fill else "x.ggx.ggx.ggXrrr")}, vel=vel * 0.74)
        claps.hit(b0, "stamp", vel * 0.84)
        claps.hit(b0 + 2, "stamp", vel * 0.74)
        if backbeat:
            claps.hit(b0 + 1, "clap", vel * 0.84)
            claps.hit(b0 + 3, "clap", vel * 0.9)
            if fill:
                claps.hit(b0 + 3.5, "clap", vel * 0.7)
                claps.hit(b0 + 3.75, "clap", vel * 0.78)


if __name__ == "__main__":
    print(build().compile().summary())
