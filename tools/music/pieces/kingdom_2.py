#!/usr/bin/env python3
"""Kingdom 2, "Boards and Thunder" (assets/audio/music/kingdom_2.ogg). G Dorian, 100 BPM, 4/4, about 3:30.

Composer's note. Form (bars, 1-based): intro 1-6 | A 7-30 (three 8-bar periods) | B 31-46 | drum bridge 47-54 |
A' 55-78 | final cadence 79-84. The metre feel is 3+3+2 throughout: two field snares interlock in that grouping
and the deep frame drum and the pizzicato bass mark it, so the bar drives forward instead of marching. The Wheel
is re-cut to the same grouping (G-A-Bb, C dotted, D: bar 7) and answered by the falling fourth C-G; bars 9-10
sequence it a third up onto the Dorian E natural and stop on a half cadence on D, bars 11-14 close on G. The second
period adds fiddle double-stops and a viola counter-line; the third inverts the Wheel and sequences it down
(D, C, Bb, A) to a horn signal. In B (on Bb) the bagpipe rests: two far horns give two-note signals and the
dulcimer answers each with a Wheel fragment in tremolo; the fiddle returns on held double-stops. The bridge is
drums only (two snares, frame drum, timpani on G and D, distant cannon booms) with the accents displaced by a
sixteenth every bar and a long crescendo. A' brings everything back, ends its last period with the Wheel in
stretto between fiddle and viola (the viola a fourth below, two beats behind), and the cadence plays the Wheel and its answer in augmentation onto a firm G
(F to G, with the last boom). Arc: soft intro, A building, B lighter, bridge from pp to ff, A' strongest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import bass_of, chord, dulcimer_bar, mel  # noqa: E402
from score import Mode, Piece, wheel  # noqa: E402

HARMONY = {
    # A (7-30)
    7: "Gm", 8: "C", 9: "Bb", 10: "F Dm", 11: "Gm", 12: "F C", 13: "F", 14: "C:1.5 Gm:2.5",
    15: "Gm", 16: "C", 17: "Bb", 18: "F Dm", 19: "Gm", 20: "F C", 21: "F", 22: "C:1.5 Gm:2.5",
    23: "Gm", 24: "F", 25: "C", 26: "Dm", 27: "Gm", 28: "F", 29: "C", 30: "Dm",
    # B (31-46) on Bb
    31: "Bb", 32: "Bb", 33: "F", 34: "F", 35: "Gm", 36: "Gm", 37: "Dm", 38: "Dm",
    39: "Bb", 40: "Bb", 41: "F", 42: "F", 43: "Gm", 44: "C", 45: "Dm", 46: "Dm",
    # A' (55-78)
    55: "Gm", 56: "C", 57: "Bb", 58: "F Dm", 59: "Gm", 60: "F C", 61: "F", 62: "C:1.5 Gm:2.5",
    63: "Gm", 64: "C", 65: "Bb", 66: "F Dm", 67: "Gm", 68: "F C", 69: "F", 70: "C:1.5 Gm:2.5",
    71: "Gm", 72: "F", 73: "C", 74: "Dm", 75: "Gm", 76: "Bb", 77: "C", 78: "Dm",
    79: "Gm", 80: "C", 81: "F:2 G5:2", 82: "G5", 83: "G5", 84: "G5",
}


def segs(bar):
    toks = HARMONY.get(bar, "Gm").split()
    out, b = [], 0.0
    even = 4.0 / len(toks)
    for t in toks:
        sym, d = (t.split(":")[0], float(t.split(":")[1])) if ":" in t else (t, even)
        out.append((b, sym, d))
        b += d
    return out


def build():
    p = Piece("kingdom_2", seed=2202, bpm=100, meter=(4, 4), key="G", mode="dorian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 3.5, (200.0, 220.0)
    p.out = "assets/audio/music/kingdom_2.ogg"
    m = Mode("G", "dorian", octave=4)            # degree 0 = G4

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    pipe = p.track("bagpipe", P.BAGPIPE.variant(gain_db=-10.0, eq=[("hp", 120), ("peak", 880, -3.0, 2.0),     # flatten the reed's
                                                                ("peak", 1200, -6.0, 1.2),   # formant: the drone
                                                                ("peak", 2600, -4.0, 1.0),   # must not sit in
                                                                ("lp", 5000)]))             # the voice band
    cb = p.track("contrabass", P.CONTRABASS)
    fid = p.track("fiddle", P.FIDDLE)
    fds = p.track("fiddle_ds", P.FIDDLE.variant(name="fiddle_ds", pan=0.08, gain_db=-6.0, color=(200, 150, 50)))
    vla = p.track("viola", P.VIOLA)
    vc = p.track("cello", P.CELLO)
    bass = p.track("bass", P.BASS_PIZZ)
    dul = p.track("dulcimer", P.DULCIMER)
    h1 = p.track("horn1", P.HORNS.variant(pan=-0.5))
    h2 = p.track("horn2", P.HORNS.variant(pan=-0.3, gain_db=-11.0))
    sn1 = p.track("snare_1", P.SNARE.variant(pan=0.22))
    sn2 = p.track("snare_2", P.SNARE.variant(name="field_snare_2", pan=-0.25, gain_db=-5.0))
    fd = p.track("frame_drum", P.FRAME_DRUM.variant(name="deep_frame_drum", gain_db=-4.0,
                                                    synth_params={"size": 0.82, "skin": 0.9, "ring": 1.2}))
    boom = p.track("cannon", P.SNARE.variant(name="cannon", pan=-0.55, reverb=0.9, gain_db=-9.0,
                                             eq=[("hp", 28), ("lp", 700)], color=(120, 120, 140)))
    timp = p.track("timpani", P.TIMPANI.variant(gain_db=-8.0))

    intro = p.section("intro", 6)
    a1 = p.section("A1", 8)
    a2 = p.section("A2 double-stops", 8)
    a3 = p.section("A3 inverted", 8)
    b1 = p.section("B horns + dulcimer", 8)
    b2 = p.section("B2", 8)
    br = p.section("drum bridge", 8)
    r1 = p.section("A'1", 8)
    r2 = p.section("A'2", 8)
    r3 = p.section("A'3 stretto", 8)
    cad = p.section("cadence", 6)
    del intro, a1, a2, a3, b1, b2, br, r1, r2, r3, cad

    for bar in (7, 15, 23, 31, 39, 55, 63, 71, 79):
        p.breathe(B(bar), beats=0.75, depth=0.03)
    p.breathe(B(47), beats=1.5, depth=0.05)
    p.rit(B(80), B(81, 2), to=0.84)

    # ================================================================ drones: bagpipe and arco contrabass
    for s, e, notes in ((1, 31, ["G3", "D4"]), (43, 47, ["G3", "D4"]), (55, 84, ["G3", "D4"])):
        pipe.drone(B(s), B(e), notes, vel=84)
    pipe.curve(B(1), B(3), 60, 96)
    pipe.curve(B(7), B(30), 92, 104)
    pipe.curve(B(30), B(31), 104, 50)
    pipe.curve(B(43), B(47), 30, 96)
    pipe.curve(B(55), B(78), 100, 112)
    pipe.curve(B(81, 3), B(83, 3), 112, 0, "lin")
    cb.drone(B(1), B(31), ["G1"], vel=70, art="legato")
    cb.drone(B(55), B(81, 2), ["G1"], vel=74, art="legato")
    cb.note(B(81, 2), "G1", 8, vel=80, art="legato")
    cb.curve(B(1), B(6), 30, 90)
    cb.curve(B(81, 3), B(83, 4), 100, 20, "lin")

    # ================================================================ drums: the 3+3+2 engine
    S1 = "X..g.gx..g..X.g.|X..g.gx..g.gX.gg"            # snare 1: accents on 1, the "and" of 2, 4
    S2 = "..o..o..o.o..o.o|..o..o..o.o..ogo"            # snare 2 interlocks in the gaps
    FD = {"dum": "X.....x.....x...", "tek": "...g.....g....g."}
    sn1.pattern(B(1), 2, "o..g..o..g..o.g.", vel=64)
    sn1.pattern(B(3), 4, S1, vel=70)
    sn2.pattern(B(3), 4, S2, vel=62)
    sn1.curve(B(1), B(7), 84, 108)
    fd.pattern(B(3), 2, {"dum": "x.....o.....o...", "tek": "...g.....g....g."}, vel=62)
    fd.pattern(B(5), 2, FD, vel=70)
    boom.hit(B(4), "boom", vel=70)
    boom.hit(B(6, 2), "boom2", vel=62)
    sn1.pattern(B(7), 23, S1, vel=70)
    sn2.pattern(B(7), 8, S2, vel=50)
    sn2.pattern(B(15), 15, S2, vel=60)
    fd.pattern(B(7), 24, FD, vel=78)
    for bar in (10, 14, 18, 22, 26, 30):
        sn1.roll(B(bar, 3), 1.0, "snare", vel0=30, vel1=72, rate=0.0625)
    for bar in (11, 19, 27):
        boom.hit(B(bar), "boom", vel=64 + (bar - 11))

    # ================================================================ A (7-30): the theme
    THEME = ("G4:.5 A4:.5 Bb4:.5 C5:1.5 D5:1 | C5:1.5 G4:1.5 F4:.5 G4:.5 | "      # Wheel 3+3+2, answer C-G
             "Bb4:.5 C5:.5 D5:.5 E5:1.5:m F5:1 | E5:.5 D5:.5 C5:.5 D5:2.5 | "      # a third up, Dorian E: on D
             "G4:.5 A4:.5 Bb4:.5 C5:1.5 D5:1 | F5:.5 E5:.5 D5:.5 C5:1.5 Bb4:1 | "
             "A4:.5 Bb4:.5 C5:.5 A4:1.5 F4:1 | C5:1.5:! G4:2.5")                   # the answer closes on G
    mel(fid, B(7), THEME, vel=82, art="legato", dyn="arch")
    for s in (7, 9, 11, 13):
        fid.swell(B(s), B(s + 2), 84, 110, peak=0.5)
    # A2: double-stops (open D or the diatonic third below) and ornaments
    THEME2 = THEME.replace("C5:1.5 D5:1 | C5:1.5", "C5:1.5:gu D5:1 | C5:1.5:m").replace("A4:1.5 F4:1", "A4:1.5:t F4:1")
    mel(fid, B(15), THEME2, vel=88, art="legato", dyn="arch")
    for s in (15, 17, 19, 21):
        fid.swell(B(s), B(s + 2), 90, 116, peak=0.5)
    for x in [x for x in fid.notes if B(15) <= x.beat < B(23) and x.dur >= 1.0]:
        d, _ = m.degree_of(x.pitch)
        low = m.pitch(d - 2)                                   # a third below; under G4 the open D string
        fds.note(x.beat, low if low >= 60 else 62, x.dur, vel=x.vel * 0.85, art="legato")
    fds.curve(B(15), B(23), 80, 100)
    mel(vla, B(15), "D4:3 E4:1 | E4:2 D4:2 | D4:2 F4:2 | A4:2 F4:2 | D4:3 E4:1 | A4:2 G4:2 | "
                    "F4:1.5 E4:1.5 D4:1 | E4:1.5 D4:2.5", vel=74, dyn="arch")     # contrary motion, held
    vla.curve(B(15), B(23), 80, 104)
    # A3: the Wheel inverted, sequenced down (D, C, Bb, A), then the build to the horn signal
    seq_start = B(23)
    for k, top in enumerate((4, 3, 2, 1)):                     # degrees: D5, C5, Bb4, A4
        mot = wheel().invert(0).transpose(top).rhythm([0.5, 0.5, 0.5, 1.5, 1.0])
        fid.play(mot.ornament(3, "mordent" if k % 2 else "grace_up"), seq_start + 4 * k, mode=m, vel=86 + 2 * k,
                 art="legato")
    mel(vla, B(23), "G3:4 | F3:4 | E3:4 | D3:4", vel=72)
    mel(fid, B(27), "D5:.5 D5:.5 D5:.5 C5:1.5 Bb4:1 | A4:.5 A4:.5 A4:.5 Bb4:1.5 C5:1 | "
                    "D5:.5 D5:.5 F5:.5 E5:1.5 D5:1 | C5:.5 D5:.5 E5:.5 D5:2.5", vel=90, art="normal", dyn="cresc")
    fid.curve(B(23), B(27), 96, 108)
    fid.curve(B(27), B(31), 104, 120)
    vla.double(fid, B(27), B(31), interval=-12, vel=0.82)
    vla.curve(B(27), B(31), 90, 112)
    h1.notes_seq(B(30), ["A3", "D4"], [1.5, 2.5], vel=72, art="legato")       # the first horn signal: a rising
    h2.notes_seq(B(30), ["F3", "A3"], [1.5, 2.5], vel=68, art="legato")       # fourth, opening B

    # ================================================================ B (31-46): horn signals, dulcimer answers
    calls = [  # (bar, horn1, horn2): two notes each, never more
        (31, ["F3", "D3"], ["D3", "Bb2"]),        # falling minor third
        (33, ["C4", "F3"], ["A3", "C3"]),         # falling fifth
        (35, ["G3", "D3"], ["D3", "Bb2"]),        # the falling fourth (the Wheel's answer)
        (37, ["A3", "D4"], ["F3", "A3"]),         # rising fourth: half cadence
        (39, ["F3", "D3"], ["D3", "Bb2"]),
        (41, ["C4", "F3"], ["A3", "C3"]),
        (43, ["D4", "G3"], ["Bb3", "D3"]),
        (45, ["A3", "D3"], ["F3", "A2"]),
    ]
    for bar, a, b in calls:
        v = 74 if bar < 39 else 80
        h1.notes_seq(B(bar), a, [1.5, 3.5], vel=v, art="legato")
        h2.notes_seq(B(bar), b, [1.5, 3.5], vel=v * 0.92, art="legato")
    answers = {  # the dulcimer answers each call with a Wheel fragment and a tremolo on its held note
        32: ("Bb4:.5 C5:.5 D5:.5", "D5"), 34: ("F4:.5 G4:.5 A4:.5", "A4"),
        36: ("G4:.5 A4:.5 Bb4:.5", "Bb4"), 38: ("D5:.5 C5:.5 A4:.5", "A4"),
        40: ("Bb4:.5 C5:.5 D5:.5", "F5"), 42: ("A4:.5 C5:.5 F5:.5", "E5"),
        44: ("G4:.5 Bb4:.5 C5:.5", "E5"), 46: ("F5:.5 E5:.5 D5:.5", "A4"),
    }
    for bar, (frag, held) in answers.items():
        e = mel(dul, B(bar), frag, vel=70, art="normal")
        dul.tremolo(e, B(bar + 1) - e - 0.25, held, rate=0.125, vel=60, dyn="arch")
    # under the dialogue: dulcimer low broken chords in the call bars, pizz bass, cello holds
    for bar in range(31, 47):
        sym = segs(bar)[0][1]
        if bar % 2 == 1:
            dulcimer_bar(dul, B(bar), sym, "half", vel=50, octave=3, ring=1.2)
        bass.note(B(bar), bass_of(sym, 2), 1.5, vel=78)
        bass.note(B(bar, 1.5), bass_of(sym, 2), 1.0, vel=60)
        bass.note(B(bar, 3), bass_of(sym, 2) + 7, 1.0, vel=66)
        if bar % 2 == 1:
            vc.note(B(bar), bass_of(sym, 3) if bass_of(sym, 3) <= 55 else bass_of(sym, 2), 8, vel=66, art="legato")
    vc.curve(B(31), B(39), 70, 88)
    vc.curve(B(39), B(47), 88, 104)
    # the fiddle comes back on held double-stops (bars 39-46)
    mel(fid, B(39), "F5:4 | F5:2 D5:2 | C5:4 | C5:2 A4:2 | D5:4 | E5:2 C5:2 | D5:4 | D5:3 A4:1", vel=78)
    mel(fds, B(39), "Bb4:4 | A4:2 F4:2 | A4:4 | F4:2 F4:2 | G4:4 | G4:2 E4:2 | F4:4 | F4:3 D4:1", vel=70)
    for s in range(39, 47, 2):
        fid.swell(B(s), B(s + 2), 72, 104, peak=0.45)
        fds.swell(B(s), B(s + 2), 66, 96, peak=0.45)
    sn1.pattern(B(31), 16, "x..g..o..g..o.g.|x..g..o..g.go.g.", vel=58)
    fd.pattern(B(31), 16, {"dum": "x.....o.....o...", "tek": "...g.....g....g."}, vel=64)
    boom.hit(B(35), "boom", vel=58)
    boom.hit(B(43, 2), "boom", vel=62)

    # ================================================================ drum bridge (47-54): drums only
    # the 3+3+2 accents slide one sixteenth later each bar (rhythmic displacement), over a long crescendo
    base = "X..g.gX..g..X.g."
    for k in range(8):
        bar = 47 + k
        sh = k % 4
        rot = base[-sh:] + base[:-sh] if sh else base
        sn1.pattern(B(bar), 1, rot, vel=58 + 4 * k)
        sn2.pattern(B(bar), 1, "..o..o..o.o..o.o" if k < 4 else "g.o.go.go.o.go.o", vel=50 + 4 * k)
        fd.pattern(B(bar), 1, {"dum": "X.....x.....x...", "tek": "...g.....g..gg.g"}, vel=66 + 3 * k)
        timp.note(B(bar), "G2", 1.5, vel=50 + 4 * k)
        timp.note(B(bar, 1.5), "D2", 1.5, vel=46 + 4 * k)
        timp.note(B(bar, 3), "G2", 1.0, vel=46 + 4 * k)
    boom.hit(B(47), "boom", vel=74)
    boom.hit(B(50, 2), "boom2", vel=66)
    boom.hit(B(53), "boom", vel=76)
    sn1.roll(B(54), 3.75, "snare", vel0=40, vel1=96, rate=0.0625)
    sn2.roll(B(54, 2), 1.75, "snare2", vel0=40, vel1=88, rate=0.0625)
    timp.roll(B(54), 3.5, "D2", vel0=40, vel1=88, rate=0.125)

    # ================================================================ A' (55-78): everything back, fuller
    mel(fid, B(55), THEME2, vel=94, art="legato", dyn="arch")
    mel(fid, B(63), THEME.replace("E5:1.5:m F5:1", "E5:1.5:t F5:1").replace("C5:1.5:! G4:2.5", "C5:1.5:! G4:2.5:s"),
        tr=0, vel=96, art="legato", dyn="arch")
    for s in range(55, 71, 2):
        fid.swell(B(s), B(s + 2), 94, 122, peak=0.5)
    for x in [x for x in fid.notes if B(55) <= x.beat < B(71) and x.dur >= 1.0]:
        d, _ = m.degree_of(x.pitch)
        low = m.pitch(d - 2)
        fds.note(x.beat, low if low >= 60 else 62, x.dur, vel=x.vel * 0.85, art="legato")
    fds.curve(B(55), B(71), 92, 112)
    mel(vla, B(55), "D4:3 E4:1 | E4:2 D4:2 | D4:2 F4:2 | A4:2 F4:2 | D4:3 E4:1 | A4:2 G4:2 | "
                    "F4:1.5 E4:1.5 D4:1 | E4:1.5 D4:2.5", vel=82, dyn="arch")
    mel(vla, B(63), "Bb3:3 C4:1 | C4:2 E4:2 | F4:2 D4:2 | C4:2 A3:2 | Bb3:3 C4:1 | F4:2 E4:2 | "
                    "C4:1.5 Bb3:1.5 A3:1 | G3:1.5 Bb3:2.5", vel=84, dyn="arch")
    vla.curve(B(55), B(71), 92, 112)
    # A'3: the Wheel in stretto: fiddle on G, the viola a bar later a fifth below, then both climb (sequence)
    for k, deg in enumerate((0, 2, 3, 4)):                      # G, Bb, C, D
        fid.play(wheel().rhythm([0.5, 0.5, 0.5, 1.5, 1.0]).transpose(deg).ornament(3, "mordent"), B(71 + k),
                 mode=m, vel=96 + 2 * k, art="legato")
        vla.play(wheel().rhythm([0.5, 0.5, 0.5, 1.5, 1.0]).transpose(deg - 3), B(71 + k, 2), mode=m, vel=86,
                 art="legato")
    mel(fid, B(75), "G5:1.5:gd F5:1.5 E5:1 | F5:1.5 E5:1.5 D5:1 | E5:1.5 D5:1.5 C5:1 | D5:4:m", vel=100,
        dyn="dim")
    mel(vla, B(75), "Bb4:1.5 A4:1.5 G4:1 | D4:1.5 E4:1.5 F4:1 | G4:1.5 F4:1.5 E4:1 | F4:2 A4:2", vel=88)
    fid.curve(B(71), B(75), 108, 127)
    fid.curve(B(75), B(79), 124, 104)
    vla.curve(B(71), B(79), 104, 118)
    mel(fds, B(75), "Bb4:1.5 A4:1.5 G4:1 | A4:1.5 G4:1.5 F4:1 | G4:1.5 F4:1.5 E4:1 | F4:4", vel=80)

    # horns in A': signals at the period seams only
    for bar, a, b in ((62, ["D4", "G3"], ["Bb3", "D3"]), (70, ["D4", "G3"], ["Bb3", "D3"]),
                      (74, ["A3", "D4"], ["F3", "A3"]), (78, ["A3", "D4"], ["F3", "A3"])):
        h1.notes_seq(B(bar), a, [1.5, 2.5], vel=80, art="legato")
        h2.notes_seq(B(bar), b, [1.5, 2.5], vel=74, art="legato")
    # dulcimer tremolos on the long notes, broken chords between
    for bar in range(55, 79):
        for off, sym, d in segs(bar):
            dulcimer_bar(dul, B(bar, off), sym, "roll2" if bar % 2 else "roll", vel=54, octave=3, beats=d, ring=1.5)
    for bar, nt in ((56, "D5"), (60, "F5"), (64, "D5"), (68, "F5"), (74, "A5"), (78, "A5")):
        dul.tremolo(B(bar, 1.5), 2.5, nt, rate=0.125, vel=56, dyn="cresc")
    for bar in range(55, 79):
        sg = segs(bar)
        for off, sym, d in sg:
            vc.note(B(bar, off), bass_of(sym, 2) if bass_of(sym, 2) >= 41 else bass_of(sym, 3), d, vel=72,
                    art="legato")
    vc.curve(B(55), B(79), 96, 116)
    sn1.pattern(B(55), 24, S1, vel=76)
    sn2.pattern(B(55), 24, S2, vel=64)
    sn1.pattern(B(55), 24, {"tambourine": "......x.......x."}, vel=46)
    fd.pattern(B(55), 24, FD, vel=86)
    for bar in (62, 70, 78):
        sn1.roll(B(bar, 3), 1.0, "snare", vel0=36, vel1=80, rate=0.0625)
    boom.hit(B(55), "boom", vel=80)
    boom.hit(B(63), "boom", vel=72)
    boom.hit(B(71), "boom", vel=76)
    timp.note(B(55), "G2", 2, vel=72)
    timp.roll(B(78, 2), 2.0, "D2", vel0=40, vel1=84, rate=0.125)

    # ================================================================ bass riff (A sections): 3+3+2, approach notes
    def riff(bar, vel):
        sg = segs(bar)
        nxt = segs(bar + 1)[0][1]
        if len(sg) == 1:
            r = bass_of(sg[0][1], 2)
            tgt = bass_of(nxt, 2)
            appr = tgt - 2 if abs(tgt - 2 - r) > 0 else tgt + 1
            bass.note(B(bar), r, 1.0, vel=vel)
            bass.note(B(bar, 1.5), r, 1.0, vel=vel * 0.86)
            bass.note(B(bar, 3), r + 7 if bar % 2 else appr, 1.0, vel=vel * 0.8)
        else:
            for off, sym, d in sg:
                bass.note(B(bar, off), bass_of(sym, 2), min(d, 1.5), vel=vel * (1.0 if off == 0 else 0.88))
                if d >= 2.5:
                    bass.note(B(bar, off + 1.5), bass_of(sym, 2), 1.0, vel=vel * 0.8)
    for bar in list(range(7, 31)) + list(range(55, 79)):
        riff(bar, 80 if bar < 55 else 86)
    bass.note(B(5), "G2", 1.0, vel=66)
    bass.note(B(5, 1.5), "G2", 1.0, vel=58)
    bass.note(B(6), "G2", 1.0, vel=68)
    bass.note(B(6, 1.5), "G2", 1.0, vel=60)
    bass.note(B(6, 3), "F2", 1.0, vel=60)
    for bar in range(7, 31):                     # cello: one held bass note per chord, a floor for the drive
        for off, sym, d in segs(bar):
            vc.note(B(bar, off), bass_of(sym, 2) if bass_of(sym, 2) >= 41 else bass_of(sym, 3), d, vel=64,
                    art="legato")
    vc.curve(B(7), B(31), 76, 96)
    for bar in range(7, 31):                     # dulcimer: broken chords, quieter in A1
        for off, sym, d in segs(bar):
            dulcimer_bar(dul, B(bar, off), sym, "roll" if bar % 2 else "pulse", vel=46 if bar < 15 else 52,
                         octave=3, beats=d, ring=1.4)
    for bar, nt in ((16, "D5"), (20, "F5")):
        dul.tremolo(B(bar, 1.5), 2.5, nt, rate=0.125, vel=50, dyn="cresc")

    # ================================================================ cadence (79-84): the Wheel and its answer
    # in augmentation over F, then G, firm, with the last boom; the drone rings out
    mel(fid, B(79), "G4:1 A4:1 Bb4:1 C5:3:m D5:2 | C5:2:! G4:8", vel=100, dyn=[1.0, 1.0, 1.02, 1.06, 1.08, 1.1, 1.0])
    mel(vla, B(79), "D4:2 F4:2 | E4:2 G4:2 | A4:2 G4:8", vel=90)
    mel(fds, B(79), "D4:3 E4:3 F4:2 | E4:2 D4:8", vel=82)
    fid.curve(B(79), B(81, 2), 110, 124)
    fid.curve(B(81, 3), B(83, 4), 124, 24, "lin")
    vla.curve(B(81, 3), B(83, 4), 112, 22, "lin")
    fds.curve(B(81, 3), B(83, 4), 104, 20, "lin")
    vc.note(B(79), "G2", 4, vel=78, art="legato")
    vc.note(B(80), "C3", 4, vel=78, art="legato")
    vc.note(B(81), "F2", 2, vel=82, art="legato")
    vc.note(B(81, 2), "G2", 8, vel=88, art="legato")
    vc.curve(B(81, 3), B(83, 4), 112, 24, "lin")
    bass.note(B(79), "G2", 1.0, vel=86)
    bass.note(B(79, 1.5), "G2", 1.0, vel=74)
    bass.note(B(80), "C3", 1.0, vel=86)
    bass.note(B(80, 1.5), "C3", 1.0, vel=74)
    bass.note(B(81), "F2", 1.5, vel=88)
    bass.note(B(81, 2), "G1", 3, vel=96)
    dulcimer_bar(dul, B(79), "Gm", "roll", vel=58, octave=3)
    dulcimer_bar(dul, B(80), "C", "roll", vel=60, octave=3)
    dul.chord(B(81), chord("F", 3) + [n + 12 for n in chord("F", 3)], 2, vel=62, strum=0.02, art="ring")
    dul.chord(B(81, 2), ["G3", "D4", "G4", "Bb4", "D5", "G5"], 8, vel=70, strum=0.03, art="ring")
    h1.notes_seq(B(80, 2), ["C4", "G3"], [2.5, 7], vel=82, art="legato")      # the answer, last signal
    h2.notes_seq(B(80, 2), ["E3", "D3"], [2.5, 7], vel=76, art="legato")
    sn1.pattern(B(79), 1, S1.split("|")[0], vel=80)
    sn2.pattern(B(79), 1, S2.split("|")[0], vel=68)
    sn1.roll(B(80), 3.5, "snare", vel0=40, vel1=90, rate=0.0625)
    sn1.flam(B(81, 2), "snare", vel=96)
    sn2.flam(B(81, 2), "snare2", vel=86)
    fd.pattern(B(79), 2, FD, vel=88)
    fd.hit(B(81), "doum", vel=96)
    fd.hit(B(81, 2), "doum", vel=110)
    timp.roll(B(80, 2), 1.5, "D2", vel0=50, vel1=90, rate=0.125)
    timp.note(B(81, 2), "G2", 4, vel=96)
    boom.hit(B(81, 2), "boom", vel=92)
    boom.hit(B(83, 1), "boom2", vel=56)                         # one far answer from the hills
    p.set_end(B(84, 1))                     # the chord has decayed by here; the tail is the room
    return p


if __name__ == "__main__":
    print(build().compile().summary())
