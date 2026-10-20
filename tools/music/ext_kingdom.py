#!/usr/bin/env python3
"""ext_kingdom.py: writing helpers for the kingdom pieces, and a zoomed check view. Additive: it only imports the
shared toolkit (score.py, analyze.py) and never changes it.

Writing helpers
  mel(track, at, "D4:.5 E4:.5 F#4:.5 G4:1.5:m A4:2", vel=80)   a melody as text (see `mel` for the token syntax)
  chord("Am7", octave=3) / bass_of("G/B", octave=2)             chord symbols to MIDI pitches
  tones("D", octave=4, span=2)                                  ascending chord tones over `span` octaves
  dulcimer_bar(track, beat, "D", "roll", vel=60)                hammered-dulcimer figures on a chord
  bass_bar(track, beat, "D", next_sym="G", style="march")       pizzicato / arco bass figures with approach notes
  coups(track, beat, beats, pitch, vel)                         hurdy-gurdy trompette coups (rhythm engine)

Check CLI (you cannot listen: look closer)
  python3 tools/music/ext_kingdom.py zoom PIECE.py T0 T1 OUT.png      piano roll of a time window, with bar numbers
  python3 tools/music/ext_kingdom.py spec FILE.ogg T0 T1 OUT.png      spectrogram of a time window (linear, 0-6 kHz)
  python3 tools/music/ext_kingdom.py bands FILE.ogg PIECE.py         band shares and level per section
  python3 tools/music/ext_kingdom.py sidecar FILE.ogg                 write the Godot .import sidecar (the repo
                                                                      tracks them; uid derived from the path)
"""
from __future__ import annotations

import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from score import _contour, n, note_name  # noqa: E402

ORN = {"m": "mordent", "lm": "lmordent", "gu": "grace_up", "gd": "grace_down", "t": "turn", "tr": "trill",
       "s": "slide", "sd": "slide_down", "ro": "roll", "fl": "flam"}
ART = {"_": "tenuto", ".": "staccato", "^": "marcato", "~": "slide", "o": "ring", "n": "normal", "l": "legato"}


def _dur(s: str) -> float:
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def parse(spec: str):
    """Tokens 'PITCH:DUR[:FLAGS]' -> [(pitch|None, dur, orn, art, vel_mult)]. '|' is ignored."""
    out = []
    for tok in spec.split():
        if tok == "|":
            continue
        parts = tok.split(":")
        p = None if parts[0] in ("r", "-") else n(parts[0])
        d = _dur(parts[1])
        orn, art, vm = None, None, 1.0
        if len(parts) > 2:
            fl = parts[2]
            for code in sorted(ORN, key=len, reverse=True):
                if code in fl and orn is None and not (code == "m" and "lm" in fl):
                    orn = ORN[code]
                    fl = fl.replace(code, "", 1)
            for ch in fl:
                if ch == "!":
                    vm *= 1.15
                elif ch == "?":
                    vm *= 0.8
                elif ch in ART:
                    art = ART[ch]
        out.append((p, d, orn, art, vm))
    return out


def mel(track, at, spec, vel=80, art="legato", dyn=None, tr=0, **kw) -> float:
    """Play a melody written as text and return the end beat.

    Tokens are 'PITCH:DUR[:FLAGS]', separated by spaces; '|' bar lines are ignored (they are for the reader).
      PITCH  a note name (D4, F#3, Bb4) or r / - for a rest
      DUR    beats (.5, 1.5, 1/3)
      FLAGS  an ornament code: m mordent, lm lower mordent, gu / gd grace from above / below, t turn, tr trill,
             s / sd slide up / down into the note, ro roll, fl flam; and marks: ! accent, ? soft, _ tenuto,
             . staccato, ^ marcato, ~ bend from the previous note (mono lines), o let ring, n normal, l legato.
    dyn shapes the phrase (see score.Track.play); tr transposes in semitones; extra keywords go to every note."""
    toks = parse(spec)
    sounding = [t for t in toks if t[0] is not None]
    contour = _contour(dyn, len(sounding))
    b, i = float(at), 0
    for (p, d, orn, a, vm) in toks:
        if p is not None:
            track.note(b, p + tr, d, vel * vm * contour[i], a or art, orn, **kw)
            i += 1
        b += d
    return b


def mel_len(spec: str) -> float:
    return sum(t[1] for t in parse(spec))


# --------------------------------------------------------------------------------------------- chords
QUAL = {"": (0, 4, 7), "m": (0, 3, 7), "5": (0, 7), "sus2": (0, 2, 7), "sus4": (0, 5, 7), "7": (0, 4, 7, 10),
        "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
        "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9), "7sus4": (0, 5, 7, 10), "dim": (0, 3, 6), "m7b5": (0, 3, 6, 10),
        "aug": (0, 4, 8)}


def _split(sym: str):
    bass = None
    if "/" in sym:
        sym, bass = sym.split("/")
    i = 1
    while i < len(sym) and sym[i] in "#b":
        i += 1
    return sym[:i], sym[i:], bass


def root_pc(sym: str) -> int:
    r, _, _ = _split(sym)
    return n(f"{r}0") - 12


def chord(sym: str, octave: int = 3, inversion: int = 0) -> list[int]:
    """Close-position chord on the root in `octave` (C-based octave numbers): chord("Am7", 3) = A3 C4 E4 G4."""
    r, q, _ = _split(sym)
    base = n(f"{r}{octave}")
    ps = [base + iv for iv in QUAL[q]]
    for _ in range(inversion):
        ps = ps[1:] + [ps[0] + 12]
    return ps


def bass_of(sym: str, octave: int = 2) -> int:
    """The bass note of a symbol (the slash note if any) in `octave`."""
    r, _, b = _split(sym)
    return n(f"{b or r}{octave}")


def tones(sym: str, octave: int = 4, span: int = 2) -> list[int]:
    """Ascending chord tones from the root in `octave` over `span` octaves (root, 3rd, 5th, 8ve, ...)."""
    base = chord(sym, octave)
    out = []
    for k in range(span + 1):
        out += [p + 12 * k for p in base if (p + 12 * k) not in out]
    return sorted(set(out))[: len(base) * span + 1]


# --------------------------------------------------------------------------------------------- band figures
DUL_FIGS = {   # indices into tones(); step in beats
    "roll": ([0, 2, 3, 1, 2, 3, 4, 2], 0.5),        # rolling broken chord, both hands
    "roll2": ([0, 2, 1, 3, 2, 4, 3, 2], 0.5),
    "pulse": ([0, 3, 2, 3, 0, 3, 2, 3], 0.5),       # oom-pa on the strings
    "climb": ([0, 1, 2, 3, 4, 5, 4, 3], 0.5),
    "fall": ([6, 5, 4, 3, 2, 1, 2, 3], 0.5),
    "wide": ([0, 3, 5, 3], 1.0),                    # open, ringing quarters
    "half": ([0, 4], 2.0),
    "trip": ([0, 2, 3, 2, 3, 4, 3, 4, 5, 4, 3, 2], 1 / 3),
    # 3/4 figures (beats=3.0)
    "lilt": ([0, 2, 3, 2, 1, 2], 0.5),              # rocking broken chord in eighths, root to octave
    "lilt2": ([0, 2, 1, 3, 2, 1], 0.5),
    "open3": ([0, 3, 5], 1.0),                      # one ringing note per beat
    "low3": ([0, 2, 3], 1.0),
}


def dulcimer_bar(track, beat, sym, fig="roll", vel=60, octave=4, beats=4.0, ring=1.8, dyn=None, accent=4,
                 skip=()):
    """One bar (or `beats`) of a hammered-dulcimer figure on chord `sym`. skip: step indices left out."""
    seq, step = DUL_FIGS[fig]
    ts = tones(sym, octave, 3)
    cnt = int(round(beats / step))
    contour = _contour(dyn, cnt)
    for i in range(cnt):
        if i in skip:
            continue
        p = ts[min(seq[i % len(seq)], len(ts) - 1)]
        while p < track.inst.lo:
            p += 12
        while p > track.inst.hi:
            p -= 12
        v = vel * contour[i] * (1.12 if accent and i % accent == 0 else 1.0)
        track.note(beat + i * step, p, step * ring, v)
    return beat + beats


def bass_bar(track, beat, sym, next_sym=None, style="march", vel=80, octave=2, beats=4.0, scale=None):
    """Bass figures. style: march (root, fifth, approach), root (one long note), halves (root, fifth),
    walk (root, 3rd, 5th, approach), pedal (repeated root quarters). The approach note leads stepwise into
    next_sym's bass from below (from the mode `scale` if given, else a semitone/tone below)."""
    r = bass_of(sym, octave)
    if r > n(f"G{octave}"):
        r -= 12
    fifth = r + 7 if r + 7 <= n(f"D{octave + 1}") else r - 5
    tgt = None
    if next_sym:
        tgt = bass_of(next_sym, octave)
        if tgt > n(f"G{octave}"):
            tgt -= 12

    def approach():
        if tgt is None:
            return fifth
        if scale is not None:
            below = max(p for p in scale if p < tgt)
            above = min(p for p in scale if p > tgt)
            c = below if below != r else above
            return c
        return tgt - 2 if tgt - 2 != r else tgt + 2
    if style == "root":
        track.note(beat, r, beats, vel)
    elif style == "halves":
        track.note(beat, r, beats / 2, vel)
        track.note(beat + beats / 2, fifth, beats / 2, vel * 0.85)
    elif style == "march":
        track.note(beat, r, 1.0, vel)
        track.note(beat + 2.0, fifth, 1.0, vel * 0.84)
        if beats >= 4:
            track.note(beat + 3.5, approach(), 0.5, vel * 0.7)
    elif style == "walk":
        third = chord(sym, octave)[1] if chord(sym, octave)[0] == r else r + 4
        while third < r:
            third += 12
        for k, p in enumerate([r, third, fifth, approach()]):
            track.note(beat + k * beats / 4, p, beats / 4, vel * (1.0, 0.8, 0.88, 0.76)[k])
    elif style == "pedal":
        for k in range(int(beats)):
            track.note(beat + k, r, 1.0, vel * (1.0 if k % 2 == 0 else 0.8))
    else:
        raise ValueError(style)
    return beat + beats


def coups(track, beat, beats, pitch="D3", vel=80, at=(1, 3), length=0.3):
    """Hurdy-gurdy trompette coups on the given offsets (beats) within each bar of `beats` length."""
    out = beat
    for off in at:
        if isinstance(off, tuple):
            off, v = off
        else:
            v = 1.0
        track.note(beat + off, pitch, length, vel * v, stroke="buzz")
        out = beat + beats
    return out


# --------------------------------------------------------------------------------------------- checks
def _load(path):
    import render
    piece, _ = render.load_piece(path)
    piece.compile()
    return piece


def zoom(piece_path, t0, t1, png, width=1800, height=760):
    """Piano roll of [t0, t1] s with bar numbers and the section lines."""
    from PIL import Image, ImageDraw
    piece = _load(piece_path)
    tracks = list(piece.tracks.values())
    notes = [(t, c) for t in tracks for c in t.compiled["notes"] if c.t1 >= t0 and c.t0 <= t1]
    ps = [c.pitch for _, c in notes] or [60]
    lo, hi = min(ps) - 2, max(ps) + 2
    left, right, top, bottom = 150, 20, 30, 40
    rh = height - top - bottom
    sx = (width - left - right) / (t1 - t0)
    im = Image.new("RGB", (width, height), (18, 18, 22))
    d = ImageDraw.Draw(im)

    def X(t):
        return left + (t - t0) * sx

    def Y(p):
        return top + rh - (p - lo + 1) / (hi - lo + 1) * rh
    for p in range(lo, hi + 1):
        if p % 12 == 0:
            d.line([(left, Y(p)), (width - right, Y(p))], fill=(50, 50, 58))
            d.text((left - 34, Y(p) - 12), f"C{p // 12 - 1}", fill=(130, 130, 140))
    nb = piece.bar_index(piece.end) + 1
    for i in range(nb + 1):
        t = piece.seconds(piece.bar(i))
        if t0 <= t <= t1:
            d.line([(X(t), top), (X(t), top + rh)], fill=(36, 36, 44))
            d.text((X(t) + 2, top + rh + 4), str(i + 1), fill=(130, 130, 140))
    for s in piece.sections:
        t = piece.seconds(s.start)
        if t0 <= t <= t1:
            d.line([(X(t), 4), (X(t), height - bottom)], fill=(200, 200, 210))
            d.text((X(t) + 3, 6), s.name, fill=(230, 230, 240))
    hgt = max(2, rh / (hi - lo + 1) * 0.8)
    for i, t in enumerate(tracks):
        col = t.inst.color or (200, 200, 200)
        for c in t.compiled["notes"]:
            if c.t1 < t0 or c.t0 > t1:
                continue
            a = 0.35 + 0.65 * min(1.0, c.mvel / 127.0)
            d.rectangle([X(max(c.t0, t0)), Y(c.pitch) - hgt, max(X(c.t0) + 1, X(min(c.t1, t1))), Y(c.pitch)],
                        fill=tuple(int(v * a) for v in col))
        d.rectangle([8, top + 4 + i * 18, 20, top + 16 + i * 18], fill=col)
        d.text((24, top + 3 + i * 18), t.name[:18], fill=(220, 220, 225))
    d.text((left, height - 18), f"{piece.name}  {t0:.1f}-{t1:.1f} s  (bar numbers 1-based)", fill=(200, 200, 205))
    im.save(png)
    return png


def spec(path, t0, t1, png):
    vf = ("showspectrumpic=s=1600x500:legend=1:fscale=lin:scale=log:color=intensity:mode=combined:"
          "start=0:stop=6000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-lavfi", vf, png],
                   check=True)
    return png


def bands(path, piece_path):
    """Band shares (sub <60, low 60-250, lowmid 250-1k, voice 1-3k, presence 3-6k, air >6k) and the
    K-weighted level of each section."""
    import numpy as np
    import analyze
    piece = _load(piece_path)
    x = analyze.decode(path)
    sr = analyze.SR
    edges = [0, 60, 250, 1000, 3000, 6000, 24000]
    names = ["sub", "low", "lowmid", "voice", "pres", "air"]
    rows = []
    secs = [(s.name, piece.seconds(s.start), piece.seconds(s.end)) for s in piece.sections]
    for name, a, b in secs:
        seg = x[int(a * sr):int(b * sr)].mean(1)
        if len(seg) < sr // 4:
            continue
        spec_ = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        tot = spec_.sum() + 1e-20
        sh = [spec_[(f >= edges[i]) & (f < edges[i + 1])].sum() / tot for i in range(6)]
        k = analyze.kweight(x[int(a * sr):int(b * sr)])
        lv = 10 * math.log10((k ** 2).mean() + 1e-20) - 0.691
        rows.append((name, round(a, 1), round(lv, 1), [round(100 * s, 1) for s in sh]))
    print(f"{'section':24s} {'t0':>6s} {'dB':>6s}  " + " ".join(f"{x:>6s}" for x in names))
    for name, a, lv, sh in rows:
        print(f"{name:24s} {a:6.1f} {lv:6.1f}  " + " ".join(f"{s:6.1f}" for s in sh))
    return rows


UID_CHARS = "abcdefghijklmnopqrstuvwxyz012345678"


def sidecar(ogg_path, loop=False):
    """Write <file>.ogg.import as the Godot 4 editor would (importer oggvorbisstr). The uid is derived from the
    res:// path, so it is stable; the editor keeps an existing sidecar's uid on reimport."""
    import hashlib
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    rel = os.path.relpath(os.path.abspath(ogg_path), root).replace(os.sep, "/")
    res = "res://" + rel
    h = hashlib.md5(res.encode()).hexdigest()
    v = int(hashlib.sha256(res.encode()).hexdigest()[:16], 16) & 0x7FFFFFFFFFFFFFFF
    txt = ""
    while True:
        txt = UID_CHARS[v % len(UID_CHARS)] + txt
        v //= len(UID_CHARS)
        if not v:
            break
    base = os.path.basename(rel)
    dest = f"res://.godot/imported/{base}-{h}.oggvorbisstr"
    body = (f'[remap]\n\nimporter="oggvorbisstr"\ntype="AudioStreamOggVorbis"\nuid="uid://{txt}"\npath="{dest}"\n\n'
            f'[deps]\n\nsource_file="{res}"\ndest_files=["{dest}"]\n\n'
            f'[params]\n\nloop={"true" if loop else "false"}\nloop_offset=0\nbpm=0\nbeat_count=0\nbar_beats=4\n')
    with open(ogg_path + ".import", "w") as f:
        f.write(body)
    return ogg_path + ".import"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    z = sub.add_parser("zoom")
    z.add_argument("piece")
    z.add_argument("t0", type=float)
    z.add_argument("t1", type=float)
    z.add_argument("png")
    s = sub.add_parser("spec")
    s.add_argument("file")
    s.add_argument("t0", type=float)
    s.add_argument("t1", type=float)
    s.add_argument("png")
    b = sub.add_parser("bands")
    b.add_argument("file")
    b.add_argument("piece")
    c = sub.add_parser("sidecar")
    c.add_argument("file")
    c.add_argument("--loop", action="store_true")
    a = ap.parse_args()
    if a.cmd == "zoom":
        print(zoom(a.piece, a.t0, a.t1, a.png))
    elif a.cmd == "spec":
        print(spec(a.file, a.t0, a.t1, a.png))
    elif a.cmd == "bands":
        bands(a.file, a.piece)
    elif a.cmd == "sidecar":
        print(sidecar(a.file, a.loop))
    else:
        ap.print_help()
