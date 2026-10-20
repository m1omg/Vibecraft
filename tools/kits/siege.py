#!/usr/bin/env python3
"""Procedural siege kit (bpy, no paid generation): the kingdom Bombard Wagon and the clans Sling-Cart.

    /opt/bpyenv/v313/bin/python tools/kits/siege.py                      # assets/models/vehicles/<id>.glb
    /opt/bpyenv/v313/bin/python tools/kits/siege.py --only kingdom_bombard_wagon --out-dir /tmp/x

Slice-plan 2.5 D1 and art bible 1.3 / 3.1 / 4.1: "a box on two big spoked wheels with a fat tube, two
small hat discs behind": a crew-pushed bronze bombard cart, 2.6 m long, two crew in kettle hats.
Built with the building kit's parts, swatches and shared texture sheets (tools/kits/buildings.py), so
it shares the kingdom atlas and the TEAM sheet in VRAM (URIs "../buildings/textures/...").

Moving parts are separate nodes (tools/kits/buildings_lib.export_glb_nodes): each node's origin is
its pivot, so UnitView can animate the cart procedurally (no skeleton, no clips):
    kingdom_bombard_wagon   the cart (bed, side boards, cheeks, axle, push bar, props)
    Wheel_L, Wheel_R        spoked wheels; spin about local X (pivot on the axle)
    Barrel                  the bronze tube, its bands and trunnions; recoils along +Z (pivot on
                            the trunnions)
    Crew_A, Crew_B          the two pushers (torso, arms, head, kettle hat, team plume; pivot at
                            the hips): bob while walking
    Crew_A_Leg_L ...        legs (pivot at the hip joint): swing about local X while walking
Node extras (glTF) carry each part's role and dimensions (wheel radius, recoil travel, stride).

Conventions as the building kit: metres, built Z-up with the front on +Y (glTF/Godot -Z), origin on
the ground at the axle line's centre; team colour on the side-board bands, the canvas stripe and the
crew's hat plumes (bible 3.1); vertex colour = painted AO. Deterministic (byte-identical re-runs).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import buildings as B  # noqa: E402  (initialises bpy, the swatches and the shared sheets)
import buildings_lib as L  # noqa: E402

REPO = L.REPO
OUT_DIR = os.path.join(REPO, "assets", "models", "vehicles")
SKIN = (1.0, 0.80, 0.68)          # tint on the palette's #C9B994 -> a warm skin tone
SKIN_CLANS = (0.86, 0.68, 0.55)   # tint on the clans palette's #E9DDBF


class SiegeCtx(B.Ctx):
    """A building-kit context whose parts are filed under nodes."""

    def __init__(self, aid, faction):
        super().__init__(aid, faction, (4, 4))
        self.node = aid
        self.nodes: dict[str, list] = {aid: []}
        self.pivots: dict[str, tuple] = {aid: (0.0, 0.0, 0.0)}
        self.node_extras: dict[str, dict] = {}
        self.bake = L.Bake(ao_dist=0.6, ao_strength=0.9, base_dark=0.8, base_h=0.25, top_light=0.08)

    def begin(self, name, pivot, **extras):
        self.node = name
        self.nodes.setdefault(name, [])
        self.pivots[name] = tuple(float(x) for x in pivot)
        if extras:
            self.node_extras[name] = extras

    def add(self, p, **kw):
        out = super().add(p, **kw)
        for q in (out if isinstance(out, list) else [out]):
            self.nodes[self.node].append(q)
        return out


# =============================================================================================
# parts
# =============================================================================================

def barrel_tube(c, pivot, tilt_deg, trunnion_z):
    """The fat bronze bombard on its own node: lathe tube along local +Z (breech at 0, muzzle at
    1.45 m), iron hoops, trunnions at `trunnion_z`, a dark bore. Returns the muzzle point."""
    prof = [(0.0, -0.11), (0.05, -0.105), (0.068, -0.07), (0.05, -0.035), (0.055, -0.012), (0.2, -0.005),
            (0.236, 0.03), (0.243, 0.1), (0.228, 0.135), (0.216, 0.15), (0.216, 0.5), (0.236, 0.515),
            (0.238, 0.6), (0.218, 0.62), (0.2, 1.16), (0.21, 1.25), (0.246, 1.33), (0.25, 1.42),
            (0.232, 1.45), (0.156, 1.452)]
    # warm cast bronze (palette #B07F3E): brighter than the cart's oak so the "fat tube" reads at
    # game zoom (bible 4.1 silhouette rule); the hoops stay dark iron
    tube = L.lathe(prof, 18, c.sw("pal"), smooth=48.0)
    c.pal_uv(tube, "#B07F3E")
    parts = [tube]
    bore = L.lathe([(0.156, 1.452), (0.156, 1.37), (0.0, 1.37)], 18, c.sw("pal"), smooth=60.0)
    c.pal_uv(bore, "#26221F")
    parts.append(bore)
    for z, r in ((0.88, 0.21), (1.07, 0.205)):
        parts.append(L.torus(r, 0.022, c.sw("iron"), segs=18, sides=6).move(0, 0, z))
    # a painted canvas hood over the breech and touch-hole (team colour, bible 3.1 "canvas cover"),
    # tied with a cord
    hood = L.lathe([(0.0, -0.15), (0.09, -0.148), (0.17, -0.12), (0.235, -0.07), (0.262, 0.0), (0.268, 0.12),
                    (0.266, 0.3), (0.258, 0.4), (0.24, 0.43)], 18, c.sw("team_plain"), smooth=50.0)
    hood.uv[:] = 0.5      # one flat team field (the cord below is its neutral piping)
    parts.append(hood)
    cord = L.torus(0.27, 0.016, c.sw("pal"), segs=18, sides=4).move(0, 0, 0.34)
    c.pal_uv(cord, "#C9B994")
    parts.append(cord)
    for sx in (-1, 1):   # trunnions: short iron stubs across the tube
        parts.append(L.lathe([(0.0, 0.2), (0.05, 0.2), (0.05, 0.31), (0.06, 0.31), (0.06, 0.33), (0.0, 0.33)],
                             8, c.sw("iron")).rot(0, 90 * sx, 0).move(0, 0, trunnion_z))
    # local +Z -> build +Y, tilted up by tilt_deg, trunnion on the pivot
    rx = -90.0 + tilt_deg
    for p in parts:
        p.move(0, 0, -trunnion_z).rot(rx, 0, 0).move(*pivot)
        c.add(p, dice=None, jit=0.0)
    R = L.rot_matrix(rx, 0, 0)
    return np.asarray(pivot) + R @ np.array([0.0, 0.0, 1.45 - trunnion_z])


def painted_wheel(c, center, r, spokes=10, width=0.085, segs=20, rim_key="team_band", spoke_key="oak"):
    """A spoked wheel built around X: a felloe (`rim_key`; the Bombard Wagon's team wheel-rim paint,
    bible 3.1) under an iron tyre, `spoke_key` spokes and an iron hub."""
    rim_w = r * 0.14
    ang = np.arange(segs) * 2 * math.pi / segs
    parts = []
    felloe = L.sweep(L.rect_profile(rim_w, width),
                     np.stack([np.cos(ang) * (r - rim_w / 2), np.sin(ang) * (r - rim_w / 2), np.zeros(segs)], 1),
                     c.sw(rim_key), closed_path=True)
    parts.append(felloe)
    tyre = L.sweep(L.rect_profile(rim_w * 0.3, width * 1.06),
                   np.stack([np.cos(ang) * (r - rim_w * 0.12), np.sin(ang) * (r - rim_w * 0.12), np.zeros(segs)], 1),
                   c.sw("iron"), closed_path=True)
    parts.append(tyre)
    hr = r * 0.2
    parts.append(L.lathe([(0, -width * 1.1), (hr * 0.7, -width * 1.1), (hr, -width * 0.4), (hr, width * 0.4),
                          (hr * 0.7, width * 1.1), (0, width * 1.1)], 8, c.sw("iron")))
    for k in range(spokes):
        a = k * 2 * math.pi / spokes + math.pi / spokes
        d = np.array([math.cos(a), math.sin(a), 0.0])
        parts.append(L.member(d * hr * 0.8, d * (r - rim_w * 0.8), width * 0.42, width * 0.55, c.sw(spoke_key),
                              rng=c.rng))
    for p in parts:
        p.rot(0, 90, 0).move(*center)
        c.add(p, dice=None, jit=0.0)


def crew(c, name, x, y, z_hip, lean_deg, bar_y, bar_z):
    """One pusher leaning `lean_deg` towards the cart (+Y): torso, arms to the push bar, head, a
    kettle hat with a team plume (node `name`, pivot at the hips) and two legs (nodes
    `name`_Leg_L / _R, pivot at each hip joint)."""
    hip = np.array([x, y, z_hip])
    c.begin(name, hip, role="crew body: bobs while walking", lean_deg=lean_deg)
    lean = L.rot_matrix(-lean_deg, 0, 0)    # pitch forward, towards +Y

    def body(p):
        p.xf(lean).move(*hip)
        return p

    torso = L.lathe([(0.0, -0.02), (0.13, -0.02), (0.155, 0.08), (0.165, 0.26), (0.15, 0.42), (0.1, 0.5),
                     (0.0, 0.5)], 10, c.sw("pal"), smooth=55.0).scale(1.18, 0.85, 1.0)
    c.pal_uv(torso, "#5A3A22")   # leather jerkin
    c.add(body(torso), dice=None, jit=0.0)
    belt = L.torus(0.16, 0.022, c.sw("pal"), segs=12, sides=4).scale(1.18, 0.85, 1.0).move(0, 0, 0.1)
    c.pal_uv(belt, "#26221F")
    c.add(body(belt), dice=None, jit=0.0)
    head_c = hip + lean @ np.array([0.0, 0.02, 0.6])
    head = L.Part(*L.icosphere(2, 0.095), c.sw("pal"), smooth=60.0).scale(1.0, 1.05, 1.08)
    c.pal_uv(head, "#C9B994")
    head.tint = np.array(SKIN)
    c.add(head.move(*head_c), dice=None, jit=0.0)
    neck = L.member(hip + lean @ np.array([0.0, 0.0, 0.46]), head_c - np.array([0, 0, 0.05]), 0.08, 0.08,
                    c.sw("pal"))
    c.pal_uv(neck, "#C9B994")
    neck.tint = np.array(SKIN)
    c.add(neck, dice=None, jit=0.0)
    # kettle hat: a wide iron brim and a low crown, worn level; the team plume on top (bible 3.1)
    hat_base = head_c + np.array([0.0, 0.0, 0.055])
    hat = L.lathe([(0.0, -0.005), (0.205, -0.005), (0.21, 0.012), (0.17, 0.024), (0.105, 0.035),
                   (0.1, 0.085), (0.075, 0.125), (0.035, 0.142), (0.0, 0.145)], 14, c.sw("iron"), smooth=50.0)
    c.add(hat.move(*hat_base), dice=None, jit=0.0)
    plume = L.Part(*L.icosphere(1, 0.065), c.sw("team_plain"), smooth=50.0).scale(0.75, 1.7, 1.0)
    plume.uv[:] = 0.5
    plume.rot(-25, 0, 0).move(*(hat_base + np.array([0.0, -0.06, 0.18])))
    c.add(plume, dice=None, jit=0.0)
    # arms: shoulder -> elbow -> hand on the push bar
    for sx in (-1, 1):
        sh = hip + lean @ np.array([sx * 0.19, 0.0, 0.44])
        hd = np.array([x + sx * 0.17, bar_y, bar_z])
        el = (sh + hd) / 2 + np.array([sx * 0.06, -0.02, -0.07])
        for a, b, w in ((sh, el, 0.085), (el, hd, 0.075)):
            m = L.member(a, b, w, w, c.sw("pal"))
            c.pal_uv(m, "#C9B994")    # linen sleeves
            c.add(m, dice=None, jit=0.0)
        fist = L.Part(*L.icosphere(1, 0.045), c.sw("pal"), smooth=60.0).move(*hd)
        c.pal_uv(fist, "#C9B994")
        fist.tint = np.array(SKIN)
        c.add(fist, dice=None, jit=0.0)
    for side, sx in (("L", -1), ("R", 1)):
        joint = hip + np.array([sx * 0.09, 0.0, -0.02])
        c.begin(f"{name}_Leg_{side}", joint, role="leg: swings about local X while walking",
                length_m=round(float(joint[2]), 3))
        foot = np.array([joint[0], joint[1], 0.07])
        leg = L.member(joint, foot + np.array([0, 0, 0.05]), 0.12, 0.11, c.sw("pal"))
        c.pal_uv(leg, "#3D4046")   # dark hose
        c.add(leg, dice=None, jit=0.0)
        shoe = L.box(0.11, 0.22, 0.09, c.sw("pal"), center=(foot[0], foot[1] + 0.05, 0.0), chamfer=0.02, base=True)
        c.pal_uv(shoe, "#2A2220")
        c.add(shoe, dice=None, jit=0.0)
    c.begin(c.aid, (0.0, 0.0, 0.0))


def bombard_wagon(c: SiegeCtx):
    """Kingdom Bombard Wagon: a plank cart with team side-board bands on two big iron-shod spoked
    wheels, a fat bronze bombard on a timber cradle (front +Y), a push bar at the back and two crew
    in kettle hats with team plumes; a canvas bundle with a team stripe and a rammer on the boards."""
    wheel_r, axle_y, track = 0.52, -0.08, 0.56
    zb = wheel_r + 0.06                       # deck bottom (the bed rides on the axle)
    zt = zb + 0.08                            # deck top
    b0, b1 = zb + 0.04, zb + 0.27             # side boards
    y0, y1, hw = -0.66, 0.56, 0.40            # bed length and half width
    # --- the bed -------------------------------------------------------------------------
    c.add(L.box(y1 - y0, hw * 2, 0.08, c.sw("planks"), center=((y0 + y1) / 2, 0, zb + 0.04), chamfer=0.015)
          .rot(0, 0, 90), dice=None, uvrot=True)
    for sx in (-1, 1):
        # side boards with an oak top rail; a team band painted along them (bible 3.1)
        c.add(L.box(y1 - y0 + 0.04, 0.05, b1 - b0, c.sw("planks"), chamfer=0.01,
                    center=((y0 + y1) / 2, -sx * (hw + 0.005), (b0 + b1) / 2)).rot(0, 0, 90), dice=None, uvrot=True)
        c.add(L.member((sx * (hw + 0.01), y0 - 0.03, b1 + 0.03), (sx * (hw + 0.01), y1 + 0.03, b1 + 0.03), 0.065, 0.06,
                       c.sw("oak"), rng=c.rng), dice=None)
        bz0, bz1 = b0 + 0.02, b1 - 0.015
        band = L.box(0.018, (y1 - y0) * 0.9, bz1 - bz0, c.sw("team_band"), chamfer=0.004,
                     center=(sx * (hw + 0.04), (y0 + y1) / 2, (bz0 + bz1) / 2))
        v = band.v[band.t]
        band.uv = np.stack([(v[..., 1] - y0) / 0.8, 1 - (v[..., 2] - bz0) / (bz1 - bz0)], -1)
        c.add(band, dice=None)
        for yy in (y0 + 0.05, y1 - 0.05):    # corner stakes
            c.add(L.member((sx * (hw + 0.035), yy, zb - 0.02), (sx * (hw + 0.035), yy, b1 + 0.07), 0.055, 0.055,
                           c.sw("oak"), rng=c.rng), dice=None)
    for yy, h in ((y0, 0.24), (y1, 0.17)):    # tail and head boards
        c.add(L.box(hw * 2 + 0.06, 0.05, h, c.sw("planks"), chamfer=0.01, center=(0, yy, b0 + h / 2)), dice=None)
    # axle under the bed, with iron straps (the axle does not turn)
    c.add(L.member((-track - 0.02, axle_y, wheel_r), (track + 0.02, axle_y, wheel_r), 0.09, 0.09, c.sw("oak"),
                   rng=c.rng), dice=None)
    for sx in (-1, 1):
        c.add(L.member((sx * 0.3, axle_y - 0.075, wheel_r), (sx * 0.3, axle_y + 0.075, wheel_r), 0.11, 0.115,
                       c.sw("iron")), dice=None)
    # the cradle: a timber bed under the breech and two cheeks rising to the trunnions
    trunnion = (0.0, 0.02, 1.08)
    c.add(L.box(0.5, 0.36, 0.12, c.sw("oak"), center=(0.0, -0.44, zt), chamfer=0.02, base=True), dice=None)
    for sx in (-1, 1):
        ch = L.plate((0.31, y0 + 0.18, zt), (0.31, y1 - 0.08, zt), (0.31, 0.25, trunnion[2] + 0.02),
                     (0.31, -0.36, trunnion[2] - 0.08), 0.07, c.sw("oak"))
        ch.box_uv()
        if sx < 0:
            ch.scale(-1, 1, 1)
        c.add(ch, dice=None)
        c.add(L.member((sx * 0.29, trunnion[1] - 0.07, trunnion[2] - 0.035), (sx * 0.29, trunnion[1] + 0.07,
                       trunnion[2] - 0.035), 0.075, 0.03, c.sw("iron")), dice=None)
    # push bar at the back: two handles and a cross bar at hand height
    bar_y, bar_z = -1.02, 1.0
    for sx in (-1, 1):
        c.add(L.member((sx * 0.33, y0 + 0.06, zt - 0.02), (sx * 0.36, bar_y, bar_z), 0.07, 0.07, c.sw("oak"),
                       rng=c.rng), dice=None)
    c.add(L.member((-0.45, bar_y, bar_z), (0.45, bar_y, bar_z), 0.065, 0.065, c.sw("oak"), rng=c.rng), dice=None)
    for sx in (-1, 1):   # iron caps on the bar ends
        c.add(L.lathe([(0.0, 0.0), (0.04, 0.0), (0.04, 0.05), (0.0, 0.05)], 8, c.sw("iron")).rot(0, 90 * sx, 0)
              .move(sx * 0.44, bar_y, bar_z), dice=None)
    # props: a canvas bundle with a team stripe on the left, a rammer and sponge on the right, shot
    rx_, rz_ = -hw + 0.1, zt + 0.12
    roll = L.lathe([(0.0, 0.0), (0.11, 0.0), (0.12, 0.04), (0.12, 0.5), (0.11, 0.54), (0.0, 0.54)], 10,
                   c.sw("pal")).rot(-90, 0, 0).move(rx_, y0 + 0.06, rz_)
    c.pal_uv(roll, "#EDE2C8")
    c.add(roll, dice=None)
    stripe = L.lathe([(0.124, 0.0), (0.124, 0.13)], 10, c.sw("team_plain")).rot(-90, 0, 0).move(rx_, y0 + 0.26, rz_)
    c.add(stripe, dice=None)
    for yy in (y0 + 0.16, y0 + 0.47):
        strap = L.torus(0.126, 0.012, c.sw("pal"), segs=10, sides=4).rot(90, 0, 0).move(rx_, yy, rz_)
        c.pal_uv(strap, "#5A3A22")
        c.add(strap, dice=None)
    c.add(L.member((hw - 0.06, y0 + 0.02, zt + 0.05), (hw - 0.06, y1 + 0.24, zt + 0.1), 0.04, 0.04, c.sw("oak"),
                   rng=c.rng), dice=None)
    sponge = L.lathe([(0.0, 0.0), (0.06, 0.0), (0.07, 0.04), (0.07, 0.16), (0.0, 0.18)], 8, c.sw("pal")) \
        .rot(-90, 0, 0).move(hw - 0.06, y1 + 0.2, zt + 0.1)
    c.pal_uv(sponge, "#9A8F7C")
    c.add(sponge, dice=None)
    for dx, dy, dz in ((0.0, 0.0, 0.0), (0.13, 0.02, 0.0), (0.065, 0.1, 0.0), (0.065, 0.04, 0.1)):
        ball = L.Part(*L.icosphere(1, 0.065), c.sw("iron"), smooth=60.0).move(0.13 + dx, y1 - 0.34 + dy,
                                                                              zt + 0.065 + dz)
        ball.box_uv()
        c.add(ball, dice=None)
    # --- wheels (one node each, pivot on the axle) ------------------------------------------
    for side, sx in (("L", -1), ("R", 1)):
        center = (sx * track, axle_y, wheel_r)
        c.begin(f"Wheel_{side}", center, role="wheel: spins about local X", radius_m=wheel_r)
        painted_wheel(c, center, wheel_r)
        c.begin(c.aid, (0.0, 0.0, 0.0))
    # --- the bombard (its own node, pivot on the trunnions) --------------------------------
    c.begin("Barrel", trunnion, role="bombard: recoils along local +Z", recoil_m=0.2, tilt_deg=7.0)
    c.anchors["muzzle"] = barrel_tube(c, trunnion, 7.0, 0.55)
    c.begin(c.aid, (0.0, 0.0, 0.0))
    # --- the crew --------------------------------------------------------------------------
    for name, x in (("Crew_A", -0.26), ("Crew_B", 0.27)):
        crew(c, name, x, -1.5, 0.8, 22.0, bar_y, bar_z)
    return {"stride_m": 1.15}


def tormai_crew(c, name, x, y, z_hip, lean_deg, bar_y, bar_z):
    """A Tormai pusher: a long teal coat (deel) with a saffron sash, a rounded felt cap with a
    turned-up brim and a team hat band (bible 3.1), arms to the push bar; legs as separate nodes."""
    hip = np.array([x, y, z_hip])
    c.begin(name, hip, role="crew body: bobs while walking", lean_deg=lean_deg)
    lean = L.rot_matrix(-lean_deg, 0, 0)

    def body(p):
        p.xf(lean).move(*hip)
        return p

    coat = L.lathe([(0.0, -0.32), (0.2, -0.32), (0.19, -0.1), (0.17, 0.08), (0.17, 0.27), (0.155, 0.42),
                    (0.1, 0.5), (0.0, 0.5)], 10, c.sw("pal"), smooth=55.0).scale(1.15, 0.9, 1.0)
    c.pal_uv(coat, "#1E5A60")
    c.add(body(coat), dice=None, jit=0.0)
    sash = L.torus(0.17, 0.03, c.sw("pal"), segs=12, sides=4).scale(1.15, 0.9, 1.0).move(0, 0, 0.08)
    c.pal_uv(sash, "#E0A030")
    c.add(body(sash), dice=None, jit=0.0)
    head_c = hip + lean @ np.array([0.0, 0.02, 0.6])
    head = L.Part(*L.icosphere(2, 0.095), c.sw("pal"), smooth=60.0).scale(1.0, 1.05, 1.08)
    c.pal_uv(head, "#E9DDBF")
    head.tint = np.array(SKIN_CLANS)
    c.add(head.move(*head_c), dice=None, jit=0.0)
    neck = L.member(hip + lean @ np.array([0.0, 0.0, 0.46]), head_c - np.array([0, 0, 0.05]), 0.08, 0.08,
                    c.sw("pal"))
    c.pal_uv(neck, "#E9DDBF")
    neck.tint = np.array(SKIN_CLANS)
    c.add(neck, dice=None, jit=0.0)
    cap_base = head_c + np.array([0.0, 0.0, 0.04])
    cap = L.lathe([(0.0, -0.01), (0.15, -0.01), (0.165, 0.03), (0.12, 0.05), (0.11, 0.1), (0.08, 0.16),
                   (0.03, 0.19), (0.0, 0.2)], 12, c.sw("pal"), smooth=55.0)
    c.pal_uv(cap, "#4E2E20")
    c.add(cap.move(*cap_base), dice=None, jit=0.0)
    band = L.lathe([(0.123, 0.045), (0.118, 0.095)], 12, c.sw("team_plain"))
    band.uv[:] = 0.5
    c.add(band.move(*cap_base), dice=None, jit=0.0)
    for sx in (-1, 1):
        sh = hip + lean @ np.array([sx * 0.19, 0.0, 0.44])
        hd = np.array([x + sx * 0.17, bar_y, bar_z])
        el = (sh + hd) / 2 + np.array([sx * 0.06, -0.02, -0.07])
        for a, b, w in ((sh, el, 0.09), (el, hd, 0.08)):
            m = L.member(a, b, w, w, c.sw("pal"))
            c.pal_uv(m, "#2F7E7E")
            c.add(m, dice=None, jit=0.0)
        fist = L.Part(*L.icosphere(1, 0.045), c.sw("pal"), smooth=60.0).move(*hd)
        c.pal_uv(fist, "#E9DDBF")
        fist.tint = np.array(SKIN_CLANS)
        c.add(fist, dice=None, jit=0.0)
    for side, sx in (("L", -1), ("R", 1)):
        joint = hip + np.array([sx * 0.09, 0.0, -0.02])
        c.begin(f"{name}_Leg_{side}", joint, role="leg: swings about local X while walking",
                length_m=round(float(joint[2]), 3))
        foot = np.array([joint[0], joint[1], 0.07])
        leg = L.member(joint, foot + np.array([0, 0, 0.06]), 0.12, 0.11, c.sw("pal"))
        c.pal_uv(leg, "#3D4046")
        c.add(leg, dice=None, jit=0.0)
        boot = L.box(0.12, 0.24, 0.16, c.sw("pal"), center=(foot[0], foot[1] + 0.05, 0.0), chamfer=0.025, base=True)
        c.pal_uv(boot, "#4E2E20")
        c.add(boot, dice=None, jit=0.0)
    c.begin(c.aid, (0.0, 0.0, 0.0))


def sling_cart(c: SiegeCtx):
    """Clans Sling-Cart: a low lattice-wood cart on two plain spoked wheels, a tall throwing arm
    on an A-frame with a felt sling hanging at rest (traction engine: haul ropes from the short end
    back to the crew, no counterweight box), a teal felt hood over the clay-pot rack, two Tormai
    crew pushing. Team colour: the felt sling, the rope-wrap on the arm, the crew's hat bands, the
    hood's middle stripe (bible 3.1, 4.1). No spikes, skulls or hide panels (slice-plan 2.5 D2)."""
    wheel_r, track = 0.5, 0.56
    zb = wheel_r + 0.06
    zt = zb + 0.07
    y0, y1, hw = -0.72, 0.64, 0.4
    # the low lattice bed
    c.add(L.box(y1 - y0, hw * 2, 0.07, c.sw("lattice"), center=((y0 + y1) / 2, 0, zb + 0.035), chamfer=0.015)
          .rot(0, 0, 90), dice=None, uvrot=True)
    for sx in (-1, 1):
        rail_z0, rail_z1 = zt, zt + 0.24
        for yy in np.linspace(y0 + 0.04, y1 - 0.04, 5):
            c.add(L.member((sx * hw, yy, zb), (sx * hw, yy, rail_z1 + 0.03), 0.05, 0.05, c.sw("lattice"), rng=c.rng),
                  dice=None)
        c.add(L.member((sx * hw, y0, rail_z1), (sx * hw, y1, rail_z1), 0.06, 0.05, c.sw("lattice"), rng=c.rng),
              dice=None)
        ys = np.linspace(y0 + 0.04, y1 - 0.04, 5)
        for i in range(4):   # the lattice: crossed slats between the posts
            for a, b in (((ys[i], rail_z0), (ys[i + 1], rail_z1)), ((ys[i], rail_z1), (ys[i + 1], rail_z0))):
                c.add(L.member((sx * hw, a[0], a[1]), (sx * hw, b[0], b[1]), 0.03, 0.02, c.sw("lattice"),
                               rng=c.rng), dice=None)
    c.add(L.member((-track - 0.02, 0.0, wheel_r), (track + 0.02, 0.0, wheel_r), 0.09, 0.09, c.sw("wood"),
                   rng=c.rng), dice=None)
    # the A-frame carrying the arm's pivot
    pivot = (0.0, 0.0, 1.4)
    for sx in (-1, 1):
        top = (sx * 0.16, 0.0, pivot[2])
        for dy in (-0.42, 0.42):
            c.add(L.member((sx * 0.3, dy, zt), top, 0.08, 0.07, c.sw("wood"), rng=c.rng), dice=None)
        c.add(L.member((sx * 0.31, -0.3, zt + 0.35), (sx * 0.31, 0.3, zt + 0.35), 0.06, 0.05, c.sw("wood"), rng=c.rng),
              dice=None)
    c.add(L.lathe([(0.0, -0.22), (0.045, -0.22), (0.045, 0.22), (0.0, 0.22)], 8, c.sw("bronze")).rot(0, 90, 0)
          .move(*pivot), dice=None)
    # the pot rack under a felt hood at the front, clay pots peeking out
    hood_y0, hood_y1 = 0.22, y1 - 0.02
    for i, yy in enumerate((0.3, 0.45)):
        for xx in (-0.2, 0.0, 0.2):
            pot = L.lathe([(0.0, 0.0), (0.06, 0.0), (0.085, 0.06), (0.08, 0.12), (0.045, 0.15), (0.05, 0.17),
                           (0.0, 0.17)], 10, c.sw("pal"), smooth=55.0)
            c.pal_uv(pot, "#A8743A")
            c.add(pot.move(xx, yy, zt), dice=None)
    nseg = 8
    prof = [(math.cos(math.pi * i / nseg) * hw * 0.92, math.sin(math.pi * i / nseg) * 0.36) for i in range(nseg + 1)]
    xs_ = [hood_y0 + 0.14, (hood_y0 + hood_y1) / 2 + 0.05, hood_y1]
    # team felt with teal hems at both ends (the hems are its neutral piping)
    segs = [(hood_y0 + 0.14, hood_y0 + 0.2, "teal"), (hood_y0 + 0.2, hood_y1 - 0.06, "team"),
            (hood_y1 - 0.06, hood_y1, "teal")]
    for ya, yb, kind in segs:
        verts = []
        for yy in (ya, yb):
            for (px, pz) in prof:
                verts.append((px, yy, zt + 0.02 + pz))
        verts = np.array(verts)
        K = len(prof)
        tris = []
        for i in range(K - 1):
            a, b, cc, d = i, i + 1, K + i + 1, K + i
            tris += [(a, b, cc), (a, cc, d)]
        tris = np.array(tris)
        cv = L.Part(verts, tris, c.sw("teal" if kind == "teal" else "team_plain"), None, 60)
        vv = cv.v[cv.t]
        ang = np.arctan2(vv[..., 2] - zt, vv[..., 0])
        cv.uv = np.stack([(vv[..., 1] - ya) / 0.8, ang / math.pi], -1) if kind == "teal" else np.full((len(tris), 3, 2), 0.5)
        c.add(cv, dice=None, form=0.0)
        back = cv.copy()
        back.t = back.t[:, ::-1]
        back.uv = back.uv[:, ::-1]
        c.add(back, dice=None, form=0.0)
    # a folded felt blanket over the rear of the bed (team felt, teal hems)
    for ya, yb, key in ((y0 + 0.06, y0 + 0.1, "teal"), (y0 + 0.1, -0.4, "team_plain"), (-0.4, -0.36, "teal")):
        blanket = L.box(hw * 2 - 0.06, yb - ya, 0.07, c.sw(key), center=(0.0, (ya + yb) / 2, zt), chamfer=0.02,
                        base=True)
        if key == "team_plain":
            blanket.uv[:] = 0.5
        c.add(blanket, dice=None)
    # push bar at the back
    bar_y, bar_z = -1.06, 1.0
    for sx in (-1, 1):
        c.add(L.member((sx * 0.33, y0 + 0.06, zt - 0.02), (sx * 0.36, bar_y, bar_z), 0.07, 0.07, c.sw("wood"),
                       rng=c.rng), dice=None)
    c.add(L.member((-0.45, bar_y, bar_z), (0.45, bar_y, bar_z), 0.065, 0.065, c.sw("wood"), rng=c.rng), dice=None)
    # wheels: plain wooden spoked wheels with an iron tyre (no spikes)
    for side, sx in (("L", -1), ("R", 1)):
        center = (sx * track, 0.0, wheel_r)
        c.begin(f"Wheel_{side}", center, role="wheel: spins about local X", radius_m=wheel_r)
        painted_wheel(c, center, wheel_r, spokes=8, width=0.08, segs=18, rim_key="wood", spoke_key="wood")
        c.begin(c.aid, (0.0, 0.0, 0.0))
    # the throwing arm (its own node, pivot on the A-frame): upright at rest, the felt sling
    # hanging from the tip, the haul ropes from the short end back to the crew
    c.begin("Arm", pivot, role="throwing arm: swings about local X (back on the haul, forward on the release)",
            length_m=1.45)
    ax = np.array(pivot)
    tip = ax + np.array([0.0, -0.08, 1.42])
    butt = ax + np.array([0.0, 0.05, -0.6])
    c.add(L.member(butt, tip, 0.12, 0.1, c.sw("wood"), rng=c.rng), dice=None)
    for z0, z1 in ((0.15, 0.42), (1.0, 1.18)):   # the team rope-wrap
        wrap = L.lathe([(0.085, 0.0), (0.085, z1 - z0)], 10, c.sw("team_plain"))
        wrap.uv[:] = 0.5
        d = (tip - butt) / np.linalg.norm(tip - butt)
        R = L.frame_from_z(d)
        wrap.xf(R).move(*(butt + d * (0.6 + z0)))
        c.add(wrap, dice=None)
    # sling: two cords from the tip and a felt pouch (team colour) hanging behind the arm
    pouch_c = tip + np.array([0.0, -0.16, -0.62])
    for sx in (-1, 1):
        cord = L.member(tip + np.array([sx * 0.03, -0.02, -0.02]), pouch_c + np.array([sx * 0.09, 0.0, 0.05]),
                        0.02, 0.02, c.sw("pal"))
        c.pal_uv(cord, "#C9A46A")
        c.add(cord, dice=None)
    pouch = L.Part(*L.icosphere(2, 0.13), c.sw("team_plain"), smooth=50.0).scale(1.2, 0.8, 0.9)
    pouch.uv[:] = 0.5
    c.add(pouch.move(*pouch_c), dice=None)
    for sx in (-1, 1):
        rope = L.member(butt + np.array([sx * 0.05, -0.02, 0.0]), np.array([sx * 0.2, bar_y + 0.02, bar_z + 0.06]),
                        0.025, 0.025, c.sw("pal"))
        c.pal_uv(rope, "#C9A46A")
        c.add(rope, dice=None)
    c.anchors["sling"] = pouch_c
    c.begin(c.aid, (0.0, 0.0, 0.0))
    for name, x in (("Crew_A", -0.26), ("Crew_B", 0.27)):
        tormai_crew(c, name, x, -1.54, 0.8, 22.0, bar_y, bar_z)
    return {"stride_m": 1.15}


ALL = {"kingdom_bombard_wagon": {"fn": bombard_wagon, "faction": "kingdom"},
       "clans_sling_cart": {"fn": sling_cart, "faction": "clans"}}


def _sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def build(aid, out_dir):
    spec = ALL[aid]
    t0 = time.time()
    c = SiegeCtx(aid, spec["faction"])
    info = spec["fn"](c) or {}
    parts = [p for ps in c.nodes.values() for p in ps]
    for p in parts:
        if p.dice:
            L.refine(p, p.dice)
    for p in parts:
        p.v[:, 2] = np.maximum(p.v[:, 2], 0.0)
    v = np.concatenate([p.v for p in parts])
    lo, hi = v.min(0), v.max(0)
    # centre the length on the origin (the sim's circle and picking sit on the unit's position)
    dy = -float(lo[1] + hi[1]) / 2.0
    for p in parts:
        p.v[:, 1] += dy
    for k in c.pivots:
        q = c.pivots[k]
        c.pivots[k] = (q[0], q[1] + dy, q[2])
    for k in c.anchors:
        c.anchors[k] = np.asarray(c.anchors[k]) + np.array([0.0, dy, 0.0])
    lo[1] += dy
    hi[1] += dy
    H = float(hi[2])
    anchors = {k: [round(float(q[0]), 3), round(float(q[2]), 3), round(float(-q[1]), 3)] for k, q in c.anchors.items()}
    extras = {"vibecraft": {"id": aid, "kit": "tools/kits/siege.py", "facing": "front faces -Z",
                            "nodes": "moving parts are child nodes at their pivots (see tools/kits/siege.py)",
                            "anchors": anchors, **({"stride_m": info["stride_m"]} if "stride_m" in info else {})}}
    nodes = [(name, c.pivots[name], c.nodes[name], c.node_extras.get(name)) for name in c.nodes if c.nodes[name]]
    path = os.path.join(out_dir, aid + ".glb")
    st = L.export_glb_nodes(path, aid, nodes, H, c.bake, B.sheets_for(spec["faction"]), extras=extras,
                            piping=(c.S["pal"], L.palette_uv(c.pal, B.PIPING[spec["faction"]])),
                            uri_prefix="../buildings/")
    rec = {"id": aid, "height_m": round(H, 3), "length_m": round(float(hi[1] - lo[1]), 3),
           "width_m": round(float(hi[0] - lo[0]), 3), "tris": st["tris"], "nodes": [n[0] for n in nodes],
           "materials": st["materials"], "anchors_godot": anchors, "glb_sha1": _sha1(path),
           "seconds": round(time.time() - t0, 1)}
    L.log(f"{aid}: {st['tris']} tris, {rec['length_m']} x {rec['width_m']} x {rec['height_m']} m, {rec['seconds']} s")
    return rec


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="comma-separated ids (default: all)")
    ap.add_argument("--out-dir", default=OUT_DIR)
    a = ap.parse_args(argv)
    ids = [x for x in a.only.split(",") if x] or list(ALL)
    recs = [build(i, a.out_dir) for i in ids]
    print(json.dumps({"built": recs}, indent=1))


if __name__ == "__main__":
    main()
