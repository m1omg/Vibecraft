"""Verify a retargeted GLB against its source by evaluating both rigs in Blender.

    /opt/bpyenv/v313/bin/python tools/tests/check_retarget.py --source src.glb --result out.glb \\
        --clips attack,death

For each clip and sampled frame it checks, from Blender's own evaluation of both rigs:
  * joint vectors: every target joint-to-joint vector (parent head -> bone head) must equal its
    rest vector rotated by the SOURCE parent's world rotation-from-rest (independent of how the
    retarget computes local keys);
  * world delta rotations: each matched bone's world rotation relative to rest must match.
Both after removing the facing difference between the rigs; a correct retarget gives ~0 deg.
It also reports the hips vertical offset ratio target/source (should equal the leg ratio).
Exit code 1 if the max angle error exceeds --max-err (deg).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402
from mathutils import Quaternion  # noqa: E402

import vc_bpy as vc  # noqa: E402


def arm_of(objs):
    return max((o for o in objs if o.type == "ARMATURE"), key=lambda a: len(a.data.bones))


def set_action(arm, act):
    ad = arm.animation_data or arm.animation_data_create()
    ad.use_nla = False
    ad.action = act
    ad.action_slot = vc.action_object_slot(act)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--clips", required=True, help="comma list; SRC:RES if names differ")
    ap.add_argument("--samples", type=int, default=9)
    ap.add_argument("--max-err", type=float, default=1.0)
    args = ap.parse_args(vc.bpy_argv())

    vc.reset_scene()
    r_objs = vc.import_glb(args.result)
    R = arm_of(r_objs)
    for a in list(bpy.data.actions):
        a.name = "res__" + a.name
    s_objs = vc.import_glb(args.source)
    S = arm_of(s_objs)
    acts = {a.name: a for a in bpy.data.actions}
    ys, yr = vc.lateral_yaw(S), vc.lateral_yaw(R)
    yaw = (yr - ys) if ys is not None and yr is not None else 0.0
    Yq = Quaternion((0, 0, 1), yaw)
    Y = Yq.to_matrix()
    common = [b.name for b in R.data.bones if b.name in S.data.bones]
    sh, rh = vc.find_hips(S), vc.find_hips(R)
    leg_ratio = vc.leg_height(R, rh) / vc.leg_height(S, sh)
    s_rest = (S.matrix_world @ sh.head_local).z
    r_rest = (R.matrix_world @ rh.head_local).z
    out = {"yaw_between_rigs_deg": round(math.degrees(yaw), 3), "leg_ratio": round(leg_ratio, 5), "clips": {}}
    worst = 0.0
    scn = bpy.context.scene
    for spec in args.clips.split(","):
        sname, _, rname = spec.partition(":")
        rname = rname or sname
        sa = acts.get(sname) or next((a for n, a in acts.items() if n.startswith(sname) and not n.startswith("res__")), None)
        ra = acts.get("res__" + rname) or next((a for n, a in acts.items() if n.startswith("res__" + rname)), None)
        if sa is None or ra is None:
            raise SystemExit(f"clip not found: {sname} / {rname} in {sorted(acts)}")
        set_action(S, sa)
        set_action(R, ra)
        f0, f1 = vc.action_range(sa)
        errs, ratios, motion, rot_errs = [], [], [], []
        for i in range(args.samples):
            fr = f0 + (f1 - f0) * i / (args.samples - 1)
            scn.frame_set(int(round(fr)))
            dg = bpy.context.evaluated_depsgraph_get()
            Se, Re = S.evaluated_get(dg), R.evaluated_get(dg)
            for n in common:
                # world rotation relative to rest (covers twist and leaf bones)
                qs = (S.matrix_world @ Se.pose.bones[n].matrix).to_3x3().normalized().to_quaternion() @ \
                    (S.matrix_world @ S.data.bones[n].matrix_local).to_3x3().normalized().to_quaternion().inverted()
                qr = (R.matrix_world @ Re.pose.bones[n].matrix).to_3x3().normalized().to_quaternion() @ \
                    (R.matrix_world @ R.data.bones[n].matrix_local).to_3x3().normalized().to_quaternion().inverted()
                qs = Yq @ qs @ Yq.inverted()
                a_ = math.degrees(qs.rotation_difference(qr).angle)
                rot_errs.append(min(a_, 360 - a_))
                # joint-to-joint vectors (parent head -> head): real glTF data, unlike bone tails
                rb = S.data.bones[n]
                if rb.parent is None or R.data.bones[n].parent is None:
                    continue
                pn = rb.parent.name
                if R.data.bones[n].parent.name != pn:
                    continue
                rest_d = (S.matrix_world @ rb.head_local - S.matrix_world @ rb.parent.head_local)
                ds = (S.matrix_world @ Se.pose.bones[n].head - S.matrix_world @ Se.pose.bones[pn].head)
                rrb = R.data.bones[n]
                rest_r = (R.matrix_world @ rrb.head_local - R.matrix_world @ rrb.parent.head_local)
                dr = (R.matrix_world @ Re.pose.bones[n].head - R.matrix_world @ Re.pose.bones[pn].head)
                if ds.length < 1e-9 or dr.length < 1e-9:
                    continue
                motion.append(math.degrees(ds.angle(rest_d, 0.0)))
                # source parent's world rotation relative to rest, applied to the TARGET rest vector
                qp = (S.matrix_world @ Se.pose.bones[pn].matrix).to_3x3().normalized().to_quaternion() @ \
                    (S.matrix_world @ S.data.bones[pn].matrix_local).to_3x3().normalized().to_quaternion().inverted()
                expected = (Yq @ qp @ Yq.inverted()) @ rest_r
                errs.append(math.degrees(expected.angle(dr, 0.0)))
            dz_s = (S.matrix_world @ Se.pose.bones[sh.name].head).z - s_rest
            dz_r = (R.matrix_world @ Re.pose.bones[rh.name].head).z - r_rest
            if abs(dz_s) > 1e-3:
                ratios.append(dz_r / dz_s)
        e = {"max_deg": round(max(errs), 4), "mean_deg": round(sum(errs) / len(errs), 4),
             "world_delta_rot_max_deg": round(max(rot_errs), 4),
             "hips_dz_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
             "source_motion_max_deg": round(max(motion), 2),
             "frames": [f0, f1], "bones_compared": len(common)}
        worst = max(worst, e["max_deg"], e["world_delta_rot_max_deg"])
        out["clips"][rname] = e
    out["ok"] = worst <= args.max_err
    vc.emit_json(out)
    sys.exit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
