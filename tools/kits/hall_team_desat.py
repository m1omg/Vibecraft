#!/usr/bin/env python3
"""Grey the TEAM texels of an already-processed AI building GLB in place (no re-processing).

    python3 tools/kits/hall_team_desat.py assets/models/buildings/kingdom_moot_hall.glb \
        assets/models/buildings/clans_shell_hall.glb

The AI halls were processed with `process_model.py --team-mask 300` but without --team-desaturate, so
their TEAM material samples magenta texels: UnitView's albedo multiply then turns the pennants and
hangings black-magenta under most player colours. This tool takes the per-texel team mask written next
to the GLB (<name>_team.png, L8 in base-colour UVs), dilates it by 2 px, replaces the masked texels by a
luminance-preserving light grey (bible 3.1 rule 6: value ~0.62 for cloth; the same formula as
process_model's --team-desaturate) and rewrites only the embedded base-colour image. Geometry, UVs and
materials stay byte-identical. Idempotent: a texture whose masked texels are already grey is left alone.
"""
from __future__ import annotations

import io
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageFilter


def read_glb(path):
    b = open(path, "rb").read()
    magic, ver, total = struct.unpack("<III", b[:12])
    assert magic == 0x46546C67 and ver == 2, "not a GLB v2"
    jl, jt = struct.unpack("<II", b[12:20])
    js = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl, bt = struct.unpack("<II", b[off:off + 8])
    return js, bytearray(b[off + 8:off + 8 + bl])


def write_glb(path, js, bin_):
    while len(bin_) % 4:
        bin_.append(0)
    js["buffers"][0]["byteLength"] = len(bin_)
    j = json.dumps(js, separators=(",", ":")).encode()
    while len(j) % 4:
        j += b" "
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(bin_)))
        f.write(struct.pack("<II", len(j), 0x4E4F534A))
        f.write(j)
        f.write(struct.pack("<II", len(bin_), 0x004E4942))
        f.write(bytes(bin_))


def replace_view(js, bin_, vi, data):
    """Replace bufferView vi's bytes, shifting the views behind it (4-byte aligned)."""
    bv = js["bufferViews"][vi]
    o, n = bv.get("byteOffset", 0), bv["byteLength"]
    pad = (-len(data)) % 4
    new = bytes(data) + b"\0" * pad
    old_span = n + ((-n) % 4)
    delta = len(new) - old_span
    out = bytearray(bin_[:o]) + new + bin_[o + old_span:]
    bv["byteLength"] = len(data)
    for k, v in enumerate(js["bufferViews"]):
        if k != vi and v.get("byteOffset", 0) > o:
            v["byteOffset"] = v.get("byteOffset", 0) + delta
    return out


def desat(path):
    js, bin_ = read_glb(path)
    stem = os.path.splitext(path)[0]
    mpath = stem + "_team.png"
    if not os.path.exists(mpath):
        return {"file": path, "skipped": "no _team.png mask"}
    team_mats = {i for i, m in enumerate(js["materials"]) if "TEAM" in m.get("name", "")}
    tex_ids = set()
    for i in team_mats:
        t = js["materials"][i].get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if t:
            tex_ids.add(js["textures"][t["index"]]["source"])
    res = []
    for ii in sorted(tex_ids):
        img = js["images"][ii]
        vi = img["bufferView"]
        bv = js["bufferViews"][vi]
        raw = bytes(bin_[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        mask = Image.open(mpath).convert("L").resize(im.size, Image.NEAREST)
        mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.8))
        m = np.asarray(mask, np.float32)[..., None] / 255.0
        rgb = np.asarray(im, np.float32)
        mx, mn = rgb.max(2), rgb.min(2)
        sat = np.where(mx > 1, (mx - mn) / np.maximum(mx, 1), 0)
        sel = m[..., 0] > 0.5
        if sel.any() and float(sat[sel].mean()) < 0.12:
            res.append({"image": img.get("name"), "skipped": "already grey"})
            continue
        lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        grey = np.clip(lum * 1.15, 0, 255)
        out = rgb * (1 - m) + np.repeat(grey, 3, axis=2) * m
        buf = io.BytesIO()
        mime = img.get("mimeType", "image/jpeg")
        Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGB").save(
            buf, "PNG" if mime == "image/png" else "JPEG", quality=92, subsampling=0, optimize=False)
        bin_ = replace_view(js, bin_, vi, buf.getvalue())
        res.append({"image": img.get("name"), "team_texels": int(sel.sum()), "mean_sat_before": round(float(sat[sel].mean()), 3)})
    if any("team_texels" in r for r in res):
        write_glb(path, js, bin_)
    return {"file": path, "images": res}


if __name__ == "__main__":
    print(json.dumps([desat(p) for p in sys.argv[1:]], indent=2))
