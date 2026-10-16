"""Copy animations from one rigged GLB to another rig with the same bone NAMES but different
proportions (e.g. two Meshy characters), rotation-only.

    /opt/bpyenv/v313/bin/python tools/retarget_anims.py --source human_merged.glb \\
        --target dwarf.glb -o dwarf_merged.glb --clip attack --clip death

For every target bone that has a source bone of the same name (namespace prefixes like
'mixamorig:' and case are ignored; --map adds explicit pairs) the target bone gets the same
WORLD-space rotation relative to its rest pose as the source bone, so differing bone-axis
conventions don't matter. Unmatched target bones follow their parent. Translations are ignored
except the hips (root motion): its offset from rest is scaled by the leg-length ratio (hips
height above the lowest bone, target/source); --hips-mode vertical (default) keeps only the up
component (bob, crouch, fall), full keeps all three (use for death/knock-back clips that travel),
none drops it. A facing difference between the rigs is detected from Left*/Right* bones and
compensated (--no-align-yaw to disable).

Assumption: both rigs share a rest pose (both T-pose or both A-pose). The output is the target
file (mesh + armature + its own clips, unless --drop-target-anims) plus the retargeted clips,
re-imported for verification.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import vc_bpy as vc  # noqa: E402


def parse_args():
    ap = argparse.ArgumentParser(prog="retarget_anims.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="rigged GLB holding the animations")
    ap.add_argument("--target", required=True, help="rigged GLB that receives them")
    ap.add_argument("-o", "--out", required=True, help="output .glb")
    ap.add_argument("--clip", action="append", default=[], metavar="SRC[=NEW]",
                    help="source clip to transfer, optionally renamed; repeatable (default: all)")
    ap.add_argument("--hips-mode", choices=["vertical", "full", "none"], default="vertical")
    ap.add_argument("--src-hips", default=None, help="source hips bone (default: auto, 'Hips'-like)")
    ap.add_argument("--tgt-hips", default=None, help="target hips bone (default: auto)")
    ap.add_argument("--map", action="append", default=[], metavar="TGT=SRC",
                    help="explicit bone pair when names differ; repeatable")
    ap.add_argument("--no-align-yaw", action="store_true", help="don't compensate a facing difference")
    ap.add_argument("--drop-target-anims", action="store_true", help="discard clips already in the target")
    ap.add_argument("--fps", type=int, default=vc.FPS_DEFAULT)
    ap.add_argument("--json", default=None, help="also write the JSON summary here")
    ap.add_argument("--no-verify", action="store_true")
    return ap.parse_args(vc.bpy_argv())


def pick_armature(objs):
    arms = [o for o in objs if o.type == "ARMATURE"]
    return max(arms, key=lambda a: len(a.data.bones)) if arms else None


def main():
    args = parse_args()
    vc.reset_scene(args.fps)
    t_objs = vc.import_glb(args.target)
    tgt = pick_armature(t_objs)
    if tgt is None:
        raise SystemExit(f"target has no armature: {args.target}")
    t_actions = vc.actions_for_armature(tgt)
    for a in t_actions:
        a.name = "__tgt_" + a.name  # keep names free while the source is imported
    before = set(bpy.data.actions)
    s_objs = vc.import_glb(args.source)
    src = pick_armature(s_objs)
    if src is None:
        raise SystemExit(f"source has no armature: {args.source}")
    s_actions = [a for a in bpy.data.actions if a not in before and vc.action_bone_names(a)]
    if not s_actions:
        raise SystemExit(f"source has no animations: {args.source}")

    wanted = []
    if args.clip:
        for c in args.clip:
            sname, _, new = c.partition("=")
            m = [a for a in s_actions if a.name == sname]
            if not m:
                raise SystemExit(f"source clip {sname!r} not found (have {[a.name for a in s_actions]})")
            wanted.append((m[0], new or sname))
    else:
        wanted = [(a, a.name) for a in s_actions]
    bone_map = dict(m.split("=", 1) for m in args.map)

    result = {"source": os.path.abspath(args.source), "target": os.path.abspath(args.target),
              "output": os.path.abspath(args.out), "clips": []}
    new_actions = []
    for act, new_name in wanted:
        new, slot, info = vc.retarget_action(
            src, act, tgt, "__new_" + new_name, hips_mode=args.hips_mode,
            src_hips=args.src_hips, tgt_hips=args.tgt_hips, align_yaw=not args.no_align_yaw,
            bone_map=bone_map)
        info["name"] = new_name
        info["source_clip"] = act.name
        result["clips"].append(info)
        new_actions.append((new, slot))
        if info["unmatched_target_bones"]:
            vc.warn(f"{new_name}: target bones without a source match (they follow their parent): "
                    f"{info['unmatched_target_bones'][:10]}")

    # remove the source rig and its clips; restore target clip names
    for a in [a for a in bpy.data.actions if a not in before]:
        if a not in [n for n, _ in new_actions]:
            bpy.data.actions.remove(a)
    vc.delete_objects(s_objs)
    new_names = {a.name[len("__new_"):] for a, _ in new_actions}
    stash = []
    for a in t_actions:
        orig = a.name[len("__tgt_"):]
        if args.drop_target_anims:
            bpy.data.actions.remove(a)
        elif orig in new_names:
            vc.warn(f"target clip '{orig}' replaced by the retargeted one")
            bpy.data.actions.remove(a)
        else:
            a.name = orig
            stash.append((a, vc.action_object_slot(a)))
    for a, s in new_actions:
        a.name = a.name[len("__new_"):]
        stash.append((a, s))
    for pb in tgt.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    vc.stash_actions(tgt, stash)
    vc.purge_orphans()
    vc.export_glb(args.out, animations=True)
    result["actions"] = [vc.action_info(a) for a, _ in stash]
    result["file_bytes"] = os.path.getsize(args.out)
    exp = sorted(a.name for a, _ in stash)
    if not args.no_verify:
        vc.reset_scene(args.fps)
        objs = vc.import_glb(args.out)
        arm = pick_armature(objs)
        got = sorted(a.name for a in bpy.data.actions)
        result["verify"] = {"actions": got, "bones": len(arm.data.bones) if arm else 0,
                            "ok": all(any(g == e or g.startswith(e + "_") for g in got) for e in exp)}
    result["warnings"] = vc.warnings()
    vc.emit_json(result, args.json)
    if result.get("verify", {}).get("ok") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
