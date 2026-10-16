#!/usr/bin/env python3
"""Image tools for Vibecraft art (Pillow + numpy; runs on the system python3).

Subcommands (each has its own --help):
  seamless       make a roughly-tileable texture tile seamlessly (+ 2x2 preview, seam scores)
  tile-preview   write a 2x2 / 3x3 tiled preview of any image (to judge tiling by eye)
  seam-score     print how visible the wrap-around seams of images are (1.0 = like any other column)
  resize         resize images (Lanczos), optional power-of-two rounding
  array          stack N same-size layers into a vertical strip for a Godot Texture2DArray
                 (optionally writes the .import file so Godot imports it as an array)
  atlas          pack images into a grid atlas + JSON with each cell's pixel rect and UV rect
  icon           crop/centre/resize to 128 and 64 px command-card icons, optional bevelled frame
                 and a greyed "disabled" variant
  palette-match  shift an image's colours toward a reference image (Lab mean/std or histogram)

All commands print a JSON summary on stdout. Outputs are overwritten (idempotent).
Examples:
  python3 tools/texture_tools.py seamless grass.png -o assets/textures/terrain/grass.png --preview
  python3 tools/texture_tools.py array grass.png dirt.png rock.png -o terrain_array.png --size 1024 --godot-import
  python3 tools/texture_tools.py icon footman_concept.png -o assets/icons/footman --frame "#b08d3c" --disabled
  python3 tools/texture_tools.py palette-match dirt.png --ref grass.png -o dirt_matched.png --strength 0.6
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = 300_000_000


# ----------------------------------------------------------------------------- helpers

def load(path) -> Image.Image:
    im = Image.open(path)
    im.load()
    if im.mode not in ("RGB", "RGBA", "L", "LA"):
        im = im.convert("RGBA" if ("transparency" in im.info or im.mode in ("PA", "P")) else "RGB")
    return im


def has_alpha(im):
    if im.mode not in ("RGBA", "LA"):
        return False
    return int(np.asarray(im.getchannel("A")).min()) < 255


def to_float(im):
    return np.asarray(im, dtype=np.float32) / 255.0


def from_float(arr, mode):
    a = (np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(a, mode)


def save(im: Image.Image, path, quality=92):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        im.convert("RGB").save(path, "JPEG", quality=quality, subsampling=0, optimize=True)
    elif ext == ".webp":
        im.save(path, "WEBP", quality=quality)
    else:
        im.save(path, "PNG", optimize=True)
    return os.path.abspath(path)


def out_paths(inputs, out, out_dir, suffix="", ext=None):
    if out and len(inputs) == 1:
        return [out]
    if out and len(inputs) > 1 and not out_dir:
        out_dir = out
    if not out_dir:
        raise SystemExit("give -o OUT for a single input or --out-dir DIR for several")
    res = []
    for p in inputs:
        stem, e = os.path.splitext(os.path.basename(p))
        res.append(os.path.join(out_dir, stem + suffix + (ext or e)))
    return res


def parse_size(s):
    if "x" in s.lower():
        w, h = s.lower().split("x")
        return int(w), int(h)
    return int(s), int(s)


def parse_color(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def box_blur(a, r, axis, mode):
    """Box blur of radius r along one axis using a cumulative sum (O(N))."""
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    p = np.pad(a, pad, mode=mode)
    c = np.cumsum(p, axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def gauss_blur(a, sigma, wrap_x=False, wrap_y=False):
    """Gaussian-ish blur (3 box passes per axis) with wrap or reflect borders per axis."""
    r = max(1, int(round(sigma * 0.85)))
    for _ in range(3):
        a = box_blur(a, r, 1, "wrap" if wrap_x else "reflect")
        a = box_blur(a, r, 0, "wrap" if wrap_y else "reflect")
    return a


def seam_scores(arr):
    """Wrap-around seam difference divided by the typical difference between neighbouring
    columns/rows right next to the seam (4 on each side), per axis.
    ~1.0: the seam is as continuous as the image itself; >1.5: visible seam."""
    a = arr[..., :3] if arr.ndim == 3 else arr

    def score(m):  # m: seam along axis 0
        seam = np.abs(m[0] - m[-1]).mean()
        near = np.concatenate([np.abs(np.diff(m[:5], axis=0)).ravel(), np.abs(np.diff(m[-5:], axis=0)).ravel()])
        return round(float(seam / max(near.mean(), 1e-6)), 3)

    return {"x": score(np.swapaxes(a, 0, 1)), "y": score(a)}


def lowfreq_unevenness(arr):
    """Std of the heavily blurred luminance relative to its mean: large-scale lighting
    gradients that make tiling obvious even without seams (0.0 = perfectly even)."""
    lum = arr[..., :3].mean(axis=2) if arr.ndim == 3 else arr
    h, w = lum.shape
    small = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).resize((16, 16), Image.BOX), np.float32)
    return round(float(small.std() / max(small.mean(), 1e-6)), 4)


def tile_image(im, n=2, max_px=2048):
    w, h = im.size
    out = Image.new(im.mode, (w * n, h * n))
    for i in range(n):
        for j in range(n):
            out.paste(im, (i * w, j * h))
    if max(out.size) > max_px:
        k = max_px / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


# ----------------------------------------------------------------------------- seamless

def _blend_strip(a_strip, b_strip, t, wrap_other):
    """Blend two strips with weight t (for a) using variance-preserving blending: the low
    frequencies cross-fade linearly, the detail is renormalized so the band doesn't go soft."""
    sigma = max(2.0, a_strip.shape[1] / 6.0) if a_strip.ndim >= 2 else 2.0
    mu_a = gauss_blur(a_strip, sigma, wrap_x=False, wrap_y=wrap_other)
    mu_b = gauss_blur(b_strip, sigma, wrap_x=False, wrap_y=wrap_other)
    wa, wb = t, 1.0 - t
    norm = np.sqrt(wa * wa + wb * wb)
    return wa * mu_a + wb * mu_b + (wa * (a_strip - mu_a) + wb * (b_strip - mu_b)) / norm


def crossfade_x(arr, b, wrap_other):
    """Make arr tile horizontally; width shrinks by b."""
    H, W = arr.shape[:2]
    x = (np.arange(b, dtype=np.float32) + 0.5) / b
    t = x * x * (3 - 2 * x)  # smoothstep
    shape = (1, b) + (1,) * (arr.ndim - 2)
    t = t.reshape(shape)
    strip = _blend_strip(arr[:, :b], arr[:, W - b:], t, wrap_other)
    return np.concatenate([strip, arr[:, b:W - b]], axis=1)


def flatten_lighting(arr, strength):
    """Remove large-scale brightness gradients (common in AI textures) before tiling."""
    rgb = arr[..., :3]
    lum = rgb.mean(axis=2, keepdims=True)
    big = gauss_blur(lum, max(arr.shape[:2]) / 6.0, wrap_x=True, wrap_y=True)
    gain = np.clip(lum.mean() / np.maximum(big, 1e-3), 0.5, 2.0)
    out = arr.copy()
    out[..., :3] = rgb * (1.0 + strength * (gain - 1.0))
    return out


def cmd_seamless(a):
    outs = out_paths(a.inputs, a.out, a.out_dir)
    res = []
    for src, dst in zip(a.inputs, outs):
        im = load(src)
        mode = "RGBA" if has_alpha(im) else "RGB"
        if im.mode == "L":
            mode = "L"
        arr = to_float(im.convert(mode))
        before = {"seam": seam_scores(arr), "unevenness": lowfreq_unevenness(arr)}
        H, W = arr.shape[:2]
        if a.flatten == "auto":
            flat = 1.0 if before["unevenness"] > 0.08 else 0.0
        else:
            flat = float(a.flatten)
        if flat > 0:
            arr = flatten_lighting(arr, flat)
        if a.method == "crossfade":
            bx = max(2, int(round(W * a.blend)))
            by = max(2, int(round(H * a.blend)))
            arr = crossfade_x(arr, bx, wrap_other=False)
            arr = np.swapaxes(crossfade_x(np.swapaxes(arr, 0, 1), by, wrap_other=True), 0, 1)
        elif a.method == "mirror":
            top = np.concatenate([arr, arr[:, ::-1]], axis=1)
            arr = np.concatenate([top, top[::-1]], axis=0)
        out_im = from_float(arr, mode)
        if not a.keep_shrunk and out_im.size != (W, H):
            # back to the original size; wrap-pad so the resampler sees the tiled neighbourhood
            p = 8
            arr_p = np.pad(np.asarray(out_im), [(p, p), (p, p)] + ([(0, 0)] if arr.ndim == 3 else []), mode="wrap")
            big = Image.fromarray(arr_p, mode)
            sx, sy = W / out_im.width, H / out_im.height
            big = big.resize((round(big.width * sx), round(big.height * sy)), Image.LANCZOS)
            ox, oy = round(p * sx), round(p * sy)
            out_im = big.crop((ox, oy, ox + W, oy + H))
        save(out_im, dst, a.quality)
        arr2 = to_float(out_im)
        entry = {"input": os.path.abspath(src), "output": os.path.abspath(dst), "method": a.method, "flatten": flat,
                 "size": list(out_im.size), "before": before,
                 "after": {"seam": seam_scores(arr2), "unevenness": lowfreq_unevenness(arr2)}}
        if a.preview:
            pv = os.path.splitext(dst)[0] + "_tile2x2.jpg"
            entry["preview"] = save(tile_image(out_im, 2), pv, 88)
            if a.preview_before:
                pb = os.path.splitext(dst)[0] + "_orig_tile2x2.jpg"
                entry["preview_before"] = save(tile_image(im.convert(mode), 2), pb, 88)
        res.append(entry)
    return {"seamless": res}


def cmd_tile_preview(a):
    outs = out_paths(a.inputs, a.out, a.out_dir, suffix=f"_tile{a.n}x{a.n}", ext=".jpg")
    res = []
    for src, dst in zip(a.inputs, outs):
        im = load(src)
        res.append({"input": os.path.abspath(src), "output": save(tile_image(im, a.n, a.max_px), dst, 88)})
    return {"tile_preview": res}


def cmd_seam_score(a):
    res = []
    for src in a.inputs:
        arr = to_float(load(src).convert("RGB"))
        res.append({"input": os.path.abspath(src), "seam": seam_scores(arr), "unevenness": lowfreq_unevenness(arr),
                    "size": [arr.shape[1], arr.shape[0]]})
    return {"seam_score": res}


# ----------------------------------------------------------------------------- resize / array / atlas

def pot(n):
    return 1 << max(0, int(round(math.log2(max(n, 1)))))


def resize_to(im, size, filt=Image.LANCZOS):
    if im.size == size:
        return im
    return im.resize(size, filt)


FILTERS = {"lanczos": Image.LANCZOS, "box": Image.BOX, "bilinear": Image.BILINEAR, "nearest": Image.NEAREST}


def cmd_resize(a):
    outs = out_paths(a.inputs, a.out, a.out_dir)
    res = []
    for src, dst in zip(a.inputs, outs):
        im = load(src)
        w, h = im.size
        if a.size:
            tw, th = parse_size(a.size)
            if a.fit:
                k = min(tw / w, th / h)
                tw, th = max(1, round(w * k)), max(1, round(h * k))
        else:
            k = a.scale
            tw, th = max(1, round(w * k)), max(1, round(h * k))
        if a.pot:
            tw, th = pot(tw), pot(th)
        out = resize_to(im, (tw, th), FILTERS[a.filter])
        res.append({"input": os.path.abspath(src), "output": save(out, dst, a.quality), "from": [w, h], "to": [tw, th]})
    return {"resize": res}


def _collect_layers(inputs, size, mode_hint=None):
    ims = [load(p) for p in inputs]
    if size:
        tw, th = parse_size(size)
    else:
        tw, th = ims[0].size
    mode = "RGBA" if any(has_alpha(i) for i in ims) else "RGB"
    return [resize_to(i.convert(mode), (tw, th)) for i in ims], (tw, th), mode


def write_array_import(png_path, layers, mipmaps=True):
    """Godot 4 import settings so the strip imports as a Texture2DArray."""
    txt = (
        "[remap]\n\n"
        "importer=\"2d_array_texture\"\n"
        "type=\"CompressedTexture2DArray\"\n\n"
        "[params]\n\n"
        "compress/mode=1\n"
        "compress/high_quality=false\n"
        "compress/lossy_quality=0.7\n"
        "compress/hdr_compression=1\n"
        "compress/channel_pack=0\n"
        f"mipmaps/generate={'true' if mipmaps else 'false'}\n"
        "mipmaps/limit=-1\n"
        "slices/horizontal=1\n"
        f"slices/vertical={layers}\n"
    )
    path = png_path + ".import"
    with open(path, "w") as f:
        f.write(txt)
    return os.path.abspath(path)


def cmd_array(a):
    layers, (tw, th), mode = _collect_layers(a.inputs, a.size)
    strip = Image.new(mode, (tw, th * len(layers)))
    for i, im in enumerate(layers):
        strip.paste(im, (0, i * th))
    out = save(strip, a.out)
    res = {"output": out, "layer_size": [tw, th], "layers": [
        {"index": i, "source": os.path.abspath(p)} for i, p in enumerate(a.inputs)],
        "godot": f"import as Texture2DArray with slices/horizontal=1, slices/vertical={len(layers)}"}
    if a.godot_import:
        res["import_file"] = write_array_import(a.out, len(layers), not a.no_mipmaps)
    return {"array": res}


def cmd_atlas(a):
    layers, (tw, th), mode = _collect_layers(a.inputs, a.size)
    n = len(layers)
    cols = a.cols or int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))
    pad = a.padding
    W, H = cols * (tw + 2 * pad), rows * (th + 2 * pad)
    atlas = Image.new(mode, (W, H), (0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
    cells = {}
    for i, im in enumerate(layers):
        c, r = i % cols, i // cols
        x, y = c * (tw + 2 * pad) + pad, r * (th + 2 * pad) + pad
        if pad:
            # edge-extend into the padding so mipmaps/bilinear don't bleed neighbours in
            ext = np.pad(np.asarray(im), [(pad, pad), (pad, pad)] + ([(0, 0)] if np.asarray(im).ndim == 3 else []),
                         mode="edge")
            atlas.paste(Image.fromarray(ext, mode), (x - pad, y - pad))
        else:
            atlas.paste(im, (x, y))
        name = os.path.splitext(os.path.basename(a.inputs[i]))[0]
        cells[name] = {"index": i, "rect": [x, y, tw, th],
                       "uv": [round(x / W, 6), round(y / H, 6), round((x + tw) / W, 6), round((y + th) / H, 6)]}
    out = save(atlas, a.out)
    meta = {"image": os.path.basename(out), "size": [W, H], "cell": [tw, th], "cols": cols, "rows": rows,
            "padding": pad, "cells": cells}
    jpath = os.path.splitext(a.out)[0] + ".json"
    with open(jpath, "w") as f:
        json.dump(meta, f, indent=2)
    return {"atlas": {"output": out, "json": os.path.abspath(jpath), **meta}}


# ----------------------------------------------------------------------------- icon

def detect_bg(arr):
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]], axis=0)
    return np.median(border[:, :3], axis=0)


def content_bbox(im, thresh):
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32)
    if has_alpha(im):
        mask = arr[..., 3] > 16
        bg = None
    else:
        bg = detect_bg(arr)
        mask = np.abs(arr[..., :3] - bg).max(axis=2) > thresh
    ys, xs = np.nonzero(mask)
    if len(xs) < 16:
        return None, bg
    # ignore stray specks: use the 0.5..99.5 percentile extents
    x0, x1 = np.percentile(xs, [0.5, 99.5])
    y0, y1 = np.percentile(ys, [0.5, 99.5])
    return (int(x0), int(y0), int(x1) + 1, int(y1) + 1), bg


def square_crop(im, bbox, pad_frac, fill):
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad_frac)
    side = max(8, int(round(side)))
    l, t = int(round(cx - side / 2)), int(round(cy - side / 2))
    canvas = Image.new(im.mode, (side, side), fill)
    canvas.paste(im, (-l, -t))
    return canvas


def bevel_frame(im, color, width_frac):
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32)
    H, W = arr.shape[:2]
    w = max(2, int(round(min(W, H) * width_frac)))
    yy, xx = np.mgrid[0:H, 0:W]
    dl, dt, dr, db = xx, yy, W - 1 - xx, H - 1 - yy
    d = np.minimum(np.minimum(dl, dr), np.minimum(dt, db))
    light = np.minimum(dl, dt) <= np.minimum(dr, db)  # top/left band (diagonal mitre at corners)
    base = np.array(color, np.float32)
    frac = d / max(w - 1, 1)  # 0 outer .. 1 inner
    hi = np.clip(base * 1.35 + 20, 0, 255)
    lo = base * 0.55
    ring = np.where(light[..., None], hi * (1 - 0.35 * frac[..., None]) + base * 0.35 * frac[..., None],
                    lo * (1 - 0.35 * frac[..., None]) + base * 0.35 * frac[..., None])
    dark = base * 0.25
    in_band = d < w
    outer = d == 0
    inner = d == w - 1
    out = arr.copy()
    out[in_band, :3] = ring[in_band]
    out[outer | inner, :3] = dark
    out[in_band, 3] = 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def cmd_icon(a):
    im = load(a.input)
    alpha = has_alpha(im)
    work = im.convert("RGBA" if alpha else "RGB")
    if a.bg == "auto":
        fill = (0, 0, 0, 0) if alpha else tuple(int(v) for v in detect_bg(np.asarray(work.convert("RGBA"))))
    elif a.bg == "transparent":
        work = work.convert("RGBA")
        fill = (0, 0, 0, 0)
    else:
        fill = parse_color(a.bg)
        if alpha:
            bgim = Image.new("RGBA", work.size, fill + (255,))
            bgim.alpha_composite(work)
            work = bgim.convert("RGB")
            alpha = False
    if work.mode == "RGBA" and isinstance(fill, tuple) and len(fill) == 3:
        fill = fill + (0,)
    crop_info = a.crop
    pad = a.pad + (a.bevel if a.frame else 0.0)  # keep the subject clear of the frame
    if a.crop == "auto":
        bbox, _ = content_bbox(work, a.threshold)
        if bbox is None:
            crop_info = "center (no content found)"
            s = min(work.size)
            bbox = ((work.width - s) // 2, (work.height - s) // 2, (work.width + s) // 2, (work.height + s) // 2)
            sq = work.crop(bbox)
        else:
            sq = square_crop(work, bbox, pad, fill)
            crop_info = {"auto_bbox": list(bbox)}
    elif a.crop == "center":
        s = min(work.size)
        l, t = (work.width - s) // 2, (work.height - s) // 2
        sq = work.crop((l, t, l + s, t + s))
    elif a.crop == "none":
        sq = work if work.width == work.height else square_crop(work, (0, 0, work.width, work.height), 0, fill)
    else:
        x, y, w, h = (int(v) for v in a.crop.split(","))
        sq = square_crop(work, (x, y, x + w, y + h), pad, fill)
    if a.zoom != 1.0:
        s = sq.width
        z = int(round(s / a.zoom))
        o = (s - z) // 2
        sq = sq.crop((o, o, o + z, o + z)) if a.zoom > 1 else square_crop(sq, (0, 0, s, s), (1 / a.zoom - 1) / 2, fill)
    files = []
    for size in [int(s) for s in a.sizes.split(",")]:
        ic = sq.resize((size, size), Image.LANCZOS)
        if a.frame:
            ic = bevel_frame(ic, parse_color(a.frame), a.bevel)
            if not alpha:
                ic = ic.convert("RGB")
        p = save(ic, f"{a.out}_{size}.png")
        files.append(p)
        if a.disabled:
            arr = np.asarray(ic.convert("RGBA"), np.float32)
            g = arr[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
            arr[..., :3] = (g * 0.55)[..., None]
            dis = Image.fromarray(arr.astype(np.uint8), "RGBA")
            files.append(save(dis if alpha else dis.convert("RGB"), f"{a.out}_{size}_dis.png"))
    return {"icon": {"input": os.path.abspath(a.input), "crop": crop_info, "files": files}}


# ----------------------------------------------------------------------------- palette match

_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]], np.float32)
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ).astype(np.float32)
_WHITE = np.array([0.95047, 1.0, 1.08883], np.float32)


def srgb_to_lab(rgb):
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = c @ _M_RGB2XYZ.T / _WHITE
    e = 216 / 24389
    k = 24389 / 27
    f = np.where(xyz > e, np.cbrt(xyz), (k * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    A = 500 * (f[..., 0] - f[..., 1])
    B = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, A, B], axis=-1)


def lab_to_srgb(lab):
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    e = 216 / 24389
    k = 24389 / 27
    f = np.stack([fx, fy, fz], axis=-1)
    xyz = np.where(f ** 3 > e, f ** 3, (116 * f - 16) / k)
    xyz[..., 1] = np.where(lab[..., 0] > k * e, fy ** 3, lab[..., 0] / k)
    c = (xyz * _WHITE) @ _M_XYZ2RGB.T
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def _valid(arr):
    if arr.shape[-1] == 4:
        return arr[..., 3] > 0.04
    return np.ones(arr.shape[:2], bool)


def cmd_palette_match(a):
    ref = to_float(load(a.ref).convert("RGBA"))
    ref_lab = srgb_to_lab(ref[..., :3])[_valid(ref)]
    outs = out_paths(a.inputs, a.out, a.out_dir, suffix=a.suffix)
    res = []
    chans = [0, 1, 2] if not a.keep_luminance else [1, 2]
    for src, dst in zip(a.inputs, outs):
        im = load(src)
        alpha = has_alpha(im)
        arr = to_float(im.convert("RGBA"))
        lab = srgb_to_lab(arr[..., :3])
        m = _valid(arr)
        src_stats = {"mean": lab[m].mean(0).round(2).tolist(), "std": lab[m].std(0).round(2).tolist()}
        out = lab.copy()
        for ch in chans:
            x = lab[..., ch]
            if a.mode == "stats":
                ms, ss = x[m].mean(), x[m].std() + 1e-6
                mr, sr = ref_lab[:, ch].mean(), ref_lab[:, ch].std() + 1e-6
                k = float(np.clip(sr / ss, 0.5, 2.0))
                y = (x - ms) * k + mr
            else:  # histogram (quantile) matching
                qs = np.linspace(0, 100, 257)
                sq = np.percentile(x[m], qs)
                rq = np.percentile(ref_lab[:, ch], qs)
                sq = np.maximum.accumulate(sq + np.arange(len(sq)) * 1e-6)
                y = np.interp(x, sq, rq)
            out[..., ch] = x + a.strength * (y - x)
        rgb = lab_to_srgb(out)
        res_arr = np.concatenate([rgb, arr[..., 3:4]], axis=-1)
        res_im = from_float(res_arr, "RGBA")
        if not alpha:
            res_im = res_im.convert("RGB")
        save(res_im, dst, a.quality)
        new_lab = srgb_to_lab(rgb)[m]
        res.append({"input": os.path.abspath(src), "output": os.path.abspath(dst), "mode": a.mode,
                    "strength": a.strength, "lab_before": src_stats,
                    "lab_after": {"mean": new_lab.mean(0).round(2).tolist(), "std": new_lab.std(0).round(2).tolist()},
                    "lab_reference": {"mean": ref_lab.mean(0).round(2).tolist(),
                                      "std": ref_lab.std(0).round(2).tolist()}})
    return {"palette_match": res}


# ----------------------------------------------------------------------------- cli

def build_parser():
    ap = argparse.ArgumentParser(prog="texture_tools.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def io_args(p, multi=True):
        p.add_argument("inputs", nargs="+" if multi else 1, help="input image(s)")
        p.add_argument("-o", "--out", help="output file (single input)")
        p.add_argument("--out-dir", help="output folder (several inputs; same file names)")
        p.add_argument("--quality", type=int, default=92, help="JPEG/WebP quality when the output is .jpg/.webp")

    p = sub.add_parser("seamless", help="make a texture tile seamlessly",
                       description="Make a roughly tileable texture tile seamlessly. 'crossfade' (default): "
                                   "the last BLEND fraction of each edge is cross-faded into the opposite edge "
                                   "with variance-preserving blending (no blurry band, no mirror symmetry), then "
                                   "the image is resampled back to its size. 'mirror': classic 4-quadrant mirror "
                                   "(always seamless, visibly symmetric). --flatten removes large lighting "
                                   "gradients/vignettes first (they make the tile grid visible even without seams). Prints seam scores (1.0 = invisible) before/after.")
    io_args(p)
    p.add_argument("--method", choices=["crossfade", "mirror"], default="crossfade")
    p.add_argument("--blend", type=float, default=0.125, help="cross-fade band as a fraction of the size")
    p.add_argument("--flatten", default="auto",
                   help="0..1 strength of large-scale lighting/vignette removal before tiling; 'auto' (default) "
                        "uses 1 when the low-frequency unevenness score is above 0.08, else 0")
    p.add_argument("--keep-shrunk", action="store_true", help="don't resample back to the original size")
    p.add_argument("--preview", action="store_true", help="also write <out>_tile2x2.jpg")
    p.add_argument("--preview-before", action="store_true", help="also write the 2x2 preview of the input")
    p.set_defaults(func=cmd_seamless)

    p = sub.add_parser("tile-preview", help="tile an image NxN for visual checking")
    io_args(p)
    p.add_argument("-n", type=int, default=2, help="tiles per side (default 2)")
    p.add_argument("--max-px", type=int, default=2048, help="downscale the preview to this size")
    p.set_defaults(func=cmd_tile_preview)

    p = sub.add_parser("seam-score", help="report wrap-around seam visibility (1.0 = seamless)")
    p.add_argument("inputs", nargs="+")
    p.set_defaults(func=cmd_seam_score)

    p = sub.add_parser("resize", help="resize images")
    io_args(p)
    p.add_argument("--size", help="N or WxH")
    p.add_argument("--scale", type=float, default=1.0, help="scale factor if --size is not given")
    p.add_argument("--fit", action="store_true", help="keep aspect ratio inside --size")
    p.add_argument("--pot", action="store_true", help="round to the nearest power of two")
    p.add_argument("--filter", choices=sorted(FILTERS), default="lanczos")
    p.set_defaults(func=cmd_resize)

    p = sub.add_parser("array", help="stack layers into a vertical strip (Godot Texture2DArray)",
                       description="Stack N images (resized to --size) top-to-bottom; layer i is image i. "
                                   "Import in Godot as Texture2DArray with slices/vertical=N "
                                   "(--godot-import writes that .import file).")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--size", default=None, help="layer size N or WxH (default: first image)")
    p.add_argument("--godot-import", action="store_true", help="write <out>.import for a Texture2DArray")
    p.add_argument("--no-mipmaps", action="store_true")
    p.set_defaults(func=cmd_array)

    p = sub.add_parser("atlas", help="grid atlas + JSON of cell rects/UVs")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--size", default=None, help="cell size N or WxH (default: first image)")
    p.add_argument("--cols", type=int, default=0, help="columns (default: square-ish)")
    p.add_argument("--padding", type=int, default=0, help="edge-extended padding around each cell (px)")
    p.set_defaults(func=cmd_atlas)

    p = sub.add_parser("icon", help="make 128/64 px command-card icons",
                       description="Crop (auto: trims the uniform background and centres the subject), "
                                   "resize to --sizes, optional bevelled frame, optional greyed disabled "
                                   "variant. Writes <out>_<size>.png (and <out>_<size>_dis.png).")
    p.add_argument("input")
    p.add_argument("-o", "--out", required=True, help="output prefix, e.g. assets/icons/footman")
    p.add_argument("--sizes", default="128,64")
    p.add_argument("--crop", default="auto", help="auto | center | none | x,y,w,h")
    p.add_argument("--pad", type=float, default=0.08, help="padding around the auto/explicit crop (fraction)")
    p.add_argument("--zoom", type=float, default=1.0, help=">1 zooms in after cropping, <1 zooms out")
    p.add_argument("--threshold", type=float, default=28.0, help="auto crop: colour distance from background")
    p.add_argument("--bg", default="auto", help="auto | transparent | #rrggbb (fill for padding / alpha)")
    p.add_argument("--frame", default=None, help="frame colour, e.g. '#b08d3c' (bevelled border)")
    p.add_argument("--bevel", type=float, default=0.06, help="frame width as a fraction of the size")
    p.add_argument("--disabled", action="store_true", help="also write greyed *_dis.png variants")
    p.set_defaults(func=cmd_icon)

    p = sub.add_parser("palette-match", help="shift colours toward a reference image",
                       description="Colour transfer in CIE Lab. 'stats' (default) matches mean/std per channel "
                                   "(Reinhard), 'hist' matches the full per-channel histogram. --strength blends "
                                   "with the original; --keep-luminance only touches a*/b* (hue/saturation).")
    io_args(p)
    p.add_argument("--ref", required=True, help="reference image")
    p.add_argument("--mode", choices=["stats", "hist"], default="stats")
    p.add_argument("--strength", type=float, default=0.7)
    p.add_argument("--keep-luminance", action="store_true")
    p.add_argument("--suffix", default="", help="file-name suffix when using --out-dir")
    p.set_defaults(func=cmd_palette_match)
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    res = a.func(a)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
