#!/usr/bin/env python3
"""synths.py: numpy instruments for what the General MIDI soundfont lacks or does badly.

Every instrument renders the same compiled note events as the MIDI tracks (score.CNote: t0, t1, pitch, mvel,
kw) to a float32 stereo stem at 48 kHz. Deterministic: the per-note randomness comes from
numpy.random.default_rng([identity, crc32(track), note index]), and each instrument's character (gong partial
set, clapper hands) from its `identity` parameter alone, so "our gong" sounds the same in every piece.

Instruments (SYNTHS keys) and their note keywords (`Track.note(..., stroke=...)` / `Track.hit(..., drum)`):
  gong       bronze gong, inharmonic partials with beating doublets, a slow high-partial bloom and a slight
             downward pitch settle. stroke="struck" (default) or "bowed" (a swell over the note length, then
             the ring). Params: decay (s), bloom (0..1), bright (0..1), glide, identity.
  bell       small town bell (hum, prime, minor-third tierce, quint, nominal, upper partials). Params: decay.
  hurdy      hurdy-gurdy: stroke="drone" (default; bourdon / mouche strings), "melody" (keyed chanter with a
             key click), "buzz" (trompette coup: the rasping buzz bridge, short, on rhythm). Params: body
             (formant scale), rosin (noise level), flutter, buzz (buzz level).
  jawharp    jaw harp: fixed fundamental (param `fundamental`, MIDI note), each note picks the mouth formant at
             the harmonic nearest its pitch; twang decay; the formant glides between notes. Params: q, decay.
  chant      wordless low voices: overtone drone / chant / hum. kw vowel ("a o u e i m"), vowels (a list,
             morphing across the note), overtones (harmonic numbers to sing through), voices, detune. Params:
             voices, detune_cents, breath, vibrato, overtone_db, far (extra low-pass for "far away").
  framedrum  pitched membrane + skin noise. strokes: dum (centre), doum (deep), tek (rim), slap, mute.
             Params: size (pitch scale), skin (noise level), ring (decay scale).
  claps      hand claps / stamps / knee slaps of a small group. strokes: clap, stamp, slap. Params: hands
             (people), spread_ms, identity.

CLI: python3 tools/music/synths.py demo OUTDIR   renders one example of every instrument to WAV (float).
"""
from __future__ import annotations

import math
import zlib

import numpy as np

SR = 48000
F32 = np.float32


def hz(p: float) -> float:
    return 440.0 * 2.0 ** ((p - 69.0) / 12.0)


def _rng(*keys) -> np.random.Generator:
    ks = []
    for k in keys:
        ks.append(zlib.crc32(k.encode()) if isinstance(k, str) else int(k) & 0xFFFFFFFF)
    return np.random.default_rng(ks)


def smooth_noise(rng, n, rate_hz, sr=SR):
    """Band-limited random curve (unit variance knots at `rate_hz`, cosine-interpolated)."""
    k = max(4, int(n * rate_hz / sr) + 4)
    knots = rng.normal(0.0, 1.0, k)
    x = np.arange(n, dtype=np.float64) * rate_hz / sr
    i = np.floor(x).astype(np.int64)
    f = x - i
    f = 0.5 - 0.5 * np.cos(np.pi * f)
    return knots[i] * (1 - f) + knots[np.minimum(i + 1, k - 1)] * f


def shaped_noise(rng, n, resp, sr=SR):
    """White noise filtered (zero phase) by a magnitude response resp(freqs_hz) -> array."""
    if n <= 0:
        return np.zeros(0)
    m = 1 << int(math.ceil(math.log2(max(n, 16))))
    x = rng.normal(0.0, 1.0, m)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(m, 1.0 / sr)
    X *= resp(f)
    return np.fft.irfft(X, m)[:n]


def bandpass(fc, q):
    def r(f):
        f = np.maximum(f, 1.0)
        return 1.0 / np.sqrt(1.0 + (q * (f / fc - fc / f)) ** 2)
    return r


def lowpass(fc, order=2):
    def r(f):
        return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))
    return r


def highpass(fc, order=2):
    def r(f):
        f = np.maximum(f, 1e-3)
        return 1.0 / np.sqrt(1.0 + (fc / f) ** (2 * order))
    return r


def resonances(f, peaks, floor=0.0):
    """Sum of resonance peaks [(fc, bw, amp)] evaluated at frequencies f."""
    out = np.full_like(np.asarray(f, dtype=np.float64), floor)
    for fc, bw, a in peaks:
        out += a / np.sqrt(1.0 + ((f - fc) / (bw * 0.5)) ** 2)
    return out


def harmonic_table(amps, phases, size=4096):
    """One period of a waveform with harmonic amplitudes amps[0] = 1st harmonic."""
    spec = np.zeros(size // 2 + 1, dtype=np.complex128)
    k = min(len(amps), size // 2 - 1)
    spec[1:k + 1] = np.asarray(amps[:k]) * np.exp(1j * np.asarray(phases[:k]))
    return np.fft.irfft(spec, size) * (size / 2.0)


def wt_read(tables, phase, pos=None):
    """Read wavetable(s) at phase (cycles). tables: (L,) or (K, L); pos: table position 0..K-1 (morph)."""
    if tables.ndim == 1:
        tables = tables[None, :]
    K, L = tables.shape
    x = (phase % 1.0) * L
    i0 = x.astype(np.int64)
    fr = x - i0
    i1 = (i0 + 1) % L
    if K == 1 or pos is None:
        t = tables[0]
        return t[i0] * (1 - fr) + t[i1] * fr
    pos = np.clip(pos, 0, K - 1 - 1e-9)
    k0 = pos.astype(np.int64)
    kf = pos - k0
    k1 = np.minimum(k0 + 1, K - 1)
    a = tables[k0, i0] * (1 - fr) + tables[k0, i1] * fr
    b = tables[k1, i0] * (1 - fr) + tables[k1, i1] * fr
    return a * (1 - kf) + b * kf


def env_adsr(n, sr, a, r, sustain_n, curve=3.0):
    """Attack (smoothstep) over a s, hold to sustain_n samples, then an exponential-ish release over r s."""
    t = np.arange(n) / sr
    e = np.ones(n)
    na = max(1, int(a * sr))
    x = np.clip(t / max(a, 1e-4), 0, 1)
    e = x * x * (3 - 2 * x)
    rel = np.clip((np.arange(n) - sustain_n) / max(1, int(r * sr)), 0, 1)
    e = e * (1 - rel) ** curve
    del na
    return e


def pan_gains(p):
    """Constant-power pan, p in -1..1."""
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def _place(out, start, buf):
    if start >= len(out):
        return
    if start < 0:
        buf = buf[-start:]
        start = 0
    m = min(len(buf), len(out) - start)
    out[start:start + m] += buf[:m]


# --------------------------------------------------------------------------------------------- instruments
class Synth:
    defaults: dict = {}

    def __init__(self, params, track, sr=SR):
        self.p = dict(self.defaults)
        self.p.update(params or {})
        self.track = track
        self.sr = sr
        self.ident = _rng("identity", type(self).__name__, int(self.p.get("identity", 1)))
        self.setup()

    def setup(self):
        pass

    def render(self, note, rng):  # -> (start_sample, (m, 2) array)
        raise NotImplementedError


class Gong(Synth):
    defaults = {"decay": 9.0, "bloom": 0.6, "bright": 0.5, "glide": 0.004, "partials": 34, "identity": 1,
                "level": 0.5}

    def setup(self):
        base = [1.0, 1.506, 2.004, 2.47, 2.985, 3.53, 4.13, 4.71, 5.27, 6.05, 6.84, 7.61, 8.52, 9.33, 10.4,
                11.7, 13.1]
        extra = sorted(self.ident.uniform(2.6, 19.0, max(0, int(self.p["partials"]) - len(base))))
        self.ratios = np.array(base + list(extra))
        r = self.ratios
        amp = r ** -0.85 * self.ident.uniform(0.55, 1.2, len(r))
        amp[0] = 1.0
        amp[2] = 0.62
        amp[1] = 0.3
        self.amps = amp
        self.beat = self.ident.uniform(0.0012, 0.0045, len(r)) * self.ident.choice([-1, 1], len(r))
        self.depth = self.ident.uniform(0.25, 0.7, len(r))

    def render(self, note, rng):
        sr = self.sr
        p = self.p
        f0 = hz(note.pitch)
        vel = min(1.0, note.mvel / 127.0)
        stroke = note.kw.get("stroke", "struck")
        decay = float(note.kw.get("decay", p["decay"]))
        bowed = stroke == "bowed"
        hold = max(0.2, note.t1 - note.t0) if bowed else 0.0
        length = hold + decay * 1.15
        n = int(length * sr)
        t = np.arange(n) / sr
        outL = np.zeros(n)
        outR = np.zeros(n)
        bright = p["bright"] * (0.6 + 0.8 * vel)
        glide = 1.0 + p["glide"] * vel * np.exp(-t / 0.45)
        for k, (r, a) in enumerate(zip(self.ratios, self.amps)):
            f = f0 * r
            if f > sr * 0.45:
                continue
            t60 = decay * r ** -0.72 * (1.0 if r < 1.2 else 0.85)
            tau = t60 / 6.91
            a_k = a * (vel ** (0.4 + 0.5 * math.log2(r + 1) * bright))
            a_k *= 1.0 + 0.15 * rng.normal()
            # how many samples until the partial is 70 dB down
            if bowed:
                m = n
            else:
                m = min(n, int((tau * 8.0 + 0.05) * sr))
            tt = t[:m]
            if bowed:
                onset = hold * (0.15 + 0.55 * min(1.0, (r - 1) / 8.0)) * (0.8 + 0.4 * rng.random())
                att = np.clip((tt - onset * 0.2) / max(0.05, onset), 0, 1)
                att = att * att * (3 - 2 * att)
                wob = 1.0 + 0.28 * smooth_noise(rng, m, 1.3)
                after = np.where(tt > hold, np.exp(-(tt - hold) / tau), 1.0)
                bowshape = 0.25 if r < 1.2 else (1.0 if r < 9 else 0.6)
                e = att * wob * after * bowshape
            else:
                e = np.exp(-tt / tau)
                if r > 3.5 and p["bloom"] > 0:
                    tb = 0.18 + 0.7 * rng.random() * (r / 19.0) ** 0.5
                    e = e * ((1 - p["bloom"]) + p["bloom"] * (1 - np.exp(-tt / tb)) * 1.6)
            ph = rng.uniform(0, 2 * math.pi)
            gl = glide[:m] if r < 4 else 1.0
            phase = 2 * math.pi * f * np.cumsum(gl) / sr if r < 4 else 2 * math.pi * f * tt
            car = np.sin(phase + ph) * e * a_k
            bf = f * abs(self.beat[k])
            d = self.depth[k]
            phl = rng.uniform(0, 2 * math.pi)
            outL[:m] += car * (1 - d + d * np.cos(2 * math.pi * bf * tt + phl))
            outR[:m] += car * (1 - d + d * np.cos(2 * math.pi * bf * tt + phl + 1.3))
        # mallet: soft low-passed thump (struck) / bow hiss (bowed)
        if bowed:
            hiss = shaped_noise(rng, n, lambda f: bandpass(2500, 0.7)(f) * 0.6) * 0.012
            hiss *= np.clip(t / max(0.1, hold * 0.4), 0, 1) * np.where(t > hold, np.exp(-(t - hold) / 0.3), 1.0)
            outL += hiss
            outR += hiss[::-1] * 0 + np.roll(hiss, 37)
        else:
            m = int(0.08 * sr)
            th = shaped_noise(rng, m, lowpass(220 + 500 * vel, 2)) * np.exp(-np.arange(m) / (0.018 * sr)) * 0.6 * vel
            outL[:m] += th
            outR[:m] += th
        out = np.stack([outL, outR], 1) * p["level"] * 0.18
        if note.kw.get("damp"):
            k = int(max(0.05, note.t1 - note.t0) * sr)
            fade = np.ones(n)
            fade[k:] = np.exp(-np.arange(n - k) / (0.12 * sr))
            out *= fade[:, None]
        return int(round(note.t0 * sr)), out


class Bell(Synth):
    defaults = {"decay": 6.0, "identity": 1, "level": 0.5}
    PARTIALS = [(0.5, 0.55, 1.0), (1.0, 0.8, 0.75), (1.183, 0.55, 0.6), (1.506, 0.3, 0.45), (2.0, 0.85, 0.42),
                (2.51, 0.32, 0.3), (2.66, 0.3, 0.27), (3.01, 0.3, 0.24), (4.07, 0.22, 0.17), (5.03, 0.14, 0.12),
                (5.98, 0.1, 0.1), (7.12, 0.07, 0.08), (8.3, 0.05, 0.06)]

    def render(self, note, rng):
        sr = self.sr
        f0 = hz(note.pitch)
        vel = min(1.0, note.mvel / 127.0)
        decay = float(note.kw.get("decay", self.p["decay"]))
        n = int(decay * 1.3 * sr)
        t = np.arange(n) / sr
        L = np.zeros(n)
        R = np.zeros(n)
        for r, a, dk in self.PARTIALS:
            f = f0 * r * (1 + 0.0015 * rng.normal())
            if f > sr * 0.45:
                continue
            tau = decay * dk / 6.91
            m = min(n, int(tau * 8 * sr) + 1)
            tt = t[:m]
            aa = a * vel ** (0.3 + 0.35 * math.log2(r + 1))
            car = np.sin(2 * math.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt / tau) * aa
            bf = 0.4 + 1.6 * rng.random()
            L[:m] += car * (0.75 + 0.25 * np.cos(2 * math.pi * bf * tt))
            R[:m] += car * (0.75 + 0.25 * np.cos(2 * math.pi * bf * tt + 1.7))
        m = int(0.012 * sr)
        click = shaped_noise(rng, m, highpass(2500, 2)) * np.exp(-np.arange(m) / (0.002 * sr)) * 0.25 * vel
        L[:m] += click
        R[:m] += click
        return int(round(note.t0 * sr)), np.stack([L, R], 1) * self.p["level"] * 0.2


class Hurdy(Synth):
    defaults = {"body": 1.0, "rosin": 0.035, "flutter": 1.0, "buzz": 0.5, "level": 0.5, "bright": 1.0}
    BODY = [(280, 160, 1.0), (520, 220, 0.7), (1100, 400, 0.45), (2600, 900, 0.55), (4200, 1500, 0.2)]

    def _table(self, f0, kind):
        nmax = int(min(9000.0, self.sr * 0.42) / f0)
        h = np.arange(1, nmax + 1)
        body = resonances(h * f0 * (1.0 / self.p["body"]), self.BODY, floor=0.12)
        # the wooden body passes little below its air resonance: the drone is nasal, not boomy
        hp = 0.18 + 0.82 * highpass(190.0, 2)(h * f0)
        if kind == "buzz":
            amps = h ** -0.3 * body * (1 + 0.6 * (h % 2 == 0)) * hp
        elif kind == "melody":
            amps = h ** -0.75 * body * self.p["bright"] * hp
        else:
            amps = h ** -0.72 * body * hp
        amps *= 1.0 / (1.0 + (h * f0 / 7000.0) ** 4)
        ph = self.ident.uniform(0, 2 * math.pi, nmax)
        tab = harmonic_table(amps, ph)
        return tab / (np.sqrt(np.mean(tab ** 2)) + 1e-9)

    def render(self, note, rng):
        sr = self.sr
        p = self.p
        kind = note.kw.get("stroke", "drone")
        f0 = hz(note.pitch)
        vel = min(1.0, note.mvel / 127.0)
        dur = max(0.03, note.t1 - note.t0)
        if kind == "buzz":
            att, rel = 0.004, 0.045
        elif kind == "melody":
            att, rel = 0.025, 0.12
        else:
            att, rel = 0.09, 0.3
        n = int((dur + rel * 2.5) * sr)
        sus = int(dur * sr)
        fl = p["flutter"]
        fm = 1.0 + fl * (0.0011 * smooth_noise(rng, n, 4.0) + 0.0006 * smooth_noise(rng, n, 11.0))
        phase = np.cumsum(f0 * fm / sr) + rng.random()
        tab = self._table(f0, kind)
        x = wt_read(tab, phase)
        am = 1.0 + fl * (0.045 * smooth_noise(rng, n, 6.0) + 0.02 * smooth_noise(rng, n, 17.0))
        env = env_adsr(n, sr, att, rel, sus, 2.0)
        if kind == "buzz":
            # the dog rattles: a fast irregular gate at roughly f0/2 on top of the bright string
            chatter = 0.55 + 0.45 * np.sign(np.sin(2 * math.pi * (f0 * 0.5) * np.arange(n) / sr + 0.4 * smooth_noise(rng, n, 30)))
            x = x * chatter
            dec = np.exp(-np.clip(np.arange(n) - int(0.02 * sr), 0, None) / (max(0.03, dur * 0.7) * sr))
            env = env * dec
        noise = shaped_noise(rng, n, lambda f: resonances(f, self.BODY, 0.05) * highpass(300)(f)) * 0.35
        y = (x + noise * p["rosin"] / 0.035 * 0.35) * am * env
        if kind == "melody":
            m = int(0.008 * sr)
            y[:m] += shaped_noise(rng, m, bandpass(1800, 1.5)) * np.exp(-np.arange(m) / (0.0015 * sr)) * 0.8
        lvl = p["level"] * 0.12 * (0.55 + 0.45 * vel) * (p["buzz"] * 1.6 if kind == "buzz" else 1.0)
        y *= lvl
        d = int(0.00035 * sr)
        R = np.concatenate([np.zeros(d), y[:-d]]) if d else y
        pan = float(note.kw.get("pan", 0.0))
        gl, gr = pan_gains(pan)
        return int(round(note.t0 * sr)), np.stack([y * gl * 1.41, R * gr * 1.41], 1)


class JawHarp(Synth):
    defaults = {"fundamental": 50, "q": 9.0, "decay": 0.9, "level": 0.5, "kmin": 2.0, "kmax": 14.0}

    def setup(self):
        f0 = hz(self.p["fundamental"])
        self.f0 = f0
        nmax = int(min(8000.0, self.sr * 0.42) / f0)
        h = np.arange(1, nmax + 1)
        src = h ** -0.55
        ph = self.ident.uniform(0, 2 * math.pi, nmax)
        self.ks = np.arange(self.p["kmin"], self.p["kmax"] + 1e-9, 0.25)
        tabs = []
        for k in self.ks:
            fc = k * f0
            bw = fc / self.p["q"]
            shape = resonances(h * f0, [(fc, bw, 1.0), (fc * 2.4, bw * 3, 0.12)], floor=0.05)
            shape[0] *= 0.6
            tab = harmonic_table(src * shape, ph)
            tabs.append(tab)
        tabs = np.array(tabs)
        self.tabs = tabs / (np.sqrt(np.mean(tabs ** 2)) + 1e-9)
        self.prev_k = None

    def render(self, note, rng):
        sr = self.sr
        f = hz(note.pitch)
        k = float(note.kw.get("k", np.clip(round(f / self.f0), self.p["kmin"], self.p["kmax"])))
        k_from = float(note.kw.get("k_from", self.prev_k if self.prev_k is not None else max(self.p["kmin"], k - 2)))
        self.prev_k = k
        vel = min(1.0, note.mvel / 127.0)
        dur = max(0.05, note.t1 - note.t0)
        dec = float(note.kw.get("decay", np.clip(dur * 2.2, 0.25, self.p["decay"] * 2)))
        n = int((dec * 1.6 + 0.05) * sr)
        t = np.arange(n) / sr
        glide = float(note.kw.get("glide", 0.06))
        x = np.clip(t / glide, 0, 1)
        kk = k_from + (k - k_from) * (1 - (1 - x) ** 2) - 0.15 * np.clip(t / dec, 0, 1)
        pos = (kk - self.p["kmin"]) / 0.25
        phase = np.cumsum(self.f0 * (1 + 0.0008 * smooth_noise(rng, n, 5)) / sr) + rng.random()
        y = wt_read(self.tabs, phase, pos)
        env = np.exp(-t / (dec / 6.91 * 2.2)) * np.clip(t / 0.0015, 0, 1)
        y = y * env
        m = int(0.004 * sr)
        y[:m] += shaped_noise(rng, m, highpass(1200)) * np.exp(-np.arange(m) / (0.0008 * sr)) * 0.6
        y *= self.p["level"] * 0.12 * (0.45 + 0.55 * vel)
        return int(round(note.t0 * sr)), np.stack([y, np.roll(y, 23)], 1)


VOWELS = {  # male formants: (F, bandwidth, amplitude)
    "a": [(700, 130, 1.0), (1220, 140, 0.5), (2600, 200, 0.22), (3300, 250, 0.08)],
    "o": [(450, 90, 1.0), (800, 100, 0.4), (2830, 160, 0.08), (3400, 250, 0.04)],
    "u": [(325, 80, 1.0), (700, 100, 0.22), (2530, 160, 0.04), (3300, 250, 0.02)],
    "e": [(400, 80, 1.0), (1700, 120, 0.38), (2600, 160, 0.26), (3400, 250, 0.08)],
    "i": [(270, 70, 1.0), (2290, 120, 0.22), (3010, 160, 0.24), (3600, 250, 0.08)],
    "m": [(250, 70, 1.0), (1100, 300, 0.035), (2500, 300, 0.012)],
}


class Chant(Synth):
    defaults = {"voices": 3, "detune_cents": 7.0, "breath": 0.04, "vibrato": (5.2, 14.0), "overtone_db": 20.0,
                "far": False, "level": 0.5, "attack": 0.35, "release": 0.6, "tilt": 1.0}

    def _table(self, f0, vowel, overtone, ph):
        nmax = int(min(5500.0, self.sr * 0.42) / f0)
        h = np.arange(1, nmax + 1)
        fr = h * f0
        env = resonances(fr, VOWELS[vowel], floor=0.004)
        if overtone:
            g = 10 ** (self.p["overtone_db"] / 20.0)
            env = env * (1.0 / (1.0 + ((fr - 400.0) / 600.0) ** 2) * 0.6 + 0.4)
            env += g * 0.08 / np.sqrt(1.0 + ((fr - overtone * f0) / 18.0) ** 2)
        amps = h ** -self.p["tilt"] * env
        if self.p["far"]:
            amps *= 1.0 / (1.0 + (fr / 2200.0) ** 4)
        tab = harmonic_table(amps, ph[:nmax])
        return tab

    def render(self, note, rng):
        sr = self.sr
        p = self.p
        f0 = hz(note.pitch)
        vel = min(1.0, note.mvel / 127.0)
        dur = max(0.2, note.t1 - note.t0)
        vowels = note.kw.get("vowels") or [note.kw.get("vowel", "o")]
        ots = note.kw.get("overtones") or [note.kw.get("overtone")]
        states = max(len(vowels), len(ots))
        vowels = [vowels[min(i, len(vowels) - 1)] for i in range(states)]
        ots = [ots[min(i, len(ots) - 1)] for i in range(states)]
        rel = p["release"]
        n = int((dur + rel * 1.5) * sr)
        t = np.arange(n) / sr
        voices = int(note.kw.get("voices", p["voices"]))
        L = np.zeros(n)
        R = np.zeros(n)
        nmax = int(min(5500.0, sr * 0.42) / f0) + 1
        for v in range(voices):
            ph = self.ident.uniform(0, 2 * math.pi, nmax + 4)
            tabs = np.array([self._table(f0, vw, ot, ph) for vw, ot in zip(vowels, ots)])
            tabs /= np.sqrt(np.mean(tabs ** 2)) + 1e-9
            # state position across the note, with glides between states
            if states > 1:
                seg = dur / states
                x = np.clip(t / seg - 0.5, 0, states - 1)
                xi = np.floor(x)
                xf = x - xi
                xf = np.clip((xf - 0.65) / 0.35, 0, 1)
                xf = xf * xf * (3 - 2 * xf)
                pos = xi + xf
            else:
                pos = None
            det = (v - (voices - 1) / 2.0) * p["detune_cents"] * (1 + 0.3 * rng.normal())
            vr, vdep = p["vibrato"]
            vib = np.sin(2 * math.pi * vr * (1 + 0.06 * rng.normal()) * t + rng.uniform(0, 6.28))
            vib *= np.clip((t - 0.5) / 0.8, 0, 1) * vdep
            cents = det + vib + 6.0 * smooth_noise(rng, n, 3.0)
            ff = f0 * 2 ** (cents / 1200.0)
            phase = np.cumsum(ff / sr) + rng.random()
            y = wt_read(tabs, phase, pos)
            off = abs(rng.normal(0, 0.03))
            att = np.clip((t - off) / p["attack"], 0, 1)
            att = att * att * (3 - 2 * att)
            relc = np.clip((t - dur) / rel, 0, 1)
            am = 1.0 + 0.05 * smooth_noise(rng, n, 2.5)
            e = att * (1 - relc) ** 2 * am
            y = y * e
            pan = (v - (voices - 1) / 2.0) / max(1, voices - 1) * 0.6 if voices > 1 else 0.0
            gl, gr = pan_gains(pan)
            L += y * gl
            R += y * gr
        br = shaped_noise(rng, n, lambda f: resonances(f, VOWELS[vowels[0]], 0.01) * highpass(200)(f))
        br *= np.clip(t / p["attack"], 0, 1) * (1 - np.clip((t - dur) / rel, 0, 1)) * p["breath"] * 1.5
        L += br
        R += np.roll(br, 61)
        g = p["level"] * 0.1 * (0.5 + 0.5 * vel) / math.sqrt(voices)
        return int(round(note.t0 * sr)), np.stack([L, R], 1) * g


class FrameDrum(Synth):
    defaults = {"size": 1.0, "skin": 1.0, "ring": 1.0, "level": 0.5}
    MODES = [1.0, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50, 3.60, 4.06]
    STROKES = {  # mode amps, decay scale, noise level, noise band (lo, hi), noise decay s
        "dum": ([1.0, 0.22, 0.12, 0.28, 0.06, 0.08, 0.04, 0.05, 0.04, 0.02], 1.0, 0.35, (120, 1800), 0.03),
        "doum": ([1.0, 0.15, 0.08, 0.2, 0.04, 0.05, 0.02, 0.03, 0.02, 0.01], 1.3, 0.25, (80, 1000), 0.04),
        "tek": ([0.04, 0.4, 0.6, 0.35, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2], 0.35, 0.8, (900, 7000), 0.014),
        "slap": ([0.4, 0.5, 0.45, 0.3, 0.3, 0.25, 0.2, 0.15, 0.12, 0.1], 0.3, 1.3, (400, 4000), 0.035),
        "mute": ([1.0, 0.2, 0.1, 0.2, 0.05, 0.05, 0.02, 0.02, 0.02, 0.01], 0.3, 0.4, (150, 1500), 0.02),
    }

    def render(self, note, rng):
        sr = self.sr
        p = self.p
        stroke = note.kw.get("stroke", "dum")
        amps, dsc, nl, band, ndec = self.STROKES.get(stroke, self.STROKES["dum"])
        vel = min(1.0, note.mvel / 127.0)
        f0 = hz(note.pitch) * p["size"] * (1 + 0.006 * rng.normal())
        base_dec = 0.55 * p["ring"] * dsc * (110.0 / max(40.0, f0)) ** 0.35
        n = int(min(2.5, base_dec * 2.2 + 0.1) * sr)
        t = np.arange(n) / sr
        y = np.zeros(n)
        g = 0.06 * vel ** 2
        glide = 1.0 + g * np.exp(-t / 0.035)
        cph = np.cumsum(glide) / sr
        for k, (r, a) in enumerate(zip(self.MODES, amps)):
            f = f0 * r
            if f > sr * 0.45:
                continue
            tau = base_dec / 6.91 * (r ** -0.9 if k else 1.0) * 2.0
            aa = a * (1 + 0.18 * rng.normal()) * vel ** (0.2 + 0.25 * k / 3.0)
            y += np.sin(2 * math.pi * f * cph + rng.uniform(0, 6.28)) * np.exp(-t / tau) * aa
        m = int(0.12 * sr)
        lo, hi = band
        nz = shaped_noise(rng, m, lambda f: highpass(lo)(f) * lowpass(hi * (0.6 + 0.6 * vel))(f))
        nz *= np.exp(-np.arange(m) / (ndec * sr)) * nl * p["skin"] * (0.4 + 0.6 * vel)
        y[:m] += nz
        y *= np.clip(t / 0.0007, 0, 1)
        y *= p["level"] * 0.32 * vel ** 0.8
        return int(round(note.t0 * sr)), np.stack([y, np.roll(y, 11)], 1)


class Claps(Synth):
    defaults = {"hands": 5, "spread_ms": 9.0, "identity": 1, "level": 0.5, "width": 0.7}

    def setup(self):
        k = int(self.p["hands"])
        self.fc = self.ident.uniform(850, 2100, k)
        self.q = self.ident.uniform(0.9, 1.8, k)
        self.bias = self.ident.normal(0, self.p["spread_ms"] / 1000.0 * 0.6, k)
        self.pan = np.linspace(-self.p["width"], self.p["width"], k) if k > 1 else np.zeros(1)
        self.ident.shuffle(self.pan)
        self.lvl = self.ident.uniform(0.6, 1.0, k)
        self.stamp_f = self.ident.uniform(48, 72, k)

    def render(self, note, rng):
        sr = self.sr
        stroke = note.kw.get("stroke", "clap")
        vel = min(1.0, note.mvel / 127.0)
        k = int(note.kw.get("hands", self.p["hands"]))
        k = min(k, len(self.fc))
        n = int(0.5 * sr)
        pre = int(0.03 * sr)
        L = np.zeros(n + pre)
        R = np.zeros(n + pre)
        for j in range(k):
            off = self.bias[j] + rng.normal(0, self.p["spread_ms"] / 1000.0 * 0.35)
            s0 = pre + int(off * sr)
            if stroke == "stamp":
                m = int(0.25 * sr)
                tt = np.arange(m) / sr
                f = self.stamp_f[j] * (1 + 0.8 * np.exp(-tt / 0.02))
                y = np.sin(2 * math.pi * np.cumsum(f) / sr) * np.exp(-tt / 0.07)
                y += shaped_noise(rng, m, lowpass(700, 2)) * np.exp(-tt / 0.02) * 0.6
                y *= 0.9
            elif stroke == "slap":
                m = int(0.08 * sr)
                tt = np.arange(m) / sr
                y = shaped_noise(rng, m, bandpass(700 + 300 * rng.random(), 1.2)) * np.exp(-tt / 0.018) * 0.9
            else:
                m = int(0.09 * sr)
                tt = np.arange(m) / sr
                y = np.zeros(m)
                bursts = 1 + int(rng.integers(1, 3))
                tpos = 0.0
                for b in range(bursts + 1):
                    main = b == bursts
                    sl = int(tpos * sr)
                    dec = 0.011 if main else 0.0025
                    seg = np.exp(-np.clip(tt - tpos, 0, None) / dec) * (tt >= tpos)
                    y += seg * (1.0 if main else 0.45)
                    tpos += rng.uniform(0.003, 0.008)
                    del sl
                y *= shaped_noise(rng, m, bandpass(self.fc[j], self.q[j]))
            y *= self.lvl[j] * (0.5 + 0.5 * vel) * (1 + 0.15 * rng.normal())
            gl, gr = pan_gains(float(self.pan[j]))
            _place(L, s0, y * gl)
            _place(R, s0, y * gr)
        g = self.p["level"] * 0.22 / math.sqrt(k)
        return int(round(note.t0 * sr)) - pre, np.stack([L, R], 1) * g


SYNTHS = {"gong": Gong, "bell": Bell, "hurdy": Hurdy, "jawharp": JawHarp, "chant": Chant, "framedrum": FrameDrum,
          "claps": Claps}


def render_track(synth, params, notes, n_samples, track="", seed=0, sr=SR, gain_curve=None):
    """Render compiled notes (score.CNote) with a synth to a (n_samples, 2) float32 stem.
    gain_curve: optional (times_s, gains) for track expression (CC11 automation)."""
    cls = SYNTHS[synth]
    s = cls(params, track, sr)
    out = np.zeros((n_samples, 2))
    for i, nn in enumerate(notes):
        rng = _rng("note", int(params.get("identity", 1)), track, i, int(seed))
        start, buf = s.render(nn, rng)
        _place(out, start, buf)
    if gain_curve is not None:
        ts, gs = gain_curve
        g = np.interp(np.arange(n_samples) / sr, ts, gs)
        out *= g[:, None]
    return out.astype(F32)


# --------------------------------------------------------------------------------------------- demo CLI
def _demo(outdir):
    import os
    import wave
    from types import SimpleNamespace as NS
    os.makedirs(outdir, exist_ok=True)

    def N(t0, t1, pitch, vel=100, **kw):
        return NS(t0=t0, t1=t1, pitch=pitch, mvel=vel, kw=kw)
    demos = {
        "gong_struck": ("gong", {}, [N(0.1, 0.2, 38, 110), N(5, 5.1, 45, 70)], 14),
        "gong_bowed": ("gong", {}, [N(0.1, 4.0, 38, 90, stroke="bowed")], 14),
        "bell": ("bell", {}, [N(0.1, 0.2, 74, 110), N(2.0, 2.1, 74, 80)], 8),
        "hurdy": ("hurdy", {}, [N(0.0, 6, 38), N(0.0, 6, 45, 80)] +
                  [N(0.5 + 0.65 * i, 0.5 + 0.65 * i + 0.15, 50, 100, stroke="buzz") for i in range(8)] +
                  [N(1 + 0.4 * i, 1.35 + 0.4 * i, 62 + [0, 2, 4, 5, 7, 7, 5, 4][i], 90, stroke="melody") for i in range(8)], 7),
        "jawharp": ("jawharp", {"fundamental": 50}, [N(0.2 + 0.33 * i, 0.4 + 0.33 * i, 50 + [24, 28, 31, 36, 31, 28, 24, 19][i], 100) for i in range(8)], 4),
        "chant": ("chant", {}, [N(0.2, 7.0, 38, 90, vowels=["u", "o", "a", "o"], overtones=[None, 8, 10, 9])], 9),
        "hum": ("chant", {"far": True, "voices": 4}, [N(0.2, 5.0, 50, 70, vowel="m")], 6.5),
        "framedrum": ("framedrum", {}, [N(0.2 + 0.25 * i, 0.3 + 0.25 * i, 38, [110, 50, 70, 90][i % 4],
                                          stroke=["dum", "tek", "tek", "slap"][i % 4]) for i in range(12)], 4),
        "claps": ("claps", {}, [N(0.2 + 0.5 * i, 0.3 + 0.5 * i, 39, 100, stroke=["clap", "stamp"][i % 2]) for i in range(8)], 5),
    }
    res = {}
    for name, (syn, prm, notes, length) in demos.items():
        y = render_track(syn, prm, notes, int(length * SR), track=name)
        pk = float(np.max(np.abs(y)))
        rms = float(np.sqrt(np.mean(y ** 2)))
        pcm = (np.clip(y / max(pk, 1e-9) * 0.7, -1, 1) * 32767).astype("<i2")
        with wave.open(os.path.join(outdir, name + ".wav"), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        res[name] = {"peak_db": round(20 * math.log10(pk + 1e-12), 1), "rms_db": round(20 * math.log10(rms + 1e-12), 1)}
    return res


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["demo"], help="demo: render one example of every instrument")
    ap.add_argument("outdir", nargs="?", default="tests/output/music/synth_demo")
    a = ap.parse_args()
    if a.cmd == "demo":
        print(json.dumps(_demo(a.outdir), indent=1))
    else:
        ap.print_help()
