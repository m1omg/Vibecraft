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
  * COLOR_0 on every material, foliage included: RGB = painted AO / base darkening / moss tint (multiply),
    A = 1. Every mesh starts with a hidden 1 mm dummy triangle, so Godot's plain glTF import sets
    vertex_color_use_as_albedo on every material (it skips a mesh's first primitive); the game loader should
    still set it explicitly on every kit material.
  * SWAY materials (foliage): alpha scissor (glTF MASK, cutoff in the material), double sided; sway weight in
    TEXCOORD_1.x, cluster phase in TEXCOORD_2.x (Godot CUSTOM0.x). Reference shader:
    tools/kits/foliage_sway.gdshader (a plain StandardMaterial3D also renders them correctly, just static).
  * TEXCOORD_1 (UV2) on every vertex of every asset: x = sway weight (0 on rigid props), y = normalized
    height (0 ground .. 1 top) for the build_progress / collapse reveal shader:
        discard if UV2.y > build_progress (plus a noisy band for a scaffold-coloured edge).
  * Atlas materials (Gold Seam, Weighstall, Hale Spring, collapsed seam, milestone): one texture of tiled
    cells; triangles are cut on the cell repeat lines at export, so every cell keeps ~128-160 px/m.
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
    # bible §1.4: trees and foliage <= 60 % saturation (HSV median ~0.48, p95 <= 0.58 after the cap)
    return Mat("bark", L.swatch(TEX + "bark_oak.png", seamless=False, sat=0.85, s_scale=0.74, s_cap=0.58),
               repeat=2.0, size=256)


def M_bark_hazel():
    # hazel: smooth grey-brown bark (desaturated, lighter, finer)
    return Mat("bark", L.swatch(TEX + "bark_oak.png", seamless=False, sat=0.45, tint=(1.05, 1.0, 0.95),
                                gamma=0.85, s_cap=0.5), repeat=1.6, size=256)


def M_leaves(kind="oak"):
    """Leaf-clump atlases. Saturation is scaled to a median of ~0.48 and soft-capped at 0.58 (bible §1.4:
    foliage <= 60 %); highlight values are compressed so the dark interior and lit tips stay one
    big shape instead of high-frequency noise."""
    if kind == "oak":
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.8, 0.95, 0.9), sat=0.78, val=0.9, s_scale=0.7,
                              s_cap=0.58, v_knee=0.5)
    elif kind == "linden":
        # sparse pale-yellow summer blossom #E8E2A0 in small clusters (3-4 px at the game camera)
        img = L.foliage_atlas(FOL + "linden_clumps.png", hue_tint=(0.98, 1.02, 0.84), sat=0.82, val=0.98,
                              s_scale=0.74, s_cap=0.58, v_knee=0.56, blossom=["#E8E2A0", "#EFEAB6", "#DED690"],
                              seed=5, blossom_n=150, blossom_r=(2.4, 3.2), blossom_cluster=5, blossom_spread=6.5,
                              blossom_centre=(206, 190, 104))
    elif kind == "hazel":
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.9, 0.98, 0.86), sat=0.7, val=0.95, s_scale=0.74,
                              s_cap=0.58, v_knee=0.54)
    elif kind == "hawthorn":
        # white blossom in clusters big enough to read at RTS distance (3-5 px: ~45-60 px in the 1024 atlas)
        img = L.foliage_atlas(FOL + "oak_clumps.png", hue_tint=(0.86, 0.95, 0.88), sat=0.72, val=0.84, s_scale=0.72,
                              s_cap=0.56, v_knee=0.5, blossom=["#F6F2E6", "#EFE9DA", "#FBF8F0"], seed=7,
                              blossom_n=260, blossom_r=(3.4, 4.6), blossom_cluster=7, blossom_spread=10.0,
                              blossom_centre=(236, 214, 128))
    else:
        raise ValueError(kind)
    return Mat("leaves", img, size=512, alpha=True, cutoff=0.42, double=True, sway=True, uv_kind="atlas")


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

def lathe_u_per_ring(p):
    """Lathe UVs use the widest ring's circumference for u; rescale u per vertex by its own radius so every
    ring keeps the same texel density (no stretch up a flared trunk). Caps (horizontal faces) are left alone."""
    r = np.hypot(p.v[:, 0], p.v[:, 1])
    rmax = max(float(r.max()), 1e-6)
    P = p.v[p.t]
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    side = np.abs(fn[:, 2]) < 0.9 * np.linalg.norm(fn, axis=1)
    p.uv[side, :, 0] = p.uv[side, :, 0] * (r[p.t[side]] / rmax)
    return p


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
    p = lathe_u_per_ring(parts[0])
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
                 upright=0.25, keep=None):
    """One leaf clump cluster: outward-facing bent alpha cards on a sphere + a small leafy hull that
    blocks see-through (mapped into the fully opaque centre of an atlas cell; it sits in the dark
    interior, so its coarse texel density never shows). Normals point away from a point a little
    below the cluster centre (soft painted volume, lit tops)."""
    rng = np.random.default_rng(seed)
    c = np.asarray(c, float)
    parts = []
    for k, d in enumerate(fib_dirs(n_cards, seed)):
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
        if keep is None or keep(k):
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


def cone_hull(mat, prof, seed, cells=(0, 1, 2, 3), sides=9):
    """Leafy tapering hull (lathe of [(r, z) ...]) mapped into the opaque centre of an atlas cell:
    blends a linden's clusters into one cone and stops see-through."""
    rng = np.random.default_rng(seed + 9)
    p = L.lathe(prof, sides, mat, a0=rng.uniform(0, 1))[0]
    p.jitter((0.12, 0.12, 0.08), seed, freq=0.9)
    d = nrm(p.v - np.array([0, 0, np.mean([z for _, z in prof])]))
    cell = int(cells[rng.integers(len(cells))])
    cc = cell_centre(cell)
    uvv = cc + np.stack([d[:, 0] * 0.1 + d[:, 1] * 0.035, -d[:, 2] * 0.1], axis=1)
    p.uv = uvv[p.t]
    p.nmode = "sphere"
    p.ncenter = np.array([0, 0, prof[0][1] + (prof[-1][1] - prof[0][1]) * 0.35])
    p.nblend = 0.95
    p.occ = 0.5
    p.ao = False
    return p


def foliage_ao(c, R, zlo, zhi, inner=0.42, low=0.7, gain=1.0):
    c = np.asarray(c, float)

    def fn(p):
        d = np.linalg.norm(p.v - c, axis=1) / R
        a = inner + (1 - inner) * smoothstep(0.15, 1.05, d)
        h = low + (1 - low) * smoothstep(zlo, zhi, p.v[:, 2])
        return a * h * gain
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
    """Generic broadleaf: trunk with root flare, branches into each cluster, clusters of cards.
    lod 1: LOD0's own cards (3 in 5 kept) as 4-triangle fans, a 20-triangle hull per cluster, no thin branches.
    lod 2: a 2-triangle impostor card (see build_tree_impostor)."""
    base_id = aid.replace("_lod1", "").replace("_lod2", "")
    if lod == 2:
        return build_tree_impostor(aid, base_id, spec)
    seed = seed_of(base_id)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.4, ao_strength=0.9, base_dark=0.5, base_h=0.5, top_light=0.18)
    bark, leaves = spec.bark(), spec.leaves()
    clusters = spec.clusters
    zlo = min(c[2] - R for c, R in clusters)
    zhi = max(c[2] + R for c, R in clusters)
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
            for i, (c, R) in enumerate(clusters[:getattr(spec, "branch_n", len(clusters))]):
                c = np.asarray(c, float)
                dirxy = c[:2] - top[:2]
                p0 = top - np.array([0, 0, 0.35]) + np.r_[nrm(dirxy) * spec.r_top * 0.3 if np.linalg.norm(dirxy) > 0.1 else np.zeros(2), 0]
                p2 = c - np.array([0, 0, R * 0.35])
                p1 = p0 + (p2 - p0) * np.array([0.35, 0.35, 0.75])
                for bp in branch(bark, p0, p1, p2, spec.r_top * 0.62, spec.r_top * 0.16, seed + i, sides=5):
                    sw_bark(bp)
                    A.add(bp)
    else:
        # coppice: several stems splaying out of a low stool
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
    leaf_parts = []
    for i, (c, R) in enumerate(clusters):
        if lod == 0:
            parts = leaf_cluster(leaves, c, R, seed + 101 * i, n_cards=spec.cards, card_scale=spec.card_scale,
                                 cells=spec.cells, bend=0.28, hull=getattr(spec, "cluster_hull", True),
                                 hull_subdiv=getattr(spec, "hull_subdiv", 1),
                                 squash=spec.squash)
        else:
            # LOD1: the LOD0 cards themselves (same centres, directions, sizes and atlas cells), 3 in 5 kept,
            # each a 4-triangle fan through its LOD0 corners and centre, and a 20-triangle hull: no rescaling,
            # the crown keeps LOD0's outline and shading
            parts = leaf_cluster(leaves, c, R, seed + 101 * i, n_cards=spec.cards, card_scale=spec.card_scale,
                                 cells=spec.cells, segs="fan", bend=0.28, hull=getattr(spec, "cluster_hull", True),
                                 hull_subdiv=0, squash=spec.squash, keep=lambda k: k % 5 not in (1, 3))
        ph = (i * 0.618 + rng.uniform(0, 0.2)) % 1.0
        for p in parts:
            p.ao_fn = foliage_ao(c, R, zlo, zhi)
            p.phase = ph
            leaf_parts.append(p)
        if lod == 1 and getattr(spec, "cluster_hull", True):
            # the 20-triangle hull has big flat faces: keep it in the canopy's shade so it reads as depth
            parts[-1].ao_fn = foliage_ao(c, R, zlo, zhi, gain=0.7)
    if getattr(spec, "cone", None):
        cp = cone_hull(leaves, spec.cone, seed, spec.cells, sides=9)
        # the hull is interior volume: keep it in shadow so its magnified texels read as depth (deeper at LOD1,
        # where 2 in 5 cards are dropped and more of it shows)
        k_ = 1.0 if lod == 0 else 0.78
        cp.ao_fn = lambda q: (0.34 + 0.2 * np.clip((q.v[:, 2] - zlo) / max(zhi - zlo, 1e-3), 0, 1)) * k_
        cp.phase = 0.37
        leaf_parts.append(cp)
    A.add(leaf_parts)
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


def rts_axes(pitch=56.0):
    """Build-space screen axes of the game camera at yaw 0 (it sits on Godot +Z = build -Y):
    right, up (in the image plane) and toward-camera."""
    p = math.radians(pitch)
    right = np.array([1.0, 0.0, 0.0])
    toward = np.array([0.0, -math.cos(p), math.sin(p)])
    up = np.array([0.0, math.sin(p), math.cos(p)])
    return right, up, toward


def sun_build():
    """Direction toward the lineup / DayNight day sun (elevation 52 deg, from screen lower-left), build space."""
    e = math.radians(52)
    h = nrm(np.array([-0.72, 0.69]))
    return nrm(np.array([h[0] * math.cos(e), -h[1] * math.cos(e), math.sin(e)]))


def _mat_rgba(m: Mat):
    im = m.image()
    if im.size != (m.size, m.size):
        im = im.resize((m.size, m.size), L.Image.LANCZOS)
    return np.asarray(im.convert("RGBA"), np.float32) / 255.0


def rasterize_view(A: Asset, size=256, ss=2, pitch=56.0, pad=0.03):
    """Orthographic software render of a baked asset along the RTS view direction: albedo x painted
    AO (COLOR_0) x a soft sun term, alpha-tested like the game. Returns (RGBA PIL image, x-range,
    y-range in the image plane, mean depth of the canopy)."""
    A.bake()
    R_, U_, T_ = rts_axes(pitch)
    sun = sun_build()
    allv = np.concatenate([p.v for p in A.parts])
    X, Y = allv @ R_, allv @ U_
    x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
    span = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1, y0, y1 = cx - span / 2, cx + span / 2, cy - span / 2, cy + span / 2
    S = size * ss
    col = np.zeros((S, S, 3), np.float32)
    cov = np.zeros((S, S), np.float32)
    zb = np.full((S, S), -1e9, np.float32)
    texs = {}
    for p in A.parts:
        if id(p.mat) not in texs:
            texs[id(p.mat)] = _mat_rgba(p.mat)
        tex = texs[id(p.mat)]
        th, tw = tex.shape[:2]
        V = p.v[p.t]                                   # (M, 3, 3)
        px = (V @ R_ - x0) / span * S
        py = (y1 - V @ U_) / span * S
        pd = V @ T_
        C = p.col[p.t]                                 # (M, 3, 4)
        shade = C[..., :3]
        lit = 0.62 + 0.48 * np.clip(np.einsum("mkj,j->mk", p.cn, sun), 0, 1)
        for f in range(len(p.t)):
            xs, ys = px[f], py[f]
            bx0, bx1 = int(max(0, math.floor(xs.min()))), int(min(S - 1, math.ceil(xs.max())))
            by0, by1 = int(max(0, math.floor(ys.min()))), int(min(S - 1, math.ceil(ys.max())))
            if bx1 < bx0 or by1 < by0:
                continue
            gy, gx = np.mgrid[by0:by1 + 1, bx0:bx1 + 1] + 0.5
            (ax, ay), (bx_, by_), (cx_, cy_) = zip(xs, ys)
            den = (by_ - cy_) * (ax - cx_) + (cx_ - bx_) * (ay - cy_)
            if abs(den) < 1e-9:
                continue
            w0 = ((by_ - cy_) * (gx - cx_) + (cx_ - bx_) * (gy - cy_)) / den
            w1 = ((cy_ - ay) * (gx - cx_) + (ax - cx_) * (gy - cy_)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not inside.any():
                continue
            d = w0 * pd[f, 0] + w1 * pd[f, 1] + w2 * pd[f, 2]
            sub = zb[by0:by1 + 1, bx0:bx1 + 1]
            ok = inside & (d > sub)
            if not ok.any():
                continue
            uv = p.uv[f]
            u = w0 * uv[0, 0] + w1 * uv[1, 0] + w2 * uv[2, 0]
            v = w0 * uv[0, 1] + w1 * uv[1, 1] + w2 * uv[2, 1]
            ti = (np.floor((u % 1.0) * tw).astype(int)) % tw
            tj = (np.floor((v % 1.0) * th).astype(int)) % th
            texel = tex[tj, ti]
            if p.mat.alpha:
                ok = ok & (texel[..., 3] >= p.mat.cutoff)
                if not ok.any():
                    continue
            sh = w0[..., None] * shade[f, 0] + w1[..., None] * shade[f, 1] + w2[..., None] * shade[f, 2]
            li = w0 * lit[f, 0] + w1 * lit[f, 1] + w2 * lit[f, 2]
            rgb = texel[..., :3] * sh * li[..., None]
            sub[ok] = d[ok]
            cs = col[by0:by1 + 1, bx0:bx1 + 1]
            cs[ok] = rgb[ok]
            cov[by0:by1 + 1, bx0:bx1 + 1][ok] = 1.0
    # downsample (coverage-weighted colour), pad colour into the transparent area
    col = col.reshape(size, ss, size, ss, 3)
    cv = cov.reshape(size, ss, size, ss)
    a = cv.mean(axis=(1, 3))
    rgb = (col * cv[..., None]).sum(axis=(1, 3)) / np.maximum(cv.sum(axis=(1, 3)), 1e-6)[..., None]
    img = L.dilate_rgb(L.to_img(np.concatenate([np.clip(rgb, 0, 1), a[..., None]], axis=2), "RGBA"), 24)
    leaf = [p for p in A.parts if p.mat.sway] or A.parts
    lv = np.concatenate([q.v for q in leaf])
    depth = float(((lv.min(axis=0) + lv.max(axis=0)) / 2) @ T_)
    return img, (x0, x1), (y0, y1), depth


def build_tree_impostor(aid, base_id, spec):
    """LOD2: one camera-facing card (2 tris) carrying the LOD0 tree rendered from the fixed RTS pitch.
    The quad is authored tilted to face the default camera; material extras `billboard: fixed_y` tell
    the game to Y-billboard it (BaseMaterial3D.BILLBOARD_FIXED_Y keeps the authored tilt), so it reads
    right from every yaw. Static (no sway)."""
    ref = build_tree(base_id, spec, lod=0)
    img, (x0, x1), (y0, y1), depth = rasterize_view(ref, size=256)
    seed = seed_of(base_id)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=1.0, base_h=0.01, top_light=0.0, ground_ao=False)
    mat = Mat("impostor", lambda: img, size=256, alpha=True, cutoff=0.5, double=True, uv_kind="atlas",
              extras={"billboard": "fixed_y", "impostor_pitch_deg": 56.0,
                      "note": "LOD2 impostor of " + base_id + ": set billboard_mode = BILLBOARD_FIXED_Y"})
    R_, U_, T_ = rts_axes()
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    v = np.array([R_ * X + U_ * Y + T_ * depth for X, Y in corners])
    if v[:, 2].min() < 0.02:
        v[:, 2] += 0.02 - v[:, 2].min()
    t = np.array([(0, 1, 2), (0, 2, 3)])
    uvc = np.array([((X - x0) / (x1 - x0), (y1 - Y) / (y1 - y0)) for X, Y in corners])
    p = Part(v, t, mat, uvc[t], 180.0)
    p.nmode = "fixed"
    p.nfixed = nrm(T_ * 0.55 + np.array([0, 0, 1.0]) * 0.85)
    p.ao = False
    p.ao_fn = lambda q: np.ones(len(q.v))
    p.occ = 0.0
    A.add(p)
    A.extras = {"kind": "tree", "lod": 2}
    return A


# Crown widths are sized for the 1 m tree grid (architecture.md §7; the map generator fills every free tree
# cell): about 3-3.6 m across (2-3x the 1 m cell, ~1.6-2x in the reference RTS), so a 2 m lane cut through a
# tree wall still shows ground between the crowns, while the crowns still overlap their neighbours (bible
# §6.4 tree-wall rule) and keep their tops >= 4.5 m.

def spec_oak(seed):
    """Hill oak: broad round crown of 4 ring clumps + a top clump and two fillers, ~3.6 m across, top ~6.2 m."""
    rng = np.random.default_rng(seed)
    cl = [((0.05, -0.03, 5.38), 1.05)]
    n = 4
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
        rr = rng.uniform(0.7, 0.8)
        z = rng.uniform(4.1, 4.32)
        R = rng.uniform(0.92, 1.0)
        cl.append(((math.cos(a) * rr, math.sin(a) * rr, z), R))
    for k in (0.5, 2.5):          # fillers between ring clumps, a little lower: rounder belly
        a = a0 + k * 2 * math.pi / n
        cl.append(((math.cos(a) * 0.55, math.sin(a) * 0.55, 3.35), 0.85))
    return TreeSpec(bark=M_bark, leaves=lambda: M_leaves("oak"), clusters=cl, trunk_h=2.6, r_base=0.33,
                    r_top=0.23, flare=0.55, roots=5, lean=(0.06, -0.04), cards=12, card_scale=1.15,
                    cells=(0, 1, 2, 3), squash=0.88)


def spec_linden(seed):
    """Linden: a taller rounded cone (bible §6.4), ~3.1 m across, top ~6.5 m; clusters overlapping heavily
    on a tapering cone hull so it reads as one crown, not stacked pom-poms."""
    rng = np.random.default_rng(seed)
    cl = []
    a0 = rng.uniform(0, 6.28)
    for k in range(5):
        a = a0 + k * 2 * math.pi / 5 + rng.uniform(-0.15, 0.15)
        cl.append(((math.cos(a) * 0.72, math.sin(a) * 0.72, 3.35 + rng.uniform(-0.1, 0.1)), 0.95))
    for k in range(4):
        a = a0 + 0.6 + k * math.pi / 2 + rng.uniform(-0.15, 0.15)
        cl.append(((math.cos(a) * 0.5, math.sin(a) * 0.5, 4.35 + rng.uniform(-0.08, 0.08)), 0.85))
    for k in range(3):
        a = a0 + 1.1 + k * 2 * math.pi / 3
        cl.append(((math.cos(a) * 0.28, math.sin(a) * 0.28, 5.25 + rng.uniform(-0.06, 0.06)), 0.72))
    cl.append(((0.03, 0.0, 5.95), 0.55))
    cone = [(0.62, 2.7), (0.72, 3.25), (0.6, 4.1), (0.42, 5.0), (0.22, 5.7), (0.0, 6.1)]   # inside the clusters
    return TreeSpec(bark=M_bark, leaves=lambda: M_leaves("linden"), clusters=cl, trunk_h=2.6, r_base=0.28,
                    r_top=0.19, flare=0.5, roots=5, lean=(-0.04, 0.03), cards=9, card_scale=1.22,
                    cells=(0, 1, 2, 3), squash=0.95, cone=cone, cluster_hull=False, branch_n=9)


def spec_hazel(seed):
    """Hazel: a 'tall coppice' (bible §1.3 / §6.4): many stems 3.4-3.9 m out of a stool, a crown of clumps
    at 3.6-4.1 m whose top reaches ~4.7 m, ~2.9 m across (tree-wall rule: crown top >= 4.5 m)."""
    rng = np.random.default_rng(seed)
    stems = []
    n = 7
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
        rb = 0.11
        rt = rng.uniform(0.5, 0.75)
        h = rng.uniform(3.4, 3.85)
        stems.append(((math.cos(a) * rb, math.sin(a) * rb, 0.2), (math.cos(a) * rt, math.sin(a) * rt, h),
                      rng.uniform(0.06, 0.08)))
    cl = [((0.0, 0.0, 3.95), 0.9)]
    for k in range(5):
        a = a0 + 0.3 + k * 2 * math.pi / 5 + rng.uniform(-0.2, 0.2)
        cl.append(((math.cos(a) * 0.68, math.sin(a) * 0.68, rng.uniform(3.55, 3.8)), rng.uniform(0.78, 0.85)))
    for k in range(3):             # lower leafy shoots along the stems (coppice reads leafy to mid height)
        a = a0 + 1.0 + k * 2 * math.pi / 3
        cl.append(((math.cos(a) * 0.55, math.sin(a) * 0.55, 2.7), 0.66))
    return TreeSpec(bark=M_bark_hazel, leaves=lambda: M_leaves("hazel"), clusters=cl, stems=stems, r_base=0.27,
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


def tex_drystone(seed=23):
    """neutral_drystone swatch with its saturated yellow lichen speckle (HSV p95 0.86) painted out
    (in-filled from the surrounding stone) and replaced by a few large soft lichen patches;
    saturation capped at 0.5 (bible §1.4 rocks; 'bigger shapes, fewer dots')."""
    def fn():
        im = L.swatch(SW + "neutral_drystone.png", seamless=True)()
        a = np.asarray(im, np.float32) / 255.0
        mx, mn = a.max(axis=2), a.min(axis=2)
        s = (mx - mn) / np.maximum(mx, 1e-4)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        # yellow lichen: red and green both well above blue, red close to green
        yellow = (s > 0.42) & (r > b + 0.18) & (g > b + 0.15) & (np.abs(r - g) < 0.2) & (mx > 0.38)
        lich = np.asarray(L.Image.fromarray((yellow * 255).astype(np.uint8)).filter(L.ImageFilter.MaxFilter(5)),
                          np.float32) / 255.0 > 0.5
        rgba = np.concatenate([a, (~lich)[..., None].astype(np.float32)], axis=2)
        filled = np.asarray(L.dilate_rgb(L.to_img(rgba, "RGBA"), 40), np.float32)[..., :3] / 255.0
        soft = np.asarray(L.to_img(filled).filter(L.ImageFilter.GaussianBlur(2.0)), np.float32) / 255.0
        a = np.where(lich[..., None], soft, a)
        n = a.shape[0]
        # few, large, soft lichen patches on the stone faces (not in the dark joints)
        pn = L.periodic_noise(n, seed, 3.2)
        patch = smoothstep(0.72, 0.84, pn) * smoothstep(0.32, 0.45, a.max(axis=2))
        speck = L.periodic_noise(n, seed + 1, 1.6)
        lc = hexcol("#ADA878") * (0.9 + 0.2 * speck)[..., None]
        a = a * (1 - 0.6 * patch[..., None]) + lc * 0.6 * patch[..., None]
        a = L.hsv_limit(np.clip(a, 0, 1), 1.0, 0.5)
        return L.to_img(a)
    return lambda: L.cached_image(("drystone_v2", seed), fn)


def M_rock(key="rock", seed=3, **kw):
    return Mat(key, tex_rock(seed, 512, **kw), repeat=2.4, size=256)


def M_drystone():
    return Mat("drystone", tex_drystone(), repeat=2.0, size=256)


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


def wall_core(mat, p0, p1, seed, heights=None, nx=10, sag=0.045, top_jit=0.03, bulge=0.05, uv_off=None):
    """Battered drystone core swept from p0 to p1 (ground points); heights: per-station scale.
    The top line sags a little and wanders by a few cm (ends kept at full height so modules join),
    the faces bulge in and out along the run: never a CAD box."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    path = np.stack([np.linspace(p0[i], p1[i], nx + 1) for i in range(3)], axis=1)
    prof = wall_profile()
    t = np.linspace(0, 1, nx + 1)
    ends = np.sin(np.pi * t)
    rng = np.random.default_rng(seed + 17)
    sc = np.ones((nx + 1, 2))
    sc[:, 1] = 1.0 - (sag * ends + np.clip(rng.normal(0, top_jit, nx + 1), -0.05, 0.05) * ends) / WALL_H
    sc[:, 0] = 1.0 + bulge * ends * np.clip(rng.normal(0, 1.0, nx + 1), -1.2, 1.2) * 0.8
    if heights is not None:
        sc[:, 1] *= heights
    parts = L.sweep(prof, path, mat, scales=sc, up=(0, 0, 1), cap0=True, cap1=True)
    p = parts[0]
    p.jitter((0.035, 0.035, 0.025), seed, freq=2.2)
    p.jitter((0.012, 0.012, 0.012), seed + 1)
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    along_y = abs(p1[1] - p0[1]) > abs(p1[0] - p0[0])
    off = uv_off if uv_off is not None else (seed % 7 * 0.13, (seed % 11) * 0.09)
    # the top follows the wall direction (courses run along the wall on every arm)
    p.uv = L.uv_box(p.v, p.t, mat.repeat, off, rot90_top=along_y)
    p.smooth = 30.0
    p.top_line = (np.linalg.norm(path - p0, axis=1) / max(np.linalg.norm(p1 - p0), 1e-6), sc[:, 1] * WALL_H)
    return p


def coping(mat, p0, p1, seed, h=WALL_H, w=WALL_W1, keep=None, top=None):
    """Vertical 'cock and hen' coping stones along the wall top; `top` = (fractions, heights) of the
    core's top line so the coping follows its sag."""
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
        hh = h if top is None else float(np.interp((s + t / 2) / L_, top[0], top[1]))
        hloc = hh - 0.04 if keep is None else hh
        b.move(z=hloc)
        b.rot(rz=ang)
        b.move(*(p0 + d * (s + t / 2)))
        b.jitter(0.012, seed + i)
        b.uv = L.uv_box(b.v, b.t, mat.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)), rot90_top=abs(d[1]) > abs(d[0]))
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
    core = wall_core(m, p0, p1, seed)
    A.add(moss_tint(core, 0.7, seed, up=0.55))
    for c in coping(m, p0, p1, seed + 1, top=core.top_line):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    A.add(through_stones(m, p0, p1, seed + 2))
    return A


def build_wall_corner(aid):
    """Joins a straight on the west (-X) and one on the north (Godot -Z)."""
    A, seed = wall_asset(aid)
    m = M_drystone()
    off = (0.31, 0.17)                                       # one projection offset for both arms: no seam
    c1 = wall_core(m, (-1.0, 0, 0), (WALL_W0 / 2, 0, 0), seed, nx=7, uv_off=off)
    c2 = wall_core(m, (0, WALL_W0 / 2 - 0.02, 0), (0, 1.0, 0), seed + 5, nx=4, uv_off=off)
    A.add(moss_tint(c1, 0.7, seed, up=0.55))
    A.add(moss_tint(c2, 0.7, seed + 5, up=0.55))
    for c in coping(m, (-1.0, 0, 0), (WALL_W1 / 2, 0, 0), seed + 1, top=c1.top_line):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    for c in coping(m, (0, WALL_W1 / 2 + 0.02, 0), (0, 1.0, 0), seed + 3, top=c2.top_line):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    A.add(through_stones(m, (-1.0, 0, 0), (0, 0, 0), seed + 2, n=2))
    return A


def build_wall_broken(aid):
    """Broken end: full height at -X, crumbling to knee height toward +X, loose slabs lying on the
    broken top and tumbled stones at the foot."""
    A, seed = wall_asset(aid)
    rng = np.random.default_rng(seed)
    m = M_drystone()
    nx = 14
    xs = np.linspace(-1, 1, nx + 1)
    hs = np.where(xs < -0.1, 1.0, np.clip(1.0 - (xs + 0.1) * 0.62 + rng.uniform(-0.06, 0.06, nx + 1), 0.28, 1.0))
    core = wall_core(m, (-1.0, 0, 0), (1.0, 0, 0), seed, heights=hs, nx=nx)
    # the broken slope: project its upward faces from the top (Z) and the rest from the side (Y), so the
    # stones are never smeared along the slope
    fnz = nrm(L.face_normals(core.v, core.t))
    uvz = L.uv_box(core.v, core.t, m.repeat, (0.31, 0.17))
    up = (fnz[:, 2] > 0.45) & (core.v[core.t][..., 0].mean(axis=1) > -0.15)
    pz = core.v[core.t[up]]
    uvz[up] = np.stack([pz[..., 0], -pz[..., 1]], axis=-1) / m.repeat + np.array([0.31, 0.17])
    core.uv = uvz
    A.add(moss_tint(core, 0.55, seed, up=0.55, patch=0.15))
    for c in coping(m, (-1.0, 0, 0), (1.0, 0, 0), seed + 1, keep=lambda t: t < 0.42, top=core.top_line):
        A.add(moss_tint(c, 0.5, seed, up=0.6))
    # loose slabs resting on the broken top (follow the slope)
    for k, x in enumerate((0.02, 0.32, 0.6)):
        h = float(np.interp(x, xs, hs)) * WALL_H
        b = L.box((rng.uniform(0.24, 0.34), rng.uniform(0.3, 0.42), rng.uniform(0.07, 0.1)), m)
        b.rot(ry=math.degrees(math.atan(0.62)) * rng.uniform(0.6, 1.0), rz=rng.uniform(-20, 20), rx=rng.uniform(-6, 6))
        b.move(x, rng.uniform(-0.08, 0.08), h - 0.02)
        b.jitter(0.012, seed + 30 + k)
        b.uv = L.uv_box(b.v, b.t, m.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(moss_tint(b, 0.5, seed + k, up=0.6))
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
    """Hawthorn hedgerow, 2 m module along X: one continuous dense leafy ridge from ~0.1 m to ~1.35 m,
    wider than tall at the base (no stilts, no flat core plate), white blossom clusters that read at
    RTS distance. Blocks pathing, not sight. Ends are identical so modules join without a gap."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, base_dark=0.55, base_h=0.4, top_light=0.2)
    leaves = M_leaves("hawthorn")
    H = 1.35
    # leafy ridge hull (interior volume, kept in shade; the cards carry the detail)
    prof = np.array([(0.6, 0.03), (0.66, 0.3), (0.6, 0.68), (0.45, 1.02), (0.22, 1.22), (-0.22, 1.22),
                     (-0.45, 1.02), (-0.6, 0.68), (-0.66, 0.3), (-0.6, 0.03)])
    nx = 14
    xs = np.linspace(-1.06, 1.06, nx + 1)
    ends = np.sin(np.pi * (xs - xs[0]) / (xs[-1] - xs[0]))
    # 4 bumps on the top line (zero at the module ends, so modules still join)
    bumps = [(-0.62, 0.17, 0.2), (-0.1, -0.09, 0.18), (0.3, 0.15, 0.17), (0.72, 0.1, 0.16)]

    def bump(x):
        x = np.asarray(x, float)
        e = np.sin(np.pi * np.clip((x + 1.06) / 2.12, 0, 1))
        return e * sum(a * np.exp(-((x - c) / w) ** 2) for c, a, w in bumps)
    path = np.stack([xs, 0.04 * ends * np.sin(xs * 2.7 + seed % 5), np.zeros(nx + 1)], axis=1)
    sc = np.stack([1 + 0.06 * ends * np.sin(xs * 3.1 + 1.0), 1 + 0.07 * ends * np.sin(xs * 2.3 + 2.0) + bump(xs)], axis=1)
    # the hull tapers into the leafy end fans (its caps stay hidden; neighbouring modules overlap there)
    sc *= (0.62 + 0.38 * smoothstep(0.0, 0.3, 1.06 - np.abs(xs)))[:, None]
    ridge = L.sweep(prof * np.array([0.9, 0.92]), path, leaves, scales=sc, up=(0, 0, 1), cap0=True, cap1=True)[0]
    d = nrm(ridge.v - np.c_[ridge.v[:, 0], np.zeros(len(ridge.v)), np.full(len(ridge.v), 0.45)])
    cc = cell_centre(1)
    ridge.uv = (cc + np.stack([d[:, 1] * 0.03 + ridge.v[:, 0] * 0.01, -d[:, 2] * 0.03], axis=1))[ridge.t]
    ridge.nmode = "sphere"
    ridge.ncenter = np.array([0.0, 0.0, 0.2])
    ridge.nblend = 0.8
    ridge.occ = 0.5
    ridge.ao = False
    ridge.ao_fn = lambda q: 0.32 + 0.16 * np.clip(q.v[:, 2] / H, 0, 1)
    A.add(ridge)
    # leaf cards on the ridge surface (an ellipse in y-z round the ridge axis), facing outward; the
    # lowest rows reach ~0.1 m above the ground
    Ry, Rz, zc = 0.62, 0.86, 0.36
    k = 0
    for ang in (-118, -100, -70, -38, -8, 22, 52, 82, 108):
        n_along = 5
        for j in range(n_along):
            x = -1.0 + (j + 0.5 + rng.uniform(-0.25, 0.25)) * 2.0 / n_along
            a = math.radians(ang + rng.uniform(-8, 8))
            y, zz = math.sin(a) * Ry, zc + math.cos(a) * Rz * (1 + float(bump(x)))
            n = nrm(np.array([rng.uniform(-0.2, 0.2), math.sin(a) / Ry, math.cos(a) / Rz + 0.2]))
            pos = np.array([x, y, max(zz, 0.22)]) + n * 0.06
            s = rng.uniform(0.6, 0.72)
            p = L.card(s, s * 0.92, leaves, cell_rect(int(rng.integers(4))), segs=(2, 2), bend=0.26)
            p.xf(m=orient(n, (0, 0, 1), rng.uniform(-30, 30)), t=pos)
            p.nmode = "sphere"
            p.ncenter = np.array([x, 0.0, 0.2])
            p.nblend = 0.9
            p.ao_fn = lambda q: 0.55 + 0.45 * smoothstep(0.05, 1.2, q.v[:, 2])
            p.phase = (k * 0.37) % 1.0
            A.add(p)
            k += 1
    # sprigs: a few small upright cards breaking the top line
    for k2, x in enumerate((-0.85, -0.35, 0.12, 0.55, 0.9)):
        ztop = zc + Rz * (1 + float(bump(x))) - 0.05
        p = L.card(0.34, 0.5, leaves, cell_rect(int(rng.integers(4))), segs=(1, 2), bend=0.15, pivot="bottom")
        p.rot(rx=rng.uniform(-15, 15)).rot(rz=rng.uniform(0, 180)).move(x, rng.uniform(-0.12, 0.12), ztop)
        p.nmode = "sphere"
        p.ncenter = np.array([x, 0.0, 0.2])
        p.nblend = 0.9
        p.ao_fn = lambda q: 0.6 + 0.4 * smoothstep(0.05, 1.5, q.v[:, 2])
        p.phase = (k2 * 0.53) % 1.0
        A.add(p)
    # leafy ends: a fan of clump cards over each ridge cap so a hedge end (or a gap) never shows the hull
    for sx in (-1, 1):
        for zz, yy in ((0.22, -0.4), (0.22, 0.4), (0.62, -0.32), (0.62, 0.32), (1.0, 0.0), (0.42, 0.0)):
            n = nrm(np.array([sx, yy * 0.9, 0.2]))
            p = L.card(0.62, 0.58, leaves, cell_rect(int(rng.integers(4))), segs=(2, 2), bend=0.26)
            p.xf(m=orient(n, (0, 0, 1), rng.uniform(-30, 30)), t=(sx * 1.1, yy * 0.9, zz))
            p.nmode = "sphere"
            p.ncenter = np.array([sx * 0.7, 0.0, 0.2])
            p.nblend = 0.9
            p.ao_fn = lambda q: 0.55 + 0.45 * smoothstep(0.05, 1.2, q.v[:, 2])
            p.phase = (k * 0.37) % 1.0
            A.add(p)
            k += 1
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
        p.uv = L.uv_box(p.v, p.t, straw.repeat, (k * 0.23, k * 0.41))      # box: strands stay vertical, no stretch
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
        stem.uv[..., 0] = 0.1 + 0.3 * stem.uv[..., 0] / max(float(stem.uv[..., 0].max()), 1e-6)
        stem.uv[..., 1] = 0.36 + 0.28 * np.clip(stem.v[stem.t][..., 2] / max(h, 1e-3), 0, 1)
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
    """neutral_mine_timber cropped between its battens (only planks: grain runs along image u), made
    seamless and tiled twice; UVs put u along each member (uv_along / beam), so posts never show
    planks running across them."""
    return Mat("timber", L.swatch(SW + "neutral_mine_timber.png", seamless=True, sat=0.9, crop=(0.27, 0.0, 0.73, 1.0),
                                  tile=2, s_cap=0.5), repeat=1.6, size=256)


def M_timber_light():
    return Mat("timber", L.swatch(SW + "neutral_mine_timber.png", seamless=True, sat=0.9, tint=(1.12, 1.04, 0.92),
                                  gamma=0.82, crop=(0.27, 0.0, 0.73, 1.0), tile=2, s_cap=0.5), repeat=1.6, size=256)


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


def tex_milestone_mark(seed=9, n=256):
    """The milestone's face: weathered stone with a carved, white-painted arrow pointing up the road and a
    tally of five notches below it (no numerals: reads as 'this way, five leagues'); paint chipped."""
    def fn():
        base = np.asarray(tex_rock(9, 256, base="#8A8478", dark="#5E594F", light="#A8A294", cells=12, lichen_amt=0.6,
                                   moss_amt=0.3)().convert("RGB"), np.float32) / 255.0
        ss = 3
        lay = L.Image.new("L", (n * ss, n * ss), 0)
        d = L.ImageDraw.Draw(lay)
        S = n * ss
        # arrow: shaft and head
        d.rectangle([S * 0.45, S * 0.3, S * 0.55, S * 0.58], fill=255)
        d.polygon([(S * 0.5, S * 0.1), (S * 0.71, S * 0.36), (S * 0.29, S * 0.36)], fill=255)
        for k in range(5):                                         # notch tally
            x = S * (0.26 + 0.12 * k)
            d.rectangle([x, S * 0.68, x + S * 0.045, S * 0.88], fill=255)
        d.line([(S * 0.22, S * 0.8), (S * 0.78, S * 0.74)], fill=255, width=int(S * 0.035))
        m = np.asarray(lay.resize((n, n), L.Image.LANCZOS), np.float32) / 255.0
        groove = np.asarray(lay.filter(L.ImageFilter.MaxFilter(9)).resize((n, n), L.Image.LANCZOS), np.float32) / 255.0
        chip = smoothstep(0.62, 0.72, L.periodic_noise(n, seed, 1.3))
        col = base * (1 - 0.45 * np.clip(groove - m, 0, 1))[..., None]          # carved recess shadow
        paint = hexcol("#E6DCC4") * (0.9 + 0.1 * L.periodic_noise(n, seed + 1, 2.0))[..., None]
        a = (m * (1 - 0.75 * chip))[..., None]
        col = col * (1 - a) + paint * a
        return L.to_img(col)
    return lambda: L.cached_image(("milestone_mark", seed, n), fn)


def build_milestone(aid):
    """Roadside milestone: a squat slab with an arched (round) top, leaning a little, its road face carved with a
    white-painted arrow and a five-notch tally; moss on the crown, a grass skirt at the foot."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.4, base_dark=0.5, base_h=0.25, top_light=0.12)
    cells = [L.Cell("stone", tex_rock(9, 512, base="#8A8478", dark="#5E594F", light="#A8A294", cells=18, lichen_amt=1.4,
                                      moss_amt=0.6), "tile", (224, 224), (1.75, 1.75)),
             L.Cell("mark", tex_milestone_mark(), "decal", (200, 200), (0.4, 0.4))]
    at = L.Atlas("milestone", cells, 512)
    mat = at.mat("stone", extras={"cells_px_per_m": at.density_report()})
    w, d, h0 = 0.44, 0.3, 0.46
    pts = [(-w / 2, -0.08), (w / 2, -0.08), (w / 2, h0)]
    for k in range(1, 8):
        a = k * math.pi / 8
        pts.append((math.cos(a) * w / 2, h0 + math.sin(a) * w / 2 * 0.85))
    pts.append((-w / 2, h0))
    sl = L.slab(np.array(pts), -d / 2, d / 2, mat, chamfer=0.03, top_chamfer_only=False)
    v = sl.v.copy()
    sl.v = np.stack([v[:, 0], v[:, 2], v[:, 1]], axis=1)        # outline (x, z), extruded along y
    sl.t = sl.t[:, ::-1]
    sl.jitter(0.012, seed, freq=4.0)
    P, n = _face_axes(sl)
    front = n[:, 1] > 0.8
    uv = L.uv_box(sl.v, sl.t, 1.75, (0.2, 0.3))
    # the road face carries the carved mark (decal mapped over the whole face)
    uv[front, :, 0] = 0.5 + P[front][..., 0] / (w * 1.05)
    uv[front, :, 1] = 0.5 - (P[front][..., 2] - 0.36) / (w * 1.15)
    sl.uv = uv
    sl.cell = np.where(front, "mark", "stone").astype(object)
    sl.rot(rx=rng.uniform(4, 7), ry=rng.uniform(-5, 5))         # leaning, as old milestones do
    A.add(moss_tint(sl, 0.85, seed, up=0.45, patch=-0.15))
    for k in range(4):
        b = L.blob(mat, 0.09, scale=(1, 0.8, 0.6), seed=seed + k, sphere="uv", segs=(6, 4), flat_top=0.8,
                   flat_bottom=0.1, smooth=40)
        a = rng.uniform(0, 6.28)
        b.move(math.cos(a) * 0.3, math.sin(a) * 0.24, -0.02)
        b.uv = L.uv_box(b.v, b.t, 1.75, (rng.uniform(0, 1), 0.0))
        b.cell = "stone"
        A.add(moss_tint(b, 0.8, seed + k))
    # grass skirt round the foot (SWAY cards)
    meadow = M_meadow()
    for k in range(5):
        a = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
        c = L.card(0.42, 0.3, meadow, cell_rect(3), segs=(1, 1), pivot="bottom")
        c.rot(rx=rng.uniform(-10, 10)).rot(rz=math.degrees(a) + 90)
        c.move(math.cos(a) * 0.24, math.sin(a) * 0.2, -0.02)
        c.nmode = "up"
        c.ao = False
        c.ao_fn = lambda q_: 0.6 + 0.4 * np.clip(q_.v[:, 2] / 0.3, 0, 1)
        c.sway = np.clip(c.v[:, 2] / 0.3, 0, 1)
        c.phase = rng.uniform(0, 1)
        A.add(c)
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
    return Mat("ember", L.tex_glow("ember", 128), repeat=0.6, size=128, emissive=True, tag="EMBER", uv_kind="atlas",
               emissive_factor=(0.5, 0.5, 0.5),
               extras={"emission": "live coals: a dim 0.5 by day; raise emission_energy to ~1.5 at night"})


def M_oilcloth():
    return Mat("oilcloth", L.tex_cloth(61, 512, base="#A07A3A", patches=4, patch_cols=("#8E4A3A", "#5E6B3E", "#6E5636"),
                                       weave=0.05, dirt=0.35), repeat=1.6, size=256)


def M_canvas():
    """Sootcoat canvas: undyed cloth pulled toward the oilcloth value, patched in ochre and faded moss (bible §2.3
    Sootcoats: soot, oilcloth ochre #A07A3A, moss #5E6B3E) - no blue."""
    return Mat("canvas", L.tex_cloth(62, 512, base="#A48E68", patches=3, patch_cols=("#A07A3A", "#5E6B3E", "#8E6E3E"),
                                     weave=0.07, dirt=0.38), repeat=1.6, size=256)


def M_sacking():
    return Mat("sacking", L.tex_cloth(63, 256, base="#9C8763", weave=0.14, dirt=0.3), repeat=0.8, size=128)


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
    """Sootcoat lean-to: two forked posts and a ridge pole, rafters down to the ground, a patched oilcloth roof
    pitched at ~60 deg whose low edge lies on the ground weighted with stones and a log; brushwood-and-oilcloth
    ends. The open side faces the front (-Z): place it sideways in camps (yaw +-90, open side to +-X) so the
    56 deg camera sees the steep roof as a slope, not a flat sheet on legs. A bedroll and a stump seat."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.9, base_dark=0.55, base_h=0.3, top_light=0.12)
    bark, cloth, rock = M_bark(), M_oilcloth(), M_rock(seed=6)
    hx, ry, rz = 1.2, 0.55, 1.75
    yb = ry - rz / math.tan(math.radians(60.0))          # where the roof meets the ground (back)
    for x in (-hx, hx):
        A.add(pole(bark, (x, ry, 0.0), (x + 0.02, ry, rz + 0.12), 0.06, 0.05, seed=int(x * 10)))
        A.add(pole(bark, (x, ry, rz - 0.05), (x + 0.18 * np.sign(x), ry + 0.05, rz + 0.25), 0.035, 0.03, sides=4))
    A.add(pole(bark, (-hx - 0.25, ry, rz + 0.02), (hx + 0.25, ry, rz + 0.04), 0.05, 0.045))
    for k, x in enumerate(np.linspace(-hx + 0.1, hx - 0.1, 5)):
        A.add(pole(bark, (x, ry + 0.06, rz + 0.08), (x + rng.uniform(-0.05, 0.05), yb - 0.05, 0.0), 0.035, 0.03,
                   sides=4, seed=k))
    for p in sheet(cloth, [(-hx - 0.1, ry + 0.1, rz + 0.12), (hx + 0.1, ry + 0.1, rz + 0.14),
                           (hx + 0.05, yb - 0.12, 0.0), (-hx - 0.05, yb - 0.12, 0.0)], 6, 5, sag=0.05, seed=seed):
        A.add(p)
    # the low edge lies on the ground: a weight log along it and stones on the cloth
    A.add(pole(bark, (-hx - 0.15, yb - 0.22, 0.07), (hx + 0.15, yb - 0.2, 0.07), 0.08, 0.07, sides=6))
    for k, x in enumerate(np.linspace(-hx + 0.15, hx - 0.15, 4)):
        b = L.blob(rock, rng.uniform(0.12, 0.16), scale=(1.0, 0.8, 0.65), seed=seed + 20 + k, sphere="uv", segs=(7, 4),
                   flat_top=0.8, flat_bottom=0.15, cuts=1, smooth=40)
        b.move(x + rng.uniform(-0.1, 0.1), yb + 0.05, 0.02)
        A.add(moss_tint(b, 0.6, seed + k))
    # closed ends: brushwood-and-oilcloth triangles
    for x in (-hx - 0.05, hx + 0.05):
        tri = np.array([(x, ry + 0.06, rz + 0.05), (x, yb - 0.1, 0.0), (x, ry + 0.05, 0.0)])
        t = np.array([(0, 1, 2)])
        for tt in (t, t[:, ::-1]):
            q = Part(tri.copy(), tt, cloth, L.uv_box(tri, tt, cloth.repeat), 30.0)
            q.tint = np.full((3, 3), 0.7)
            A.add(q)
    # bedroll and a stump seat in front
    br = L.lathe([(0.0, -0.45), (0.14, -0.44), (0.15, 0.0), (0.14, 0.44), (0.0, 0.45)], 7, cloth)[0]
    br.rot(ry=90).rot(rz=8).move(0.1, 0.05, 0.14)
    br.tint = np.full((len(br.v), 3), 0.75)
    A.add(br)
    st = L.lathe([(0.2, 0.0), (0.17, 0.08), (0.16, 0.38), (0.0, 0.4)], 7, bark)[0]
    st.move(0.95, ry + 0.45, 0)
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
            stake = np.array([sgn * 1.25, y * 1.45, 0.0])
            # guy rope: a 3 cm round line (two crossed strips would shimmer), and a stake
            for lp in pole(bark, (0, y, h + 0.08), stake + (0, 0, 0.12), 0.015, 0.015, sides=4):
                lp.tint = np.full((len(lp.v), 3), 1.25)
                A.add(lp)
            for lp in pole(bark, stake - (0, 0, 0.05), stake + (sgn * 0.05, 0, 0.2), 0.03, 0.025, sides=4):
                A.add(lp)
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


def sack_part(mat, h=0.55, r=0.24, seed=0, rep=0.8, lean=8.0):
    """A filled grain sack: slumped bulging belly, a gathered neck tied with a dark cord, a short tuft of
    cloth above the tie, leaning a little; darker sacking so it never reads as a pale egg."""
    rng = np.random.default_rng(seed)
    prof = [(0.0, 0.0), (r * 0.82, 0.0), (r * 1.06, h * 0.16), (r * 1.02, h * 0.42), (r * 0.78, h * 0.64),
            (r * 0.36, h * 0.78), (r * 0.2, h * 0.82), (r * 0.21, h * 0.86), (r * 0.36, h * 0.93), (r * 0.3, h * 0.99),
            (0.0, h * 0.97)]
    p = L.lathe(prof, 9, mat, a0=rng.uniform(0, 1))[0]
    p.v[:, 0] *= rng.uniform(1.0, 1.15)                       # slumped: wider than deep
    p.v[:, 1] *= rng.uniform(0.8, 0.92)
    p.jitter((0.025, 0.025, 0.02), seed, freq=5.0)
    p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    z = p.v[:, 2]
    tie = np.exp(-((z - h * 0.83) / (h * 0.035)) ** 2)
    belly = smoothstep(h * 0.75, h * 0.1, z)
    p.tint = np.ones((len(p.v), 3)) * (0.92 - 0.12 * belly)[:, None] * (1 - 0.65 * tie)[:, None]
    p.rot(ry=rng.uniform(-lean, lean), rx=rng.uniform(-lean, lean))
    p.uv = L.uv_box(p.v, p.t, rep, (rng.uniform(0, 1), rng.uniform(0, 1)))
    return p


def build_crates(aid):
    """Camp stores: two iron-strapped crates, a barrel and two sacks."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.6, base_dark=0.55, base_h=0.25, top_light=0.12)
    tim, sack = M_timber(), M_sacking()
    tops = []
    for k, (x, y, s, rz, on) in enumerate([(-0.35, 0.0, 0.62, 12, None), (0.32, 0.15, 0.5, -20, None),
                                           (-0.3, 0.05, 0.42, 40, 0)]):
        b = L.box((s, s * 0.9, s * 0.85), tim, chamfer=0.03, center=(0, 0, s * 0.425))
        z = 0.0 if on is None else tops[on] - 0.005             # stacked crates sit on the one below
        b.rot(rz=rz).move(x, y, z)
        b.uv = L.uv_box(b.v, b.t, tim.repeat, (k * 0.31, k * 0.17))
        tops.append(float(b.v[:, 2].max()))
        # a darker ground-contact band (and a contact band under the stacked crate)
        zz = b.v[:, 2] - z
        b.tint = np.ones((len(b.v), 3)) * (0.62 + 0.38 * smoothstep(0.0, 0.12, zz))[:, None]
        A.add(b)
    prof = [(0.0, 0.0), (0.24, 0.0), (0.28, 0.2), (0.3, 0.4), (0.28, 0.6), (0.24, 0.8), (0.0, 0.8)]
    br = L.lathe(prof, 9, tim)[0]
    z = br.v[:, 2]
    hoop = (np.exp(-((z - 0.12) / 0.03) ** 2) + np.exp(-((z - 0.68) / 0.03) ** 2))
    br.tint = np.ones((len(br.v), 3)) * (1 - 0.6 * np.clip(hoop, 0, 1))[:, None]
    br.move(0.85, -0.35, 0)
    A.add(br)
    for k, (x, y, rz) in enumerate([(0.15, -0.65, 20), (-0.6, -0.6, -35)]):
        sk = sack_part(sack, 0.62, 0.25, seed=seed + k)
        sk.rot(rz=rz).move(x, y, 0)
        A.add(sk)
    return A


def build_scarecrow_pole(aid):
    """Tattiebogle field pole: a crossed-pole frame dressed like a scarecrow - a tied sack-and-straw
    bundle on the cross, a tattered patched coat hanging from the arms, straw tufts at the cuffs and
    the hem. No head and no face (neutrals §10.2); the creeps slump on these by day."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.55, base_h=0.3, top_light=0.12)
    bark, sack, straw, coat = M_bark_hazel(), M_sacking(), tex_straw_m(), M_canvas()
    A.add(pole(bark, (0, 0, -0.05), (0.03, 0.02, 2.25), 0.06, 0.05))
    A.add(pole(bark, (-0.95, 0.02, 1.62), (0.95, 0.0, 1.7), 0.045, 0.04))
    # body bundle: a stuffed sack tied at the cross with a rope band
    body = L.blob(sack, 0.36, scale=(1.0, 0.72, 1.0), seed=seed, sphere="uv", segs=(9, 7), noise_amp=0.12,
                  smooth=60)
    body.move(0.0, -0.02, 0.97)
    A.add(body)
    band = L.lathe([(0.27, 1.52), (0.29, 1.58), (0.27, 1.64)], 7, bark)[0]
    band.v[:, 1] *= 0.75
    band.tint = np.ones((len(band.v), 3)) * np.array([1.2, 1.1, 0.8])
    A.add(band)
    # coat: a ragged sheet over the shoulders, hanging in front and behind, with torn hem
    for side in (1, -1):
        y = 0.2 * side
        for p in sheet(coat, [(-0.62, y, 1.68), (0.62, y, 1.7), (0.5, y * 1.2, 0.72), (-0.55, y * 1.2, 0.78)], 4, 4,
                       sag=-0.03 * side, seed=seed + side, flutter=0.03):
            # ragged hem: pull alternate bottom vertices up
            low = p.v[:, 2] < 0.8
            p.v[low, 2] += np.where(np.arange(low.sum()) % 2 == 0, 0.0, 0.16)
            A.add(p)
    # sleeves along the arms, open cuffs
    for sx in (-1, 1):
        sl = L.lathe([(0.11, 0.0), (0.13, 0.3), (0.12, 0.62)], 7, coat)[0]
        sl.rot(ry=90 * sx).move(0.28 * sx, 0.01, 1.62)
        sl.v[:, 2] -= 0.06 * np.abs(sl.v[:, 0]) * 0.3
        A.add(sl)
        # straw spilling from the cuffs
        for k in range(3):
            tuft = L.lathe([(0.07, 0.0), (0.05, 0.1), (0.0, 0.24)], 5, straw)[0]
            tuft.rot(ry=90 * sx + rng.uniform(-35, 35), rx=rng.uniform(-25, 25)).move(0.88 * sx, 0.01, 1.64)
            A.add(tuft)
    # straw tufts at the hem and the neck
    for k in range(6):
        tuft = L.lathe([(0.06, 0.0), (0.04, 0.1), (0.0, 0.22)], 5, straw)[0]
        a = k * 1.05
        tuft.rot(rx=180 + rng.uniform(-20, 20), ry=rng.uniform(-20, 20)).move(math.cos(a) * 0.3, math.sin(a) * 0.18,
                                                                           0.86 + rng.uniform(-0.04, 0.04))
        A.add(tuft)
    for k in range(4):
        tuft = L.lathe([(0.05, 0.0), (0.035, 0.08), (0.0, 0.2)], 5, straw)[0]
        tuft.rot(rx=rng.uniform(-35, 35), ry=rng.uniform(-35, 35)).move(rng.uniform(-0.08, 0.08), rng.uniform(-0.05, 0.05),
                                                                     1.72)
        A.add(tuft)
    return A


def M_turnip():
    def fn():
        n = 64
        y = (np.arange(n) + 0.5)[:, None] / n
        top, bot = hexcol("#7A3E6A"), hexcol("#EDE6D8")
        col = top + (bot - top) * smoothstep(0.25, 0.6, y)[..., None]
        col = np.repeat(col, n, axis=1) * (0.92 + 0.12 * L.periodic_noise(n, 3, 1.6))[..., None]
        return L.to_img(col)
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
            b.uv[..., 0] = 3.0 * b.uv[..., 0] / max(float(b.uv[..., 0].max()), 1e-6)      # ~same px/m as v
            b.uv[..., 1] = 1.0 - np.clip(b.v[b.t][..., 2] / 0.18, 0.02, 0.98)
            b.move(c[0], c[1], 0.07)
            A.add(b)
    for k in range(3):
        b = L.lathe([(0.0, 0.0), (0.08, 0.04), (0.1, 0.1), (0.07, 0.17), (0.0, 0.2)], 6, tn)[0]
        b.uv[..., 0] = 3.0 * b.uv[..., 0] / max(float(b.uv[..., 0].max()), 1e-6)
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
    p.uv = L.uv_box(p.v, p.t, straw.repeat)
    A.add(p)
    A.add(pole(bark, (0.0, 0.0, 1.5), (0.04, 0.0, 2.55), 0.05, 0.04))
    # straw tufts dropped at the foot
    for t in range(4):
        a = rng.uniform(0, 6.28)
        q = L.lathe([(0.25, 0.0), (0.18, 0.08), (0.0, 0.12)], 6, straw)[0]
        q.move(math.cos(a) * 1.25, math.sin(a) * 1.25, -0.02)
        q.uv = L.uv_box(q.v, q.t, straw.repeat, (t * 0.3, 0.1))
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


def uv_along(v, t, axis, rep, off=(0.0, 0.0)):
    """Timber UVs with the grain (image u) along the member's long `axis` (0 x, 1 y, 2 z) on every
    side face; end faces get a plain box projection. Stops plank texture running across posts."""
    p = v[t]
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    ax = np.argmax(np.abs(n), axis=1)
    uv = L.uv_box(v, t, rep, off)
    side = ax != axis
    other = 3 - axis - ax
    for f in np.nonzero(side)[0]:
        uv[f, :, 0] = p[f, :, axis] / rep + off[0]
        uv[f, :, 1] = -p[f, :, other[f]] / rep + off[1]
    return uv


# =============================================================================================
# Gold Seam (neutrals §5.2): a layered cliff block with a gold seam band on every side
# =============================================================================================

# strata beds (z0, z1) shared by the painted band and the geometry: bed edges line up with the ledges
MINE_BEDS = [(0.0, 0.65), (0.65, 1.30), (1.30, 1.88), (1.88, 2.38), (2.38, 3.05), (3.05, 3.80)]
MINE_SEAM = 3                                   # index of the gold seam bed (0.5 m band)
# outward offset per bed: the face is battered back ~10 deg overall (so the 56 deg camera sees more of it),
# with ledges, one overhang over the seam and the seam itself a little proud (its gold catches the light)
MINE_OFF = [0.40, 0.27, 0.15, 0.10, 0.05, -0.20]
BAND_TOP = 4.0                                  # the band cell covers z 0 .. 4.0 m (v = (4 - z) / 4)
BAND_PX = (992, 576)                            # 144 px/m both ways
BAND_RU = BAND_PX[0] / 144.0                    # metres per u repeat (6.89 m)
GOLD = "#D8B048"
ROCK = ("#857555", "#54493A", "#A39373")       # gold-veined rock base / dark / light (bible §2.3 #8A7A5A)


def _voronoi_xwrap(W, H, pts):
    """F1, F2 and nearest index on a W x H grid, wrapped in x only."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    f1 = np.full((H, W), 1e9, np.float32)
    f2 = np.full((H, W), 1e9, np.float32)
    idx = np.zeros((H, W), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px)
        dx = np.minimum(dx, W - dx)
        dy = (yy - py) * 1.0
        d = np.sqrt(dx * dx * 0.35 + dy * dy)          # squashed: long, low facets (bedding, not bricks)
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        idx = np.where(closer, i, idx)
        f1 = np.where(closer, d, f1)
    return f1, f2, idx


def _xwrap_noise(W, H, seed, beta=2.2):
    """Noise tileable in x (crop of a periodic square field whose width is W)."""
    n = max(W, H)
    f = L.periodic_noise(n, seed, beta)
    f = np.asarray(L.Image.fromarray((f * 255).astype(np.uint8)).resize((W, n), L.Image.BILINEAR), np.float32) / 255.0
    return f[:H]


def tex_mine_band(seed=29):
    """Gold Seam cliff band (u wraps every BAND_RU m, v = (4 - z) / 4, 144 px/m). Natural layered rock in
    the gold-veined palette #8A7A5A: one tone per bed, long low chisel facets, sparse irregular joints,
    lit top lips where the next bed steps back and a cast shadow where it overhangs, moss on some ledges.
    The seam bed (z 1.95-2.30) is a solid band of gold #D8B048 with quartz-white chunks and a dark
    under-line; three thin branching veins climb out of it; gold flecks scatter round it."""
    W, H = BAND_PX
    ppm = 144.0

    def row(z):
        return (BAND_TOP - z) * ppm

    def fn():
        rng = np.random.default_rng(seed)
        b, dk, lt = (hexcol(c) for c in ROCK)
        yy, xx = np.mgrid[0:H, 0:W] + 0.5
        z = BAND_TOP - yy / ppm
        bed = np.full((H, W), -1, np.int32)
        fpos = np.zeros((H, W), np.float32)
        for i, (z0, z1) in enumerate(MINE_BEDS):
            m = (z >= z0) & (z < z1)
            bed[m] = i
            fpos[m] = ((z1 - z) / (z1 - z0))[m]                   # 0 at the bed top -> 1 at its bottom
        bed[z >= MINE_BEDS[-1][1]] = len(MINE_BEDS) - 1
        tone = rng.uniform(-1, 1, len(MINE_BEDS))
        tone[MINE_SEAM - 1] = 0.35
        tone[MINE_SEAM + 1] = -0.25
        tb = tone[np.clip(bed, 0, len(MINE_BEDS) - 1)]
        low = _xwrap_noise(W, H, seed + 1, 2.6)
        mid = _xwrap_noise(W, H, seed + 2, 1.9)
        hi = _xwrap_noise(W, H, seed + 3, 1.1)
        streak = np.mean([np.roll(mid, k * 6, axis=1) for k in range(7)], axis=0)       # smeared along x
        pts = np.stack([rng.uniform(0, W, 70), rng.uniform(0, H, 70)], axis=1)
        f1, f2, idx = _voronoi_xwrap(W, H, pts)
        cellv = rng.uniform(-1, 1, 70)[idx]
        t = np.clip(0.5 + 0.17 * tb + 0.16 * cellv + 0.22 * (streak - 0.5) + 0.25 * (low - 0.5), 0, 1)[..., None]
        col = np.where(t < 0.5, dk + (b - dk) * (t / 0.5), b + (lt - b) * ((t - 0.5) / 0.5))
        # facet edges: lit upper rim, dark crack (only where the noise says so: sparse)
        gy = np.roll(f2 - f1, 2, axis=0) - (f2 - f1)
        rim = np.clip(gy / 3.0, 0, 1) * ((f2 - f1) < 6)
        col = col + (lt - col) * (0.3 * rim)[..., None]
        crack = (1 - smoothstep(0.0, 2.2, f2 - f1)) * smoothstep(0.42, 0.62, mid)
        col = col * (1 - 0.4 * crack)[..., None]
        # sparse irregular vertical joints (2-3 per bed per repeat, slanted, varying depth; never bricks)
        joint = np.zeros((H, W), np.float32)
        for i, (z0, z1) in enumerate(MINE_BEDS):
            if i == MINE_SEAM:
                continue
            r0, r1 = int(max(row(z1), 0)), int(min(row(z0), H))
            for _ in range(int(rng.integers(2, 4))):
                x0 = rng.uniform(0, W)
                sl = rng.uniform(-0.35, 0.35)
                frac = rng.uniform(0.55, 1.0)                     # some joints stop part-way
                ys = np.arange(r0, r1)
                keep = (ys - r0) < (r1 - r0) * frac
                dxx = ((xx[r0:r1] - x0 - sl * (ys[:, None] - r0) + W / 2) % W) - W / 2
                j = smoothstep(2.8, 0.7, np.abs(dxx)) * keep[:, None] * rng.uniform(0.6, 1.0)
                joint[r0:r1] = np.maximum(joint[r0:r1], j)
        col = col * (1 - 0.5 * joint)[..., None]
        # bed boundaries: lit lip where the bed above steps back, shadow where it overhangs, crevice line
        for i, (z0, z1) in enumerate(MINE_BEDS):
            rt = row(z1)
            above = MINE_OFF[i + 1] if i + 1 < len(MINE_OFF) else -1.0
            d = yy - rt                                            # px below the bed top
            if above < MINE_OFF[i]:
                lip = smoothstep(6.0, 0.0, d) * (d >= 0)
                col = col + (lt * 1.12 - col) * (0.55 * lip)[..., None]
            else:
                sh = smoothstep(14.0, 0.0, d) * (d >= 0)
                col = col * (1 - 0.45 * sh)[..., None]
            cre = np.exp(-((yy - row(z0)) / 2.2) ** 2)
            col = col * (1 - 0.55 * cre)[..., None]
        # moss on some ledge tops (not on the seam)
        mz = smoothstep(0.22, 0.0, fpos) * smoothstep(0.55, 0.78, low) * (bed != MINE_SEAM) * (bed != MINE_SEAM - 1)
        col = col * (1 - 0.75 * mz[..., None]) + hexcol("#5B7A43") * (0.85 + 0.3 * hi)[..., None] * 0.75 * mz[..., None]
        col = L.hsv_limit(np.clip(col, 0, 1), 1.0, 0.42)
        # ---- gold: the seam band, quartz chunks, an under-line; veins; flecks
        gold = np.zeros((H, W), np.float32)
        s0, s1 = MINE_BEDS[MINE_SEAM]
        rs1, rs0 = row(s1), row(s0)
        wav = 3.0 * np.sin(xx[0] / W * 2 * math.pi * 3 + 1.0) + 2.0 * np.sin(xx[0] / W * 2 * math.pi * 7 + 0.3)
        inband = (yy > rs1 + 1 + wav[None, :] * 0.3) & (yy < rs0 - 5 + wav[None, :] * 0.5)
        gold = np.maximum(gold, inband.astype(np.float32))
        ss = 2
        lay = L.Image.new("L", (W * ss, H * ss), 0)
        qz = L.Image.new("L", (W * ss, H * ss), 0)
        dg, dq = L.ImageDraw.Draw(lay), L.ImageDraw.Draw(qz)

        def wrap_poly(d, pts, fill=255):
            for ox in (-W, 0, W):
                d.polygon([((x + ox) * ss, y * ss) for x, y in pts], fill=fill)

        def wrap_line(d, pts, width):
            for ox in (-W, 0, W):
                d.line([((x + ox) * ss, y * ss) for x, y in pts], fill=255, width=int(width * ss), joint="curve")
        # quartz chunks inside the band (angular, 10-30 px)
        for _ in range(26):
            cx, cy = rng.uniform(0, W), rng.uniform(rs1 + 6, rs0 - 8)
            r = rng.uniform(5, 14)
            k = int(rng.integers(5, 8))
            a0 = rng.uniform(0, 6.28)
            pts = [(cx + math.cos(a0 + j * 6.283 / k) * r * rng.uniform(0.6, 1.3) * 1.5,
                    cy + math.sin(a0 + j * 6.283 / k) * r * rng.uniform(0.6, 1.2) * 0.8) for j in range(k)]
            wrap_poly(dq, pts)
        # branching veins: three, wandering out of the band (up or down), tapering, each with a fork
        def vein(x, y, up, length, w0, steps, drift):
            pts = [(x, y)]
            for k in range(steps):
                drift = 0.7 * drift + rng.normal(0, 5.0)
                x += drift
                y += (-1 if up else 1) * length / steps * rng.uniform(0.7, 1.3)
                pts.append((x, y))
            for k in range(steps):
                w = w0 * (1 - 0.75 * k / steps)
                if rng.random() < 0.12 and k > 2:
                    continue                                       # a break in the vein
                wrap_line(dg, [pts[k], pts[k + 1]], w)
            return pts
        for vx, up in ((0.17, True), (0.52, False), (0.79, True)):
            pts = vein(vx * W, rs1 + 3 if up else rs0 - 5, up, rng.uniform(90, 130), rng.uniform(5.0, 6.5), 11,
                       rng.uniform(-4, 4))
            k = int(rng.integers(3, 6))
            vein(pts[k][0], pts[k][1], up, rng.uniform(40, 70), 3.6, 6, rng.uniform(-6, 6))
        vein_only = lay.copy()                                    # quartz rims go round the veins, not the flecks
        # gold flecks within ~0.5 m of the band
        for _ in range(240):
            cx = rng.uniform(0, W)
            cy = rng.uniform(rs1 - 0.55 * ppm, rs0 + 0.5 * ppm)
            r = rng.uniform(1.4, 2.8)
            for ox in (-W, 0, W):
                dg.ellipse([((cx + ox) - r) * ss, (cy - r * 0.8) * ss, ((cx + ox) + r) * ss, (cy + r * 0.8) * ss], fill=255)
        vein = np.asarray(lay.resize((W, H), L.Image.LANCZOS), np.float32) / 255.0
        quartz = np.asarray(qz.resize((W, H), L.Image.LANCZOS), np.float32) / 255.0 * gold
        gold = np.clip(np.maximum(gold, vein), 0, 1)
        gnz = 0.82 + 0.3 * hi + 0.12 * (low - 0.5)
        gcol = hexcol(GOLD)[None, None, :] * gnz[..., None]
        # painted highlight on the upper part of the band, shade on its lower part
        fb = np.clip((yy - rs1) / max(rs0 - rs1, 1), 0, 1)
        gcol = gcol * (1.12 - 0.3 * fb)[..., None] * np.where(inband, 1.0, 1.0)[..., None]
        gcol = gcol + (hexcol("#F0D888") - gcol) * (0.35 * smoothstep(0.75, 0.95, hi) * inband)[..., None]
        qcol = hexcol("#EFE6CB") * (0.9 + 0.12 * hi)[..., None]
        col = col * (1 - gold[..., None]) + gcol * gold[..., None]
        col = col * (1 - quartz[..., None]) + qcol * quartz[..., None]
        # dark under-line below the band and a thin dark line on top: makes the band pop at range
        ul = smoothstep(7.0, 1.0, np.abs(yy - (rs0 - 2.5))) * (1 - quartz)
        col = col * (1 - 0.72 * ul[..., None])
        tl = smoothstep(2.5, 0.5, np.abs(yy - (rs1 + 0.5)))
        col = col * (1 - 0.35 * tl[..., None])
        # vein edges: quartz rim (only outside the band)
        vo = vein_only.resize((W, H), L.Image.LANCZOS)
        vedge = np.clip(np.asarray(vo.filter(L.ImageFilter.MaxFilter(3)), np.float32) / 255.0
                        - np.asarray(vo, np.float32) / 255.0, 0, 1) * (~inband) * (1 - vein)
        col = col * (1 - 0.6 * vedge[..., None]) + hexcol("#E6DCC0") * 0.6 * vedge[..., None]
        emit = gold * (1 - 0.6 * quartz)
        return L.to_img(np.clip(col, 0, 1)), L.to_img(np.clip(gcol * emit[..., None], 0, 1))

    def albedo():
        return L.cached_image(("mine_band", seed), fn)[0]

    def emissive():
        return L.cached_image(("mine_band", seed), fn)[1]
    return albedo, emissive


def tex_tailings(seed=33):
    """Spoil-heap gravel: gv_scree cropped to 1.8 m, made seamless, cooled to grey tailings, a few
    #D8B048 gold flecks (no nuggets)."""
    def fn():
        im = L.load_rgb(TEX + "gv_scree.png").convert("RGB")
        Wf = im.width
        im = im.crop((0, 0, int(Wf * 0.45), int(Wf * 0.45)))
        im = L.make_seamless(im).resize((256, 256), L.Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        a = L.hsv_limit(a, 0.45, 0.2) * np.array([1.0, 0.98, 0.95]) * 1.05
        rng = np.random.default_rng(seed)
        lay = L.Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        d = L.ImageDraw.Draw(lay)
        g, hl = tuple(int(v * 255) for v in hexcol(GOLD)), tuple(int(v * 255) for v in hexcol("#F4E0A0"))
        for _ in range(26):
            x, y, r = rng.uniform(0, 512), rng.uniform(0, 512), rng.uniform(2.2, 4.5)
            for ox in (-512, 0, 512):
                for oy in (-512, 0, 512):
                    d.ellipse([x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8], fill=g + (255,))
                    d.ellipse([x + ox - r * 0.4, y + oy - r * 0.5, x + ox + r * 0.2, y + oy], fill=hl + (255,))
        la = np.asarray(lay.resize((256, 256), L.Image.LANCZOS), np.float32) / 255.0
        a = a * (1 - la[..., 3:]) + la[..., :3] * la[..., 3:]
        return L.to_img(a)
    return lambda: L.cached_image(("tailings", seed), fn)


def _swatch_crop(path, frac, px, s_cap=None, sat=None, tint=None, key=""):
    """A `frac` crop of a 4 m terrain swatch made seamless again (keeps its texel density at a smaller repeat)."""
    def fn():
        im = L.load_rgb(path).convert("RGB")
        n = im.width
        im = im.crop((0, 0, int(n * frac), int(n * frac)))
        im = L.make_seamless(im).resize((px, px), L.Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        if sat is not None:
            lum = a.mean(axis=2, keepdims=True)
            a = lum + (a - lum) * sat
        if tint is not None:
            a = a * np.asarray(tint)
        if s_cap is not None:
            a = L.hsv_limit(np.clip(a, 0, 1), 1.0, s_cap)
        return L.to_img(a)
    return lambda: L.cached_image(("swcrop", path, frac, px, s_cap, sat, tuple(tint) if tint else None, key), fn)


def tex_ledge(seed=41, n=256):
    """Rock tops and ledges of the Gold Seam: soft chiselled facets in the gold-veined palette (no dark crack
    network, so it never reads as paving), lichen dots, big soft moss patches. Tileable."""
    def fn():
        rng = np.random.default_rng(seed)
        b, dk, lt = (hexcol(c) for c in ("#76694F", "#504536", "#958566"))
        pts = rng.uniform(0, n, (14, 2))
        f1, f2, idx = _wrap_voronoi(n, pts)
        cellv = rng.uniform(-1, 1, 14)[idx]
        low = L.periodic_noise(n, seed + 1, 2.8)
        mid = L.periodic_noise(n, seed + 2, 1.8)
        hi = L.periodic_noise(n, seed + 3, 1.0)
        t = np.clip(0.5 + 0.14 * cellv + 0.4 * (low - 0.5) + 0.2 * (mid - 0.5), 0, 1)[..., None]
        col = np.where(t < 0.5, dk + (b - dk) * (t / 0.5), b + (lt - b) * ((t - 0.5) / 0.5))
        edge = f2 - f1
        gy = np.roll(edge, 2, axis=0) - edge
        col = col + (lt - col) * (0.25 * np.clip(gy / 3.0, 0, 1) * (edge < 6))[..., None]
        col = col * (1 - 0.18 * (1 - smoothstep(0.0, 2.0, edge)) * smoothstep(0.5, 0.7, mid))[..., None]
        m = smoothstep(0.55, 0.75, low) * 0.85
        mc = hexcol("#5B7A43") * (0.8 + 0.35 * hi)[..., None]
        col = col * (1 - m[..., None]) + mc * m[..., None]
        li = (smoothstep(0.76, 0.82, hi) * smoothstep(0.4, 0.6, mid))[..., None] * 0.7
        col = col * (1 - li) + hexcol("#AAB061") * li
        return L.to_img(L.hsv_limit(np.clip(col, 0, 1), 1.0, 0.45))
    return lambda: L.cached_image(("ledge", seed, n), fn)


def mine_rock_atlas():
    band, band_e = tex_mine_band()
    cells = [
        L.Cell("band", band, "band", BAND_PX, (BAND_RU, BAND_TOP), emissive=band_e),
        L.Cell("turf", _swatch_crop(TEX + "gv_thick_meadow.png", 0.75, 384, s_cap=0.46), "tile", (384, 384), (3.0, 3.0)),
        L.Cell("tailings", tex_tailings(), "tile", (256, 256), (1.8, 1.8)),
        L.Cell("ledge", tex_ledge(), "tile", (224, 224), (1.75, 1.75)),
        L.Cell("dark", L.tex_flat("#1E1A16", 48, 0.08, 3), "decal", (48, 48), (1.0, 1.0)),
    ]
    return L.Atlas("gold_mine_rock", cells, 1024)


def tex_rope(n=128):
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        ph = ((xx + yy * 1.6) / n * 6) % 1.0
        strand = 0.55 + 0.45 * np.sin(ph * math.pi) ** 0.7
        col = hexcol("#B9A27E")[None, None, :] * strand[..., None] * (0.9 + 0.1 * L.periodic_noise(n, 3, 1.5))[..., None]
        return L.to_img(col)
    return lambda: L.cached_image(("rope", n), fn)


def tex_riffle(seed=37):
    """Sluice floor: wet planks with dark cross riffles and gold flecks caught behind them."""
    def fn():
        base = np.asarray(M_timber().image().convert("RGB").resize((128, 128), L.Image.LANCZOS), np.float32) / 255.0
        base = base * 0.72
        yy, xx = np.mgrid[0:128, 0:128] + 0.5
        rif = np.exp(-(((xx % 32) - 4) / 2.0) ** 2)
        base = base * (1 - 0.55 * rif[..., None])
        rng = np.random.default_rng(seed)
        lay = L.Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = L.ImageDraw.Draw(lay)
        g = tuple(int(v * 255) for v in hexcol(GOLD)) + (255,)
        for _ in range(30):
            k = int(rng.integers(0, 4))
            x = (k * 32 + 10 + rng.uniform(0, 14)) * 2
            y, r = rng.uniform(0, 256), rng.uniform(2.0, 4.0)
            d.ellipse([x - r, y - r, x + r, y + r], fill=g)
        la = np.asarray(lay.resize((128, 128), L.Image.LANCZOS), np.float32) / 255.0
        base = base * (1 - la[..., 3:]) + la[..., :3] * la[..., 3:]
        return L.to_img(base)
    return lambda: L.cached_image(("riffle", seed), fn)


def tex_water_tile():
    def fn():
        im = L.load_rgb(TEX + "water_ripples.png").convert("RGB").resize((128, 128), L.Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        lum = a.mean(axis=2, keepdims=True)
        col = hexcol("#5AA3A0") * 0.82 * (0.8 + 0.28 * (lum - lum.mean()) / max(lum.std() * 3, 1e-3))
        return L.to_img(L.hsv_limit(np.clip(col, 0, 1), 1.0, 0.45))
    return lambda: L.cached_image(("water_tile",), fn)


def timber_atlas(key, light=False):
    """Timber atlas shared by the Gold Seam and the Weighstall: planks (grain along u), end grain, painted
    water, dark iron, rope, lantern glass (the only emissive texels) and a gold-flecked sluice floor."""
    tim = M_timber_light() if light else M_timber()
    def two_up():
        def fn():
            im = tim.image().convert("RGB").resize((224, 224), L.Image.LANCZOS)
            out = L.Image.new("RGB", (448, 224))
            out.paste(im, (0, 0))
            out.paste(im, (224, 0))
            return out
        return lambda: L.cached_image(("timber2", key, light), fn)
    cells = [
        L.Cell("timber", two_up(), "tile", (448, 224), (2.8, 1.4)),          # 160 px/m, grain along u
        L.Cell("endgrain", L.tex_rings(5, 256), "decal", (100, 100), (0.4, 0.4)),
        L.Cell("water", tex_water_tile(), "tile", (96, 96), (0.75, 0.75)),
        L.Cell("iron", L.tex_flat("#3D4046", 64, 0.12, 5), "tile", (96, 96), (1.5, 1.5)),
        L.Cell("rope", tex_rope(), "decal", (100, 100), (0.3, 0.3)),
        L.Cell("glass", L.tex_glow("lamp", 64), "decal", (52, 52), (0.2, 0.2), emissive=L.tex_glow("lamp", 64)),
        L.Cell("riffle", tex_riffle(), "tile", (96, 96), (0.75, 0.75)),
    ]
    return L.Atlas(key, cells, 512)


def _face_axes(p):
    P = p.v[p.t]
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    n = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    return P, n


def rock_uv(p, top="ledge", side="band", bottom="ledge", rep_top=2.0, off=(0.0, 0.0), up_thr=0.62, rep_side=None):
    """Per-face projection onto the mine rock atlas: side faces -> the band (u along the face, v = height,
    so strata and seam line up all round), up / down faces -> a tile cell in plan (x, y)."""
    P, n = _face_axes(p)
    M = len(p.t)
    uv = np.zeros((M, 3, 2))
    up, dn = n[:, 2] > up_thr, n[:, 2] < -up_thr
    sd = ~(up | dn)
    axx = np.abs(n[:, 0]) >= np.abs(n[:, 1])
    sx = np.where(n[:, 0] >= 0, 1.0, -1.0)
    sy = np.where(n[:, 1] >= 0, 1.0, -1.0)
    um = np.where(axx[:, None], P[..., 1] * sx[:, None], -P[..., 0] * sy[:, None])
    if side == "band":
        uv[sd, :, 0] = um[sd] / BAND_RU + off[0]
        uv[sd, :, 1] = (BAND_TOP - np.clip(P[sd][..., 2], 0, BAND_TOP)) / BAND_TOP
    else:
        rs = rep_side or rep_top
        uv[sd, :, 0] = um[sd] / rs + off[0]
        uv[sd, :, 1] = -P[sd][..., 2] / rs + off[1]
    tb = up | dn
    uv[tb, :, 0] = P[tb][..., 0] / rep_top + off[0]
    uv[tb, :, 1] = -P[tb][..., 1] / rep_top + off[1]
    cells = np.where(sd, side, np.where(up, top, bottom)).astype(object)
    p.uv = uv
    p.cell = cells
    return p


def round_rect(x0, x1, y0, y1, r, step=0.5, front_stops=()):
    """CCW rounded rectangle outline, densified (~step m); front_stops: x values that must be vertices of the
    front (y1) edge (e.g. the adit jambs)."""
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(4):
            a = math.radians(a0 + k * 30)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        if a0 == 0:
            for x in sorted(front_stops, reverse=True):
                if x0 + r + 0.05 < x < x1 - r - 0.05:
                    pts.append((x, y1))
    return densify(pts, step)


def offset_outline(poly, d):
    """Offset a CCW polygon outward by d (per-vertex, mitred, clamped)."""
    K = len(poly)
    out = np.zeros_like(poly)
    for i in range(K):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % K]
        e0 = nrm(p1 - p0)
        e1 = nrm(p2 - p1)
        n0 = np.array([e0[1], -e0[0]])
        n1 = np.array([e1[1], -e1[0]])
        b = nrm(n0 + n1)
        cosh = max(np.dot(b, n0), 0.5)
        out[i] = p1 + b * np.asarray(d)[i % np.size(d)] / cosh if np.ndim(d) else p1 + b * d / cosh
    return out


def ring_wall(rings, mat, cap_in=None, smooth=32.0, inner=None):
    """Side wall through stacked CCW outline rings [(poly (K,2), z), ...] plus a top strip from the last ring
    inward by cap_in metres (or to the given `inner` ring); the rest of the top is hidden under the next bed."""
    K = len(rings[0][0])
    allr = list(rings)
    if inner is not None:
        allr.append((inner, rings[-1][1]))
    elif cap_in:
        allr.append((offset_outline(rings[-1][0], -cap_in), rings[-1][1]))
    verts = np.concatenate([np.c_[poly, np.full(K, z)] for poly, z in allr])
    tris = np.array(L._ring_faces(len(allr), K, True), np.int64)
    # outward / upward winding: the side walls must face away from the outline centre
    P = verts[tris]
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    cen = np.r_[rings[0][0].mean(axis=0), (rings[0][1] + rings[-1][1]) / 2]
    side = np.abs(fn[:, 2]) < np.linalg.norm(fn, axis=1) * 0.7
    if np.sum(np.einsum("ij,ij->i", fn[side], P[side].mean(axis=1) - cen) < 0) > side.sum() / 2:
        tris = tris[:, ::-1]
    return Part(verts, tris, mat, np.zeros((len(tris), 3, 2)), smooth)


def bed_slab(mat, base, z0, z1, off, seed, jit=0.17, lip=0.035, cap_in=0.45, notch=True, portal=None):
    """One stratum of a cliff stack: the base outline pushed out by `off` plus low-frequency noise (the bed
    wanders in and out by ~10 cm), its top and bottom edges wandering independently (faces lean a little),
    an eroded notch or two, a small chamfered lip and a top strip only as deep as can be seen (cap_in).
    Side faces map to the band, the top strip (ledge) to the ledge tile."""
    base = np.asarray(base, float)
    rng = np.random.default_rng(seed)
    q = np.c_[base, np.zeros(len(base))]
    nz = L.noise1(q, 0.85, (seed % 31 * 0.7, 2.0 + z0, 5.0)) + 0.35 * L.noise1(q, 2.4, (3.0, seed % 17 * 0.3, z0))
    nb = L.noise1(q, 1.3, (5.0 + z0, seed % 13 * 0.5, 1.0))
    d = off + nz * jit
    if notch:
        # erosion notches: a stretch of the bed set back 10-20 cm (breaks the regular courses)
        per = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(np.vstack([base, base[:1]]), axis=0), axis=1))]
        tot = per[-1]
        for _ in range(int(rng.integers(2, 4))):            # eroded stretches
            c0, w = rng.uniform(0, tot), rng.uniform(0.7, 1.8)
            dd = np.abs(((per[:-1] - c0 + tot / 2) % tot) - tot / 2)
            d = d - rng.uniform(0.15, 0.3) * smoothstep(w * 0.5, w * 0.2, dd)
        for _ in range(int(rng.integers(1, 3))):            # vertical joints opened into cracks
            c0 = rng.uniform(0, tot)
            dd = np.abs(((per[:-1] - c0 + tot / 2) % tot) - tot / 2)
            d = d - rng.uniform(0.12, 0.2) * (dd < 0.26)
    if portal is not None:
        # a flat portal face round the adit: front-edge vertices with |x| < xh sit at offset d_portal
        xh, yfront, dp = portal
        pm = (np.abs(base[:, 0]) < xh) & (base[:, 1] > yfront - 0.05)
        d = np.where(pm, dp, d)
        nb = np.where(pm, 0.0, nb)
    top = offset_outline(base, d)
    bot = offset_outline(base, d - 0.02 + nb * 0.07)
    rings = [(bot, z0), (top, z1)]
    # the top strip never insets past the middle of a narrow stack (an inverted strip shows as big flat triangles)
    mw = float(min(np.ptp(base[:, 0]), np.ptp(base[:, 1])))
    inner = offset_outline(base, np.maximum(d - cap_in, -0.38 * mw))
    p = ring_wall(rings, mat, inner=inner)
    p.jitter((0.02, 0.02, 0.008), seed + 3, freq=2.4)
    return p


def mine_stack(A, mat, base, top_z, seed, beds=MINE_BEDS, offs=MINE_OFF, adit=None, cap=True, rng=None):
    """A stack of bed slabs up to top_z (+ a turf cap). adit = (x_half, y_front, z_top): remove the
    front faces inside the opening (the interior box closes it)."""
    parts = []
    last = 0
    for i, (z0, z1) in enumerate(beds):
        if z0 >= top_z - 1e-6:
            break
        last = i
        portal = None if adit is None or z0 >= adit[2] - 1e-6 else (1.35, adit[1], MINE_OFF[0])
        p = bed_slab(mat, base, z0, min(z1, top_z), offs[i], seed + 7 * i, notch=adit is None or i > 2, portal=portal)
        if adit is not None and z0 < adit[2] - 1e-6:
            P, n = _face_axes(p)
            c = P.mean(axis=1)
            cut = (n[:, 1] > 0.35) & (np.abs(c[:, 0]) < adit[0]) & (c[:, 1] > adit[1] - 0.3)
            p.t = p.t[~cut]
        rock_uv(p)
        parts.append(p)
    if cap:
        # rock top: a thin capstone layer set just inside the top bed's lit lip, mossy, with turf patches
        q = np.c_[base, np.zeros(len(base))]
        nz = L.noise1(q, 1.4, (seed % 13 * 0.9, 7.0, 1.0))
        d = offs[last] - 0.04 + nz * 0.06
        rings = [(offset_outline(base, d), top_z - 0.02), (offset_outline(base, d - 0.03), top_z + 0.08),
                 (offset_outline(base, d - 0.1), top_z + 0.11)]
        cp = rings_solid(rings, mat)
        cp.jitter((0.03, 0.03, 0.025), seed + 91, freq=2.0)
        rock_uv(cp, top="ledge", side="band", rep_top=1.75, off=((seed % 7) * 0.13, (seed % 5) * 0.21))
        moss_tint(cp, 0.75, seed + 92, col=(0.55, 0.72, 0.38), up=0.6, patch=0.05)
        parts.append(cp)
        rr = rng if rng is not None else np.random.default_rng(seed)
        lo_, hi_ = base.min(axis=0), base.max(axis=0)
        mid_ = (lo_ + hi_) / 2
        x0, y0 = np.minimum(lo_ + 0.55, mid_)
        x1, y1 = np.maximum(hi_ - 0.55, mid_)
        area = max(x1 - x0, 0.1) * max(y1 - y0, 0.1)
        for k in range(int(np.clip(area / 1.2, 1, 5))):
            cx, cy = rr.uniform(x0, x1), rr.uniform(y0, y1)
            r = min(rr.uniform(0.55, 0.95), 0.33 * float(min(np.ptp(base[:, 0]), np.ptp(base[:, 1]))))
            tp = L.blob(mat, r, scale=(1.0, rr.uniform(0.6, 0.9), 0.16), seed=seed + 95 + k, sphere="uv", segs=(10, 4),
                        noise_amp=0.18, flat_bottom=0.3, smooth=60)
            tp.rot(rz=rr.uniform(0, 180)).move(cx, cy, top_z + 0.06)
            rock_uv(tp, top="turf", side="turf", bottom="turf", rep_top=3.0)
            tp.tint = np.ones((len(tp.v), 3)) * (0.78 + 0.16 * smoothstep(top_z + 0.06, top_z + 0.16, tp.v[:, 2]))[:, None]
            parts.append(tp)
    for p in parts:
        A.add(p)
    return parts


def tim_part(p, cell="timber", grain_axis=None, rep=1.4):
    # timber cell: 2.8 m along the grain (u) x 1.4 m (v); UVs below are in 1.4 m units, so halve u
    """Assign a timber-atlas cell; box UVs (grain along `grain_axis` when given) in repeat units."""
    if grain_axis is None:
        p.uv = L.uv_box(p.v, p.t, rep)
    else:
        p.uv = uv_along(p.v, p.t, grain_axis, rep)
    if cell == "timber":
        p.uv = p.uv * np.array([0.5, 1.0])
    p.cell = cell
    return p


def tbeam(mat, p0, p1, w, h=None, seed=0, chamfer=0.035, jitter=0.01, cell="timber"):
    """Chamfered timber along p0 -> p1 on the timber atlas (grain along the member)."""
    h = w if h is None else h
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    up = (0, 0, 1) if abs(nrm(d)[2]) < 0.9 else (1, 0, 0)
    q = L.sweep(L.chamfer_rect(w, h, chamfer), np.stack([p0, (p0 + p1) / 2, p1]), mat, up=up, cap0=True, cap1=True,
                smooth=25.0, repeat=1.4)[0]
    q.uv = np.stack([-q.uv[..., 1], q.uv[..., 0]], axis=-1) + np.array([(seed * 0.37) % 1.0, (seed * 0.61) % 1.0])
    if cell == "timber":
        q.uv = q.uv * np.array([0.5, 1.0])
    q.cell = cell
    if jitter:
        q.jitter(jitter, seed)
    return q


def tlathe(mat, prof, sides, cell="timber", a0=0.0, swap=True, rep=1.4):
    q = L.lathe(prof, sides, mat, a0=a0, repeat=rep)[0]
    if swap:
        q.uv = np.stack([-q.uv[..., 1], q.uv[..., 0]], axis=-1)
    if cell == "timber":
        q.uv = q.uv * np.array([0.5, 1.0])
    q.cell = cell
    return q


def atlas_lantern(mat, hang, cell_frame="iron"):
    """Hanging lantern on a timber atlas: iron cage + emissive glass decal."""
    hang = np.asarray(hang, float)
    sc = 1.5
    body = tlathe(mat, [(0.0, -0.36 * sc), (0.1 * sc, -0.34 * sc), (0.1 * sc, -0.3 * sc), (0.03 * sc, -0.28 * sc),
                        (0.03 * sc, -0.12 * sc), (0.11 * sc, -0.11 * sc), (0.06 * sc, -0.05 * sc), (0.0, 0.0)], 6,
                  cell=cell_frame, rep=1.5)
    glass = L.lathe([(0.0, -0.29 * sc), (0.085 * sc, -0.27 * sc), (0.09 * sc, -0.13 * sc), (0.0, -0.11 * sc)], 6, mat)[0]
    glass.uv = np.clip(L.uv_box(glass.v, glass.t, 0.3) % 1.0, 0.05, 0.95) * 0.5 + 0.25
    glass.cell = "glass"
    for p in (body, glass):
        p.move(*hang)
        p.ao = False
        p.ao_fn = lambda q: np.ones(len(q.v))
    return [glass, body]


def spoked_wheel(mat, R, w=0.12, spokes=8, rim_d=0.14, hub_r=0.16, seed=0):
    """Big windlass wheel in the local XZ plane (axle along Y), centre at the origin."""
    parts = []
    K = 20
    a = np.linspace(0, 2 * math.pi, K + 1)
    path = np.stack([np.cos(a) * R, np.zeros(K + 1), np.sin(a) * R], axis=1)
    rim = L.sweep(np.array([(rim_d / 2, -w / 2), (rim_d / 2, w / 2), (-rim_d / 2, w / 2), (-rim_d / 2, -w / 2)]),
                  path, mat, up=(0, 1, 0), cap0=False, cap1=False, smooth=30, repeat=1.4)[0]
    rim.uv = np.stack([-rim.uv[..., 1], rim.uv[..., 0]], axis=-1) * np.array([0.5, 1.0])
    rim.cell = "timber"
    parts.append(rim)
    for k in range(spokes):
        ang = k * 2 * math.pi / spokes + 0.2
        d = np.array([math.cos(ang), 0, math.sin(ang)])
        parts.append(tbeam(mat, d * hub_r * 0.8, d * (R - rim_d * 0.3), 0.075, 0.06, seed=seed + k, jitter=0))
    hub = tlathe(mat, [(0.0, -0.16), (hub_r, -0.15), (hub_r * 1.1, 0.0), (hub_r, 0.15), (0.0, 0.16)], 8, cell="iron",
                 rep=0.75)
    hub.rot(rx=90)
    parts.append(hub)
    # iron tyre band round the rim
    tyre = L.sweep(np.array([(0.012, -w * 0.4), (0.012, w * 0.4), (-0.012, w * 0.4), (-0.012, -w * 0.4)]),
                   path * ((R + rim_d / 2 + 0.006) / R), mat, up=(0, 1, 0), cap0=False, cap1=False, smooth=30,
                   repeat=1.5)[0]
    tyre.cell = "iron"
    parts.append(tyre)
    return parts


def build_gold_mine(aid):
    """Gold Seam (neutrals §5.2, bible §4.4 / §2.3): a squared block of layered cliff (stepped top: a 3.8 m
    centre with 3.05 m shoulders and back terrace), strata running round all four sides with a 0.35 m band
    of gold #D8B048 (quartz chunks, dark under-line, three branching veins; emissive texels only there,
    factor 0: the game pulses it) at 1.95-2.30 m on every face. A low square timber-framed adit in the
    middle of the front face opens into a dark recessed tunnel box. On the cliff top one bold headframe (two
    A-frames over a timber-collared shaft) carries a drum and a 1.7 m windlass wheel (node windlass_drum) whose
    rope lowers a bucket (node windlass_bucket) into the shaft; from the default camera the wheel rises above
    the far skyline. Gold veins outcrop across the rock tops. Spoil heap of grey tailings with gold flecks
    (front right), sluice on two trestles with gold-flecked riffles into a tub (front left), two lanterns.
    Fills the 12 x 12-cell (6 m) footprint: x, z in -3 .. 3. Two materials: rock atlas (GLOW) and timber
    atlas (LAMP)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.0, ao_strength=1.0, base_dark=0.62, base_h=0.4, top_light=0.14)
    ra, ta = mine_rock_atlas(), timber_atlas("gold_mine_timber")
    rock = ra.mat("rock", tag="GLOW", extras={
        "emission": "only the gold seam / vein texels have emission; emissiveFactor ships at 0 (no daylight glow): "
                    "raise emission_energy to pulse it while a worker is inside",
        "cells_px_per_m": ra.density_report()})
    tim = ta.mat("timber", tag="LAMP", extras={
        "emission": "only the lantern-glass texels have emission; emissiveFactor ships at 0: DayNight raises "
                    "emission_energy at night (windows light at 17:45, bible §1.5)",
        "cells_px_per_m": ta.density_report()})
    yf = 1.85                                         # front face of the centre stack (build +Y = front)
    adit_hw, adit_h = 0.84, MINE_BEDS[2][1]
    # ---------------------------------------------------------------- cliff stacks ---------------------
    stacks = [  # (outline, top, seed salt, adit)
        (round_rect(-2.0, 2.0, -0.95, yf, 0.25, front_stops=(-adit_hw, adit_hw)), 3.80, 1, (adit_hw, yf, adit_h)),
        (round_rect(-2.48, -1.7, -1.6, yf - 0.15, 0.22), 3.05, 2, None),
        (round_rect(1.7, 2.48, -1.5, yf - 0.12, 0.22), 3.05, 3, None),
        (round_rect(-2.46, 2.44, -2.48, -0.7, 0.3), 2.38, 4, None),     # back terrace: the seam bed is its top
    ]
    for base, top, salt, adit in stacks:
        mine_stack(A, rock, base, top, seed + 100 * salt, adit=adit, rng=rng)
    # rubble foot: a low scree skirt round the base and a few fallen blocks
    skirt = round_rect(-2.86, 2.86, -2.86, yf + 0.2, 0.5, step=0.4)
    q = np.c_[skirt, np.zeros(len(skirt))]
    nzs = L.noise1(q, 1.6, (2.0, 9.0, 4.0))
    outer = offset_outline(skirt, 0.08 + 0.06 * nzs)
    inner = offset_outline(skirt, -0.35)
    rings = [(outer, -0.03), (offset_outline(skirt, -0.1), 0.14), (inner, 0.22)]
    sk = rings_solid(rings, rock)
    sk.t = sk.t[np.abs(_face_axes(sk)[1][:, 2]) < 0.999]          # no cap (inside the cliff)
    keep = ~((np.abs(sk.v[sk.t][..., 0]).max(axis=1) < adit_hw + 0.1) & (sk.v[sk.t][..., 1].min(axis=1) > yf - 0.6))
    sk.t = sk.t[keep]
    sk.jitter((0.04, 0.04, 0.03), seed + 5, freq=2.0)
    rock_uv(sk, top="tailings", side="tailings", bottom="tailings", rep_top=1.8)
    sk.tint = np.full((len(sk.v), 3), 0.9)
    A.add(sk)
    for k in range(14):
        side = k % 4
        t = rng.uniform(-0.85, 0.85)
        if side == 0:
            x, y = -2.95, t * 2.6
        elif side == 1:
            x, y = 2.92, t * 2.6
        elif side == 2:
            x, y = t * 2.6, -2.93
        else:
            x, y = (2.6 if t > 0 else -2.6) - t * 0.4, yf + 0.25
            if abs(x) < 1.4:
                continue
        r = rng.uniform(0.14, 0.26)
        b = L.blob(rock, r, scale=(1.0, 0.8, 0.6), seed=seed + 300 + k, sphere="uv", segs=(7, 5), flat_top=0.8,
                   flat_bottom=0.1, cuts=2, smooth=36)
        b.rot(rz=rng.uniform(0, 360)).move(np.clip(x, -2.95 + r, 2.95 - r), np.clip(y, -2.95 + r, 2.95 - r), -0.03)
        rock_uv(b, top="ledge", side="ledge", bottom="ledge", rep_top=2.0, off=(rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(moss_tint(b, 0.7, seed + k, col=(0.62, 0.74, 0.45)))
    # gold veins outcropping across the plateau tops (the band's gold rows, slightly proud of the capstone):
    # the gold reads from the 56 deg camera, not only on the faces
    zg0, zg1 = (BAND_TOP - 2.25) / BAND_TOP, (BAND_TOP - 2.02) / BAND_TOP
    for k, (x0_, y0_, ang, ln, zt) in enumerate([(-1.7, 1.2, -20, 3.2, 3.8), (-0.3, -0.6, 25, 2.2, 3.8),
                                                  (-2.2, -1.2, 70, 1.6, 3.05), (0.6, -2.25, -8, 1.6, 2.38),
                                                  (2.1, -1.0, 95, 1.9, 3.05)]):
        pts = [np.array([x0_, y0_])]
        a = math.radians(ang)
        for j_ in range(8):
            a += rng.normal(0, 0.25)
            pts.append(pts[-1] + np.array([math.cos(a), math.sin(a)]) * ln / 8)
        pts = np.array(pts)
        path = np.c_[pts, np.full(len(pts), zt + 0.135)]
        widths = np.linspace(0.11, 0.035, len(pts))
        vr = L.ribbon(path, widths, rock, u_range=(zg0, zg1), v_range=(0.0, ln / BAND_RU), normal_hint=(0, 0, 1))
        vr.uv = np.stack([vr.uv[..., 1] + rng.uniform(0, 1), vr.uv[..., 0]], axis=-1)
        vr.cell = "band"
        vr.nmode = "up"
        vr.ao = False
        vr.ao_fn = lambda q: np.full(len(q.v), 0.95)
        A.add(vr)
    # plateau dressing: outcrops and turf humps
    for k, (x, y, r, zt) in enumerate([(-1.35, 0.6, 0.34, 3.88), (1.75, 1.0, 0.26, 3.88), (-1.6, -2.0, 0.32, 2.46),
                                       (1.5, -2.1, 0.28, 2.46), (2.35, 0.6, 0.22, 3.13)]):
        b = L.blob(rock, r, scale=(1, 0.8, 0.62), seed=seed + 320 + k, sphere="uv", segs=(8, 5), flat_top=0.85,
                   flat_bottom=0.1, noise_amp=0.2, smooth=38)
        b.move(x, y, zt - r * 0.3)
        rock_uv(b, top="ledge", side="ledge", bottom="ledge", rep_top=2.0)
        A.add(moss_tint(b, 0.9, seed + 320 + k, col=(0.5, 0.66, 0.36), up=0.45, patch=-0.1))
    # ---------------------------------------------------------------- adit: dark tunnel box --------------
    dep = 1.0
    yp = yf + MINE_OFF[0]                                     # the portal face round the adit
    yb = yp - dep
    bw = adit_hw + 0.03                                       # box a little wider than the cut: no gaps at the jambs
    box_q = [  # (quad, shade at the 4 corners)
        (np.array([(-bw, yb, 0.01), (bw, yb, 0.01), (bw, yp + 0.2, 0.01), (-bw, yp + 0.2, 0.01)]),
         (0.04, 0.04, 0.08, 0.08)),                                                      # floor (up)
        (np.array([(-bw, yb, 0.0), (bw, yb, 0.0), (bw, yb, adit_h), (-bw, yb, adit_h)]),
         (0.04, 0.04, 0.04, 0.04)),                                                      # back wall
        (np.array([(-bw, yb, 0.0), (-bw, yb, adit_h), (-bw, yp + 0.02, adit_h), (-bw, yp + 0.02, 0.0)]),
         (0.04, 0.04, 0.07, 0.07)),
        (np.array([(bw, yb, 0.0), (bw, yp + 0.02, 0.0), (bw, yp + 0.02, adit_h), (bw, yb, adit_h)]),
         (0.04, 0.07, 0.07, 0.04)),
        (np.array([(-bw, yb, adit_h), (bw, yb, adit_h), (bw, yp + 0.02, adit_h), (-bw, yp + 0.02, adit_h)]),
         (0.04, 0.04, 0.06, 0.06)),                                                      # ceiling
    ]
    for k, (quad, sh) in enumerate(box_q):
        tt = np.array([(0, 1, 2), (0, 2, 3)])
        c = quad.mean(axis=0)
        fn = np.cross(quad[1] - quad[0], quad[2] - quad[0])
        # faces must point into the tunnel (toward its centre line)
        inside = np.array([0.0, (yb + yp) / 2, adit_h / 2])
        if np.dot(fn, inside - c) < 0:
            tt = tt[:, ::-1]
        q = Part(quad.copy(), tt, rock, None, 30.0)
        q.uv = 0.15 + 0.7 * ((L.uv_box(quad, tt, 4.0) % 1.0))
        q.cell = "dark"
        q.ao = False
        q.ao_fn = (lambda s: (lambda p_: np.asarray(s, float)))(sh)
        A.add(q)
    # timber frame: outer set proud of the face, inner set half way in (darker)
    def post(x, y, z0, z1, w=0.26, s=0, cell="timber"):
        b = L.box((w, w, z1 - z0), tim, chamfer=0.035, center=(x, y, (z0 + z1) / 2))
        tim_part(b, cell, grain_axis=2)
        b.uv = b.uv + np.array([(s * 0.31) % 1, (s * 0.17) % 1])
        b.rot(ry=rng.uniform(-1.5, 1.5), pivot=(x, y, z0))
        b.jitter(0.006, seed + s)
        return b

    def rail(x0, x1, y, z, w=0.28, h=0.3, s=0):
        b = L.box((x1 - x0, w, h), tim, chamfer=0.035, center=((x0 + x1) / 2, y, z))
        tim_part(b, grain_axis=0)
        b.uv = b.uv + np.array([(s * 0.43) % 1, (s * 0.29) % 1])
        b.rot(ry=rng.uniform(-1.2, 1.2), pivot=((x0 + x1) / 2, y, z))
        b.jitter(0.006, seed + 40 + s)
        return b
    fy = yp + 0.12
    for k, (yy, sc, dk) in enumerate(((fy, 1.0, 1.0), (yp - 0.55, 0.94, 0.35))):
        xin = (adit_hw + 0.06) * sc
        ps = [post(-xin, yy, 0.0, 1.78 * sc, s=k * 2), post(xin, yy, 0.0, 1.78 * sc, s=k * 2 + 1),
              rail(-xin - 0.36, xin + 0.36, yy, 1.78 * sc + 0.12, s=k)]
        for p in ps:
            if dk < 1:
                p.ao = False
                p.ao_fn = (lambda d_: (lambda q_: np.full(len(q_.v), d_)))(dk * 0.5)
            A.add(p)
    for sx in (-1, 1):                                       # knee braces
        A.add(tbeam(tim, (sx * (adit_hw + 0.02), fy + 0.02, 1.25), (sx * 0.4, fy + 0.02, 1.84), 0.13, seed=seed + 7 + sx))
    A.add(rail(-1.02, 1.02, fy + 0.06, 0.06, w=0.36, h=0.12, s=7))   # sill
    lpts = []
    for sx in (-1, 1):                                       # lanterns on iron hooks either side of the mouth
        hook = L.box((0.05, 0.36, 0.05), tim, center=(sx * 1.22, fy + 0.02, 1.55))
        tim_part(hook, "iron", rep=1.5)
        A.add(hook)
        A.add(atlas_lantern(tim, (sx * 1.22, fy + 0.2, 1.55)))
        lpts.append([round(sx * 1.22, 3), 1.3, round(-(fy + 0.2), 3)])
    # ---------------------------------------------------------------- windlass headframe over a shaft ----
    # Two A-frames straddle a timber-collared shaft at the back of the top plateau; the axle runs front-back
    # through their apexes with the drum over the shaft, a crank in front and the big 1.7 m wheel behind the
    # back frame. Placed at the back, the wheel rises above the far skyline from the default camera (the
    # flat-black squint test: a squared cliff block crowned by a wheel, never a mound with a door).
    xc, lip = 0.45, 3.80
    top = lip + 0.11                                          # capstone top
    ys = -0.12                                                # shaft centre (y)
    yfr, ybk = ys + 0.52, ys - 0.5                            # front / back A-frames
    apex = lip + 1.75
    sx_c = xc + 0.2                                           # the rope drops off the drum's right side
    for k, (x0_, x1_, y0_, y1_) in enumerate([(sx_c - 0.5, sx_c + 0.5, ys - 0.5, ys - 0.32),
                                              (sx_c - 0.5, sx_c + 0.5, ys + 0.32, ys + 0.5),
                                              (sx_c - 0.5, sx_c - 0.32, ys - 0.32, ys + 0.32),
                                              (sx_c + 0.32, sx_c + 0.5, ys - 0.32, ys + 0.32)]):
        col = L.box((x1_ - x0_, y1_ - y0_, 0.2), tim, chamfer=0.03, center=((x0_ + x1_) / 2, (y0_ + y1_) / 2, top + 0.06))
        A.add(tim_part(col, grain_axis=0 if (x1_ - x0_) > (y1_ - y0_) else 1))
    hole = np.array([(sx_c - 0.33, ys - 0.33, top + 0.02), (sx_c + 0.33, ys - 0.33, top + 0.02),
                     (sx_c + 0.33, ys + 0.33, top + 0.02), (sx_c - 0.33, ys + 0.33, top + 0.02)])
    hq = Part(hole, np.array([(0, 1, 2), (0, 2, 3)]), rock, None, 30.0)
    hq.uv = 0.15 + 0.7 * ((L.uv_box(hole, hq.t, 4.0) % 1.0))
    hq.cell = "dark"
    hq.nmode = "up"
    hq.ao = False
    hq.ao_fn = lambda p_: np.full(4, 0.05)
    A.add(hq)
    for k, yy in enumerate((yfr, ybk)):
        bl = np.array([xc - 1.0, yy, top - 0.04])
        br = np.array([xc + 1.0, yy, top - 0.04])
        ap = np.array([xc, yy, apex])
        A.add(tbeam(tim, bl, ap + (-0.08, 0, 0.1), 0.26, seed=seed + 11 + k))
        A.add(tbeam(tim, br, ap + (0.08, 0, 0.1), 0.26, seed=seed + 13 + k))
        A.add(tbeam(tim, (xc - 0.62, yy + 0.02, top + 0.62), (xc + 0.62, yy + 0.02, top + 0.62), 0.17, seed=seed + 15 + k))
        cap = L.box((0.4, 0.4, 0.2), tim, chamfer=0.03, center=(xc, yy, apex + 0.16))
        A.add(tim_part(cap, grain_axis=0))
    for sx in (-1, 1):                                       # cross ties between the frames
        A.add(tbeam(tim, (xc + sx * 0.85, yfr, top + 0.25), (xc + sx * 0.45, ybk, top + 1.05), 0.14, seed=seed + 19 + sx))
    ax_c = np.array([xc, ys, apex + 0.1])
    A.node("windlass_drum", ax_c)
    R = 0.85
    whl = []
    axle = tlathe(tim, [(0.0, -1.0), (0.09, -0.99), (0.09, 0.84), (0.0, 0.85)], 8, cell="iron", rep=1.5)
    axle.rot(rx=-90)                                         # lathe Z -> +Y: from the wheel (back) to the crank (front)
    whl.append(axle)
    drum = tlathe(tim, [(0.0, -0.3), (0.2, -0.29), (0.2, 0.29), (0.0, 0.3)], 9)
    drum.rot(rx=-90)
    whl.append(drum)
    for p in spoked_wheel(tim, R, seed=seed + 30):
        p.move(0.0, -0.9, 0.0)
        whl.append(p)
    whl += [tbeam(tim, (0.0, 0.8, 0.0), (0.0, 0.8, -0.45), 0.08, seed=seed + 31, jitter=0, cell="iron"),
            tbeam(tim, (0.0, 0.8, -0.45), (0.0, 1.05, -0.45), 0.07, seed=seed + 32, jitter=0)]
    for p in whl:
        p.move(*ax_c)
        p.node = "windlass_drum"
        A.add(p)
    # rope off the drum down into the shaft; the bucket (node windlass_bucket) half out of the collar
    rope_x = xc + 0.21
    bucket_top = top + 0.32
    A.node("windlass_bucket", np.array([rope_x, ys, ax_c[2]]))
    rope = []
    for nh in ((0, 1, 0), (1, 0, 0)):
        r_ = L.ribbon(np.array([(rope_x, ys, ax_c[2]), (rope_x, ys, bucket_top + 0.45)]), 0.06, tim,
                      u_range=(0.1, 0.9), v_range=(0.0, 1.0), normal_hint=nh)
        r_.cell = "rope"
        r_.node = "windlass_bucket"
        rope.append(r_)
    bc = np.array([rope_x, ys, bucket_top])
    bucket = tlathe(tim, [(0.0, 0.0), (0.23, 0.0), (0.28, 0.42), (0.27, 0.44), (0.0, 0.42)], 9)
    bucket.move(*bc)
    hoops = []
    for z in (0.07, 0.33):
        hp = tlathe(tim, [(0.235 + z * 0.12, z), (0.245 + z * 0.12, z + 0.05)], 9, cell="iron", rep=1.5)
        hp.move(*bc)
        hoops.append(hp)
    handle = tbeam(tim, bc + (-0.28, 0, 0.46), bc + (0.28, 0, 0.46), 0.035, seed=seed + 33, jitter=0, cell="iron")
    for p in [bucket, handle] + hoops:
        p.node = "windlass_bucket"
    A.add(rope, bucket, handle, hoops)
    # ---------------------------------------------------------------- spoil heap (front right) ---------
    hc = np.array([2.05, 2.45])
    prof = [(1.0, 0.0), (0.86, 0.1), (0.62, 0.3), (0.38, 0.5), (0.15, 0.66), (0.0, 0.72)]
    heap = L.lathe(prof, 14, rock, a0=0.2)[0]
    heap.v[:, 0] *= 0.95
    heap.v[:, 1] *= 0.75
    heap.jitter((0.07, 0.07, 0.05), seed + 50, freq=2.4)
    heap.jitter((0.025, 0.025, 0.02), seed + 51)
    heap.v[:, 2] = np.maximum(heap.v[:, 2], 0.0)
    heap.move(hc[0], hc[1], -0.03)
    heap.v[:, 0] = np.clip(heap.v[:, 0], None, 2.97)
    heap.v[:, 1] = np.clip(heap.v[:, 1], None, 2.97)
    rock_uv(heap, top="tailings", side="tailings", bottom="tailings", rep_top=1.8)
    heap.smooth = 70
    heap.tint = np.full((len(heap.v), 3), 0.95)
    A.add(heap)
    for k in range(14):
        a, rr = rng.uniform(-0.3, 3.5), rng.uniform(0.2, 1.0)
        x, y = hc[0] + math.cos(a) * rr * 0.95, hc[1] + math.sin(a) * rr * 0.75
        if x > 2.85 or y > 2.85:
            continue
        zs = float(np.interp(rr, [p_[0] for p_ in prof[::-1]], [p_[1] for p_ in prof[::-1]]))
        st = L.blob(rock, rng.uniform(0.07, 0.13), scale=(1, 0.8, 0.5), seed=seed + 60 + k, sphere="uv", segs=(6, 4),
                    flat_bottom=0.2, flat_top=0.8, cuts=1, smooth=40)
        st.rot(rz=rng.uniform(0, 360), rx=rng.uniform(-20, 20)).move(x, y, max(0.0, zs * 0.85 - 0.06))
        rock_uv(st, top="tailings", side="tailings", bottom="tailings", rep_top=1.8)
        st.tint = np.full((len(st.v), 3), rng.uniform(0.75, 0.95))
        A.add(st)
    # spare pit props stacked on the plateau behind the headframe
    for k in range(4):
        z = lip + 0.22 + (0.17 if k == 3 else 0.0)
        x0 = -1.55 + (0.19 * k if k < 3 else 0.1)
        A.add(tbeam(tim, (x0, -0.45, z), (x0 + rng.uniform(-0.06, 0.06), 0.85, z), 0.17, seed=seed + 100 + k))
    # ---------------------------------------------------------------- sluice (front left) --------------
    path = np.array([(-1.15, yf - 0.1, lip + 0.12), (-1.65, yf + 0.28, 2.75), (-2.15, yf + 0.55, 1.55),
                     (-2.45, 2.62, 0.78)])
    trough_prof = np.array([(0.24, 0.22), (0.24, 0.0), (-0.24, 0.0), (-0.24, 0.22), (-0.18, 0.22), (-0.18, 0.05),
                            (0.18, 0.05), (0.18, 0.22)])
    trough = L.sweep(trough_prof, path, tim, up=(0, 0, 1), cap0=True, cap1=True, smooth=25, repeat=1.4)[0]
    trough.uv = np.stack([-trough.uv[..., 1], trough.uv[..., 0]], axis=-1) * np.array([0.5, 1.0])
    P, n = _face_axes(trough)
    # the inner floor (faces pointing up between the walls) carries the gold-flecked riffles
    trough.cell = np.where(n[:, 2] > 0.55, "riffle", "timber").astype(object)
    A.add(trough)
    wr = L.ribbon(path + np.array([0, 0, 0.11]), 0.3, tim, u_range=(0.0, 0.4), v_range=(0.0, 4.0), normal_hint=(0, 0, 1))
    wr.cell = "water"
    wr.nmode = "up"
    wr.ao = False
    wr.ao_fn = lambda q: np.full(len(q.v), 0.92)
    A.add(wr)
    for k, t in enumerate((1, 2)):                          # two trestles
        c = path[t]
        dvec = nrm(path[t + 1] - path[t - 1])
        side = nrm(np.cross(dvec, (0, 0, 1)))
        for sg in (-1, 1):
            foot = c + side * sg * 0.45
            foot = np.array([foot[0], foot[1], 0.0])
            A.add(tbeam(tim, foot, c + side * sg * 0.2 - np.array([0, 0, 0.02]), 0.13, seed=seed + 80 + k * 2 + sg))
        A.add(tbeam(tim, c + side * 0.33 - np.array([0, 0, c[2] * 0.55]), c - side * 0.33 - np.array([0, 0, c[2] * 0.55]),
                    0.09, seed=seed + 90 + k))
    tub_c = np.array([-2.5, 2.62, 0.0])
    tub = tlathe(tim, [(0.0, 0.03), (0.32, 0.0), (0.36, 0.44), (0.38, 0.46), (0.32, 0.46), (0.29, 0.06), (0.0, 0.09)], 10)
    tub.move(*tub_c)
    tub.v[:, 0] = np.maximum(tub.v[:, 0], -2.97)
    tub.v[:, 1] = np.minimum(tub.v[:, 1], 2.97)
    A.add(tub)
    for z in (0.1, 0.36):
        hp = tlathe(tim, [(0.33 + z * 0.08, z), (0.34 + z * 0.08, z + 0.05)], 10, cell="iron", rep=1.5)
        hp.move(*tub_c)
        A.add(hp)
    tw = L.lathe([(0.0, 0.38), (0.29, 0.38)], 10, tim)[0]
    tw.uv = L.uv_planar(tw.v, tw.t, (0, 1), 1 / 0.75)
    tw.cell = "water"
    tw.move(*tub_c)
    tw.nmode = "up"
    tw.ao = False
    tw.ao_fn = lambda q: np.full(len(q.v), 0.85)
    A.add(tw)
    lip_c = path[-1] + nrm(path[-1] - path[-2]) * 0.05
    fall = L.ribbon(np.array([lip_c + (0, 0, 0.1), tub_c + (0.05, -0.04, 0.42)]), 0.18, tim, u_range=(0.0, 0.3),
                    v_range=(0.0, 1.0), normal_hint=(0, 1, 0))
    fall.cell = "water"
    fall.ao = False
    fall.ao_fn = lambda q: np.ones(len(q.v))
    A.add(fall)
    # a feed pipe on the plateau from a little spring box to the sluice head
    A.add(tbeam(tim, (-0.65, yf - 0.9, lip + 0.12), path[0] + (0, 0, 0.05), 0.2, 0.16, seed=seed + 95))
    for p in A.parts:                                      # the mesh never leaves the 6 x 6 m footprint
        p.v[:, :2] = np.clip(p.v[:, :2], -2.99, 2.99)
    A.extras = {"adit_point": [0.0, 0.0, round(-(yp - 0.5), 3)], "worker_enter_point": [0.0, 0.0, -3.4],
                "lantern_points": lpts, "seam_height_m": list(MINE_BEDS[MINE_SEAM]), "cliff_height_m": lip,
                "headframe_top_m": round(float(ax_c[2] + R + 0.07), 2),
                "silhouette": "flat-black from the RTS pitch (front): a squared, stepped cliff block crowned by the "
                              "headframe's 1.7 m wheel"}
    return A


def tex_awning_stripes(seed=71, n=256):
    """Awning cloth: cream #E8DCC0 / sage #7E9A6E stripes along v (6 per 2 m repeat), piping, faint folds and
    grime; tileable both ways (128 px/m)."""
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        u = xx / n
        ph = (u * 6) % 1.0
        stripe = np.where((np.floor(u * 6) % 2) == 0, 1.0, 0.0)[..., None]
        col = hexcol("#E8DCC0") * stripe + hexcol("#7E9A6E") * (1 - stripe)
        pip = (np.exp(-((ph - 0.0) / 0.015) ** 2) + np.exp(-((ph - 1.0) / 0.015) ** 2))[..., None]
        col = col * (1 - 0.28 * np.clip(pip, 0, 1))
        fold = 0.9 + 0.1 * np.cos(u * 2 * math.pi * 3)[..., None]
        grime = L.periodic_noise(n, seed, 2.2)[..., None]
        weave = (0.5 + 0.5 * np.sin(xx * math.pi / 1.5) * np.sin(yy * math.pi / 1.5))[..., None]
        return L.to_img(col * fold * (0.9 + 0.12 * grime) * (0.96 + 0.06 * weave))
    return lambda: L.cached_image(("awning", seed, n), fn)


def tex_sacking(seed=72, n=128):
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        weave = 0.5 + 0.5 * np.sin(xx * math.pi / 2.0) * np.sin(yy * math.pi / 2.0)
        col = hexcol("#9C8763") * (0.82 + 0.12 * weave + 0.16 * L.periodic_noise(n, seed, 2.0))[..., None]
        return L.to_img(col)
    return lambda: L.cached_image(("sacking2", seed, n), fn)


def tex_scales(seed=73, n=200):
    """Rundling scales: staggered rows of overlapping umber #7A5A3A scales edged #B08A5A."""
    def fn():
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        rows, cols = 9, 8
        sy, sx = n / rows, n / cols
        r_ = yy / sy
        row = np.floor(r_)
        fy_ = r_ - row
        cx = (xx / sx + 0.5 * (row % 2)) % 1.0 - 0.5
        d = np.hypot(cx, (fy_ - 0.05) * 0.9)
        edge = smoothstep(0.36, 0.48, d)
        base = hexcol("#7A5A3A") * (0.75 + 0.35 * (1 - fy_))[..., None]
        sc = base * (1 - edge[..., None]) + hexcol("#B08A5A") * edge[..., None]
        return L.to_img(sc * (0.9 + 0.2 * L.periodic_noise(n, seed, 2.0))[..., None])
    return lambda: L.cached_image(("scales", seed, n), fn)


def stall_cloth_atlas():
    cells = [
        L.Cell("stripes", tex_awning_stripes(), "tile", (256, 256), (2.0, 2.0)),
        L.Cell("sacking", tex_sacking(), "tile", (128, 128), (1.0, 1.0)),
        L.Cell("scales", tex_scales(), "decal", (200, 200), (0.6, 0.6)),
        L.Cell("jar", L.tex_flat("#C9B48A", 32, 0.1, 9), "decal", (24, 24), (0.3, 0.3)),
    ]
    return L.Atlas("neutral_weighstall_cloth", cells, 512)


def M_brass():
    """Brass #B8913A (bible §2.3): the polished-bronze swatch's light pattern re-coloured on a brass ramp
    (shadow #6E5424 -> #B8913A -> painted highlight #D9B868), hue ~41 deg, saturation capped at 0.62."""
    def fn():
        im = L.swatch(SW + "clans_polished_bronze.png", seamless=True)().convert("RGB")
        a = np.asarray(im, np.float32) / 255.0
        lum = a.mean(axis=2)
        lo, hi = np.percentile(lum, 3), np.percentile(lum, 97)
        t = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
        d, m, h = hexcol("#6E5424"), hexcol("#B8913A"), hexcol("#D9B868")
        col = np.where((t < 0.55)[..., None], d + (m - d) * (t / 0.55)[..., None],
                       m + (h - m) * ((t - 0.55) / 0.45)[..., None])
        return L.to_img(L.hsv_limit(np.clip(col, 0, 1), 1.0, 0.62))
    return Mat("brass", lambda: L.cached_image(("brass_v2",), fn), repeat=1.2, size=256)


def cloth_sheet(mat, corners, nu, nv, sag=0.0, seed=0, cell="stripes", rep=2.0):
    """Awning sheet on the cloth atlas: UVs by arc length in metres / rep (128 px/m both ways)."""
    parts = sheet(mat, corners, nu, nv, sag=sag, seed=seed, repeat=rep)
    for p in parts:
        p.cell = cell
    return parts


def build_weighstall(aid):
    """Weighstall (neutrals §5.3, bible §2.3): a timber market stall under a cream-and-sage striped awning with
    a sagging canopy and a scalloped valance on three sides, piled with crates, sacks and jars; side tables
    left and right, the Rundlings' two-wheeled handcart and stores at the back, so the stall fills its 12 x
    12-cell (6 m) footprint. Crowned by a ~7 m brass balance on a 0.5 m post on a stepped plinth (nodes
    balance_beam > balance_pan_l / balance_pan_r tip in the wind and swing on a purchase), a curled-up Rundling
    dozing on the counter (node shopkeeper: breathe by scaling), a stall lantern (timber atlas, LAMP)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=1.0, ao_strength=1.0, base_dark=0.55, base_h=0.4, top_light=0.18)
    ta = timber_atlas("neutral_weighstall_timber", light=True)
    tim = ta.mat("timber", tag="LAMP", extras={
        "emission": "only the lantern-glass texels have emission; emissiveFactor ships at 0: lit at night",
        "cells_px_per_m": ta.density_report()})
    ca = stall_cloth_atlas()
    cloth = ca.mat("cloth", extras={"cells_px_per_m": ca.density_report()})
    brass = M_brass()

    def box(sz, c, ch=0.0, rot=None, cell="timber"):
        b = L.box(sz, tim, chamfer=ch, center=c)
        if rot:
            b.rot(*rot, pivot=c)
        tim_part(b, cell, grain_axis=int(np.argmax(sz)))
        b.uv = b.uv + np.array([rng.uniform(0, 1), rng.uniform(0, 1)])
        A.add(b)
        return b

    def bbox(sz, c, ch=0.0):
        b = L.box(sz, brass, chamfer=ch, center=c)
        b.uv = L.uv_box(b.v, b.t, brass.repeat, (rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(b)
        return b
    # deck and counter
    box((3.8, 3.1, 0.18), (0.0, -0.05, 0.09))
    box((3.1, 0.6, 0.9), (0.0, 0.92, 0.63))
    box((3.35, 0.72, 0.08), (0.0, 0.98, 1.12), ch=0.02)
    # posts (front lower than back: the awning slopes to the front)
    for x in (-1.65, 1.65):
        box((0.18, 0.18, 2.42), (x, 1.2, 1.21), rot=(0, rng.uniform(-1.5, 1.5), 0))
        box((0.17, 0.17, 2.9), (x, -1.4, 1.45), rot=(0, rng.uniform(-1.5, 1.5), 0))
        box((0.1, 2.7, 0.12), (x, -0.1, 2.66), rot=(-9.5, 0, 0))
    # back wall with shelves and jars
    box((3.2, 0.08, 1.7), (0.0, -1.34, 1.03))
    for z in (1.0, 1.55):
        box((3.0, 0.32, 0.05), (0.0, -1.17, z))
    jar_cols = [(1.0, 0.75, 0.45), (0.6, 0.75, 0.55), (0.75, 0.4, 0.32), (1.0, 0.9, 0.7)]

    def jar(x, y, z, hgt, rad):
        j = L.lathe([(0.0, 0.0), (rad, 0.0), (rad * 1.15, hgt * 0.45), (rad * 0.6, hgt * 0.9), (rad * 0.65, hgt),
                     (0.0, hgt)], 6, cloth)[0]
        j.uv = np.clip(L.uv_box(j.v, j.t, 0.3) % 1.0, 0.1, 0.9)
        j.cell = "jar"
        j.tint = np.ones((len(j.v), 3)) * np.asarray(jar_cols[rng.integers(4)])
        j.move(x, y, z)
        A.add(j)
    for z in (1.025, 1.575):
        x = -1.35
        while x < 1.35:
            hgt, rad = rng.uniform(0.18, 0.3), rng.uniform(0.07, 0.1)
            jar(x, -1.14 + rng.uniform(-0.04, 0.04), z, hgt, rad)
            x += rad * 2 + rng.uniform(0.04, 0.12)
    # awning: a sagging striped canopy and a scalloped valance on the front and both sides
    y0, y1, zb, zf = -1.55, 1.32, 2.98, 2.48
    for p in cloth_sheet(cloth, [(-1.9, y0, zb), (1.9, y0, zb), (1.9, y1, zf), (-1.9, y1, zf)], 8, 6, sag=0.16, seed=seed):
        A.add(p)

    def valance(p0, p1, n, zt, seed_):
        """Scalloped flaps hanging from the awning edge p0 -> p1: n half-round tongues, double sided."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        L_ = np.linalg.norm(d)
        verts, tris = [], []
        segs = 5
        for k in range(n):
            a = p0 + d * k / n
            b = p0 + d * (k + 1) / n
            base_i = len(verts)
            for j in range(segs + 1):
                t = j / segs
                pt = a + (b - a) * t
                drop = 0.2 + 0.14 * math.sin(math.pi * t)
                verts.append(pt + np.array([0, 0, 0.0]))
                verts.append(pt + np.array([0, 0, -drop]) + np.r_[nrm(np.cross(d, (0, 0, 1)))[:2] * 0.02, 0])
            for j in range(segs):
                i0 = base_i + 2 * j
                tris += [(i0, i0 + 2, i0 + 3), (i0, i0 + 3, i0 + 1)]
        verts = np.array(verts)
        verts[:, 2] += zt - p0[2]
        tris = np.array(tris)
        out = []
        for tt in (tris, tris[:, ::-1]):
            q = Part(verts.copy(), tt, cloth, None, 60.0)
            P = q.v[q.t]
            along = (P - p0) @ (d / L_)
            q.uv = np.stack([along / 2.0, -P[..., 2] / 2.0], axis=-1)
            q.cell = "stripes"
            out.append(q)
        return out
    for p in valance((-1.92, y1 + 0.01, zf), (1.92, y1 + 0.01, zf), 9, zf, seed):
        A.add(p)
    for sx in (-1, 1):
        for p in valance((sx * 1.92, y1, zf), (sx * 1.92, y0, zb), 7, zf, seed + sx):
            # the side valance follows the sloping edge
            t = (p.v[:, 1] - y1) / (y0 - y1)
            p.v[:, 2] += (zb - zf) * np.clip(t, 0, 1)
            A.add(p)
    # goods: sacks and crates in front of and on the counter, keeping the middle of the front open
    def sack(x, y, z, s, node=""):
        sk = sack_part(cloth, s * 2.0, s * 0.8, seed=seed + int(x * 10 + y * 7), rep=1.0)
        sk.rot(rz=rng.uniform(0, 360)).move(x, y, z)
        sk.uv = L.uv_box(sk.v, sk.t, 1.0)
        sk.cell = "sacking"
        sk.node = node
        A.add(sk)
        return sk
    for x, y, z, s in [(-2.2, 2.25, 0.0, 0.34), (-1.8, 2.55, 0.0, 0.3), (1.0, 1.06, 1.16, 0.22), (2.15, 2.3, 0.0, 0.32),
                       (2.5, 2.65, 0.0, 0.28)]:
        sack(x, y, z, s)
    for k, (x, y, s, rz) in enumerate([(2.5, 1.9, 0.5, 15), (-2.55, 1.85, 0.55, -10), (-2.5, 1.85, 0.4, 30)]):
        z = 0.0 if k < 2 else 0.47
        box((s, s, s * 0.85), (x, y, z + s * 0.425), ch=0.025, rot=(0, 0, rz))
    # side tables (trestle tables with goods) left and right
    for sx in (-1, 1):
        x = sx * 2.5
        box((0.8, 2.3, 0.07), (x, -0.15, 0.82), ch=0.015)
        for yy in (-1.1, 0.8):
            for dx in (-0.3, 0.3):
                box((0.08, 0.08, 0.8), (x + dx, yy, 0.4), rot=(0, sx * 6, 0))
        for k in range(3):
            jar(x + rng.uniform(-0.2, 0.2), -0.9 + k * 0.45, 0.855, rng.uniform(0.2, 0.3), rng.uniform(0.08, 0.11))
        sack(x, 0.55, 0.85, 0.24)
        box((0.5, 0.42, 0.34), (x, -1.45 + 0.0, 0.855 + 0.17), ch=0.02, rot=(0, 0, rng.uniform(-10, 10)))
    # the Rundlings' handcart behind the stall (two wheels, a box bed, long push handles), stores beside it
    cart = []
    bed_c = np.array([-1.15, -2.35, 0.62])
    cart.append(L.box((1.5, 0.95, 0.07), tim, center=bed_c))
    cart.append(L.box((1.5, 0.06, 0.32), tim, center=bed_c + (0, 0.47, 0.18)))
    cart.append(L.box((1.5, 0.06, 0.32), tim, center=bed_c + (0, -0.47, 0.18)))
    cart.append(L.box((0.06, 0.95, 0.32), tim, center=bed_c + (0.75, 0, 0.18)))
    for p in cart:
        tim_part(p, grain_axis=0 if np.ptp(p.v[:, 0]) > 1 else 1)
    for sy in (-1, 1):
        cart.append(tbeam(tim, bed_c + (-0.7, sy * 0.38, 0.03), bed_c + (-1.55, sy * 0.42, -0.42), 0.07, seed=seed + 50 + sy))
    for sy in (-1, 1):
        for p in spoked_wheel(tim, 0.42, w=0.06, spokes=6, rim_d=0.07, hub_r=0.08, seed=seed + 60 + sy):
            p.move(*(bed_c + np.array([0.15, sy * 0.55, -0.2])))
            cart.append(p)
    for p in cart:
        p.rot(rz=12, pivot=bed_c)
        A.add(p)
    for k, (x, y) in enumerate([(-1.5, -2.35), (-0.95, -2.2)]):
        sack(x, y, 0.66, 0.24)
    for k, (x, y, s, rz) in enumerate([(1.55, -2.45, 0.6, 8), (2.25, -2.5, 0.5, -14), (1.75, -2.4, 0.42, 25)]):
        z = 0.0 if k < 2 else 0.51
        box((s, s, s * 0.85), (x, y, z + s * 0.425), ch=0.025, rot=(0, 0, rz))
    # brass weighing pots on the counter
    for x in (-0.55, -0.3):
        p = L.lathe([(0.0, 0.0), (0.09, 0.0), (0.1, 0.12), (0.07, 0.16), (0.0, 0.16)], 7, brass)[0]
        p.move(x, 1.0, 1.16)
        A.add(p)
    # the Rundling, curled into a scaled ball, dozing on the counter
    sk_c = np.array([0.3, 1.1, 1.16])
    A.node("shopkeeper", sk_c)
    bv, bt = L.uvsphere(10, 7, 0.3)
    bv = bv * np.array([1.0, 0.92, 0.85])
    bv[:, 2] += 0.255
    bp = Part(bv + sk_c, bt, cloth, None, 60.0)
    bp.uv = L.uv_box(bv - np.array([0, 0, 0.255]), bt, 0.7) + 0.5
    bp.cell = "scales"
    bp.node = "shopkeeper"
    A.add(bp)
    tail = L.sweep(ngon(5, 1.0), bezier(sk_c + (0.18, -0.22, 0.05), sk_c + (0.38, 0.05, 0.08), sk_c + (0.2, 0.27, 0.12), 5),
                   cloth, scales=[0.11, 0.09, 0.07, 0.05, 0.02], cap1=True)[0]
    tail.uv = L.uv_box(tail.v - sk_c, tail.t, 1.2) + 0.5
    tail.cell = "scales"
    tail.node = "shopkeeper"
    A.add(tail)
    snout = L.lathe([(0.06, 0.0), (0.045, 0.1), (0.02, 0.17), (0.0, 0.19)], 6, cloth)[0]
    snout.rot(ry=-75).move(*(sk_c + (-0.24, 0.12, 0.2)))
    snout.uv = L.uv_box(snout.v - sk_c, snout.t, 1.2) + 0.5
    snout.cell = "scales"
    snout.node = "shopkeeper"
    A.add(snout)
    for dy in (-0.035, 0.035):
        g = L.lathe([(0.0, -0.004), (0.028, -0.004), (0.028, 0.004), (0.0, 0.004)], 6, brass)[0]
        g.rot(ry=90).move(*(sk_c + (-0.33, 0.12 + dy, 0.27)))
        g.node = "shopkeeper"
        A.add(g)
    # the giant balance: a 0.5 m post on a stepped plinth, pivot, beam (node), chains and pans (child nodes)
    px, py = 0.0, -1.75
    box((1.15, 1.15, 0.24), (px, py, 0.12), ch=0.04)
    bbox((0.82, 0.82, 0.22), (px, py, 0.35), ch=0.04)
    post = L.box((0.5, 0.5, 6.05), tim, center=(px, py, 3.45), chamfer=0.05)
    A.add(tim_part(post, grain_axis=2))
    for z in (1.3, 3.1, 4.9):
        bbox((0.6, 0.6, 0.15), (px, py, z), ch=0.025)
    piv = L.lathe([(0.0, 6.35), (0.38, 6.4), (0.44, 6.6), (0.33, 6.78), (0.11, 6.86), (0.19, 7.0), (0.08, 7.2),
                   (0.0, 7.3)], 8, brass)[0]
    piv.move(px, py, 0)
    A.add(piv)
    beam_c = np.array([px, py, 6.62])
    A.node("balance_beam", beam_c)
    span_x = 2.12
    bpath = np.array([(-span_x, py, 6.56), (-1.0, py, 6.64), (0.0, py, 6.67), (1.0, py, 6.64), (span_x, py, 6.56)])
    beam = L.sweep(np.array([(0.0, 0.11), (0.07, 0.0), (0.0, -0.11), (-0.07, 0.0)]), bpath, brass,
                   scales=[1.1, 1.5, 2.0, 1.5, 1.1], up=(0, 0, 1), cap0=True, cap1=True)[0]
    beam.node = "balance_beam"
    A.add(beam)
    for sx in (-1, 1):
        knob = L.lathe([(0.0, -0.17), (0.15, -0.1), (0.17, 0.0), (0.15, 0.1), (0.0, 0.17)], 7, brass)[0]
        knob.move(sx * span_x, py, 6.56)
        knob.node = "balance_beam"
        A.add(knob)
        name = "balance_pan_l" if sx < 0 else "balance_pan_r"
        hang = np.array([sx * (span_x - 0.05), py, 6.5])
        A.node(name, hang, parent="balance_beam")
        pan_z = 4.35
        prad = 0.78
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
            sk = sack(hang[0], py, pan_z + 0.06, 0.3, node=name)
        else:
            for k, (dx, dy, r) in enumerate([(0.0, 0.0, 0.17), (0.0, 0.0, 0.12), (0.22, 0.12, 0.1)]):
                w = L.lathe([(0.0, 0.0), (r, 0.0), (r, 0.1), (r * 0.6, 0.13), (0.0, 0.13)], 7, brass)[0]
                w.move(hang[0] + dx, py + dy, pan_z + 0.06 + (0.1 * k if k < 2 else 0.0))
                w.node = name
                A.add(w)
    # stall lantern hanging under the front corner of the awning
    hook = L.box((0.04, 0.04, 0.2), tim, center=(1.65, 1.6, 2.28))
    A.add(tim_part(hook, "iron", rep=1.5))
    A.add(atlas_lantern(tim, (1.65, 1.6, 2.2)))
    for p in A.parts:
        p.v[:, :2] = np.clip(p.v[:, :2], -2.99, 2.99)
        if p.mat is brass:
            p.uv = L.uv_box(p.v, p.t, brass.repeat, (0.37, 0.11))
    A.extras = {"counter_point": [0.0, 1.16, -1.0], "lantern_points": [[1.65, 1.8, -1.6]]}
    return A


def spring_atlas():
    """Hale Spring atlas: moss bank, mossy stone, oak bark, planks (grain along u), painted spring water
    #5AA3A0 (S <= 0.45, no glow), end grain."""
    def bark2():
        return lambda: L.cached_image(("spring_bark",), lambda: M_bark().image().convert("RGB").resize((256, 256),
                                                                                                       L.Image.LANCZOS))

    def water():
        def fn():
            im = L.load_rgb(TEX + "water_ripples.png").convert("RGB")
            n = im.width
            im = L.make_seamless(im.crop((0, 0, n // 2, n // 2))).resize((256, 256), L.Image.LANCZOS)
            a = np.asarray(im, np.float32) / 255.0
            lum = a.mean(axis=2, keepdims=True)
            col = hexcol("#5AA3A0") * 0.85 * (0.82 + 0.3 * (lum - lum.mean()) / max(lum.std() * 3, 1e-3))
            return L.to_img(L.hsv_limit(np.clip(col, 0, 1), 1.0, 0.45))
        return lambda: L.cached_image(("spring_water",), fn)
    tim = timber_atlas("tmp_spring").cells["timber"]
    cells = [
        L.Cell("moss", _swatch_crop(TEX + "gv_thick_meadow.png", 0.5, 256, sat=0.95, key="sp"), "tile", (256, 256), (2.0, 2.0)),
        L.Cell("rock", tex_rock(12, 512, moss_amt=1.3), "tile", (256, 256), (2.0, 2.0)),
        L.Cell("bark", bark2(), "tile", (256, 256), (2.0, 2.0)),
        L.Cell("endgrain", L.tex_rings(5, 256), "decal", (100, 100), (0.4, 0.4)),
        L.Cell("water", water(), "tile", (256, 256), (2.0, 2.0)),
        L.Cell("timber", tim.image, "tile", (448, 224), (2.8, 1.4)),
    ]
    return L.Atlas("neutral_hale_spring", cells, 1024)


def build_hale_spring(aid):
    """Hale Spring (neutrals §5.8, bible §2.3): a moss-ringed spring pool (r ~1.7 m, walkable shallow water)
    filling the 8 x 8-cell (4 m) pad, fed by a hollow-log flume on two trestles from a mossy source rock at the
    back (both up to the 2 m height cap); the flume spills onto a 1.2 m overshot waterwheel at the pool's edge
    (node `waterwheel`, spins about its local Z axis = the axle, which runs front-back on two forked posts).
    Three flat stepping stones cross the front of the pool. Natural stones only: no carved rim, no glowing
    water (warm sparkles are VFX by day)."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.8, ao_strength=1.0, base_dark=0.65, base_h=0.2, top_light=0.15)
    at = spring_atlas()
    mat = at.mat("spring", extras={"cells_px_per_m": at.density_report()})
    meadow = M_meadow()
    pc = np.array([0.0, 0.2])                          # pool centre (a little forward of the pad centre)
    K = 28
    ang = np.linspace(0, 2 * math.pi, K, endpoint=False)
    q = np.stack([np.cos(ang) * 2, np.sin(ang) * 2, np.zeros(K)], axis=1)
    wob = L.noise1(q, 0.6, (3.0, 1.0, 7.0))

    def ring(r, amp=0.12):
        rr = r * (1 + amp * wob)
        return np.stack([pc[0] + np.cos(ang) * rr * 1.05, pc[1] + np.sin(ang) * rr * 0.93], axis=1)
    # moss bank: from under the water edge up over a low lip and down to the pad edge
    rings = [(ring(1.55), 0.02), (ring(1.72), 0.16), (ring(1.86), 0.24), (ring(2.0, 0.06), 0.14), (ring(2.12, 0.04), -0.02)]
    verts = np.concatenate([np.c_[r_, np.full(K, z)] for r_, z in rings])
    tris = np.array(L._ring_faces(len(rings), K, True), np.int64)
    P = verts[tris]
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    if (fn[:, 2] < 0).sum() > len(fn) / 2:
        tris = tris[:, ::-1]
    bank = Part(verts, tris, mat, None, 40.0)
    bank.jitter((0.05, 0.05, 0.025), seed, freq=1.8)
    bank.v[:, 2] = np.maximum(bank.v[:, 2], -0.02)
    bank.v[:, :2] = np.clip(bank.v[:, :2], -2.0, 2.0)
    rock_uv(bank, top="moss", side="moss", bottom="moss", rep_top=2.0, up_thr=0.0)
    bank.nmode = "up"
    bank.nblend = 0.6
    A.add(bank)
    # pool floor (dark, under the water) and the water surface
    fl = Part(np.vstack([[pc[0], pc[1], -0.12]] + [np.r_[p_, 0.0] for p_ in ring(1.62)]),
              np.array([(0, i, i % K + 1) for i in range(1, K + 1)]), mat, None, 60.0)
    fl.uv = L.uv_planar(fl.v, fl.t, (0, 1), 1 / 2.0)
    fl.cell = "rock"
    fl.ao = False
    fl.ao_fn = lambda p_: np.full(len(p_.v), 0.35)
    A.add(fl)
    wv = np.vstack([[pc[0], pc[1], 0.07]] + [np.r_[p_, 0.07] for p_ in ring(1.66)])
    wt = np.array([(0, i, i % K + 1) for i in range(1, K + 1)])
    wp = Part(wv, wt, mat, L.uv_planar(wv, wt, (0, 1), 1 / 2.0), 60.0)
    wp.cell = "water"
    wp.nmode = "up"
    wp.ao = False
    wp.ao_fn = lambda p_: 0.72 + 0.28 * smoothstep(0.2, 1.6, np.hypot(p_.v[:, 0] - pc[0], p_.v[:, 1] - pc[1]))
    A.add(wp)
    # bank stones: irregular, mossy, half sunk in the moss (none on the front, where the stepping stones are)
    for k in range(9):
        a = k * 2 * math.pi / 9 + rng.uniform(-0.2, 0.2) + 0.3
        if math.sin(a) > 0.75:
            continue
        r = rng.uniform(0.18, 0.32)
        b = L.blob(mat, r, scale=(1.0, 0.8, 0.6), seed=seed + 10 + k, sphere="uv", segs=(8, 5), noise_amp=0.16,
                   flat_top=0.82, flat_bottom=0.12, cuts=2, smooth=40)
        rr = 1.78 + rng.uniform(-0.08, 0.1)
        b.rot(rz=math.degrees(a)).move(pc[0] + math.cos(a) * rr * 1.05, pc[1] + math.sin(a) * rr * 0.93, 0.06)
        b.v[:, :2] = np.clip(b.v[:, :2], -2.0, 2.0)
        rock_uv(b, top="rock", side="rock", bottom="rock", rep_top=2.0, off=(rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(moss_tint(b, 0.9, seed + k, patch=-0.1))
    # stepping stones across the front of the pool
    for k, (x, y) in enumerate([(-0.75, 1.28), (0.05, 1.42), (0.85, 1.25)]):
        b = L.blob(mat, 0.26, scale=(1.0, 0.85, 0.32), seed=seed + 40 + k, sphere="uv", segs=(9, 4), noise_amp=0.1,
                   flat_top=0.7, flat_bottom=0.1, cuts=1, smooth=40)
        b.rot(rz=rng.uniform(0, 180)).move(x, y, 0.0)
        rock_uv(b, top="rock", side="rock", bottom="rock", rep_top=2.0, off=(0.3 * k, 0.17 * k))
        A.add(moss_tint(b, 0.5, seed + 40 + k, patch=0.2))
    # source rock at the back (the spring issues from a cleft ~1.4 m up), and a companion
    src = L.blob(mat, 0.85, subdiv=3, scale=(1.0, 0.75, 1.05), seed=seed + 30, noise_amp=0.15, flat_top=0.88,
                 flat_bottom=0.06, cuts=5, cut_depth=0.14, smooth=30)
    src.move(-0.45, -1.4, -0.05)
    src2 = L.blob(mat, 0.5, scale=(1.0, 0.8, 0.85), seed=seed + 31, noise_amp=0.15, flat_top=0.85, flat_bottom=0.1,
                  cuts=3, smooth=30, sphere="uv", segs=(8, 5))
    src2.move(0.45, -1.55, -0.04)
    for b in (src, src2):
        b.v[:, :2] = np.clip(b.v[:, :2], -2.0, 2.0)
        rock_uv(b, top="rock", side="rock", bottom="rock", rep_top=2.0)
        A.add(moss_tint(b, 1.0, seed + 30, patch=-0.2))
    top_src = float(src.v[:, 2].max())
    # hollow-log flume from the cleft to the wheel, on two forked trestles
    wc = np.array([1.42, -0.15, 0.68])                 # wheel centre (axle along Y)
    wr = 0.6
    f0 = np.array([-0.15, -1.25, min(top_src + 0.05, 1.86)])
    f2 = np.array([wc[0] - 0.12, wc[1], wc[2] + wr + 0.22])
    f1 = (f0 + f2) / 2 + np.array([0.0, 0.0, 0.03])
    path = np.stack([f0, f1, f2])
    K2 = 9
    a2 = np.linspace(-0.25 * math.pi, 1.25 * math.pi, K2)      # open U (cut away on top)
    outer = np.stack([np.cos(a2) * 0.19, -np.sin(a2) * 0.19], axis=1)
    inner = np.stack([np.cos(a2[::-1]) * 0.12, -np.sin(a2[::-1]) * 0.12], axis=1)
    log_ = L.sweep(np.vstack([outer, inner]), path, mat, up=(0, 0, 1), cap0=True, cap1=True, repeat=2.0)[0]
    log_.cell = "bark"
    A.add(log_)
    wrib = L.ribbon(path + np.array([0, 0, -0.05]), 0.17, mat, u_range=(0.1, 0.25), v_range=(0.0, 1.2),
                    normal_hint=(0, 0, 1))
    wrib.cell = "water"
    wrib.nmode = "up"
    wrib.ao = False
    wrib.ao_fn = lambda p_: np.ones(len(p_.v))
    A.add(wrib)
    for t in (0.33, 0.7):                                       # two trestles under the flume
        c = f0 + (f2 - f0) * t
        c[2] -= 0.18
        dvec = nrm(f2 - f0)
        side = nrm(np.cross(dvec, (0, 0, 1)))
        for sg in (-1, 1):
            foot = c + side * sg * 0.38
            foot[2] = 0.0
            leg = pole(mat, foot, c + side * sg * 0.06 + np.array([0, 0, 0.12]), 0.055, 0.045, sides=5, seed=int(t * 10) + sg)
            for lp in leg:
                lp.uv = lp.uv / 2.0
                lp.cell = "bark"
                A.add(lp)
        cross = tbeam(mat, c + side * 0.3 - np.array([0, 0, c[2] * 0.45]), c - side * 0.3 - np.array([0, 0, c[2] * 0.45]),
                      0.07, seed=seed + int(t * 100))
        A.add(cross)
    # spill from the flume end onto the wheel's top buckets, and from the wheel into the pool
    spout = f2 + nrm(f2 - f1) * 0.1
    fall = L.ribbon(np.array([spout + (0, 0, -0.04), spout + (0.12, 0, -0.25), (wc[0] + 0.3, wc[1], 0.08)]), 0.15, mat,
                    u_range=(0.3, 0.45), v_range=(0.0, 0.8), normal_hint=(0, 1, 0.3))
    fall.cell = "water"
    fall.ao = False
    fall.ao_fn = lambda p_: np.ones(len(p_.v))
    A.add(fall)
    # the waterwheel: two rims, 10 paddles, hub (node waterwheel; axle along Y)
    A.node("waterwheel", wc)
    parts = []
    for dy in (-0.13, 0.13):
        a_ = np.linspace(0, 2 * math.pi, 17)
        rim_path = np.stack([np.cos(a_) * wr, np.full(17, dy), np.sin(a_) * wr], axis=1)
        rim = L.sweep(np.array([(0.035, 0.022), (0.035, -0.022), (-0.035, -0.022), (-0.035, 0.022)]), rim_path, mat,
                      up=(0, 1, 0), cap0=False, cap1=False, smooth=30, repeat=1.4)[0]
        rim.uv = np.stack([-rim.uv[..., 1], rim.uv[..., 0]], axis=-1) * np.array([0.5, 1.0])
        rim.cell = "timber"
        parts.append(rim)
        for k in range(5):                                      # spokes
            a = k * 2 * math.pi / 5 + 0.3
            d = np.array([math.cos(a), 0.0, math.sin(a)])
            parts.append(tbeam(mat, d * 0.07 + (0, dy, 0), d * (wr - 0.03) + (0, dy, 0), 0.045, 0.035, seed=seed + k,
                               jitter=0))
    for k in range(10):
        a = k * 2 * math.pi / 10
        pd = L.box((0.3, 0.32, 0.04), mat, center=(0, 0, 0))
        pd.rot(ry=-math.degrees(a)).move(math.cos(a) * (wr - 0.1), 0.0, math.sin(a) * (wr - 0.1))
        parts.append(tim_part(pd, grain_axis=1))
    hub = L.lathe([(0.0, -0.2), (0.075, -0.19), (0.075, 0.19), (0.0, 0.2)], 7, mat, repeat=1.4)[0]
    hub.rot(rx=90)
    hub.uv = np.stack([-hub.uv[..., 1], hub.uv[..., 0]], axis=-1) * np.array([0.5, 1.0])
    hub.cell = "timber"
    parts.append(hub)
    for p in parts:
        p.move(*wc)
        p.node = "waterwheel"
        A.add(p)
    # the axle on two forked posts (static)
    ax = L.lathe([(0.0, -0.42), (0.04, -0.41), (0.04, 0.41), (0.0, 0.42)], 6, mat, repeat=1.4)[0]
    ax.rot(rx=90).move(*wc)
    ax.uv = np.stack([-ax.uv[..., 1], ax.uv[..., 0]], axis=-1) * np.array([0.5, 1.0])
    ax.cell = "timber"
    A.add(ax)
    for dy in (-0.36, 0.36):
        for lp in pole(mat, (wc[0], wc[1] + dy, -0.05), (wc[0], wc[1] + dy, wc[2] + 0.04), 0.05, 0.045, sides=5,
                       seed=int(dy * 10)):
            lp.uv = lp.uv / 2.0
            lp.cell = "bark"
            A.add(lp)
        for sx in (-1, 1):
            for lp in pole(mat, (wc[0], wc[1] + dy, wc[2] - 0.03), (wc[0] + sx * 0.09, wc[1] + dy, wc[2] + 0.12), 0.025,
                           0.02, sides=4, seed=int(dy * 10) + sx):
                lp.uv = lp.uv / 2.0
                lp.cell = "bark"
                A.add(lp)
    # grass and flower tufts on the bank (lush, SWAY)
    for k in range(12):
        a = k * 2 * math.pi / 12 + rng.uniform(-0.15, 0.15)
        if math.sin(a) < -0.6 or (math.cos(a) > 0.7 and abs(math.sin(a)) < 0.4):
            continue                                            # not under the source rock or the wheel
        rr = 1.9 + rng.uniform(-0.05, 0.08)
        cell = [3, 3, 1, 3, 0, 3, 2, 3, 1, 3, 0, 3][k]
        for j in range(2):
            c = L.card(0.55, 0.45, meadow, cell_rect(cell), segs=(1, 1), pivot="bottom")
            c.rot(rx=rng.uniform(-10, 10)).rot(rz=math.degrees(a) + 90 * j + rng.uniform(-20, 20))
            c.move(pc[0] + math.cos(a) * rr * 1.05, pc[1] + math.sin(a) * rr * 0.93, 0.1)
            c.v[:, :2] = np.clip(c.v[:, :2], -2.0, 2.0)
            c.nmode = "up"
            c.ao = False
            c.ao_fn = lambda q_: 0.6 + 0.4 * np.clip((q_.v[:, 2] - 0.1) / 0.45, 0, 1)
            c.sway = np.clip((c.v[:, 2] - 0.1) / 0.45, 0, 1)
            c.phase = rng.uniform(0, 1)
            A.add(c)
    for p in A.parts:
        p.v[:, :2] = np.clip(p.v[:, :2], -2.0, 2.0)
    A.extras = {"pool_radius": 1.7, "aura_radius": 7.8,
                "blocking_rect_godot": [-1.4, 0.7, 2.0, 2.0],
                "walkable": "the pool and the bank are walkable shallow water; only the source rock at the back "
                            "(blocking_rect_godot: x0, z0, x1, z1) and the wheel posts should block"}
    return A


def build_gold_mine_collapsed(aid):
    """Empty Gold Seam (neutrals §5.2 'the footprint becomes walkable rubble: a ground decal with small
    non-blocking rocks'): a scree-and-dirt ground skirt over the whole 6 x 6 m pad (<= 0.25 m), a few small
    rocks and broken timbers round the edges, the tipped headframe (A-frame and wheel) lying flat along the
    back edge, outside the walkable centre. Replaces gold_mine at the same position and facing."""
    seed = seed_of(aid)
    rng = np.random.default_rng(seed)
    A = Asset(aid, seed, ao_dist=0.5, base_dark=0.8, base_h=0.15, top_light=0.1)
    cells = [
        L.Cell("tailings", tex_tailings(), "tile", (224, 224), (1.75, 1.75)),
        L.Cell("ledge", tex_ledge(), "tile", (224, 224), (1.75, 1.75)),
        L.Cell("dirt", _swatch_crop(TEX + "gv_dirt.png", 0.5, 256, s_cap=0.4, key="col"), "tile", (224, 224), (1.75, 1.75)),
    ]
    ra = L.Atlas("gold_mine_collapsed_rock", cells, 512)
    rock = ra.mat("rock", extras={"cells_px_per_m": ra.density_report()})
    ta = timber_atlas("gold_mine_timber")
    tim = ta.mat("timber", emissive=False, extras={"cells_px_per_m": ta.density_report()})
    # ground skirt: a 24 x 24 grid, a low rubble swell in the middle (the fallen adit), dipping under the
    # terrain at the pad edge; scree where it swells, packed dirt toward the edge
    n = 24
    xs = np.linspace(-3.0, 3.0, n + 1)
    X, Y = np.meshgrid(xs, xs)
    q = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], axis=1)
    nz = L.noise1(q, 0.9, (seed % 17 * 0.3, 2.0, 5.0)).reshape(X.shape)
    nz2 = L.noise1(q, 2.6, (4.0, seed % 13 * 0.4, 1.0)).reshape(X.shape)
    r = (np.abs(X) ** 3.5 + np.abs(Y) ** 3.5) ** (1 / 3.5) / 3.0 * (1 + 0.09 * nz)   # rounded, ragged outline
    edge = smoothstep(0.97, 0.8, r)
    swell = np.exp(-((X / 1.9) ** 2 + ((Y - 0.4) / 1.6) ** 2))
    Z = (0.05 + 0.12 * swell + 0.035 * nz + 0.02 * nz2) * edge - 0.03 * (1 - edge)
    V = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)
    tris = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            b, c, d = a + 1, a + n + 2, a + n + 1
            tris += [(a, b, c), (a, c, d)] if (i + j) % 2 == 0 else [(a, b, d), (b, c, d)]
    T = np.array(tris)
    T = T[V[T][..., 2].max(axis=1) > -0.005]
    g = Part(V, T, rock, None, 50.0)
    rock_uv(g, top="tailings", side="tailings", bottom="tailings", rep_top=1.75, up_thr=0.0)
    cen = g.v[g.t].mean(axis=1)
    rr = (np.abs(cen[:, 0]) ** 3.5 + np.abs(cen[:, 1]) ** 3.5) ** (1 / 3.5) / 3.0
    ncen = L.noise1(cen, 1.2, (1.0, 2.0, 3.0))
    dirt = (rr + 0.15 * ncen) > 0.72
    g.cell = np.where(dirt, "dirt", "tailings").astype(object)
    P = g.v[g.t]
    g.uv[dirt] = np.stack([P[dirt][..., 0], -P[dirt][..., 1]], axis=-1) / 1.75
    g.nmode = "up"
    g.ao = False
    g.ao_fn = lambda p_: 0.85 + 0.15 * np.clip(p_.v[:, 2] / 0.15, 0, 1)
    A.add(g)

    def hz(x, y):
        return float(np.interp(0, [0], [0])) + float(
            (0.05 + 0.12 * math.exp(-((x / 1.9) ** 2 + ((y - 0.4) / 1.6) ** 2)))
            * smoothstep(0.97, 0.8, (abs(x) ** 3.5 + abs(y) ** 3.5) ** (1 / 3.5) / 3.0))
    # small rocks and slabs, mostly round the edges (non-blocking: <= 0.2 m)
    for k in range(22):
        if k < 15:
            side = k % 4
            t = rng.uniform(-2.6, 2.6)
            x, y = [(t, 2.55), (t, -2.0), (-2.55, t), (2.55, t)][side]
            x, y = x + rng.uniform(-0.25, 0.25), y + rng.uniform(-0.25, 0.25)
        else:
            x, y = rng.uniform(-1.6, 1.6), rng.uniform(-1.2, 1.8)
        rad = rng.uniform(0.1, 0.22) if k < 15 else rng.uniform(0.08, 0.14)
        b = L.blob(rock, rad, scale=(1.0, 0.8, rng.uniform(0.45, 0.65)), seed=seed + 10 + k, sphere="uv", segs=(7, 4),
                   flat_top=0.8, flat_bottom=0.15, cuts=2, smooth=38)
        b.rot(rz=rng.uniform(0, 360)).move(np.clip(x, -2.85, 2.85), np.clip(y, -2.85, 2.85), hz(x, y) - 0.04)
        rock_uv(b, top="ledge", side="ledge", bottom="ledge", rep_top=1.75, off=(rng.uniform(0, 1), rng.uniform(0, 1)))
        A.add(moss_tint(b, 0.5, seed + k, patch=0.3))
    # broken adit timbers lying at the front edge and the sides
    for k, (p0, p1, w) in enumerate([((-1.9, 2.35), (-0.6, 2.7), 0.18), ((0.4, 2.55), (1.8, 2.3), 0.16),
                                     ((2.45, 0.9), (2.7, -0.6), 0.15), ((-2.5, 0.2), (-2.35, 1.6), 0.15)]):
        z0, z1 = hz(*p0) + w / 2 - 0.02, hz(*p1) + w / 2 - 0.02
        A.add(tbeam(tim, (p0[0], p0[1], z0), (p1[0], p1[1], z1), w, w * 0.9, seed=seed + 20 + k))
    # the tipped headframe lying flat along the back edge: two legs, the cross tie, the wheel on its side
    yb = -2.45
    for k, (x0, x1) in enumerate([(-2.6, 0.2), (-2.4, 0.5)]):
        y0 = yb - 0.25 + k * 0.5
        A.add(tbeam(tim, (x0, y0, 0.11), (x1, yb + 0.05, 0.11), 0.2, 0.18, seed=seed + 30 + k))
    A.add(tbeam(tim, (-1.6, yb - 0.4, 0.17), (-1.5, yb + 0.45, 0.17), 0.13, 0.11, seed=seed + 33))
    for p in spoked_wheel(tim, 0.85, w=0.11, spokes=8, rim_d=0.12, hub_r=0.15, seed=seed + 40):
        p.rot(rx=90)                                   # lying flat
        p.scale(1.0, 1.0, 0.9)
        p.move(1.65, yb + 0.05, 0.08)
        A.add(p)
    for p in A.parts:
        p.v[:, :2] = np.clip(p.v[:, :2], -2.99, 2.99)
        p.v[:, 2] = np.minimum(p.v[:, 2], 0.25)
    A.extras = {"walkable": True, "max_height_m": 0.25}
    return A


# =============================================================================================
# registry
# =============================================================================================

REGISTRY = {}


def asset(aid, out="doodads", category="doodad", footprint=None, blocks_sight=False, sway=False, lods=None,
          notes="", blocks_pathing=None):
    """footprint: (w, d) in 0.5 m pathing cells (the sim footprint = the mesh width), or None (decorative,
    walkable). blocks_pathing defaults to bool(footprint). Trees use the 2x2-cell tree grid of
    architecture.md §7."""
    def deco(fn):
        REGISTRY[aid] = dict(fn=fn, out=out, category=category, footprint=footprint, blocks_sight=blocks_sight,
                             sway=sway, lods=lods or [], notes=notes,
                             blocks_pathing=bool(footprint) if blocks_pathing is None else blocks_pathing)
        return fn
    return deco


TREE_NOTE = ("Tree-grid doodad: blocks 2x2 cells (1 m) of pathing and sight; harvestable (rules §4.2, 50 lumber); "
             "leaves a tree_stump when felled. Crown ~3-3.6 m across (2-3x the 1 m tree cell, so a 2 m lane cut along "
             "the view shows ground between crowns at the generator's density; crown top >= 4.5 m). Place with "
             "±15-20 % scale, random yaw, ±3° hue jitter (bible §6.4).")


LOD1_NOTE = ("Low LOD of {base}: LOD0's own leaf cards (same cluster centres, directions, sizes and atlas cells, 3 in "
             "5 kept) as 4-triangle fans through their LOD0 corners and centre, a 20-triangle hull per cluster, no thin "
             "branches: same outline and shading, no rescaling. Suggested switch: beyond ~60 m from the camera (the "
             "line-up 'lod' shot compares LOD0 and LOD1 at the 46 m maximum zoom-out).")
LOD2_NOTE = ("Impostor of {base}: 2 triangles carrying the LOD0 tree rendered from the RTS pitch (56 deg). Material "
             "extras billboard=fixed_y: set BaseMaterial3D.billboard_mode = BILLBOARD_FIXED_Y (keeps the authored "
             "tilt toward the camera). No sway. Suggested switch: beyond ~70 m (far map edge, minimap renders).")


@asset("tree_hill_oak", category="tree", footprint=(2, 2), blocks_sight=True, sway=True,
       lods=["tree_hill_oak_lod1", "tree_hill_oak_lod2"], notes=TREE_NOTE + " Default tree-wall species.")
def a_oak():
    return build_tree("tree_hill_oak", spec_oak(seed_of("tree_hill_oak")))


@asset("tree_hill_oak_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes=LOD1_NOTE.format(base="tree_hill_oak"))
def a_oak_lod():
    return build_tree("tree_hill_oak_lod1", spec_oak(seed_of("tree_hill_oak")), lod=1)


@asset("tree_hill_oak_lod2", category="tree_impostor", footprint=(2, 2), blocks_sight=True,
       notes=LOD2_NOTE.format(base="tree_hill_oak"))
def a_oak_lod2():
    return build_tree("tree_hill_oak_lod2", spec_oak(seed_of("tree_hill_oak")), lod=2)


@asset("tree_linden", category="tree", footprint=(2, 2), blocks_sight=True, sway=True,
       lods=["tree_linden_lod1", "tree_linden_lod2"],
       notes=TREE_NOTE + " Taller rounded cone with summer blossom; mix into tree lines near kingdom starts.")
def a_linden():
    return build_tree("tree_linden", spec_linden(seed_of("tree_linden")))


@asset("tree_linden_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes=LOD1_NOTE.format(base="tree_linden"))
def a_linden_lod():
    return build_tree("tree_linden_lod1", spec_linden(seed_of("tree_linden")), lod=1)


@asset("tree_linden_lod2", category="tree_impostor", footprint=(2, 2), blocks_sight=True,
       notes=LOD2_NOTE.format(base="tree_linden"))
def a_linden_lod2():
    return build_tree("tree_linden_lod2", spec_linden(seed_of("tree_linden")), lod=2)


@asset("tree_hazel", category="tree", footprint=(2, 2), blocks_sight=True, sway=True,
       lods=["tree_hazel_lod1", "tree_hazel_lod2"],
       notes=TREE_NOTE + " Tall coppice (crown top >= 4.5 m, tree-wall rule) that fills gaps inside tree lines "
                         "(harvestable like the others).")
def a_hazel():
    return build_tree("tree_hazel", spec_hazel(seed_of("tree_hazel")))


@asset("tree_hazel_lod1", category="tree_lod", footprint=(2, 2), blocks_sight=True, sway=True,
       notes=LOD1_NOTE.format(base="tree_hazel"))
def a_hazel_lod():
    return build_tree("tree_hazel_lod1", spec_hazel(seed_of("tree_hazel")), lod=1)


@asset("tree_hazel_lod2", category="tree_impostor", footprint=(2, 2), blocks_sight=True,
       notes=LOD2_NOTE.format(base="tree_hazel"))
def a_hazel_lod2():
    return build_tree("tree_hazel_lod2", spec_hazel(seed_of("tree_hazel")), lod=2)


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
       notes="2 m module on the tile centre line (X -1..1), 1.3 m with coping, sagging top line and bulging "
             "faces (ends at full height so modules join); _b / _c are other seeds: alternate them so long walls do "
             "not repeat. Blocks pathing, not sight.")
def a_wall_s():
    return build_wall_straight("wall_drystone_straight")


@asset("wall_drystone_straight_b", category="wall", footprint=(4, 2),
       notes="Second seed of wall_drystone_straight (same size and joins): alternate seeds along a long wall.")
def a_wall_s_b():
    return build_wall_straight("wall_drystone_straight_b")


@asset("wall_drystone_straight_c", category="wall", footprint=(4, 2),
       notes="Third seed of wall_drystone_straight (same size and joins).")
def a_wall_s_c():
    return build_wall_straight("wall_drystone_straight_c")


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


@asset("camp_lean_to", category="camp", footprint=(5, 4),
       notes="Sootcoat lean-to, 60 deg roof, open side to the front (-Z). Place it sideways in camps (yaw +-90: open "
             "side to +-X) so the RTS camera sees the roof slope; tools/kits/lineup.py does.")
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


@asset("gold_mine", out="neutral", category="neutral_building", footprint=(12, 12), blocks_sight=True,
       notes="Gold Seam (neutrals §5.2): 12x12 cells (6 m; the mesh fills x, z -3..3), adit on the -Z face; spawn "
             "facing the hall (src/main.gd) - every side is finished cliff with the gold band, so any yaw reads. "
             "Materials: gold_mine_rock_GLOW (rock atlas: strata band, turf, tailings, ledge, dark tunnel, soil; "
             "emission only on the gold seam / vein texels, factor 0: pulse it when a worker enters) and "
             "gold_mine_timber_LAMP (timber atlas: planks, iron, rope, painted water, gold-flecked riffles; emission "
             "only on the lantern glass, factor 0: lit at night). Node windlass_drum (wheel + axle, pivot on the "
             "axle) spins about its local Z axis (the axle runs front-back); node windlass_bucket moves along Y "
             "(scale the rope). No mine cart, no rails, no nugget heaps (neutrals §5.2 / §10.2).")
def a_mine():
    return build_gold_mine("gold_mine")


@asset("neutral_weighstall", out="neutral", category="neutral_building", footprint=(12, 12), blocks_sight=True,
       notes="Weighstall merchant (neutrals §5.3): 12x12 cells (6 m; side tables, the Rundlings' handcart and stores "
             "fill x, z -3..3), counter faces -Z (spawn with facing PI). Materials: timber_LAMP (timber atlas; only "
             "the lantern glass is emissive, factor 0: lit at night), cloth (atlas: awning stripes and valance at "
             "128 px/m, sacking, Rundling scales, jars) and brass (#B8913A ramp, highlight #D9B868). Nodes: "
             "balance_beam (pivot at the beam centre, rotate about local Z to tip) > balance_pan_l / balance_pan_r "
             "(pivots at the hanging points: counter-rotate so the pans hang plumb), shopkeeper (curled Rundling: "
             "breathe by scaling, uncurl on purchase is VFX/anim). The balance beam reaches ~7 m on a 0.5 m post "
             "(exempt from the height ratio).")
def a_shop():
    return build_weighstall("neutral_weighstall")


@asset("neutral_hale_spring", out="neutral", category="neutral_building", footprint=(8, 8), blocks_pathing=False,
       sway=True,
       notes="Hale Spring (neutrals §5.8): 8x8 cells (4 m; the mesh fills x, z -2..2); the pool and bank are walkable "
             "shallow water (blocks_pathing false), only the source rock at the back (extras.blocking_rect_godot) and "
             "the wheel posts should block. Front faces -Z. Materials: neutral_hale_spring_spring (atlas: moss, stone, "
             "bark, planks, painted water #5AA3A0, no glow) and the meadow_SWAY tufts. Node waterwheel (pivot on the "
             "axle) spins about its local Z axis (the axle runs front-back). Warm sparkles are VFX.")
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
        "path": "assets/models/" + ("doodads" if meta["out"] == "doodads" else "neutral") + "/" + aid + ".glb",
        "category": meta["category"],
        "size": [round(float(x), 3) for x in size],
        "aabb_min": [round(float(x), 3) for x in lo],
        "tris": A.exported_tris,
        "footprint_cells": list(meta["footprint"]) if meta["footprint"] else None,
        "blocks_pathing": bool(meta["blocks_pathing"]),
        "blocks_sight": bool(meta["blocks_sight"]),
        "sway": bool(meta["sway"]),
        "materials": [m.gltf_name(aid) for m in mats],
        "texel_density_px_per_m": {m.gltf_name(aid): (m.atlas.density_report() if m.atlas is not None
                                                       else round(m.size / m.repeat)) for m in mats
                                   if m.atlas is not None or (m.repeat and m.key not in (
                                       "leaves", "meadow", "cloth", "glyph", "lily", "mushroom", "reeds", "endgrain",
                                       "turnip", "impostor"))},
        "lods": meta["lods"],
        "nodes": nodes,
        "notes": meta["notes"],
    }
    if aid.endswith(("_lod1", "_lod2")):
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
            "footprint_cells": "footprint [x, z] in 0.5 m cells = the mesh width (bible §1.3: sim footprint and mesh "
                               "width are the same number); null = walkable decoration. blocks_pathing says whether "
                               "those cells block (false for the Hale Spring: walkable pool)",
            "vertex_colour": "COLOR_0 RGB on every material (foliage included) = painted AO / base darkening / moss "
                             "tint, multiplied into the albedo; A = 1. Every mesh starts with a hidden 1 mm dummy "
                             "triangle, so a plain GLTFDocument import sets vertex_color_use_as_albedo on every material "
                             "(Godot 4.7 skips a mesh's first primitive); the game loader should still set it explicitly "
                             "on every material whose meta 'extras'.vc_vertex_color == 'multiply' (all kit materials)",
            "sway_materials": "name contains SWAY: alpha scissor, double sided; sway weight in UV2.x (0 base -> 1 "
                              "tip), cluster phase in TEXCOORD_2.x (Godot CUSTOM0.x); shader "
                              "tools/kits/foliage_sway.gdshader adds the wind (a plain import renders them static)",
            "uv2": "x sway weight, y normalized height 0..1 (build_progress reveal: discard where UV2.y > progress)",
            "atlas_materials": "materials with extras.cells_px_per_m are atlases of tiled cells (triangles cut on the "
                               "repeat lines at export): texel density per cell",
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
    ap.add_argument("--check", action="store_true",
                    help="build into a temp dir and compare byte-for-byte with the files on disk (exit 1 if stale)")
    args = ap.parse_args(L_argv())
    if args.list:
        for k, m in REGISTRY.items():
            print(f"{k:32s} {m['out']:8s} {m['category']}")
        return
    ids = list(REGISTRY)
    if args.only:
        want = [w.strip() for w in args.only.split(",") if w.strip()]
        ids = [i for i in ids if any(i == w or (w.endswith("*") and i.startswith(w[:-1])) for w in want)]
    if args.check:
        return check(ids)
    entries = []
    for aid in ids:
        entries.append(build_one(aid))
    mpath = write_manifest(entries)
    print(json.dumps({"built": [e["id"] for e in entries], "manifest": os.path.relpath(mpath, REPO),
                      "tris": {e["id"]: e["tris"] for e in entries}}, indent=1))


def check(ids):
    """Rebuild `ids` (and the manifest) into a temp copy and report every output that differs from disk."""
    import filecmp
    import shutil
    import tempfile
    global OUT_DOODADS, OUT_NEUTRAL
    real = (OUT_DOODADS, OUT_NEUTRAL)
    tmp = tempfile.mkdtemp(prefix="vc_doodads_check_")
    OUT_DOODADS, OUT_NEUTRAL = os.path.join(tmp, "doodads"), os.path.join(tmp, "neutral")
    os.makedirs(OUT_DOODADS)
    os.makedirs(OUT_NEUTRAL)
    if os.path.exists(os.path.join(real[0], "manifest.json")):
        shutil.copy(os.path.join(real[0], "manifest.json"), os.path.join(OUT_DOODADS, "manifest.json"))
    entries = [build_one(aid) for aid in ids]
    write_manifest(entries)
    stale = []
    for e in entries:
        rel = e["path"]
        built = os.path.join(OUT_DOODADS if REGISTRY[e["id"]]["out"] == "doodads" else OUT_NEUTRAL, os.path.basename(rel))
        disk = os.path.join(REPO, rel)
        if not os.path.exists(disk) or not filecmp.cmp(built, disk, shallow=False):
            stale.append(rel)
    if not filecmp.cmp(os.path.join(OUT_DOODADS, "manifest.json"), os.path.join(real[0], "manifest.json"), shallow=False):
        stale.append(os.path.relpath(os.path.join(real[0], "manifest.json"), REPO))
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"checked": len(ids), "stale": stale}, indent=1))
    sys.exit(1 if stale else 0)


def L_argv():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:]


if __name__ == "__main__":
    main()
