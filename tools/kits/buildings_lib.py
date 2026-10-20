"""Core of the procedural building kit (used by tools/kits/buildings.py).

Self-contained (only numpy, Pillow, bpy/bmesh/mathutils and tools/texture_tools.py), deterministic:
geometry comes from seeded numpy generators and mathutils noise, textures are the repo's painted
swatches (made tileable in memory) or painted procedurally with numpy/Pillow, and the GLB writer
emits byte-identical files for identical inputs.

Build space is Blender-like: metres, **Z up, the building's front (door) faces +Y**. The writer
converts to glTF/Godot space with (x, y, z) -> (x, z, -y), so the front ends up facing **-Z**.

Materials per building (glTF names):
  <id>          opaque atlas of every tileable swatch the building uses (one texture, cells of
                512 px: 448 px of swatch + 32 px wrap padding, 128 px/m at the default 3.5 m repeat)
  <id>_GLOW     night windows / smoke-ring glow (emissive; scale emission at night)
  <id>_TEAM     team-colour cloth (light grey texture, UnitView multiplies albedo_color)

Vertex data written per vertex:
  COLOR_0     RGB = painted AO + per-part tint (multiplies albedo), A = 1
  TEXCOORD_1  (UV2) x = build layer (0 = frame / lattice / structure, 1 = covering: felt, roof
              skin; lets a build_progress shader reveal in two passes), y = normalized height
              (0 at the ground, 1 at the building's top) for the bottom-up build reveal
"""
from __future__ import annotations

import io
import json
import math
import os
import struct
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import bmesh
import mathutils
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import texture_tools as TT  # noqa: E402

Image.MAX_IMAGE_PIXELS = 300_000_000

CELL = 512          # atlas cell (px)
PAD = 32            # wrap padding inside a cell (px)
INNER = CELL - 2 * PAD


def log(*a):
    print("[buildings]", *a, file=sys.stderr, flush=True)


def seed_of(*parts) -> int:
    return zlib.crc32("|".join(str(p) for p in parts).encode()) & 0x7FFFFFFF


# =============================================================================================
# small math helpers
# =============================================================================================

def nrm(a, axis=-1):
    a = np.asarray(a, float)
    n = np.linalg.norm(a, axis=axis, keepdims=True)
    return a / np.maximum(n, 1e-12)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / max(e1 - e0, 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hexcol(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    """Euler XYZ in degrees -> 3x3 numpy."""
    m = mathutils.Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix()
    return np.array(m)


def axis_angle(axis, deg):
    return np.array(Matrix.Rotation(math.radians(deg), 3, Vector(axis)))


def frame_from_z(n):
    """3x3 basis whose third column is n."""
    n = nrm(n)
    ref = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    t = nrm(np.cross(ref, n))
    b = np.cross(n, t)
    return np.stack([t, b, n], axis=1)


# NB: mathutils.noise.noise_vector() reads a random offset table that Blender seeds from the clock
# when the module loads (unless noise.seed_set() is called), so it differs between runs. Vector noise
# here is three scalar noise() lookups at fixed offsets instead: deterministic whatever the global seed.
_VEC_OFFS = ((0.0, 0.0, 0.0), (31.416, 47.853, 12.793), (73.205, 5.741, 91.517))


def noise_vec(p, freq, off):
    out = np.empty((len(p), 3))
    nz = mathutils.noise.noise
    for i, q in enumerate(p):
        x, y, z = q[0] * freq + off[0], q[1] * freq + off[1], q[2] * freq + off[2]
        for k, (ox, oy, oz) in enumerate(_VEC_OFFS):
            out[i, k] = nz(Vector((x + ox, y + oy, z + oz)), noise_basis="PERLIN_ORIGINAL")
    return out


def noise_scalar(p, freq, off):
    out = np.empty(len(p))
    for i, q in enumerate(p):
        out[i] = mathutils.noise.noise(Vector((q[0] * freq + off[0], q[1] * freq + off[1], q[2] * freq + off[2])),
                                       noise_basis="PERLIN_ORIGINAL")
    return out


# =============================================================================================
# textures
# =============================================================================================

_IMG_CACHE: dict = {}


def cached(key, fn):
    if key not in _IMG_CACHE:
        _IMG_CACHE[key] = fn()
    return _IMG_CACHE[key]


def load_rgb(rel):
    im = Image.open(os.path.join(REPO, rel))
    im.load()
    return im


def to_img(a, mode="RGB"):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode)


def to_arr(im):
    return np.asarray(im.convert("RGB"), np.float32) / 255.0


def periodic_noise(n, seed, beta=2.2, lo=1.0):
    """Tileable fractal noise in [0, 1] (FFT 1/f^beta)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    f = np.fft.fft2(w)
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt(kx * kx + ky * ky)
    k[0, 0] = 1.0
    amp = 1.0 / np.power(np.maximum(k, lo), beta / 2.0)
    amp[0, 0] = 0.0
    r = np.real(np.fft.ifft2(f * amp))
    r -= r.min()
    r /= max(r.max(), 1e-9)
    return r


def crossfade_seamless(im, blend=0.125, flatten="auto"):
    """texture_tools.py `seamless` (variance-preserving crossfade + optional lighting flatten)."""
    arr = TT.to_float(im.convert("RGB"))
    H, W = arr.shape[:2]
    flat = (1.0 if TT.lowfreq_unevenness(arr) > 0.08 else 0.0) if flatten == "auto" else float(flatten)
    if flat > 0:
        arr = TT.flatten_lighting(arr, flat)
    bx = max(2, int(round(W * blend)))
    by = max(2, int(round(H * blend)))
    arr = TT.crossfade_x(arr, bx, wrap_other=False)
    arr = np.swapaxes(TT.crossfade_x(np.swapaxes(arr, 0, 1), by, wrap_other=True), 0, 1)
    out = TT.from_float(arr, "RGB")
    p = 8
    arr_p = np.pad(np.asarray(out), [(p, p), (p, p), (0, 0)], mode="wrap")
    big = Image.fromarray(arr_p, "RGB")
    sx, sy = W / out.width, H / out.height
    big = big.resize((round(big.width * sx), round(big.height * sy)), Image.LANCZOS)
    ox, oy = round(p * sx), round(p * sy)
    return big.crop((ox, oy, ox + W, oy + H))


def _period(lum, axis, lo_frac=0.06, hi_frac=0.55):
    """Dominant period (px, float) of a 2D luminance image along `axis` (autocorrelation peak)."""
    a = lum - lum.mean()
    if axis == 0:
        a = a.T
    n = a.shape[1]
    f = np.fft.rfft(a, n=2 * n, axis=1)
    ac = np.fft.irfft(f * np.conj(f), axis=1)[:, :n].mean(axis=0)
    ac /= max(ac[0], 1e-9)
    lo, hi = int(n * lo_frac), int(n * hi_frac)
    seg = ac[lo:hi]
    # first strong local maximum (avoid picking harmonics)
    peaks = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]]
    if not peaks:
        return None
    best = max(seg[i] for i in peaks)
    for i in peaks:
        if seg[i] >= 0.8 * best:
            k = i + lo
            # parabolic refinement
            y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
            d = 0.5 * (y0 - y2) / max(y0 - 2 * y1 + y2, -1e9) if (y0 - 2 * y1 + y2) != 0 else 0.0
            return float(k + np.clip(d, -0.5, 0.5)), float(seg[i])
    return None


def period_seamless(im, blend=0.06, axes=(True, True), min_corr=0.25):
    """Patterned swatch (tiles, quilting, lattice, scales): crop an integer number of pattern
    periods per axis, resample back to the input size, then a light crossfade for the residue."""
    arr = to_arr(im)
    H, W = arr.shape[:2]
    lum = arr.mean(axis=2)
    crop = [W, H]
    for ax, use in ((1, axes[0]), (0, axes[1])):
        if not use:
            continue
        r = _period(lum, axis=0 if ax == 0 else 1)
        if r is None or r[1] < min_corr:
            continue
        P = r[0]
        size = W if ax == 1 else H
        n = max(1, int(size // P))
        crop[0 if ax == 1 else 1] = int(round(n * P))
    cw, ch = crop
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    c = im.convert("RGB").crop((x0, y0, x0 + cw, y0 + ch))
    if c.size != (W, H):
        c = c.resize((W, H), Image.LANCZOS)
    return crossfade_seamless(c, blend=blend, flatten=0.0)


def adjust(im, tint=None, sat=None, gamma=None, gain=None):
    a = to_arr(im)
    if sat is not None:
        lum = a.mean(axis=2, keepdims=True)
        a = lum + (a - lum) * sat
    if tint is not None:
        a = a * np.asarray(tint, np.float32)
    if gain is not None:
        a = a * gain
    if gamma is not None:
        a = np.power(np.clip(a, 0, 1), gamma)
    return to_img(a)


def recolor(im, target_hex, strength=1.0, keep_value=True):
    """Shift the image's mean colour to target (keeps the value structure)."""
    a = to_arr(im)
    mean = a.reshape(-1, 3).mean(axis=0)
    tgt = hexcol(target_hex)
    if keep_value:
        out = a * (tgt / np.maximum(mean, 1e-3))
    else:
        out = a - mean + tgt
    return to_img(lerp(a, out, strength))


def _sat_val(a):
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0), mx


def grade(im, mean=None, sat_cap=0.65, v_floor=None, strength=1.0):
    """Faction-LUT stand-in for a swatch (art bible 1.4 / 5.7): move the mean colour to `mean`
    (per-channel gain, keeps the painted value structure), then clamp every pixel's HSV saturation to
    `sat_cap` (chroma scaled towards the pixel's max channel: hue and value kept). v_floor lifts the
    mean value to at least that (0..1)."""
    a = to_arr(im).astype(np.float64)
    for _ in range(3):
        if mean is not None:
            m = a.reshape(-1, 3).mean(axis=0)
            tgt = hexcol(mean)
            a = lerp(a, a * (tgt / np.maximum(m, 1e-3)), strength)
        if v_floor is not None:
            mv = a.max(axis=2).mean()
            if mv < v_floor:
                a = a * (v_floor / max(mv, 1e-3))
        a = np.clip(a, 0, 1)
        s, mx = _sat_val(a)
        over = s > sat_cap
        if over.any():
            k = np.where(over, sat_cap / np.maximum(s, 1e-6), 1.0)[..., None]
            a = mx[..., None] - (mx[..., None] - a) * k
    return to_img(a)


def swatch_stats(im):
    """Mean colour (hex), mean value, mean / p95 saturation of a swatch image."""
    a = to_arr(im).astype(np.float64)
    s, mx = _sat_val(a)
    m = a.reshape(-1, 3).mean(axis=0)
    return {"mean": "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in m), "V": round(float(mx.mean()), 3),
            "S": round(float(s.mean()), 3), "S_p95": round(float(np.percentile(s, 95)), 3)}


def swatch_img(rel, method="crossfade", size=INNER, grade_to=None, sat_cap=0.65, v_floor=None, **kw):
    """Painted swatch from the repo, made tileable, adjusted and graded (faction LUT stand-in:
    mean colour `grade_to`, saturation <= sat_cap). Returns a callable (cached)."""
    def fn():
        im = load_rgb(rel).convert("RGB")
        if method == "crossfade":
            im = crossfade_seamless(im)
        elif method == "period":
            im = period_seamless(im)
        elif method == "periodx":
            im = period_seamless(im, axes=(True, False))
        elif method == "periody":
            im = period_seamless(im, axes=(False, True))
        if kw:
            im = adjust(im, **kw)
        if grade_to is not None or sat_cap is not None:
            im = grade(im, grade_to, 1.0 if sat_cap is None else sat_cap, v_floor)
        return im
    key = ("sw", rel, method, grade_to, sat_cap, v_floor, tuple(sorted((k, str(v)) for k, v in kw.items())))
    return lambda: cached(key, fn)


# ---------------------------------------------------------------------------- procedural paint

def _strokes(W, H, strokes, ss=2, wrap=True):
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    offs = (-W, 0, W) if wrap else (0,)
    for pts, width, col in strokes:
        for ox in offs:
            for oy in offs:
                q = [((x + ox) * ss, (y + oy) * ss) for x, y in pts]
                d.line(q, fill=col, width=max(1, int(width * ss)), joint="curve")
    return im.resize((W, H), Image.LANCZOS)


def _ellipses(W, H, items, ss=2, wrap=True):
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    offs = (-W, 0, W) if wrap else (0,)
    for (x, y, rx, ry, col) in items:
        for ox in offs:
            for oy in offs:
                cx, cy = (x + ox) * ss, (y + oy) * ss
                d.ellipse([cx - rx * ss, cy - ry * ss, cx + rx * ss, cy + ry * ss], fill=col)
    return im.resize((W, H), Image.LANCZOS)


def tex_iron(seed=7, n=INNER):
    """Blackened iron: dark grey-blue, broad painted highlight streaks, a few rivets. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        base = hexcol("#3D4046")
        nz = periodic_noise(n, seed, 2.4)[..., None]
        a = np.ones((n, n, 3)) * base * (0.82 + 0.35 * nz)
        im = to_img(a).convert("RGBA")
        hi = hexcol("#7E848C")
        st = []
        for _ in range(70):
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            L = rng.uniform(30, 110)
            c = tuple(int(v * 255) for v in hi) + (int(rng.uniform(40, 110)),)
            st.append(([(x, y), (x + L, y + rng.normal(0, 2))], rng.uniform(2, 5), c))
        im.alpha_composite(_strokes(n, n, st))
        riv = []
        step = n // 4
        for i in range(4):
            for j in range(4):
                x, y = i * step + step / 2, j * step + step / 2
                riv.append((x + 1.5, y + 1.5, 6, 6, (20, 22, 26, 200)))
                riv.append((x, y, 5, 5, (110, 114, 120, 255)))
                riv.append((x - 1.5, y - 1.5, 2, 2, (170, 174, 180, 255)))
        im.alpha_composite(_ellipses(n, n, riv))
        return im.convert("RGB")
    return lambda: cached(("iron", seed, n), fn)


def tex_brick(seed=9, n=INNER, base="#8A4632", mortar="#B9A88A", rows=6, per_row=3):
    """Chunky hand-painted brick: few big bricks, lighter top edges, dark gaps. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        a = np.ones((n, n, 3)) * hexcol(mortar) * (0.85 + 0.2 * periodic_noise(n, seed + 1, 2.0)[..., None])
        im = to_img(a).convert("RGBA")
        d = ImageDraw.Draw(im)
        bh = n / rows
        bw = n / per_row
        g = max(3, int(n * 0.012))
        for r in range(rows):
            off = (bw / 2) * (r % 2)
            for k in range(-1, per_row + 1):
                x0 = k * bw + off + g
                x1 = x0 + bw - 2 * g
                y0 = r * bh + g
                y1 = y0 + bh - 2 * g
                col = hexcol(base) * rng.uniform(0.78, 1.12) * np.array([1.0, rng.uniform(0.92, 1.05), rng.uniform(0.9, 1.05)])
                c = tuple(int(np.clip(v, 0, 1) * 255) for v in col)
                for ox in (-n, 0, n):
                    d.rounded_rectangle([x0 + ox, y0, x1 + ox, y1], radius=g * 2, fill=c + (255,))
                    # lighter top edge, darker bottom edge (painted light)
                    lc = tuple(int(min(255, v * 1.25)) for v in c) + (255,)
                    dc = tuple(int(v * 0.7) for v in c) + (255,)
                    d.rectangle([x0 + ox + g, y0, x1 + ox - g, y0 + g * 1.2], fill=lc)
                    d.rectangle([x0 + ox + g, y1 - g * 1.2, x1 + ox - g, y1], fill=dc)
        a = to_arr(im)
        a *= (0.88 + 0.24 * periodic_noise(n, seed + 2, 2.6))[..., None]
        return to_img(a).filter(ImageFilter.GaussianBlur(0.6))
    return lambda: cached(("brick", seed, n, base, mortar, rows, per_row), fn)


def tex_straw(seed=11, n=INNER):
    """Golden straw / thatch: dense strands, painted highlights, darker gaps. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        base = hexcol("#B8954A")
        bg = np.ones((n, n, 3)) * base * 0.62
        bg *= (0.85 + 0.3 * periodic_noise(n, seed + 1, 2.6))[..., None]
        im = to_img(bg).convert("RGBA")
        cols = ["#E6CC7A", "#D8B460", "#C9A85A", "#A8843E", "#EED98E", "#8E6E30"]
        st = []
        for _ in range(1300):
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            L = rng.uniform(30, 120)
            ang = rng.normal(0, 0.35)
            c = hexcol(cols[rng.integers(0, len(cols))])
            st.append(([(x, y), (x + math.sin(ang) * L, y + math.cos(ang) * L)], rng.uniform(1.4, 3.0),
                       tuple(int(v * 255) for v in c) + (int(rng.uniform(170, 255)),)))
        im.alpha_composite(_strokes(n, n, st))
        return im.convert("RGB")
    return lambda: cached(("straw", seed, n), fn)


def tex_wattle(seed=13, n=INNER):
    """Woven hazel wattle panel: horizontal rods woven around vertical stakes. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        a = np.ones((n, n, 3)) * hexcol("#3A2A1C") * 0.8
        im = to_img(a).convert("RGBA")
        d = ImageDraw.Draw(im)
        rows = 10
        rh = n / rows
        stakes = 4
        sw = n / stakes
        for r in range(rows):
            y = r * rh + rh / 2
            for k in range(stakes):
                x0 = k * sw
                phase = (r + k) % 2
                yy = y + (rh * 0.18 if phase else -rh * 0.18)
                col = hexcol("#8A6A44") * rng.uniform(0.8, 1.15)
                c = tuple(int(np.clip(v, 0, 1) * 255) for v in col) + (255,)
                hc = tuple(int(np.clip(v * 1.3, 0, 1) * 255) for v in col) + (255,)
                for ox in (-n, 0, n):
                    d.ellipse([x0 + ox - 4, yy - rh * 0.42, x0 + sw + ox + 4, yy + rh * 0.42], fill=c)
                    d.line([(x0 + ox + sw * 0.15, yy - rh * 0.22), (x0 + sw * 0.85 + ox, yy - rh * 0.22)], fill=hc, width=3)
        for k in range(stakes):
            x = k * sw
            for ox in (-n, 0, n):
                d.rectangle([x + ox - 7, 0, x + ox + 7, n], fill=(70, 50, 34, 255))
                d.line([(x + ox - 3, 0), (x + ox - 3, n)], fill=(110, 82, 56, 255), width=3)
        return im.convert("RGB").filter(ImageFilter.GaussianBlur(0.7))
    return lambda: cached(("wattle", seed, n), fn)


def tex_stone(seed=17, n=INNER, base="#7D766A", dark="#5E574E", light="#9A9284"):
    """Rough-hewn grey standing-stone surface: big soft facets, chisel strokes, lichen specks."""
    def fn():
        rng = np.random.default_rng(seed)
        nz = periodic_noise(n, seed, 2.8)
        nz2 = periodic_noise(n, seed + 3, 1.6)
        b, dk, lt = hexcol(base), hexcol(dark), hexcol(light)
        a = lerp(dk[None, None, :], lt[None, None, :], np.clip(nz * 1.2 - 0.1, 0, 1)[..., None])
        a = a * (0.9 + 0.2 * nz2[..., None])
        a = lerp(a, b[None, None, :], 0.35)
        im = to_img(a).convert("RGBA")
        st = []
        for _ in range(140):
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            L = rng.uniform(12, 40)
            ang = rng.uniform(-0.6, 0.6) + math.pi / 2 * rng.integers(0, 2)
            c = (60, 56, 50, int(rng.uniform(60, 130))) if rng.random() < 0.6 else (175, 170, 160, int(rng.uniform(50, 110)))
            st.append(([(x, y), (x + math.cos(ang) * L, y + math.sin(ang) * L)], rng.uniform(2, 4), c))
        im.alpha_composite(_strokes(n, n, st))
        sp = []
        for _ in range(60):
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            r = rng.uniform(3, 9)
            c = (168, 176, 78, 200) if rng.random() < 0.6 else (190, 190, 150, 160)
            sp.append((x, y, r, r * rng.uniform(0.6, 1.0), c))
        im.alpha_composite(_ellipses(n, n, sp))
        return im.convert("RGB")
    return lambda: cached(("stone", seed, n, base), fn)


def tex_glyph_stone(seed=19, n=INNER, which="both"):
    """Decal: standing-stone face with carved hail (six-pointed star in a ring) and wind (flowing
    double curl) glyphs, pale lichen-gold infill so they read from above. No faces. which = "hail" or
    "wind" paints one glyph centred in a square decal (a square quad on the stone: no stretch)."""
    if which in ("hail", "wind"):
        return _glyph_single(seed, n, which)

    def fn():
        im = tex_stone(seed, n)().copy().convert("RGBA")
        ss = 3
        lay = Image.new("RGBA", (n * ss, n * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx = n * ss / 2
        groove = (58, 54, 48, 255)
        fill = (214, 206, 150, 255)
        # hail glyph: ring + six spokes with hooks (upper)
        cy = n * ss * 0.33
        R = n * ss * 0.17
        for w, col in ((int(n * ss * 0.045), groove), (int(n * ss * 0.022), fill)):
            d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=w)
            for k in range(6):
                a = k * math.pi / 3 + math.pi / 6
                x1, y1 = cx + math.cos(a) * R * 0.25, cy + math.sin(a) * R * 0.25
                x2, y2 = cx + math.cos(a) * R * 0.78, cy + math.sin(a) * R * 0.78
                d.line([(x1, y1), (x2, y2)], fill=col, width=w)
        # wind glyph: two flowing curls (lower)
        for w, col in ((int(n * ss * 0.045), groove), (int(n * ss * 0.022), fill)):
            for dy, sgn in ((0.62, 1), (0.80, -1)):
                pts = []
                for i in range(40):
                    t = i / 39
                    x = n * ss * (0.18 + 0.64 * t)
                    y = n * ss * dy + sgn * math.sin(t * math.pi * 2) * n * ss * 0.05
                    pts.append((x, y))
                d.line(pts, fill=col, width=w, joint="curve")
                ex, ey = pts[-1]
                d.ellipse([ex - n * ss * 0.03, ey - n * ss * 0.03, ex + n * ss * 0.03, ey + n * ss * 0.03], outline=col, width=w)
        lay = lay.resize((n, n), Image.LANCZOS)
        im.alpha_composite(lay)
        return im.convert("RGB")
    return lambda: cached(("glyph", seed, n), fn)


def _glyph_single(seed, n, which):
    def fn():
        im = tex_stone(seed, n)().copy().convert("RGBA")
        ss = 3
        N = n * ss
        lay = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        groove = (58, 54, 48, 255)
        fill = (214, 206, 150, 255)
        cx = cy = N / 2
        for w, col in ((int(N * 0.075), groove), (int(N * 0.038), fill)):
            if which == "hail":
                R = N * 0.34
                d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=w)
                for k in range(6):
                    a = k * math.pi / 3 + math.pi / 6
                    d.line([(cx + math.cos(a) * R * 0.22, cy + math.sin(a) * R * 0.22),
                            (cx + math.cos(a) * R * 0.76, cy + math.sin(a) * R * 0.76)], fill=col, width=w)
            else:
                for dy, sgn in ((0.36, 1), (0.66, -1)):
                    pts = [(N * (0.14 + 0.66 * t), N * dy + sgn * math.sin(t * math.pi * 2) * N * 0.08)
                           for t in np.linspace(0, 1, 40)]
                    d.line(pts, fill=col, width=w, joint="curve")
                    ex, ey = pts[-1]
                    r = N * 0.05
                    d.ellipse([ex - r, ey - r, ex + r, ey + r], outline=col, width=w)
        im.alpha_composite(lay.resize((n, n), Image.LANCZOS))
        return im.convert("RGB")
    return lambda: cached(("glyph1", seed, n, which), fn)


def tex_bronze(seed=47, n=INNER, base="#6E4A26", hi="#B07F3E", dark="#3E2A18"):
    """Smooth hand-painted bronze (domes, cowls, bells): soft vertical value bands and a few broad
    highlight strokes, no scales or rivets (reads as one smooth bulb from the RTS camera). Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        nz = periodic_noise(n, seed, 2.8)
        x = (np.arange(n) + 0.5) / n
        band = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 2 + 0.7)
        t = np.clip(0.55 * band[None, :] + 0.45 * nz, 0, 1)[..., None]
        a = lerp(hexcol(dark)[None, None, :], hexcol(base)[None, None, :], np.clip(t * 1.6, 0, 1))
        a = lerp(a, hexcol(hi)[None, None, :], np.clip(t * 1.6 - 1.0, 0, 1) * 0.8)
        im = to_img(a).convert("RGBA")
        st = []
        hc = hexcol(hi)
        for _ in range(16):
            xx, yy = rng.uniform(0, n), rng.uniform(0, n)
            L = rng.uniform(n * 0.15, n * 0.4)
            c = tuple(int(v * 255) for v in np.clip(hc * 1.15, 0, 1)) + (int(rng.uniform(40, 90)),)
            st.append(([(xx, yy), (xx + rng.normal(0, 3), yy + L)], rng.uniform(n * 0.012, n * 0.03), c))
        im.alpha_composite(_strokes(n, n, st))
        return im.convert("RGB").filter(ImageFilter.GaussianBlur(1.2))
    return lambda: cached(("bronze", seed, n, base, hi, dark), fn)


def tex_rings(seed=5, n=INNER):
    """Decal: end-grain disc (pale rings, growth lines, radial cracks, bark rim); disc fills the
    square (centre 0.5, 0.5, radius 0.5)."""
    def fn():
        rng = np.random.default_rng(seed)
        y, x = np.mgrid[0:n, 0:n] + 0.5
        dx, dy = (x - n / 2) / (n / 2), (y - n / 2) / (n / 2)
        r = np.sqrt(dx * dx + dy * dy)
        th = np.arctan2(dy, dx)
        rr = r + (0.025 * np.sin(th * 3 + 1.3) + 0.018 * np.sin(th * 5 + 0.4)) * r
        pale, mid, dark = hexcol("#E9CF9B"), hexcol("#D2AF72"), hexcol("#9A7442")
        rings = np.power(0.5 + 0.5 * np.cos(rr * 2 * math.pi * 6.5), 6)
        col = pale[None, None, :] * (1 - r[..., None] * 0.25) + (mid - pale)[None, None, :] * 0.3 * r[..., None]
        col = col * (1 - rings[..., None] * 0.35) + dark * rings[..., None] * 0.35
        col = np.where((r < 0.06)[..., None], dark * 0.95, col)
        for _ in range(3):
            a0 = rng.uniform(-math.pi, math.pi)
            d_ang = np.abs(np.angle(np.exp(1j * (th - a0))))
            crack = (d_ang < 0.035 * (1.0 - r)) & (r > 0.08) & (r < rng.uniform(0.55, 0.85))
            col = np.where(crack[..., None], dark * 0.7, col)
        bark = hexcol("#4A3424") * (0.8 + 0.4 * periodic_noise(n, seed + 3, 2.0))[..., None]
        rim = smoothstep(0.80, 0.88, r)[..., None]
        col = col * (1 - rim) + bark * rim
        return to_img(col)
    return lambda: cached(("rings", seed, n), fn)


def tex_leaves(seed=23, n=INNER, src="assets/textures/foliage/linden_clumps.png", base="#3F5A2C"):
    """Opaque leafy tile: the painted 2x2 clump cards scattered (wrapped) over a dark green."""
    def fn():
        rng = np.random.default_rng(seed)
        clumps = load_rgb(src).convert("RGBA")
        cw = clumps.width // 2
        cards = [clumps.crop((i * cw, j * cw, (i + 1) * cw, (j + 1) * cw)) for j in range(2) for i in range(2)]
        a = np.ones((n, n, 3)) * hexcol(base) * (0.8 + 0.35 * periodic_noise(n, seed, 2.2))[..., None]
        im = to_img(a).convert("RGBA")
        big = Image.new("RGBA", (n * 3, n * 3), (0, 0, 0, 0))
        for _ in range(26):
            c = cards[rng.integers(0, 4)]
            s = int(n * rng.uniform(0.42, 0.62))
            c = c.resize((s, s), Image.LANCZOS).rotate(float(rng.uniform(0, 360)), resample=Image.BICUBIC)
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            for ox in (0, n, 2 * n):
                for oy in (0, n, 2 * n):
                    big.alpha_composite(c, (int(x + ox - s / 2), int(y + oy - s / 2)))
        im.alpha_composite(big.crop((n, n, 2 * n, 2 * n)))
        return im.convert("RGB")
    return lambda: cached(("leaves", seed, n, src), fn)


def tex_palette(colors, seed=29, n=INNER):
    """Decal: 4x4 blocks of flat painted colours for small props (UVs collapse to a block centre)."""
    def fn():
        a = np.zeros((n, n, 3))
        k = 4
        s = n // k
        for i, c in enumerate(colors[:16]):
            r, q = divmod(i, k)
            a[r * s:(r + 1) * s, q * s:(q + 1) * s] = hexcol(c)
        return to_img(a)
    return lambda: cached(("palette", tuple(colors), n), fn)


def palette_uv(colors, name):
    i = colors.index(name)
    r, q = divmod(i, 4)
    return ((q + 0.5) / 4.0, (r + 0.5) / 4.0)


def tex_stripes(a_img, b_img, stripes=6, n=INNER, seam=(0.12, 0.10, 0.06), vertical=True):
    """Felt in broad alternating stripes of two swatches with dark stitched seams. Tileable."""
    def fn():
        A = to_arr(a_img().resize((n, n), Image.LANCZOS))
        B = to_arr(b_img().resize((n, n), Image.LANCZOS))
        x = (np.arange(n) + 0.5) / n
        band = (np.floor(x * stripes) % 2).astype(bool)
        m = band[None, :] if vertical else band[:, None]
        out = np.where(m[..., None], B, A)
        f = (x * stripes) % 1.0
        edge = np.minimum(f, 1 - f) * n / stripes
        sm = (1 - smoothstep(0, 4, edge))
        sm = sm[None, :] if vertical else sm[:, None]
        out = out * (1 - 0.45 * sm[..., None])
        # stitch dashes along the seams
        im = to_img(out).convert("RGBA")
        d = ImageDraw.Draw(im)
        for k in range(stripes):
            p = k * n / stripes + 6
            for j in range(0, n, 18):
                if vertical:
                    d.line([(p, j), (p, j + 9)], fill=(236, 214, 160, 230), width=3)
                else:
                    d.line([(j, p), (j + 9, p)], fill=(236, 214, 160, 230), width=3)
        return im.convert("RGB")
    return lambda: cached(("stripes", id(a_img), id(b_img), stripes, n, vertical), fn)


def tex_team_cloth(seed=31, n=256, border=False, emblem=None):
    """TEAM material texture: light neutral grey cloth (multiplied by the player colour) with an
    optional lighter emblem (decal). No piping in here: the neutral piping (bible 3.1 rule 4) is cut
    out of the TEAM faces at export (split_team_border) and lands in the faction atlas as ivory /
    bronze, so it is never tinted."""
    def fn():
        nz = periodic_noise(n, seed, 2.4)
        g = 0.80 + 0.06 * (nz - 0.5)
        a = np.stack([g, g, g], axis=-1)
        # faint weave
        y, x = np.mgrid[0:n, 0:n]
        a *= (1.0 + 0.02 * np.sin(x * 1.3) * np.sin(y * 1.3))[..., None]
        im = to_img(a).convert("RGBA")
        d = ImageDraw.Draw(im)
        if emblem == "wheel":
            cx = cy = n / 2
            R = n * 0.26
            col = (246, 246, 246, 255)
            d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=max(5, n // 22))
            for k in range(6):
                ang = k * math.pi / 3
                d.line([(cx, cy), (cx + math.cos(ang) * R, cy + math.sin(ang) * R)], fill=col, width=max(4, n // 36))
            d.ellipse([cx - R * 0.24, cy - R * 0.24, cx + R * 0.24, cy + R * 0.24], fill=(150, 150, 150, 255))
        elif emblem == "gong":
            cx = cy = n / 2
            R = n * 0.24
            d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(246, 246, 246, 255))
            d.ellipse([cx - R * 0.55, cy - R * 0.55, cx + R * 0.55, cy + R * 0.55], outline=(165, 165, 165, 255), width=4)
            for k in (-1, 1):
                pts = [(cx + k * R * (1.2 + 0.5 * t), cy - R * 0.6 + R * 1.2 * t + k * math.sin(t * 6) * 4) for t in np.linspace(0, 1, 12)]
                d.line(pts, fill=(246, 246, 246, 255), width=max(3, n // 40), joint="curve")
        return im.convert("RGB")
    return lambda: cached(("teamcloth", seed, n, border, emblem), fn)


def tex_team_band(seed=37, n=256):
    """TEAM tile: plain felt band (tiles in u); piping is cut out at export like on the cloth."""
    def fn():
        nz = periodic_noise(n, seed, 2.4)
        g = 0.80 + 0.06 * (nz - 0.5)
        a = np.stack([g, g, g], axis=-1)
        y, x = np.mgrid[0:n, 0:n]
        a *= (1.0 + 0.025 * np.sin(x * 0.9 + y * 0.9))[..., None]
        # stitches (lighter, so they tint to a lighter shade of the player colour)
        for j in range(0, n, 16):
            a[n // 2 - 2:n // 2 + 1, j:j + 8] = 0.9
        return to_img(a)
    return lambda: cached(("teamband", seed, n), fn)


def tex_window(seed=41, n=224, style="kingdom"):
    """GLOW decal: a mullioned window (dark oak frame and cross, warm amber panes, lighter top)."""
    def fn():
        a = np.zeros((n, n, 3))
        y, x = np.mgrid[0:n, 0:n] / n
        warm = lerp(hexcol("#F7C46A"), hexcol("#D9722A"), np.clip(y * 1.1, 0, 1)[..., None])
        a[:] = warm
        im = to_img(a).convert("RGBA")
        d = ImageDraw.Draw(im)
        f = int(n * 0.11)
        oak = (58, 38, 24, 255)
        d.rectangle([0, 0, n - 1, f], fill=oak)
        d.rectangle([0, n - 1 - f, n - 1, n - 1], fill=oak)
        d.rectangle([0, 0, f, n - 1], fill=oak)
        d.rectangle([n - 1 - f, 0, n - 1, n - 1], fill=oak)
        m = int(n * 0.06)
        d.rectangle([n / 2 - m, 0, n / 2 + m, n], fill=oak)
        d.rectangle([0, n * 0.48 - m, n, n * 0.48 + m], fill=oak)
        # lead cames (diamond panes)
        for k in range(-4, 5):
            d.line([(k * n / 4, 0), (k * n / 4 + n, n)], fill=(120, 70, 30, 160), width=2)
            d.line([(k * n / 4 + n, 0), (k * n / 4, n)], fill=(120, 70, 30, 160), width=2)
        d.rectangle([0, 0, n - 1, f], fill=oak)
        d.rectangle([0, n - 1 - f, n - 1, n - 1], fill=oak)
        d.rectangle([0, 0, f, n - 1], fill=oak)
        d.rectangle([n - 1 - f, 0, n - 1, n - 1], fill=oak)
        d.rectangle([n / 2 - m, 0, n / 2 + m, n], fill=oak)
        d.rectangle([0, n * 0.48 - m, n, n * 0.48 + m], fill=oak)
        return im.convert("RGB")
    return lambda: cached(("window", seed, n, style), fn)


def tex_ember(seed=43, n=224):
    """GLOW decal: glowing coals / molten bronze / smoke-ring glow (radial)."""
    def fn():
        rng = np.random.default_rng(seed)
        y, x = np.mgrid[0:n, 0:n] + 0.5
        r = np.sqrt((x - n / 2) ** 2 + (y - n / 2) ** 2) / (n / 2)
        nz = periodic_noise(n, seed, 2.0)
        hot = lerp(hexcol("#FFE6A0"), hexcol("#F08A2A"), np.clip(r * 1.1 + (nz - 0.5) * 0.5, 0, 1)[..., None])
        hot = lerp(hot, hexcol("#8A2E12"), np.clip((r - 0.65) * 2.5, 0, 1)[..., None])
        return to_img(hot)
    return lambda: cached(("ember", seed, n), fn)


# =============================================================================================
# swatches and atlas packing
# =============================================================================================

class Swatch:
    """A texture region of a building material.

    kind  "tile":  UVs in repeat units (u, v); triangles are cut on integer lines and each piece is
                   mapped into the cell (wrap padding hides the cell border at normal mip levels)
          "decal": UVs in [0, 1] map onto the cell's inner square (clamped)
    group "atlas" | "team" | "glow": which glTF material (and shared sheet) the swatch belongs to
    repeat  world size (m) of one cell for tile swatches; the cell is repeat * DENSITY px wide, so
            every swatch has the same texel density
    tiles   the swatch image is tiled tiles x tiles inside its cell (smaller pattern, e.g. roof
            tiles, without cutting the mesh on more UV lines)
    px      inner cell size for decals
    sheet_key  key in the shared sheet (defaults to key; TEAM / GLOW sheets are shared by both factions)
    """

    def __init__(self, key, image, repeat=3.5, kind="tile", group="atlas", rot90=False, tiles=1, px=None,
                 sheet_key=None):
        self.key = key
        self.image = image
        self.repeat = repeat
        self.kind = kind
        self.group = group
        self.rot90 = rot90
        self.tiles = tiles
        self.px = px
        self.sheet_key = sheet_key or key

    def __repr__(self):
        return f"Swatch({self.key})"


DENSITY = 144.0      # px per metre for tile swatches (art bible 1.6: buildings 128-160 px/m)
TILE_PAD = 16        # wrap padding (px) around tile cells
DECAL_PAD = 8        # edge padding (px) around decal cells


def build_atlas(swatches, cell=CELL, pad=PAD):
    """Legacy fixed-grid packer (kept for tools that still want one square grid)."""
    n = len(swatches)
    cols = 1 if n <= 1 else (2 if n <= 4 else 4)
    rows = 1 if n <= 2 else (2 if n <= 8 else 4)
    W, H = cols * cell, rows * cell
    atlas = np.zeros((H, W, 3), np.uint8)
    inner = cell - 2 * pad
    rects = {}
    for i, sw in enumerate(swatches):
        r, c = divmod(i, cols)
        arr = np.asarray(_cell_image(sw, inner))
        arr = np.pad(arr, [(pad, pad), (pad, pad), (0, 0)], mode="wrap" if sw.kind == "tile" else "edge")
        atlas[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = arr
        rects[sw.sheet_key] = (c * cell + pad, r * cell + pad, inner)
    return Image.fromarray(atlas, "RGB"), rects, (W, H)


def _cell_image(sw, inner):
    im = sw.image().convert("RGB")
    if sw.rot90:
        im = im.transpose(Image.ROTATE_90)
    k = max(1, int(sw.tiles))
    sub = max(8, int(round(inner / k)))
    if im.size != (sub, sub):
        im = im.resize((sub, sub), Image.LANCZOS)
    if k > 1:
        big = Image.new("RGB", (sub * k, sub * k))
        for i in range(k):
            for j in range(k):
                big.paste(im, (i * sub, j * sub))
        im = big.resize((inner, inner), Image.LANCZOS) if sub * k != inner else big
    return im


def cell_px(sw):
    """Inner cell size (px) of a swatch in a shared sheet."""
    if sw.kind == "tile":
        return int(max(64, round(sw.repeat * DENSITY / 8.0) * 8))
    return int(sw.px or 256)


class Sheet:
    """A shared texture sheet (faction atlas, TEAM sheet, GLOW sheet) referenced by every building GLB
    as an external image (uri), so all buildings of a faction share one texture in VRAM.

    Shelf packing (largest cells first, deterministic order), width `width`, height rounded up to a
    multiple of 64. rects: {sheet_key: (x0, y0, inner)} in px."""

    def __init__(self, name, swatches, width=2048, fmt="jpeg", quality=90):
        uniq = {}
        for sw in swatches:
            uniq.setdefault(sw.sheet_key, sw)
        items = sorted(uniq.values(), key=lambda s: (-cell_px(s), s.sheet_key))
        x = y = row_h = 0
        place = []
        for sw in items:
            inner = cell_px(sw)
            pad = TILE_PAD if sw.kind == "tile" else DECAL_PAD
            c = inner + 2 * pad
            if x + c > width:
                x, y, row_h = 0, y + row_h, 0
            place.append((sw, x, y, inner, pad))
            x += c
            row_h = max(row_h, c)
        H = y + row_h
        H = int(math.ceil(H / 64.0) * 64)
        W = width if y > 0 else int(math.ceil(x / 64.0) * 64)
        img = np.zeros((H, W, 3), np.uint8)
        self.rects = {}
        for sw, x0, y0, inner, pad in place:
            arr = np.asarray(_cell_image(sw, inner))
            arr = np.pad(arr, [(pad, pad), (pad, pad), (0, 0)], mode="wrap" if sw.kind == "tile" else "edge")
            img[y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]] = arr
            self.rects[sw.sheet_key] = (x0 + pad, y0 + pad, inner)
        # unused area: mean colour (clean mips)
        used = np.zeros((H, W), bool)
        for sw, x0, y0, inner, pad in place:
            used[y0:y0 + inner + 2 * pad, x0:x0 + inner + 2 * pad] = True
        if (~used).any():
            img[~used] = img[used].reshape(-1, 3).mean(0).astype(np.uint8)
        self.name = name
        self.image = Image.fromarray(img, "RGB")
        self.size = (W, H)
        self.fmt = fmt
        self.quality = quality
        ext = "jpg" if fmt == "jpeg" else "png"
        self.uri = f"textures/{name}.{ext}"
        self.mime = "image/jpeg" if fmt == "jpeg" else "image/png"
        self.swatches = [s.sheet_key for s in items]
        self.fill = round(float(used.mean()), 3)

    def write(self, out_dir):
        path = os.path.join(out_dir, self.uri)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data, _ = encode(self.image, self.fmt, self.quality)
        with open(path, "wb") as f:
            f.write(data)
        if not os.path.exists(path + ".import"):
            # first import as a 3D texture (VRAM-compressed, mipmaps); Godot keeps these params and adds uid / dest
            with open(path + ".import", "w") as f:
                f.write(GODOT_TEXTURE_IMPORT)
        return path


# Godot import settings for the shared sheets: VRAM-compressed with mipmaps (3D use). Godot fills in
# uid / dest paths on the first import.
GODOT_TEXTURE_IMPORT = (
    "[remap]\n\nimporter=\"texture\"\ntype=\"CompressedTexture2D\"\nmetadata={\n\"imported_formats\": "
    "[\"s3tc_bptc\", \"etc2_astc\"],\n\"vram_texture\": true\n}\n\n[params]\n\ncompress/mode=2\n"
    "compress/high_quality=false\ncompress/lossy_quality=0.7\ncompress/hdr_compression=1\ncompress/normal_map=2\n"
    "compress/channel_pack=0\nmipmaps/generate=true\nmipmaps/limit=-1\nroughness/mode=0\nprocess/fix_alpha_border=true\n"
    "process/premult_alpha=false\nprocess/size_limit=0\ndetect_3d/compress_to=0\n")


# =============================================================================================
# geometry: parts
# =============================================================================================

class Part:
    """Triangle mesh piece with one swatch. Shared vertices (v, t), per-corner UVs (M, 3, 2):
    tile swatches in repeat units, decals in [0, 1] (image convention, v down)."""

    def __init__(self, v, t, sw, uv=None, smooth=35.0):
        self.v = np.asarray(v, float).reshape(-1, 3)
        self.t = np.asarray(t, np.int64).reshape(-1, 3)
        self.sw = sw
        self.uv = np.zeros((len(self.t), 3, 2)) if uv is None else np.asarray(uv, float).reshape(-1, 3, 2)
        self.smooth = smooth          # normal smoothing angle (deg)
        self.dice = None              # max edge length (m) for AO tessellation, None = keep
        self.jit = 0.0                # smooth-noise jitter amplitude (m), scalar or (3,)
        self.tint = np.ones(3)        # vertex-colour multiplier (3,) or (N, 3)
        self.occ = True               # occludes AO rays
        self.ao = True                # receives raycast AO
        self.ao_mul = 1.0             # AO strength multiplier
        self.layer = 0.0              # UV2.x build layer
        self.form = 0.10              # lighter towards the top of this part (painted top light)
        self.uvrot = False            # swap u/v (grain direction) when mapping into the atlas
        self.min_shade = 0.0          # floor for the baked shade (e.g. emissive bits)
        self.faceted = False          # flat faces at hard angles (box / member / prism): each face
                                      # direction may get its own UV offset (no visible seam, fewer cuts)
        self.below = False            # may reach below the ground (apron skirts); everything else is
                                      # clamped to z >= 0
        self.base = True              # painted base darkening near the ground (off for ground aprons)

    # --- transforms (return self) -------------------------------------------------------------
    def xf(self, m):
        self.v = self.v @ np.asarray(m, float).T
        return self

    def rot(self, rx=0.0, ry=0.0, rz=0.0, pivot=(0, 0, 0)):
        p = np.asarray(pivot, float)
        self.v = (self.v - p) @ rot_matrix(rx, ry, rz).T + p
        return self

    def rot_axis(self, axis, deg, pivot=(0, 0, 0)):
        p = np.asarray(pivot, float)
        self.v = (self.v - p) @ axis_angle(axis, deg).T + p
        return self

    def move(self, x=0.0, y=0.0, z=0.0):
        self.v = self.v + np.array([x, y, z], float)
        return self

    def at(self, p):
        return self.move(*p)

    def scale(self, sx, sy=None, sz=None, pivot=(0, 0, 0)):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        p = np.asarray(pivot, float)
        self.v = (self.v - p) * np.array([sx, sy, sz]) + p
        if sx * sy * sz < 0:
            self.t = self.t[:, ::-1]
            self.uv = self.uv[:, ::-1]
        return self

    def set(self, **kw):
        for k, val in kw.items():
            if not hasattr(self, k):
                raise AttributeError(k)
            setattr(self, k, val)
        return self

    def tinted(self, rgb):
        self.tint = np.asarray(hexcol(rgb) if isinstance(rgb, str) else rgb, float)
        return self

    def copy(self):
        p = Part(self.v.copy(), self.t.copy(), self.sw, self.uv.copy(), self.smooth)
        for k in ("dice", "jit", "occ", "ao", "ao_mul", "layer", "form", "uvrot", "min_shade", "faceted", "below", "base"):
            setattr(p, k, getattr(self, k))
        p.tint = np.array(self.tint, float).copy()
        return p

    def box_uv(self, repeat=None, off=(0.0, 0.0)):
        rep = repeat if repeat is not None else self.sw.repeat
        self.uv = uv_box(self.v, self.t, rep, off)
        return self

    def tris(self):
        return len(self.t)


def uv_box(v, t, repeat, off=(0.0, 0.0)):
    """Per-triangle box projection, texture upright on side faces (image convention)."""
    p = v[t]
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    ax = np.argmax(np.abs(n), axis=1)
    uv = np.zeros((len(t), 3, 2))
    s = np.sign(n)
    s[s == 0] = 1
    mx, my, mz = ax == 0, ax == 1, ax == 2
    uv[mx, :, 0] = p[mx, :, 1] * s[mx, 0][:, None]
    uv[mx, :, 1] = -p[mx, :, 2]
    uv[my, :, 0] = -p[my, :, 0] * s[my, 1][:, None]
    uv[my, :, 1] = -p[my, :, 2]
    uv[mz, :, 0] = p[mz, :, 0]
    uv[mz, :, 1] = -p[mz, :, 1] * s[mz, 2][:, None]
    return uv / repeat + np.asarray(off, float)


def bm_arrays(bm):
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bm.verts.index_update()
    v = np.array([x.co[:] for x in bm.verts], float)
    t = np.array([[lp.vert.index for lp in f.loops] for f in bm.faces], np.int64)
    bm.free()
    return v, t


def icosphere(subdiv=2, radius=1.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius, calc_uvs=False)
    return bm_arrays(bm)


# ---------------------------------------------------------------------------- primitives

def box(sx, sy, sz, sw, center=(0, 0, 0), chamfer=0.0, uv_off=(0.0, 0.0), repeat=None, smooth=30.0,
        base=False):
    """Chamfered box centred at `center` (base=True: bottom at center z)."""
    c = min(chamfer, min(sx, sy, sz) * 0.45)
    if c > 1e-4:
        # chamfered along the four edges parallel to x (no bmesh bevel: its vertex order is not
        # stable between runs)
        p = sweep(rect_profile(sy, sz, c), np.array([(-sx / 2, 0.0, 0.0), (sx / 2, 0.0, 0.0)]), sw, up=(0, 0, 1),
                  smooth=smooth)
        # sweep frame for a +x path: N = up x T = +y, B = T x N = +z -> profile (y, z) as wanted
    else:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        v, t = bm_arrays(bm)
        p = Part(v, t, sw, smooth=smooth)
    p.box_uv(repeat, uv_off)
    p.faceted = True
    cz = center[2] + (sz / 2 if base else 0.0)
    return p.move(center[0], center[1], cz)


def member(p0, p1, w, h, sw, chamfer=None, roll_up=(0, 0, 1), extend=0.0, uv_off=None, rng=None):
    """Timber member (beam / post / brace) from p0 to p1 with a w x h section; grain along it."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d)) + 2 * extend
    if uv_off is None:
        uv_off = (0.0, 0.0) if rng is None else (float(rng.uniform(0, 1)), float(rng.uniform(0, 1)))
    ch = (min(w, h) * 0.15 if min(w, h) >= 0.13 else 0.0) if chamfer is None else chamfer
    p = box(L, w, h, sw, chamfer=ch, uv_off=uv_off)
    x = d / max(np.linalg.norm(d), 1e-9)
    up = np.asarray(roll_up, float)
    if abs(np.dot(up, x)) > 0.95:
        up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    y = nrm(np.cross(up, x))
    z = np.cross(x, y)
    R = np.stack([x, y, z], axis=1)
    p.xf(R)
    return p.move(*((p0 + p1) / 2))


def _poly_subdiv(ol, g):
    out = []
    K = len(ol)
    for i in range(K):
        a, b = ol[i], ol[(i + 1) % K]
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / g - 1e-6)))
        for k in range(n):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def _inside(poly, pts):
    """Even-odd point-in-polygon for (N, 2) points."""
    x, y = pts[:, 0], pts[:, 1]
    ins = np.zeros(len(pts), bool)
    K = len(poly)
    for i in range(K):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % K]
        cond = (y1 > y) != (y2 > y)
        xi = (x2 - x1) * (y - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1
        ins ^= cond & (x < xi)
    return ins


def _seg_dist(poly, pts):
    d = np.full(len(pts), 1e9)
    K = len(poly)
    for i in range(K):
        a, b = poly[i], poly[(i + 1) % K]
        ab = b - a
        t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        q = a + t[:, None] * ab
        d = np.minimum(d, np.linalg.norm(pts - q, axis=1))
    return d


def cap_tris(poly, z, g=None, up=True):
    """Triangulate a 2D polygon at height z (constrained Delaunay, optional interior grid points
    every g metres so AO can vary across big faces). Returns (verts (N, 3), tris)."""
    poly = np.asarray(poly, float)
    pts = [tuple(p) for p in poly]
    if g:
        xs = np.arange(poly[:, 0].min() + g * 0.5, poly[:, 0].max(), g)
        ys = np.arange(poly[:, 1].min() + g * 0.5, poly[:, 1].max(), g)
        if len(xs) and len(ys):
            gx, gy = np.meshgrid(xs, ys)
            cand = np.stack([gx.ravel(), gy.ravel()], 1)
            ok = _inside(poly, cand) & (_seg_dist(poly, cand) > g * 0.35)
            pts += [tuple(p) for p in cand[ok]]
    r = mathutils.geometry.delaunay_2d_cdt([Vector(p) for p in pts], [], [list(range(len(poly)))], 1, 1e-7)
    V2 = np.array([(v.x, v.y) for v in r[0]], float)
    T = np.array([f for f in r[2] if len(f) == 3], np.int64)
    used = np.unique(T)
    remap = np.full(len(V2), -1)
    remap[used] = np.arange(len(used))
    V2, T = V2[used], remap[T]
    a = V2[T]
    area = (a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1]) - (a[:, 2, 0] - a[:, 0, 0]) * (a[:, 1, 1] - a[:, 0, 1])
    flip = area < 0 if up else area > 0
    T[flip] = T[flip][:, ::-1]
    return np.concatenate([V2, np.full((len(V2), 1), z)], 1), T


def prism(outline, z0, z1, sw, chamfer=0.03, bottom=True, top=True, repeat=None, uv_off=(0.0, 0.0),
          smooth=30.0, grid=None, cap_grid="same"):
    """Extruded polygon (outline (K, 2), any winding, may be concave) from z0 to z1 with a chamfered
    top edge. grid (m): subdivide outline edges, add rings up the sides and interior points on the
    caps so the baked AO has vertices to vary on. Box-projected UVs."""
    ol = np.asarray(outline, float)
    area = 0.5 * np.sum(ol[:, 0] * np.roll(ol[:, 1], -1) - np.roll(ol[:, 0], -1) * ol[:, 1])
    if area < 0:
        ol = ol[::-1].copy()
    if grid:
        ol = _poly_subdiv(ol, grid)
    K = len(ol)

    def inset(poly, d):
        out = np.zeros_like(poly)
        for i in range(K):
            a, b, c = poly[i - 1], poly[i], poly[(i + 1) % K]
            e0, e1 = nrm(b - a), nrm(c - b)
            n0, n1 = np.array([e0[1], -e0[0]]), np.array([e1[1], -e1[0]])
            bis = nrm(n0 + n1)
            cosh = max(np.dot(bis, n0), 0.35)
            out[i] = b - bis * d / cosh
        return out

    c = min(chamfer, (z1 - z0) * 0.45)
    zt = z1 - c if c > 1e-4 else z1
    nz = max(1, int(math.ceil((zt - z0) / grid - 1e-6))) if grid else 1
    rings = [(ol, z0 + (zt - z0) * i / nz) for i in range(nz + 1)]
    if c > 1e-4:
        rings.append((inset(ol, c), z1))
    verts = [np.array([(p[0], p[1], z) for p in poly]) for poly, z in rings]
    V = np.concatenate(verts)
    tris = []
    R = len(rings)
    for s_ in range(R - 1):
        for k in range(K):
            a, b = s_ * K + k, s_ * K + (k + 1) % K
            cc, d = (s_ + 1) * K + (k + 1) % K, (s_ + 1) * K + k
            tris += [(a, b, cc), (a, cc, d)]
    tris = [np.array(tris, np.int64)]
    cg = grid if cap_grid == "same" else cap_grid
    if top:
        tv, tt = cap_tris(rings[-1][0], z1, cg, up=True)
        tris.append(tt + len(V))
        V = np.vstack([V, tv])
    if bottom:
        bv, bt = cap_tris(ol, z0, cg, up=False)
        tris.append(bt + len(V))
        V = np.vstack([V, bv])
    part = Part(V, np.concatenate(tris), sw, smooth=smooth)
    part.faceted = True
    return part.box_uv(repeat, uv_off)


def gbox(sx, sy, sz, sw, center=(0, 0, 0), chamfer=0.03, grid=0.4, base=True, bottom=False):
    """Box built as a gridded prism (for big boxes that need AO resolution)."""
    x, y, z = center
    ol = np.array([(x - sx / 2, y - sy / 2), (x + sx / 2, y - sy / 2), (x + sx / 2, y + sy / 2), (x - sx / 2, y + sy / 2)])
    z0 = z if base else z - sz / 2
    return prism(ol, z0, z0 + sz, sw, chamfer=chamfer, grid=grid, bottom=bottom)


def lathe(profile, sides, sw, a0=0.0, cap_bottom=False, cap_top=False, repeat=None, uv_off=(0.0, 0.0),
          smooth=60.0, int_repeat=True, vscale=1.0, stretch=0.0):
    """Revolve [(r, z), ...] (bottom -> top) around Z. r == 0 at an end makes a pole. u goes round
    (an integer number of repeats, so no seam), v along the profile. stretch = a > 0 makes a
    stadium plan (two half rings joined by straight sides of length 2a along x)."""
    prof = [tuple(map(float, p)) for p in profile]
    rep = repeat if repeat is not None else sw.repeat
    rmax = max(p[0] for p in prof)
    if stretch > 0 and a0 == 0.0:
        a0 = math.pi / sides
    angs = [a0 + k * 2 * math.pi / sides for k in range(sides)]

    def ring_pt(a, r):
        x = math.cos(a) * r
        if stretch > 0:
            x += stretch if math.cos(a) >= 0 else -stretch
        return (x, math.sin(a) * r)

    ref = np.array([ring_pt(a, max(rmax, 1e-3)) for a in angs] + [ring_pt(angs[0], max(rmax, 1e-3))])
    seg = np.linalg.norm(np.diff(ref, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    circ = cum[-1]
    frac = cum / circ
    nrep = circ / rep
    if int_repeat and nrep >= 0.75:
        # whole repeats round the ring (no seam). Thin rings (poles, ropes, finials) keep their true
        # arc length instead (u = arc length / repeat: no 3-5x stretch, one seam on the +x side)
        nrep = max(1.0, round(nrep))
    verts, rings = [], []
    for r, z in prof:
        if r <= 1e-6 and stretch <= 0:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            idx = []
            for a in angs:
                idx.append(len(verts))
                x, y = ring_pt(a, max(r, 1e-4))
                verts.append((x, y, z))
            rings.append(idx)
    verts = np.array(verts, float)
    L = [0.0]
    for i in range(1, len(prof)):
        L.append(L[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))

    def uvk(k, i):
        kk = int(math.floor(k))
        f = frac[kk] + (frac[min(kk + 1, sides)] - frac[kk]) * (k - kk) if kk < sides else 1.0
        return (f * nrep + uv_off[0], -L[i] / rep * vscale + uv_off[1])

    tris, uvs = [], []
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            k1 = k + 1
            if len(r0) == 1:
                tris.append((r0[0], r1[k % sides], r1[k1 % sides]))
                uvs.append((uvk(k + 0.5, i), uvk(k, i + 1), uvk(k1, i + 1)))
            elif len(r1) == 1:
                tris.append((r0[k % sides], r0[k1 % sides], r1[0]))
                uvs.append((uvk(k, i), uvk(k1, i), uvk(k + 0.5, i + 1)))
            else:
                a, b = r0[k % sides], r0[k1 % sides]
                c, d = r1[k1 % sides], r1[k % sides]
                tris += [(a, b, c), (a, c, d)]
                uvs += [(uvk(k, i), uvk(k1, i), uvk(k1, i + 1)), (uvk(k, i), uvk(k1, i + 1), uvk(k, i + 1))]
    tris = list(tris)
    uvs = list(uvs)
    for flag, i, top in ((cap_bottom, 0, False), (cap_top, len(rings) - 1, True)):
        if not flag or len(rings[i]) == 1:
            continue
        ring = rings[i]
        z = prof[i][1]
        if stretch > 0:
            poly = verts[ring][:, :2]
            cv, ct = cap_tris(poly, z, None, up=top)
            base = len(verts)
            verts = np.vstack([verts, cv])
            for tri in ct:
                tri = tuple(int(t_) + base for t_ in tri)
                tris.append(tri)
                uvs.append(tuple((verts[j][0] / rep + uv_off[0], -verts[j][1] / rep + uv_off[1]) for j in tri))
            continue
        cen = len(verts)
        verts = np.vstack([verts, [[0.0, 0.0, z]]])
        for k in range(sides):
            a, b = ring[k], ring[(k + 1) % sides]
            tri = (cen, a, b) if top else (cen, b, a)
            tris.append(tri)
            uvs.append(tuple((verts[j][0] / rep + uv_off[0], -verts[j][1] / rep + uv_off[1]) for j in tri))
    return Part(verts, np.array(tris, np.int64), sw, np.array(uvs, float), smooth)


def sweep(profile, path, sw, scales=None, closed_path=False, cap0=True, cap1=True, repeat=None, uv_off=(0.0, 0.0),
          up=(0, 0, 1), smooth=50.0):
    """Sweep a closed 2D profile (K, 2, CCW) along a 3D polyline (S, 3). u along the path (grain),
    v around the profile."""
    prof = np.asarray(profile, float)
    path = np.asarray(path, float)
    S, K = len(path), len(prof)
    sc = np.ones((S, 2)) if scales is None else np.asarray(scales, float)
    if sc.ndim == 1:
        sc = np.stack([sc, sc], axis=1)
    rep = repeat if repeat is not None else sw.repeat
    T = np.zeros_like(path)
    if closed_path:
        T = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    else:
        T[1:-1] = path[2:] - path[:-2]
        T[0] = path[1] - path[0]
        T[-1] = path[-1] - path[-2]
    T = nrm(T)
    upv = np.asarray(up, float)
    frames = []
    for s in range(S):
        u = upv if abs(np.dot(T[s], nrm(upv))) < 0.97 else np.array([1.0, 0, 0])
        N = nrm(np.cross(u, T[s]))
        B = np.cross(T[s], N)
        frames.append((N, B))
    verts = np.zeros((S * K, 3))
    for s in range(S):
        Nn, Bb = frames[s]
        for k in range(K):
            px, py = prof[k] * sc[s]
            verts[s * K + k] = path[s] + Nn * px + Bb * py
    per = np.linalg.norm(np.roll(prof, -1, axis=0) - prof, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(per)]) * sc.mean()
    seg = np.linalg.norm(np.diff(np.vstack([path, path[:1]]) if closed_path else path, axis=0), axis=1)
    along = np.concatenate([[0.0], np.cumsum(seg)])
    tris, uvs = [], []
    nseg = S if closed_path else S - 1
    for s in range(nseg):
        s1 = (s + 1) % S
        for k in range(K):
            k1 = (k + 1) % K
            a, b, c, d = s * K + k, s * K + k1, s1 * K + k1, s1 * K + k
            ua, ub = along[s], along[s + 1]
            va, vb = cum[k], cum[k + 1]
            tris += [(a, b, c), (a, c, d)]
            uvs += [((ua, va), (ua, vb), (ub, vb)), ((ua, va), (ub, vb), (ub, va))]
    uvs = np.array(uvs, float)
    uvs[..., 1] *= -1
    uvs = uvs / rep + np.asarray(uv_off, float)
    tris = [tuple(x) for x in tris]
    uvs = list(uvs)
    verts = list(verts)
    if not closed_path:
        for end, flag in ((0, cap0), (S - 1, cap1)):
            if not flag:
                continue
            ring = [end * K + k for k in range(K)]
            cen = np.mean([verts[i] for i in ring], axis=0)
            ci = len(verts)
            verts.append(cen)
            Nn, Bb = frames[end]
            for k in range(K):
                a, b = ring[k], ring[(k + 1) % K]
                tri = (ci, b, a) if end == 0 else (ci, a, b)
                tris.append(tri)
                uvs.append(np.array([((verts[j] - cen) @ Nn / rep, -((verts[j] - cen) @ Bb) / rep) for j in tri]))
    return Part(np.array(verts), np.array(tris, np.int64), sw, np.array(uvs, float), smooth)


def circle(n, r=1.0, a0=0.0):
    a = a0 + np.arange(n) * 2 * math.pi / n
    return np.stack([np.cos(a) * r, np.sin(a) * r], axis=1)


def rect_profile(w, h, c=0.0):
    x, y = w / 2, h / 2
    if c <= 0:
        return np.array([(x, -y), (x, y), (-x, y), (-x, -y)], float)
    c = min(c, x * 0.45, y * 0.45)
    return np.array([(x, -y + c), (x, y - c), (x - c, y), (-x + c, y), (-x, y - c), (-x, -y + c),
                     (-x + c, -y), (x - c, -y)], float)


def torus(R, r, sw, segs=24, sides=8, a0=0.0, arc=360.0, repeat=None):
    """Ring around Z (full or an arc)."""
    closed = arc >= 359.9
    n = segs if closed else segs + 1
    ang = math.radians(a0) + np.arange(n) * math.radians(arc) / segs
    path = np.stack([np.cos(ang) * R, np.sin(ang) * R, np.zeros(n)], axis=1)
    return sweep(circle(sides, r), path, sw, closed_path=closed, repeat=repeat)


def quad(p0, p1, p2, p3, sw, uv=((0, 1), (1, 1), (1, 0), (0, 0)), segs=(1, 1)):
    """Single-sided bilinear patch p0 (bottom-left) p1 (bottom-right) p2 (top-right) p3 (top-left),
    front = CCW. Decal UVs by default."""
    P = [np.asarray(x, float) for x in (p0, p1, p2, p3)]
    U = [np.asarray(x, float) for x in uv]
    nu, nv = segs
    verts, uvv = [], []
    for j in range(nv + 1):
        b = j / nv
        for i in range(nu + 1):
            a = i / nu
            verts.append((1 - b) * ((1 - a) * P[0] + a * P[1]) + b * ((1 - a) * P[3] + a * P[2]))
            uvv.append((1 - b) * ((1 - a) * U[0] + a * U[1]) + b * ((1 - a) * U[3] + a * U[2]))
    verts, uvv = np.array(verts), np.array(uvv)
    tris = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            tris += [(a, a + 1, a + nu + 2), (a, a + nu + 2, a + nu + 1)]
    tris = np.array(tris, np.int64)
    return Part(verts, tris, sw, uvv[tris], 0.0)


def plate(p0, p1, p2, p3, th, sw, uv=None, segs=(1, 1), smooth=25.0):
    """Thick panel: front face p0..p3 (CCW seen from the front) extruded backwards by th."""
    P = [np.asarray(x, float) for x in (p0, p1, p2, p3)]
    n = nrm(np.cross(P[1] - P[0], P[3] - P[0]))
    back = [p - n * th for p in P]
    parts = [quad(*P, sw, uv=uv or ((0, 1), (1, 1), (1, 0), (0, 0)), segs=segs),
             quad(back[1], back[0], back[3], back[2], sw, uv=uv or ((0, 1), (1, 1), (1, 0), (0, 0)), segs=segs)]
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        parts.append(quad(P[b], P[a], back[a], back[b], sw, uv=((0, 0), (1, 0), (1, 0.05), (0, 0.05))))
    out = merge(parts)
    out.smooth = smooth
    return out


def merge(parts):
    """Concatenate parts (keeps the first part's settings and swatch)."""
    parts = [p for p in parts if p is not None]
    if len(parts) == 1:
        return parts[0]
    vs, ts, uvs, off = [], [], [], 0
    tints = []
    for p in parts:
        vs.append(p.v)
        ts.append(p.t + off)
        uvs.append(p.uv)
        tints.append(np.broadcast_to(np.asarray(p.tint, float), (len(p.v), 3)) if np.ndim(p.tint) == 1 else p.tint)
        off += len(p.v)
    q = parts[0].copy()
    q.v, q.t, q.uv = np.concatenate(vs), np.concatenate(ts), np.concatenate(uvs)
    q.tint = np.concatenate(tints)
    return q


def blob(sw, radius=1.0, subdiv=2, scale=(1, 1, 1), seed=0, noise_amp=0.15, noise_freq=1.2, cuts=0,
         cut_depth=0.18, flat_bottom=0.0, repeat=None, smooth=40.0):
    """Stone / mound: icosphere scaled, noise-displaced, chiselled by `cuts` planes; bottom on z=0."""
    v, t = icosphere(subdiv, radius)
    rng = np.random.default_rng(seed)
    v = v * np.asarray(scale, float)
    if noise_amp:
        off = (rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50))
        d = noise_scalar(v, noise_freq / max(radius, 1e-3), off)
        v = v + nrm(v) * (d * noise_amp * radius)[:, None]
    for _ in range(cuts):
        n = nrm(rng.normal(0, 1, 3) * np.array([1, 1, 0.5]))
        s = v @ n
        dcut = s.max() - cut_depth * radius * rng.uniform(0.6, 1.3)
        over = s > dcut
        v[over] -= np.outer(s[over] - dcut, n) * 0.92
    zmin = v[:, 2].min()
    if flat_bottom is not None:
        zb = zmin + (v[:, 2].max() - zmin) * flat_bottom
        v[:, 2] = np.maximum(v[:, 2], zb)
    v[:, 2] -= v[:, 2].min()
    p = Part(v, t, sw, smooth=smooth)
    return p.box_uv(repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))


# =============================================================================================
# tessellation (AO resolution) and jitter
# =============================================================================================

def refine(p: Part, maxlen: float, max_iter=8):
    """Conforming red-green refinement: split every edge longer than maxlen (shared midpoints, no
    T-junctions); per-corner UVs are interpolated."""
    v, t, uv = p.v, p.t, p.uv
    tint_pv = np.ndim(p.tint) == 2
    tint = p.tint
    for _ in range(max_iter):
        e = np.stack([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]], axis=1)  # (M, 3, 2)
        ek = np.sort(e, axis=2)
        L = np.linalg.norm(v[e[..., 0]] - v[e[..., 1]], axis=2)
        mark = L > maxlen
        if not mark.any():
            break
        keys = ek[mark]
        uniq, inv = np.unique(keys, axis=0, return_inverse=True)
        mids = (v[uniq[:, 0]] + v[uniq[:, 1]]) / 2
        base = len(v)
        v = np.vstack([v, mids])
        if tint_pv:
            tint = np.vstack([tint, (tint[uniq[:, 0]] + tint[uniq[:, 1]]) / 2])
        midx = np.full((len(t), 3), -1, np.int64)
        midx[mark] = base + inv.reshape(-1)
        nt, nuv = [], []
        for f in range(len(t)):
            m = midx[f]
            a, b, c = t[f]
            ua, ub, uc = uv[f]
            cnt = int((m >= 0).sum())
            if cnt == 0:
                nt.append((a, b, c))
                nuv.append((ua, ub, uc))
                continue
            # rotate so that the first marked edge is (0,1)
            verts3 = [a, b, c]
            uvs3 = [ua, ub, uc]
            mids3 = list(m)
            muv = [(uvs3[0] + uvs3[1]) / 2, (uvs3[1] + uvs3[2]) / 2, (uvs3[2] + uvs3[0]) / 2]
            if cnt == 3:
                m0, m1, m2 = mids3
                nt += [(verts3[0], m0, m2), (m0, verts3[1], m1), (m2, m1, verts3[2]), (m0, m1, m2)]
                nuv += [(uvs3[0], muv[0], muv[2]), (muv[0], uvs3[1], muv[1]), (muv[2], muv[1], uvs3[2]),
                        (muv[0], muv[1], muv[2])]
                continue
            # find rotation r so that edge r is marked (and for cnt==2, edge r+1 also marked)
            rr = 0
            for r in range(3):
                if cnt == 1 and mids3[r] >= 0:
                    rr = r
                    break
                if cnt == 2 and mids3[r] >= 0 and mids3[(r + 1) % 3] >= 0:
                    rr = r
                    break
            V = [verts3[(rr + i) % 3] for i in range(3)]
            U = [uvs3[(rr + i) % 3] for i in range(3)]
            Mi = [mids3[(rr + i) % 3] for i in range(3)]
            MU = [muv[(rr + i) % 3] for i in range(3)]
            if cnt == 1:
                nt += [(V[0], Mi[0], V[2]), (Mi[0], V[1], V[2])]
                nuv += [(U[0], MU[0], U[2]), (MU[0], U[1], U[2])]
            else:
                nt += [(Mi[0], V[1], Mi[1]), (V[0], Mi[0], Mi[1]), (V[0], Mi[1], V[2])]
                nuv += [(MU[0], U[1], MU[1]), (U[0], MU[0], MU[1]), (U[0], MU[1], U[2])]
        t = np.array(nt, np.int64)
        uv = np.array(nuv, float)
    p.v, p.t, p.uv = v, t, uv
    if tint_pv:
        p.tint = tint
    return p


def jitter(parts, seed, freq=1.3):
    rng = np.random.default_rng(seed)
    off = tuple(rng.uniform(0, 100, 3))
    for p in parts:
        amp = np.asarray(p.jit, float)
        if np.all(amp == 0):
            continue
        p.v = p.v + noise_vec(p.v, freq, off) * amp


# =============================================================================================
# baking: normals, AO, vertex colours, height
# =============================================================================================

def face_normals(v, t):
    p = v[t]
    return np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])


def corner_normals(v, t, angle_deg):
    fn = face_normals(v, t)
    fu = nrm(fn)
    M = len(t)
    if angle_deg <= 0.1:
        return np.repeat(fu[:, None, :], 3, axis=1)
    corners = t.reshape(-1)
    face_of = np.repeat(np.arange(M), 3)
    if angle_deg >= 179.0:
        vn = np.zeros_like(v)
        np.add.at(vn, corners, fn[face_of])
        return nrm(vn)[t]
    cos_t = math.cos(math.radians(angle_deg))
    order = np.argsort(corners, kind="stable")
    cs = corners[order]
    bounds = np.flatnonzero(np.diff(cs)) + 1
    starts = np.concatenate([[0], bounds])
    ends = np.concatenate([bounds, [len(cs)]])
    out = np.zeros((M * 3, 3))
    for s0, s1 in zip(starts, ends):
        idx = order[s0:s1]
        fs = face_of[idx]
        if len(idx) == 1:
            out[idx] = fu[fs]
            continue
        d = fu[fs] @ fu[fs].T
        w = (d >= cos_t).astype(float)
        out[idx] = w @ fn[fs]
    return nrm(out).reshape(M, 3, 3)


def vertex_normals(v, t):
    vn = np.zeros_like(v)
    np.add.at(vn, t.reshape(-1), np.repeat(face_normals(v, t), 3, axis=0))
    return nrm(vn)


def _hemi(k=24):
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(k):
        u = (i + 0.5) / k
        r = math.sqrt(u)
        a = i * ga
        out.append((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - u))))
    return np.array(out)


HEMI = _hemi(24)


class Bake:
    def __init__(self, ao_dist=1.1, ao_strength=1.0, base_dark=0.62, base_h=0.45, top_light=0.10, ground=True):
        self.ao_dist = ao_dist
        self.ao_strength = ao_strength
        self.base_dark = base_dark
        self.base_h = base_h
        self.top_light = top_light
        self.ground = ground


def bake(parts, H, cfg: Bake):
    vs, ts, off = [], [], 0
    for p in parts:
        if p.occ:
            vs.append(p.v)
            ts.append(p.t + off)
            off += len(p.v)
    V = np.concatenate(vs)
    T = np.concatenate(ts)
    bvh = BVHTree.FromPolygons([tuple(x) for x in V], [tuple(int(i) for i in x) for x in T],
                               all_triangles=True, epsilon=0.0)
    maxd = cfg.ao_dist
    nh = len(HEMI)
    for p in parts:
        n = len(p.v)
        p.cn = corner_normals(p.v, p.t, p.smooth)
        if p.ao:
            vn = vertex_normals(p.v, p.t)
            ao = np.ones(n)
            for i in range(n):
                o = p.v[i]
                F = frame_from_z(vn[i])
                org = Vector(o + vn[i] * 0.01)
                occ = 0.0
                for d in HEMI:
                    dw = F @ d
                    hit = bvh.ray_cast(org, Vector(dw), maxd)
                    h = 0.0
                    if hit[0] is not None:
                        h = 1.0 - (hit[3] / maxd) ** 2
                    elif cfg.ground and dw[2] < -1e-3:
                        tg = -(o[2] + 0.002) / dw[2]
                        if 0 < tg < maxd:
                            h = 0.85 * (1.0 - (tg / maxd) ** 2)
                    occ += h
                ao[i] = 1.0 - cfg.ao_strength * p.ao_mul * occ / nh
            ao = np.clip(ao, 0.15, 1.0)
            ao = 0.30 + 0.70 * np.power(ao, 1.3)
        else:
            ao = np.ones(n)
        z = p.v[:, 2]
        base = lerp(cfg.base_dark, 1.0, smoothstep(0.0, cfg.base_h, z)) if p.base else np.ones(n)
        top = 1.0 - cfg.top_light + cfg.top_light * np.clip(z / H, 0, 1)
        zr = max(z.max() - z.min(), 1e-6)
        form = 1.0 - p.form + 2 * p.form * np.clip((z - z.min()) / zr, 0, 1) * 0.5 if p.form else np.ones(n)
        shade = np.maximum(ao * base * top * form, p.min_shade)
        tint = np.broadcast_to(np.asarray(p.tint, float), (n, 3))
        p.col = np.concatenate([np.clip(tint * shade[:, None], 0, 1), np.ones((n, 1))], axis=1)
        p.hn = np.clip(z / H, 0.0, 1.0)


# =============================================================================================
# atlas mapping (cut tile triangles on integer UV lines) and export
# =============================================================================================

def _clip(poly, k, val, keep_ge):
    """Sutherland-Hodgman against attribute k >= val (keep_ge) or <= val. poly: list of arrays."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ina = a[k] >= val - 1e-9 if keep_ge else a[k] <= val + 1e-9
        inb = b[k] >= val - 1e-9 if keep_ge else b[k] <= val + 1e-9
        if ina:
            out.append(a)
        if ina != inb:
            t = (val - a[k]) / (b[k] - a[k])
            out.append(a + (b - a) * t)
    return out


def cut_tiles(A):
    """A: (M, 3, K) per-corner attributes with uv in [..., 0:2]. Returns (M', 3, K) with every
    triangle inside one integer UV cell and the uv reduced to [0, 1]."""
    if len(A) == 0:
        return A
    u, v = A[..., 0], A[..., 1]
    eps = 1e-6
    u0, u1 = np.floor(u.min(1) + eps), np.floor(u.max(1) - eps)
    v0, v1 = np.floor(v.min(1) + eps), np.floor(v.max(1) - eps)
    simple = (u0 == u1) & (v0 == v1)
    out = [A[simple].copy()]
    out[0][..., 0] -= u0[simple][:, None]
    out[0][..., 1] -= v0[simple][:, None]
    rest = np.flatnonzero(~simple)
    pieces = []
    for f in rest:
        tri = [A[f, 0], A[f, 1], A[f, 2]]
        for iu in range(int(u0[f]), int(u1[f]) + 1):
            pu = _clip(_clip(tri, 0, iu, True), 0, iu + 1, False)
            if len(pu) < 3:
                continue
            for iv in range(int(v0[f]), int(v1[f]) + 1):
                pv = _clip(_clip(pu, 1, iv, True), 1, iv + 1, False)
                if len(pv) < 3:
                    continue
                for j in range(1, len(pv) - 1):
                    t3 = np.stack([pv[0], pv[j], pv[j + 1]])
                    pa = np.linalg.norm(np.cross(t3[1, 2:5] - t3[0, 2:5], t3[2, 2:5] - t3[0, 2:5]))
                    if pa < 1e-10:
                        continue
                    t3 = t3.copy()
                    t3[:, 0] -= iu
                    t3[:, 1] -= iv
                    pieces.append(t3)
    if pieces:
        out.append(np.stack(pieces))
    R = np.concatenate(out)
    R[..., 0:2] = np.clip(R[..., 0:2], 0.0, 1.0)
    return R


def _to_gltf(a):
    a = np.asarray(a, float)
    return np.stack([a[..., 0], a[..., 2], -a[..., 1]], axis=-1)


def encode(im, mode="jpeg", quality=88):
    buf = io.BytesIO()
    if mode == "png":
        im.save(buf, "PNG", optimize=False, compress_level=9)
        return buf.getvalue(), "image/png"
    im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=False, progressive=False, subsampling=0)
    return buf.getvalue(), "image/jpeg"


def _uv_extent(A):
    """Area-weighted metres per unit u and per unit v of a corner-attribute array (uv 0:2, pos 2:5)."""
    U = A[..., 0:2]
    P = A[..., 2:5]
    E = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]], axis=2)          # (M, 3, 2)
    D = np.stack([U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]], axis=2)          # (M, 2, 2)
    det = D[:, 0, 0] * D[:, 1, 1] - D[:, 0, 1] * D[:, 1, 0]
    ok = np.abs(det) > 1e-9
    if not ok.any():
        return 1.0, 1.0
    Dinv = np.zeros_like(D)
    Dinv[ok, 0, 0] = D[ok, 1, 1] / det[ok]
    Dinv[ok, 1, 1] = D[ok, 0, 0] / det[ok]
    Dinv[ok, 0, 1] = -D[ok, 0, 1] / det[ok]
    Dinv[ok, 1, 0] = -D[ok, 1, 0] / det[ok]
    J = E @ Dinv                                                          # (M, 3, 2): dP/du, dP/dv
    area = np.linalg.norm(np.cross(E[..., 0], E[..., 1]), axis=1) * ok
    w = area / max(area.sum(), 1e-12)
    return float((np.linalg.norm(J[..., 0], axis=1) * w).sum()), float((np.linalg.norm(J[..., 1], axis=1) * w).sum())


PIPING_M = 0.045     # neutral piping width round every TEAM area (bible 3.1 rule 4)


def split_team_border(A, sw, width=PIPING_M):
    """Cut the outer band of a TEAM part's UV field (decals: all four edges; tiled bands: the two long
    edges, v = 0 and v = 1) out of the TEAM faces. The band is `width` m wide (at most 12 % of the
    field). Returns (inner, border) corner arrays; the caller re-maps the border to the faction's
    neutral piping colour in the atlas. Each triangle is peeled sequentially (left, right, bottom, top
    strip), so it yields at most five polygons."""
    if len(A) == 0:
        return A, A[:0]
    mu, mv = _uv_extent(A)
    bu = 0.0 if sw.kind == "tile" else min(0.12, width / max(mu, 1e-6))
    bv = min(0.12, width / max(mv, 1e-6))
    cuts = []
    if bu > 1e-4:
        cuts += [(0, bu, False), (0, 1.0 - bu, True)]
    if bv > 1e-4:
        cuts += [(1, bv, False), (1, 1.0 - bv, True)]
    if not cuts:
        return A, A[:0]
    lo_u, hi_u = A[..., 0].min(1), A[..., 0].max(1)
    lo_v, hi_v = A[..., 1].min(1), A[..., 1].max(1)
    touch = (lo_v < bv) | (hi_v > 1.0 - bv)
    if bu > 1e-4:
        touch |= (lo_u < bu) | (hi_u > 1.0 - bu)
    inner = [A[~touch]]
    border = []

    def fan(poly, out):
        for j in range(1, len(poly) - 1):
            t3 = np.stack([poly[0], poly[j], poly[j + 1]])
            if np.linalg.norm(np.cross(t3[1, 2:5] - t3[0, 2:5], t3[2, 2:5] - t3[0, 2:5])) > 1e-10:
                out.append(t3[None])

    for f in np.flatnonzero(touch):
        rest = [A[f, 0], A[f, 1], A[f, 2]]
        for k, val, upper in cuts:
            strip = _clip(rest, k, val, keep_ge=upper)        # the band side of this line
            rest = _clip(rest, k, val, keep_ge=not upper)
            if len(strip) >= 3:
                fan(strip, border)
            if len(rest) < 3:
                break
        if len(rest) >= 3:
            fan(rest, inner)
    inner = np.concatenate([x for x in inner if len(x)]) if any(len(x) for x in inner) else A[:0]
    border = np.concatenate(border) if border else A[:0]
    return inner, border


# GLOW first: Godot's glTF importer (4.7) does not set vertex_color_use_as_albedo on the FIRST primitive
# of a mesh (it does on the following ones), and windows / embers must not be darkened anyway. When a
# building has no GLOW part a 1 mm dummy triangle hidden at the origin takes the first slot.
GROUP_ORDER = ("glow", "atlas", "team")
GLOW_DAY = (0.0, 0.0, 0.0)           # emissiveFactor shipped in the GLB (day: off); the game raises it at dusk
GLOW_NIGHT = (1.6, 0.95, 0.4)        # suggested night emissive factor (after 17:45, bible 1.5)


def export_glb(path, aid, parts, H, cfg: Bake, sheets, extras=None, glow_factor=GLOW_DAY, piping=None):
    """Bake and write one GLB whose materials reference the shared sheets (external images).
    sheets: {"atlas": Sheet, "team": Sheet, "glow": Sheet}. piping: (pal_swatch, (u, v)) = the atlas
    palette swatch and the UV of the neutral piping colour (TEAM borders are re-mapped there)."""
    bake(parts, H, cfg)
    routed = {g: [] for g in GROUP_ORDER}
    stats = {"materials": [], "team_piping_tris": 0}
    for p in parts:
        M = len(p.t)
        uv = p.uv[..., ::-1].copy() if p.uvrot else p.uv.copy()
        A = np.concatenate([uv, p.v[p.t], p.cn, p.col[p.t], np.stack([np.full((M, 3), p.layer), p.hn[p.t]], -1)],
                           axis=2)
        g = p.sw.group
        if g == "team" and piping is not None:
            inner, border = split_team_border(A, p.sw)
            if len(inner):
                routed["team"].append((p.sw, inner, False))
            if len(border):
                border = border.copy()
                border[..., 0] = piping[1][0]
                border[..., 1] = piping[1][1]
                routed["atlas"].append((piping[0], border, False))
                stats["team_piping_tris"] += len(border)
        else:
            routed[g].append((p.sw, A, p.faceted))
    mats, prims = [], []
    dummy = not routed["glow"]
    for g in GROUP_ORDER:
        sel = routed[g]
        if not sel:
            continue
        sh = sheets[g]
        W, Hh = sh.size
        sws = []
        pos, nor, uv0, uv1, col = [], [], [], [], []
        for sw, A, fac in sel:
            if sw.sheet_key not in sws:
                sws.append(sw.sheet_key)
            A = A.copy()
            if sw.kind == "tile":
                # parts (or, for faceted parts, each face direction) smaller than one repeat: shift their
                # UVs inside a single cell, so they need no cuts
                if fac:
                    fn = face_normals(A[:, :, 2:5].reshape(-1, 3), np.arange(len(A) * 3).reshape(-1, 3))
                    grp = np.argmax(np.abs(fn), axis=1) * 2 + (fn[np.arange(len(fn)), np.argmax(np.abs(fn), axis=1)] > 0)
                    groups = [np.flatnonzero(grp == gi) for gi in range(6)]
                else:
                    groups = [np.arange(len(A))]
                for idx in groups:
                    if len(idx) == 0:
                        continue
                    for ax in (0, 1):
                        lo_, hi_ = A[idx, :, ax].min(), A[idx, :, ax].max()
                        if hi_ - lo_ < 0.999:
                            frac = (seed_of(len(idx), round(float(lo_), 4), ax) % 1000) / 1000.0
                            A[idx, :, ax] += np.floor(lo_) + frac * (0.999 - (hi_ - lo_)) - lo_ + 0.0005
                n_in = len(A)
                A = cut_tiles(A)
                stats.setdefault("cut_by_swatch", {}).setdefault(sw.key, [0, 0])
                stats["cut_by_swatch"][sw.key][0] += n_in
                stats["cut_by_swatch"][sw.key][1] += len(A)
            else:
                A[..., 0:2] = np.clip(A[..., 0:2], 0, 1)
            x0, y0, inner = sh.rects[sw.sheet_key]
            uvA = np.stack([(x0 + A[..., 0] * inner) / W, (y0 + A[..., 1] * inner) / Hh], -1)
            pos.append(A[..., 2:5].reshape(-1, 3))
            nor.append(A[..., 5:8].reshape(-1, 3))
            col.append(A[..., 8:12].reshape(-1, 4))
            uv1.append(A[..., 12:14].reshape(-1, 2))
            uv0.append(uvA.reshape(-1, 2))
        name = aid if g == "atlas" else f"{aid}_{g.upper()}"
        mats.append({"name": name, "sheet": sh, "group": g, "swatches": sws})
        if dummy and g == "atlas":
            # hidden first primitive (see GROUP_ORDER): one 1 mm triangle inside the base
            dp = np.array([[0.0, 0.0, 0.02], [0.001, 0.0, 0.02], [0.0, 0.001, 0.02]])
            prims.append((len(mats) - 1, dp, np.tile([0.0, 0.0, 1.0], (3, 1)), np.tile(uv0[0][:1], (3, 1)),
                          np.zeros((3, 2)), np.ones((3, 4))))
        prims.append((len(mats) - 1, np.concatenate(pos), np.concatenate(nor), np.concatenate(uv0),
                      np.concatenate(uv1), np.concatenate(col)))
    tris = _write_glb(path, aid, prims, mats, extras or {}, glow_factor)
    stats["materials"] = [{"name": m["name"], "texture": m["sheet"].uri, "texture_px": list(m["sheet"].size),
                           "swatches": m["swatches"]} for m in mats]
    stats["tris"] = tris
    return stats


def _write_glb(path, aid, prims, mats, extras, glow_factor):
    bin_chunks = bytearray()
    buffer_views, accessors = [], []

    def add_view(data, target=None):
        while len(bin_chunks) % 4:
            bin_chunks.append(0)
        off = len(bin_chunks)
        bin_chunks.extend(data)
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            bv["target"] = target
        buffer_views.append(bv)
        return len(buffer_views) - 1

    def add_acc(arr, comp, typ, target, minmax=False):
        arr = np.ascontiguousarray(arr)
        view = add_view(arr.tobytes(), target)
        acc = {"bufferView": view, "componentType": comp, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            acc["min"] = [float(x) for x in arr.min(axis=0)]
            acc["max"] = [float(x) for x in arr.max(axis=0)]
        accessors.append(acc)
        return len(accessors) - 1

    gl_images, textures, materials = [], [], []
    tex_of = {}
    for m in mats:
        sh = m["sheet"]
        if sh.uri not in tex_of:
            gl_images.append({"uri": sh.uri, "mimeType": sh.mime, "name": sh.name})
            textures.append({"sampler": 0, "source": len(gl_images) - 1})
            tex_of[sh.uri] = len(textures) - 1
        m["image"] = tex_of[sh.uri]
    for m in mats:
        md = {"name": m["name"],
              "pbrMetallicRoughness": {"baseColorTexture": {"index": m["image"]}, "metallicFactor": 0.0,
                                       "roughnessFactor": 1.0}}
        ex = {"vc_vertex_color": "multiply",
              "vertex_color": "RGB = painted AO and tint (multiplies albedo), A = 1",
              "uv2": "x = build layer (0 structure, 1 covering), y = normalized height (0 ground, 1 top)",
              "swatches": m["swatches"]}
        if m["group"] == "glow":
            md["emissiveTexture"] = {"index": m["image"]}
            md["emissiveFactor"] = [float(x) for x in glow_factor]
            ex["role"] = ("GLOW: windows / embers. Shipped dark (emissiveFactor 0: windows do not glow at noon); "
                          f"raise emission to emissive_night {list(GLOW_NIGHT)} at 17:45 and back to 0 after 06:30 "
                          "(bible 1.5)")
            ex["emissive_day"] = [float(x) for x in glow_factor]
            ex["emissive_night"] = list(GLOW_NIGHT)
        if m["group"] == "team":
            ex["role"] = ("TEAM: light grey cloth (no piping: the neutral piping is in the atlas); UnitView "
                          "multiplies albedo_color by the player colour")
        md["extras"] = ex
        materials.append(md)
    prims_out = []
    total_tris = 0
    for (mi, pos, nor, uv0, uv1, col) in prims:
        P = _to_gltf(pos).astype(np.float32)
        N = _to_gltf(nrm(nor)).astype(np.float32)
        rows = np.concatenate([P, N, uv0.astype(np.float32), uv1.astype(np.float32), col.astype(np.float32)], axis=1)
        rows = np.round(rows, 6).astype(np.float32)
        # canonical order (byte-identical output whatever order the parts' triangles came in):
        # vertices sorted (np.unique), each triangle rotated to start at its smallest index, then
        # triangles sorted
        uniq, inv = np.unique(rows, axis=0, return_inverse=True)
        idx = inv.reshape(-1)
        tri = idx.reshape(-1, 3)
        ok = (tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])
        tri = tri[ok]
        rot = np.argmin(tri, axis=1)
        tri = np.stack([tri[np.arange(len(tri)), (rot + k) % 3] for k in range(3)], axis=1)
        tri = np.unique(tri, axis=0)
        total_tris += len(tri)
        P, N, U0, U1, C = uniq[:, 0:3], uniq[:, 3:6], uniq[:, 6:8], uniq[:, 8:10], uniq[:, 10:14]
        N = nrm(N).astype(np.float32)
        attrs = {
            "POSITION": add_acc(P.astype(np.float32), 5126, "VEC3", 34962, minmax=True),
            "NORMAL": add_acc(N, 5126, "VEC3", 34962),
            "TEXCOORD_0": add_acc(U0.astype(np.float32), 5126, "VEC2", 34962),
            "TEXCOORD_1": add_acc(U1.astype(np.float32), 5126, "VEC2", 34962),
            "COLOR_0": add_acc(C.astype(np.float32), 5126, "VEC4", 34962),
        }
        ind_arr = tri.reshape(-1)
        if len(uniq) < 65535:
            ind = add_acc(ind_arr.astype(np.uint16), 5123, "SCALAR", 34963)
        else:
            ind = add_acc(ind_arr.astype(np.uint32), 5125, "SCALAR", 34963)
        prims_out.append({"attributes": attrs, "indices": ind, "material": int(mi), "mode": 4})
    node = {"name": aid, "mesh": 0}
    if extras:
        node["extras"] = extras
    gltf = {
        "asset": {"version": "2.0", "generator": "Vibecraft tools/kits/buildings.py"},
        "scene": 0,
        "scenes": [{"name": aid, "nodes": [0]}],
        "nodes": [node],
        "meshes": [{"name": aid, "primitives": prims_out}],
        "materials": materials,
        "textures": textures,
        "images": gl_images,
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_chunks)}],
    }
    js = json.dumps(gltf, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    while len(js) % 4:
        js += b" "
    while len(bin_chunks) % 4:
        bin_chunks.append(0)
    total = 12 + 8 + len(js) + 8 + len(bin_chunks)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(bin_chunks), 0x004E4942))
        f.write(bytes(bin_chunks))
    return total_tris
