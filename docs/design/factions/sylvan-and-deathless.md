# Faction designs (roster level): `sylvan` (Glaermere) and `deathless` (the Long Wake)

*Design date: 2026-10-16, revised twice the same day after two rounds of IP-safety and WC3-fidelity reviews (see the Review logs at the end).
Status: roster-level proposal for **later milestones** (full game). Neither faction is in the vertical slice, which is kingdom vs clans.
Faction ids: **`sylvan`** and **`deathless`**; data prefixes are `sylvan_` and `deathless_`.*

**Read with:**
- `docs/design/rules.md`: the authority for every global rule (it supersedes mechanics §13.1, §13.2 and §13.7). Values here follow it;
  the few places that need a rules.md change are listed under "Follow-ups in other files" in the round-2 Review log (the current list).
- `docs/design/neutrals.md`: creep families, items and neutral buildings. Its §10.2 squint table and §11 Q12 cross-check request are
  answered in Part E.
- `docs/research/ip-safety.md`: §0, the §2 banned lists and the §3.2 rubric.
- `docs/research/gameplay-mechanics.md`: §11–§13 (§12.2: never copy a whole WC3 unit kit or hero kit).
- The two full faction docs, `kingdom.md` and `clans.md`. Every name, theme, palette and ability below was checked against both docs
  to avoid collisions. For example, the clans own hospitality comedy, weather metaphors, dust and blind effects, "Updraft", ancestor
  stones, "Elder" ranks and doubled-vowel names, and the kingdom owns ledger, register and contract comedy, "Smoke Pall", firepots and
  burning ground, so this doc avoids all of them. (Round 2 fixed the collisions the first check missed; two requests go to the other docs.)

**Brief, restated.** Gameplay, structure and feel stay as close to Warcraft III as possible. A fan should name each unit's
job and the build-order logic at a glance: the forest-elf race and the undead-plague race. All expression is ours:
names, looks, palettes, emblems, culture, voices and lore.

**Depth.** This doc is about a third as deep as `kingdom.md`. It covers identity, look, signature mechanics, a full role roster with
numbers, projectile speeds, the minimum ability and research numbers needed to simulate a fight, four heroes per faction, buildings
with footprints, shops and tiers, command cards and hotkeys (§A7.5, §B7.5), and voice. Per-rank unit tables, build orders and VO scripts
get written when each faction enters production.

**Global rules apply unchanged** (rules.md):
- Start with 500 gold / 150 lumber at 08:00. Food cap 100. Upkeep keeps 100 / 70 / 40 % of gold at 0–50 / 51–80 / 81–100 food.
- Hero rules: XP table, 3 abilities + an ultimate at level 6, STR/AGI/INT formulas, 6 item slots, at most 3 heroes, altar revive,
  proper names shown as "Title: Name" (rules §6.1).
- 480 s day/night cycle and the damage matrix.

**Conventions** follow `kingdom.md`:
- Distances in metres, speeds in m/s, sight as day / night in metres.
- Attack types Blade, Pierce, Siege, Arcane, Heroic, Spell, Pure. "G+A" means the attack hits ground and air.
- **FE** marks a functional equivalent of a WC3 ability. **Orig** marks an original mechanic. **Genre echo** marks an original mechanic with
  a loose precedent in other games (not WC3); it does not count as FE, but its name, look and numbers must still be ours. Every unit and
  hero ability is tagged.
- **FE rules** (this doc's own, stricter than the brief):
  1. At most 2 of a hero's 4 abilities may be FE.
  2. At most **2 heroes per faction** may use 2 FE; every other hero has **at most 1**.
  3. An FE ability may share **at most one numeric parameter** (damage, heal, mana, cooldown, duration, range or radius, at any rank)
     with its WC3 source.
  4. No unit keeps its WC3 slot's whole kit. Each faction keeps a unit equivalence ledger (§A5.3, §B5.3).
- **Internal audit material.** The squint tables, the equivalence ledgers, the distinctness rubrics (§A9, §B9), the FE notes and every
  block headed **"Internal audit, never in prompts or data"**, and the WC3 columns of the signature-mechanic tables (§A3.1, §B3.1) name
  WC3 or other IP on purpose. **Never paste them into prompts, negative
  prompts, data or filenames** (ip-safety §2.8). The "Role" columns and the FE tags use neutral role words only.
- **Display names.** The faction ids `sylvan` and `deathless` are internal. The UI never shows them, and never displays "Sylvan" or
  "Silvan elves" (a Tolkien term).
- **Flags** (rules §10.7): `organic`, `mechanical`, `summoned`, `spell_immune`, `worker`, plus the **`undead`** flag this doc asks rules.md
  to add (every Wakeful unit except constructs and carts). "Living" means `organic` and not `undead`. Repair targets only `mechanical`
  units and structures (rules §4.8).
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
| **Emblem** | **The Kept Light**: a tall amber teardrop, point up, crossed by one charcoal bark-dash, between two downward birch leaves, on moss sage |
| **Motto** | "Waste no summer." |
| **Cultural inspiration** | Northern European lakeland forests: prehistoric pile-dwellings on stilts, birch-bark craft (boxes, shoes, shingles), Baltic amber working, resin tapping and tar-burning, stilted storehouses, plucked box-zithers, alternating-voice chant |
| **Palette** | Moss sage and birch white, with charcoal bark-dashes and amber glow. No violet, teal, silver, red or gold |
| **WC3-derived mechanic (the one allowed)** | **Tapping**: workers harvest lumber without felling trees, shown as resin tapping with spigot and pail (§A3.1) |
| **Original mechanics** | **Summerhoard**: lodges and towers bank daylight and burn it as "noonlight" through the night; by day their "sunlit yards" heal (§A3.2). **Stilt-built**: buildings may stand in shallow water |
| **Play pattern** | A fragile, fast, ranged-heavy army with the best anti-air and dispel. Siege is weak early. Strong by day and around its lanterns at night; weak when caught on the march at night or when burst down |
| **Role mirror** (internal) | Worker that never fells trees, archer, bouncing skirmisher, bolt siege, spell-immune anti-caster, shape-changing healer, debuff-and-disable caster, giant tank, anti-air flyer (detects with a research), magic-immune anti-caster flyer, heavy air. Heroes: archer captain (ranged aura), grove caster (root and control), mana-draining melee, mobile assassin. No summons anywhere (§A9) |

## A1. Identity

**Names.**
- **Glaer** comes from Old English *glǣr*, "amber, resin". It also suggests "glare", fitting a people who hoard light. *Mere* means lake.
  This Old English etymology is the in-world source. (*Glaer* is also an obscure Tolkien Noldorin word, "long lay"; low risk, recorded in Part D item 7.)
- Neither word uses a rival naming pattern (the avoided stems are in the internal audit block below), and there are no moon, night, star,
  shadow or sun-reservoir compounds.
- The UI never says "elf". Lore text may say "the elf-folk of the meres" once, as a description.

**Naming rules.**
- Units and buildings get English nature-craft compounds: Larkbow, Stilt Larder, Glare Post.
- Personal names are short invented given names with a soft ending (*-e, -i, -ve*) plus an English light or craft epithet, e.g. *Tieve Brightstring*.
- No apostrophes and no doubled-vowel names, because the clans use those.
- No real Finnic or Baltic deities, epic heroes or sun-signs.

> **Internal audit, never in prompts or data** (ip-safety §2.8). Avoided name stems: *-dorei*, *Kal-*, *Quel-*, *Thal-*, *Sil-*, and
> "sun-well" compounds (the round-1 mechanic name "Sunstore" was one, so it became **Summerhoard**). Avoided creature designs from the
> nearest rival race: hippogryphs, chimaeras, faerie dragons, owls, the big-cat mount, deer-bodied units. Avoided neutral look-alikes:
> toads and frogs (the neutral Mire Toads). The Hazeweaver's disable is never called "Amber Prison" (a *World of Warcraft* raid ability).

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
   −56° camera, the read is a teardrop trailing behind the unit. No other faction has this read: kingdom kettle-hat discs
   and clans cones point the other way.
2. **Bark-scale capelets.** Overlapping birch-bark shingles form a short flared cone over the shoulders. The read is a pale ring with charcoal dashes.
3. **Amber lanterns.** Every unit carries one glowing amber point: hung from a bow tip, a staff, a yoke or a gondola.
   These are the faction's night read. Lanterns are **always caged teardrops** (withy or birch lattice), never a pierced or drilled
   head-shaped lantern (that is the neutral Hollow Harvest's read; Part E).
4. **Bodies.** Tall and long-limbed, with chunky hands, feet and weapons. Ears are long and **droop down and back like birch leaves**,
   never huge and upswept. Skin is warm birch-cream with charcoal freckle-dashes across the cheekbones and forearms.
   Hair runs from flax to amber, and eyes are amber. No violet or blue skin, and no blindfolds or tattoos.
5. **Weapons.** Long laminated birch bows, sling-staffs, punt poles, tapping mallets and fishing gaffs.
   **No glaives or crescent blades.**
6. **Creatures are lake-forest animals.** A giant beaver, a giant flying squirrel and amber fireflies. No eagle-horse hybrids,
   no two-headed winged reptiles, no dragons, and no owls, big cats, deer-bodied units, toads or frogs.

**Palette** (albedo targets):

| Role | Name | Hex | Where |
|---|---|---|---|
| Mass 1 | Moss sage | `#8DA27A` | Nettle-cloth tunics, leggings, roof moss trims |
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

**Squint-test risks** (internal audit; WC3 names appear only here and in the ledgers):

| Glaer design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Larkbow | Night-elf archer | **Medium** (an elf woman archer is a genre staple) | Leaf-tip hood, bark capelet, lantern on the bow, sage and birch palette, drooping ears; no purple, no moon motifs |
| Lark Captain | Priestess of the Moon | **Medium** (archer heroine) | On foot, no big-cat mount, no owl, no moon. Lark-feather crest; the ultimate makes a daylight zone, not falling stars |
| Thicket Weaver | Keeper of the Grove | **Medium** (druid hero) | Old man on two legs: **no antlers, no deer body, no glowing staff**. A huge withy back-loom is his read. No summons, no tree ring, no area heal and no living roots in his kit (Withy Snare is woven hoops) |
| Lampbreaker | Demon Hunter (and the DotA mana-breaker hero) | **Medium** (mana-draining AGI melee) | A lamp-thief, not an exile: eyes open (no blindfold), no tattoos, no twin blades, no green fire, no damage aura, no transformation. Punt pole and a broken lantern gauntlet |
| Reedstalker | Warden (and the DotA stealth assassin) | **Medium** (assassin with a volley and a short blink) | A **male** eel-fisher with no hood and no helm, a reed-sheaf cloak and a fishing gaff; no blades, no purple; the blink only works from water or beside a tree |
| Sapsinger | Druid of the Claw | **Medium** (shape-changing healer) | A stout singer with a bucket staff; the heavy form is a **bark coat**, never an animal |
| Stoneskipper / Ambermail / Woodgnaw | Huntress / Dryad / Mountain Giant | Low | Biped runner with a sling-staff (no cat, no glaive); biped in amber-lacquered bark (no deer body); a beaver (no rock giant) |
| Treeglider / Glimmerswarm / Thistleship | Hippogryph / Faerie Dragon / Chimaera | Low | Flying squirrel with a small rider and a caged lantern (no archer-rider merge since round 2); firefly swarm; floating thistle-down balloon |
| Stilt Lodge | Tree of Life | Low | Gabled stilt house, never a tree |

## A3. Signature mechanics

### A3.1 Tapping (the one WC3-derived mechanic, presented differently)

| | WC3 forest-elf worker | Glaer Tapster |
|---|---|---|
| Harvest | A glowing spirit hovers at a tree; the tree is never felled | A biped elf knocks a **spigot** into the trunk and catches resin in a pail. The tree is never felled; tapped trees show amber drips and a cup |
| Yield | 5 per cycle (verify) | **10 per trip**, 1 lumber per **0.9 s**; **12** with *Deep Spigots* (T2) |
| Return trip | Credits lumber in place, no return trip (verify) | **Walks it back** to a Lodge or the Resinworks. *Deliberate change*: it keeps WC3's gather-and-return rhythm and gives raiders a woodline lane to hit |
| Per tree | Several workers may share a tree | **One Tapster per tree** |
| Woodline | Never recedes | Never recedes either. Glaer cannot open new paths by harvesting. Only Woodgnaw (**Fell**) and Springbough shots remove trees |
| Presentation | Hovering glow, chime | Mallet *tok-tok*, a resin "plink" into the pail, honey-coloured drip decal |

**Rate check** at rules.md's 10 m reference walk (3.1 m/s, 0.35 m radius, ≈ 6.45 s round trip): 10 ÷ (9.0 + 6.45) ≈ **0.65 lumber/s**
per Tapster, against kingdom ≈ 0.68 and clans ≈ 0.75. *Deep Spigots*: 12 ÷ (10.8 + 6.45) ≈ **0.70/s**. One-per-tree pushes a sixth or
later Tapster to a farther tree; check that in AI runs (Part D item 3).

Glaer drop the rest of the forest-elf set: workers living inside the gold mine, walking and uprooting buildings,
night-only regeneration, night invisibility, moon-energy supply wells, the self-destructing dispel worker, and eating trees for a buff.

### A3.2 Summerhoard and noonlight (original)

| Rule | Value |
|---|---|
| Charge | Each Lodge (any tier) and each Glare Post banks daylight: **+1 charge per 20 s of day**. Capacity: Lodge **12**, Glare Post **6** |
| Start | Lodges and Posts **start at 0 charges** when finished, the starting Lodge included. The match starts at 08:00 with 200 s of day left, so the starting Lodge banks **10 charges** and the first night burns them in **200 s** of the 240 s night |
| *Lantern Glass* (Resinworks, T2) | Capacity **+4** (Lodge 16, Post 10) **and** charging **+1 per 15 s** (16 per day), so a Lodge reaches dusk with 4 spare charges for *Open the Shutters* or a longer burn |
| Burn | From dusk, a charged lantern burns **1 charge per 20 s** and projects **noonlight**: Lodge radius **14 m**, Glare Post **10 m**. Without Lantern Glass a full day fills a Lodge for exactly one night (240 s ÷ 20 s = 12 charges); a Glare Post lasts half the night (6 charges, 120 s) |
| Inside noonlight | Glaer units **and structures** count as **in daylight**: day sight, regeneration **+1.5 HP/s for units** (heroes too) and **+1 HP/s for structures**, and day-keyed abilities stay on (Larkbow *Warm Strings*). **Enemy invisible units inside are revealed.** No other effect on enemies. Noonlight does not wake creeps |
| **Sunlit yard** (by day) | Glaer units within a Lodge's **14 m** or a Glare Post's **10 m** regenerate **+1.5 HP/s** by day, with **no charge spent** (the same rate as noonlight and as the Wakeful Pall). This is the faction's walk-home-and-top-up loop between creep camps. It reveals nothing and has no other effect |
| **Open the Shutters** (Lodge ability) | Spend **4 charges**: a **16 m** noonlight anywhere within 30 m of the Lodge for **15 s**, day or night (by day it only reveals). Cooldown 60 s |
| Presentation | Lantern-cages glow honey-orange (HDR) and warm motes drift. Inside the circle the night grade lifts to the day grade (a shader light mask). Our own "shutter clack" and a two-note rising chime |
| Counterplay | Kill Glare Posts, fight away from lanterns and yards, and catch Glaer armies on the march at night |
| Why it is ours | The nearest rival race (§A9) is **night-aligned** and tops up at home wells. The Glaer are **day-aligned**, carry daylight into the night, and heal in their lodges' sunlit yards. No rival race projects daylight zones |
| Tuning | If Part D item 2's turtling flag fires, cut the unit rate in noonlight and the sunlit yard from +1.5 to **+1.0 HP/s** (structures stay +1) |

**Stilt-built** (minor, original): every Glaer building may be placed in **shallow water**. Deep water and cliffs are still
excluded. Land units walk shallow water normally, so this gives placement freedom, not protection.

## A4. Economy and faction rules

| Rule | Value |
|---|---|
| Gold | Walked back to a Lodge, 10 per trip (global) |
| Lumber | Tapping (§A3.1): 10 per trip, 1 per 0.9 s, one Tapster per tree; *Deep Spigots* +2 |
| Food | Stilt Lodge 10 → Lantern Lodge 12 → Amber Lodge 14. **Stilt Larder +10** (140 g / 40 l, 45 s) |
| Construction | Woven. One Tapster builds; a second may assist (+50 % rate). *Resin Seal* repair: structures and the `mechanical` Springbough and Thistleship; autocast, default off, costs 30 % pro rata |
| Night | Summerhoard only (noonlight by night, the sunlit yard by day; §A3.2); no other night modifiers |
| Woodline tell | **Hang Lantern** (Tapster): hangs a lantern on the tree it is tapping (8 m vision, 60 s, one per Tapster). A raid warning on the woodline, not a scouting tool |
| Shop | Trinket Stall (§A7.4): recall item *Lake Whistle* (the first hero's free item), potions, the *Birch-Bark Poultice* field heal, *Lantern Stake* vision wards, a T2 *Bottled Noon* reveal, a T2 anti-magic tonic, a T2 permanent and the T3 *Noon-Stone Chip* |
| Scouting and detection | No unit has true sight by default. *Lantern Riders* (High Drey, T2) gives Treegliders true sight 9 m; noonlight reveals invisible units inside it; *Bottled Noon* (T2) is the hero's reveal item |

## A5. Unit roster

### A5.1 Roles (one line each)

| id | Unit | Role | Look (upper-third read first) | Abilities (tagged) | Prod. |
|---|---|---|---|---|---|
| `sylvan_tapster` | **Tapster** | Worker | Young elf, leaf-tip hood, wooden yoke with two resin pails, tapping mallet, hand lantern | Taps trees (§A3.1); **Hang Lantern** (Orig): on its tapped tree only; *Resin Seal* repair | [B] |
| `sylvan_larkbow` | **Larkbow** | T1 ranged | Tall archer, laminated birch longbow taller than she is, amber-bead nocks, bark capelet | **Warm Strings** (Orig, passive): +15 % attack speed in daylight or noonlight. *Long Draw* research: +1.4 m range (FE) | [B] |
| `sylvan_stoneskipper` | **Stoneskipper** | T1 fast skirmisher with a bouncing attack | Barefoot runner in a bark-scale kilt, long sling-staff with a forked amber-beaded tip, stone pouch | **Skip** (FE, passive): each stone skips to a second enemy within 3 m behind the target for 50 % damage. *Skipping Lore* adds a third skip at 25 % | [B] |
| `sylvan_springbough` | **Springbough** | Siege (bolt thrower) | Bark sledge on runners with a bent-larch spring arm and a resin pot, hauled by two Tapsters (reused mesh) | Can attack trees (FE). *Sticky Resin* research (Orig): impacts leave sticky resin for 5 s (−30 % move speed) | [P] |
| `sylvan_ambermail` | **Ambermail** | Spell-immune anti-caster | Elf in glossy amber-lacquered bark plates with a resin-dart sling | **Spell immune** (FE). **Amber Fleck** (Orig, passive): 3 hits on one target within 6 s make its next spell cost +25 % mana and reveal it for 10 s. **Scrape Clean** (FE, autocast off): area dispel, 200 damage to summons | [B] |
| `sylvan_sapsinger` | **Sapsinger** | Shape-changing healer | Stout singer with a sap-bucket staff and a long choir scarf | **Warm Sap** (FE, autocast on): 300 HP over 12 s. Second Verse: **Lantern Hymn** (Orig): allies within 8 m count as in noonlight for 20 s. Full Chorus: **Bark Coat** (FE): a heavy melee form wrapped in bark plates, **not an animal**; no Warm Sap or Lantern Hymn in that form | [B] |
| `sylvan_hazeweaver` | **Hazeweaver** | Debuff and disable caster | Tall cone hat with a long midge-net veil, smoking birch-tar censer | **Midge Haze** (FE, autocast on): −3 armour and revealed for 75 s. Second Verse: **Fog Bank** (Orig): a 6 m fog; units inside cannot be targeted by ranged attacks from outside. Full Chorus: **Set in Amber** (FE): seals a non-hero in a standing lump of amber resin **on the ground** for 6 s, disabled and untargetable; never lifted or spun | [B] |
| `sylvan_woodgnaw` | **Woodgnaw** | T3 giant tank | Shaggy giant beaver with a bark-shingle saddle-roof; a lodge-keeper rides and sings | **Tail Slap** (FE): taunts within 5 m for 4 s. **Fell** (Orig): chews down a tree in 3 s and leaves a 20-lumber log for Tapsters; no combat buff. *Thick Pelt* research (FE): −25 % Pierce damage taken | [C] |
| `sylvan_treeglider` | **Treeglider** | Anti-air flyer | Giant flying squirrel with a small elf rider and lantern | Attacks air only (FE). **Dive** (Orig, passive): after 3 s without attacking, the next hit deals +60 % and slows the air target 50 % for 2 s. *Lantern Riders* research (FE, T2): true sight 9 m. **Lantern Drop** (Orig, research T3): drops a caged lantern below it that makes a 6 m noonlight for 20 s | [C] |
| `sylvan_glimmerswarm` | **Glimmerswarm** | Magic-immune anti-caster flyer | Drifting cloud of 20+ amber fireflies around a faint caged-lantern core, with a team-colour ring of motes | **Spell immune** (FE). **Wink Out** (FE, autocast on): on taking damage, untargetable for 1.2 s. **Snuff** (Orig, passive): attacks burn 8 mana | [V] |
| `sylvan_thistleship` | **Thistleship** | T3 heavy air vs ground and buildings | Floating giant thistle-down seed with a wicker gondola; two crew drop resin bombs | Ground-only splash bomber. *Burning Resin* research (Orig): +50 % vs buildings, plus 4 s of burning ground (10 damage/s) | [P] |

### A5.2 Stats

| Unit | Built at (needs) | Gold / lumber / food | Time (s) | Lvl | HP | Mana | Armour | Attack, damage | CD (s) | Range (m) | Hits | Speed (m/s) | Radius (m) | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tapster | Lodge | 70 / 0 / 1 | 15 | 1 | 220 | – | 0 Medium | Blade 4–6 | 2.0 | 0.6 | G | 3.1 | 0.35 | organic, worker |
| Larkbow | Fletchery | 125 / 10 / 2 | 19 | 2 | 300 | – | 0 Medium | Pierce 15–18 | 1.5 | 8.0 (9.4) | G+A | 4.4 | 0.45 | organic |
| Stoneskipper | Fletchery (Resinworks) | 185 / 20 / 3 | 28 | 3 | 580 | – | 1 Medium | Blade 18–22 | 1.8 | 3.5 | G | 5.0 | 0.45 | organic |
| Springbough | Fletchery (Lantern Lodge, Resinworks) | 210 / 65 / 3 | 36 | 3 | 400 | – | 2 Heavy | Siege 58–70, splash 1.0 / 2.0 m | 3.6 | 15.0 (min 3.5) | G, trees | 3.3 | 0.8 | mechanical |
| Ambermail | Singers' Hall | 150 / 50 / 3 | 30 | 3 | 450 | 200 | 0 Light | Pierce 13–16 | 1.8 | 6.0 | G+A | 4.7 | 0.45 | organic, spell_immune |
| Sapsinger | Singers' Hall | 190 / 60 / 3 | 33 | 3 | 420 | 225 | 0 Unarmored | Arcane 10–12 | 1.9 | 6.0 | G+A | 4.4 | 0.40 | organic |
| ↳ Bark Coat form | (Full Chorus, 3 s to switch) | – | – | 3 | 870 | 225 | 3 Heavy | Blade 24–30 | 1.6 | 0.8 | G | 4.0 | 0.6 | organic |
| Hazeweaver | Singers' Hall | 140 / 25 / 2 | 28 | 2 | 320 | 250 | 0 Unarmored | Arcane 9–11 | 1.8 | 6.25 | G+A | 4.4 | 0.40 | organic |
| Woodgnaw | Singers' Hall (Amber Lodge) | 340 / 90 / 6 | 50 | 6 | 1450 | – | 2 Heavy | Blade 26–34 | 2.0 | 1.0 | G | 3.4 | 1.0 | organic |
| Treeglider | High Drey | 150 / 20 / 2 | 22 | 2 | 450 | – | 0 Light | Pierce 18–22 | 1.5 | 1.5 | A | 5.6 (fly) | 0.6 | organic |
| Glimmerswarm | Thistle Mooring | 155 / 25 / 2 | 25 | 2 | 400 | – | 0 Light | Arcane 12–15 | 1.6 | 4.5 | G+A | 5.2 (fly) | 0.6 | organic, spell_immune |
| Thistleship | Thistle Mooring (Amber Lodge) | 330 / 90 / 5 | 50 | 5 | 1050 | – | 1 Light | Siege 70–84, splash 1.25 / 2.5 m | 3.0 | 2.0 (drops below) | G | 3.9 (fly) | 0.8 | mechanical |

Sight is 21.9 / 12.5 m for all units except the Tapster (12.5 / 9.4). Noonlight raises night sight to the day value.
Caster training ranks **Second Verse** (T2) and **Full Chorus** (T3): **+40 HP, +50 mana and +1 damage per rank** (the same values as
the kingdom's ranks; the names are the Glaer's own choir terms). Casters start with the global 75 mana.

**Projectiles** (rules §7.7; hero missiles are in the §A6 hero table):

| Attack | Speed (m/s) | Arc |
|---|---|---|
| Larkbow arrow | 20 | – |
| Stoneskipper stone (and each skip) | 18 | Low, skipping |
| Ambermail resin dart | 20 | – |
| Springbough bolt | 14 | High arc |
| Sapsinger, Hazeweaver and Glimmerswarm bolts | 15 | – |
| Thistleship resin bomb | Falls 0.5 s from the gondola | Drop |
| Glare Post | 20 | – |
| Treeglider | Instant (claw strike, 1.5 m) | – |

**One-line rules.**
- **Fell:** the Woodgnaw channels 3 s beside a tree (cooldown 10 s); the tree is removed (cells freed, `tree_felled` fires) and a **log
  holding 20 lumber** lies there for 120 s. Any Tapster loads up to its trip size (10, or 12) from the log in 1 s, so a log is two trips.
- **Lantern Drop:** the Treeglider releases a caged lantern that falls to the ground below it in 0.5 s and burns a **6 m noonlight for 20 s**
  (cooldown 45 s; needs the T3 research). The lantern is an untargetable ground effect, not a unit. It reveals invisible enemies inside and
  gives Glaer inside the noonlight effects (§A3.2). One per Treeglider at a time; a new drop replaces the old.
- **Bark Coat:** in the heavy form the Sapsinger cannot cast Warm Sap or Lantern Hymn; the Bark Coat button toggles back (3 s).
- **Set in Amber:** the amber lump stands on the target's cell and blocks it; the target is untargetable, takes no damage and cannot act.
  It is never lifted, spun or moved.

### A5.3 Unit equivalence ledger (internal)

| Unit | Role | WC3 equivalents kept (FE) | Original |
|---|---|---|---|
| Tapster | Worker | Non-felling harvest (the faction's one signature, §A3.1) | Spigot and walk-back, one per tree, tree-bound Hang Lantern |
| Larkbow | T1 ranged | Range research | Warm Strings |
| Stoneskipper | Bouncing skirmisher | Bouncing attack and its third-bounce research | A sling-staff runner on foot (no mount) |
| Springbough | Bolt siege | Attacks trees | Sticky Resin slow ground |
| Ambermail | Spell-immune anti-caster | Spell immunity; area dispel that hurts summons | Amber Fleck (no slowing darts) |
| Sapsinger | Shape-changing healer | Heal over time; heavy melee form | Lantern Hymn (no damage-roar buff) |
| Hazeweaver | Debuff and disable caster | Armour debuff with reveal; untargetable disable (on the ground, never lifted) | Fog Bank |
| Woodgnaw | Giant tank | Taunt; Pierce-resist research | Fell (a log for Tapsters, no buff) |
| Treeglider | Anti-air flyer | Air-only attack; detection research | Dive; Lantern Drop (no archer-rider merge) |
| Glimmerswarm | Magic-immune anti-caster flyer | Spell immunity; phase-on-hit | Snuff (drains mana on hit) |
| Thistleship | Heavy air vs ground | Anti-building research | Burning ground |

### A5.4 Minimum ability numbers

| Ability (unit) | Mana | Cooldown | Range / radius | Duration | Autocast default | Notes |
|---|---|---|---|---|---|---|
| Hang Lantern (Tapster) | – | 30 s | Its tapped tree; 8 m vision | 60 s | – | One per Tapster (a new one replaces the old); no true sight |
| Resin Seal (Tapster) | – | – | Seeks within 8 m | – | **off** | Repair (rules §4.8) |
| Scrape Clean (Ambermail) | 40 | 4 s | Cast 6 m, radius 3 m | Instant | **off** | Removes dispellable buffs (rules §10.4); 200 damage to enemy summons |
| Amber Fleck (Ambermail) | passive | – | – | 10 s | – | 3 hits within 6 s on one target |
| Warm Sap (Sapsinger) | 75 | 4 s | 6 m | 12 s | **on** | 300 HP over 12 s; refreshes, never stacks |
| Lantern Hymn (Sapsinger, Second Verse) | 75 | 30 s | Radius 8 m | 20 s | – | Allies count as in noonlight (day sight, +1.5 HP/s, Warm Strings). A status, not a zone: it reveals nothing |
| Bark Coat (Sapsinger, Full Chorus) | – | 3 s | Self | Toggle | – | 3 s switch each way; HP fraction kept; no Warm Sap or Lantern Hymn in Bark Coat |
| Midge Haze (Hazeweaver) | 30 | 0 s | 7 m | 75 s (heroes 20 s) | **on** | −3 armour; target revealed |
| Fog Bank (Hazeweaver, Second Verse) | 90 | 25 s | Cast 8 m, radius 6 m | 15 s | – | Blocks ranged targeting from outside into the fog |
| Set in Amber (Hazeweaver, Full Chorus) | 110 | 12 s | 7 m | 6 s | – | Non-heroes only; sealed in amber on the ground |
| Tail Slap (Woodgnaw) | – | 12 s | Radius 5 m | 4 s | **off** | Taunt (rules §10.2) |
| Fell (Woodgnaw) | – | 10 s | Adjacent tree | 3 s channel | – | 20-lumber log |
| Dive (Treeglider) | passive | – | – | 2 s slow | – | Ready after 3 s without attacking |
| Lantern Drop (Treeglider, T3 research) | – | 45 s | 6 m noonlight below it | 20 s | – | Untargetable ground effect; one per Treeglider |
| Lantern Riders (Treeglider, T2 research) | passive | – | True sight 9 m | – | – | Detection (rules §11) |
| Wink Out (Glimmerswarm) | – | 7 s | Self | 1.2 s | **on** | Triggers on taking damage |
| Snuff (Glimmerswarm) | passive | – | – | – | – | Burns 8 mana per hit |
| Open the Shutters (Lodge) | 4 charges | 60 s | Within 30 m; radius 16 m | 15 s | – | §A3.2 |

## A6. Heroes

Global hero rules apply. Heroes are trained at the **Calling Pier**: they arrive across the lake by boat. All heroes: sight 28.1 / 12.5 m,
radius 0.55 m (rules §6.6, §7.10).

| Hero (id) | Role | Primary | STR (+/lvl) | AGI (+/lvl) | INT (+/lvl) | Base damage (+primary) | Base armour | Base CD (s) | Attack (range) | Targets | Speed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Lark Captain** (`sylvan_hero_lark_captain`) | Archer captain (AGI ranged, ranged aura) | AGI | 17 (+1.8) | 21 (+2.3) | 16 (+1.9) | 2–10 | −1 | 2.1 | Missile 8.4 m, 20 m/s | G+A | 4.7 |
| **Thicket Weaver** (`sylvan_hero_thicket_weaver`) | Grove caster (INT root and control) | INT | 16 (+1.8) | 13 (+1.2) | 21 (+3.0) | 3–9 | −1 | 2.2 | Missile 7.0 m, 15 m/s | G+A | 4.4 |
| **Lampbreaker** (`sylvan_hero_lampbreaker`) | Mana-draining melee (AGI) | AGI | 20 (+2.1) | 22 (+2.4) | 15 (+1.6) | 2–8 | −2 | 2.1 | Melee 1.2 m (pole) | G | 4.8 |
| **Reedstalker** (`sylvan_hero_reedstalker`) | Assassin (AGI melee, mobility) | AGI | 18 (+2.0) | 22 (+2.5) | 14 (+1.5) | 3–9 | −1 | 2.0 | Melee 0.9 m | G | 4.9 |

Derived values (HP / mana / armour / damage / attack cooldown):

| Hero | Level 1 | Level 5 | Level 10 |
|---|---|---|---|
| Lark Captain | 525 / 240 / 5.3 / 23–31 / 1.48 s | 700 / 345 / 8.0 / 32–40 / 1.31 s | 925 / 495 / 11.3 / 43–51 / 1.15 s |
| Thicket Weaver | 500 / 315 / 2.9 / 24–30 / 1.75 s | 675 / 495 / 4.1 / 36–42 / 1.64 s | 900 / 720 / 5.9 / 51–57 / 1.51 s |
| Lampbreaker | 600 / 225 / 4.6 / 24–30 / 1.46 s | 800 / 315 / 7.3 / 33–39 / 1.30 s | 1050 / 435 / 10.9 / 45–51 / 1.13 s |
| Reedstalker | 550 / 210 / 5.6 / 25–31 / 1.39 s | 750 / 300 / 8.6 / 35–41 / 1.22 s | 1000 / 405 / 12.2 / 47–53 / 1.06 s |

| Hero | Look (one oversized prop) | Proper names (one at random, "Title: Name") |
|---|---|---|
| Lark Captain | Tall archer, a lark-feather crest on her leaf hood, and a **huge birch longbow strung with amber beads** | *Tieve Brightstring, Saile Longdraw, Meive Amberbead, Roive Highnock* |
| Thicket Weaver | Stooped old elf with a **towering withy back-loom** above his head and a hooked weaving staff. No antlers | *Senne Barkhand, Aldre Withyknot, Tove Warpwise, Orre Tightweave* |
| Lampbreaker | Wiry **lamp-thief** in a patched leaf hood hung with stolen lantern-glass shards, a **shattered lantern-cage gauntlet** leaking light, and an iron-shod punt pole | *Kesse the Unlit, Lotte Wickpinch, Nive Shardglass, Ebbe Snuffhand* |
| Reedstalker | Lanky **male** eel-fisher under a **tall reed-sheaf cloak** that rises from his shoulders like a bulrush crown (no hood), with a long fishing gaff and a dart pouch | *Ivve Stillwater, Arre Reedfoot, Pelle Quietgaff, Sande Mudwade* |

**Kits** (ranks 1 / 2 / 3; mana; cooldown). FE rules 1–3 apply (Conventions).

| Hero | Q | W | E | R (ultimate, level 6) | FE |
|---|---|---|---|---|---|
| Lark Captain | **Farshot** (unit, 12 m): 90 / 150 / 210 Spell damage, **+35 %** if the target is more than 8 m away. 85 mana, 10 s. *Orig* | **Lark Flight** (self): the next 3 / 4 / 5 attacks each split to 2 extra enemies within 4 m at 50 % damage. 60 mana, 14 s. *Orig* | **Bowyer's Hum** (aura, 9 m): allied ranged attackers deal +8 / 16 / 24 % damage. Ranged heroes count; structures do not. *FE (ranged damage aura)* | **Midsummer Hour** (point within 12 m, 12 m radius, 20 s): allies inside count as in daylight (day sight, +15 % attack speed; for Larkbows this **replaces** *Warm Strings* and does not add to it). Enemies inside are revealed and deal −15 % damage. Ends in a 150 Spell flash that hits the enemies inside. 150 mana, 150 s. *Orig* | **1** |
| Thicket Weaver | **Withy Snare** (unit, 9 m): woven withy hoops snap shut around a ground unit's legs, rooting it 2 / 3 / 4 s (heroes 1 / 1.5 / 2) for 12 / 18 / 24 Spell damage/s. Withies only, no living roots. 70 mana, 10 s. *FE (root)* | **Thatch Screen** (point, 9 m): a 6 m wicker screen, **perpendicular to the caster→point direction and centred on the point**, for 8 / 11 / 14 s that **blocks enemy missile attacks** crossing it. Units walk through it. 80 mana, 18 s. *Orig* | **Shuttle Throw** (unit, 8 m): a loom shuttle bounces from the target through up to 3 / 4 / 5 enemies, each within 4 m of the last, and **threads** them for 6 s. A threaded unit more than 4 m from every other threaded unit is yanked 1.5 m toward the nearest one and takes 40 / 60 / 80 Spell damage (at most once per second per unit). **Threading needs at least 2 threaded units: when fewer than 2 remain alive, threading ends at once. Each threaded unit triggers at most 2 times per cast** (at most 80 / 120 / 160 per unit). The cast is refused, with no mana spent, if the target has no other enemy within 4 m. 90 mana, 16 s. *Orig* | **Warp and Weft** (a 16 m line centred on a point within 10 m, **perpendicular to the caster→point direction**, 12 s; a drag-to-rotate input can come later): a woven hurdle fence. **Enemy** ground units cannot cross it; allies pass through. Enemies within 1 m of it move 30 % slower. No trees, no healing. 160 mana, 150 s. *Orig* | **1** |
| Lampbreaker | **Drink the Light** (unit, 4 m): burns 60 / 120 / 180 mana, deals that much Spell damage, and she gains 50 % of it. 55 mana, 9 s. *FE (mana-drain nuke)* | **Wick Draw** (passive; no toggle, no mana upkeep): each enemy spell cast within 6 m gives her 6 / 10 / 14 mana and +3 / 4 / 5 % attack speed for 10 s (up to 5 stacks, refreshed per cast). *Orig* | **Punt Vault** (point, 3–9 m): vaults over units and one cliff level. Landing deals 40 / 80 / 120 and knocks back 1.5 m. 60 mana, 12 / 10 / 8 s. *Orig* | **Pocket the Flame** (enemy hero, 6 m, 20 s): she steals **12 points of the target's primary attribute** and gains them as AGI; the target stays revealed for the duration. Both heroes' HP and mana keep their percentages when the attributes change, and the points return when it ends. Not dispellable. 125 mana, 120 s. *Orig* | **1** |
| Reedstalker | **Reed Darts** (self, 6 m): up to 6 nearest enemies take 60 / 110 / 160 Spell damage and −20 % move speed for 2 s. 85 mana, 10 s. *FE (around-self volley)* | **Slip Under** (point, 10 m; must start or end in shallow water or within 2 m of a tree): instant reposition; the next attack deals +40 / 60 / 80. 45 mana, 12 / 9 / 6 s. *FE (short teleport, restricted)* | **Reed Ambush** (passive): while he stands in shallow water or within 2 m of a tree, his first hit on a target deals +60 / 100 / 140 % and roots it for 1 s; the same target cannot trigger it again for 8 s. *Orig* | **Spring Flood** (point within 10 m, 10 m radius, 12 s): the ground floods into shallow water. Enemy ground units inside move 30 % slower and have −2 armour. Inside the flood, *Slip Under* ignores its water-or-tree requirement and its cooldown resets once, the first time he enters; he gains +30 % move speed inside, and the flood counts as shallow water for *Reed Ambush*. The flood is visual and status only: pathing and building placement do not change. 150 mana, 120 s. *Orig* | **2** |

FE audit: one Glaer hero (Reedstalker) uses 2 FE; the other three use 1 (FE rule 2). No Glaer hero uses its WC3 counterpart's
ultimate, which removes the most recognisable signature from each kit. Round 2 also broke two kits' match with well-known heroes from
the WC3 custom-map lineage (ip-safety §1.2): the Lampbreaker's ultimate is now *Pocket the Flame* and *Wick Draw* is a plain passive; the
Reedstalker's area-silence ultimate became *Spring Flood*, and *Reed Ambush* no longer reads as a back-stab.

**One-line pathing rule** (Warp and Weft, and the Wakeful Sealed Precinct): units standing on cells that become blocked are pushed to the
nearest free cell **on the side their centre is on** (never into unwalkable cells; if none is free within 3 m, that cell stays open).
Warp and Weft blocks cells for enemy players' ground units only (a per-player pathing mask); flyers ignore both.

## A7. Buildings and tech tiers

```
Stilt Lodge (T1) ──► Lantern Lodge (T2, needs Calling Pier) ──► Amber Lodge (T3, needs Resinworks)
│
├─ Stilt Larder (+10 food)
├─ Calling Pier ── heroes
├─ Fletchery ── Larkbow, Stoneskipper [Resinworks], Springbough [T2 + Resinworks]
├─ Resinworks ── weapon and armour lines, Deep Spigots, Lantern Glass; lumber drop-off ── Glare Post (tower, built directly)
├─ Trinket Stall ── items (stock grows with tier: T1, T2, T3)
│
├─ [T2] Singers' Hall ── Ambermail, Sapsinger, Hazeweaver; Woodgnaw [T3]
├─ [T2] High Drey ── Treeglider; Lantern Riders; Lantern Drop [T3]
└─ [T2] Thistle Mooring ── Glimmerswarm; Thistleship [T3]
```

Every building has Fortified armour 5 and 14.0 / 9.4 m sight unless stated (rules §8). Inside noonlight, Glaer structures regenerate +1 HP/s.
Footprints are in 0.5 m pathing cells (the kingdom's convention: halls 10×10, production buildings 8×8, altar, smithy and shop 6×6,
supply and towers 4×4). Hall upgrades keep the footprint. Stilts do not change the footprint; units never walk under a building.

| id | Building | Role | Needs | Gold / lumber | Time (s) | HP | Footprint | Food | Function |
|---|---|---|---|---|---|---|---|---|---|
| `sylvan_stilt_lodge` | **Stilt Lodge** | Hall T1 | – | 380 / 190 | 160 | 1550 | 10×10 | +10 | Tapster; gold and lumber drop-off; Summerhoard 12 (sunlit yard 14 m); *Open the Shutters* |
| `sylvan_lantern_lodge` | **Lantern Lodge** | Hall T2 (upgrade) | Calling Pier | +300 / 200 | 130 | 2050 | 10×10 | +12 | Tier 2, hero 2 |
| `sylvan_amber_lodge` | **Amber Lodge** | Hall T3 (upgrade) | Lantern Lodge, Resinworks | +340 / 220 | 140 | 2600 | 10×10 | +14 | Tier 3, hero 3 |
| `sylvan_stilt_larder` | **Stilt Larder** | Supply | – | 140 / 40 | 45 | 500 | 4×4 | +10 | A stilted storehouse; may stand in shallow water |
| `sylvan_calling_pier` | **Calling Pier** | Hero altar | – | 180 / 50 | 60 | 900 | 6×6 | – | Trains and revives heroes |
| `sylvan_fletchery` | **Fletchery** | Barracks | – | 170 / 60 | 60 | 1300 | 8×8 | – | Larkbow, Stoneskipper, Springbough; *Long Draw*, *Skipping Lore*, *Sticky Resin* |
| `sylvan_resinworks` | **Resinworks** | Smithy and lumber mill | – | 150 / 60 | 60 | 1100 | 6×6 | – | Lumber drop-off; four upgrade lines (§A7.2); *Deep Spigots*, *Lantern Glass*; enables the Glare Post |
| `sylvan_singers_hall` | **Singers' Hall** | Caster hall with the giant | Lantern Lodge | 165 / 120 | 65 | 1100 | 8×8 | – | Ambermail, Sapsinger, Hazeweaver; Woodgnaw at T3. Caster trainings; *Thick Pelt* |
| `sylvan_high_drey` | **High Drey** | Air nest | Lantern Lodge | 140 / 110 | 55 | 950 | 8×8 | – | Treeglider; *Lantern Riders* (T2), *Lantern Drop* (T3). A tall stilted nest-platform (a drey is a squirrel's nest) |
| `sylvan_thistle_mooring` | **Thistle Mooring** | Air mooring | Lantern Lodge | 160 / 160 | 65 | 1100 | 8×8 | – | Glimmerswarm; Thistleship at T3; *Burning Resin* |
| `sylvan_glare_post` | **Glare Post** | Tower (built directly; no scout-tower step) | Resinworks | 110 / 50 | 40 | 480 | 4×4 | – | Pierce 18–22, CD 1.1 s, 10.0 m, G+A, arrow 20 m/s. **Level 3** (XP). Sight 16 / 10 m (16 / 16 while it burns noonlight). Summerhoard 6 (10 m noonlight; sunlit yard 10 m). Static, never walks |
| `sylvan_trinket_stall` | **Trinket Stall** | Faction shop | – | 130 / 30 | 60 | 480 | 6×6 | – | Items (§A7.4) |

### A7.2 Upgrades and research

Weapon and armour lines (rules §5.4; L2 needs T2, L3 needs T3). Weapon levels add each unit's `upgrade_damage` (rules §5.4 default).

| Line (Resinworks) | Level 1 | Level 2 | Level 3 | Effect per level | Affects |
|---|---|---|---|---|---|
| **Hardened Points** | 110 g / 60 l, 60 s | 180 / 170, 75 s | 260 / 290, 90 s | `upgrade_damage` | Larkbow, Stoneskipper, Springbough, Ambermail |
| **Gnaw-and-Talon** | 110 / 60, 60 s | 180 / 170, 75 s | 260 / 290, 90 s | `upgrade_damage` | Woodgnaw, Sapsinger in Bark Coat, Treeglider, Glimmerswarm, Thistleship |
| **Resin Varnish** | 130 / 70, 60 s | 160 / 180, 75 s | 190 / 270, 90 s | +2 armour | Foot units: Larkbow, Stoneskipper, Ambermail, Sapsinger (both forms), Hazeweaver |
| **Tarred Shingles** | 130 / 70, 60 s | 160 / 180, 75 s | 190 / 270, 90 s | +2 armour | Tarred bark shingles on saddle-roofs, gondolas, lantern cages and the sledge: Woodgnaw, Treeglider, Glimmerswarm, Thistleship, Springbough |

| Building | Research | Tier | Gold / lumber | Time | Effect |
|---|---|---|---|---|---|
| Fletchery | *Long Draw* | T2 | 125 / 100 | 55 s | Larkbow +1.4 m range |
| Fletchery | *Skipping Lore* | T2 | 150 / 100 | 60 s | Stoneskipper third skip at 25 % |
| Fletchery | *Sticky Resin* | T2 | 125 / 150 | 60 s | Springbough impacts leave resin 5 s (−30 % move speed) |
| Resinworks | *Deep Spigots* | T2 | 100 / 0 | 60 s | +2 lumber per trip (10 → 12) |
| Resinworks | *Lantern Glass* | T2 | 125 / 100 | 50 s | Summerhoard capacity +4; charging +1 per 15 s (§A3.2) |
| Singers' Hall | Sapsinger and Hazeweaver **Second Verse** | T2 | 100 / 50 each | 60 s | +40 HP, +50 mana, +1 damage; Lantern Hymn / Fog Bank |
| Singers' Hall | Sapsinger and Hazeweaver **Full Chorus** | T3 | 150 / 100 each | 70 s | +40 HP, +50 mana, +1 damage; Bark Coat / Set in Amber |
| Singers' Hall | *Thick Pelt* | T3 | 150 / 200 | 60 s | Woodgnaw −25 % Pierce damage taken |
| High Drey | *Lantern Riders* | T2 | 75 / 75 | 40 s | Treegliders gain true sight 9 m |
| High Drey | *Lantern Drop* | T3 | 150 / 150 | 60 s | Treeglider ability: a 6 m noonlight for 20 s below it, cooldown 45 s (§A5.2) |
| Thistle Mooring | *Burning Resin* | T3 | 150 / 175 | 75 s | Thistleship +50 % vs buildings; 4 s burning ground (10 damage/s) |

### A7.4 Trinket Stall items (faction shop)

Potion values stay off the common WC3 values (250 HP, 150 mana) and off the kingdom's (240, 140), as kingdom §7.4 asks.

| Item | Hall tier | Cost | Stock / restock | Effect |
|---|---|---|---|---|
| **Lake Whistle** | T1 | 325 g | 2 / 120 s | Blow it for 3 s (rules §6.8 channel), then the hero and **up to 11 of your own units within 6 m** teleport next to your nearest finished Lodge. The first hero gets one free |
| **Birch Syrup** | T1 | 140 g | 3 / 60 s | +270 HP over 6 s (thick syrup; `heal_over_time`; taking damage does not cancel it) |
| **Cloudberry Cordial** | T1 | 120 g | 3 / 60 s | +160 mana at once |
| **Birch-Bark Poultice** | T1 | 120 g | 2 / 90 s | Your non-structure units within 6 m of the hero restore 160 HP over 8 s (below the neutral Picnic Hamper's 180 HP for 200 g) |
| **Lantern Stake** | T1 | 70 g | 2 / 60 s | 2 charges. Plants a caged-teardrop lantern on a stake at a point within 5 m: 10 m vision for 180 s, **no true sight** (`place_ward`; a `ward` with 50 HP) |
| **Bottled Noon** | T2 | 80 g | 2 / 60 s | A 9 m noonlight at a point within 8 m for 15 s, day or night (reveals invisible enemies inside; Glaer inside get the noonlight effects) |
| **Tar-Water Tonic** | T2 | 100 g | 1 / 90 s | The hero is spell immune for 10 s |
| **Summer Bead** | T2 | 350 g | 1 / 120 s | Permanent, unique: the hero always counts as in noonlight (day sight at night, +1.5 HP/s, day-keyed abilities on) |
| **Noon-Stone Chip** | T3 | 300 g | 1 / 180 s | Sets a chip of noon-stone on a post at a point within 6 m for 120 s: a 10 m noonlight, day or night, holding 6 charges (1 per 20 s). A `ward` with 250 HP, Fortified 2; it counts as a Glaer structure for noonlight only |

| Tier | Unlocks |
|---|---|
| T1 Stilt Lodge | Tapster, Larkbow, Stoneskipper, Glare Post; hero 1; level-1 upgrades; shop T1 (Lake Whistle, Birch Syrup, Cloudberry Cordial, Birch-Bark Poultice, Lantern Stake) |
| T2 Lantern Lodge | Springbough, Singers' Hall, High Drey, Thistle Mooring, Ambermail, Sapsinger, Hazeweaver, Treeglider, Glimmerswarm; hero 2; Second Verse trainings; *Long Draw*, *Skipping Lore*, *Sticky Resin*, *Deep Spigots*, *Lantern Glass*, *Lantern Riders*; level-2 upgrades; shop T2 (Bottled Noon, Tar-Water Tonic, Summer Bead) |
| T3 Amber Lodge | Woodgnaw, Thistleship; hero 3; Full Chorus trainings (Bark Coat, Set in Amber); *Thick Pelt*, *Lantern Drop*, *Burning Resin*; level-3 upgrades; shop T3 (Noon-Stone Chip) |

### A7.5 Command cards and hotkeys (Classic preset; rules §18.4)

Letters are unique per card (`Defs` validates this). Unit cards always carry Move **M**, Stop **S**, Hold **H**, Attack **A**, Patrol **P**;
heroes add Learn **O** and abilities **Q / W / E / R** in kit order (§A6). Production buildings carry Rally **R**. Unit abilities use
**Q / W / E** in the order listed in §A5.1. The Grid preset uses positions only.

| Card | Buttons (letter) |
|---|---|
| Tapster | Gather **G**, Return Cargo **C**, Resin Seal **R** (autocast toggle by right-click), **Build Basic B**, **Build Advanced V**, Hang Lantern **L** |
| Build Basic (B) | Stilt Lodge **H**, Stilt Larder **L**, Calling Pier **C**, Fletchery **F**, Resinworks **W**, Glare Post **G**; Esc back |
| Build Advanced (V) | Singers' Hall **S**, High Drey **D**, Thistle Mooring **M**, Trinket Stall **T**; Esc back |
| Stilt / Lantern / Amber Lodge | Tapster **T**, Open the Shutters **O**, Upgrade to the next tier **U**, Rally **R** |
| Calling Pier | Lark Captain **C**, Thicket Weaver **W**, Lampbreaker **L**, Reedstalker **E** (a dead hero's button becomes Revive in place), Rally **R** |
| Fletchery | Larkbow **L**, Stoneskipper **S**, Springbough **B**, Long Draw **D**, Skipping Lore **K**, Sticky Resin **T**, Rally **R** |
| Resinworks | Hardened Points **H**, Gnaw-and-Talon **N**, Resin Varnish **V**, Tarred Shingles **T**, Deep Spigots **D**, Lantern Glass **G** |
| Singers' Hall | Ambermail **A**, Sapsinger **S**, Hazeweaver **H**, Woodgnaw **W**, Sapsinger Second Verse **V**, Sapsinger Full Chorus **C**, Hazeweaver Second Verse **E**, Hazeweaver Full Chorus **U**, Thick Pelt **P**, Rally **R** |
| High Drey | Treeglider **T**, Lantern Riders **L**, Lantern Drop **D**, Rally **R** |
| Thistle Mooring | Glimmerswarm **G**, Thistleship **T**, Burning Resin **B**, Rally **R** |
| Trinket Stall | Lake Whistle **W**, Birch Syrup **S**, Cloudberry Cordial **C**, Birch-Bark Poultice **P**, Lantern Stake **L**, Bottled Noon **N**, Tar-Water Tonic **T**, Summer Bead **B**, Noon-Stone Chip **K** |
| Unit abilities | Springbough: Attack Ground **G**. Ambermail: Scrape Clean **Q**. Sapsinger: Warm Sap **Q**, Lantern Hymn **W**, Bark Coat **E**. Hazeweaver: Midge Haze **Q**, Fog Bank **W**, Set in Amber **E**. Woodgnaw: Tail Slap **Q**, Fell **W**. Treeglider: Lantern Drop **Q**. Glimmerswarm: Wink Out **Q** |
| Heroes | Lark Captain: Farshot **Q**, Lark Flight **W**, Bowyer's Hum **E**, Midsummer Hour **R**. Thicket Weaver: Withy Snare **Q**, Thatch Screen **W**, Shuttle Throw **E**, Warp and Weft **R**. Lampbreaker: Drink the Light **Q**, Wick Draw **W**, Punt Vault **E**, Pocket the Flame **R**. Reedstalker: Reed Darts **Q**, Slip Under **W**, Reed Ambush **E**, Spring Flood **R** |

## A8. Voice and music

**Voice personality: bright, unhurried light-hoarders.**
- They rate everything by how much light it has, tell the time in "lights left", and take shade personally.
- They are a little smug about their summers and quietly terrified of the dark.
- Delivery is soft and even, with a lilting chant cadence. **No faux Finnish or Baltic accent.**
- Their metaphors are light, resin, lanterns and lakes. Never weather (a clans trait), hospitality or ledgers.
- Each unit gets one tic. For example, the Tapster counts drips; the Woodgnaw rider sings to the beaver mid-line.
- **Annoyed lines may not use poke / poked / poking or paraphrase any WC3 line** (check each against the quote pages; ip-safety §2.2).
  Self-aware lines about being clicked are allowed in the faction's own idiom, e.g. Tapster: *"Click all you like. Resin runs at resin speed."*

**Sample lines** (original; check against the WC3 night-elf quote page before recording):
- Larkbow (What): *"Mm? Step aside, friend. You're standing in my light."*
- Tapster (Annoyed, last in sequence): *"Forty-one drips… forty-two… and now I've lost count. There goes an hour of summer."*

**VO review list (both factions; internal audit, never in prompts or data).** Reject any line that contains or paraphrases: "high noon" (a Blizzard *Overwatch* catch-phrase),
"as you wish", "if that is your wish", "I wish only to serve", "stop poking me", any use of poke / poked / poking, or any other WC3
quote-page line. Self-aware lines about being clicked are allowed in each faction's own idiom (as kingdom §3.3 and clans §3.1 allow).
`high noon` and `it's high noon` are in `tools/ip/banned_terms.txt` under catch-phrases (added in round 2).

**Music:**
- Plucked box-zither, birch-bark horn, wooden clappers, soft frame drum and bowed lyre.
- An alternating two-voice wordless chant. Lilting 5/4 and 6/8, Aeolian or Dorian, 72–96 BPM.
- **Avoid** an airy solo female voice with harp and flute as the lead colour (too close to the nearest rival race's sound; §A9).

## A9. Distinctness rubric (ip-safety §3.2; nearest WC3 race: the forest elves)

| Axis | WC3 forest elves | Glaermere | Differs? |
|---|---|---|---|
| 1. Silhouette | Huge upswept ears, crescent glaives, owls, antlers, big-cat mounts, walking tree buildings | Swept-back leaf hoods, bark capelets, caged lanterns, drooping ears; beaver, flying squirrel, thistle balloon; gabled stilt houses | **Yes** (required) |
| 2. Palette | Violet, teal, silver | Moss sage, birch white with charcoal dashes, small amber | **Yes** |
| 3. Materials | Moonstone, silver, living wood, leaves | Birch bark, amber and resin, nettle cloth, tar, withies | **Yes** |
| 4. Culture | Moon cult, night, ancient temple ruins | Northern lakeland pile-dwellings, amber craft, resin tapping, day-keeping | **Yes** |
| 5. Signature mechanic | Non-felling wisps, mine entangling, uprooting, night stealth and regeneration, moon wells, eating trees, the archer-on-flyer merge | Tapping (the one WC3-derived mechanic, re-presented) plus original Summerhoard (noonlight and the sunlit yard) and Stilt-built. Fell gives no combat buff, Hang Lantern is tree-bound, and there is **no archer-rider merge** (round 2 replaced it with *Lantern Drop*) | **Yes** (within policy after round 2. Honest history: Partial before round 1, and still Partial after round 1 because the merge was a second WC3 signature) |
| 6. Names and voice | WC3 unit, hero and place names; solemn, mystic | All original; sunny, smug light-hoarders | **Yes** |

**Result: 6 / 6 after round 2** (5 / 6 before round 1, and 5 / 6 in honest terms after round 1). **Signature budget:** Tapping is the
faction's one WC3-derived signature (ip-safety §2.3). If a later fidelity pass insists on an archer-rider merge, the faction must drop
Tapping for ordinary felling instead (IP wins under this doc's conflict rule). **No summons by design:** the IP fixes keep summons
out of the grove caster's kit (its WC3 counterpart's best-known move), and no Glaer hero or unit summons anything. Home sustain (the sunlit yard and noonlight, §A3.2) and the
T1 *Birch-Bark Poultice* carry the creep-walk-home-creep loop instead (mechanics §11.3). **Tech-tree deviations** (deliberate, to break
the WC3 "object hierarchy" while keeping the build-order logic): (1) the debuff-and-disable caster trains at the caster hall (Singers'
Hall), not the air building; (2) the magic-immune anti-caster flyer trains at the Thistle Mooring, which becomes a T2 building, so the
second air building opens a tier early; (3) the anti-air flyer's nest (High Drey) trains only that flyer and researches its lanterns.
Residual risk: elf archers and a druid hero are genre staples. Run the squint test on every Larkbow, Lark Captain and Thicket Weaver
concept before image-to-3D.

---

# Part B: `deathless`, the Long Wake

## B0. At a glance

| | |
|---|---|
| **Display name** | **The Long Wake** (UI: "Long Wake"). **Internal until the title clearance pass**; the marketing fallback is **"the Unending Wake"** (Part D item 7) |
| **People** | **the Wakeful** (singular "a Wakeful", adjective "Wakeful"). The risen dead of the **Old Families**, plus everyone they have since "adopted" |
| **Emblem** | **The Remembered Face**: a calm chalk-white mask with closed eyes above a chalk-outlined offering bowl, inside a ring of five grave-rose dried roses, on soot. Terracotta never fills the emblem or a banner field |
| **Motto** | "Every face kept." |
| **Cultural inspiration** | Ancient Mediterranean funerary culture of extinct civilisations: Etruscan round tumulus tombs and painted tomb walls, terracotta sarcophagus lids with reclining figures, Roman ancestor-mask processions and patron households, rose-days for the dead, cinerary urns with head-shaped lids, double pipes and lyre. **Not** Egyptian (no mummies, pyramids, jackals or "canopic" jars), not Nordic or gothic, and no frost |
| **Palette** | Cool soot lacquer and chalk bone as the two masses, with fired-clay terracotta accents (masks, urns, roof tiles), grave-rose and tarnished silver; pale lamp-rose glow. No purple, cyan or toxic green, and no red-brown masses |
| **WC3-derived mechanic (the one allowed)** | **The Pall**: a ground layer that helps the Wakeful. It is the plague-ground idea, re-presented and softened (§B3.1) |
| **Original mechanic** | **Heirloom Masks**: fallen Wakeful drop their masks, and the next to pick one up inherits its rank (§B3.2) |
| **Play pattern** | Cheap, fast melee, sturdy siege and strong sustain on their own Pall. Veteran Lineage snowballs if they win trades. Weak to burst that kills before masks pass on, to fights far from Pall, and to mask denial |
| **Role mirror** (internal) | Worker, invisible scout (marks what it watches; detects only while planted), fast cheap melee, ranged anti-air pinner, anti-air flyer, corpse-raising caster, curse-and-shield caster, healing construct, anti-magic flyer (its own unit), siege cart, T3 heavy melee, heavy air. Heroes: dark commander (army aura, raised army), matriarch caster (nuke, armour buff), noble lord (sleep, life-steal aura), mason tank (line stun) |

## B1. Identity

**Names.**
- A *wake* is the vigil kept over the dead. The Long Wake is a vigil nobody has ended, and its people literally never sleep.
- The names use no rival naming patterns (the avoided names are in the internal audit block below).
- In-world, the faction is a federation of **the Old Families**, each led by its oldest masks. The UI uses "Long Wake" and "Wakeful".

**Naming rules.**
- Units and buildings get English funeral vocabulary: Sexton, Eulogist, Cenotaph, Columbarium.
- Personal names are invented Latinate names ending *-us / -a / -ia*, plus a family or funeral epithet, e.g. *Aulenus the Unfinished*.
- No real Roman or Etruscan people, no deities, and no liturgical words (requiem, mass, saint, abbot, last rites, *tenebrae*).
- No "*N*th of the Name" formula (a famous TV-series formula).

**Tone guard** (the aristocratic-afterlife look of a well-known MMO expansion sits close to this faction):
- No gothic or Victorian dress, no crimson-and-gold, and no bats.
- Never use "court", "sin", "atonement", "anima" or "masquerade ball" in names, tooltips, lore or lines.
- Guests stay **festive funeral mourners** at a wake, never party-goers at a court. The dead keep masks and processions, not registers of
  sins, and their comic servants are household retainers, not court flunkeys.

> **Internal audit, never in prompts or data** (ip-safety §2.8). Avoided rival names and stems: Scourge, Forsaken, Lich, Necro-,
> Death Knight, Ghoul, Crypt. "Great Houses" was dropped because a federation of undead Houses is a known *World of Warcraft* realm
> structure. The tone guard above answers *World of Warcraft: Shadowlands* (gothic court parties, sin registers, comic servants). The
> Pomp-Bearer was renamed from the round-1 "Imaginifer", one syllable from a *Warhammer 40,000* martyr-image standard-bearer.

**Emblem rules.**
- Read test at 24 px: "a face over a bowl".
- Banners are horizontal "runner" cloths on T-poles, with tasselled ends.
- **Never** use skulls with horns, spikes, crowns, crosses or other religious symbols, purple, or a cyan glow.

**Lore (original).**

> Along the warm southern coast, the Old Families buried their dead in round hill-tombs. Each tomb had painted
> walls and a mask of the deceased hung by the door, so that no ancestor would ever be forgotten. The Families took
> remembrance further than anyone intended. When the last heirs died, the families simply did not stop. Each family still
> walks behind its masks (patriarchs, dowagers, retainers and clients), unrolling a grey **Pall** before it like a carpet laid
> for a procession. Whoever falls beneath it is quietly handed a mask and a place at the back of the procession. The Wakeful are not cruel. They are
> very old, very proud and entirely sleepless. By their reckoning, every field, river and kingdom from the coast to the northern
> lakes is "the family estate", currently overrun by trespassers. They call it the Long Wake: a funeral that, out of good
> manners, nobody has ever ended.

## B2. Visual identity

**Silhouette rules:**

1. **Oversized masks are the faction read.** Each unit type wears a mask about 1.4× head size with its own fixed expression:
   grinning servant, open-mouthed orator, disdainful dowager, stern general. The faces are gone, so the mask *is* the face.
2. **Lineage poles.** Units with Lineage (§B3.2) carry 1–3 small masks on a short pole behind the shoulder. This rank read is unique to the faction.
3. **Long draped shapes.** Shrouds, togas and runner banners give A-line silhouettes. **Burial linen has weighted, square-cut, tasselled
   hems; never tattered or ragged.** Of the cloth-draped figures, **only the Drift-Shroud flies**; everyone else walks with feet on the
   ground (no hover gap). Everyone stands **upright and processional**: no hunching, no crawling, and **no spikes anywhere**.
4. **Round, closed forms.** Urns, wheels, drum-mounds and sarcophagus boxes.
   **No spider bodies, stitched flesh, hooks and cleavers, gargoyles, wings, frost or skeletal horses.**

**Palette:**

| Role | Name | Hex | Where |
|---|---|---|---|
| Mass 1 | Soot lacquer | `#25262A` (neutral blue-black) | Shrouds, togas, cart and barge lacquer |
| Mass 2 | Chalk bone | `#DCD0B9` | Bones, plaster masks, tumulus stone drums, half-columns, shroud linings, banner fields |
| Accent | Fired clay (terracotta) | `#C07E5C` | Masks, urns and roof tiles only; **at most about 25 % of any unit's albedo** |
| Accent | Grave-rose | `#9E4F63` | Dried roses, ribbons, crest plumes (saturation ≤ 45 %, so pink and red team colours still read) |
| Metal | Tarnished silver | `#8C8A86` | Bells, coins, small fittings |
| Ground | Pall grey | `#6F6A66` with grave-rose flecks | The Pall layer |
| VFX (HDR) | Lamp-rose | `#FFC7D1` | Eyes behind the masks, spells, tomb-lamp flames |

Team colour goes on runner banners, mask ribbons, shroud hems, cart canopies and the barge's garlands. **Banners are soot plus chalk plus
team colour, never terracotta on black** (a red-brown on brown-black mass is the palette axis §3.2 bans).
**Not** purple, black-violet, cyan or green glows. **Not** the art doc's Blightmire corruption palette. **No salt crystals or brine-blue
glow** (the neutral Saltbound; Part E).

**Materials.** Fired terracotta, chalk plaster, black lacquer, heavy linen shrouds, dried flowers, tarnished silver, cut limestone.

**Prompt words.** Write "terracotta cinerary urn with a human-head lid", **never "canopic"** (it pulls Egyptian jackal and falcon jars and
a known tabletop Egyptian-undead look).

**Architecture: "drums and mounds".**
- Buildings are **tumuli**: a low drum of chalk-stone blocks under a grassy dome of dead grass and rose-briar.
- A dark doorway is framed by two chalk half-columns with fired-clay capitals, with rows of urns and pairs of tall black cypress doodads.
- **Construction verb: "unearthed".** The ground splits, and the building rises from below as the Sexton digs. The `build_progress` reveal runs top-down from a sunken start.
- **Tier growth of the hall:**
  - **Wake Barrow:** one drum.
  - **Long Barrow:** an elongated mound with a painted frieze of processions and a bronze tomb bell over the door.
  - **Grand Barrow:** three stacked drums crowned by a terracotta reclining couple.
- **Never** stepped pyramids, ziggurats, spiked towers, obelisks or purple stone.

**Squint-test risks** (internal audit):

| Wakeful design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Mourning Legate | Death Knight | **Medium** (dark armoured commander with a raised-army ultimate) | On foot (no skeletal horse), no runeblade, no blue glow, no skull helm, no coil-style nuke, no haste aura. Rose-crested helm and a terracotta-faced shield |
| Urn Hearse | Meat Wagon | **Medium** (siege cart) | Black-lacquer funeral cart with urns, **no corpses, no meat, no gore, and no cargo it collects or hands out** |
| Veiled Mourner | Shade | **Medium** (invisible, unarmed scout) | A short **walking** funeral mute with adult proportions, a veil to the ground with **feet visible**, and a tall candle-pole. Trained normally, never converted from a worker. It detects only while its candle is planted, and its own trick is *Mute Witness*. No hover, no hood with a glowing face, no tattered cloak |
| Pomp-Bearer | Banshee | **Medium** (curse and anti-spell-shield caster) | An ungendered, mask-faced standard-bearer **marching on foot** in a ground-length toga (gliding walk, no hover gap) with a pole of masks. No wailing, no streaming hair, no sheer ghost-woman, no tattered hem. Also near a tabletop martyr-image standard-bearer: the pole carries **masks only, never a saint or martyr icon** |
| Ash Urn and the Released | Obsidian Statue and Destroyer | **Medium** (healing construct; anti-magic flyer) | Two separate units since round 2: **no morph** between them. A fired-clay head-lidded urn that heals HP only and feeds on nearby deaths; the Released is a spiral of ash-rose smoke under a lid-head, not a winged beast, trained at the air pier. It never absorbs buffs; its active is Scatter Ashes |
| Retainer / Tombwalker / Shroudcaster | Ghoul / Abomination / Crypt Fiend | Low | Upright masked servant with a billhook; stone sarcophagus on stub legs; gaunt shrouded thrower whose grounding is a soot-black weighted cloth pinned by a cord to a grave stake (never a white web or net) |
| Drift-Shroud / Wake Barge | Gargoyle / Frost Wyrm | Low | Flying burial sheet with square-cut weighted corners and no stone form; floating funeral boat |
| The Dowager / The Patriarch / Gravewright | Lich / Dreadlord / Crypt Lord | Low | Matriarch with a tall cap (no frost); patrician with a collar of masks (no bat wings); stonemason (no insect, no burrowing, no thorns) |
| Barrows | Necropolis, Ziggurat | Low | Round grassy drum-mounds, never spikes or steps |

## B3. Signature mechanics

### B3.1 The Pall (the one WC3-derived mechanic, presented differently)

| | WC3 plague ground | The Pall |
|---|---|---|
| Look | Purple-black dead ground | A grey burial-cloth and grave-dust texture with dried rose-petal flecks. It **unrolls like a carpet** at 1 m/s from its source, and petals drift above it. Reuses the art doc's spreading-mask shader with our own textures |
| Sources | Hall, supply buildings, the cursed gold mine | Wake / Long / Grand Barrow (16 / 18 / 20 m), Columbarium (8 m), Cenotaph (the hero altar, 6 m), a Gravewright's Stele (*Raise Stele*, 6 m), Sexton *Lay the Pall* (a 6 m patch for 60 s, cooldown 90 s; castable only within 12 m of a friendly structure or construction site), and the *Folded Pall* shop item (6 m for 60 s). *Wide Pall* (T2): +25 % radius for every source |
| Emission | Grows from the source | A source emits Pall at its **fixed radius once complete** (never while under construction). Gameplay coverage reaches the full radius **2 s** after completion; the 1 m/s unroll after that is visual only. Pall never spreads beyond its sources' radii; overlapping sources form a union |
| Building rule | Hard: most buildings require it | **Soft:** build anywhere. A building whose **centre cell is off Pall** builds 30 % slower and has −3 armour; both are checked **live**, so laying Pall under a site removes the penalty at once |
| Own units and structures | Regenerate faster | Wakeful non-heroes +1.5 HP/s; heroes +2 HP/s; Wakeful structures +1 HP/s |
| Enemies | No effect | **Enemy organic units on Pall get no natural HP regeneration**: enemy players' units and neutral hostile creeps alike. Spells, items and fountains still heal. A creep's leash-return regeneration (rules §15.2) is not natural regeneration and still applies. Non-hero natural regen is only 0.25 HP/s, so this matters mainly against heroes |
| Removal | Recedes after its sources die | 10 s after a source dies, its Pall recedes at 1 m/s (gameplay follows the visual edge) |

**Intended play:** start the expansion Barrow, then lay the Pall under it (a Sexton's *Lay the Pall*, which the construction site now
allows, or a *Folded Pall*). The off-Pall penalty is checked live, so it lifts at once; the Barrow becomes a source once complete.
The Pall is home turf: *Lay the Pall* cannot follow the army into the field, and a *Folded Pall* costs 110 g for 60 s. The B4 notes
repeat this for the AI script.

The Wakeful drop the rest of the undead set: the cursed gold mine, workers who summon a building and walk away, melee units that double
as lumberjacks, the siege cart's corpse cargo, supply buildings that turn into towers, the worker sacrificed into an invisible scout,
the two-way tower split, and frost.

### B3.2 Heirloom Masks (original)

| Rule | Value |
|---|---|
| Drop | Only **`undead`-flagged, non-summoned** units drop a **mask** when they die; it lies on the ground for **40 s** (**60 s** if an Ash Urn's *Gathered Ashes* caught the death). A flyer's mask falls to the ground under it. Masks are visible to both players. The Ash Urn, the Released and the Urn Hearse (mechanical), Guests (*Late Guests*) and *Roll Call* units drop none |
| Who takes masks | **Automatic** for Wakeful non-hero, non-summoned **ground** units that walk within 0.5 m (pickup 0.5 s; instant within 3 m inside a Legate's *Standing Vigil*). **Sextons** only on an explicit *Take Mask* order. **Never:** heroes, flyers (rules §12.2), the Veiled Mourner, the Ash Urn, the Released, the Urn Hearse, Guests and *Roll Call* units |
| Inherit | The taker's **Lineage** becomes the higher of its own and **the dead unit's Lineage + 1**, up to **3** |
| Lineage bonus | **+6 % max HP and +6 % damage per rank** (+18 % at rank 3). Ranks are titled *Heir*, *Eminent* and *Venerable*, and shown as 1–3 masks on the back-pole. **Max-HP changes keep the HP percentage** (as kingdom's Flail Levy does) |
| Temporary Lineage | Pomp-Bearer *Procession Standard* gives +1 for 30 s and **may reach 4** (+24 %); it drops back on expiry (HP percentage kept). The Dowager's *Mantle of Rank* (*Precedence*) gives a non-hero wearer +1 while it lasts, **capped at 3** on its own; with both, the Standard's cap of 4 applies |
| Deny | An enemy unit standing on a mask for 1.5 s **smashes** it: a terracotta crunch and a puff of petals |
| Hooks | Pomp-Bearer *Procession Standard*; Legate *Standing Vigil* and *Roll Call*; Eulogist *Final Words*; Ash Urn *Gathered Ashes*; Dowager *Mantle of Rank*; shop items *Spare Mask* (T2) and *Ancestor Cast* (T3) |
| Why it is ours | WC3 uses corpses only to raise or eat. No WC3 race passes rank from the dead to the living |

## B4. Economy and faction rules

| Rule | Value |
|---|---|
| Gold | The Sexton digs at an ordinary mine and walks back 10 per trip. There is no mine-cursing step |
| Lumber | Sextons fell trees: 10 per trip, 1 per 0.8 s; drop-off at a Barrow or the Ossuary |
| Food | Wake Barrow 10 → Long Barrow 12 → Grand Barrow 14. **Columbarium +10** (150 g / 50 l, 45 s) |
| Construction | Unearthed. Up to 2 Sextons dig (+50 % rate for the second). Off-Pall sites build 30 % slower (§B3.1): **start the expansion Barrow, then lay the Pall under it** (the penalty is checked live, so it lifts at once). The AI script does the same. *Re-mortar* repair: structures and the `mechanical` Urn Hearse, Ash Urn and the Released; autocast, default off, costs 30 % pro rata |
| Base defence | The Long Barrow and Grand Barrow ring a **Tomb Bell** (Arcane 16–20, CD 1.8 s, range 9.4 m, G+A, no detection). The Wake Barrow has no attack |
| Night | No modifiers. The Wakeful never sleep, which is a voice and flavour point only |
| Corpses | Uses the global corpse rule (rules §10.8, including the later 60 s "remains" stage) for the Eulogist's *Late Guests* |
| Shop | Grave Goods (§B7.4): recall item *Coin for the Ferry* (the first hero's free item), potions, *Folded Pall*, *Spare Mask*, a T2 reveal item and the T3 *Ancestor Cast* |
| Scouting and detection | The Veiled Mourner scouts invisibly and marks what it watches (*Mute Witness*); it detects only with its candle planted. Static detection: Mourning Posts and Urn Towers with *Tomb Lamps*. The hero's reveal item is the T2 *Vigil Candle* |

## B5. Unit roster

### B5.1 Roles (one line each)

| id | Unit | Role | Look (upper-third read first) | Abilities (tagged) | Prod. |
|---|---|---|---|---|---|
| `deathless_sexton` | **Sexton** | Worker | Lanky gravedigger with a gap-toothed terracotta grin-mask, long spade, grave lantern and soot smock | Digs gold, fells trees, unearths buildings. **Lay the Pall** (FE-adjacent: part of the Pall signature) | [B] |
| `deathless_veiled_mourner` | **Veiled Mourner** | Invisible scout | A short (1.3 m) funeral mute with adult proportions, a black veil to the ground with **small lacquered sandals visible**, carrying a tall candle-pole; a tiny chalk mask under the veil | Permanently invisible (rules §11 `permanent`); no attack (FE). **Mute Witness** (Orig, passive): an enemy unit it stays within 6 m of for 4 s is marked and stays visible to the Wakeful for 30 s, even in fog (at most 2 marks). **Plant Candle** (Orig): 3 s to plant; while planted it cannot move and the candle gives **true sight 9 m**; any move order picks it up. Trained normally | [B] |
| `deathless_retainer` | **Retainer** | Fast cheap melee | Skeletal household servant in soot livery-shroud, blank smiling terracotta mask, billhook and a small round shield painted with the family mask | **Grief** (Orig, passive): +12 % attack speed for 8 s when an allied Wakeful dies within 6 m (stacks ×3). *Brisk Step* research (FE): +0.7 m/s | [B] |
| `deathless_shroudcaster` | **Shroudcaster** | Ranged anti-air pinner | Gaunt shrouded figure with a satchel of weighted burial cloths; flings sharpened terracotta shards | **Burial Shroud** (FE, autocast on): a soot-black weighted cloth with tassel weights pins an air unit by a cord to a grave stake: grounded for 8 s (rules §12.3). No white net or strands | [B] |
| `deathless_drift_shroud` | **Drift-Shroud** | Anti-air flyer | An animated burial sheet with a chalk mask and **weighted, square-cut, tasselled corners** | Strong-vs-air, weak-vs-ground attack (FE). **Winding Sheet** (Orig, research): drops onto a ground unit and disarms it for 3 s; the Drift-Shroud is grounded while it wraps | [V/P] |
| `deathless_eulogist` | **Eulogist** | Raise-the-dead caster | Dead orator in a toga with a scroll-roll and an open-mouthed speaking mask | **Late Guests** (FE, autocast on): raises 2 Guests from a corpse for 35 s. Half Mourning: **Funeral Pace** (FE): −25 % move and attack speed for 8 s (heroes 4 s). Deep Mourning: **Final Words** (Orig): marks an ally for 10 s; if it dies, it bursts for 150 Spell damage within 3 m and its mask drops at +1 Lineage | [B] |
| `deathless_pomp_bearer` | **Pomp-Bearer** | Curse and spell-shield caster | Ungendered standard-bearer **marching on foot** in a ground-length rose-dyed toga (gliding walk, no hover gap), holding a tall pole topped by a frame of masks (masks only: never a saint or martyr icon) | **Borrowed Face** (FE, autocast on): the target misses 30 % of attacks for 60 s. Half Mourning: **Lacquer Ward** (FE): absorbs 250 spell damage for 45 s. Deep Mourning: **Procession Standard** (Orig): plants the pole for 30 s; Wakeful within 8 m gain +1 temporary Lineage | [B/P] |
| `deathless_ash_urn` | **Ash Urn** | Healing construct | A floating waist-high cinerary urn in soot lacquer with chalk bands, whose fired-clay lid is a sculpted human head | **Ash-Balm** (FE, autocast on): heals up to 8 HP/s in total, split among wounded allies within 6 m, paid from its own mana. **HP only**; it skips mechanical units and structures. **Gathered Ashes** (Orig, passive): each non-summoned allied `undead` unit that dies within 8 m gives the Urn +30 mana, and that unit's mask lasts 60 s instead of 40. No morph | [P] |
| `deathless_released` | **the Released** | T3 anti-magic flyer (its own unit, trained at the Ferry Steps) | A spiral of ash-rose smoke under a floating fired-clay lid-head | Attacks burn 10 mana and dispel one buff per hit (FE). **Scatter Ashes** (Orig): becomes a 6 m ash cloud for 4 s; enemy summons inside take 60 damage/s, and allied Wakeful inside cannot be targeted by enemy spells | [V/P] |
| `deathless_urn_hearse` | **Urn Hearse** | Siege cart | Black-lacquered funeral cart with tall rear wheels, a sling arm and stacked urns, pushed by two Sextons (reused mesh) | Ground-only siege (FE). **Tolling Urns** (Orig, passive): each hit on a building or Heavy-armour unit lowers the **primary target's** armour by 1 for 10 s (up to −3; splash victims are unaffected), with a bell toll. Urns burst into grave-dust | [P] |
| `deathless_tombwalker` | **Tombwalker** | T3 heavy melee | A walking stone sarcophagus on stumpy legs. A single reclining figure is carved on the lid | **Lid Slam** (Orig): every 4th attack splashes 1.5 m and stuns 0.5 s. *Grave-Damp* research (FE): 4 damage/s to enemies within 2.5 m | [P] |
| `deathless_wake_barge` | **Wake Barge** | T3 heavy air | A long, narrow black-lacquered funeral boat floating 4 m up, with a masked ferryman poling at the stern, rose garlands and a prow bell | Splash attack. **Take Aboard** (Orig): carries up to 6 food of allied ground units | [P] |

### B5.2 Stats

| Unit | Built at (needs) | Gold / lumber / food | Time (s) | Lvl | HP | Mana | Armour | Attack, damage | CD (s) | Range (m) | Hits | Speed (m/s) | Radius (m) | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sexton | Barrow | 70 / 0 / 1 | 15 | 1 | 230 | – | 0 Medium | Blade 5–7 | 2.0 | 0.6 | G | 3.0 | 0.35 | organic, undead, worker |
| Veiled Mourner | Mask Atrium | 80 / 10 / 1 | 20 | 1 | 180 | – | 0 Light | – | – | – | – | 4.8 | 0.35 | organic, undead |
| Retainer | Household Tomb | 125 / 0 / 2 | 18 | 2 | 380 | – | 0 Heavy | Blade 12–15 | 1.3 | 0.7 | G | 4.2 (4.9) | 0.45 | organic, undead |
| Shroudcaster | Household Tomb (Ossuary) | 210 / 40 / 3 | 30 | 3 | 540 | – | 0 Medium | Pierce 24–30 | 2.0 | 7.0 | G+A | 4.0 | 0.45 | organic, undead |
| Drift-Shroud | Ferry Steps | 180 / 30 / 2 | 26 | 2 | 400 | – | 2 Light | Pierce 16–20 vs air; Blade 7–9 vs ground | 1.5 | 3.0 | G+A | 5.6 (fly) | 0.6 | organic, undead |
| Eulogist | Mask Atrium | 150 / 15 / 2 | 28 | 2 | 300 | 200 | 0 Unarmored | Arcane 9–11 | 1.9 | 6.0 | G+A | 4.2 | 0.40 | organic, undead |
| Pomp-Bearer | Mask Atrium | 160 / 30 / 2 | 30 | 2 | 290 | 250 | 0 Unarmored | Arcane 10–12 | 1.8 | 6.0 | G+A | 4.4 | 0.40 | organic, undead |
| Ash Urn | Mask Atrium | 200 / 40 / 3 | 32 | 3 | 650 | 300 | 3 Heavy | – | – | – | – | 4.0 (hover) | 0.5 | mechanical |
| the Released | Ferry Steps (Grand Barrow) | 220 / 60 / 3 | 34 | 3 | 800 | 300 | 1 Light | Arcane 20–24 | 1.6 | 4.0 | G+A | 5.0 (fly) | 0.6 | mechanical |
| Urn Hearse | Kiln Yard | 220 / 50 / 3 | 36 | 3 | 400 | – | 2 Heavy | Siege 68–82, splash 1.0 / 2.0 m | 4.0 | 14.5 (min 3.0) | G | 3.4 | 0.8 | mechanical |
| Tombwalker | Kiln Yard (Grand Barrow) | 240 / 70 / 4 | 42 | 4 | 1150 | – | 2 Heavy | Blade 32–40 | 1.9 | 1.0 | G | 3.6 | 0.9 | organic, undead |
| Wake Barge | Ferry Steps (Grand Barrow) | 380 / 110 / 6 | 60 | 6 | 1350 | – | 1 Light | Arcane 80–98, splash 1.25 / 2.5 m | 3.2 | 4.5 | G+A | 4.0 (fly) | 0.9 | organic, undead |
| Guest (summon) | *Late Guests* | – | – | 1 | 210 | – | 1 Medium | Blade 9–11 | 1.5 | 0.6 | G | 3.8 | 0.40 | organic, undead, summoned |

Sight is 21.9 / 12.5 m for all units except the Sexton (12.5 / 9.4) and the Veiled Mourner (18.0 / 18.0).
Lineage bonuses apply on top of these values. Caster training ranks **Half Mourning** (T2) and **Deep Mourning** (T3): **+40 HP,
+50 mana and +1 damage per rank** (the kingdom's values under the Wakeful's own mourning terms). Casters, the Ash Urn and the Released
start with the global 75 mana.
Guests: a skeletal funeral mourner in a festive paper mask (a merry mourner at a wake, never a party-goer at a court); summoned (no food,
50 % XP, no bounty, rules §10.6); they neither take nor drop masks.

**Projectiles** (rules §7.7; hero missiles are in the §B6 hero table):

| Attack | Speed (m/s) | Arc |
|---|---|---|
| Shroudcaster terracotta shard | 18 | – |
| Drift-Shroud | Instant (weighted-corner lash, 3 m) | – |
| Eulogist and Pomp-Bearer bolts | 15 | – |
| the Released | 15 | – |
| Urn Hearse urn | 12 | High arc |
| Wake Barge | 14 | – |
| Urn Tower | 20 | – |
| Tomb Bell (Long / Grand Barrow) | 15 | – |

**One-line rules.**
- **Take Aboard:** an allied ground unit within 2 m boards in 0.5 s; *Unload* drops 1 unit per 0.5 s at the nearest walkable cells. The Wake Barge
  **cannot attack while carrying cargo**. If it dies, the cargo is dropped at once and each unit takes 25 % of its max HP.
- **The Released's mana:** it is trained at the Ferry Steps (T3) with the global 75 starting mana, regenerates 0.65 mana/s like a caster,
  and gains nothing from the mana its attacks burn. Nothing morphs into it or out of it.
- **Mute Witness:** the 4 s timer runs per enemy unit while it stays within 6 m of the Mourner and resets if it leaves. A third mark
  replaces the oldest. A mark shows the unit and its minimap pip to the Wakeful for 30 s; it **does not reveal invisibility** (that needs
  true sight). Heroes can be marked.
- **Plant Candle:** planting takes 3 s and can be interrupted; the planted Mourner stays invisible. Picking the candle up on a move order
  takes 0.5 s, and true sight ends at once.
- **Winding Sheet:** while wrapping (3 s; heroes 1.5 s) the Drift-Shroud counts as a grounded flyer (rules §12.3) and can be hit by melee.

### B5.3 Unit equivalence ledger (internal)

| Unit | Role | WC3 equivalents kept (FE) | Original |
|---|---|---|---|
| Sexton | Worker | – | Lay the Pall; the worker stays to dig (no summon-and-walk-away) |
| Veiled Mourner | Invisible scout | Permanent invisibility, no attack; detection (only while planted) | Mute Witness (marks what it watches through fog); Plant Candle (no mobile true sight); trained, not converted from a worker; walking look |
| Retainer | Fast cheap melee | Speed research | Grief |
| Shroudcaster | Ranged anti-air pinner | Air grounding | Shard-thrower body; pinned-cloth look (no net) |
| Drift-Shroud | Anti-air flyer | Strong-vs-air, weak-vs-ground attack | Winding Sheet (no immobile stone form) |
| Eulogist | Raise caster | Corpse raise; move-and-attack slow | Final Words |
| Pomp-Bearer | Curse and shield caster | Miss-chance curse; spell-damage shield | Procession Standard |
| Ash Urn | Healing construct | Area HP heal paid from its own mana | Gathered Ashes (death-fed mana and longer masks); no mana restore; no morph |
| the Released | Anti-magic flyer | Mana-draining, dispelling attack | Scatter Ashes (no buff absorbing); its own trained unit, not a morph |
| Urn Hearse | Siege cart | Siege role | Tolling Urns (no cargo) |
| Tombwalker | T3 heavy melee | Damage aura research | Lid Slam |
| Wake Barge | Heavy air | Splash attack | Take Aboard (transport) |

### B5.4 Minimum ability numbers

| Ability (unit) | Mana | Cooldown | Range / radius | Duration | Autocast default | Notes |
|---|---|---|---|---|---|---|
| Lay the Pall (Sexton) | – | 90 s | 6 m patch at the Sexton; only within 12 m of a friendly structure or construction site | 60 s | – | A Pall source (§B3.1) |
| Re-mortar (Sexton) | – | – | Seeks within 8 m | – | **off** | Repair (rules §4.8) |
| Mute Witness (Veiled Mourner) | passive | – | 6 m for 4 s | 30 s mark | – | At most 2 marks; visible through fog; no invisibility reveal |
| Plant Candle (Veiled Mourner) | – | – | Self; true sight 9 m | While planted | – | 3 s to plant; a move order picks it up |
| Grief (Retainer) | passive | – | 6 m | 8 s | – | Stacks ×3 |
| Burial Shroud (Shroudcaster) | – | 10 s | 6 m | 8 s (heroes 4 s) | **on** | Grounds an air unit (rules §12.3): a weighted soot cloth pinned by a cord to a grave stake |
| Winding Sheet (Drift-Shroud) | – | 15 s | 1.5 m | 3 s (heroes 1.5 s) | **off** | Disarm (rules §10.2) |
| Late Guests (Eulogist) | 70 | 3 s | Corpse within 8 m | 35 s | **on** | 2 Guests per corpse |
| Funeral Pace (Eulogist, Half Mourning) | 80 | 13 s | 7 m | 8 s (heroes 4 s) | – | −25 % move and attack speed |
| Final Words (Eulogist, Deep Mourning) | 80 | 15 s | 7 m, allied non-hero | 10 s | – | 150 Spell within 3 m on death; mask at +1 Lineage |
| Borrowed Face (Pomp-Bearer) | 45 | 0 s | 7 m | 60 s (heroes 15 s) | **on** | 30 % miss chance |
| Lacquer Ward (Pomp-Bearer, Half Mourning) | 70 | 8 s | 6 m, ally | 45 s | – | Absorbs 250 Spell damage |
| Procession Standard (Pomp-Bearer, Deep Mourning) | 100 | 45 s | Planted at the Pomp-Bearer; radius 8 m | 30 s | – | +1 temporary Lineage (may reach 4) |
| Ash-Balm (Ash Urn) | 1 per 4 HP restored | – | Radius 6 m | Continuous | **on** | Up to 8 HP/s in total, split among wounded allies. **HP only. Skips mechanical units and structures** (it never affects Ash Urns, the Released or the Urn Hearse) |
| Gathered Ashes (Ash Urn) | passive | – | 8 m | – | – | +30 mana per non-summoned allied `undead` death in range; that unit's mask lasts 60 s |
| Scatter Ashes (the Released) | 100 | 30 s | Radius 6 m | 4 s | – | The Released is untargetable as the cloud and re-forms at its centre |
| Tolling Urns (Urn Hearse) | passive | – | – | 10 s | – | −1 armour per hit on buildings and Heavy units, up to −3; primary target only |
| Lid Slam (Tombwalker) | passive | – | 1.5 m splash | 0.5 s stun | – | Every 4th attack |
| Grave-Damp (Tombwalker) | passive aura | – | 2.5 m | – | – | 4 Spell damage/s; does not stack between Tombwalkers |
| Take Aboard (Wake Barge) | – | – | Board within 2 m | 0.5 s per unit | – | 6 food of ground units; see one-line rules |
| Tomb Bell (Long / Grand Barrow) | attack | 1.8 s | 9.4 m | – | – | Arcane 16–20, G+A, no detection |

## B6. Heroes

Global hero rules apply. Heroes rise at the **Cenotaph**. All heroes: sight 28.1 / 12.5 m, radius 0.55 m.

| Hero (id) | Role | Primary | STR (+/lvl) | AGI (+/lvl) | INT (+/lvl) | Base damage (+primary) | Base armour | Base CD (s) | Attack (range) | Targets | Speed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Mourning Legate** (`deathless_hero_legate`) | Dark commander (STR melee, army aura, raised army) | STR | 24 (+2.7) | 12 (+1.4) | 17 (+1.8) | 1–9 | +1 | 2.2 | Melee 1.0 m | G | 4.6 |
| **The Dowager** (`deathless_hero_dowager`) | Matriarch caster (INT nuke, armour buff) | INT | 15 (+1.7) | 13 (+1.1) | 22 (+3.0) | 3–9 | −1 | 2.3 | Missile 7.5 m, 15 m/s | G+A | 4.4 |
| **The Patriarch** (`deathless_hero_patriarch`) | Noble lord (INT melee, sleep, life-steal aura) | INT | 19 (+2.2) | 12 (+1.2) | 20 (+2.7) | 3–11 | 0 | 2.1 | Melee 1.0 m | G | 4.5 |
| **Gravewright** (`deathless_hero_gravewright`) | Mason tank (STR, line stun, armour break) | STR | 26 (+2.8) | 11 (+1.1) | 14 (+1.4) | 1–7 | +1 | 2.3 | Melee 1.0 m | G | 4.4 |

Derived values (HP / mana / armour / damage / attack cooldown):

| Hero | Level 1 | Level 5 | Level 10 |
|---|---|---|---|
| Mourning Legate | 700 / 255 / 4.6 / 25–33 / 1.77 s | 950 / 360 / 6.1 / 35–43 / 1.64 s | 1300 / 495 / 8.2 / 49–57 / 1.49 s |
| The Dowager | 475 / 330 / 2.9 / 25–31 / 1.83 s | 625 / 510 / 4.1 / 37–43 / 1.72 s | 850 / 735 / 5.6 / 52–58 / 1.60 s |
| The Patriarch | 575 / 300 / 3.6 / 23–31 / 1.69 s | 775 / 450 / 4.8 / 33–41 / 1.59 s | 1050 / 660 / 6.6 / 47–55 / 1.46 s |
| Gravewright | 750 / 210 / 4.3 / 27–33 / 1.89 s | 1025 / 285 / 5.5 / 38–44 / 1.77 s | 1375 / 390 / 7.0 / 52–58 / 1.64 s |

| Hero | Look (one oversized prop) | Proper names (one at random, "Title: Name") |
|---|---|---|
| Mourning Legate | Towering dead general on foot. Blackened face-mask, **huge transverse crest of dried roses**, soot cloak, round shield painted with a calm face | *Aulenus the Unfinished, Ostrenus Last-in-Line, Varrenus the Twice-Buried, Septilius of the Rose Crest* |
| The Dowager | Tall, thin matriarch in a **towering conical headdress**, with a disdainful chalk mask (painted raised eyebrows). She flicks stiff dried petals from a fan | *Pellavia of the Raised Brow, Cassoria Thrice-Widowed, Sabrenna the Unamused, Ilvoria of the Tall Cap* |
| The Patriarch | Immense patrician in a soot toga with a rose border, a **broad collar of small heirloom masks**, a fist-sized silver signet and a heavy rod of office. No wings | *Massenus the Ninth Mask, Ferrenus of the Heavy Signet, Avitorus First-at-Table, Galbrenus the Undisputed* |
| Gravewright | Hulking dead stonemason in a chalk-caked apron with a limestone mask, a **tomb-slab shield** and a stone-cutter's pick | *Lapidus Plumbline, Tufenus Six-Chisels, Marmora the Patient, Ossorius Deep-Footing* |

**Kits** (ranks 1 / 2 / 3; mana; cooldown). FE rules 1–3 apply.

| Hero | Q | W | E | R (ultimate, level 6) | FE |
|---|---|---|---|---|---|
| Mourning Legate | **Pallbearer's Charge** (unit, 10 m): he charges the target for 80 / 140 / 200 Spell damage and drags it 3 m back along his charge path. If the target stands on Pall, it is rooted for 1 s. 80 mana, 12 s. *Orig* | **Standing Vigil** (aura, 8 m): allied Wakeful non-heroes inside deal +4 / 8 / 12 % damage, **doubled to +8 / 16 / 24 %** while they hold any Lineage; they also take masks within 3 m instantly. *Orig* | **Marching Orders** (point, 12 m): allied non-heroes within 8 m surge toward the point at +80 % speed for 2 s; their next hit deals +30 / 50 / 70 %. 70 mana, 18 s. *Orig* | **Roll Call** (20 m): up to 8 dropped masks in range rise as the units that dropped them, for 25 s (full HP; Pure damage; cannot be healed; they neither take nor drop masks). They are **`summoned`** (0 food, 50 % XP, no bounty, dispel `summon_damage`), have **Lineage 0** and are **not invulnerable**. A raised flyer rises as a flyer; raised Sextons cannot gather, build or repair. The masks are consumed. 160 mana, 165 s. *FE (temporary raised army)* | **1** |
| The Dowager | **Withering Look** (unit, 8 m): 90 / 150 / 210 Spell damage; the target and enemies within 3 m get −40 % move and attack speed for 3 / 4 / 5 s. 85 mana, 9 s. *FE (nuke plus area slow)* | **Mantle of Rank** (ally, 8 m, 30 s; autocast, **default off**; when on it targets an engaged ally without the buff): +2 / 4 / 6 armour. **Precedence:** a non-hero wearer counts as **1 Lineage rank higher** (cap 3; §B3.2), and a hero wearer ignores knockbacks and drags. 55 mana, 6 s. *FE (armour buff)* | **The Cut Direct** (enemy, 10 m, 10 s): the target takes +10 / 15 / 20 % damage from Wakeful sources. If it dies, she regains 50 / 75 / 100 mana. 75 mana, 15 s. *Orig* | **Damnatio** (enemy hero, 9 m, 8 s; `hero_duration` 8 s): the hero is "struck from the record": its auras switch off and it takes **+25 %** damage from all sources. It can still cast and use items. If it dies during Damnatio, its altar revive time is +50 % (up to 165 s, past the usual 110 s cap); an inn's instant revive is unaffected. 150 mana, 120 s. *Orig (genre echo)* | **2** |
| The Patriarch | **Entail** (enemy, 8 m, 8 s): binds the target to its current spot. If it ends up more than 5 m away, it takes 120 / 200 / 280 Spell damage and is stunned 1 / 1.25 / 1.5 s, which ends Entail. 70 mana, 12 s. *Orig* | **Old Money** (aura, 9 m): allied melee attacks heal the attacker for 10 / 20 / 30 % of damage dealt. *FE (life-steal aura)* | **Ancestral Drowse** (unit, 8 m): sleep for 15 / 30 / 45 s (heroes 3 / 6 / 9 s, `hero_duration`); damage wakes the target. 85 mana, 10 s. *FE (sleep)* | **Family Vault** (point within 10 m, 8 m circle): a stone vault (a 4×4-cell object at the point) rises for 10 s. Allied non-heroes inside the circle **at cast** sink into it: untargetable, healing 5 % max HP/s; no unit can enter afterwards. They re-emerge when it ends or he recasts. The vault has 1500 HP, Fortified 5; if it is destroyed, they emerge stunned for 1 s. 175 mana, 150 s. *Orig* | **2** |
| Gravewright | **Headstone Row** (line 10 m × 1.5 m): a row of headstones topples forward like dominoes, from the Gravewright to the end of the line, and flattens the units it falls on for 70 / 130 / 190 Spell damage and a stun of 1.25 / 1.75 / 2.25 s (heroes take the rules' 50 %). Nothing bursts from the ground and nobody is thrown into the air. 95 mana, 11 s. *FE (line stun)* | **Mason's Mark** (passive): each hit carves a mark on the target (marks last 6 s). At 3 marks they break: the target is slowed 20 / 25 / 30 % for 2 s and takes +10 / 15 / 20 % damage from Siege attacks for 6 s. *Orig* | **Raise Stele** (point, 6 m): a 2×2-cell **Stele** (a carved upright slab) for 30 s with 600 / 800 / 1000 HP, Fortified 5. It counts as Pall within 6 m, and allied Wakeful there regenerate +3 HP/s. 70 mana, 20 s. *Orig* | **Sealed Precinct** (8 m ring on himself or a point within 6 m, 8 s): stone slabs stop ground units crossing in or out (pathing rule in §A6). Wakeful inside deal +20 % damage. 150 mana, 150 s. *Orig* | **1** |

FE audit: two Wakeful heroes (Dowager, Patriarch) use 2 FE; the Legate and the Gravewright use 1 (FE rule 2). Only the Legate keeps an
ultimate that is functionally equivalent to its WC3 counterpart's (a temporary raised army, fed by masks); it is his only FE. The faction's
only regeneration denial is the Pall; *The Cut Direct* and *Damnatio* amplify damage instead of blocking heals. FE rule 3 check (round 2):
*Headstone Row* (95 mana; 1.25 / 1.75 / 2.25 s) and *Ancestral Drowse* (85 mana, 10 s; 15 / 30 / 45 s, heroes 3 / 6 / 9 s) now share no
value with their WC3 sources; *Funeral Pace* (80 mana, 13 s, 8 s) shares none either. *Damnatio* is a genre echo (a single-target
"doom" curse exists outside WC3) with no silence and no item lock. The Dowager's *Mantle of Rank* rider is *Precedence* (Lineage), so
her third and fourth slots no longer line up with the WC3 frost caster's armour spell and mana ritual.

**Summoned objects and monuments** (one-line rules):
- **Stele** (*Raise Stele*) and **Family Vault:** Fortified 5; they are **not structures for defeat** (like the kingdom's Grand Bombard),
  block their cells, give no XP or bounty, and cannot be repaired. Creeps in camp mode ignore them.
- **Roll Call units** use the global summon rules (rules §10.6) plus the kit line above.

## B7. Buildings and tech tiers

```
Wake Barrow (T1) ──► Long Barrow (T2, needs Cenotaph) ──► Grand Barrow (T3, needs Ossuary)
│
├─ Columbarium (+10 food, Pall 8 m)
├─ Cenotaph ── heroes (Pall 6 m)
├─ Household Tomb ── Retainer, Shroudcaster [Ossuary]
├─ Ossuary ── weapon and armour lines, Wide Pall, Tomb Lamps; lumber drop-off ── Mourning Post ─► Urn Tower
├─ Grave Goods ── items (stock grows with tier: T1, T2, T3)
│
├─ [T2] Mask Atrium ── Eulogist, Pomp-Bearer, Veiled Mourner, Ash Urn
├─ [T2] Kiln Yard ── Urn Hearse; Tombwalker [T3]
└─ [T2] Ferry Steps ── Drift-Shroud; the Released [T3], Wake Barge [T3]
```

Every building has Fortified armour 5 (the Mourning Post 2, as a scout tower) and 14.0 / 9.4 m sight unless stated (rules §8). On Pall,
Wakeful structures regenerate +1 HP/s; off Pall they suffer the §B3.1 penalties. Footprints are in 0.5 m pathing cells (halls 10×10,
production buildings 8×8, altar, smithy and shop 6×6, supply and towers 4×4); hall and tower upgrades keep the footprint.

| id | Building | Role | Needs | Gold / lumber | Time (s) | HP | Footprint | Food | Function |
|---|---|---|---|---|---|---|---|---|---|
| `deathless_wake_barrow` | **Wake Barrow** | Hall T1 | – | 385 / 190 | 160 | 1550 | 10×10 | +10 | Sexton; gold and lumber drop-off; Pall 16 m |
| `deathless_long_barrow` | **Long Barrow** | Hall T2 (upgrade) | Cenotaph | +300 / 200 | 130 | 2050 | 10×10 | +12 | Tier 2, hero 2; Pall 18 m; **Tomb Bell** |
| `deathless_grand_barrow` | **Grand Barrow** | Hall T3 (upgrade) | Long Barrow, Ossuary | +350 / 220 | 140 | 2600 | 10×10 | +14 | Tier 3, hero 3; Pall 20 m; **Tomb Bell** |
| `deathless_columbarium` | **Columbarium** | Supply | – | 150 / 50 | 45 | 520 | 4×4 | +10 | A curved wall of urn niches; Pall 8 m. **Does not** upgrade into a tower |
| `deathless_cenotaph` | **Cenotaph** | Hero altar | – | 180 / 50 | 60 | 900 | 6×6 | – | Raises and revives heroes; Pall 6 m |
| `deathless_household_tomb` | **Household Tomb** | Barracks | – | 180 / 50 | 60 | 1300 | 8×8 | – | Retainer, Shroudcaster; *Brisk Step*, *Burial Shroud* |
| `deathless_ossuary` | **Ossuary** | Smithy and lumber drop-off | – | 150 / 50 | 60 | 1100 | 6×6 | – | Four upgrade lines (§B7.2); *Wide Pall*, *Tomb Lamps*; enables the Mourning Post |
| `deathless_mask_atrium` | **Mask Atrium** | Caster hall | Long Barrow | 160 / 130 | 65 | 1000 | 8×8 | – | Eulogist, Pomp-Bearer, Veiled Mourner, Ash Urn; caster trainings |
| `deathless_kiln_yard` | **Kiln Yard** | Workshop | Long Barrow | 150 / 140 | 60 | 1150 | 8×8 | – | Urn Hearse; Tombwalker at T3; *Grave-Damp* (T3) |
| `deathless_ferry_steps` | **Ferry Steps** | Air pier | Long Barrow | 160 / 160 | 65 | 1100 | 8×8 | – | Drift-Shroud; the Released and the Wake Barge at T3; *Winding Sheet* (T2) |
| `deathless_mourning_post` | **Mourning Post** | Scout tower (Fortified 2) | Ossuary | 40 / 20 | 25 | 320 | 4×4 | – | Sight 25 / 18 m; no attack. **One upgrade path:** Urn Tower |
| `deathless_urn_tower` | **Urn Tower** | Tower (upgrade, Fortified 5) | Mourning Post | +80 / 40 | 30 | 500 | 4×4 | – | Pierce 20–24, CD 1.0 s, 10.9 m, G+A, shard 20 m/s. **Level 3** (XP). True sight 9 m with *Tomb Lamps* |
| `deathless_grave_goods` | **Grave Goods** | Faction shop | – | 130 / 30 | 60 | 480 | 6×6 | – | Items (§B7.4) |

### B7.2 Upgrades and research

| Line (Ossuary) | Level 1 | Level 2 | Level 3 | Effect per level | Affects |
|---|---|---|---|---|---|
| **Honed Bone** | 110 g / 60 l, 60 s | 180 / 170, 75 s | 260 / 290, 90 s | `upgrade_damage` | Retainer, Tombwalker |
| **Fired Shards** | 110 / 60, 60 s | 180 / 170, 75 s | 260 / 290, 90 s | `upgrade_damage` | Shroudcaster, Drift-Shroud, the Released, Wake Barge |
| **Lacquered Shrouds** | 130 / 70, 60 s | 160 / 180, 75 s | 190 / 270, 90 s | +2 armour | Retainer, Shroudcaster, Tombwalker, Urn Hearse (Sexton-crewed), Eulogist, Pomp-Bearer |
| **Glazed Clay** | 130 / 70, 60 s | 160 / 180, 75 s | 190 / 270, 90 s | +2 armour | Drift-Shroud, Ash Urn, the Released, Wake Barge |

The Urn Hearse has no weapon line (Tolling Urns is its scaling); the Veiled Mourner has no armour line.

| Building | Research | Tier | Gold / lumber | Time | Effect |
|---|---|---|---|---|---|
| Household Tomb | *Brisk Step* | T2 | 100 / 75 | 50 s | Retainer +0.7 m/s |
| Household Tomb | *Burial Shroud* | T2 | 125 / 100 | 50 s | Shroudcaster can ground flyers |
| Ferry Steps | *Winding Sheet* | T2 | 125 / 75 | 50 s | Drift-Shroud ability |
| Ossuary | *Wide Pall* | T2 | 125 / 100 | 50 s | +25 % Pall radius for every source |
| Ossuary | *Tomb Lamps* | T2 | 100 / 75 | 45 s | Mourning Posts and Urn Towers get true sight 9 m |
| Mask Atrium | Eulogist and Pomp-Bearer **Half Mourning** | T2 | 100 / 50 each | 60 s | +40 HP, +50 mana, +1 damage; Funeral Pace / Lacquer Ward |
| Mask Atrium | Eulogist and Pomp-Bearer **Deep Mourning** | T3 | 150 / 100 each | 70 s | +40 HP, +50 mana, +1 damage; Final Words / Procession Standard |
| Kiln Yard | *Grave-Damp* | T3 | 150 / 150 | 60 s | Tombwalker damage aura |

### B7.4 Grave Goods items (faction shop)

Potion values stay off the common WC3 values (250 HP, 150 mana) and off the kingdom's (240, 140) and the Glaer's (270, 160).

| Item | Hall tier | Cost | Stock / restock | Effect |
|---|---|---|---|---|
| **Coin for the Ferry** | T1 | 350 g | 2 / 120 s | Pay the coin over 3 s (rules §6.8 channel), then the hero and **up to 11 of your own units within 6 m** teleport next to your nearest finished Barrow. The first hero gets one free |
| **Funeral Honey** | T1 | 130 g | 3 / 60 s | +230 HP at once |
| **Lamp-Oil Draught** | T1 | 110 g | 3 / 60 s | +130 mana at once |
| **Folded Pall** | T1 | 110 g | 2 / 90 s | Lays a 6 m Pall patch at a point within 8 m for 60 s |
| **Spare Mask** | T2 | 120 g | 2 / 90 s | +1 Lineage on a Wakeful non-hero within 6 m (cap 3) |
| **Vigil Candle** | T2 | 75 g | 2 / 60 s | Reveals invisible units within 9 m of the hero for 15 s |
| **Ancestor Cast** | T3 | 300 g | 1 / 180 s | A plaster cast of a family face: +1 Lineage to every Wakeful non-hero within 6 m that may take masks (§B3.2), cap 3 |

| Tier | Unlocks |
|---|---|
| T1 Wake Barrow | Sexton, Retainer, Shroudcaster, Mourning Post and Urn Tower; hero 1; level-1 upgrades; shop T1 (Coin for the Ferry, Funeral Honey, Lamp-Oil Draught, Folded Pall) |
| T2 Long Barrow | Mask Atrium, Kiln Yard, Ferry Steps, Eulogist, Pomp-Bearer, Veiled Mourner, Ash Urn, Urn Hearse, Drift-Shroud; hero 2; Half Mourning trainings; *Brisk Step*, *Burial Shroud*, *Winding Sheet*, *Wide Pall*, *Tomb Lamps*; Tomb Bell; level-2 upgrades; shop T2 (Spare Mask, Vigil Candle) |
| T3 Grand Barrow | Tombwalker, the Released, Wake Barge; hero 3; Deep Mourning trainings; *Grave-Damp*; level-3 upgrades; shop T3 (Ancestor Cast) |

### B7.5 Command cards and hotkeys (Classic preset; rules §18.4)

Same conventions as §A7.5: Move **M**, Stop **S**, Hold **H**, Attack **A**, Patrol **P** on unit cards; heroes add Learn **O** and
**Q / W / E / R**; production buildings carry Rally **R**; unit abilities use **Q / W / E** in §B5.1 order.

| Card | Buttons (letter) |
|---|---|
| Sexton | Gather **G**, Return Cargo **C**, Re-mortar **R** (autocast toggle by right-click), **Build Basic B**, **Build Advanced V**, Lay the Pall **L**, Take Mask **T** |
| Build Basic (B) | Wake Barrow **W**, Columbarium **C**, Cenotaph **N**, Household Tomb **T**, Ossuary **O**, Mourning Post **M**; Esc back |
| Build Advanced (V) | Mask Atrium **A**, Kiln Yard **K**, Ferry Steps **F**, Grave Goods **G**; Esc back |
| Wake / Long / Grand Barrow | Sexton **S**, Upgrade to the next tier **U**, Rally **R** |
| Cenotaph | Mourning Legate **L**, The Dowager **D**, The Patriarch **P**, Gravewright **G** (a dead hero's button becomes Revive in place), Rally **R** |
| Household Tomb | Retainer **T**, Shroudcaster **S**, Brisk Step **B**, Burial Shroud **U**, Rally **R** |
| Ossuary | Honed Bone **H**, Fired Shards **F**, Lacquered Shrouds **L**, Glazed Clay **G**, Wide Pall **W**, Tomb Lamps **T** |
| Mask Atrium | Eulogist **E**, Pomp-Bearer **P**, Veiled Mourner **V**, Ash Urn **U**, Eulogist Half Mourning **H**, Eulogist Deep Mourning **D**, Pomp-Bearer Half Mourning **A**, Pomp-Bearer Deep Mourning **M**, Rally **R** |
| Kiln Yard | Urn Hearse **H**, Tombwalker **T**, Grave-Damp **D**, Rally **R** |
| Ferry Steps | Drift-Shroud **D**, the Released **E**, Wake Barge **B**, Winding Sheet **W**, Rally **R** |
| Mourning Post | Urn Tower **U** |
| Grave Goods | Coin for the Ferry **C**, Funeral Honey **H**, Lamp-Oil Draught **L**, Folded Pall **F**, Spare Mask **S**, Vigil Candle **V**, Ancestor Cast **A** |
| Unit abilities | Veiled Mourner: Plant Candle **Q**. Shroudcaster: Burial Shroud **Q**. Drift-Shroud: Winding Sheet **Q**. Eulogist: Late Guests **Q**, Funeral Pace **W**, Final Words **E**. Pomp-Bearer: Borrowed Face **Q**, Lacquer Ward **W**, Procession Standard **E**. Ash Urn: Ash-Balm **Q**. the Released: Scatter Ashes **Q**. Urn Hearse: Attack Ground **G**. Tombwalker: none (passives). Wake Barge: Take Aboard **Q**, Unload **U** |
| Heroes | Mourning Legate: Pallbearer's Charge **Q**, Standing Vigil **W**, Marching Orders **E**, Roll Call **R**. The Dowager: Withering Look **Q**, Mantle of Rank **W**, The Cut Direct **E**, Damnatio **R**. The Patriarch: Entail **Q**, Old Money **W**, Ancestral Drowse **E**, Family Vault **R**. Gravewright: Headstone Row **Q**, Mason's Mark **W**, Raise Stele **E**, Sealed Precinct **R** |

## B8. Voice and music

**Voice personality: languid, snobbish old money that happens to be dead.**
- They boast about lineage and precedence and treat the living as upstart trespassers on the family estate.
- They are nostalgic ("in my day the hills were smaller") and slightly hard of hearing after a few centuries.
- They are theatrically, impeccably polite while doing something terrible.
- The comedy is **snobbery and ancestry**. It is never hospitality or feasting (a clans trait) and never ledgers, registers or contracts
  (a kingdom trait).
- The §B1 tone guard applies to every line: no "court", "sin", "atonement", "anima" or "masquerade ball"; the dead are a funeral
  procession of old families, not a gothic court.
- Delivery is unhurried, with long vowels and the faint echo of speaking through a mask (a short pre-delay reverb).
- **No faux Italian accent.**
- Each unit gets one tic. For example, the Retainer repeats **"In order of precedence"**; the Tombwalker speaks in a single grinding
  voice that recites its own epitaph (one voice only: an interrupting second voice belongs to the clans' Mound-Speaker).
- **Annoyed lines may not use poke / poked / poking or paraphrase any WC3 line** (check against the quote pages). Self-aware lines about
  being clicked are allowed in the faction's own idiom, e.g. Retainer: *"One does not hurry the dead. One clicks, and one waits."*
  The shared VO review list is in §A8.

**Sample lines** (original; check against the WC3 undead quote page before recording):
- Retainer (Yes): *"In order of precedence, of course. Always in order of precedence."*
- Eulogist (Annoyed, last in sequence): *"I have eulogised better men than you. Several of them were alive at the time."*

**Music:**
- Double reed-pipes and lyre, frame drum and finger cymbals, small tarnished bells, and a low unison male hum.
- A slow, stately processional at 60–76 BPM that is unsettlingly *too* festive.
- **Avoid** dark choir with pipe organ and dissonant strings (too close to the nearest rival race's sound; §B9).

## B9. Distinctness rubric (ip-safety §3.2; nearest WC3 race: the undead plague)

| Axis | WC3 undead | Long Wake | Differs? |
|---|---|---|---|
| 1. Silhouette | Spikes, hunched ghouls, spider fiends, stitched brutes, gargoyles, floating tattered ghosts, ziggurats and spiked halls | Upright masked processions on foot, Lineage poles, square-cut weighted linen (only one cloth flyer), urns, a sarcophagus walker, a funeral barge, round tumuli | **Yes** (required) |
| 2. Palette | Purple, black, teal glow, sickly green | Cool blue-black soot and chalk masses, small fired-clay accents (≤ 25 % of a unit), grave-rose, lamp-rose glow; banners never terracotta on black, so no red-brown mass either | **Yes** |
| 3. Materials | Bone spikes, frost, purple stone, ooze | Terracotta, chalk plaster, lacquer, linen shrouds, dried flowers, limestone | **Yes** |
| 4. Culture | Gothic and Nordic frost necromancy, insect horror | Etruscan and Roman funerary families: tomb paintings, ancestor masks, urns | **Yes** |
| 5. Signature mechanic | Blight, cursed mine, summon-and-walk-away building, corpse economy, worker-to-scout sacrifice, supply-to-tower split, the healing statue that morphs into an anti-magic flyer | The Pall (the one WC3-derived mechanic, softened, re-presented and tied to home turf) plus original Heirloom Masks. The scout is trained normally; the Mourning Post has one upgrade path with detection as a separate research; the Ash Urn and the Released are **separate units with no morph** (round 2) | **Yes** (within policy after round 2. Honest history: Partial before round 1, and still Partial after round 1 because the morph was a second WC3 signature) |
| 6. Names and voice | WC3 unit, hero and place names; sinister, hungry | All original; snobbish ancestral aristocrats | **Yes** |

**Result: 6 / 6 after round 2** (5 / 6 before round 1, and 5 / 6 in honest terms after round 1). **Signature budget:** the Pall is the
faction's one WC3-derived signature (ip-safety §2.3). If a later fidelity pass insists on the urn-to-flyer morph, the faction must drop the
Pall instead (IP wins under this doc's conflict rule). **Tech-tree deviations** (deliberate): (1) the anti-air flyer trains at the air pier
(Ferry Steps, now a T2 building), not the barracks; (2) the healing construct trains at the caster hall (Mask Atrium), not the workshop;
(3) the invisible scout is trained, not converted from a worker; (4) the anti-magic flyer is trained directly at the air pier (T3). Residual risk: the plague-ground idea and the siege cart are familiar
shapes. Keep the Pall grey and petal-flecked, and keep the Urn Hearse free of bodies and of any cargo-handling ability.

---

# Part C: Production fit (later milestones)

| | Glaermere | Long Wake |
|---|---|---|
| [B] bipeds: Tripo H3.1 image-to-3D (9 cr) plus the bpy auto-rig | Tapster, Larkbow, Stoneskipper, Ambermail, Sapsinger (Bark Coat as a prop and texture swap), Hazeweaver, and 4 heroes: **10 × ≈ 9.25 cr ≈ 93 cr** | Sexton, Retainer, Shroudcaster, Eulogist, Pomp-Bearer (upper body; the gliding walk under the toga is procedural), Veiled Mourner, and 4 heroes: **10 × ≈ 9.25 cr ≈ 93 cr** |
| [C] creatures: AI mesh with rigid-segment procedural motion | Woodgnaw (waddle, tail pivot), Treeglider (spread-eagle glide; the dropped lantern is a reused prop): **≈ 19 cr** | – |
| [P] / [V] procedural or VFX: bpy plus AI textures | Springbough (Tapster crew reused), Thistleship (lathe seed plus wicker gondola), Glimmerswarm (particles): **≈ 2 cr** | Urn Hearse (Sexton crew reused), Wake Barge, Tombwalker (box, lid and stub legs; the lid figure can be a 9 cr AI relief), Ash Urn (lathe), the Released (smoke particles under the Ash Urn's lid mesh, reused), Drift-Shroud (cloth card with vertex waves): **≈ 3–12 cr** |
| Buildings | One AI hall (9 cr) plus a **bpy stilt-and-gable kit**: **≈ 12 cr** | One AI hall (9 cr) plus a **bpy drum-mound kit** (cylinder, dome, door frame, urns, cypress): **≈ 12 cr** |
| Icons (about 35 each) | ≈ 9 cr (0.25 cr each) or 2×2 Krea sheets | ≈ 9 cr |
| **Total** | **≈ 135 cr** (93 + 19 + 2 + 12 + 9) | **≈ 117–126 cr** (93 + 3–12 + 12 + 9) |
| Voice | About 11 units × 18 + 4 heroes × 26 + advisor 14 ≈ **315 lines** | About **330 lines** (the Veiled Mourner is mute: select and move are breath and candle-gutter sounds) |

**Budget warning.** After the slice (kingdom ≈ 70–95 cr, clans ≈ 80–90 cr), only about 85–120 of the 269.75 Higgsfield credits remain.
These two factions need **≈ 252–261 cr (about 255)**. Options:
- Run the README §6 bake-off. If Krea's legacy Tripo (8 CU) or TRELLIS (10 CU) passes for rank-and-file units, move them there.
- Otherwise top up credits before these milestones.

**Default voices expire on 31 Dec 2026.** Either record these lines before then, or plan for voices that will still be available later.

---

# Part D: Open questions and tuning flags

1. **Engine features these factions need** (not in the slice):
   - Glaer: per-tree tapper occupancy without depletion; shallow-water building placement; noonlight sight-override zones in the fog grid
     (a light mask in the grade shader); a **per-player pathing mask** for *Warp and Weft*; lumber log pickups (*Fell*); dropped
     ground-effect lanterns (*Lantern Drop*); a temporary "counts as shallow water" status zone (*Spring Flood*); attribute transfer
     between heroes (*Pocket the Flame*).
   - Wakeful: a Pall ground layer (reuse the corruption mask shader) with live "centre cell on Pall" checks; mask pickup entities; a
     deterministic snapshot for *Roll Call* and *Family Vault*; ring displacement for *Sealed Precinct*; transport cargo (*Take Aboard*);
     fog-piercing marks (*Mute Witness*); planted-state true sight (*Plant Candle*); a "near a friendly structure or site" cast check
     (*Lay the Pall*).
2. **Summerhoard strength.** A Lodge exactly covers one night without Lantern Glass, and the sunlit yard heals by day at no cost. If
   Glaer turtling is too strong, cut the unit rate in noonlight and the sunlit yard from +1.5 to **+1.0 HP/s** first (structures stay
   +1), then the Post capacity. If the creep-walk-home loop is still too slow, raise the Birch-Bark Poultice stock before the rates.
3. **Tapping economy.** At 10 lumber per trip and 0.9 s per lumber, a Tapster yields ≈ 0.65 lumber/s at the 10 m reference walk (kingdom
   ≈ 0.68, clans ≈ 0.75), ≈ 0.70 with *Deep Spigots*. One-per-tree pushes extra Tapsters to farther trees, and the Glaer roster is
   lumber-hungry. Check lumber per minute at 0–6 min and at 15 min in AI-vs-AI runs.
4. **Pall regeneration denial** mainly affects **heroes**, because non-hero natural regeneration is only 0.25 HP/s. If it still feels bad
   for hero-centred opponents, the fallback is enemy regeneration −50 % instead of 0.
5. **Lineage snowball.** +18 % at rank 3 (+24 % temporary), *Standing Vigil* and the mask hooks may over-reward early trades. Tune the
   cap (3 → 2) before the per-rank value.
6. **Woodgnaw and Treeglider** are the riskiest assets (quadruped and glider). If the rigid-segment motion looks poor, replace
   Woodgnaw with a biped "bark giant" in walking armour (wood and bark plates only: never a tree-man and never stone or slabs, which are the
   neutral Old Menhir's read) and the Treeglider with a wicker hang-glider rider (it keeps *Lantern Drop*).
7. **Name clearance.** Record before any public use:
   - **"The Long Wake"** is the title of a game in development (*The Long Wake: What Remains Observed*, by SpaceBoy, listed in the DeVuego
     presskit). Keep "Long Wake" **internal** until the clearance pass; the marketing fallback is **"the Unending Wake"**.
   - **"Glaer"** is also an obscure Tolkien Noldorin word ("long lay"). Low risk as a faction name; the in-world etymology stays Old English
     *glǣr*.
   - Glaermere and Wakeful had no web search. Add all four to the `tools/ip/banned_terms.txt` CI review notes and check them at the
     public-title clearance pass (ip-safety §4), together with the round-2 names *Summerhoard*, *Pomp-Bearer*, *Spring Flood* and
     *Pocket the Flame*.
8. **Real-culture respect.** Etruscan and Roman sources are extinct civilisations, so the risk is low, but avoid real tomb names, real
   inscriptions, real war-memorial epitaphs (the first motto echoed one and was replaced) and real deity iconography. The Veiled Mourner is
   an adult funeral mute, never a child. Northern lakeland sources: no real sacred signs, deities or epic names, and no caricature accent.
9. **Full-game matchups.** Glaer air plus anti-magic should counter Wakeful casters. Wakeful Pall sustain should punish Glaer
   hit-and-run. Kingdom towers and clans haste pushes need re-tuning once all four factions exist.
10. **Damnatio's revive extension** goes past the global 110 s cap (up to 165 s). If testers find a 165 s revive too punishing, cap it at
    +25 % (137 s).
11. **Home-turf Pall.** *Lay the Pall* now needs a friendly structure or construction site within 12 m (60 s patch, 90 s cooldown), and a
    *Folded Pall* costs 110 g for 60 s. Check in AI runs that Wakeful armies still win fights on their own Pall and lose clearly away
    from it. If the expansion timing suffers, shorten the cooldown before lengthening the patch.
12. **Long sleep.** *Ancestral Drowse* lasts 15 / 30 / 45 s on units (heroes 3 / 6 / 9 s) on a 10 s cooldown. It breaks on damage, so it
    is a set-up and creep-skip tool. Watch for chain-sleeping a whole creep camp; if it happens, add "one sleeping target per Patriarch".

---

# Part E: Cross-checks with `neutrals.md` (its §10.2 and §11 Q12)

| Neutral element | Collides with | Rule (both docs must keep it) |
|---|---|---|
| **Saltbound** (salt-crusted dead caravan; rose-salt `#E8C2C0`, brine-blue eye glow; *Raise the Caravan*) | Wakeful (lamp-rose `#FFC7D1`, terracotta masks, Urn Hearse, *Roll Call*) | Wakeful never show salt crystals, caravan robes or brine-blue light. Saltbound never wear masks, terracotta, roses or lacquer, and their glow stays blue. Their raise is a once-per-fight creep trigger, ours is masks |
| **Mire Toads** | Glaer lakeland setting | Glaer use no toads or frogs in units, VFX, icons or emblems |
| **Hollow Harvest** (night-active scarecrows with drilled turnip lanterns, glow `#FFC46B`; the Turnip King's *Lantern Glare*) | Glaer lanterns (`#FFB547`) and the Glare Post | Glaer lanterns are always caged amber teardrops, never drilled, pierced or head-shaped; Glaer never use straw figures or crows. *Lantern Glare* (a creep ability) and *Glare Post* (a building) differ in kind; keep both |
| **Old Menhir** (walking standing stone; *Lichen Hide*; *Drystone Wall* pathing wall) | The Woodgnaw fallback "bark giant"; *Warp and Weft* | The fallback giant is wood and bark, never stone. *Drystone Wall* blocks everyone; *Warp and Weft* is a woven one-sided fence that allies pass through |

**Name and readability collisions** (requested changes to `neutrals.md`, listed in the Review log follow-ups):
- Neutral marketplace **Lucky Barrow** vs the Wake / Long / Grand Barrow halls → rename the neutral **Lucky Cart** (it is already a pedlar's handcart).
- Neutral **Glimmer Font**, the **Firefly Drift** critter and the **Firefly Jar** item vs the Glimmerswarm → rename the fountain
  **Clearwater Font**; give Firefly Drift and Firefly Jar motes a **cool green-white tint, never amber**, at most 6 motes. The Glimmerswarm
  stays amber with 20+ motes, a caged-lantern core, a team-colour ring, a selection ring and a health bar.
- The **amber** camp band vs the Amber Lodge and amber accents: the band is minimap UI only; Glaer buildings never show amber minimap pips
  (team colour only).

---

## Review log (2026-10-16: IP-safety and WC3-fidelity reviews)

Where the two reviews conflicted, IP won and the closest legal alternative was kept. "Combined" means two issues touched the same item and
one change answers both.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | Thicket Weaver echoed the grove-druid kit; Old Thicket (tree ring + area heal) was a known editor-hero design and duplicated Entomb | Old Thicket → **Warp and Weft** (one-sided woven fence, −30 % slow nearby, 160 mana, 150 s, no trees, no heal); optional fix taken: Seed Spit → **Shuttle Throw** (threading bounce). FE count 2 → **1**. Squint row and pathing rule updated (§A2, §A6) |
| 2 | Major | Mourning Legate = coil + inverted haste/regen aura + raised army, with copied numbers | Grave Honours → **Pallbearer's Charge** (Orig). Funeral Pace → **Standing Vigil** (Orig; see #19). **Roll Call** kept as the only FE with our numbers (160 mana, 165 s, 25 s, up to 8). Closing line rewritten (§B6) |
| 3 | Major | Dowager numbers equal WC3 frost spells | Mantle of Rank +2 / 4 / 6, 30 s, 55 mana, 6 s, rider **Insolence** (−2 armour on melee attackers); Withering Look 90 / 150 / 210, 9 s. New **FE rule 3** (one shared parameter at most). Proactive sweep under the rule: Rootbind 70 mana, 10 s, 12 / 18 / 24 dps; Drink the Light 55 mana, 9 s; Reed Darts 10 s; Slip Under 45 mana; Ancestral Drowse 4 / 6 / 8 s, 80 mana, 10 s |
| 4 | Major | Sapsinger, Ambermail, Drift-Shroud and Ash Urn → Released copied whole unit kits | Sapsinger Chorus → **Lantern Hymn** (from #39; chosen over *Hold the Note* because it uses the faction's own noonlight). Ambermail slowing darts → **Amber Fleck** (the anti-caster read; *Resin Tack* from #39 not used). Drift-Shroud keeps its dual attack; Lie in State → **Winding Sheet**. The Released: buff absorbing → **Scatter Ashes**. Every ability tagged (§A5.1, §B5.1) |
| 5 | Major | Mask Cart was the corpse-cargo function re-skinned; "corpse-carrying wagons" line contradicted the doc | Mask Cart removed from the Urn Hearse and the §B3.2 hooks; new passive **Tolling Urns**. §B3.1 now lists "the siege cart's corpse cargo" among dropped features. No mask carrier was needed |
| 6 | Major | "High Noon" is a Blizzard *Overwatch* catch-phrase | Ultimate renamed **Midsummer Hour**. `high noon` added to `tools/ip/banned_terms.txt` (in fact only in round 2; see round-2 #7); §A8 VO review list created |
| 7 | Major | Floating tattered ghost cue: Veiled Mourner ≈ Shade, Imaginifer ≈ Banshee | Rule 3 rewritten (square-cut tasselled hems; only the Drift-Shroud flies). Veiled Mourner: a walking adult funeral mute, feet visible, candle-pole, [B]. Imaginifer marches on foot, no hover gap. Shade, Banshee and Ash Urn rows added to the §B2 squint table |
| 8 | Minor | Extra WC3 signatures: worker-to-scout, two-way tower split, Fell = eat-tree, Tail Slap untagged | Veiled Mourner trained normally (80 / 10 / 1, 20 s). Mourning Post → Urn Tower only; detection is the *Tomb Lamps* research. Fell leaves a 20-lumber log, no buff. Tail Slap tagged FE. Both rubrics re-scored (axis 5 "Partial" before the fixes, 5 / 6 → 6 / 6 after) |
| 9 | Minor | Every hero spent both FE slots on its counterpart's best-known basics | New **FE rule 2** (at most 2 heroes per faction with 2 FE). Lampbreaker Corona → **Wick Draw**, brief is now a lamp-thief (no "exile", no "scorched"); Gravewright Stone Lid → **Mason's Mark** (every hit marks, so it triggers at a useful pace). Reedstalker recast as a male eel-fisher with no hood. Glaer: 1 hero at 2 FE; Wakeful: 2 |
| 10 | Minor | Unit spell numbers copied from WC3 | Late Guests 2 for 35 s, 70 mana; Lacquer Ward 250 for 45 s; Midge Haze −3 for 75 s (30 mana); Scrape Clean 40 mana; Ash-Balm 8 HP/s and 4 mana/s |
| 11 | Minor | Names echoing other IP | Upheaval → **Headstone Row**; Entomb → **Sealed Precinct**; Split Volley → **Lark Flight**; Wind Perch → **High Drey**; House of Masks → **Mask Atrium**; "Great Houses" → **the Old Families**; Gravius → *the Ninth Mask*; Dowager Tenebra → **Pellavia**; *tenebrae* and the "Nth of the Name" formula added to the §B1 rules |
| 12 | Minor | Tapster line paraphrased "stop poking me"; Retainer tic on the "as you wish" formula | Rule: no annoyed line may refer to being clicked, poked, tapped, prodded or touched (§A8, §B8). New Tapster line as proposed. Retainer tic **"In order of precedence"** instead of the proposed "Noted in the household book", which would collide with the kingdom's ledger comedy (§B8 rule) |
| 13 | Minor | Motto echoed a war-memorial epitaph | "The register is never closed." Part D item 8 now bans real war-memorial epitaphs |
| 14 | Minor | "The Long Wake" is a game title; "Glaer" is a Tolkien word | Both recorded in Part D item 7; "Long Wake" internal until clearance, fallback "the Unending Wake" (§B0); Old English etymology kept (§A1) |
| 15 | Minor | Banned words in role columns; "canopic" pulls an Egyptian look | Header rule on internal audit material; role columns and role mirrors rewritten in neutral words; prompt rule "terracotta cinerary urn with a human-head lid"; unit renamed **Ash Urn**, id `deathless_ash_urn` |
| 16 | Minor | Each production building trained exactly its WC3 counterpart's units | Sylvan: Hazeweaver at the Singers' Hall; Glimmerswarm at the Thistle Mooring (now T2). Deathless: Drift-Shroud at the Ferry Steps (now T2); Ash Urn at the Mask Atrium. Decision recorded in §A9 and §B9 |
| 17 | Minor | "Lichen sage" contains a banned stem | Swatch renamed **Moss sage**. (The checker already matches whole words, so `lich` alone would not fire.) |
| 18 | Major | No hero base damage, armour, cooldown or attack kind | Hero tables now carry base damage, base armour, base cooldown, attack range and missile speed (reviewer's values), plus L1 / L5 / L10 derived rows computed with the rules §6.6 formulas (§A6, §B6) |
| 19 | Major | Funeral Pace was an FE in disguise and duplicated the Pall's regen denial | Combined with #2: Funeral Pace → **Standing Vigil** (mask-linked aura). IP won on Grave Honours (#2), so the Legate ends at **1 FE**, not the 2 the fidelity fix proposed; the closing line says Roll Call is his only FE |
| 20 | Major | One weapon line and one armour line per faction, no costs | Four lines per faction with costs and times (§A7.2, §B7.2): Hardened Points / Gnaw-and-Talon / Resin Varnish / Tarred Hides; Honed Bone / Fired Shards / Lacquered Shrouds / Glazed Clay. Lantern Glass and Wide Pall 125 / 100, 50 s |
| 21 | Major | Tapping was 19–26 % slower than the other workers | 10 per trip at 0.9 s (≈ 0.65 lumber/s); *Deep Spigots* (T2, 100 / 0, 60 s) → 12 per trip (≈ 0.70). WC3 column now says "credits in place (verify)", Glaer column "walks it back (deliberate change)" (§A3.1, §A4, Part D item 3) |
| 22 | Major | Hang Lantern was free map-wide warding | Option (a): only on the Tapster's own tapped tree, 8 m for 60 s, one per Tapster, cooldown 30 s |
| 23 | Major | Shops had no stock tables; recall item unpriced | Six-row tables: Trinket Stall (§A7.4) and Grave Goods (§B7.4), including Lake Whistle 325 g and Coin for the Ferry 350 g, both with the rules §6.8 wording |
| 24 | Major | Missing simulation numbers | Minimum ability tables (§A5.4, §B5.4); research tables; training ranks +40 HP / +50 mana / +1 damage at 100 / 50, 60 s and 150 / 100, 70 s; Radius and Flags columns; building ids; Guest stats; the Released's mana; Ferry, Fell and pathing one-liners; Glare Post sight 16 / 10 |
| 25 | Minor | Lantern Glass did nothing for Lodges | It now also raises charging to +1 per 15 s (16 per day), so the extra capacity carries over (§A3.2) |
| 26 | Minor | Four overlapping anti-heal effects; weak Damnatio | Damnatio: auras off, silence, +25 % damage taken, revive +50 % (up to 165 s; inn unaffected). Old Grudge loses "cannot be healed". The Pall keeps the only regen denial; Part D item 4 reworded (mainly heroes) |
| 27 | Minor | Values contradicted rules.md | Glaer halls 1550 / 2050 / 2600, Stilt Larder 500 HP, Tapster 220 HP; Mourning Post Fortified 2; structure regen rows (Pall +1 HP/s, noonlight +1 HP/s); Urn Hearse 3 food / level 3 (and the Wake Barge 6 food / level 6, inside the rules §4.4 heavy band); Glare Post marked "built directly"; recall items use the §6.8 wording; rules.md and neutrals.md added to "Read with" |
| 28 | Minor | Unit classes never assigned | Flags column on both stats tables; `undead` flag defined; "living" = organic and not undead; mechanical (repairable): Springbough, Thistleship, Urn Hearse, Ash Urn, the Released; Tombwalker and Wake Barge are `organic, undead`. The Pall's denial applies to enemy players and hostile creeps alike. (Simplified from the review: undead units accept any heal, so no "Wakeful-only healing" rule) |
| 29 | Minor | Autocasts without defaults | Late Guests on; Mantle of Rank on (engaged ally without the buff); Warm Sap on, Midge Haze on, Scrape Clean off, Wink Out on, Burial Shroud on, Borrowed Face on, Ash-Balm on, Tail Slap off, Winding Sheet off, repairs off (§A5.4, §B5.4) |
| 30 | Minor | Mask pickup underspecified | §B3.2 rows for who takes masks, Roll Call and Guests (never), temporary Lineage up to 4, HP percentage kept |
| 31 | Minor | Pall emission and "on Pall" test undefined | Emits at fixed radius once complete, full coverage after 2 s, unroll visual only; centre-cell test checked live; "lay the Pall, then build" in §B3.1 and §B4 |
| 32 | Minor | Veiled Mourner "+60 / 0 / 0" | Superseded by #8 (trained normally at 80 / 10 / 1, 20 s, true sight 9 m, rules §11 `permanent`) |
| 33 | Minor | One proper name per hero | Four names per hero following each naming rule, checked against the banned list (§A6, §B6) |
| 34 | Minor | Missing archer-rider merge | *Tandem Glide* (High Drey, T3, 150 / 150, 60 s) → **Glide Archer** 750 HP, 1 Light, Pierce 18–22 at 1.5 s, 8.0 m, G+A, 5.6 m/s, 4 food; reuses both meshes. On death the Larkbow survives at 50 % HP |
| 35 | Minor | No Wakeful base-defence crutch | **Tomb Bell** on the Long and Grand Barrow: Arcane 16–20, CD 1.8 s, 9.4 m, G+A, no detection |
| 36 | Minor | Farshot outranged everything | Cast range 12 m, +35 % beyond 8 m, cooldown 10 s |
| 37 | Minor | Long Wake total did not add up | Recomputed. With the Veiled Mourner now a rigged biped (#7), the Long Wake is ≈ 117–126 cr (it would have been 107–116 without that change); combined need ≈ 252–261 cr |
| 38 | Minor | Name and readability collisions with neutrals.md | Part E: 4-row family cross-check (Saltbound, Mire Toads, Hollow Harvest, Old Menhir) plus the Lucky Barrow, Glimmer Font, Firefly Drift / Jar and amber-band rules; neutrals.md added to "Read with" |
| 39 | Minor | FE / Orig tagging incomplete; no ledgers | Ledgers §A5.3 and §B5.3; all unit abilities tagged. Chorus → Lantern Hymn adopted (see #4); Resin Tack not adopted (Amber Fleck answers the same issue) |

**Follow-ups in other files** (not edited here except the banned-terms list; each owner doc should take these in its next pass):

- `docs/design/rules.md`:
  - §4.3 and §20.2: `sylvan` lumber 10 per trip, `chop_interval` 0.9 (12 per trip with Deep Spigots); the rate-check sentence can add
    "sylvan ≈ 0.65 (0.70)". `deathless` row unchanged.
  - §4.4: food providers unchanged; no siege exception needed (Urn Hearse is now 3 food).
  - §8: "Towers: upgraded in place from a scout tower" → add "except the sylvan Glare Post, which is built directly"; the deathless tower
    path is now single (Mourning Post → Urn Tower). Note the deathless Long / Grand Barrow attack (Tomb Bell).
  - §9: add "structures" to both faction regen hooks (Pall +1 HP/s; noonlight +1 HP/s).
  - §10.7: add the `undead` flag (all Wakeful units except the Ash Urn, the Released and the Urn Hearse); define "living".
  - §6.7: note that the deathless *Damnatio* may extend an altar revive past 110 s (up to 165 s).
  - §20.2: `sylvan` and `deathless` building ids are now all listed in §A7 and §B7.
- `docs/design/neutrals.md`: rename **Lucky Barrow → Lucky Cart** and **Glimmer Font → Clearwater Font** (§0, §0.2, §5, §7, §10.1);
  tint the **Firefly Drift** critter and the **Firefly Jar** cool green-white, never amber, at most 6 motes; mark §11 Q12 as answered by this doc's Part E.
- `tools/ip/banned_terms.txt`: `high noon` added under catch-phrases. *(Correction: this was claimed in round 1 but not actually done;
  it was added in round 2, see the round-2 log #7. The round-2 follow-up list below supersedes this one.)*

---

## Review log, round 2 (2026-10-16: second IP-safety and WC3-fidelity reviews)

Same conflict rule as round 1: where the reviews conflicted, IP won and the closest legal alternative was kept. Old names are kept in
the round-1 log above as history; everything above the logs uses the new names.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | Headstone Row shared 2 numbers with its source (90 mana; 1 / 1.5 / 2 s) and its burst-and-knock-up look; Drowse's 80 mana / 4 s sat on the source | Headstone Row: **95 mana**, stun **1.25 / 1.75 / 2.25 s** (heroes 50 %), damage and 11 s kept; new look: headstones **topple like dominoes** and flatten, nothing bursts up, nobody is airborne. Drowse **85 mana** (IP margin; see #24 for durations) (§B6) |
| 2 | Major | Reedstalker had 3 FE (Silent Mere = area silence) and a stealth-assassin kit shape | Silent Mere → **Spring Flood** (Orig: 10 m flood, −30 % move, −2 armour, Slip Under freed and reset once, +30 % speed inside; 150 mana, 120 s). Reed Ambush now triggers from shallow water or within 2 m of a tree (8 s per target). FE back to **2** (§A6) |
| 3 | Major | Lampbreaker matched a custom-map mana-breaker hero ability for ability; Wick Draw copied a mana-drain toggle | Broken Lantern → **Pocket the Flame** (steal 12 primary attribute as AGI, target revealed, 20 s; 125 mana, 120 s). Wick Draw is a **plain passive** (no toggle, no drain) (§A6) |
| 4 | Major | Second WC3 signature per faction: archer-on-flyer merge (Glaer), healing statue → anti-magic flyer morph (Wakeful) | Glaer: Tandem Glide and the Glide Archer **deleted**; new **Lantern Drop** (High Drey, T3, 150 / 150, 60 s: 6 m noonlight for 20 s, 45 s cooldown). Wakeful: Uncork **deleted**; **the Released** is its own T3 unit at the Ferry Steps (220 / 60 / 3, 34 s, 800 HP to sit in the flyer band). Both rubrics re-scored honestly (axis 5 was Partial after round 1; Yes now) with the "drop Tapping / the Pall instead" rule recorded (§A5, §A7, §A9, §B5, §B7, §B9, Parts C and D) |
| 5 | Major | Ash Urn and Veiled Mourner kept their slots' whole kits | Ash-Balm **HP only**; new **Gathered Ashes** (+30 mana per nearby `undead` death; that mask lasts 60 s); no morph. Veiled Mourner: passive true sight → **Mute Witness** (4 s watch → 30 s fog-piercing mark, 2 marks, no invisibility reveal) plus **Plant Candle** (true sight 9 m only while planted, 3 s). Ledger rows list the originals (§B5) |
| 6 | Minor | Dirge shared mana, cooldown and duration with its source | Renamed **Funeral Pace**: 80 mana, 13 s, 8 s (heroes 4 s), −25 % kept (§B5.1, §B5.4) |
| 7 | Minor | `high noon` was claimed in `banned_terms.txt` but absent | Added `high noon` and `it's high noon` under catch-phrases, and a prompt-words section with `canopic`. The round-1 log line now says so (§A8) |
| 8 | Minor | Rootbind, Seedspin and Burial Shroud copied iconic looks | **Withy Snare** (woven hoops, no living roots); **Set in Amber** (sealed in a standing amber lump on the ground, never lifted or spun; the raid-ability name is banned in the internal block); Burial Shroud is a soot-black tasselled cloth **pinned by a cord to a grave stake**, no white net (§A5, §A6, §B5) |
| 9 | Minor | "Tarred Hides" and "Journeyman / Master" echoed WC3 and the kingdom | **Tarred Shingles**; Glaer ranks **Second Verse / Full Chorus**; Wakeful ranks **Half Mourning / Deep Mourning**; research tables and hotkeys updated (§A5, §A7, §B5, §B7) |
| 10 | Minor | "Sunstore" was a sun-reservoir compound | Renamed **Summerhoard** everywhere; noonlight and Open the Shutters kept (§A0, §A3.2, Part D) |
| 11 | Minor | Imaginifer ≈ a tabletop martyr-image standard-bearer | **Pomp-Bearer**, id `deathless_pomp_bearer`; masks only on the pole, never a saint or martyr icon (§B2, §B5) |
| 12 | Minor | Mantle of Rank's Insolence rider kept the frost caster's armour-spell structure | Rider → **Precedence** (non-hero wearer +1 Lineage rank, cap 3; hero wearer ignores knockbacks and drags); autocast **default off**; numbers kept (§B6, §B3.2) |
| 13 | Minor | Damnatio = a known "doom" ultimate; Old Grudge, Family Fortune, Gravius echoed other IP | Damnatio: no silence, no item lock; tagged **genre echo** (new convention). **The Cut Direct**, **Old Money**, **Massenus the Ninth Mask**. Display rule: never show "Sylvan" / "Silvan elves" (Conventions, §B6) |
| 14 | Minor | Banned tokens outside the internal blocks | New **"Internal audit, never in prompts or data"** blocks in §A1 and §B1 hold the stems and rival names; A2 rule 6 rewritten descriptively; FE tags neutral (*mana-drain nuke*, *ranged damage aura*, *drains mana on hit*); "mana-burning" role words → "mana-draining"; music notes and the VO list relabelled (Conventions, §A1, §A2, §A6, §A8, §B1, §B8) |
| 15 | Minor | Soot `#2B2426` + terracotta `#A9573B` read as red/brown | Soot **`#25262A`**; **chalk bone is mass 2**; fired clay **`#C07E5C`** limited to masks, urns and roof tiles (≤ 25 % of a unit); banners soot + chalk + team colour, never terracotta on black; emblem bowl chalk-outlined; Ash Urn body re-coloured (§B0, §B2, §B5, §B9) |
| 16 | Minor | No guard against an MMO's aristocratic-afterlife look | **Tone guard** in §B1 (no gothic or Victorian dress, no crimson-and-gold, no bats; never "court", "sin", "atonement", "anima", "masquerade ball"); repeated in §B8; Guests are festive funeral mourners |
| 17 | Minor | Collisions with kingdom and clans (Smoke Pall, Pitch Firepots, Elder, shoulder-mask, ledger words) | **Sticky Resin**; Thistleship drops **resin bombs**; Lineage **Heir / Eminent / Venerable**; Tombwalker tic is **one grinding voice reciting its epitaph** (lid figure now single); Tapster line ends "There goes an hour of summer."; motto **"Every face kept."**; lore "register" line rewritten. Requests to kingdom.md and clans.md in the follow-ups below |
| 18 | Major | Ash-Balm mana restore let Urns refill each other endlessly | Mana restore removed (#5), and Ash-Balm now **skips mechanical units and structures** (never Ash Urns, the Released or the Urn Hearse). rules §10.7 follow-up below (§B5.4) |
| 19 | Major | Shuttle Throw was undefined for one threaded unit and uncapped | Threading needs **≥ 2 threaded units** and ends when fewer remain; **at most 2 triggers per unit per cast** (80 / 120 / 160); the cast is refused without spending mana if the target has no other enemy within 4 m (§A6) |
| 20 | Major | No home sustain for the Glaer creep loop | **Sunlit yard**: by day +1.5 HP/s within a Lodge's 14 m or a Post's 10 m, no charge; noonlight unit regen raised to **+1.5** (structures +1); tuning fallback +1.0. New T1 **Birch-Bark Poultice** (120 g, 2 / 90 s, 160 HP over 8 s in 6 m). §A9 records "no summons by design". Lantern Hymn and Summer Bead follow (§A3.2, §A5.4, §A7.4, §A9, Part D item 2) |
| 21 | Major | Lay the Pall gave a free permanent mobile Pall; Folded Pall underpriced | Lay the Pall: **only within 12 m of a friendly structure or construction site**, 60 s, cooldown 90 s. Folded Pall **110 g, 2 / 90 s, 60 s**. Intended play and the AI note: "start the expansion Barrow, then lay the Pall under it" (§B3.1, §B4, §B5.4, §B7.4, Part D item 11) |
| 22 | Minor | Thinnest Glaer scouting and detection; Bottled Noon out of band | **Lantern Riders** (High Drey, T2, 75 / 75, 40 s: Treeglider true sight 9 m); T1 **Lantern Stake** (70 g, 2 / 60 s, 2 charges, 10 m vision 180 s, no true sight, caged teardrop); **Bottled Noon** moved to T2: 9 m, 15 s, 8 m range, 80 g (§A4, §A5, §A7) |
| 23 | Minor | Standing Vigil did nothing without Lineage | +4 / 8 / 12 % damage baseline, **doubled** with any Lineage; instant mask pickup kept; still Orig (§B6) |
| 24 | Minor | Drowse too short for the sleep role | Units **15 / 30 / 45 s**, heroes **3 / 6 / 9 s**, 10 s cooldown; mana 85 from #1 (IP won over "keep 80"). Shares no value with its source. Part D item 12 watches chain-sleeping |
| 25 | Minor | Click rule stricter than the project rule | Both bullets and the VO list now ban only poke / poked / poking and WC3 paraphrases; self-aware click lines allowed in each idiom (examples: Tapster "Click all you like. Resin runs at resin speed."; Retainer "One does not hurry the dead. One clicks, and one waits.") (§A8, §B8) |
| 26 | Minor | Potions reused the WC3 250 / 150 values | Birch Syrup +270 over 6 s (140 g); Cloudberry Cordial +160 (120 g); Funeral Honey +230 at once (**130 g**); Lamp-Oil Draught +130 at once (**110 g**). The two Wakeful values were moved off the reviewer's examples, which equalled the kingdom's Sage's Tincture (+140 at 115 g) (§A7.4, §B7.4) |
| 27 | Minor | No T3 shop stock; tier tables incomplete | T3 **Noon-Stone Chip** (300 g, 1 / 180 s, 10 m noonlight post for 120 s, ward 250 HP) and **Ancestor Cast** (300 g, 1 / 180 s, +1 Lineage in 6 m, cap 3). Every research and every shop item now sits in its tier row (§A7, §B7) |
| 28 | Minor | Not concrete enough for data entry | **Footprint** columns (10×10 / 8×8 / 6×6 / 4×4); **projectile tables** (§A5.2, §B5.2); "Lodges and Posts start at 0 charges; the first night burns 10 = 200 s" (§A3.2); Glare Post and Urn Tower **level 3**; **command cards and hotkeys** §A7.5 and §B7.5 |
| 29 | Minor | Masks, Roll Call units and hero-made objects underspecified | Only **`undead`, non-summoned** units drop masks (none from the Ash Urn, the Released, the Urn Hearse; a flyer's mask falls under it). Roll Call units are `summoned`, Lineage 0, 50 % XP, not invulnerable, take summon dispel damage. Stele and Family Vault: Fortified 5, not structures for defeat, block their cells, no XP or bounty, ignored by camp-mode creeps; the Vault takes only allies inside at cast (§B3.2, §B6) |
| 30 | Minor | Six one-line ambiguities | Lines are **perpendicular to caster→point**, centred on the point; Midsummer Hour's bonus **replaces** Warm Strings and its flash hits enemies inside; Bowyer's Hum includes ranged heroes, excludes structures; Tolling Urns hits the **primary target only**; no Warm Sap or Lantern Hymn in Bark Coat, which toggles back; creep leash-return regen still applies on Pall (§A5, §A6, §B3.1, §B5) |
| 31 | Minor | Speeds outside the bands | Wake Barge **4.0**, Thistleship **3.9**, Gravewright **4.4**, Springbough **3.3**; a heavy-air row for rules §7.10 is requested below (§A5.2, §B5.2, §B6) |
| 32 | Minor | "Cenotaph" and "Ferry" each named two things | Raise Cenotaph → **Raise Stele** (the object is a **Stele**); Wake Barge Ferry → **Take Aboard**; Ferry Steps and Coin for the Ferry kept (§B3.1, §B5, §B6, Part D) |

**Follow-ups in other files** (current list; supersedes the round-1 list. Only `tools/ip/banned_terms.txt` was edited in this pass):

- `docs/design/rules.md`:
  - §4.3 and §20.2: `sylvan` lumber 10 per trip, `chop_interval` 0.9 (12 per trip with Deep Spigots); the rate-check sentence can add
    "sylvan ≈ 0.65 (0.70)". `deathless` row unchanged.
  - §7.10: add a **heavy air** row (3.8–4.2 m/s, 5–6 food) for the Wake Barge (4.0) and the Thistleship (3.9).
  - §8: "Towers: upgraded in place from a scout tower" → add "except the sylvan Glare Post, which is built directly"; the deathless tower
    path is single (Mourning Post → Urn Tower). Note the deathless Long / Grand Barrow attack (Tomb Bell).
  - §9: faction regen hooks: Pall non-heroes +1.5 / heroes +2 / structures +1 HP/s; noonlight units +1.5 / structures +1 HP/s; sylvan
    **sunlit yard** units +1.5 HP/s by day near Lodges (14 m) and Glare Posts (10 m).
  - §10.7: add the `undead` flag (all Wakeful units except the Ash Urn, the Released and the Urn Hearse) and define "living"; add
    "**Mana-restore effects skip mechanical units unless the ability says otherwise.**"
  - §15.2: note that leash-return regeneration is not natural regeneration (the deathless Pall does not block it).
  - §6.7: note that the deathless *Damnatio* may extend an altar revive past 110 s (up to 165 s).
  - §20.2: `sylvan` and `deathless` building ids are all listed in §A7 and §B7; the deathless caster id is now `deathless_pomp_bearer`.
- `docs/design/factions/kingdom.md`: rename the **Smoke Pall** research and ability to **Smoke Curtain** (it collides with the Wakeful Pall).
- `docs/design/factions/clans.md`: drop the Mound-Speaker's **ancestor shoulder-mask** (the Wakeful own masks); its interrupting second
  voice can stay with a different prop.
- `docs/design/neutrals.md` (from round 1, still open): rename **Lucky Barrow → Lucky Cart** and **Glimmer Font → Clearwater Font**; tint
  the **Firefly Drift** critter and the **Firefly Jar** cool green-white, never amber, at most 6 motes; mark §11 Q12 as answered by Part E.
- `tools/ip/banned_terms.txt`: **done** in round 2 (`high noon`, `it's high noon`, prompt word `canopic`).
- `tools/ip/value_echo_reference.json` (if the value-echo check is adopted): add this doc's FE-rule-3 rows (Headstone Row, Ancestral
  Drowse, Funeral Pace, Withering Look, Mantle of Rank) so CI keeps them off their WC3 values.
