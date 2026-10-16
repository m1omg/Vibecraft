# Faction designs (roster level): `sylvan` (Glaermere) and `deathless` (the Long Wake)

*Design date: 2026-10-16. Status: roster-level proposal for **later milestones** (full game). Neither faction is in the
vertical slice, which is kingdom vs clans. Faction ids: **`sylvan`** and **`deathless`**; data prefixes are `sylvan_` and `deathless_`.*

**Read with:**
- `docs/research/ip-safety.md`: §0, the §2 banned lists and the §3.2 rubric.
- `docs/research/gameplay-mechanics.md`: §11–§13.
- The two full faction docs, `kingdom.md` and `clans.md`. Every name, theme, palette and ability below was checked
  against both docs to avoid collisions. For example, the clans own hospitality comedy, weather metaphors, dust and blind effects,
  "Updraft", ancestor stones and doubled-vowel names, so this doc avoids all of them.

**Brief, restated.** Gameplay, structure and feel stay as close to Warcraft III as possible. A fan should name each unit's
job and the build-order logic at a glance: the forest-elf race and the undead-plague race. All expression is ours:
names, looks, palettes, emblems, culture, voices and lore.

**Depth.** This doc is about a third as deep as `kingdom.md`. It covers identity, look, signature mechanics, a full role
roster with numbers, four heroes, buildings and tiers, and voice. Per-rank unit ability tables, upgrade costs, build
orders and VO scripts get written when each faction enters production.

**Global rules apply unchanged** (mechanics §13.1–§13.2):
- Start with 500 gold / 150 lumber at 08:00. Food cap 100. Upkeep keeps 100 / 70 / 40 % of gold at 0–50 / 51–80 / 81–100 food.
- Hero rules: XP table, 3 abilities + an ultimate at level 6, STR/AGI/INT formulas, 6 item slots, at most 3 heroes, altar revive.
- 480 s day/night cycle and the damage matrix.

**Conventions** follow `kingdom.md`:
- Distances in metres, speeds in m/s, sight as day / night in metres.
- Attack types Blade, Pierce, Siege, Arcane, Heroic, Spell, Pure. "G+A" means the attack hits ground and air.
- **FE** marks a functional equivalent of a WC3 ability. **Orig** marks an original mechanic.
- Production tags:
  - **[B]** biped: AI mesh plus the bpy auto-rig.
  - **[P]** procedural: bpy parts with rigid or vertex animation, no rig.
  - **[C]** creature: AI mesh with rigid-segment procedural motion, because quadrupeds and flyers rig poorly.
  - **[V]** VFX only.

---

# Part A: `sylvan`, Glaermere

## A0. At a glance

| | |
|---|---|
| **Display name** | **Glaermere** (say *GLAIR-meer*). Long form: "the Thousand Meres" |
| **People** | **the Glaer** (singular "a Glaer", adjective "Glaerish"). A forest-elf people of the northern lake-forests |
| **Emblem** | **The Kept Light**: a tall amber teardrop, point up, crossed by one charcoal bark-dash, between two downward birch leaves, on lichen sage |
| **Motto** | "Waste no summer." |
| **Cultural inspiration** | Northern European lakeland forests: prehistoric pile-dwellings on stilts, birch-bark craft (boxes, shoes, shingles), Baltic amber working, resin tapping and tar-burning, stilted storehouses, plucked box-zithers, alternating-voice chant |
| **Palette** | Lichen sage and birch white, with charcoal bark-dashes and amber glow. No violet, teal, silver, red or gold |
| **WC3-derived mechanic (the one allowed)** | **Tapping**: workers harvest lumber without felling trees, shown as resin tapping with spigot and pail (§A3.1) |
| **Original mechanics** | **Sunstore**: lodges and towers bank daylight and burn it as "noonlight" through the night (§A3.2). **Stilt-built**: buildings may stand in shallow water |
| **Play pattern** | A fragile, fast, ranged-heavy army with the best anti-air and dispel. Siege is weak early. Strong by day and around its lanterns at night; weak when caught on the march at night or when burst down |
| **WC3 role mirror** | The forest-elf race: wisp-like worker, archer, bouncing skirmisher, bolt siege, anti-magic dryad role, shape-changing healer, debuff druid, giant tank, anti-air flyer, faerie-dragon role, heavy air. Four heroes in the archer-priestess, grove-druid, mana-burning exile and assassin roles |

## A1. Identity

**Names.**
- **Glaer** comes from Old English *glǣr*, "amber, resin". It also suggests "glare", fitting a people who hoard light. *Mere* means lake.
- Neither word uses a Blizzard pattern: no *-dorei*, *Kal-*, *Quel-*, *Thal-* or *Sil-*, and no moon, night, star, shadow or "sun-well" compounds.
- The UI never says "elf". Lore text may say "the elf-folk of the meres" once, as a description.

**Naming rules.**
- Units and buildings get English nature-craft compounds: Larkbow, Stilt Larder, Glare Post.
- Personal names are short invented given names with a soft ending (*-e, -i, -ve*) plus an English light or craft epithet, e.g. *Tieve Brightstring*.
- No apostrophes and no doubled-vowel names, because the clans use those.
- No real Finnic or Baltic deities, epic heroes or sun-signs.

**Emblem rules.**
- Read test at 24 px: "a drop with a bar".
- Banners are tall, narrow birch-white streamers with charcoal dashes, hung from carved poles.
- **Never** use a crescent, star, owl, tree silhouette, rayed sun, sun-cross or other folk sun-sign, phoenix, or red-and-gold colours.
- No sun disc either, because the clans' emblem is a saffron disc.

**Lore (original).**

> North of Brennmark the land breaks into a thousand dark lakes ringed with white birch and golden larch. This is
> Glaermere, and the Glaer live above its water in stilt-towns joined by plank walks. Their nights are long and their
> winters longer. Long ago a winter that did not lift for a generation taught them one lesson: *waste no summer*. Every Glaer
> child learns to tap the larches for resin, set the resin into amber, and shut daylight inside it like a fly in amber. So the
> lantern-cages of their lodges burn noon through the darkest night. The Glaer are bright, unhurried and a little smug about all this.
> They never cut a living tree (the great beavers do that, and are paid in songs). They tell the hour by how much light is left,
> and they take shade as a personal insult. Now smoke from the lowland wars dims their summers, and from the south a grey
> pall is creeping up the rivers toward the meres. The Glaer have opened their shutters.

## A2. Visual identity

**Silhouette rules** (upper-third identity, art doc §7.1):

1. **Leaf-tip hoods.** Stiff birch-bark hoods sweep **backward** into a long leaf point behind the head. Seen from the
   −56° camera, the read is a teardrop trailing behind the unit. WC3 forest elves have none, and kingdom kettle-hat discs
   and clans cones point the other way.
2. **Bark-scale capelets.** Overlapping birch-bark shingles form a short flared cone over the shoulders. The read is a pale ring with charcoal dashes.
3. **Amber lanterns.** Every unit carries one glowing amber point: hung from a bow tip, a staff, a yoke or a gondola.
   These are the faction's night read.
4. **Bodies.** Tall and long-limbed, with chunky hands, feet and weapons. Ears are long and **droop down and back like birch leaves**,
   never huge and upswept. Skin is warm birch-cream with charcoal freckle-dashes across the cheekbones and forearms.
   Hair runs from flax to amber, and eyes are amber. No violet or blue skin, and no blindfolds or tattoos.
5. **Weapons.** Long laminated birch bows, sling-staffs, punt poles, tapping mallets and fishing gaffs.
   **No glaives or crescent blades.**
6. **Creatures are lake-forest animals, not WC3's.** A giant beaver, a giant flying squirrel and amber fireflies.
   No owls, cats, deer-bodies, hippogryphs, chimaeras or dragons.

**Palette** (albedo targets):

| Role | Name | Hex | Where |
|---|---|---|---|
| Mass 1 | Lichen sage | `#8DA27A` | Nettle-cloth tunics, leggings, roof moss trims |
| Mass 2 | Birch white | `#E9E4D6` | Hoods, capelets, bows, roof shingles |
| Pattern | Charcoal dash | `#2F2C2B` | Horizontal dashes on every birch surface; skin freckle-dashes |
| Wood | Tarred brown | `#3A2C22` | Stilts, hulls, rope, sledges |
| Skin | Birch cream | `#E3D2BC` | |
| Accent | Amber | `#C9781A` | Solid amber beads, arrow nocks, lantern glass by day |
| VFX (HDR) | Noon amber | `#FFB547` | Lanterns at night, noonlight, spells |

Rules:
- Sage and birch white are the two masses. The charcoal dash is the faction's pattern read.
- Amber stays **small and translucent**, so it does not compete with the clans' saffron felt mass.
- Team colour goes on hood linings, bow-grip wraps, capelet edges, banner streamers and roof-ridge pennants.

**Materials.** Birch bark (white with black dashes), amber and resin (glossy only as painted highlights), nettle cloth, tar-blackened wood,
woven withies, river stone. No silver, moonstone or living-tree wood.

**Architecture: "stilts and gables".**
- Every building stands on **tarred stilts** (1–1.5 m), joined by plank walks.
- **Steep two-pitch roofs** of birch-bark shingles (60°). The gable boards cross at the peak and are carved into upturned leaf tips.
- An **amber lantern-cage** hangs under each gable.
- **Construction verb: "woven".** A withy lattice frame rises, then bark shingles flake on from the bottom up (`build_progress` shader).
- **Tier growth of the hall:**
  - **Stilt Lodge:** one long-house.
  - **Lantern Lodge:** adds a second storey and a large lantern-cage.
  - **Amber Lodge:** three roofs around an open cage holding a huge amber "noon-stone".
- **Never** living trees, tree-shaped buildings, walking or uprooting buildings, or wells. The silhouette contrasts with
  kingdom onion domes, clans yurt domes and Wakeful mounds.

**Squint-test risks** (internal audit; WC3 names appear only here):

| Glaer design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Larkbow | Night-elf archer | **Medium** (an elf woman archer is a genre staple) | Leaf-tip hood, bark capelet, lantern on the bow, sage and birch palette, drooping ears; no purple, no moon motifs |
| Lark Captain | Priestess of the Moon | **Medium** (archer heroine) | On foot, no big-cat mount, no owl, no moon. Lark-feather crest; the ult makes daylight, not falling stars |
| Thicket Weaver | Keeper of the Grove | **Medium** (druid hero) | Old man on two legs: **no antlers, no deer body, no glowing staff**. A huge withy back-loom is his read |
| Lampbreaker | Demon Hunter | **Medium** (mana-burning exile) | Eyes open (no blindfold), no tattoos, no twin blades, no green fire, no transformation. Punt pole and a broken lantern gauntlet |
| Stoneskipper / Ambermail / Woodgnaw | Huntress / Dryad / Mountain Giant | Low | Biped runner with a sling-staff (no cat, no glaive); biped in amber-lacquered bark (no deer body); a beaver (no rock giant) |
| Treeglider / Glimmerswarm / Thistleship | Hippogryph / Faerie Dragon / Chimaera | Low | Flying squirrel; firefly swarm; floating thistle-down balloon |
| Stilt Lodge | Tree of Life | Low | Gabled stilt house, never a tree |

## A3. Signature mechanics

### A3.1 Tapping (the one WC3-derived mechanic, presented differently)

| | WC3 forest-elf worker | Glaer Tapster |
|---|---|---|
| Harvest | A glowing spirit hovers at a tree; the tree is never felled | A biped elf knocks a **spigot** into the trunk and catches resin in a pail. The tree is never felled; tapped trees show amber drips and a cup |
| Yield | 5 per trip | **8 per trip**, 1 lumber per 1.0 s; drop-off at a Lodge or the Resinworks |
| Per tree | Several workers may share a tree | **One Tapster per tree** |
| Woodline | Never recedes | Never recedes either. Glaer cannot open new paths by harvesting. Only Woodgnaw (**Fell**) and Springbough shots remove trees |
| Presentation | Hovering glow, chime | Mallet *tok-tok*, a resin "plink" into the pail, honey-coloured drip decal |

Glaer drop the rest of the forest-elf set: workers living inside the gold mine, walking and uprooting buildings,
night-only regeneration, night invisibility, moon-energy supply wells, and the self-destructing dispel worker.

### A3.2 Sunstore and noonlight (original)

| Rule | Value |
|---|---|
| Charge | Each Lodge (any tier) and each Glare Post banks daylight: **+1 charge per 20 s of day**. Capacity: Lodge **12**, Glare Post **6** (research *Lantern Glass*: +4 each) |
| Burn | From dusk, a charged lantern burns **1 charge per 20 s** and projects **noonlight**: Lodge radius **14 m**, Glare Post **10 m**. A full day fills a Lodge for exactly one full night (240 s ÷ 20 s = 12 charges) |
| Inside noonlight | Glaer units count as **in daylight**: day sight, **+1 HP/s**, and day-keyed abilities stay on (Larkbow *Warm Strings*). **Enemy invisible units inside are revealed.** No other effect on enemies. Noonlight does not wake creeps |
| **Open the Shutters** (Lodge ability) | Spend **4 charges**: a **16 m** noonlight anywhere within 30 m of the Lodge for **15 s**, day or night (by day it only reveals). Cooldown 60 s |
| Presentation | Lantern-cages glow honey-orange (HDR) and warm motes drift. Inside the circle the night grade lifts to the day grade (a shader light mask). Our own "shutter clack" and a two-note rising chime |
| Counterplay | Kill Glare Posts, fight away from lanterns, and catch Glaer armies on the march at night |
| Why it is ours | WC3's forest elves are **night-aligned**. The Glaer are **day-aligned** and carry daylight into the night. No WC3 race projects daylight zones |

**Stilt-built** (minor, original): every Glaer building may be placed in **shallow water**. Deep water and cliffs are still
excluded. Land units walk shallow water normally, so this gives placement freedom, not protection.

## A4. Economy and faction rules

| Rule | Value |
|---|---|
| Gold | Walked back to a Lodge, 10 per trip (global) |
| Lumber | Tapping (§A3.1) |
| Food | Stilt Lodge 10 → Lantern Lodge 12 → Amber Lodge 14. **Stilt Larder +10** (140 g / 40 l, 45 s) |
| Construction | Woven. One Tapster builds; a second may assist (+50 % rate). *Resin Seal* repair: autocast, default off, costs 30 % pro rata |
| Night | Sunstore only; no other night modifiers |
| Shop item hook | **Bottled Noon** (Trinket Stall, 90 g): a 12 m noonlight at a point for 30 s |

## A5. Unit roster

### A5.1 Roles (one line each)

| id | Unit | WC3 role slot | Look (upper-third read first) | Key ability | Prod. |
|---|---|---|---|---|---|
| `sylvan_tapster` | **Tapster** | Worker | Young elf, leaf-tip hood, wooden yoke with two resin pails, tapping mallet, hand lantern | Taps trees (§A3.1); **Hang Lantern**: a 10 m vision ward for 60 s, cooldown 45 s | [B] |
| `sylvan_larkbow` | **Larkbow** | T1 ranged (archer) | Tall archer, laminated birch longbow taller than she is, amber-bead nocks, bark capelet | **Warm Strings** (passive): +15 % attack speed in daylight or noonlight. *Long Draw* research: +1.4 m range | [B] |
| `sylvan_stoneskipper` | **Stoneskipper** | T1 fast skirmisher with a bouncing attack | Barefoot runner in a bark-scale kilt, long sling-staff with a forked amber-beaded tip, stone pouch | **Skip** (passive): each stone skips to a second enemy within 3 m behind the target for 50 % damage. *Skipping Lore* adds a third skip at 25 % | [B] |
| `sylvan_springbough` | **Springbough** | Siege (bolt thrower) | Bark sledge on runners with a bent-larch spring arm and a resin pot, hauled by two Tapsters (reused mesh) | Can attack trees. *Pitch Pot* research: impacts leave sticky resin for 5 s (−30 % move speed) | [P] |
| `sylvan_ambermail` | **Ambermail** | Spell-immune anti-caster (dryad slot) | Elf in glossy amber-lacquered bark plates with a resin-dart sling | **Spell immune**; darts slow 15 % (FE). **Scrape Clean** (autocast, 50 mana): removes buffs in 3 m, 200 damage to summons (FE) | [B] |
| `sylvan_sapsinger` | **Sapsinger** | Healer that changes form (claw-druid slot) | Stout singer with a sap-bucket staff and a long choir scarf | **Warm Sap** (autocast heal over time, 300 HP over 12 s, 75 mana). Journeyman: **Chorus** (+20 % damage to allies within 8 m for 30 s). Master: **Bark Coat** (a heavy melee form wrapped in bark plates, **not an animal**) | [B] |
| `sylvan_hazeweaver` | **Hazeweaver** | Debuff and disable caster (talon-druid slot) | Tall cone hat with a long midge-net veil, smoking birch-tar censer | **Midge Haze** (autocast, 35 mana): −4 armour and revealed for 60 s (FE). Journeyman: **Fog Bank** (Orig): a 6 m fog for 15 s; units inside cannot be targeted by ranged attacks from outside. Master: **Seedspin**: lifts a non-hero for 6 s, disabled and untargetable (FE) | [B] |
| `sylvan_woodgnaw` | **Woodgnaw** | T3 giant tank | Shaggy giant beaver with a bark-shingle saddle-roof; a lodge-keeper rides and sings | **Tail Slap**: taunts within 5 m for 4 s, cooldown 12 s. **Fell** (Orig): chews down a tree in 3 s and gains +3 armour for 30 s. *Thick Pelt* research: −25 % Pierce damage taken | [C] |
| `sylvan_treeglider` | **Treeglider** | Anti-air flyer | Giant flying squirrel with a small elf rider and lantern | **Dive** (Orig): after 3 s without attacking, the next hit deals +60 % and slows the air target 50 % for 2 s. Attacks air only | [C] |
| `sylvan_glimmerswarm` | **Glimmerswarm** | Magic-immune anti-caster flyer | Drifting cloud of amber fireflies around a faint lantern core | **Spell immune.** **Scatter** (autocast): on taking damage, untargetable for 1.5 s, cooldown 8 s (FE). **Snuff** (passive): attacks burn 8 mana | [V] |
| `sylvan_thistleship` | **Thistleship** | T3 heavy air vs ground and buildings | Floating giant thistle-down seed with a wicker gondola; two crew drop resin firepots | *Burning Resin* research: +50 % vs buildings, plus 4 s of burning ground (10 damage/s) | [P] |

### A5.2 Stats

| Unit | Built at (needs) | Gold / lumber / food | Time (s) | Lvl | HP | Mana | Armour | Attack, damage | CD (s) | Range (m) | Hits | Speed (m/s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tapster | Lodge | 70 / 0 / 1 | 15 | 1 | 210 | – | 0 Medium | Blade 4–6 | 2.0 | 0.6 | G | 3.1 |
| Larkbow | Fletchery | 125 / 10 / 2 | 19 | 2 | 300 | – | 0 Medium | Pierce 15–18 | 1.5 | 8.0 (9.4) | G+A | 4.4 |
| Stoneskipper | Fletchery (Resinworks) | 185 / 20 / 3 | 28 | 3 | 580 | – | 1 Medium | Blade 18–22 | 1.8 | 3.5 | G | 5.0 |
| Springbough | Fletchery (Lantern Lodge, Resinworks) | 210 / 65 / 3 | 36 | 3 | 400 | – | 2 Heavy | Siege 58–70, splash 1.0 / 2.0 m | 3.6 | 15.0 (min 3.5) | G, trees | 3.1 |
| Ambermail | Singers' Hall | 150 / 50 / 3 | 30 | 3 | 450 | 200 | 0 Light | Pierce 13–16 | 1.8 | 6.0 | G+A | 4.7 |
| Sapsinger | Singers' Hall | 190 / 60 / 3 | 33 | 3 | 420 | 225 | 0 Unarmored | Arcane 10–12 | 1.9 | 6.0 | G+A | 4.4 |
| ↳ Bark Coat form | (Master, 3 s to switch) | – | – | 3 | 870 | 225 | 3 Heavy | Blade 24–30 | 1.6 | melee | G | 4.0 |
| Hazeweaver | Wind Perch | 140 / 25 / 2 | 28 | 2 | 320 | 250 | 0 Unarmored | Arcane 9–11 | 1.8 | 6.25 | G+A | 4.4 |
| Woodgnaw | Singers' Hall (Amber Lodge) | 340 / 90 / 6 | 50 | 6 | 1450 | – | 2 Heavy | Blade 26–34 | 2.0 | 1.0 | G | 3.4 |
| Treeglider | Wind Perch | 150 / 20 / 2 | 22 | 2 | 450 | – | 0 Light | Pierce 18–22 | 1.5 | 1.5 | A | 5.6 (fly) |
| Glimmerswarm | Wind Perch | 155 / 25 / 2 | 25 | 2 | 400 | – | 0 Light | Arcane 12–15 | 1.6 | 4.5 | G+A | 5.2 (fly) |
| Thistleship | Thistle Mooring | 330 / 90 / 5 | 50 | 5 | 1050 | – | 1 Light | Siege 70–84, splash 1.25 / 2.5 m | 3.0 | 2.0 (drops below) | G | 3.6 (fly) |

Sight is 21.9 / 12.5 m for all units except the Tapster (12.5 / 9.4). Noonlight raises night sight to the day value.

## A6. Heroes

Global hero rules apply. Heroes are trained at the **Calling Pier**: they arrive across the lake by boat.

| Hero (id) | WC3 role match | Primary; STR / AGI / INT (+ per level) | HP / mana at L1 | Range; speed | Look (one oversized prop) |
|---|---|---|---|---|---|
| **Lark Captain** (`sylvan_hero_lark_captain`) | Archer priestess (AGI ranged, ranged aura) | AGI; 17 (+1.8) / 21 (+2.3) / 16 (+1.9) | 525 / 240 | 8.4 m; 4.7 | Tall archer, a lark-feather crest on her leaf hood, and a **huge birch longbow strung with amber beads**. Example name: *Tieve Brightstring* |
| **Thicket Weaver** (`sylvan_hero_thicket_weaver`) | Grove druid (INT roots and summons) | INT; 16 (+1.8) / 13 (+1.2) / 21 (+3.0) | 500 / 315 | 7.0 m; 4.4 | Stooped old elf with a **towering withy back-loom** above his head and a hooked weaving staff. No antlers. Example name: *Senne Barkhand* |
| **Lampbreaker** (`sylvan_hero_lampbreaker`) | Mana-burning exile (AGI melee) | AGI; 20 (+2.1) / 22 (+2.4) / 15 (+1.6) | 600 / 225 | 1.2 m (pole); 4.8 | Scorched exile whose hood is half burned away, with a **shattered lantern-cage gauntlet** leaking light and an iron-shod punt pole. Example name: *Kesse the Unlit* |
| **Reedstalker** (`sylvan_hero_reedstalker`) | Assassin (AGI melee, mobility) | AGI; 18 (+2.0) / 22 (+2.5) / 14 (+1.5) | 550 / 210 | 0.9 m; 4.9 | Slim hunter under a **tall reed-sheaf cloak** with a long fishing gaff and a dart pouch. Example name: *Ivve Stillwater* |

**Kits** (ranks 1 / 2 / 3; mana; cooldown). At most 2 of the 4 abilities may be FE.

| Hero | Q | W | E | R (ultimate, level 6) | FE |
|---|---|---|---|---|---|
| Lark Captain | **Farshot** (unit, 16 m): 90 / 150 / 210 Spell damage, **+50 %** if the target is more than 10 m away. 85 mana, 9 s. *Orig* | **Split Volley** (self): the next 3 / 4 / 5 attacks each split to 2 extra enemies within 4 m at 50 % damage. 60 mana, 14 s. *Orig* | **Bowyer's Hum** (aura, 9 m): allied ranged attackers deal +8 / 16 / 24 % damage. *FE (ranged aura)* | **High Noon** (point within 12 m, 12 m radius, 20 s): daylight for allies inside (day sight, +15 % attack speed). Enemies inside are revealed and deal −15 % damage. Ends in a 150 Spell flash. 150 mana, 150 s. *Orig* | **1** |
| Thicket Weaver | **Rootbind** (unit, 9 m): roots a ground unit 2 / 3 / 4 s (heroes 1 / 1.5 / 2) and deals 15 / 20 / 25 damage/s. 75 mana, 9 s. *FE (root)* | **Thatch Screen** (point, 9 m): a 6 m wicker screen for 8 / 11 / 14 s that **blocks enemy missile attacks** crossing it. Units walk through it. 80 mana, 18 s. *Orig* | **Seed Spit** (point, 8 m): plants 1 / 2 / 3 **Briar Saplings** for 30 s (stationary, 300 HP, Pierce 10–12, range 5 m, level 1, 50 % XP). 110 mana, 25 s. *FE (summon)* | **Old Thicket** (9 m ring around a point within 10 m, 20 s): a ring of birches **blocks pathing**, leaving one 2 m gap facing the Weaver. Allies inside regenerate 12 HP/s; Tapsters may tap the ring. 175 mana, 160 s. *Orig* | **2** |
| Lampbreaker | **Drink the Light** (unit, 4 m): burns 60 / 120 / 180 mana, deals that much Spell damage, and she gains 50 % of it. 50 mana, 8 s. *FE (mana burn)* | **Corona** (toggle): 12 / 20 / 28 Spell damage/s to enemies within 2.5 m; drains 6 mana/s. *FE (damage aura)* | **Punt Vault** (point, 3–9 m): vaults over units and one cliff level. Landing deals 40 / 80 / 120 and knocks back 1.5 m. 60 mana, 12 / 10 / 8 s. *Orig* | **Broken Lantern** (self): for 30 s, all mana she burns is stored. Recast, or let it expire, to release it in an 8 m flash dealing **1.5 ×** the stored amount (cap 600) and dazing (−30 % move and attack speed) for 4 s. 125 mana, 120 s. *Orig* | **2** |
| Reedstalker | **Reed Darts** (self, 6 m): up to 6 nearest enemies take 60 / 110 / 160 Spell damage and −20 % move speed for 2 s. 85 mana, 9 s. *FE (around-self volley)* | **Slip Under** (point, 10 m; must start or end in shallow water or within 2 m of a tree): instant reposition; the next attack deals +40 / 60 / 80. 50 mana, 12 / 9 / 6 s. *FE (short teleport, restricted)* | **Reed Ambush** (passive): her first attack on a target that has not damaged her in the last 5 s deals +60 / 100 / 140 % and roots it for 1 s. *Orig* | **Silent Mere** (point within 10 m, 9 m radius, 8 s): enemies inside cannot cast spells or use items and have −3 armour. She gains +30 % move speed inside. 150 mana, 120 s. *Orig* | **2** |

No Glaer hero uses its WC3 counterpart's ultimate. That removes the most recognisable signature from each kit.

## A7. Buildings and tech tiers

```
Stilt Lodge (T1) ──► Lantern Lodge (T2, needs Calling Pier) ──► Amber Lodge (T3, needs Resinworks)
│                         │                                          │
├─ Stilt Larder (+10 food)├─ Singers' Hall ── Ambermail, Sapsinger   ├─ Singers' Hall ── Woodgnaw
├─ Calling Pier ── heroes ├─ Wind Perch ── Treeglider, Hazeweaver,   ├─ Thistle Mooring ── Thistleship
├─ Fletchery ── Larkbow, Stoneskipper [Resinworks],    Glimmerswarm  └─ Master trainings, level-3 upgrades
│               Springbough [T2 + Resinworks]
├─ Resinworks ── upgrades, lumber drop-off ── Glare Post (tower)
└─ Trinket Stall ── items (stock grows with tier)
```

Every building has Fortified armour 5.

| Building (id) | WC3 role slot | Needs | Gold / lumber | Time (s) | HP | Food | Function |
|---|---|---|---|---|---|---|---|
| **Stilt Lodge** (`sylvan_stilt_lodge`) | Hall T1 | – | 380 / 190 | 160 | 1500 | +10 | Tapster; gold and lumber drop-off; Sunstore 12; *Open the Shutters* |
| **Lantern Lodge** | Hall T2 (upgrade) | Calling Pier | +300 / 200 | 130 | 2000 | +12 | Tier 2, hero 2 |
| **Amber Lodge** | Hall T3 (upgrade) | Lantern Lodge, Resinworks | +340 / 220 | 140 | 2500 | +14 | Tier 3, hero 3 |
| **Stilt Larder** | Supply | – | 140 / 40 | 45 | 450 | +10 | A stilted storehouse; may stand in shallow water |
| **Calling Pier** | Hero altar | – | 180 / 50 | 60 | 900 | – | Trains and revives heroes |
| **Fletchery** | Barracks | – | 170 / 60 | 60 | 1300 | – | Larkbow, Stoneskipper, Springbough. Research: *Long Draw*, *Skipping Lore*, *Pitch Pot* (each T2) |
| **Resinworks** | Smithy and lumber mill | – | 150 / 60 | 60 | 1100 | – | Lumber drop-off. *Hardened Points* (+10 % damage per level for non-caster attacks), *Resin Varnish* (+2 armour per level), 3 levels each; *Lantern Glass* (T2: Sunstore +4) |
| **Singers' Hall** | Caster lodge with the giant | Lantern Lodge | 165 / 120 | 65 | 1100 | – | Ambermail, Sapsinger; Woodgnaw at T3. Sapsinger Journeyman (T2) and Master (T3); *Thick Pelt* (T3) |
| **Wind Perch** | Air lodge | Lantern Lodge | 160 / 150 | 60 | 1050 | – | Treeglider, Hazeweaver, Glimmerswarm. Hazeweaver Journeyman (T2) and Master (T3) |
| **Thistle Mooring** | Heavy-air roost | Amber Lodge | 160 / 200 | 70 | 1150 | – | Thistleship; *Burning Resin* |
| **Glare Post** | Tower | Resinworks | 110 / 50 | 40 | 480 | – | Pierce 18–22, CD 1.1 s, 10.0 m, G+A; Sunstore 6 (10 m noonlight). Static, never walks |
| **Trinket Stall** | Faction shop | – | 130 / 30 | 60 | 480 | – | Potions, *Lake Whistle* (recall to a Lodge after 3 s), *Bottled Noon* |

| Tier | Unlocks |
|---|---|
| T1 Stilt Lodge | Tapster, Larkbow, Stoneskipper, Glare Post; hero 1; level-1 upgrades |
| T2 Lantern Lodge | Springbough, Singers' Hall, Wind Perch, Ambermail, Sapsinger, Hazeweaver, Treeglider, Glimmerswarm; hero 2; Journeyman trainings; level-2 upgrades |
| T3 Amber Lodge | Woodgnaw, Thistle Mooring and Thistleship, Master trainings (Bark Coat, Seedspin); hero 3; level-3 upgrades |

## A8. Voice and music

**Voice personality: bright, unhurried light-hoarders.**
- They rate everything by how much light it has, tell the time in "lights left", and take shade personally.
- They are a little smug about their summers and quietly terrified of the dark.
- Delivery is soft and even, with a lilting chant cadence. **No faux Finnish or Baltic accent.**
- Their metaphors are light, resin, lanterns and lakes. Never weather (a clans trait), hospitality or ledgers.
- Each unit gets one tic. For example, the Tapster counts drips; the Woodgnaw rider sings to the beaver mid-line.
- Annoyed lines avoid the word "poke".

**Sample lines** (original; check against the WC3 night-elf quote page before recording):
- Larkbow (What): *"Mm? Step aside, friend. You're standing in my light."*
- Tapster (Annoyed, last in sequence): *"Every tap on my shoulder dims me a little. Keep going and I'll be dusk."*

**Music:**
- Plucked box-zither, birch-bark horn, wooden clappers, soft frame drum and bowed lyre.
- An alternating two-voice wordless chant. Lilting 5/4 and 6/8, Aeolian or Dorian, 72–96 BPM.
- **Avoid** an airy solo female voice with harp and flute as the lead colour (the WC3 forest-elf sound).

## A9. Distinctness rubric (ip-safety §3.2; nearest WC3 race: the forest elves)

| Axis | WC3 forest elves | Glaermere | Differs? |
|---|---|---|---|
| 1. Silhouette | Huge upswept ears, crescent glaives, owls, antlers, big-cat mounts, walking tree buildings | Swept-back leaf hoods, bark capelets, lanterns, drooping ears; beaver, flying squirrel, thistle balloon; gabled stilt houses | **Yes** (required) |
| 2. Palette | Violet, teal, silver | Lichen sage, birch white with charcoal dashes, small amber | **Yes** |
| 3. Materials | Moonstone, silver, living wood, leaves | Birch bark, amber and resin, nettle cloth, tar, withies | **Yes** |
| 4. Culture | Moon cult, night, ancient temple ruins | Northern lakeland pile-dwellings, amber craft, resin tapping, day-keeping | **Yes** |
| 5. Signature mechanic | Non-felling wisps, mine entangling, uprooting, night stealth and regeneration, moon wells | Tapping (the one WC3-derived mechanic, re-presented) plus original Sunstore and Stilt-built | **Yes** (within policy) |
| 6. Names and voice | WC3 unit, hero and place names; solemn, mystic | All original; sunny, smug light-hoarders | **Yes** |

**Result: 6 / 6.** Residual risk: elf archers and a druid hero are genre staples. Run the squint test on every Larkbow and
Weaver concept before image-to-3D.

---

# Part B: `deathless`, the Long Wake

## B0. At a glance

| | |
|---|---|
| **Display name** | **The Long Wake** (UI: "Long Wake") |
| **People** | **the Wakeful** (singular "a Wakeful", adjective "Wakeful"). The risen dead of the old Great Houses, plus everyone they have since "adopted" |
| **Emblem** | **The Remembered Face**: a calm chalk-white mask with closed eyes above a terracotta offering bowl, inside a ring of five dried roses, on soot black |
| **Motto** | "No one is forgotten. No one is excused." |
| **Cultural inspiration** | Ancient Mediterranean funerary culture of extinct civilisations: Etruscan round tumulus tombs and painted tomb walls, terracotta sarcophagus lids with reclining figures, Roman ancestor-mask processions and patron households, rose-days for the dead, cinerary urns with head-shaped lids, double pipes and lyre. **Not** Egyptian (no mummies, pyramids or jackals), not Nordic or gothic, and no frost |
| **Palette** | Soot lacquer and terracotta, with chalk bone, grave-rose and tarnished silver; pale lamp-rose glow. No purple, cyan or toxic green |
| **WC3-derived mechanic (the one allowed)** | **The Pall**: a spreading ground layer that helps the Wakeful. It is the plague-ground idea, re-presented and softened (§B3.1) |
| **Original mechanic** | **Heirloom Masks**: fallen Wakeful drop their masks, and the next to pick one up inherits its rank (§B3.2) |
| **Play pattern** | Cheap, fast melee, sturdy siege and strong sustain on their own Pall. Veteran Lineage snowballs if they win trades. Weak to burst that kills before masks pass on, to fights far from Pall, and to mask denial |
| **WC3 role mirror** | The undead race: worker, invisible scout, fast cheap melee, ranged anti-air pinner, anti-air flyer that turns to stone, corpse-raising caster, curse caster, healing construct that becomes a flyer, siege cart, T3 heavy melee, heavy air. Four heroes in the dark-commander, cold-caster, noble-vampire and burrowing-tank roles |

## B1. Identity

**Names.**
- A *wake* is the vigil kept over the dead. The Long Wake is a vigil nobody has ended, and its people literally never sleep.
- The names use no Blizzard patterns: no Scourge, Forsaken, Lich, Necro-, Death Knight, Ghoul or Crypt.
- In-world, the faction is a federation of **Great Houses**, each led by its oldest masks. The UI uses "Long Wake" and "Wakeful".

**Naming rules.**
- Units and buildings get English funeral vocabulary: Sexton, Eulogist, Cenotaph, Columbarium.
- Personal names are invented Latinate names ending *-us / -a / -ia*, plus a house or funeral epithet, e.g. *Aulenus the Unfinished*.
- No real Roman or Etruscan people, no deities, and no liturgical words (requiem, mass, saint, abbot, last rites).

**Emblem rules.**
- Read test at 24 px: "a face over a bowl".
- Banners are horizontal "runner" cloths on T-poles, with tasselled ends.
- **Never** use skulls with horns, spikes, crowns, crosses or other religious symbols, purple, or a cyan glow.

**Lore (original).**

> Along the warm southern coast, the old Great Houses buried their dead in round hill-tombs. Each tomb had painted
> walls and a mask of the deceased hung by the door, so that no ancestor would ever be forgotten. The Houses took
> remembrance further than anyone intended. When the last heirs died, the families simply did not stop. Each House still
> walks behind its masks (patriarchs, dowagers, retainers and clients), unrolling a grey **Pall** before it like a carpet laid
> for a procession. Whoever falls beneath it is quietly entered in the family register. The Wakeful are not cruel. They are
> very old, very proud and entirely sleepless. By their reckoning, every field, river and kingdom from the coast to the northern
> lakes is "the family estate", currently overrun by trespassers. They call it the Long Wake: a funeral that, out of good
> manners, nobody has ever ended.

## B2. Visual identity

**Silhouette rules:**

1. **Oversized masks are the faction read.** Each unit type wears a mask about 1.4× head size with its own fixed expression:
   grinning servant, open-mouthed orator, disdainful dowager, stern general. The faces are gone, so the mask *is* the face.
2. **Lineage poles.** Units with Lineage (§B3.2) carry 1–3 small masks on a short pole behind the shoulder. This rank read is unique to the faction.
3. **Long draped shapes.** Shrouds, togas and runner banners give A-line silhouettes. Spirits have floating, tattered hems. Everyone stands
   **upright and processional**: no hunching, no crawling, and **no spikes anywhere**.
4. **Round, closed forms.** Urns, wheels, drum-mounds and sarcophagus boxes.
   **No spider bodies, stitched flesh, hooks and cleavers, gargoyles, wings, frost or skeletal horses.**

**Palette:**

| Role | Name | Hex | Where |
|---|---|---|---|
| Mass 1 | Soot lacquer | `#2B2426` | Shrouds, togas, cart and barge lacquer |
| Mass 2 | Terracotta | `#A9573B` | Masks, urns, roof tiles, sarcophagi, tomb half-columns |
| Light | Chalk bone | `#DCD0B9` | Bones, plaster masks, tumulus stone drums |
| Accent | Grave-rose | `#9E4F63` | Dried roses, ribbons, crest plumes (saturation ≤ 45 %, so pink and red team colours still read) |
| Metal | Tarnished silver | `#8C8A86` | Bells, coins, small fittings |
| Ground | Pall grey | `#6F6A66` with grave-rose flecks | The Pall layer |
| VFX (HDR) | Lamp-rose | `#FFC7D1` | Eyes behind the masks, spells, tomb-lamp flames |

Team colour goes on runner banners, mask ribbons, shroud hems, cart canopies and the barge's garlands.
**Not** purple, black-violet, cyan or green glows. **Not** the art doc's Blightmire corruption palette.

**Materials.** Fired terracotta, chalk plaster, black lacquer, heavy linen shrouds, dried flowers, tarnished silver, cut limestone.

**Architecture: "drums and mounds".**
- Buildings are **tumuli**: a low drum of chalk-stone blocks under a grassy dome of dead grass and rose-briar.
- A dark doorway is framed by two terracotta half-columns, with rows of urns and pairs of tall black cypress doodads.
- **Construction verb: "unearthed".** The ground splits, and the building rises from below as the Sexton digs. The `build_progress` reveal runs top-down from a sunken start.
- **Tier growth of the hall:**
  - **Wake Barrow:** one drum.
  - **Long Barrow:** an elongated mound with a painted frieze of processions.
  - **Grand Barrow:** three stacked drums crowned by a terracotta reclining couple.
- **Never** stepped pyramids, ziggurats, spiked towers, obelisks or purple stone.

**Squint-test risks** (internal audit):

| Wakeful design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Mourning Legate | Death Knight | **Medium** (dark armoured commander) | On foot (no skeletal horse), no runeblade, no blue glow, no skull helm. Rose-crested helm and a terracotta-faced shield |
| Urn Hearse | Meat Wagon | **Medium** (siege cart with grim cargo) | Black-lacquer funeral cart with urns and masks, **no corpses, no meat, no gore** |
| Imaginifer | Banshee | **Medium** (floating curse caster) | Ungendered, mask-faced standard-bearer with a pole of masks. No wailing, no streaming hair, no sheer ghost-woman |
| Retainer / Tombwalker / Shroudcaster | Ghoul / Abomination / Crypt Fiend | Low | Upright masked servant with a billhook; stone sarcophagus on stub legs; gaunt shrouded thrower |
| Drift-Shroud / Wake Barge | Gargoyle / Frost Wyrm | Low | Flying burial sheet; floating funeral boat |
| The Dowager / The Patriarch / Gravewright | Lich / Dreadlord / Crypt Lord | Low | Matriarch with a tall cap; patrician with a collar of masks (no bat wings); stonemason (no insect) |
| Barrows | Necropolis, Ziggurat | Low | Round grassy drum-mounds, never spikes or steps |

## B3. Signature mechanics

### B3.1 The Pall (the one WC3-derived mechanic, presented differently)

| | WC3 plague ground | The Pall |
|---|---|---|
| Look | Purple-black dead ground | A grey burial-cloth and grave-dust texture with dried rose-petal flecks. It **unrolls like a carpet** at 1 m/s from its source, and petals drift above it. Reuses the art doc's spreading-mask shader with our own textures |
| Sources | Hall, supply buildings, the cursed gold mine | Wake / Long / Grand Barrow (16 / 18 / 20 m), Columbarium (8 m), Cenotaph (6 m), Gravewright's *Raise Cenotaph*, and Sexton *Lay the Pall* (a 6 m patch for 90 s, cooldown 60 s) |
| Building rule | Hard: most buildings require it | **Soft:** build anywhere. Off-Pall buildings build 30 % slower and have −3 armour until Pall reaches them |
| Own units | Regenerate faster | Wakeful non-heroes +1.5 HP/s; heroes +2 HP/s |
| Enemies | No effect | **Enemy organic units on Pall get no natural HP regeneration.** Spells, items and fountains still heal |
| Removal | Recedes after its sources die | Rolls back at 1 m/s, starting 10 s after its source dies |

The Wakeful drop the rest of the undead set: the cursed gold mine, workers who summon a building and walk away,
melee units that double as lumberjacks, corpse-carrying wagons, supply buildings that turn into towers, and frost.

### B3.2 Heirloom Masks (original)

| Rule | Value |
|---|---|
| Drop | Every non-summoned Wakeful unit that dies drops its **mask** on the ground for **40 s**. Masks are visible to both players |
| Inherit | A Wakeful non-hero unit that walks over a mask takes it in 0.5 s. Its **Lineage** becomes the higher of its own and **the dead unit's Lineage + 1**, up to **3** |
| Lineage bonus | **+6 % max HP and +6 % damage per rank** (+18 % at rank 3). Ranks are titled *Heir*, *Elder* and *Venerable*, and shown as 1–3 masks on the back-pole |
| Deny | An enemy unit standing on a mask for 1.5 s **smashes** it: a terracotta crunch and a puff of petals |
| Hooks | Urn Hearse *Mask Cart* (stores 4 masks and hands them out); Imaginifer *Procession Standard* (+1 temporary Lineage); Legate *Roll Call* (raises masks as units); shop item *Spare Mask* |
| Why it is ours | WC3 uses corpses only to raise or eat. No WC3 race passes rank from the dead to the living |

## B4. Economy and faction rules

| Rule | Value |
|---|---|
| Gold | The Sexton digs at an ordinary mine and walks back 10 per trip. There is no mine-cursing step |
| Lumber | Sextons fell trees: 10 per trip, 1 per 0.8 s; drop-off at a Barrow or the Ossuary |
| Food | Wake Barrow 10 → Long Barrow 12 → Grand Barrow 14. **Columbarium +10** (150 g / 50 l, 45 s) |
| Construction | Unearthed. Up to 2 Sextons dig (+50 % rate for the second). *Re-mortar* repair: autocast, default off, costs 30 % pro rata |
| Night | No modifiers. The Wakeful never sleep, which is a voice and flavour point only |
| Corpses | Uses the global corpse rule (mechanics §13.1) for the Eulogist's *Late Guests* |
| Shop item hooks | **Spare Mask** (Grave Goods, 120 g): +1 Lineage on a unit. **Coin for the Ferry** (350 g): after 3 s, the hero and units within 6 m return to the nearest Barrow |

## B5. Unit roster

### B5.1 Roles (one line each)

| id | Unit | WC3 role slot | Look (upper-third read first) | Key ability | Prod. |
|---|---|---|---|---|---|
| `deathless_sexton` | **Sexton** | Worker | Lanky gravedigger with a gap-toothed terracotta grin-mask, long spade, grave lantern and soot smock | Digs gold, fells trees, unearths buildings. **Lay the Pall** (§B3.1) | [B] |
| `deathless_veiled_mourner` | **Veiled Mourner** | Invisible scout | A floating black veil around a small chalk mask | A Sexton **takes the veil** at the House of Masks (60 g, 10 s). Permanently invisible; sees invisible units within 9 m; no attack (FE) | [V] |
| `deathless_retainer` | **Retainer** | Fast cheap melee | Skeletal household servant in soot livery-shroud, blank smiling terracotta mask, billhook and a small round shield painted with the house mask | **Grief** (Orig, passive): +12 % attack speed for 8 s when an allied Wakeful dies within 6 m (stacks ×3). *Brisk Step* research: +0.7 m/s | [B] |
| `deathless_shroudcaster` | **Shroudcaster** | Ranged anti-air pinner | Gaunt shrouded figure with a satchel of weighted burial cloths; flings sharpened terracotta shards | **Burial Shroud** (autocast, cooldown 10 s): pins an air unit to the ground for 8 s (FE) | [B] |
| `deathless_drift_shroud` | **Drift-Shroud** | Anti-air flyer | An animated burial sheet with a chalk mask and tattered hem | **Lie in State**: drops as a heap of cloth; cannot move or attack; Heavy armour, spell immune, +15 HP/s (FE) | [V/P] |
| `deathless_eulogist` | **Eulogist** | Raise-the-dead caster | Dead orator in a toga with a scroll-roll and an open-mouthed speaking mask | **Late Guests** (75 mana): raises 2 skeletal guests from a corpse for 40 s (FE). Journeyman: **Dirge**: −25 % move and attack speed for 10 s (FE). Master: **Final Words** (Orig): marks an ally for 10 s; if it dies, it bursts for 150 Spell damage within 3 m and its mask drops at +1 Lineage | [B] |
| `deathless_imaginifer` | **Imaginifer** | Curse and spell-shield caster | Floating, ungendered standard-bearer in a rose-dyed shroud, holding a tall pole topped by a frame of masks | **Borrowed Face** (autocast): the target misses 30 % of attacks for 60 s (FE). Journeyman: **Lacquer Ward**: absorbs 300 spell damage for 60 s (FE). Master: **Procession Standard** (Orig): plants the pole for 30 s; Wakeful within 8 m gain +1 temporary Lineage | [B/P] |
| `deathless_canopic_urn` | **Canopic Urn** | Healing construct that can become a flyer | A floating waist-high terracotta urn whose lid is a sculpted head | **Ash-Balm** (autocast): heals 10 HP/s and restores 5 mana/s, split among allies within 6 m, paid from its own mana (FE). Master: **Uncork** turns it into **the Released**, a spiral of ash-rose smoke under the lid-head (FE) | [P] |
| `deathless_released` | **the Released** | Anti-magic heavy flyer | (see above) | Attacks burn 10 mana and dispel one buff per hit. It can absorb an area's buffs to regain mana | [V/P] |
| `deathless_urn_hearse` | **Urn Hearse** | Siege cart | Black-lacquered funeral cart with tall rear wheels, a sling arm and stacked urns, pushed by two Sextons (reused mesh) | **Mask Cart** (Orig): stores up to 4 dropped masks and hands them to Wakeful units within 3 m. Urns burst into grave-dust | [P] |
| `deathless_tombwalker` | **Tombwalker** | T3 heavy melee | A walking stone sarcophagus on stumpy legs. A reclining couple carved on the lid bicker as it walks | **Lid Slam** (Orig): every 4th attack splashes 1.5 m and stuns 0.5 s. *Grave-Damp* research: 4 damage/s to enemies within 2.5 m (FE) | [P] |
| `deathless_wake_barge` | **Wake Barge** | T3 heavy air | A long, narrow black-lacquered funeral boat floating 4 m up, with a masked ferryman poling at the stern, rose garlands and a prow bell | **Ferry** (Orig): carries up to 6 food of allied ground units. Splash attack | [P] |

### B5.2 Stats

| Unit | Built at (needs) | Gold / lumber / food | Time (s) | Lvl | HP | Mana | Armour | Attack, damage | CD (s) | Range (m) | Hits | Speed (m/s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sexton | Barrow | 70 / 0 / 1 | 15 | 1 | 230 | – | 0 Medium | Blade 5–7 | 2.0 | 0.6 | G | 3.0 |
| Veiled Mourner | House of Masks (from a Sexton) | +60 / 0 / 0 | 10 | 1 | 160 | – | 0 Light | – | – | – | – | 5.2 (hover) |
| Retainer | Household Tomb | 125 / 0 / 2 | 18 | 2 | 380 | – | 0 Heavy | Blade 12–15 | 1.3 | 0.7 | G | 4.2 (4.9) |
| Shroudcaster | Household Tomb (Ossuary) | 210 / 40 / 3 | 30 | 3 | 540 | – | 0 Medium | Pierce 24–30 | 2.0 | 7.0 | G+A | 4.0 |
| Drift-Shroud | Household Tomb (Long Barrow) | 180 / 30 / 2 | 26 | 2 | 400 | – | 2 Light | Pierce 16–20 vs air; Blade 7–9 vs ground | 1.5 | 3.0 | G+A | 5.6 (fly) |
| Eulogist | House of Masks | 150 / 15 / 2 | 28 | 2 | 300 | 200 | 0 Unarmored | Arcane 9–11 | 1.9 | 6.0 | G+A | 4.2 |
| Imaginifer | House of Masks | 160 / 30 / 2 | 30 | 2 | 290 | 250 | 0 Unarmored | Arcane 10–12 | 1.8 | 6.0 | G+A | 4.4 (hover) |
| Canopic Urn | Kiln Yard | 200 / 40 / 3 | 32 | 3 | 650 | 300 | 3 Heavy | – | – | – | – | 4.0 (hover) |
| ↳ the Released | (Master *Uncork*, 8 s) | – | 8 | 4 | 850 | 300 | 1 Light | Arcane 20–24 | 1.6 | 4.0 | G+A | 5.0 (fly) |
| Urn Hearse | Kiln Yard | 220 / 50 / 4 | 36 | 3 | 400 | – | 2 Heavy | Siege 68–82, splash 1.0 / 2.0 m | 4.0 | 14.5 (min 3.0) | G | 3.4 |
| Tombwalker | Kiln Yard (Grand Barrow) | 240 / 70 / 4 | 42 | 4 | 1150 | – | 2 Heavy | Blade 32–40 | 1.9 | 1.0 | G | 3.6 |
| Wake Barge | Ferry Steps | 380 / 110 / 7 | 60 | 7 | 1350 | – | 1 Light | Arcane 80–98, splash 1.25 / 2.5 m | 3.2 | 4.5 | G+A | 3.4 (fly) |

Sight is 21.9 / 12.5 m for all units except the Sexton (12.5 / 9.4) and the Veiled Mourner (18.0 / 18.0).
Lineage bonuses apply on top of these values.

## B6. Heroes

Global hero rules apply. Heroes rise at the **Cenotaph**.

| Hero (id) | WC3 role match | Primary; STR / AGI / INT (+ per level) | HP / mana at L1 | Range; speed | Look (one oversized prop) |
|---|---|---|---|---|---|
| **Mourning Legate** (`deathless_hero_legate`) | Dark commander (STR melee, heal-the-dead) | STR; 24 (+2.7) / 12 (+1.4) / 17 (+1.8) | 700 / 255 | 1.0 m; 4.6 | Towering dead general on foot. Blackened face-mask, **huge transverse crest of dried roses**, soot cloak, round shield painted with a calm face. Example name: *Aulenus the Unfinished* |
| **The Dowager** (`deathless_hero_dowager`) | Cold caster (INT nuke and armour buff) | INT; 15 (+1.7) / 13 (+1.1) / 22 (+3.0) | 475 / 330 | 7.5 m; 4.4 | Tall, thin matriarch in a **towering conical headdress**, with a disdainful chalk mask (painted raised eyebrows). She flicks stiff dried petals from a fan. Example name: *Dowager Tenebra* |
| **The Patriarch** (`deathless_hero_patriarch`) | Noble lord (INT melee, sleep, life-steal aura) | INT; 19 (+2.2) / 12 (+1.2) / 20 (+2.7) | 575 / 300 | 1.0 m; 4.5 | Immense patrician in a soot toga with a rose border, a **broad collar of small heirloom masks**, a fist-sized silver signet and a heavy rod of office. No wings. Example name: *Gravius Ninth-of-the-Name* |
| **Gravewright** (`deathless_hero_gravewright`) | Burrowing tank (STR, line stun, thorns) | STR; 26 (+2.8) / 11 (+1.1) / 14 (+1.4) | 750 / 210 | 1.0 m; 4.3 | Hulking dead stonemason in a chalk-caked apron with a limestone mask, a **tomb-slab shield** and a stone-cutter's pick. Example name: *Master Lapidus* |

**Kits** (ranks 1 / 2 / 3; mana; cooldown). At most 2 FE per hero.

| Hero | Q | W | E | R (ultimate, level 6) | FE |
|---|---|---|---|---|---|
| Mourning Legate | **Grave Honours** (unit, 8 m): 100 / 175 / 250 Spell damage to a living enemy, **or** heals an allied Wakeful 200 / 350 / 500. 75 mana, 7 s. *FE* | **Funeral Pace** (aura, 8 m): **enemies** have −8 / −14 / −20 % move speed and no natural HP regeneration. *Orig (a debuff aura, not an ally haste)* | **Marching Orders** (point, 12 m): allied non-heroes within 8 m surge toward the point at +80 % speed for 2 s; their next hit deals +30 / 50 / 70 %. 70 mana, 18 s. *Orig* | **Roll Call** (20 m): every dropped mask in range rises as the unit that dropped it, for 30 s (up to 8; full HP; Pure damage; cannot be healed). The masks are consumed. 175 mana, 180 s. *FE (temporary raised army)* | **2** |
| The Dowager | **Withering Look** (unit, 8 m): 100 / 160 / 220 Spell damage; the target and enemies within 3 m get −40 % move and attack speed for 3 / 4 / 5 s. 85 mana, 8 s. *FE (nuke plus area slow)* | **Mantle of Rank** (ally, 8 m, 45 s): +3 / 5 / 7 armour; melee attackers of the wearer get −25 % attack speed for 3 s. 40 mana, 2 s. *FE (armour buff)* | **Old Grudge** (enemy, 10 m, 10 s): the target cannot be healed and takes +10 / 15 / 20 % damage from Wakeful sources. If it dies, she regains 50 / 75 / 100 mana. 75 mana, 15 s. *Orig* | **Damnatio** (enemy hero, 9 m, 8 s): the hero is "struck from the record": its auras switch off, and allied heals and buffs cannot target it. If it dies during Damnatio, its revive time is +50 %. 150 mana, 120 s. *Orig* | **2** |
| The Patriarch | **Entail** (enemy, 8 m, 8 s): binds the target to its current spot. If it ends up more than 5 m away, it takes 120 / 200 / 280 Spell damage and is stunned 1 / 1.25 / 1.5 s, which ends Entail. 70 mana, 12 s. *Orig* | **Family Fortune** (aura, 9 m): allied melee attacks heal the attacker for 10 / 20 / 30 % of damage dealt. *FE (life-steal aura)* | **Ancestral Drowse** (unit, 8 m): sleep for 5 / 7 / 9 s (heroes 2 / 3 / 4); damage wakes the target. 75 mana, 9 s. *FE (sleep)* | **Family Vault** (point within 10 m, 8 m circle): a stone vault rises for 10 s. Allied non-heroes inside sink into it: untargetable, healing 5 % max HP/s. They re-emerge when it ends or he recasts. The vault has 1500 HP; if it is destroyed, they emerge stunned for 1 s. 175 mana, 150 s. *Orig* | **2** |
| Gravewright | **Upheaval** (line 10 m × 1.5 m): tombstones erupt for 70 / 130 / 190 Spell damage, knocking up and stunning for 1 / 1.5 / 2 s. 90 mana, 11 s. *FE (line stun)* | **Stone Lid** (passive): +2 / 4 / 6 armour; melee attackers take back 10 / 20 / 30 % of their damage. *FE (thorns)* | **Raise Cenotaph** (point, 6 m): a 2×2-cell monument for 30 s with 600 / 800 / 1000 HP. It counts as Pall within 6 m, and allied Wakeful there regenerate +3 HP/s. 70 mana, 20 s. *Orig* | **Entomb** (8 m ring on himself or a point within 6 m, 8 s): stone slabs stop ground units crossing in or out. Wakeful inside deal +20 % damage. 150 mana, 150 s. *Orig* | **2** |

No Wakeful hero copies its WC3 counterpart's ultimate except the Legate's raised army, which is fed by our own mask system.

## B7. Buildings and tech tiers

```
Wake Barrow (T1) ──► Long Barrow (T2, needs Cenotaph) ──► Grand Barrow (T3, needs Ossuary)
│                         │                                        │
├─ Columbarium (+10 food, ├─ House of Masks ── Eulogist,           ├─ Kiln Yard ── Tombwalker, Uncork
│   Pall)                 │   Imaginifer, Veiled Mourner           ├─ Ferry Steps ── Wake Barge
├─ Cenotaph ── heroes     ├─ Kiln Yard ── Urn Hearse, Canopic Urn  └─ Master trainings, level-3 upgrades
├─ Household Tomb ── Retainer, Shroudcaster [Ossuary], Drift-Shroud [T2]
├─ Ossuary ── upgrades, lumber drop-off ── Mourning Post ─► Urn Tower | Knell Tower
└─ Grave Goods ── items (stock grows with tier)
```

Every building has Fortified armour 5.

| Building (id) | WC3 role slot | Needs | Gold / lumber | Time (s) | HP | Food | Function |
|---|---|---|---|---|---|---|---|
| **Wake Barrow** (`deathless_wake_barrow`) | Hall T1 | – | 385 / 190 | 160 | 1550 | +10 | Sexton; gold and lumber drop-off; Pall 16 m |
| **Long Barrow** | Hall T2 (upgrade) | Cenotaph | +300 / 200 | 130 | 2050 | +12 | Tier 2, hero 2; Pall 18 m |
| **Grand Barrow** | Hall T3 (upgrade) | Long Barrow, Ossuary | +350 / 220 | 140 | 2600 | +14 | Tier 3, hero 3; Pall 20 m |
| **Columbarium** | Supply | – | 150 / 50 | 45 | 520 | +10 | A curved wall of urn niches; Pall 8 m. **Does not** upgrade into a tower |
| **Cenotaph** | Hero altar | – | 180 / 50 | 60 | 900 | – | Raises and revives heroes; Pall 6 m |
| **Household Tomb** | Barracks | – | 180 / 50 | 60 | 1300 | – | Retainer, Shroudcaster, Drift-Shroud. *Brisk Step*, *Burial Shroud*, *Lie in State* (T2) |
| **Ossuary** | Smithy and lumber drop-off | – | 150 / 50 | 60 | 1100 | – | *Honed Bone* (+10 % non-caster damage per level), *Lacquered Shrouds* (+2 armour per level), 3 levels each; *Wide Pall* (T2: +25 % Pall radius) |
| **House of Masks** | Caster temple | Long Barrow | 160 / 130 | 65 | 1000 | – | Eulogist, Imaginifer; Veiled Mourner. Journeyman (T2) and Master (T3) trainings |
| **Kiln Yard** | Workshop | Long Barrow | 150 / 140 | 60 | 1150 | – | Urn Hearse, Canopic Urn; Tombwalker at T3. *Uncork* and *Grave-Damp* (T3) |
| **Ferry Steps** | Heavy-air pier | Grand Barrow | 175 / 200 | 70 | 1150 | – | Wake Barge |
| **Mourning Post** | Scout tower | Ossuary | 40 / 20 | 25 | 320 | – | Sight 25 / 18 m. Exclusive upgrades: **Urn Tower** (+80 / 40: Pierce 20–24, CD 1.0 s, 10.9 m, G+A) or **Knell Tower** (+90 / 70: Arcane 11–13, CD 1.6 s, 10.0 m, G+A, hits slow 25 % for 3 s, detects invisible within 9 m) |
| **Grave Goods** | Faction shop | – | 130 / 30 | 60 | 480 | – | Potions, *Coin for the Ferry*, *Spare Mask* |

| Tier | Unlocks |
|---|---|
| T1 Wake Barrow | Sexton, Retainer, Shroudcaster, Mourning Post; hero 1; level-1 upgrades |
| T2 Long Barrow | Drift-Shroud, House of Masks, Kiln Yard, Eulogist, Imaginifer, Veiled Mourner, Urn Hearse, Canopic Urn; hero 2; Journeyman trainings; *Wide Pall*; level-2 upgrades |
| T3 Grand Barrow | Tombwalker, Ferry Steps and Wake Barge, *Uncork*, Master trainings; hero 3; level-3 upgrades |

## B8. Voice and music

**Voice personality: languid, snobbish old money that happens to be dead.**
- They boast about lineage and precedence and treat the living as upstart trespassers on the family estate.
- They are nostalgic ("in my day the hills were smaller") and slightly hard of hearing after a few centuries.
- They are theatrically, impeccably polite while doing something terrible.
- The comedy is **snobbery and ancestry**. It is never hospitality or feasting (a clans trait) and never ledgers or contracts (a kingdom trait).
- Delivery is unhurried, with long vowels and the faint echo of speaking through a mask (a short pre-delay reverb).
- **No faux Italian accent.**
- Each unit gets one tic. For example, the Retainer repeats "as the family wishes"; the Tombwalker's two lid-figures interrupt each other.
- Annoyed lines avoid the word "poke".

**Sample lines** (original; check against the WC3 undead quote page before recording):
- Retainer (Yes): *"As the family wishes. As the family always wishes."*
- Eulogist (Annoyed, last in sequence): *"I have eulogised better men than you. Several of them were alive at the time."*

**Music:**
- Double reed-pipes and lyre, frame drum and finger cymbals, small tarnished bells, and a low unison male hum.
- A slow, stately processional at 60–76 BPM that is unsettlingly *too* festive.
- **Avoid** dark choir with pipe organ and dissonant strings (the WC3 undead sound).

## B9. Distinctness rubric (ip-safety §3.2; nearest WC3 race: the undead plague)

| Axis | WC3 undead | Long Wake | Differs? |
|---|---|---|---|
| 1. Silhouette | Spikes, hunched ghouls, spider fiends, stitched brutes, gargoyles, ziggurats and spiked halls | Upright masked processions, Lineage poles, cloth spirits, urns, a sarcophagus walker, a funeral barge, round tumuli | **Yes** (required) |
| 2. Palette | Purple, black, teal glow, sickly green | Soot and terracotta, chalk, grave-rose, lamp-rose glow | **Yes** |
| 3. Materials | Bone spikes, frost, purple stone, ooze | Terracotta, chalk plaster, lacquer, linen shrouds, dried flowers, limestone | **Yes** |
| 4. Culture | Gothic and Nordic frost necromancy, insect horror | Etruscan and Roman funerary houses: tomb paintings, ancestor masks, urns | **Yes** |
| 5. Signature mechanic | Blight, cursed mine, summon-and-walk-away building, corpse economy | The Pall (the one WC3-derived mechanic, softened and re-presented) plus original Heirloom Masks | **Yes** (within policy) |
| 6. Names and voice | WC3 unit, hero and place names; sinister, hungry | All original; snobbish ancestral aristocrats | **Yes** |

**Result: 6 / 6.** Residual risk: the plague-ground idea and the siege cart are familiar shapes. Keep the Pall grey and petal-flecked,
and keep the Urn Hearse free of bodies.

---

# Part C: Production fit (later milestones)

| | Glaermere | Long Wake |
|---|---|---|
| [B] bipeds: Tripo H3.1 image-to-3D (9 cr) plus the bpy auto-rig | Tapster, Larkbow, Stoneskipper, Ambermail, Sapsinger (Bark Coat as a prop and texture swap), Hazeweaver, and 4 heroes: **10 × ≈ 9.25 cr ≈ 93 cr** | Sexton, Retainer, Shroudcaster, Eulogist, Imaginifer (upper body only; the hover is procedural), and 4 heroes: **9 × ≈ 9.25 cr ≈ 83 cr** |
| [C] creatures: AI mesh with rigid-segment procedural motion | Woodgnaw (waddle, tail pivot), Treeglider (spread-eagle glide): **≈ 19 cr** | – |
| [P] / [V] procedural or VFX: bpy plus AI textures | Springbough (Tapster crew reused), Thistleship (lathe seed plus wicker gondola), Glimmerswarm (particles): **≈ 2 cr** | Urn Hearse (Sexton crew reused), Wake Barge, Tombwalker (box, lid and stub legs; the lid couple can be a 9 cr AI relief), Canopic Urn (lathe), Drift-Shroud and Veiled Mourner (cloth cards with vertex waves): **≈ 3–12 cr** |
| Buildings | One AI hall (9 cr) plus a **bpy stilt-and-gable kit**: **≈ 12 cr** | One AI hall (9 cr) plus a **bpy drum-mound kit** (cylinder, dome, door frame, urns, cypress): **≈ 12 cr** |
| Icons (about 35 each) | ≈ 9 cr (0.25 cr each) or 2×2 Krea sheets | ≈ 9 cr |
| **Total** | **≈ 135 cr** | **≈ 115–125 cr** |
| Voice | About 11 units × 18 + 4 heroes × 26 + advisor 14 ≈ **315 lines** | About **330 lines** |

**Budget warning.** After the slice (kingdom ≈ 70–95 cr, clans ≈ 80–90 cr), only about 85–120 of the 269.75 Higgsfield credits remain.
These two factions need about 250 cr. Options:
- Run the README §6 bake-off. If Krea's legacy Tripo (8 CU) or TRELLIS (10 CU) passes for rank-and-file units, move them there.
- Otherwise top up credits before these milestones.

**Default voices expire on 31 Dec 2026.** Either record these lines before then, or plan for voices that will still be available later.

---

# Part D: Open questions and tuning flags

1. **Engine features these factions need** (not in the slice):
   - Glaer: per-tree tapper occupancy without depletion; shallow-water building placement; noonlight sight-override zones in the fog grid
     (a light mask in the grade shader).
   - Wakeful: a Pall ground layer (reuse the corruption mask shader); mask pickup entities; a deterministic snapshot for *Roll Call* and *Family Vault*.
2. **Sunstore strength.** A Lodge exactly covers one night. If Glaer turtling at night is too strong, cut regeneration to +0.5 HP/s first,
   then the Post capacity.
3. **Tapping economy.** At 8 lumber per trip and 1.0 s per lumber, Glaer lumber is slower early than the kingdom's (10) or the clans' (15),
   but the woodline never recedes. Check lumber per minute at 0–6 min and at 15 min in AI-vs-AI runs.
4. **Pall regeneration denial** may feel bad for melee-heavy opponents. Fallback: enemy regeneration −50 % instead of 0.
5. **Lineage snowball.** +18 % at rank 3 plus mask hooks may over-reward early trades. Tune the cap (3 → 2) before the per-rank value.
6. **Woodgnaw and Treeglider** are the riskiest assets (quadruped and glider). If the rigid-segment motion looks poor, replace
   Woodgnaw with a biped "bark giant" in walking armour (never a tree-man) and the Treeglider with a wicker hang-glider rider.
7. **Name clearance.** Glaermere, Glaer, Long Wake and Wakeful had no web search (budget exhausted). Add them to the
   `tools/ip_banned_terms.txt` CI review list and check them at the public-title clearance pass (ip-safety §4).
8. **Real-culture respect.** Etruscan and Roman sources are extinct civilisations, so the risk is low, but avoid real tomb names, real
   inscriptions and real deity iconography. Northern lakeland sources: no real sacred signs, deities or epic names, and no caricature accent.
9. **Full-game matchups.** Glaer air plus anti-magic should counter Wakeful casters. Wakeful Pall sustain should punish Glaer
   hit-and-run. Kingdom towers and clans haste pushes need re-tuning once all four factions exist.
