"""Core of the procedural Greenvale doodad kit (used by tools/kits/doodads.py).

Everything here is deterministic: geometry comes from seeded `random.Random` / numpy generators and
mathutils noise, textures are painted procedurally with numpy/Pillow (or derived from the repo's
painted swatches), and the GLB writer below emits byte-identical files for identical inputs.

Build space is Blender-like: metres, **Z up, the model's front faces +Y**. The writer converts to
glTF/Godot space with (x, y, z) -> (x, z, -y), so the front ends up facing **-Z** (Godot forward).

Vertex data written per vertex (see docs in doodads.py / the manifest):
  COLOR_0     standard materials: RGB = painted AO + tint (multiplies albedo, glTF semantics), A = 1
              SWAY materials (name contains "SWAY"): R = sway weight (0 at the trunk base -> 1 at the
              canopy edge), G = painted AO (multiply into albedo in the sway shader), B = phase (0..1,
              per leaf cluster, to de-synchronise gusts), A = 1
  TEXCOORD_1  (UV2) x = sway weight (0 for rigid props), y = normalized height (0 at ground, 1 at the
              top of the asset) for build/collapse reveals and height gradients
"""
from __future__ import annotations

import io
import json
import math
import os
import random
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import bmesh  # noqa: F401  (needs bpy, imported by the caller)
import mathutils
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import texture_tools as TT  # noqa: E402

Image.MAX_IMAGE_PIXELS = 300_000_000


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# =============================================================================================
# small math helpers
# =============================================================================================

def nrm(a, axis=-1):
    a = np.asarray(a, float)
    n = np.linalg.norm(a, axis=axis, keepdims=True)
    return a / np.maximum(n, 1e-12)


def smoothstep(e0, e1, x):
    """Hermite step; e0 > e1 gives the falling step (1 below e1 -> 0 above e0)."""
    d = e1 - e0
    if abs(d) < 1e-9:
        d = 1e-9
    t = np.clip((np.asarray(x, float) - e0) / d, 0.0, 1.0)
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


def noise3(p, scale=1.0, offset=(0.0, 0.0, 0.0)):
    """Smooth vector noise in [-1, 1]^3 per point (mathutils Perlin). noise_vector() samples at
    offsets drawn from mathutils' per-process random state, so reseed first (deterministic output)."""
    mathutils.noise.seed_set(1)       # NB: 0 would mean "seed from the clock"
    out = np.empty((len(p), 3))
    ox, oy, oz = offset
    for i, q in enumerate(p):
        v = mathutils.noise.noise_vector(Vector((q[0] * scale + ox, q[1] * scale + oy, q[2] * scale + oz)),
                                         noise_basis="PERLIN_ORIGINAL")
        out[i] = v[:]
    return out


def noise1(p, scale=1.0, offset=(0.0, 0.0, 0.0)):
    out = np.empty(len(p))
    ox, oy, oz = offset
    for i, q in enumerate(p):
        out[i] = mathutils.noise.noise(Vector((q[0] * scale + ox, q[1] * scale + oy, q[2] * scale + oz)),
                                       noise_basis="PERLIN_ORIGINAL")
    return out


# =============================================================================================
# materials and textures
# =============================================================================================

class Mat:
    """A material slot of the kit. `image` is a callable returning a PIL image (cached per run)."""

    def __init__(self, key, image, repeat=2.0, size=512, alpha=False, cutoff=0.5, double=False,
                 sway=False, emissive=False, emissive_factor=(1.0, 1.0, 1.0), roughness=1.0, tag="",
                 base_factor=(1.0, 1.0, 1.0), emissive_image=None):
        self.key = key
        self.image = image
        self.repeat = repeat          # metres per texture repeat (box / cylinder projection)
        self.size = size              # embedded texture size in px
        self.alpha = alpha            # alpha scissor (glTF MASK)
        self.cutoff = cutoff
        self.double = double
        self.sway = sway
        self.emissive = emissive
        self.emissive_factor = emissive_factor
        self.roughness = roughness
        self.tag = tag                # name suffix: SWAY, GLOW, LAMP, WATER ...
        self.base_factor = base_factor
        self.emissive_image = emissive_image   # optional separate emissive texture (callable -> PIL)

    def gltf_name(self, asset_id):
        tags = []
        if self.sway:
            tags.append("SWAY")
        if self.tag:
            tags.append(self.tag)
        return "_".join([asset_id, self.key] + tags)

    def px_per_m(self):
        return self.size / self.repeat


_IMG_CACHE: dict = {}
_ENC_CACHE: dict = {}


def cached_image(key, fn):
    if key not in _IMG_CACHE:
        _IMG_CACHE[key] = fn()
    return _IMG_CACHE[key]


def load_rgb(path):
    im = Image.open(os.path.join(REPO, path))
    im.load()
    return im


def make_seamless(im, blend=0.125, flatten="auto"):
    """texture_tools.py `seamless` (crossfade + optional lighting flatten), in memory."""
    mode = "RGBA" if im.mode == "RGBA" else "RGB"
    arr = TT.to_float(im.convert(mode))
    H, W = arr.shape[:2]
    if flatten == "auto":
        flat = 1.0 if TT.lowfreq_unevenness(arr) > 0.08 else 0.0
    else:
        flat = float(flatten)
    if flat > 0:
        arr = TT.flatten_lighting(arr, flat)
    bx = max(2, int(round(W * blend)))
    by = max(2, int(round(H * blend)))
    arr = TT.crossfade_x(arr, bx, wrap_other=False)
    arr = np.swapaxes(TT.crossfade_x(np.swapaxes(arr, 0, 1), by, wrap_other=True), 0, 1)
    out = TT.from_float(arr, mode)
    p = 8
    arr_p = np.pad(np.asarray(out), [(p, p), (p, p)] + ([(0, 0)] if arr.ndim == 3 else []), mode="wrap")
    big = Image.fromarray(arr_p, mode)
    sx, sy = W / out.width, H / out.height
    big = big.resize((round(big.width * sx), round(big.height * sy)), Image.LANCZOS)
    ox, oy = round(p * sx), round(p * sy)
    return big.crop((ox, oy, ox + W, oy + H))


def swatch(path, seamless=True, tint=None, sat=None, gamma=None, blend=0.125):
    """Load a painted swatch (optionally made seamless in memory, tinted / desaturated)."""
    def fn():
        im = load_rgb(path).convert("RGB")
        if seamless:
            im = make_seamless(im, blend=blend)
        a = np.asarray(im, np.float32) / 255.0
        if sat is not None:
            lum = a.mean(axis=2, keepdims=True)
            a = lum + (a - lum) * sat
        if tint is not None:
            a = a * np.asarray(tint, np.float32)
        if gamma is not None:
            a = np.power(np.clip(a, 0, 1), gamma)
        return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    return lambda: cached_image(("swatch", path, seamless, tuple(tint) if tint is not None else None, sat,
                                 gamma, blend), fn)


def encode_image(mat: Mat):
    """PNG (alpha) or JPEG bytes of a material's texture at its size; cached."""
    im = mat.image()                      # cached for the whole run, so id() is stable and unique
    key = (id(im), mat.size, mat.alpha)
    if key in _ENC_CACHE:
        return _ENC_CACHE[key]
    if im.size != (mat.size, mat.size):
        im = im.resize((mat.size, mat.size), Image.LANCZOS)
    buf = io.BytesIO()
    if mat.alpha or im.mode == "RGBA":
        im = im.convert("RGBA")
        im.save(buf, "PNG", optimize=False, compress_level=9)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=88, optimize=False, progressive=False, subsampling=0)
        mime = "image/jpeg"
    _ENC_CACHE[key] = (buf.getvalue(), mime)
    return _ENC_CACHE[key]


# ---------------------------------------------------------------------------- procedural paint

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


def to_img(a, mode="RGB"):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode)


def dilate_rgb(im: Image.Image, iterations=12):
    """Pad colour into fully transparent pixels (prevents dark/magenta fringes when mip-mapped)."""
    a = np.asarray(im.convert("RGBA"), np.float32) / 255.0
    rgb, al = a[..., :3].copy(), a[..., 3]
    known = al > 0.02
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(al.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sh_k = np.roll(np.roll(known, dy, 0), dx, 1)
            sh_c = np.roll(np.roll(rgb, dy, 0), dx, 1)
            acc += sh_c * sh_k[..., None]
            cnt += sh_k
        grow = (~known) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    if not known.all():
        mean = rgb[known].mean(axis=0) if known.any() else np.array([0.3, 0.4, 0.2])
        rgb[~known] = mean
    out = np.concatenate([rgb, al[..., None]], axis=2)
    return to_img(out, "RGBA")


def foliage_atlas(path, hue_tint=None, sat=1.0, val=1.0, blossom=None, seed=1, size=1024):
    """Leaf-clump atlas (2x2 clumps) from the painted foliage cards, recoloured, optional
    blossom specks (list of hex colours), colour padded into the transparent area."""
    def fn():
        im = load_rgb(path).convert("RGBA")
        if im.size != (size, size):
            im = im.resize((size, size), Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        rgb, al = a[..., :3], a[..., 3:]
        lum = rgb.mean(axis=2, keepdims=True)
        rgb = lum + (rgb - lum) * sat
        if hue_tint is not None:
            rgb = rgb * np.asarray(hue_tint, np.float32)
        rgb = rgb * val
        if blossom:
            rng = np.random.default_rng(seed)
            H, W = al.shape[:2]
            layer = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            alpha_np = al[..., 0]
            n = int(W * H / 900)
            for _ in range(n):
                x, y = rng.integers(8, W - 8), rng.integers(8, H - 8)
                if alpha_np[y, x] < 0.95:
                    continue
                # only on the lighter, outer leaves
                if lum[y, x, 0] < 0.28:
                    continue
                col = blossom[rng.integers(0, len(blossom))]
                c = tuple(int(v * 255) for v in hexcol(col)) + (255,)
                r = rng.uniform(2.2, 3.6) * 2
                for k in range(5):
                    ang = k * 1.2566 + rng.uniform(0, 1.2)
                    px, py = 2 * x + math.cos(ang) * r * 0.9, 2 * y + math.sin(ang) * r * 0.9
                    d.ellipse([px - r * 0.7, py - r * 0.7, px + r * 0.7, py + r * 0.7], fill=c)
                d.ellipse([2 * x - r * 0.45, 2 * y - r * 0.45, 2 * x + r * 0.45, 2 * y + r * 0.45],
                          fill=(232, 206, 110, 255))
            layer = layer.resize((W, H), Image.LANCZOS)
            la = np.asarray(layer, np.float32) / 255.0
            m = la[..., 3:] * al
            rgb = rgb * (1 - m) + la[..., :3] * m
        out = np.concatenate([np.clip(rgb, 0, 1), al], axis=2)
        return dilate_rgb(to_img(out, "RGBA"), 24)
    return lambda: cached_image(("foliage", path, tuple(hue_tint) if hue_tint is not None else None, sat, val,
                                 tuple(blossom) if blossom else None, seed, size), fn)


def _paint_strokes(W, H, strokes, ss=2):
    """strokes: list of (points [(x,y)...], width, rgba). Drawn wrapped (tileable) at ss x."""
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for pts, width, col in strokes:
        for ox in (-W, 0, W):
            for oy in (-H, 0, H):
                q = [((x + ox) * ss, (y + oy) * ss) for x, y in pts]
                d.line(q, fill=col, width=max(1, int(width * ss)), joint="curve")
    return im.resize((W, H), Image.LANCZOS)


def tex_straw(seed=11, n=512):
    """Golden straw: dense vertical strands, painted highlights, darker gaps. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        base = hexcol("#B8954A")
        bg = np.ones((n, n, 3)) * base * 0.62
        noise = periodic_noise(n, seed + 1, 2.6)[..., None]
        bg *= 0.85 + 0.3 * noise
        im = to_img(bg).convert("RGBA")
        cols = ["#E6CC7A", "#D8B460", "#C9A85A", "#A8843E", "#EED98E", "#8E6E30", "#F2E2A2"]
        strokes = []
        for _ in range(1500):
            x = rng.uniform(0, n)
            y = rng.uniform(0, n)
            L = rng.uniform(40, 160)
            ang = rng.normal(0, 0.06)
            pts = [(x, y), (x + math.sin(ang) * L * 0.5 + rng.normal(0, 1.5), y + L * 0.5),
                   (x + math.sin(ang) * L, y + L)]
            c = hexcol(cols[rng.integers(0, len(cols))])
            strokes.append((pts, rng.uniform(1.4, 3.2), tuple(int(v * 255) for v in c) + (int(rng.uniform(170, 255)),)))
        layer = _paint_strokes(n, n, strokes)
        im.alpha_composite(layer)
        a = np.asarray(im.convert("RGB"), np.float32) / 255.0
        # soft horizontal banding (bundles) and a little vertical light streak
        band = periodic_noise(n, seed + 2, 3.0)
        a *= (0.9 + 0.2 * band)[..., None]
        return to_img(a)
    return lambda: cached_image(("straw", seed, n), fn)


def tex_rings(seed=5, n=256):
    """End-grain disc: pale rings #E9CF9B, darker growth lines, radial cracks, bark rim.
    Mapped with planar UVs: the disc fills the square (centre 0.5, 0.5, radius 0.5)."""
    def fn():
        rng = np.random.default_rng(seed)
        y, x = np.mgrid[0:n, 0:n] + 0.5
        cx = cy = n / 2
        dx, dy = (x - cx) / (n / 2), (y - cy) / (n / 2)
        r = np.sqrt(dx * dx + dy * dy)
        th = np.arctan2(dy, dx)
        wob = 0.025 * np.sin(th * 3 + 1.3) + 0.018 * np.sin(th * 5 + 0.4)
        rr = r + wob * r
        pale = hexcol("#E9CF9B")
        mid = hexcol("#D2AF72")
        dark = hexcol("#9A7442")
        rings = 0.5 + 0.5 * np.cos(rr * 2 * math.pi * 7.5)
        rings = np.power(rings, 6)
        col = pale[None, None, :] * (1 - r[..., None] * 0.25) + (mid - pale)[None, None, :] * 0.3 * r[..., None]
        col = col * (1 - rings[..., None] * 0.35) + dark * rings[..., None] * 0.35
        # pith
        col = np.where((r < 0.06)[..., None], dark * 0.95, col)
        # radial cracks
        for k in range(4):
            a0 = rng.uniform(-math.pi, math.pi)
            d_ang = np.abs(np.angle(np.exp(1j * (th - a0))))
            crack = (d_ang < 0.035 * (1.0 - r)) & (r > 0.08) & (r < rng.uniform(0.55, 0.85))
            col = np.where(crack[..., None], dark * 0.7, col)
        # bark rim
        bark = hexcol("#4A3424") * (0.8 + 0.4 * periodic_noise(n, seed + 3, 2.0))[..., None]
        rim = smoothstep(0.84, 0.9, r)[..., None]
        col = col * (1 - rim) + bark * rim
        # cambium line
        cam = np.exp(-((r - 0.85) / 0.012) ** 2)[..., None]
        col = col * (1 - cam * 0.5) + hexcol("#C49A5E") * cam * 0.5
        return to_img(col)
    return lambda: cached_image(("rings", seed, n), fn)


def tex_cloth(seed=3, n=512, base="#E8DCC0", stripe=None, stripes=4, patches=0, patch_cols=(),
              weave=0.06, dirt=0.18):
    """Painted cloth: soft folds, faint weave, optional vertical stripes and sewn patches."""
    def fn():
        rng = np.random.default_rng(seed)
        b = hexcol(base)
        col = np.ones((n, n, 3)) * b
        if stripe is not None:
            s = hexcol(stripe)
            x = (np.arange(n) + 0.5) / n
            ph = (x * stripes) % 1.0
            m = smoothstep(0.47, 0.5, ph) * (1 - smoothstep(0.97, 1.0, ph))
            col = col * (1 - m[None, :, None]) + s * m[None, :, None]
            # piping lines between stripes
            edge = np.exp(-((ph - 0.5) / 0.008) ** 2) + np.exp(-((ph - 0.985) / 0.008) ** 2)
            col *= (1 - 0.18 * np.clip(edge, 0, 1))[None, :, None]
        for k in range(patches):
            pc = hexcol(patch_cols[k % len(patch_cols)]) if patch_cols else b * 0.8
            x0, y0 = rng.integers(0, n), rng.integers(0, n)
            w, h = rng.integers(n // 8, n // 4), rng.integers(n // 8, n // 4)
            yy, xx = np.mgrid[0:n, 0:n]
            inside = (((xx - x0) % n) < w) & (((yy - y0) % n) < h)
            col[inside] = col[inside] * 0.25 + pc * 0.75
            border = inside & ((((xx - x0) % n) < 4) | (((xx - x0) % n) > w - 5) | (((yy - y0) % n) < 4)
                               | (((yy - y0) % n) > h - 5))
            col[border] *= 0.62
        fold = periodic_noise(n, seed + 7, 3.2)
        fold_x = np.repeat(periodic_noise(n, seed + 8, 3.0)[:1], n, axis=0)
        shade = 0.82 + 0.26 * (0.6 * fold + 0.4 * fold_x)
        yy, xx = np.mgrid[0:n, 0:n]
        weave_p = 0.5 + 0.5 * np.sin(xx * math.pi / 2.0) * np.sin(yy * math.pi / 2.0)
        shade = shade * (1 - weave + weave * weave_p)
        grime = periodic_noise(n, seed + 9, 2.0)
        shade *= 1 - dirt * smoothstep(0.55, 0.95, grime)
        return to_img(col * shade[..., None])
    return lambda: cached_image(("cloth", seed, n, base, stripe, stripes, patches, tuple(patch_cols), weave,
                                 dirt), fn)


def tex_flat(hexc, n=64, noise_amt=0.06, seed=0):
    def fn():
        c = hexcol(hexc)
        a = np.ones((n, n, 3)) * c * (1 - noise_amt + noise_amt * 2 * periodic_noise(n, seed, 2.0))[..., None]
        return to_img(a)
    return lambda: cached_image(("flat", hexc, n, noise_amt, seed), fn)


def tex_glow(kind="gold", n=128, seed=4):
    """Emissive textures: gold seam sparkle, lantern glass, embers, lichen glyph."""
    def fn():
        rng = np.random.default_rng(seed)
        nz = periodic_noise(n, seed, 2.0)
        if kind == "gold":
            c0, c1 = hexcol("#B8862A"), hexcol("#FFE79A")
            a = c0 + (c1 - c0) * smoothstep(0.25, 0.85, nz)[..., None]
            for _ in range(40):
                x, y = rng.integers(0, n), rng.integers(0, n)
                a[y, x] = (1.0, 0.97, 0.85)
        elif kind == "lamp":
            c0, c1 = hexcol("#E8902E"), hexcol("#FFE2A8")
            a = c0 + (c1 - c0) * smoothstep(0.2, 0.8, nz)[..., None]
        elif kind == "ember":
            c0, c1 = hexcol("#5A140A"), hexcol("#FFB04A")
            a = c0 + (c1 - c0) * np.power(smoothstep(0.35, 0.9, nz), 1.4)[..., None]
        elif kind == "lichen":
            c0, c1 = hexcol("#B8B060"), hexcol("#F4F0B0")
            a = c0 + (c1 - c0) * nz[..., None]
        else:
            a = np.ones((n, n, 3)) * hexcol(kind)
        return to_img(a)
    return lambda: cached_image(("glow", kind, n, seed), fn)


def _blade(d, base, tip, width, col_base, col_tip, ss, segs=6, curve=(0.0, 0.0)):
    """Tapered grass/reed blade polygon with a vertical colour gradient (drawn as segments)."""
    bx, by = base
    tx, ty = tip
    cx, cy = curve
    pts = []
    for i in range(segs + 1):
        t = i / segs
        x = bx + (tx - bx) * t + cx * math.sin(t * math.pi) * (1 - t * 0.3)
        y = by + (ty - by) * t + cy * math.sin(t * math.pi)
        pts.append((x, y))
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        w0, w1 = width * (1 - t0) ** 0.8, width * (1 - t1) ** 0.8
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        poly = [(x0 + nx * w0, y0 + ny * w0), (x1 + nx * w1, y1 + ny * w1),
                (x1 - nx * w1, y1 - ny * w1), (x0 - nx * w0, y0 - ny * w0)]
        tm = (t0 + t1) / 2
        c = tuple(int(255 * (col_base[k] + (col_tip[k] - col_base[k]) * tm)) for k in range(3)) + (255,)
        d.polygon([(p[0] * ss, p[1] * ss) for p in poly], fill=c)


def _flower(d, x, y, r, petal, centre, ss, rng, petals=5):
    pc = tuple(int(v * 255) for v in petal) + (255,)
    sh = tuple(int(v * 255 * 0.72) for v in petal) + (255,)
    cc = tuple(int(v * 255) for v in centre) + (255,)
    a0 = rng.uniform(0, 6.28)
    for k in range(petals):
        ang = a0 + k * 2 * math.pi / petals
        px, py = x + math.cos(ang) * r * 0.62, y + math.sin(ang) * r * 0.62
        rr = r * 0.52
        d.ellipse([(px - rr) * ss, (py - rr + r * 0.12) * ss, (px + rr) * ss, (py + rr + r * 0.12) * ss], fill=sh)
        d.ellipse([(px - rr) * ss, (py - rr) * ss, (px + rr) * ss, (py + rr) * ss], fill=pc)
    rc = r * 0.34
    d.ellipse([(x - rc) * ss, (y - rc) * ss, (x + rc) * ss, (y + rc) * ss], fill=cc)


def tex_meadow_cards(seed=21, n=1024):
    """2x2 card atlas: 0 yellow flower clump, 1 white flower clump, 2 mixed (yellow, white, a few
    tiny blue), 3 grass tuft. Blades fan up from the bottom centre of each cell."""
    def fn():
        rng = np.random.default_rng(seed)
        ss = 2
        im = Image.new("RGBA", (n * ss, n * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = n // 2
        greens = [(hexcol("#3E5A2A"), hexcol("#8DAE60")), (hexcol("#486236"), hexcol("#9DBA68")),
                  (hexcol("#41602E"), hexcol("#B4C470"))]
        for cell in range(4):
            ox, oy = (cell % 2) * c, (cell // 2) * c
            nb = 70 if cell == 3 else 46
            for _ in range(nb):
                bx = ox + c * 0.5 + rng.normal(0, c * 0.07)
                by = oy + c * 0.97
                ang = rng.normal(0, 0.55)
                L = c * rng.uniform(0.45, 0.9) * (1.0 if cell == 3 else 0.8)
                tx = bx + math.sin(ang) * L
                ty = by - math.cos(ang) * L
                g0, g1 = greens[rng.integers(0, 3)]
                _blade(d, (bx, by), (tx, ty), c * rng.uniform(0.012, 0.022), g0, g1, ss,
                       curve=(rng.normal(0, c * 0.05), 0))
            if cell == 3:
                continue
            nf = 16 if cell != 2 else 20
            for k in range(nf):
                x = ox + c * 0.5 + rng.normal(0, c * 0.17)
                y = oy + c * rng.uniform(0.18, 0.62)
                x = min(max(x, ox + c * 0.1), ox + c * 0.9)
                if cell == 0:
                    petal, cen = hexcol("#F2D64A"), hexcol("#C97A20")
                elif cell == 1:
                    petal, cen = hexcol("#F4EFE0"), hexcol("#E8C040")
                else:
                    sel = k % 5
                    petal = [hexcol("#F2D64A"), hexcol("#F4EFE0"), hexcol("#F2D64A"), hexcol("#F4EFE0"),
                             hexcol("#7C8EE0")][sel]
                    cen = hexcol("#C97A20") if sel != 4 else hexcol("#F4EFE0")
                r = c * (rng.uniform(0.035, 0.055) if not (cell == 2 and k % 5 == 4) else 0.025)
                # stem
                g0, g1 = greens[0]
                _blade(d, (x + rng.normal(0, 4), oy + c * 0.97), (x, y), c * 0.007, g0, g1, ss, segs=3)
                _flower(d, x, y, r, petal, cen, ss, rng)
        im = im.resize((n, n), Image.LANCZOS)
        return dilate_rgb(im, 24)
    return lambda: cached_image(("meadow_cards", seed, n), fn)


def tex_reeds(seed=31, n=512):
    """Reed atlas: left 3/4 a blade strip (u across, v along: dark base -> pale tip), right 1/4
    the brown bulrush head."""
    def fn():
        rng = np.random.default_rng(seed)
        y, x = np.mgrid[0:n, 0:n] + 0.5
        v = y / n  # 0 top (tip) .. 1 bottom (base)
        tip, mid, base = hexcol("#C9C47A"), hexcol("#7E9A4A"), hexcol("#3C5428")
        t = v[..., None]
        col = np.where(t < 0.35, tip + (mid - tip) * (t / 0.35), mid + (base - mid) * ((t - 0.35) / 0.65))
        # midrib and streaks
        u = (x % (n * 0.75)) / (n * 0.75)
        rib = np.exp(-((u - 0.5) / 0.03) ** 2)[..., None]
        streak = periodic_noise(n, seed, 1.2)
        streak = np.repeat(streak[:1], n, axis=0)[..., None]
        col = col * (0.85 + 0.25 * streak) * (1 + 0.15 * rib)
        # bulrush head region
        head = x > n * 0.75
        hb = hexcol("#5A3A22") * (0.8 + 0.35 * periodic_noise(n, seed + 1, 2.4))[..., None]
        col = np.where(head[..., None], hb, col)
        return to_img(col)
    return lambda: cached_image(("reeds", seed, n), fn)


def tex_lily(seed=41, n=512):
    """Lily atlas: left half a pad (disc with a notch, radial veins), right half petal colour."""
    def fn():
        y, x = np.mgrid[0:n, 0:n] + 0.5
        h = n / 2
        cx, cy = h / 2, h
        dx, dy = (x - cx) / (h / 2), (y - cy) / (h / 2)
        r = np.sqrt(dx * dx + dy * dy)
        th = np.arctan2(dy, dx)
        base, dark, light = hexcol("#4F7A2E"), hexcol("#2F4A1E"), hexcol("#8DAE60")
        col = base + (light - base) * smoothstep(0.0, 1.0, 1 - r)[..., None] * 0.6
        veins = np.power(0.5 + 0.5 * np.cos(th * 11), 18) * smoothstep(0.1, 0.3, r)
        col = col * (1 - 0.25 * veins[..., None]) + light * 0.25 * veins[..., None]
        rim = smoothstep(0.82, 1.0, r)[..., None]
        col = col * (1 - rim) + dark * rim
        nz = periodic_noise(n, seed, 2.4)[..., None]
        col *= 0.88 + 0.24 * nz
        right = x > h
        pet = hexcol("#F4EFE0") * (1 - 0.35 * (y / n))[..., None] + hexcol("#E8B8C0") * 0.25 * (y / n)[..., None]
        col = np.where(right[..., None], pet, col)
        return to_img(col)
    return lambda: cached_image(("lily", seed, n), fn)


# =============================================================================================
# geometry: parts
# =============================================================================================

class Part:
    """A triangle mesh piece with one material. UVs are per corner (M, 3, 2) in image convention
    (u right, v down). Built in local space, UVs assigned, then transformed."""

    def __init__(self, v, t, mat, uv=None, smooth=40.0):
        self.v = np.asarray(v, float).reshape(-1, 3)
        self.t = np.asarray(t, np.int64).reshape(-1, 3)
        self.mat = mat
        self.uv = uv
        self.smooth = smooth           # degrees for corner normals
        self.nmode = "angle"           # 'angle' | 'sphere' | 'up'
        self.ncenter = None
        self.nblend = 0.85
        self.tint = np.ones((len(self.v), 3))
        self.sway = None               # per-vertex weight or None
        self.phase = 0.0
        self.ao = True                 # receive raycast AO
        self.ao_fn = None              # callable(part) -> per-vertex AO (replaces raycast)
        self.occ = 1.0                 # occluder weight (0 none, 0.5 cards, 1 solid)
        self.node = ""
        self.dark = None               # per-vertex extra darkening (crevices), multiplies

    # --- transforms -------------------------------------------------------------------------
    def xf(self, m=None, t=(0, 0, 0), s=None):
        v = self.v
        if s is not None:
            v = v * np.asarray(s, float)
        if m is not None:
            v = v @ np.asarray(m, float).T
        self.v = v + np.asarray(t, float)
        return self

    def rot(self, rx=0.0, ry=0.0, rz=0.0, pivot=(0, 0, 0)):
        p = np.asarray(pivot, float)
        self.v = (self.v - p) @ rot_matrix(rx, ry, rz).T + p
        return self

    def move(self, x=0.0, y=0.0, z=0.0):
        self.v = self.v + np.array([x, y, z], float)
        return self

    def scale(self, sx, sy=None, sz=None, pivot=(0, 0, 0)):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        p = np.asarray(pivot, float)
        self.v = (self.v - p) * np.array([sx, sy, sz]) + p
        return self

    def jitter(self, amp, seed, freq=None):
        """Random (freq None) or smooth-noise (freq per metre) displacement."""
        if freq is None:
            rng = np.random.default_rng(seed)
            self.v = self.v + rng.uniform(-1, 1, self.v.shape) * np.asarray(amp, float)
        else:
            off = (seed * 3.17 % 97.0, seed * 7.31 % 89.0, seed * 1.93 % 83.0)
            self.v = self.v + noise3(self.v, freq, off) * np.asarray(amp, float)
        return self

    def copy(self):
        p = Part(self.v.copy(), self.t.copy(), self.mat, None if self.uv is None else self.uv.copy(), self.smooth)
        for k in ("nmode", "ncenter", "nblend", "sway", "phase", "ao", "ao_fn", "occ", "node"):
            setattr(p, k, getattr(self, k))
        p.tint = self.tint.copy()
        p.dark = None if self.dark is None else self.dark.copy()
        if p.sway is not None:
            p.sway = np.array(p.sway, float).copy()
        return p

    def set_tint(self, rgb):
        self.tint = np.ones((len(self.v), 3)) * np.asarray(rgb, float)
        return self

    def tris(self):
        return len(self.t)


def merge_parts(parts):
    """Concatenate parts that share a material into one (keeps per-vertex data)."""
    if len(parts) == 1:
        return parts[0]
    vs, ts, uvs, tints = [], [], [], []
    off = 0
    for p in parts:
        vs.append(p.v)
        ts.append(p.t + off)
        uvs.append(p.uv)
        tints.append(p.tint)
        off += len(p.v)
    q = Part(np.concatenate(vs), np.concatenate(ts), parts[0].mat, np.concatenate(uvs), parts[0].smooth)
    q.tint = np.concatenate(tints)
    return q


# ---------------------------------------------------------------------------- UV projections

def uv_box(v, t, repeat, off=(0.0, 0.0), rot90_top=False):
    """Per-triangle box projection (texture upright on side faces). Image convention."""
    p = v[t]
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    a = np.abs(n)
    ax = np.argmax(a, axis=1)
    uv = np.zeros((len(t), 3, 2))
    sx = np.sign(n[:, 0])[:, None]
    sy = np.sign(n[:, 1])[:, None]
    sz = np.sign(n[:, 2])[:, None]
    sx[sx == 0] = 1
    sy[sy == 0] = 1
    sz[sz == 0] = 1
    mx, my, mz = ax == 0, ax == 1, ax == 2
    uv[mx, :, 0] = (p[mx, :, 1] * sx[mx])
    uv[mx, :, 1] = -p[mx, :, 2]
    uv[my, :, 0] = (-p[my, :, 0] * sy[my])
    uv[my, :, 1] = -p[my, :, 2]
    if rot90_top:
        uv[mz, :, 0] = p[mz, :, 1]
        uv[mz, :, 1] = p[mz, :, 0] * sz[mz]
    else:
        uv[mz, :, 0] = p[mz, :, 0]
        uv[mz, :, 1] = -p[mz, :, 1] * sz[mz]
    uv = uv / repeat + np.asarray(off, float)
    return uv


def uv_planar(v, t, axes=(0, 1), scale=1.0, off=(0.0, 0.0), flip_v=True):
    p = v[t]
    uv = np.stack([p[..., axes[0]], (-p[..., axes[1]] if flip_v else p[..., axes[1]])], axis=-1)
    return uv * scale + np.asarray(off, float)


def uv_disc(v, t, center, radius, axes=(0, 1)):
    """Disc mapping: the disc of `radius` around center fills the [0,1]^2 square."""
    p = v[t]
    c = np.asarray(center, float)
    u = 0.5 + (p[..., axes[0]] - c[axes[0]]) / (2 * radius)
    w = 0.5 - (p[..., axes[1]] - c[axes[1]]) / (2 * radius)
    return np.stack([u, w], axis=-1)


# ---------------------------------------------------------------------------- bmesh helpers

def bm_arrays(bm):
    """Vertices + triangles of a bmesh, triangulated here in face order (bmesh.ops.triangulate emits
    its faces in a run-dependent order, which broke byte-identical output)."""
    bm.verts.index_update()
    bm.faces.index_update()
    v = np.array([x.co[:] for x in bm.verts], float)
    tris = []
    faces = []
    for f in bm.faces:
        ids = [lp.vert.index for lp in f.loops]
        k = ids.index(min(ids))                 # canonical loop start (bmesh's varies run to run)
        faces.append(ids[k:] + ids[:k])
    faces.sort()
    for ids in faces:
        if len(ids) == 3:
            tris.append(ids)
        elif len(ids) == 4:
            tris += [[ids[0], ids[1], ids[2]], [ids[0], ids[2], ids[3]]]
        else:
            pts = [[bm.verts[k].co.copy() for k in ids]]
            for a, b, c in mathutils.geometry.tessellate_polygon(pts):
                tris.append([ids[a], ids[b], ids[c]])
    bm.free()
    return v, np.array(tris, np.int64)


def icosphere(subdiv=2, radius=1.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius, calc_uvs=False)
    return bm_arrays(bm)


def uvsphere(segs=10, rings=7, radius=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius, calc_uvs=False)
    return bm_arrays(bm)


# ---------------------------------------------------------------------------- primitives

def chamfer_rect(w, h, c):
    """8-point chamfered rectangle outline (CCW), centred."""
    x, y = w / 2, h / 2
    c = min(c, x * 0.45, y * 0.45)
    return np.array([(x - c, -y), (x, -y + c), (x, y - c), (x - c, y), (-x + c, y), (-x, y - c),
                     (-x, -y + c), (-x + c, -y)], float)


def circle(n, r=1.0, a0=0.0):
    a = a0 + np.arange(n) * 2 * math.pi / n
    return np.stack([np.cos(a) * r, np.sin(a) * r], axis=1)


def _ring_faces(S, K, closed=True):
    tris = []
    kk = K if closed else K - 1
    for s in range(S - 1):
        for k in range(kk):
            a = s * K + k
            b = s * K + (k + 1) % K
            c = (s + 1) * K + (k + 1) % K
            d = (s + 1) * K + k
            tris.append((a, b, c))
            tris.append((a, c, d))
    return tris


def sweep(profile, path, mat, scales=None, up=(0, 0, 1), cap0=True, cap1=True, repeat=None,
          uv_off=(0.0, 0.0), cap_mat=None, cap_radius=None, twist=0.0, smooth=50.0, closed=True):
    """Sweep a closed 2D profile (K,2) along a 3D polyline (S,3). Grain-aligned UVs:
    u around the profile, v along the path (both / repeat). Caps: fan (own material optional,
    disc-mapped for end grain). Returns a list of Parts (body [+ caps])."""
    prof = np.asarray(profile, float)
    path = np.asarray(path, float)
    S, K = len(path), len(prof)
    if scales is None:
        scales = np.ones(S)
    scales = np.asarray(scales, float)
    if scales.ndim == 1:
        scales = np.stack([scales, scales], axis=1)
    rep = repeat if repeat is not None else mat.repeat
    # tangents
    T = np.zeros_like(path)
    T[1:-1] = path[2:] - path[:-2]
    T[0] = path[1] - path[0]
    T[-1] = path[-1] - path[-2]
    T = nrm(T)
    upv = np.asarray(up, float)
    if abs(np.dot(T[0], nrm(upv))) > 0.95:
        upv = np.array([1.0, 0, 0]) if abs(T[0][0]) < 0.9 else np.array([0, 1.0, 0])
    N = nrm(np.cross(upv, T[0]))
    frames = []
    for s in range(S):
        if s > 0:
            # parallel transport
            b = np.cross(T[s - 1], T[s])
            bl = np.linalg.norm(b)
            if bl > 1e-9:
                ang = math.asin(min(1.0, bl))
                if np.dot(T[s - 1], T[s]) < 0:
                    ang = math.pi - ang
                N = np.array(Matrix.Rotation(ang, 3, Vector(b / bl)) @ Vector(N))
        B = np.cross(T[s], N)
        tw = math.radians(twist) * s / max(S - 1, 1)
        c, si = math.cos(tw), math.sin(tw)
        frames.append((N * c + B * si, -N * si + B * c))
    verts = np.zeros((S * K, 3))
    for s in range(S):
        Nn, Bb = frames[s]
        for k in range(K):
            px, py = prof[k] * scales[s]
            verts[s * K + k] = path[s] + Nn * px + Bb * py
    tris = np.array(_ring_faces(S, K, closed), np.int64)
    # UVs per corner
    per = np.linalg.norm(np.roll(prof, -1, axis=0) - prof, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(per)])          # K+1 entries
    mean_scale = scales.mean()
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    along = np.concatenate([[0.0], np.cumsum(seg)])
    uv = np.zeros((len(tris), 3, 2))
    for i, (a, b, c) in enumerate(tris):
        for j, vi in enumerate((a, b, c)):
            s, k = divmod(vi, K)
            uv[i, j] = (cum[k] * mean_scale, along[s])
        # wrap seam: corners with k == 0 that belong to a quad starting at k == K-1
        ks = [vi % K for vi in (a, b, c)]
        if K - 1 in ks and 0 in ks:
            for j, kv in enumerate(ks):
                if kv == 0:
                    uv[i, j, 0] = cum[K] * mean_scale
    uv[..., 1] *= -1
    uv = uv / rep + np.asarray(uv_off, float)
    body = Part(verts, tris, mat, uv, smooth)
    parts = [body]
    for end, flag in ((0, cap0), (S - 1, cap1)):
        if not flag:
            continue
        ring = verts[end * K:(end + 1) * K]
        cen = ring.mean(axis=0)
        cv = np.vstack([ring, cen[None]])
        ct = []
        for k in range(K):
            if end == 0:
                ct.append((K, (k + 1) % K, k))
            else:
                ct.append((K, k, (k + 1) % K))
        ct = np.array(ct, np.int64)
        cm = cap_mat or mat
        # disc mapping in the end frame
        Nn, Bb = frames[end]
        loc = np.stack([(cv - cen) @ Nn, (cv - cen) @ Bb], axis=1)
        if cap_mat is not None:
            R = cap_radius or np.abs(loc).max() * 1.02
            cuv = 0.5 + loc[ct] / (2 * R) * np.array([1, -1])
        else:
            cuv = loc[ct] * np.array([1, -1]) / rep + np.asarray(uv_off, float)
        cp = Part(cv, ct, cm, cuv, 25.0)
        parts.append(cp)
    if cap_mat is None and len(parts) > 1:
        return [merge_parts(parts)]
    return parts


def lathe(profile, sides, mat, repeat=None, a0=0.0, uv_off=(0.0, 0.0), smooth=50.0, cap_bottom=False,
          cap_top=False, cap_mat=None):
    """Revolve [(r, z), ...] (bottom -> top) around Z. r == 0 at an end makes a pole."""
    prof = [tuple(p) for p in profile]
    rep = repeat if repeat is not None else mat.repeat
    verts, rings = [], []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            idx = []
            for k in range(sides):
                a = a0 + k * 2 * math.pi / sides
                idx.append(len(verts))
                verts.append((math.cos(a) * r, math.sin(a) * r, z))
            rings.append(idx)
    verts = np.array(verts, float)
    tris, uvs = [], []
    # arc length along profile
    L = [0.0]
    for i in range(1, len(prof)):
        L.append(L[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    rmax = max(p[0] for p in prof)
    circ = 2 * math.pi * max(rmax, 1e-3)

    def uvk(k, i):
        return (k / sides * circ / rep + uv_off[0], -L[i] / rep + uv_off[1])

    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(sides):
            k1 = k + 1
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                tris.append((r0[0], r1[k % sides], r1[k1 % sides]))
                uvs.append((uvk(k + 0.5, i), uvk(k, i + 1), uvk(k1, i + 1)))
            elif len(r1) == 1:
                tris.append((r0[k % sides], r0[k1 % sides], r1[0]))
                uvs.append((uvk(k, i), uvk(k1, i), uvk(k + 0.5, i + 1)))
            else:
                a, b = r0[k % sides], r0[k1 % sides]
                c, d = r1[k1 % sides], r1[k % sides]
                tris.append((a, b, c))
                uvs.append((uvk(k, i), uvk(k1, i), uvk(k1, i + 1)))
                tris.append((a, c, d))
                uvs.append((uvk(k, i), uvk(k1, i + 1), uvk(k, i + 1)))
    parts = [Part(verts, np.array(tris, np.int64), mat, np.array(uvs, float), smooth)]
    for flag, i, top in ((cap_bottom, 0, False), (cap_top, len(rings) - 1, True)):
        if not flag or len(rings[i]) == 1:
            continue
        ring = verts[rings[i]]
        cen = ring.mean(axis=0)
        cv = np.vstack([ring, cen[None]])
        K = len(ring)
        ct = np.array([(K, k, (k + 1) % K) if top else (K, (k + 1) % K, k) for k in range(K)], np.int64)
        cm = cap_mat or mat
        r = prof[i][0]
        if cap_mat is not None:
            cuv = uv_disc(cv, ct, cen, r * 1.02)
        else:
            cuv = uv_planar(cv, ct, (0, 1), 1.0 / rep, uv_off)
        parts.append(Part(cv, ct, cm, cuv, 25.0))
    if cap_mat is None and len(parts) > 1:
        return [merge_parts(parts)]
    return parts


def slab(outline, z0, z1, mat, chamfer=0.04, bottom=True, repeat=None, uv_off=(0.0, 0.0), smooth=35.0,
         top_chamfer_only=True):
    """Extruded polygon (outline (K,2) CCW, may be concave) from z0 to z1 with a chamfered top
    edge (and bottom when top_chamfer_only is False). Box-projected UVs."""
    ol = np.asarray(outline, float)
    K = len(ol)

    def inset(poly, d):
        out = np.zeros_like(poly)
        for i in range(K):
            p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % K]
            e0 = nrm(p1 - p0)
            e1 = nrm(p2 - p1)
            n0 = np.array([e0[1], -e0[0]])
            n1 = np.array([e1[1], -e1[0]])
            b = nrm(n0 + n1)
            cosh = max(np.dot(b, n0), 0.35)
            out[i] = p1 - b * d / cosh
        return out

    rings = []
    c = min(chamfer, (z1 - z0) * 0.45)
    if not top_chamfer_only and c > 0:
        rings.append((inset(ol, c), z0))
        rings.append((ol, z0 + c))
    else:
        rings.append((ol, z0))
    if c > 0:
        rings.append((ol, z1 - c))
        rings.append((inset(ol, c), z1))
    else:
        rings.append((ol, z1))
    verts = []
    for poly, z in rings:
        for p in poly:
            verts.append((p[0], p[1], z))
    verts = np.array(verts, float)
    tris = _ring_faces(len(rings), K, True)
    # caps via tessellation (concave safe)
    top = rings[-1][0]
    tri_idx = mathutils.geometry.tessellate_polygon([[Vector((p[0], p[1], 0)) for p in top]])
    base_top = (len(rings) - 1) * K
    for a, b, cc in tri_idx:
        tris.append((base_top + a, base_top + b, base_top + cc))
    if bottom:
        bot = rings[0][0]
        tri_idx = mathutils.geometry.tessellate_polygon([[Vector((p[0], p[1], 0)) for p in bot]])
        for a, b, cc in tri_idx:
            tris.append((cc, b, a))
    tris = np.array(tris, np.int64)
    # fix winding so faces point outward: check top cap normal points up
    p = verts[tris]
    fn = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    # side faces: outward means dot(fn, centroid - polygon centre) > 0 ; flip whole mesh if majority inward
    cen = np.array([ol[:, 0].mean(), ol[:, 1].mean(), (z0 + z1) / 2])
    fc = p.mean(axis=1)
    if np.sum(np.einsum("ij,ij->i", fn, fc - cen) < 0) > len(tris) / 2:
        tris = tris[:, ::-1]
    rep = repeat if repeat is not None else mat.repeat
    uv = uv_box(verts, tris, rep, uv_off)
    return Part(verts, tris, mat, uv, smooth)


def box(size, mat, chamfer=0.0, center=(0, 0, 0), repeat=None, uv_off=(0.0, 0.0), smooth=35.0,
        segs=None):
    """Chamfered box (z from -h/2..h/2 around center). segs=(nx, ny, nz) subdivides for bending."""
    sx, sy, sz = size
    if segs is None and chamfer <= 0:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        v, t = bm_arrays(bm)
        v = v * np.array([sx, sy, sz])
    elif segs is None:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=min(chamfer, min(size) * 0.45),
                        offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
        v, t = bm_arrays(bm)
    else:
        nx, ny, nz = segs
        prof = chamfer_rect(sy, sz, chamfer) if chamfer > 0 else np.array(
            [(sy / 2, -sz / 2), (sy / 2, sz / 2), (-sy / 2, sz / 2), (-sy / 2, -sz / 2)])
        path = np.stack([np.linspace(-sx / 2, sx / 2, nx + 1), np.zeros(nx + 1), np.zeros(nx + 1)], axis=1)
        parts = sweep(prof, path, mat, up=(0, 0, 1), repeat=repeat, uv_off=uv_off, smooth=smooth)
        p = parts[0]
        p.v = p.v + np.asarray(center, float)
        return p
    rep = repeat if repeat is not None else mat.repeat
    uv = uv_box(v, t, rep, uv_off)
    p = Part(v + np.asarray(center, float), t, mat, uv, smooth)
    return p


def blob(mat, radius=1.0, subdiv=2, scale=(1, 1, 1), seed=0, noise_amp=0.15, noise_freq=1.2,
         flat_top=None, flat_bottom=0.0, cuts=0, cut_depth=0.18, repeat=None, smooth=55.0, sphere="ico",
         segs=(10, 7)):
    """Rock / mound primitive: ico/uv sphere scaled, noise-displaced, top/bottom flattened, chiselled
    by `cuts` random planes (flat facets give the hand-cut stylised look). Bottom sits on z=0."""
    if sphere == "ico":
        v, t = icosphere(subdiv, radius)
    else:
        v, t = uvsphere(segs[0], segs[1], radius)
    rng = np.random.default_rng(seed)
    v = v * np.asarray(scale, float)
    if noise_amp:
        off = (rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50))
        d = noise1(v, noise_freq / max(radius, 1e-3), off)
        d2 = noise1(v, noise_freq * 2.3 / max(radius, 1e-3), (off[1], off[2], off[0]))
        nn = nrm(v)
        v = v + nn * ((d * 0.7 + d2 * 0.3) * noise_amp * radius)[:, None]
    for _ in range(cuts):
        n = nrm(rng.normal(0, 1, 3) * np.array([1, 1, 0.6]))
        if n[2] < -0.3:
            n[2] = -n[2]
        ext = np.max(v @ n)
        dcut = ext - cut_depth * radius * rng.uniform(0.6, 1.3)
        s = v @ n
        over = s > dcut
        v[over] -= np.outer(s[over] - dcut, n) * 0.92
    zmin = v[:, 2].min()
    if flat_bottom is not None:
        zb = zmin + (v[:, 2].max() - zmin) * flat_bottom
        v[:, 2] = np.maximum(v[:, 2], zb)
    if flat_top is not None:
        zmax = v[:, 2].max()
        zt = zmin + (zmax - zmin) * flat_top
        over = v[:, 2] > zt
        v[over, 2] = zt + (v[over, 2] - zt) * 0.15
    v[:, 2] -= v[:, 2].min()
    rep = repeat if repeat is not None else mat.repeat
    uv = uv_box(v, t, rep, (rng.uniform(0, 1), rng.uniform(0, 1)))
    return Part(v, t, mat, uv, smooth)


def card(w, h, mat, rect, segs=(1, 1), bend=0.0, pivot="center"):
    """Foliage/billboard card in the local XZ plane (normal -Y), rect=(u0, v0, u1, v1) in the
    atlas. bend pushes the edges back (+Y) for volume. pivot 'center' or 'bottom'."""
    nx, nz = segs
    xs = np.linspace(-w / 2, w / 2, nx + 1)
    zs = np.linspace(-h / 2, h / 2, nz + 1) if pivot == "center" else np.linspace(0, h, nz + 1)
    verts, uvv = [], []
    u0, v0, u1, v1 = rect
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            r = math.hypot(x / (w / 2), (z - (zs[0] + zs[-1]) / 2) / (h / 2))
            verts.append((x, bend * r * r * max(w, h) * 0.5, z))
            uvv.append((u0 + (u1 - u0) * i / nx, v1 - (v1 - v0) * j / nz))
    verts = np.array(verts, float)
    uvv = np.array(uvv, float)
    tris = []
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + 1
            c = a + nx + 2
            d = a + nx + 1
            tris.append((a, b, c))
            tris.append((a, c, d))
    tris = np.array(tris, np.int64)
    p = Part(verts, tris, mat, uvv[tris], 180.0)
    p.occ = 0.5
    p.ao = False
    return p


def ribbon(path, widths, mat, u_range=(0.0, 1.0), v_range=(0.0, 1.0), normal_hint=(0, 0, 1)):
    """Flat strip along a path (blades, streams): u across, v along (v_range[0] at the start)."""
    path = np.asarray(path, float)
    S = len(path)
    T = np.zeros_like(path)
    T[1:-1] = path[2:] - path[:-2]
    T[0] = path[1] - path[0]
    T[-1] = path[-1] - path[-2]
    T = nrm(T)
    hint = np.asarray(normal_hint, float)
    verts, uvs = [], []
    for s in range(S):
        side = np.cross(T[s], hint)
        if np.linalg.norm(side) < 1e-6:
            side = np.cross(T[s], np.array([1.0, 0, 0]))
        side = nrm(side)
        w = widths[s] if hasattr(widths, "__len__") else widths
        verts.append(path[s] - side * w / 2)
        verts.append(path[s] + side * w / 2)
        vv = v_range[0] + (v_range[1] - v_range[0]) * s / (S - 1)
        uvs.append((u_range[0], vv))
        uvs.append((u_range[1], vv))
    verts = np.array(verts)
    uvs = np.array(uvs)
    tris = []
    for s in range(S - 1):
        a, b, c, d = 2 * s, 2 * s + 1, 2 * s + 3, 2 * s + 2
        tris.append((a, b, c))
        tris.append((a, c, d))
    tris = np.array(tris, np.int64)
    p = Part(verts, tris, mat, uvs[tris], 180.0)
    return p


# =============================================================================================
# asset assembly: normals, AO, colours, export
# =============================================================================================

def face_normals(v, t):
    p = v[t]
    return np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])


def corner_normals(v, t, angle_deg):
    fn = face_normals(v, t)
    fu = nrm(fn)
    if angle_deg >= 179.0:
        vn = np.zeros_like(v)
        np.add.at(vn, t.ravel(), np.repeat(fn, 3, axis=0))
        vn = nrm(vn)
        return vn[t]
    if angle_deg <= 0.1:
        return np.repeat(fu[:, None, :], 3, axis=1)
    cos_t = math.cos(math.radians(angle_deg))
    vf = [[] for _ in range(len(v))]
    for f, tri in enumerate(t):
        for k in range(3):
            vf[tri[k]].append(f)
    out = np.zeros((len(t), 3, 3))
    for f, tri in enumerate(t):
        for k in range(3):
            adj = vf[tri[k]]
            if len(adj) == 1:
                out[f, k] = fu[f]
                continue
            fa = fu[adj]
            ok = fa @ fu[f] >= cos_t
            acc = fn[np.array(adj)[ok]].sum(axis=0)
            out[f, k] = acc
    return nrm(out)


def vertex_normals(v, t):
    vn = np.zeros_like(v)
    np.add.at(vn, t.ravel(), np.repeat(face_normals(v, t), 3, axis=0))
    return nrm(vn)


def _hemi_dirs(k=24):
    """Cosine-weighted hemisphere directions around +Z (Fibonacci spiral, deterministic)."""
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(k):
        u = (i + 0.5) / k
        r = math.sqrt(u)
        a = i * ga
        out.append((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - u))))
    return np.array(out)


HEMI = _hemi_dirs(24)


class Asset:
    """Collects parts, then bakes normals / AO / vertex colours / UV2 and writes a GLB."""

    def __init__(self, aid, seed=1, ao_dist=1.0, ao_strength=1.0, base_dark=0.55, base_h=0.35,
                 top_light=0.12, ground_ao=True):
        self.id = aid
        self.seed = seed
        self.parts: list[Part] = []
        self.nodes = {"": {"parent": None, "pivot": np.zeros(3)}}
        self.node_order = [""]
        self.ao_dist = ao_dist
        self.ao_strength = ao_strength
        self.base_dark = base_dark
        self.base_h = base_h
        self.top_light = top_light
        self.ground_ao = ground_ao
        self.sway_fn = None            # callable(points (N,3), part) -> weights
        self.extras = {}
        self.height = None             # override for UV2.y normalisation

    def add(self, *parts):
        for p in parts:
            if isinstance(p, (list, tuple)):
                self.add(*p)
            else:
                self.parts.append(p)
        return parts[0] if len(parts) == 1 else parts

    def node(self, name, pivot, parent=""):
        self.nodes[name] = {"parent": parent, "pivot": np.asarray(pivot, float)}
        self.node_order.append(name)

    def tris(self):
        return int(sum(p.tris() for p in self.parts))

    def bounds(self):
        v = np.concatenate([p.v for p in self.parts])
        return v.min(axis=0), v.max(axis=0)

    # ---------------------------------------------------------------------------- baking
    def bake(self):
        parts = self.parts
        lo, hi = self.bounds()
        H = self.height or max(hi[2], 1e-3)
        # occluders
        def bvh(sel):
            vs, ts, off = [], [], 0
            for p in sel:
                vs.append(p.v)
                ts.append(p.t + off)
                off += len(p.v)
            if not vs:
                return None
            V = np.concatenate(vs)
            T = np.concatenate(ts)
            return BVHTree.FromPolygons([tuple(x) for x in V], [tuple(int(i) for i in x) for x in T],
                                        all_triangles=True, epsilon=0.0)
        solid = bvh([p for p in parts if p.occ >= 1.0])
        soft = bvh([p for p in parts if 0.0 < p.occ < 1.0])
        maxd = self.ao_dist
        for p in parts:
            n = len(p.v)
            # --- normals per corner
            if p.nmode == "sphere":
                c = np.asarray(p.ncenter, float)
                rn = nrm(p.v - c)
                fn = nrm(face_normals(p.v, p.t))
                cn = rn[p.t] * p.nblend + np.repeat(fn[:, None, :], 3, axis=1) * (1 - p.nblend)
                # double-sided cards: never let the blended normal point inward
                p.cn = nrm(cn)
                p.cn = nrm(rn[p.t] * 0.9 + p.cn * 0.1)
            elif p.nmode == "up":
                p.cn = np.tile(np.array([0, 0, 1.0]), (len(p.t), 3, 1))
            else:
                p.cn = corner_normals(p.v, p.t, p.smooth)
            # --- AO per vertex
            if p.ao_fn is not None:
                ao = np.asarray(p.ao_fn(p), float)
            elif p.ao and solid is not None:
                vn = vertex_normals(p.v, p.t)
                ao = np.ones(n)
                for i in range(n):
                    o = p.v[i]
                    nv = vn[i]
                    F = frame_from_z(nv)
                    org = Vector(o + nv * 0.012)
                    occ = 0.0
                    for d in HEMI:
                        dw = F @ d
                        dv = Vector(dw)
                        hit = solid.ray_cast(org, dv, maxd)
                        h = 0.0
                        if hit[0] is not None:
                            h = 1.0 - (hit[3] / maxd) ** 2
                        elif soft is not None:
                            hs = soft.ray_cast(org, dv, maxd)
                            if hs[0] is not None:
                                h = 0.5 * (1.0 - (hs[3] / maxd) ** 2)
                        if h == 0.0 and self.ground_ao and dw[2] < -1e-3:
                            tg = -(o[2] + 0.002) / dw[2]
                            if 0 < tg < maxd:
                                h = 0.8 * (1.0 - (tg / maxd) ** 2)
                        occ += h
                    ao[i] = 1.0 - self.ao_strength * occ / len(HEMI)
                ao = np.clip(ao, 0.2, 1.0)
                ao = 0.25 + 0.75 * np.power(ao, 1.25)
            else:
                ao = np.ones(n)
            z = p.v[:, 2]
            base = lerp(self.base_dark, 1.0, smoothstep(0.0, self.base_h, z))
            top = 1.0 - self.top_light + self.top_light * np.clip(z / H, 0, 1)
            shade = ao * base * top
            if p.dark is not None:
                shade = shade * p.dark
            p.shade = shade
            # sway + height
            if p.sway is not None:
                sw = np.asarray(p.sway, float) * np.ones(n)
            elif p.mat.sway and self.sway_fn is not None:
                sw = np.asarray(self.sway_fn(p.v, p), float)
            else:
                sw = np.zeros(n)
            p.sw = np.clip(sw, 0.0, 1.0)
            p.hn = np.clip(z / H, 0.0, 1.0)
            if p.mat.sway:
                g = np.clip(shade * p.tint.mean(axis=1), 0, 1)
                p.col = np.stack([p.sw, g, np.full(n, p.phase % 1.0), np.ones(n)], axis=1)
            else:
                rgb = np.clip(p.tint * shade[:, None], 0, 1)
                p.col = np.concatenate([rgb, np.ones((n, 1))], axis=1)

    # ---------------------------------------------------------------------------- export
    def export(self, path, mats_used=None):
        self.bake()
        # materials in order of first use
        mats = []
        for p in self.parts:
            if p.mat not in mats:
                mats.append(p.mat)
        nodes_out = []
        for name in self.node_order:
            nd = self.nodes[name]
            prims = []
            for m in mats:
                sel = [p for p in self.parts if p.node == name and p.mat is m]
                if not sel:
                    continue
                pos, nor, uv0, uv1, col = [], [], [], [], []
                piv = nd["pivot"]
                for p in sel:
                    T = p.t
                    pos.append((p.v[T] - piv).reshape(-1, 3))
                    nor.append(p.cn.reshape(-1, 3))
                    uv0.append(p.uv.reshape(-1, 2))
                    uv1.append(np.stack([p.sw[T], p.hn[T]], axis=-1).reshape(-1, 2))
                    col.append(p.col[T].reshape(-1, 4))
                prims.append((mats.index(m), np.concatenate(pos), np.concatenate(nor), np.concatenate(uv0),
                              np.concatenate(uv1), np.concatenate(col)))
            nodes_out.append({"name": self.id if name == "" else name, "parent": nd["parent"], "pivot": nd["pivot"],
                              "prims": prims, "key": name})
        write_glb(path, self.id, nodes_out, mats, self.extras)
        return mats


def _to_gltf(a):
    """Build space (x, y, z) Z-up/front +Y -> glTF (x, z, -y)."""
    a = np.asarray(a, float)
    return np.stack([a[..., 0], a[..., 2], -a[..., 1]], axis=-1)


def write_glb(path, aid, nodes, mats, extras):
    """Deterministic minimal glTF 2.0 binary writer (no Draco)."""
    bin_chunks = bytearray()
    buffer_views, accessors = [], []

    def add_view(data: bytes, target=None):
        while len(bin_chunks) % 4:
            bin_chunks.append(0)
        off = len(bin_chunks)
        bin_chunks.extend(data)
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            bv["target"] = target
        buffer_views.append(bv)
        return len(buffer_views) - 1

    def add_acc(arr, comp, typ, target, minmax=False, normalized=False):
        arr = np.ascontiguousarray(arr)
        view = add_view(arr.tobytes(), target)
        acc = {"bufferView": view, "componentType": comp, "count": int(arr.shape[0]), "type": typ}
        if normalized:
            acc["normalized"] = True
        if minmax:
            acc["min"] = [float(x) for x in arr.min(axis=0)]
            acc["max"] = [float(x) for x in arr.max(axis=0)]
        accessors.append(acc)
        return len(accessors) - 1

    # images / textures / materials
    images, textures, materials = [], [], []
    tex_index = {}
    for m in mats:
        data, mime = encode_image(m)
        k = (id(m.image()), m.size, m.alpha)
        if k not in tex_index:
            bv = add_view(data)
            images.append({"bufferView": bv, "mimeType": mime, "name": f"{aid}_{m.key}_basecolor"})
            textures.append({"sampler": 0, "source": len(images) - 1})
            tex_index[k] = len(textures) - 1
        ti = tex_index[k]
        md = {"name": m.gltf_name(aid),
              "pbrMetallicRoughness": {"baseColorTexture": {"index": ti},
                                       "baseColorFactor": [float(m.base_factor[0]), float(m.base_factor[1]),
                                                           float(m.base_factor[2]), 1.0],
                                       "metallicFactor": 0.0, "roughnessFactor": float(m.roughness)}}
        if m.alpha:
            md["alphaMode"] = "MASK"
            md["alphaCutoff"] = float(m.cutoff)
        if m.double:
            md["doubleSided"] = True
        if m.emissive:
            if m.emissive_image is not None:
                eim = m.emissive_image()
                ek = ("emissive", id(eim), m.size)
                if ek not in tex_index:
                    em = Mat(m.key + "_emissive", lambda: eim, size=m.size)
                    edata, emime = encode_image(em)
                    bv = add_view(edata)
                    images.append({"bufferView": bv, "mimeType": emime, "name": f"{aid}_{m.key}_emission"})
                    textures.append({"sampler": 0, "source": len(images) - 1})
                    tex_index[ek] = len(textures) - 1
                md["emissiveTexture"] = {"index": tex_index[ek]}
            else:
                md["emissiveTexture"] = {"index": ti}
            md["emissiveFactor"] = [float(x) for x in m.emissive_factor]
        ex = {"vc_vertex_color": "sway" if m.sway else "multiply"}
        if m.sway:
            ex["vertex_color"] = "R=sway weight, G=painted AO, B=cluster phase, A=1"
            ex["uv2"] = "x=sway weight, y=normalized height"
        else:
            ex["vertex_color"] = "RGB=painted AO and tint (multiply), A=1"
            ex["uv2"] = "x=sway weight (0), y=normalized height"
        if m.tag:
            ex["role"] = m.tag
        md["extras"] = ex
        materials.append(md)

    meshes, gnodes = [], []
    name_to_idx = {}
    for nd in nodes:
        prims_out = []
        for (mi, pos, nor, uv0, uv1, col) in nd["prims"]:
            P = _to_gltf(pos).astype(np.float32)
            N = _to_gltf(nor).astype(np.float32)
            U0 = uv0.astype(np.float32)
            U1 = uv1.astype(np.float32)
            C = col.astype(np.float32)
            rows = np.concatenate([P, N, U0, U1, C], axis=1)
            uniq, inv = np.unique(rows, axis=0, return_inverse=True)
            inv = inv.reshape(-1)
            # keep first-occurrence order for nicer locality (still deterministic)
            first = np.full(len(uniq), len(inv), np.int64)
            np.minimum.at(first, inv, np.arange(len(inv)))
            order = np.argsort(first, kind="stable")
            remap = np.empty_like(order)
            remap[order] = np.arange(len(order))
            uniq = uniq[order]
            idx = remap[inv]
            P, N, U0, U1, C = uniq[:, 0:3], uniq[:, 3:6], uniq[:, 6:8], uniq[:, 8:10], uniq[:, 10:14]
            N = nrm(N).astype(np.float32)
            attrs = {
                "POSITION": add_acc(P.astype(np.float32), 5126, "VEC3", 34962, minmax=True),
                "NORMAL": add_acc(N, 5126, "VEC3", 34962),
                "TEXCOORD_0": add_acc(U0.astype(np.float32), 5126, "VEC2", 34962),
                "TEXCOORD_1": add_acc(U1.astype(np.float32), 5126, "VEC2", 34962),
                "COLOR_0": add_acc(C.astype(np.float32), 5126, "VEC4", 34962),
            }
            if len(uniq) < 65535:
                ind = add_acc(idx.astype(np.uint16), 5123, "SCALAR", 34963)
            else:
                ind = add_acc(idx.astype(np.uint32), 5125, "SCALAR", 34963)
            prims_out.append({"attributes": attrs, "indices": ind, "material": int(mi), "mode": 4})
        node = {"name": nd["name"]}
        if prims_out:
            meshes.append({"name": nd["name"], "primitives": prims_out})
            node["mesh"] = len(meshes) - 1
        name_to_idx[nd["key"]] = len(gnodes)
        gnodes.append(node)
    # hierarchy + translations (relative to parent pivot)
    roots = []
    for nd in nodes:
        i = name_to_idx[nd["key"]]
        if nd["parent"] is None:
            roots.append(i)
            continue
        par = [x for x in nodes if x["key"] == nd["parent"]][0]
        rel = np.asarray(nd["pivot"]) - np.asarray(par["pivot"])
        t = _to_gltf(rel)
        if np.abs(t).max() > 0:
            gnodes[i]["translation"] = [float(x) for x in t]
        pi = name_to_idx[nd["parent"]]
        gnodes[pi].setdefault("children", []).append(i)
    if extras:
        gnodes[roots[0]]["extras"] = extras
    gltf = {
        "asset": {"version": "2.0", "generator": "Vibecraft tools/kits/doodads.py"},
        "scene": 0,
        "scenes": [{"name": aid, "nodes": roots}],
        "nodes": gnodes,
        "meshes": meshes,
        "materials": materials,
        "textures": textures,
        "images": images,
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
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
    return path
