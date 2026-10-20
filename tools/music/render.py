#!/usr/bin/env python3
"""render.py: render a piece module to stems, mix, master and export Ogg Vorbis (plus PNGs and a report).

  python3 tools/music/render.py tools/music/pieces/style_kingdom.py
  python3 tools/music/render.py PIECE.py --out assets/audio/music/kingdom_1.ogg --length-check
  python3 tools/music/render.py PIECE.py --loop --xfade 3          # menu / score beds
  python3 tools/music/render.py PIECE.py --trim 2.4 --trim-fade 0.3 # opening cues

The piece module defines build() -> score.Piece. Pipeline (all deterministic):
  1. compile the score (humanise, ornaments, tempo map) and write <work>/<name>.mid (the full MIDI);
  2. stems: every soundfont track gets its own stem MIDI rendered by FluidSynth (no internal reverb or chorus,
     float output, release tails kept), every numpy-synth track is rendered by synths.py; each stem is a
     float32 WAV in <work>/stems/;
  3. mix (ffmpeg): per stem trim, optional drive (soft saturation), EQ, gain, width and pan, a send to one
     shared room (an impulse response generated with numpy, convolved with afir), summed to the bus;
  4. glue: the bus is set to the mix preset's level, gently EQ'd (a dip in the unit-voice band) and bus
     compressed (acompressor, about 2:1);
  5. form: tracks get a short end fade; --loop crossfades the music after the loop point into the start
     (equal power, --xfade s); --trim keeps the first N s with a cosine fade (opening cues);
  6. master: ffmpeg loudnorm two-pass (linear) to -16 LUFS integrated with true peak <= -1 dBTP (a lookahead
     limiter runs first only when the peak-to-loudness ratio would force loudnorm out of linear mode), then
     Ogg Vorbis -q:a 6, 48 kHz stereo, bit-exact muxing;
  7. checks: loudness, true peak, duration, band balance, dynamic arc, quiet spans, loop seam; spectrogram
     and piano-roll PNGs in tests/output/music/ (git-ignored); a JSON report on stdout and in <work>.
Exit code 2 when --length-check fails or the master misses its loudness / peak targets.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import analyze  # noqa: E402
import score  # noqa: E402
import synths  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 48000
FS_GAIN = 0.5
OUT_DIR = os.path.join(ROOT, "tests", "output", "music")
DEFAULT_MIX = {
    "reverb": {"decay": 2.0, "predelay_ms": 22, "early": 0.3, "damp": 0.55, "width": 0.9, "hp": 160, "lp": 7500,
               "seed": 11},
    "bus": {"lufs": -20.0, "threshold_db": -21.0, "ratio": 2.0, "attack": 25, "release": 280, "knee": 4},
    "master": {"lufs": -16.0, "tp": -1.0, "dip": (2300, -1.5, 0.8), "lowshelf": (90, 0.0), "highshelf": (10000, -1.0)},
}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def run(cmd, **kw):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd[:6])} ...\n{p.stderr[-2000:]}")
    return p


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_piece(path):
    spec = importlib.util.spec_from_file_location("piece_" + os.path.splitext(os.path.basename(path))[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    piece = mod.build()
    return piece, mod


# ----------------------------------------------------------------------------------------------- audio io
def write_wav(path, x, sr=SR):
    """Float32 stereo WAV with a fixed header (byte-identical for identical audio)."""
    x = np.ascontiguousarray(x, dtype="<f4")
    data = x.tobytes()
    ch = x.shape[1]
    import struct
    hdr = b"RIFF" + struct.pack("<I", 4 + 26 + 8 + len(data)) + b"WAVE"
    hdr += b"fmt " + struct.pack("<IHHIIHH", 18, 3, ch, sr, sr * 4 * ch, 4 * ch, 32) + struct.pack("<H", 0)
    hdr += b"data" + struct.pack("<I", len(data))
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(data)


def read_wav(path):
    return analyze.decode(path)


def fit(x, n):
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros((n - len(x), x.shape[1]), dtype=x.dtype)])


# ----------------------------------------------------------------------------------------------- stems
CACHE = {"on": True}


def _cache_get(work, key, n):
    p = os.path.join(work, "cache", key + ".f32")
    if CACHE["on"] and os.path.exists(p):
        y = np.fromfile(p, dtype="<f4").reshape(-1, 2)
        if len(y) == n:
            return y
    return None


def _cache_put(work, key, y):
    if CACHE["on"]:
        os.makedirs(os.path.join(work, "cache"), exist_ok=True)
        np.ascontiguousarray(y, dtype="<f4").tofile(os.path.join(work, "cache", key + ".f32"))


def render_gm(piece, name, tail_s, n, work):
    mid = os.path.join(work, "stems_midi", f"{name}.mid")
    raw = os.path.join(work, "stems_midi", f"{name}.raw")
    piece.write_midi(mid, tracks=[name], stem=True, tail_s=tail_s + 1.0)
    key = hashlib.sha256(open(mid, "rb").read() + f"|{SF2}|{FS_GAIN}|{SR}|{n}".encode()).hexdigest()[:32]
    hit = _cache_get(work, key, n)
    if hit is not None:
        return hit
    run(["fluidsynth", "-ni", "-q", "-o", "synth.reverb.active=0", "-o", "synth.chorus.active=0",
         "-o", "synth.cpu-cores=1", "-o", "synth.polyphony=512", "-O", "float", "-T", "raw", "-F", raw,
         "-r", str(SR), "-g", str(FS_GAIN), SF2, mid])
    y = np.fromfile(raw, dtype="<f4").reshape(-1, 2)
    os.remove(raw)
    y = fit(y, n)
    _cache_put(work, key, y)
    return y


def synth_gain_curve(piece, tr):
    ev = [(piece.tick_to_sec(t), v) for (t, kind, v) in tr.compiled["ctrl"].get(0, []) if kind == "cc11"]
    if not ev:
        return None
    ts = np.array([e[0] for e in ev] + [1e6])
    gs = np.array([(e[1] / 127.0) ** 2 for e in ev] + [(ev[-1][1] / 127.0) ** 2])
    ref = (tr.inst.expr / 127.0) ** 2
    return ts, gs / max(ref, 1e-6)


def render_synth(piece, name, n, work):
    tr = piece.tracks[name]
    gc = synth_gain_curve(piece, tr)
    src = open(synths.__file__, "rb").read()
    desc = repr((tr.inst.synth, sorted(tr.inst.synth_params.items()), n, piece.seed, name,
                 [(c.t0, c.t1, c.pitch, c.mvel, sorted(c.kw.items())) for c in tr.compiled["notes"]],
                 None if gc is None else (list(gc[0]), list(gc[1]))))
    key = hashlib.sha256(src + desc.encode()).hexdigest()[:32]
    hit = _cache_get(work, key, n)
    if hit is not None:
        return hit
    y = synths.render_track(tr.inst.synth, tr.inst.synth_params, tr.compiled["notes"], n, track=name,
                            seed=piece.seed, gain_curve=gc)
    _cache_put(work, key, y)
    return y


def stem_level(path, inst):
    """Active level of a stem after its mix chain: the mean power of the 0.4 s windows within 20 dB of the
    loudest one (how loud the instrument sounds while it plays), plus its octave-band balance."""
    raw = run_bytes(["ffmpeg", "-v", "error", "-i", path, "-af", stem_chain(inst), "-f", "f32le", "-"])
    y = np.frombuffer(raw, dtype="<f4").astype(np.float64).reshape(-1, 2)
    m = (y ** 2).mean(1)
    w = int(0.4 * SR)
    k = len(m) // w
    if k == 0:
        return {"active_db": -120.0}
    pw = m[:k * w].reshape(k, w).mean(1)
    top = pw.max()
    act = pw[pw > top * 0.01]
    return {"active_db": round(10 * math.log10(act.mean() + 1e-20), 1),
            "share_active": round(len(act) / k, 2)}


def run_bytes(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[-2000:])
    return p.stdout


# ----------------------------------------------------------------------------------------------- room
def make_ir(decay=2.0, predelay_ms=20, early=0.3, damp=0.5, width=1.0, seed=1, sr=SR, **_):
    """Stereo room impulse response: early reflections + a noise tail with per-band decay times (the highs die
    faster, `damp`), a 15 ms diffusion build-up, decorrelated channels (`width`). Energy-normalised, so a send
    of 0.25 returns the room about 12 dB under the dry signal."""
    rng = np.random.default_rng(seed)
    pd = predelay_ms / 1000.0
    n = int((decay * 1.35 + pd + 0.1) * sr)
    t = np.arange(n) / sr
    bands = [(0, 180, 1.15), (180, 500, 1.05), (500, 1200, 1.0), (1200, 2500, 1 - 0.25 * damp),
             (2500, 5000, 1 - 0.45 * damp), (5000, 10000, 1 - 0.62 * damp), (10000, sr / 2 + 1, 1 - 0.75 * damp)]
    N = 1 << int(math.ceil(math.log2(n)))
    f = np.fft.rfftfreq(N, 1.0 / sr)
    tl = np.clip(t - pd, 0, None)
    onset = (t >= pd) * (1 - np.exp(-tl / 0.015))
    ir = np.zeros((n, 2))
    for ch in range(2):
        X = np.fft.rfft(rng.normal(size=N))
        for lo, hi, k in bands:
            m = ((f >= lo) & (f < hi)).astype(float)
            band = np.fft.irfft(X * m, N)[:n]
            ir[:, ch] += band * np.exp(-6.91 * tl / (decay * k)) * onset
    M = (ir[:, 0] + ir[:, 1]) / 2
    S = (ir[:, 0] - ir[:, 1]) / 2
    ir = np.stack([M + width * S, M - width * S], 1)
    late_e = np.sqrt(np.mean(np.sum(ir ** 2, 0)))
    ir /= late_e
    for ch in range(2):
        for i in range(14):
            ti = pd * 0.4 + rng.uniform(0.004, 0.07)
            g = early * rng.uniform(0.3, 1.0) * math.exp(-ti / 0.06) * rng.choice([-1, 1])
            k = int(ti * sr)
            ir[k:k + 3, ch] += g * np.array([0.5, 1.0, 0.5])
    ir /= np.sqrt(np.mean(np.sum(ir ** 2, 0)))
    return ir.astype(np.float32)


# ----------------------------------------------------------------------------------------------- mix
def eq_filters(eq):
    out = []
    for e in eq or []:
        k = e[0]
        if k == "hp":
            out.append(f"highpass=f={e[1]}:poles=2")
        elif k == "lp":
            out.append(f"lowpass=f={e[1]}:poles=2")
        elif k == "peak":
            out.append(f"equalizer=f={e[1]}:t=q:w={e[3] if len(e) > 3 else 1.0}:g={e[2]}")
        elif k == "lowshelf":
            out.append(f"lowshelf=f={e[1]}:g={e[2]}")
        elif k == "highshelf":
            out.append(f"highshelf=f={e[1]}:g={e[2]}")
        else:
            raise ValueError(f"unknown EQ band {e!r}")
    return out


def pan_filter(pan, width):
    a = (max(-1.0, min(1.0, pan)) + 1) * math.pi / 4
    gl, gr = math.cos(a) * math.sqrt(2), math.sin(a) * math.sqrt(2)
    w = max(0.0, width)
    c00, c01 = gl * (0.5 + 0.5 * w), gl * (0.5 - 0.5 * w)
    c10, c11 = gr * (0.5 - 0.5 * w), gr * (0.5 + 0.5 * w)
    return f"pan=stereo|c0={c00:.6f}*c0+{c01:.6f}*c1|c1={c10:.6f}*c0+{c11:.6f}*c1"


def stem_chain(inst):
    ch = ["aformat=sample_fmts=flt:channel_layouts=stereo", f"volume={inst.trim_db:.2f}dB"]
    if inst.drive > 0:
        pre = 10.0 + 14.0 * inst.drive
        # (asoftclip's oversample option loses about 6 dB in ffmpeg 6.1, so it is not used)
        ch += [f"volume={pre:.2f}dB", "asoftclip=type=tanh", f"volume={-pre:.2f}dB"]
    ch += eq_filters(inst.eq)
    ch += [f"volume={inst.gain_db:.2f}dB", pan_filter(inst.pan, inst.width)]
    return ",".join(ch)


def mix_stems(stems, ir_path, out_path, cfg, work):
    """stems: list of (wav_path, Instrument). Writes the dry+wet bus (float WAV)."""
    rv = cfg["reverb"]
    lines = []
    dry, sends = [], []
    for i, (path, inst) in enumerate(stems):
        lines.append(f"[{i}:a]{stem_chain(inst)},asplit=2[d{i}][x{i}]")
        lines.append(f"[x{i}]volume={max(inst.reverb, 0.0):.4f}[s{i}]")
        dry.append(f"[d{i}]")
        sends.append(f"[s{i}]")
    k = len(stems)
    lines.append("".join(dry) + f"amix=inputs={k}:normalize=0:duration=longest[dry]")
    lines.append("".join(sends) + f"amix=inputs={k}:normalize=0:duration=longest,"
                 f"highpass=f={rv.get('hp', 160)}:poles=2,lowpass=f={rv.get('lp', 7500)}:poles=2[snd]")
    # afir: `dry` is the INPUT gain and `wet` the output gain (not a dry/wet mix); gtype=none keeps the
    # energy-normalised IR as generated
    lines.append(f"[snd][{k}:a]afir=dry=1:wet=1:gtype=none:irgain=1:irfmt=input:maxir=12[wet]")
    lines.append("[dry][wet]amix=inputs=2:normalize=0:duration=first[out]")
    script = os.path.join(work, "mix.filter")
    with open(script, "w") as f:
        f.write(";\n".join(lines))
    cmd = ["ffmpeg", "-v", "error", "-y", "-filter_complex_threads", "1"]
    for path, _ in stems:
        cmd += ["-i", path]
    cmd += ["-i", ir_path, "-filter_complex_script", script, "-map", "[out]", "-c:a", "pcm_f32le",
            "-fflags", "+bitexact", "-flags:a", "+bitexact", out_path]
    run(cmd)
    return out_path


def glue(bus_path, out_path, cfg):
    b, m = cfg["bus"], cfg["master"]
    meas = analyze.ebur128(bus_path)
    gain = b["lufs"] - meas["lufs"]
    chain = [f"volume={gain:.3f}dB"]
    if m.get("lowshelf") and m["lowshelf"][1]:
        chain.append(f"lowshelf=f={m['lowshelf'][0]}:g={m['lowshelf'][1]}")
    if m.get("dip"):
        f0, g, q = m["dip"]
        chain.append(f"equalizer=f={f0}:t=q:w={q}:g={g}")
    if m.get("highshelf") and m["highshelf"][1]:
        chain.append(f"highshelf=f={m['highshelf'][0]}:g={m['highshelf'][1]}")
    thr = 10 ** (b["threshold_db"] / 20.0)
    chain.append(f"acompressor=threshold={thr:.6f}:ratio={b['ratio']}:attack={b['attack']}:release={b['release']}"
                 f":knee={b['knee']}:makeup=1:detection=rms:link=average")
    run(["ffmpeg", "-v", "error", "-y", "-i", bus_path, "-af", ",".join(chain), "-c:a", "pcm_f32le",
         "-fflags", "+bitexact", "-flags:a", "+bitexact", out_path])
    return {"bus_lufs_in": round(meas["lufs"], 2), "bus_gain_db": round(gain, 2)}


# ----------------------------------------------------------------------------------------------- form
def shape_form(x, piece, kind, xfade_s, trim_s, trim_fade_s, tail_s):
    info = {"kind": kind}
    if kind == "loop":
        L = int(round(piece.duration_s * SR))
        X = int(round(xfade_s * SR))
        if len(x) < L + X:
            raise RuntimeError(f"loop: need {L + X} samples after the loop point, have {len(x)}; raise tail_s")
        u = (np.arange(X) + 0.5) / X
        fin, fout = np.sin(u * math.pi / 2), np.cos(u * math.pi / 2)
        y = x[:L].copy()
        y[:X] = x[:X] * fin[:, None] + x[L:L + X] * fout[:, None]
        info.update(loop_len_s=round(L / SR, 3), xfade_s=xfade_s)
        return y, info
    if kind == "cue":
        T = int(round(trim_s * SR))
        F = int(round(trim_fade_s * SR))
        y = x[:T].copy()
        u = np.arange(F) / max(1, F - 1)
        y[T - F:] *= (0.5 + 0.5 * np.cos(u * math.pi))[:, None]
        info.update(trim_s=trim_s, trim_fade_s=trim_fade_s)
        return y, info
    T = min(len(x), int(round((piece.duration_s + tail_s) * SR)))
    y = x[:T].copy()
    F = int(min(1.2, tail_s * 0.4) * SR)
    u = np.arange(F) / max(1, F - 1)
    y[T - F:] *= (0.5 + 0.5 * np.cos(u * math.pi))[:, None]
    info.update(end_fade_s=round(F / SR, 2))
    return y, info


# ----------------------------------------------------------------------------------------------- master
def loudnorm_pass1(path, lufs, tp):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        f"loudnorm=I={lufs}:TP={tp}:LRA=50:print_format=json", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True)
    t = p.stderr
    return json.loads(t[t.rfind("{"): t.rfind("}") + 1])


def master(form_path, ogg_path, cfg, work):
    m = cfg["master"]
    target, tp_target = m["lufs"], m["tp"]
    tp_aim = tp_target - 0.6      # headroom for the Vorbis encode
    src = form_path
    meas = loudnorm_pass1(src, target, tp_aim)
    info = {"pass1": {k: meas[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh")}}
    I, TP = float(meas["input_i"]), float(meas["input_tp"])
    if TP - I > (tp_aim - target) - 0.2:
        # peak-to-loudness ratio too high for linear loudnorm: a transparent lookahead limiter first
        ceiling_db = I + (tp_aim - target) - 1.0
        lim = os.path.join(work, "limited.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
             f"alimiter=limit={10 ** (ceiling_db / 20):.6f}:attack=4:release=80:level=disabled:asc=1,"
             f"aresample={SR}", "-c:a", "pcm_f32le", "-fflags", "+bitexact", "-flags:a", "+bitexact", lim])
        src = lim
        meas = loudnorm_pass1(src, target, tp_aim)
        info["limiter_ceiling_db"] = round(ceiling_db, 2)
        info["pass1_limited"] = {k: meas[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh")}
    mwav = os.path.join(work, "master.wav")
    lra = min(50.0, max(7.0, float(meas["input_lra"]) + 1.0))
    af = (f"loudnorm=I={target}:TP={tp_aim}:LRA={lra}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}"
          f":measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}"
          f":linear=true:print_format=json,aresample={SR}")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", src, "-af", af, "-c:a", "pcm_f32le",
                        "-fflags", "+bitexact", "-flags:a", "+bitexact", mwav], stderr=subprocess.PIPE, text=True)
    t = p.stderr
    p2 = json.loads(t[t.rfind("{"): t.rfind("}") + 1])
    info["normalization_type"] = p2.get("normalization_type")
    if p2.get("normalization_type") != "linear":
        # never accept dynamic mode (it pumps): plain gain instead
        g = target - float(meas["input_i"])
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"volume={g:.3f}dB", "-c:a", "pcm_f32le",
             "-fflags", "+bitexact", "-flags:a", "+bitexact", mwav])
        info["normalization_type"] = "gain"
    gain_fix = 0.0
    for attempt in range(3):
        enc_in = mwav
        if gain_fix:
            enc_in = os.path.join(work, "master_fix.wav")
            run(["ffmpeg", "-v", "error", "-y", "-i", mwav, "-af", f"volume={gain_fix:.3f}dB", "-c:a", "pcm_f32le",
                 "-fflags", "+bitexact", "-flags:a", "+bitexact", enc_in])
        run(["ffmpeg", "-v", "error", "-y", "-i", enc_in, "-c:a", "libvorbis", "-q:a", "6", "-ar", str(SR), "-ac", "2",
             "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", ogg_path])
        r = analyze.ebur128(ogg_path)
        over = r["true_peak_db"] - tp_target
        off = r["lufs"] - target
        if over <= 0.0 and abs(off) <= 0.5:
            break
        gain_fix += -max(over + 0.15, 0.0) if over > 0 else -off
    info["post_gain_fix_db"] = round(gain_fix, 2)
    return info


# ----------------------------------------------------------------------------------------------- main
def render(piece_path, out=None, kind=None, xfade=None, trim=None, trim_fade=None, length_check=False,
           length=None, work=None, png_dir=OUT_DIR, pngs=True, jobs=4, levels=True, cache=True):
    t_start = time.time()
    CACHE["on"] = cache
    piece, mod = load_piece(piece_path)
    piece.compile()
    kind = kind or piece.kind
    if trim is not None:
        kind = "cue"
    xfade = xfade if xfade is not None else piece.xfade_s
    trim = trim if trim is not None else piece.trim_s
    trim_fade = trim_fade if trim_fade is not None else piece.trim_fade_s
    name = piece.name
    work = work or os.path.join(OUT_DIR, name)
    os.makedirs(os.path.join(work, "stems"), exist_ok=True)
    os.makedirs(os.path.join(work, "stems_midi"), exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)
    out = out or piece.out or os.path.join(OUT_DIR, f"{name}.ogg")
    if not os.path.isabs(out):
        out = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cfg = json.loads(json.dumps(DEFAULT_MIX))
    for k, v in (piece.mix or {}).items():
        cfg.setdefault(k, {}).update(v)
    tail = piece.tail_s
    if kind == "loop":
        tail = max(tail, xfade + 0.5)
    n = int(math.ceil((piece.duration_s + tail) * SR))
    midi_path = os.path.join(work, f"{name}.mid")
    piece.write_midi(midi_path)
    report = {"piece": piece.summary(), "kind": kind, "out": os.path.relpath(out, ROOT)}
    log(f"[render] {name}: {len(piece.tracks)} tracks, {piece.duration_s:.1f} s + {tail:.1f} s tail")
    # stems
    stems = {}
    gm = [k for k, t in piece.tracks.items() if not t.inst.is_synth]
    sy = [k for k, t in piece.tracks.items() if t.inst.is_synth]
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {k: ex.submit(render_gm, piece, k, tail, n, work) for k in gm}
        for k in sy:
            stems[k] = render_synth(piece, k, n, work)
        for k, f in futs.items():
            stems[k] = f.result()
    stem_list, stem_info, hashes = [], {}, {"midi": sha(midi_path)}
    for k in piece.tracks:
        p = os.path.join(work, "stems", f"{k}.wav")
        write_wav(p, stems[k])
        y = stems[k].astype(np.float64)
        trim_g = 10 ** (piece.tracks[k].inst.trim_db / 20)
        rms = math.sqrt(np.mean(y ** 2)) * trim_g
        stem_info[k] = {"rms_db_trimmed": round(20 * math.log10(rms + 1e-12), 1),
                        "peak_db_trimmed": round(20 * math.log10(np.max(np.abs(y)) * trim_g + 1e-12), 1)}
        if levels:
            stem_info[k].update(stem_level(p, piece.tracks[k].inst))
        hashes["stem:" + k] = sha(p)
        stem_list.append((p, piece.tracks[k].inst))
    report["stems"] = stem_info
    # room, mix, glue
    ir = make_ir(**cfg["reverb"])
    ir_path = os.path.join(work, "room_ir.wav")
    write_wav(ir_path, ir)
    bus = mix_stems(stem_list, ir_path, os.path.join(work, "bus.wav"), cfg, work)
    comp = os.path.join(work, "glued.wav")
    report["glue"] = glue(bus, comp, cfg)
    # form
    x = read_wav(comp)
    y, form = shape_form(x, piece, kind, xfade, trim, trim_fade, tail)
    form_path = os.path.join(work, "form.wav")
    write_wav(form_path, y)
    report["form"] = form
    # master
    report["master"] = master(form_path, out, cfg, work)
    hashes["ogg"] = sha(out)
    report["hashes"] = hashes
    # checks
    meas = analyze.measure(out, loop=(kind == "loop"))
    report["measure"] = meas
    problems = []
    tgt = cfg["master"]
    if abs(meas["lufs"] - tgt["lufs"]) > 1.0 and kind != "cue":
        problems.append(f"integrated {meas['lufs']} LUFS (target {tgt['lufs']})")
    if meas["true_peak_db"] > tgt["tp"] + 0.05:
        problems.append(f"true peak {meas['true_peak_db']} dBTP (max {tgt['tp']})")
    rng = length or piece.length_range
    if length_check and rng:
        if not (rng[0] <= meas["duration_s"] <= rng[1]):
            problems.append(f"duration {meas['duration_s']} s outside {rng}")
    audio = analyze.decode(out)
    spans = []
    for i, s in enumerate(piece.sections):
        t0 = piece.seconds(s.start)
        t1 = piece.seconds(s.end) if i + 1 < len(piece.sections) else min(len(audio) / SR, piece.seconds(s.end))
        spans.append((s.name, t0, min(t1, len(audio) / SR)))
    if len(audio) / SR > piece.duration_s + 0.5:
        spans.append(("(tail)", piece.duration_s, len(audio) / SR))
    report["sections_db"] = analyze.section_loudness(audio, spans)
    report["problems"] = problems
    if pngs:
        spec = os.path.join(png_dir, f"{name}_spectrogram.png")
        roll = os.path.join(png_dir, f"{name}_pianoroll.png")
        analyze.spectrogram(out, spec, title=name)
        marks = []
        if kind == "loop":
            marks.append((piece.duration_s - xfade, "xfade"))
        if kind == "cue":
            marks.append((trim, "trim"))
        analyze.pianoroll(piece, roll, audio=audio, marks=marks)
        report["png"] = {"spectrogram": os.path.relpath(spec, ROOT), "pianoroll": os.path.relpath(roll, ROOT)}
    report["seconds"] = round(time.time() - t_start, 1)
    with open(os.path.join(work, "report.json"), "w") as f:
        json.dump(report, f, indent=1)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("piece", help="piece module (.py with build() -> score.Piece)")
    ap.add_argument("--out", help="output .ogg (default: piece.out or tests/output/music/<name>.ogg)")
    ap.add_argument("--kind", choices=["track", "loop", "cue"], help="override piece.kind")
    ap.add_argument("--loop", action="store_true", help="loopable: crossfade the music after the loop point into the start")
    ap.add_argument("--xfade", type=float, help="loop crossfade seconds (2-4; default piece.xfade_s = 3)")
    ap.add_argument("--trim", type=float, help="opening cue: keep the first N seconds (e.g. 2.4)")
    ap.add_argument("--trim-fade", type=float, help="fade at the end of the trimmed cue (default 0.3 s)")
    ap.add_argument("--length-check", action="store_true", help="fail when the duration is outside the range")
    ap.add_argument("--length", type=float, nargs=2, metavar=("MIN", "MAX"), help="duration range in s (default piece.length_range)")
    ap.add_argument("--work", help="work directory (default tests/output/music/<name>)")
    ap.add_argument("--no-png", action="store_true", help="skip the spectrogram and piano-roll PNGs")
    ap.add_argument("--jobs", type=int, default=4, help="parallel FluidSynth renders")
    ap.add_argument("--no-cache", action="store_true", help="re-render every stem (the cache in <work>/cache is keyed "
                    "by the stem MIDI or the synth notes and code, so it is safe to keep)")
    ap.add_argument("--no-levels", action="store_true", help="skip the per-stem active-level measurement")
    a = ap.parse_args(argv)
    kind = "loop" if a.loop else a.kind
    rep = render(a.piece, out=a.out, kind=kind, xfade=a.xfade, trim=a.trim, trim_fade=a.trim_fade,
                 length_check=a.length_check, length=a.length, work=a.work, pngs=not a.no_png, jobs=a.jobs,
                 levels=not a.no_levels, cache=not a.no_cache)
    print(json.dumps(rep, indent=1))
    if rep["problems"]:
        log("[render] PROBLEMS: " + "; ".join(rep["problems"]))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
