#!/usr/bin/env python3
"""Visual QA for a GLB: load it in Godot exactly like the game would (GLTFDocument), print a
JSON report, render a labelled contact sheet PNG.

    python3 tools/render_preview.py assets/models/soldier.glb -o /tmp/soldier_sheet.png

The sheet shows, left to right: RTS camera (56 deg pitch, from the model's front), front,
side, back three-quarter, and an "in-game" 256 px crop taken with the real RTS camera
(pitch 56, FOV 47, 26 m away at 1920x1080), so you see the true on-screen size. Below that,
one row per animation clip with frames at --fractions of the clip length (default 0% and 50%).
A 1.8 m capsule stands next to the model for scale, the ground grid has 1 m lines and darker
2 m (terrain TILE) lines, and the red arrow points along -Z: the model's forward direction.
Materials whose name contains TEAM are tinted with --team-color, as UnitView does.

Requirements: Godot 4.7 (`godot` on PATH or --godot / $VC_GODOT), xvfb-run, Vulkan
(lavapipe works: VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json is set automatically
when that file exists and VK_ICD_FILENAMES is unset). Pillow for the sheet.

--info-only runs just the headless load check (no Xvfb/GPU): exit code 1 if Godot fails to
load the file or prints ERROR lines.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, "preview")
LVP = "/usr/share/vulkan/icd.d/lvp_icd.json"
IGNORED_STDERR = (
    re.compile(r"ALSA lib"),
    re.compile(r"audio", re.I),
    re.compile(r"^\s*at: "),
    re.compile(r"Condition \"status < 0\""),
    # A GLB outside tools/preview whose external images have Godot .import files (the building kit's shared
    # sheets): ResourceLoader looks for the imported .ctex in the preview project's .godot, fails, and
    # GLTFDocument falls back to reading the image bytes, so the texture still loads.
    re.compile(r"(Unable to open file|Failed loading resource): (res://\.godot/imported/\S+\.ctex"
               r"|/\S+\.(png|jpe?g|webp))\."),
)


def godot_bin(arg):
    return arg or os.environ.get("VC_GODOT") or shutil.which("godot") or "/usr/local/bin/godot"


def run(cmd, env=None, timeout=600):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def godot_errors(text: str) -> list[str]:
    errs = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(("ERROR:", "SCRIPT ERROR:", "USER ERROR:")):
            ctx = " ".join(lines[i:i + 2])
            if any(r.search(ctx) for r in IGNORED_STDERR):
                continue
            errs.append(ln.strip())
    return errs


def inspect(glbs, godot, timeout=300):
    cmd = [godot, "--headless", "--audio-driver", "Dummy", "--path", PREVIEW, "-s", "inspect.gd", "--"]
    cmd += [os.path.abspath(g) for g in glbs]
    code, out, err = run(cmd, timeout=timeout)
    data = None
    for ln in out.splitlines():
        if ln.startswith("VC_JSON:"):
            data = json.loads(ln[len("VC_JSON:"):])
    errors = godot_errors(out + "\n" + err)
    if data is None:
        raise SystemExit(f"godot inspect failed (exit {code}):\n{out}\n{err}")
    return data, errors, code


def render_frames(glb, out_dir, godot, args):
    env = dict(os.environ)
    if "VK_ICD_FILENAMES" not in env and os.path.exists(LVP):
        env["VK_ICD_FILENAMES"] = LVP
    cmd = []
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd += ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"]
    cmd += [godot, "--rendering-driver", "vulkan", "--audio-driver", "Dummy", "--path", PREVIEW,
            "-s", "turntable.gd", "--", "--glb", os.path.abspath(glb), "--out-dir", out_dir,
            "--size", str(args.size), "--fractions", args.fractions, "--clips", args.clips]
    if args.no_ingame:
        cmd.append("--no-ingame")
    cmd += ["--team-color", args.team_color]
    code, out, err = run(cmd, env=env, timeout=args.timeout)
    meta_path = os.path.join(out_dir, "meta.json")
    if code != 0 or not os.path.exists(meta_path):
        raise SystemExit(f"godot render failed (exit {code}):\n{out[-3000:]}\n{err[-3000:]}")
    with open(meta_path) as f:
        return json.load(f), godot_errors(out + "\n" + err)


def font(size):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def compose(frames_dir, meta, info, glb, out_png, cell):
    from PIL import Image, ImageDraw
    pad, label_h, head_h = 6, 22, 58
    f_lab, f_head, f_small = font(14), font(18), font(13)
    cells = [(os.path.join(frames_dir, v["file"]), v["label"]) for v in meta["views"]]
    if meta.get("ingame"):
        cells.append((os.path.join(frames_dir, meta["ingame"]["file"]), "in-game scale (1080p)"))
    rows = [cells]
    clip_cells = []
    for c in meta.get("clips", []):
        for fr in c["frames"]:
            clip_cells.append((os.path.join(frames_dir, fr["file"]),
                               f'{c["name"]} @{int(round(fr["fraction"] * 100))}% ({fr["time"]:.2f}s)'))
    per_row = max(len(cells), 4)
    for i in range(0, len(clip_cells), per_row):
        rows.append(clip_cells[i:i + per_row])
    W = pad + per_row * (cell + pad)
    H = head_h + sum(cell + label_h + pad for _ in rows) + pad
    sheet = Image.new("RGB", (W, H), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    rep = info or {}
    size = rep.get("aabb_size", meta.get("aabb_size", [0, 0, 0]))
    skel = rep.get("skeletons") or []
    anims = rep.get("animations") or []
    texs = rep.get("textures") or []
    title = os.path.basename(glb)
    l1 = (f"{title}   tris {rep.get('tris_total', '?')}   size W {size[0]:.2f} x H {size[1]:.2f} x D {size[2]:.2f} m"
          f"   bones {skel[0]['bones'] if skel else 0}   clips {len(anims)}")
    l2 = ("textures: " + ", ".join(f"{t['name']} {t['size'][0]}x{t['size'][1]}" for t in texs)
          + ("   clips: " + ", ".join(f"{a['name']} {a['length']:.2f}s" for a in anims) if anims else ""))
    d.text((pad + 2, 8), l1, fill=(235, 235, 235), font=f_head)
    d.text((pad + 2, 34), l2[:220], fill=(170, 175, 185), font=f_small)
    y = head_h
    for r in rows:
        x = pad
        for path, label in r:
            im = Image.open(path).convert("RGB")
            if im.size != (cell, cell):
                if im.width <= cell // 1.4:
                    im = im.resize((cell, cell), Image.NEAREST)  # in-game crop: keep pixels crisp
                else:
                    im = im.resize((cell, cell), Image.LANCZOS)
            sheet.paste(im, (x, y))
            d.text((x + 3, y + cell + 3), label, fill=(220, 220, 220), font=f_lab)
            x += cell + pad
        y += cell + label_h + pad
    os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
    sheet.save(out_png, optimize=True)
    return out_png


def main():
    ap = argparse.ArgumentParser(prog="render_preview.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("glb", nargs="+", help="GLB file(s); one sheet per file")
    ap.add_argument("-o", "--out", default=None,
                    help="output PNG (single input) or directory (several inputs). Default: <glb>_sheet.png")
    ap.add_argument("--size", type=int, default=384, help="cell size in px (default 384)")
    ap.add_argument("--fractions", default="0,0.5", help="clip positions to capture, fractions of length")
    ap.add_argument("--clips", default="all", help="comma list of clips to capture (default all)")
    ap.add_argument("--no-ingame", action="store_true", help="skip the in-game scale crop")
    ap.add_argument("--team-color", default="#2f6bff",
                    help="tint for materials whose name contains TEAM, like UnitView (default blue)")
    ap.add_argument("--keep-frames", default=None, help="keep the individual frames in this folder")
    ap.add_argument("--info-only", action="store_true", help="only run the headless Godot load check")
    ap.add_argument("--godot", default=None, help="godot binary (default: $VC_GODOT or godot on PATH)")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    godot = godot_bin(args.godot)

    info, errs, code = inspect(args.glb, godot)
    result = {"files": []}
    failed = bool(errs) or code != 0
    for g, rep in zip(args.glb, info["files"]):
        entry = {"glb": os.path.abspath(g), "godot": rep}
        if "error" in rep:
            failed = True
        if not args.info_only and "error" not in rep:
            if args.out and len(args.glb) > 1:
                os.makedirs(args.out, exist_ok=True)
                out_png = os.path.join(args.out, os.path.splitext(os.path.basename(g))[0] + "_sheet.png")
            else:
                out_png = args.out or os.path.splitext(g)[0] + "_sheet.png"
            tmp = args.keep_frames or tempfile.mkdtemp(prefix="vc_frames_")
            if args.keep_frames and len(args.glb) > 1:
                tmp = os.path.join(args.keep_frames, os.path.splitext(os.path.basename(g))[0])
            os.makedirs(tmp, exist_ok=True)
            meta, rerrs = render_frames(g, tmp, godot, args)
            entry["sheet"] = compose(tmp, meta, rep, g, out_png, args.size)
            entry["render_errors"] = rerrs
            if not args.keep_frames:
                shutil.rmtree(tmp, ignore_errors=True)
        result["files"].append(entry)
    result["load_errors"] = errs
    result["ok"] = not failed
    print(json.dumps(result, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
