#!/usr/bin/env python3
"""Procedural building kit for the two slice factions (bpy, no paid generation).

    /opt/bpyenv/v313/bin/python tools/kits/buildings.py                  # every building
    /opt/bpyenv/v313/bin/python tools/kits/buildings.py --only kingdom_croft,clans_home_yurt
    /opt/bpyenv/v313/bin/python tools/kits/buildings.py --sheets tests/output/buildings \
        --lineup tests/output/buildings_lineup.png                       # + contact sheets / line-up

Writes assets/models/buildings/<id>.glb (+ manifest.json). Every [SLICE] building of `kingdom`
and `clans` except the two AI-modelled halls; the T2 hall upgrades (`kingdom_walled_burg`,
`clans_banner_shell`) are ADD-ON meshes in the hall GLB's own space: place them under the same
parent with the same transform as the T1 hall model and show both.

Conventions (tools/README.md): metres, origin at the footprint centre on the ground, the door faces
-Z in Godot (+Y in the build space used here), footprint = faction-doc cells x 0.5 m, heights per
art bible 1.3 (10-cell fallback column). One opaque atlas material + <id>_GLOW + <id>_TEAM.
Vertex colour = painted AO; UV2.y = normalized height for the build_progress reveal; UV2.x =
build layer (0 structure / lattice, 1 covering / felt) for the clans two-pass "Raising" reveal.
Deterministic: seeded per building id; identical inputs give byte-identical files.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402,F401  (initialises bmesh / mathutils)
import buildings_lib as L  # noqa: E402
from buildings_lib import Swatch, Part, hexcol, nrm, lerp  # noqa: E402

REPO = L.REPO
MAT = "assets_src/textures/materials/"
TER = "assets/textures/terrain/"

# =============================================================================================
# swatches
# =============================================================================================

KPAL = ["#EDE2C8", "#C9B994", "#7B1E2E", "#6E4A26", "#B07F3E", "#3D4046", "#7E848C", "#5A3A22",
        "#C9A85A", "#7E9A4A", "#F4F1EA", "#26221F", "#C8502A", "#2A2220", "#5F7A43", "#9A8F7C"]
CPAL = ["#1E5A60", "#2F7E7E", "#E0A030", "#B7772A", "#A8743A", "#D9A55E", "#5FA08E", "#7A4A32",
        "#E9DDBF", "#1C2230", "#6F7C88", "#4E2E20", "#3D4046", "#2A2220", "#C9A46A", "#8A6A44"]


def kingdom_swatches():
    return {
        "plaster": Swatch("plaster", L.swatch_img(MAT + "kingdom_lime_plaster.png", "crossfade"), 3.0),
        "oak": Swatch("oak", L.swatch_img(MAT + "kingdom_dark_oak_beam.png", "crossfade"), 2.2),
        "roof": Swatch("roof", L.swatch_img(MAT + "kingdom_burgundy_roof_tiles.png", "period"), 2.6),
        "rubble": Swatch("rubble", L.swatch_img(MAT + "kingdom_rubble_stone.png", "crossfade"), 2.4),
        "scales": Swatch("scales", L.swatch_img(MAT + "kingdom_bronze_scale_roof.png", "period", sat=0.75,
                                                tint=(0.95, 1.0, 1.02), gamma=0.9), 1.4),
        "planks": Swatch("planks", L.swatch_img(MAT + "kingdom_painted_planks.png", "periodx"), 1.5),
        "iron": Swatch("iron", L.tex_iron(), 1.0),
        "brick": Swatch("brick", L.tex_brick(), 1.3),
        "straw": Swatch("straw", L.tex_straw(), 1.0),
        "bark": Swatch("bark", L.swatch_img(TER + "bark_oak.png", "none"), 1.2),
        "rings": Swatch("rings", L.tex_rings(), kind="decal"),
        "wattle": Swatch("wattle", L.tex_wattle(), 0.75),
        "leaves": Swatch("leaves", L.tex_leaves(), 1.6),
        "dirt": Swatch("dirt", L.swatch_img(TER + "gv_dirt.png", "none"), 3.0),
        "pal": Swatch("pal", L.tex_palette(KPAL), kind="decal"),
        "team": Swatch("team", L.tex_team_cloth(emblem="wheel"), kind="decal", group="team"),
        "team_plain": Swatch("team_plain", L.tex_team_cloth(seed=33), kind="decal", group="team"),
        "team_band": Swatch("team_band", L.tex_team_band(), 0.8, group="team"),
        "window": Swatch("window", L.tex_window(), kind="decal", group="glow"),
        "ember": Swatch("ember", L.tex_ember(), kind="decal", group="glow"),
    }


def clans_swatches():
    teal = L.swatch_img(MAT + "clans_teal_felt.png", "period")
    saffron = L.swatch_img(MAT + "clans_saffron_felt.png", "period", tint=(0.92, 0.84, 0.74), sat=0.85)
    return {
        "teal": Swatch("teal", teal, 2.4),
        "saffron": Swatch("saffron", saffron, 1.0),
        "stripes": Swatch("stripes", L.tex_stripes(teal, saffron, stripes=4), 2.4),
        "lattice": Swatch("lattice", L.swatch_img(MAT + "clans_lattice_wood.png", "period"), 1.4),
        "shell": Swatch("shell", L.swatch_img(MAT + "clans_tortoise_shell.png", "crossfade"), 2.6),
        "bronze": Swatch("bronze", L.swatch_img(MAT + "clans_polished_bronze.png", "period"), 1.4),
        "wood": Swatch("wood", L.swatch_img(MAT + "kingdom_dark_oak_beam.png", "crossfade",
                                            tint=(1.32, 0.98, 0.86)), 2.0),
        "stone": Swatch("stone", L.tex_stone(), 1.6),
        "glyph": Swatch("glyph", L.tex_glyph_stone(), kind="decal"),
        "drystone": Swatch("drystone", L.swatch_img(MAT + "neutral_drystone.png", "crossfade"), 2.0),
        "clay": Swatch("clay", L.swatch_img(TER + "gv_cracked.png", "none"), 2.0),
        "dirt": Swatch("dirt", L.swatch_img(TER + "gv_dirt.png", "none"), 3.0),
        "bark": Swatch("bark", L.swatch_img(TER + "bark_oak.png", "none"), 1.2),
        "rings": Swatch("rings", L.tex_rings(), kind="decal"),
        "iron": Swatch("iron", L.tex_iron(), 1.0),
        "pal": Swatch("pal", L.tex_palette(CPAL), kind="decal"),
        "team": Swatch("team", L.tex_team_cloth(emblem="gong"), kind="decal", group="team"),
        "team_plain": Swatch("team_plain", L.tex_team_cloth(seed=33), kind="decal", group="team"),
        "team_band": Swatch("team_band", L.tex_team_band(), 0.8, group="team"),
        "ember": Swatch("ember", L.tex_ember(), kind="decal", group="glow"),
    }


# per-swatch defaults: (dice max edge m, jitter amplitude m, smoothing angle deg)
DEFAULTS = {
    "plaster": (None, 0.012, 30), "rubble": (None, 0.03, 40), "roof": (0.4, 0.02, 40),
    "oak": (None, 0.006, 25), "planks": (None, 0.006, 25), "scales": (None, 0.0, 60), "brick": (None, 0.012, 30),
    "iron": (None, 0.0, 35), "straw": (0.3, 0.03, 50), "bark": (0.5, 0.0, 50), "rings": (None, 0.0, 10),
    "wattle": (0.4, 0.008, 30), "leaves": (0.3, 0.0, 60), "dirt": (0.4, 0.0, 40), "pal": (None, 0.0, 35),
    "team": (0.3, 0.0, 40), "team_plain": (0.3, 0.0, 40), "team_band": (0.3, 0.0, 40),
    "window": (None, 0.0, 0), "ember": (None, 0.0, 30),
    "teal": (0.3, 0.012, 60), "saffron": (0.3, 0.012, 60), "stripes": (0.3, 0.012, 60),
    "lattice": (0.35, 0.004, 40), "shell": (0.35, 0.0, 60), "bronze": (0.35, 0.0, 50),
    "wood": (0.6, 0.006, 25), "stone": (0.3, 0.0, 40), "glyph": (0.3, 0.0, 40), "drystone": (0.3, 0.025, 40),
    "clay": (0.3, 0.02, 50),
}


class Ctx:
    """Assembly context of one building."""

    def __init__(self, aid, faction, fp_cells, scale=1.0):
        self.aid = aid
        self.faction = faction
        self.seed = L.seed_of(aid)
        self.rng = np.random.default_rng(self.seed)
        self.S = kingdom_swatches() if faction == "kingdom" else clans_swatches()
        self.pal = KPAL if faction == "kingdom" else CPAL
        self.fp = (fp_cells[0] * 0.5 * scale, fp_cells[1] * 0.5 * scale)
        self.k = scale
        self.parts: list[Part] = []
        self.notes = []
        self.bake = L.Bake()

    def sw(self, key):
        return self.S[key]

    def add(self, p, **kw):
        if isinstance(p, (list, tuple)):
            return [self.add(q, **kw) for q in p]
        d = DEFAULTS.get(p.sw.key, (None, 0.0, 35))
        if "dice" not in kw:
            p.dice = d[0]
        if "jit" not in kw:
            p.jit = d[1]
        p.set(**kw)
        self.parts.append(p)
        return p

    def r(self, a=0.0, b=1.0):
        return float(self.rng.uniform(a, b))

    # palette helpers -----------------------------------------------------------------------
    def pal_uv(self, p, name):
        u, v = L.palette_uv(self.pal, name)
        p.uv = np.zeros_like(p.uv)
        p.uv[..., 0] = u
        p.uv[..., 1] = v
        return p

    def P(self, p, name, **kw):
        """Add a part painted with one flat palette colour."""
        p.sw = self.S["pal"]
        self.pal_uv(p, name)
        return self.add(p, **kw)


# =============================================================================================
# generic helpers: wall frames
# =============================================================================================

class Wall:
    """A vertical wall plane: origin O (2D), along-direction e (2D), outward normal n (2D)."""

    def __init__(self, O, e, n, length):
        self.O = np.asarray(O, float)
        self.e = np.asarray(e, float)
        self.n = np.asarray(n, float)
        self.L = float(length)

    def p(self, s, z, d=0.0):
        q = self.O + self.e * s + self.n * d
        return np.array([q[0], q[1], z])

    def frame(self):
        """3x3 matrix mapping local (s, z, d) -> world xyz directions."""
        return np.stack([np.array([self.e[0], self.e[1], 0.0]), np.array([0.0, 0.0, 1.0]),
                         np.array([self.n[0], self.n[1], 0.0])], axis=1)

    def place(self, part, s=0.0, z=0.0, d=0.0):
        """Map a part built in local (x=s, y=z, z=d) into the wall."""
        part.xf(self.frame())
        return part.move(*self.p(s, z, d))


def rect_walls(x0, x1, y0, y1):
    """Front (+y), right (+x), back (-y), left (-x) walls, each seen from outside left->right."""
    return {
        "front": Wall((x1, y1), (-1, 0), (0, 1), x1 - x0),
        "right": Wall((x1, y0), (0, 1), (1, 0), y1 - y0),
        "back": Wall((x0, y0), (1, 0), (0, -1), x1 - x0),
        "left": Wall((x0, y1), (0, -1), (-1, 0), y1 - y0),
    }


def wall_prism(c, wall, outline_sz, d0, d1, key, chamfer=0.02, grid=0.42, **kw):
    """Polygon in the wall's (s, z) plane extruded from offset d0 to d1 (outward); the big faces are
    gridded (AO resolution)."""
    p = L.prism(outline_sz, d0, d1, c.sw(key), chamfer=chamfer, grid=grid)
    # prism is built with local z = extrusion; map local (x, y, z) = (s, z, d)
    wall.place(p)
    return c.add(p, **kw)


# =============================================================================================
# kingdom modules
# =============================================================================================

def plinth(c, x0, x1, y0, y1, h, key="rubble", batter=0.05, chamfer=0.06, z0=0.0, **kw):
    """Battered rubble-stone base."""
    ol = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], float)
    p = L.prism(ol, z0, z0 + h, c.sw(key), chamfer=chamfer, grid=0.4, bottom=False)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    top = p.v[:, 2] > z0 + h * 0.5
    p.v[top, 0] = cx + (p.v[top, 0] - cx) * (1 - batter)
    p.v[top, 1] = cy + (p.v[top, 1] - cy) * (1 - batter)
    p.box_uv()
    return c.add(p, **kw)


def timber_wall(c, wall, z0, z1, t, openings=(), bay=0.75, braces=True, rail=True, key="oak", depth=None,
                corner=True):
    """Half-timber frame on a wall: sill, plate, corner posts, studs, rail, braces, around
    openings. openings: [(s_centre, width, z_bottom, z_top, kind)] kind in window / door / blank."""
    dep = depth or t * 0.8
    off = dep / 2 - 0.015
    Lw = wall.L
    rng = c.rng
    sw = c.sw(key)

    def mem(s0, z_0, s1, z_1, w=t, d=dep, o=off):
        p = L.member(wall.p(s0, z_0, o), wall.p(s1, z_1, o), w, d, sw, rng=rng,
                     roll_up=(wall.n[0], wall.n[1], 0.0))
        # small hand-made irregularity
        p.rot_axis((wall.n[0], wall.n[1], 0.0), c.r(-1.2, 1.2), pivot=p.v.mean(0))
        return c.add(p)

    H = z1 - z0
    mem(0, z0 + t / 2, Lw, z0 + t / 2, w=t * 1.1, d=dep * 1.05)          # sill
    mem(0, z1 - t / 2, Lw, z1 - t / 2, w=t * 1.05)                       # plate
    if corner:
        for s in (t * 0.5, Lw - t * 0.5):
            mem(s, z0, s, z1, w=t * 1.15, d=dep * 1.1)
    nb = max(1, int(round((Lw - t) / bay)))
    edges = np.linspace(t * 0.5, Lw - t * 0.5, nb + 1)
    zr = z0 + H * 0.42
    ops = list(openings)
    for b in range(nb):
        sa, sb = edges[b], edges[b + 1]
        if 0 < b:
            # stud unless an opening covers this edge
            if not any(abs(o[0] - sa) < o[1] / 2 + t * 0.3 for o in ops):
                mem(sa, z0 + t, sa, z1 - t, w=t * 0.9)
        cen = (sa + sb) / 2
        here = [o for o in ops if sa - 1e-6 <= o[0] <= sb + 1e-6]
        if here:
            continue
        if braces:
            if b == 0:
                mem(sa + t * 0.4, zr, sb - t * 0.3, z1 - t, w=t * 0.85)
                mem(sa + t * 0.4, z0 + t, sb - t * 0.3, zr, w=t * 0.85)
            elif b == nb - 1:
                mem(sb - t * 0.4, zr, sa + t * 0.3, z1 - t, w=t * 0.85)
                mem(sb - t * 0.4, z0 + t, sa + t * 0.3, zr, w=t * 0.85)
            elif rail:
                mem(sa + t * 0.4, z0 + t, sb - t * 0.4, z1 - t, w=t * 0.8)
                mem(sb - t * 0.4, z0 + t, sa + t * 0.4, z1 - t, w=t * 0.8)
    for (s, w, zb, zt, kind) in ops:
        a, b2 = s - w / 2 - t / 2, s + w / 2 + t / 2
        mem(a, z0 + t, a, z1 - t, w=t)
        mem(b2, z0 + t, b2, z1 - t, w=t)
        if kind != "door":
            mem(a, zb - t / 2, b2, zb - t / 2, w=t * 0.95, d=dep * 1.25, o=off + 0.02)   # window sill
        if zt < z1 - t * 1.5:
            mem(a, zt + t / 2, b2, zt + t / 2, w=t * 1.05)                              # lintel
            if kind == "door":
                mem(a, zt + t, s, z1 - t, w=t * 0.8)
                mem(b2, zt + t, s, z1 - t, w=t * 0.8)
    return edges


def window(c, wall, s, zb, zt, w, shutters=True, open_deg=158.0, recess=0.0):
    h = zt - zb
    q = L.quad(wall.p(s + w / 2, zb, 0.012 - recess), wall.p(s - w / 2, zb, 0.012 - recess),
               wall.p(s - w / 2, zt, 0.012 - recess), wall.p(s + w / 2, zt, 0.012 - recess), c.sw("window"))
    # wall.e points to the viewer's left of an outside observer looking at the wall? use winding check
    q = _face_out(q, wall)
    c.add(q, ao=False, occ=False, min_shade=1.0, form=0.0)
    if shutters:
        sw_ = w / 2 + 0.02
        for side in (-1, 1):
            hinge = s + side * (w / 2 + 0.01)
            p = L.box(sw_, h * 1.02, 0.03, c.sw("team_plain"))
            p.uv = _uv_rect(p, sw_, h)
            # local: x along wall (s), y up (z), z out (d)
            p.move(side * sw_ / 2, h / 2, 0.0)
            p.rot(0, side * -(180 - open_deg), 0)
            p.move(0, 0, 0.03)
            wall.place(p, hinge, zb, 0.0)
            c.add(p)
            # painted plank lines: two thin dark battens
            for zz in (0.25, 0.75):
                bt = L.box(sw_ * 0.9, 0.035, 0.012, c.sw("pal"))
                bt.move(side * sw_ / 2, h * zz, 0.0).rot(0, side * -(180 - open_deg), 0).move(0, 0, 0.05)
                wall.place(bt, hinge, zb, 0.0)
                c.P(bt, "#26221F")


def _uv_rect(p, w, h):
    """Decal UVs for a box built at the origin: map x,y extents to [0,1] (front/back faces)."""
    v = p.v[p.t]
    u = (v[..., 0] + w / 2) / w
    vv = 1.0 - (v[..., 1] + h / 2) / h
    return np.stack([np.clip(u, 0, 1), np.clip(vv, 0, 1)], -1)


def _face_out(q, wall):
    fnrm = np.cross(q.v[q.t[0, 1]] - q.v[q.t[0, 0]], q.v[q.t[0, 2]] - q.v[q.t[0, 0]])
    if fnrm[0] * wall.n[0] + fnrm[1] * wall.n[1] < 0:
        q.t = q.t[:, ::-1]
        q.uv = q.uv[:, ::-1]
    return q


def door(c, wall, s, zb, w, h, key="planks", arch=False):
    """Plank door set into the wall, iron straps, a step."""
    th = 0.06
    p = L.box(w, h, th, c.sw(key), chamfer=0.01)
    p.move(0, h / 2, 0)
    wall.place(p, s, zb, 0.0)
    c.add(p, dice=0.25, uvrot=True)
    for zz in (0.22, 0.75):
        strap = L.box(w * 0.85, 0.045, 0.02, c.sw("iron"))
        strap.move(w * 0.04, h * zz, th / 2 + 0.01)
        wall.place(strap, s, zb, 0.0)
        c.add(strap)
    ring = L.torus(0.045, 0.012, c.sw("iron"), segs=8, sides=4).rot(90, 0, 0)
    ring.move(-w * 0.3, h * 0.48, th / 2 + 0.03)
    wall.place(ring, s, zb, 0.0)
    c.add(ring)
    step = L.box(w * 1.3, 0.12, 0.28, c.sw("rubble"), chamfer=0.03)
    step.move(0, 0.06, 0.14)
    wall.place(step, s, 0.0, 0.0)
    c.add(step, jit=0.01)


def gable_roof(c, x0, x1, yc, half, z_eave, z_ridge, th=0.12, sag=0.04, flare=0.12, kick=0.05, nu=10, nv=6,
               key="roof", ridge_team=True, soffit=True, barge=True, t=0.1, ridge_key="team_band",
               axis="x", cx=0.0):
    """Thick gable roof, ridge along x from x0..x1 (incl. overhang) at y = yc; eaves at yc +- half.
    axis='y' builds it rotated (ridge along y, about the vertical axis through (cx, yc))."""
    sw = c.sw(key)
    rep = sw.repeat
    Lx = x1 - x0
    xm = (x0 + x1) / 2
    top_v, top_t, top_uv = [], [], []
    grids = []
    for side in (1, -1):
        base = len(top_v)
        for j in range(nv + 1):
            f = j / nv
            for i in range(nu + 1):
                x = x0 + Lx * i / nu
                xr = 2 * (x - xm) / Lx
                zf = f + flare * f * (1 - f)
                z = z_ridge - (z_ridge - z_eave) * zf
                z += -sag * (1 - xr * xr) * (1 - f * 0.6)
                z += kick * (xr ** 4) * f * f
                y = yc + side * half * f
                top_v.append((x, y, z))
        grids.append(base)
    top_v = np.array(top_v, float)
    slope_len = math.hypot(half, z_ridge - z_eave)
    parts = []
    # top surfaces
    for gi, side in enumerate((1, -1)):
        base = grids[gi]
        tris, uvs = [], []
        for j in range(nv):
            for i in range(nu):
                a = base + j * (nu + 1) + i
                b, cc, d = a + 1, a + nu + 2, a + nu + 1
                tri1, tri2 = (a, b, cc), (a, cc, d)
                if side < 0:
                    tri1, tri2 = (a, cc, b), (a, d, cc)
                for tri in (tri1, tri2):
                    tris.append(tri)
                    uvs.append([((top_v[k][0] - x0) / rep * side, (slope_len * ((k - base) // (nu + 1)) / nv) / rep)
                                for k in tri])
        parts.append(Part(top_v, np.array(tris), sw, np.array(uvs), 40.0))
    roof_top = L.merge(parts)
    # thickness: bottom = top - th (vertical), border strips on eaves and gable edges
    bot = top_v - np.array([0, 0, th])
    rimparts = []
    for gi, side in enumerate((1, -1)):
        base = grids[gi]
        eave = [base + nv * (nu + 1) + i for i in range(nu + 1)]
        g0 = [base + j * (nu + 1) for j in range(nv + 1)]
        g1 = [base + j * (nu + 1) + nu for j in range(nv + 1)]
        for chain in (eave, g0, g1):
            for k in range(len(chain) - 1):
                a, b = chain[k], chain[k + 1]
                q = L.quad(bot[a], bot[b], top_v[b], top_v[a], sw, uv=((0, 0.1), (0.3, 0.1), (0.3, 0), (0, 0)))
                # orient outward: away from the roof centre
                mid = (top_v[a] + top_v[b]) / 2
                out = mid - np.array([xm, yc, mid[2]])
                out[2] = 0
                fnrm = np.cross(q.v[1] - q.v[0], q.v[3] - q.v[0])
                if np.dot(fnrm, out) < 0:
                    q.t = q.t[:, ::-1]
                    q.uv = q.uv[:, ::-1]
                rimparts.append(q)
    rim = L.merge(rimparts)
    rim.box_uv(0.6)
    rim.tint = hexcol("#8A6A60")
    out = [c.add(roof_top, layer=1.0), c.add(rim, dice=None, layer=1.0)]
    if soffit:
        st, su = [], []
        for gi, side in enumerate((1, -1)):
            base = grids[gi]
            for j in range(nv):
                for i in range(nu):
                    a = base + j * (nu + 1) + i
                    b, cc, d = a + 1, a + nu + 2, a + nu + 1
                    tri1, tri2 = (a, cc, b), (a, d, cc)
                    if side < 0:
                        tri1, tri2 = (a, b, cc), (a, cc, d)
                    st += [tri1, tri2]
        sp = Part(bot, np.array(st), c.sw("oak"), None, 30.0)
        sp.box_uv(1.2)
        out.append(c.add(sp, dice=0.5, layer=1.0, ao_mul=1.0, form=0.0))
    if ridge_team:
        xs = np.linspace(x0 - 0.02, x1 + 0.02, nu + 1)
        path = []
        for x in xs:
            xr = 2 * (x - xm) / Lx
            path.append((x, yc, z_ridge - sag * (1 - xr * xr) + 0.015))
        w = max(0.12, t * 1.4)
        prof = np.array([(w * 0.3, w * 0.62), (0.0, w * 0.55), (-w * 0.5, 0.0), (0.0, -w * 0.55),
                         (w * 0.3, -w * 0.62)])
        rp = L.sweep(prof, path, c.sw(ridge_key), up=(0, 1, 0))
        normalize_v(rp)
        # band texture: u along ridge (tile), v across (0..1)
        out.append(c.add(rp, layer=1.0))
    if barge:
        for xe in (x0 + t * 0.4, x1 - t * 0.4):
            xr = 2 * (xe - xm) / Lx
            zr = z_ridge - sag * (1 - xr * xr) + kick * 0
            for side in (1, -1):
                pts = []
                for j in range(nv + 1):
                    f = j / nv
                    zf = f + flare * f * (1 - f)
                    z = z_ridge - (z_ridge - z_eave) * zf - sag * (1 - xr * xr) * (1 - f * 0.6) + kick * xr ** 4 * f * f
                    pts.append((xe, yc + side * half * f, z + t * 0.25))
                for k in range(0, nv, 2):
                    a, b = pts[k], pts[min(k + 2, nv)]
                    out.append(c.add(L.member(a, b, t * 0.9, t * 1.2, c.sw("oak"), rng=c.rng, roll_up=(1, 0, 0))))
    if axis == "y":
        for p in out:
            p.v = p.v - np.array([cx, yc, 0])
            p.rot(0, 0, 90)
            p.v = p.v + np.array([cx, yc, 0])
    return out


def gable_infill(c, wall, z0, z_apex, t, key="plaster", infill=True, timbers=True, window_w=0.0):
    """Triangle above a wall (plaster + king post, collar and braces)."""
    Lw = wall.L
    if infill:
        ol = [(0.0, z0), (Lw, z0), (Lw / 2, z_apex)]
        wall_prism(c, wall, ol, -0.05, 0.0, key, chamfer=0.0)
    if timbers:
        dep = t * 0.8
        o = dep / 2 - 0.015
        sw = c.sw("oak")
        zc = z0 + (z_apex - z0) * 0.45

        def mem(s0, a, s1, b, w=t):
            c.add(L.member(wall.p(s0, a, o), wall.p(s1, b, o), w, dep, sw, rng=c.rng,
                           roll_up=(wall.n[0], wall.n[1], 0)))
        mem(Lw / 2, z0, Lw / 2, z_apex - t * 0.6)
        half = (Lw / 2) * (1 - (zc - z0) / (z_apex - z0))
        mem(Lw / 2 - half + t * 0.3, zc, Lw / 2 + half - t * 0.3, zc, w=t * 0.9)
        mem(Lw * 0.5 - t * 0.4, z0 + t * 0.4, Lw * 0.2, zc - t * 0.3, w=t * 0.8)
        mem(Lw * 0.5 + t * 0.4, z0 + t * 0.4, Lw * 0.8, zc - t * 0.3, w=t * 0.8)
        if window_w > 0:
            zb = zc + t * 0.8
            zt = zb + window_w * 0.9
            if zt < z_apex - t * 1.5:
                window(c, wall, Lw / 2, zb, zt, window_w, shutters=False)


def chimney(c, x, y, z0, z1, w, key="rubble", cap=True):
    p = L.gbox(w, w, z1 - z0, c.sw(key), center=(x, y, z0), chamfer=0.03, grid=0.35)
    top = p.v[:, 2] > (z0 + z1) / 2
    p.v[top, 0] = x + (p.v[top, 0] - x) * 0.88
    p.v[top, 1] = y + (p.v[top, 1] - y) * 0.88
    p.box_uv()
    c.add(p)
    if cap:
        cp = L.box(w * 1.12, w * 1.12, 0.07, c.sw(key), center=(x, y, z1), base=True, chamfer=0.02)
        c.add(cp)
        pot = L.lathe([(w * 0.22, z1 + 0.07), (w * 0.2, z1 + 0.22), (w * 0.24, z1 + 0.25), (w * 0.17, z1 + 0.25)],
                      8, c.sw("brick"))
        pot.move(x, y, 0)
        c.add(pot, dice=None)


def normalize_v(p):
    """Map a sweep's v (around the profile) to [0, 1] so a band texture spans it once."""
    v = p.uv[..., 1]
    lo, hi = v.min(), v.max()
    p.uv[..., 1] = (v - lo) / max(hi - lo, 1e-9)
    return p


def wheel(c, center, r, axis="x", spokes=6, width=None, key="oak", iron=None, hub_r=None, rim_w=None, segs=None):
    """Spoked wagon wheel in the plane perpendicular to `axis` (low poly: square rim profile)."""
    w = width or r * 0.16
    rim_w = rim_w or r * 0.14
    segs = segs or (12 if r < 0.5 else 16)
    iron = (r >= 0.5) if iron is None else iron
    parts = []
    ang = np.arange(segs) * 2 * math.pi / segs
    path = np.stack([np.cos(ang) * (r - rim_w / 2), np.sin(ang) * (r - rim_w / 2), np.zeros(segs)], 1)
    rim = L.sweep(L.rect_profile(rim_w, w), path, c.sw(key), closed_path=True)
    if not iron:
        rim.tint = np.where(np.linalg.norm(rim.v[:, :2], axis=1)[:, None] > r - rim_w * 0.3, 0.55, 1.0) * np.ones((1, 3))
    parts.append(rim)
    if iron:
        tyre = L.sweep(L.rect_profile(rim_w * 0.3, w * 1.05),
                       np.stack([np.cos(ang) * (r - rim_w * 0.12), np.sin(ang) * (r - rim_w * 0.12), np.zeros(segs)], 1),
                       c.sw("iron"), closed_path=True)
        parts.append(tyre)
    hr = hub_r or r * 0.2
    hub = L.lathe([(0, -w * 1.1), (hr * 0.7, -w * 1.1), (hr, -w * 0.4), (hr, w * 0.4), (hr * 0.7, w * 1.1), (0, w * 1.1)],
                  6, c.sw("iron" if key == "iron" else "oak"))
    parts.append(hub)
    for k in range(spokes):
        a = k * 2 * math.pi / spokes + math.pi / spokes
        d = np.array([math.cos(a), math.sin(a), 0.0])
        parts.append(L.member(d * hr * 0.8, d * (r - rim_w * 0.8), w * 0.42, w * 0.55, c.sw(key), rng=c.rng))
    for p in parts:
        if axis == "x":
            p.rot(0, 90, 0)
        elif axis == "y":
            p.rot(90, 0, 0)
        p.move(*center)
    for p in parts:
        c.add(p, dice=None, jit=0.0)
    return parts


def pennant(c, base, pole_h, flag_len, flag_w, dirn=(1, 0), pole_r=None, swallow=True, key="team", phase=0.0,
            finial=True, pole_key="oak"):
    """Pole with a swallow-tailed team pennant flying along dirn (2D)."""
    pr = pole_r or max(0.025, flag_w * 0.09)
    base = np.asarray(base, float)
    top = base + np.array([0, 0, pole_h])
    pole = L.lathe([(pr * 1.2, 0), (pr, 0.05), (pr * 0.8, pole_h)], 6, c.sw(pole_key))
    pole.move(*base)
    c.add(pole, dice=None, uvrot=True)
    if finial:
        ball = L.lathe([(0, 0), (pr * 1.6, pr * 0.8), (pr * 1.7, pr * 1.8), (pr * 0.8, pr * 3.0), (0, pr * 3.8)], 8,
                       c.sw("iron"))
        ball.move(*top)
        c.add(ball, dice=None)
    flag(c, top - np.array([0, 0, pr * 0.5 + flag_w]), flag_len, flag_w, dirn, swallow, key, phase)


def flag(c, attach_bottom, length, width, dirn=(1, 0), swallow=True, key="team", phase=0.0, droop=0.15,
         amp=None, thick=0.012):
    """Flag cloth attached along a vertical edge [attach_bottom, +width], flying along dirn."""
    nu, nv = 10, 3
    notch = 0.38 if swallow else 0.0
    amp = amp if amp is not None else width * 0.12
    d2 = nrm(np.array([dirn[0], dirn[1]], float))
    d = np.array([d2[0], d2[1], 0.0])
    side = np.array([-d2[1], d2[0], 0.0])
    verts, uvs = [], []
    for j in range(nv + 1):
        b = j / nv
        for i in range(nu + 1):
            a = i / nu
            L_ = length * a
            # swallow notch: centre row shorter
            if swallow:
                cut = notch * (1 - abs(2 * b - 1))
                L_ = length * a * (1 - cut * a)
            z = width * b - droop * width * a * a
            wv = math.sin(a * 5.0 + phase) * amp * a
            verts.append(attach_bottom + d * L_ + side * wv + np.array([0, 0, z]))
            uvs.append((a, 1 - b))
    verts, uvs = np.array(verts), np.array(uvs)
    tris = []
    for j in range(nv):
        for i in range(nu):
            a0 = j * (nu + 1) + i
            tris += [(a0, a0 + 1, a0 + nu + 2), (a0, a0 + nu + 2, a0 + nu + 1)]
    tris = np.array(tris)
    front = Part(verts + side * thick / 2, tris[:, ::-1], c.sw(key), uvs[tris][:, ::-1], 50.0)
    back = Part(verts - side * thick / 2, tris, c.sw(key), uvs[tris], 50.0)
    f = L.merge([front, back])
    c.add(f, dice=None, jit=0.0, form=0.0)
    return f


def banner(c, top_center, width, height, normal=(0, 1), key="team", tails=True, bar=True):
    """Hanging banner on a crossbar, facing `normal` (2D)."""
    n2 = nrm(np.array(normal, float))
    n = np.array([n2[0], n2[1], 0.0])
    e = np.array([-n2[1], n2[0], 0.0])
    tc = np.asarray(top_center, float)
    nu, nv = 3, 6
    verts, uvs = [], []
    for j in range(nv + 1):
        b = j / nv
        for i in range(nu + 1):
            a = i / nu
            z = -height * b
            if tails and j == nv:
                z += height * 0.12 * (1 - abs(2 * a - 1))
            fold = math.sin(a * math.pi * 2 + b * 1.5) * 0.02 * width
            verts.append(tc + e * (a - 0.5) * width + n * (fold + 0.01 * b) + np.array([0, 0, z]))
            uvs.append((a, b))
    verts, uvs = np.array(verts), np.array(uvs)
    tris = []
    for j in range(nv):
        for i in range(nu):
            a0 = j * (nu + 1) + i
            tris += [(a0, a0 + nu + 2, a0 + 1), (a0, a0 + nu + 1, a0 + nu + 2)]
    tris = np.array(tris)
    th = 0.012
    front = Part(verts + n * th, tris, c.sw(key), uvs[tris], 40.0)
    back = Part(verts - n * th, tris[:, ::-1], c.sw(key), uvs[tris][:, ::-1], 40.0)
    c.add(L.merge([front, back]), dice=None, form=0.0)
    if bar:
        c.add(L.member(tc - e * width * 0.6 + n * 0.01 + np.array([0, 0, 0.02]),
                       tc + e * width * 0.6 + n * 0.01 + np.array([0, 0, 0.02]), 0.045, 0.045, c.sw("oak"), rng=c.rng))


def onion_dome(c, center, r, h, key="scales", team_ring=True, finial_h=None, sides=16, repeat=None, ribs=0,
               tint=(1.0, 1.0, 1.0)):
    """Bronze onion dome (base radius r at center z, total height h without finial)."""
    x, y, z = center
    prof = [(r * 0.98, 0.0), (r * 1.14, h * 0.1), (r * 1.24, h * 0.24), (r * 1.18, h * 0.38),
            (r * 0.9, h * 0.54), (r * 0.5, h * 0.7), (r * 0.22, h * 0.83), (r * 0.09, h * 0.93), (0.0, h)]
    d = L.lathe(prof, sides, c.sw(key), smooth=70.0, vscale=1.0, repeat=repeat)
    d.move(x, y, z)
    c.add(d, dice=None, layer=1.0, tint=tint)
    for k in range(ribs):
        a = k * 2 * math.pi / ribs
        pts = [(x + math.cos(a) * (pr + 0.012), y + math.sin(a) * (pr + 0.012), z + pz) for pr, pz in prof[:-1]]
        rib = L.sweep(L.rect_profile(max(0.03, r * 0.06), max(0.025, r * 0.05)), np.array(pts), c.sw("iron"), up=(0, 0, 1))
        c.add(rib, dice=None, layer=1.0, tint=(1.1, 1.0, 0.85))
    if team_ring:
        ring = L.lathe([(r * 1.04, -0.10 * r - 0.04), (r * 1.08, -0.02), (r * 1.04, 0.06 * r + 0.04)], sides,
                       c.sw("team_band"), int_repeat=True)
        ring.uv[..., 1] = np.where(ring.v[ring.t][..., 2] > 0, 0.0, 1.0)
        ring.move(x, y, z)
        c.add(ring, dice=None, layer=1.0)
    fh = finial_h if finial_h is not None else h * 0.6
    spike = L.lathe([(r * 0.08, 0), (r * 0.05, fh * 0.6), (r * 0.03, fh)], 6, c.sw("iron"))
    spike.move(x, y, z + h * 0.95)
    c.add(spike, dice=None)
    wr = max(0.12, r * 0.32)
    wheel(c, (x, y, z + h * 0.95 + fh * 0.55), wr, axis="y", spokes=6, key="iron", iron=False,
          width=wr * 0.18, rim_w=wr * 0.2)


def stork_nest(c, pos, r=0.32, stork=True, facing=0.0):
    x, y, z = pos
    nest = L.lathe([(r * 0.55, 0), (r * 0.95, r * 0.12), (r * 1.05, r * 0.35), (r * 0.8, r * 0.45),
                    (r * 0.5, r * 0.3), (0, r * 0.28)], 12, c.sw("straw"))
    nest.move(x, y, z)
    c.add(nest, jit=0.03, dice=0.12)
    # twigs sticking out
    for k in range(9):
        a = k * 2 * math.pi / 9 + c.r(0, 0.5)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        p0 = np.array(pos) + d * r * 0.7 + np.array([0, 0, r * 0.3])
        p1 = p0 + d * r * 0.55 + np.array([0, 0, c.r(-0.05, 0.12)])
        c.P(L.member(p0, p1, 0.025, 0.025, c.sw("pal"), rng=c.rng), "#5A3A22")
    if stork:
        s = r * 1.3
        bz = z + r * 0.4
        body = L.blob(c.sw("pal"), radius=s * 0.5, subdiv=1, scale=(1.0, 0.6, 0.55), seed=3, noise_amp=0.02)
        body.move(x, y, bz + s * 0.15)
        c.P(body, "#F4F1EA")
        wing = L.blob(c.sw("pal"), radius=s * 0.42, subdiv=1, scale=(1.05, 0.66, 0.35), seed=4, noise_amp=0.02)
        wing.move(x - s * 0.08, y, bz + s * 0.3)
        c.P(wing, "#26221F")
        neck = L.member((x + s * 0.35, y, bz + s * 0.3), (x + s * 0.5, y, bz + s * 0.85), s * 0.1, s * 0.1, c.sw("pal"))
        c.P(neck, "#F4F1EA")
        head = L.blob(c.sw("pal"), radius=s * 0.11, subdiv=1, seed=5, noise_amp=0.0)
        head.move(x + s * 0.52, y, bz + s * 0.8)
        c.P(head, "#F4F1EA")
        bill = L.member((x + s * 0.58, y, bz + s * 0.88), (x + s * 0.98, y, bz + s * 0.76), s * 0.06, s * 0.05,
                        c.sw("pal"))
        c.P(bill, "#C8502A")
        for p in (body, wing, neck, head, bill):
            p.rot(0, 0, facing, pivot=(x, y, z))


def barrel(c, pos, r=0.2, h=0.45, key="oak"):
    x, y, z = pos
    prof = [(r * 0.85, 0), (r, h * 0.3), (r * 1.04, h * 0.5), (r, h * 0.7), (r * 0.85, h)]
    b = L.lathe(prof, 10, c.sw(key), cap_top=True)
    b.move(x, y, z)
    c.add(b, dice=None, uvrot=True)
    for zz in (0.12, 0.88):
        hoop = L.torus(r * (0.9 + 0.08 * (1 - abs(zz - 0.5) * 2)) + 0.005, 0.014, c.sw("iron"), segs=12, sides=4)
        hoop.move(x, y, z + h * zz)
        c.add(hoop, dice=None)


def crate(c, pos, s=0.35, rz=0.0):
    p = L.box(s, s, s, c.sw("planks"), chamfer=0.02)
    p.move(0, 0, s / 2).rot(0, 0, rz).move(*pos)
    c.add(p, dice=None)


def log_stack(c, center, length, rows, r=0.12, axis="x", key_bark="bark", rz=0.0):
    """Pyramid stack of logs with ring ends."""
    x, y, z = center
    k = 0
    for row in range(rows):
        n = rows - row
        for i in range(n):
            off = (i - (n - 1) / 2) * r * 2.02
            zz = z + r + row * r * 1.75
            rr = r * (0.88 + 0.22 * c.r())
            L_ = length * (0.92 + 0.12 * c.r())
            bark = L.lathe([(rr, -L_ / 2), (rr * 1.02, 0), (rr, L_ / 2)], 9, c.sw(key_bark), a0=c.r(0, 1))
            bark.rot(0, 90, 0)
            ends = []
            for sgn in (-1, 1):
                ang = np.arange(9) * 2 * math.pi / 9
                ring = np.stack([np.cos(ang) * rr * 0.98, np.sin(ang) * rr * 0.98, np.zeros(9)], 1)
                vv = np.vstack([ring, [[0, 0, 0]]])
                tt = np.array([(9, j, (j + 1) % 9) for j in range(9)])
                uv = np.stack([0.5 + vv[..., 0] / (2 * rr), 0.5 - vv[..., 1] / (2 * rr)], -1)[tt]
                e = Part(vv, tt, c.sw("rings"), uv, 0.0)
                e.rot(0, 90 * sgn, 0).move(sgn * L_ / 2, 0, 0)
                ends.append(e)
            for p in [bark] + ends:
                p.move(0, off, zz - z)
                p.rot(0, 0, rz)
                if axis == "y":
                    p.rot(0, 0, 90)
                p.move(x, y, z)
                c.add(p, dice=None, jit=0.0)
            k += 1


def fence_wattle(c, p0, p1, h=0.5, key="wattle"):
    p0 = np.array([p0[0], p0[1], p0[2] if len(p0) > 2 else 0.0], float)
    p1 = np.array([p1[0], p1[1], p1[2] if len(p1) > 2 else 0.0], float)
    d = p1 - p0
    Lf = float(np.linalg.norm(d[:2]))
    e = d / max(Lf, 1e-9)
    n = np.array([-e[1], e[0], 0])
    panel = L.plate(p0 + n * 0.02, p1 + n * 0.02, p1 + n * 0.02 + np.array([0, 0, h]), p0 + n * 0.02 + np.array([0, 0, h]),
                    0.04, c.sw(key))
    panel.box_uv()
    c.add(panel, dice=0.3)
    ns = max(2, int(round(Lf / 0.6)) + 1)
    for i in range(ns):
        q = p0 + d * i / (ns - 1)
        c.add(L.member(q, q + np.array([0, 0, h + 0.1]), 0.05, 0.05, c.sw("oak"), rng=c.rng))


def sapling(c, pos, h=1.6, r=0.45, key="leaves"):
    """Chunky lollipop linden: trunk + two lumpy canopy blobs."""
    x, y, z = pos
    tr = L.lathe([(0.07, 0), (0.05, h * 0.5), (0.04, h * 0.75)], 6, c.sw("bark"))
    tr.move(x, y, z)
    c.add(tr, dice=None, uvrot=True)
    for k, (dz, rr, dx) in enumerate(((h * 0.62, r, 0.0), (h * 0.85, r * 0.75, r * 0.15))):
        b = L.blob(c.sw(key), radius=rr, subdiv=2, scale=(1, 1, 0.85), seed=int(c.r(0, 1e6)), noise_amp=0.18,
                   noise_freq=1.6)
        b.move(x + dx, y, z + dz - rr * 0.6)
        c.add(b, dice=None, smooth=70.0)


def roof_solid(c, verts, faces, th, key="roof", deform=None, dice=0.4, soffit=True, rim_tint="#8A6A60",
               layer=1.0):
    """Thick roof from top-surface polygons (CCW seen from above). Each face gets its own UV frame
    (u along its eave, v down the slope). deform(v) -> v is applied after tessellation."""
    sw = c.sw(key)
    rep = sw.repeat
    V = np.asarray(verts, float)
    tris, uvs = [], []
    for f in faces:
        P = V[f]
        lo = np.argsort(P[:, 2])[:2]
        e = P[lo[1]] - P[lo[0]]
        e[2] = 0
        if np.linalg.norm(e) < 1e-6:
            e = P[1] - P[0]
            e[2] = 0
        e = nrm(e)
        n = nrm(np.cross(P[1] - P[0], P[2] - P[0]))
        d = nrm(np.cross(n, e))
        if d[2] > 0:
            d = -d
        ztop = P[np.argmax(P[:, 2])]
        for k in range(1, len(f) - 1):
            tri = (f[0], f[k], f[k + 1])
            tris.append(tri)
            uvs.append([(np.dot(V[i] - ztop, e) / rep, np.dot(V[i] - ztop, d) / rep) for i in tri])
    top = Part(V.copy(), np.array(tris), sw, np.array(uvs), 40.0)
    if dice:
        L.refine(top, dice)
    if deform is not None:
        top.v = deform(top.v)
    # boundary edges
    e2 = {}
    for tri in top.t:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            k = (min(a, b), max(a, b))
            e2[k] = e2.get(k, 0) + 1
    bnd = []
    for tri in top.t:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if e2[(min(a, b), max(a, b))] == 1:
                bnd.append((a, b))
    bot_v = top.v - np.array([0, 0, th])
    out = [c.add(top, dice=None, layer=layer)]
    rim = []
    for a, b in bnd:
        # top edge a->b is CCW on the top face: outward side quad = (bot a, bot b, top b, top a) reversed
        q = L.quad(bot_v[a], bot_v[b], top.v[b], top.v[a], sw)
        rim.append(q)
    if rim:
        r = L.merge(rim)
        r.box_uv(0.6)
        r.tint = hexcol(rim_tint)
        out.append(c.add(r, dice=None, layer=layer))
    if soffit:
        sp = Part(bot_v, top.t[:, ::-1].copy(), c.sw("oak"), None, 30.0)
        sp.box_uv(1.2)
        out.append(c.add(sp, dice=None, layer=layer, form=0.0))
    return out


def hip_roof(c, x0, x1, y0, y1, z_eave, z_top, ridge_frac=0.45, th=0.12, sag=0.04, kick=0.07, key="roof",
             dice=0.4, ridge_team=True, finials=True, hips=True, hip_w=0.16):
    """Hip roof over [x0,x1]x[y0,y1] (eaves incl. overhang); ridge along the longer axis with length
    ridge_frac * (long - short), or a pyramid when ridge_frac == 0."""
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    along_x = hx >= hy
    rl = ridge_frac * abs(hx - hy) if ridge_frac > 0 else 0.0
    if rl > 1e-3:
        if along_x:
            r0, r1 = (xc - rl, yc, z_top), (xc + rl, yc, z_top)
        else:
            r0, r1 = (xc, yc - rl, z_top), (xc, yc + rl, z_top)
        V = [(x0, y0, z_eave), (x1, y0, z_eave), (x1, y1, z_eave), (x0, y1, z_eave), r0, r1]
        if along_x:
            faces = [[0, 1, 5, 4], [2, 3, 4, 5], [1, 2, 5], [3, 0, 4]]
        else:
            faces = [[1, 2, 5, 4], [3, 0, 4, 5], [0, 1, 4], [2, 3, 5]]
    else:
        V = [(x0, y0, z_eave), (x1, y0, z_eave), (x1, y1, z_eave), (x0, y1, z_eave), (xc, yc, z_top)]
        faces = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]

    def deform(v):
        xn = (v[:, 0] - xc) / hx
        yn = (v[:, 1] - yc) / hy
        v = v.copy()
        hgt = np.clip((v[:, 2] - z_eave) / max(z_top - z_eave, 1e-6), 0, 1)
        v[:, 2] += kick * (np.abs(xn) * np.abs(yn)) ** 3
        v[:, 2] -= sag * (1 - np.minimum(np.abs(xn), 1) ** 2) * hgt if along_x else sag * (1 - np.minimum(np.abs(yn), 1) ** 2) * hgt
        # concave flare: drop the middle of each slope a little
        v[:, 2] -= 0.06 * (z_top - z_eave) * hgt * (1 - hgt) * 4 * 0.5
        return v

    out = roof_solid(c, V, faces, th, key, deform, dice)
    if ridge_team:
        w = hip_w
        prof = np.array([(w * 0.3, w * 0.62), (0.0, w * 0.55), (-w * 0.5, 0.0), (0.0, -w * 0.55), (w * 0.3, -w * 0.62)])
        lines = []
        if rl > 1e-3:
            lines.append((np.array(r0, float), np.array(r1, float)))
            ends = [(np.array(r0, float), [V[0], V[3]] if along_x else [V[0], V[1]]),
                    (np.array(r1, float), [V[1], V[2]] if along_x else [V[2], V[3]])]
        else:
            ends = [(np.array((xc, yc, z_top), float), [V[0], V[1], V[2], V[3]])]
        if hips:
            for top, corners in ends:
                for cr in corners:
                    lines.append((top, np.array(cr, float)))
        for a, b in lines:
            n = 8
            pts = np.array([a + (b - a) * i / n for i in range(n + 1)])
            pts = deform(pts) + np.array([0, 0, 0.012])
            d = b - a
            upv = nrm(np.cross(np.cross(d, [0, 0, 1.0]), d))
            side = nrm(np.cross(d, upv))
            rp = L.sweep(prof, pts, c.sw("team_band"), up=tuple(side))
            normalize_v(rp)
            out.append(c.add(rp, layer=1.0))
    if finials:
        tops = [r0, r1] if rl > 1e-3 else [(xc, yc, z_top)]
        for tp in tops:
            sp = L.lathe([(0.05, -0.05), (0.05, 0.08), (0.075, 0.14), (0.0, 0.32)], 6, c.sw("iron"))
            sp.move(tp[0], tp[1], tp[2])
            out.append(c.add(sp, dice=None))
    return out


def stepped_gable(c, wall, z0, z_apex, steps=3, th=0.22, key="plaster", coping="rubble", rise=0.22, d0=-0.05):
    """Crow-stepped gable wall standing proud of a roof whose ridge meets this wall at z_apex
    (the roof line runs straight from z0 at both wall ends to z_apex in the middle)."""
    Lw = wall.L
    sw_ = Lw / (2 * steps + 1)
    zs = [z0 + (z_apex - z0) * min(1.0, (i + 1) * sw_ / (Lw / 2)) + rise for i in range(steps)]
    ztop = z_apex + rise * 1.6
    ol = [(0.0, z0)]
    for i in range(steps):
        ol += [(i * sw_, zs[i]), ((i + 1) * sw_, zs[i])]
    ol += [(steps * sw_, ztop), (Lw - steps * sw_, ztop)]
    for i in range(steps - 1, -1, -1):
        ol += [(Lw - (i + 1) * sw_, zs[i]), (Lw - i * sw_, zs[i])]
    ol += [(Lw, z0)]
    clean = []
    for q in ol:
        if not clean or abs(clean[-1][0] - q[0]) + abs(clean[-1][1] - q[1]) > 1e-6:
            clean.append(q)
    wall_prism(c, wall, clean, d0, d0 + th, key, chamfer=0.02)
    tops = [(i * sw_, (i + 1) * sw_, zs[i]) for i in range(steps)]
    tops += [(steps * sw_, Lw - steps * sw_, ztop)]
    tops += [(Lw - (i + 1) * sw_, Lw - i * sw_, zs[i]) for i in range(steps)]
    for a, b, z in tops:
        p = L.box(b - a + 0.06, 0.07, th + 0.08, c.sw(coping), chamfer=0.015)
        p.move((a + b) / 2, z + 0.035, d0 + th / 2)
        wall.place(p)
        c.add(p, dice=None, jit=0.004)
    return ztop + 0.07


def tower_frame(c, z_top, base_half, top_half, levels=2, t=0.12, key="oak", footing=True):
    """Four splayed posts with X braces (scout tower legs)."""
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    posts = []
    for sx, sy in corners:
        a = np.array([sx * base_half, sy * base_half, 0.0])
        b = np.array([sx * top_half, sy * top_half, z_top])
        posts.append((a, b))
        c.add(L.member(a, b + np.array([0, 0, 0.1]), t, t, c.sw(key), rng=c.rng, chamfer=0.02))
        if footing:
            f = L.box(t * 2.2, t * 2.2, 0.22, c.sw("rubble"), center=(a[0], a[1], 0), base=True, chamfer=0.03)
            c.add(f, dice=None, jit=0.01)
    zl = np.linspace(0.35, z_top - 0.1, levels + 1)
    for i in range(4):
        (a0, b0), (a1, b1) = posts[i], posts[(i + 1) % 4]

        def at(a, b, z):
            return a + (b - a) * (z / z_top)
        for k in range(levels):
            za, zb = zl[k], zl[k + 1]
            p00, p01 = at(a0, b0, za), at(a0, b0, zb)
            p10, p11 = at(a1, b1, za), at(a1, b1, zb)
            out = nrm(((p00 + p10) / 2)[:2])
            o = np.array([out[0], out[1], 0]) * t * 0.55
            c.add(L.member(p00 + o, p11 + o, t * 0.7, t * 0.6, c.sw(key), rng=c.rng))
            c.add(L.member(p10 + o * 1.4, p01 + o * 1.4, t * 0.7, t * 0.6, c.sw(key), rng=c.rng))
            c.add(L.member(p01 + o, p11 + o, t * 0.8, t * 0.7, c.sw(key), rng=c.rng))
    return posts


def ladder(c, p0, p1, w=0.36, t=0.05, key="oak"):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    side = nrm(np.cross(d, [0, 0, 1]))
    for sgn in (-1, 1):
        c.add(L.member(p0 + side * sgn * w / 2, p1 + side * sgn * w / 2, t, t, c.sw(key), rng=c.rng))
    n = int(np.linalg.norm(d) / 0.32)
    for i in range(1, n):
        q = p0 + d * i / n
        c.add(L.member(q - side * w / 2, q + side * w / 2, t * 0.6, t * 0.6, c.sw(key), rng=c.rng))


def platform(c, cx, cy, z, half, th=0.1, rail_h=0.5, rail=True, key="planks", t=0.08):
    p = L.box(half * 2, half * 2, th, c.sw(key), center=(cx, cy, z), base=True, chamfer=0.02)
    c.add(p, dice=0.5)
    if rail:
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            q = np.array([cx + sx * (half - t / 2), cy + sy * (half - t / 2), z + th])
            c.add(L.member(q, q + np.array([0, 0, rail_h]), t, t, c.sw("oak"), rng=c.rng))
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            for zz in (rail_h * 0.5, rail_h):
                a = np.array([cx + ax * (half - t / 2), cy + ay * (half - t / 2), z + th + zz])
                b = np.array([cx + bx * (half - t / 2), cy + by * (half - t / 2), z + th + zz])
                c.add(L.member(a, b, t * 0.8, t * 0.8, c.sw("oak"), rng=c.rng))


def pavise(c, pos, facing_deg, h=1.0, w=0.5, lean=8.0):
    """Tall flat round-topped shield standing on its foot: team face field with an ivory wheel
    (TEAM decal), dark oak back."""
    x, y, z = pos
    th = 0.05
    n = 10
    ol = [(-w / 2, 0.0), (w / 2, 0.0)]
    for i in range(n + 1):
        a = i / n * math.pi
        ol.append((math.cos(a) * w / 2, h - w * 0.3 + math.sin(a) * w * 0.3))
    ol = ol[:2] + ol[2:]
    face = L.prism(np.array(ol[1:] + ol[:1]), 0.0, 0.012, c.sw("team"), chamfer=0.0, bottom=False)
    v = face.v[face.t]
    face.uv = np.stack([(v[..., 0] + w / 2) / w, 1 - v[..., 1] / h], -1)
    back = L.prism(np.array(ol[1:] + ol[:1]), -th, 0.0, c.sw("oak"), chamfer=0.01)
    ridge = L.box(0.06, h * 0.92, 0.04, c.sw("oak"), center=(0, h * 0.46, 0.03))
    for p in (face, back, ridge):
        # local: x across, y up, z out -> world: rotate so y->z
        p.rot(90 - lean, 0, 0).rot(0, 0, facing_deg + 180.0).move(x, y, z)
    c.add(face, dice=None)
    c.add(back, dice=None)
    c.add(ridge, dice=None)


def weapon_rack(c, center, rz=0.0, width=1.2, h=1.1, n=4):
    x, y, z = center
    parts = []
    for sx in (-1, 1):
        parts.append(L.member((sx * width / 2, 0, 0), (sx * width / 2, 0, h), 0.08, 0.08, c.sw("oak"), rng=c.rng))
        parts.append(L.member((sx * width / 2, -0.2, 0), (sx * width / 2, 0.0, h * 0.5), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    parts.append(L.member((-width / 2, 0, h * 0.85), (width / 2, 0, h * 0.85), 0.07, 0.07, c.sw("oak"), rng=c.rng))
    parts.append(L.member((-width / 2, 0, h * 0.3), (width / 2, 0, h * 0.3), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    for p in parts:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p)
    for i in range(n):
        u = (i + 0.5) / n - 0.5
        lean = 0.12
        a = np.array([u * width * 0.9, 0.12, 0.05])
        b = np.array([u * width * 0.9 + 0.05, -lean, h * 1.45])
        shaft = L.member(a, b, 0.04, 0.04, c.sw("oak"), rng=c.rng)
        shaft.rot(0, 0, rz).move(x, y, z)
        c.add(shaft)
        # head: flail beater / falchion blade / pole hook alternating
        if i % 2 == 0:
            head = L.member(b, b + np.array([0.0, 0.08, -0.38]), 0.07, 0.07, c.sw("iron"))
        else:
            head = L.box(0.05, 0.16, 0.3, c.sw("iron"), center=b + np.array([0, -0.06, 0.12]))
        head.rot(0, 0, rz, pivot=(0, 0, 0)).move(x, y, z)
        c.add(head, dice=None)


def trestle(c, center, rz=0.0, w=0.7, h=0.75):
    x, y, z = center
    parts = [L.member((-w / 2, 0, h), (w / 2, 0, h), 0.09, 0.09, c.sw("oak"), rng=c.rng)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(L.member((sx * w * 0.42, 0, h), (sx * w * 0.5, sy * 0.22, 0), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    for p in parts:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p)


def anvil(c, pos, rz=0.0):
    x, y, z = pos
    stump = L.lathe([(0.2, 0), (0.18, 0.42), (0.17, 0.45), (0.0, 0.45)], 9, c.sw("bark"))
    stump.move(x, y, z)
    c.add(stump, dice=None, uvrot=True)
    top = L.box(0.42, 0.16, 0.12, c.sw("iron"), chamfer=0.02, center=(0, 0, 0.62))
    waist = L.box(0.18, 0.12, 0.12, c.sw("iron"), center=(0, 0, 0.51))
    foot = L.box(0.3, 0.18, 0.06, c.sw("iron"), center=(0, 0, 0.48))
    horn = L.lathe([(0.06, 0), (0.0, 0.2)], 6, c.sw("iron")).rot(0, 90, 0).move(0.2, 0, 0.62)
    for p in (top, waist, foot, horn):
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p, dice=None)


def drawer_chest(c, center, w=1.0, h=0.8, d=0.42, rz=0.0, cols=3, rows=3):
    """The Curio Cabinet sign: a giant painted chest of small drawers with brass knobs."""
    x, y, z = center
    parts = []
    body = L.box(w, d, h, c.sw("planks"), chamfer=0.03, center=(0, 0, h / 2))
    parts.append((body, None))
    top = L.box(w * 1.08, d * 1.1, 0.07, c.sw("oak"), chamfer=0.02, center=(0, 0, h + 0.035))
    parts.append((top, None))
    for sx in (-1, 1):
        leg = L.box(0.1, d * 0.9, 0.12, c.sw("oak"), center=(sx * (w / 2 - 0.08), 0, -0.04))
        parts.append((leg, None))
    cols_ = ["#EDE2C8", "#7B1E2E", "#C9B994", "#7E9A4A", "#C9A85A", "#EDE2C8"]
    gw, gh = w * 0.9 / cols, h * 0.86 / rows
    k = 0
    for r in range(rows):
        for q in range(cols):
            cx_ = -w * 0.45 + gw * (q + 0.5)
            cz = h * 0.07 + gh * (r + 0.5)
            fr = L.box(gw * 0.86, 0.05, gh * 0.8, c.sw("pal"), chamfer=0.012, center=(cx_, d / 2 + 0.01, cz))
            parts.append((fr, cols_[(k * 2 + r) % len(cols_)]))
            kn = L.lathe([(0, 0), (0.035, 0.01), (0.04, 0.04), (0.0, 0.07)], 6, c.sw("pal"))
            kn.rot(-90, 0, 0).move(cx_, d / 2 + 0.03, cz)
            parts.append((kn, "#B07F3E"))
            k += 1
    for p, col in parts:
        p.rot(0, 0, rz).move(x, y, z)
        if col:
            c.P(p, col, dice=None)
        else:
            c.add(p, dice=None)


def bell_cote(c, base, size=0.5, rz=0.0):
    """Small timber bell frame with a mini gable roof and a bronze bell."""
    x, y, z = base
    s = size
    parts = []
    for sx in (-1, 1):
        parts.append((L.member((sx * s * 0.4, 0, 0), (sx * s * 0.35, 0, s * 1.1), 0.07, 0.07, c.sw("oak")), None))
    parts.append((L.member((-s * 0.45, 0, s * 1.05), (s * 0.45, 0, s * 1.05), 0.07, 0.07, c.sw("oak")), None))
    bell = L.lathe([(0.0, 0.0), (s * 0.22, 0.0), (s * 0.24, s * 0.04), (s * 0.17, s * 0.15), (s * 0.15, s * 0.32),
                    (s * 0.08, s * 0.38), (0, s * 0.4)], 10, c.sw("scales"))
    bell.move(0, 0, s * 0.62)
    parts.append((bell, "bronze"))
    for p, kind in parts:
        p.rot(0, 0, rz).move(x, y, z)
        if kind == "bronze":
            c.P(p, "#B07F3E", dice=None)
        else:
            c.add(p, dice=None)
    gable_roof_small(c, (x, y, z + s * 1.08), s * 1.1, s * 0.75, s * 0.45, rz)


def gable_roof_small(c, base, length, span, rise, rz=0.0, key="roof", th=0.05):
    """Tiny gable roof (bell-cotes, dormers, porches): ridge along local x."""
    x, y, z = base
    hl, hs = length / 2, span / 2
    V = [(-hl, -hs, 0), (hl, -hs, 0), (hl, 0, rise), (-hl, 0, rise), (hl, hs, 0), (-hl, hs, 0)]
    faces = [[0, 1, 2, 3], [4, 5, 3, 2]]
    out = roof_solid(c, V, faces, th, key, None, dice=None, soffit=True)
    for p in out:
        p.rot(0, 0, rz).move(x, y, z)
    return out


def wagon(c, center, rz=0.0, length=1.6, width=0.8, h=0.55, wheel_r=0.38, cover=False, team_band=True,
          four=True, shafts=True):
    """Kingdom plank wagon: folk-painted box on spoked wheels; team band on the side boards."""
    x, y, z = center
    zb = wheel_r * 0.95
    local = []
    body = L.box(length, width, h, c.sw("planks"), chamfer=0.02, center=(0, 0, zb + h / 2))
    local.append(body)
    floor = L.box(length * 1.02, width * 0.96, 0.06, c.sw("oak"), center=(0, 0, zb))
    local.append(floor)
    for p in local:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p, dice=None)
    if team_band:
        for sy in (-1, 1):
            band = L.box(length * 0.92, 0.012, h * 0.22, c.sw("team_band"), center=(0, sy * (width / 2 + 0.008), zb + h * 0.62))
            v = band.v[band.t]
            band.uv = np.stack([v[..., 0] / 0.8, 1 - (v[..., 2] - (zb + h * 0.51)) / (h * 0.22)], -1)
            band.rot(0, 0, rz).move(x, y, z)
            c.add(band, dice=None)
    xs = (-length * 0.3, length * 0.3) if four else (0.0,)
    for wx in xs:
        for sy in (-1, 1):
            cc = np.array([wx, sy * (width / 2 + 0.07), wheel_r])
            R = np.array(L.rot_matrix(0, 0, rz))
            wc = R @ cc + np.array([x, y, z])
            for p in wheel(c, tuple(wc), wheel_r, axis="y", spokes=8):
                p.rot(0, 0, rz, pivot=wc)
    if shafts:
        for sy in (-1, 1):
            a = np.array([length / 2, sy * width * 0.3, zb + 0.05])
            b = np.array([length / 2 + 0.75, sy * width * 0.25, 0.12])
            p = L.member(a, b, 0.05, 0.05, c.sw("oak"), rng=c.rng)
            p.rot(0, 0, rz).move(x, y, z)
            c.add(p)
    if cover:
        prof = []
        for i in range(9):
            a = math.pi * i / 8
            prof.append((math.cos(a) * width * 0.52, math.sin(a) * width * 0.55))
        verts = []
        n = 6
        for j in range(n + 1):
            xx = -length * 0.42 + length * 0.84 * j / n
            for (py, pz) in prof:
                verts.append((xx, py, zb + h + pz))
        verts = np.array(verts)
        K = len(prof)
        tris, uvs = [], []
        for j in range(n):
            for i in range(K - 1):
                a, b = j * K + i, j * K + i + 1
                cc2, d = (j + 1) * K + i + 1, (j + 1) * K + i
                tris += [(a, b, cc2), (a, cc2, d)]
        tris = np.array(tris)
        cv = Part(verts, tris, c.sw("team_band"), None, 60)
        vv = cv.v[cv.t]
        ang = np.arctan2(vv[..., 2] - zb - h, vv[..., 1])
        cv.uv = np.stack([vv[..., 0] / 0.8, (ang / math.pi) * 3 % 1.0], -1)
        cv.rot(0, 0, rz).move(x, y, z)
        c.add(cv, dice=None)


# =============================================================================================
# kingdom buildings
# =============================================================================================

def house(c, x0, x1, y0, y1, zp, stories, t, ops=None, stone=(), jetty=0.0, plinth_pad=0.06, bay=0.62,
          shutters=True):
    """Half-timber house body. stories: storey top heights (absolute z). ops: {(wall, k): [(s_frac,
    width, zb_rel, zt_rel, kind)]} with kind window / door / blank. stone: storey indices built as
    rubble walls (no frame). jetty: upper storeys overhang front and back by this much each.
    Returns (walls of the top storey, (x0, x1, y0, y1) of the top storey)."""
    ops = ops or {}
    plinth(c, x0 - plinth_pad, x1 + plinth_pad, y0 - plinth_pad, y1 + plinth_pad, zp)
    zb = zp
    ext = 0.0
    walls = None
    for k, zt in enumerate(stories):
        bx0, bx1, by0, by1 = x0, x1, y0 - ext, y1 + ext
        walls = rect_walls(bx0, bx1, by0, by1)
        for name, w in walls.items():
            ol = [(0, zb), (w.L, zb), (w.L, zt), (0, zt)]
            if k in stone:
                wall_prism(c, w, ol, -0.08, 0.04, "rubble", chamfer=0.03)
            else:
                wall_prism(c, w, ol, -0.06, 0.0, "plaster", chamfer=0.0)
            o = [(f * w.L, ww, zb + a, zb + b_, kind) for (f, ww, a, b_, kind) in ops.get((name, k), [])]
            if k not in stone:
                timber_wall(c, w, zb, zt, t, o, bay=bay)
            for (s_, ww, za, zz, kind) in o:
                if kind == "window":
                    window(c, w, s_, za, zz, ww, shutters=shutters)
                    if k in stone:
                        c.add(L.member(w.p(s_ - ww / 2 - 0.06, zz + 0.05, 0.06), w.p(s_ + ww / 2 + 0.06, zz + 0.05, 0.06),
                                       0.1, 0.1, c.sw("oak"), rng=c.rng))
                        c.add(L.member(w.p(s_ - ww / 2 - 0.04, za - 0.04, 0.07), w.p(s_ + ww / 2 + 0.04, za - 0.04, 0.07),
                                       0.07, 0.12, c.sw("rubble"), rng=c.rng), jit=0.0)
                elif kind == "door":
                    door(c, w, s_, za, ww, zz - za)
                    if k in stone:
                        c.add(L.member(w.p(s_ - ww / 2 - 0.1, zz + 0.06, 0.07), w.p(s_ + ww / 2 + 0.1, zz + 0.06, 0.07),
                                       0.14, 0.12, c.sw("oak"), rng=c.rng))
        if k > 0 and jetty > 0:
            # joist ends under the overhang (front and back)
            for name in ("front", "back"):
                w = walls[name]
                n = max(2, int(w.L / 0.32))
                for i in range(n):
                    s_ = (i + 0.5) * w.L / n
                    c.add(L.member(w.p(s_, zb - t * 0.5, -jetty - 0.05), w.p(s_, zb - t * 0.5, 0.05), t * 0.7, t * 0.7,
                                   c.sw("oak"), rng=c.rng))
        zb = zt
        ext += jetty if k + 1 < len(stories) else 0.0
    return walls, (x0, x1, y0 - jetty * (len(stories) - 1), y1 + jetty * (len(stories) - 1))


def k_croft(c):
    """Croft (supply, 4x4 cells = 2 m): small steep-roofed half-timber cottage, chimney, stork nest."""
    W, D = c.fp
    hw, hd = W / 2, D / 2
    t = 0.09
    x0, x1, y0, y1 = -hw * 0.72, hw * 0.72, -hd * 0.62, hd * 0.55
    zp, zw = 0.32, 1.22
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, ops={
        ("front", 0): [(0.68, 0.36, 0.0, 0.66, "door"), (0.27, 0.3, 0.3, 0.62, "window")],
        ("back", 0): [(0.5, 0.3, 0.3, 0.62, "window")],
        ("right", 0): [(0.5, 0.26, 0.32, 0.6, "window")]}, bay=0.55)
    ov = 0.2
    half = (y1 - y0) / 2 + ov
    yc = (y0 + y1) / 2
    pitch = math.radians(60)
    z_eave = zw - ov * math.tan(pitch) * 0.55
    z_ridge = zw + ((y1 - y0) / 2) * math.tan(pitch)
    gable_roof(c, x0 - 0.16, x1 + 0.16, yc, half, z_eave, z_ridge, th=0.1, sag=0.035, t=0.08, nu=8, nv=5)
    for k in ("left", "right"):
        gable_infill(c, walls[k], zw, z_ridge - 0.05, t)
    chimney(c, x0 + 0.3, yc - 0.18, z_ridge - 0.7, z_ridge + 0.32, 0.26)
    stork_nest(c, (x1 - 0.28, yc, z_ridge - 0.02), r=0.24, facing=200)
    pennant(c, (x0 - 0.05, yc + 0.0, z_ridge - 0.08), 0.62, 0.62, 0.24, dirn=(-0.5, 1), phase=0.4)
    barrel(c, (x1 + 0.08, y1 + 0.22, 0), r=0.13, h=0.3)
    log_stack(c, (x0 + 0.25, y0 - 0.2, 0), 0.6, 2, r=0.07, axis="x")
    return {"height_target": (2.5, 3.5)}


def braziers(c, pts, r=0.16, h=0.55):
    for (x, y) in pts:
        for k in range(3):
            a = k * 2 * math.pi / 3 + 0.3
            c.add(L.member((x + math.cos(a) * r * 1.1, y + math.sin(a) * r * 1.1, 0), (x, y, h * 0.85), 0.035, 0.035,
                           c.sw("iron")))
        bowl = L.lathe([(0.0, h * 0.8), (r * 0.6, h * 0.8), (r, h * 0.95), (r * 1.05, h * 1.05), (r * 0.9, h * 1.03)], 10,
                       c.sw("iron"), cap_top=False)
        bowl.move(x, y, 0)
        c.add(bowl, dice=None)
        coals = L.lathe([(r * 0.95, h * 1.0), (r * 0.5, h * 1.1), (0, h * 1.13)], 8, c.sw("ember"))
        coals.uv = np.stack([0.5 + coals.v[coals.t][..., 0] / (2.2 * r), 0.5 + coals.v[coals.t][..., 1] / (2.2 * r)], -1)
        coals.move(x, y, 0)
        c.add(coals, dice=None, ao=False, min_shade=1.0, form=0.0)


def iron_wheel_arch(c, cx, cy, zc, R, depth=0.18, spokes=5):
    """Oath Hall: half of a giant iron wheel framing the door, rim legs to the ground, a hub boss."""
    rim_w = R * 0.14
    n = 14
    ang = np.linspace(0, math.pi, n + 1)
    path = np.stack([cx + np.cos(ang) * (R - rim_w / 2), np.full(n + 1, cy), zc + np.sin(ang) * (R - rim_w / 2)], 1)
    rim = L.sweep(L.rect_profile(rim_w, depth, 0.02), path, c.sw("iron"), up=(0, 1, 0))
    c.add(rim, dice=None)
    tyre_path = np.stack([cx + np.cos(ang) * (R + 0.01), np.full(n + 1, cy), zc + np.sin(ang) * (R + 0.01)], 1)
    c.add(L.sweep(L.rect_profile(rim_w * 0.35, depth * 1.1, 0.01), tyre_path, c.sw("iron"), up=(0, 1, 0)), dice=None,
          tint=(0.75, 0.75, 0.78))
    for sx in (-1, 1):
        c.add(L.member((cx + sx * (R - rim_w / 2), cy, 0.0), (cx + sx * (R - rim_w / 2), cy, zc + 0.02), rim_w * 1.05, depth,
                       c.sw("iron"), roll_up=(0, 1, 0)))
        foot = L.box(rim_w * 2.2, depth * 1.8, 0.22, c.sw("rubble"), chamfer=0.03, center=(cx + sx * (R - rim_w / 2), cy, 0), base=True)
        c.add(foot, dice=None)
    hub = L.lathe([(0, -depth * 0.8), (R * 0.2, -depth * 0.8), (R * 0.22, 0), (R * 0.2, depth * 0.8), (R * 0.1, depth * 1.4),
                   (0, depth * 1.5)], 12, c.sw("iron"))
    hub.rot(-90, 0, 0).move(cx, cy, zc)
    c.add(hub, dice=None)
    for k in range(spokes):
        a = math.pi * (k + 0.5) / spokes
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        c.add(L.member(np.array([cx, cy, zc]) + d * R * 0.18, np.array([cx, cy, zc]) + d * (R - rim_w * 0.7),
                       rim_w * 0.6, depth * 0.7, c.sw("iron"), roll_up=(0, 1, 0)))
    # hub coal (dark bronze, kingdom emblem)
    coal = L.lathe([(0, 0), (R * 0.09, 0.0), (R * 0.07, R * 0.06), (0, R * 0.08)], 8, c.sw("pal"))
    coal.rot(-90, 0, 0).move(cx, cy + depth * 1.45, zc)
    c.P(coal, "#6E4A26", dice=None)


def floor_wheel(c, cx, cy, r):
    ang = np.arange(18) * 2 * math.pi / 18
    path = np.stack([cx + np.cos(ang) * r, cy + np.sin(ang) * r, np.full(18, 0.03)], 1)
    c.add(L.sweep(L.rect_profile(r * 0.16, 0.06, 0.01), path, c.sw("iron"), closed_path=True), dice=None)
    for k in range(6):
        a = k * math.pi / 3
        c.add(L.member((cx, cy, 0.03), (cx + math.cos(a) * r, cy + math.sin(a) * r, 0.03), r * 0.1, 0.05, c.sw("iron")))
    hub = L.lathe([(r * 0.2, 0), (r * 0.18, 0.07), (0, 0.09)], 10, c.sw("iron"))
    hub.move(cx, cy, 0)
    c.add(hub, dice=None)
    slab = L.lathe([(r * 1.25, 0.0), (r * 1.25, 0.02), (r * 1.2, 0.03), (0, 0.03)], 16, c.sw("rubble"))
    slab.move(cx, cy, 0)
    c.add(slab, dice=0.3, jit=0.0)


def k_oath_hall(c):
    """Oath Hall (altar, 6x6 cells = 3 m): squat stone hall, hip roof, a giant iron wheel arch over
    the door, the oath wheel set in the floor in front."""
    W, D = c.fp
    t = 0.1
    x0, x1, y0, y1 = -1.25, 1.25, -1.2, 0.62
    zp, zw = 0.26, 1.42
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, stone=(0,), ops={
        ("front", 0): [(0.5, 0.62, 0.0, 0.98, "door")],
        ("left", 0): [(0.5, 0.26, 0.42, 0.86, "window")],
        ("right", 0): [(0.5, 0.26, 0.42, 0.86, "window")],
        ("back", 0): [(0.3, 0.26, 0.42, 0.86, "window"), (0.7, 0.26, 0.42, 0.86, "window")]})
    # heavy corner buttresses
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bx, by = (x1 if sx > 0 else x0), (y1 if sy > 0 else y0)
        p = L.gbox(0.34, 0.34, 1.25, c.sw("rubble"), chamfer=0.04, center=(bx + sx * 0.04, by + sy * 0.04, 0), grid=0.4)
        top = p.v[:, 2] > 0.6
        p.v[top, 0] = bx + sx * 0.04 + (p.v[top, 0] - bx - sx * 0.04) * 0.7
        p.v[top, 1] = by + sy * 0.04 + (p.v[top, 1] - by - sy * 0.04) * 0.7
        p.box_uv()
        c.add(p)
    ov = 0.2
    hip_roof(c, x0 - ov, x1 + ov, y0 - ov, y1 + ov + 0.05, zw - 0.06, 2.75, ridge_frac=1.0, th=0.13, kick=0.09, hip_w=0.075,
             hips=True)
    iron_wheel_arch(c, 0.0, y1 + 0.13, zp + 0.98, 0.72)
    floor_wheel(c, 0.0, y1 + 0.62, 0.27)
    braziers(c, [(-0.88, y1 + 0.55), (0.88, y1 + 0.55)])
    for sx in (-1, 1):
        banner(c, (sx * 0.98, y1 + 0.05, zw - 0.02), 0.42, 0.95, normal=(0, 1))
    # pennants on the ridge ends
    rl = 1.0 * abs((x1 - x0) / 2 - (y1 - y0 + 0.05) / 2)
    ycen = (y0 + y1 + 0.05) / 2
    for sx in (-1, 1):
        pennant(c, (sx * rl, ycen, 2.72), 0.7, 0.75, 0.28, dirn=(sx, 0.5), phase=sx)
    return {"height_target": (2.8, 3.6)}


def k_drill_yard(c):
    """Drill Yard (barracks, 8x8 cells = 4 m): timber longhouse with a front cross-gable, a fenced
    yard with a pavise wall, a weapon rack and a straw drill dummy; tall pennant mast."""
    t = 0.11
    x0, x1, y0, y1 = -1.8, 1.8, -1.72, -0.32
    zp, zw = 0.3, 1.5
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, ops={
        ("front", 0): [(0.16, 0.34, 0.35, 0.82, "window"), (0.84, 0.34, 0.35, 0.82, "window")],
        ("back", 0): [(0.25, 0.34, 0.35, 0.82, "window"), (0.75, 0.34, 0.35, 0.82, "window")],
        ("left", 0): [(0.5, 0.3, 0.38, 0.8, "window")], ("right", 0): [(0.5, 0.3, 0.38, 0.8, "window")]}, bay=0.7)
    ov = 0.22
    yc = (y0 + y1) / 2
    half = (y1 - y0) / 2 + ov
    z_ridge = zw + (y1 - y0) / 2 * math.tan(math.radians(60))
    gable_roof(c, x0 - 0.2, x1 + 0.2, yc, half, zw - 0.12, z_ridge, th=0.13, sag=0.06, t=0.1, nu=12, nv=5)
    for k in ("left", "right"):
        gable_infill(c, walls[k], zw, z_ridge - 0.06, t)
    # front cross-gable porch over the door
    wx0, wx1, wy0, wy1 = -0.55, 0.55, y1 - 0.1, y1 + 0.42
    pw, _ = house(c, wx0, wx1, wy0, wy1, zp, [zw], t, ops={("front", 0): [(0.5, 0.46, 0.0, 0.92, "door")]}, bay=0.5,
                  plinth_pad=0.04)
    zr2 = zw + 0.55 * math.tan(math.radians(58))
    gable_roof(c, wy0 - 0.25, wy1 + 0.18, 0.0, 0.55 + 0.16, zw - 0.1, zr2, th=0.11, sag=0.03, t=0.09, nu=6, nv=4,
               axis="y", cx=0.0, ridge_team=False)
    gable_infill(c, pw["front"], zw, zr2 - 0.05, t, window_w=0.26)
    # yard
    yy0, yy1 = 0.15, 1.9
    fence_wattle(c, (-1.9, yy0), (-1.9, yy1), 0.45)
    fence_wattle(c, (1.9, yy1), (1.9, yy0), 0.45)
    fence_wattle(c, (-1.9, yy1), (-0.5, yy1), 0.45)
    fence_wattle(c, (0.5, yy1), (1.9, yy1), 0.45)
    for gx in (-0.5, 0.5):
        c.add(L.member((gx, yy1, 0), (gx, yy1, 0.95), 0.1, 0.1, c.sw("oak"), rng=c.rng))
    for i, px in enumerate(np.linspace(-1.55, -0.35, 4)):
        pavise(c, (px, 0.55 + 0.05 * (i % 2), 0.0), 0.0, h=0.95, w=0.42, lean=10)
    weapon_rack(c, (1.25, 0.65, 0.0), rz=0.0, width=1.0, h=0.95, n=4)
    # drill dummy: post, crossbar, straw body, kettle hat
    dx, dy = 0.75, 1.3
    c.add(L.member((dx, dy, 0), (dx, dy, 1.25), 0.08, 0.08, c.sw("oak"), rng=c.rng))
    c.add(L.member((dx - 0.35, dy, 1.0), (dx + 0.35, dy, 1.0), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    body = L.blob(c.sw("straw"), radius=0.22, subdiv=1, scale=(1, 0.8, 1.3), seed=7, noise_amp=0.1)
    body.move(dx, dy, 0.62)
    c.add(body, dice=None)
    hat = L.lathe([(0.0, 0.0), (0.3, 0.0), (0.3, 0.02), (0.14, 0.05), (0.13, 0.15), (0.0, 0.17)], 10, c.sw("iron"))
    hat.move(dx, dy, 1.2)
    c.add(hat, dice=None)
    # tall pennant mast at the house corner
    pennant(c, (1.82, -0.2, 0.0), 3.55, 0.85, 0.34, dirn=(-0.4, 1), phase=0.8)
    return {"height_target": (3.4, 4.2)}


def k_timber_yard(c):
    """Timber Yard (lumber drop-off, 8x8 cells = 4 m): open timber shed over a sawpit with a log on
    trestles and a two-man pit saw, a tall cribbed log stack at one end, sawn planks."""
    t = 0.13
    px = [-1.6, -0.3, 1.0]
    py = [-1.45, 0.25]
    zt = 1.62
    for x in px:
        for y in py:
            c.add(L.member((x, y, 0), (x, y, zt), t, t, c.sw("oak"), rng=c.rng, chamfer=0.02))
            f = L.box(t * 2, t * 2, 0.16, c.sw("rubble"), center=(x, y, 0), base=True, chamfer=0.03)
            c.add(f, dice=None)
    for y in py:
        c.add(L.member((px[0] - 0.15, y, zt - t / 2), (px[-1] + 0.15, y, zt - t / 2), t * 1.1, t * 1.2, c.sw("oak"), rng=c.rng))
        for i in range(len(px) - 1):
            for sgn in (0, 1):
                xa, xb = (px[i], px[i] + 0.45) if sgn == 0 else (px[i + 1], px[i + 1] - 0.45)
                c.add(L.member((xa, y, zt - 0.45), (xb, y, zt - t), t * 0.7, t * 0.7, c.sw("oak"), rng=c.rng))
    for x in px:
        c.add(L.member((x, py[0] - 0.1, zt - t / 2), (x, py[1] + 0.1, zt - t / 2), t, t, c.sw("oak"), rng=c.rng))
    # back plank wall
    bw = L.plate((px[-1] + 0.05, py[0] - 0.08, 0.05), (px[0] - 0.05, py[0] - 0.08, 0.05), (px[0] - 0.05, py[0] - 0.08, zt - 0.1),
                 (px[-1] + 0.05, py[0] - 0.08, zt - 0.1), 0.05, c.sw("planks"))
    bw.box_uv()
    c.add(bw, dice=0.4, uvrot=True)
    yc = (py[0] + py[1]) / 2
    half = (py[1] - py[0]) / 2 + 0.3
    gable_roof(c, px[0] - 0.3, px[-1] + 0.3, yc, half, zt - 0.05, zt + 1.1, th=0.12, sag=0.07, t=0.1, nu=12, nv=5)
    for x in (px[0], px[-1]):
        w = Wall((x, py[1]), (0, -1), (-1 if x < 0 else 1, 0), py[1] - py[0])
        if x > 0:
            w = Wall((x, py[0]), (0, 1), (1, 0), py[1] - py[0])
        gable_infill(c, w, zt, zt + 1.05, 0.1, key="planks", timbers=True)
    # sawpit with a log on trestles and a pit saw
    sx, sy = -0.3, -0.6
    rim = L.prism(L.rect_profile(1.9, 0.75, 0.05), 0.0, 0.14, c.sw("planks"), chamfer=0.02)
    rim.move(sx, sy, 0)
    c.add(rim, dice=None)
    pit = L.quad((sx - 0.85, sy - 0.28, 0.02), (sx + 0.85, sy - 0.28, 0.02), (sx + 0.85, sy + 0.28, 0.02), (sx - 0.85, sy + 0.28, 0.02),
                 c.sw("pal"))
    c.P(pit, "#2A2220", ao=False, min_shade=0.0)
    pit.v[:, 2] = 0.145
    for tx in (sx - 0.7, sx + 0.7):
        trestle(c, (tx, sy, 0.14), rz=90, w=0.75, h=0.55)
    lg = L.lathe([(0.17, -1.0), (0.18, 0), (0.16, 1.0)], 10, c.sw("bark"))
    lg.rot(0, 90, 0).move(sx, sy, 0.86)
    c.add(lg, dice=None)
    for sgn in (-1, 1):
        e = Part(np.vstack([np.stack([np.cos(a) * 0.165, np.sin(a) * 0.165, np.zeros_like(a)], 1) for a in
                            [np.arange(10) * 2 * math.pi / 10]] + [np.zeros((1, 3))]),
                 np.array([(10, j, (j + 1) % 10) for j in range(10)]), c.sw("rings"))
        vv = e.v[e.t]
        e.uv = np.stack([0.5 + vv[..., 0] / 0.34, 0.5 - vv[..., 1] / 0.34], -1)
        e.rot(0, 90 * sgn, 0).move(sx + sgn * 1.0, sy, 0.86)
        c.add(e, dice=None)
    blade = L.box(0.02, 0.16, 1.5, c.sw("iron"), center=(sx + 0.25, sy, 0.75))
    c.add(blade, dice=None)
    for zz in (0.1, 1.45):
        c.add(L.member((sx + 0.25, sy - 0.22, zz), (sx + 0.25, sy + 0.22, zz), 0.05, 0.05, c.sw("oak")))
    # tall cribbed log stack at the right end (logs along y)
    lx0 = 1.35
    for row in range(6):
        for k in range(2):
            rr = 0.13 + 0.025 * c.r()
            xx = lx0 + 0.15 + k * 0.29 + (0.06 if row % 2 else 0)
            zz = 0.14 + row * 0.25
            Lg = 2.7 + 0.2 * c.r()
            b = L.lathe([(rr, -Lg / 2), (rr * 1.03, 0), (rr, Lg / 2)], 8, c.sw("bark"), a0=c.r())
            b.rot(90, 0, 0).move(xx, -0.25 + 0.1 * (c.r() - 0.5), zz)
            c.add(b, dice=None)
            for sgn in (-1, 1):
                ang = np.arange(8) * 2 * math.pi / 8
                vv = np.vstack([np.stack([np.cos(ang) * rr * 0.98, np.sin(ang) * rr * 0.98, np.zeros(8)], 1), [[0, 0, 0]]])
                e = Part(vv, np.array([(8, j, (j + 1) % 8) for j in range(8)]), c.sw("rings"))
                q = e.v[e.t]
                e.uv = np.stack([0.5 + q[..., 0] / (2 * rr), 0.5 - q[..., 1] / (2 * rr)], -1)
                e.rot(-90 * sgn, 0, 0).move(xx, b.v[:, 1].mean() + sgn * Lg / 2, zz)
                c.add(e, dice=None)
    for yy in (-1.6, 1.1):
        for xx in (lx0 + 0.02, lx0 + 0.72):
            c.add(L.member((xx, yy, 0), (xx, yy, 1.75), 0.1, 0.1, c.sw("oak"), rng=c.rng))
    # sawn planks and a chopping block
    for i in range(5):
        p = L.box(1.3, 0.24, 0.05, c.sw("oak"), center=(-1.05 + 0.02 * c.r(), 1.35 + 0.03 * c.r(), 0.025 + i * 0.055))
        p.rot(0, 0, c.r(-4, 4), pivot=(-1.05, 1.35, 0))
        c.add(p, dice=None)
    for i in range(3):
        p = L.box(1.2, 0.22, 0.05, c.sw("oak"), center=(-1.05, 1.62, 0.025 + i * 0.055))
        c.add(p, dice=None)
    pennant(c, (px[0] - 0.25, yc, zt + 1.0), 0.75, 0.8, 0.3, dirn=(-0.6, 1), phase=0.2)
    for i in range(len(px) - 1):
        banner(c, ((px[i] + px[i + 1]) / 2, py[1] + 0.09, zt - 0.02), (px[i + 1] - px[i]) * 0.8, 0.58, normal=(0, 1),
               bar=False)
    return {"height_target": (3.0, 4.0)}


def k_foundry(c):
    """Foundry (smithy, 6x6 cells = 3 m): stone ground floor, timber upper storey, a crow-stepped
    front gable, a tall brick chimney with a bronze cap, forge glow through open doors, anvil."""
    t = 0.1
    x0, x1, y0, y1 = -1.08, 1.08, -1.12, 0.62
    zp, z1, z2 = 0.26, 1.22, 2.05
    jet = 0.1
    walls, _ = house(c, x0, x1, y0, y1, zp, [z1, z2], t, stone=(0,), jetty=jet, ops={
        ("front", 0): [(0.5, 0.78, 0.0, 0.88, "blank")],
        ("left", 0): [(0.5, 0.26, 0.35, 0.72, "window")], ("right", 0): [(0.35, 0.26, 0.35, 0.72, "window")],
        ("front", 1): [(0.27, 0.3, 0.15, 0.6, "window"), (0.73, 0.3, 0.15, 0.6, "window")],
        ("left", 1): [(0.5, 0.3, 0.15, 0.6, "window")], ("right", 1): [(0.5, 0.3, 0.15, 0.6, "window")],
        ("back", 1): [(0.5, 0.3, 0.15, 0.6, "window")]})
    # forge opening: dark recess, ember glow, open doors, oak lintel
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    s0 = fw.L / 2
    dk = L.quad(fw.p(s0 - 0.4, zp, 0.045), fw.p(s0 + 0.4, zp, 0.045), fw.p(s0 + 0.4, zp + 0.88, 0.045), fw.p(s0 - 0.4, zp + 0.88, 0.045),
                c.sw("pal"))
    c.P(_face_out(dk, fw), "#2A2220", ao=False, min_shade=0.0)
    gl = L.quad(fw.p(s0 - 0.28, zp, 0.05), fw.p(s0 + 0.28, zp, 0.05), fw.p(s0 + 0.28, zp + 0.5, 0.05), fw.p(s0 - 0.28, zp + 0.5, 0.05),
                c.sw("ember"))
    gl.uv = np.array([[(0.15, 0.95), (0.85, 0.95), (0.85, 0.35)], [(0.15, 0.95), (0.85, 0.35), (0.15, 0.35)]])
    c.add(_face_out(gl, fw), ao=False, min_shade=1.0, form=0.0, occ=False)
    c.add(L.member(fw.p(s0 - 0.55, zp + 0.95, 0.09), fw.p(s0 + 0.55, zp + 0.95, 0.09), 0.16, 0.14, c.sw("oak"), rng=c.rng))
    for sgn in (-1, 1):
        dp = L.box(0.4, 0.86, 0.05, c.sw("planks"))
        dp.move(sgn * 0.2, 0.43, 0).rot(0, sgn * -62, 0).move(0, 0, 0.06)
        fw.place(dp, s0 + sgn * 0.4, zp, 0.0)
        c.add(dp, dice=None, uvrot=True)
    # roof: ridge along y, gable to the front, crow-stepped front gable
    pitch = math.radians(52)
    half = (x1 - x0) / 2
    z_ridge = z2 + half * math.tan(pitch)
    ov = 0.18
    yf = y1 + jet
    gable_roof(c, y0 - jet - 0.2, yf - 0.02, 0.0, half + ov, z2 - ov * math.tan(pitch) * 0.6, z_ridge, th=0.12, sag=0.04,
               t=0.09, nu=8, nv=5, axis="y", cx=0.0)
    # the gable roof built along x then rotated: x range maps to y (after rotation about (0, 0)):
    gw = Wall((x1, yf), (-1, 0), (0, 1), x1 - x0)
    ztop = stepped_gable(c, gw, z2, z_ridge, steps=3, th=0.2, key="brick", rise=0.2, d0=-0.12)
    gable_infill(c, Wall((x0, y0 - jet), (1, 0), (0, -1), x1 - x0), z2, z_ridge - 0.05, t, window_w=0.0)
    window(c, gw, gw.L / 2, z2 + 0.25, z2 + 0.65, 0.28, shutters=False)
    # brick chimney with a bronze cap
    chx, chy = 0.62, -0.78
    ch = L.gbox(0.55, 0.55, 4.1, c.sw("brick"), center=(chx, chy, 0.0), chamfer=0.03, grid=0.45)
    top = ch.v[:, 2] > 2.0
    ch.v[top, 0] = chx + (ch.v[top, 0] - chx) * 0.8
    ch.v[top, 1] = chy + (ch.v[top, 1] - chy) * 0.8
    ch.box_uv()
    c.add(ch, jit=0.006)
    band = L.box(0.5, 0.5, 0.1, c.sw("rubble"), center=(chx, chy, 3.5), chamfer=0.02)
    c.add(band, dice=None)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.add(L.member((chx + sx * 0.17, chy + sy * 0.17, 4.08), (chx + sx * 0.17, chy + sy * 0.17, 4.28), 0.05, 0.05,
                           c.sw("iron")))
    cap = L.lathe([(0.38, 0.0), (0.36, 0.05), (0.2, 0.24), (0.07, 0.38), (0.0, 0.44)], 4, c.sw("scales"), a0=math.pi / 4)
    cap.move(chx, chy, 4.26)
    c.add(cap, dice=None, tint=(1.15, 1.05, 0.95))
    knob = L.lathe([(0, 0), (0.07, 0.04), (0.06, 0.1), (0, 0.14)], 8, c.sw("pal"))
    knob.move(chx, chy, 4.66)
    c.P(knob, "#6E4A26", dice=None)
    anvil(c, (0.55, y1 + 0.55, 0), rz=20)
    barrel(c, (-0.62, y1 + 0.5, 0), r=0.2, h=0.42)
    coal = L.blob(c.sw("pal"), radius=0.3, subdiv=1, scale=(1, 0.8, 0.45), seed=11, noise_amp=0.2, flat_bottom=0.0)
    coal.move(-1.05, y1 + 0.62, 0)
    c.P(coal, "#26221F", dice=None)
    pennant(c, (0.0, yf - 0.02, ztop), 0.65, 0.75, 0.28, dirn=(1, 0.3), phase=1.0)
    awning(c, -0.62, 0.62, y1 + 0.06, zp + 1.12, 0.42, 0.22, posts=False, stripes=True)
    for sx in (-1, 1):
        banner(c, (sx * 0.86, y1 + 0.08, z1 - 0.04), 0.3, 0.62, normal=(0, 1))
    return {"height_target": (3.0, 4.6)}


def k_collegium(c):
    """Collegium (caster hall, 8x8 cells = 4 m): a tall narrow jettied guild house with a bell-cote
    on its front gable, beside a walled linden herb garden."""
    t = 0.1
    x0, x1, y0, y1 = -1.85, -0.05, -1.45, 1.0
    zp = 0.3
    st = [1.2, 1.98, 2.7]
    jet = 0.1
    walls, _ = house(c, x0, x1, y0, y1, zp, st, t, jetty=jet, ops={
        ("front", 0): [(0.5, 0.5, 0.0, 0.92, "door")],
        ("right", 0): [(0.3, 0.28, 0.35, 0.75, "window"), (0.75, 0.28, 0.35, 0.75, "window")],
        ("left", 0): [(0.5, 0.28, 0.35, 0.75, "window")],
        ("front", 1): [(0.25, 0.3, 0.18, 0.62, "window"), (0.75, 0.3, 0.18, 0.62, "window")],
        ("right", 1): [(0.25, 0.3, 0.18, 0.62, "window"), (0.75, 0.3, 0.18, 0.62, "window")],
        ("left", 1): [(0.5, 0.3, 0.18, 0.62, "window")], ("back", 1): [(0.5, 0.3, 0.18, 0.62, "window")],
        ("front", 2): [(0.5, 0.34, 0.14, 0.58, "window")],
        ("right", 2): [(0.3, 0.26, 0.14, 0.56, "window"), (0.7, 0.26, 0.14, 0.56, "window")],
        ("left", 2): [(0.5, 0.26, 0.14, 0.56, "window")]})
    xm = (x0 + x1) / 2
    half = (x1 - x0) / 2
    pitch = math.radians(56)
    z_ridge = st[-1] + half * math.tan(pitch)
    ov = 0.14
    yf, yb = y1 + 2 * jet, y0 - 2 * jet
    gable_roof(c, yb - 0.16, yf + 0.16, xm, half + ov, st[-1] - ov * math.tan(pitch) * 0.6, z_ridge, th=0.12, sag=0.05,
               t=0.09, nu=10, nv=6, axis="y", cx=xm)
    gable_infill(c, Wall((x1, yf), (-1, 0), (0, 1), x1 - x0), st[-1], z_ridge - 0.05, t, window_w=0.0)
    gable_infill(c, Wall((x0, yb), (1, 0), (0, -1), x1 - x0), st[-1], z_ridge - 0.05, t, window_w=0.0)
    bell_cote(c, (xm, yf - 0.05, z_ridge - 0.12), size=0.52, rz=0)
    banner(c, (xm, y1 + 2 * jet + 0.06, st[1] - 0.04), 0.62, 0.72, normal=(0, 1))
    for sx in (-1, 1):
        banner(c, (xm + sx * (x1 - x0) * 0.42, y1 + jet + 0.06, st[0] + 0.62), 0.3, 0.75, normal=(0, 1))
    pennant(c, (xm, yb - 0.08, z_ridge - 0.08), 0.6, 0.75, 0.28, dirn=(1, -0.4), phase=0.9)
    # walled herb garden
    gx0, gx1, gy0, gy1 = 0.18, 1.92, -1.85, 1.9
    wt, wh = 0.16, 0.5
    segs = [((gx0, gy0), (gx1, gy0)), ((gx1, gy0), (gx1, gy1)), ((gx1, gy1), (1.25, gy1)), ((0.75, gy1), (gx0, gy1)),
            ((gx0, gy1), (gx0, gy0))]
    for (a, b) in segs:
        a, b = np.array(a, float), np.array(b, float)
        d = b - a
        Lw = float(np.linalg.norm(d))
        e = d / Lw
        n = np.array([e[1], -e[0]])
        wl = Wall(a + n * wt / 2, e, n, Lw)
        wall_prism(c, wl, [(-wt / 2, 0.0), (Lw + wt / 2, 0.0), (Lw + wt / 2, wh), (-wt / 2, wh)], -wt, 0.0, "plaster",
                   chamfer=0.03, grid=0.45)
        cp = L.box(Lw + wt + 0.04, 0.07, wt + 0.06, c.sw("rubble"), chamfer=0.015)
        cp.move(Lw / 2, wh + 0.035, -wt / 2)
        wl.place(cp)
        c.add(cp, dice=None)
    for gx in (0.75, 1.25):
        c.add(L.box(0.2, 0.2, 0.72, c.sw("rubble"), center=(gx, gy1 - wt / 2, 0), base=True, chamfer=0.03), dice=None)
        ball = L.lathe([(0, 0), (0.08, 0.04), (0.07, 0.12), (0, 0.15)], 8, c.sw("rubble"))
        ball.move(gx, gy1 - wt / 2, 0.72)
        c.add(ball, dice=None)
    for gx in (0.75, 1.25):
        c.add(L.member((gx, gy1 - 0.16, 0.7), (gx, gy1 - 0.16, 1.85), 0.06, 0.06, c.sw("oak"), rng=c.rng))
        banner(c, (gx, gy1 - 0.08, 1.8), 0.3, 0.75, normal=(0, 1))
    sapling(c, (0.85, -1.05, 0), h=1.9, r=0.5)
    sapling(c, (1.45, 0.25, 0), h=1.7, r=0.45)
    for (bx, by) in ((1.25, 1.2), (0.6, -0.15)):
        bed = L.box(0.7, 0.42, 0.18, c.sw("planks"), center=(bx, by, 0), base=True, chamfer=0.02)
        c.add(bed, dice=None)
        soil = L.box(0.64, 0.36, 0.02, c.sw("dirt"), center=(bx, by, 0.18), base=True)
        c.add(soil, dice=None)
        for k in range(4):
            hb = L.blob(c.sw("leaves"), radius=0.1, subdiv=1, scale=(1, 1, 0.8), seed=int(c.r(0, 9999)), noise_amp=0.25)
            hb.move(bx - 0.24 + k * 0.16, by + c.r(-0.06, 0.06), 0.18)
            c.add(hb, dice=None, tint=(1.0, 1.08, 0.9) if k % 2 else (0.85, 0.95, 0.8))
    return {"height_target": (4.0, 4.9)}


def k_wainwright_yard(c):
    """Wainwright Yard (siege workshop, 8x8 cells = 4 m): open shed with a wagon on the stocks, wheels
    leaning on the posts, and a giant wagon wheel on a pole as the yard sign."""
    t = 0.13
    px = [-1.75, -0.45, 0.85]
    py = [-1.6, -0.2]
    zt = 1.6
    for x in px:
        for y in py:
            c.add(L.member((x, y, 0), (x, y, zt), t, t, c.sw("oak"), rng=c.rng, chamfer=0.02))
            c.add(L.box(t * 2, t * 2, 0.16, c.sw("rubble"), center=(x, y, 0), base=True, chamfer=0.03), dice=None)
    for y in py:
        c.add(L.member((px[0] - 0.15, y, zt - t / 2), (px[-1] + 0.15, y, zt - t / 2), t * 1.1, t * 1.2, c.sw("oak"), rng=c.rng))
        for i in range(len(px) - 1):
            c.add(L.member((px[i], y, zt - 0.45), (px[i] + 0.45, y, zt - t), t * 0.7, t * 0.7, c.sw("oak"), rng=c.rng))
            c.add(L.member((px[i + 1], y, zt - 0.45), (px[i + 1] - 0.45, y, zt - t), t * 0.7, t * 0.7, c.sw("oak"), rng=c.rng))
    for x in px:
        c.add(L.member((x, py[0] - 0.1, zt - t / 2), (x, py[1] + 0.1, zt - t / 2), t, t, c.sw("oak"), rng=c.rng))
    bw = L.plate((px[-1] + 0.05, py[0] - 0.08, 0.05), (px[0] - 0.05, py[0] - 0.08, 0.05), (px[0] - 0.05, py[0] - 0.08, zt - 0.1),
                 (px[-1] + 0.05, py[0] - 0.08, zt - 0.1), 0.05, c.sw("planks"))
    bw.box_uv()
    c.add(bw, dice=0.4, uvrot=True)
    yc = (py[0] + py[1]) / 2
    gable_roof(c, px[0] - 0.28, px[-1] + 0.28, yc, (py[1] - py[0]) / 2 + 0.32, zt - 0.06, zt + 1.05, th=0.12, sag=0.06,
               t=0.1, nu=12, nv=5)
    for x, sgn in ((px[0], -1), (px[-1], 1)):
        w = Wall((x, py[1]), (0, -1), (-1, 0), py[1] - py[0]) if sgn < 0 else Wall((x, py[0]), (0, 1), (1, 0), py[1] - py[0])
        gable_infill(c, w, zt, zt + 1.0, 0.1, key="planks")
    # wagon on the stocks (no front wheels yet) under the shed
    wagon(c, (-0.45, -0.9, 0.12), rz=0.0, length=1.7, width=0.82, h=0.42, wheel_r=0.36, team_band=True, four=False,
          shafts=False)
    for xx in (-1.15, 0.25):
        c.add(L.box(0.22, 0.7, 0.3, c.sw("oak"), center=(xx, -0.9, 0), base=True), dice=None)
    # wheels leaning on posts
    for (wx, wy, rz) in ((px[0] - 0.08, 0.05, 90), (px[-1] + 0.1, 0.05, 90)):
        for p in wheel(c, (wx, wy, 0.42), 0.42, axis="y", spokes=8):
            p.rot(-12, 0, 0, pivot=(wx, wy, 0)).rot(0, 0, rz - 90, pivot=(wx, wy, 0))
    # the sign: a giant wagon wheel on a pole (front right), pennant above
    sx_, sy_ = 1.45, 1.15
    c.add(L.member((sx_, sy_, 0), (sx_, sy_, 3.85), 0.16, 0.16, c.sw("oak"), rng=c.rng, chamfer=0.03))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c.add(L.member((sx_ + math.cos(a) * 0.45, sy_ + math.sin(a) * 0.45, 0), (sx_, sy_, 0.9), 0.08, 0.08, c.sw("oak"), rng=c.rng))
    c.add(L.box(0.5, 0.5, 0.2, c.sw("rubble"), center=(sx_, sy_, 0), base=True, chamfer=0.04), dice=None)
    wheel(c, (sx_, sy_ + 0.14, 3.2), 0.68, axis="y", spokes=8, width=0.12)
    pennant(c, (sx_, sy_, 3.8), 0.7, 0.62, 0.26, dirn=(-1, 0.4), phase=0.3)
    # spare spokes and a felloe pile, a finished wagon in the yard
    for i in range(6):
        p = L.member((-1.5 + i * 0.06, 0.6, 0.04), (-0.9 + i * 0.06, 0.95, 0.04), 0.05, 0.05, c.sw("oak"), rng=c.rng)
        c.add(p)
    wagon(c, (-0.3, 1.15, 0.0), rz=8.0, length=1.6, width=0.78, h=0.4, wheel_r=0.34, cover=True, team_band=False)
    return {"height_target": (3.6, 4.6)}


def awning(c, x0, x1, y_wall, z_wall, depth, drop, key="team_band", valance=0.12, posts=False, stripes=False,
           stripe_col="#EDE2C8"):
    """Cloth awning projecting from a wall (+y) with a scalloped valance; stripes=True alternates
    team cloth and ivory (palette) strips."""
    if stripes:
        n = max(4, int(round((x1 - x0) / 0.22)))
        if n % 2 == 0:
            n += 1
        for i in range(n):
            xa, xb = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
            if i % 2 == 0:
                awning(c, xa, xb, y_wall, z_wall, depth, drop, key=key, valance=valance, stripes=False)
            else:
                k0 = len(c.parts)
                awning(c, xa, xb, y_wall, z_wall, depth, drop, key=key, valance=valance, stripes=False)
                for p in c.parts[k0:]:
                    p.sw = c.sw("pal")
                    c.pal_uv(p, stripe_col)
        if posts:
            for x in (x0 + 0.05, x1 - 0.05):
                c.add(L.member((x, y_wall + depth, 0), (x, y_wall + depth, z_wall - drop), 0.06, 0.06, c.sw("oak"), rng=c.rng))
        return
    n = max(1, int((x1 - x0) / 0.25))
    verts, uvs = [], []
    for j in range(3):
        f = j / 2
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            sag = math.sin(math.pi * i / n * n / 2) ** 2 * 0.0
            verts.append((x, y_wall + depth * f, z_wall - drop * f - 0.03 * math.sin(math.pi * f)))
            uvs.append(((x - x0) / 0.5, f * 0.999))
    verts, uvs = np.array(verts), np.array(uvs)
    tris = []
    for j in range(2):
        for i in range(n):
            a = j * (n + 1) + i
            tris += [(a, a + 1, a + n + 2), (a, a + n + 2, a + n + 1)]
    tris = np.array(tris)
    th = 0.02
    top = Part(verts + [0, 0, th], tris, c.sw(key), uvs[tris], 40)
    bot = Part(verts - [0, 0, th], tris[:, ::-1], c.sw(key), uvs[tris][:, ::-1], 40)
    c.add(L.merge([top, bot]), dice=None, form=0.0)
    # valance: scalloped strip hanging from the front edge
    yv = y_wall + depth
    zv = z_wall - drop
    for i in range(n):
        xa, xb = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
        q = L.quad((xa, yv + 0.01, zv - valance), (xb, yv + 0.01, zv - valance), (xb, yv + 0.01, zv), (xa, yv + 0.01, zv),
                   c.sw("team_plain"), uv=((0.1, 0.9), (0.9, 0.9), (0.9, 0.1), (0.1, 0.1)))
        mid = (xa + xb) / 2
        q.v[(q.v[:, 2] < zv - valance + 1e-6), 2] = zv - valance
        back = q.copy()
        back.t = back.t[:, ::-1]
        back.uv = back.uv[:, ::-1]
        back.move(0, -0.02, 0)
        c.add(L.merge([q, back]), dice=None, form=0.0)
    if posts:
        for x in (x0 + 0.05, x1 - 0.05):
            c.add(L.member((x, yv, 0), (x, yv, zv), 0.06, 0.06, c.sw("oak"), rng=c.rng))


def k_curio_cabinet(c):
    """Curio Cabinet (shop, 6x6 cells = 3 m): narrow shopfront house with a striped awning over the
    counter and its sign: a giant painted chest of small drawers standing out on the front."""
    t = 0.09
    x0, x1, y0, y1 = -0.92, 0.92, -1.25, 0.5
    zp, z1, z2 = 0.25, 1.3, 2.18
    jet = 0.12
    walls, _ = house(c, x0, x1, y0, y1, zp, [z1, z2], t, jetty=jet, ops={
        ("front", 0): [(0.24, 0.36, 0.0, 0.9, "door"), (0.68, 0.62, 0.32, 0.86, "window")],
        ("left", 0): [(0.5, 0.28, 0.35, 0.75, "window")], ("right", 0): [(0.5, 0.28, 0.35, 0.75, "window")],
        ("front", 1): [(0.5, 0.3, 0.15, 0.6, "window")],
        ("left", 1): [(0.5, 0.3, 0.15, 0.6, "window")], ("right", 1): [(0.5, 0.3, 0.15, 0.6, "window")],
        ("back", 1): [(0.5, 0.3, 0.15, 0.6, "window")]}, shutters=True)
    half = (x1 - x0) / 2
    pitch = math.radians(58)
    z_ridge = z2 + half * math.tan(pitch)
    ov = 0.16
    yf, yb = y1 + jet, y0 - jet
    gable_roof(c, yb - 0.16, yf + 0.18, 0.0, half + ov, z2 - ov * math.tan(pitch) * 0.6, z_ridge, th=0.11, sag=0.04,
               t=0.08, nu=8, nv=5, axis="y", cx=0.0)
    gable_infill(c, Wall((x1, yf), (-1, 0), (0, 1), x1 - x0), z2, z_ridge - 0.05, t, window_w=0.0)
    gable_infill(c, Wall((x0, yb), (1, 0), (0, -1), x1 - x0), z2, z_ridge - 0.05, t, window_w=0.24)
    # counter board under the shop window
    c.add(L.box(0.75, 0.3, 0.07, c.sw("oak"), center=(x1 - 0.68 * (x1 - x0), y1 + 0.13, zp + 0.3), chamfer=0.02), dice=None)
    awning(c, x0 - 0.02, x1 + 0.02, y1 + 0.02, z1 - 0.02, 0.55, 0.32, posts=False, stripes=True)
    # the sign: shelf brackets + giant chest of drawers in front of the upper storey
    for sx in (-0.42, 0.42):
        c.add(L.member((sx, yf, z2 - 0.05), (sx, yf + 0.42, z2 + 0.02), 0.07, 0.07, c.sw("oak"), rng=c.rng))
        c.add(L.member((sx, yf, z2 - 0.4), (sx, yf + 0.38, z2 - 0.02), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    c.add(L.box(1.1, 0.5, 0.06, c.sw("oak"), center=(0, yf + 0.22, z2 + 0.02), chamfer=0.015), dice=None)
    drawer_chest(c, (0.0, yf + 0.24, z2 + 0.12), w=1.05, h=0.82, d=0.42, cols=3, rows=3)
    pennant(c, (0.0, yb - 0.1, z_ridge - 0.06), 0.55, 0.5, 0.2, dirn=(1, -0.2), phase=0.6)
    barrel(c, (x0 - 0.18, y1 + 0.55, 0), r=0.15, h=0.34)
    crate(c, (x1 + 0.2, y1 + 0.62, 0), s=0.32, rz=15)
    crate(c, (x1 + 0.22, y1 + 0.62, 0.32), s=0.24, rz=40)
    return {"height_target": (3.2, 4.2)}


def k_lookout(c, gun=False):
    """Lookout (scout tower, 4x4 cells = 2 m): thin splayed timber tower, railed platform, steep
    pyramid roof on posts. gun=True: the Gun Tower upgrade (stone base, plank parapet with
    hook-guns, onion cap)."""
    zb = 1.05 if gun else 0.0
    zpl = 3.75 if not gun else 4.05
    if gun:
        plinth(c, -0.88, 0.88, -0.88, 0.88, zb, batter=0.1, chamfer=0.05)
    tower_frame(c, zpl - zb, 0.74 if not gun else 0.62, 0.48, levels=2 if not gun else 2, t=0.12, footing=not gun)
    if gun:
        # lift the frame onto the stone base
        for p in c.parts:
            if p.sw.key == "oak":
                p.v[:, 2] = zb + p.v[:, 2]
    half = 0.66 if not gun else 0.74
    platform(c, 0, 0, zpl, half, rail=not gun, rail_h=0.48)
    ladder(c, (0.0, 0.8 if not gun else 0.72, zb), (0.0, half + 0.02, zpl + 0.1))
    if not gun:
        zr = zpl + 0.88
        for sx in (-1, 1):
            for sy in (-1, 1):
                c.add(L.member((sx * (half - 0.05), sy * (half - 0.05), zpl + 0.1), (sx * (half - 0.05), sy * (half - 0.05), zr),
                               0.09, 0.09, c.sw("oak"), rng=c.rng))
        hip_roof(c, -half - 0.3, half + 0.3, -half - 0.3, half + 0.3, zr - 0.05, zr + 1.45, ridge_frac=0.0, th=0.1,
                 kick=0.18, sag=0.0, ridge_team=True, hip_w=0.08, finials=False)
        pennant(c, (0, 0, zr + 1.6), 0.6, 0.85, 0.3, dirn=(1, 0.4), phase=0.5, finial=True)
        for name, w in rect_walls(-half, half, -half, half).items():
            if name in ("front", "back"):
                banner(c, w.p(w.L / 2, zpl + 0.1 + 0.46, 0.05), w.L * 0.5, 0.42, normal=tuple(w.n), bar=False)
        # a shuttered lantern box hanging under the platform? keep the read clean: a horn on a hook
        return {"height_target": (6.0, 8.0)}
    # gun tower: plank parapet with gun loops and two hook-guns, onion cap
    ph = 0.62
    for name, w in rect_walls(-half, half, -half, half).items():
        p = L.box(w.L + 0.1, ph, 0.08, c.sw("planks"), chamfer=0.015)
        p.move(w.L / 2, ph / 2, 0.0)
        w.place(p, 0.0, zpl + 0.1, 0.0)
        c.add(p, dice=0.3)
        for s_ in (w.L * 0.3, w.L * 0.7):
            q = L.quad(w.p(s_ - 0.05, zpl + 0.35, 0.045), w.p(s_ + 0.05, zpl + 0.35, 0.045), w.p(s_ + 0.05, zpl + 0.55, 0.045),
                       w.p(s_ - 0.05, zpl + 0.55, 0.045), c.sw("pal"))
            c.P(_face_out(q, w), "#26221F", ao=False, min_shade=0.0)
        c.add(L.member(w.p(-0.05, zpl + 0.1 + ph + 0.03, 0.0), w.p(w.L + 0.05, zpl + 0.1 + ph + 0.03, 0.0), 0.08, 0.12, c.sw("oak"), rng=c.rng))
    for sx in (-0.25, 0.25):
        brl = L.lathe([(0.05, 0), (0.045, 0.7), (0.06, 0.72), (0.06, 0.78), (0.0, 0.78)], 8, c.sw("iron"))
        brl.rot(-80, 0, 0).move(sx, half - 0.25, zpl + 0.55)
        c.add(brl, dice=None)
    zr = zpl + 0.1 + ph + 0.62
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.add(L.member((sx * (half - 0.06), sy * (half - 0.06), zpl + 0.1), (sx * (half - 0.06), sy * (half - 0.06), zr),
                           0.1, 0.1, c.sw("oak"), rng=c.rng))
    hip_roof(c, -half - 0.22, half + 0.22, -half - 0.22, half + 0.22, zr - 0.08, zr + 0.42, ridge_frac=0.0, th=0.1,
             kick=0.12, sag=0.0, ridge_team=True, hip_w=0.13, finials=False)
    for name, w in rect_walls(-half, half, -half, half).items():
        banner(c, w.p(w.L * 0.5, zpl + 0.1 + ph + 0.02, 0.06), 0.46, 1.0, normal=tuple(w.n), bar=False)
    drum = L.lathe([(0.42, 0), (0.42, 0.22), (0.38, 0.26)], 12, c.sw("oak"))
    drum.move(0, 0, zr + 0.28)
    c.add(drum, dice=None, uvrot=True)
    onion_dome(c, (0, 0, zr + 0.52), 0.42, 1.15, finial_h=0.55, sides=14, repeat=1.4, ribs=6, tint=(0.75, 0.85, 0.85))
    return {"height_target": (6.0, 8.0)}


def k_gun_tower(c):
    return k_lookout(c, gun=True)


def k_walled_burg(c):
    """Walled Burg (T2 hall upgrade): ADD-ON pieces in the Moot Hall GLB's own space (8 m model):
    a ring of parked wagons as a low wall, stone corner buttresses for the stone ground floor, team
    banners on tall poles, and a taller onion dome enclosing the T1 turret (+14 % height)."""
    # ring of wagons (back and sides; the front stays open)
    spots = [(-3.42, -1.75, 92), (-3.45, 0.75, 86), (3.42, -1.75, 88), (3.45, 0.75, 94), (-1.45, -3.42, 2), (1.35, -3.45, -3)]
    for k, (x, y, rz) in enumerate(spots):
        wagon(c, (x, y, 0.0), rz=rz, length=1.95, width=0.82, h=0.55, wheel_r=0.46, team_band=True, shafts=False,
              four=False, cover=k in (1, 3, 4))
    # taller dome over the turret (turret axis ~ (1.86, 1.93), old dome top ~9.3 m, finial ~10.6 m)
    tx, ty = 1.86, 1.93
    drum = L.lathe([(1.02, 0.0), (1.0, 0.42), (0.96, 0.5)], 16, c.sw("plaster"))
    drum.move(tx, ty, 7.2)
    c.add(drum, dice=0.3)
    for k in range(8):
        a = k * math.pi / 4
        p0 = (tx + math.cos(a) * 1.02, ty + math.sin(a) * 1.02, 7.2)
        c.add(L.member(p0, (p0[0], p0[1], 7.68), 0.1, 0.1, c.sw("oak"), roll_up=(math.cos(a), math.sin(a), 0)))
    onion_dome(c, (tx, ty, 7.62), 0.98, 3.35, finial_h=0.9, sides=16, repeat=2.4, ribs=8, tint=(0.62, 0.74, 0.74))
    # stone corner buttresses (stone ground floor read)
    for (bx, by) in ((-3.32, -3.55), (3.22, -3.55), (-3.32, 2.95), (3.22, 2.95)):
        p = L.gbox(0.75, 0.75, 2.25, c.sw("rubble"), chamfer=0.06, center=(bx, by, 0), grid=0.45)
        top = p.v[:, 2] > 1.0
        p.v[top, 0] = bx + (p.v[top, 0] - bx) * 0.72
        p.v[top, 1] = by + (p.v[top, 1] - by) * 0.72
        p.box_uv()
        c.add(p, jit=0.03)
        cap = L.box(0.6, 0.6, 0.12, c.sw("roof"), center=(bx, by, 2.25), base=True, chamfer=0.03)
        c.add(cap, dice=None)
    # team banners on tall poles at the front corners and beside the back wagons
    for sx, x, y in ((-1, -3.55, 3.45), (1, 3.55, 3.45), (-1, -2.65, -3.75), (1, 2.65, -3.75)):
        ny = 1.0 if y > 0 else -1.0
        c.add(L.member((x, y, 0), (x, y, 5.6), 0.14, 0.14, c.sw("oak"), rng=c.rng, chamfer=0.02))
        c.add(L.box(0.5, 0.5, 0.25, c.sw("rubble"), center=(x, y, 0), base=True, chamfer=0.04), dice=None)
        banner(c, (x, y + 0.12 * ny, 5.35), 0.75, 2.0, normal=(0, ny))
        ball = L.lathe([(0, 0), (0.1, 0.05), (0.11, 0.15), (0.05, 0.25), (0, 0.32)], 8, c.sw("iron"))
        ball.move(x, y, 5.6)
        c.add(ball, dice=None)
    return {"height_target": (10.6, 12.2), "addon_of": "kingdom_moot_hall"}


# =============================================================================================
# clans modules
# =============================================================================================

def ribbon(c, path, width, key="team_plain", thick=0.012, normal_hint=(0, 0, 1), taper=0.0, **kw):
    """Double-sided cloth strip along a 3D path (streamers, felt ribbons); u along, v across."""
    path = np.asarray(path, float)
    S = len(path)
    T = np.zeros_like(path)
    T[1:-1] = path[2:] - path[:-2]
    T[0] = path[1] - path[0]
    T[-1] = path[-1] - path[-2]
    T = nrm(T)
    hint = np.asarray(normal_hint, float)
    verts, uvs = [], []
    for i in range(S):
        side = np.cross(T[i], hint)
        if np.linalg.norm(side) < 1e-6:
            side = np.cross(T[i], np.array([1.0, 0, 0]))
        side = nrm(side)
        w = width * (1 - taper * i / (S - 1))
        verts += [path[i] - side * w / 2, path[i] + side * w / 2]
        f = i / (S - 1)
        uvs += [(f, 1.0), (f, 0.0)]
    verts, uvs = np.array(verts), np.array(uvs)
    nrm_ = nrm(np.cross(verts[1] - verts[0], verts[2] - verts[0]))
    tris = []
    for i in range(S - 1):
        a, b, cc, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        tris += [(a, b, cc), (a, cc, d)]
    tris = np.array(tris)
    fn = L.face_normals(verts, tris)
    off = nrm(fn.mean(0)) * thick / 2
    front = Part(verts + off, tris, c.sw(key), uvs[tris], 60.0)
    back = Part(verts - off, tris[:, ::-1], c.sw(key), uvs[tris][:, ::-1], 60.0)
    q = L.merge([front, back])
    kw.setdefault("dice", None)
    kw.setdefault("form", 0.0)
    return c.add(q, **kw)


def streamer(c, attach, length, width, dirn=(1, 0), droop=0.45, wave=0.12, phase=0.0, key="team_plain", n=10):
    width = width * 1.35
    d = nrm(np.array([dirn[0], dirn[1], 0.0]))
    side = np.array([-d[1], d[0], 0.0])
    a = np.asarray(attach, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(a + d * length * t * (1 - 0.25 * t) - np.array([0, 0, droop * length * t * t])
                   + side * math.sin(t * 5.5 + phase) * wave * t)
    return ribbon(c, pts, width, key=key, normal_hint=side, taper=0.35)


def carved_mast(c, base, h, r0=0.11, r1=0.07, key="wood", cap="cone", bands=4, streamers=2, s_len=None, dirn=(1, 0.3),
                cap_key="saffron", phase=0.0):
    """Carved pole: tapering lathe with carved bulges, bronze bands, a felt cone (or bronze knob)
    cap and team felt streamers tied under it (no horse-hair tassels, clans 2.4)."""
    x, y, z = base
    prof = [(r0 * 1.15, 0.0), (r0, 0.12)]
    nb = bands
    for i in range(nb):
        zc = h * (0.22 + 0.62 * i / max(nb - 1, 1))
        rr = r0 + (r1 - r0) * zc / h
        prof += [(rr, zc - 0.09), (rr * 1.32, zc - 0.05), (rr * 1.32, zc + 0.05), (rr, zc + 0.09)]
    prof += [(r1, h)]
    m = L.lathe(prof, 8, c.sw(key))
    m.move(x, y, z)
    c.add(m, dice=None, uvrot=True, layer=0.0)
    for i in range(nb):
        if i % 2:
            continue
        zc = h * (0.22 + 0.62 * i / max(nb - 1, 1))
        rr = (r0 + (r1 - r0) * zc / h) * 1.36
        b = L.lathe([(rr, zc - 0.045), (rr * 1.05, zc), (rr, zc + 0.045)], 8, c.sw("bronze"))
        b.move(x, y, z)
        c.add(b, dice=None)
    top = z + h
    if cap == "cone":
        cn = L.lathe([(r1 * 2.6, 0.0), (r1 * 2.7, 0.05), (r1 * 0.9, 0.42), (0.0, 0.5)], 10, c.sw(cap_key))
        cn.move(x, y, top - 0.05)
        c.add(cn, dice=None, layer=1.0)
        kb = L.lathe([(0, 0), (0.04, 0.03), (0.035, 0.08), (0, 0.11)], 6, c.sw("bronze"))
        kb.move(x, y, top + 0.43)
        c.add(kb, dice=None)
    elif cap == "knob":
        kb = L.lathe([(0, 0), (r1 * 1.8, 0.06), (r1 * 1.9, 0.16), (r1 * 0.9, 0.26), (0, 0.3)], 8, c.sw("bronze"))
        kb.move(x, y, top)
        c.add(kb, dice=None)
    sl = s_len or h * 0.42
    for k in range(streamers):
        ang = math.atan2(dirn[1], dirn[0]) + (k - (streamers - 1) / 2) * 0.55
        streamer(c, (x, y, top - 0.12 - 0.1 * k), sl * (1 - 0.15 * k), 0.13, dirn=(math.cos(ang), math.sin(ang)),
                 phase=phase + k * 1.7)


def stone_ring(c, cx, cy, r, h=0.14, stretch=0.0, key="drystone", sides=20):
    p = L.lathe([(r + 0.06, 0.0), (r + 0.06, h * 0.55), (r + 0.01, h), (r - 0.12, h)], sides, c.sw(key), stretch=stretch,
                cap_top=True)
    p.move(cx, cy, 0)
    return c.add(p, dice=None, jit=0.015, layer=0.0)


def yurt(c, cx, cy, r, wall_h, roof_h, felt="teal", roof_felt=None, door=True, stretch=0.0, crown=True, band=True,
         ropes=True, lb=0.13, base_h=0.13, sides=20, door_w=None, team_w=0.17, rope_col="#E0A030", glow=True,
         roof_shape="dome", door_key="saffron"):
    """Felt yurt: stone ring, visible lattice band below a rolled felt skirt, felt wall, domed felt
    roof with a team felt band at its base, a bronze crown ring with a warm smoke-ring glow, saffron
    girth and roof ropes, a lattice-wood door frame with a saffron felt hanging (front = +y)."""
    roof_felt = roof_felt or felt
    a = stretch
    stone_ring(c, cx, cy, r, base_h, stretch=a, sides=sides)
    z0 = base_h
    lat = L.lathe([(r - 0.02, z0 - 0.02), (r - 0.02, z0 + lb + 0.03)], sides, c.sw("lattice"), stretch=a)
    lat.move(cx, cy, 0)
    c.add(lat, dice=None, layer=0.0)
    zs = z0 + lb
    wall = L.lathe([(r + 0.01, zs), (r * 1.022, (zs + wall_h) / 2), (r + 0.015, wall_h)], sides, c.sw(felt), stretch=a)
    wall.move(cx, cy, 0)
    c.add(wall, dice=0.45, layer=1.0)
    sk = L.lathe([(r - 0.01, zs - 0.035), (r + 0.05, zs - 0.01), (r + 0.06, zs + 0.035), (r + 0.01, zs + 0.07)], sides,
                 c.sw(felt), stretch=a)
    sk.move(cx, cy, 0)
    c.add(sk, dice=None, layer=1.0, tint=(0.85, 0.85, 0.85))
    rc = max(0.12, r * 0.17)
    if roof_shape == "tall":
        prof = [(r * 1.08, wall_h - 0.03), (r * 1.09, wall_h + 0.03), (r * 1.0, wall_h + 0.2 * roof_h),
                (r * 0.86, wall_h + 0.45 * roof_h), (r * 0.6, wall_h + 0.72 * roof_h), (r * 0.32, wall_h + 0.92 * roof_h),
                (rc, wall_h + roof_h)]
    else:
        prof = [(r * 1.08, wall_h - 0.03), (r * 1.09, wall_h + 0.03), (r * 0.98, wall_h + 0.24 * roof_h),
                (r * 0.78, wall_h + 0.52 * roof_h), (r * 0.5, wall_h + 0.8 * roof_h), (rc, wall_h + roof_h)]
    roof = L.lathe(prof, sides, c.sw(roof_felt), stretch=a)
    roof.move(cx, cy, 0)
    c.add(roof, dice=0.45, layer=1.0)
    ztop = wall_h + roof_h
    if band:
        # team felt band hugging the lower dome
        bp = []
        for (rr, zz) in prof[:3]:
            bp.append((rr + 0.025, zz))
        z_hi = wall_h + team_w
        t_ = (z_hi - prof[1][1]) / max(prof[2][1] - prof[1][1], 1e-6)
        r_hi = prof[1][0] + (prof[2][0] - prof[1][0]) * min(t_, 1.0) + 0.025
        bnd = L.lathe([(r * 1.105, wall_h - 0.05), (r * 1.115, wall_h + 0.03), (r_hi, z_hi)], sides, c.sw("team_band"),
                      stretch=a, repeat=0.8)
        normalize_v(bnd)
        bnd.uv[..., 1] = 1.0 - bnd.uv[..., 1]
        bnd.move(cx, cy, 0)
        c.add(bnd, dice=None, layer=1.0)
    if crown:
        ring = L.torus(rc, 0.045, c.sw("bronze"), segs=12, sides=5)
        ring.move(cx, cy, ztop + 0.02)
        if a > 0:
            ring.v[:, 0] = cx + (ring.v[:, 0] - cx) + np.sign(ring.v[:, 0] - cx) * a
        c.add(ring, dice=None, layer=1.0)
        cap = L.lathe([(rc * 0.95, 0.0), (rc * 0.7, 0.07), (0.0, 0.1)], 10, c.sw("ember" if glow else "bronze"), stretch=a)
        if glow:
            vv = cap.v[cap.t]
            cap.uv = np.stack([0.5 + vv[..., 0] / (2.4 * (rc + a)), 0.5 + vv[..., 1] / (2.4 * rc)], -1)
        cap.move(cx, cy, ztop - 0.04)
        c.add(cap, dice=None, ao=False, min_shade=1.0, form=0.0, layer=1.0)
        # four crown spokes crossing the opening (the classic roof-wheel read)
        if a > 0:
            for xx in np.linspace(-a, a, 4):
                c.add(L.member((cx + xx, cy - rc, ztop + 0.04), (cx + xx, cy + rc, ztop + 0.04), 0.035, 0.035, c.sw("wood")),
                      layer=1.0)
        else:
            for k in range(2):
                ang = k * math.pi / 2 + math.pi / 4
                d = np.array([math.cos(ang), math.sin(ang), 0.0]) * rc
                c.add(L.member(np.array([cx, cy, ztop + 0.04]) - d, np.array([cx, cy, ztop + 0.04]) + d, 0.035, 0.035,
                               c.sw("wood")), layer=1.0)
    if ropes:
        for zz in (zs + (wall_h - zs) * 0.32, zs + (wall_h - zs) * 0.72):
            rr = r * 1.024 + 0.012
            g = L.lathe([(rr, zz - 0.025), (rr + 0.012, zz), (rr, zz + 0.025)], sides, c.sw("pal"), stretch=a)
            g.move(cx, cy, 0)
            c.P(g, rope_col, dice=None, layer=1.0)
        nr = 8
        for k in range(nr):
            ang = (k + 0.5) * 2 * math.pi / nr
            pts = []
            for (rr, zz) in prof[2:]:
                x_ = math.cos(ang) * (rr + 0.02)
                x_ += a if math.cos(ang) >= 0 else -a
                pts.append((cx + x_, cy + math.sin(ang) * (rr + 0.02), zz))
            c.P(L.sweep(L.rect_profile(0.035, 0.03), np.array(pts), c.sw("pal")), rope_col, dice=None, layer=1.0)
    if door:
        dw = door_w or min(0.62, r * 0.6)
        dh = min(wall_h - zs - 0.02, 0.95)
        yd = cy + r + 0.03
        for sx in (-1, 1):
            c.add(L.member((cx + sx * dw / 2, yd, z0), (cx + sx * dw / 2, yd, zs + dh + 0.06), 0.07, 0.08, c.sw("wood")),
                  layer=0.0)
        c.add(L.member((cx - dw / 2 - 0.06, yd, zs + dh + 0.06), (cx + dw / 2 + 0.06, yd, zs + dh + 0.06), 0.09, 0.09,
                       c.sw("wood")), layer=0.0)
        hang = L.box(dw - 0.04, 0.04, dh, c.sw(door_key), center=(cx, yd + 0.01, z0 + (dh + lb) / 2 + 0.01))
        if door_key.startswith("team"):
            hang.uv = _uv_rect(L.box(dw - 0.04, 0.04, dh, c.sw(door_key)).rot(90, 0, 0), dw - 0.04, dh)
        c.add(hang, dice=None, layer=1.0)
        lin = L.box(dw + 0.16, 0.06, 0.12, c.sw("saffron"), center=(cx, yd + 0.04, zs + dh + 0.14), chamfer=0.02)
        c.add(lin, dice=None, layer=1.0, tint=(0.8, 0.8, 0.8))
    return ztop


def shell_dome(c, cx, cy, r, h, key="shell", sides=16, rim_key="drystone"):
    """Tortoise-shell dome: hex-plated shell on a low stone rim."""
    prof = [(r * 1.0, 0.0), (r * 1.02, 0.12 * h), (r * 0.94, 0.4 * h), (r * 0.72, 0.7 * h), (r * 0.4, 0.92 * h), (0.0, h)]
    d = L.lathe(prof, sides, c.sw(key), smooth=70)
    d.move(cx, cy, 0.1)
    c.add(d, dice=0.45, layer=1.0)
    stone_ring(c, cx, cy, r * 0.98, 0.14, key=rim_key, sides=sides)


def standing_stone(c, pos, h, w, d, rz=0.0, lean=(0.0, 0.0), glyph=True, seed=0):
    x, y, z = pos
    p = L.gbox(w, d, h, c.sw("stone"), center=(0, 0, 0), chamfer=0.05, grid=0.3)
    rng = np.random.default_rng(seed)
    zf = p.v[:, 2] / h
    p.v[:, 0] *= 1.0 - 0.28 * zf
    p.v[:, 1] *= 1.0 - 0.18 * zf
    top = zf > 0.7
    p.v[top, 2] -= (np.abs(p.v[top, 0]) / (w / 2)) ** 2 * h * 0.12 * rng.uniform(0.6, 1.4)
    p.v += L.noise_vec(p.v, 3.0, tuple(rng.uniform(0, 50, 3))) * np.array([0.04, 0.03, 0.03])
    p.box_uv()
    parts = [(p, None)]
    if glyph:
        gw_, gh_ = w * 0.72, h * 0.62
        q = L.quad((-gw_ / 2, d / 2 + 0.035, h * 0.22), (gw_ / 2, d / 2 + 0.035, h * 0.22),
                   (gw_ / 2 * 0.85, d / 2 + 0.03 - 0.01, h * 0.22 + gh_), (-gw_ / 2 * 0.85, d / 2 + 0.03 - 0.01, h * 0.22 + gh_),
                   c.sw("glyph"))
        q = _face_out(q, Wall((0, 0), (1, 0), (0, 1), 1))
        parts.append((q, "g"))
    for q, kind in parts:
        q.rot(lean[0], lean[1], 0).rot(0, 0, rz).move(x, y, z)
        c.add(q, dice=None, jit=0.0, layer=0.0)


def gong(c, center, r, facing=(0, 1), boss=True):
    """Bronze gong disc (rim, dished face, central boss), facing the 2D direction."""
    t = r * 0.06
    prof = [(0.0, -t), (r * 0.9, -t), (r, 0.0), (r * 0.97, t * 1.6), (r * 0.82, t * 1.2), (r * 0.3, t * 0.4)]
    if boss:
        prof += [(r * 0.2, t * 0.5), (r * 0.17, t * 2.2), (0.0, t * 2.6)]
    else:
        prof += [(0.0, t * 0.4)]
    g = L.lathe(prof, 16, c.sw("bronze"))
    g.rot(-90, 0, 0)          # face +y
    ang = math.degrees(math.atan2(facing[1], facing[0])) - 90
    g.rot(0, 0, ang).move(*center)
    c.add(g, dice=None, layer=1.0)
    return g


def gong_frame(c, base, width, height, gongs=1, gr=0.4, facing=(0, 1), team_cords=True):
    """Two carved posts, a crossbar with upturned ends, gongs hung on team-felt cords."""
    x, y, z = base
    ang = math.degrees(math.atan2(facing[1], facing[0])) - 90
    R = L.rot_matrix(0, 0, ang)
    o = np.array([x, y, z])
    ex = R @ np.array([1.0, 0, 0])
    for sx in (-1, 1):
        p0 = o + ex * sx * width / 2
        carved_mast(c, tuple(p0), height, r0=0.07, r1=0.055, bands=2, cap="knob", streamers=0)
    bar = []
    for i in range(9):
        t = i / 8 * 2 - 1
        bar.append(o + ex * t * (width / 2 + 0.22) + np.array([0, 0, height - 0.12 + 0.12 * t ** 4]))
    c.add(L.sweep(L.rect_profile(0.09, 0.1, 0.015), np.array(bar), c.sw("wood"), up=(0, 0, 1)), dice=None, uvrot=False, layer=0.0)
    c.add(L.member(o + ex * (-width / 2) + np.array([0, 0, height * 0.3]), o + ex * (width / 2) + np.array([0, 0, height * 0.3]),
                   0.06, 0.06, c.sw("wood")), layer=0.0)
    for k in range(gongs):
        u = (k + 0.5) / gongs - 0.5
        gc = o + ex * u * width * 0.92 + np.array([0, 0, height - 0.2 - gr * 1.15])
        gong(c, tuple(gc), gr, facing=facing)
        for sgn in (-1, 1):
            a = gc + ex * sgn * gr * 0.55 + np.array([0, 0, gr * 0.8])
            b = o + ex * (u * width * 0.92 + sgn * gr * 0.35) + np.array([0, 0, height - 0.17])
            if team_cords:
                ribbon(c, np.array([a, (a + b) / 2, b]), 0.06, key="team_plain", normal_hint=R @ np.array([0, 1.0, 0]))
            else:
                c.P(L.member(a, b, 0.025, 0.025, c.sw("pal")), "#E0A030")


def ring_fence(c, cx, cy, r, n=12, h=0.7, gap=None, rope_col="#E0A030", floor_key="clay"):
    """Round wrestling ring: carved posts, two sagging saffron rope rails, packed sand floor."""
    fl = L.lathe([(r + 0.05, 0.0), (r + 0.05, 0.03), (r - 0.05, 0.05), (0.0, 0.055)], 20, c.sw(floor_key))
    fl.move(cx, cy, 0)
    c.add(fl, dice=0.5, jit=0.0, tint=(1.12, 1.06, 0.95))
    angs = [2 * math.pi * k / n + math.pi / n for k in range(n)]
    for k, a in enumerate(angs):
        if gap is not None and abs(math.atan2(math.sin(a - gap), math.cos(a - gap))) < math.pi / n * 1.2:
            continue
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r, 0.0)
        m = L.lathe([(0.075, 0), (0.06, h), (0.085, h + 0.03), (0.0, h + 0.1)], 6, c.sw("wood"))
        m.move(*p)
        c.add(m, dice=None, uvrot=True, layer=0.0)
    for zz in (h * 0.45, h * 0.88):
        for k in range(n):
            a0, a1 = angs[k], angs[(k + 1) % n]
            if gap is not None:
                mid = math.atan2(math.sin((a0 + a1) / 2 + (math.pi if k == n - 1 else 0)), math.cos((a0 + a1) / 2 + (math.pi if k == n - 1 else 0)))
                if any(abs(math.atan2(math.sin(aa - gap), math.cos(aa - gap))) < math.pi / n * 1.2 for aa in (a0, a1)):
                    continue
            if a1 < a0:
                a1 += 2 * math.pi
            pts = []
            for i in range(5):
                t = i / 4
                a = a0 + (a1 - a0) * t
                pts.append((cx + math.cos(a) * (r + 0.02), cy + math.sin(a) * (r + 0.02), zz - 0.06 * math.sin(math.pi * t)))
            c.P(L.sweep(L.rect_profile(0.04, 0.04), np.array(pts), c.sw("pal"), cap0=False, cap1=False), rope_col, dice=None)


def mace_rack(c, center, rz=0.0, width=1.0, h=0.9, n=3):
    x, y, z = center
    parts = []
    for sx in (-1, 1):
        parts.append(L.member((sx * width / 2, 0, 0), (sx * width / 2, 0, h), 0.08, 0.08, c.sw("wood")))
    parts.append(L.member((-width / 2 - 0.08, 0, h), (width / 2 + 0.08, 0, h), 0.08, 0.1, c.sw("wood")))
    parts.append(L.member((-width / 2, 0, h * 0.25), (width / 2, 0, h * 0.25), 0.06, 0.06, c.sw("wood")))
    for p in parts:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p, layer=0.0)
    for i in range(n):
        u = (i + 0.5) / n - 0.5
        a = np.array([u * width * 0.85, 0.1, 0.0])
        b = np.array([u * width * 0.85, -0.04, h + 0.05])
        sh = L.member(a, b, 0.045, 0.045, c.sw("wood"))
        head = L.lathe([(0, 0), (0.09, 0.03), (0.11, 0.12), (0.09, 0.22), (0, 0.25)], 6, c.sw("bronze"))
        head.move(*(b + np.array([0, 0, -0.02])))
        for p in (sh, head):
            p.rot(0, 0, rz).move(x, y, z)
            c.add(p, dice=None)


def kiln(c, cx, cy, r, h):
    """Charcoal / casting kiln: concave clay cone, a glowing stoke-hole at the front, bronze vent ring
    with a glow inside."""
    prof = [(r * 1.04, 0.0), (r, 0.12 * h), (r * 0.82, 0.35 * h), (r * 0.55, 0.65 * h), (r * 0.32, 0.92 * h), (r * 0.3, h)]
    k = L.lathe(prof, 16, c.sw("clay"))
    k.move(cx, cy, 0)
    c.add(k, dice=0.4, jit=0.02, tint=(0.95, 0.85, 0.78))
    for zz in (0.3 * h, 0.62 * h):
        rr = np.interp(zz, [p[1] for p in prof], [p[0] for p in prof]) + 0.015
        b = L.lathe([(rr, zz - 0.04), (rr + 0.015, zz), (rr, zz + 0.04)], 16, c.sw("iron"))
        b.move(cx, cy, 0)
        c.add(b, dice=None)
    vent = L.torus(r * 0.3, 0.05, c.sw("bronze"), segs=12, sides=5)
    vent.move(cx, cy, h + 0.02)
    c.add(vent, dice=None)
    gd = L.lathe([(r * 0.28, 0.0), (0.0, 0.02)], 10, c.sw("ember"))
    vv = gd.v[gd.t]
    gd.uv = np.stack([0.5 + vv[..., 0] / (0.7 * r), 0.5 + vv[..., 1] / (0.7 * r)], -1)
    gd.move(cx, cy, h - 0.06)
    c.add(gd, dice=None, ao=False, min_shade=1.0, form=0.0)
    # stoke hole (front, +y)
    w = Wall((cx + r * 0.3, cy + r * 0.93), (-1, 0), (0, 1), r * 0.6)
    arch = [(0, 0.0), (r * 0.6, 0.0), (r * 0.6, h * 0.16), (r * 0.3, h * 0.24), (0, h * 0.16)]
    q = L.prism(arch, 0.0, 0.02, c.sw("ember"), chamfer=0.0, bottom=False)
    vv = q.v[q.t]
    q.uv = np.stack([0.15 + vv[..., 0] / (r * 0.6) * 0.7, 0.95 - vv[..., 1] / (h * 0.24) * 0.6], -1)
    w.place(q)
    c.add(q, dice=None, ao=False, min_shade=1.0, form=0.0, occ=False)
    lip = L.member(w.p(-0.04, h * 0.25, 0.04), w.p(r * 0.64, h * 0.25, 0.04), 0.09, 0.08, c.sw("clay"))
    c.add(lip, tint=(0.8, 0.7, 0.62))


def urn_tripod(c, pos, s=1.0):
    """Big round polished bronze urn with lid and spout on an iron tripod."""
    x, y, z = pos
    zh = 0.42 * s
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        c.add(L.member((x + math.cos(a) * 0.32 * s, y + math.sin(a) * 0.32 * s, z), (x + math.cos(a) * 0.14 * s,
                       y + math.sin(a) * 0.14 * s, z + zh), 0.04 * s, 0.04 * s, c.sw("iron")))
    ring = L.torus(0.17 * s, 0.025 * s, c.sw("iron"), segs=10, sides=4)
    ring.move(x, y, z + zh)
    c.add(ring, dice=None)
    prof = [(0.0, 0.0), (0.12, 0.0), (0.24, 0.12), (0.27, 0.26), (0.22, 0.42), (0.11, 0.5), (0.1, 0.56), (0.14, 0.6),
            (0.12, 0.64), (0.06, 0.7), (0.035, 0.76), (0.0, 0.79)]
    u = L.lathe([(a_ * s, b_ * s) for a_, b_ in prof], 14, c.sw("bronze"))
    u.move(x, y, z + zh - 0.02 * s)
    c.add(u, dice=None)
    sp = L.member((x + 0.18 * s, y + 0.12 * s, z + zh + 0.32 * s), (x + 0.36 * s, y + 0.26 * s, z + zh + 0.5 * s), 0.05 * s,
                  0.05 * s, c.sw("bronze"))
    c.add(sp, dice=None)
    for sgn in (-1, 1):
        hd = L.torus(0.07 * s, 0.018 * s, c.sw("bronze"), segs=8, sides=4).rot(90, 0, 0).rot(0, 0, 90)
        hd.move(x + sgn * 0.26 * s, y, z + zh + 0.36 * s)
        c.add(hd, dice=None)


def low_table(c, pos, w=0.7, d=0.45, h=0.32, cups=3, rz=0.0):
    x, y, z = pos
    parts = [L.box(w, d, 0.05, c.sw("wood"), chamfer=0.015, center=(0, 0, h))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(L.box(0.06, 0.06, h, c.sw("wood"), center=(sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), h / 2)))
    for p in parts:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p, dice=None)
    for k in range(cups):
        cu = L.lathe([(0.0, 0.0), (0.04, 0.0), (0.06, 0.07), (0.055, 0.075), (0.0, 0.03)], 8, c.sw("bronze"))
        u = (k + 0.5) / cups - 0.5
        cu.move(u * w * 0.75, (0.08 if k % 2 else -0.06), h + 0.025).rot(0, 0, rz).move(x, y, z)
        c.add(cu, dice=None)


def cushion(c, pos, key, r=0.24):
    b = L.blob(c.sw(key), radius=r, subdiv=1, scale=(1, 1, 0.42), seed=int(c.r(0, 999)), noise_amp=0.05, flat_bottom=0.0)
    b.move(*pos)
    c.add(b, dice=None)


def mirror_post(c, pos, h, facing_deg, tilt=40.0, mr=0.3):
    """Carved post with a yoke holding a bronze sun-mirror tilted to the sky."""
    x, y, z = pos
    carved_mast(c, pos, h, r0=0.08, r1=0.06, bands=2, cap=None, streamers=1, s_len=0.6,
                dirn=(math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))), phase=facing_deg)
    zc = z + h + mr * 0.7
    parts = []
    for sgn in (-1, 1):
        parts.append(L.member((sgn * (mr + 0.05), 0, h - 0.05), (sgn * (mr + 0.05), 0, h + mr * 0.8), 0.05, 0.05, c.sw("wood")))
    parts.append(L.member((-(mr + 0.08), 0, h - 0.04), ((mr + 0.08), 0, h - 0.04), 0.06, 0.06, c.sw("wood")))
    for p in parts:
        p.rot(0, 0, facing_deg - 90).move(x, y, z)
        c.add(p, dice=None)
    t = mr * 0.05
    prof = [(0.0, -t * 2), (mr * 0.9, -t), (mr, 0.0), (mr * 0.96, t * 1.8), (mr * 0.85, t * 1.2), (0.0, t * 0.6)]
    m = L.lathe(prof, 16, c.sw("bronze"))
    m.rot(-90 + tilt, 0, 0).rot(0, 0, facing_deg - 90).move(x, y, zc)
    c.add(m, dice=None, tint=(1.15, 1.08, 0.98))


def recurve_bow(c, center, span, facing_deg=90.0):
    """Large laminated recurve bow of wood and bronze on a swivel stock."""
    x, y, z = center
    n = 16
    pts = []
    for i in range(n + 1):
        t = i / n * 2 - 1
        bx = t * span / 2
        by = -0.16 * span * (1 - t * t) + 0.09 * span * max(0.0, abs(t) - 0.78) ** 1.0 * 5.0 * (abs(t) - 0.78)
        pts.append((bx, by, 0.0))
    pts = np.array(pts)
    sc = np.array([0.7 + 0.5 * (1 - abs(i / n * 2 - 1)) for i in range(n + 1)])
    bow = L.sweep(L.rect_profile(0.1, 0.12, 0.02), pts, c.sw("wood"), scales=sc, up=(0, 0, 1))
    parts = [(bow, None)]
    for sgn in (-1, 1):
        tip = L.lathe([(0.035, 0), (0.03, 0.09), (0.0, 0.12)], 6, c.sw("bronze")).rot(0, sgn * 90, 0)
        tip.move(sgn * span / 2, pts[-1 if sgn > 0 else 0][1], 0)
        parts.append((tip, None))
    string = L.member(pts[0] + np.array([0.02, 0, 0]), pts[-1] - np.array([0.02, 0, 0]), 0.018, 0.018, c.sw("pal"))
    parts.append((string, "#E9DDBF"))
    stock = L.box(0.1, span * 0.62, 0.09, c.sw("wood"), chamfer=0.02, center=(0, -span * 0.12, -0.02))
    parts.append((stock, None))
    grip = L.box(0.16, 0.12, 0.12, c.sw("bronze"), chamfer=0.02, center=(0, -0.16 * span, 0.0))
    parts.append((grip, None))
    for p, col in parts:
        p.rot(0, 0, facing_deg - 90).move(x, y, z)
        if col:
            c.P(p, col, dice=None)
        else:
            c.add(p, dice=None)
    post = L.lathe([(0.11, -0.45), (0.09, -0.05), (0.13, -0.04), (0.13, 0.0), (0.0, 0.0)], 8, c.sw("bronze"))
    post.move(x, y - 0.0, z - 0.06)
    c.add(post, dice=None)


def felt_panel(c, cx, cy, r, a0, a1, z0, z1, key="teal"):
    """Curved felt windbreak (arc between angles a0..a1 deg at radius r)."""
    n = max(3, int(abs(a1 - a0) / 15))
    ang = np.radians(np.linspace(a0, a1, n + 1))
    pts = np.stack([cx + np.cos(ang) * r, cy + np.sin(ang) * r, np.zeros(n + 1)], 1)
    path = pts
    p = L.sweep(L.rect_profile(0.04, z1 - z0), path + np.array([0, 0, (z0 + z1) / 2]), c.sw(key), up=(0, 0, 1))
    if key.startswith("team"):
        normalize_v(p)
    c.add(p, dice=None, layer=1.0)
    for a in ang[::2]:
        q = (cx + math.cos(a) * r, cy + math.sin(a) * r)
        c.add(L.member((q[0], q[1], z0 - 0.02), (q[0], q[1], z1 + 0.12), 0.05, 0.05, c.sw("wood")), layer=0.0)


def log_pile(c, center, length, rows, r=0.12, rz=0.0, key="bark"):
    """Pyramid pile of logs (both factions)."""
    log_stack(c, center, length, rows, r=r, rz=rz)


# =============================================================================================
# clans buildings
# =============================================================================================

def c_home_yurt(c):
    """Home Yurt (supply + worker garrison, 4x4 cells = 2 m): small round felt dome with a smoke ring
    and a rolled felt skirt (rolls up for Roll the Felt), a short streamer mast by the door."""
    ztop = yurt(c, 0.0, -0.08, 0.78, 0.82, 0.7, felt="teal", roof_felt="teal", lb=0.14, sides=18, door_w=0.42)
    carved_mast(c, (0.62, 0.66, 0.0), 1.95, r0=0.06, r1=0.045, bands=2, streamers=2, s_len=0.75, dirn=(1, 0.2))
    log_stack(c, (-0.55, 0.72, 0.0), 0.5, 2, r=0.065, axis="x")
    jar = L.lathe([(0.0, 0.0), (0.09, 0.0), (0.14, 0.12), (0.12, 0.26), (0.07, 0.32), (0.08, 0.36), (0.0, 0.36)], 10,
                  c.sw("clay"))
    jar.move(0.82, -0.62, 0)
    c.add(jar, dice=None, tint=(0.85, 0.7, 0.6))
    return {"height_target": (2.0, 2.8)}


def c_grapple_yard(c):
    """Grapple Yard (barracks, 8x8 cells = 4 m): a long yurt behind a round fenced wrestling ring,
    mace racks, two carved masts with team streamers at the ring's entrance."""
    yurt(c, 0.0, -1.12, 0.74, 0.98, 0.85, felt="teal", roof_felt="teal", stretch=0.9, sides=16, door_w=0.55, team_w=0.26,
         door_key="team_plain")
    ring_fence(c, -0.15, 0.82, 1.0, n=12, h=0.68, gap=math.pi / 2)
    for sx in (-1, 1):
        carved_mast(c, (-0.15 + sx * 0.5, 1.78, 0.0), 3.1, r0=0.1, r1=0.07, bands=4, streamers=2, s_len=1.1,
                    dirn=(1, -0.35), phase=sx)
    mace_rack(c, (1.55, 0.55, 0.0), rz=80, width=0.9, h=0.85)
    mace_rack(c, (1.55, -0.2, 0.0), rz=95, width=0.7, h=0.8, n=2)
    # bench + water barrel by the ring
    c.add(L.box(1.0, 0.28, 0.08, c.sw("wood"), chamfer=0.02, center=(-1.6, 0.6, 0.34)), dice=None)
    for sx in (-0.4, 0.4):
        c.add(L.box(0.1, 0.24, 0.32, c.sw("wood"), center=(-1.6, 0.6 + sx, 0.16)), dice=None)
    c.parts[-3].rot(0, 0, 90, pivot=(-1.6, 0.6, 0))
    for p in c.parts[-2:]:
        p.rot(0, 0, 90, pivot=(-1.6, 0.6, 0))
    return {"height_target": (3.0, 4.2)}


def c_naming_stones(c):
    """Naming Stones (hero altar, 6x6 cells = 3 m): a ring of rough standing stones carved with hail
    and wind glyphs (nothing hung on them, no faces), a flat naming stone at the centre, a frame of
    small bronze gongs beside them."""
    disc = L.lathe([(1.42, 0.0), (1.42, 0.06), (1.36, 0.1), (0.0, 0.1)], 22, c.sw("drystone"), cap_top=True)
    c.add(disc, dice=0.5, jit=0.02)
    angs = [150, 205, 255, 300, 345, 30]
    hs = [1.55, 1.85, 2.15, 1.9, 1.6, 1.35]
    for k, (a, h) in enumerate(zip(angs, hs)):
        ar = math.radians(a)
        p = (math.cos(ar) * 1.05, math.sin(ar) * 1.05 - 0.05, 0.05)
        rz = a + 90
        standing_stone(c, p, h, 0.5 + 0.08 * (k % 2), 0.32, rz=rz, lean=(c.r(-4, 4), c.r(-4, 4)), seed=k + 3)
    centre = L.lathe([(0.38, 0.0), (0.4, 0.1), (0.36, 0.17), (0.0, 0.18)], 12, c.sw("stone"))
    centre.move(0.0, -0.05, 0.08)
    c.add(centre, dice=None, jit=0.01)
    gong_frame(c, (0.98, 0.98, 0.0), 0.82, 1.75, gongs=3, gr=0.17, facing=(-0.35, 1))
    rug = L.lathe([(0.7, 0.115), (0.0, 0.118)], 18, c.sw("team_plain"))
    vv = rug.v[rug.t]
    rug.uv = np.stack([0.5 + vv[..., 0] / 1.5, 0.5 + vv[..., 1] / 1.5], -1)
    rug.scale(1.0, 0.62, 1.0).move(0.0, 0.62, 0.0)
    c.add(rug, dice=None, form=0.0)
    for sx in (-1, 1):
        carved_mast(c, (sx * 0.38, 1.22, 0.0), 2.5, r0=0.075, r1=0.055, bands=3, streamers=3, s_len=1.0,
                    dirn=(sx * 0.9, 0.15), phase=sx * 2)
    return {"height_target": (2.2, 3.0)}


def c_casting_pit(c):
    """Casting Pit (war mill + lumber drop-off, 6x6 cells = 3 m): a sunken stone-rimmed casting pit
    with molten bronze, a clay cone kiln, log stacks, a felt awning on poles."""
    px, py = -0.45, 0.45
    rim = L.lathe([(0.78, 0.0), (0.8, 0.14), (0.74, 0.24), (0.58, 0.24), (0.55, 0.1)], 18, c.sw("drystone"))
    rim.move(px, py, 0)
    c.add(rim, dice=None, jit=0.02)
    fl = L.lathe([(0.56, 0.06), (0.0, 0.06)], 14, c.sw("pal"))
    fl.move(px, py, 0)
    c.P(fl, "#2A2220", ao=False)
    mol = L.lathe([(0.3, 0.07), (0.0, 0.09)], 12, c.sw("ember"))
    vv = mol.v[mol.t]
    mol.uv = np.stack([0.5 + vv[..., 0] / 0.7, 0.5 + vv[..., 1] / 0.7], -1)
    mol.move(px, py, 0)
    c.add(mol, dice=None, ao=False, min_shade=1.0, form=0.0)
    cru = L.lathe([(0.33, 0.06), (0.34, 0.16), (0.3, 0.17)], 12, c.sw("clay"))
    cru.move(px, py, 0)
    c.add(cru, dice=None, tint=(0.7, 0.6, 0.55))
    kiln(c, 0.72, -0.5, 0.68, 2.05)
    # log stacks (lumber drop-off read)
    log_stack(c, (-0.65, -1.15, 0.0), 1.3, 4, r=0.1, axis="x")
    log_stack(c, (1.2, 0.95, 0.0), 0.8, 3, r=0.09, axis="y")
    # felt awning on two poles shading the pit; team valance
    ax0, ax1, ay0, ay1 = -1.42, -0.12, -0.72, -0.08     # lean-to over the mould bench (back left)
    for xx in (ax0 + 0.06, ax1 - 0.06):
        c.add(L.member((xx, ay1, 0.0), (xx, ay1, 1.25), 0.07, 0.07, c.sw("wood")))
        c.add(L.member((xx, ay0, 0.0), (xx, ay0, 1.6), 0.07, 0.07, c.sw("wood")))
    aw = L.plate((ax0 - 0.08, ay0 - 0.12, 1.62), (ax1 + 0.08, ay0 - 0.12, 1.62), (ax1 + 0.08, ay1 + 0.12, 1.25),
                 (ax0 - 0.08, ay1 + 0.12, 1.25), 0.03, c.sw("teal"), segs=(3, 2))
    aw.box_uv()
    c.add(aw, dice=None, layer=1.0)
    c.add(L.box(1.1, 0.4, 0.08, c.sw("wood"), chamfer=0.02, center=(-0.77, -0.4, 0.55)), dice=None)
    for xx in (-1.22, -0.32):
        c.add(L.box(0.08, 0.34, 0.55, c.sw("wood"), center=(xx, -0.4, 0.275)), dice=None)
    for k in range(3):
        c.add(L.box(0.22, 0.14, 0.09, c.sw("clay"), chamfer=0.02, center=(-1.1 + k * 0.32, -0.4, 0.63)), dice=None,
              tint=(0.75, 0.62, 0.55))
    for i in range(4):
        xa, xb = ax0 - 0.08 + (ax1 - ax0 + 0.16) * i / 4, ax0 - 0.08 + (ax1 - ax0 + 0.16) * (i + 1) / 4
        yv = ay1 + 0.13
        q = L.quad((xa, yv, 0.95), (xb, yv, 0.95), (xb, yv, 1.25), (xa, yv, 1.25), c.sw("team_plain"),
                   uv=((0.1, 0.95), (0.9, 0.95), (0.9, 0.05), (0.1, 0.05)))
        b2 = q.copy()
        b2.t = b2.t[:, ::-1]
        b2.uv = b2.uv[:, ::-1]
        b2.move(0, -0.02, 0)
        c.add(L.merge([q, b2]), dice=None, form=0.0)
    carved_mast(c, (1.25, -1.25, 0.0), 2.7, r0=0.08, r1=0.06, bands=3, streamers=2, s_len=1.0, dirn=(-0.3, 1))
    c.add(L.member((1.25 - 0.3, -1.25 + 0.06, 2.45), (1.25 + 0.3, -1.25 + 0.06, 2.45), 0.05, 0.05, c.sw("wood")))
    banner(c, (1.25, -1.25 + 0.1, 2.43), 0.5, 1.1, normal=(0, 1), bar=False)
    return {"height_target": (2.4, 3.2)}


def c_mirror_yurt(c):
    """Mirror Yurt (caster lodge, 8x8 cells = 4 m): a tall felt dome ringed by bronze sun-mirrors on
    tilting carved posts (nothing sewn or studded on the felt)."""
    ztop = yurt(c, 0.0, -0.1, 1.22, 1.12, 2.15, felt="teal", roof_felt="teal", sides=22, roof_shape="tall", door_w=0.6,
                team_w=0.34, door_key="team_plain")
    cap = L.lathe([(0.42, ztop - 0.36), (0.36, ztop - 0.12), (0.22, ztop + 0.02)], 16, c.sw("saffron"))
    cap.move(0.0, -0.1, 0.0)
    c.add(cap, dice=None, layer=1.0)
    kb = L.lathe([(0, 0), (0.12, 0.06), (0.13, 0.18), (0.06, 0.3), (0.0, 0.45)], 10, c.sw("bronze"))
    kb.move(0.0, -0.1, ztop + 0.08)
    c.add(kb, dice=None)
    for k, a in enumerate((25, 75, 125, 175, 225, 275, 325)):
        if 60 < a < 120:
            continue
        ar = math.radians(a)
        mirror_post(c, (math.cos(ar) * 1.62, -0.1 + math.sin(ar) * 1.55, 0.0), 2.05 + 0.25 * (k % 2), a, tilt=42.0, mr=0.3)
    return {"height_target": (3.6, 4.6)}


def c_bow_mast(c):
    """Bow-Mast (tower, 4x4 cells = 2 m): a tall carved mast with a round deck, a felt windbreak, a
    large laminated recurve bow of wood and bronze on a swivel, felt streamers and a felt cone cap."""
    stone_ring(c, 0.0, 0.0, 0.62, 0.22, sides=14)
    zd = 3.55
    carved_mast(c, (0.0, 0.0, 0.18), 5.45, r0=0.17, r1=0.1, bands=5, cap="cone", streamers=3, s_len=1.6, dirn=(1, 0.25),
                cap_key="saffron")
    # deck on struts
    deck = L.lathe([(0.82, zd - 0.06), (0.86, zd), (0.82, zd + 0.06)], 14, c.sw("wood"), cap_top=True, cap_bottom=True)
    c.add(deck, dice=None, layer=0.0)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c.add(L.member(d * 0.15 + np.array([0, 0, zd - 1.2]), d * 0.72 + np.array([0, 0, zd - 0.05]), 0.08, 0.08, c.sw("wood")),
              layer=0.0)
        c.add(L.member(d * 0.66 + np.array([0, 0, zd]), d * 0.66 + np.array([0, 0, zd + 0.7]), 0.06, 0.06, c.sw("wood")),
              layer=0.0)
    felt_panel(c, 0.0, 0.0, 0.74, 150, 390, zd + 0.06, zd + 0.36, key="teal")
    felt_panel(c, 0.0, 0.0, 0.745, 150, 390, zd + 0.36, zd + 0.62, key="team_band")
    rr = L.torus(0.74, 0.03, c.sw("pal"), segs=16, sides=4)
    rr.move(0, 0, zd + 0.66)
    c.P(rr, "#E0A030", dice=None)
    recurve_bow(c, (0.0, 0.5, zd + 0.66), 2.0, facing_deg=90)
    # ladder pegs up the mast
    for i in range(10):
        zz = 0.5 + i * 0.3
        a = (0.0, 0.17, zz)
        c.add(L.member(a, (0.0, 0.32, zz + 0.02), 0.04, 0.04, c.sw("wood")), layer=0.0)
    return {"height_target": (6.0, 8.0)}


def c_tea_tent(c):
    """Tea Tent (faction shop, 6x6 cells = 3 m): a striped saffron-and-teal yurt, a felt awning at the
    door, a big bronze urn on a tripod and bronze cups on a low table, felt cushions."""
    ztop = yurt(c, 0.0, -0.32, 1.0, 1.02, 1.42, felt="stripes", roof_felt="stripes", sides=20, door_w=0.55, team_w=0.26,
                door_key="team_plain")
    kb = L.lathe([(0, 0), (0.1, 0.05), (0.1, 0.14), (0.0, 0.3)], 8, c.sw("bronze"))
    kb.move(0.0, -0.32, ztop + 0.08)
    c.add(kb, dice=None)
    # awning: felt canopy on two carved poles over the door
    for sx in (-1, 1):
        carved_mast(c, (sx * 0.62, 1.12, 0.0), 1.35, r0=0.06, r1=0.05, bands=2, cap="knob", streamers=1 if sx > 0 else 0,
                    s_len=0.7, dirn=(1, 0.3))
    aw = L.plate((-0.75, 0.62, 1.42), (0.75, 0.62, 1.42), (0.75, 1.2, 1.32), (-0.75, 1.2, 1.32), 0.03, c.sw("saffron"))
    aw.box_uv()
    c.add(aw, dice=None, layer=1.0)
    for i in range(4):
        xa, xb = -0.75 + 1.5 * i / 4, -0.75 + 1.5 * (i + 1) / 4
        q = L.quad((xa, 1.21, 1.14), (xb, 1.21, 1.14), (xb, 1.21, 1.32), (xa, 1.21, 1.32), c.sw("team_plain"),
                   uv=((0.1, 0.95), (0.9, 0.95), (0.9, 0.05), (0.1, 0.05)))
        b2 = q.copy()
        b2.t = b2.t[:, ::-1]
        b2.uv = b2.uv[:, ::-1]
        b2.move(0, -0.02, 0)
        c.add(L.merge([q, b2]), dice=None, form=0.0)
    urn_tripod(c, (0.72, 1.0, 0.0), s=1.1)
    low_table(c, (-0.45, 1.05, 0.0), w=0.7, d=0.42, h=0.3, cups=3)
    cushion(c, (-1.0, 0.95, 0.0), "teal", 0.22)
    cushion(c, (-0.45, 1.5, 0.0), "saffron", 0.2)
    cushion(c, (0.05, 1.42, 0.0), "teal", 0.2)
    return {"height_target": (2.6, 3.4)}


def lattice_gallery(c, r_in, r_out, z, a0, a1, rail_h=0.5, posts_every=22.0, bracket_to=None):
    """Ring gallery (deck + lattice railing + brackets) between angles a0..a1 (deg) around (0, 0)."""
    n = max(4, int(abs(a1 - a0) / 8))
    ang = np.radians(np.linspace(a0, a1, n + 1))
    rm = (r_in + r_out) / 2
    path = np.stack([np.cos(ang) * rm, np.sin(ang) * rm, np.full(n + 1, z)], 1)
    deck = L.sweep(L.rect_profile(r_out - r_in, 0.1, 0.02), path, c.sw("wood"), up=(0, 0, 1))
    c.add(deck, dice=None, layer=0.0)
    rpath = np.stack([np.cos(ang) * (r_out - 0.03), np.sin(ang) * (r_out - 0.03), np.full(n + 1, z + 0.05 + rail_h / 2)], 1)
    rail = L.sweep(L.rect_profile(0.04, rail_h), rpath, c.sw("lattice"), up=(0, 0, 1), repeat=1.4)
    c.add(rail, dice=None, layer=0.0)
    tpath = np.stack([np.cos(ang) * (r_out - 0.03), np.sin(ang) * (r_out - 0.03), np.full(n + 1, z + 0.08 + rail_h)], 1)
    c.add(L.sweep(L.rect_profile(0.09, 0.07, 0.015), tpath, c.sw("wood"), up=(0, 0, 1)), dice=None, layer=0.0)
    np_ = max(2, int(abs(a1 - a0) / posts_every))
    for a in np.radians(np.linspace(a0, a1, np_ + 1)):
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c.add(L.member(d * (r_out - 0.03) + np.array([0, 0, z - 0.05]), d * (r_out - 0.03) + np.array([0, 0, z + 0.12 + rail_h]),
                       0.08, 0.08, c.sw("wood")), layer=0.0)
        if bracket_to:
            rb, zb = bracket_to
            c.add(L.member(d * (r_out - 0.1) + np.array([0, 0, z - 0.04]), d * rb + np.array([0, 0, zb]), 0.07, 0.07,
                           c.sw("wood")), layer=0.0)


def c_banner_shell(c):
    """Banner Shell (T2 hall upgrade): ADD-ON pieces in the Shell Hall GLB's own space (8 m model):
    tall felt banners on carved masts, a second gong frame at the door and a lattice gallery round the
    shell (+12 % height)."""
    lattice_gallery(c, 2.86, 3.42, 2.42, 118.0, 422.0, rail_h=0.46, bracket_to=(3.12, 1.62))
    for a in (118.0, 422.0):
        ar = math.radians(a)
        shell_dome(c, math.cos(ar) * 3.25, math.sin(ar) * 3.25, 0.42, 0.55, sides=12)
        p = c.parts[-2]
        p.v[:, 2] += 2.45
        c.parts[-1].v[:, 2] += 2.4
    for (x, y, h) in ((-2.62, -2.72, 6.2), (2.62, -2.72, 6.2), (-3.5, 1.45, 5.75), (3.5, 1.45, 5.75)):
        carved_mast(c, (x, y, 0.0), h, r0=0.13, r1=0.09, bands=4, cap="knob", streamers=0)
        out = nrm(np.array([x, y]))
        bar_a = np.array([x, y, h - 0.25]) - np.array([-out[1], out[0], 0]) * 0.42
        bar_b = np.array([x, y, h - 0.25]) + np.array([-out[1], out[0], 0]) * 0.42
        c.add(L.member(bar_a, bar_b, 0.07, 0.07, c.sw("wood")), layer=0.0)
        banner(c, (x + out[0] * 0.09, y + out[1] * 0.09, h - 0.27), 0.68, 2.55, normal=tuple(out), bar=False)
        c.add(L.box(0.5, 0.5, 0.2, c.sw("drystone"), center=(x, y, 0), base=True, chamfer=0.04), dice=None)
    gong_frame(c, (-1.98, 3.28, 0.0), 1.05, 2.2, gongs=1, gr=0.46, facing=(0.12, 1))
    return {"height_target": (5.73, 6.6), "addon_of": "clans_shell_hall"}


KINGDOM = {
    "kingdom_croft": dict(fn=k_croft, cells=(4, 4), role="supply (Croft)"),
    "kingdom_oath_hall": dict(fn=k_oath_hall, cells=(6, 6), role="hero altar (Oath Hall)"),
    "kingdom_drill_yard": dict(fn=k_drill_yard, cells=(8, 8), role="barracks (Drill Yard)"),
    "kingdom_timber_yard": dict(fn=k_timber_yard, cells=(8, 8), role="lumber drop-off (Timber Yard)"),
    "kingdom_foundry": dict(fn=k_foundry, cells=(6, 6), role="smithy (Foundry)"),
    "kingdom_collegium": dict(fn=k_collegium, cells=(8, 8), role="caster hall (Collegium)"),
    "kingdom_wainwright_yard": dict(fn=k_wainwright_yard, cells=(8, 8), role="siege workshop (Wainwright Yard)"),
    "kingdom_curio_cabinet": dict(fn=k_curio_cabinet, cells=(6, 6), role="faction shop (Curio Cabinet)"),
    "kingdom_lookout": dict(fn=k_lookout, cells=(4, 4), role="scout tower (Lookout)"),
    "kingdom_gun_tower": dict(fn=k_gun_tower, cells=(4, 4), role="gun tower (Lookout upgrade)"),
    "kingdom_walled_burg": dict(fn=k_walled_burg, cells=(10, 10), role="T2 hall upgrade: add-on to kingdom_moot_hall",
                                addon_of="kingdom_moot_hall"),
}
CLANS = {
    "clans_home_yurt": dict(fn=c_home_yurt, cells=(4, 4), role="supply + worker garrison (Home Yurt)"),
    "clans_grapple_yard": dict(fn=c_grapple_yard, cells=(8, 8), role="barracks (Grapple Yard)"),
    "clans_naming_stones": dict(fn=c_naming_stones, cells=(6, 6), role="hero altar (Naming Stones)"),
    "clans_casting_pit": dict(fn=c_casting_pit, cells=(6, 6), role="war mill + lumber drop-off (Casting Pit)"),
    "clans_mirror_yurt": dict(fn=c_mirror_yurt, cells=(8, 8), role="caster lodge (Mirror Yurt)"),
    "clans_bow_mast": dict(fn=c_bow_mast, cells=(4, 4), role="tower (Bow-Mast)"),
    "clans_tea_tent": dict(fn=c_tea_tent, cells=(6, 6), role="faction shop (Tea Tent)"),
    "clans_banner_shell": dict(fn=c_banner_shell, cells=(10, 10), role="T2 hall upgrade: add-on to clans_shell_hall",
                               addon_of="clans_shell_hall"),
}
ALL = {**KINGDOM, **CLANS}


# =============================================================================================
# build + CLI
# =============================================================================================

def build(aid, out_dir, scale=1.0):
    spec = ALL[aid]
    t0 = time.time()
    faction = aid.split("_")[0]
    c = Ctx(aid, faction, spec["cells"], scale)
    info = spec["fn"](c) or {}
    parts = c.parts
    for p in parts:
        if p.dice:
            L.refine(p, p.dice)
    L.jitter(parts, c.seed)
    v = np.concatenate([p.v for p in parts])
    lo, hi = v.min(0), v.max(0)
    for p in parts:   # nothing below ground
        p.v[:, 2] = np.maximum(p.v[:, 2], 0.0) if lo[2] < 0 else p.v[:, 2]
    H = float(hi[2])
    extras = {
        "vibecraft": {
            "id": aid, "kit": "tools/kits/buildings.py", "footprint_cells": list(spec["cells"]),
            "build_progress": "reveal bottom-up: discard fragments whose UV2.y > progress (+ noise band); "
                              "clans two-pass: UV2.x = 0 lattice/frame first, 1 felt/cover second",
        }
    }
    path = os.path.join(out_dir, aid + ".glb")
    st = L.export_glb(path, aid, parts, H, c.bake, extras=extras)
    v = np.concatenate([p.v for p in parts])
    lo, hi = v.min(0), v.max(0)
    rec = {
        "id": aid, "faction": faction, "role": spec.get("role", ""),
        "footprint_cells": list(spec["cells"]), "footprint_m": [round(c.fp[0], 3), round(c.fp[1], 3)],
        "height_m": round(H, 3), "bounds_m": {"x": [round(lo[0], 3), round(hi[0], 3)], "z_godot": [round(-hi[1], 3), round(-lo[1], 3)]},
        "tris": st["tris"], "materials": st["materials"], "file_bytes": os.path.getsize(path),
        "notes": " ".join((spec["fn"].__doc__ or "").split()), "seconds": round(time.time() - t0, 1),
    }
    if "height_target" in info:
        rec["height_target_m"] = list(info["height_target"])
    if spec.get("addon_of"):
        rec["addon_of"] = spec["addon_of"]
        rec["footprint_m"] = [8.0, 8.0]
        rec["placement"] = (f"add-on in the {spec['addon_of']}.glb model space (8 m model): same parent and transform as "
                            f"the T1 hall, show both after the upgrade")
    L.log(f"{aid}: {st['tris']} tris, H {H:.2f} m, {rec['file_bytes'] / 1e6:.2f} MB, {rec['seconds']} s")
    return rec


LINEUP_ROWS = [
    ["kingdom_moot_hall", "kingdom_walled_burg", "kingdom_croft", "kingdom_oath_hall", "kingdom_drill_yard",
     "kingdom_timber_yard"],
    ["kingdom_foundry", "kingdom_collegium", "kingdom_wainwright_yard", "kingdom_curio_cabinet", "kingdom_lookout",
     "kingdom_gun_tower"],
    ["clans_shell_hall", "clans_banner_shell", "clans_home_yurt", "clans_grapple_yard", "clans_naming_stones",
     "clans_casting_pit", "clans_mirror_yurt", "clans_bow_mast", "clans_tea_tent"],
]
TEAM_COLOURS = {"kingdom": "#285DE6", "clans": "#D8232A"}   # art bible 2.4 lobby rule: Royal Blue / Crimson
HALLS = {"kingdom_moot_hall": "kingdom_moot_hall", "kingdom_walled_burg": "kingdom_moot_hall",
         "clans_shell_hall": "clans_shell_hall", "clans_banner_shell": "clans_shell_hall"}


def render_lineup(out_png, model_dir, hall_scale=0.625, unit="assets/models/units/kingdom_infantry.glb", size=(2600, 1560)):
    """Line-up of every building (+ the AI halls) on meadow ground at the RTS pitch, a 1.75 m unit
    beside each, team colours per faction. hall_scale: the 8 m AI halls scaled to the faction-doc
    10x10-cell footprint (0.625) or native (1.0)."""
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    tmp = tempfile.mkdtemp(prefix="vc_lineup_")
    items, labels = [], []
    gap = 1.6
    rows = [[a for a in row if a in HALLS or (a in ALL and os.path.exists(os.path.join(model_dir, a + ".glb")))]
            for row in LINEUP_ROWS]
    extra = max(0.0, 8.0 * hall_scale - 5.0)
    z_rows = [0.0, 11.0 + extra, 22.0 + extra]
    widths = []
    for row in rows:
        tot = 0.0
        for aid in row:
            w = (10 * 0.5 * hall_scale / 0.625) if aid in HALLS else ALL[aid]["cells"][0] * 0.5
            tot += w + gap + 0.9
        widths.append(tot)
    maxw = max(widths)
    for r, row in enumerate(rows):
        x = widths[r] / 2
        for aid in row:
            fac = aid.split("_")[0]
            if aid in HALLS:
                w = d = 8.0 * hall_scale
            else:
                w, d = ALL[aid]["cells"][0] * 0.5, ALL[aid]["cells"][1] * 0.5
            cx = x - w / 2
            z = z_rows[r]
            glbs = []
            if aid in HALLS:
                glbs.append((os.path.join(model_dir, HALLS[aid] + ".glb"), hall_scale))
                if aid != HALLS[aid]:
                    glbs.append((os.path.join(model_dir, aid + ".glb"), hall_scale))
            else:
                glbs.append((os.path.join(model_dir, aid + ".glb"), 1.0))
            for g, sc in glbs:
                if not os.path.exists(g):
                    continue
                items.append({"glb": os.path.abspath(g), "pos": [cx, 0.0, z], "scale": sc, "team": TEAM_COLOURS[fac]})
            items.append({"glb": os.path.join(REPO, unit), "pos": [cx - w / 2 - 0.45, 0.0, z - d / 2 + 0.2],
                          "team": TEAM_COLOURS["kingdom"], "clip": "idle"})
            label = aid.replace("kingdom_", "").replace("clans_", "").replace("_", " ")
            sub = f"{ALL[aid]['cells'][0]}x{ALL[aid]['cells'][1]} cells" if aid in ALL and aid not in HALLS else (
                "AI hall" + (" + add-on" if aid in ALL else "") + (f", x{hall_scale:g}" if hall_scale != 1 else ""))
            labels.append({"label": label, "sub": sub, "world": [cx, 0.0, z - d / 2 - 0.9]})
            x -= w + gap + 0.9
    spec = {"out": os.path.join(tmp, "frame.png"), "anchors": os.path.join(tmp, "anchors.json"), "size": list(size),
            "pitch": 56.0, "fov": 21.0, "target": [0.0, 0.0, 12.6 + extra * 0.6], "distance": maxw * 1.66 + extra * 2.2,
            "ground": os.path.join(REPO, "assets/textures/terrain/gv_meadow.png"), "items": items, "labels": labels}
    sp = os.path.join(tmp, "spec.json")
    with open(sp, "w") as f:
        json.dump(spec, f)
    cmd, env = _godot_cmd("buildings_lineup.gd", sp)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=900)
    if "VC_LINEUP_OK" not in r.stdout:
        raise SystemExit("lineup render failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
    im = Image.open(spec["out"]).convert("RGB")
    with open(spec["anchors"]) as f:
        anchors = json.load(f)
    d = ImageDraw.Draw(im)
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    for a in anchors:
        for txt, fnt, dy in ((a["label"], f1, 0), (a.get("sub", ""), f2, 24)):
            if not txt:
                continue
            tw = d.textlength(txt, font=fnt)
            x, y = a["x"] - tw / 2, a["y"] + dy
            for ox in (-2, -1, 0, 1, 2):
                for oy in (-2, -1, 0, 1, 2):
                    d.text((x + ox, y + oy), txt, font=fnt, fill=(15, 15, 15))
            d.text((x, y), txt, font=fnt, fill=(250, 246, 235))
    title = (f"Vibecraft procedural buildings (tools/kits/buildings.py) next to the AI halls; RTS pitch 56 deg; "
             f"unit = kingdom_infantry 1.75 m; halls x{hall_scale:g}; team: kingdom Royal Blue, clans Crimson")
    d.rectangle([0, 0, im.width, 34], fill=(20, 22, 26))
    d.text((12, 6), title, font=f2, fill=(235, 235, 235))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    im.save(out_png, optimize=True)
    return out_png


def _godot_cmd(script, spec_path):
    env = dict(os.environ)
    lvp = "/usr/share/vulkan/icd.d/lvp_icd.json"
    if "VK_ICD_FILENAMES" not in env and os.path.exists(lvp):
        env["VK_ICD_FILENAMES"] = lvp
    cmd = []
    if not env.get("DISPLAY"):
        cmd += ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"]
    cmd += ["godot", "--rendering-driver", "vulkan", "--audio-driver", "Dummy", "--path", os.path.join(REPO, "tools/preview"),
            "-s", os.path.join(HERE, script), "--", "--spec", spec_path]
    return cmd, env


def team_coverage(ids, model_dir, yaws=(0, 90, 180, 270)):
    """Visible TEAM fraction of the silhouette from the RTS pitch (front view and the mean of four
    yaws). Add-ons are measured together with their T1 hall."""
    import tempfile
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="vc_mask_")
    shots, meta = [], []
    with open(os.path.join(model_dir, "manifest.json")) as f:
        man = json.load(f)["buildings"]
    for aid in ids:
        rec = man.get(aid)
        if rec is None:
            continue
        ext = max(rec["footprint_m"][0], rec["height_m"] * 0.8)
        if aid in HALLS:
            ext = max(8.0, rec["height_m"] * 0.8)
        glbs = [os.path.join(model_dir, aid + ".glb")]
        if aid in HALLS and HALLS[aid] != aid:
            glbs.insert(0, os.path.join(model_dir, HALLS[aid] + ".glb"))
        for y in yaws:
            out = os.path.join(tmp, f"{aid}_{y}.png")
            shots.append({"glbs": glbs, "glb": glbs[-1], "out": out, "yaw": y,
                          "target": [0.0, rec["height_m"] * 0.4, 0.0], "distance": ext * 2.6})
            meta.append((aid, y, out))
    spec = {"size": 384, "pitch": 56.0, "fov": 30.0, "shots": shots}
    sp = os.path.join(tmp, "spec.json")
    with open(sp, "w") as f:
        json.dump(spec, f)
    cmd, env = _godot_cmd("buildings_teammask.gd", sp)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=1200)
    if "VC_MASKS_OK" not in r.stdout:
        raise SystemExit("team mask render failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
    res = {}
    for aid, y, out in meta:
        a = np.asarray(Image.open(out).convert("RGB"), np.int32)
        red = ((a[..., 0] > 128) & (a[..., 1] < 100)).sum()
        green = ((a[..., 1] > 128) & (a[..., 0] < 100)).sum()
        res.setdefault(aid, {})[y] = red / max(red + green, 1)
    out = {}
    for aid, d in res.items():
        out[aid] = {"front": round(d[yaws[0]], 3), "mean_4_yaws": round(float(np.mean(list(d.values()))), 3)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="comma list of ids (default: all)")
    ap.add_argument("--out-dir", default=os.path.join(REPO, "assets/models/buildings"))
    ap.add_argument("--manifest", default=None, help="default: <out-dir>/manifest.json")
    ap.add_argument("--sheets", default=None, help="render a render_preview contact sheet per building here")
    ap.add_argument("--lineup", default=None, help="render the line-up PNG here")
    ap.add_argument("--hall-scale", type=float, default=0.625,
                    help="line-up scale of the 8 m AI halls (0.625 = faction-doc 10x10 cells, 1 = native)")
    ap.add_argument("--no-build", action="store_true", help="only render (sheets / line-up) existing GLBs")
    ap.add_argument("--coverage", action="store_true",
                    help="measure the visible TEAM fraction from the RTS pitch (Godot) into the manifest")
    args = ap.parse_args(L_argv())
    ids = [x for x in args.only.split(",") if x] or list(ALL)
    recs = []
    man_path = args.manifest or os.path.join(args.out_dir, "manifest.json")
    if not args.no_build:
        for aid in ids:
            recs.append(build(aid, args.out_dir))
        write_manifest(man_path, recs, partial=bool(args.only))
    if args.coverage:
        cov = team_coverage(ids, args.out_dir)
        with open(man_path) as f:
            man = json.load(f)
        for aid, cv in cov.items():
            man["buildings"][aid]["team_coverage_rts"] = cv
        with open(man_path, "w") as f:
            json.dump(man, f, indent=2)
            f.write("\n")
        for aid, cv in cov.items():
            L.log(f"team coverage {aid}: front {cv['front'] * 100:.1f} %, 4-yaw mean {cv['mean_4_yaws'] * 100:.1f} %")
    if args.lineup:
        L.log("line-up:", render_lineup(args.lineup, args.out_dir, hall_scale=args.hall_scale))
    if args.sheets:
        os.makedirs(args.sheets, exist_ok=True)
        glbs = [os.path.join(args.out_dir, a + ".glb") for a in ids]
        for a in ids:
            hall = ALL[a].get("addon_of")
            if hall and os.path.exists(os.path.join(args.out_dir, hall + ".glb")):
                glbs.append(combo_glb([os.path.join(args.out_dir, hall + ".glb"), os.path.join(args.out_dir, a + ".glb")],
                                      os.path.join(args.sheets, a + "_on_" + hall.split("_", 1)[1] + ".glb")))
        cmd = ["python3", os.path.join(REPO, "tools/render_preview.py")] + glbs + ["--size", "320", "-o"]
        cmd.append(args.sheets if len(glbs) > 1 else os.path.join(args.sheets, ids[0] + "_sheet.png"))
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        L.log("sheets:", args.sheets, "(render_preview exit %d)" % r.returncode)
    print(json.dumps({"built": [r["id"] for r in recs], "manifest": man_path}, indent=2))


def combo_glb(paths, out):
    """QA only: an add-on and its hall merged into one GLB (Blender re-export) for a contact sheet."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import vc_bpy as V
    V.reset_scene()
    with V.stdout_to_stderr():
        for p in paths:
            V.import_glb(p)
        bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_vertex_color="ACTIVE",
                                  export_all_vertex_colors=True)
    return out


def L_argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else argv[1:]


MANIFEST_INFO = {
    "generator": "tools/kits/buildings.py (procedural bpy kit, no paid generation)",
    "conventions": {
        "units": "metres, Y up (Godot), origin = footprint centre on the ground, door/front faces -Z",
        "footprint": "faction-doc cells x 0.5 m (kingdom.md 7.2, clans.md 7); heights per art bible 1.3 (10-cell column)",
        "materials": "<id> = opaque atlas of tileable swatches (cells 448 px + 32 px wrap padding); <id>_GLOW = windows / "
                     "embers / smoke-ring glow (emissive, raise emission at night); <id>_TEAM = light grey cloth, UnitView "
                     "multiplies albedo_color by the player colour. Primitive order GLOW, atlas, TEAM (Godot 4.7's glTF "
                     "import skips vertex_color_use_as_albedo on a mesh's first primitive; buildings without GLOW start "
                     "with a hidden 1 mm dummy triangle)",
        "COLOR_0": "RGB = painted AO (ray-cast crevices, ground contact) x top light x per-part tint; A = 1",
        "TEXCOORD_1": "x = build layer (0 frame / lattice / walls, 1 covering: roofs, felt), y = normalized height "
                      "(0 ground .. 1 top)",
    },
    "build_progress": {
        "approach": "no _construction meshes: a build_progress shader reveals the finished mesh bottom-up from UV2",
        "kingdom": "scaffold-raised: discard where UV2.y > progress (+ a ragged noise band and a glowing edge); "
                   "scaffold and ladders are particles / a separate shared prop",
        "clans": "Raising, two passes: layer 0 (lattice, masts, stone ring) reveals over progress 0..0.6, layer 1 (felt "
                 "walls and domes, team bands) over 0.4..1.0",
        "gdshader": "float p = mix(progress / 0.6, (progress - 0.4) / 0.6, step(0.5, UV2.x)); "
                    "if (UV2.y > clamp(p, 0.0, 1.0) + 0.03 * noise(VERTEX.xz * 4.0)) discard;",
    },
    "team_coverage": "team_coverage_rts = visible TEAM fraction of the silhouette from the 56 deg RTS pitch, front view and "
                     "mean of 4 yaws (art bible 3.1 asks 6-10 % for buildings; the kit aims at ~8-15 %)",
}


def write_manifest(path, recs, partial=False):
    data = dict(MANIFEST_INFO)
    data["buildings"] = {}
    if partial and os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            pass
    for k, v in MANIFEST_INFO.items():
        data[k] = v
    for r in recs:
        r = dict(r)
        r.pop("seconds", None)
        data["buildings"][r["id"]] = r
    data["buildings"] = dict(sorted(data["buildings"].items()))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
