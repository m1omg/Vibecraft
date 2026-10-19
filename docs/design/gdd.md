# Vibecraft: Game Design Document (overview)

*Version 1.0, 2026-10-19 (synthesis of the reviewed design docs). Status: proposal for the owner's sign-off. Audience: everyone on the
project. "Vibecraft" is an **internal codename only** (ip-safety §4): the public title, store page and trailer need a cleared name.*

> **Internal document.** It names the reference game on purpose, to explain what we keep and what we change. It never ships, and its
> text never goes into data, UI strings, file names or generation prompts. **Owner action:** `rules.md` records that the GitHub repo was
> **public** on 2026-10-19. Make it private, or move this file, the rules doc's reference columns and the research docs out of the
> tracked tree (rules.md header, §23 #15a).

This document is the front door. It states the vision, the rules we use to stay legal, the factions, the exact vertical-slice scope and
the plan, and it links to the documents that own the details. Where it summarises a number, the owning document wins
(index in §16). Machine-readable slice content for the implementation team is in [`slice-content.json`](slice-content.json).

---

## 0. The game on one page

| | |
|---|---|
| **What it is** | A hero-driven fantasy real-time strategy game for PC (Godot 4.7), built to play **as much like Warcraft III as possible** without copying any of its expression |
| **The player does** | Builds a base on a gold mine and a tree line, trains an army under a food cap of 100 with upkeep, levels up to three heroes by fighting neutral creep camps and the enemy, shops at neutral and faction stores, and wins by destroying every enemy structure |
| **Factions** | Four classic archetypes with original identities: **Brennmark** (`kingdom`, the human kingdom), **the Tormai** (`clans`, the warrior people), **Glaermere** (`sylvan`, the forest elves) and **the Long Wake** (`deathless`, the undead) |
| **Look** | "Storm-lit Heroic Diorama": chunky, hand-painted, readable forms under a fixed three-quarter top-down camera (pitch −56°, 25.8 m) |
| **Sound** | Characterful unit voices with original humour (including annoyed click-spam runs), folk-instrument faction music with silences, a genre-standard bottom-console HUD in our own art |
| **Vertical slice** | Brennmark vs the Tormai, 1v1 against a scripted AI (Easy, Normal, Hard), on one map: **Wether Downs** (96 × 96 tiles, Greenvale tileset) |
| **Match length** | 12–20 minutes |
| **Production** | Small team plus AI-generated assets (Higgsfield, Krea), procedural Blender kits, a free in-house auto-rigger; slice target 23 Dec 2026 |

---

## 1. Vision

**The brief, in the owner's words:** "It should be as much like Warcraft 3 as possible WITHOUT copyright infringement." The owner, a
lifelong fan of that game, rejected high-concept original worlds (sound magic, folklore animals, sheep against roosters) as "not
Warcraft 3". So:

- **Gameplay, structure and feel stay as close to the reference game as the law allows.** A fan should recognise, within seconds, every
  unit's job, every building's place in the tech tree and the logic of every build order. The systems and numbers that make the genre
  feel right are kept: hero levels 1–10 with three abilities and an ultimate at level 6, STR/AGI/INT, six item slots, at most three
  heroes, altar and inn revives, gold mines and lumber, a 100-food cap with upkeep tiers, creep camps that drop items and sleep at night,
  day and night, the attack-type and armour-type matrix, the bottom console, smart right-click, control groups and hotkeys.
- **Every piece of expression is ours.** Names of factions, units, heroes, abilities, items, buildings and places; lore; character and
  building designs; palettes and emblems; materials and cultural inspirations; voice lines; music; UI art; maps.

**What a veteran should say after 15 minutes:** "This is the warrior race, that's the healer, my hero needs level 3 before the amber
camp, I'm about to hit upkeep, and I know exactly how to play it." **What they must never say:** "That's just [a named unit, building,
icon, line or map] from the old game." The M5 release gate tests both (slice-plan §4.5).

---

## 2. Design pillars

| # | Pillar | What it means here | Owner |
|---|---|---|---|
| 1 | **Heroes are the army's centre** | Levels 1–10, 3 abilities × 3 ranks plus an ultimate at 6, attributes, 6 items, max 3 heroes gated by hall tier, the first hero free with a recall item; dead heroes give big XP and cost time and gold to revive | rules §6 |
| 2 | **Creeping is a third side** | Green, amber and red camps by total level, XP that stops at hero level 5, seeded item drops, camps that sleep at night and never respawn, a contested centre and creep-jacking | neutrals, rules §15 |
| 3 | **Small armies, real choices** | Food cap 100; upkeep keeps 100 / 70 / 40 % of gold at 0–50 / 51–80 / 81–100 food, so a 50-food army is the norm and every unit matters | rules §4.4–§4.5 |
| 4 | **A low-scale economy** | 10 gold per trip, one worker inside the mine for 1 s, 5 workers saturate a mine at a 6.0 m hall gap; lumber from felled trees; expanding is a defended commitment | rules §3–§4 |
| 5 | **Fights you can micro** | High HP-to-damage ratios, damage point and backswing, focus fire, body-blocking, pull-backs, recall items, fights of 10–30 s | rules §7 |
| 6 | **The hall tier is the tech decision** | T1 → T2 → T3 upgrades in place and gate heroes 2 and 3, units and upgrade levels | rules §5 |
| 7 | **Day and night change play** | 480 s cycle; night sight 12.5 m; most camps sleep at night; faction rhythms | rules §13 |
| 8 | **Familiar by role, original by expression** | Each faction mirrors a reference race's role slots and tech shape but differs on silhouette, palette, materials, culture, names and voice | faction docs, ip-safety §3.2 |
| 9 | **Readable, chunky, characterful** | Identity in the upper third of every silhouette, two colour masses plus team colour, painted light, units louder than terrain, only VFX blooms | art bible §1 |
| 10 | **Units that talk back** | Ready, What, Yes, Attack, Warcry, Annoyed (click-spam micro-stories), Built and Death lines; character comedy only | art bible §8 |
| 11 | **Juice is information** | Every flourish answers a player question (did it land, is my base safe, when does it fire); no generic sparkles or shake | juice bible |

---

## 3. How we stay legal

**The principle.** Copyright never covers "any idea, procedure, process, system, method of operation" (17 U.S.C. §102(b)), so mechanics,
rules and numbers are free to reuse. Expression is protected, and courts look at the *whole*: *Tetris v. Xio* (2012) found infringement
when a clone copied the visual expression while claiming to copy only the rules, and *Spry Fox v. Lolapps* (2012) let a claim proceed
against a re-skin that swapped the theme but kept the expressive choices. Trademarks (names, trade dress) and the Blizzard EULA (no
extraction, no editor work) are separate risks. Full analysis: [ip-safety.md](../research/ip-safety.md).

### 3.1 The fidelity policy (how the tension is resolved)

| We keep (free: systems, numbers, genre conventions) | We make ours (protected: expression) |
|---|---|
| Global rules and their numbers: start, mining, food, upkeep, XP table, revive formulas, damage matrix, day/night, sight, leash | Every name: factions, peoples, units, heroes, abilities, items, buildings, places, maps |
| **Role structure:** worker, line infantry, ranged, healer, debuffer, anti-magic, siege, cavalry, flyers, T3 giants; altar, barracks, smithy, workshop, shop, towers | Silhouettes, palettes, emblems, materials, architecture and cultural inspiration of every faction (late-medieval Bohemia; Central-Asian steppe; northern lakelands; Etruscan funerary culture) |
| Tech-tree shape and build-order logic | Unit kits: every unit keeps its role but has at least one mechanic of its own |
| Hero archetypes (tank-healer, fire mage, stealth duelist, seer) | Hero kits: **at most 2 of 4 abilities** may be functional equivalents of the matching reference hero's; never the reference ultimate's signature; all names, VFX and numbers ours |
| One signature faction mechanic per faction, **re-presented** | Its presentation (see §4) |
| HUD layout: bottom console, minimap bottom-left, 4×3 command card, top resource bar, hero buttons, idle-worker button | All HUD art: our chassis and faction inlays, the **Horizon Ribbon** day/night strip (never an orb), our cursors, our fonts (SIL OFL), our icons |
| Map principles: 2 starts, natural expansions, tiered camps, central shop, fountains, chokes | Map layouts drawn from our own written brief, checked against every classic 1v1 map (`map_lookalike`) |
| Voice line *categories* (including click-spam) | Every line, written from scratch and checked against the reference quote pages |

### 3.2 The rules every contributor follows

1. **Distinctness rubric** (ip-safety §3.2): each faction differs from its nearest reference race on at least 4 of 6 axes (silhouette,
   palette, materials, cultural inspiration, signature mechanic, names and voice), and always on silhouette. Brennmark and the Tormai pass
   6 of 6 (kingdom §12, clans §2.6); Glaermere and the Long Wake pass in sylvan-and-deathless §A9 and §B9.
2. **One inherited signature mechanic per faction**, shown differently (§4). Multi-builder sites are a cross-faction rule (kingdom,
   sylvan, deathless), not a second kingdom signature.
3. **Hero kits:** at most 2 of 4 functional equivalents, audited per hero (kingdom §6.4, clans §6.2, neutrals §5.6.7).
4. **Numbers:** global rules keep the reference values. Faction values never equal a reference value, and **functional equivalents differ
   by at least 20 % at every rank** (slice-plan M1 #11). `tools/ip/check_value_echo.py` checks every recorded pair.
5. **Names and lines:** nothing from the ip-safety §2.1–§2.2 lists, no paraphrase of a reference line, no one-word swaps of a reference
   coinage, no "poke/tap/prod/jab" click jokes, no Ready line starting "Ready to", no crew splitting a punchline (art bible §8.1).
   `tools/ip/check_banned_terms.py` scans `src`, `data`, `assets`, `tests`, `tools/prompts` and the art bible; `banned_ui_terms.txt`
   guards UI strings ("Keen Sight", "Spellproof", never the reference status names).
6. **Generation hygiene:** prompts describe qualities, never analogies; no brand, artist, composer or actor names; no reference
   screenshots as inputs; every generation logged in `docs/asset-ledger.md` with the human edits made afterwards.
7. **Never touch the reference game's data:** no archive extraction, no World Editor, no fan rips.
8. **Trade dress:** each faction has its own team-colour preference list so a default match never shows the reference franchise's
   canonical pairings (kingdom Emerald vs clans Royal Blue by default; art bible §2.4).
9. **Release gate** (ip-safety §5.3): a cleared public title, an attorney's review of name and key art, a veteran's 15-minute look-alike
   review, Steam AI disclosure, terms snapshots, `CREDITS.md`.

---

## 4. Factions at a glance

| | **Brennmark** (`kingdom`) | **The Tormai** (`clans`) | **Glaermere** (`sylvan`, later) | **The Long Wake** (`deathless`, later) |
|---|---|---|---|---|
| Archetype mirrored | The human kingdom | The warrior people | The forest elves | The undead plague |
| People | The Brennish (human guild towns) | The Tormai: big, ash-grey, heavy-jawed, tuskless steppe nomads; allies the Thoom (gentle cauldron-helmed giants) | The Glaer, a lakeland forest-elf people | The Wakeful: the risen dead of the Old Families |
| Culture | Late-medieval Bohemia: wagon-forts, pavises, hand-cannons, flails, guilds, onion domes, linden and storks | Steppe hospitality: felt yurts, lamellar, bronze gongs and mirrors, tea, wrestling | Pile-dwellings, birch bark, amber, resin tapping, tar-burning | Etruscan and Roman funerary culture: tumulus tombs, ancestor masks, urns, rose-days |
| Palette | Burgundy, ivory, dark bronze, blackened iron, oak | Dark ink-teal and saffron felt, warm bronze, ash-grey skin | Moss sage, birch white, charcoal, amber | Soot lacquer, chalk bone, terracotta, grave-rose, tarnished silver |
| Emblem | The Ember Wheel: an ivory six-spoke wheel with a coal at its hub and three crown points, on burgundy | The Gong and the Twin Winds: a saffron disc crossed by two teal wind-strokes | The Kept Light: an amber teardrop between two birch leaves | The Remembered Face: a closed-eyed chalk mask above an offering bowl in a ring of roses |
| Inherited signature (one) | **Levy Horn**: workers near a hall arm in place as a 40 s flail levy | **Sound the Gong / Roll the Felt**: 3 workers garrison a Home Yurt and sling stones | **Tapping**: workers tap trees for resin and never fell them | **The Pall**: a ground layer that favours the Wakeful |
| Original mechanic | Wagon Fort (deploying, chaining gun-wagons) | — (kits carry the originality: Shove, Heel-Seeker, Withdraw, Shelter) | Summerhoard: lumber-fuelled noonlight lanterns | Heirloom Masks: veteran ranks pass to whoever picks a mask up |
| Worker / hall | Hodman / Moot Hall → Walled Burg → Crown Burg | Yurtwright / Shell Hall → Banner Shell → Sun-Gong Shell | Tapster / Stilt Lodge → Lantern Lodge → Amber Lodge | Sexton / Wake Barrow → Long Barrow → Grand Barrow |
| Heroes | Wheel Marshal, Firewright (slice); Flail Hetman (P1); Orrery Sage | The Uncut, Skymirror (slice); Omen-Mother (P1); Kettle-Uncle | Lark Captain, Thicket Weaver, Lampbreaker, Reedstalker | Mourning Legate, the Dowager, the Patriarch, Gravewright |
| Play pattern | Sturdy, slow, expensive; infantry walls behind gunpowder; strong towers; weak to early harassment and caster burst | Durable units and strong heroes; mobile mid-game pushes; pulls, traps and sleeps; few cheap detectors | Fragile, fast, ranged; best anti-air and dispel; strong by day and by its lanterns | Cheap fast melee, sturdy siege, sustain on the Pall; snowballs through masks |
| Voice | Deadpan guild tradesfolk; the advisor is the Reeve | Courteous menace ("guests"), a throat-hum "Hm-hm"; the advisor is the gong-keeper | Bright, unhurried light-hoarders with a lilting chant cadence | Languid, snobbish old money that happens to be dead |
| Owning doc | [kingdom.md](factions/kingdom.md) | [clans.md](factions/clans.md) | [sylvan-and-deathless.md](factions/sylvan-and-deathless.md) Part A | Part B |

The Tormai UI never shows the word "Clans" and no faction is ever called "orc" (clans §1.1): a distinct people's name is the cheapest
strong signal of independent creation, and it keeps generated art away from green skin and tusks.

---

## 5. Decisions made at synthesis (2026-10-19)

The seven design docs were reviewed separately. This pass read them together and resolved every place where they disagreed. Each
decision was applied in place in the owning docs (see their notes dated 2026-10-19).

| # | Conflict | Decision | Why |
|---|---|---|---|
| 1 | The slice plan named units by role (`kingdom.worker` …) pending final names | Final display names substituted throughout; Appendix A keeps the role → name index; ids in `slice-content.json` | Names lock on 3 Nov for VO |
| 2 | Slice plan proposed a clans "rope-holder" second builder; clans and rules kept one builder | **Declined.** The clans keep one builder per site; the kingdom's Hod Chain stays | Fidelity: the reference warrior race could not multi-build. Multi-building stays a cross-faction rule (kingdom, sylvan, deathless), so it is not a second kingdom signature |
| 3 | Worker completion VO id: `built` (slice plan) vs an interim "job" + "done" id (art bible) | **`built`**, label "Built"; the three spellings of the old id are banned terms | The old id put a banned catch-phrase into file names |
| 4 | Art bible requested renames the faction docs had not adopted | **Adopted:** Keen Edge → **Clean Cut**; Homeward Horn / Felt → **Way-Home Horn / Felt**; Cauldron-Father → **Kettle-Uncle**; creeps Crowcaller → **Crowherd**, Smoker → **Coal-Lobber** | Other-IP echoes; the old forms are on the banned list |
| 5 | Some functional equivalents sat within 20 % of the reference value | Dust Veil +60 / 100 / 140, 55 mana, 0.35 s fade, +20 / 30 / 45 % speed; Clean Cut 20 %, 1.6× / 2.3× / 3.0×; Hail-Swifts 38 s; Linden Balm 150 / 290 / 430 and 80 mana; The Wagon Ring 150 mana | The M1 IP number gate; value-echo reference updated |
| 6 | Wheel Marshal kit (kingdom vs slice plan) | Linden Balm may target herself at 50 %; The Wagon Ring counts as her second functional equivalent (2 of 4); its VFX is physical painted wagon boards; Brace the Wheel shows a `fx_wheel_rim_ring`, never a slam or shockwave | Keeps the kit legal and away from the reference holy warrior's look |
| 7 | Footprints: 10-cell halls (kingdom, clans, sylvan, deathless) vs 8 m halls (art bible, meshes) | **Art bible §1.3 sizes everywhere:** hall 16 × 16 cells (8 m); production, altar, shop, research 12 × 12; supply 8 × 8; tower 4 × 4; Gold Seam, Weighstall and inn 12 × 12; Hale Spring 8 × 8 | Sim footprint = mesh width; halls already processed at 8 m. The slice map is re-validated in M1 (seams and stall grew; the Den's acquire range is now 7.2 m) |
| 8 | Siege crews | The Bombard Wagon has one speaking gunner; the Sling-Cart brothers speak only in unison | A bickering two-gunner act is the reference artillery crew's device |
| 9 | Voice line counts (faction docs ≈ 152–162 per faction; art bible 181 / 180) | The art bible §8.2 counts are the full set: **371 slice lines**; slice-plan P0 records **251** | One source of record; P0 remains the funded subset |
| 10 | Clans skin (slate blue-grey vs ash-grey) and hero heights | Ash-grey "weathered granite" `#77746F`; Tormai heroes 2.35–2.4 m | Blue-grey drifted generated art toward a reference race |
| 11 | Team colours and HUD inlays | Coral Rose joins the clans' trade-dress skip set; Cornflower is the clans' fallback; the clans HUD inlay is ochre-washed lattice (never red-brown); autocast is a steady bottom bar, never corner marks | Trade-dress distance |
| 12 | Gold Seams ×4 (neutrals) vs ×5 (map) | **5**: a contested third seam inside the Standing Ring, which stands in guard mode | Gives long games an expansion to fight over |
| 13 | Push hero levels ("levels 4–5" in build orders) | Hero 1 level 4, hero 2 level 3 at the push (3–4 / 2–3 when the shared camps are contested) | The neutrals XP route |
| 14 | Rat-Piper hire ([SLICE+] vs P1) | Inn revive is P0; hiring the Rat-Piper is **P1** (next Higgsfield grant) | Budget plan |
| 15 | Tileset id `greenvale` vs `gv` | Tileset id `gv`, map id `wether_downs`; players see "Downland" | Working titles; "greenvale" never ships |
| 16 | AI rules for contested camps and the third expansion existed only in the slice plan | Added to rules §19 | One AI source |

**Still open after synthesis** (owners named in each doc): the juice docs still use some retired names (Homeward, the old completion id,
Hollow Harvest); `architecture.md` and `tools/kits/buildings.py` still use the old footprints; `src/systems/player_state.gd` still has
the reference colours; kingdom value-echo rows (and a check of the Firewright's two equivalents) are due before kit data entry;
`assets/models/buildings/manifest.json` carries a banned smithy term from the kit script; the Way-Home Felt's 325 g may echo a reference
price (neutrals §11).

---

## 6. Vertical slice scope

**Brennmark vs the Tormai, 1v1 against the AI, on Wether Downs. Tiers T1 and T2 only (2 hero slots).** Priorities: **P0** the slice is
not done without it; **P1** funded from the next Higgsfield grant (≈ 16 Nov); **P2** stretch. Ids and stats: `slice-content.json`.

### 6.1 Brennmark (`kingdom`) roster

| Unit | Role | Built at | Gold / lumber / food | HP, armour | Attack | Notes |
|---|---|---|---|---|---|---|
| Hodman | Worker | Moot Hall | 70 / 0 / 1 | 230, 0 Medium | Blade 5–7 | 10 lumber per trip; **Hod Chain**: up to 2 extra carriers, +40 % build rate each, 5 lumber per 10 s; **Take Up the Flail** |
| Flail Levy | Worker militia form | (Hodman, 1.5 s) | — | 330, 3 Medium | Blade 10–13 | 40 s; within 22 m of a hall; leash 30 m |
| Pavisier | T1 line infantry | Drill Yard | 140 / 0 / 2 | 440, 2 Heavy | Blade 12–14 | **Plant Pavise** (Pavise Drill): −45 % Pierce, Cover for allies behind |
| Hookgunner | T1 gunpowder ranged | Drill Yard (Foundry) | 200 / 30 / 3 | 520, 0 Medium | Pierce 22–28, 7 m (9 m) | **Braced Shot** +15 % after 2 s still |
| Linden Sister | Healer caster (T2) | Collegium | 125 / 20 / 2 | 300, 0 Unarmored, 180 mana | Arcane 8–10 | **Herb Poultice** (autocast heal); **Smoke of Rue** (dispel, anti-summon) with Journeyman Papers |
| Bombard Wagon | Siege (T2) | Wainwright Yard | 190 / 60 / 3 | 420, 1 Heavy, mechanical | Siege 52–64 splash, 15.5 m | **Signal Shell** (area reveal), **Case Shot** (splash slow) |

**Heroes:** Wheel Marshal (STR tank and support) and Firewright (INT fire caster), §6.3. **Buildings (10):** Moot Hall → Walled Burg,
Croft (+7 food), Oath Hall (altar), Drill Yard, Timber Yard (lumber drop-off, tower gate), Foundry, Collegium, Wainwright Yard, Curio
Cabinet (shop), Lookout → Gun Tower. **Research (14):** Tempered Blades, Corned Powder, Gothic Plate and Quilted Gambesons (levels 1–2
each), Pavise Drill, Drawn Barrels, Case Shot, Signal Shells, Lime Mortar, Linden Journeyman Papers.

### 6.2 The Tormai (`clans`) roster

| Unit | Role | Built at | Gold / lumber / food | HP, armour | Attack | Notes |
|---|---|---|---|---|---|---|
| Yurtwright | Worker | Shell Hall | 70 / 0 / 1 | 240, 0 Medium | Blade 6–8 | 15 lumber per trip, slower chop; one builder per site; **Roll the Felt** into a Home Yurt; **Mend** |
| Grappler | Heavy melee infantry | Grapple Yard | 185 / 10 / 3 | 660, 1 Heavy | Blade 17–22 | **Shove** (Wrestler's Training): every 4th hit shoves and cancels a swing |
| Javelineer | Ranged thrower | Grapple Yard | 140 / 20 / 2 | 370, 0 Medium | Pierce 19–24, 7 m (8.6 m) | Throwing-Sticks range research |
| Gustcaller | Buff and dispel caster (T2) | Mirror Yurt | 135 / 25 / 2 | 320, 0 Unarmored, 180 mana | Arcane 9–11 | **Unbind** (area selective dispel); **Wind at Your Back** (haste, autocast) with Second Ribbon |
| Sling-Cart | Siege (T2) | Grapple Yard (Casting Pit) | 200 / 70 / 3 | 420, 1 Heavy, mechanical | Siege 60–74 splash, 15.6 m | Packed Clay Pots widens the splash |

**Heroes:** the Uncut (AGI stealth duelist) and Skymirror (INT seer), §6.3. **Buildings (8):** Shell Hall → Banner Shell, Home Yurt
(+10 food, garrison 3), Grapple Yard, Naming Stones (altar), Casting Pit (smithy, lumber drop-off), Mirror Yurt, Bow-Mast (tower), Tea
Tent (shop). **Research (10):** Bronze Edges, Bronze Points and Lamellar Plates (levels 1–2 each), Wrestler's Training, Throwing-Sticks,
Packed Clay Pots, Gustcaller Second Ribbon.

### 6.3 Slice heroes (all four kits, with hotkeys; ≤ 2 of 4 functional equivalents each)

| Hero | Ability (hotkey) | Kind | Key numbers (rank 1 / 2 / 3) | Equivalent? |
|---|---|---|---|---|
| **Wheel Marshal** (STR) | Linden Balm (L) | Ally heal, self at 50 % | 150 / 290 / 430; 80 mana, 7 s | Yes |
| | Brace the Wheel (B) | Taunt plus armour | 4 / 5 / 6 m, taunt 2 / 3 / 4 s, +4 / 6 / 8 armour | No |
| | Measured Cadence (C) | Aura | +6 / 10 / 14 % attack speed | No |
| | The Wagon Ring (R) | Ultimate | 7 s: allies cannot drop below 1 HP, then +15 % HP; 150 mana, 160 s | Yes |
| **Firewright** (INT) | Naphtha Flask (N) | Area burn | 55 / 90 / 125 + 12 / 20 / 28 per s for 6 s; 95 mana, 9 s | Yes |
| | Fuse Mark (F) | Delayed bomb | 80 / 140 / 200 after 4 s; 80 mana, 11 s | No |
| | Incendiary Wadding (W) | Aura | Allied ranged attacks burn 3 / 5 / 7 per s | No |
| | Grand Bombard (B) | Ultimate | 25 s crewed bombard, 900 HP, Siege 75–85; 175 mana, 150 s | Yes |
| **The Uncut** (AGI) | Dust Veil (D) | Stealth opener | 15 / 20 / 25 s, +20 / 30 / 45 % speed, +60 / 100 / 140 first hit; 55 mana, 8 s | Yes |
| | Braid Lash (L) | Pull and root | 40 / 75 / 110, pull 3 m, root 1 / 1.25 / 1.5 s; 70 mana | No |
| | Clean Cut (C) | Passive crit | 20 %: 1.6× / 2.3× / 3.0× | Yes |
| | Through the Tall Grass (T) | Ultimate | 10 s: +40 % attack speed, line cleave 8 m × 2 m; 125 mana, 120 s | No |
| **Skymirror** (INT) | Sunglint (G) | Cone blind | 35 % miss 3 / 4 / 5 s, 50 / 85 / 120 damage; Moonglint at night | No |
| | Bronze Window (B) | Remote reveal | 10 / 14 / 18 m for 10 s; rank 3 detects | Yes |
| | Hail-Swifts (W) | Summon | 2 / 2 / 3 ground swifts for 45 s, tank creeps; 100 mana, 38 s | Yes |
| | Swallowed Sun (U) | Ultimate | 9 m darkness for 12 s: sight 3 m, 40 % miss; 175 mana, 150 s | No |

Hero rules: 425 gold / 100 lumber / 5 food / 55 s (the first is free with the faction's recall item); hotkeys use the ability's
mnemonic letter, with an optional Q / W / E / R setting (rules §18.4).

### 6.4 Items

| Source | Items |
|---|---|
| Curio Cabinet (kingdom) | Way-Home Horn (recall, 300 g), Linden Salve (+240 HP, 135 g), Sage's Tincture (+140 mana, 115 g), Tin Watchman (ward, 60 g); T2: Tailor's Chalk (detection, 70 g) |
| Tea Tent (clans) | Salt Tea (300 HP over 12 s), Kettle-Bottom Tea (+230 HP), Brick-Tea Shavings (mana over time), Overnight Steep (+130 mana), Hail-Eye Pebble (vision ward), Way-Home Felt (recall, 325 g); T2: Folded Yurt (instant supply) |
| Weighstall (neutral, centre) | Rosehip Draught, Bluebell Cordial, Homing Pigeon (recall), Snoop Peg (ward), Tattle-Burrs (detection), Picnic Hamper (3:00), Wanderer's Hobnails and Stoutheart Weight (4:00), Wiped Slate (retrain, 5:00); the **Fair Exchange** service (100 gold ↔ 60 lumber, once per 120 s) |
| Creep drops (24 in the slice) | 7 power-ups (+1 STR / AGI / INT objects, Wild Strawberries, Dropped Purse, Fair-Day Rosette, Old Soldier's Tally-Stick), 13 permanents (levels 2–4), 4 charged (Honeycomb Wedge, Mint Sprig, Smoke Pellets, Firefly Jar) |

Every recall item follows one spec: target a point or own hall, 5 s channel that enemy stuns cannot break (any own order does), the hero
plus up to 23 units within 9.4 m (rules §6.8). The slice has 33 neutral items plus 12 faction-shop items.

### 6.5 Creeps, camps and neutral buildings

| Family | Creeps (level) | Look |
|---|---|---|
| **Sootcoats** (outlaw charcoal burners; sleep at night) | Cutpurse (1), Coal-Lobber (2), Collier (3), Kiln-Master (5) | Wide conical leather hoods, sooty faces, oilcloth |
| **Tattiebogles** (walking scarecrows; awake at night) | Strawling (1), Fieldkeeper (3), Crowherd (4, summons Crows) | Crossed poles, sack heads, drilled turnip lanterns with no face |
| **Cairnwakes** (drystone that got up; never sleep) | Cairnling (3), Drystone Walker (5), Menhir Elder (7) | Slab stacks with cup-and-ring marks |

| Camp | Colour, level | Count | Role on Wether Downs |
|---|---|---|---|
| Charcoal Clamp | Green 5 | 2 | Hero 1's first camp (~2:10) |
| Turnip Patch | Green 8 | 2 | Hero 1's second camp, asleep from the first dusk |
| Woodward's Rest | Green 9 | 2 | Hero 1's third camp |
| Collier's Hut | Green 8 | 2 | Hero 2's first camp |
| Drystone Fold | Amber 14, guard, never sleeps | 2 | Guards each natural expansion |
| Charcoal Yard | Amber 14 | 2 | Hero 2's second camp |
| Smugglers' Den | Amber 11 | 1 | Guards the central Weighstall; contested |
| Crow Field | Amber 12, the one day camp | 1 | Guards the Hale Spring at night; contested |
| Cairn Gate | Amber 16, never sleeps | 1 | Shared prize at ~6:20; contested |
| Standing Ring | Red 20, guard, never sleeps | 1 | Red prize and key to the third Gold Seam |

16 camps (8 green, 7 amber, 1 red), 3,815 raw XP, ≈ 984 gold of bounty, 11 of 16 asleep at night. **Neutral buildings:** 5 Gold Seams
(12,000 main, 8,000 others), the Weighstall (merchant with Rundling traders), the Hale Spring (health fountain), the Coaching Inn *The
Muddy Lantern* (instant revive at P0; hiring the Rat-Piper at P1). **Critters (P1):** 6 hares, 4 geese, fireflies; they never explode.

### 6.6 The map: Wether Downs

| | |
|---|---|
| Size | 96 × 96 tiles of 2 m (192 m), tileset `gv` ("Downland" to players), cliff levels 0–2 |
| Layout | Mirror-symmetric across the NW–SE diagonal; P1 starts SW, P2 NE; one 8 m ramp per main; natural below the ramp behind a guard-mode amber camp |
| Centre | A level-0 basin with the Weighstall and Smugglers' Den on its north-west side; the shortest lane crosses the basin's south-east half |
| Flanks | NW: Hale Spring with the day-sleeping Crow Field and the shared Cairn Gate. SE: the red Standing Ring over the contested third seam, and the never-guarded Coaching Inn on the axis |
| Distances | Main to main 206 m of path (≈ 49 s for infantry); main to natural 57.5 m |
| Evidence | Drawn from a written brief; the ASCII sketch is copied to `data/maps/` and checked against every classic 1v1 map (slice-plan §1.1, M1 #10) |

### 6.7 P1 and out of scope

- **P1 (next Higgsfield grant, ≈ 48.5 cr):** a second caster per side (Lacewright, Pole-Carver), a third hero per side (Flail Hetman,
  Omen-Mother) or the Rat-Piper hired at the inn, and the T3 data tier (Crown Burg, Sun-Gong Shell, Burgher's Oath → Sworn Pavisier,
  Proving Rite → Proven Javelineer, Guild Seal and Elder Ribbon trainings, level-3 smithy lines). Their VO is funded separately (§13).
- **Out of the slice:** flyers and mounts (rig poorly), the clans' Herd Pen and Guest Ring and the kingdom's Stork Loft, all T3 units,
  the sylvan and deathless factions, the Rimeholt and Sunscar tilesets, the Lucky Barrow, Hiring Fair, Contraption Barn, Twin
  Milestones and Beacon Cairns, team games.

---

## 7. Core loop and match rhythm

**The loop:** mine and chop → spend on supply, production and tech → train an army that stays under the upkeep line → take the free
hero and creep with it for XP, gold and items → shop, revive and recall → tier up for hero 2 and casters → push or expand → a decisive
fight. Night closes the creep window and opens the scouting one.

| Clock | What happens (Normal AI scripts follow this) |
|---|---|
| 0:00–2:00 | 5 idle workers to gold; worker 1 builds the altar; supply and barracks. The altar finishes at ~1:00–1:05; the free hero is out at **~2:00** |
| 2:00–3:20 | Hero 1 creeps the nearest green camp alone or with its first unit (the Skymirror behind two Hail-Swifts); towers and worker defences (Levy Horn, Sound the Gong) answer early raids |
| 3:20 | **First dusk.** Night camps fall asleep (the attacker gets the first blow); the Crow Field wakes; sight drops to 12.5 m |
| 3:40–4:30 | Hall upgrade to T2 (kingdom 3:45, clans 4:15); faction shop built; hero 1 reaches level 2 |
| ~5:30 | Hero 1 level 3 on the own Drystone Fold; the natural can be taken |
| 5:55 / 6:25 | T2 done (kingdom / clans): hero 2, the caster building, siege |
| ~6:20–7:00 | Both hero 1s contest the shared Cairn Gate and Crow Field: creep-jacking |
| 7:20 | Dawn |
| 8:30–9:30 | First push at ≈ 50 food, Upkeep 0 %: hero 1 level 4, hero 2 level 3; siege takes towers |
| 10:00–14:00 | Decisive fights, the red camp, expansions; median game end 12–20 min |

**Rules at a glance** (rules.md owns them): 500 gold / 150 lumber, 5 idle workers, 08:00 start; mines 12,000 / 8,000 with a low warning
at 1,500; food cap 100, upkeep 100 / 70 / 40 %; XP 200 … 5,400 to level 10, creep factor 80 / 70 / 60 / 50 / 0 %; altar revive ≤ 550
gold and ≤ 110 s, inn revive instant at 50 % HP; armour reduction 0.06A / (1 + 0.06A); 7 attack × 7 armour types under our names
(Blade, Pierce, Siege, Arcane, Heroic, Spell, Raw; Light, Medium, Heavy, Fortified, Hero, Unarmored, Adamant); 480 s day/night; leash
18.75 m; bounty 4 × level + 2 + rand(0–4); defeat when a player owns no structure.

---

## 8. Controls

| Input | Behaviour |
|---|---|
| Left-click / drag | Select (cap **12**, the 12-slot selection grid); Shift adds or removes; Ctrl or double-click selects a type on screen |
| Right-click | Smart command: move, attack, gather, repair, enter garrison, pick up, return cargo, rally |
| Hotkeys (Classic preset) | Move M, Stop S, Hold H, Attack A (A-click attack-move), Patrol P, Build B / V, Learn O; abilities on mnemonic letters (optional Q / W / E / R); a Grid preset maps the 4 × 3 card to QWER / ASDF / ZXCV |
| Groups | 10 control groups (Ctrl+N set, Shift+N add, double-tap to centre); Tab cycles subgroups; F1–F3 heroes; F8 or ` idle worker; Backspace halls; Space last alert |
| Queues | Shift-queue up to 32 orders; Shift + train queues 5; 7-item building queues |
| Autocast | Right-click an ability button |
| Items | Numpad 7 8 4 5 1 2 (Alt+1–6 laptop preset) |
| Other | Alt shows health bars and rally flags; Insert / Delete rotate the camera temporarily; minimap clicks move the camera or issue the armed order |

---

## 9. Camera

| Constant | Value |
|---|---|
| Rig | Ground focus node plus a perspective `Camera3D`; yaw locked |
| Pitch | −56° |
| Distance | Default 25.8 m; zoom 18.75–35.2 m (optional pitch drift ≤ 4°) |
| Field of view | 55° vertical (`KEEP_HEIGHT`) |
| Feel | Smoothing `1 − exp(−12·dt)`; edge pan inside ~8 px at ~1.1 × distance m/s; arrows and middle-drag; jumps to alerts and heroes |
| Readability | Infantry ≥ 40 px and heroes ≥ 50 px tall at 1080p; the minimap draws the camera trapezoid |

---

## 10. UI layout

The genre structure, our proportions and art (art bible §7):

| Element | Placement |
|---|---|
| Top bar (34 px) | Menus left; the **Horizon Ribbon** (a flat strip of painted hills with a travelling sun and moon) centre; gold, lumber, food used/cap and the upkeep label right |
| Hero buttons | Left edge, up to 3, with HP and mana bars and a level badge; the idle-worker button sits above the minimap |
| Bottom console (≤ 20 % of height) | One low-opacity band carrying four translucent plates: minimap (bottom-left, with Formation, Show Camps and colour-mode toggles), live 3D portrait, info plate (stats or a 2 × 6 selection grid), hero inventory (2 × 3), and the 4 × 3 command card (bottom-right) |
| Skins | A shared plain dark chassis; faction inlays on the rims only: kingdom burgundy-stained oak with bronze rivets and wheel-rim brackets; clans ink-teal felt over ochre-washed lattice with bronze studs |
| Fonts | Alegreya Sans, Alegreya SC, Grenze Gotisch (kingdom), Philosopher (clans); all SIL OFL |
| Never | Gilded or carved-stone frames, gargoyles, skulls, an orb or dial clock, a gauntlet cursor, the reference icons or button bevels |

---

## 11. Art direction (summary of the art bible)

- **Style:** "Storm-lit Heroic Diorama". Chunky heroic proportions with identity in the upper third; hands, weapons, hats and shoulders
  1.5–2× real; two colour masses plus team colour; painted light (roughness 1, metallic 0, no specular); terrain quiet (value 30–65 %,
  saturation ≤ 45 %), units loud (≤ 85 %), only VFX above HDR 1.0. Sun at 50–55° (`#FFF0D8`), blue-white moon at night.
- **Scale:** worker 1.2–1.4 m, infantry 1.6–1.9 m, heroes 2.1–2.4 m; halls 8 m wide and 6.5–7 m tall; every building no taller than it
  is wide (towers excepted).
- **Team colour:** our own 12 colours (each ≥ ΔE 20 from the reference set) on 10–15 % of each silhouette; per-faction preference lists.
- **Terrain:** a 7-tile Greenvale ladder with crisp corner-mask blending, drystone cliffs authored for 2 m, painted water, procedural
  trees with wind sway; drifting cloud shadows.
- **Factions:** Brennmark is burgundy and ivory with kettle-hat discs, pavises, wagons, half-timber and onion domes. The Tormai are
  teal and saffron felt with bronze cones and streamers, flat lamellar flaps, low domes and carved masts. Neutrals carry no team colour.
- **Process:** fixed style suffix, faction clauses and counter-clauses per look-alike risk; 64 px black-silhouette squint test from the
  game camera on every asset; post-processing clamps (palette LUT, saturation, skin band); everything logged.

## 12. Audio direction (summary)

- **Voices** (ElevenLabs preset voices through Krea, never cloned): categories Ready, What, Yes, Attack, Warcry, Annoyed, Built,
  Mechanic, hero lines and non-verbal deaths. Counts: worker 21, infantry or ranged 19 (standout 21), caster 21, siege crew 17, hero 31,
  advisor 19: **371 slice lines**, 251 at P0. Acks are short (≤ 4 words at ≥ 3 words/s). Kingdom: deadpan guild tradesfolk in crisp
  neutral English. Clans: formal, courteous menace with a throat-hum. No accents imitated, no pop culture, no reference lines.
  **All VO by 15 Dec 2026** (default voices expire 31 Dec).
- **SFX** (Seed Audio via Krea, CC0 fallback): a swing × material combat matrix, per-faction UI and construction sets, signature cues
  (Levy Horn, gong call, recall channels, our level-up bells into a singing bronze bowl). 3D world sounds pooled and capped; acks in 2D.
- **Music** (ElevenLabs Music, instrumental): 3 tracks per faction in shuffled rotation with 20–40 s of silence, a menu theme, victory and
  defeat stingers, opening cues. Kingdom: a village band gone to war (hurdy-gurdy, bagpipe drone, dulcimer, fiddle, field snare, horns).
  Clans: frame drums in 6/8, bronze gongs, two-string fiddle, jaw harp, overtone drone. No battle-music switching.
- **Ambience:** day and night beds per biome with our own dusk and dawn stingers.

---

## 13. Production approach and budget

| Area | Approach |
|---|---|
| Characters | Concept on Higgsfield `gpt_image_2_5` (0.25 cr) → Tripo H3.1 image-to-3D (9 cr) → the free CPU auto-rigger (`tools/autorig.py`) on one library skeleton; bought library clips transfer to every biped. All 12 slice characters and both halls are made |
| Buildings, props, siege | Procedural Blender kits (half-timber kit, yurt kit, slab kit) with AI-painted tiling textures; wheeled siege and crews animated procedurally |
| Mounts, flyers, beasts | Later: they rig poorly; procedural motion where needed |
| 2D | Icons on 2 × 2 sheets, portraits, UI frame parts and loading art on Krea 2 Medium with our own style anchors |
| Audio | §12; probes first (one TTS batch, one music clip, one Seed Audio job) |
| Budgets (derived, 2026-10-17) | Higgsfield ≈ 77.5 cr (20 reserve; 45 cr of P0 still to spend before the ~15 Nov reset); Krea ≈ 1,500 CU (150 reserve; P0 1,056 CU; P1 cap 294 CU). The next grant funds the P1 roster (48.5 cr) |
| Gates | Names lock 3 Nov; Higgsfield P0 3D before ~15 Nov; VO by 15 Dec; every asset passes the squint test and the IP checkers |

## 14. Milestones

| Milestone | Window | Exit criteria (summary; slice-plan §4) |
|---|---|---|
| **M1 Playable loop (graybox)** | 17 Oct – 2 Nov | Wether Downs authored and validated; economy, construction, production, research, shops, heroes, items, creeps, worker defences, flying layer; bot-vs-bot 15 min with deterministic hashes; timeline (first hero ≤ 2:05, T2 within ±15 s of script); IP number and name gate passes; `controls_parity` |
| **M2 Art pass** | 20 Oct – 14 Nov | Every P0 asset imported and logged; 64 px silhouette test ≥ 90 % for 16 silhouettes; team colours read day and night; 200 units at ≥ 60 fps (Forward+), ≥ 30 fps (Compatibility); rubric re-run on rendered units |
| **M3 Audio pass** | 3 Nov – 28 Nov | P0 VO (251 lines), SFX and music in; ack and annoyed rules; loudness targets; all VO generated by 15 Dec |
| **M4 AI opponent** | 17 Nov – 11 Dec | Easy, Normal, Hard per faction; seat fairness and faction balance 40–60 %; median game 12–20 min; creeping discipline and contested-camp branch; items, shop and revive use |
| **M5 Polish and release gate** | 7 Dec – 23 Dec | Juice P0 rows; front end; 3 external testers incl. a veteran (fidelity checklist ≥ 10 of 12); zero look-alike findings; zero crashes in 20 games; ledger and `CREDITS.md` complete |

## 15. Top risks and open questions

| Risk or question | Plan |
|---|---|
| The repo is public and carries this internal brief | Owner makes it private, or moves the internal material out of history (rules header) |
| Public title and "Tormai" cultural check | Clearance search and attorney review before any public step; fallbacks Tormun / Torvai (clans §13 Q7) |
| Higgsfield credits reset monthly; next grant uncertain | Spend P0 3D first; P1 roster depends on the grant; if unfunded, the third hero slot is dropped (slice-plan §2.3) |
| Audio costs unmeasured | Probe first; VO and music before SFX; CC0 for generic SFX (art bible §11) |
| Contested camps leave heroes under-levelled | Planned (§7); per-faction hero-2 metric in M4; fallback camp pair (slice-plan §1.14) |
| Footprint change touches the map and the kits | M1 re-validation of the seam gap, chokes, wall-offs, the Den coverage and the inn clearance; kit and architecture updates |
| Balance between the two slice factions | Scripted AI-vs-AI sets in M4 (40 seeds); tuning flags listed in each faction doc §13 |
| Unverified reference behaviours (XP-share radius, leash, recall radius, proc distribution) | Kept as data switches; verify from footage (rules §23) |

---

## 16. Document index

| Document | Owns |
|---|---|
| [gdd.md](gdd.md) (this file) | Vision, pillars, legal approach, factions at a glance, slice scope summary, synthesis decisions, index |
| [slice-content.json](slice-content.json) | Machine-readable slice content: ids, names, roles, key stats, abilities, items, creeps, camps, map landmarks |
| [rules.md](rules.md) | Every global rule and constant (economy, heroes, combat, status effects, vision, creeps, neutrals, controls, AI, `data/factions.json` constants, verification tests) |
| [factions/kingdom.md](factions/kingdom.md) | Brennmark: identity, look, voice, roster, heroes, buildings, upgrades, build order, slice subset |
| [factions/clans.md](factions/clans.md) | The Tormai: the same, plus the cultural-respect rules |
| [factions/sylvan-and-deathless.md](factions/sylvan-and-deathless.md) | Glaermere and the Long Wake at roster level (later milestones) |
| [neutrals.md](neutrals.md) | Creep families and camps, items and drop tables, neutral buildings and heroes, critters |
| [art-and-audio-bible.md](art-and-audio-bible.md) | How everything looks and sounds: style, palettes, team colours, silhouettes, prompts, terrain, UI art, voice, SFX, music |
| [slice-plan.md](slice-plan.md) | The slice map (Wether Downs), the asset list and budgets, the 3D bake-off, milestones M1–M5, risks |
| [juice-bible.md](juice-bible.md) and [juice/](juice/) | Game feel: combat, economy and buildings, heroes and VFX, world and atmosphere, UI, camera and audio |
| [../research/README.md](../research/README.md) | Research index and key decisions (camera, art, audio, mechanics, tech, pipeline, IP) |
| [../research/ip-safety.md](../research/ip-safety.md) | Legal map, banned names and lines, the distinctness rubric, the name risk, checklists |
| [../research/gameplay-mechanics.md](../research/gameplay-mechanics.md) | Reference numbers and why the genre plays as it does (§11), reuse vs copy (§12) |
| [../research/visual-art-direction.md](../research/visual-art-direction.md), [audio-direction.md](../research/audio-direction.md), [ai-asset-pipeline.md](../research/ai-asset-pipeline.md), [godot-rts-tech.md](../research/godot-rts-tech.md), [video-references.md](../research/video-references.md) | Research behind the art, audio, pipeline and engine choices |
| `docs/architecture.md`, `docs/asset-ledger.md` | Engine architecture; the generation ledger (provenance of every asset) |
| `tools/ip/` | `check_banned_terms.py`, `banned_terms.txt`, `banned_ui_terms.txt`, `check_value_echo.py`, `value_echo_reference.json` |
