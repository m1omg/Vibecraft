"""Synthesize rigged test characters (Meshy-like) for the Vibecraft asset tools.

Run with the bpy interpreter:
    /opt/bpyenv/v313/bin/python tools/tests/make_test_rigs.py --out-dir /tmp/rigs

Writes, per variant, one GLB per animation clip (each file holds the full mesh +
armature and exactly ONE action, all named "Take 001" like generator exports):
    char_a_idle.glb char_a_walk.glb char_a_attack.glb char_a_death.glb char_a_rest.glb
    char_b_idle.glb char_b_walk.glb char_b_rest.glb

Variant a: 1.8 m human proportions, legs 50% of height, armature object at identity.
Variant b: 1.2 m stocky dwarf, legs 36% of height, data authored in centimetres with
           an armature object scale of 0.01 (what FBX->GLB converted rigs look like).
Both share bone names / hierarchy / rest bone directions (T-pose), so a rotation-only
retarget between them should reproduce bone directions exactly.

The skinned mesh is a voxel-remeshed union of ellipsoids (~25-40k tris, one connected
manifold), automatic (bone heat) weights, cylindrical UVs with a real seam at the back,
and a 2048 px texture with a white front centre-line, a yellow visor (front of head)
and a magenta tabard (team-colour test region). Variant a also holds an unskinned sword parented
to the RightHand bone (bone-parented props are how some generators attach weapons).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402  (must precede bmesh)
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

import vc_bpy as vc  # noqa: E402

VARIANTS = {
    "a": dict(height=1.8, leg=0.50, girth=1.0, unit=1.0, clips=("idle", "walk", "attack", "death"), sword=True),
    "b": dict(height=1.2, leg=0.36, girth=1.45, unit=100.0, clips=("idle", "walk")),
}


def bone_layout(H, leg, girth):
    hip = leg * H
    neck = 0.83 * H
    sw = 0.10 * H * (0.8 + 0.2 * girth)
    sh = neck - 0.03 * H
    lx = 0.055 * H * (0.7 + 0.3 * girth)
    b = {
        "Hips": ((0, 0, hip), (0, 0, hip + 0.08 * H), None),
        "Spine": ((0, 0, hip + 0.08 * H), (0, 0, hip + 0.08 * H + 0.45 * (neck - hip - 0.08 * H)), "Hips"),
        "Spine1": ((0, 0, hip + 0.08 * H + 0.45 * (neck - hip - 0.08 * H)), (0, 0, neck), "Spine"),
        "Neck": ((0, 0, neck), (0, 0, neck + 0.05 * H), "Spine1"),
        "Head": ((0, 0, neck + 0.05 * H), (0, 0, H), "Neck"),
    }
    for side, s in (("Left", 1), ("Right", -1)):
        b[f"{side}Shoulder"] = ((s * 0.02 * H, 0, sh), (s * sw, 0, sh), "Spine1")
        b[f"{side}Arm"] = ((s * sw, 0, sh), (s * (sw + 0.16 * H), 0, sh), f"{side}Shoulder")
        b[f"{side}ForeArm"] = ((s * (sw + 0.16 * H), 0, sh), (s * (sw + 0.30 * H), 0, sh), f"{side}Arm")
        b[f"{side}Hand"] = ((s * (sw + 0.30 * H), 0, sh), (s * (sw + 0.37 * H), 0, sh), f"{side}ForeArm")
        knee = 0.5 * hip
        ankle = 0.045 * H
        b[f"{side}UpLeg"] = ((s * lx, 0, hip), (s * lx, 0, knee), "Hips")
        b[f"{side}Leg"] = ((s * lx, 0, knee), (s * lx, 0, ankle), f"{side}UpLeg")
        b[f"{side}Foot"] = ((s * lx, 0, ankle), (s * lx, -0.07 * H, 0.012 * H), f"{side}Leg")
        b[f"{side}ToeBase"] = ((s * lx, -0.07 * H, 0.012 * H), (s * lx, -0.11 * H, 0.012 * H), f"{side}Foot")
    return b


def build_armature(name, layout):
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    vc.select_only([arm], arm)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for bn, (h, t, p) in layout.items():
        eb = arm_data.edit_bones.new(bn)
        eb.head, eb.tail = Vector(h), Vector(t)
        eb.roll = 0.0
        ebs[bn] = eb
    for bn, (h, t, p) in layout.items():
        if p:
            ebs[bn].parent = ebs[p]
            ebs[bn].use_connect = (Vector(layout[p][1]) - Vector(h)).length < 1e-6
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return arm


def ellipsoid(bm, center, axis_dir, half_len, r1, r2=None):
    r2 = r2 or r1
    geom = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
    verts = geom["verts"]
    d = Vector(axis_dir).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
    m = Matrix.Translation(Vector(center)) @ rot @ Matrix.Diagonal((r1, r2, half_len, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=verts)


def build_body(layout, H, girth):
    bm = bmesh.new()
    rad = {"UpLeg": 0.055, "Leg": 0.042, "Foot": 0.032, "ToeBase": 0.028, "Arm": 0.034,
           "ForeArm": 0.029, "Hand": 0.027, "Shoulder": 0.035, "Neck": 0.035}
    for bn, (h, t, p) in layout.items():
        h, t = Vector(h), Vector(t)
        key = bn.replace("Left", "").replace("Right", "")
        if key in rad:
            g = girth if key in ("UpLeg", "Leg", "Arm", "ForeArm", "Shoulder") else 1.0
            ellipsoid(bm, (h + t) / 2, t - h, (t - h).length * 0.62, rad[key] * H * g)
    # torso and head
    hip = Vector(layout["Hips"][0])
    neck = Vector(layout["Neck"][0])
    ellipsoid(bm, (hip + neck) / 2 + Vector((0, 0, 0.02 * H)), (0, 0, 1), (neck - hip).length * 0.62,
              0.13 * H * girth, 0.085 * H * girth)
    head = (Vector(layout["Head"][0]) + Vector(layout["Head"][1])) / 2
    ellipsoid(bm, head, (0, 0, 1), 0.075 * H, 0.062 * H)
    ellipsoid(bm, head + Vector((0, -0.06 * H, 0)), (0, -1, 0), 0.025 * H, 0.015 * H)  # nose: front = -Y
    me = bpy.data.meshes.new("body_src")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Body", me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("remesh", "REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = H / 150.0
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data
    obj.data = new_me
    new_me.name = "Body"
    bpy.data.meshes.remove(old)
    new_me.shade_smooth()
    return obj


def cylindrical_uvs(obj, H):
    me = obj.data
    uv = me.uv_layers.new(name="UVMap")
    co = [v.co for v in me.vertices]
    for poly in me.polygons:
        us = []
        for li in poly.loop_indices:
            c = co[me.loops[li].vertex_index]
            us.append(0.5 + math.atan2(c.x, -c.y) / (2 * math.pi))
        if max(us) - min(us) > 0.5:
            us = [u + 1.0 if u < 0.5 else u for u in us]
        for li, u in zip(poly.loop_indices, us):
            c = co[me.loops[li].vertex_index]
            uv.data[li].uv = (u, min(max(c.z / H, 0.0), 1.0))


def make_texture(name, size=2048):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size  # y = v (0 bottom row in Blender)
    img = np.zeros((size, size, 4), np.float32)
    # body colours by height band
    col = np.where((y < 0.45)[..., None], [0.20, 0.30, 0.65],
                   np.where((y < 0.82)[..., None], [0.62, 0.22, 0.18], [0.85, 0.65, 0.5]))
    checker = ((np.floor(x * 32) + np.floor(y * 32)) % 2) * 0.18 + 0.82
    img[..., :3] = col * checker[..., None]
    # magenta tabard on the front of the torso (team colour test)
    tab = (np.abs(x - 0.5) < 0.09) & (y > 0.5) & (y < 0.78)
    img[tab, :3] = [0.85, 0.1, 0.8]
    # white front centre-line and yellow visor
    img[(np.abs(x - 0.5) < 0.004), :3] = 1.0
    vis = (np.abs(x - 0.5) < 0.07) & (y > 0.88) & (y < 0.93)
    img[vis, :3] = [1.0, 0.9, 0.1]
    img[..., 3] = 1.0
    im = bpy.data.images.new(name, size, size, alpha=False)
    im.pixels.foreach_set(img.ravel())
    im.update()
    im.pack()
    im.file_format = "PNG"
    return im


def make_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def add_sword(arm, mat, H):
    """Unskinned prop parented to the RightHand BONE (how generators attach weapons)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new("Sword")
    bm.to_mesh(me)
    bm.free()
    uv = me.uv_layers.new(name="UVMap")
    for d in uv.data:
        d.uv = (0.25, 0.3)
    me.materials.append(mat)
    sw = bpy.data.objects.new("Sword", me)
    bpy.context.scene.collection.objects.link(sw)
    hand = arm.data.bones["RightHand"]
    sw.parent = arm
    sw.parent_type = "BONE"
    sw.parent_bone = hand.name
    tip = arm.matrix_world @ hand.tail_local
    sw.matrix_world = Matrix.Translation(tip + Vector((0, -0.3 * H / 1.8, 0))) @ Matrix.Diagonal(
        (0.03 * H, 0.6 * H / 1.8, 0.012 * H, 1.0))
    return sw


# ----------------------------------------------------------------------------- animation

def q_arm(arm, bone, axis_angle_list):
    """Local pose quaternion that rotates `bone` about armature-space axes (applied in
    order), as if its parent were at rest."""
    R = arm.data.bones[bone].matrix_local.to_quaternion()
    Q = Quaternion()
    for axis, ang in axis_angle_list:
        Q = Quaternion(Vector(axis), math.radians(ang)) @ Q
    return R.inverted() @ Q @ R


def q_dir(arm, bone, direction):
    R = arm.data.bones[bone].matrix_local.to_quaternion()
    b = arm.data.bones[bone]
    rest_dir = (b.tail_local - b.head_local).normalized()
    Q = rest_dir.rotation_difference(Vector(direction).normalized())
    return R.inverted() @ Q @ R


def loc_arm(arm, bone, world_delta, unit):
    R = arm.data.bones[bone].matrix_local.to_quaternion()
    return R.inverted() @ (Vector(world_delta) * unit)


def arms_down(arm, t_swing=0.0):
    out = {}
    for side, s in (("Left", 1), ("Right", -1)):
        out[f"{side}Arm"] = q_arm(arm, f"{side}Arm", [((0, 1, 0), 75 * s), ((1, 0, 0), t_swing * s)])
    return out


def clip_keys(arm, clip, H, unit):
    """Return (frames, {bone: [(frame, quat)]}, {bone: [(frame, loc)]})."""
    rot, loc = {}, {}

    def kr(b, f, q):
        rot.setdefault(b, []).append((f, q))

    def kl(b, f, v):
        loc.setdefault(b, []).append((f, v))

    if clip == "idle":
        n = 60
        for f in range(0, n + 1, 5):
            ph = 2 * math.pi * f / n
            for b, q in arms_down(arm, 4 * math.sin(ph)).items():
                kr(b, f, q)
            kr("Spine", f, q_arm(arm, "Spine", [((1, 0, 0), 3 * math.sin(ph))]))
            kr("Head", f, q_arm(arm, "Head", [((0, 0, 1), 8 * math.sin(ph))]))
            kl("Hips", f, loc_arm(arm, "Hips", (0, 0, -0.008 * H * (1 - math.cos(ph))), unit))
    elif clip == "walk":
        n = 30
        for f in range(0, n + 1, 3):
            ph = 2 * math.pi * f / n
            sw = math.cos(ph)  # extremes at 0% and 50% (contact poses)
            for side, s in (("Left", 1), ("Right", -1)):
                kr(f"{side}UpLeg", f, q_arm(arm, f"{side}UpLeg", [((1, 0, 0), -28 * sw * s)]))
                bend = 35 * max(0.0, math.sin(ph + (0 if s > 0 else math.pi) + 1.2))
                kr(f"{side}Leg", f, q_arm(arm, f"{side}Leg", [((1, 0, 0), bend)]))
            for b, q in arms_down(arm, 22 * sw).items():
                kr(b, f, q)
            kr("Spine", f, q_arm(arm, "Spine", [((0, 0, 1), 6 * sw)]))
            kl("Hips", f, loc_arm(arm, "Hips", (0, 0, -0.02 * H * abs(math.cos(ph))), unit))
    elif clip == "attack":
        n = 24
        dirs = {0: (-0.26, 0, -0.97), 8: (-0.25, 0.35, 0.9), 13: (-0.2, -0.95, 0.15), 18: (-0.2, -0.6, -0.75),
                24: (-0.26, 0, -0.97)}
        for f, d in dirs.items():
            kr("RightArm", f, q_dir(arm, "RightArm", d))
            kr("LeftArm", f, arms_down(arm)["LeftArm"])
            tw = {0: 0, 8: -20, 13: 25, 18: 15, 24: 0}[f]
            kr("Spine", f, q_arm(arm, "Spine", [((0, 0, 1), tw)]))
            kr("RightForeArm", f, q_arm(arm, "RightForeArm", [((0, 1, 0), {0: 0, 8: -40, 13: -5, 18: 0, 24: 0}[f])]))
    elif clip == "death":
        n = 40
        hip = arm.data.bones["Hips"].head_local.z / unit
        keys = {0: (0, 0, 0, 0), 12: (-25, 0.05, -0.12, 30), 28: (-80, 0.2, -0.75, 60), 40: (-88, 0.22, -0.8, 50)}
        for f, (ang, back, drop, kb) in keys.items():
            kr("Hips", f, q_arm(arm, "Hips", [((1, 0, 0), ang)]))
            kl("Hips", f, loc_arm(arm, "Hips", (0, back * H, drop * hip), unit))
            for side, s in (("Left", 1), ("Right", -1)):
                kr(f"{side}UpLeg", f, q_arm(arm, f"{side}UpLeg", [((1, 0, 0), -kb)]))
                kr(f"{side}Leg", f, q_arm(arm, f"{side}Leg", [((1, 0, 0), kb * 1.3)]))
            for b, q in arms_down(arm, -ang * 0.6).items():
                kr(b, f, q)
    else:
        raise ValueError(clip)
    return n, rot, loc


def make_action(arm, clip, H, unit, name="Take 001"):
    n, rot, loc = clip_keys(arm, clip, H, unit)
    act, slot, cb = vc.new_action_for(arm, name)
    for b, keys in rot.items():
        prev = None
        fixed = []
        for f, q in keys:
            q = q.normalized()
            if prev is not None and prev.dot(q) < 0:
                q = -q
            prev = q
            fixed.append((f, q))
        for i in range(4):
            vc.fcurve_set_keys(cb, f'pose.bones["{b}"].rotation_quaternion', i,
                               [f for f, _ in fixed], [q[i] for _, q in fixed], group=b)
    for b, keys in loc.items():
        for i in range(3):
            vc.fcurve_set_keys(cb, f'pose.bones["{b}"].location', i,
                               [f for f, _ in keys], [v[i] for _, v in keys], group=b)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    ad.action_slot = slot
    return act


def build_variant(key, spec, out_dir):
    vc.reset_scene()
    H, unit = spec["height"], spec["unit"]
    layout = bone_layout(H, spec["leg"], spec["girth"])
    arm = build_armature(f"char_{key}", layout)
    body = build_body(layout, H, spec["girth"])
    cylindrical_uvs(body, H)
    img = make_texture(f"char_{key}_tex")
    body.data.materials.append(make_material(f"char_{key}_material", img))
    vc.select_only([body, arm], arm)
    with vc.stdout_to_stderr():
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    ws = vc.weight_stats(body)
    if ws["unweighted_verts"]:
        vc.warn(f"variant {key}: {ws['unweighted_verts']} verts without weights after bone heat")
    if spec.get("sword"):
        add_sword(arm, body.data.materials[0], H)
    if unit != 1.0:
        # author in centimetres with an armature object scale of 1/unit
        S = Matrix.Diagonal((unit, unit, unit, 1.0))
        body.data.transform(S)
        arm.data.transform(S)
        arm.scale = (1 / unit,) * 3
        body.matrix_parent_inverse = Matrix.Identity(4)
    tris = vc.mesh_tris(body)
    vc.log(f"variant {key}: {tris} tris, {len(arm.data.bones)} bones, weights {ws['weighted_fraction']}")
    files = []
    p = os.path.join(out_dir, f"char_{key}_rest.glb")
    vc.export_glb(p, animations=False)
    files.append(p)
    for clip in spec["clips"]:
        act = make_action(arm, clip, H, unit)
        p = os.path.join(out_dir, f"char_{key}_{clip}.glb")
        vc.export_glb(p, animations=True)
        files.append(p)
        arm.animation_data.action = None
        bpy.data.actions.remove(act)
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
    return {"variant": key, "tris": tris, "bones": len(arm.data.bones), "weights": {
        k: v for k, v in ws.items() if not k.startswith("_")}, "files": files}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, help="output folder for the GLBs")
    ap.add_argument("--variants", default="a,b", help="comma list of variants to build (a,b)")
    args = ap.parse_args(vc.bpy_argv())
    os.makedirs(args.out_dir, exist_ok=True)
    res = [build_variant(k, VARIANTS[k], args.out_dir) for k in args.variants.split(",")]
    vc.emit_json({"rigs": res, "warnings": vc.warnings()})


if __name__ == "__main__":
    main()
