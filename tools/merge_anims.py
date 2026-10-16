"""Merge single-clip GLBs of the SAME rigged character into one GLB with named clips.

Generators such as Meshy export one animation per rigged file. This takes the mesh + armature
from the base file (default: the first --clip file, or --base, e.g. the output of
process_model.py) and adds the animation of every --clip file under the given name.

    /opt/bpyenv/v313/bin/python tools/merge_anims.py -o assets/models/footman.glb \\
        --base build/footman_lod.glb \\
        --clip idle=raw/footman_idle.glb --clip walk=raw/footman_walk.glb \\
        --clip attack=raw/footman_attack.glb --clip death=raw/footman_death.glb

--clip NAME=FILE[:ACTION]  ACTION picks one animation when FILE holds several (default: the
                           longest one). Standard names: idle walk attack death work cast birth.

How keys are transferred: if the clip file's skeleton has the same parent-relative rest
orientations as the base (normal for exports of one character; process_model's scale/turn does
not change them), bone-local keys are copied verbatim and location keys are rescaled by the
bone-length ratio (so a base re-scaled by process_model still gets correct hip motion).
Otherwise the clip is retargeted (rotation-only, see retarget_anims.py) with a warning.

Each clip becomes an action on its own muted NLA track, so the glTF exporter writes one
animation per clip. The result is re-imported and the clip list is verified.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import vc_bpy as vc  # noqa: E402


def parse_args():
    ap = argparse.ArgumentParser(prog="merge_anims.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip", action="append", required=True, metavar="NAME=FILE[:ACTION]",
                    help="clip name and the GLB that holds it; repeatable, order is kept")
    ap.add_argument("--base", default=None, help="GLB providing mesh+armature (default: first --clip file)")
    ap.add_argument("--keep-base-anims", action="store_true",
                    help="keep animations already in the base file (default: dropped)")
    ap.add_argument("-o", "--out", required=True, help="output .glb")
    ap.add_argument("--rest-tolerance", type=float, default=1.0,
                    help="max rest-orientation difference (deg) for verbatim key copy (default 1)")
    ap.add_argument("--fps", type=int, default=vc.FPS_DEFAULT)
    ap.add_argument("--json", default=None, help="also write the JSON summary here")
    ap.add_argument("--no-verify", action="store_true")
    return ap.parse_args(vc.bpy_argv())


def parse_clip(spec):
    if "=" not in spec:
        raise SystemExit(f"--clip expects NAME=FILE[:ACTION], got {spec!r}")
    name, rest = spec.split("=", 1)
    action = None
    if not os.path.isfile(rest) and ":" in rest:
        rest, action = rest.rsplit(":", 1)
    return name.strip(), rest, action


def pick_armature(objs):
    arms = [o for o in objs if o.type == "ARMATURE"]
    if not arms:
        return None
    return max(arms, key=lambda a: len(a.data.bones))


def main():
    args = parse_args()
    clips = [parse_clip(c) for c in args.clip]
    names = [c[0] for c in clips]
    if len(set(names)) != len(names):
        raise SystemExit(f"duplicate clip names: {names}")
    for n in names:
        if n not in vc.STANDARD_CLIPS:
            vc.warn(f"clip name '{n}' is not one of the standard names {vc.STANDARD_CLIPS}")
    base_path = args.base or clips[0][1]

    vc.reset_scene(args.fps)
    base_objs = vc.import_glb(base_path)
    arm = pick_armature(base_objs)
    if arm is None:
        raise SystemExit(f"base file has no armature: {base_path}")
    base_actions = vc.actions_for_armature(arm)
    kept = []
    if args.keep_base_anims:
        kept = [a for a in base_actions if a.name not in names]
        for a in base_actions:
            if a.name in names:
                vc.warn(f"base clip '{a.name}' replaced by --clip {a.name}")
                bpy.data.actions.remove(a)
    else:
        for a in base_actions:
            bpy.data.actions.remove(a)
    if arm.animation_data:
        arm.animation_data.action = None
        for tr in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(tr)

    result = {"base": os.path.abspath(base_path), "output": os.path.abspath(args.out), "clips": []}
    stash = [(a, vc.action_object_slot(a)) for a in kept]
    for name, path, want in clips:
        before_actions = set(bpy.data.actions)
        objs = vc.import_glb(path)
        src = pick_armature(objs)
        if src is None:
            raise SystemExit(f"{path}: no armature")
        acts = [a for a in bpy.data.actions if a not in before_actions]
        acts = [a for a in acts if vc.action_bone_names(a)]
        if not acts:
            raise SystemExit(f"{path}: no animation found")
        if want:
            sel = [a for a in acts if a.name == want or a.name.startswith(want)]
            if not sel:
                raise SystemExit(f"{path}: no action named {want!r} (have {[a.name for a in acts]})")
            src_act = sel[0]
        else:
            src_act = max(acts, key=lambda a: (vc.action_range(a)[1] - vc.action_range(a)[0]))
            if len(acts) > 1:
                vc.warn(f"{path}: {len(acts)} animations, using the longest '{src_act.name}' "
                        f"(pick with {name}={path}:ACTION)")
        missing = sorted(vc.action_bone_names(src_act) - {b.name for b in arm.data.bones})
        mism, worst_bone = vc.rest_mismatch_deg(src, arm)
        entry = {"name": name, "file": os.path.abspath(path), "source_action": src_act.name,
                 "rest_mismatch_deg": round(mism, 4), "missing_bones": missing}
        if mism <= args.rest_tolerance:
            ratio = vc.bone_length_ratio(src, arm)
            new, slot = vc.copy_action_direct(src_act, arm, "__tmp_" + name, loc_scale=ratio)
            entry.update(method="copy", location_scale=round(ratio, 6))
        else:
            vc.warn(f"{name}: rest pose differs from base by {mism:.1f} deg at '{worst_bone}', retargeting")
            new, slot, info = vc.retarget_action(src, src_act, arm, "__tmp_" + name, hips_mode="full")
            entry.update(method="retarget", retarget=info)
        entry["frames"] = list(vc.action_range(new))
        stash.append((new, slot))
        result["clips"].append(entry)
        # drop everything that came from the clip file
        for a in [a for a in bpy.data.actions if a not in before_actions and a is not new]:
            bpy.data.actions.remove(a)
        vc.delete_objects([o for o in objs])
    for a, _ in stash:
        if a.name.startswith("__tmp_"):
            a.name = a.name[len("__tmp_"):]
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    vc.stash_actions(arm, stash)
    vc.purge_orphans()
    vc.export_glb(args.out, animations=True)
    result["actions"] = [vc.action_info(a) for a, _ in stash]
    result["file_bytes"] = os.path.getsize(args.out)
    if not args.no_verify:
        result["verify"] = verify(args.out, [a.name for a, _ in stash])
    result["warnings"] = vc.warnings()
    vc.emit_json(result, args.json)
    if result.get("verify", {}).get("ok") is False:
        sys.exit(1)


def verify(path, expected):
    vc.reset_scene()
    objs = vc.import_glb(path)
    arm = pick_armature(objs)
    acts = {a.name: a for a in bpy.data.actions}
    # importer may suffix names with the object; map back by prefix
    found = {}
    for e in expected:
        m = [a for n, a in acts.items() if n == e or n.startswith(e + "_") or n.startswith(e + ".")]
        if m:
            found[e] = vc.action_info(m[0])
    return {"actions": found, "missing": [e for e in expected if e not in found],
            "bones": len(arm.data.bones) if arm else 0, "ok": len(found) == len(expected)}


if __name__ == "__main__":
    main()
