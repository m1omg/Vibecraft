#!/usr/bin/env python3
"""Victory, kingdom (assets/audio/music/victory_kingdom.ogg). D major, 96 BPM, 12.0 s end-screen stinger.

Composer's note. Beats 0-2: a field-snare roll swells to an accent. Beats 2-7: the fiddle plays the Wheel in D
major intact (D-E-F# short, G and A held) with the viola a third below, a breath on the held A; on beat 7 it leaps
the rising fourth A-D with a grace note, where the band lands on the tonic chord together, and the two far horns
answer the leap a beat later with their own A-D signal; the fiddle turns D-C#-D on the held tonic. The dulcimer
strums the chord and runs a sparkle up to F#6, a second snare roll ends on a flam, and the bagpipe drone (A-D)
swells under the held chord. Beats 7-16 are the held D major chord
with a natural decay (the bowed parts and the drone fade with CC11; the dulcimer and the room ring out), so the
score bed can cross-fade in under it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import palette as P  # noqa: E402
from ext_kingdom import mel  # noqa: E402
from score import Piece  # noqa: E402


def build():
    p = Piece("victory_kingdom", seed=4404, bpm=96, meter=(4, 4), key="D", mode="major")
    p.mix = P.MIX_KINGDOM
    p.kind, p.tail_s, p.length_range = "track", 1.8, (11.8, 12.2)
    p.out = "assets/audio/music/victory_kingdom.ogg"

    sn = p.track("snare", P.SNARE.variant(gain_db=-3.0))
    fid = p.track("fiddle", P.FIDDLE)
    vla = p.track("viola", P.VIOLA.variant(gain_db=-3.0))
    vc = p.track("cello", P.CELLO)
    bass = p.track("bass", P.BASS_PIZZ)
    dul = p.track("dulcimer", P.DULCIMER.variant(gain_db=-2.0))
    h1 = p.track("horn1", P.HORNS.variant(gain_db=-7.0))
    h2 = p.track("horn2", P.HORNS.variant(pan=-0.25, gain_db=-9.0))
    pipe = p.track("bagpipe", P.BAGPIPE.variant(gain_db=-5.0, eq=[("hp", 120), ("peak", 880, -3.0, 2.0),
                                                                   ("peak", 1200, -6.0, 1.2),
                                                                   ("peak", 2600, -4.0, 1.0), ("lp", 5000)]))
    fd = p.track("frame_drum", P.FRAME_DRUM)
    p.section("roll + rising phrase", 2)          # bars of 4/4: the phrase lands on beat 7
    p.section("tonic chord", 2)
    p.mark(7.0, "arrival")
    p.fermata(6.0, 1.0, stretch=1.25)             # a breath on the held A before the leap
    p.rit(5.0, 7.0, to=0.92)

    # snare: roll into the phrase, a second roll into the chord, a flam on the arrival
    sn.roll(0.0, 2.0, "snare", vel0=28, vel1=92, rate=0.0625)
    for t, v in ((2.0, 84), (2.75, 30), (3.25, 34), (4.0, 70), (4.5, 30), (5.0, 50), (5.5, 34), (5.75, 38)):
        sn.hit(t, "snare", vel=v)
    sn.roll(6.0, 1.0, "snare", vel0=40, vel1=96, rate=0.0625, accent_end=False)
    sn.flam(7.0, "snare", vel=104)
    sn.hit(7.0, "tambourine", vel=60)

    # the Wheel in D major, intact; the leap of a fourth to the tonic; the viola a third below
    mel(fid, 2.0, "D4:.5 E4:.5 F#4:.5 G4:1.5 A4:2:m | D5:2:gu C#5:.25 D5:5.75", vel=96,
        dyn=[0.86, 0.9, 0.94, 0.98, 1.0, 1.08, 1.0, 1.02])
    mel(vla, 2.0, "B3:.5 C#4:.5 D4:.5 E4:1.5 F#4:2 | A4:8", vel=86, dyn="cresc")
    fid.curve(2.0, 7.0, 96, 124)
    fid.curve(7.0, 9.0, 124, 112)
    fid.curve(9.0, 15.0, 112, 30, "lin")
    vla.curve(2.0, 7.0, 90, 112)
    vla.curve(9.0, 15.0, 108, 26, "lin")

    # horns: one two-note signal answering the fiddle's leap (the rising fourth A-D), a beat later, from afar
    h1.notes_seq(7.0, ["A3", "D4"], [1.0, 7.0], vel=84, art="legato")
    h2.notes_seq(7.0, ["F#3", "A3"], [1.0, 7.0], vel=80, art="legato")
    h1.curve(7.5, 14.0, 110, 30, "lin")
    h2.curve(7.5, 14.0, 110, 30, "lin")

    # floor: pizz and cello on D
    bass.note(2.0, "D2", 1.0, vel=86)
    bass.note(4.0, "A2", 1.0, vel=74)
    bass.note(5.5, "C#3", 0.5, vel=70)
    bass.note(7.0, "D2", 4.0, vel=96)
    vc.note(2.0, "D3", 4.0, vel=78, art="legato")
    vc.note(6.0, "A2", 1.0, vel=82, art="legato")
    vc.note(7.0, "D2", 8.0, vel=90, art="legato")
    vc.curve(7.0, 15.0, 112, 26, "lin")
    fd.hit(2.0, "dum", vel=90)
    fd.hit(4.0, "dum", vel=70)
    fd.hit(5.5, "tek", vel=60)
    fd.hit(7.0, "doum", vel=110)

    # dulcimer: chord on the downbeat, sparkle on the arrival, the held chord rings
    dul.chord(2.0, ["D3", "A3", "D4"], 2.0, vel=72, strum=0.02, art="ring")
    dul.tremolo(4.0, 2.0, "A4", rate=0.125, vel=56, dyn="cresc")
    dul.chord(7.0, ["D3", "A3", "D4", "F#4", "A4"], 8.0, vel=86, strum=0.025, art="ring")
    mel(dul, 7.0, "D5:.125 F#5:.125 A5:.125 D6:.125 F#6:4", vel=78, art="ring")

    # bagpipe drone swells under the held chord
    pipe.drone(5.0, 15.0, ["A3", "D4"], vel=88)
    pipe.curve(5.0, 7.0, 10, 60)
    pipe.curve(7.0, 9.5, 60, 108)
    pipe.curve(9.5, 15.0, 108, 0, "lin")
    p.set_end(16.0)
    return p


if __name__ == "__main__":
    print(build().compile().summary())
