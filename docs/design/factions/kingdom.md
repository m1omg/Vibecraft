# Faction design: `kingdom` — the Kingdom of Brennmark

*Design date: 2026-10-16. Status: proposal for review. Faction id: **`kingdom`** (use this id in every doc and data file).*

**Read with:** `docs/research/ip-safety.md` (§0, §2, §3.2), `docs/research/gameplay-mechanics.md` (§11, §12, §13),
`docs/research/visual-art-direction.md` (§3, §7), `docs/research/audio-direction.md` (§3) and `docs/architecture.md`
(cell and footprint conventions).

**Supersedes for this faction:** the "Bastion" placeholder roster and heroes A-H1/A-H2 in `gameplay-mechanics.md` §13.3 and §13.5,
and the "Hearth Wardens" working name and slate-blue/brass palette (README decision 8; see §1.1 for why the name is retired).
Global rules from `gameplay-mechanics.md` §13.1 still apply: food cap 100, upkeep 0–50 / 51–80 / 81–100 → 100 / 70 / 40 % gold,
hero XP table, revive formula, 480 s day/night, damage matrix.

**Design brief in one line.** A fan should know the job of every Brennish unit and the logic of every build order in seconds,
like the WC3 human kingdom. Nothing a fan sees or hears is Blizzard's: not a name, a silhouette, a palette, an emblem, a voice line
or the culture behind them.

**Units and conventions used below**

- Distances are in metres (1 m = 64 WC3 gu). Speeds are in m/s, and footprints are in 0.5 m pathing cells (`architecture.md`).
- Attack types: Blade, Pierce, Siege, Arcane, Heroic, Spell, Pure (data ids `blade, pierce, siege, arcane, hero, spell, chaos`).
- Armour types: Light, Medium, Heavy, Fortified, Hero, Unarmored.
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
| **Emblem** | **The Ember Wheel**: an ivory six-spoked wagon wheel on a burgundy field, with a bronze flame at the hub and three short crown points on the top of the rim |
| **Motto** | "Every wheel a wall." |
| **Cultural inspiration** | Late-medieval Bohemia and Central Europe: wagon-forts, pavise shields, early hand-cannons, threshing flails, guild towns, half-timbered houses with onion-dome towers, astronomical clocks, silver mining, bobbin lace, the linden tree, storks nesting on rooftops |
| **Palette** | Burgundy, ivory, dark bronze and blackened iron, with oak brown (§2.2). Not blue/white/gold, and no lion |
| **Signature mechanics** | **Levy Horn**: workers arm themselves in place as a temporary flail levy. This is the faction's one WC3-derived mechanic (militia), shown differently. **Wagon Fort**: Wall Wagons deploy into fortified gun-wagons and chain into walls. This mechanic is original |
| **Play pattern** | Sturdy, slow, expensive. Strong infantry walls behind gunpowder, the best towers, flexible casters, late heavy cavalry and air. Weak to mobile harassment early and to magic-damage burst on its unarmoured casters |
| **Slice content** | Hodman (+ Flail Levy), Pavisier, Hookgunner, Bombard Wagon, [SLICE+] Linden Sister. Heroes: Wheel Marshal and Firewright. 7 buildings: Moot Hall → Walled Burg, Croft, Oath Hall, Drill Yard, Foundry, Wainwright Yard, Lookout → Gun Tower. [SLICE+] Collegium |

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

### 1.2 Emblem: the Ember Wheel

- **Shape:**
  - An ivory wagon wheel with **six** thick spokes.
  - A bronze **flame tongue** inside a ring at the hub.
  - Three blunt **crown points** rising from the top of the rim.
  - It sits on a burgundy field.
  - Banners are **swallow-tailed pennants** (two-tailed), never rectangular hanging banners.
- **Read test:** it must read at 24 px as "wheel with a fire in it". Keep spokes thick and the flame one solid shape.
- **Do not:**
  - Ship a bare white wheel on red. Several real civic coats of arms use that (e.g. Mainz, Osnabrück).
  - Use 8- or 16-spoke wheels, which resemble religious or national symbols.
  - Add a lion, eagle, gryphon or chalice.
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
| **Thunder behind the boards** | Gunpowder (Hookgunners, Bombard Wagons, Gun and Bombard Towers) hits hard but is slow to reload |
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
   | Stork Rider | White stork, black wingtips, red beak; the rider's kettle hat |

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
| Metal 1 | Dark bronze | `#6E4A26` | Onion domes, cannon barrels, buckles, the hub flame |
| Metal 1 highlight | Bronze | `#B07F3E` | Painted highlights only |
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
- **No polished steel, gold leaf, marble or glowing holy light.**

### 2.4 Team-colour placement (magenta key `#FF00FF` in concept art; shader-tinted in game)

| Asset | Team-colour areas (aim for 10–15 % of the visible silhouette from the game camera) |
|---|---|
| Workers | Hat band, shoulder sash |
| Infantry / ranged | **Pavise face field** (the emblem stays ivory), arm sash, kettle-hat plume |
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

### 2.6 Squint-test risks and mitigations (internal audit; WC3 names appear here for review only)

| Brennish design | Nearest WC3 design | Risk | Mitigation |
|---|---|---|---|
| Pavisier | Footman | Low | Kettle-hat disc, tall pavise, falchion, ivory gambeson. Never a closed helm with a kite shield |
| Hookgunner | Rifleman (a dwarf) | Low | Human, long thin hook-gun on a forked rest, slow-match smoke. No backpack, no beard |
| Ironrider | Knight | **Medium** (horse and lance is a genre staple) | Burgundy caparison with painted wheels, horse **chest pavise**, kettle-brimmed sallet with plume, no blue/gold, no full-face great helm |
| Wheel Marshal | Paladin | **Medium** (armoured holy-tank role) | A woman in blackened plate with a **wheel-shield and war-pick**. No hammer, no book, no gold, no glowing hands. The heal VFX is drifting linden blossom, not light beams |
| Orrery Sage | Archmage, and the Blood Mage's orbiting orbs | Medium | A woman with a brass armillary frame on her back and a telescope staff. **Never** a long white beard, pointed hat or robe-and-staff look, and **never orbs circling her head** |
| Flail Hetman | Mountain King | Low | A tall human (not a dwarf), no beard braids, no hammer. The flail is the read |
| Firewright | Blood Mage | Low | A soot-faced human in a leather apron with a chimney-hat. No elf, no red-and-gold robes, no orbs |
| Brass Kestrel | Flying Machine | Low | A clockwork bird, not a rotor craft |
| Stork Rider | Gryphon Rider | Low | Stork, not gryphon; human rider; firepots, not hammers |
| Moot Hall | Town Hall | Low | Half-timber, onion dome, stepped gable, burgundy roof |

**Review rule:** every concept image is checked side by side against its nearest WC3 analogue before image-to-3D (ip-safety §2.8).

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
  | Hodman | Older, wry. Counts pokes as billable. Calls his hod "Agnes" |
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
| Ready | "Hod's loaded, boots are muddy." · "Fresh off the cart and already behind schedule." · "Signed, sealed and somewhat willing." |
| What | "Mm? Mind the bricks." · "Hodman. Guild card's in me hat." · "Talk quick, Agnes is heavy." |
| Yes | "Lifting with the knees." · "Agnes and I'll see to it." · "Fine, fine. It's on the ledger." |
| Attack (as Flail Levy) | "This was not in the contract!" · "Flail's out, mind your heads!" · "Like threshing, only it shouts back." |
| Annoyed (played in order) | "That's a poke. I'm noting it." → "Two pokes. Guild says that's a fee." → "Agnes thinks you've got cold fingers." → "Not saying I'll strike. Just saying I own a flail." |
| Built (job-complete category) | "Raised, roofed, and only slightly crooked." |

**Pavisier (line infantry)**

| Category | Lines |
|---|---|
| Ready | "Pavise painted, wall's open for business." · "One more plank in the wall." · "Chin strap tight. Let's be stubborn." |
| What | "The wall's listening." · "Pavisier. What needs holding?" · "Careful, the paint's still wet." |
| Yes | "Wall's moving." · "Shifting the boards." · "Plant me where you point." |
| Attack | "Over the boards!" · "Falchions out!" · "Wall forward, step together!" |
| Annoyed (in order) | "Knocking won't get you through. It's a wall." → "There's a wheel painted on the front. Did it myself." → "It's a good wheel. Bit wobbly on the left." → "Mum calls me a wall with legs. She means it nicely. I think." |

**Wheel Marshal (hero)**

| Category | Lines |
|---|---|
| Ready / revived | "The wheel turns, and I turn with it." · "Spokes tight, rim true." · "Show me a road and I'll be the wall on it." |
| What | "Speak. I hear you over the axles." · "The Marshal attends." · "Which road, which wall?" |
| Yes | "Wheels turning." · "Rolling out." · "Where you point, the rim follows." |
| Attack | "Brace, then break them!" · "Wheel to wall!" · "Hold the ring, then push!" |
| Annoyed (in order) | "A poked wheel keeps turning. Mostly." → "I replaced thirty spokes this year. Don't be the thirty-first." → "I once stopped a runaway cart with my face. This is worse." → "...Fine. Squeak, squeak. Happy?" |

**Advisor ("the Reeve", clipped town official)**

| Event | Line |
|---|---|
| Low gold | "The strongbox is light." |
| Low lumber | "We're short on timber." |
| Food cap | "Raise more crofts." |
| Cannot build | "The ground won't take it there." |
| Hall attacked | "Our hall is taking a beating!" |
| Research complete | "The guild reports it's done." |
| Upkeep changes | "Wages are eating the strongbox." |
| Hero ready | "A captain stands sworn." |

### 3.3 Production notes (audio)

- **Line budget:** follows audio §3.2. For the slice:

  | Voice | Lines |
  |---|---|
  | Hodman | 19 |
  | Pavisier | 18 |
  | Hookgunner | 18 |
  | Bombard crew | 16 |
  | Wheel Marshal | 26 |
  | Firewright | 26 |
  | Reeve (advisor) | 14 |
  | **Total** | **137** |

  Add 18 if the Linden Sister makes the slice. Probe TTS cost with one 5-line batch first (README open question 3).
- **Casting and processing:**
  - ElevenLabs preset voices through Krea, never cloned from real actors.
  - Wheel Marshal: a calm low female voice, light room reverb.
  - Hodman: an older male voice with a slight rasp.
  - Pavisier: a young male voice.
  - Hookgunner: an EQ notch to sound slightly muffled.
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
| Start (global) | Moot Hall, 5 Hodmen, 500 gold / 150 lumber, 08:00 | `gameplay-mechanics.md` §13.1 |
| Gold | Workers walk 10 gold per trip to a hall | Genre standard |
| Lumber | 10 per trip (15 with Bow Saws, 20 with Felling Crews). Drop-off at a hall or the Timber Yard; 1 lumber per 0.8 s chop | Trees are felled when empty (50 lumber) |
| Food | Moot Hall 12 → Walled Burg 14 → Crown Burg 16; **Croft +7** | About 12 Crofts reach the cap of 100 |
| Hero slots | T1: 1, T2: 2, T3: 3. First hero free (5 food) with a free Homeward Horn | Global |
| Construction | Scaffold-raised. **Up to 3 Hodmen** may work one site; each extra builder adds +60 % build rate and costs nothing extra | Multi-builder sites are a genre convention (e.g. *Age of Empires*), not a WC3-only signature |
| Repair | Hodman autocast (default off); costs 30 % of the building's cost pro rata; restores HP at 1.5× its build rate | |
| **Levy Horn** (WC3-derived signature, re-presented) | See below | The one WC3 signature mechanic this faction uses |
| **Wagon Fort** (original signature) | Wall Wagon deploy and chain (§5.4) | |
| Night | No unit modifiers. Buildings glow at night. The **Night Watch** research lets buildings keep day sight at night | |

**Levy Horn: how it differs from WC3's call to arms**

| | WC3 militia | Brennmark Levy Horn |
|---|---|---|
| Trigger | Hall ability only | Hall ability **and** a per-worker command ("Take Up the Flail") |
| Where workers transform | They must run to the hall | **In place**, after 1.5 s (they unsling the flail and swap the straw hat for a kettle hat) |
| Range | Map-wide call | Hodmen within **22 m** of the hall |
| Cooldown | None | 60 s on the hall horn. 20 s per worker after standing down |
| Duration | 45 s | **40 s**, or until "Stand Down" |
| After it ends | Back to work order | Automatically resumes the last gather or build order. Carried resources are kept |
| Presentation | Hall command and call sound | Low wooden horn blast, and a burgundy levy flag runs up the hall's pole |

---

## 5. Unit roster

### 5.1 Fidelity map (WC3 role slot → Brennish unit)

| WC3 human role slot | Brennish unit | Kept familiar (role, build logic) | Made ours (expression and mechanics) |
|---|---|---|---|
| Worker + call to arms | **Hodman / Flail Levy** | Gathers, builds, repairs; the hall turns workers into temporary militia | Arms in place, can arm individually; flail and hat swap; horn and flag |
| T1 melee with defensive stance | **Pavisier** | Cheap heavy-armour line infantry; research a stance that blunts Pierce | Covers allies behind it; painted pavise and falchion |
| T1 gunpowder ranged | **Hookgunner** | Pierce ranged that needs the smithy; range research at T2 | Hook-gun on a forked rest; **Braced Shot** passive |
| T3 heavy cavalry | **Ironrider** | Fast, heavy, expensive, T3 | **Couched Lance** charge; Bohemian barding |
| Healer caster | **Linden Sister** | Autocast heal; dispel at Journeyman; buff at Master | Herbalist; Master buff is spell resistance plus regeneration |
| Slow / debuff caster | **Lacewright** | Autocast slow; ally invisibility; hard disable at Master | **Lace Cocoon** can also protect an ally |
| Anti-magic melee | **Assayer** | Spell-immune melee, burns mana on hit | **Silver Seal** area silence instead of stealing or controlling |
| Mortar siege | **Bombard Wagon** | Long-range splash siege, reveal shot, anti-Medium research | Crew-pushed bronze bombard cart |
| Armoured anti-building engine | **Wall Wagon** | Slow armoured building-breaker with an anti-air mode | **Wagon Fort** deploy and chaining |
| Air scout / anti-air | **Brass Kestrel** | Cheap fast flyer, anti-air, true sight, ground-attack research | Clockwork bird |
| Heavy air | **Stork Rider** | T3 heavy air, Arcane damage, splash research | Giant stork, firepots |
| Air disabler (extra slot) | **Netcaster** (ground special) | Grounds enemy flyers, disables towers | A biped stork-catcher instead of a third air unit (cheaper to produce) |

### 5.2 Production table

| id | Unit | Built at | Requires | Gold | Lumber | Food | Time (s) | Level (XP) | Slice |
|---|---|---|---|---|---|---|---|---|---|
| `kingdom_hodman` | Hodman | Moot Hall (any tier) | — | 70 | 0 | 1 | 15 | 1 | **[SLICE]** |
| `kingdom_flail_levy` | Flail Levy | (Hodman transform) | — | — | — | (1) | 1.5 | 1 | **[SLICE]** |
| `kingdom_pavisier` | Pavisier | Drill Yard | — | 140 | 0 | 2 | 21 | 2 | **[SLICE]** |
| `kingdom_hookgunner` | Hookgunner | Drill Yard | Foundry | 200 | 30 | 3 | 27 | 3 | **[SLICE]** |
| `kingdom_ironrider` | Ironrider | Drill Yard | Crown Burg, Foundry | 250 | 70 | 4 | 45 | 4 | *later* |
| `kingdom_linden_sister` | Linden Sister | Collegium | — | 135 | 15 | 2 | 28 | 2 | **[SLICE+]** |
| `kingdom_lacewright` | Lacewright | Collegium | — | 150 | 25 | 2 | 30 | 2 | *later* |
| `kingdom_assayer` | Assayer | Collegium | — | 200 | 40 | 3 | 30 | 3 | *later* |
| `kingdom_bombard_wagon` | Bombard Wagon | Wainwright Yard | — | 190 | 60 | 3 | 34 | 3 | **[SLICE]** |
| `kingdom_wall_wagon` | Wall Wagon | Wainwright Yard | Crown Burg | 260 | 80 | 4 | 46 | 4 | *later* |
| `kingdom_brass_kestrel` | Brass Kestrel | Wainwright Yard | — | 100 | 25 | 1 | 20 | 1 | *later* |
| `kingdom_netcaster` | Netcaster | Stork Loft | — | 160 | 40 | 2 | 26 | 2 | *later* |
| `kingdom_stork_rider` | Stork Rider | Stork Loft | Crown Burg | 300 | 60 | 4 | 46 | 4 | *later* |

The Collegium, Wainwright Yard and Stork Loft themselves need the Walled Burg (§7), so every unit from them is tier 2 or later.

### 5.3 Combat stats

Sight is day / night in metres. Radius is the collision radius in metres.

| Unit | HP | Mana | Armour | Attack | Damage | Cooldown (s) | Range (m) | Targets | Speed (m/s) | Sight (m) | Radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hodman | 230 | — | 0 Medium | Blade | 5–7 | 2.0 | 0.6 | G | 3.0 | 12.5 / 9.4 | 0.35 |
| Flail Levy | 330 (+100, current HP scaled) | — | 3 Medium | Blade | 10–13 | 1.35 | 0.8 | G | 3.6 | 18.0 / 11.0 | 0.35 |
| Pavisier | 440 | — | 2 Heavy | Blade | 12–14 | 1.35 | 0.8 | G | 4.1 | 21.9 / 12.5 | 0.45 |
| Hookgunner | 520 | — | 0 Medium | Pierce | 22–28 | 1.7 | 7.0 (9.0) | G+A | 4.1 | 21.9 / 12.5 | 0.45 |
| Ironrider | 860 | — | 5 Heavy | Blade | 30–36 | 1.45 | 0.9 | G | 5.5 | 21.9 / 12.5 | 0.7 |
| Linden Sister | 300 | 200 | 0 Unarmored | Arcane | 8–10 | 2.0 | 6.0 | G+A | 4.2 | 21.9 / 12.5 | 0.4 |
| Lacewright | 330 | 250 | 0 Unarmored | Arcane | 10–12 | 1.75 | 6.25 | G+A | 4.2 | 21.9 / 12.5 | 0.4 |
| Assayer | 560 | 250 | 2 Medium | Blade | 15–19 | 1.6 | 0.8 | G | 4.1 | 21.9 / 12.5 | 0.45 |
| Bombard Wagon | 420 | — | 1 Heavy | Siege | 52–64, splash | 3.4 | 15.5 (minimum 3.5) | G | 3.4 | 21.9 / 12.5 | 0.8 |
| Wall Wagon (rolling) | 1050 | — | 3 Heavy | Siege | 46–54 | 2.2 | 1.0 | Buildings and mechanical units | 3.1 | 18.0 / 12.5 | 1.0 |
| Wall Wagon (Fort) | 1050 | — | 6 Fortified | Pierce | 18–22 | 1.3 | 9.4 | G+A | 0 | 21.9 / 14.0 | (blocks 6×4 cells) |
| Brass Kestrel | 280 | — | 1 Light | Pierce | 11–13 | 1.3 | 5.5 | Air (ground with Pellet Hopper) | 6.25 | 23.4 / 15.6 | 0.5 |
| Netcaster | 420 | 180 | 1 Medium | Pierce | 13–16 (+50 % vs air) | 1.6 | 6.0 | G+A | 4.4 | 21.9 / 12.5 | 0.4 |
| Stork Rider | 800 | — | 1 Light | Arcane | 42–50 | 2.1 | 4.5 | G+A | 5.6 | 21.9 / 15.6 | 0.8 |

- **Casters:**
  - Mana regenerates at 0.67/s. Netcaster: 0.6/s.
  - Casters start with 40 % mana.
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

Fights between equal armies should last 10–30 s (mechanics §11.4).

### 5.4 Unit abilities

Autocast toggles with a right-click (global rule). "Research" names the upgrade that unlocks an ability (§8).

**Hodman / Flail Levy [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Gather / Build / Repair | Commands | Repair: autocast, default **off**. See §4 |
| Take Up the Flail | Instant, self | Becomes a Flail Levy for 40 s after 1.5 s of arming. 20 s lockout after standing down |
| Stand Down (as Levy) | Instant | Back to Hodman, resumes the last order |
| (Hall) Levy Horn | No target | All Hodmen within 22 m of the hall arm. Cooldown 60 s. No cost |

**Pavisier [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Plant Pavise (research **Pavise Drill**) | Toggle, 0.75 s to switch | While on: −50 % Pierce and Siege damage taken, +2 armour, move speed −40 %. **Cover:** allied units within 2 m behind the Pavisier take −20 % Pierce damage (does not stack). AI default: on when ranged enemies are in 12 m |

**Hookgunner [SLICE]**

| Ability | Type | Numbers |
|---|---|---|
| Braced Shot | Passive | After 2 s without moving, attacks deal +15 % damage. A forked rest is planted (visual) |
| Drawn Barrels (research) | Passive | Range 7.0 → 9.0 m |

**Ironrider** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Couched Lance (research) | Passive | After 3 s of continuous movement without attacking, the next attack deals **+100 %** damage and knocks a non-hero ground target back 1.5 m. A pennon flutters when the lance is ready |
| Heavy Remounts (research) | Passive | +150 max HP (shared with the Stork Rider) |

**Linden Sister [SLICE+]** (Journeyman and Master training each add +40 HP, +50 max mana and +1 damage)

| Ability | Rank | Mana | Cooldown | Range | Effect |
|---|---|---|---|---|---|
| Herb Poultice (autocast **on**) | Novice | 6 | 1.0 s | 5 m | Heals a damaged allied non-mechanical unit for 30 HP |
| Smoke of Rue | Journeyman | 70 | 2 s | 8 m | Area 3 m radius: removes all buffs (friend and foe) and deals 250 damage to summoned units |
| Linden Wreath (autocast, default off) | Master | 50 | 1 s | 7 m | An ally gains 25 % Spell damage resistance and +1.5 HP/s for 60 s |

**Lacewright** *(later)* (same training bonuses as the Linden Sister)

| Ability | Rank | Mana | Cooldown | Range | Effect |
|---|---|---|---|---|---|
| Tangle Thread (autocast **on**) | Novice | 50 | 1 s | 7 m | Enemy: −50 % move speed, −25 % attack speed for 25 s (heroes 10 s) |
| Muslin Veil | Journeyman | 70 | 1 s | 7 m | An ally becomes invisible for 90 s. Attacking or casting breaks it |
| Lace Cocoon | Master | 160 | 45 s | 8 m | **On an enemy** non-hero up to level 6: cannot move, attack or cast for 12 s, and takes −50 % damage. **On an ally:** it cannot act for 6 s but takes −75 % damage (a rescue tool) |

**Assayer** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Silver-Shod | Passive | Immune to spells, both hostile and friendly (it cannot be healed by the Linden Sister). Ultimates with "Pure" damage still hit it |
| Salt Strike | Passive | Each attack burns 10 mana from the target and deals the burned amount as bonus Spell damage. +40 bonus damage against summoned units |
| Silver Seal (research) | Point, 7 m | Area 3 m radius: enemy units are **silenced** (no spells, no autocasts) for 5 s (heroes 3 s). 75 mana, cooldown 20 s |

**Bombard Wagon [SLICE]** (two crew push a two-wheeled cart; crew and wheels are procedural)

| Ability | Type | Numbers |
|---|---|---|
| Deploy / Pack | Automatic | Must stand still for 0.5 s before the first shot (crew brace the wheels) |
| Signal Shell (research) | Point, 30 m | Reveals an area of 8 m radius for 12 s, including invisible units. Cooldown 40 s, no mana |
| Scatter Shot (research) | Passive | +25 % damage against Medium and Unarmored. Full-damage splash radius 1.25 → 1.75 m |

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
| Pellet Hopper (research) | Passive | Can attack ground units and buildings: Siege 10–12, cooldown 1.6 s, range 3 m |

**Netcaster** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Stork-Catcher | Passive | +50 % damage against air units |
| Weighted Net | Unit, 8 m | An enemy **air** unit is pulled down to ground level for 8 s (heroes 4 s). It cannot move or attack and counts as a ground unit (melee can hit it). 60 mana, cooldown 12 s |
| Soot Pots (research **Soot Pall**) | Point, 9 m | A 4 m radius cloud for 25 s: enemy buildings inside cannot attack. 80 mana, cooldown 30 s |

**Stork Rider** *(later)*

| Ability | Type | Numbers |
|---|---|---|
| Pitch Firepots (research) | Passive | Attacks splash 50 % within 2 m and leave burning ground (2 m radius, 4 s, 8 damage per second) |
| Heavy Remounts (research) | Passive | +150 max HP |

---

## 6. Heroes

### 6.1 Common rules (global, §13.1)

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

### 6.2 Attributes and growth

| Hero | id | Primary | STR (+/lvl) | AGI (+/lvl) | INT (+/lvl) | Base damage (+primary) | Base armour | Base cooldown | Range (m) | Speed (m/s) | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wheel Marshal | `kingdom_wheel_marshal` | STR | 23 (+2.6) | 12 (+1.4) | 16 (+1.7) | 1–7 | 1 | 2.2 | 1.0 (melee) | 4.5 | **[SLICE]** |
| Orrery Sage | `kingdom_orrery_sage` | INT | 15 (+1.6) | 14 (+1.0) | 20 (+3.1) | 2–8 | −1 | 2.1 | 7.8 (missile) | 4.4 | *later* |
| Flail Hetman | `kingdom_flail_hetman` | STR | 24 (+2.5) | 17 (+1.8) | 13 (+1.3) | 1–9 | 0 | 2.0 | 1.1 (melee) | 4.6 | *later* |
| Firewright | `kingdom_firewright` | INT | 16 (+1.8) | 12 (+1.0) | 21 (+3.0) | 3–9 | −1 | 2.2 | 7.0 (missile) | 4.4 | **[SLICE]** |

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
| **Linden Balm** (unit target, may target self) | 1 / 2 / 3 | 70 | 7 s | 8 m | Heals the allied target for **190 / 360 / 530**. Other allies within 2.5 m of the target heal 25 % of that. Does not work on mechanical units. VFX: drifting linden blossoms |
| **Brace the Wheel** (no target) | 1 / 2 / 3 | 60 | 15 s | 4 / 5 / 6 m | Taunts enemy **non-hero** units in the radius to attack her for 2 / 3 / 4 s. She gains +4 / +6 / +8 armour for 6 s |
| **Steady Ranks** (aura) | 1 / 2 / 3 | — | — | 9 m | Allies regenerate +1 / +2 / +3 HP/s, doubled while the ally is below 40 % HP |
| **The Wagon Ring** (ultimate, no target) | — | 175 | 160 s | 11 m | A ghostly ring of wagon wheels rises around her. For **7 s**, allied non-structure units in the ring when cast **cannot drop below 1 HP**. When it ends, each affected unit restores 15 % of its max HP |

#### Orrery Sage (INT caster, the "court magus" role) *(later)*

- **Look:** a middle-aged woman astronomer in an ivory coat with burgundy lining and spectacles. **Brass armillary rings** stand on a
  back-frame above her head, and she carries a telescope staff.
- **Proper names:** Magistra Vendula Starwright · Magistra Ilse Meridian · Magistra Johanka Lenscraft.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Burning Lens** (line toward a point) | 1 / 2 / 3 | 85 | 8 s | Line 12 m × 1.5 m | **75 / 125 / 175** Spell damage to enemies in the line. Struck enemies are **Marked** for 5 s and take +12 % damage from all sources |
| **Clockwork Halberdier** (summon) | 1 / 2 / 3 | 125 | 20 s | Spawns within 3 m | One automaton for 60 s (melee, Heavy armour). Ranks: HP 450 / 650 / 850; armour 2 / 3 / 4; Blade 16–20 / 25–31 / 35–41; cooldown 1.5 s; speed 4.0 m/s; level 2 / 3 / 4. Rank 3: on death it bursts for 60 Spell damage within 2 m |
| **Lucid Hours** (aura) | 1 / 2 / 3 | — | — | 9 m | Allies gain +0.6 / +1.2 / +1.8 mana/s |
| **Hour of Return** (ultimate, no target) | — | 200 | 150 s | 10 m | Marks the Sage and allied non-structure units in range. After **8 s**, or when she recasts it, every marked unit still alive teleports back to where it was marked, and its HP and mana become **the higher** of current and marked values. Summons included. Does not resurrect |

#### Flail Hetman (STR/AGI melee stunner) *(later)*

- **Look:** a towering ex-thresher in a quilted burgundy jack, iron gorget and wide kettle hat. He carries a giant **three-club
  war-flail** (iron-shod clubs on chains) over his shoulder.
- **Proper names:** Hetman Radek Ironchaff · Hetman Bora Sheafbreaker · Hetman Jarmil Wagonwall.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Hurled Chain** (unit target) | 1 / 2 / 3 | 75 | 9 s | 8 m | A weighted chain deals **90 / 170 / 250** Spell damage and **stuns** for 2 / 2.5 / 3 s (heroes 1 / 1.25 / 1.5 s) |
| **Threshing Sweep** (frontal cone) | 1 / 2 / 3 | 80 | 10 s | 5 m, 90° cone | **60 / 100 / 140** Spell damage, **knockback 2 m**, and −2 / −3 / −4 armour for 8 s |
| **Chaff and Grain** (passive) | 1 / 2 / 3 | — | — | 1.5 m arc | Attacks splash 25 / 35 / 45 % damage to enemies around and behind the target. Every 3rd attack on the same target also slows its attack speed by 30 % for 2 s |
| **Wagon-Breaker Charge** (ultimate, point) | — | 150 | 120 s | Up to 16 m | Charges at 12 m/s and is immune to stuns and slows while charging. Enemies in a 2 m-wide path take **150** Spell damage, are pushed aside and **stunned 1.5 s** (heroes 0.75 s). Buildings in the path take 300. On arrival: +40 % attack speed and +1.5 m/s move speed for 10 s |

#### Firewright (INT fire caster) [SLICE]

- **Look:** a stocky, soot-faced man with no eyebrows, a leather apron over an ivory shirt, a **tall felt chimney-hat** with a bronze smoke cap,
  a bandolier of clay flasks, and a linstock staff with a smouldering match-cord.
- **Proper names:** Firewright Kunrat Pitchley · Firewright Vit Sootwick · Firewright Matej Saltpetre.

| Ability | Rank | Mana | Cooldown | Range / area | Effect |
|---|---|---|---|---|---|
| **Naphtha Flask** (point) | 1 / 2 / 3 | 95 | 9 s | 10 m, radius 3 m | Impact **50 / 80 / 110** Spell damage, then the ground burns for 6 s at **12 / 20 / 28** damage per second. Buildings take 50 % |
| **Fuse Mark** (unit or building) | 1 / 2 / 3 | 75 | 10 s | 8 m | Lights a fuse on the target. After **4 s** it explodes for **80 / 140 / 200** Spell damage to the target and 50 % to enemies within 2.5 m. If the target dies first, the fuse explodes at once where it fell. Buildings take ×1.5 |
| **Incendiary Wadding** (aura) | 1 / 2 / 3 | — | — | 9 m | Allied **ranged** units' attacks set targets alight for **3 / 5 / 7** damage per second for 3 s. Refreshes, does not stack; buildings take 50 % |
| **Grand Bombard** (ultimate, point within 6 m) | — | 175 | 150 s | Fires up to 17 m (minimum 3 m) | Places a crewed bronze bombard for **25 s**: 900 HP, 5 armour Fortified, immobile. Fires every 2.4 s at enemy ground units and buildings: Siege **75–85**, splash 1.25 m full / 2.5 m half. Counts as a level-5 summon for XP. Reuses the Bombard Wagon mesh at 1.3× scale |

### 6.4 Kit fidelity audit (policy: at most 2 of 4 abilities may be functional equivalents of the matching WC3 hero's)

| Brennish hero | WC3 role match | Functional equivalents (counted strictly) | Original mechanics | Count |
|---|---|---|---|---|
| Wheel Marshal | Paladin | Linden Balm (targeted heal); Steady Ranks (defensive aura, regeneration instead of armour) | Brace the Wheel (taunt plus armour); The Wagon Ring (cannot drop below 1 HP, instead of a resurrection) | **2** |
| Orrery Sage | Archmage | Clockwork Halberdier (combat summon, melee instead of ranged); Lucid Hours (mana-regeneration aura) | Burning Lens (instant line nuke plus damage mark, not a channelled area rain); Hour of Return (group rewind, not a teleport to a building) | **2** |
| Flail Hetman | Mountain King | Hurled Chain (thrown single-target stun); Threshing Sweep (melee area attack: cone and knockback instead of a slowing circle) | Chaff and Grain (cleave plus attack-speed slow, not a stun chance); Wagon-Breaker Charge (line charge, not a self-transform) | **2** |
| Firewright | Blood Mage | Naphtha Flask (fire area damage over time); Grand Bombard (big summon ultimate: stationary artillery instead of a flying firebird) | Fuse Mark (delayed bomb on a unit); Incendiary Wadding (burning-ammo aura for ranged allies) | **2** |

Every name, VFX, number and visual is ours. No hero reproduces the expressive *combination* of a WC3 kit (ip-safety §2.3).

---

## 7. Buildings and tech tree

### 7.1 Tech tree

```
Moot Hall (T1) ──upgrade──► Walled Burg (T2) ──upgrade──► Crown Burg (T3, needs Oath Hall + Foundry)
│                               │                               │
├─ Croft (+7 food)              ├─ Collegium ── Linden Sister, Lacewright, Assayer
├─ Oath Hall ── heroes          │                (Journeyman training at T2, Master at T3)
├─ Drill Yard ── Pavisier       ├─ Wainwright Yard [needs Foundry]
│              ├ Hookgunner [needs Foundry]       ── Bombard Wagon, Brass Kestrel
│              └ Ironrider  [needs Crown Burg + Foundry]  └ Wall Wagon [needs Crown Burg]
├─ Timber Yard ── Lookout ─┬─ Gun Tower         ├─ Stork Loft [needs Timber Yard]
│                          ├─ Bombard Tower [needs Wainwright Yard]   ── Netcaster
│                          └─ Silver Spire  [needs Collegium]          └ Stork Rider [needs Crown Burg]
├─ Foundry ── weapon / armour / powder upgrades (level 2 needs T2, level 3 needs T3)
└─ Curio Cabinet ── items (stock grows with hall tier)
```

**Slice tree:** the Timber Yard, Stork Loft, Curio Cabinet and T3 are cut. The Lookout needs only the Moot Hall, and the hall takes lumber.

### 7.2 Building table

All buildings have **Fortified** armour and 14 m sight (towers excepted). Footprints are in 0.5 m cells (`architecture.md`: hall 10×10,
barracks 8×8, farm 4×4, tower 4×4).

| id | Building | WC3 role slot | Requires | Gold | Lumber | Time (s) | HP | Armour | Footprint | Food | Function | Slice |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `kingdom_moot_hall` | Moot Hall | T1 town hall | — | 400 | 200 | 170 | 1550 | 5 | 10×10 | +12 | Trains Hodmen; **Levy Horn**; gold and lumber drop-off | **[SLICE]** |
| `kingdom_walled_burg` | Walled Burg | T2 hall (upgrade) | Moot Hall | +310 | +200 | 130 | 2050 | 5 | 10×10 | +14 | Unlocks tier 2 and hero 2 | **[SLICE]** |
| `kingdom_crown_burg` | Crown Burg | T3 hall (upgrade) | Walled Burg, Oath Hall, Foundry | +350 | +220 | 140 | 2600 | 6 | 10×10 | +16 | Unlocks tier 3 and hero 3 | *later* |
| `kingdom_croft` | Croft | Farm | — | 95 | 20 | 38 | 500 | 3 | 4×4 | +7 | Food | **[SLICE]** |
| `kingdom_oath_hall` | Oath Hall | Hero altar | — | 175 | 45 | 60 | 900 | 5 | 6×6 | — | Trains and revives heroes. Heroes swear on an iron wheel set in the floor | **[SLICE]** |
| `kingdom_drill_yard` | Drill Yard | Barracks | — | 160 | 55 | 60 | 1350 | 5 | 8×8 | — | Pavisier, Hookgunner, Ironrider; their research | **[SLICE]** |
| `kingdom_timber_yard` | Timber Yard | Lumber mill | — | 125 | 0 | 55 | 1000 | 5 | 8×8 | — | Lumber drop-off; lumber and masonry research; enables towers | *later* |
| `kingdom_foundry` | Foundry | Blacksmith | — | 150 | 50 | 65 | 1200 | 5 | 6×6 | — | Weapon, powder and armour lines | **[SLICE]** |
| `kingdom_collegium` | Collegium | Arcane sanctum | Walled Burg | 160 | 120 | 65 | 1050 | 5 | 8×8 | — | Casters; Journeyman and Master training | **[SLICE+]** |
| `kingdom_wainwright_yard` | Wainwright Yard | Workshop | Walled Burg, Foundry | 140 | 130 | 60 | 1200 | 5 | 8×8 | — | Bombard Wagon, Brass Kestrel, Wall Wagon | **[SLICE]** |
| `kingdom_stork_loft` | Stork Loft | Aviary | Walled Burg, Timber Yard | 150 | 140 | 60 | 1150 | 5 | 8×8 | — | Netcaster, Stork Rider. Visual: a tall timber tower crowned with a huge stork nest | *later* |
| `kingdom_curio_cabinet` | Curio Cabinet | Faction shop | — | 130 | 30 | 60 | 480 | 5 | 6×6 | — | Sells items (§7.4) | *later* |
| `kingdom_lookout` | Lookout | Scout tower | Timber Yard (slice: none) | 35 | 20 | 25 | 320 | 2 | 4×4 | — | Sight 25 / 18 m; no attack | **[SLICE]** |
| `kingdom_gun_tower` | Gun Tower | Guard tower | Lookout | +75 | +45 | 35 | 520 | 5 | 4×4 | — | See §7.3 | **[SLICE]** |
| `kingdom_bombard_tower` | Bombard Tower | Cannon tower | Lookout, Wainwright Yard | +100 | +100 | 40 | 520 | 5 | 4×4 | — | See §7.3 | *later* |
| `kingdom_silver_spire` | Silver Spire | Arcane tower | Lookout, Collegium | +80 | +90 | 40 | 520 | 5 | 4×4 | — | See §7.3 | *later* |

Notes:

- Hall upgrades keep the footprint. Food from the hall replaces, not adds: 12 → 14 → 16.
- The architecture contract (10-cell hall, 5 m) governs until the slice playtest. The visual doc's 8 m hall proposal is an open question (§13).

### 7.3 Towers (upgrade paths are exclusive: a Lookout becomes one of three)

| Tower | Attack | Damage | Cooldown (s) | Range (m) | Targets | Special |
|---|---|---|---|---|---|---|
| Lookout | — | — | — | — | — | Sight 25 / 18 m; cheap scouting post |
| Gun Tower | Pierce | 21–25 | 1.0 | 10.9 | G+A | Two crew with hook-guns behind a parapet |
| Bombard Tower | Siege | 70–86, splash 1.25 m full / 2.5 m half | 2.6 | 12.5 (minimum 2) | G | Squat stone drum with a bronze barrel |
| Silver Spire | Arcane | 13–15 | 1.6 | 10.0 | G+A | Each hit burns 12 mana (bonus damage equal to the mana burned). ×3 damage against summons. True sight 9.4 m |

### 7.4 Curio Cabinet items (faction shop; the first hero's free item is the Homeward Horn)

| Item | Hall tier | Cost | Stock / restock | Effect |
|---|---|---|---|---|
| Homeward Horn | T1 | 300 g | 2 / 90 s | Blow it for 3 s, then the hero and allied units within 6 m teleport to the nearest friendly hall |
| Linden Salve | T1 | 140 g | 3 / 60 s | +250 HP |
| Sage's Tincture | T1 | 120 g | 3 / 60 s | +150 mana |
| Tin Watchman | T1 | 60 g | 3 / 45 s | Places a tiny clockwork ward: 10 m vision for 180 s |
| Chalk of Seeing | T2 | 75 g | 2 / 60 s | Reveals invisible units within 9 m for 15 s |
| Folding Pavise | T2 | 100 g | 2 / 90 s | Unfolds a 3 m wooden barricade (6×1 cells, 300 HP) for 30 s. Blocks pathing |

---

## 8. Upgrades

Level-2 research needs the Walled Burg (T2); level-3 research needs the Crown Burg (T3).

**Foundry**

| Line | Level 1 | Level 2 | Level 3 | Effect per level | Affects |
|---|---|---|---|---|---|
| **Tempered Blades** **[SLICE: levels 1–2]** | 110 g / 50 l, 60 s | 175 / 160, 75 s | 245 / 290, 90 s | +12 % base damage | Blade attacks: Pavisier, Flail Levy, Assayer, Ironrider, Clockwork Halberdier |
| **Corned Powder** **[SLICE: levels 1–2]** | 110 / 60, 60 s | 180 / 170, 75 s | 250 / 300, 90 s | +12 % base damage | Non-caster ranged and siege: Hookgunner, Bombard Wagon, Wall Wagon (both attacks), Brass Kestrel, Netcaster, Stork Rider |
| **Gothic Plate** **[SLICE: levels 1–2]** | 120 / 70, 60 s | 160 / 170, 75 s | 190 / 260, 90 s | +2 armour | Heavy units: Pavisier, Ironrider, Bombard Wagon, Wall Wagon |
| **Quilted Gambesons** **[SLICE: levels 1–2]** | 100 / 80, 60 s | 150 / 160, 75 s | 200 / 240, 90 s | +2 armour | Medium and Light units: Hookgunner, Flail Levy, Assayer, Netcaster, Brass Kestrel, Stork Rider |

**Timber Yard** *(later)*

| Upgrade | Requires | Cost | Time | Effect |
|---|---|---|---|---|
| Bow Saws | T2 | 110 g / 0 l | 60 s | +5 lumber per trip (10 → 15) |
| Felling Crews | T3, Bow Saws | 210 g / 0 l | 75 s | +5 lumber per trip (15 → 20) |
| Lime Mortar | T1 | 125 / 25 | 60 s | All buildings: +2 armour, +15 % max HP |
| Ashlar Courses | T2, Lime Mortar | 150 / 75 | 70 s | Again +2 armour, +15 % max HP |
| Iron Cramps | T3, Ashlar Courses | 175 / 125 | 80 s | Again +2 armour, +15 % max HP |
| Night Watch | T2 | 75 / 75 | 45 s | Kingdom buildings and towers keep day sight at night |

**Drill Yard**

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Pavise Drill | T1 | 130 / 90 | 45 s | Unlocks Plant Pavise | **[SLICE]** |
| Drawn Barrels | T2 | 80 / 130 | 45 s | Hookgunner range 7.0 → 9.0 m | **[SLICE]** |
| Couched Lance | T3 | 150 / 150 | 60 s | Ironrider charge passive | *later* |
| Heavy Remounts | T3 | 125 / 150 | 50 s | Ironrider and Stork Rider +150 HP | *later* |

**Collegium** (each caster trade has a Journeyman and a Master rank, like a guild)

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Linden Sister: Journeyman Papers | T2 | 120 / 60 | 60 s | Smoke of Rue; +40 HP, +50 mana, +1 damage | [SLICE+] |
| Linden Sister: Master's Seal | T3 | 180 / 140 | 75 s | Linden Wreath; +40 HP, +50 mana, +1 damage | *later* |
| Lacewright: Journeyman Papers | T2 | 120 / 60 | 60 s | Muslin Veil; same stat bonus | *later* |
| Lacewright: Master's Seal | T3 | 180 / 140 | 75 s | Lace Cocoon; same stat bonus | *later* |
| Silver Seal | T2 | 80 / 100 | 45 s | Assayer area silence | *later* |

**Wainwright Yard**

| Upgrade | Requires | Cost | Time | Effect | Slice |
|---|---|---|---|---|---|
| Scatter Shot | T2 | 125 / 100 | 45 s | Bombard Wagon: +25 % vs Medium and Unarmored; full splash radius 1.75 m | **[SLICE]** |
| Signal Shells | T2 | 50 / 50 | 30 s | Bombard Wagon: Signal Shell | *later* |
| Spring Coils | T2 | 125 / 50 | 45 s | Brass Kestrel: air splash | *later* |
| Pellet Hopper | T3 | 150 / 100 | 45 s | Brass Kestrel: can attack ground | *later* |
| Wagon Chains | T3 | 150 / 150 | 60 s | Wall Wagon: chain links | *later* |

**Stork Loft** *(later)*

| Upgrade | Requires | Cost | Time | Effect |
|---|---|---|---|---|
| Soot Pall | T2 | 125 / 150 | 50 s | Netcaster: Soot Pots |
| Pitch Firepots | T3 | 200 / 150 | 60 s | Stork Rider: splash plus burning ground |

**Hall:** the Levy Horn needs no research.

---

## 9. The four tiers of play

| Phase | Clock (typical) | What Brennmark does | Power spike | Main risk |
|---|---|---|---|---|
| **0. Opening** (Moot Hall, no army) | 0:00–1:50 | Hodmen to 5 on gold; Oath Hall, Croft and Drill Yard; first hero at about 1:05 | **Levy Horn**: 5–8 Flail Levies plus a hero repel any early rush; a levy-assisted creep of the nearest green camp is possible | Losing mining time if the levy is overused |
| **1. Tier 1** (Moot Hall) | 1:50–5:55 | Pavisiers, then Hookgunners after the Foundry; hero creeps green camps to level 3; level-1 weapons; Lookouts at chokes | Hero level 3 with 4 Pavisiers and 2–3 Hookgunners | Slow army; vulnerable to fast raiders on the woodline (answer: Levy Horn plus a Lookout → Gun Tower) |
| **2. Tier 2** (Walled Burg) | 5:55–12:00 | Hero 2; Collegium casters (heal, slow, anti-magic); Bombard Wagons; Brass Kestrel scouting; Netcasters if the enemy has air; Drawn Barrels; level-2 upgrades; expansion behind a Gun Tower | Firewright plus Hookgunners with Incendiary Wadding behind planted Pavisiers; Bombard Wagons crack defences | Caster losses to burst; upkeep (stay ≤ 50 food or commit) |
| **3. Tier 3** (Crown Burg) | 12:00+ | Hero 3; Ironriders, Stork Riders, Wall Wagon forts; Master casters; level-3 upgrades; ultimates at hero level 6 | Wagon Ring plus Hour of Return dives; Ironrider Couched Lance flanks; chained Wagon Forts lock a map lane | Heavy gold cost; immobile fort lines can be bypassed |

---

## 10. Recommended opening build order (also the slice AI's script)

Standard "tower-safe hero" opening. Times assume about 2 gold/s per gold worker and a 6–8 m hall–mine gap.

| Time | Food (used / cap) | Action |
|---|---|---|
| 0:00 | 5 / 12 | Moot Hall trains Hodmen continuously until about 14. **Hodman 1 → Oath Hall** (175 / 45). Hodmen 2–5 → gold |
| 0:15 | 6 / 12 | New Hodman → **Croft** (95 / 20), then lumber |
| 0:30 | 7 / 12 | New Hodman → gold (5 on gold = saturated) |
| 0:45 | 8 / 12 | New Hodman → **Drill Yard** (160 / 55), then lumber |
| 0:58 | 9 / 19 | Croft 1 done |
| 1:05 | 14 / 19 | Oath Hall done → **free hero: Wheel Marshal** (sustain for creeping). Hodman 1 → lumber |
| 1:10 | 14 / 19 | Croft 2 (done about 1:53) |
| 1:50 | 17 / 26 | Drill Yard done → Pavisiers continuously. Hero plus the first Pavisiers creep the nearest green camp from about 2:00 |
| 2:15 | 19 / 26 | **Foundry** (150 / 50), then (full game) **Timber Yard** with the next Hodman |
| 2:40 | 22 / 26 | Croft 3 |
| 3:20 | 25 / 33 | Foundry done → Hookgunners mixed in. Corned Powder 1 if the enemy is melee-heavy, Gothic Plate 1 if ranged-heavy |
| 3:45 | 29 / 33 | **Walled Burg** (310 / 200) at about 13 Hodmen (5 gold, 7 lumber, 1 builder). Croft 4 |
| 4:30 | 34 / 40 | Pavise Drill if the enemy shows ranged units. Croft 5 at about 5:00. Keep creeping; hero aims for level 3 by 5:30 |
| 5:55 | 36 / 49 | Walled Burg done (+2 food) → **hero 2: Firewright** and **Wainwright Yard**. Croft 6. A Lookout at the natural expansion |
| 6:45 | 44 / 56 | Lookout → **Gun Tower**; optional second Moot Hall at the expansion |
| 7:00 | 47 / 56 | Croft 7. **Bombard Wagons** ×2, **Drawn Barrels**, level-2 Tempered Blades or Corned Powder |
| 8:30–9:30 | 50–56 | Push: 2 heroes (levels 4–5), 4 Pavisiers, 4 Hookgunners, 2 Bombard Wagons. Plant pavises against ranged, siege the expansion. Accept Low Upkeep only for a decisive push |

**Variants:**

- **Levy creep (aggressive economy):** at 1:10 sound the Levy Horn and creep the nearest green camp with the hero plus the levy.
  It costs about 150 gold of mining and gains about 1 hero level 40 s earlier. Only do it if the camp is within 20 m of the hall.
- **Tower expand:** skip the 3rd Croft until 3:00; at 4:30 build a second Moot Hall at the natural plus 2 Lookouts → Gun Towers.
- **Slice AI** (`gameplay-mechanics.md` §13.7, kingdom flavour):
  - Follow the standard order above.
  - Sound the Levy Horn whenever enemy army food ≥ 6 is within 20 m of the hall.
  - Retreat the hero below 35 % HP.
  - Attack at army food ≥ 40 or when an enemy hero is seen creeping within 31 m.

---

## 11. Vertical slice scope (kingdom vs clans, 1v1 vs AI, one map)

| Category | In the slice | Count |
|---|---|---|
| Worker | Hodman (+ Flail Levy via prop swap: flail and kettle hat; no new model) | 1 |
| Combat units | Pavisier, Hookgunner, **Bombard Wagon** (siege); [SLICE+] Linden Sister | 3 (+1) |
| Heroes | **Wheel Marshal** (STR tank/support), **Firewright** (INT fire; the ultimate reuses the Bombard mesh) | 2 |
| Buildings | Moot Hall (→ Walled Burg), Croft, Oath Hall, Drill Yard, Foundry, Wainwright Yard, Lookout (→ Gun Tower); [SLICE+] Collegium | 7 (+1) |
| Research | Foundry 4 lines × 2 levels, Pavise Drill, Drawn Barrels, Scatter Shot; [SLICE+] Linden Journeyman Papers | 11 (+1) |
| Hall tiers | T1 and T2 only (2 hero slots) | |

**Asset plan and Higgsfield credit estimate (balance 269.75 cr)**

| Asset | Method | Estimated cost |
|---|---|---|
| Hodman, Pavisier, Hookgunner (bipeds; weapons, hod and pavise as separate props) | Concept image (0.25 cr) → Tripo H3.1 image-to-3D (9 cr) → bpy auto-rig plus shared procedural clips | 3 × 9.25 ≈ 28 cr |
| Wheel Marshal, Firewright (bipeds; wheel-shield, flail-free) | Same; Higgsfield rig plus 1 clip (8 cr) only if the bpy rig fails | 2 × 9.25 (+16) ≈ 19–35 cr |
| Bombard Wagon | Cart, wheels and barrel built procedurally in bpy (lathe plus boxes) with AI 2D textures; crew = Hodman mesh in kettle hats | ≈ 1 cr |
| Linden Sister [SLICE+] | Like the bipeds | ≈ 9 cr |
| Moot Hall + Walled Burg | One AI hero building (9 cr); T2 = bpy kitbash (stone plinth, wagon ring, taller dome) | ≈ 10 cr |
| Croft, Oath Hall, Drill Yard, Foundry, Wainwright Yard, Lookout / Gun Tower | **Procedural half-timber kit** in bpy (plaster box, beam trims, tile roof, stepped gable, onion dome, scaffold) with AI-painted textures | ≈ 3 cr |
| Icons (about 30: units, abilities, research) | Higgsfield images (0.25 cr each) or Krea 2 Medium (9 CU each) | ≈ 8 cr or ≈ 270 CU |
| **Total** | | **≈ 70–95 Higgsfield cr** (leaves room for the clans faction and retries) |

Audio: about 137 lines (§3.3) plus about 15 faction SFX through Krea (≈ 70 CU for SFX; TTS cost to be probed).

---

## 12. Distinctness rubric check (ip-safety §3.2; nearest WC3 race: the human kingdom)

| Axis | WC3 human kingdom | Brennmark | Differs? |
|---|---|---|---|
| 1. Silhouette | Closed helms, kite shields, plate pauldrons, steepled stone halls | Kettle-hat discs, tall pavises, flails and hook-guns, wagon boxes, half-timber and onion domes | **Yes** (required) |
| 2. Palette | Blue / white / gold | Burgundy / ivory / dark bronze / blackened iron; no blue, no gold | **Yes** |
| 3. Materials | Polished plate, gold trim, grey stone, blue tile | Lime plaster, dark oak, quilted linen, cast bronze, folk-painted wood, lace, wicker | **Yes** |
| 4. Cultural inspiration | Western high-medieval / Arthurian chivalry | Late-medieval Bohemian guild towns: wagon-forts, early firearms, astronomical clocks, silver mining, linden and storks | **Yes** |
| 5. Signature mechanic | Militia call-up; multiple builders | Levy Horn (the one WC3-derived mechanic, presented differently: in place, per worker, horn and flag) plus an original Wagon Fort | **Yes** (within policy) |
| 6. Names and voice | Footman/Knight/Priest…, "Yes, milord"-style lines | All names original; deadpan guild humour; advisor "the Reeve" | **Yes** |

**Result: 6 / 6 axes differ** (the policy needs 4 plus silhouette). The roles stay close to WC3 on purpose (§5.1).

---

## 13. Open questions and tuning flags

1. **Hall footprint:** 10×10 cells (architecture contract) or 16×16 (the visual doc's 8 m hall)? Decide after the first
   in-engine scale test. The rest of the building footprints scale with it.
2. **Croft +7 food at 95 gold:** check the 0–3 minute supply timing in playtests. If players get supply-blocked at the hero, use +6 food at 85 gold.
3. **Levy Horn abuse:** if "levy rushes" across the map appear, limit the Flail Levy to 30 m from any friendly hall (it stands down outside that range).
4. **Braced Shot plus Plant Pavise** may make static Brennish lines too strong against ranged armies. Tune the Braced bonus (15 %) first.
5. **Hour of Return** needs an implementation check: store the position, HP and mana snapshot per unit; it must stay deterministic.
6. **Netcaster vs a true third flyer:** if playtests miss a third air unit, revisit at full-game scope. The Netcaster was chosen because bipeds are cheap to produce.
7. **Red-team readability** of burgundy units: verify with the first rendered Pavisier at night grading (§2.2 rule).
8. **Clans interaction:** counters and timings in §9 and §10 assume a melee-heavy opponent with beast riders. Re-tune once `clans.md` exists.
9. **Line check:** before recording, check every line in §3.2 against the WC3 quote pages (audio §3.2) and the shelved concept doc, so nothing echoes either.
