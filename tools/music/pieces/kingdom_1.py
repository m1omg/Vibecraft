#!/usr/bin/env python3
"""Kingdom 1, "Market-Day Muster" (assets/audio/music/kingdom_1.ogg). D Mixolydian, 92 BPM, 4/4, about 3:27.

Composer's note. Form (bars, 1-based): intro 1-8 | A 9-24 (two 8-bar periods) | B "muster" 25-40 | interlude 41-48 |
retransition 49-52 | A' 53-68 | outro 69-76. The fiddle's theme is the Wheel (D-E-F#, G, A) answered by the falling
fourth G-D (bars 9-10); bars 11-12 sequence it a third up to the Mixolydian C and close on a half cadence on A (Am),
and bars 13-16 let the Wheel climb past the fifth to the octave before the answer brings it home (C-Am-Dsus4-D).
In B the harmony turns to G: two far-off horns call in two-note signals (the falling minor third D-B, the rising
fourth D-G) and the viola answers above them (G4-E5, the cello an octave below, the fiddle joining in unison) with
the Wheel inverted in a dotted march rhythm, over a field-snare ostinato and a hurdy-gurdy re-tuned low to D2-G2;
in its second half the tune drops an octave under a fiddle descant. The interlude drops the
drone and the drums: dulcimer and plucked fiddle trade the Wheel in diminution, then run it in stretto a third apart.
The retransition fragments the Wheel's first three notes in a rising sequence over an A pedal (G/A) into A', where
the second period lifts the Wheel an octave (climax at bar 66, the top A) with the hum and the timpani. The outro
plays the Wheel and its answer in augmentation and resolves on D. Arc: soft intro, A rising, B strongest so far,
interlude soft, A'2 peak, outro fading to the drone.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import bass_bar, bass_of, chord as _ch, coups, dulcimer_bar, mel  # noqa: E402
from score import Mode, Piece, wheel, wheel_answer  # noqa: E402

# Harmony, bar by bar (1-based). "A:2 B:2" = A for two beats then B; plain tokens split the bar evenly.
HARMONY = {
    1: "D", 2: "D", 3: "D", 4: "C/D", 5: "G/D", 6: "D", 7: "Am7", 8: "D",
    9: "D", 10: "G D", 11: "Em:3 C:1", 12: "C Am", 13: "D", 14: "G", 15: "C Am", 16: "Dsus4:1 D:3",
    17: "D", 18: "G D", 19: "Em:3 C:1", 20: "C Am", 21: "Am:1.5 G:1.5 C:1", 22: "C G", 23: "C Am", 24: "Dsus4:1 D:3",
    25: "G", 26: "G", 27: "Em", 28: "Am D", 29: "G", 30: "C G", 31: "Am D", 32: "G",
    33: "G", 34: "G", 35: "Em", 36: "Am D", 37: "G", 38: "C G", 39: "C", 40: "D",
    41: "D", 42: "G", 43: "D", 44: "Am", 45: "D", 46: "C", 47: "G", 48: "Dsus4:2 D:2",
    49: "Am/A", 50: "G/A", 51: "Am7/A", 52: "G/A",
    53: "D", 54: "G D", 55: "Em:3 C:1", 56: "C Am", 57: "D", 58: "G", 59: "C Am", 60: "Dsus4:1 D:3",
    61: "D", 62: "G D", 63: "D:1.5 C:1.5 G:1", 64: "G Am", 65: "Am:1.5 G:1.5 C:1", 66: "C:1 D:3", 67: "C Am", 68: "Dsus4:1 D:3",
    69: "D", 70: "D", 71: "G/D", 72: "D", 73: "D", 74: "C/D", 75: "G/D", 76: "D",
}


def segs(bar):
    """[(beat_offset, symbol, beats)] for a bar of HARMONY."""
    toks = HARMONY[bar].split()
    out, b = [], 0.0
    even = 4.0 / len(toks)
    for t in toks:
        sym, d = (t.split(":")[0], float(t.split(":")[1])) if ":" in t else (t, even)
        out.append((b, sym, d))
        b += d
    return out


def build():
    p = Piece("kingdom_1", seed=1101, bpm=92, meter=(4, 4), key="D", mode="mixolydian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 2.0, (200.0, 220.0)   # the tail is the room's real decay
    p.out = "assets/audio/music/kingdom_1.ogg"

    def B(bar, beat=0.0):            # 1-based bar numbers, as in the composer's note
        return p.at(bar - 1, beat)

    # the bass approach notes stay in the mode: D Mixolydian in A, G Mixolydian (F natural) in the muster
    SC_D = p.mode.scale(28, 62)
    SC_G = Mode("G", "mixolydian").scale(28, 62)

    hurdy = p.track("hurdy", P.HURDY)
    dul = p.track("dulcimer", P.DULCIMER)
    fid = p.track("fiddle", P.FIDDLE)
    fpz = p.track("fiddle_pizz", P.BASS_PIZZ.variant(name="fiddle_pizz", pan=-0.22, gain_db=-1.0, lo=55, hi=96,
                                                     eq=[("hp", 220), ("peak", 2600, -2.0, 1.0),
                                                         ("highshelf", 8000, -2.0)], reverb=0.3,
                                                     color=(240, 210, 120)))
    vla = p.track("viola", P.VIOLA)
    vc = p.track("cello", P.CELLO)
    bass = p.track("bass", P.BASS_PIZZ)
    h1 = p.track("horn1", P.HORNS)
    h2 = p.track("horn2", P.HORNS.variant(pan=-0.22, gain_db=-11.0))
    sn = p.track("snare", P.SNARE)
    fd = p.track("frame_drum", P.FRAME_DRUM)
    hum = p.track("hum", P.HUM.variant(gain_db=-10.0))
    timp = p.track("timpani", P.TIMPANI.variant(gain_db=-10.0))

    intro = p.section("intro", 8)
    a1 = p.section("A1 theme", 8)
    a2 = p.section("A2 theme + counter", 8)
    b1 = p.section("B1 muster", 8)
    b2 = p.section("B2 muster + descant", 8)
    inter = p.section("interlude", 8)
    retr = p.section("retransition", 4)
    r1 = p.section("A'1", 8)
    r2 = p.section("A'2 climax", 8)
    out = p.section("outro", 8)

    # ---- tempo: breaths at the period ends, a ritardando into the last chord
    for bar in (9, 17, 25, 33, 41, 49, 53, 61, 69):
        p.breathe(B(bar), beats=1.0, depth=0.035)
    p.breathe(B(25), beats=2.0, depth=0.05)
    p.rit(B(73), B(77), to=0.78)

    # ================================================================ hurdy-gurdy: the floor and the pulse
    hurdy.drone(B(1), B(25), ["D2", "A2"], vel=88)
    hurdy.drone(B(25), B(40, 2), ["D2", "G2"], vel=88)          # re-tuned to G for the muster, under the tune
    hurdy.drone(B(40, 2), B(41), ["D2", "A2"], vel=84)
    hurdy.drone(B(49), B(77, 3), ["D2", "A2"], vel=88)
    hurdy.curve(B(1), B(3), 25, 92)
    hurdy.curve(B(9), B(16), 86, 96)
    hurdy.curve(B(17), B(24), 100, 106)
    hurdy.curve(B(25), B(40), 104, 112)
    hurdy.curve(B(40, 2), B(41), 100, 40)
    hurdy.curve(B(49), B(52, 3), 20, 104)
    hurdy.curve(B(53), B(68), 106, 116)
    hurdy.curve(B(69), B(73), 108, 92)
    hurdy.curve(B(73), B(77, 3), 92, 18)
    hurdy.note(B(2, 2), "D3", 0.3, vel=58, stroke="buzz")       # the wheel catching
    for bar in range(5, 41):
        b0 = B(bar)
        pitch = "D3"                                            # the trompette stays on D (the fifth of G)
        if bar < 9:
            coups(hurdy, b0, 4, pitch, 66, at=(1, 3))
        elif bar < 17:
            coups(hurdy, b0, 4, pitch, 76, at=(1, 3))
        elif bar < 25:
            coups(hurdy, b0, 4, pitch, 80, at=(1, (2.5, 0.7), 3, (3.5, 0.66)))
        else:
            coups(hurdy, b0, 4, pitch, 84, at=(1, (1.5, 0.6), 3, (3.5, 0.6)))
    for bar in range(53, 69):
        coups(hurdy, B(bar), 4, "D3", 86, at=(1, (1.5, 0.6), 3, (3.5, 0.66)))
    coups(hurdy, B(69), 4, "D3", 66, at=(1,))

    # ================================================================ intro (1-8): drone, dulcimer, the inverted Wheel
    dul.chord(B(1), ["D3", "A3", "D4"], 4, vel=44, strum=0.03, art="ring")
    dulcimer_bar(dul, B(3), "D", "wide", vel=48, octave=3, ring=3.0)
    dulcimer_bar(dul, B(4), "C", "wide", vel=48, octave=3, ring=3.0)
    dulcimer_bar(dul, B(5), "G", "roll", vel=50, octave=3, dyn="cresc")
    dulcimer_bar(dul, B(6), "D", "roll2", vel=54, octave=3)
    dulcimer_bar(dul, B(7), "Am7", "roll", vel=54, octave=3, beats=3.0)
    # the Wheel upside down (A-G-F#-E-D) cascades into the fiddle's entry
    dul.play(wheel().invert(2), B(7, 3), octave=1, vel=64, dyn="dim", art="ring")
    dul.note(B(8), "D3", 3, vel=50, art="ring")
    dul.note(B(8, 1), "A3", 2.5, vel=44, art="ring")
    bass.note(B(5), "G2", 2, vel=62)
    bass.note(B(6), "D2", 2, vel=66)
    bass.note(B(7), "A2", 2, vel=62)
    bass.note(B(8), "D2", 2, vel=66)
    fd.pattern(B(7), 2, {"dum": "x.......o.......|x.......o...o...", "tek": "........g...g...|....g...g..gg.g.g"},
               vel=56)

    # ================================================================ A (9-24): the theme on the fiddle
    THEME_ANT = ("D4:.5 E4:.5 F#4:.5 G4:1.5 A4:2 G4:1 D4:2 | "               # the Wheel and its answer
                 "F#4:.5 G4:.5 A4:.5 B4:1.5:m C5:2 B4:.5 G4:.5 A4:2")        # the Wheel a third up: half cadence
    THEME_CON = ("D4:.5 E4:.5 F#4:.5 G4:1.5:gu A4:2 B4:.5 C5:.5 D5:2 | "      # the Wheel climbs past the fifth
                 "C5:1:t B4:.5 A4:.5 B4:.5 C5:.5 A4:1 G4:1 D4:3")             # ... and the answer brings it home
    mel(fid, B(9), THEME_ANT, vel=78, dyn="arch")
    mel(fid, B(13), THEME_CON, vel=82, dyn="arch")
    for s, e, lo, hi in ((9, 11, 76, 102), (11, 13, 82, 108), (13, 15, 84, 112), (15, 17, 100, 78)):
        fid.swell(B(s), B(e), lo, hi, peak=0.55) if s != 15 else fid.curve(B(s), B(e), lo, hi)

    # A2: ornamented; the consequent turns the Wheel on the fifth (A-B-C-D-E) and closes the same way
    mel(fid, B(17), "D4:.5 E4:.5 F#4:.5 G4:1.5:m A4:2:s G4:1 D4:2:gd | "
                    "F#4:.5 G4:.5 A4:.5 B4:1.5:t C5:2 B4:.5 G4:.5 A4:2:m", vel=84, dyn="arch")
    fid.play(wheel().transpose(4).ornament(3, "mordent"), B(21), vel=88, art="legato", dyn="cresc")
    mel(fid, B(22, 1), "D5:.5 C5:.5 B4:1 A4:1 | C5:1:t B4:.5 A4:.5 B4:1 A4:1 G4:1 D4:3", vel=86, dyn="dim")
    for s, e, lo, hi in ((17, 19, 84, 108), (19, 21, 88, 112), (21, 23, 90, 118)):
        fid.swell(B(s), B(e), lo, hi, peak=0.55)
    fid.curve(B(23), B(25), 108, 84)

    # viola counter-melody: contrary motion against the theme, longer notes
    mel(vla, B(17), "A3:2 G3:1.5 F#3:.5 | G3:1 A3:1 B3:2 | D4:2 C4:1 B3:1 | A3:1 G3:1 E3:2 | "
                    "C4:2 B3:1 G3:1 | G3:1 A3:1 B3:1 C4:1 | E4:2 C4:2 | D4:1 F#3:3", vel=72, dyn="arch")
    vla.swell(B(17), B(21), 76, 100)
    vla.swell(B(21), B(25), 80, 106)

    # dulcimer, bass, cello under A
    for bar in range(9, 25):
        for off, sym, d in segs(bar):
            fig = ("roll" if bar % 2 else "roll2") if d >= 4 else "roll"
            dulcimer_bar(dul, B(bar, off), sym, fig, vel=52 if bar < 17 else 58, octave=3, beats=d,
                         ring=1.7)
    for bar in range(9, 25):
        sg = segs(bar)
        nxt = segs(bar + 1)[0][1]
        if len(sg) == 1:
            bass_bar(bass, B(bar), sg[0][1], nxt, "march", vel=76 if bar < 17 else 82, scale=SC_D)
        else:
            for k, (off, sym, d) in enumerate(sg):
                bass_bar(bass, B(bar, off), sym, None, "root", vel=76 if bar < 17 else 82, beats=min(d, 1.5))
    for bar in range(17, 25):                     # cello: sustained roots and thirds, the bowed floor
        for off, sym, d in segs(bar):
            r = bass_of(sym, 3)
            if r > 55:
                r -= 12
            vc.note(B(bar, off), r, d, vel=66, art="legato")
    vc.curve(B(17), B(21), 64, 88)
    vc.curve(B(21), B(25), 88, 78)

    fd.pattern(B(9), 8, {"dum": "x.......x.....o.", "tek": "..g.o.g...g.o.g."}, vel=54)
    fd.pattern(B(17), 8, {"dum": "x..o....x..o..o.", "tek": "..g.x.g...g.x.gg"}, vel=70)
    hum.note(B(21), "D3", 16, vel=60, vowel="m")
    hum.note(B(21), "A2", 16, vel=54, vowel="m")
    hum.swell(B(21), B(25), 30, 92, peak=0.6)

    # ================================================================ B (25-40): the muster in G
    def horn_call(bar, top, low, durs=(1.5, 2.5), beat=0.0, vel=74):
        """Two horns, two notes each: a signal, not a fanfare."""
        h1.notes_seq(B(bar, beat), top, list(durs), vel=vel, art="legato")
        h2.notes_seq(B(bar, beat), low, list(durs), vel=vel * 0.92, art="legato")

    MARCH_ANS1 = "D4:.75 C4:.25 B3:.5 A3:1.5 G3:1"          # the Wheel inverted (D-C-B-A-G), dotted
    MARCH_ANS2 = "E4:.75 D4:.25 C4:.5 B3:1.5 A3:1"          # ... a step higher: half cadence on D
    MARCH_TUNE = ("G3:.5 A3:.5 B3:.5 C4:1.5 D4:1 | D4:.75 E4:.25 D4:.5 C4:.5 B3:1 G3:1 | "   # the Wheel on G
                  "A3:.75 B3:.25 C4:.5 A3:.5 D4:1 C4:1 | B3:1 A3:1 G3:2")
    for base in (25, 33):
        loud = 1.0 if base == 25 else 1.1
        up = 12 if base == 25 else 0          # B1: the tune lies above the horns and the drone (viola G4-E5)
        horn_call(base, ["D4", "B3"], ["B3", "G3"], vel=74 * loud)              # falling minor third
        mel(vla, B(base + 1), MARCH_ANS1, vel=86 * loud, art="normal", tr=up)
        horn_call(base + 2, ["D4", "G4"], ["B3", "D4"], vel=76 * loud)          # rising fourth
        mel(vla, B(base + 3), MARCH_ANS2, vel=88 * loud, art="normal", tr=up)
        if base == 25:
            mel(vla, B(base + 4), MARCH_TUNE, vel=90, art="normal", dyn="arch", tr=up)
            horn_call(base + 7, ["C4", "G3"], ["A3", "B3"], durs=(1.0, 3.0), beat=0.0, vel=70)
        else:
            mel(vla, B(base + 4), "G3:.5 A3:.5 B3:.5 C4:1.5 D4:1 | D4:.75 E4:.25 D4:.5 C4:.5 B3:1 G3:1 | "
                                  "C4:.75 D4:.25 E4:.5 C4:.5 G3:1 E4:1 | D4:4", vel=96, art="normal", dyn="arch")
            horn_call(base + 7, ["G3", "D3"], ["B2", "A2"], durs=(1.0, 3.0), vel=78)   # the answer, home on D
    vc.double(vla, B(25), B(41), interval=-12, vel=0.86)         # the cello an octave under the viola's tune
    fid.double(vla, B(26), B(33), interval=0, vel=0.78)           # B1: the fiddle joins the muster in unison
    fid.curve(B(26), B(33), 96, 110)
    vla.curve(B(25), B(33), 112, 120)
    vla.curve(B(33), B(41), 110, 122)
    vc.curve(B(25), B(33), 70, 84)
    vc.curve(B(33), B(41), 100, 112)

    # fiddle descant over the second muster
    mel(fid, B(33), "D5:4 | C5:2 B4:2 | B4:2 D5:2:gu | C5:2 A4:1 C5:1", vel=78, dyn="cresc")
    for s in (33, 34, 35, 36):
        fid.swell(B(s), B(s + 1), 78, 104, peak=0.5)
    mel(fid, B(37), "G4:.5 A4:.5 B4:.5 C5:1.5:m D5:1 | D5:.75 E5:.25 D5:.5 C5:.5 B4:1 G4:1 | "
                    "E5:2:gu C5:1 G4:1 | A4:1 D5:3:s", vel=86, dyn="arch")
    fid.curve(B(37), B(39), 96, 116)
    fid.curve(B(39), B(41), 116, 92)

    for bar in range(25, 41):
        sg = segs(bar)
        nxt = segs(bar + 1)[0][1]
        for off, sym, d in sg:
            dulcimer_bar(dul, B(bar, off), sym, "pulse" if bar < 33 else "roll", vel=52 if bar < 33 else 54,
                         octave=3, beats=d, ring=1.5)                  # under the tune, not above it
        if len(sg) == 1:
            bass_bar(bass, B(bar), sg[0][1], nxt, "march", vel=80, scale=SC_G)
        else:
            for off, sym, d in sg:
                bass_bar(bass, B(bar, off), sym, None, "halves", vel=78, beats=d)

    MARCH = "X..go.g.x.ggo.g.|X..go.g.x.ggr.X."
    sn.roll(B(24, 3), 1.0, "snare", vel0=20, vel1=60, rate=0.0625)
    sn.pattern(B(25), 7, MARCH, vel=72)
    sn.pattern(B(25), 7, {"tambourine": "....o.......o..."}, vel=44)
    sn.roll(B(32), 3.5, "snare", vel0=30, vel1=74, rate=0.0625)
    sn.pattern(B(33), 7, MARCH, vel=78)
    sn.pattern(B(33), 7, {"tambourine": "....x.......x.g."}, vel=50)
    sn.pattern(B(40), 1, "X..go.g.r.r.rrr.", vel=72)
    sn.hit(B(40, 3.75), "snare", vel=60)
    sn.curve(B(25), B(41), 96, 112)
    fd.pattern(B(25), 15, {"dum": "X.......x.......", "tek": "....x.......x..g"}, vel=70)
    fd.pattern(B(40), 1, {"dum": "X.......x...x...", "tek": "....x.......x..."}, vel=80)
    hum.note(B(33), "G2", 16, vel=56, vowel="m")
    hum.note(B(33), "D3", 16, vel=56, vowel="m")
    hum.swell(B(33), B(41), 28, 86, peak=0.5)

    # ================================================================ interlude (41-48): dulcimer and plucked fiddle
    # call and response with the Wheel in diminution, then a stretto a third apart
    dim = wheel().diminish(2)                                   # D-E-F#-G-A in sixteenths and eighths
    dul.play(dim, B(41), octave=1, vel=72, art="normal")
    mel(fpz, B(41, 2.5), "A5:.5 F#5:.5 D5:.5", vel=66)
    fpz.play(dim.transpose(3), B(42), vel=78, art="normal")      # in G: G-A-B-C-D
    mel(dul, B(42, 2.5), "D6:.5 B5:.5 G5:.5", vel=60, art="normal")
    mel(dul, B(43), "F#5:.25 G5:.25 A5:.25 B5:.75 C6:.5 A5:.5 F#5:.5 D5:1", vel=70, art="normal")
    mel(fpz, B(43), "D5:1 r:1 A4:1 r:1", vel=60)
    mel(fpz, B(44), "E5:.25 F#5:.25 G5:.25 A5:.75 G5:.5 E5:.5 C5:.5 A4:1", vel=76)
    mel(dul, B(44), "A4:1:o E5:1:o C5:1:o A4:1:o", vel=54)
    dul.play(dim, B(45), octave=1, vel=72, art="normal")                       # stretto: the dulcimer leads,
    fpz.play(dim.transpose(-2), B(45, 1), octave=1, vel=72, art="normal")      # the pizz follows a beat later
    mel(dul, B(45, 2.5), "B5:.5 A5:.5 F#5:.5", vel=60)
    mel(dul, B(46), "G5:1 E5:.5 C5:.5 G5:1 E5:1", vel=64)
    mel(fpz, B(46), "E5:.5 C5:.5 G4:1 C5:1 r:1", vel=64)
    dul.play(wheel().invert(0).transpose(7).diminish(2), B(47), vel=68, art="normal")   # falling, against ...
    fpz.play(dim.transpose(3), B(47), octave=-1, vel=70, art="normal")              # ... rising: contrary
    mel(dul, B(47, 2.5), "D5:.5 B4:.5 G4:.5", vel=56)
    mel(dul, B(48), "A4:1 G4:1 D4:2:o", vel=60)                  # the answer, in octaves
    mel(fpz, B(48), "A5:1 G5:1 D5:2", vel=62)
    for bar in range(41, 49):                     # low dulcimer and bass: just the roots
        for off, sym, d in segs(bar):
            bass_bar(bass, B(bar, off), sym, None, "root", vel=58, beats=1.0)
    for bar in (41, 43, 45, 47):
        sym = segs(bar)[0][1]
        dul.note(B(bar), _ch(sym, 3)[0], 3, vel=46, art="ring")
    fd.pattern(B(41), 8, {"tek": "..g...g...g..g.g", "dum": "o..............."}, vel=52)

    # ================================================================ retransition (49-52): fragments rising over A
    mel(vla, B(49), "A3:.5 B3:.5 C4:3", vel=76)          # the Wheel's head, a fragment, on the fifth
    mel(fid, B(50), "B4:.5 C5:.5 D5:3", vel=78)          # ... a step higher, answered across the band
    mel(vla, B(51), "C4:.5 D4:.5 E4:3", vel=82)
    mel(fid, B(52), "D5:.5 E5:.5 F#5:1 E5:.5 D5:.5 C5:.5 B4:.5", vel=86, dyn="cresc")
    fid.curve(B(50), B(53), 80, 110)
    vla.curve(B(49), B(52), 80, 104)
    vc.note(B(49), "A2", 16, vel=70, art="legato")
    vc.curve(B(49), B(53), 60, 106)
    bass.note(B(49), "A1", 2, vel=72)
    bass.note(B(50), "A1", 2, vel=74)
    bass.note(B(51), "A1", 2, vel=78)
    bass.note(B(52), "A1", 1, vel=80)
    bass.note(B(52, 2), "A1", 1, vel=82)
    for bar in range(49, 53):
        dulcimer_bar(dul, B(bar), segs(bar)[0][1].split("/")[0], "climb", vel=50 + 3 * (bar - 49), octave=3,
                     ring=1.4, dyn="cresc")
    timp.roll(B(52), 3.0, "A1", vel0=26, vel1=74, rate=0.125)
    sn.roll(B(52), 3.75, "snare", vel0=16, vel1=78, rate=0.0625)
    fd.pattern(B(49), 4, {"dum": "x.......x.......|x.......x.......|x...x...x...x...|x.x.x.x.x.xxxxxx"},
               vel=64)

    # ================================================================ A' (53-68): the full theme, then the climb
    mel(fid, B(53), THEME_ANT.replace("G4:1.5 A4:2", "G4:1.5:m A4:2:s"), vel=90, dyn="arch")
    mel(fid, B(57), THEME_CON, vel=92, dyn="arch")
    vla.double(fid, B(53), B(61), interval=-12, vel=0.8)          # heterophony: plainer, an octave down
    for s, e in ((53, 55), (55, 57), (57, 59)):
        fid.swell(B(s), B(e), 92, 116, peak=0.55)
    fid.curve(B(59), B(61), 112, 96)
    vla.curve(B(53), B(61), 92, 100)
    # A'2: the Wheel an octave up, its inversion, the Wheel on the fifth to the top A, the answer
    fid.play(wheel().ornament(3, "mordent"), B(61), octave=1, vel=96, art="legato", dyn="cresc")
    mel(fid, B(62, 1), "G5:1 D5:2", vel=94)
    fid.play(wheel().invert(0).transpose(2), B(63), octave=1, vel=92, art="legato")
    mel(fid, B(64, 1), "C5:.5 B4:.5 A4:2:m", vel=90)
    fid.play(wheel().transpose(4), B(65), vel=96, art="legato", dyn="cresc")
    mel(fid, B(66, 1), "F#5:.5 G5:.5 A5:2:gd", vel=104)
    mel(fid, B(67), "G5:1:t F#5:.5 E5:.5 F#5:1 E5:1 | G5:1 D5:3", vel=98, dyn="dim")
    fid.curve(B(61), B(66, 2), 104, 127)
    fid.curve(B(66, 2), B(69), 122, 96)
    # viola: counter-melody against the climax (contrary motion, held notes), cello in octaves below
    mel(vla, B(61), "F#4:2 E4:2 | D4:2 F#4:2 | A4:2 G4:1 F#4:1 | E4:2 C4:2 | "
                    "C4:2 D4:1 E4:1 | E4:1 F#4:3 | E4:2 C4:2 | B3:1 A3:3", vel=82, dyn="arch")
    vla.swell(B(61), B(69), 92, 124, peak=0.65)
    for bar in range(53, 69):
        for off, sym, d in segs(bar):
            r = bass_of(sym, 3)
            if r > 55:
                r -= 12
            vc.note(B(bar, off), r, d, vel=74, art="legato")
    vc.curve(B(53), B(66), 96, 116)
    vc.curve(B(66), B(69), 116, 96)
    for bar in range(53, 69):
        sg = segs(bar)
        nxt = segs(bar + 1)[0][1]
        for off, sym, d in sg:
            fig = "roll2" if bar % 2 else "roll"
            dulcimer_bar(dul, B(bar, off), sym, fig, vel=60 if bar < 61 else 64, octave=4 if bar >= 61 else 3,
                         beats=d, ring=1.7)
        if len(sg) == 1:
            bass_bar(bass, B(bar), sg[0][1], nxt, "march", vel=88, scale=SC_D)
        else:
            for off, sym, d in sg:
                bass_bar(bass, B(bar, off), sym, None, "halves", vel=86, beats=d)
    for bar, nt in ((56, "A5"), (64, "A5"), (66, "A5")):   # dulcimer tremolo on the long notes
        dul.tremolo(B(bar, 2), 2.0, nt, rate=0.125, vel=52, dyn="cresc")
    horn_call(56, ["A3", "E3"], ["E3", "C3"], durs=(1.0, 3.0), vel=70)
    horn_call(60, ["G3", "D3"], ["D3", "A2"], durs=(1.0, 3.0), vel=72)
    horn_call(64, ["E3", "A3"], ["C3", "E3"], durs=(1.0, 3.0), vel=76)
    horn_call(68, ["G3", "D3"], ["B2", "A2"], durs=(1.0, 3.0), vel=78)
    sn.pattern(B(53), 8, "o..g..g.o..g.gg.|o..g..g.o.ggr.o.", vel=52)
    sn.pattern(B(61), 7, MARCH, vel=76)
    sn.pattern(B(61), 7, {"tambourine": "....x.......x.g."}, vel=54)
    sn.roll(B(68), 3.0, "snare", vel0=40, vel1=80, rate=0.0625)
    sn.curve(B(53), B(69), 100, 116)
    fd.pattern(B(53), 8, {"dum": "X..o....x..o..o.", "tek": "..g.x.g...g.x.gg"}, vel=80)
    fd.pattern(B(61), 7, {"dum": "X..o....x..o..o.", "tek": "..g.x.g...g.x.gg"}, vel=92)
    fd.pattern(B(68), 1, {"dum": "X...x...x.x.x...", "tek": "..g...g........."}, vel=88)
    hum.note(B(61), "D3", 32, vel=62, vowel="m")
    hum.note(B(61), "A2", 32, vel=58, vowel="m")
    for bar, beat, pitch, d in ((62, 0, "G3", 2), (62, 2, "F#3", 3.5), (63, 1.5, "E3", 1.5),
                                (63, 3, "G3", 3), (64, 2, "A3", 2)):       # the hum's third follows the chords
        hum.note(B(bar, beat), pitch, d, vel=48, vowel="m")
    hum.swell(B(61), B(69), 50, 112, peak=0.7)
    timp.note(B(61), "D2", 2, vel=70)
    timp.roll(B(67, 2), 2.0, "A1", vel0=30, vel1=72, rate=0.125)
    timp.note(B(69), "D2", 3, vel=60)

    # ================================================================ outro (69-76): the Wheel slowly, home on D
    fid.play(wheel().augment(2), B(69), vel=74, art="legato", dyn="dim")
    fid.play(wheel_answer().augment(2).ornament(0, "grace_up"), B(71, 2), vel=70, art="legato")
    fid.curve(B(69), B(73), 96, 80)
    mel(dul, B(73), "D5:.5 E5:.5 F#5:3:o", vel=56)
    mel(fid, B(74), "A4:2 G4:2 | G4:2:gu E4:2 | D4:5", vel=64, dyn="dim")
    fid.curve(B(73), B(77, 1), 84, 56)
    mel(vla, B(69), "A3:8 | B3:4 | A3:4 | F#3:4 | E3:4 | D3:4 | D3:5", vel=62)
    vla.curve(B(69), B(77), 84, 54)
    vc.note(B(69), "D3", 16, vel=62, art="legato")
    vc.note(B(73), "D3", 17, vel=58, art="legato")
    vc.curve(B(69), B(77, 1), 90, 50)
    for bar in range(69, 73):
        sym = segs(bar)[0][1].split("/")[0]
        dulcimer_bar(dul, B(bar), sym, "wide", vel=50 - 2 * (bar - 69), octave=3, ring=3.0)
    dul.note(B(74), "C4", 3, vel=42, art="ring")
    dul.note(B(75), "B3", 3, vel=40, art="ring")
    dul.chord(B(76), ["D3", "A3", "D4", "F#4", "A4", "D5"], 5, vel=50, strum=0.045, art="ring")
    for bar in range(69, 76):
        bass.note(B(bar), "D2", 1.5, vel=62 - 2 * (bar - 69))
    bass.note(B(76), "D2", 4, vel=58)
    fd.pattern(B(69), 6, {"dum": "x.......o.......", "tek": "........g......."}, vel=60)
    fd.hit(B(76), "doum", vel=54)
    hum.note(B(73), "D3", 17, vel=56, vowel="m")
    hum.note(B(73), "A2", 17, vel=52, vowel="m")
    hum.swell(B(73), B(77, 2), 30, 80, peak=0.4)
    p.set_end(B(77))
    return p


if __name__ == "__main__":
    print(build().compile().summary())
