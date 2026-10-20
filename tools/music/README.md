# Music toolkit (composed music, no paid generation)

Vibecraft's music is composed in Python and rendered offline: a piece is a Python module that writes a score with
`score.py`, `render.py` turns it into stems (FluidSynth with the MIT-licensed FluidR3_GM soundfont, plus numpy
instruments from `synths.py`), mixes and masters them with ffmpeg, and exports the game's Ogg Vorbis. Every step is
deterministic: the same source and seed give byte-identical MIDI, stems and Ogg (`test_determinism.sh`).

| File | What it is |
|---|---|
| `score.py` | the composition API: modes, motifs and transforms, tempo/meter maps, sections, tracks, articulations, ornaments, drum grids, CC11 phrasing, humanisation, MIDI export |
| `synths.py` | numpy instruments: bronze gong (struck/bowed), town bell, hurdy-gurdy (drone, melody, trompette buzz), jaw harp, overtone chant / hum, frame drum, claps/stamps |
| `palette.py` | the tuned band per faction (programs, calibration, balance, pan, EQ, room sends) and the mix presets |
| `render.py` | piece → stems → mix → glue → form (track / loop / cue) → master → Ogg, plus checks, PNGs and a JSON report |
| `analyze.py` | loudness, true peak, band balance, K-weighted arc, section loudness, quiet spans, loop seam; spectrogram and piano roll |
| `pieces/` | piece modules: `style_kingdom.py`, `style_clans.py` (the 40 s style tests), `example_minimal.py` |
| `test_determinism.sh` | renders the style tests twice from scratch and compares the hashes |

Requirements: python3 with numpy, mido and Pillow; fluidsynth 2.3; `/usr/share/sounds/sf2/FluidR3_GM.sf2`; ffmpeg 6.1
with libvorbis. Nothing else, and no network. Every CLI has `--help`.

## Quick start

```bash
python3 tools/music/render.py tools/music/pieces/style_kingdom.py                 # -> tests/output/music/style_kingdom.ogg
python3 tools/music/render.py PIECE.py --out assets/audio/music/kingdom_1.ogg --length-check
python3 tools/music/render.py PIECE.py --out assets/audio/music/menu.ogg --loop --xfade 3
python3 tools/music/render.py PIECE.py --out assets/audio/music/opening_kingdom.ogg --trim 2.4 --trim-fade 0.3
bash tools/music/test_determinism.sh
```

Output: the `.ogg`; `tests/output/music/<name>_spectrogram.png` and `<name>_pianoroll.png`; the work folder
`tests/output/music/<name>/` (full MIDI, stem MIDIs, float stems, room IR, intermediate mixes, `report.json`, the stem
cache). The JSON report is also printed on stdout; exit code 2 means a check failed (see "Checks").

## Writing a piece

A piece module defines `build()` and returns a `Piece`. The minimal example (`pieces/example_minimal.py`):

```python
import palette as P
from score import Piece, wheel, wheel_answer

def build():
    p = Piece("example_minimal", seed=3, bpm=92, key="D", mode="mixolydian")
    p.mix, p.tail_s = P.MIX_KINGDOM, 4.0
    fid, hg, dul, fd = (p.track("fiddle", P.FIDDLE), p.track("hurdy", P.HURDY),
                        p.track("dulcimer", P.DULCIMER), p.track("drum", P.FRAME_DRUM))
    a = p.section("A", 4)
    hg.drone(a.start, a.end, ["D2", "A2"], vel=86)
    b = fid.play(wheel(), a.b(0), art="legato", dyn="cresc")
    fid.play(wheel_answer().ornament(0, "grace_up"), b, art="legato")
    fid.play(wheel().transpose(2).ornament(3, "mordent"), a.b(2), art="legato")
    for bar, deg in enumerate([0, 0, 6, 0]):
        dul.arp(a.b(bar), a.b(bar + 1), p.mode.chord(deg, octave=-1 if deg > 4 else 0), step=0.5, ring=1.6)
    fd.pattern(a.start, 4, {"dum": "x.......x.....o.", "tek": "..g.o.g...g.o.g."}, vel=76)
    fid.swell(a.b(0), a.b(4), 80, 112)
    p.breathe(a.end, beats=1.0)
    return p
```

(Piece files start with `sys.path.insert(0, <tools/music>)` so they also run on their own; copy the header of an
existing piece.)

### Units

* **Time is in beats** (quarter notes) from the start of the piece. `Section.b(bar, beat)` turns a 0-based bar of the
  section into an absolute beat; `Piece.at(bar, beat)` does the same for the whole piece.
* **Pitches** are MIDI numbers or names (`"D4"` = 62). **Scale degrees** are 0-based in a `Mode`: 0 = tonic, 4 = fifth,
  7 = octave, negative = below. `Mode("D", "dorian")` has degree 0 on D4; `octave=2` moves it to D2.
* **Velocity** is musical (1-127); each instrument maps it into its sweet range. Long-note **dynamics come from CC11**
  (`expr`, `curve`, `swell`), not from velocity: FluidR3 velocity only scales the level.

### API summary

| Object | Calls |
|---|---|
| `Piece(name, seed, bpm, meter=(4,4), key, mode)` | `track(name, inst)`, `section(name, bars, meter=None, bpm=None)`, `set_tempo`, `ramp(b0,b1,bpm0,bpm1)`, `rit(b0,b1,to)`, `accel`, `breathe(beat, beats, depth)`, `fermata(beat, beats, stretch)`, `mark`, `set_end`, `seconds(beat)`, `compile()`, `write_midi(path)`; attributes `mix`, `kind` (track/loop/cue), `tail_s`, `xfade_s`, `trim_s`, `trim_fade_s`, `length_range`, `out` |
| `Section` | `start`, `end`, `b(bar, beat)`, `bar_len` |
| `Mode(tonic, name, octave)` | `pitch(deg, octave, alt)`, `chord(deg, size, octave, shape, inversion, drop)` with shapes triad, seventh, sus2, sus4, power, add9, quartal, open, sixth; `neighbour(p, ±1)`, `snap`, `degree_of`, `scale(lo, hi)`. Modes: ionian/major, dorian, phrygian, lydian, mixolydian, aeolian/minor, locrian, harmonic_minor, pent_major, pent_minor |
| `Motif(degrees, durs, vels, arts, alts, orns)` | `transpose(k)` (in mode), `invert(axis)`, `retrograde()`, `augment(f)`, `diminish(f)`, `displace(beats)`, `fragment(i, j)`, `ornament(i, kind)`, `accent(i)`, `rhythm(durs)`, `hold_last(beats)`, `with_art(art)`, `then(...)` / `+`, `repeat(k)`, `sequence(steps)`, `rest(beats)`, `length` |
| our motifs | `wheel()` (kingdom: tonic→fifth stepwise, short-short-short-long-long), `wheel_answer()` (the falling fourth 3→0), `gong_ring()` (clans: 5-4-1, held 2 resolving to 1) |
| `Track` | `note(beat, pitch, dur, vel, art, orn, **kw)`, `notes_seq`, `play(motif, at, mode, octave, vel, dyn, art)` (returns the end beat), `chord(beat, pitches, dur, vel, strum)`, `arp(start, end, pitches, step, order, ring, dyn)`, `drone(start, end, pitches)`, `tremolo`, `hit(beat, drum, vel)`, `flam`, `roll(beat, dur, drum, vel0, vel1, rate)`, `pattern(start, bars, spec, vel, steps, swing)`, `expr(beat, v)`, `curve(b0, b1, v0, v1, shape)`, `swell(b0, b1, lo, hi, peak)`, `cc(beat, num, val)`, `double(other, start, end, interval, vel)` |

* **Articulations** (`art`): `legato` (overlaps the next note by 35 ms), `tenuto`, `normal`, `staccato`, `marcato`,
  `ghost`, `ring` (let ring, at least 2 beats), `exact` (no humanisation: drones), `slide` (on a mono line: a
  pitch-bend slide from the previous note).
* **Ornaments** (`orn` or `Motif.ornament`): `grace_up` / `grace_down` (before the beat), `mordent` / `lmordent`, `turn`,
  `trill`, `slide` / `slide_down` (bend into the note), `slide_from` (kw `semis`, `time`), `roll`, `flam`. Neighbour
  notes come from the mode.
* **Phrase dynamics:** `dyn="arch" | "cresc" | "dim" | (v0, v1) | [list]` on `play` and `arp`; metric accents on strong
  beats are automatic (`Instrument.accent`, compound meters accent every dotted quarter).
* **Drum grids:** `pattern(start, bars, {"dum": "x.......x.....o.", "tek": "..g.o.g...g.o.g."})`. One character per step;
  the number of characters is the steps per bar: 16 = sixteenths in 4/4, **12 = triplet eighths: the galloping 6/8
  feel over a 4/4 line**. `X` accent, `x` hit, `o` soft, `g` ghost, `f` flam, `r` roll, `.`/`-` rest, `|` separates
  bars (the string cycles over `bars`).
* **Tempo breathing:** `breathe(beat)` slows into a phrase end and returns a tempo on `beat`; `rit` for endings;
  all tempo curves are stepped every 1/8 beat in the MIDI and shared exactly by the synth stems.
* **Humanisation** (seeded per track with crc32, so adding a track never changes another): a smooth ensemble drift
  (±`drift_ms`, shared by every track), a per-instrument lag (`lag_ms`, e.g. horns 12 ms behind), per-note jitter
  (`timing_ms`, clipped to ±15 ms), velocity jitter, small length jitter.
* **Mono expressive lines** (`Instrument.mono`: fiddles, horns) alternate two MIDI channels so each note owns its pitch
  bend and CC11: per-note bow or breath shaping (`shape="bow" | "breath"`), delayed vibrato (5-6 Hz via pitch bend,
  `vibrato=`), and slides that never bend the previous note's release.

### Synth instruments (`synths.py`)

Synth tracks take the same calls; the note keywords pick the sound:

| Synth | Keywords |
|---|---|
| `gong` | `stroke="struck"` (default) or `"bowed"` (a swell over the note length, then the ring); `decay`, `damp=True` |
| `bell` | `decay` |
| `hurdy` | `stroke="drone"` (default), `"melody"` (keyed, with a key click), `"buzz"` (a trompette coup: put them on the beat as the rhythm engine); `pan` |
| `jawharp` | the note pitch picks the mouth formant at the nearest harmonic of the fixed fundamental (`synth_params["fundamental"]`), or `k=` gives the harmonic directly; `k_from`, `glide`, `decay` |
| `chant` | `vowel` (a o u e i m; "m" = closed-mouth hum) or `vowels=[...]` (morph across the note), `overtones=[None, 8, 9, 12]` (the whistled overtone per stage), `voices` |
| `framedrum` | drum names `dum` (centre), `doum` (deep), `tek` (rim), `slap`, `mute` |
| `claps` | `clap`, `stamp`, `slap` (knee); a small group of `hands` with fixed people (timing bias, pitch, position) |

`python3 tools/music/synths.py demo OUTDIR` renders one example of each.

## Palette (`palette.py`)

**Calibration:** `trim_db` brings every preset or synth to one reference: with `gain_db = 0` a typical line plays at
the melody's level (-30 dB active level after its EQ). So **`gain_db` reads as "dB relative to the melody"**, and
the default balance is in the palette. Use `P.FIDDLE.variant(pan=-0.2, gain_db=-3)` for per-piece changes; never
change `trim_db` in a piece.

| Kingdom | Source | gain | pan | room | Role and notes |
|---|---|---|---|---|---|
| `FIDDLE` | GM 110 | 0 | +0.18 | 0.22 | melody; bow shaping, vibrato, unit-voice dip at 2.4 kHz |
| `VIOLA` | GM 41 | -4 | -0.32 | 0.25 | counter-melody |
| `CELLO` | GM 42 | -6 | -0.12 | 0.20 | sustained bass and tenor lines |
| `BASS_PIZZ` | GM 45 | -4 | +0.05 | 0.12 | pizzicato bass |
| `CONTRABASS` | GM 43 | -5 | 0 | 0.15 | arco floor |
| `DULCIMER` | GM 15 | -4 | +0.40 | 0.28 | hammered arpeggios, tremolo (raw preset is 14 dB quiet) |
| `HORNS` | GM 60 | -9 | -0.45 | 0.65 | two low horns far away: short two-note calls only, never fanfares |
| `BAGPIPE` | GM 109 | -8 | +0.25 | 0.35 | drone colour |
| `SNARE` | GM kit 48 | -4 | +0.12 | 0.20 | field snare (concert snare 38/40), `boom` 35/36 = distant cannon, `tambourine` |
| `BRUSH` | GM kit 40 | -8 | +0.20 | 0.20 | soft brush taps / swirls |
| `TIMPANI` | GM 47 | -6 | 0 | 0.35 | sparingly |
| `HURDY` | synth | -8 | -0.08 | 0.20 | drone (D2+A2) and trompette coups |
| `HUM` | synth chant | -12 | +0.10 | 0.55 | soft wordless male hum, far (4 voices) |
| `FRAME_DRUM` | synth | -5 | -0.15 | 0.18 | heartbeat, dum/tek |
| `BELL` | synth | -6 | +0.30 | 0.50 | small town bell |

| Clans | Source | gain | pan | room | Role and notes |
|---|---|---|---|---|---|
| `TWO_STRING` | GM 42 + drive 0.35 | 0 | +0.12 | 0.28 | the raspy two-string bowed fiddle: wide vibrato, slides (bend range 4) |
| `TWO_STRING_HI` | GM 110 + drive 0.25 | -2 | +0.12 | 0.28 | its upper register |
| `LUTE` | GM 106 | -4 | -0.35 | 0.22 | plucked long-necked lute, answers the fiddle |
| `BRONZE_HORNS` | GM 57 | -8 | -0.40 | 0.60 | long low bronze horns, swelling calls (use two tracks, panned apart, to call and answer) |
| `GONG` | synth | -5 | +0.05 | 0.40 | big bronze gong, struck or bowed |
| `GONG_SMALL` | synth | -9 | +0.35 | 0.40 | small bright gong accents |
| `JAW_HARP` | synth | -9 | +0.30 | 0.15 | pulses on the triplet grid |
| `CHANT` | synth | -9 | 0 | 0.45 | deep overtone drone / chant, 3 voices |
| `DEEP_DRUM` | synth | -4 | -0.10 | 0.22 | deep frame drum, the gallop |
| `HAND_DRUM` | synth | -8 | +0.28 | 0.18 | hand frame drum, ghost strokes |
| `CLAPS` | synth | -8 | 0 | 0.30 | claps, stamps, knee slaps (6 people) |

**Mix presets:** `MIX_KINGDOM` (a warm wooden hall: T60 1.9 s, 20 ms pre-delay), `MIX_CLANS` (a larger, darker space:
T60 2.6 s, 32 ms pre-delay), `MIX_SHARED` (menu / score: T60 2.3 s). All glue the bus at -20 LUFS with a 2:1 RMS
compressor (threshold -21 dB, 25-30 ms attack, 280-320 ms release), dip -1.5 dB at 2.3 kHz (room for unit voices),
lift 4.8 kHz (+2 / +3 dB) and 8.5 kHz (+1.5 dB) so the mix is not muffled, and master to -16 LUFS / -1 dBTP.

**Palette notes (measured, FluidR3_GM with fluidsynth 2.3):**
* "Fiddle" (110) and "Violin" (40) are the same sample; velocity scales level only (about 40·log10(v/127) dB, so
  60 → 100 is +8.8 dB), so dynamics are written with CC11 and the per-note bow shaping.
* The dulcimer and the plucks (shamisen 106, sitar 104, banjo 105, koto 107) sit 12-19 dB under the bowed strings;
  the calibration handles it.
* Orchestra kit (bank 128, program 48): 38/40 concert snare, 35/36 long concert bass drum, 41-53 timpani, 54
  tambourine. Brush kit (40): 38 tap, 39 slap, 40 swirl.
* ffmpeg 6.1 traps found while building this: `afir`'s `dry` is the input gain (dry=0 gives silence), and
  `asoftclip`'s `oversample` loses about 6 dB. `render.py` works around both.
* Avoid: no symphonic brass fanfare with a big choir (kingdom), no taiko and no low brass with electric guitar
  (clans), no airy solo female voice with harp and flute as the lead colour (anyone). The palette has none of
  them on purpose; horns are distant two-note calls.

## Render pipeline

1. compile the score and write the full MIDI;
2. stems: one FluidSynth render per soundfont track (its own stem MIDI, internal reverb and chorus off, float, release
   tails kept), one numpy render per synth track; cached in `<work>/cache` by content hash (`--no-cache` to force);
3. mix (ffmpeg): trim → drive → EQ → gain → width/pan, and a send to one shared room (an IR generated with numpy: early
   reflections plus a noise tail whose highs die faster, convolved with `afir`);
4. glue: the bus is set to -20 LUFS, EQ'd (unit-voice dip, presence, shelves) and compressed 2:1;
5. form: `track` = the music plus `tail_s` with a short end fade; `loop` = the music after the loop point (the piece's
   end) crossfaded equal-power into its start over `--xfade` s, so the file is exactly the musical length; `cue` = the
   first `--trim` s with a cosine `--trim-fade`;
6. master: loudnorm two-pass in linear mode to -16 LUFS with a -1.6 dBTP aim (a lookahead limiter runs first only when
   the peak-to-loudness ratio would push loudnorm into dynamic mode), then Ogg Vorbis `-q:a 6`, 48 kHz stereo,
   bit-exact; if the encoded file misses -16 ±0.5 LUFS or -1 dBTP, a small gain fix is applied and it is re-encoded.

**File names** (bible §10.4): `assets/audio/music/<faction>_<n>.ogg`, `menu.ogg`, `score.ogg`, `victory_<faction>.ogg`,
`defeat_<faction>.ogg`, `opening_<faction>.ogg`. Commit the `.ogg` and the piece source; the MIDI, stems and PNGs
regenerate.

## Checks (you cannot listen: measure and LOOK)

`report.json` (and stdout) holds:

* `measure`: integrated LUFS (target -16 ±1), true peak (≤ -1 dBTP), LRA, duration, `bands` (energy shares: sub <60,
  low 60-250, lowmid 250-1k, voice 1-3k, presence 3-6k, air >6k), `arc_db` (K-weighted 3 s windows), `quiet_spans_s`
  (empty spans 40 dB under the median), and for loops `seam` (`rms_step_db` aim within ±2, `spec_ratio` aim < 1.5,
  `jump_vs_p99` aim < 1);
* `sections_db`: K-weighted loudness of each section and the tail: **the dynamic arc**, which should rise and fall
  (the style tests span about 8 dB);
* `stems`: per-stem `active_db` (level while playing, after the stem's EQ and gain): melody about -30, counter-lines
  -34, drones -38, background voices -42 are the palette defaults;
* `master`: loudnorm measurements, `normalization_type` (must be `linear`), any limiter ceiling;
* `hashes`: MIDI, every stem, the Ogg.

Then **look at both PNGs** with an image viewer: the piano roll (one colour per track, section lines, a K-weighted
loudness lane) for register spread, density, call and response and the arc; the spectrogram for mud (a solid
yellow block under 250 Hz), empty spans, a melody that stands out in 300 Hz-3 kHz, and a clean ending with a
room tail. Exit code 2 = loudness or peak out of range, or `--length-check` failed (`Piece.length_range` or
`--length MIN MAX`).

## Style tests (40 s each, final measurements)

| | LUFS | dBTP | LRA | length | bands sub/low/lowmid/voice/presence/air (%) | sections (K-weighted dB) |
|---|---|---|---|---|---|---|
| `style_kingdom` (D Mixolydian, 92) | -16.0 | -2.4 | 10.5 | 41.3 s | 0.2 / 28 / 56 / 12.5 / 3.0 / 0.4 | intro -24.3, antecedent -17.9, consequent -15.9, outro -19.6, tail -31.2 |
| `style_clans` (D Dorian, 92) | -16.0 | -2.2 | 8.5 | 42.3 s | 0.4 / 30 / 50 / 17.9 / 1.7 / 0.3 | intro -23.4, A -18.0, B -15.6, outro -19.8, tail -33.1 |

Both master in linear mode (clans needs a transparent limiter at -9 dB for its gong and drum peaks). The renders and
their PNGs are kept in `docs/audio/music-style/` for review.

## Known limitations

* FluidR3 samples are single-layer and fairly dark (little energy above 6 kHz); the mix adds presence, but bowed
  strings will never sound like a real section. Long bowed notes rely on the CC11 bow shaping and pitch-bend vibrato.
* The numpy instruments are models, not recordings: gongs, hurdy-gurdy and chant are convincing in a mix, and the
  frame drum and claps are good; the jaw harp is the least natural when exposed solo. The chant is wordless by
  construction (formant vowels only).
* The rally percussion stem (juice MUS-01, P2) is not split out yet: tracks carry `perc=True` so a `--split-perc` mode
  can mix the two stem groups through the same chain later.
* Rendering takes about real time (40 s for a 40 s piece, most of it the numpy synths and the ffmpeg passes); the stem
  cache makes mix-only changes fast.
* Pieces are rendered at 48 kHz only; the stem MIDI uses up to 2 channels per mono track and channel 10 for kits.
