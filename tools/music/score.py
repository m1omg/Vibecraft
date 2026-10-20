#!/usr/bin/env python3
"""score.py: a small composition API for Vibecraft music (python3 + mido + numpy).

A piece is a Python module with a `build()` function that returns a `Piece`. `render.py` compiles it to MIDI,
renders the stems (FluidSynth for soundfont instruments, `synths.py` for the numpy instruments) and masters the
mix. Everything is deterministic: the same source and seed give byte-identical MIDI and stems.

Units
  * Time is in BEATS (quarter notes) from the start of the piece, as floats. `Section.b(bar, beat)` and
    `Piece.at(bar, beat)` turn bar numbers (0-based) into beats.
  * Pitches are MIDI numbers; `n("D4") == 62`. Scale DEGREES are 0-based integers in a `Mode`:
    0 = tonic, 4 = fifth, 7 = octave, -3 = the fifth below. Degrees are what motifs are written in.
  * Velocities are musical (1-127); each instrument maps them through its own curve (`palette.py`).

The pieces of the API
  Mode(tonic, name)            modal scales and chords: .pitch(deg, octave), .chord(deg), .neighbour(pitch, +1/-1)
  Motif(degrees, durs)         a melodic cell with transforms: transpose (in mode), invert, retrograde, augment,
                               diminish, displace, fragment, ornament, sequence, then (+), repeat, hold_last, rhythm
  Piece(name, seed, bpm, ...)  tempo map (set_tempo, ramp, rit, breathe, fermata), meter map, sections, tracks
  Section                      returned by piece.section(name, bars): .start, .end, .b(bar, beat)
  Track                        returned by piece.track(name, instrument): note, play (a motif), chord, arp, drone,
                               tremolo, hit, pattern (drum grids, any steps per bar: 12 steps in 4/4 = the 6/8 feel),
                               roll, flam, expr / curve / swell (CC11), double (copy another line)
  Instrument                   a GM program (bank/program) OR a numpy synth (`synth="gong"`), plus mix settings
  Piece.compile()              humanise, ornament, articulate, quantise: the single source of truth for MIDI,
                               the synth stems and the piano roll
  Piece.write_midi(path)       type-1 MIDI with tempo map, meters, section markers

Performance model (applied in compile, seeded per track with crc32 so adding a track never changes another):
  * ensemble timing drift shared by all tracks (smooth, +-drift_ms) + per-instrument lag + per-note jitter
    (sigma = Instrument.timing_ms, clipped to +-15 ms); metric accents on strong beats; velocity jitter;
  * articulations: legato (overlap into the next note), tenuto, normal, staccato, marcato, ghost, ring (let ring);
  * ornaments expanded to real notes: grace_up / grace_down (before the beat), mordent / lmordent, turn, trill,
    slide / slide_down (pitch-bend slide into the note), roll (repeated strokes), flam;
  * mono expressive instruments (fiddles, horns) alternate two MIDI channels so each note owns its pitch bend
    and CC11: per-note bow or breath shaping, delayed vibrato via pitch bend, slides that never bend the
    previous note's release.

Run `python3 tools/music/score.py --help` for this text; `python3 tools/music/score.py --demo out.mid` writes a
tiny demo MIDI.
"""
from __future__ import annotations

import bisect
import copy
import math
import zlib
from dataclasses import dataclass, field

import numpy as np

TPQ = 960                      # MIDI ticks per quarter note
TEMPO_RES = 0.125              # beats: tempo curves are stepped at this grid
CTRL_RATE = 100.0              # Hz: CC11 and pitch-bend curves are sampled at this rate
MAX_JITTER_S = 0.015           # humanisation never moves a note by more than 15 ms

# --------------------------------------------------------------------------------------------- pitches and modes
_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def n(name) -> int:
    """Note name to MIDI number: n("C4") == 60, n("F#3") == 54, n("Bb2") == 46. Ints pass through."""
    if isinstance(name, (int, np.integer)):
        return int(name)
    s = name.strip()
    pc = _NOTE[s[0].upper()]
    i = 1
    while i < len(s) and s[i] in "#b":
        pc += 1 if s[i] == "#" else -1
        i += 1
    octave = int(s[i:]) if i < len(s) else 4
    return 12 * (octave + 1) + pc


def note_name(p: int) -> str:
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    return f"{names[p % 12]}{p // 12 - 1}"


MODES = {
    "ionian": [0, 2, 4, 5, 7, 9, 11], "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10], "minor": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "pent_major": [0, 2, 4, 7, 9],
    "pent_minor": [0, 3, 5, 7, 10],
}


class Mode:
    """A modal scale on a tonic. Mode("D", "dorian") puts degree 0 on D4 (62); octave=3 puts it on D3.

    pitch(deg, octave=0, alt=0)   degree -> MIDI (deg may be negative or > 6; alt adds semitones)
    chord(deg, size=3, ...)       stacked thirds inside the mode (modal chords: in D dorian chord(3) = G B D)
    sus2 / sus4 / power / quartal shapes via chord(deg, shape="sus4")
    neighbour(pitch, +1|-1)       the next scale tone above / below any pitch (for ornaments)
    snap(pitch)                   nearest scale tone
    degree_of(pitch)              (degree, alt) of a pitch
    """

    def __init__(self, tonic="D", name="dorian", octave=4):
        self.name = name
        self.steps = MODES[name]
        t = n(tonic) if isinstance(tonic, int) or any(c.isdigit() for c in str(tonic)) else n(f"{tonic}{octave}")
        self.tonic = t

    def __repr__(self):
        return f"Mode({note_name(self.tonic)} {self.name})"

    def pitch(self, deg: int, octave: int = 0, alt: int = 0) -> int:
        k = len(self.steps)
        o, d = divmod(int(deg), k)
        return self.tonic + 12 * (o + octave) + self.steps[d] + alt

    def degree_of(self, p: int):
        rel = p - self.tonic
        o, pc = divmod(rel, 12)
        best = min(range(len(self.steps)), key=lambda i: (abs(self.steps[i] - pc), self.steps[i]))
        return o * len(self.steps) + best, pc - self.steps[best]

    def snap(self, p: int) -> int:
        d, _ = self.degree_of(p)
        return self.pitch(d)

    def neighbour(self, p: int, direction: int = 1) -> int:
        cands = [self.pitch(d) for d in range(-40, 40)]
        if direction > 0:
            return min(c for c in cands if c > p)
        return max(c for c in cands if c < p)

    SHAPES = {"triad": (0, 2, 4), "seventh": (0, 2, 4, 6), "sus2": (0, 1, 4), "sus4": (0, 3, 4),
              "power": (0, 4, 7), "add9": (0, 2, 4, 8), "quartal": (0, 3, 6), "open": (0, 4, 9), "sixth": (0, 2, 4, 5)}

    def chord(self, deg: int, size: int = 3, octave: int = 0, shape: str | None = None, inversion: int = 0,
              drop: int | None = None) -> list[int]:
        """Chord on scale degree `deg`. shape: triad (default for size 3), seventh, sus2, sus4, power, add9,
        quartal, open, sixth. inversion rotates the lowest notes up an octave; drop moves the n-th note from the
        top down an octave (drop=2 gives open, guitar-like voicings)."""
        if shape is None:
            shape = "seventh" if size >= 4 else "triad"
        ps = [self.pitch(deg + s, octave) for s in self.SHAPES[shape]]
        for _ in range(inversion):
            ps = ps[1:] + [ps[0] + 12]
        if drop:
            ps = sorted(ps)
            i = len(ps) - drop
            ps[i] -= 12
            ps = sorted(ps)
        return ps

    def scale(self, lo: int, hi: int) -> list[int]:
        return [p for p in (self.pitch(d) for d in range(-50, 50)) if lo <= p <= hi]


# --------------------------------------------------------------------------------------------- motifs
@dataclass
class MNote:
    deg: int | None          # None = rest
    dur: float               # beats
    vel: float = 1.0         # velocity multiplier
    art: str | None = None   # articulation override
    alt: int = 0             # chromatic alteration in semitones
    orn: str | None = None   # ornament name


class Motif:
    """A melodic cell in scale degrees. Motif([0, 1, 2, 3, 4], [.5, .5, .5, 1.5, 2]) is the kingdom Wheel.

    All transforms return a new Motif:
      transpose(k)        diatonic shift by k scale steps (stays in the mode)
      invert(axis=None)   mirror the degrees around `axis` (default: the first note)
      retrograde()        reverse the order (rhythm reversed too)
      augment(f=2)        durations x f;  diminish(f=2): durations / f
      displace(beats)     start later by `beats` (rhythmic displacement; a leading rest)
      fragment(i, j)      notes[i:j] (motivic fragmentation)
      ornament(i, kind)   put an ornament on note i (grace_up, grace_down, mordent, lmordent, turn, trill,
                          slide, slide_down)
      accent(i, f=1.2)    velocity x f on note i
      rhythm(durs)        same pitches, new rhythm
      hold_last(beats)    lengthen the last note
      then(*m) / m1 + m2  concatenation;  repeat(k)
      sequence(steps)     the motif repeated at each diatonic transposition in `steps` (a melodic sequence)
      with_art(art)       articulation for every note
    """

    def __init__(self, degrees, durs, vels=None, arts=None, alts=None, orns=None, name="", offset=0.0):
        degrees = list(degrees)
        if isinstance(durs, (int, float)):
            durs = [float(durs)] * len(degrees)
        assert len(durs) == len(degrees), "Motif: degrees and durs differ in length"
        self.notes = []
        for i, d in enumerate(degrees):
            self.notes.append(MNote(d, float(durs[i]),
                                    vels[i] if vels else 1.0,
                                    arts[i] if arts else None,
                                    alts[i] if alts else 0,
                                    orns[i] if orns else None))
        self.name = name
        self.offset = float(offset)

    @classmethod
    def _from(cls, notes, name="", offset=0.0):
        m = cls([], [])
        m.notes = [copy.copy(x) for x in notes]
        m.name = name
        m.offset = offset
        return m

    def __repr__(self):
        body = " ".join(("r" if x.deg is None else str(x.deg)) + f":{x.dur:g}" for x in self.notes)
        return f"Motif({self.name or '-'} [{body}] +{self.offset:g})"

    def __len__(self):
        return len(self.notes)

    @property
    def length(self) -> float:
        """Total length in beats, including the displacement offset."""
        return self.offset + sum(x.dur for x in self.notes)

    @property
    def degrees(self):
        return [x.deg for x in self.notes]

    def _map(self, fn):
        m = Motif._from(self.notes, self.name, self.offset)
        for x in m.notes:
            if x.deg is not None:
                x.deg = fn(x.deg)
        return m

    def transpose(self, k: int) -> "Motif":
        return self._map(lambda d: d + k)

    def invert(self, axis: int | None = None) -> "Motif":
        if axis is None:
            axis = next((x.deg for x in self.notes if x.deg is not None), 0)
        return self._map(lambda d: 2 * axis - d)

    def retrograde(self) -> "Motif":
        return Motif._from(list(reversed(self.notes)), self.name, self.offset)

    def augment(self, f: float = 2.0) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset * f)
        for x in m.notes:
            x.dur *= f
        return m

    def diminish(self, f: float = 2.0) -> "Motif":
        return self.augment(1.0 / f)

    def displace(self, beats: float) -> "Motif":
        return Motif._from(self.notes, self.name, self.offset + beats)

    def fragment(self, i: int, j: int | None = None) -> "Motif":
        return Motif._from(self.notes[i:j], self.name, 0.0 if i else self.offset)

    def ornament(self, i: int, kind: str) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset)
        m.notes[i].orn = kind
        return m

    def accent(self, i: int, f: float = 1.2) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset)
        m.notes[i].vel *= f
        return m

    def rhythm(self, durs) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset)
        for x, d in zip(m.notes, durs):
            x.dur = float(d)
        return m

    def hold_last(self, beats: float) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset)
        m.notes[-1].dur += beats
        return m

    def with_art(self, art: str | None) -> "Motif":
        m = Motif._from(self.notes, self.name, self.offset)
        for x in m.notes:
            x.art = art
        return m

    def then(self, *others: "Motif") -> "Motif":
        notes = [copy.copy(x) for x in self.notes]
        for o in others:
            if o.offset:
                notes.append(MNote(None, o.offset))
            notes += [copy.copy(x) for x in o.notes]
        return Motif._from(notes, self.name, self.offset)

    __add__ = then

    def repeat(self, k: int) -> "Motif":
        return self.then(*[self] * (k - 1)) if k > 1 else Motif._from(self.notes, self.name, self.offset)

    def sequence(self, steps) -> "Motif":
        parts = [self.transpose(s) for s in steps]
        return parts[0].then(*parts[1:])

    def rest(self, beats: float) -> "Motif":
        """Append a rest."""
        return self.then(Motif([None], [beats]))


def wheel(rhythm=(0.5, 0.5, 0.5, 1.5, 2.0)) -> Motif:
    """Kingdom "Wheel" call (bible 10.2): five notes climbing stepwise tonic -> fifth, the last two held."""
    return Motif([0, 1, 2, 3, 4], list(rhythm), vels=[0.92, 0.95, 1.0, 1.08, 1.04], name="wheel")


def wheel_answer(rhythm=(1.0, 2.0)) -> Motif:
    """The Wheel's answer: a falling fourth (degree 3 -> 0), closing the period on the tonic."""
    return Motif([3, 0], list(rhythm), vels=[1.0, 0.92], name="wheel_answer")


def gong_ring(rhythm=(1.0, 1.0, 1.5, 3.0, 1.5)) -> Motif:
    """Clans "Gong-Ring" (bible 10.2): falling fifth-fourth-tonic, then a held second resolving to the tonic."""
    return Motif([4, 3, 0, 1, 0], list(rhythm), vels=[1.05, 0.95, 1.0, 1.02, 0.9], name="gong_ring")


# --------------------------------------------------------------------------------------------- instruments
@dataclass
class Instrument:
    """One playable voice. Either a General MIDI preset (program/bank, or drums=True for a kit) rendered by
    FluidSynth, or a numpy synth (`synth` = a key of synths.SYNTHS, `synth_params` its settings).

    Mix settings (used by render.py): gain_db (musical balance), trim_db (calibration of the raw preset or
    synth level; leave it alone), drive (0..1 soft saturation for rasp), pan (-1..1), width (stereo width
    0..1.5), reverb (send 0..1),
    eq (list of ('hp', f) ('lp', f) ('peak', f, gain_db, q) ('lowshelf', f, gain_db) ('highshelf', f, gain_db)).
    Performance: vel_lo/vel_hi/vel_gamma (velocity curve), timing_ms (jitter sigma), lag_ms (constant
    placement: + behind the beat), accent (metric accent size), mono (one line: alternating channels, bow or
    breath shaping, vibrato, slides), shape ('bow' | 'breath' | None), vibrato dict or None, bend_range
    (semitones), expr (default CC11), release_s (how long a released note keeps its channel), perc (the
    rally-stem split: True for drums), drum_map (name -> MIDI note)."""
    name: str
    program: int = 0
    bank: int = 0
    drums: bool = False
    synth: str | None = None
    synth_params: dict = field(default_factory=dict)
    gain_db: float = 0.0
    trim_db: float = 0.0
    drive: float = 0.0
    pan: float = 0.0
    width: float = 1.0
    reverb: float = 0.2
    eq: list = field(default_factory=list)
    vel_lo: int = 20
    vel_hi: int = 118
    vel_gamma: float = 1.0
    timing_ms: float = 5.0
    lag_ms: float = 0.0
    accent: float = 6.0
    mono: bool = False
    shape: str | None = None
    vibrato: dict | None = None
    bend_range: int = 2
    expr: int = 100
    release_s: float = 0.35
    perc: bool = False
    drum_map: dict = field(default_factory=dict)
    lo: int = 0
    hi: int = 127
    color: tuple | None = None

    def variant(self, **kw) -> "Instrument":
        """A copy with some fields changed: palette.FIDDLE.variant(pan=0.3, reverb=0.4)."""
        d = copy.deepcopy(self)
        for k, v in kw.items():
            if not hasattr(d, k):
                raise AttributeError(f"Instrument has no field {k!r}")
            setattr(d, k, v)
        return d

    @property
    def is_synth(self):
        return self.synth is not None

    def map_vel(self, v: float) -> int:
        x = min(max(v, 1.0), 127.0) / 127.0
        return int(round(min(127, max(1, self.vel_lo + (self.vel_hi - self.vel_lo) * x ** self.vel_gamma))))


# GM percussion note numbers (channel 10)
GM_DRUMS = {
    "kick": 36, "kick2": 35, "rim": 37, "snare": 38, "clap": 39, "snare2": 40, "tom_floor_lo": 41, "hat": 42,
    "tom_floor_hi": 43, "hat_pedal": 44, "tom_lo": 45, "hat_open": 46, "tom_lomid": 47, "tom_himid": 48,
    "crash": 49, "tom_hi": 50, "ride": 51, "china": 52, "ride_bell": 53, "tambourine": 54, "splash": 55,
    "cowbell": 56, "crash2": 57, "vibraslap": 58, "ride2": 59, "bongo_hi": 60, "bongo_lo": 61, "conga_mute": 62,
    "conga_hi": 63, "conga_lo": 64, "timbale_hi": 65, "timbale_lo": 66, "agogo_hi": 67, "agogo_lo": 68,
    "cabasa": 69, "maracas": 70, "guiro_short": 73, "guiro_long": 74, "claves": 75, "wood_hi": 76, "wood_lo": 77,
    "cuica_mute": 78, "cuica_open": 79, "triangle_mute": 80, "triangle": 81, "shaker": 82, "bells": 83,
}

ARTS = {  # duration factor, velocity add
    None: (0.92, 0), "normal": (0.92, 0), "legato": (1.0, 0), "tenuto": (1.0, 0), "staccato": (0.45, -6),
    "marcato": (0.78, 12), "ghost": (0.7, -40), "ring": (1.0, 0), "pizz": (0.5, 0), "exact": (1.0, 0),
    "hit": (1.0, 0),
}
LEGATO_OVERLAP_S = 0.035


# --------------------------------------------------------------------------------------------- notes and tracks
@dataclass
class Note:
    beat: float
    dur: float
    pitch: int
    vel: float
    art: str | None = None
    orn: str | None = None
    kw: dict = field(default_factory=dict)


@dataclass
class CNote:
    """A compiled note: ticks for MIDI, seconds for synths and analysis."""
    on: int
    off: int
    pitch: int
    vel: int            # instrument-mapped MIDI velocity
    mvel: float         # musical velocity (before the instrument curve), used by synths
    t0: float
    t1: float
    chan: int = 0       # voice index (0/1) for mono tracks
    kw: dict = field(default_factory=dict)
    slide: tuple | None = None   # (semitones_from, seconds)
    vib: bool = False


class Section:
    """A run of bars. piece.section("A", 8) appends it after the previous section."""

    def __init__(self, piece, name, bar0, bars):
        self.piece, self.name, self.bar0, self.bars = piece, name, bar0, bars

    @property
    def start(self) -> float:
        return self.piece.bar(self.bar0)

    @property
    def end(self) -> float:
        return self.piece.bar(self.bar0 + self.bars)

    def b(self, bar: float, beat: float = 0.0) -> float:
        """Absolute beat of (bar, beat) counted from this section's first bar (0-based). Fractional bars work."""
        whole = int(math.floor(bar))
        frac = bar - whole
        base = self.piece.bar(self.bar0 + whole)
        return base + frac * self.piece.bar_len(self.bar0 + whole) + beat

    @property
    def bar_len(self) -> float:
        return self.piece.bar_len(self.bar0)

    def __repr__(self):
        return f"Section({self.name} bars {self.bar0}-{self.bar0 + self.bars} beats {self.start:g}-{self.end:g})"


class Track:
    """A line for one instrument. All `beat` arguments are absolute beats (use Section.b to get them)."""

    def __init__(self, piece, name, inst: Instrument):
        self.piece, self.name, self.inst = piece, name, inst
        self.notes: list[Note] = []
        self.expr_segs: list = []      # (b0, b1, v0, v1, shape)
        self.cc_events: list = []      # (beat, cc, value): raw controller events
        self.compiled = None

    # ---- single notes
    def note(self, beat, pitch, dur, vel=80, art=None, orn=None, **kw) -> float:
        """One note. pitch: MIDI number or a name ("D4"). Returns the beat where the note ends."""
        p = n(pitch) if not isinstance(pitch, (int, np.integer)) else int(pitch)
        self.notes.append(Note(float(beat), float(dur), p, float(vel), art, orn, dict(kw)))
        return beat + dur

    def notes_seq(self, beat, pitches, durs, vel=80, art=None) -> float:
        """Consecutive notes from lists of pitches (None = rest) and durations (or one duration)."""
        if isinstance(durs, (int, float)):
            durs = [durs] * len(pitches)
        b = beat
        for p, d in zip(pitches, durs):
            if p is not None:
                self.note(b, p, d, vel, art)
            b += d
        return b

    def play(self, motif: Motif, at: float, mode: Mode | None = None, octave: int = 0, vel: float = 80,
             dyn=None, art=None, transpose: int = 0) -> float:
        """Place a motif at beat `at` in `mode` (default: the piece mode). dyn shapes velocity across the
        phrase: None, "arch" (rise to the middle, fall), "cresc", "dim", (v0, v1) multipliers, or a list.
        art is the default articulation ("legato" for bowed lines). Returns the beat after the motif."""
        mode = mode or self.piece.mode
        k = len(motif.notes)
        contour = _contour(dyn, k)
        b = at + motif.offset
        for i, x in enumerate(motif.notes):
            if x.deg is not None:
                p = mode.pitch(x.deg, octave, x.alt) + transpose
                kw = {"upper": mode.neighbour(p, 1), "lower": mode.neighbour(p, -1)}
                self.notes.append(Note(b, x.dur, p, vel * x.vel * contour[i], x.art or art, x.orn, kw))
            b += x.dur
        return b

    def chord(self, beat, pitches, dur, vel=70, strum=0.0, art=None, **kw) -> float:
        """Notes together. strum: seconds between successive notes (plucked spread, e.g. 0.015)."""
        for i, p in enumerate(pitches):
            k = dict(kw)
            if strum:
                k["delay_s"] = i * strum
            self.note(beat, p, dur, vel * (1.0 - 0.04 * i), art, None, **k)
        return beat + dur

    def arp(self, start, end, pitches, step=0.5, order="up", vel=70, art=None, accent_every=None, dyn=None,
            ring=1.0) -> float:
        """Arpeggio over [start, end) at `step` beats. order: up, down, updown, or a list of indices into
        `pitches`. ring > 1 lets each note sound for ring x step (dulcimer strings ring on)."""
        ps = list(pitches)
        if order == "up":
            seq = list(range(len(ps)))
        elif order == "down":
            seq = list(range(len(ps)))[::-1]
        elif order == "updown":
            seq = list(range(len(ps))) + list(range(len(ps) - 2, 0, -1))
        else:
            seq = list(order)
        count = int(round((end - start) / step))
        contour = _contour(dyn, count)
        for i in range(count):
            p = ps[seq[i % len(seq)]]
            v = vel * contour[i]
            if accent_every and i % accent_every == 0:
                v *= 1.15
            self.note(start + i * step, p, step * ring, v, art)
        return end

    def drone(self, start, end, pitches, vel=70, art="exact", **kw) -> float:
        """Held notes over [start, end) (no humanised start: drones are the floor of the ensemble)."""
        if isinstance(pitches, (int, str)):
            pitches = [pitches]
        for p in pitches:
            self.note(start, p, end - start, vel, art, None, **kw)
        return end

    def tremolo(self, beat, dur, pitch, rate=0.125, vel=60, dyn=None) -> float:
        """Rapid repeated strokes (dulcimer tremolo, bowed tremolo)."""
        cnt = max(1, int(round(dur / rate)))
        contour = _contour(dyn, cnt)
        for i in range(cnt):
            self.note(beat + i * rate, pitch, rate * 1.6, vel * contour[i] * (1.0 if i % 2 == 0 else 0.86), "hit")
        return beat + dur

    # ---- percussion
    def _drum(self, drum):
        if isinstance(drum, (int, np.integer)):
            return int(drum), {}
        if not self.inst.drums and not self.inst.drum_map and isinstance(drum, str):
            return n(drum), {}          # pitched percussion (timpani): a note name
        m = self.inst.drum_map or GM_DRUMS
        if drum not in m:
            raise KeyError(f"{self.name}: unknown drum {drum!r} (known: {', '.join(m)})")
        return m[drum], {"stroke": drum}

    def hit(self, beat, drum, vel=90, dur=0.25, **kw) -> float:
        p, k = self._drum(drum)
        k.update(kw)
        self.notes.append(Note(float(beat), dur, p, float(vel), "hit", None, k))
        return beat + dur

    def flam(self, beat, drum, vel=90) -> float:
        p, k = self._drum(drum)
        self.notes.append(Note(float(beat), 0.25, p, float(vel), "hit", "flam", k))
        return beat + 0.25

    def roll(self, beat, dur, drum, vel0=50, vel1=90, rate=0.0625, accent_end=True) -> float:
        """A roll: strokes every `rate` beats with a velocity ramp vel0 -> vel1 (and an accented last stroke)."""
        cnt = max(2, int(round(dur / rate)))
        for i in range(cnt):
            v = vel0 + (vel1 - vel0) * i / (cnt - 1)
            v *= 1.0 if i % 2 == 0 else 0.9
            self.hit(beat + i * rate, drum, v, dur=rate * 2)
        if accent_end:
            self.hit(beat + dur, drum, min(127, vel1 * 1.15))
        return beat + dur

    def pattern(self, start, bars, spec, vel=90, steps=None, swing=0.0, drum=None) -> float:
        """Drum grid. spec: a string (with `drum`) or {drum: string}. One string holds one or more bars
        separated by '|' and is cycled over `bars` bars. A plain string without `drum` plays the first drum of
        the instrument's drum_map. Steps per bar = the length of each bar's string,
        so 16 chars = sixteenths in 4/4 and 12 chars = triplet eighths (the 6/8-over-4/4 gallop).
        Step characters: X accent, x hit, o soft, g ghost, f flam, r roll (3 strokes in the step),
        . or - rest. Spaces are ignored. swing delays every second step by swing x step."""
        if isinstance(spec, str):
            spec = {drum if drum is not None else next(iter(self.inst.drum_map or GM_DRUMS)): spec}
        bar0 = self.piece.bar_index(start)
        for dname, s in spec.items():
            segs = [x.replace(" ", "") for x in s.split("|")]
            for i in range(bars):
                seg = segs[i % len(segs)]
                nb = bar0 + i
                bl = self.piece.bar_len(nb)
                st = steps or len(seg)
                sd = bl / st
                b0 = self.piece.bar(nb)
                for j, ch in enumerate(seg):
                    if ch in ".-":
                        continue
                    t = b0 + j * sd + (swing * sd if j % 2 == 1 else 0.0)
                    f = {"X": 1.25, "x": 1.0, "o": 0.75, "g": 0.4, "f": 1.0, "r": 0.8}[ch]
                    if ch == "f":
                        self.flam(t, dname, vel * f)
                    elif ch == "r":
                        for q in range(3):
                            self.hit(t + q * sd / 3, dname, vel * f * (0.8 + 0.1 * q), dur=sd / 2)
                    else:
                        self.hit(t, dname, vel * f, dur=sd)
        return self.piece.bar(bar0 + bars)

    # ---- expression (CC11)
    def expr(self, beat, value) -> None:
        """Set the phrase expression (CC11, 0-127) from `beat` on."""
        self.expr_segs.append((float(beat), float(beat), float(value), float(value), "lin"))

    def curve(self, b0, b1, v0, v1, shape="ease") -> None:
        """Expression ramp v0 -> v1 over [b0, b1]. shape: lin, ease (smoothstep), exp (slow then fast)."""
        self.expr_segs.append((float(b0), float(b1), float(v0), float(v1), shape))

    def swell(self, b0, b1, lo=50, hi=110, peak=0.6) -> None:
        """Rise lo -> hi until b0 + peak*(b1-b0), then fall back to lo at b1 (bowed and blown sustains)."""
        bp = b0 + peak * (b1 - b0)
        self.curve(b0, bp, lo, hi, "ease")
        self.curve(bp, b1, hi, lo, "ease")

    def cc(self, beat, number, value) -> None:
        """A raw controller event (not CC11: use expr/curve/swell for expression)."""
        self.cc_events.append((float(beat), int(number), int(value)))

    def double(self, other: "Track", start=None, end=None, interval=0, vel=0.8, delay=0.0) -> None:
        """Copy another track's notes in [start, end) transposed by `interval` semitones (octave doublings,
        heterophony). Ornaments are not copied (a doubling instrument plays plainer)."""
        for x in other.notes:
            if (start is None or x.beat >= start) and (end is None or x.beat < end):
                self.notes.append(Note(x.beat + delay, x.dur, x.pitch + interval, x.vel * vel, x.art, None,
                                       {k: v for k, v in x.kw.items() if k not in ("upper", "lower")}))

    def _expr_at(self, beat: float) -> float:
        """Phrase expression at a beat. The latest event wins: a ramp counts from its start while it runs,
        a finished ramp or a step holds its end value from its end on."""
        val, anchor = float(self.inst.expr), -1e18
        for (b0, b1, v0, v1, shape) in self.expr_segs:
            if b1 > b0 and b0 <= beat <= b1:
                if b0 >= anchor:
                    x = (beat - b0) / (b1 - b0)
                    if shape == "ease":
                        x = x * x * (3 - 2 * x)
                    elif shape == "exp":
                        x = x * x
                    val, anchor = v0 + (v1 - v0) * x, b0
            elif b1 <= beat and b1 >= anchor:
                val, anchor = v1, b1
        return val


def _contour(dyn, k):
    if k <= 0:
        return []
    if dyn is None:
        return [1.0] * k
    if isinstance(dyn, (list, tuple)) and len(dyn) == k and k != 2:
        return [float(v) for v in dyn]
    xs = np.linspace(0.0, 1.0, k) if k > 1 else np.array([0.5])
    if dyn == "arch":
        return list(0.86 + 0.22 * np.sin(np.pi * xs))
    if dyn == "cresc":
        return list(0.78 + 0.3 * xs)
    if dyn == "dim":
        return list(1.08 - 0.3 * xs)
    if isinstance(dyn, (list, tuple)) and len(dyn) == 2:
        return list(dyn[0] + (dyn[1] - dyn[0]) * xs)
    raise ValueError(f"unknown dyn {dyn!r}")


def _rng(seed: int, *names) -> np.random.Generator:
    key = zlib.crc32(("/".join(str(x) for x in names)).encode()) ^ (seed * 2654435761 & 0xFFFFFFFF)
    return np.random.default_rng(key)


# --------------------------------------------------------------------------------------------- the piece
class Piece:
    """A piece of music: tempo map, meter map, sections and tracks.

    Piece("style_kingdom", seed=7, bpm=92, meter=(4, 4), key="D", mode="mixolydian")
      .track(name, instrument)      -> Track
      .section(name, bars, meter=None, bpm=None) -> Section (appended after the last one)
      .bar(i) / .at(bar, beat) / .bar_len(i) / .bar_index(beat)
      .set_tempo(beat, bpm), .ramp(b0, b1, bpm0, bpm1)        base tempo (step / linear)
      .rit(b0, b1, to=0.9), .accel(b0, b1, to=1.05)           temporary factors (back a tempo after b1)
      .breathe(beat, beats=1.0, depth=0.05)                   a small phrase-end breath into `beat`
      .fermata(beat, beats, stretch=1.6)                      hold time still over [beat, beat+beats]
      .mark(beat, text)                                       extra marker (section starts are automatic)
      .set_end(beat)                                          musical end (default: end of the last section)
    Attributes for render.py: kind ("track" | "loop" | "cue"), length_range (s), tail_s, xfade_s, trim_s,
    trim_fade_s, mix (dict: reverb / bus / master overrides), out (default output path).
    """

    def __init__(self, name, seed=1, bpm=92.0, meter=(4, 4), key="D", mode="dorian", octave=4, drift_ms=6.0):
        self.name = name
        self.seed = int(seed)
        self.mode = Mode(key, mode, octave)
        self.meters = [(0, meter[0], meter[1])]
        self.tempo_pts = [(0.0, float(bpm), "step")]
        self.factors = []          # (b0, b1, f0, f1)
        self.tracks: dict[str, Track] = {}
        self.sections: list[Section] = []
        self.markers: list = []
        self.next_bar = 0
        self.end_beat = None
        self.drift_ms = drift_ms
        self.kind = "track"
        self.length_range = None
        self.tail_s = 6.0
        self.xfade_s = 3.0
        self.trim_s = None
        self.trim_fade_s = 0.3
        self.mix = {}
        self.out = None
        self._compiled = False

    # ---- structure
    def track(self, name: str, inst: Instrument) -> Track:
        if name in self.tracks:
            raise ValueError(f"track {name!r} exists")
        t = Track(self, name, inst)
        self.tracks[name] = t
        return t

    def section(self, name: str, bars: int, meter=None, bpm=None) -> Section:
        bar0 = self.next_bar
        if meter is not None:
            self.set_meter(bar0, meter)
        s = Section(self, name, bar0, bars)
        if bpm is not None:
            self.set_tempo(s.start, bpm)
        self.sections.append(s)
        self.next_bar = bar0 + bars
        return s

    def set_meter(self, bar: int, meter) -> None:
        self.meters = [m for m in self.meters if m[0] != bar] + [(bar, meter[0], meter[1])]
        self.meters.sort()

    def _meter_at_bar(self, i):
        cur = self.meters[0]
        for m in self.meters:
            if m[0] <= i:
                cur = m
        return cur

    def bar_len(self, i: int) -> float:
        _, num, den = self._meter_at_bar(i)
        return num * 4.0 / den

    def bar(self, i: float) -> float:
        """Beat at the start of bar i (0-based)."""
        i = int(i)
        b = 0.0
        for k in range(i):
            b += self.bar_len(k)
        return b

    def at(self, bar, beat=0.0) -> float:
        return self.bar(bar) + beat

    def bar_index(self, beat: float) -> int:
        i, b = 0, 0.0
        while b + self.bar_len(i) <= beat + 1e-9:
            b += self.bar_len(i)
            i += 1
        return i

    def mark(self, beat, text):
        self.markers.append((float(beat), str(text)))

    def set_end(self, beat):
        self.end_beat = float(beat)

    @property
    def end(self) -> float:
        if self.end_beat is not None:
            return self.end_beat
        if self.sections:
            return self.sections[-1].end
        return max((x.beat + x.dur for t in self.tracks.values() for x in t.notes), default=0.0)

    # ---- tempo
    def set_tempo(self, beat, bpm):
        self.tempo_pts = [p for p in self.tempo_pts if abs(p[0] - beat) > 1e-9] + [(float(beat), float(bpm), "step")]
        self.tempo_pts.sort()

    def ramp(self, b0, b1, bpm0, bpm1):
        """Linear base-tempo change bpm0 -> bpm1 over [b0, b1], then bpm1 holds."""
        self.tempo_pts = [p for p in self.tempo_pts if not (b0 - 1e-9 <= p[0] <= b1 + 1e-9)]
        self.tempo_pts += [(float(b0), float(bpm0), "lin"), (float(b1), float(bpm1), "step")]
        self.tempo_pts.sort()

    def rit(self, b0, b1, to=0.9):
        """Ritardando: tempo factor 1 -> `to` over [b0, b1], back to 1 after b1."""
        self.factors.append((float(b0), float(b1), 1.0, float(to)))

    def accel(self, b0, b1, to=1.05):
        self.factors.append((float(b0), float(b1), 1.0, float(to)))

    def breathe(self, beat, beats=1.0, depth=0.05):
        """A breath at a phrase end: slow by `depth` over the `beats` before `beat`, a tempo at `beat`."""
        self.factors.append((float(beat - beats), float(beat), 1.0, 1.0 - depth))

    def fermata(self, beat, beats=1.0, stretch=1.6):
        self.factors.append((float(beat), float(beat + beats), 1.0 / stretch, 1.0 / stretch))

    def _base_bpm(self, b):
        pts = self.tempo_pts
        idx = bisect.bisect_right([p[0] for p in pts], b) - 1
        idx = max(idx, 0)
        b0, v0, kind = pts[idx]
        if kind == "lin" and idx + 1 < len(pts):
            b1, v1, _ = pts[idx + 1]
            return v0 + (v1 - v0) * (b - b0) / max(1e-9, b1 - b0)
        return v0

    def _factor(self, b):
        f = 1.0
        for (b0, b1, f0, f1) in self.factors:
            if b0 <= b < b1:
                x = (b - b0) / max(1e-9, b1 - b0)
                f *= f0 + (f1 - f0) * (x * x if f1 < f0 else x)
        return f

    def _build_tempo(self, horizon_beats):
        """Stepped tempo table: list of (tick, usec_per_quarter). Shared by MIDI and synth timing."""
        cells = int(math.ceil(horizon_beats / TEMPO_RES)) + 1
        table = []
        last = None
        varying = bool(self.factors) or any(p[2] == "lin" for p in self.tempo_pts)
        change_beats = sorted({p[0] for p in self.tempo_pts} | {f[0] for f in self.factors} | {f[1] for f in self.factors})
        if not varying:
            for b, bpm, _ in self.tempo_pts:
                us = int(round(60e6 / bpm))
                if us != last:
                    table.append((int(round(b * TPQ)), us))
                    last = us
        else:
            for k in range(cells):
                b = k * TEMPO_RES
                bpm = self._base_bpm(b + TEMPO_RES * 0.5) * self._factor(b + TEMPO_RES * 0.5)
                us = int(round(60e6 / bpm))
                if us != last:
                    table.append((int(round(b * TPQ)), us))
                    last = us
        del change_beats
        if table[0][0] != 0:
            table.insert(0, (0, int(round(60e6 / self.tempo_pts[0][1]))))
        self._tempo_ticks = [t for t, _ in table]
        self._tempo_us = [u for _, u in table]
        secs = [0.0]
        for i in range(1, len(table)):
            secs.append(secs[-1] + (table[i][0] - table[i - 1][0]) * table[i - 1][1] / 1e6 / TPQ)
        self._tempo_secs = secs
        self.tempo_table = table

    def tick_to_sec(self, tick: float) -> float:
        i = bisect.bisect_right(self._tempo_ticks, tick) - 1
        i = max(i, 0)
        return self._tempo_secs[i] + (tick - self._tempo_ticks[i]) * self._tempo_us[i] / 1e6 / TPQ

    def sec_to_tick(self, sec: float) -> float:
        i = bisect.bisect_right(self._tempo_secs, sec) - 1
        i = max(i, 0)
        return self._tempo_ticks[i] + (sec - self._tempo_secs[i]) * 1e6 * TPQ / self._tempo_us[i]

    def seconds(self, beat: float) -> float:
        """Seconds at a beat (after compile, or builds the tempo map on demand)."""
        if not hasattr(self, "_tempo_ticks"):
            self._build_tempo(max(self.end, beat) + 64)
        return self.tick_to_sec(beat * TPQ)

    def bpm_at(self, beat: float) -> float:
        i = max(0, bisect.bisect_right(self._tempo_ticks, beat * TPQ) - 1)
        return 60e6 / self._tempo_us[i]

    # ---- compile
    def compile(self):
        """Expand ornaments and articulations, humanise, quantise. Fills track.compiled with
        {"notes": [CNote], "chans": n, "ctrl": {chan: [(tick, kind, value)]}} and returns self."""
        horizon = self.end + 64
        for t in self.tracks.values():
            for x in t.notes:
                horizon = max(horizon, x.beat + x.dur + 8)
        self._build_tempo(horizon)
        self.duration_s = self.seconds(self.end)
        drift = self._drift_curve(horizon)
        for name, tr in self.tracks.items():
            tr.compiled = self._compile_track(tr, drift)
        self._compiled = True
        return self

    def _drift_curve(self, horizon):
        rng = _rng(self.seed, "ensemble-drift")
        knots = int(horizon / 2) + 3
        vals = rng.normal(0.0, self.drift_ms / 2000.0, knots)
        vals = np.clip(vals, -self.drift_ms / 1000.0, self.drift_ms / 1000.0)

        def f(beat):
            x = beat / 2.0
            i = int(math.floor(x))
            fr = x - i
            fr = 0.5 - 0.5 * math.cos(math.pi * fr)
            return vals[min(i, knots - 1)] * (1 - fr) + vals[min(i + 1, knots - 1)] * fr
        return f

    def _metric_accent(self, beat):
        bi = self.bar_index(beat)
        pos = beat - self.bar(bi)
        _, num, den = self._meter_at_bar(bi)
        if abs(pos) < 1e-6:
            return 1.0
        compound = den == 8 and num % 3 == 0
        if compound:
            if abs(pos / 1.5 - round(pos / 1.5)) < 1e-6:
                return 0.55
            return -0.2 if abs(pos * 2 - round(pos * 2)) < 1e-6 else -0.35
        if num == 4 and abs(pos - 2.0) < 1e-6:
            return 0.55
        if abs(pos - round(pos)) < 1e-6:
            return 0.2
        return -0.25

    def _expand(self, tr: Track):
        """Ornaments and articulations -> raw note dicts in beats (before humanisation)."""
        inst = tr.inst
        out = []
        notes = sorted(tr.notes, key=lambda x: (x.beat, x.pitch))
        for x in notes:
            dur_f, vadd = ARTS.get(x.art, ARTS[None])
            base = dict(beat=x.beat, dur=x.dur * dur_f, pitch=x.pitch, vel=x.vel + vadd, art=x.art, kw=dict(x.kw),
                        exact=(x.art in ("exact",)), slide=None, legato=(x.art == "legato"), orig_beat=x.beat)
            if x.art == "ring":
                base["dur"] = max(x.dur, 2.0)
            bpm = self._base_bpm(x.beat)
            ms = bpm / 60.0 / 1000.0            # beats per millisecond
            up = x.kw.get("upper", self.mode.neighbour(x.pitch, 1))
            lo = x.kw.get("lower", self.mode.neighbour(x.pitch, -1))
            o = x.orn
            if o in ("grace_up", "grace_down"):
                g = 70 * ms
                out.append(dict(base, beat=x.beat - g, dur=g * 1.2, pitch=up if o == "grace_up" else lo,
                                vel=x.vel * 0.72, legato=True, grace=True))
                out.append(base)
            elif o in ("mordent", "lmordent"):
                g = 55 * ms
                nb = up if o == "mordent" else lo
                out.append(dict(base, dur=g * 1.1, legato=True))
                out.append(dict(base, beat=x.beat + g, dur=g * 1.1, pitch=nb, vel=x.vel * 0.8, legato=True))
                out.append(dict(base, beat=x.beat + 2 * g, dur=max(base["dur"] - 2 * g, g), vel=x.vel * 0.9))
            elif o == "turn":
                g = 60 * ms
                seq = [up, x.pitch, lo, x.pitch]
                for i, p in enumerate(seq):
                    last = i == len(seq) - 1
                    out.append(dict(base, beat=x.beat + i * g, dur=(max(base["dur"] - 3 * g, g) if last else g * 1.1),
                                    pitch=p, vel=x.vel * (0.95 if i == 0 else 0.82), legato=True))
            elif o == "trill":
                g = 1000.0 / 13.0 * ms
                cnt = max(3, int(base["dur"] / g))
                for i in range(cnt):
                    out.append(dict(base, beat=x.beat + i * g, dur=g * 1.15, pitch=(x.pitch if i % 2 == 0 else up),
                                    vel=x.vel * (1.0 if i == 0 else 0.8), legato=True))
            elif o in ("slide", "slide_down"):
                out.append(dict(base, slide=(-1 if o == "slide" else 1, 0.12)))
            elif o == "slide_from":
                out.append(dict(base, slide=(x.kw.get("semis", -2), x.kw.get("time", 0.15))))
            elif o == "flam":
                out.append(dict(base, beat=x.beat - 28 * ms, vel=x.vel * 0.55, dur=base["dur"]))
                out.append(base)
            elif o == "roll":
                g = 1000.0 / 18.0 * ms
                cnt = max(3, int(x.dur / g))
                for i in range(cnt):
                    out.append(dict(base, beat=x.beat + i * g, dur=g * 1.5, vel=x.vel * (0.7 + 0.3 * i / cnt)))
            elif o is None:
                out.append(base)
            else:
                raise ValueError(f"{tr.name}: unknown ornament {o!r}")
            if inst.mono and x.art == "slide":
                out[-1]["slide"] = ("prev", 0.14)
        return out

    def _compile_track(self, tr: Track, drift):
        inst = tr.inst
        rng = _rng(self.seed, "track", tr.name)
        raw = self._expand(tr)
        raw.sort(key=lambda d: (d["beat"], d["pitch"]))
        cnotes = []
        jit = inst.timing_ms / 1000.0
        for d in raw:
            b = d["beat"]
            bpm = self._base_bpm(b)
            if d["exact"]:
                off_s = 0.0
            else:
                off_s = drift(b) + inst.lag_ms / 1000.0 + float(np.clip(rng.normal(0.0, jit), -MAX_JITTER_S, MAX_JITTER_S))
                off_s = float(np.clip(off_s, -MAX_JITTER_S, MAX_JITTER_S))
            delay = d["kw"].get("delay_s", 0.0)
            vel = d["vel"]
            if not inst.drums and not inst.perc and not d.get("grace") and inst.accent:
                vel += inst.accent * self._metric_accent(d["orig_beat"])
            vel *= 1.0 + float(rng.normal(0.0, 0.035))
            vel = float(np.clip(vel, 1, 127))
            on_s = self.seconds(b) + off_s + delay
            on = int(round(self.sec_to_tick(max(0.0, on_s))))
            dur_jit = 1.0 + float(rng.normal(0.0, 0.025)) if not d["exact"] else 1.0
            end_beat = b + d["dur"] * dur_jit
            off = int(round(self.sec_to_tick(self.seconds(end_beat) + off_s + delay)))
            off = max(off, on + 12)
            cnotes.append(dict(on=on, off=off, pitch=d["pitch"], mvel=vel, kw=d["kw"], slide=d["slide"],
                               legato=d["legato"], bpm=bpm))
        cnotes.sort(key=lambda c: (c["on"], c["pitch"]))
        # legato overlap (mono lines) and same-pitch clean-up
        if inst.mono:
            for i in range(len(cnotes) - 1):
                c = cnotes[i]
                j = i + 1
                while j < len(cnotes) and cnotes[j]["on"] <= c["on"] + 10:
                    j += 1
                if j >= len(cnotes):
                    continue
                nx = cnotes[j]
                if c["legato"] and nx["on"] - c["off"] < TPQ // 4:
                    ov = int(round(self.sec_to_tick(self.tick_to_sec(nx["on"]) + LEGATO_OVERLAP_S))) - nx["on"]
                    c["off"] = nx["on"] + ov
        last_off = {}
        for c in cnotes:
            p = c["pitch"]
            if p in last_off and last_off[p]["off"] > c["on"] - 2 and not inst.mono:
                last_off[p]["off"] = max(last_off[p]["on"] + 6, c["on"] - 2)
            last_off[p] = c
        # voices (channels): mono expressive lines alternate 2 channels
        chans = 2 if inst.mono and not inst.drums and not inst.is_synth else 1
        out = []
        prev_pitch = None
        for i, c in enumerate(cnotes):
            ch = (i % 2) if chans == 2 else 0
            sl = c["slide"]
            if sl and sl[0] == "prev":
                if prev_pitch is not None and 0 < abs(prev_pitch - c["pitch"]) <= inst.bend_range:
                    sl = (prev_pitch - c["pitch"], sl[1])
                else:
                    sl = (-1 if prev_pitch is None or prev_pitch < c["pitch"] else 1, 0.1)
            if sl and abs(sl[0]) > inst.bend_range:
                sl = (math.copysign(inst.bend_range, sl[0]), sl[1])
            t0 = self.tick_to_sec(c["on"])
            t1 = self.tick_to_sec(c["off"])
            vib = bool(inst.vibrato) and (t1 - t0) >= inst.vibrato.get("min_dur", 0.45)
            out.append(CNote(c["on"], c["off"], c["pitch"], inst.map_vel(c["mvel"]), c["mvel"], t0, t1, ch,
                             c["kw"], sl, vib))
            prev_pitch = c["pitch"]
        ctrl = self._controls(tr, out, chans, rng)
        ccs = [(int(round(b * TPQ)), num, val) for (b, num, val) in tr.cc_events]
        return {"notes": out, "chans": chans, "ctrl": ctrl, "cc": ccs}

    def _controls(self, tr: Track, notes, chans, rng):
        """Per-channel CC11 (expression) and pitch-bend streams: [(tick, 'cc11'|'bend', value)]."""
        inst = tr.inst
        ctrl = {ch: [] for ch in range(chans)}
        if inst.drums or not notes:
            return ctrl
        dt = 1.0 / CTRL_RATE
        if not inst.mono:
            t_end = max(nn.t1 for nn in notes) + inst.release_s + 0.5
            last = None
            for k in range(int(t_end / dt) + 1):
                t = k * dt
                beat = self.sec_to_tick(t) / TPQ
                v = int(round(min(127, max(0, tr._expr_at(beat)))))
                if v != last:
                    ctrl[0].append((int(round(self.sec_to_tick(t))), "cc11", v))
                    last = v
            return ctrl
        vib = inst.vibrato or {}
        gidx = {id(nn): i for i, nn in enumerate(notes)}
        for ch in range(chans):
            mine = [nn for nn in notes if nn.chan == ch]
            last_cc = last_bend = None
            for j, nn in enumerate(mine):
                nxt_on = mine[j + 1].t0 if j + 1 < len(mine) else nn.t1 + 4.0
                t_stop = min(nn.t1 + inst.release_s, nxt_on - 0.002)
                gi = gidx[id(nn)]
                prev = notes[gi - 1] if gi > 0 else None
                connected = prev is not None and nn.t0 - prev.t1 < 0.03
                d = max(nn.t1 - nn.t0, 0.02)
                vr = vib.get("rate", 5.6) * (1.0 + float(rng.normal(0, 0.05)))
                vd = vib.get("depth", 0.12) * (1.0 + float(rng.normal(0, 0.15)))
                vdel = vib.get("delay", 0.28)
                vrise = vib.get("rise", 0.35)
                ph = float(rng.uniform(0, 2 * math.pi))
                k0 = int(math.floor((nn.t0 - 0.004) / dt))
                k1 = int(math.ceil(t_stop / dt))
                for k in range(k0, k1 + 1):
                    t = max(nn.t0 - 0.004, k * dt)
                    if k == k0:
                        t = nn.t0 - 0.004
                    beat = self.sec_to_tick(max(t, 0.0)) / TPQ
                    base = tr._expr_at(beat)
                    u = t - nn.t0
                    m = _note_shape(inst.shape, u, d, connected)
                    cc = int(round(min(127, max(0, base * m))))
                    bend = 0.0
                    if nn.slide:
                        s_from, s_time = nn.slide
                        if u < s_time:
                            x = max(0.0, u) / s_time
                            bend += s_from * (1.0 - (1.0 - (1.0 - x) ** 2)) if u >= 0 else s_from
                    if nn.vib and u > vdel:
                        ramp = min(1.0, (u - vdel) / vrise)
                        bend += vd * ramp * math.sin(2 * math.pi * vr * (u - vdel) + ph)
                    bv = int(round(max(-8192, min(8191, bend / inst.bend_range * 8191))))
                    tick = int(round(self.sec_to_tick(max(t, 0.0))))
                    if k == k0:
                        tick = max(0, nn.on - 2)
                    if cc != last_cc:
                        ctrl[ch].append((tick, "cc11", cc))
                        last_cc = cc
                    if bv != last_bend:
                        ctrl[ch].append((tick, "bend", bv))
                        last_bend = bv
        return ctrl

    # ---- MIDI export
    def write_midi(self, path, tracks=None, stem=False, tail_s=0.0):
        """Write a type-1 MIDI file. tracks: names to include (default all). stem=True writes the stem form
        used for rendering: channels from 0 (9 for kits), pan centred (panning is done in the mix), and an
        end marker `tail_s` after the music so FluidSynth renders the release tails."""
        import mido
        if not self._compiled:
            self.compile()
        mf = mido.MidiFile(type=1, ticks_per_beat=TPQ)
        cond = mido.MidiTrack()
        mf.tracks.append(cond)
        ev = [(0, 0, mido.MetaMessage("track_name", name=self.name, time=0))]
        for (bar, num, den) in self.meters:
            ev.append((int(round(self.bar(bar) * TPQ)), 1, mido.MetaMessage("time_signature", numerator=num,
                                                                            denominator=den, time=0)))
        for tick, us in self.tempo_table:
            ev.append((tick, 2, mido.MetaMessage("set_tempo", tempo=us, time=0)))
        for s in self.sections:
            ev.append((int(round(s.start * TPQ)), 3, mido.MetaMessage("marker", text=s.name, time=0)))
        for b, txt in self.markers:
            ev.append((int(round(b * TPQ)), 3, mido.MetaMessage("marker", text=txt, time=0)))
        end_tick = int(round(self.sec_to_tick(self.duration_s + tail_s)))
        _emit(cond, ev, end_tick)
        names = tracks or list(self.tracks)
        chan_next = 0
        for name in names:
            tr = self.tracks[name]
            if tr.inst.is_synth and stem:
                continue
            comp = tr.compiled
            if tr.inst.drums:
                chmap = {0: 9}
            elif stem:
                chmap = {v: v for v in range(comp["chans"])}
            else:
                free = [c for c in range(16) if c != 9]
                chmap = {}
                for v in range(comp["chans"]):
                    chmap[v] = free[chan_next % len(free)]
                    chan_next += 1
            mt = mido.MidiTrack()
            mf.tracks.append(mt)
            ev = [(0, 0, mido.MetaMessage("track_name", name=name, time=0))]
            pan = 64 if stem else int(round(64 + 63 * max(-1.0, min(1.0, tr.inst.pan))))
            for v, ch in chmap.items():
                if tr.inst.is_synth:
                    prog, bank = 0, 0
                else:
                    prog, bank = tr.inst.program, tr.inst.bank
                if not tr.inst.drums:
                    ev.append((0, 1, mido.Message("control_change", channel=ch, control=0, value=bank, time=0)))
                    ev.append((0, 1, mido.Message("control_change", channel=ch, control=32, value=0, time=0)))
                ev.append((0, 2, mido.Message("program_change", channel=ch, program=prog, time=0)))
                for c, val in ((101, 0), (100, 0), (6, tr.inst.bend_range), (38, 0), (101, 127), (100, 127),
                               (7, 100), (10, pan), (91, 0), (93, 0), (11, tr.inst.expr), (64, 0)):
                    ev.append((0, 3, mido.Message("control_change", channel=ch, control=c, value=val, time=0)))
            for v, stream in comp["ctrl"].items():
                ch = chmap.get(v, chmap[0])
                for tick, kind, val in stream:
                    if kind == "cc11":
                        ev.append((tick, 4, mido.Message("control_change", channel=ch, control=11, value=val, time=0)))
                    else:
                        ev.append((tick, 4, mido.Message("pitchwheel", channel=ch, pitch=val, time=0)))
            for tick, num, val in comp["cc"]:
                ev.append((tick, 4, mido.Message("control_change", channel=chmap[0], control=num, value=val, time=0)))
            for c in comp["notes"]:
                ch = chmap.get(c.chan, chmap[0])
                ev.append((c.on, 6, mido.Message("note_on", channel=ch, note=c.pitch, velocity=c.vel, time=0)))
                ev.append((c.off, 5, mido.Message("note_off", channel=ch, note=c.pitch, velocity=0, time=0)))
            _emit(mt, ev, end_tick)
        mf.save(path)
        return path

    # ---- summaries
    def summary(self):
        if not self._compiled:
            self.compile()
        return {
            "name": self.name, "seed": self.seed, "mode": repr(self.mode), "duration_s": round(self.duration_s, 3),
            "sections": [(s.name, round(self.seconds(s.start), 2)) for s in self.sections],
            "tracks": {k: len(t.compiled["notes"]) for k, t in self.tracks.items()},
        }


def _note_shape(shape, u, d, connected):
    """Per-note expression multiplier at u seconds into a note of length d."""
    if shape is None or u < 0:
        return 1.0 if shape is None else (0.86 if connected else 0.7)
    if shape == "bow":
        a = min(0.12, 0.4 * d)
        start = 0.86 if connected else 0.68
        if u < a:
            x = u / a
            return start + (1.0 - start) * (x * x * (3 - 2 * x))
        if d > 0.8:
            x = (u - a) / max(1e-6, d - a)
            if x <= 0.55:
                return 1.0 + 0.07 * math.sin(math.pi * x / 1.1)
            return 1.07 - 0.17 * min(1.0, (x - 0.55) / 0.45)
        return 1.0
    if shape == "breath":
        a = min(0.2, 0.45 * d)
        if u < a:
            x = u / a
            return 0.45 + 0.55 * (x * x * (3 - 2 * x))
        x = (u - a) / max(1e-6, d - a)
        if d > 1.0:
            return 1.0 + 0.06 * math.sin(math.pi * min(1.0, x) * 0.9) - 0.25 * max(0.0, x - 0.75) / 0.25
        return 1.0 - 0.15 * max(0.0, min(1.0, x))
    return 1.0


def _emit(track, ev, end_tick):
    import mido
    ev.sort(key=lambda e: (e[0], e[1]))
    now = 0
    for tick, _, msg in ev:
        tick = max(tick, 0)
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - now)))


# --------------------------------------------------------------------------------------------- CLI
def _demo(path):
    p = Piece("demo", seed=3, bpm=92, key="D", mode="mixolydian")
    vio = p.track("violin", Instrument("violin", program=40, mono=True, shape="bow",
                                       vibrato={"rate": 5.6, "depth": 0.12}))
    a = p.section("A", 4)
    b = vio.play(wheel(), a.b(0), art="legato", dyn="arch")
    vio.play(wheel_answer(), b, art="legato")
    p.compile().write_midi(path)
    return p.summary()


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", metavar="OUT.mid", help="write a 4-bar demo MIDI (the Wheel motif on a violin)")
    a = ap.parse_args()
    if a.demo:
        print(json.dumps(_demo(a.demo)))
    else:
        ap.print_help()
