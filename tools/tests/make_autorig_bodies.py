"""Synthesize differently-proportioned test bodies for tools/autorig.py, with ground-truth joints.

Run with the bpy interpreter:
    /opt/bpyenv/v313/bin/python tools/tests/make_autorig_bodies.py --mesh MESH.glb --rig RIG.glb \\
        --out-dir /tmp/bodies

MESH is a static character facing +Z (glTF) with feet on 0 (e.g. the mesh a paid rig was made
on), RIG the rigged file of that same mesh (its joints are the ground truth). Every variant is a
smooth spatial deformation f of the mesh; the same f applied to the rig's joints gives the joints
the variant should get. Output per variant: <name>.glb (static, faces +Z, normalised to the
variant height, bounds-centred like autorig does) and <name>_joints.json ({"joints": {bone:
[x, y, z]}} in glTF axes, the format of autorig --reference-joints).

  brute   1.3x wider, 1.15x deeper, legs 0.85x, upper body hunched 25 deg forward   -> 2.10 m
  caster  0.82x slimmer, legs 1.12x, long closed robe hiding the legs, a separate staff
          (own mesh island) through the right hand                                 -> 1.90 m
  worker  1.15x wider, legs 0.75x, head 1.35x bigger                                 -> 1.10 m
  hero    1.08x wider shoulders, legs 1.06x, a long cape (own mesh island, touching the
          shoulders, hanging free behind the back and legs down to the knees)       -> 2.10 m
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix  # noqa: E402

import vc_bpy as vc  # noqa: E402

HIP = 0.87     # template-space heights (1.75 m soldier): hip joints, waist, neck
WAIST = 1.0
NECK = 1.33


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def legs(P, k):
    """Scale everything below the hip height by k (continuous above: shifted)."""
    z = P[:, 2]
    P[:, 2] = np.where(z < HIP, z * k, z + HIP * (k - 1.0))
    return P


def widen(P, kx, ky, cx, cy):
    P[:, 0] = cx + (P[:, 0] - cx) * kx
    P[:, 1] = cy + (P[:, 1] - cy) * ky
    return P


def hunch(P, deg, z0, ztop, cy):
    """Bend the body above z0 forward (towards -Y = glTF +Z front), up to `deg` at ztop."""
    th = np.radians(deg) * smoothstep(z0, ztop, P[:, 2]) ** 1.2
    y, z = P[:, 1] - cy, P[:, 2] - z0
    above = P[:, 2] > z0
    yn = y * np.cos(th) - z * np.sin(th)
    zn = y * np.sin(th) + z * np.cos(th)
    P[above, 1] = (yn + cy)[above]
    P[above, 2] = (zn + z0)[above]
    return P


def big_head(P, k, c):
    s = 1.0 + (k - 1.0) * smoothstep(NECK - 0.03, NECK + 0.07, P[:, 2])
    return c + (P - c) * s[:, None]


def variant(name, P, cx, cy):
    P = P.copy()
    if name == "brute":
        P = widen(P, 1.3, 1.15, cx, cy)
        P = legs(P, 0.85)
        P = hunch(P, 25.0, WAIST + HIP * (0.85 - 1.0), 1.75, cy)
    elif name == "caster":
        P = widen(P, 0.82, 0.9, cx, cy)
        P = legs(P, 1.12)
    elif name == "worker":
        P = big_head(P, 1.35, np.array([cx, cy, NECK]))
        P = widen(P, 1.15, 1.05, cx, cy)
        P = legs(P, 0.75)
    elif name == "hero":
        k = 1.0 + 0.08 * smoothstep(WAIST, NECK, P[:, 2])
        P[:, 0] = cx + (P[:, 0] - cx) * k
        P = legs(P, 1.06)
    return P


HEIGHT = {"brute": 2.10, "caster": 1.90, "worker": 1.10, "hero": 2.10}


def flat_uv(bm, faces, p, exclude=()):
    """Give `faces` the UV of the existing vertex nearest to p (one flat, opaque texel colour;
    new geometry would otherwise sample UV (0, 0), often the transparent atlas background)."""
    uvl = bm.loops.layers.uv.active
    if uvl is None:
        return
    best, bd = None, 1e9
    for f in bm.faces:
        if f in faces or f in exclude:
            continue
        for lp in f.loops:
            d = (lp.vert.co - p).length
            if d < bd:
                best, bd = lp[uvl].uv.copy(), d
    if best is None:
        return
    for f in faces:
        for lp in f.loops:
            lp[uvl].uv = best


def add_robe(bm, cx, cy, ztop, zbot, rtop, rbot, seg=40, rings=10):
    """Closed, slightly flared robe (truncated elliptic cone) around the legs. Returns its faces."""
    verts = []
    faces = []
    for r in range(rings + 1):
        t = r / rings
        z = ztop + (zbot - ztop) * t
        ax, ay = rtop[0] + (rbot[0] - rtop[0]) * t ** 1.3, rtop[1] + (rbot[1] - rtop[1]) * t ** 1.3
        ring = []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            ring.append(bm.verts.new((cx + ax * math.cos(a), cy + ay * math.sin(a), z)))
        verts.append(ring)
    for r in range(rings):
        for s in range(seg):
            a, b = verts[r][s], verts[r][(s + 1) % seg]
            c, d = verts[r + 1][(s + 1) % seg], verts[r + 1][s]
            faces.append(bm.faces.new((a, b, c, d)))
    faces.append(bm.faces.new(list(reversed(verts[0]))))
    faces.append(bm.faces.new(verts[-1]))
    return faces


def add_cape(bm, co, cx, ztop, zbot, half_top, half_bot, gap_bot=0.07, thick=0.012, nu=14, nv=18):
    """Closed thin slab behind the back: touches the body at ztop, hangs `gap_bot` behind the
    back profile at zbot, wraps slightly around the body. `co` = body vertices (back = +Y)."""
    def back_y(z):
        band = co[(np.abs(co[:, 2] - z) < 0.04) & (np.abs(co[:, 0] - cx) < 0.12)]
        return float(np.percentile(band[:, 1], 90)) if len(band) else float(co[:, 1].max())
    zs = np.linspace(ztop, zbot, nv + 1)
    prof = np.maximum.accumulate(np.array([back_y(z) for z in zs]))   # hangs straight, never tucks in
    grid = {}
    for side, off in (("out", thick), ("in", 0.0)):
        for i, z in enumerate(zs):
            t = i / nv
            half = half_top + (half_bot - half_top) * t
            for j in range(nu + 1):
                u = -1.0 + 2.0 * j / nu
                y = prof[i] + gap_bot * t ** 1.5 + off - 0.05 * u * u * (1 - 0.5 * t)
                grid[side, i, j] = bm.verts.new((cx + u * half, y, z))
    faces = []
    for i in range(nv):
        for j in range(nu):
            o = [grid["out", i, j], grid["out", i, j + 1], grid["out", i + 1, j + 1], grid["out", i + 1, j]]
            n = [grid["in", i, j], grid["in", i + 1, j], grid["in", i + 1, j + 1], grid["in", i, j + 1]]
            faces += [bm.faces.new(o), bm.faces.new(n)]
    rim = [(i, 0) for i in range(nv)] + [(nv, j) for j in range(nu)] + [(i, nu) for i in range(nv, 0, -1)] \
        + [(0, j) for j in range(nu, 0, -1)]
    for a, b in zip(rim, rim[1:] + rim[:1]):
        faces.append(bm.faces.new([grid["out", a[0], a[1]], grid["in", a[0], a[1]], grid["in", b[0], b[1]],
                                   grid["out", b[0], b[1]]]))
    return faces


def add_staff(bm, p0, p1, radius=0.018, seg=10):
    """Closed cylinder (own mesh island). Returns its faces."""
    d = (np.array(p1) - np.array(p0))
    L = np.linalg.norm(d)
    d /= L
    up = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, up)
    u /= np.linalg.norm(u)
    w = np.cross(d, u)
    rings = []
    for end in (p0, p1):
        rings.append([bm.verts.new(tuple(np.array(end) + radius * (math.cos(2 * math.pi * s / seg) * u
                                                               + math.sin(2 * math.pi * s / seg) * w)))
                      for s in range(seg)])
    faces = [bm.faces.new((rings[0][s], rings[0][(s + 1) % seg], rings[1][(s + 1) % seg], rings[1][s]))
             for s in range(seg)]
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[1]))
    return faces


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--rig", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--variants", default="brute,caster,worker,hero")
    args = ap.parse_args(vc.bpy_argv())
    os.makedirs(args.out_dir, exist_ok=True)

    vc.reset_scene()
    objs = vc.import_glb(args.rig)
    arm = max([o for o in objs if o.type == "ARMATURE"], key=lambda a: len(a.data.bones))
    names = [b.name for b in arm.data.bones]
    J = np.array([list(arm.matrix_world @ b.head_local) for b in arm.data.bones])

    summary = {"variants": []}
    for name in [v.strip() for v in args.variants.split(",") if v.strip()]:
        vc.reset_scene()
        objs = vc.import_glb(args.mesh)
        meshes = [o for o in objs if o.type == "MESH"]
        for o in meshes:
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)
        if len(meshes) > 1:
            vc.select_only(meshes, meshes[0])
            bpy.ops.object.join()
        body = meshes[0]
        me = body.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        cx, cy = float(J[names.index("Hips"), 0]), float(J[names.index("Hips"), 1])
        new = variant(name, co, cx, cy)
        me.vertices.foreach_set("co", new.ravel())
        me.update()
        Jv = variant(name, J, cx, cy)
        if name == "caster":
            bm = bmesh.new()
            bm.from_mesh(me)
            zh = float(Jv[names.index("LeftUpLeg"), 2])
            hips_w = abs(float(Jv[names.index("LeftUpLeg"), 0] - Jv[names.index("RightUpLeg"), 0]))
            from mathutils import Vector
            knee = Jv[names.index("LeftLeg")]
            robe_uv_at = Vector((float(knee[0]) + 0.06, float(knee[1]), float(knee[2])))   # trouser cloth
            hand = Jv[names.index("RightHand")]
            hand_uv_at = Vector((float(hand[0]), float(hand[1]), float(hand[2])))           # glove leather
            robe = add_robe(bm, cx, cy + 0.01, zh + 0.12, 0.012, (hips_w * 0.95, 0.17),
                            (hips_w * 1.45 + 0.05, 0.27))
            staff = add_staff(bm, (hand[0] - 0.03, hand[1] - 0.05, 0.03), (hand[0] - 0.03, hand[1] - 0.05, 1.95))
            new = set(robe) | set(staff)
            flat_uv(bm, set(robe), robe_uv_at, exclude=new)
            flat_uv(bm, set(staff), hand_uv_at, exclude=new)
            bm.to_mesh(me)
            bm.free()
            me.update()
        if name == "hero":
            from mathutils import Vector
            bm = bmesh.new()
            bm.from_mesh(me)
            co_b = np.array([v.co[:] for v in bm.verts])
            sh = abs(float(Jv[names.index("LeftArm"), 0] - Jv[names.index("RightArm"), 0])) / 2
            knee = Jv[names.index("LeftLeg")]
            cape = add_cape(bm, co_b, cx, float(Jv[names.index("neck"), 2]) - 0.05, float(knee[2]) + 0.02,
                            0.8 * sh, 1.05 * sh)
            flat_uv(bm, set(cape), Vector((float(knee[0]) + 0.06, float(knee[1]), float(knee[2]) + 0.15)),
                    exclude=set(cape))
            bm.to_mesh(me)
            bm.free()
            me.update()
        # normalise exactly like autorig: bounds-centred in X/Y, feet on 0, scaled to the height
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        s = HEIGHT[name] / (hi[2] - lo[2])
        off = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        co = (co + off) * s
        me.vertices.foreach_set("co", co.ravel())
        me.update()
        Jn = (Jv + off) * s
        path = os.path.join(args.out_dir, name + ".glb")
        body.name = me.name = name
        vc.export_glb(path, animations=False)
        joints = {b: [round(float(p[0]), 5), round(float(p[2]), 5), round(float(-p[1]), 5)] for b, p in zip(names, Jn)}
        jpath = os.path.join(args.out_dir, name + "_joints.json")
        with open(jpath, "w") as f:
            json.dump({"joints": joints, "height": HEIGHT[name]}, f, indent=1)
        summary["variants"].append({"name": name, "glb": path, "joints": jpath, "height": HEIGHT[name],
                                    "verts": len(me.vertices)})
    vc.emit_json(summary)


if __name__ == "__main__":
    main()
