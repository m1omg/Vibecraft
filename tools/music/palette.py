#!/usr/bin/env python3
"""palette.py: the tuned Vibecraft music palette. Composers import these instruments instead of picking
programs by hand, so every piece shares one band sound per faction.

    import palette as P
    fid = piece.track("fiddle", P.FIDDLE)                  # as tuned
    hrn = piece.track("horns", P.HORNS.variant(pan=-0.5))  # a per-piece change

Calibration (`trim_db`) brings each raw FluidR3_GM preset or numpy synth to one reference: with gain_db = 0
a typical line of the instrument plays at the melody's level (-30 dB active level after its EQ, measured by
render.py's per-stem report in the style tests and a calibration run); do not change it per piece.
`gain_db` is the musical balance relative to the melody and is what a composer adjusts: the defaults are
melody 0, counter-line -4, accompaniment -4..-6, drone -8, far horns -8..-9, hum and chant -9..-12. Measured facts behind
the choices (FluidR3_GM, fluidsynth 2.3, see README "Palette notes"):
  * "Fiddle" (110) and "Violin" (40) share one sample; velocity only scales level (about 40*log10(v/127)
    dB), so dynamics come from CC11 phrasing and the per-note bow shaping in score.py.
  * Dulcimer and the plucks (shamisen, sitar, banjo, koto) sit 12-19 dB below the bowed strings.
  * The orchestra kit (bank 128 program 48) has a real concert snare (38/40), a long concert bass drum
    (35/36, the distant-cannon boom) and a tambourine (54). The brush kit (40) gives soft brush taps (38-40).

Run `python3 tools/music/palette.py` to print the palette as JSON.
"""
from score import Instrument

# ----------------------------------------------------------------------------------- shared helpers
BOW_VIB = {"rate": 5.7, "depth": 0.13, "delay": 0.24, "rise": 0.32, "min_dur": 0.42}
WIDE_VIB = {"rate": 5.3, "depth": 0.2, "delay": 0.18, "rise": 0.25, "min_dur": 0.35}
HORN_VIB = {"rate": 4.8, "depth": 0.05, "delay": 0.5, "rise": 0.6, "min_dur": 1.2}
UNIT_DIP = ("peak", 2400, -2.0, 1.0)       # leave room for unit voices (1-3 kHz) on bright melody lines

# ----------------------------------------------------------------------------------- KINGDOM (Brennmark)
# A village band gone to war: hurdy-gurdy, fiddle, hammered dulcimer, frame drum and field snare, low horns
# far away, a soft wordless male hum. No symphonic brass fanfare, no big choir.
FIDDLE = Instrument("fiddle", program=110, mono=True, shape="bow", vibrato=BOW_VIB, bend_range=2,
                    gain_db=0.0, trim_db=5.5, pan=0.18, width=0.5, reverb=0.22,
                    eq=[("hp", 190), ("peak", 900, 1.0, 1.0), UNIT_DIP, ("highshelf", 8000, -2.0)],
                    vel_lo=46, vel_hi=112, timing_ms=6, lag_ms=4, lo=55, hi=100, color=(232, 176, 64))
VIOLA = Instrument("viola", program=41, mono=True, shape="bow", vibrato=BOW_VIB, gain_db=-4.0, trim_db=8.5,
                   pan=-0.32, width=0.5, reverb=0.25, eq=[("hp", 140), ("peak", 2600, -2.0, 1.0),
                                                         ("highshelf", 7000, -3.0)],
                   vel_lo=44, vel_hi=108, timing_ms=7, lag_ms=6, lo=48, hi=88, color=(206, 120, 60))
CELLO = Instrument("cello", program=42, mono=True, shape="bow", vibrato=dict(BOW_VIB, depth=0.1), gain_db=-6.0,
                   trim_db=5.7, pan=-0.12, width=0.6, reverb=0.2, eq=[("hp", 55), ("lowshelf", 160, 1.5),
                                                                       ("lp", 6000)],
                   vel_lo=44, vel_hi=110, timing_ms=7, lag_ms=5, lo=36, hi=76, color=(150, 82, 40))
BASS_PIZZ = Instrument("bass_pizz", program=45, gain_db=-4.0, trim_db=3.4, pan=0.05, width=0.4, reverb=0.12,
                       eq=[("hp", 38), ("lowshelf", 120, 2.0), ("lp", 3500)],
                       vel_lo=50, vel_hi=118, timing_ms=5, lo=28, hi=60, color=(110, 70, 40))
CONTRABASS = Instrument("contrabass", program=43, mono=True, shape="bow", gain_db=-5.0, trim_db=3.4, pan=0.0,
                        width=0.5, reverb=0.15, eq=[("hp", 35), ("lp", 2500)], vel_lo=44, vel_hi=104,
                        timing_ms=8, lag_ms=6, lo=28, hi=55, color=(90, 55, 30))
DULCIMER = Instrument("dulcimer", program=15, gain_db=-4.0, trim_db=14.1, pan=0.4, width=0.8, reverb=0.28,
                      eq=[("hp", 160), ("peak", 3000, -2.0, 1.0), ("highshelf", 8000, -3.0)],
                      vel_lo=40, vel_hi=118, timing_ms=5, accent=7, lo=50, hi=96, color=(110, 190, 230))
HORNS = Instrument("horns", program=60, mono=True, shape="breath", vibrato=HORN_VIB, gain_db=-9.0, trim_db=9.3,
                   pan=-0.45, width=0.7, reverb=0.65, eq=[("hp", 70), ("lp", 2800), ("peak", 600, -1.5, 0.8)],
                   vel_lo=40, vel_hi=96, timing_ms=10, lag_ms=12, lo=36, hi=72, color=(190, 150, 90))
BAGPIPE = Instrument("bagpipe", program=109, gain_db=-8.0, trim_db=4.2, pan=0.25, width=0.4, reverb=0.35,
                     eq=[("hp", 120), ("peak", 2600, -4.0, 1.0), ("lp", 5000)], vel_lo=60, vel_hi=100,
                     timing_ms=4, lo=55, hi=81, color=(160, 120, 170))
SNARE = Instrument("field_snare", drums=True, program=48, perc=True, gain_db=-4.0, trim_db=15.1, pan=0.12,
                   width=0.6, reverb=0.2, eq=[("hp", 120), ("peak", 4500, -2.0, 1.0), ("highshelf", 9000, -3.0)],
                   vel_lo=10, vel_hi=118, timing_ms=3, accent=0, color=(200, 200, 200),
                   drum_map={"snare": 38, "snare2": 40, "boom": 35, "boom2": 36, "tambourine": 54})
BRUSH = Instrument("brush", drums=True, program=40, perc=True, gain_db=-8.0, trim_db=15.3, pan=0.2, width=0.6,
                   reverb=0.2, eq=[("hp", 150), ("highshelf", 8000, -2.0)], vel_lo=10, vel_hi=110, timing_ms=4,
                   accent=0, color=(170, 170, 170), drum_map={"tap": 38, "slap": 39, "swirl": 40, "kick": 36})
TIMPANI = Instrument("timpani", program=47, gain_db=-6.0, trim_db=12.3, pan=0.0, width=0.6, reverb=0.35,
                     eq=[("hp", 40), ("lp", 4000)], vel_lo=30, vel_hi=110, timing_ms=4, perc=True, accent=0,
                     color=(120, 100, 80))
HURDY = Instrument("hurdy_gurdy", synth="hurdy", program=109, gain_db=-8.0, trim_db=-6.0, pan=-0.08, width=0.8,
                   reverb=0.2, eq=[("hp", 60), ("peak", 2500, -2.5, 0.9), ("highshelf", 6500, -3.0)],
                   synth_params={"body": 1.0, "rosin": 0.035, "flutter": 1.0, "buzz": 0.55, "level": 0.5},
                   timing_ms=4, accent=3, color=(160, 100, 200))
HUM = Instrument("male_hum", synth="chant", program=53, gain_db=-12.0, trim_db=0.0, pan=0.1, width=1.0,
                 reverb=0.55, eq=[("hp", 90), ("lp", 2600)],
                 synth_params={"voices": 4, "detune_cents": 9.0, "far": True, "breath": 0.03, "level": 0.5},
                 timing_ms=20, accent=0, color=(120, 160, 120))
FRAME_DRUM = Instrument("frame_drum", synth="framedrum", program=0, perc=True, gain_db=-5.0, trim_db=2.2,
                        pan=-0.15, width=0.5, reverb=0.18, eq=[("hp", 40), ("lp", 7000)],
                        synth_params={"size": 1.0, "skin": 1.0, "ring": 1.0}, vel_lo=1, vel_hi=127,
                        timing_ms=4, accent=0, color=(220, 90, 70),
                        drum_map={"dum": 41, "doum": 38, "tek": 41, "slap": 41, "mute": 41})
BELL = Instrument("town_bell", synth="bell", program=14, gain_db=-6.0, trim_db=3.3, pan=0.3, width=0.8,
                  reverb=0.5, eq=[("hp", 200), ("peak", 2800, -2.0, 1.0)], synth_params={"decay": 6.0},
                  timing_ms=0, accent=0, color=(250, 230, 120))

# ----------------------------------------------------------------------------------- CLANS (Tormai)
# Proud nomad households: frame drums in a galloping 6/8 over 4/4, struck and bowed bronze gongs, a raspy
# two-string bowed fiddle, jaw harp, long low bronze horns, wordless overtone chant, claps and stamps.
# No taiko, no low brass + electric guitar.
TWO_STRING = Instrument("two_string_fiddle", program=42, mono=True, shape="bow", vibrato=WIDE_VIB, bend_range=4,
                        gain_db=0.0, trim_db=7.4, drive=0.35, pan=0.12, width=0.5, reverb=0.28,
                        eq=[("hp", 110), ("peak", 1300, 1.0, 1.2), ("peak", 2600, -3.0, 1.0),
                            ("highshelf", 6500, -3.0)],
                        vel_lo=46, vel_hi=112, timing_ms=8, lag_ms=5, lo=43, hi=84, color=(232, 150, 60))
TWO_STRING_HI = TWO_STRING.variant(name="two_string_high", program=110, trim_db=5.6, gain_db=-2.0, drive=0.25,
                                   eq=[("hp", 200), ("peak", 1500, 1.5, 1.2), UNIT_DIP, ("highshelf", 6000, -5.0)],
                                   lo=55, hi=93, color=(240, 190, 90))
LUTE = Instrument("long_lute", program=106, gain_db=-4.0, trim_db=13.8, pan=-0.35, width=0.5, reverb=0.22,
                  eq=[("hp", 120), ("peak", 2200, -2.0, 1.0), ("highshelf", 7000, -3.0)],
                  vel_lo=44, vel_hi=118, timing_ms=6, accent=7, lo=45, hi=86, color=(110, 200, 170))
BRONZE_HORNS = Instrument("bronze_horns", program=57, mono=True, shape="breath", vibrato=HORN_VIB,
                          gain_db=-8.0, trim_db=12.8, pan=-0.4, width=0.7, reverb=0.6,
                          eq=[("hp", 50), ("lp", 2200), ("lowshelf", 150, 1.5)], vel_lo=36, vel_hi=92,
                          timing_ms=12, lag_ms=14, lo=33, hi=62, color=(200, 140, 70))
GONG = Instrument("gong", synth="gong", program=0, perc=True, gain_db=-5.0, trim_db=1.3, pan=0.05, width=1.0,
                  reverb=0.4, eq=[("hp", 30), ("highshelf", 7000, -3.0)],
                  synth_params={"decay": 9.0, "bloom": 0.6, "bright": 0.5, "identity": 1},
                  timing_ms=3, accent=0, color=(240, 200, 60))
GONG_SMALL = GONG.variant(name="gong_small", pan=0.35, gain_db=-9.0, trim_db=3.9,
                          synth_params={"decay": 4.5, "bloom": 0.35, "bright": 0.7, "identity": 2},
                          color=(250, 220, 120))
JAW_HARP = Instrument("jaw_harp", synth="jawharp", program=0, gain_db=-9.0, trim_db=7.2, pan=0.3, width=0.4,
                      reverb=0.15, eq=[("hp", 80), ("peak", 2500, -3.0, 1.0), ("lp", 7000)],
                      synth_params={"fundamental": 50, "q": 9.0, "decay": 0.9}, timing_ms=4, accent=4,
                      color=(150, 220, 90))
CHANT = Instrument("overtone_chant", synth="chant", program=53, gain_db=-9.0, trim_db=2.1, pan=0.0, width=1.0,
                   reverb=0.45, eq=[("hp", 60), ("peak", 2200, -2.0, 1.0), ("lp", 5000)],
                   synth_params={"voices": 3, "detune_cents": 7.0, "overtone_db": 20.0, "breath": 0.04},
                   timing_ms=15, accent=0, color=(110, 140, 200))
DEEP_DRUM = Instrument("deep_frame_drum", synth="framedrum", program=0, perc=True, gain_db=-4.0, trim_db=-1.6,
                       pan=-0.1, width=0.5, reverb=0.22, eq=[("hp", 32), ("lp", 6000)],
                       synth_params={"size": 1.0, "skin": 0.9, "ring": 1.25}, vel_lo=1, vel_hi=127, timing_ms=4,
                       accent=0, color=(210, 70, 60),
                       drum_map={"dum": 36, "doum": 33, "tek": 36, "slap": 36, "mute": 36})
HAND_DRUM = Instrument("hand_frame_drum", synth="framedrum", program=0, perc=True, gain_db=-8.0, trim_db=9.9,
                       pan=0.28, width=0.5, reverb=0.18, eq=[("hp", 60), ("lp", 8000)],
                       synth_params={"size": 1.0, "skin": 1.1, "ring": 0.8}, vel_lo=1, vel_hi=127, timing_ms=4,
                       accent=0, color=(230, 120, 100),
                       drum_map={"dum": 45, "doum": 43, "tek": 45, "slap": 45, "mute": 45})
CLAPS = Instrument("claps", synth="claps", program=0, perc=True, gain_db=-8.0, trim_db=15.8, pan=0.0, width=1.0,
                   reverb=0.3, eq=[("hp", 40), ("peak", 2200, -2.0, 1.0), ("highshelf", 8000, -3.0)],
                   synth_params={"hands": 6, "spread_ms": 9.0, "identity": 1}, vel_lo=1, vel_hi=127, timing_ms=6,
                   accent=0, color=(230, 230, 230),
                   drum_map={"clap": 39, "stamp": 36, "slap": 40})

# ----------------------------------------------------------------------------------- mix presets
# reverb: the generated room (render.make_ir): decay = T60 in s, predelay_ms, early (early-reflection level),
#         damp (how much faster the highs die, 0..1), width (0..1 decorrelation), hp/lp on the return.
# bus:    the glue stage: the dry+wet bus is set to `lufs` and compressed (threshold_db, ratio, attack/release ms).
# master: EQ on the bus (dip = (Hz, dB, Q) for the unit-voice band; presence = a lift above it so the mix is
#         not muffled; shelves) and the final target (lufs, tp).
MIX_KINGDOM = {
    "reverb": {"decay": 1.9, "predelay_ms": 20, "early": 0.35, "damp": 0.55, "width": 0.9, "hp": 170, "lp": 9000,
               "seed": 11},
    "bus": {"lufs": -20.0, "threshold_db": -21.0, "ratio": 2.0, "attack": 25, "release": 280, "knee": 4},
    "master": {"lufs": -16.0, "tp": -1.0, "dip": (2300, -1.5, 0.8), "presence": (4800, 2.0, 0.9), "lowshelf": (90, 0.0),
               "highshelf": (8500, 1.5)},
}
MIX_CLANS = {
    "reverb": {"decay": 2.6, "predelay_ms": 32, "early": 0.25, "damp": 0.65, "width": 1.0, "hp": 140, "lp": 8500,
               "seed": 23},
    "bus": {"lufs": -20.0, "threshold_db": -21.0, "ratio": 2.0, "attack": 30, "release": 320, "knee": 4},
    "master": {"lufs": -16.0, "tp": -1.0, "dip": (2300, -1.5, 0.8), "presence": (4800, 3.0, 0.9), "lowshelf": (80, 0.0),
               "highshelf": (8500, 1.5)},
}
MIX_SHARED = {  # menu / score bed: both palettes meet
    "reverb": {"decay": 2.3, "predelay_ms": 26, "early": 0.3, "damp": 0.6, "width": 1.0, "hp": 150, "lp": 7000,
               "seed": 17},
    "bus": dict(MIX_KINGDOM["bus"]),
    "master": dict(MIX_KINGDOM["master"]),
}

KINGDOM = {k: v for k, v in globals().items() if isinstance(v, Instrument) and k in (
    "FIDDLE", "VIOLA", "CELLO", "BASS_PIZZ", "CONTRABASS", "DULCIMER", "HORNS", "BAGPIPE", "SNARE", "BRUSH",
    "TIMPANI", "HURDY", "HUM", "FRAME_DRUM", "BELL")}
CLANS = {k: v for k, v in globals().items() if isinstance(v, Instrument) and k in (
    "TWO_STRING", "TWO_STRING_HI", "LUTE", "BRONZE_HORNS", "GONG", "GONG_SMALL", "JAW_HARP", "CHANT",
    "DEEP_DRUM", "HAND_DRUM", "CLAPS")}


if __name__ == "__main__":
    import argparse
    import json
    from dataclasses import asdict
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    print(json.dumps({"kingdom": {k: asdict(v) for k, v in KINGDOM.items()},
                      "clans": {k: asdict(v) for k, v in CLANS.items()},
                      "mix": {"kingdom": MIX_KINGDOM, "clans": MIX_CLANS, "shared": MIX_SHARED}}, indent=1, default=str))
