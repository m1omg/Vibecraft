# Neutral layer design: creeps, items, neutral buildings and critters

*Design date: 2026-10-16. Status: proposal for review. Scope: everything on the map that belongs to no player: creep camps,
items, neutral buildings (gold mine, merchant, inn, mercenaries, fountains, lab, gate, vision tower), neutral heroes and critters.
Data owners: `PlayerState.NEUTRAL_HOSTILE = 12` (creeps) and `PlayerState.NEUTRAL_PASSIVE = 13` (mines, shops, critters), per `architecture.md`.*

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
- Attack types: Blade, Pierce, Siege, Arcane, Heroic, Spell, **Pure** (data ids `blade, pierce, siege, arcane, hero, spell, chaos`).
  Armour types: Light, Medium, Heavy, Fortified, Hero, Unarmored.
- "Lvl" is the creep's **level**: it sets XP value and bounty, and sums into the camp's colour.
- Ids use the prefixes `creep_`, `camp_`, `item_`, `neutral_`, `nhero_` and `critter_`.
- Slice tags:
  - **[SLICE]**: in the vertical slice (kingdom vs clans, 1v1 vs AI, the Greenvale map).
  - **[SLICE+]**: a stretch goal if the budget holds.
  - *later*: full game only.
- WC3 names appear in this document **only** inside the fidelity and audit tables (§0.2, §5.6.7, §10), for review. They never go into data, UI, filenames or prompts.

---

## 0. At a glance

### 0.1 Summary

| | Choice |
|---|---|
| **Creep families** | 10 families, 43 creep types, levels 1–9. **Greenvale** (slice tileset): Sootcoats (charcoal-burner outlaws), Hollow Harvest (walking scarecrows, awake at night), Cairnwakes (drystone constructs that never sleep; universal), Mire Toads. **Frostmarch** (later): Stoatkin, Whiteouts, Shagbull Herd. **Sunscar Steppe** (later): Moundbuilders, Saltbound, Rollbacks |
| **Camp rules** | Green 1–9 / amber 10–19 / red 20+ total level. Creeps sleep at night (with two deliberate exceptions: **never-sleep** and **night-active** families). Leash 18.75 m. XP = the global unit-kill table × the creep factor. Bounty 4 × level + 2 + rand(0–4), taxed by upkeep. No respawn |
| **Items** | **47 items** in five classes (purchasable, power-up, permanent, charged, artifact), item levels 1–8, drop tables by camp total level, all names original |
| **Merchant people** | **Rundlings**: knee-high, pangolin-like traders who curl into a ball when frightened and are obsessed with *fair* weight, not profit |
| **Neutral buildings** | **Gold Seam** (gold mine), **Weighstall** (merchant), **Lucky Barrow** (rotating rare stock), **Wayfarers' Inn** (neutral heroes), **Free Company Camp** (mercenaries), **Hale Spring** / **Glimmer Font** (health / mana fountains), **Contraption Barn** (lab-equivalent), **Twin Milestones** (paired teleport), **Beacon Cairn** (capturable vision tower) |
| **Neutral heroes** | **Rat-Piper** (AGI ranged trapper and rat summoner), **Old Menhir** (STR stone tank who walls and shoves), **Weighmaster** (INT Rundling support who pays gold for hired pikes) |
| **Critters** | Hares, geese, hedgehogs, fireflies and a flushing sparrow roost in Greenvale; snow hares, ptarmigan and lemmings in Frostmarch; meerkats and guinea fowl in Sunscar. Each has its own click-spam gag; **nothing explodes** |
| **Slice subset** | 10 creep types in 3 families, 9 camps (4 green, 4 amber, 1 red), 29 items, Gold Seam ×4, Weighstall, Hale Spring, 2 critters + fireflies. [SLICE+]: Wicker Brute, Rat-Piper at the Wayfarers' Inn, Free Company Camp, Beacon Cairn ×2, Glimmer Font, sparrow roosts (§7) |

### 0.2 Fidelity map (WC3 neutral element → Vibecraft)

Function stays close to WC3 on purpose. Expression (names, designs, visuals, text, sounds, icons) is ours.

| WC3 element (reference only) | Vibecraft | Kept familiar (function, numbers) | Made ours |
|---|---|---|---|
| Creep camps, levels 1–10, camp colours by total level | Creep camps | Level bands, XP falloff by hero level, item drops by camp level, sleep at night, leash, no respawn, camp acts as one | Families and designs; **shield-shaped minimap pips** (not dots); sleep shown by in-world posture plus snore puffs, not a "Z"; never-sleep and night-active families as a planned mix |
| Gold Mine | **Gold Seam** | 12,000 / 8,000 gold, 5-worker saturation, low-gold warning | A timbered adit cut into a cliff seam, lit by lanterns at night; collapses to rubble when empty |
| Goblin Merchant | **Weighstall** | Potions, recall, wards, reveal, boots; buys items at 50 % | A market stall under a giant brass balance; Rundling traders; comedy of fussy honesty (never greed, never explosives) |
| Marketplace | **Lucky Barrow** *(later)* | Rotating random stronger items | A pedlar's handcart; restocks on a visible timer |
| Tavern | **Wayfarers' Inn** | Hire neutral heroes with any faction; instant revive; never guarded | Three original heroes; kits follow the 2-of-4 rule (§5.6.7) |
| Mercenary Camp | **Free Company Camp** | Hire local creep types; stock and restock | Hiring board with tally sticks; rosters per tileset |
| Goblin Laboratory | **Contraption Barn** *(later)* | Lumber machine, transport, area reveal | Balloon instead of an airship; a **Ram-Barrow** instead of a suicide sapper |
| Fountain of Health / Mana | **Hale Spring** / **Glimmer Font** | Area regeneration around a contested landmark | A spring pool fed by a log flume; guarded by a night-active camp, so it is free by day and dangerous by night |
| Way Gate | **Twin Milestones** *(later)* | Paired teleport | Units fold into road dust; per-unit cooldown |
| (no WC3 equivalent) | **Beacon Cairn** [SLICE+] | — | Original: capture by standing, fuel timer, visible flame |
| Critters (and the click-spam sheep gag) | Critters | Neutral passive ambient animals | Every gag is original; no exploding animals |
| Item levels 1–8 and classes | Items | Same classes and levels | All names, numbers and effects ours; dropped items are a **twine-tied oilcloth bundle**, not a chest |

---

## 1. Global creep rules

### 1.1 Level stat curve (baseline; each creep deviates by role)

Creeps are a little weaker per level than player units of the same level, as in WC3. Baselines are for a melee creep.
Ranged creeps and casters get about 60–75 % of the melee HP, brutes about 120 %.

| Lvl | HP (melee) | Avg damage | Cooldown (s) | Armour | XP (global table) | Bounty (gold) | Spell resistance | Attack type |
|---|---|---|---|---|---|---|---|---|
| 1 | 200–240 | 8–9 | 1.2–1.6 | 0 | 25 | 6–10 | — | by role |
| 2 | 340–420 | 11–13 | 1.6–1.8 | 1 | 40 | 10–14 | — | by role |
| 3 | 460–520 | 14–17 | 1.6–1.8 | 1–2 | 60 | 14–18 | — | by role |
| 4 | 560–720 | 19–22 | 1.4–1.8 | 1–2 | 85 | 18–22 | — | by role |
| 5 | 760–980 | 26–29 | 1.8–2.1 | 2 | 115 | 22–26 | — | by role |
| 6 | 760–1050 | 22–33 | 1.9–2.0 | 2–3 | 150 | 26–30 | **Hardy** 30 % | by role |
| 7 | 1250–1350 | 38–40 | 1.7–2.2 | 3–5 | 190 | 30–34 | **Hardy** 30 % | **Pure** |
| 8 | 1500–1800 | 45–49 | 1.8–2.0 | 3–5 | 235 | 34–38 | **Hardy** 30 % | **Pure** |
| 9 | 2100 | 58 | 2.4 | 6 | 285 | 38–42 | **Hardy** 30 % | **Pure** |
| 10 | (reserved) | — | — | — | 340 | 42–46 | **Hardy** 30 % | **Pure** |

- **Hardy (level 6+):** Spell damage taken ×0.7 (the same multiplier the matrix gives the Hero armour type), and
  sleep, polymorph, enthral and root effects last 50 % as long. This mirrors WC3's "level 6+ creeps have hero magic resistance".
- **Pure from level 7:** every creep of level 7 or more attacks with Pure (data id `chaos`), ignoring the armour-type matrix
  (WC3's "level 7+ creeps deal Chaos").
- **Regeneration:** 0.25 HP/s for organic creeps, 0 for constructs and the dead; casters regenerate 0.6 mana/s and start full.
- **Sight:** 14 m day / 9 m night (used only by creep AI; creeps grant no vision to any player).
- **Default collision radius:** small 0.3 m, standard 0.45 m, large 0.7–1.0 m.

### 1.2 Camp colour and the minimap

| Colour | Total camp level | Typical position | Typical drop |
|---|---|---|---|
| **Green** | 1–9 | Near each start, off the main road | One L1 power-up or one L2 item |
| **Amber** (WC3's "orange" band) | 10–19 | Expansions, neutral buildings, flanks | L1 power-up + an L2–L3 item |
| **Red** | 20+ (slice: 20) | Contested pockets toward the centre | L2 item + an L4–L7 item |

- **Pip design (ours):** a small upright **shield shape with a notch at the top**, filled green (#5FBF4A), amber (#E8A93A) or red (#D9483B),
  with a 1 px dark rim. It is drawn on the minimap once the camp's area has been explored, stays as a last-seen ghost in fog and
  disappears when the camp is cleared. WC3's round camp dots are not copied (ip-safety §2.4 and mechanics §12.2).
- A minimap toggle, **Show Camps**, hides the pips (default on).
- Hovering a camp in the world shows a tooltip with the camp's colour word and "Sleeping" or "Awake". It never shows the drop.

### 1.3 Aggro: camp mode, guard mode and help

- **Acquire range:** 3.9 m (250 gu) by default, 5.0 m for casters, **6.0 m for guard-mode camps**. Creeps auto-acquire only units
  of real players (never critters or other neutrals).
- **The camp acts as one.** Every creep has a `camp_id`. When any member acquires a target or takes damage, every awake member of
  that camp engages. Members of *other* camps never join, even inside the 6 m `help_radius` (prevents chain pulls between camps).
- **Camp mode** (default for every camp that guards no gold mine): the camp fights only units that come into acquire range or attack
  it. It ignores buildings, including buildings under construction next to it.
- **Guard mode** (camps at expansion gold mines): as camp mode, plus the camp **attacks any building started within 12 m** of its centre.
  So an expansion cannot be "built through" its guards (mechanics §5 design note).
- **Flyers:** creeps that are not fighting do not acquire flying units. Once engaged, ranged creeps shoot flyers normally.
- **Towers:** a creep that is being hit by a tower it cannot reach drops that target after 2 s and returns home.
- **Creep notice (juice CMB-06):** creeps lift their heads toward an intruder at 1.5× acquire range, so the pull distance can be felt before it is tripped.

### 1.4 Leash and return

- **Leash:** 18.75 m from each creep's **guard position** (its spawn point). A creep past the leash drops its target and returns.
- **Give-up timer:** if the camp has neither dealt nor taken damage for 10 s, every member returns.
- **Returning:** creeps walk home ignoring hits (they are **not invulnerable**) and regenerate **2 % of max HP per second** until home,
  then resume normal regeneration. Head-down "leashing" gait per juice CMB-33.
- Because the camp acts as one, a single creep cannot be pulled away from its camp-mates. The whole camp can still be dragged toward
  your army or towers, up to the leash, and slow members turn back first (the classic "pull and fight at home" play).
- **Tuning flag:** WC3's real leash and give-up values are unverified (mechanics §14). 18.75 m and 10 s are starting values.

### 1.5 Day and night

Every creep has a **sleep schedule**: `night` (default), `never` or `day` (night-active).

| Schedule | Asleep | Families | Why |
|---|---|---|---|
| `night` | 18:00 → 06:00 | Sootcoats, Mire Toads, Stoatkin, Shagbull Herd, Moundbuilders | The WC3 default: night is safe for scouting past camps |
| `never` | Never | Cairnwakes, Whiteouts, Saltbound | WC3 has never-sleeping creeps too (golems, the dead) |
| `day` | 06:00 → 18:00 | **Hollow Harvest**, **Rollbacks** | **Original twist:** scarecrows slump on their poles by day and walk at night; dung-beetles roll by starlight. One per tileset at most, so the rule stays readable |

- **Falling asleep:** each creep falls asleep 0–6 s after its sleep time (seeded stagger), only if its camp is not fighting and is home.
- **Waking up:** at its wake time (+0–6 s stagger), or at once when:
  1. it or a camp-mate takes damage (the whole camp wakes);
  2. a building is started within 12 m;
  3. a player **buys or hires** at a neutral building within 10 m (passive auras such as a spring's healing do not wake anyone).
- **Players' units never auto-acquire sleeping creeps.** Attacking them is an explicit order (attack, or attack-move onto them).
- **Sleep tells (ours, instead of WC3's "Z"):**
  - **In-world posture per family:** Sootcoats doze around a banked fire with smoke puffing from their hoods;
    Hollow Harvest slump on their poles with a **crow perched on each head** (the crow flies off when they wake: that is the tell);
    toads half-sink with eyes shut; stoats curl nose-to-tail.
  - **Small UI glyph:** a closed-eye glyph above the health bar plus slow drifting snore puffs (VFX). Never letters.
- **Night sight drops** for players (global rule), so night creeping trades safety for vision.

### 1.6 XP and bounty

- **XP** per kill = the global unit-kill table by creep level (25 / 40 / 60 / 85 / 115 / 150 / 190 / 235 / 285 / 340)
  × the creep XP factor of the receiving hero's level (80 / 70 / 60 / 50 / **0 %** at levels 1 / 2 / 3 / 4 / 5+).
  It is split evenly between the owner's heroes within 18.75 m of the kill. With no hero nearby, the owner's heroes still get it (global rule).
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
| Heal / regeneration aura | Passive | — |
| Silence or blind area | An enemy hero starts casting, or 2+ enemy casters/ranged units are clustered | That cluster |
| Pull | Off cooldown | The farthest enemy ranged unit or caster in range |
| Once-only "last stand" passive | Automatic at its HP threshold | — |

Creep casters keep 1.5 m more distance than melee creeps and never flee.

### 1.8 Item drops

- A camp template lists up to two drops (§3.1). **Drop B** (the better item) is carried by the camp's **highest-level** creep,
  **Drop A** by its **lowest-level** creep. A single drop is carried by the highest-level creep. The player learns
  "kill the big one for the prize", as in WC3.
- The item for each drop slot is chosen at **match start** from the matching pool (§4.7) by the seeded sim RNG. Boss camps may name a fixed item.
- **Ground visual:** a twine-tied **oilcloth bundle** with a red wax seal (bpy prop). It glints every 3 s and casts a small warm light at night.
  Power-ups instead show as their own small prop (book, berries, purse) so the player can see what they are.
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
| G2 | **Hollow Harvest** (walking scarecrows) | Greenvale | Stick-and-sack biped, stiff joints | **Day** (night-active) | 1, 3, 4, 5, 8 | 5 | 1 AI mesh (or bpy sticks and cloth); Strawling and crows procedural | **[SLICE]** 3, [SLICE+] 1 |
| G3 | **Cairnwakes** (drystone constructs) | **Universal** (retinted per tileset) | Stacked stone slabs | **Never** | 3, 5, 7, 9 | 4 | bpy procedural, rigid segments: **0 3D credits** | **[SLICE]** 3 of 4 |
| G4 | **Mire Toads** | Greenvale | Toad, hops | Night | 1, 3, 5, 7 | 4 | bpy procedural body, squash-and-stretch hop | *later* |
| F1 | **Stoatkin** (ermine raiders) | Frostmarch | Small mustelid biped 1.1 m | Night | 1, 2, 4, 6 | 4 | 1 AI mesh + props | *later* |
| F2 | **Whiteouts** (snow-squall spirits) | Frostmarch | Floating cloud body | Never | 2, 4, 6, 8 | 4 | bpy + shader, no rig | *later* |
| F3 | **Shagbull Herd** | Frostmarch | Shaggy quadruped | Night | 2, 4, 6, 8 | 4 | 1 AI mesh, quadruped rig risk | *later* |
| S1 | **Moundbuilders** (termite masons) | Sunscar Steppe | Insect biped 1.4–2.4 m | Night | 1, 2, 3, 5, 8 | 5 | 1–2 AI meshes | *later* |
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
- **Never:** purple or red hooded cloaks, daggers-and-masks rogue kit, invisibility assassins (that is the WC3 bandit set; §10.2).
- **Palette:** soot #2E2B29, oilcloth ochre #A07A3A, faded moss #5E6B3E; ember accent #E07A2A glows in hood smoke at night.
- **Inspiration:** the historic European woodland charcoal trade (a craft, not a culture).
- **Sound:** wordless. Coughs, grunts and a hoarse "Hup!", a coin flick for Light Fingers, crackling embers.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_sootcoat_cutpurse` | Sootcoat Cutpurse | 1 | 230 | – | 0 Medium | Blade | 8–10 | 1.5 | melee 0.6 | 4.4 | Light Fingers | **[SLICE]** |
| `creep_sootcoat_smoker` | Sootcoat Smoker | 2 | 260 | 150 | 0 Unarmored | Pierce (hot coal) | 10–13 | 2.0 | 6.0 | 4.2 | Smoke Pot | **[SLICE]** |
| `creep_sootcoat_collier` | Sootcoat Collier | 3 | 520 | – | 2 Heavy | Blade | 15–19 | 1.7 | melee 1.0 (rake) | 4.0 | Ember Rake | **[SLICE]** |
| `creep_sootcoat_kiln_master` | Kiln-Master | 5 | 760 | 250 | 2 Medium | Blade | 24–30 | 1.8 | melee 1.0 | 4.2 | Banked Coals, Choking Fumes | **[SLICE]** |
| `creep_sootcoat_earl_of_ash` | Earl of Ash | 7 | 1250 | – | 3 Heavy | Pure | 34–42 | 1.7 | melee 1.1 | 4.2 | Hardy, Cinder Cloak, Call the Gang | *later* |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Light Fingers** | Cutpurse | Passive | Its first hit on an enemy hero steals **6 gold** from that hero's owner (once per Cutpurse). The stolen gold is added to its bounty |
| **Smoke Pot** | Smoker | Point, 7 m | 3 m cloud for 8 s: enemy units inside have a **30 % miss chance**. 60 mana, cooldown 18 s |
| **Ember Rake** | Collier | Passive | Every 3rd attack sets the target alight: **6 Spell damage/s for 3 s** (refreshes, does not stack) |
| **Banked Coals** | Kiln-Master | Aura, 8 m | Allied creeps regenerate **+1.5 HP/s** and attack **10 %** faster |
| **Choking Fumes** | Kiln-Master | Unit target, 7 m | A 3 m cloud on the target for 3 s: enemies inside are **silenced 3 s** and slowed 25 %. 75 mana, cooldown 16 s |
| **Cinder Cloak** | Earl of Ash | Aura, 2.5 m | Enemy ground units take **10 Spell damage/s** |
| **Call the Gang** | Earl of Ash | Once, on first aggro | 2 Cutpurses climb out of the clamp (summons, 30 s; 50 % XP, no bounty) |

#### G2. Hollow Harvest: scarecrows that walk at night [SLICE]

- **Concept:** field scarecrows that a hedge-spirit long ago taught to walk. **By day they slump on their poles in a turnip field**,
  each with a crow on its head. **At dusk the crows lift off and the field gets up.** They are the Greenvale night-active family (§1.5).
- **Look:**
  - Crossed-pole frames inside patched coats, stuffed sacking faces with stitched features, straw spilling at the joints,
    harrow-tine fingers.
  - The larger ones have **pierced turnip lanterns** for heads. The light shows through a sieve of drilled holes, never a carved grin,
    which keeps them away from pumpkin-head designs.
  - They walk **stiff-kneed** (the "toy" motion the art doc wants).
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
| `creep_harvest_crowcaller` | Crowcaller | 4 | 420 | 200 | 0 Unarmored | Arcane | 13–16 | 1.9 | 6.5 | 3.8 | Stuffed, Scatter-Crows | **[SLICE]** |
| `creep_harvest_wicker_brute` | Wicker Brute | 5 | 980 | – | 2 Heavy | Blade | 26–32 | 2.1 | melee 1.2 | 3.6 | Stuffed, Harrow Slam | [SLICE+] |
| `creep_harvest_turnip_king` | Turnip King | 8 | 1800 | 300 | 4 Heavy | Pure | 44–54 | 2.0 | melee 1.3 | 4.0 | Hardy, Stuffed, Lantern Glare, Last Sheaf | *later* |
| `creep_harvest_crow` (summon) | Crow | 1 | 110 | – | 0 Light | Pierce (peck) | 6–8 | 1.3 | melee 0.8 | 5.5 flying | — | **[SLICE]** |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Loose Straw** | Strawling | On death | Leaves a 2 m straw patch for 4 s: enemies inside move 20 % slower |
| **Stuffed** | All but Strawling and Crow | Passive | −25 % damage taken from Pierce |
| **Stand Still** | Fieldkeeper | Passive | After 3 s without moving: +3 armour until it moves |
| **Scatter-Crows** | Crowcaller | No target | 3 Crows (flying summons, 20 s; 50 % XP). 80 mana, cooldown 25 s. Used on aggro |
| **Harrow Slam** | Wicker Brute | No target, 3 m | 50 Spell damage and **stun 1.0 s** (heroes 0.5 s). Cooldown 12 s |
| **Lantern Glare** | Turnip King | Cone 6 m, 60° | 80 Spell damage; struck enemies **flee** from him for 2 s (heroes 1 s). 100 mana, cooldown 15 s |
| **Last Sheaf** | Turnip King | Once, at 25 % HP | Roots himself and re-stuffs for 3 s, healing **40 % of max HP** over that time. Kill him through it or lose the fight |

#### G3. Cairnwakes: drystone that got up (universal) [SLICE]

- **Concept:** the old field walls, cairns and standing stones of the hills, woken by whatever runs under them.
  They **never sleep**: the stones were asleep for a thousand years and are making up for it.
- **Look:**
  - Bodies of **stacked flat slabs** with visible gaps, lichen and moss in the cracks.
  - The larger ones have a standing-stone head carved with **cup-and-ring marks** that glow faintly lichen-yellow at night.
  - They move by grinding and clacking, slab by slab.
- **Never:** boulder-throwing, a rounded "rock man" body, glowing crystal cores (the WC3 golem read; §10.2).
- **Palette (Greenvale):** drystone #7D766A and #5E574E (the biome rock), lichen #A8B04E, moss #4F7A2E, night glyph glow #E8E29A.
  - **Retints:** Frostmarch "rime cairns" are glazed blue-grey granite with icicles. Sunscar "sand cairns" are banded sandstone.
- **Tags:** `construct`, **Earthbound** (cannot be knocked back or pulled). Heavy armour, so Arcane damage (casters) is the natural answer.
- **Production:** bpy procedural. Bevelled slab primitives are grouped per body part and parented to bones, animated rigidly with no skinning.
  One AI-painted stone texture per tileset. **No 3D credits.**
- **Sound:** grinding stone, slab clacks, a deep hum for Ley Pulse.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_cairn_cairnling` | Cairnling | 3 | 520 | – | 3 Heavy | Blade | 12–16 | 1.8 | melee 0.8 | 3.3 | Settle, Earthbound | **[SLICE]** |
| `creep_cairn_drystone_walker` | Drystone Walker | 5 | 960 | – | 4 Heavy | Blade | 25–31 | 2.0 | melee 1.1 | 3.4 | Rockfall Blow, Earthbound | **[SLICE]** |
| `creep_cairn_menhir_elder` | Menhir Elder | 7 | 1350 | 200 | 5 Heavy | Pure | 36–44 | 2.2 | melee 1.2 | 3.2 | Hardy, Old Ward, Ley Pulse, Earthbound | **[SLICE]** |
| `creep_cairn_dolmen_colossus` | Dolmen Colossus | 9 | 2100 | – | 6 Heavy | Pure | 52–64 | 2.4 | melee 1.5 | 3.0 | Hardy, Capstone Slam, Moss Regrowth, Earthbound | *later* |

| Ability | Creep | Kind | Numbers |
|---|---|---|---|
| **Settle** | Cairnling | Passive | After 2 s without moving: +3 armour until it moves |
| **Rockfall Blow** | Drystone Walker | Passive | Every 4th attack **stuns 1.0 s** (heroes 0.5 s) |
| **Old Ward** | Menhir Elder | Aura, 8 m | Other allied creeps take **−20 % Spell damage** |
| **Ley Pulse** | Menhir Elder | No target, 4 m | **90 Spell damage** and slow 30 % for 3 s. 75 mana, cooldown 14 s |
| **Capstone Slam** | Dolmen Colossus | No target, 4 m | **150 Spell damage, stun 1.5 s** (heroes 0.75 s). Cooldown 15 s |
| **Moss Regrowth** | Dolmen Colossus | Passive | +8 HP/s after 5 s without taking damage |
| **Earthbound** | All Cairnwakes | Passive | Immune to knockback and pull effects |

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

### 2.2 Frostmarch (winter highlands) *(later)*

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
| `creep_whiteout_flurry` | Flurry | 2 | 240 | 100 | 0 Light | Arcane | 10–12 | 1.7 | 6.0 | 4.4 (float) | Chill Touch |
| `creep_whiteout_squall` | Squall | 4 | 480 | 150 | 1 Light | Arcane | 17–21 | 1.8 | 6.0 | 4.6 | Gust |
| `creep_whiteout_whiteout` | Whiteout | 6 | 720 | 250 | 2 Light | Arcane | 24–29 | 1.9 | 6.5 | 4.4 | Hardy, Snowblind, Rime Coat |
| `creep_whiteout_polar_gale` | Polar Gale | 8 | 1500 | 300 | 3 Light | Pure | 40–50 | 1.9 | 6.5 | 4.4 | Hardy, Icefield |

| Ability | Numbers |
|---|---|
| **Chill Touch** (Flurry) | Attacks slow movement 10 % for 2 s |
| **Gust** (Squall) | Unit target 7 m: 50 Spell damage, **knockback 3 m**, interrupts channels. 60 mana, cooldown 12 s |
| **Snowblind** (Whiteout) | Point 8 m, radius 4 m, 6 s: enemies inside have **4 m sight** and a **25 % miss chance**. 90 mana, cooldown 18 s |
| **Rime Coat** (Whiteout) | An allied creep is encased in ice for 3 s: invulnerable and stunned, healing 8 % of max HP/s. 75 mana, cooldown 20 s. Used on a creep below 35 % HP |
| **Icefield** (Polar Gale) | Point 9 m, radius 6 m, 8 s: enemies move 35 % slower, turn at half rate and take 15 Spell damage/s. 125 mana, cooldown 20 s |

#### F3. Shagbull Herd *(later)*

- **Concept:** wild, shaggy highland cattle-oxen that winter in the passes. Mostly placid; deeply protective of calves.
- **Look:**
  - Low, wide, curtain-of-hair bodies with sweeping downward horns and frosted fringes.
  - Snow caked on their backs.
- **Never:** a drum-backed grey beast (the WC3 beast-of-burden read) or a tusked mammoth.
- **Palette:** russet shag #8A5A3A, frost tips #DCE4EA, horn ivory #D8CDB0, nose black #2A2224.
- **Production:** 1 AI quadruped mesh. Quadrupeds rig poorly, so the fallback is a procedural four-leg sway plus rigid legs.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_shag_calf` | Shag Calf | 2 | 380 | – | 1 Medium | Blade | 11–14 | 1.6 | melee 0.8 | 4.2 | — |
| `creep_shag_bull` | Shagbull | 4 | 720 | – | 2 Heavy | Blade | 20–25 | 1.8 | melee 1.0 | 4.2 | Horn Toss |
| `creep_shag_herd_bull` | Herd-Bull | 6 | 1050 | – | 3 Heavy | Blade | 30–37 | 2.0 | melee 1.1 | 4.4 | Hardy, Stampede |
| `creep_shag_grandsire` | Grandsire | 8 | 1700 | – | 4 Heavy | Pure | 44–54 | 2.0 | melee 1.2 | 4.0 | Hardy, Herd Wall, Bellowing Charge |

| Ability | Numbers |
|---|---|
| **Horn Toss** (Shagbull) | Every 5th attack tosses the target: airborne 1 s (stunned) |
| **Stampede** (Herd-Bull) | Charges along a 10 m line: 80 Spell damage and 2 m knockback to every enemy in the path. Cooldown 15 s |
| **Herd Wall** (Grandsire) | Aura 6 m: allied creeps take 25 % less damage |
| **Bellowing Charge** (Grandsire) | As Stampede, 12 m: 120 Spell damage, knockback 2 m and **stun 1 s** (heroes 0.5 s). Cooldown 16 s |

---

### 2.3 Sunscar Steppe (savanna badlands) *(later)*

Mood (visual §7.2): terracotta earth, bleached grass, sky-blue contrast, salt flats. This is where the Tormai Herd Road crosses the Salt Lakes (`clans.md` §1.3).

#### S1. Moundbuilders: termite masons *(later)*

- **Concept:** upright, pale termite-folk who are **master clay masons**. Their tall, fluted mound-towers are the most beautiful buildings on the steppe,
  and they defend them as fiercely as any guild defends its hall.
- **Look:**
  - Cream carapace, oversized mandibled heads, four-fingered hands with **plaster trowels and spades**.
  - Wide reed sun-hats on the masons.
- **Never:** a purple-black chitin swarm, spider legs, sand-burrowing ambushers or a giant hive god. The look is craftsfolk,
  not a bug horde (squint risks in §10.2).
- **Palette:** carapace cream #E6D8B8, clay red #B0603A, reed straw #C9A86A, mandible umber #5A3A28.
- **Production:** 1–2 AI biped meshes (mason body; champion body).

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_mound_mason` | Mound Mason | 1 | 220 | – | 1 Medium | Blade | 7–9 | 1.5 | melee 0.6 | 4.0 | Clay Plaster |
| `creep_mound_etch_spitter` | Etch-Spitter | 2 | 260 | – | 0 Medium | Pierce | 10–13 | 1.8 | 6.0 | 4.0 | Etch |
| `creep_mound_mandible_guard` | Mandible Guard | 3 | 520 | – | 2 Heavy | Blade | 15–19 | 1.6 | melee 0.8 | 4.0 | Lockjaw |
| `creep_mound_drummer` | Mound Drummer | 5 | 600 | 250 | 1 Unarmored | Arcane | 18–22 | 1.9 | 6.5 | 4.0 | Clay Rhythm, Call the Mound |
| `creep_mound_champion` | Mound-Mother's Champion | 8 | 1750 | – | 5 Heavy | Pure | 42–52 | 1.8 | melee 1.1 | 4.0 | Hardy, Shield the Mound, Swarm Rise |

| Ability | Numbers |
|---|---|
| **Clay Plaster** (Mason) | Unit target, an ally within 5 m: +3 armour for 10 s. Cooldown 15 s |
| **Etch** (Etch-Spitter) | Each hit: −1 armour for 6 s, stacking to −3 |
| **Lockjaw** (Mandible Guard) | Grabs its attack target for 1.5 s: both are rooted and the target cannot attack. Cooldown 14 s |
| **Clay Rhythm** (Drummer) | Aura 8 m: allied Moundbuilders attack 20 % faster |
| **Call the Mound** (Drummer) | 2 Mound Masons (summons, 30 s). 90 mana, cooldown 30 s. Used on aggro |
| **Shield the Mound** (Champion) | No target, 4 m: enemy units must attack him for 3 s (taunt). Cooldown 16 s |
| **Swarm Rise** (Champion) | Once, at 50 % HP: 4 Mound Masons burst out of the ground around him (summons, 30 s) |

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
- **Carapace:** −25 % damage from Pierce, for every Rollback.

| id | Name | Lvl | HP | Mana | Armour | Attack | Damage | CD | Range | Speed | Abilities |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `creep_roller_dung` | Dung Roller | 2 | 420 | – | 2 Heavy | Blade | 11–14 | 1.7 | melee 0.8 | 3.8 | Carapace |
| `creep_roller_boulder` | Boulder Roller | 4 | 700 | – | 3 Heavy | Blade | 20–25 | 1.8 | melee 0.9 | 3.8 | Carapace, Ball Roll |
| `creep_roller_horned` | Horned Roller | 6 | 1000 | – | 4 Heavy | Blade | 30–36 | 1.9 | melee 1.0 | 4.0 | Hardy, Carapace, Horn Lift |
| `creep_roller_matriarch` | Brass-Shell Matriarch | 8 | 1700 | 200 | 5 Heavy | Pure | 44–52 | 2.0 | melee 1.2 | 3.8 | Hardy, Carapace, Shell-Flash |

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
or `guard` (also attacks buildings started within 12 m; used at expansion gold mines).

### 3.3 Greenvale templates

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode | Props and placement | Slice |
|---|---|---|---|---|---|---|---|---|---|---|
| `camp_gv_charcoal_clamp` | Green | Cutpurse ×3, Smoker | 5 | 115 | 36 | B: L1 power-up | Night | camp | Smoking clamp, lean-to, cordwood. Near each start, beside the natural path | **[SLICE]** ×2 |
| `camp_gv_turnip_patch` | Green | Strawling ×3, Fieldkeeper | 6 | 135 | 40 | B: L1 power-up | **Day** | camp | Turnip rows, poles, a crow-picked haystack. The other side of each start | **[SLICE]** ×2 |
| `camp_gv_colliers_hut` | Green | Collier, Smoker ×2, Cutpurse | 8 | 165 | 48 | B: L2 any | Night | camp | A sooty cottage. Side lanes | *later* |
| `camp_gv_toad_pond` | Green | Mudgulper, Peeper ×4 | 7 | 160 | 48 | B: L1 power-up | Night | camp | Reed pond | *later* |
| `camp_gv_smugglers_den` | **Amber** | Kiln-Master, Collier, Smoker, Cutpurse | 11 | 240 | 60 | A: L1 power-up; B: L2 permanent | Night | camp | Ringed around the central **Weighstall** at 3–5 m, so any approach is acquired | **[SLICE]** ×1 |
| `camp_gv_crow_field` | **Amber** | Crowcaller, Fieldkeeper ×2, Strawling ×2 | 12 | 255 | 68 | A: L1 power-up; B: L2 permanent | **Day** | camp | Scarecrow field around the **Hale Spring**: free to use by day, guarded by night | **[SLICE]** ×1 |
| `camp_gv_drystone_fold` | **Amber** | Drystone Walker, Cairnling ×3 | 14 | 295 | 72 | A: L1 power-up; B: L3 permanent | Never | **guard** | Broken sheep-fold walls around each **expansion** Gold Seam | **[SLICE]** ×2 |
| `camp_gv_wicker_field` | Amber | Wicker Brute, Crowcaller, Fieldkeeper ×2, Strawling ×2 | 17 | 370 | 92 | A: L1 power-up; B: L3 permanent or charged | Day | camp | Upgrade of Crow Field when the Wicker Brute exists | [SLICE+] |
| `camp_gv_bellow_marsh` | Amber | Bellower ×2, Mudgulper, Peeper ×2 | 15 | 340 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp | Marsh | *later* |
| `camp_gv_standing_ring` | **Red** | Menhir Elder, Drystone Walker ×2, Cairnling | 20 | 480 | 96 | A: L2 any; B: L4 permanent | Never | camp | A ring of standing stones in a contested centre-flank pocket | **[SLICE]** ×1 |
| `camp_gv_grandmothers_bog` | Red | Grandmother Toad, Bellower ×2, Peeper ×4 | 21 | 520 | 112 | A: L2 any; B: L4 permanent | Night | camp | Deep bog | *later* |
| `camp_gv_earls_court` | Red | Earl of Ash, Kiln-Master, Collier ×2, Smoker ×2 | 22 | 505 | 112 | A: L2 any; B: L5 permanent or charged | Night | camp | Big clamp and a charcoal-burners' hall | *later* |
| `camp_gv_dolmen_hill` | Red | Dolmen Colossus, Menhir Elder, Drystone Walker ×2 | 26 | 705 | 120 | A: L2 power-up; B: L6 permanent or charged | Never | camp | A dolmen on a hilltop | *later* |
| `camp_gv_harvest_court` | Red (boss) | Turnip King, Wicker Brute ×3, Crowcaller ×2 | 31 | 750 | 148 | A: L3 any; B: **fixed** Hollow Lantern or Turnip King's Sickle (seeded) | Day | camp | A harvest-home barn with a giant turnip lantern | *later* |

### 3.4 Frostmarch templates *(later)*

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode |
|---|---|---|---|---|---|---|---|---|
| `camp_fm_stoat_warren` | Green | Ermine Kit ×3, Snowslinger ×2 | 7 | 155 | 48 | B: L1 power-up | Night | camp |
| `camp_fm_calf_drift` | Green | Shagbull, Shag Calf ×2 | 8 | 165 | 44 | B: L2 any | Night | camp |
| `camp_fm_squall_line` | Amber | Squall ×2, Flurry ×3 | 14 | 290 | 76 | A: L1 power-up; B: L3 permanent or charged | Never | guard (expansion) |
| `camp_fm_shag_herd` | Amber | Herd-Bull, Shagbull ×2, Shag Calf | 16 | 360 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp |
| `camp_fm_matriarchs_den` | Red | Ermine Matriarch, Rime-Biter ×3, Snowslinger ×2 | 22 | 485 | 112 | A: L2 any; B: L5 permanent or charged | Night | camp |
| `camp_fm_whiteout_peak` | Red | Polar Gale, Whiteout ×2, Squall, Flurry | 26 | 660 | 124 | A: L2 power-up; B: L6 permanent or charged | Never | camp |

### 3.5 Sunscar templates *(later)*

| id | Colour | Composition | Total | XP | Gold | Drops | Sleeps | Mode |
|---|---|---|---|---|---|---|---|---|
| `camp_ss_mound_gate` | Green | Mandible Guard, Etch-Spitter, Mound Mason ×2 | 7 | 150 | 44 | B: L1 power-up | Night | camp |
| `camp_ss_dung_trail` | Green | Dung Roller ×3 | 6 | 120 | 36 | B: L1 power-up | Day | camp |
| `camp_ss_salt_wagon` | Amber | Salt Seer, Brine Drover, Salt Husk ×2 | 13 | 280 | 68 | A: L1 power-up; B: L2 permanent | Never | guard (expansion) |
| `camp_ss_boulder_run` | Amber | Horned Roller, Boulder Roller ×2 | 14 | 320 | 68 | A: L1 power-up; B: L3 permanent or charged | Day | camp |
| `camp_ss_drum_mound` | Amber | Mound Drummer, Mandible Guard ×2, Etch-Spitter ×2 | 15 | 315 | 80 | A: L1 power-up; B: L3 permanent or charged | Night | camp |
| `camp_ss_dead_caravan` | Red | Caravan-Master, Salt Seer, Brine Drover ×2, Salt Husk | 23 | 560 | 112 | A: L2 any; B: L5 permanent or charged | Never | camp |
| `camp_ss_mother_mound` | Red | Mound-Mother's Champion, Mound Drummer, Mandible Guard ×3, Etch-Spitter | 24 | 570 | 120 | A: L2 any; B: L5 permanent or charged | Night | camp |

### 3.6 Slice map: the neutral layout (Greenvale, 96 × 96 tiles = 192 m)

Two starts in opposite corners, rotationally symmetric. Written from rules (ip-safety §2.6), not from any existing map.
Distances are hall-centre to camp-centre.

| Neutral | Count | Where | Why |
|---|---|---|---|
| Gold Seam (main, 12,000) | 2 | At each start, hall edge to seam edge about 4 m | Global economy rule |
| Gold Seam (expansion, 8,000) + **Drystone Fold** (amber 14, guard mode) | 2 | One natural expansion per player, 55–65 m from the main, on lower ground | Never-sleep guards: the expansion costs a real fight at any hour |
| **Charcoal Clamp** (green 5) | 2 | 28–35 m from each main, beside the natural path | First creep at about 2:00 (both faction build orders) |
| **Turnip Patch** (green 6) | 2 | 35–45 m from each main, the other side | Second creep. It sleeps by day, so a passing army is safe until dusk at 3:20 |
| **Weighstall** + **Smugglers' Den** (amber 11) | 1 | Map centre | Potions and recall are contested; at night the Den sleeps, so a sneaky purchase is possible but wakes them |
| **Hale Spring** + **Crow Field** (amber 12, night-active) | 1 | On the side lane that is *not* the shortest attack path | Free healing by day, a guarded spring by night |
| **Standing Ring** (red 20) | 1 | Opposite flank to the spring, equidistant from both starts | The big prize (L2 + L4); never sleeps, so it is never a free kill |
| Critters | 10–14 | Meadows (hares), ponds and roads (geese), fireflies by water at night | Ambience |
| [SLICE+] **Beacon Cairn** | 2 | On the two high ground knolls overlooking the centre | Vision fights |
| [SLICE+] **Wayfarers' Inn** | 1 | Unguarded, beside the centre road, about 12 m from the Weighstall | Never guarded (WC3 convention) |

**Totals on the slice map:** 9 camps (4 green, 4 amber, 1 red), 93 total creep levels, **2,065 raw XP** and about **520 gold** in bounty.

**XP check against the faction build orders** (`kingdom.md` §10 and `clans.md` §10 both aim for hero level 3 by about 5:30):

| Step | Raw XP | Factor | Hero XP | Level |
|---|---|---|---|---|
| Charcoal Clamp at level 1 | 115 | 80 % | 92 | 1 |
| Turnip Patch at level 1 | 135 | 80 % | 200 | **2** |
| Own Drystone Fold at level 2 | 295 | 70 % | 406 | 2 |
| Crow Field (or about 3 enemy unit kills at full XP) | 255 | 70 % | 584 | **3** |

---

## 4. Items

### 4.1 Rules

| Rule | Value |
|---|---|
| **Classes** | **Purchasable** (shop stock; never drops) · **Power-up** (used the moment it is picked up) · **Permanent** (passive while carried) · **Charged** (limited uses, then gone) · **Artifact** (level 7–8; permanent, some with an active) |
| **Levels** | 1–8. Level sets the drop band (§3.1) and the sell value |
| **Who carries** | Heroes only, **6 slots**. Exception: **food power-ups** (Wild Strawberries) can be picked up by any unit, and act at once |
| **Hotkeys** | Numpad 7 / 8 / 4 / 5 / 1 / 2 (the classic grid) and Alt+1–6 (for keyboards without a numpad). Right-click an item with a hero to pick it up; drag it onto an allied hero within 2 m to give it; drag it onto the ground to drop it |
| **Death** | A dying hero keeps its items (revives with them) |
| **Charges** | Identical purchasable consumables merge into one slot, up to 2 × their base charges (tuning flag) |
| **Stacking** | Move-speed items do not stack with each other; evasion from items does not stack (highest applies); the same aura item twice gives one aura |
| **Shared cooldowns** | Item actives share a cooldown per item id, per hero |
| **Selling** | At the Weighstall or Lucky Barrow, for **50 % of value** (charged items: × remaining / base charges). Taxed by upkeep. Power-ups cannot be sold (they are never carried) |
| **Ground look** | A twine-tied oilcloth bundle with a wax seal (§1.8); power-ups show as their own small props |
| **Text** | Every name and tooltip is written from scratch (ip-safety §2.2). No WC3 item name or tooltip wording |

**Slice effect scripts** (12, all simple): `stat_bonus`, `heal_instant`, `mana_instant`, `heal_area_over_time`, `recall_to_hall`,
`place_ward`, `reveal_invisible_area`, `self_invisibility`, `vision_flare`, `grant_xp`, `grant_gold`, `heal_area_on_pickup`.

### 4.2 Purchasable (sold at the Weighstall; stock is per player)

| id | Name | Lvl | Charges | Effect | Price | Stock / restock | From | Slice |
|---|---|---|---|---|---|---|---|---|
| `item_rosehip_draught` | Rosehip Draught | 1 | 1 | Restores **260 HP** at once | 150 g | 3 / 45 s | 0:00 | **[SLICE]** |
| `item_bluebell_cordial` | Bluebell Cordial | 1 | 1 | Restores **160 mana** at once | 110 g | 3 / 45 s | 0:00 | **[SLICE]** |
| `item_homing_pigeon` | Homing Pigeon | 1 | 1 | Releases a pigeon. After a **3 s** channel, the hero and up to 11 of your non-structure units within 6 m vanish in a puff of feathers and reappear at your nearest town hall. Damage does not interrupt it; stuns do | 325 g | 2 / 120 s | 0:00 | **[SLICE]** |
| `item_snoop_peg` | Snoop Peg | 1 | 2 | Hammers in an invisible peg within 5 m: **13 m vision for 240 s** (25 HP). It sees no invisible units | 80 g | 2 / 60 s | 0:00 | **[SLICE]** |
| `item_flour_bomb` | Flour Bomb | 1 | 2 | Bursts at a point within 8 m: invisible units within **9 m** are revealed, and stay revealed for **12 s** wherever they go (they are dusted) | 60 g | 2 / 60 s | 0:00 | **[SLICE]** (counters Long-Braid's Dust Veil) |
| `item_picnic_hamper` | Picnic Hamper | 2 | 1 | Your and allied non-structure units within **7 m** restore **180 HP over 6 s** | 200 g | 2 / 90 s | 3:00 | **[SLICE]** |
| `item_wanderers_hobnails` | Wanderer's Hobnails | 2 | — (permanent) | **+0.7 m/s** move speed | 200 g | 1 / 120 s | 4:00 | **[SLICE]** |
| `item_coilspring_heels` | Coilspring Heels | 4 | 3 | Leap to a point within **9 m** (over units, not up cliffs). Cooldown 15 s | 325 g | 1 / 180 s | 8:00 | *later* |

### 4.3 Power-ups (drop only; used on pickup)

| id | Name | Lvl | Effect | Picked up by | Ground prop | Slice |
|---|---|---|---|---|---|---|
| `item_chapbook_grit` | Chapbook of Grit | 1 | **+1 STR**, permanently | Heroes | A dog-eared red pamphlet | **[SLICE]** |
| `item_chapbook_knacks` | Chapbook of Knacks | 1 | **+1 AGI**, permanently | Heroes | A green pamphlet | **[SLICE]** |
| `item_chapbook_wits` | Chapbook of Wits | 1 | **+1 INT**, permanently | Heroes | A blue pamphlet | **[SLICE]** |
| `item_wild_strawberries` | Wild Strawberries | 1 | Your non-structure units within 6 m restore **200 HP** | **Any unit** | A leaf of berries | **[SLICE]** |
| `item_dropped_purse` | Dropped Purse | 1 | **+75 gold** to the owner (taxed by upkeep) | Heroes | A drawstring purse | **[SLICE]** |
| `item_hedge_almanac` | Hedge Almanac | 2 | **+1 to all three attributes**, permanently | Heroes | A thick almanac tied with string | **[SLICE]** |
| `item_veterans_diary` | Veteran's Diary | 2 | **+100 XP**, never reduced by the creep XP factor (respects the level cap) | Heroes | A battered diary | **[SLICE]** |

### 4.4 Permanent (drop only; Lucky Barrow may stock them)

| id | Name | Lvl | Effect | Value | Slice |
|---|---|---|---|---|---|
| `item_plowmans_belt` | Plowman's Belt | 2 | +3 STR | 300 | **[SLICE]** |
| `item_hares_foot_charm` | Hare's-Foot Charm | 2 | +3 AGI | 300 | **[SLICE]** |
| `item_inkhorn_pendant` | Inkhorn Pendant | 2 | +3 INT | 300 | **[SLICE]** |
| `item_whetstone_fob` | Whetstone Fob | 2 | +5 attack damage | 300 | **[SLICE]** |
| `item_tin_gorget` | Tin Gorget | 2 | +2 armour | 300 | **[SLICE]** |
| `item_dewdrop_locket` | Dewdrop Locket | 2 | +0.6 mana/s | 300 | **[SLICE]** |
| `item_moss_amulet` | Moss Amulet | 3 | +2.5 HP/s | 450 | **[SLICE]** |
| `item_four_leaf_brooch` | Four-Leaf Brooch | 3 | +2 STR, +2 AGI, +2 INT | 450 | **[SLICE]** |
| `item_woodpecker_gloves` | Woodpecker Gloves | 3 | +15 % attack speed | 450 | **[SLICE]** |
| `item_millstone_girdle` | Millstone Girdle | 4 | +6 STR | 650 | **[SLICE]** |
| `item_fox_fur_mantle` | Fox-Fur Mantle | 4 | +6 AGI | 650 | **[SLICE]** |
| `item_lensgrinders_monocle` | Lensgrinder's Monocle | 4 | +6 INT | 650 | **[SLICE]** |
| `item_ironwood_knuckles` | Ironwood Knuckles | 4 | +10 attack damage | 650 | **[SLICE]** |
| `item_thistledown_cloak` | Thistledown Cloak | 4 | 15 % chance to evade attacks | 650 | *later* |
| `item_marching_fife` | Marching Fife | 5 | Aura 9 m: allied units deal **+12 %** attack damage | 850 | *later* |
| `item_shepherds_bell` | Shepherd's Bell | 5 | Aura 9 m: allied units **+2 armour** and +6 % move speed | 850 | *later* |
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
| `item_dolmen_crown` | Dolmen Crown | 7 | +5 STR, +5 AGI, +5 INT, +1 armour | 1400 | *later* |
| `item_hollow_lantern` | Hollow Lantern | 7 | **True sight 9 m.** The hero's night sight equals its day sight, and it moves +0.5 m/s at night | 1400 | *later* |
| `item_turnip_kings_sickle` | Turnip King's Sickle | 7 | +15 attack damage; melee attacks **cleave 30 %** to enemies within 1.5 m in front | 1400 | *later* |
| `item_heart_of_the_hill` | Heart of the Hill | 8 | +450 HP, +4 HP/s, +3 armour | 1800 | *later* |
| `item_hill_mist_shawl` | Hill-Mist Shawl | 8 | +4 AGI. Active (90 s cooldown): your units within 9 m become **invisible for 10 s** (0.75 s fade; attacking or casting breaks it per unit) | 1800 | *later* |

**Count:** 8 purchasable + 7 power-up + 20 permanent + 7 charged + 5 artifact = **47 items** (29 in the slice).
The brief asked for about 40. The extra 7 make sure every class-and-level cell used by a drop band has at least two candidates, so a drop is never fully predictable.

### 4.7 Drop pools (class × level)

| Level | Power-up | Permanent | Charged | Artifact |
|---|---|---|---|---|
| 1 | Chapbook of Grit, Chapbook of Knacks, Chapbook of Wits, Wild Strawberries, Dropped Purse | — | — | — |
| 2 | Hedge Almanac, Veteran's Diary | Plowman's Belt, Hare's-Foot Charm, Inkhorn Pendant, Whetstone Fob, Tin Gorget, Dewdrop Locket | Smoke Pellets, Firefly Jar | — |
| 3 | — | Moss Amulet, Four-Leaf Brooch, Woodpecker Gloves | Straw Double, Salt Circle | — |
| 4 | — | Millstone Girdle, Fox-Fur Mantle, Lensgrinder's Monocle, Ironwood Knuckles, Thistledown Cloak | — | — |
| 5 | — | Marching Fife, Shepherd's Bell, Nettle-Sting Oil, Ravening Torc | Free Company Horn | — |
| 6 | — | Hedge-Witch's Knot, Lodestone Ring | Cat's Ninth Life, Bottled Thunderhead | — |
| 7 | — | — | — | Dolmen Crown, Hollow Lantern, Turnip King's Sickle |
| 8 | — | — | — | Heart of the Hill, Hill-Mist Shawl |

- "L2 any" draws from all 10 level-2 entries. "L3 permanent or charged" draws from the 5 level-3 entries.
- In the slice, pools contain only **[SLICE]** items. So L3 draws from the 3 permanents, and L4 from 4 permanents (no Thistledown Cloak).
- Each pool entry has a `weight` (default 1). Chapbooks have weight 1 each, so a "L1 power-up" is a chapbook 60 % of the time.

---

## 5. Neutral buildings

### 5.1 Overview

All neutral buildings belong to `NEUTRAL_PASSIVE`, are **invulnerable**, grant no vision and are used by having one of your units within
**4 m of the building's edge** (the **patron range**; WC3's is tighter, see §11). Items go to your selected hero if it is in range, otherwise to
your nearest hero in range. A purchase or hire wakes sleeping creeps within 10 m (§1.5).

| id | Name | Function | Footprint (cells) | Guarded by | Slice |
|---|---|---|---|---|---|
| `gold_mine` (display **Gold Seam**) | Gold Seam | Gold source | 8×8 | Expansions: a guard-mode amber camp | **[SLICE]** ×4 |
| `neutral_weighstall` | Weighstall | Merchant: consumables, recall, wards, reveal, boots; buys items | 8×8 | Amber 9–15 | **[SLICE]** ×1 |
| `neutral_lucky_barrow` | Lucky Barrow | Rotating stronger items | 4×4 | Amber 10–15 | *later* |
| `neutral_wayfarers_inn` | Wayfarers' Inn | Neutral heroes; instant revive | 10×10 | **Never guarded** | [SLICE+] (Rat-Piper only) |
| `neutral_free_company_camp` | Free Company Camp | Hire local creep types | 10×10 | Amber 9–15 | [SLICE+] |
| `neutral_hale_spring` | Hale Spring | Area health regeneration | 6×6 | Amber 10–14 | **[SLICE]** ×1 |
| `neutral_glimmer_font` | Glimmer Font | Area mana regeneration | 6×6 | Amber 10–14 | [SLICE+] |
| `neutral_contraption_barn` | Contraption Barn | Lumber machine, balloon transport, ram, area reveal | 10×10 | Amber 12–15 | *later* |
| `neutral_twin_milestones` | Twin Milestones | Paired teleport | 2×2 each | Unguarded | *later* |
| `neutral_beacon_cairn` | Beacon Cairn | Capturable vision tower | 4×4 | Unguarded | [SLICE+] ×2 |

### 5.2 Gold Seam (gold mine) [SLICE]

| Rule | Value |
|---|---|
| Data id | `gold_mine` (kept for the code in `architecture.md`); display name **Gold Seam** |
| Gold | **12,000** (main), **8,000** (expansion). Low-gold warning at **1,500**: minimap ping plus the faction advisor line |
| Mining | 10 gold per trip; one worker inside at a time for **1.0 s**; about 5 workers saturate it at the standard hall gap (global rule) |
| Footprint | 8×8 cells (4×4 m), blocks pathing |
| Look | A **timbered adit** cut into a short cliff seam: gold-veined rock face, an ore-cart stub on rails, a hand winch, two lanterns lit at night. A worker vanishes into the dark mouth for its 1 s |
| Empty | The props crack, the adit collapses in a puff of dust, and the footprint becomes walkable rubble (a ground decal with small non-blocking rocks) |
| Minimap | Our faceted-nugget glyph in pale gold, not the WC3 icon |
| Faction hooks | Later factions (`sylvan`, `deathless`) may change how they claim a seam; that is their business, not this doc's |
| Production | bpy kitbash (rock seam mesh, timber frame, lanterns) with AI-painted textures |

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
  - Their joke is *fussy fairness*: receipts, re-weighing, polite outrage at a light coin.
  - **Never** the greedy-merchant caricature: no hoarded gold piles, no hooked noses, no swindling, no explosives gags, no green skin, no big ears.
- **Palette:** scales #7A5A3A with #B08A5A edges, brass #B8913A, awning cream #E8DCC0 and sage #7E9A6E.
- **In the slice** the shopkeeper is a **curled-up Rundling ball** dozing on the counter. It is a bpy prop that "breathes" with a scale bob and uncurls a nose when you buy.
  A full Rundling shopkeeper model is [SLICE+] (one AI mesh), and it is reused for the Weighmaster hero (§5.6) and the Contraption Barn.

**Shopkeeper lines** (original; one voice, Krea TTS):

| Category | Lines |
|---|---|
| Select | "Fair weight, fair price." · "Everything weighed twice. Once for you, once for me." · "Wipe your boots, please. The scales notice." |
| Buy | "Weighed and wrapped!" · "Receipt's in the bag." |
| Sell | "Hm. Light. Half it is." |
| Can't afford | "The scales say no." |
| Annoyed (4 clicks in 3 s) | "Tap the counter once more and I'm adding a tapping fee." · "I'm curling up. I am curling up!" |

### 5.4 Lucky Barrow (rotating stock) *(later)*

- **Look:** a Rundling pedlar's handcart with a tall stack of drawers and a wind-up chime that plays when the stock changes.
- **Stock:** every **120 s** it rerolls 4 slots: 1 L3 permanent, 1 L3–L4 charged, 1 L4 permanent, and 1 L5 permanent from 10:00.
  Price is value × 1.25, with 1 of each in stock. A visible countdown sits over the cart.
- It buys items at 50 % like the Weighstall.

### 5.5 Wayfarers' Inn (neutral heroes) [SLICE+]

- **Look:**
  - A two-storey **coaching inn**: a stable arch, a horse trough, smoke from two chimneys.
  - A great **hanging lantern sign**, named per map (the Greenvale inn is *The Muddy Lantern*).
  - It is never guarded, so it is a calm place in a hostile map.
- **Hire** a neutral hero (§5.6):
  - **425 gold / 135 lumber**, 5 food. The lumber premium over a faction hero (100) is a deliberate WC3 echo.
  - It needs a free hero slot (T1: 1, T2: 2, T3: 3). **The free first-hero token works here.**
  - The hire is instant. The hero appears at the inn door with 1 skill point.
  - **Each neutral hero can be hired once per match, by one player.** It goes grey for everyone else.
- **Instant revive** (any of your dead heroes, faction or neutral):
  - Gold = 425 × (0.6 + 0.12 × level), at most 800. Lumber = 50 + 10 × level, at most 150.
  - The hero returns **at once**, at the inn, with **50 % HP and 0 mana**. Compare the altar: at most 550 gold and up to 110 s, at full HP.
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
| R | **The Long Tune** (ultimate, channel up to 6 s, radius 9 m) | — | 175 | 160 s | He plays. Enemy **non-hero** units in the radius at the start are **enthralled**: they follow him (at most 3.0 m/s) and cannot attack or cast; damage does not break it. Enemy heroes in the radius are slowed 40 % instead. He can walk at 2.4 m/s while playing (lead them into your towers). Level 6+ units are enthralled for 3 s only. Stuns, silences or his death end it |

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
| E | **Lichen Hide** (passive) | −4 / −7 / −10 per hit; +1 / +2 / +3 HP/s | — | — | Reduces each incoming **attack** by a flat amount (minimum 1; spells unaffected) and adds HP regeneration |
| R | **Sleep of Stones** (ultimate, self, 7 m) | — | 150 | 140 s | He and every allied non-structure unit within 7 m turn to stone for **4 s**: invulnerable, unable to act or be moved. When it ends he releases a ring shockwave: **150 Spell damage** and 40 % slow for 3 s to enemies within 7 m. Allies cannot opt out (the skill is in the timing) |

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
| Q | **Tip the Scales** (enemy unit, 8 m) | 70 / 115 / 160 | 85 | 8 s | Deals Spell damage to the enemy, then **heals the most-injured allied non-structure unit within 8 m of her** by the damage actually dealt |
| W | **Hired Pikes** (summon) | 1 / 2 / 2 Pikeguards | 80 mana **+ 25 gold** | 25 s | Summons Rundling Pikeguards for **40 s** (stats in §5.6.4). The **gold cost** is the gimmick: can't afford it, can't cast it |
| E | **Strongbox Shell** (ally unit, 8 m) | 120 / 200 / 280 | 70 | 10 s | Wraps the ally in a brass-banded shell that **absorbs damage for 12 s**. When the shell breaks it bursts, knocking adjacent enemies back 1.5 m |
| R | **The Great Scales** (ultimate, point within 10 m, radius 8 m) | — | 175 | 150 s | A translucent bronze balance hangs over the area for **8 s**. Enemy units inside deal **−35 % damage** and your units inside regenerate 8 HP/s. When it ends, each enemy unit takes Spell damage equal to **50 % of the damage it dealt** during the 8 s (at most 300 per unit) |

#### 5.6.7 Kit fidelity audit (policy: at most 2 of 4 abilities may be functional equivalents of the nearest WC3 hero)

| Neutral hero | Nearest WC3 tavern hero (reference) | Functional equivalents (counted strictly) | Original mechanics | Count |
|---|---|---|---|---|
| Rat-Piper | Dark Ranger (AGI ranged) | Sack of Rats (summoned minions); The Long Tune (taking control of enemy units: temporary and mass, instead of permanent and single) | Deadfall Snare (invisible root traps); Ratter's Instinct (execute bonus plus mana on kill) | **2** |
| Old Menhir | Pandaren Brewmaster (STR tank) | Lichen Hide (defensive passive, a flat block instead of evasion) | Barge (knockback into terrain for a stun); Drystone Wall (pathing wall); Sleep of Stones (group stasis plus shockwave) | **1** |
| Weighmaster | Goblin Alchemist (comedic merchant-people hero) | Tip the Scales (has a healing component) | Hired Pikes (summon paid in gold); Strongbox Shell (absorb shield); The Great Scales (damage reduction plus delayed rebound) | **1** |

No neutral hero uses its nearest WC3 hero's ultimate. Names, VFX, numbers and designs are ours.

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
| Greenvale | Wicker Brute | 5 | 320 | 60 | 4 | 1 | 120 s | 8:00 | *later* |
| Frostmarch | Snowslinger | 2 | 150 | 15 | 2 | 2 | 60 s | 2:00 | *later* |
| Frostmarch | Rime-Biter | 4 | 260 | 40 | 3 | 2 | 90 s | 5:00 | *later* |
| Frostmarch | Shagbull | 4 | 250 | 50 | 3 | 1 | 90 s | 5:00 | *later* |
| Frostmarch | Ermine Matriarch | 6 | 360 | 80 | 4 | 1 | 120 s | 10:00 | *later* |
| Sunscar | Etch-Spitter | 2 | 150 | 15 | 2 | 2 | 60 s | 2:00 | *later* |
| Sunscar | Mandible Guard | 3 | 200 | 20 | 3 | 2 | 60 s | 2:00 | *later* |
| Sunscar | Boulder Roller | 4 | 260 | 50 | 3 | 1 | 90 s | 5:00 | *later* |
| Sunscar | Mound Drummer | 5 | 300 | 60 | 3 | 1 | 120 s | 8:00 | *later* |

Pricing rule of thumb: 50–60 gold per level + 40, lumber about 10 per level (more for beasts), food by size. That is about the price of a
faction unit of the same level. The player pays instead in flexibility lost: no faction research, a small stock, and a trip to the camp.

### 5.8 Hale Spring and Glimmer Font (fountains)

| | Hale Spring [SLICE] | Glimmer Font [SLICE+] |
|---|---|---|
| Effect | **+2 % of max HP per second** | **+1.5 % of max mana per second, +0.5 mana/s** |
| Radius | 7.8 m from the centre | 7.8 m |
| Who | Every non-structure unit in range, **any owner, creeps included**, except mechanical units (wagons, carts, balloons) | Every unit with mana in range, any owner |
| Look | A moss-ringed spring pool fed by a hollow-log flume with a tiny turning waterwheel. Warm sparkles rise off the water by day | A stone trough brimming with water that glows soft blue at night, ringed with pale water-lilies |
| Guard | Crow Field (amber 12, night-active): free by day, contested at night | An amber 10–14 camp, usually never-sleep |
| Footprint | 6×6 cells; the pool itself is walkable shallow water | 6×6 cells |

A spring heals but never wakes creeps (passive aura). A unit standing in it shows a soft rising-bubble VFX.

### 5.9 Contraption Barn (lab-equivalent) *(later)*

- **Look:** a big red-brown barn whose roof slides open. Inside are Rundling gadgets: a hot-air balloon tethered to the roof beam, a saw-cart, crates of springs.
- **Rules:** hires and services, gold and lumber, **stock per player**.

| Offer | Kind | Cost | Food | Stock / restock | From | Stats and effect |
|---|---|---|---|---|---|---|
| **Sawcart** | Unit (wheeled) | 275 g / 40 l | 3 | 2 / 120 s | 5:00 | HP 450, 2 Heavy, 3.4 m/s. Fells trees fast: **5 lumber/s**, carries **100** per trip, returns to any of your drop-offs. No attack. Pushed by a Rundling |
| **Lift Balloon** | Unit (flying transport) | 220 g / 60 l | 2 | 1 / 120 s | 6:00 | HP 500, 0 Light, 5.0 m/s, sight 16 / 12 m. Carries **8 food** of ground units; unloading takes 0.5 s per unit. No attack |
| **Ram-Barrow** | Unit (wheeled siege) | 190 g / 70 l | 2 | 2 / 90 s | 6:00 | HP 380, 3 Heavy, 3.6 m/s. **Siege 70–90 vs buildings only**, CD 3.0, melee. Battering Run: the first hit after 2 s of moving deals ×2 |
| **Survey Lantern** | Service | 60 g | — | per-player cooldown 30 s | 0:00 | A paper sky-lantern rises over any point: **reveals a 16 m radius for 10 s** |

### 5.10 Twin Milestones (paired teleport) *(later)*

- **Look:** two worn roadside **milestones**, each carved with a road that runs off its own edge, placed far apart on the map.
- **Use:** right-click a milestone with any ground units. Each unit walks within 1 m, folds into a swirl of **road dust** for 1.0 s
  (interrupted by damage) and unfolds beside the twin. **Per-unit cooldown 5 s.** Heroes and armies both use it; creeps never do.
- **Readability:** both stones show the same coloured road-ribbon, and the minimap draws a faint dotted link between them.

### 5.11 Beacon Cairn (capturable vision tower) [SLICE+]

- **Look:** a tall cairn on a knoll topped by an iron fire-basket. It burns in the capturing player's team colour.
- **Capture:** a ground unit of yours stands within **2.5 m** for **3 s** with no enemy unit within 2.5 m.
- **While lit:**
  - Its owner gets vision of **20 m (day) / 16 m (night)** around it. That vision ignores tree occlusion but not higher cliffs.
  - The flame's team colour is visible to **everyone** on the minimap, so a capture is never secret.
- **Fuel:** it stays lit for **60 s** after your last unit leaves, then gutters out (neutral).
  An enemy **douses** it with the same 3 s uncontested stand, which resets it to neutral (a second 3 s captures it).
- **Why:** an original "high ground watch" landmark. It rewards map presence and gives the slice AI an easy objective.
  WC3's melee neutral buildings include no capturable vision tower, so this one is ours to define.
- **Production:** bpy cairn kit + fire VFX; no 3D credits.

---

## 6. Critters

**Rules (all critters):**
- Owner `NEUTRAL_PASSIVE`, level 0. They give **no XP and no bounty**, never block pathing (radius 0.15 m) and are never auto-acquired.
  Players can attack them with an explicit order.
- They flee from combat within 6 m and from any unit that comes within their **startle radius**. They do not respawn.
- They leave a corpse for the normal decay time, which later factions (for example `deathless`) may use.
- **Density:** about 3 per 16 × 16-tile chunk of open ground; none within 15 m of a start location.
- **Click-spam gag:** after **6 clicks within 3 s**, each critter does its own gag, then cools down for 20 s.
  **Nothing explodes or dies**: an exploding farm animal is a famous Blizzard easter egg, so we never use it.

| id | Name | Tileset | HP | Speed (wander / flee) | Active | Startle radius | Behaviour | Click-spam gag | Slice |
|---|---|---|---|---|---|---|---|---|---|
| `critter_brown_hare` | Brown Hare | Greenvale | 20 | 2.0 / 7.0 | Day (crouches still at night) | 4 m | Grazes in meadows; bolts 8 m when startled | Thumps a hind foot twice, bolts 10 m and freezes flat with ears down | **[SLICE]** |
| `critter_grey_goose` | Grey Goose | Greenvale | 30 | 2.4 / 3.5 | Day | 2 m (it hisses instead of fleeing) | Gaggles of 2–4 on roads and ponds | Honks, flaps, and **nips** the clicking player's nearest unit for 1 damage every 1.5 s for 6 s (never below 1 HP), then struts off | **[SLICE]** |
| `critter_fireflies` | Firefly Drift | Greenvale | — (untargetable) | drifts | Night | — | Soft lights over water and meadow edges; part of the night ambience | — | **[SLICE]** (VFX only) |
| `critter_sparrow_roost` | Sparrow Roost | Greenvale | — (untargetable) | — | Day | 4 m | A roost sits in a tree line. **Flush:** when any player's ground unit comes within 4 m, the flock bursts up for 2.5 s with a wing-flutter sound. The flock is drawn **above the fog in explored areas** (never in black mask), so all players see something moving there. It resettles after 30 s | — | [SLICE+] |
| `critter_hedgehog` | Hedgehog | Greenvale | 15 | 1.4 / 1.4 | Night | 2 m (it curls instead of fleeing) | Snuffles along hedges | Curls into a ball, rolls 2 m and sneezes | *later* |
| `critter_snow_hare` | Snow Hare | Frostmarch | 20 | 2.0 / 7.0 | Day | 4 m | As the Brown Hare, in white | As the Brown Hare | *later* |
| `critter_ptarmigan` | Ptarmigan | Frostmarch | 20 | 2.0 / 4.0 | Day | 3 m | Small flocks in snowfields | Dives head-first into the snow; only its tail sticks out for 4 s | *later* |
| `critter_lemming` | Lemming | Frostmarch | 10 | 3.0 / 3.0 | Day | 3 m | Scurries between rocks | Puffs its cheeks and squeaks furiously at the camera | *later* |
| `critter_meerkat` | Meerkat | Sunscar | 15 | 3.0 / 5.0 | Day | 5 m | Families of 3; one always stands upright on watch | All three pop upright at once and **stare straight at the camera** for 3 s | *later* |
| `critter_guinea_fowl` | Guinea Fowl | Sunscar | 20 | 3.0 / 4.5 | Day | 3 m | Flocks in dry grass | Runs in tight shrieking circles | *later* |

**Production:** bpy low-poly primitives with AI-painted textures. Procedural hop (hare), waddle (goose), scurry (lemming, rats) and
flock boids (sparrows). No rigging and no 3D credits.

---

## 7. Vertical slice subset

| Category | In the slice | [SLICE+] | Later |
|---|---|---|---|
| Creep types | **10:** Sootcoat Cutpurse, Smoker, Collier, Kiln-Master; Strawling, Fieldkeeper, Crowcaller (+ Crow summon); Cairnling, Drystone Walker, Menhir Elder | Wicker Brute | Earl of Ash, Turnip King, Dolmen Colossus, all Mire Toads, all Frostmarch and Sunscar families |
| Camps | **9:** Charcoal Clamp ×2, Turnip Patch ×2 (green); Smugglers' Den, Crow Field, Drystone Fold ×2 (amber); Standing Ring (red) | Wicker Field replaces Crow Field | All other templates |
| Sleep schedules | All three (`night`, `day`, `never`) | — | — |
| Items | **29:** 7 purchasable, 7 power-ups, 13 permanent (L2–L4), 2 charged (L2) | — | 18 more, including all artifacts |
| Neutral buildings | **Gold Seam ×4, Weighstall** (curled shopkeeper prop), **Hale Spring** | Wayfarers' Inn (Rat-Piper only), Free Company Camp (Greenvale roster), Glimmer Font, Beacon Cairn ×2, Rundling shopkeeper model | Lucky Barrow, Contraption Barn, Twin Milestones, Old Menhir, Weighmaster |
| Critters | Brown Hare, Grey Goose, Firefly Drift | Sparrow Roost (flush) | Hedgehog, all Frostmarch and Sunscar critters |
| Systems | Camp/guard modes, leash and return, sleep and wake, XP factor, bounty with upkeep tax, seeded drops, shop stock and restock, selling, 12 item effect scripts | Hero hire and inn revive, mercenary stock, beacon capture | Rotating stock, transport, teleport pairs |

---

## 8. Production plan

### 8.1 Slice assets and cost estimate

Higgsfield balance at the last ledger check: **228.5 credits** (`docs/asset-ledger.md`, 2026-10-16 14:45). The kingdom doc estimates
70–95 credits for its faction, and the clans need a similar amount. So the neutral layer is designed to cost **about 25–33 credits**,
and none of it needs paid rigging.

| Asset | Method | Higgsfield cr | Krea CU |
|---|---|---|---|
| Sootcoat base (Cutpurse, Smoker, Collier by prop swap and tint) | Concept (0.25) → Tripo H3.1 image-to-3D (9) → bpy auto-rig on the shared humanoid skeleton; shared biped clips | 9.25 | — |
| Kiln-Master | The Sootcoat mesh at 1.12× scale, plus a bpy apron, tall hood and bellows prop | 0.25 (texture) | — |
| Fieldkeeper / Crowcaller | Concept → H3.1 (9). Crowcaller = the same mesh + bpy cloak cards, crow props and staff. The rig uses a **stiff-knee clip variant**. *Saving:* build it procedurally in bpy (poles, sack head, cloth coat) for about 0.5 | 9.25 (or 0.5) | — |
| Strawling, Crow summon | bpy procedural (straw bundle; low-poly bird with flap) | 0.5 | — |
| Cairnling, Drystone Walker, Menhir Elder | bpy procedural slab stacks, rigid-bone animation, 2 stone textures | 0.5 | — |
| Weighstall + curled shopkeeper | bpy kit: stall, awning, crates, 7 m brass balance; 3 textures | 0.75 | — |
| Gold Seam, Hale Spring, loot bundle, power-up props | bpy kitbash; 4 textures | 1.0 | — |
| Critters (hare, goose), fireflies | bpy primitives, procedural motion, 2 textures | 0.5 | — |
| Icons: 29 items + 14 creep abilities | Higgsfield images (0.25 cr each), our own style anchors | ≈ 11 | — |
| Creep vocal sets: 3 families × (aggro, attack, pain, death), 2–3 variants per job (audio §1.6, prompt C1 pattern) | Krea Seed Audio, about 4.63 CU per job | — | 12 jobs ≈ 56 |
| World SFX: buy, sell, can't-afford, item pickup, bundle glint, spring loop, critter set, crow caws, stone grind | Seed Audio | — | 12 jobs ≈ 56 |
| Shopkeeper VO (9 lines) | Krea ElevenLabs TTS (cost per line still to be probed; audio §4.1) | — | probe |
| **Total (slice)** | | **≈ 33 cr** (≈ 24 with the procedural scarecrow) | **≈ 112 CU + TTS** |

**[SLICE+] add-ons:** Wicker Brute (bpy wicker lattice, ~0.5 cr) · Rat-Piper (H3.1 + bpy auto-rig, 9.25 cr; rats procedural; about 26 VO lines) ·
Rundling shopkeeper (H3.1, 9.25 cr; reused for the Weighmaster later) · Wayfarers' Inn (bpy half-timber kit reused from the kingdom kit,
retinted to neutral browns, ~1 cr) · Free Company Camp, Beacon Cairn and Glimmer Font (bpy, ~1.5 cr together).

### 8.2 Prompt and review rules (neutral layer)

- Describe creeps by **function and qualities**, never by analogy. Write "charcoal-burner outlaw with a wide conical leather hood, soot-black face, patched oilcloth coat",
  never "a bandit like in …" (ip-safety §5.2).
- No pumpkin heads in Hollow Harvest prompts. Say "pierced turnip lantern head with drilled holes, no carved face".
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

// data/camps.json
"camp_gv_drystone_fold": {
  "tileset": "greenvale", "mode": "guard", "guard_radius": 12.0,
  "creeps": [["creep_cairn_drystone_walker", 1], ["creep_cairn_cairnling", 3]],
  "drops": {"A": {"class": ["powerup"], "level": 1},
            "B": {"class": ["permanent", "charged"], "level": 3}},
  "props": ["sheepfold_ruin", "gold_seam_expansion"]
}

// data/items.json
"item_homing_pigeon": {
  "name": "Homing Pigeon", "class": "purchasable", "level": 1, "charges": 1,
  "price": {"gold": 325}, "value": 325, "effect": "recall_to_hall",
  "channel": 3.0, "radius": 6.0, "max_units": 11, "cooldown": 0
}

// data/neutrals.json (shop stock)
"neutral_weighstall": {
  "footprint": [8, 8], "patron_range": 4.0, "buys_items": 0.5,
  "stock": [["item_rosehip_draught", 3, 45, 0], ["item_homing_pigeon", 2, 120, 0],
            ["item_picnic_hamper", 2, 90, 180], ["item_wanderers_hobnails", 1, 120, 240]]
}
```

- `sleeps`: `"night"` (default), `"day"` or `"never"`. `level` drives XP and bounty. Level 6+ automatically gets `hardy`.
- Stock rows are `[item, max, restock_s, available_from_s]`, kept per player.
- Drops are resolved at match start with `World.rng`, so a replay with the same seed has the same items.
- **Determinism:** sleep staggers, bounty rolls, drops and critter wander all use the seeded sim RNG.
  Critter wander may instead use a separate *visual* RNG if critters are moved out of the sim (they affect no gameplay except the goose nip and the sparrow flush).

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
| "Waystone Inn", "Mended Drum", "Prancing Pony" | Inns from famous novels | **Wayfarers' Inn**; the Greenvale sign is *The Muddy Lantern* |
| "Farmer's Almanac" | A real publication's trade name | **Hedge Almanac** |
| "Queen" for the termite leader | Hive-queen bug-race read (WoW desert insects) | **Mound-Mother's Champion** |
| WC3 item names (tomes, runes, town portal, sentry ward, appearance dust, ankh, crown of kings, claws, speed boots, protection ring, strength gauntlets, death mask, orbs, escape dagger) | WC3 items (ip-safety §2.1) | Chapbooks, wild berries, Homing Pigeon, Snoop Peg, Flour Bomb, Cat's Ninth Life, Dolmen Crown, Whetstone Fob, Wanderer's Hobnails, Tin Gorget, Plowman's Belt, Ravening Torc, Nettle-Sting Oil, Coilspring Heels |
| WC3 neutral building names | ip-safety §2.1 and mechanics §12.2 | Weighstall, Contraption Barn, Free Company Camp, Wayfarers' Inn, Hale Spring, Glimmer Font, Twin Milestones, Lucky Barrow |
| Other games' names for the same item mechanics (a blink dagger, a revive shield, a spell-blocking sphere) | Dota 2 / League of Legends items | Coilspring Heels, Cat's Ninth Life, Hedge-Witch's Knot |
| "Time is money" / "friend" in the merchant's voice | A famous WoW goblin catchphrase | The shopkeeper never uses either |
| Lemmings marching in a line | The image of a famous puzzle game | The lemming gag is cheek-puffing |
| Exploding farm animal after click spam | A famous Blizzard easter egg | No critter explodes or dies |
| "Gold Mine" | A dictionary term (also WC3) | Data id kept; displayed as **Gold Seam** |

### 10.2 Squint-test risks (WC3 names appear here for review only)

| Ours | Nearest existing design | Allowed overlap (genre) | Rule for the art and kit |
|---|---|---|---|
| Sootcoats | WC3 bandits | Human outlaw creeps | Wide conical leather hoods, soot faces, rakes, billhooks, smoke-pots. No daggers, purple or red hooded cloaks, invisible assassins or a "lord" aura leader |
| Hollow Harvest | Blizzard harvest-golem and pumpkin-headed horseman designs | Scarecrow folklore | Turnip lanterns with drilled holes, never a carved grin; no pumpkins, machinery or horses |
| Cairnwakes, Old Menhir | WC3 rock and granite golems | Stone constructs that never sleep | Stacked slabs with visible gaps, menhir heads with cup-and-ring marks. No boulder throw, no rounded rock-man body, no crystal core |
| Mire Toads | WC3 shore fish-folk | Pond creeps | Real toad anatomy and a hop. No spears, nets, upright posture or gurgled speech |
| Stoatkin | WC3 hyena-folk and candle-miner rat-folk | Small animal-folk raiders | Stoat anatomy, white coat, black tail tip. No candles, mining, hyena or rat features |
| Whiteouts | WC3 ice elementals and revenants | Elemental spirits | Cloud bodies with no torso, limbs or armour |
| Shagbull Herd | WC3 drum-backed beast; Blizzard yaks and mammoths | Beasts | Highland-cattle and musk-ox shapes. No drums, riders, tusks or trunks |
| Moundbuilders | WC3 spider-folk; Blizzard desert bug race | Insect-folk | Upright cream-coloured clay masons with trowels and reed sun-hats. No spider legs, purple chitin, burrowing or swarm god |
| Saltbound | WC3 skeletons and the WC3 undead race | Restless dead | A salt-crystal crust and caravan robes. No visible bones, ziggurats, blight or green skull-glow. Cross-check with `deathless` |
| Rollbacks | WC3 beetle summons | Giant beetles | Brass-green dung-beetles rolling balls. No undead look, burrowing or impale spikes |
| Rundlings, Weighstall, Contraption Barn | WC3 goblin merchants and lab | A small trader people | Pangolin scales, spectacles, a giant brass balance, fairness comedy. No green skin, big ears, greed, explosives, mech suits or airships |
| Wayfarers' Inn | WC3 tavern | An inn where heroes are hired | Coaching inn with a stable arch and a lantern sign |
| Rat-Piper | Folklore's pied piper (public domain); DC's rat-controller; WC3 ranged hero | A rat controller with a ranged weapon | Stovepipe hat, pocket coat, crossbow, tin whistle. No motley, no gas-mask device, no hooded-ranger look |
| Old Menhir | WC3 walking-tree buildings and mountain giants | A big walking piece of landscape | Stone only. No roots, branches, leaves or bark |
| Weighmaster | WC3 goblin gadget heroes | A small merchant-people hero | A Rundling official with a balance-staff. No flasks, no robot suit, no rider |

### 10.3 Compliance summary

- **Names:** none on the ip-safety §2.1 list; collisions resolved (§10.1).
- **Text and voice:** every tooltip and line here is new. Before recording, check every line against the WC3 quote pages
  (including the tavern heroes and the goblin merchant) and the WoW goblin lines (audio §3.2).
- **Numbers:** the systems follow WC3 (camp colours, XP falloff, drop-band shape, upkeep on bounty). The creep stats, item numbers,
  prices and drop bands are our own values, not a copied balance sheet (mechanics §12.2 gray zone).
- **Maps:** the slice layout in §3.6 is written from rules (ip-safety §2.6). Sketch it in `data/maps/` before building.
- **UI:** shield-shaped camp pips, a faceted-nugget mine glyph, a closed-eye sleep glyph and an oilcloth loot bundle: no WC3 icon, chest or "Z".
- **Inputs:** no WC3 data, screenshots or fan assets in any prompt or reference (ip-safety §2.7–2.8). Prompts follow §8.2.
- **Fidelity:** neutral heroes have at most 2 of 4 functional equivalents (§5.6.7). The two signature presentation risks (the merchant people and stone constructs) have explicit art rules (§10.2).

---

## 11. Open questions and tuning flags

1. **Leash, give-up and return:** 18.75 m, 10 s and 2 %/s regeneration are starting values. WC3's real values are unverified (mechanics §14).
2. **Bounty pacing:** 4 × level + 2 + rand(0–4), taxed by upkeep, puts about 520 gold on the slice map (about 3.7 Pavisiers). Check it against mining income in scripted playtests.
3. **Night-active camps:** do new players read the crow-on-head and lantern tells? If not, make the slice Turnip Patch a normal `night` sleeper and keep only the Crow Field night-active.
4. **Stuffed and Carapace** (−25 % Pierce): the slice AI's creep-route picker must weigh camp resistances against army composition (clans Javelineers, kingdom Hookgunners).
5. **Patron range:** 4 m from the building edge is generous. WC3's 45–60 gu (under 1 m) is reported but its reference point is unverified. Guards must ring the Weighstall so that a 4 m range cannot snipe purchases past them.
6. **Stock ownership:** per player (chosen for fairness) or shared like WC3 (unverified)? The same question applies to the Free Company Camp and the Contraption Barn.
7. **Neutral-hero uniqueness:** once per match (first come) is the WC3 feel (reported, unverified). In 1v1, does it create a must-rush pick? An alternative is once per player.
8. **Information leaks:** the Beacon Cairn's minimap flame and the Sparrow Roost flush both reveal positions on purpose. Everything else must pass the fog-leak test in `juice/combat-and-units.md` ("an enemy in fog fighting a creep produces zero sprites, labels and sounds").
9. **Old Menhir:** Drystone Wall makes up to 10 m of cells temporarily blocked. Check region relabel cost against the pathing budget (`architecture.md` §7). Also define how Sleep of Stones interacts with The Wagon Ring and other ultimates (stone units are invulnerable; buffs keep ticking).
10. **The Long Tune:** enthralled units follow a deterministic "follow at most 3.0 m/s" order. Test with cliffs and walls, and the AI's response.
11. **Weighmaster:** her gold-cost spell needs a gold icon on the command card, a "not enough gold" message, and an AI rule.
12. **Faction cross-checks:** Saltbound vs `deathless`, and Mire Toads / Hollow Harvest / Old Menhir vs `sylvan`, once those faction docs exist. Neither later faction may reuse these motifs, and vice versa.
13. **An apex flyer family** (the dragon-like red-camp prize of WC3) is not designed. It needs procedural flight (flyers rig poorly) and must avoid colour-coded dragon families and the hatchling-to-adult ladder naming.
14. **Item count:** 47 against the brief's ~40. If the list must shrink, cut only from pool cells that keep at least two candidates afterwards: for example Shepherd's Bell (L5 permanent), Dewdrop Locket (L2 permanent) and Dropped Purse (L1 power-up). That removes up to 7 items without emptying any drop band.
15. **"Gold Seam" display name:** if testers miss that it is the gold mine, show "Gold Seam (gold mine)" in the tooltip.
16. **Critters in the sim:** the goose nip changes HP, so critters live in the sim (seeded wander). If that costs too much, keep the goose in the sim and move the others to a visual-only system.
17. **Charge merging** of identical consumables (up to 2 × base) is a quality-of-life change from classic WC3. Keep it unless playtests say it hurts shop pressure.
18. **VO volume:** about 26 lines per neutral hero plus 9 for the shopkeeper. Generate all default-voice VO before **31 Dec 2026** (audio decision; ElevenLabs default voices expire).
