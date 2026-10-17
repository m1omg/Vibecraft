# Neutral layer design: creeps, items, neutral buildings and critters

*Design date: 2026-10-16; revised 2026-10-17 after the IP-safety and WC3-fidelity reviews (see the Review log at the end).
Status: proposal for review. Scope: everything on the map that belongs to no player: creep camps,
items, neutral buildings (gold mine, merchant, inn, mercenaries, fountains, lab, gate, vision tower), neutral heroes and critters.
Data owners: `PlayerState.NEUTRAL_HOSTILE = 12` (creeps) and `PlayerState.NEUTRAL_PASSIVE = 13` (mines, shops, critters), per `architecture.md`.
Global rules (XP sharing, revive costs, item pickup and give ranges, neutral use range) are owned by `docs/design/rules.md`; where this doc
restates one, rules.md wins.*

**Read with:** `docs/research/ip-safety.md` (§0, §2, §3.2), `docs/research/gameplay-mechanics.md` (§4, §5, §10, §11, §13),
`docs/research/README.md`, `docs/research/visual-art-direction.md` (§1.4 tilesets, §7.2 biome palettes),
`docs/research/audio-direction.md` (§1.6, creep vocal sets), `docs/design/factions/kingdom.md` and `docs/design/factions/clans.md`
(slice units this layer must be balanced against), and `docs/design/juice/combat-and-units.md` (CMB-06 creep notice, CMB-28 bounty coins, CMB-33 leashing gait).

**Supersedes:** the slice creep roster ("Briar Hound" … "Ancient Rootwarden"), the camp layout and the 12-item list in
`gameplay-mechanics.md` §13.6. The global numbers from §13.1 still apply: hero XP table, unit-kill XP by level, creep XP factor
80/70/60/50/0 %, XP share radius 18.75 m, 480 s day/night with the first dusk at 200 s, the slice damage matrix and the armour formula.

**Design brief in one line.** A Warcraft III fan should walk onto the map and feel at home at once: green, amber and red camps that
sleep at night and drop items, a merchant at the centre, a fountain worth fighting over, an inn with odd mercenary heroes, critters to
click on. Nothing they see, read or hear is Blizzard's: not a creep design, a shop, an item name, a voice line or a minimap icon.

**Conventions**

- Distances in metres (1 m = 64 WC3 gu), speeds in m/s, times in seconds. Melee range is edge to edge (`architecture.md`).
- Attack types: Blade, Pierce, Siege, Arcane, Heroic, Spell, **Pure** (data ids `blade, pierce, siege, arcane, heroic, spell, pure`; rules §7.1 and §20.4).
  Armour types: Light, Medium, Heavy, Fortified, Hero, Unarmored, Adamant (data ids `light, medium, heavy, fortified, hero, unarmored, adamant`;
  no neutral uses Adamant in the slice).
- "Lvl" is the creep's **level**: it sets XP value and bounty, and sums into the camp's colour.
- Ids use the prefixes `creep_`, `camp_`, `item_`, `neutral_`, `nhero_` and `critter_`.
- Slice tags:
  - **[SLICE]**: in the vertical slice (kingdom vs clans, 1v1 vs AI, the Greenvale map).
  - **[SLICE+]**: a stretch goal if the budget holds.
  - *later*: full game only.
- **WC3 and Blizzard names appear only in rationale and audit text** (the fidelity map §0.2, "Why" columns and notes marked *Why*,
  "Never" art rules, the kit audit §5.6.7 and §10), never in ids, data, UI strings, filenames or prompts. Player-facing drafts in this
  doc (ability "Numbers" and item "Effect" cells, which become tooltips; the rule wording shown in hover text; every voice line) are kept
  free of them, so they can be pasted into data as they stand.

---

## 0. At a glance

### 0.1 Summary

| | Choice |
|---|---|
| **Creep families** | 10 families, 43 creep types, levels 1–9. **Greenvale** (slice tileset): Sootcoats (charcoal-burner outlaws), Tattiebogles (walking scarecrows, awake at night), Cairnwakes (drystone constructs that never sleep; universal), Mire Toads. **Rimeholt** (later): Stoatkin, Whiteouts, Longfringe Herd. **Sunscar Steppe** (later): Claywrights, Saltbound, Rollbacks |
| **Camp rules** | Green 1–9 / amber 10–19 / red 20+ total level. Creeps sleep at night; the exceptions are **never-sleep** families and at most **one** day-sleeping camp per map, and at least 60 % of a map's camps sleep at night (§1.5). Leash 18.75 m; unreachable attackers are dropped. XP = the global unit-kill table × the creep factor, lost if no hero is near (rules §6.4). Bounty 4 × level + 2 + rand(0–4), taxed by upkeep. No respawn |
| **Items** | **52 items** in five classes (purchasable, power-up, permanent, charged, artifact), item levels 1–8, drop tables by camp total level, all names original |
| **Merchant people** | **Rundlings**: knee-high, pangolin-like traders who curl into a ball when frightened and are obsessed with *fair* weight, not profit |
| **Neutral buildings** | **Gold Seam** (gold mine), **Weighstall** (merchant), **Lucky Barrow** (rotating rare stock), **Coaching Inn** (neutral heroes and instant revive; each map names its own inn, Greenvale's is *The Muddy Lantern*), **Free Company Camp** (mercenaries), **Hale Spring** / **Dewstone** (health / mana landmarks), **Contraption Barn** (lab-equivalent, run by hill-country millwrights), **Twin Milestones** (paired teleport), **Beacon Cairn** (capturable vision cairn) |
| **Neutral heroes** | **Rat-Piper** (AGI ranged trapper and rat summoner), **Old Menhir** (STR stone tank who walls and shoves), **Weighmaster** (INT Rundling support who pays gold for hired pikes) |
| **Critters** | Hares, geese, hedgehogs, fireflies and a flushing sparrow roost in Greenvale; snow hares, ptarmigan and lemmings in Rimeholt; meerkats and guinea fowl in Sunscar. Each has its own click-spam gag; **nothing explodes** |
| **Slice subset** | 10 creep types in 3 families, 11 camps (6 green, 4 amber, 1 red), 31 items, Gold Seam ×4, Weighstall, Hale Spring, **Coaching Inn (instant revive only)**, 2 critters + fireflies. [SLICE+]: Withy Brute, hiring the Rat-Piper at the inn, the Curl-Up Scale, Free Company Camp, Beacon Cairn ×2, Dewstone, sparrow roosts (§7) |

### 0.2 Fidelity map (WC3 neutral element → Vibecraft)

Function stays close to WC3 on purpose. Expression (names, designs, visuals, text, sounds, icons) is ours.

| WC3 element (reference only) | Vibecraft | Kept familiar (function, numbers) | Made ours |
|---|---|---|---|
| Creep camps, levels 1–10, camp colours by total level | Creep camps | Level bands, XP falloff by hero level, item drops by camp level, **most camps asleep at night** (≥ 60 % per map), leash and give-up, no respawn, camp acts as one | Families and designs; **shield-shaped minimap pips** (not dots); sleep shown by in-world posture plus snore puffs, not a "Z"; never-sleep families and one day-sleeping camp per map as a planned mix |
| Gold Mine | **Gold Seam** | 12,000 / 8,000 gold, 5-worker saturation, low-gold warning, **collapses when empty** | An adit cut into a layered **cliff seam** (not a free-standing rock mound), with a windlass headframe on the cliff lip, a spoil heap and a wooden sluice; lanterns at night (§5.2, §10.2) |
| Goblin Merchant | **Weighstall** | Potions, recall, wards, reveal, boots, a permanent HP item, skill reset, a self-stasis item; buys items at 50 % | A market stall under a giant brass balance; Rundling traders; comedy of fussy honesty (never greed, never explosives) |
| Marketplace | **Lucky Barrow** *(later)* | Rotating random stronger items | A pedlar's handcart; restocks on a visible timer; also sells two fixed late items |
| Tavern | **Coaching Inn** [SLICE: revive only] | Hire neutral heroes with any faction; instant revive; never guarded | A generic building type with a per-map sign name; three original heroes; kits follow the 2-of-4 rule (§5.6.7) |
| Mercenary Camp | **Free Company Camp** | Hire local creep types; stock and restock | Hiring board with tally sticks; rosters per tileset |
| Goblin Laboratory | **Contraption Barn** *(later)* | Lumber machine and transport | **The 1:1 offer mapping is broken:** staffed by human hill-country millwrights, not the merchant people; the balloon carries 6 food for 200 g / 40 l and drifts faster downwind; the paid reveal is replaced by an original **Hedge-Cutters** service that clears a strip of trees; the ram hits buildings and survives (no suicide sapper) |
| Fountain of Health / Mana | **Hale Spring** / **Dewstone** | Area regeneration around a contested landmark | A spring pool fed by a log flume, guarded by the map's one day-sleeping camp (free by day, dangerous by night); the mana landmark is a **sweating quartz boulder**, with no water, no basin and no blue glow |
| Way Gate | **Twin Milestones** *(later)* | Paired teleport | Units fold into road dust; per-unit cooldown |
| Capture-by-standing vision tower (no WC3 melee building; StarCraft II's Xel'Naga Tower has the mechanic) | **Beacon Cairn** [SLICE+] | Capture by standing, wide vision | The mechanic is generic. Ours differs in presentation: a low drystone cairn with an iron fire-basket, a 60 s fuel timer after you leave, and a douse rule (§5.11, §10.2) |
| Critters (and the click-spam sheep gag) | Critters | Neutral passive ambient animals | Every gag is original; no exploding animals |
| Item levels 1–8 and classes | Items | Same classes and levels | All names, numbers and effects ours; dropped items are a **twine-tied oilcloth bundle**, not a chest |

---

## 1. Global creep rules

### 1.1 Level stat curve (baseline; each creep deviates by role)

Creeps are a little weaker per level than player units of the same level (*Why:* the WC3 feel). Baselines are for a melee creep and
rise monotonically with level. Ranged creeps and casters get about 60–75 % of the melee HP, brutes about 120 %.

| Lvl | HP (melee) | Avg damage | Cooldown (s) | Armour | XP (global table) | Bounty (gold) | Spell resistance | Attack type |
|---|---|---|---|---|---|---|---|---|
| 1 | 200–240 | 8–9 | 1.2–1.6 | 0 | 25 | 6–10 | — | by role |
| 2 | 340–420 | 11–13 | 1.6–1.8 | 1 | 40 | 10–14 | — | by role |
| 3 | 460–520 | 14–17 | 1.6–1.8 | 1–2 | 60 | 14–18 | — | by role |
| 4 | 560–720 | 19–22 | 1.4–1.8 | 1–2 | 85 | 18–22 | — | by role |
| 5 | 760–980 | 26–29 | 1.8–2.1 | 2 | 115 | 22–26 | — | by role |
| 6 | 1000–1100 | 30–34 | 1.9–2.0 | 2–3 | 150 | 26–30 | **Hardy** 30 % | by role |
| 7 | 1250–1350 | 38–40 | 1.7–2.2 | 3–5 | 190 | 30–34 | **Hardy** 30 % | **Pure** |
| 8 | 1500–1800 | 45–49 | 1.8–2.0 | 3–5 | 235 | 34–38 | **Hardy** 30 % | **Pure** |
| 9 | 2100 | 58 | 2.4 | 6 | 285 | 38–42 | **Hardy** 30 % | **Pure** |
| 10 | (reserved) | — | — | — | 340 | 42–46 | **Hardy** 30 % | **Pure** |

- **Hardy (level 6+):** the creep **counts as a hero for control durations** (rules §6.5: stun, sleep, root, slow, silence, disarm and
  enthral last 50 % unless the ability sets `hero_duration`) **and for Spell damage** (×0.7, the multiplier the matrix gives the Hero armour type).
  Polymorph-type and remove-from-game effects cannot target it. Hover text: "Hardy: takes less damage from spells; disabling effects
  last half as long." *Why:* WC3's level-6+ creeps have hero-style magic resistance. Rules §10.2's "Hardy creeps" row should read the same (follow-up, §11).
- **Pure from level 7:** every creep of level 7 or more attacks with Pure (data id `pure`), which ignores the armour-type matrix.
  *Why:* WC3's level-7+ creeps use its matrix-ignoring attack type.
- **Regeneration:** 0.25 HP/s for organic creeps, 0 for constructs and the dead; casters regenerate 0.6 mana/s and start full.
- **Sight:** 14 m day / 9 m night (used only by creep AI; creeps grant no vision to any player).
- **Default collision radius:** small 0.3 m, standard 0.45 m, large 0.7–1.0 m.

### 1.2 Camp colour and the minimap

| Colour | Total camp level | Typical position | Typical drop |
|---|---|---|---|
| **Green** | 1–9 | Near each start, off the main road | One L1 power-up or one L2 item |
| **Amber** | 10–19 | Expansions, neutral buildings, flanks | L1 power-up + an L2–L3 item |
| **Red** | 20+ (slice: 20) | Contested pockets toward the centre | L2 item + an L4–L7 item |

*Why:* the bands are WC3's green / orange / red bands; "amber" is our colour word.

- **Pip design (ours):** a small upright **shield shape with a notch at the top**, filled green (#5FBF4A), amber (#E8A93A) or red (#D9483B),
  with a 1 px dark rim. *Why:* WC3's round camp dots are not copied (ip-safety §2.4 and mechanics §12.2).
- **When pips show** (`rules.minimap.show_unexplored_neutrals`, proposed default `true`, to be set from footage; §11):
  - `true`: every camp pip and every neutral-building glyph is drawn from **0:00** as a static marker, even on the black mask, so players
    can plan a creep route at the start. A cleared camp's pip disappears only once the player has **seen** the empty spot
    (it stays as a ghost until then, so the minimap never leaks an enemy's creeping).
  - `false`: pips and glyphs appear once the area is explored, stay as last-seen ghosts in fog, and disappear when the cleared camp is seen.
  - *Why:* WC3's minimap is commonly remembered as showing camps, shops and mines from the start (unverified; the wiki only says the
    minimap "has a special ability to show Creep Camps").
- **Neutral-building glyphs (ours),** pale ivory with a dark rim: Gold Seam = a faceted nugget; Weighstall = a balance beam with two pans;
  Hale Spring = a droplet inside a ring; Coaching Inn = a hanging lantern; *later:* Dewstone = an upright stone with one droplet,
  Free Company Camp = two crossed tally sticks, Beacon Cairn = a small flame (team-coloured when lit), Lucky Barrow = a cart wheel,
  Twin Milestones = a pair of short posts joined by a dotted line.
- A minimap toggle, **Show Camps**, hides the pips (default on).
- Hovering a camp in the world shows a tooltip with the camp's colour word and "Sleeping" or "Awake". It never shows the drop.

### 1.3 Aggro: camp mode, guard mode and help

- **Acquire range:** 3.9 m (250 gu) by default, 5.0 m for casters, **6.0 m for guard-mode camps**. A camp template may set
  `acquire_override` for all its members (the shop guard uses 6.5 m, §3.3). Creeps auto-acquire only units of real players
  (never critters or other neutrals).
- **The camp acts as one.** Every creep has a `camp_id`. When any member acquires a target or takes damage, every awake member of
  that camp engages. Members of *other* camps never join, however close they stand (no chain pulls between camps).
- **Camp mode** (default for every camp that guards no gold mine): the camp fights only units that come into acquire range or attack
  it. It **ignores buildings**, including buildings under construction next to it, **except a structure that damages the camp**
  (a tower): that structure counts as an attacker like any unit, so a camp pulled under a reachable tower fights the tower.
- **Guard mode** (camps at expansion gold mines): as camp mode, plus the camp **attacks any building started within 12 m** of its centre.
  So an expansion cannot be "built through" its guards (mechanics §5 design note).
- **Flyers:** creeps that are not fighting do not acquire flying units. Once engaged, ranged creeps shoot flyers normally.
- **Unreachable attackers** (replaces the old tower-only rule):
  - If a creep cannot path to its current attacker for **2 s**, it drops that target and picks another attacker it can reach.
    **Unreachable** means: no ground path, a path longer than **2 ×** the straight distance, or a path that leaves the creep's leash.
    A ranged creep that can already hit the attacker from where it stands counts it as reachable.
  - If **every** enemy that damaged the camp in the last 3 s has been unreachable for **3 s**, the **whole camp returns home**
    (regenerating 2 % of max HP/s, §1.4) and **ignores those attackers** until one of them becomes reachable again. While it ignores them
    the camp stays in its return state at home and keeps regenerating 2 %/s.
  - *Why:* without this, a hero on a cliff, behind a tree line or across water could farm a camp forever, because a camp that keeps
    taking damage never gives up. WC3 added creeps that "eventually give up and return" for the same abuse. Test
    `creep_unreachable_attacker` (§9): a single ranged unit on a cliff cannot kill a camp below it.
- **Creep notice (juice CMB-06):** creeps lift their heads toward an intruder at 1.5× acquire range, so the pull distance can be felt before it is tripped.

### 1.4 Leash and return

- **Leash:** 18.75 m from each creep's **guard position** (its spawn point). A creep past the leash drops its target and returns.
- **Give-up timer:** if the camp has neither dealt nor taken damage for 10 s, every member returns. Attackers it cannot reach make it
  return after 3 s (§1.3), even while it is taking damage.
- **Returning:** creeps walk home ignoring hits (they are **not invulnerable**) and regenerate **2 % of max HP per second** until home,
  then resume normal regeneration. Head-down "leashing" gait per juice CMB-33.
- Because the camp acts as one, a single creep cannot be pulled away from its camp-mates. The whole camp can still be dragged toward
  your army or towers, up to the leash, and slow members turn back first (the classic "pull and fight at home" play).
- **Tuning flag:** WC3's real leash and give-up values are unverified (mechanics §14). 18.75 m, 10 s and the 2 s / 3 s unreachable
  timers are starting values. Rules §15.1–15.2 should carry the unreachable rule (follow-up, §11).

### 1.5 Day and night

Every creep has a **sleep schedule**: `night` (default), `never` or `day` (night-active). The family sets the default; a camp template
may set **`sleeps_override`** (`"night"`, `"day"` or `"never"`) for all its members.

| Schedule | Asleep | Families (default) | Why |
|---|---|---|---|
| `night` | 18:00 → 06:00 | Sootcoats, Mire Toads, Stoatkin, Longfringe Herd, Claywrights | The WC3 default: night is safe for scouting past camps |
| `never` | Never | Cairnwakes, Whiteouts, Saltbound | WC3 has never-sleeping creeps too (golems, the dead) |
| `day` | 06:00 → 18:00 | **Tattiebogles**, **Rollbacks** | **Original twist:** scarecrows slump on their poles by day and walk at night; dung-beetles roll by starlight. One night-active family per tileset at most |

**Map rules** (so a WC3 player can rely on "night = most camps asleep"; also proposed for rules §15.3, follow-up in §11):
1. **At most one `day` camp per map.** Other camps of a night-active family use `sleeps_override: "night"`.
2. **At least 60 % of a map's camps sleep at night.**
3. `never` camps are allowed where an always-awake guard is the point (expansion mines, the red prize).

The slice map has 11 camps: **7 sleep at night** (Charcoal Clamp ×2, Turnip Patch ×2, Collier's Hut ×2, Smugglers' Den), 3 never sleep
(Drystone Fold ×2, Standing Ring) and **1 sleeps by day** (the Crow Field, the spring's special guard). 7 / 11 = 64 %.
The Turnip Patch is a Tattiebogles camp with `sleeps_override: "night"`. Lore line: *"Tame scarecrows that guard the turnips by day."*
Its sleep tell is the family's own: by night they slump on their poles and a crow roosts on each head.

- **Falling asleep:** each creep falls asleep 0–6 s after its sleep time (seeded stagger), only if its camp is not fighting and is home.
- **Waking up:** at its wake time (+0–6 s stagger), or at once when:
  1. it or a camp-mate takes damage (the whole camp wakes);
  2. a building is started within 12 m;
  3. a player **buys or hires** at a neutral building within 10 m (passive auras such as a spring's healing do not wake anyone).
- **Players' units never auto-acquire sleeping creeps.** Attacking them is an explicit order (attack, or attack-move onto them).
- **Sleep tells** (*Why:* ours, instead of WC3's letter "Z"):
  - **In-world posture per family:** Sootcoats doze around a banked fire with smoke puffing from their hoods;
    Tattiebogles slump on their poles with a **crow perched on each head**, whichever schedule the camp keeps (the crow flies off when
    they wake: that is the tell); toads half-sink with eyes shut; stoats curl nose-to-tail.
  - **Small UI glyph:** a closed-eye glyph above the health bar plus slow drifting snore puffs (VFX). Never letters.
- **Night sight drops** for players (global rule), so night creeping trades safety for vision.

### 1.6 XP and bounty

- **XP** per kill = the global unit-kill table by creep level (25 / 40 / 60 / 85 / 115 / 150 / 190 / 235 / 285 / 340)
  × the creep XP factor of the receiving hero's level (80 / 70 / 60 / 50 / **0 %** at levels 1 / 2 / 3 / 4 / 5+).
  It is split evenly between the owner's eligible heroes within 18.75 m of the kill. If no eligible hero (alive, below level 10) is
  within 18.75 m of the kill, **the XP is lost** (rules §6.4, `rules.xp.no_hero_in_range`). The XP route in §3.6 assumes the hero is
  present at every camp.
- **Summoned creeps** (crows, gang members, raised husks, called masons) give 50 % XP and **no bounty**.
- **No XP** when a tower lands the killing blow.
- **Bounty** = 4 × level + 2 + rand(0–4) gold (seeded sim RNG), paid to the killer's owner. **Upkeep taxes bounty** like mined gold
  (Liquipedia, via mechanics §2.4). Shown by the bounty pop and coin flight of juice CMB-28.

### 1.7 Creep spell AI (applies to every family)

| Ability kind | When a creep uses it | Target choice |
|---|---|---|
| Summon | On first aggro, then off cooldown while fighting | — |
| Area damage or stun | 2+ enemies inside the area, or an enemy hero inside | Point with the most enemy units, heroes counted ×2 |
| Single-target disable | Off cooldown | Enemy hero first, then the enemy unit with the highest damage |
| Heal (single target) | An allied creep below 60 % HP is in range, off cooldown | Lowest HP % first; **never itself first** (it heals itself only when no other ally qualifies) |
| Regeneration aura | Passive | — |
| Silence or blind area | An enemy hero starts casting, or 2+ enemy casters/ranged units are clustered | That cluster |
| Pull | Off cooldown | The farthest enemy ranged unit or caster in range |
| Once-only "last stand" passive | Automatic at its HP threshold | — |

Creep casters keep 1.5 m more distance than melee creeps and never flee.

### 1.8 Item drops

- A camp template lists up to two drops (§3.1). **Drop B** (the better item) is carried by the camp's **highest-level** creep,
  **Drop A** by its **lowest-level** creep. A single drop is carried by the highest-level creep. The player learns
  "kill the big one for the prize" (*Why:* as in WC3).
- **Ties and summons:** the carrier is the **first** creep of the highest (Drop B) or lowest (Drop A) level in the template's `creeps`
  order. Summons never carry. The item drops where the carrier dies, whoever kills it (a player, a tower or another camp's creep).
- The item for each drop slot is chosen at **match start** from the matching pool (§4.7) by the seeded sim RNG. Boss camps may name a fixed item.
- **Ground visual:** a twine-tied **oilcloth bundle** with a red wax seal (bpy prop). It glints every 3 s and casts a small warm light at night.
  Power-ups instead show as their own small prop (an iron nail, a juggling ball, a knotted cord, berries, a purse, the almanac, a tally-stick)
  so the player can see what they are.

### 1.9 Camp layout

- Each camp template may give a **`layout`**: one `[dx, dz, facing_deg]` entry per creep, in the template's `creeps` order, in metres
  from the camp centre (§9).
- **Default** when a template has no layout: the highest-level creep (first in order on a tie) stands at the centre; the others stand
  evenly spaced on a **2.5 m ring**, facing the nearest lane centreline (slice-plan §1.10).
- A creep's layout position is its **guard position** (leash and return, §1.4).
- Items on the ground never expire. Anyone can pick them up (heroes only, except food power-ups: §4.1).

---

## 2. Creep families

### 2.0 Overview

Rules every family follows:
- **Original design.** Each family has its own body plan, culture or folklore source, palette and camp props, and none maps onto a
  WC3 creep family (audit in §10.2).
- **Neutral readability.** Creeps carry **no team colour**. Their palettes are kept off both slice factions (Brennmark burgundy/ivory/bronze,
  Tormai ink-teal/saffron/bronze) and off the WC3 race palettes.
- **Slice families are cheap.** They are bipeds on the shared humanoid skeleton, or rigid stone stacks animated procedurally in bpy.
  Quadrupeds, flyers and floating spirits wait for the full game, or use procedural motion (hop, float, roll).

| # | Family | Tileset | Body plan | Sleeps | Levels | Types | Production | Slice |
|---|---|---|---|---|---|---|---|---|
| G1 | **Sootcoats** (charcoal-burner outlaws) | Greenvale | Human biped 1.7 m | Night | 1, 2, 3, 5, 7 | 5 | 1 AI mesh + prop swaps; Kiln-Master = scaled kitbash | **[SLICE]** 4 of 5 |
| G2 | **Tattiebogles** (walking scarecrows) | Greenvale | Stick-and-sack biped, stiff joints | **Day** (night-active) | 1, 3, 4, 5, 8 | 5 | 1 AI mesh (or bpy sticks and cloth); Strawling and crows procedural | **[SLICE]** 3, [SLICE+] 1 |
| G3 | **Cairnwakes** (drystone constructs) | **Universal** (retinted per tileset) | Stacked stone slabs | **Never** | 3, 5, 7, 9 | 4 | bpy procedural, rigid segments: **0 3D credits** | **[SLICE]** 3 of 4 |
| G4 | **Mire Toads** | Greenvale | Toad, hops | Night | 1, 3, 5, 7 | 4 | bpy procedural body, squash-and-stretch hop | *later* |
| F1 | **Stoatkin** (ermine raiders) | Rimeholt | Small mustelid biped 1.1 m | Night | 1, 2, 4, 6 | 4 | 1 AI mesh + props | *later* |
| F2 | **Whiteouts** (snow-squall spirits) | Rimeholt | Floating cloud body | Never | 2, 4, 6, 8 | 4 | bpy + shader, no rig | *later* |
| F3 | **Longfringe Herd** | Rimeholt | Shaggy quadruped | Night | 2, 4, 6, 8 | 4 | 1 AI mesh, quadruped rig risk | *later* |
| S1 | **Claywrights** (termite masons) | Sunscar Steppe | Insect biped 1.4–2.4 m | Night | 1, 2, 3, 5, 8 | 5 | 1–2 AI meshes | *later* |
| S2 | **Saltbound** (salt-crusted dead) | Sunscar Steppe | Human biped, crystal crust | Never | 2, 4, 5, 8 | 4 | 1 AI mesh + crystal kitbash | *later* |
| S3 | **Rollbacks** (giant dung-beetles) | Sunscar Steppe | Six-legged beetle + ball | **Day** (night-active) | 2, 4, 6, 8 | 4 | bpy procedural legs, rolling ball | *later* |

Total: **43 creep types**, plus one summon-only type (the Crow). Other creep summons reuse existing types.

**Stat table columns:** HP · Mana · Armour (value and type) · Attack type · Damage · Cooldown (s) · Range (m; "melee" = 0.6–1.5 m edge to edge) ·
Speed (m/s). Abilities are detailed under each table. XP and bounty follow the creep's level (§1.6).

---

### 2.1 Greenvale (temperate forest; the slice tileset)

Mood (visual §7.2): golden-green meadows, ochre roads, mossy standing stones, hedgerows, ponds. The neutral world of Greenvale is
the hill country between Brennmark's market towns and the Tormai Herd Road. Both factions claim it; nobody has tamed it.

#### G1. Sootcoats: charcoal-burner outlaws [SLICE]

- **Concept:** deep-wood **charcoal burners** who sell charcoal to whoever pays and rob whoever does not. They camp around a **charcoal clamp**
  (a smoking, turf-covered earth mound) with lean-to shelters and stacked cordwood.
- **Look:**
  - **Wide conical leather hoods** with neck flaps. This hood is the family read at 64 px.
  - Soot-blackened faces with pale rings round the eyes, from wiping.
  - Patched oilcloth coats, clay smoke-pots on bandoliers, long-handled rakes and billhooks.
- **Never:** purple or red hooded cloaks, daggers-and-masks rogue kit, invisibility assassins, a noble-titled leader or a leader with a
  passive aura (that is the WC3 bandit set and its level-7 lord; §10.2). Their leader is named for his craft, not a rank.
- **Palette:** soot #2E2B29, oilcloth ochre #A07A3A, faded moss #5E6B3E; ember accent #E07A2A glows in hood smoke at night.
- **Inspiration:** the historic European woodland charcoal trade (a craft, not a culture).
- **Sound:** wordless. Coughs, grunts and a hoarse "Hup!", a coin flick for Light Fingers, crackling embers.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_sootcoat_cutpurse` | Sootcoat Cutpurse | 1 | 230 | – | 0 Medium | Blade | 8–10 | 1.5 | melee 0.6 | 4.4 | Light Fingers | **[SLICE]** |
| `creep_sootcoat_smoker` | Sootcoat Smoker | 2 | 260 | 150 | 0 Unarmored | Pierce (hot coal) | 10–13 | 2.0 | 6.0 | 4.2 | Smoke Pot | **[SLICE]** |
| `creep_sootcoat_collier` | Sootcoat Collier | 3 | 520 | – | 2 Heavy | Blade | 15–19 | 1.7 | melee 1.0 (rake) | 4.0 | Ember Rake | **[SLICE]** |
| `creep_sootcoat_kiln_master` | Kiln-Master | 5 | 760 | 250 | 2 Medium | Blade | 24–30 | 1.8 | melee 1.0 | 4.2 | Banked Coals, Choking Fumes, Pine-Tar Dressing | **[SLICE]** |
| `creep_sootcoat_clamp_father` | Clamp-Father | 7 | 1250 | – | 3 Heavy | Pure | 34–42 | 1.7 | melee 1.1 | 4.2 | Hardy, Rake the Clamp, Call the Gang | *later* |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Light Fingers** | Cutpurse | Passive | Its first hit on an enemy hero steals **6 gold** from that hero's owner (once per Cutpurse). The stolen gold is added to its bounty |
| **Smoke Pot** | Smoker | Point, 7 m | 3 m cloud for 8 s: enemy units inside have a **30 % miss chance**. 60 mana, cooldown 18 s |
| **Ember Rake** | Collier | Passive | Every 3rd attack sets the target alight: **6 Spell damage/s for 3 s** (refreshes, does not stack) |
| **Banked Coals** | Kiln-Master | Aura, 8 m | Allied creeps regenerate **+1.5 HP/s** and attack **10 %** faster |
| **Choking Fumes** | Kiln-Master | Unit target, 7 m | A 3 m cloud on the target for 3 s: enemies inside are **silenced 3 s** and slowed 25 %. 75 mana, cooldown 16 s |
| **Pine-Tar Dressing** | Kiln-Master | Unit target, 6 m (allied creep) | Slaps a hot pine-tar dressing on a wounded camp-mate: heals **150 HP**. 50 mana, cooldown 8 s. AI: the heal row of §1.7 |
| **Rake the Clamp** | Clamp-Father | No target, 3 m | Rakes the clamp's coals over everyone near him: **60 Spell damage**, then **8 Spell damage/s for 3 s** to enemy ground units within 3 m. Cooldown 12 s |
| **Call the Gang** | Clamp-Father | Once, on first aggro | 2 Cutpurses climb out of the clamp (summons, 30 s; 50 % XP, no bounty) |

#### G2. Tattiebogles: scarecrows that walk at night [SLICE]

- **Name:** *tattiebogle* is the Scots folk word for a scarecrow.
- **Concept:** field scarecrows that a hedge-spirit long ago taught to walk. **By day they slump on their poles in a turnip field**,
  each with a crow on its head. **At dusk the crows lift off and the field gets up.** They are the Greenvale night-active family (§1.5).
  Some farms have **tamed** theirs to guard the turnips by day; those slump at night instead (the slice's Turnip Patch, `sleeps_override: "night"`).
  The map's one day-sleeping camp is the wild Crow Field.
- **Look:**
  - Crossed-pole frames inside patched coats, stuffed sacking faces with stitched features, straw spilling at the joints,
    harrow-tine fingers. The head is part of the body; it never comes off or gets swapped.
  - The larger ones have **pierced turnip lanterns** for heads. The light shows through a random sieve of drilled holes, **never arranged
    as eyes or a mouth**, and never a carved or painted face. That keeps them away from carved-pumpkin and turnip-headed scarecrow characters.
  - They walk **stiff-kneed** (the "toy" motion the art doc wants).
- **Never:** swappable or detachable heads; a carved or painted face on a turnip; a feather-cloaked "crow-man" figure; a woven wicker
  effigy body or cage; pumpkins; a horseman. Crows perch on them; nobody is dressed as one (§10.2).
- **Type notes:** the **Crowcaller** is a taller scarecrow with a patched sacking cape (no feathers) and long outstretched pole-arms on
  which its crows perch. The **Withy Brute** is a hulking frame of tightly **bound willow-rod bundles** (like hedge-layers' fascines)
  lashed round a hay-rake spine and a harrow, stuffed with straw: solid bundles, never woven basketwork. **Old Mangold** is the oldest
  scarecrow of the shire, a giant mangold (fodder beet) lantern on a hay-wain pole, with a sickle.
- **Palette:** straw #C9A85A, sacking #B9A27E, patchwork coats in faded madder #8E4A3A, woad #5E6E8A and undyed #CDBE9A,
  crow black #1F1E24, lantern glow #FFC46B (night only; emissive).
- **Inspiration:** European field scarecrows, harvest-home customs, old-style turnip lanterns.
- **Tags:** `construct` (no blood, no poison effects later). **Stuffed:** they take −25 % damage from Pierce, because arrows and bullets pass through straw.
  Brennish Hookgunners and Tormai Javelineers should prefer other camps: that is the intended texture.
- **Sound:** wooden creaks, straw rustle, crow caws, a dry hiss when hit.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_harvest_strawling` | Strawling | 1 | 210 | – | 0 Light | Blade | 7–9 | 1.3 | melee 0.6 | 4.8 | Loose Straw | **[SLICE]** |
| `creep_harvest_fieldkeeper` | Fieldkeeper | 3 | 480 | – | 1 Medium | Blade (pitchfork) | 15–18 | 1.7 | melee 1.2 | 3.8 | Stuffed, Stand Still | **[SLICE]** |
| `creep_harvest_crowcaller` | Crowcaller | 4 | 420 | 200 | 0 Unarmored | Arcane | 13–16 | 1.9 | 6.5 | 3.8 | Stuffed, Scatter-Crows, Re-Stuff | **[SLICE]** |
| `creep_harvest_withy_brute` | Withy Brute | 5 | 980 | – | 2 Heavy | Blade | 26–32 | 2.1 | melee 1.2 | 3.6 | Stuffed, Harrow Slam | [SLICE+] |
| `creep_harvest_old_mangold` | Old Mangold | 8 | 1800 | 300 | 4 Heavy | Pure | 44–54 | 2.0 | melee 1.3 | 4.0 | Hardy, Stuffed, Lantern Glare, Last Sheaf | *later* |
| `creep_harvest_crow` (summon) | Crow | 1 | 110 | – | 0 Light | Pierce (peck) | 6–8 | 1.3 | melee 0.8 | 5.5 flying | — | **[SLICE]** |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Loose Straw** | Strawling | On death | Leaves a 2 m straw patch for 4 s: enemies inside move 20 % slower |
| **Stuffed** | All but Strawling and Crow | Passive | −25 % damage taken from Pierce |
| **Stand Still** | Fieldkeeper | Passive | After 3 s with **neither moving nor attacking**: +3 armour. Lost on its first step or swing (ambush armour, not fight armour) |
| **Scatter-Crows** | Crowcaller | No target | 3 Crows (flying summons, 20 s; 50 % XP). 80 mana, cooldown 25 s. Used on aggro |
| **Re-Stuff** | Crowcaller | Unit target, 6 m (allied Tattiebogle, not a Crow) | Stuffs fresh straw into a torn camp-mate: heals **120 HP**. 60 mana, cooldown 10 s. AI: the heal row of §1.7 |
| **Harrow Slam** | Withy Brute | No target, 3 m | 50 Spell damage and **stun 1.0 s** (heroes 0.5 s). Cooldown 12 s |
| **Lantern Glare** | Old Mangold | Cone 6 m, 60° | 80 Spell damage; struck enemies **flee** from him for 2 s (heroes 1 s). 100 mana, cooldown 15 s |
| **Last Sheaf** | Old Mangold | Once, at 25 % HP | Roots himself and re-stuffs for 3 s, healing **40 % of max HP** over that time. Kill him through it or lose the fight |

#### G3. Cairnwakes: drystone that got up (universal) [SLICE]

- **Concept:** the old field walls, cairns and standing stones of the hills, woken by whatever runs under them.
  They **never sleep**: the stones were asleep for a thousand years and are making up for it.
- **Look:**
  - Bodies of **stacked flat slabs** with visible gaps, lichen and moss in the cracks.
  - The larger ones have a standing-stone head carved with **cup-and-ring marks** that glow faintly lichen-yellow at night.
  - They move by grinding and clacking, slab by slab.
- **Never:** boulder-throwing, a rounded "rock man" body, glowing crystal cores (the WC3 golem read; §10.2).
- **Palette (Greenvale):** drystone #7D766A and #5E574E (the biome rock), lichen #A8B04E, moss #4F7A2E, night glyph glow #E8E29A.
  - **Retints:** Rimeholt "rime cairns" are glazed blue-grey granite with icicles. Sunscar "sand cairns" are banded sandstone.
- **Tags:** `construct`, **Set in Stone** (cannot be knocked back or pulled). Heavy armour, so Arcane damage (casters) is the natural answer.
- **Production:** bpy procedural. Bevelled slab primitives are grouped per body part and parented to bones, animated rigidly with no skinning.
  One AI-painted stone texture per tileset. **No 3D credits.**
- **Sound:** grinding stone, slab clacks, a deep hum for Ley Pulse.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_cairn_cairnling` | Cairnling | 3 | 520 | – | 3 Heavy | Blade | 12–16 | 1.8 | melee 0.8 | 3.3 | Settle, Set in Stone | **[SLICE]** |
| `creep_cairn_drystone_walker` | Drystone Walker | 5 | 960 | – | 4 Heavy | Blade | 25–31 | 2.0 | melee 1.1 | 3.4 | Rockfall Blow, Set in Stone | **[SLICE]** |
| `creep_cairn_menhir_elder` | Menhir Elder | 7 | 1350 | 200 | 5 Heavy | Pure | 36–44 | 2.2 | melee 1.2 | 3.2 | Hardy, Old Ward, Ley Pulse, Set in Stone | **[SLICE]** |
| `creep_cairn_dolmen_colossus` | Dolmen Colossus | 9 | 2100 | – | 6 Heavy | Pure | 52–64 | 2.4 | melee 1.5 | 3.0 | Hardy, Capstone Slam, Moss Regrowth, Set in Stone | *later* |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Settle** | Cairnling | Passive | After 2 s with **neither moving nor attacking**: +3 armour. Lost on its first step or swing, so it protects a resting camp, not a fighting one |
| **Rockfall Blow** | Drystone Walker | Passive | Every 4th attack **stuns 1.0 s** (heroes 0.5 s) |
| **Old Ward** | Menhir Elder | Aura, 8 m | Other allied creeps take **−20 % Spell damage** |
| **Ley Pulse** | Menhir Elder | No target, 4 m | **90 Spell damage** and slow 30 % for 3 s. 75 mana, cooldown 14 s |
| **Capstone Slam** | Dolmen Colossus | No target, 4 m | **150 Spell damage, stun 1.5 s** (heroes 0.75 s). Cooldown 15 s |
| **Moss Regrowth** | Dolmen Colossus | Passive | +8 HP/s after 5 s without taking damage |
| **Set in Stone** | All Cairnwakes | Passive | Immune to knockback and pull effects |

**Drystone Fold fight estimate** (after the Settle change): Drystone Walker 960 HP at 4 armour (≈ 1,190 Blade-effective HP) plus
3 Cairnlings at 520 HP and 3 armour (≈ 614 each) ≈ **3,030 Blade-effective HP**, down from ≈ 3,310 when Settle was always on in melee.
At ≈ 75 dps (a hero plus 5–6 line units at 4–5 minutes) that is ≈ 40 s of fighting before abilities, against ≈ 45 s before. It is still the
toughest step on the early route, which is right for an expansion guard, but no longer the slowest per creep level.

#### G4. Mire Toads *(later)*

- **Concept:** pond and bog toads grown far too large. The biggest wear a small marsh on their backs: reeds, lily pads and one sleeping duck.
- **Look:**
  - Fat, warty bodies with **orange throat sacs** that inflate before a Bellow.
  - Squash-and-stretch hops, eyes on top.
- **Never:** upright fish-folk, spears, nets or gurgled speech (the WC3 shore-creep read; §10.2).
- **Palette:** olive #6B7A3A, mud #6A4E34, belly cream #D8CFA0, throat sac #E08A3A.
- **Production:** one bpy procedural body (metaball remesh) at four scales, AI texture, procedural hop. No rig.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_toad_peeper` | Peeper | 1 | 200 | – | 0 Light | Blade | 7–9 | 1.2 | melee 0.6 | 4.6 | — | *later* |
| `creep_toad_mudgulper` | Mudgulper | 3 | 460 | – | 1 Medium | Blade | 14–18 | 1.6 | melee 0.8 | 4.0 | Tongue Snap | *later* |
| `creep_toad_bellower` | Bellower | 5 | 800 | 150 | 2 Medium | Blade | 24–29 | 1.9 | melee 1.0 | 3.8 | Bellow | *later* |
| `creep_toad_grandmother` | Grandmother Toad | 7 | 1300 | 250 | 3 Medium | Pure | 34–42 | 2.0 | melee 1.2 | 3.6 | Hardy, Mud Wallow | *later* |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Tongue Snap** | Mudgulper | Unit target, 6 m | Pulls a ground unit **4 m** toward itself (heroes 2 m) and slows it 30 % for 2 s. Cooldown 14 s. Prefers ranged units and casters |
| **Bellow** | Bellower | No target, 3.5 m | 60 Spell damage, **stun 1 s** (heroes 0.5 s). 60 mana, cooldown 12 s |
| **Mud Wallow** | Grandmother Toad | Point, 8 m | A 5 m mud pool for 10 s: enemies inside move 40 % slower; she regenerates **2 % of max HP/s** while standing in it. 90 mana, cooldown 20 s |

---

### 2.2 Rimeholt (winter highlands) *(later)*

Mood (visual §7.2): blue-white snow, dark pines, teal ice, warm torchlight accents. Creeps here punish slow armies and ranged-light comps.

#### F1. Stoatkin: ermine raiders *(later)*

- **Concept:** knee-high **stoat-folk** in their white winter coats (black tail-tips), who raid trappers' caches and live in snow burrows.
  Quick, vicious and very proud of their whiskers.
- **Look:**
  - Quilted hide hoods and antler-tine knives; slings of braided sinew.
  - Long, low, bounding silhouettes; the tail-tip is the read.
- **Rules:** generic northern winter gear only. No real Arctic people's dress, motifs or tools.
- **Palette:** ermine white #EDEFF2, tail-tip black #1C1C20, hide brown #7A5C44, berry-red cord #A8343A.
- **Production:** 1 AI biped mesh (small) + props; a 2-bone procedural tail.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_stoat_kit` | Ermine Kit | 1 | 210 | – | 0 Light | Blade | 8–10 | 1.2 | melee 0.6 | 5.0 | Dart |
| `creep_stoat_snowslinger` | Snowslinger | 2 | 250 | – | 0 Medium | Pierce | 10–13 | 1.8 | 6.5 | 4.6 | Packed Snow |
| `creep_stoat_rime_biter` | Rime-Biter | 4 | 560 | – | 1 Medium | Blade | 18–22 | 1.4 | melee 0.7 | 4.8 | Weasel Dance, Throat-Nip |
| `creep_stoat_matriarch` | Ermine Matriarch | 6 | 760 | 250 | 2 Medium | Arcane | 20–25 | 1.9 | 6.5 | 4.6 | Hardy, Pack Fury, Winter Coat |

| Ability | Numbers |
|---|---|
| **Dart** (Kit) | When an allied creep is first hit, +30 % move speed for 3 s |
| **Packed Snow** (Snowslinger) | 20 % chance on hit: the target attacks 20 % slower for 3 s |
| **Weasel Dance** (Rime-Biter) | 20 % chance to evade attacks |
| **Throat-Nip** (Rime-Biter) | 15 % chance to deal ×2 damage |
| **Pack Fury** (Matriarch) | Aura 8 m: allied creeps attack 15 % faster |
| **Winter Coat** (Matriarch) | 2 allied creeps within 8 m turn snow-white and become **invisible for 10 s** (broken by attacking). 90 mana, cooldown 25 s |

#### F2. Whiteouts: snow-squall spirits *(later)*

- **Concept:** knots of blizzard that hold together when the wind drops. They **never sleep**: they *are* the weather.
- **Look:**
  - Spinning cloud bodies with two dark "eye" hollows and trailing snow ribbons. No limbs.
  - The largest one carries a slow ring of floating ice shards.
- **Palette:** snow #E6EEF5, shadow blue #8FA6C4, ice teal #9ED4E8, eye hollows #2F3B52.
- **Armour:** Light. **Pierce deals ×2** (the classic "archers beat spirits" lesson).
- **Production:** bpy cloud mesh, vertex-noise shader and particles. No rig.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_whiteout_flurry` | Flurry | 2 | 240 | 100 | 0 Light | Arcane | 10–12 | 1.7 | 6.0 | 4.4 (float) | Frostnip |
| `creep_whiteout_squall` | Squall | 4 | 480 | 150 | 1 Light | Arcane | 17–21 | 1.8 | 6.0 | 4.6 | Gust |
| `creep_whiteout_whiteout` | Whiteout | 6 | 720 | 250 | 2 Light | Arcane | 24–29 | 1.9 | 6.5 | 4.4 | Hardy, Snowblind, Rime Coat |
| `creep_whiteout_polar_gale` | Polar Gale | 8 | 1500 | 300 | 3 Light | Pure | 40–50 | 1.9 | 6.5 | 4.4 | Hardy, Icefield |

| Ability | Numbers |
|---|---|
| **Frostnip** (Flurry) | Attacks slow movement 10 % for 2 s |
| **Gust** (Squall) | Unit target 7 m: 50 Spell damage, **knockback 3 m**, interrupts channels. 60 mana, cooldown 12 s |
| **Snowblind** (Whiteout) | Point 8 m, radius 4 m, 6 s: enemies inside have **4 m sight** and a **25 % miss chance**. 90 mana, cooldown 18 s |
| **Rime Coat** (Whiteout) | An allied creep is encased in ice for 3 s: invulnerable and stunned, healing 8 % of max HP/s. 75 mana, cooldown 20 s. Used on a creep below 35 % HP |
| **Icefield** (Polar Gale) | Point 9 m, radius 6 m, 8 s: enemies move 35 % slower, turn at half rate and take 15 Spell damage/s. 125 mana, cooldown 20 s |

#### F3. Longfringe Herd *(later)*

- **Concept:** wild, shaggy highland cattle-oxen that winter in the passes. Mostly placid; deeply protective of calves.
- **Look:**
  - Low, wide, curtain-of-hair bodies with sweeping downward horns and frosted fringes.
  - Snow caked on their backs.
- **Never:** a drum-backed grey beast (the WC3 beast-of-burden read) or a tusked mammoth.
- **Palette:** russet fringe #8A5A3A, frost tips #DCE4EA, horn ivory #D8CDB0, nose black #2A2224.
- **Production:** 1 AI quadruped mesh. Quadrupeds rig poorly, so the fallback is a procedural four-leg sway plus rigid legs.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_longfringe_calf` | Longfringe Calf | 2 | 380 | – | 1 Medium | Blade | 11–14 | 1.6 | melee 0.8 | 4.2 | — |
| `creep_longfringe_bull` | Longfringe Bull | 4 | 720 | – | 2 Heavy | Blade | 20–25 | 1.8 | melee 1.0 | 4.2 | Horn Toss |
| `creep_longfringe_herd_bull` | Herd-Bull | 6 | 1050 | – | 3 Heavy | Blade | 30–37 | 2.0 | melee 1.1 | 4.4 | Hardy, Herd Rush |
| `creep_longfringe_grandsire` | Grandsire | 8 | 1700 | – | 4 Heavy | Pure | 44–54 | 2.0 | melee 1.2 | 4.0 | Hardy, Herd Wall, Bellowing Charge |

| Ability | Numbers |
|---|---|
| **Horn Toss** (Longfringe Bull) | Every 5th attack tosses the target: airborne 1 s (stunned) |
| **Herd Rush** (Herd-Bull) | Charges along a 10 m line: 80 Spell damage and 2 m knockback to every enemy in the path. Cooldown 15 s |
| **Herd Wall** (Grandsire) | Aura 6 m: allied creeps take 25 % less damage |
| **Bellowing Charge** (Grandsire) | As Herd Rush, 12 m: 120 Spell damage, knockback 2 m and **stun 1 s** (heroes 0.5 s). Cooldown 16 s |

---

### 2.3 Sunscar Steppe (savanna badlands) *(later)*

Mood (visual §7.2): terracotta earth, bleached grass, sky-blue contrast, salt flats. This is where the Tormai Herd Road crosses the Salt Lakes (`clans.md` §1.3).

#### S1. Claywrights: termite masons *(later)*

- **Concept:** upright, pale termite-folk who are **master clay masons**. Their tall, fluted mound-towers are the most beautiful buildings on the steppe,
  and they defend them as fiercely as any guild defends its hall. The greatest tower is the **Mother-Mound**; its champion leads them.
- **Naming rule:** the people are *Claywrights*, never "mound builders" (a real-world term for pre-Columbian Native American cultures,
  tied to a 19th-century racist myth; ip-safety §3.2 asks us to treat real cultures respectfully). "Mound" stays only for the buildings.
- **Look:**
  - Cream carapace, oversized mandibled heads, four-fingered hands with **plaster trowels and spades**.
  - Wide reed sun-hats on the masons.
- **Never:** a purple-black chitin swarm, spider legs, sand-burrowing ambushers or a giant hive god. The look is craftsfolk,
  not a bug horde (squint risks in §10.2).
- **Palette:** carapace cream #E6D8B8, clay red #B0603A, reed straw #C9A86A, mandible umber #5A3A28.
- **Production:** 1–2 AI biped meshes (mason body; champion body).

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_claywright_mason` | Claywright Mason | 1 | 220 | – | 1 Medium | Blade | 7–9 | 1.5 | melee 0.6 | 4.0 | Clay Plaster |
| `creep_claywright_etch_spitter` | Etch-Spitter | 2 | 260 | – | 0 Medium | Pierce | 10–13 | 1.8 | 6.0 | 4.0 | Etch |
| `creep_claywright_mandible_guard` | Mandible Guard | 3 | 520 | – | 2 Heavy | Blade | 15–19 | 1.6 | melee 0.8 | 4.0 | Lockjaw |
| `creep_claywright_drummer` | Claywright Drummer | 5 | 600 | 250 | 1 Unarmored | Arcane | 18–22 | 1.9 | 6.5 | 4.0 | Clay Rhythm, Call the Mound |
| `creep_claywright_champion` | The Mother-Mound's Champion | 8 | 1750 | – | 5 Heavy | Pure | 42–52 | 1.8 | melee 1.1 | 4.0 | Hardy, Shield the Mound, The Mound Opens |

| Ability | Numbers |
|---|---|
| **Clay Plaster** (Mason) | Unit target, an ally within 5 m: +3 armour for 10 s. Cooldown 15 s |
| **Etch** (Etch-Spitter) | Each hit: −1 armour for 6 s, stacking to −3 |
| **Lockjaw** (Mandible Guard) | Grabs its attack target for 1.5 s: both are rooted and the target cannot attack. Cooldown 14 s |
| **Clay Rhythm** (Drummer) | Aura 8 m: allied Claywrights attack 20 % faster |
| **Call the Mound** (Drummer) | 2 Claywright Masons (summons, 30 s). 90 mana, cooldown 30 s. Used on aggro |
| **Shield the Mound** (Champion) | No target, 4 m: enemy units must attack him for 3 s (taunt). Cooldown 16 s |
| **The Mound Opens** (Champion) | Once, at 50 % HP: a doorway cracks open in the nearest mound-tower and 4 Claywright Masons climb out to his side (summons, 30 s) |

#### S2. Saltbound: the salt-crusted dead *(later)*

- **Concept:** a caravan that died crossing the Salt Lakes and never stopped walking. Salt has preserved them into **glittering crystal-crusted** figures
  that still drive their phantom wagon. They **never sleep**. Tag `dead` (for later anti-dead effects).
- **Look:**
  - Human bipeds in sun-bleached caravan robes; skin and cloth crusted with **white-pink salt crystals** (cubic, faceted).
  - Hollow eyes glowing pale brine-blue.
- **Never:** bones on show, rusted plate armour, green-glowing skulls, ziggurats or blight. Must also differ from the `deathless` faction,
  whose look is not designed yet (cross-check in §11).
- **Palette:** salt white #F2ECE6, rose salt #E8C2C0, robe ochre #C49A5A, brine glow #9FD8E8.
- **Production:** 1 AI biped mesh + a bpy crystal-scatter modifier for the crust variants.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_salt_husk` | Salt Husk | 2 | 360 | – | 1 Medium | Blade | 11–14 | 1.8 | melee 0.8 | 3.4 | Brine Burst |
| `creep_salt_brine_drover` | Brine Drover | 4 | 600 | – | 2 Medium | Blade (whip) | 19–23 | 1.6 | 2.0 | 3.8 | Crack the Whip |
| `creep_salt_seer` | Salt Seer | 5 | 560 | 250 | 0 Unarmored | Arcane | 18–22 | 1.9 | 6.5 | 3.8 | Thirst, Crystallize |
| `creep_salt_caravan_master` | Caravan-Master | 8 | 1650 | 300 | 4 Medium | Pure | 42–50 | 1.8 | melee 1.2 | 3.8 | Hardy, Parching Air, Raise the Caravan |

| Ability | Numbers |
|---|---|
| **Brine Burst** (Husk) | On death: 30 Spell damage and a 20 % slow for 3 s within 2 m |
| **Crack the Whip** (Drover) | No target, 8 m: allied Saltbound attack and move 25 % faster for 6 s. Cooldown 15 s |
| **Thirst** (Seer) | Unit target 8 m: the target loses 4 mana/s and attacks 20 % slower for 8 s. 60 mana, cooldown 12 s |
| **Crystallize** (Seer) | Unit target 7 m: 60 Spell damage and **stun 2 s** (heroes 1 s). 80 mana, cooldown 18 s |
| **Parching Air** (Caravan-Master) | Aura 8 m: enemy units lose 1.5 HP/s |
| **Raise the Caravan** (Caravan-Master) | Once, on first aggro: 3 Salt Husks claw up out of the salt (summons, 40 s) |

#### S3. Rollbacks: giant dung-beetles *(later)*

- **Concept:** cart-sized beetles that roll balls of dung and gravel across the steppe **by starlight**. Real dung-beetles steer by the night sky,
  so these are the Sunscar night-active family (§1.5).
- **Look:**
  - Iridescent brass-green and bronze shells, spade-edged heads, bristly legs.
  - Each one pushes a ball bigger than itself.
- **Never:** undead, burrowing-spike attacks, carrion swarms (the WC3 beetle-summon read).
- **Palette:** shell brass-green #5E7A4A to #A88C3A (iridescent shift), leg umber #4A3628, ball #7A6248.
- **Production:** bpy procedural. A shell mesh, six rigid two-segment legs with a sine gait, and a rolling ball (a sphere with noise). No rig.
- **Dung Crust:** a caked crust of dried dung and grit on every shell: −25 % damage from Pierce, for every Rollback.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_roller_dung` | Dung Roller | 2 | 420 | – | 2 Heavy | Blade | 11–14 | 1.7 | melee 0.8 | 3.8 | Dung Crust |
| `creep_roller_boulder` | Boulder Roller | 4 | 700 | – | 3 Heavy | Blade | 20–25 | 1.8 | melee 0.9 | 3.8 | Dung Crust, Ball Roll |
| `creep_roller_horned` | Horned Roller | 6 | 1000 | – | 4 Heavy | Blade | 30–36 | 1.9 | melee 1.0 | 4.0 | Hardy, Dung Crust, Horn Lift |
| `creep_roller_matriarch` | Brass-Shell Matriarch | 8 | 1700 | 200 | 5 Heavy | Pure | 44–52 | 2.0 | melee 1.2 | 3.8 | Hardy, Dung Crust, Shell-Flash |

| Ability | Numbers |
|---|---|
| **Ball Roll** (Boulder Roller) | Rolls its ball along a 12 m line: 70 Spell damage and 2 m knockback to every enemy hit. Cooldown 14 s |
| **Horn Lift** (Horned Roller) | Every 4th attack flips the target: airborne 1 s (stunned) |
| **Shell-Flash** (Matriarch) | No target, 6 m: 80 Spell damage, and enemies are **blinded (30 % miss)** for 5 s. 90 mana, cooldown 18 s |

---

## 3. Camp templates

### 3.1 Drop table by camp total level

Our bands follow the *shape* of Blizzard's melee-map guideline (mechanics §5): one small item for small camps, a small plus a big item
for larger ones, an artifact only for the hardest camps. "Any" means permanent, charged or power-up (purchasables never drop).

| Camp total level | Drop A (carried by the lowest-level creep) | Drop B (carried by the highest-level creep) |
|---|---|---|
| 1–4 | — | — |
| 5–7 | — | L1 power-up |
| 8–9 | — | L2 any |
| 10–13 | L1 power-up | L2 permanent |
| 14–17 | L1 power-up | L3 permanent or charged |
| 18–21 | L2 any | L4 permanent |
| 22–24 | L2 any | L5 permanent or charged |
| 25–29 | L2 power-up | L6 permanent or charged |
| 30+ | L3 any | L7 artifact |
| Map boss (designer-placed, named) | L3 any | L8 artifact (may be fixed) |

### 3.2 Template columns

**XP** is the raw sum before the hero's creep factor. **Gold** is the average total bounty. **Mode:** `camp` (fights only when engaged)
or `guard` (also attacks buildings started within 12 m; used at expansion gold mines). **Sleeps** is the family default unless the row
says *override* (`sleeps_override`, §1.5). Optional per-template fields: `sleeps_override`, `acquire_override` (§1.3) and `layout` (§1.9).

### 3.3 Greenvale templates

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode | Props and placement | Slice |
|---|---|---|---|---|---|---|---|---|---|---|
| `camp_gv_charcoal_clamp` | Green | Cutpurse ×3, Smoker | 5 | 115 | 36 | B: L1 power-up | Night | camp | Smoking clamp, lean-to, cordwood. Near each start, beside the natural path | **[SLICE]** ×2 |
| `camp_gv_turnip_patch` | Green | Fieldkeeper ×2, Strawling ×2 | 8 | 170 | 48 | B: L2 any | **Night** (*override*: tame scarecrows that guard by day) | camp | Turnip rows, poles, a crow-picked haystack. The other side of each start | **[SLICE]** ×2 |
| `camp_gv_colliers_hut` | Green | Collier, Smoker ×2, Cutpurse | 8 | 165 | 48 | B: L2 any | Night | camp | A sooty cottage with a small clamp. 40–50 m path from each main hall on the own side, away from the Charcoal Clamp (exact spot: slice-plan §1.8) | **[SLICE]** ×2 |
| `camp_gv_toad_pond` | Green | Mudgulper, Peeper ×4 | 7 | 160 | 48 | B: L1 power-up | Night | camp | Reed pond | *later* |
| `camp_gv_smugglers_den` | **Amber** | Kiln-Master, Collier, Smoker, Cutpurse | 11 | 240 | 60 | A: L1 power-up; B: L2 permanent | Night | camp | Guards the central **Weighstall**. Explicit `layout`: one creep 3.5 m out from each of the stall's four corners, facing out. `acquire_override: 6.5`, so every spot within the 7.0 m use range is inside an awake Den creep's acquire range (computed need with four creeps: 6.4 m; test `shop_guard_coverage`, §9) | **[SLICE]** ×1 |
| `camp_gv_crow_field` | **Amber** | Crowcaller, Fieldkeeper ×2, Strawling ×2 | 12 | 255 | 68 | A: L1 power-up; B: L2 permanent | **Day** (the map's one day camp) | camp | Scarecrow field around the **Hale Spring**: free to use by day, guarded by night | **[SLICE]** ×1 |
| `camp_gv_drystone_fold` | **Amber** | Drystone Walker, Cairnling ×3 | 14 | 295 | 72 | A: L1 power-up; B: L3 permanent | Never | **guard** | Broken sheep-fold walls around each **expansion** Gold Seam | **[SLICE]** ×2 |
| `camp_gv_withy_field` | Amber | Withy Brute, Crowcaller, Fieldkeeper ×2, Strawling ×2 | 17 | 370 | 92 | A: L1 power-up; B: L3 permanent or charged | Day (it replaces the Crow Field as the map's one day camp) | camp | Upgrade of Crow Field when the Withy Brute exists | [SLICE+] |
| `camp_gv_bellow_marsh` | Amber | Bellower ×2, Mudgulper, Peeper ×2 | 15 | 340 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp | Marsh | *later* |
| `camp_gv_standing_ring` | **Red** | Menhir Elder, Drystone Walker ×2, Cairnling | 20 | 480 | 96 | A: L2 any; B: L4 permanent | Never | camp | A ring of standing stones in a contested centre-flank pocket | **[SLICE]** ×1 |
| `camp_gv_grandmothers_bog` | Red | Grandmother Toad, Bellower ×2, Peeper ×4 | 21 | 520 | 112 | A: L2 any; B: L4 permanent | Night | camp | Deep bog | *later* |
| `camp_gv_clamp_fathers_yard` | Red | Clamp-Father, Kiln-Master, Collier ×2, Smoker ×2 | 22 | 505 | 112 | A: L2 any; B: L5 permanent or charged | Night | camp | Big clamp and a charcoal-burners' hall | *later* |
| `camp_gv_dolmen_hill` | Red | Dolmen Colossus, Menhir Elder, Drystone Walker ×2 | 26 | 705 | 120 | A: L2 power-up; B: L6 permanent or charged | Never | camp | A dolmen on a hilltop | *later* |
| `camp_gv_harvest_court` | Red (boss) | Old Mangold, Withy Brute ×3, Crowcaller ×2 | 31 | 750 | 148 | A: L3 any; B: **fixed** Mangold Lantern or Old Mangold's Sickle (seeded) | Day (a map that uses it sets its other Tattiebogles camps to `night`) | camp | A harvest-home barn with a giant mangold lantern | *later* |

### 3.4 Rimeholt templates *(later)*

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode |
|---|---|---|---|---|---|---|---|---|
| `camp_rh_stoat_warren` | Green | Ermine Kit ×3, Snowslinger ×2 | 7 | 155 | 48 | B: L1 power-up | Night | camp |
| `camp_rh_calf_drift` | Green | Longfringe Bull, Longfringe Calf ×2 | 8 | 165 | 44 | B: L2 any | Night | camp |
| `camp_rh_squall_line` | Amber | Squall ×2, Flurry ×3 | 14 | 290 | 76 | A: L1 power-up; B: L3 permanent or charged | Never | guard (expansion) |
| `camp_rh_longfringe_herd` | Amber | Herd-Bull, Longfringe Bull ×2, Longfringe Calf | 16 | 360 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp |
| `camp_rh_matriarchs_den` | Red | Ermine Matriarch, Rime-Biter ×3, Snowslinger ×2 | 22 | 485 | 112 | A: L2 any; B: L5 permanent or charged | Night | camp |
| `camp_rh_whiteout_peak` | Red | Polar Gale, Whiteout ×2, Squall, Flurry | 26 | 660 | 124 | A: L2 power-up; B: L6 permanent or charged | Never | camp |

### 3.5 Sunscar templates *(later)*

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode |
|---|---|---|---|---|---|---|---|---|
| `camp_ss_mound_gate` | Green | Mandible Guard, Etch-Spitter, Claywright Mason ×2 | 7 | 150 | 44 | B: L1 power-up | Night | camp |
| `camp_ss_dung_trail` | Green | Dung Roller ×3 | 6 | 120 | 36 | B: L1 power-up | Day | camp |
| `camp_ss_salt_wagon` | Amber | Salt Seer, Brine Drover, Salt Husk ×2 | 13 | 280 | 68 | A: L1 power-up; B: L2 permanent | Never | guard (expansion) |
| `camp_ss_boulder_run` | Amber | Horned Roller, Boulder Roller ×2 | 14 | 320 | 68 | A: L1 power-up; B: L3 permanent or charged | Day | camp |
| `camp_ss_drum_mound` | Amber | Claywright Drummer, Mandible Guard ×2, Etch-Spitter ×2 | 15 | 315 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp |
| `camp_ss_dead_caravan` | Red | Caravan-Master, Salt Seer, Brine Drover ×2, Salt Husk | 23 | 560 | 112 | A: L2 any; B: L5 permanent or charged | Never | camp |
| `camp_ss_mother_mound` | Red | The Mother-Mound's Champion, Claywright Drummer, Mandible Guard ×3, Etch-Spitter | 24 | 570 | 120 | A: L2 any; B: L5 permanent or charged | Night | camp |

The Dung Trail and the Boulder Run are both `day` by family default. A Sunscar map keeps at most one of them as `day` and sets the other to
`night` with `sleeps_override` (§1.5 map rule 1).

### 3.6 Slice map: the neutral layout (Greenvale, 96 × 96 tiles = 192 m)

Two starts in opposite corners, rotationally symmetric. Written from rules (ip-safety §2.6), not from any existing map.
Distances are hall-centre to camp-centre.

| Neutral | Count | Where | Why |
|---|---|---|---|
| Gold Seam (main, 12,000) | 2 | At each start, **6.0 m** hall edge to seam edge (rules §3.3) | Global economy rule; the 5-worker saturation maths needs the 6.0 m gap |
| Gold Seam (expansion, 8,000) + **Drystone Fold** (amber 14, guard mode) | 2 | One natural expansion per player, **40–60 m path distance** from the main, on lower ground; exact positions in slice-plan §1.4 | Never-sleep guards: the expansion costs a real fight at any hour |
| **Charcoal Clamp** (green 5) | 2 | 28–35 m from each main, beside the natural path | First creep at about 2:00 (both faction build orders) |
| **Turnip Patch** (green 8) | 2 | 35–45 m from each main, the other side | Second creep. It sleeps at night like most camps (tame scarecrows, §1.5) |
| **Collier's Hut** (green 8) | 2 | 40–50 m path from each main, on the own side, away from the Clamp; at least 25 m from the Clamp and the Patch and 14 m off any lane centreline | Third own-side creep, so level 3 comes from creeps by about 5:30; it reuses slice creep types (0 new assets) |
| **Weighstall** + **Smugglers' Den** (amber 11) | 1 | Map centre | Potions and recall are contested. By day every buying spot is inside the Den's acquire range. At night the Den sleeps, so you can walk up unseen, but the purchase wakes it with you in range |
| **Hale Spring** + **Crow Field** (amber 12, the one day camp) | 1 | On the side lane that is *not* the shortest attack path | Free healing by day, a guarded spring by night |
| **Standing Ring** (red 20) | 1 | Opposite flank to the spring, equidistant from both starts | The big prize (L2 + L4); never sleeps, so it is never a free kill |
| Critters | 10–14 | Hand-placed (slice-plan §1.9: 6 hares in the meadows, 4 geese at the ponds), fireflies by water at night | Ambience |
| **Coaching Inn** [SLICE: revive only] | 1 | Unguarded, at (106, 106) in the centre basin, about 14 m from the Weighstall (slice-plan §1.4) | Never guarded (*Why:* the WC3 convention). Instant revive is the comeback tool; hiring the Rat-Piper is [SLICE+] |
| [SLICE+] **Beacon Cairn** | 2 | On the two high ground knolls overlooking the centre | Vision fights |

**Totals on the slice map:** 11 camps (6 green, 4 amber, 1 red), 113 total creep levels, **2,465 raw XP** and about **632 gold** in bounty
(plus whatever the Cutpurses steal). Each player's half holds 745 raw XP (Clamp 115, Patch 170, Hut 165, Fold 295); the three shared camps
(Den 240, Crow Field 255, Ring 480) hold 975. So one player can collect about **1,230 raw XP** from creeps; reaching hero level 4 from
creeps alone needs 1,346 raw (250 + 429 + 667 at 80 / 70 / 60 %), so the last steps come from killing enemy units, as in WC3.

**XP check against the faction build orders** (`kingdom.md` §10 and `clans.md` §10 both aim for hero level 3 by about 5:30).
The hero must be at every camp (XP with no hero in range is lost, §1.6). Factor changes mid-camp when the hero levels.

| Step | Raw XP | Factor | Hero XP (running) | Level | Clock (clans §10) |
|---|---|---|---|---|---|
| Charcoal Clamp at level 1 | 115 | 80 % | 92 | 1 | ≈ 2:00–3:10 |
| Turnip Patch at level 1 (level 2 at 200, partway through) | 170 | 80 % → 70 % | ≈ 225 | **2** | ≈ 4:20 |
| Collier's Hut at level 2 | 165 | 70 % | ≈ 340 | 2 | ≈ 4:50 |
| Own Drystone Fold at level 2 (level 3 at 500, partway through) | 295 | 70 % → 60 % | ≈ 540 | **3** | ≈ 5:30 (tight; 5:45 if the Fold fight runs long, §2.1) |
| Den or Crow Field, plus 3–4 enemy unit kills at full XP | 240–255 | 60 % | ≈ 690 + unit kills | 3 → **4** near 900 | after 6:00 |
| Standing Ring at level 4 (with an army) | 480 | 50 % | + 240 | 4 → 5 with fighting | mid-game |

This matches the slice plan's "Standing Ring at hero level 4–5 plus an army". **Known gap:** after T2 a second hero finds little left
to creep on this map. *Later:* add one more amber camp per side (a Withy Field or Bellow Marsh-sized camp) so the second hero has creep XP (§11).

---

## 4. Items

### 4.1 Rules

| Rule | Value |
|---|---|
| **Classes** | **Purchasable** (shop stock; never drops) · **Power-up** (used the moment it is picked up) · **Permanent** (passive while carried) · **Charged** (limited uses, then gone) · **Artifact** (level 7–8; permanent, some with an active) |
| **Levels** | 1–8. Level sets the drop band (§3.1) and the sell value |
| **Who carries** | Heroes only, **6 slots**. Exception: **food power-ups** (Wild Strawberries) can be picked up by any unit, and act at once |
| **Hotkeys** | Numpad 7 / 8 / 4 / 5 / 1 / 2 (the classic grid) and Alt+1–6 (for keyboards without a numpad). Right-click an item with a hero to pick it up (within 1.0 m); drag it onto **another own hero within 1.5 m** to give it; drag it onto the ground to drop it (rules §6.8) |
| **Buying** | **Buying an item needs an own hero within the use range** (7.0 m, §5.1). Any own unit can hire or use a service. The item goes to the selected hero if it is in range, else to the nearest own hero in range with a free slot; if every hero in range is full, it **drops at that hero's feet** (rules §16) |
| **Death** | A dying hero keeps its items (revives with them) |
| **Charges** | Identical purchasable consumables merge into one slot, up to 2 × their base charges (tuning flag) |
| **Stacking** | Different items stack additively (rules §6.8). Items flagged **`unique`** do not stack with another item of the same unique group; the highest applies: move speed (Wanderer's Hobnails, Coilspring Heels), evasion (Thistledown Cloak), and each aura item (Drillmaster's Pace-Stick, Shepherd's Crook; two of the same give one aura) |
| **Shared cooldowns** | Item actives share a cooldown per **`cooldown_group`** (default: the item id), per hero (rules §6.8). Rosehip Draught is in group `heal`, Bluebell Cordial in group `mana`, with the faction shops' instant heals and mana items. Proposed: `rules.items.group_cooldown.heal = 8 s`, `rules.items.group_cooldown.mana = 8 s` (§9) |
| **Selling** | At the Weighstall or Lucky Barrow, for **50 % of value** (charged items: × remaining / base charges). Taxed by upkeep. Power-ups cannot be sold (they are never carried) |
| **Ground look** | A twine-tied oilcloth bundle with a wax seal (§1.8); power-ups show as their own small props |
| **Text** | Every name and tooltip is written from scratch (ip-safety §2.2). No WC3 item name or tooltip wording |

**Slice effect scripts** (14, all simple): `stat_bonus`, `heal_instant`, `mana_instant`, `heal_area_over_time`, `recall_to_hall`
(now point-targeted, §4.2), `place_ward`, `reveal_invisible_area`, `self_invisibility`, `vision_flare`, `grant_xp`, `grant_gold`,
`heal_area_on_pickup`, **`grant_attribute`** (permanent attribute gains from power-ups) and **`retrain`** (Wiped Slate).
[SLICE+] adds **`self_invulnerable`** (Curl-Up Scale). *Later:* `teleport_to_own_structure`, `armor_area_buff`.

### 4.2 Purchasable (sold at the Weighstall unless noted; stock is per player)

| id | Name | Lvl | Charges | Effect | Cooldown (group) | Price | Stock / restock | From | Slice |
|---|---|---|---|---|---|---|---|---|---|
| `item_rosehip_draught` | Rosehip Draught | 1 | 1 | Restores **260 HP** at once | 8 s (`heal`) | 150 g | 3 / 45 s | 0:00 | **[SLICE]** |
| `item_bluebell_cordial` | Bluebell Cordial | 1 | 1 | Restores **160 mana** at once | 8 s (`mana`) | 110 g | 3 / 45 s | 0:00 | **[SLICE]** |
| `item_homing_pigeon` | Homing Pigeon | 1 | 1 | **Target a point** (minimap clicks work): the pigeon flies to your finished hall nearest that point; press the hotkey twice to send it to your highest-tier hall. After a **5 s** channel the hero and up to 11 of your non-structure units within 6 m vanish in a puff of feathers and reappear beside that hall. Enemy stuns, silences and damage **do not cancel it**; only the hero's death or your own Stop or move order does. The charge is spent when it completes | — | 325 g | 2 / 120 s | 0:00 | **[SLICE]** |
| `item_snoop_peg` | Snoop Peg | 1 | 2 | Hammers in an invisible peg within 5 m: **13 m vision for 240 s** (25 HP). It sees no invisible units | — | 80 g | 2 / 60 s | 0:00 | **[SLICE]** |
| `item_flour_bomb` | Flour Bomb | 1 | 2 | Bursts at a point within 8 m: invisible units within **9 m** are revealed, and stay revealed for **12 s** wherever they go (they are dusted) | — | 60 g | 2 / 60 s | 0:00 | **[SLICE]** (counters the Uncut's Dust Veil) |
| `item_picnic_hamper` | Picnic Hamper | 2 | 1 | Your and allied non-structure units within **7 m** restore **180 HP over 6 s** | — | 200 g | 2 / 90 s | 3:00 | **[SLICE]** |
| `item_wanderers_hobnails` | Wanderer's Hobnails | 2 | — (permanent) | **+0.7 m/s** move speed. *Unique* (move speed) | — | 200 g | 1 / 120 s | 4:00 | **[SLICE]** |
| `item_stoutheart_weight` | Stoutheart Weight | 2 | — (permanent) | A stamped brass shop-weight hung from the belt, "true to the grain": **+175 max HP** (`stat_bonus`) | — | 300 g | 1 / 120 s | 4:00 | **[SLICE]** |
| `item_wiped_slate` | Wiped Slate | 3 | 1 | Wipe the tally-slate clean: the hero **forgets every learned ability** and gets all its skill points back to spend again, the ultimate included (`retrain`). Cannot be used while the hero is channelling | — | 280 g | 1 / 300 s | 5:00 | **[SLICE]** |
| `item_curl_up_scale` | Curl-Up Scale | 2 | 1 | Snap a shed Rundling scale: a shell of overlapping brass scales closes over the hero for **6 s**. The hero is **invulnerable** but cannot move, attack, cast or use items; buffs and debuffs keep ticking (`self_invulnerable`) | — | 140 g | 1 / 90 s | 6:00 | [SLICE+] |
| `item_coilspring_heels` | Coilspring Heels | 4 | 3 | Leap to a point within **9 m** (over units, not up cliffs). *Unique* (move speed) | 15 s | 325 g | 1 / 180 s | 8:00 | *later* |
| `item_pocket_signpost` | Pocket Signpost | 3 | 2 | Unfold a tiny signpost and point it at one of your structures anywhere on the map: after a **3 s** channel the hero alone appears beside it (`teleport_to_own_structure`). Stuns, silences, the hero's death or your own orders cancel it. **Lucky Barrow only** (fixed slot) | 30 s | 250 g | 1 / 120 s | 10:00 | *later* |
| `item_oilcloth_capes` | Oilcloth Capes | 3 | 1 | Throw out a bundle of oilcloth capes: your non-structure units within **9 m** gain **+3 armour for 20 s** (`armor_area_buff`). **Lucky Barrow only** (fixed slot) | — | 175 g | 1 / 90 s | 8:00 | *later* |

- **Homing Pigeon data:** `"target": "point_nearest_own_hall", "channel": 5.0, "enemy_interruptible": false`. *Why:* the classic return
  scroll targets a hall the player picks and cannot be stopped once started, which is what saves an army; a stun-cancelled, nearest-hall
  recall loses that (mechanics §11.4). Rules §6.8's recall row, and so the faction recall items (Homeward Horn, Homeward Felt), should
  change the same way; until they do, this is a Δ to list in rules §21 (follow-up, §11).
- **Mid-game merchant choices** (the Stoutheart Weight, Wiped Slate and Curl-Up Scale) give the 4–8 minute shop visit a decision beyond
  potions. Objects are chosen so no item pairs a WC3 object with its WC3 effect (a pendant for +HP, a book for retraining, a potion for
  invulnerability, a staff for teleport, a scroll for armour; §10.2).

### 4.3 Power-ups (drop only; used on pickup)

| id | Name | Lvl | Effect | Picked up by | Ground prop | Slice |
|---|---|---|---|---|---|---|
| `item_horseshoe_nail` | Smith's Horseshoe Nail | 1 | **+1 STR**, permanently: bend it straight and feel stronger (`grant_attribute`) | Heroes | A bent iron horseshoe nail | **[SLICE]** |
| `item_jugglers_ball` | Juggler's Ball | 1 | **+1 AGI**, permanently (`grant_attribute`) | Heroes | A patched leather juggling ball in faded undyed and ochre patches | **[SLICE]** |
| `item_riddle_knot` | Riddle Knot | 1 | **+1 INT**, permanently: untie it and learn the trick (`grant_attribute`) | Heroes | A hemp puzzle-knot on a wooden toggle | **[SLICE]** |
| `item_wild_strawberries` | Wild Strawberries | 1 | Your non-structure units within 6 m restore **200 HP** | **Any unit** | A leaf of berries | **[SLICE]** |
| `item_dropped_purse` | Dropped Purse | 1 | **+75 gold** to the owner (taxed by upkeep) | Heroes | A drawstring purse | **[SLICE]** |
| `item_hedge_almanac` | Hedge Almanac | 2 | **+1 to all three attributes**, permanently (`grant_attribute`) | Heroes | A thick almanac tied with string: the only book among the items (no clasp, no glow, no coloured cover code) | **[SLICE]** |
| `item_old_soldiers_tally_stick` | Old Soldier's Tally-Stick | 2 | **+100 XP**, never reduced by the creep XP factor (respects the level cap) | Heroes | A notched hazel tally-stick, one notch per battle | **[SLICE]** |

The three attribute power-ups are deliberately **three different objects** (iron, leather, cord), with no colour code per attribute.
*Why:* a red / green / blue book trio for STR / AGI / INT, lying on the ground as books, mirrors the WC3 tome family (§10.2).

### 4.4 Permanent (drop only; Lucky Barrow may stock them)

| id | Name | Lvl | Effect | Value | Slice |
|---|---|---|---|---|---|
| `item_plow_horse_brass` | Plow-Horse Brass | 2 | +3 STR (a polished harness brass, worn as a badge) | 300 | **[SLICE]** |
| `item_hares_foot_charm` | Hare's-Foot Charm | 2 | +3 AGI | 300 | **[SLICE]** |
| `item_inkhorn_pendant` | Inkhorn Pendant | 2 | +3 INT | 300 | **[SLICE]** |
| `item_whetstone_fob` | Whetstone Fob | 2 | +5 attack damage | 300 | **[SLICE]** |
| `item_tin_gorget` | Tin Gorget | 2 | +2 armour | 300 | **[SLICE]** |
| `item_dewdrop_locket` | Dewdrop Locket | 2 | +0.6 mana/s | 300 | **[SLICE]** |
| `item_moss_amulet` | Moss Amulet | 3 | +2.5 HP/s | 450 | **[SLICE]** |
| `item_four_leaf_brooch` | Four-Leaf Brooch | 3 | +2 STR, +2 AGI, +2 INT | 450 | **[SLICE]** |
| `item_woodpecker_quill` | Woodpecker Quill | 3 | +12 % attack speed (a barred woodpecker feather in the hat-band) | 450 | **[SLICE]** |
| `item_millstone_yoke` | Millstone Yoke | 4 | +6 STR (a carrying yoke with two small millstone weights) | 650 | **[SLICE]** |
| `item_fox_fur_mantle` | Fox-Fur Mantle | 4 | +6 AGI | 650 | **[SLICE]** |
| `item_lensgrinders_monocle` | Lensgrinder's Monocle | 4 | +6 INT | 650 | **[SLICE]** |
| `item_blackthorn_knuckles` | Blackthorn Knuckles | 4 | +10 attack damage | 650 | **[SLICE]** |
| `item_thistledown_cloak` | Thistledown Cloak | 4 | 15 % chance to evade attacks. *Unique* (evasion) | 650 | *later* |
| `item_drillmasters_pace_stick` | Drillmaster's Pace-Stick | 5 | Aura 9 m: allied units deal **+12 %** attack damage (the hero taps out the marching pace with a brass-capped stick). *Unique* | 850 | *later* |
| `item_shepherds_crook` | Shepherd's Crook | 5 | Aura 9 m: allied units **+2 armour** and +6 % move speed (the flock is kept together). *Unique* | 850 | *later* |
| `item_nettle_sting_oil` | Nettle-Sting Oil | 5 | Attacks sting: **5 Spell damage/s** and 20 % slow for 3 s (heroes 1.5 s) | 850 | *later* |
| `item_ravening_torc` | Ravening Torc | 5 | Attacks heal the wearer for **15 %** of damage dealt | 850 | *later* |
| `item_hedge_witchs_knot` | Hedge-Witch's Knot | 6 | +150 HP. Blocks one targeted enemy spell every **35 s** (the knot visibly unties, then re-ties) | 1100 | *later* |
| `item_lodestone_ring` | Lodestone Ring | 6 | +4 STR, +4 AGI, +4 INT, +1 armour | 1100 | *later* |

### 4.5 Charged (drop only)

| id | Name | Lvl | Charges | Effect | Cooldown | Value | Slice |
|---|---|---|---|---|---|---|---|
| `item_smoke_pellets` | Smoke Pellets | 2 | 2 | The hero becomes **invisible for 10 s** (0.6 s fade); attacking or casting breaks it | 20 s | 200 | **[SLICE]** |
| `item_firefly_jar` | Firefly Jar | 2 | 3 | Releases fireflies over a point within **30 m**: **10 m vision for 20 s** (no true sight) | 10 s | 200 | **[SLICE]** |
| `item_straw_double` | Straw Double | 3 | 3 | Creates a straw double of one of your units within 6 m for **45 s**. It looks real to the enemy, deals no damage and takes **250 %** damage | 10 s | 320 | *later* |
| `item_salt_circle` | Salt Circle | 3 | 2 | Throws a ring of salt at a point within 8 m (radius 4 m): removes buffs from enemies and debuffs from allies; summoned units take **350** damage | 15 s | 320 | *later* |
| `item_free_company_horn` | Free Company Horn | 5 | 1 | Calls **3 mercenaries of the map's tileset** for 45 s (Greenvale: Sootcoat Colliers; level 3 summons) | — | 500 | *later* |
| `item_cats_ninth_life` | Cat's Ninth Life | 6 | 1 | When the hero dies, it rises where it fell after **4 s** with **600 HP and 150 mana**. Consumed | — | 700 | *later* |
| `item_bottled_thunderhead` | Bottled Thunderhead | 6 | 2 | Uncorks a storm cloud over a point within 10 m (radius 5 m): **35 Spell damage/s for 6 s**; buildings take 50 % | 15 s | 700 | *later* |

### 4.6 Artifacts (drop only, red and boss camps)

| id | Name | Lvl | Effect | Value | Slice |
|---|---|---|---|---|---|
| `item_dolmen_keystone` | Dolmen Keystone | 7 | +4 STR, +4 AGI, +4 INT, +2 armour (a fist-sized capstone charm carried in a net bag) | 1400 | *later* |
| `item_mangold_lantern` | Mangold Lantern | 7 | **True sight 9 m.** The hero's night sight equals its day sight, and it moves +0.5 m/s at night | 1400 | *later* |
| `item_old_mangolds_sickle` | Old Mangold's Sickle | 7 | +15 attack damage; melee attacks **cleave 30 %** to enemies within 1.5 m in front | 1400 | *later* |
| `item_heart_of_the_hill` | Heart of the Hill | 8 | +450 HP, +4 HP/s, +3 armour | 1800 | *later* |
| `item_hill_mist_shawl` | Hill-Mist Shawl | 8 | +4 AGI. Active (90 s cooldown): your units within 9 m become **invisible for 10 s** (0.75 s fade; attacking or casting breaks it per unit) | 1800 | *later* |

**Count:** 13 purchasable + 7 power-up + 20 permanent + 7 charged + 5 artifact = **52 items** (**31 in the slice**, 32 with the [SLICE+] Curl-Up Scale).
The brief asked for about 40. The extra drop items make sure every class-and-level cell used by a drop band has at least two candidates,
so a drop is never fully predictable; the five extra purchasables give the merchant its mid-game choices (§4.2).

### 4.7 Drop pools (class × level)

| Level | Power-up | Permanent | Charged | Artifact |
|---|---|---|---|---|
| 1 | Smith's Horseshoe Nail, Juggler's Ball, Riddle Knot, Wild Strawberries, Dropped Purse | — | — | — |
| 2 | Hedge Almanac, Old Soldier's Tally-Stick | Plow-Horse Brass, Hare's-Foot Charm, Inkhorn Pendant, Whetstone Fob, Tin Gorget, Dewdrop Locket | Smoke Pellets, Firefly Jar | — |
| 3 | — | Moss Amulet, Four-Leaf Brooch, Woodpecker Quill | Straw Double, Salt Circle | — |
| 4 | — | Millstone Yoke, Fox-Fur Mantle, Lensgrinder's Monocle, Blackthorn Knuckles, Thistledown Cloak | — | — |
| 5 | — | Drillmaster's Pace-Stick, Shepherd's Crook, Nettle-Sting Oil, Ravening Torc | Free Company Horn | — |
| 6 | — | Hedge-Witch's Knot, Lodestone Ring | Cat's Ninth Life, Bottled Thunderhead | — |
| 7 | — | — | — | Dolmen Keystone, Mangold Lantern, Old Mangold's Sickle |
| 8 | — | — | — | Heart of the Hill, Hill-Mist Shawl |

- "L2 any" draws from all 10 level-2 entries. "L3 permanent or charged" draws from the 5 level-3 entries.
- In the slice, pools contain only **[SLICE]** items. So L3 draws from the 3 permanents, and L4 from 4 permanents (no Thistledown Cloak).
- Each pool entry has a `weight` (default 1). The three attribute power-ups have weight 1 each, so an "L1 power-up" is an attribute
  power-up 60 % of the time.

---

## 5. Neutral buildings

### 5.1 Overview

All neutral buildings belong to `NEUTRAL_PASSIVE`, are **invulnerable**, grant no vision and are used by having one of your units within
**7.0 m of the building's edge** (`rules.neutral.use_range`, rules §16). Buying an item needs an own hero in that range; hiring and services
need any own unit (§4.1). Items go to your selected hero if it is in range, otherwise to your nearest hero in range with a free slot, otherwise
they drop at that hero's feet. A purchase or hire wakes sleeping creeps within 10 m (§1.5).

| id | Name | Function | Footprint (cells) | Guarded by | Slice |
|---|---|---|---|---|---|
| `gold_mine` (display **Gold Seam**) | Gold Seam | Gold source | 8×8 | Expansions: a guard-mode amber camp | **[SLICE]** ×4 |
| `neutral_weighstall` | Weighstall | Merchant: consumables, recall, wards, reveal, boots, a permanent HP item, skill reset; buys items | 8×8 | Amber 9–15 | **[SLICE]** ×1 |
| `neutral_lucky_barrow` | Lucky Barrow | Rotating stronger items; two fixed late items | 4×4 | Amber 10–15 | *later* |
| `neutral_coaching_inn` | Coaching Inn (per-map sign name; Greenvale: *The Muddy Lantern*) | Instant revive; neutral heroes | 10×10 | **Never guarded** | **[SLICE]** (revive only); hiring the Rat-Piper [SLICE+] |
| `neutral_free_company_camp` | Free Company Camp | Hire local creep types | 10×10 | Amber 9–15 | [SLICE+] |
| `neutral_hale_spring` | Hale Spring | Area health regeneration | 6×6 | Amber 10–14 | **[SLICE]** ×1 |
| `neutral_dewstone` | Dewstone | Area mana regeneration | 4×4 | Amber 10–14 | [SLICE+] |
| `neutral_contraption_barn` | Contraption Barn | Lumber machine, balloon transport, ram, tree-clearing crew | 10×10 | Amber 12–15 | *later* |
| `neutral_twin_milestones` | Twin Milestones | Paired teleport | 2×2 each | Unguarded | *later* |
| `neutral_beacon_cairn` | Beacon Cairn | Capturable vision cairn | 4×4 | Unguarded | [SLICE+] ×2 |

**Command cards** (Classic preset, rules §18.4; letters unique per card; the 4×3 grid is the genre convention, our own button art):

| Card | Buttons (letter) | Notes |
|---|---|---|
| **Weighstall** | Rosehip Draught **R**, Bluebell Cordial **B**, Homing Pigeon **H**, Snoop Peg **P**, Flour Bomb **F**, Picnic Hamper **K**, Wanderer's Hobnails **W**, Stoutheart Weight **T**, Wiped Slate **L**, Curl-Up Scale **C** [SLICE+], Coilspring Heels **J** *(later)*, **Select Patron Tab** | 11 items + Select Patron fill the 12 slots. Each item button shows a **stock-count badge** (bottom right) and a **restock sweep** when the count is below max. Items not yet on sale are greyed with the tooltip "On the counter from 4:00" (their own time). Greyed too when no own hero is in range ("Bring a hero to the counter"). **Select Patron** cycles which of your units in range receives the item. **Sell:** drag an item from a hero's inventory onto the shop, or right-click the item and click the shop |
| **Lucky Barrow** *(later)* | Four rotating slots **Q W E R**, Pocket Signpost **G**, Oilcloth Capes **O**, Select Patron **Tab** | The rotating slots show the reroll countdown as a sweep across all four |
| **Coaching Inn** | One hire button per neutral hero: Rat-Piper **R**, Old Menhir **M** *(later)*, Weighmaster **W** *(later)*; one **Revive** button per own dead hero, letters **V / B / N** in hero-slot order; **Select Patron Tab** | Hire buttons show the hero portrait and "425 / 135, 5 food" (or "Free" while the first-hero token is unused); they grey out for everyone once the hero is taken ("Hired by another commander") or when no hero slot is free. Revive buttons show that hero's rules §6.7 cost for its level and grey out without 5 free food. In the slice the card holds only the Revive buttons and Select Patron |
| **Free Company Camp** [SLICE+] | Sootcoat Smoker **S**, Sootcoat Collier **C**, Fieldkeeper **F**, Withy Brute **B** *(later)*, Select Patron **Tab** | Stock badge and restock sweep per button, as at the Weighstall |
| **Contraption Barn** *(later)* | Sawcart **S**, Lift Balloon **L**, Ram-Barrow **R**, Hedge-Cutters **H**, Select Patron **Tab** | Hedge-Cutters then asks for a target line (§5.9) |

### 5.2 Gold Seam (gold mine) [SLICE]

| Rule | Value |
|---|---|
| Data id | `gold_mine` (kept for the code in `architecture.md`); display name **Gold Seam** |
| Gold | **12,000** (main), **8,000** (expansion). Low-gold warning at **1,500**: minimap ping plus the faction advisor line |
| Mining | 10 gold per trip; one worker inside at a time for **1.0 s**; about 5 workers saturate it at the **6.0 m** hall gap (rules §3.3) |
| Footprint | 8×8 cells (4×4 m), blocks pathing |
| Look | The differentiator is the **cliff seam**: the mine is an **adit** (a low, square timber-framed tunnel mouth) cut into the face of a short, **layered cliff** with a thin bright quartz-and-gold line running through the strata, never a free-standing rock mound with gold nuggets heaped at the door. On the cliff lip above stands a **windlass headframe** (two timber A-frames and a crank drum lowering a bucket). Beside the adit: a **spoil heap** of grey tailings and a **wooden sluice** trough carrying a trickle of water down from the cliff. Two lanterns on hooks are lit at night. No mine cart, no rails. A worker vanishes into the dark mouth for its 1 s |
| Empty | Collapses when empty (the familiar rule): the headframe tips, the adit mouth falls in with a puff of dust, the sluice runs dry, and the footprint becomes walkable rubble (a ground decal with small non-blocking rocks) |
| Minimap | Our faceted-nugget glyph in pale gold (§1.2) |
| Faction hooks | Later factions (`sylvan`, `deathless`) may change how they claim a seam; that is their business, not this doc's |
| Production | bpy kitbash (layered cliff-seam mesh, timber adit frame, windlass headframe, spoil heap, sluice, lanterns) with AI-painted textures. Squint test against the WC3 mine in §10.2 |

### 5.3 Weighstall (merchant) and the Rundlings [SLICE]

**The building.**
- A timber market stall under a **cream-and-sage striped awning**, piled with crates, sacks and jars.
- It is crowned by a **giant brass balance**: a beam about 7 m tall with two great pans. The beam is the silhouette read from across the map.
- The pans tip slowly in the wind and swing hard when someone buys.
- Stock: §4.2. It **buys** any carried item for 50 % of value.

**The Rundlings**, the traders' people:
- **Look:**
  - Knee-high (1.0–1.1 m), **pangolin-like** folk with overlapping umber scales.
  - Long snouts wearing brass spectacles.
  - A heavy tail they sit on like a stool. Abacus beads, tally sticks and a pencil behind one ear.
  - When frightened they **curl into a scaled ball**.
- **Culture:**
  - A wandering guild of **honest weighers**. They push handcarts between market towns and trade with Brennmark, the Tormai and anyone else.
  - Their joke is *fussy fairness*: re-weighing, double-counting, polite outrage at a light coin. Paper slips tucked into every
    bag are a **visual prop only**; receipts never appear in the voice script (*Why:* a shop-receipt gag is a known WC3 merchant line).
  - **Never** the greedy-merchant caricature: no hoarded gold piles, no hooked noses, no swindling, no explosives gags, no green skin, no big ears.
- **Palette:** scales #7A5A3A with #B08A5A edges, brass #B8913A, awning cream #E8DCC0 and sage #7E9A6E.
- **In the slice** the shopkeeper is a **curled-up Rundling ball** dozing on the counter. It is a bpy prop that "breathes" with a scale bob and uncurls a nose when you buy.
  A full Rundling shopkeeper model is [SLICE+] (one AI mesh). It is reused only for the Weighstall, the Lucky Barrow pedlar and the
  Weighmaster hero (§5.6). The Rundlings are merchants and nothing else; the Contraption Barn has its own staff (§5.9).
- **Guards:** the Smugglers' Den stands at the stall's four corners (§3.3), so every buying spot is covered by day.

**Shopkeeper lines** (original; one voice, Krea TTS):

| Category | Lines |
|---|---|
| Select | "Fair weight, fair price." · "Everything weighed twice. Once for you, once for me." · "Wipe your boots, please. The scales notice." |
| Buy | "Weighed and wrapped!" · "Counted, tied, and yours." |
| Sell | "Hm. Light. Half it is." |
| Can't afford | "The scales say no." |
| Annoyed (4 clicks in 3 s) | "Tap the counter once more and I'm adding a tapping fee." · "I'm curling up. I am curling up!" |

### 5.4 Lucky Barrow (rotating stock) *(later)*

- **Look:** a Rundling pedlar's handcart with a tall stack of drawers and a wind-up chime that plays when the stock changes.
- **Stock:** every **120 s** it rerolls 4 slots: 1 L3 permanent, 1 L3–L4 charged, 1 L4 permanent, and 1 L5 permanent from 10:00.
  Price is value × 1.25, with 1 of each in stock. A visible countdown sits over the cart.
- **Fixed slots:** the Pocket Signpost and the Oilcloth Capes (§4.2), which do not fit on the Weighstall's 12-slot card.
- It buys items at 50 % like the Weighstall.

### 5.5 Coaching Inn (instant revive and neutral heroes) [SLICE: revive only; hiring SLICE+]

- **Building type and name:** the building type is the generic **Coaching Inn** (`neutral_coaching_inn`). Each map gives its inn a
  proper name on the sign; Greenvale's is ***The Muddy Lantern***. The tooltip reads "*The Muddy Lantern* (coaching inn)".
- **Look:**
  - A two-storey **coaching inn**: a stable arch, a horse trough, smoke from two chimneys.
  - A great **hanging lantern sign** with the map's inn name.
  - It is never guarded, so it is a calm place in a hostile map.
- **In the slice** (P1, at (106, 106) per slice-plan §1.4): the inn offers **instant revive only**. Hiring the Rat-Piper is [SLICE+].
  Production: the bpy half-timber kit retinted to neutral browns (≈ 0.5–1 cr, §8.1).
- **Instant revive** (any of your dead heroes, faction or neutral): cost and result are **rules §6.7** (`rules.heroes.inn_revive`):
  gold 425 × (0.8 + 0.2 × (L − 1)) up to **1,105**, lumber 100 × (0.8 + 0.2 × (L − 1)) up to **260**, i.e. **340 g / 80 l at level 1 …
  1,105 g / 260 l at level 10**. It needs **5 free food** (rules §4.4). The hero returns **at once**, at the inn door, with **50 % HP and 0 mana**.
  Compare the altar: at most 550 gold and up to 110 s, at full HP.
- **Hire** a neutral hero (§5.6) [SLICE+]:
  - **425 gold / 135 lumber**, 5 food (rules §6.1). *Why:* the lumber premium over a faction hero (100) echoes WC3 on purpose.
  - It needs a free hero slot (T1: 1, T2: 2, T3: 3). **The free first-hero token works here**, and an inn-hired first hero also receives
    the hiring faction's **recall item** (rules §3.2), exactly as an altar-trained first hero does.
  - The hire is instant. The hero appears at the inn door with 1 skill point.
  - **Each neutral hero can be hired once per match, by one player.** It goes grey for everyone else.
- Neutral heroes can also be revived at your own altar with the normal formula.
- **Sound:** a murmur of a crowded room, a fiddle through the wall, a door bell for a hire. No voice for the inn itself.

### 5.6 Neutral heroes

#### 5.6.1 Common rules

- Global hero rules apply: Heroic attack, Hero armour, 30 % spell resistance, 6 item slots, XP table and creep factor,
  abilities at levels 1/3/5 (3 ranks) and an ultimate at 6.
- Attribute formulas: HP = 100 + 25 × STR; mana = 15 × INT; armour = base + 0.3 × AGI; attack cooldown = base ÷ (1 + 0.02 × AGI);
  primary attribute +1 damage. Attributes are floored for the derived values.
- Sight 28.1 / 12.5 m. A random proper name from the hero's list is shown as "Title: Name".

#### 5.6.2 Stats

| Hero | id | Primary | STR (+/lvl) | AGI (+/lvl) | INT (+/lvl) | Base damage (+primary) | Base armour | Base CD | Range | Speed | Height | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Rat-Piper** | `nhero_rat_piper` | AGI | 17 (+1.8) | 21 (+2.3) | 16 (+1.6) | 2–10 | −2 | 2.1 | 7.0 m (crossbow) | 4.8 | 2.1 m (hat) | [SLICE+] |
| **Old Menhir** | `nhero_old_menhir` | STR | 25 (+2.8) | 10 (+1.0) | 14 (+1.4) | 6–14 | 1 | 2.5 | 1.2 m melee | 4.2 | 3.0 m | *later* |
| **Weighmaster** | `nhero_weighmaster` | INT | 17 (+1.9) | 13 (+1.1) | 21 (+2.8) | 4–10 | −1 | 2.2 | 6.5 m (flung weight) | 4.5 | 1.1 m body, 2.2 m with the balance staff | *later* |

Derived values (HP / mana / armour / damage / cooldown):

| Hero | Level 1 | Level 5 | Level 10 |
|---|---|---|---|
| Rat-Piper | 525 / 240 / 4.3 / 23–31 / 1.48 s | 700 / 330 / 7.0 / 32–40 / 1.31 s | 925 / 450 / 10.3 / 43–51 / 1.15 s |
| Old Menhir | 725 / 210 / 4.0 / 31–39 / 2.08 s | 1000 / 285 / 5.2 / 42–50 / 1.95 s | 1350 / 390 / 6.7 / 56–64 / 1.81 s |
| Weighmaster | 525 / 315 / 2.9 / 25–31 / 1.75 s | 700 / 480 / 4.1 / 36–42 / 1.64 s | 950 / 690 / 5.6 / 50–56 / 1.53 s |

#### 5.6.3 Rat-Piper (AGI ranged trapper and summoner) [SLICE+]

- **Look:**
  - A lanky man in a mustard-and-rust **coat of a hundred pockets**, with rats peering out of half of them.
  - A tall **crooked stovepipe hat**, a long-stocked crossbow, and a tin whistle on a cord.
  - A wicker rat-cage lantern on his back.
  - Silhouette: stovepipe hat plus crossbow plus backpack cage.
- **Origin:** a Greenvale cellar-clearer for hire, who discovered that rats prefer him to the people who pay him.
- **Never:** pied motley costume, a hood-and-bow ranger look, dark undead archery.
- **Proper names:** Pell Whistlewick · Odo Ferrick · Tam Gullow · Jory Thimblebrook.
- **Voice:** cheery and conspiratorial; talks to his rats more than to you.
  - Select: "Mind the coat. It bites."
  - Move: "Down the drain and round the bend."
  - Attack: "Teeth first!"
  - Annoyed: "There's a rat in my left boot. Been there for years. Calls himself Gerald."

| Key | Ability | Rank 1 / 2 / 3 | Mana | Cooldown | Effect |
|---|---|---|---|---|---|
| Q | **Sack of Rats** (point, 9 m) | 3 / 4 / 5 rats | 90 | 16 s | Throws a squirming sack; rats burst out where it lands and fight for **20 s**. Rat stats in §5.6.4. Each bite **gnaws −1 armour** (5 s, stacks to −3 per target) |
| W | **Deadfall Snare** (point, 5 m) | Up to 2 / 3 / 4 snares | 40 | 8 s | Sets a snare that turns invisible after 2 s and lasts 180 s. The first enemy ground unit within 0.8 m is **rooted 2 / 2.5 / 3 s** (heroes 1 / 1.25 / 1.5 s), takes **40 / 75 / 110** Spell damage and is revealed while rooted. True sight shows snares |
| E | **Ratter's Instinct** (passive) | +6 / +11 / +16 | — | — | Attacks deal the bonus damage to targets **below 50 % HP**. Each kill by him or his rats restores 15 / 20 / 25 mana |
| R | **The Long Tune** (ultimate, channel up to 4 s, radius 6 m) | — | 175 | 180 s | He plays. Up to **8** enemy **non-hero** units in the radius at the start, **highest level first, at most 16 levels in total**, are **enthralled** for **4 s** (**2 s** on units of level 5+ and on Hardy creeps; Hardy's own halving does not apply on top): they follow him (at most 3.0 m/s) and cannot attack or cast. An enthralled unit **breaks free** once it has taken damage of at least **20 % of its max HP**. Enemy heroes in the radius are slowed 40 % instead. He can walk at 2.4 m/s while playing. Stuns, silences or his death end it |

#### 5.6.4 Summons

| Summon | From | Level | HP | Armour | Attack | Damage | CD | Range | Speed | Duration | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rat (`nhero_summon_rat`) | Sack of Rats | 1 | 110 | 0 Light | Blade | 5–6 | 1.2 | melee 0.4 | 5.0 | 20 s | Gnaw: −1 armour per bite (stacks to −3, 5 s). Procedural scurry; no rig |
| Rundling Pikeguard (`nhero_summon_pikeguard`) | Hired Pikes | 2 / 3 / 3 | 380 / 420 / 520 | 2 / 3 / 3 Heavy | Blade | 12–15 / 14–17 / 17–21 | 1.5 | melee 1.2 (pike) | 4.0 | 40 s | **Curl Up** (once): below 30 % HP it curls for 3 s, unable to act, taking −70 % damage |

#### 5.6.5 Old Menhir (STR stone tank and terrain shaper) *(later)*

- **Look:**
  - A **standing stone that woke up and walked off**: a tall, lichen-crusted menhir for a torso, with cup-and-ring carvings that glow at night.
  - Drystone-slab arms and legs; moss and a bird's nest on one shoulder.
  - He is the Cairnwakes' eldest (§2.1 G3); the same procedural slab kit at hero scale.
- **Never:** a rounded rock-man body, a crystal core, a tree-like or root-like body.
- **Proper names:** Mossmantle · Greyhallow · Ninefold · Longstanding.
- **Voice:** geological patience. Very slow, low, amused.
  - Select: "...Mm. I was standing here before the road was."
  - Move: "Moving. Quickly, for a stone."
  - Attack: "Fall down."
  - Annoyed: "I have outlasted a glacier and several kings. I will outlast your clicking."

| Key | Ability | Rank 1 / 2 / 3 | Mana | Cooldown | Effect |
|---|---|---|---|---|---|
| Q | **Barge** (unit target, 2 m) | 60 / 110 / 160 dmg | 75 | 10 s | Shoulder-charges the target, dealing Spell damage and **knocking it back 4 m**. If it hits a cliff, tree, building or another unit, it is **stunned 1.5 / 2 / 2.5 s** (heroes half), and a unit it hits takes 50 % |
| W | **Drystone Wall** (point, 10 m) | 6 / 8 / 10 m long | 90 | 20 / 17 / 14 s | Raises a 1 m-thick drystone wall across the cast direction for **6 s**. It blocks all ground pathing; units under it are pushed to the nearer side |
| E | **Lichen Hide** (passive) | −25 / −40 / −55 on the first hit; +1 / +2 / +3 HP/s | — | — | The lichen takes the first blow: the **first attack** against him in any **3 s window** is reduced by a flat amount (minimum 1; spells unaffected). Later attacks in that window hit normally. Also adds HP regeneration |
| R | **Sleep of Stones** (ultimate, self, 7 m) | — | 150 | 140 s | He and every allied non-structure unit within 7 m turn to stone for **4 s**: invulnerable, unable to act or be moved. When it ends he releases a ring shockwave: **150 Spell damage** to enemies within 7 m, which are **pushed 1 m outward**. Allies cannot opt out (the skill is in the timing) |

#### 5.6.6 Weighmaster (INT Rundling support who pays for help) *(later)*

- **Look:**
  - A small, stout Rundling official in a brass-buttoned coat and a tall felt hat with a chain of office.
  - She carries a **2.2 m balance-staff** with two hanging brass pans; the staff makes the hero silhouette.
  - She flings small brass weights as her attack.
- **Proper names:** Tilda Truebalance · Ottoline Brassweigh · Bram Fairpan · Wendel Notchstick.
- **Voice:** a fussy, scrupulously fair official.
  - Select: "Weighed, measured, noted."
  - Move: "Proceeding. Within regulations."
  - Attack: "Your account is overdue."
  - Annoyed: "That is the eleventh click. I have written them all down."

| Key | Ability | Rank 1 / 2 / 3 | Mana | Cooldown | Effect |
|---|---|---|---|---|---|
| Q | **Even the Ledger** (enemy unit, 8 m) | 70 / 115 / 160 | 85 | 8 s | Deals Spell damage to the enemy, then **heals the most-injured allied non-structure unit within 8 m of her** by the damage actually dealt |
| W | **Hired Pikes** (summon) | 1 / 2 / 2 Pikeguards | 80 mana **+ 25 gold** | 25 s | Summons Rundling Pikeguards for **40 s** (stats in §5.6.4). The **gold cost** is the gimmick: can't afford it, can't cast it |
| E | **Strongbox Shell** (ally unit, 8 m) | 120 / 200 / 280 | 70 | 10 s | Wraps the ally in a brass-banded shell that **absorbs damage for 12 s**. When the shell breaks it bursts, knocking adjacent enemies back 1.5 m |
| R | **The Great Scales** (ultimate, point within 10 m, radius 8 m) | — | 175 | 150 s | A translucent bronze balance hangs over the area for **8 s**. Enemy units inside deal **−35 % damage** and your units inside regenerate 8 HP/s. When it ends, each enemy unit takes Spell damage equal to **50 % of the damage it dealt** during the 8 s (at most 300 per unit) |

#### 5.6.7 Kit fidelity audit (policy: at most 2 of 4 abilities may be functional equivalents of the nearest WC3 hero)

| Neutral hero | Nearest WC3 hero(es) compared (reference) | Functional equivalents (counted strictly) | Original mechanics | Count |
|---|---|---|---|---|
| Rat-Piper | Dark Ranger (AGI ranged tavern hero) | Sack of Rats (summoned minions); The Long Tune (taking control of enemy units: temporary, capped and breakable, instead of permanent and single; counted as a Charm equivalent) | Deadfall Snare (invisible root traps); Ratter's Instinct (execute bonus plus mana on kill) | **2** |
| Old Menhir | Pandaren Brewmaster (STR tank tavern hero); **Mountain King** (STR stone-and-hammer melee hero); **Mountain Giant** (stone tank unit) | Brewmaster: Lichen Hide (a defensive passive), 1. Mountain King: Barge (single-target damage plus stun, though the stun needs a collision), 1; the Sleep of Stones ring no longer slows (it pushes 1 m), so it is not a Thunder Clap read. Mountain Giant: none (Lichen Hide is a first-hit-per-window rule, not a flat block on every attack) | Drystone Wall (pathing wall); Sleep of Stones (group stasis plus shockwave push); Lichen Hide's first-blow rule | **1** against each |
| Weighmaster | Goblin Alchemist (comedic merchant-people hero) | Even the Ledger (has a healing component) | Hired Pikes (summon paid in gold); Strongbox Shell (absorb shield); The Great Scales (damage reduction plus delayed rebound) | **1** |

No ultimate reproduces its WC3 counterpart's exact mechanic; The Long Tune (temporary mass control) is counted as a Charm equivalent in the
Rat-Piper's two. Names, VFX, numbers and designs are ours.

### 5.7 Free Company Camp (mercenaries) [SLICE+]

- **Look:** a ring of lean-to shelters around a big cooking fire, weapon racks, and a **hiring board** of hanging tally sticks.
  Each hire cuts a notch; a fresh stick is hung on restock.
- **Rules:**
  - Hires are **instant**; the unit appears beside the camp.
  - Mercenaries use food and count for upkeep. They never receive faction research.
  - Their level is their XP value.
  - **Stock is per player.**
  - Each tileset has its own roster.

| Tileset | Unit (creep stats from §2) | Lvl | Gold | Lumber | Food | Stock | Restock | From | Slice |
|---|---|---|---|---|---|---|---|---|---|
| Greenvale | Sootcoat Smoker | 2 | 150 | 15 | 2 | 2 | 60 s | 2:00 | [SLICE+] |
| Greenvale | Sootcoat Collier | 3 | 200 | 20 | 3 | 2 | 60 s | 2:00 | [SLICE+] |
| Greenvale | Fieldkeeper ("a hired scarecrow"; it never sleeps while hired) | 3 | 190 | 30 | 3 | 2 | 75 s | 4:00 | [SLICE+] |
| Greenvale | Withy Brute | 5 | 320 | 60 | 4 | 1 | 120 s | 8:00 | *later* |
| Rimeholt | Snowslinger | 2 | 150 | 15 | 2 | 2 | 60 s | 2:00 | *later* |
| Rimeholt | Rime-Biter | 4 | 260 | 40 | 3 | 2 | 90 s | 5:00 | *later* |
| Rimeholt | Longfringe Bull | 4 | 250 | 50 | 3 | 1 | 90 s | 5:00 | *later* |
| Rimeholt | Ermine Matriarch | 6 | 360 | 80 | 4 | 1 | 120 s | 10:00 | *later* |
| Sunscar | Etch-Spitter | 2 | 150 | 15 | 2 | 2 | 60 s | 2:00 | *later* |
| Sunscar | Mandible Guard | 3 | 200 | 20 | 3 | 2 | 60 s | 2:00 | *later* |
| Sunscar | Boulder Roller | 4 | 260 | 50 | 3 | 1 | 90 s | 5:00 | *later* |
| Sunscar | Claywright Drummer | 5 | 300 | 60 | 3 | 1 | 120 s | 8:00 | *later* |

Pricing rule of thumb: 50–60 gold per level + 40, lumber about 10 per level (more for beasts), food by size. That is about the price of a
faction unit of the same level. The player pays instead in flexibility lost: no faction research, a small stock, and a trip to the camp.

### 5.8 Hale Spring and Dewstone (fountains)

| | Hale Spring [SLICE] | Dewstone [SLICE+] |
|---|---|---|
| Effect | **+2 % of max HP per second** | **+1.5 % of max mana per second, +0.5 mana/s** |
| Radius | 7.8 m from the centre | 7.8 m |
| Who | Every non-structure unit in range, **any owner, creeps included**, except mechanical units (wagons, carts, balloons) | Every unit with mana in range, any owner |
| Look | A moss-ringed spring pool fed by a hollow-log flume with a tiny turning waterwheel. Warm sparkles rise off the water by day. No carved stone rim and no glowing water | A tall (about 3 m) **upright quartz-veined boulder** that **sweats warm white-gold droplets at dusk**, with moths circling it after dark. **No water body:** no pool, basin, trough, water-lilies or stone ring, and **no blue or teal glow** anywhere |
| Unit VFX | A soft rising-bubble shimmer on units regenerating | **Warm white motes** drift up from units regenerating mana (never a blue shine) |
| Guard | Crow Field (amber 12, the map's one day camp): free by day, contested at night | An amber 10–14 camp, usually never-sleep |
| Footprint | 6×6 cells; the pool itself is walkable shallow water | 4×4 cells (the boulder blocks pathing) |

A landmark's aura never wakes creeps (passive). *Why the Dewstone:* a stone-rimmed pool of glowing blue water that restores mana is the
WC3 night-elf moon well and the mana fountain together (ip-safety §2.3; `sylvan-and-deathless.md` avoids it too), so the neutral mana
landmark is a dry stone instead (§10.2).

### 5.9 Contraption Barn (lab-equivalent) *(later)*

- **Staff:** the **hill-country millwrights**, a human mill-guild that builds and mends the mills of the downs. Leather aprons, flat felt
  caps, measuring rods and wooden mallets; flour-dusted, oak-brown and verdigris-copper palette. They are not Rundlings: the Rundling model
  is used only for the merchants and the Weighmaster (§5.3). The millwrights reuse the shared human biped mesh with prop swaps.
- **Look:** a big timber **mill-barn** on a millrace, with an undershot waterwheel and a windsock on the ridge; its roof slides open.
  Inside: wooden gearwork, a hot-air balloon tethered to the roof beam, a saw-cart, stacked mill timbers.
- **Rules:** hires and services, gold and lumber, **stock per player**.

| Offer | Kind | Cost | Food | Stock / restock | From | Stats and effect |
|---|---|---|---|---|---|---|
| **Sawcart** | Unit (wheeled) | 275 g / 40 l | 3 | 2 / 120 s | 5:00 | HP 450, 2 Heavy, 3.4 m/s. Fells trees fast: **5 lumber/s**, carries **100** per trip, returns to any of your drop-offs. No attack. Pushed by a millwright |
| **Lift Balloon** | Unit (flying transport) | 200 g / 40 l | 2 | 1 / 120 s | 6:00 | HP 500, 0 Light, 5.0 m/s, sight 16 / 12 m. Carries **6 food** of ground units; unloading takes 0.5 s per unit. No attack. **Drifts downwind:** +20 % move speed while it moves within 45° of the map's wind direction (a per-map vector, shown by the barn's windsock) |
| **Ram-Barrow** | Unit (wheeled siege) | 190 g / 70 l | 2 | 2 / 90 s | 6:00 | HP 380, 3 Heavy, 3.6 m/s. **Siege 70–90 vs buildings only**, CD 3.0, melee. Battering Run: the first hit after 2 s of moving deals ×2. It survives its hits (not a suicide unit) |
| **Hedge-Cutters** | Service | 90 g | — | per-player cooldown 120 s | 6:00 | Target a line of up to 6 m on a tree belt where you have vision: three millwrights step out of the trees at its end and fell **every tree in a 6 m × 2 m strip over 10 s**, opening a new path. They are neutral, untargetable by AI creeps, and can be attacked by enemies (150 HP each, 0 Light); killing them stops the felling. The lumber goes to nobody |

*Why:* the lab's offers used to map one to one onto the WC3 goblin lab (lumber machine, 8-unit airship at 240 / 60, sapper slot, paid
reveal), staffed by the same merchant people as the shop and a tavern hero. The staff, the balloon's numbers and movement, and the fourth
offer are now our own (§0.2).

### 5.10 Twin Milestones (paired teleport) *(later)*

- **Look:** two worn roadside **milestones**, each carved with a road that runs off its own edge, placed far apart on the map.
- **Use:** right-click a milestone with any ground units. Each unit walks within 1 m, folds into a swirl of **road dust** for 1.0 s
  (interrupted by damage) and unfolds beside the twin. **Per-unit cooldown 5 s.** Heroes and armies both use it; creeps never do.
- **Readability:** both stones show the same coloured road-ribbon, and the minimap draws a faint dotted link between them.

### 5.11 Beacon Cairn (capturable vision cairn) [SLICE+]

- **Look:** a **low, broad drystone cairn** (about 2.5 m, wider than it is tall) on a knoll, topped by an iron fire-basket on a short
  iron post. It burns in the capturing player's team colour. Never a tall obelisk, a crystal, carved runes or glowing alien stone (§10.2).
- **Capture:** a ground unit of yours stands within **2.5 m** for **3 s** with no enemy unit within 2.5 m.
- **While lit:**
  - Its owner gets vision of **20 m (day) / 16 m (night)** around it. That vision ignores tree occlusion but not higher cliffs.
  - The flame's team colour is visible to **everyone** on the minimap, so a capture is never secret.
- **Fuel:** it stays lit for **60 s** after your last unit leaves, then gutters out (neutral).
  An enemy **douses** it with the same 3 s uncontested stand, which resets it to neutral (a second 3 s captures it).
- **Why:** a "high ground watch" landmark. It rewards map presence and gives the slice AI an easy objective. WC3's melee neutral
  buildings include no capturable vision tower, but **capture-by-standing vision towers exist in StarCraft II (the Xel'Naga Tower)**.
  The mechanic is generic; ours differs in presentation: a drystone cairn with an iron fire-basket, a 60 s fuel timer and a douse rule.
- **Production:** bpy cairn kit + fire VFX; no 3D credits.

---

## 6. Critters

**Rules (all critters):**
- Owner `NEUTRAL_PASSIVE`, level 0. They give **no XP and no bounty**, never block pathing (radius 0.15 m) and are never auto-acquired.
- **Visual-only in the slice.** Critters run in a client-side visual system with their own visual RNG, outside the deterministic sim:
  players can select them (info panel and click gags) but cannot attack them, and they leave no corpse. *Later:* if killable critters or
  critter corpses are wanted (for example by `deathless`), they move into the sim with seeded wander.
- The one exception is the **Sparrow Roost flush** (§6 table), which reveals position: it is a deterministic sim trigger (a ground unit
  within 4 m), with only the flock's flight drawn by the visual system.
- They flee from combat within 6 m and from any unit that comes within their **startle radius**. They do not respawn.
- **Density:** hand-placed on the slice map (10–14; slice-plan §1.9). Generated maps: about **0.4 per 16 × 16-tile chunk of open ground,
  at most 14 per map**; none within 15 m of a start location.
- **Click-spam gag:** after **6 clicks within 3 s**, each critter does its own gag, then cools down for 20 s.
  **Nothing explodes or dies.** *Why:* an exploding farm animal is a famous Blizzard easter egg, so we never use it.

| id | Name | Tileset | HP | Speed (wander / flee) | Active | Startle radius | Behaviour | Click-spam gag | Slice |
|---|---|---|---|---|---|---|---|---|---|
| `critter_brown_hare` | Brown Hare | Greenvale | 20 | 2.0 / 7.0 | Day (crouches still at night) | 4 m | Grazes in meadows; bolts 8 m when startled | Thumps a hind foot twice, bolts 10 m and freezes flat with ears down | **[SLICE]** |
| `critter_grey_goose` | Grey Goose | Greenvale | 30 | 2.4 / 3.5 | Day | 2 m (it hisses instead of fleeing) | Gaggles of 2–4 on roads and ponds | Honks, flaps, and **nips** the clicking player's nearest unit every 1.5 s for 6 s, then struts off. The nip is `"cosmetic": true`: a peck animation, a honk and a white hit flash on the unit, with **no HP change and no damage event** (so it never stops a drink-over-time, breaks a channel, reveals an attacker or resets a give-up timer) | **[SLICE]** |
| `critter_fireflies` | Firefly Drift | Greenvale | — (untargetable) | drifts | Night | — | Soft lights over water and meadow edges; part of the night ambience | — | **[SLICE]** (VFX only) |
| `critter_sparrow_roost` | Sparrow Roost | Greenvale | — (untargetable) | — | Day | 4 m | A roost sits in a tree line. **Flush** (a deterministic sim trigger): when any player's ground unit comes within 4 m, the flock bursts up for 2.5 s with a wing-flutter sound. The flock is drawn **above the fog in explored areas** (never in black mask), so all players see something moving there. It resettles after 30 s | — | [SLICE+] |
| `critter_hedgehog` | Hedgehog | Greenvale | 15 | 1.4 / 1.4 | Night | 2 m (it curls instead of fleeing) | Snuffles along hedges | Curls into a ball, rolls 2 m and sneezes | *later* |
| `critter_snow_hare` | Snow Hare | Rimeholt | 20 | 2.0 / 7.0 | Day | 4 m | As the Brown Hare, in white | As the Brown Hare | *later* |
| `critter_ptarmigan` | Ptarmigan | Rimeholt | 20 | 2.0 / 4.0 | Day | 3 m | Small flocks in snowfields | Dives head-first into the snow; only its tail sticks out for 4 s | *later* |
| `critter_lemming` | Lemming | Rimeholt | 10 | 3.0 / 3.0 | Day | 3 m | Scurries between rocks | Puffs its cheeks and squeaks furiously at the camera | *later* |
| `critter_meerkat` | Meerkat | Sunscar | 15 | 3.0 / 5.0 | Day | 5 m | Families of 3; one always stands upright on watch | All three pop upright at once and **stare straight at the camera** for 3 s | *later* |
| `critter_guinea_fowl` | Guinea Fowl | Sunscar | 20 | 3.0 / 4.5 | Day | 3 m | Flocks in dry grass | Runs in tight shrieking circles | *later* |

**Production:** bpy low-poly primitives with AI-painted textures. Procedural hop (hare), waddle (goose), scurry (lemming, rats) and
flock boids (sparrows). No rigging and no 3D credits.

---

## 7. Vertical slice subset

| Category | In the slice | [SLICE+] | Later |
|---|---|---|---|
| Creep types | **10:** Sootcoat Cutpurse, Smoker, Collier, Kiln-Master; Strawling, Fieldkeeper, Crowcaller (+ Crow summon); Cairnling, Drystone Walker, Menhir Elder | Withy Brute | Clamp-Father, Old Mangold, Dolmen Colossus, all Mire Toads, all Rimeholt and Sunscar families |
| Camps | **11:** Charcoal Clamp ×2, Turnip Patch ×2, Collier's Hut ×2 (green); Smugglers' Den, Crow Field, Drystone Fold ×2 (amber); Standing Ring (red) | Withy Field replaces Crow Field | All other templates; one more amber camp per side for the second hero (§3.6) |
| Sleep schedules | All three (`night` ×7 camps, `never` ×3, `day` ×1) and `sleeps_override` | — | — |
| Items | **31:** 9 purchasable, 7 power-ups, 13 permanent (L2–L4), 2 charged (L2) | Curl-Up Scale | 20 more, including all artifacts |
| Neutral buildings | **Gold Seam ×4, Weighstall** (curled shopkeeper prop), **Hale Spring**, **Coaching Inn** (*The Muddy Lantern*; instant revive only, P1) | Hiring the Rat-Piper, Free Company Camp (Greenvale roster), Dewstone, Beacon Cairn ×2, Rundling shopkeeper model | Lucky Barrow, Contraption Barn, Twin Milestones, Old Menhir, Weighmaster |
| Critters | Brown Hare, Grey Goose, Firefly Drift (all visual-only) | Sparrow Roost (flush trigger in the sim) | Hedgehog, all Rimeholt and Sunscar critters |
| Systems | Camp/guard modes, `acquire_override`, `layout`, leash and return, unreachable-attacker return, sleep and wake with the map rules, XP factor (lost with no hero near), bounty with upkeep tax, seeded drops with tie-break, shop stock and restock, buying needs a hero, cooldown groups, selling, inn revive, neutral command cards, minimap neutral markers, **14 item effect scripts** | Hero hire, mercenary stock, beacon capture, `self_invulnerable` | Rotating stock, transport, teleport pairs, tree-clearing service |

---

## 8. Production plan

### 8.1 Slice assets and cost estimate

Higgsfield balance at the last ledger check: **228.5 credits** (`docs/asset-ledger.md`, 2026-10-16 14:45). The kingdom doc estimates
70–95 credits for its faction, and the clans need a similar amount. So the neutral layer is designed to cost **about 26–35 credits**,
and none of it needs paid rigging.

| Asset | Method | Higgsfield cr | Krea CU |
|---|---|---|---|
| Sootcoat base (Cutpurse, Smoker, Collier by prop swap and tint) | Concept (0.25) → Tripo H3.1 image-to-3D (9) → bpy auto-rig on the shared humanoid skeleton; shared biped clips | 9.25 | — |
| Kiln-Master | The Sootcoat mesh at 1.12× scale, plus a bpy apron, tall hood and bellows prop | 0.25 (texture) | — |
| Fieldkeeper / Crowcaller | Concept → H3.1 (9). Crowcaller = the same mesh + bpy cloak cards, crow props and staff. The rig uses a **stiff-knee clip variant**. *Saving:* build it procedurally in bpy (poles, sack head, cloth coat) for about 0.5 | 9.25 (or 0.5) | — |
| Strawling, Crow summon | bpy procedural (straw bundle; low-poly bird with flap) | 0.5 | — |
| Cairnling, Drystone Walker, Menhir Elder | bpy procedural slab stacks, rigid-bone animation, 2 stone textures | 0.5 | — |
| Weighstall + curled shopkeeper | bpy kit: stall, awning, crates, 7 m brass balance; 3 textures | 0.75 | — |
| Gold Seam (cliff seam, adit, windlass headframe, spoil heap, sluice), Hale Spring, loot bundle, power-up props (nail, ball, knot, almanac, tally-stick, berries, purse) | bpy kitbash; 4 textures | 1.0 | — |
| Coaching Inn (*The Muddy Lantern*), revive only | bpy half-timber kit reused from the kingdom kit, retinted to neutral browns; lantern sign | 0.5–1 | — |
| Collier's Hut cottage | The same half-timber kit, sooted; a small clamp from the Charcoal Clamp props | 0.25 | — |
| Critters (hare, goose), fireflies | bpy primitives, procedural motion, 2 textures | 0.5 | — |
| Icons: 31 items + 16 creep abilities (adds Pine-Tar Dressing and Re-Stuff) | Higgsfield images (0.25 cr each), our own style anchors | ≈ 12 | — |
| Minimap glyphs (camp pip, nugget, balance, droplet ring, lantern) | Drawn in-house as SVG | 0 | — |
| Creep vocal sets: 3 families × (aggro, attack, pain, death), 2–3 variants per job (audio §1.6, prompt C1 pattern) | Krea Seed Audio, about 4.63 CU per job | — | 12 jobs ≈ 56 |
| World SFX: buy, sell, can't-afford, item pickup, bundle glint, spring loop, inn revive bell, critter set (incl. the goose honk), crow caws, stone grind | Seed Audio | — | 12 jobs ≈ 56 |
| Shopkeeper VO (9 lines) | Krea ElevenLabs TTS (cost per line still to be probed; audio §4.1) | — | probe |
| **Total (slice)** | | **≈ 35 cr** (≈ 26 with the procedural scarecrow) | **≈ 112 CU + TTS** |

**[SLICE+] add-ons:** Withy Brute (bpy bound-rod bundles, ~0.5 cr) · Rat-Piper (H3.1 + bpy auto-rig, 9.25 cr; rats procedural; about 26 VO lines) ·
Rundling shopkeeper (H3.1, 9.25 cr; reused for the Weighmaster later) · Curl-Up Scale icon (0.25 cr) · Free Company Camp, Beacon Cairn and
Dewstone (bpy, ~1.5 cr together).

### 8.2 Prompt and review rules (neutral layer)

- Describe creeps by **function and qualities**, never by analogy. Write "charcoal-burner outlaw with a wide conical leather hood, soot-black face, patched oilcloth coat",
  never "a bandit like in …" (ip-safety §5.2).
- No pumpkin heads in Tattiebogles prompts. Say "pierced turnip lantern head with randomly scattered drilled holes, no face of any kind".
  The Crowcaller is "a patched sacking cape, crows perched on outstretched pole-arms", never feathers; the Withy Brute is "tightly bound
  willow-rod bundles", never "wicker" or "woven".
- Landmarks: the Dewstone is "a dry upright quartz-veined boulder sweating warm white-gold droplets", never "pool", "well", "fountain" or
  "glowing water"; the Gold Seam is "an adit in a layered cliff with a windlass headframe", never "mine cart"; the Beacon Cairn is "a low
  drystone cairn with an iron fire-basket", never "obelisk", "tower" or "crystal".
- The Cairnwakes and Old Menhir are procedural: no prompt is needed beyond the stone texture.
- Every generated creep is squint-tested against §10.2 and logged in `docs/asset-ledger.md`, as for faction units.

---

## 9. Data sketch

The layer is data-driven like the rest of the game (`architecture.md` rule 3). Suggested shapes (field names follow the existing `units.json` defs):

```jsonc
// data/units.json (creep entry)
"creep_sootcoat_smoker": {
  "name": "Sootcoat Smoker", "kind": "unit", "flags": ["creep", "organic"],
  "level": 2, "sleeps": "night", "family": "sootcoats",
  "hp": 260, "mana": 150, "mana_regen": 0.6, "armor": 0, "armor_type": "unarmored",
  "radius": 0.4, "speed": 4.2, "height": 1.7, "leash": 18.75,
  "attack": {"type": "pierce", "damage": [10, 13], "cooldown": 2.0, "range": 6.0,
             "damage_point": 0.4, "backswing": 0.4, "acquire": 5.0,
             "projectile": {"speed": 14.0, "arc": 0.3, "model": "coal_lump"}},
  "abilities": ["creep_smoke_pot"]
}
"creep_cairn_menhir_elder": {
  "level": 7, "sleeps": "never", "family": "cairnwakes", "flags": ["creep", "construct"],
  "hp": 1350, "mana": 200, "armor": 5, "armor_type": "heavy",
  "attack": {"type": "pure", "damage": [36, 44], "cooldown": 2.2, "range": 1.2},
  "abilities": ["creep_old_ward", "creep_ley_pulse", "creep_set_in_stone"]   // "hardy" is added automatically at level 6+
}

// data/units.json (neutral hero, attack excerpt)
"nhero_rat_piper": { "attack": {"type": "heroic", "damage": [2, 10], "cooldown": 2.1, "range": 7.0}, "armor_type": "hero" }

// data/camps.json
"camp_gv_drystone_fold": {
  "tileset": "greenvale", "mode": "guard", "guard_radius": 12.0,
  "creeps": [["creep_cairn_drystone_walker", 1], ["creep_cairn_cairnling", 3]],
  "drops": {"A": {"class": ["powerup"], "level": 1},
            "B": {"class": ["permanent", "charged"], "level": 3}},
  "props": ["sheepfold_ruin", "gold_seam_expansion"]
}
"camp_gv_turnip_patch": {
  "tileset": "greenvale", "mode": "camp", "sleeps_override": "night",
  "creeps": [["creep_harvest_fieldkeeper", 2], ["creep_harvest_strawling", 2]],
  "drops": {"B": {"class": ["permanent", "charged", "powerup"], "level": 2}}
}
"camp_gv_smugglers_den": {
  "tileset": "greenvale", "mode": "camp", "acquire_override": 6.5,
  "creeps": [["creep_sootcoat_kiln_master", 1], ["creep_sootcoat_collier", 1],
             ["creep_sootcoat_smoker", 1], ["creep_sootcoat_cutpurse", 1]],
  // one [dx, dz, facing_deg] per creep, in creeps order, metres from the stall centre (stall 4 x 4 m)
  "layout": [[4.5, 4.5, 45], [-4.5, 4.5, 135], [-4.5, -4.5, 225], [4.5, -4.5, 315]],
  "drops": {"A": {"class": ["powerup"], "level": 1}, "B": {"class": ["permanent"], "level": 2}},
  "guards": "neutral_weighstall"
}

// data/items.json
"item_homing_pigeon": {
  "name": "Homing Pigeon", "class": "purchasable", "level": 1, "charges": 1,
  "price": {"gold": 325}, "value": 325, "effect": "recall_to_hall",
  "target": "point_nearest_own_hall", "double_tap": "highest_tier_hall",
  "channel": 5.0, "enemy_interruptible": false, "radius": 6.0, "max_units": 11, "cooldown": 0
}
"item_rosehip_draught": {
  "class": "purchasable", "level": 1, "charges": 1, "price": {"gold": 150}, "value": 150,
  "effect": "heal_instant", "amount": 260, "cooldown_group": "heal"
}
"item_bluebell_cordial": { "effect": "mana_instant", "amount": 160, "cooldown_group": "mana" }
"item_wanderers_hobnails": {
  "class": "purchasable", "level": 2, "price": {"gold": 200}, "value": 200,
  "effect": "stat_bonus", "move_speed": 0.7, "unique": true, "unique_group": "move_speed"
}
// also "unique": true on item_coilspring_heels (move_speed), item_thistledown_cloak (evasion),
// item_drillmasters_pace_stick and item_shepherds_crook (their own aura groups)
"item_stoutheart_weight": { "class": "purchasable", "level": 2, "price": {"gold": 300}, "effect": "stat_bonus", "max_hp": 175 }
"item_wiped_slate": { "class": "purchasable", "level": 3, "charges": 1, "price": {"gold": 280}, "effect": "retrain" }
"item_horseshoe_nail": { "class": "powerup", "level": 1, "effect": "grant_attribute", "str": 1 }

// data/neutrals.json (shop stock; the use range is global: rules.neutral.use_range = 7.0)
"neutral_weighstall": {
  "footprint": [8, 8], "buys_items": 0.5, "minimap_glyph": "balance",
  "stock": [["item_rosehip_draught", 3, 45, 0], ["item_bluebell_cordial", 3, 45, 0],
            ["item_homing_pigeon", 2, 120, 0], ["item_snoop_peg", 2, 60, 0], ["item_flour_bomb", 2, 60, 0],
            ["item_picnic_hamper", 2, 90, 180], ["item_wanderers_hobnails", 1, 120, 240],
            ["item_stoutheart_weight", 1, 120, 240], ["item_wiped_slate", 1, 300, 300]]
}
"neutral_coaching_inn": {
  "footprint": [10, 10], "sign_name": "The Muddy Lantern", "minimap_glyph": "lantern",
  "services": ["revive"], "heroes": []          // [SLICE+]: ["nhero_rat_piper"]
}

// data/factions.json, rules object (proposed additions; owned by rules.md)
"items":   { "group_cooldown": {"heal": 8.0, "mana": 8.0} },
"minimap": { "show_unexplored_neutrals": true }   // set from footage (§11)
```

- `sleeps`: `"night"` (default), `"day"` or `"never"`; a camp's `sleeps_override` wins over every member's family default.
  `level` drives XP and bounty. Level 6+ automatically gets `hardy`.
- Attack type ids are `blade, pierce, siege, arcane, heroic, spell, pure`; armour type ids add `adamant` (rules §20.4). The old ids
  `hero` (attack) and `chaos` must not appear in `data/`. Once the rules §20.4 migration has removed `chaos` from `data/factions.json` and
  `tests/unit/test_combat.gd`, add `chaos` to `tools/ip/banned_terms.txt` (adding it before then would fail the IP check on today's files).
- Stock rows are `[item, max, restock_s, available_from_s]`, kept per player.
- Drops are resolved at match start with `World.rng`, so a replay with the same seed has the same items.
- **Determinism:** sleep staggers, bounty rolls and drops use the seeded sim RNG. Critters are visual-only (§6) and use a separate
  *visual* RNG; the goose nip is cosmetic. Only the sparrow flush is a sim trigger, and it is deterministic (no RNG).

**Headless tests** (`tests/unit/`, alongside rules §22):

| Test | Asserts |
|---|---|
| `test_shop_guard_coverage` | Every walkable cell within the 7.0 m use range of the Weighstall lies within acquire range of at least one Smugglers' Den creep (with `acquire_override`), for the authored layout |
| `test_creep_unreachable_attacker` | A single ranged unit on a cliff above a camp cannot kill it: the camp drops the target after 2 s, returns after 3 s and regenerates at home; the same unit on the camp's level is fought normally |
| `test_camp_sleep_ratio` | For every map: at most one `day` camp, and at least 60 % of camps sleep at night (after `sleeps_override`) |
| `test_drop_carrier` | Drop B sits on the first highest-level creep in `creeps` order, Drop A on the first lowest-level creep; summons never carry; the item drops at the carrier's death point |
| `test_xp_route_slice` | Scripted clear of Clamp → Patch → Hut → own Fold with the hero present: level 2 after the Patch, level 3 after the Fold |
| `test_recall_point_target` | The Homing Pigeon goes to the own hall nearest the target point; an enemy stun during the 5 s channel does not cancel it; a move order does |

---

## 10. IP and distinctness checks

### 10.1 Name audit (every name in this doc was checked against ip-safety §2.1 and the collisions below)

| Considered | Collision | Final |
|---|---|---|
| "Field Warden", "Menhir Warden" | "Warden" is a WC3 hero name (ip-safety §2.1) | **Fieldkeeper**, **Menhir Elder** |
| "Ratcatcher" (hero title) | A DC Comics villain who commands rats | **Rat-Piper** |
| "Murder of Crows" | A WoW hunter talent | **Scatter-Crows** |
| "Threshing Slam" / "Toppling Shove" / "Toppling Strike" | Clash with `kingdom` Threshing Sweep and `clans` Grappler Shove | **Harrow Slam**, **Barge**, **Rockfall Blow** |
| Anything with "Hearthstone" or "Hearth" (stone creeps, inn) | Blizzard mark | Not used |
| "Waystone Inn", "Mended Drum", "Prancing Pony" | Inns from famous novels | The generic building type **Coaching Inn**, with a per-map sign name (Greenvale: *The Muddy Lantern*) |
| "Wayfarers' Inn" (first draft) | A coined game location: the inn in Britain in EA's *Ultima* V–VII and the player's tavern in *Tavern Talk* (2024); WoW has "Wayfarer's Rest" | **Coaching Inn** (`neutral_coaching_inn`) + per-map sign name |
| "Farmer's Almanac" | A real publication's trade name | **Hedge Almanac** |
| "Queen" for the termite leader | Hive-queen bug-race read (WoW desert insects) | **The Mother-Mound's Champion** |
| WC3 item names (tomes, runes, town portal, sentry ward, appearance dust, ankh, crown of kings, claws, speed boots, protection ring, strength gauntlets, death mask, orbs, escape dagger) | WC3 items (ip-safety §2.1) | Smith's Horseshoe Nail, Juggler's Ball, Riddle Knot, wild berries, Homing Pigeon, Snoop Peg, Flour Bomb, Cat's Ninth Life, Dolmen Keystone, Whetstone Fob, Wanderer's Hobnails, Tin Gorget, Plow-Horse Brass, Ravening Torc, Nettle-Sting Oil, Coilspring Heels |
| "Frostmarch" (tileset) | A coined fantasy-game title: *Talisman: The Frostmarch*, an expansion to a Games Workshop-originated board game, later sold digitally by Nomad Games | **Rimeholt** (no game or IP hit found); camp prefix `rh_` |
| "Tip the Scales" (Weighmaster Q) | An exact Blizzard ability name twice over: a WoW Evoker talent and a Hearthstone Paladin card; also a Magic: The Gathering card | **Even the Ledger** |
| "Stampede" (Herd-Bull) | WC3 Beastmaster ultimate; also a WoW Hunter talent and a Hearthstone card | **Herd Rush** (Bellowing Charge reads "As Herd Rush, 12 m") |
| "Earl of Ash" (level-7 Sootcoat leader) | A lord's title on a level-7 human-outlaw boss with a matrix-ignoring attack and a passive aura: the WC3 bandit lord's role point for point | **Clamp-Father**; the passive Cinder Cloak aura is replaced by the active **Rake the Clamp**; camp **Clamp-Father's Yard** |
| "Glimmer Font" | Its look (a stone trough of blue-glowing water ringed with lilies) combined the WC3 mana fountain with the night-elf moon well | **Dewstone**: a dry quartz boulder (§5.8) |
| "Ironwood Knuckles" | "Ironwood" is the signature word of DotA Allstars' "Ironwood Branch", from a WC3 custom map whose ownership Blizzard asserted | **Blackthorn Knuckles** |
| "Carapace" (Rollback passive) | Echoes the WC3 Crypt Lord's "Spiked Carapace" on a beetle creep | **Dung Crust** |
| "Chill Touch" (Flurry) | A well-known D&D spell name | **Frostnip** |
| "Earthbound" (Cairnwakes) | Nintendo's *EarthBound* | **Set in Stone** |
| "Hollow Harvest", "Wicker Brute", "Turnip King" | WoW's Hallow's End holiday (a Wickerman effigy, the "Wickerman Guardian"); *Worzel Gummidge*, a famous turnip-headed walking scarecrow made by "the Crowman"; Disney's "Pumpkin King" | Family **Tattiebogles** (the Scots folk word for scarecrows); **Withy Brute**; **Old Mangold** (item **Old Mangold's Sickle**; artifact **Mangold Lantern**) |
| "Moundbuilders", "Mound Mason", "Mound Drummer", "Mound-Mother's Champion" | "Mound Builders" is a real-world term for pre-Columbian Native American cultures, tied to a 19th-century racist myth | **Claywrights** (Claywright Mason, Claywright Drummer), **the Mother-Mound's Champion**; ids `creep_claywright_*`; camp names Mound Gate and Drum Mound kept |
| "Swarm Rise" (Champion) | Contradicted the family's own "no swarm, no burrowing" rule | **The Mound Opens** |
| "Shagbull", "Shag Calf" | Not IP: "shag" is vulgar British slang, an unintended joke in an English-countryside setting | **Longfringe Herd**: Longfringe Calf, Longfringe Bull; ids `creep_longfringe_*` |
| Chapbook of Grit / Knacks / Wits (red, green, blue books), "Veteran's Diary" | With the almanac, a book family on the ground mirroring the WC3 tomes (object + effect) | **Smith's Horseshoe Nail**, **Juggler's Ball**, **Riddle Knot**, **Old Soldier's Tally-Stick**; the Hedge Almanac is the only book |
| "Woodpecker Gloves" (+15 % attack speed), "Dolmen Crown" (+5 all), "Millstone Girdle" (+6 STR), "Plowman's Belt" (+3 STR) | The WC3 object with the WC3 effect: gloves of haste (+15 %), crown of kings (+5), giant-strength belt (+6), and a belt for STR | **Woodpecker Quill** (+12 %), **Dolmen Keystone** (+4 all, +2 armour), **Millstone Yoke**, **Plow-Horse Brass** |
| "Marching Fife", "Shepherd's Bell" (aura items) | Every WC3 aura item is an instrument (horn, war drums, chimes, janggo) | **Drillmaster's Pace-Stick**, **Shepherd's Crook** |
| Proposed merchant additions "Stoutheart Locket" (+150 HP), "Blank Ledger", "Curl-Up Tonic", "Signpost Staff", an armour scroll | Each pairs the WC3 object with its effect: a pendant for +150 HP, a book for retraining, a potion for invulnerability, a staff for teleport, a scroll for armour | **Stoutheart Weight** (+175 HP), **Wiped Slate**, **Curl-Up Scale**, **Pocket Signpost**, **Oilcloth Capes** |
| "Warm Poultice" (Kiln-Master heal) | Clashes with `kingdom`'s Herb Poultice | **Pine-Tar Dressing** |
| "Receipt's in the bag." (shopkeeper Buy line) | The same shop-receipt gag as a WC3 merchant's annoyed line | **"Counted, tied, and yours."**; receipts are a visual prop only |
| WC3 neutral building names | ip-safety §2.1 and mechanics §12.2 | Weighstall, Contraption Barn, Free Company Camp, Coaching Inn, Hale Spring, Dewstone, Twin Milestones, Lucky Barrow |
| Other games' names for the same item mechanics (a blink dagger, a revive shield, a spell-blocking sphere) | Dota 2 / League of Legends items | Coilspring Heels, Cat's Ninth Life, Hedge-Witch's Knot |
| "Time is money" / "friend" in the merchant's voice | A famous WoW goblin catchphrase | The shopkeeper never uses either |
| Lemmings marching in a line | The image of a famous puzzle game | The lemming gag is cheek-puffing |
| Exploding farm animal after click spam | A famous Blizzard easter egg | No critter explodes or dies |
| "Gold Mine" | A dictionary term (also WC3) | Data id kept; displayed as **Gold Seam** |

### 10.2 Squint-test risks (WC3 names appear here for review only)

| Ours | Nearest existing design | Allowed overlap (genre) | Rule for the art and kit |
|---|---|---|---|
| Sootcoats | WC3 bandits and their level-7 lord | Human outlaw creeps | Wide conical leather hoods, soot faces, rakes, billhooks, smoke-pots. No daggers, purple or red hooded cloaks, invisible assassins, noble-titled leader or passive-aura leader: the level-7 Clamp-Father is named for his craft and carries an active (Rake the Clamp), not an aura |
| Tattiebogles | Blizzard harvest-golem and pumpkin-headed horseman designs; **WoW's Hallow's End** (the Wickerman effigy and Wickerman Guardian); ***Worzel Gummidge*** (a turnip-headed walking scarecrow with swappable heads, made by "the Crowman"); Disney's **Pumpkin King** | Scarecrow folklore | Turnip lanterns with randomly drilled holes, never arranged as a face; **no carved or painted face on a turnip, no swappable or detachable heads, no feather-cloaked "crow-man" figure, no wicker effigy body or cage**; no pumpkins, machinery or horses. The family name is the Scots folk word, not a holiday pun |
| Cairnwakes, Old Menhir | WC3 rock and granite golems | Stone constructs that never sleep | Stacked slabs with visible gaps, menhir heads with cup-and-ring marks. No boulder throw, no rounded rock-man body, no crystal core |
| Mire Toads | WC3 shore fish-folk | Pond creeps | Real toad anatomy and a hop. No spears, nets, upright posture or gurgled speech |
| Stoatkin | WC3 hyena-folk and candle-miner rat-folk | Small animal-folk raiders | Stoat anatomy, white coat, black tail tip. No candles, mining, hyena or rat features |
| Whiteouts | WC3 ice elementals and revenants | Elemental spirits | Cloud bodies with no torso, limbs or armour |
| Longfringe Herd | WC3 drum-backed beast; Blizzard yaks and mammoths | Beasts | Highland-cattle and musk-ox shapes. No drums, riders, tusks or trunks |
| Claywrights | WC3 spider-folk; Blizzard desert bug race | Insect-folk | Upright cream-coloured clay masons with trowels and reed sun-hats. No spider legs, purple chitin, burrowing or swarm god |
| Saltbound | WC3 skeletons and the WC3 undead race | Restless dead | A salt-crystal crust and caravan robes. No visible bones, ziggurats, blight or green skull-glow. Cross-check with `deathless` |
| Rollbacks | WC3 beetle summons | Giant beetles | Brass-green dung-beetles rolling balls. No undead look, burrowing or impale spikes |
| Rundlings, Weighstall | WC3 goblin merchant | A small trader people | Pangolin scales, spectacles, a giant brass balance, fairness comedy. No green skin, big ears, greed, explosives, mech suits or airships. The Rundlings fill only the merchant and one hero role, not the lab |
| Contraption Barn | WC3 goblin laboratory | A neutral workshop that hires out machines | Human hill-country millwrights in a mill-barn with a waterwheel. Its offers no longer map 1:1: the balloon carries 6 food at 200 / 40 and drifts downwind; the ram survives its hits; the fourth offer is a tree-clearing crew, not a paid reveal. No airship, no saw-armed walker robot, no suicide sapper |
| Coaching Inn | WC3 tavern | An inn where heroes are hired | A generic building type with a per-map sign name; coaching inn with a stable arch and a lantern sign |
| **Gold Seam** | **WC3 gold mine** (a rocky mound with a timber-braced entrance and gold showing) | A gold mine that workers enter | Squint test: put the Gold Seam next to the WC3 mine at 64 px. Ours must read as **a cut in a layered cliff face** (horizontal strata, a thin bright seam line) with a **windlass headframe** on top, a **spoil heap** and a **wooden sluice**. No free-standing rock mound, no heaped gold nuggets at the entrance, no mine cart or rails. "Collapses when empty" is shared on purpose and is not a differentiator |
| **Dewstone** | **WC3 mana fountain; night-elf moon well** | A mana landmark | No water body, no blue glow, no stone ring: a dry upright quartz-veined boulder that sweats warm white-gold droplets at dusk, with moths; units regenerating show warm white motes |
| Hale Spring | WC3 health fountain; night-elf moon well | A healing landmark | A moss-ringed natural spring fed by a hollow-log flume with a tiny waterwheel; no carved stone basin or rim, no glowing water, warm sparkles by day only |
| **Beacon Cairn** | **StarCraft II Xel'Naga Tower** (capture by standing next to it, wide vision) | A vision landmark | A low stacked drystone cairn with an iron fire-basket; no obelisk, tower, crystal or glowing alien stone; the team-colour flame is the only glow |
| Items (all) | WC3 item art and object–effect pairs | Generic RPG items | No item pairs the WC3 object with the WC3 effect (gloves for attack speed, a crown for all stats, a belt for STR, books for attributes, instruments for auras, a pendant for +HP, a potion for invulnerability, a staff for teleport, a scroll for armour). Icons are composed from our own descriptions (ip-safety §2.4) |
| Rat-Piper | Folklore's pied piper (public domain); DC's rat-controller; WC3 ranged hero | A rat controller with a ranged weapon | Stovepipe hat, pocket coat, crossbow, tin whistle. No motley, no gas-mask device, no hooded-ranger look |
| Old Menhir | WC3 walking-tree buildings, mountain giants and the stone-and-hammer mountain hero | A big walking piece of landscape | Stone only. No roots, branches, leaves or bark; no hammer, no beard, no hurled bolt. Kit audit against all three in §5.6.7 |
| Weighmaster | WC3 goblin gadget heroes | A small merchant-people hero | A Rundling official with a balance-staff. No flasks, no robot suit, no rider |

### 10.3 Compliance summary

- **Names:** none on the ip-safety §2.1 list; collisions resolved (§10.1).
- **Text and voice:** every tooltip and line here is new. Before recording, check every line against the WC3 quote pages
  (including the tavern heroes and the goblin merchant) and the WoW goblin lines (audio §3.2).
- **Numbers:** the systems and a few common item values deliberately echo WC3 (legal under 17 USC §102(b)): camp colours, XP falloff,
  drop-band shape, upkeep on bounty, +1 attribute power-ups, +3 / +6 attribute items at L2 / L4, +2 armour at L2, +100 XP, the inn
  revive formula. The full balance sheet is not copied: creep stats, most item numbers, prices and drop bands are our own values
  (mechanics §12.2 gray zone), and where an object and an effect together would echo a WC3 item, the object is changed (§10.2 Items).
- **Maps:** the slice layout in §3.6 is written from rules (ip-safety §2.6). Sketch it in `data/maps/` before building.
- **UI:** shield-shaped camp pips, our own neutral-building glyphs (§1.2), a closed-eye sleep glyph, an oilcloth loot bundle and our own
  command-card art: no WC3 icon, chest or "Z".
- **Inputs:** no WC3 data, screenshots or fan assets in any prompt or reference (ip-safety §2.7–2.8). Prompts follow §8.2.
- **Fidelity:** neutral heroes have at most 2 of 4 functional equivalents against every WC3 hero they were compared with (§5.6.7).
  The signature presentation risks (the merchant people, the lab, the stone constructs, the scarecrows, the mine and the landmarks) have
  explicit art rules (§10.2).
- **Hygiene:** WC3 and Blizzard names appear only in rationale and audit text (Conventions); tooltip-ready cells and voice lines are clean.

---

## 11. Open questions and tuning flags

1. **Leash, give-up and return:** 18.75 m, 10 s, 2 %/s regeneration and the 2 s / 3 s unreachable-attacker timers (§1.3) are starting
   values. WC3's real values are unverified (mechanics §14).
2. **Bounty pacing:** 4 × level + 2 + rand(0–4), taxed by upkeep, now puts about 632 gold on the slice map (about 4.5 Pavisiers). Check it
   against mining income in scripted playtests.
3. ~~Night-active camps~~ **Closed:** the slice keeps one `day` camp (the Crow Field); the Turnip Patch sleeps at night (`sleeps_override`),
   and the map rules (§1.5) cap day camps at one per map with at least 60 % night sleepers. Still to watch: do players read the crow tell
   on the one day camp?
4. **Stuffed and Dung Crust** (−25 % Pierce): the slice AI's creep-route picker must weigh camp resistances against army composition
   (clans Javelineers, kingdom Hookgunners).
5. ~~Patron range~~ **Closed:** the use range is rules §16's **7.0 m** from the building edge. The research's "45 (60 before 1.15)" is
   probably warcraft.wiki.gg's ×10-scaled notation for 450 / 600 gu (the same notation lists a melee infantry range as 9), so WC3's range is
   not tighter than ours. The Smugglers' Den's corner layout and `acquire_override: 6.5` cover the whole 7 m band (test
   `shop_guard_coverage`). Fallback if that feels oppressive in playtests: return to a looser ring and accept max-range "sneak buys" by day
   as a WC3-style trick.
6. **Stock ownership:** per player (chosen for fairness) or shared like WC3 (unverified)? The same question applies to the Free Company
   Camp and the Contraption Barn.
7. **Neutral-hero uniqueness:** once per match (first come) is the WC3 feel (reported, unverified). The Long Tune is now capped (6 m,
   8 units, 16 levels, 4 s, breaks on 20 % damage), which removes the main must-rush reason. Re-check in 1v1; the alternative is once per player.
8. **Information leaks:** the Beacon Cairn's minimap flame and the Sparrow Roost flush both reveal positions on purpose. Minimap camp pips
   drawn from 0:00 disappear only when the player sees the cleared spot, so they never reveal an enemy's creeping. Everything else must pass
   the fog-leak test in `juice/combat-and-units.md` ("an enemy in fog fighting a creep produces zero sprites, labels and sounds").
9. **Old Menhir:** Drystone Wall makes up to 10 m of cells temporarily blocked. Check region relabel cost against the pathing budget
   (`architecture.md` §7). Also define how Sleep of Stones interacts with The Wagon Ring and other ultimates (stone units are invulnerable;
   buffs keep ticking). The Hedge-Cutters service (§5.9, *later*) has the same relabel cost when it fells a strip.
10. **The Long Tune:** enthralled units follow a deterministic "follow at most 3.0 m/s" order. Test with cliffs and walls, and the AI's
    response. Tie-break for the level-ordered pick: highest level, then nearest, then lowest unit id.
11. **Weighmaster:** her gold-cost spell needs a gold icon on the command card, a "not enough gold" message, and an AI rule.
12. **Faction cross-checks:** Saltbound vs `deathless`, and Mire Toads / Tattiebogles / Old Menhir / the Dewstone vs `sylvan`. Neither
    later faction may reuse these motifs, and vice versa.
13. **An apex flyer family** (the dragon-like red-camp prize of WC3) is not designed. It needs procedural flight (flyers rig poorly) and
    must avoid colour-coded dragon families and the hatchling-to-adult ladder naming.
14. **Item count:** 52 against the brief's ~40. If the list must shrink, cut only from pool cells that keep at least two candidates
    afterwards (for example Shepherd's Crook, Dewdrop Locket and Dropped Purse), or move the two Lucky Barrow fixed items to a later patch.
15. **"Gold Seam" display name:** if testers miss that it is the gold mine, show "Gold Seam (gold mine)" in the tooltip.
16. ~~Critters in the sim~~ **Closed:** the goose nip is cosmetic, so critters are visual-only in the slice (§6); only the sparrow flush is a
    deterministic sim trigger.
17. **Charge merging** of identical consumables (up to 2 × base) is a quality-of-life change from classic WC3. Keep it unless playtests
    say it hurts shop pressure.
18. **VO volume:** about 26 lines per neutral hero plus 9 for the shopkeeper. Generate all default-voice VO before **31 Dec 2026**
    (audio decision; ElevenLabs default voices expire).
19. **Minimap neutral markers from 0:00** (`rules.minimap.show_unexplored_neutrals`, proposed `true`): verify from recorded WC3 footage
    whether camps, shops and mines show on the black minimap at the start, then set the flag.
20. **Second-hero creep XP:** after T2 the slice map has little left to creep (§3.6). *Later:* one more amber camp per side.
21. **Lift Balloon wind** (*later*): needs a per-map wind vector in `data/maps/` and a readable windsock; check that the 20 % downwind
    bonus is noticed.

**Required follow-up edits in sibling docs** (owners decide; this doc already assumes them):

| Doc | Edit |
|---|---|
| `rules.md` §6.8 (and §21) | Recall items become point-targeted with a 5 s channel that enemy stuns, silences and damage cannot cancel (§4.2); the Homeward Horn and Homeward Felt follow. Otherwise list the Homing Pigeon's difference as a Δ in §21 |
| `rules.md` §6.8, §16, §20 | Buying an item needs an own hero in use range; a full inventory drops the item at the hero's feet; add `rules.items.group_cooldown` (`heal`, `mana` = 8 s) and `rules.minimap.show_unexplored_neutrals` |
| `rules.md` §10.2 | "Hardy creeps" row: counts as a hero for control durations (§6.5) and Spell damage; polymorph and remove-from-game cannot target it |
| `rules.md` §15.1–15.3, §22 | The unreachable-attacker rule replaces the tower rule; camp mode fights a structure that damages it; map sleep rules (≤ 1 `day` camp, ≥ 60 % night sleepers); `sleeps_override`, `acquire_override`, `layout`; tests from §9 |
| `rules.md` §23 Q1, Q4 | Q1 (no-hero XP) is resolved here in rules' favour ("lost"); Q4's use range is adopted |
| `slice-plan.md` §1.4, §1.8, §1.9, §2.6 E16 | Turnip Patch sleeps at night (green 8); add Collier's Hut ×2 (coordinates 40–50 m path from each main, away from the Clamp); 11 camps, 113 levels, 2,465 raw XP, ≈ 632 g; the Coaching Inn becomes P1 (revive only) at (106, 106); the Den uses the corner layout; rename Wayfarers' Inn → Coaching Inn and Glimmer Font → Dewstone |
| `tools/ip/banned_terms.txt` | Add `chaos` once the rules §20.4 migration has removed it from `data/factions.json` and `tests/unit/test_combat.gd` |
| `visual-art-direction.md` §1.4, §7.2; `juice/*.md`; `sylvan-and-deathless.md` | Rename Frostmarch → Rimeholt, Hollow Harvest → Tattiebogles, Wicker Brute → Withy Brute, Turnip King → Old Mangold, Earthbound → Set in Stone, Glimmer Font → Dewstone, Wayfarers' Inn → Coaching Inn, Chapbooks / Veteran's Diary → the new power-ups (mechanical find-and-replace; nothing is in data yet) |

---

## Review log (2026-10-17: IP-safety and WC3-fidelity reviews)

Where IP and fidelity conflicted, IP won and the closest legal alternative was taken. Severity as given by the reviewers.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | Tileset "Frostmarch" is a fantasy-game product title (*Talisman: The Frostmarch*) | Renamed **Rimeholt** everywhere; camp prefix `fm_` → `rh_`; §10.1 row |
| 2 | Major | "Tip the Scales" is an exact WoW / Hearthstone ability name | Renamed **Even the Ledger**; mechanic unchanged; §5.6.7 audit updated (no VO line names the ability); §10.1 row |
| 3 | Major | "Stampede" is the WC3 Beastmaster ultimate (and WoW / Hearthstone) | Renamed **Herd Rush**; Bellowing Charge reads "As Herd Rush, 12 m"; §10.1 row |
| 4 | Major | The Earl of Ash rebuilt the WC3 bandit lord (title, level 7, Pure, passive aura) | **Clamp-Father** (`creep_sootcoat_clamp_father`), camp **Clamp-Father's Yard** (`camp_gv_clamp_fathers_yard`); Cinder Cloak aura replaced by the active **Rake the Clamp** (3 m, 60 Spell damage then 8/s for 3 s, cooldown 12 s); Call the Gang kept; G1 "Never" rule and §10.2 row extended |
| 5 | Major | Glimmer Font = WC3 mana fountain + moon well | Redesigned as **Dewstone** (`neutral_dewstone`): a dry quartz-veined boulder sweating warm white-gold droplets at dusk, moths; no water, basin, lilies, stone ring or blue glow; warm white motes on units; footprint 4×4; §10.2 squint row; §8.2 prompt rule |
| 6 | Minor | Items reused WC3 object + effect (gloves +15 %, crown +5, belt +6, coloured books, instrument auras) | Woodpecker Quill +12 %; Dolmen Keystone +4 all, +2 armour; Millstone Yoke; Smith's Horseshoe Nail / Juggler's Ball / Riddle Knot (non-book props, no colour code); Old Soldier's Tally-Stick; Drillmaster's Pace-Stick; Shepherd's Crook; §4.7 pools and §9 ids updated. **Extra:** Plowman's Belt (+3 STR, a belt for STR) → **Plow-Horse Brass** |
| 7 | Minor | Contraption Barn copied the goblin lab offer by offer, staffed by the merchant people | Staffed by **human hill-country millwrights** (the Rundling model now only for shop, Barrow pedlar and Weighmaster); Lift Balloon **6 food, 200 g / 40 l, +20 % downwind**; Survey Lantern replaced by the original **Hedge-Cutters** service (fells a 6 m × 2 m tree strip); §0.2 row and §10.2 row record it |
| 8 | Minor | Beacon Cairn was called original, but SC2's Xel'Naga Tower has the mechanic | §0.2 and §5.11 reworded as the reviewer asked; look made a low, broad cairn; §10.2 row against the Xel'Naga Tower |
| 9 | Minor | "Collapses when empty" is WC3's rule, and the mine look was the generic WC3 image | Moved to "Kept familiar"; the **layered cliff seam** is the differentiator; ore cart and rails replaced by a **windlass headframe, spoil heap and wooden sluice**; §10.2 squint row against the WC3 mine |
| 10 | Minor | WC3 attack-type ids `hero` and `chaos` | Conventions and §1.1 use `heroic` and `pure`; `adamant` added to the armour list; §9 shows `pure` and `heroic` entries. `chaos` is **not yet** added to `tools/ip/banned_terms.txt`, because `data/factions.json` and `tests/unit/test_combat.gd` still use it until the rules §20.4 migration, and adding it now would fail the IP check; the follow-up is listed in §9 and §11 |
| 11 | Minor | The "WC3 names only in §0.2, §5.6.7, §10" claim was false | Conventions reworded as the reviewer proposed (rationale and audit text only; never ids, data, UI, filenames or prompts); rule bullets now mark rationale with *Why:*; "Amber (WC3's orange band)" label and other tooltip-ready cells cleaned; §10.3 hygiene line |
| 12 | Minor | Hollow Harvest near-reads: WoW Hallow's End Wickerman, *Worzel Gummidge*, "Pumpkin King" | Both added to §10.2 with the art rules (no swappable heads, no face on a turnip, no feather-cloaked crow-man, no wicker effigy body); **Withy Brute** (bound willow-rod bundles), **Old Mangold** (Old Mangold's Sickle); family renamed **Tattiebogles**; artifact Hollow Lantern → **Mangold Lantern**; §8.2 prompt rules |
| 13 | Minor | "Moundbuilders" names a real-world culture tied to a racist myth | **Claywrights** (Claywright Mason, Claywright Drummer, the Mother-Mound's Champion), ids `creep_claywright_*`; a naming rule in S1. **Extra:** "Swarm Rise" contradicted the family's no-swarm, no-burrowing rule → **The Mound Opens** |
| 14 | Minor | "Wayfarer's Inn" is a used fantasy-inn name (Ultima, *Tavern Talk*; WoW "Wayfarer's Rest") | Building type **Coaching Inn** (`neutral_coaching_inn`) with a per-map sign name (Greenvale: *The Muddy Lantern*); §10.1 rows |
| 15 | Minor | "Ironwood" is DotA's signature item word | **Blackthorn Knuckles** (`item_blackthorn_knuckles`) |
| 16 | Minor | "Carapace" echoes the Crypt Lord's Spiked Carapace | **Dung Crust** (−25 % from Pierce, unchanged) |
| 17 | Minor | "Chill Touch" (D&D) and "Earthbound" (Nintendo) | **Frostnip** and **Set in Stone** |
| 18 | Minor | Old Menhir audited only against the Brewmaster | Audit adds the Mountain King and the Mountain Giant. Both margin fixes applied: **Lichen Hide** is now "the first attack in any 3 s window is reduced by 25 / 40 / 55, plus 1 / 2 / 3 HP/s", and the **Sleep of Stones** ring pushes 1 m instead of slowing. Count is 1 against each |
| 19 | Minor | "Receipt's in the bag." reused the WC3 merchant's receipt gag | Replaced with **"Counted, tied, and yours."**; receipts are a visual prop only, kept out of the VO script |
| 20 | Minor | "Shagbull" reads as British slang | **Longfringe Herd** (Longfringe Calf, Longfringe Bull, Herd-Bull, Grandsire), ids `creep_longfringe_*`, camp `camp_rh_longfringe_herd` |
| 21 | Major | Only 3 of 9 slice camps slept at night | `sleeps_override` added; **Turnip Patch → `night`** with the crow-slump tell and the line "tame scarecrows that guard by day"; only the **Crow Field** stays `day`; map rules **≤ 1 `day` camp, ≥ 60 % night sleepers** (§1.5); result 7 night, 3 never, 1 day; §3.6 "Why" updated; open question §11 #3 closed; rules §15.3 and slice-plan §1.8 listed as follow-ups; test `camp_sleep_ratio` |
| 22 | Major | Too little creep XP for level 3 by 5:30 | **Collier's Hut [SLICE] ×2** (green 8, 165 XP, 48 g; 0 new assets), 40–50 m from each main away from the Clamp; **Turnip Patch = Fieldkeeper ×2 + Strawling ×2** (green 8, 170 XP, 48 g, Drop B L2 any); totals **11 camps (6 / 4 / 1), 113 levels, 2,465 raw XP, ≈ 632 g** (the reviewer's 624 g recomputed per camp); §3.6 XP-check table rewritten (Clamp 92 → Patch ≈ 225 (L2) → Hut ≈ 340 → Fold ≈ 540 (L3) by ≈ 5:30); second-hero gap noted (§11 #20) |
| 23 | Major | §1.6 said heroes elsewhere still get XP, against rules §6.4 | Replaced with the reviewer's sentence (XP lost if no eligible hero within 18.75 m, `rules.xp.no_hero_in_range`); §3.6 notes the route assumes the hero is present |
| 24 | Major | Inn revive formula contradicted rules §6.7 | Formula deleted; §5.5 points to rules §6.7 and `rules.heroes.inn_revive` (340 g / 80 l at L1 … 1,105 g / 260 l at L10) and adds "needs 5 free food (rules §4.4)" |
| 25 | Major | Patron range 4 m contradicted rules §16's 7.0 m; the Den could be bypassed | §5.1 uses 7.0 m (rules §16); `patron_range` removed from §9; §11 #5 rewritten and closed. **Deviation:** the reviewer's `acquire_override: 5.0` leaves gaps with four creeps (computed: four creeps need 6.4 m to cover the 7 m band), so the Den stands 3.5 m out from the stall's four corners with **`acquire_override: 6.5`**; test `shop_guard_coverage` added |
| 26 | Major | Homing Pigeon lost the "save the army with a scroll" pillar | Point-targeted (minimap too), nearest own hall to the point, double-tap = highest-tier hall; **5 s channel not cancelled by enemy stuns, silences or damage**, only by death or own orders; charge spent on completion; data `"target": "point_nearest_own_hall", "channel": 5.0, "enemy_interruptible": false`; rules §6.8 change requested (or a Δ in §21); test `recall_point_target` |
| 27 | Major | The Long Tune disabled the whole army for 6 s | Radius **6 m**, at most **8 units, 16 levels**, highest level first; **4 s** (2 s on level-5+ units and Hardy creeps); breaks on **20 % max-HP damage**; mana 175, cooldown **180 s**; follow 3.0 m/s and walk 2.4 m/s kept |
| 28 | Major | Camps could be farmed from unreachable positions | The tower rule is replaced by the reviewer's **unreachable-attacker rule** (2 s drop, 3 s whole-camp return, regenerating 2 %/s, ignore until reachable); camp mode fights a structure that damages it; test `creep_unreachable_attacker`; §1.4 give-up note |
| 29 | Major | No tavern in the slice | **Coaching Inn [SLICE] (P1), instant revive only**, at (106, 106); hiring the Rat-Piper stays [SLICE+]; inn-hired first hero gets the recall item (rules §3.2); §7 and §8.1 (≈ 0.5–1 cr) updated |
| 30 | Major | The merchant lacked mid-game decisions | Added with our own names, numbers and **objects** (IP wins over the reviewer's suggested objects, which each paired a WC3 object with its effect): **Stoutheart Weight** [SLICE] +175 HP, 300 g, 1 / 120 s, from 4:00 (`stat_bonus`); **Wiped Slate** [SLICE] skill reset, 280 g, 1 / 300 s, from 5:00 (`retrain`); **Curl-Up Scale** [SLICE+] 6 s self-stasis, 140 g, 1 / 90 s, from 6:00 (`self_invulnerable`); *later* **Pocket Signpost** and **Oilcloth Capes** (sold as Lucky Barrow fixed slots, since the Weighstall card is full). Slice items 31 (32 with SLICE+), icons ≈ 12 cr, scripts listed |
| 31 | Minor | No creep heals or dispels | Kiln-Master **Pine-Tar Dressing** (heals an allied creep 150 HP, 6 m, 50 mana, 8 s); named so it does not clash with `kingdom`'s Herb Poultice. Optional Crowcaller **Re-Stuff** (120 HP on a Tattiebogle ally, 60 mana, 10 s) also added; §1.7 heal AI row; 2 icons |
| 32 | Minor | Hardy did not shorten stuns and other control | Hardy now counts as a hero for control durations (rules §6.5) and Spell damage; polymorph and remove-from-game cannot target it; rules §10.2 follow-up listed |
| 33 | Minor | Item cooldowns per id; potions could be chain-drunk | `cooldown_group` per hero (rules §6.8); Rosehip in `heal`, Bluebell in `mana`; proposed `rules.items.group_cooldown` 8 s; §9 sketch |
| 34 | Minor | Give range, buying without a hero, full inventory, `unique` flags | Give 1.5 m to own heroes; buying needs an own hero in use range, services any unit; full inventory drops at the hero's feet; `unique` on Hobnails, Coilspring Heels, Thistledown Cloak, Pace-Stick and Crook (tables and §9) |
| 35 | Minor | Hall gap 4 m and natural 55–65 m contradicted rules §3.3 | "6.0 m edge to edge (rules §3.3)", "natural at 40–60 m path distance; exact positions in slice-plan §1.4"; §5.2 "about 5 workers saturate at the 6.0 m gap" |
| 36 | Minor | Critter density formula gave 80–100 critters | "Hand-placed on the slice map (10–14)"; generated maps "about 0.4 per chunk of open ground, at most 14 per map" |
| 37 | Minor | The goose nip dealt real damage | Nip is `"cosmetic": true` (animation, honk, hit flash; no HP change, no damage event); critters are visual-only in the slice; sparrow flush is a deterministic trigger; §11 #16 closed |
| 38 | Minor | Drop-carrier ties, summons, and no camp layout | Tie-break by `creeps` order, summons never carry, item drops where the carrier dies; new §1.9 with `layout` and the default 2.5 m ring; test `drop_carrier` |
| 39 | Minor | No script for permanent attribute gains | `grant_attribute` added; with `retrain`, 14 slice scripts (`self_invulnerable` is SLICE+) |
| 40 | Minor | Minimap pips only after exploring; only the mine had a glyph | Flag `rules.minimap.show_unexplored_neutrals` (proposed `true`, set from footage): markers from 0:00, a cleared pip disappears only once seen; our own glyphs for the Weighstall (balance), Hale Spring (droplet ring), Coaching Inn (lantern) and later buildings (§1.2) |
| 41 | Minor | Stand Still / Settle always on in melee | Both now need **neither moving nor attacking** (ambush armour that drops on the first swing); Fold fight re-estimated at ≈ 3,030 Blade-effective HP (was ≈ 3,310), ≈ 40 s at ≈ 75 dps |
| 42 | Minor | Level-6 baseline not monotone | Level 6 melee: **1,000–1,100 HP, 30–34 average damage**; the ranged / caster note kept (the level-6 casters and ranged creeps fit 60–75 %) |
| 43 | Minor | `help_radius` named but unused | Deleted; the sentence now says other camps never join, however close |
| 44 | Minor | Audit closing line and §10.3 "our own values" overstated | Audit line reworded as proposed (The Long Tune counted as a Charm equivalent); §10.3 now says systems and a few common item values deliberately echo WC3 (legal under §102(b)) and the full balance sheet is not copied |
| 45 | Minor | No neutral command cards | §5.1 card table: Weighstall (R B H P F K W T L C J + Tab; stock badges, restock sweep, "from 4:00" grey-out, no-hero grey-out, sell gesture), Lucky Barrow, Coaching Inn (hire buttons with portrait and 425 / 135, grey when taken; Revive per dead hero with the rules §6.7 cost), Free Company Camp, Contraption Barn |
