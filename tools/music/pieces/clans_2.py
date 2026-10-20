#!/usr/bin/env python3
"""Clans 2, "The Gong-Ring Gathers" (in-game rotation, about 3:37). E Mixolydian, 84 BPM, 6/4 felt as three slow
half-note beats: the big frame drum strikes every second beat (1, 3, 5), a processional sway, not a gallop.
Dignified, warm and faintly humorous: the households arrive at the council one by one.

Form (49 bars of 6/4). Intro 1-5: the ring of gongs is bowed one by one around the stereo field (big E, mid B,
small E), the overtone drone enters, the big drum starts its slow heartbeat. Horns 6-8: two bronze horns call and
answer from opposite sides of the valley (rising fifth, falling fifth, then the motif's own held F# resolving to E).
A 9-20: the two-string fiddle in its tenor register sings the Gong-Ring augmented to half notes (B-A-E, held F#
resolving to E); the antecedent answers it with its own inversion, quarter-quarter-long, climbing to the flat
seventh D and falling to an open half close on B over A (9-12); the consequent leaps up and sequences the motif
DOWN a step, so it lands on the flat seventh (A-G#-D, E over D), then climbs B-D-F# and cadences to E: the
Mixolydian D-to-E close (13-16); the b-phrase 17-20 climbs through the flat seventh to a held A and stops on B, the high
fiddle shadowing it softly an octave up. B 21-28: the motif in quarter notes, danced, and sequenced down a step
(21-24), call and response with the horns (25-26); the claps build
from one shy clap per bar to every off-beat, then a hemiola (two claps against the drum's three, bar 27), and one
late clap after everyone has stopped (bar 28). Bridge 29-32: drone only; the chant whistles the motif in pure
harmonics (12-8-9-8 = B, E, F#, E); a one-beat general pause. A' 33-44: the full ring: theme in the tenor, a
slow descant above it on the high fiddle (a, then the b-phrase climax on A5 in bar 40, then a'), horns and chant
swelling, claps on every off-beat. Close 45-49: the motif augmented once more, the held F# over D resolves to the
open E chord; everyone stops together but the hum, a short breath while the hall still rings, and then one last
gong, softer than the close. Mix: the tenor fiddle carries a 3.2 kHz bow edge (outside the 2.3 kHz unit-voice dip),
the low end is kept clear (drone fifth out in A, the drone and the big drum thinned below 70-90 Hz).
Render: python3 tools/music/render.py tools/music/pieces/clans_2.py --out assets/audio/music/clans_2.ogg --length-check
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext_clans as E  # noqa: E402
import palette as P  # noqa: E402
from ext_clans import M, plain  # noqa: E402
from score import Piece, n  # noqa: E402

E2, B2, E3 = "E2", "B2", "E3"


def build():
    p = Piece("clans_2", seed=202, bpm=84, meter=(6, 4), key="E", mode="mixolydian")
    p.mix = {k: dict(v) for k, v in P.MIX_CLANS.items()}
    p.mix["master"]["lowshelf"] = (160, -3.0)                   # a tenor melody over a drone: keep the low end clear
    p.mix["master"]["presence"] = (4500, 5.0, 0.8)              # ... and give the bowed rasp and the claps their air
    p.mix["master"]["highshelf"] = (8000, 2.5)
    p.kind, p.tail_s, p.length_range = "track", 10.0, (205.0, 222.0)

    gong = p.track("gong", P.GONG)
    gmid = p.track("gong_mid", P.GONG.variant(name="gong_mid", pan=-0.38, gain_db=-7.0, trim_db=2.4,
                                               synth_params={"decay": 7.0, "bloom": 0.5, "bright": 0.6,
                                                             "identity": 3}, color=(230, 170, 50)))
    gsm = p.track("gong_small", P.GONG_SMALL.variant(pan=0.42))
    gend = p.track("gong_end", P.GONG.variant(name="gong_end", gain_db=-17.0))   # the last stroke, under the close
    chant = p.track("chant", P.CHANT.variant(gain_db=-8.0))
    # the noble tenor melody: thinned below 250 Hz (its fundamentals sit on the drone), a nasal bowed body at
    # 1.3 kHz and the horsehair rasp at 3.2 kHz (more drive), outside the 2.3 kHz room left for unit voices
    fid = p.track("two_string", P.TWO_STRING.variant(pan=0.08, gain_db=-1.5, drive=0.48, eq=[
        ("hp", 150), ("lowshelf", 260, -5.0), ("peak", 1300, 3.0, 1.0), ("peak", 2300, -2.5, 1.4),
        ("peak", 3200, 3.0, 1.0), ("peak", 4200, 3.0, 1.0)]))
    fhi = p.track("two_string_high", P.TWO_STRING_HI.variant(pan=0.22, gain_db=-4.0))   # descant
    flo = p.track("two_string_low", E.TWO_STRING_LOW.variant(gain_db=-13.5, eq=[            # drone / bass
        ("hp", 70), ("peak", 1300, 0.5, 1.2), ("peak", 2600, -3.0, 1.0), ("highshelf", 5000, -4.0)]))
    hrn1 = p.track("horn_left", P.BRONZE_HORNS.variant(pan=-0.62, reverb=0.7))
    hrn2 = p.track("horn_right", P.BRONZE_HORNS.variant(pan=0.62, reverb=0.9, gain_db=-9.5,
                                                         eq=[("hp", 50), ("lp", 1700), ("lowshelf", 150, 1.0)],
                                                         color=(220, 160, 90)))
    drum = p.track("big_drum", P.DEEP_DRUM.variant(name="big_frame_drum", gain_db=-4.5,
                                                   eq=[("hp", 32), ("lowshelf", 90, -3.0), ("lp", 6000)],
                                                   drum_map={"dum": 40, "doum": 35, "tek": 40, "slap": 40,
                                                             "mute": 40},
                                                   synth_params={"size": 1.0, "skin": 0.9, "ring": 1.1}))
    hand = p.track("hand_drum", P.HAND_DRUM.variant(eq=[("hp", 60), ("highshelf", 4000, 3.0)]))   # crisp rim
    claps = p.track("claps", P.CLAPS.variant(eq=[("hp", 60), ("peak", 2200, -2.0, 1.0), ("highshelf", 5000, 2.0)]))
    jaw = p.track("jaw_harp", P.JAW_HARP.variant(synth_params=dict(P.JAW_HARP.synth_params, fundamental=52),
                                                  gain_db=-11.0, pan=-0.2))

    intro = p.section("intro", 5)
    horns = p.section("horn calls", 3)
    A = p.section("A", 12)
    B = p.section("B", 8)
    br = p.section("bridge", 4)
    A2 = p.section("A'", 12)
    cl = p.section("close", 5)
    p.set_end(cl.b(4, 1.0))

    for s, bar in ((A, 4), (A, 8), (A2, 4), (A2, 8)):
        p.breathe(s.b(bar), beats=1.5, depth=0.04)
    p.breathe(B.b(0), beats=2.0, depth=0.05)
    p.breathe(br.b(4), beats=2.0, depth=0.06)
    p.rit(cl.b(1, 3), cl.b(3, 4.5), to=0.74)
    p.fermata(cl.b(3, 5.0), 1.0, stretch=0.55)              # a short breath: the hall still rings when the gong comes

    # ================================================================= INTRO (bars 1-5): the ring of gongs
    gong.note(intro.b(0), E2, 9.0, vel=70, stroke="bowed")
    gmid.note(intro.b(1, 2), B2, 8.0, vel=66, stroke="bowed")
    gsm.note(intro.b(2, 4), "E4", 6.0, vel=60, stroke="bowed")
    gong.note(intro.b(3, 3), E2, 9.0, vel=62, stroke="bowed")
    gsm.note(intro.b(4, 4), "B3", 1, vel=54)
    chant.note(intro.b(1), E2, 41.5, vel=74, vowels=["u", "o", "u", "o", "a", "o", "u"],
               overtones=[None, 8, None, 12, 8, 6, None])
    chant.curve(intro.b(1), intro.b(3), 35, 86)
    chant.curve(intro.b(3), horns.b(3), 86, 70)
    flo.drone(intro.b(2), A.b(0, 3), [E2, B2], vel=70)
    flo.curve(intro.b(2), intro.b(5), 25, 80)
    for bar in range(3, 5):
        for beat, v in ((0, 52), (2, 40), (4, 46)):
            drum.hit(intro.b(bar, beat), "doum" if beat == 0 else "dum", v + 8 * (bar - 3))

    # ================================================================= HORN CALLS (bars 6-8): across the valley
    hrn1.notes_seq(horns.b(0), ["E2", "B2"], [2.0, 4.0], vel=76, art="legato")
    hrn1.swell(horns.b(0), horns.b(1), 40, 108, peak=0.55)
    hrn2.notes_seq(horns.b(1), ["B2", "E2"], [2.0, 4.5], vel=72, art="legato")
    hrn2.swell(horns.b(1), horns.b(2), 38, 104, peak=0.5)
    hrn1.note(horns.b(2), "F#2", 3.5, vel=78, art="legato", orn="slide")
    hrn1.note(horns.b(2, 3.5), "E2", 4.0, vel=72, art="legato")
    hrn1.swell(horns.b(2), horns.b(3, 1.5), 40, 110, peak=0.45)
    hrn2.note(horns.b(2, 4), "F#2", 2.0, vel=62, art="legato")
    hrn2.note(horns.b(3), "E2", 4.0, vel=58, art="legato")
    hrn2.swell(horns.b(2, 4), horns.b(3, 4), 30, 86, peak=0.4)
    for bar in range(3):
        for beat, v in ((0, 70), (2, 52), (4, 58)):
            drum.hit(horns.b(bar, beat), "doum" if beat == 0 else "dum", v + 4 * bar)
    gong.note(horns.b(0), E2, 1, vel=92)
    gmid.note(horns.b(2), B2, 1, vel=70)

    # ================================================================= A (bars 9-20): the noble melody
    # a: the Gong-Ring, answered by its inversion climbing to the flat seventh D, down to a half close on B
    # a': an octave up, the motif sequenced down a step (it lands on D), then B-D-F# and the cadence on E
    a1 = M("4:2 3:2 0:2 | 1:4~s 0:2 | 2:1 3:1 6:4~s | 5:2~m 3:1 4:3", bar=6, name="a")
    a2 = M("10:2~gu 9:2 6:2 | 7:4~s 6:2 | 4:2 6:1 8:3~s | 7:6~lm", bar=6, name="a'")
    bb = M("7:3 8:1 9:2 | 10:4~s 9:2 | 8:2 7:1 6:1~m 7:2 | 4:4~s r:2", bar=6, name="b")
    fid.play(a1, A.b(0), octave=-1, vel=82, art="legato", dyn="arch")
    fid.play(a2, A.b(4), octave=-1, vel=84, art="legato", dyn="arch")
    fid.play(bb, A.b(8), octave=-1, vel=88, art="legato", dyn="arch")
    fid.curve(A.b(0), A.b(0, 3), 70, 100)
    fid.swell(A.b(0, 3), A.b(4), 96, 112, peak=0.6)
    fid.swell(A.b(4), A.b(8), 98, 114, peak=0.55)
    fid.swell(A.b(8), A.b(12), 100, 122, peak=0.45)
    fhi.play(plain(bb), A.b(8), vel=58, art="legato", dyn="arch")                 # the b-phrase shadowed above
    fhi.curve(A.b(8), A.b(9), 36, 70)
    fhi.curve(A.b(9), A.b(11), 70, 84)
    fhi.curve(A.b(11), A.b(12), 84, 40)
    # harmony per half bar (3 beats): E E | E E | E D | A A || E E | A D | E D | E E || E E | A E | D E | A A
    har_a = ["E", "E", "E", "E", "E", "D", "A", "A", "E", "E", "A", "D", "E", "D", "E", "E",
             "E", "E", "A", "E", "D", "E", "A", "A"]
    _bass(flo, A, har_a, vel=74, fifth_on_e=False)
    flo.curve(A.b(0), A.b(12), 84, 96)
    for bar in range(12):
        _drum_bar(drum, A.b(bar), 84 + (6 if bar >= 8 else 0))
    gong.note(A.b(0), E2, 1, vel=104)
    gmid.note(A.b(4), B2, 1, vel=84)
    gong.note(A.b(8), E2, 1, vel=96)
    gsm.note(A.b(3, 3), "B3", 1, vel=62)
    gsm.note(A.b(7, 0), "E4", 1, vel=58)
    gsm.note(A.b(11, 0), "B3", 1, vel=66)
    hrn1.notes_seq(A.b(3), ["A2", "E2"], [3.0, 3.5], vel=70, art="legato")
    hrn1.swell(A.b(3), A.b(4, 0.5), 36, 96, peak=0.5)
    hrn2.notes_seq(A.b(7), ["B2", "E2"], [3.0, 4.0], vel=66, art="legato")
    hrn2.swell(A.b(7), A.b(8, 1), 34, 92, peak=0.5)
    hrn1.notes_seq(A.b(9), ["A2"], [6.0], vel=72, art="legato")
    hrn2.notes_seq(A.b(10, 3), ["E2"], [9.0], vel=68, art="legato")
    hrn1.swell(A.b(9), A.b(10), 36, 100, peak=0.6)
    hrn2.swell(A.b(10, 3), A.b(12), 34, 98, peak=0.5)
    chant.note(A.b(0), E2, 72.5, vel=70, vowels=["o", "u", "o", "a", "o", "u"], overtones=[None, None, 8, 12, 9, 8])
    chant.curve(A.b(0), A.b(1), 60, 64)
    chant.curve(A.b(8), A.b(11), 64, 92)
    chant.curve(A.b(11), A.b(12), 92, 60)

    # ================================================================= B (bars 21-28): claps and drums build
    fb = M("4:1~gu 3:1 0:1 1:2~s 0:1 | 3:1~gu 2:1 -1:1 0:2~s -1:1 | 3:1 5:1 7:1 6:1 5:1 3:1 | 4:2 2:1 1:1~m 0:2 |"
           "7:1~gu 8:1 9:1 8:2~s 7:1 | r:6 | 10:1~gu 9:1 7:1 8:2~s 7:1 | 4:5~s r:1", bar=6, name="danced")
    fid.play(fb, B.b(0), octave=-1, vel=86, art="legato", dyn="cresc")
    fid.curve(B.b(0), B.b(4), 96, 110)
    fid.curve(B.b(4), B.b(7), 110, 122)
    fid.curve(B.b(7), B.b(8), 122, 90)
    fhi.play(plain(fb.fragment(20, 25)), B.b(4), vel=62, art="legato")             # doubles bar 25, an octave up
    fhi.play(plain(fb.fragment(26, None)), B.b(6), vel=66, art="legato")           # and bars 27-28
    fhi.curve(B.b(4), B.b(8), 70, 104)
    # the horns answer the fiddle in bar 26 (a sly slide into each note)
    hrn1.note(B.b(5), "D3", 2.0, vel=78, art="legato", orn="slide")
    hrn1.note(B.b(5, 2), "A2", 4.0, vel=74, art="legato")
    hrn2.note(B.b(5, 2), "A2", 2.0, vel=70, art="legato", orn="slide")
    hrn2.note(B.b(5, 4), "D2", 4.0, vel=66, art="legato")
    hrn1.swell(B.b(5), B.b(6), 40, 112, peak=0.4)
    hrn2.swell(B.b(5, 2), B.b(6, 2), 36, 100, peak=0.4)
    hrn1.notes_seq(B.b(7), ["B2"], [6.0], vel=76, art="legato")
    hrn2.notes_seq(B.b(7), ["E2"], [6.0], vel=72, art="legato")
    hrn1.swell(B.b(7), B.b(8), 40, 110, peak=0.7)
    hrn2.swell(B.b(7), B.b(8), 40, 104, peak=0.7)
    har_b = ["E", "E", "D", "D", "A", "A", "E", "E", "E", "E", "D", "D", "A", "A", "E", "E"]
    _bass(flo, B, har_b, vel=80)
    flo.curve(B.b(0), B.b(8), 92, 108)
    for bar in range(8):
        _drum_bar(drum, B.b(bar), 92 + 2 * bar, busy=bar >= 4)
    # hand drum: ruffs into the drum strokes, then off-beat teks
    for bar in range(2, 8):
        for beat in (2, 4) if bar < 4 else (0, 2, 4):
            hand.roll(B.b(bar, beat) - 1 / 3.0, 1 / 3.0, "tek", vel0=34, vel1=58 + 3 * bar, rate=1 / 9.0,
                      accent_end=False)
        if bar >= 4:
            for beat in (1, 3, 5):
                hand.hit(B.b(bar, beat), "tek", 56 + 2 * bar)
                hand.hit(B.b(bar, beat + 0.5), "tek", 30)
    # claps: one shy clap, then every off-beat, then the hemiola, then one too many
    claps.hit(B.b(0, 5), "clap", 62, hands=2)
    claps.hit(B.b(1, 5), "clap", 68, hands=3)
    for bar in (2, 3):
        for beat in (1, 3, 5):
            claps.hit(B.b(bar, beat), "clap", 74 + 4 * (bar - 2), hands=4)
    for bar in (4, 5):
        for beat in (1, 3, 5):
            claps.hit(B.b(bar, beat), "clap", 86 + 4 * (bar - 4))
        for beat in (0, 2, 4):
            claps.hit(B.b(bar, beat), "stamp", 76)
    for beat, v in ((0, 104), (3, 108)):                                           # bar 27: two against three
        claps.hit(B.b(6, beat), "clap", v)
        claps.hit(B.b(6, beat), "stamp", 92)
    for beat in (1, 3):
        claps.hit(B.b(7, beat), "clap", 98)
        claps.hit(B.b(7, beat - 1), "stamp", 84)
    claps.hit(B.b(7, 5.5), "clap", 70, hands=1)                                    # one late clap
    gong.note(B.b(0), E2, 1, vel=98)
    gmid.note(B.b(4), B2, 1, vel=92)
    gsm.note(B.b(2, 0), "E4", 1, vel=66)
    gsm.note(B.b(6, 0), "E4", 1, vel=78)
    gsm.note(B.b(6, 3), "B3", 1, vel=74)
    gong.note(B.b(7), E2, 1, vel=106)
    jaw.note(B.b(1, 5), "E3", 0.5, vel=70, k=4)
    jaw.note(B.b(1, 5.5), "E3", 0.5, vel=60, k=6, k_from=4, glide=0.15)
    jaw.note(B.b(3, 5), "E3", 0.5, vel=74, k=6)
    jaw.note(B.b(3, 5.5), "E3", 0.5, vel=64, k=4, k_from=7, glide=0.2)
    jaw.note(B.b(7, 4.5), "E3", 0.75, vel=66, k=8, k_from=4, glide=0.3)
    chant.note(B.b(4), E2, 24.5, vel=78, vowels=["o", "a", "o", "a"], overtones=[None, 8, 9, 12])
    chant.curve(B.b(4), B.b(5), 40, 86)
    chant.curve(B.b(5), B.b(7, 4), 86, 112)
    chant.curve(B.b(7, 4), B.b(8), 112, 60)

    # ================================================================= BRIDGE (bars 29-32): the drone whistles the motif
    chant.note(br.b(0), E2, 24.4, vel=80, vowels=["u", "o", "o", "o", "u", "u", "m"],
               overtones=[None, 12, 8, 9, 8, None, None])
    chant.curve(br.b(0), br.b(1), 50, 88)
    chant.curve(br.b(1), br.b(3), 88, 96)
    chant.curve(br.b(3), br.b(3, 4), 96, 58)
    chant.curve(br.b(3, 4), br.b(4, 0.4), 58, 46)                               # held softly through the pause
    gong.note(br.b(0, 1), E2, 9.0, vel=62, stroke="bowed")
    gmid.note(br.b(2), B2, 8.0, vel=56, stroke="bowed")
    flo.drone(br.b(0), br.b(4, 0.25), [E2, B2], vel=66)
    flo.curve(br.b(0), br.b(2), 80, 62)
    flo.curve(br.b(2), br.b(3, 4), 62, 48)
    flo.curve(br.b(3, 4), br.b(4, 0.25), 48, 40)
    for bar in range(4):
        drum.hit(br.b(bar), "doum", 50 - 4 * bar)
    hrn2.notes_seq(br.b(1, 2), ["B2", "E2"], [2.0, 4.0], vel=58, art="legato")      # an echo from far away
    hrn2.swell(br.b(1, 2), br.b(2, 2), 30, 80, peak=0.5)
    gsm.note(br.b(3, 5.5), "E4", 1, vel=52)                                         # the general pause, then: tink

    # ================================================================= A' (bars 33-44): the full ring
    fid.play(a1, A2.b(0), octave=-1, vel=88, art="legato", dyn="arch")
    fid.play(bb, A2.b(4), octave=-1, vel=94, art="legato", dyn="arch")
    fid.play(a2, A2.b(8), octave=-1, vel=90, art="legato", dyn="arch")
    fid.swell(A2.b(0), A2.b(4), 102, 116, peak=0.55)
    fid.swell(A2.b(4), A2.b(8), 104, 124, peak=0.4)
    fid.curve(A2.b(8), A2.b(12), 116, 100)
    desc = M("4:6 | 3:4 2:2 | 2:2 1:4 | 0:6 |"                        # over a: E | E | E D | A
             "7:6 | 8:3 7:3 | 8:4 9:2 | 10:6~s |"                     # over b: E | A E | D E | A  (climax on A5)
             "9:6 | 7:6 | 4:3 3:3 | 2:6", bar=6, name="descant")      # over a': E | A D | E D | E
    fhi.play(desc, A2.b(0), vel=78, art="legato", dyn=None)
    fhi.curve(A2.b(0), A2.b(1), 50, 96)
    fhi.curve(A2.b(1), A2.b(7), 96, 124)
    fhi.curve(A2.b(7), A2.b(8), 124, 104)
    fhi.curve(A2.b(8), A2.b(12), 104, 92)
    har_a2 = ["E", "E", "E", "E", "E", "D", "A", "A", "E", "E", "A", "E", "D", "E", "A", "A",
              "E", "E", "A", "D", "E", "D", "E", "E"]
    _bass(flo, A2, har_a2, vel=84)
    flo.curve(A2.b(0), A2.b(8), 96, 110)
    flo.curve(A2.b(8), A2.b(12), 110, 100)
    for bar in range(12):
        _drum_bar(drum, A2.b(bar), 100 if bar < 8 else 94, busy=True)
        for beat in (1, 3, 5):
            claps.hit(A2.b(bar, beat), "clap", 92 if 4 <= bar < 8 else 84)
        for beat in (0, 2, 4):
            claps.hit(A2.b(bar, beat), "stamp", 80 if beat == 0 else 66)
        if bar % 4 == 3:
            claps.hit(A2.b(bar, 5.5), "slap", 64)
        for beat in (2, 4):
            hand.roll(A2.b(bar, beat) - 1 / 3.0, 1 / 3.0, "tek", vel0=34, vel1=62, rate=1 / 9.0, accent_end=False)
        for beat in (1, 3, 5):
            hand.hit(A2.b(bar, beat), "tek", 60)
    gong.note(A2.b(0), E2, 1, vel=104)
    gmid.note(A2.b(4), B2, 1, vel=96)
    gong.note(A2.b(6), E2, 1, vel=100)
    gong.note(A2.b(8), E2, 1, vel=104)
    for bar, beat in ((1, 3), (3, 0), (5, 3), (7, 0), (9, 3), (11, 0)):
        gsm.note(A2.b(bar, beat), "E4" if bar % 4 == 3 else "B3", 1, vel=70)
    for h, bar, ps, ds in ((hrn1, 0, ["E2", "B2"], [3, 9]), (hrn2, 2, ["B2", "A2"], [3, 9]),
                           (hrn1, 4, ["B2", "E3"], [3, 9]), (hrn2, 6, ["A2", "E2"], [3, 9]),
                           (hrn1, 8, ["E2", "A2"], [3, 9]), (hrn2, 10, ["A2", "E2"], [3, 9])):
        h.notes_seq(A2.b(bar), ps, ds, vel=78, art="legato")
        h.swell(A2.b(bar), A2.b(bar + 2), 40, 114 if 4 <= bar < 8 else 104, peak=0.45)
    chant.note(A2.b(0), E2, 48.5, vel=80, vowels=["o", "a", "o", "a"], overtones=[None, 8, 12, 10])
    chant.note(A2.b(8), E2, 24.5, vel=80, vowels=["o", "a", "o"], overtones=[None, 9, 12])
    chant.curve(A2.b(0), A2.b(1), 50, 86)
    chant.curve(A2.b(1), A2.b(7), 86, 122)
    chant.curve(A2.b(7), A2.b(12), 122, 88)

    # ================================================================= CLOSE (bars 45-49): one last gong
    fid.play(M("4:3 3:3 | 0:6 | 1:6~s | 0:5~lm"), cl.b(0), octave=-1, vel=86, art="legato", dyn="dim")
    fid.curve(cl.b(0), cl.b(2), 104, 112)
    fid.curve(cl.b(2), cl.b(3, 3.5), 112, 92)
    fid.curve(cl.b(3, 3.5), cl.b(3, 5), 92, 70)
    fhi.play(M("7:6 | 6:6 | 5:6~s | 2:5"), cl.b(0), vel=72, art="legato")         # E | D | C# | G# (the major third)
    fhi.curve(cl.b(0), cl.b(3, 3.5), 96, 80)
    fhi.curve(cl.b(3, 3.5), cl.b(3, 5), 80, 62)
    for i, (r, top) in enumerate((("E2", "B2"), ("D2", "A2"), ("D2", "A2"))):
        flo.chord(cl.b(i), [n(r), n(top)], 6.05, vel=82, art="tenuto")
    flo.chord(cl.b(3), ["E2", "B2", "E3"], 5.0, vel=84, art="exact")
    flo.curve(cl.b(0), cl.b(3), 104, 96)
    flo.curve(cl.b(3, 3.0), cl.b(3, 5), 96, 72)
    hrn1.notes_seq(cl.b(0), ["B2", "A2"], [6.0, 6.0], vel=74, art="legato")
    hrn1.notes_seq(cl.b(2), ["F#2"], [6.0], vel=76, art="legato")
    hrn1.notes_seq(cl.b(3), ["E2"], [5.0], vel=76, art="legato")
    hrn2.notes_seq(cl.b(1), ["D2"], [12.0], vel=70, art="legato")
    hrn2.notes_seq(cl.b(3), ["B2"], [5.0], vel=72, art="legato")
    hrn1.curve(cl.b(0), cl.b(3), 100, 106)
    hrn1.curve(cl.b(3), cl.b(3, 5), 106, 84)
    hrn2.curve(cl.b(1), cl.b(3), 70, 100)
    hrn2.curve(cl.b(3), cl.b(3, 5), 100, 82)
    for bar in range(3):
        _drum_bar(drum, cl.b(bar), 88 - 8 * bar)
        for beat in (1, 3, 5):
            claps.hit(cl.b(bar, beat), "clap", 78 - 12 * bar, hands=6 - 2 * bar)
    drum.hit(cl.b(3), "doum", 84)
    chant.note(cl.b(0), E2, 18.0, vel=76, vowels=["a", "o", "u"], overtones=[12, 9, 8])
    chant.note(cl.b(3), E2, 9.0, vel=70, vowel="m")                                # the hum carries the breath
    chant.curve(cl.b(0), cl.b(3), 92, 80)
    chant.curve(cl.b(3), cl.b(3, 5), 80, 62)
    chant.curve(cl.b(3, 5), cl.b(4, 3), 62, 30)
    gong.note(cl.b(0), E2, 1, vel=100)
    gmid.note(cl.b(2), "D3", 9.0, vel=58, stroke="bowed")
    gsm.note(cl.b(3), "E4", 1, vel=64)
    gend.note(cl.b(4), E2, 1, vel=96, decay=16.0)                                   # one last gong, softer
    gmid.note(cl.b(4, 0.02), B2, 1, vel=44, decay=12.0)
    drum.hit(cl.b(4), "doum", 44)
    return p


def _bass(flo, sec, chords, vel=76, fifth_on_e=True):
    """The low two-string under the harmony: E2 drone with the fifth; on D and A the bass moves (open fifths).
    fifth_on_e=False leaves the E chord on the bare E2 (a lighter low end under the tenor)."""
    roots = {"E": ("E2", "B2"), "D": ("D2", "A2"), "A": ("A2", "E3")}
    i = 0
    while i < len(chords):
        j = i
        while j + 1 < len(chords) and chords[j + 1] == chords[i]:
            j += 1
        r, t = roots[chords[i]]
        ps = [n(r)] if chords[i] == "E" and not fifth_on_e else [n(r), n(t)]
        flo.chord(sec.start + 3 * i, ps, 3 * (j - i + 1) + 0.08, vel=vel, art="tenuto")
        i = j + 1


def _drum_bar(drum, b0, vel, busy=False):
    """The big frame drum on every second beat (1, 3, 5); busy adds a soft pickup before 3 and 5."""
    drum.hit(b0, "doum", vel)
    drum.hit(b0 + 2, "dum", vel * 0.8)
    drum.hit(b0 + 4, "dum", vel * 0.86)
    if busy:
        drum.hit(b0 + 1.5, "tek", vel * 0.42)
        drum.hit(b0 + 3.5, "tek", vel * 0.45)
        drum.hit(b0 + 5.5, "tek", vel * 0.5)


if __name__ == "__main__":
    print(build().compile().summary())
