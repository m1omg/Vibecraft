"""Build extra unrigged test GLBs from any textured GLB (e.g. the sample boulder).

    /opt/bpyenv/v313/bin/python tools/tests/make_test_props.py --src boulder.glb --out-dir /tmp/props

Writes:
  pbr_prop.glb    the source mesh with a full PBR set at 2048 px: base colour (RGBA with a
                  fully opaque alpha channel), tangent-space normal map, metallic-roughness map
                  and an emission map -> exercises texture role detection / formats.
  multi_prop.glb  two copies of the mesh as separate objects (Y-up data in centimetres) under
                  an empty rotated 90 deg about X and scaled 0.01 (typical FBX->GLB hierarchy), the
                  second copy smaller, offset, with its own material whose base colour has real alpha (cutout)
                  -> exercises transform baking, joining, multi-material naming, PNG alpha path.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix  # noqa: E402

import vc_bpy as vc  # noqa: E402


def gen_image(name, size, rgba, non_color=False):
    im = bpy.data.images.new(name, size, size, alpha=True)
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    im.update()
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    im.pack()
    im.file_format = "PNG"
    return im


def noise(size, seed, scale=24):
    rng = np.random.default_rng(seed)
    small = rng.random((scale, scale)).astype(np.float32)
    from PIL import Image
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC),
                      np.float32) / 255.0


def add_pbr(mat, size=2048):
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    n = noise(size, 1)
    # normal map from the noise gradient
    gy, gx = np.gradient(n * 8.0)
    nrm = np.dstack([-gx, -gy, np.ones_like(n)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    rgba = np.dstack([nrm * 0.5 + 0.5, np.ones_like(n)])
    tex_n = nt.nodes.new("ShaderNodeTexImage")
    tex_n.image = gen_image("src_normal", size, rgba, non_color=True)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex_n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    # metallic (B) / roughness (G)
    mr = np.dstack([np.zeros_like(n), 0.4 + 0.5 * n, (n > 0.8).astype(np.float32), np.ones_like(n)])
    tex_mr = nt.nodes.new("ShaderNodeTexImage")
    tex_mr.image = gen_image("src_mr", size, mr, non_color=True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex_mr.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    # emission
    em = np.dstack([(n > 0.85) * 1.0, (n > 0.85) * 0.5, np.zeros_like(n), np.ones_like(n)]).astype(np.float32)
    tex_e = nt.nodes.new("ShaderNodeTexImage")
    tex_e.image = gen_image("src_emission", size, em)
    nt.links.new(tex_e.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(vc.bpy_argv())
    os.makedirs(a.out_dir, exist_ok=True)

    # --- pbr_prop
    vc.reset_scene()
    objs = vc.import_glb(a.src)
    mesh = next(o for o in objs if o.type == "MESH")
    mat = mesh.data.materials[0]
    # make the base colour RGBA (opaque alpha) at 2048
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.image.scale(2048, 2048)
    add_pbr(mat)
    vc.export_glb(os.path.join(a.out_dir, "pbr_prop.glb"), animations=False)

    # --- multi_prop
    vc.reset_scene()
    objs = vc.import_glb(a.src)
    m1 = next(o for o in objs if o.type == "MESH")
    for o in objs:
        o.parent = None
    root = bpy.data.objects.new("RootNode", None)
    bpy.context.scene.collection.objects.link(root)
    # FBX-style: mesh data authored Y-up in centimetres, root node rotates +90 X and scales 0.01
    root.matrix_world = Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Scale(0.01, 4)
    m1.data.transform(Matrix.Scale(100, 4) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    m2 = m1.copy()
    m2.data = m1.data.copy()
    bpy.context.scene.collection.objects.link(m2)
    for o, loc, sc in ((m1, (0, 0, 0), 1.0), (m2, (85, 0, 0), 0.6)):
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Translation(loc) @ Matrix.Scale(sc, 4)
    mat2 = bpy.data.materials.new("cutout")
    mat2.use_nodes = True
    nt = mat2.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    n = noise(512, 3)
    rgba = np.dstack([n, n * 0.6, n * 0.2, (n > 0.4).astype(np.float32)])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = gen_image("leaf_rgba", 512, rgba)
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
    m2.data.materials.clear()
    m2.data.materials.append(mat2)
    vc.export_glb(os.path.join(a.out_dir, "multi_prop.glb"), animations=False)
    vc.emit_json({"files": [os.path.join(a.out_dir, f) for f in ("pbr_prop.glb", "multi_prop.glb")]})


if __name__ == "__main__":
    main()
