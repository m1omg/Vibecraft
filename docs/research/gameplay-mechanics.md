# WC3-style gameplay mechanics reference (for Vibecraft)

Purpose: a numeric reference for the mechanics that give Warcraft III (2002/2003, Blizzard) its feel. It ends with a
**recommended rule set for our vertical slice** (1v1 vs AI, 2 original factions, about 8 units and 2 heroes each, creep camps).

Conventions used in this document:

- **WC3 numbers** are in WC3 "game units" (gu). Our architecture (`docs/architecture.md`) uses 1 m per Godot unit,
  a 2 m terrain tile and 0.5 m pathing cells. A WC3 terrain tile is 128 gu and a WC3 pathing cell is 32 gu, so
  **1 m = 64 gu** gives an exact mapping. Every slice number below is also given in metres, using **÷64**.
- Values are **The Frozen Throne (TFT) / ladder-classic** unless marked otherwise. Reforged-era patches (1.30–2.0)
  have changed some values; the per-unit numbers here come from Blizzard's classic.battle.net pages.
- **Sources.** Liquipedia blocked direct fetching (HTTP 403, then a 429 rate-limit page). Liquipedia facts here come
  from search-result excerpts and are marked "(Liquipedia, excerpt)". Everything else comes from pages fetched
  directly: Blizzard's classic.battle.net, warcraft.wiki.gg, Hive Workshop, and Blizzard's own `Blizzard.j` script.
- **(unverified)** marks a value from memory or community lore that I could not confirm in a fetched source.
  Treat it as a design starting point, not a fact.
- The web-search budget ran out near the end of the research, so a few items stay unverified. They are listed in §14.
- **Fact-check pass (2026-10-16).** An adversarial review re-fetched the primary sources and corrected or flagged
  the items listed in §15. Liquipedia's MediaWiki API (`liquipedia.net/warcraft/api.php`) was reachable
  between rate limits, so the Upkeep, Daytime, Gold Mine and Experience pages were read directly.

---

## 1. Starting conditions (melee)

These come from Blizzard's `Blizzard.j`, the script that sets up every melee map (fetched from the `lep/jassdoc` repo):

| Constant | Value | Note |
|---|---|---|
| `bj_MELEE_STARTING_GOLD_V1` / `_LUMBER_V1` | **500 gold / 150 lumber** | TFT (V1). Reign of Chaos (V0) used 750 / 200. |
| `bj_MELEE_STARTING_TOD` | **08:00** | Each game starts in the morning. Dawn is 06:00 (`bj_TOD_DAWN`) and dusk is 18:00 (`bj_TOD_DUSK`). |
| `bj_MELEE_STARTING_HERO_TOKENS` | **1** | The first hero costs no gold or lumber, only food. |
| `bj_MELEE_HERO_LIMIT` | **3** | Maximum heroes per player. |
| `bj_MELEE_HERO_TYPE_LIMIT` | **1** | Only one of each hero type. |
| `bj_MELEE_MAX_TWINKED_HEROES_V1` | **1** | Only the first hero gets the free Town Portal scroll (`'stwp'`). |
| `bj_MELEE_MINE_SEARCH_RADIUS` | 2000 gu (31 m) | How far from the start location the script looks for the main mine. |
| `bj_MELEE_CRIPPLE_TIMEOUT` | 120 s | A player who has lost every town hall is revealed after 120 s. |
| Camera defaults | distance **1650**, FOV **70°**, angle of attack **304°** (a 56° downward pitch), far Z 5000 | Useful for our camera rig. |

Starting units (`MeleeStartingUnits*`). Units are placed on a 64 gu spacing between the hall and the mine:

- Human: Town Hall + **5** Peasants.
- Orc: Great Hall + **5** Peons.
- Undead: Necropolis + **3** Acolytes + **1** Ghoul + a Haunted Gold Mine already built.
- Night Elf: Tree of Life (already entangling the mine) + **5** Wisps.

## 2. Economy

### 2.1 Gold

- **Gold mine capacity:** 12,500 by default. The game warns at **1,500 remaining** (warcraft.wiki.gg, Hive Workshop).
  Individual maps vary the amount per mine (unverified).
- **Gold per trip:** **10** (Peasant "Gold Capacity 10", warcraft.wiki.gg).
- **Saturation:** **5 workers per mine** reaches maximum efficiency when the hall is built as close as allowed.
  This has been the rule since Patch 1.13. A Human or Orc hall placed far from the mine needs more than 5.
  Undead (Acolytes haunt the mine) and Night Elves (Wisps sit inside the entangled mine) use exactly 5; extra
  workers are wasted.
- **Time inside the mine:** about 1 s per trip (unverified).
  Practical income from one saturated mine is roughly 8–10 gold/s (unverified). Liquipedia's Gold Mine page says
  "each worker needs 5 seconds to mine 10 gold". That is about 2 gold/s per worker, or about 10 gold/s for 5
  workers, which agrees with this estimate. The same page says Humans and Orcs have no hard cap on how many
  workers can be assigned to a mine; Undead and Night Elves are capped at 5.
- **How each race mines:**
  - Human and Orc workers walk gold back to the hall.
  - Undead Acolytes stand around a haunted mine.
  - Wisps enter an entangled mine, so gold is never carried.

  This asymmetry is cheap to build and gives factions flavour (see §11).

### 2.2 Lumber

| Worker | Lumber per trip | Notes |
|---|---|---|
| Human Peasant | 10 → 20 → 30 | Improved Lumber Harvesting (+10, 100 g, 60 s, needs Keep) and Advanced (+10, 200 g, 75 s, needs Castle), per Blizzard's Lumber Mill page; requirements may differ in later patches. Gathers 1 lumber per hit. |
| Orc Peon | 10 | |
| Undead Ghoul | 20 | Gathers 2 lumber per hit. Ghouls are also the Undead's basic melee unit. |
| Night Elf Wisp | 5 | Does not use up trees. |
| Goblin Shredder (mercenary) | 200 | Bought at a neutral building. |

- Lumber per tree and the chop interval: about 50 lumber per tree (unverified).
- Delivery: Humans and Orcs return lumber to the hall or a lumber mill, Undead to a Graveyard. Wisps harvest in
  place but still return lumber to an Ancient.

### 2.3 Food (supply) and the cap

- **Food cap: 100** in TFT and **90** in Reign of Chaos.

| Building | Food provided | Cost | Build time |
|---|---|---|---|
| Human Town Hall / Keep / Castle | 12 | 385 g / 205 l (hall) | 180 s |
| Human Farm | **6** | 80 g / 20 l | 35 s |
| Orc Great Hall | 10 | 385 g / 185 l | 150 s |
| Orc Burrow | 10 (unverified; the fetched page gave no number) | 160 g / 40 l | 50 s |
| Undead Ziggurat | **10** | 150 g / 50 l | 50 s |
| Night Elf Moon Well | **10** | 180 g / 40 l | 50 s |

- Typical unit food costs:

  | Unit type | Food | Example |
  |---|---|---|
  | Worker | 1 | |
  | Basic melee | 2–3 | Footman 2 |
  | Ranged | 3 | Rifleman 3 |
  | Heavy tier-3 unit | 4–7 | Knight 4; Frost Wyrm and Mountain Giant 7 |
  | Hero | 5 | |

- A unit's **level** (which sets the XP it is worth) is usually its food cost. Exceptions exist: Gryphon Rider is
  level 5 but costs 4 food; Mountain Giant is level 6 but costs 7 food.

### 2.4 Upkeep (the signature WC3 economic rule)

| Tier | Food used (TFT) | Gold received per trip | Reign of Chaos bands |
|---|---|---|---|
| No Upkeep | 0–50 | **100 %** | 0–40 |
| Low Upkeep | 51–80 | **70 %** | 41–70 |
| High Upkeep | 81–100 | **40 %** | 71–90 |

- Upkeep taxes **gold only**, never lumber. It is applied to each gold delivery: a 10-gold trip yields 7 at low
  upkeep and 4 at high upkeep (the per-trip rounding is unverified).
  - Liquipedia's Upkeep page adds that gold from creep bounties, item sales and Transmute is also reduced by
    upkeep, although the floating gold text does not show the reduction.
- **Blizzard's stated intent** (classic.battle.net Upkeep page): "Upkeep has been included to improve tactical
  management for players while fostering a more aggressive style of gameplay" and "to focus the game on smaller
  numbers of units."
  - warcraft.wiki.gg's copy of the same text adds: players "turtle far less", it creates real decisions about army
    size, big armies make heroes matter less, and "High Upkeep is MEANT to be very punishing."
- Lead artist Rob McNaughton has said upkeep was partly a workaround for memory limits in early 3D (PCGamesN).
- The HUD shows the current tier as a label next to food ("No Upkeep" / "Low Upkeep" / "High Upkeep").
  A warning sounds when the tier changes (unverified).

## 3. Tech tiers and typical costs and times

### 3.1 Main-hall tiers

The town hall is upgraded in place, in three tiers:

| Tier | Human (cost / time) | HP (Human) | Unlocks |
|---|---|---|---|
| T1 | Town Hall 385 g / 205 l, 180 s | 1500 | Basic units; **hero #1** |
| T2 | Keep: +320 g / 210 l, 140 s | 2000 | Mid-tier units and casters; **hero #2**; level-2 upgrades |
| T3 | Castle: +360 g / 210 l, 140 s | 2500 | Top-tier units; **hero #3**; level-3 upgrades |

The other races use the same three-tier pattern:

- Orc: Great Hall → Stronghold → Fortress.
- Undead: Necropolis → Halls of the Dead → Black Citadel.
- Night Elf: Tree of Life → Tree of Ages → Tree of Eternity.

**Single-hero XP bonus:** a player with only one hero (dead heroes count) gets +15 % XP at T2 and +30 % at T3.
Patch 1.17 raised this from +10 % / +20 %.

### 3.2 Typical build and train times and costs (Human examples, classic.battle.net)

| Thing | Cost | Food | Time |
|---|---|---|---|
| Worker (Peasant) | 75 g | 1 | 15 s |
| Wisp | 60 g | 1 | 14 s |
| T1 melee (Footman) | 135 g | 2 | 20 s |
| Ghoul | 120 g | 2 | 18 s |
| T1 ranged (Rifleman) | 205 g / 30 l | 3 | 26 s |
| T3 heavy (Knight) | 245 g / 60 l | 4 | 45 s |
| Hero | 425 g / 100 l (first one free) | 5 | 55 s |
| Farm | 80 g / 20 l | — | 35 s |
| Barracks | 160 g / 60 l | — | 60 s |
| Altar (hero building) | 180 g / 50 l | — | 60 s |
| Hall T1 → T2 → T3 | 385/205 → 320/210 → 360/210 | — | 180 → 140 → 140 s |

Weapon and armor upgrades: three levels each, researched at the Blacksmith. Level 2 needs T2 and level 3 needs T3.

| Upgrade line | Level 1 | Level 2 (needs T2) | Level 3 (needs T3) | Effect |
|---|---|---|---|---|
| Weapons (Human swords) | 100 g / 50 l, 60 s | 175 g / 175 l, 75 s | 250 g / 300 l, 90 s | +damage per level |
| Armor | 125 g / 75 l, 60 s | 150 g / 175 l, 75 s | 175 g / 275 l, 90 s | +2 armor per level |

Exact armor costs vary between patches and sources.

Building HP and armor: buildings have **Fortified** armor and armor values of 5–8 (from 5 base to 8 fully upgraded).
Halls have 1500–2500 HP; farms and supply buildings 500–600 HP; production buildings 1500 HP.

## 4. Heroes

### 4.1 Limits and acquisition

- At most **3 heroes**, and **1 of each type**.
- Hero 2 needs a T2 hall and hero 3 needs a T3 hall.
- The first hero is **free** apart from 5 food, and comes with **1 Town Portal scroll** and 1 skill point.
  Later heroes cost **425 g / 100 l** and 5 food, and take **55 s** to train.
- Tavern (neutral) heroes can be hired by any race. They cost more lumber: 135 instead of 100 since Patch 1.15.
  The buying unit must be within 45 gu of the Tavern.

### 4.2 XP and levels

**XP needed (cumulative):**

| Level | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| Total XP | 200 | 500 | 900 | 1400 | 2000 | 2700 | 3500 | 4400 | 5400 |

The formula is: XP for level L = XP for level L−1 + 100 × L. The **level cap is 10**.

**XP for killing a non-hero unit, by the victim's level:**

| Victim level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| XP | 25 | 40 | 60 | 85 | 115 | 150 | 190 | 235 | 285 | 340 |

- **XP for killing an enemy hero,** by the victim hero's level: 100, 120, 160, 220, 300, 400, 500, 600, 700, 800.
- **Summoned units** give 50 % XP.
- **Creep XP factor (TFT),** by the killing hero's level:

  | Hero level | 1 | 2 | 3 | 4 | 5+ |
  |---|---|---|---|---|---|
  | warcraft.wiki.gg | 80 % | 70 % | 60 % | 50 % | **0 %** |
  | classic.battle.net (older TFT) | 80 % | 70 % | 62 % | 55 % | **0 %** |

  So a hero must fight players to pass level 5. This is the core of the "creep early, fight late" rhythm.

- **Sharing:** XP from a kill is **split evenly among your heroes in range**. A hero outside the range gets nothing.
  If no hero is nearby, XP still goes to your heroes. The sharing radius is a gameplay constant whose value I could
  not confirm; about 1200 gu is a guess (unverified).
- **No XP** when a tower or Ancient lands the killing blow, or for destroying buildings that cannot attack.

### 4.3 Abilities

- Each hero has **4 abilities**: **3 normal abilities with 3 ranks each**, learnable at hero levels **1 / 3 / 5**,
  and **1 ultimate with 1 rank**, learnable at level **6**.
- The hero gets 1 skill point per level and starts with 1 point. 10 levels give 10 points: 9 for the normal ranks
  and 1 for the ultimate. Every hero ends up fully skilled at level 10.
- Example kit shape (Paladin):
  - Holy Light: heal, 65 mana, 5 s cooldown.
  - Devotion Aura: passive armor aura.
  - Divine Shield: invulnerability, 35/50/65 s cooldown.
  - Resurrection: ultimate, 200 mana, 240 s cooldown.

  Shape to reuse: **one active spell, one aura or passive, one defensive or utility spell, and one big ultimate**.

### 4.4 Attributes (classic TFT values)

| Attribute | Per point | Notes |
|---|---|---|
| **Strength** | +25 max HP, +0.05 HP regen per second | HP = 100 + 25 × STR |
| **Agility** | +0.30 armor, +2 % attack speed | Armor = −2 + 0.3 × AGI (plus base armor) |
| **Intelligence** | +15 max mana, +0.05 mana regen per second | Mana = 15 × INT |
| **Primary attribute** | +1 attack damage | Each hero has one: STR, AGI or INT. |

- Example: Paladin at level 1 has STR 22 / AGI 13 / INT 17, which gives 650 HP and 255 mana. He gains +2.7 / +1.5 /
  +1.8 per level, reaching 1250 HP and 495 mana at level 10.
- Base regeneration:
  - HP: 0.25 per second for Human, Orc and neutral heroes.
  - Night Elf heroes: 0.5 per second, at night only.
  - Undead heroes: 2.0 per second, on Blight only.
- Base mana regeneration: 0.01 per second, so mana comes almost entirely from INT.
- Movement-speed cap: 400 gu/s by default, for **all** units, not only heroes. This is the "Movement – Unit Speed –
  Maximum" gameplay constant; map makers can raise it to the engine's hard limit of 522 (Hive Workshop).
- Heroes have 6 inventory slots and leave no corpse.
- Heroes have built-in **magic resistance**: spell damage is reduced by 30 %, and negative spells last a shorter time.
- Patches 1.30 through 2.x may have changed these per-point values. I found no patch note that does (unverified).

### 4.5 Revival

- **Altar:** costs gold only, no lumber.
  - Cost = original cost × (0.40 + 0.10 × (level − 1)), capped at **550 gold**.
  - Time = training time × level × 0.65, capped at 2 × the training time and **110 s**.
  - Example: a level-1 hero takes 55 × 0.65 ≈ 36 s.
  - The hero returns with full HP, 100 mana and its items.
- **Tavern instant revive:**
  - It costs more and returns the hero at **50 % HP and 0 mana**.
  - The sources disagree on price. Warcraft Wiki: 80 % of the base cost + 20 % per level, capped at 1,400 g / 350 l.
    classic.battle.net: capped at 1,105 g / 260 l. Patch 1.10 tripled the lumber cost.

## 5. Creeps (neutral hostile camps)

- **Creep levels** run from 1 to 10.
  - Level 6+ creeps have hero-style magic resistance.
  - Level 7+ creeps act like strong melee AI and deal **Chaos** damage (since Patch 1.03).
- **Camp colours** on the minimap are set by the camp's total level (Blizzard's melee-map guidelines):

  | Colour | Total camp level |
  |---|---|
  | **Green** | 1–9 |
  | **Orange** | 10–19 |
  | **Red** | 20+ (Blizzard rarely goes above 23) |

- Creeps guarding a neutral building are usually total level 9–15.
- Blizzard noticed red camps were seldom attacked and later made them easier.
- **Item drops, by total camp level** (Blizzard melee guidelines; the bands overlap at the edges as written):

  | Camp level | Drops |
  |---|---|
  | 3–8 | L1 permanent or power-up |
  | 8–11 | L2 permanent, charged or power-up |
  | 11–14 | L1 + L2 |
  | 14–17 | L1 + L3 permanent or charged |
  | 18–21 | L2 + L4 |
  | 21–23 | L2 + L5 |
  | 23–26 | L2 + L6 |
  | 26–29 | L1 + L3 + L7 artifact |

  - Items are assigned to camps consistently, so players can guess the drop from how a camp looks.
  - Usually one specific creep in the camp carries the item. Players often kill just that creep and leave.
  - Example map (Lost Temple):
    - green camps drop L1 power-ups and L2 permanents;
    - orange camps drop L2 power-ups and L4 permanents;
    - red camps drop L5–6 items.
- **Aggro:**
  - Auto-acquire range is usually **200 or 500 gu**; 200 is common, so creeps do not pull from far away.
  - A camp acts as one unit: if any member is hit, the whole camp responds.
  - Creeps chase only a limited distance and then return home; the leash distance was not confirmed.
  - Since Patch 1.10, creeps that keep being attacked eventually give up and return to their start point.
  - Creeps run from towers below 60 % HP.
  - Creeps attack buildings placed next to their camp, but do not seek out finished buildings.
  - Creeps that are not fighting ignore flying units unless ordered to attack-move.
- **Night:**
  - Nearly all creeps **sleep at night** and show an animated "Z".
  - Your units do not auto-attack sleeping creeps, so night is a safe time to scout.
  - Creeps wake when attacked, when something is built too close, or when a nearby neutral building is used.
  - These never sleep: golems, sea elementals, adult dragons, bandits, most demonic and undead creeps.
- **No respawn:** killed creeps do not come back. A few creeps reincarnate once.
- **Bounty:** each creep killed shows a gold amount above its corpse. The amount per level was not confirmed;
  2–40 gold scaling with level is a guess (unverified).
- **Design note (Blizzard guidelines):**
  - Put an easy camp near each start and harder camps toward contested ground.
  - Keep camps off main roads.
  - Mix melee, ranged and caster creeps; avoid camps that are all ranged or all air.
  - Guards at gold mines are deliberately **not** set to "camp mode". In camp mode, players could fast-expand or
    build towers next to the camp without the creeps attacking the building under construction.
  - Every other camp **is** set to camp mode, so it only fights when a player chooses to engage it.

## 6. Day/night cycle

- One full cycle is **480 game seconds: 240 s of day (06:00–18:00) and 240 s of night**
  (Liquipedia Daytime page, read via its API in the fact-check). That is 20 game seconds per game hour.
  The name of the underlying gameplay constant is unverified.
  - The same Liquipedia excerpt also says "each hour = 40 real seconds". That contradicts 480 s, possibly because
    of game-speed scaling. Use 480 s.
  - Games start at 08:00, so the **first dusk comes 200 s into the match**.
- **Sight drops at night.** Each unit has separate day and night sight values:

  | Unit | Day sight | Night sight |
  |---|---|---|
  | Most units | 1400 | 800 |
  | Heroes | 1800 | 800 |
  | Peasant | 800 | 600 |
  | Wisp | 1000 | 750 |

  - The cap is 1800 for both.
  - Sight changes **over about 3.2 s**, stepping every 0.4 s, rather than snapping.
- The day/night switch is marked by an indicator orb (8 segments), a wolf howl at dusk, and the minimap vision
  visibly shrinking.
- Race hooks:
  - Night Elf units regenerate only at night and can Shadowmeld (stationary invisibility at night).
  - Night Elves can research Ultravision to keep full sight at night.
  - Moon Wells regenerate at night.

## 7. Combat model

### 7.1 Attack type vs armor type (TFT; percent of damage dealt)

| Attack ↓ / Armor → | Light | Medium | Heavy | Fortified | Hero | Unarmored |
|---|---|---|---|---|---|---|
| **Normal** | 100 | **150** | 100 | 70 | 100 | 100 |
| **Pierce** | **200** | 75 | 100 (wiki: 90) | 35 | 50 | 150 |
| **Siege** | 100 | 50 | 100 | **150** | 50 | 150 |
| **Magic** | 125 | 75 | **200** | 35 | 50 | 100 |
| **Chaos** | 100 | 100 | 100 | 100 | 100 | 100 |
| **Spells** | 100 | 100 | 100 | 100 | 70 | 100 |
| **Hero** | 100 | 100 | 100 | 50 | 100 | 100 |

**What each attack type is for:**

| Attack type | Used by | Notes |
|---|---|---|
| Normal | Melee units | |
| Pierce | Archers and gunners | |
| Siege | Artillery | |
| Magic | Most casters and some air units | Deals 66 % extra damage to ethereal units and none to magic-immune units. |
| Chaos | High-level creeps and big summons | |
| Hero | Hero attacks | |

**Which units wear each armor type:**

| Armor type | Typical wearers |
|---|---|
| Light | Most air units |
| Medium | Ranged units and workers |
| Heavy | Melee units |
| Fortified | Buildings |
| Hero | Heroes |
| Unarmored | Casters |

- Divine armor (special cases): 5 % damage from everything except Chaos, and 50 % from spells.
- Reign of Chaos rotated Light, Medium and Heavy (for example, Normal did 150 % to Light).
  The table above is the version players know.
- **Spells vs heroes:** spells do 30 % less damage to heroes (since Patch 1.15).

### 7.2 Armor value formula

- Positive armor: damage reduction = **0.06 × A / (1 + 0.06 × A)**.
  - Armor 1 gives 5.7 % reduction, armor 5 gives 23 %, and armor 10 gives 37.5 %.
- Negative armor: damage multiplier = **2 − 0.94^(−A)**. Armor −10 gives +46 % damage taken.
- Order of operations: first the attack-type multiplier, then the armor-value reduction.

### 7.3 Attack timing

- Every attack has three timers: the **damage point**, then the **backswing**, then the **cooldown**.
  - The damage point is the wind-up before the hit lands.
  - The backswing is the animation tail after the hit. It can be interrupted, which is the basis of
    "animation cancelling".
  - The cooldown is the weapon timer.
- If the attacker is interrupted (moved or stopped) **before the damage point**, the attack is cancelled.
- The animation timers scale with attack speed.
- Classic WC3 attack speed is said to be capped at +400 % and −80 % (unverified; no source was fetched).
  How the timers combine into DPS is debated in the community.
- Typical cooldowns:

  | Unit | Cooldown |
  |---|---|
  | Ghoul | 1.30 s |
  | Footman | 1.35 s |
  | Knight | 1.4 s |
  | Rifleman | 1.5 s |
  | Peasant | 2.0 s |
  | Paladin at level 1 | 2.2 s (AGI shortens it) |

- Typical damage points are 0.3–0.6 s and backswings 0.3–0.7 s (unverified).

### 7.4 Typical stat ranges

| Stat | Range | Examples |
|---|---|---|
| Move speed (gu/s) | 190 (slow) / 270 (average) / 350 (fast); default cap **400** for all units, engine max **522** | Peasant 190, Footman 270, Knight 350, Ghoul 270 → 350 upgraded |
| Melee range | short, about 90–128 gu (unverified) | warcraft.wiki.gg's Footman infobox lists range "9" (×10-scaled); classic.battle.net just says "Melee" |
| Ranged attack range | 400–600 gu | Rifleman 400, or 600 with Long Rifles (75 g / 125 l, needs T2) |
| Siege range | about 1000–1150 gu (unverified) | |
| Sight (day / night) | 1400 / 800 for units, 1800 / 800 for heroes | Cap 1800 |
| HP, T1 | 420 (Footman), 535 (Rifleman), 340 (Ghoul) | |
| HP, T3 | 835 (Knight) | |
| Hero HP | 650 at level 1, about 1250 at level 10 | |
| Average damage | 12.5 (Footman), 21 (Rifleman), 34 (Knight), 29 (Paladin at level 1) | |
| Armor | 0–5 base; +6 from full upgrades | Footman 2→8, Knight 5→11 |

- **Feel takeaway:** HP is high relative to damage. A Footman needs about 30+ hits to kill another Footman,
  so fights last 10–30 s. That gives players time to micro: pull hurt units back, focus fire, and use spells.
  This is central to the WC3 feel.

### 7.5 Collision and pathing

- The pathing grid uses **32 gu cells**; fog and terrain use **128 gu cells**.
- Unit collision acts like a radius rounded to grid cells:

  | Collision size | Cells occupied |
  |---|---|
  | 0–15 | 1×1 |
  | 16–31 | 2×2 |
  | 32–47 | 3×3 |
  | 48+ | 4×4 (the default maximum) |

  - The Footman's wiki stats block lists collision size 31.
  - In the cited Hive test, sizes from 48 up to 1024 all occupy 4×4 cells; the poster says the maximum can be
    raised in Gameplay Constants. The "engine cap of about 200" figure is unverified.
- Buildings use painted pathing textures on the 32 gu grid rather than a radius.
- Formation movement: a group given a move order on open ground travels in formation at the slowest unit's speed.
  Alt+right-click moves at full speed with no formation.

## 8. Vision, fog of war, terrain

- **Three visibility states:**
  - black mask (never explored);
  - fog (explored; buildings shown as last seen);
  - visible.
- Fog updates **every 0.4 s** on a **128 gu grid**. A unit leaving vision is fogged at once.
- **Line of sight:**
  - Trees and cliffs block it.
  - Each cliff level is 128 gu high. A medium tree blocks to cliff level 2 (occluder height 230).
  - Units on low ground **cannot see up a cliff**.
  - Flying units ignore occluders.
- High-ground miss chance: some versions use a chance-to-miss when attacking uphill (unverified). We recommend
  **vision-only** high-ground advantage.
- **Shared vision** between allies is an alliance setting; in team melee games it is on.
- Attacking reveals the attacker for a short time ("Fog Reveal Radius – Attacking Unit"). Its value was not
  confirmed (unverified).
- A player who loses every main hall is **revealed to all after 120 s** (`bj_MELEE_CRIPPLE_TIMEOUT`).

## 9. Controls and command semantics (from Blizzard's "Special Commands" page)

- **Selection:**
  - Drag-box to select.
  - Shift+click adds or removes units.
  - Double-click, or Ctrl+click, selects every unit of that type on screen.
  - A selection holds **12 units** in classic WC3 (Blizzard's Special Commands page: "the selection limit").
  - A 24-unit selection in a later Reforged patch is reported only by an Icy Veins headline. The article returned
    HTTP 403 to the fact-checker, so which patch added it, and whether it is live on ladder, is unverified.
    In 2018 warcraft.wiki.gg recorded Blizzard saying the 12-unit cap would remain "at least initially".
- **Subgroups:** Tab and Shift+Tab cycle the active subgroup, whose abilities fill the command card. Clicking a
  portrait in the selection panel selects that subgroup.
- **Control groups:**
  - **Ctrl+0–9** assigns a group and **0–9** recalls it.
  - Pressing the number twice centres the camera on the group.
  - Buildings can be grouped. For example, group the hall, then press 1 and the train hotkey to queue a worker.
  - Towers cannot be grouped with other building types.
- **Hero hotkeys:** F1–F3 select your heroes; pressing again centres the camera.
- **Other hotkeys:** idle worker is F8 or `~`; Backspace cycles your town halls; Space jumps to the last alert.
- **Smart right-click** depends on what you click:

  | Right-click target | Result |
  |---|---|
  | Ground | Move, in formation |
  | Enemy | Attack |
  | Friendly or neutral unit | Follow; a follower attacks only when its leader does |
  | Mine or tree (with a worker) | Gather |
  | Unfinished friendly building (with a worker) | Help build or repair |
  | Item | Pick up |
  | Neutral shop | Select the shop for buying |
  | Ground or object (with a building selected) | Set the rally point |

- **Explicit orders:** Attack-move (A, then click), Move (M), Stop (S), Hold Position (H), Patrol (P).
  Ability hotkeys are grid letters.
- **Shift-queue:** Shift queues commands (move, attack, patrol, build, gather, load/unload, research and training).
  Blizzard's page says only that "there is a limited number of commands that can be queued"; the figure of 35 is
  unverified. Shift+A on several targets builds a focus-fire list.
- **Autocast:** right-click an ability icon to toggle autocast; a golden animated border shows it is on.
  Typical autocast abilities are heals, buffs, worker repair and a summon's own attack spell.
- **Rally points:** right-click with a production building selected. Workers rallied to a mine or tree start
  gathering when they arrive. The exact patch history of mine/tree rallying is unverified.
- **Inventory:** 6 slots, with numpad hotkeys 7/8, 4/5, 1/2.
- **Display:** hold Alt for health bars; mouse wheel or PgUp/PgDn zooms; Insert/Delete rotates the camera
  temporarily.

## 10. Items, shops and neutral buildings

### 10.1 Items

- Every item has a **level from 1 to 8** and a class (Patch 1.10):

  | Class | How it works | Example |
  |---|---|---|
  | Permanent | Passive while carried | "+6 STR belt", level 4 |
  | Charged | Limited uses; vanishes when empty | |
  | Power-up | Used instantly on pickup | "Tome of +2 STR"; runes are level 0 |
  | Artifact | Level 7+ | |
  | Purchasable | Shop stock | Potions, Town Portal, scrolls |

- Items dropped on the ground show as a **treasure chest**.
- Items can be **sold** to a merchant (since Patch 1.10).
- Shop stock **replenishes** on a per-item timer (unverified).

### 10.2 Neutral buildings

Blizzard's guideline is to use 2–3 types per map, each with equal access for every player.

| Building | Function |
|---|---|
| **Goblin Merchant** | Item shop: potions, scrolls, utility; buys items back |
| **Marketplace** | Random, stronger items that rotate |
| **Tavern** | Neutral heroes for any race; instant hero revive (expensive); never guarded by creeps |
| **Mercenary Camp** | Hire creep-type units; the roster depends on the map tileset |
| **Goblin Laboratory** | Shredder (lumber harvester), Zeppelin (transport), Sappers (suicide demolition), map reveal |
| **Fountain of Health / Mana** | Area regeneration; usually a central, contested landmark |
| Goblin Shipyard, Dragon Roost (TFT) | Ships; dragons |

- Neutral buildings are usually guarded by a total level 9–15 camp. The Tavern is the exception.
- You use a neutral building by having a hero or unit within about 45–60 gu of it.

### 10.3 Race shops

Each race also has its own shop, unlocked by tech (Arcane Vault, Voodoo Lounge, Tomb of Relics, Ancient of Wonders).

## 11. Why WC3 plays differently from StarCraft (design pillars to keep)

1. **Small armies.** Food cap is 100 (StarCraft has 200), units cost more food, and **upkeep** taxes big armies.
   A typical fight is 10–25 units a side, so each unit matters and players notice individual deaths.
2. **Heroes are the army's centre.** They level, gain items and turn fights with spells, auras and ultimates.
   A dead hero gives the enemy a lot of XP, and reviving one costs time and gold.
3. **Creeping is a third side in the game.** Early PvE gives XP (only until level 5), items and gold.
   The map becomes a risk/reward route, and creeping exposes you to a "catch" by the enemy.
4. **High HP-to-damage ratio.** Fights last long enough to micro: focus fire, pull back damaged units, surround,
   bodyblock, and save units with Town Portal scrolls.
5. **Feeding.** Every unit you lose gives enemy heroes XP, so throwing units away has a cost.
6. **Low economic scale.** 5 workers saturate a mine, and expanding is a risky, defended commitment rather than
   constant spreading.
7. **Day/night rhythm.** It changes scouting, creeping (creeps sleep at night) and race strengths.
8. **Tiered town hall.** The hall upgrade is the main tech decision. It gates heroes 2 and 3 and upgrade levels.
9. **Readable, chunky visuals and strong unit voices.** This is presentation rather than rules, but it is part of
   the feel. See `visual-art-direction.md`.

## 12. What we may reuse vs what we must not copy

### 12.1 Fine to reuse: generic mechanics, ideas and systems

Rules, methods of play and game mechanics are not protected by US copyright. 17 U.S.C. §102(b), confirmed on
Cornell LII, excludes "any idea, procedure, process, system, method of operation, concept, principle, or discovery".
The Copyright Office's FL-108 factsheet and an ABA Landslide article make the same point for games; neither could be
re-fetched in the fact-check. **Caveat:** this protects mechanics, not look and feel. US courts have found
infringement where a clone copied a game's visual expression, even though the rules were free to use. The
best-known case is *Tetris Holding v. Xio Interactive* (D.N.J. 2012). That is why §12.2 matters as much as this
list. These are fine to reuse:

- Gold and lumber economy, worker gathering, saturating a mine, food supply, **upkeep tiers**
  (the concept and the numbers).
- Town-hall tier progression; tier-gated hero slots; the hero limit; free first hero.
- Hero levels, the XP curve, 3 normal abilities × 3 ranks plus an ultimate at level 6,
  STR/AGI/INT-style attributes and their formulas, revival at a base building, 6-slot inventories.
- Neutral creep camps, colour-coded difficulty, creep XP decay by hero level, sleeping at night, item drops by
  camp level.
- The attack-type × armor-type matrix, the armor formula, damage point / backswing / cooldown.
- Day/night cycle with reduced night sight; fog of war with black mask and fog; cliffs and trees blocking sight.
- Control groups, smart right-click, shift-queue, autocast toggle, rally points, subgroup Tab, idle-worker key.
- Shops, a mercenary camp, a hero tavern, a healing fountain, town-portal-style recall items.
- Generic archetypes: footman-like line infantry, ranged gunner, healer caster, siege, cavalry, flyer,
  summoner hero, aura hero, and so on.

### 12.2 Must NOT copy: specific expression, trademarks and distinctive presentation

- **Names:**
  - Factions: "Human Alliance", "Orcish Horde", "Undead Scourge", "Night Elf Sentinels".
  - Heroes: Paladin, Archmage, Blademaster, Far Seer, Death Knight, Lich, Demon Hunter, Keeper of the Grove, etc.
  - Units, buildings and abilities: Holy Light, Devotion Aura, Mirror Image, Bladestorm, Death Coil, Starfall,
    Bloodlust, Defend, Haunted Gold Mine, Entangle, Moon Well, Ziggurat, Altar of Kings, etc.
  - Items: Claws of Attack, Boots of Speed, Scroll of Town Portal, Tome of Experience, etc.
  - Neutral buildings: "Goblin Merchant", "Goblin Laboratory".
  - "Warcraft", "Blizzard", "Azeroth", "Lordaeron", lore characters and place names.
- **Exact unit kits and ability combos** that identify a specific WC3 unit or hero. Example: a holy melee hero
  with Holy Light + Devotion Aura + Divine Shield + Resurrection. Mix archetypes in new combinations and give them
  our own numbers.
- **Flavour text, tooltips, unit voice lines** ("Ready to work!", "Zug zug", "Jobs done", and so on), music,
  sound effects, icons, portraits, models, textures, UI art, and the specific HUD frame design.
- **Distinctive trade dress:**
  - Avoid a 1:1 copy of the gargoyle-framed console layout with the same ornament style.
  - Avoid the same race colour schemes paired with the same silhouettes.
  - Avoid the same minimap camp icons.

  A bottom console, a minimap at bottom-left and a command card at bottom-right are generic RTS conventions and
  are fine.
- **Specific map layouts**, such as Lost Temple's exact geometry.

Gray zone: copying the *entire* numeric balance sheet unit-for-unit does not infringe as mechanics, but it makes
the game read as a re-skin. It also clashes with the user's "be creative" brief. Keep the *systems* and give our
own units their own numbers and kits.

## 13. Recommended rule set for the vertical slice

Goal: capture the WC3 rhythm in a 12–20 minute 1v1 against the AI:

- 0–2 min: build up and get the first hero.
- 2–6 min: creep with the hero and a small army, and harass.
- 5–8 min: T2, the second hero, and a push or an expansion.
- 10+ min: a decisive fight.

Faction names below are **placeholders** for the creative-direction doc to rename. Distances are given in gu with
metres in brackets (÷64).

### 13.1 Global constants (`data/factions.json → rules`)

| Rule | Slice value | Rationale |
|---|---|---|
| Start | 1 T1 Hall, 5 workers, **500 gold / 150 lumber**, 08:00 | WC3-proven opening tempo |
| Food cap | **100** | |
| Upkeep | 0–50 → 100 %, 51–80 → 70 %, 81–100 → 40 % (applied per gold delivery, round down) | The core feel |
| Gold mine | Main **12,000**; expansion **8,000**; warn at 1,500 | Slightly below WC3, for shorter games |
| Gold trip | **10 gold**, 1.0 s inside the mine, **one worker inside at a time** | One-at-a-time naturally makes about 5 workers saturate a mine 6–8 m from the hall |
| Hall–mine gap | Hall edge to mine edge about 4 m (≈256 gu) | Target about 8–10 gold/s per saturated mine |
| Lumber | 10 per trip (Faction A) / 15 per trip (Faction B, slower chop); 1 lumber per 0.8 s chop; **50 lumber per tree** | |
| Hero slots | T1: 1, T2: 2 (the slice has 2 heroes per faction; a T3 slot is reserved for later) | |
| Hero cost | First free (5 food) plus a free Recall Scroll; second 425 g / 100 l, 5 food, **55 s** | |
| Hero XP table | 200 / 500 / 900 / 1400 / 2000 / 2700 / 3500 / 4400 / 5400, cap 10 | Keep the WC3 curve |
| Unit-kill XP by victim level | 25 / 40 / 60 / 85 / 115 / 150 / 190 / 235 / 285 / 340 | |
| Hero-kill XP | 100 / 120 / 160 / 220 / 300, then +100 per level | |
| Creep XP factor | Hero level 1: 80 %, 2: 70 %, 3: 60 %, 4: 50 %, 5+: **0 %** | Forces fighting the enemy after level 5 |
| XP share radius | **1200 gu (18.75 m)**, split evenly between heroes | WC3 value unverified; tune |
| Abilities | 3 normal × 3 ranks (hero levels 1/3/5) + 1 ultimate (level 6) | |
| Attributes | STR +25 HP, +0.05 HP/s; AGI +0.3 armor, +2 % attack speed; INT +15 mana, +0.05 mana/s; primary +1 damage | |
| Revive (altar) | Gold = 425 × (0.40 + 0.10 × (L−1)), max 550; time = 55 × L × 0.65, max 110 s; full HP | |
| Day/night | 480 s cycle (240 / 240); dawn 06:00, dusk 18:00; first dusk at 200 s | |
| Sight | Units 1400 / 800 gu (21.9 / 12.5 m) day/night; heroes 1800 / 800 (28.1 / 12.5 m); workers 800 / 600 (12.5 / 9.4 m); sight changes over 3 s | |
| Fog | Black mask + fog + visible; update every 0.2–0.4 s; cliffs block sight upward; trees block sight; no uphill miss chance | |
| Selection | **24** max; 10 control groups; shift-queue up to 32 orders | Design choice. Classic WC3 is 12; a Reforged 24-unit cap is reported but unverified (§9). |
| Corpses/remains | Units leave a corpse for about 8 s (unverified), then the remains decay | Later use for necromancy-style spells |

### 13.2 Damage matrix for the slice

Use our own type names. Values follow the proven TFT matrix (Pierce vs Heavy rounded to 90):

| Attack ↓ / Armor → | Light | Medium | Heavy | Fortified | Hero | Unarmored |
|---|---|---|---|---|---|---|
| **Blade** (≈ Normal) | 100 | 150 | 100 | 70 | 100 | 100 |
| **Pierce** | 200 | 75 | 90 | 35 | 50 | 150 |
| **Siege** | 100 | 50 | 100 | 150 | 50 | 150 |
| **Arcane** (≈ Magic) | 125 | 75 | 200 | 35 | 50 | 100 |
| **Heroic** (hero attacks) | 100 | 100 | 100 | 50 | 100 | 100 |
| **Pure** (big creeps, ultimates) | 100 | 100 | 100 | 100 | 100 | 100 |
| **Spell** (ability damage) | 100 | 100 | 100 | 100 | 70 | 100 |

Armor formula: as in §7.2.

Attack phases:
- damage point 0.3–0.5 s;
- backswing 0.3–0.5 s;
- cooldown measured from the start of the swing (implementation choice);
- moving before the damage point cancels the swing.

### 13.3 Faction A — "Bastion" (placeholder): disciplined, armored, stone and steel; fragile casters; strong towers

Faction economy:
- Workers walk gold and lumber back to the hall.
- Supply building: **+6 food**, 80 g / 20 l, 35 s.
- Hall: +12 food.

| # | Role (placeholder name) | Tier / building | Cost (g / l / food) | Time | HP | Armor (type) | Attack | Cooldown | Range gu (m) | Speed gu/s (m/s) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Worker "Delver" | T1 Hall | 75 / 0 / 1 | 15 s | 220 | 0 (Medium) | Blade 5–6 | 2.0 | melee | 190 (3.0) | Builds, repairs (autocast), carries 10 gold / 10 lumber |
| A2 | Line infantry "Shieldbearer" | T1 Barracks | 135 / 0 / 2 | 20 s | 420 | 2 (Heavy) | Blade 11–14 | 1.35 | melee | 270 (4.2) | Research **Shield Wall**: +3 armor to itself and adjacent Shieldbearers while not moving |
| A3 | Ranged "Arbalester" | T1 Barracks (+ Smithy) | 200 / 30 / 3 | 26 s | 500 | 0 (Medium) | Pierce 18–24 | 1.5 | 500 (7.8) → 650 (10.2) with an upgrade | 270 (4.2) | Hits air and ground |
| A4 | Caster "Lamplighter" | T2 Sanctum | 140 / 20 / 2 | 28 s | 320 | 0 (Unarmored) | Arcane 8–10 | 1.75 | 600 (9.4) | 270 (4.2) | **Mend** (autocast, 3 mana, heals 15 HP/s); at rank 2, **Lantern Ward**: a ward that reveals invisible units and lights a small area at night |
| A5 | Siege "Ram-Ballista" | T2 Workshop | 190 / 70 / 3 | 35 s | 450 | 2 (Heavy) | Siege 55–65, splash 40/120 gu | 3.0 | 1050 (16.4), minimum 250 (3.9) | 220 (3.4) | Ground only |
| A6 | Cavalry "Lancer" | T2 Barracks (needs T2) | 245 / 60 / 4 | 40 s | 820 | 4 (Heavy) | Blade 28–36 | 1.4 | melee | 350 (5.5) | **Charge**: the first hit after 2 s of movement deals +50 % damage |
| A7 | Flyer "Kite-Rider" | T2 Aerie | 260 / 60 / 4 | 40 s | 650 | 1 (Light) | Arcane 30–40 | 2.0 | 450 (7.0) | 320 (5.0) | Flying; ground targets only |
| A8 | Anti-air "Skyhook Team" | T1 Workshop | 160 / 40 / 3 | 26 s | 380 | 1 (Medium) | Pierce 20–26 vs air ×1.5 | 1.6 | 600 (9.4) | 270 (4.2) | **Grapnel**: pulls a flyer to the ground for 6 s |

Faction A buildings:

| Building | Cost (g / l) | Time | Notes |
|---|---|---|---|
| Hall T1 | 385 / 205 | 180 s | |
| Hall T2 | +320 / 210 | 120 s | |
| Supply | 80 / 20 | 35 s | +6 food |
| Barracks | 160 / 60 | 60 s | |
| Hero Altar | 180 / 50 | 60 s | |
| Smithy | 140 / 60 | 60 s | Weapon and armor upgrades, 2 levels in the slice |
| Sanctum | 150 / 100 | 60 s | Needs T2 |
| Workshop | 140 / 140 | 60 s | |
| Aerie | 150 / 120 | 60 s | Needs T2 |
| Watchtower | 30 / 20 → Guard Tower +70 / 50 | | Pierce 20–24, range 700 (10.9 m) |

### 13.4 Faction B — "Wildborn" (placeholder): beasts and spirits; fewer, tougher units; regeneration; living siege

Faction economy:
- Gold is walked back like Faction A's. Workers carry 15 lumber and chop more slowly; trees are not felled until
  they are empty.
- Supply building: "Totem Lodge", **+10 food**, 150 g / 40 l, 50 s.
- Hall: +10 food.
- All Faction B units **regenerate an extra 0.5 HP/s at night**. This is a day/night hook distinct from the Night
  Elf version.

| # | Role (placeholder name) | Tier / building | Cost (g / l / food) | Time | HP | Armor (type) | Attack | Cooldown | Range gu (m) | Speed gu/s (m/s) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Worker "Gatherer" | T1 Hall | 70 / 0 / 1 | 15 s | 240 | 0 (Medium) | Blade 6–7 | 2.0 | melee | 200 (3.1) | Carries 10 gold / 15 lumber; **Burrow-in**: hides inside the supply building and throws stones (base defense) |
| B2 | Bruiser "Tusker" | T1 War Lodge | 160 / 0 / 3 | 24 s | 650 | 1 (Heavy) | Blade 17–21 | 1.6 | melee | 270 (4.2) | **Gore**: 15 % chance of +40 % damage |
| B3 | Ranged "Spear-Hurler" | T1 War Lodge | 140 / 20 / 2 | 22 s | 380 | 0 (Medium) | Pierce 14–18 | 1.6 | 450 (7.0) | 300 (4.7) | Fast and fragile skirmisher |
| B4 | Caster "Hexweaver" | T2 Spirit Hut | 150 / 25 / 2 | 30 s | 300 | 0 (Unarmored) | Arcane 9–11 | 1.75 | 550 (8.6) | 270 (4.2) | **Thornsnare**: roots for 3 s, 60 mana; **Fervor**: +25 % attack speed for 30 s (autocast) |
| B5 | Living siege "Boulderback" | T2 Beast Pen | 210 / 60 / 4 | 40 s | 700 | 1 (Heavy) | Siege 55–70, splash 40/120 gu | 3.5 | 900 (14.1) | 220 (3.4) | Ground only; regenerates 1 HP/s |
| B6 | Raider "Stagrunner" | T2 Beast Pen | 180 / 40 / 3 | 32 s | 560 | 1 (Medium) | Blade 16–20 | 1.5 | melee | 380 (5.9) | **Bola**: knocks a flyer to the ground or slows a ground unit by 50 % for 4 s |
| B7 | Heavy "Ironbark Colossus" | T2 Beast Pen (needs T2) | 340 / 100 / 6 | 50 s | 1300 | 2 (Heavy) | Blade 24–32 | 2.0 | melee | 240 (3.75) | **Taunt** (radius 300 gu); takes 50 % less damage from Pierce (an exception to the matrix) |
| B8 | Flyer "Duskwing" | T2 Roost | 230 / 50 / 3 | 35 s | 480 | 0 (Light) | Pierce 20–26 | 1.75 | 400 (6.25) | 350 (5.5) | Flying; hits air and ground; **stealthed at night while not attacking** |

Faction B buildings mirror Faction A's roles:

| Building | Cost (g / l) | Notes |
|---|---|---|
| Great Lodge (hall) | 385 / 185 | T1 → T2 +300 / 200 |
| War Lodge | 180 / 50 | |
| Spirit Altar | 180 / 50 | |
| War Forge | 150 / 50 | |
| Spirit Hut | 160 / 80 | |
| Beast Pen | 140 / 140 | |
| Roost | 150 / 120 | |
| Thorn Watch tower | 120 / 40 | Pierce, range 700 |

### 13.5 Heroes (2 per faction; original kits built from generic archetypes)

All heroes:
- cost 425 g / 100 l when not free; 5 food; 55 s to train;
- 6 item slots; Heroic attack type; Hero armor type; base speed 280–300 gu/s;
- abilities learnable at levels 1/3/5 (normal) and 6 (ultimate).

**A-H1 "Vanguard Marshal"** (primary STR, melee). STR 22 (+2.6/level), AGI 14 (+1.4), INT 15 (+1.6),
base damage 22–30, base armor 2.

| Ability | Effect | Mana | Cooldown |
|---|---|---|---|
| **Shield Rush** (active) | Dashes 400/500/600 gu in a line, dealing 50/90/130 damage and stunning 1 s | 75 | 12 s |
| **War Banner** (aura) | Allies within 900 gu deal +10/20/30 % damage | — | — |
| **Second Wind** (self) | Heals 150/275/400 HP over 6 s and gives +3 armor | 50 | 20 s |
| **Last Stand** (ultimate) | For 8 s, allies within 600 gu cannot drop below 1 HP | 150 | 150 s |

**A-H2 "Storm Magister"** (primary INT, ranged 600, missile attack). STR 15 (+1.6), AGI 13 (+1.0),
INT 21 (+3.0).

| Ability | Effect | Mana | Cooldown |
|---|---|---|---|
| **Arc Bolt** | Lightning that bounces to 3/4/5 targets for 85/125/170 damage, −15 % per bounce | 90 | 9 s |
| **Static Ward** | Places a ward that slows enemies within 300 gu by 20/30/40 % for 20 s | 60 | 15 s |
| **Wellspring** (aura) | Allies regenerate +0.5/1.0/1.5 mana/s | — | — |
| **Tempest** (ultimate) | Channels 6 s, dealing 40 damage/s in a 500 gu radius and briefly revealing the area | 175 | 180 s |

**B-H1 "Beast Chieftain"** (primary AGI, melee). STR 20 (+2.0), AGI 20 (+2.4), INT 13 (+1.3).

| Ability | Effect | Mana | Cooldown |
|---|---|---|---|
| **Pounce** | Leaps up to 700 gu, deals 60/100/140 damage and slows 40 % for 2 s | 70 | 10 s |
| **Pack Call** | Summons 1/2/2 wolves (level 2/2/3, 60 s duration; summons give 50 % XP when killed) | 100 | 30 s |
| **Feral Instinct** (passive) | 10/15/20 % chance to deal ×2 damage | — | — |
| **Primal Form** (ultimate) | Transforms for 45 s: +500 HP, +20 damage, melee splash | 150 | 160 s |

**B-H2 "Bone Seer"** (primary INT, ranged 600). STR 16 (+1.8), AGI 12 (+1.0), INT 21 (+2.8).

| Ability | Effect | Mana | Cooldown |
|---|---|---|---|
| **Hex Bolt** | Deals 75/130/185 damage and slows attack speed by 25 % for 4 s | 85 | 8 s |
| **Mending Totem** | A totem heals allies within 450 gu for 6/10/14 HP/s for 15 s | 80 | 22 s |
| **Soul Leech** | Channels 4 s, draining 25/40/55 HP per second | 75 | 12 s |
| **Ancestral Host** (ultimate) | Summons 4 spectral warriors (Pure damage, 30 s) | 175 | 180 s |

### 13.6 Creeps and the slice map

The slice map is 96×96 tiles (192 m).

**Creep roster (6 types):**

| Creep | Level | Damage type | Notes |
|---|---|---|---|
| "Briar Hound" | 1 | Blade | |
| "Moss Shaman" | 2 | Arcane | Casts heal |
| "Bog Lurker" | 3 | Pierce | |
| "Cave Brute" | 4 | Blade | Stun on hit |
| "Hill Ogre-kin" | 5 | Blade | Hero-type armor |
| "Ancient Rootwarden" | 7 | Pure | Never sleeps |

**Camp layout:**

| Camp | Count | Total level | Drop | Location |
|---|---|---|---|---|
| Green | 4 | 4–8 | L1 power-up / consumable | 2 per base, inside the natural path |
| Orange | 2 | 12–16 | L1 + L2 permanent | At the 2 expansions |
| Red | 1 | 20–22 | L2 + L4 permanent | Guarding the center **Merchant** |

**Behaviour:**
- Acquire range: **250 gu (3.9 m)** at day; asleep at night except the Ancient Rootwarden.
- Leash: return home when pulled **> 1200 gu (18.75 m)** from the camp centre, or after 10 s with no damage dealt.
  While returning, creeps are invulnerable and regenerate fully. This is a common RTS/MOBA convention
  (WC3 numbers unverified).
- Gold bounty per creep: **level × 4 + random(0–5)** (design proposal).

**Neutral buildings:**
- 1 central **Merchant**: potions, a Recall Scroll, boots, and a ward-revealing dust.
- 1 **Healing Fountain** on a side path: +2 % HP/s within 500 gu.
- A Tavern or Mercenary Camp can come later.

**Items (about 12):**
- Minor healing potion (+250 HP) and mana potion (+150 mana);
- Recall Scroll (teleport to your hall after 3 s);
- Boots (+50 speed);
- +3 STR, +3 AGI and +3 INT charms (L2);
- +4 damage gloves (L2);
- +2 armor ring (L2);
- regen pendant (L3);
- tomes: +1 attribute, or +100 XP (power-ups, L1–2);
- an L4 "Crown of the Rootwarden" (+4 all attributes) as the red-camp prize.

### 13.7 AI opponent baseline (for testing the rules)

The AI follows a simple scripted plan:

1. Get the worker count to 5 on gold and 3–4 on lumber.
2. Build the Altar first and get hero #1 by about 1:30.
3. Mix 2 Barracks units with the hero and creep the green camps in order of distance.
   Retreat when the hero drops below 35 % HP or the army falls below 50 % of its total HP.
4. Upgrade to T2 at about 4:30, train hero #2 and start the caster or siege building.
5. Attack when army food reaches 40 or more (deliberately staying in No Upkeep), or when an enemy hero is seen
   creeping within 2000 gu (31 m).

## 14. Open questions and items to verify later

- **Mining:** exact mine dwell time and occupancy rules in WC3; how the per-trip upkeep rounding works.
- **Trees and creeps:** lumber per tree; creep leash distance; creep gold bounty table; the XP-share radius.
- **Combat:** the high-ground miss chance in current patches; default damage point and backswing per unit class;
  the attack-reveal radius and duration.
- **Liquipedia cross-check:** confirm against Liquipedia (Upkeep, Experience, Daytime, Armor, Damage Calculation)
  when it is reachable. The "each hour = 40 real seconds" Liquipedia excerpt needs reconciling with the 480 s cycle.
- **Reforged-era drift:** any changes since 1.32 to attribute values or the selection cap (24 is reported by
  Icy Veins, which was unreachable in the fact-check).
- **Controls:** the actual shift-queue limit; attack-speed min and max caps; the maximum collision size.

## 15. Fact-check log (2026-10-16)

**Confirmed against fetched primary sources:**

- `Blizzard.j` constants:
  - starting gold and lumber, V1 500/150 and V0 750/200;
  - start time 08:00, dawn 6.00, dusk 18.00;
  - hero limit 3, one per type, 1 free hero token, 1 twinked hero in V1;
  - mine search radius 2000, cripple timeout 120 s;
  - camera distance 1650, FOV 70, angle of attack 304, far Z 5000;
  - 64 gu unit spacing and the per-race starting units, including the Night Elf instant entangle and the Undead
    haunted mine.
- classic.battle.net Upkeep: 0–50 / 51–80 / 81–100 food gives 100 / 70 / 40 % gold. warcraft.wiki.gg gives the
  Reign of Chaos bands as 0–40 / 41–70 / 71–90.
- classic.battle.net Heroes:
  - the XP table and the hero-kill XP table;
  - the unit-kill formula F(x) = F(x−1) + 5x + 5 with F(1) = 25;
  - creep XP of 80/70/62/55/0 %;
  - the single-hero bonus of 15/30 % (warcraft.wiki.gg dates it to patch 1.17, up from 10/20 %);
  - the revive formula (0.40 base factor, 0.10 per level, 0.65 time factor, 2.0 time cap, maximum 550 g and 110 s);
  - the Tavern maximum of 1105 g / 260 l, returning the hero with 0 mana and 50 % HP;
  - the attribute values: STR +25 HP / +0.05 regen, INT +15 mana / +0.05 regen, AGI +0.3 armor / +2 % attack rate.
- classic.battle.net Armor and Weapon Types:
  - the whole TFT matrix in §7.1;
  - the armor formulas (armor 1 ≈ 5.7 %, armor −10 = +46.1 %);
  - Magic deals +66 % to ethereal units.
- warcraft.wiki.gg:
  - Pierce vs Heavy is 90 % (a later value);
  - Divine armor takes 5 % from attacks and 50 % from spells;
  - since patch 1.03, creeps of level 7+ deal Chaos damage and level 6+ have hero magic resistance.
- Unit pages:
  - Footman: 135 g, 2 food, 20 s, 420 HP, 12.5 average damage, 1.35 s cooldown, sight 1400/800, speed 270.
  - Knight: 245/60, 4 food, 45 s, 835 HP, 34 average damage, 1.4 s, speed 350.
  - Rifleman: 205/30, 3 food, 26 s, 535 HP, 21 average damage, 1.5 s, range 400 → 600.
  - Peasant: 75 g, 15 s, 220 HP, 2.0 s, sight 800/600, speed 190.
  - Wisp: 60 g, 14 s, sight 1000/750.
  - Ghoul: 120 g, 18 s, 340 HP, 1.30 s, harvests 20 lumber.
  - Paladin: 650 HP / 255 mana at level 1, 1250 / 495 at level 10, cooldown 2.2 s, mana regeneration 0.01.
  - Paladin abilities: Holy Light 65 mana / 5 s; Divine Shield 35/50/65 s; Resurrection 200 mana / 240 s.
- Building pages: Town Hall, Keep, Castle, Farm, Barracks, Altar, Great Hall, Orc Burrow, Ziggurat and Moon Well
  costs, times, HP and food all match. The Blacksmith upgrade costs match §3.2.
- Blizzard melee guidelines: green 1–9, orange 10–19, red 20+; the item-drop table; neutral-building guards at
  level 9–15; red camps were made easier.
- Gold mine: 12,500 gold, with a warning at 1,500 (warcraft.wiki.gg; classic.battle.net Resources).
- Tavern: neutral heroes cost 135 lumber since 1.15; the purchase range is 45 gu since 1.15 (down from 60).
- Spells do 30 % less damage to heroes since 1.15.
- Hive vision guide: 128 gu fog cells; 0.4 s fog updates; sight capped at 1800; a 3.2 s day/night transition;
  tree occluder height 230 (level 2); flying units ignore occluders.
- Hive collision thread: the 0–15 / 16–31 / 32–47 / 48+ → 1×1 … 4×4 cell table.
- Liquipedia Daytime: a 480 s cycle split 240 / 240.
- PCGamesN (29 January 2020): Rob McNaughton's quote that upkeep was partly a response to memory limits.
- Gamebanshee: patch 1.10 introduced item levels 1–8 and classes, and item selling.

**Corrected in this pass:**

- The rationale for gold-mine guards was inverted (§5).
- "Hero speed cap 400" is really the default cap for **all** units (§4.4, §7.4).
- The Lumber Mill upgrade requirements were wrong (§2.2).
- The Blizzard upkeep quote was paraphrased inside quotation marks; it now quotes the page (§2.4).
- The "Day Length" constant name was attributed to Liquipedia, which does not name it (§6).
- The Liquipedia note that upkeep also taxes creep bounties and item sales has been added (§2.4).

**Marked unverified in this pass:**

- the shift-queue limit of 35 (§9);
- the Reforged 24-unit selection (§9, §13.1);
- the attack-speed caps (§7.3);
- the collision cap of about 200 (§7.5).

**Still unverified:**

- the 1200 gu XP-share radius: neither Blizzard's Heroes page nor Liquipedia's Experience page gives a radius;
- lumber per tree;
- creep bounty values;
- the creep leash distance.

**Sources that could not be re-fetched** (they are kept because each is a plausible, well-known page, but they
are not confirmed):

- Icy Veins: HTTP 403;
- ABA Landslide: HTTP 403;
- the FL-108 archive on webharvest.gov: rate-limited by archive.org.

---

## Sources

**Blizzard (official):**

- [Blizzard classic.battle.net – Upkeep](https://classic.battle.net/war3/basics/upkeep.shtml)
- [Blizzard classic.battle.net – Armor and Weapon Types](https://classic.battle.net/war3/basics/armorandweapontypes.shtml)
- [Blizzard classic.battle.net – Heroes](https://classic.battle.net/war3/basics/heroes.shtml)
- [Blizzard classic.battle.net – Special Commands](https://classic.battle.net/war3/basics/specialcommands.shtml)
- [Blizzard classic.battle.net – Melee map design guidelines](https://classic.battle.net/mod/dev/melee.shtml)
- [classic.battle.net – Footman](https://classic.battle.net/war3/human/units/footman.shtml)
- [classic.battle.net – Knight](https://classic.battle.net/war3/human/units/knight.shtml)
- [classic.battle.net – Rifleman](https://classic.battle.net/war3/human/units/rifleman.shtml)
- [classic.battle.net – Peasant](https://classic.battle.net/war3/human/units/peasant.shtml)
- [classic.battle.net – Paladin](https://classic.battle.net/war3/human/units/paladin.shtml)
- [classic.battle.net – Town Hall](https://classic.battle.net/war3/human/buildings/townhall.shtml)
- [classic.battle.net – Keep](https://classic.battle.net/war3/human/buildings/keep.shtml)
- [classic.battle.net – Castle](https://classic.battle.net/war3/human/buildings/castle.shtml)
- [classic.battle.net – Farm](https://classic.battle.net/war3/human/buildings/farm.shtml)
- [classic.battle.net – Barracks](https://classic.battle.net/war3/human/buildings/barracks.shtml)
- [classic.battle.net – Altar of Kings](https://classic.battle.net/war3/human/buildings/altarofkings.shtml)
- [classic.battle.net – Orc Burrow](https://classic.battle.net/war3/orc/buildings/orcburrow.shtml)
- [classic.battle.net – Great Hall](https://classic.battle.net/war3/orc/buildings/greathall.shtml)
- [classic.battle.net – Ziggurat](https://classic.battle.net/war3/undead/buildings/ziggurat.shtml)
- [classic.battle.net – Ghoul](https://classic.battle.net/war3/undead/units/ghoul.shtml)
- [classic.battle.net – Moon Well](https://classic.battle.net/war3/nightelf/buildings/moonwell.shtml)
- [classic.battle.net – Wisp](https://classic.battle.net/war3/nightelf/units/wisp.shtml)
- [classic.battle.net – Lumber Mill (lumber-harvesting upgrades)](https://classic.battle.net/war3/human/buildings/lumbermill.shtml)
- [classic.battle.net – Blacksmith (weapon and armor upgrade costs)](https://classic.battle.net/war3/human/buildings/blacksmith.shtml)
- [classic.battle.net – Resources (gold mine low warning at 1500)](https://classic.battle.net/war3/basics/resources.shtml)
- [classic.battle.net – Economy (5 workers per mine)](https://classic.battle.net/war3/basics/economy.shtml)
- [classic.battle.net – Day/Night Cycle (8-segment orb, wolf howl)](https://classic.battle.net/war3/basics/daynight.shtml)
- [Blizzard.j (melee constants, starting units, camera defaults) via lep/jassdoc](https://raw.githubusercontent.com/lep/jassdoc/master/Blizzard.j)

**Liquipedia** (the HTML pages were blocked; in the fact-check, Daytime, Upkeep, Gold Mine and Experience were
read through the MediaWiki API, and every page below was confirmed to exist):

- [Liquipedia – Upkeep](https://liquipedia.net/warcraft/Upkeep)
- [Liquipedia – Gold Mine](https://liquipedia.net/warcraft/Gold_Mine)
- [Liquipedia – Experience](https://liquipedia.net/warcraft/Experience)
- [Liquipedia – Daytime](https://liquipedia.net/warcraft/Daytime)
- [Liquipedia – Damage Calculation](https://liquipedia.net/warcraft/Damage_Calculation)
- [Liquipedia – Armor](https://liquipedia.net/warcraft/Armor)
- [Liquipedia – Economy](https://liquipedia.net/warcraft/Economy)
- [Liquipedia – Gold](https://liquipedia.net/warcraft/Gold)
- [Liquipedia – Heroes](https://liquipedia.net/warcraft/Heroes)
- [Liquipedia – Attack](https://liquipedia.net/warcraft/Attack)

**warcraft.wiki.gg:**

- [warcraft.wiki.gg – Upkeep](https://warcraft.wiki.gg/wiki/Upkeep)
- [warcraft.wiki.gg – Warcraft III armor and attack types](https://warcraft.wiki.gg/wiki/Warcraft_III_armor_and_attack_types)
- [warcraft.wiki.gg – Hero (Warcraft III)](https://warcraft.wiki.gg/wiki/Hero_unit)
- [warcraft.wiki.gg – Creeps](https://warcraft.wiki.gg/wiki/Creeps)
- [warcraft.wiki.gg – Gold Mine (Warcraft III)](https://warcraft.wiki.gg/wiki/Gold_Mine_(Warcraft_III))
- [warcraft.wiki.gg – Entangled Gold Mine](https://warcraft.wiki.gg/wiki/Entangled_Gold_Mine)
- [warcraft.wiki.gg – Peasant (Warcraft III)](https://warcraft.wiki.gg/wiki/Peasant_(Warcraft_III))
- [warcraft.wiki.gg – Ghoul (Warcraft III)](https://warcraft.wiki.gg/wiki/Ghoul_(Warcraft_III))
- [warcraft.wiki.gg – Footman (Warcraft III)](https://warcraft.wiki.gg/wiki/Footman_(Warcraft_III))
- [warcraft.wiki.gg – Tavern (Warcraft III)](https://warcraft.wiki.gg/wiki/Tavern_(Warcraft_III))
- [warcraft.wiki.gg – Blacksmith (Warcraft III)](https://warcraft.wiki.gg/wiki/Blacksmith_(Warcraft_III))
- [warcraft.wiki.gg – Lost Temple (Warcraft III)](https://warcraft.wiki.gg/wiki/Lost_Temple_(Warcraft_III))
- [warcraft.wiki.gg – Goblin Merchant](https://warcraft.wiki.gg/wiki/Goblin_Merchant)

**Hive Workshop (community):**

- [Hive Workshop classic – Creeping](https://classic.hiveworkshop.com/war3/basics/creeping.shtml)
- [Hive Workshop classic – Day/Night](https://classic.hiveworkshop.com/war3/basics/daynight.shtml)
- [Hive Workshop classic – Resources](https://classic.hiveworkshop.com/war3/basics/resources.shtml)
- [Hive Workshop classic – Economy](https://classic.hiveworkshop.com/war3/basics/economy.shtml)
- [Hive Workshop classic – Unit stats legend](https://classic.hiveworkshop.com/war3/basics/unitstats.shtml)
- [Hive Workshop – Basic knowledge: the resources](https://www.hiveworkshop.com/threads/basic-knowledge-of-warcraft-iii-the-resources.32293)
- [Hive Workshop – Vision guide (fog cells, 0.4 s update, occluders)](https://www.hiveworkshop.com/threads/vision-guide.290769/)
- [Hive Workshop – Collision size to pathing cells](https://www.hiveworkshop.com/threads/pathing-collision-size-values-into-real-values.271205)
- [Hive Workshop – Max unit speed (522)](https://www.hiveworkshop.com/threads/max-unit-speed-amount.255045)
- [Hive Workshop – DPS and attack animation damage point](https://www.hiveworkshop.com/threads/dps-and-attack-animation-damage-point.247190)

**Press, design history and IP:**

- [Icy Veins – 24-unit selection and new Tavern hero](https://www.icy-veins.com/blizzard/news/a-new-tavern-hero-and-24-unit-selection-could-change-how-you-play-warcraft-3/) (HTTP 403 in the fact-check; content unconfirmed)
- [warcraft.wiki.gg – Warcraft III: Reforged (12-unit cap to remain "at least initially", 2018)](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reforged)
- [PCGamesN – Warcraft 3 upkeep (Rob McNaughton)](https://www.pcgamesn.com/warcraft-3/upkeep)
- [Corerunner – Warcraft III review (upkeep and small armies)](https://corerunner.substack.com/p/warcraft-iii-review)
- [Gamebanshee – Warcraft III v1.10 (item levels and classes)](https://gamebanshee.com/3rcp)
- [Game Informer – Warcraft III was almost "Warcraft Legends"](https://www.gameinformer.com/b/news/archive/2014/11/03/warcraft-iii-was-almost-a-non-traditional-rts-called-warcraft-legends.aspx)
- [17 U.S.C. §102 (Cornell LII), subsection (b): ideas, systems and methods of operation are not protected](https://www.law.cornell.edu/uscode/text/17/102)
- [US Copyright Office FL-108 "Games" (archived)](https://webharvest.gov/peth04/20041015023438/http://www.copyright.gov/fls/fl108.html) (archive.org rate-limited the fact-check; content unconfirmed)
- [ABA Landslide – Why videogame rules are not expression protected by copyright law](https://www.americanbar.org/groups/intellectual_property_law/resources/landslide/archive/why-videogame-rules-are-not-expression-protected-copyright-law/) (HTTP 403 in the fact-check; content unconfirmed)
