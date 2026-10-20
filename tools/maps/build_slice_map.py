#!/usr/bin/env python3
"""Builds data/maps/slice.json (Wether Downs, map id `wether_downs`, tileset `gv`) from the written brief.

Usage: python3 tools/maps/build_slice_map.py [--out data/maps/slice.json] [--hall-footprint-m 8]

Inputs (all ours, slice-plan.md §1):
  * data/maps/wether_downs_sketch.txt  the §1.3 ASCII sketch (1 char = 2 x 2 tiles): levels, trees, water, edge
  * the §1.4 landmark table and §1.5 ramp table, copied below (exact positions win over sketch letters)
  * data/creep_camps.json              camp templates (creep lists are expanded into the map's camp entries)
  * docs/design/slice-content.json     creep route and landmark list (copied into the map's meta)

Output: the MapData JSON format (src/world/map_data.gd; data/SCHEMA.md "maps"): per-tile layers as digit rows
(tex 0..7, cliff 0..2, water, boundary), explicit ramps, starts, gold mines, camps, neutral buildings, trees on
the 1 m tree grid, plus `meta` (starts, expansions, gold amounts, creep route, lanes, critters, landmarks).

Rules applied (slice-plan §1.2, rules §3.3): mirror symmetry across the NW-SE diagonal (x, z) -> (z, x); every
hall pad is flat and tree-free; hall-seam gap 6.0 m edge to edge; trees are placed as a diagonal pair per 2 x 2 m
tile (impassable checkerboard on the 1 m tree grid, so tree walls hold); the outer 2 tiles are unpathable boundary.
Deterministic: no randomness except a fixed-seed hash for tree types and texture noise.
"""
import argparse
import json
import math
import os
import sys
from collections import deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SIZE = 96
TILE = 2.0
CLIFF_H = 1.75
CHAR_TILES = 2

# texture slots (terrain.gdshader; slice-plan §1.12)
T_GRASS, T_THICK, T_DIRT, T_CRACKED, T_ROCK, T_GRASSY_DIRT, T_MEADOW, T_ROAD = range(8)

# slice-plan §1.5: (rect tiles x, z, w, h), ascending dir, low level
RAMPS = [
    ((27, 75, 2, 4), (-1, 0), 1),   # P1 main, ascends west
    ((75, 27, 4, 2), (0, -1), 1),   # P2 main, ascends north
    ((36, 46, 2, 4), (-1, 0), 0),   # basin W (P1 side)
    ((46, 36, 4, 2), (0, -1), 0),   # basin N (P2 side)
    ((46, 58, 4, 2), (0, 1), 0),    # basin S (P1 side)
    ((58, 46, 2, 4), (1, 0), 0),    # basin E (P2 side)
    ((18, 27, 4, 2), (0, 1), 0),    # spring dell S (P1)
    ((27, 18, 2, 4), (1, 0), 0),    # spring dell E (P2)
    ((36, 41, 4, 2), (0, -1), 1),   # K1 knoll S face (P1), ascends north into the knoll
    ((41, 36, 2, 4), (-1, 0), 1),   # K1 knoll E face (P2)
    ((53, 56, 2, 4), (1, 0), 1),    # K2 knoll W face (P1)
    ((56, 53, 4, 2), (0, 1), 1),    # K2 knoll N face (P2)
]

GOLD_MAIN = 12000
GOLD_EXPANSION = 8000


def mirror(p):
    return (p[1], p[0])


class Map:
    def __init__(self, hall_m):
        self.hall_m = hall_m
        self.level = [[1] * SIZE for _ in range(SIZE)]   # [z][x]
        self.water = [[0] * SIZE for _ in range(SIZE)]
        self.boundary = [[0] * SIZE for _ in range(SIZE)]
        self.treed = [[0] * SIZE for _ in range(SIZE)]   # tile carries a tree pair
        self.ramp = [[0] * SIZE for _ in range(SIZE)]    # ramp index + 1
        self.tex = [[T_GRASS] * SIZE for _ in range(SIZE)]
        self.ramps = []
        self.sketch = []

    # --- sketch --------------------------------------------------------------------------------
    def load_sketch(self, path):
        lines = open(path, encoding="utf-8").read().split("\n")
        start = lines.index("----") + 3          # skip the two column-header rows
        rows = [ln[4:].ljust(48)[:48] for ln in lines[start:start + 48]]
        assert len(rows) == 48, "sketch must have 48 rows"
        self.sketch = rows
        lv = [[None] * 48 for _ in range(48)]
        known = {":": 2, ".": 1, ",": 0}
        for z in range(48):
            for x in range(48):
                c = rows[z][x]
                if c in known:
                    lv[z][x] = known[c]
        # '/' chars: lower neighbour level for now (ramps fix them below)
        for z in range(48):
            for x in range(48):
                if rows[z][x] == "/":
                    ns = [lv[zz][xx] for zz in range(z - 1, z + 2) for xx in range(x - 1, x + 2)
                          if 0 <= zz < 48 and 0 <= xx < 48 and lv[zz][xx] is not None]
                    lv[z][x] = min(ns) if ns else 1
        # everything else (trees, water, landmarks, edge): level of the nearest known char (BFS; ties -> max)
        dist = [[None] * 48 for _ in range(48)]
        q = deque()
        for z in range(48):
            for x in range(48):
                if lv[z][x] is not None:
                    dist[z][x] = 0
                    q.append((x, z))
        while q:
            x, z = q.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, nz = x + dx, z + dz
                if 0 <= nx < 48 and 0 <= nz < 48:
                    if dist[nz][nx] is None:
                        dist[nz][nx] = dist[z][x] + 1
                        lv[nz][nx] = lv[z][x]
                        q.append((nx, nz))
                    elif dist[nz][nx] == dist[z][x] + 1 and lv[z][x] > lv[nz][nx]:
                        lv[nz][nx] = lv[z][x]
        for z in range(SIZE):
            for x in range(SIZE):
                cz, cx = z // CHAR_TILES, x // CHAR_TILES
                c = rows[cz][cx]
                self.level[z][x] = lv[cz][cx]
                if c == "~":
                    self.water[z][x] = 1
                if c == "#":
                    self.treed[z][x] = 1
                if c == " ":
                    self.boundary[z][x] = 1
                    self.treed[z][x] = 1
        self._ramp_chars = [(x, z) for z in range(SIZE) for x in range(SIZE)
                            if rows[z // CHAR_TILES][x // CHAR_TILES] == "/"]

    # --- ramps ---------------------------------------------------------------------------------
    def apply_ramps(self):
        for i, (rect, d, low) in enumerate(RAMPS):
            rx, rz, rw, rh = rect
            self.ramps.append({"rect": [rx, rz, rw, rh], "dir": list(d), "low": low})
            for z in range(rz, rz + rh):
                for x in range(rx, rx + rw):
                    self.ramp[z][x] = i + 1
                    self.level[z][x] = low
                    self.treed[z][x] = 0
                    self.water[z][x] = 0
        # sketch '/' tiles outside the exact ramps: high level beyond the high end, low level elsewhere
        for (x, z) in self._ramp_chars:
            if self.ramp[z][x]:
                continue
            best = None
            for i, (rect, d, low) in enumerate(RAMPS):
                rx, rz, rw, rh = rect
                cx, cz = rx + rw / 2.0, rz + rh / 2.0
                dd = math.hypot(x + 0.5 - cx, z + 0.5 - cz)
                if best is None or dd < best[0]:
                    best = (dd, rect, d, low)
            _, (rx, rz, rw, rh), d, low = best
            along = (x - rx if d[0] > 0 else rx + rw - 1 - x) if d[0] != 0 else (z - rz if d[1] > 0 else rz + rh - 1 - z)
            span = rw if d[0] != 0 else rh
            self.level[z][x] = low + 1 if along >= span else low
        # approaches: one tile beyond each end must be at the right level and walkable
        for i, (rect, d, low) in enumerate(RAMPS):
            rx, rz, rw, rh = rect
            for k in range(rh if d[0] != 0 else rw):
                if d[0] != 0:
                    hi_t = (rx - 1 if d[0] < 0 else rx + rw, rz + k)
                    lo_t = (rx + rw if d[0] < 0 else rx - 1, rz + k)
                else:
                    hi_t = (rx + k, rz - 1 if d[1] < 0 else rz + rh)
                    lo_t = (rx + k, rz + rh if d[1] < 0 else rz - 1)
                for (tx, tz), want in ((hi_t, low + 1), (lo_t, low)):
                    self.level[tz][tx] = want
                    self.treed[tz][tx] = 0
                    self.water[tz][tx] = 0

    # --- pads, clearings -----------------------------------------------------------------------
    def tiles_in_rect_m(self, x0, z0, x1, z1):
        for tz in range(max(0, int(math.floor(z0 / TILE))), min(SIZE, int(math.ceil(z1 / TILE)))):
            for tx in range(max(0, int(math.floor(x0 / TILE))), min(SIZE, int(math.ceil(x1 / TILE)))):
                yield tx, tz

    def flatten_pad(self, cx, cz, size_m, margin_m=2.0, clear_margin_m=3.0):
        lvl = self.level[int(cz // TILE)][int(cx // TILE)]
        h = size_m / 2.0
        for tx, tz in self.tiles_in_rect_m(cx - h - margin_m, cz - h - margin_m, cx + h + margin_m, cz + h + margin_m):
            assert self.ramp[tz][tx] == 0, "pad at (%s, %s) overlaps a ramp" % (cx, cz)
            self.level[tz][tx] = lvl
            self.water[tz][tx] = 0
        self.clear(cx, cz, h + clear_margin_m, square=True)
        return lvl

    def clear(self, cx, cz, r, square=False):
        for tx, tz in self.tiles_in_rect_m(cx - r, cz - r, cx + r, cz + r):
            px, pz = (tx + 0.5) * TILE, (tz + 0.5) * TILE
            if square or math.hypot(px - cx, pz - cz) <= r + 1.0:
                if not self.boundary[tz][tx]:
                    self.treed[tz][tx] = 0

    # --- symmetry ------------------------------------------------------------------------------
    def symmetrize(self):
        """Copy the P1 half (z >= x, SW) onto the mirror half so every layer is exactly symmetric."""
        for layer in (self.level, self.water, self.boundary, self.treed, self.tex):
            for z in range(SIZE):
                for x in range(z):
                    layer[x][z] = layer[z][x]

    def asymmetric(self):
        bad = 0
        for layer in (self.level, self.water, self.boundary, self.treed, self.ramp, self.tex):
            for z in range(SIZE):
                for x in range(SIZE):
                    if layer is self.ramp:
                        a, b = layer[z][x] > 0, layer[x][z] > 0
                    else:
                        a, b = layer[z][x], layer[x][z]
                    if a != b:
                        bad += 1
        return bad

    # --- heights (same rules as MapData.compute_heights) -----------------------------------------
    def corner_heights(self, tx, tz):
        i = self.ramp[tz][tx]
        base = self.level[tz][tx] * CLIFF_H
        out = []
        for c in range(4):
            vx, vz = tx + (c & 1), tz + (c >> 1)
            if i:
                r = RAMPS[i - 1]
                (rx, rz, rw, rh), d, low = r
                if d[0] != 0:
                    t = (vx - rx) / rw
                    if d[0] < 0:
                        t = 1 - t
                else:
                    t = (vz - rz) / rh
                    if d[1] < 0:
                        t = 1 - t
                out.append((low + min(max(t, 0), 1)) * CLIFF_H)
            else:
                out.append(base)
        return out

    def height_at(self, x, z):
        tx, tz = min(int(x // TILE), SIZE - 1), min(int(z // TILE), SIZE - 1)
        h = self.corner_heights(tx, tz)
        u, v = x / TILE - tx, z / TILE - tz
        return round((h[0] * (1 - u) + h[1] * u) * (1 - v) + (h[2] * (1 - u) + h[3] * u) * v, 2)

    def passable(self, tx, tz):
        return not (self.water[tz][tx] or self.boundary[tz][tx] or self.treed[tz][tx])

    def connected(self, a, b):
        (ax, az), (bx, bz) = a, b
        ha, hb = self.corner_heights(ax, az), self.corner_heights(bx, bz)
        if bx == ax + 1:
            return abs(ha[1] - hb[0]) < 0.05 and abs(ha[3] - hb[2]) < 0.05
        if bx == ax - 1:
            return self.connected(b, a)
        if bz == az + 1:
            return abs(ha[2] - hb[0]) < 0.05 and abs(ha[3] - hb[1]) < 0.05
        return self.connected(b, a)

    def path_len(self, a, b):
        """Octile tile-graph path length in metres (Dijkstra) from world point a to b, or None."""
        import heapq
        sa = (int(a[0] // TILE), int(a[1] // TILE))
        sb = (int(b[0] // TILE), int(b[1] // TILE))
        dist = {sa: 0.0}
        pq = [(0.0, sa)]
        while pq:
            d, (x, z) = heapq.heappop(pq)
            if (x, z) == sb:
                return d * TILE
            if d > dist.get((x, z), 1e18):
                continue
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0:
                        continue
                    nx, nz = x + dx, z + dz
                    if not (0 <= nx < SIZE and 0 <= nz < SIZE) or not self.passable(nx, nz):
                        continue
                    if dx and dz:
                        if not (self.passable(x + dx, z) and self.passable(x, z + dz)):
                            continue
                        if not (self.connected((x, z), (x + dx, z)) and self.connected((x + dx, z), (nx, nz))
                                and self.connected((x, z), (x, z + dz)) and self.connected((x, z + dz), (nx, nz))):
                            continue
                        step = math.sqrt(2)
                    else:
                        if not self.connected((x, z), (nx, nz)):
                            continue
                        step = 1.0
                    nd = d + step
                    if nd < dist.get((nx, nz), 1e18):
                        dist[(nx, nz)] = nd
                        heapq.heappush(pq, (nd, (nx, nz)))
        return None


def hash01(*v):
    h = 2166136261
    for x in v:
        h = ((h ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5bd1e995) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "maps", "slice.json"))
    ap.add_argument("--hall-footprint-m", type=float, default=8.0)
    args = ap.parse_args(argv)
    F = args.hall_footprint_m
    camps_def = json.load(open(os.path.join(ROOT, "data", "creep_camps.json")))["camps"]
    sc = json.load(open(os.path.join(ROOT, "docs", "design", "slice-content.json")))

    m = Map(F)
    m.load_sketch(os.path.join(ROOT, "data", "maps", "wether_downs_sketch.txt"))
    m.apply_ramps()

    # ---- landmarks (slice-plan §1.4; P1 side, P2 mirrored) -------------------------------------
    seam_m = 6.0
    p1_hall = (20.0 + 6.0 + F / 2.0, 166.0)                 # seam east edge x = 20
    p1_seam = (17.0, 166.0)
    p1_nat_hall = (80.0, 174.0 - 6.0 - F / 2.0)              # natural seam north edge z = 174
    p1_nat_seam = (80.0, 177.0)
    ring_seam = (153.0, 153.0)
    ring_hall_c = 156.0 + 6.0 / math.sqrt(2) + F / 2.0       # corner-to-corner gap 6.0 m
    ring_hall_c = math.ceil(ring_hall_c * 2.0) / 2.0          # snap to the 0.5 m cell grid, never closer
    ring_hall = (ring_hall_c, ring_hall_c)

    pads = []   # (x, z, size_m)
    for p in (p1_hall, p1_nat_hall):
        pads += [(p[0], p[1], F), (mirror(p)[0], mirror(p)[1], F)]
    pads.append((ring_hall[0], ring_hall[1], F))
    for p in (p1_seam, p1_nat_seam):
        pads += [(p[0], p[1], seam_m), (mirror(p)[0], mirror(p)[1], seam_m)]
    pads.append((ring_seam[0], ring_seam[1], seam_m))
    neutral = [("neutral_weighstall", (92.0, 92.0), 6.0, 135.0), ("neutral_hale_spring", (40.0, 40.0), 4.0, 135.0),
               ("neutral_coaching_inn", (128.0, 128.0), 6.0, 315.0)]
    for _, p, s, _f in neutral:
        pads.append((p[0], p[1], s))
    for x, z, s in pads:
        m.flatten_pad(x, z, s)

    # ---- camps (slice-plan §1.8; neutrals §3.3 templates) --------------------------------------
    camp_list = []
    for cid, cdef in camps_def.items():
        src = next(c for c in sc["neutrals"]["camps"] if c["id"] == cid)
        for k, pos in enumerate(src["positions_m"]):
            side = -1 if len(src["positions_m"]) == 1 else k
            creeps = []
            for unit_id, n in cdef["creeps"]:
                creeps += [unit_id] * n
            camp_list.append({"id": cid if side < 0 else "%s_p%d" % (cid, side + 1), "template": cid, "side": side,
                              "pos": [float(pos[0]), 0.0, float(pos[1])], "creeps": creeps})
            m.clear(pos[0], pos[1], 5.0)

    # ---- roads and textures --------------------------------------------------------------------
    paint_textures(m, [p1_hall, mirror(p1_hall)], [p1_nat_hall, mirror(p1_nat_hall), ring_hall],
                   [p1_seam, mirror(p1_seam), p1_nat_seam, mirror(p1_nat_seam), ring_seam],
                   [(c["pos"][0], c["pos"][2]) for c in camp_list], [p for _, p, _, _ in neutral])
    m.symmetrize()
    bad = m.asymmetric()
    assert bad == 0, "map is not symmetric (%d cells)" % bad

    # ---- trees: a diagonal pair per treed tile (checkerboard on the 1 m tree grid) -------------
    trees = []
    for tz in range(SIZE):
        for tx in range(SIZE):
            if not m.treed[tz][tx] or m.water[tz][tx] or m.ramp[tz][tx]:
                continue
            for gx, gz in ((2 * tx, 2 * tz), (2 * tx + 1, 2 * tz + 1)):
                # tree type from the mirrored-invariant pair (min, max) so P1 and P2 forests look alike
                a, b = min(gx, gz), max(gx, gz)
                trees.append([gx, gz, 0 if hash01(a, b, 7) < 0.18 else 1])
    trees.sort(key=lambda t: (t[1], t[0]))

    def y(p):
        return m.height_at(p[0], p[1])

    def v3(p):
        return [round(p[0], 2), y(p), round(p[1], 2)]

    starts = [v3(p1_hall), v3(mirror(p1_hall))]
    mines = [v3(p1_seam), v3(mirror(p1_seam)), v3(p1_nat_seam), v3(mirror(p1_nat_seam)), v3(ring_seam)]
    for c in camp_list:
        c["pos"] = v3((c["pos"][0], c["pos"][2]))
        tmpl = camps_def[c["template"]]
        c["facing"] = 0.0
        if "layout" in tmpl:
            c["layout"] = tmpl["layout"]
    nb = [{"def": d, "pos": v3(p), "facing": f} for d, p, _, f in neutral]
    critters = []
    for p in ((20.0, 96.0), (30.0, 112.0), (48.0, 128.0)):
        critters += [{"def": "critter_brown_hare", "pos": v3(p)}, {"def": "critter_brown_hare", "pos": v3(mirror(p))}]
    for p in ((34.0, 100.0), (47.0, 100.0)):
        critters += [{"def": "critter_grey_goose", "pos": v3(p)}, {"def": "critter_grey_goose", "pos": v3(mirror(p))}]

    route = sc["map"]["creep_route"]
    meta = {
        "id": "wether_downs", "display_name": "map_wether_downs", "tileset": "gv", "symmetry": "mirror_xz",
        "hall_footprint_m": F, "players": 2,
        "neutral_flags": {"beacon_cairns": False},
        "gold_amounts": [GOLD_MAIN, GOLD_MAIN, GOLD_EXPANSION, GOLD_EXPANSION, GOLD_EXPANSION],
        "starts": [{"slot": 0, "hall": starts[0], "mine": 0, "natural": 0, "camera": starts[0]},
                   {"slot": 1, "hall": starts[1], "mine": 1, "natural": 1, "camera": starts[1]}],
        "expansions": [{"hall": v3(p1_nat_hall), "mine": 2, "side": 0, "guard_camp": "camp_gv_drystone_fold_p1"},
                       {"hall": v3(mirror(p1_nat_hall)), "mine": 3, "side": 1,
                        "guard_camp": "camp_gv_drystone_fold_p2"},
                       {"hall": v3(ring_hall), "mine": 4, "side": -1, "guard_camp": "camp_gv_standing_ring"}],
        "creep_route": {"hero_1": route["hero_1"], "hero_2": route["hero_2"], "after_push": route["after_push"],
                        "fallback": {"hero_1": ["shop", "natural"], "hero_2": ["camp_gv_charcoal_yard", "shop"]},
                        "note": "Own-side template ids resolve to the player's own copy (<id>_p1 / <id>_p2)."},
        "lanes": {"shortest": [v3(p1_hall), v3((58.0, 154.0)), v3((96.0, 121.0)), v3((96.0, 104.0)),
                               v3((104.0, 96.0)), v3((121.0, 96.0)), v3((154.0, 58.0)), v3(mirror(p1_hall))]},
        "landmarks": sc["map"]["landmarks_m"],
        "critters": critters,
        "ramp_names": ["p1_main", "p2_main", "basin_w", "basin_n", "basin_s", "basin_e", "dell_s", "dell_e",
                       "k1_s", "k1_e", "k2_w", "k2_n"],
    }

    def rows(layer):
        return ["".join(str(layer[z][x]) for x in range(SIZE)) for z in range(SIZE)]

    out = {
        "version": 1, "name": "wether_downs", "width": SIZE, "height": SIZE, "water_level": -0.45,
        "tex": rows(m.tex), "cliff": rows(m.level), "water": rows(m.water), "boundary": rows(m.boundary),
        "ramps": m.ramps, "start_locations": starts, "gold_mines": mines, "creep_camps": camp_list,
        "neutral_buildings": nb, "trees": trees, "meta": meta,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(dump(out))

    # ---- report ---------------------------------------------------------------------------------
    print("wrote %s: %d trees, %d camps, %d mines, %d ramps" % (os.path.relpath(args.out, ROOT), len(trees),
                                                               len(camp_list), len(mines), len(m.ramps)))
    for name, a, b in (("main -> main", p1_hall, mirror(p1_hall)), ("main -> natural", p1_hall, p1_nat_hall),
                       ("main -> weighstall", p1_hall, (92.0, 99.0)), ("main -> inn", p1_hall, (128.0, 136.0)),
                       ("main -> ring hall", p1_hall, ring_hall), ("main -> spring", p1_hall, (40.0, 48.0))):
        d = m.path_len(a, b)
        print("  path %-20s %s" % (name, "UNREACHABLE" if d is None else "%.1f m" % d))
    gap = 26.0 - 20.0 if F == 8.0 else None
    print("  hall-seam gap (main): %.2f m; ring: %.2f m" % (
        (p1_hall[0] - F / 2.0) - (p1_seam[0] + seam_m / 2.0),
        math.hypot(*(((ring_hall[0] - F / 2.0) - (ring_seam[0] + seam_m / 2.0)),) * 2)))
    return 0


def paint_textures(m, halls, sites, seams, camps, neutrals):
    def disc(cx, cz, r, t, only_if=None):
        for tx, tz in m.tiles_in_rect_m(cx - r, cz - r, cx + r, cz + r):
            if math.hypot((tx + 0.5) * TILE - cx, (tz + 0.5) * TILE - cz) <= r:
                if only_if is None or m.tex[tz][tx] in only_if:
                    m.tex[tz][tx] = t

    def road(a, b, w=2.5):
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 1.0) + 1
        for i in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            jitter = (hash01(int(p[0]), int(p[1]), 3) - 0.5) * 1.2
            disc(p[0], p[1], w + jitter, T_ROAD)

    for z in range(SIZE):
        for x in range(SIZE):
            if z < x:
                continue   # P1 half only; symmetrize() mirrors it
            lv = m.level[z][x]
            n = hash01(x // 3, z // 3, 11)
            t = T_GRASS
            if lv == 0:
                t = T_GRASSY_DIRT if n < 0.3 else T_GRASS
            elif lv == 1 and (x < 26 or z < 26) and n < 0.55:
                t = T_MEADOW            # the west and north fields
            if m.treed[z][x]:
                t = T_THICK
            elif m.ramp[z][x]:
                t = T_DIRT
            m.tex[z][x] = t
    for z in range(SIZE):
        for x in range(SIZE):
            if z < x or m.treed[z][x]:
                continue
            higher = any(0 <= x + dx < SIZE and 0 <= z + dz < SIZE and m.level[z + dz][x + dx] > m.level[z][x]
                         and not m.ramp[z + dz][x + dx] and not m.ramp[z][x]
                         for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            shore = any(0 <= x + dx < SIZE and 0 <= z + dz < SIZE and m.water[z + dz][x + dx]
                        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)))
            if m.water[z][x]:
                m.tex[z][x] = T_GRASSY_DIRT
            elif shore:
                m.tex[z][x] = T_GRASSY_DIRT
            elif higher:
                m.tex[z][x] = T_ROCK
    # roads (P1 side; mirrored): ramp foot -> natural, ramp foot -> basin S ramp, spur to the inn
    road((58.0, 155.0), (80.0, 158.0))
    road((58.0, 154.0), (96.0, 121.0))
    road((96.0, 121.0), (96.0, 117.0))
    road((112.0, 112.0), (124.0, 124.0))
    for h in halls:
        disc(h[0], h[1], 7.0, T_DIRT)
    for s in sites:
        disc(s[0], s[1], 6.0, T_DIRT)
    for s in seams:
        disc(s[0], s[1], 5.0, T_CRACKED)
    for c in camps:
        disc(c[0], c[1], 4.5, T_CRACKED, only_if=(T_GRASS, T_MEADOW, T_GRASSY_DIRT, T_THICK))
    for p in neutrals:
        disc(p[0], p[1], 6.0, T_ROCK, only_if=(T_GRASS, T_MEADOW, T_GRASSY_DIRT, T_DIRT, T_ROAD))
    # the ring floor (red camp pocket)
    disc(158.0, 158.0, 6.0, T_ROCK, only_if=(T_GRASS, T_MEADOW, T_GRASSY_DIRT))


def dump(out):
    """JSON with one row string per line (the layers stay readable and diff well)."""
    parts = ["{"]
    keys = list(out.keys())
    for i, k in enumerate(keys):
        v = out[k]
        sep = "," if i < len(keys) - 1 else ""
        if k in ("tex", "cliff", "water", "boundary"):
            parts.append('  "%s": [\n%s\n  ]%s' % (k, ",\n".join('    "%s"' % r for r in v), sep))
        elif k == "trees":
            chunks = [", ".join(json.dumps(t) for t in v[j:j + 12]) for j in range(0, len(v), 12)]
            parts.append('  "trees": [\n%s\n  ]%s' % (",\n".join("    " + c for c in chunks), sep))
        elif k in ("creep_camps", "neutral_buildings", "ramps"):
            parts.append('  "%s": [\n%s\n  ]%s' % (k, ",\n".join("    " + json.dumps(e) for e in v), sep))
        else:
            parts.append('  "%s": %s%s' % (k, json.dumps(v), sep))
    parts.append("}")
    text = "\n".join(parts) + "\n"
    json.loads(text)
    return text


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
