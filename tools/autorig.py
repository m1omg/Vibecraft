"""Free, local auto-rigger: static AI character GLB -> skinned, animated, game-ready GLB.

Replaces paid auto-rigging (Meshy / Higgsfield 3d_rigging). Run with the bpy interpreter:

    /opt/bpyenv/v313/bin/python tools/autorig.py raw/soldier.glb -o assets/models/soldier.glb \\
        --template assets_src/characters/kingdom_infantry/rig_walk.glb --facing +x --height 1.75 \\
        --clip idle=.../rig_idle.glb --clip walk=.../rig_walk.glb \\
        --clip attack=.../rig_attack_sword.glb --clip death=.../rig_death.glb \\
        --target-tris 4500 --team-mask 300:45:0.3 --name soldier

Pipeline
  1. import the static mesh(es), bake transforms, join, weld exact duplicates; turn it to face +Z
     (glTF front) from --facing, scale to --height, feet on 0, centred on the bounds
  2. LANDMARKS: the mesh is voxelised (H/160 voxels, flood-filled solid, distance-to-surface per
     voxel). Horizontal slices of the "core" (voxels at least 2-3 voxels inside the surface, which
     drops thin props: blades, shield plates, capes, aprons, hat brims) give: two leg sections
     tracked up from the floor until they merge (crotch), the torso section per height (centre,
     width, depth), the shoulder top (where the torso+arms width collapses to the neck), the head
     top (on the head axis, so plumes and crests are ignored), and the arm sections tracked down
     from the armpit to the fist. Every template joint is expressed relative to these features ON
     THE TEMPLATE'S OWN MESH (calibration: height between feature levels, fraction across the
     local torso/leg section, fraction along the arm path), and the same relative position is
     looked up on the target. Missing features (robes hide the legs, arms touching the body)
     fall back to template proportions scaled per region; the JSON says which joint came from what.
  3. ARMATURE: exactly the template's bones, names, hierarchy and rest orientations (rolls), only
     the joint positions move, so clips map 1:1 (merge_anims would even copy keys verbatim).
  4. SKIN: voxel-remeshed watertight proxy (--voxel x height) -> Blender automatic weights (bone
     heat) on a helper armature whose bones run joint-to-joint -> Data Transfer (nearest face,
     interpolated) to the real mesh -> held props (geometry that is thin or disconnected and touches
     only the hand/forearm: swords, shields, staffs) are bound 100% to the hand -> clean < 0.01,
     limit 4, normalise. Nearest-bone-segment weights fill anything bone heat missed.
  5. CLIPS: every --clip NAME=FILE[:ACTION] is retargeted with vc_bpy.retarget_action (the code
     behind retarget_anims.py), then the clip's mean facing (left/right axis of hips+shoulders over
     the clip) is measured and removed with a constant yaw on the root bone, so the body faces the
     unit's forward on average (library idle/attack clips turn ~60 deg away). Hips motion is kept
     vertical (in place) except for death (full), see --hips-mode.
  6. unless --raw: process_model.py is run on the result (decimate, team mask, textures, turn to
     face -Z for Godot), so OUT is game-ready.
  7. QA (JSON on stdout): landmark source per joint, skin stats, per clip the max vertex
     displacement / height and edge stretch (deformed/rest, flagged > 2), facing after the fix,
     foot slide, and with --reference-rig/--reference-joints the joint position error in cm.

Coordinates in the JSON are glTF/Godot axes of the normalised +Z-facing rig (x = character's left,
y = up, z = forward), metres. --debug-png draws the joints on front/side voxel projections.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

import vc_bpy as vc  # noqa: E402

# yaw (deg, CCW about up) that turns a model facing <key> (glTF axes) to face +Z
FACING_TO_PZ = {"+z": 0.0, "-z": 180.0, "+x": -90.0, "-x": 90.0, "auto": 0.0}
DEFAULT_HIPS_MODE = {"death": "full"}
ANALYSIS_SLICES = 160


def facing_arg(v):
    v = v.strip().lower()
    alias = {"z": "+z", "z+": "+z", "pz": "+z", "z-": "-z", "nz": "-z", "x": "+x", "x+": "+x", "px": "+x",
             "x-": "-x", "nx": "-x"}
    v = alias.get(v, v)
    if v not in FACING_TO_PZ:
        raise argparse.ArgumentTypeError(f"facing must be one of {sorted(FACING_TO_PZ)}")
    return v


def parse_args():
    ap = argparse.ArgumentParser(prog="autorig.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="static character .glb (any armature in it is discarded)")
    ap.add_argument("-o", "--out", required=True, help="output .glb")
    ap.add_argument("--template", required=True,
                    help="rigged GLB whose skeleton (names, hierarchy, rest orientations) is fitted; its own skinned "
                         "mesh, if present, calibrates where joints sit relative to body landmarks")
    ap.add_argument("--facing", type=facing_arg, default="+z", metavar="{+z,-z,+x,-x,auto}",
                    help="direction the INPUT faces in glTF axes (raw Tripo: +x; glTF convention / Meshy: +z "
                         "[default]; process_model output: -z). Write negatives as --facing=-x. 'auto' guesses it "
                         "from the feet (toes point forward); a given facing is always checked the same way and a "
                         "disagreement is warned about")
    ap.add_argument("--yaw", type=float, default=0.0, help="extra input turn, degrees CCW from above, after --facing")
    ap.add_argument("--height", type=float, default=0.0, help="character height in metres (default: template's)")
    c = ap.add_argument_group("clips")
    c.add_argument("--clip", action="append", default=[], metavar="NAME=FILE[:ACTION]",
                   help="animation to transfer (any rig with the template's bone names); repeatable")
    c.add_argument("--hips-mode", action="append", default=[], metavar="NAME=MODE",
                   help="hips translation per clip: vertical (in place, default), full (keeps travel, default for "
                        "death), none")
    c.add_argument("--no-face-fix", action="store_true", help="don't remove the clips' mean yaw")
    c.add_argument("--no-foot-ik", action="store_true",
                   help="don't correct the legs with IK (feet then slide when proportions differ from the clip's rig)")
    s = ap.add_argument_group("skinning")
    s.add_argument("--voxel", type=float, default=0.008, help="proxy voxel size as a fraction of height (0.008)")
    s.add_argument("--no-props", action="store_true", help="don't bind held props rigidly to the hand")
    s.add_argument("--weights", choices=["heat", "envelope"], default="heat",
                   help="heat = bone heat on a voxel proxy (default), envelope = nearest bone segments only")
    lm = ap.add_argument_group("landmarks")
    lm.add_argument("--no-calibrate", action="store_true",
                    help="use built-in landmark coefficients instead of calibrating on the template's mesh")
    lm.add_argument("--joints", default=None,
                    help="JSON {bone: [x, y, z]} (glTF axes of the normalised +Z-facing model) overriding joints")
    lm.add_argument("--debug-png", default=None, help="write front/side voxel projections with the joints")
    lm.add_argument("--landmarks-json", default=None, help="write detected features + joints here")
    p = ap.add_argument_group("game-ready output (process_model.py)")
    p.add_argument("--raw", action="store_true",
                   help="skip process_model: OUT is the full-res rig facing +Z (glTF), not game-ready")
    p.add_argument("--target-tris", type=int, default=0)
    p.add_argument("--team-mask", default=None)
    p.add_argument("--team-desaturate", action="store_true")
    p.add_argument("--name", default=None, help="mesh/material base name (default: output stem)")
    p.add_argument("--tex-size", type=int, default=1024)
    p.add_argument("--pm-arg", action="append", default=[], help="extra argument for process_model; repeatable")
    p.add_argument("--keep-rig", default=None, help="also save the full-res +Z-facing rig GLB here")
    q = ap.add_argument_group("QA")
    q.add_argument("--reference-rig", default=None,
                   help="rigged GLB in the same space (e.g. the paid rig of this very mesh): joint error in cm")
    q.add_argument("--reference-joints", default=None, help="JSON {bone: [x,y,z]} (glTF axes) for the joint error")
    q.add_argument("--qa-frames", type=int, default=24, help="frames sampled per clip for the QA metrics")
    ap.add_argument("--fps", type=int, default=vc.FPS_DEFAULT)
    ap.add_argument("--json", default=None, help="also write the JSON summary here")
    return ap.parse_args(vc.bpy_argv())


# =========================================================================== numpy voxel tools

def _offsets(ndim, diag):
    offs = []
    for o in itertools.product((-1, 0, 1), repeat=ndim):
        if not any(o):
            continue
        if not diag and sum(abs(v) for v in o) != 1:
            continue
        if next(v for v in o if v) > 0:
            offs.append(o)
    return offs


def _slices(o):
    src, dst = [], []
    for v in o:
        if v > 0:
            src.append(slice(0, -v)); dst.append(slice(v, None))
        elif v < 0:
            src.append(slice(-v, None)); dst.append(slice(0, v))
        else:
            src.append(slice(None)); dst.append(slice(None))
    return tuple(src), tuple(dst)


def label_cc(mask, diag=False):
    """Connected components without scipy. Returns (labels, sizes); labels -1 = background,
    0 = largest component. Deterministic (ties broken by first voxel index)."""
    mask = np.ascontiguousarray(mask, dtype=bool)
    n = mask.size
    grid = np.arange(n, dtype=np.int64).reshape(mask.shape)
    A, B = [], []
    for o in _offsets(mask.ndim, diag):
        s, d = _slices(o)
        both = mask[s] & mask[d]
        if both.any():
            A.append(grid[s][both]); B.append(grid[d][both])
    lab = np.arange(n, dtype=np.int64)
    if A:
        A = np.concatenate(A); B = np.concatenate(B)
        while True:
            la, lb = lab[A], lab[B]
            diff = la != lb
            if not diff.any():
                break
            np.minimum.at(lab, np.maximum(la[diff], lb[diff]), np.minimum(la[diff], lb[diff]))
            while True:
                nl = lab[lab]
                if np.array_equal(nl, lab):
                    break
                lab = nl
    flat = mask.ravel()
    out = np.full(n, -1, dtype=np.int32)
    if not flat.any():
        return out.reshape(mask.shape), np.zeros(0, np.int64)
    uniq, inv, counts = np.unique(lab[flat], return_inverse=True, return_counts=True)
    order = np.lexsort((uniq, -counts))
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    out[flat] = rank[inv]
    return out.reshape(mask.shape), counts[order]


def dilate(m, diag=True):
    out = m.copy()
    for o in _offsets(m.ndim, diag):
        for oo in (o, tuple(-v for v in o)):
            s, d = _slices(oo)
            out[d] |= m[s]
    return out


def erode(m, diag=False):
    return ~dilate(~m, diag)


def sample_surface(V, F, step):
    """Points on every triangle on a barycentric lattice with spacing <= step (deterministic)."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    L = np.maximum(np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1)),
                   np.linalg.norm(a - c, axis=1))
    s = np.clip(np.ceil(L / step).astype(np.int64), 1, 96)
    pts = [V]
    for k in np.unique(s):
        sel = np.where(s == k)[0]
        ij = np.array([(i, j) for i in range(k + 1) for j in range(k + 1 - i)], dtype=np.float64) / k
        u, w = ij[:, 0], ij[:, 1]
        for chunk in np.array_split(sel, max(1, len(sel) * len(ij) // 400000 + 1)):
            P = (a[chunk, None, :] * (1 - u - w)[None, :, None] + b[chunk, None, :] * u[None, :, None]
                 + c[chunk, None, :] * w[None, :, None])
            pts.append(P.reshape(-1, 3))
    return np.concatenate(pts)


class Grid:
    """Solid voxelisation of a (not necessarily watertight) triangle mesh + distance to surface."""

    def __init__(self, V, F, vsize, pad=3):
        self.v = float(vsize)
        self.lo = V.min(0) - pad * vsize
        hi = V.max(0) + pad * vsize
        self.shape = tuple(int(x) for x in (np.ceil((hi - self.lo) / vsize).astype(int) + 1))
        ijk = self.index(sample_surface(V, F, vsize * 0.5))
        surf = np.zeros(self.shape, bool)
        surf[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
        self.surf = surf
        self.solid = self._fill(surf)
        self.dt = self._dt(self.solid)

    def index(self, P):
        ijk = np.floor((np.asarray(P) - self.lo) / self.v).astype(np.int64)
        return np.clip(ijk, 0, np.array(self.shape) - 1)

    def center(self, ijk):
        return self.lo + (np.asarray(ijk, dtype=np.float64) + 0.5) * self.v

    def zk(self, z):
        return int(np.clip(np.floor((z - self.lo[2]) / self.v), 0, self.shape[2] - 1))

    def kz(self, k):
        return float(self.lo[2] + (k + 0.5) * self.v)

    @staticmethod
    def _fill(surf):
        block = dilate(surf, diag=True)             # closes holes up to ~2 voxels
        free = ~block
        out = np.zeros_like(surf)
        out[0], out[-1] = True, True
        out[:, 0], out[:, -1] = True, True
        out[:, :, 0], out[:, :, -1] = True, True
        out &= free
        for _ in range(1000):
            for ax in range(3):
                for flip in (False, True):
                    f = np.flip(free, ax) if flip else free
                    o = np.flip(out, ax) if flip else out
                    seg = np.cumsum(~f, axis=ax)
                    acc = np.maximum.accumulate(seg * 2 + o.astype(np.int64), axis=ax)
                    r = (acc == seg * 2 + 1) & f
                    out |= np.flip(r, ax) if flip else r
            new = out | (dilate(out, diag=False) & free)
            if np.array_equal(new, out):
                break
            out = new
        return erode(~out, diag=False) | surf

    @staticmethod
    def _dt(solid):
        """Erosion depth (alternating 6/26 neighbourhoods ~ euclidean), in voxels; 1 = surface layer."""
        dt = np.zeros(solid.shape, np.float32)
        cur = solid.copy()
        k = 0
        while cur.any():
            dt[cur] += 1
            k += 1
            cur = erode(cur, diag=(k % 2 == 0))
        return dt


# =========================================================================== landmark features

def slice_comps(g, k, r, min_n=3):
    """Components of the slice k of the core (dt >= r), with DT-weighted centroids and extents."""
    core = g.dt[:, :, k] >= r
    if not core.any():
        return []
    lab, sizes = label_cc(core, diag=True)
    out = []
    for ci, n in enumerate(sizes):
        if n < min_n:
            break
        m = lab == ci
        ii, jj = np.nonzero(m)
        w = g.dt[ii, jj, k] - (r - 1)
        x = g.lo[0] + (ii + 0.5) * g.v
        y = g.lo[1] + (jj + 0.5) * g.v
        ws = float(w.sum())
        out.append(dict(mask=m, n=int(n), k=k, cx=float((x * w).sum() / ws), cy=float((y * w).sum() / ws),
                        x0=float(x.min()), x1=float(x.max()), y0=float(y.min()), y1=float(y.max()),
                        dtmax=float(g.dt[ii, jj, k].max()), mass=ws))
    return out


def _centre_score(c, x0, H):
    return c["mass"] * math.exp(-((c["cx"] - x0) / (0.08 * H)) ** 2)


def analyse_body(g, H):
    """Body features of a voxelised character standing on z=0, facing -Y (Blender), left = +X."""
    v = g.v
    nz = g.shape[2]
    F = {"H": H}
    thick = g.dt >= 0.6 * g.dt.max()
    ii, jj, kk = np.nonzero(thick)
    w = g.dt[ii, jj, kk]
    F["x0"] = float(((g.lo[0] + (ii + 0.5) * v) * w).sum() / w.sum())
    F["y0"] = float(((g.lo[1] + (jj + 0.5) * v) * w).sum() / w.sum())
    # torso section per slice: the core component (dt >= 2) that best covers the body centre
    torso = {}
    comps3 = {}
    for k in range(nz):
        cs = slice_comps(g, k, 2)
        if cs:
            best = max(cs, key=lambda c: _centre_score(c, F["x0"], H))
            if _centre_score(best, F["x0"], H) > 1.0:
                torso[k] = best
    F["torso"] = torso
    F["legs"] = track_legs(g, H, F, comps3)
    F["zc"] = F["legs"]["zc"] if F["legs"]["ok"] else None
    # x0 refined: torso centre between crotch and chest
    zc = F["legs"].get("zc") if F["legs"]["ok"] else 0.35 * H
    ks = [k for k in torso if zc + 0.05 * H < g.kz(k) < 0.7 * H]
    if ks:
        F["x0"] = float(np.median([torso[k]["cx"] for k in ks]))
    # shoulder top: where the torso(+arms) width collapses towards the neck
    ks = sorted(k for k in torso if 0.45 * H < g.kz(k) < 0.97 * H)
    F["zs"] = None
    if ks:
        wv = {k: torso[k]["x1"] - torso[k]["x0"] for k in ks}
        kmax = max(ks, key=lambda k: (wv[k], -k))
        F["w_sh"] = wv[kmax]
        for k in range(kmax, nz):
            if k not in torso or (torso[k]["x1"] - torso[k]["x0"]) < 0.6 * wv[kmax]:
                F["zs"] = g.kz(k) - 0.5 * v
                break
    if F["zs"] is None or F["zs"] < 0.5 * H:
        F["zs"] = None
    F["arms"] = track_arms(g, H, F, comps3)
    zas = [F["arms"][s]["za"] for s in "LR" if F["arms"][s]["ok"]]
    F["za"] = float(np.mean(zas)) if zas else None
    F["zt"] = head_top(g, H, F)
    F["feet"] = footprints(g, H, F)
    return F


def _comps3(g, k, cache):
    if k not in cache:
        cache[k] = slice_comps(g, k, 3)
    return cache[k]


def track_legs(g, H, F, cache):
    """Two leg sections followed up from the floor until they merge (crotch)."""
    nz = g.shape[2]
    k0 = g.zk(0.035 * H)
    res = {"ok": False}
    cs = [c for c in _comps3(g, k0, cache) if c["dtmax"] >= 4]
    if len(cs) < 2:
        res["why"] = "fewer than two foot sections at the floor (robe/skirt?)"
        return res
    cs.sort(key=lambda c: -c["mass"])
    a, b = cs[0], cs[1]
    if a["mass"] > 3.0 * b["mass"]:
        res["why"] = "foot sections very unequal (robe or prop on the floor?)"
        return res
    L, R = (a, b) if a["cx"] > b["cx"] else (b, a)
    tracks = {"L": [L], "R": [R]}
    end_k, how = None, None
    for k in range(k0 + 1, nz):
        cs = _comps3(g, k, cache)
        pick = {}
        for side in "LR":
            prev = dilate(tracks[side][-1]["mask"], diag=True)
            best, bo = None, 0
            for ci, c in enumerate(cs):
                o = int((c["mask"] & prev).sum())
                if o > bo:
                    best, bo = ci, o
            pick[side] = best
        if pick["L"] is None or pick["R"] is None:
            end_k, how = k, "track lost"
            break
        if pick["L"] == pick["R"]:
            end_k, how = k, "merged"
            break
        grew = any(cs[pick[s]]["n"] > 3.0 * np.median([c["n"] for c in tracks[s]]) and len(tracks[s]) > 5
                   for s in "LR")
        if grew:
            end_k, how = k, "section grew"
            break
        for s in "LR":
            tracks[s].append(cs[pick[s]])
    if end_k is None:
        res["why"] = "leg sections never merged"
        return res
    zc = g.kz(end_k) - 0.5 * g.v
    res.update(zc=zc, tracks=tracks, end=how)
    res["ok"] = zc > 0.15 * H
    if not res["ok"]:
        res["why"] = f"legs separate only below {zc:.2f} m (robe/long coat?)"
    return res


def _aspect(c, v):
    ex, ey = c["x1"] - c["x0"] + v, c["y1"] - c["y0"] + v
    return min(ex, ey) / max(ex, ey)


def track_arms(g, H, F, cache):
    """Arm sections lateral to the torso, tracked down from the armpit (A-pose). Every lateral
    section either continues a track (overlap with its previous section) or, when it touches the
    torso, starts one; the winner is the longest track of thick, roundish sections (shield
    plates and blades are thin, so they lose even when they are longer)."""
    out = {}
    x0 = F["x0"]
    ztop = F["zs"] if F["zs"] else 0.85 * H
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        active, done = [], []
        for k in range(g.zk(ztop), g.zk(0.2 * H), -1):
            cs = _comps3(g, k, cache)
            tor = max(cs, key=lambda c: _centre_score(c, x0, H)) if cs else None
            half = 0.5 * (tor["x1"] - tor["x0"]) if tor else 0.0
            lateral = [c for c in cs if c is not tor and sgn * (c["cx"] - x0) > 0.5 * half]
            used = set()
            nxt = []
            for t in active:
                prev = dilate(dilate(t[-1]["mask"], diag=True), diag=True)
                best, bo = None, 0
                for i, c in enumerate(lateral):
                    if i in used:
                        continue
                    o = int((c["mask"] & prev).sum())
                    if o > bo:
                        best, bo = i, o
                if best is not None and not (lateral[best]["n"] > 3.0 * np.median([c["n"] for c in t]) and len(t) > 4):
                    t.append(lateral[best])
                    used.add(best)
                    nxt.append(t)
                else:
                    done.append(t)
            for i, c in enumerate(lateral):
                if i in used or c["dtmax"] < 3 or c["n"] < 4:
                    continue
                gap = (c["x0"] - tor["x1"]) if sgn > 0 else (tor["x0"] - c["x1"])
                if gap < 0.08 * H:
                    nxt.append([c])
            active = nxt
        done += active

        def extent(t):
            p0 = np.array([t[0]["cx"], t[0]["cy"], g.kz(t[0]["k"])])
            p1 = np.array([t[-1]["cx"], t[-1]["cy"], g.kz(t[-1]["k"])])
            return float(np.linalg.norm(p1 - p0))

        def score(t):
            dt = float(np.mean([c["dtmax"] for c in t]))
            asp = float(np.mean([_aspect(c, g.v) for c in t]))
            return extent(t) * min(1.0, dt / 5.0) ** 2 * min(1.0, asp / 0.4)

        cands = [t for t in done if len(t) >= 4 and extent(t) > 0.06 * H]
        best = max(cands, key=lambda t: (score(t), -t[0]["k"])) if cands else []
        r = {"ok": bool(best)}
        if best:
            r["za"] = g.kz(best[0]["k"]) + 0.5 * g.v
            r["path"] = [np.array([c["cx"], c["cy"], g.kz(c["k"])]) for c in best]
            r["n"] = len(best)
            r["candidates"] = len(cands)
        else:
            r["why"] = "no arm section separated from the torso (arms touching the body or T-pose)"
        out[side] = r
    return out


def head_top(g, H, F):
    """Top of the head on the vertical head axis (ignores plumes/crests off the axis)."""
    zs = F["zs"] or 0.8 * H
    torso = F["torso"]
    ks = [k for k in torso if zs + 0.03 * H < g.kz(k) < zs + 0.12 * H]
    if not ks:
        return None
    hx = float(np.median([torso[k]["cx"] for k in ks]))
    hy = float(np.median([torso[k]["cy"] for k in ks]))
    F["head_axis"] = (hx, hy)
    i0, j0 = g.index([hx, hy, 0])[:2]
    r = max(1, int(round(0.03 * H / g.v)))
    col = g.solid[max(0, i0 - r):i0 + r + 1, max(0, j0 - r):j0 + r + 1, :].any(axis=(0, 1))
    k = g.zk(zs)
    while k + 1 < g.shape[2] and col[k + 1]:
        k += 1
    return g.kz(k) + 0.5 * g.v


def footprints(g, H, F):
    """Per-foot sole extents (solid voxels below 3.5 % of height), split between the leg tracks."""
    legs = F["legs"]
    if "tracks" not in legs:
        return None
    xl, xr = legs["tracks"]["L"][0]["cx"], legs["tracks"]["R"][0]["cx"]
    xm = 0.5 * (xl + xr)
    ks = g.zk(0.035 * H)
    sub = g.solid[:, :, :ks + 1].any(axis=2)
    ii, jj = np.nonzero(sub)
    x = g.lo[0] + (ii + 0.5) * g.v
    y = g.lo[1] + (jj + 0.5) * g.v
    out = {}
    for side, sel in (("L", x > xm), ("R", x <= xm)):
        if sel.sum() < 4:
            return None
        xs, ys = x[sel], y[sel]
        out[side] = dict(x0=float(np.percentile(xs, 2)), x1=float(np.percentile(xs, 98)),
                         y0=float(np.percentile(ys, 2)), y1=float(np.percentile(ys, 98)))
    return out


# =========================================================================== skeleton roles

def bone_roles(names, parents):
    """Semantic role of every template bone from names + hierarchy. Roles: hips, trunk (spine,
    neck, head and their leaves, clavicles, upper-arm joints), forearm/hand chain, leg chain."""
    children = {n: [c for c in names if parents[c] == n] for n in names}

    def low(n):
        return n.split(":")[-1].lower().replace("_", "").replace(".", "")

    def side(n):
        ln = n.split(":")[-1].lower()
        if ln.startswith("left") or ln.endswith(("_l", ".l", "left")) or ln.startswith("l_"):
            return "L"
        if ln.startswith("right") or ln.endswith(("_r", ".r", "right")) or ln.startswith("r_"):
            return "R"
        return None

    roles = {}
    hips = next((n for n in names if low(n) in ("hips", "hip", "pelvis")), None)
    if hips is None:
        hips = next(n for n in names if parents[n] is None)
    roles[hips] = ("hips", None, 0)
    for n in names:
        s = side(n)
        ln = low(n)
        if s is None:
            continue
        if any(t in ln for t in ("upleg", "thigh", "upperleg")):
            chain = [n]
            while children[chain[-1]]:
                chain.append(children[chain[-1]][0])
            for i, b in enumerate(chain):
                roles[b] = ("leg", s, i)          # 0 thigh 1 shin 2 foot 3 toe 4+ ends
        elif ln.endswith(("forearm", "lowerarm")) or "forearm" in ln or "lowerarm" in ln:
            chain = [n]
            stack = list(children[n])
            while stack:
                b = stack.pop(0)
                chain.append(b)
                stack.extend(children[b])
            for i, b in enumerate(chain):
                roles[b] = ("arm", s, min(i, 2) if i < 2 else 2)   # 0 elbow 1 wrist 2+ hand subtree
            # the parent of the forearm is the upper arm (shoulder joint): trunk-relative
    for n in names:
        if n not in roles:
            roles[n] = ("trunk", side(n), 0)
    # hand subtree index: 1 for the hand itself, 2 for fingers/ends
    return roles


# =========================================================================== template + calibration

def mesh_arrays(objs):
    Vs, Fs, off = [], [], 0
    for o in objs:
        me = o.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        m = np.array(o.matrix_world)
        co = co @ m[:3, :3].T + m[:3, 3]
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", t)
        Vs.append(co)
        Fs.append(t.reshape(-1, 3) + off)
        off += n
    return np.concatenate(Vs), np.concatenate(Fs)


def is_helper_mesh(o):
    return o.type == "MESH" and (o.name.lower().startswith(("icosphere", "widget", "wgt", "bone_shape"))
                                 or len(o.data.polygons) == 0)


def load_template(path):
    vc.reset_scene()
    objs = vc.import_glb(path)
    arms = [o for o in objs if o.type == "ARMATURE"]
    if not arms:
        raise SystemExit(f"template has no armature: {path}")
    arm = max(arms, key=lambda a: len(a.data.bones))
    meshes = [o for o in objs if o.type == "MESH" and not is_helper_mesh(o)
              and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    mw = arm.matrix_world
    order = [b.name for b in vc.bones_in_hierarchy_order(arm)]
    T = {"path": os.path.abspath(path), "names": order,
         "parents": {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones},
         "joints": {b.name: np.array(mw @ b.head_local) for b in arm.data.bones},
         "rot": {b.name: (mw @ b.matrix_local).to_3x3().normalized() for b in arm.data.bones},
         "deform": {b.name: b.use_deform for b in arm.data.bones}}
    yaw = vc.lateral_yaw(arm) or 0.0
    if meshes:
        T["V"], T["F"] = mesh_arrays(meshes)
    if abs(yaw) > math.radians(1.0):
        # template not facing glTF +Z: turn its data so it does
        R = Matrix.Rotation(-yaw, 3, "Z")
        Rn = np.array(R)
        T["joints"] = {k: Rn @ v for k, v in T["joints"].items()}
        T["rot"] = {k: R @ m for k, m in T["rot"].items()}
        if "V" in T:
            T["V"] = T["V"] @ Rn.T
        vc.warn(f"template faces {math.degrees(yaw):.1f} deg away from +Z; turned for fitting")
    if "V" in T:
        lo, hi = T["V"].min(0), T["V"].max(0)
        T["height"] = float(hi[2] - lo[2])
        T["floor"] = float(lo[2])
    else:
        zs = [v[2] for v in T["joints"].values()]
        T["floor"] = min(zs) - 0.03 * (max(zs) - min(zs))
        T["height"] = (max(zs) - T["floor"]) * 1.06
    T["roles"] = bone_roles(order, T["parents"])
    return T


KNOTS = ("zc", "za", "zs", "zt")


def knots_of(F):
    return {k: F.get(k) for k in KNOTS}


def zmap_fn(Ft, Fg):
    """Piecewise-linear map template height -> target height through the detected feature levels
    (ground, crotch, armpit, shoulder top, head top, top). Missing target levels are estimated by
    the map through the levels that were found (template proportions scaled per region)."""
    Ht, Hg = Ft["H"], Fg["H"]
    pairs = [(0.0, 0.0)] + [(Ft[k], Fg[k]) for k in KNOTS if Ft.get(k) is not None and Fg.get(k) is not None] \
        + [(Ht, Hg)]
    pairs.sort()
    xs = np.array([p[0] for p in pairs])
    ys = np.array([p[1] for p in pairs])
    keep = np.concatenate([[True], np.diff(xs) > 1e-6])
    xs, ys = xs[keep], ys[keep]
    ys = np.maximum.accumulate(ys)
    return lambda z: float(np.interp(z, xs, ys, left=z * Hg / Ht, right=Hg + (z - Ht) * Hg / Ht))


def torso_at(F, g, z):
    torso = F["torso"]
    k = g.zk(z)
    if k in torso:
        return torso[k]
    if not torso:
        return None
    kk = min(torso, key=lambda q: (abs(q - k), q))
    return torso[kk]


def leg_line(F, g, side):
    tr = F["legs"]["tracks"][side]
    zc = F["legs"]["zc"]
    pts = [(g.kz(c["k"]), c["cx"], c["cy"]) for c in tr if 0.45 * zc <= g.kz(c["k"]) <= 0.97 * zc]
    if len(pts) < 3:
        pts = [(g.kz(c["k"]), c["cx"], c["cy"]) for c in tr]
    P = np.array(pts)
    A = np.stack([P[:, 0], np.ones(len(P))], 1)
    cx = np.linalg.lstsq(A, P[:, 1], rcond=None)[0]
    cy = np.linalg.lstsq(A, P[:, 2], rcond=None)[0]
    return lambda z: (cx[0] * z + cx[1], cy[0] * z + cy[1])


def leg_section(F, g, side, z):
    tr = F["legs"]["tracks"][side]
    k = g.zk(z)
    return min(tr, key=lambda c: (abs(c["k"] - k), c["k"]))


def leg_width(F, side):
    tr = F["legs"]["tracks"][side]
    return float(np.median([c["x1"] - c["x0"] for c in tr]))


def arm_path(F, side, S):
    pts = [np.asarray(S)] + list(F["arms"][side]["path"])
    seg = np.linalg.norm(np.diff(np.array(pts), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    return np.array(pts), cum


def point_on_path(P, cum, s):
    s = float(np.clip(s, 0, cum[-1]))
    i = int(np.searchsorted(cum, s, side="right") - 1)
    i = min(max(i, 0), len(P) - 2)
    t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return P[i] + t * (P[i + 1] - P[i])


def project_on_path(P, cum, q):
    best = (1e9, 0.0)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        ab = b - a
        t = float(np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1))
        d = float(np.linalg.norm(a + t * ab - q))
        if d < best[0]:
            best = (d, cum[i] + t * (cum[i + 1] - cum[i]))
    return best[1]


def _frac(v, a, b):
    return (v - a) / (b - a) if abs(b - a) > 1e-9 else 0.5


def calibrate(T, Ft, gt):
    """Express each template joint relative to the template mesh's features."""
    J = T["joints"]
    roles = T["roles"]
    C = {}
    legs_ok = Ft["legs"]["ok"]
    for n in T["names"]:
        role, side, idx = roles[n]
        p = J[n]
        c = {"role": role, "side": side, "idx": idx}
        tc = torso_at(Ft, gt, p[2])
        c["z"] = float(p[2])
        c["trunk"] = dict(dx=float(_frac(p[0] - tc["cx"], 0, tc["x1"] - tc["x0"])),
                          ty=float(_frac(p[1], tc["y0"], tc["y1"])))
        if role == "leg" and legs_ok:
            if idx == 0:
                lx, ly = leg_line(Ft, gt, side)(p[2])
                w = leg_width(Ft, side)
                c["leg"] = dict(mode="line", dx=float((p[0] - lx) / w), dy=float((p[1] - ly) / w))
            elif idx in (1, 2):
                sc = leg_section(Ft, gt, side, p[2])
                c["leg"] = dict(mode="section", tx=float(_frac(p[0], sc["x0"], sc["x1"])),
                                ty=float(_frac(p[1], sc["y0"], sc["y1"])))
            elif idx == 3 and Ft["feet"]:
                fp = Ft["feet"][side]
                c["leg"] = dict(mode="foot", tx=float(_frac(p[0], fp["x0"], fp["x1"])),
                                ty=float(_frac(p[1], fp["y0"], fp["y1"])))
        if role == "arm" and idx in (0, 1) and Ft["arms"][side]["ok"]:
            up = T["parents"][n] if idx == 0 else T["parents"][T["parents"][n]]
            P, cum = arm_path(Ft, side, J[up])
            c["arm"] = dict(frac=float(project_on_path(P, cum, p) / cum[-1]), length=float(cum[-1]),
                            shoulder=up)
        C[n] = c
    # symmetrise left/right coefficients (mirror x-like terms)
    for n, c in C.items():
        if c["side"] != "L":
            continue
        m = mirror_name(n, C)
        if m is None:
            continue
        cm = C[m]
        for key in ("trunk", "leg", "arm"):
            if key in c and key in cm and c[key].get("mode") == cm[key].get("mode"):
                for f in list(c[key]):
                    if f in ("mode", "shoulder"):
                        continue
                    a, b = c[key][f], cm[key][f]
                    if key == "trunk" and f == "dx":
                        avg = 0.5 * (a - b)
                        c[key][f], cm[key][f] = avg, -avg
                    elif key == "leg" and f in ("dx",):
                        avg = 0.5 * (a - b)
                        c[key][f], cm[key][f] = avg, -avg
                    elif key == "leg" and f == "tx":
                        avg = 0.5 * (a + (1 - b))
                        c[key][f], cm[key][f] = avg, 1 - avg
                    else:
                        avg = 0.5 * (a + b)
                        c[key][f], cm[key][f] = avg, avg
        za, zb = c["z"], cm["z"]
        c["z"] = cm["z"] = 0.5 * (za + zb)
    return C


def mirror_name(n, names):
    for a, b in (("Left", "Right"), ("left", "right"), ("_L", "_R"), (".L", ".R"), ("_l", "_r"), (".l", ".r"),
                 ("L_", "R_"), ("l_", "r_")):
        if a in n:
            m = n.replace(a, b, 1)
            if m in names:
                return m
    return None


def solve_joints(T, Ft, gt, C, Fg, g):
    """Target joint positions (Blender space) + where each one came from."""
    zmap = zmap_fn(Ft, Fg)
    Hs = Fg["H"] / Ft["H"]
    J, src = {}, {}
    legs_ok = Fg["legs"]["ok"] and Ft["legs"]["ok"]
    for n in T["names"]:
        c = C[n]
        role, side, idx = c["role"], c["side"], c["idx"]
        z = zmap(c["z"])
        tc = torso_at(Fg, g, z)
        tr = c["trunk"]
        trunk_p = np.array([tc["cx"] + tr["dx"] * (tc["x1"] - tc["x0"]), tc["y0"] + tr["ty"] * (tc["y1"] - tc["y0"]), z])
        if role in ("hips", "trunk"):
            par = T["parents"][n]
            if _is_leaf_marker(n) and par in J and Ft.get("zt") and Fg.get("zt") and "head_axis" in Fg:
                # head end / face markers: template offset in the head's frame (parent joint -> head top)
                a = np.array([*Ft["head_axis"], Ft["zt"]]) - T["joints"][par]
                b = np.array([*Fg["head_axis"], Fg["zt"]]) - J[par]
                if np.linalg.norm(a) > 1e-6 and np.linalg.norm(b) > 1e-6:
                    R = np.array(Vector(a).rotation_difference(Vector(b)).to_matrix())
                    k = np.linalg.norm(b) / np.linalg.norm(a)
                    J[n], src[n] = J[par] + R @ (T["joints"][n] - T["joints"][par]) * k, "head-frame"
                    continue
            J[n], src[n] = trunk_p, "torso-section"
            continue
        if role == "leg":
            if legs_ok and "leg" in c:
                L = c["leg"]
                if L["mode"] == "line":
                    lx, ly = leg_line(Fg, g, side)(z)
                    w = leg_width(Fg, side)
                    J[n], src[n] = np.array([lx + L["dx"] * w, ly + L["dy"] * w, z]), "leg-axis"
                    continue
                if L["mode"] == "section":
                    sc = leg_section(Fg, g, side, z)
                    J[n] = np.array([sc["x0"] + L["tx"] * (sc["x1"] - sc["x0"]),
                                     sc["y0"] + L["ty"] * (sc["y1"] - sc["y0"]), z])
                    src[n] = "leg-section"
                    continue
                if L["mode"] == "foot" and Fg["feet"]:
                    fp = Fg["feet"][side]
                    J[n] = np.array([fp["x0"] + L["tx"] * (fp["x1"] - fp["x0"]),
                                     fp["y0"] + L["ty"] * (fp["y1"] - fp["y0"]), z])
                    src[n] = "footprint"
                    continue
            # fallback: template offset from the parent joint, scaled by the hip section
            par = T["parents"][n]
            if idx == 0 or par not in J:
                J[n], src[n] = trunk_p, "fallback:torso-proportion"
            else:
                d = T["joints"][n] - T["joints"][par]
                th = T["joints"][next(b for b in T["names"] if C[b]["role"] == "hips")][2]
                wt = float(np.clip(_torso_width_ratio(Ft, gt, Fg, g, th, zmap(th)) / Hs, 0.6, 1.6)) * Hs
                J[n] = J[par] + np.array([d[0] * wt, d[1] * Hs, 0.0])
                J[n][2] = z
                src[n] = "fallback:template-leg"
            continue
        if role == "arm":
            ar = Fg["arms"].get(side, {})
            if "arm" in c and ar.get("ok"):
                A = c["arm"]
                S = J[A["shoulder"]]
                P, cum = arm_path(Fg, side, S)
                L = cum[-1]
                Lexp = A["length"] * Hs
                note = ""
                if L > 1.35 * Lexp:  # arm track ran into a weapon: cut it
                    L, note = 1.35 * Lexp, " (path clipped)"
                J[n], src[n] = point_on_path(P, cum, A["frac"] * L), "arm-path" + note
                continue
            par = T["parents"][n]
            d = T["joints"][n] - T["joints"][par]
            J[n] = J[par] + d * Hs
            src[n] = "fallback:template-arm" if idx < 2 else "template-offset"
            continue
    # leaves that hang off arms / legs beyond the modelled joints keep template offsets
    return J, src


def _torso_width_ratio(Ft, gt, Fg, g, zt_, zg):
    a = torso_at(Ft, gt, zt_)
    b = torso_at(Fg, g, zg)
    return (b["x1"] - b["x0"]) / max(a["x1"] - a["x0"], 1e-6)


# =========================================================================== scene helpers

def import_static(path, name):
    objs = vc.import_glb(path)
    meshes = [o for o in objs if o.type == "MESH" and not is_helper_mesh(o)]
    if not meshes:
        raise SystemExit(f"no mesh in {path}")
    arms = [o for o in objs if o.type == "ARMATURE"]
    for o in meshes:
        if o.data.users > 1:
            o.data = o.data.copy()
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
        for m in list(o.modifiers):
            o.modifiers.remove(m)
        o.vertex_groups.clear()
        if o.data.shape_keys:
            o.shape_key_clear()
    if arms:
        vc.warn(f"input already has an armature ({len(arms[0].data.bones)} bones): discarded, re-rigging")
    vc.delete_objects([o for o in objs if o not in meshes])
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    if len(meshes) > 1:
        vc.select_only(meshes, meshes[0])
        with vc.stdout_to_stderr():
            bpy.ops.object.join()
    body = meshes[0]
    body.name = name
    body.data.name = name
    bm = bmesh.new()
    bm.from_mesh(body.data)
    co = np.array([v.co[:] for v in bm.verts])
    diag = float(np.linalg.norm(co.max(0) - co.min(0)))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5 * diag)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return body


def normalise_body(body, facing, yaw, height):
    lo, hi = vc.world_bounds([body])
    R = Matrix.Rotation(math.radians(FACING_TO_PZ[facing] + yaw), 4, "Z")
    body.data.transform(R)
    lo, hi = vc.world_bounds([body])
    h0 = hi.z - lo.z
    s = height / max(h0, 1e-9) if height > 0 else 1.0
    M = Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    body.data.transform(M)
    body.data.update()
    return {"source_height": round(h0, 5), "scale": round(s, 6), "yaw_deg": FACING_TO_PZ[facing] + yaw}


def detect_forward(g, H):
    """Forward direction from the feet: the two shin sections define the left/right axis, the soles
    stick out forward of the shins (toes). Returns (yaw_deg of forward relative to -Y, CCW from
    above; confidence 0..1) or (None, 0)."""
    for zf in (0.22, 0.18, 0.28, 0.14):
        k = g.zk(zf * H)
        cs = [c for c in slice_comps(g, k, 3) if c["dtmax"] >= 3]
        if len(cs) < 2:
            continue
        cs.sort(key=lambda c: -c["mass"])
        a, b = cs[0], cs[1]
        if a["mass"] > 3.0 * b["mass"]:
            continue
        pa, pb = np.array([a["cx"], a["cy"]]), np.array([b["cx"], b["cy"]])
        lat = pb - pa
        if np.linalg.norm(lat) < 0.05 * H:
            continue
        lat /= np.linalg.norm(lat)
        perp = np.array([-lat[1], lat[0]])
        ks = g.zk(0.035 * H)
        ii, jj = np.nonzero(g.solid[:, :, :ks + 1].any(axis=2))
        P = np.stack([g.lo[0] + (ii + 0.5) * g.v, g.lo[1] + (jj + 0.5) * g.v], 1)
        if len(P) < 8:
            continue
        near_a = np.linalg.norm(P - pa, axis=1) < np.linalg.norm(P - pb, axis=1)
        offs = []
        for sel, c in ((near_a, pa), (~near_a, pb)):
            if sel.sum() >= 4:
                offs.append(float(((P[sel] - c) @ perp).mean()))
        if not offs:
            continue
        o = float(np.mean(offs))
        fwd = perp * np.sign(o)
        conf = float(min(1.0, abs(o) / (0.03 * H)))
        yaw = math.degrees(math.atan2(fwd[0], -fwd[1]))  # 0 = facing -Y (glTF +Z), CCW from above
        return yaw, conf
    return None, 0.0


def body_arrays(body):
    return mesh_arrays([body])


def main_child(n, T):
    kids = [c for c in T["names"] if T["parents"][c] == n]
    if not kids:
        return None
    role = T["roles"]
    plain = [c for c in kids if role[c][1] is None and not _is_leaf_marker(c)]
    if plain:
        return plain[0]
    same = [c for c in kids if not _is_leaf_marker(c)]
    return (same or kids)[0]


def _is_leaf_marker(n):
    ln = n.lower()
    return any(t in ln for t in ("end", "front", "nub", "_top", "tip"))


def skin_deform_bones(T):
    return [n for n in T["names"] if not _is_leaf_marker(n)]


def build_export_armature(T, J, name="Armature"):
    """Armature with the template's bones: same names/parents/rest orientations, heads at J."""
    ad = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(arm)
    vc.select_only([arm], arm)
    with vc.stdout_to_stderr():
        bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    H = max(v[2] for v in J.values())
    for n in T["names"]:
        eb = ad.edit_bones.new(n)
        kid = main_child(n, T)
        L = float(np.linalg.norm(J[kid] - J[n])) if kid else 0.0
        if L < 0.02 * H:
            L = 0.05 * H
        eb.head = (0, 0, 0)
        eb.tail = (0, L, 0)
        M = T["rot"][n].to_4x4()
        M.translation = Vector(J[n])
        eb.matrix = M
        ebs[n] = eb
    for n in T["names"]:
        p = T["parents"][n]
        if p:
            ebs[n].parent = ebs[p]
            ebs[n].use_connect = False
    with vc.stdout_to_stderr():
        bpy.ops.object.mode_set(mode="OBJECT")
    for b in ad.bones:
        b.use_deform = True
    return arm


def build_skin_armature(T, J, ends):
    """Helper armature for bone heat: deform bones run joint -> main child joint (or a fitted end)."""
    ad = bpy.data.armatures.new("vc_skin_arm")
    arm = bpy.data.objects.new("vc_skin_arm", ad)
    bpy.context.scene.collection.objects.link(arm)
    vc.select_only([arm], arm)
    with vc.stdout_to_stderr():
        bpy.ops.object.mode_set(mode="EDIT")
    deform = set(skin_deform_bones(T))
    H = max(v[2] for v in J.values())
    ebs = {}
    for n in T["names"]:
        eb = ad.edit_bones.new(n)
        head = Vector(J[n])
        kid = main_child(n, T)
        if n in ends:
            tail = Vector(ends[n])
        elif kid is not None and np.linalg.norm(J[kid] - J[n]) > 0.01 * H:
            tail = Vector(J[kid])
        else:
            par = T["parents"][n]
            d = (Vector(J[n]) - Vector(J[par])) if par else Vector((0, 0, 1))
            if d.length < 1e-6:
                d = Vector((0, 0, 1))
            tail = head + d.normalized() * 0.04 * H
        if (tail - head).length < 0.005 * H:
            tail = head + Vector((0, 0, 0.01 * H))
        eb.head, eb.tail = head, tail
        ebs[n] = eb
    for n in T["names"]:
        p = T["parents"][n]
        if p:
            ebs[n].parent = ebs[p]
    with vc.stdout_to_stderr():
        bpy.ops.object.mode_set(mode="OBJECT")
    for b in ad.bones:
        b.use_deform = b.name in deform
    return arm


# =========================================================================== skinning

def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def envelope_weights(P, segs, k=3, power=4.0, x0=0.0, sides=None):
    """Nearest-bone-segment weights: w ~ 1/d^power over the k nearest segments (same body side)."""
    names = list(segs)
    D = np.stack([seg_dist(P, *segs[n]) for n in names], 1)
    if sides:
        H = max(float(P[:, 2].max()), 1e-6)
        for j, n in enumerate(names):
            s = sides.get(n)
            if s == "L":
                D[P[:, 0] < x0 - 0.02 * H, j] += 10.0
            elif s == "R":
                D[P[:, 0] > x0 + 0.02 * H, j] += 10.0
    order = np.argsort(D, axis=1)[:, :k]
    d = np.take_along_axis(D, order, 1)
    w = 1.0 / np.maximum(d, 1e-4) ** power
    w /= w.sum(1, keepdims=True)
    return names, order, w


def set_weights_rows(obj, rows, names, order, w):
    """Replace the weights of vertices `rows` with (names[order], w)."""
    vgs = {n: (obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)) for n in names}
    rows = list(map(int, rows))
    for vg in obj.vertex_groups:
        vg.remove(rows)
    for r_i, vi in enumerate(rows):
        for j in range(order.shape[1]):
            if w[r_i, j] > 1e-4:
                vgs[names[order[r_i, j]]].add([vi], float(w[r_i, j]), "REPLACE")


def bone_heat_proxy(body, skin_arm, voxel):
    """Voxel-remeshed copy of body, bound with automatic weights. Returns (proxy, info)."""
    t0 = time.time()
    proxy = body.copy()
    proxy.data = body.data.copy()
    proxy.name = "vc_proxy"
    bpy.context.scene.collection.objects.link(proxy)
    for m in list(proxy.modifiers):
        proxy.modifiers.remove(m)
    proxy.vertex_groups.clear()
    rm = proxy.modifiers.new("vox", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    vc.select_only([proxy], proxy)
    with vc.stdout_to_stderr():
        bpy.ops.object.modifier_apply(modifier="vox")
    # bone heat fails for the WHOLE mesh when a loose piece contains no bone (sword tips, plume
    # bits): keep only big islands (small ones get weights from the transfer / prop binding)
    inv, counts = mesh_islands(proxy)
    small = counts < max(0.05 * counts.sum(), 1)
    small[int(np.argmax(counts))] = False
    removed = int(counts[small].sum())
    if removed:
        _delete_verts(proxy, np.nonzero(small[inv])[0])
    t1 = time.time()
    vc.select_only([proxy, skin_arm], skin_arm)
    with vc.stdout_to_stderr():
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    t2 = time.time()
    st = vc.weight_stats(proxy)
    info = {"proxy_verts": len(proxy.data.vertices), "proxy_islands_dropped": int(small.sum()),
            "proxy_verts_dropped": removed, "proxy_unweighted": st["unweighted_verts"],
            "remesh_s": round(t1 - t0, 2), "heat_s": round(t2 - t1, 2)}
    return proxy, info


def _delete_verts(obj, rows):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[int(i)] for i in rows], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def transfer_weights(body, proxy, names):
    for n in names:
        if body.vertex_groups.get(n) is None:
            body.vertex_groups.new(name=n)
    dt = body.modifiers.new("vc_dt", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    vc.select_only([body], body)
    with vc.stdout_to_stderr():
        bpy.ops.object.modifier_apply(modifier="vc_dt")


def vertex_weight_matrix(obj, names):
    idx = {obj.vertex_groups[n].index: j for j, n in enumerate(names) if obj.vertex_groups.get(n)}
    W = np.zeros((len(obj.data.vertices), len(names)), np.float32)
    for v in obj.data.vertices:
        for gr in v.groups:
            j = idx.get(gr.group)
            if j is not None:
                W[v.index, j] = gr.weight
    return W


def cleanup_weights(obj, limit=4, clean=0.01):
    vc.select_only([obj], obj)
    with vc.stdout_to_stderr():
        bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=clean, keep_single=True)
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=limit)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def mesh_islands(obj):
    me = obj.data
    n = len(me.vertices)
    e = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    lab = np.arange(n)
    if len(e):
        while True:
            la, lb = lab[e[:, 0]], lab[e[:, 1]]
            d = la != lb
            if not d.any():
                break
            np.minimum.at(lab, np.maximum(la[d], lb[d]), np.minimum(la[d], lb[d]))
            while True:
                nl = lab[lab]
                if np.array_equal(nl, lab):
                    break
                lab = nl
    uniq, inv, counts = np.unique(lab, return_inverse=True, return_counts=True)
    return inv, counts


def detect_props(g, Fg, J, T, body_P, islands):
    """Vertices of held props (thin or disconnected geometry touching only a hand/forearm).
    Returns {hand_bone: vertex index array}, info."""
    H = Fg["H"]
    v = g.v
    r = 3
    info = {}
    core = g.dt >= r + 1
    opened = core.copy()
    for i in range(r):
        opened = dilate(opened, diag=(i % 2 == 1))
    opened &= g.solid
    lab_o, sz_o = label_cc(opened, diag=False)
    main = lab_o == 0
    app = g.solid & ~main
    lab_a, sz_a = label_cc(app, diag=True)
    # arm regions (forearm + hand segments, swollen by the local arm radius)
    roles = T["roles"]
    seg_by_side = {}
    hand_bone = {}
    for n in T["names"]:
        role, side, idx = roles[n]
        if role == "arm" and idx in (0, 1):
            a = J[n]
            if idx == 1:  # hand: from the wrist to the fitted arm end
                ar = Fg["arms"].get(side, {})
                if ar.get("ok"):
                    b = ar["path"][-1]
                else:
                    b = J[n] + (J[n] - J[T["parents"][n]]) * 0.6
                hand_bone[side] = n
            else:  # forearm: only its distal third counts as "hand" (elbow pads are not props)
                kid = main_child(n, T)
                if kid is None:
                    continue
                b = J[kid]
                a = b + 0.35 * (a - b)
            seg_by_side.setdefault(side, []).append((a, b))
    if not seg_by_side:
        return {}, {"why": "no arm bones"}
    ii, jj, kk = np.nonzero(g.solid)
    C = g.center(np.stack([ii, jj, kk], 1))
    region = {}
    for side, segs in seg_by_side.items():
        d = np.min(np.stack([seg_dist(C, a, b) for a, b in segs], 1), axis=1)
        m = np.zeros(g.shape, bool)
        m[ii, jj, kk] = d < 0.075 * H
        region[side] = m
    body_near = dilate(main, diag=True)
    hand_contact = {s: dilate(region[s] & main, diag=True) for s in region}
    other_body = main.copy()
    for m in region.values():
        other_body &= ~m
    other_near = dilate(other_body, diag=True)
    solid_vox = int(g.solid.sum())
    prop_vox = {s: np.zeros(g.shape, bool) for s in seg_by_side}
    comps = []
    for ci, n in enumerate(sz_a):
        if n < 8:
            break
        m = lab_a == ci
        touch = {s: int((m & hand_contact[s]).sum()) for s in region}
        touch_other = int((m & other_near).sum())
        ext = g.center(np.argwhere(m))
        span = float(np.linalg.norm(ext.max(0) - ext.min(0)))
        entry = {"voxels": int(n), "span_m": round(span, 3), "touch_hand": touch, "touch_body": touch_other}
        side = max(sorted(touch), key=lambda s: touch[s]) if touch else None
        if side and touch[side] > 0:
            if n < 0.25 * solid_vox and span > 0.08 * H and touch[side] >= 0.5 * touch_other:
                prop_vox[side] |= m
                entry["prop_of"] = side
        elif not (m & body_near).any():
            entry["floating"] = True
            for s in sorted(seg_by_side):
                dmin = min(float(np.min(seg_dist(ext, a, b))) for a, b in seg_by_side[s])
                if dmin < 0.06 * H:
                    prop_vox[s] |= m
                    entry["prop_of"] = s
                    break
        comps.append(entry)
    info["appendages"] = comps[:12]
    out = {}
    vi = g.index(body_P)
    for s, m in prop_vox.items():
        if not m.any():
            continue
        # vertices whose voxel (or a 1-voxel neighbour) is prop, and not inside the main body
        mm = dilate(m, diag=True) & ~main
        sel = mm[vi[:, 0], vi[:, 1], vi[:, 2]]
        out[hand_bone[s]] = np.nonzero(sel)[0]
    # disconnected mesh islands near a hand
    inv, counts = islands
    if len(counts) > 1:
        mainisl = int(np.argmax(counts))
        for isl in range(len(counts)):
            if isl == mainisl or counts[isl] < 4:
                continue
            rows = np.nonzero(inv == isl)[0]
            P = body_P[rows]
            best = None
            for s, segs in seg_by_side.items():
                dh = np.min(np.stack([seg_dist(P, a, b) for a, b in segs], 1), axis=1)
                frac = float((dh < 0.06 * H).mean())
                if frac > 0.2 and (best is None or frac > best[1]):
                    best = (s, frac)
            if best:
                # only if the island is closer to the hand than to the torso axis
                s = best[0]
                out.setdefault(hand_bone[s], np.zeros(0, np.int64))
                out[hand_bone[s]] = np.union1d(out[hand_bone[s]], rows)
                info.setdefault("islands", []).append({"verts": int(len(rows)), "prop_of": s})
    info["prop_verts"] = {k: int(len(v)) for k, v in out.items()}
    return out, info


def skin(body, T, J, Fg, g, args, H):
    info = {}
    ends = {}
    roles = T["roles"]
    for n in T["names"]:
        role, side, idx = roles[n]
        if role == "arm" and idx == 1 and Fg["arms"].get(side, {}).get("ok"):
            e = Fg["arms"][side]["path"][-1]
            if np.linalg.norm(e - J[n]) > 0.02 * H:
                ends[n] = e
        if role == "leg" and idx == 3 and Fg.get("feet"):
            fp = Fg["feet"][side]
            ends[n] = np.array([J[n][0], fp["y0"], J[n][2]])
    skin_arm = build_skin_armature(T, J, ends)
    deform = skin_deform_bones(T)
    segs = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in skin_arm.data.bones if b.use_deform}
    sides = {n: roles[n][1] for n in deform}
    P, _ = body_arrays(body)
    method = args.weights
    if method == "heat":
        proxy, pinfo = bone_heat_proxy(body, skin_arm, args.voxel * H)
        info["proxy"] = pinfo
        if pinfo["proxy_unweighted"] > 0.02 * pinfo["proxy_verts"]:
            vc.warn(f"bone heat left {pinfo['proxy_unweighted']} proxy verts unweighted; envelope fallback there")
        transfer_weights(body, proxy, deform)
        vc.delete_objects([proxy])
    body.vertex_groups.active_index = 0
    for n in deform:
        if body.vertex_groups.get(n) is None:
            body.vertex_groups.new(name=n)
    W = vertex_weight_matrix(body, deform)
    unweighted = np.nonzero(W.sum(1) < 1e-3)[0] if method == "heat" else np.arange(len(P))
    info["method"] = method
    info["envelope_filled_verts"] = int(len(unweighted))
    if len(unweighted):
        names, order, w = envelope_weights(P[unweighted], segs, x0=Fg["x0"], sides=sides)
        set_weights_rows(body, unweighted, names, order, w)
    if not args.no_props:
        props, pinfo = detect_props(g, Fg, J, T, P, mesh_islands(body))
        info["props"] = pinfo
        for bone, rows in props.items():
            if len(rows):
                set_weights_rows(body, rows, [bone], np.zeros((len(rows), 1), np.int64), np.ones((len(rows), 1)))
    cleanup_weights(body)
    vc.delete_objects([skin_arm])
    return info


# =========================================================================== clips

def parse_clip(spec):
    if "=" not in spec:
        raise SystemExit(f"--clip expects NAME=FILE[:ACTION], got {spec!r}")
    name, rest = spec.split("=", 1)
    action = None
    if not os.path.isfile(rest) and ":" in rest:
        rest, action = rest.rsplit(":", 1)
    if not os.path.isfile(rest):
        raise SystemExit(f"clip file not found: {rest}")
    return name.strip(), rest, action


def lateral_bones(arm):
    pref = [("LeftUpLeg", "RightUpLeg"), ("LeftArm", "RightArm"), ("LeftShoulder", "RightShoulder")]
    pairs = [(a, b) for a, b in pref if a in arm.pose.bones and b in arm.pose.bones]
    if pairs:
        return pairs
    names = [b.name for b in arm.data.bones]
    return [(n, mirror_name(n, names)) for n in names if n.lower().startswith("left") and mirror_name(n, names)]


def bind_action(arm, act):
    """Make `act` the active action; channels it doesn't key are reset to rest (frame_set only
    overwrites keyed channels, so a previous clip's pose would leak into the evaluation)."""
    reset_pose(arm)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slot = vc.action_object_slot(act)
    if slot is not None:
        ad.action_slot = slot
    return ad


def clip_yaws(arm, act, frames):
    """Per-frame facing of the posed body (left/right axis of hips+shoulders), radians vs rest."""
    pairs = lateral_bones(arm)
    rest = Vector()
    for a, b in pairs:
        rest += arm.data.bones[a].head_local - arm.data.bones[b].head_local
    ry = math.atan2(rest.y, rest.x)
    scn = bpy.context.scene
    bind_action(arm, act)
    out = []
    for f in frames:
        scn.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        lat = Vector()
        for a, b in pairs:
            lat += arm.pose.bones[a].head - arm.pose.bones[b].head
        out.append((math.atan2(lat.y, lat.x) - ry, math.hypot(lat.x, lat.y)))
    return out


def remove_mean_yaw(arm, act, hips, max_frames=400):
    """Rotate the root bone about the vertical axis through its rest position by the clip's mean yaw."""
    a0, a1 = vc.action_range(act)
    frames = list(np.arange(math.floor(a0), math.ceil(a1) + 1, 1.0))
    if len(frames) > max_frames:
        frames = list(np.linspace(a0, a1, max_frames))
    ys = clip_yaws(arm, act, frames)
    sw = sum(w for _, w in ys) or 1.0
    mean = math.atan2(sum(math.sin(y) * w for y, w in ys) / sw, sum(math.cos(y) * w for y, w in ys) / sw)
    spread = max(abs(((y - mean + math.pi) % (2 * math.pi)) - math.pi) for y, _ in ys)
    res = {"mean_yaw_before_deg": round(math.degrees(mean), 2), "yaw_spread_deg": round(math.degrees(spread), 2)}
    pb = arm.pose.bones[hips]
    bone = arm.data.bones[hips]
    rest = bone.matrix_local.copy()
    pivot = bone.head_local.copy()
    pivot.z = 0.0
    res["_pivot"], res["_yaw"] = pivot, 0.0
    if abs(math.degrees(mean)) < 1.0:
        res["applied"] = False
        return res
    res["_yaw"] = -mean
    Rz = Matrix.Translation(pivot) @ Matrix.Rotation(-mean, 4, "Z") @ Matrix.Translation(-pivot)
    # sample the current keys, then rewrite location + quaternion for every key frame
    fcs = {}
    for fc in vc.action_fcurves(act):
        if fc.data_path.startswith(f'pose.bones["{hips}"].'):
            fcs[(fc.data_path.rsplit(".", 1)[-1], fc.array_index)] = fc
    key_frames = sorted({kp.co.x for fc in fcs.values() for kp in fc.keyframe_points}) or [a0, a1]

    def ev(prop, i, f, d):
        fc = fcs.get((prop, i))
        return fc.evaluate(f) if fc else d

    mode = pb.rotation_mode
    locs, quats = [], []
    for f in key_frames:
        loc = Vector([ev("location", i, f, 0.0) for i in range(3)])
        if mode == "QUATERNION":
            q = Quaternion([ev("rotation_quaternion", i, f, (1, 0, 0, 0)[i]) for i in range(4)]).normalized()
        else:
            from mathutils import Euler
            q = Euler([ev("rotation_euler", i, f, 0.0) for i in range(3)], mode).to_quaternion()
        scl = Vector([ev("scale", i, f, 1.0) for i in range(3)])
        B = Matrix.LocRotScale(loc, q, scl)
        Wm = Rz @ rest @ B
        B2 = rest.inverted() @ Wm
        l2, q2, _ = B2.decompose()
        locs.append(l2)
        quats.append(q2)
    for i in range(1, len(quats)):
        if quats[i - 1].dot(quats[i]) < 0:
            quats[i] = -quats[i]
    cb = None
    for c in vc.action_channelbags(act):
        cb = c
        break
    for fc in [fc for k, fc in fcs.items() if k[0] in ("rotation_euler", "rotation_axis_angle")]:
        cb.fcurves.remove(fc)
    pb.rotation_mode = "QUATERNION"
    for i in range(3):
        vc.fcurve_set_keys(cb, f'pose.bones["{hips}"].location', i, key_frames, [v[i] for v in locs], group=hips)
    for i in range(4):
        vc.fcurve_set_keys(cb, f'pose.bones["{hips}"].rotation_quaternion', i, key_frames, [q[i] for q in quats],
                           group=hips)
    after = clip_yaws(arm, act, frames)
    sw = sum(w for _, w in after) or 1.0
    m2 = math.atan2(sum(math.sin(y) * w for y, w in after) / sw, sum(math.cos(y) * w for y, w in after) / sw)
    res.update(applied=True, mean_yaw_after_deg=round(math.degrees(m2), 2))
    return res


def leg_chains(arm):
    """{side: (thigh, shin, foot)} from the armature's names/hierarchy."""
    names = [b.name for b in arm.data.bones]
    roles = bone_roles(names, {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones})
    out = {}
    for side in "LR":
        ch = sorted((idx, n) for n, (role, s, idx) in roles.items() if role == "leg" and s == side and idx <= 2)
        if [i for i, _ in ch] == [0, 1, 2]:
            out[side] = tuple(n for _, n in ch)
    return out if len(out) == 2 else {}


def sample_source_feet(src, act, legs, frames, hips):
    """World positions of the source ankles and hips per frame (+ rest)."""
    mw = src.matrix_world
    bind_action(src, act)
    scn = bpy.context.scene
    data = {"rest": {s: mw @ src.data.bones[ch[2]].head_local for s, ch in legs.items()},
            "hips_rest": mw @ src.data.bones[hips].head_local, "frames": frames, "ankle": {s: [] for s in legs},
            "hips": []}
    for f in frames:
        scn.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        for s, ch in legs.items():
            data["ankle"][s].append(mw @ src.pose.bones[ch[2]].head)
        data["hips"].append(mw @ src.pose.bones[hips].head)
    src.animation_data.action = None
    return data


def foot_ik(arm, act, legs, S, ratio, yaw_align, mode, yaw_fix, pivot):
    """Two-bone IK per leg so each ankle follows the source ankle's motion (scaled by the leg ratio,
    relative to its own rest position): a planted source foot stays planted on a body with other
    proportions. The knee keeps its bend plane, the foot keeps its world orientation."""
    Ya = Matrix.Rotation(yaw_align, 3, "Z")
    Yf = Matrix.Rotation(yaw_fix, 3, "Z")
    bones = arm.data.bones
    rest_rel = {n: (bones[n].parent.matrix_local.inverted() @ bones[n].matrix_local) for ch in legs.values() for n in ch}
    frames = S["frames"]
    q_out = {n: [] for ch in legs.values() for n in ch}
    bind_action(arm, act)
    scn = bpy.context.scene
    moved, clamped = 0.0, 0
    for fi, f in enumerate(frames):
        scn.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        dh = S["hips"][fi] - S["hips_rest"]
        sub = Vector((0, 0, 0)) if mode == "full" else (Vector((dh.x, dh.y, 0)) if mode == "vertical" else dh)
        for side, (up, lo, ft) in legs.items():
            pu, pl, pf = arm.pose.bones[up], arm.pose.bones[lo], arm.pose.bones[ft]
            Mh = pu.parent.matrix.copy()
            Mu, Ml, Mf = pu.matrix.copy(), pl.matrix.copy(), pf.matrix.copy()
            Hp, K0, A0 = Mu.translation.copy(), Ml.translation.copy(), Mf.translation.copy()
            A_rest = bones[ft].head_local.copy()
            disp = Ya @ (S["ankle"][side][fi] - S["rest"][side] - sub) * ratio
            D = pivot + Yf @ (A_rest + disp - pivot)
            l1, l2 = (K0 - Hp).length, (A0 - K0).length
            dv = D - Hp
            d = dv.length
            dmin, dmax = abs(l1 - l2) + 1e-4, (l1 + l2) * 0.999
            if d > dmax or d < dmin:
                clamped += 1
                d = min(max(d, dmin), dmax)
            dn = dv.normalized() if dv.length > 1e-9 else (A0 - Hp).normalized()
            D = Hp + dn * d
            pole = (K0 - Hp) - dn * (K0 - Hp).dot(dn)
            if pole.length < 1e-6:
                pole = (K0 - (Hp + A0) * 0.5)
                pole = pole - dn * pole.dot(dn)
            pole = pole.normalized() if pole.length > 1e-9 else Vector((0, -1, 0))
            a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            K1 = Hp + dn * a + pole * h
            sw1 = (K0 - Hp).rotation_difference(K1 - Hp).to_matrix().to_4x4()
            Mu_n = Matrix.Translation(Hp) @ sw1 @ Matrix.Translation(-Hp) @ Mu
            follow = Mu_n @ Mu.inverted()
            Ml_f = follow @ Ml
            A1 = (follow @ Mf).translation
            sw2 = (A1 - K1).rotation_difference(D - K1).to_matrix().to_4x4()
            Ml_n = Matrix.Translation(K1) @ sw2 @ Matrix.Translation(-K1) @ Ml_f
            Mf_n = Mf.to_3x3().to_4x4()
            Mf_n.translation = (Ml_n @ Ml.inverted() @ Mf).translation
            moved = max(moved, (D - A0).length)
            for n, M, Mp in ((up, Mu_n, Mh), (lo, Ml_n, Mu_n), (ft, Mf_n, Ml_n)):
                B = (Mp @ rest_rel[n]).inverted() @ M
                q_out[n].append(B.to_quaternion().normalized())
    cb = vc.action_channelbags(act)[0]
    for n, qs in q_out.items():
        for i in range(1, len(qs)):
            if qs[i - 1].dot(qs[i]) < 0:
                qs[i] = -qs[i]
        arm.pose.bones[n].rotation_mode = "QUATERNION"
        for i in range(4):
            vc.fcurve_set_keys(cb, f'pose.bones["{n}"].rotation_quaternion', i, frames, [q[i] for q in qs], group=n)
    return {"max_correction_m": round(moved, 4), "frames_out_of_reach": clamped}


def transfer_clips(arm, clips, args):
    hm = dict(DEFAULT_HIPS_MODE)
    for s in args.hips_mode:
        k, _, v = s.partition("=")
        if v not in ("vertical", "full", "none"):
            raise SystemExit(f"--hips-mode {s!r}: mode must be vertical, full or none")
        hm[k] = v
    hips = vc.find_hips(arm).name
    out, stash = [], []
    for name, path, want in clips:
        before_a = set(bpy.data.actions)
        objs = vc.import_glb(path)
        srcs = [o for o in objs if o.type == "ARMATURE"]
        if not srcs:
            raise SystemExit(f"{path}: no armature")
        src = max(srcs, key=lambda a: len(a.data.bones))
        acts = [a for a in bpy.data.actions if a not in before_a and vc.action_bone_names(a)]
        if not acts:
            raise SystemExit(f"{path}: no animation")
        if want:
            sel = [a for a in acts if a.name == want or a.name.startswith(want)]
            if not sel:
                raise SystemExit(f"{path}: no action {want!r} (have {[a.name for a in acts]})")
            src_act = sel[0]
        else:
            src_act = max(acts, key=lambda a: vc.action_range(a)[1] - vc.action_range(a)[0])
        mode = hm.get(name, "vertical")
        new, slot, info = vc.retarget_action(src, src_act, arm, "__clip_" + name, hips_mode=mode)
        entry = {"name": name, "file": os.path.abspath(path), "source_action": src_act.name, "hips_mode": mode,
                 "frames": info["frames"], "bones_matched": info["bones_matched"], "leg_ratio": info["leg_ratio"],
                 "unmatched_target_bones": info["unmatched_target_bones"]}
        legs = leg_chains(arm)
        feet_src = None
        if legs and not args.no_foot_ik and all(all(b in src.pose.bones for b in ch) for ch in legs.values()):
            frames = sorted({kp.co.x for fc in vc.action_fcurves(new) for kp in fc.keyframe_points})
            feet_src = sample_source_feet(src, src_act, legs, frames, info["hips"][0])
        for a in [a for a in bpy.data.actions if a not in before_a and a is not new]:
            bpy.data.actions.remove(a)
        vc.delete_objects(objs)
        fix = {"_yaw": 0.0, "_pivot": Vector((0, 0, 0))}
        if not args.no_face_fix:
            fix = remove_mean_yaw(arm, new, hips)
            entry["facing_fix"] = {k: v for k, v in fix.items() if not k.startswith("_")}
        if feet_src is not None:
            entry["foot_ik"] = foot_ik(arm, new, legs, feet_src, info["leg_ratio"], math.radians(info["yaw_align_deg"]),
                                       mode, fix["_yaw"], fix["_pivot"])
        out.append(entry)
        stash.append((new, slot))
    for a, _ in stash:
        a.name = a.name[len("__clip_"):]
    return out, stash


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)


# =========================================================================== QA

def to_gltf(p):
    return [round(float(p[0]), 4), round(float(p[2]), 4), round(float(-p[1]), 4)]


def from_gltf(p):
    return np.array([p[0], -p[2], p[1]], dtype=np.float64)


def joint_error(J, ref):
    names = [n for n in J if n in ref]
    if not names:
        return None
    errs = {n: float(np.linalg.norm(J[n] - ref[n])) * 100 for n in names}
    vals = np.array(list(errs.values()))
    core = [n for n in names if not _is_leaf_marker(n)] or names
    cv = np.array([errs[n] for n in core])
    # horizontally aligned (other meshes of a character are centred differently by their props)
    off = np.mean([J[n] - ref[n] for n in core], axis=0)
    off[2] = 0.0
    al = np.array([np.linalg.norm(J[n] - off - ref[n]) * 100 for n in core])
    worst = max(errs, key=errs.get)
    return {"bones": len(errs), "mean_cm": round(float(vals.mean()), 2), "max_cm": round(float(vals.max()), 2),
            "worst": worst, "core_mean_cm": round(float(cv.mean()), 2), "core_max_cm": round(float(cv.max()), 2),
            "aligned_core_mean_cm": round(float(al.mean()), 2), "aligned_core_max_cm": round(float(al.max()), 2),
            "aligned_offset_cm": [round(float(v) * 100, 1) for v in to_gltf(off)],
            "per_bone_cm": {n: round(e, 2) for n, e in errs.items()},
            "per_bone_delta_cm_gltf": {n: [round(float(v) * 100, 1) for v in to_gltf(J[n] - ref[n])]
                                       for n in J if n in ref}}


def reference_joints(args):
    if args.reference_joints:
        with open(args.reference_joints) as f:
            d = json.load(f)
        d = d.get("joints", d)
        return {k: from_gltf(v) for k, v in d.items()}
    if args.reference_rig:
        vc.reset_scene(args.fps)
        objs = vc.import_glb(args.reference_rig)
        arm = max([o for o in objs if o.type == "ARMATURE"], key=lambda a: len(a.data.bones))
        mw = arm.matrix_world
        return {b.name: np.array(mw @ b.head_local) for b in arm.data.bones}
    return None


def qa_glb(path, n_frames, fps):
    """Skin + deformation metrics of a rigged GLB as the game will load it."""
    vc.reset_scene(fps)
    objs = vc.import_glb(path)
    arm = max([o for o in objs if o.type == "ARMATURE"], key=lambda a: len(a.data.bones))
    body = max([o for o in objs if o.type == "MESH" and not is_helper_mesh(o)], key=lambda o: len(o.data.vertices))
    st = vc.weight_stats(body)
    res = {"verts": st["verts"], "tris": vc.mesh_tris(body), "unweighted_verts": st["unweighted_verts"],
           "max_influences": st["max_influences"], "groups_used": st["groups_used"], "clips": {}}
    me = body.data
    n = len(me.vertices)
    rest = np.empty(n * 3)
    me.vertices.foreach_get("co", rest)
    mw = np.array(body.matrix_world)
    rest = rest.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    H = float(rest[:, 2].max() - rest[:, 2].min())
    E = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", E)
    E = E.reshape(-1, 2)
    L0 = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1)
    ok = L0 > 1e-3 * H
    scn = bpy.context.scene
    ad = arm.animation_data or arm.animation_data_create()
    ad.use_nla = False
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    pairs = lateral_bones(arm)
    feet = [b for b in ("LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot") if b in arm.pose.bones]
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
        if not vc.action_bone_names(act):
            continue
        bind_action(arm, act)
        a0, a1 = vc.action_range(act)
        frames = np.linspace(a0, a1, max(2, n_frames))
        maxd, smax, s999, nbad = 0.0, 0.0, 0.0, 0
        dg = bpy.context.evaluated_depsgraph_get()
        yaws = []
        foot_track = {b: [] for b in feet}
        for f in frames:
            scn.frame_set(int(math.floor(f)), subframe=float(f - math.floor(f)))
            dg = bpy.context.evaluated_depsgraph_get()
            ev = body.evaluated_get(dg)
            m2 = ev.to_mesh()
            co = np.empty(len(m2.vertices) * 3)
            m2.vertices.foreach_get("co", co)
            ev.to_mesh_clear()
            co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
            if len(co) != n:
                continue
            maxd = max(maxd, float(np.linalg.norm(co - rest, axis=1).max()))
            L1 = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1)
            r = L1[ok] / L0[ok]
            smax = max(smax, float(r.max()))
            s999 = max(s999, float(np.percentile(r, 99.9)))
            nbad = max(nbad, int((r > 2.0).sum()))
            lat = Vector()
            for a, b in pairs:
                lat += arm.pose.bones[a].head - arm.pose.bones[b].head
            yaws.append((math.atan2(lat.y, lat.x), math.hypot(lat.x, lat.y)))
            for b in feet:
                foot_track[b].append(np.array(arm.matrix_world @ arm.pose.bones[b].head))
        rest_lat = Vector()
        for a, b in pairs:
            rest_lat += arm.data.bones[a].head_local - arm.data.bones[b].head_local
        ry = math.atan2(rest_lat.y, rest_lat.x)
        sw = sum(w for _, w in yaws) or 1.0
        my = math.atan2(sum(math.sin(y - ry) * w for y, w in yaws) / sw, sum(math.cos(y - ry) * w for y, w in yaws) / sw)
        slide = {}
        for b, pts in foot_track.items():
            P = np.array(pts)
            if len(P):
                slide[b] = round(float(np.linalg.norm(P[:, :2].max(0) - P[:, :2].min(0))) * 100, 1)
        name = act.name.split("|")[0]
        res["clips"][name] = {
            "frames_sampled": len(frames), "max_disp_ratio": round(maxd / H, 3),
            "stretch_max": round(smax, 3), "stretch_p999": round(s999, 3), "edges_over_2x": nbad,
            "stretch_flag": smax > 2.0, "mean_facing_deg": round(math.degrees(my), 1),
            "foot_slide_cm": slide,
        }
    return res


def debug_png(path, g, joints_sets, parents):
    from PIL import Image, ImageDraw
    S = 4

    def proj(axis):
        occ = g.solid.any(axis=axis)
        dmax = g.dt.max(axis=axis)
        img = np.zeros(occ.shape + (3,), np.uint8)
        img[occ] = (80, 80, 80)
        img[dmax >= 3] = (140, 140, 140)
        img[dmax >= 6] = (190, 190, 190)
        return np.transpose(img, (1, 0, 2))[::-1]

    front, side = proj(1), proj(0)
    W = front.shape[1] + side.shape[1] + 4
    canvas = np.zeros((front.shape[0], W, 3), np.uint8)
    canvas[:, :front.shape[1]] = front
    canvas[:, front.shape[1] + 4:] = side
    im = Image.fromarray(canvas).resize((W * S, front.shape[0] * S), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    nz = g.shape[2]

    def px(p, view):
        i = (np.asarray(p) - g.lo) / g.v
        x = i[0] if view == 0 else front.shape[1] + 4 + i[1]
        return x * S, (nz - i[2]) * S

    cols = [(255, 70, 70), (70, 200, 255), (255, 210, 0)]
    for ci, (label, J) in enumerate(joints_sets):
        col = cols[ci % len(cols)]
        dr.text((6, 6 + 14 * ci), label, fill=col)
        for n, p in J.items():
            for view in (0, 1):
                x, y = px(p, view)
                dr.ellipse([x - 3, y - 3, x + 3, y + 3], outline=col, width=2)
                par = parents.get(n)
                if par and par in J:
                    x2, y2 = px(J[par], view)
                    dr.line([x, y, x2, y2], fill=col, width=1)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    im.save(path)


def features_summary(F, g):
    legs = F["legs"]
    arms = F["arms"]
    r = lambda x: None if x is None else round(float(x), 4)  # noqa: E731
    return {
        "crotch_y": r(legs.get("zc")) if legs["ok"] else None, "legs": "detected" if legs["ok"] else legs.get("why"),
        "armpit_y": r(F["za"]), "arms": {s: ("detected" if arms[s]["ok"] else arms[s].get("why")) for s in "LR"},
        "shoulder_top_y": r(F["zs"]), "head_top_y": r(F["zt"]), "centre_x": r(F["x0"]),
        "feet": "detected" if F.get("feet") else "not detected",
    }


# =========================================================================== main

def run_process_model(rig_glb, out, args, H, name):
    pm = os.path.join(HERE, "process_model.py")
    pm_args = [rig_glb, "-o", out, "--facing", "+z", "--height", repr(H), "--name", name,
               "--tex-size", str(args.tex_size)]
    if args.target_tris:
        pm_args += ["--target-tris", str(args.target_tris)]
    if args.team_mask:
        pm_args += ["--team-mask", args.team_mask]
    if args.team_desaturate:
        pm_args.append("--team-desaturate")
    pm_args += args.pm_arg
    exe = sys.executable
    if os.path.basename(exe).lower().startswith("python"):
        cmd = [exe, pm] + pm_args
    else:
        cmd = [exe, "-b", "--factory-startup", "-P", pm, "--"] + pm_args
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sys.stderr.write(p.stderr[-4000:])
    if p.returncode != 0:
        raise SystemExit(f"process_model failed ({p.returncode}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"raw_stdout": p.stdout[-2000:]}


def main():
    args = parse_args()
    t_start = time.time()
    out = os.path.abspath(args.out)
    name = args.name or os.path.splitext(os.path.basename(out))[0]
    clips = [parse_clip(c) for c in args.clip]
    if len({c[0] for c in clips}) != len(clips):
        raise SystemExit("duplicate clip names")
    for c in clips:
        if c[0] not in vc.STANDARD_CLIPS:
            vc.warn(f"clip name '{c[0]}' is not one of {vc.STANDARD_CLIPS}")

    # ---- template
    T = load_template(args.template)
    H = args.height if args.height > 0 else round(T["height"], 4)
    result = {"input": os.path.abspath(args.input), "output": out, "template": T["path"], "height_m": H,
              "facing_in": args.facing, "bones": len(T["names"])}

    ref = reference_joints(args) if (args.reference_rig or args.reference_joints) else None

    # ---- target mesh
    vc.reset_scene(args.fps)
    body = import_static(args.input, name)
    result["normalise"] = normalise_body(body, args.facing, args.yaw, H)
    result["tris_in"] = vc.mesh_tris(body)
    V, Fc = body_arrays(body)

    # ---- landmarks
    t0 = time.time()
    g = Grid(V, Fc, H / ANALYSIS_SLICES)
    yaw_det, conf = detect_forward(g, H)
    fc = {"detected_turn_deg": None if yaw_det is None else round(yaw_det, 1), "confidence": round(conf, 2)}
    if args.facing == "auto":
        if yaw_det is None or conf < 0.3:
            vc.warn("--facing auto: could not tell the facing from the feet; assuming +z")
        else:
            turn = 90.0 * round(yaw_det / 90.0)
            if turn % 360:
                body.data.transform(Matrix.Rotation(math.radians(-turn), 4, "Z"))
                result["normalise"]["yaw_deg"] = normalise_body(body, "+z", 0.0, H)["yaw_deg"] - turn
                V, Fc = body_arrays(body)
                g = Grid(V, Fc, H / ANALYSIS_SLICES)
            fc["applied_turn_deg"] = -turn
    elif yaw_det is not None and conf >= 0.5 and abs(((yaw_det + 180) % 360) - 180) > 45:
        vc.warn(f"the feet suggest the model faces {yaw_det:+.0f} deg (CCW from above) away from the assumed "
                f"front: check --facing (or use --facing auto)")
    result["facing_check"] = fc
    Fg = analyse_body(g, H)
    if "V" in T and not args.no_calibrate:
        Vt = T["V"].copy()
        Vt[:, 2] -= T["floor"]
        gt = Grid(Vt, T["F"], T["height"] / ANALYSIS_SLICES)
        Ft = analyse_body(gt, T["height"])
        Jt = {k: v - np.array([0, 0, T["floor"]]) for k, v in T["joints"].items()}
        T2 = dict(T, joints=Jt)
        C = calibrate(T2, Ft, gt)
        calib = "template mesh"
    else:
        raise SystemExit("template has no skinned mesh to calibrate landmarks on (--no-calibrate needs built-in "
                         "coefficients, not available for this template)")
    J, src = solve_joints(T2, Ft, gt, C, Fg, g)
    if args.joints:
        with open(args.joints) as f:
            ov = json.load(f)
        for k, p in ov.items():
            if k in J:
                J[k] = from_gltf(p)
                src[k] = "override"
    result["landmarks"] = {
        "calibration": calib, "analysis_voxel_m": round(g.v, 5), "seconds": round(time.time() - t0, 2),
        "features": features_summary(Fg, g), "template_features": features_summary(Ft, gt),
        "joints": {n: {"pos": to_gltf(J[n]), "source": src[n]} for n in T["names"]},
    }
    fallbacks = sorted(n for n in T["names"] if src[n].startswith("fallback"))
    result["landmarks"]["fallback_joints"] = fallbacks
    if fallbacks:
        vc.warn(f"{len(fallbacks)} joints use template-proportion fallbacks: {fallbacks}")
    if ref is not None:
        result["joint_error"] = joint_error(J, ref)
    if args.debug_png:
        sets = [("autorig", J)]
        if ref is not None:
            sets.append(("reference", ref))
        debug_png(args.debug_png, g, sets, T["parents"])
        result["debug_png"] = os.path.abspath(args.debug_png)
    if args.landmarks_json:
        with open(args.landmarks_json, "w") as f:
            json.dump({"joints": {n: to_gltf(J[n]) for n in T["names"]}, "sources": src,
                       "features": result["landmarks"]["features"]}, f, indent=1)

    # ---- armature + skin
    t0 = time.time()
    arm = build_export_armature(T, J)
    result["skin"] = skin(body, T, J, Fg, g, args, H)
    body.parent = arm
    body.matrix_parent_inverse = Matrix.Identity(4)
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    st = vc.weight_stats(body)
    result["skin"].update({k: v for k, v in st.items() if not k.startswith("_")})
    result["skin"]["seconds"] = round(time.time() - t0, 2)

    # ---- clips
    t0 = time.time()
    result["clips"], stash = transfer_clips(arm, clips, args)
    result["clips_seconds"] = round(time.time() - t0, 2)
    reset_pose(arm)
    if stash:
        vc.stash_actions(arm, stash)
    vc.purge_orphans()

    # ---- export
    tmpdir = tempfile.TemporaryDirectory(prefix="vc_autorig_")
    rig_glb = os.path.abspath(args.keep_rig) if args.keep_rig else os.path.join(tmpdir.name, name + "_rig.glb")
    if args.raw:
        rig_glb = out
    vc.export_glb(rig_glb, animations=bool(stash))
    if not args.raw:
        pm = run_process_model(rig_glb, out, args, H, name)
        result["process_model"] = {k: pm.get(k) for k in ("tris_after", "verts_after", "dims_godot_m", "materials",
                                                         "team_mask", "skin", "warnings", "file_bytes") if k in pm}
    if args.keep_rig and not args.raw:
        result["rig_glb"] = rig_glb

    # ---- QA on what the game gets
    result["qa"] = qa_glb(out, args.qa_frames, args.fps)
    flags = [c for c, m in result["qa"]["clips"].items() if m["stretch_flag"]]
    if flags:
        vc.warn(f"edge stretch > 2x in clips {flags}")
    if result["qa"]["unweighted_verts"]:
        vc.warn(f"{result['qa']['unweighted_verts']} unweighted vertices in the output")
    tmpdir.cleanup()
    result["file_bytes"] = os.path.getsize(out)
    result["seconds"] = round(time.time() - t_start, 1)
    result["warnings"] = vc.warnings()
    vc.emit_json(result, args.json)


if __name__ == "__main__":
    main()
