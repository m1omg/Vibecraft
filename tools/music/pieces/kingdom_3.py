#!/usr/bin/env python3
"""Kingdom 3, "Linden Curfew" (assets/audio/music/kingdom_3.ogg). A Dorian, 84 BPM, 3/4, about 3:26.

Composer's note. Form (bars, 1-based): intro 1-10 | A 11-42 (two 16-bar periods) | B 43-58 | interlude 59-70 |
A' 71-86 | coda 87-94. The only 3/4 piece of the set: an evening air over a soft hurdy-gurdy drone (A-E) and a
frame-drum heartbeat. The fiddle's tune is the Wheel stretched to the waltz (A-B-C in quarters, D and E held a bar
each, bars 11-13); the antecedent turns on the Dorian F# and stops on a half cadence on Em (bar 18), the consequent
climbs to the high A (bar 22) and closes with the Wheel's answer, D falling to A, over the Dorian IV-i (D to Am);
a soft viola second voice holds under its consequent. The second period is the air with a lilt (dotted quarter
and eighth), eighth-note passing tones and pickups into its phrases, ornamented (slides, grace notes, a turn),
under a cello counter-line in contrary motion; it closes stepwise. B moves to D, the kingdom's home key (the
homesick turn): the fiddle states the Wheel's head and its sequence, inversion and fall in 2-bar phrases, its held
notes turning, re-bowing and sliding while a single far horn answers each with a two-note call. The interlude is
the dulcimer alone, slower (78 BPM), sparse, playing the Wheel in retrograde and the falling-fourth answer with
space around it. A' is a variation: the air in the viola an octave down under an ornamented fiddle descant, then
a new consequent in the fiddle (an arpeggio rise to the high A and a stepwise close D-C-B-A). In the coda the
dulcimer recalls the Wheel's head, the fiddle falls gently to A, and the far horn has the last word, the falling
fifth E-A. Arc: low intensity throughout; A2 and A' are the warmest, the interlude the quietest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import bass_of, dulcimer_bar, mel  # noqa: E402
from score import Piece  # noqa: E402

A_CHORDS = ["Am", "D", "C", "Em", "G", "Em", "Bm", "Em", "Am", "D", "C", "D", "C", "Am", "D", "Am"]
NEW_CON_CHORDS = ["Am", "D", "C", "D", "Am", "Em", "D", "Am"]
HARMONY = {}
for i, c in enumerate(["Am", "Am", "Am", "G", "D", "Am", "Em", "Am", "G", "Em"]):
    HARMONY[1 + i] = c
for base in (11, 27, 71):
    for i, c in enumerate(A_CHORDS):
        HARMONY[base + i] = c
for i, c in enumerate(NEW_CON_CHORDS):
    HARMONY[79 + i] = c
for i, c in enumerate(["D", "G", "D", "D", "Em", "D", "C", "G", "D", "C", "Em", "Em", "C", "G", "Em", "Em"]):
    HARMONY[43 + i] = c
for i, c in enumerate(["Am", "Em", "G", "Am", "D", "C", "Em", "Am", "Am", "D", "Am", "Am"]):
    HARMONY[59 + i] = c
for i, c in enumerate(["Am", "D", "D", "Am", "Am", "Am", "Am", "Am"]):
    HARMONY[87 + i] = c

TUNE_A1 = ("A4:1 B4:1 C5:1 | D5:3:s | E5:3 | G5:1 F#5:1 E5:1 | D5:2 C5:1 | B4:1.5 A4:.5 B4:.5 C5:.5 | D5:3 | "
           "B4:2 G4:.5 B4:.5 | "
           "A4:1 B4:1 C5:1 | D5:3 | E5:2 G5:1 | A5:2 G5:1 | E5:2 D5:1 | C5:2 B4:.5 C5:.5 | D5:3:gu | A4:3")
# A2: the same air with a lilt (dotted quarter + eighth), eighth-note passing tones and pickups into the phrases
TUNE_A2 = ("A4:1.5 B4:.5 C5:1 | D5:2:s C5:.5 D5:.5 | E5:3:m | G5:1.5:gu F#5:.5 E5:1 | "
           "D5:1.5 E5:.5 D5:.5 C5:.5 | B4:1 C5:1 D5:1 | D5:1.5 E5:.5 F#5:1 | B4:2:s A4:.5 G4:.5 | "
           "A4:1.5 B4:.5 C5:1 | D5:2:s C5:.5 D5:.5 | E5:1.5 F#5:.5 G5:1 | A5:2:gd G5:.5 F#5:.5 | "
           "G5:2 E5:.5 D5:.5 | E5:1.5 D5:.5 C5:1 | D5:2:t C5:.5 B4:.5 | A4:3")
# A': the air in the viola, an ornamented fiddle descant above it, then a new consequent in the fiddle
TUNE_LOW = "A3:1 B3:1 C4:1 | D4:3:s | E4:3 | G4:1 F#4:1 E4:1 | D4:2 C4:1 | B3:2 C4:1 | D4:3 | B3:3"
DESCANT = ("A5:2:gd G5:.5 E5:.5 | F#5:3:m | G5:2 E5:1 | E5:1 F#5:1 G5:1 | G5:2:t A5:.5 G5:.5 | G5:2 E5:1 | "
           "F#5:3:m | E5:2:s D5:.5 B4:.5")
NEW_CON = ("A4:1 C5:1 E5:1 | F#5:1.5:m E5:.5 D5:1 | G5:2:gu E5:1 | D5:1 F#5:1 G5:.5 A5:.5 | A5:2:gd E5:1 | "
           "G5:1 A5:.5 G5:.5 E5:1 | D5:1.5 C5:.5 B4:1 | A4:3")
NEW_CON_VLA = "E4:3 | F#4:3 | G4:3 | D4:3 | E4:3 | B3:3 | F#4:1.5 E4:.5 D4:1 | C4:3"
A1_VLA = "E4:3 | F#4:3 | E4:3 | D4:3 | G4:3 | E4:3 | F#4:3 | E4:3"          # a soft second voice, A1 bars 19-26
COUNTER = ("A3:3 | F#3:3 | E3:3 | G3:3 | B3:2 A3:1 | G3:3 | F#3:3 | E3:3 | "
           "E3:3 | F#3:3 | G3:2 E3:1 | F#3:3 | G3:3 | E3:2 C3:1 | F#3:3 | E3:3")


def build():
    p = Piece("kingdom_3", seed=3303, bpm=84, meter=(3, 4), key="A", mode="dorian")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 2.0, (200.0, 220.0)   # the tail is the room's real decay
    p.out = "assets/audio/music/kingdom_3.ogg"

    def B(bar, beat=0.0):
        return p.at(bar - 1, beat)

    hurdy = p.track("hurdy", P.HURDY.variant(gain_db=-9.0, synth_params=dict(P.HURDY.synth_params, buzz=0.3)))
    dul = p.track("dulcimer", P.DULCIMER.variant(gain_db=-6.0))
    fid = p.track("fiddle", P.FIDDLE.variant(vibrato=dict(P.BOW_VIB, depth=0.15, delay=0.3)))
    vla = p.track("viola", P.VIOLA.variant(gain_db=-2.0))
    vc = p.track("cello", P.CELLO.variant(gain_db=-3.0))
    horn = p.track("horn", P.HORNS.variant(pan=-0.5, reverb=0.8, gain_db=-8.0))
    fd = p.track("heartbeat", P.FRAME_DRUM.variant(name="heartbeat", gain_db=-9.0, pan=-0.05,
                                                   synth_params={"size": 0.9, "skin": 0.7, "ring": 1.1}))

    p.section("intro", 10)
    p.section("A1 air", 16)
    p.section("A2 air + cello", 16)
    p.section("B horn answers (D)", 16)
    p.section("interlude dulcimer", 12)
    p.section("A' air", 16)
    p.section("coda", 8)

    for bar in (11, 19, 27, 35, 47, 51, 55, 59, 71, 79, 87):
        p.breathe(B(bar), beats=1.5, depth=0.05)
    p.ramp(B(59), B(61), 84, 78)
    p.ramp(B(69), B(71), 78, 84)
    p.rit(B(89), B(95), to=0.8)

    # ================================================================ drone
    hurdy.drone(B(1), B(43), ["A2", "E3"], vel=74)
    hurdy.drone(B(43), B(58, 2), ["D3", "A3"], vel=72)
    hurdy.drone(B(71), B(95), ["A2", "E3"], vel=74)
    hurdy.curve(B(1), B(4), 20, 84)
    hurdy.curve(B(11), B(27), 84, 88)
    hurdy.curve(B(27), B(42), 88, 96)
    hurdy.curve(B(42), B(43), 96, 70)
    hurdy.curve(B(43), B(45), 70, 86)
    hurdy.curve(B(55), B(58, 2), 86, 20)
    hurdy.curve(B(71), B(73), 30, 90)
    hurdy.curve(B(79), B(87), 92, 98)
    hurdy.curve(B(87), B(95), 96, 14)

    # ================================================================ dulcimer: the floor under the air
    figs = {range(1, 11): ("open3", 44), range(11, 27): ("lilt", 48), range(27, 43): ("lilt2", 52),
            range(43, 59): ("open3", 46), range(71, 79): ("lilt", 50), range(79, 87): ("lilt2", 54)}
    for rng, (fig, v) in figs.items():
        for bar in rng:
            if bar <= 2:
                continue
            sym = HARMONY[bar]
            dulcimer_bar(dul, B(bar), sym, fig, vel=v, octave=3, beats=3.0, ring=2.2 if fig == "open3" else 1.8,
                         accent=6 if fig != "open3" else 3)
    mel(dul, B(9), "E5:1 D5:1 C5:1 | B4:3:o", vel=56)                  # a falling pre-echo into the air

    # ================================================================ A1 (11-26): the air, fiddle alone
    mel(fid, B(11), TUNE_A1, vel=72, dyn="arch")
    for s, e, lo, hi in ((11, 15, 70, 98), (15, 19, 80, 100), (19, 23, 76, 108), (23, 27, 90, 70)):
        fid.swell(B(s), B(e), lo, hi, peak=0.55) if s != 23 else fid.curve(B(s), B(e), lo, hi)
    mel(vla, B(19), A1_VLA, vel=54, dyn="arch")                     # pp: a second voice under the held notes
    vla.swell(B(19), B(27), 52, 78, peak=0.55)

    # ================================================================ A2 (27-42): ornamented, cello counter-line
    mel(fid, B(27), TUNE_A2, vel=78, dyn="arch")
    for s, e, lo, hi in ((27, 31, 76, 104), (31, 35, 84, 106), (35, 39, 82, 116), (39, 43, 100, 74)):
        fid.swell(B(s), B(e), lo, hi, peak=0.6) if s != 39 else fid.curve(B(s), B(e), lo, hi)
    mel(vc, B(27), COUNTER, vel=66, dyn="arch")
    vc.swell(B(27), B(35), 70, 96, peak=0.6)
    vc.swell(B(35), B(43), 74, 100, peak=0.5)

    # ================================================================ B (43-58): in D; a far horn answers the fiddle
    phrases = [  # (bar, fiddle phrase, horn call): the held notes turn, re-bow and slide while the horn answers
        (43, "D5:1 E5:1 F#5:1 | G5:2:t A5:.5 G5:.5 | F#5:2:s", ["D4", "A3"]),     # the Wheel's head in D;
        (47, "E5:1 F#5:1 G5:1 | A5:2:m G5:.5 F#5:.5 | G5:2:s", ["C4", "G3"]),     # a step higher (sequence)
        (51, "A5:1 G5:1 F#5:1 | E5:2:t D5:.5 E5:.5 | G5:2:s", ["B3", "E3"]),      # inverted: falling
        (55, "G5:1.5 F#5:.5 E5:1 | D5:1 E5:.5 D5:.5 C5:1", ["E4", "B3"]),         # half cadence on E
    ]
    for bar, phrase, call in phrases:
        mel(fid, B(bar), phrase, vel=74, dyn="arch")           # the held note fades under the horn
        fid.swell(B(bar), B(bar + 2, 2), 70, 100, peak=0.5)
        horn.notes_seq(B(bar + 2), call, [3.0, 4.5], vel=72, art="legato")
    mel(fid, B(57), "B4:2 A4:.5 B4:.5 | B4:2:s G4:1", vel=66)
    fid.curve(B(57), B(59), 86, 64)
    for bar in range(43, 59, 2):
        r = bass_of(HARMONY[bar], 2)
        vc.note(B(bar), r if r >= 41 else r + 12, 6, vel=60, art="legato")
    vc.curve(B(43), B(51), 64, 84)
    vc.curve(B(51), B(59), 84, 60)

    # ================================================================ interlude (59-70): dulcimer alone, sparse
    # the Wheel in retrograde (E-D-C-B-A) and the answer (D-A), with space around every phrase
    mel(dul, B(59), "A3:3:o | r:3 | G3:3:o | r:3 | D4:3:o | C4:3:o | E3:3:o | A3:3:o | A3:3:o | D4:3:o | A3:3:o",
        vel=54)
    mel(dul, B(59), "E4:1 A4:1 C5:1 | B4:3:o | D4:1 G4:1 B4:1 | A4:3:o | D4:1 F#4:1 A4:1 | E5:1 D5:1 C5:1 | "
                    "B4:3:o | A4:3:o | C5:1 E5:1 A5:1 | D5:3:o | A4:3:o | r:1 E4:1 G4:1", vel=66, dyn="arch")
    hurdy.drone(B(59), B(71), ["A2", "E3"], vel=60)               # the drone sinks to almost nothing
    hurdy.curve(B(59), B(60), 64, 56)
    hurdy.curve(B(68), B(71), 56, 70)

    # ================================================================ A' (71-86): the air once more
    mel(vla, B(71), TUNE_LOW, vel=80, dyn="arch")                  # the air in the viola ...
    vla.swell(B(71), B(75), 86, 108, peak=0.55)
    vla.swell(B(75), B(79), 88, 110, peak=0.55)
    mel(fid, B(71), DESCANT, vel=70, dyn="arch")                    # ... under an ornamented fiddle descant
    fid.swell(B(71), B(75), 66, 92, peak=0.55)
    fid.swell(B(75), B(79), 70, 96, peak=0.55)
    mel(fid, B(79), NEW_CON, vel=78, dyn="arch")                    # a new consequent, closing D-C-B-A
    fid.swell(B(79), B(83), 82, 112, peak=0.7)
    fid.curve(B(83), B(87), 104, 72)
    mel(vla, B(79), NEW_CON_VLA, vel=66, dyn="arch")
    vla.curve(B(79), B(87), 86, 70)
    for bar in range(71, 87):
        r = bass_of(HARMONY[bar], 2)
        vc.note(B(bar), r if r >= 41 else r + 12, 3, vel=58, art="legato")
    vc.curve(B(71), B(79), 60, 80)
    vc.curve(B(79), B(87), 80, 70)
    horn.notes_seq(B(77), ["B3", "E3"], [3.0, 3.0], vel=66, art="legato")     # far answer at the half cadence
    horn.notes_seq(B(85), ["D4", "A3"], [3.0, 4.0], vel=64, art="legato")     # ... and at the close

    # ================================================================ coda (87-94): settle on A
    mel(dul, B(87), "A4:1 B4:1 C5:1 | D5:3:o", vel=54)              # the Wheel's head, once more
    mel(fid, B(89), "F#5:1.5 E5:.5 D5:1 | C5:2 B4:1 | A4:3", vel=64, dyn="dim")   # a lilting fall to A
    fid.curve(B(89), B(92), 82, 52)
    mel(vla, B(89), "D4:3 E4:6", vel=56)
    vla.curve(B(89), B(92), 72, 44)
    dul.chord(B(91), ["A3", "E4", "A4", "C5", "E5"], 9, vel=52, strum=0.06, art="ring")
    vc.note(B(87), "A2", 15, vel=56, art="legato")
    vc.curve(B(87), B(94), 76, 30)
    horn.notes_seq(B(92), ["E3", "A2"], [3.0, 6.0], vel=58, art="legato")     # the last word: the far horn, E-A

    # ================================================================ heartbeat (very soft)
    fd.pattern(B(5), 6, "x.o...", vel=42)
    fd.pattern(B(11), 32, "x.o...", vel=46)
    fd.pattern(B(43), 16, "x.....", vel=44)
    for bar in range(60, 71, 2):
        fd.hit(B(bar), "dum", vel=32)
    fd.pattern(B(71), 16, "x.o...", vel=48)
    fd.pattern(B(87), 5, "x.....", vel=38)
    fd.hit(B(92), "doum", vel=34)
    p.set_end(B(95))
    return p


if __name__ == "__main__":
    print(build().compile().summary())
