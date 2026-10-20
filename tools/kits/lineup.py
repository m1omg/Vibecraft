#!/usr/bin/env python3
"""Line-up render of the procedural doodad kit, seen through the real RTS camera.

    python3 tools/kits/lineup.py [-o tests/output/doodads_lineup.png] [--shots map,neutral,cat1,cat2]

Builds a small Greenvale scene (painted terrain splat, a pond, the kit placed like a map maker
would, the AI-made reference hall and units for scale and style) and renders it with
tools/kits/lineup.gd: RtsCamera pitch 56 deg, vertical FOV 45, DayNight day light. Shots:
  map      vignette at the default camera distance (28 m): tree wall, Gold Seam beside the
           reference Moot Hall, road, walls, hedges, pond, a creep camp
  neutral  the neutral structures (Gold Seam, Weighstall, Hale Spring) next to the Shell Hall, 25 m
  forest   a tree block at the map generator's density (a tree on ~88 % of the 1 m tree cells) with a
           2 m lane cut along and one across the view, units standing in them (28 m)
  lod      the same tree block twice at the maximum zoom-out (46 m): LOD0 left, LOD1 right
  mine4    the Gold Seam at yaw 180 / 90 / 0 / 270 (every side must read as cliff + gold seam), 28 m
  cat1-3   every asset in labelled rows at close zoom (22 m)
The composed PNG stacks the shots with a title bar each.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PREVIEW = os.path.join(REPO, "tools", "preview")
LVP = "/usr/share/vulkan/icd.d/lvp_icd.json"
D = os.path.join(REPO, "assets", "models", "doodads")
N = os.path.join(REPO, "assets", "models", "neutral")
B = os.path.join(REPO, "assets", "models", "buildings")
U = os.path.join(REPO, "assets", "models", "units")
T = os.path.join(REPO, "assets", "textures", "terrain")

RECT = (-36.0, -28.0, 470.0, 28.0)     # x0, z0, x1, z1 of the painted splat
PPM = 4                                 # splat pixels per metre


def glb(aid):
    for d in (D, N, B, U):
        p = os.path.join(d, aid + ".glb")
        if os.path.exists(p):
            return p
    return os.path.join(D, aid + ".glb")


class Scene:
    def __init__(self):
        self.objects = []
        self.water = []
        W = int((RECT[2] - RECT[0]) * PPM)
        H = int((RECT[3] - RECT[1]) * PPM)
        self.splat = np.zeros((H, W, 4), np.float32)
        self.rng = random.Random(7)

    def put(self, aid, x, z, yaw=0.0, s=1.0, label=None, y=0.0):
        o = {"glb": glb(aid), "pos": [x, y, z], "yaw": yaw, "scale": s}
        if label:
            o["label"] = label if label is not True else aid
        self.objects.append(o)

    # --- splat painting (layer: 0 thick meadow, 1 dirt, 2 road, 3 scree)
    def _grid(self):
        H, W = self.splat.shape[:2]
        zz, xx = np.mgrid[0:H, 0:W]
        return RECT[0] + (xx + 0.5) / PPM, RECT[1] + (zz + 0.5) / PPM

    def disc(self, layer, cx, cz, r, soft=1.0, amt=1.0):
        X, Z = self._grid()
        d = np.hypot(X - cx, Z - cz)
        w = np.clip((r - d) / max(soft, 1e-3) + 0.5, 0, 1) * amt
        self.splat[..., layer] = np.maximum(self.splat[..., layer], w)

    def rect(self, layer, x0, z0, x1, z1, soft=1.0):
        X, Z = self._grid()
        dx = np.maximum(np.maximum(x0 - X, X - x1), 0)
        dz = np.maximum(np.maximum(z0 - Z, Z - z1), 0)
        d = np.hypot(dx, dz)
        w = np.clip(1 - d / max(soft, 1e-3), 0, 1)
        self.splat[..., layer] = np.maximum(self.splat[..., layer], w)

    def path(self, layer, pts, width, soft=0.8):
        X, Z = self._grid()
        best = np.full(X.shape, 1e9)
        for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
            vx, vz = bx - ax, bz - az
            L2 = vx * vx + vz * vz
            t = np.clip(((X - ax) * vx + (Z - az) * vz) / L2, 0, 1)
            d = np.hypot(X - (ax + t * vx), Z - (az + t * vz))
            best = np.minimum(best, d)
        w = np.clip((width / 2 - best) / soft + 0.5, 0, 1)
        self.splat[..., layer] = np.maximum(self.splat[..., layer], w)

    def clear(self, layer, cx, cz, r):
        X, Z = self._grid()
        d = np.hypot(X - cx, Z - cz)
        self.splat[..., layer] *= np.clip((d - r) / 1.0, 0, 1)


# =============================================================================================
# layouts
# =============================================================================================

def tree_wall(sc, x0, x1, z_back, z_front, seed=3, fill=0.88, mix=(0.55, 0.25, 0.20), lanes=(), lod=""):
    """Tree wall on the 1 m tree grid like src/world/map_generator.gd: a tree on ~88 % of the cells
    (cell centre + up to 15 cm, src/world/doodads.gd), an irregular front edge, oaks / lindens / hazels
    (hazels more likely on the front edge), +-15 % scale, random yaw. lanes: [(x0, z0, x1, z1)] cut out."""
    rng = random.Random(seed)
    for gx in range(int(math.floor(x0)), int(math.ceil(x1))):
        edge = z_front + 1.2 * math.sin(gx * 0.7 + seed) + 0.8 * math.sin(gx * 0.23 + seed * 2.1)
        for gz in range(int(math.floor(z_back)), int(math.ceil(z_front + 2.0))):
            x, z = gx + 0.5, gz + 0.5
            r_fill, r_kind = rng.random(), rng.random()
            yaw, s = rng.uniform(0, 360), rng.uniform(0.85, 1.15)
            jx, jz = rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)
            if z > edge or r_fill > fill:
                continue
            if any(a <= x < b and c <= z < d for a, c, b, d in lanes):
                continue
            front = z > edge - 2.0
            if front and r_kind < 0.4:
                kind = "tree_hazel"
            elif r_kind < mix[0]:
                kind = "tree_hill_oak"
            elif r_kind < mix[0] + mix[1]:
                kind = "tree_linden"
            else:
                kind = "tree_hazel"
            sc.put(kind + lod, x + jx, z + jz, yaw=yaw, s=s)


def scatter(sc, rng, centre, radius, n, ids, scale=(0.85, 1.2)):
    for _ in range(n):
        a, r = rng.uniform(0, 6.283), radius * math.sqrt(rng.random())
        sc.put(rng.choice(ids), centre[0] + math.cos(a) * r, centre[1] + math.sin(a) * r, yaw=rng.uniform(0, 360),
               s=rng.uniform(*scale))


def layout_map(sc):
    """Shot 'map': focus (0, 0) at the default 28 m. Visible ground: z -19 (top) .. +11 (bottom),
    about x +-29 at the top, +-20 mid-frame, +-17 at the bottom."""
    rng = random.Random(5)
    # ground paint: thick meadow under the forest and in hollows, dirt pads, the road, scree knolls
    sc.rect(0, -40, -30, 40, -9.0, soft=3.0)
    sc.disc(0, -26.0, -4.0, 6.0, soft=2.5)
    sc.disc(1, -11.0, 3.5, 6.0, soft=1.5)                     # kingdom hall pad (gv_dirt)
    sc.disc(1, -10.5, -6.0, 3.8, soft=1.5)                    # mine front
    sc.path(1, [(-11, 0), (-10.5, -5)], 3.0)
    sc.path(2, [(-34, 10.0), (-14, 9.2), (-2, 8.6), (10, 8.0), (22, 6.6), (34, 4.5)], 3.0)   # cart road
    sc.disc(1, 9.0, -5.0, 6.0, soft=1.6)                      # Sootcoat camp
    sc.disc(3, 2.0, -9.0, 2.6, soft=1.2)                      # scree knoll
    sc.disc(3, -16.5, -7.0, 2.0, soft=1.0)
    sc.disc(3, 21.0, -1.0, 2.0, soft=1.0)
    sc.rect(0, -1.0, -1.5, 7.5, 4.5, soft=1.5)                # walled field (thick meadow)
    sc.disc(0, 17.0, 1.0, 4.4, soft=2.0)                      # pond margin
    # forest edge with a tongue of trees down the left
    tree_wall(sc, -34, 34, -22.0, -11.0, seed=11)
    tree_wall(sc, -34, -21, -11.0, -2.0, seed=12)
    # Gold Seam at the forest edge, 6 m (hall edge -> seam edge) above the reference Moot Hall
    sc.put("kingdom_moot_hall", -11.0, 3.5, yaw=180.0)
    sc.put("gold_mine", -10.5, -8.5, yaw=180.0)
    for i, (x, z, yw) in enumerate([(-9.6, -4.6, 200), (-12.0, -3.4, 160), (-8.2, -2.2, 10), (-5.0, 5.8, 120),
                                    (-4.2, 2.0, 250)]):
        sc.put("kingdom_infantry" if i % 2 == 0 else "kingdom_hodman", x, z, yaw=yw)
    # rocks: clusters of 3-7 objects at transitions (bible §6.4)
    for aid, x, z, yw, sz in [("rock_boulder_large", 2.6, -9.6, 30, 1.0), ("rock_boulder_medium", 4.4, -8.0, 110, 1.0),
                              ("rock_boulder_small", 0.6, -8.0, 200, 1.0), ("rock_boulder_small", 5.0, -10.2, 60, 0.8),
                              ("rock_boulder_medium", -16.5, -7.2, 250, 0.9), ("rock_boulder_small", -15.0, -5.8, 20, 1.0),
                              ("rock_boulder_small", -6.2, -8.4, 140, 0.9),
                              ("rock_boulder_medium", 21.0, -1.2, 80, 1.0), ("rock_boulder_small", 22.4, 0.2, 10, 0.9)]:
        sc.put(aid, x, z, yaw=yw, s=sz)
    # walled field north of the road: broken end, straights, a corner turning north, hay stooks inside
    sc.put("wall_drystone_end_broken", -2.0, 5.2, yaw=180.0)
    for x in (0.0, 2.0, 4.0, 6.0):
        sc.put("wall_drystone_straight", x, 5.2, yaw=0.0)
    sc.put("wall_drystone_corner", 8.0, 5.2, yaw=0.0)
    sc.put("wall_drystone_straight", 8.0, 3.2, yaw=90.0)
    sc.put("wall_drystone_straight", 8.0, 1.2, yaw=90.0)
    for x, z, yw in [(0.8, 1.0, 10), (3.2, 2.6, 70), (5.4, 0.6, 150), (2.2, -0.6, 220), (5.8, 3.2, 300)]:
        sc.put("hay_stook", x, z, yaw=yw)
    # wattle pen beside the hall, hedgerow along the road's far side
    for z in (-0.5, 1.5):
        sc.put("fence_wattle", -4.6, z, yaw=90.0)
    sc.put("fence_wattle", -3.6, -1.5, yaw=0.0)
    for x in (-15.0, -13.0, -11.0, -9.0):
        sc.put("hedge_hawthorn", x, 11.0, yaw=0.0)
    sc.put("beehive_skeps", -3.4, 0.6, yaw=200.0)
    # road furniture
    sc.put("milestone", -1.5, 10.4, yaw=180.0)
    sc.put("cart_broken", 12.0, 10.4, yaw=160.0)
    sc.put("cairn_small", 24.0, 4.0, yaw=40.0)
    # pond with reeds and lilies
    sc.water.append({"center": [17.0, 1.0], "radius": 3.0, "y": 0.03, "texture": os.path.join(T, "water_ripples.png")})
    for x, z, yw in [(14.4, -0.8, 0), (19.6, 2.8, 120), (15.0, 3.4, 240), (19.8, -1.2, 60)]:
        sc.put("reeds_clump", x, z, yaw=yw)
    sc.put("lily_pads", 17.4, 0.8, yaw=30.0, y=0.03)
    # Sootcoat camp (Charcoal Clamp)
    sc.put("camp_charcoal_clamp", 11.5, -7.0, yaw=0.0)
    sc.put("camp_lean_to", 6.0, -6.6, yaw=275.0)              # sideways: open side to -X (see the manifest)
    sc.put("camp_campfire", 8.6, -3.6, yaw=0.0)
    sc.put("camp_cordwood_stack", 13.2, -3.2, yaw=250.0)
    sc.put("camp_crates", 5.4, -3.0, yaw=30.0)
    # woodland floor and meadow dressing
    sc.put("mushroom_ring", -24.0, 1.5, yaw=0.0)
    sc.put("tree_stump", -4.0, -9.6, yaw=40.0)
    sc.put("tree_stump", -22.0, 3.6, yaw=200.0)
    sc.put("tree_felled_log", -6.5, -10.6, yaw=20.0)
    for c, r, n in [((2.5, -7.2), 2.5, 5), ((-16.0, -5.5), 1.8, 3), ((21.5, -0.2), 2.0, 3), ((-1.5, 6.5), 1.6, 3),
                    ((-6.0, -6.0), 2.0, 4), ((15.0, -1.8), 1.5, 3), ((-19.0, 6.0), 2.5, 5), ((24.0, 6.0), 2.0, 4),
                    ((0.0, -3.0), 3.0, 4), ((-6.5, 9.6), 2.0, 3)]:
        scatter(sc, rng, c, r, n, ["grass_tuft", "grass_tuft", "wildflowers_yellow", "wildflowers_white",
                                   "wildflowers_mixed"])
    for k in range(26):
        x, z = rng.uniform(-20, 28), rng.uniform(-9.5, 11)
        if (abs(x + 11) < 6.5 and -10 < z < 8) or abs(z - (8.6 - 0.07 * x)) < 2.2:
            continue
        if math.hypot(x - 17, z - 1) < 3.6 or math.hypot(x - 9, z + 5) < 6 or (-1 < x < 8.5 and -1.5 < z < 5.5):
            continue
        sc.put(rng.choice(["grass_tuft", "wildflowers_yellow", "wildflowers_white", "wildflowers_mixed"]), x, z,
               yaw=rng.uniform(0, 360), s=rng.uniform(0.8, 1.2))


def layout_neutral(sc, ox=70.0):
    """Shot 'neutral': the three neutral structures next to the Shell Hall, focus (ox, 0)."""
    sc.rect(0, ox - 30, -26, ox + 30, -10.5, soft=3.0)
    tree_wall(sc, ox - 28, ox + 28, -20.0, -12.5, seed=21)
    sc.disc(1, ox - 9.0, -1.0, 4.4, soft=1.5)                # weighstall yard
    sc.path(2, [(ox - 30, 6.0), (ox - 9, 4.0), (ox + 30, 5.5)], 3.0)
    sc.disc(0, ox + 9.0, -1.0, 4.6, soft=2.0)                # spring dell
    sc.disc(3, ox + 1.0, -7.5, 3.2, soft=1.2)
    sc.put("neutral_weighstall", ox - 9.0, -1.0, yaw=180.0)
    sc.put("gold_mine", ox + 1.0, -7.0, yaw=180.0)
    sc.put("neutral_hale_spring", ox + 9.0, -1.0, yaw=180.0)
    sc.put("clans_shell_hall", ox + 17.0, 1.0, yaw=180.0)
    for i, (x, z, yw) in enumerate([(ox - 6.0, 2.4, 200), (ox + 6.4, 2.0, 160), (ox + 12.5, 3.2, 220),
                                    (ox + 1.5, -2.4, 180)]):
        sc.put(["clans_grappler", "kingdom_infantry", "clans_yurtwright", "kingdom_hodman"][i], x, z, yaw=yw)
    for aid, x, z in [("rock_boulder_medium", ox + 4.2, -8.2), ("rock_boulder_small", ox - 2.4, -8.0),
                      ("rock_boulder_large", ox - 18.0, -6.0)]:
        sc.put(aid, x, z, yaw=70.0)
    # creep-camp kits: Turnip Patch / Standing Ring props near the spring
    sc.rect(0, ox - 21.0, 4.5, ox - 13.0, 9.5, soft=1.0)
    sc.put("camp_turnip_rows", ox - 17.0, 7.0, yaw=0.0)
    sc.put("camp_scarecrow_pole", ox - 19.5, 5.0, yaw=170.0)
    sc.put("camp_scarecrow_pole", ox - 14.5, 5.2, yaw=190.0)
    sc.put("camp_haystack", ox - 12.0, 8.5, yaw=40.0)
    sc.put("camp_standing_stone", ox + 7.0, -9.0, yaw=190.0)
    sc.put("camp_standing_stone", ox + 10.0, -8.0, yaw=150.0, s=0.85)
    sc.put("camp_standing_stone", ox + 12.0, -10.5, yaw=170.0, s=1.1)
    sc.put("camp_tent", ox - 17.0, -5.0, yaw=200.0)
    sc.put("camp_crates", ox - 6.0, 3.6, yaw=160.0)


def layout_forest(sc, ox=320.0):
    """Shot 'forest': tree block at the generator's density with a 2 m lane along the view (x 319-321)
    and one across it (z -3..-1), units standing in both."""
    sc.rect(0, ox - 24, -24, ox + 24, 6.0, soft=2.0)
    tree_wall(sc, ox - 22, ox + 22, -22.0, 4.0, seed=31, lanes=[(ox - 1.0, -30.0, ox + 1.0, 10.0),
                                                                (ox - 30.0, -3.0, ox + 30.0, -1.0)])
    for k, (x, z, yw) in enumerate([(ox, -9.0, 180), (ox, -2.0, 200), (ox - 8.0, -2.0, 90), (ox + 7.0, -2.0, 270),
                                    (ox, 2.5, 160)]):
        sc.put(["kingdom_infantry", "kingdom_hodman", "clans_grappler", "kingdom_infantry", "clans_yurtwright"][k],
               x, z, yaw=yw)


def layout_lod(sc, ox=380.0):
    """Shot 'lod': the same 14 x 12 m tree block with LOD0 (left) and LOD1 (right), seen from 46 m."""
    for dx, lod in ((-11.0, ""), (11.0, "_lod1")):
        tree_wall(sc, ox + dx - 7, ox + dx + 7, -10.0, 2.0, seed=41, lod=lod)
        sc.put("kingdom_infantry", ox + dx, 5.0, yaw=180.0, label="LOD1" if lod else "LOD0")


def layout_mine4(sc, ox=440.0):
    """Shot 'mine4': the Gold Seam at four yaws (the game spawns it facing the hall, so any side may face
    the camera)."""
    for k, yw in enumerate((180.0, 90.0, 0.0, 270.0)):
        x = ox - 12.0 + k * 8.0
        sc.disc(3, x, -1.0, 3.6, soft=1.0)
        sc.put("gold_mine", x, -1.0, yaw=yw)
        sc.put("kingdom_hodman", x - 2.0, 3.2, yaw=200.0, label=f"yaw {int(yw)}")


CATALOGUE = [
    # (shot, z, ids): far row first so tall trees never hide the near row
    ("cat1", -3.5, ["tree_hill_oak", "tree_hill_oak_lod1", "tree_linden", "tree_linden_lod1", "tree_hazel",
                    "tree_hazel_lod1"]),
    ("cat1", 4.0, ["tree_stump", "tree_felled_log", "rock_boulder_small", "rock_boulder_medium", "rock_boulder_large",
                   "wall_drystone_straight", "wall_drystone_corner", "wall_drystone_end_broken"]),
    ("cat2", -3.0, ["hedge_hawthorn", "fence_wattle", "hay_stook", "reeds_clump", "lily_pads", "wildflowers_yellow",
                    "wildflowers_white", "wildflowers_mixed", "grass_tuft"]),
    ("cat2", 3.5, ["mushroom_ring", "cart_broken", "milestone", "cairn_small", "camp_campfire", "camp_lean_to",
                   "camp_tent"]),
    ("cat3", -3.0, ["camp_charcoal_clamp", "camp_cordwood_stack", "camp_crates", "camp_scarecrow_pole",
                    "camp_turnip_rows", "camp_haystack", "camp_standing_stone"]),
    ("cat3", 3.5, ["gold_mine_collapsed", "beehive_skeps"]),
]
CAT_X0 = 130.0
LABELLED = ("cat", "mine4", "lod")


def layout_catalogue(sc):
    widths = {"tree_hill_oak": 3.8, "tree_hill_oak_lod1": 3.8, "tree_linden": 3.6, "tree_linden_lod1": 3.6,
              "tree_hazel": 3.4, "tree_hazel_lod1": 3.4, "tree_felled_log": 4.2, "camp_charcoal_clamp": 4.4,
              "cart_broken": 4.0, "mushroom_ring": 3.0, "camp_turnip_rows": 4.6, "wall_drystone_corner": 3.0,
              "rock_boulder_large": 3.2, "wall_drystone_straight": 2.8, "wall_drystone_end_broken": 3.2,
              "hedge_hawthorn": 3.2, "fence_wattle": 2.8, "camp_lean_to": 3.4, "camp_tent": 3.2, "lily_pads": 3.0,
              "camp_cordwood_stack": 3.0, "camp_haystack": 3.2, "camp_standing_stone": 2.4, "gold_mine_collapsed": 5.0,
              "wildflowers_yellow": 2.3, "wildflowers_white": 2.3, "wildflowers_mixed": 2.3, "grass_tuft": 2.0}
    shots = {}
    for shot, z, row in CATALOGUE:
        k = int(shot[3:]) - 1
        cx = CAT_X0 + k * 60.0
        shots[shot] = cx
        total = sum(widths.get(a, 2.6) for a in row)
        x = cx - total / 2
        for aid in row:
            w = widths.get(aid, 2.6)
            if aid == "lily_pads":
                sc.water.append({"center": [x + w / 2, z], "radius": 1.6, "y": 0.03,
                                 "texture": os.path.join(T, "water_ripples.png")})
            if aid.startswith("camp_"):
                sc.disc(1, x + w / 2, z, w * 0.45, soft=0.8)
            yaw = 270.0 if aid == "camp_lean_to" else 180.0       # the lean-to is placed sideways (manifest note)
            sc.put(aid, x + w / 2, z, yaw=yaw, label=True, y=0.03 if aid == "lily_pads" else 0.0)
            x += w
    return [{"name": n, "focus": [cx, 0.0], "distance": 22.0, "pitch": 56.0, "fov": 45.0} for n, cx in shots.items()]


# =============================================================================================
# render + compose
# =============================================================================================

def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


TITLES = {
    "map": "Greenvale vignette, default RTS camera (pitch 56, FOV 45, 28 m): tree wall, Gold Seam beside the "
           "reference Moot Hall (AI), road, walls, hedge, pond, Sootcoat camp",
    "neutral": "Neutral structures at 25 m: Weighstall, Gold Seam, Hale Spring; reference Shell Hall (AI) and units; "
               "Turnip Patch and Standing Ring props",
    "forest": "Tree wall at the map generator's density (a tree on ~88 % of the 1 m tree cells), 2 m lanes cut along "
              "and across the view, units in the lanes, 28 m",
    "lod": "The same tree block at maximum zoom-out (46 m): LOD0 (left) vs LOD1 (right)",
    "mine4": "Gold Seam at yaw 180 / 90 / 0 / 270 (spawned facing the hall: every side is cliff with the gold seam), 28 m",
    "cat1": "Catalogue 1 (22 m): trees + low LODs, stump, felled log, boulders, drystone walls",
    "cat2": "Catalogue 2 (22 m): hedge, wattle, hay stook, shore, meadow cards; mushroom ring, cart, milestone, cairn, camp",
    "cat3": "Catalogue 3 (22 m): creep-camp kit (Sootcoats, Tattiebogles, Cairnwakes) and extras",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(REPO, "tests", "output", "doodads_lineup.png"))
    ap.add_argument("--shots", default="map,neutral,forest,lod,mine4,cat1,cat2,cat3")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--keep", default=None, help="keep the individual shot PNGs in this folder")
    ap.add_argument("--godot", default=os.environ.get("VC_GODOT") or shutil.which("godot") or "godot")
    args = ap.parse_args()
    want = args.shots.split(",")
    W, H = (int(x) for x in args.size.split("x"))

    sc = Scene()
    shots = []
    if "map" in want:
        layout_map(sc)
        shots.append({"name": "map", "focus": [0.0, 0.0], "distance": 28.0, "pitch": 56.0, "fov": 45.0})
    if "neutral" in want:
        layout_neutral(sc)
        shots.append({"name": "neutral", "focus": [70.0, 0.0], "distance": 25.0, "pitch": 56.0, "fov": 45.0})
    if "forest" in want:
        layout_forest(sc)
        shots.append({"name": "forest", "focus": [320.0, -2.0], "distance": 28.0, "pitch": 56.0, "fov": 45.0})
    if "lod" in want:
        layout_lod(sc)
        shots.append({"name": "lod", "focus": [380.0, -2.0], "distance": 46.0, "pitch": 56.0, "fov": 45.0})
    if "mine4" in want:
        layout_mine4(sc)
        shots.append({"name": "mine4", "focus": [440.0, 0.0], "distance": 28.0, "pitch": 56.0, "fov": 45.0})
    if any(w.startswith("cat") for w in want):
        shots += [s for s in layout_catalogue(sc) if s["name"] in want]

    work = args.keep or tempfile.mkdtemp(prefix="vc_lineup_")
    os.makedirs(work, exist_ok=True)
    splat = Image.fromarray((np.clip(sc.splat, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    splat = splat.filter(ImageFilter.GaussianBlur(1.2))
    splat_path = os.path.join(work, "splat.png")
    splat.save(splat_path)
    scene = {
        "size": [W, H],
        "kit_dir": HERE,
        "ground": {"textures": [os.path.join(T, n + ".png") for n in
                                ("gv_meadow", "gv_thick_meadow", "gv_dirt", "gv_road", "gv_scree")],
                   "splat": splat_path, "rect": list(RECT), "tile_m": 4.0},
        "water": sc.water,
        "objects": sc.objects,
        "shots": shots,
    }
    scene_path = os.path.join(work, "scene.json")
    with open(scene_path, "w") as f:
        json.dump(scene, f)
    env = dict(os.environ)
    if "VK_ICD_FILENAMES" not in env and os.path.exists(LVP):
        env["VK_ICD_FILENAMES"] = LVP
    cmd = []
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd += ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"]
    cmd += [args.godot, "--rendering-driver", "vulkan", "--audio-driver", "Dummy", "--path", PREVIEW,
            "-s", os.path.join(HERE, "lineup.gd"), "--", "--scene", scene_path, "--out-dir", work]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=1800)
    errs = [ln for ln in (p.stdout + p.stderr).splitlines()
            if ln.startswith(("ERROR", "SCRIPT ERROR", "missing", "failed")) and "ALSA" not in ln]
    if p.returncode != 0 or not os.path.exists(os.path.join(work, "labels.json")):
        sys.exit(f"godot failed ({p.returncode}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    with open(os.path.join(work, "labels.json")) as f:
        labels = json.load(f)

    f_t, f_l = font(22), font(15)
    tiles = []
    for s in shots:
        im = Image.open(os.path.join(work, s["name"] + ".png")).convert("RGB")
        d = ImageDraw.Draw(im)
        if s["name"].startswith(LABELLED):
            for lb in labels.get(s["name"], []):
                txt = lb["label"]
                x, y = lb["bx"], lb["by"] + 6
                tw = d.textlength(txt, font=f_l)
                d.rectangle([x - tw / 2 - 4, y - 1, x + tw / 2 + 4, y + 18], fill=(20, 22, 26))
                d.text((x - tw / 2, y), txt, fill=(235, 235, 235), font=f_l)
        bar = Image.new("RGB", (im.width, 40), (24, 26, 30))
        ImageDraw.Draw(bar).text((10, 8), TITLES.get(s["name"], s["name"]), fill=(235, 235, 235), font=f_t)
        tile = Image.new("RGB", (im.width, im.height + 40))
        tile.paste(bar, (0, 0))
        tile.paste(im, (0, 40))
        tiles.append(tile)
        if args.keep:
            tile.save(os.path.join(work, s["name"] + "_labelled.png"))
    out = Image.new("RGB", (W, sum(t.height for t in tiles)))
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.height
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.save(args.out, optimize=True)
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    missing = sorted({ln.split(" ", 1)[1] for ln in errs if ln.startswith("missing")})
    print(json.dumps({"out": os.path.relpath(args.out, REPO), "shots": [s["name"] for s in shots],
                      "objects": len(sc.objects), "missing": [os.path.relpath(m, REPO) for m in missing],
                      "errors": [e for e in errs if not e.startswith("missing")][:20]}, indent=1))


if __name__ == "__main__":
    main()
