"""Normalize an AI-generated GLB (Tripo / Meshy / Hunyuan) into a game-ready Vibecraft model.

Run with the bpy interpreter:
    /opt/bpyenv/v313/bin/python tools/process_model.py in.glb --out assets/models/soldier.glb \\
        --target-tris 6000 --height 1.8 --tex-size 1024

Pipeline (each step optional where it makes sense):
  1. import GLB; bake every object transform into the data (armature included: rest bones are
     transformed and pose-location keys rescaled, so animations stay valid)
  2. join all meshes into one object (an armature, if present, is kept and re-bound)
  3. weld co-located vertices (UV seams stay as per-corner UV data, which keeps the
     decimator from tearing cracks along seams); --cleanup also removes loose geometry,
     degenerate faces and tiny floating islands
  4. decimate (collapse, quadric) to --target-tris; skin weights are interpolated by the
     decimator and verified afterwards (unweighted verts + posed-bounds comparison)
  5. origin -> bottom-centre of the bounds (feet on y=0 in Godot), scale to --height
     (or --width footprint), rotate by --facing / --yaw so the model faces -Z (Godot forward)
  6. smooth shading with sharp edges above --smooth-angle
  7. textures: downscale to --tex-size (Lanczos), JPEG for opaque colour maps, PNG for
     data maps, embedded in the GLB; images/materials get stable names
  8. optional team colour (--team-mask HUE): texels of that hue form a mask (<out>_team.png) and
     the faces they cover move to a second material '<name>_TEAM' (UnitView tints materials whose
     name contains TEAM)
  9. export GLB (no Draco/meshopt) with every animation; print a JSON summary on stdout

Facing convention: the exported model faces -Z in Godot space (Godot's forward, what
Node3D.look_at() and Unit.facing use: forward = (-sin f, 0, -cos f)). Raw AI GLBs normally face
+Z (glTF convention), so the default --facing +z turns them 180 degrees. --yaw D adds D degrees
counter-clockwise seen from above (about +Y), applied after --facing.
"""
from __future__ import annotations

import argparse
import io
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402  (must precede bmesh)
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import vc_bpy as vc  # noqa: E402

# yaw (deg, CCW about +Y) that turns a model facing <key> (glTF/Godot axes) to face -Z
FACING_YAW = {"+z": 180.0, "-z": 0.0, "+x": 90.0, "-x": -90.0}


def facing_arg(v):
    v = v.strip().lower()
    alias = {"z": "+z", "z+": "+z", "pz": "+z", "z-": "-z", "nz": "-z", "x": "+x", "x+": "+x", "px": "+x",
             "x-": "-x", "nx": "-x"}
    v = alias.get(v, v)
    if v not in FACING_YAW:
        raise argparse.ArgumentTypeError(f"facing must be one of {sorted(FACING_YAW)}")
    return v


def parse_args():
    ap = argparse.ArgumentParser(
        prog="process_model.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="source .glb")
    ap.add_argument("-o", "--out", required=True, help="output .glb path")
    g = ap.add_argument_group("geometry")
    g.add_argument("--target-tris", type=int, default=0, help="decimate to about this many triangles (0 = keep)")
    g.add_argument("--cleanup", action="store_true",
                   help="weld with --merge-dist, dissolve degenerate faces, delete loose verts/edges and "
                        "floating islands smaller than --min-island")
    g.add_argument("--merge-dist", type=float, default=None,
                   help="weld distance in OUTPUT metres (default: exact duplicates only; 0.0005 with --cleanup)")
    g.add_argument("--min-island", type=float, default=0.01,
                   help="with --cleanup: delete disconnected pieces whose bbox diagonal is below this fraction "
                        "of the model diagonal (default 0.01)")
    g.add_argument("--symmetry", choices=["none", "x"], default="none",
                   help="symmetric decimation about the model's X axis (good for characters)")
    g.add_argument("--smooth-angle", type=float, default=60.0,
                   help="shade smooth, splitting normals at edges sharper than this (degrees). 180 = all smooth, "
                        "0 = flat")
    t = ap.add_argument_group("transform")
    t.add_argument("--height", type=float, default=0.0, help="uniformly scale so the height is this many metres")
    t.add_argument("--width", type=float, default=0.0,
                   help="alternative to --height: scale so the larger horizontal extent (X/Z) is this many metres "
                        "(buildings: footprint)")
    t.add_argument("--scale", type=float, default=0.0, help="explicit uniform scale factor (overrides height/width)")
    t.add_argument("--yaw", type=float, default=0.0, help="extra rotation about up (+Y Godot), degrees CCW from above")
    t.add_argument("--facing", type=facing_arg, default="+z", metavar="{+z,-z,+x,-x}",
                   help="direction the INPUT model faces in glTF/Godot axes; it is turned to face -Z. "
                        "AI generators usually output +z (default). Write negatives as --facing=-x or x-")
    t.add_argument("--no-recenter", action="store_true", help="keep the original origin")
    x = ap.add_argument_group("textures / materials")
    x.add_argument("--tex-size", type=int, default=1024, help="max texture edge in px (never upscales)")
    x.add_argument("--tex-format", choices=["auto", "png", "jpeg"], default="auto",
                   help="auto: JPEG for opaque colour/emission maps, PNG for normal/ORM/alpha maps")
    x.add_argument("--jpeg-quality", type=int, default=90)
    x.add_argument("--drop-maps", default="",
                   help="comma list of maps to strip: normal,orm,emission,occlusion (saves memory)")
    x.add_argument("--name", "--material-name", dest="name", default=None,
                   help="base name for the mesh node, material(s) and images (default: output file stem)")
    x.add_argument("--team-mask", default=None, metavar="HUE[:TOL[:SATMIN]]",
                   help="team-colour area = base-colour texels within TOL degrees of HUE (sat >= SATMIN, "
                        "default 25 and 0.35), e.g. 300 for magenta. Writes <out>_team.png and moves the faces "
                        "whose UVs sample the mask (> --team-threshold) to a material named <name>_TEAM")
    x.add_argument("--team-threshold", type=float, default=0.5,
                   help="mean mask value over a face's corners+centre that makes it a team face (default 0.5)")
    x.add_argument("--team-desaturate", action="store_true",
                   help="with --team-mask: turn masked base-colour pixels grey so the shader can tint them")
    a = ap.add_argument_group("animation")
    a.add_argument("--clip-name", default=None, help="rename the (single) animation clip, e.g. walk")
    a.add_argument("--rename-clip", action="append", default=[], metavar="OLD=NEW", help="rename a clip; repeatable")
    a.add_argument("--no-anims", action="store_true", help="drop all animations")
    a.add_argument("--fps", type=int, default=vc.FPS_DEFAULT, help="scene fps used for import/export (default 30)")
    ap.add_argument("--json", default=None, help="also write the JSON summary to this file")
    ap.add_argument("--no-verify", action="store_true", help="skip re-importing the output for verification")
    return ap.parse_args(vc.bpy_argv())


# ----------------------------------------------------------------------------- steps

def bake_transforms(meshes, arm, others):
    """Bake world transforms into mesh/armature data; everything ends at identity."""
    info = {"armature_object_scale": 1.0}
    if arm is not None:
        # bone-parented children must be read in the REST pose (bind pose), not the current frame
        arm.data.pose_position = "REST"
        bpy.context.view_layer.update()
    for o in meshes:
        if o.data.users > 1:
            o.data = o.data.copy()
    bone_parented = []
    for o in meshes:
        mw = o.matrix_world.copy()
        if o.parent_type == "BONE" and o.parent is not None and o.parent_bone:
            bone_parented.append((o, o.parent_bone))
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    if arm is not None:
        arm.data.pose_position = "POSE"
        mw = arm.matrix_world.copy()
        s = vc.uniform_scale(mw)
        arm.parent = None
        arm.data.transform(mw)
        arm.matrix_world = Matrix.Identity(4)
        info["armature_object_scale"] = round(s, 6)
        for act in vc.actions_for_armature(arm):
            vc.scale_location_curves(act, s)
        # props parented to a bone: give them a full-weight vertex group so they stay attached
        for o, bone in bone_parented:
            vg = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
            vg.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
            if not any(m.type == "ARMATURE" for m in o.modifiers):
                o.modifiers.new("Armature", "ARMATURE").object = arm
            vc.warn(f"mesh '{o.name}' was parented to bone '{bone}', converted to a skinned weight group")
    for o in others:
        if o.animation_data and o.animation_data.action:
            vc.warn(f"object-level animation on '{o.name}' dropped (only armature animation is kept)")
    vc.delete_objects(others)
    return info


def join_meshes(meshes, arm, name):
    if len(meshes) > 1:
        vc.select_only(meshes, meshes[0])
        with vc.stdout_to_stderr():
            bpy.ops.object.join()
    body = meshes[0]
    body.name = name
    body.data.name = name
    # exactly one armature modifier, first in the stack
    arms = [m for m in body.modifiers if m.type == "ARMATURE"]
    for m in list(body.modifiers):
        if m.type != "ARMATURE":
            vc.warn(f"dropping modifier '{m.name}' ({m.type}) from imported mesh")
            body.modifiers.remove(m)
    for m in arms[1:]:
        body.modifiers.remove(m)
    if arm is not None:
        mod = arms[0] if arms else body.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        body.parent = arm
        body.matrix_parent_inverse = Matrix.Identity(4)
    else:
        for m in arms:
            body.modifiers.remove(m)
    return body


def weld_and_cleanup(body, dist, cleanup, min_island_frac):
    me = body.data
    bm = bmesh.new()
    bm.from_mesh(me)
    v0, f0 = len(bm.verts), len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    res = {"welded_verts": v0 - len(bm.verts)}
    if cleanup:
        bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges[:])
        loose_e = [e for e in bm.edges if not e.link_faces]
        bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
        loose_v = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
        # islands
        bm.verts.ensure_lookup_table()
        seen = set()
        islands = []
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, isl = [v], []
            seen.add(v.index)
            while stack:
                cur = stack.pop()
                isl.append(cur)
                for e in cur.link_edges:
                    o = e.other_vert(cur)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
            islands.append(isl)
        if len(islands) > 1:
            allco = np.array([v.co[:] for v in bm.verts])
            diag = np.linalg.norm(allco.max(0) - allco.min(0))
            kill = []
            for isl in islands:
                co = np.array([v.co[:] for v in isl])
                if np.linalg.norm(co.max(0) - co.min(0)) < min_island_frac * diag:
                    kill.extend(isl)
            if kill and len(kill) < len(bm.verts):
                bmesh.ops.delete(bm, geom=kill, context="VERTS")
            res["islands"] = len(islands)
            res["islands_removed_verts"] = len(kill)
        res["faces_removed"] = f0 - len(bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return res


def clear_custom_normals(body):
    me = body.data
    if me.has_custom_normals:
        vc.select_only([body], body)
        with vc.stdout_to_stderr():
            bpy.ops.mesh.customdata_custom_splitnormals_clear()


def eval_tris(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def decimate(body, target, symmetry):
    cur = vc.mesh_tris(body)
    if target <= 0 or cur <= target:
        return {"skipped": True, "tris": cur}
    if body.data.shape_keys:
        vc.warn("removing shape keys (decimation cannot keep them)")
        body.shape_key_clear()
    arm_mods = [m for m in body.modifiers if m.type == "ARMATURE"]
    for m in arm_mods:
        m.show_viewport = False  # evaluate the bind-pose base mesh only
    mod = body.modifiers.new("vc_decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.use_collapse_triangulate = True
    if symmetry != "none":
        mod.use_symmetry = True
        mod.symmetry_axis = symmetry.upper()
    while body.modifiers.find(mod.name) > 0:
        body.modifiers.move(body.modifiers.find(mod.name), 0)
    ratio = target / cur
    got = cur
    for _ in range(4):
        mod.ratio = min(1.0, max(1e-4, ratio))
        got = eval_tris(body)
        if abs(got - target) <= 0.02 * target:
            break
        ratio *= target / max(got, 1)
    used_ratio = mod.ratio
    vc.select_only([body], body)
    with vc.stdout_to_stderr():
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for m in arm_mods:
        m.show_viewport = True
    return {"skipped": False, "ratio": round(used_ratio, 5), "tris": vc.mesh_tris(body)}


def limit_weights(body, n):
    """Keep the n strongest bone influences per vertex and normalize (what glTF/Godot use)."""
    if not body.vertex_groups:
        return
    vc.select_only([body], body)
    with vc.stdout_to_stderr():
        bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=1e-4, keep_single=True)
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=n)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def posed_bounds(arm, body, actions):
    """Evaluated (skinned) bounds at the middle frame of every action."""
    out = {}
    if arm is None or not actions:
        return out
    ad = arm.animation_data or arm.animation_data_create()
    saved = (ad.action, ad.use_nla)
    ad.use_nla = False
    scn = bpy.context.scene
    for act in actions:
        ad.action = act
        slot = vc.action_object_slot(act)
        if slot is not None:
            ad.action_slot = slot
        a, b = vc.action_range(act)
        scn.frame_set(int(round((a + b) / 2)))
        lo, hi = vc.world_bounds([body], use_eval=True)
        out[act.name] = (lo.copy(), hi.copy())
    ad.action, ad.use_nla = saved
    scn.frame_set(0)
    return out


def normalize_transform(body, arm, actions, args, lo, hi):
    size = hi - lo
    if args.scale > 0:
        s = args.scale
    elif args.height > 0:
        s = args.height / max(size.z, 1e-9)
    elif args.width > 0:
        s = args.width / max(size.x, size.y, 1e-9)
    else:
        s = 1.0
    yaw = FACING_YAW[args.facing] + args.yaw
    if args.no_recenter:
        T = Matrix.Identity(4)
    else:
        T = Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    M = Matrix.Scale(s, 4) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ T
    body.data.transform(M)
    if arm is not None:
        arm.data.transform(M)
        for act in actions:
            vc.scale_location_curves(act, s)
    body.data.update()
    return {"scale_factor": round(s, 6), "yaw_deg": yaw}


def set_shading(body, angle):
    me = body.data
    n = len(me.polygons)
    if angle <= 0:
        me.polygons.foreach_set("use_smooth", [False] * n)
    else:
        me.polygons.foreach_set("use_smooth", [True] * n)
        for e in me.edges:
            e.use_edge_sharp = False
        if angle < 180:
            me.set_sharp_from_angle(angle=math.radians(angle))
    me.update()


# ----------------------------------------------------------------------------- textures

def _socket_role(sock_name):
    s = sock_name.lower()
    if s in ("base color", "alpha"):
        return "basecolor"
    if s.startswith("emission"):
        return "emission"
    if s in ("roughness", "metallic"):
        return "orm"
    if s == "normal":
        return "normal"
    if "occlusion" in s:
        return "occlusion"
    return None


def image_roles(mat):
    """Map image -> (role, tex_node list) by following links downstream to the BSDF."""
    roles = {}
    if not mat or not mat.node_tree:
        return roles
    nt = mat.node_tree
    for node in nt.nodes:
        if node.type != "TEX_IMAGE" or node.image is None:
            continue
        role = None
        frontier = [node]
        visited = set()
        while frontier and role is None:
            n = frontier.pop()
            if n.name in visited:
                continue
            visited.add(n.name)
            for out in n.outputs:
                for link in out.links:
                    tn = link.to_node
                    if tn.type in ("BSDF_PRINCIPLED", "GROUP") or tn.type == "OUTPUT_MATERIAL":
                        role = _socket_role(link.to_socket.name) or role
                    elif tn.type == "NORMAL_MAP":
                        role = "normal"
                    else:
                        frontier.append(tn)
        roles.setdefault(node.image, [role or "other", []])[1].append(node)
    return roles


def image_to_pil(img):
    from PIL import Image
    if img.packed_file is not None:
        return Image.open(io.BytesIO(img.packed_file.data))
    path = bpy.path.abspath(img.filepath)
    if path and os.path.isfile(path):
        return Image.open(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    arr = (np.clip(px.reshape(h, w, 4)[::-1], 0, 1) * 255 + 0.5).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def team_mask(pil_rgb, spec, desaturate):
    from PIL import Image, ImageFilter
    parts = [float(p) for p in spec.split(":")]
    hue, tol, smin = parts[0], (parts[1] if len(parts) > 1 else 25.0), (parts[2] if len(parts) > 2 else 0.35)
    hsv = np.asarray(pil_rgb.convert("HSV"), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0] * 360.0, hsv[..., 1], hsv[..., 2]
    dh = np.abs((h - hue + 180.0) % 360.0 - 180.0)
    m = np.clip((tol - dh) / max(tol * 0.25, 1e-3), 0, 1) * np.clip((s - smin) / 0.1, 0, 1) * np.clip((v - 0.12) / 0.1, 0, 1)
    mask = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8))
    out_rgb = pil_rgb
    if desaturate:
        rgb = np.asarray(pil_rgb.convert("RGB"), dtype=np.float32)
        lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        mm = (np.asarray(mask, np.float32) / 255.0)[..., None]
        grey = np.clip(lum * 1.15, 0, 255)  # slightly brighter so the tint reads
        mixed = rgb * (1 - mm) + grey * mm
        out_rgb = Image.fromarray(mixed.astype(np.uint8), "RGB")
        if pil_rgb.mode == "RGBA":
            out_rgb.putalpha(pil_rgb.getchannel("A"))
    coverage = float((np.asarray(mask) > 127).mean())
    return mask, out_rgb, coverage


def process_textures(body, args, base_name, tmpdir):
    from PIL import Image
    drop = {d.strip() for d in args.drop_maps.split(",") if d.strip()}
    report = []
    team = []
    mats = []
    for s in body.material_slots:
        if s.material and s.material not in mats:
            mats.append(s.material)
    done = set()
    for mi, mat in enumerate(mats):
        prefix = base_name if len(mats) == 1 else f"{base_name}_{mi}"
        roles = image_roles(mat)
        roles = {i: r for i, r in roles.items() if i.name not in done}  # image shared by materials
        for img, (role, nodes) in roles.items():
            if role in drop:
                for n in nodes:
                    mat.node_tree.nodes.remove(n)
                report.append({"role": role, "image": img.name, "dropped": True})
                continue
            src = image_to_pil(img)
            fmt_in = (src.format or "RAW").upper()
            w, h = src.size
            k = min(1.0, args.tex_size / max(w, h))
            nw, nh = max(1, round(w * k)), max(1, round(h * k))
            has_alpha = src.mode in ("RGBA", "LA", "PA") or "transparency" in src.info
            alpha_used = False
            if has_alpha:
                a = np.asarray(src.convert("RGBA").getchannel("A"))
                alpha_used = int(a.min()) < 250
            pil = src
            if (nw, nh) != (w, h):
                pil = src.convert("RGBA" if alpha_used else "RGB").resize((nw, nh), Image.LANCZOS)
            colour = role in ("basecolor", "emission", "other")
            if args.tex_format == "png":
                fmt = "PNG"
            elif args.tex_format == "jpeg":
                fmt = "PNG" if alpha_used else "JPEG"
            else:
                fmt = "JPEG" if (colour and not alpha_used) else "PNG"
            team_cov = None
            if role == "basecolor" and args.team_mask:
                mask, pil, team_cov = team_mask(pil.convert("RGBA" if alpha_used else "RGB"), args.team_mask,
                                                args.team_desaturate)
                team.append((mat, mask, team_cov))
            unchanged = (pil is src) and fmt_in == fmt and img.packed_file is not None
            new_name = f"{prefix}_{role}" if role != "other" else f"{prefix}_{img.name}"
            if not unchanged:
                ext = ".jpg" if fmt == "JPEG" else ".png"
                path = os.path.join(tmpdir, new_name + ext)
                if fmt == "JPEG":
                    pil.convert("RGB").save(path, "JPEG", quality=args.jpeg_quality, subsampling=0, optimize=True)
                else:
                    if pil.mode not in ("RGB", "RGBA", "L", "LA"):
                        pil = pil.convert("RGBA" if alpha_used else "RGB")
                    if not alpha_used and pil.mode == "RGBA":
                        pil = pil.convert("RGB")
                    pil.save(path, "PNG", optimize=True)
                new = bpy.data.images.load(path)
                new.colorspace_settings.name = img.colorspace_settings.name
                new.alpha_mode = img.alpha_mode
                new.pack()
                img.user_remap(new)
                old_name = img.name
                bpy.data.images.remove(img)
                new.name = new_name
                img = new
            else:
                old_name = img.name
                img.name = new_name
            done.add(img.name)
            entry = {"role": role, "image": img.name, "source": old_name, "size_before": [w, h],
                     "size_after": [nw, nh], "format": fmt.lower(), "alpha": alpha_used}
            if team_cov is not None:
                entry["team_mask_coverage"] = round(team_cov, 5)
            report.append(entry)
    return report, team


def rename_materials(body, base):
    mats = []
    for s in body.material_slots:
        if s.material and s.material not in mats:
            mats.append(s.material)
    for i, m in enumerate(mats):
        m.name = base if len(mats) == 1 else f"{base}_{i}"
    return [m.name for m in mats]


def split_team_faces(body, mat, mask_img, threshold):
    """Move faces of `mat` whose UVs sample the team mask to a copy named '<mat>_TEAM'."""
    me = body.data
    if not me.uv_layers:
        vc.warn("no UVs: cannot split team faces")
        return 0
    slot = next(i for i, s in enumerate(body.material_slots) if s.material == mat)
    m = np.asarray(mask_img, np.float32) / 255.0
    H, W = m.shape
    nl, npoly = len(me.loops), len(me.polygons)
    uv = np.empty(nl * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    start = np.empty(npoly, np.int32)
    total = np.empty(npoly, np.int32)
    midx = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_start", start)
    me.polygons.foreach_get("loop_total", total)
    me.polygons.foreach_get("material_index", midx)
    poly_of_loop = np.repeat(np.arange(npoly), total)

    def sample(u, v):
        x = np.clip(((u % 1.0) * W).astype(np.int64), 0, W - 1)
        y = np.clip(((1.0 - (v % 1.0)) * H).astype(np.int64), 0, H - 1)
        return m[y, x]

    corner = sample(uv[:, 0], uv[:, 1])
    csum = np.bincount(poly_of_loop, weights=corner, minlength=npoly)
    cu = np.bincount(poly_of_loop, weights=uv[:, 0], minlength=npoly) / total
    cv = np.bincount(poly_of_loop, weights=uv[:, 1], minlength=npoly) / total
    score = (csum + 2.0 * sample(cu, cv)) / (total + 2.0)
    sel = (midx == slot) & (score > threshold)
    n = int(sel.sum())
    if n == 0:
        return 0
    team_mat = mat.copy()
    team_mat.name = mat.name + "_TEAM"
    me.materials.append(team_mat)
    midx[sel] = len(me.materials) - 1
    me.polygons.foreach_set("material_index", midx)
    me.update()
    return n


# ----------------------------------------------------------------------------- main

def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    stem = os.path.splitext(os.path.basename(out))[0]
    base_name = args.name or stem
    vc.reset_scene(args.fps)
    objs = vc.import_glb(args.input)
    meshes = [o for o in objs if o.type == "MESH"]
    arms = [o for o in objs if o.type == "ARMATURE"]
    if not meshes:
        raise SystemExit("no mesh in input")
    tris_before = sum(vc.mesh_tris(o) for o in meshes)
    arm = None
    if arms:
        used = {}
        for o in meshes:
            for m in o.modifiers:
                if m.type == "ARMATURE" and m.object:
                    used[m.object] = used.get(m.object, 0) + 1
        arm = max(arms, key=lambda a: (used.get(a, 0), len(a.data.bones)))
        if len(arms) > 1:
            vc.warn(f"{len(arms)} armatures found; keeping '{arm.name}'")
    others = [o for o in objs if o not in meshes and o is not arm]
    if arm is not None:
        others = [o for o in others if o.type != "ARMATURE"] + [a for a in arms if a is not arm]

    summary = {"input": os.path.abspath(args.input), "output": out, "tris_before": tris_before}
    summary.update(bake_transforms(meshes, arm, others))
    body = join_meshes(meshes, arm, base_name)
    actions = vc.actions_for_armature(arm) if arm is not None else []
    if args.no_anims and actions:
        for act in actions:
            bpy.data.actions.remove(act)
        actions = []
    if arm is not None and arm.animation_data and args.no_anims:
        arm.animation_data_clear()

    lo, hi = vc.world_bounds([body])
    diag = (hi - lo).length
    size = hi - lo
    s_plan = (args.scale if args.scale > 0 else args.height / max(size.z, 1e-9) if args.height > 0
              else args.width / max(size.x, size.y, 1e-9) if args.width > 0 else 1.0)
    if args.merge_dist is not None:
        dist = args.merge_dist / s_plan
    elif args.cleanup:
        dist = 0.0005 / s_plan
    else:
        dist = 1e-5 * diag
    summary["source_dims_godot"] = vc.godot_dims(lo, hi)

    w_before = vc.weight_stats(body) if arm is not None else None
    pose_before = posed_bounds(arm, body, actions)
    summary["weld"] = weld_and_cleanup(body, dist, args.cleanup, args.min_island)
    clear_custom_normals(body)
    summary["decimate"] = decimate(body, args.target_tris, args.symmetry)

    if arm is not None:
        limit_weights(body, 4)
        w_after = vc.weight_stats(body)
        lost = sorted(set(w_before["_used_names"]) - set(w_after["_used_names"]))
        pose_after = posed_bounds(arm, body, actions)
        dev = {}
        h = max(size.z, 1e-9)
        for k in pose_before:
            (l0, h0), (l1, h1) = pose_before[k], pose_after[k]
            dev[k] = round(max(max(abs(a - b) for a, b in zip(l0, l1)), max(abs(a - b) for a, b in zip(h0, h1))) / h, 5)
        summary["skin"] = {
            "before": {k: v for k, v in w_before.items() if not k.startswith("_")},
            "after": {k: v for k, v in w_after.items() if not k.startswith("_")},
            "groups_lost": lost,
            "posed_bounds_deviation_frac_of_height": dev,
        }
        if w_after["unweighted_verts"]:
            vc.warn(f"{w_after['unweighted_verts']} vertices have no skin weight after processing")
        if lost:
            vc.warn(f"bone influences lost by decimation: {lost}")
        if dev and max(dev.values()) > 0.03:
            vc.warn(f"posed bounds moved by up to {max(dev.values()):.3f} x height after decimation")

    lo, hi = vc.world_bounds([body])
    summary["transform"] = normalize_transform(body, arm, actions, args, lo, hi)
    set_shading(body, args.smooth_angle)

    tmp = tempfile.TemporaryDirectory(prefix="vc_tex_")
    summary["textures"], team = process_textures(body, args, base_name, tmp.name)
    rename_materials(body, base_name)
    if args.team_mask:
        if not team:
            vc.warn("--team-mask given but no base colour texture found")
        else:
            best = max(team, key=lambda t: t[2])
            mask_path = os.path.splitext(out)[0] + "_team.png"
            os.makedirs(os.path.dirname(mask_path), exist_ok=True)
            best[1].save(mask_path, optimize=True)
            faces = sum(split_team_faces(body, mat, mask, args.team_threshold) for mat, mask, _ in team)
            summary["team_mask"] = {"path": mask_path, "texel_coverage": round(best[2], 5),
                                    "team_faces": faces, "team_face_fraction": round(faces / len(body.data.polygons), 5)}
            if best[2] < 0.001 or faces == 0:
                vc.warn("team mask is (almost) empty or covers no face - check the hue")
    vc.select_only([body], body)
    with vc.stdout_to_stderr():
        try:
            bpy.ops.object.material_slot_remove_unused()
        except RuntimeError:
            pass
    summary["materials"] = [s.material.name for s in body.material_slots if s.material]

    # animations: rename + stash so every action exports as its own clip
    renames = dict(r.split("=", 1) for r in args.rename_clip)
    if args.clip_name:
        if len(actions) == 1:
            renames[actions[0].name] = args.clip_name
        elif actions:
            vc.warn(f"--clip-name ignored: {len(actions)} clips present (use --rename-clip OLD=NEW)")
    for act in actions:
        if act.name in renames:
            act.name = renames[act.name]
    if arm is not None:
        arm.name = "Armature"
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.rotation_euler = (0, 0, 0)
            pb.scale = (1, 1, 1)
        if actions:
            vc.stash_actions(arm, [(a, vc.action_object_slot(a)) for a in actions])
    vc.purge_orphans()

    vc.export_glb(out, animations=bool(actions), jpeg_quality=args.jpeg_quality)
    tmp.cleanup()

    lo, hi = vc.world_bounds([body])
    summary.update({
        "tris_after": vc.mesh_tris(body),
        "verts_after": len(body.data.vertices),
        "dims_godot_m": vc.godot_dims(lo, hi),
        "bounds_min_godot": [round(lo.x, 4), round(lo.z, 4), round(-hi.y, 4)],
        "bones": len(arm.data.bones) if arm is not None else 0,
        "actions": [vc.action_info(a) for a in actions],
        "file_bytes": os.path.getsize(out),
    })
    if not args.no_verify:
        summary["verify"] = verify(out)
    summary["warnings"] = vc.warnings()
    vc.emit_json(summary, args.json)


def verify(path):
    """Re-import the written GLB in a clean scene and report what is in it."""
    vc.reset_scene()
    objs = vc.import_glb(path)
    meshes = [o for o in objs if o.type == "MESH"]
    arms = [o for o in objs if o.type == "ARMATURE"]
    res = {"meshes": len(meshes), "tris": sum(vc.mesh_tris(o) for o in meshes),
           "armatures": len(arms), "actions": sorted(a.name for a in bpy.data.actions),
           "images": sorted(f"{i.name}:{i.size[0]}x{i.size[1]}" for i in bpy.data.images)}
    if arms and meshes:
        res["weighted_fraction"] = vc.weight_stats(meshes[0])["weighted_fraction"]
    return res


if __name__ == "__main__":
    main()
