"""Shared helpers for the Vibecraft Blender (bpy) asset tools.

Imported by process_model.py, merge_anims.py, retarget_anims.py and the tests.
Must be run with the bpy-enabled interpreter (e.g. /opt/bpyenv/v313/bin/python).

Conventions (see tools/README.md):
  * Blender is Z-up, the glTF exporter converts to Y-up (Godot space).
    Blender (x, y, z)  ->  glTF/Godot (x, z, -y).
  * Exported models FACE -Z in Godot space (= +Y in Blender), feet on y=0,
    origin at the bottom-centre of the bounds, 1 unit = 1 metre. Raw AI models
    usually face +Z (glTF convention) and are turned 180 degrees by process_model.
  * Animations are exported one glTF animation per Blender action, named after
    the action (idle, walk, attack, death, work, cast, birth).
"""
from __future__ import annotations

import contextlib
import json
import math
import os
import sys

import bpy
import mathutils
from bpy_extras import anim_utils

FPS_DEFAULT = 30
STANDARD_CLIPS = ("idle", "walk", "attack", "death", "work", "cast", "birth")

_WARNINGS: list[str] = []


# --------------------------------------------------------------------------- logging

def log(*args):
    print("[vc]", *args, file=sys.stderr, flush=True)


def warn(msg: str):
    _WARNINGS.append(msg)
    print("[vc] WARNING:", msg, file=sys.stderr, flush=True)


def warnings() -> list[str]:
    return list(_WARNINGS)


@contextlib.contextmanager
def stdout_to_stderr():
    """Route fd 1 to fd 2 so Blender/glTF chatter never pollutes our JSON on stdout."""
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


def emit_json(data: dict, path: str | None = None):
    text = json.dumps(data, indent=2, sort_keys=False)
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            f.write(text + "\n")
    print(text, flush=True)


def bpy_argv() -> list[str]:
    """Arguments for argparse, whether run as `python tool.py ...` (bpy module) or
    `blender -b -P tool.py -- ...`."""
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:]


# --------------------------------------------------------------------------- scene / io

def reset_scene(fps: int = FPS_DEFAULT):
    with stdout_to_stderr():
        bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = int(fps)
    scn.render.fps_base = 1.0
    scn.frame_start = 0
    scn.frame_current = 0


def import_glb(path: str) -> list[bpy.types.Object]:
    if not os.path.isfile(path):
        raise SystemExit(f"input not found: {path}")
    before = set(bpy.data.objects)
    with stdout_to_stderr():
        bpy.ops.import_scene.gltf(
            filepath=os.path.abspath(path),
            merge_vertices=False,           # we weld ourselves (keeps UV seams as loop data)
            import_shading="NORMALS",
            bone_heuristic="BLENDER",       # keep glTF joint rest orientations exactly
            disable_bone_shape=True,        # no icosphere custom-shape meshes for bones
            guess_original_bind_pose=True,
            import_pack_images=True,
            import_select_created_objects=False,
        )
    bpy.context.view_layer.update()
    return [o for o in bpy.data.objects if o not in before]


def export_glb(path: str, animations: bool = True, jpeg_quality: int = 90,
               objects: list | None = None):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    if objects is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objects)
    kw = dict(
        filepath=os.path.abspath(path),
        check_existing=False,
        export_format="GLB",
        export_image_format="AUTO",
        export_jpeg_quality=int(jpeg_quality),
        export_image_quality=int(jpeg_quality),
        export_yup=True,
        export_apply=True,                  # apply non-armature modifiers
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_vertex_color="MATERIAL",
        export_cameras=False,
        export_lights=False,
        export_extras=False,
        export_skins=True,
        export_influence_nb=4,
        export_all_influences=False,
        export_def_bones=False,
        export_leaf_bone=False,
        export_rest_position_armature=True,
        export_reset_pose_bones=True,
        export_animations=bool(animations),
        export_animation_mode="ACTIONS",
        export_anim_single_armature=True,
        export_nla_strips=True,
        export_merge_animation="ACTION",
        export_force_sampling=True,
        export_optimize_animation_size=True,
        export_anim_slide_to_zero=True,
        export_frame_range=False,
        export_draco_mesh_compression_enable=False,
        export_meshopt_compression_enable=False,
        use_selection=objects is not None,
    )
    with stdout_to_stderr():
        bpy.ops.export_scene.gltf(**kw)
    return path


def select_only(objs, active=None):
    vl = bpy.context.view_layer
    vl.update()
    for o in list(vl.objects):
        if o is not None:
            o.select_set(False)
    for o in objs:
        o.select_set(True)
    vl.objects.active = active or (objs[0] if objs else None)


def delete_objects(objs):
    for o in list(objs):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and getattr(data, "users", 1) == 0:
            coll = {bpy.types.Mesh: bpy.data.meshes, bpy.types.Armature: bpy.data.armatures,
                    bpy.types.Camera: bpy.data.cameras, bpy.types.Light: bpy.data.lights}
            for t, c in coll.items():
                if isinstance(data, t):
                    c.remove(data)
                    break
    bpy.context.view_layer.update()


def purge_orphans():
    with stdout_to_stderr():
        for _ in range(3):
            bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


# --------------------------------------------------------------------------- mesh info

def mesh_tris(obj) -> int:
    me = obj.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def world_bounds(mesh_objs, use_eval=False):
    """Axis-aligned world bounds (Blender space) of mesh vertices."""
    lo = mathutils.Vector((math.inf,) * 3)
    hi = mathutils.Vector((-math.inf,) * 3)
    dg = bpy.context.evaluated_depsgraph_get() if use_eval else None
    import numpy as np
    for o in mesh_objs:
        if use_eval:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
        else:
            me = o.data
        n = len(me.vertices)
        if n:
            co = np.empty(n * 3, dtype=np.float64)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            m = np.array(o.matrix_world, dtype=np.float64)
            w = co @ m[:3, :3].T + m[:3, 3]
            lo = mathutils.Vector(np.minimum(np.array(lo), w.min(0)))
            hi = mathutils.Vector(np.maximum(np.array(hi), w.max(0)))
        if use_eval:
            ev.to_mesh_clear()
    return lo, hi


def godot_dims(lo, hi):
    """Blender bounds -> Godot (x width, y height, z depth) dimensions in metres."""
    d = hi - lo
    return [round(d.x, 4), round(d.z, 4), round(d.y, 4)]


def weight_stats(obj):
    """Skin-weight statistics for a mesh: how many verts are influenced, max influences."""
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    n = len(me.vertices)
    unweighted = 0
    max_inf = 0
    used = set()
    for v in me.vertices:
        ws = [g for g in v.groups if g.weight > 1e-4]
        if not ws:
            unweighted += 1
        max_inf = max(max_inf, len(ws))
        for g in ws:
            used.add(names.get(g.group, "?"))
    return {
        "verts": n,
        "unweighted_verts": unweighted,
        "weighted_fraction": round(1.0 - unweighted / n, 5) if n else 0.0,
        "max_influences": max_inf,
        "groups_total": len(obj.vertex_groups),
        "groups_used": len(used),
        "_used_names": sorted(used),
    }


# --------------------------------------------------------------------------- actions

def action_channelbags(action):
    """All channelbags of a (layered, Blender >= 4.4) action."""
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            if strip.type == "KEYFRAME":
                out.extend(strip.channelbags)
    return out


def action_fcurves(action, slot=None):
    fcs = []
    for cb in action_channelbags(action):
        if slot is None or cb.slot_handle == slot.handle:
            fcs.extend(cb.fcurves)
    return fcs


def action_bone_names(action) -> set[str]:
    names = set()
    for fc in action_fcurves(action):
        if fc.data_path.startswith('pose.bones["'):
            names.add(fc.data_path.split('"')[1])
    return names


def action_object_slot(action):
    for s in action.slots:
        if s.target_id_type == "OBJECT":
            return s
    return action.slots[0] if len(action.slots) else None


def action_range(action):
    a, b = action.frame_range
    return float(a), float(b)


def actions_for_armature(arm) -> list:
    """Actions that animate `arm`: active action, NLA strips, then any other action in
    the file whose fcurves address this armature's pose bones."""
    found = []
    ad = arm.animation_data
    if ad:
        if ad.action:
            found.append(ad.action)
        for tr in ad.nla_tracks:
            for st in tr.strips:
                if st.action and st.action not in found:
                    found.append(st.action)
    bones = {b.name for b in arm.data.bones}
    for act in bpy.data.actions:
        if act in found:
            continue
        bn = action_bone_names(act)
        if bn and len(bn & bones) >= max(1, 0.5 * len(bn)):
            found.append(act)
    return found


def action_info(action, fps=None):
    fps = fps or bpy.context.scene.render.fps
    a, b = action_range(action)
    return {
        "name": action.name,
        "frames": [round(a, 3), round(b, 3)],
        "duration_s": round((b - a) / fps, 4),
        "bones_animated": len(action_bone_names(action)),
    }


def new_action_for(arm, name):
    """Create an empty action with an OBJECT slot bound to `arm`; returns (action, channelbag)."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type="OBJECT", name=arm.name)
    layer = act.layers.new("Layer")
    strip = layer.strips.new(type="KEYFRAME")
    cb = strip.channelbag(slot, ensure=True)
    return act, slot, cb


def fcurve_set_keys(cb, data_path, index, frames, values, group=None):
    fc = cb.fcurves.find(data_path, index=index)
    if fc is None:
        fc = cb.fcurves.new(data_path, index=index, group_name=group or "")
    fc.keyframe_points.clear()
    n = len(frames)
    fc.keyframe_points.add(n)
    co = [0.0] * (2 * n)
    co[0::2] = [float(f) for f in frames]
    co[1::2] = [float(v) for v in values]
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    fc.update()
    return fc


def stash_actions(arm, actions_slots):
    """Put every action on its own NLA track (muted) so the glTF exporter
    ('ACTIONS' mode) writes each one as a separate animation, and nothing is
    blended into the rest pose."""
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for act, slot in actions_slots:
        act.use_fake_user = True
        tr = ad.nla_tracks.new()
        tr.name = act.name
        start = int(math.floor(action_range(act)[0]))
        st = tr.strips.new(act.name, start, act)
        if slot is not None:
            try:
                st.action_slot = slot
            except Exception as e:  # pragma: no cover
                warn(f"could not bind slot for {act.name}: {e}")
        tr.mute = True
    return ad


def scale_location_curves(action, factor: float):
    """Multiply all pose-bone location keys (and handles) by `factor`."""
    if abs(factor - 1.0) < 1e-9:
        return 0
    n = 0
    for fc in action_fcurves(action):
        if fc.data_path.startswith("pose.bones[") and fc.data_path.endswith(".location"):
            for kp in fc.keyframe_points:
                kp.co.y *= factor
                kp.handle_left.y *= factor
                kp.handle_right.y *= factor
            fc.update()
            n += 1
    return n


def bones_in_hierarchy_order(arm):
    out = []

    def rec(b):
        out.append(b)
        for c in b.children:
            rec(c)

    for b in arm.data.bones:
        if b.parent is None:
            rec(b)
    return out


def find_hips(arm, hint: str | None = None):
    bones = arm.data.bones
    if hint:
        if hint in bones:
            return bones[hint]
        raise SystemExit(f"hips bone '{hint}' not found in {arm.name}")
    for b in bones:
        n = b.name.lower().split(":")[-1]
        if n in ("hips", "hip", "pelvis", "root_hips"):
            return b
    roots = [b for b in bones if b.parent is None]
    # a root at ground level with a single child is usually a 'Root' bone above the hips
    r = max(roots, key=lambda b: len(b.children_recursive))
    if len(r.children) == 1 and len(r.children[0].children) >= 2:
        return r.children[0]
    return r


def uniform_scale(m: mathutils.Matrix) -> float:
    s = m.to_scale()
    if max(s) - min(s) > 1e-3 * max(abs(max(s)), 1e-9):
        warn(f"non-uniform object scale {tuple(round(x, 5) for x in s)}; using the mean")
    return (abs(s.x) + abs(s.y) + abs(s.z)) / 3.0


# --------------------------------------------------------------------------- transfer / retarget

def _rot(m):
    return m.to_3x3().normalized().to_quaternion()


def local_rest(bone):
    """Bone rest matrix relative to its parent (armature data units)."""
    if bone.parent is None:
        return bone.matrix_local.copy()
    return bone.parent.matrix_local.inverted() @ bone.matrix_local


def rest_mismatch_deg(src_arm, tgt_arm) -> tuple[float, str]:
    """Largest difference (degrees) between parent-relative rest rotations of bones present in
    both armatures. ~0 means local pose keys can be copied verbatim."""
    worst, wname = 0.0, ""
    for b in tgt_arm.data.bones:
        sb = src_arm.data.bones.get(b.name)
        if sb is None:
            continue
        if (sb.parent.name if sb.parent else None) != (b.parent.name if b.parent else None):
            return 180.0, b.name
        if b.parent is None:
            continue  # root orientation is absorbed by the object/armature transform
        d = math.degrees(_rot(local_rest(sb)).rotation_difference(_rot(local_rest(b))).angle)
        d = min(d, 360.0 - d)
        if d > worst:
            worst, wname = d, b.name
    return worst, wname


def bone_length_ratio(src_arm, tgt_arm) -> float:
    """Median target/source joint distance (head to parent head, armature data units) over
    shared bones. Joint positions are real glTF data; bone tails are importer guesses."""
    rs = []
    for b in tgt_arm.data.bones:
        sb = src_arm.data.bones.get(b.name)
        if sb is None or b.parent is None or sb.parent is None:
            continue
        ls = (sb.head_local - sb.parent.head_local).length
        lt = (b.head_local - b.parent.head_local).length
        if ls > 1e-9 and lt > 1e-9:
            rs.append(lt / ls)
    if not rs:
        return 1.0
    rs.sort()
    return rs[len(rs) // 2]


def copy_action_direct(src_act, tgt_arm, name, loc_scale=1.0):
    """Copy an action for a same-rig armature: keys stay in bone-local space; location keys are
    multiplied by loc_scale. Channels for bones missing on the target are dropped."""
    act = src_act.copy()
    act.name = name
    act.use_fake_user = True
    bones = {b.name for b in tgt_arm.data.bones}
    dropped = set()
    for cb in action_channelbags(act):
        for fc in list(cb.fcurves):
            dp = fc.data_path
            if dp.startswith('pose.bones["'):
                bn = dp.split('"')[1]
                if bn not in bones:
                    dropped.add(bn)
                    cb.fcurves.remove(fc)
            else:
                dropped.add(dp)
                cb.fcurves.remove(fc)
    if dropped:
        warn(f"{name}: dropped channels not on target: {sorted(dropped)[:12]}{' ...' if len(dropped) > 12 else ''}")
    scale_location_curves(act, loc_scale)
    return act, action_object_slot(act)


def _bone_channels(action, slot):
    ch = {}
    for fc in action_fcurves(action, slot):
        dp = fc.data_path
        if not dp.startswith('pose.bones["'):
            continue
        bn = dp.split('"')[1]
        prop = dp.rsplit(".", 1)[-1]
        ch.setdefault(bn, {}).setdefault(prop, {})[fc.array_index] = fc
    return ch


def _eval(chs, prop, n, default, frame):
    d = chs.get(prop)
    if not d:
        return list(default)
    return [d[i].evaluate(frame) if i in d else default[i] for i in range(n)]


def lateral_yaw(arm) -> float | None:
    """Yaw (radians, about world Z) of the character's left->right axis, from Left*/Right* bones."""
    lefts, rights = [], []
    mw = arm.matrix_world
    for b in arm.data.bones:
        n = b.name.lower().split(":")[-1]
        if n.startswith("left") or n.endswith(("_l", ".l", "left")):
            lefts.append(mw @ b.head_local)
        elif n.startswith("right") or n.endswith(("_r", ".r", "right")):
            rights.append(mw @ b.head_local)
    if not lefts or not rights:
        return None
    lv = sum(lefts, mathutils.Vector()) / len(lefts) - sum(rights, mathutils.Vector()) / len(rights)
    if lv.x * lv.x + lv.y * lv.y < 1e-12:
        return None
    return math.atan2(lv.y, lv.x)


def leg_height(arm, hips):
    """Hips joint height above the lowest joint (world units). Uses joint heads only: bone
    tails of imported glTF rigs are synthesized by the importer."""
    mw = arm.matrix_world
    zs = [(mw @ b.head_local).z for b in arm.data.bones]
    return (mw @ hips.head_local).z - min(zs)


def match_bones(src_arm, tgt_arm, explicit=None):
    """target bone name -> source bone name. Exact names first, then names compared without a
    namespace prefix ('mixamorig:'), case, '_', '.', ' '. `explicit` (tgt->src) wins."""
    def norm(n):
        return n.split(":")[-1].lower().replace("_", "").replace(".", "").replace(" ", "")
    src = {b.name for b in src_arm.data.bones}
    by_norm = {}
    for n in src:
        by_norm.setdefault(norm(n), n)
    out = {}
    for b in tgt_arm.data.bones:
        if explicit and b.name in explicit:
            if explicit[b.name] in src:
                out[b.name] = explicit[b.name]
            continue
        if b.name in src:
            out[b.name] = b.name
        elif norm(b.name) in by_norm:
            out[b.name] = by_norm[norm(b.name)]
    return out


def retarget_action(src_arm, src_act, tgt_arm, name, hips_mode="vertical", src_hips=None, tgt_hips=None,
                    align_yaw=True, step=1.0, bone_map=None):
    """Rotation-only retarget of `src_act` (animating src_arm) onto tgt_arm, by bone name.

    Each matched bone gets the same WORLD-space rotation relative to its rest pose as the source
    bone (so differing bone-axis conventions are handled); unmatched target bones follow their
    parent. Only the hips translation is transferred, scaled by the leg-length ratio
    (hips height above the lowest bone): hips_mode 'vertical' keeps the up component, 'full' all
    three, 'none' nothing. Assumes both rigs share a rest pose (both T-pose or both A-pose).
    If align_yaw, a difference in facing between the rigs (from Left*/Right* bones) is removed.
    """
    from mathutils import Matrix, Quaternion, Vector
    slot = action_object_slot(src_act)
    ch = _bone_channels(src_act, slot)
    sb_all = src_arm.data.bones
    tb_all = tgt_arm.data.bones
    s_order = bones_in_hierarchy_order(src_arm)
    t_order = bones_in_hierarchy_order(tgt_arm)
    S, T = src_arm.matrix_world.copy(), tgt_arm.matrix_world.copy()
    s_restrel = {b.name: local_rest(b) for b in s_order}
    t_restrel = {b.name: local_rest(b) for b in t_order}
    s_rest_w = {b.name: _rot(S @ b.matrix_local) for b in s_order}
    t_rest_w = {b.name: _rot(T @ b.matrix_local) for b in t_order}
    rot_t_obj = _rot(T)
    s_mode = {pb.name: pb.rotation_mode for pb in src_arm.pose.bones}

    smap = match_bones(src_arm, tgt_arm, bone_map)
    th = tgt_hips or find_hips(tgt_arm)
    if isinstance(th, str):
        th = tb_all[th]
    sh = src_hips or (sb_all[smap[th.name]] if th.name in smap else find_hips(src_arm))
    if isinstance(sh, str):
        sh = sb_all[sh]
    if isinstance(th, str):
        th = tb_all[th]
    ratio = leg_height(tgt_arm, th) / max(leg_height(src_arm, sh), 1e-9)
    s_hips_rest_w = S @ sh.head_local
    t_hips_rest_w = T @ th.head_local

    yaw = 0.0
    if align_yaw:
        ys, yt = lateral_yaw(src_arm), lateral_yaw(tgt_arm)
        if ys is not None and yt is not None:
            yaw = (yt - ys + math.pi) % (2 * math.pi) - math.pi
    Y = Quaternion((0, 0, 1), yaw)
    Yi = Y.inverted()
    Ym = Y.to_matrix()

    matched = [b.name for b in t_order if b.name in smap]
    f0, f1 = action_range(src_act)
    frames = []
    f = math.floor(f0)
    while f <= math.ceil(f1) + 1e-6:
        frames.append(float(f))
        f += step

    keys_q = {n: [] for n in matched}
    keys_l = []
    for fr in frames:
        # --- source pose, armature space then world
        M = {}
        for b in s_order:
            c = ch.get(b.name, {})
            loc = Vector(_eval(c, "location", 3, (0, 0, 0), fr))
            mode = s_mode.get(b.name, "QUATERNION")
            if mode == "QUATERNION":
                q = Quaternion(_eval(c, "rotation_quaternion", 4, (1, 0, 0, 0), fr)).normalized()
            elif mode == "AXIS_ANGLE":
                aa = _eval(c, "rotation_axis_angle", 4, (0, 0, 1, 0), fr)
                q = Quaternion(Vector(aa[1:]), aa[0])
            else:
                q = mathutils.Euler(_eval(c, "rotation_euler", 3, (0, 0, 0), fr), mode).to_quaternion()
            sc = Vector(_eval(c, "scale", 3, (1, 1, 1), fr))
            L = Matrix.LocRotScale(loc, q, sc)
            M[b.name] = (M[b.parent.name] @ s_restrel[b.name] if b.parent else b.matrix_local) @ L
        D = {}
        for n in matched:
            sn = smap[n]
            Rw = _rot(S @ M[sn])
            D[n] = Y @ (Rw @ s_rest_w[sn].inverted()) @ Yi
        d_hips = Ym @ ((S @ M[sh.name]).to_translation() - s_hips_rest_w)
        # --- target, top-down
        Rp = {}
        Wp = {}
        for b in t_order:
            n = b.name
            par_R = Rp[b.parent.name] if b.parent else rot_t_obj
            par_W = Wp[b.parent.name] if b.parent else T
            rr = _rot(t_restrel[n])
            if n in D:
                q = ((par_R @ rr).inverted() @ D[n] @ t_rest_w[n]).normalized()
                keys_q[n].append(q)
            else:
                q = Quaternion()
            Rp[n] = par_R @ rr @ q
            base = par_W @ t_restrel[n]
            loc = Vector((0, 0, 0))
            if n == th.name and hips_mode != "none":
                dd = d_hips * ratio
                if hips_mode == "vertical":
                    dd = Vector((0, 0, dd.z))
                P = t_hips_rest_w + dd
                loc = base.inverted() @ P
                keys_l.append(loc)
            Wp[n] = base @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()

    act, aslot, cb = new_action_for(tgt_arm, name)
    written = 0
    for n in matched:
        qs = keys_q[n]
        if all(abs(q.w) > 1 - 1e-7 for q in qs):
            continue
        prev = None
        for i, q in enumerate(qs):
            if prev is not None and prev.dot(q) < 0:
                qs[i] = -q
            prev = qs[i]
        for i in range(4):
            fcurve_set_keys(cb, f'pose.bones["{n}"].rotation_quaternion', i, frames, [q[i] for q in qs], group=n)
        written += 1
    if keys_l:
        for i in range(3):
            fcurve_set_keys(cb, f'pose.bones["{th.name}"].location', i, frames, [v[i] for v in keys_l], group=th.name)
    for pb in tgt_arm.pose.bones:
        if pb.name in keys_q:
            pb.rotation_mode = "QUATERNION"
    info = {"name": name, "frames": [frames[0], frames[-1]], "bones_written": written,
            "bones_matched": len(matched), "bones_target": len(t_order),
            "unmatched_source_bones": sorted(set(ch) - set(smap.values())),
            "unmatched_target_bones": sorted(set(tb_all.keys()) - set(smap)),
            "hips": [sh.name, th.name], "leg_ratio": round(ratio, 5), "yaw_align_deg": round(math.degrees(yaw), 3)}
    return act, aslot, info
