#!/usr/bin/env python3
"""Procedural Greenvale doodads and neutral structures for Vibecraft (bpy, no paid API calls).

    PY=/opt/bpyenv/v313/bin/python
    $PY tools/kits/doodads.py                       # build everything + manifest
    $PY tools/kits/doodads.py --only tree_hill_oak,gold_mine
    $PY tools/kits/doodads.py --list
    python3 tools/kits/lineup.py                    # line-up render -> tests/output/doodads_lineup.png

Outputs
  assets/models/doodads/<id>.glb        trees (+ <id>_lod1), rocks, walls, hedges, props, creep-camp kit
  assets/models/neutral/<id>.glb        gold_mine (Gold Seam), neutral_weighstall, neutral_hale_spring
  assets/models/doodads/manifest.json   id, path, size, tris, pathing footprint suggestion, sway, nodes ...

Conventions (what the game can rely on; see also tools/kits/doodads_lib.py)
  * 1 unit = 1 m, Y up, origin at the footprint centre on the ground, the front (door, adit, stall
    counter) faces -Z. Built Z-up/front +Y and converted on write.
  * Materials are named `<id>_<key>[_SWAY][_GLOW|_LAMP|_EMBER|_WATER|_GLYPH]`. No TEAM material: neutrals
    and doodads never carry team colour (art bible §3.1 rule 8).
  * SWAY materials (foliage): alpha scissor (glTF MASK, cutoff in the material), double sided,
    COLOR_0 = (R sway weight 0 at trunk base -> 1 at canopy edge, G painted AO, B cluster phase, A 1).
    Reference shader: tools/kits/foliage_sway.gdshader.
  * Every other material: COLOR_0 RGB = painted AO / base darkening / moss tint (multiply), A = 1.
  * TEXCOORD_1 (UV2) on every vertex of every asset: x = sway weight (0 on rigid props), y = normalized
    height (0 ground .. 1 top) for the build_progress / collapse reveal shader:
        discard if UV2.y > build_progress (plus a noisy band for a scaffold-coloured edge).
  * GLOW / LAMP / EMBER / GLYPH materials are emissive (emissiveTexture = baseColor texture, factor in
    the material). The game pulses them by scaling `emission_energy` (Gold Seam veins when a worker
    enters, lanterns and windows at night).
  * Animated parts are separate glTF nodes with their pivot as the node origin (listed in the
    manifest `nodes`): windlass drum, balance beam and pans, waterwheel.
  * Texel density ~128 px/m (box / cylinder / grain-aligned projection, `Mat.repeat` metres per
    texture repeat at `Mat.size` px).
  * Deterministic: seeded numpy / mathutils noise only, a deterministic GLB writer; re-running
    produces byte-identical files.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zlib

import bpy  # noqa: F401  (bmesh / mathutils need the module)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import doodads_lib as L  # noqa: E402
from doodads_lib import Asset, Mat, Part, hexcol, nrm, smoothstep, lerp  # noqa: E402,F401

import numpy as np  # noqa: E402

REPO = L.REPO
OUT_DOODADS = os.path.join(REPO, "assets", "models", "doodads")
OUT_NEUTRAL = os.path.join(REPO, "assets", "models", "neutral")
log = L.log


def seed_of(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


# =============================================================================================
# materials (shared definitions; each GLB embeds its own copy of the textures it uses)
# =============================================================================================

TEX = "assets/textures/terrain/"
SW = "assets_src/textures/materials/"
FOL = "assets/textures/foliage/"


def M_bark():
    return Mat("bark", L.swatch(TEX + "bark_oak.png", seamless=False, sat=0.85), repeat=2.0, size=256)


def M_bark_hazel():
    # hazel: smooth grey-brown bark (desaturated, lighter, finer)
    return Mat("bark", L.swatch(TEX + "bark_oak.png", seamless=False, sat=0.45, tint=(1.05, 1.0, 0.95),
                                gamma=0.85), repeat=1.2, size=256)


def M_leaves(kind="oak"):
    if kind == "oak":
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.8, 0.95, 0.9), sat=0.78, val=0.84)
    elif kind == "linden":
        img = L.foliage_atlas(FOL + "linden_clumps.png", hue_tint=(0.98, 1.02, 0.84), sat=0.82, val=0.98)
    elif kind == "hazel":
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.9, 0.98, 0.86), sat=0.7, val=0.92)
    elif kind == "hawthorn":
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.86, 0.95, 0.88), sat=0.72, val=0.8,
                              blossom=["#F4EFE0", "#EDE6D2", "#F6F1E6"], seed=7)
    else:
        raise ValueError(kind)
    return Mat("leaves", img, size=512, alpha=True, cutoff=0.42, double=True, sway=True)


def M_rings():
    return Mat("endgrain", L.tex_rings(5, 256), repeat=1.0, size=256)


# =============================================================================================
# small geometry helpers on top of doodads_lib
# =============================================================================================

def fib_dirs(n, seed=0):
    """n roughly even unit directions on the sphere (Fibonacci), randomly rotated (deterministic)."""
    i = np.arange(n) + 0.5
    z = 1 - 2 * i / n
    r = np.sqrt(np.maximum(0, 1 - z * z))
    a = i * math.pi * (3 - math.sqrt(5))
    d = np.stack([r * np.cos(a), r * np.sin(a), z], axis=1)
    rng = np.random.default_rng(seed)
    R = L.rot_matrix(*rng.uniform(0, 360, 3))
    return d @ R.T


def orient(n, up=(0, 0, 1), roll=0.0):
    """3x3 mapping card-local axes (X right, -Y normal, Z up) so that the card normal becomes n."""
    n = nrm(np.asarray(n, float))
    up = np.asarray(up, float)
    u = up - n * np.dot(up, n)
    if np.linalg.norm(u) < 1e-4:
        u = np.array([0.0, 1.0, 0.0]) - n * n[1]
    u = nrm(u)
    if roll:
        u = np.array(L.axis_angle(n, roll)) @ u
    Y = -n
    Z = u
    X = np.cross(Y, Z)
    return np.stack([X, Y, Z], axis=1)


def cell_rect(i, grid=2):
    cx, cy = i % grid, i // grid
    s = 1.0 / grid
    return (cx * s, cy * s, cx * s + s, cy * s + s)


def cell_centre(i, grid=2):
    u0, v0, u1, v1 = cell_rect(i, grid)
    return np.array([(u0 + u1) / 2, (v0 + v1) / 2])


def bezier(p0, p1, p2, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.asarray(x, float) for x in (p0, p1, p2))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2


def ngon(n, r=1.0, a0=0.0, jitter=0.0, seed=0):
    rng = np.random.default_rng(seed)
    c = L.circle(n, r, a0)
    if jitter:
        c = c * (1 + rng.uniform(-jitter, jitter, (n, 1)))
    return c


# =============================================================================================
# trees
# =============================================================================================

def trunk(mat, height, r_base, r_top, seed, sides=9, flare=0.55, roots=5, root_amp=0.38, lean=(0.0, 0.0),
          rings=None, jitter=0.025, cap=True):
    """Tapered bark trunk with a root flare (radial lobes at the base) and a slight lean."""
    rng = np.random.default_rng(seed)
    zs = rings if rings is not None else [0.0, 0.1, 0.28, 0.6, 1.1, 1.7, 2.3, height]
    zs = [z for z in zs if z < height - 1e-3] + [height]
    prof = []
    for z in zs:
        t = z / height
        r = r_top + (r_base - r_top) * (1 - t) ** 1.6
        r += flare * r_base * math.exp(-z / 0.32)
        prof.append((r, z))
    parts = L.lathe(prof, sides, mat, a0=rng.uniform(0, 1), cap_top=cap)
    p = parts[0]
    v = p.v
    th = np.arctan2(v[:, 1], v[:, 0])
    z = v[:, 2]
    ph = rng.uniform(0, 6.28)
    lobes = np.maximum(0, np.cos(roots * th + ph)) ** 3 * root_amp * np.exp(-z / 0.3)
    v[:, 0] *= 1 + lobes
    v[:, 1] *= 1 + lobes
    t = np.clip(z / height, 0, 1)
    v[:, 0] += lean[0] * t * t
    v[:, 1] += lean[1] * t * t
    p.v = v
    p.jitter(jitter, seed + 1, freq=2.5)
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    return p


def branch(mat, p0, p1, p2, r0, r1, seed, sides=5, n=5):
    path = bezier(p0, p1, p2, n)
    scales = np.linspace(r0, r1, n)
    prof = ngon(sides, 1.0, seed * 0.37 % 1.0)
    parts = L.sweep(prof, path, mat, scales=scales, cap0=False, cap1=True)
    return parts


def leaf_cluster(mat, c, R, seed, n_cards=12, cells=(0, 1, 2, 3), card_scale=1.2, segs=(2, 2), bend=0.28,
                 hull=True, hull_subdiv=1, hull_scale=0.5, down_keep=0.3, offset=0.62, squash=0.88,
                 upright=0.25):
    """One leaf clump cluster: outward-facing bent alpha cards on a sphere + a small leafy hull that
    blocks see-through (mapped into the fully opaque centre of an atlas cell; it sits in the dark
    interior, so its coarse texel density never shows). Normals point away from a point a little
    below the cluster centre (soft painted volume, lit tops)."""
    rng = np.random.default_rng(seed)
    c = np.asarray(c, float)
    parts = []
    for d in fib_dirs(n_cards, seed):
        if d[2] < -0.45 and rng.random() > down_keep:
            continue
        size = R * card_scale * rng.uniform(0.85, 1.12)
        cell = int(cells[rng.integers(len(cells))])
        p = L.card(size, size, mat, cell_rect(cell), segs=segs, bend=bend)
        n = nrm(d + rng.normal(0, 0.22, 3) + np.array([0, 0, upright]))
        M = orient(n, (0, 0, 1), rng.uniform(-35, 35))
        pos = c + d * np.array([1, 1, squash]) * R * offset
        p.xf(m=M, t=pos)
        p.nmode = "sphere"
        p.ncenter = c - np.array([0, 0, R * 0.3])
        p.nblend = 0.9
        parts.append(p)
    if hull:
        parts.append(leaf_hull(mat, c, R * hull_scale, seed, cells, hull_subdiv, squash))
    return parts


def leaf_hull(mat, c, r, seed, cells=(0, 1, 2, 3), subdiv=1, squash=0.88):
    rng = np.random.default_rng(seed + 5)
    v, t = L.icosphere(subdiv, 1.0)
    d = nrm(v)
    off = (seed % 97 * 0.31, seed % 89 * 0.17, seed % 83 * 0.23)
    k = 1 + 0.18 * L.noise1(v, 1.6, off)
    v = v * k[:, None] * r * np.array([1, 1, squash]) + c
    cell = int(cells[rng.integers(len(cells))])
    cc = cell_centre(cell) + rng.uniform(-0.02, 0.02, 2)
    uv = (cc + np.stack([d[:, 0] * 0.1 + d[:, 1] * 0.035, -d[:, 2] * 0.1], axis=1))[t]
    hp = Part(v, t, mat, uv, 180.0)
    hp.nmode = "sphere"
    hp.ncenter = c
    hp.nblend = 0.95
    hp.occ = 0.5
    hp.ao = False
    return hp


def star_cluster(mat, c, R, seed, cells=(0, 1, 2, 3), squash=0.88):
    """Low LOD / impostor-friendly cluster: a tilted top card + three crossed upright cards and a
    tiny hull. Few, large, overlapping silhouettes: reads the same from every yaw, bakes cleanly."""
    rng = np.random.default_rng(seed)
    c = np.asarray(c, float)
    parts = []
    a0 = rng.uniform(0, 180)
    for k in range(3):
        a = math.radians(a0 + k * 60)
        n = np.array([math.cos(a), math.sin(a), 0.35])
        p = L.card(R * 2.05, R * 2.05 * squash, mat, cell_rect(int(cells[(k + seed) % len(cells)])), segs=(1, 1))
        p.xf(m=orient(n, (0, 0, 1), rng.uniform(-10, 10)), t=c)
        parts.append(p)
    p = L.card(R * 2.1, R * 2.1, mat, cell_rect(int(cells[seed % len(cells)])), segs=(1, 1))
    p.xf(m=orient((0.15, 0.25, 1.0), (0, 1, 0), rng.uniform(0, 360)), t=c + np.array([0, 0, R * 0.35 * squash]))
    parts.append(p)
    parts.append(leaf_hull(mat, c, R * 0.55, seed, cells, 0, squash))
    for q in parts:
        q.nmode = "sphere"
        q.ncenter = c - np.array([0, 0, R * 0.3])
        q.nblend = 0.92
    return parts


def foliage_ao(c, R, zlo, zhi, inner=0.42, low=0.7, gain=1.0):
    c = np.asarray(c, float)

    def fn(p):
        d = np.linalg.norm(p.v - c, axis=1) / R
        a = inner + (1 - inner) * smoothstep(0.15, 1.05, d)
        h = low + (1 - low) * smoothstep(zlo, zhi, p.v[:, 2])
        return a * h * gain
    return fn


def canopy_sway(H, Rmax):
    def fn(v, p):
        r = np.hypot(v[:, 0], v[:, 1])
        return np.clip(0.62 * v[:, 2] / H + 0.5 * r / Rmax, 0, 1) ** 1.25
    return fn


def rigid_sway(H, k=0.3):
    """Small sway weights for bark (UV2.x only): the trunk bends a little with the crown."""
    def apply(p):
        p.sway = np.clip(p.v[:, 2] / H, 0, 1) ** 2 * k
    return apply


class TreeSpec:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def build_tree(aid, spec: TreeSpec, lod=0):
    """Generic broadleaf: trunk with root flare, branches into each cluster, clusters of cards."""
    seed = seed_of(aid.replace("_lod1", ""))
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.4, ao_strength=0.9, base_dark=0.5, base_h=0.5, top_light=0.18)
    bark, leaves = spec.bark(), spec.leaves()
    clusters = spec.clusters
    zlo = min(c[2] - R for c, R in clusters)
    zhi = max(c[2] + R for c, R in clusters)
    rmax = max(np.hypot(c[0], c[1]) + R for c, R in clusters)
    H = zhi
    sw_bark = rigid_sway(H)
    stems = spec.stems if hasattr(spec, "stems") else None
    if stems is None:
        sides = 9 if lod == 0 else 5
        rings = None if lod == 0 else [0.0, 0.25, 1.0, spec.trunk_h]
        tp = trunk(bark, spec.trunk_h, spec.r_base, spec.r_top, seed, sides=sides, flare=spec.flare,
                   roots=spec.roots, lean=spec.lean, rings=rings)
        sw_bark(tp)
        A.add(tp)
        top = np.array([spec.lean[0], spec.lean[1], spec.trunk_h])
        if lod == 0:
            for i, (c, R) in enumerate(clusters):
                c = np.asarray(c, float)
                dirxy = c[:2] - top[:2]
                p0 = top - np.array([0, 0, 0.35]) + np.r_[nrm(dirxy) * spec.r_top * 0.3 if np.linalg.norm(dirxy) > 0.1 else np.zeros(2), 0]
                p2 = c - np.array([0, 0, R * 0.35])
                p1 = p0 + (p2 - p0) * np.array([0.35, 0.35, 0.75])
                for bp in branch(bark, p0, p1, p2, spec.r_top * 0.62, spec.r_top * 0.16, seed + i, sides=5):
                    sw_bark(bp)
                    A.add(bp)
    else:
        # coppice: several thin stems splaying out of a low stool
        stool = trunk(bark, 0.35, spec.r_base, spec.r_base * 0.8, seed, sides=8 if lod == 0 else 5, flare=0.4,
                      roots=4, rings=[0.0, 0.12, 0.35])
        sw_bark(stool)
        A.add(stool)
        for i, (base, tip, r) in enumerate(stems):
            if lod and i % 2:
                continue
            base, tip = np.asarray(base, float), np.asarray(tip, float)
            mid = base + (tip - base) * np.array([0.3, 0.3, 0.55])
            for bp in branch(bark, base, mid, tip, r, r * 0.35, seed + 11 * i, sides=5 if lod == 0 else 4,
                             n=5 if lod == 0 else 3):
                sw_bark(bp)
                A.add(bp)
    # leaves
    for i, (c, R) in enumerate(clusters):
        if lod == 0:
            parts = leaf_cluster(leaves, c, R, seed + 101 * i, n_cards=spec.cards, card_scale=spec.card_scale,
                                 cells=spec.cells, bend=0.28, hull=True, hull_subdiv=1, squash=spec.squash)
        else:
            parts = star_cluster(leaves, c, R, seed + 101 * i, cells=spec.cells, squash=spec.squash)
        ph = (i * 0.618 + rng.uniform(0, 0.2)) % 1.0
        for p in parts:
            p.ao_fn = foliage_ao(c, R, zlo, zhi) if lod == 0 else foliage_ao(c, R, zlo, zhi, inner=0.35, low=0.6, gain=0.8)
            p.phase = ph
            A.add(p)
    # sway weight over the whole canopy: ~0.2 where leaves meet the trunk top, 1.0 at the outermost edge
    leaf = [p for p in A.parts if p.mat.sway]
    allv = np.concatenate([p.v for p in leaf])
    top = allv[:, 2].max()
    rr = np.hypot(allv[:, 0], allv[:, 1]).max()

    def raw(v):
        return 0.6 * v[:, 2] / top + 0.55 * np.hypot(v[:, 0], v[:, 1]) / rr
    m = raw(allv).max()
    for p in leaf:
        p.sway = np.clip(raw(p.v) / m, 0, 1) ** 1.2
    A.extras = {"kind": "tree", "lod": lod}
    return A


def spec_oak(seed):
    rng = np.random.default_rng(seed)
    cl = [((0.1, -0.05, 4.5), 1.95)]
    n = 5
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
        rr = rng.uniform(1.65, 1.85)
        z = rng.uniform(3.3, 3.7)
        R = rng.uniform(1.6, 1.75)
        cl.append(((math.cos(a) * rr, math.sin(a) * rr, z), R))
    for k in (0.5, 2.5):          # fillers between ring clusters, a little higher
        a = a0 + k * 2 * math.pi / n
        cl.append(((math.cos(a) * 1.05, math.sin(a) * 1.05, 4.25), 1.3))
    return TreeSpec(bark=M_bark, leaves=lambda: M_leaves("oak"), clusters=cl, trunk_h=2.05, r_base=0.42,
                    r_top=0.3, flare=0.55, roots=5, lean=(0.08, -0.05), cards=12, card_scale=1.15,
                    cells=(0, 1, 2, 3), squash=0.86)


def spec_linden(seed):
    rng = np.random.default_rng(seed)
    cl = []
    a0 = rng.uniform(0, 6.28)
    for k in range(4):
        a = a0 + k * math.pi / 2 + rng.uniform(-0.2, 0.2)
        cl.append(((math.cos(a) * 1.35, math.sin(a) * 1.35, 2.85 + rng.uniform(-0.15, 0.15)), 1.4))
    for k in range(3):
        a = a0 + 0.8 + k * 2 * math.pi / 3
        cl.append(((math.cos(a) * 0.8, math.sin(a) * 0.8, 4.2 + rng.uniform(-0.1, 0.1)), 1.2))
    cl.append(((0.05, 0.0, 5.45), 1.0))
    return TreeSpec(bark=M_bark, leaves=lambda: M_leaves("linden"), clusters=cl, trunk_h=2.35, r_base=0.34,
                    r_top=0.24, flare=0.5, roots=5, lean=(-0.05, 0.04), cards=11, card_scale=1.2,
                    cells=(0, 1, 2, 3), squash=0.95)


def spec_hazel(seed):
    rng = np.random.default_rng(seed)
    stems = []
    n = 7
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
        rb = 0.12
        rt = rng.uniform(0.75, 1.05)
        h = rng.uniform(1.9, 2.4)
        stems.append(((math.cos(a) * rb, math.sin(a) * rb, 0.2), (math.cos(a) * rt, math.sin(a) * rt, h),
                      rng.uniform(0.05, 0.07)))
    cl = [((0.0, 0.0, 2.35), 0.95)]
    for k in range(5):
        a = a0 + 0.3 + k * 2 * math.pi / 5 + rng.uniform(-0.2, 0.2)
        cl.append(((math.cos(a) * 0.95, math.sin(a) * 0.95, rng.uniform(1.75, 2.15)), rng.uniform(0.72, 0.85)))
    return TreeSpec(bark=M_bark_hazel, leaves=lambda: M_leaves("hazel"), clusters=cl, stems=stems, r_base=0.3,
                    cards=10, card_scale=1.25, cells=(0, 1, 2, 3), squash=0.9)


# =============================================================================================
# painted procedural textures (tileable)
# =============================================================================================

def _wrap_voronoi(n, pts):
    """F1, F2 distances (pixels) and nearest index on a wrapped n x n grid."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    f1 = np.full((n, n), 1e9, np.float32)
    f2 = np.full((n, n), 1e9, np.float32)
    idx = np.zeros((n, n), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px)
        dx = np.minimum(dx, n - dx)
        dy = np.abs(yy - py)
        dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        idx = np.where(closer, i, idx)
        f1 = np.where(closer, d, f1)
    return f1, f2, idx


def tex_rock(seed=3, n=512, base="#6F6A60", dark="#4A4640", light="#8E887C", lichen="#AAB061", moss="#5B7A43",
             cells=34, lichen_amt=1.0, moss_amt=1.0, warm=(1.0, 1.0, 1.0)):
    """Hand-painted stone: chiselled facets (flat value per Voronoi cell, lit upper edge, dark
    crack between cells), soft value patches, sparse lichen dots and moss in the cracks. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        pts = rng.uniform(0, n, (cells, 2))
        f1, f2, idx = _wrap_voronoi(n, pts)
        edge = f2 - f1
        cell_val = rng.uniform(-1, 1, cells)[idx]
        low = L.periodic_noise(n, seed + 1, 2.8)
        mid = L.periodic_noise(n, seed + 2, 1.8)
        hi = L.periodic_noise(n, seed + 3, 1.0)
        b, dk, lt = hexcol(base), hexcol(dark), hexcol(light)
        t = np.clip(0.5 + 0.12 * cell_val + 0.45 * (low - 0.5) + 0.25 * (mid - 0.5), 0, 1)[..., None]
        col = np.where(t < 0.5, dk + (b - dk) * (t / 0.5), b + (lt - b) * ((t - 0.5) / 0.5))
        # facet edge light (top side of each crack) and dark cracks
        gy = np.roll(edge, 2, axis=0) - edge
        rim = np.clip(gy / 3.0, 0, 1) * (edge < 7)
        col = col + (lt - col) * (0.35 * rim)[..., None]
        crack = (1 - smoothstep(0.0, 2.6, edge)) * smoothstep(0.3, 0.6, mid)
        col = col * (1 - 0.45 * crack)[..., None]
        # moss in cracks and low patches, lichen dots on high spots
        m = np.clip(crack * 1.3 * smoothstep(0.45, 0.75, low) + smoothstep(0.78, 0.92, mid) * 0.6, 0, 1) * moss_amt
        mc = hexcol(moss) * (0.85 + 0.3 * hi)[..., None]
        col = col * (1 - m[..., None]) + mc * m[..., None]
        li = (smoothstep(0.74, 0.8, hi) * smoothstep(0.5, 0.7, low))[..., None] * 0.8 * lichen_amt
        col = col * (1 - li) + hexcol(lichen) * li
        col = col * (0.94 + 0.12 * hi)[..., None] * np.asarray(warm)
        return L.to_img(col)
    return lambda: L.cached_image(("rock", seed, n, base, dark, light, cells, lichen_amt, moss_amt, tuple(warm)), fn)


def tex_wattle(seed=13, n=256):
    """Woven hazel rods, horizontal (image rows = rods ~ 7.5 per repeat), shading alternates per
    stake gap to suggest the weave. Tileable in u; v covers the panel height once."""
    def fn():
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        rods = 7.5
        ph = yy / n * rods
        k = np.floor(ph)
        f = ph - k
        prof = np.sin(np.clip(f, 0, 1) * math.pi) ** 0.6
        weave = np.where((np.floor(xx / n * 3) + k) % 2 == 0, 1.0, 0.82)
        tone = rng.uniform(0.85, 1.12, int(rods) + 2)[k.astype(int)]
        bark = np.array([0.42, 0.33, 0.22]) * 1.15
        nz = L.periodic_noise(n, seed + 1, 1.4)
        col = bark[None, None, :] * (0.35 + 0.75 * prof * weave * tone + 0.12 * (nz - 0.5))[..., None]
        hl = np.exp(-((f - 0.3) / 0.08) ** 2) * 0.25
        col = col + np.array([0.75, 0.68, 0.52]) * hl[..., None] * weave[..., None]
        return L.to_img(col)
    return lambda: L.cached_image(("wattle", seed, n), fn)


def tex_strata(seed=17, n=512, base="#857A66", dark="#574E43", light="#A89C84", moss="#5B7A43"):
    """Layered sedimentary cliff face: horizontal beds of varying thickness and tone, lit top lips,
    dark undercut lines, vertical joints per bed, streaky grain, moss on some bed tops. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        b, dk, lt = hexcol(base), hexcol(dark), hexcol(light)
        # bed boundaries (tileable in v)
        th = []
        while sum(th) < n:
            th.append(int(rng.uniform(0.16, 0.34) * n))
        th[-1] -= sum(th) - n
        if th[-1] < 12:
            th[-2] += th[-1]
            th.pop()
        starts = np.cumsum([0] + th[:-1])
        bed = np.zeros(n, int)
        fpos = np.zeros(n)
        for i, (s0, t) in enumerate(zip(starts, th)):
            bed[s0:s0 + t] = i
            fpos[s0:s0 + t] = (np.arange(t) + 0.5) / t
        tone = rng.uniform(-1, 1, len(th))[bed]
        yy, xx = np.mgrid[0:n, 0:n]
        streak = L.periodic_noise(n, seed + 1, 1.8)
        streak = np.mean([np.roll(streak, k * 4, axis=1) for k in range(5)], axis=0)   # smear in x
        low = L.periodic_noise(n, seed + 2, 2.6)
        # chiselled facets inside the beds (flat value per Voronoi cell, squashed horizontally)
        pts = rng.uniform(0, n, (40, 2))
        f1, f2, idx = _wrap_voronoi(n, pts)
        cellv = rng.uniform(-1, 1, 40)[idx]
        t = np.clip(0.5 + 0.2 * tone[:, None] + 0.2 * cellv + 0.2 * (streak - 0.5) + 0.3 * (low - 0.5), 0, 1)[..., None]
        col = np.where(t < 0.5, dk + (b - dk) * (t / 0.5), b + (lt - b) * ((t - 0.5) / 0.5))
        f = fpos[:, None] * np.ones((1, n))
        lip = smoothstep(0.16, 0.0, f)[..., None]               # lit top of each bed
        under = smoothstep(0.82, 1.0, f)[..., None]             # shadowed underside
        col = col + (lt * 1.08 - col) * lip * 0.55
        col = col * (1 - 0.5 * under)
        # vertical joints per bed
        joint = np.zeros((n, n))
        for i, (s0, tk) in enumerate(zip(starts, th)):
            for _ in range(rng.integers(1, 4)):
                x0 = rng.uniform(0, n)
                dx = np.abs(((xx[s0:s0 + tk] - x0 + n / 2) % n) - n / 2) - rng.uniform(-1, 1) * (yy[s0:s0 + tk] - s0) * 0.15
                joint[s0:s0 + tk] = np.maximum(joint[s0:s0 + tk], smoothstep(2.6, 0.6, np.abs(dx)))
        col = col * (1 - 0.55 * joint)[..., None]
        crack = 1 - smoothstep(0.0, 2.2, f2 - f1)
        col = col * (1 - 0.35 * crack * smoothstep(0.35, 0.6, low))[..., None]
        # moss on some bed tops
        mz = (smoothstep(0.25, 0.0, f) * smoothstep(0.55, 0.8, low))[..., None] * 0.8
        col = col * (1 - mz) + hexcol(moss) * (0.85 + 0.3 * streak)[..., None] * mz
        return L.to_img(col)
    return lambda: L.cached_image(("strata", seed, n, base, dark, light), fn)


def M_rock(key="rock", seed=3, **kw):
    return Mat(key, tex_rock(seed, 512, **kw), repeat=2.4, size=256)


def M_drystone():
    return Mat("drystone", L.swatch(SW + "neutral_drystone.png", seamless=True, sat=0.85), repeat=2.0, size=256)


# =============================================================================================
# rocks
# =============================================================================================

def moss_tint(p, amount=1.0, seed=0, col=(0.5, 0.78, 0.3), up=0.45, patch=0.0):
    """Moss caps by vertex colour: upward-facing, noisy patches multiply the albedo green.
    `patch` raises the noise threshold (0 = most of the cap, 0.3 = scattered patches)."""
    vn = L.vertex_normals(p.v, p.t)
    nz = L.noise1(p.v, 1.6, (seed * 0.13 % 7, 3.1, 1.7))
    cap = smoothstep(up, up + 0.22, vn[:, 2])
    m = cap * smoothstep(patch - 0.07, patch + 0.07, nz) * amount
    p.tint = p.tint * (1 - m[:, None]) + np.asarray(col)[None, :] * m[:, None]
    return p


def build_boulder(aid, kind):
    """Mossy flat-topped boulder: chiselled facets, dark base, lit top lip, crisp moss caps."""
    seed = seed_of(aid)
    A = Asset(aid, seed, ao_dist=0.8, ao_strength=1.0, base_dark=0.42, base_h=0.55, top_light=0.28)
    mat = M_rock(base="#615C53", dark="#3F3C37", light="#8A8274", cells=30)
    moss = dict(col=(0.36, 0.6, 0.2), up=0.62)
    if kind == "small":
        p = L.blob(mat, 0.52, scale=(1.0, 0.82, 0.72), seed=seed, noise_amp=0.14, noise_freq=1.3, flat_top=0.8,
                   flat_bottom=0.1, cuts=5, cut_depth=0.16, smooth=26, sphere="uv", segs=(10, 7))
        A.add(moss_tint(p, 0.95, seed, patch=0.0, **moss))
    elif kind == "medium":
        p = L.blob(mat, 0.8, subdiv=3, scale=(1.0, 0.8, 0.62), seed=seed, noise_amp=0.15, noise_freq=1.25,
                   flat_top=0.8, flat_bottom=0.08, cuts=7, cut_depth=0.13, smooth=26)
        A.add(moss_tint(p, 0.95, seed, patch=-0.05, **moss))
    else:
        p = L.blob(mat, 1.15, subdiv=3, scale=(1.0, 0.78, 0.6), seed=seed, noise_amp=0.15, noise_freq=1.2,
                   flat_top=0.82, flat_bottom=0.08, cuts=8, cut_depth=0.12, smooth=26)
        A.add(moss_tint(p, 0.95, seed, patch=-0.05, **moss))
        q = L.blob(mat, 0.42, scale=(1.0, 0.85, 0.7), seed=seed + 3, noise_amp=0.15, flat_top=0.8, flat_bottom=0.1,
                   cuts=4, smooth=34, sphere="uv", segs=(8, 5))
        q.rot(rz=40).move(0.95, -0.75, 0.0)
        A.add(moss_tint(q, 0.9, seed + 3, patch=0.05, **moss))
    for q in A.parts:
        q.move(z=-0.04)
    return A


# =============================================================================================
# drystone walls (2 m modules; straight spans X -1..1 on the tile centre line)
# =============================================================================================

WALL_H, WALL_W0, WALL_W1 = 1.0, 0.74, 0.5


def wall_profile(h=WALL_H, w0=WALL_W0, w1=WALL_W1):
    a, b = w0 / 2, w1 / 2
    return np.array([(a, 0.0), (a * 0.97 + b * 0.03, h * 0.35), (a * 0.6 + b * 0.4, h * 0.7), (b + 0.02, h - 0.05),
                     (b - 0.04, h), (-b + 0.04, h), (-b - 0.02, h - 0.05), (-(a * 0.6 + b * 0.4), h * 0.7),
                     (-(a * 0.97 + b * 0.03), h * 0.35), (-a, 0.0)])


def wall_core(mat, p0, p1, seed, heights=None, nx=7):
    """Battered drystone core swept from p0 to p1 (ground points); heights: per-station scale."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    path = np.stack([np.linspace(p0[i], p1[i], nx + 1) for i in range(3)], axis=1)
    prof = wall_profile()
    sc = np.ones((nx + 1, 2))
    if heights is not None:
        sc[:, 1] = heights
    parts = L.sweep(prof, path, mat, scales=sc, up=(0, 0, 1), cap0=True, cap1=True)
    p = parts[0]
    p.jitter((0.035, 0.035, 0.03), seed, freq=2.2)
    p.jitter((0.012, 0.012, 0.012), seed + 1)
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    p.uv = L.uv_box(p.v, p.t, mat.repeat, (seed % 7 * 0.13, 0.0))
    p.smooth = 30.0
    return p


def coping(mat, p0, p1, seed, h=WALL_H, w=WALL_W1, keep=None):
    """Vertical 'cock and hen' coping stones along the wall top."""
    rng = np.random.default_rng(seed)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L_ = np.linalg.norm(p1 - p0)
    d = (p1 - p0) / L_
    ang = math.degrees(math.atan2(d[1], d[0]))
    parts = []
    s = 0.04
    i = 0
    while s < L_ - 0.04:
        t = rng.uniform(0.11, 0.17)
        if keep is not None and not keep(s / L_):
            s += t + 0.02
            continue
        tall = rng.uniform(0.2, 0.26) if i % 2 == 0 else rng.uniform(0.27, 0.36)
        b = L.box((t, w + rng.uniform(0.0, 0.08), tall), mat, center=(0, 0, tall / 2))
        b.rot(ry=rng.uniform(-9, 9), rx=rng.uniform(-5, 5))
        hloc = h - 0.04 if keep is None else h
        b.move(z=hloc)
        b.rot(rz=ang)
        b.move(*(p0 + d * (s + t / 2)))
        b.jitter(0.012, seed + i)
        b.uv = L.uv_box(b.v, b.t, mat.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        b.smooth = 20
        parts.append(b)
        s += t + 0.015
        i += 1
    return parts


def through_stones(mat, p0, p1, seed, n=3, h=WALL_H):
    rng = np.random.default_rng(seed)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    ang = math.degrees(math.atan2(d[1], d[0]))
    parts = []
    for k in range(n):
        t = rng.uniform(0.15, 0.85)
        z = rng.uniform(0.3, 0.65) * h
        b = L.box((rng.uniform(0.25, 0.4), WALL_W0 + 0.16, rng.uniform(0.06, 0.09)), mat, center=(0, 0, 0))
        b.rot(rx=rng.uniform(-4, 4), rz=rng.uniform(-8, 8) + ang).move(*(p0 + (p1 - p0) * t + np.array([0, 0, z])))
        b.jitter(0.01, seed + k)
        b.uv = L.uv_box(b.v, b.t, mat.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        parts.append(b)
    return parts


def wall_asset(aid):
    seed = seed_of(aid)
    A = Asset(aid, seed, ao_dist=0.6, ao_strength=1.0, base_dark=0.55, base_h=0.35, top_light=0.15)
    return A, seed


def build_wall_straight(aid):
    A, seed = wall_asset(aid)
    m = M_drystone()
    p0, p1 = (-1.0, 0, 0), (1.0, 0, 0)
    A.add(moss_tint(wall_core(m, p0, p1, seed), 0.7, seed, up=0.55))
    for c in coping(m, p0, p1, seed + 1):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    A.add(through_stones(m, p0, p1, seed + 2))
    return A


def build_wall_corner(aid):
    """Joins a straight on the west (-X) and one on the north (Godot -Z)."""
    A, seed = wall_asset(aid)
    m = M_drystone()
    A.add(moss_tint(wall_core(m, (-1.0, 0, 0), (WALL_W0 / 2, 0, 0), seed, nx=5), 0.7, seed, up=0.55))
    A.add(moss_tint(wall_core(m, (0, WALL_W0 / 2 - 0.02, 0), (0, 1.0, 0), seed + 5, nx=3), 0.7, seed + 5, up=0.55))
    for c in coping(m, (-1.0, 0, 0), (WALL_W1 / 2, 0, 0), seed + 1):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    for c in coping(m, (0, WALL_W1 / 2 + 0.02, 0), (0, 1.0, 0), seed + 3):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    A.add(through_stones(m, (-1.0, 0, 0), (0, 0, 0), seed + 2, n=2))
    return A


def build_wall_broken(aid):
    """Broken end: full height at -X, crumbling to knee height toward +X, tumbled stones."""
    A, seed = wall_asset(aid)
    rng = np.random.default_rng(seed)
    m = M_drystone()
    nx = 8
    xs = np.linspace(-1, 1, nx + 1)
    hs = np.where(xs < -0.1, 1.0, np.clip(1.0 - (xs + 0.1) * 0.62 + rng.uniform(-0.08, 0.08, nx + 1), 0.28, 1.0))
    A.add(moss_tint(wall_core(m, (-1.0, 0, 0), (1.0, 0, 0), seed, heights=hs, nx=nx), 0.8, seed, up=0.5))
    for c in coping(m, (-1.0, 0, 0), (1.0, 0, 0), seed + 1, keep=lambda t: t < 0.42):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    for k in range(7):
        b = L.box((rng.uniform(0.18, 0.34), rng.uniform(0.14, 0.26), rng.uniform(0.07, 0.12)), m)
        b.rot(rx=rng.uniform(-25, 25), ry=rng.uniform(-25, 25), rz=rng.uniform(0, 180))
        b.move(rng.uniform(0.6, 1.5), rng.uniform(-0.75, 0.75), 0.04)
        b.jitter(0.012, seed + 10 + k)
        b.uv = L.uv_box(b.v, b.t, m.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(moss_tint(b, 0.6, seed + k, up=0.55))
    return A


# =============================================================================================
# hedge, wattle fence, hay stook
# =============================================================================================

def build_hedge(aid):
    """Hawthorn hedgerow, 2 m module along X, ~1.35 m tall. Blocks pathing, not sight."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, base_dark=0.5, base_h=0.4, top_light=0.2)
    leaves = M_leaves("hawthorn")
    bark = M_bark()
    H = 1.4
    clusters = []
    for k, x in enumerate(np.linspace(-0.8, 0.8, 4)):
        clusters.append(((x + rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), rng.uniform(0.62, 0.72)),
                         rng.uniform(0.55, 0.62)))
    for x in (-0.45, 0.4):
        clusters.append(((x + rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), rng.uniform(0.95, 1.05)),
                         rng.uniform(0.42, 0.5)))
    for i, (c, R) in enumerate(clusters):
        for p in leaf_cluster(leaves, c, R, seed + 31 * i, n_cards=9, card_scale=1.25, hull=True, hull_subdiv=0,
                              hull_scale=0.6, squash=0.92, down_keep=0.0):
            p.ao_fn = foliage_ao(c, R, 0.0, H, inner=0.45, low=0.6)
            p.phase = (i * 0.37) % 1.0
            A.add(p)
    core = leaf_hull(leaves, np.array([0.0, 0.0, 0.5]), 1.0, seed, subdiv=1, squash=1.0)
    core.v = (core.v - np.array([0, 0, 0.5])) * np.array([0.98, 0.36, 0.42]) + np.array([0, 0, 0.5])
    core.ao_fn = lambda p: np.full(len(p.v), 0.45)
    A.add(core)
    # a few woody stems at the foot
    for k in range(5):
        x = -0.85 + k * 0.42 + rng.uniform(-0.05, 0.05)
        for bp in branch(bark, (x, 0.0, 0.0), (x + rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 0.25),
                         (x + rng.uniform(-0.2, 0.2), rng.uniform(-0.15, 0.15), 0.55), 0.045, 0.02, seed + k, sides=4, n=3):
            A.add(bp)
    A.sway_fn = lambda v, p: np.clip(v[:, 2] / H, 0, 1) ** 1.5 * 0.7
    return A


def build_wattle(aid):
    """Woven hazel wattle hurdle, 2 m module along X, 0.95 m tall with stakes poking above."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.6, base_h=0.3, top_light=0.12)
    wat = Mat("wattle", tex_wattle(13, 256), repeat=0.85, size=256)
    bark = M_bark_hazel()
    nst = 7
    xs = np.linspace(-0.97, 0.97, nst)
    gap = xs[1] - xs[0]
    nx, nz = 36, 3
    z0, z1 = 0.08, 0.86
    th = 0.025
    X = np.linspace(-1.0, 1.0, nx + 1)
    Z = np.linspace(z0, z1, nz + 1)
    for side in (1, -1):
        verts, uvs = [], []
        for j, z in enumerate(Z):
            for i, x in enumerate(X):
                y = 0.04 * math.sin((x - xs[0]) / gap * math.pi) * (1 if j % 2 == 0 else 0.85) + side * th
                y += 0.01 * math.sin(z * 9 + x * 3)
                verts.append((x, y, z + 0.015 * math.sin(x * 5.0)))
                uvs.append(((x + 1.0) / 0.85 * (1 if side > 0 else -1), 1.0 - (z - z0) / (z1 - z0) * 0.98))
        verts, uvs = np.array(verts), np.array(uvs)
        tris = []
        for j in range(nz):
            for i in range(nx):
                a = j * (nx + 1) + i
                b, c, d = a + 1, a + nx + 2, a + nx + 1
                tris += [(a, b, c), (a, c, d)] if side < 0 else [(a, c, b), (a, d, c)]
        tris = np.array(tris)
        A.add(Part(verts, tris, wat, uvs[tris], 60.0))
    # top and bottom edges (thin strips)
    for z in (z0, z1):
        verts, uvs = [], []
        for x in X:
            y = 0.04 * math.sin((x - xs[0]) / gap * math.pi)
            zz = z + 0.015 * math.sin(x * 5.0)
            verts += [(x, y - th, zz), (x, y + th, zz)]
            uvs += [((x + 1) / 0.85, 0.02), ((x + 1) / 0.85, 0.05)]
        verts, uvs = np.array(verts), np.array(uvs)
        tris = []
        for i in range(nx):
            a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
            tris += [(a, b, c), (a, c, d)] if z == z1 else [(a, c, b), (a, d, c)]
        tris = np.array(tris)
        A.add(Part(verts, tris, wat, uvs[tris], 60.0))
    for k, x in enumerate(xs):
        top = rng.uniform(1.0, 1.12)
        lean = rng.uniform(-0.04, 0.04)
        for bp in L.sweep(ngon(5, 1.0, k * 0.4), np.array([(x, 0, -0.05), (x + lean * 0.5, 0, top * 0.5),
                                                              (x + lean, rng.uniform(-0.02, 0.02), top)]),
                          bark, scales=[0.04, 0.036, 0.03], cap0=False, cap1=True):
            A.add(bp)
    return A


def tex_straw_m():
    return Mat("straw", L.tex_straw(11, 512), repeat=1.6, size=256)


def build_hay_stook(aid):
    """A stook: 8 sheaves stood up leaning into each other (tops meet), not a round bale."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.6, base_h=0.25, top_light=0.2)
    straw = tex_straw_m()
    n = 7
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.15, 0.15)
        h = rng.uniform(1.05, 1.2)
        r0 = rng.uniform(0.15, 0.17)
        prof = [(r0, 0.0), (r0 * 0.95, 0.15), (r0 * 0.75, 0.42 * h), (r0 * 0.66, 0.5 * h), (r0 * 1.1, 0.62 * h),
                (r0 * 1.5, 0.78 * h), (r0 * 1.2, 0.92 * h), (0.0, h)]
        p = L.lathe(prof, 5, straw, a0=rng.uniform(0, 1))[0]
        z = p.v[:, 2]
        band = np.exp(-((z - 0.5 * h) / 0.035) ** 2)
        head = smoothstep(0.62 * h, 0.9 * h, z)
        tint = np.array([1.0, 0.96, 0.86]) * (1 + 0.12 * head)[:, None]
        p.tint = tint * (1 - 0.6 * band)[:, None] + 0.6 * band[:, None] * np.array([0.5, 0.38, 0.22])
        lean = rng.uniform(14, 17)
        p.rot(ry=-lean).rot(rz=math.degrees(a))
        rad = h * math.sin(math.radians(lean)) * 0.92
        p.move(math.cos(a) * rad, math.sin(a) * rad, 0)
        p.v[:, 2] = np.maximum(p.v[:, 2], -0.02)
        A.add(p)
    return A


# =============================================================================================
# stump, felled log
# =============================================================================================

def root_lobes(v, seed, roots=5, amp=0.35, fall=0.3):
    rng = np.random.default_rng(seed)
    th = np.arctan2(v[:, 1], v[:, 0])
    ph = rng.uniform(0, 6.28)
    k = 1 + np.maximum(0, np.cos(roots * th + ph)) ** 3 * amp * np.exp(-np.maximum(v[:, 2], 0) / fall)
    v = v.copy()
    v[:, 0] *= k
    v[:, 1] *= k
    return v


def build_stump(aid):
    """Felled-tree stump (replaces a harvested tree): 0.4 m, root flare, pale rings #E9CF9B."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.5, base_h=0.25, top_light=0.1)
    bark, rings = M_bark(), M_rings()
    h = 0.42
    prof = [(0.5, 0.0), (0.44, 0.05), (0.37, 0.14), (0.34, 0.26), (0.33, h - 0.03), (0.31, h)]
    body, cap = L.lathe(prof, 11, bark, a0=rng.uniform(0, 1), cap_top=True, cap_mat=rings)
    for p in (body, cap):
        p.v = root_lobes(p.v, seed, roots=5, amp=0.45, fall=0.12)
        # slanted saw cut
        p.v[:, 2] += np.where(p.v[:, 2] > h - 0.06, p.v[:, 0] * 0.08, 0.0)
    body.jitter(0.012, seed, freq=4.0)
    body.v[:, 2] = np.maximum(body.v[:, 2], 0.0)
    cap.ao = False
    cap.ao_fn = lambda p: np.full(len(p.v), 1.0)
    A.add(body, cap)
    # splinter where the trunk tore off the hinge
    for k in range(3):
        a = 2.4 + k * 0.25
        x, y = math.cos(a) * 0.26, math.sin(a) * 0.26
        sp = L.lathe([(0.05, 0.0), (0.03, 0.08), (0.0, 0.16 + 0.05 * k)], 3, bark, a0=0.3 * k)[0]
        sp.rot(ry=-12).move(x, y, h - 0.03 + x * 0.08)
        A.add(sp)
    return A


def build_log(aid):
    """Felled log (shores, woodland floors): 3.6 m, end grain both ends, branch stubs, mossy top."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.6, base_dark=0.55, base_h=0.2, top_light=0.12)
    bark, rings = M_bark(), M_rings()
    n = 7
    xs = np.linspace(-1.8, 1.8, n)
    path = np.stack([xs, 0.06 * np.sin(xs * 1.3), np.zeros(n)], axis=1)
    r = np.linspace(0.32, 0.24, n)
    path[:, 2] = r - 0.06
    parts = L.sweep(ngon(9, 1.0, 0.2, jitter=0.06, seed=seed), path, bark, scales=r, cap0=True, cap1=True,
                    cap_mat=rings, up=(0, 0, 1))
    body = parts[0]
    body.jitter(0.015, seed, freq=3.0)
    A.add(moss_tint(body, 0.7, seed, up=0.5, patch=0.0))
    for cp in parts[1:]:
        cp.ao = False
        cp.ao_fn = lambda p: np.full(len(p.v), 0.95)
        A.add(cp)
    for k, (x, a, L_) in enumerate([(-0.9, 70, 0.45), (0.35, -60, 0.35), (1.1, 110, 0.5)]):
        rr = np.interp(x, xs, r)
        d = np.array([0, math.cos(math.radians(a)), math.sin(math.radians(a))])
        p0 = np.array([x, 0, rr - 0.06]) + d * rr * 0.6
        p2 = p0 + d * L_ + np.array([0.12, 0, 0])
        for bp in branch(bark, p0, (p0 + p2) / 2, p2, 0.09, 0.05, seed + k, sides=5, n=3):
            A.add(bp)
    return A


# =============================================================================================
# shore: reeds and lily pads
# =============================================================================================

def M_reeds():
    return Mat("reeds", L.tex_reeds(31, 512), repeat=1.0, size=256, alpha=True, cutoff=0.5, double=True, sway=True)


def build_reeds(aid):
    """Reed and bulrush clump for shores (place on the wet band, base at water level or just above)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.4, base_dark=0.55, base_h=0.3, top_light=0.2)
    mat = M_reeds()
    H = 1.5
    for k in range(20):
        a = rng.uniform(0, 6.28)
        rr = rng.uniform(0.0, 0.42)
        bx, by = math.cos(a) * rr, math.sin(a) * rr
        h = rng.uniform(0.85, 1.45)
        lean = rng.uniform(0.1, 0.45)
        la = a + rng.uniform(-0.6, 0.6)
        tip = np.array([bx + math.cos(la) * lean, by + math.sin(la) * lean, h])
        mid = np.array([bx + math.cos(la) * lean * 0.25, by + math.sin(la) * lean * 0.25, h * 0.55])
        path = bezier((bx, by, 0.0), mid, tip, 4)
        w = rng.uniform(0.045, 0.065)
        u0 = rng.uniform(0.05, 0.35)
        p = L.ribbon(path, [w, w * 0.85, w * 0.55, 0.004], mat, u_range=(u0, u0 + 0.3), v_range=(0.98, 0.02),
                     normal_hint=(math.cos(la + 1.57), math.sin(la + 1.57), 0))
        p.nmode = "sphere"
        p.ncenter = np.array([0, 0, -0.6])
        p.nblend = 0.7
        p.ao = False
        p.ao_fn = lambda q: 0.55 + 0.45 * np.clip(q.v[:, 2] / 1.2, 0, 1)
        p.phase = rng.uniform(0, 1)
        A.add(p)
    for k in range(5):
        a = rng.uniform(0, 6.28)
        rr = rng.uniform(0.05, 0.3)
        bx, by = math.cos(a) * rr, math.sin(a) * rr
        h = rng.uniform(1.15, 1.5)
        tip = np.array([bx + rng.uniform(-0.12, 0.12), by + rng.uniform(-0.12, 0.12), h])
        stem = L.ribbon(bezier((bx, by, 0), ((bx + tip[0]) / 2, (by + tip[1]) / 2, h / 2), tip, 3), 0.018, mat,
                        u_range=(0.48, 0.52), v_range=(0.98, 0.3), normal_hint=(1, 0, 0))
        stem.ao = False
        stem.ao_fn = lambda q: 0.6 + 0.4 * np.clip(q.v[:, 2] / 1.2, 0, 1)
        A.add(stem)
        hd = L.lathe([(0.0, 0.0), (0.035, 0.02), (0.04, 0.16), (0.03, 0.2), (0.0, 0.22)], 5, mat)[0]
        hd.uv = np.full_like(hd.uv, 0.0)
        hd.uv[..., 0] = 0.88
        hd.uv[..., 1] = 0.35 + 0.3 * (hd.v[hd.t][..., 2] / 0.22)
        d = nrm(tip - np.array([bx, by, 0]))
        hd.xf(m=L.frame_from_z(d))
        hd.move(*(tip - d * 0.25))
        hd.ao = False
        hd.ao_fn = lambda q: np.full(len(q.v), 0.9)
        A.add(hd)
    A.sway_fn = lambda v, p: np.clip(v[:, 2] / H, 0, 1) ** 1.4
    return A


def tex_lily_m():
    return Mat("lily", L.tex_lily(41, 512), repeat=1.0, size=256)


def build_lily_pads(aid):
    """Lily pads with a few white flowers. Origin = water surface: place at the water height."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.2, base_dark=1.0, base_h=0.01, top_light=0.0, ground_ao=False)
    mat = tex_lily_m()
    pads = []
    for k in range(7):
        for _ in range(30):
            a, rr = rng.uniform(0, 6.28), rng.uniform(0.0, 1.0)
            x, y = math.cos(a) * rr, math.sin(a) * rr
            R = rng.uniform(0.18, 0.32)
            if all(math.hypot(x - px, y - py) > (R + pr) * 0.9 for px, py, pr in pads):
                pads.append((x, y, R))
                break
    for k, (x, y, R) in enumerate(pads):
        K = 12
        notch = rng.uniform(0, 6.28)
        verts = [(0.0, 0.0, 0.012)]
        uvs = [(0.25, 0.5)]
        for i in range(K + 1):
            a = notch + 0.32 + i * (2 * math.pi - 0.64) / K
            verts.append((math.cos(a) * R, math.sin(a) * R, 0.004 + 0.01 * math.sin(i)))
            uvs.append((0.25 + 0.235 * math.cos(a - notch), 0.5 - 0.235 * math.sin(a - notch)))
        tris = np.array([(0, i, i + 1) for i in range(1, K + 1)])
        verts, uvs = np.array(verts), np.array(uvs)
        p = Part(verts, tris, mat, uvs[tris], 30.0)
        p.nmode = "up"
        p.move(x, y, 0)
        p.sway = np.full(len(p.v), 0.15)
        p.ao = False
        p.ao_fn = lambda q: np.full(len(q.v), 0.95)
        A.add(p)
    # flowers on two pads
    for x, y, R in pads[:2]:
        for ring, (n, rad, tilt, h) in enumerate([(7, 0.07, 55, 0.05), (5, 0.045, 30, 0.06)]):
            for i in range(n):
                a = i * 2 * math.pi / n + ring * 0.4
                pt = L.card(0.06, 0.09, mat, (0.6, 0.15, 0.9, 0.6), pivot="bottom")
                pt.rot(rx=-tilt).rot(rz=math.degrees(a) + 90)
                pt.move(x + math.cos(a) * rad * 0.3, y + math.sin(a) * rad * 0.3, 0.02)
                pt.nmode = "up"
                pt.ao_fn = lambda q: np.full(len(q.v), 1.0)
                pt.sway = np.full(len(pt.v), 0.15)
                A.add(pt)
    return A


# =============================================================================================
# meadow cards: wildflowers and grass tufts
# =============================================================================================

def M_meadow():
    return Mat("meadow", L.tex_meadow_cards(21, 1024), size=512, alpha=True, cutoff=0.5, double=True, sway=True)


def build_meadow_clump(aid, cell, size=0.85, n=3, extra=2):
    """Crossed cards with ground-like (up) normals, so they light like the terrain."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.2, base_dark=1.0, base_h=0.01, top_light=0.0, ground_ao=False)
    mat = M_meadow()
    H = size
    a0 = rng.uniform(0, 180)
    specs = [(0.0, 0.0, a0 + k * 180 / n, size * rng.uniform(0.92, 1.08)) for k in range(n)]
    for k in range(extra):
        a = rng.uniform(0, 6.28)
        specs.append((math.cos(a) * size * 0.45, math.sin(a) * size * 0.45, rng.uniform(0, 180),
                      size * rng.uniform(0.6, 0.75)))
    for i, (x, y, yaw, s) in enumerate(specs):
        p = L.card(s * 1.1, s, mat, cell_rect(cell), segs=(1, 2), pivot="bottom")
        p.rot(rx=rng.uniform(-12, 12)).rot(rz=yaw).move(x, y, -0.02)
        p.nmode = "up"
        p.ao = False
        p.ao_fn = lambda q: 0.62 + 0.38 * np.clip(q.v[:, 2] / H, 0, 1)
        p.phase = rng.uniform(0, 1)
        A.add(p)
    A.sway_fn = lambda v, p: np.clip(v[:, 2] / H, 0, 1) ** 1.5
    return A


# =============================================================================================
# mushroom ring
# =============================================================================================

def tex_mushroom(seed=51, n=256):
    """Left half: stem (cream, faint vertical streaks); right half: cap disc (tan centre -> cream rim, gills dark)."""
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        u, v = xx / n, yy / n
        stem = hexcol("#E2D6BC") * (0.92 + 0.08 * np.sin(u * 60))[..., None]
        cx, cy, R = 0.75, 0.5, 0.24
        r = np.hypot(u - cx, v - cy) / R
        cap = hexcol("#A8865A") + (hexcol("#EDE3CC") - hexcol("#A8865A")) * smoothstep(0.1, 0.85, r)[..., None]
        spots = L.periodic_noise(n, seed, 1.2)
        cap = cap * (1 - 0.12 * smoothstep(0.75, 0.85, spots))[..., None]
        rim = smoothstep(0.9, 1.0, r)[..., None]
        cap = cap * (1 - rim * 0.25)
        col = np.where((u > 0.5)[..., None], cap, stem)
        return L.to_img(col)
    return lambda: L.cached_image(("mushroom", seed, n), fn)


def build_mushroom_ring(aid):
    """Fairy ring of pale caps (deep woods only), ~2.4 m across."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.25, base_dark=0.6, base_h=0.06, top_light=0.1)
    mat = Mat("mushroom", tex_mushroom(), repeat=1.0, size=128)
    n = 13
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.12, 0.12)
        rr = 1.05 + rng.uniform(-0.12, 0.12)
        s = rng.uniform(1.0, 1.6) * (1.25 if k % 4 == 0 else 1.0)
        h = 0.14 * s
        cr = 0.085 * s
        stem = L.lathe([(0.026 * s, 0.0), (0.02 * s, h)], 4, mat)[0]
        stem.uv[..., 0] = 0.1 + 0.3 * (stem.uv[..., 0] % 1.0)
        stem.uv[..., 1] = 0.5
        cap = L.lathe([(0.018 * s, h - 0.01), (cr, h + 0.005), (cr * 0.85, h + 0.035 * s), (cr * 0.45, h + 0.06 * s),
                       (0.0, h + 0.068 * s)], 6, mat)[0]
        cap.uv = L.uv_disc(cap.v, cap.t, (0, 0, 0), cr * 1.02)
        cap.uv = np.stack([0.75 + (cap.uv[..., 0] - 0.5) * 0.48, 0.5 + (cap.uv[..., 1] - 0.5) * 0.48], axis=-1)
        for p in (stem, cap):
            p.rot(rx=rng.uniform(-10, 10), ry=rng.uniform(-10, 10))
            p.move(math.cos(a) * rr, math.sin(a) * rr, 0)
            A.add(p)
    return A


# =============================================================================================
# broken cart, milestone, small cairn
# =============================================================================================

def M_timber():
    return Mat("timber", L.swatch(SW + "neutral_mine_timber.png", seamless=True, sat=0.9), repeat=1.6, size=256)


def M_timber_light():
    return Mat("timber", L.swatch(SW + "neutral_mine_timber.png", seamless=True, sat=0.9, tint=(1.12, 1.04, 0.92),
                                  gamma=0.82), repeat=1.6, size=256)


def M_planks_painted():
    return Mat("painted", L.swatch(SW + "kingdom_painted_planks.png", seamless=True, sat=0.8), repeat=1.6, size=256)


def wheel(mat, R=0.46, seed=0, spokes=6, w=0.07):
    """Cart wheel in the local XZ plane (axle along Y), centre at origin."""
    parts = []
    K = 14
    a = np.linspace(0, 2 * math.pi, K + 1)
    path = np.stack([np.cos(a) * R, np.zeros(K + 1), np.sin(a) * R], axis=1)
    rim = L.sweep(np.array([(0.045, -w / 2), (0.045, w / 2), (-0.03, w / 2), (-0.03, -w / 2)]), path, mat,
                  up=(0, 1, 0), cap0=False, cap1=False, smooth=30)[0]
    rim.uv = L.uv_box(rim.v, rim.t, mat.repeat)
    parts.append(rim)
    hub = L.lathe([(0.0, -0.11), (0.08, -0.1), (0.1, -0.05), (0.1, 0.05), (0.08, 0.1), (0.0, 0.11)], 7, mat)[0]
    hub.rot(rx=90)
    parts.append(hub)
    for k in range(spokes):
        ang = k * 360 / spokes
        b = L.box((0.045, 0.04, R - 0.06), mat, center=(0, 0, (R - 0.06) / 2 + 0.04))
        b.rot(ry=ang)
        parts.append(b)
    for p in parts:
        p.uv = L.uv_box(p.v, p.t, mat.repeat, ((seed * 0.17) % 1, 0))
    return parts


def build_cart(aid):
    """Wrecked market wagon: tipped bed, one wheel lost (lying in the grass), broken shaft, a crate."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.7, base_dark=0.55, base_h=0.25, top_light=0.12)
    tim, pnt = M_timber(), M_planks_painted()
    bed = []
    bed.append(L.box((1.9, 1.05, 0.07), tim, center=(0, 0, 0)))
    for y in (0.5, -0.5):
        if y < 0:
            continue
        bed.append(L.box((1.9, 0.06, 0.32), pnt, center=(0, y, 0.18)))
    bed.append(L.box((0.06, 1.05, 0.32), pnt, center=(-0.94, 0, 0.18)))
    bed.append(L.box((0.08, 1.2, 0.08), tim, center=(0.0, 0, -0.08)))     # axle bed
    for p in bed:
        p.rot(rx=-14, ry=6)
        p.move(0, 0.05, 0.42)
        p.uv = L.uv_box(p.v, p.t, p.mat.repeat)
        A.add(p)
    # the wheel still on (+Y side)
    for p in wheel(tim, seed=seed):
        p.rot(rx=0).move(0.0, 0.68, 0.46)
        A.add(p)
    # the lost wheel, flat in the grass
    for p in wheel(tim, seed=seed + 1):
        p.rot(rx=90).rot(rz=20).move(0.55, -1.35, 0.06)
        A.add(p)
    # fallen side board
    sb = L.box((1.7, 0.06, 0.3), pnt, center=(0, 0, 0))
    sb.rot(rx=86, rz=-8).move(-0.25, -0.95, 0.04)
    sb.uv = L.uv_box(sb.v, sb.t, pnt.repeat)
    A.add(sb)
    # shafts: one whole, resting on the ground; one snapped
    for y, Ls, broken in ((0.42, 1.6, False), (-0.42, 0.85, True)):
        x0 = 0.95
        p0 = np.array([x0, y, 0.48])
        p1 = np.array([x0 + Ls, y + (0.05 if not broken else -0.15), 0.05 if not broken else 0.3])
        for bp in L.sweep(ngon(5, 1.0), np.stack([p0, (p0 + p1) / 2, p1]), tim, scales=[0.045, 0.042, 0.038],
                          cap0=True, cap1=True):
            A.add(bp)
    sh = L.sweep(ngon(5, 1.0), np.array([(1.9, -0.75, 0.04), (2.6, -0.95, 0.04)]), tim, scales=[0.04, 0.036])[0]
    A.add(sh)
    # spilled crate
    cr = L.box((0.5, 0.5, 0.42), pnt, chamfer=0.03, center=(0, 0, 0.21))
    cr.rot(rz=33, rx=8).move(-1.45, 0.35, 0.0)
    cr.uv = L.uv_box(cr.v, cr.t, pnt.repeat, (0.3, 0.1))
    A.add(cr)
    return A


def M_milestone():
    return Mat("stone", tex_rock(9, 512, base="#8A8478", dark="#5E594F", light="#A8A294", cells=18, lichen_amt=1.4,
                                 moss_amt=0.6), repeat=1.6, size=256)


def build_milestone(aid):
    """Roadside milestone: a squat square post with a slanted inscription face (carved band) and a
    shallow pyramid cap, moss at the foot. Deliberately not a round-topped (grave-like) slab."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.4, base_dark=0.5, base_h=0.25, top_light=0.12)
    mat = M_milestone()
    w, d, h = 0.4, 0.34, 0.62
    # side outline (y, z): front face slanted back above the inscription
    outline = np.array([(d / 2, -0.08), (d / 2, h * 0.55), (d / 2 - 0.12, h), (-d / 2, h), (-d / 2, -0.08)])
    p = L.slab(outline[:, ::-1] * np.array([1, 1]), -w / 2, w / 2, mat, chamfer=0.03, top_chamfer_only=False)
    # slab extrudes along Z with the outline in (x, y): map (x=z_side, y=y_side, z=x) -> build axes
    v = p.v.copy()
    p.v = np.stack([v[:, 2], v[:, 1], v[:, 0]], axis=1)
    p.t = p.t[:, ::-1]
    cap = L.lathe([(w * 0.62, h - 0.01), (w * 0.62, h + 0.04), (0.0, h + 0.2)], 4, mat, a0=math.pi / 4)[0]
    cap.v[:, 1] *= d / w
    for q in (p, cap):
        q.jitter(0.01, seed, freq=4.0)
        q.rot(rz=rng.uniform(-4, 4), rx=rng.uniform(-3, 3))
        q.uv = L.uv_box(q.v, q.t, mat.repeat, (0.2, 0.3))
    band = np.exp(-((p.v[:, 2] - 0.42) / 0.035) ** 2) * (p.v[:, 1] > 0.05)
    p.dark = 1 - 0.5 * band
    A.add(moss_tint(p, 0.6, seed, up=0.6), moss_tint(cap, 0.4, seed + 1, up=0.7, patch=0.2))
    for k in range(3):
        b = L.blob(mat, 0.1, scale=(1, 0.8, 0.6), seed=seed + k, sphere="uv", segs=(6, 4), flat_top=0.8,
                   flat_bottom=0.1, smooth=40)
        a = rng.uniform(0, 6.28)
        b.move(math.cos(a) * 0.32, math.sin(a) * 0.28, -0.02)
        A.add(moss_tint(b, 0.8, seed + k))
    return A


def build_cairn(aid):
    """Small roadside cairn: a stack of flat stones ~1.1 m."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.5, base_h=0.3, top_light=0.15)
    mat = M_rock(seed=4)
    z = 0.0
    r = 0.42
    for k in range(8):
        th = r * rng.uniform(0.5, 0.62)
        b = L.blob(mat, r, scale=(1.0, rng.uniform(0.75, 0.9), th / r), seed=seed + k, sphere="uv", segs=(8, 5),
                   noise_amp=0.12, flat_top=0.75, flat_bottom=0.2, cuts=2, smooth=40)
        b.rot(rz=rng.uniform(0, 360), rx=rng.uniform(-6, 6))
        b.move(rng.uniform(-0.05, 0.05) * (k > 0), rng.uniform(-0.05, 0.05) * (k > 0), z - 0.02)
        A.add(moss_tint(b, 0.7, seed + k, up=0.6, patch=0.1))
        z += b.v[:, 2].max() - b.v[:, 2].min() - 0.05 - z * 0.0
        z = b.v[:, 2].max() - 0.03
        r *= 0.87
    return A


# =============================================================================================
# creep-camp kit (neutrals §2.1, §3.3): Sootcoats (clamp, lean-to, campfire, cordwood, crates, tent),
# Tattiebogles (scarecrow pole, turnip rows, haystack), Cairnwakes (standing stone)
# =============================================================================================

def M_ember():
    return Mat("ember", L.tex_glow("ember", 128), repeat=0.6, size=128, emissive=True, tag="EMBER")


def M_oilcloth():
    return Mat("oilcloth", L.tex_cloth(61, 512, base="#A07A3A", patches=4, patch_cols=("#8E4A3A", "#5E6B3E", "#6E5636"),
                                       weave=0.05, dirt=0.35), repeat=1.6, size=256)


def M_canvas():
    return Mat("canvas", L.tex_cloth(62, 512, base="#CDBE9A", patches=3, patch_cols=("#8E4A3A", "#5E6E8A", "#B9A27E"),
                                     weave=0.07, dirt=0.3), repeat=1.6, size=256)


def M_sacking():
    return Mat("sacking", L.tex_cloth(63, 256, base="#B9A27E", weave=0.14, dirt=0.25), repeat=0.8, size=128)


def M_turf():
    return Mat("turf", L.swatch(TEX + "gv_grassy_dirt.png", seamless=False, sat=0.9), repeat=2.0, size=256)


def M_soil():
    return Mat("soil", L.swatch(TEX + "gv_dirt.png", seamless=False), repeat=2.0, size=256)


def sheet(mat, corners, nu, nv, sag=0.0, seed=0, flutter=0.0, repeat=None):
    """Cloth sheet over a bilinear patch (corners p00, p10, p11, p01), sagging downwards in the
    middle, double faced (two windings). UV by arc length (repeat metres)."""
    rng = np.random.default_rng(seed)
    p00, p10, p11, p01 = (np.asarray(c, float) for c in corners)
    rep = repeat or mat.repeat
    verts, uvs = [], []
    lu = np.linalg.norm(p10 - p00)
    lv = np.linalg.norm(p01 - p00)
    for j in range(nv + 1):
        t = j / nv
        for i in range(nu + 1):
            s = i / nu
            p = (1 - s) * (1 - t) * p00 + s * (1 - t) * p10 + s * t * p11 + (1 - s) * t * p01
            p = p - np.array([0, 0, 1.0]) * sag * math.sin(math.pi * s) * math.sin(math.pi * t)
            if flutter:
                p = p + rng.normal(0, flutter, 3) * math.sin(math.pi * s) * math.sin(math.pi * t)
            verts.append(p)
            uvs.append((s * lu / rep, t * lv / rep))
    verts, uvs = np.array(verts), np.array(uvs)
    tris = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            b, c, d = a + 1, a + nu + 2, a + nu + 1
            tris += [(a, b, c), (a, c, d)]
    tris = np.array(tris)
    front = Part(verts, tris, mat, uvs[tris], 60.0)
    back = Part(verts.copy(), tris[:, ::-1], mat, uvs[tris[:, ::-1]], 60.0)
    return [front, back]


def pole(mat, p0, p1, r0, r1=None, sides=5, seed=0, cap=True):
    r1 = r0 * 0.85 if r1 is None else r1
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    return L.sweep(ngon(sides, 1.0, seed * 0.3 % 1), np.stack([p0, (p0 + p1) / 2, p1]), mat,
                   scales=[r0, (r0 + r1) / 2, r1], cap0=False, cap1=cap)


def build_campfire(aid):
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.4, base_dark=0.6, base_h=0.12, top_light=0.1)
    rock, bark, ember = M_rock(seed=6), M_bark(), M_ember()
    n = 10
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.1, 0.1)
        b = L.blob(rock, rng.uniform(0.13, 0.17), scale=(1.0, 0.8, 0.7), seed=seed + k, sphere="uv", segs=(7, 4),
                   noise_amp=0.15, flat_top=0.8, flat_bottom=0.15, cuts=1, smooth=40)
        b.rot(rz=math.degrees(a)).move(math.cos(a) * 0.62, math.sin(a) * 0.62, -0.02)
        dark = smoothstep(0.75, 0.45, np.hypot(b.v[:, 0], b.v[:, 1]))
        b.tint = b.tint * (1 - 0.55 * dark)[:, None]
        A.add(b)
    # ember bed
    K = 10
    verts = [(0, 0, 0.05)] + [(math.cos(a) * 0.48, math.sin(a) * 0.48, 0.02) for a in np.linspace(0, 2 * math.pi, K, endpoint=False)]
    tris = np.array([(0, i, i % K + 1) for i in range(1, K + 1)])
    verts = np.array(verts)
    eb = Part(verts, tris, ember, L.uv_planar(verts, tris, (0, 1), 1 / 0.6), 60.0)
    eb.nmode = "up"
    eb.ao = False
    eb.ao_fn = lambda p: np.ones(len(p.v))
    A.add(eb)
    # teepee of logs, charred toward the centre
    for k in range(5):
        a = k * 2 * math.pi / 5 + rng.uniform(-0.2, 0.2)
        p0 = np.array([math.cos(a) * 0.55, math.sin(a) * 0.55, 0.04])
        p1 = np.array([math.cos(a) * 0.06, math.sin(a) * 0.06, rng.uniform(0.4, 0.5)])
        for lp in pole(bark, p0, p1, 0.055, 0.045, seed=k):
            ch = smoothstep(0.35, 0.1, np.hypot(lp.v[:, 0], lp.v[:, 1]))
            lp.tint = lp.tint * (1 - 0.75 * ch)[:, None]
            A.add(lp)
    # a cooking tripod with a pot
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        for lp in pole(bark, (math.cos(a) * 0.9, math.sin(a) * 0.9, 0), (0.0, 0.0, 1.25), 0.03, 0.025, sides=4, seed=k + 9):
            A.add(lp)
    pot = L.lathe([(0.0, 0.62), (0.12, 0.64), (0.17, 0.72), (0.16, 0.84), (0.13, 0.88), (0.14, 0.9)], 7, rock)[0]
    pot.tint = np.ones((len(pot.v), 3)) * 0.35
    A.add(pot)
    return A


def build_lean_to(aid):
    """Sootcoat lean-to: two forked posts, a ridge pole, rafters to the ground, a patched oilcloth
    roof; open side faces the front (-Z). A bedroll and a stump seat."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.9, base_dark=0.55, base_h=0.3, top_light=0.12)
    bark, cloth, can = M_bark(), M_oilcloth(), M_canvas()
    hx, ry, rz = 1.25, 0.5, 1.9
    for x in (-hx, hx):
        A.add(pole(bark, (x, ry, 0.0), (x + 0.02, ry, rz + 0.12), 0.06, 0.05, seed=int(x * 10)))
        A.add(pole(bark, (x, ry, rz - 0.05), (x + 0.18 * np.sign(x), ry + 0.05, rz + 0.25), 0.035, 0.03, sides=4))
    A.add(pole(bark, (-hx - 0.25, ry, rz + 0.02), (hx + 0.25, ry, rz + 0.04), 0.05, 0.045))
    for k, x in enumerate(np.linspace(-hx + 0.1, hx - 0.1, 5)):
        A.add(pole(bark, (x, ry + 0.12, rz + 0.08), (x + rng.uniform(-0.05, 0.05), -0.95, 0.0), 0.035, 0.03, sides=4, seed=k))
    for p in sheet(cloth, [(-hx - 0.1, ry + 0.15, rz + 0.12), (hx + 0.1, ry + 0.15, rz + 0.14),
                           (hx + 0.05, -1.0, 0.02), (-hx - 0.05, -1.0, 0.02)], 6, 4, sag=0.07, seed=seed):
        A.add(p)
    # closed ends: brushwood-and-oilcloth triangles
    for x in (-hx - 0.05, hx + 0.05):
        tri = np.array([(x, ry + 0.1, rz + 0.05), (x, -0.95, 0.0), (x, ry + 0.05, 0.0)])
        t = np.array([(0, 1, 2)])
        for tt in (t, t[:, ::-1]):
            q = Part(tri.copy(), tt, cloth, L.uv_box(tri, tt, cloth.repeat), 30.0)
            q.tint = np.full((3, 3), 0.75)
            A.add(q)
    # bedroll and a stump seat in front
    br = L.lathe([(0.0, -0.45), (0.14, -0.44), (0.15, 0.0), (0.14, 0.44), (0.0, 0.45)], 7, can)[0]
    br.rot(ry=90).rot(rz=8).move(0.1, -0.45, 0.14)
    A.add(br)
    st = L.lathe([(0.2, 0.0), (0.17, 0.08), (0.16, 0.38), (0.0, 0.4)], 7, bark)[0]
    st.move(0.9, 1.1, 0)
    A.add(st)
    return A


def build_tent(aid):
    """Small ridge tent of patched canvas, door to the front (-Z), guy ropes."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.9, base_dark=0.55, base_h=0.3, top_light=0.12)
    bark, can = M_bark(), M_canvas()
    hx, w, h = 0.75, 0.85, 1.4      # tent runs along Y (door at +Y)
    for y in (-hx, hx):
        A.add(pole(bark, (0, y, 0), (0, y, h + 0.15), 0.035, 0.03, sides=4))
    A.add(pole(bark, (0, -hx - 0.1, h), (0, hx + 0.1, h), 0.03, 0.03, sides=4))
    for sgn in (1, -1):
        for p in sheet(can, [(0, -hx, h), (0, hx, h), (sgn * w, hx, 0.0), (sgn * w, -hx, 0.0)], 5, 3, sag=0.06,
                       seed=seed + sgn):
            A.add(p)
    # back wall and one door flap closed, the other tied open
    tri = [np.array([(0, -hx, h), (w, -hx, 0), (-w, -hx, 0)])]
    for pts in tri:
        t = np.array([(0, 1, 2)])
        A.add(Part(pts, t, can, L.uv_box(pts, t, can.repeat), 30.0))
        A.add(Part(pts.copy(), t[:, ::-1], can, L.uv_box(pts, t[:, ::-1], can.repeat), 30.0))
    flap = np.array([(0, hx, h), (0.02, hx + 0.02, 0.0), (-w, hx, 0.0)])
    t = np.array([(0, 1, 2)])
    A.add(Part(flap, t, can, L.uv_box(flap, t, can.repeat), 30.0), Part(flap.copy(), t[:, ::-1], can,
                                                                      L.uv_box(flap, t[:, ::-1], can.repeat), 30.0))
    open_flap = np.array([(0, hx, h), (w * 0.9, hx + 0.25, 0.05), (w * 0.3, hx + 0.05, 0.3)])
    A.add(Part(open_flap, t, can, L.uv_box(open_flap, t, can.repeat), 30.0),
          Part(open_flap.copy(), t[:, ::-1], can, L.uv_box(open_flap, t[:, ::-1], can.repeat), 30.0))
    # dark interior floor
    fl = np.array([(-w * 0.9, -hx, 0.01), (w * 0.9, -hx, 0.01), (w * 0.9, hx, 0.01), (-w * 0.9, hx, 0.01)])
    ft = np.array([(0, 1, 2), (0, 2, 3)])
    fp = Part(fl, ft, can, L.uv_box(fl, ft, can.repeat), 30.0)
    fp.dark = np.full(4, 0.3)
    A.add(fp)
    for y in (-hx - 0.1, hx + 0.1):
        for sgn in (1, -1):
            r = L.ribbon(np.array([(0, y, h + 0.1), (sgn * 1.4, y * 1.5, 0.0)]), 0.02, bark, normal_hint=(0, 1, 0))
            A.add(r)
    return A


def build_charcoal_clamp(aid):
    """Charcoal clamp: a turf-covered earth mound with soot patches and glowing vents (smoke is VFX:
    emit from the `extras.smoke_points`)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, base_dark=0.6, base_h=0.3, top_light=0.15)
    turf, bark, ember = M_turf(), M_bark(), M_ember()
    R, H = 1.75, 1.2
    prof = [(R, 0.0), (R * 0.97, 0.15), (R * 0.86, 0.45), (R * 0.68, 0.78), (R * 0.42, 1.02), (R * 0.15, H - 0.02),
            (0.0, H)]
    p = L.lathe(prof, 16, turf, a0=rng.uniform(0, 1))[0]
    p.jitter((0.05, 0.05, 0.04), seed, freq=1.3)
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    p.uv = L.uv_box(p.v, p.t, turf.repeat)
    nz = L.noise1(p.v, 1.1, (2.0, 5.0, 1.0))
    soot = smoothstep(0.0, 0.3, nz) * smoothstep(0.2, 0.7, p.v[:, 2])
    p.tint = np.ones((len(p.v), 3)) * (1 - 0.7 * soot)[:, None]
    A.add(p)
    smoke = []
    for k, (a, z) in enumerate([(0.0, H - 0.04), (0.6, 0.62), (2.7, 0.5), (4.4, 0.75)]):
        rr = np.interp(z, [q[1] for q in prof], [q[0] for q in prof]) * (0.0 if k == 0 else 1.0)
        c = np.array([math.cos(a) * rr, math.sin(a) * rr, z])
        nrm_ = nrm(np.array([math.cos(a), math.sin(a), 0.9 if k else 4.0]))
        e = L.lathe([(0.0, -0.02), (0.13 if k == 0 else 0.09, 0.0), (0.0, 0.03)], 6, ember)[0]
        e.xf(m=L.frame_from_z(nrm_), t=c + nrm_ * 0.02)
        e.ao = False
        e.ao_fn = lambda q: np.ones(len(q.v))
        A.add(e)
        smoke.append([round(float(c[0]), 3), round(float(c[2]), 3), round(float(-c[1]), 3)])
    # billets leaning on the mound and a long rake
    for k in range(4):
        a = 3.6 + k * 0.32
        base = np.array([math.cos(a) * (R + 0.25), math.sin(a) * (R + 0.25), 0.0])
        top = np.array([math.cos(a) * (R - 0.35), math.sin(a) * (R - 0.35), 0.75 + 0.1 * k])
        A.add(pole(bark, base, top, 0.06, 0.055, seed=k))
    A.add(pole(bark, (1.2, 1.6, 0.0), (0.2, 0.6, 1.2), 0.025, 0.022, sides=4))
    A.extras = {"smoke_points": smoke}
    return A


def build_cordwood(aid):
    """Cordwood stack between stakes (Sootcoat camps): split logs, end grain to the front."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.55, base_h=0.25, top_light=0.12)
    bark, rings = M_bark(), M_rings()
    rows = 4
    z = 0.08
    for r in range(rows):
        x = -0.85 + (r % 2) * 0.1
        while x < 0.8:
            rr = rng.uniform(0.095, 0.12)
            L_ = rng.uniform(0.55, 0.66)
            y0 = rng.uniform(-0.04, 0.04)
            path = np.array([(x + rr, -L_ / 2 + y0, z + rr), (x + rr, L_ / 2 + y0, z + rr)])
            parts = L.sweep(ngon(5, 1.0, rng.uniform(0, 1), jitter=0.12, seed=int(abs(x) * 100 + r * 7)), path, bark,
                            scales=[rr, rr], cap0=True, cap1=True, cap_mat=rings, up=(0, 0, 1))
            for q in parts:
                if q.mat is rings:
                    q.ao = False
                    q.ao_fn = lambda p: np.full(len(p.v), 0.9)
                A.add(q)
            x += 2 * rr + 0.01
        z += 0.22
    for x in (-0.98, 0.98):
        for y in (-0.25, 0.25):
            A.add(pole(bark, (x, y, 0.0), (x + rng.uniform(-0.03, 0.03), y, 1.0), 0.04, 0.035, seed=int(x + y * 10)))
    # base sleepers
    for y in (-0.22, 0.22):
        A.add(pole(bark, (-1.0, y, 0.05), (1.0, y, 0.05), 0.05, 0.05, sides=5))
    return A


def build_crates(aid):
    """Camp stores: two iron-strapped crates, a barrel and two sacks."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.6, base_dark=0.55, base_h=0.25, top_light=0.12)
    tim, sack = M_timber(), M_sacking()
    for k, (x, y, s, rz, z) in enumerate([(-0.35, 0.0, 0.62, 12, 0.0), (0.32, 0.15, 0.5, -20, 0.0),
                                          (-0.3, 0.05, 0.42, 40, 0.62)]):
        b = L.box((s, s * 0.9, s * 0.85), tim, chamfer=0.03, center=(0, 0, s * 0.425))
        b.rot(rz=rz).move(x, y, z)
        b.uv = L.uv_box(b.v, b.t, tim.repeat, (k * 0.31, k * 0.17))
        A.add(b)
    prof = [(0.0, 0.0), (0.24, 0.0), (0.28, 0.2), (0.3, 0.4), (0.28, 0.6), (0.24, 0.8), (0.0, 0.8)]
    br = L.lathe(prof, 9, tim)[0]
    z = br.v[:, 2]
    hoop = (np.exp(-((z - 0.12) / 0.03) ** 2) + np.exp(-((z - 0.68) / 0.03) ** 2))
    br.tint = np.ones((len(br.v), 3)) * (1 - 0.6 * np.clip(hoop, 0, 1))[:, None]
    br.move(0.85, -0.35, 0)
    A.add(br)
    for k, (x, y, rz) in enumerate([(0.15, -0.65, 20), (-0.6, -0.6, -35)]):
        sk = L.blob(sack, 0.32, scale=(0.85, 0.65, 0.85), seed=seed + k, sphere="uv", segs=(8, 6), noise_amp=0.1,
                    flat_bottom=0.15, smooth=60)
        sk.v[:, 2] *= 1 + 0.25 * smoothstep(0.25, 0.5, sk.v[:, 2])
        sk.rot(rz=rz, ry=10).move(x, y, 0)
        A.add(sk)
    return A


def build_scarecrow_pole(aid):
    """Tattiebogle field pole: an empty crossed-pole frame with a tattered sacking rag (the creeps
    slump on these by day)."""
    seed = seed_of(aid)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.55, base_h=0.3, top_light=0.12)
    bark, sack = M_bark_hazel(), M_sacking()
    A.add(pole(bark, (0, 0, -0.05), (0.03, 0.02, 2.3), 0.055, 0.045))
    A.add(pole(bark, (-0.85, 0.02, 1.62), (0.85, 0.0, 1.7), 0.04, 0.035))
    for p in sheet(sack, [(-0.45, -0.05, 1.66), (0.2, -0.05, 1.7), (0.15, -0.12, 0.95), (-0.5, -0.1, 1.05)], 3, 3,
                   sag=-0.04, seed=seed, flutter=0.03):
        A.add(p)
    rope = L.lathe([(0.075, 1.6), (0.075, 1.72)], 6, bark)[0]
    rope.tint = np.ones((len(rope.v), 3)) * np.array([1.2, 1.1, 0.8])
    A.add(rope)
    return A


def M_turnip():
    def fn():
        n = 64
        y = (np.arange(n) + 0.5)[:, None] / n
        top, bot = hexcol("#7A3E6A"), hexcol("#EDE6D8")
        col = top + (bot - top) * smoothstep(0.25, 0.6, y)[..., None]
        return L.to_img(np.repeat(col, n, axis=1))
    return Mat("turnip", lambda: L.cached_image(("turnip",), fn), repeat=1.0, size=64)


def build_turnip_rows(aid):
    """Turnip Patch: three earthed-up furrows with leafy turnip tops and a few lifted turnips."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.4, base_dark=0.7, base_h=0.1, top_light=0.1)
    soil, leaves, tn = M_soil(), M_leaves("hazel"), M_turnip()
    for r, y in enumerate((-0.8, 0.0, 0.8)):
        xs = np.linspace(-2.0, 2.0, 9)
        path = np.stack([xs, y + 0.04 * np.sin(xs * 2 + r), np.zeros(9)], axis=1)
        prof = np.array([(0.4, 0.0), (0.12, 0.17), (-0.12, 0.17), (-0.4, 0.0)])
        ridge = L.sweep(prof, path, soil, cap0=True, cap1=True)[0]
        ridge.v[:, 2] = np.maximum(ridge.v[:, 2] - 0.02, -0.02)
        ridge.uv = L.uv_box(ridge.v, ridge.t, soil.repeat)
        ridge.jitter((0.02, 0.02, 0.02), seed + r, freq=3.0)
        A.add(ridge)
        for k, x in enumerate(np.linspace(-1.75, 1.75, 7)):
            c = np.array([x + rng.uniform(-0.1, 0.1), y + rng.uniform(-0.05, 0.05), 0.3])
            for q in leaf_cluster(leaves, c, 0.24, seed + 13 * r + k, n_cards=4, card_scale=1.6, segs=(1, 1), bend=0.0,
                                  hull=False, offset=0.3, squash=0.8, upright=0.8):
                q.ao_fn = lambda p: 0.55 + 0.45 * np.clip(p.v[:, 2] / 0.5, 0, 1)
                q.phase = rng.uniform(0, 1)
                A.add(q)
            if (k + r) % 2:
                continue
            b = L.lathe([(0.0, 0.0), (0.09, 0.08), (0.05, 0.16), (0.0, 0.18)], 5, tn)[0]
            b.uv[..., 0] = 0.5
            b.uv[..., 1] = 1.0 - np.clip(b.v[b.t][..., 2] / 0.18, 0.02, 0.98)
            b.move(c[0], c[1], 0.07)
            A.add(b)
    for k in range(3):
        b = L.lathe([(0.0, 0.0), (0.08, 0.04), (0.1, 0.1), (0.07, 0.17), (0.0, 0.2)], 6, tn)[0]
        b.uv[..., 0] = 0.5
        b.uv[..., 1] = 1.0 - np.clip(b.v[b.t][..., 2] / 0.2, 0.02, 0.98)
        b.rot(ry=80 + 10 * k, rz=rng.uniform(0, 360)).move(2.3 + 0.2 * k, -0.4 + 0.35 * k, 0.08)
        A.add(b)
    A.sway_fn = lambda v, p: np.clip(v[:, 2] / 0.5, 0, 1) ** 1.3
    return A


def build_haystack(aid):
    """Crow-picked haystack: a domed rick round a stack pole, with a pecked-out hollow."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, base_dark=0.6, base_h=0.3, top_light=0.18)
    straw, bark = tex_straw_m(), M_bark_hazel()
    prof = [(1.0, 0.0), (1.1, 0.35), (1.08, 0.75), (0.9, 1.15), (0.55, 1.6), (0.18, 1.95), (0.0, 2.05)]
    p = L.lathe(prof, 14, straw, a0=rng.uniform(0, 1))[0]
    p.jitter((0.05, 0.05, 0.03), seed, freq=1.6)
    # pecked hollow on the front-left
    c = np.array([-0.55, 0.8, 0.95])
    d = np.linalg.norm(p.v - c, axis=1)
    k = smoothstep(0.55, 0.0, d)
    p.v = p.v - (p.v - np.array([0, 0, p.v[:, 2].mean()])) * (0.28 * k)[:, None] * np.array([1, 1, 0])
    p.tint = np.ones((len(p.v), 3)) * (1 - 0.35 * k)[:, None]
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    A.add(p)
    A.add(pole(bark, (0.0, 0.0, 1.5), (0.04, 0.0, 2.55), 0.05, 0.04))
    # straw tufts dropped at the foot
    for t in range(4):
        a = rng.uniform(0, 6.28)
        q = L.lathe([(0.25, 0.0), (0.18, 0.08), (0.0, 0.12)], 6, straw)[0]
        q.move(math.cos(a) * 1.25, math.sin(a) * 1.25, -0.02)
        A.add(q)
    return A


def tex_glyph(n=256):
    """Cup-and-ring marks: a cup with three concentric rings and a gutter line, on transparent."""
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        u, v = xx / n - 0.5, yy / n - 0.5
        r = np.hypot(u, v)
        m = np.zeros((n, n))
        m = np.maximum(m, smoothstep(0.075, 0.06, r))
        for rr in (0.15, 0.25, 0.35):
            m = np.maximum(m, smoothstep(0.022, 0.012, np.abs(r - rr)) * (np.abs(np.arctan2(v, u) - 1.6) > 0.18))
        gutter = (np.abs(u) < 0.018) & (v > 0.0) & (v < 0.48)
        m = np.maximum(m, gutter * 1.0)
        rgb = np.ones((n, n, 3)) * hexcol("#3E3A34")
        out = np.concatenate([rgb, m[..., None]], axis=2)
        return L.dilate_rgb(L.to_img(out, "RGBA"), 4)
    return lambda: L.cached_image(("glyph", n), fn)


def tex_glyph_emit(n=256):
    def fn():
        a = np.asarray(tex_glyph(n)(), np.float32) / 255.0
        rgb = hexcol("#E8E29A")[None, None, :] * a[..., 3:4]
        return L.to_img(rgb)
    return lambda: L.cached_image(("glyph_emit", n), fn)


def build_standing_stone(aid):
    """Standing Ring menhir: a tall tapered slab (flat broad faces, slanted chiselled top) with
    cup-and-ring marks on the front (GLYPH: emissive lichen-yellow at night)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.7, base_dark=0.5, base_h=0.4, top_light=0.18)
    rock = M_rock(seed=8, lichen_amt=1.6, moss_amt=0.7)
    glyph = Mat("glyph", tex_glyph(), size=256, alpha=True, cutoff=0.5, emissive=True, emissive_image=tex_glyph_emit(),
                tag="GLYPH")
    K = 10
    ang = np.linspace(0, 2 * math.pi, K, endpoint=False) + 0.15
    prof = np.stack([np.cos(ang) * 0.24, np.sin(ang) * 0.47], axis=1)
    prof[:, 0] = np.sign(prof[:, 0]) * np.abs(prof[:, 0]) ** 0.75 * 0.24 ** 0.25      # flatter broad faces
    prof *= 1 + rng.uniform(-0.08, 0.08, (K, 1))
    zs = np.array([-0.08, 0.45, 1.05, 1.6, 2.0, 2.25])
    path = np.stack([np.array([0, 0.02, 0.05, 0.08, 0.1, 0.11]), np.zeros(6), zs], axis=1)
    scales = np.array([1.1, 1.02, 0.98, 0.86, 0.68, 0.42])
    p = L.sweep(prof, path, rock, scales=scales, cap0=False, cap1=True, up=(1, 0, 0))[0]
    top = p.v[:, 2] > 2.1
    p.v[top, 2] -= (p.v[top, 0] - 0.1) * 0.35 + 0.05
    p.jitter((0.035, 0.03, 0.03), seed, freq=1.6)
    p.jitter(0.01, seed + 1)
    p.uv = L.uv_box(p.v, p.t, rock.repeat, (0.37, 0.11))
    p.smooth = 32.0
    A.add(moss_tint(p, 0.75, seed, up=0.5, patch=0.15))
    foot = smoothstep(0.3, 0.0, p.v[:, 2])
    p.tint = p.tint * (1 - 0.8 * foot[:, None]) + 0.8 * np.array([0.5, 0.75, 0.32]) * foot[:, None]
    for k, (z, sz, dx) in enumerate([(1.3, 0.46, 0.04), (0.72, 0.3, -0.12)]):
        g = L.card(sz, sz, glyph, (0, 0, 1, 1))
        g.rot(rz=180)
        sel = np.abs(p.v[:, 2] - z) < 0.25
        y = p.v[sel, 1].max() if sel.any() else 0.25
        g.move(0.07 + dx, y + 0.005, z)
        g.ao = False
        g.ao_fn = lambda q: np.full(len(q.v), 0.85)
        A.add(g)
    return A


def build_skeps(aid):
    """Two straw beehive skeps on a plank bench (kingdom-side farms)."""
    seed = seed_of(aid)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.55, base_h=0.25, top_light=0.15)
    straw, tim = tex_straw_m(), M_timber()
    A.add(L.box((1.3, 0.45, 0.06), tim, center=(0, 0, 0.42)))
    for x in (-0.5, 0.5):
        A.add(L.box((0.08, 0.36, 0.4), tim, center=(x, 0, 0.2)))
    for k, x in enumerate((-0.32, 0.33)):
        prof = [(0.26, 0.0)] + [(0.26 * math.cos(t) + 0.0, 0.42 * math.sin(t)) for t in np.linspace(0.15, 1.5, 6)] + [(0.0, 0.43)]
        sk = L.lathe(prof, 9, straw, a0=0.2 * k)[0]
        z = sk.v[:, 2]
        coil = 0.5 + 0.5 * np.cos(z / 0.055 * 2 * math.pi)
        sk.tint = np.ones((len(sk.v), 3)) * (0.75 + 0.3 * coil)[:, None]
        sk.move(x, 0, 0.45)
        A.add(sk)
        door = L.box((0.1, 0.05, 0.05), tim, center=(x, 0.24, 0.475))
        door.dark = np.full(len(door.v), 0.15)
        A.add(door)
    return A


# =============================================================================================
# neutral structures (neutrals.md §5): Gold Seam, Weighstall, Hale Spring
# =============================================================================================

def densify(poly, step):
    out = []
    n = len(poly)
    for i in range(n):
        a, b = np.asarray(poly[i], float), np.asarray(poly[(i + 1) % n], float)
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for j in range(k):
            out.append(a + (b - a) * j / k)
    return np.array(out)


def rings_solid(rings, mat, bottom=False, repeat=None, smooth=32.0):
    """Closed solid from stacked outline rings [(poly (K,2), z), ...] (same K, CCW), concave-safe caps."""
    K = len(rings[0][0])
    verts = np.concatenate([np.c_[poly, np.full(K, z)] for poly, z in rings])
    tris = list(L._ring_faces(len(rings), K, True))
    top = rings[-1][0]
    base_top = (len(rings) - 1) * K
    for a, b, c in L.mathutils.geometry.tessellate_polygon([[L.Vector((p[0], p[1], 0)) for p in top]]):
        tris.append((base_top + a, base_top + b, base_top + c))
    if bottom:
        for a, b, c in L.mathutils.geometry.tessellate_polygon([[L.Vector((p[0], p[1], 0)) for p in rings[0][0]]]):
            tris.append((c, b, a))
    tris = np.array(tris, np.int64)
    # outward winding check on the side walls
    p = verts[tris]
    fn = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    cen = np.r_[rings[0][0].mean(axis=0), (rings[0][1] + rings[-1][1]) / 2]
    side = np.abs(fn[:, 2]) < np.linalg.norm(fn, axis=1) * 0.7
    if np.sum(np.einsum("ij,ij->i", fn[side], p[side].mean(axis=1) - cen) < 0) > side.sum() / 2:
        tris = tris[:, ::-1]
    rep = repeat or mat.repeat
    return Part(verts, tris, mat, L.uv_box(verts, tris, rep), smooth)


def strata_layer(base, z0, z1, mat, seed, scale=1.0, off=(0.0, 0.0), centre=(0.0, -0.4), jit=0.08, lip=0.05,
                 keep_straight=None):
    """One cliff stratum: outline scaled about `centre`, radial noise per vertex (except vertices
    flagged keep_straight), a slight outward bulge mid-height and a chamfered top lip."""
    c = np.asarray(centre)
    poly = (base - c) * scale + c + np.asarray(off)
    rng = np.random.default_rng(seed)
    nz = L.noise1(np.c_[poly, np.zeros(len(poly))], 1.3, (seed % 31 * 0.7, 2.0, 5.0))
    d = nrm(np.c_[poly - c, np.zeros(len(poly))])[:, :2]
    k = np.ones(len(poly)) if keep_straight is None else (~keep_straight).astype(float)
    poly = poly + d * (nz * jit * k)[:, None]

    def inset(pl, amt):
        return pl - d * amt * (0.4 + 0.6 * k)[:, None]
    h = z1 - z0
    rings = [(inset(poly, 0.02), z0), (poly + d * 0.03 * k[:, None], z0 + h * 0.45), (poly, z1 - lip),
             (inset(poly, lip * 1.2), z1)]
    p = rings_solid(rings, mat)
    p.jitter((0.03, 0.03, 0.012), seed + 3, freq=2.5)
    fnz = nrm(L.face_normals(p.v, p.t))[:, 2]
    top = fnz > 0.6
    p.uv[top] = p.uv[top] * 0.22 + 0.37
    return p


def M_cliff():
    return Mat("rock", tex_strata(17, 512), repeat=3.2, size=512)


def gold_vein_mask_img():
    def fn():
        im = L.swatch(SW + "neutral_gold_vein_rock.png", seamless=True)()
        a = np.asarray(im, np.float32) / 255.0
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        m = smoothstep(0.18, 0.4, r - b) * smoothstep(0.45, 0.7, r)
        out = a * m[..., None] * np.array([1.15, 1.0, 0.75])
        return L.to_img(out)
    return lambda: L.cached_image(("goldmask",), fn)


def M_seam():
    return Mat("seam", L.swatch(SW + "neutral_gold_vein_rock.png", seamless=True), repeat=1.4, size=512,
               emissive=True, emissive_image=gold_vein_mask_img(), tag="GLOW")


def M_lamp():
    return Mat("lamp", L.tex_glow("lamp", 64), repeat=0.3, size=64, emissive=True, tag="LAMP")


def M_water():
    def fn():
        im = L.load_rgb(TEX + "water_ripples.png").convert("RGB").resize((256, 256), L.Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        lum = a.mean(axis=2, keepdims=True)
        col = hexcol("#3F8A88") * (0.72 + 0.3 * (lum - lum.mean()) / max(lum.std() * 3, 1e-3))
        return L.to_img(col)
    return Mat("water", lambda: L.cached_image(("water",), fn), repeat=2.0, size=256, roughness=0.35, tag="WATER")


def lantern(frame_mat, lamp_mat, hang, seed=0):
    """Hanging lantern: dark iron cage over an emissive glass core. `hang` = hook point."""
    hang = np.asarray(hang, float)
    parts = []
    sc = 1.5
    body = L.lathe([(0.0, -0.36 * sc), (0.1 * sc, -0.34 * sc), (0.1 * sc, -0.3 * sc), (0.03 * sc, -0.28 * sc),
                    (0.03 * sc, -0.12 * sc), (0.11 * sc, -0.11 * sc), (0.06 * sc, -0.05 * sc), (0.0, 0.0)], 6, frame_mat)[0]
    body.tint = np.ones((len(body.v), 3)) * 0.28
    glass = L.lathe([(0.0, -0.29 * sc), (0.085 * sc, -0.27 * sc), (0.09 * sc, -0.13 * sc), (0.0, -0.11 * sc)], 6,
                    lamp_mat)[0]
    for p in (body, glass):
        p.move(*hang)
        p.ao = False
        p.ao_fn = lambda q: np.ones(len(q.v))
    # cut windows: the body is drawn smaller than the glass between its rings, so glass shows through
    body.v[:, :2] *= 1.0
    parts += [glass, body]
    return parts


def build_gold_mine(aid):
    """Gold Seam: an adit (low square timber-framed tunnel mouth) cut into a short layered cliff with a
    thin bright quartz-and-gold stratum (GLOW, pulse it when a worker enters), a windlass headframe on
    the lip (node `windlass_drum`), a spoil heap of grey tailings, a wooden sluice with a trickle of
    water, two lanterns on hooks (LAMP, lit at night). No cart, no rails (neutrals §5.2, §10.2)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.2, ao_strength=1.0, base_dark=0.55, base_h=0.5, top_light=0.2)
    rock, seam, tim, lamp, water = M_cliff(), M_seam(), M_timber(), M_lamp(), M_water()
    fy, nw, nd = 1.15, 0.78, 0.15        # front face y, notch half-width, notch back y
    outer = [(1.85, -1.95), (2.12, -1.3), (2.15, -0.3), (2.05, 0.6), (1.7, fy - 0.02), (1.2, fy + 0.06), (nw, fy),
             (nw, nd), (-nw, nd), (-nw, fy), (-1.25, fy + 0.04), (-1.75, fy - 0.1), (-2.1, 0.45), (-2.18, -0.6),
             (-2.0, -1.65), (-1.5, -2.05), (-0.5, -2.12), (0.7, -2.1), (1.4, -2.05)]
    base_n = densify(outer, 0.42)
    notch = (np.abs(base_n[:, 0]) <= nw + 1e-6) & (base_n[:, 1] >= nd - 1e-6)
    plain = [(1.85, -1.95), (2.12, -1.3), (2.15, -0.3), (2.05, 0.6), (1.7, fy - 0.02), (1.2, fy + 0.06),
             (0.0, fy + 0.04), (-1.25, fy + 0.04), (-1.75, fy - 0.1), (-2.1, 0.45), (-2.18, -0.6), (-2.0, -1.65),
             (-1.5, -2.05), (-0.5, -2.12), (0.7, -2.1), (1.4, -2.05)]
    base_p = densify(plain, 0.42)
    def terrace(poly, amt, front_amt=0.0, k=0, shift=(0.0, 0.0)):
        """Inset sides and back by an irregular `amt` (noise around the outline), the front face only by
        `front_amt` (it stays a vertical cut face); `shift` slides the inset part (off-centre crags)."""
        c = np.array([0.0, -0.4])
        out = poly.copy()
        nz = L.noise1(np.c_[poly * 0.9, np.full(len(poly), k * 1.7)], 1.0, (seed % 13 * 0.9, 1.0, 4.0))
        for i, (x, y) in enumerate(poly):
            lo_, hi_ = (0.25, 1.9) if amt < 0.8 else (0.75, 1.25)
            a = amt * float(np.clip(0.45 + 1.4 * (nz[i] + 0.35), lo_, hi_))
            if y > fy - 0.4:
                out[i] = (x - np.sign(x) * a * min(1.0, abs(x) / 1.6), y - front_amt)
            else:
                d = nrm(np.array([x, y]) - c)
                out[i] = np.array([x, y]) - d * a + np.asarray(shift) * min(1.0, amt)
        return out
    layers = [  # (z0, z1, mat, outline, notched, jitter)
        (0.0, 0.8, rock, base_n, True, 0.16),
        (0.8, 1.0, seam, terrace(base_n, 0.04, k=1), True, 0.08),
        (1.0, 1.85, rock, terrace(base_n, 0.2, k=2), True, 0.16),
        (1.85, 2.55, rock, terrace(base_p, 0.5, 0.12, k=3, shift=(-0.15, -0.1)), False, 0.17),
        (2.55, 3.3, rock, terrace(base_p, 1.05, 0.95, k=4, shift=(-0.55, -0.35)), False, 0.15),
    ]
    for i, (z0, z1, m, base, notched, jit) in enumerate(layers):
        ks = notch if notched else None
        if notched:
            ks = (np.abs(base[:, 0]) <= nw + 1e-6) & (base[:, 1] >= nd - 1e-6)
        p = strata_layer(base, z0, z1, m, seed + 7 * i, scale=1.0, off=(0.0, 0.0), jit=jit, keep_straight=ks)
        if m is rock:
            moss_tint(p, 0.85 if i >= 2 else 0.7, seed + i, col=(0.46, 0.7, 0.3), up=0.55, patch=-0.3 if i >= 2 else 0.1)
        A.add(p)
    # darkness at the back of the adit + inner timber sets for depth
    back = np.array([(-nw, nd + 0.02, 0.0), (nw, nd + 0.02, 0.0), (nw, nd + 0.02, 1.82), (-nw, nd + 0.02, 1.82)])
    bt = np.array([(0, 2, 1), (0, 3, 2)])
    bp = Part(back, bt, tim, L.uv_box(back, bt, tim.repeat), 30.0)
    bp.tint = np.full((4, 3), 0.04)
    bp.ao = False
    bp.ao_fn = lambda q: np.ones(len(q.v))
    A.add(bp)
    for y, s in ((fy + 0.06, 1.0), (0.62, 0.92)):
        posts = []
        for x in (-nw + 0.1, nw - 0.1):
            b = L.box((0.2, 0.2, 1.72 * s), tim, center=(x, y, 0.86 * s))
            b.rot(ry=rng.uniform(-2.5, 2.5), pivot=(x, y, 0))
            posts.append(b)
        lin = L.box((2 * nw + 0.45, 0.24, 0.26), tim, center=(0, y, 1.72 * s + 0.1))
        lin.rot(ry=rng.uniform(-1.5, 1.5))
        posts.append(lin)
        if s == 1.0:
            for x in (-nw + 0.1, nw - 0.1):
                br = L.box((0.12, 0.14, 0.55), tim, center=(0, 0, 0))
                br.rot(ry=45 * np.sign(x)).move(x - 0.17 * np.sign(x), y + 0.02, 1.5)
                posts.append(br)
            sill = L.box((2 * nw + 0.2, 0.3, 0.1), tim, center=(0, y + 0.05, 0.05))
            posts.append(sill)
        for b in posts:
            b.jitter(0.008, seed + int(y * 10))
            b.uv = L.uv_box(b.v, b.t, tim.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
            A.add(b)
    # lanterns on iron hooks either side of the mouth
    for x in (-nw - 0.28, nw + 0.28):
        hook = L.box((0.04, 0.32, 0.04), tim, center=(x, fy + 0.18, 1.55))
        hook.tint = np.full((len(hook.v), 3), 0.25)
        A.add(hook)
        A.add(lantern(tim, lamp, (x, fy + 0.32, 1.55)))
    # windlass headframe on the lip (two A-frames, a drum with a crank, a rope to a bucket)
    top_z = 2.55
    lip_y = fy - 0.12 - 0.35
    wx, dz = 0.95, 1.05
    drum_c = np.array([0.35, lip_y + 0.12, top_z + dz])
    for x in (drum_c[0] - wx / 2, drum_c[0] + wx / 2):
        for dy in (-0.55, 0.42):
            A.add(pole(tim, (x, drum_c[1] + dy, top_z - 0.05), (x, drum_c[1], drum_c[2] + 0.12), 0.07, 0.06, sides=4))
        A.add(pole(tim, (x, drum_c[1] - 0.3, top_z + 0.45), (x, drum_c[1] + 0.25, top_z + 0.45), 0.05, 0.05, sides=4))
    A.node("windlass_drum", drum_c)
    drum = L.lathe([(0.0, -wx / 2 - 0.05), (0.2, -wx / 2 - 0.04), (0.2, -wx / 2 + 0.04), (0.15, -wx / 2 + 0.06),
                    (0.15, wx / 2 - 0.06), (0.2, wx / 2 - 0.04), (0.2, wx / 2 + 0.04), (0.0, wx / 2 + 0.05)], 8, tim)[0]
    drum.rot(ry=90).move(*drum_c)
    crank = [L.box((0.05, 0.05, 0.36), tim, center=(drum_c[0] + wx / 2 + 0.12, drum_c[1], drum_c[2] + 0.16)),
             L.box((0.24, 0.05, 0.05), tim, center=(drum_c[0] + wx / 2 + 0.22, drum_c[1], drum_c[2] + 0.33)),
             L.box((0.3, 0.06, 0.06), tim, center=(drum_c[0] + wx / 2 + 0.05, drum_c[1], drum_c[2]))]
    rope_top = drum_c + np.array([0.0, 0.18, 0.0])
    bucket_c = np.array([drum_c[0], lip_y + 0.62, 1.95])
    rope = L.ribbon(np.array([rope_top, bucket_c + np.array([0, 0, 0.42])]), 0.03, tim, u_range=(0.1, 0.12),
                    normal_hint=(0, 1, 0))
    rope2 = L.ribbon(np.array([rope_top, bucket_c + np.array([0, 0, 0.42])]), 0.03, tim, u_range=(0.1, 0.12),
                     normal_hint=(1, 0, 0))
    for p in [drum] + crank + [rope, rope2]:
        p.node = "windlass_drum"
        p.uv = L.uv_box(p.v, p.t, tim.repeat) if p not in (rope, rope2) else p.uv
        A.add(p)
    rope.tint = np.full((len(rope.v), 3), np.array([1.2, 1.05, 0.75]))
    rope2.tint = rope.tint.copy()
    bucket = L.lathe([(0.0, 0.0), (0.16, 0.0), (0.2, 0.3), (0.19, 0.32), (0.0, 0.3)], 7, tim)[0]
    bucket.move(*bucket_c)
    handle = L.box((0.42, 0.03, 0.03), tim, center=bucket_c + np.array([0, 0, 0.42]))
    for p in (bucket, handle):
        p.node = "windlass_drum"
        A.add(p)
    # spoil heap of grey tailings, front-left: a low gravel cone with loose stones
    heap = L.lathe([(1.0, 0.0), (0.85, 0.12), (0.55, 0.38), (0.25, 0.55), (0.0, 0.6)], 12, rock, a0=0.3)[0]
    heap.v[:, 1] *= 0.8
    heap.jitter((0.06, 0.06, 0.05), seed + 50, freq=2.2)
    heap.v[:, 2] = np.maximum(heap.v[:, 2], 0.0)
    heap.move(-1.6, 1.5, -0.03)
    heap.uv = L.uv_box(heap.v, heap.t, 9.0, (0.42, 0.55))
    heap.tint = np.ones((len(heap.v), 3)) * np.array([0.8, 0.82, 0.88])
    heap.smooth = 60
    A.add(heap)
    for k in range(14):
        st = L.blob(rock, rng.uniform(0.08, 0.16), scale=(1, 0.8, 0.6), seed=seed + 60 + k, sphere="uv", segs=(5, 4),
                    flat_bottom=0.15, smooth=40)
        a = rng.uniform(0, 6.28)
        rr = rng.uniform(0.4, 1.05)
        st.move(-1.6 + math.cos(a) * rr, 1.5 + math.sin(a) * rr * 0.8, max(0.0, 0.5 - rr * 0.5) - 0.03)
        st.tint = np.ones((len(st.v), 3)) * 0.85
        A.add(st)
    # wooden sluice down the right flank, on two trestles, with a trickle of water
    s0 = np.array([1.55, -0.6, 2.6])
    s1 = np.array([2.35, 1.75, 0.42])
    path = np.stack([s0, s0 + (s1 - s0) * 0.5, s1])
    trough = L.sweep(np.array([(0.13, 0.12), (0.13, -0.02), (-0.13, -0.02), (-0.13, 0.12), (-0.1, 0.12), (-0.1, 0.02),
                               (0.1, 0.02), (0.1, 0.12)]), path, tim, up=(0, 0, 1), cap0=True, cap1=True)[0]
    trough.uv = L.uv_box(trough.v, trough.t, tim.repeat)
    A.add(trough)
    wpath = path + np.array([0, 0, 0.06])
    wr = L.ribbon(wpath, 0.17, water, normal_hint=(0, 0, 1))
    wr.nmode = "up"
    wr.ao = False
    wr.ao_fn = lambda q: np.ones(len(q.v))
    A.add(wr)
    fall = L.ribbon(np.array([s1 + np.array([0, 0.12, 0.05]), s1 + np.array([0, 0.3, -0.42])]), 0.12, water,
                    normal_hint=(0, 1, 0))
    fall.ao = False
    fall.ao_fn = lambda q: np.ones(len(q.v))
    A.add(fall)
    for t in (0.35, 0.78):
        c = path[0] + (path[-1] - path[0]) * t
        for dx in (-0.22, 0.22):
            A.add(pole(tim, (c[0] + dx, c[1], 0.0), (c[0], c[1], c[2] - 0.02), 0.05, 0.045, sides=4))
    puddle = L.blob(water, 0.4, scale=(1, 0.8, 0.02), seed=seed + 70, sphere="uv", segs=(8, 3), noise_amp=0.0,
                    flat_bottom=0.5, smooth=60)
    puddle.move(s1[0], s1[1] + 0.35, 0.005)
    puddle.nmode = "up"
    A.add(puddle)
    # a few gold-flecked boulders at the cliff foot (not a heap of nuggets)
    for k, (x, y) in enumerate([(-2.0, -1.2), (1.95, 0.75), (-1.1, -2.1)]):
        b = L.blob(rock, rng.uniform(0.3, 0.42), scale=(1, 0.85, 0.7), seed=seed + 80 + k, sphere="uv", segs=(8, 5),
                   flat_top=0.85, flat_bottom=0.1, cuts=2, smooth=38)
        b.move(x, y, -0.03)
        A.add(moss_tint(b, 0.6, seed + k))
    A.extras = {"adit_point": [0.0, 0.0, -nd - 0.25], "worker_enter_point": [0.0, 0.0, -(fy + 0.6)],
                "lantern_points": [[-nw - 0.28, 1.4, -(fy + 0.32)], [nw + 0.28, 1.4, -(fy + 0.32)]]}
    return A


def tex_stall_atlas(seed=71, n=1024):
    """Weighstall cloth atlas. Top half: cream #E8DCC0 / sage #7E9A6E awning stripes (vertical in the
    image, 6 per u repeat, tileable in u). Bottom-left: sacking. Bottom-right: Rundling scales
    (overlapping umber #7A5A3A scales edged #B08A5A)."""
    def fn():
        rng = np.random.default_rng(seed)
        h = n // 2
        yy, xx = np.mgrid[0:h, 0:n] + 0.5
        u = xx / n
        ph = (u * 6) % 1.0
        stripe = np.where((np.floor(u * 6) % 2) == 0, 1.0, 0.0)[..., None]
        cream, sage = hexcol("#E8DCC0"), hexcol("#7E9A6E")
        col = cream * stripe + sage * (1 - stripe)
        pip = (np.exp(-((ph - 0.0) / 0.012) ** 2) + np.exp(-((ph - 1.0) / 0.012) ** 2))[..., None]
        col = col * (1 - 0.25 * np.clip(pip, 0, 1))
        fold = 0.88 + 0.12 * np.cos(u * 2 * math.pi * 12)[..., None]
        grime = L.periodic_noise(n, seed, 2.2)[:h][..., None]
        col = col * fold * (0.92 + 0.12 * grime)
        top = col
        # sacking
        q = n // 2
        yy, xx = np.mgrid[0:q, 0:q] + 0.5
        weave = 0.5 + 0.5 * np.sin(xx * math.pi / 2.5) * np.sin(yy * math.pi / 2.5)
        sack = hexcol("#B9A27E") * (0.8 + 0.12 * weave + 0.15 * L.periodic_noise(q, seed + 1, 2.0))[..., None]
        # scales: staggered rows of overlapping rounded scales
        rows, cols = 9, 8
        sy, sx = q / rows, q / cols
        r_ = (yy / sy)
        row = np.floor(r_)
        fy_ = r_ - row
        cx = (xx / sx + 0.5 * (row % 2)) % 1.0 - 0.5
        d = np.hypot(cx * 1.0, (fy_ - 0.05) * 0.9)
        edge = smoothstep(0.36, 0.48, d)
        base = hexcol("#7A5A3A") * (0.75 + 0.35 * (1 - fy_))[..., None]
        sc = base * (1 - edge[..., None]) + hexcol("#B08A5A") * edge[..., None]
        sc = sc * (0.9 + 0.2 * L.periodic_noise(q, seed + 2, 2.0))[..., None]
        bottom = np.concatenate([sack, sc], axis=1)
        return L.to_img(np.concatenate([top, bottom], axis=0))
    return lambda: L.cached_image(("stall_atlas", seed, n), fn)


def fit_uv(p, rect, rep=1.0):
    """Box-project, then squeeze the part's UVs into an atlas rect (u0, v0, u1, v1) with a margin."""
    uv = L.uv_box(p.v, p.t, rep)
    lo = uv.reshape(-1, 2).min(axis=0)
    hi = uv.reshape(-1, 2).max(axis=0)
    t = (uv - lo) / np.maximum(hi - lo, 1e-6)
    u0, v0, u1, v1 = rect
    m = 0.02
    p.uv = np.stack([u0 + m + t[..., 0] * (u1 - u0 - 2 * m), v0 + m + t[..., 1] * (v1 - v0 - 2 * m)], axis=-1)
    return p


def M_brass():
    return Mat("brass", L.swatch(SW + "clans_polished_bronze.png", seamless=True, tint=(1.08, 1.02, 0.8), sat=0.85),
               repeat=1.2, size=256)


def build_weighstall(aid):
    """Weighstall (neutrals §5.3): a timber market stall under a cream-and-sage striped awning, piled
    with crates, sacks and jars, crowned by a ~7 m brass balance (nodes balance_beam > balance_pan_l /
    balance_pan_r tip in the wind and swing on a purchase), a curled-up Rundling dozing on the counter
    (node shopkeeper: breathe by scaling), and a stall lantern (LAMP)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.0, ao_strength=1.0, base_dark=0.55, base_h=0.4, top_light=0.18)
    tim, brass, cloth, lamp = M_timber_light(), M_brass(), Mat("cloth", tex_stall_atlas(), repeat=1.0, size=512), M_lamp()
    STRIPE, SACK, SCALES = (0.0, 0.0, 1.0, 0.5), (0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0)

    def box(sz, c, mat=tim, ch=0.0, rot=None):
        b = L.box(sz, mat, chamfer=ch, center=c)
        if rot:
            b.rot(*rot, pivot=c)
        b.uv = L.uv_box(b.v, b.t, mat.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(b)
        return b
    # deck and counter
    box((3.7, 3.0, 0.18), (0.0, -0.05, 0.09))
    box((3.1, 0.6, 0.9), (0.0, 0.92, 0.63))
    box((3.35, 0.72, 0.08), (0.0, 0.98, 1.12), ch=0.02)
    # posts (front lower than back: the awning slopes to the front)
    for x in (-1.6, 1.6):
        box((0.16, 0.16, 2.4), (x, 1.18, 1.2), rot=(0, rng.uniform(-1.5, 1.5), 0))
        box((0.15, 0.15, 2.85), (x, -1.38, 1.43), rot=(0, rng.uniform(-1.5, 1.5), 0))
        box((0.1, 2.6, 0.12), (x, -0.1, 2.62), rot=(-9.5, 0, 0))
    # back wall with shelves and jars
    box((3.1, 0.08, 1.7), (0.0, -1.32, 1.03))
    for z in (1.0, 1.55):
        box((3.0, 0.32, 0.05), (0.0, -1.15, z))
    jar_cols = [(1.0, 0.75, 0.45), (0.6, 0.75, 0.55), (0.75, 0.4, 0.32), (1.0, 0.9, 0.7)]
    for z in (1.025, 1.575):
        x = -1.35
        while x < 1.35:
            hgt = rng.uniform(0.18, 0.3)
            rad = rng.uniform(0.07, 0.1)
            j = L.lathe([(0.0, 0.0), (rad, 0.0), (rad * 1.15, hgt * 0.45), (rad * 0.6, hgt * 0.9), (rad * 0.65, hgt),
                         (0.0, hgt)], 6, cloth)[0]
            fit_uv(j, (0.3, 0.05, 0.4, 0.45))
            j.tint = np.ones((len(j.v), 3)) * np.asarray(jar_cols[rng.integers(4)])
            j.move(x, -1.12 + rng.uniform(-0.04, 0.04), z)
            A.add(j)
            x += rad * 2 + rng.uniform(0.04, 0.12)
    # awning: striped sheet + scalloped valance at the front
    aw = sheet(cloth, [(-1.85, -1.5, 2.95), (1.85, -1.5, 2.95), (1.85, 1.28, 2.45), (-1.85, 1.28, 2.45)], 8, 5, sag=0.1,
               seed=seed)
    for p in aw:
        x = p.v[p.t][..., 0]
        y = p.v[p.t][..., 1]
        p.uv = np.stack([(x + 1.85) / 3.7 * 2.0, 0.03 + (y + 1.5) / 2.8 * 0.44], axis=-1)
        A.add(p)
    nd = 14
    verts, uvs = [], []
    for i in range(nd + 1):
        x = -1.85 + 3.7 * i / nd
        verts += [(x, 1.29, 2.46), (x, 1.31, 2.22 if i % 2 else 2.45)]
        uvs += [((x + 1.85) / 3.7 * 2.0, 0.46), ((x + 1.85) / 3.7 * 2.0, 0.49)]
    verts, uvs = np.array(verts), np.array(uvs)
    tris = []
    for i in range(nd):
        a, b, c, d = 2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1
        tris += [(a, b, c), (a, c, d)]
    tris = np.array(tris)
    for tt in (tris, tris[:, ::-1]):
        A.add(Part(verts, tt, cloth, uvs[tt], 60.0))
    # goods: sacks and crates in front of and on the counter
    for k, (x, y, z, s) in enumerate([(-1.25, 1.65, 0.18, 0.34), (-0.85, 1.7, 0.18, 0.3), (1.0, 1.06, 1.16, 0.22),
                                      (1.35, 1.65, 0.18, 0.32)]):
        sk = L.blob(cloth, s, scale=(0.85, 0.7, 0.9), seed=seed + k, sphere="uv", segs=(8, 5), noise_amp=0.1,
                    flat_bottom=0.15, smooth=60)
        sk.v[:, 2] *= 1 + 0.25 * smoothstep(s * 0.8, s * 1.4, sk.v[:, 2])
        sk.rot(rz=rng.uniform(0, 360)).move(x, y, z)
        fit_uv(sk, SACK)
        sk.tint = np.full((len(sk.v), 3), 0.72)
        A.add(sk)
    for k, (x, y, s, rz) in enumerate([(1.85, 0.9, 0.5, 15), (-1.9, 0.75, 0.55, -10), (-1.85, 0.75, 0.4, 30)]):
        z = 0.18 if k < 2 else 0.73
        box((s, s, s * 0.85), (x, y, z + s * 0.425), ch=0.025, rot=(0, 0, rz))
    # brass weighing pots on the counter
    for x in (-0.55, -0.3):
        p = L.lathe([(0.0, 0.0), (0.09, 0.0), (0.1, 0.12), (0.07, 0.16), (0.0, 0.16)], 7, brass)[0]
        p.move(x, 1.0, 1.16)
        A.add(p)
    # the Rundling, curled into a scaled ball, dozing on the counter
    sk_c = np.array([0.3, 1.1, 1.16])
    A.node("shopkeeper", sk_c)
    ball = L.uvsphere(10, 7, 0.3)
    bv, bt = ball
    bv = bv * np.array([1.0, 0.92, 0.85])
    bv[:, 2] += 0.255
    bp = Part(bv + sk_c, bt, cloth, None, 60.0)
    d = nrm(bv - np.array([0, 0, 0.255]))
    uvs = np.stack([0.5 + 0.48 * (0.5 + np.arctan2(d[:, 1], d[:, 0]) / (2 * math.pi)),
                    0.52 + 0.46 * (0.5 - np.arcsin(np.clip(d[:, 2], -1, 1)) / math.pi)], axis=1)
    bp.uv = uvs[bt]
    # fix the wrap seam: corners of a triangle spanning the seam get u + region width
    uu = bp.uv[..., 0]
    span = uu.max(axis=1) - uu.min(axis=1) > 0.3
    for f in np.nonzero(span)[0]:
        for k in range(3):
            if bp.uv[f, k, 0] < 0.75:
                bp.uv[f, k, 0] += 0.48
    bp.uv[..., 0] = np.clip(bp.uv[..., 0], 0.5, 0.995)
    bp.node = "shopkeeper"
    A.add(bp)
    tail = L.sweep(ngon(5, 1.0), bezier(sk_c + (0.18, -0.22, 0.05), sk_c + (0.38, 0.05, 0.08), sk_c + (0.2, 0.27, 0.12), 5),
                   cloth, scales=[0.11, 0.09, 0.07, 0.05, 0.02], cap1=True)[0]
    fit_uv(tail, (0.55, 0.55, 0.95, 0.95))
    tail.node = "shopkeeper"
    A.add(tail)
    snout = L.lathe([(0.06, 0.0), (0.045, 0.1), (0.02, 0.17), (0.0, 0.19)], 6, cloth)[0]
    snout.rot(ry=-75).move(*(sk_c + (-0.24, 0.12, 0.2)))
    fit_uv(snout, (0.6, 0.6, 0.7, 0.7))
    snout.node = "shopkeeper"
    A.add(snout)
    for dy in (-0.035, 0.035):
        g = L.lathe([(0.0, -0.004), (0.028, -0.004), (0.028, 0.004), (0.0, 0.004)], 6, brass)[0]
        g.rot(ry=90).move(*(sk_c + (-0.33, 0.12 + dy, 0.27)))
        g.node = "shopkeeper"
        A.add(g)
    # the giant balance: post, pivot, beam (node), chains and pans (child nodes)
    px, py = 0.0, -1.62
    box((0.8, 0.8, 0.45), (px, py, 0.22), mat=brass, ch=0.05)
    post = L.box((0.42, 0.42, 6.0), tim, center=(px, py, 3.3), chamfer=0.04)
    post.uv = L.uv_box(post.v, post.t, tim.repeat)
    A.add(post)
    for z in (1.2, 3.0, 4.8):
        box((0.5, 0.5, 0.14), (px, py, z), mat=brass, ch=0.02)
    piv = L.lathe([(0.0, 6.15), (0.34, 6.2), (0.4, 6.4), (0.3, 6.58), (0.1, 6.66), (0.17, 6.8), (0.07, 7.0),
                   (0.0, 7.1)], 8, brass)[0]
    piv.move(px, py, 0)
    A.add(piv)
    beam_c = np.array([px, py, 6.42])
    A.node("balance_beam", beam_c)
    span_x = 2.25
    bpath = np.array([(-span_x, py, 6.36), (-1.0, py, 6.44), (0.0, py, 6.47), (1.0, py, 6.44), (span_x, py, 6.36)])
    beam = L.sweep(np.array([(0.0, 0.11), (0.07, 0.0), (0.0, -0.11), (-0.07, 0.0)]), bpath, brass,
                   scales=[1.1, 1.5, 2.0, 1.5, 1.1], up=(0, 0, 1), cap0=True, cap1=True)[0]
    beam.node = "balance_beam"
    A.add(beam)
    for sx in (-1, 1):
        knob = L.lathe([(0.0, -0.17), (0.15, -0.1), (0.17, 0.0), (0.15, 0.1), (0.0, 0.17)], 7, brass)[0]
        knob.move(sx * span_x, py, 6.36)
        knob.node = "balance_beam"
        A.add(knob)
        name = "balance_pan_l" if sx < 0 else "balance_pan_r"
        hang = np.array([sx * (span_x - 0.05), py, 6.3])
        A.node(name, hang, parent="balance_beam")
        pan_z = 4.15
        prad = 0.82
        for k in range(3):
            a = k * 2 * math.pi / 3 + 0.5
            rim = np.array([hang[0] + math.cos(a) * prad * 0.92, py + math.sin(a) * prad * 0.92, pan_z + 0.14])
            for nh in ((1, 0, 0), (0, 1, 0)):
                ch = L.ribbon(np.array([hang, rim]), 0.05, brass, normal_hint=nh)
                ch.node = name
                ch.tint = np.full((len(ch.v), 3), 0.8)
                A.add(ch)
        pan = L.lathe([(0.0, pan_z), (prad * 0.55, pan_z + 0.02), (prad, pan_z + 0.14), (prad * 1.03, pan_z + 0.17),
                       (prad * 0.97, pan_z + 0.17), (prad * 0.55, pan_z + 0.07), (0.0, pan_z + 0.05)], 12, brass)[0]
        pan.move(hang[0], py, 0)
        pan.node = name
        A.add(pan)
        if sx < 0:
            sk = L.blob(cloth, 0.3, scale=(0.9, 0.75, 0.75), seed=seed + 40, sphere="uv", segs=(8, 5), noise_amp=0.1,
                        flat_bottom=0.2, smooth=60)
            sk.move(hang[0], py, pan_z + 0.06)
            fit_uv(sk, SACK)
            sk.node = name
            A.add(sk)
        else:
            for k, (dx, dy, r) in enumerate([(0.0, 0.0, 0.17), (0.0, 0.0, 0.12), (0.22, 0.12, 0.1)]):
                w = L.lathe([(0.0, 0.0), (r, 0.0), (r, 0.1), (r * 0.6, 0.13), (0.0, 0.13)], 7, brass)[0]
                w.move(hang[0] + dx, py + dy, pan_z + 0.06 + (0.1 * k if k < 2 else 0.0))
                w.node = name
                A.add(w)
    # stall lantern hanging under the front corner of the awning
    A.add(L.box((0.04, 0.04, 0.2), tim, center=(1.6, 1.72, 2.2)))
    A.add(lantern(tim, lamp, (1.6, 1.72, 2.12)))
    A.extras = {"counter_point": [0.0, 1.16, -1.0], "lantern_points": [[1.6, 1.8, -1.72]]}
    return A


def M_moss():
    return Mat("moss", L.swatch(TEX + "gv_thick_meadow.png", seamless=False, sat=0.9), repeat=2.0, size=256)


def build_hale_spring(aid):
    """Hale Spring (neutrals §5.8): a moss-ringed spring pool (walkable shallow water) fed by a
    hollow-log flume from a mossy source rock, with a tiny waterwheel (node `waterwheel`, spin about
    local X) under the flume's spout. Natural stones only: no carved rim, no glowing water (sparkles
    are VFX by day)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, ao_strength=1.0, base_dark=0.65, base_h=0.2, top_light=0.15)
    moss, rock, bark, water = M_moss(), M_rock(seed=12, moss_amt=1.3), M_bark(), M_water()
    # bank ring
    R0 = 1.0
    prof = [(R0 - 0.1, 0.02), (R0 + 0.06, 0.2), (R0 + 0.28, 0.3), (R0 + 0.5, 0.2), (R0 + 0.7, 0.0)]
    ring = L.lathe(prof, 20, moss, a0=0.1)[0]
    ring.jitter((0.06, 0.06, 0.025), seed, freq=1.8)
    ring.v[:, 2] = np.maximum(ring.v[:, 2], 0.0)
    ring.uv = L.uv_planar(ring.v, ring.t, (0, 1), 1 / moss.repeat)
    ring.nmode = "up"
    ring.nblend = 0.6
    A.add(ring)
    # water surface (shallow) and a darker floor rim under it
    K = 20
    ang = np.linspace(0, 2 * math.pi, K, endpoint=False)
    wv = np.vstack([[0.0, 0.0, 0.07]] + [[math.cos(a) * (R0 + 0.02), math.sin(a) * (R0 + 0.02), 0.07] for a in ang])
    wt = np.array([(0, i, i % K + 1) for i in range(1, K + 1)])
    wp = Part(wv, wt, water, L.uv_planar(wv, wt, (0, 1), 1 / water.repeat), 60.0)
    wp.nmode = "up"
    wp.ao = False
    wp.ao_fn = lambda q: 0.75 + 0.25 * smoothstep(R0, 0.2, np.hypot(q.v[:, 0], q.v[:, 1]))
    A.add(wp)
    # natural stones in the bank (irregular sizes, mossy)
    for k in range(8):
        a = k * 2 * math.pi / 8 + rng.uniform(-0.25, 0.25)
        if -2.0 < a - 3 * math.pi / 2 < -1.0 or abs(math.sin(a) + 1) < 0.15:
            pass
        r = rng.uniform(0.2, 0.34)
        b = L.blob(rock, r, scale=(1.0, 0.8, 0.62), seed=seed + 10 + k, sphere="uv", segs=(8, 5), noise_amp=0.16,
                   flat_top=0.82, flat_bottom=0.12, cuts=2, smooth=40)
        rr = R0 + rng.uniform(0.12, 0.35)
        b.rot(rz=math.degrees(a)).move(math.cos(a) * rr, math.sin(a) * rr, 0.08)
        A.add(moss_tint(b, 0.9, seed + k, patch=-0.1))
    # source rock at the back
    src = L.blob(rock, 0.95, subdiv=3, scale=(1.0, 0.72, 0.9), seed=seed + 30, noise_amp=0.15, flat_top=0.85,
                 flat_bottom=0.08, cuts=5, cut_depth=0.14, smooth=30)
    src.move(-0.35, -1.5, -0.05)
    src2 = L.blob(rock, 0.5, scale=(1.0, 0.8, 0.75), seed=seed + 31, noise_amp=0.15, flat_top=0.85, flat_bottom=0.1,
                  cuts=3, smooth=30, sphere="uv", segs=(8, 5))
    src2.move(0.65, -1.45, -0.04)
    A.add(moss_tint(src2, 1.0, seed + 31, patch=-0.2))
    A.add(moss_tint(src, 1.0, seed + 30, patch=-0.2))
    # hollow-log flume on a forked trestle
    f0 = np.array([-0.25, -1.3, 1.35])
    f1 = np.array([0.05, -0.42, 0.78])
    path = np.stack([f0, (f0 + f1) / 2, f1])
    K2 = 9
    ang = np.linspace(-0.25 * math.pi, 1.25 * math.pi, K2)      # open U (cut away on top)
    outer = np.stack([np.cos(ang) * 0.17, -np.sin(ang) * 0.17], axis=1)
    inner = np.stack([np.cos(ang[::-1]) * 0.11, -np.sin(ang[::-1]) * 0.11], axis=1)
    prof = np.vstack([outer, inner])
    log_ = L.sweep(prof, path, bark, up=(0, 0, 1), cap0=True, cap1=True)[0]
    A.add(log_)
    wr = L.ribbon(path + np.array([0, 0, -0.04]), 0.15, water, normal_hint=(0, 0, 1))
    wr.nmode = "up"
    wr.ao = False
    wr.ao_fn = lambda q: np.ones(len(q.v))
    A.add(wr)
    for dx in (-0.2, 0.2):
        mid = path[1]
        A.add(pole(bark, (mid[0] + dx, mid[1], -0.02), (mid[0] - dx * 0.3, mid[1], mid[2] + 0.08), 0.05, 0.045, sides=5))
    # spout trickle onto the wheel, then into the pool
    spout = f1 + nrm(f1 - f0) * 0.12
    fall = L.ribbon(np.array([spout, spout + np.array([0, 0.1, -0.2]), np.array([spout[0], spout[1] + 0.3, 0.08])]),
                    0.11, water, normal_hint=(0, 1, 0.4))
    fall.ao = False
    fall.ao_fn = lambda q: np.ones(len(q.v))
    A.add(fall)
    # tiny overshot waterwheel (axle along X), on two stakes
    wc = np.array([spout[0], spout[1] + 0.32, 0.43])
    A.node("waterwheel", wc)
    wr_ = 0.32
    parts = []
    for dx in (-0.09, 0.09):
        a = np.linspace(0, 2 * math.pi, 13)
        rim_path = np.stack([np.full(13, dx), np.cos(a) * wr_, np.sin(a) * wr_], axis=1) + wc
        rim = L.sweep(np.array([(0.025, 0.015), (0.025, -0.015), (-0.025, -0.015), (-0.025, 0.015)]), rim_path, bark,
                      up=(1, 0, 0), cap0=False, cap1=False, smooth=30)[0]
        parts.append(rim)
    for k in range(8):
        a = k * 2 * math.pi / 8
        pd = L.box((0.22, 0.03, 0.13), bark, center=(0, 0, wr_ - 0.05))
        pd.rot(rx=math.degrees(a)).move(*wc)
        parts.append(pd)
    hub = L.lathe([(0.0, -0.16), (0.05, -0.15), (0.05, 0.15), (0.0, 0.16)], 6, bark)[0]
    hub.rot(ry=90).move(*wc)
    parts.append(hub)
    for p in parts:
        p.uv = L.uv_box(p.v, p.t, bark.repeat)
        p.node = "waterwheel"
        A.add(p)
    for dx in (-0.2, 0.2):
        A.add(pole(bark, (wc[0] + dx, wc[1], 0.0), (wc[0] + dx, wc[1], wc[2] + 0.05), 0.035, 0.03, sides=4))
    # grass and flower tufts on the bank (lush, SWAY)
    meadow = M_meadow()
    for k in range(9):
        a = k * 2 * math.pi / 9 + rng.uniform(-0.2, 0.2)
        if math.sin(a) < -0.75:
            continue
        rr = R0 + rng.uniform(0.4, 0.65)
        cell = [3, 3, 1, 3, 0, 3, 2, 3, 1][k]
        for j in range(2):
            c = L.card(0.55, 0.45, meadow, cell_rect(cell), segs=(1, 1), pivot="bottom")
            c.rot(rx=rng.uniform(-10, 10)).rot(rz=math.degrees(a) + 90 * j + rng.uniform(-20, 20))
            c.move(math.cos(a) * rr, math.sin(a) * rr, 0.05)
            c.nmode = "up"
            c.ao = False
            c.ao_fn = lambda q: 0.6 + 0.4 * np.clip((q.v[:, 2] - 0.05) / 0.45, 0, 1)
            c.sway = np.clip((c.v[:, 2] - 0.05) / 0.45, 0, 1)
            c.phase = rng.uniform(0, 1)
            A.add(c)
    A.extras = {"pool_radius": R0, "aura_radius": 7.8}
    return A


def build_gold_mine_collapsed(aid):
    """Empty Gold Seam: the adit has fallen in, the headframe tipped, the sluice lies dry. Walkable
    rubble that replaces gold_mine (same footprint centre and facing)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, base_dark=0.6, base_h=0.3, top_light=0.15)
    rock, tim = M_rock(seed=14), M_timber()
    # low rubble mounds
    for k, (x, y, r, h) in enumerate([(0.1, -0.6, 1.5, 0.5), (-1.2, 0.5, 0.85, 0.3), (1.3, 0.3, 0.8, 0.26),
                                      (-0.9, -1.4, 0.7, 0.28), (0.4, 0.9, 0.6, 0.2)]):
        m = L.lathe([(r, 0.0), (r * 0.8, h * 0.45), (r * 0.4, h * 0.9), (0.0, h)], 10, rock, a0=k * 0.3)[0]
        m.v[:, 1] *= 0.8
        m.jitter((0.12, 0.12, 0.06), seed + k, freq=2.4)
        m.v[:, 2] = np.maximum(m.v[:, 2], 0.0)
        m.move(x, y, -0.02)
        m.uv = L.uv_box(m.v, m.t, 1.6, (k * 0.31, k * 0.17))
        moss_tint(m, 0.5, seed + k, patch=0.3)
        A.add(m)
    # fallen slabs and stones
    for k in range(16):
        b = L.blob(rock, rng.uniform(0.15, 0.4), scale=(1.0, 0.75, rng.uniform(0.35, 0.6)), seed=seed + 10 + k,
                   sphere="uv", segs=(7, 4), flat_top=0.8, flat_bottom=0.15, cuts=2, smooth=38)
        b.rot(rz=rng.uniform(0, 360), rx=rng.uniform(-15, 15))
        b.move(rng.uniform(-1.9, 1.9), rng.uniform(-1.7, 1.6), -0.03)
        A.add(b)
    # broken adit timbers and the tipped headframe
    for k, (p0, p1, r) in enumerate([((-0.9, 1.2, 0.05), (0.5, 0.8, 0.45), 0.1), ((0.8, 1.3, 0.05), (0.9, 0.2, 0.55), 0.1),
                                     ((-0.4, 1.5, 0.08), (1.4, 1.6, 0.1), 0.12), ((-1.6, -0.6, 0.06), (-0.3, -1.4, 0.5), 0.07),
                                     ((-1.4, -1.2, 0.06), (-0.5, -0.4, 0.62), 0.07)]):
        b = L.box((np.linalg.norm(np.subtract(p1, p0)), r * 2, r * 2), tim)
        d = np.subtract(p1, p0)
        yaw = math.degrees(math.atan2(d[1], d[0]))
        pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
        b.rot(ry=-pitch).rot(rz=yaw).move(*((np.asarray(p0) + np.asarray(p1)) / 2))
        b.uv = L.uv_box(b.v, b.t, tim.repeat, (k * 0.2, 0))
        A.add(b)
    drum = L.lathe([(0.0, -0.5), (0.18, -0.48), (0.18, 0.48), (0.0, 0.5)], 7, tim)[0]
    drum.rot(ry=90).rot(rz=35).move(-0.9, -0.9, 0.2)
    A.add(drum)
    trough = L.sweep(np.array([(0.13, 0.12), (0.13, -0.02), (-0.13, -0.02), (-0.13, 0.12), (-0.1, 0.12), (-0.1, 0.02),
                               (0.1, 0.02), (0.1, 0.12)]), np.array([(1.2, -1.5, 0.05), (2.0, 0.9, 0.05)]), tim,
                     up=(0, 0, 1), cap0=True, cap1=True)[0]
    trough.uv = L.uv_box(trough.v, trough.t, tim.repeat)
    trough.rot(ry=8, pivot=(1.6, 0, 0))
    A.add(trough)
    return A


# =============================================================================================
# registry
# =============================================================================================

REGISTRY = {}


def asset(aid, out="doodads", category="doodad", footprint=None, blocks_sight=False, sway=False, lods=None,
          notes=""):
    """footprint: (w, d) in 0.5 m pathing cells blocked by the object, or None (decorative,
    walkable). Trees use the 2x2-cell tree grid of architecture.md §7."""
    def deco(fn):
        REGISTRY[aid] = dict(fn=fn, out=out, category=category, footprint=footprint, blocks_sight=blocks_sight,
                             sway=sway, lods=lods or [], notes=notes)
        return fn
    return deco


TREE_NOTE = ("Tree-grid doodad: blocks 2x2 cells (1 m) of pathing and sight; harvestable (rules §4.2, 50 lumber); "
             "leaves a tree_stump when felled. Place with ±20 % scale, random yaw, ±3° hue jitter (bible §6.4).")


@asset("tree_hill_oak", category="tree", footprint=(2, 2), blocks_sight=True, sway=True, lods=["tree_hill_oak_lod1"],
       notes=TREE_NOTE + " Default tree-wall species.")
def a_oak():
    return build_tree("tree_hill_oak", spec_oak(seed_of("tree_hill_oak")))


@asset("tree_hill_oak_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes="Low LOD / impostor source of tree_hill_oak: same materials and atlas, closed leafy hulls "
             "+ 4 cards per cluster, no thin branches (clean silhouette for octahedral impostor baking).")
def a_oak_lod():
    return build_tree("tree_hill_oak_lod1", spec_oak(seed_of("tree_hill_oak")), lod=1)


@asset("tree_linden", category="tree", footprint=(2, 2), blocks_sight=True, sway=True, lods=["tree_linden_lod1"],
       notes=TREE_NOTE + " Taller rounded cone with summer blossom; mix into tree lines near kingdom starts.")
def a_linden():
    return build_tree("tree_linden", spec_linden(seed_of("tree_linden")))


@asset("tree_linden_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes="Low LOD / impostor source of tree_linden.")
def a_linden_lod():
    return build_tree("tree_linden_lod1", spec_linden(seed_of("tree_linden")), lod=1)


@asset("tree_hazel", category="tree", footprint=(2, 2), blocks_sight=True, sway=True, lods=["tree_hazel_lod1"],
       notes=TREE_NOTE + " Many-stemmed coppice that fills gaps inside tree lines (harvestable like the others).")
def a_hazel():
    return build_tree("tree_hazel", spec_hazel(seed_of("tree_hazel")))


@asset("tree_hazel_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes="Low LOD / impostor source of tree_hazel.")
def a_hazel_lod():
    return build_tree("tree_hazel_lod1", spec_hazel(seed_of("tree_hazel")), lod=1)


@asset("rock_boulder_small", category="rock", footprint=(2, 2), notes="Mossy flat-topped boulder ~0.9 m; cluster 3-7 objects at transitions (bible §6.4).")
def a_rock_s():
    return build_boulder("rock_boulder_small", "small")


@asset("rock_boulder_medium", category="rock", footprint=(3, 3), notes="Mossy flat-topped boulder ~1.4 m.")
def a_rock_m():
    return build_boulder("rock_boulder_medium", "medium")


@asset("rock_boulder_large", category="rock", footprint=(4, 4), notes="Mossy boulder ~2.4 m with a leaning companion stone.")
def a_rock_l():
    return build_boulder("rock_boulder_large", "large")


@asset("wall_drystone_straight", category="wall", footprint=(4, 2),
       notes="2 m module on the tile centre line (X -1..1), 1.3 m with coping; blocks pathing, not sight.")
def a_wall_s():
    return build_wall_straight("wall_drystone_straight")


@asset("wall_drystone_corner", category="wall", footprint=(4, 4),
       notes="Corner module joining a straight on the west (-X) and one on the north (-Z); rotate for other corners.")
def a_wall_c():
    return build_wall_corner("wall_drystone_corner")


@asset("wall_drystone_end_broken", category="wall", footprint=(4, 2),
       notes="Broken end: full height at -X, crumbling toward +X with tumbled stones (walkable beyond x > 1).")
def a_wall_b():
    return build_wall_broken("wall_drystone_end_broken")


@asset("hedge_hawthorn", category="hedge", footprint=(4, 2), sway=True,
       notes="Hawthorn hedgerow 2 m module along X: blocks pathing but not sight; non-harvestable; never inside a tree line.")
def a_hedge():
    return build_hedge("hedge_hawthorn")


@asset("fence_wattle", category="fence", footprint=(4, 1), notes="Woven hazel hurdle, 2 m module along X.")
def a_fence():
    return build_wattle("fence_wattle")


@asset("hay_stook", category="prop", footprint=(2, 2), notes="Leaning sheaves; scatter in fields near kingdom-side farms.")
def a_stook():
    return build_hay_stook("hay_stook")


@asset("tree_stump", category="tree_stump", footprint=None,
       notes="Replaces a felled tree (walkable). Pale rings #E9CF9B on the cut.")
def a_stump():
    return build_stump("tree_stump")


@asset("tree_felled_log", category="prop", footprint=(7, 2),
       notes="Fallen oak log, 3.6 m along X; shores and woodland floors.")
def a_log():
    return build_log("tree_felled_log")


@asset("reeds_clump", category="shore", footprint=None, sway=True,
       notes="Reeds and bulrushes, shores only (bible §6.3); walkable decoration.")
def a_reeds():
    return build_reeds("reeds_clump")


@asset("lily_pads", category="shore", footprint=None,
       notes="Lily pads with white flowers; origin = water surface (place at the water height).")
def a_lily():
    return build_lily_pads("lily_pads")


@asset("wildflowers_yellow", category="meadow_card", footprint=None, sway=True, notes="Yellow wildflower clump (cards).")
def a_wf_y():
    return build_meadow_clump("wildflowers_yellow", 0)


@asset("wildflowers_white", category="meadow_card", footprint=None, sway=True, notes="White wildflower clump (cards).")
def a_wf_w():
    return build_meadow_clump("wildflowers_white", 1)


@asset("wildflowers_mixed", category="meadow_card", footprint=None, sway=True,
       notes="Mixed clump: yellow and white with a few tiny blue flowers (blue only as tiny flowers).")
def a_wf_m():
    return build_meadow_clump("wildflowers_mixed", 2)


@asset("grass_tuft", category="meadow_card", footprint=None, sway=True, notes="Grass tuft cards for clusters and cliff lips.")
def a_grass():
    return build_meadow_clump("grass_tuft", 3, size=0.7, n=3, extra=3)


@asset("mushroom_ring", category="prop", footprint=None, notes="Fairy ring of pale caps, deep woods only.")
def a_mush():
    return build_mushroom_ring("mushroom_ring")


@asset("cart_broken", category="prop", footprint=(6, 4), notes="Wrecked market wagon (kingdom painted side boards).")
def a_cart():
    return build_cart("cart_broken")


@asset("milestone", category="prop", footprint=(1, 1), notes="Roadside milestone, neutral; along roads.")
def a_mile():
    return build_milestone("milestone")


@asset("cairn_small", category="prop", footprint=(2, 2), notes="Small roadside cairn of flat stones.")
def a_cairn():
    return build_cairn("cairn_small")


@asset("camp_campfire", category="camp", footprint=(3, 3),
       notes="Stone-ringed campfire with a cooking tripod; EMBER material glows (flames and smoke are VFX).")
def a_fire():
    return build_campfire("camp_campfire")


@asset("camp_lean_to", category="camp", footprint=(6, 6), notes="Sootcoat lean-to, open side to the front (-Z).")
def a_leanto():
    return build_lean_to("camp_lean_to")


@asset("camp_tent", category="camp", footprint=(4, 4), notes="Small patched ridge tent, door to the front (-Z).")
def a_tent():
    return build_tent("camp_tent")


@asset("camp_charcoal_clamp", category="camp", footprint=(7, 7),
       notes="Turf-covered charcoal clamp (Charcoal Clamp / Charcoal Yard / Collier's Hut camps); EMBER vents; "
             "emit smoke VFX at extras.smoke_points (Godot space).")
def a_clamp():
    return build_charcoal_clamp("camp_charcoal_clamp")


@asset("camp_cordwood_stack", category="camp", footprint=(4, 2), notes="Cordwood stack, end grain to the front.")
def a_cord():
    return build_cordwood("camp_cordwood_stack")


@asset("camp_crates", category="camp", footprint=(4, 3), notes="Crates, a barrel and sacks (camp stores, Smugglers' Den).")
def a_crates():
    return build_crates("camp_crates")


@asset("camp_scarecrow_pole", category="camp", footprint=(1, 1),
       notes="Tattiebogle field pole (Turnip Patch / Crow Field): the creeps slump on these by day.")
def a_pole():
    return build_scarecrow_pole("camp_scarecrow_pole")


@asset("camp_turnip_rows", category="camp", footprint=None, sway=True,
       notes="Turnip Patch furrows, walkable (4.6 x 2.4 m); pair with gv_thick_meadow + furrows ground paint.")
def a_turnips():
    return build_turnip_rows("camp_turnip_rows")


@asset("camp_haystack", category="camp", footprint=(5, 5), notes="Crow-picked haystack (Turnip Patch / Crow Field).")
def a_hay():
    return build_haystack("camp_haystack")


@asset("camp_standing_stone", category="camp", footprint=(2, 2), blocks_sight=False,
       notes="Standing Ring / Cairnwake menhir with cup-and-ring marks: GLYPH material is emissive #E8E29A, "
             "drive its emission to 0 by day and ~1.5 at night.")
def a_menhir():
    return build_standing_stone("camp_standing_stone")


@asset("beehive_skeps", category="prop", footprint=(3, 2), notes="Straw skeps on a plank bench, near kingdom-side farms.")
def a_skeps():
    return build_skeps("beehive_skeps")


@asset("gold_mine", out="neutral", category="neutral_building", footprint=(8, 8), blocks_sight=True,
       notes="Gold Seam (neutrals §5.2): 8x8 cells, front (adit) faces -Z; spawn with facing PI so it faces the "
             "default camera. Materials: rock + timber, seam_GLOW (gold stratum: pulse emission when a worker "
             "enters), lamp_LAMP (two lanterns, lit at night), water_WATER (sluice trickle). Node windlass_drum "
             "spins about its local X axis while mining. Per the bible's squint test there is no mine cart and no "
             "rails (the task brief's 'small cart' is overridden by neutrals §5.2 / §10.2).")
def a_mine():
    return build_gold_mine("gold_mine")


@asset("neutral_weighstall", out="neutral", category="neutral_building", footprint=(8, 8), blocks_sight=True,
       notes="Weighstall merchant (neutrals §5.3): 8x8 cells, counter faces -Z (spawn with facing PI). Nodes: "
             "balance_beam (pivot at the beam centre, rotate about local Z to tip) > balance_pan_l / balance_pan_r "
             "(pivots at the hanging points: counter-rotate so the pans hang plumb), shopkeeper (curled Rundling: "
             "breathe by scaling, uncurl on purchase is VFX/anim). The balance beam reaches 7 m (exempt from the "
             "height ratio). lamp_LAMP lit at night.")
def a_shop():
    return build_weighstall("neutral_weighstall")


@asset("neutral_hale_spring", out="neutral", category="neutral_building", footprint=None, sway=True,
       notes="Hale Spring (neutrals §5.8): 6x6 cells, the pool is walkable shallow water (no blocking; the source "
             "rock at the back may block 2x2 cells). Front faces -Z. Node waterwheel spins about local X. "
             "water_WATER is the pool surface (swap for the game's water shader if wanted); warm sparkles are VFX.")
def a_spring():
    return build_hale_spring("neutral_hale_spring")


@asset("gold_mine_collapsed", out="neutral", category="neutral_building", footprint=None,
       notes="Empty Gold Seam (neutrals §5.2 'collapses when empty'): walkable rubble that replaces gold_mine at "
             "the same position and facing; play a dust puff when swapping.")
def a_mine_rubble():
    return build_gold_mine_collapsed("gold_mine_collapsed")


# =============================================================================================
# export + manifest
# =============================================================================================

def gltf_bounds(A: Asset):
    lo, hi = A.bounds()
    # build (x, y, z) -> godot (x, z, -y)
    g_lo = np.array([lo[0], lo[2], -hi[1]])
    g_hi = np.array([hi[0], hi[2], -lo[1]])
    return g_lo, g_hi


def build_one(aid):
    meta = REGISTRY[aid]
    t0 = time.time()
    A = meta["fn"]()
    out_dir = OUT_DOODADS if meta["out"] == "doodads" else OUT_NEUTRAL
    path = os.path.join(out_dir, aid + ".glb")
    mats = A.export(path)
    lo, hi = gltf_bounds(A)
    size = hi - lo
    nodes = []
    for name in A.node_order:
        if not name:
            continue
        nd = A.nodes[name]
        pv = nd["pivot"]
        nodes.append({"name": name, "parent": nd["parent"] or aid,
                      "pivot": [round(float(pv[0]), 3), round(float(pv[2]), 3), round(float(-pv[1]), 3)]})
    entry = {
        "id": aid,
        "path": os.path.relpath(path, REPO),
        "category": meta["category"],
        "size": [round(float(x), 3) for x in size],
        "aabb_min": [round(float(x), 3) for x in lo],
        "tris": A.tris(),
        "footprint_cells": list(meta["footprint"]) if meta["footprint"] else None,
        "blocks_pathing": bool(meta["footprint"]),
        "blocks_sight": bool(meta["blocks_sight"]),
        "sway": bool(meta["sway"]),
        "materials": [m.gltf_name(aid) for m in mats],
        "texel_density_px_per_m": {m.gltf_name(aid): round(m.size / m.repeat) for m in mats
                                   if m.repeat and m.key not in ("leaves", "meadow", "cloth", "glyph", "lily", "mushroom",
                                                                 "reeds", "endgrain", "turnip")},
        "lods": meta["lods"],
        "nodes": nodes,
        "notes": meta["notes"],
    }
    if aid.endswith("_lod1"):
        entry["lod_of"] = aid[:-5]
    if A.extras:
        ex = {k: v for k, v in A.extras.items() if k not in ("kind", "lod")}
        if ex:
            entry["extras"] = ex
    log(f"  {aid}: {entry['tris']} tris, size {entry['size']}, {time.time() - t0:.1f}s")
    return entry


def write_manifest(entries):
    path = os.path.join(OUT_DOODADS, "manifest.json")
    old = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                for e in json.load(f).get("assets", []):
                    old[e["id"]] = e
        except Exception:  # noqa: BLE001
            old = {}
    for e in entries:
        old[e["id"]] = e
    order = [k for k in REGISTRY if k in old]
    data = {
        "generator": "tools/kits/doodads.py",
        "conventions": {
            "units": "metres, Y up, origin at footprint centre on the ground",
            "facing": "front (door, adit, counter, open side) faces -Z like units; the default RtsCamera sits on the +Z "
                      "side, so spawn neutral buildings with facing = PI for the door-toward-camera look",
            "nodes": "animated parts are child nodes whose origin is the pivot (Godot space, relative to the asset root)",
            "footprint_cells": "suggested blocked pathing cells [x, z] (0.5 m cells); null = walkable decoration",
            "sway_materials": "name contains SWAY: alpha scissor; COLOR_0 R sway weight (0 trunk base -> 1 canopy "
                              "edge), G painted AO, B cluster phase; shader tools/kits/foliage_sway.gdshader",
            "other_materials": "COLOR_0 RGB painted AO / base darkening / moss tint: multiply into the albedo. Godot's "
                               "glTF importer leaves vertex_color_use_as_albedo off: set it on every material whose "
                               "meta 'extras'.vc_vertex_color == 'multiply' (see tools/kits/lineup.gd _fix_materials)",
            "uv2": "x sway weight, y normalized height 0..1 (build_progress reveal: discard where UV2.y > progress)",
            "emissive": "materials tagged GLOW / LAMP / EMBER / GLYPH are emissive; scale emission energy to pulse",
            "team_colour": "none: neutrals and doodads never carry team colour (art bible §3.1 rule 8)",
        },
        "assets": [old[k] for k in order],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=1, sort_keys=False)
        f.write("\n")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="comma list of ids (prefix* allowed)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(L_argv())
    if args.list:
        for k, m in REGISTRY.items():
            print(f"{k:32s} {m['out']:8s} {m['category']}")
        return
    ids = list(REGISTRY)
    if args.only:
        want = [w.strip() for w in args.only.split(",") if w.strip()]
        ids = [i for i in ids if any(i == w or (w.endswith("*") and i.startswith(w[:-1])) for w in want)]
    entries = []
    for aid in ids:
        entries.append(build_one(aid))
    mpath = write_manifest(entries)
    print(json.dumps({"built": [e["id"] for e in entries], "manifest": os.path.relpath(mpath, REPO),
                      "tris": {e["id"]: e["tris"] for e in entries}}, indent=1))


def L_argv():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:]


if __name__ == "__main__":
    main()
