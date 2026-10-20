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
-Z in Godot (+Y in the build space used here; UnitView draws structures at a fixed yaw of PI so the door
faces the +Z RTS camera), footprint = faction-doc cells x 0.5 m (art bible 1.3, decided 2026-10-19:
supply 8x8 = 4 m, production / altar / shop / research 12x12 = 6 m, towers 4x4 = 2 m, halls 16x16 = 8 m),
heights per art bible 1.3. Every building stands on a ground apron (1.5 cm above y = 0, a skirt to
-0.2 m). One opaque atlas material + <id>_GLOW + <id>_TEAM. Vertex colour = painted AO; UV2.y =
normalized height, UV2.x = build layer (0 structure / lattice, 1 covering / felt) for the two-pass
"Raising" reveal (tools/kits/build_reveal.gdshader computes the height from VERTEX.y, so it also works
on the AI halls).
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
        # roof: 7 tile courses per swatch copy over 2.1 m = ~0.3 m courses (the Moot Hall's tile scale)
        "roof": Swatch("roof", L.swatch_img(MAT + "kingdom_burgundy_roof_tiles.png", "period", grade_to="#7B2C36",
                                            sat_cap=0.65), 2.1),
        # rubble / cobbles: big stones 0.5-0.7 m, small ones 0.25 m (the AI halls' plinth stones)
        "rubble": Swatch("rubble", L.swatch_img(MAT + "kingdom_rubble_stone.png", "crossfade"), 3.0),
        "bronze": Swatch("bronze", L.tex_bronze(base="#4E3E30", hi="#A08458", dark="#231C17"), 1.6),
        "scales": Swatch("scales", L.swatch_img(MAT + "kingdom_bronze_scale_roof.png", "period", grade_to="#7C5631",
                                                sat_cap=0.62, v_floor=0.5, sat=0.3), 2.8),
        "planks": Swatch("planks", L.swatch_img(MAT + "kingdom_painted_planks.png", "periodx", sat_cap=0.6), 1.5),
        "iron": Swatch("iron", L.tex_iron(), 1.0),
        "brick": Swatch("brick", L.tex_brick(), 1.6),
        "straw": Swatch("straw", L.tex_straw(), 1.2),
        "bark": Swatch("bark", L.swatch_img(TER + "bark_oak.png", "none", sat_cap=0.55), 1.2),
        "rings": Swatch("rings", L.tex_rings(), kind="decal", px=160),
        "wattle": Swatch("wattle", L.tex_wattle(), 0.9),
        "leaves": Swatch("leaves", graded(L.tex_leaves(), mean="#45602F", sat_cap=0.5), 1.6),
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
        "glyph_hail": Swatch("glyph_hail", L.tex_glyph_stone(which="hail"), kind="decal", px=192),
        "glyph_wind": Swatch("glyph_wind", L.tex_glyph_stone(which="wind"), kind="decal", px=192),
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
    "clay": (0.7, 0.02, 50), "bronze": (None, 0.0, 60), "glyph_hail": (None, 0.0, 40), "glyph_wind": (None, 0.0, 40),
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
# ground apron (every building): one selectable base instead of props scattered on the grass
# =============================================================================================

APRON_Z = 0.015      # apron top: 1.5 cm above the terrain (y = 0)
SKIRT_Z = -0.2       # skirt bottom: terrain bumps under the building never open a gap


def apron_outline(c, inset=0.06, n_exp=5.0, noise=0.06, N=72, scale=(1.0, 1.0)):
    """Irregular rounded-square ('squircle', exponent n_exp) outline inside the footprint. The radial
    noise only pulls inwards, so the apron never leaves the footprint."""
    hx, hy = c.fp[0] / 2 * scale[0] - inset, c.fp[1] / 2 * scale[1] - inset
    ph = [c.r(0, 6.28) for _ in range(2)]
    pts = []
    for k in range(N):
        t = 2 * math.pi * k / N
        ct, st = math.cos(t), math.sin(t)
        x = hx * math.copysign(abs(ct) ** (2 / n_exp), ct)
        y = hy * math.copysign(abs(st) ** (2 / n_exp), st)
        w = noise * (0.55 + 0.25 * math.sin(3 * t + ph[0]) + 0.2 * math.sin(7 * t + ph[1]))
        r = math.hypot(x, y)
        f = max(0.0, 1 - w / max(r, 1e-6))
        pts.append((x * f, y * f))
    return np.array(pts)


def _shrink(ol, d):
    r = np.linalg.norm(ol, axis=1, keepdims=True)
    return ol * np.maximum(r - d, 0.0) / np.maximum(r, 1e-6)


def _runs(ol, gaps):
    """Split a closed outline into open runs, leaving out points in front-side gaps [(x, half_w)]."""
    keep = np.array([not any(p[1] > 0 and abs(p[0] - gx) < gw for gx, gw in gaps) for p in ol])
    if keep.all():
        return [(ol, True)]
    k0 = int(np.flatnonzero(~keep)[0])
    order = [(k0 + i) % len(ol) for i in range(len(ol))]
    runs, cur = [], []
    for i in order:
        if keep[i]:
            cur.append(ol[i])
        elif cur:
            runs.append((np.array(cur), False))
            cur = []
    if cur:
        runs.append((np.array(cur), False))
    return [r for r in runs if len(r[0]) >= 2]


def apron(c, key="dirt", inset=0.06, n_exp=5.0, noise=0.06, gaps=(), edge="kerb", tint=None, scale=(1.0, 1.0)):
    """Ground apron covering the footprint: top 1.5 cm above the ground, a skirt down to -0.2 m (hidden
    in the terrain), painted AO from the building on it. edge: "kerb" (kingdom: a timber kerb),
    "curb" (clans: a low drystone curb), None. gaps: openings in the edge on the front side
    [(x_centre, half_width)]. Returns the outline."""
    ol = apron_outline(c, inset, n_exp, noise, scale=scale)
    p = L.prism(ol, SKIRT_Z, APRON_Z, c.sw(key), chamfer=0.03, grid=0.7, bottom=False)
    c.add(p, jit=0.0, below=True, base=False, form=0.0, smooth=60.0, tint=tint if tint is not None else (1, 1, 1))
    if edge:
        k = 40
        idx = np.linspace(0, len(ol), k, endpoint=False).astype(int)
        e_ol = _shrink(ol[idx], 0.11)
        for run, closed in _runs(e_ol, gaps):
            if edge == "kerb":
                path = np.concatenate([run, np.full((len(run), 1), APRON_Z + 0.04)], 1)
                kb = L.sweep(L.rect_profile(0.14, 0.11), path, c.sw("oak"), closed_path=closed, up=(0, 0, 1))
                c.add(kb, jit=0.012, tint=(0.85, 0.82, 0.8))
            else:
                path = np.concatenate([run, np.full((len(run), 1), APRON_Z + 0.05)], 1)
                sc = np.array([0.8 + 0.4 * abs(math.sin(i * 1.7 + 0.3)) for i in range(len(run))])
                prof = np.array([(0.13, -0.06), (0.1, 0.06), (0.0, 0.09), (-0.1, 0.06), (-0.13, -0.06)])
                cb = L.sweep(prof, path, c.sw("drystone"), closed_path=closed, up=(0, 0, 1),
                             scales=np.stack([np.ones(len(run)), sc], 1))
                c.add(cb, jit=0.03, dice=None)
    return ol


def cobbles(c, x0, x1, y0, y1, z=0.035, key="rubble", jit=0.05):
    """Cobbled path / forecourt patch (kingdom) sitting on the apron."""
    ol = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    ol = L._poly_subdiv(ol, 0.45)
    ol = ol + np.array([[c.r(-jit, jit), c.r(-jit, jit)] for _ in ol]) * np.array([1, 1])
    p = L.prism(ol, -0.05, z, c.sw(key), chamfer=0.02, grid=0.6, bottom=False)
    return c.add(p, jit=0.0, below=True, base=False, form=0.0, tint=(0.95, 0.93, 0.9))


def rug(c, cx, cy, w, d, rz=0.0, key="teal", tint=(1, 1, 1)):
    """Felt rug on the clans apron."""
    return pbox(c, w, d, 0.035, key, center=(cx, cy, APRON_Z - 0.005), taper=0.0, chamfer=0.012, rz=rz, jit=0.0,
                layer=1.0, tint=tint, base=False)


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
            mem(s, z0, s, z1, w=t * 1.15, d=dep * 1.1, o=off + 0.008)       # corner posts stand proud
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
                mem(sa, z0 + t, sa, z1 - t, w=t * 0.9, o=off - 0.006)     # studs set back 6 mm
        cen = (sa + sb) / 2
        here = [o for o in ops if sa - 1e-6 <= o[0] <= sb + 1e-6]
        if here:
            continue
        if braces:
            if b == 0:
                mem(sa + t * 0.4, zr, sb - t * 0.3, z1 - t, w=t * 0.85, o=off - 0.012)
                mem(sa + t * 0.4, z0 + t, sb - t * 0.3, zr, w=t * 0.85, o=off - 0.012)
            elif b == nb - 1:
                mem(sb - t * 0.4, zr, sa + t * 0.3, z1 - t, w=t * 0.85, o=off - 0.012)
                mem(sb - t * 0.4, z0 + t, sa + t * 0.3, zr, w=t * 0.85, o=off - 0.012)
            elif rail:
                mem(sa + t * 0.4, z0 + t, sb - t * 0.4, z1 - t, w=t * 0.8, o=off - 0.012)
                mem(sb - t * 0.4, z0 + t, sa + t * 0.4, z1 - t, w=t * 0.8, o=off - 0.012)
    for (s, w, zb, zt, kind) in ops:
        a, b2 = s - w / 2 - t / 2, s + w / 2 + t / 2
        mem(a, z0 + t, a, z1 - t, w=t)
        mem(b2, z0 + t, b2, z1 - t, w=t)
        if kind != "door":
            mem(a, zb - t / 2, b2, zb - t / 2, w=t * 0.95, d=dep * 1.25, o=off + 0.02)   # window sill
        if zt < z1 - t * 1.5:
            mem(a, zt + t / 2, b2, zt + t / 2, w=t * 1.05, o=off + 0.006)              # lintel
            if kind == "door":
                mem(a, zt + t, s, z1 - t, w=t * 0.8, o=off - 0.012)
                mem(b2, zt + t, s, z1 - t, w=t * 0.8, o=off - 0.012)
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
    face +-y (the front). Hand-made read: the ridge sags `sag` m (default 2 cm per metre of ridge, 4-8 cm),
    the eave line wanders by +-eave_jit, chunky eave trim boards (trim m) and bargeboards (t m) stand
    proud of the tiles so they show from the high camera."""
    sw = c.sw(key)
    rep = sw.repeat
    Lx = x1 - x0
    xm = (x0 + x1) / 2
    if sag is None:
        sag = float(np.clip(0.02 * Lx, 0.04, 0.08))      # a 4-8 cm hand-laid ridge sag
    ph = c.r(0, 6.28)
    ph2 = c.r(0, 6.28)
    ph3 = c.r(0, 6.28)

    def eave_off(x, side):
        return eave_jit * (0.6 * math.sin(2.1 * x + ph + side) + 0.4 * math.sin(5.3 * x + ph2 - side))

    def ridge_off(x):
        # hand-laid ridge: a 1.5-2 cm wander in height and plan (same for both slopes)
        return (0.012 * math.sin(3.1 * x + ph3), 0.018 * math.sin(2.3 * x + ph2) + 0.008 * math.sin(6.1 * x + ph))

    def surf(x, f, side):
        xr = 2 * (x - xm) / Lx
        zf = f + flare * f * (1 - f)
        z = z_ridge - (z_ridge - z_eave) * zf
        z += -sag * (1 - xr * xr) * (1 - f * 0.6)
        z += kick * (xr ** 4) * f * f
        z += eave_off(x, side) * f ** 3
        ry, rz = ridge_off(x)
        z += rz * (1 - f) ** 2
        y = yc + side * (half * f + 0.5 * eave_off(x * 1.3, -side) * f ** 3) + ry * (1 - f) ** 2
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
            ry, rz = ridge_off(x)
            path.append((x, yc + ry, z_ridge - sag * (1 - xr * xr) + rz + 0.015))
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
    sag = float(np.clip(0.02 * ridge_len, 0.04, 0.08))
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


def half_hip_roof(c, x0w, x1w, y0w, y1w, zw, pitch=44.0, ov=0.3, ovg=0.32, clip=0.6, th=0.13, key="roof",
                  hip_front=True, hip_back=True, sag=0.06, kick=0.07, eave_jit=0.03, t=0.13, trim=0.11, ridge_w=0.15):
    """Half-hipped (jerkinhead) roof over the wall box [x0w, x1w] x [y0w, y1w] with top zw, ridge along y
    (gables to the front and the back, their tops clipped by small hips). Planar slopes of one pitch, th
    thick, then hand-made: the ridge sags `sag` m and wanders, the eave corners kick up, the eaves wander
    +-eave_jit, oak bargeboards on the verges, eave trim boards and oak hip boards stand proud; the ridge
    tiles are the team band. Returns {z_eave, z_ridge, z_clip, wall_clip, wall_apex, wall_eave, rf, rb}."""
    xm = (x0w + x1w) / 2
    half = (x1w - x0w) / 2 + ov
    sl = math.tan(math.radians(pitch))
    ze = zw + th + 0.05 - sl * ov
    zr = ze + sl * half
    x0, x1 = xm - half, xm + half
    y0, y1 = y0w - ovg, y1w + ovg
    zc = ze + (zr - ze) * clip
    xc = half * (1 - clip)
    yf = y1 - xc if hip_front else y1
    yb = y0 + xc if hip_back else y0
    P = {"e0": (x0, y0, ze), "e1": (x1, y0, ze), "e2": (x1, y1, ze), "e3": (x0, y1, ze),
         "rb": (xm, yb, zr), "rf": (xm, yf, zr),
         "cbl": (xm - xc, y0, zc), "cbr": (xm + xc, y0, zc), "cfl": (xm - xc, y1, zc), "cfr": (xm + xc, y1, zc)}
    names = list(P)
    V = [P[k] for k in names]
    ix = {k: i for i, k in enumerate(names)}
    left = ["e0"] + (["cbl"] if hip_back else []) + ["rb", "rf"] + (["cfl"] if hip_front else []) + ["e3"]
    right = ["e1", "e2"] + (["cfr"] if hip_front else []) + ["rf", "rb"] + (["cbr"] if hip_back else [])
    faces = [[ix[k] for k in left], [ix[k] for k in right]]
    if hip_front:
        faces.append([ix["cfr"], ix["cfl"], ix["rf"]])
    if hip_back:
        faces.append([ix["cbl"], ix["cbr"], ix["rb"]])
    ph, ph2, ph3 = c.r(0, 6.28), c.r(0, 6.28), c.r(0, 6.28)
    ym = (y0 + y1) / 2

    def deform(v):
        v = np.array(v, float).copy()
        one = v.ndim == 1
        v = v.reshape(-1, 3)
        hgt = np.clip((v[:, 2] - ze) / max(zr - ze, 1e-6), 0, 1)
        yr = 2 * (v[:, 1] - ym) / (y1 - y0)
        xr = (v[:, 0] - xm) / half
        dz = -sag * (1 - np.minimum(yr * yr, 1)) * hgt ** 2
        dz += kick * (np.abs(xr) * np.abs(yr)) ** 3
        dz -= 0.05 * (zr - ze) * hgt * (1 - hgt)
        f = 1 - hgt
        dz += eave_jit * (0.6 * np.sin(2.1 * v[:, 1] + ph) + 0.4 * np.sin(5.3 * v[:, 0] + ph2)) * f ** 3
        dz += 0.015 * np.sin(2.3 * v[:, 1] + ph3) * hgt ** 4
        v[:, 2] += dz
        v[:, 0] += 0.014 * np.sin(3.1 * v[:, 1] + ph3) * hgt ** 4
        return v[0] if one else v

    out = roof_solid(c, V, faces, th, key, deform, dice=0.4)
    oak = c.sw("oak")

    def line(a, b, n=8):
        a, b = np.asarray(a, float), np.asarray(b, float)
        return deform(np.array([a + (b - a) * i / n for i in range(n + 1)]))

    # team ridge-tile band
    w = ridge_w
    prof = np.array([(w * 0.3, w * 0.62), (0.0, w * 0.55), (-w * 0.5, 0.0), (0.0, -w * 0.55), (w * 0.3, -w * 0.62)])
    rp = L.sweep(prof, line(P["rb"], P["rf"]) + np.array([0, 0, 0.012]), c.sw("team_band"), up=(1, 0, 0))
    normalize_v(rp)
    out.append(c.add(rp, layer=1.0))
    # oak hip boards
    hips = []
    if hip_front:
        hips += [("rf", "cfl"), ("rf", "cfr")]
    if hip_back:
        hips += [("rb", "cbl"), ("rb", "cbr")]
    for a, b in hips:
        pts = line(P[a], P[b], 6) + np.array([0, 0, 0.02])
        d = np.asarray(P[b]) - np.asarray(P[a])
        upv = nrm(np.cross(np.cross(d, [0, 0, 1.0]), d))
        side = nrm(np.cross(d, upv))
        hp = L.sweep(prof * np.array([0.75, 0.9]), pts, oak, up=tuple(side))
        out.append(c.add(hp, layer=1.0, tint=(0.8, 0.78, 0.76)))
    # bargeboards on the verges (stand ~t proud, 10-15 cm thick read)
    verges = []
    for (ya, ca, cb_) in ((y1, "cfl", "cfr"), (y0, "cbl", "cbr")):
        hipped = hip_front if ya == y1 else hip_back
        top_l = P[ca] if hipped else (xm, ya, zr)
        top_r = P[cb_] if hipped else (xm, ya, zr)
        verges += [((x0, ya, ze), top_l, ya), ((x1, ya, ze), top_r, ya)]
    for a, b, ya in verges:
        sgn = -1 if ya > ym else 1
        a = np.asarray(a, float) + np.array([0, sgn * t * 0.4, 0])
        b = np.asarray(b, float) + np.array([0, sgn * t * 0.4, 0])
        pts = line(a, b, 3) + np.array([0, 0, t * 0.3])
        for k in range(len(pts) - 1):
            out.append(c.add(L.member(pts[k], pts[k + 1], t * 0.9, t * 1.3, oak, rng=c.rng, roll_up=(0, 1, 0))))
    # eave trim boards along both long eaves
    for xe, sgn in ((x0, -1), (x1, 1)):
        pts = line((xe, y0 + 0.02, ze), (xe, y1 - 0.02, ze), 8) + np.array([sgn * 0.02, 0, -th * 0.35])
        tb = L.sweep(L.rect_profile(trim * 0.9, trim + th * 0.6), pts, oak, up=(0, 0, 1))
        out.append(c.add(tb, layer=1.0, jit=0.0))
    # where the wall planes meet the roof underside (for the gable walls under it)
    clr = th + 0.05
    return {"z_eave": ze, "z_ridge": zr, "z_clip": zc, "rf": P["rf"], "rb": P["rb"],
            "wall_eave": ze + sl * ov - clr, "wall_apex": zr - clr,
            "wall_clip_front": (zc + sl * ovg - clr) if hip_front else None,
            "wall_clip_back": (zc + sl * ovg - clr) if hip_back else None}


def mono_roof(c, x0, x1, y_hi, y_lo, z_hi, z_lo, th=0.14, key="roof", fascia=True, rafters=True, t=0.14, eave_jit=0.03):
    """Mono-pitch (lean-to) roof: the high eave along y_hi at z_hi, falling to y_lo at z_lo; [x0, x1] incl.
    overhang. Thick, a little sagging between the posts, a wandering eave, chunky rafter ends and a
    fascia board on the high side."""
    V = [(x0, y_lo, z_lo), (x1, y_lo, z_lo), (x1, y_hi, z_hi), (x0, y_hi, z_hi)]
    if (y_hi - y_lo) < 0:
        face = [[1, 0, 3, 2]]
    else:
        face = [[0, 1, 2, 3]]
    ph = c.r(0, 6.28)
    xm, Lx = (x0 + x1) / 2, (x1 - x0)

    def deform(v):
        v = v.copy()
        xr = 2 * (v[:, 0] - xm) / Lx
        f = np.clip((v[:, 1] - y_lo) / (y_hi - y_lo), 0, 1)
        v[:, 2] -= 0.05 * (1 - xr * xr) * (1 - np.abs(2 * f - 1))
        v[:, 2] += eave_jit * np.sin(2.3 * v[:, 0] + ph) * (np.abs(2 * f - 1) ** 3)
        return v
    out = roof_solid(c, V, face, th, key, deform, dice=0.45)
    oak = c.sw("oak")
    if fascia:
        n = 8
        pts = deform(np.array([(x0 + (x1 - x0) * i / n, y_hi, z_hi) for i in range(n + 1)])) - np.array([0, 0, th * 0.4])
        fb = L.sweep(L.rect_profile(t * 0.7, t * 1.6), pts + np.array([0, 0.03 * np.sign(y_hi - y_lo), 0]), oak, up=(0, 0, 1))
        out.append(c.add(fb, layer=1.0))
    if rafters:
        nr = max(3, int(round((x1 - x0) / 0.7)))
        d = np.array([0, y_hi - y_lo, z_hi - z_lo])
        d = d / np.linalg.norm(d)
        for i in range(nr + 1):
            x = x0 + 0.12 + (x1 - x0 - 0.24) * i / nr
            a = np.array([x, y_lo, z_lo]) - np.array([0, 0, th + 0.05])
            b = np.array([x, y_hi, z_hi]) - np.array([0, 0, th + 0.05]) + d * 0.12
            out.append(c.add(L.member(a, b, t * 0.6, t * 0.75, oak, rng=c.rng), layer=0.0))
    return out


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
               apex_window=None, clip_z=None):
    """Kingdom gable-front wall: plaster pentagon (eave walls + gable triangle up to the roof) in a
    timber frame, a door that may rise above the eave line (doors stay ~2 m for 1.75 m units), shuttered
    windows. door = (s, w, h); windows = [(s, zb, zt, w)]; apex_window = (zb, zt, w) in the gable.
    clip_z: half-hipped gable, the triangle is cut flat at clip_z (under the little hip)."""
    Lw = wall.L
    if clip_z is not None and clip_z < z_apex - 0.05:
        xw = (Lw / 2) * (z_apex - clip_z) / max(z_apex - z_eave, 1e-6)
        ol = [(0.0, z0), (Lw, z0), (Lw, z_eave), (Lw / 2 + xw, clip_z), (Lw / 2 - xw, clip_z), (0.0, z_eave)]
    else:
        clip_z, xw = None, 0.0
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
        mem(s_, z0, s_, z_eave + t * 0.3, w=t * 1.2, d=dep * 1.1, oo=o + 0.008)
    # rafters along the gable edges (to the clip line of a half-hipped gable)
    if clip_z is None:
        for s_a, s_b in ((0.0, Lw / 2), (Lw, Lw / 2)):
            mem(s_a, z_eave - t * 0.2, s_b, z_apex - t * 0.6, w=t * 1.05, oo=o + 0.006)
    else:
        for s_a, s_b in ((0.0, Lw / 2 - xw), (Lw, Lw / 2 + xw)):
            mem(s_a, z_eave - t * 0.2, s_b, clip_z - t * 0.5, w=t * 1.05, oo=o + 0.006)
        mem(Lw / 2 - xw - t * 0.3, clip_z - t * 0.5, Lw / 2 + xw + t * 0.3, clip_z - t * 0.5, w=t * 1.1, oo=o + 0.01)
        z_apex = clip_z + t * 0.3
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
        mem(Lw / 2, kp0, Lw / 2, z_apex - t * 0.8, w=t, oo=o - 0.006)
    hz = z_eave + (z_apex - z_eave) * 0.45
    hw = (Lw / 2) * (1 - 0.45)
    if not door or kp0 < hz - t:
        mem(Lw / 2 - hw + t * 0.4, hz, Lw / 2 + hw - t * 0.4, hz, w=t * 0.9, oo=o - 0.012)
    for sgn in (-1, 1):
        mem(Lw / 2 + sgn * Lw * 0.14, kp0 + t * 0.4 if kp0 < hz else hz, Lw / 2 + sgn * Lw * 0.36,
            z_eave + t * 0.4, w=t * 0.85, oo=o - 0.012)
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


def onion_dome(c, center, r, h, key="bronze", team_ring=True, finial_h=None, sides=16, repeat=None, ribs=7,
               tint=(1.0, 1.0, 1.0), wheel_finial=True):
    """Smooth dark-bronze onion dome (base radius r at center z, height h without finial) with `ribs`
    raised vertical ribs, a team ring under it and a pointed iron finial carrying the Ember Wheel."""
    x, y, z = center
    prof = [(r * 0.98, 0.0), (r * 1.12, h * 0.1), (r * 1.22, h * 0.24), (r * 1.16, h * 0.38),
            (r * 0.88, h * 0.54), (r * 0.5, h * 0.7), (r * 0.24, h * 0.82), (r * 0.12, h * 0.91), (r * 0.07, h * 0.97),
            (0.0, h)]
    d = L.lathe(prof, sides, c.sw(key), smooth=75.0, repeat=repeat)
    d.move(x, y, z)
    c.add(d, dice=None, layer=1.0, tint=tint)
    for k in range(ribs):
        a = k * 2 * math.pi / ribs + math.pi / ribs
        pts = [(x + math.cos(a) * (pr + 0.006), y + math.sin(a) * (pr + 0.006), z + pz) for pr, pz in prof[1:-2]]
        rib = L.sweep(np.array([(0.0, max(0.025, r * 0.05)), (-max(0.02, r * 0.04), 0.0), (0.0, -max(0.025, r * 0.05)),
                                (max(0.012, r * 0.02), 0.0)]), np.array(pts), c.sw(key), up=(0, 0, 1))
        c.add(rib, dice=None, layer=1.0, tint=(1.35, 1.2, 1.0))
    if team_ring:
        ring = L.lathe([(r * 1.04, -0.10 * r - 0.04), (r * 1.09, -0.02), (r * 1.04, 0.06 * r + 0.04)], sides,
                       c.sw("team_band"), int_repeat=True)
        ring.uv[..., 1] = np.where(ring.v[ring.t][..., 2] > 0, 0.0, 1.0)
        ring.move(x, y, z)
        c.add(ring, dice=None, layer=1.0)
    fh = finial_h if finial_h is not None else h * 0.6
    spike = L.lathe([(r * 0.09, 0), (r * 0.12, fh * 0.12), (r * 0.06, fh * 0.2), (r * 0.045, fh * 0.75), (0.0, fh)], 8,
                    c.sw("iron"))
    spike.move(x, y, z + h * 0.95)
    c.add(spike, dice=None)
    if wheel_finial:
        wr = max(0.13, r * 0.3)
        wheel(c, (x, y, z + h * 0.95 + fh * 0.52), wr, axis="y", spokes=6, key="iron", iron=False,
              width=wr * 0.2, rim_w=wr * 0.22)


def stork_nest(c, pos, r=0.55, stork=True, facing=0.0):
    """Big stork nest (1.0-1.2 m across) of straw and chunky sticks, a large white stork standing in it
    (black flight feathers, red bill and legs): the Croft's upper-third read."""
    x, y, z = pos
    nest = L.lathe([(r * 0.5, -0.04), (r * 0.92, r * 0.12), (r * 1.04, r * 0.38), (r * 0.86, r * 0.56),
                    (r * 0.55, r * 0.46), (0, r * 0.42)], 11, c.sw("straw"))
    nest.move(x, y, z)
    c.add(nest, jit=0.04, dice=None, tint=(0.85, 0.78, 0.68))
    for k in range(9):
        a = k * 2 * math.pi / 9 + c.r(0, 0.4)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        p0 = np.array(pos) + d * r * 0.55 + np.array([0, 0, r * 0.42 + c.r(-0.05, 0.05)])
        p1 = p0 + d * r * 0.62 + np.array([-d[1], d[0], 0]) * c.r(-0.15, 0.15) + np.array([0, 0, c.r(-0.12, 0.1)])
        c.add(L.member(p0, p1, 0.05, 0.05, c.sw("oak"), rng=c.rng), tint=(0.9, 0.85, 0.8))
    if stork:
        s = r * 1.25
        bz = z + r * 0.45
        parts = []
        body = L.blob(c.sw("pal"), radius=s * 0.42, subdiv=1, scale=(1.15, 0.62, 0.6), seed=3, noise_amp=0.02)
        body.move(x, y, bz + s * 0.38)
        parts.append((body, "#F4F1EA"))
        for sgn in (-1, 1):
            wing = L.blob(c.sw("pal"), radius=s * 0.33, subdiv=1, scale=(1.25, 0.3, 0.42), seed=4 + sgn, noise_amp=0.02)
            wing.rot(0, -12, 0).move(x - s * 0.16, y + sgn * s * 0.2, bz + s * 0.46)
            parts.append((wing, "#26221F"))
        neck = L.member((x + s * 0.32, y, bz + s * 0.5), (x + s * 0.46, y, bz + s * 0.98), s * 0.12, s * 0.12, c.sw("pal"))
        parts.append((neck, "#F4F1EA"))
        head = L.blob(c.sw("pal"), radius=s * 0.12, subdiv=1, scale=(1.2, 0.9, 0.9), seed=6, noise_amp=0.0)
        head.move(x + s * 0.5, y, bz + s * 0.94)
        parts.append((head, "#F4F1EA"))
        bill = L.lathe([(s * 0.05, 0), (s * 0.035, s * 0.2), (0.0, s * 0.36)], 6, c.sw("pal"))
        bill.rot(0, 100, 0).move(x + s * 0.58, y, bz + s * 1.02)
        parts.append((bill, "#C8502A"))
        for sgn in (-1, 1):
            leg = L.member((x + s * 0.02, y + sgn * s * 0.09, bz - 0.02), (x + s * 0.04, y + sgn * s * 0.09, bz + s * 0.3),
                           s * 0.05, s * 0.05, c.sw("pal"))
            parts.append((leg, "#C8502A"))
        tail = L.blob(c.sw("pal"), radius=s * 0.16, subdiv=1, scale=(1.3, 0.7, 0.4), seed=8, noise_amp=0.02)
        tail.rot(0, 18, 0).move(x - s * 0.5, y, bz + s * 0.36)
        parts.append((tail, "#26221F"))
        for p, col in parts:
            p.rot(0, 0, facing, pivot=(x, y, z))
            c.P(p, col, dice=None, min_shade=0.55 if col == "#F4F1EA" else 0.0)


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


def linden_tree(c, pos, h=2.9, seed=0):
    """Garden linden after the doodad kit's tree_linden (spec_linden scaled to 2.5-3 m): a visible trunk
    and a rounded cone crown of overlapping leaf clusters (rings of 5, 3 and a top cluster, squashed
    0.95), dark leaf swatch at <= 50 % saturation, lighter towards the top."""
    x, y, z = pos
    k = h / 6.6
    rng = np.random.default_rng(seed)
    tr = L.lathe([(0.34 * k * 1.4, 0), (0.3 * k, 0.4 * k), (0.24 * k, 2.5 * k), (0.12 * k, 3.6 * k)], 7, c.sw("bark"))
    tr.move(x, y, z)
    c.add(tr, dice=None, uvrot=True)
    a0 = rng.uniform(0, 6.28)
    cl = []
    for i in range(5):
        a = a0 + i * 2 * math.pi / 5 + rng.uniform(-0.15, 0.15)
        cl.append((math.cos(a) * 1.2 * k, math.sin(a) * 1.2 * k, 3.15 * k, 1.42 * k, 0.82))
    for i in range(3):
        a = a0 + 0.6 + i * 2 * math.pi / 3
        cl.append((math.cos(a) * 0.75 * k, math.sin(a) * 0.75 * k, 4.4 * k, 1.2 * k, 0.95))
    cl.append((0.0, 0.0, 5.55 * k, 0.95 * k, 1.08))
    for i, (cx_, cy_, cz, R, shade) in enumerate(cl):
        b = L.blob(c.sw("leaves"), radius=R, subdiv=1, scale=(1, 1, 0.92), seed=int(rng.integers(0, 9999)),
                   noise_amp=0.16, noise_freq=1.8)
        b.move(x + cx_, y + cy_, z + cz - R * 0.92)
        c.add(b, dice=None, smooth=80.0, tint=(shade, shade * 1.02, shade * 0.95))


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
    # ridge: team-felt ridge-tile band (the only team area on a roof, bible 3.1 rule 7); hips: chunky
    # oak hip boards (never team: team on every hip read as gift-wrap ribbon)
    w = hip_w
    prof = np.array([(w * 0.3, w * 0.62), (0.0, w * 0.55), (-w * 0.5, 0.0), (0.0, -w * 0.55), (w * 0.3, -w * 0.62)])
    lines = []
    if rl > 1e-3:
        lines.append((np.array(r0, float), np.array(r1, float), "team_band" if ridge_team else "oak"))
        ends = [(np.array(r0, float), [V[0], V[3]] if along_x else [V[0], V[1]]),
                (np.array(r1, float), [V[1], V[2]] if along_x else [V[2], V[3]])]
    else:
        ends = [(np.array((xc, yc, z_top), float), [V[0], V[1], V[2], V[3]])]
    if hips:
        for top, corners in ends:
            for cr in corners:
                lines.append((top, np.array(cr, float), "oak"))
    for a, b, lk in lines:
        n = 8
        pts = np.array([a + (b - a) * i / n for i in range(n + 1)])
        pts = deform(pts) + np.array([0, 0, 0.012 if lk != "oak" else 0.02])
        d = b - a
        upv = nrm(np.cross(np.cross(d, [0, 0, 1.0]), d))
        side = nrm(np.cross(d, upv))
        pr = prof if lk != "oak" else prof * np.array([0.75, 1.0])
        rp = L.sweep(pr, pts, c.sw(lk), up=tuple(side))
        if lk != "oak":
            normalize_v(rp)
        out.append(c.add(rp, layer=1.0, tint=(1, 1, 1) if lk != "oak" else (0.8, 0.78, 0.76)))
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
    burgundy boards with ivory top rails (bible K_WAGON). team_band: a team-painted side board on both
    sides (a separate plank 6 mm proud of the body, no coplanar faces). cover: ivory canvas with one
    team stripe round the middle hoop."""
    x, y, z = center
    zb = wheel_r * 0.95
    R = L.rot_matrix(0, 0, rz)
    o = np.array([x, y, z])

    def put(p):
        return p.rot(0, 0, rz).move(x, y, z)

    if paint == "burgundy":
        # burgundy-painted boards: the plank swatch under a burgundy vertex tint (textured, not a flat cell)
        body = L.box(length, width, h, c.sw("planks"), chamfer=0.02, center=(0, 0, zb + h / 2))
        c.add(put(body), dice=None, uvrot=True, tint=(0.82, 0.3, 0.33))
        for sy in (-1, 1):
            rail = L.box(length * 1.03, 0.07, 0.08, c.sw("oak"), chamfer=0.01, center=(0, sy * (width / 2 + 0.03), zb + h - 0.01))
            c.add(put(rail), dice=None, tint=(1.5, 1.4, 1.25))
        for sx in (-1, 1):
            rail = L.box(0.07, width * 1.05, 0.08, c.sw("oak"), chamfer=0.01, center=(sx * (length / 2 + 0.03), 0, zb + h + 0.005))
            c.add(put(rail), dice=None, tint=(1.5, 1.4, 1.25))
    else:
        c.add(put(L.box(length, width, h, c.sw("planks"), chamfer=0.02, center=(0, 0, zb + h / 2))), dice=None)
    c.add(put(L.box(length * 1.04, width * 0.96, 0.07, c.sw("oak"), center=(0, 0, zb))), dice=None)
    if team_band:
        bh = h * 0.42
        for sy in (-1, 1):
            band = L.box(length * 0.86, 0.02, bh, c.sw("team_band"), chamfer=0.006,
                         center=(0, sy * (width / 2 + 0.016), zb + h * 0.48))
            v = band.v[band.t]
            band.uv = np.stack([v[..., 0] / 0.8, 1 - (v[..., 2] - (zb + h * 0.48 - bh / 2)) / bh], -1)
            c.add(put(band), dice=None)
    xs = (-length * 0.3, length * 0.3) if four else (0.0,)
    for wx in xs:
        for sy in (-1, 1):
            cc = np.array([wx, sy * (width / 2 + 0.1), wheel_r])
            wc = R @ cc + o
            for p in wheel(c, tuple(wc), wheel_r, axis="y", spokes=spokes, segs=14):
                p.rot(0, 0, rz, pivot=wc)
    if shafts:
        for sy in (-1, 1):
            a = np.array([length / 2, sy * width * 0.3, zb + 0.05])
            b = np.array([length / 2 + 0.9, sy * width * 0.25, 0.1])
            c.add(put(L.member(a, b, 0.07, 0.07, c.sw("oak"), rng=c.rng)))
    if cover:
        nseg = 8
        prof = [(math.cos(math.pi * i / nseg) * width * 0.53, math.sin(math.pi * i / nseg) * width * 0.62)
                for i in range(nseg + 1)]
        xs_ = [-0.44, -0.12, 0.12, 0.44]
        for k in range(3):
            xa, xb = xs_[k] * length, xs_[k + 1] * length
            verts = []
            for xx in (xa, xb):
                for (py, pz) in prof:
                    verts.append((xx, py, zb + h + pz))
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
            put(cv)
            if not team_mid:
                c.pal_uv(cv, "#EDE2C8")
            c.add(cv, dice=None, form=0.0)
            back = cv.copy()
            back.t = back.t[:, ::-1]
            back.uv = back.uv[:, ::-1]
            c.add(back, dice=None, form=0.0)
        for xx in xs_:
            hp = np.array([(xx * length, py * 1.03, zb + h + pz * 1.03) for (py, pz) in prof])
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
    """Croft (supply, 8x8 cells = 4 m, 3-3.5 m): a half-timber cottage under a steep half-hipped roof whose
    gable faces the camera (door rising into the gable, team-shuttered windows), a chunky chimney, a big
    stork nest with a white stork on the back of the ridge, a lean-to woodshed with ring-ended logs, a
    wattle-fenced cabbage bed and a hay stook, all on a packed-earth apron with a timber kerb and a cobbled
    door path."""
    apron(c, gaps=[(0.0, 0.48)])
    t = 0.11
    x0, x1, y0, y1 = -1.3, 1.3, -1.45, 0.72
    zp, zw = 0.22, 1.62
    house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front", "back"), ops={
        ("right", 0): [(0.5, 0.5, 0.42, 1.05, "window")],
        ("left", 0): [(0.62, 0.44, 0.45, 1.0, "window")]}, bay=0.8)
    rf = half_hip_roof(c, x0, x1, y0, y1, zw, pitch=44.0, ov=0.3, ovg=0.3, clip=0.58, th=0.13, t=0.13, trim=0.1,
                       sag=0.05)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, rf["wall_eave"], rf["wall_apex"], t, door=(fw.L / 2, 0.9, 1.95),
               windows=[(0.45, 0.7, 1.32, 0.42), (fw.L - 0.45, 0.7, 1.32, 0.42)], clip_z=rf["wall_clip_front"])
    bw = Wall((x0, y0), (1, 0), (0, -1), x1 - x0)
    gable_wall(c, bw, zp, rf["wall_eave"], rf["wall_apex"], t, windows=[(bw.L / 2, 0.72, 1.3, 0.42)],
               clip_z=rf["wall_clip_back"])
    zr = rf["z_ridge"]
    chimney(c, 0.62, -0.78, zw, zr + 0.12, 0.5)
    # the read: a big stork nest on the back of the ridge, the stork looking out over the door side
    stork_nest(c, (0.0, rf["rb"][1] + 0.38, zr - 0.08), r=0.55, facing=-35.0)
    pennant(c, (0.0, rf["rf"][1] - 0.05, zr - 0.04), 0.55, 1.6, 0.55, dirn=(-1, 0.3), phase=0.4, pole_r=0.04)
    pennant(c, (0.0, rf["rb"][1] + 0.02, zr - 0.04), 0.75, 1.3, 0.46, dirn=(1, -0.25), phase=1.7, pole_r=0.035)
    # lean-to woodshed on the left: ring ends of the logs to the front
    lx0, lx1, ly0, ly1 = -1.9, -1.36, -1.15, 0.45
    for yy in (ly0, ly1):
        c.add(L.member((lx0 + 0.05, yy, 0), (lx0 + 0.05, yy, 1.02), 0.1, 0.1, c.sw("oak"), rng=c.rng))
    roof_solid(c, [(lx0 - 0.08, ly0 - 0.15, 0.98), (lx1 + 0.06, ly0 - 0.15, 1.42), (lx1 + 0.06, ly1 + 0.15, 1.42),
                   (lx0 - 0.08, ly1 + 0.15, 0.98)], [[0, 1, 2, 3]], 0.08, "roof", None, dice=0.5)
    for row in range(3):
        for k in range(2 if row < 2 else 1):
            rr = 0.12 + 0.015 * c.r()
            log1(c, (lx0 + 0.18 + k * 0.25 + 0.12 * (row % 2), (ly0 + ly1) / 2, row * 0.21), 1.5, rr, axis="y", sides=7)
    # wattle-fenced cabbage bed at the front right, water butt by the door, hay stook front left
    fence_wattle(c, (1.85, 0.25), (1.85, 1.85), 0.5)
    fence_wattle(c, (1.85, 1.85), (0.75, 1.85), 0.5)
    pbox(c, 0.85, 1.15, 0.2, "planks", center=(1.32, 1.12, APRON_Z), taper=0.0)
    bed = L.blob(c.sw("leaves"), radius=0.5, subdiv=2, scale=(0.78, 1.05, 0.42), seed=41, noise_amp=0.3, noise_freq=3.0)
    bed.move(1.32, 1.12, 0.2)
    c.add(bed, dice=None, smooth=70.0, tint=(0.95, 1.05, 0.85))
    barrel(c, (0.72, 1.0, APRON_Z), r=0.25, h=0.62)
    stook(c, (-1.45, 1.35, 0.0), 0.48, 1.15)
    cobbles(c, -0.46, 0.46, y1 + 0.04, 1.9)
    return {"height_target": (3.0, 3.5), "budget_note": "roof ridge 3.0 m; the stork in its nest stands to ~3.8 m"}


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
    """Oath Hall (hero altar, 12x12 cells = 6 m, 4.5-5.5 m): a squat rubble-stone hall under a heavy hip roof
    (oak hip boards, team ridge tiles) with battered corner buttresses; in front of the door stands its
    signature, a free-standing gate made of the upper half of a giant iron wheel rising well above the
    eaves and leaning back towards the camera; the oath wheel is set in the cobbled forecourt before it,
    braziers and team banners flank it."""
    apron(c, gaps=[(0.0, 2.0)])
    cobbles(c, -2.0, 2.0, 0.55, 2.82)
    t = 0.12
    x0, x1, y0, y1 = -2.32, 2.32, -2.62, 0.42
    zp, zw = 0.3, 2.4
    house(c, x0, x1, y0, y1, zp, [zw], t, stone=(0,), ops={
        ("front", 0): [(0.5, 1.3, 0.0, 2.05, "door"), (0.17, 0.44, 0.85, 1.6, "window"), (0.83, 0.44, 0.85, 1.6, "window")],
        ("left", 0): [(0.5, 0.42, 0.85, 1.6, "window")],
        ("right", 0): [(0.5, 0.42, 0.85, 1.6, "window")]})
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bx, by = (x1 if sx > 0 else x0), (y1 if sy > 0 else y0)
        pbox(c, 0.56, 0.56, 2.1, "rubble", center=(bx + sx * 0.04, by + sy * 0.04, 0), taper=0.3, chamfer=0.06, grid=0.6)
    ov = 0.36
    hip_roof(c, x0 - ov, x1 + ov, y0 - ov, y1 + ov, zw + 0.02, 4.6, ridge_frac=0.85, th=0.17, kick=0.1, hip_w=0.12,
             hips=True, ridge_team=True)
    iron_wheel_arch(c, 0.0, y1 + 0.95, 1.95, 1.55, lean=15.0)
    floor_wheel(c, 0.0, y1 + 1.85, 0.46)
    braziers(c, [(-1.95, y1 + 1.2), (1.95, y1 + 1.2)], r=0.24, h=0.8)
    for sx in (-1, 1):
        x = sx * 2.6
        c.add(L.member((x, y1 + 0.7, 0), (x, y1 + 0.7, 3.75), 0.14, 0.14, c.sw("oak"), rng=c.rng, chamfer=0.02))
        pbox(c, 0.42, 0.42, 0.25, "rubble", center=(x, y1 + 0.7, 0))
        banner(c, (x, y1 + 0.79, 3.6), 0.7, 1.55, normal=(0, 1))
        ball = L.lathe([(0, 0), (0.09, 0.05), (0.1, 0.14), (0.04, 0.22), (0, 0.27)], 7, c.sw("iron"))
        ball.move(x, y1 + 0.7, 3.75)
        c.add(ball, dice=None)
    rl = 0.85 * abs((x1 - x0) / 2 - (y1 - y0) / 2)
    ycen = (y0 + y1) / 2
    for sx in (-1, 1):
        pennant(c, (sx * rl, ycen, 4.55), 0.5, 1.25, 0.42, dirn=(sx, 0.45), phase=sx)
    return {"height_target": (4.5, 5.5)}


def k_drill_yard(c):
    """Drill Yard (barracks, 12x12 cells = 6 m, 5-6 m): a big timber longhouse with its gable (double
    door, team-shuttered windows) to the camera, a dormer and a chimney on the slopes; an L-shaped
    wattle-fenced drill yard round it on packed earth: a pavise wall of tall shields, a polearm rack, a
    straw drill dummy in a kettle hat and a tall team pennant mast at the gate."""
    apron(c, gaps=[(1.4, 0.55)])
    t = 0.13
    x0, x1, y0, y1 = -2.82, 0.78, -2.62, 0.95
    zp, zw = 0.32, 2.35
    house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front",), ops={
        ("right", 0): [(0.3, 0.55, 0.75, 1.5, "window"), (0.72, 0.55, 0.75, 1.5, "window")],
        ("left", 0): [(0.5, 0.55, 0.75, 1.5, "window")]}, bay=1.0)
    ov = 0.3
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ridge_len = y1 - y0 + 0.65
    z_eave, z_ridge = roof_fit(zw, half, ov, 50, 0.16, ridge_len)
    gable_roof(c, y0 - 0.3, y1 + 0.35, xm, half + ov, z_eave, z_ridge, th=0.16, t=0.16, nu=10, nv=6, axis="y",
               cx=xm, trim=0.13, ridge_w=0.18)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, zw, z_ridge - 0.22, t, door=(fw.L / 2, 1.35, 2.2),
               windows=[(fw.L * 0.15, 0.95, 1.6, 0.48), (fw.L * 0.85, 0.95, 1.6, 0.48)])
    window(c, fw, fw.L / 2, z_ridge - 1.75, z_ridge - 1.15, 0.5, shutters=True)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zw, z_ridge - 0.22, t)
    chimney(c, xm - 0.95, y0 + 0.95, zw, z_ridge + 0.2, 0.6)
    zr = roof_z(1.0, half + ov, z_eave, z_ridge)
    dormer(c, (xm + 1.2, -1.0, zr - 0.4), (1, 0), w=0.95, h=0.8, depth=1.1, rise=0.5)
    # L-shaped drill yard: front strip + right strip
    fh = 0.8
    fence_wattle(c, (2.8, -2.75), (2.8, 2.8), fh)
    fence_wattle(c, (1.15, -2.75), (2.8, -2.75), fh)
    fence_wattle(c, (2.8, 2.8), (1.95, 2.8), fh)
    fence_wattle(c, (0.85, 2.8), (-2.8, 2.8), fh)
    fence_wattle(c, (-2.8, 2.8), (-2.8, 1.35), fh)
    for gx in (0.85, 1.95):
        c.add(L.member((gx, 2.8, 0), (gx, 2.8, 1.35), 0.17, 0.17, c.sw("oak"), rng=c.rng))
        cap = L.lathe([(0, 0), (0.11, 0.03), (0.12, 0.1), (0.05, 0.16), (0, 0.18)], 6, c.sw("iron"))
        cap.move(gx, 2.8, 1.35)
        c.add(cap, dice=None)
    for i, (px, py) in enumerate(((1.6, -2.1), (2.15, -1.4), (2.5, -0.7), (2.15, -0.02))):
        pavise(c, (px, py, APRON_Z), -12.0 * (i - 1.5), h=1.9, w=0.66, lean=9, n=6,
               face_key="team" if i in (1, 3) else "planks")
    weapon_rack(c, (2.45, 0.95, APRON_Z), rz=90.0, width=1.3, h=1.15, n=4)
    dx, dy = 1.7, 1.85
    c.add(L.member((dx, dy, 0), (dx, dy, 1.6), 0.11, 0.11, c.sw("oak"), rng=c.rng))
    c.add(L.member((dx - 0.45, dy, 1.25), (dx + 0.45, dy, 1.25), 0.09, 0.09, c.sw("oak"), rng=c.rng))
    body = L.blob(c.sw("straw"), radius=0.32, subdiv=1, scale=(1, 0.75, 1.35), seed=7, noise_amp=0.1)
    body.move(dx, dy, 0.75)
    c.add(body, dice=None)
    hat = L.lathe([(0.0, 0.0), (0.42, 0.0), (0.42, 0.03), (0.19, 0.07), (0.18, 0.21), (0.0, 0.24)], 9, c.sw("iron"))
    hat.move(dx, dy, 1.56)
    c.add(hat, dice=None)
    pennant(c, (1.95, 2.8, 1.35), 4.2, 1.5, 0.55, dirn=(-1, -0.25), phase=0.8, pole_r=0.06)
    # barrels and crates clustered against the gable, beside the door
    barrel(c, (-2.35, 1.35, APRON_Z), r=0.27, h=0.62)
    barrel(c, (-1.85, 1.3, APRON_Z), r=0.25, h=0.58)
    crate(c, (-2.25, 1.85, APRON_Z), s=0.48, rz=12)
    crate(c, (-2.25, 1.85, APRON_Z + 0.48), s=0.36, rz=35)
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
    """Timber Yard (lumber drop-off, 12x12 cells = 6 m, 5-6 m), built at the tree line: an open mono-pitch
    lean-to (high open front, roof falling to a plank back wall) over stacked planks and squared beams, a
    sawpit in front with a log on tall trestles and a two-man pit saw, a tall gin-pole hoist with a jib and
    a team pennant over the pit, and a tall end pile of big logs held by posts with their ring ends to the
    camera."""
    apron(c, gaps=[(-1.15, 1.5)], tint=(1.0, 0.96, 0.9))
    sx0, sx1 = -2.78, 0.5
    yf, yb = -0.9, -2.72
    zf, zb = 3.2, 2.0
    xs = (sx0, (sx0 + sx1) / 2, sx1)
    oak = c.sw("oak")
    for x in xs:
        for y, zz in ((yf, zf), (yb, zb)):
            c.add(L.member((x, y, 0), (x, y, zz), 0.17, 0.17, oak, rng=c.rng, chamfer=0.02))
            pbox(c, 0.36, 0.36, 0.2, "rubble", center=(x, y, 0))
        c.add(L.member((x, yf + 0.08, zf - 0.08), (x, yb - 0.08, zb - 0.08), 0.15, 0.18, oak, rng=c.rng))
    c.add(L.member((sx0 - 0.15, yf, zf - 0.08), (sx1 + 0.15, yf, zf - 0.08), 0.18, 0.22, oak, rng=c.rng))
    c.add(L.member((sx0 - 0.15, yb, zb - 0.08), (sx1 + 0.15, yb, zb - 0.08), 0.15, 0.17, oak, rng=c.rng))
    for x in (xs[0], xs[2]):
        c.add(L.member((x, yf, zf - 0.95), (x + (0.6 if x < 0 else -0.6), yf, zf - 0.14), 0.12, 0.12, oak, rng=c.rng))
    bw = L.plate((sx1 + 0.06, yb - 0.09, 0.05), (sx0 - 0.06, yb - 0.09, 0.05), (sx0 - 0.06, yb - 0.09, zb - 0.12),
                 (sx1 + 0.06, yb - 0.09, zb - 0.12), 0.06, c.sw("planks"))
    bw.box_uv()
    c.add(bw, uvrot=True)
    sl = (zf - zb) / (yf - yb)
    mono_roof(c, sx0 - 0.3, sx1 + 0.3, yf + 0.38, yb - 0.2, zf + 0.12 + sl * 0.38, zb + 0.12 - sl * 0.2, th=0.15)
    banner(c, (xs[1] - 0.85, yf + 0.13, zf - 0.22), 1.05, 1.5, normal=(0, 1), bar=False)
    banner(c, (xs[1] + 0.85, yf + 0.13, zf - 0.22), 1.05, 1.5, normal=(0, 1), bar=False)
    for k in range(5):
        for j in range(2):
            pbox(c, 2.9, 0.36, 0.08, "oak", center=(-1.14, -2.35 + j * 0.6, 0.14 + k * 0.09), taper=0.0, jit=0.006)
    for j in range(2):
        for x_ in (-2.45, 0.15):
            pbox(c, 0.14, 0.42, 0.14, "oak", center=(x_, -2.35 + j * 0.6, APRON_Z), taper=0.0)
    for k in range(3):
        pbox(c, 2.6, 0.26, 0.26, "oak", center=(-1.1, -1.3 - (k % 2) * 0.05, APRON_Z + k * 0.26), taper=0.0, jit=0.008)
    # sawpit: dark pit with a plank rim, log on tall trestles, two-man pit saw
    sx, sy = -1.15, 1.1
    rim = L.prism(L.rect_profile(2.8, 1.3, 0.08), 0.0, 0.18, c.sw("planks"), chamfer=0.03)
    rim.move(sx, sy, 0)
    c.add(rim, dice=None)
    pit = L.quad((sx - 1.25, sy - 0.5, 0.185), (sx + 1.25, sy - 0.5, 0.185), (sx + 1.25, sy + 0.5, 0.185),
                 (sx - 1.25, sy + 0.5, 0.185), c.sw("pal"))
    c.P(pit, "#2A2220", ao=False, min_shade=0.0)
    for tx in (sx - 0.95, sx + 0.95):
        trestle(c, (tx, sy, 0.18), rz=90, w=0.95, h=1.0)
    log1(c, (sx, sy, 1.1), 2.9, 0.3, axis="x", sides=9)
    fx = sx + 0.4
    c.add(L.box(0.035, 0.3, 2.3, c.sw("iron"), center=(fx, sy, 1.45)), dice=None, tint=(1.2, 1.2, 1.2))
    for zz in (0.35, 2.55):
        c.add(L.member((fx, sy - 0.36, zz), (fx, sy + 0.36, zz), 0.08, 0.08, oak, rng=c.rng))
    # gin-pole hoist with a jib over the pit (one tall clean shape instead of crossing sheer legs)
    gx, gy = sx + 1.62, sy + 0.12
    c.add(L.member((gx, gy, 0), (gx, gy, 4.7), 0.2, 0.2, oak, rng=c.rng, chamfer=0.03))
    pbox(c, 0.55, 0.55, 0.25, "rubble", center=(gx, gy, 0))
    for a in (30.0, 150.0, 270.0):
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0])
        c.add(L.member(np.array([gx, gy, 0]) + d * 0.75, (gx, gy, 1.6), 0.11, 0.11, oak, rng=c.rng))
    jib_end = np.array([sx - 0.25, sy, 4.05])
    c.add(L.member((gx, gy, 4.45), jib_end, 0.15, 0.15, oak, rng=c.rng))
    c.add(L.member((gx, gy, 2.6), jib_end + np.array([0.4, 0, -0.1]), 0.11, 0.11, oak, rng=c.rng))
    pul = L.torus(0.16, 0.05, c.sw("iron"), segs=10, sides=4).rot(90, 0, 0)
    pul.move(*(jib_end + np.array([0.1, 0, -0.2])))
    c.add(pul, dice=None)
    c.add(L.member(jib_end + np.array([0.1, 0, -0.3]), (sx - 0.1, sy, 1.42), 0.045, 0.045, c.sw("iron")), dice=None)
    pennant(c, (gx, gy, 4.7), 0.6, 1.7, 0.58, dirn=(-1, 0.3), phase=0.2, pole_r=0.05)
    # tall end pile of big logs (ring ends to the camera), held by posts
    lx0, lx1 = 0.98, 2.8
    ly = -0.55
    Lg = 3.2
    rows = [(3, 0.0), (3, 0.5), (2, 0.0), (2, 0.5), (1, 0.0)]
    zz = 0.0
    for ri, (n, off) in enumerate(rows):
        for k in range(n):
            rr = 0.3 * (0.9 + 0.16 * c.r())
            xx = lx0 + 0.3 + (k + off + (3 - n) * 0.5) * 0.55
            log1(c, (xx, ly + c.r(-0.08, 0.08), zz), Lg * (0.94 + 0.06 * c.r()), rr, axis="y", sides=9)
        zz += 0.5
    for px in (lx0 - 0.04, lx1 + 0.0):
        for py in (ly - 1.3, ly + 1.3):
            c.add(L.member((px, py, 0), (px, py, 2.9), 0.16, 0.16, oak, rng=c.rng, chamfer=0.02))
    c.add(L.member((lx0 - 0.04, ly + 1.3, 2.75), (lx1, ly + 1.3, 2.75), 0.13, 0.13, oak, rng=c.rng))
    # chopping block with an axe and a sawdust heap by the pit
    blk = L.lathe([(0.34, 0), (0.32, 0.55), (0.0, 0.58)], 8, c.sw("bark"))
    blk.move(0.62, 2.25, APRON_Z)
    c.add(blk, dice=None)
    c.add(L.member((0.62, 2.25, 0.52), (0.92, 2.4, 1.08), 0.055, 0.055, oak, rng=c.rng))
    c.add(L.box(0.07, 0.3, 0.24, c.sw("iron"), center=(0.92, 2.43, 1.05)), dice=None)
    dust = L.blob(c.sw("straw"), radius=0.65, subdiv=1, scale=(1.3, 0.9, 0.32), seed=12, noise_amp=0.15, flat_bottom=0.0)
    dust.move(sx + 0.45, sy + 1.3, 0)
    c.add(dust, dice=None, tint=(1.05, 0.95, 0.75))
    return {"height_target": (5.0, 6.0)}


def k_foundry(c):
    """Foundry (smithy, 12x12 cells = 6 m, 5-6 m): a stone-and-brick forge house with a crow-stepped brick
    gable to the camera and a glowing forge door, a massive square brick chimney stack on the camera-side
    corner under a simple dark-bronze cowl (smoke anchor for VFX), and an open lean-to smithy with anvil,
    forge bed, quench tub and grindstone; an ingot stack, a coal heap and barrels on the cobbled yard."""
    apron(c, gaps=[(-1.3, 0.9)])
    cobbles(c, -2.6, 0.4, 0.82, 2.0)
    t = 0.12
    x0, x1, y0, y1 = -2.8, 0.2, -2.7, 0.75
    zp, zw = 0.3, 2.3
    house(c, x0, x1, y0, y1, zp, [zw], t, stone=(0,), skip=("front",), ops={
        ("left", 0): [(0.5, 0.42, 0.95, 1.6, "window")]})
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ov = 0.25
    z_eave, z_ridge = roof_fit(zw, half, ov, 52, 0.15, y1 - y0 + 0.5)
    gable_roof(c, y0 - 0.25, y1 + 0.05, xm, half + ov, z_eave, z_ridge, th=0.15, t=0.15, nu=8, nv=5, axis="y", cx=xm,
               trim=0.12, ridge_w=0.17)
    gw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    wall_prism(c, gw, [(0, zp), (gw.L, zp), (gw.L, zw), (0, zw)], -0.08, 0.04, "rubble", chamfer=0.03)
    ztop = stepped_gable(c, gw, zw, z_ridge, steps=4, th=0.24, key="brick", rise=0.2, d0=-0.1)
    gable_infill(c, Wall((x0, y0), (1, 0), (0, -1), x1 - x0), zw, z_ridge - 0.17, t)
    window(c, gw, gw.L / 2, zw + 0.35, zw + 0.85, 0.42, shutters=True)
    s0 = gw.L / 2
    dk = L.quad(gw.p(s0 - 0.65, zp, 0.05), gw.p(s0 + 0.65, zp, 0.05), gw.p(s0 + 0.65, zp + 1.95, 0.05),
                gw.p(s0 - 0.65, zp + 1.95, 0.05), c.sw("pal"))
    c.P(_face_out(dk, gw), "#2A2220", ao=False, min_shade=0.0)
    gl = L.quad(gw.p(s0 - 0.48, zp, 0.056), gw.p(s0 + 0.48, zp, 0.056), gw.p(s0 + 0.48, zp + 1.0, 0.056),
                gw.p(s0 - 0.48, zp + 1.0, 0.056), c.sw("ember"))
    gl.uv = np.array([[(0.15, 0.95), (0.85, 0.95), (0.85, 0.35)], [(0.15, 0.95), (0.85, 0.35), (0.15, 0.35)]])
    c.add(_face_out(gl, gw), ao=False, min_shade=1.0, form=0.0, occ=False)
    c.add(L.member(gw.p(s0 - 0.9, zp + 2.05, 0.1), gw.p(s0 + 0.9, zp + 2.05, 0.1), 0.2, 0.18, c.sw("oak"), rng=c.rng))
    for sgn in (-1, 1):
        dp = L.box(0.66, 1.9, 0.06, c.sw("planks"))
        dp.move(sgn * 0.33, 0.95, 0).rot(0, sgn * -65, 0).move(0, 0, 0.07)
        gw.place(dp, s0 + sgn * 0.66, zp, 0.0)
        c.add(dp, dice=None, uvrot=True)
    # the chimney stack on the camera-side corner under a dark-bronze cowl
    chx, chy = x1 + 0.28, y1 - 0.3
    hch = 5.0
    ch = L.gbox(1.0, 1.0, hch, c.sw("brick"), center=(chx, chy, 0.0), chamfer=0.04, grid=0.9)
    zf = ch.v[:, 2] / hch
    ch.v[:, 0] = chx + (ch.v[:, 0] - chx) * (1 - 0.16 * zf)
    ch.v[:, 1] = chy + (ch.v[:, 1] - chy) * (1 - 0.16 * zf)
    ch.box_uv()
    c.add(ch, jit=0.012)
    for zz, w_ in ((0.0, 1.16), (4.15, 0.98)):
        pbox(c, w_, w_, 0.22, "rubble", center=(chx, chy, zz), taper=0.04, chamfer=0.04)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.add(L.member((chx + sx * 0.3, chy + sy * 0.3, hch - 0.05), (chx + sx * 0.3, chy + sy * 0.3, hch + 0.3), 0.07,
                           0.07, c.sw("iron")))
    cowl = L.lathe([(0.62, 0.0), (0.66, 0.05), (0.56, 0.14), (0.3, 0.3), (0.08, 0.4), (0.0, 0.42)], 4, c.sw("bronze"),
                   a0=math.pi / 4)
    cowl.move(chx, chy, hch + 0.28)
    c.add(cowl, dice=None, smooth=20.0)
    knob = L.lathe([(0, 0), (0.07, 0.04), (0.06, 0.12), (0, 0.18)], 7, c.sw("bronze"))
    knob.move(chx, chy, hch + 0.68)
    c.add(knob, dice=None, tint=(1.2, 1.1, 0.95))
    c.anchors["smoke"] = (chx, chy, hch + 0.15)
    banner(c, (chx, chy + 0.5 * (1 - 0.16 * 3.95 / hch) + 0.05, 3.95), 0.66, 1.75, normal=(0, 1))
    # open lean-to smithy on the right
    lx0, lx1, ly0, ly1 = 0.85, 2.82, -2.25, 0.5
    for x, y in ((lx1, ly1), (lx1, ly0), ((lx0 + lx1) / 2 + 0.3, ly1)):
        c.add(L.member((x, y, 0), (x, y, 1.95), 0.15, 0.15, c.sw("oak"), rng=c.rng, chamfer=0.02))
        pbox(c, 0.3, 0.3, 0.18, "rubble", center=(x, y, 0))
    c.add(L.member((lx1, ly0 - 0.15, 1.9), (lx1, ly1 + 0.15, 1.9), 0.15, 0.16, c.sw("oak"), rng=c.rng))
    roof_solid(c, [(lx0 - 0.1, ly0 - 0.3, 2.72), (lx1 + 0.12, ly0 - 0.3, 1.86), (lx1 + 0.12, ly1 + 0.3, 1.86),
                   (lx0 - 0.1, ly1 + 0.3, 2.72)], [[0, 1, 2, 3]], 0.12, "roof", None, dice=None)
    pbox(c, 1.1, 0.8, 0.75, "brick", center=(1.35, -1.55, 0), taper=0.06)
    coals = L.quad((0.9, -1.85, 0.76), (1.8, -1.85, 0.76), (1.8, -1.25, 0.76), (0.9, -1.25, 0.76), c.sw("ember"))
    coals.uv = np.array([[(0.2, 0.8), (0.8, 0.8), (0.8, 0.2)], [(0.2, 0.8), (0.8, 0.2), (0.2, 0.2)]])
    c.add(coals, ao=False, min_shade=1.0, form=0.0, occ=False)
    anvil(c, (2.0, -0.35, APRON_Z), rz=15, s=1.5)
    barrel(c, (2.4, 0.95, APRON_Z), r=0.3, h=0.58)
    wheel(c, (1.45, 0.85, 0.5), 0.42, axis="x", spokes=0, key="rubble", width=0.18, rim_w=0.42, segs=12)
    for sx_ in (-0.12, 0.12):
        c.add(L.member((1.45 + sx_, 0.85, 0), (1.45 + sx_, 0.85, 0.55), 0.07, 0.07, c.sw("oak"), rng=c.rng))
    # one ingot stack, a coal heap, a barrel pair (clustered, no loose bits)
    for k in range(3):
        for j in range(3 - k):
            ing = pbox(c, 0.5, 0.2, 0.13, "pal", center=(-0.55 + j * 0.24 + k * 0.12, 1.6, APRON_Z + k * 0.13),
                       taper=0.2, chamfer=0.02)
            c.pal_uv(ing, "#B07F3E")
    coal = L.blob(c.sw("pal"), radius=0.55, subdiv=1, scale=(1.2, 0.9, 0.5), seed=11, noise_amp=0.22, flat_bottom=0.0)
    coal.move(-2.05, 1.6, 0)
    c.P(coal, "#26221F", dice=None)
    barrel(c, (-1.3, 1.65, APRON_Z), r=0.26, h=0.56)
    pennant(c, (xm, y1 - 0.02, ztop), 0.6, 1.5, 0.5, dirn=(-1, 0.3), phase=1.0)
    banner(c, ((lx0 + lx1) / 2 + 0.3, ly1 + 0.42, 1.88), 0.8, 0.7, normal=(0, 1), bar=False)
    return {"height_target": (5.0, 6.0), "budget_note": "chimney stack + cowl 5.7 m (art bible 4.2), the rest <= 4.3 m"}


def k_collegium(c):
    """Collegium (caster hall, 12x12 cells = 6 m, 5-6 m): a tall narrow two-storey jettied guild house with
    its gable to the camera and a little bell-cote on the gable, beside a walled herb garden: a low
    rubble-stone wall with an irregular mossy coping and gate piers, two garden lindens (2.6-2.9 m, the
    doodad kit's rounded-cone crown), box-hedge rows and raised herb beds."""
    apron(c, gaps=[(-1.6, 0.55), (1.5, 0.5)])
    t = 0.11
    x0, x1, y0, y1 = -2.82, -0.35, -2.55, 0.95
    zp = 0.3
    st = [2.05, 3.35]
    jet = 0.18
    house(c, x0, x1, y0, y1, zp, st, t, jetty=jet, ops={
        ("front", 0): [(0.5, 1.0, 0.0, 1.85, "door")],
        ("right", 0): [(0.35, 0.42, 0.8, 1.45, "window"), (0.75, 0.42, 0.8, 1.45, "window")],
        ("left", 0): [(0.5, 0.42, 0.8, 1.45, "window")],
        ("front", 1): [(0.25, 0.42, 0.25, 0.95, "window"), (0.75, 0.42, 0.25, 0.95, "window")],
        ("right", 1): [(0.3, 0.4, 0.25, 0.92, "window"), (0.7, 0.4, 0.25, 0.92, "window")],
        ("left", 1): [(0.5, 0.4, 0.25, 0.92, "window")]}, bay=0.85)
    xm = (x0 + x1) / 2
    half = (x1 - x0) / 2
    ov = 0.24
    yf, yb = y1 + jet, y0 - jet
    z_eave, z_ridge = roof_fit(st[-1], half, ov, 50, 0.14, yf - yb + 0.4)
    gable_roof(c, yb - 0.12, yf + 0.22, xm, half + ov, z_eave, z_ridge, th=0.14, t=0.14, nu=8, nv=5, axis="y", cx=xm,
               trim=0.11, ridge_w=0.16)
    gable_infill(c, Wall((x1, yf), (-1, 0), (0, 1), x1 - x0), st[-1], z_ridge - 0.17, t, window_w=0.36)
    gable_infill(c, Wall((x0, yb), (1, 0), (0, -1), x1 - x0), st[-1], z_ridge - 0.17, t, window_w=0.0)
    bell_cote(c, (xm, yf - 0.02, z_ridge - 0.12), size=0.62, rz=0)
    banner(c, (xm, yf + 0.06, st[0] + 0.22), 1.15, 1.25, normal=(0, 1))
    pennant(c, (xm, yb - 0.02, z_ridge - 0.08), 0.45, 1.5, 0.5, dirn=(1, -0.3), phase=0.9)
    # walled herb garden on the right: rubble wall, irregular mossy coping (no white frame)
    gx0, gx1, gy0, gy1 = 0.0, 2.7, -2.68, 2.68
    wt = 0.3
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
        nst = max(2, int(round(Lw / 0.55)))
        hs = [0.62 + 0.12 * math.sin(i * 2.3 + Lw) + c.r(-0.05, 0.05) for i in range(nst + 1)]
        ol = [(-wt / 2, 0.0), (Lw + wt / 2, 0.0)] + [(Lw + wt / 2 - (Lw + wt) * i / nst, hs[nst - i]) for i in range(nst + 1)]
        wall_prism(c, wl, ol, -wt, 0.0, "rubble", chamfer=0.04, grid=0.6)
        for i in range(nst):
            s_a, s_b = (Lw + wt) * i / nst - wt / 2, (Lw + wt) * (i + 1) / nst - wt / 2
            zc = (hs[i] + hs[i + 1]) / 2
            cp = L.box(s_b - s_a + 0.02, 0.1 + c.r(0, 0.04), wt + 0.1 + c.r(-0.03, 0.03), c.sw("rubble"), chamfer=0.035)
            cp.move((s_a + s_b) / 2, zc + 0.04, -wt / 2)
            cp.rot_axis((e[0], e[1], 0.0), c.r(-4, 4), pivot=cp.v.mean(0))
            wl.place(cp)
            c.add(cp, dice=None, jit=0.015, tint=(0.82, 0.95, 0.68))
    for gx in (gate0, gate1):
        pbox(c, 0.4, 0.4, 1.2, "rubble", center=(gx, gy1 - wt / 2, 0), taper=0.08)
        ball = L.lathe([(0, 0), (0.13, 0.05), (0.12, 0.18), (0, 0.24)], 8, c.sw("rubble"))
        ball.move(gx, gy1 - wt / 2, 1.2)
        c.add(ball, dice=None, tint=(0.85, 0.95, 0.75))
        banner(c, (gx + (0.3 if gx > 1.5 else -0.3), gy1 + 0.02, 1.15), 0.44, 0.85, normal=(0, 1), bar=False)
    pbox(c, 0.42, 0.42, 0.28, "rubble", center=(2.38, 1.95, APRON_Z))
    pennant(c, (2.38, 1.95, APRON_Z + 0.28), 4.0, 1.5, 0.55, dirn=(-1, 0.2), phase=2.1, pole_r=0.055)
    linden_tree(c, (1.0, -1.55, APRON_Z), h=2.95, seed=c.seed + 1)
    linden_tree(c, (1.95, 0.25, APRON_Z), h=2.55, seed=c.seed + 2)
    cobbles(c, -2.15, -1.05, y1 + jet + 0.04, 2.85)
    # box-hedge rows and raised herb beds
    for (hx, hy, hl) in ((1.95, -1.75, 1.0), (0.85, -0.05, 0.9)):
        hb = L.blob(c.sw("leaves"), radius=0.5, subdiv=2, scale=(hl, 0.36, 0.52), seed=int(c.r(0, 999)), noise_amp=0.12,
                    noise_freq=2.5)
        hb.move(hx, hy, APRON_Z)
        c.add(hb, dice=None, smooth=70.0, tint=(0.72, 0.82, 0.68))
    for (bx, by) in ((0.85, 1.5), (1.95, 1.45)):
        pbox(c, 0.85, 1.1, 0.24, "planks", center=(bx, by, APRON_Z), taper=0.0)
        hb = L.blob(c.sw("leaves"), radius=0.5, subdiv=2, scale=(0.78, 1.0, 0.4), seed=int(c.r(0, 999)), noise_amp=0.3,
                    noise_freq=3.2)
        hb.move(bx, by, 0.24)
        c.add(hb, dice=None, smooth=70.0, tint=(1.0, 1.08, 0.88) if bx < 1.5 else (0.9, 1.0, 0.82))
    return {"height_target": (5.0, 6.0)}

def k_wainwright_yard(c):
    """Wainwright Yard (siege workshop, 12x12 cells = 6 m, 5-6 m): a two-bay open shed (twin gables to the
    camera over a valley) with a wagon on the stocks and wheels leaning on the posts, and its sign: a
    giant 2.8 m wagon wheel mounted high on a braced pole, tilted back so it reads as a full circle from
    the RTS camera. A finished wagon under an ivory canvas (one team stripe) waits in the yard beside a
    stack of new wheels and a timber pile."""
    apron(c, gaps=[(1.2, 1.5)])
    sx0, sx1, sy0, sy1 = -0.45, 2.8, -2.75, -0.35
    xm = (sx0 + sx1) / 2
    zt = 2.45
    oak = c.sw("oak")
    ys = (sy0, (sy0 + sy1) / 2, sy1)
    for x in (sx0, xm, sx1):
        for y in ys:
            c.add(L.member((x, y, 0), (x, y, zt), 0.15, 0.15, oak, rng=c.rng, chamfer=0.02))
            pbox(c, 0.32, 0.32, 0.2, "rubble", center=(x, y, 0))
        c.add(L.member((x, sy0 - 0.12, zt - 0.07), (x, sy1 + 0.12, zt - 0.07), 0.16, 0.18, oak, rng=c.rng))
        for ya, yb_ in ((sy0, sy0 + 0.55), (sy1, sy1 - 0.55)):
            c.add(L.member((x, ya, zt - 0.6), (x, yb_, zt - 0.12), 0.1, 0.1, oak, rng=c.rng))
    for y in (sy0, sy1):
        c.add(L.member((sx0 - 0.12, y, zt - 0.07), (sx1 + 0.12, y, zt - 0.07), 0.16, 0.18, oak, rng=c.rng))
    bw = L.plate((sx1 + 0.06, sy0 - 0.1, 0.05), (sx0 - 0.06, sy0 - 0.1, 0.05), (sx0 - 0.06, sy0 - 0.1, zt - 0.1),
                 (sx1 + 0.06, sy0 - 0.1, zt - 0.1), 0.06, c.sw("planks"))
    bw.box_uv()
    c.add(bw, uvrot=True)
    bayw = (sx1 - sx0) / 2
    for bx0 in (sx0, xm):
        bxm = bx0 + bayw / 2
        hw = bayw / 2
        z_eave, z_ridge = roof_fit(zt, hw, 0.2, 54, 0.13, sy1 - sy0 + 0.6)
        gable_roof(c, sy0 - 0.25, sy1 + 0.35, bxm, hw + 0.2, z_eave, z_ridge, th=0.13, t=0.13, nu=8, nv=4, axis="y",
                   cx=bxm, trim=0.1, ridge_w=0.15)
        gable_infill(c, Wall((bx0, sy0), (1, 0), (0, -1), bayw), zt, z_ridge - 0.16, 0.11, key="planks")
        fw = Wall((bx0 + bayw, sy1), (-1, 0), (0, 1), bayw)
        za = z_ridge - 0.18
        c.add(L.member(fw.p(fw.L / 2, zt, 0.04), fw.p(fw.L / 2, za, 0.04), 0.13, 0.13, oak, rng=c.rng))
        for sgn in (-1, 1):
            c.add(L.member(fw.p(fw.L / 2, zt + (za - zt) * 0.25, 0.04), fw.p(fw.L / 2 + sgn * fw.L * 0.3, zt + (za - zt) * 0.6, 0.04),
                           0.1, 0.1, oak, rng=c.rng))
    c.add(L.member((xm, sy0 - 0.25, zt + 0.08), (xm, sy1 + 0.35, zt + 0.08), 0.2, 0.08, oak, rng=c.rng), tint=(0.7, 0.68, 0.66))
    # bay 1: wagon body on the stocks; bay 2: wheels leaning on the posts and a workbench
    wagon(c, (sx0 + bayw / 2, -1.55, 0.18), rz=90.0, length=2.0, width=0.95, h=0.5, wheel_r=0.42, team_band=False,
          four=False, shafts=False)
    for yy in (-2.25, -0.85):
        pbox(c, 0.75, 0.28, 0.3, "oak", center=(sx0 + bayw / 2, yy, 0.0))
    for (wx, wy, tilt) in ((xm + 0.2, -2.1, 14), (sx1 - 0.18, -1.0, -14)):
        for p in wheel(c, (wx, wy, 0.6), 0.6, axis="x", spokes=8, segs=14):
            p.rot(0, tilt, 0, pivot=(wx, wy, 0))
    pbox(c, 1.2, 0.55, 0.12, "oak", center=(xm + bayw / 2 + 0.1, -2.35, 0.78), taper=0.0)
    for sx_ in (-0.5, 0.5):
        c.add(L.member((xm + bayw / 2 + 0.1 + sx_, -2.35, 0), (xm + bayw / 2 + 0.1 + sx_, -2.35, 0.78), 0.09, 0.09, oak,
                       rng=c.rng))
    # the sign: giant wheel on a braced pole, front left
    px_, py_ = -1.75, 0.55
    c.add(L.member((px_, py_, 0), (px_, py_, 3.65), 0.25, 0.25, oak, rng=c.rng, chamfer=0.04))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c.add(L.member((px_ + math.cos(a) * 0.72, py_ + math.sin(a) * 0.72, 0), (px_, py_, 1.3), 0.12, 0.12, oak, rng=c.rng))
    pbox(c, 0.75, 0.75, 0.28, "rubble", center=(px_, py_, 0))
    c.add(L.member((px_, py_ - 0.1, 3.5), (px_, py_ + 0.45, 3.85), 0.14, 0.14, c.sw("iron")), dice=None)
    giant_wheel(c, (px_, py_ + 0.5, 3.95), 1.4, tilt=38.0, spokes=8)
    pennant(c, (px_, py_ - 0.15, 3.65), 1.5, 1.3, 0.45, dirn=(1, 0.3), phase=0.3, pole_r=0.05)
    # finished wagon under a canvas, a stack of new wheels, a timber pile
    wagon(c, (1.3, 1.75, APRON_Z), rz=172.0, length=2.2, width=1.0, h=0.5, wheel_r=0.45, cover=True, team_band=False)
    for k in range(3):
        for p in wheel(c, (-0.55, 2.25, APRON_Z + 0.06 + k * 0.13), 0.55, axis="z", spokes=8, segs=14):
            p.rot(0, 0, 11 * k, pivot=(-0.55, 2.25, 0))
    log_stack(c, (-2.05, -1.65, APRON_Z), 1.6, 3, r=0.16, axis="y")
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
    """Curio Cabinet (faction shop, 12x12 cells = 6 m, 4.5-5.5 m): a narrow half-timber shopfront with its
    gable to the camera, a wide shop window with a counter under a striped team awning, and its sign: a
    giant painted chest of small drawers standing on a bracket shelf at the eaves in front of the gable;
    a market table with crates, a barrel group and a handcart on a cobbled forecourt."""
    apron(c, gaps=[(-1.8, 0.55)])
    t = 0.1
    x0, x1, y0, y1 = -2.7, 0.5, -2.62, 0.7
    zp, zw = 0.25, 2.45
    house(c, x0, x1, y0, y1, zp, [zw], t, skip=("front",), ops={
        ("left", 0): [(0.5, 0.42, 0.95, 1.6, "window")],
        ("right", 0): [(0.3, 0.42, 0.95, 1.6, "window"), (0.7, 0.42, 0.95, 1.6, "window")]}, bay=0.85)
    half = (x1 - x0) / 2
    xm = (x0 + x1) / 2
    ov = 0.25
    z_eave, z_ridge = roof_fit(zw, half, ov, 50, 0.14, y1 - y0 + 0.6)
    gable_roof(c, y0 - 0.25, y1 + 0.35, xm, half + ov, z_eave, z_ridge, th=0.14, t=0.14, nu=8, nv=5, axis="y", cx=xm,
               trim=0.11, ridge_w=0.16)
    fw = Wall((x1, y1), (-1, 0), (0, 1), x1 - x0)
    gable_wall(c, fw, zp, zw, z_ridge - 0.17, t, door=(fw.L * 0.22, 0.95, 2.05), windows=[])
    sw0 = fw.L * 0.66
    window(c, fw, sw0, 0.95, 1.95, 1.35, shutters=False)
    for sgn in (-1, 1):
        c.add(L.member(fw.p(sw0 + sgn * 0.74, 0.85, 0.05), fw.p(sw0 + sgn * 0.74, 2.05, 0.05), 0.11, 0.1, c.sw("oak"),
                       rng=c.rng))
    c.add(L.member(fw.p(sw0 - 0.8, 2.05, 0.05), fw.p(sw0 + 0.8, 2.05, 0.05), 0.12, 0.1, c.sw("oak"), rng=c.rng))
    cx_, cy_ = fw.p(sw0, 0.0, 0.0)[:2]
    pbox(c, 1.55, 0.42, 0.08, "oak", center=(cx_, y1 + 0.2, 0.88), taper=0.0)
    for k in range(2):
        jar = L.lathe([(0, 0), (0.12, 0), (0.16, 0.14), (0.1, 0.28), (0.12, 0.33), (0, 0.33)], 8, c.sw("pal"))
        jar.move(cx_ - 0.35 + k * 0.7, y1 + 0.22, 0.96)
        c.P(jar, ("#C9B994", "#6E4A26")[k], dice=None)
    awning(c, cx_ - 0.9, cx_ + 0.9, y1 + 0.02, 2.2, 0.8, 0.4, posts=False, stripes=True)
    yf = y1
    for sx in (xm - 0.6, xm + 0.6):
        c.add(L.member((sx, yf, zw - 0.45), (sx, yf + 0.55, zw + 0.02), 0.1, 0.1, c.sw("oak"), rng=c.rng))
    pbox(c, 1.85, 0.7, 0.08, "oak", center=(xm, yf + 0.3, zw + 0.02), taper=0.0)
    drawer_chest(c, (xm, yf + 0.32, zw + 0.12), w=1.7, h=1.25, d=0.55, cols=3, rows=3)
    pennant(c, (xm, y0 - 0.15, z_ridge - 0.08), 0.5, 1.5, 0.52, dirn=(1, -0.3), phase=0.6)
    cobbles(c, -2.5, 0.4, y1 + 0.05, 2.15)
    # market table with crates, a barrel group, a handcart (clusters on the forecourt)
    tx, ty = 1.75, 0.35
    trestle(c, (tx - 0.55, ty, APRON_Z), rz=90, w=0.7, h=0.78)
    trestle(c, (tx + 0.55, ty, APRON_Z), rz=90, w=0.7, h=0.78)
    pbox(c, 1.6, 0.78, 0.06, "planks", center=(tx, ty, 0.79), taper=0.0)
    for k in range(3):
        crate(c, (tx - 0.5 + k * 0.5, ty + c.r(-0.08, 0.08), 0.85), s=0.36, rz=c.r(-20, 20))
    for k, (bx, by) in enumerate(((1.3, -1.05), (1.85, -1.2), (1.55, -1.6))):
        barrel(c, (bx, by, APRON_Z), r=0.26, h=0.6)
    crate(c, (2.4, -2.2, APRON_Z), s=0.52, rz=10)
    crate(c, (2.38, -2.2, APRON_Z + 0.52), s=0.4, rz=-15)
    crate(c, (1.8, -2.25, APRON_Z), s=0.46, rz=30)
    wagon(c, (1.75, 1.95, 0.0), rz=200.0, length=1.3, width=0.8, h=0.4, wheel_r=0.38, four=False, team_band=False,
          shafts=True)
    return {"height_target": (4.5, 5.5)}

def k_lookout(c, gun=False):
    """Lookout (scout tower, 4x4 cells = 2 m, 6-8 m): thin splayed timber tower, railed platform, steep
    pyramid roof (oak hip boards) on posts, a big team pennant on the finial. gun=True: the Gun Tower
    upgrade (stone base, plank parapet with hook-guns, a smooth ribbed dark-bronze onion cap)."""
    zb = 1.05 if gun else 0.0
    zpl = 3.75 if not gun else 4.05
    if gun:
        plinth(c, -0.88, 0.88, -0.88, 0.88, zb, batter=0.1, chamfer=0.05)
    apron(c, key="dirt", n_exp=4.0, noise=0.04, edge=None, inset=0.03)
    tower_frame(c, zpl - zb, 0.74 if not gun else 0.62, 0.48, levels=2, t=0.12, footing=not gun)
    if gun:
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
        hip_roof(c, -half - 0.28, half + 0.28, -half - 0.28, half + 0.28, zr - 0.05, zr + 1.45, ridge_frac=0.0, th=0.11,
                 kick=0.18, sag=0.0, ridge_team=False, hip_w=0.1, finials=False)
        pennant(c, (0, 0, zr + 1.55), 0.55, 1.25, 0.45, dirn=(1, 0.35), phase=0.5, finial=True)
        for name, w in rect_walls(-half, half, -half, half).items():
            if name in ("front", "back"):
                banner(c, w.p(w.L / 2, zpl + 0.1 + 0.46, 0.05), w.L * 0.55, 0.45, normal=tuple(w.n), bar=False)
        return {"height_target": (6.0, 8.0)}
    ph = 0.62
    for name, w in rect_walls(-half, half, -half, half).items():
        dz = 0.0 if name in ("front", "back") else -0.014        # no coplanar parapet tops at the corners
        dd = 0.0 if name in ("front", "back") else -0.006
        p = L.box(w.L + 0.1, ph + dz, 0.08, c.sw("planks"), chamfer=0.015)
        p.move(w.L / 2, (ph + dz) / 2, dd)
        w.place(p, 0.0, zpl + 0.1, 0.0)
        c.add(p, dice=0.3)
        for s_ in (w.L * 0.3, w.L * 0.7):
            q = L.quad(w.p(s_ - 0.05, zpl + 0.35, 0.045), w.p(s_ + 0.05, zpl + 0.35, 0.045), w.p(s_ + 0.05, zpl + 0.55, 0.045),
                       w.p(s_ - 0.05, zpl + 0.55, 0.045), c.sw("pal"))
            c.P(_face_out(q, w), "#26221F", ao=False, min_shade=0.0)
        c.add(L.member(w.p(-0.05, zpl + 0.1 + ph + dz + 0.03, dd), w.p(w.L + 0.05, zpl + 0.1 + ph + dz + 0.03, dd), 0.08, 0.12,
                       c.sw("oak"), rng=c.rng))
        # team-painted parapet band (a painted plank strip 6 mm proud of the parapet face)
        tb = L.box(w.L - 0.1, 0.16, 0.012, c.sw("team_band"), chamfer=0.0)
        v_ = tb.v[tb.t]
        tb.uv = np.stack([v_[..., 0] / 0.8, 1 - (v_[..., 1] + 0.08) / 0.16], -1)
        tb.move(w.L / 2, 0.53 + dz, dd + 0.052)
        w.place(tb, 0.0, zpl + 0.1, 0.0)
        c.add(tb, dice=None)
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
             kick=0.12, sag=0.0, ridge_team=False, hip_w=0.1, finials=False)
    for name, w in rect_walls(-half, half, -half, half).items():
        banner(c, w.p(w.L * 0.5, zpl + 0.1 + ph + 0.02, 0.06), 0.74, 1.45, normal=tuple(w.n), bar=False)
    drum = L.lathe([(0.42, 0), (0.42, 0.22), (0.38, 0.26)], 12, c.sw("oak"))
    drum.move(0, 0, zr + 0.28)
    c.add(drum, dice=None, uvrot=True)
    onion_dome(c, (0, 0, zr + 0.52), 0.42, 1.1, finial_h=0.6, sides=16, ribs=7)
    return {"height_target": (6.0, 8.0)}


def k_gun_tower(c):
    return k_lookout(c, gun=True)


def k_walled_burg(c):
    """Walled Burg (T2 hall upgrade): ADD-ON pieces in the Moot Hall GLB's own space (8 m model): a ring of
    parked Bombard-sized wagons (2.6 m, burgundy boards, team-painted side boards) as a low wall, an arc of
    four in front flanking the door and two along the sides; stone corner buttresses for the stone ground
    floor; team banners on tall poles; and a taller smooth dark-bronze onion (7 ribs, team ring, Ember
    Wheel finial) lifted on a drum over the T1 turret, set above the stepped gable so the gable stays
    clear (+14 % height)."""
    # wagons: (x, y, rz, cover) in the hall's build space (front = +y)
    spots = [(-2.08, 3.28, 5.0, False, 0.95), (2.08, 3.28, -5.0, True, 0.95), (-3.55, 1.25, 92.0, True, 0.72),
             (3.55, 1.25, 88.0, False, 0.72)]
    for (x, y, rz, cov, wd) in spots:
        wagon(c, (x, y, 0.0), rz=rz, length=2.5, width=wd, h=0.55, wheel_r=0.46, team_band=True, shafts=False,
              four=True, cover=cov, paint="burgundy")
    tx, ty = 1.86, 1.93
    drum = L.lathe([(0.84, 0.0), (0.82, 1.05), (0.88, 1.12), (0.88, 1.2)], 16, c.sw("plaster"))
    drum.move(tx, ty, 8.95)
    c.add(drum, dice=0.3)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        p0 = (tx + math.cos(a) * 0.86, ty + math.sin(a) * 0.86, 8.95)
        c.add(L.member(p0, (p0[0], p0[1], 10.12), 0.09, 0.09, c.sw("oak"), roll_up=(math.cos(a), math.sin(a), 0)))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        w_ = L.box(0.28, 0.05, 0.5, c.sw("window"))
        w_.uv = _uv_rect(L.box(0.28, 0.05, 0.5, c.sw("window")).rot(90, 0, 0), 0.28, 0.5)
        w_.rot(0, 0, math.degrees(a) - 90).move(tx + math.cos(a) * 0.82, ty + math.sin(a) * 0.82, 9.62)
        c.add(w_, dice=None, ao=False, min_shade=1.0, form=0.0)
    onion_dome(c, (tx, ty, 10.15), 0.78, 1.3, finial_h=0.7, sides=18, ribs=7)
    # stone corner buttresses (stone ground floor read)
    for (bx, by) in ((-3.38, -3.5), (3.25, -3.5), (-3.42, 2.95), (3.3, 2.95)):
        p = L.gbox(0.7, 0.7, 2.2, c.sw("rubble"), chamfer=0.06, center=(bx, by, 0), grid=0.45)
        top = p.v[:, 2] > 1.0
        p.v[top, 0] = bx + (p.v[top, 0] - bx) * 0.72
        p.v[top, 1] = by + (p.v[top, 1] - by) * 0.72
        p.box_uv()
        c.add(p, jit=0.03)
        cap = L.box(0.58, 0.58, 0.12, c.sw("roof"), center=(bx, by, 2.2), base=True, chamfer=0.03)
        c.add(cap, dice=None)
    for x, y in ((-3.62, 3.62), (3.62, 3.62), (-3.62, -3.62), (3.62, -3.62)):
        ny = 1.0 if y > 0 else -1.0
        c.add(L.member((x, y, 0), (x, y, 5.6), 0.14, 0.14, c.sw("oak"), rng=c.rng, chamfer=0.02))
        c.add(L.box(0.5, 0.5, 0.25, c.sw("rubble"), center=(x, y, 0), base=True, chamfer=0.04), dice=None)
        banner(c, (x, y + 0.12 * ny, 5.35), 0.75, 2.0, normal=(0, ny))
        ball = L.lathe([(0, 0), (0.1, 0.05), (0.11, 0.15), (0.05, 0.25), (0, 0.32)], 8, c.sw("iron"))
        ball.move(x, y, 5.6)
        c.add(ball, dice=None)
    return {"height_target": (11.0, 12.2), "addon_of": "kingdom_moot_hall"}


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


def rope_ring(c, cx, cy, rr, zz, sides, a=0.0, th=0.03):
    """Saffron felt rope round a yurt (felt swatch, u = arc length: no flat palette cell)."""
    g = L.lathe([(rr, zz - th), (rr + th * 0.5, zz), (rr, zz + th)], sides, c.sw("saffron"), stretch=a, repeat=1.2)
    g.move(cx, cy, 0)
    return c.add(g, dice=None, layer=1.0, tint=(1.0, 0.92, 0.8))


def rope_path(c, pts, w=0.035, key="saffron", tint=(1.0, 0.92, 0.8), layer=1.0):
    """Rope / cord along a 3D polyline (felt swatch, u along the rope, v round it)."""
    p = L.sweep(L.rect_profile(w, w * 0.85), np.asarray(pts, float), c.sw(key), up=(0, 0, 1), repeat=1.2)
    return c.add(p, dice=None, layer=layer, tint=tint)


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
         ropes=True, lb=0.13, base_h=0.13, sides=20, door_w=None, team_w=0.17, glow=True,
         roof_shape="dome", door_key="saffron", vents=None, skirt=True):
    """Felt yurt: stone ring, visible lattice band below a rolled felt skirt, felt wall, domed felt roof
    with a team felt band at its base, a bronze crown ring with a warm smoke-ring glow (a long, stretched
    yurt gets `vents` round smoke vents along its top instead of one stretched strip), saffron girth and
    roof ropes, a lattice-wood door frame (door up to 1.5 m) with a felt hanging (front = +y)."""
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
    if skirt:
        sr = max(0.06, r * 0.05)
        sk = L.lathe([(r - 0.01, zs - sr * 0.6), (r + sr, zs - sr * 0.2), (r + sr * 1.15, zs + sr * 0.5),
                      (r + sr * 0.6, zs + sr * 1.2), (r + 0.01, zs + sr * 1.3)], sides, c.sw(felt), stretch=a)
        sk.move(cx, cy, 0)
        c.add(sk, dice=None, layer=1.0, tint=(0.78, 0.8, 0.8))
    rc = max(0.14, r * 0.17)
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
        z_hi = wall_h + team_w
        t_ = (z_hi - prof[1][1]) / max(prof[2][1] - prof[1][1], 1e-6)
        r_hi = prof[1][0] + (prof[2][0] - prof[1][0]) * min(t_, 1.0) + 0.025
        bnd = L.lathe([(r * 1.105, wall_h - 0.05), (r * 1.115, wall_h + 0.03), (r_hi, z_hi)], sides, c.sw("team_band"),
                      stretch=a, repeat=0.8)
        normalize_v(bnd)
        bnd.uv[..., 1] = 1.0 - bnd.uv[..., 1]
        bnd.move(cx, cy, 0)
        c.add(bnd, dice=None, layer=1.0)

    def crown_ring(x, y, rr, z):
        ring = L.torus(rr, max(0.045, rr * 0.18), c.sw("bronze"), segs=14, sides=5)
        ring.move(x, y, z + 0.02)
        c.add(ring, dice=None, layer=1.0)
        cap = L.lathe([(rr * 0.95, 0.0), (rr * 0.7, 0.07), (0.0, 0.1)], 12, c.sw("ember" if glow else "bronze"))
        if glow:
            vv = cap.v[cap.t]
            cap.uv = np.stack([0.5 + vv[..., 0] / (2.4 * rr), 0.5 + vv[..., 1] / (2.4 * rr)], -1)
        cap.move(x, y, z - 0.04)
        c.add(cap, dice=None, ao=False, min_shade=1.0, form=0.0, layer=1.0)
        for k in range(2):
            ang = k * math.pi / 2 + math.pi / 4
            d = np.array([math.cos(ang), math.sin(ang), 0.0]) * rr
            c.add(L.member(np.array([x, y, z + 0.04]) - d, np.array([x, y, z + 0.04]) + d, 0.04, 0.04, c.sw("wood")),
                  layer=1.0)

    if crown:
        if a > 0:
            # close the long ridge with felt, then round smoke vents along it (no stretched glow strip)
            top = L.lathe([(rc, 0.0), (rc * 0.55, 0.05), (0.0, 0.07)], sides, c.sw(roof_felt), stretch=a)
            top.move(cx, cy, ztop - 0.01)
            c.add(top, dice=None, layer=1.0)
            nv = vents or 2
            for xx in np.linspace(-a * 0.75, a * 0.75, nv):
                crown_ring(cx + xx, cy, rc * 0.95, ztop + 0.04)
        else:
            crown_ring(cx, cy, rc, ztop)
    if ropes:
        for zz in (zs + (wall_h - zs) * 0.32, zs + (wall_h - zs) * 0.72):
            rope_ring(c, cx, cy, r * 1.024 + 0.012, zz, sides, a=a, th=max(0.025, r * 0.018))
        nr = 8
        for k in range(nr):
            ang = (k + 0.5) * 2 * math.pi / nr
            pts = []
            for (rr, zz) in prof[2:]:
                x_ = math.cos(ang) * (rr + 0.02)
                x_ += a if math.cos(ang) >= 0 else -a
                pts.append((cx + x_, cy + math.sin(ang) * (rr + 0.02), zz))
            rope_path(c, pts, w=max(0.035, r * 0.025))
    if door:
        dw = door_w or min(0.62, r * 0.6)
        dh = min(wall_h - zs - 0.06, 1.5)
        yd = cy + r + 0.03
        fw_ = max(0.07, r * 0.05)
        for sx in (-1, 1):
            c.add(L.member((cx + sx * dw / 2, yd, z0), (cx + sx * dw / 2, yd, zs + dh + 0.06), fw_, fw_ * 1.15, c.sw("wood")),
                  layer=0.0)
        c.add(L.member((cx - dw / 2 - 0.06, yd, zs + dh + 0.06), (cx + dw / 2 + 0.06, yd, zs + dh + 0.06), fw_ * 1.3,
                       fw_ * 1.3, c.sw("wood")), layer=0.0)
        hang = L.box(dw - 0.04, 0.04, dh, c.sw(door_key), center=(cx, yd + 0.012, z0 + (dh + lb) / 2 + 0.01))
        if door_key.startswith("team"):
            hang.uv = _uv_rect(L.box(dw - 0.04, 0.04, dh, c.sw(door_key)).rot(90, 0, 0), dw - 0.04, dh)
        c.add(hang, dice=None, layer=1.0)
        lin = L.box(dw + 0.2, 0.07, 0.14, c.sw("saffron"), center=(cx, yd + 0.045, zs + dh + 0.16), chamfer=0.02)
        c.add(lin, dice=None, layer=1.0, tint=(0.8, 0.8, 0.8))
    return ztop


def shell_dome(c, cx, cy, r, h, key="shell", sides=16, rim_key="drystone"):
    """Tortoise-shell dome: hex-plated shell on a low stone rim."""
    prof = [(r * 1.0, 0.0), (r * 1.02, 0.12 * h), (r * 0.94, 0.4 * h), (r * 0.72, 0.7 * h), (r * 0.4, 0.92 * h), (0.0, h)]
    d = L.lathe(prof, sides, c.sw(key), smooth=70)
    d.move(cx, cy, 0.1)
    c.add(d, dice=0.45, layer=1.0)
    stone_ring(c, cx, cy, r * 0.98, 0.14, key=rim_key, sides=sides)


def standing_stone(c, pos, h, w, d, rz=0.0, lean=(0.0, 0.0), glyphs=("hail", "wind"), seed=0):
    """Rough standing stone (tapered, rounded top, noise-chiselled, box-projected stone) with one or two
    square carved glyph decals (hail, wind) on its inner face: square quads, so the glyphs never stretch."""
    x, y, z = pos
    p = L.gbox(w, d, h, c.sw("stone"), center=(0, 0, 0), chamfer=0.06, grid=0.32)
    rng = np.random.default_rng(seed)
    zf = p.v[:, 2] / h
    p.v[:, 0] *= 1.0 - 0.26 * zf
    p.v[:, 1] *= 1.0 - 0.16 * zf
    top = zf > 0.7
    p.v[top, 2] -= (np.abs(p.v[top, 0]) / (w / 2)) ** 2 * h * 0.1 * rng.uniform(0.6, 1.4)
    p.v += L.noise_vec(p.v, 2.6, tuple(rng.uniform(0, 50, 3))) * np.array([0.05, 0.035, 0.04])
    p.box_uv()
    parts = [p]
    gs = w * 0.6
    zc = h * 0.62
    for k, g in enumerate(glyphs):
        zz = zc - k * gs * 1.15
        wk = (1.0 - 0.26 * (zz / h))
        hw = gs / 2 * wk
        yy = d / 2 * (1.0 - 0.16 * (zz / h)) + 0.04
        q = L.quad((-hw, yy, zz - gs / 2), (hw, yy, zz - gs / 2), (hw * 0.97, yy - 0.006, zz + gs / 2),
                   (-hw * 0.97, yy - 0.006, zz + gs / 2), c.sw("glyph_" + g))
        q = _face_out(q, Wall((0, 0), (1, 0), (0, 1), 1))
        parts.append(q)
    for q in parts:
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


def ring_fence(c, cx, cy, r, n=12, h=0.7, gap=None, floor_key="clay", post_r=0.085):
    """Round wrestling ring: carved posts, two sagging saffron rope rails, a packed sand floor."""
    fl = L.lathe([(r + 0.12, 0.0), (r + 0.1, 0.04), (r - 0.05, 0.065), (0.0, 0.07)], 24, c.sw(floor_key))
    fl.move(cx, cy, 0)
    c.add(fl, dice=0.6, jit=0.0, tint=(1.25, 1.12, 0.92), base=False)
    angs = [2 * math.pi * k / n + math.pi / n for k in range(n)]

    def in_gap(a):
        return gap is not None and abs(math.atan2(math.sin(a - gap), math.cos(a - gap))) < math.pi / n * 1.2

    for k, a in enumerate(angs):
        if in_gap(a):
            continue
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r, 0.0)
        m = L.lathe([(post_r * 1.1, 0), (post_r * 0.8, h), (post_r * 1.15, h + 0.04), (0.0, h + 0.14)], 7, c.sw("wood"))
        m.move(*p)
        c.add(m, dice=None, uvrot=True, layer=0.0)
    for zz in (h * 0.45, h * 0.88):
        for k in range(n):
            a0, a1 = angs[k], angs[(k + 1) % n]
            if in_gap(a0) or in_gap(a1):
                continue
            if a1 < a0:
                a1 += 2 * math.pi
            pts = []
            for i in range(5):
                t = i / 4
                a = a0 + (a1 - a0) * t
                pts.append((cx + math.cos(a) * (r + 0.02), cy + math.sin(a) * (r + 0.02), zz - 0.07 * math.sin(math.pi * t)))
            rope_path(c, pts, w=0.045, layer=0.0)


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
    """Charcoal / casting kiln: concave clay cone with iron hoops, a glowing stoke-hole at the front, a
    bronze vent ring with a glow inside."""
    prof = [(r * 1.04, 0.0), (r, 0.12 * h), (r * 0.8, 0.35 * h), (r * 0.54, 0.65 * h), (r * 0.33, 0.92 * h), (r * 0.31, h)]
    k = L.lathe(prof, 18, c.sw("clay"))
    k.move(cx, cy, 0)
    c.add(k, dice=0.4, jit=0.025, tint=(0.95, 0.85, 0.78))
    for zz in (0.3 * h, 0.62 * h):
        rr = np.interp(zz, [p[1] for p in prof], [p[0] for p in prof]) + 0.015
        b = L.lathe([(rr, zz - 0.05), (rr + 0.02, zz), (rr, zz + 0.05)], 18, c.sw("iron"))
        b.move(cx, cy, 0)
        c.add(b, dice=None)
    vent = L.torus(r * 0.31, 0.07, c.sw("bronze"), segs=14, sides=5)
    vent.move(cx, cy, h + 0.03)
    c.add(vent, dice=None)
    gd = L.lathe([(r * 0.29, 0.0), (0.0, 0.02)], 12, c.sw("ember"))
    vv = gd.v[gd.t]
    gd.uv = np.stack([0.5 + vv[..., 0] / (0.7 * r), 0.5 + vv[..., 1] / (0.7 * r)], -1)
    gd.move(cx, cy, h - 0.06)
    c.add(gd, dice=None, ao=False, min_shade=1.0, form=0.0)
    w = Wall((cx + r * 0.32, cy + r * 0.94), (-1, 0), (0, 1), r * 0.64)
    arch = [(0, 0.0), (r * 0.64, 0.0), (r * 0.64, h * 0.15), (r * 0.32, h * 0.23), (0, h * 0.15)]
    q = L.prism(arch, 0.0, 0.02, c.sw("ember"), chamfer=0.0, bottom=False)
    vv = q.v[q.t]
    q.uv = np.stack([0.15 + vv[..., 0] / (r * 0.64) * 0.7, 0.95 - vv[..., 1] / (h * 0.23) * 0.6], -1)
    w.place(q)
    c.add(q, dice=None, ao=False, min_shade=1.0, form=0.0, occ=False)
    lip = L.member(w.p(-0.06, h * 0.24, 0.05), w.p(r * 0.7, h * 0.24, 0.05), 0.12, 0.1, c.sw("clay"))
    c.add(lip, tint=(0.8, 0.7, 0.62))


def urn_tripod(c, pos, s=1.0, steam=True):
    """Big polished bronze tea urn with lid, spout and ring handles on an iron tripod; a curl of steam
    from the spout."""
    x, y, z = pos
    zh = 0.42 * s
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        c.add(L.member((x + math.cos(a) * 0.36 * s, y + math.sin(a) * 0.36 * s, z), (x + math.cos(a) * 0.15 * s,
                       y + math.sin(a) * 0.15 * s, z + zh), 0.05 * s, 0.05 * s, c.sw("iron")))
    ring = L.torus(0.18 * s, 0.03 * s, c.sw("iron"), segs=12, sides=4)
    ring.move(x, y, z + zh)
    c.add(ring, dice=None)
    prof = [(0.0, 0.0), (0.12, 0.0), (0.25, 0.12), (0.28, 0.26), (0.23, 0.42), (0.11, 0.5), (0.1, 0.56), (0.15, 0.6),
            (0.13, 0.64), (0.06, 0.7), (0.035, 0.76), (0.0, 0.79)]
    u = L.lathe([(a_ * s * 1.3, b_ * s) for a_, b_ in prof], 16, c.sw("bronze"))
    u.move(x, y, z + zh - 0.02 * s)
    c.add(u, dice=None, tint=(1.12, 1.06, 0.95), smooth=70.0)
    sp0 = np.array([x + 0.26 * s, y + 0.16 * s, z + zh + 0.3 * s])
    sp1 = np.array([x + 0.48 * s, y + 0.3 * s, z + zh + 0.5 * s])
    c.add(L.member(sp0, sp1, 0.055 * s, 0.055 * s, c.sw("bronze")), dice=None)
    for sgn in (-1, 1):
        hd = L.torus(0.075 * s, 0.02 * s, c.sw("bronze"), segs=8, sides=4).rot(90, 0, 0).rot(0, 0, 90)
        hd.move(x + sgn * 0.35 * s, y, z + zh + 0.36 * s)
        c.add(hd, dice=None)
    if steam:
        pts = []
        for i in range(9):
            t = i / 8
            pts.append(sp1 + np.array([0.06 * s * math.sin(t * 5.0), 0.05 * s * math.cos(t * 4.0), 0.0]) * (1 + t)
                       + np.array([0.08 * s * t, 0.02 * s * t, 0.55 * s * t]))
        st = ribbon(c, pts, 0.1 * s, key="pal", normal_hint=(1, -1, 0), taper=0.6, min_shade=0.85, occ=False)
        c.pal_uv(st, "#E9DDBF")


def low_table(c, pos, w=1.3, d=0.75, h=0.38, cups=3, rz=0.0):
    """One big low tea table with a bronze tray and a few big cups on it (no loose cups on the ground)."""
    x, y, z = pos
    parts = [L.box(w, d, 0.07, c.sw("wood"), chamfer=0.02, center=(0, 0, h))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(L.box(0.09, 0.09, h, c.sw("wood"), center=(sx * (w / 2 - 0.08), sy * (d / 2 - 0.08), h / 2)))
    for p in parts:
        p.rot(0, 0, rz).move(x, y, z)
        c.add(p, dice=None)
    tray = L.lathe([(0.0, 0.0), (d * 0.42, 0.0), (d * 0.45, 0.04), (d * 0.42, 0.045), (0.0, 0.02)], 14, c.sw("bronze"))
    tray.move(0.0, 0.0, h + 0.035).rot(0, 0, rz).move(x, y, z)
    c.add(tray, dice=None, tint=(1.1, 1.05, 0.95))
    for k in range(cups):
        a = k * 2 * math.pi / cups + 0.4
        cu = L.lathe([(0.0, 0.0), (0.06, 0.0), (0.1, 0.11), (0.09, 0.12), (0.0, 0.05)], 10, c.sw("bronze"))
        cu.move(math.cos(a) * d * 0.25, math.sin(a) * d * 0.25, h + 0.075).rot(0, 0, rz).move(x, y, z)
        c.add(cu, dice=None)


def cushion(c, pos, key, r=0.24):
    b = L.blob(c.sw(key), radius=r, subdiv=1, scale=(1, 1, 0.42), seed=int(c.r(0, 999)), noise_amp=0.05, flat_bottom=0.0)
    b.move(*pos)
    c.add(b, dice=None)


def mirror_post(c, pos, h, facing_deg, tilt=52.0, mr=0.45, streamer=True):
    """Carved post with a yoke holding a big bronze sun-mirror (mr = radius), its face turned towards
    `facing_deg` and tilted up by `tilt` degrees (towards the RTS camera at ~56)."""
    x, y, z = pos
    carved_mast(c, pos, h, r0=0.1, r1=0.075, bands=2, cap=None, streamers=1 if streamer else 0, s_len=1.4,
                dirn=(math.cos(math.radians(facing_deg + 90)), math.sin(math.radians(facing_deg + 90))), phase=facing_deg)
    zc = z + h + mr * 0.62
    parts = []
    for sgn in (-1, 1):
        parts.append(L.member((sgn * (mr + 0.06), 0, h - 0.08), (sgn * (mr + 0.06), 0, h + mr * 0.85), 0.07, 0.07, c.sw("wood")))
    parts.append(L.member((-(mr + 0.1), 0, h - 0.06), ((mr + 0.1), 0, h - 0.06), 0.08, 0.08, c.sw("wood")))
    for p in parts:
        p.rot(0, 0, facing_deg - 90).move(x, y, z)
        c.add(p, dice=None)
    t = mr * 0.06
    prof = [(0.0, -t * 2), (mr * 0.9, -t), (mr, 0.0), (mr * 0.96, t * 1.8), (mr * 0.85, t * 1.2), (0.0, t * 0.6)]
    m = L.lathe(prof, 18, c.sw("bronze"))
    m.rot(-90 + tilt, 0, 0).rot(0, 0, facing_deg - 90).move(x, y, zc)
    c.add(m, dice=None, tint=(1.2, 1.12, 1.0), min_shade=0.6)


def recurve_bow(c, center, span, facing_deg=90.0, elev=10.0, limb=0.13):
    """Large laminated recurve bow of wood and bronze (span m, limbs `limb` m thick) with bronze-capped tips
    that flick forward, a string, a stock and grip; aimed at facing_deg, raised by elev degrees."""
    x, y, z = center
    n = 18
    pts = []
    for i in range(n + 1):
        t = i / n * 2 - 1
        bx = t * span / 2
        by = -0.15 * span * (1 - t * t) + (0.11 * span * ((abs(t) - 0.75) / 0.25) ** 2 if abs(t) > 0.75 else 0.0)
        pts.append((bx, by, 0.0))
    pts = np.array(pts)
    sc = np.array([0.65 + 0.55 * (1 - abs(i / n * 2 - 1)) for i in range(n + 1)])
    bow = L.sweep(L.rect_profile(limb * 0.85, limb, 0.02), pts, c.sw("wood"), scales=sc, up=(0, 0, 1))
    parts = [(bow, None, 1.0)]
    for sgn in (-1, 1):
        k = n if sgn > 0 else 0
        dvec = nrm(pts[k] - pts[k - 1 if sgn > 0 else 1])
        tip = L.lathe([(limb * 0.55, 0), (limb * 0.5, 0.12), (limb * 0.25, 0.2), (0.0, 0.26)], 8, c.sw("bronze"))
        ang = math.degrees(math.atan2(dvec[1], dvec[0]))
        tip.rot(0, 90, 0).rot(0, 0, ang).move(*(pts[k] - dvec * 0.04))
        parts.append((tip, None, 1.15))
    for (bx, bw_) in ((-span * 0.22, 0.1), (span * 0.22, 0.1)):
        band = L.box(0.1, limb * 1.0, limb * 1.15, c.sw("bronze"), chamfer=0.015,
                     center=(bx, -0.15 * span * (1 - (2 * bx / span) ** 2), 0.0))
        parts.append((band, None, 1.1))
    string = L.member(pts[0] + np.array([0.03, 0.02, 0]), pts[-1] - np.array([0.03, -0.02, 0]), 0.025, 0.025, c.sw("pal"))
    parts.append((string, "#E9DDBF", 1.0))
    stock = L.box(0.14, span * 0.5, 0.12, c.sw("wood"), chamfer=0.025, center=(0, -span * 0.1, -0.03))
    parts.append((stock, None, 1.0))
    grip = L.box(0.22, 0.18, 0.18, c.sw("bronze"), chamfer=0.025, center=(0, -0.15 * span, 0.0))
    parts.append((grip, None, 1.1))
    arrow = L.member((0, -0.15 * span - 0.05, 0.06), (0, span * 0.22, 0.06), 0.035, 0.035, c.sw("wood"))
    parts.append((arrow, None, 1.0))
    for p, col, tn in parts:
        p.rot(elev, 0, 0).rot(0, 0, facing_deg - 90).move(x, y, z)
        if col:
            c.P(p, col, dice=None)
        else:
            c.add(p, dice=None, tint=(tn, tn * 0.97, tn * 0.92))


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


def clans_apron(c, gaps=(), n_exp=3.2, **kw):
    """Clans apron: trampled earth inside a low drystone curb."""
    return apron(c, key="dirt", n_exp=n_exp, noise=0.09, edge="curb", gaps=gaps, tint=(1.0, 0.94, 0.86), **kw)


# =============================================================================================
# clans buildings
# =============================================================================================

def c_home_yurt(c):
    """Home Yurt (supply + worker garrison, 8x8 cells = 4 m, 3-3.5 m): a round felt dome with a glowing
    smoke ring, a rolled felt skirt (it rolls up for Roll the Felt) and a team band, a carved streamer
    mast by the door, a log pile and big clay jars, a felt rug on the trampled-earth apron inside a low
    stone curb."""
    clans_apron(c, gaps=[(0.0, 0.55)])
    yurt(c, 0.0, -0.18, 1.42, 1.62, 1.3, felt="teal", roof_felt="teal", lb=0.2, base_h=0.15, sides=24, door_w=0.8,
         team_w=0.26)
    carved_mast(c, (1.18, 1.05, APRON_Z), 2.8, r0=0.09, r1=0.065, bands=3, streamers=2, s_len=1.35, dirn=(1, 0.1))
    log_stack(c, (-1.38, 1.25, APRON_Z), 0.95, 3, r=0.11, axis="x")
    for (jx, jy, js) in ((1.62, -1.22, 1.0), (1.22, -1.62, 0.8)):
        jar = L.lathe([(0.0, 0.0), (0.14 * js, 0.0), (0.24 * js, 0.2 * js), (0.21 * js, 0.44 * js), (0.12 * js, 0.54 * js),
                       (0.14 * js, 0.6 * js), (0.0, 0.6 * js)], 12, c.sw("clay"))
        jar.move(jx, jy, APRON_Z)
        c.add(jar, dice=None, tint=(0.85, 0.7, 0.6))
    rug(c, 0.0, 1.55, 1.05, 0.62, rz=4.0, key="saffron")
    return {"height_target": (3.0, 3.5)}


def c_grapple_yard(c):
    """Grapple Yard (barracks, 12x12 cells = 6 m, 5-6 m): a long felt yurt at the back (two round smoke
    vents) beside a 3.6 m round wrestling ring with a sand floor and a post-and-rope fence (its entrance
    away from the yurt door), two tall carved masts with team streamers at the ring's entrance, mace racks
    and a bench on the trampled-earth apron."""
    clans_apron(c, gaps=[(-1.1, 0.6)])
    yurt(c, -0.98, -1.86, 0.98, 1.68, 1.45, felt="teal", roof_felt="teal", stretch=0.85, sides=18, door_w=0.82,
         team_w=0.3, door_key="team_plain", vents=2, lb=0.18, base_h=0.15)
    rcx, rcy, rr = 1.08, 1.06, 1.75
    gap = math.radians(160.0)
    ring_fence(c, rcx, rcy, rr, n=14, h=0.9, gap=gap)
    for k, (da, hh) in enumerate(((-0.24, 5.3), (0.24, 4.85))):
        a = gap + da
        carved_mast(c, (rcx + math.cos(a) * (rr + 0.12), rcy + math.sin(a) * (rr + 0.12), APRON_Z), hh, r0=0.13, r1=0.09,
                    bands=4, streamers=3, s_len=2.0, dirn=(1, -0.25 + 0.5 * k), phase=1.3 * k)
    mace_rack(c, (-2.45, 0.3, APRON_Z), rz=90, width=1.2, h=1.05, n=4)
    mace_rack(c, (-2.25, 1.55, APRON_Z), rz=75, width=1.0, h=1.0, n=3)
    c.add(L.box(1.2, 0.34, 0.09, c.sw("wood"), chamfer=0.025, center=(-1.2, 2.5, 0.4)), dice=None)
    for sx in (-0.45, 0.45):
        c.add(L.box(0.12, 0.3, 0.38, c.sw("wood"), center=(-1.2 + sx, 2.5, 0.19)), dice=None)
    barrel(c, (-2.3, 2.5, APRON_Z), r=0.27, h=0.62, key="wood")
    rug(c, -0.98, -0.42, 1.1, 0.6, rz=-3.0, key="saffron")
    return {"height_target": (5.0, 6.0)}


def c_naming_stones(c):
    """Naming Stones (hero altar, 12x12 cells = 6 m, 4.5-5.5 m): a ring of six rough standing stones (2.6-3.5
    m) carved with hail and wind glyphs (nothing hung on them, no faces), open to the camera, round an ochre
    felt floor with a flat naming stone at its centre; a frame of bronze gongs on team-ribboned cords beside
    them and two taller carved masts with long team streamers at the back."""
    clans_apron(c, gaps=[(0.0, 1.0)])
    plat = L.lathe([(2.38, 0.0), (2.36, 0.12), (2.26, 0.2), (0.0, 0.2)], 28, c.sw("drystone"))
    plat.move(0.0, -0.25, 0)
    c.add(plat, dice=0.6, jit=0.02, base=False)
    mat = L.lathe([(1.45, 0.205), (1.4, 0.235), (0.0, 0.24)], 24, c.sw("saffron"))
    mat.move(0.0, -0.25, 0)
    c.add(mat, dice=0.6, jit=0.0, tint=(0.74, 0.6, 0.44), layer=1.0, base=False)
    angs = [140, 185, 228, 270, 312, 355, 40]
    hs = [2.7, 3.2, 3.5, 3.3, 3.45, 3.0, 2.6]
    for k, (a, h) in enumerate(zip(angs, hs)):
        ar = math.radians(a)
        p = (math.cos(ar) * 1.95, -0.25 + math.sin(ar) * 1.95, 0.12)
        standing_stone(c, p, h, 0.82 + 0.1 * (k % 2), 0.5, rz=a + 90, lean=(c.r(-4, 4), c.r(-4, 4)),
                       glyphs=("hail", "wind") if k % 2 == 0 else ("wind", "hail"), seed=k + 3)
    centre = L.lathe([(0.62, 0.0), (0.64, 0.14), (0.58, 0.24), (0.0, 0.25)], 14, c.sw("stone"))
    centre.move(0.0, -0.25, 0.22)
    c.add(centre, dice=None, jit=0.015)
    gb, gw_, gh_ = np.array([1.9, 2.05, APRON_Z]), 1.35, 2.55
    gong_frame(c, tuple(gb), gw_, gh_, gongs=3, gr=0.26, facing=(-0.45, 1))
    ga = math.atan2(1, -0.45) - math.pi / 2
    ex = np.array([math.cos(ga), math.sin(ga), 0.0])
    fn = np.array([-0.45, 1.0, 0.0]) / math.hypot(0.45, 1.0)
    for sgn in (-1, 1):
        top = gb + ex * sgn * (gw_ / 2 + 0.16) + np.array([0, 0, gh_ - 0.02])
        pts = [top + np.array([0, 0, -1.45 * t]) + ex * sgn * 0.08 * math.sin(t * 4.0) + fn * 0.04 * t for t in np.linspace(0, 1, 9)]
        ribbon(c, pts, 0.3, key="team_plain", normal_hint=tuple(fn), taper=0.2)
    for sx in (-1, 1):
        carved_mast(c, (sx * 2.42, -2.25, APRON_Z), 4.85, r0=0.12, r1=0.085, bands=4, streamers=3, s_len=2.1,
                    dirn=(-sx * 0.55, 0.85), phase=sx * 2)
        mt = np.array([sx * 2.42, -2.25, APRON_Z + 4.45])
        c.add(L.member(mt - np.array([0.5, 0, 0]), mt + np.array([0.5, 0, 0]), 0.08, 0.08, c.sw("wood")), layer=0.0)
        banner(c, mt + np.array([0, 0.1, -0.02]), 0.82, 2.3, normal=(0, 1), bar=False)
    return {"height_target": (4.5, 5.5)}


def c_casting_pit(c):
    """Casting Pit (smithy + lumber drop-off, 12x12 cells = 6 m, 5-6 m): a casting pit sunk into a raised
    packed-clay working floor (stone-lined inner wall dropping to a dark floor, a glowing crucible and a
    glowing pour channel), a 2.8 m clay cone kiln, a tall log stack under a felt lean-to (lumber drop-off
    read), a carved mast with team streamers and a team banner on the lean-to."""
    clans_apron(c, gaps=[(0.5, 0.6)])
    px, py = -0.55, 0.7
    mound = L.lathe([(2.05, 0.0), (1.98, 0.1), (1.62, 0.3), (1.32, 0.36), (1.24, 0.36)], 26, c.sw("clay"))
    mound.move(px, py, 0)
    c.add(mound, dice=0.5, jit=0.02, tint=(1.0, 0.9, 0.8), base=False)
    lip = L.lathe([(1.3, 0.34), (1.28, 0.42), (1.18, 0.44), (1.1, 0.4)], 22, c.sw("drystone"))
    lip.move(px, py, 0)
    c.add(lip, dice=None, jit=0.025)
    wall = L.lathe([(1.1, 0.4), (1.02, 0.25), (0.96, 0.05)], 22, c.sw("drystone"))    # top -> bottom: faces inwards
    wall.move(px, py, 0)
    c.add(wall, dice=None, tint=(0.42, 0.38, 0.36), ao_mul=1.4, form=0.0)
    fl = L.lathe([(0.97, 0.05), (0.0, 0.05)], 20, c.sw("clay"))
    fl.move(px, py, 0)
    c.add(fl, dice=0.4, tint=(0.3, 0.25, 0.23), ao_mul=1.3, form=0.0, base=False)
    cru = L.lathe([(0.3, 0.05), (0.42, 0.18), (0.45, 0.38), (0.4, 0.42)], 14, c.sw("clay"))
    cru.move(px + 0.1, py - 0.05, 0)
    c.add(cru, dice=None, tint=(0.75, 0.6, 0.52))
    mol = L.lathe([(0.39, 0.38), (0.0, 0.4)], 14, c.sw("ember"))
    vv = mol.v[mol.t]
    mol.uv = np.stack([0.5 + vv[..., 0] / 0.9, 0.5 + vv[..., 1] / 0.9], -1)
    mol.move(px + 0.1, py - 0.05, 0)
    c.add(mol, dice=None, ao=False, min_shade=1.0, form=0.0)
    ch = L.quad((px - 0.85, py + 0.42, 0.065), (px - 0.25, py + 0.12, 0.065), (px - 0.2, py + 0.25, 0.065),
                (px - 0.8, py + 0.55, 0.065), c.sw("ember"), uv=((0.1, 0.55), (0.9, 0.55), (0.9, 0.45), (0.1, 0.45)))
    c.add(ch, dice=None, ao=False, min_shade=1.0, form=0.0, occ=False)
    for sgn in (-1, 1):
        c.add(L.member((px + 0.55, py + sgn * 0.08, 0.42), (px + 1.45, py + sgn * 0.2, 0.75), 0.05, 0.05, c.sw("iron")),
              dice=None)
    # kiln: 2.8 m clay cone, its stoke-hole glowing at the camera
    kiln(c, 1.72, -1.15, 1.08, 2.8)
    # lean-to (felt roof on poles) at the back left with a tall log stack against it (ring ends to the camera)
    ax0, ax1, ay0, ay1 = -2.82, -0.35, -2.8, -1.5
    for xx in (ax0 + 0.08, (ax0 + ax1) / 2, ax1 - 0.08):
        c.add(L.member((xx, ay1, 0.0), (xx, ay1, 2.25), 0.1, 0.1, c.sw("wood")))
        c.add(L.member((xx, ay0, 0.0), (xx, ay0, 1.75), 0.1, 0.1, c.sw("wood")))
    aw = L.plate((ax0 - 0.1, ay0 - 0.15, 1.72), (ax1 + 0.1, ay0 - 0.15, 1.72), (ax1 + 0.1, ay1 + 0.25, 2.3),
                 (ax0 - 0.1, ay1 + 0.25, 2.3), 0.04, c.sw("teal"), segs=(4, 2))
    aw.box_uv()
    c.add(aw, dice=None, layer=1.0)
    for row, n in enumerate((5, 5, 4, 4, 3, 2)):
        for k in range(n):
            xx = ax0 + 0.3 + (k + 0.5 * (row % 2)) * 0.44
            log1(c, (xx, (ay0 + ay1) / 2 + 0.05, row * 0.3), 1.2, 0.16 + 0.02 * c.r(), axis="y", sides=8)
    banner(c, ((ax0 + ax1) / 2, ay1 + 0.3, 2.27), 1.2, 1.3, normal=(0, 1), bar=False)
    for i in range(6):
        xa, xb = ax0 - 0.1 + (ax1 - ax0 + 0.2) * i / 6, ax0 - 0.1 + (ax1 - ax0 + 0.2) * (i + 1) / 6
        q = L.quad((xa, ay1 + 0.27, 1.98), (xb, ay1 + 0.27, 1.98), (xb, ay1 + 0.27, 2.3), (xa, ay1 + 0.27, 2.3),
                   c.sw("team_plain"), uv=((0.1, 0.95), (0.9, 0.95), (0.9, 0.05), (0.1, 0.05)))
        b2 = q.copy()
        b2.t = b2.t[:, ::-1]
        b2.uv = b2.uv[:, ::-1]
        b2.move(0, -0.02, 0)
        c.add(L.merge([q, b2]), dice=None, form=0.0)
    carved_mast(c, (2.45, 1.95, APRON_Z), 5.0, r0=0.12, r1=0.085, bands=4, streamers=3, s_len=1.9, dirn=(-1, -0.25))
    log_stack(c, (1.95, 0.75, APRON_Z), 1.0, 3, r=0.13, axis="x")
    return {"height_target": (5.0, 6.0)}


def c_mirror_yurt(c):
    """Mirror Yurt (caster lodge, 12x12 cells = 6 m, 5-6 m): a tall felt dome under a saffron cap and a bronze
    knob, ringed by big bronze sun-mirrors (0.9 m) on tilting carved posts, their faces turned up towards
    the sky and the RTS camera (nothing sewn or studded on the felt)."""
    clans_apron(c, gaps=[(0.0, 0.6)])
    ztop = yurt(c, 0.0, -0.4, 1.72, 1.62, 2.85, felt="teal", roof_felt="teal", sides=26, roof_shape="tall", door_w=0.82,
                team_w=0.55, door_key="team_plain", lb=0.2, base_h=0.15)
    cap = L.lathe([(0.55, ztop - 0.45), (0.46, ztop - 0.15), (0.28, ztop + 0.02)], 18, c.sw("saffron"))
    cap.move(0.0, -0.4, 0.0)
    c.add(cap, dice=None, layer=1.0)
    kb = L.lathe([(0, 0), (0.15, 0.07), (0.16, 0.22), (0.08, 0.36), (0.0, 0.55)], 12, c.sw("bronze"))
    kb.move(0.0, -0.4, ztop + 0.06)
    c.add(kb, dice=None, tint=(1.15, 1.08, 0.95))
    for k, (a, hh) in enumerate(((22, 2.45), (52, 2.2), (128, 2.2), (158, 2.45), (205, 2.6), (335, 2.6))):
        ar = math.radians(a)
        pos = (math.cos(ar) * 2.32, -0.4 + math.sin(ar) * 2.2, APRON_Z)
        diff = (a - 90 + 180) % 360 - 180
        mirror_post(c, pos, hh, 90.0 + 0.3 * diff, tilt=52.0, mr=0.45)
    rug(c, 0.0, 1.65, 1.1, 0.62, rz=-4.0, key="saffron")
    return {"height_target": (5.0, 6.0)}


def c_bow_mast(c):
    """Bow-Mast (tower, 4x4 cells = 2 m, 6-8 m): a tall carved mast on a 1.7 m drystone footing with a carved
    collar and three raking braces, a round deck with a felt windbreak (team band), a 2.6 m laminated
    recurve bow of wood and bronze on a visible swivel post (bronze-capped tips projecting past the
    windbreak, aimed 20 degrees off the camera axis), long felt streamers and a felt cone cap."""
    apron(c, key="dirt", n_exp=3.0, noise=0.04, edge=None, inset=0.03, tint=(1.0, 0.94, 0.86))
    foot = L.lathe([(0.86, 0.0), (0.85, 0.16), (0.74, 0.22), (0.62, 0.24), (0.6, 0.36), (0.42, 0.4), (0.0, 0.4)], 16,
                   c.sw("drystone"))
    c.add(foot, dice=None, jit=0.03)
    zd = 3.7
    carved_mast(c, (0.0, 0.0, 0.38), 5.75, r0=0.21, r1=0.11, bands=5, cap="cone", streamers=3, s_len=2.4, dirn=(1, 0.2),
                cap_key="saffron")
    col = L.lathe([(0.3, 0.38), (0.33, 0.48), (0.27, 0.58), (0.31, 0.7), (0.24, 0.82), (0.0, 0.82)], 12, c.sw("bronze"))
    c.add(col, dice=None, tint=(1.05, 1.0, 0.92))
    for k in range(3):
        a = math.radians(90 + 120 * k + 60)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c.add(L.member(d * 0.66 + np.array([0, 0, 0.3]), d * 0.2 + np.array([0, 0, 1.75]), 0.12, 0.12, c.sw("wood")),
              layer=0.0)
        pbox(c, 0.26, 0.26, 0.16, "drystone", center=tuple(d * 0.66 + np.array([0, 0, 0.26])), taper=0.1)
    deck = L.lathe([(0.84, zd - 0.07), (0.88, zd), (0.84, zd + 0.07)], 16, c.sw("wood"), cap_top=True, cap_bottom=True)
    c.add(deck, dice=None, layer=0.0)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c.add(L.member(d * 0.17 + np.array([0, 0, zd - 1.25]), d * 0.74 + np.array([0, 0, zd - 0.05]), 0.09, 0.09, c.sw("wood")),
              layer=0.0)
    for a in np.radians(np.linspace(150, 390, 7)):
        q = (math.cos(a) * 0.76, math.sin(a) * 0.76)
        c.add(L.member((q[0], q[1], zd - 0.02), (q[0], q[1], zd + 0.72), 0.06, 0.06, c.sw("wood")), layer=0.0)
    felt_panel(c, 0.0, 0.0, 0.76, 150, 390, zd + 0.06, zd + 0.36, key="teal")
    felt_panel(c, 0.0, 0.0, 0.765, 150, 390, zd + 0.36, zd + 0.64, key="team_band")
    rope_ring(c, 0.0, 0.0, 0.77, zd + 0.68, 16, th=0.03)
    # swivel post (bronze-banded) and the big bow on it
    sp = L.lathe([(0.11, 0.0), (0.1, 0.42), (0.15, 0.45), (0.15, 0.55), (0.12, 0.6)], 10, c.sw("wood"))
    sp.move(0.0, 0.14, zd)
    c.add(sp, dice=None)
    for zz in (0.12, 0.5):
        b = L.lathe([(0.125, zz - 0.04), (0.14, zz), (0.125, zz + 0.04)], 10, c.sw("bronze"))
        b.move(0.0, 0.14, zd)
        c.add(b, dice=None)
    recurve_bow(c, (0.05, 0.1, zd + 0.72), 2.5, facing_deg=125.0, elev=12.0, limb=0.13)
    for i in range(10):
        zz = 0.6 + i * 0.3
        c.add(L.member((0.0, 0.2, zz), (0.0, 0.36, zz + 0.02), 0.045, 0.045, c.sw("wood")), layer=0.0)
    return {"height_target": (6.0, 8.0)}


def c_tea_tent(c):
    """Tea Tent (faction shop, 12x12 cells = 6 m, 4.5-5.5 m): a striped saffron-and-teal yurt with a felt
    porch awning on carved posts (team valance), a 1.45 m polished bronze tea urn on an iron tripod with a
    curl of steam at the door, one big low tea table with a bronze tray and cups, felt cushions, two
    streamer masts."""
    clans_apron(c, gaps=[(0.0, 0.7)])
    ztop = yurt(c, 0.0, -0.6, 1.68, 1.55, 1.8, felt="stripes", roof_felt="stripes", sides=24, door_w=0.82, team_w=0.46,
                door_key="team_plain", lb=0.2, base_h=0.15)
    kb = L.lathe([(0, 0), (0.14, 0.06), (0.14, 0.18), (0.0, 0.4)], 10, c.sw("bronze"))
    kb.move(0.0, -0.6, ztop + 0.08)
    c.add(kb, dice=None)
    for sx in (-1, 1):
        carved_mast(c, (sx * 1.05, 1.95, APRON_Z), 2.05, r0=0.075, r1=0.06, bands=2, cap="knob", streamers=0)
    aw = L.plate((-1.25, 1.12, 2.12), (1.25, 1.12, 2.12), (1.25, 2.05, 1.85), (-1.25, 2.05, 1.85), 0.04, c.sw("stripes"))
    aw.box_uv()
    c.add(aw, dice=None, layer=1.0)
    for i in range(5):
        xa, xb = -1.25 + 2.5 * i / 5, -1.25 + 2.5 * (i + 1) / 5
        q = L.quad((xa, 2.07, 1.47), (xb, 2.07, 1.47), (xb, 2.07, 1.85), (xa, 2.07, 1.85), c.sw("team_plain"),
                   uv=((0.1, 0.95), (0.9, 0.95), (0.9, 0.05), (0.1, 0.05)))
        b2 = q.copy()
        b2.t = b2.t[:, ::-1]
        b2.uv = b2.uv[:, ::-1]
        b2.move(0, -0.02, 0)
        c.add(L.merge([q, b2]), dice=None, form=0.0)
    urn_tripod(c, (1.88, 1.42, APRON_Z), s=1.2)
    low_table(c, (-1.55, 1.85, APRON_Z), w=1.35, d=0.78, h=0.38, cups=3, rz=-8.0)
    for (cx_, cy_, key) in ((-2.45, 1.45, "teal"), (-1.6, 2.55, "saffron"), (-0.55, 2.3, "teal")):
        cushion(c, (cx_, cy_, APRON_Z), key, 0.32)
    for sx, hh in ((-2.4, 4.7), (2.45, 4.3)):
        carved_mast(c, (sx, -2.2, APRON_Z), hh, r0=0.1, r1=0.075, bands=3, streamers=2, s_len=1.7,
                    dirn=(0.3 * (1 if sx < 0 else -1), 1), phase=sx)
    return {"height_target": (4.5, 5.5)}


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
    "clans_casting_pit": dict(fn=c_casting_pit, cells=(12, 12), role="smithy + lumber drop-off (Casting Pit)"),
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
    for p in parts:   # nothing below ground except the apron skirts
        if not p.below:
            p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    v = np.concatenate([p.v for p in parts])
    lo, hi = v.min(0), v.max(0)
    H = float(hi[2])
    # footprint check: ground-level geometry inside the footprint, at most ~0.3 m overhang above
    hx, hy = c.fp[0] / 2, c.fp[1] / 2
    over = {"below_1.5m": 0.0, "above_1.5m": 0.0}
    for p in parts:
        ox = np.maximum(np.abs(p.v[:, 0]) - hx, np.abs(p.v[:, 1]) - hy)
        low = p.v[:, 2] < 1.5
        if low.any():
            over["below_1.5m"] = max(over["below_1.5m"], float(ox[low].max()))
            if os.environ.get("VC_FP_DEBUG") and ox[low].max() > 0.03:
                L.log(f"  fp {aid}: {p.sw.key} overshoots {ox[low].max():.3f} m at "
                      f"{np.round(p.v[low][np.argmax(ox[low])], 2)}")
        if (~low).any():
            over["above_1.5m"] = max(over["above_1.5m"], float(ox[~low].max()))
            if os.environ.get("VC_FP_DEBUG") and ox[~low].max() > 0.3:
                L.log(f"  fp {aid}: {p.sw.key} overhangs {ox[~low].max():.3f} m at "
                      f"{np.round(p.v[~low][np.argmax(ox[~low])], 2)}")
    over = {k: round(max(v_, 0.0), 3) for k, v_ in over.items()}
    if over["below_1.5m"] > 0.05 or over["above_1.5m"] > 0.32:
        L.log(f"  WARNING {aid}: geometry outside the footprint {over}")
    anchors = {k: [round(float(v[0]), 3), round(float(v[2]), 3), round(float(-v[1]), 3)] for k, v in c.anchors.items()}
    extras = {
        "vibecraft": {
            "id": aid, "kit": "tools/kits/buildings.py", "footprint_cells": list(spec["cells"]),
            "facing": "front faces -Z; UnitView draws structures at a fixed world yaw of PI (door to the +Z RTS camera)",
            "build_progress": "tools/kits/build_reveal.gdshader: height = VERTEX.y / model_height (height_m), "
                              "reveal bottom-up behind a ragged edge; clans two_pass: UV2.x = 0 lattice/frame "
                              "first, 1 felt/cover second",
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
        "glb_sha1": _sha1(path),
        "team_piping_tris": st["team_piping_tris"], "outside_footprint_m": over,
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
    ["clans_shell_hall", "clans_banner_shell", "clans_home_yurt", "clans_grapple_yard", "clans_naming_stones"],
    ["clans_casting_pit", "clans_mirror_yurt", "clans_bow_mast", "clans_tea_tent"],
]
# art bible 2.4: the slice default is kingdom Emerald against clans Royal Blue (screenshots never show the
# kingdom in blue / gold or the clans in Crimson / Violet); Crimson is only a readability stress test
TEAM_COLOURS = {"kingdom": "#2EAE3A", "clans": "#285DE6"}
STRESS_COLOURS = {"kingdom": "#D8232A", "clans": "#D8232A"}
HALLS = {"kingdom_moot_hall": "kingdom_moot_hall", "kingdom_walled_burg": "kingdom_moot_hall",
         "clans_shell_hall": "clans_shell_hall", "clans_banner_shell": "clans_shell_hall"}


def _run_lineup(spec, tmp, name):
    spec = dict(spec)
    spec["out"] = os.path.join(tmp, name + ".png")
    spec["anchors"] = os.path.join(tmp, name + "_anchors.json")
    sp = os.path.join(tmp, name + "_spec.json")
    with open(sp, "w") as f:
        json.dump(spec, f)
    cmd, env = _godot_cmd("buildings_lineup.gd", sp)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=900)
    if "VC_LINEUP_OK" not in r.stdout:
        raise SystemExit("lineup render failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
    with open(spec["anchors"]) as f:
        return spec["out"], json.load(f)


def _label(im, anchors, title):
    from PIL import ImageDraw, ImageFont
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
    d.rectangle([0, 0, im.width, 34], fill=(20, 22, 26))
    d.text((12, 6), title, font=f2, fill=(235, 235, 235))
    return im


def render_lineup(out_png, model_dir, hall_scale=1.0, unit="assets/models/units/kingdom_infantry.glb", size=(2600, 2000),
                  colours=None, tag=""):
    """Catalogue line-up of every building (+ the AI halls, native 8 m unless hall_scale) on meadow ground
    at the RTS pitch (56 deg; FOV 30 so the whole set fits), a 1.75 m unit beside each. colours: team
    colour per faction (default: the slice default kingdom Emerald / clans Royal Blue, bible 2.4)."""
    import tempfile
    from PIL import Image
    colours = colours or TEAM_COLOURS
    tmp = tempfile.mkdtemp(prefix="vc_lineup_")
    items, labels = [], []
    gap = 1.8
    rows = [[a for a in row if a in HALLS or (a in ALL and os.path.exists(os.path.join(model_dir, a + ".glb")))]
            for row in LINEUP_ROWS]

    def wid(aid):
        return 8.0 * hall_scale if aid in HALLS else ALL[aid]["cells"][0] * 0.5

    widths = [sum(wid(a) + gap + 0.9 for a in row) for row in rows]
    depth = [max(wid(a) for a in row) for row in rows]
    z_rows, z = [], 0.0
    for r in range(len(rows)):
        z_rows.append(z + depth[r] / 2)
        z += depth[r] + 5.5
    maxw = max(widths)
    for r, row in enumerate(rows):
        x = widths[r] / 2
        for aid in row:
            fac = aid.split("_")[0]
            w = d = wid(aid)
            cx = x - w / 2
            zc = z_rows[r]
            glbs = []
            if aid in HALLS:
                glbs.append((os.path.join(model_dir, HALLS[aid] + ".glb"), hall_scale))
                if aid != HALLS[aid]:
                    glbs.append((os.path.join(model_dir, aid + ".glb"), hall_scale))
            else:
                glbs.append((os.path.join(model_dir, aid + ".glb"), 1.0))
            for g, sc in glbs:
                if os.path.exists(g):
                    items.append({"glb": os.path.abspath(g), "pos": [cx, 0.0, zc], "scale": sc, "team": colours[fac]})
            items.append({"glb": os.path.join(REPO, unit), "pos": [cx - w / 2 - 0.45, 0.0, zc - d / 2 + 0.2],
                          "team": colours["kingdom"], "clip": "idle"})
            label = aid.replace("kingdom_", "").replace("clans_", "").replace("_", " ")
            sub = f"{ALL[aid]['cells'][0]}x{ALL[aid]['cells'][1]} cells" if aid in ALL and aid not in HALLS else (
                "AI hall 16x16" + (" + add-on" if aid in ALL else "") + (f", x{hall_scale:g}" if hall_scale != 1 else ""))
            labels.append({"label": label, "sub": sub, "world": [cx, 0.0, zc - d / 2 - 0.9]})
            x -= w + gap + 0.9
    zmid = (z_rows[0] + z_rows[-1]) / 2
    spec = {"size": list(size), "pitch": 56.0, "fov": 30.0, "target": [0.0, 0.0, zmid - 0.5],
            "distance": max(maxw * 1.42, (z_rows[-1] - z_rows[0] + 10.0) * 2.0),
            "ground": os.path.join(REPO, "assets/textures/terrain/gv_meadow.png"), "items": items, "labels": labels}
    frame, anchors = _run_lineup(spec, tmp, "catalogue")
    im = Image.open(frame).convert("RGB")
    title = (f"Vibecraft procedural buildings (tools/kits/buildings.py) beside the AI halls (x{hall_scale:g}); RTS pitch 56, "
             f"FOV 30 catalogue; unit = kingdom_infantry 1.75 m; team: kingdom {colours['kingdom']}, clans {colours['clans']}"
             + (f"  [{tag}]" if tag else ""))
    _label(im, anchors, title)
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    im.save(out_png, optimize=True)
    return out_png


GAME_BASES = {
    "kingdom": [("kingdom_moot_hall", 0.0, 9.5), ("kingdom_walled_burg", 0.0, 9.5), ("kingdom_croft", -8.2, 2.0),
                ("kingdom_croft", -12.6, 2.0), ("kingdom_croft", -8.2, -2.6), ("kingdom_drill_yard", 8.0, 2.2),
                ("kingdom_foundry", 14.6, 2.2), ("kingdom_oath_hall", -9.8, 9.8), ("kingdom_curio_cabinet", 9.8, 10.2),
                ("kingdom_timber_yard", -16.6, 9.8), ("kingdom_gun_tower", 3.6, -4.6), ("kingdom_lookout", -3.6, -4.6)],
    "clans": [("clans_shell_hall", 0.0, 9.5), ("clans_banner_shell", 0.0, 9.5), ("clans_home_yurt", -8.2, 2.0),
              ("clans_home_yurt", -12.6, 2.0), ("clans_home_yurt", -8.2, -2.6), ("clans_grapple_yard", 8.0, 2.2),
              ("clans_casting_pit", 14.6, 2.2), ("clans_naming_stones", -9.8, 9.8), ("clans_tea_tent", 9.8, 10.2),
              ("clans_mirror_yurt", -16.6, 9.8), ("clans_bow_mast", 3.6, -4.6), ("clans_bow_mast", -3.6, -4.6)],
}
GAME_UNITS = {
    "kingdom": [("kingdom_infantry", 1.5, -2.0), ("kingdom_infantry", 2.6, -2.6), ("kingdom_hodman", -3.0, -1.0),
                ("kingdom_hookgunner", 0.5, -3.0), ("kingdom_wheel_marshal", -1.5, -3.0)],
    "clans": [("clans_grappler", 1.5, -2.0), ("clans_grappler", 2.6, -2.6), ("clans_yurtwright", -3.0, -1.0),
              ("clans_javelineer", 0.5, -3.0), ("clans_hero_uncut", -1.5, -3.0)],
}


def render_game_frames(out_png, model_dir, colours=None, tag=""):
    """The real game camera (RtsCamera: pitch 56, FOV 45, 28 m, 1920x1080) over a T2 base of each faction
    at native scale with slice units in front: kingdom frame on top, clans frame below."""
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    colours = colours or TEAM_COLOURS
    tmp = tempfile.mkdtemp(prefix="vc_game_")
    frames = []
    for fac in ("kingdom", "clans"):
        items = []
        for aid, x, z in GAME_BASES[fac]:
            g = os.path.join(model_dir, aid + ".glb")
            if os.path.exists(g):
                items.append({"glb": os.path.abspath(g), "pos": [x, 0.0, z], "team": colours[fac]})
        for uid, x, z in GAME_UNITS[fac]:
            g = os.path.join(REPO, "assets/models/units", uid + ".glb")
            if os.path.exists(g):
                items.append({"glb": g, "pos": [x, 0.0, z], "team": colours[fac], "clip": "idle"})
        spec = {"size": [1920, 1080], "pitch": 56.0, "fov": 45.0, "target": [0.0, 0.0, 4.2], "distance": 28.0,
                "ground": os.path.join(REPO, "assets/textures/terrain/gv_meadow.png"), "items": items, "labels": []}
        frame, _ = _run_lineup(spec, tmp, fac)
        frames.append(Image.open(frame).convert("RGB"))
    im = Image.new("RGB", (1920, 2160))
    im.paste(frames[0], (0, 0))
    im.paste(frames[1], (0, 1080))
    d = ImageDraw.Draw(im)
    try:
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        f2 = ImageFont.load_default()
    for k, fac in enumerate(("kingdom", "clans")):
        txt = (f"{fac}: game camera (pitch 56, FOV 45, 28 m, 1920x1080), T2 base at native scale, team {colours[fac]}"
               + (f"  [{tag}]" if tag else ""))
        d.rectangle([0, k * 1080, 1920, k * 1080 + 30], fill=(20, 22, 26))
        d.text((10, k * 1080 + 5), txt, font=f2, fill=(235, 235, 235))
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


GROUND_CUT = 0.12     # QA silhouettes / coverage ignore everything lower than this (apron, rugs, kerbs)


def team_coverage(ids, model_dir, yaws=(0, 90, 180, 270)):
    """Visible TEAM fraction of the standing silhouette from the RTS pitch (front view and the mean of
    four yaws; the ground apron below GROUND_CUT is left out). Add-ons are measured with their T1 hall."""
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
    spec = {"size": 384, "pitch": 56.0, "fov": 30.0, "shots": shots, "min_y": GROUND_CUT}
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


def silhouette_sheet(ids, model_dir, out_png, px=128):
    """Bible 4.1 check: a flat-black silhouette of each building from the RTS pitch at 128 px (front view),
    on one sheet, plus the most similar pair per faction (IoU of the bbox-normalized silhouettes)."""
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    tmp = tempfile.mkdtemp(prefix="vc_sil_")
    with open(os.path.join(model_dir, "manifest.json")) as f:
        man = json.load(f)["buildings"]
    shots, meta = [], []
    for aid in ids:
        rec = man.get(aid)
        if rec is None or aid in HALLS:
            continue
        ext = max(rec["footprint_m"][0], rec["height_m"] * 0.8)
        out = os.path.join(tmp, aid + ".png")
        shots.append({"glbs": [os.path.join(model_dir, aid + ".glb")], "glb": os.path.join(model_dir, aid + ".glb"),
                      "out": out, "yaw": 0, "target": [0.0, rec["height_m"] * 0.4, 0.0], "distance": ext * 2.6})
        meta.append((aid, out))
    spec = {"size": px * 2, "pitch": 56.0, "fov": 30.0, "shots": shots, "min_y": GROUND_CUT}
    sp = os.path.join(tmp, "spec.json")
    with open(sp, "w") as f:
        json.dump(spec, f)
    cmd, env = _godot_cmd("buildings_teammask.gd", sp)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=1200)
    if "VC_MASKS_OK" not in r.stdout:
        raise SystemExit("silhouette render failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
    sils = {}
    for aid, out in meta:
        a = np.asarray(Image.open(out).convert("RGB"), np.int32).sum(2) > 60
        sils[aid] = Image.fromarray(np.where(a, 0, 255).astype(np.uint8), "L").resize((px, px), Image.LANCZOS)
    cols = 6
    n = len(sils)
    rows = (n + cols - 1) // cols
    sheet = Image.new("L", (cols * (px + 8) + 8, rows * (px + 28) + 40), 255)
    d = ImageDraw.Draw(sheet)
    try:
        fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except OSError:
        fnt = ImageFont.load_default()
    for i, (aid, im) in enumerate(sils.items()):
        x, y = 8 + (i % cols) * (px + 8), 36 + (i // cols) * (px + 28)
        sheet.paste(im, (x, y))
        d.text((x, y + px + 2), aid.split("_", 1)[1][:22], font=fnt, fill=0)

    def norm(im):
        a = np.asarray(im) < 128
        ys, xs = np.nonzero(a)
        c = Image.fromarray((a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype(np.uint8))
        return np.asarray(c.resize((64, 64), Image.BILINEAR)) > 127

    worst = {}
    keys = list(sils)
    nm = {k: norm(sils[k]) for k in keys}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if a.split("_")[0] != b.split("_")[0]:
                continue
            iou = float((nm[a] & nm[b]).sum() / max((nm[a] | nm[b]).sum(), 1))
            fac = a.split("_")[0]
            if iou > worst.get(fac, ("", "", 0.0))[2]:
                worst[fac] = (a, b, round(iou, 3))
    d.text((8, 8), "128 px flat-black silhouettes, RTS pitch 56, front (bible 4.1). Most similar pair: " +
           "; ".join(f"{k}: {v[0].split('_', 1)[1]} / {v[1].split('_', 1)[1]} IoU {v[2]}" for k, v in worst.items()),
           font=fnt, fill=0)
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    sheet.save(out_png, optimize=True)
    return out_png, worst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="comma list of ids (default: all)")
    ap.add_argument("--out-dir", default=os.path.join(REPO, "assets/models/buildings"))
    ap.add_argument("--manifest", default=None, help="default: <out-dir>/manifest.json")
    ap.add_argument("--sheets", default=None, help="render a render_preview contact sheet per building here")
    ap.add_argument("--lineup", default=None, help="render the line-up PNG here")
    ap.add_argument("--hall-scale", type=float, default=1.0,
                    help="line-up scale of the 8 m AI halls (1 = native 16x16 cells, the decided footprint)")
    ap.add_argument("--no-build", action="store_true", help="only render (sheets / line-up) existing GLBs")
    ap.add_argument("--silhouettes", default=None, help="render the 128 px silhouette sheet (bible 4.1) here")
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
    if args.silhouettes:
        L.log("silhouettes:", *silhouette_sheet(ids, args.out_dir, args.silhouettes))
    if args.lineup:
        stem = os.path.splitext(args.lineup)[0]
        L.log("line-up:", render_lineup(args.lineup, args.out_dir, hall_scale=args.hall_scale))
        L.log("game camera:", render_game_frames(stem + "_game.png", args.out_dir))
        L.log("crimson stress test:", render_lineup(stem + "_crimson.png", args.out_dir, hall_scale=args.hall_scale,
                                                    colours=STRESS_COLOURS, tag="Crimson readability stress test"))
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
        "footprint": "faction-doc cells x 0.5 m (kingdom.md 7.2, clans.md 7; art bible 1.3, decided 2026-10-19): supply "
                     "8x8 (4 m, 3-3.5 m tall), production / altar / shop / research 12x12 (6 m, 5-6 m; altar and shops "
                     "4.5-5.5 m), towers 4x4 (2 m, 6-8 m), halls 16x16 (8 m). Ground geometry stays inside the "
                     "footprint (outside_footprint_m reports the overshoot below / above 1.5 m: eaves, pennants and "
                     "streamers may reach ~0.3 m out)",
        "ground": "every building stands on an irregular ground apron covering its footprint: top 1.5 cm above "
                  "y = 0 (packed earth with a timber kerb and cobbles for the kingdom, trampled earth with a drystone "
                  "curb and felt rugs for the clans), a skirt down to -0.2 m so terrain bumps never open a gap",
        "facing": "door on -Z like units; UnitView draws structures at a fixed world yaw of PI so the door always "
                  "faces the RTS camera (which sits on +Z) whatever the sim facing",
        "materials": "<id> = opaque faction atlas (textures/<faction>_buildings_atlas.jpg, tileable swatches at 144 px/m, "
                     "pattern periods matched to the AI halls: roof courses ~0.3 m, rubble stones 0.4-0.7 m); <id>_GLOW = "
                     "windows / embers / smoke-ring glow (textures/buildings_glow.png; shipped with emissiveFactor 0 for "
                     "day, extras emissive_night = the dusk value to set at 17:45, bible 1.5); <id>_TEAM = light grey cloth "
                     "(textures/buildings_team.png), UnitView multiplies albedo_color by the player colour. Primitive order "
                     "GLOW, atlas, TEAM (Godot 4.7's glTF import skips vertex_color_use_as_albedo on a mesh's first "
                     "primitive; buildings without GLOW start with a hidden 1 mm dummy triangle)",
        "COLOR_0": "RGB = painted AO (ray-cast crevices, ground contact) x top light x per-part tint; A = 1",
        "TEXCOORD_1": "x = build layer (0 frame / lattice / walls, 1 covering: roofs, felt), y = normalized height "
                      "(0 ground .. 1 top)",
    },
    "build_progress": {
        "approach": "no _construction meshes: tools/kits/build_reveal.gdshader reveals the finished mesh bottom-up. "
                    "Height = object-space VERTEX.y / model_height (set it to height_m; AI halls: their AABB height), "
                    "so it needs no vertex data and works on the AI halls and hall upgrades too",
        "kingdom": "scaffold-raised: two_pass = false; a ragged hash-noise edge with an ember glow; scaffold and "
                   "ladders are particles / a separate shared prop",
        "clans": "Raising, two_pass = true: UV2.x = 0 (lattice, masts, stone ring) rises over progress 0..0.6, "
                 "UV2.x = 1 (felt walls and domes, team bands) over 0.4..1.0",
        "uniforms": "albedo_tex, albedo_color (team colour on TEAM surfaces), use_vertex_color, emission_tex, "
                    "emission, progress, model_height, two_pass, band, edge_color, edge_energy",
    },
    "team_coverage": "team_coverage_rts = visible TEAM fraction of the silhouette from the 56 deg RTS pitch, front view and "
                     "mean of 4 yaws (art bible 3.1 asks 6-10 % for buildings, the kit brief 12-18 %: the kit aims at "
                     "~8-15 %, at least one team area in the upper third)",
}


def _sha1(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:16]


def write_manifest(path, recs, partial=False):
    data = dict(MANIFEST_INFO)
    data["buildings"] = {}
    old = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                old = json.load(f)
        except Exception:
            old = {}
    if partial and old:
        data = old
    # measured QA numbers (--coverage) survive a rebuild that reproduces the same GLB bytes
    for r in recs:
        o = old.get("buildings", {}).get(r["id"], {}) if old else {}
        if o.get("glb_sha1") == r.get("glb_sha1") and "team_coverage_rts" in o:
            r["team_coverage_rts"] = o["team_coverage_rts"]
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
