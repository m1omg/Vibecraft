# Faction design: `kingdom` — the Kingdom of Brennmark

*Design date: 2026-10-16. Status: proposal for review. Faction id: **`kingdom`** (use this id in every doc and data file).*

**Read with:** `docs/research/ip-safety.md` (§0, §2, §3.2), `docs/research/gameplay-mechanics.md` (§11, §12, §13),
`docs/research/visual-art-direction.md` (§3, §7), `docs/research/audio-direction.md` (§3) and `docs/architecture.md`
(cell and footprint conventions).

**Supersedes for this faction:** the "Bastion" placeholder roster and heroes A-H1/A-H2 in `gameplay-mechanics.md` §13.3 and §13.5,
and the "Hearth Wardens" working name and slate-blue/brass palette (README decision 8; see §1.1 for why the name is retired).
Global rules from `docs/design/rules.md` apply (it supersedes `gameplay-mechanics.md` §13.1): food cap 100, upkeep 0–50 / 51–80 / 81–100
→ 100 / 70 / 40 % gold, hero XP table, revive formula, 480 s day/night, damage matrix, 6.0 m hall–mine gap, caster start mana 75.

**Design brief in one line.** A fan should know the job of every Brennish unit and the logic of every build order in seconds,
like the WC3 human kingdom. Nothing a fan sees or hears is Blizzard's: not a name, a silhouette, a palette, an emblem, a voice line
or the culture behind them.

**Units and conventions used below**

- Distances are in metres (1 m = 64 WC3 gu). Speeds are in m/s, and footprints are in 0.5 m pathing cells (`architecture.md`).
- Attack types: Blade, Pierce, Siege, Arcane, Heroic, Spell, Pure (data ids `blade, pierce, siege, arcane, heroic, spell, pure`; rules.md §7.1).
- Armour types: Light, Medium, Heavy, Fortified, Hero, Unarmored, Adamant (data ids `light, medium, heavy, fortified, hero, unarmored, adamant`;
  no Brennish unit wears Adamant).
- "G+A" means the attack hits ground and air units.
- Slice tags:
  - **[SLICE]**: in the vertical slice.
  - **[SLICE+]**: a stretch goal if the budget holds.
  - *later*: full game only.

---

## 0. At a glance

| | |
|---|---|
| **Display name** | **Brennmark** (long form "the Kingdom of Brennmark") |
| **People** | **the Brennish** (singular "a Brenn"; adjective "Brennish") |
| **Government / army** | The Wheel League, a league of guild towns under an elected Wheel Crown |
| **Emblem** | **The Ember Wheel**: an ivory six-spoked wagon wheel on a burgundy field, with a glowing coal (a dark-bronze disc with an ember-orange core) at the hub and three pointed, tapered crown points on the top of the rim |
| **Motto** | "Every wheel a wall." |
| **Cultural inspiration** | Late-medieval Bohemia and Central Europe: wagon-forts, pavise shields, early hand-cannons, threshing flails, guild towns, half-timbered houses with onion-dome towers, astronomical clocks, silver mining, bobbin lace, the linden tree, storks nesting on rooftops |
| **Palette** | Burgundy, ivory, dark bronze and blackened iron, with oak brown (§2.2). Not blue/white/gold, and no lion |
| **Signature mechanics** | **Levy Horn**: workers near a hall arm themselves in place as a temporary flail levy. This is the faction's one WC3-derived mechanic (militia), shown differently. Multi-builder sites (the **Hod Chain**, §4) are a cross-faction rule in this game, not a Kingdom signature. **Wagon Fort**: Wall Wagons deploy into fortified gun-wagons and chain into walls. This mechanic is original |
| **Play pattern** | Sturdy, slow, expensive. Strong infantry walls behind gunpowder, the best towers, flexible casters, late heavy cavalry and air. Weak to mobile harassment early and to magic-damage burst on its unarmoured casters |
| **Slice content** | Hodman (+ Flail Levy), Pavisier, Hookgunner, Bombard Wagon, Linden Sister. Heroes: Wheel Marshal and Firewright. 10 buildings: Moot Hall → Walled Burg, Croft, Oath Hall, Drill Yard, Timber Yard, Foundry, Collegium, Wainwright Yard, Curio Cabinet, Lookout → Gun Tower. 14 research (§11) |

---

## 1. Identity

### 1.1 Names

- **Faction display name: Brennmark.**
  - It is invented, short (9 letters, fits the faction picker) and pronounceable.
  - It sounds Central European ("brenn" means *burn* in German), and it points at the faction's fire-and-gunpowder identity.
  - It does not use any Blizzard pattern (§2.1 of the IP doc) or a "-craft/War-/Star-/-storm" pattern.
- **People name: the Brennish.**
  - They are human, so no invented species name is needed. Treat the people's name as a nationality ("the Brennish", like "the Danish").
  - In UI, use "Brennmark" for the faction and "Brennish" in tooltips and lore. Never "Human" or "Alliance".
- **Why "Hearth Wardens" is retired for this faction:**
  1. "Hearth" sits close to Blizzard's *Hearthstone* mark (same goods: fantasy games). Hearthstone is also an item in WoW's world.
  2. "Warden" is a WC3 hero name (ip-safety §2.1).
  3. Its slate-blue and brass palette sat next to Alliance blue/gold (README open question 9).

  The **voice personality** of the audio doc (guild-proud, deadpan tradesfolk) is kept. It fits Hussite-style town militias.
- **Naming rule for every Brennish name:** plain English trade or historical words ("Hodman", "Pavisier", "Moot Hall", "Wainwright"),
  or compounds of them. Personal names mix Central-European first names with English trade surnames ("Dame Hedvika Spokewright").
  - UI strings use no diacritics, for font coverage.
  - No real historical people, no real place names, no religious symbols (in particular, **no chalice**, the Hussite emblem).
  - No `-craft` token in any name (ip-safety §4 keeps distance from that pattern around this project).
- **Names never to use** (they belong to other games in the same space):
  - *Age of Empires II* Bohemian terms: **Hussite Wagon, Houfnice, Wagenburg Tactics, Hand Cannoneer, Bombard Tower**.
  - *World of Warcraft* ability names (e.g. Scatter Shot) and WC3 building coinages (arcane sanctum, arcane vault, arcane tower, gryphon aviary, call to arms).
  - *Warhammer* casters named by colour or college (**Bright, Celestial, Amethyst**…), and **"the Moot"** as a region name. "Moot Hall" as a building is fine.

### 1.2 Emblem: the Ember Wheel

- **Shape:**
  - An ivory wagon wheel with **six** thick spokes.
  - A **glowing coal** at the hub: a solid dark-bronze (`#6E4A26`) disc with a small ember-orange (`#F08A2A`) core. The coal is at most
    **20 %** of the emblem's diameter. No flame shape and no bronze highlight (`#B07F3E`) anywhere on the emblem.
  - Three **crown points** rising from the top of the rim, each **pointed and tapered** (never square or blunt, so they never read as cog teeth).
  - It sits on a burgundy field.
  - Banners are **swallow-tailed pennants** (two-tailed), never rectangular hanging banners.
- **Read test:** it must read at 24 px as "wheel with a coal at its hub". Keep spokes thick and the coal one solid round shape.
- **Do not:**
  - Ship a bare white wheel on red. Several real civic coats of arms use that (e.g. Mainz, Osnabrück).
  - Use 8-, 16- or 24-spoke wheels, which resemble religious or national symbols (24 spokes: India's Ashoka Chakra).
  - Add a lion, eagle, gryphon, griffon, chalice, twin-tailed comet or warhammer.
  - Use a **flame on its own** on banners, cloaks or tabards. Red/ivory plus a gold-looking flame is a known human military-order look in
    another Blizzard game; the coal stays inside the wheel and is never gold.
- **Where it appears:** pavise faces, the hall's gable, roof finials (forged iron wheels on poles), the Wall Wagon's side boards, hero cloaks and the loading screen.

### 1.3 Lore (original)

> Brennmark is a hill-kingdom of market towns, silver pits and gun foundries strung along the slow brown River Vel.
> Two generations ago its knights rode east to a war beyond the passes and never came home. The towns they left behind
> refused to wait politely to be conquered. Coopers, smiths, threshers, carters and lacemakers swore themselves into the
> **Wheel League**. They chained their market wagons into rolling walls, swung their threshing flails at anything that came over
> the boards, and taught themselves to make thunder in iron pipes. When the League won, it melted the old crown down and
> recast it as the rim of a wagon wheel. That **Wheel Crown** is worn by whichever guildmaster the towns elect, for as long as
> the towns put up with them.
>
> The Brennish are craftsfolk first and soldiers second. They drill like a trade, keep a ledger of every arrow, argue about
> overtime while holding the line, and paint their shields themselves, badly and proudly. Their storks come back every spring
> to the same chimneys; their astronomers keep the great town clocks honest; their healers swear by linden-flower tea.
> Now the steppe clans have come over the eastern passes, the levy horns are blowing on every hall, and every wheel in
> Brennmark is about to become a wall.

### 1.4 Faction personality (gameplay)

| Pillar | What it means in play |
|---|---|
| **Walls of wood and iron** | Pavisiers soak ranged fire, Wall Wagons deploy into forts, towers are strong and buildings armour up with masonry research |
| **Thunder behind the boards** | Gunpowder (Hookgunners, Bombard Wagons, Gun Towers and Bombard Rondels) hits hard but is slow to reload |
| **Every hand counts** | Workers become a fighting levy at a horn blast. Cheap Lookouts become towers. Crofts are sturdy |
| **Guild casters** | Three caster trades (healer, debuffer, anti-mage), each with Journeyman and Master training, like a guild |
| **Late power** | Tier 3 adds the Ironrider heavy cavalry, the Stork Rider heavy air and Wagon Fort chains |

---

## 2. Visual identity

Base style: "Storm-lit Heroic Diorama" (`visual-art-direction.md` §7.1): chunky heroic proportions, identity in the upper third,
painted light, 1–2 colour masses plus team colour, toy-soldier procedural motion.

### 2.1 Silhouette rules

1. **The kettle-hat brim is the faction read.**
   - Soldiers wear wide-brimmed iron kettle hats. Workers wear wide straw hats.
   - From the −56° game camera a brim reads as a **disc**, which no WC3 human unit has. Brims are 1.6× head width.
2. **The pavise is the second read.**
   - A tall, flat, round-topped rectangular shield with a vertical central ridge, 1.1× unit height when carried.
   - Never a kite shield or a heater shield. Never a round shield on infantry; only the Wheel Marshal's wheel-shield is round.
3. **Long, two-part weapons:** threshing flails, war-scythes (blade straightened on a pole), hook-guns on forked rests, falchions,
   horseman's picks. **No** iconic broadsword-and-kite combination, and no giant hammer on any hero.
4. **Machines are boxes on wheels.** Wagons are plank boxes with gun-loops and big spoked wheels. The wheels are the moving
   read, and animating them is procedural.
5. **Upper-third identity per unit:**

   | Unit | Upper-third read |
   |---|---|
   | Hodman | Straw-hat disc plus a V-shaped hod on one shoulder |
   | Pavisier | Kettle-hat disc plus the top edge of the pavise |
   | Hookgunner | Long gun barrel sloped over the shoulder, forked rest, a curl of slow-match smoke |
   | Linden Sister | Large wreath of linden leaves, basket on her back |
   | Lacewright | Huge stiff lace collar, tall cap, bobbin pillow at her hip |
   | Assayer | Balance scales strapped on his back, tall felt hat with a silver plaque |
   | Ironrider | Horse with a pavise-like chest plate, tall lance with a swallow-tail pennon |
   | Bombard Wagon | Fat bronze tube on a two-wheeled cart, two crew in kettle hats |
   | Wall Wagon | Plank box, hinged side board, an iron wheel finial on a pole |
   | Brass Kestrel | Brass bird with spread wings, a spinning key on its back |
   | Netcaster | Rolled weighted net slung over the shoulder, short pole-hook |
   | Stork Rider | White stork with its **neck stretched straight forward**, **long red legs trailing**, a long straight red bill and black flight feathers as one mass; the rider sits **behind the wings** in a kettle hat with a sling (see §2.6) |

6. **Heroes are 1.25× infantry and each has one oversized prop:**

   | Hero | Oversized prop |
   |---|---|
   | Wheel Marshal | Wheel-shield |
   | Orrery Sage | Brass armillary rings on a back-frame, rising above the head |
   | Flail Hetman | Giant three-club war-flail over the shoulder |
   | Firewright | Tall felt chimney-hat, bandolier of clay flasks |

7. **Buildings** use steep roofs with **onion-dome** turrets and stepped gables, and big wagon wheels as decoration.
   Never steepled grey stone with blue roofs.

### 2.2 Palette (albedo targets; tune in engine with the faction LUT)

| Role | Name | Hex | Where |
|---|---|---|---|
| Primary cloth / roof | Burgundy | `#7B1E2E` | Hoods, aprons, roof tiles, caparisons |
| Primary light | Ivory linen | `#EDE2C8` | Quilted gambesons, plaster walls, linen covers, the emblem wheel |
| Ivory shadow | Oat | `#C9B994` | Painted shadow of ivory areas |
| Metal 1 | Dark bronze | `#6E4A26` | Onion domes, cannon barrels, buckles, the hub coal |
| Metal 1 highlight | Bronze | `#B07F3E` | Painted highlights only; **never on the emblem** |
| Metal 2 | Blackened iron | `#3D4046` | Kettle hats, plate, chains, wheel rims |
| Metal 2 highlight | Iron | `#7E848C` | Painted rim highlights |
| Wood | Dark oak | `#5A3A22` | Timber frames, wagons, gunstocks, pavise backs |
| Accent | Straw | `#C9A85A` | Worker hats, thatch accents, rope |
| Accent (small) | Linden green | `#7E9A4A` | Linden Sister wreath, herb bundles only |
| Accent (VFX) | Ember orange | `#F08A2A` | Fuse sparks, muzzle flash, window glow at night |

Rules:

- **Per unit:** ivory and burgundy are the two big masses. Iron and bronze are the third value, and team colour is the fourth.
- **Saturation:** at most 70 % on cloth, which leaves room for team colour at 90 %+.
- **No blue anywhere** except as team colour.
- **No gold-yellow trim.** Use bronze, which is darker and browner.
- **Red-team readability:** when the player is red, team colour sits next to burgundy. Keep team-colour areas **brighter and more saturated**
  than burgundy (value ≥ 60 %) and outline team-colour panels with a thin ivory border, so red-team Brennmark still reads.

### 2.3 Material language

- **Lime plaster** (ivory, slightly lumpy) between **dark oak timber frames**.
- **Red-brown clay tiles** with a burgundy tint.
- **Cast bronze:** domes, cannons, the Sage's rings, the Kestrel.
- **Blackened iron:** hats, chains, plate with simple fluting.
- **Quilted linen:** gambesons with diamond quilting painted into the albedo.
- **Folk-painted wood:** pavises and wagon boards carry hand-painted wheels, flowers and stripes, deliberately a little crude.
- **Bobbin lace:** Lacewright only.
- **Straw and wicker:** hats, hods, baskets, stork nests on roofs.
- **No polished steel, gold leaf, marble or radiant golden glow.**
- **No slashed-and-puffed sleeves** in two-colour stripes (the Landsknecht look of a well-known tabletop Empire army). Sleeves are plain
  quilted linen or fitted wool.

### 2.4 Team-colour placement (magenta key `#FF00FF` in concept art; shader-tinted in game)

| Asset | Team-colour areas (aim for 10–15 % of the visible silhouette from the game camera) |
|---|---|
| Workers | Hat band, shoulder sash |
| Infantry / ranged | **Pavise face field** (the emblem keeps its ivory wheel and dark-bronze coal), arm sash, kettle-hat plume |
| Casters | Hood lining, apron stripe, collar ribbon |
| Cavalry | Caparison panels, lance pennon |
| Wagons | Canvas cover stripes, the painted band on the side boards, wheel-rim paint |
| Air | Stork Rider: saddle cloth and rider sash. Kestrel: enamel wing panels. Netcaster: net floats |
| Heroes | Cloak, plume, and the hub enamel on the Wheel Marshal's shield |
| Buildings | Swallow-tail roof pennants, window shutters, the ridge-tile band, the ring under each onion dome |

### 2.5 Architecture language

- **Body:**
  - Half-timbered: ivory plaster, dark oak frames with diagonal braces. The ground floor is rubble stone on larger buildings.
  - Steep burgundy-red tile roofs, 55–60°.
  - **Stepped gables** on halls and the Foundry.
  - Wooden galleries and arcades at street level.
- **Crowns:** **onion domes** in dark bronze on the hall and towers, each topped by an iron Ember Wheel finial.
- **Tier growth of the hall (upgrade in place):**
  - **Moot Hall:** a two-storey half-timbered hall with one small onion turret.
  - **Walled Burg:** adds a stone ground floor, a ring of parked wagons as a low wall, and a taller dome.
  - **Crown Burg:** adds a square clock tower with a painted **astronomical clock face** (rings, sun and moon hands; our own design) and a double onion dome.
- **Construction verb: "scaffold-raised".**
  - Timber scaffolding with ladders rises first, and Hodmen climb it carrying hods.
  - The building appears ground-up inside it (the `build_progress` shader). The scaffold drops away with a dust puff when the building is done.
- **Night:** windows glow ember orange (`#F08A2A`, emissive above 1.0, so they bloom). There are no other light effects on buildings.
- **Distinct from WC3 human buildings:** no blue roofs, no grey-stone steeples, no gold trim, no lion banners, no gryphon roosts.

### 2.6 Squint-test risks and mitigations (internal audit; other games' names appear here for review only)

**Against WC3:**

| Brennish design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Pavisier | Footman | Low | Kettle-hat disc, tall pavise, falchion, ivory gambeson. Never a closed helm with a kite shield |
| Hookgunner | Rifleman (a dwarf) | Low | Human, long thin hook-gun on a forked rest, slow-match smoke. No backpack, no beard |
| Ironrider | Knight | **Medium** (horse and lance is a genre staple) | Burgundy caparison with painted wheels, horse **chest pavise**, kettle-brimmed sallet with plume, no blue/gold, no full-face great helm |
| Wheel Marshal | Paladin | **Medium** (armoured support-tank role) | A woman in blackened plate with a **wheel-shield and war-pick**. No hammer, no book, no gold, no glowing hands. The heal VFX is drifting linden blossom; its **icon** is a linden sprig over a wheel hub, never a glowing hand or a pillar of light (ip-safety §2.4). Her aura is offensive (§6.3), which breaks the heal / defensive-aura / shield / save-the-team slot pattern |
| Orrery Sage | Archmage, and the Blood Mage's orbiting orbs | Medium | A woman with a brass armillary frame on her back and a telescope staff. **Never** a long white beard, pointed hat or robe-and-staff look, and **never orbs circling her head** |
| Flail Hetman | Mountain King | Low | A tall human (not a dwarf), no beard braids, no hammer. The flail is the read |
| Firewright | Blood Mage | Low | A soot-faced human in a leather apron with a chimney-hat. No elf, no red-and-gold robes, no orbs |
| Brass Kestrel | Flying Machine | Low | A clockwork bird, not a rotor craft |
| Stork Rider | Gryphon Rider | **Medium** (from above at 64 px, a rider on a big white-feathered bird throwing things, as heavy Arcane air with a splash research, reads as the WC3 unit) | Stork-only reads: neck stretched straight forward in flight, long red legs trailing, long straight red bill, black flight feathers as one mass. **No** hooked beak, no feathered ruff or mane, no brown hindquarters, no four-legged body. The rider sits **behind** the wings and attacks with a **sling** (underarm whirl), never an overhead throw |
| Moot Hall | Town Hall | Low | Half-timber, onion dome, stepped gable, burgundy roof |

**Against other famous Central-European gunpowder humans and Bohemian factions:**

| Brennish design | Nearest design elsewhere | Risk | Mitigation |
|---|---|---|---|
| Hookgunner | *Warhammer* Empire Handgunners | Low–Medium | No slashed-and-puffed Landsknecht sleeves, no two-colour stripes, no feathered beret. Kettle hat, quilted ivory jack, forked rest |
| Flail Levy | *Warhammer* Flagellants | Low | A tired worker with a threshing flail and a borrowed kettle hat. Never bare-chested, never self-harm, never zealot banners |
| Orrery Sage | *Warhammer* Celestial Wizard and its "arcane orrery" war-altar | **Medium** | **No** blue starry robes, no comet-topped staff, no twin-tailed comet anywhere. Her armillary stays on her **back-frame**: never mounted on a wagon, cart or altar. Ivory coat, spectacles, telescope staff |
| Firewright | *Warhammer* Bright Wizard | Low | A soot-faced tradesman with flasks and a linstock, not a robed flame mage. Never called "Bright" or any college name |
| Clockwork units (Kestrel, Halberdier) | *Warhammer* Engineers' contraptions | Low | Brass-and-wood toy-like automata with wind-up keys; no steam boilers, no goggled engineer hero |
| Iconography | *Warhammer* Empire (twin-tailed comet, griffon, warhammer) | Low | None of these anywhere: emblem, banners, props or VFX |
| Wall Wagon | *Age of Empires II* Bohemian armoured wagon | Low–Medium | Never use the AoE2 names (§1.1). Our wagon deploys into a fort and chains to others; its look is a painted plank box with an iron wheel finial |
| Bombard Rondel | *AoE2* bombard-armed tower | Low | Named and shaped as a squat round rondel (§7.3), never "Bombard Tower" |

**Review rule:** every concept image is checked side by side against its nearest WC3 analogue (and, for the rows above, the other
franchise's analogue) before image-to-3D (ip-safety §2.8).

### 2.7 Example compliant concept prompt (Pavisier)

> full body late-medieval town militia soldier carrying a tall flat round-topped rectangular wooden shield with a vertical central ridge
> and a hand-painted pale wagon-wheel motif, wide-brimmed blackened iron kettle hat, quilted ivory linen jacket, burgundy hood,
> dark iron arm guards, short heavy curved single-edged sword held clear of the body, standing A-pose, front three-quarter view,
> centered, entire figure visible including feet, solid magenta (#FF00FF) on the shield face field and on the arm sash, evenly lit flat albedo,
> no cast shadows, + global style suffix (visual §7.3). No text, no logo, no watermark.

Generate the pavise and the falchion separately as props (the weapon is its own pivoting mesh, visual §7.1).

---

## 3. Voice and audio identity

### 3.1 Voice personality

- **Faction voice: guild-proud, deadpan, stubborn tradesfolk.** War is a job with contracts, fees, tea breaks and pride in
  workmanship. Humour comes from **who they are**: ledgers, guild rules, painted shields, bad backs. Never pop culture.
- **Delivery:**
  - Neutral English with crisp consonants and an unhurried rhythm.
  - **No faux Czech or German accent.** A caricature accent is disrespectful and dates badly.
  - Colour comes from invented guild jargon instead ("on the ledger", "fee", "journeyman papers", "the boards").
- **Per-unit verbal tic** (one each):

  | Unit | Voice and verbal tic |
  |---|---|
  | Hodman | Older, wry. Counts clicks as billable. Calls his hod "Agnes" |
  | Pavisier | Young, earnest. Proud of the wheel he painted on his pavise himself |
  | Hookgunner | Slightly deaf from gunfire: "Eh? Louder!" |
  | Ironrider | An ex-noble now on the League's payroll, quietly offended by it |
  | Linden Sister | Brisk, motherly: "Sit. Drink this." |
  | Lacewright | Precise and soft-spoken, counts stitches, a little menacing |
  | Assayer | A bureaucrat who weighs everything: "Seven grains light. Fraud." |
  | Bombard Wagon | Two crew who bicker |
  | Wall Wagon | A teamster who talks to his wagon |
  | Brass Kestrel | No voice: clockwork whirr and a two-note whistle |
  | Netcaster | A cheerful stork-catcher |
  | Stork Rider | Talks to her stork |
  | Heroes | See below |

- **Hero voices:**

  | Hero | Voice |
  |---|---|
  | Wheel Marshal | Calm low alto; carter and road metaphors |
  | Orrery Sage | Precise; always mentions the time |
  | Flail Hetman | Booming ex-thresher; harvest metaphors |
  | Firewright | Cheerful pyromaniac with no eyebrows left |

### 3.2 Sample lines (original; checked against the WC3 human and orc quote pages per audio §3.2; reject any line a fan would recognise)

**Hodman (worker)**

| Category | Lines |
|---|---|
| Ready | "Hod's loaded, boots are muddy." · "Fresh off the cart and already behind schedule." · "Signed on, paid up, mostly willing." |
| What | "Mm? Mind the bricks." · "Hodman. Guild card's in me hat." · "Talk quick, Agnes is heavy." |
| Yes | "Lifting with the knees." · "Agnes and I'll see to it." · "Fine, fine. It's on the ledger." |
| Attack (as Flail Levy) | "This was not in the contract!" · "Flail's out, mind your heads!" · "Like threshing, only it shouts back." |
| Annoyed (played in order) | "That's a prod. I'm noting it." → "Two prods. Guild says that's a fee." → "Agnes thinks you've got cold fingers." → "Not saying I'll strike. Just saying I own a flail." |
| Built (job-complete category) | "Raised, roofed, and only slightly crooked." |

**Pavisier (line infantry)**

| Category | Lines |
|---|---|
| Ready | "Pavise painted, wall's open for business." · "Plank by plank, the boards go up." · "Chin strap tight. Let's be stubborn." |
| What | "The wall's listening." · "Pavisier. What needs holding?" · "Careful, the paint's still wet." |
| Yes | "Wall's moving." · "Shifting the boards." · "Plant me where you point." |
| Attack | "Over the boards!" · "Falchions out!" · "Wall forward, step together!" |
| Annoyed (in order) | "Knocking won't get you through. It's a wall." → "There's a wheel painted on the front. Did it myself." → "It's a good wheel. Bit wobbly on the left." → "Mum calls me a wall with legs. She means it nicely. I think." |

**Wheel Marshal (hero)**

| Category | Lines |
|---|---|
| Ready / revived | "Spoke to spoke, rim to road. I'm ready." · "Spokes tight, rim true." · "Show me a road and I'll be the wall on it." |
| What | "Speak. I hear you over the axles." · "The Marshal attends." · "Which road, which wall?" |
| Yes | "Wheels turning." · "On the road." · "Where you point, the rim follows." |
| Attack | "Brace, then break them!" · "Wheel to wall!" · "Hold the ring, then push!" |
| Annoyed (in order) | "A jostled wheel keeps turning. Mostly." → "I replaced thirty spokes this year. Don't be the thirty-first." → "I once stopped a runaway cart with my face. This is worse." → "...Fine. Squeak, squeak. Happy?" |

**Hookgunner (ranged, slightly deaf)**

| Category | Lines |
|---|---|
| Ready | "Match lit, barrel's clean." · "Hookgunner. Point me at something loud." · "Powder's in the pouch, ears are ringing." |
| What | "Eh? Louder!" · "Say again? Gun's still ringing." · "Hookgunner, listening. Mostly." |
| Yes | "Moving the hook." · "Right, right. That way?" · "Carrying the rest, don't rush me." |
| Attack | "Hook on the boards. Fire!" · "Give them the thunder!" · "Cover your ears, lads!" |
| Annoyed (in order) | "What? I can't hear you clicking." → "Oh, that. Yes, I felt that one." → "My ears ring, my back aches, and now this." → "One more and I'll fire this thing indoors." |

**Bombard crew (two bickering gunners: the Elder and the Younger)**

| Category | Lines |
|---|---|
| Ready | "Wheels chocked, barrel swabbed." · "Two crew, one bombard, no agreement." · "She's loaded. — Who loaded her? — I did. — Did you, though?" |
| What | "Bombard crew. — Mostly me." · "Barrel's warm, talk fast." · "We're listening. — He's not." |
| Yes | "Push! — I am pushing!" · "Heave together. — Together, he says." · "Shifting her. Slowly." |
| Attack | "Touch it off! — You touch it off!" · "Mind the kick!" · "Ranging shot... and again, properly." |
| Annoyed (in order) | "Careful, she's loaded. — Is she? — She is now." → "He packed the charge. If it goes off, it's on his ledger." → "We drew straws for this job. I lost. — You lost twice." → "Do that again and I'll let him aim." |

**Firewright (hero, cheerful pyromaniac)**

| Category | Lines |
|---|---|
| Ready / revived | "Who ordered a bonfire?" · "Eyebrows? Overrated." · "Firewright, freshly singed." |
| What | "Hm? Mind the flasks." · "Speak up, the fuse is short." · "Firewright, at your elbow. Not too close." |
| Yes | "To the warm side, then." · "Fuse is lit, feet are moving." · "Off we go. Mind the sparks." |
| Attack | "Here's some warmth for you!" · "Catch!" · "With my compliments!" |
| Annoyed (in order) | "Careful, I'm combustible." → "I've lost two eyebrows and a good hat to this trade." → "Click once more and I'll juggle the flasks." → "...Ooh, that one's fizzing. That's not good. That's not good at all." |

**Advisor ("the Reeve", clipped town official).** One line per rules.md §17.3 trigger (plus the placement error and hero-trained events).
**Reeve rules:** no "[build verb] more [supply building]" pattern; never the word "done" on a completion event; never "…under attack" (§17.3).

| # | Trigger (rules.md §17.3) | Line |
|---|---|---|
| 1 | Own units attacked | "Our soldiers are in a scrap out there." |
| 2 | Own building attacked | "Someone's breaking our timber!" (halls: "Our hall is taking a beating!") |
| 3 | Workers attacked (the Levy Horn cue) | "They're at the Hodmen! Shall I sound the horn?" |
| 4 | Hero died | "The captain's been carried off the field." |
| 5 | Hero revived | "Back on the oath, back on the payroll." |
| 6 | Hero level-up | "The captain's learned a new trade." |
| 7 | Hero trained | "A captain stands sworn." |
| 8 | Building finished | "Raised and roofed. The guild approves." |
| 9 | Research finished | "The guild has signed it off." |
| 10 | Unit trained, queue now idle | "The yard's queue is empty." |
| 11 | Need gold | "The strongbox is light." |
| 12 | Need lumber | "We're short on timber." |
| 13 | Need supply (food) | "Every croft's full. No room for more hands." |
| 14 | Need hero slot | "No more oaths until the burg grows." |
| 15 | Cannot build there (placement) | "The ground won't take it there." |
| 16 | Gold mine low (1,500) | "The seam's running thin." |
| 17 | Gold mine exhausted | "That seam's picked clean." |
| 18 | Upkeep tier rises | "Wages are eating the strongbox." |
| 19 | Cripple countdown started | "No hall, no town. Raise one, or they'll find us." |
| 20 | Cripple revealed | "Every roof we own is on their map now." |

### 3.3 Production notes (audio)

- **Line budget:** follows audio §3.2. For the slice:

  | Voice | Lines |
  |---|---|
  | Hodman | 19 |
  | Pavisier | 18 |
  | Hookgunner | 18 |
  | Bombard crew | 16 |
  | Linden Sister | 18 |
  | Wheel Marshal | 26 |
  | Firewright | 26 |
  | Reeve (advisor) | 21 |
  | **Total** | **162** |

  Probe TTS cost with one 5-line batch first (README open question 3).
- **VO lint (run on the VO script before recording; to be added to `tools/ip/` with the script):**
  1. No "poke", "poked" or "poking" in any **Annoyed** line (the word fans tie to a banned WC3 click-spam line).
  2. Reeve lines: no "[build verb] more [supply building]" pattern; no "done" on a completion event; no "…under attack".
  3. Every line passes `check_banned_terms.py` and the quote-page check (§13 Q9).
  4. No line echoes a song, film, book or slogan (§3.1 "never pop culture"). Rejected in review so far: plank-in-the-wall, the turning
     wheel, "rolling out", "signed, sealed…", "burn bright…", "smell that…".
- **Casting and processing:**
  - ElevenLabs preset voices through Krea, never cloned from real actors.
  - Wheel Marshal: a calm low female voice, light room reverb.
  - Hodman: an older male voice with a slight rasp.
  - Pavisier: a young male voice.
  - Hookgunner: an EQ notch to sound slightly muffled.
  - Bombard crew: two contrasting male voices (older gravelly, younger quick), alternating within a line.
  - Linden Sister: a brisk, warm middle-aged female voice.
  - Firewright: a bright, quick male tenor; a faint crackle layer under ability lines only.
- **Faction music:**
  - Instruments: a village band gone to war. Hurdy-gurdy, bagpipe drone, hammered dulcimer (cimbalom-like), fiddle,
    frame drum and field snare, low horns, wordless male chorus hum.
  - Mixolydian/Dorian, 84–100 BPM.
  - **Avoid** full symphonic brass fanfares with big choir, which is the WC3 human colour.
- **Signature SFX:**
  - Hand-cannon "whump-crack" with a 1.5 s smoke hiss tail.
  - Flail chain rattle.
  - Wagon creak and wheel rumble.
  - The levy horn: a two-note low wooden horn, our own interval.
  - The "construction complete" cue: a scaffold collapsing with a dust "fwump".
- **UI sounds:** wood knock plus iron latch (click); hand-planed wood stroke (complete); dull double knock on boards (error).

---

## 4. Economy and faction rules

| Rule | Brennmark value | Note |
|---|---|---|
| Start (global) | Moot Hall, 5 Hodmen, 500 gold / 150 lumber, 08:00 | rules.md §3.2 |
| Gold | Workers walk 10 gold per trip to a hall | Genre standard |
| Lumber | 10 per trip (15 with Bow Saws, 20 with Felling Crews; both *later*). Drop-off at a hall or the **Timber Yard** (in the slice; build it at the tree line); 1 lumber per 0.8 s chop | Trees are felled when empty (50 lumber). With a Timber Yard 4 m from the trees a Hodman makes ≈ 0.93 lumber/s, the same as a clans Yurtwright (rules.md §4.3) |
| Food | Moot Hall 12 → Walled Burg 14 → Crown Burg 16; **Croft +7** | About 12 Crofts reach the cap of 100 |
| Hero slots | T1: 1, T2: 2, T3: 3. First hero free (5 food) with a free Homeward Horn | Global |
| Construction: the **Hod Chain** | Scaffold-raised. One Hodman builds. Up to **2 more** may join as **hod carriers** (they ferry materials up the scaffold): each adds **+40 %** build rate and costs **5 lumber per 10 s** while carrying (paid continuously; a carrier stops when lumber runs out). Rate: 1 / 1.4 / 1.8 × | Multi-builder sites are a **cross-faction rule** in this game (rules.md §4.3: sylvan and deathless 2 builders each), re-presented here with a lumber cost. Not a Kingdom signature (§12 row 5) |
| Repair | Hodman autocast (default off); costs 30 % of the building's cost pro rata. A full repair takes **1.5 × the building's build time** for one Hodman; each extra repairer adds the same rate (rules.md §4.8) | |
| **Levy Horn** (WC3-derived signature, re-presented) | See below | The one WC3 signature mechanic this faction uses |
| **Wagon Fort** (original signature) | Wall Wagon deploy and chain (§5.4) | |
| Night | No unit modifiers. Buildings glow at night. The **Night Watch** research lets buildings keep day sight at night | |

**Levy Horn: rules**

- **Take Up the Flail** (per Hodman) is usable only within **22 m** of a finished friendly hall (any tier). Outside that range the button
  is greyed, with the tooltip "Too far from a hall".
- **Levy Horn** (hall button, no target): every Hodman within 22 m of that hall arms. A Hodman inside the mine when the horn sounds arms
  as it exits.
- **Leash:** a Flail Levy more than **30 m** from every friendly hall stands down after **5 s** (a "levy far from home" countdown shows over it).
- **Stand Down (all)** (hall button, no cooldown): every Flail Levy of the player stands down at once. Each Levy also has its own Stand Down.

**Levy Horn: how it differs from WC3's militia call-up**

| | WC3 militia | Brennmark Levy Horn |
|---|---|---|
| Trigger | A hall command and a per-peasant command; the peasant runs to a hall to transform | Hall horn and a per-Hodman command, both usable only near a hall |
| Where workers transform | At the hall, after running there | **In place**, after 1.5 s (they unsling the flail and swap the straw hat for a kettle hat) |
| Range | Peasants around the hall (radius unverified) | Hodmen within **22 m** of a hall; Levies leash at 30 m |
| Cooldown | None | 60 s on the hall horn. 20 s per worker after standing down |
| Duration | 45 s | **40 s**, or until Stand Down |
| After it ends | Back to work order | Automatically resumes the last gather or build order. Carried resources are kept |
| Presentation | Hall command and call sound | Low wooden horn blast, and a burgundy levy flag runs up the hall's pole |

---

## 5. Unit roster

### 5.1 Fidelity map (role slot → Brennish unit)

Policy (mechanics §12.2): keep each **role**, never a unit's whole **kit**. Every unit below has at least one mechanic of its own.

| Role slot (generic) | Brennish unit | Kept familiar (role, build logic) | Made ours (expression and mechanics) |
|---|---|---|---|
| Worker + militia call-up | **Hodman / Flail Levy** | Gathers, builds, repairs; near a hall, workers turn into temporary militia | Arms in place near a hall; flail and hat swap; horn and flag; Hod Chain building with a lumber cost |
| T1 melee with defensive stance | **Pavisier** | Cheap heavy-armour line infantry; research a stance that blunts Pierce | **Cover** for allies behind it; painted pavise and falchion |
| T1 gunpowder ranged | **Hookgunner** | Pierce ranged that needs the smithy; range research at T2 | Hook-gun on a forked rest; **Braced Shot** passive |
| T3 heavy cavalry | **Ironrider** | Fast, heavy, expensive, T3 | **Couched Lance** charge; Bohemian barding |
| Healer caster | **Linden Sister** | Autocast heal; dispel at Journeyman; buff at Master | Herbalist; Master buff is spell resistance plus regeneration |
| Slow / debuff caster | **Lacewright** | Autocast slow; ally invisibility; hard disable at Master | **Lace Cocoon** can also protect an ally |
| Anti-magic melee | **Assayer** | Spell-immune melee, burns mana on hit | **Silver Seal** area silence instead of stealing or controlling |
| Long-range splash siege | **Bombard Wagon** | Long-range splash siege with a reveal shot | **Case Shot**: splash slows; crew-pushed bronze bombard cart |
| Armoured anti-building engine | **Wall Wagon** | Slow armoured building-breaker with an anti-air mode | **Wagon Fort** deploy and chaining |
| Air scout / anti-air | **Brass Kestrel** | Cheap fast flyer, anti-air, true sight, air-splash research | **Hunting Stoop**: a periodic dive that marks one ground unit (no permanent ground attack); clockwork bird |
| Heavy air | **Stork Rider** | T3 heavy air, Arcane damage, splash research | Giant stork, sling-thrown firepots that leave burning ground; **Long Flights** speed research |
| Air disabler (extra slot) | **Netcaster** (ground special) | Grounds enemy flyers | **Smoke Pall** blinds towers instead of disabling them; a biped stork-catcher instead of a third air unit (cheaper to produce) |

### 5.2 Production table

| id | Unit | Built at | Requires | Gold | Lumber | Food | Time (s) | Level (XP) | Slice |
|---|---|---|---|---|---|---|---|---|---|
| `kingdom_hodman` | Hodman | Moot Hall (any tier) | — | 70 | 0 | 1 | 15 | 1 | **[SLICE]** |
| `kingdom_flail_levy` | Flail Levy | (Hodman transform) | — | — | — | (1) | 1.5 | 1 | **[SLICE]** |
| `kingdom_pavisier` | Pavisier | Drill Yard | — | 140 | 0 | 2 | 21 | 2 | **[SLICE]** |
| `kingdom_hookgunner` | Hookgunner | Drill Yard | Foundry | 200 | 30 | 3 | 27 | 3 | **[SLICE]** |
| `kingdom_ironrider` | Ironrider | Drill Yard | Crown Burg, Foundry | 250 | 70 | 4 | 40 | 4 | *later* |
| `kingdom_linden_sister` | Linden Sister | Collegium | — | 125 | 20 | 2 | 26 | 2 | **[SLICE]** |
| `kingdom_lacewright` | Lacewright | Collegium | — | 150 | 25 | 2 | 32 | 2 | *later* |
| `kingdom_assayer` | Assayer | Collegium | — | 200 | 40 | 3 | 30 | 3 | *later* |
| `kingdom_bombard_wagon` | Bombard Wagon | Wainwright Yard | — | 190 | 60 | 3 | 34 | 3 | **[SLICE]** |
| `kingdom_wall_wagon` | Wall Wagon | Wainwright Yard | Crown Burg | 260 | 80 | 4 | 46 | 4 | *later* |
| `kingdom_brass_kestrel` | Brass Kestrel | Wainwright Yard | — | 100 | 25 | 1 | 20 | 1 | *later* |
| `kingdom_netcaster` | Netcaster | Stork Loft | — | 160 | 40 | 2 | 26 | 2 | *later* |
| `kingdom_stork_rider` | Stork Rider | Stork Loft | Crown Burg | 300 | 60 | 4 | 46 | 4 | *later* |

The Collegium, Wainwright Yard and Stork Loft themselves need the Walled Burg (§7), so every unit from them is tier 2 or later.

### 5.3 Combat stats

Sight is day / night in metres. Radius is the collision radius in metres.

| Unit | Flags (rules.md §10.7) | HP | Mana | Armour | Attack | Damage | Cooldown (s) | Range (m) | Targets | Speed (m/s) | Sight (m) | Radius |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hodman | ground, organic, worker | 230 | — | 0 Medium | Blade | 5–7 | 2.0 | 0.6 | G | 3.0 | 12.5 / 9.4 | 0.35 |
| Flail Levy | ground, organic, worker | 330 (+100, current HP scaled) | — | 3 Medium | Blade | 10–13 | 1.35 | 0.8 | G | 3.6 | 18.0 / 11.0 | 0.35 |
| Pavisier | ground, organic | 440 | — | 2 Heavy | Blade | 12–14 | 1.35 | 0.8 | G | 4.1 | 21.9 / 12.5 | 0.45 |
| Hookgunner | ground, organic | 520 | — | 0 Medium | Pierce | 22–28 | 1.7 | 7.0 (9.0) | G+A | 4.1 | 21.9 / 12.5 | 0.45 |
| Ironrider | ground, organic | 860 | — | 5 Heavy | Blade | 30–36 | 1.45 | 0.9 | G | 5.5 | 21.9 / 12.5 | 0.7 |
| Linden Sister | ground, organic | 300 | 180 | 0 Unarmored | Arcane | 8–10 | 1.8 | 6.0 | G+A | 4.2 | 21.9 / 12.5 | 0.4 |
| Lacewright | ground, organic | 330 | 250 | 0 Unarmored | Arcane | 10–12 | 1.75 | 6.25 | G+A | 4.2 | 21.9 / 12.5 | 0.4 |
| Assayer | ground, organic, spell_immune | 560 | 220 | 2 Medium | Blade | 15–19 | 1.6 | 0.8 | G | 4.1 | 21.9 / 12.5 | 0.45 |
| Bombard Wagon | ground, **mechanical** (repairable, not healable) | 420 | — | 1 Heavy | Siege | 52–64, splash | 3.4 | 15.5 (minimum 3.5) | G | 3.4 | 21.9 / 12.5 | 0.8 |
| Wall Wagon (rolling) | ground, **mechanical** | 1050 | — | 3 Heavy | Siege | 46–54 | 2.2 | 1.0 | Buildings and mechanical units | 3.1 | 18.0 / 12.5 | 1.0 |
| Wall Wagon (Fort) | ground, **mechanical** (a unit form, not a structure) | 1050 | — | 6 Fortified | Pierce | 18–22 | 1.3 | 9.4 | G+A | 0 | 21.9 / 14.0 | (blocks 6×4 cells) |
| Brass Kestrel | **air, mechanical** | 280 | — | 1 Light | Pierce | 11–13 | 1.3 | 5.5 | Air only | 6.25 | 23.4 / 15.6 | 0.5 |
| Netcaster | ground, organic | 420 | 180 | 1 Medium | Pierce | 13–16 (+50 % vs air) | 1.6 | 6.0 | G+A | 4.4 | 21.9 / 12.5 | 0.4 |
| Stork Rider | air, organic | 800 | — | 1 Light | Arcane | 42–50 | 2.1 | 4.5 | G+A | 5.6 (6.35 with Long Flights) | 21.9 / 15.6 | 0.8 |

Summons from hero abilities: **Clockwork Halberdier** = summoned, mechanical, ground. **Grand Bombard** = summoned, mechanical, ground,
immobile; it is **not** a structure (it does not count for defeat, cannot be built on, and is repairable).

- **Casters:**
  - Mana regenerates at the global **0.65/s** (rules.md §9). Netcaster: 0.6/s.
  - Casters start with the global **75** mana (`rules.regen.start_mana`); no kingdom override.
- **Splash:** Bombard Wagon splash is full damage within 1.25 m, half within 2.5 m and a quarter within 3.5 m. There is no friendly fire.
- **Damage points and backswings:** the global defaults (0.3–0.5 s).
- **Ranged projectile speeds:**

  | Attack | Speed (m/s) | Arc |
  |---|---|---|
  | Bullet (Hookgunner) | 30 | — |
  | Bombard ball | 12 | High arc |
  | Firepot (Stork Rider) | 14 | — |

**Damage sanity check against the global matrix:**

| Unit | DPS | Note |
|---|---|---|
| Pavisier | ≈ 9.6 | Blade |
| Hookgunner | ≈ 14.7 Pierce | +15 % braced |
| Ironrider | ≈ 22.8 | |

Fights between equal armies should last 10–30 s (mechanics §7.4).

### 5.4 Unit abilities

Autocast toggles with a right-click (global rule). "Research" names the upgrade that unlocks an ability (§8).

**Hodman / Flail Levy [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Gather / Build / Repair | Commands | Repair: autocast, default **off**. Building with extra Hodmen uses the Hod Chain. See §4 |
| Take Up the Flail | Instant, self | **Only within 22 m of a finished friendly hall** (greyed otherwise: "Too far from a hall"). Becomes a Flail Levy for 40 s after 1.5 s of arming. 20 s lockout after standing down |
| Stand Down (as Levy) | Instant | Back to Hodman, resumes the last order |
| Levy leash | Passive (Levy) | More than 30 m from every friendly hall: stands down after 5 s |
| (Hall) Levy Horn | No target | All Hodmen within 22 m of the hall arm (a Hodman inside the mine arms as it exits). Cooldown 60 s. No cost |
| (Hall) Stand Down (all) | No target | Every Flail Levy of the player stands down. No cooldown |

**Pavisier [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Plant Pavise (research **Pavise Drill**) | Toggle, 0.75 s to switch | While on: **−45 % Pierce** damage taken (Siege unchanged), +2 armour, move speed −40 %. **Cover:** allied units within 2 m behind the Pavisier take −20 % Pierce damage (does not stack). AI default: on when ranged enemies are in 12 m |

**Hookgunner [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Braced Shot | Passive | After 2 s without moving, attacks deal +15 % damage. A forked rest is planted (visual) |
| Drawn Barrels (research) | Passive | Range 7.0 → 9.0 m |

**Ironrider** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Couched Lance (research) | Passive | After 3 s of continuous movement without attacking, the next attack deals **+100 %** damage and knocks a non-hero ground target back 1.5 m. A pennon flutters when the lance is ready |
| Heavy Remounts (research) | Passive | Ironrider only: +100 max HP and +1 armour |

**Linden Sister [SLICE]** (Journeyman and Master training each add +35 HP, +60 max mana and +1 damage)

| Ability | Rank | Mana | Cooldown | Range | Effect |
|---|---|---|---|---|---|
| Herb Poultice (autocast **on**) | Novice | 6 | 1.0 s | 5 m | Heals a damaged allied non-mechanical unit for 30 HP |
| Smoke of Rue **[SLICE]** | Journeyman | 70 | 2 s | 8 m | Area 3 m radius: removes every **dispellable** buff (friend and foe; rules.md §10.4) and deals 250 damage to summoned units |
| Linden Wreath (autocast, default off) | Master | 50 | 1 s | 7 m | An ally gains 25 % Spell damage resistance and +1.5 HP/s for 60 s. Dispellable |

**Lacewright** *(later)* (same training bonuses as the Linden Sister)

| Ability | Rank | Mana | Cooldown | Range | Effect |
|---|---|---|---|---|---|
| Tangle Thread (autocast **on**) | Novice | 45 | 1 s | 7 m | Enemy: −50 % move speed, −20 % attack speed for 25 s (heroes 8 s). Dispellable |
| Muslin Veil | Journeyman | 70 | 1 s | 7 m | An ally becomes invisible for 90 s. Attacking or casting breaks it |
| Lace Cocoon | Master | 160 | 45 s | 8 m | **On an enemy** non-hero up to level 6: cannot move, attack or cast for 12 s, and takes −50 % damage. **On an ally:** it cannot act for 6 s but takes −75 % damage (a rescue tool) |

**Assayer** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Silver-Shod | Passive | `spell_immune` (rules.md §7.2, §10.5): immune to spells, both hostile and friendly (it cannot be healed by the Linden Sister). Only abilities flagged `pierces_immunity` still affect it |
| Salt Strike | Passive | Each attack burns 10 mana from the target and deals the burned amount as bonus Spell damage. +40 bonus damage against summoned units |
| Silver Seal (research) | Point, 7 m | Area 3 m radius: enemy units are **silenced** (no spells, no autocasts) for 5 s (heroes 3 s). 75 mana, cooldown 20 s |

**Bombard Wagon [SLICE]** (two crew push a two-wheeled cart; crew and wheels are procedural)

| Ability | Type | Numbers |
|---|---|---|
| Deploy / Pack | Automatic | Must stand still for 0.5 s before the first shot (crew brace the wheels) |
| Signal Shell (research **Signal Shells**) **[SLICE]** | Point, 30 m | Reveals an area of 8 m radius for 12 s, including invisible units (`reveal_invisible_area`). Cooldown 40 s, no mana |
| Case Shot (research) **[SLICE]** | Passive | Enemies hit by the splash are slowed: −25 % move speed for 3 s (heroes 1.5 s). Refreshes, does not stack. Physical debuff, not dispellable. No damage bonus |

**Wall Wagon** *(later)*: the **Wagon Fort**, an original signature mechanic

| Ability | Type | Numbers |
|---|---|---|
| Iron Prow Ram | Attack (rolling) | Siege 46–54, cooldown 2.2 s, range 1 m. Targets only buildings and mechanical units |
| Wagon Fort | Toggle: 3 s to deploy, 2 s to pack | Deployed: immobile; armour type becomes **Fortified** with +3 armour; blocks a 6×4-cell rectangle snapped to the nearest 90° facing; gains **Loophole Volley** (Pierce 18–22, cooldown 1.3 s, range 9.4 m, G+A). The ram is unavailable while deployed |
| Wagon Chains (research) | Passive | Deployed wagons within 3.5 m of each other link automatically with an iron chain that blocks pathing between them. Each link gives both wagons +2 armour (at most 2 links per wagon) |
| Repairable | — | Hodmen can repair it (mechanical) |

**Brass Kestrel** *(later)* (clockwork; repairable; flying units ignore occluders)

| Ability | Type | Numbers |
|---|---|---|
| Keen Lenses | Passive | True sight 14 m |
| Spring Coils (research) | Passive | Air attacks splash 50 % within 1.5 m |
| Hunting Stoop (research) | Unit target (ground), 6 m; autocast default on | Once every **20 s**, the Kestrel dives on one enemy ground unit (not a building) for **40 Siege** damage and **reveals** it for **6 s** (it stays visible, and an invisible target is shown, wherever it goes). The Kestrel has **no** permanent ground attack |

**Netcaster** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Stork-Catcher | Passive | +50 % damage against air units |
| Weighted Net | Unit, 8 m | An enemy **air** unit is **grounded** (rules.md §12.3) for 8 s (heroes 4 s): it counts as a ground unit (melee can hit it, roots can hold it) and moves at 50 % speed on ground pathing. It cannot attack while netted. Dispellable. 60 mana, cooldown 12 s |
| Smoke Pall (research **Smoke Pall**) | Point, 9 m | A 4 m radius smoke cloud for **20 s**. It **blocks sight into it**: enemies outside cannot see units inside. Enemy towers inside see only **2 m** (they still attack whatever they can see). 80 mana, cooldown 30 s |

**Stork Rider** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Pitch Firepots (research) | Passive | Sling-thrown firepots splash 50 % within 2 m and leave burning ground (2 m radius, 4 s, 8 Spell damage per second, ignores armour value) |
| Long Flights (research) | Passive | +0.75 m/s move speed (5.6 → 6.35) |

---

## 6. Heroes

### 6.1 Common rules (global, rules.md §6)

- **Recruitment:** 425 gold / 100 lumber (the first hero is free), 5 food, 55 s, trained at the **Oath Hall**. One of each type; at most 3.
- **Abilities:** 3 abilities × 3 ranks (learned at levels 1/3/5) plus an ultimate at level 6.
- **Attack and armour:** Heroic attack, Hero armour, 30 % spell resistance, 6 item slots.
- **Attribute formulas:**
  - STR: HP = 100 + 25 × STR; +0.05 HP/s per point (base regeneration 0.25 HP/s).
  - AGI: armour = base + 0.3 × AGI; attack cooldown = base ÷ (1 + 0.02 × AGI).
  - INT: mana = 15 × INT; +0.05 mana/s per point.
  - Primary attribute: +1 damage per point.
  - Attributes grow fractionally and are floored for display.
- **Sight:** 28.1 / 12.5 m. Collision radius 0.55 m.
- **Names:** each hero gets a random proper name from its list, shown as "Title: Name".
- **Hotkeys (Classic preset, rules.md §18.4):** the four abilities are **Q / W / E / R** in the order of each kit table below (the ultimate is
  always R); Learn is O.
- **Ability damage defaults:** all ability damage is **Spell** damage, which ignores the armour value (rules.md §7.3). Damage-over-time
  effects and marks are magic buffs, **dispellable: yes**, unless a row says otherwise.

### 6.2 Attributes and growth

| Hero | id | Primary | STR (+/lvl) | AGI (+/lvl) | INT (+/lvl) | Base damage (+primary) | Base armour | Base cooldown | Range (m) | Targets | Speed (m/s) | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wheel Marshal | `kingdom_wheel_marshal` | STR | 23 (+2.6) | 12 (+1.4) | 16 (+1.7) | 1–7 | 1 | 2.2 | 1.0 (melee) | G | 4.5 | **[SLICE]** |
| Orrery Sage | `kingdom_orrery_sage` | INT | 15 (+1.6) | 14 (+1.0) | 20 (+3.1) | 2–8 | −1 | 2.1 | 7.8 (missile) | G+A | 4.4 | *later* |
| Flail Hetman | `kingdom_flail_hetman` | STR | 24 (+2.5) | 17 (+1.8) | 13 (+1.3) | 1–9 | 0 | 2.0 | 1.1 (melee) | G | 4.6 | *later* |
| Firewright | `kingdom_firewright` | INT | 16 (+1.8) | 12 (+1.0) | 21 (+3.0) | 3–9 | −1 | 2.2 | 7.0 (missile) | G+A | 4.4 | **[SLICE]** |

Derived values (HP / mana / armour / damage / cooldown):

| Hero | Level 1 | Level 5 | Level 10 |
|---|---|---|---|
| Wheel Marshal | 675 / 240 / 4.6 / 24–30 / 1.77 s | 925 / 330 / 6.1 / 34–40 / 1.64 s | 1250 / 465 / 8.2 / 47–53 / 1.49 s |
| Orrery Sage | 475 / 300 / 3.2 / 22–28 / 1.64 s | 625 / 480 / 4.4 / 34–40 / 1.54 s | 825 / 705 / 5.9 / 49–55 / 1.44 s |
| Flail Hetman | 700 / 195 / 5.1 / 25–33 / 1.49 s | 950 / 270 / 7.2 / 35–43 / 1.35 s | 1250 / 360 / 9.9 / 47–55 / 1.20 s |
| Firewright | 500 / 315 / 2.6 / 24–30 / 1.77 s | 675 / 495 / 3.8 / 36–42 / 1.67 s | 900 / 720 / 5.3 / 51–57 / 1.55 s |

### 6.3 Kits

#### Wheel Marshal (STR tank and support) [SLICE]

- **Look:** a broad, tall woman in blackened Gothic plate with an ivory surcoat. She carries a **wheel-shield** (a cart wheel planked between
  the spokes, with a bronze hub boss in team-colour enamel) and a long-hafted **war-pick**. Her sallet has a kettle brim and a burgundy plume.
- **Proper names:** Dame Hedvika Spokewright · Dame Zdenka Ironrim · Dame Bertha Wainsworth.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Linden Balm** (Q; allied unit target, **not herself**) | 1 / 2 / 3 | 70 | 7 s | 8 m | Heals the allied target for **190 / 360 / 530**. Other allies within 2.5 m of the target heal 25 % of that (the Marshal included if she stands there). Does not work on mechanical units. VFX: drifting linden blossoms. Icon: a linden sprig over a wheel hub (never a glowing hand or a light pillar) |
| **Brace the Wheel** (W; no target) | 1 / 2 / 3 | 60 | 15 s | 4 / 5 / 6 m | Taunts enemy **non-hero** units in the radius to attack her for 2 / 3 / 4 s. She gains +4 / +6 / +8 armour for 6 s. VFX: she grounds the wheel-shield and a **wheel-rim shockwave** (an ivory ring with spoke ticks) rolls out to the radius; no red shout, no roar |
| **Measured Cadence** (E; aura) | 1 / 2 / 3 | — | — | 9 m | Allied units gain **+6 / +10 / +14 % attack speed**. VFX: a faint drum-beat pulse ring under her every 1.5 s. Regeneration is left to the Linden Sister |
| **The Wagon Ring** (R; ultimate, no target) | — | 175 | 160 s | 11 m | A ghostly ring of wagon wheels rises around her. For **7 s**, allied non-structure units in the ring when cast **cannot drop below 1 HP**. When it ends, each affected unit restores 15 % of its max HP. Not dispellable (ultimate) |

#### Orrery Sage (INT caster, the "court magus" role) *(later)*

- **Look:** a middle-aged woman astronomer in an ivory coat with burgundy lining and spectacles. **Brass armillary rings** stand on a
  back-frame above her head, and she carries a telescope staff.
- **Proper names:** Horologer Vendula Starwright · Horologer Ilse Meridian · Horologer Johanka Lensgrind.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Burning Lens** (Q; line toward a point) | 1 / 2 / 3 | 85 | 8 s | Line 12 m × 1.5 m | **75 / 125 / 175** Spell damage to enemies in the line. Struck enemies are **Marked** for 5 s and take +12 % damage from all sources (dispellable) |
| **Clockwork Halberdier** (W; summon) | 1 / 2 / 3 | 110 | 24 s | Spawns within 3 m | One automaton for **45 s** (melee, Heavy armour; summoned, mechanical). Ranks: HP **480 / 680 / 880**; armour 2 / 3 / 4; Blade 16–20 / 25–31 / 35–41; cooldown 1.5 s; speed 4.0 m/s; level 2 / 3 / 4. Rank 3: on death it bursts for 60 Spell damage within 2 m |
| **Lucid Hours** (E; aura) | 1 / 2 / 3 | — | — | 9 m | Allies gain +0.6 / +1.2 / +1.8 mana/s |
| **Hour Rewound** (R; ultimate, no target) | — | 200 | 150 s | 10 m | Marks the Sage and allied non-structure units in range (summons included) and snapshots each one's HP. After **8 s**, or when she recasts it, each marked unit still alive **regains 60 % of the HP it lost since the mark**, and its **current ability cooldowns are halved**. **Nobody moves.** It does not resurrect. Not dispellable (ultimate). VFX: a translucent clock dial over each marked unit whose hand sweeps back |

#### Flail Hetman (STR/AGI melee stunner) *(later)*

- **Look:** a towering ex-thresher in a quilted burgundy jack, iron gorget and wide kettle hat. He carries a giant **three-club
  war-flail** (iron-shod clubs on chains) over his shoulder.
- **Proper names:** Hetman Radek Ironchaff · Hetman Bora Sheafbreaker · Hetman Jarmil Wagonwall.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Hurled Chain** (Q; unit target) | 1 / 2 / 3 | 80 | 10 s | 8 m | A weighted chain deals **95 / 175 / 255** Spell damage and **stuns** for 2 / 2.5 / 3 s (heroes 1 / 1.25 / 1.5 s) |
| **Threshing Sweep** (W; frontal cone) | 1 / 2 / 3 | 85 | 11 s | 5 m, 90° cone | **70 / 115 / 160** Spell damage, **knockback 2 m**, and −2 / −3 / −4 armour for 8 s (dispellable) |
| **Chaff and Grain** (E; passive) | 1 / 2 / 3 | — | — | 1.5 m arc | Attacks splash 25 / 35 / 45 % damage to enemies around and behind the target. Every 3rd attack on the same target also slows its attack speed by 30 % for 2 s |
| **Wagon-Breaker Charge** (R; ultimate, point) | — | 140 | 120 s | Up to 16 m | Charges at 12 m/s and is immune to stuns and slows while charging. Enemies in a 2 m-wide path take **150** Spell damage, are pushed aside and **stunned 1.5 s** (heroes 0.75 s). Buildings in the path take 300. On arrival: +40 % attack speed and +1.5 m/s move speed for 10 s |

#### Firewright (INT fire caster) [SLICE]

- **Look:** a stocky, soot-faced man with no eyebrows, a leather apron over an ivory shirt, a **tall felt chimney-hat** with a bronze smoke cap,
  a bandolier of clay flasks, and a linstock staff with a smouldering match-cord.
- **Proper names:** Firewright Kunrat Pitchley · Firewright Vit Sootwick · Firewright Matej Saltpetre.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Naphtha Flask** (Q; point) | 1 / 2 / 3 | 95 | 9 s | 10 m, radius 3 m | Impact **55 / 90 / 125** Spell damage, then the ground burns for 6 s at **12 / 20 / 28** damage per second (a ground effect: Spell damage, ignores armour value; not a buff, so it cannot be dispelled; leaving the area ends it). Buildings take 50 % |
| **Fuse Mark** (W; **enemy** unit or building) | 1 / 2 / 3 | 80 | 11 s | 8 m | Lights a fuse on the target. After **4 s** it explodes for **80 / 140 / 200** Spell damage to the target and 50 % to enemies within 2.5 m. If the target dies first, the fuse explodes at once where it fell. Buildings take ×1.5. The fuse is a magic debuff, **dispellable: yes** (a dispel defuses it with no explosion) |
| **Incendiary Wadding** (E; aura) | 1 / 2 / 3 | — | — | 9 m | Attacks by allied **ranged non-structure units, heroes included** (the Firewright too) set targets alight for **3 / 5 / 7** damage per second for 3 s. The burn is Spell damage (ignores armour value), refreshes, does not stack, **dispellable: yes**; buildings take 50 %. Towers do not apply it |
| **Grand Bombard** (R; ultimate, point within 6 m) | — | 175 | 150 s | Fires up to 17 m (minimum 3 m) | Places a crewed bronze bombard for **25 s**: summoned, mechanical, ground, immobile (**not** a structure), 900 HP, 5 armour Fortified. Fires every 2.4 s at enemy ground units and buildings: Siege **75–85**, splash 1.25 m full / 2.5 m half. Counts as a level-5 summon for XP. Reuses the Bombard Wagon mesh at 1.3× scale |

### 6.4 Kit fidelity audit (policy: at most 2 of 4 abilities may be functional equivalents of the matching WC3 hero's)

| Brennish hero | WC3 role match | Functional equivalents (counted strictly) | Original mechanics | Count |
|---|---|---|---|---|
| Wheel Marshal | Paladin | Linden Balm (targeted heal; like the WC3 heal it cannot target the caster) | Brace the Wheel (taunt plus armour); Measured Cadence (**offensive** attack-speed aura; the WC3 aura is defensive armour); The Wagon Ring (cannot drop below 1 HP, instead of a resurrection) | **1** |
| Orrery Sage | Archmage | Clockwork Halberdier (combat summon, melee instead of ranged); Lucid Hours (mana-regeneration aura) | Burning Lens (instant line nuke plus damage mark, not a channelled area rain); Hour Rewound (a delayed partial **heal-back and cooldown refund in place**; no unit moves, so it is not a group teleport) | **2** |
| Flail Hetman | Mountain King | Hurled Chain (thrown single-target stun); Threshing Sweep (melee area attack: cone and knockback instead of a slowing circle) | Chaff and Grain (cleave plus attack-speed slow, not a stun chance); Wagon-Breaker Charge (line charge, not a self-transform) | **2** |
| Firewright | Blood Mage | Naphtha Flask (fire area damage over time); Grand Bombard (big summon ultimate: stationary artillery instead of a flying firebird) | Fuse Mark (delayed bomb on a unit); Incendiary Wadding (burning-ammo aura for ranged allies) | **2** |

**Slot-pattern check** (ip-safety §2.3 warns against the *combination*, not just the count):

- Wheel Marshal: heal / taunt / **offensive** aura / save-the-team. The WC3 pattern is heal / shield-self / defensive aura / save-the-team; two of four slots differ in purpose.
- Orrery Sage: nuke / summon / mana aura / **in-place recovery**. The WC3 pattern ends in a group teleport; the ultimate's purpose differs (the army stays in the fight).
- Flail Hetman: stun / area slam / cleave / charge. The WC3 pattern has a passive stun chance and a self-transform ultimate.
- Firewright: area DoT / delayed bomb / ally burn aura / artillery summon. The WC3 pattern has a banish and a mana drain.

**Numbers are ours.** No mana cost, cooldown, duration or per-rank value of an ability listed as a functional equivalent matches the WC3
ability it mirrors, and no ability's (mana, cooldown) pair matches any ability of the matching WC3 hero. This is enforced by a data test:

- **`test_no_wc3_number_fingerprints`** (`tests/unit/`). It reads a reference table that lives **only** in `docs/research/`
  (`docs/research/wc3-hero-ability-reference.csv`: our ability id → the WC3 hero and ability it is audited against, with that ability's
  mana, cooldown, duration and per-rank damage / heal / summon HP). It loads our values from `data/` and **fails** on:
  1. any exact match of mana, cooldown or duration between a functional equivalent and its WC3 counterpart;
  2. any per-rank damage, heal or summon-HP value equal at the same rank for a functional equivalent;
  3. any (mana, cooldown) pair of any of our hero abilities equal to that of any ability of the matching WC3 hero.
- The test file contains **no** WC3 names (the banned-term checker scans `tests/`); all names stay in the docs-only CSV. New hero kits
  must add their rows before data entry.

Every name, VFX, number and visual is ours. No hero reproduces the expressive *combination* of a WC3 kit (ip-safety §2.3).

---

## 7. Buildings and tech tree

### 7.1 Tech tree

```
Moot Hall (T1) ──upgrade──► Walled Burg (T2, needs Oath Hall) ──upgrade──► Crown Burg (T3, needs Oath Hall + Foundry)
│                               │                               │
├─ Croft (+7 food)              ├─ Collegium ── Linden Sister, Lacewright, Assayer
├─ Oath Hall ── heroes          │                (Journeyman training at T2, Master at T3)
├─ Drill Yard ── Pavisier       ├─ Wainwright Yard [needs Foundry]
│              ├ Hookgunner [needs Foundry]       ── Bombard Wagon, Brass Kestrel
│              └ Ironrider  [needs Crown Burg + Foundry]  └ Wall Wagon [needs Crown Burg]
├─ Timber Yard ── Lookout ─┬─ Gun Tower         ├─ Stork Loft [needs Timber Yard]
│                          ├─ Bombard Rondel [needs Wainwright Yard]   ── Netcaster
│                          └─ Silver Spire   [needs Collegium]          └ Stork Rider [needs Crown Burg]
├─ Foundry ── weapon / armour / powder upgrades (level 2 needs T2, level 3 needs T3)
└─ Curio Cabinet ── items (stock grows with hall tier)
```

**Slice tree:** the Stork Loft and T3 are cut. Everything else above is in the slice, with these limits: the Timber Yard offers only
Lime Mortar; the Collegium trains only the Linden Sister (Novice, plus Journeyman Papers); the Wainwright Yard builds only the Bombard
Wagon; the Lookout upgrades only to the Gun Tower. **The Lookout requires the Timber Yard**, so no tower exists before a Timber Yard.

### 7.2 Building table

All buildings have **Fortified** armour 5 (scout towers 2; rules.md §8) and 14 m sight (towers excepted). Footprints are in 0.5 m cells
(`architecture.md`: hall 10×10, barracks 8×8, farm 4×4, tower 4×4).

| id | Building | Role | Requires | Gold | Lumber | Time (s) | HP | Armour | Footprint | Food | Function | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `kingdom_moot_hall` | Moot Hall | Main hall, T1 | — | 400 | 200 | 170 | 1550 | 5 | 10×10 | +12 | Trains Hodmen; **Levy Horn**; **Stand Down (all)**; gold and lumber drop-off | **[SLICE]** |
| `kingdom_walled_burg` | Walled Burg | Main hall, T2 (upgrade) | Moot Hall, **Oath Hall** | +310 | +200 | 130 | 2050 | 5 | 10×10 | +14 | Unlocks tier 2 and hero 2 | **[SLICE]** |
| `kingdom_crown_burg` | Crown Burg | Main hall, T3 (upgrade) | Walled Burg, Oath Hall, Foundry | +350 | +220 | 140 | 2600 | 6 | 10×10 | +16 | Unlocks tier 3 and hero 3 | *later* |
| `kingdom_croft` | Croft | Supply | — | 95 | 20 | 38 | 500 | 5 | 4×4 | +7 | Food | **[SLICE]** |
| `kingdom_oath_hall` | Oath Hall | Hero altar | — | 175 | 45 | 60 | 900 | 5 | 6×6 | — | Trains and revives heroes. Heroes swear on an iron wheel set in the floor | **[SLICE]** |
| `kingdom_drill_yard` | Drill Yard | Barracks | — | 160 | 55 | 60 | 1350 | 5 | 8×8 | — | Pavisier, Hookgunner, Ironrider; their research | **[SLICE]** |
| `kingdom_timber_yard` | Timber Yard | Lumber drop-off and masonry | — | 125 | 0 | 55 | 1000 | 5 | 8×8 | — | **Lumber drop-off**; masonry and lumber research; **enables towers**. Build it at the tree line | **[SLICE]** (Lime Mortar only) |
| `kingdom_foundry` | Foundry | Weapons and armour smithy | — | 150 | 50 | 65 | 1200 | 5 | 6×6 | — | Weapon, powder and armour lines | **[SLICE]** |
| `kingdom_collegium` | Collegium | Caster hall | Walled Burg | 160 | 120 | 65 | 1050 | 5 | 8×8 | — | Casters; Journeyman and Master training | **[SLICE]** (Linden Sister only) |
| `kingdom_wainwright_yard` | Wainwright Yard | Siege workshop | Walled Burg, Foundry | 140 | 130 | 60 | 1200 | 5 | 8×8 | — | Bombard Wagon, Brass Kestrel, Wall Wagon | **[SLICE]** |
| `kingdom_stork_loft` | Stork Loft | Air roost | Walled Burg, Timber Yard | 150 | 140 | 60 | 1150 | 5 | 8×8 | — | Netcaster, Stork Rider. Visual: a tall timber tower crowned with a huge stork nest | *later* |
| `kingdom_curio_cabinet` | Curio Cabinet | Faction shop | — | 130 | 30 | 60 | 480 | 5 | 6×6 | — | Sells items (§7.4) | **[SLICE]** |
| `kingdom_lookout` | Lookout | Scout tower | **Timber Yard** | 35 | 20 | 25 | 320 | 2 | 4×4 | — | Sight 25 / 18 m; no attack | **[SLICE]** |
| `kingdom_gun_tower` | Gun Tower | Gun tower | Lookout | +75 | +45 | 35 | 520 | 5 | 4×4 | — | See §7.3 | **[SLICE]** |
| `kingdom_bombard_rondel` | Bombard Rondel | Cannon tower | Lookout, Wainwright Yard | +100 | +100 | 40 | 520 | 5 | 4×4 | — | See §7.3 | *later* |
| `kingdom_silver_spire` | Silver Spire | Anti-magic tower | Lookout, Collegium | +80 | +90 | 40 | 520 | 5 | 4×4 | — | See §7.3 | *later* |

Notes:

- Hall upgrades keep the footprint. Food from the hall replaces, not adds: 12 → 14 → 16.
- The architecture contract (10-cell hall, 5 m) governs until the slice playtest. The visual doc's 8 m hall proposal is an open question (§13).
- The Croft uses the global structure armour 5 ("Crofts are sturdy" comes from their 500 HP and the Lime Mortar research, not an override).

### 7.3 Towers (upgrade paths are exclusive: a Lookout becomes one of three)

| Tower | Attack | Damage | Cooldown (s) | Range (m) | Targets | Special |
|---|---|---|---|---|---|---|
| Lookout | — | — | — | — | — | Sight 25 / 18 m; cheap scouting post |
| Gun Tower | Pierce | 21–25 | 1.0 | 10.9 | G+A | Two crew with hook-guns behind a parapet |
| Bombard Rondel | Siege | 70–86, splash 1.25 m full / 2.5 m half | 2.6 | 12.5 (minimum 2) | G | A squat round stone **rondel** (a drum-shaped artillery tower) with a bronze barrel in an embrasure |
| Silver Spire | Arcane | 13–15 | 1.6 | 10.0 | G+A | **Each hit interrupts channelling** and adds **+1 s** to every ability cooldown the target currently has running (abilities that are ready are unaffected). True sight 9.4 m. Visual: a slim tower with a silver weighing-scale finial |

### 7.4 Curio Cabinet items (faction shop; the first hero's free item is the Homeward Horn)

| Item | Hall tier | Cost | Stock / restock | Effect | Slice |
|---|---|---|---|---|---|
| Homeward Horn | T1 | 300 g | 2 / 90 s | Blow it for 3 s (rules.md §6.8 channel), then the hero and **up to 11 of your own units within 6 m** teleport next to the nearest own finished hall | **[SLICE]** |
| Linden Salve | T1 | 140 g | 3 / 60 s | +250 HP | **[SLICE]** |
| Sage's Tincture | T1 | 120 g | 3 / 60 s | +150 mana | **[SLICE]** |
| Tin Watchman | T1 | 60 g | 3 / 45 s | Places a tiny clockwork ward: 10 m vision for 180 s | **[SLICE]** |
| Chalk of Seeing | T2 | 75 g | 2 / 60 s | Reveals invisible units within 9 m for 15 s (`reveal_invisible_area`) | **[SLICE]** |
| Folding Pavise | T2 | 100 g | 2 / 90 s | Unfolds a 3 m wooden barricade (6×1 cells, 300 HP) for 30 s. Blocks pathing | *later* |
| Lookout in a Crate | T3 | 150 g | 1 / 120 s | Unfolds a finished Lookout at a point within 6 m in 5 s (obeys normal placement rules) | *later* |

Slice cost: the Curio Cabinet uses the bpy half-timber kit (≈ 0 credits); 5 item icons ≈ 1.25 credits.

### 7.5 Command cards and hotkeys (Classic preset; rules.md §18.4)

Letters are unique per card (`Defs` validates this). Unit cards always carry Move **M**, Stop **S**, Hold **H**, Attack **A**, Patrol **P**;
heroes add Learn **O** and abilities **Q / W / E / R** (§6.1). Production buildings carry Rally **R**.

| Card | Buttons (letter) |
|---|---|
| Hodman | Gather **G**, Return Cargo **C**, Repair **R** (autocast toggle by right-click), **Build Basic B**, **Build Advanced V**, Take Up the Flail **F** |
| Build Basic (B) | Moot Hall **H**, Croft **C**, Oath Hall **O**, Drill Yard **D**, Timber Yard **T**, Foundry **F**, Lookout **L**; Esc back |
| Build Advanced (V) | Collegium **G**, Wainwright Yard **W**, Stork Loft **S**, Curio Cabinet **U**; Esc back |
| Flail Levy | Stand Down **D** |
| Moot Hall / Walled Burg / Crown Burg | Hodman **H**, Levy Horn **L**, Stand Down (all) **D**, Upgrade to the next tier **U**, Rally **R** |
| Oath Hall | Wheel Marshal **M**, Orrery Sage **O**, Flail Hetman **H**, Firewright **F** (a dead hero's button becomes Revive in place), Rally **R** |
| Drill Yard | Pavisier **P**, Hookgunner **G**, Ironrider **I**, Pavise Drill **D**, Drawn Barrels **B**, Couched Lance **L**, Heavy Remounts **E**, Rally **R** |
| Timber Yard | Lime Mortar **M**, Bow Saws **S**, Felling Crews **F**, Ashlar Courses **A**, Iron Cramps **I**, Night Watch **N** |
| Foundry | Tempered Blades **T**, Corned Powder **P**, Gothic Plate **G**, Quilted Gambesons **Q** |
| Collegium | Linden Sister **L**, Lacewright **W**, Assayer **A**, Linden Journeyman Papers **J**, Linden Master's Seal **M**, Lacewright Journeyman Papers **U**, Lacewright Master's Seal **E**, Silver Seal **S**, Rally **R** |
| Wainwright Yard | Bombard Wagon **B**, Brass Kestrel **K**, Wall Wagon **W**, Case Shot **C**, Signal Shells **S**, Spring Coils **P**, Hunting Stoop **H**, Wagon Chains **N**, Rally **R** |
| Stork Loft | Netcaster **N**, Stork Rider **S**, Smoke Pall **P**, Pitch Firepots **F**, Long Flights **L**, Rally **R** |
| Lookout | Gun Tower **G**, Bombard Rondel **B**, Silver Spire **S** |
| Curio Cabinet | Homeward Horn **H**, Linden Salve **L**, Sage's Tincture **T**, Tin Watchman **W**, Chalk of Seeing **C**, Folding Pavise **F**, Lookout in a Crate **K** |
| Unit abilities | Pavisier: Plant Pavise **Q**. Bombard Wagon: Attack Ground **G**, Signal Shell **Q**. Wall Wagon: Attack Ground **G**, Wagon Fort **Q**. Linden Sister: Herb Poultice **Q**, Smoke of Rue **W**, Linden Wreath **E**. Lacewright: Tangle Thread **Q**, Muslin Veil **W**, Lace Cocoon **E**. Assayer: Silver Seal **Q**. Netcaster: Weighted Net **Q**, Smoke Pall **W**. Brass Kestrel: Hunting Stoop **Q** |
| Heroes | Wheel Marshal: Linden Balm **Q**, Brace the Wheel **W**, Measured Cadence **E**, The Wagon Ring **R**. Orrery Sage: Burning Lens **Q**, Clockwork Halberdier **W**, Lucid Hours **E**, Hour Rewound **R**. Flail Hetman: Hurled Chain **Q**, Threshing Sweep **W**, Chaff and Grain **E**, Wagon-Breaker Charge **R**. Firewright: Naphtha Flask **Q**, Fuse Mark **W**, Incendiary Wadding **E**, Grand Bombard **R** |

---

## 8. Upgrades

Level-2 research needs the Walled Burg (T2); level-3 research needs the Crown Burg (T3).

**Foundry**

| Line | Level 1 | Level 2 | Level 3 | Effect per level | Affects |
|---|---|---|---|---|---|
| **Tempered Blades** **[SLICE: levels 1–2]** | 110 g / 50 l, 60 s | 175 / 160, 75 s | 245 / 290, 90 s | Each unit's flat `upgrade_damage` (table below) | Blade attacks: Pavisier, Flail Levy, Assayer, Ironrider, Clockwork Halberdier |
| **Corned Powder** **[SLICE: levels 1–2]** | 110 / 60, 60 s | 180 / 170, 75 s | 250 / 300, 90 s | Each unit's flat `upgrade_damage` (table below) | Non-caster ranged and siege: Hookgunner, Bombard Wagon, Wall Wagon (both attacks), Brass Kestrel, Netcaster, Stork Rider |
| **Gothic Plate** **[SLICE: levels 1–2]** | 120 / 70, 60 s | 160 / 170, 75 s | 190 / 260, 90 s | +2 armour | Heavy units: Pavisier, Ironrider, Bombard Wagon, Wall Wagon |
| **Quilted Gambesons** **[SLICE: levels 1–2]** | 100 / 80, 60 s | 150 / 160, 75 s | 200 / 240, 90 s | +2 armour | Medium and Light units: Hookgunner, Flail Levy, Assayer, Netcaster, Brass Kestrel, Stork Rider |

**Flat `upgrade_damage` per weapon level** (added to both minimum and maximum damage; integers, so no rounding; rules.md §5.4 lets a def
override the 10 % default):

| Unit | Base damage | +per level | Unit | Base damage | +per level |
|---|---|---|---|---|---|
| Pavisier | 12–14 | **+2** | Wall Wagon ram / volley | 46–54 / 18–22 | **+6 / +2** |
| Flail Levy | 10–13 | **+1** | Brass Kestrel | 11–13 | **+1** |
| Hookgunner | 22–28 | **+3** | Netcaster | 13–16 | **+2** |
| Bombard Wagon | 52–64 | **+7** | Stork Rider | 42–50 | **+6** |
| Ironrider | 30–36 | **+4** | Clockwork Halberdier (rank 1 / 2 / 3) | 16–20 / 25–31 / 35–41 | **+2 / +3 / +5** |
| Assayer | 15–19 | **+2** | | | |

**Timber Yard**

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Lime Mortar | T1 | 125 / 25 | 60 s | All buildings: +2 armour, +15 % max HP | **[SLICE]** |
| Bow Saws | T2 | 110 g / 0 l | 60 s | +5 lumber per trip (10 → 15) | *later* |
| Felling Crews | T3, Bow Saws | 210 g / 0 l | 75 s | +5 lumber per trip (15 → 20) | *later* |
| Ashlar Courses | T2, Lime Mortar | 150 / 75 | 70 s | Again +2 armour, +15 % max HP | *later* |
| Iron Cramps | T3, Ashlar Courses | 175 / 125 | 80 s | Again +2 armour, +15 % max HP | *later* |
| Night Watch | T2 | 75 / 75 | 45 s | Kingdom buildings and towers keep day sight at night | *later* |

**Drill Yard**

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Pavise Drill | T1 | 130 / 90 | 40 s | Unlocks Plant Pavise | **[SLICE]** |
| Drawn Barrels | T2 | 80 / 130 | 45 s | Hookgunner range 7.0 → 9.0 m | **[SLICE]** |
| Couched Lance | T3 | 150 / 150 | 60 s | Ironrider charge passive | *later* |
| Heavy Remounts | T3 | 125 / 150 | 50 s | Ironrider only: +100 HP, +1 armour | *later* |

**Collegium** (each caster trade has a Journeyman and a Master rank, like a guild)

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Linden Sister: Journeyman Papers | T2 | 120 / 60 | 60 s | Smoke of Rue; +35 HP, +60 mana, +1 damage | **[SLICE]** |
| Linden Sister: Master's Seal | T3 | 180 / 140 | 75 s | Linden Wreath; +35 HP, +60 mana, +1 damage | *later* |
| Lacewright: Journeyman Papers | T2 | 120 / 60 | 60 s | Muslin Veil; same stat bonus | *later* |
| Lacewright: Master's Seal | T3 | 180 / 140 | 75 s | Lace Cocoon; same stat bonus | *later* |
| Silver Seal | T2 | 80 / 100 | 45 s | Assayer area silence | *later* |

**Wainwright Yard**

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Case Shot | T2 | 125 / 100 | 45 s | Bombard Wagon: splash slows −25 % move speed for 3 s | **[SLICE]** |
| Signal Shells | T2 | 50 / 50 | 30 s | Bombard Wagon: Signal Shell (area reveal, detects invisible) | **[SLICE]** |
| Spring Coils | T2 | 125 / 50 | 45 s | Brass Kestrel: air splash | *later* |
| Hunting Stoop | T3 | 150 / 100 | 45 s | Brass Kestrel: periodic dive and reveal on one ground unit | *later* |
| Wagon Chains | T3 | 150 / 150 | 60 s | Wall Wagon: chain links | *later* |

**Stork Loft** *(later)*

| Upgrade | Requires | Cost | Time | Effect |
|---|---|---|---|---|
| Smoke Pall | T2 | 125 / 150 | 50 s | Netcaster: Smoke Pall (sight-blocking cloud; blinds towers) |
| Pitch Firepots | T3 | 200 / 150 | 60 s | Stork Rider: splash plus burning ground |
| Long Flights | T3 | 100 / 100 | 40 s | Stork Rider: +0.75 m/s move speed |

**Hall:** the Levy Horn needs no research.

---

## 9. The four tiers of play

| Phase | Clock (typical) | What Brennmark does | Power spike | Main risk |
|---|---|---|---|---|
| **0. Opening** (Moot Hall, no army) | 0:00–2:00 | Hodmen to 5 on gold; Oath Hall, Croft and Drill Yard. **Oath Hall done about 1:05; hero 1 out about 2:00** | **Levy Horn**: 5–8 Flail Levies near the hall repel any early rush | Losing mining time if the levy is overused |
| **1. Tier 1** (Moot Hall) | 2:00–5:55 | Pavisiers, then Hookgunners after the Foundry; **Timber Yard at the tree line (about 2:30)**; Curio Cabinet for salves and the recall horn; hero creeps green camps to level 3; level-1 weapons; Lookouts at chokes | Hero level 3 with 4 Pavisiers and 2–3 Hookgunners | Slow army; vulnerable to fast raiders on the woodline (answer: Levy Horn plus a Lookout → Gun Tower) |
| **2. Tier 2** (Walled Burg) | 5:55–12:00 | Hero 2; **Collegium Linden Sisters** (healing; Smoke of Rue strips enemy buffs and kills summons; the full game adds Lacewright slows and Assayers); Bombard Wagons with Signal Shells and Case Shot; Chalk of Seeing against invisible heroes; Brass Kestrel scouting and Netcasters *(later)*; Drawn Barrels; level-2 upgrades; expansion behind a Gun Tower | Firewright plus Hookgunners with Incendiary Wadding behind planted Pavisiers, Linden Sisters healing behind them; Bombard Wagons crack defences | Caster losses to burst; upkeep (stay ≤ 50 food or commit) |
| **3. Tier 3** (Crown Burg) *(later)* | 12:00+ | Hero 3; Ironriders, Stork Riders, Wall Wagon forts; Master casters; level-3 upgrades; ultimates at hero level 6 | The Wagon Ring holds a collapsing line, then Hour Rewound gives back the lost HP and half the cooldowns, so the same army fights the next round; Ironrider Couched Lance flanks; chained Wagon Forts lock a map lane | Heavy gold cost; immobile fort lines can be bypassed |

---

## 10. Recommended opening build order (also the slice AI's script)

Standard "tower-safe hero" opening. Times assume about 2 gold/s per gold worker and the fixed **6.0 m** hall–mine gap (rules.md §3.3),
on Greenvale (neutrals §3.6).

| Time | Food (used / cap) | Action |
|---|---|---|
| 0:00 | 5 / 12 | Moot Hall trains Hodmen continuously until about 14. **Hodman 1 → Oath Hall** (175 / 45). Hodmen 2–5 → gold |
| 0:15 | 6 / 12 | New Hodman → **Croft** (95 / 20), then lumber |
| 0:30 | 7 / 12 | New Hodman → gold (5 on gold = saturated) |
| 0:45 | 8 / 12 | New Hodman → **Drill Yard** (160 / 55), then lumber |
| 0:58 | 9 / 19 | Croft 1 done |
| 1:05 | 14 / 19 | Oath Hall done → **free hero: Wheel Marshal** starts training (55 s; 5 food reserved now). Hodman 1 → lumber |
| 1:10 | 14 / 19 | Croft 2 (done about 1:53) |
| 1:50 | 17 / 26 | Drill Yard done → Pavisiers continuously (gold permitting) |
| 2:00 | 18 / 26 | **Wheel Marshal out.** She and the first Pavisier walk to the nearest green camp (Greenvale: the Charcoal Clamp, 28–35 m) and creep from about 2:10 |
| 2:15 | 19 / 26 | **Foundry** (150 / 50) |
| 2:30 | 20 / 26 | Next Hodman → **Timber Yard** (125 / 0) **at the tree line** (done about 3:25); lumber Hodmen drop off there from then on |
| 2:40 | 22 / 26 | Croft 3 |
| 3:20 | 25 / 33 | Foundry done → Hookgunners mixed in. Corned Powder 1 if the enemy is melee-heavy, Gothic Plate 1 if ranged-heavy |
| 3:45 | 29 / 33 | **Walled Burg** (310 / 200) at about 13 Hodmen (5 gold, 7 lumber, 1 builder). Croft 4 |
| 4:30 | 34 / 40 | **Curio Cabinet** (130 / 30) near the hall. Pavise Drill if the enemy shows ranged units. Croft 5 at about 5:00. Keep creeping; hero aims for level 3 by 5:30 |
| 5:55 | 36 / 49 | Walled Burg done (+2 food) → **hero 2: Firewright** and **Wainwright Yard** (140 / 130). Croft 6. A Lookout at the natural expansion |
| 6:30 | 41 / 49 | **Collegium** (160 / 120); build it at 5:55 beside the Wainwright Yard instead if lumber allows. If Long-Braid has been seen: one **Chalk of Seeing** on the Wheel Marshal |
| 6:45 | 44 / 56 | Lookout → **Gun Tower**. Croft 7 |
| 7:00 | 47 / 56 | **Bombard Wagons** ×2, **Drawn Barrels**, **Signal Shells** (50 / 50) |
| 7:40 | 50 / 63 | Collegium done → **Linden Sisters** ×2. **Journeyman Papers** (Smoke of Rue) if the enemy leans on Wind at Your Back or Hail-Hawks |
| 8:30–9:30 | 54–58 / 63 | Push: 2 heroes (levels 4–5), 4 Pavisiers, 4 Hookgunners, 2 Bombard Wagons, 2 Linden Sisters. Plant pavises against ranged; Signal Shell or Chalk any Dust Veil; siege the expansion. Level-2 Tempered Blades or Corned Powder during the push. Accept the first upkeep step (51+ food) only for a decisive push. The push leaves between 8:30 and 9:30, depending on creep gold |

**Variants:**

- **Levy creep (not used on Greenvale):** at about 2:00, with the hero out, sound the Levy Horn only if a green camp is within **25 m of
  path** from the hall (Levies leash at 30 m from a hall, §4). It costs about 150 gold of mining and gains about one hero level 40 s earlier.
  On Greenvale the nearest green camp is 28–35 m away, so the AI never uses this variant there.
- **Tower expand:** skip the 3rd Croft until 3:00. **Clear the natural's Drystone Fold first** (amber, guard mode: it attacks any building
  started within 12 m; rules.md §15.1) with the hero at level 2 plus 4 Pavisiers at about 4:00–4:30, then build a second Moot Hall at the
  natural plus 2 Lookouts → Gun Towers (the Timber Yard is already up).
- **Slice AI** (rules.md §19, kingdom flavour):
  - Follow the standard order above.
  - Sound the Levy Horn when **≥ 6 enemy combat food is within 20 m of any Hodman that is within 22 m of a hall**; press **Stand Down (all)**
    10 s after none remain.
  - Retreat the hero below 35 % HP.
  - Buy Chalk of Seeing (T2), or fire a Signal Shell, as soon as an invisible enemy hero has been seen.
  - Attack at army food ≥ 40 or when an enemy hero is seen creeping within 31 m.

---

## 11. Vertical slice scope (kingdom vs clans, 1v1 vs AI, one map)

| Category | In the slice | Count |
|---|---|---|
| Worker | Hodman (+ Flail Levy via prop swap: flail and kettle hat; no new model) | 1 |
| Combat units | Pavisier, Hookgunner, **Bombard Wagon** (siege), **Linden Sister** (healer caster: Herb Poultice; Smoke of Rue with Journeyman Papers) | 4 |
| Heroes | **Wheel Marshal** (STR tank/support), **Firewright** (INT fire; the ultimate reuses the Bombard mesh) | 2 |
| Buildings | Moot Hall (→ Walled Burg), Croft, Oath Hall, Drill Yard, **Timber Yard** (lumber drop-off, tower gate), Foundry, **Collegium**, Wainwright Yard, **Curio Cabinet** (faction shop: recall, salves, detection), Lookout (→ Gun Tower) | 10 |
| Research | Foundry 4 lines × 2 levels, Pavise Drill, Drawn Barrels, Case Shot, Signal Shells, Lime Mortar, Linden Journeyman Papers | 14 |
| Items (Curio Cabinet) | Homeward Horn, Linden Salve, Sage's Tincture, Tin Watchman (T1); Chalk of Seeing (T2) | 5 |
| Detection | Signal Shell (Bombard Wagon), Chalk of Seeing (shop, T2), and the neutral Flour Bomb (Weighstall) | 3 sources |
| Hall tiers | T1 and T2 only (2 hero slots) | |

**Asset plan and Higgsfield credit estimate (balance 269.75 cr)**

| Asset | Method | Estimated cost |
|---|---|---|
| Hodman, Pavisier, Hookgunner (bipeds; weapons, hod and pavise as separate props) | Concept image (0.25 cr) → Tripo H3.1 image-to-3D (9 cr) → bpy auto-rig plus shared procedural clips | 3 × 9.25 ≈ 28 cr |
| Wheel Marshal, Firewright (bipeds; wheel-shield, flail-free) | Same; Higgsfield rig plus 1 clip (8 cr) only if the bpy rig fails | 2 × 9.25 (+16) ≈ 19–35 cr |
| Bombard Wagon | Cart, wheels and barrel built procedurally in bpy (lathe plus boxes) with AI 2D textures; crew = Hodman mesh in kettle hats | ≈ 1 cr |
| Linden Sister | Like the bipeds (slice-plan B16 `kingdom.caster`, now **P0**) | ≈ 9.25 cr |
| Moot Hall + Walled Burg | One AI hero building (9 cr); T2 = bpy kitbash (stone plinth, wagon ring, taller dome) | ≈ 10 cr |
| Croft, Oath Hall, Drill Yard, Timber Yard, Foundry, Collegium, Wainwright Yard, Curio Cabinet, Lookout / Gun Tower | **Procedural half-timber kit** in bpy (plaster box, beam trims, tile roof, stepped gable, onion dome, scaffold) with AI-painted textures | ≈ 3 cr |
| Icons (about 45: units, abilities, research, 5 items, new buildings) | Higgsfield images (0.25 cr each) or Krea 2 Medium (9 CU each) | ≈ 11.25 cr or ≈ 405 CU |
| **Total** | | **≈ 80–100 Higgsfield cr** (leaves room for the clans faction and retries) |

Audio: about 162 lines (§3.3) plus about 15 faction SFX through Krea (≈ 70 CU for SFX; TTS cost to be probed).

---

## 12. Distinctness rubric check (ip-safety §3.2; nearest WC3 race: the human kingdom)

| Axis | WC3 human kingdom | Brennmark | Differs? |
|---|---|---|---|
| 1. Silhouette | Closed helms, kite shields, plate pauldrons, steepled stone halls | Kettle-hat discs, tall pavises, flails and hook-guns, wagon boxes, half-timber and onion domes | **Yes** (required) |
| 2. Palette | Blue / white / gold | Burgundy / ivory / dark bronze / blackened iron; no blue, no gold | **Yes** |
| 3. Materials | Polished plate, gold trim, grey stone, blue tile | Lime plaster, dark oak, quilted linen, cast bronze, folk-painted wood, lace, wicker | **Yes** |
| 4. Cultural inspiration | Western high-medieval / Arthurian chivalry | Late-medieval Bohemian guild towns: wagon-forts, early firearms, astronomical clocks, silver mining, linden and storks | **Yes** |
| 5. Signature mechanic | Militia call-up | Levy Horn (the one WC3-derived mechanic, presented differently: arms in place near a hall, per worker, leashed to halls, horn and flag) plus an original Wagon Fort | **Yes** (within policy) |
| 6. Names and voice | Footman/Knight/Priest…, "Yes, milord"-style lines | All names original; deadpan guild humour; advisor "the Reeve" | **Yes** |

**Note on multi-builder sites:** several builders on one site is a genre convention from the *Age of Empires* era and, in this game,
a cross-faction rule (rules.md §4.3: sylvan and deathless allow 2 builders each). The Kingdom re-presents it as the **Hod Chain**
(extra Hodmen carry materials for +40 % rate each at a lumber cost, §4), so it is not counted as a second WC3 signature.

**Result: 6 / 6 axes differ** (the policy needs 4 plus silhouette). The roles stay close to WC3 on purpose (§5.1); every unit kit has at
least one mechanic of its own, and the checks against *Warhammer* and *Age of Empires II* are in §2.6.

---

## 13. Open questions and tuning flags

1. **Hall footprint:** 10×10 cells (architecture contract) or 16×16 (the visual doc's 8 m hall)? Decide after the first
   in-engine scale test. The rest of the building footprints scale with it.
2. **Croft +7 food at 95 gold:** check the 0–3 minute supply timing in playtests. If players get supply-blocked at the hero, use +6 food at 85 gold.
3. **Levy Horn range (now the default):** Take Up the Flail only within 22 m of a finished hall, and a Levy more than 30 m from every
   friendly hall stands down after 5 s (§4). Tune 22 / 30 m and the 5 s grace if playtests show either "levy rushes" or a horn too
   short to defend the woodline.
4. **Braced Shot plus Plant Pavise** may make static Brennish lines too strong against ranged armies. Plant Pavise is now −45 % Pierce
   with **Siege unchanged**, so Sling-Carts and bombards still break a planted line. Tune the Braced bonus (15 %) first; if siege then
   shreds planted Pavisiers, allow at most −25 % Siege.
5. **Hour Rewound** needs an implementation check: store an HP snapshot per marked unit (no position, no mana); at resolution heal
   60 % of `max(0, snapshot_hp − current_hp)` and halve each running cooldown; it must stay deterministic (`test_determinism`).
6. **Netcaster vs a true third flyer:** if playtests miss a third air unit, revisit at full-game scope. The Netcaster was chosen because bipeds are cheap to produce.
7. **Red-team readability** of burgundy units: verify with the first rendered Pavisier at night grading (§2.2 rule).
8. **Clans interaction:** counters and timings in §9 and §10 assume a melee-heavy opponent with beast riders. Re-tune against `clans.md`
   (Long-Braid's Dust Veil, Gustcaller buffs, Sling-Cart range) after the first AI-vs-AI runs.
9. **Line check:** before recording, check every line in §3.2 against the WC3 quote pages (audio §3.2) and the shelved concept doc, so nothing echoes either.
10. **Wheel Marshal sustain (tuning flags):** Linden Balm cannot target the Marshal herself (default). If solo creeping proves too
    punishing, the fallback is a self-heal at 50 %. Measured Cadence replaced the Steady Ranks regeneration aura; if it tests badly, the
    fallback is Steady Ranks at +0.75 / 1.5 / 2.25 HP/s, ×1.5 (not ×2) below 40 % HP.
11. **Case Shot slow** (−25 % for 3 s on every splash victim, near-permanent on a clump at 3.4 s per shot) may be strong against the
    melee-heavy clans. Tune to 2 s first.
12. **Hod Chain cost:** 5 lumber per 10 s per carrier. If power-built towers become a problem, raise it; if nobody uses it, lower it.

---

## Review log (2026-10-16: IP-safety and WC3-fidelity reviews)

Where the two reviews conflicted, IP won and the closest legal alternative was kept. "Superseded" means a duplicate issue whose fix was
replaced by the stronger fix of another issue.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | Hour of Return was a group teleport: 3 of 4 Sage abilities were Archmage equivalents | Renamed **Hour Rewound**: no movement; marked units regain 60 % of HP lost since the mark and halve running cooldowns; no resurrection (§6.3). §6.4 count = 2 (Halberdier, Lucid Hours), slot-pattern check added; §9 Tier 3 and §13 Q5 rewritten |
| 2 | Major | Hero numbers copied WC3 values | Threshing Sweep 70/115/160, 85 mana, 11 s; Hurled Chain 95/175/255, 80 mana, 10 s; Clockwork Halberdier 110 mana, 24 s, 45 s, HP 480/680/880; Naphtha Flask impact 55/90/125. Own sweep: Wagon-Breaker Charge mana 150 → 140 (matched the WC3 transform ultimate's cost); Fuse Mark 75 mana / 10 s → 80 / 11 s (too close to the matching WC3 hero's costs to pass rule 3 safely). Added the `test_no_wc3_number_fingerprints` data test spec with a docs-only reference CSV (§6.4) |
| 3 | Major | Five units copied whole WC3 kits | (a) Scatter Shot → **Case Shot** (splash slows 25 % for 3 s, no damage bonus); (b) Pellet Hopper → **Hunting Stoop** (20 s dive, 40 Siege, 6 s reveal; no ground attack); (c) Soot Pots → **Smoke Pall** (sight-blocking cloud, towers see 2 m, still attack); (d) Silver Spire: no mana burn, no anti-summon bonus; hits interrupt channels and add +1 s to running cooldowns; (e) Heavy Remounts: Ironrider only, +100 HP +1 armour; Stork Rider gets **Long Flights** (+0.75 m/s). §5.1, §5.3, §5.4, §7.3, §8 updated. Also aligned Weighted Net with the grounded rule (rules.md §12.3) |
| 4 | Minor | Reeve food and research lines echoed known advisories | "Every croft's full. No room for more hands." and "The guild has signed it off."; Reeve rules added (§3.2) |
| 5 | Minor | Pop-culture echoes | Pavisier, Wheel Marshal (Ready, Yes) and Hodman lines replaced as proposed; two new Firewright drafts that echoed films/idioms were also cut (§3.3 lint item 4) |
| 6 | Minor | "Poke" in click-spam lines | Tic "counts clicks as billable"; "prod" lines; Marshal "A jostled wheel…"; lint rule: no poke/poked/poking in Annoyed lines (§3.3) |
| 7 | Minor | Hub flame + red team colour = a known military-order look; cog-like crown points; 24 spokes | Flame → round **glowing coal** (dark-bronze disc, ember core, ≤ 20 % of diameter, no `#B07F3E` on the emblem); no lone flame on banners, cloaks, tabards; crown points pointed and tapered; 24-spoke wheels forbidden (§0, §1.2, §2.2) |
| 8 | Minor | "Bombard Tower" (AoE2) and "Scatter Shot" (WoW) | **Bombard Rondel** (`kingdom_bombard_rondel`); **Case Shot**; AoE2 Bohemian terms added to the names-never-to-use list (§1.1) |
| 9 | Minor | "Lenscraft" and "Magistra" | **Lensgrind**; title **Horologer**; no-`-craft` rule added to §1.1 |
| 10 | Minor | No check against the *Warhammer* Empire | Six *Warhammer* rows and an AoE2 row in §2.6; do-nots for slashed sleeves, comet/griffon/warhammer iconography, starry robes, armillary on a wagon or altar, colour/college caster names, "the Moot" (§1.1, §1.2, §2.3, §2.6) |
| 11 | Minor | 3-Hodman multi-building was a second WC3 human signature | Option B: the **Hod Chain** (1 builder + up to 2 carriers at +40 % each, 5 lumber per 10 s each); noted as a cross-faction rule (§4, §12) |
| 12 | Minor | WC3 coinages in data ids and the role column | Data ids `heroic`/`pure` (+ `adamant`); §7.2 column renamed **Role** with generic labels; §5.1 uses generic role slots; `arcane sanctum`, `arcane vault`, `arcane tower`, `gryphon aviary`, `call to arms` added to `tools/ip/banned_terms.txt` (checker passes) |
| 13 | Minor | "holy light" token in a material rule | "…marble or radiant golden glow" (§2.3) |
| 14 | Minor | Unit stat lines within a few % of WC3 | Linden Sister 125/20, 26 s, 180 mana, 1.8 s, training +35 HP/+60 mana; Tangle Thread 45 mana, −20 % attack speed, 8 s on heroes; Lacewright 32 s; Ironrider 40 s; Plant Pavise −45 % Pierce, Pavise Drill 40 s; Assayer 220 mana |
| 15 | Minor | Stork Rider risk understated | Rated **Medium**; stork-only reads and a sling attack from behind the wings required (§2.1, §2.6) |
| 16 | Minor | Marshal kit mirrored the paladin's slot purposes; Brace's presentation | Steady Ranks → **Measured Cadence** (+6/10/14 % attack speed aura); Linden Balm icon/VFX rule; Brace the Wheel gets a wheel-rim shockwave, no red shout (§6.3, §6.4: count now 1) |
| 17 | Major | Timber Yard cut: no tree-line drop-off, no tower gate | `kingdom_timber_yard` **[SLICE]** (drop-off + Lime Mortar only); Lookout requires Timber Yard again; Timber Yard at 2:30 in §10; counts updated (§0, §7, §8, §11) |
| 18 | Major | No slice detection and no faction shop | Signal Shells **[SLICE]** (7:00 row); Curio Cabinet **[SLICE]** with T1 Homeward Horn, Linden Salve, Sage's Tincture, Tin Watchman and T2 Chalk of Seeing (§7.4, §10, §11) |
| 19 | Major | No caster tier in the slice | Collegium and Linden Sister **[SLICE]** (Herb Poultice; Journeyman Papers/Smoke of Rue); Collegium at 6:30 (5:55 if lumber allows), 2 Linden Sisters in the push; §0, §3.3 (+18 lines), §11 updated |
| 20 | Major | Levy could be armed anywhere (worker-rush cheese); WC3 column wrong; no hall-wide Stand Down | Take Up the Flail only within 22 m of a finished hall; 30 m leash with 5 s grace (§13 Q3 now default); **Stand Down (all)** hall button; Hodmen in the mine arm on exit; WC3 column corrected (§4, §5.4) |
| 21 | Major | First hero timing wrong; impossible variants | Hero 1 out about 2:00 (§9, §10); Levy creep limited to camps within 25 m of path and marked "not used on Greenvale"; Tower expand clears the Drystone Fold first |
| 22 | Major | Marshal sustain over-tuned | Linden Balm cannot target herself; regen aura removed by issue 16; both fallbacks (50 % self-heal; Steady Ranks +0.75/1.5/2.25, ×1.5) recorded as §13 Q10 |
| 23 | Minor | Repair rate wording | "A full repair takes 1.5 × the building's build time for one Hodman; each extra repairer adds the same rate" (§4) |
| 24 | Minor | Hero numbers (alternative set) | Superseded by issue 2's numbers, which move every flagged value further |
| 25 | Minor | Hour of Return as a third equivalent | Superseded by issue 1 (Hour Rewound) |
| 26 | Minor | Plant Pavise also halved Siege | Siege unchanged (at most −25 % if playtests ask); §13 Q4 |
| 27 | Minor | Missing implementer fields | Hero Targets column (§6.2); unit Flags column and summon flags (§5.3); DoT/mark damage type and dispellability; Wadding covers ranged non-structure units incl. heroes; Fuse Mark is enemy-only (§6.1, §6.3). Naphtha's burn is a ground effect, so it is stated as not dispellable |
| 28 | Minor | "+12 % base damage" not implementable | Flat `upgrade_damage` per unit table (§8) |
| 29 | Minor | Out of sync with rules.md | Header points to rules.md; attack ids; §7.4 reference; caster start mana 75 and regen 0.65; Croft armour 5; Assayer uses `pierces_immunity`; Homeward Horn moves up to 11 own units within 6 m; 6.0 m gap |
| 30 | Minor | Walled Burg lacked the altar gate | Requires Moot Hall + Oath Hall (§7.1, §7.2) |
| 31 | Minor | No command cards or hotkeys | New §7.5 (Basic B / Advanced V split, unique letters per card, hero Q/W/E/R) |
| 32 | Minor | Too few Reeve lines; missing sample lines | 20 Reeve triggers mapped to rules.md §17.3; Hookgunner, Bombard crew and Firewright sample lines; line budget 162 (§3.2, §3.3) |
| 33 | Minor | Rubric row 5 listed multiple builders | WC3 column = "Militia call-up"; multi-builder note added (§12) |
| 34 | Minor | Slice AI Levy trigger differed from rules.md §19; no stand-down | New trigger (≥ 6 enemy combat food within 20 m of a Hodman within 22 m of a hall; Stand Down (all) after 10 s) (§10) |
| 35 | Minor | No T3 shop stock | **Lookout in a Crate** (150 g, 1 / 120 s) (§7.4) |

**Follow-ups in other files** (not edited here; each owner doc should take these in its next pass):

- `docs/design/rules.md`: §4.3 kingdom row (Hod Chain: +40 % per carrier at 5 lumber per 10 s; Timber Yard drop-off in the slice);
  §9 and §23 Q14 (drop "kingdom casters start at 40 %"); §10.6 example (the Silver Spire no longer has an anti-summon bonus);
  §11 slice detection sources (Signal Shell and Chalk of Seeing are now slice; Silver Spire stays *later*).
- `docs/design/slice-plan.md`: §1.11 should read "2:00 first hero"; B16 `kingdom.caster` → **P0**; add the Timber Yard, Collegium and
  Curio Cabinet to the procedural building kit list.
- `docs/design/factions/clans.md`: mirror the shop decision, i.e. tag the **Tea Tent [SLICE]** with T1 consumables and recall and T2 detection.
- New files at data entry: `docs/research/wc3-hero-ability-reference.csv` and `tests/unit/test_no_wc3_number_fingerprints` (§6.4); a
  VO lint script in `tools/ip/` (§3.3).
