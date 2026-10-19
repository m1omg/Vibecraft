# Vertical slice plan: map, assets, 3D bake-off, milestones

*Design date: 2026-10-16. Status: proposal for review. Scope: the vertical slice only. That is `kingdom` vs `clans`, 1v1 against
the AI, on one Greenvale map. The full game (4 factions) comes later.*

*Revision 2 (2026-10-16, resumed after an interruption): Higgsfield reserve set to 20 cr (208.5 spendable); texture count corrected
(57 images, 14.25 cr); margin ladder for rig fallbacks (§2.15); Krea 3D ban widened to every model except TRELLIS v1; ambience beds
planned as stitched jobs; bake-off round 1 record completed and round 2 sequenced; loop-critical procedural clips moved to P0.*

*Revision 3 (2026-10-17): IP-safety and fidelity review fixes (Review log at the end). The map is re-sited for the neutrals revision of
17 Oct (16 camps, the Coaching Inn at P0); main ramps are 8 m; the slice roster matches kingdom and clans §11; the Wheel Marshal attacks
one-handed with her shield forward; HUD and audio similarity checks join the gate; the budget is re-based on ledger #24.*

*Revision 4 (2026-10-19): second IP-safety and fidelity review (Review log, round 2, at the end). Slice lobby colours are kingdom
Emerald vs clans Royal Blue; the worker completion id stays `built` against the art bible; M1 gains an IP number gate (≥ 20 % from
every classic value), `controls_parity` and flying units; the creep flow is planned for contested shared camps; a third Gold Seam sits
in the Standing Ring; P1 adds a second caster and a third hero per side; P0 annoyed runs grow to 5 lines (Krea P1 cap 294 CU).*

**Read with:** `docs/research/ip-safety.md` (§0, §2, §3.2), `docs/research/gameplay-mechanics.md` (§11, §13),
`docs/research/README.md`, `docs/research/visual-art-direction.md` (§1.4, §3, §7), `docs/research/audio-direction.md` (§3–§4),
`docs/research/ai-asset-pipeline.md` (§2, §3), `docs/design/rules.md`, `docs/design/neutrals.md`, the faction docs
`docs/design/factions/kingdom.md` and `clans.md`, the four juice docs and `docs/asset-ledger.md`.

**Supersedes:**
- The slice map geometry in `gameplay-mechanics.md` §13.6.
- The point-symmetric generator map (`MapGenerator.test_map`) *as the slice map*. It stays as a test fixture.
- Neutrals §3.6 *positions and distances*, where they differ (listed in §1.14). Neutrals keeps ownership of camp templates, items and creep stats.

**Naming convention in this doc.** Faction units and buildings are named by **role**: `kingdom.worker`, `clans.hero1` and so on.
The synthesis step substitutes display names. Appendix A maps each role to the working name in today's faction docs.
Neutral names (creep families, Weighstall, Hale Spring) come from `neutrals.md`. "Greenvale" is the docs' name for the tileset, whose
internal id is `gv`; players see it as **Downland** (§1.12).

**Hero 1 / hero 2.** In §1 and §4, "hero 1" and "hero 2" mean the **first and second hero trained**. In §2 and Appendix A the role ids
(`kingdom.hero1`, `clans.hero2` …) are fixed kits. Both slice heroes are offered at the altar from T1 and the free token covers either,
so either kit can be hero 1 (clans §10: the Uncut first 60 %, the Skymirror 40 %). The route timings in §1.11 are written for a melee
hero 1; §1.13 `creep_route` runs both first-hero choices per faction.

**Priorities**
- **P0** — the slice is not done without it.
- **P1** — planned, and funded if the probes land at or under estimate. Otherwise it is cut in the order given.
- **P2** — stretch goal (`[SLICE+]` in other docs), funded from next month's Higgsfield grant or from savings.

---

## 0. At a glance

| | |
|---|---|
| **Map** | **Wether Downs**. Greenvale tileset (shown to players as Downland), 96 × 96 tiles of 2 m (192 m square), 2 players. Mirror-symmetric across the NW–SE diagonal: P1 starts SW, P2 starts NE. Four test lanes (shortest through the basin, centre via the shop, NW spring flank, SE ring flank). **16 creep camps** (8 green, 7 amber, 1 red; 11 sleep at night); three of the shared camps are contested by both players' heroes (§1.11). **5 Gold Seams**: main and natural per player, plus a contested third inside the Standing Ring. Central Weighstall; NW Hale Spring and Cairn Gate; SE Standing Ring and Coaching Inn |
| **Rush distance** | Main hall to main hall is **206 m** of path: about 49 s for infantry at 4.2 m/s and 69 s for workers. Main to natural is 57.5 m of path |
| **3D policy** | Characters and both signature halls: **Higgsfield Tripo H3.1** (9 cr). Done for 12 characters and both halls (ledger #10, #20, #24); the Sootcoat creep (B12) is the last mesh. Everything else is **procedural bpy with AI-painted textures** |
| **Rigging** | All 12 characters are rigged with the **free CPU auto-rigger** (`tools/autorig.py`, commit 2bb913d) on the library skeleton (the `kingdom.infantry` Higgsfield rig). Higgsfield is used only to buy library clips on that rig (8 cr each; 7 owned, 2 more at P0). Secondary motions are procedural keyframes |
| **Budgets (derived from ledger #24, 2026-10-17)** | Higgsfield **≈ 77.5 cr** (reserve 20 → **57.5 spendable**). Krea **≈ 1,500 CU** (reserve 150 → **1,350 spendable**). Revision 2's live readings were 228.5 cr and 1,529.6 CU; ledger #15–#24 spent 151 cr and 29.6 CU since. Ledger #25 records the next live reading |
| **P0 spend plan** | Higgsfield **45.0 cr** still to spend (B12, 2 clips, textures, icons), leaving a **12.5 cr margin** that a fixed fallback ladder spends (§2.15). Krea **1,056 CU** (style anchors, UI frames, P0 audio), leaving a **294 CU P1 cap**. P1 audio is funded only if the M1 audio probes land at estimate. The second caster and third hero per side (P1) come from the next Higgsfield grant (§2.3) |
| **Banned generators** | Every Krea 3D model except TRELLIS v1 (measured 148–222 CU each). Higgsfield Meshy textured (30 cr quoted) and the Higgsfield "mesh + rig + clip" bundle (38 cr quoted; the same result costs 9 + 8 = 17 cr piecewise) |
| **Hard dates** | Higgsfield subscription credits appear to **reset monthly**. The 16 Oct grant of 270 cr deducted the 4 cr left over, so **spend the P0 3D before ~15 Nov**. ElevenLabs default voices **expire 31 Dec 2026**, so **all VO must be generated by 15 Dec** |
| **Milestones** | M1 playable loop (graybox) → M2 art pass → M3 audio pass → M4 AI opponent → M5 polish and release gate (§4) |

---

## 1. Map brief: Wether Downs (Greenvale)

### 1.1 Design goals

The map is designed from written principles (ip-safety §2.6). It is not traced from, and does not resemble, any existing melee map.
The sketch in §1.3 is the evidence of independent creation. Copy it to `data/maps/wether_downs_sketch.txt` in M1, where the
look-alike review (M1 acceptance `map_lookalike`, §4.1) checks it before the AI and seat tests are built on it.

1. **The classic hero-RTS rhythm in 12–20 minutes.**
   - 0–2 min: build up; the first hero is out at about 2:00.
   - 2–6 min: creep with the first hero; the first dusk falls at 3:20.
   - 5–8 min: T2, the second hero, and an expansion or a push. From about 6:20 both players' heroes meet at the shared camps, so
     creep-jacking (fighting the enemy hero at a camp) is part of the plan (§1.11).
   - 10+ min: a decisive fight. A T3 tier (P1, §2.6 E17: a third hero and top-tier upgrades) and the contested third Gold Seam give
     long games something to tech and expand into.
2. **A safe main with exactly one ramp.**
   - The ramp is 8 m wide, like every other ramp on the map, so a few supply buildings cannot seal the main.
   - The main sits on high ground (level 2), so lowland units cannot see into it.
3. **A natural expansion just below the ramp.**
   - It is guarded by a **never-sleeping, guard-mode** amber camp, so expanding always costs a fight.
   - It has two extra approaches: a 12 m road gap to the north and a 10 m tree-wall gap to the SE.
4. **Four green camps per player, on the own side and off the lanes** (neutrals §3.3, §3.6).
   - The Charcoal Clamp is beside the natural path; the Turnip Patch is on the other side of the main.
   - Woodward's Rest sits in the natural's north-east corner, on the way to the Fold.
   - The Collier's Hut sits by the west-field copse. It is the second hero's first camp.
   - An amber **Charcoal Yard** on each player's ring flank gives the second hero XP near home.
5. **A contested centre.** The Weighstall (merchant) sits on the north-west side of a level-0 basin. Units inside the basin cannot
   see up its rim. The shortest main-to-main route crosses the basin's south-east half through the S and E ramps. It passes 12 m clear
   of the Den's guards and about 6 m outside the stall's use range, so armies pass the shop without waking it, but blind to the rim.
   Shopping is a short, deliberate step aside.
6. **Flanks with a purpose.**
   - NW flank: the **Hale Spring**, guarded by night-active scarecrows (free by day, contested by night), and the shared amber
     **Cairn Gate**, which never sleeps.
   - SE flank: the **Standing Ring**, the red camp, whose creeps never sleep and whose pocket lies between the two naturals. It
     stands in **guard mode** over the map's **third Gold Seam** (8,000), a contested late expansion. The
     **Coaching Inn** (instant revive and, at P1, the Rat-Piper's hire; never guarded) stands on the axis between the SE knoll and the
     ring pocket. Each player's Charcoal Yard, with the Dewstone site `[SLICE+]`, lies on this side.
7. **Vision terrain.**
   - Two level-2 knolls sit on the axis. They are the Beacon Cairn sites `[SLICE+]`, which are off by default
     (`neutral.beacon_cairns`, neutrals §5.11), and they give vision fights even without them.
   - Tree walls and copses break sight lines.
8. **Fairness.** The map is mirror-symmetric across the NW–SE diagonal, so the axis can hold the unique landmarks. The test is in §1.13.
9. **Night means sleeping creeps.** Eleven of the 16 camps sleep at night, four never sleep and one (the Crow Field) sleeps by day
   (neutrals §1.5 map rules: at most one day camp, at least 60 % night sleepers).

### 1.2 Conventions

| Item | Value |
|---|---|
| Grid | 96 × 96 tiles, `TILE` 2 m. Coordinates are in metres: x = east, z = south (screen down). Tile = floor(m / 2). Origin at the NW corner (architecture §2) |
| Playable area | The outer 2 tiles are unpathable edge. Tiles 2–4 are border forest. The playable interior is about 172 m square |
| Cliff levels | 0 (basin, spring dell), 1 (fields, naturals, flanks), 2 (mains, knolls). `CLIFF_H` 1.75 m today; the research recommends 2.0 m (README §8). The map works with either |
| Ramps | 2 tiles long, one level per ramp (architecture §7). **Every ramp is 4 tiles wide (8 m)**, the main ramps included |
| Symmetry | Mirror across the NW–SE diagonal: (x, z) → (z, x). P1 (SW) maps to P2 (NE). The NW corner, the centre and the SE corner lie on the axis and map to themselves |
| Hall pads | 8 × 8 m reserved per hall. This covers both the 5 m (10-cell) architecture footprint and the 8 m footprint in the art and clans docs (kingdom §13 Q1). The map script takes a parameter **`hall_footprint_m` = F** and **derives every hall centre from it**, so the seam gap is exactly **6.0 m edge to edge** for either footprint: hall centre = seam edge + 6.0 + F/2 along the seam-to-hall axis. P1 main: x = 20 (seam east edge) + 6.0 + F/2 = **30.0 for F = 8 m, 28.5 for F = 5 m** (P2 mirrored in z). Natural: z = 174 − 6.0 − F/2 = 164.0 / 165.5. The pad stays reserved at 8 × 8 m; a 5 m hall sits at its seam-side end, never at the pad centre. Worker trips, and so M1 #2, depend on this gap (≈ 8.6 gold/s at a 7.5 m gap) |
| Distances | "Straight" is centre to centre. "Path" is octile A* on the 2 m tile grid, respecting cliffs and ramps. The in-engine string-pulled path is about 3–6 % shorter |
| Lanes | The four main-to-main routes used by the tests: **shortest**, **centre** (via the Weighstall), **NW** (via the Hale Spring) and **SE** (via the Standing Ring), each also tested in its mirrored copy (§1.10) |

**Why mirror and not 180° rotation.** The generator's test map uses point symmetry. Point symmetry cannot place a single landmark anywhere
except the exact centre. The mirror lets the spring (NW), the Cairn Gate, the inn and the ring (SE) be one-of-a-kind, and all of them lie
at equal distance from both players.

The cost is chirality under a fixed-yaw camera:
- P1's ramp faces east, so it is seen side-on.
- P2's ramp faces south, toward the camera.

The seat-fairness tests (§1.13, M4) check that this does not matter. If it does, swap the ramp facing for both players, not the layout.

### 1.3 ASCII sketch (1 character = 2 × 2 tiles = 4 m; the column and row headers are character indices)

```
    000000000011111111112222222222333333333344444444
    012345678901234567890123456789012345678901234567
  0                                                 
  1  ############################################## 
  2  ############################################## 
  3  ##..............................::::::::::::## 
  4  ##..............................::::::::$:::## 
  5  ##..............................::::::::::::## 
  6  ##..............................::::::::::::## 
  7  ##.....,,,,.....................::::::::2:::## 
  8  ##....,,,,,,..................g.::::::::::::## 
  9  ##....,,,,,,//.........~~.......::::::::::::## 
 10  ##....,,,+,,//.........~~.......::::::::::::## 
 11  ##....,,,,,,....................::::::::::::## 
 12  ##.....,,,,.....................::::::::::::## 
 13  ##......//......................::::///:::::## 
 14  ##......//..........................///.....## 
 15  ##........................##...............g## 
 16  ##.............q..........##.....#..........## 
 17  ##...............::.......##.....#..........## 
 18  ##..............::://.//..h......#..........## 
 19  ##..............::k//.,,....................## 
 20  ##...............//.,,,,,,..............n..$## 
 21  ##...............//,,,,,,,,.................## 
 22  ##.................,,,,,,,,......#........a.## 
 23  ##.............../,,,,S,,,,,/....#w.........## 
 24  ##......~~......./,,,,,,,,,,/....#..........## 
 25  ##......~~.........,,,,,,,,......###..######## 
 26  ##.................,,,,,,,,//....###..######## 
 27  ##............###h..,,,,,,.//...............## 
 28  ##............###.....,,.//:::..............## 
 29  ##....................//.//:k:............y.## 
 30  ##.........................::......##.......## 
 31  ##.....g...........................##......d## 
 32  ##.............................i...##.......## 
 33  ##:::::::::::...............................## 
 34  ##:::::::::::..###...#####..................## 
 35  ##:::::::::::.........w.##.........##...##..## 
 36  ##:::::::::::...........##...###..###...###.## 
 37  ##:::::::::://...............###..##.....##.## 
 38  ##:::::::::://............................#### 
 39  ##:::::::::://..........##............r...#### 
 40  ##:::::::::::...........##................#### 
 41  ##:$::1::::::......n....##........##.....##### 
 42  ##:::::::::::...........##........###...###### 
 43  ##:::::::::::........a..##..y......########### 
 44  ##:::::::::::.g....$....##....d......######### 
 45  ############################################## 
 46  ############################################## 
 47                                                 
```

Legend:

| Symbol | Meaning |
|---|---|
| `:` | Level 2 (mains, knolls) |
| `.` | Level 1 |
| `,` | Level 0 (centre basin, spring dell) |
| `/` | Ramp |
| `#` | Trees (lumber) |
| `~` | Pond, deep water (impassable) |
| blank | Unpathable edge |
| `1` / `2` | P1 / P2 main hall (start location) |
| `$` | Gold Seam (12,000 at the mains, 8,000 at the naturals). The fifth, contested seam (8,000) inside the Standing Ring is added by the layout script (§1.4 RS) and is not drawn in this sketch |
| `n` | Natural hall site |
| `g` | Green camp: Charcoal Clamp south of the ramp; Turnip Patch north of the P1 main (west of the P2 main) |
| `w` | Woodward's Rest (green 9) in the natural's north-east corner |
| `h` | Collier's Hut (green 8) by the west-field copse |
| `y` | Charcoal Yard (amber 14) on the ring flank |
| `d` | Dewstone site `[SLICE+]`, beside each Charcoal Yard |
| `a` | Drystone Fold (amber 14, guard mode) at each natural |
| `S` | Weighstall with the Smugglers' Den (amber 11) |
| `+` | Hale Spring with the Crow Field (amber 12, the one day camp) |
| `q` | Cairn Gate (amber 16, never sleeps), shared, on the axis |
| `r` | Standing Ring (red 20) |
| `k` | Knoll: Beacon Cairn site `[SLICE+]`, off by default |
| `i` | Coaching Inn, *The Muddy Lantern* (instant revive only, P0) |

The sketch is generated from a tile-level layout script (kept with the sketch in M1). Re-checked on 2026-10-17: 0 asymmetric tiles and
0 asymmetric characters across the diagonal (with `1` ↔ `2`), and every landmark letter lies within one character (4 m) of its §1.4
coordinate.

### 1.4 Landmarks and coordinates

P2 coordinates are P1's with x and z swapped. Axis features appear once.

| Id | Landmark | P1 centre (m) | P2 centre (m) | Size / notes |
|---|---|---|---|---|
| H | Main hall (start location) | (30, 166) for F = 8 m; (28.5, 166) for F = 5 m | mirrored: (166, 30) / (166, 28.5) | 8 × 8 m pad reserved, level 2; centre derived from `hall_footprint_m` (§1.2). Camera starts here. 5 idle workers on a 1 m spacing between hall and seam |
| M | Main Gold Seam, 12,000 | (18, 166) | (166, 18) | 4 × 4 m. **Gap 6.0 m** from the hall's real footprint, edge to edge (rules §3.3), for either F |
| R | Main ramp | (56, 154) | (154, 56) | 8 m wide; from level 1 up to 2. P1 ascends west; P2 ascends north |
| N | Natural hall site | (80, 164) for F = 8 m; (80, 165.5) for F = 5 m | mirrored | 8 × 8 m pad, level 1; centre derived from F (§1.2) |
| n | Natural Gold Seam, 8,000 | (80, 176) | (176, 80) | 6.0 m gap to the natural hall's real footprint |
| D | Drystone Fold, amber 14, guard | (88, 172) | (172, 88) | 11.3 m from the natural pad centre, inside the 12 m guard radius. Never sleeps |
| G | Charcoal Clamp, green 5 | (60, 176) | (176, 60) | Below the main cliff, about 19 m off the ramp-to-natural road. Sleeps at night |
| T | Turnip Patch, green 8 | (32, 124) | (124, 32) | North of the P1 main's cliff, 13 m off the NW lane. Sleeps at night (`sleeps_override`, neutrals §3.3) |
| W | Woodward's Rest, green 9 | (95, 143) | (143, 95) | The natural's north-east corner, under the east hedge belt and 7 m clear of the north road gap. 14 m off the SE lane; 32.5 m of path to the Fold. Sleeps at night |
| CH | Collier's Hut, green 8 | (73, 111) | (111, 73) | Beside copse C1 (the colliers' wood), 14 m off the shortest lane. Sleeps at night |
| Y | Charcoal Yard, amber 14 | (117, 175) | (175, 117) | The SE lowland behind the TW1 tree wall, 16 m south of the SE lane, 29 m from the Fold. Sleeps at night |
| DW | Dewstone site `[SLICE+]` | (124, 178) | (178, 124) | 7.6 m east of the Yard, which guards it (neutrals §5.8) |
| P | Pond, deep, r 5 m | (40, 100) | (100, 40) | Geese; fireflies at night |
| C1 | Copse, r 4 m | (66, 112) | (112, 66) | Blocks sight between the centre lane and the NW lane; the Collier's Hut stands at its east edge |
| C2 | Copse, r 4 m | (126, 148) | (148, 126) | Breaks the SE lowland |
| S | Weighstall + Smugglers' Den (amber 11) | (92, 92) | axis | 4 × 4 m stall on the basin's north-west side, 5.7 m from the basin centre. One Den creep 3.5 m out from each stall corner, facing out, `acquire_override` 6.5 m (neutrals §3.3) |
| B | Centre basin | (96, 96) | axis | Level 0, radius 20 m, four 8 m ramps (W, N, S, E). The S and E ramps carry the shortest route |
| K1 | NW knoll | (76, 76) | axis | Level 2, radius 6 m. Ramps face S (toward P1) and E (toward P2) |
| K2 | SE knoll | (116, 116) | axis | Level 2, radius 6 m. Ramps face W (toward P1) and N (toward P2) |
| Q | Cairn Gate, amber 16 | (66, 66) | axis | Between K1 and the spring dell. Never sleeps. 23 m off the NW lane; 34 m from the Crow Field's nearest creep |
| I | Coaching Inn, *The Muddy Lantern* | (128, 128) | axis | 5 × 5 m, door facing SE (away from the stall). 6.5 m from the K2 cliff base, 51 m from the stall, 29 m off the nearest lane. **Never guarded:** the nearest camp member stands 30.7 m from its footprint |
| SP | Hale Spring + Crow Field (amber 12) | (40, 40) | axis | A level-0 dell of radius 14 m. Ramps face S (P1) and E (P2) |
| RG | Standing Ring (red 20, **guard mode**, 12 m) | (158, 158) | axis | Level-1 pocket of radius 14 m inside a tree ring 14–19 m out. 12 m gaps face W and N. The camp stands between the gaps and the seam, so the third expansion always costs the red fight |
| RS | Ring Gold Seam, 8,000 (contested third) | (154, 154) | axis | 4 × 4 m on the axis. Its hall site sits on the axis to the SE, centre at 156 + 6.0/√2 + F/2 = **(164.2, 164.2) for F = 8 m, (162.7, 162.7) for F = 5 m**, so the corner-to-corner gap is 6.0 m. The hall centre is 8.8 m from the camp centre, inside the 12 m guard radius. The ring's SE tree arc is pushed out from 14–19 m to **17–22 m** so the pad fits (the border forest starts at 182 m) |

### 1.5 Cliff levels and ramps (`MapData.add_ramp(rect_tiles, dir_ascending, low)`)

| Ramp | Rect (tiles: x, z, w, h) | Ascends | Low → high | Width |
|---|---|---|---|---|
| P1 main | (27, 75, 2, 4) | West (−1, 0) | 1 → 2 | 8 m |
| P2 main | (75, 27, 4, 2) | North (0, −1) | 1 → 2 | 8 m |
| Basin W (P1 side) | (36, 46, 2, 4) | West | 0 → 1 | 8 m |
| Basin N (P2 side) | (46, 36, 4, 2) | North | 0 → 1 | 8 m |
| Basin S (P1 side) | (46, 58, 4, 2) | South | 0 → 1 | 8 m |
| Basin E (P2 side) | (58, 46, 2, 4) | East | 0 → 1 | 8 m |
| Spring dell S (P1) | (18, 27, 4, 2) | South | 0 → 1 | 8 m |
| Spring dell E (P2) | (27, 18, 2, 4) | East | 0 → 1 | 8 m |
| K1 knoll S face (P1) | (36, 41, 4, 2) | North (into the knoll) | 1 → 2 | 8 m |
| K1 knoll E face (P2) | (41, 36, 2, 4) | West | 1 → 2 | 8 m |
| K2 knoll W face (P1) | (53, 56, 2, 4) | East | 1 → 2 | 8 m |
| K2 knoll N face (P2) | (56, 53, 4, 2) | South | 1 → 2 | 8 m |

**Levels**
- **Level 2:** each main plateau. P1's is x 8–54, z 134–184 m, about 1,030 walkable tiles together with the knolls.
- **Level 0:** the centre basin and the spring dell, 520 tiles.
- **Level 1:** everything else, about 5,300 tiles.

**Cliff dressing:** rock clusters at every cliff base, and shrubs and single trees along cliff tops. The main's north and east cliff
tops get a broken tree line, so defenders on high ground are partly hidden.

### 1.6 Chokepoints

| Choke | Width | Why it matters |
|---|---|---|
| Main ramp (×2) | **8 m** | The only way into a main; tower placement and each faction's worker-defence mechanic (the `kingdom` Levy Horn, the `clans` gong and felt garrison) play here. At 8 m, sealing it takes more buildings than an opening can spare. **Levy ranges are measured edge to edge from the hall footprint** (Take Up the Flail 22 m, Levy leash 30 m; kingdom §4 follow-up, §7): the centre of the ramp top is 21.5 m and the centre of the ramp foot 25.3 m from the 8 m hall's edge (28.6 m from a 5 m hall's), so Levies hold the whole ramp and disarm only when they chase past its foot into the field |
| Natural north road gap (×2) | 12 m, between hedge belts at z 136–140 | The direct route from the centre to the natural. Woodward's Rest stands 7 m east of it, so the gap itself is never guarded |
| Natural SE tree-wall gap (×2) | 10 m (TW1 gap, z 148–158) | The back door from the SE flank and the ring |
| Corridor between the main's NE cliff corner and the hedge belt (×2) | about 12 m | Where the shortest, centre and NW lanes leave home. The SE lane leaves along the natural road and through the SE gap |
| Basin ramps (×4) | 8 m | The S and E ramps carry the shortest main-to-main route through the basin; the W and N ramps are the quiet way to the shop. Holding the rim gives vision into the basin |
| Spring dell ramps (×2) | 8 m | Night ambushes at the spring |
| Ring pocket gaps (×2) | 12 m | One per player; the red camp is pulled through them |
| Knoll ramps (×4) | 8 m | Vision control |

### 1.7 Tree walls and lumber

| Tree group | Where (P1 side; mirror for P2) | Purpose |
|---|---|---|
| Border forest | Tiles 2–4 all round, thicker in the SE corner behind the ring | Map edge is never a void (art §1.4). Harvestable |
| Main back forest | z 180–184 inside the main and the border rows behind it (z 184–188), plus a west band x 8–12 with the border columns behind it (x 4–8): **4 rows deep on both sides** | Main lumber. Its front rows are about 10 m from the hall's south edge, inside rules §3.3's 8–12 m. **Total harvestable inside each main: ≈ 196 trees (≈ 9,800 lumber); ≈ 184 trees (≈ 9,200 lumber) lie within 30 m of the hall's edge** (counted from the §1.3 sketch at one tree per 2 × 2 m tile; the layout script gives the exact figure). At 7–8 choppers (≈ 7 lumber/s) that is about 22 min of chopping before walks lengthen. `map_economy_rules` requires ≥ 7,000 lumber (≥ 140 trees) within 30 m of each main hall's edge |
| Natural back forest | z 182–186, x 58–100 | Natural lumber: about 130 trees within 30 m of the natural pad |
| TW1 tree wall | x 100–108, z 136–184, with a gap at z 148–158 | Encloses the natural on the east; creates the 10 m SE back door; screens the Charcoal Yard from the natural |
| Hedge belts | x 66–76 and x 88–100 at z 136–140 | Frame the natural's 12 m north road gap. Thin (2 rows); can be chopped through, which opens new paths (a deliberate classic hero-RTS lumber decision) |
| Copses C1, C2 | See §1.4 | Break sight lines; small lumber |
| Ring tree ring | r 14–19 m around (158, 158); the SE arc (facing the map corner) at 17–22 m to fit the third hall site (§1.4 RS) | Makes the red camp a pocket; units can only pull it through the gaps |

Trees are placed one per 2 × 2 m tile with ±0.4 m jitter, ±20 % scale and three Greenvale species variants (§2.7, F3).
Each tree holds 50 lumber (rules §4.2).

### 1.8 Creep camps

Camp templates, stats and drops are owned by `neutrals.md` §3.3 (revision of 2026-10-17); this section owns the positions. Global rules
(rules §15, neutrals §1.3):
- acquire range 3.9 m (5.0 m for casters, 6.0 m in guard mode, 6.5 m for the Den by `acquire_override`);
- leash 18.75 m;
- XP factor 80/70/60/50/0 % by hero level;
- bounty 4 × level + 2 + rand(0–4), taxed by upkeep.

| Camp (template id) | Colour, total level | Count | Positions (P1, P2) | Sleeps | Mode | Straight / path from the nearer main hall | Role on this map |
|---|---|---|---|---|---|---|---|
| Charcoal Clamp (`camp_gv_charcoal_clamp`) | Green 5 | 2 | (60, 176), (176, 60) | Night | Camp | 31.6 / **50.6 m** | Hero 1's first camp, from about 2:10. 23.7 m from the ramp foot |
| Turnip Patch (`camp_gv_turnip_patch`) | **Green 8** | 2 | (32, 124), (124, 32) | **Night** (override) | Camp | 42.0 / 73.9 m | Hero 1's second camp (3:10–4:20), asleep from the first dusk |
| Woodward's Rest (`camp_gv_woodwards_rest`) | Green 9 | 2 | (95, 143), (143, 95) | Night | Camp | 68.9 / 73.9 m | Hero 1's third camp (≈ 4:45), 32.5 m from the own Fold |
| Collier's Hut (`camp_gv_colliers_hut`) | Green 8 | 2 | (73, 111), (111, 73) | Night | Camp | 69.8 / 78.1 m | Hero 2's first camp (≈ 7:15 kingdom, ≈ 7:45 clans) |
| Drystone Fold (`camp_gv_drystone_fold`) | Amber 14 | 2 | (88, 172), (172, 88) | Never | **Guard** (12 m) | 58.3 / 68.8 m | Clearing it opens the natural. The hero 2 → 3 step at about 5:30 |
| Charcoal Yard (`camp_gv_charcoal_yard`) | Amber 14 | 2 | (117, 175), (175, 117) | Night | Camp | 87.5 / 103.5 m | Hero 2's second camp (≈ 8:00); guards the Dewstone site `[SLICE+]` |
| Smugglers' Den (`camp_gv_smugglers_den`) | Amber 11 | 1 | (92, 92) | Night | Camp, corner layout | 96.5 / 110.2 m from both | Guards the Weighstall. A purchase within 10 m wakes it. Hero 2's third camp (≈ 8:30), **contested**: both hero 2s route here and the kingdom's arrives about 30 s first |
| Crow Field (`camp_gv_crow_field`) | Amber 12 | 1 | (40, 40) | **Day** (the one day camp) | Camp | 126.4 / 146.4 m from both | Spring free by day, guarded by night. Hero 1 at level 3 (≈ 7:00, before dawn), **contested** |
| Cairn Gate (`camp_gv_cairn_gate`) | Amber 16 | 1 | (66, 66) | Never | Camp | 106.3 / 119.6 m from both | Shared amber prize for hero 1 at level 3 (≈ 6:20), **contested**: both hero 1s arrive at about the same time |
| Standing Ring (`camp_gv_standing_ring`) | **Red 20** | 1 | (158, 158) | Never | **Guard** (12 m) over the third Gold Seam | 128.2 / 133.0 m from both | The big prize (L2 + L4 drop) and the key to the third expansion. Hero 1 level ≥ 4, hero 2 level ≥ 3 and an army (§4.4) |

- **Totals:** 16 camps (8 green, 7 amber, 1 red), 175 creep levels, **3,815 raw XP**, about **984 gold** of bounty (neutrals §3.6).
  Each player's own half holds 1,245 raw XP; the four shared camps hold 1,325, of which the three non-red ones (Cairn Gate, Crow Field,
  Den) hold **845 for both players together, ≈ 422 per player as a fair share**. Hero 1 at level 4 plus hero 2 at level 3 needs
  **2,024 raw XP** (80 / 70 / 60 % factors); own half plus fair share gives ≈ 1,667. So in a contested game the push comes at hero 1
  level 3–4 and hero 2 level 2–3, and the gap is made up by killing enemy units (creep-jacks, harassment), as in the classic game (§1.11).
- **Sleep mix:** 11 camps sleep at night, 4 never sleep (both Folds, the Cairn Gate, the Ring) and 1 sleeps by day (the Crow Field):
  69 % night sleepers (test `map_sleep_mix`, §1.13).
- **Authored `creep_route`** per player (neutrals §9; the AI follows it, not raw distance): hero 1 Clamp → Turnip Patch →
  Woodward's Rest → own Fold → Cairn Gate → Crow Field; hero 2 Collier's Hut → Charcoal Yard → Smugglers' Den; both heroes and the army
  take the Standing Ring after the first push. The three shared legs (Cairn Gate, Crow Field, Den) are **contested**: each carries a
  fallback leg in the map file (hero 1: the faction shop, then hold at the natural or scout the enemy's Charcoal Yard approach; hero 2:
  back to the own Charcoal Yard if still alive, else the faction shop), used by the M4 contested-camp branch (§4.4).
- **Off-road check** (test `camp_off_road`, §1.13): every camp centre is at least 13 m from every lane centreline (the Turnip Patch,
  13.0 m from the NW lane, is the closest), except on the lane routed through that camp's own landmark (centre lane and Den, NW lane and
  Crow Field, SE lane and Ring). The Den's creeps stand 12.1 m from the shortest lane, which crosses the basin's SE half. The Ring's
  switch to guard mode raises its acquire range to 6.0 m; it sits inside its tree pocket, far from every lane but the SE one, and
  `camp_off_road` re-checks it with the guard threshold.

### 1.9 Neutral buildings and critters

| Neutral | Where | Priority |
|---|---|---|
| Gold Seam ×5 | §1.4 M, n (two per player) and RS (the contested third, inside the Standing Ring) | P0 |
| Weighstall + Smugglers' Den | (92, 92), basin NW side | P0 |
| Hale Spring + Crow Field | NW dell | P0 |
| Standing Ring props (standing stones; Cairnwake slab kit) | SE pocket | P0 |
| Coaching Inn, sign *The Muddy Lantern* (`neutral_coaching_inn`; instant revive, never guarded) | (128, 128) | **P0** for revive. Hiring the Rat-Piper (B19; 425 g / 135 l, 5 food, instant, the free first-hero token works here, rules §6.1) is **P1** with E17 |
| Cairn Gate gateposts and field-wall ruin (slab kit) | (66, 66) | P0 |
| Beacon Cairn ×2 (behind `neutral.beacon_cairns`, off on this map by default) | Knoll tops (76, 76) and (116, 116) | P2 |
| Dewstone ×2 (a dry quartz-veined boulder: no water, basin or blue glow; neutrals §5.8) | (124, 178), (178, 124), each guarded by its Charcoal Yard | P2, first in line |
| Hiring Fair | **Not placed in the slice.** If added later, it goes on the axis | P2 |
| Brown hares ×6 | Meadows of each west/south field, 3 per side, never within 15 m of a start | P1 |
| Grey geese ×4 | 2 per pond | P1 |
| Firefly drifts | Ponds and the spring dell, night only, VFX | P1 |

### 1.10 Lanes, distances and travel times

Path lengths are octile A* on the tile grid. Seconds are given at worker 3.0 m/s, infantry 4.2, hero 4.5 and fast unit 5.5.
The kingdom is a little slower: the Pavisier and the Hookgunner move at 4.1 m/s (main-to-main rush ≈ 50 s) and the Firewright at
4.4 m/s. `map_distances` tests path lengths only; the seconds are for planning.

| Route | Straight | Path | s @ 3.0 | s @ 4.2 | s @ 4.5 | s @ 5.5 |
|---|---|---|---|---|---|---|
| Main hall → own Gold Seam (F = 8 m; 10.5 m for F = 5 m) | 12.0 | 12.0 | 4.0 | 2.9 | 2.7 | 2.2 |
| Main hall → own ramp | 28.6 | 31.0 | 10.3 | 7.4 | 6.9 | 5.6 |
| Main hall → natural hall site | 50.0 | **57.5** | 19.2 | 13.7 | 12.8 | 10.4 |
| Main hall → Weighstall | 96.5 | 110.2 | 36.7 | 26.2 | 24.5 | 20.0 |
| Main hall → Coaching Inn | 105.1 | 113.7 | 37.9 | 27.1 | 25.3 | 20.7 |
| Main hall → Standing Ring | 128.2 | 133.0 | 44.3 | 31.7 | 29.5 | 24.2 |
| Main hall → Ring hall site (third expansion, through the own pocket gap; F = 8 m) | 134.2 | ≈ 142 (the layout script confirms) | ≈ 47 | ≈ 34 | ≈ 32 | ≈ 26 |
| Main hall → Hale Spring | 126.4 | 146.4 | 48.8 | 34.9 | 32.5 | 26.6 |
| Main hall → enemy natural | 159.2 | 172.0 | 57.3 | 41.0 | 38.2 | 31.3 |
| **Main hall → enemy main hall (shortest lane: crosses the basin's SE half via the S and E ramps)** | 192.3 | **206.4** | **68.8** | **49.1** | **45.9** | **37.5** |
| Main → main over the SE knoll, avoiding the basin (next shortest) | — | 208.7 | 69.6 | 49.7 | 46.4 | 37.9 |
| Main → main via the Weighstall (centre lane) | — | 220.5 | 73.5 | 52.5 | 49.0 | 40.1 |
| Main → main via the ring pocket (SE lane) | — | 265.9 | 88.6 | 63.3 | 59.1 | 48.3 |
| Main → main via the spring (NW lane) | — | 292.9 | 97.6 | 69.7 | 65.1 | 53.3 |
| Natural → enemy natural | 118.8 | 125.8 | 41.9 | 30.0 | 28.0 | 22.9 |

**Creep-route legs** (path):
- hero 1: ramp → Clamp 23.7 m; Clamp → Turnip Patch 71.8 m; Turnip Patch → Woodward's Rest 69.5 m; Woodward's Rest → own Fold
  32.5 m; own Fold → Cairn Gate 115.1 m; Cairn Gate → Crow Field 43.8 m;
- hero 2: main hall → Collier's Hut 78.1 m; Hut → Charcoal Yard 85.7 m; Yard → Smugglers' Den 91.9 m (Hut → Den 33.3 m);
- other: Clamp → own Fold 29.7 m; Weighstall → spring 84.1 m; Weighstall → ring 103.9 m.

### 1.11 Intended game flow on this map

The checks come from the faction build orders (kingdom §10, clans §10), rules §19 (Normal) and the neutrals §3.6 XP route. Hero 1 is
the first hero trained (naming convention); the times assume a melee hero 1.

| Time | Expected event | Map feature that drives it |
|---|---|---|
| 0:00 | **4 workers on gold; worker 1 builds the altar.** The hall trains the next worker; **5 on gold by 0:30 (kingdom) / 0:45 (clans)** | Seam gap 6 m; 5 workers saturate at about 10 gold/s |
| 1:00–1:05 | Altar done; the free hero starts training (55 s) | — |
| 1:50–2:00 | First hero out | — |
| 2:10–3:10 | Charcoal Clamp cleared: the hero alone, with 1 Pavisier, or behind 2 Hail-Swifts | 50.6 m of path from the hall, 11 s of walking |
| 3:20 | First dusk. Every night camp falls asleep (each creep within 0–6 s); the Crow Field wakes; the Folds, the Cairn Gate and the Ring never sleep | Night sight drops to 12.5 m; the spring becomes dangerous |
| 3:26–4:25 | Turnip Patch, reached after the 71.8 m (≈ 16 s) walk from the Clamp; hero level 2 partway through | It fell asleep at 3:20–3:26 and nobody has touched it, so the attacker gets the first blow |
| ≈ 4:50 | Woodward's Rest | On the way to the Fold |
| 4:55–5:50 | Own Drystone Fold; **hero level 3** (≈ 5:30, 5:50 if the fight runs long). Expand now or keep it for later | Guard mode means the natural cannot be built through |
| 5:55 / 6:25 | T2 done (kingdom / clans); hero 2 out at ≈ 6:50 / ≈ 7:20 | — |
| 7:20 | Dawn | Night camps wake; scarecrows slump |
| | ***Uncontested best case (one player creeps the shared camps alone; `creep_route` against a passive opponent):*** | |
| ≈ 6:20 | Hero 1 takes the shared Cairn Gate | Never sleeps |
| ≈ 7:00 | Hero 1 takes the Crow Field before dawn: **level 4** | The one day camp is awake at night |
| 7:15–9:00 | Hero 2: Collier's Hut → Charcoal Yard (level 2) → Smugglers' Den (**level 3** at ≈ 8:30 / ≈ 9:00) | Own-side camps keep the second hero's XP near home |
| 8:30–9:30 | First push: hero 1 level 4, hero 2 level 3 | The 49 s rush distance keeps reinforcement waves short |
| | ***Contested (both players follow their routes: the AI mirror and most real games):*** | |
| ≈ 5:30 | Both hero 1s reach level 3 on their own side | Own-side camps are never shared |
| ≈ 6:20 | Both hero 1s reach the Cairn Gate: a **creep-jack fight**. The one who arrives second fights (if its army food and hero level are at least the enemy's) or turns back (§4.4 contested-camp branch) | The Gate is 106 m from both mains; the NW knoll and the spring dell give the approach vision |
| 7:00–8:30 | The winner takes the Crow Field before dawn. The other hero 1 shops at its faction shop, then holds at its natural or scouts the enemy's Charcoal Yard approach, staying more than 18.75 m from its own hero 2 so it does not split hero 2's XP | Faction shop at home; the SE lowland behind TW1 |
| 7:15–9:00 | Both hero 2s take their own Collier's Hut and Charcoal Yard. The Den goes to whoever gets there first, usually the kingdom (about 30 s earlier); the other re-routes | The Den is on the axis, 110 m from both mains |
| 8:30–9:30 | First push: **hero 1 level 3–4, hero 2 level 2–3** (own half 1,245 raw XP plus about half of the 845 shared, §1.8) | As above |
| | ***Both cases:*** | |
| 8:00–11:00 | Shop fights in the basin, Ring attempts (hero 1 ≥ 4, hero 2 ≥ 3, ≥ 30 army food; in contested games usually after the first push), natural harassment through the SE gap | Ring pocket gaps; basin rim vision |
| 10:00–14:00 | Decisive fight; median end at 12–20 min. Long games tech to T3 (P1: third hero, top-tier upgrades) | — |
| ≈ 14:00+ | The third expansion: clear the Ring, then build at the Ring Gold Seam (AI: ≈ 14:00 or when its main seam is under 3,000 gold). A saturated main runs dry at about 20:45 | Ring pocket, guard mode |

### 1.12 Dressing guide (Greenvale)

**Name.** The internal tileset id is **`gv`** (prefix `gv_`); the docs call the tileset Greenvale. Its **player-facing name is
"Downland"** (decision of 2026-10-17): "Greenvale" was a one-word swap of a banned tileset name in the same role (clans §1.1).
"Downland" is a dictionary word for chalk hill country and fits Wether Downs; it is also the title of a 1983 home-computer game, so the
M3 name check covers it (§6 Q6). **Rule:** the full word "greenvale" never appears in a shipped filename, data string, asset id, UI
string, tooltip, loading screen or store text. It is allowed only in docs; shipped names use the `gv_` prefix (the terrain textures
already do: `gv_dirt.png`, `gv_cracked.png` …).

**Texture layers** (`terrain.gdshader` slots; ladder order from art §1.4):

| Slot | Layer | Where |
|---|---|---|
| 0 | Grass | Default |
| 1 | Thick grass | Under tree lines and along hedges |
| 2 | Dirt | Building pads and cart tracks to the flanks |
| 3 | Cracked dirt | Clamp, Collier's Hut and Charcoal Yard camps, around the gold seams, worn patches in the basin |
| 4 | Rock / cobble | Cliff bases, the ring floor, the stall plaza, the Cairn Gate |
| 5 | Grassy dirt (reuses the "sand" slot) | All transitions and shores |
| 6 | Dry golden meadow | The west and north fields, the knoll tops |
| 7 | Ochre road | Ramp → natural; ramp → basin S ramp; basin E ramp → P2 ramp; a spur to the inn. 4–6 m wide, ragged edges |

**Doodad clusters:**
- Use clusters of 3–7 objects (rock + shrub + tuft or flower) with ±20 % scale jitter.
- **Hedgerows and fences** line the roads.
- **Drystone sheepfold walls** at the Folds, **standing stones** at the ring, a **ruined field-wall gateway** at the Cairn Gate, and the
  **charcoal clamp props** at the Clamps, the Collier's Hut and the Charcoal Yards.
- **Turnip rows and poles** at the Turnip Patches; a **woodpile and felled-oak bench** at Woodward's Rest; **reeds and lily pads** at the ponds.
- A wayside **signpost** at each basin ramp and at the inn spur.

**Lighting and weather:**
- Time-of-day keys follow the world juice doc §5, with `sun_axis` at the default (screen-left).
- Cloud shadows are on. The weather is clear; a drizzle state is P2.

### 1.13 Validation tests (M1)

| Test | Pass condition |
|---|---|
| `map_symmetry` | Every per-tile layer (level, ramp, water, tex, trees) satisfies `layer[x][z] == layer[z][x]`. Object lists mirror exactly |
| `map_reachability` | Every hall pad (the Ring hall site included), seam, camp, shop, the inn and the spring are reachable from both starts. Each ramp connects exactly its two levels |
| `map_distances` | Path lengths for the §1.10 rows are within ±5 % of the table. Both players' values are equal within one tile |
| `map_economy_rules` | Run for `hall_footprint_m` = 8 and = 5. The hall–seam gap is 6.0 m edge to edge (Euclidean, to the real footprint) at all **5** seams. A tree line lies within 8–12 m of each main hall's edge. **≥ 7,000 lumber (≥ 140 trees) within 30 m of each main hall's edge** (this map: ≈ 184 trees). Natural path distance is 40–60 m |
| `map_buildability` | Each hall pad is buildable, explored-at-start for its owner, and free of ramps and cliffs. At least 1,200 m² of buildable level-2 ground per main. Both main ramps are 8 m wide |
| `camp_off_road` | No sampled point of the four lanes (§1.2, both mirrored copies) comes within **max(12 m, layout radius + 1.5 × the camp's acquire range)** of a camp centre, except on the lane routed through that camp's own landmark (centre lane and Den, NW lane and Crow Field, SE lane and Ring). That is 8.4 m for camp mode, 10 m for casters and 11.5 m for guard mode, so 12 m applies in practice; the Den (corner layout 6.4 m, acquire 6.5 m) needs 16.1 m from the three other lanes. This map: ≥ 13.0 m for every camp, 18.4 m for the Den |
| `map_sleep_mix` | At most 1 `day` camp, and at least 60 % of camps sleep at night (this map: 1 day, 11 night, 4 never: 69 %) |
| `inn_unguarded` | No camp member stands within 10 m of the inn footprint (edge to edge, the wake radius of neutrals §1.5), and no camp member's acquire range (with `acquire_override`) reaches the inn's 7.0 m use band. This map: the nearest member is 30.7 m from the footprint |
| `creep_route` | Each player's authored route (§1.8), with its fallback legs, is in the map file, and neutrals' `test_xp_route_slice` passes on it **against a passive opponent** (the uncontested best case): hero 1 level 3 by 6:00 and level 4 by 7:30, hero 2 level 3 by 9:30. It runs **4 times**, once per faction and first-hero choice; the caster-first runs (Firewright, Skymirror) get +30 s on each threshold |
| `creep_route_mirror` (M4) | AI mirror match (same faction), 40 seeds per faction, both players following their routes: **both hero 1s reach level 3 by 6:00 in ≥ 95 % of seeds; at least one hero 1 reaches level 4 by 8:00 in ≥ 80 %.** If it fails, add the §1.14 #8 own-side camps |
| `seat_fairness` (M4) | AI mirror match, 40 seeds: each seat wins 40–60 % |

### 1.14 Deviations and notes

1. ~~Natural distance~~ **Resolved:** neutrals §3.6 now uses rules §3.3's 40–60 m of path; this map gives 57.5 m (50 m straight).
2. ~~Hall–seam gap~~ **Resolved:** neutrals §3.6 now uses the 6.0 m gap.
3. **Hale Spring path.**
   - The spring (146.4 m of path) is farther than the ring (133 m). That is deliberate: the spring sits on the lane that is "not the
     shortest attack path" (neutrals §3.6).
   - Its Crow Field is night-active, so day visits are free.
4. **Generator map.** `src/world/map_generator.gd` stays as a point-symmetric test fixture. M1 adds an authored
   `data/maps/wether_downs.json`, built by a script from the tables above.
5. **Upkeep labels.** `data/factions.json` still uses the classic upkeep wording. Rules §4.5 replaces it with
   "Upkeep 0 % / 30 % / 60 %". This is an M1 data fix.
6. **Own-side camp distances differ from neutrals §3.3's bands**, because the lanes leave no off-lane ground in those bands on this
   layout (the whole 40–65 m band is the apron below the ramp, where three lanes leave home, and the natural road, which carries the SE lane):
   - Woodward's Rest is at 73.9 m of path (band 55–65 m) and sits in the natural's north-east corner rather than beside the ramp road.
     It is still "on the other side from the Clamp" and on the way to the Fold.
   - The Collier's Hut is at 78.1 m (band 60–75 m). It stays farther than the Clamp and Woodward's Rest, as neutrals asks.
   - The Charcoal Yard is at 103.5 m (band 70–90 m), behind the TW1 tree wall on the ring flank.
   - The route timings in §1.11 already include the longer walks (a few seconds each). Neutrals §3.3/§3.6 should cite these spots.
7. **Inn and stall moved.** The inn moved from neutrals' proposed (124, 124), where its footprint stood 1.5 m from the K2 cliff base, to
   (128, 128). The Weighstall moved 4 m north-west along the axis, from (96, 96) to (92, 92): the shortest route crosses the basin's SE
   half (206.4 m, against 208.7 m over the SE knoll), and from the old spot the Den's south-east creep stood 6.4 m from that route,
   inside its 6.5 m acquire range. At (92, 92) the clearance is 12.1 m. Revision 2 of this doc wrongly said the shortest route skirts the basin.
8. **Contested XP and the fallback camps.** The shared camps are meant to be fought over (§1.11). If `creep_route_mirror` fails,
   add about **360 raw XP of own-side camps per player**: a mirrored **amber 15 pair** built from the existing Cairnwake or Sootcoat
   templates (0 new creep assets), sited by the same layout search as #6 (own side, ≥ 13 m off every lane, night sleepers), then re-run
   `map_symmetry`, `map_sleep_mix` (13 of 18 would sleep at night: 72 %) and `camp_off_road`. Not placed by default.
9. **Third Gold Seam.** Neutrals §3.6 has no third mine; this map adds one inside the Standing Ring (§1.4 RS) and puts the Ring in
   guard mode. One more E11 instance (0 cr). Neutrals follow-up in §7.

---

## 2. Asset list

### 2.1 Budgets and unit prices

**Balances, read live on 2026-10-16:**
- **Higgsfield: 228.5 cr** on the `starter` plan.
- **Krea: 1,529.63 CU** of purchased CU on Individual Basic.

**Reserves:** Higgsfield **20 cr**, Krea **150 CU**. They stay untouched for fixes and retries. The one exception: the Higgsfield
reserve is released, with a ledger note and the user's OK, about 3 days before the inferred monthly reset, because unspent subscription
credits appear to be wiped (see Expiry below).

**Spendable:** Higgsfield **208.5 cr**, Krea **1,379.6 CU**.

**Since revision 2** (ledger #15–#24, 16–17 Oct): Higgsfield spent 151 cr and Krea 29.6 CU, leaving derived balances of **≈ 77.5 cr**
(57.5 spendable) and **≈ 1,500 CU** (1,350 spendable). §2.15 has the breakdown and the remaining P0.

**Reference price of one more humanoid (brief):** concept 0.25 + H3.1 9 + rig with clip 8 = **17.25 cr**. With the free auto-rigger
(§2.3) a new humanoid now costs concept 0.25–0.5 + H3.1 9 = **9.25–9.5 cr**; library clips are bought once for every unit.

| Service : model | Use | Price | Status |
|---|---|---|---|
| Higgsfield `gpt_image_2_5` | Concepts, textures, icon sheets, VFX sheets | **0.25 cr** per 1K image (0.5–1 cr at higher settings) | Verified (ledger #6–#7) |
| Higgsfield `tripo_h3_1_image_to_3d` | Characters, signature hall | **9 cr** (12 cr observed once with other settings) | Verified (ledger #10) |
| Higgsfield `3d_rigging` + 1 clip | Rig plus one library clip | **8 cr** | Verified (ledger #11–#14) |
| Higgsfield `3d_rigging`, no clip | Rig only | **5 cr** | Observed in account transactions (2 Oct); re-quote before use |
| Higgsfield `sam_3_3d` ("3D Objects") | Bake-off challenger for props, buildings and maybe units | **1 cr** | Observed in account transactions (6–8 Oct); quality on our art untested |
| Higgsfield `tripo_p2_image_to_3d`, `hunyuan3d_v3_image_to_3d` (LowPoly) | Conditional bake-off challenger (§3.2 track A) | Tripo P2 unknown; Hunyuan 14 cr (quoted) | Quote before running |
| Higgsfield Meshy image-to-3D, textured | — | 30 cr (quoted) | **Excluded**: 3.3× H3.1 with no quality case |
| Higgsfield image-to-3D + rig + 1 clip bundle | — | 38 cr (quoted) | **Excluded**: H3.1 9 + `3d_rigging` 8 = 17 cr does the same |
| Higgsfield `elevenlabs_v4`, `seed_audio`, `sonilo_music`, `mirelo_text_to_audio` | Audio alternates (dialogue batches of up to 10 voices and 10,000 characters, 4 takes); `elevenlabs_v4` is the planned route for the P1 roster's VO (§2.3) | Unknown | Probe in M1; some are marked "game pipeline only" (terms unclear) |
| Krea `krea-2-medium` | Style anchors, UI frames, P1 menu and loading art | **9 CU** | Verified |
| Krea `microsoft/trellis` (v1) | Bake-off control; becomes the default for AI buildings and props if it wins track B (static objects only: backs and sides come out dark) | **14.81 CU** | Verified (ledger #9) |
| Krea `tripo/tripo` (legacy) | — | **222.22 CU**, not 8 CU as the research assumed | **Banned** (ledger #8) |
| Krea Tripo H3.1 text-to-3D, Hunyuan3D 3.1 Rapid, and every other Krea 3D model except TRELLIS v1 | — | **148.15 / 166.67 CU** measured (ledger #2, #4); others 148–222 CU | **Banned** |
| Krea `bytedance/seed-audio-1.0` | SFX, creature vocals, ambience | 4.63 CU per ~2.5 s job. Multi-variant and long jobs are **planned at about 7 CU** (probe) | Partly verified |
| Krea `elevenlabs/tts` (`eleven_v4`) | Unit VO | Unknown. **Planned at about 1.5 CU per line** in batched requests (probe) | Probe first |
| Krea `elevenlabs/music-v2.5` | Music | Unknown. **Planned envelope 200 CU for P0** (probe with a 30 s clip) | Probe first |

**Expiry**
- **Higgsfield:** subscription credits look like they reset at each monthly renewal (16 Oct: "Subscription Credits Reset −4", then +270).
  Inference: spend month-1 P0 before about 15 Nov. The next grant of about 270 cr funds P1/P2 3D if the subscription renews.
  Confirm on the plan page.
- **Krea:** purchased packs last 90 days (pipeline §1.1). Look up the purchase date before M3.
- **ElevenLabs:** default voices expire on 31 Dec 2026.

**Sunk to date (for the record):**
- Higgsfield: 41.25 cr since the 269.75 cr baseline (41.5 cr including the dirt texture, ledger #6). That bought the `kingdom.infantry`
  concept, mesh, rig and 4 clips.
- Krea: 237 CU since the 1,766 CU baseline (the 222.22 CU legacy Tripo probe plus the 14.81 CU TRELLIS run). The earlier
  probes (ledger #1–#5, including both Krea text-to-3D runs) were charged before that baseline.

### 2.2 Pipelines (one line each; detail lives in the research docs and `tools/README.md`)

| Pipeline | Steps |
|---|---|
| **Character** | 1. Concept on `gpt_image_2_5`: A-pose, light-grey background, magenta team cloth, weapon held clear, flat light, 1.3× exaggeration, faction prompt kit with no banned tokens.<br>2. Squint test against the nearest classic unit (comparison images viewed on public web pages only, §2.16).<br>3. Tripo H3.1, `face_limit` 12,000, submitted **async**; log the job id first.<br>4. `process_model.py`: target tris, height, `--facing +x` (H3.1 outputs face +X), `--team-mask 300 --team-desaturate`, `--cleanup`.<br>5. Rig: the free auto-rigger (`tools/autorig.py` via `tools/build_slice_units.sh`; the default since commit 2bb913d), or the Higgsfield `3d_rigging` call as a fallback (the GLB is re-oriented to +Z and uploaded for a public URL; strip the stray "Icosphere" helper).<br>6. `retarget_anims.py`: library clips onto the rig, `--hips-mode vertical` (`full` for death).<br>7. `merge_anims.py`: clip names `idle walk attack death work cast birth` plus extras.<br>8. `render_preview.py` contact sheet.<br>9. Ledger entry |
| **Free auto-rigger: bpy library-skeleton transfer** (`tools/autorig.py`, CPU, 0 cr) | Copy the library rig's 24-bone skeleton (same names, A-pose rest). Fit the joints to the new mesh from landmarks (bounding-box ratios plus a hand/foot/head scan). Voxel-proxy bone heat, Data Transfer of the weights, limit to 4 influences (pipeline §3.3). Because names and rest pose match the library, `retarget_anims.py` applies without `--map` |
| **Signature building** | Concept (45° high three-quarter view) → H3.1 `face_limit` 20,000, or the bake-off winner → `process_model --width` (footprint) → construction-reveal shader → LODs |
| **Procedural building and doodad** | bpy kit scripts (box, beam trim, roof, dome, lattice, felt band, slab stack) → AI-painted tiling swatches on `gpt_image_2_5` → `texture_tools seamless` and `palette-match` → GLB. Team colour on pennants, felt bands and roof trim through a material named `*_TEAM`; the colours are the art bible §2.4 set, assigned by the slice lobby rule (§2.6), so a default match never shows a blue-trimmed kingdom or a crimson-streamered clans |
| **Texture** | `gpt_image_2_5` "seamless tileable hand-painted…" → `texture_tools seamless` (seam score ≤ 1.3) → `palette-match` against the biome or faction palette → array or atlas |
| **Icon** | 2 × 2 sheet per `gpt_image_2_5` job, with our approved style anchors as references (fallback: Krea 2 Medium at 9 CU) → split → `texture_tools icon --frame` (128 and 64 px, plus disabled variants) |
| **Voice** | Final script per faction doc §3 (names locked) → IP line check → batched TTS per speaker and category with `eleven_v4` tags → split on silence → ffmpeg character chain → −18 LUFS → Ogg. Raw takes go to `assets_src/audio/` |
| **SFX** | Seed Audio "sound effect only…" with 3–6 variants per job → split, trim, fade, −1 dBFS peak → WAV (Godot QOA) |
| **Music** | ElevenLabs Music v2.5 with `force_instrumental` → trim and loop → −16 LUFS → Ogg |

### 2.3 Characters (AI 3D, rigged)

**Status on 17 Oct (ledger #16–#20; commit 2bb913d).**
- The concepts and Tripo H3.1 meshes for B1, B3–B11 and **B16** are made (2.75 + 99 cr).
- All 12 characters, `kingdom.infantry` included, are rigged and animated with the **free CPU auto-rigger** (`tools/autorig.py`). It fits
  the library 24-bone skeleton, and `tools/build_slice_units.sh` rebuilds every unit from `assets_src/`.
- Per-unit Higgsfield rigs are no longer bought. Each library clip is bought once on the library rig (8 cr, ledger #16–#18) and
  transferred to every unit.
- **B12 (Sootcoat) is the only character mesh still to make.** The last column gives what each row cost or still costs.

| # | Asset | Height | Tris / texture | Rig | Status / Higgsfield cr | Pri |
|---|---|---|---|---|---|---|
| B1 | `kingdom.worker` (Hodman). The levy form (`kingdom.levy`, the Flail Levy) is a prop swap (flail plus kettle hat as bpy props), not a new model. "Levy" is the role word in every id, clip and icon name (`kingdom.levy`, `arm_levy`, `kingdom_flail_levy_{128,64}.png`); the reference unit's name for this form is never used as an id | 1.25 m | 2.5k / 512² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B2 | `kingdom.infantry` (Pavisier; `assets/models/units/kingdom_infantry.glb`, the library rig) | 1.75 m | 3.5k / 512² | Higgsfield (the library rig) | Done (sunk 41.25) | P0 ✓ |
| B3 | `kingdom.ranged` (Hookgunner) | 1.75 m | 3.5k / 512² | Auto-rig | Done (0.25 + 9). Plays the throw clip until `attack_shoot` 104 is bought (§2.4) | P0 ✓ |
| B4 | `kingdom.hero1` (Wheel Marshal; STR tank/support). **Weapon rules** (kingdom §2.6, squint risk Medium): the war-pick is a **one-handed** bpy prop (B21). Its **head is at most 0.35 × the haft length and has a visible curved beak**, so the 64 px black thumbnail never reads as a hammer. The wheel-shield is always held forward on the off arm. No two-handed swing, no ground slam (§2.4). **VFX rules:** no golden dome, halo, bubble or light pillar on Linden Balm or The Wagon Ring; Linden Balm shows drifting linden blossoms, The Wagon Ring physical painted wagon boards and wheels (art bible `K_WAGON`), never a ghostly or glowing ring | 2.3 m | 6k / 1024² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B5 | `kingdom.hero2` (Firewright; INT fire caster) | 2.1 m + hat | 6k / 1024² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B6 | `clans.worker` (Yurtwright) | 1.4 m | 2.5k / 512² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B7 | `clans.infantry` (Grappler; huge wrestler) | 2.0 m | 4k / 512² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B8 | `clans.ranged` (Javelineer) | 1.85 m | 3.5k / 512² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B9 | `clans.caster` (Gustcaller) | 1.8 m | 3.5k / 512² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B10 | `clans.hero1` (the Uncut; AGI duelist; trailing braid and split coat) | 2.2 m | 6k / 1024² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B11 | `clans.hero2` (Skymirror; INT seer) | 2.2 m | 6k / 1024² | Auto-rig | Done (0.25 + 9) | P0 ✓ |
| B12 | Creep: Sootcoat base. Cutpurse, **Coal-Lobber** (it throws the G1 coal lump; formerly "Smoker") and Collier come from prop and tint swaps; the Kiln-Master is the same mesh at 1.12× with a bpy apron and hood | 1.7 m | 3k / 512² | Auto-rig | **To do:** 2 concept tries 0.5 + H3.1 9 = **9.5** | P0 |
| B13 | Creep: **Tattiebogles** (Strawling, Fieldkeeper, **Crowherd**, formerly "Crowcaller"). bpy poles, sack head, cloth cards and a turnip lantern; stiff-knee procedural walk. **Art rules** (neutrals §8.2, §10.2): the turnip lantern's holes are drilled at random and **never form a face**; no carved or painted face; **no detachable or swappable heads**; **no feather-cloaked crow-man** (the Crowherd wears a patched sacking cape, with crows perched on outstretched pole-arms); **no wicker effigy body** or cage; no pumpkins | 1.2–2.0 m | 1.5k | Rigid bones | 0.5 (2 textures) | P0 |
| B14 | Creep: Cairnwakes (Cairnling, Drystone Walker, Menhir Elder). bpy slab stacks, rigid bones, retinted per tileset | 1.4–3.0 m | 1–2.5k | Rigid bones | 0.25 (1 more stone texture; drystone done, ledger #21) | P0 |
| B15 | Summons and birds: Crow (the Crowherd's summon: a **flyer** per rules §12, 3.5 m up, so idle creeps ignore it and only G+A attacks such as the Hookgunner's and the Javelineer's hit it; M1 adds the flying layer. If the layer is cut from M1, the slice Crow becomes a ground skimmer like the Hail-Swift and neutrals says so), Hail-Swift (`clans.hero2` summon: a ground summon skimming 0.6 m, opaque packed-hail material, no spirit shader). bpy low-poly bird, wing-flap in the vertex shader | 0.4 m | 300 | None | 0 | P0 |
| B16 | `kingdom.caster` (Linden Sister; healer: Herb Poultice, plus Smoke of Rue with Journeyman Papers; kingdom §11 `[SLICE]`). The T2 healer at the core of the kingdom mid-game | 1.7 m | 3.5k / 512² | Auto-rig | Done (0.25 + 9; ledger #19–#20) | **P0 ✓** |
| B17 | Critters: hare, goose. bpy primitives; procedural hop and waddle | 0.3–0.6 m | 200 | None | 0.25 | P1 |
| B18 | Fieldkeeper as an AI mesh, only if the procedural scarecrow fails review | 1.9 m | 2.5k | Auto-rig | 9.25 | P2 |
| B19 | Neutral hero (the Rat-Piper; AGI ranged trapper, crossbow), plus procedural rats. Hired at the Coaching Inn (§1.9). **Concept-review rules** (distance from another game's rat-summoning piper hero): the pipe is carried, never a melee weapon; no rat-swarm ultimate (its rats stay the Sack of Rats summon, neutrals §5.6.3) | 2.1 m | 6k / 1024² | Auto-rig | 9.25 + 1 icon sheet 0.25 + ≈ 20 VO lines | **P1** (next grant, with E17) |
| B20 | Rundling shopkeeper (P0 uses a curled-ball bpy prop instead) | 1.1 m | 2.5k | Auto-rig | 9.25 | P2 |
| B21 | Hand-prop kit: falchion, pavise, hand-cannon, hod, flail, kettle hat, javelin bundle, sabre, staff, mirror disc, rake, **war-pick** (B4 rules) and **wheel-shield**. Used whenever H3.1 thins or fuses a held item: the item is cut from the mesh and replaced by a bpy prop on the hand bone | 0.3–1.5 m | 100–400 each | Parented to `RightHand` / `LeftHand` | 0 (reuses faction swatches) | P0 |
| B22 | `kingdom.caster2` (**Lacewright**; Collegium; autocast slow Tangle Thread, ally invisibility Muslin Veil with Lacewright Journeyman Papers; kingdom §5.2: 150 g / 25 l / 2 food, 32 s). The second T2 caster, so the kingdom player chooses which casters to make | 1.7 m | 3.5k / 512² | Auto-rig; cast clip 129 | 0.5 + 9 = 9.5 + 1 icon sheet 0.25 + 14 VO lines | **P1** (next grant) |
| B23 | `clans.caster2` (**Pole-Carver**; Mirror Yurt; Mirror Pole, an invisible sentry pole; clans §5.1: 150 g / 30 l / 2 food, 32 s). Poles are bpy props | 1.7 m | 3.5k / 512² | Auto-rig; cast clip 129 | 0.5 + 9 = 9.5 + 1 icon sheet 0.25 + 14 VO lines | **P1** (next grant) |
| B24 | `kingdom.hero3` (**Flail Hetman**; STR melee stunner; kingdom §6.3; a tall human with a three-club flail, never a dwarf or a hammer, kingdom §2.6) | 2.3 m | 6k / 1024² | Auto-rig | 0.5 + 9 = 9.5 + 1 icon sheet 0.25 + ≈ 20 VO lines | **P1** (next grant) |
| B25 | `clans.hero3` (**Omen-Mother**; INT support, hex and heal; clans §6.1) | 2.2 m | 6k / 1024² | Auto-rig | 0.5 + 9 = 9.5 + 1 icon sheet 0.25 + ≈ 20 VO lines | **P1** (next grant) |

**P1 roster rows (B19, B22–B25), funded from the next Higgsfield grant** (≈ 48.5 cr: 4 × 9.5 + 9.25 + 5 icon sheets 1.25). They
restore two classic structures: the **caster choice** at T2 (every caster building in the classic game trains two casters) and the
**choice of three heroes at the altar**, with the inn as the neutral alternative, which fills the T3 hero slot (§2.6 E17). All five are
bipeds, auto-rigged, and reuse the owned clips. Their VO (≈ 88 lines) needs ≈ 132 CU, which the Krea P1 cap cannot hold: it goes through
the Higgsfield `elevenlabs_v4` dialogue model from the next grant if the M1 probe clears its price and terms, otherwise from probe
savings. Names lock by 3 Nov with the rest; VO by 15 Dec. **If neither the heroes nor the Rat-Piper are funded**, the third hero slot
leaves E17 and M4 #8 is dropped.

**Concept iteration:** 2 tries for B12 and any later rank-and-file subject, 3 for heroes and halls (all done). The concept rules and
faction prompt kits are in kingdom §2.7, clans §12.3 and neutrals §8.2. Every prompt carries the art-doc style suffix and **no** banned
tokens, and never uses the genre word for the clans' people.

**Clans jaw rule** (clans §12.3): describe the jaw positively ("very heavy square lower jaw, flat square teeth"). Put tusks, fangs,
green skin and protruding teeth in the **negative** field. For a model without a negative field (check `gpt_image_2_5`), end the prompt
with "mouth closed, no teeth showing". Reject any tooth protrusion at the squint test.

### 2.4 Animation library and per-unit clips

**Library skeleton:** the `kingdom.infantry` Higgsfield rig. It has 24 joints (`Hips`, 3 spine joints, `neck`, `Head` plus 2 head helpers,
and per side `Shoulder/Arm/ForeArm/Hand` and `UpLeg/Leg/Foot/ToeBase`; no fingers), an A-pose rest and 100 % weighting.
The auto-rigger fits that skeleton, with the same bone names, to every character. So any clip bought on the library rig transfers to
all of them, and each 8 cr clip call serves every humanoid.

**Before each clip is picked,** preview the GIFs from the Higgsfield `animation_actions` catalogue.
**Rename clips on import;** library action names never ship.

| Library clip | Source (Higgsfield id) | Cost | Pri |
|---|---|---|---|
| idle | 0 (owned) | sunk | P0 |
| walk | 30 (owned). Workers at 3.0–3.1 m/s, stride-matched | sunk | P0 |
| attack_1h | 219 (owned). Also the **Wheel Marshal's attack**: a one-handed overhand pick chop at **0.85×** with the `shield_fwd` layer, the wheel-shield leading by 0.08 m at contact (combat juice) | sunk | P0 |
| death | 8 (owned). Retarget with `--hips-mode full` | sunk | P0 |
| attack_heavy | 128 (owned, ledger #17). Played **only** by `clans.infantry` (the Grappler's flanged mace) and as the workers' chop until 237 is bought. **Never on `kingdom.hero1`**: a two-handed swing cannot hold her shield and reads as the classic armoured hammer hero | sunk | P0 |
| cast | 129 (owned, ledger #16; alternates 125, 130–137) | sunk | P0 |
| attack_throw | 421 (owned, ledger #18; alternates 239, 398) | sunk | P0 |
| run | 14 (alternates 16, 510): all units' locomotion at 4–5.5 m/s. To buy on the library rig | 8 | P0 |
| attack_shoot | 104 (alternate 232): Hookgunner and gun-tower crew. To buy on the library rig | 8 | P0 |
| work_chop | 237: bought only if 128 reads wrong as a chop on the workers | 8 | P1 |
| Procedural keyframes in bpy on the library skeleton, **needed by the loop**: build (chop arc at chest height), carry (arm hold layered over walk), push (arms forward over walk, for siege crews), **haul** (both arms overhead pulling a rope down, 0.6 s: the Sling-Cart crew's release and the clans rope-holder, §4.1), doze (sit plus breathing; sleeping creeps must read as asleep at night), **shield_fwd** (additive: the off arm holds the wheel-shield forward; layered over idle, run and attack_1h on `kingdom.hero1`) | `tools/` bpy script, 0 cr | 0 | P0 |
| Procedural keyframes, **polish**: cheer (ready / level-up / victory); **shield_plant** (Brace the Wheel: a 0.6 s crouch with the wheel-shield's rim driven down in front of her and the pick held up; fallback idle plus an additive crouch hold, never attack_heavy or a ground-slam clip); **arm_levy** (1.5 s; fallback a 1.5 s idle with the prop swap); lash (a straight forward braid snap over attack_1h, for `clans.hero1`'s Braid Lash; fallback attack_1h; never a spin, clans §2.5); stagger (additive) | `tools/` bpy script, 0 cr | 0 | P1 |
| Higgsfield top-ups, only where a procedural clip fails review: push 261, doze 268, cheer 59, heavy walk 119 (`clans.infantry`), and a brace or reload clip if the catalogue preview has one. **Cut:** the ground-slam clip 127 (`kingdom.hero1` never slams) and the spin attack 238 (nothing spins on any hero, clans §2.5) | Library rig, 8 cr each (next grant) | ≤ 40 | P2 |

**Runtime layers on top of every clip** (juice docs): bob, lean, squash on hit, lunge, topple and sink, flinch.
Siege wheels spin by distance travelled. Buildings and doodads use vertex-shader motion.

**Per-unit clip matrix** (source clip → game clip):

| Role | idle | locomotion | attack | death | work / cast | Extras |
|---|---|---|---|---|---|---|
| `kingdom.worker` | 0 | walk 30 | 219 | 8 | chop 128 (237 if bought), build (procedural) | carry; the levy form (`kingdom.levy`) uses run + 219 + arm_levy |
| `kingdom.infantry` | 0 | run | 219 | 8 | — | Brace pose (procedural, for the stance research) |
| `kingdom.ranged` | 0 | run | shoot 104 (throw 421 until bought) | 8 | — | Reload hiss timed on the backswing |
| `kingdom.hero1` | 0 + shield_fwd | run + shield_fwd | **219 at 0.85× + shield_fwd** (one-handed pick chop, shield forward) | 8 | shield_plant (procedural) for Brace the Wheel; cast 129 for Linden Balm | cheer |
| `kingdom.hero2` | 0 | run | cast 129 (staff missile) | 8 | throw 421 (flask) | — |
| `kingdom.caster` | 0 | walk / run | cast 129 | 8 | cast 129 | — |
| `clans.worker` | 0 | walk 30 | 219 | 8 | chop 128 (237 if bought) | push and haul (crew), haul (rope-holder), carry |
| `clans.infantry` | 0 | run (0.9×) | heavy 128 (the flanged mace) | 8 | — | Heavy walk (P2 clip 119, else procedural) |
| `clans.ranged` | 0 | run | throw 421 | 8 | — | — |
| `clans.caster` | 0 | walk / run | cast 129 | 8 | cast 129 | — |
| `clans.hero1` | 0 | run | 219 (sabre) | 8 | lash (procedural, a straight snap; nothing spins, clans §2.5) | Braid swing is secondary motion: 3 extra bpy bones parented to `Head` and driven at runtime by a spring (the 24-bone library rig has no braid chain, so clips ignore them) |
| `clans.hero2` | 0 | run | cast 129 | 8 | cast 129 | Mirror-polish idle (procedural) |
| Sootcoats | 0 | run | 219; the Coal-Lobber uses throw 421 | 8 | — | Doze (procedural) for night sleep |

**Build-script follow-up:** `tools/build_slice_units.sh` still gives `kingdom_wheel_marshal` `attack=$HEAVY` (the 128 swing). Change
it to `attack=$SWORD` (219) with the `shield_fwd` layer before the M2 gate (§2.16).

### 2.5 Siege and vehicles (procedural; 0 cr geometry)

| # | Asset | Method | Higgsfield cr | Pri |
|---|---|---|---|---|
| D1 | `kingdom.siege` (crew-pushed bronze bombard cart) | bpy: lathe barrel, box frame, spoked wheels. Crew = 2 × `kingdom.worker` meshes with the push clip. Recoil and wheel spin are procedural. Textures: bronze, oak planks, iron bands | 0.75 | P0 |
| D2 | `clans.siege` (sling-cart) | bpy: frame, throwing arm, wheels, sling. Crew = 2 × `clans.worker`. The arm swing is keyframed. Textures: lattice wood and felt (done, ledger #21), rope. **Art rules** (squint risk against the classic orc siege engine, a two-wheeled wooden cart with a long throwing arm): it is a **traction sling engine**: the two crew haul ropes (the `haul` pose) to swing the arm, with **no counterweight box**. At rest the **felt sling hangs from an upright arm**; there is no cup or bucket. A **low lattice cart** with a **felt hood over the pot rack**. **No spiked wheels, no skull or bone dressing**, no hide or leather panels. M2 #2 squint-tests it | 0.25 | P0 |
| D3 | `kingdom.hero2` ultimate turret | D1 barrel at 1.3× on a static carriage | 0 | P0 |
| D4 | Rally flag (team colour) and waypoint marker | bpy + shader | 0 | P0 |

### 2.6 Buildings and neutral structures

Costs are `gpt_image_2_5` reference and texture images. Geometry is 0 cr unless a row says otherwise. Both signature halls are already
AI meshes (ledger #22–#24).

| # | Asset | Method | Cost | Pri |
|---|---|---|---|---|
| E1 | `kingdom` Moot Hall (T1; `assets/models/buildings/kingdom_moot_hall.glb`, H3.1, `--yaw 90`) → Walled Burg (T2 add-ons in the half-timber kit: wall ring, taller dome) | AI 3D (done) + bpy add-ons | Done (0.25 + 9) | P0 ✓ |
| E2 | `kingdom` farm (Croft), altar (Oath Hall), barracks (Drill Yard), **Timber Yard** (lumber drop-off; the tower gate), Foundry, workshop (Wainwright Yard), **Curio Cabinet** (faction shop), Lookout → Gun Tower: **8 buildings** | **Procedural "half-timber kit"**: plaster box, beam trims, steep tile roof, stepped gable, onion dome, wheel finials, swallow-tail pennants (team colour), scaffold construction state | 0.5 (2 references) | P0 |
| E3 | `kingdom` Collegium (caster hall; trains the Linden Sister) | Same kit | 0 | **P0** |
| E4 | `kingdom` kit swatches ×6: lime plaster, dark oak beam, burgundy roof tile, rubble stone, bronze scale roof, painted planks | `gpt_image_2_5` → seamless → palette-match | Done (ledger #21) | P0 ✓ |
| E5 | *(Superseded: the Moot Hall is already the AI model, E1)* | — | — | — |
| E6 | `clans` Shell Hall (T1; `assets/models/buildings/clans_shell_hall.glb`, H3.1) with the Banner Shell's T2 banners and gong props in bpy | AI 3D (done) + bpy props | Done (0.25 + 9) | P0 ✓ |
| E7 | `clans` supply (Home Yurt, with the felt roll-up animation), barracks (Grapple Yard: yurt plus fenced ring), altar (Naming Stones: glyph stones beside a small gong frame; nothing hung on the stones), lumber drop-off and blacksmith (Casting Pit), caster building (Mirror Yurt), tower (Bow-Mast: a mast with a mounted horn bow), **Tea Tent** (faction shop: the yurt kit with a striped-felt swatch and an urn prop): **7 buildings** | **Procedural "yurt kit"**: lattice cylinder, dome, felt bands, team-colour band, ring fences, standing stones, mast | 0.75 (2 references + the striped-felt swatch) | P0 |
| E8 | `clans` kit swatches ×6: teal felt, saffron felt, lattice wood, tortoise shell, polished bronze (done, ledger #21), carved stone | `gpt_image_2_5` | 0.25 (carved stone) | P0 |
| E9 | Construction states | `build_progress` reveal shader + faction kit props (kingdom scaffold, clans felt stack) | 0 | P0 |
| E10 | Rubble and destruction decal + debris chunks | bpy + 1 texture | 0.25 | P1 |
| E11 | **Gold Seam ×5** (main and natural per player, plus the Ring's contested third): a low, square, timber-framed adit cut into a short **layered cliff** with a thin bright quartz-and-gold strata line; a **windlass headframe** on the lip; a **spoil heap**; a **wooden sluice**; two night lanterns; a collapse state. **No mine cart, rails or heaped nuggets** (neutrals §5.2, §10.2) | bpy kitbash; textures done (gold-veined rock and mine timber, ledger #21; the strata from `cliff_limestone`, ledger #15) | 0 | P0 |
| E12 | Weighstall: timber stall, cream-and-sage awning, crates, 7 m brass balance with swinging pans, curled shopkeeper prop | bpy + 3 textures | 0.75 | P0 |
| E13 | Hale Spring: moss-ringed pool, log flume, tiny waterwheel; walkable shallow water | bpy + water shader + 1 texture | 0.25 | P0 |
| E14 | Camp props: charcoal clamp (smoking turf mound), lean-to and cordwood (the Clamps; two clamps at each Charcoal Yard; a small clamp at each Collier's Hut); the Collier's Hut **sooty cottage** and the Woodward's Rest **lodge** with a woodpile and a felled-oak bench (the half-timber kit, sooted or retinted); turnip rows, poles and a crow-picked haystack; drystone sheepfold walls; standing stones and the Cairn Gate's **gateposts in a ruined field wall** (slab kit) | bpy + 2 textures + 1 reference | 0.75 | P0 |
| E15 | Loot bundle (oilcloth, twine, wax seal). **Power-up props:** a bent iron horseshoe nail (Smith's Horseshoe Nail), a patched leather juggling ball (Juggler's Ball), a hemp puzzle-knot on a wooden toggle (Riddle Knot), a leaf of wild strawberries, a drawstring purse (Dropped Purse), a faded prize rosette (Fair-Day Rosette) and a notched hazel tally-stick (Old Soldier's Tally-Stick). **No books** and no colour code per attribute (neutrals §4.3, §10.2) | bpy primitives + 1 atlas | 0.25 | P0 |
| E16 | **Coaching Inn**, sign *The Muddy Lantern* (`neutral_coaching_inn`; instant revive only): the half-timber kit retinted to neutral browns, with a stable arch, a horse trough, two chimneys and a hanging lantern sign | bpy + 2 references | 0.5 | **P0** |
| E17 | **T3 tier, no new building 3D:** the Crown Burg and the Sun-Gong Shell as bpy add-on props on the existing halls. They unlock: the level-3 Foundry and Casting Pit lines (the same icons with a third pip); the Linden Sister's **Guild Seal** (`kingdom_linden_guild_seal`; Linden Wreath); the Gustcaller's Elder Ribbon (Dust Shroud); the clans' **Proving Rite** (the Proven Javelineer is the Javelineer mesh at 1.12× with a texture swap, clans §5.2) and, for parity, the kingdom's **Burgher's Oath** at the Drill Yard (`kingdom_burghers_oath`, proposed 175 g / 150 l, 60 s: every Pavisier becomes a **Sworn Pavisier**, the Pavisier mesh at 1.1× with a texture swap, +150 HP, +1 armour, +2 damage and **Close Order**, +2 armour while another Pavisier stands within 2.5 m; kingdom doc owns the numbers); the Timber Yard's **Felling Crews** (its prerequisite **Bow Saws** is a **T2** research, kingdom §8: 110 g, 60 s, also P1 here); and the **third hero slot**, filled by the P1 third heroes (B24, B25) or the inn's Rat-Piper (B19). If none of those is funded, the slot is dropped from E17 | bpy props + data | 0 (+ 8 icons, §2.10) | P1 |
| E18 | Beacon Cairn ×2 (behind `neutral.beacon_cairns`, off by default); Dewstone ×2 (a dry, upright quartz-veined boulder; no water, basin, stone ring or blue glow) | bpy | 0.5 | P2 |

**Team colours in the slice (rule).** Every unit, building, pennant, felt band, roof trim, rally flag and minimap pip takes its team
colour from the **art bible §2.4 set** (12 colours in our own order, each ≥ ΔE 20 from every reference player colour), assigned by its
**lobby rule**:
- **Defaults:** `kingdom` **Emerald** (`#2EAE3A`, slot 4); `clans` **Royal Blue** (`#285DE6`, slot 2), with **Cornflower** as the
  clans' fallback. A default match is therefore green against blue, never blue against red.
- **Never assigned automatically:** to the kingdom, Royal Blue, Cornflower or Gold (blue over ivory and bronze is the excluded
  blue/white/gold livery; gold on burgundy and ivory is the red-ivory-gold crusader look of another franchise); to the clans,
  Crimson, Coral Rose or Violet (crimson streamers read as the reference warrior race's red). Manual picks of any free colour stay allowed.
- **Every slice capture** (dev clips, playtests, the M2 rubric renders, the M5 look-alike review, store or key art) uses the defaults.
- **Code:** `src/systems/player_state.gd` still ships the reference game's 12 player colours in near-reference order (player 1 blue,
  player 2 red); `python3 tools/ip/check_value_echo.py` fails on them today (7 team-colour errors). M1 replaces `COLORS` with the art
  bible set and implements the lobby rule; M1 #11 requires the check to exit 0.

### 2.7 Terrain and doodads (Greenvale)

| # | Asset | Method | Higgsfield cr | Pri |
|---|---|---|---|---|
| F1 | Terrain layers, 8 slots (§1.12): made (ledger #15: meadow, thick meadow, dirt, grassy dirt, cracked, road, scree) | `gpt_image_2_5` → seamless (seam ≤ 1.3) → palette-match (Greenvale, art §7.2) → `Texture2DArray` | Done + 0.5 (retries) | P0 |
| F2 | Cliff-wall rock (triplanar), cool grey: made (ledger #15: limestone, earth bank) | `gpt_image_2_5` | Done | P0 ✓ |
| F3 | Trees: 2 broadleaf variants and 1 fir; felled stump; 2 LODs; vertex-shader sway | bpy procedural; oak bark and oak and linden foliage cards made (ledger #15); fir cards to do | 0.25 | P0 |
| F4 | Rocks ×4 (procedural; the existing mossy boulder is decimated and reused), shrubs and hedgerow ×2, grass/flower tuft atlas (4 + 4), reeds and lily pads, fences ×2, signpost, cart, barrels and crates | bpy + 3 atlas images | 0.75 | P0 (fences, cart, signpost: P1) |
| F5 | Water: 2 stroke normal maps and foam | Procedural `FastNoiseLite` first; AI if it looks generic | 0.5 | P1 |
| F6 | Ground decals: scorch, ash, footprints, road edging | 2 textures | 0.5 | P1 |
| F7 | Cloud-shadow mask, brush-edge noise, paper grain (world juice §10) | Procedural noise | 0 | P0 |

### 2.8 Projectiles and VFX textures

| # | Asset | Method | Higgsfield cr | Pri |
|---|---|---|---|---|
| G1 | Projectiles: bullet tracer, javelin, bombard ball, sling stone, naphtha flask, coal lump, caster bolts, staff missile | bpy primitives + shader trails | 0 | P0 |
| H1 | FxSprites atlas sheets ×4: smoke puffs, dust, sparks, linden petals, embers, flame-tongue flipbook (8 frames), shock ring, glint star, ink crescents, leaves, feathers, our stun-star shape | `gpt_image_2_5` 2 × 2 sheets + procedural shapes | 1.0 | P0 |
| H2 | Spell-school geometry (the Orrery rings, rosettes, spokes, felt roof, wheel ring) | Procedural meshes and SDF shaders (heroes juice §5) | 0 | P0 |
| H3 | Sleep glyph (closed eye) and startle strokes | Hand-drawn vector | 0 | P0 |

### 2.9 UI art (structure is the genre convention; all art is ours, ip-safety §2.4)

The HUD follows the art bible §7: a **shared, ornament-free chassis** of four floating plates, with the faction identity only in
**inlays** on rims, corners, button bezels and end caps (§7.2). There is no per-faction console slab. **Never in any UI art:** gilded
metal, carved stone, gargoyles, skulls, relief faces, spikes, or a slab that spans the whole console.

| # | Asset | Method | Cost | Pri |
|---|---|---|---|---|
| I1 | Style anchors ×6: kingdom unit, kingdom building, clans unit, clans building, Greenvale terrain, creep | Krea 2 Medium, `creativity: raw`, fixed seeds, built on the approved concepts | 54 CU | P0 |
| I2 | `kingdom` **inlay sheet** (rails, corners, button bezels, top-bar and Ribbon end caps) over the shared chassis, per art bible §7.2: carved dark oak stained burgundy, domed dark-bronze rivets, blackened-iron corner brackets shaped as wagon-wheel rim segments, a folk-painted ivory band. Never gilded metal, carved stone, gargoyles, relief faces or a full-width slab | Krea 2 Medium with anchors (art bible T11) | 9 CU | P0 |
| I3 | `clans` **inlay sheet**: stitched ink-teal felt over **ochre-washed lattice-wood** (ochre `#B7772A`, highlight dust ochre `#C9A46A`; not the neutral inlay's pale ash `#B8A07A`), saffron blanket-stitch, bronze studs, small gong-disc corners (art bible §7.2; no lacquer, clans §2.3). The inlay must read **teal, saffron and bronze**. **Red-brown never appears on UI art** (it is the reference warrior race's console palette). Never gilded metal, carved stone, gargoyles, relief faces or a full-width slab | Krea 2 Medium (T11) | 9 CU | P0 |
| I4 | Top bar strip and resource plates (gold, lumber, food, upkeep notched coin) | Krea 2 Medium | 9 CU | P0 |
| I5 | Day/night indicator: the **Horizon Ribbon** (art bible §7.5), a 260 × 44 px window with a painted hill strip, a sun token and a moon token, and faction end caps from I2/I3. Never an orb, a globe, a disc split into sun and moon, or a round clock face. **Decision:** the Ribbon replaces the round top-centre clocks in ui juice HUD-07 (the kingdom astronomical dial and the clans bronze mirror disc), because a round day clock squints toward the classic day/night orb (ip-safety §2.4). HUD-07's lit frame, golden-hour rim and day tally move onto the Ribbon and its end caps (§7 follow-ups) | Krea 2 Medium (housing) + shader | 9 CU | P0 |
| I6 | Panel sheet: tooltip parchment; 2 × 3 inventory slots; hero buttons on the left edge with **HP, mana and XP bars, the level badge and the pulsing "+" skill-point seal**; the **12-tile selection grid** (40 px) with a **subgroup lift state**; queue slots; the **idle-worker button** with its count badge | Krea 2 Medium | 9 CU | P0 |
| I7 | Command button frames and states (normal, hover, pressed, disabled, autocast border, cooldown sweep) | Programmatic (`texture_tools icon --frame`) + shader | 0 | P0 |
| I8 | Minimap frame (cut from I2/I3), shield camp pips, faceted-nugget mine glyph, camera trapezoid | Procedural | 0 | P0 |
| I9 | Faction emblems (Ember Wheel; gong with twin winds) as vector SVG | Hand-built vector, no AI | 0 | P0 |
| I10 | Selection rings, health and mana bars, fog, placement ghost | Shaders (architecture §11) | 0 | P0 |
| I11 | Fonts: OFL fonts per art bible §7.7 (Alegreya SC and Alegreya Sans; faction display faces). Licences go in `CREDITS.md` | Google Fonts (OFL) | 0 | P0 |
| I12 | Cursors: pointer, target (green / yellow / red), invalid, 8 scroll arrows, build. **No hand, gauntlet, glove or claw**. The **programmatic target states (green / yellow / red) are P0** at 0 cost, because every hero ability is castable from M1; painted cursors stay P1 | Programmatic first; Krea sheet if needed | 0–9 CU | P0 (programmatic targets) / P1 |
| I13 | Main-menu background | Krea 2 Medium | 9 CU | P1 |
| I14 | Loading screens ×2 (one per faction) | Krea 2 Medium | 18 CU | P1 |
| I15 | Victory and defeat banners | Programmatic: emblem + text | 0 | P1 |
| I16 | **Type glyphs** for the info plate: 7 attack types (Blade, Pierce, Siege, Arcane, Heroic, Raw, Spell) and 6 armour types (Light, Medium, Heavy, Fortified, Hero, Unarmored), per art bible §7.8 | Hand-built vector | 0 | P0 |
| I17 | Control-group badge strip | Programmatic | 0 | P1 |
| I18 | Neutral inlay (main menu, shop window, neutral and creep info) | Krea 2 Medium (T11) | 9 CU | P1 |

One T11 sheet per inlay is the plan. If a single sheet cannot hold the art bible §7.3 parts cleanly, the per-part route (about 6 × 9 CU
per inlay) comes out of the Krea P1 cap.

### 2.10 Icons (128 / 64 px with disabled variants; 4 per `gpt_image_2_5` 2 × 2 sheet)

**One icon per research line:** the level shows as 1–3 pips under the icon (art bible §7.4), so a two-level line needs one icon. An
ability unlocked by a research reuses that research's icon.

| Group | Count | Pri |
|---|---|---|
| Commands: move, stop, hold, attack, patrol, **attack ground** (both siege units, rules §18.4), build basic, build advanced, gather, return cargo, repair / mend (autocast), cancel, rally, learn skill, select idle worker, hero select, set autocast | 17 | P0 |
| `kingdom`: units 6 (worker, Flail Levy `kingdom_flail_levy`, infantry, ranged, caster, siege); hero abilities 8; buildings 10; research 10 icons for 14 researches; worker defence 3 (Take Up the Flail, Levy Horn, Lay Down Flails; the per-Levy Lay Down the Flail reuses the last); Herb Poultice 1 (Plant Pavise, Signal Shell and Smoke of Rue reuse their research icons); hall upgrade 1; **tower upgrade 1 (Lookout → Gun Tower)** | 40 | P0 |
| `clans`: units 5; hero abilities 8; buildings 8; research 7 icons for 10 researches; garrison and gong 4 (Roll the Felt, Unload All, Sound the Gong, All Clear); Unbind 1 (Wind at Your Back reuses Second Ribbon); hall upgrade 1 | 34 | P0 |
| Items and shop services: the 33 neutral slice items and the Fair Exchange button (neutrals §4, §8.1), 5 Curio Cabinet items (kingdom §7.4), 7 Tea Tent items (clans §9). The power-up icons show the E15 objects (nail, ball, knot, berries, purse, rosette, tally-stick): no books | 46 | P0 |
| Resources and HUD glyphs | 6 | P0 |
| T3 tier (E17): hall upgrade ×2, Linden Guild Seal (`kingdom_linden_guild_seal`), Gustcaller Elder Ribbon, Proving Rite, Burgher's Oath, Felling Crews; plus Bow Saws (T2) | 8 | P1 |
| Creep ability icons (shown when selecting creeps; neutrals §8.1) | 17 | P1 |
| P1 roster (next grant): Lacewright sheet (unit, Tangle Thread, Lacewright Journeyman Papers, which Muslin Veil reuses, + 1 spare); Pole-Carver sheet (unit, Mirror Pole + 2 spares for its later abilities); Flail Hetman, Omen-Mother and Rat-Piper ability sheets (4 each; hire and hero buttons use rendered busts, J2) | 20 (5 sheets) | P1 |

**Totals:**
- P0: 143 icons in 36 sheets, plus about 25 % rejects → **45 sheets ≈ 11.25 cr**.
- P1: 25 icons in 7 sheets ≈ 1.75 cr, plus the P1 roster's 5 sheets ≈ 1.25 cr (next grant).
- Placeholder icons (text plus silhouette, generated programmatically) serve M1.
- **Composition rule:** never repeat a famous icon composition, such as a glowing hand for a heal (ip-safety §2.4).

### 2.11 Portraits

| # | Asset | Method | Cost | Pri |
|---|---|---|---|---|
| J1 | Live 3D portrait: the unit's own model and clips, close camera on the head, procedural "talk" head-bob while a line plays | 128² `SubViewport`, `UPDATE_WHEN_VISIBLE` | 0 | P0 |
| J2 | Hero buttons on the left edge and bust thumbnails for tooltips | Rendered from the models (`render_preview`-style bust camera) | 0 | P0 |
| J3 | Painted hero busts for loading screens and the victory screen | Krea 2 Medium (4 × 9 CU) | 36 CU | P2 |

### 2.12 Voice

Casting, tags and sample lines are in kingdom §3 and clans §3 (preset voices only, never cloned). The **IP line check** is mandatory:
compare every line with the classic quote pages and with ip-safety §2.2. Names must be **locked before generation** (synthesis step).
Before generation the final scripts are exported to `tools/prompts/vo/`, a default path of `check_banned_terms.py`, so every line is
also machine-checked.

**Worker completion id: `built`, label "Built".** Category names become VO ids and file names (audio §4.6), so no category is named
after a banned line. The **art bible currently says the opposite**: its review #23 renamed `built` to `job_done`, and that id and the
label "Job done" appear in its §8.1, the §8.2 table, §13 #16 and the review log; clans §3.3, juice AUD-03, the economy juice and a
debug print in `tests/output/probe_relabel.gd` follow it. VO files would then be named like `hodman_job_done_01.ogg`, an echo of the
banned catch-phrase in the very file names this rule protects, and the checker cannot see it (it maps `_` to a space only in file
names, and bans only the possessive and plural spellings). **This plan wins for slice VO:** the id is `built` and the label "Built"
(kingdom §3.2 already uses it). §7 lists the renames, then the ban of `job done`, `job_done` and `job-done`, before names lock on 3 Nov.

**VO lint** (part of the IP line check; applies to every P0 and P1 line):
- No line uses **poke, poked, poking, tap, tapped, tapping, prod or jab**: the clicking-as-physical-touch premise is the reference
  game's best-known annoyed-line family. Clicks are called clicks.
- **No Ready line starts with "Ready to"** (the frame of a banned line).
- No crew splits a line or punchline between two voices (the reference artillery crew's device); a two-person crew speaks as one
  speaker or in unison.
- No completion line or label built on "done" for workers (§8.1 of the art bible keeps its own ban on "…'s done" and a bare "Done.").

| Speaker | Full set (faction doc) | **P0 lines** | P1 to full | Pri |
|---|---|---|---|---|
| `kingdom.worker` (incl. the `built` line) | 19 | 15 | +4 | P0 |
| `kingdom.infantry` | 18 | 14 | +4 | P0 |
| `kingdom.ranged` | 18 | 14 | +4 | P0 |
| `kingdom.caster` (Linden Sister) | 18 | 14 | +4 | **P0** |
| `kingdom.siege` (Bombard Wagon: **one speaker**, below) | ≈ 14 | 8 | +6 | P0 |
| `kingdom.hero1` | 26 | 20 | +6 | P0 |
| `kingdom.hero2` | 26 | 20 | +6 | P0 |
| `kingdom` advisor (the Reeve) | 21 | 18 | +3 | P0 |
| `clans.worker` (incl. the `built` line) | 19 | 15 | +4 | P0 |
| `clans.infantry` | 18 | 14 | +4 | P0 |
| `clans.ranged` | 18 | 14 | +4 | P0 |
| `clans.caster` | 18 | 14 | +4 | P0 |
| `clans.siege` crew (two brothers **speaking in unison**, below) | ≈ 14 | 8 | +6 | P0 |
| `clans.hero1` | 26 | 20 | +6 | P0 |
| `clans.hero2` | 26 | 20 | +6 | P0 |
| `clans` advisor (the gong-keeper) | 19 | 18 | +1 | P0 |
| Weighstall shopkeeper (neutrals §5.3) | 10 | 5 | +5 | P0 |
| **Total** | **≈ 328** | **251** | **+77** | |

**P0 line mix:**
- Regular unit: Ready 1, What 3, Yes 3, Attack 2, **Annoyed 5**: 14. The annoyed click-spam run is the signature, a 4–6-line
  micro-story (audio §3.2) that needs room for the joke to land (the classic game's rank-and-file units have 4–8, audio §1.2), and is
  never cut first.
- **Workers:** as a regular unit plus the `built` line: 15.
- **Hero:** Ready 1, What 4, Yes 4, Attack 3, **Annoyed 5**, one bark per ability (4), level-up 1, death 1. That is 23; P0 records 20 by
  dropping a What, a Yes and an Attack. Hero Annoyed never drops below 5.
- **Advisor:** one line per rules §17.3 trigger, 18 per faction: unit, building and worker under attack; hero died, revived and
  levelled; building, research and unit finished; need gold, lumber, supply and hero slot; mine low and exhausted; upkeep tier rises;
  cripple countdown. (Dusk and dawn are stingers only.) **Inventory full** (rules §6.8) is an error text plus the S39 / S40 error click
  at P0, not an advisor line; the hero `pack_full` line (art bible §8.2) is P1.
- **Siege, 8:** Ready 1, What 1, Yes 1, Attack 1, **Annoyed 4**.
- **P1, first item: Warcry**, 1 line per combat unit and hero (the 4 infantry, ranged, caster and siege speakers per faction and the
  4 heroes: 12 lines ≈ 18 CU).

**Bombard Wagon (`kingdom.siege`): one speaker.** The Elder gunner speaks, deadpan; the Younger is heard only as non-verbal coughs and
effort sounds. The two-gunner double act in kingdom §3.2 is retired for this slot: a bickering two-voice crew on the human-kingdom
faction's two-man gunpowder artillery copies the classic game's character choice for that slot, even with new words. Proposed P0 lines
(original; acks within the art bible's 4-word limit; they still go through the IP line check):

| Category | Line |
|---|---|
| Ready | "Barrel's swabbed. Nobody touch the fuse." |
| What | "Talk slow. Measuring powder." |
| Yes | "Chock the wheels." |
| Attack | "Ranging shot first." |
| Annoyed 1 | "Measure twice, fire once. You've measured eleven times." |
| Annoyed 2 | "The lad's coughing, not laughing. Probably." |
| Annoyed 3 | "Now he's laughing. Powder doesn't like laughing. Neither do I." |
| Annoyed 4 | "Right. I'm chalking 'the boss' on the next ball. Neat letters, mind." |

**Sling-Cart (`clans.siege`): two brothers in unison.** The finish-each-other's-sentences act is retired: a two-man artillery crew
splitting lines and punchlines is the reference human artillery crew's defining device, and moving it to the warrior-people faction keeps
the same character choice (the reference warrior race's catapult does not speak). The brothers speak **together**, as a hauling count
or a single shared sentence: their joke is that they always agree, even when wrong (clans §3.2 tic). The younger brother's effort
grunts on the rope (non-verbal) are mixed under the release. Proposed P0 lines:

| Category | Line (both, in unison) |
|---|---|
| Ready | "Pots stacked. Wheels round." |
| What | "Two ropes, one arm." |
| Yes | "Heave on the count." |
| Attack | "One, two… loose!" |
| Annoyed 1 | "Hm-hm. One, two… three? We only count to two." |
| Annoyed 2 | "We both heard that. We both agree it was rude." |
| Annoyed 3 | "Mother said never argue before guests. So we agree: you are strange." |
| Annoyed 4 | "We discussed it, together, as always. The answer is more pots." |

**Deaths** of regular units are non-verbal (SFX S15/S16).

**Generation and cost:**
- Batch per speaker and category, about 3 requests per speaker for P0 (about 55 requests).
- P0 envelope **379 CU** (251 lines, planned at about 1.5 CU per line); P1 **106 CU**, which funds the Warcry lines first and then
  about 58 more of the 77 P1 lines; the last ≈ 7 (Whats) wait for probe savings.
- Probe both the Krea `elevenlabs/tts` and the Higgsfield `elevenlabs_v4` dialogue model (up to 10 voices, 4 takes) with the same 5-line script, then pick the cheaper per accepted line.
- **Deadline:** all lines are generated, processed and archived **by 15 Dec 2026**.

### 2.13 SFX (Seed Audio jobs of 3–6 variants each; planned at about 7 CU per job, to be probed)

**P0 (50 ids, 54 jobs ≈ 378 CU)**

| Group | Jobs |
|---|---|
| Combat | S01 light swing (blade and sabre) · S02 heavy swing (mace, war-pick) · S03 hit metal · S04 hit wood (pavise, lattice) · S05 hit flesh/leather (no gore) · S06 hit stone · S07 hit straw/felt · S08 hand-cannon "whump-crack" + smoke hiss (`kingdom.ranged`, gun tower) · S09 javelin throw (`clans.ranged`) and horn-bow loose (bow-mast) · S10 missile impacts (bullet, javelin into wood, body, dirt) · S11 bombard boom (`kingdom.siege`, `kingdom.hero2` ultimate) · S12 sling-arm thwack + rope creak (`clans.siege`) · S13 siege impact · S14 building hit + crumble |
| Deaths | S15 kingdom non-verbal deaths · S16 clans non-verbal deaths · S17 hero-death stings (one per faction) |
| Creeps (non-verbal sets) | S18 Sootcoats (cough, "Hup!", effort huff, pain, death; the Coal-Lobber's coal toss) · S19 **Tattiebogles** (creak, straw rustle, dry hiss, collapse, the Crowherd's crow caw) · S20 Cairnwakes (grind, slab clack, hum, crumble) |
| Spell schools (riser → release → tail; school ids per heroes juice §5) | S21 **Blossom** (`blossom`) · S22 Ember · S23 Gale · S24 Gloam · S25 Orrery · S26 Stone · S27 hero level-up signature (×3) · S28 caster bolt + haste whoosh |
| Status and items (moved up from P1: the mechanics are P0 and players read them by ear) | S47a stun and root application (stun bonk chime, root cinch) · S50 recall (horn ×3, felt whirl, arrival thump; the free first-hero recall item is in use from minute 2) · S69 invisibility fade and reveal puff (the Uncut's Dust Veil and its Tattle-Burrs counter) |
| Economy | S29 chop + tree fall · S30 mine enter/exit + gold deposit · S31 lumber deposit · S32 kingdom construction loop (mallet, saw) · S33 clans construction loop (felt thumps, rope creak) · S34 kingdom "complete" (scaffold fwump + planed-wood stroke) · S35 clans "complete" (gong swell) · S36 placement stamp + foundation thoomp · **S57a burning-building fire-bed loop** (moved up from P1: juice BLD-15 makes "every burning building visibly and audibly burns" a P0 rule, and the crackle is the cue to repair or defend) |
| Faction signatures | S37 levy horn (two-note low wooden horn, our own interval) · S38 bronze gong strikes + felt roll |
| UI | S39 kingdom click and error · S40 clans click and error · S41 minimap ping + under-attack sting · S42 item pickup, drop, coin bounty, potion · S43 research complete + upkeep-tier tick |
| Ambience | S44 Greenvale day bed (60 s loop) · S45 Greenvale night bed (60 s loop) · S46 dusk and dawn stingers (our own; no wolf howl or rooster). Seed Audio has no duration control, so each bed is planned as **3 jobs** crossfade-stitched in ffmpeg (S44a–c, S45a–c) |

**Ear test** (§2.16 step 2c) before any of S17, S27, S35, S41 and S43 ships.

**P1 (23 jobs ≈ 161 CU)**

| Group | Jobs |
|---|---|
| Status and spells | S47b blind ting, burn tick · S48–S49 4 ultimate stingers · S51 summon arrive/expire |
| Building select one-shots | S52–S55, 2 sets per faction |
| World | S56 mine low / collapse · S57b destruction patter (the fire-bed loop S57a is P0) · S58 flail chain rattle · S59 wagon creak + wheel rumble loops · S60 shop buy / sell / can't afford · S61 hare, goose · S62 crows + sparrow flush · S63 spring and pond water loops · S64 clamp fire crackle · S65 wind gusts · S66 lark, owl, frog sweeteners · S70 creep snore + yawn |
| Mix and UI | S67 battle-bed loop · S68 page turn / skill learned · S71 victory and defeat UI stings |

### 2.14 Music (ElevenLabs Music v2.5, `force_instrumental: true`; prompts in kingdom §3.3, clans §3.4, audio §4.5, with names updated)

| # | Track | Length | Pri |
|---|---|---|---|
| MU1 | `kingdom` in-game 1 (village band gone to war: hurdy-gurdy, bagpipe drone, cimbalom-like dulcimer, fiddle, frame drum, low horns) | 3:30 | P0 |
| MU2 | `clans` in-game 1 (galloping frame drums, bronze gongs, two-string fiddle, jaw harp, overtone chant) | 3:30 | P0 |
| MU3 | Main menu (both palettes meet), loopable | 2:00 | P0 |
| MU4 | Victory stinger (neutral instrumentation) | 0:12 | P0 |
| MU5 | Defeat stinger | 0:12 | P0 |
| MU6–MU7 | Second in-game track per faction | 2 × 3:30 | P1 |
| MU8–MU9 | Third in-game track per faction | 2 × 3:30 | P2 |
| MU10 | Night / creep-camp exploration layer | 2:30 | P2 |
| MU11–MU14 | Per-faction victory and defeat stingers | 4 × 0:12 | P2 |

**Budget:**
- P0 envelope **200 CU**.
- P1 is funded from whatever the Krea P1 cap leaves, otherwise from a cheaper Higgsfield music model if the probe shows one.
- Rotation: shuffle, 20–40 s gaps, never battle-switched.
- Every piece, MU4 and MU5 included, passes the ear test (§2.16 step 2c) before it ships.

### 2.15 Budget roll-up (re-based on ledger #24, 17 Oct)

Production moved ahead of revision 2's plan (ledger #15–#24). Most of the planned 3D and texture work is already bought, so this
section counts what was spent and what remains. The balances are **derived from the ledger, not read live**; ledger #25 records the next
live reading, and any difference moves the margin.

**Higgsfield, spent since revision 2** (the revision 2 balance was 228.5 cr):

| Bucket | Items | cr |
|---|---|---|
| Concepts | 11 characters (B1, B3–B11, B16) + 2 halls (ledger #19, #22) | 3.25 |
| Character meshes | 11 × H3.1 (ledger #20) | 99.0 |
| Hall meshes | 2 × H3.1, Moot Hall and Shell Hall (ledger #24), after TRELLIS failed on both (#23) | 18.0 |
| Library clips | cast 129, heavy 128, throw 421 on the library rig (ledger #16–#18) | 24.0 |
| Textures | 13 terrain, cliff, foliage and bark + 14 building swatches (ledger #15, #21) | 6.75 |
| **Spent** | | **151.0** |

Derived balance **77.5 cr**; reserve 20 → **57.5 cr spendable**. Spend it before the inferred ~15 Nov reset.

**Higgsfield, remaining P0:**

| Bucket | Items | cr |
|---|---|---|
| Character mesh | B12 Sootcoat: 2 concept tries + H3.1 (free auto-rig) | 9.5 |
| Library clips | run 14, attack_shoot 104 | 16.0 |
| Textures, references, swatches, VFX sheets | 33 images × 0.25: B13 2, B14 1, D1 3, D2 1, E2 2, E7 3, E8 1, E12 3, E13 1, E14 3, E15 1, E16 2, F1 retries 2, F3 1, F4 3, H1 4 | 8.25 |
| Icons | 45 sheets × 0.25 (§2.10) | 11.25 |
| **Remaining P0 total** | | **45.0** |
| **Margin** | Spent only by the ladder below | **12.5** |
| **Reserve** | Untouched; released about 3 days before the reset with the user's OK | **20.0** |
| **Balance (derived)** | | **77.5** |

What the review fixes cost here: B16 and its Collegium (E3) moved to P0 at no new cost (the mesh is ledger #19–#20; the Collegium is
kit-built); one icon per research line kept the icon growth to 7 sheets (1.75 cr) for 25 more icons; the Tea Tent swatch, the inn
references and the new camp props add 1.0 cr; the 2-try concept rule for B12 saves 0.25.

What the round-2 fixes cost: **0 cr this month** (the Gun Tower icon fits the 45 sheets; the `haul` pose, the D2 rules, Burgher's Oath,
the rope-holder, the flying layer, the third Gold Seam and the lobby colours are code, data or bpy). The **next grant** carries the P1
roster (48.5 cr, §2.3) and 0.25 cr more of P1 icons. **Krea P0 +31 CU** (VO +24 for the 5-line annoyed runs, S57a +7), so the P1 cap
falls from 325 to 294 CU.

**Margin ladder** (decided in this order; each rung is logged in the ledger):
1. **A P0 mesh fails the rendered squint test or the rubric** (§2.16, M2 #6): re-generate it (0.25–0.5 concept + 9 cr). Held items are
   bpy props (B21), so a weapon read such as the war-pick is fixed in bpy at 0 cr first.
2. **work_chop 237** (8 cr), only if the 128 swing reads wrong as a chop on the workers.
3. **Concept tries stay at 2** for B12 and any rank-and-file re-generation (planned, not a fallback).
4. **Defer B12's mesh** (9.5 cr) to the first days of the next grant. Graybox creeps stay in, and M2 slips by up to a week.
5. A SAM 3 props probe (§3.2, 1 cr per asset), only if the margin still holds 5 cr after M2.
6. Whatever is left after M2 goes on re-generating the weakest P0 asset (by the §3.3 score), then on P1 icons.

**Worst case** (one mesh re-generated and 237 bought): 9.5 + 8 = 17.5 cr. Margin 12.5 + deferring B12 9.5 = 22.0, so the plan still fits
without touching the reserve.

**Higgsfield, next grant (≈ 270 cr if renewed; unverified):**
- P1: B17 critters 0.25; 237 if not bought 8; P1 icons 1.75; E10 0.25; F5–F6 1.0.
- **P1 roster** (§2.3), in this order: B22 Lacewright and B23 Pole-Carver 19.0 + 2 icon sheets 0.5; B24 Flail Hetman and B25
  Omen-Mother 19.0 + 2 icon sheets 0.5; B19 Rat-Piper 9.25 + 1 icon sheet 0.25. Total **48.5 cr**, plus their VO through
  `elevenlabs_v4` if the probe clears it.
- P2: library clip top-ups ≤ 40; B18 and B20 ≈ 18.5; E18 0.5.
- Re-generations of weak P0 assets ≈ 40, and audio alternates.

**Krea** (revision 2 balance 1,529.6 CU; ledger #23 spent 29.63 CU on the two hall TRELLIS runs, the plan's "bake-off control" line;
derived balance **1,500.0 CU**, reserve 150 → **1,350 CU spendable**):

| Bucket | CU |
|---|---|
| Style anchors (I1) | 54 |
| UI P0 (I2–I6) | 45 |
| SFX P0 (50 ids in 54 jobs, including the multi-variant probe; S57a added) | 378 |
| VO P0 (251 lines, including the 5-line probe; 5-line annoyed runs) | 379 |
| Music P0 (5 pieces, including the 30 s probe) | 200 |
| **Remaining P0 total** | **1,056** |
| **P1 cap** | **294** |
| Reserve | 150 |

P1 is allocated in this order:
1. SFX P1, 161.
2. VO P1, 106 (Warcry lines first, §2.12).
3. UI P1 gets the remaining 27 CU: I13 and I14 (27 CU). I12's programmatic target states are P0; I18 waits for savings.
4. Music P1 has nothing left. It is funded only if the probes land under estimate, or from a Higgsfield music model once its terms
   are read (§5), or after the slice.

If the probes come in above estimate, cut P1 from the bottom of the list. Never cut P0 annoyed lines.

### 2.16 Naming, ledger and IP gate (every asset)

**Paths:**
- `assets/models/units/<faction>_<role>.glb`
- `assets/models/buildings/<faction>_<role>.glb`
- `assets/models/neutral/<id>.glb`
- `assets/textures/terrain/gv_<layer>.png` (`gv` is the internal tileset id; the word "greenvale" never appears in a shipped filename,
  data string or asset id, §1.12)
- `assets/icons/<faction|common|items>/<id>_{128,64}.png`
- Audio follows audio §4.6, using the faction ids `kingdom` and `clans`.

**Raw outputs** go in `assets_src/` and never ship.

**Gate** (ip-safety §5.2):
1. No banned tokens in the prompt, the negative prompt or the filename (`tools/ip/check_banned_terms.py`). The term list still lacks
   lines and names that ip-safety §2.1–§2.2 ban explicitly; §7 lists the additions and the order they go in. Until they are in, the
   VO lint (§2.12) and the reviewer cover them by hand.
2. A side-by-side squint test against the nearest classic unit, building or icon.
   - **2b. UI:** a squint test of an in-game HUD screenshot against the classic game's human and orc consoles. It must show the art
     bible §7.2 shared chassis with faction inlays only, the Horizon Ribbon (§2.9 I5), and no gilded metal, carved stone, gargoyles,
     relief faces or full-width slab. The **clans inlay must read teal, saffron and bronze**, with no red-brown anywhere (§2.9 I3).
   - **2c. Audio ear test:** a reviewer A/B-listens to each S17, S27, S35, S41 and S43 output and to MU1–MU5 against the nearest cue or
     race theme of the classic game (listening only, never as a model input). Reject any recognisable melodic contour, interval sequence
     or rhythmic figure, and log the verdict in the ledger.
3. Distinctness rubric axes still hold on the rendered model.
4. A ledger entry: service, model, plan tier, job id, prompt, seed, references, cost, reviewer, squint or ear-test result, human edits.

**Comparison material** (steps 2, 2b, 2c and the M1 map look-alike check) is viewed or heard on public web pages at review time only.
Never download it into the repo or `assets_src/`, or into Krea styles or moodboards or the Higgsfield media library, where it could end
up as a reference input (ip-safety §2.7). The ledger records the verdict and the page URL, not the image or the audio.

---

## 3. 3D generator bake-off

### 3.1 Round 1 (done, 2026-10-16; ledger #7–#14)

Input: the `kingdom.infantry` A-pose concept, made with `gpt_image_2_5` (0.25 cr). This was the brief's "first real unit concept through
3–4 generators": three image-to-3D generators ran on the same concept and seed, after two Krea text-to-3D probes.

| Generator | Cost | Result | Verdict |
|---|---|---|---|
| *Probe:* Krea Tripo H3.1 text-to-3D (pine tree) | 148.15 CU | Charged, but the sync call timed out and the result was lost | Banned for cost. Taught the rule: always submit 3D **async** and log the job id first |
| *Probe:* Krea Hunyuan3D 3.1 Rapid text-to-3D (boulder) | 166.67 CU | 50k faces, 4K texture; the mossy boulder is reused (F4) | Banned for cost |
| Krea Tripo legacy (`tripo/tripo`) | **222.22 CU** | Quality about equal to H3.1, 482k tris, faces +X | Banned for cost. The research's "8 CU" figure was wrong |
| Krea TRELLIS v1 | 14.81 CU | Front usable; sides and back nearly black | Only for static objects seen from the front |
| **Higgsfield Tripo H3.1** (`face_limit` 12,000) | **9 cr** | 11.4k tris, painted all round, holds up at 4k tris | **Winner** for characters |
| Higgsfield `3d_rigging` + 1 clip | 8 cr | 24-bone humanoid, 100 % weighted, clips in place | Adopted. This rig became the library skeleton |

### 3.2 Round 2 (M1, days 1–5): three open questions, three tracks

**Status (17 Oct): overtaken by production; kept as the record of the plan.** H3.1 made all 11 remaining characters (ledger #20),
`clans.hero1`'s braid and sabre included (track A). TRELLIS failed on both halls (black sides, ledger #23), so H3.1 made them too
(ledger #24, track B). The free auto-rigger (commit 2bb913d) closed track C in favour of the CPU transfer. Only the SAM 3 props probe
is left, as margin rung 5 (§2.15).

**Track A — hero shapes.** Concept: `clans.hero1` (split riding coat, ground-length trailing braid with a weight, normal-length straight sabre carried low). It has the thinnest parts and the most cloth in the slice.

| Generator | Settings | Cost | Notes |
|---|---|---|---|
| Higgsfield Tripo H3.1 | `face_limit` 12,000, `texture_alignment: original_image`, PBR off where allowed | 9 cr | Becomes production if it wins (counted in B10) |
| Higgsfield SAM 3 3D Objects | Default; textured GLB | 1 cr | Cheapest candidate |
| Krea TRELLIS v1 (control) | Texture 1024 | 14.81 CU | Measures back and side darkness on a character |
| *Conditional fourth:* Higgsfield Tripo P2 or Hunyuan3D v3 LowPoly (Meshy is excluded at 30 cr) | The lower quote, at most 14 cr. For P2: `delight: false` to keep painted light; `face_limit` 12,000 | 9–14 cr | Runs **only if H3.1 scores ≤ 2 on mesh integrity** (the braid or sabre is lost), paid from the margin (§2.15 rung 5). A cheaper generator that might match H3.1 is already covered by SAM 3 |

**Track B — signature building.** Concept: the `clans` hall (tortoise-shell dome) at a 45° high three-quarter view.

| Generator | Settings | Cost | Notes |
|---|---|---|---|
| Higgsfield Tripo H3.1 | `face_limit` 20,000 | 9 cr | Production if it wins (counted in E6) |
| Higgsfield SAM 3 3D Objects | Default | 1 cr | If it passes, it becomes the default for E5, E16 and props, saving 8 cr per asset |
| Krea TRELLIS v1 | Texture 1024 | 14.81 CU | Buildings always face the camera and the yaw is locked, so the back is never seen. The sides are seen near screen edges, so score them at ±30° yaw. If it passes, TRELLIS becomes the default for AI buildings and props, paid in CU, which frees Higgsfield credits for characters |
| *If all three fail* | — | 0 | No further paid generator: the hall falls back to the yurt kit with a bpy shell-plate dome (E6), like every other building |

**Track C — rigging method.** Input: the `kingdom.worker` H3.1 mesh (production, B1). Run it first, because its result decides rung 1 of the
margin ladder (§2.15).

| Method | Cost | Notes |
|---|---|---|
| bpy library-skeleton transfer | 0 cr | The proposed default for B6, B7, B9, B12 |
| Higgsfield `3d_rigging`, rig only | 5 cr | The better of the two becomes the worker's production rig. If rig-only is no longer sold, use rig + the push clip 261 (8 cr; the extra 3 cr come from the margin), which also gives the siege crews a native push clip |

Compare both with the same retargeted clips: idle, walk, chop, death.

**Sequence** (M1, days 1–5):
- Day 1: concepts for `kingdom.worker`, `clans.hero1` and the `clans` hall (3 tries each), squint test, approve one each.
- Day 2: track C (H3.1 worker mesh, then the bpy transfer and the rig-only call in parallel). Submit the track A and B jobs the same day.
- Days 3–4: process, preview and score every candidate (two reviewers).
- Day 5: decisions logged; the conditional fourth generator runs only if rung 5 allows it, with a decision by 22 Oct at the latest.

**Procedure** (all tracks):
- Submit every 3D job **async**; record the job id in the ledger before waiting.
- Process with `process_model.py` to the final budget: hero 6k, building 10k, worker 2.5k.
- Run `render_preview.py`. Its sheet includes the in-game 256 px crop at the RTS camera.
- Add 3 extra renders: yaw ±30° (screen-edge perspective) and night grading.

### 3.3 Scoring rubric and decision rules

Each criterion is scored 1–5 by two reviewers, then averaged and weighted.

| Criterion | Weight | How it is measured |
|---|---|---|
| Silhouette at game scale | 30 | The 64 px black-fill thumbnail is identifiable, and matches the concept's upper-third read (headgear, weapon, roof) |
| Mesh integrity after decimation | 20 | No fused limbs, holes or spikes. Thin parts (braid, staff, sabre) survive. Track C: no candy-wrapping at shoulders, hips or knees in the 4 clips |
| Texture on visible faces | 20 | Painted light kept. Sides seen at ±30° yaw are not dark. Team-colour magenta keys cleanly (`team_face_fraction` > 0) |
| Proportion fidelity | 10 | The 1.3× exaggeration (shoulders, weapon, hat) survives |
| Rig-ability / clip quality | 10 | A-pose with limb gaps (A, B). Track C: foot slide ≤ 0.1 m per stride, hand props aligned |
| Cost per accepted asset | 10 | Price × expected retries |

**Decision rules:**
1. Any score ≤ 2 on silhouette, integrity or texture disqualifies the candidate.
2. Pick the **cheapest candidate within 10 % of the best weighted score**. To compare a CU price with a credit price, use the ratio of
   the two spendable pools, **1 cr ≈ 7 CU** (1,379.6 CU / 208.5 cr). So TRELLIS (14.81 CU ≈ 2.1 cr) is cheaper than H3.1 (9 cr)
   but dearer than SAM 3 (1 cr).
3. If SAM 3 wins track A, re-plan B1–B19 at 1 cr per mesh. The freed credits go first to B12 (the Sootcoat), then to the P1 list
   (B16 `kingdom.caster` is already made, ledger #20).
4. If SAM 3 or TRELLIS wins track B, it becomes the default for every AI building and prop (E5, E6, E16, B18 props).
5. *(Closed by the auto-rigger, §3.2 status.)* If bpy wins track C (or loses by ≤ 10 %), B6, B7, B9 and B12 stay on bpy. Otherwise they move to Higgsfield rigs, paid by the margin
   ladder (§2.15 rung 1), never by the 20 cr reserve.
6. Log the scores, renders and decision as a ledger entry titled "Bake-off R2".

### 3.4 Round 3 (M2, week 1): retarget QA

- Retarget the 9 P0 library clips onto three body types: `kingdom.worker` (1.25 m), `kingdom.infantry` (1.75 m) and `clans.infantry` (2.0 m, broad).
- Measure foot slide, hand-prop drift, and wrist and hip artefacts.
- Any clip that fails on a body type gets either a procedural fix (IK foot lock in bpy, an arm-offset layer) or a P2 Higgsfield native clip on that character.

---

## 4. Milestones (M1–M5)

### 4.0 Calendar and external deadlines (proposal)

| Milestone | Target window | Hard constraint |
|---|---|---|
| M1 Playable loop (graybox) | 17 Oct – 2 Nov | Bake-off overtaken by production (§3.2); `map_lookalike` logged before M4 work starts on the map |
| M2 Art pass | 20 Oct – 14 Nov (overlaps M1) | Month-1 Higgsfield credits spent before the inferred ~15 Nov reset |
| M3 Audio pass | 3 Nov – 28 Nov | Names locked by 3 Nov. All VO generated by **15 Dec** at the latest (voices expire 31 Dec) |
| M4 AI opponent | 17 Nov – 11 Dec | — |
| M5 Polish and release gate | 7 Dec – 23 Dec | — |

**Engineering baseline today:** about 5.8k lines of GDScript.
- **Exists:** sim, pathing, terrain, selection, combat core, HUD skeleton, minimap, fog, day/night.
- **Missing:** economy, production, construction, heroes, abilities, items, creeps, AI, audio playback rules.

### 4.1 M1 — Playable loop (graybox)

**Scope:**
- **Map:** Wether Downs as `data/maps/wether_downs.json`, authored by a script from §1, with the sketch and the authored `creep_route`
  saved alongside.
- **Economy:** gold, lumber, food, upkeep (labels per rules §4.5), construction with both faction verbs as graybox, production queues,
  repair and mend, T1→T2.
- **Multi-builder sites as a cross-faction rule in the slice** (rules §4.3 `max_builders`, `extra_builder_rate`,
  `extra_builder_lumber_per_s`): the kingdom's **Hod Chain** (1 Hodman + up to 2 carriers at +40 % each) and a clans **rope-holder**
  (1 Yurtwright + 1 more holding the guy-ropes at **+30 %**, also 5 lumber per 10 s; it plays the `haul` pose and the felt rises
  faster). With both factions able to speed a site, multi-building is a game rule, not a second inherited kingdom signature, and the
  Levy Horn stays the kingdom's one signature. Clans §4 and rules §4.3 follow-ups (§7); if the clans doc rejects it, the Hod Chain
  leaves the slice instead (one builder for both factions) until the later factions ship.
- **Team colours:** `src/systems/player_state.gd` `COLORS` replaced by the art bible §2.4 set, with the slice lobby rule (§2.6).
- **Research and upgrades:** the slice research and upgrade lines (levels 1–2) with their tier gates (kingdom §8, clans §8).
- **Shops:** the faction shops (Curio Cabinet, Tea Tent) and the Weighstall: buy and sell, per-player stock and restock, the Fair Exchange.
- **Faction signatures:** Take Up the Flail / Levy Horn / Lay Down Flails (kingdom §4); Sound the Gong / Roll the Felt / Unload All /
  All Clear (clans §4.1).
- **Towers:** the Lookout → Gun Tower upgrade and the Bow-Mast.
- **Commands:** the autocast toggle (Herb Poultice, Wind at Your Back, repair and Mend), Attack Ground, rally to a mine or a tree.
- **Heroes:** altar, free first hero and recall item, XP, levels, attributes, the Learn card and the "+" badge, revive at the altar and
  instant revive at the Coaching Inn, inventory. All four slice hero kits function, with placeholder VFX. **Kit rules:**
  - Linden Balm may also target the Wheel Marshal herself, at **50 %** effect (this breaks the classic heal's cannot-target-self quirk);
  - The Wagon Ring is recorded as her **second** functional equivalent (a group save in the resurrection slot), so her kit is at the
    2-of-4 limit with no spare room (kingdom §6.4 follow-up);
  - **any change to a hero kit re-runs the ≤ 2-of-4 audit** and the slot-pattern check (kingdom §6.4, clans §6.2), logged in the ledger.
- **Neutrals:** items and the Weighstall stock; the 16 camps with schedules, guard mode, leash (returning creeps walk home invulnerable
  and arrive at full HP and mana, rules §15.2), seeded drops and bounty; the 5 Gold Seams.
- **World and rules:** day/night, fog and win/lose; **flying units** per rules §12 (air movement layer at 3.5 m, G/A targeting,
  flyer-only collision, idle creeps ignore flyers) for the Crowherd's Crows (B15).
- **Opponent:** a **build-order bot** that plays the faction §10 orders with no tactics, for test games.
- **Art:** the 12 auto-rigged characters and both halls already made (§2.3, §2.6); everything else placeholder.
- **Asset track:** style anchors; the run and shoot clips; audio probes (TTS on both services, Seed multi-variant, a 30 s music clip)
  logged with cost.

**Acceptance criteria:**
1. `map_symmetry`, `map_reachability`, `map_distances` (±5 %), `map_economy_rules`, `map_buildability`, `camp_off_road`,
   `map_sleep_mix`, `inn_unguarded` and `creep_route` all pass (§1.13).
2. `economy_saturation`: 5 workers on a main seam give **9–11 gold/s** over 120 s. A sixth worker adds < 0.5 gold/s.
3. Upkeep: a 10-gold trip yields 10 / 7 / 4 at 50 / 51 / 81 food (unit test). Bounty is taxed; lumber is not.
4. Headless bot-vs-bot, 15 min, for each faction pairing and both seats: no script errors.
   - The determinism hash is identical across two runs with the same seed.
   - The timeline holds: **first hero ≤ 2:05; first camp cleared ≤ 3:15; T2 complete within ±15 s of the faction §10 time (kingdom
     5:55, clans 6:25); hero level 3 ≤ 6:00** (§1.11).
5. Camps sleep and wake on schedule: **the Crow Field by day; the Folds, the Cairn Gate and the Ring never; all other camps at night.**
   The leash returns at 18.75 m; **a pulled camp walks home invulnerable and arrives at full HP and mana** (neutrals §1.4, rules §15.2;
   `test_creep_leash`). Drops are identical for the same seed.
6. A human tester beats the passive bot in under 20 min using only HUD controls: smart right-click, control groups, hotkeys,
   shift-queue (the full list is #12).
7. **Style anchors and the remaining P0 concepts (B12) are approved and squint-tested;** the rendered squint notes for the 12 made
   characters and both halls are in the ledger.
8. **Budget checkpoint:** Higgsfield ≤ 20 cr spent in M1 (run and shoot clips 16, early references and textures ≤ 4). Krea ≤ 130 CU
   (style anchors 54, audio probes ≤ 75). Balances are read live and reconciled with the ledger (ledger #25 corrects the derived balances
   in §2.15).
9. **Worker defence** (unit tests): the Levy Horn arms every Hodman within 22 m of the hall's edge in 1.5 s; a Levy more than 30 m
   from every hall's edge lays down its flail after 5 s; a Home Yurt holding 3 Yurtwrights fires 3 sling attacks; Lay Down Flails and
   All Clear return every worker to its previous job with its cargo kept. Multi-builder sites: 1 / 1.4 / 1.8 × for the Hod Chain and
   1 / 1.3 × for the rope-holder, each helper paying 5 lumber per 10 s.
10. **`map_lookalike`:** a reviewer compares the §1.3 sketch and an overhead render (view-only, §2.16 comparison rule) with the overview
    images of **every 2-player melee map on Liquipedia's map pages for the classic game**: the classic and expansion ladder pools, the remastered
    pools and the W3Champions 1v1 pools (the ip-safety §2.1 Maps row is not exhaustive and lacks current-era maps). The ledger records the
    URL list and the verdict. The reviewer checks this map's **specific arrangement**: a merchant in a central basin, a health spring on
    one flank and the red camp on the opposite flank, an inn on the axis, SW/NE starts with one ramp and a guarded natural below it. If
    something matches, move landmarks; do not just retouch art.
11. **IP number and name gate** (before and after kit data entry):
    1. `python3 tools/ip/check_banned_terms.py` (its default paths include `data/`) and `python3 tools/ip/check_value_echo.py` both
       **exit 0**. The value check fails today only on the engine's team colours (§2.6), which this milestone replaces.
    2. **Before** kit and unit data are entered, `tools/ip/value_echo_reference.json` gains **kingdom rows** (it has 264 entries for
       clans, sylvan, deathless and items, and none for the kingdom): the Wheel Marshal against the classic armoured holy hero, the
       Firewright against the classic fire mage hero, and the Pavisier, Hookgunner, Linden Sister and Bombard Wagon against their classic
       role units (cost, time, HP, damage, cooldown, range, mana and per-rank ability values). The kingdom §6.4 test
       (`tests/unit/test_number_fingerprints.gd` with `docs/research/reference-ability-numbers.csv`) is the alternative; one of the two
       must exist before the kingdom data does.
    3. **Policy: a functional equivalent differs by at least 20 % at every rank** from the classic value it mirrors (|ours − ref| ≥
       0.20 × ref) in mana, cooldown, duration, fade time and every per-rank value; exact inequality is not enough, because a tuning
       pass can drift back onto a classic value. `check_value_echo.py` gains a `min_rel_diff` of 0.20 for entries marked as functional
       equivalents. Known failures to fix at data entry: the Uncut's Dust Veil (bonus +45 / 80 / 115 against 40 / 70 / 100; mana 70
       against 75; fade 0.5 s against 0.6 s; e.g. bonus **60 / 100 / 140**, mana **55**, fade **0.35 s**), Keen Edge's rank-1 multiplier
       (1.8× against 2×; e.g. 20 % chance, 1.6× / 2.3× / 3.0×), the Hail-Swifts cooldown (35 s against 30 s), and whatever the new
       kingdom rows flag (the Wheel Marshal's Linden Balm heal per rank is the first suspect).
    4. The ≤ 2-of-4 hero audit and slot-pattern check pass for all four slice kits after any kit change (scope above).
12. **`controls_parity`** (UI tests driven by `Input.parse_input_event`): Tab / Shift+Tab cycle subgroups; double-click and Ctrl+click
    select all of a type on screen; Ctrl+N sets, Shift+N adds, N selects and a double-tap of N centres a control group; F1–F3 select
    heroes (double-tap centres); F8 and ` select an idle worker; Space jumps to the last alert; Backspace cycles halls; Alt shows health
    bars; numpad 7 / 8 / 4 / 5 / 1 / 2 use items; right-click on an ability toggles autocast; A-click attack-moves; right-click on the
    minimap orders; Shift+train queues 5; shift-queue holds up to 32 orders.
13. **`test_flying_layer`:** a Crow flies over cliffs and trees at 3.5 m; melee units cannot hit it, the Hookgunner and the Javelineer
    can; idle creeps do not acquire flyers, a fighting camp's ranged creeps do; flyers separate only from flyers.

### 4.2 M2 — Art pass

**Scope:**
- Every P0 row of §2.3–§2.11 imported: characters rigged with clips merged, procedural creeps, siege, buildings and kits, terrain array, cliff, trees and doodads, neutral structures.
- VFX sheets, UI kit, icons and live portraits.
- Retarget QA (§3.4).

**Acceptance criteria:**
1. Every P0 asset has a complete ledger entry (§2.16) and passes `check_banned_terms.py`. Each P0 3D asset has a contact sheet on file.
2. **Readability** at 1080p, default zoom (25.8 m):
   - infantry ≥ 40 px tall, heroes ≥ 50 px;
   - a blind tester tells apart the 64 px black silhouettes of these 16 with ≥ 90 % accuracy: the 6 kingdom units (Hodman, Flail
     Levy, Pavisier, Hookgunner, Linden Sister, Bombard Wagon), the 5 clans units (Yurtwright, Grappler, Javelineer, Gustcaller,
     Sling-Cart), the 4 heroes (Wheel Marshal, Firewright, the Uncut, Skymirror) and the Sootcoat;
   - workers, infantry and ranged of the two factions are never confused at a glance;
   - when the P1 roster lands (§2.3), the test re-runs with **18** silhouettes (+ Lacewright, Pole-Carver) and then 21 (+ Flail Hetman,
     Omen-Mother, Rat-Piper);
   - **squint tests against the classic siege engines:** the Sling-Cart (D2) against the classic warrior race's catapult (it must read
     as a traction sling with a hanging felt sling and a low hooded lattice cart, §2.5 art rules), and the Bombard Wagon (D1) against
     the classic human artillery.
3. Team colour reads on every unit and building, day and night, for all 12 colours of the **art bible §2.4 set** (not the engine's
   old list; colour-blind simulation included). Every M2 capture uses the §2.6 slice defaults: kingdom Emerald, clans Royal Blue.
4. Each unit plays idle, locomotion, attack, death (and work or cast) with stride-matched playback: foot slide ≤ 0.1 m per stride at sim speed. The attack damage frame lines up with the sim damage point within 1 tick. The Wheel Marshal attacks one-handed with the shield forward (§2.4).
5. **Performance:**
   - 200 animated units on the full map at ≥ 60 fps (Forward+, reference GPU);
   - ≥ 30 fps on the Compatibility renderer;
   - frame times logged by a playtest script.
6. The distinctness rubric is re-run on the *rendered* faction units (≥ 4 of 6 axes plus silhouette, ip-safety §3.2), in the default
   slice colours, and the HUD squint test (§2.16 step 2b, including the clans inlay's teal-saffron-bronze read) is run on an in-game
   screenshot. The look-alike notes and the HUD result are in the ledger.
7. **Budget:** Higgsfield spend from 17 Oct ≤ 57.5 cr (remaining P0 45.0 plus margin-ladder rungs, all logged); the 20 cr reserve is
   untouched until the pre-reset release. Any credit still unspent 3 days before the reset goes on rung 6 items rather than being lost.

### 4.3 M3 — Audio pass

**Scope:**
- VO P0 (251 lines), plus P1 if the probes allow (Warcry first).
- SFX P0 (54 jobs); ambience day and night beds; music P0.
- Audio runtime: pooled 3D players, per-id caps, buses and ducking, the ack rules (2D, one at a time, 0.25 s debounce), annoyed lines in sequence after 4 clicks in 3 s.

**Acceptance criteria:**
1. Every P0 speaker responds on select, order and attack. Annoyed runs play in order. Heroes bark on ability orders, with a 30 % repeat chance inside 20 s.
2. Every recorded line has passed the IP line check and the §2.12 VO lint (log entry), every VO id and file name passes
   `check_banned_terms.py` (the worker completion files are `*_built_*`), and **every P0 stinger and music piece (S17, S27, S35, S41, S43,
   MU1–MU5) has a logged ear-test verdict** (§2.16 step 2c). Raw takes are archived in `assets_src/audio/`, and **all VO generation is
   finished by 15 Dec**.
3. 10-minute capture:
   - integrated −20 to −24 LUFS;
   - peaks ≤ −1 dBFS;
   - no sound id has more than 4 instances;
   - a 40-unit fight stays ≤ 10 combat voices plus the battle bed.
4. Melee impacts follow the swing × material matrix. Ambience crossfades over 8 s at dawn and dusk. Music rotates with 20–40 s gaps and never switches for battle.
5. **Budget:** Krea audio P0 ≤ 957 CU (SFX 378, VO 379, music 200), with probe results recorded. The P1 audio list is fixed
   against the remaining 294 CU cap (§2.15).

### 4.4 M4 — AI opponent

**Scope:** the rules §19 AI at Easy, Normal and Hard for each faction.
- Faction build orders (kingdom §10, clans §10).
- A **creep-route planner for Wether Downs** that follows the map's authored `creep_route` (§1.8), respects sleep schedules, guard mode
  and the Stuffed/Pierce resistance (neutrals Q4), and skips a camp the fight estimate says is lost.
  - **Contested-camp branch** (the Cairn Gate, the Crow Field and the Den): if the shared camp is seen cleared, or an enemy hero was
    seen within 40 m of it in the last 20 s, the **creep-jack trigger** applies: fight there when own army food ≥ the seen enemy army
    food and own hero level ≥ the enemy hero's; otherwise take the route's fallback leg (the next own-side camp, or the faction shop).
  - **Hero 1 from 7:00 to 8:30** (when the Crow Field is taken or lost): shop at the faction shop, then hold at the natural or scout the
    enemy's Charcoal Yard approach, staying more than 18.75 m from its own hero 2 so it does not split hero 2's XP.
- Hero skill builds and item use (potions, recall, power-ups, picking up drops); the worker-defence trigger (rules §19).
- Expansion to the natural after clearing the Fold; a **late-game expansion** to the Ring Gold Seam after the Ring is cleared, at
  ≈ 14:00 or when its main seam is under 3,000 gold.
- For the P1 roster: the Lacewright and Pole-Carver in each faction's T2 mix, the third hero at T3 (or the Rat-Piper hired at the inn).
- Retreat below 35 % hero HP. **Attack trigger = the faction script's push row** (kingdom §10 at 8:30–9:30; clans §10 at 36 army
  food, Upkeep 0 %). **≥ 40 army food is the generic fallback** (rules §19), and an enemy hero seen creeping within 31 m always triggers.

**Acceptance criteria:**
1. Normal AI (either faction) beats a passive opponent by 14:00 in 10 of 10 seeds. Normal beats Easy ≥ 80 %. Hard beats Normal ≥ 70 % over 20 seeds.
2. **Seat fairness:** a Normal vs Normal mirror (same faction), 40 seeds: each seat wins 40–60 %. This is the map's chirality check (§1.2).
3. **Faction balance:** `kingdom` vs `clans`, Normal vs Normal, 40 seeds split across seats: each faction wins 40–60 %.
4. Median game length 12–20 min; fewer than 5 % of games exceed 30 min.
5. **Watchdog:** no unit with an order stays stuck for more than 30 s, and no AI worker idles for more than 20 s in the first 10 min.
6. **Creeping discipline:** greens first; the own Drystone Fold at hero level ≥ 2 with ≥ 4 combat units; other ambers per rules §19
   Normal (skip camps above the army's total level × 1.2); the red camp only with **hero 1 at level ≥ 4, hero 2 at level ≥ 3 and ≥ 30
   army food** (neutrals §3.6: both heroes at level 4 cannot happen before the Ring on this map); never start a camp the fight estimate
   says is lost.
7. **Second hero, per faction:** each faction's hero 2 reaches level 3 by 10:00 in ≥ 50 % of **its** Normal games (kills of enemy
   units included), measured in the faction-balance set (#3), where the kingdom usually reaches the Den first. `creep_route_mirror`
   (§1.13) passes.
8. **Late game** (only once E17 and at least one third-hero option, B19 or B24 / B25, are in; otherwise dropped): ≥ 30 % of games
   longer than 14 min reach T3, and those that do field a third hero.
9. **Items, shop and revive** (20 Normal seeds per faction): the hero picks up **≥ 95 %** of creep drops within 30 s of the carrier's
   death and uses power-ups at once; buys **≥ 1 heal item by 6:00**; queues a revive within **5 s** of being able to afford it;
   follows the rules §19 recall rule (Hard saves its army with it); in a scripted 6-food worker raid, sounds the Levy Horn or the Gong
   within its difficulty's reaction delay + 1 s; with a full inventory, sells or drops its lowest-value item to pick up a better drop.

### 4.5 M5 — Polish and release gate

**Scope:**
- Juice P0 rows from the four juice docs.
- Front end: main menu; skirmish setup (faction, colour with the §2.6 lobby rule as the default, AI difficulty); options (volumes, ack and annoyed toggles, hotkeys); pause; victory and defeat screens with stats; tooltips everywhere.
- Every playtest, capture and the look-alike review use the default slice colours (kingdom Emerald, clans Royal Blue).
- P1 assets as the budget allows; bug bash.
- Rehearse the ip-safety §5.3 release gate; write `CREDITS.md`; export builds.

**Acceptance criteria:**
1. **Playtest:** 3 external testers play 3 games each; one of them is a long-time player of classic hero-RTS games.
   - **Fidelity checklist**, 12 yes/no items answered by each tester after each game:
     1. The hero was out and creeping by about 2:00.
     2. Creep XP stopped mattering at hero level 5.
     3. The upkeep step was felt at 51 food.
     4. Creeps were asleep at night, and attacking a sleeping camp got the first hit.
     5. A recall saved an army.
     6. Creep drops were worth fighting for.
     7. The Levy Horn or the felt garrison repelled a worker rush (or would have).
     8. There was a shop run in the centre.
     9. An inn revive was used or considered.
     10. Night changed how I scouted.
     11. The click-spam (annoyed) lines landed.
     12. My control habits worked: A-click, F1, Tab, F8, numpad items.

     **Pass:** the veteran answers yes to ≥ 10 of 12 (averaged over their games), and no single item is failed by 2 of the 3 testers.
     Each "no" becomes a tracked fix with the item number.
   - Average "feels like the classic hero-RTS loop" score ≥ 4/5 (kept as a summary, not the gate).
   - The look-alike review finds **zero** items that read as a specific copied unit, building, icon, UI piece, line or map, or every one found is fixed.
2. Zero crashes in 20 consecutive full games (17 headless AI vs AI, 3 rendered with a human).
3. The juice P0 verification tables (in each juice doc) pass.
4. The ledger and `CREDITS.md` are complete: every shipped asset has provenance and plan tier, and fonts and any CC0 items are licensed.
5. Final balances on both services are recorded. Reserves are either untouched or released with a written reason.

---

## 5. Risks and decision gates

| Risk | Likelihood / impact | Mitigation and gate |
|---|---|---|
| Higgsfield credits reset monthly (inferred) and unspent ones are lost | High / high | Spend P0 3D in M1–M2 (by about 14 Nov). Confirm on the plan page in M1 |
| TTS or music cost much more than planned | Medium / high | Probe in M1 on both services. Cut P1 VO, then P1 music. Keep the P0 annoyed lines |
| Default voices expire 31 Dec | Certain / high | Lock names by 3 Nov; finish VO by 15 Dec; archive the raw takes |
| H3.1 loses thin parts (braid, staff, sabre) | Medium / medium | Bake-off track A. Generate weapons as separate bpy props attached to hand bones |
| The free auto-rigger deforms badly on a body type | Medium / medium | §3.4 retarget QA; the three `--force` fits were checked by eye (commit 2bb913d). Fallback: Higgsfield `3d_rigging` + clip at 8 cr per unit, paid from the §2.15 margin, never the reserve |
| Retargeted clips slide or misalign props on very different bodies | Medium / medium | §3.4 QA; IK foot lock; P2 native clips |
| Krea purchased packs expire after 90 days | Unknown / high | Check the purchase date in M1. Front-load Krea audio if the expiry falls before Jan |
| Map chirality under the fixed camera favours one seat | Low / medium | M4 seat-fairness test. If it fails, swap the ramp facings (both players), not the layout |
| Hall footprint (5 m vs 8 m) undecided | Certain / low | 8 m pads reserved; the map script derives each hall centre from `hall_footprint_m` so the seam gap is 6.0 m for either (§1.2); `map_economy_rules` runs both |
| Contested shared camps leave heroes under-levelled at the push | Medium / medium | Planned for (§1.11 contested rows); `creep_route_mirror` and per-faction M4 #7 measure it; fallback: the §1.14 #8 amber pair (0 new assets) |
| The clans doc rejects the rope-holder | Low / low | Drop the Hod Chain from the slice instead, so neither faction multi-builds (§4.1) |
| Look-alike risk from the AI outputs | Medium / high | Squint test per asset; rubric re-run at M2; release gate at M5 |
| "Game pipeline only" Higgsfield audio models have unclear terms | Unknown / medium | Do not ship their output until the terms are read and logged |

---

## 6. Open questions

1. Higgsfield: confirm the renewal date, whether unused credits are wiped, the commercial-use terms of the `starter` tier, and current prices for rig-only (5?), SAM 3 (1?), Tripo P2 and Meshy 7.
2. Krea: purchase date and expiry of the 1,529.6 CU; the per-request price of TTS and Music.
3. Which ElevenLabs terms govern output generated through Krea or Higgsfield (ip-safety §6).
4. The final hall footprint (kingdom §13 Q1). Does `CLIFF_H` change to 2.0 m (README §8)?
5. Whether `gpt_image_2_5` on Higgsfield honours image references well enough for icon-sheet consistency. If not, icons move to Krea 2 Medium at 9 CU per sheet (about 340 CU), which displaces P1 audio.
6. Map name "Wether Downs" and the tileset's player-facing name "Downland" (§1.12) are working titles. Run the usual name check on both
   before names lock on 3 Nov; "Downland" is also the title of a 1983 home-computer game.
7. Do the own-side camps feel too far for hero 2 (Collier's Hut 78 m, Charcoal Yard 104 m of path, §1.14 #6)? Watch the per-faction
   M4 hero-2 metric (§4.4 #7). If only the walk is the problem, move the Yard closer by thinning the TW1 wall; if the XP total is the
   problem (contested Den), add the §1.14 #8 amber pair.
8. Is the next Higgsfield grant real and on time (≈ 16 Nov)? The P1 roster (§2.3: second casters, third heroes, the Rat-Piper) and
   its VO depend on it, and the VO must be done by 15 Dec.

---

## 7. Required follow-up edits in sibling docs

| Doc | Edit |
|---|---|
| `neutrals.md` §3.3, §3.6, §5.5 | Cite this map's spots (§1.4): Woodward's Rest (95, 143), Collier's Hut (73, 111), Charcoal Yard (117, 175), Dewstone site (124, 178), Cairn Gate (66, 66), Weighstall and Den (92, 92), Coaching Inn (128, 128). The own-side path bands become "this map: 73.9 / 78.1 / 103.5 m" (§1.14 #6–#7) |
| `juice/ui-camera-audio.md` HUD-07 | Replace the round top-centre clocks with the Horizon Ribbon (art bible §7.5). Move the lit frame, the golden-hour rim and the day tally onto the Ribbon and its end caps (§2.9 I5) |
| `juice/heroes-abilities-vfx.md` and `factions/kingdom.md` §6.3 (Brace the Wheel) | The wheel-rim ring rolls out from the planted shield rim. No dust-burst shockwave and no camera shake at a strike, so it never reads as a ground slam (§2.4). **Rename "wheel-rim shockwave" to "wheel-rim ring"** in kingdom §6.3 and the heroes juice; the fx id is `fx_wheel_rim_ring` (the old wording would ship a banned classic ability name as an id) |
| `factions/kingdom.md` §3.2, §3.3 | The Bombard Wagon has one speaker (the Elder; the Younger is non-verbal), about 14 lines; use the §2.12 P0 lines, 4 Annoyed (the old "barrel you're tapping" line is retired) |
| `factions/kingdom.md` §4, §5 | Take Up the Flail (22 m) and the Levy leash (30 m) are measured **edge to edge from the hall footprint** (§1.6). The role word in every id is "levy" (`kingdom_flail_levy`, clip `arm_levy`, icon `kingdom_flail_levy_{128,64}.png`); prose like "town-militia" in prompts may stay |
| `factions/kingdom.md` §6.3, §6.4, §13 Q10 | Linden Balm may target the Marshal herself at 50 % effect (Q10's fallback becomes the default). The Wagon Ring becomes her **second** functional equivalent (§6.4 count 2). Its VFX is the art bible's physical painted wagon boards (`K_WAGON`), not "a ghostly ring"; no golden dome, halo, bubble or light pillar on either ability |
| `factions/kingdom.md` §8, §9, §11 | T3 parity: **Burgher's Oath** at the Drill Yard (Sworn Pavisier, §2.6 E17; numbers proposed, kingdom owns them). Bow Saws stays T2 (110 g). The Lacewright and the Flail Hetman move from *later* to the P1 slice roster (§2.3) |
| `factions/clans.md` §3.3 | (1) Rename the "Job done" row to **"Built"** (id `built`). (2) **Sling-Cart:** the two brothers speak **in unison** (§2.12 lines); no split lines or punchlines, and "Ready to throw—" goes. (3) Lines that "tap" (Yurtwright Annoyed) say "click" instead (VO lint, §2.12) |
| `factions/clans.md` §4, `rules.md` §4.3 | Clans **rope-holder**: `max_builders` 2, `extra_builder_rate` 0.3, `extra_builder_lumber_per_s` 0.5, presented as a second Yurtwright hauling the guy-ropes (`haul`). If rejected, the Hod Chain leaves the slice (§4.1) |
| `factions/clans.md` §5–§6 | Numbers per the 20 % policy (M1 #11): Dust Veil (e.g. bonus 60 / 100 / 140, mana 55, fade 0.35 s), Keen Edge (e.g. 20 %, 1.6× / 2.3× / 3.0×), Hail-Swifts cooldown (≥ 36 s or ≤ 24 s). The Pole-Carver and the Omen-Mother move to the P1 slice roster (§2.3) |
| `art-and-audio-bible.md` §8.1, §8.2 table, §13 #16, review #23; `juice/ui-camera-audio.md` AUD-03; `juice/economy-and-buildings.md` (BLD-09, the audio table, the IP note); `factions/clans.md` §3.3; `tests/output/probe_relabel.gd` | **The art bible currently says the opposite of this plan:** its review #23 renamed `built` to `job_done`, and the others follow it. **This plan wins for slice VO** (§2.12): rename the id back to `built` and the label to "Built" everywhere listed, and reword the debug print ("[relabel] finished after %d ticks"). **Then** add `job done`, `job_done` and `job-done` to `tools/ip/banned_terms.txt` and re-run the default check, **before names lock on 3 Nov**. Adding them first fails the check on the art bible |
| `art-and-audio-bible.md` §8 (Hodman, Yurtwright) and §8.1 lint | The Hodman's Annoyed 1–2 and voice note ("bills the player by the tap") and the Yurtwright's Annoyed 1–4 ("One tap is a greeting" …) use the clicking-as-touch premise: say "click" ("That's a click. I'm writing it down."; "One click is a greeting."). Extend the §8.1 lint from poke / poked / poking to **tap, tapped, tapping, prod and jab**, and add "no Ready line starts with 'Ready to'" and the no-split-crew rule (§2.12) |
| `tools/ip/banned_terms.txt` | **Add now** (none hits the default scan paths, checked 2026-10-19): `m'lord`, `right-o`, `ready for action`, `more work`, `not that kind of orc`, `your hero has fallen`, `free company`, `shockwave`, `banish`, `metamorphosis`, `tranquility`, `paladin`, `khaz modan`, `mortar combat`, `hammerfall`, `shallow grave`, `gloom stalker`. **Add after the renames:** `milord` (first reword the art bible §8.1 lint sentence that lists it as an address word), `crowcaller` and `smoker` (art bible §9 SFX rows; retired-names block), `job done` / `job_done` / `job-done` (row above) |
| `art-and-audio-bible.md` §2.4 | Checked 2026-10-19: the lobby rule and the marketing rule already give the kingdom Emerald and the clans Royal Blue, never the kingdom blue or gold and never the clans Crimson or Violet. Remaining: move **Coral Rose** from the clans' preferred list to their trade-dress skip set, and name Cornflower as the clans' fallback in the marketing rule (§2.6) |
| `art-and-audio-bible.md` §7.2 (clans inlay row and its T11 `UI_CLAUSE`) | Red-brown lattice-wood (`#5C3826`) → **ochre-washed lattice** (`#B7772A`, highlight `#C9A46A`); add "red-brown never appears on UI art" (§2.9 I3) |
| `src/systems/player_state.gd` | Replace `COLORS` (the reference game's colours in near-reference order) with the art bible §2.4 set and implement the lobby rule (M1; §2.6) |
| `tools/ip/value_echo_reference.json`, `tools/ip/check_value_echo.py` | Kingdom rows before kit data entry; a `min_rel_diff` of 0.20 for entries marked as functional equivalents (M1 #11) |
| `neutrals.md` §3, §8, §10, camp rows; art bible creep and SFX rows | **Crowcaller → Crowherd** (`creep_harvest_crowherd`), **Smoker → Coal-Lobber** (`creep_sootcoat_coal_lobber`; Smoke Pot stays its ability); S18 / S19 ids and the `cr_ember_rake`, `cr_heal_tar` and `atk_herb_mote` notes. Then the old names join the retired block of `banned_terms.txt`. The Crow is a flyer (rules §12) unless M1 cuts the layer (B15) |
| `neutrals.md` §1.4 | The "Status" line is stale: rules §15.2 already has the invulnerable return with a full heal (checked 2026-10-19). Mark the blocking follow-up resolved; `test_creep_leash` is in M1 #5 |
| `neutrals.md` §3.6, §5.5, §5.6.3 | The map's third Gold Seam inside the Standing Ring, with the Ring in guard mode (§1.4 RS); Rat-Piper hiring is P1 with E17 and its concept-review rules (B19) |
| `rules.md` §19 | Hard's red-camp trigger: hero 1 at level 4+, hero 2 at level 3+, ≥ 30 army food (§4.4 #6; neutrals §11 lists the same edit). The contested-camp branch and the late-game expansion step (§4.4) |
| `tools/build_slice_units.sh` | `kingdom_wheel_marshal`: `attack=$SWORD` plus the `shield_fwd` layer, not `$HEAVY` (§2.4) |
| `art-and-audio-bible.md` §7.8 (minimap glyphs) | Free Company Camp → Hiring Fair (the neutrals rename). The Gold Seam prompt row (§4.4) was updated in this change |
| `docs/asset-ledger.md` | #25: live balance readings on both services, to replace the derived balances in §2.15 |
| Every doc that shows the tileset to players | Player-facing name "Downland"; the internal id is `gv`, and "greenvale" never appears in a shipped filename, data string or asset id (§1.12) |

---

## Appendix A. Role → working names in today's faction docs (the synthesis step may change them)

| Role | `kingdom` (kingdom.md) | `clans` (clans.md) |
|---|---|---|
| worker | Hodman (+ Flail Levy form) | Yurtwright |
| infantry | Pavisier | Grappler |
| ranged | Hookgunner | Javelineer |
| caster | Linden Sister `[SLICE]` (P0) | Gustcaller |
| caster2 (P1, next grant) | Lacewright | Pole-Carver |
| siege | Bombard Wagon | Sling-Cart |
| hero1 (fixed kit; either kit may be trained first) | Wheel Marshal (STR) | the Uncut (AGI) |
| hero2 (fixed kit) | Firewright (INT) | Skymirror (INT) |
| hero3 (P1, next grant) | Flail Hetman (STR) | Omen-Mother (INT) |
| neutral hero (P1, inn) | Rat-Piper (AGI) | Rat-Piper (AGI) |
| T3 unit upgrade (P1) | Burgher's Oath → Sworn Pavisier | Proving Rite → Proven Javelineer |
| hall T1 → T2 (→ T3, P1 data tier) | Moot Hall → Walled Burg (→ Crown Burg) | Shell Hall → Banner Shell (→ Sun-Gong Shell) |
| farm / supply | Croft | Home Yurt |
| altar | Oath Hall | Naming Stones |
| barracks | Drill Yard | Grapple Yard |
| lumber drop-off | Timber Yard (also the tower gate) | Casting Pit |
| blacksmith | Foundry | Casting Pit |
| workshop | Wainwright Yard | — (siege comes from the barracks) |
| caster building | Collegium (P0) | Mirror Yurt |
| faction shop | Curio Cabinet | Tea Tent |
| tower | Lookout → Gun Tower | Bow-Mast |
| worker defence (the one inherited signature mechanic) | Take Up the Flail / Levy Horn / Lay Down Flails (role id `levy`) | Roll the Felt / Sound the Gong / Unload All / All Clear |
| multi-builder sites (a cross-faction game rule in the slice, not a signature) | Hod Chain: 1 Hodman + up to 2 carriers, +40 % each | Rope-holder: 1 Yurtwright + 1, +30 % |
| advisor | the Reeve | the gong-keeper |

## Appendix B. Higgsfield animation catalogue ids referenced above

Preview each GIF before choosing; names are renamed on import.

| Id | Name | Use |
|---|---|---|
| 0 | Idle | idle (owned) |
| 8 | Dead | death (owned) |
| 30 | Casual_Walk | walk (owned) |
| 219 | Right_Hand_Sword_Slash | attack_1h (owned); also the Wheel Marshal's one-handed pick chop at 0.85× with `shield_fwd` |
| 128 | Heavy_Hammer_Swing | attack_heavy (owned, ledger #17): `clans.infantry` and the workers' chop only. **Never on `kingdom.hero1`** |
| 129 | mage_soell_cast (catalogue spelling) | cast (owned, ledger #16) |
| 421 | Over_Shoulder_Throw | attack_throw (owned, ledger #18; alternates 239, 398) |
| 14 | Run_02 | run, to buy (alternates: 16 RunFast, 510 Standard_Forward_Charge) |
| 104 | Side_Shot | attack_shoot, to buy (alternates: 232, 98) |
| 125 | Charged_Spell_Cast | cast alternate (129 is owned) |
| 237 | Charged_Axe_Chop | work_chop (P1) |
| 261 | Push_and_Walk_Forward | P2 top-up |
| 268 | Sit_and_Doze_Off | P2 top-up |
| 59 | Victory_Cheer | P2 top-up |
| 119 | Heavy lumbering walk | P2 top-up (`clans.infantry`) |
| 127 | Charged_Ground_Slam | **Cut. Never used:** a ground slam on the armoured support hero rebuilds the classic stomp presentation (kingdom §2.6) |
| 238 | Axe_Spin_Attack | **Cut. Never used:** no spinning or circular motion on any hero (clans §2.5) |

---

## Review log (2026-10-17: IP-safety and fidelity reviews of revision 2)

Where IP and fidelity conflicted, IP won and the closest legal alternative was taken. Severity as given by the reviewers. Two items
(#31, #32) were found while making the fixes.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | The S21 spell-school name sat next to a banned mark and failed `check_banned_terms.py` | S21 is **Blossom** (`blossom`, heroes juice §5). The doc passes the checker |
| 2 | Major | Three names retired by the neutrals IP review (the scarecrow family, the inn, the mana font) were still in use | B13 and S19 → **Tattiebogles**, with the neutrals §10.2 art rules in B13; the inn → **Coaching Inn** (`neutral_coaching_inn`, sign *The Muddy Lantern*) in the legend, §1.4, §1.9 and E16; the mana landmark → **Dewstone**; the mercenary camp → Hiring Fair. The art bible already used the new names; `banned_terms.txt` gains a "retired neutral names" block (the three old names with spelling variants, the retired brute and the retired booklet names) |
| 3 | Major | The Wheel Marshal attacked with the two-handed hammer swing (128), had a ground "slam" and a slam top-up (127): with Brace the Wheel's ring, the classic armoured hammer hero's swing and stomp | Attack = 219 at 0.85× plus a new additive `shield_fwd` layer; 128 stays owned but plays only on `clans.infantry` and as the workers' chop; "slam" → **shield_plant** (fallback idle plus a crouch hold); 127 cut from §2.4, §2.15 and Appendix B; B4 and B21 get the pick-head rule (≤ 0.35 × haft, curved beak); build-script and heroes-juice follow-ups (§7) |
| 4 | Major | E15 modelled the retired booklet trio plus the XP diary | E15 and the power-up icons use the neutrals §4.3 objects. The reviewer kept the almanac as the one book; neutrals has since replaced it with the Fair-Day Rosette ("no item is a book"), so the rosette is used |
| 5 | Major | No similarity check for HUD art or audio | §2.16 steps 2b (HUD squint) and 2c (ear test on S17, S27, S35, S41, S43, MU1–MU5); M2 #6 and M3 #2 extended |
| 6 | Minor | The Gold Seam kept an ore-cart stub and lacked the strata, spoil heap and sluice | E11 rewritten per neutrals §5.2 and §10.2; the art bible's prompt row edited the same way |
| 7 | Minor | The Bombard crew's two-voice bickering copied the classic artillery crew's character choice | `kingdom.siege` has one speaker; 6 P0 solo lines written; full set ≈ 14. The double act stays only on `clans.siege`. Kingdom follow-up (§7) |
| 8 | Minor | The worker's category label echoed a banned catch-phrase and could leak into VO file names | Category `built` (kingdom §3.2); clans follow-up (§7). The label's spellings are **not yet** in `banned_terms.txt`: the art bible §8, juice AUD-03 and the economy juice still use the label as their category id, and a debug print in `tests/output/probe_relabel.gd` uses it, so adding them now fails the default check. §7 orders the renames first, then the ban (with the underscore form for ids inside text) |
| 9 | Minor | Appendix B still offered the spin clip as a top-up | Row marked **Cut** |
| 10 | Minor | No rule for where comparison images may live | §2.16 comparison-material rule (public pages only; never in the repo, `assets_src/`, Krea styles or moodboards, or the Higgsfield library; the ledger keeps the verdict and the URL) |
| 11 | Minor | The map's only look-alike check came at M5 | M1 acceptance #10 `map_lookalike` against the ip-safety §2.1 ladder maps; on a match, move landmarks |
| 12 | Minor | "no tusks" in a positive prompt can pull the feature in | §2.3 clans jaw rule (positive jaw text, negative field, "mouth closed, no teeth showing" fallback, reject at the squint test) |
| 13 | Minor | "Greenvale" is a one-word swap of a banned tileset name in the same role | Decision (§1.12): `greenvale` / `gv_` stays the internal id; players see **Downland**; §6 Q6 name check |
| 14 | Minor | Per-faction console sheets risked the race-skinned slab; I3 said "lacquered" | I2 and I3 are inlay sheets over the art bible §7.2 shared chassis, with the "never" list; I3 is felt over red-brown lattice-wood |
| 15 | Blocker | The slice roster did not match kingdom and clans §7 and §11 | B16 and E3 → P0 (B16 was already made, ledger #19–#20); E2 adds the Timber Yard and the Curio Cabinet (8 buildings); E7 adds the Tea Tent; §2.10 recounted (kingdom units 6, buildings 10, 14 researches in 10 icons, worker defence 3; clans buildings 8; items 46); the P1 caster row deleted; Linden Sister P0 in §2.12 (12 lines); Appendix A splits lumber and blacksmith and adds the shop and worker-defence rows; budget in #32 |
| 16 | Blocker | The map predated the neutrals revision: camp list, sleep mix, XP route | §1 rebuilt on neutrals' current templates. Neutrals round 2 has since gone past the reviewer's 11-camp list, so the map carries **16 camps** (8 / 7 / 1; 175 levels, 3,815 raw XP, ≈ 984 g): Turnip Patch green 8 at night; Collier's Hut, Woodward's Rest and Charcoal Yard per side; the shared Cairn Gate. Sites come from a layout search (§1.4, §1.14 #6); the plateau-corner option was dropped because neutrals now wants the Hut beyond the Clamp by path. Sleep mix 11 / 4 / 1 (69 %) with test `map_sleep_mix`; goal 4, goal 9, M1 #5 and the authored `creep_route`; new camp props in E14 |
| 17 | Major | The opening times were impossible (first hero ≤ 1:30) | §1.11 rewritten (altar 1:00–1:05, hero out 1:50–2:00, Clamp 2:10–3:10, Patch 3:10–4:20, Woodward's Rest ≈ 4:45, Fold and level 3 4:50–5:45); M1 #4 per the reviewer |
| 18 | Major | The inn's nearest corner stood 4.2 m from a Den creep, and the inn was P2 | Coaching Inn P0, revive only, at **(128, 128)** (neutrals' (124, 124) left 1.5 m to the K2 cliff base); test `inn_unguarded` (nearest camp member 30.7 m); §1.4 S row describes the corner layout; neutrals follow-up |
| 19 | Major | M1 left out systems the faction openings need | M1 scope adds research, shops, the faction signatures, towers, autocast, repair, the Learn card, inn revive and rally to a mine or tree; criterion 9. The reviewer's name for the hall release command is now banned (rules review), so the faction docs' **Lay Down Flails** and **All Clear** are used |
| 20 | Major | The M4 creeping rules contradicted the other docs | Criterion 6 rewritten. The red trigger follows neutrals §3.6 (hero 1 ≥ 4, hero 2 ≥ 3, ≥ 30 army food), not the reviewer's "both ≥ 4", which this map's route cannot reach before the Ring. Attack trigger = the faction push row; 40 army food is the fallback |
| 21 | Major | No T3, so nothing to tech into after about 10 min | E17 (P1): the T3 data tier on bpy hall add-ons, 7 icons; M4 #8 |
| 22 | Major | Hero 2 had no creep XP after T2 | Neutrals' Charcoal Yard (amber 14) per side and the shared Cairn Gate replace the proposed amber pair; both are `[SLICE]` in neutrals with 0 new creep assets, so they are P0 here; M4 #7 |
| 23 | Minor | `camp_off_road` (6 m) was looser than the camps' acquire ranges | Threshold max(12 m, layout radius + 1.5 × acquire), exempting only the lane routed through a camp's own landmark; every camp is ≥ 13 m off the lanes |
| 24 | Minor | Details lagged the neutrals revision | Covered by #2, #4 and #6; §1.14 notes 1–2 marked resolved |
| 25 | Minor | HUD elements were missing | Commands 17 (Attack Ground); I16 type glyphs; I6 extended (XP bar, level badge, "+" seal, 12 selection tiles with a subgroup lift, idle-worker button); I17 control-group strip (P1) |
| 26 | Minor | I5 conflicted with juice HUD-07 | The art bible's Horizon Ribbon stays: a round day clock squints toward the classic orb. HUD-07 follow-up (§7) |
| 27 | Minor | Advisor and annoyed line counts were too low | Advisor P0 = 18 per faction (one per rules §17.3 trigger); heroes and workers get 5 annoyed lines. VO P0 203 → 235 lines, 355 CU. The label fix is #8 |
| 28 | Minor | Cues for P0 mechanics were P1 | S47a (stun, root), S50 (recall) and S69 (invisibility) moved to P0: 53 jobs ≈ 371 CU |
| 29 | Minor | A 6 m main ramp could be sealed | Both main ramps are 8 m, like every other ramp; `map_buildability` checks the width |
| 30 | Minor | The M2 readability set was not an exact list | M2 #2 lists the 16 silhouettes |
| 31 | Found | The shortest route crossed the basin 6.4 m from a Den creep (revision 2 wrongly said it skirted the basin) | Weighstall and Den moved 4 m north-west to (92, 92): clearance 12.1 m; goal 5, §1.6, §1.10 and §1.14 #7 corrected |
| 32 | Found | Production had moved ahead of the plan (ledger #15–#24: 12 characters auto-rigged, both halls, 27 textures) | §2.3, §2.4 and §2.6 show status; §2.15 re-based (151 cr spent, 77.5 cr derived, remaining P0 45.0 cr, margin 12.5; Krea P1 cap 325); §3.2 marked overtaken. The reviewer's funding steps are kept where they still apply (one icon per research line, 2 concept tries, deferring B12 as the last rung) |

## Review log, round 2 (2026-10-19: IP-safety and fidelity reviews of revision 3)

Where IP and fidelity conflicted, IP won and the closest legal alternative was taken. Severity as given by the reviewers. Edits to
other files are listed in §7, not made here.

| # | Severity | Issue | What changed |
|---|---|---|---|
| R2-1 | Major | Every slice game showed the kingdom in blue and the clans in red (the engine's reference colours; the art bible's old lobby rule) | §2.6 slice rule: kingdom Emerald, clans Royal Blue (Cornflower fallback); the kingdom never auto-gets Royal Blue, Cornflower or Gold, the clans never Crimson, Coral Rose or Violet; all captures use the defaults. M1 replaces `player_state.gd` `COLORS`; M1 #11 needs `check_value_echo.py` to exit 0; §2.2, M2 #3, M2 #6, M5 scope. §7: the art bible §2.4 lobby and marketing rules already match (checked); Coral Rose moves to the clans' skip set |
| R2-2 | Major | The art bible had renamed `built` back to `job_done`, so VO files would echo the banned catch-phrase | §2.12 states the conflict and that this plan wins (id `built`, label "Built"); §7 lists every rename (art bible §8.1, §8.2, §13 #16, review #23; AUD-03; economy juice; clans §3.3; the debug print), then the ban of `job done` / `job_done` / `job-done` before 3 Nov; M3 #2 checks VO file names |
| R2-3 | Major | Nothing in M1 checked our numbers against the classic ones; no kingdom reference rows; equivalents sat just past equality | M1 #11: both IP checkers exit 0; kingdom rows in `value_echo_reference.json` (or the kingdom §6.4 fingerprint test) before data entry; the **≥ 20 % at every rank** policy with a `min_rel_diff` check; known failures listed (Dust Veil → e.g. 60 / 100 / 140, 55 mana, 0.35 s fade; Keen Edge rank 1; Hail-Swifts cooldown) |
| R2-4 | Minor | Bombard "tapping" line echoed the banned touch premise and a classic artillery gag | New Annoyed 1 ("Measure twice, fire once…"); 4 Annoyed lines; acks trimmed to the 4-word limit; VO lint bans tap / tapped / tapping / prod / jab; §7 rewrites the art bible's "tap" runs |
| R2-5 | Minor | The clans crew's finish-each-other act moved the classic artillery crew's device to the other faction; "Ready to throw—" | Option B: the brothers speak in unison (a hauling count; their joke is that they always agree); 8 P0 lines in §2.12; lint: no Ready line starts with "Ready to", no split crew lines; §7 clans row |
| R2-6 | Minor | `banned_terms.txt` lacked explicitly banned lines and names; "wheel-rim shockwave" would ship as an fx id | §7 lists the 17 terms to add now (verified: no hits on the default paths) and the 6 that wait for renames (`milord`, `crowcaller`, `smoker` and the 3 completion-label spellings); `fx_wheel_rim_ring`; gate step 1 notes the gap; VO scripts are exported to `tools/prompts/vo/` so the checker sees them |
| R2-7 | Minor | "Militia" as the role word would ship in ids, clips and icons | "levy" everywhere: `kingdom.levy`, `arm_levy`, `kingdom_flail_levy_{128,64}.png` (B1, §2.4, §2.10, Appendix A, §7) |
| R2-8 | Minor | The path convention wrote "greenvale" into shipped filenames | `assets/textures/terrain/gv_<layer>.png`; rule in §1.12 and §2.16: the word appears only in docs |
| R2-9 | Minor | `map_lookalike` compared only against a non-exhaustive list | M1 #10: every 2-player melee map on Liquipedia's classic, expansion, remastered and W3Champions pools, view-only, URL list logged, with this map's specific arrangement named; the three map names join `banned_terms.txt` (§7) |
| R2-10 | Minor | D2 had no squint rules against the classic orc catapult | D2 art rules (traction sling, two crew hauling, no counterweight box, hanging felt sling, low hooded lattice cart, no spikes or bones); `haul` pose (P0, 0 cr); M2 #2 squint test |
| R2-11 | Minor | Red-brown lattice on the clans HUD inlay | I3: ochre-washed lattice (`#B7772A` / `#C9A46A`), "red-brown never on UI art"; gate 2b checks the teal-saffron-bronze read; §7 art bible §7.2 row |
| R2-12 | Minor | "Master's Seal" swapped one word of a banned coinage | Already "Guild Seal" in this doc and in kingdom §8 (round-2 rules review); the id `kingdom_linden_guild_seal` (kingdom's convention) is now named in E17 and §2.10 |
| R2-13 | Minor | Only the kingdom could multi-build, a second classic human signature | Option A: a clans rope-holder (+30 %, 5 lumber per 10 s, `haul`) makes multi-building a cross-faction rule in the slice (M1 scope and #9, Appendix A, §7); Option B (drop the Hod Chain) is the fallback if the clans doc rejects it (§5) |
| R2-14 | Minor | "Crowcaller" and "Smoker" collide with well-known coined enemies; Rat-Piper overlap | Crowherd and Coal-Lobber in B12, B13, B15, §2.4, S18 / S19; B19 concept-review rules (no pipe melee, no rat-swarm ultimate); §7 neutrals row, then the old names are banned |
| R2-15 | Minor | Wheel Marshal's slots matched the classic armoured hero's, with the heal's self-target quirk | Linden Balm self-target at 50 %; The Wagon Ring counted as her second equivalent; VFX rules (no golden dome, halo, bubble or light pillar; physical wagon boards, not a ghostly ring); any kit change re-runs the audit (M1 scope and #11) |
| R2-16 | Major | The flow assumed each player takes all the shared-camp XP | §1.11 split into uncontested best case and contested rows (creep-jack at the Cairn Gate ≈ 6:20; push at hero 1 L3–4, hero 2 L2–3); §1.8 XP arithmetic (845 shared, ≈ 422 each, 2,024 needed); `creep_route` is against a passive opponent; new `creep_route_mirror` (≥ 95 % / ≥ 80 %); M4 contested-camp branch with the creep-jack trigger and hero 1's 7:00–8:30 task; M4 #7 per faction. The +360 XP amber pair is a fallback (§1.14 #8), not placed by default, because the classic loop expects shared camps to be fought over |
| R2-17 | Major | The T3 hero slot could never be filled; the kingdom had no T3 unit upgrade; Bow Saws in the wrong tier | P1 (next grant): B19 Rat-Piper with inn hiring (425 g / 135 l, instant, free token valid) and third heroes B24 Flail Hetman and B25 Omen-Mother (9.5 cr each + icons + ≈ 20 VO lines); kingdom **Burgher's Oath** (Sworn Pavisier, 0 cr) mirrors the Proving Rite; Bow Saws stays T2, Felling Crews T3; E17 drops the slot and M4 #8 is dropped if none is funded |
| R2-18 | Major | One caster per faction removed the caster choice | P1 (next grant) B22 Lacewright and B23 Pole-Carver (9.5 cr each, cast clip 129, 1 icon sheet each, 14 VO lines each); M2 #2 re-runs at 18 silhouettes when they land; §2.10 and §2.15 counts. Their VO (with the heroes', ≈ 132 CU) goes through `elevenlabs_v4` on the next grant, since the Krea P1 cap cannot hold it |
| R2-19 | Major | 3 annoyed lines were too few for the click-spam signature; no Warcry | Regular units Annoyed 5 (14 lines), siege Annoyed 4 (8 lines): P0 VO 235 → 251 lines, 355 → 379 CU; P1 VO 130 → 106 CU with 12 Warcry lines first; Krea P1 cap 325 → 294 after R2-31 |
| R2-20 | Minor | A 5 m hall at the fixed pad centre left a 7.5 m seam gap | `hall_footprint_m`: hall centre = seam edge + 6.0 + F/2 (30.0 or 28.5 m; natural 164.0 or 165.5 m); §1.2, §1.4, §1.10, `map_economy_rules` runs both, §5 |
| R2-21 | Minor | The creep walk home was undecided and untested | M1 #5: invulnerable walk home, full HP and mana (`test_creep_leash`). Rules §15.2 already says so (checked); §7 marks neutrals §1.4's stale status line |
| R2-22 | Minor | The Crowherd's Crows fly but M1 had no flying units | M1 scope: rules §12 flying layer; #13 `test_flying_layer`; B15 fallback to a ground skimmer if cut |
| R2-23 | Minor | Classic control habits were not tested | M1 #12 `controls_parity` (the reviewer's full list) |
| R2-24 | Minor | AI item, shop and revive behaviour untested | M4 #9 (drops, power-ups, heal item by 6:00, revive within 5 s, recall rule, worker-raid reaction, full-inventory swap) |
| R2-25 | Minor | "Hero 1 / hero 2" meant both kit and training order | Naming convention: training order in §1 and §4, fixed kits in §2; `creep_route` runs both first-hero choices per faction (4 runs, +30 s for caster-first) |
| R2-26 | Minor | Levies at the ramp foot could exceed the 30 m leash | Levy ranges measured edge to edge from the hall footprint: ramp foot 25.3 m (8 m hall) / 28.6 m (5 m); §1.6, M1 #9, §7 kingdom row |
| R2-27 | Minor | Main lumber stated only within 25 m | §1.7: ≈ 196 trees (≈ 9,800 lumber) in each main, ≈ 184 within 30 m of the hall's edge (counted from the sketch; 4 rows deep); `map_economy_rules` requires ≥ 7,000 / ≥ 140 |
| R2-28 | Minor | No contested third mine | An 8,000 Gold Seam on the axis inside the Standing Ring (154, 154), hall site (164.2, 164.2) for F = 8 m, SE tree arc at 17–22 m; the Ring switches to guard mode; E11 ×5 (0 cr); §0, §1.1, §1.4, §1.7, §1.8, §1.9, §1.10, §1.13, §1.14 #9; M4 late-game expansion step |
| R2-29 | Minor | Fidelity judged by one subjective score | M5 #1: 12-item yes/no checklist; pass ≥ 10 / 12 from the veteran and no item failed by 2 of 3 testers |
| R2-30 | Minor | 0:00 worker count, the Turnip Patch first blow and kingdom speeds were inconsistent | 0:00 = 4 on gold, worker 1 builds the altar, 5 by 0:30 / 0:45; the Patch starts at 3:26 after the walk, so the first-blow claim holds; §1.10 notes 4.1 / 4.4 m/s and that `map_distances` tests path length only |
| R2-31 | Minor | Small asset gaps | Gun Tower upgrade icon (kingdom 39 → 40, still 45 sheets); S57a fire-bed loop to P0 (+7 CU; P0 SFX 54 jobs ≈ 378 CU); I12 programmatic target cursors P0; "inventory full" is text plus the S39 / S40 error click |
