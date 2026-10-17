# Core rules spec (global, all factions)

*Design date: 2026-10-16. Status: proposal for review. Scope: every rule that is the same for all four factions
(`kingdom`, `clans`, `sylvan`, `deathless`) and for neutrals. Data home: `data/factions.json` (§20).*

**Read with:** `docs/research/gameplay-mechanics.md` (all numbers below come from it unless marked), `docs/research/ip-safety.md`
(§0, §2, §3.2), `docs/research/README.md`, `docs/architecture.md` (§2, §4, §5, §8–§11), `docs/design/neutrals.md` (creep families,
items, neutral buildings) and the faction docs `docs/design/factions/kingdom.md`, `clans.md` and `sylvan-and-deathless.md`.

**Supersedes:** `gameplay-mechanics.md` §13.1 (global constants), §13.2 (damage matrix) and §13.7 (AI baseline). Where this doc and a
faction doc disagree on a *global* rule, this doc wins. Faction docs own faction numbers (unit stats, costs, tiers, signature mechanics).
`neutrals.md` owns creep rosters, camps and items; §15 here restates its global creep rules so the engine has one source.

**Brief, restated.** It should play *as much like Warcraft III as possible* without copying any expression. Rules, systems and numbers
are free to reuse (17 U.S.C. §102(b); ip-safety §1.1), so this spec keeps WC3's numbers **wherever the research gives them**.
Every deviation is marked **Δ** with a reason and listed in the fidelity ledger (§21). Names, UI text, icons and presentation are ours:
no WC3 term appears in data or UI (attack/armour type names in §7.1, upkeep labels in §4.5, advisories in §17.3).

**Conventions**

- **Distance:** metres. **1 WC3 game unit (gu) = 1/64 m** (a 128 gu WC3 tile = our 2 m tile; architecture §2). Values converted from gu
  are rounded to 0.1 m and shown as "(1400 gu)" where it helps review. Ranges are **edge to edge** (architecture §5).
- **Time:** sim seconds. The sim runs at **30 Hz** (`World.DT = 1/30`). Speed: m/s. Rates: per second.
- **Sight** is written day / night.
- Slice tags as in the faction docs: **[SLICE]**, **[SLICE+]**, *later*.
- "WC3" in a column means the reference value from the research docs. It never goes into data or UI.

---

## Contents

1. At a glance
2. Units of measure, ticks, rounding and randomness
3. Match setup and start conditions
4. Economy: gold, lumber, food, upkeep, spending, construction, repair
5. Tech tiers and upgrades
6. Heroes
7. Combat
8. Structures
9. Regeneration and mana
10. Status effects: buffs, debuffs, auras, dispel, immunity, summons
11. Invisibility and detection
12. Flying units
13. Day and night
14. Vision and fog of war
15. Creeps and bounty
16. Neutral buildings and items (global rules)
17. Game end, alerts and advisories
18. Controls
19. AI opponents
20. Constants: `data/factions.json`
21. Fidelity ledger (WC3 → Vibecraft)
22. Verification tests
23. Open questions, tuning flags and required follow-up edits

---

## 1. At a glance

| Rule | Value | WC3 |
|---|---|---|
| Start | T1 hall, 5 workers (idle), 500 gold / 150 lumber, clock 08:00, 1 free hero token | Same |
| Gold mine | 12,000 (main), 8,000 (expansion); low warning at 1,500 | 12,500 **Δ** |
| Mining | 10 gold per trip; 1 worker inside at a time for 1.0 s; 5 workers saturate at the standard 6 m hall gap (≈ 10 gold/s) | Same rhythm |
| Lumber | 50 per tree; per-faction trip size and chop rate (§4.3) | Same model |
| Food | Cap **100**. Upkeep: 0–50 food keeps 100 % of gold, 51–80 keeps 70 %, 81–100 keeps 40 % | Same |
| Tiers | Hall T1 → T2 → T3, upgraded in place; tier gates hero slots 1 / 2 / 3 and upgrade levels | Same |
| Heroes | Max 3, one per type; 425 g / 100 l, 5 food, 55 s (first free); XP 200 … 5400, cap level 10; 3 abilities × 3 ranks + ultimate at 6 | Same |
| XP | Unit kill 25 / 40 / 60 / 85 / 115 / 150 / 190 / 235 / 285 / 340 by level; creep factor 80 / 70 / 60 / 50 / 0 % by hero level; shared within 18.75 m | Same |
| Revive | Altar: gold 425 × (0.40 + 0.10 × (L − 1)) ≤ 550, time 55 × L × 0.65 ≤ 110 s. Inn: instant, 50 % HP, 0 mana | Same |
| Combat | 7 attack types × 7 armour types matrix (TFT values, our names); armour reduction 0.06A / (1 + 0.06A); damage point / backswing / cooldown | Same |
| Day / night | 480 s cycle, 240 s day + 240 s night; first dusk at 200 s; sight 21.9 / 12.5 m (units), 28.1 / 12.5 (heroes), 12.5 / 9.4 (workers) | Same |
| Fog | Black mask, fog, visible; cliffs block upward sight; trees block sight; flyers ignore both | Same |
| Creeps | Acquire 3.9 m; camp acts as one; leash 18.75 m; give up after 10 s; sleep at night; no respawn; bounty 4 × level + 2 + rand(0–4) | Leash/bounty unverified in WC3 |
| End | Defeat when a player owns no structure. Lose every hall → revealed after 120 s | Same |
| Controls | Smart right-click; 12-unit selection; 10 control groups; shift-queue 32; autocast; rally; F1–F3 heroes; 4×3 card | Same |
| AI | Easy / Normal / Hard, no cheats, scripted per-faction build orders (§19) | Our design |

---

## 2. Units of measure, ticks, rounding and randomness

### 2.1 Conversions

| Quantity | Rule | Examples |
|---|---|---|
| Distance | m = gu ÷ 64 | 250 gu = 3.9 m; 500 = 7.8; 700 = 10.9; 800 = 12.5; 1200 = 18.75; 1400 = 21.9; 1800 = 28.1; 2000 = 31.25 |
| Speed | m/s = (gu/s) ÷ 64 | 150 = 2.34; 190 = 2.97; 270 = 4.22; 350 = 5.47; 400 = 6.25; 522 = 8.16 |
| Collision | radius m = collision size ÷ 64 | 16 = 0.25; 31 = 0.48; 48 = 0.75 |
| Cliff level | WC3 128 gu; ours `CLIFF_H` (architecture §2) | Rules count levels, not metres |

### 2.2 Ticks and rounding

- **Timers** are stored in data as seconds and converted once to integer ticks: `ticks = max(1, round(seconds × 30))`. The error is at most 1/60 s.
  - Attack and cast timings that change with attack speed are reconverted at the start of each swing from the *modified* seconds.
  - Periodic effects (regeneration, DoTs, auras) run every tick with `rate × DT`, or on their own interval in ticks.
- **HP and mana** are floats. Damage and healing are **not rounded**. The UI shows `ceil(hp)` while alive (a unit at 0.3 HP shows 1).
  A unit dies when `hp ≤ 0`.
- **Resources** (gold, lumber, food) are integers. Each rate that produces fractions (repair cost, gold-drain abilities) keeps a per-player
  fractional accumulator and pays whole units.
- **Upkeep** rounds each taxed income event **down** (§4.5).
- **Attributes** are floored (§6.6).

### 2.3 Randomness

- All sim randomness comes from the seeded `World.rng` in a fixed call order (architecture §1 rule 2). Uses: damage rolls (integer, uniform in
  `[min, max]`), proc chances (critical, bash, evasion), creep bounty, creep item picks at match start, random hero proper names, AI choices.
- **AI** draws from its own stream `rng_ai = seeded(match_seed ^ 0xA1)` so adding an AI decision never shifts combat rolls.
- Proc chances are **true random** per roll (WC3 1.x style). Pseudo-random distribution is a later option (`combat.proc_mode`).
- Visual-only randomness (fx jitter, idle fidgets) never touches the sim RNG (juice docs).

### 2.4 Game speed

`rules.match.game_speed` 1.0 = WC3 ladder speed: game seconds equal real seconds. Single-player may offer 0.75 / 1.0 / 1.25 by scaling
`Engine.time_scale` (more or fewer ticks per real second). Every number in this doc is in game seconds.

---

## 3. Match setup and start conditions

### 3.1 Players

| Item | Rule |
|---|---|
| Slice | 1v1: one human player vs one AI, on one map (Greenvale). `kingdom` vs `clans`, either side |
| Later | Up to 12 players in teams; allied shared vision on by default (team melee) |
| Neutrals | `PlayerState.NEUTRAL_HOSTILE = 12` (creeps, enemy of all), `NEUTRAL_PASSIVE = 13` (mines, shops, critters, enemy of none) |
| Colours | Team colour per player id (`PlayerState.COLORS`); shown on unit team-colour masks, flags and minimap |

### 3.2 Start conditions

| Rule | Value | Notes |
|---|---|---|
| Starting resources | **500 gold / 150 lumber** | WC3 TFT values. Per-faction field, all four factions use the same numbers |
| Starting structure | The faction's **T1 hall**, complete, at the start location | `kingdom_moot_hall`, `clans_shell_hall`, `sylvan_stilt_lodge`, `deathless_wake_barrow` |
| Starting units | **5 workers**, placed on a 1 m (64 gu) spacing between the hall and the mine, **idle** | WC3 workers start idle; the first clicks are part of the feel. `rules.match.start_units_idle` |
| Clock | **08:00**, so the first dusk is at 200 s | `rules.match.start_hour` |
| Hero token | **1**: the first hero (altar or inn) costs no gold or lumber, only 5 food | WC3 `bj_MELEE_STARTING_HERO_TOKENS` |
| First-hero item | The first hero trained gets the faction's **recall item** once (Homeward Horn, Homeward Felt, Lake Whistle, Coin for the Ferry) | WC3 gave the first hero a free return scroll |
| Vision | Everything is black mask except what the starting units see | |
| Camera | Centred on the hall | |
| Main mine | The mine nearest the start within 31.25 m (2000 gu) | WC3 search radius |

### 3.3 Map placement rules that the economy depends on

- **Hall–mine gap:** a hall footprint may not be placed within **6.0 m** (3 tiles, 384 gu) of a gold mine footprint, edge to edge.
  Start locations are placed at exactly 6.0 m. This gap is what makes 5 workers saturate (§4.1). **Δ** mechanics §13.1 said 4 m;
  the walk-time maths below needs 6 m with 3.0 m/s workers. Verify with test `economy_saturation` (§22).
- Every start has 1 main mine; each expansion has 1 expansion mine with a guard-mode creep camp (neutrals §1.3).
- A tree line within 8–12 m of the hall (lumber walk) and a natural expansion within 40–60 m path distance.

---

## 4. Economy

### 4.1 Gold

| Rule | Value | WC3 |
|---|---|---|
| Mine capacity | **12,000** main, **8,000** expansion | 12,500 (maps vary). **Δ** shorter games; neutrals "Gold Seam" |
| Low-gold warning | At **1,500** remaining: advisory + minimap ping, once per mine | 1,500 |
| Gold per trip | **10** for every faction's worker | 10 |
| Inside time (dwell) | **1.0 s** (30 ticks). The worker is hidden inside the mine | ≈ 1 s (unverified) |
| Occupancy | **1 worker inside at a time.** Others wait at the mine door in arrival order (no stacking) | Same behaviour |
| Saturation | **5 workers** at the standard 6 m gap | 5 since patch 1.13 |
| Depletion | At 0 gold the mine collapses (juice ECO-07), workers inside pop out idle, pathing is freed, advisory "mine exhausted" | |
| Delivery | The worker walks the gold to the **nearest finished friendly hall** (any tier) by path distance; delivery is instant on touching the footprint | Same |

**Why 5 workers saturate.** Cycle per worker = 2 × (gap − 2 × worker radius) ÷ speed + dwell + turn-arounds
= 2 × (6.0 − 0.7) ÷ 3.0 + 1.0 + ≈ 0.3 ≈ **4.8 s**. Five workers need 5 × 1.0 s of mine time per 4.8 s, so the mine is always busy and
income is ≈ **10 gold/s** (≈ 2 gold/s per worker, matching the WC3 "5 seconds per 10 gold" figure). Four workers give ≈ 8.3 gold/s; a sixth
adds almost nothing. If a playtest misses this, tune `mine_dwell`, never the gap.

**Per-faction gold:** all four factions walk gold back to a hall. WC3's "worker lives inside the mine" and "mine must be cursed first" variants
were dropped by the faction docs (sylvan §A3.1, deathless §B3.1), so there is **one mining model**.

### 4.2 Lumber

| Rule | Value | WC3 |
|---|---|---|
| Lumber per tree | **50** (`data/doodads.json` per tree type; default `rules.economy.lumber_per_tree_default`) | ≈ 50 (unverified) |
| Chopping | The worker stands adjacent to the tree and gains 1 lumber per `chop_interval` until it carries `lumber_per_trip`, then walks to the nearest lumber drop-off | 1 per hit |
| Felling | A tree at 0 lumber is removed: its cells are freed, `tree_felled` fires, pathing relabels (architecture §6) | Same |
| Sharing a tree | Any number of workers may chop one tree (except `sylvan`, one per tree) | Same |
| Drop-off | Any finished friendly hall, or the faction's lumber building | Same |
| Taxes | Lumber is **never** taxed by upkeep | Same |

### 4.3 Per-faction gathering differences

| Faction | Worker | Gold | Lumber per trip | Chop | Trees | Lumber drop-off | Builders per site | Notes |
|---|---|---|---|---|---|---|---|---|
| `kingdom` | Hodman | 10, walked | **10** (15 with Bow Saws, 20 with Felling Crews) | 1 per 0.8 s | Felled | Hall, Timber Yard *(later)* | Up to **3**; each extra +60 % rate, no extra cost | **Levy Horn** turns workers into militia in place (kingdom §4) |
| `clans` | Yurtwright | 10, walked | **15** | 1 per 0.9 s | Felled | Hall, Casting Pit | **1**; others may Mend (repair) | **Sound the Gong / Roll the Felt** worker garrison (clans §4.1) |
| `sylvan` *(later)* | Tapster | 10, walked | **8** | 1 per 1.0 s | **Never felled** (tapping) | Lodge, Resinworks | Up to **2**; second +50 % | One Tapster per tree; woodline never recedes (sylvan §A3.1) |
| `deathless` *(later)* | Sexton | 10, walked | **10** | 1 per 0.8 s | Felled | Barrow, Ossuary | Up to **2**; second +50 % | Pall spreads from buildings (deathless §B3.1) |

Rate check at the slice's typical 10 m tree walk: kingdom 10 ÷ (8.0 + 6.7) ≈ 0.68 lumber/s per worker; clans 15 ÷ (13.5 + 6.5) ≈ 0.75.
At 4 m the two are equal (≈ 0.93). Clans trade early tempo (first delivery 13.5 s after arrival vs 8 s) for fewer, longer trips.

**Worker cargo rules**

- A worker carries one resource kind at a time (`carry_gold` or `carry_lumber`).
- Ordering a worker to gather the *other* kind while it carries a load **discards the load** (WC3 behaviour). "Return Cargo" (§18.4) delivers
  it first; shift-queue Return Cargo then Gather to switch without loss. `rules.economy.switch_resource_discards_load`.
- A worker that dies, is garrisoned, or turns into militia keeps or drops its cargo per its faction mechanic; the default is that cargo is kept
  and delivered on its next return.
- A worker that finishes a building becomes **idle** (WC3 behaviour; the idle-worker key exists for this). Shift-queued Gather after Build works.

### 4.4 Food (supply)

| Rule | Value |
|---|---|
| Cap | **100** (`rules.economy.food_cap`). Food provided above 100 is ignored; the HUD shows `used / min(provided, 100)` |
| Providers | Halls (per tier, replacing not adding) and supply buildings, **only when complete**: kingdom hall 12 / 14 / 16, Croft +7; clans hall 10 / 10 / 10, Home Yurt +10; sylvan lodge 10 / 12 / 14, Stilt Larder +10; deathless barrow 10 / 12 / 14, Columbarium +10 |
| Costs | Unit `cost.food`: worker 1, line infantry 2–3, ranged 2–3, casters 2, siege 3, heavy 4–6, hero 5. Summoned units and structures cost **0** |
| Training | Gold and lumber are paid when the item is **queued**. Food is reserved when the item **starts** training. If free food is short, the queue head **waits** ("stalled for food", juice ECO-16) and the advisory "need supply" plays at most every 8 s |
| Counting | `food_used` includes units in training and living heroes. **Dead heroes free their 5 food**; reviving needs 5 free food |
| Losing supply | If supply drops below `food_used` (a farm died), nothing dies; new training waits until food is free |
| Unit level | A unit's **level** (XP value, creep-style difficulty) defaults to its food cost; defs may override (`level`) |

### 4.5 Upkeep

| Tier | Food used | Gold kept per taxed income | Per 10-gold trip | Label (ours) |
|---|---|---|---|---|
| 0 | 0–50 | **100 %** | 10 | "Upkeep 0 %" |
| 1 | 51–80 | **70 %** | 7 | "Upkeep 30 %" |
| 2 | 81–100 | **40 %** | 4 | "Upkeep 60 %" |

- **Evaluated** at each income event from the current `food_used` (including units in training).
- **Rounding:** each taxed amount is floored separately: `floor(amount × factor)`.
- **Taxed income** (`rules.economy.upkeep_taxed_income`): mined gold, creep bounty, gold from selling items, gold-producing abilities.
  Liquipedia notes WC3 taxes bounty and sales too; the floating number shows the **taxed** amount (we show the real value, unlike WC3).
- **Not taxed:** lumber, refunds from cancels, starting resources.
- **HUD:** the tier label sits next to food with the notched-coin icon (juice economy §1). Crossing a tier upward plays an advisory
  ("our gold income falls", in each faction's own words) and flashes the label for 3 s. The labels avoid WC3's wording on purpose.
- Design intent (from WC3, classic.battle.net): keep armies small, reward aggression, punish turtling. "High upkeep is meant to be punishing."

### 4.6 Spending, queues and cancels

| Action | When paid | Cancel refund | Notes |
|---|---|---|---|
| Train unit | On queue | **100 %** | Food reserved on start (§4.4) |
| Research / upgrade | On queue | **100 %** | One research of each line at a time per player |
| Hall tier upgrade | On start | **100 %** | The hall cannot train while upgrading (WC3) |
| Construct building | When the worker **arrives and starts** (`build_pay = "on_start"`) | **75 %** **Δ** (unverified in WC3) | If unaffordable on arrival, the order fails with the "need gold/lumber" advisory |
| Hero (altar) | On queue (or the free token) | 100 % (token returns) | |
| Hero revive | On queue | 100 % | |

- **Production queue:** **7** items per building (1 active + 6 waiting). Shift-click on a train button queues **5**.
- **Placement:** footprints need buildable, explored cells (black-mask cells are refused), no cliffs or ramps, no water (sylvan may use shallow
  water), no units of another player inside. Own units inside the footprint are pushed out when construction starts. Hall-type buildings obey
  the 6.0 m mine gap (§3.3). Flying units never block placement.

### 4.7 Construction

| Rule | Value |
|---|---|
| Start HP | **10 %** of max HP; HP rises linearly with progress to 100 % |
| Progress | `build_time` seconds for one builder. Extra builders per faction (§4.3) |
| Armour | The building's own type and value during construction |
| Builders | Stay on site until it completes (extra builders per §4.3), then go idle |
| Supply / function | A building provides food, drop-off and production only when complete |
| Destroyed site | Paid resources are lost |
| Construction verb | Per faction (scaffold-raised, raised felt, woven, unearthed); the `build_progress` reveal shader (juice BLD-06) |

### 4.8 Repair

| Rule | Value | WC3 |
|---|---|---|
| Who | Workers with the faction's repair ability (Hodman *Repair*, Yurtwright *Mend*, Tapster *Resin Seal*, Sexton *Re-mortar*) | Worker repair |
| Targets | Friendly structures, and friendly **mechanical** units (siege carts, constructs). Never organic units or heroes | Same |
| Rate | Full repair takes `build_time × 1.5` for one repairer; each extra repairer adds the same rate | ≈ Same (unverified) |
| Cost | **30 %** of the building's gold and lumber cost, pro rata to HP restored, paid continuously (fractional accumulator) | ≈ 35 % (unverified) |
| No money | Repair pauses when the player cannot pay the next whole unit | |
| Autocast | Default **off**. When on, an idle worker repairs damaged targets within **8.0 m** | Same |
| Under construction | Builders on a damaged site keep building (no repair cost); repair applies to complete buildings only | |

---

## 5. Tech tiers and upgrades

### 5.1 Hall tiers by faction

| Faction | T1 | T2 (upgrade) | T3 (upgrade, *later*) |
|---|---|---|---|
| WC3 reference | 385 g / 205 l, 180 s, 1500 HP, +12 food | +320 / 210, 140 s, 2000 HP | +360 / 210, 140 s, 2500 HP |
| `kingdom` | Moot Hall 400 / 200, 170 s, 1550 HP, +12 | Walled Burg +310 / 200, 130 s, 2050 HP, +14 | Crown Burg +350 / 220, 140 s, 2600 HP, +16 (needs Oath Hall + Foundry) |
| `clans` | Shell Hall 375 / 190, 155 s, 1550 HP, +10 | Banner Shell +305 / 195, 130 s, 2050 HP, +10 (needs Naming Stones) | Sun-Gong Shell +330 / 215, 145 s, 2600 HP, +10 |
| `sylvan` | Stilt Lodge, +10 | Lantern Lodge, +12 (needs Calling Pier) | Amber Lodge, +14 (needs Resinworks) |
| `deathless` | Wake Barrow, +10 | Long Barrow, +12 (needs Cenotaph) | Grand Barrow, +14 (needs Ossuary) |

Halls have **Fortified** armour 5 and train the faction worker at every tier. Upgrades keep the footprint and current HP fraction.

### 5.2 What tiers unlock (global shape)

| Tier | Unlocks (every faction) |
|---|---|
| **T1** | Workers; the barracks-type building and its two basic units; altar and **hero 1**; supply; towers; level-1 weapon/armour upgrades; faction shop stock T1 |
| **T2** | Caster, workshop/siege and beast/air buildings; mid-tier units; **hero 2**; level-2 upgrades; caster *Adept/Journeyman* training; shop stock T2; **single-hero XP bonus +15 %** |
| **T3** | Top-tier units (heavy cavalry/giants, heavy air); **hero 3**; level-3 upgrades; caster *Master* training; shop stock T3; **single-hero XP bonus +30 %** |

Exact unit and building gates are in each faction doc (§7 of kingdom and clans; A7/B7 of sylvan-and-deathless). The slice uses **T1 and T2 only**.

### 5.3 Requirement rules

- The player's **tier** is the highest tier among their *finished* halls.
- Requirements (tier, buildings, research) are checked **live**. Losing them greys the dependent buttons; items already in production finish.
- Hero slots follow the live tier, but existing heroes are never removed (§6.1).

### 5.4 Weapon and armour upgrade lines (global shape)

| Line | Levels | Requirement | Effect per level |
|---|---|---|---|
| Weapons (per damage family, e.g. melee, ranged, siege) | 3 (slice: 2) | L2 needs T2, L3 needs T3 | Each affected unit gains its def's `upgrade_damage` (default: 10 % of base average damage, rounded, at least 1) |
| Armour (per armour family) | 3 (slice: 2) | Same | **+2 armour** per level (WC3) |
| Building armour (masonry-type) | Faction-defined | | +1 or +2 armour per level; faction docs |

WC3 cost reference (classic.battle.net): weapons 100/50, 175/175, 250/300 (60/75/90 s); armour 125/75, 150/175, 175/275. Faction docs set their own.

---

## 6. Heroes

### 6.1 Slots and acquisition

| Rule | Value | WC3 |
|---|---|---|
| Maximum | **3** heroes per player, **1 of each type** (altar and inn heroes count the same) | Same |
| Slots by tier | T1: **1**, T2: **2**, T3: **3**. Dead heroes awaiting revive occupy their slot | Same |
| Cost | **425 gold / 100 lumber, 5 food, 55 s** at the faction altar | Same |
| First hero | Free (token), 5 food, plus the faction recall item | Same |
| Inn heroes | **425 g / 135 l**, 5 food, **hired instantly** (no train time); a free token also covers an inn hero | Same (lumber 135 since 1.15) |
| Spawn | Full HP and mana, at the altar's edge toward its rally point | |
| Proper name | Random from the hero's name list, shown as "Title: Name" (faction docs) | Same idea |
| Hero glow | A ground glow ring identifies heroes (juice CMB-34) | |

### 6.2 Levels and XP table

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Total XP to reach | 0 | 200 | 500 | 900 | 1400 | 2000 | 2700 | 3500 | 4400 | 5400 |

`XP(L) = XP(L − 1) + 100 × L` from `XP(2) = 200`. **Cap: level 10** (no XP gained at 10).

**Level-up:** max HP and mana rise from the new attributes; current HP and mana rise by the **same amount** (the missing amount is kept).
The hero gains 1 skill point.

### 6.3 XP sources

| Source | XP | Notes |
|---|---|---|
| Enemy non-hero unit | By the victim's level: **25, 40, 60, 85, 115, 150, 190, 235, 285, 340** (levels 1–10) | `F(1) = 25`, `F(x) = F(x − 1) + 5x + 5` |
| Enemy hero | By the victim hero's level: **100, 120, 160, 220, 300, 400, 500, 600, 700, 800** | |
| Creep (neutral hostile) | The unit-kill table × the receiving hero's **creep factor** | Hero level 1: **80 %**, 2: **70 %**, 3: **60 %**, 4: **50 %**, 5+: **0 %** |
| Summoned unit | **50 %** of its level's value | Applies to creep and player summons |
| Structure | **None**, unless the structure has an attack; then by its def `level` (towers 2–4) | WC3: no XP for passive buildings |
| Tower kill (killing blow by a structure) | **None** to anyone | WC3 |
| Own or allied unit (deny) | **None** to anyone, and no bounty | |
| Critter | None | |
| Item "tome of experience"-type power-ups | Flat XP, **ignores** the creep factor, still blocked at level 10 | |

### 6.4 XP sharing

1. On a kill, collect the killer's owner's **eligible heroes**: alive, level < 10, within **18.75 m** (1200 gu) of the dying unit (edge to edge).
2. Split the base XP (after the summon factor) **evenly** among them.
3. Each hero multiplies its share by its own creep factor (creeps only) and by the **single-hero bonus**.
4. **No eligible hero in range → the XP is lost** (`rules.xp.no_hero_in_range = "lost"`). **Flag:** the research quotes a WC3 claim that
   heroes elsewhere still get it; neutrals §1.6 copied that. This spec chooses "lost" because WC3 exposes a hero-XP *range* constant and
   players bring heroes to fights to level them. The other behaviour is one data switch (`"all_heroes"`). Verify against WC3 before shipping.
5. **Single-hero bonus:** a player who owns exactly **one** hero (alive or dead) gets **+15 % at T2** and **+30 % at T3** on all XP.
6. Allied heroes (team games, *later*): only the killer's owner's heroes receive XP.

Worked example: a level-1 hero kills a green camp of two level-2 and two level-1 creeps: (40 + 40 + 25 + 25) × 0.80 = **104 XP**.
Two green camps reach level 2. At level 5 the same camps give nothing, so the hero must fight the enemy to grow.

### 6.5 Abilities and skill points

| Rule | Value |
|---|---|
| Kit | **3 normal abilities × 3 ranks + 1 ultimate × 1 rank** (fidelity: at most 2 of 4 may be functional equivalents of the matching WC3 hero's) |
| Skill points | **1 at level 1**, +1 per level (10 total = 9 normal ranks + 1 ultimate) |
| Rank gates | Normal rank *r* needs hero level ≥ **2r − 1** (levels 1 / 3 / 5). Ultimate needs level **6** |
| Learning | The **Learn** button (§18.4) opens the skill card; unspent points show a "+" badge on the hero portrait |
| Cast timing | `cast_point` (default 0.3 s) then the effect; `cast_backswing` (default 0.5 s) can be cancelled by any order. Mana and cooldown are spent **at the cast point**. An order or stun before the cast point cancels at no cost |
| Channels | Stop when the caster moves, is stunned, silenced or ordered elsewhere |
| Duration on heroes | Control effects (stun, sleep, root, slow, silence, disarm) last **50 %** as long on heroes unless the ability sets `hero_duration`. Polymorph-type and "remove from game" effects cannot target heroes |
| Spell damage on heroes | ×0.7 through the matrix (Spell vs Hero), §7.2 |

### 6.6 Attributes

Every hero has STR, AGI and INT with a base and a per-level growth (faction docs §6), and one **primary** attribute.

| Derived stat | Formula | Per point |
|---|---|---|
| Effective attribute | `floor(base + growth × (level − 1))` + item and buff bonuses | |
| Max HP | `100 + 25 × STR` | STR +25 HP |
| HP regen | `0.25 + 0.05 × STR` HP/s | STR +0.05 HP/s |
| Max mana | `15 × INT` | INT +15 mana |
| Mana regen | `0.01 + 0.05 × INT` mana/s | INT +0.05 mana/s |
| Armour | `base_armor + 0.3 × AGI` (+ items, buffs). Hero base armour is usually −2 … +1 | AGI +0.3 armour |
| Attack cooldown | `base_cooldown ÷ (1 + 0.02 × AGI + other attack-speed bonuses)`, clamped (§7.5) | AGI +2 % attack speed |
| Damage | `base_damage [min, max]` + **1 × primary attribute** | Primary +1 damage |
| Sight | 28.1 / 12.5 m (1800 / 800 gu) | |
| Spell resistance | Built into the Hero armour type (×0.7 vs Spell) | |

Check against kingdom §6.2: Wheel Marshal at level 10 has STR floor(23 + 2.6 × 9) = 46 → 1250 HP; AGI floor(12 + 1.4 × 9) = 24 → armour 1 + 7.2 = 8.2. ✓

### 6.7 Revival

| Where | Cost | Time | Returns with |
|---|---|---|---|
| **Altar** | Gold only: `floor(425 × (0.40 + 0.10 × (L − 1)))`, max **550** | `55 × L × 0.65` s, max **110 s** (= min(110, 2 × 55)) | **Full HP**, mana `min(max, 100)` (**flag:** research value, verify), level, XP, skills and items |
| **Inn** (neutral) | Gold `425 × (0.8 + 0.2 × (L − 1))`, max **1,105**; lumber `100 × (0.8 + 0.2 × (L − 1))`, max **260** | **Instant** | **50 % HP, 0 mana** |

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Altar gold | 170 | 212 | 255 | 297 | 340 | 382 | 425 | 467 | 510 | 550 |
| Altar time (s) | 36 | 72 | 107 | 110 | 110 | 110 | 110 | 110 | 110 | 110 |
| Inn gold / lumber | 340 / 80 | 425 / 100 | 510 / 120 | 595 / 140 | 680 / 160 | 765 / 180 | 850 / 200 | 935 / 220 | 1020 / 240 | 1105 / 260 |

- Revive needs 5 free food and a free altar queue slot. The revived hero appears at the altar (or inn) and walks to the rally point.
- **Hero death:** the body fades (no usable corpse); the hero **keeps its items**; its portrait shows a revive timer once queued.

### 6.8 Inventory and items (hero rules)

| Rule | Value |
|---|---|
| Slots | **6** per hero. Non-hero units carry nothing in the slice |
| Hotkeys | Numpad 7 / 8 / 4 / 5 / 1 / 2 (WC3 layout); laptop preset Alt+1 … Alt+6 |
| Pick up | Smart-click an item; picked up within 1.0 m. Power-ups apply on pickup and vanish |
| Give / drop | Drag to another own hero within 1.5 m to give; drag to the ground to drop. Items on the ground never expire |
| Classes | Permanent, charged, power-up, artifact, purchasable; levels 1–8 (neutrals §4) |
| Stacking | Different items stack additively; identical permanent effects stack unless the item says "unique" (auras never stack, §10.3) |
| Cooldown groups | Items of one group (e.g. healing potions) share a cooldown |
| **Recall items** | Channel **3.0 s** (cancelled if the hero is stunned, silenced or ordered to move), then the hero and up to **11** own units within **6.0 m** teleport next to the nearest own finished hall. Price and stock per faction (300–350 g) |

---

## 7. Combat

### 7.1 Attack and armour types (our names)

**Attack types**

| Id | Display name | Used by | WC3 analogue |
|---|---|---|---|
| `blade` | **Blade** | Melee units | Normal |
| `pierce` | **Pierce** | Archers, throwers, gunners, most towers | Pierce |
| `siege` | **Siege** | Siege engines, demolition | Siege |
| `arcane` | **Arcane** | Casters' attacks, some flyers | Magic |
| `heroic` | **Heroic** | Every hero's attack | Hero |
| `pure` | **Pure** | Creeps of level 7+, big summons, some ultimates | Chaos |
| `spell` | **Spell** | Ability damage (default for all ability damage) | Spells |

**Armour types**

| Id | Display name | Worn by | WC3 analogue |
|---|---|---|---|
| `light` | **Light** | Most flyers, fast skirmishers | Light |
| `medium` | **Medium** | Ranged units, workers, riders | Medium |
| `heavy` | **Heavy** | Melee infantry, siege carts, giants | Heavy |
| `fortified` | **Fortified** | Buildings, deployed forts | Fortified |
| `hero` | **Hero** | Heroes; neutral heroes | Hero |
| `unarmored` | **Unarmored** | Casters, critters, some summons | Unarmored |
| `adamant` | **Adamant** | Special objectives and boss shrines (*later*); none in the slice | Divine |

The weight names (light, medium, heavy, fortified, unarmored) are plain descriptive English used across the genre; only the distinctive
WC3 coinages are replaced (Normal → Blade, Magic → Arcane, Chaos → Pure, Divine → Adamant). **Data ids change** from today's file:
attack `hero` → `heroic`, `chaos` → `pure`, plus the new armour `adamant` (migration in §20.4).

### 7.2 Damage matrix (percent of damage dealt)

| Attack ↓ / Armour → | Light | Medium | Heavy | Fortified | Hero | Unarmored | Adamant |
|---|---|---|---|---|---|---|---|
| **Blade** | 100 | **150** | 100 | 70 | 100 | 100 | 5 |
| **Pierce** | **200** | 75 | 90 | 35 | 50 | 150 | 5 |
| **Siege** | 100 | 50 | 100 | **150** | 50 | 150 | 5 |
| **Arcane** | 125 | 75 | **200** | 35 | 50 | 100 | 5 |
| **Heroic** | 100 | 100 | 100 | 50 | 100 | 100 | 5 |
| **Pure** | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| **Spell** | 100 | 100 | 100 | 100 | **70** | 100 | 50 |

TFT values from classic.battle.net with the later Pierce vs Heavy 90 % (warcraft.wiki.gg). Adamant column: WC3 Divine (5 % from attacks,
100 % from Chaos, 50 % from spells).

**Special statuses** (flags, not armour types):

| Status | Effect |
|---|---|
| `spell_immune` | Takes **0** from Arcane attacks and Spell damage; cannot be targeted by abilities unless the ability has `pierces_immunity` (some ultimates); positive auras still apply, negative auras do not |
| `spectral` (*later*, our "ethereal") | Immune to Blade, Pierce, Siege, Heroic and Pure attacks; takes **×1.66** from Arcane and Spell; cannot attack |
| `invulnerable` | Cannot be targeted or damaged by anything |

### 7.3 Armour value

- **Positive armour:** damage multiplier `= 1 − 0.06A / (1 + 0.06A)`. Each armour point adds **6 % effective HP**.
- **Negative armour:** multiplier `= 2 − 0.94^(−A)` (approaches ×2.0).
- **Spell damage ignores the armour value** (only the type multiplier applies). WC3 behaviour from memory: spell damage of the magic kind skips
  armour; **flag** to verify. Pure attacks use the armour value but ignore the type matrix.

| Armour | −10 | −5 | −2 | −1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 15 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Damage × | 1.461 | 1.266 | 1.116 | 1.060 | 1.000 | 0.943 | 0.893 | 0.847 | 0.806 | 0.769 | 0.735 | 0.676 | 0.625 | 0.526 | 0.455 |
| Reduction | −46.1 % | −26.6 % | −11.6 % | −6.0 % | 0 | 5.7 % | 10.7 % | 15.3 % | 19.4 % | 23.1 % | 26.5 % | 32.4 % | 37.5 % | 47.4 % | 54.5 % |

### 7.4 Damage pipeline (order of operations)

1. **Base roll:** integer uniform in `[damage_min, damage_max]` (`World.rng`) + flat bonuses (upgrades, items, auras, primary attribute).
2. **Percent bonuses** (damage auras, buffs) on the result of step 1, added together.
3. **Proc multipliers** (critical strike); different crit sources do not stack: the highest roll applies.
4. **Type multiplier** from the matrix (§7.2).
5. **Armour multiplier** (§7.3); skipped for Spell damage.
6. **Damage-taken modifiers** on the target (e.g. Ironbark-style "−25 % Pierce taken", spell shields that absorb).
7. Apply to HP. **No minimum** and no rounding (§2.2).

Example: Hookgunner (Pierce 22–28, average 25) shoots a Grappler (Heavy, armour 1): 25 × 0.90 × 0.943 ≈ **21.2** damage.

**Life steal** heals a percentage of the final damage dealt; it does nothing against structures and mechanical units.
**Evasion / miss chance** sources do not stack: the highest applies. A missed attack deals 0 and shows a "miss" tell.
**High ground:** **no** uphill miss chance (some WC3 versions had one). High ground is a **vision** advantage only (§14.3). **Δ**

### 7.5 Attack timing

Every weapon has three phases (architecture §5): **damage point** (wind-up), **backswing** (tail), **cooldown** (weapon timer, measured from
the **start** of the swing).

| Rule | Value |
|---|---|
| Start a swing | Target in range and within ±0.35 rad of facing (turning at `turn_rate`) |
| At the damage point | Melee damage lands if the target is within `range + 2.5 m` (range buffer); a ranged unit launches its projectile |
| Cancel before the damage point | Any new order or a stun cancels the swing, **no damage**, and the cooldown is refunded (animation cancelling) |
| During the backswing | Any order ends it at once (backswing cancelling) |
| Attack speed | Damage point, backswing and cooldown are all divided by the attack-speed factor `1 + Σ bonuses`, clamped to **[0.2, 5.0]** (−80 % … +400 %) |
| Units while swinging | Do not move |

**Default timings by class** (data `combat.defaults` fills only `damage_point` and `backswing` today; the class defaults go into unit defs).
WC3 values per unit are unverified; these are starting values in the documented WC3 ranges (damage point 0.3–0.6 s, backswing 0.3–0.7 s).

| Class | Damage point (s) | Backswing (s) | Turn rate (rad/s) | Typical cooldown (s) |
|---|---|---|---|---|
| Worker | 0.45 | 0.55 | 9 | 2.0 |
| Melee infantry | 0.40 | 0.45 | 9 | 1.35–1.6 |
| Ranged infantry (bow, sling, javelin, gun) | 0.35 | 0.55 | 9 | 1.5–2.0 |
| Caster attack | 0.45 | 0.55 | 9 | 1.75–2.0 |
| Heavy melee, cavalry, giants | 0.50 | 0.50 | 6 | 1.4–2.0 |
| Siege engine | 0.60 | 0.80 | 4 | 3.0–3.5 |
| Flyer | 0.40 | 0.50 | 6 | 1.75–2.1 |
| Hero, melee | 0.35 | 0.60 | 9 | 2.0–2.4 base |
| Hero, ranged | 0.40 | 0.50 | 9 | 2.1–2.3 base |
| Tower | 0.25 | 0.0 | instant | 1.0–2.6 |

### 7.6 Acquisition, targeting and chasing

| Rule | Value |
|---|---|
| Auto-acquire range | Units **8.0 m** (WC3 ≈ 500 gu), heroes **9.4 m** (600 gu), ranged units at least `range + 1 m`, workers **0** (never auto-attack), creeps 3.9 m (§15) |
| Scan | Every 5 ticks, staggered by id (architecture §5) |
| Target choice | Nearest valid enemy, with **structures +6 m** penalty (units first). Ties by id |
| Retaliation | An idle or attack-moving unit that is hit engages its attacker if it can reach it |
| Call for help | When a unit is hit, idle units of the **same player** within **6.0 m** (`help_radius`) that can attack engage the attacker |
| Leash (player units) | An auto-acquired chase ends **14 m** from the unit's guard position, or when the target escapes beyond `max(acquire, engage distance) + 3 m`, or after 1.5 s without progress (architecture §5) |
| Explicit Attack | Chases until the target dies, becomes invisible to us, or leaves vision. No leash |
| Force attack | The Attack order may target own and allied units (deny); no XP or bounty |
| Sleeping creeps | Never auto-acquired; only an explicit Attack or an attack-move click on them engages (§15) |

### 7.7 Ranged attacks and projectiles

- Projectiles **home** on the target's current hit point and **cannot miss** except through evasion; a projectile whose target died lands harmlessly.
- Damage is rolled at **launch** (architecture §5); type and armour apply on **arrival**.
- Typical speeds: arrows and javelins 18–22 m/s (≈ 1200–1400 gu/s), bullets 30 m/s, siege shells 12–14 m/s on a high arc, caster bolts 15 m/s.
- **Minimum range** (siege): 3.5–3.9 m; targets inside it cannot be attacked.

### 7.8 Splash

| Rule | Value |
|---|---|
| Shape | Up to three rings: **full**, **half**, **quarter** damage (def `splash: [r_full, r_half, r_quarter]` in metres) |
| Victims | **Enemies and neutral hostiles only**; no friendly fire (`combat.splash_friendly_fire = false`) **Δ** (WC3 artillery behaviour unverified) |
| Air | Splash hits air only if the attack's `targets` include air |
| Type | Same attack type as the main hit; each victim's own armour applies |
| Structures | Take splash |

### 7.9 Attack Ground

Units with `can_attack_ground` (all siege engines) get **Attack Ground** (§18.4): they fire at a point repeatedly until ordered otherwise.
The shell lands at the point and applies splash there. It never targets a unit, so it can hit units the attacker cannot see (fog), and it does
not reveal the area.

### 7.10 Class baselines (for unit authors)

| Class | HP | Armour | Speed (m/s) | Sight (m) | Radius (m) | Food / level |
|---|---|---|---|---|---|---|
| Worker | 220–240 | 0 Medium | 3.0–3.1 | 12.5 / 9.4 | 0.35 | 1 |
| T1 line melee | 420–660 | 1–2 Heavy | 4.1–4.2 | 21.9 / 12.5 | 0.45 | 2–3 |
| T1 ranged | 370–535 | 0 Medium | 4.1–4.2 | 21.9 / 12.5 | 0.45 | 2–3 |
| Caster | 300–330 | 0 Unarmored | 4.2 | 21.9 / 12.5 | 0.40 | 2 |
| Siege cart | 420–450 | 1–2 Heavy | 3.3–3.4 | 21.9 / 12.5 | 0.80 | 3 |
| Cavalry / T3 heavy | 820–1300 | 2–5 Heavy | 3.9–5.5 | 21.9 / 12.5 | 0.70–1.0 | 4–5 |
| Flyer | 480–800 | 0–1 Light | 5.0–6.25 | 21.9 / 12.5 | 0.5–0.8 | 3–4 |
| Hero (level 1) | 475–750 | Hero | 4.4–5.0 | 28.1 / 12.5 | 0.55 | 5 |

Movement speed is clamped to **[2.34, 6.25] m/s** (150–400 gu/s; WC3 default min and max) after all modifiers. The hard engine cap is
8.16 m/s (522 gu/s) for special cases. **Flag:** the 150 gu/s minimum is from memory.

**Formation:** a group whose spread is under 8 m moves in formation at the speed of its slowest member (architecture §4). Larger groups move independently.

---

## 8. Structures

| Rule | Value |
|---|---|
| Armour | **Fortified**, value **5** (scout towers 2); masonry-type research per faction |
| HP | Halls 1550 / 2050 / 2600; production buildings 900–1350; supply 500–620; towers 320–520 (faction docs) |
| Sight | Default **14.0 / 9.4 m**; halls and towers set their own (clans hall 18.0 / 12.5; kingdom Lookout 25 / 18); capped at 28.1 m |
| Regeneration | **None** by default (WC3 human/orc buildings). Faction exceptions only (deathless Pall, sylvan noonlight) |
| Under construction | §4.7 (starts at 10 % HP) |
| Destroyed | Footprint freed at once; rubble decays over **4 s** (`structure_decay`); no XP unless it had an attack |
| Fog | Enemy buildings, once seen, leave a **ghost** (last-seen state, no HP shown) until re-scouted (§14) |
| Towers | Upgraded in place from a scout tower; exclusive branches per faction. Towers turn instantly and use auto-acquire = range |
| Burning | Visual only below 50 % HP (no damage over time) |
| Rally | Production buildings have a rally point (§18.6); trained units appear at the footprint edge nearest the rally (or toward the map centre) |

---

## 9. Regeneration and mana

| Who | HP regen | Mana regen | Start mana |
|---|---|---|---|
| Organic units | **0.25 HP/s** | Casters **0.65 mana/s** (def may set 0.6–0.67) | **75** (def `start_mana` may override; kingdom casters start at 40 %) |
| Mechanical units, constructs | 0 (repairable) | As def | As def |
| Structures | 0 | — | — |
| Heroes | 0.25 + 0.05 × STR | 0.01 + 0.05 × INT | Full on training |
| Creeps | 0.25 organic, 0 constructs (neutrals §1.1) | 0.6 | Full |
| Summons | As def (usually 0) | As def | As def |

- Regeneration is continuous (`rate × DT` per tick) and stops at max. Dead units do not regenerate.
- **No out-of-combat bonus** (WC3 has none). Healing comes from abilities, items, fountains (neutrals) and faction terrain effects.
- **Faction regen hooks:** deathless on Pall +1.5 HP/s (heroes +2.0), enemies on Pall get no natural regen; sylvan in noonlight +1 HP/s.
  `kingdom` and `clans` have none.
- **Mana** exists only on units with `max_mana > 0`. Spending mana below 0 is impossible; abilities check cost at the cast point.

---

## 10. Status effects: buffs, debuffs, auras, dispel, immunity, summons

### 10.1 Buff model

Each applied effect is a **buff** record: `{id, source_unit, source_player, polarity: positive|negative, kind: magic|physical|aura|ultimate,
remaining, rank, data}`.

| Rule | Value |
|---|---|
| Same buff again | **Refreshes** duration; the stronger rank replaces the weaker. Magnitudes never stack from the same buff id (`status.same_buff = "refresh"`) |
| Different buffs | Stack additively (e.g. two different attack-speed buffs add) |
| Periodic effects | DoTs and HoTs tick every **1.0 s** unless the ability sets `tick_interval` |
| Death | All buffs end; auras emitted by the dead unit vanish after the linger time |

### 10.2 Hard and soft control

| Effect | Rule |
|---|---|
| Stun | No move, attack or cast; cancels channels and wind-ups; queued orders **resume** afterwards |
| Sleep | As stun, but **any damage wakes** the target |
| Root | No movement; can attack and cast. Flyers cannot be rooted unless grounded |
| Silence | No active abilities or item use; passives and auras keep working |
| Disarm | No attacks |
| Slow | Lowers move speed and/or attack speed; speed floor 2.34 m/s (§7.10) |
| Taunt | Forces the victim to attack the taunter; ends early if the taunter becomes invalid |
| Grounded (flyers) | §12.3 |
| Heroes | Control lasts **50 %** unless `hero_duration` is set (§6.5) |
| Hardy creeps (level 6+) | Sleep, polymorph, enthral and root last 50 % (neutrals §1.1) |

### 10.3 Auras

- Radius per ability (typically 8–14 m); the aura re-applies every **0.5 s** and lingers **2.0 s** after a unit leaves.
- **Same aura from two sources:** only the **highest rank** applies. Different auras stack.
- Auras ignore fog, affect the emitter itself unless stated, and are **not dispellable**.

### 10.4 Dispel

| Rule | Value |
|---|---|
| What it removes | Every buff with `dispellable: true` in the area or on the target, **both polarities** (WC3 style). Defaults: magic buffs **true**; auras, ultimates, upgrades and item passives **false** |
| Summons | A dispel deals the ability's `summon_damage` to every enemy summon hit (typical 200–400) |
| Spell-immune units | Not affected by enemy dispels; own dispels can cleanse allies that are not spell-immune |

### 10.5 Magic immunity

`spell_immune` units: §7.2 table. They cannot be healed by single-target spells, cannot be targeted by abilities (except `pierces_immunity`),
are not hit by area spell damage, take 0 from Arcane attacks, and still receive positive auras. In the slice: sylvan Ambermail and
Glimmerswarm are *later*; kingdom Assayer is *later*. No slice unit is spell-immune.

### 10.6 Summoned units

| Rule | Value |
|---|---|
| Food | 0; never counted for upkeep |
| Timed life | Def `lifetime`; shown as a draining bar |
| XP and bounty | 50 % XP; **no bounty** |
| Dispel | Takes `summon_damage` (§10.4) |
| Corpses | Leave none |
| Classification | `summoned` flag (targets for anti-summon effects, e.g. kingdom Silver Spire ×3 damage) |

### 10.7 Unit classification flags

`ground` / `air`, `organic` / `mechanical`, `structure`, `hero`, `worker`, `summoned`, `spell_immune`, `invulnerable`, `ward`.
Abilities list allowed targets with these flags. Healing spells skip `mechanical` and `structure`. Repair targets only `mechanical` and `structure`.

### 10.8 Corpses

Units leave a corpse for **8 s** (`corpse_decay`), then it sinks and is removed (architecture §4; juice CMB-31). Heroes, summons and mechanical
units leave none. *Later* (deathless corpse abilities): a 60 s "remains" stage, usable by corpse-consuming spells.

---

## 11. Invisibility and detection

| Rule | Value |
|---|---|
| Invisible units | Cannot be seen, selected, targeted or auto-acquired by an enemy without **detection**. Allies see them translucent |
| Kinds | `permanent` (scouts, wards; never breaks), `fade` (an ability; **breaks on attack, cast or item use**, refades after `fade_time`, default 1.0 s), `still` (only while not moving or attacking, e.g. a flyer stealthed at night) |
| Breaking | The attack or cast that breaks invisibility still happens; the unit is visible from that tick |
| Losing a target | An enemy that turns invisible during an attack is dropped by attackers without detection |
| Pathing | Invisible units still block movement (bodies collide) |
| **Detection (true sight)** | A unit or structure with `true_sight` radius R reveals invisible enemies within R that are also inside its owner's **visible** area. Typical R 9.0–9.4 m (detector towers, scouts, the reveal items) |
| Reveal effects | Area reveals (shop dust, flare-type spells, Fog Bank exceptions) show terrain **and** invisible units for their duration |
| Presentation | Detected invisible enemies get a shimmer outline for the detecting player (our shader, not WC3's) |

Slice sources: kingdom Silver Spire (*later*) and Chalk of Seeing (T2 shop), neutral merchant reveal dust, clans per their doc.
Faction detection gaps are part of their identity (clans: "few cheap detectors").

---

## 12. Flying units

### 12.1 Movement

- Flyers ignore ground pathing, cliffs, water and trees. They collide (separate) **only with other flyers**.
- Fly height default **3.5 m** above terrain (def `fly_height`); selection ring and shadow on the ground beneath.
- They never block ground units, building placement or body-blocks, and cannot be body-blocked.
- Speed caps as ground units (§7.10).

### 12.2 Combat and vision

- Only attacks with `targets` including **air** can hit flyers (`G`, `A`, `G+A` in the faction tables). Ground-only splash ignores them.
- Flyers' sight **ignores occluders** (cliffs and trees) (§14.3).
- Idle creeps do **not** acquire flyers; once a camp is fighting, ranged creeps shoot them (neutrals §1.3).
- Flyers cannot pick up items; flying heroes (none planned) would be an exception.

### 12.3 Grounded state

Effects that "pull a flyer down" (kingdom Netcaster net, clans Hobble-Bola, deathless Burial Shroud) set **grounded** for their duration:
the flyer counts as a ground unit (melee can hit it, root can hold it), moves at 50 % speed on ground pathing, and if it lands over an
unwalkable cell it is placed on the nearest walkable one. When the effect ends it lifts off in 0.5 s.

---

## 13. Day and night

| Rule | Value | WC3 |
|---|---|---|
| Cycle | **480 s**: day 240 s (06:00–18:00), night 240 s | Same |
| Game hour | 20 s | Same |
| Start | 08:00 | Same |
| Events | First **dusk at 200 s**, first **dawn at 440 s**, then every 240 s (dusk at 680, 1160, 1640 s; dawn at 920, 1400 s) | Same |
| Hour at time t | `hour = (8 + t / 20) mod 24` (`DayNight.hour_at`) | |
| Sight change | Over **3.2 s** from the event (WC3 steps every 0.4 s; we interpolate) | Same duration |
| Night effects (global) | Night sight values (§14.2); most creeps sleep, Hollow-Harvest-type creeps wake (neutrals §1.5) | Same |
| Faction hooks | kingdom: none (Night Watch research keeps building day sight); clans: Skymirror abilities only; sylvan: Sunstore/noonlight; deathless: none | Our designs |
| Presentation | Our own clock widget (no orb copy), our own dusk and dawn stingers (audio doc), minimap vision visibly shrinking | |

---

## 14. Vision and fog of war

### 14.1 States

| State | Meaning | Shows |
|---|---|---|
| **Black mask** (unexplored) | Never seen | Nothing (#0A0C12). Neutral buildings are not shown either |
| **Fog** (explored) | Seen before, not now | Terrain and doodads at reduced value; **ghosts** of enemy and neutral structures as last seen; mines and shops; no units |
| **Visible** | Inside a friendly sight area now | Everything except invisible enemies |

- Per-player grid at **1 m**, recomputed every **0.1 s** (3 ticks; WC3 0.4 s on 2 m cells). A unit leaving vision is hidden at the next recompute.
- An enemy unit is visible when the cell under its centre is visible. Large units (radius > 0.7 m) also count any visible footprint cell.
- Allies share vision (team games). Neutral hostile and passive players grant no vision to anyone.

### 14.2 Sight values

| Who | Day (m) | Night (m) | gu |
|---|---|---|---|
| Most units | **21.9** | **12.5** | 1400 / 800 |
| Heroes | **28.1** | **12.5** | 1800 / 800 |
| Workers | **12.5** | **9.4** | 800 / 600 |
| Structures (default) | 14.0 | 9.4 | ≈ 900 / 600 |
| Creeps (AI use only) | 14.0 | 9.0 | neutrals §1.1 |
| Cap | 28.1 | 28.1 | 1800 |

### 14.3 Line of sight

| Rule | Value |
|---|---|
| Cliffs | A viewer sees cells whose level is **≤ its own**. Ground units **cannot see up** a cliff. Ramp cells take a fractional level along the slope, so a unit halfway up a ramp sees the lower level but not the plateau |
| Trees | A tree blocks sight for viewers below `tree base level + 2` (WC3 occluder height ≈ 2 cliff levels). The tree's own cell is visible; cells behind it are not |
| Flyers | Ignore cliffs and trees |
| Structures | Do not block sight |
| Shadowcasting | Per sight source, grid shadowcasting over the 1 m grid; cost budget in architecture §8. `vision.trees_block_sight` may be turned off only if the perf test fails (it is a WC3 feel rule) |
| Attack reveal | A unit that attacks from where the victim's owner cannot see is revealed to that player in a **1.5 m** radius for **1.0 s** (WC3 "attacking unit" reveal; values unverified). This is what makes high ground a vision, not a dice, advantage |
| Creep notice | Never leaks invisible or fogged units (juice anti-pattern 15) |

### 14.4 Cripple reveal

A player who owns **no finished hall** (any tier) starts a **120 s** countdown (shown to that player in our own words). At 0 all their
structures are revealed to every enemy until they finish a hall again. Losing the last hall while a new one is under construction still starts it.

---

## 15. Creeps and bounty

`neutrals.md` §1 is the full creep rule set. The engine-relevant rules, restated:

### 15.1 Creep AI

| Rule | Value |
|---|---|
| Acquire | **3.9 m** (250 gu) by default; casters 5.0 m; guard-mode camps 6.0 m. Only real players' units (not critters or other neutrals) |
| Notice | Head turn toward an intruder at 1.5 × acquire (visual tell only) |
| Camp acts as one | Every creep has a `camp_id`. If any member acquires a target or takes damage, every awake member engages. Other camps never join |
| Camp mode (default) | Fights only units in acquire range or attackers; ignores buildings |
| Guard mode (expansion mines) | Also attacks any building **started within 12 m** of the camp centre |
| Flyers | Idle creeps do not acquire flyers |
| Towers | A creep hit by a tower it cannot reach drops that target after **2 s** and returns |
| Target choice | Keep the current target while it is in range; switch to an attacker that is at least 3 m closer, or to the unit that damaged the camp most in the last 3 s if the current target leaves range |
| Spell AI | neutrals §1.7 table (summon on aggro; area spells on 2+ targets or a hero; disables on heroes first) |
| Respawn | **Never** (a few creeps reincarnate once, per creep def) |

### 15.2 Leash and return

| Rule | Value |
|---|---|
| Leash | A creep past **18.75 m** from its **guard position** drops its target and returns |
| Give up | If the camp neither dealt nor took damage for **10 s**, every member returns |
| Returning | Walks home ignoring hits (**not invulnerable**), regenerating **2 % of max HP/s** until home |
| Split pulls | Allowed: the slowest creeps turn back first |

WC3 leash and give-up values are unverified; these are starting values (neutrals §1.4).

### 15.3 Sleep

| Rule | Value |
|---|---|
| Schedules | `night` (default: asleep 18:00 → 06:00), `never`, `day` (night-active families, at most one per tileset) |
| Falling asleep | 0–6 s after sleep time (seeded stagger), only if the camp is home and not fighting |
| Waking | At wake time (+0–6 s), or at once when a camp member takes damage, a building starts within 12 m, or a player buys or hires at a neutral building within 10 m |
| Player units | **Never auto-acquire sleeping creeps** (night is safe scouting) |
| Tells | Family posture, closed-eye glyph and snore puffs (never a letter "Z") |

### 15.4 Camp colours and drops

Green total level 1–9, amber 10–19, red 20+ (WC3 bands; shield-shaped minimap pips, not dots). Drops are rolled at match start and carried
by the highest-level (better drop) and lowest-level (second drop) creep (neutrals §1.8).

### 15.5 Bounty

| Rule | Value |
|---|---|
| Creeps | `4 × level + 2 + rand(0–4)` gold (seeded), paid to the killer's owner. Level 1: 6–10 … level 9: 38–42 |
| Taxed | By upkeep, like mined gold (§4.5) |
| Summoned creeps | No bounty |
| Player units | **No bounty** in melee (WC3 default). A *later* game option may enable it |
| Shown | Bounty pop and coin flight (juice CMB-28), showing the taxed amount |

---

## 16. Neutral buildings and items (global rules)

| Rule | Value |
|---|---|
| Use range | An own unit within **7.0 m** (edge to edge) of a neutral building can buy, hire or use it. **Flag:** the research quotes "45 gu (60 before 1.15)", which looks like warcraft.wiki.gg's ×10-scaled notation for 450 / 600 gu; 7.0 m = 450 gu |
| Buying | Smart-click the shop to select it; its card shows stock. The item goes to the selected hero if in range, else the nearest own hero in range with a free slot, else drops at the buyer's feet |
| Stock | Per item: stock count and restock timer; stock is **per player** (**flag**: WC3 behaviour unverified) |
| Selling | To a merchant-type building for **50 %** of the item's gold cost (taxed by upkeep). Lumber is not refunded |
| Inn | Hires neutral heroes (§6.1) and revives any hero instantly (§6.7). Never guarded |
| Fountains | Area regeneration (Hale Spring +2 % max HP/s within its radius; neutrals). No effect on structures |
| Waking creeps | Buying or hiring within 10 m of a sleeping camp wakes it (§15.3) |

---

## 17. Game end, alerts and advisories

### 17.1 Defeat and victory

| Rule | Value |
|---|---|
| Defeat | A player is defeated the moment they own **no structure** (finished or under construction). Units do not count (WC3 rule). Deployed unit-forms (e.g. Wagon Fort) are units |
| On defeat | Their remaining units are removed (they scatter and fade) and their vision ends |
| Victory | The last team with an undefeated player wins |
| Surrender | A player may concede (menu); the AI never concedes |
| Cripple | §14.4 |
| Time limit | None |
| End screen | Our own score summary (units, heroes, resources, creeps); no WC3 layout |

### 17.2 Pausing

Single-player pause is unlimited. Multiplayer (*later*): 3 pauses of 60 s per player.

### 17.3 Alerts and advisories (rule triggers; wording lives in each faction's VO script)

| Trigger | Throttle | Minimap ping |
|---|---|---|
| Own unit or building attacked | Once per **8 s** per category (units, buildings, workers) | Yes; Space jumps there |
| Hero died / hero revived / hero level-up | Each event | Death: yes |
| Building finished / research finished / unit trained (idle queue) | Each event | No |
| Need gold / lumber / supply / hero slot | At most once per 1.0 s (error), "need supply" stall at most once per 8 s | No |
| Gold mine low (1,500) / exhausted | Once per mine | Yes |
| Upkeep tier rises | Each change | No |
| Cripple countdown started / revealed | Each event | No |
| Dusk / dawn | Each event | No (stinger only) |

Wording is ours (ip-safety §2.2). No WC3 line or paraphrase ("…under attack" phrasing gets each faction's own voice).

---

## 18. Controls

### 18.1 Mouse

| Input | Result |
|---|---|
| Left-click / drag box | Select. Own mobile units are preferred over own buildings, which are preferred over one foreign unit |
| Shift + left-click | Add or remove a unit |
| Ctrl + left-click, or double-click | Select every own unit of that type on screen |
| Right-click | **Smart command** (§18.2) |
| Shift + right-click | Queue the smart command |
| Wheel, PgUp / PgDn | Zoom (18.75–35.2 m) |
| Middle drag | Grab-pan the ground |
| Minimap left-click / right-click | Jump camera / smart command at that point |

### 18.2 Smart right-click (resolved per unit, architecture §4)

| Target | Workers | Combat units | Production building selected |
|---|---|---|---|
| Ground | Move | Move (formation) | Set rally point |
| Enemy unit or structure | Attack | Attack | Rally on it |
| Own or allied unit | Follow | Follow (attacks only when the leader attacks) | Rally: follow that unit |
| Gold mine | Gather gold | Move | Rally: workers gather |
| Tree | Gather lumber | Move | Rally: workers gather |
| Own unfinished building | Help build (if the faction allows extra builders) | Move | — |
| Own damaged building or mechanical unit | Repair | Move | — |
| Own hall / drop-off while carrying | Return cargo | Move | — |
| Item on the ground | Hero: pick up. Others: move | | |
| Neutral shop or inn | Select it for buying (a unit walks into use range) | | |
| Sleeping creep | Attack (explicit) | Attack (explicit) | |

### 18.3 Selection and groups

| Rule | Value |
|---|---|
| Selection cap | **12** units (WC3 classic; matches the 12-slot selection grid). 24 is a later option |
| Subgroups | The selection is grouped by unit type in a fixed priority (heroes first, then by food cost). **Tab / Shift+Tab** cycles the active subgroup, whose card is shown. Shared orders (move, stop, hold, attack, patrol) go to everyone; abilities go to the active subgroup |
| Smart casting | A targeted ability ordered for a subgroup is cast by **one** caster: the nearest that has the mana and is off cooldown |
| Control groups | **10** (0–9). **Ctrl+N** set, **Shift+N** add, **N** select, double-tap **N** centres the camera. Buildings can be grouped (towers only with towers) |
| Heroes | **F1–F3** select heroes in training order; double-tap centres |
| Halls | **Backspace** cycles own halls |
| Idle worker | **F8** or **`** (backtick) selects the next idle worker; HUD button shows the count |
| Last alert | **Space** jumps to the last alert position |

### 18.4 Orders and the command card

The card is **4 × 3**. Positions follow WC3's structure (a genre convention, Lotus v. Borland "method of operation"), with our own art.

| Row | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
|---|---|---|---|---|
| Top | Move | Stop | Hold Position | Attack |
| Middle | Patrol | Unit command (Attack Ground, Build, Gather, faction toggle) | Unit command (Build Advanced, Return Cargo, garrison) | **Learn** (heroes) / unit command |
| Bottom | Ability 1 | Ability 2 | Ability 3 | Ability 4 (hero ultimate) |

**Hotkey presets** (Settings; both rebindable):

| Command | **Classic** (default) | **Grid** |
|---|---|---|
| Move / Stop / Hold / Attack | M / S / H / A | Q / W / E / R |
| Patrol | P | A |
| Attack Ground | G | S |
| Build / Build Advanced | B / V | S / D |
| Gather / Return Cargo / Repair | G / C / R | position |
| Learn | O | F |
| Abilities (bottom row) | Hero: **Q / W / E / R**. Units: the ability def's `hotkey` letter (validated unique per card), else Q / W / E / R | Z / X / C / V |
| Building cards (train, research) | The def's `hotkey` letter, else grid position | Position |
| Cancel / back | Esc | Esc |

Classic keeps WC3's letter habits ("A-click" attack-move). Grid matches `card_0..11` in architecture §11. `Defs` validates that no two buttons
on one card share a Classic key.

**Order semantics** (architecture §5): Move ignores enemies; **Attack** on ground = attack-move (engages anything on the way, re-paths after
each fight); Attack on a unit = chase to the death; **Hold** never moves and only attacks enemies already in range; **Stop** clears the queue
and cancels a wind-up; **Patrol** = attack-move ping-pong; **Attack Ground** §7.9.

### 18.5 Queueing and autocast

| Rule | Value |
|---|---|
| Shift-queue | Move, attack, attack-move, patrol, gather, return, build, repair, cast, use item. Up to **32** orders per unit (WC3 limit unverified) |
| Waypoints | Shown while Shift is held (juice CMB-11) |
| Shift + Attack on several units | Builds a focus-fire list |
| Building queues | 7 items (§4.6); Shift + train = 5 |
| Autocast | **Right-click** an ability button to toggle; a gold animated border (our style) marks it on. Applies to every unit of that type in the selection. Defaults per ability def (`autocast_default`); repair defaults off |

### 18.6 Rally points

- Right-click (or the Rally command) with a production building selected sets its rally: ground, unit (follow) or resource (workers gather on arrival; non-workers move).
- New units walk to the rally. A rally on a unit that dies falls back to its last position.
- Alt shows every own rally flag (juice CMB-12).

### 18.7 Other keys

| Key | Action |
|---|---|
| Alt (hold) | Show all health bars and rally flags |
| Insert / Delete | Rotate the camera temporarily (springs back) |
| F10 | Menu |
| Numpad 7 8 4 5 1 2 | Inventory slots (§6.8) |
| Arrow keys / screen edge | Pan |

---

## 19. AI opponents

The slice AI is a scripted player that issues the same command dictionaries as input (architecture §4). It follows its faction's opening
(kingdom §10, clans §10), then a simple state machine: **Build up → Creep → Tier up → Army → Push / Defend**. It never cheats: it sees only
its own fog, gets no resource bonus and obeys every rule in this doc.

| Behaviour | Easy | Normal | Hard |
|---|---|---|---|
| Think interval | 1.0 s | 0.5 s | 0.5 s |
| Reaction delay (seeing → acting) | 1.5 s | 0.8 s | 0.3 s |
| Action cap (orders per minute) | 40 | 90 | 180 |
| Build-order slack (added per step) | +20 s | +5 s | 0 |
| Gold workers per mine / lumber workers (T1 / T2) | 4 / 3 / 5 | 5 / 4 / 7 | 5 / 5 / 8 |
| First hero ready by | ≈ 2:00 | ≈ 1:50 (per faction script) | ≈ 1:50, rushes altar |
| T2 started (latest) | 6:00 | Faction script (3:45–4:15), at the latest 4:30 | 3:45 |
| Creeping | Green camps only, by distance | Green then amber; skips camps above its army's total level × 1.2 | Green, amber, and red once 2 heroes are level 4+; times camps to finish before dusk |
| Hero retreat | Below 25 % HP | Below 35 % HP | Below 35 % HP; uses potions and recall item first |
| Army retreat | Never | Below 50 % of its starting army HP | Below 50 %, re-engages when healed |
| Attack trigger | Army food ≥ 50 and time ≥ 10:00 | Army food ≥ 40, or an enemy hero seen creeping within 31 m | Army food ≥ 30 with a level advantage, or any enemy creeping within 31 m (creep-jacking) |
| Focus fire | None | Lowest-HP enemy in range | Heroes first, then casters, then lowest HP; finishes kills for XP |
| Micro | None | Pulls the hero back | Pulls units below 30 % HP behind the line; kites with ranged; keeps siege behind melee |
| Abilities | Off cooldown on the nearest enemy | Standard rules (area on 2+ targets, heals below 60 % HP) | Best target (most enemies in area, interrupt channels, disable heroes) |
| Items and shops | Uses drops only | Buys potions and the recall item | Shops each return home; buys detection when it sees invisibility |
| Upkeep discipline | Ignores | Stays ≤ 50 food before T2 | Stays ≤ 50 until the push, then up to 80 |
| Expansion | Never | ≈ 10:00, or when the main mine is below 4,000 | ≈ 7:00, behind a tower |
| Scouting | None | Hero creep route only | Worker scout at 0:45, then every 2 min |
| Faction signature | Never | Levy Horn / Sound the Gong when 3+ enemy combat units (6+ food) are within 15–20 m of its workers | Same, plus All Clear / Stand Down promptly and rebuilds lost supply |
| Determinism | Uses `rng_ai` (§2.3) | | |

---

## 20. Constants: `data/factions.json`

### 20.1 Shape

The file keeps its current top-level keys and gains one: **`rules`** (match, economy, heroes, xp, regen, status, items, daynight, vision,
creeps, neutral, controls, ai). `combat`, `upkeep` and `factions` stay where `Defs` already loads them. `Defs` adds `var rules: Dictionary`
and `func rule(path: String, fallback)` (e.g. `Defs.rule("economy.gold_per_trip", 10)`).

### 20.2 Constants table (every row is one JSON field)

Units: m, s, m/s, per second. "—" = unitless.

**`rules.match`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.match.start_hour` | 8.0 | hour | 3.2 |
| `rules.match.hero_tokens` | 1 | — | 3.2 |
| `rules.match.twinked_heroes` | 1 | — | 3.2 |
| `rules.match.start_units_idle` | true | — | 3.2 |
| `rules.match.main_mine_search_radius` | 31.25 | m | 3.2 |
| `rules.match.cripple_reveal_time` | 120.0 | s | 14.4 |
| `rules.match.defeat_rule` | "no_structures" | — | 17.1 |
| `rules.match.game_speed` | 1.0 | × | 2.4 |

**`rules.economy`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.economy.gold_per_trip` | 10 | gold | 4.1 |
| `rules.economy.mine_dwell` | 1.0 | s | 4.1 |
| `rules.economy.mine_occupancy` | 1 | workers | 4.1 |
| `rules.economy.mine_gold_main` | 12000 | gold | 4.1 |
| `rules.economy.mine_gold_expansion` | 8000 | gold | 4.1 |
| `rules.economy.mine_low_warning` | 1500 | gold | 4.1 |
| `rules.economy.hall_mine_gap` | 6.0 | m | 3.3 |
| `rules.economy.lumber_per_tree_default` | 50 | lumber | 4.2 |
| `rules.economy.food_cap` | 100 | food | 4.4 |
| `rules.economy.upkeep_rounding` | "floor" | — | 4.5 |
| `rules.economy.upkeep_taxed_income` | ["mine", "bounty", "item_sale", "ability"] | — | 4.5 |
| `rules.economy.build_pay` | "on_start" | — | 4.6 |
| `rules.economy.build_start_hp` | 0.1 | fraction | 4.7 |
| `rules.economy.build_cancel_refund` | 0.75 | fraction | 4.6 |
| `rules.economy.train_cancel_refund` | 1.0 | fraction | 4.6 |
| `rules.economy.research_cancel_refund` | 1.0 | fraction | 4.6 |
| `rules.economy.production_queue` | 7 | items | 4.6 |
| `rules.economy.shift_train_count` | 5 | items | 4.6 |
| `rules.economy.repair_cost_factor` | 0.30 | fraction | 4.8 |
| `rules.economy.repair_time_factor` | 1.5 | × build time | 4.8 |
| `rules.economy.repair_autocast_range` | 8.0 | m | 4.8 |
| `rules.economy.switch_resource_discards_load` | true | — | 4.3 |
| `rules.economy.supply_stall_advisory` | 8.0 | s | 4.4 |

**`rules.heroes`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.heroes.max` | 3 | heroes | 6.1 |
| `rules.heroes.slots_by_tier` | [1, 2, 3] | heroes | 6.1 |
| `rules.heroes.unique_types` | true | — | 6.1 |
| `rules.heroes.cost_gold` | 425 | gold | 6.1 |
| `rules.heroes.cost_lumber` | 100 | lumber | 6.1 |
| `rules.heroes.food` | 5 | food | 6.1 |
| `rules.heroes.train_time` | 55.0 | s | 6.1 |
| `rules.heroes.inn_cost_lumber` | 135 | lumber | 6.1 |
| `rules.heroes.level_cap` | 10 | level | 6.2 |
| `rules.heroes.xp_levels` | [0, 200, 500, 900, 1400, 2000, 2700, 3500, 4400, 5400] | XP | 6.2 |
| `rules.heroes.skill_points_start` | 1 | — | 6.5 |
| `rules.heroes.skill_points_per_level` | 1 | — | 6.5 |
| `rules.heroes.rank_levels` | [1, 3, 5] | level | 6.5 |
| `rules.heroes.ultimate_level` | 6 | level | 6.5 |
| `rules.heroes.base_hp` | 100 | HP | 6.6 |
| `rules.heroes.base_hp_regen` | 0.25 | HP/s | 6.6 |
| `rules.heroes.base_mana_regen` | 0.01 | mana/s | 6.6 |
| `rules.heroes.str_hp` | 25 | HP/pt | 6.6 |
| `rules.heroes.str_hp_regen` | 0.05 | HP/s/pt | 6.6 |
| `rules.heroes.agi_armor` | 0.3 | armour/pt | 6.6 |
| `rules.heroes.agi_attack_speed` | 0.02 | /pt | 6.6 |
| `rules.heroes.int_mana` | 15 | mana/pt | 6.6 |
| `rules.heroes.int_mana_regen` | 0.05 | mana/s/pt | 6.6 |
| `rules.heroes.primary_damage` | 1 | dmg/pt | 6.6 |
| `rules.heroes.attribute_rounding` | "floor" | — | 6.6 |
| `rules.heroes.control_duration_factor` | 0.5 | × | 6.5 |
| `rules.heroes.inventory_slots` | 6 | slots | 6.8 |
| `rules.heroes.sight` | [28.1, 12.5] | m | 14.2 |
| `rules.heroes.acquire` | 9.4 | m | 7.6 |
| `rules.heroes.revive.gold_base` | 0.40 | × cost | 6.7 |
| `rules.heroes.revive.gold_per_level` | 0.10 | × cost | 6.7 |
| `rules.heroes.revive.gold_max` | 550 | gold | 6.7 |
| `rules.heroes.revive.time_factor` | 0.65 | × train × L | 6.7 |
| `rules.heroes.revive.time_max` | 110.0 | s | 6.7 |
| `rules.heroes.revive.time_max_train_factor` | 2.0 | × train | 6.7 |
| `rules.heroes.revive.hp` | 1.0 | fraction | 6.7 |
| `rules.heroes.revive.mana_flat` | 100 | mana | 6.7 |
| `rules.heroes.inn_revive.base` | 0.8 | × cost | 6.7 |
| `rules.heroes.inn_revive.per_level` | 0.2 | × cost | 6.7 |
| `rules.heroes.inn_revive.gold_max` | 1105 | gold | 6.7 |
| `rules.heroes.inn_revive.lumber_max` | 260 | lumber | 6.7 |
| `rules.heroes.inn_revive.hp` | 0.5 | fraction | 6.7 |
| `rules.heroes.inn_revive.mana` | 0.0 | fraction | 6.7 |

**`rules.xp`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.xp.unit_kill` | [25, 40, 60, 85, 115, 150, 190, 235, 285, 340] | XP by level 1–10 | 6.3 |
| `rules.xp.hero_kill` | [100, 120, 160, 220, 300, 400, 500, 600, 700, 800] | XP by level 1–10 | 6.3 |
| `rules.xp.summon_factor` | 0.5 | × | 6.3 |
| `rules.xp.creep_factor` | [0.8, 0.7, 0.6, 0.5, 0.0] | × by hero level 1, 2, 3, 4, 5+ | 6.3 |
| `rules.xp.share_radius` | 18.75 | m | 6.4 |
| `rules.xp.no_hero_in_range` | "lost" | "lost" or "all_heroes" | 6.4 |
| `rules.xp.single_hero_bonus` | [0.0, 0.15, 0.30] | × by tier 1–3 | 6.4 |
| `rules.xp.max_level_takes_share` | false | — | 6.4 |
| `rules.xp.structure_kills_give_xp` | false | — | 6.3 |
| `rules.xp.deny_gives_xp` | false | — | 6.3 |

**`combat`** (existing object; changed or new fields marked ✱)

| Field | Value | Unit | § |
|---|---|---|---|
| `combat.armor_k` | 0.06 | — | 7.3 |
| `combat.neg_armor_base` ✱ | 0.94 | — | 7.3 |
| `combat.attack_types` ✱ | ["blade", "pierce", "siege", "arcane", "heroic", "pure", "spell"] | — | 7.1 |
| `combat.armor_types` ✱ | ["light", "medium", "heavy", "fortified", "hero", "unarmored", "adamant"] | — | 7.1 |
| `combat.types.<attack>.<armor>` ✱ | §7.2 matrix (49 numbers) | × | 7.2 |
| `combat.spell_ignores_armor_value` ✱ | true | — | 7.3 |
| `combat.spell_immune_multiplier` ✱ | {"arcane": 0.0, "spell": 0.0} | × | 7.2 |
| `combat.spectral_multiplier` ✱ | 1.66 | × | 7.2 |
| `combat.attack_speed_clamp` ✱ | [0.2, 5.0] | × | 7.5 |
| `combat.move_speed_clamp` ✱ | [2.34, 6.25] | m/s | 7.10 |
| `combat.move_speed_hard_max` ✱ | 8.16 | m/s | 7.10 |
| `combat.range_buffer` ✱ | 2.5 | m | 7.5 |
| `combat.facing_tolerance` ✱ | 0.35 | rad | 7.5 |
| `combat.structure_target_penalty` ✱ | 6.0 | m | 7.6 |
| `combat.splash_friendly_fire` ✱ | false | — | 7.8 |
| `combat.evasion_stacking` ✱ | "max" | — | 7.4 |
| `combat.crit_stacking` ✱ | "max" | — | 7.4 |
| `combat.proc_mode` ✱ | "random" | "random" or "prd" | 2.3 |
| `combat.attack_reveal_radius` ✱ | 1.5 | m | 14.3 |
| `combat.attack_reveal_time` ✱ | 1.0 | s | 14.3 |
| `combat.defaults.acquire` | 8.0 | m | 7.6 |
| `combat.defaults.leash` | 14.0 | m | 7.6 |
| `combat.defaults.damage_point` | 0.4 | s | 7.5 |
| `combat.defaults.backswing` | 0.4 | s | 7.5 |
| `combat.defaults.turn_rate` ✱ | 9.0 | rad/s | 7.5 |
| `combat.defaults.cast_point` ✱ | 0.3 | s | 6.5 |
| `combat.defaults.cast_backswing` ✱ | 0.5 | s | 6.5 |
| `combat.defaults.corpse_decay` | 8.0 | s | 10.8 |
| `combat.defaults.structure_decay` | 4.0 | s | 8 |
| `combat.defaults.help_radius` | 6.0 | m | 7.6 |
| `combat.defaults.alert_interval` | 8.0 | s | 17.3 |
| `combat.defaults.food_max` ✱ | *removed* → `rules.economy.food_cap` | | 4.4 |

**`upkeep`** (existing array; labels become string keys)

| Field | Value |
|---|---|
| `upkeep[0]` | `{"food": 0, "gold_factor": 1.0, "label": "upkeep_none"}` → UI "Upkeep 0 %" |
| `upkeep[1]` | `{"food": 51, "gold_factor": 0.7, "label": "upkeep_low"}` → UI "Upkeep 30 %" |
| `upkeep[2]` | `{"food": 81, "gold_factor": 0.4, "label": "upkeep_high"}` → UI "Upkeep 60 %" |

**`rules.regen`, `rules.status`, `rules.items`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.regen.organic_hp` | 0.25 | HP/s | 9 |
| `rules.regen.mechanical_hp` | 0.0 | HP/s | 9 |
| `rules.regen.structure_hp` | 0.0 | HP/s | 9 |
| `rules.regen.caster_mana` | 0.65 | mana/s | 9 |
| `rules.regen.start_mana` | 75 | mana | 9 |
| `rules.status.same_buff` | "refresh" | — | 10.1 |
| `rules.status.same_aura` | "highest" | — | 10.3 |
| `rules.status.dot_interval` | 1.0 | s | 10.1 |
| `rules.status.aura_refresh` | 0.5 | s | 10.3 |
| `rules.status.aura_linger` | 2.0 | s | 10.3 |
| `rules.status.fade_time` | 1.0 | s | 11 |
| `rules.status.grounded_speed_factor` | 0.5 | × | 12.3 |
| `rules.status.liftoff_time` | 0.5 | s | 12.3 |
| `rules.items.pickup_range` | 1.0 | m | 6.8 |
| `rules.items.give_range` | 1.5 | m | 6.8 |
| `rules.items.recall_channel` | 3.0 | s | 6.8 |
| `rules.items.recall_radius` | 6.0 | m | 6.8 |
| `rules.items.recall_max_units` | 11 | units (+ hero) | 6.8 |

**`rules.daynight`, `rules.vision`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.daynight.day_length` | 480.0 | s | 13 |
| `rules.daynight.dawn` | 6.0 | hour | 13 |
| `rules.daynight.dusk` | 18.0 | hour | 13 |
| `rules.daynight.sight_transition` | 3.2 | s | 13 |
| `rules.vision.unit` | [21.9, 12.5] | m | 14.2 |
| `rules.vision.worker` | [12.5, 9.4] | m | 14.2 |
| `rules.vision.structure` | [14.0, 9.4] | m | 14.2 |
| `rules.vision.cap` | 28.1 | m | 14.2 |
| `rules.vision.fog_cell` | 1.0 | m | 14.1 |
| `rules.vision.fog_update` | 0.1 | s | 14.1 |
| `rules.vision.cliffs_block_upward` | true | — | 14.3 |
| `rules.vision.trees_block_sight` | true | — | 14.3 |
| `rules.vision.tree_occluder_levels` | 2 | cliff levels | 14.3 |
| `rules.vision.flyers_ignore_occluders` | true | — | 12.2 |
| `rules.vision.structure_ghosts` | true | — | 14.1 |
| `rules.vision.shared_allied_vision` | true | — | 14.1 |
| `rules.vision.fly_height_default` | 3.5 | m | 12.1 |

**`rules.creeps`, `rules.neutral`**

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.creeps.acquire` | 3.9 | m | 15.1 |
| `rules.creeps.acquire_caster` | 5.0 | m | 15.1 |
| `rules.creeps.acquire_guard` | 6.0 | m | 15.1 |
| `rules.creeps.notice_factor` | 1.5 | × acquire | 15.1 |
| `rules.creeps.guard_build_radius` | 12.0 | m | 15.1 |
| `rules.creeps.tower_give_up` | 2.0 | s | 15.1 |
| `rules.creeps.retarget_closer` | 3.0 | m | 15.1 |
| `rules.creeps.ignore_idle_flyers` | true | — | 15.1 |
| `rules.creeps.leash` | 18.75 | m | 15.2 |
| `rules.creeps.give_up_time` | 10.0 | s | 15.2 |
| `rules.creeps.return_regen` | 0.02 | max HP/s | 15.2 |
| `rules.creeps.return_invulnerable` | false | — | 15.2 |
| `rules.creeps.sleep_stagger` | 6.0 | s | 15.3 |
| `rules.creeps.wake_trade_radius` | 10.0 | m | 15.3 |
| `rules.creeps.hardy_level` | 6 | level | 10.2 |
| `rules.creeps.hardy_spell_factor` | 0.7 | × | 10.2 |
| `rules.creeps.hardy_control_factor` | 0.5 | × | 10.2 |
| `rules.creeps.pure_level` | 7 | level | 7.1 |
| `rules.creeps.camp_color_levels` | [10, 20] | amber from, red from | 15.4 |
| `rules.creeps.bounty` | {"per_level": 4, "base": 2, "rand": 4} | gold | 15.5 |
| `rules.creeps.respawn` | false | — | 15.1 |
| `rules.creeps.sight` | [14.0, 9.0] | m | 14.2 |
| `rules.neutral.use_range` | 7.0 | m | 16 |
| `rules.neutral.sell_factor` | 0.5 | × gold cost | 16 |
| `rules.neutral.stock_per_player` | true | — | 16 |
| `rules.neutral.player_unit_bounty` | false | — | 15.5 |

**`rules.controls`** (rules, not user settings; `Settings` reads these as defaults)

| Field | Value | Unit | § |
|---|---|---|---|
| `rules.controls.max_selection` | 12 | units | 18.3 |
| `rules.controls.control_groups` | 10 | — | 18.3 |
| `rules.controls.shift_queue_max` | 32 | orders | 18.5 |
| `rules.controls.formation_spread` | 8.0 | m | 7.10 |
| `rules.controls.hotkey_preset` | "classic" | "classic" or "grid" | 18.4 |

**`rules.ai.<easy|normal|hard>`** (one object per level; values from §19)

| Field | Easy | Normal | Hard | Unit |
|---|---|---|---|---|
| `think_interval` | 1.0 | 0.5 | 0.5 | s |
| `reaction_delay` | 1.5 | 0.8 | 0.3 | s |
| `apm_cap` | 40 | 90 | 180 | orders/min |
| `build_slack` | 20.0 | 5.0 | 0.0 | s per step |
| `gold_workers` | 4 | 5 | 5 | per mine |
| `lumber_workers` | [3, 5] | [4, 7] | [5, 8] | T1, T2 |
| `tier2_at` (latest T2 start) | 360.0 | 270.0 | 225.0 | s |
| `max_camp` | "green" | "amber" | "red" | — |
| `camp_level_ratio` | 0.8 | 1.2 | 1.5 | × army level |
| `hero_retreat_hp` | 0.25 | 0.35 | 0.35 | fraction |
| `army_retreat_hp` | 0.0 | 0.5 | 0.5 | fraction |
| `attack_food` | 50 | 40 | 30 | food |
| `attack_not_before` | 600.0 | 0.0 | 0.0 | s |
| `punish_creep_range` | 0.0 | 31.0 | 31.0 | m |
| `focus_fire` | "none" | "lowest_hp" | "priority" | — |
| `pull_back_hp` | 0.0 | 0.0 | 0.3 | fraction |
| `buys_items` | false | true | true | — |
| `upkeep_cap_before_push` | 100 | 50 | 50 | food |
| `expand_at` | -1 | 600.0 | 420.0 | s (−1 never) |
| `scout_at` | -1 | -1 | 45.0 | s |
| `use_signature` | false | true | true | — |

**`factions.<id>`** (existing object, extended)

| Field | `kingdom` | `clans` | `sylvan` *(later)* | `deathless` *(later)* |
|---|---|---|---|---|
| `name` | "Brennmark" | "Tormai" | "Glaermere" | "Long Wake" |
| `worker` | `kingdom_hodman` | `clans_yurtwright` | `sylvan_tapster` | `deathless_sexton` |
| `hall` (T1, existing field) | `kingdom_moot_hall` | `clans_shell_hall` | `sylvan_stilt_lodge` | `deathless_wake_barrow` |
| `hall_tiers` | [moot_hall, walled_burg, crown_burg] | [shell_hall, banner_shell, sun_gong_shell] | [stilt_lodge, lantern_lodge, amber_lodge] | [wake_barrow, long_barrow, grand_barrow] |
| `altar` | `kingdom_oath_hall` | `clans_naming_stones` | `sylvan_calling_pier` | `deathless_cenotaph` |
| `supply` | `kingdom_croft` (+7) | `clans_home_yurt` (+10) | `sylvan_stilt_larder` (+10) | `deathless_columbarium` (+10) |
| `lumber_drop` | [hall tiers, `kingdom_timber_yard`] | [hall tiers, `clans_casting_pit`] | [hall tiers, `sylvan_resinworks`] | [hall tiers, `deathless_ossuary`] |
| `start_units` | {`kingdom_hodman`: 5} | {`clans_yurtwright`: 5} | {`sylvan_tapster`: 5} | {`deathless_sexton`: 5} |
| `start_gold` / `start_lumber` | 500 / 150 | 500 / 150 | 500 / 150 | 500 / 150 |
| `recall_item` | `item_homeward_horn` | `item_homeward_felt` | `item_lake_whistle` | `item_coin_for_the_ferry` |
| `lumber_per_trip` | 10 | 15 | 8 | 10 |
| `chop_interval` | 0.8 | 0.9 | 1.0 | 0.8 |
| `fells_trees` | true | true | false | true |
| `workers_per_tree` | 0 (no limit) | 0 | 1 | 0 |
| `max_builders` | 3 | 1 | 2 | 2 |
| `extra_builder_rate` | 0.6 | 0.0 | 0.5 | 0.5 |

Hall, supply and building ids for `sylvan` and `deathless` follow the display names in their doc (only the T1 hall ids are written there yet).
Hall-tier ids are written with the faction prefix in data (`kingdom_walled_burg`, …).

### 20.3 Target JSON (the `rules` object plus changed parts; paste-ready)

```json
{
  "rules": {
    "match": {"start_hour": 8.0, "hero_tokens": 1, "twinked_heroes": 1, "start_units_idle": true,
              "main_mine_search_radius": 31.25, "cripple_reveal_time": 120.0, "defeat_rule": "no_structures", "game_speed": 1.0},
    "economy": {"gold_per_trip": 10, "mine_dwell": 1.0, "mine_occupancy": 1, "mine_gold_main": 12000,
                "mine_gold_expansion": 8000, "mine_low_warning": 1500, "hall_mine_gap": 6.0, "lumber_per_tree_default": 50,
                "food_cap": 100, "upkeep_rounding": "floor", "upkeep_taxed_income": ["mine", "bounty", "item_sale", "ability"],
                "build_pay": "on_start", "build_start_hp": 0.1, "build_cancel_refund": 0.75, "train_cancel_refund": 1.0,
                "research_cancel_refund": 1.0, "production_queue": 7, "shift_train_count": 5, "repair_cost_factor": 0.3,
                "repair_time_factor": 1.5, "repair_autocast_range": 8.0, "switch_resource_discards_load": true,
                "supply_stall_advisory": 8.0},
    "heroes": {"max": 3, "slots_by_tier": [1, 2, 3], "unique_types": true, "cost_gold": 425, "cost_lumber": 100, "food": 5,
               "train_time": 55.0, "inn_cost_lumber": 135, "level_cap": 10,
               "xp_levels": [0, 200, 500, 900, 1400, 2000, 2700, 3500, 4400, 5400],
               "skill_points_start": 1, "skill_points_per_level": 1, "rank_levels": [1, 3, 5], "ultimate_level": 6,
               "base_hp": 100, "base_hp_regen": 0.25, "base_mana_regen": 0.01, "str_hp": 25, "str_hp_regen": 0.05,
               "agi_armor": 0.3, "agi_attack_speed": 0.02, "int_mana": 15, "int_mana_regen": 0.05, "primary_damage": 1,
               "attribute_rounding": "floor", "control_duration_factor": 0.5, "inventory_slots": 6,
               "sight": [28.1, 12.5], "acquire": 9.4,
               "revive": {"gold_base": 0.4, "gold_per_level": 0.1, "gold_max": 550, "time_factor": 0.65, "time_max": 110.0,
                          "time_max_train_factor": 2.0, "hp": 1.0, "mana_flat": 100},
               "inn_revive": {"base": 0.8, "per_level": 0.2, "gold_max": 1105, "lumber_max": 260, "hp": 0.5, "mana": 0.0}},
    "xp": {"unit_kill": [25, 40, 60, 85, 115, 150, 190, 235, 285, 340],
           "hero_kill": [100, 120, 160, 220, 300, 400, 500, 600, 700, 800],
           "summon_factor": 0.5, "creep_factor": [0.8, 0.7, 0.6, 0.5, 0.0], "share_radius": 18.75,
           "no_hero_in_range": "lost", "single_hero_bonus": [0.0, 0.15, 0.3], "max_level_takes_share": false,
           "structure_kills_give_xp": false, "deny_gives_xp": false},
    "regen": {"organic_hp": 0.25, "mechanical_hp": 0.0, "structure_hp": 0.0, "caster_mana": 0.65, "start_mana": 75},
    "status": {"same_buff": "refresh", "same_aura": "highest", "dot_interval": 1.0, "aura_refresh": 0.5, "aura_linger": 2.0,
               "fade_time": 1.0, "grounded_speed_factor": 0.5, "liftoff_time": 0.5},
    "items": {"pickup_range": 1.0, "give_range": 1.5, "recall_channel": 3.0, "recall_radius": 6.0, "recall_max_units": 11},
    "daynight": {"day_length": 480.0, "dawn": 6.0, "dusk": 18.0, "sight_transition": 3.2},
    "vision": {"unit": [21.9, 12.5], "worker": [12.5, 9.4], "structure": [14.0, 9.4], "cap": 28.1, "fog_cell": 1.0,
               "fog_update": 0.1, "cliffs_block_upward": true, "trees_block_sight": true, "tree_occluder_levels": 2,
               "flyers_ignore_occluders": true, "structure_ghosts": true, "shared_allied_vision": true,
               "fly_height_default": 3.5},
    "creeps": {"acquire": 3.9, "acquire_caster": 5.0, "acquire_guard": 6.0, "notice_factor": 1.5, "guard_build_radius": 12.0,
               "tower_give_up": 2.0, "retarget_closer": 3.0, "ignore_idle_flyers": true, "leash": 18.75, "give_up_time": 10.0,
               "return_regen": 0.02, "return_invulnerable": false, "sleep_stagger": 6.0, "wake_trade_radius": 10.0,
               "hardy_level": 6, "hardy_spell_factor": 0.7, "hardy_control_factor": 0.5, "pure_level": 7,
               "camp_color_levels": [10, 20], "bounty": {"per_level": 4, "base": 2, "rand": 4}, "respawn": false,
               "sight": [14.0, 9.0]},
    "neutral": {"use_range": 7.0, "sell_factor": 0.5, "stock_per_player": true, "player_unit_bounty": false},
    "controls": {"max_selection": 12, "control_groups": 10, "shift_queue_max": 32, "formation_spread": 8.0,
                 "hotkey_preset": "classic"},
    "ai": {
      "easy":   {"think_interval": 1.0, "reaction_delay": 1.5, "apm_cap": 40, "build_slack": 20.0, "gold_workers": 4,
                 "lumber_workers": [3, 5], "tier2_at": 360.0, "max_camp": "green", "camp_level_ratio": 0.8,
                 "hero_retreat_hp": 0.25, "army_retreat_hp": 0.0, "attack_food": 50, "attack_not_before": 600.0,
                 "punish_creep_range": 0.0, "focus_fire": "none", "pull_back_hp": 0.0, "buys_items": false,
                 "upkeep_cap_before_push": 100, "expand_at": -1, "scout_at": -1, "use_signature": false},
      "normal": {"think_interval": 0.5, "reaction_delay": 0.8, "apm_cap": 90, "build_slack": 5.0, "gold_workers": 5,
                 "lumber_workers": [4, 7], "tier2_at": 270.0, "max_camp": "amber", "camp_level_ratio": 1.2,
                 "hero_retreat_hp": 0.35, "army_retreat_hp": 0.5, "attack_food": 40, "attack_not_before": 0.0,
                 "punish_creep_range": 31.0, "focus_fire": "lowest_hp", "pull_back_hp": 0.0, "buys_items": true,
                 "upkeep_cap_before_push": 50, "expand_at": 600.0, "scout_at": -1, "use_signature": true},
      "hard":   {"think_interval": 0.5, "reaction_delay": 0.3, "apm_cap": 180, "build_slack": 0.0, "gold_workers": 5,
                 "lumber_workers": [5, 8], "tier2_at": 225.0, "max_camp": "red", "camp_level_ratio": 1.5,
                 "hero_retreat_hp": 0.35, "army_retreat_hp": 0.5, "attack_food": 30, "attack_not_before": 0.0,
                 "punish_creep_range": 31.0, "focus_fire": "priority", "pull_back_hp": 0.3, "buys_items": true,
                 "upkeep_cap_before_push": 50, "expand_at": 420.0, "scout_at": 45.0, "use_signature": true}
    }
  },
  "combat": {
    "armor_k": 0.06,
    "neg_armor_base": 0.94,
    "attack_types": ["blade", "pierce", "siege", "arcane", "heroic", "pure", "spell"],
    "armor_types": ["light", "medium", "heavy", "fortified", "hero", "unarmored", "adamant"],
    "types": {
      "blade":  {"light": 1.0,  "medium": 1.5,  "heavy": 1.0, "fortified": 0.7,  "hero": 1.0, "unarmored": 1.0, "adamant": 0.05},
      "pierce": {"light": 2.0,  "medium": 0.75, "heavy": 0.9, "fortified": 0.35, "hero": 0.5, "unarmored": 1.5, "adamant": 0.05},
      "siege":  {"light": 1.0,  "medium": 0.5,  "heavy": 1.0, "fortified": 1.5,  "hero": 0.5, "unarmored": 1.5, "adamant": 0.05},
      "arcane": {"light": 1.25, "medium": 0.75, "heavy": 2.0, "fortified": 0.35, "hero": 0.5, "unarmored": 1.0, "adamant": 0.05},
      "heroic": {"light": 1.0,  "medium": 1.0,  "heavy": 1.0, "fortified": 0.5,  "hero": 1.0, "unarmored": 1.0, "adamant": 0.05},
      "pure":   {"light": 1.0,  "medium": 1.0,  "heavy": 1.0, "fortified": 1.0,  "hero": 1.0, "unarmored": 1.0, "adamant": 1.0},
      "spell":  {"light": 1.0,  "medium": 1.0,  "heavy": 1.0, "fortified": 1.0,  "hero": 0.7, "unarmored": 1.0, "adamant": 0.5}
    },
    "spell_ignores_armor_value": true,
    "spell_immune_multiplier": {"arcane": 0.0, "spell": 0.0},
    "spectral_multiplier": 1.66,
    "attack_speed_clamp": [0.2, 5.0],
    "move_speed_clamp": [2.34, 6.25],
    "move_speed_hard_max": 8.16,
    "range_buffer": 2.5,
    "facing_tolerance": 0.35,
    "structure_target_penalty": 6.0,
    "splash_friendly_fire": false,
    "evasion_stacking": "max",
    "crit_stacking": "max",
    "proc_mode": "random",
    "attack_reveal_radius": 1.5,
    "attack_reveal_time": 1.0,
    "defaults": {"acquire": 8.0, "leash": 14.0, "damage_point": 0.4, "backswing": 0.4, "turn_rate": 9.0,
                 "cast_point": 0.3, "cast_backswing": 0.5, "corpse_decay": 8.0, "structure_decay": 4.0,
                 "help_radius": 6.0, "alert_interval": 8.0}
  },
  "upkeep": [
    {"food": 0, "gold_factor": 1.0, "label": "upkeep_none"},
    {"food": 51, "gold_factor": 0.7, "label": "upkeep_low"},
    {"food": 81, "gold_factor": 0.4, "label": "upkeep_high"}
  ],
  "factions": {
    "kingdom": {"name": "Brennmark", "worker": "kingdom_hodman", "hall": "kingdom_moot_hall",
                "hall_tiers": ["kingdom_moot_hall", "kingdom_walled_burg", "kingdom_crown_burg"],
                "altar": "kingdom_oath_hall", "supply": "kingdom_croft",
                "lumber_drop": ["kingdom_moot_hall", "kingdom_walled_burg", "kingdom_crown_burg", "kingdom_timber_yard"],
                "start_units": {"kingdom_hodman": 5}, "start_gold": 500, "start_lumber": 150,
                "recall_item": "item_homeward_horn", "lumber_per_trip": 10, "chop_interval": 0.8, "fells_trees": true,
                "workers_per_tree": 0, "max_builders": 3, "extra_builder_rate": 0.6},
    "clans":   {"name": "Tormai", "worker": "clans_yurtwright", "hall": "clans_shell_hall",
                "hall_tiers": ["clans_shell_hall", "clans_banner_shell", "clans_sun_gong_shell"],
                "altar": "clans_naming_stones", "supply": "clans_home_yurt",
                "lumber_drop": ["clans_shell_hall", "clans_banner_shell", "clans_sun_gong_shell", "clans_casting_pit"],
                "start_units": {"clans_yurtwright": 5}, "start_gold": 500, "start_lumber": 150,
                "recall_item": "item_homeward_felt", "lumber_per_trip": 15, "chop_interval": 0.9, "fells_trees": true,
                "workers_per_tree": 0, "max_builders": 1, "extra_builder_rate": 0.0}
  }
}
```

The `sylvan` and `deathless` entries follow the §20.2 table when those factions enter production.

### 20.4 Migration from today's file

1. Rename attack ids `hero` → `heroic` and `chaos` → `pure`; add the `adamant` armour column (`data/factions.json`,
   `tests/unit/test_combat.gd` lines 51 and 57, and the "data ids" convention line in `kingdom.md`, `clans.md`, `sylvan-and-deathless.md`
   and `neutrals.md`).
2. Move `combat.defaults.food_max` to `rules.economy.food_cap`.
3. Replace `placeholder_a` / `placeholder_b` with `kingdom` / `clans` once their unit defs exist (clans §11 data mapping).
4. Upkeep `label` becomes a string key; the HUD maps it to "Upkeep 0 % / 30 % / 60 %".
5. `src/world/day_night.gd`: read `DAY_LENGTH`, `DAWN`, `DUSK` and `START_HOUR` from `Defs.rules` (keep the constants as fallbacks).
6. `src/autoload/settings.gd`: `max_selection` defaults to `rules.controls.max_selection`.
7. `Defs`: load `rules`, validate that every unit `attack.type` and `armor_type` is in the lists, and that Classic hotkeys are unique per card.

---

## 21. Fidelity ledger (WC3 → Vibecraft)

| Rule | WC3 (TFT ladder) | Vibecraft | Status |
|---|---|---|---|
| Start | Hall + 5 workers, 500 / 150, 08:00, 1 hero token, free return scroll | Same (our recall items) | Kept |
| Mine | 12,500, warn 1,500 | 12,000 / 8,000, warn 1,500 | **Δ** shorter games |
| Mining | 10 per trip, 5 workers saturate | Same (6 m gap, 1 s dwell) | Kept (values tuned to reproduce) |
| Lumber | 10 per trip (race-dependent), ≈ 50 per tree | 8–15 per faction, 50 per tree | Kept shape |
| Food / upkeep | 100; 50 / 80 thresholds; 100 / 70 / 40 % | Same | Kept |
| Upkeep on bounty and sales | Yes | Yes | Kept |
| Tiers | 3 hall tiers; hero slots 1 / 2 / 3 | Same | Kept |
| Heroes | 3 max, unique, 425 / 100, 55 s, 5 food | Same | Kept |
| Inn heroes | 425 / 135, instant | Same | Kept |
| XP | Level table, kill tables, creep 80 / 70 / 60 / 50 / 0 % | Same (wiki.gg creep values) | Kept |
| XP range | ≈ 1200 gu (unverified) | 18.75 m; no-hero kills give nothing | Kept (flag) |
| Single-hero bonus | +15 % / +30 % | Same | Kept |
| Attributes | STR 25 HP / 0.05; AGI 0.3 / 2 %; INT 15 / 0.05; primary +1 | Same | Kept |
| Revive | Altar formula, cap 550 g / 110 s; inn 50 % HP, 0 mana | Same | Kept |
| Damage matrix | TFT (Pierce vs Heavy 90 later) | Same numbers, our names | Kept, renamed |
| Armour formula | 0.06; 2 − 0.94^(−A) | Same | Kept |
| Attack phases | Damage point, backswing, cooldown; cancels | Same | Kept |
| Uphill miss | Version-dependent | None (vision only) | **Δ** clarity |
| Splash friendly fire | Unverified | Off | **Δ** design |
| Day / night | 480 s, 240 / 240, sight 1400 / 800, hero 1800 / 800 | Same in metres | Kept |
| Fog | Black mask, fog, visible; 0.4 s, 128 gu cells | Same states; 0.1 s, 1 m cells | Kept (finer) |
| LOS | Cliffs block upward, trees block, flyers ignore | Same | Kept |
| Creeps | Sleep at night, camp acts as one, no respawn, colour bands | Same; plus day-active families (neutrals) | Kept + twist |
| Creep leash / bounty | Unverified | 18.75 m, 10 s; 4L + 2 + rand(0–4) | Our values |
| Creep return | Commonly invulnerable | Not invulnerable, 2 % HP/s | **Δ** (neutrals) |
| Cripple reveal | 120 s | 120 s | Kept |
| Defeat | All structures lost | Same | Kept |
| Selection | 12 | 12 | Kept |
| Shift-queue | Limited (≈ 35, unverified) | 32 | ≈ Kept |
| Hotkeys | Letter mnemonics; grid in later versions | Classic (letters) default + Grid | Kept |
| Neutral use range | "45" (likely 450 gu) | 7.0 m | Kept (flag) |
| Construction pay / cancel | Unverified | On start / 75 % | Our values |

---

## 22. Verification tests (headless, `tests/unit/`)

| Test | Asserts |
|---|---|
| `test_economy_saturation` | Standard start (6 m gap): 5 workers average 9.5–10.5 gold/s over 120 s; 4 workers ≤ 9.0; 6 workers ≤ 5 workers + 3 % |
| `test_upkeep` | Deliveries yield 10 / 7 / 4 at 50 / 51 / 81 food; bounty is taxed; lumber is not |
| `test_food_stall` | Training waits when food is short and resumes when a supply building completes |
| `test_xp` | Unit-kill and hero-kill tables; creep factor by hero level; split between 2 heroes; out of range gets 0; level 10 excluded; single-hero bonus |
| `test_hero_attributes` | Wheel Marshal levels 1 / 5 / 10 match kingdom §6.2 derived values |
| `test_revive_costs` | Altar and inn tables for levels 1–10 (§6.7) |
| `test_damage_matrix` | All 49 multipliers; armour table (§7.3); spell ignores armour value; pure ignores type |
| `test_attack_cancel` | An order before the damage point deals no damage and refunds the cooldown; backswing cancels instantly |
| `test_day_night` | Dusk at 200 s, dawn at 440 s; unit sight 21.9 → 12.5 m over 3.2 s |
| `test_fog_los` | Low-ground viewer cannot see the plateau; high ground sees low; trees block; flyers see over both |
| `test_creep_leash` | A pulled camp returns past 18.75 m; give-up after 10 s; sleeping creeps are never auto-acquired |
| `test_end_conditions` | Last structure destroyed → defeat; hall lost → revealed at +120 s |
| `test_determinism` | The existing state-hash test, extended with an AI-vs-AI 5-minute match |

---

## 23. Open questions, tuning flags and required follow-up edits

**Flags (decide or verify before data entry)**

1. **XP with no hero in range:** this spec says *lost*; research and neutrals §1.6 say heroes elsewhere still get it. Verify in WC3 and set
   `rules.xp.no_hero_in_range`.
2. **Altar revive mana:** research says 100 mana; full mana is the other candidate. `rules.heroes.revive.mana_flat`.
3. **Construction:** pay on start vs on placement; cancel refund 75 % vs 100 %.
4. **Neutral use range** 7.0 m (from the probable ×10 notation). **Shop stock** per player vs shared.
5. **Speed floor** 2.34 m/s (150 gu/s) is from memory; it limits slows on slow units.
6. **Spell damage ignores armour value** (from memory). If wrong, set `combat.spell_ignores_armor_value = false`.
7. **Attack reveal** 1.5 m / 1.0 s and **damage point / backswing** class defaults: tune from recorded clips (research README Q6).
8. **Structure sight** default 14.0 / 9.4 m: the faction docs give 14 m (kingdom), 18 / 12.5 (clans hall) and 12.5 / 9.4 (clans others).
9. **Selection cap** 12 vs 24 (research README Q7); this spec keeps 12 and the 12-slot grid.

**Inconsistencies found in sibling docs (to fix there)**

10. **Footprint units:** `clans.md` §7 lists footprints in metres ("8×8 m", "4×4 m", "2×2 m"), while `kingdom.md` and `architecture.md` use
    0.5 m cells (hall 10×10 cells = 5 m). One convention (cells) must be chosen before data entry; the hall size itself (5 m vs the visual
    doc's 8 m) is an open art question.
11. **Hall–mine gap:** `gameplay-mechanics.md` §13.1 says 4 m; `kingdom.md` §10 says 6–8 m; this spec sets **6.0 m** (§3.3).
12. **Selection cap:** `gameplay-mechanics.md` §13.1 says 24; the code and this spec say 12.
13. **Data ids:** the faction and neutral docs list attack ids `hero` and `chaos`; this spec renames them `heroic` and `pure` (§20.4).
14. **Caster start mana:** kingdom says 40 % of max; clans says 75. The global default is 75; kingdom units set `start_mana` per def.

**Code follow-ups** are listed in §20.4. `architecture.md` §8 (trees block sight), §10 (type ids) and §11 (hotkey presets) need a line each
when the code changes, in the same commit (architecture rule).
