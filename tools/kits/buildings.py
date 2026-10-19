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


def graded(img_fn, mean=None, sat_cap=0.65, v_floor=None):
    """Grade a procedural texture callable (faction-LUT stand-in)."""
    return lambda: L.cached(("graded", id(img_fn), mean, sat_cap, v_floor),
                            lambda: L.grade(img_fn(), mean, sat_cap, v_floor))


def kingdom_swatches():
    """Kingdom swatches, graded towards the kingdom palette (art bible 2.1) with saturation <= 65 %
    (bible 1.4, buildings) as the faction-LUT stand-in. repeat = metres per cell (every cell is
    repeat x DENSITY px, so texel density is the same everywhere); tiles = pattern copies per cell."""
    return {
        "plaster": Swatch("plaster", L.swatch_img(MAT + "kingdom_lime_plaster.png", "crossfade"), 3.0),
        "oak": Swatch("oak", L.swatch_img(MAT + "kingdom_dark_oak_beam.png", "crossfade", grade_to="#5A3A22",
                                          sat_cap=0.62), 2.2),
        "roof": Swatch("roof", L.swatch_img(MAT + "kingdom_burgundy_roof_tiles.png", "period", grade_to="#7B2C36",
                                            sat_cap=0.65), 2.4, tiles=2),
        "rubble": Swatch("rubble", L.swatch_img(MAT + "kingdom_rubble_stone.png", "crossfade"), 2.4),
        "scales": Swatch("scales", L.swatch_img(MAT + "kingdom_bronze_scale_roof.png", "period", grade_to="#7C5631",
                                                sat_cap=0.62, v_floor=0.5, sat=0.3), 2.8),
        "planks": Swatch("planks", L.swatch_img(MAT + "kingdom_painted_planks.png", "periodx", sat_cap=0.6), 1.5),
        "iron": Swatch("iron", L.tex_iron(), 1.0),
        "brick": Swatch("brick", L.tex_brick(), 1.6),
        "straw": Swatch("straw", L.tex_straw(), 1.2),
        "bark": Swatch("bark", L.swatch_img(TER + "bark_oak.png", "none", sat_cap=0.55), 1.2),
        "rings": Swatch("rings", L.tex_rings(), kind="decal", px=160),
        "wattle": Swatch("wattle", L.tex_wattle(), 0.9),
        "leaves": Swatch("leaves", graded(L.tex_leaves(), sat_cap=0.6), 1.6),
        "dirt": Swatch("dirt", L.swatch_img(TER + "gv_dirt.png", "none", sat_cap=0.45), 3.0),
        "pal": Swatch("pal", L.tex_palette(KPAL), kind="decal", px=64, sheet_key="pal"),
        "team": Swatch("team", L.tex_team_cloth(emblem="wheel"), kind="decal", group="team", sheet_key="team_wheel",
                       px=224),
        "team_plain": Swatch("team_plain", L.tex_team_cloth(seed=33), kind="decal", group="team", px=224),
        "team_band": Swatch("team_band", L.tex_team_band(), 0.8, group="team"),
        "window": Swatch("window", L.tex_window(), kind="decal", group="glow", px=128),
        "ember": Swatch("ember", L.tex_ember(), kind="decal", group="glow", px=128),
    }


def clans_swatches():
    """Clans swatches graded towards the clans palette (bible 2.2): ink-teal felt #1E5A60..#2F7E7E at
    V >= 38 %, lattice-wood #7A4A32 (never red-brown), warm bronze #A8743A; saturation <= 65 %."""
    teal = L.swatch_img(MAT + "clans_teal_felt.png", "period", grade_to="#24605F", sat_cap=0.65, v_floor=0.40)
    saffron = L.swatch_img(MAT + "clans_saffron_felt.png", "period", grade_to="#D29A3E", sat_cap=0.65)
    return {
        "teal": Swatch("teal", teal, 2.4),
        "saffron": Swatch("saffron", saffron, 1.2),
        "stripes": Swatch("stripes", L.tex_stripes(teal, saffron, stripes=4), 2.4),
        "lattice": Swatch("lattice", L.swatch_img(MAT + "clans_lattice_wood.png", "period", grade_to="#7A4A32",
                                                  sat_cap=0.6), 1.4),
        "shell": Swatch("shell", L.swatch_img(MAT + "clans_tortoise_shell.png", "crossfade"), 2.6),
        "bronze": Swatch("bronze", L.swatch_img(MAT + "clans_polished_bronze.png", "period", grade_to="#A8743A",
                                                sat_cap=0.65), 1.4),
        "wood": Swatch("wood", L.swatch_img(MAT + "kingdom_dark_oak_beam.png", "crossfade", grade_to="#6E4632",
                                            sat_cap=0.58), 2.0),
        "stone": Swatch("stone", L.tex_stone(), 1.6),
        "glyph": Swatch("glyph", L.tex_glyph_stone(), kind="decal", px=224),
        "drystone": Swatch("drystone", L.swatch_img(MAT + "neutral_drystone.png", "crossfade", sat_cap=0.3), 2.0),
        "clay": Swatch("clay", L.swatch_img(TER + "gv_cracked.png", "none", sat_cap=0.45), 2.0),
        "dirt": Swatch("dirt", L.swatch_img(TER + "gv_dirt.png", "none", sat_cap=0.45), 3.0),
        "bark": Swatch("bark", L.swatch_img(TER + "bark_oak.png", "none", sat_cap=0.55), 1.2),
        "rings": Swatch("rings", L.tex_rings(), kind="decal", px=160),
        "iron": Swatch("iron", L.tex_iron(), 1.0),
        "pal": Swatch("pal", L.tex_palette(CPAL), kind="decal", px=64, sheet_key="pal"),
        "team": Swatch("team", L.tex_team_cloth(emblem="gong"), kind="decal", group="team", sheet_key="team_gong",
                       px=224),
        "team_plain": Swatch("team_plain", L.tex_team_cloth(seed=33), kind="decal", group="team", px=224),
        "team_band": Swatch("team_band", L.tex_team_band(), 0.8, group="team"),
        "ember": Swatch("ember", L.tex_ember(), kind="decal", group="glow", px=128),
    }


PIPING = {"kingdom": "#EDE2C8", "clans": "#A8743A"}      # neutral piping round TEAM areas (bible 3.1 rule 4)
_SHEETS = {}


def sheets_for(faction):
    """Shared texture sheets: one atlas per faction + one TEAM and one GLOW sheet for both factions."""
    if faction not in _SHEETS:
        if "team" not in _SHEETS:
            k, c = kingdom_swatches(), clans_swatches()
            _SHEETS["team"] = L.Sheet("buildings_team", [s for s in list(k.values()) + list(c.values())
                                                         if s.group == "team"], width=512, fmt="png")
            _SHEETS["glow"] = L.Sheet("buildings_glow", [s for s in list(k.values()) + list(c.values())
                                                         if s.group == "glow"], width=512, fmt="png")
        sw = kingdom_swatches() if faction == "kingdom" else clans_swatches()
        _SHEETS[faction] = L.Sheet(f"{faction}_buildings_atlas", [s for s in sw.values() if s.group == "atlas"],
                                   width=2048, fmt="jpeg", quality=90)
    return {"atlas": _SHEETS[faction], "team": _SHEETS["team"], "glow": _SHEETS["glow"]}


# per-swatch defaults: (dice max edge m, jitter amplitude m, smoothing angle deg)
DEFAULTS = {
    "plaster": (None, 0.012, 30), "rubble": (None, 0.03, 40), "roof": (0.75, 0.02, 40),
    "oak": (None, 0.006, 25), "planks": (None, 0.006, 25), "scales": (None, 0.0, 60), "brick": (None, 0.012, 30),
    "iron": (None, 0.0, 35), "straw": (0.6, 0.03, 50), "bark": (None, 0.0, 50), "rings": (None, 0.0, 10),
    "wattle": (None, 0.008, 30), "leaves": (None, 0.0, 60), "dirt": (0.9, 0.0, 40), "pal": (None, 0.0, 35),
    "team": (None, 0.0, 40), "team_plain": (None, 0.0, 40), "team_band": (None, 0.0, 40),
    "window": (None, 0.0, 0), "ember": (None, 0.0, 30),
    "teal": (0.6, 0.012, 60), "saffron": (0.6, 0.012, 60), "stripes": (0.6, 0.012, 60),
    "lattice": (None, 0.004, 40), "shell": (0.6, 0.0, 60), "bronze": (None, 0.0, 50),
    "wood": (None, 0.006, 25), "stone": (None, 0.0, 40), "glyph": (None, 0.0, 40), "drystone": (0.7, 0.025, 40),
    "clay": (0.7, 0.02, 50),
}


TEAM_MIN_SHADE = 0.8


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
        self.anchors = {}
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
        if p.sw.group == "team":
            # painted AO never drags team cloth below the bible's 50 % team value floor (1.4)
            p.min_shade = max(p.min_shade, TEAM_MIN_SHADE)
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


def wall_prism(c, wall, outline_sz, d0, d1, key, chamfer=0.02, grid=0.6, **kw):
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
    p = L.prism(ol, z0, z0 + h, c.sw(key), chamfer=chamfer, grid=0.6, bottom=False, cap_grid=None)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    top = p.v[:, 2] > z0 + h * 0.5
    p.v[top, 0] = cx + (p.v[top, 0] - cx) * (1 - batter)
    p.v[top, 1] = cy + (p.v[top, 1] - cy) * (1 - batter)
    p.box_uv()
    return c.add(p, **kw)


def timber_wall(c, wall, z0, z1, t, openings=(), bay=0.75, braces=True, rail=True, key="oak", depth=None,
                corner=True, simple=False):
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
    if simple:
        # walls the fixed RTS camera never shows (the back): sill, plate and posts only
        bay = max(bay, 1.2)
        braces = False
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


def door_(c, wall, s, zb, w, h, key="planks", arch=False):
    """Plank door set into the wall, iron straps, a step."""
    th = 0.06
    p = L.box(w, h, th, c.sw(key), chamfer=0.01)
    p.move(0, h / 2, 0)
    wall.place(p, s, zb, 0.0)
    c.add(p, dice=None, uvrot=True)
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


def gable_roof(c, x0, x1, yc, half, z_eave, z_ridge, th=0.14, sag=None, flare=0.12, kick=0.05, nu=10, nv=6,
               key="roof", ridge_team=True, soffit=False, barge=True, t=0.14, ridge_key="team_band",
               axis="x", cx=0.0, eave_jit=0.035, trim=0.11, ridge_w=None):
    """Thick gable roof, ridge along x from x0..x1 (incl. overhang) at y = yc; eaves at yc +- half.
    axis='y' builds it rotated (ridge along y, about the vertical axis through (cx, yc)), so the gables
    face +-y (the front). Hand-made read: the ridge sags `sag` m (default 4.5 cm per metre of ridge),
    the eave line wanders by +-eave_jit, chunky eave trim boards (trim m) and bargeboards (t m) stand
    proud of the tiles so they show from the high camera."""
    sw = c.sw(key)
    rep = sw.repeat
    Lx = x1 - x0
    xm = (x0 + x1) / 2
    if sag is None:
        sag = min(0.26, 0.045 * Lx)
    ph = c.r(0, 6.28)
    ph2 = c.r(0, 6.28)

    def eave_off(x, side):
        return eave_jit * (0.6 * math.sin(2.1 * x + ph + side) + 0.4 * math.sin(5.3 * x + ph2 - side))

    def surf(x, f, side):
        xr = 2 * (x - xm) / Lx
        zf = f + flare * f * (1 - f)
        z = z_ridge - (z_ridge - z_eave) * zf
        z += -sag * (1 - xr * xr) * (1 - f * 0.6)
        z += kick * (xr ** 4) * f * f
        z += eave_off(x, side) * f ** 3
        y = yc + side * (half * f + 0.5 * eave_off(x * 1.3, -side) * f ** 3)
        return (x, y, z)

    slope_len = math.hypot(half, z_ridge - z_eave)
    # grid lines also on every tile line (u = k, v = k), so the atlas mapping needs no extra cuts
    xs = list(x0 + Lx * np.arange(nu + 1) / nu)
    for k in range(1, int(Lx / rep) + 1):
        xt = x0 + k * rep
        if xt < x1 - 0.05:
            j = int(np.argmin([abs(x - xt) for x in xs[1:-1]])) + 1 if nu > 1 else None
            if j is not None and abs(xs[j] - xt) < 0.5 * Lx / nu:
                xs[j] = xt
            else:
                xs.append(xt)
    xs = sorted(xs)
    fs = list(np.arange(nv + 1) / nv)
    for k in range(1, int(slope_len / rep) + 1):
        ft = k * rep / slope_len
        if ft < 0.98:
            j = int(np.argmin([abs(f - ft) for f in fs[1:-1]])) + 1 if nv > 1 else None
            if j is not None and abs(fs[j] - ft) < 0.5 / nv:
                fs[j] = ft
            else:
                fs.append(ft)
    fs = sorted(fs)
    nu, nv = len(xs) - 1, len(fs) - 1
    top_v, grids = [], []
    for side in (1, -1):
        base = len(top_v)
        for f in fs:
            for x in xs:
                top_v.append(surf(x, f, side))
        grids.append(base)
    top_v = np.array(top_v, float)
    parts = []
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
                    uvs.append([((xs[(k - base) % (nu + 1)] - x0) / rep * side,
                                 (slope_len * fs[(k - base) // (nu + 1)]) / rep) for k in tri])
        parts.append(Part(top_v, np.array(tris), sw, np.array(uvs), 40.0))
    roof_top = L.merge(parts)
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
                q = L.quad(bot[a], bot[b], top_v[b], top_v[a], sw, uv=((0, 0), (0.3, 0), (0.3, 0.1), (0, 0.1)))
                mid = (top_v[a] + top_v[b]) / 2
                out = mid - np.array([xm, yc, mid[2]])
                out[2] = 0
                fnrm = np.cross(q.v[1] - q.v[0], q.v[3] - q.v[0])
                if np.dot(fnrm, out) < 0:
                    q.t = q.t[:, ::-1]
                    q.uv = q.uv[:, ::-1]
                rimparts.append(q)
    rim = L.merge(rimparts)
    rim.box_uv(rep)
    rim.faceted = True
    rim.tint = hexcol("#8A6A60")
    out = [c.add(roof_top, layer=1.0, dice=None), c.add(rim, dice=None, layer=1.0)]
    if soffit:
        st = []
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
        out.append(c.add(sp, dice=0.6, layer=1.0, ao_mul=1.0, form=0.0))
    if trim:
        # chunky eave trim board along each eave (sits on the tile edge, shows from above)
        for gi, side in enumerate((1, -1)):
            base = grids[gi]
            pts = np.array([top_v[base + nv * (nu + 1) + i] for i in range(nu + 1)])
            pts = pts + np.array([0, side * 0.02, -th * 0.35])
            tb = L.sweep(L.rect_profile(trim * 0.9, trim + th * 0.6), pts, c.sw("oak"), up=(0, 0, 1))
            out.append(c.add(tb, dice=None, layer=1.0, jit=0.0))
    if ridge_team:
        xs = np.linspace(x0 - 0.02, x1 + 0.02, nu + 1)
        path = []
        for x in xs:
            xr = 2 * (x - xm) / Lx
            path.append((x, yc, z_ridge - sag * (1 - xr * xr) + 0.015))
        w = ridge_w or max(0.14, t * 1.25)
        prof = np.array([(w * 0.3, w * 0.62), (0.0, w * 0.55), (-w * 0.5, 0.0), (0.0, -w * 0.55),
                         (w * 0.3, -w * 0.62)])
        rp = L.sweep(prof, path, c.sw(ridge_key), up=(0, 1, 0))
        normalize_v(rp)
        out.append(c.add(rp, layer=1.0))
    if barge:
        for xe in (x0 + t * 0.4, x1 - t * 0.4):
            for side in (1, -1):
                pts = [np.array(surf(xe, f, side)) + np.array([0, 0, t * 0.3]) for f in (0.0, 0.5, 1.0)]
                for k in range(2):
                    a, b = pts[k], pts[k + 1]
                    out.append(c.add(L.member(a, b, t * 0.9, t * 1.25, c.sw("oak"), rng=c.rng, roll_up=(1, 0, 0))))
    if axis == "y":
        for p in out:
            p.v = p.v - np.array([cx, yc, 0])
            p.rot(0, 0, 90)
            p.v = p.v + np.array([cx, yc, 0])
    return out


def roof_fit(zw, hw, ov, pitch_deg, th, ridge_len, flare=0.12):
    """(z_eave, z_ridge) of a gable_roof whose underside clears walls of half-width hw and top zw
    (accounts for the flare and the default ridge sag)."""
    tp = math.tan(math.radians(pitch_deg))
    sag = min(0.26, 0.045 * ridge_len)
    f = hw / (hw + ov)
    zf = f + flare * f * (1 - f)
    rise = (hw + ov) * tp
    # top surface at the wall line must sit th + 4 cm above the wall even where the ridge sags most
    z_ridge = zw + th + 0.04 + sag * (1 - 0.6 * f) + rise * zf
    return z_ridge - rise, z_ridge


def roof_z(x_or_off, half, z_eave, z_ridge, flare=0.12):
    """Height of a gable_roof slope (no sag) at distance x_or_off from the ridge line."""
    f = min(1.0, abs(x_or_off) / max(half, 1e-6))
    zf = f + flare * f * (1 - f)
    return z_ridge - (z_ridge - z_eave) * zf


def pbox(c, sx, sy, sz, key, center=(0, 0, 0), base=True, chamfer=0.03, taper=0.05, jit=None, rz=0.0, grid=None,
         **kw):
    """Chunky prop block: chamfered on every edge, a little narrower at the top, jittered (never a
    clean CAD box)."""
    x, y, z = center
    z0 = z if base else z - sz / 2
    ol = L.rect_profile(sx, sy, min(chamfer, sx * 0.3, sy * 0.3))
    p = L.prism(ol, z0, z0 + sz, c.sw(key), chamfer=chamfer, grid=grid)
    if taper:
        k = 1.0 - taper * np.clip((p.v[:, 2] - z0) / max(sz, 1e-6), 0, 1)
        p.v[:, 0] *= k
        p.v[:, 1] *= k
    if rz:
        p.rot(0, 0, rz)
    p.move(x, y, 0)
    p.box_uv()
    if jit is None:
        jit = min(0.03, 0.025 * min(sx, sy, sz) + 0.004)
    return c.add(p, jit=jit, **kw)


def gable_wall(c, wall, z0, z_eave, z_apex, t, door=None, windows=(), key="plaster", timbers=True, team_shutters=True,
               apex_window=None):
    """Kingdom gable-front wall: plaster pentagon (eave walls + gable triangle up to the roof) in a
    timber frame, a door that may rise above the eave line (doors stay ~2 m for 1.75 m units), shuttered
    windows. door = (s, w, h); windows = [(s, zb, zt, w)]; apex_window = (zb, zt, w) in the gable."""
    Lw = wall.L
    ol = [(0.0, z0), (Lw, z0), (Lw, z_eave), (Lw / 2, z_apex), (0.0, z_eave)]
    wall_prism(c, wall, ol, -0.06, 0.0, key, chamfer=0.0, grid=0.5)
    if not timbers:
        return
    dep = t * 0.8
    o = dep / 2 - 0.015
    sw = c.sw("oak")

    def mem(s0, a, s1, b, w=t, d=dep, oo=o):
        p = L.member(wall.p(s0, a, oo), wall.p(s1, b, oo), w, d, sw, rng=c.rng, roll_up=(wall.n[0], wall.n[1], 0))
        p.rot_axis((wall.n[0], wall.n[1], 0.0), c.r(-1.2, 1.2), pivot=p.v.mean(0))
        return c.add(p)

    mem(0, z0 + t / 2, Lw, z0 + t / 2, w=t * 1.15, d=dep * 1.05)
    for s_ in (t * 0.55, Lw - t * 0.55):
        mem(s_, z0, s_, z_eave + t * 0.3, w=t * 1.2, d=dep * 1.1)
    # rafters along the gable edges
    for s_a, s_b in ((0.0, Lw / 2), (Lw, Lw / 2)):
        mem(s_a, z_eave - t * 0.2, s_b, z_apex - t * 0.6, w=t * 1.05)
    ds, dw, dh = door if door else (None, 0.0, 0.0)
    gaps = []
    if door:
        gaps.append((ds - dw / 2 - t, ds + dw / 2 + t))
    # girt at the eave line, broken by the door
    segs = [(0.0, Lw)]
    for g0, g1 in gaps:
        nsegs = []
        for a, b in segs:
            if g1 <= a or g0 >= b:
                nsegs.append((a, b))
            else:
                if g0 > a:
                    nsegs.append((a, g0))
                if g1 < b:
                    nsegs.append((g1, b))
        segs = nsegs
    for a, b in segs:
        if b - a > t:
            mem(a, z_eave - t / 2, b, z_eave - t / 2, w=t * 1.05)
    if door and dh + z0 > z_eave - t:
        zl = z0 + dh + t / 2
        # how high the gable is at the door edges
        for sgn in (-1, 1):
            se = ds + sgn * (dw / 2 + t / 2)
            mem(se, z0 + t, se, zl, w=t)
        mem(ds - dw / 2 - t, zl, ds + dw / 2 + t, zl, w=t * 1.1)
        kp0 = zl + t / 2
    else:
        kp0 = z_eave
    if door:
        door_(c, wall, ds, z0, dw, dh)
        if dh + z0 <= z_eave - t:
            for sgn in (-1, 1):
                se = ds + sgn * (dw / 2 + t / 2)
                mem(se, z0 + t, se, z_eave - t, w=t)
            mem(ds - dw / 2 - t, z0 + dh + t / 2, ds + dw / 2 + t, z0 + dh + t / 2, w=t * 1.05)
    # king post + collar braces in the gable
    if apex_window is None:
        mem(Lw / 2, kp0, Lw / 2, z_apex - t * 0.8, w=t)
    hz = z_eave + (z_apex - z_eave) * 0.45
    hw = (Lw / 2) * (1 - 0.45)
    if not door or kp0 < hz - t:
        mem(Lw / 2 - hw + t * 0.4, hz, Lw / 2 + hw - t * 0.4, hz, w=t * 0.9)
    for sgn in (-1, 1):
        mem(Lw / 2 + sgn * Lw * 0.14, kp0 + t * 0.4 if kp0 < hz else hz, Lw / 2 + sgn * Lw * 0.36,
            z_eave + t * 0.4, w=t * 0.85)
    for (s_, zb, zt, w_) in windows:
        window(c, wall, s_, zb, zt, w_, shutters=team_shutters)
        for sgn in (-1, 1):
            mem(s_ + sgn * (w_ / 2 + t / 2), zb - t * 0.5, s_ + sgn * (w_ / 2 + t / 2), zt + t * 0.5, w=t * 0.9)
        mem(s_ - w_ / 2 - t, zb - t / 2, s_ + w_ / 2 + t, zb - t / 2, w=t * 0.95, d=dep * 1.25, oo=o + 0.02)
        mem(s_ - w_ / 2 - t, zt + t / 2, s_ + w_ / 2 + t, zt + t / 2, w=t)
    if apex_window:
        zb, zt, w_ = apex_window
        window(c, wall, Lw / 2, zb, zt, w_, shutters=False)
        for sgn in (-1, 1):
            mem(Lw / 2 + sgn * (w_ / 2 + t / 2), zb - t * 0.5, Lw / 2 + sgn * (w_ / 2 + t / 2), zt + t * 0.5, w=t * 0.9)
        mem(Lw / 2 - w_ / 2 - t, zb - t / 2, Lw / 2 + w_ / 2 + t, zb - t / 2, w=t * 0.95)
        mem(Lw / 2 - w_ / 2 - t, zt + t / 2, Lw / 2 + w_ / 2 + t, zt + t / 2, w=t)


def dormer(c, base, facing, w=0.8, h=0.75, depth=1.3, rise=0.45, team_shutters=False):
    """Small gabled dormer: front-bottom centre `base` (on the roof slope), facing the 2D direction
    `facing`; its body runs `depth` m back into the roof."""
    f2 = nrm(np.array(facing, float))
    ang = math.degrees(math.atan2(f2[1], f2[0])) - 90.0
    x, y, z = base
    body = L.prism(L.rect_profile(w, depth), 0.0, h, c.sw("plaster"), chamfer=0.0, grid=0.5)
    body.move(0, -depth / 2, 0).rot(0, 0, ang).move(x, y, z - 0.25)
    body.box_uv()
    c.add(body)
    wl = Wall((x, y), (-f2[1], f2[0]), (f2[0], f2[1]), 1.0)
    wl.O = np.array([x, y]) - wl.e * (w / 2)
    wl.L = w
    for s_ in (0.05, w - 0.05):
        c.add(L.member(wl.p(s_, z - 0.25, 0.03), wl.p(s_, z + h, 0.03), 0.09, 0.08, c.sw("oak"), rng=c.rng))
    window(c, wl, w / 2, z + 0.08, z + h - 0.12, w * 0.55, shutters=team_shutters)
    rf = gable_roof_small(c, (0, 0, 0), depth + 0.25, w + 0.3, rise, 0.0, th=0.07)
    for p in rf:
        p.rot(0, 0, 90).move(0, -depth / 2 + 0.12, 0).rot(0, 0, ang).move(x, y, z + h - 0.02)


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
                    (r * 0.5, r * 0.3), (0, r * 0.28)], 9, c.sw("straw"))
    nest.move(x, y, z)
    c.add(nest, jit=0.03, dice=None)
    # twigs sticking out
    for k in range(6):
        a = k * 2 * math.pi / 6 + c.r(0, 0.5)
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
        head = L.lathe([(0, -s * 0.1), (s * 0.1, -s * 0.05), (s * 0.11, s * 0.03), (0, s * 0.1)], 6, c.sw("pal"))
        head.move(x + s * 0.52, y, bz + s * 0.8)
        c.P(head, "#F4F1EA")
        bill = L.member((x + s * 0.58, y, bz + s * 0.88), (x + s * 0.98, y, bz + s * 0.76), s * 0.06, s * 0.05,
                        c.sw("pal"))
        c.P(bill, "#C8502A")
        for p in (body, wing, neck, head, bill):
            p.rot(0, 0, facing, pivot=(x, y, z))


def barrel(c, pos, r=0.2, h=0.45, key="oak"):
    x, y, z = pos
    prof = [(r * 0.85, 0), (r * 1.02, h * 0.35), (r * 1.02, h * 0.65), (r * 0.85, h)]
    b = L.lathe(prof, 9, c.sw(key), cap_top=True)
    b.move(x, y, z)
    c.add(b, dice=None, uvrot=True)
    for zz in (0.12, 0.88):
        hoop = L.torus(r * (0.9 + 0.08 * (1 - abs(zz - 0.5) * 2)) + 0.005, 0.016, c.sw("iron"), segs=10, sides=3)
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
    c.add(panel)
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


def roof_solid(c, verts, faces, th, key="roof", deform=None, dice=0.4, soffit=False, rim_tint="#8A6A60",
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
        r.box_uv(rep)
        r.faceted = True
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


def pavise(c, pos, facing_deg, h=1.0, w=0.5, lean=8.0, face_key="team", n=10):
    """Tall flat round-topped shield standing on its foot: team face field with an ivory wheel
    (TEAM decal), dark oak back."""
    x, y, z = pos
    th = 0.05
    ol = [(-w / 2, 0.0), (w / 2, 0.0)]
    for i in range(n + 1):
        a = i / n * math.pi
        ol.append((math.cos(a) * w / 2, h - w * 0.3 + math.sin(a) * w * 0.3))
    ol = ol[:2] + ol[2:]
    face = L.prism(np.array(ol[1:] + ol[:1]), 0.0, 0.012, c.sw(face_key), chamfer=0.0, bottom=False)
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


def anvil(c, pos, rz=0.0, s=1.0):
    x, y, z = pos
    stump = L.lathe([(0.2 * s, 0), (0.18 * s, 0.42 * s), (0.17 * s, 0.45 * s), (0.0, 0.45 * s)], 8, c.sw("bark"))
    stump.move(x, y, z)
    c.add(stump, dice=None, uvrot=True)
    top = L.box(0.42 * s, 0.16 * s, 0.12 * s, c.sw("iron"), chamfer=0.02, center=(0, 0, 0.62 * s))
    waist = L.box(0.18 * s, 0.12 * s, 0.12 * s, c.sw("iron"), center=(0, 0, 0.51 * s))
    foot = L.box(0.3 * s, 0.18 * s, 0.06 * s, c.sw("iron"), center=(0, 0, 0.48 * s))
    horn = L.lathe([(0.06 * s, 0), (0.0, 0.2 * s)], 6, c.sw("iron")).rot(0, 90, 0).move(0.2 * s, 0, 0.62 * s)
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
          four=True, shafts=True, paint=None, spokes=8):
    """Kingdom plank wagon on spoked wheels. paint=None: folk-painted planks swatch; paint="burgundy":
    burgundy boards with ivory top rails (bible K_WAGON). team_band: a team band on the side boards.
    cover: False | True (ivory canvas with one team stripe round the middle hoop)."""
    x, y, z = center
    zb = wheel_r * 0.95
    R = L.rot_matrix(0, 0, rz)
    o = np.array([x, y, z])

    def put(p):
        return p.rot(0, 0, rz).move(x, y, z)

    if paint == "burgundy":
        body = L.box(length, width, h, c.sw("pal"), chamfer=0.02, center=(0, 0, zb + h / 2))
        c.P(put(body), "#7B1E2E", dice=None)
        for sy in (-1, 1):
            rail = L.box(length * 1.02, 0.06, 0.07, c.sw("pal"), center=(0, sy * (width / 2 + 0.01), zb + h - 0.02))
            c.P(put(rail), "#EDE2C8", dice=None)
        for sx in (-1, 1):
            rail = L.box(0.06, width * 1.02, 0.07, c.sw("pal"), center=(sx * (length / 2 + 0.01), 0, zb + h - 0.02))
            c.P(put(rail), "#EDE2C8", dice=None)
    else:
        c.add(put(L.box(length, width, h, c.sw("planks"), chamfer=0.02, center=(0, 0, zb + h / 2))), dice=None)
    c.add(put(L.box(length * 1.04, width * 0.96, 0.07, c.sw("oak"), center=(0, 0, zb))), dice=None)
    if team_band:
        for sy in (-1, 1):
            band = L.box(length * 0.84, 0.014, h * 0.3, c.sw("team_band"), center=(0, sy * (width / 2 + 0.01), zb + h * 0.5))
            v = band.v[band.t]
            band.uv = np.stack([v[..., 0] / 0.8, 1 - (v[..., 2] - (zb + h * 0.35)) / (h * 0.3)], -1)
            c.add(put(band), dice=None)
    xs = (-length * 0.3, length * 0.3) if four else (0.0,)
    for wx in xs:
        for sy in (-1, 1):
            cc = np.array([wx, sy * (width / 2 + 0.08), wheel_r])
            wc = R @ cc + o
            for p in wheel(c, tuple(wc), wheel_r, axis="y", spokes=spokes, segs=12):
                p.rot(0, 0, rz, pivot=wc)
    if shafts:
        for sy in (-1, 1):
            a = np.array([length / 2, sy * width * 0.3, zb + 0.05])
            b = np.array([length / 2 + 0.8, sy * width * 0.25, 0.1])
            c.add(put(L.member(a, b, 0.06, 0.06, c.sw("oak"), rng=c.rng)))
    if cover:
        # canvas on three hoops: ivory, with one team stripe round the middle (about 1/4 of the canvas)
        nseg = 8
        prof = [(math.cos(math.pi * i / nseg) * width * 0.53, math.sin(math.pi * i / nseg) * width * 0.6)
                for i in range(nseg + 1)]
        xs_ = [-0.44, -0.12, 0.12, 0.44]
        for k in range(3):
            xa, xb = xs_[k] * length, xs_[k + 1] * length
            verts = []
            for xx in (xa, xb):
                for (py, pz) in prof:
                    sagz = -0.04 if xx not in (xs_[0] * length, xs_[-1] * length) else 0.0
                    verts.append((xx, py, zb + h + pz + sagz * 0))
            verts = np.array(verts)
            K = len(prof)
            tris = []
            for i in range(K - 1):
                a, b, cc, d = i, i + 1, K + i + 1, K + i
                tris += [(a, cc, b), (a, d, cc)]
            tris = np.array(tris)
            team_mid = k == 1
            cv = Part(verts, tris, c.sw("team_band" if team_mid else "pal"), None, 60)
            vv = cv.v[cv.t]
            ang = np.arctan2(vv[..., 2] - zb - h, vv[..., 1])
            cv.uv = np.stack([(vv[..., 0] - xa) / 0.8, ang / math.pi], -1)
            # bulge the canvas between the hoops
            cv.v[:, 1:] = cv.v[:, 1:]
            put(cv)
            if team_mid:
                c.add(cv, dice=None, form=0.0)
            else:
                c.pal_uv(cv, "#EDE2C8")
                c.add(cv, dice=None, form=0.0)
            back = cv.copy()
            back.t = back.t[:, ::-1]
            back.uv = back.uv[:, ::-1]
            c.add(back, dice=None, form=0.0)
        for xx in xs_:
            hp = np.array([(xx * length, py * 1.02, zb + h + pz * 1.02) for (py, pz) in prof])
            hoop = L.sweep(L.rect_profile(0.05, 0.035), hp, c.sw("oak"), up=(1, 0, 0))
            c.add(put(hoop), dice=None)


# =============================================================================================
# kingdom buildings
# =============================================================================================

def house(c, x0, x1, y0, y1, zp, stories, t, ops=None, stone=(), jetty=0.0, plinth_pad=0.06, bay=0.62,
          shutters=True, skip=()):
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
            if name in skip:
                continue
            ol = [(0, zb), (w.L, zb), (w.L, zt), (0, zt)]
            if k in stone:
                wall_prism(c, w, ol, -0.08, 0.04, "rubble", chamfer=0.03)
            else:
                wall_prism(c, w, ol, -0.06, 0.0, "plaster", chamfer=0.0)
            o = [(f * w.L, ww, zb + a, zb + b_, kind) for (f, ww, a, b_, kind) in ops.get((name, k), [])]
            if k not in stone:
                timber_wall(c, w, zb, zt, t, o, bay=bay, simple=(name == "back"))
            for (s_, ww, za, zz, kind) in o:
                if kind == "window":
                    window(c, w, s_, za, zz, ww, shutters=shutters)
                    if k in stone:
                        c.add(L.member(w.p(s_ - ww / 2 - 0.06, zz + 0.05, 0.06), w.p(s_ + ww / 2 + 0.06, zz + 0.05, 0.06),
                                       0.1, 0.1, c.sw("oak"), rng=c.rng))
                        c.add(L.member(w.p(s_ - ww / 2 - 0.04, za - 0.04, 0.07), w.p(s_ + ww / 2 + 0.04, za - 0.04, 0.07),
                                       0.07, 0.12, c.sw("rubble"), rng=c.rng), jit=0.0)
                elif kind == "door":
                    door_(c, w, s_, za, ww, zz - za)
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
    """Croft (supply, 8x8 cells = 4 m): a half-timber cottage with its steep gable to the front
    (door rising into the gable, shuttered gable window), a chunky chimney on the slope, a stork nest
    on the back of the ridge, a lean-to woodshed and a wattle-fenced cabbage patch on the pad."""
    t = 0.1
    x0, x1, y0, y1 = -1.15, 1.15, -1.55, 0.95
    zp, zw = 0.22, 1.5
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front",), ops={
        ("back", 0): [(0.5, 0.42, 0.45, 0.95, "window")],
        ("right", 0): [(0.5, 0.4, 0.45, 0.95, "window")],
        ("left", 0): [(0.5, 0.4, 0.45, 0.95, "window")]}, bay=0.85)
    ov = 0.32
    half = (x1 - x0) / 2
    z_eave, z_ridge = roof_fit(zw, half, ov, 50, 0.13, y1 - y0 + 0.64)
    gable_roof(c, y0 - 0.3, y1 + 0.34, 0.0, half + ov, z_eave, z_ridge, th=0.13, t=0.13, nu=8, nv=5, axis="y",
               cx=0.0, trim=0.1, ridge_w=0.15)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, zw, z_ridge - 0.17, t, door=(fw.L / 2, 0.86, 1.9), apex_window=None,
               windows=[])
    window(c, fw, fw.L / 2, 2.32, 2.62, 0.3, shutters=True)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zw, z_ridge - 0.17, t)
    # chimney through the right slope near the back, stork nest on the back of the ridge
    chimney(c, 0.55, -0.85, zw, z_ridge + 0.12, 0.46)
    stork_nest(c, (0.0, y0 + 0.02, z_ridge - 0.07), r=0.27, facing=150)
    # small pennant on the front gable apex
    pennant(c, (0.0, y1 + 0.3, z_ridge - 0.05), 0.3, 0.5, 0.2, dirn=(-1, 0.45), phase=0.4, pole_r=0.03)
    # lean-to woodshed on the left: logs with ring ends to the front
    lx0, lx1, ly0, ly1 = -1.95, -1.22, -1.35, 0.55
    for yy in (ly0, ly1):
        c.add(L.member((lx0, yy, 0), (lx0, yy, 1.05), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    roof_solid(c, [(lx0 - 0.15, ly0 - 0.15, 0.98), (lx1 + 0.05, ly0 - 0.15, 1.42), (lx1 + 0.05, ly1 + 0.15, 1.42),
                   (lx0 - 0.15, ly1 + 0.15, 0.98)], [[0, 1, 2, 3]], 0.07, "roof", None, dice=0.5)
    for row in range(2):
        for k in range(2 - row):
            rr = 0.13 + 0.02 * c.r()
            xx = lx0 + 0.22 + k * 0.27 + 0.13 * row
            log1(c, (xx, (ly0 + ly1) / 2, row * 0.23), 1.75, rr, axis="y", sides=7)
    # wattle-fenced cabbage patch at the front right
    fence_wattle(c, (0.35, 1.3), (1.9, 1.3), 0.45)
    fence_wattle(c, (1.9, 1.3), (1.9, -0.2), 0.45)
    for k in range(6):
        cb = L.blob(c.sw("leaves"), radius=0.16, subdiv=1, scale=(1, 1, 0.75), seed=40 + k, noise_amp=0.25)
        cb.move(0.6 + (k % 3) * 0.42 + c.r(-0.05, 0.05), 0.95 - (k // 3) * 0.42, 0.0)
        c.add(cb, dice=None, tint=(0.95, 1.05, 0.85) if k % 2 else (0.8, 0.95, 0.75))
    stook(c, (1.55, -1.45, 0.0), 0.5, 1.1)
    return {"height_target": (3.0, 3.5)}


def log1(c, center, length, r, axis="y", ends=True, key="bark", sides=8):
    """One log with end-grain ring caps (axis 'x' or 'y')."""
    x, y, z = center
    b = L.lathe([(r, -length / 2), (r * 1.03, 0), (r, length / 2)], sides, c.sw(key), a0=c.r(0, 1))
    parts = [b]
    if ends:
        for sgn in (-1, 1):
            ang = np.arange(sides) * 2 * math.pi / sides
            ring = np.stack([np.cos(ang) * r * 0.98, np.sin(ang) * r * 0.98, np.zeros(sides)], 1)
            vv = np.vstack([ring, [[0, 0, 0]]])
            tt = np.array([(sides, j, (j + 1) % sides) if sgn > 0 else (sides, (j + 1) % sides, j) for j in range(sides)])
            uv = np.stack([0.5 + vv[..., 0] / (2 * r), 0.5 - vv[..., 1] / (2 * r)], -1)[tt]
            e = Part(vv, tt, c.sw("rings"), uv, 0.0)
            e.move(0, 0, sgn * length / 2)
            parts.append(e)
    for p in parts:
        if axis == "y":
            p.rot(-90, 0, 0)
        elif axis == "x":
            p.rot(0, 90, 0)
        p.move(x, y, z + r)
        c.add(p, dice=None, jit=0.0)
    return parts


def stook(c, pos, r, h):
    """Leaning straw sheaf (hay stook)."""
    x, y, z = pos
    st = L.lathe([(r, 0.0), (r * 0.9, h * 0.35), (r * 0.45, h * 0.8), (r * 0.12, h), (0.0, h * 1.02)], 10, c.sw("straw"))
    st.move(x, y, z)
    c.add(st, dice=None, jit=0.04)
    band = L.lathe([(r * 0.62, h * 0.55), (r * 0.66, h * 0.6), (r * 0.6, h * 0.65)], 10, c.sw("pal"))
    band.move(x, y, z)
    c.P(band, "#5A3A22", dice=None)


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


def iron_wheel_arch(c, cx, cy, zc, R, depth=0.2, spokes=3, lean=14.0):
    """Oath Hall gate: the upper half of a giant six-spoked iron wheel (three spokes show) standing
    free in front of the door on iron rim legs, its top leaning back by `lean` degrees so the arch
    reads from the high camera; hub boss with the dark-bronze coal of the emblem."""
    k0 = len(c.parts)
    rim_w = R * 0.15
    n = 16
    ang = np.linspace(0, math.pi, n + 1)
    path = np.stack([cx + np.cos(ang) * (R - rim_w / 2), np.full(n + 1, cy), zc + np.sin(ang) * (R - rim_w / 2)], 1)
    c.add(L.sweep(L.rect_profile(rim_w, depth, 0.03), path, c.sw("iron"), up=(0, 1, 0)), dice=None)
    tyre_path = np.stack([cx + np.cos(ang) * (R + 0.015), np.full(n + 1, cy), zc + np.sin(ang) * (R + 0.015)], 1)
    c.add(L.sweep(L.rect_profile(rim_w * 0.35, depth * 1.12), tyre_path, c.sw("iron"), up=(0, 1, 0)), dice=None,
          tint=(1.25, 1.25, 1.3))
    for sx in (-1, 1):
        c.add(L.member((cx + sx * (R - rim_w / 2), cy, 0.0), (cx + sx * (R - rim_w / 2), cy, zc + 0.02), rim_w * 1.05,
                       depth, c.sw("iron"), roll_up=(0, 1, 0)))
    hub = L.lathe([(0, -depth * 0.8), (R * 0.2, -depth * 0.8), (R * 0.22, 0), (R * 0.2, depth * 0.8), (R * 0.1, depth * 1.4),
                   (0, depth * 1.5)], 10, c.sw("iron"))
    hub.rot(-90, 0, 0).move(cx, cy, zc)
    c.add(hub, dice=None)
    for k in range(spokes):
        a_ = math.pi * (k + 0.5) / spokes
        d = np.array([math.cos(a_), 0.0, math.sin(a_)])
        c.add(L.member(np.array([cx, cy, zc]) + d * R * 0.18, np.array([cx, cy, zc]) + d * (R - rim_w * 0.7),
                       rim_w * 0.62, depth * 0.75, c.sw("iron"), roll_up=(0, 1, 0)))
    coal = L.lathe([(0, 0), (R * 0.1, 0.0), (R * 0.08, R * 0.06), (0, R * 0.08)], 8, c.sw("pal"))
    coal.rot(-90, 0, 0).move(cx, cy + depth * 1.45, zc)
    c.P(coal, "#6E4A26", dice=None)
    for p in c.parts[k0:]:
        p.rot(lean, 0, 0, pivot=(cx, cy, 0.0))
    for sx in (-1, 1):
        pbox(c, rim_w * 2.6, depth * 2.4, 0.3, "rubble", center=(cx + sx * (R - rim_w / 2), cy, 0))


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
    """Oath Hall (hero altar, 12x12 cells = 6 m): a squat rubble-stone hall under a heavy hip roof with
    battered corner buttresses; in front of the door stands its signature, a free-standing gate made
    of the upper half of a giant iron wheel, rising well above the eaves (about 1.4x) and leaning back
    towards the camera; the oath wheel is set in the floor before it, braziers and team banners flank it."""
    t = 0.12
    x0, x1, y0, y1 = -2.4, 2.4, -2.75, 0.65
    zp, zw = 0.3, 2.45
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, stone=(0,), ops={
        ("front", 0): [(0.5, 1.3, 0.0, 2.1, "door"), (0.18, 0.42, 0.9, 1.6, "window"), (0.82, 0.42, 0.9, 1.6, "window")],
        ("left", 0): [(0.5, 0.4, 0.9, 1.6, "window")],
        ("right", 0): [(0.5, 0.4, 0.9, 1.6, "window")]})
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bx, by = (x1 if sx > 0 else x0), (y1 if sy > 0 else y0)
        pbox(c, 0.6, 0.6, 2.15, "rubble", center=(bx + sx * 0.06, by + sy * 0.06, 0), taper=0.3, chamfer=0.06, grid=0.6)
    ov = 0.38
    hip_roof(c, x0 - ov, x1 + ov, y0 - ov, y1 + ov, zw + 0.02, 4.75, ridge_frac=0.85, th=0.17, kick=0.1, hip_w=0.09,
             hips=True)
    iron_wheel_arch(c, 0.0, y1 + 1.0, 1.95, 1.55, lean=15.0)
    floor_wheel(c, 0.0, y1 + 1.95, 0.48)
    braziers(c, [(-1.95, y1 + 1.25), (1.95, y1 + 1.25)], r=0.22, h=0.75)
    for sx in (-1, 1):
        x = sx * 2.65
        c.add(L.member((x, y1 + 0.75, 0), (x, y1 + 0.75, 3.7), 0.13, 0.13, c.sw("oak"), rng=c.rng, chamfer=0.02))
        pbox(c, 0.42, 0.42, 0.25, "rubble", center=(x, y1 + 0.75, 0))
        banner(c, (x, y1 + 0.84, 3.55), 0.62, 1.35, normal=(0, 1))
        ball = L.lathe([(0, 0), (0.09, 0.05), (0.1, 0.14), (0.04, 0.22), (0, 0.27)], 7, c.sw("iron"))
        ball.move(x, y1 + 0.75, 3.7)
        c.add(ball, dice=None)
    rl = 0.85 * abs((x1 - x0) / 2 - (y1 - y0) / 2)
    ycen = (y0 + y1) / 2
    for sx in (-1, 1):
        pennant(c, (sx * rl, ycen, 4.7), 0.6, 0.7, 0.28, dirn=(sx, 0.5), phase=sx)
    return {"height_target": (4.5, 5.5)}


def k_drill_yard(c):
    """Drill Yard (barracks, 12x12 cells = 6 m): a big timber longhouse with its gable (double door,
    shuttered windows) to the front, a dormer and a chimney on the slopes; an L-shaped wattle-fenced
    drill yard round it: a pavise wall of tall shields, a polearm rack, a straw drill dummy in a kettle
    hat and a tall team pennant mast at the gate."""
    t = 0.13
    x0, x1, y0, y1 = -2.9, 0.85, -2.9, 0.95
    zp, zw = 0.32, 2.35
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front",), ops={
        ("right", 0): [(0.3, 0.55, 0.75, 1.5, "window"), (0.72, 0.55, 0.75, 1.5, "window")],
        ("left", 0): [(0.5, 0.55, 0.75, 1.5, "window")]}, bay=1.0)
    ov = 0.38
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ridge_len = y1 - y0 + 0.8
    z_eave, z_ridge = roof_fit(zw, half, ov, 50, 0.16, ridge_len)
    gable_roof(c, y0 - 0.38, y1 + 0.42, xm, half + ov, z_eave, z_ridge, th=0.16, t=0.16, nu=10, nv=6, axis="y",
               cx=xm, trim=0.13, ridge_w=0.18)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, zw, z_ridge - 0.22, t, door=(fw.L / 2, 1.35, 2.2),
               windows=[(fw.L * 0.15, 0.95, 1.6, 0.48), (fw.L * 0.85, 0.95, 1.6, 0.48)])
    window(c, fw, fw.L / 2, z_ridge - 1.75, z_ridge - 1.15, 0.5, shutters=True)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zw, z_ridge - 0.22, t)
    chimney(c, xm - 0.95, y0 + 0.95, zw, z_ridge + 0.2, 0.6)
    zr = roof_z(1.0, half + ov, z_eave, z_ridge)
    dormer(c, (xm + 1.2, -1.1, zr - 0.4), (1, 0), w=0.95, h=0.8, depth=1.1, rise=0.5)
    # L-shaped drill yard: front strip + right strip
    fh = 0.8
    fence_wattle(c, (2.95, -2.9), (2.95, 2.9), fh)
    fence_wattle(c, (1.25, -2.9), (2.95, -2.9), fh)
    fence_wattle(c, (2.95, 2.9), (1.95, 2.9), fh)
    fence_wattle(c, (0.85, 2.9), (-2.9, 2.9), fh)
    fence_wattle(c, (-2.9, 2.9), (-2.9, 1.3), fh)
    for gx in (0.85, 1.95):
        c.add(L.member((gx, 2.9, 0), (gx, 2.9, 1.35), 0.17, 0.17, c.sw("oak"), rng=c.rng))
        cap = L.lathe([(0, 0), (0.11, 0.03), (0.12, 0.1), (0.05, 0.16), (0, 0.18)], 6, c.sw("iron"))
        cap.move(gx, 2.9, 1.35)
        c.add(cap, dice=None)
    for i, (px, py) in enumerate(((1.6, -2.15), (2.15, -1.45), (2.6, -0.75), (2.15, -0.05))):
        pavise(c, (px, py, 0.0), -12.0 * (i - 1.5), h=1.9, w=0.64, lean=9, n=6,
               face_key="team" if i == 1 else "planks")
    weapon_rack(c, (2.6, 0.9, 0.0), rz=90.0, width=1.3, h=1.15, n=4)
    dx, dy = 1.75, 1.85
    c.add(L.member((dx, dy, 0), (dx, dy, 1.6), 0.11, 0.11, c.sw("oak"), rng=c.rng))
    c.add(L.member((dx - 0.45, dy, 1.25), (dx + 0.45, dy, 1.25), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    body = L.blob(c.sw("straw"), radius=0.32, subdiv=1, scale=(1, 0.75, 1.35), seed=7, noise_amp=0.1)
    body.move(dx, dy, 0.75)
    c.add(body, dice=None)
    hat = L.lathe([(0.0, 0.0), (0.42, 0.0), (0.42, 0.03), (0.19, 0.07), (0.18, 0.21), (0.0, 0.24)], 9, c.sw("iron"))
    hat.move(dx, dy, 1.56)
    c.add(hat, dice=None)
    pennant(c, (1.95, 2.92, 1.35), 4.3, 1.25, 0.5, dirn=(-0.7, 1), phase=0.8, pole_r=0.06)
    barrel(c, (-0.3, 1.75, 0), r=0.26, h=0.6)
    crate(c, (0.25, 1.65, 0), s=0.42, rz=12)
    crate(c, (0.25, 1.65, 0.42), s=0.32, rz=35)
    return {"height_target": (5.0, 6.0)}


def open_shed(c, x0, x1, y0, y1, zt, pitch_deg=50, t=0.15, mid_posts=True, back_wall=True, front_banner=True,
              ov=0.32):
    """Open timber shed, gable to the front (+y) left open so the work inside shows: posts on rubble
    footings, tie beams, a plank back wall, a plank back gable, an open front gable with a tie beam,
    king post and braces. Returns z_ridge."""
    xs = [x0, (x0 + x1) / 2, x1] if mid_posts else [x0, x1]
    ys = [y0, (y0 + y1) / 2, y1] if (y1 - y0) > 2.6 else [y0, y1]
    for x in (x0, x1):
        for y in ys:
            c.add(L.member((x, y, 0), (x, y, zt), t, t, c.sw("oak"), rng=c.rng, chamfer=0.02))
            pbox(c, t * 2.1, t * 2.1, 0.2, "rubble", center=(x, y, 0))
    if mid_posts:
        pbox(c, t * 2.1, t * 2.1, 0.2, "rubble", center=(xs[1], y0, 0))
        c.add(L.member((xs[1], y0, 0), (xs[1], y0, zt), t, t, c.sw("oak"), rng=c.rng, chamfer=0.02))
    for x in (x0, x1):
        c.add(L.member((x, y0 - 0.12, zt - t / 2), (x, y1 + 0.12, zt - t / 2), t * 1.1, t * 1.2, c.sw("oak"), rng=c.rng))
        for ya, yb in ((y0, y0 + 0.55), (y1, y1 - 0.55)):
            c.add(L.member((x, ya, zt - 0.6), (x, yb, zt - t), t * 0.75, t * 0.75, c.sw("oak"), rng=c.rng))
    for y in (y0, y1):
        c.add(L.member((x0 - 0.12, y, zt - t / 2), (x1 + 0.12, y, zt - t / 2), t * 1.1, t * 1.2, c.sw("oak"), rng=c.rng))
    if back_wall:
        bw = L.plate((x1 + 0.06, y0 - 0.1, 0.05), (x0 - 0.06, y0 - 0.1, 0.05), (x0 - 0.06, y0 - 0.1, zt - 0.08),
                     (x1 + 0.06, y0 - 0.1, zt - 0.08), 0.06, c.sw("planks"))
        bw.box_uv()
        c.add(bw, uvrot=True)
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    z_eave, z_ridge = roof_fit(zt, half, ov, pitch_deg, 0.14, y1 - y0 + 2 * ov)
    gable_roof(c, y0 - ov, y1 + ov + 0.05, xm, half + ov, z_eave, z_ridge, th=0.14, t=0.15, nu=10, nv=5, axis="y",
               cx=xm, trim=0.12, ridge_w=0.17)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zt, z_ridge - 0.18, 0.12, key="planks")
    # open front gable: king post + braces only
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    za = z_ridge - 0.2
    c.add(L.member(fw.p(fw.L / 2, zt, 0.04), fw.p(fw.L / 2, za, 0.04), t, t, c.sw("oak"), rng=c.rng))
    for sgn in (-1, 1):
        c.add(L.member(fw.p(fw.L / 2, zt + (za - zt) * 0.25, 0.04), fw.p(fw.L / 2 + sgn * fw.L * 0.32, zt + (za - zt) * 0.62, 0.04),
                       t * 0.8, t * 0.8, c.sw("oak"), rng=c.rng))
    return z_ridge


def giant_wheel(c, center, r, tilt=38.0, spokes=8, rz=0.0):
    """A big spoked wagon wheel (iron tyre, oak felloes) facing +y, tilted back by `tilt` degrees so
    it reads as a full circle from the high camera; rz turns it about the vertical."""
    parts = wheel(c, (0.0, 0.0, 0.0), r, axis="y", spokes=spokes, width=r * 0.12, rim_w=r * 0.13, segs=18,
                  hub_r=r * 0.17)
    for p in parts:
        p.rot(tilt, 0, 0).rot(0, 0, rz).move(*center)    # top leans back, away from the camera
    return parts


def k_timber_yard(c):
    """Timber Yard (lumber drop-off, 12x12 cells = 6 m), built at the tree line: an open timber shed
    (gable to the front, open so its plank racks show) at the back, a sawpit in front with a log on tall
    trestles, an upright two-man pit-saw frame and a sheer-legs hoist standing above it, and a tall end
    pile of big logs with their ring ends to the camera."""
    zt = 2.55
    z_ridge = open_shed(c, -2.9, 0.75, -2.9, -0.55, zt, pitch_deg=52)
    # sawn plank racks inside the shed
    for k in range(4):
        for j in range(3):
            pbox(c, 2.6, 0.26, 0.06, "oak", center=(-1.1, -2.45 + j * 0.62, 0.12 + k * 0.08), taper=0.0, jit=0.006)
    for j in range(3):
        for sx in (-2.3, 0.1):
            pbox(c, 0.12, 0.3, 0.12, "oak", center=(sx, -2.45 + j * 0.62, 0.0), taper=0.0)
    # sawpit: dark pit with a plank rim, log on tall trestles, pit-saw frame, sheer legs + hoist
    sx, sy = -1.15, 1.05
    rim = L.prism(L.rect_profile(2.7, 1.2, 0.08), 0.0, 0.16, c.sw("planks"), chamfer=0.03)
    rim.move(sx, sy, 0)
    c.add(rim, dice=None)
    pit = L.quad((sx - 1.2, sy - 0.45, 0.165), (sx + 1.2, sy - 0.45, 0.165), (sx + 1.2, sy + 0.45, 0.165),
                 (sx - 1.2, sy + 0.45, 0.165), c.sw("pal"))
    c.P(pit, "#2A2220", ao=False, min_shade=0.0)
    for tx in (sx - 0.95, sx + 0.95):
        trestle(c, (tx, sy, 0.16), rz=90, w=0.9, h=0.95)
    log1(c, (sx, sy, 1.04), 2.8, 0.26, axis="x", sides=9)
    fx = sx + 0.35
    for sgn in (-1, 1):
        c.add(L.member((fx, sy + sgn * 0.32, 0.2), (fx, sy + sgn * 0.32, 2.75), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    for zz in (0.25, 2.7):
        c.add(L.member((fx, sy - 0.42, zz), (fx, sy + 0.42, zz), 0.08, 0.08, c.sw("oak"), rng=c.rng))
    c.add(L.box(0.025, 0.22, 2.4, c.sw("iron"), center=(fx, sy, 1.5)), dice=None)
    for zz in (2.95, 0.05):
        c.add(L.member((fx, sy - 0.32, zz), (fx, sy + 0.32, zz), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    # sheer legs (A-frames at both pit ends) with a ridge beam and a hoist chain
    zt2 = 4.35
    for ex in (sx - 1.35, sx + 1.35):
        for sgn in (-1, 1):
            c.add(L.member((ex, sy + sgn * 0.85, 0.0), (ex, sy, zt2), 0.13, 0.13, c.sw("oak"), rng=c.rng))
        c.add(L.member((ex, sy - 0.55, 1.25), (ex, sy + 0.55, 1.25), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    c.add(L.member((sx - 1.5, sy, zt2 - 0.05), (sx + 1.5, sy, zt2 - 0.05), 0.14, 0.15, c.sw("oak"), rng=c.rng))
    pul = L.torus(0.13, 0.04, c.sw("iron"), segs=10, sides=4).rot(90, 0, 0)
    pul.move(sx - 0.55, sy, zt2 - 0.25)
    c.add(pul, dice=None)
    c.add(L.member((sx - 0.55, sy, zt2 - 0.35), (sx - 0.55, sy, 1.32), 0.035, 0.035, c.sw("iron")), dice=None)
    # tall end pile of big logs, ring ends to the camera, held by posts
    lx0, lx1 = 1.05, 2.95
    ly = -0.75
    Lg = 3.6
    rows = [(3, 0.0), (3, 0.5), (2, 0.0), (2, 0.5), (1, 0.0)]
    rr0 = 0.3
    zz = 0.0
    for ri, (n, off) in enumerate(rows):
        for k in range(n):
            rr = rr0 * (0.9 + 0.18 * c.r())
            xx = lx0 + 0.34 + (k + off + (3 - n) * 0.5) * 0.6
            log1(c, (xx, ly + c.r(-0.08, 0.08), zz), Lg * (0.94 + 0.08 * c.r()), rr, axis="y", sides=9)
        zz += 0.5
    for px in (lx0 - 0.02, lx1 + 0.02):
        for py in (ly - 1.3, ly + 1.3):
            c.add(L.member((px, py, 0), (px, py, 2.85), 0.14, 0.14, c.sw("oak"), rng=c.rng, chamfer=0.02))
    pennant(c, (lx1 + 0.02, ly + 1.3, 2.85), 1.2, 0.95, 0.38, dirn=(-0.5, 1), phase=0.2, pole_r=0.05)
    # chopping block with an axe, sawdust heap
    blk = L.lathe([(0.3, 0), (0.28, 0.5), (0.0, 0.52)], 8, c.sw("bark"))
    blk.move(0.55, 2.3, 0)
    c.add(blk, dice=None)
    c.add(L.member((0.55, 2.3, 0.5), (0.85, 2.45, 1.05), 0.05, 0.05, c.sw("oak"), rng=c.rng))
    c.add(L.box(0.06, 0.24, 0.2, c.sw("iron"), center=(0.85, 2.48, 1.02)), dice=None)
    dust = L.blob(c.sw("straw"), radius=0.5, subdiv=1, scale=(1.3, 1.0, 0.35), seed=12, noise_amp=0.15, flat_bottom=0.0)
    dust.move(sx + 0.2, sy - 0.9, 0)
    c.add(dust, dice=None, tint=(1.05, 0.95, 0.75))
    banner(c, (-1.1, -0.6 + 0.1, zt - 0.05), 1.0, 0.7, normal=(0, 1), bar=False)
    return {"height_target": (5.0, 6.0)}


def k_foundry(c):
    """Foundry (smithy, 12x12 cells = 6 m): a stone-and-brick forge house with a crow-stepped brick
    gable to the front and a glowing forge door, a massive square brick chimney stack (about 1.6x the
    ridge) with a big dark-bronze cap on the camera-side corner (smoke anchor for VFX), and an open
    lean-to smithy with anvil, quench tub and grindstone; ingots and coal in the yard."""
    t = 0.12
    x0, x1, y0, y1 = -2.85, 0.2, -2.85, 0.75
    zp, zw = 0.3, 2.3
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, stone=(0,), skip=("front",), ops={
        ("left", 0): [(0.5, 0.42, 0.95, 1.6, "window")]})
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ov = 0.25
    z_eave, z_ridge = roof_fit(zw, half, ov, 44, 0.15, y1 - y0 + 0.5)
    gable_roof(c, y0 - 0.3, y1 + 0.05, xm, half + ov, z_eave, z_ridge, th=0.15, t=0.15, nu=8, nv=5, axis="y", cx=xm,
               trim=0.12, ridge_w=0.17)
    gw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    wall_prism(c, gw, [(0, zp), (gw.L, zp), (gw.L, zw), (0, zw)], -0.08, 0.04, "rubble", chamfer=0.03)
    ztop = stepped_gable(c, gw, zw, z_ridge, steps=3, th=0.24, key="brick", rise=0.24, d0=-0.1)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zw, z_ridge - 0.17, t)
    window(c, gw, gw.L / 2, zw + 0.35, zw + 0.85, 0.42, shutters=True)
    # forge door: dark recess, ember glow, open plank doors, oak lintel
    s0 = gw.L / 2
    dk = L.quad(gw.p(s0 - 0.65, zp, 0.05), gw.p(s0 + 0.65, zp, 0.05), gw.p(s0 + 0.65, zp + 1.95, 0.05),
                gw.p(s0 - 0.65, zp + 1.95, 0.05), c.sw("pal"))
    c.P(_face_out(dk, gw), "#2A2220", ao=False, min_shade=0.0)
    gl = L.quad(gw.p(s0 - 0.48, zp, 0.055), gw.p(s0 + 0.48, zp, 0.055), gw.p(s0 + 0.48, zp + 1.0, 0.055),
                gw.p(s0 - 0.48, zp + 1.0, 0.055), c.sw("ember"))
    gl.uv = np.array([[(0.15, 0.95), (0.85, 0.95), (0.85, 0.35)], [(0.15, 0.95), (0.85, 0.35), (0.15, 0.35)]])
    c.add(_face_out(gl, gw), ao=False, min_shade=1.0, form=0.0, occ=False)
    c.add(L.member(gw.p(s0 - 0.9, zp + 2.05, 0.1), gw.p(s0 + 0.9, zp + 2.05, 0.1), 0.2, 0.18, c.sw("oak"), rng=c.rng))
    for sgn in (-1, 1):
        dp = L.box(0.66, 1.9, 0.06, c.sw("planks"))
        dp.move(sgn * 0.33, 0.95, 0).rot(0, sgn * -65, 0).move(0, 0, 0.07)
        gw.place(dp, s0 + sgn * 0.66, zp, 0.0)
        c.add(dp, dice=None, uvrot=True)
    # the chimney stack on the camera-side corner, a dark-bronze cap, smoke anchor
    chx, chy = x1 + 0.3, y1 - 0.25
    hch = 5.45
    ch = L.gbox(1.0, 1.0, hch, c.sw("brick"), center=(chx, chy, 0.0), chamfer=0.04, grid=0.9)
    zf = ch.v[:, 2] / hch
    ch.v[:, 0] = chx + (ch.v[:, 0] - chx) * (1 - 0.16 * zf)
    ch.v[:, 1] = chy + (ch.v[:, 1] - chy) * (1 - 0.16 * zf)
    ch.box_uv()
    c.add(ch, jit=0.012)
    for zz, w_ in ((0.0, 1.16), (4.55, 0.98)):
        pbox(c, w_, w_, 0.22, "rubble", center=(chx, chy, zz), taper=0.04, chamfer=0.04)
    cap = L.lathe([(0.66, 0.0), (0.7, 0.06), (0.62, 0.14), (0.36, 0.34), (0.16, 0.5), (0.0, 0.58)], 4, c.sw("scales"),
                  a0=math.pi / 4)
    cap.move(chx, chy, hch + 0.06)
    c.add(cap, dice=None)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.add(L.member((chx + sx * 0.3, chy + sy * 0.3, hch - 0.05), (chx + sx * 0.3, chy + sy * 0.3, hch + 0.12), 0.07,
                           0.07, c.sw("iron")))
    knob = L.lathe([(0, 0), (0.09, 0.05), (0.08, 0.13), (0, 0.18)], 7, c.sw("pal"))
    knob.move(chx, chy, hch + 0.62)
    c.P(knob, "#B07F3E", dice=None)
    c.anchors["smoke"] = (chx, chy, hch + 0.2)
    # open lean-to smithy on the right
    lx0, lx1, ly0, ly1 = 0.8, 2.95, -2.2, 0.55
    for x, y in ((lx1, ly1), (lx1, ly0), ((lx0 + lx1) / 2 + 0.3, ly1)):
        c.add(L.member((x, y, 0), (x, y, 1.95), 0.15, 0.15, c.sw("oak"), rng=c.rng, chamfer=0.02))
        pbox(c, 0.3, 0.3, 0.18, "rubble", center=(x, y, 0))
    c.add(L.member((lx1, ly0 - 0.15, 1.9), (lx1, ly1 + 0.15, 1.9), 0.15, 0.16, c.sw("oak"), rng=c.rng))
    roof_solid(c, [(lx0 - 0.1, ly0 - 0.3, 2.75), (lx1 + 0.3, ly0 - 0.3, 1.88), (lx1 + 0.3, ly1 + 0.35, 1.88),
                   (lx0 - 0.1, ly1 + 0.35, 2.75)], [[0, 1, 2, 3]], 0.12, "roof", None, dice=None)
    hearth = pbox(c, 1.1, 0.8, 0.75, "brick", center=(1.3, -1.5, 0), taper=0.06)
    coals = L.quad((0.85, -1.8, 0.76), (1.75, -1.8, 0.76), (1.75, -1.2, 0.76), (0.85, -1.2, 0.76), c.sw("ember"))
    coals.uv = np.array([[(0.2, 0.8), (0.8, 0.8), (0.8, 0.2)], [(0.2, 0.8), (0.8, 0.2), (0.2, 0.2)]])
    c.add(coals, ao=False, min_shade=1.0, form=0.0, occ=False)
    anvil(c, (2.0, -0.25, 0), rz=15, s=1.5)
    barrel(c, (2.55, 0.75, 0), r=0.28, h=0.55)
    grind = wheel(c, (1.45, 0.8, 0.5), 0.42, axis="x", spokes=0, key="rubble", width=0.18, rim_w=0.42, segs=12)
    for sx_ in (-0.12, 0.12):
        c.add(L.member((1.45 + sx_, 0.8, 0), (1.45 + sx_, 0.8, 0.55), 0.07, 0.07, c.sw("oak"), rng=c.rng))
    # ingots, coal heap, yard barrel
    for k in range(3):
        for j in range(3 - k):
            ing = pbox(c, 0.36, 0.14, 0.1, "pal", center=(-0.3 + j * 0.2 + k * 0.1, 1.75 + (k % 2) * 0.03, k * 0.1),
                       taper=0.2, chamfer=0.02)
            c.pal_uv(ing, "#B07F3E")
    coal = L.blob(c.sw("pal"), radius=0.5, subdiv=1, scale=(1.2, 0.9, 0.5), seed=11, noise_amp=0.22, flat_bottom=0.0)
    coal.move(-2.1, 1.65, 0)
    c.P(coal, "#26221F", dice=None)
    barrel(c, (-1.15, 1.6, 0), r=0.24, h=0.52)
    pennant(c, (xm, y1 - 0.02, ztop), 0.7, 0.9, 0.34, dirn=(-1, 0.35), phase=1.0)
    banner(c, ((lx0 + lx1) / 2 + 0.3, ly1 + 0.42, 1.88), 0.75, 0.62, normal=(0, 1), bar=False)
    return {"height_target": (5.0, 6.2), "budget_note": "chimney stack 1.6x the ridge (art bible 4.2), the rest <= 4.3 m"}


def k_collegium(c):
    """Collegium (caster hall, 12x12 cells = 6 m): a tall narrow two-storey jettied guild house with its
    gable to the front and a little bell-cote on the gable, beside a walled linden herb garden (low
    lime-washed wall with rubble coping, gate piers, two linden saplings, raised herb beds)."""
    t = 0.11
    x0, x1, y0, y1 = -2.9, -0.3, -2.7, 0.95
    zp = 0.3
    st = [2.15, 3.55]
    jet = 0.18
    walls, _ = house(c, x0, x1, y0, y1, zp, st, t, jetty=jet, ops={
        ("front", 0): [(0.5, 1.0, 0.0, 1.85, "door")],
        ("right", 0): [(0.35, 0.42, 0.8, 1.45, "window"), (0.75, 0.42, 0.8, 1.45, "window")],
        ("left", 0): [(0.5, 0.42, 0.8, 1.45, "window")],
        ("front", 1): [(0.25, 0.42, 0.3, 1.05, "window"), (0.75, 0.42, 0.3, 1.05, "window")],
        ("right", 1): [(0.3, 0.4, 0.3, 1.0, "window"), (0.7, 0.4, 0.3, 1.0, "window")],
        ("left", 1): [(0.5, 0.4, 0.3, 1.0, "window")]}, bay=0.85)
    xm = (x0 + x1) / 2
    half = (x1 - x0) / 2
    ov = 0.25
    yf, yb = y1 + jet, y0 - jet
    z_eave, z_ridge = roof_fit(st[-1], half, ov, 52, 0.14, yf - yb + 0.4)
    gable_roof(c, yb - 0.2, yf + 0.22, xm, half + ov, z_eave, z_ridge, th=0.14, t=0.14, nu=8, nv=5, axis="y", cx=xm,
               trim=0.11, ridge_w=0.16)
    gable_infill(c, Wall((x1, yf), (-1, 0), (0, 1), x1 - x0), st[-1], z_ridge - 0.17, t, window_w=0.36)
    gable_infill(c, Wall((x0, yb), (1, 0), (0, -1), x1 - x0), st[-1], z_ridge - 0.17, t, window_w=0.0)
    bell_cote(c, (xm, yf - 0.02, z_ridge - 0.12), size=0.62, rz=0)
    banner(c, (xm, yf + 0.06, st[0] + 0.2), 0.95, 0.9, normal=(0, 1))
    pennant(c, (xm, yb - 0.1, z_ridge - 0.08), 0.5, 0.8, 0.3, dirn=(1, -0.4), phase=0.9)
    # walled herb garden on the right
    gx0, gx1, gy0, gy1 = 0.05, 2.9, -2.85, 2.65
    wt, wh = 0.22, 0.72
    gate0, gate1 = 1.05, 1.95
    segs = [((gx0, gy0), (gx1, gy0)), ((gx1, gy0), (gx1, gy1)), ((gx1, gy1), (gate1, gy1)), ((gate0, gy1), (gx0, gy1)),
            ((gx0, gy1), (gx0, gy0))]
    for (a_, b_) in segs:
        a_, b_ = np.array(a_, float), np.array(b_, float)
        d = b_ - a_
        Lw = float(np.linalg.norm(d))
        e = d / Lw
        n = np.array([e[1], -e[0]])
        wl = Wall(a_ + n * wt / 2, e, n, Lw)
        wall_prism(c, wl, [(-wt / 2, 0.0), (Lw + wt / 2, 0.0), (Lw + wt / 2, wh), (-wt / 2, wh)], -wt, 0.0, "plaster",
                   chamfer=0.03, grid=1.2)
        cp = L.box(Lw + wt + 0.06, 0.09, wt + 0.08, c.sw("rubble"), chamfer=0.02)
        cp.move(Lw / 2, wh + 0.045, -wt / 2)
        wl.place(cp)
        c.add(cp, dice=None, jit=0.012)
    for gx in (gate0, gate1):
        pbox(c, 0.34, 0.34, 1.15, "rubble", center=(gx, gy1 - wt / 2, 0), taper=0.08)
        ball = L.lathe([(0, 0), (0.12, 0.05), (0.11, 0.17), (0, 0.22)], 8, c.sw("rubble"))
        ball.move(gx, gy1 - wt / 2, 1.15)
        c.add(ball, dice=None)
        banner(c, (gx + (0.24 if gx > 1.5 else -0.24), gy1 + 0.02, 1.08), 0.32, 0.62, normal=(0, 1), bar=False)
    sapling(c, (0.95, -1.7, 0), h=2.9, r=0.72)
    sapling(c, (2.05, 0.1, 0), h=2.5, r=0.62)
    for (bx, by) in ((1.95, -1.6), (0.85, 1.45)):
        pbox(c, 1.0, 0.55, 0.24, "planks", center=(bx, by, 0), taper=0.0)
        c.add(L.box(0.92, 0.47, 0.02, c.sw("dirt"), center=(bx, by, 0.24), base=True), dice=None)
        for k in range(4):
            hb = L.blob(c.sw("leaves"), radius=0.13, subdiv=1, scale=(1, 1, 0.8), seed=int(c.r(0, 9999)), noise_amp=0.25)
            hb.move(bx - 0.33 + k * 0.22, by + c.r(-0.06, 0.06), 0.24)
            c.add(hb, dice=None, tint=(1.0, 1.08, 0.9) if k % 2 else (0.85, 0.95, 0.8))
    pbox(c, 0.95, 0.3, 0.08, "oak", center=(2.3, 1.6, 0.42), taper=0.0)
    for sx_ in (1.95, 2.65):
        pbox(c, 0.12, 0.26, 0.42, "oak", center=(sx_, 1.6, 0.0), taper=0.0)
    return {"height_target": (5.0, 6.0)}

def k_wainwright_yard(c):
    """Wainwright Yard (siege workshop, 12x12 cells = 6 m): an open shed (gable to the front) with a
    wagon on the stocks, wheels leaning on the posts, and its sign: a giant wagon wheel (2.8 m) mounted
    high on a braced pole, tilted back so it reads as a full circle from the RTS camera. A finished
    wagon with an ivory canvas (one team stripe) waits in the yard."""
    zt = 2.5
    sx0, sx1, sy0, sy1 = -0.55, 2.85, -2.85, -0.35
    open_shed(c, sx0, sx1, sy0, sy1, zt, pitch_deg=50)
    wagon(c, (1.15, -1.55, 0.18), rz=90.0, length=2.0, width=0.95, h=0.5, wheel_r=0.42, team_band=False, four=False,
          shafts=False)
    for yy in (-2.25, -0.85):
        pbox(c, 0.75, 0.28, 0.3, "oak", center=(1.15, yy, 0.0))
    for (wx, wy) in ((sx0 - 0.12, -1.0), (sx1 + 0.12, -2.0)):
        for p in wheel(c, (wx, wy, 0.55), 0.55, axis="x", spokes=8, segs=12):
            p.rot(0, 14 if wx < 0 else -14, 0, pivot=(wx, wy, 0))
    # the sign: giant wheel on a braced pole, front left
    px_, py_ = -1.75, 0.35
    c.add(L.member((px_, py_, 0), (px_, py_, 3.65), 0.24, 0.24, c.sw("oak"), rng=c.rng, chamfer=0.04))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c.add(L.member((px_ + math.cos(a) * 0.7, py_ + math.sin(a) * 0.7, 0), (px_, py_, 1.3), 0.11, 0.11, c.sw("oak"),
                       rng=c.rng))
    pbox(c, 0.7, 0.7, 0.28, "rubble", center=(px_, py_, 0))
    c.add(L.member((px_, py_ - 0.1, 3.5), (px_, py_ + 0.45, 3.85), 0.14, 0.14, c.sw("iron")), dice=None)
    giant_wheel(c, (px_, py_ + 0.5, 3.95), 1.4, tilt=38.0, spokes=8)
    pennant(c, (px_, py_ - 0.15, 3.65), 1.6, 1.0, 0.4, dirn=(1, 0.35), phase=0.3, pole_r=0.05)
    # finished wagon with a canvas cover in the yard, spare spokes and felloes, a workbench
    wagon(c, (1.05, 1.55, 0.0), rz=-8.0, length=2.1, width=0.98, h=0.5, wheel_r=0.44, cover=True, team_band=False)
    for i in range(7):
        c.add(L.member((-2.6 + i * 0.07, 2.25, 0.05), (-1.85 + i * 0.07, 2.6, 0.05), 0.06, 0.06, c.sw("oak"), rng=c.rng))
    pbox(c, 1.5, 0.6, 0.12, "oak", center=(-2.0, -1.85, 0.78), taper=0.0)
    for sx_ in (-2.6, -1.4):
        for sy_ in (-2.05, -1.65):
            c.add(L.member((sx_, sy_, 0), (sx_, sy_, 0.78), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    c.add(L.box(0.5, 0.06, 0.05, c.sw("iron"), center=(-2.1, -1.8, 0.93)), dice=None)
    for p in wheel(c, (-2.0, -1.0, 0.07), 0.5, axis="z", spokes=8, segs=12):
        pass
    return {"height_target": (5.0, 6.0)}


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
    """Curio Cabinet (faction shop, 12x12 cells = 6 m): a narrow half-timber shopfront with its gable
    to the front, a wide shop window with a counter under a striped awning, and its sign: a giant
    painted chest of small drawers standing on a bracket shelf at the eaves in front of the gable; a
    market table, crates, barrels and a handcart on the pad."""
    t = 0.1
    x0, x1, y0, y1 = -2.75, 0.55, -2.7, 0.7
    zp, zw = 0.25, 2.45
    walls, _ = house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front",), ops={
        ("left", 0): [(0.5, 0.42, 0.95, 1.6, "window")],
        ("right", 0): [(0.3, 0.42, 0.95, 1.6, "window"), (0.7, 0.42, 0.95, 1.6, "window")]}, bay=0.85)
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ov = 0.3
    z_eave, z_ridge = roof_fit(zw, half, ov, 50, 0.14, y1 - y0 + 0.65)
    gable_roof(c, y0 - 0.3, y1 + 0.35, xm, half + ov, z_eave, z_ridge, th=0.14, t=0.14, nu=8, nv=5, axis="y", cx=xm,
               trim=0.11, ridge_w=0.16)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, zw, z_ridge - 0.17, t, door=(fw.L * 0.22, 0.95, 2.05), windows=[])
    # shop window with a counter board and goods
    sw0 = fw.L * 0.66
    window(c, fw, sw0, 0.95, 1.95, 1.35, shutters=False)
    for sgn in (-1, 1):
        c.add(L.member(fw.p(sw0 + sgn * 0.74, 0.85, 0.05), fw.p(sw0 + sgn * 0.74, 2.05, 0.05), 0.11, 0.1, c.sw("oak"),
                       rng=c.rng))
    c.add(L.member(fw.p(sw0 - 0.8, 2.05, 0.05), fw.p(sw0 + 0.8, 2.05, 0.05), 0.12, 0.1, c.sw("oak"), rng=c.rng))
    cx_, cy_ = fw.p(sw0, 0.0, 0.0)[:2]
    pbox(c, 1.55, 0.42, 0.08, "oak", center=(cx_, y1 + 0.2, 0.88), taper=0.0)
    for k in range(3):
        jar = L.lathe([(0, 0), (0.07, 0), (0.09, 0.08), (0.06, 0.16), (0.07, 0.19), (0, 0.19)], 7, c.sw("pal"))
        jar.move(cx_ - 0.45 + k * 0.4, y1 + 0.22, 0.96)
        c.P(jar, ("#C9B994", "#6E4A26", "#7E9A4A")[k], dice=None)
    awning(c, cx_ - 0.85, cx_ + 0.85, y1 + 0.02, 2.2, 0.75, 0.38, posts=False, stripes=True)
    # the sign: shelf on brackets at the eaves, giant painted chest of drawers on it
    yf = y1
    for sx in (xm - 0.55, xm + 0.55):
        c.add(L.member((sx, yf, zw - 0.45), (sx, yf + 0.55, zw + 0.02), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    pbox(c, 1.7, 0.66, 0.08, "oak", center=(xm, yf + 0.3, zw + 0.02), taper=0.0)
    drawer_chest(c, (xm, yf + 0.32, zw + 0.12), w=1.55, h=1.15, d=0.55, cols=3, rows=3)
    pennant(c, (xm, y0 - 0.25, z_ridge - 0.08), 0.55, 0.75, 0.3, dirn=(1, -0.3), phase=0.6)
    # market table, crates, barrels, handcart
    tx, ty = 1.75, 0.2
    trestle(c, (tx - 0.55, ty, 0), rz=90, w=0.7, h=0.78)
    trestle(c, (tx + 0.55, ty, 0), rz=90, w=0.7, h=0.78)
    pbox(c, 1.6, 0.75, 0.06, "planks", center=(tx, ty, 0.78), taper=0.0)
    for k in range(3):
        crate(c, (tx - 0.5 + k * 0.48, ty + c.r(-0.1, 0.1), 0.84), s=0.3, rz=c.r(-20, 20))
    for k, (bx, by) in enumerate(((1.25, -1.0), (1.8, -1.15), (2.45, -0.95))):
        barrel(c, (bx, by, 0), r=0.24, h=0.56)
    crate(c, (2.5, -2.0, 0), s=0.5, rz=10)
    crate(c, (2.45, -2.0, 0.5), s=0.38, rz=-15)
    crate(c, (1.85, -2.1, 0), s=0.44, rz=30)
    wagon(c, (1.7, 1.85, 0.0), rz=-25.0, length=1.2, width=0.75, h=0.38, wheel_r=0.36, four=False, team_band=False,
          shafts=True)
    return {"height_target": (4.5, 5.5)}

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
    "kingdom_croft": dict(fn=k_croft, cells=(8, 8), role="supply (Croft)"),
    "kingdom_oath_hall": dict(fn=k_oath_hall, cells=(12, 12), role="hero altar (Oath Hall)"),
    "kingdom_drill_yard": dict(fn=k_drill_yard, cells=(12, 12), role="barracks (Drill Yard)"),
    "kingdom_timber_yard": dict(fn=k_timber_yard, cells=(12, 12), role="lumber drop-off (Timber Yard)"),
    "kingdom_foundry": dict(fn=k_foundry, cells=(12, 12), role="smithy (Foundry)"),
    "kingdom_collegium": dict(fn=k_collegium, cells=(12, 12), role="caster hall (Collegium)"),
    "kingdom_wainwright_yard": dict(fn=k_wainwright_yard, cells=(12, 12), role="siege workshop (Wainwright Yard)"),
    "kingdom_curio_cabinet": dict(fn=k_curio_cabinet, cells=(12, 12), role="faction shop (Curio Cabinet)"),
    "kingdom_lookout": dict(fn=k_lookout, cells=(4, 4), role="scout tower (Lookout)"),
    "kingdom_gun_tower": dict(fn=k_gun_tower, cells=(4, 4), role="gun tower (Lookout upgrade)"),
    "kingdom_walled_burg": dict(fn=k_walled_burg, cells=(16, 16), role="T2 hall upgrade: add-on to kingdom_moot_hall",
                                addon_of="kingdom_moot_hall"),
}
CLANS = {
    "clans_home_yurt": dict(fn=c_home_yurt, cells=(8, 8), role="supply + worker garrison (Home Yurt)"),
    "clans_grapple_yard": dict(fn=c_grapple_yard, cells=(12, 12), role="barracks (Grapple Yard)"),
    "clans_naming_stones": dict(fn=c_naming_stones, cells=(12, 12), role="hero altar (Naming Stones)"),
    "clans_casting_pit": dict(fn=c_casting_pit, cells=(12, 12), role="war mill + lumber drop-off (Casting Pit)"),
    "clans_mirror_yurt": dict(fn=c_mirror_yurt, cells=(12, 12), role="caster lodge (Mirror Yurt)"),
    "clans_bow_mast": dict(fn=c_bow_mast, cells=(4, 4), role="tower (Bow-Mast)"),
    "clans_tea_tent": dict(fn=c_tea_tent, cells=(12, 12), role="faction shop (Tea Tent)"),
    "clans_banner_shell": dict(fn=c_banner_shell, cells=(16, 16), role="T2 hall upgrade: add-on to clans_shell_hall",
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
    anchors = {k: [round(float(v[0]), 3), round(float(v[2]), 3), round(float(-v[1]), 3)] for k, v in c.anchors.items()}
    extras = {
        "vibecraft": {
            "id": aid, "kit": "tools/kits/buildings.py", "footprint_cells": list(spec["cells"]),
            "facing": "front faces -Z; spawn with yaw = PI so the door faces the default +Z RTS camera",
            "build_progress": "reveal bottom-up: discard fragments whose UV2.y > progress (+ noise band); "
                              "clans two-pass: UV2.x = 0 lattice/frame first, 1 felt/cover second "
                              "(tools/kits/build_reveal.gdshader)",
        }
    }
    if anchors:
        extras["vibecraft"]["anchors"] = anchors
    path = os.path.join(out_dir, aid + ".glb")
    st = L.export_glb(path, aid, parts, H, c.bake, sheets_for(faction), extras=extras,
                      piping=(c.S["pal"], L.palette_uv(c.pal, PIPING[faction])))
    v = np.concatenate([p.v for p in parts])
    lo, hi = v.min(0), v.max(0)
    rec = {
        "id": aid, "faction": faction, "role": spec.get("role", ""),
        "footprint_cells": list(spec["cells"]), "footprint_m": [round(c.fp[0], 3), round(c.fp[1], 3)],
        "height_m": round(H, 3), "bounds_m": {"x": [round(lo[0], 3), round(hi[0], 3)], "z_godot": [round(-hi[1], 3), round(-lo[1], 3)]},
        "tris": st["tris"], "materials": st["materials"], "file_bytes": os.path.getsize(path),
        "team_piping_tris": st["team_piping_tris"],
        "notes": " ".join((spec["fn"].__doc__ or "").split()), "seconds": round(time.time() - t0, 1),
    }
    if "height_target" in info:
        rec["height_target_m"] = list(info["height_target"])
    if anchors:
        rec["anchors_godot"] = anchors
    if info.get("budget_note"):
        rec["budget_note"] = info["budget_note"]
    if spec.get("addon_of"):
        rec["addon_of"] = spec["addon_of"]
        rec["footprint_m"] = [8.0, 8.0]
        rec["placement"] = (f"add-on in the {spec['addon_of']}.glb model space (8 m model): same parent and transform as "
                            f"the T1 hall, show both after the upgrade")
    L.log(f"{aid}: {st['tris']} tris, H {H:.2f} m, {rec['file_bytes'] / 1e6:.2f} MB, {rec['seconds']} s")
    if os.environ.get("VC_TRIS_DEBUG"):
        L.log("  cuts:", sorted(st.get("cut_by_swatch", {}).items(), key=lambda kv: -kv[1][1]))
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
        for f in ("kingdom", "clans"):
            sheets_for(f)
        for sh in (_SHEETS["kingdom"], _SHEETS["clans"], _SHEETS["team"], _SHEETS["glow"]):
            L.log("sheet:", sh.write(args.out_dir), sh.size, f"fill {sh.fill}")
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
