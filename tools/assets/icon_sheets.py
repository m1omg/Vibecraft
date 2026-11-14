#!/usr/bin/env python3
"""Game icons (128 x 128 PNG) from generated 2x2 sheets and from building renders (art bible §5.5 T9, pipeline §4.4).

    python3 tools/assets/icon_sheets.py items       # assets_src/icons/items/sheets/<sheet>.png -> assets/ui/icons/...
    python3 tools/assets/icon_sheets.py buildings   # assets_src/icons/buildings/renders/<id>.png -> assets/ui/icons/buildings/
    python3 tools/assets/icon_sheets.py all

items: each sheet listed in tools/prompts/icons/item_icon_sheets.json is split into its four quadrants (1 top-left, 2 top-right,
3 bottom-left, 4 bottom-right), the painted panel's rounded gutter is trimmed, the square is fitted to 116 px (Lanczos) with a light
unsharp mask and set in the 6 px pewter item frame. Ids starting with "item_" go to icons/items, building ids (buildings.json) to
icons/buildings, everything else (shop services) to icons/services.

buildings: each transparent render from tools/assets/render_building_icons.gd is cropped to its opaque pixels, scaled so its
upper part fills the icon (the T9 "upper-third read": the foundation may run off the bottom edge), set on the faction's dark
vignette with a soft accent glow behind it, and framed with the 6 px bronze "normal" frame. A building that already has an icon
from a sheet (the model-less Coaching Inn) is skipped.

Every output gets a Godot .import file with mipmaps on (the HUD draws them at 40-60 px).
"""
from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHEETS_JSON = ROOT / "tools/prompts/icons/item_icon_sheets.json"
SHEET_DIR = ROOT / "assets_src/icons/items/sheets"
RENDER_DIR = ROOT / "assets_src/icons/buildings/renders"
OUT = ROOT / "assets/ui/icons"
SIZE = 128
BORDER = 6
GUTTER = 0.075             # share of a quadrant trimmed on each side (panel gaps and rounded corners)

# art bible §5.5 T9: background tint and accent per kind
BG = {"kingdom": (0x2A, 0x10, 0x14), "clans": (0x0E, 0x24, 0x26), "neutral": (0x24, 0x1C, 0x14)}
ACCENT = {"kingdom": (0xF0, 0x8A, 0x2A), "clans": (0xE0, 0xB0, 0x40), "neutral": (0xF2, 0xC2, 0x6E)}
FRAMES = {
    # light (upper left) and dark (lower right) bevel colours
    "item": ((0xC4, 0xC6, 0xCC), (0x48, 0x4A, 0x52)),     # pewter
    "normal": ((0xB0, 0x7F, 0x3E), (0x3A, 0x26, 0x12)),   # bronze
}

IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://{path}"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=1
"""


def building_ids() -> dict[str, dict]:
    doc = json.loads((ROOT / "data/buildings.json").read_text())
    return {k: v for k, v in doc.get("buildings", doc).items() if isinstance(v, dict) and not k.startswith("_")}


def frame(img: Image.Image, kind: str) -> Image.Image:
    """Draws the 6 px bevelled frame over the outer edge of a SIZE x SIZE RGBA image."""
    light, dark = FRAMES[kind]
    out = img.copy()
    d = ImageDraw.Draw(out)
    n = SIZE - 1
    for i in range(BORDER):
        t = i / (BORDER - 1)
        # outer and inner rows darker, the middle catches the light
        k = 0.55 + 0.45 * (1.0 - abs(t - 0.4) / 0.6)
        lc = tuple(int(c * k) for c in light)
        dc = tuple(int(c * k) for c in dark)
        d.line([(i, n - i), (i, i), (n - i, i)], fill=lc + (255,))           # left and top: lit
        d.line([(n - i, i + 1), (n - i, n - i), (i + 1, n - i)], fill=dc + (255,))  # right and bottom: shade
    d.rectangle([0, 0, n, n], outline=(0x14, 0x11, 0x0E, 255))
    d.rectangle([BORDER, BORDER, n - BORDER, n - BORDER], outline=(0x14, 0x11, 0x0E, 200))
    return out


def save(img: Image.Image, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGBA").save(path, optimize=True)
    rel = path.relative_to(ROOT).as_posix()
    imp = path.with_name(path.name + ".import")
    if not imp.exists() or "mipmaps/generate=true" not in imp.read_text():
        imp.write_text(IMPORT_TEMPLATE.format(path=rel))
    print("wrote", rel)


def fit_inner(img: Image.Image) -> Image.Image:
    inner = SIZE - 2 * BORDER
    face = img.resize((inner, inner), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    canvas.paste(face.convert("RGBA"), (BORDER, BORDER))
    return canvas


def out_dir_for(icon_id: str, buildings: dict) -> pathlib.Path:
    if icon_id.startswith("item_"):
        return OUT / "items"
    if icon_id in buildings:
        return OUT / "buildings"
    return OUT / "services"


def do_items() -> None:
    spec = json.loads(SHEETS_JSON.read_text())
    buildings = building_ids()
    for sheet in spec["sheets"]:
        src = SHEET_DIR / f"{sheet['id']}.png"
        if not src.exists():
            print("missing sheet", src.relative_to(ROOT))
            continue
        im = Image.open(src).convert("RGB")
        w, h = im.size
        qw, qh = w // 2, h // 2
        for q, (icon_id, _subject) in enumerate(sheet["icons"]):
            x0, y0 = (q % 2) * qw, (q // 2) * qh
            gx, gy = int(qw * GUTTER), int(qh * GUTTER)
            tile = im.crop((x0 + gx, y0 + gy, x0 + qw - gx, y0 + qh - gy))
            kind = "normal" if icon_id in buildings else "item"
            save(frame(fit_inner(tile), kind), out_dir_for(icon_id, buildings) / f"{icon_id}.png")


def vignette(kind: str) -> Image.Image:
    bg = BG[kind]
    acc = ACCENT[kind]
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    c = (SIZE - 1) / 2.0
    for y in range(SIZE):
        for x in range(SIZE):
            # light pooled a little above the centre, toward the upper left key light
            dx, dy = (x - c * 0.92) / c, (y - c * 0.8) / c
            r = min(1.0, (dx * dx + dy * dy) ** 0.5)
            k = 1.9 - 1.3 * r
            glow = max(0.0, 1.0 - r * 1.25) * 0.14
            px[x, y] = tuple(min(255, int(b * k + a * glow)) for b, a in zip(bg, acc))
    return img


def do_buildings() -> None:
    buildings = building_ids()
    spec = json.loads(SHEETS_JSON.read_text())
    from_sheets = {i[0] for s in spec["sheets"] for i in s["icons"]}
    for src in sorted(RENDER_DIR.glob("*.png")):
        bid = src.stem
        if bid in from_sheets:
            print("skip", bid, "(icon from a sheet)")
            continue
        d = buildings.get(bid, {})
        fac = str(d.get("faction", ""))
        kind = fac if fac in BG else "neutral"
        rgba = Image.open(src).convert("RGBA")
        box = rgba.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if box is None:
            print("empty render", bid)
            continue
        sub = rgba.crop(box)
        bw, bh = sub.size
        inner = SIZE - 2 * BORDER
        # the upper part leads: fill the width (up to 92 %), let a tall building's foot (up to a fifth of
        # its height) run off the bottom edge
        scale = min(inner * 0.92 / bw, inner * 0.97 / (bh * 0.8))
        sub = sub.resize((max(1, round(bw * scale)), max(1, round(bh * scale))), Image.LANCZOS)
        face = vignette(kind).convert("RGBA")
        ox = BORDER + (inner - sub.width) // 2
        oy = BORDER + max(int(inner * 0.04), (inner - sub.height) // 2)
        # soft accent glow behind the silhouette
        glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        mask = Image.new("L", (SIZE, SIZE), 0)
        mask.paste(sub.getchannel("A"), (ox, oy))
        mask = mask.filter(ImageFilter.GaussianBlur(7)).point(lambda a: int(a * 0.55))
        glow.paste(Image.new("RGBA", (SIZE, SIZE), ACCENT[kind] + (255,)), (0, 0), mask)
        face.alpha_composite(glow)
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        layer.paste(sub, (ox, oy), sub)
        face.alpha_composite(layer.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2)))
        save(frame(face, "normal"), OUT / "buildings" / f"{bid}.png")


def main(argv: list[str]) -> int:
    what = argv[1] if len(argv) > 1 else "all"
    if what in ("items", "all"):
        do_items()
    if what in ("buildings", "all"):
        do_buildings()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
