#!/usr/bin/env python3
"""Kingdom 2, "Boards and Thunder" (assets/audio/music/kingdom_2.ogg). G Dorian, 100 BPM, 4/4, about 3:22.

Composer's note. Form (bars, 1-based): intro 1-6 | A 7-30 (three 8-bar periods) | B 31-46 | drum bridge 47-54 |
A' 55-78 | stop-time cadence 79-84. The metre feel is 3+3+2 throughout: two field snares interlock in that
grouping, the deep frame drum and the pizzicato bass mark it, and the hammered dulcimer plays a tremolo chord on
the downbeat and chops on the two off-beat accents (beats 2.5 and 4), so the bar drives forward instead of
marching. The Wheel is re-cut to the same grouping: its three short notes are a sixteenth-note pickup (G-A-Bb)
and its two long notes fill the bar as 3 + 5 eighths (C, D; bar 7, over the Dorian IV). The answer falls C-G on
the off-beat accents (bar 8), the third bar hammers D on all three accents, the fourth stops on a half cadence on
D with the pickup again, and the consequent climbs to G5 and closes IV-i (C-G) on G. A2 varies the rhythm (a
neighbour-note chop on D, an off-beat E), adds double-stops picked from the chord, a viola counter-line in
contrary motion and a new consequent: the pickup a step higher (A-Bb-C into D-E) and a v-i close. A3 develops:
the Wheel inverted falls from the fiddle while the viola answers with it upright from below, a step lower each
time, then both hammer the build to the first horn signal. In B (on Bb) the bagpipe rests: two far horns give
signals in fifths and octaves only, voiced an open fifth or octave apart, and the dulcimer answers each with a
Wheel fragment and a tremolo; the fiddle returns on held double-stops. The bridge is drums only (two snares,
frame drum, timpani on G and D, distant cannon booms) with the accents displaced by a sixteenth every bar and a
long crescendo. A' is a set of variations, not a repeat: A'1 puts the theme in the viola and cello an octave down
under a new fiddle descant in double-stops (a 4-3 suspension at bar 59); A'2 gives the theme back to the fiddle
with a new consequent that climbs C-D-E-F-G and closes high, D rising to the upper G; A'3 runs the Wheel in 3+3+2
augmentation (dotted, dotted, quarter) in stretto, the viola a fifth below and a dotted quarter behind, to the
top A5, then turns it upside down over the viola's counter-line. The cadence is stop-time: the Wheel and its
answer once more, three band hits on the 3+3+2 accents of bar 81 with the top line falling C-Bb-A, and one struck
G (an open fifth) with the cannon; the bowed parts cut off together on a beat and the dulcimer, timpani and the
boom ring into the room. Arc: soft intro, A building, B lighter, bridge from pp to ff, A' strongest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import bass_of, chord, dulcimer_bar, mel  # noqa: E402
from score import Mode, Piece, _contour, n  # noqa: E402

HARMONY = {
    # A1 (7-14): the theme
    7: "C:1.5 Gm:2.5", 8: "F:1.5 C:1.5 Gm:1", 9: "Bb:1.5 Dm:1.5 F:1", 10: "C:1.5 Dm:2.5",
    11: "C:1.5 Gm:1.5 F:1", 12: "C:1.5 F:2.5", 13: "Bb:1.5 F:1.5 C:1", 14: "Gm",
    # A2 (15-22): the antecedent varied, a new consequent
    15: "C:1.5 Gm:2.5", 16: "F:1.5 C:1.5 Gm:1", 17: "Bb:1.5 Dm:1.5 F:1", 18: "C:1.5 Dm:2.5",
    19: "Gm:1.5 C:2.5", 20: "C:1.5 Bb:1.5 F:1", 21: "Bb:1.5 Dm:2.5", 22: "Gm",
    # A3 (23-30): development
    23: "Gm:1.5 F:2.5", 24: "C:1.5 Gm:2.5", 25: "F:1.5 Bb:2.5", 26: "Bb:1.5 F:2.5",
    27: "Gm:1.5 F:2.5", 28: "Bb:1.5 C:1.5 Dm:1", 29: "Bb:1.5 C:2.5", 30: "Dm",
    # B (31-46) on Bb
    31: "Bb", 32: "Bb", 33: "F", 34: "F", 35: "Gm", 36: "Gm", 37: "Dm", 38: "Dm",
    39: "Bb", 40: "Bb", 41: "F", 42: "F", 43: "Gm", 44: "C", 45: "Dm", 46: "Dm",
    # A'1 (55-62): the theme low under a descant
    55: "C:1.5 Gm:2.5", 56: "F:1.5 C:1.5 Gm:1", 57: "Bb:1.5 Dm:1.5 F:1", 58: "C:1.5 Dm:2.5",
    59: "C:1.5 Gm:1.5 F:1", 60: "C:1.5 F:2.5", 61: "Bb:1.5 F:1.5 C:1", 62: "Gm",
    # A'2 (63-70): the theme and a new, climbing consequent
    63: "C:1.5 Gm:2.5", 64: "F:1.5 C:1.5 Gm:1", 65: "Bb:1.5 Dm:1.5 F:1", 66: "C:1.5 Dm:2.5",
    67: "F:1.5 C:2.5", 68: "Dm:1.5 Bb:1.5 C:1", 69: "Bb:1.5 F:1.5 Gm:1", 70: "Gm",
    # A'3 (71-78): the Wheel in augmentation, in stretto
    71: "Gm:1.5 C:1.5 F:1", 72: "C7:1.5 F:1.5 Dm:1", 73: "Dm:1.5 C:1.5 F:1", 74: "C:1.5 Dm:2.5",
    75: "Gm:1.5 Bb:1.5 C:1", 76: "F:1.5 Dm:2.5", 77: "Bb:1.5 C:2.5", 78: "Dm",
    # stop-time cadence (79-84)
    79: "C:1.5 Gm:2.5", 80: "F:1.5 C:2.5", 81: "C:1.5 Gm:1.5 F:1", 82: "G5", 83: "G5", 84: "G5",
}

# ---------------------------------------------------------------------------------------- the lines
PICKUP = "G4:.25 A4:.25 Bb4:.25"                       # the Wheel's three short notes, before the bar
THEME_ANT = ("C5:1.5:gu D5:2.5 | "                      # ... and its two long notes as 3 + 5 eighths
             "F5:.75 E5:.25 D5:.5 C5:1.5 G4:1 | "        # the answer: C falls to G on the off-beat accents
             "D5:1.5:^ D5:1.5:^ F5:1 | "                 # D hammered on the three accents
             "E5:1.5 D5:1.75")                           # half cadence on D (+ the pickup)
THEME_CON = ("C5:1.5 D5:1.5 F5:1 | "                    # the Wheel lands and keeps climbing
             "G5:1.5:m F5:.75 E5:.25 F5:1.5 | "          # F tied across the "2"
             "D5:.75 C5:.25 Bb4:.5 A4:1.5 C5:1 | "       # C on the last accent ...
             "G4:2.5")                                   # ... falls the fourth to G: IV-i
A2_ANT = ("C5:1.5:gu D5:1 C5:.5 D5:1 | "               # D chopped around its neighbour
          "F5:1 E5:.5 C5:1.5:m G4:1 | "
          "D5:1.5 F5:1 E5:.5 F5:1 | "
          "E5:1.5 D5:1.75 A4:.25 Bb4:.25 C5:.25")       # the pickup a step higher ...
A2_CON = ("D5:1.5 E5:2.5:m | "                          # ... the Wheel on A, onto the Dorian E
          "G5:.75 F5:.25 E5:.5 D5:1.5 C5:1 | "
          "F5:1.5 D5:.5 E5:.5 C5:.5 A4:1 | "             # v-i: A to G
          "G4:1.5 D5:1.75 G5:.25 F5:.25 E5:.25")         # pickup: the Wheel upside down
A3_FID = ("D5:1.5 C5:2.5 | r:3.25 F5:.25 E5:.25 D5:.25 | "   # falling from G, then from F, then from E
          "C5:.75 D5:.25 C5:.5 Bb4:2.5 | r:3.25 E5:.25 D5:.25 C5:.25 | "
          "Bb4:1.5 A4:2.5 | "
          "D5:.75 D5:.25 D5:.5 E5:1.5 F5:1 | "               # the build
          "F5:1.5 G5:1 F5:.5 E5:1 | D5:2.5:m")
A3_VLA = ("r:3.25 G3:.25 A3:.25 Bb3:.25 | C4:1.5 D4:2.5 | "  # ... the viola answers it upright from below
          "r:3.25 F3:.25 G3:.25 A3:.25 | Bb3:1.5 C4:2.5 | "
          "G3:1.5 F3:1.75 A3:.25 Bb3:.25 C4:.25")
B_FID = "F5:4 | F5:1.5 D5:2.5 | C5:4 | C5:2 A4:2 | D5:4 | E5:1.5 C5:2.5 | D5:4 | D5:3 A4:1"
B_FDS = "Bb4:4 | Bb4:1.5 F4:2.5 | A4:4 | F4:2 F4:2 | G4:4 | G4:1.5 E4:2.5 | F4:4 | F4:3 D4:1"
DESCANT = ("E5:1.5 D5:2.5 | r:.5 C5:1 E5:1.5 D5:1 | F5:2.5 E5:.5 F5:1 | "      # over the low theme (A'1)
           "G5:1.5 F5:3 E5:1 D5:1.5 C5:1 | "                                     # F over C: a 4-3 suspension
           "E5:1 G5:.5 F5:2.5 | F5:1.5 C5:1.5 E5:1 | D5:2.5")
R2_CON = ("F5:1.5 G5:2.5:m | "                          # the Wheel on C, to G5
          "F5:.75 E5:.25 D5:.5 Bb4:1.5 C5:1 | "
          "D5:1.5 C5:1 A4:.5 Bb4:1 | "
          "D5:1.5 G5:2.5:gd")                            # closes high: D rises to the upper G
R3_FID = ("D5:1.5 E5:1.5 F5:1 | G5:1.5 A5:2.5:m | "      # the Wheel in 3+3+2 augmentation, to the top A
          "A5:1.5 G5:1.5 F5:1 | E5:1.5 D5:1 C5:.5 D5:1 | "   # ... and upside down
          "G5:1.5:gd D5:1 F5:.5 E5:1 | F5:.75 E5:.25 C5:.5 D5:2.5 | "
          "D5:1.5 E5:1 G5:.5 E5:1 | D5:2.5:m")
R3_VLA = ("r:1.5 G4:1.5 A4:1.5 Bb4:1 C5:1.5 D5:2.5 C5:1.5 A4:1 G4:1.5 A4:2.5 | "   # stretto, a 5th below
          "Bb4:1.5 F4:1.5 G4:1 | A4:1.5 F4:2.5 | F4:1.5 G4:2.5 | A4:2.5 F4:1.5")
A2_VLA = ("E4:1.5 D4:2.5 | F4:1.5 E4:1.5 D4:1 | D4:3 C4:1 | E4:1.5 F4:2.5 | "      # contrary motion, held
          "G4:1.5 E4:2.5 | E4:1.5 F4:1.5 A4:1 | D4:1.5 F4:2.5 | D4:1.5 G4:2.5")
R2_VLA = ("E4:1.5 D4:2.5 | F4:1.5 E4:1.5 D4:1 | D4:3 C4:1 | E4:1.5 F4:2.5 | "
          "A4:1.5 G4:2.5 | A4:1.5 F4:1.5 G4:1 | F4:1.5 A4:1.5 G4:1 | G4:1.5 Bb4:2.5")


def segs(bar):
    toks = HARMONY.get(bar, "Gm").split()
    out, b = [], 0.0
    even = 4.0 / len(toks)
    for t in toks:
        sym, d = (t.split(":")[0], float(t.split(":")[1])) if ":" in t else (t, even)
        out.append((b, sym, d))
        b += d
    return out


def sym_at(bar, off):
    for o, sym, d in segs(bar):
        if o <= off + 1e-6 < o + d:
            return sym
    return segs(bar)[-1][1]


def voicing(sym, lo=50):
    """A close triad with every note at or above `lo` (the dulcimer's low D3 by default)."""
    return sorted(p if p >= lo else p + 12 for p in chord(sym, 3))


def build():
    p = Piece("kingdom_2", seed=2202, bpm=100, meter=(4, 4), key="G", mode="dorian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 2.0, (200.0, 220.0)
    p.out = "assets/audio/music/kingdom_2.ogg"
    m = Mode("G", "dorian", octave=4)            # degree 0 = G4
    SC = m.scale(28, 62)

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    def bar_beat(beat):
        bi = p.bar_index(beat + 1e-6)
        return bi + 1, beat - p.bar(bi)

    pipe = p.track("bagpipe", P.BAGPIPE.variant(gain_db=-10.0, eq=[("hp", 120), ("peak", 880, -3.0, 2.0),
                                                                ("peak", 1174, -10.0, 8.0),  # the G3/D4 partial
                                                                ("peak", 1174, -10.0, 8.0),  # (6th / 4th harmonic)
                                                                ("peak", 1200, -3.0, 1.2),   # the reed formant
                                                                ("peak", 2600, -4.0, 1.0),
                                                                ("lp", 5000)]))
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

    for name, bars in (("intro", 6), ("A1", 8), ("A2 double-stops", 8), ("A3 development", 8),
                       ("B horns + dulcimer", 8), ("B2", 8), ("drum bridge", 8), ("A'1 theme low + descant", 8),
                       ("A'2 new consequent", 8), ("A'3 stretto", 8), ("stop-time cadence", 6)):
        p.section(name, bars)

    for bar in (7, 15, 23, 31, 39, 55, 63, 71, 79):
        p.breathe(B(bar), beats=0.75, depth=0.03)
    p.breathe(B(47), beats=1.5, depth=0.05)
    p.rit(B(80), B(82), to=0.88)

    # ---------------------------------------------------------------- helpers
    def horn(bar, a, b, durs=(1.5, 2.5), beat=0.0, vel=74):
        """A signal: two notes per horn, melodic fifths or octaves only, the horns a fifth or octave apart."""
        h1.notes_seq(B(bar, beat), a, list(durs), vel=vel, art="legato")
        h2.notes_seq(B(bar, beat), b, list(durs), vel=vel * 0.92, art="legato")

    def double_stops(b0, b1, min_dur=1.0, vel=0.85):
        """Under each long fiddle note a chord tone a third or sixth below (else the open A or D string)."""
        for x in [x for x in fid.notes if b0 <= x.beat < b1 and x.dur >= min_dur]:
            bar, off = bar_beat(x.beat)
            pcs = {q % 12 for q in chord(sym_at(bar, off), 3)}
            if x.pitch % 12 not in pcs:
                continue
            low = None
            for k in (3, 4, 8, 9):
                if (x.pitch - k) % 12 in pcs and x.pitch - k >= 57:
                    low = x.pitch - k
                    break
            if low is None:
                for s in (69, 62):                      # open A, open D
                    if s < x.pitch - 2 and s % 12 in pcs:
                        low = s
                        break
            if low is not None:
                fds.note(x.beat, low, x.dur, vel=x.vel * vel, art="legato")

    def trem(beat, dur, lo, hi, vel, dyn=None, rate=0.125):
        """Hammered tremolo on two strings, the hands alternating."""
        cnt = max(2, int(round(dur / rate)))
        con = _contour(dyn, cnt)
        for i in range(cnt):
            dul.note(beat + i * rate, lo if i % 2 == 0 else hi, rate * 2.2, vel * con[i] * (1.0 if i % 2 else 0.9),
                     "hit")

    def chop(beat, sym, vel, lo=50):
        dul.chord(beat, voicing(sym, lo=lo), 0.3, vel=vel, strum=0.008, art="staccato")

    def dul_drive(bar, vel, ghost=False, high=False, trem_len=1.25):
        """The A-section dulcimer: a tremolo chord on the downbeat, chops on the off-beat accents (2.5, 4)."""
        lo = 55 if high else 50
        v = voicing(sym_at(bar, 0), lo=lo)
        trem(B(bar), trem_len, v[0], v[-1], vel * 0.8, dyn="dim")
        for off in (1.5, 3.0):
            chop(B(bar, off), sym_at(bar, off), vel * (1.1 if off == 1.5 else 1.0), lo=lo)
        if ghost:
            dul.note(B(bar, 2.5), voicing(sym_at(bar, 2.5), lo=lo)[1], 0.25, vel=vel * 0.55, art="staccato")

    # ================================================================ drones: bagpipe and arco contrabass
    for s, e, notes in ((1, 31, ["G3", "D4"]), (43, 47, ["G3", "D4"]), (55, 81, ["G3", "D4"])):
        pipe.drone(B(s), B(e), notes, vel=84)
    pipe.curve(B(1), B(3), 60, 96)
    pipe.curve(B(7), B(30), 92, 104)
    pipe.curve(B(30), B(31), 104, 50)
    pipe.curve(B(43), B(47), 30, 96)
    pipe.curve(B(55), B(78), 100, 112)
    cb.drone(B(1), B(31), ["G1"], vel=70, art="legato")
    cb.drone(B(55), B(81), ["G1"], vel=74, art="legato")
    cb.curve(B(1), B(6), 30, 90)

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
    mel(fid, B(6, 3.25), PICKUP, vel=74, art="legato", dyn=(0.85, 1.0))
    e = mel(fid, B(7), THEME_ANT, vel=82, art="legato", dyn="arch")
    e = mel(fid, e, PICKUP, vel=80, art="legato")
    mel(fid, e, THEME_CON, vel=84, art="legato", dyn="arch")
    for s in (7, 9, 11, 13):
        fid.swell(B(s), B(s + 2), 84, 110, peak=0.5)
    # A2: a rhythmic variation, double-stops from the chord, a viola counter-line, a new consequent
    mel(fid, B(14, 3.25), PICKUP, vel=80, art="legato")
    mel(fid, B(15), A2_ANT + " | " + A2_CON, vel=88, art="legato", dyn="arch")
    for s in (15, 17, 19, 21):
        fid.swell(B(s), B(s + 2), 90, 116, peak=0.5)
    double_stops(B(15), B(22))
    fds.curve(B(15), B(23), 80, 100)
    mel(vla, B(15), A2_VLA, vel=74, dyn="arch")
    vla.curve(B(15), B(23), 80, 104)
    # A3: the Wheel inverted from the fiddle, upright from the viola, a step lower each time; the build
    mel(fid, B(23), A3_FID, vel=86, art="legato", dyn="cresc")
    mel(vla, B(23), A3_VLA, vel=78, art="legato")
    fid.curve(B(23), B(28), 96, 108)
    fid.curve(B(28), B(31), 104, 120)
    vla.curve(B(23), B(28), 96, 106)
    vla.double(fid, B(28), B(31), interval=-12, vel=0.82)
    vla.curve(B(28), B(31), 96, 114)
    horn(22, ["G3", "D4"], ["G2", "G3"], vel=70)                    # rising fifth / octave
    horn(30, ["A3", "A4"], ["D3", "D4"], vel=72)                    # rising octaves: open B

    # ================================================================ B (31-46): horn signals, dulcimer answers
    calls = [  # (bar, horn1, horn2): fifths and octaves only, the horns an open fifth or octave apart
        (31, ["F3", "F4"], ["Bb2", "Bb3"]),       # rising octave
        (33, ["C4", "F3"], ["F3", "F2"]),         # falling fifth / octave
        (35, ["D4", "G3"], ["G3", "G2"]),
        (37, ["A3", "A4"], ["D3", "D4"]),         # rising octave: half cadence
        (39, ["Bb3", "F4"], ["Bb2", "Bb3"]),      # rising fifth
        (41, ["F3", "C4"], ["F2", "F3"]),
        (43, ["G3", "D4"], ["G2", "G3"]),
        (45, ["A4", "D4"], ["A3", "D3"]),         # falling fifth
    ]
    for bar, a, b in calls:
        horn(bar, a, b, durs=(1.5, 3.5), vel=74 if bar < 39 else 80)
    answers = {  # the dulcimer answers each call with a Wheel fragment and a tremolo on its held note
        32: ("Bb4:.25 C5:.25 D5:.5", "D5"), 34: ("F4:.25 G4:.25 A4:.5", "A4"),
        36: ("G4:.25 A4:.25 Bb4:.5", "Bb4"), 38: ("D5:.25 C5:.25 A4:.5", "A4"),
        40: ("Bb4:.25 C5:.25 D5:.5", "F5"), 42: ("A4:.25 C5:.25 E5:.5", "F5"),
        44: ("G4:.25 Bb4:.25 C5:.5", "E5"), 46: ("F5:.25 E5:.25 D5:.5", "A4"),
    }
    for bar, (frag, held) in answers.items():
        e = mel(dul, B(bar), frag, vel=72, art="normal")
        dul.tremolo(e, B(bar + 1) - e - 0.25, held, rate=0.125, vel=60, dyn="arch")
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
    mel(fid, B(39), B_FID, vel=78)
    mel(fds, B(39), B_FDS, vel=70)
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

    # ================================================================ A' (55-78): variations, fuller
    # A'1: the theme in viola and cello (unison, an octave down), a fiddle descant in double-stops above
    low_theme = PICKUP + " | " + THEME_ANT + " " + PICKUP + " | " + THEME_CON
    mel(vla, B(54, 3.25), low_theme, vel=90, art="legato", dyn="arch", tr=-12)
    mel(vc, B(54, 3.25), low_theme, vel=84, art="legato", dyn="arch", tr=-12)
    for s in (55, 57, 59, 61):
        vla.swell(B(s), B(s + 2), 96, 122, peak=0.5)
        vc.swell(B(s), B(s + 2), 92, 118, peak=0.5)
    mel(fid, B(55), DESCANT, vel=84, art="legato", dyn="arch")
    for s in (55, 57, 59, 61):
        fid.swell(B(s), B(s + 2), 80, 108, peak=0.55)
    # A'2: the theme back in the fiddle, a new consequent that climbs to G5 and closes high
    mel(fid, B(62, 3.25), PICKUP, vel=86, art="legato")
    mel(fid, B(63), THEME_ANT.replace("C5:1.5:gu D5:2.5", "C5:1.5:gu D5:2.5:m")
        .replace("C5:1.5 G4:1", "C5:1.5:t G4:1") + " C5:.25 D5:.25 E5:.25 | " + R2_CON,
        vel=94, art="legato", dyn="arch")
    for s in range(63, 71, 2):
        fid.swell(B(s), B(s + 2), 96, 122, peak=0.5)
    mel(vla, B(63), R2_VLA, vel=82, dyn="arch")
    vla.curve(B(63), B(71), 92, 112)
    # A'3: the Wheel in augmentation in stretto (the viola a fifth below, a dotted quarter behind), to A5
    mel(fid, B(71), R3_FID, vel=98, art="legato", dyn=(1.06, 0.94))
    mel(vla, B(71), R3_VLA, vel=88, art="legato")
    fid.curve(B(71), B(73), 108, 127)
    fid.curve(B(73), B(79), 124, 104)
    vla.curve(B(71), B(79), 104, 118)
    double_stops(B(55), B(63), min_dur=0.9)
    double_stops(B(63), B(79))
    fds.curve(B(55), B(63), 82, 100)
    fds.curve(B(63), B(79), 94, 112)

    # horns in A': signals at the period seams only
    horn(62, ["G3", "D4"], ["G2", "G3"], vel=78)                    # rising fifth
    horn(70, ["D4", "G3"], ["D3", "G2"], vel=80)                    # falling fifths
    horn(78, ["A3", "A4"], ["D3", "D4"], vel=80)                    # rising octaves, into the cadence
    # dulcimer: tremolo chords and off-beat chops, a tremolo under the long notes
    for bar in range(55, 79):
        dul_drive(bar, 56 if bar < 63 else 60, ghost=bar >= 63, high=bar >= 71)
    for bar, lo_, hi_ in ((60, "F4", "A4"), (67, "A4", "C5"), (72, "A4", "C5"), (76, "A4", "D5")):
        trem(B(bar, 1.5), 2.25, n(lo_), n(hi_), 54, dyn="cresc")
    # cello: the floor (A'2, A'3)
    for bar in range(63, 79):
        for off, sym, d in segs(bar):
            vc.note(B(bar, off), bass_of(sym, 2) if bass_of(sym, 2) >= 41 else bass_of(sym, 3), d, vel=72,
                    art="legato")
    vc.curve(B(63), B(79), 100, 116)
    sn1.pattern(B(55), 24, S1, vel=76)
    sn2.pattern(B(55), 24, S2, vel=64)
    sn1.pattern(B(55), 24, {"tambourine": "......x.......x."}, vel=46)
    fd.pattern(B(55), 24, FD, vel=86)
    for bar in (62, 70):
        sn1.roll(B(bar, 3), 1.0, "snare", vel0=36, vel1=80, rate=0.0625)
    boom.hit(B(55), "boom", vel=80)
    boom.hit(B(63), "boom", vel=72)
    boom.hit(B(71), "boom", vel=76)
    timp.note(B(55), "G2", 2, vel=72)
    timp.note(B(71), "G2", 2, vel=74)
    timp.roll(B(78, 2), 2.0, "D2", vel0=40, vel1=84, rate=0.125)

    # ================================================================ bass riff (A sections): 3+3+2, diatonic
    def riff(bar, vel):
        sg = segs(bar)
        nxt = segs(bar + 1)[0][1]
        if len(sg) == 1:
            r = bass_of(sg[0][1], 2)
            tgt = bass_of(nxt, 2)
            below = max(q for q in SC if q < tgt)
            appr = below if below != r else min(q for q in SC if q > tgt)   # the Dorian neighbour of the target
            if appr % 12 not in {q % 12 for q in chord(sg[0][1], 3)}:
                appr = r + 7                                               # ... if it is in the chord, else the 5th
            bass.note(B(bar), r, 1.0, vel=vel)
            bass.note(B(bar, 1.5), r, 1.0, vel=vel * 0.86)
            bass.note(B(bar, 3), r + 7 if bar % 2 else appr, 1.0, vel=vel * 0.8)
        else:
            for off, sym, d in sg:
                bass.note(B(bar, off), bass_of(sym, 2), min(d, 1.5), vel=vel * (1.0 if off == 0 else 0.88))
                if d >= 2.5:
                    bass.note(B(bar, off + 1.5), bass_of(sym, 2), 1.0, vel=vel * 0.8)
    for bar in list(range(7, 31)) + list(range(55, 81)):
        riff(bar, 80 if bar < 55 else 86)
    bass.note(B(5), "G2", 1.0, vel=66)
    bass.note(B(5, 1.5), "G2", 1.0, vel=58)
    bass.note(B(6), "G2", 1.0, vel=68)
    bass.note(B(6, 1.5), "G2", 1.0, vel=60)
    bass.note(B(6, 3), "D2", 1.0, vel=60)
    for bar in range(7, 31):                     # cello: one held bass note per chord, a floor for the drive
        for off, sym, d in segs(bar):
            vc.note(B(bar, off), bass_of(sym, 2) if bass_of(sym, 2) >= 41 else bass_of(sym, 3), d, vel=64,
                    art="legato")
    vc.curve(B(7), B(31), 76, 96)
    for bar in range(7, 31):                     # dulcimer: tremolo chords and chops, quieter in A1
        dul_drive(bar, 48 if bar < 15 else 54, ghost=bar >= 15, trem_len=1.0 if bar < 15 else 1.25)
    for bar, lo_, hi_ in ((10, "F4", "A4"), (14, "G4", "Bb4"), (18, "F4", "A4"), (19, "G4", "C5")):
        trem(B(bar, 1.5), 1.5, n(lo_), n(hi_), 50, dyn="cresc")

    # ================================================================ stop-time cadence (79-84)
    mel(fid, B(78, 3.25), PICKUP, vel=96, art="legato")
    mel(fid, B(79), "C5:1.5:gu D5:2.5 | F5:.75 E5:.25 D5:.5 C5:2.5", vel=100, art="legato",
        dyn=[1.0, 1.02, 1.04, 1.02, 1.0, 1.04])
    fid.curve(B(79), B(81), 112, 124)
    mel(vla, B(79), "E4:1.5 D4:2.5 | A4:1.5 G4:2.5", vel=90)
    mel(fds, B(79), "E4:1.5 Bb4:2.5 | A4:1.5 E4:2.5", vel=84)
    vla.curve(B(79), B(81), 110, 118)
    fds.curve(B(79), B(81), 104, 112)
    for off, sym, d in ((0, "C", 1.5), (1.5, "Gm", 2.5)):
        vc.note(B(79, off), bass_of(sym, 2) if bass_of(sym, 2) >= 41 else bass_of(sym, 3), d, vel=78,
                art="legato")
    vc.note(B(80), "F2", 1.5, vel=80, art="legato")
    vc.note(B(80, 1.5), "C3", 2.5, vel=80, art="legato")
    vc.curve(B(79), B(81), 108, 118)
    dul_drive(79, 62)
    dul_drive(80, 64)
    sn1.pattern(B(79), 1, S1.split("|")[0], vel=80)
    sn2.pattern(B(79), 1, S2.split("|")[0], vel=68)
    sn1.pattern(B(80), 1, "X..g.gx..g..", vel=82, steps=16)
    sn1.roll(B(80, 3), 1.0, "snare", vel0=40, vel1=96, rate=0.0625, accent_end=False)
    sn2.pattern(B(80), 1, "..o..o..o.o.", vel=70, steps=16)
    fd.pattern(B(79), 2, FD, vel=88)
    # bar 81: three band hits on the 3+3+2 accents, the top line falling C-Bb-A; the drones stop for them
    hits = [(0.0, "C", "C5", "E4", "G4", "C3", "C3", "C2"), (1.5, "Gm", "Bb4", "D4", "G4", "G2", "Bb2", "Bb1"),
            (3.0, "F", "A4", "C4", "F4", "F2", "F2", "F1")]
    for off, sym, top, ds, va, cl, bs, cbn in hits:
        b = B(81, off)
        fid.note(b, top, 0.6, vel=108, art="marcato")
        fds.note(b, ds, 0.6, vel=96, art="marcato")
        vla.note(b, va, 0.6, vel=100, art="marcato")
        vc.note(b, cl, 0.6, vel=100, art="marcato")
        bass.note(b, bs, 0.6, vel=104)
        cb.note(b, cbn, 0.6, vel=92, art="marcato")
        vo = voicing(sym, lo=55)
        dul.chord(b, vo + [vo[0] + 12], 0.5, vel=80, strum=0.01, art="staccato")
        sn1.hit(b, "snare", vel=104)
        sn2.hit(b, "snare2", vel=86)
        fd.hit(b, "dum", vel=104)
        timp.note(b, {"C": "C3", "Gm": "G2", "F": "F2"}[sym], 0.6, vel=88)
    for t in (fid, fds, vla, vc, cb):
        t.expr(B(81), 118)
    # bar 82: one struck G (an open fifth) with the cannon; the bowed parts hold, then stop together on bar 84
    hold = 8.0
    g = B(82)
    fid.note(g, "D5", hold, vel=110, art="tenuto")
    fds.note(g, "G4", hold, vel=100, art="tenuto")
    vla.note(g, "D4", hold, vel=104, art="tenuto")
    vc.note(g, "G2", hold, vel=106, art="tenuto")
    cb.note(g, "G1", hold, vel=90, art="tenuto")
    pipe.drone(g, g + hold, ["G3", "D4"], vel=86)
    for t, v in ((fid, 118), (fds, 110), (vla, 114), (vc, 116), (cb, 108), (pipe, 108)):
        t.curve(g, g + hold, v, v - 8, "lin")
    bass.note(g, "G2", 2.0, vel=100)
    horn(82, ["G3", "D4"], ["G2", "G3"], durs=(1.5, 6.5), vel=86)  # the last signal over the struck G
    dul.chord(g, ["G3", "D4", "G4", "D5", "G5"], 12.0, vel=92, strum=0.025, art="ring")
    sn1.flam(g, "snare", vel=108)
    sn2.flam(g, "snare2", vel=92)
    fd.hit(g, "doum", vel=116)
    timp.note(g, "G2", 10.0, vel=96)
    boom.hit(g, "boom", vel=96)
    boom.hit(B(84, 1), "boom2", vel=54)                         # one far answer from the hills
    p.set_end(B(84, 1))                     # the strike has rung into the room by here; the tail is the room
    return p


if __name__ == "__main__":
    print(build().compile().summary())
