"""Shared helpers for the Vibecraft Blender (bpy) asset tools.

Imported by process_model.py, merge_anims.py, retarget_anims.py and the tests.
Must be run with the bpy-enabled interpreter (e.g. /opt/bpyenv/v313/bin/python).

Conventions (see tools/README.md):
  * Blender is Z-up, the glTF exporter converts to Y-up (Godot space).
    Blender (x, y, z)  ->  glTF/Godot (x, z, -y).
  * Exported models FACE +Z in Godot/glTF space (= -Y in Blender), feet on y=0,
    origin at the bottom-centre of the bounds, 1 unit = 1 metre.
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
            guess_original_bind_pose=True,
            import_pack_images=True,
            import_select_created_objects=False,
        )
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
    for o in vl.objects:
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
