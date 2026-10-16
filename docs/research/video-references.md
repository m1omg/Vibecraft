# Video Reference List: WC3-Feel RTS (Vibecraft)

*Research date: 2026-10-16. Purpose: give the art, audio, design and engineering leads a curated watch list that shows what made Warcraft III (2002/2003, Blizzard) feel the way it did, plus Godot-specific implementation tutorials. We study these for timing, structure, readability and feel only. We do not copy assets, names, lines, music or UI art (see "IP guardrails" at the end).*

## How this list was verified

- Every YouTube link below was checked on 2026-10-16 through YouTube's public oEmbed endpoint, so the **title and channel are confirmed**. YouTube blocked page and description scraping from the container, so I could not watch the videos or read their descriptions.
- **Timestamps are given only where I actually saw them** in a search-result description. Everywhere else, "Watch for" says what to look at, not where it is in the video. Treat it as a viewing brief, not a claim about the video's content.
- GDC Vault pages were fetched directly, and their speaker, track and abstract are confirmed.
- Game-mechanic numbers in the "Key moments" table come from classic.battle.net, Warcraft Wiki and Liquipedia (cited). Anything else is marked **(unverified)**.
- Two links found in search failed oEmbed: a full Reign of Chaos soundtrack upload (`sJ1jlcuFPdA`) and a "Happy vs Lyn, first-person view (Lyn)" upload (`_3CcBZQNSpc`). Both are excluded. They may be removed or have embedding turned off. A **first-person-view (POV) pro game** is the single most valuable video type for UI work, so it is worth finding a live one manually.

---

## 0. Watch-first shortlist (about 6 hours, in this order)

| # | Video | Who should watch | Why |
|---|---|---|---|
| 1 | [WCG 2008 GF Final, Round 1: Moon vs Grubby](https://www.youtube.com/watch?v=4gH_BFhjqwg) (official WCG channel) | Everyone | The canonical WC3 game: creeping, hero focus, Night Elf vs Orc, classic 2008 visuals |
| 2 | [Never played Warcraft 3? WATCH THIS!: Grubby](https://www.youtube.com/watch?v=5ygNDJdUVnY) | Design, new team members | A pro explains the core loop (heroes, creeps, upkeep) in plain language |
| 3 | [WC3 Reforged 3.0 Graphics Comparison (Classic/Reforged/Definitive)](https://www.youtube.com/watch?v=k0dJga13D1Q) | Art | Shows how readability changes between art passes: the art lead's key lesson |
| 4 | [Warcraft III: RoC Human Campaign full longplay (VGL)](https://www.youtube.com/watch?v=53Ot4lq6YsY) | Art, Audio, Level design | Atmosphere, tilesets, day/night, ambient sound, mission pacing |
| 5 | [Warcraft 3: Human Building Sounds](https://www.youtube.com/watch?v=3wHMAluEC6g) + [Footman Sounds](https://www.youtube.com/watch?v=KgOswctVGpA) | Audio | The structure of feedback audio: select, order and complete cues |
| 6 | [Inside the Creation of Warcraft III's Soundtrack (Game Informer)](https://www.youtube.com/watch?v=ouNEzATaDMs) | Audio, Music | First-hand account from the composer team (Derek Duke) |
| 7 | [Making a Standard: Blizzard Design Philosophies (Rob Pardo, GDC Vault)](https://www.gdcvault.com/play/1012291/Making-a-Standard-(and-Trying) | Design leads | Blizzard's own design-values talk from the WC3/WoW era |
| 8 | [How I did fog of war without Physics in Godot (Nanotech Gamedev)](https://www.youtube.com/watch?v=pKlEnQUvH9Y) | Engineering | Chapters: 00:00 Intro, 00:32 FoW examples, 05:54 Concepts, 26:58 Code |

---

## A. Full pro WC3 games: macro, micro, creeping, hero use, UI interaction

**What to study across all of these:**
1. **Creep route timing:** when the first hero leaves base and how many camps are cleared before the first fight.
2. **Hero focus-fire:** how clearly a hero reads in a 40-unit fight, through silhouette, team-color ring, scale and name/HP bar.
3. **Army size vs upkeep:** pros often hover around 50 or 80 food on purpose.
4. **Town Portal / item use** as a comeback mechanic.
5. **How often casters and players look at the minimap.**
6. **Fight length:** most decisive fights last about 10 to 30 s *(unverified, so measure it)*.

| # | Link | Notes / what to watch |
|---|---|---|
| A1 | [WCG 2008 GF Final, Round 1: Moon vs Grubby](https://www.youtube.com/watch?v=4gH_BFhjqwg) | Official WCG upload. Map: Turtle Rock. Moon (NE) wins with Druid of the Talon armies (Inven Global recap). **Watch for** NE "tree" base silhouettes and how air and caster units read against grass. |
| A2 | [WCG 2008 GF Final, Round 2: Moon vs Grubby](https://www.youtube.com/watch?v=Ldx-u8coJQw) | Map: Secret Valley. Grubby (Orc) traps Moon's Demon Hunter twice. **Watch for** hero-trap micro (net/ensnare plus body-block), the hero-low-HP panic, and the hero retreat-to-base pattern. |
| A3 | [WCG 2008 GF Final, Round 3: Moon vs Grubby](https://www.youtube.com/watch?v=CjskE1xU54s) | Map: Twisted Meadows. Grubby gets an early hero kill, then surrounds both NE heroes with a Scroll-of-Speed army and wins the title. **Watch for** a hero dying: the global "has fallen" message, no corpse, and the momentum swing. |
| A4 | [WCG 2010 GF Final, Set 3: Grubby vs ReMinD](https://www.youtube.com/watch?v=GQRV_HXjhes) | Official WCG. Later-era Orc vs NE. Compare how the pacing evolved over two years. |
| A5 | [Yuwan Cup Grand Final: Moon (NE) vs Infi (Hu)](https://www.youtube.com/watch?v=Lot6N4doe8Q) | Back2Warcraft, cast by Neo & remo (Oct 1, 2016). Human "Infi" style: towers, expansions, Archmage + Mountain King. **Watch for** Human base layout and Town Hall / militia moments. |
| A6 | [Show Cup #34: Happy (UD) vs Infi (NE)](https://www.youtube.com/watch?v=c_RivjkBo7Q) | Back2Warcraft, cast by Neo (Aug 12, 2022). **Watch for** Undead blight spreading as a terrain-state change, Acolyte "summoned" construction, and Death Knight coil and heal micro. |
| A7 | [Happy (UD) vs Lyn (Orc) Grand Final: TeD Cup 17](https://www.youtube.com/watch?v=4ckacR_3CFg) | Back2Warcraft. The defining modern matchup. **Watch for** Blademaster harass with invisibility (Wind Walk) and how the UI telegraphs invisible units. |
| A8 | [Happy vs Lyn: TeD Cup 19 Grand Finale](https://www.youtube.com/watch?v=zEvs8ramsOk) | Tak3r cast. Played Dec 14, 2023, Bo7 on Reforged. Long series, good for sampling many maps. |
| A9 | [Happy vs Lyn, cast by Grubby (Games 1 & 2)](https://www.youtube.com/watch?v=kmwV6WWGE2g) | A pro caster explains *why* each decision matters. Note every time Grubby says "creep", "level", "item" or "upkeep". |
| A10 | [Moon vs Sok: Grubby analysis ("best Elf vs Human")](https://www.youtube.com/watch?v=PpYx1FMVTBc) | Grubby channel. NE vs Human micro. **Watch for** Moon Well mana top-ups, Ancient (building) uprooting, and hero-item juggling. |
| A11 | [Moon vs Sok: BetBoom Classic (NE vs Hu)](https://www.youtube.com/watch?v=ihb4Oizqu28) | Tak3r cast, Bo3 (Jan 30, 2024). Same matchup in a tournament setting. |
| A12 | [Grubby vs ToD (Orc vs Human): W3Champions ladder](https://www.youtube.com/watch?v=fZyIhW2r1Is) | Tak3r cast (May 2022). ToD's Human play. Good for Town Hall "Call to Arms" and tower rush/defense moments. |
| A13 | [MYM Grubby (Orc) vs MYM Moon (NE): RN34](https://www.youtube.com/watch?v=qNiy7YFS10I) | Replay upload from the Frozen Throne era. Uncast replays are better for **listening to raw game audio** (unit acks, combat SFX) without commentary. |
| A14 | [Moon: "I'm the best Nightelf in the world" (Back2Warcraft)](https://www.youtube.com/watch?v=u3NO1nfneCM) | Interview/feature. Useful context on player identity and race fantasy. |

**Pro-guide videos (explain the loop):**

| # | Link | What to study |
|---|---|---|
| A15 | [Never played Warcraft 3? WATCH THIS!: Grubby](https://www.youtube.com/watch?v=5ygNDJdUVnY) | The game's pitch in a pro's words. Use it to write our own one-paragraph core-loop pitch. |
| A16 | [Interface: Hotkeys and Control Groups (#2, Beginner's Guide 2026)](https://www.youtube.com/watch?v=QGwAUV4bdIw) | GrubbyTalks. **Command card grid, control groups, hero selection hotkeys.** Required viewing for the UI engineer. |
| A17 | [Early Game: Creeping and Build Orders (#6, Beginner's Guide 2026)](https://www.youtube.com/watch?v=YMUTzguoT3o) | GrubbyTalks. Creep-camp difficulty, the order of camps, and the first hero's level curve. |
| A18 | [Grubby: The Importance of Creeping](https://www.youtube.com/watch?v=jWnalz1L0bM) and [Planning Your Route w/ Creep Orders](https://www.youtube.com/watch?v=k-gCz2MLW8o) | HeroesHearthWC3 re-uploads of Grubby guides. Creep routes are the "PvE layer" that makes WC3 feel unlike Stratagus-style clones. |
| A19 | [A guide to creeping in WC3: Part II of III](https://www.youtube.com/watch?v=5ccoajNlgYo) | carsoNNN. Per-race creeping tricks such as pulling and aggro range. Use it to tune our creep leash and aggro radii. |
| A20 | [Is it TIME to play Warcraft 3? Grubby's "Getting Started" guide (WTii Reacts)](https://www.youtube.com/watch?v=EDv2lcgEEA0) | A newcomer's view of what is confusing. Helps decide tutorial content. |

---

## B. Casual and campaign gameplay: atmosphere, tilesets, day/night, sound, music

**What to study:**
1. **Saturated, hand-painted terrain with strong tile-blend edges** (grass to dirt to rock) and doodads such as fences, crates, lamps and mushrooms that make a map feel lived in.
2. **The light color at night**: the bluish tint, and that units stay readable.
3. **Ambient beds per tileset**: birds, wind, water.
4. **Music that switches per race and per mission.**
5. **In-engine cutscene staging**: the letterbox, the portrait with talking-head animation.

| # | Link | Notes / what to watch |
|---|---|---|
| B1 | [Warcraft III: RoC Human Campaign full longplay (VGL)](https://www.youtube.com/watch?v=53Ot4lq6YsY) | Lordaeron Summer/Fall tilesets, villages, the first heroes. **Log** each mission's length, objective type, and first-hero level at the first boss. |
| B2 | [Warcraft III: RoC Undead Campaign full longplay (VGL)](https://www.youtube.com/watch?v=AQIiQHvLAGQ) | Blight terrain transformation, night missions, the snow tileset. **Watch** how blight changes the ground texture as a gameplay-visible state. |
| B3 | [The Culling (RoC, no commentary)](https://www.youtube.com/watch?v=R4eom7ZUz1c) | The iconic timed mission (designed by David Fried per Warcraft Wiki). Study urgency created through a kill-counter UI and scripted spawns. |
| B4 | [Warcraft 3 Movie (Original, not Reforged): full RoC + TFT campaigns](https://www.youtube.com/watch?v=LMPgM1IIk7c) | All in-engine cutscenes stitched together. Study the **talking-portrait + letterbox** cutscene grammar. It is cheap for us to reproduce with our own art. |
| B5 | [Warcraft III RoC Intro Cinematic](https://www.youtube.com/watch?v=uAKPumG-6J4) | Prerendered tone-setter (grunt vs footman skirmish). Mood board for our own key art, not something to imitate shot for shot. |
| B6 | [Warcraft 3 Cinematic: Human Intro "The Warning"](https://www.youtube.com/watch?v=mi4BApIqsDA) | Campaign-intro pacing for a faction. |
| B7 | [Day night cycle, Warcraft III Reforged (#shorts)](https://www.youtube.com/watch?v=JvDIC7BZDVk) | A short clip of the transition. Measure how long the light lerp takes and how dark the night gets. |
| B8 | [How to use the new Warcraft 3 Light Editor (MickCraft)](https://www.youtube.com/watch?v=Yup1xH4Gmw8) | Shows how WC3 (Reforged) authors per-map lighting. A reference for building our own day/night `Environment` presets. |
| B9 | [Orcs: Music & Ambience, Warcraft III (Everness)](https://www.youtube.com/watch?v=d-HYwNeJRQM) | A long ambience-plus-music mix. Use it as a **mood target** when prompting ElevenLabs Music / Seed Audio: tempo, instrumentation (drums, low brass, throat chant), and loop density. |
| B10 | [Blackrock & Roll (Alliance), RoC OST](https://www.youtube.com/watch?v=uyx5AYHI2Vs) / [Rise of the Ancients (Night Elves)](https://www.youtube.com/watch?v=nxiGNossTLg) | Race-themed scoring. Note the instrument palette per faction. RoC composers per listings: Tracy W. Bush, Derek Duke, Jason Hayes, Glenn Stafford. |
| B11 | [Warcraft 3: Human Building Sounds (The Game Archiver)](https://www.youtube.com/watch?v=3wHMAluEC6g) | The click-to-select "building voice" for every structure (bell, forge clang, chants). We need an **equivalent one-shot per building type**. |
| B12 | [Warcraft 3: Undead Building Sounds (The Game Archiver)](https://www.youtube.com/watch?v=WHwDTfF8qdo) | Contrast: the same function, a completely different sonic identity. |
| B13 | [Warcraft 3 Frozen Throne: Footman Sounds (VGSoundFX)](https://www.youtube.com/watch?v=KgOswctVGpA) | The full acknowledgement set for one unit. Template for our VO script categories (see Key moments, M10). |
| B14 | [Warcraft 3 Orc Quotes](https://www.youtube.com/watch?v=MXgr6SYYNZM) / [Warcraft III Funny Quotes Part 1: Humans](https://www.youtube.com/watch?v=QiwiuDW52hY) | The "pissed" easter-egg lines (repeated clicks). This **personality layer** is a big part of the WC3 charm. Write our own originals. |
| B15 | [Warcraft 3: Level up sound effect](https://www.youtube.com/watch?v=r6v8zgsXJrU) | The single most iconic feedback sound. Analyze it: a bright, rising, short sound, roughly 1 to 2 s *(unverified)*. Design our own with a different motif. |
| B16 | [Warcraft 3: Gold mine](https://www.youtube.com/watch?v=lD55CrlRPl0) | Workers entering and exiting the mine. Check what visual cue, if any, plays on enter/exit (the "gold-mine flash" the user remembers). |
| B17 | [The BEST HERO DEATH SOUNDS in WC3; a tier list (GrubbyTalks)](https://www.youtube.com/watch?v=U6ZrCOARhZc) | Hero deaths must be loud, distinct and global. A pro explains which ones "feel" best and why. |
| B18 | [Secrets in Warcraft 3's Icons & Sounds (Abelhawk)](https://www.youtube.com/watch?v=WzLnOyWTZsA) | How Blizzard reused and layered sounds and painted icons. Good for our icon style guide: chunky 64 px icons with a beveled frame. |

---

## C. Reforged vs Classic comparisons: what readability means for our art

**Key lesson to extract:** many viewers and pros felt Reforged's higher-detail models and lower-saturation palette "blend" into the ground. Commenters noted the classic terrain had baked shading and depth that the new textures lacked. For an AI-generated asset pipeline (Krea / Tripo / Hunyuan GLBs), we must **enforce silhouette, saturation and team-color readability** rather than detail.

| # | Link | What to study |
|---|---|---|
| C1 | [Warcraft III: Reforged vs Classic, Direct Comparison (Nick930)](https://www.youtube.com/watch?v=TUXjHKh2hpY) | The same scenes side by side. Screenshot pairs at gameplay zoom and judge which reads faster. |
| C2 | [WC3 Reforged 3.0 Graphics Comparison: Classic / Reforged / Definitive (Churchy)](https://www.youtube.com/watch?v=k0dJga13D1Q) | Three art passes in one client. Best single video for art direction. |
| C3 | [WC3 Reforged 3.0 Graphics Comparison: Neutrals (Churchy)](https://www.youtube.com/watch?v=NV8YGW6zVCw) | **Creeps and neutral buildings** (shops, mines, taverns). These are what we will generate first. |
| C4 | [Human Models: Original vs Definitive Edition (YOYO-DODO)](https://www.youtube.com/watch?v=qU2TlJtBCMo) | Proportions: big hands, weapons and shoulder pads; small legs. Measure the head-to-body ratio. |
| C5 | [All Night Elves: Original vs Reforged (YOYO-DODO)](https://www.youtube.com/watch?v=41PvXoiNWWw) | Glow and emissive accents as faction identity. |
| C6 | [All Undeads: Classic vs Reforged](https://www.youtube.com/watch?v=yxWHNVYiKOM) / [All Demons](https://www.youtube.com/watch?v=UZgSUMt3_uM) (YOYO-DODO) | Spiky silhouettes and green/purple VFX palettes. |
| C7 | [Warcraft 3 Original vs Reforged (ComputerBase)](https://www.youtube.com/watch?v=TeGv40-PoKM) | Press comparison (German outlet), including cutscenes. |
| C8 | [Let's mix it up! Reforged environments with Classic HD models: WC3 2.0 (Grubby)](https://www.youtube.com/watch?v=FcbklFRr7jc) | Mixing high-detail terrain with stylized units. This is exactly our risk with AI terrain textures plus AI GLB units. |
| C9 | [Warcraft 3 Just Got Ambient Occlusion: PTR Patch (Daily Warcraft Reforged)](https://www.youtube.com/watch?v=zWq-Q94ejrM) | How much AO helps ground units visually. On our software renderer, consider **baked AO or a blob shadow** instead of SSAO. |
| C10 | [I don't even know what Warcraft III looks like anymore (Xander Dorn)](https://www.youtube.com/watch?v=-HD6E42Su8Q) | Critical essay on WC3's visual identity drift. Useful for writing our art "do / don't" rules. |
| C11 | [Blizzard Released WC3: Reforged 2.0, Flawed but Significantly Improved (Costin Gaming)](https://www.youtube.com/watch?v=YTLVMBGF0Fg) / [HUGE Warcraft 3 CHANGES (WTii)](https://www.youtube.com/watch?v=SeiIkWfRUW8) | The 2024 2.0 update brought back classic-style art options. Shows what the community values. |
| C12 | [STYLE over FUNCTION! How we can improve Warcraft3's 2.0 Menus (Back2Warcraft)](https://www.youtube.com/watch?v=9wefqiem_-A) | Pro criticism of the menu UI. A checklist of what not to do in our menus. |

---

## D. Design talks, interviews and video essays

| # | Link | What to study |
|---|---|---|
| D1 | [GDC Vault: Making a Standard (and Trying to Stick to it!): Blizzard Design Philosophies, Rob Pardo](https://www.gdcvault.com/play/1012291/Making-a-Standard-(and-Trying) | GDC 2010 lecture, Game Design track (confirmed on the Vault page). Blizzard's core design values. Use it to write our own 5 to 7 pillar statements. The Vault may require a subscription. |
| D2 | [GDC Vault: Rules of Engagement: Blizzard's Approach to Multiplayer Game Design, Rob Pardo](https://www.gdcvault.com/play/315/Rules-of-Engagement-Blizzard-s) | GDC 2008. Multiplayer design (WC3 was its ladder-era proving ground). |
| D3 | [GDC Vault: The Game Design of STARCRAFT II: Designing an E-Sport, Dustin Browder](https://www.gdcvault.com/play/1014488/The-Game-Design-of-STARCRAFT) | GDC 2011. The closest Blizzard RTS design postmortem with an online recording. Focus on unit counters, readability, and "spectator clarity". |
| D4 | [Classic Game Postmortem: Command & Conquer (GDC, free on YouTube)](https://www.youtube.com/watch?v=rIXK3fRx4Zo) ([Vault page](https://www.gdcvault.com/play/1025777/Classic-Game-Postmortem-Command-Conquer)) | GDC 2019, with Louis Castle, Erik Yeo, Frank Klepacki and Steve Wetherill. An RTS-genre origin talk covering UI and unit-voice conventions WC3 inherited. |
| D5 | [Designer Notes podcast: Rob Pardo Part 1](https://www.idlethumbs.net/designernotes/episodes/rob-pardo-part-1) / [Part 2](https://www.idlethumbs.net/designernotes/episodes/rob-pardo-part-2) (audio) | Soren Johnson's 2014 interview. Part 1 covers StarCraft, Brood War and **Warcraft III**, including that it began as "Warcraft Legends", a third-person, small-squad concept ([Game Informer summary](https://www.gameinformer.com/b/news/archive/2014/11/03/warcraft-iii-was-almost-a-non-traditional-rts-called-warcraft-legends.aspx)). Explains *why* WC3 has heroes and small armies. |
| D6 | [Game Masters: Rob Pardo and Chris Metzen of Blizzard (National Museums Scotland)](https://www.youtube.com/watch?v=Jsl6aKj4JW8) | Museum interview with the WC3 lead designer and the story/art lead. |
| D7 | [Samwise Didier, Senior Art Director, Blizzard (Computer History Museum)](https://www.youtube.com/watch?v=hCx6lDSlZ40) | The source of the "Blizzard look": chunky proportions, oversized armor and weapons, bold color. Pair it with D8. |
| D8 | [WonderCon 2015: Blizzard Artist Samwise Didier Spotlight](https://www.youtube.com/watch?v=inLg4b38pY8) | Panel format with more on drawing style and exaggeration. |
| D9 | [How Blizzard Created Warcraft III's Cinematics (Game Informer)](https://www.youtube.com/watch?v=Jgndut9nY0Q) | Interview with Jeff Chamberlain on WC3 cinematics and story. Tone and staging. |
| D10 | [Inside the Creation of Warcraft III's Soundtrack (Game Informer)](https://www.youtube.com/watch?v=ouNEzATaDMs) | Derek Duke on the WC3 score. Use it for music direction and ElevenLabs Music prompts. |
| D11 | [How Blizzard Created the Sound of World of Warcraft: Behind the Music of Vanilla WoW (The WoW Archives)](https://www.youtube.com/watch?v=gy4ePZnvuKc) | From Blizzard's 2004 archive material. The same audio-team era as WC3/TFT, covering their sound-design philosophy. |
| D12 | [How Blizzard Hopes To Renew Interest In The RTS With WC3: Reforged (Game Informer)](https://www.youtube.com/watch?v=x-H99TnQnl0) | Interview with the Reforged lead environment artist, lead producer and lead designer. Explains what they tried to preserve. |
| D13 | [New, Exclusive Details On WC3: Reforged's Development (Game Informer Show excerpt)](https://www.youtube.com/watch?v=vipXWdVic2Q) | Hosts recount a visit with original WC3 developers. |
| D14 | [WC3 Reforged: Developers Interview at BlizzCon 2019 (Back2Warcraft)](https://www.youtube.com/watch?v=_oiRnFGgD_I) | Production director Kaeo Milker and senior animator Keith Sizemore. Note the animation comments: Reforged reportedly kept attack timings frame-identical for gameplay parity (GamingBolt). |
| D15 | [Warcraft 3 Level Designer AMA, Part 1](https://www.youtube.com/watch?v=C_v-zonH91s) / [Part 3](https://www.youtube.com/watch?v=6BDckItrg3Y) (Abelhawk) | David "DesignerDave" Fried, WC3 campaign/melee map designer (The Culling and others, per Warcraft Wiki). Level design, map flow and creep placement. |
| D16 | [Warcraft III Reforged: Forsaken Kingdom: What's Next Panel, BlizzCon 2026 (official Warcraft channel)](https://www.youtube.com/watch?v=mHKNDO-PTs8) | The current (2026) official direction for WC3 content. Shows what Blizzard itself considers "modern WC3". Content not reviewed. |
| D17 | [How Warcraft 3 Became the Most Successful RTS in History (Nixxiom)](https://www.youtube.com/watch?v=rw4yHKcIdyw) | Video essay: why it worked (heroes, custom maps, story). |
| D18 | [Why Warcraft 3 Accidentally Killed Its Own Genre (nelvox)](https://www.youtube.com/watch?v=YURF3AbgIw4) | Video essay on how the MOBA spun out of WC3's hero focus. Useful to decide how hero-centric we go. |
| D19 | [The History of Warcraft 3 and what it Means Now (WTiiWarcraft)](https://www.youtube.com/watch?v=5D_SbpLsMDI) | A technical/historical breakdown from a long-time WC3 caster. |
| D20 | [Warcraft 3 Retrospective (acritical)](https://www.youtube.com/watch?v=zMBTnT99WyQ) | Story, gameplay and Battle.net legacy. |
| D21 | [GDC Vault: Visual Effects Summit: "World of Warcraft" VFX Pillars (Sarah Carmody, Blizzard)](https://gdcvault.com/play/1029418/Visual-Effects-Summit-World-of) | Blizzard's stylized VFX art direction and style guides. This is the closest public Blizzard talk on spell-FX style. |
| D22 | [Why Does World of Warcraft Look Like This? (EMC3D)](https://www.youtube.com/watch?v=ptwQWuDsExQ) | Hand-painted, low-poly, texture-carries-lighting style. **Our software-rendered target should look like this**: unlit/half-lambert plus painted AO. |
| D23 | [Secrets of Game Feel and Juice (Game Maker's Toolkit)](https://www.youtube.com/watch?v=216_5nu4aVQ) | Not WC3-specific, but the vocabulary for hit-flash, screenshake, anticipation and sound layering. Apply it sparingly in an RTS: the camera does not shake for every hit. |
| D24 | [Experiential Unit Design: RTS Podcast Highlights (Stardock)](https://www.youtube.com/watch?v=nVzVL7zo2MI) | Ashes designer Callum McCole on making units feel experientially distinct. |

---

## E. Devlogs of modern indie and AA RTS (Godot, Unity, Stormgate)

| # | Link | What to study |
|---|---|---|
| E1 | [Stormgate: The difference a year makes (Frost Giant Studios, official)](https://www.youtube.com/watch?v=mZoMdLAcq24) | Ex-Blizzard RTS team showing a year of art and feel iteration. Study **what they changed after public feedback** (art readability, unit scale). |
| E2 | [Stormgate: Official Developer Update Video, Summer of Gaming 2022 (IGN)](https://www.youtube.com/watch?v=GvFPchpfP8M) | Pitch, pillars, setting. Compare how a Blizzard-lineage team frames an RTS in 2022. |
| E3 | [Stormgate Engine, Art & Faction Reveal (WinterStarcraft)](https://www.youtube.com/watch?v=VkLE8FQ9nQQ) | Engine (named "Snowplay", unverified) plus art reveal, with a caster's reaction to readability. |
| E4 | [Stormgate Patch 0.3: Big Graphics, Hotkeys & Gameplay Update (WintergamingTV)](https://www.youtube.com/watch?v=kN3ljseDB8w) | A concrete before/after graphics patch. |
| E5 | [STORMGATE: How the gameplay will look (with a Frost Giant lead designer)](https://www.youtube.com/watch?v=O14znz-kKKA) | Design rationale from the lead designer (Kevin Dong per the search listing). |
| E6 | [Godsworn is a Base-building RTS with Heroes and Creatures (perafilozof)](https://www.youtube.com/watch?v=6sSoYO-vGB0) / [A Fusion of WC3 and Age of Mythology?! Godsworn EA (Bandanner)](https://www.youtube.com/watch?v=lp5MoI4Kl_8) | The closest indie "WC3-like" (heroes plus creeps). **Study what reads as generic vs distinctive.** Steam: [Godsworn](https://store.steampowered.com/app/1328990/Godsworn). |
| E7 | [The Scouring: Warcraft 3 Inspired Indie RTS (JustDaZack)](https://www.youtube.com/watch?v=1CHc3B10Ds4) | Another WC3-inspired indie. Compare its art scale and UI against WC3. |
| E8 | [Godot RTS Devlog 001: Faction System, Gamedata, Asset Workflow](https://www.youtube.com/watch?v=KicnrR9CXXo) / [002: Prefabs, Gamedata, GLTF & Materials Loading](https://www.youtube.com/watch?v=l9Ba3HrTKI0) (Nanotech Gamedev) | **Data-driven units and a GLTF import pipeline in Godot**, which maps directly onto our Krea GLB pipeline. |
| E9 | [How to develop code structures for an RTS in Godot: Composition System (Nanotech Gamedev)](https://www.youtube.com/watch?v=MRwM3LOal5o) | Component architecture (health, attack, mover, selectable). Compare it with our planned architecture. |
| E10 | [I release my Godot RTS game!! (Slick Games)](https://www.youtube.com/watch?v=UMyWbCSZqI0) | A shipped small Godot RTS. Covers sound, music and steering behaviour at the end of production. |
| E11 | [Unit Movement and Armies: Making an Unnamed RTS in Godot, Devlog 2 (Fun Noober Codes)](https://www.youtube.com/watch?v=2F0p1DNN1a0) | Squad coordination and pathfinding problems in Godot. |
| E12 | [Demo my RTS Game in Godot: Unit selection, movement, pathfind and combat (Phantawalker)](https://www.youtube.com/watch?v=qp6W4SLU7W8) | A quick benchmark of what a minimal Godot RTS loop looks like. |
| E13 | [Game Dev: How to make a 3D Fog of War in Godot: Detailed Recap (ScyDev Games)](https://www.youtube.com/watch?v=VY2I7XdvsMY) | About a year of iteration on 3D FoW for a free-camera Godot RTS. |
| E14 | (Repo, not video) [lampe-games/godot-open-rts](https://github.com/lampe-games/godot-open-rts) | MIT-licensed open-source Godot 4 RTS: 8 players, AI, terrain and air units. **Read its code before writing ours**: selection, navigation, match flow. |

---

## F. Godot 4 RTS tutorials: selection box, fog of war, minimap, avoidance, camera

> Our target is Godot 4.7. Most tutorials target 4.0 to 4.5. Navigation and avoidance APIs changed in 4.1/4.2 (avoidance layers, `velocity_computed`), so check every snippet against the 4.7 class reference.

| # | Topic | Link | Notes |
|---|---|---|---|
| F1 | Series overview | [Rts in Godot Part 1: Series Intro & Project Setup, RTS From Scratch in Godot 4.5+ (Nanotech Gamedev)](https://www.youtube.com/watch?v=IJAJ_d_JaeY) | The newest full series (4.5+). |
| F2 | Camera | [How I made an RTS Camera on Godot 4, Part 1 (Nanotech Gamedev)](https://www.youtube.com/watch?v=t-tkFxhpiCs) | Pan, zoom, edge-scroll foundation. |
| F3 | Camera | [RTS Camera controller: Zoom](https://www.youtube.com/watch?v=MOoL7a4G46g) / [Rotation](https://www.youtube.com/watch?v=EHYVbS2sWjQ) (Indie Quest) | Zoom-to-cursor (keep the point under the mouse fixed). May be Godot 3 era, so port it. |
| F4 | Camera | [Smooth camera: move, pan, rotate, zoom in Godot 4.3 (S&Nanimation)](https://www.youtube.com/watch?v=ssTa8LgeO3M) | Smoothing and lerp patterns. |
| F5 | Selection | [Godot RTS Tutorial Ep. 1: Unit Selection and Movement (LegionGames)](https://www.youtube.com/watch?v=JXvNOnmBgRg) | Click and box select basics. |
| F6 | Selection | [RTS Selection System, Part 2](https://www.youtube.com/watch?v=f6SXH_27kNA) / [Part 4](https://www.youtube.com/watch?v=ysV8GnFtJkc) (Nanotech Gamedev) | Drag-box selection in 3D via screen-space projection of unit positions. Part 4 adds a 3D move-cursor animation, which is our "move order ping". |
| F7 | Selection | [RTS Selection Operations Done in Godot (Nanotech Gamedev)](https://www.youtube.com/watch?v=BnmNrGGBIPk) | Shift-add, ctrl-type-select, double-click select-all-of-type. These are WC3 conventions. |
| F8 | Control groups | [Control Units & Group System: RTS inspired, Godot 4 (16BitDev)](https://www.youtube.com/watch?v=eQjBLFKamms) | Control groups, box selection, formation, navigation, animation. |
| F9 | Selection | [Godot Recipe: Drag-select Multiple Units (KidsCanCode)](https://www.youtube.com/watch?v=Lx2d5cgMj5U) | Short and canonical. Likely Godot 3 era, but the concept transfers. |
| F10 | Selection VFX | [Godot 4 Shader VFX: Selection Circle & Danger Zone Effect (Dev Quest)](https://www.youtube.com/watch?v=YLhodhfV-18) | The team-colored selection ring under units and AoE target circles. The WC3 look is a crisp ring on the ground. |
| F11 | Decals | [Decals! But what is it good for?? Godot 4 Feature Preview (Aknakos)](https://www.youtube.com/watch?v=jAMHtxUcBUI) | `Decal` node for selection rings, blight/creep ground, and building footprints. Check the software-renderer cost; a ground-aligned quad may be cheaper. |
| F12 | HP bars | [3D Unit HP Bars with Shaders for an RTS (Nanotech Gamedev)](https://www.youtube.com/watch?v=N69LpNSgnag) | Billboarded, shader-driven HP bars: one draw per unit, no Control nodes. |
| F13 | Pathfinding / avoidance | [How to Navigate units in Godot: Navigation Agents (Nanotech Gamedev)](https://www.youtube.com/watch?v=BGevOhQq1Cw) | `NavigationAgent3D` with dynamic (RVO) avoidance. Set `radius`, `neighbor_distance`, `max_neighbors`, `time_horizon_agents`, `max_speed`, and use the `velocity_computed` signal. |
| F14 | Avoidance (alternative) | [RTS Without Physics Collisions or Navigation Agents (Nanotech Gamedev)](https://www.youtube.com/watch?v=IuS-U3tDQ1c) | Argues for custom separation/steering instead of physics bodies for performance, which matters on our CPU-only container. |
| F15 | Group pathing | [Godot RTS Tutorial Ep. 3: Group Pathfinding (LegionGames)](https://www.youtube.com/watch?v=FRvqBdXMd7Q) | Steering plus a group destination offset (formation spread). Uses older Navigation2D, so port the concepts. |
| F16 | Fog of war | [How I did fog of war without Physics in Godot (Nanotech Gamedev)](https://www.youtube.com/watch?v=pKlEnQUvH9Y) | **Chapters (seen in listing): 00:00 Intro · 00:32 FoW examples · 05:54 The Concepts · 26:58 Code.** Grid/texture-based visibility, no Area3D overlaps. |
| F17 | Fog of war | [How to make Fog of War in Godot 4+ (Sinisperi)](https://www.youtube.com/watch?v=GeD0ZeQfi68) | A Godot 4 implementation. |
| F18 | Fog of war | [Godot: Fog Of War Tutorial in Under 6 Minutes (HeartBeast)](https://www.youtube.com/watch?v=zkMSbQoUd9o) | Code at [uheartbeast/godot-fow-tutorial](https://github.com/uheartbeast/godot-fow-tutorial). 2D, but the "explored vs visible" two-layer idea is exactly WC3's black mask plus grey fog. |
| F19 | Minimap | [Rts in Godot Part 25: RTS Minimap (Nanotech Gamedev)](https://www.youtube.com/watch?v=uZtX4SfP46E) | Minimap node plus shader. Pair it with F16 so the minimap shares the FoW texture. |
| F20 | Minimap | [Setting up a 3D minimap, Godot 4/C# (Mina Pêcheux)](https://www.youtube.com/watch?v=LXzQXoheXAA) | SubViewport plus orthographic camera approach. On software rendering, **prefer a CPU-drawn ImageTexture of dots** over a second 3D viewport. |

---

## G. Key "moments" that define the WC3 feel

These are the micro-experiences to replicate *in function and timing* with our own art, sound and words. Numbers come from the cited sources. "Ref" points to the videos above where you can see or hear the moment.

| # | Moment | What actually happens in WC3 (sourced) | Our original equivalent / implementation note | Ref |
|---|---|---|---|---|
| M1 | **Hero level-up** | "A sound plays and a flash of light appears around the hero", plus "a small flashing overlay" on the hero portrait. Max level 10. XP to reach L2–L10: 200 / 500 / 900 / 1400 / 2000 / 2700 / 3500 / 4400 / 5400. Creep XP falls from 80% (L1) to 0% at L5+. Ultimate at L6. 1 skill point per level. 6 item slots. Max 3 heroes. First hero free, 5 food. ([classic.battle.net Heroes](https://classic.battle.net/war3/basics/heroes.shtml)) | Golden vertical light pillar plus ring burst (about 0.8–1.2 s, unverified target), our own rising chime, and a portrait pulse plus a "+1" skill-point badge on the command card. **Never reuse the WC3 sound.** | B15, A3 |
| M2 | **Hero death** | Global message "<Name> the <Type> (Level N) has fallen". Heroes leave no corpse. Revive at the Altar (cost scales with level: ×(0.40 + 0.10×(L−1)), cap 4×; altar max 550 gold). Revived at the altar with full HP and 100 mana. ([classic.battle.net Heroes](https://classic.battle.net/war3/basics/heroes.shtml)) | Distinctive death scream plus a global banner and minimap ping. The hero dissolves into light (no ragdoll needed, which helps since we have no rigging). An altar "revive" button with a countdown. | B17, A3 |
| M3 | **Day/night cycle** | Full cycle 480 s game time = 240 s day + 240 s night ([Liquipedia "Daytime"](https://liquipedia.net/warcraft/Daytime)). An orb at the top of the UI morphs sun↔moon with a yellowish/bluish glow. **A wolf howl plays at dusk.** Sight shrinks at night (e.g., Felguard 1400 day / 800 night; Sea Giant 1200/800). Night Elves Shadowmeld at night. Some creeps sleep ([classic.battle.net Day/Night](https://classic.battle.net/war3/basics/daynight.shtml), [Wowpedia Felguard](https://wowpedia.fandom.com/wiki/Felguard_(Warcraft_III))). Community notes a smooth sight transition (about 3.2 s for heroes, Hive vision guide, unverified). A dawn rooster call is commonly remembered (unverified). | Two `Environment`/`DirectionalLight3D` presets lerped over about 3 s. A dusk stinger (our own animal call, e.g., an owl or horn) plus a dawn stinger. Night sight multiplier about 0.6 of day. A sun/moon clock widget at top-center. | B7, B8, B1 |
| M4 | **Creep camp sleeping at night** | Most creeps fall asleep at night and won't attack unless disturbed. Attacking, building nearby, or using a nearby neutral building wakes them ([Liquipedia "Daytime"](https://liquipedia.net/warcraft/Daytime)). A floating "Zzz" over sleepers (unverified visual). Pros creep at night specifically to pick fights safely (watch A17/A18). | Sleeping creeps get a slow breathing scale-bob (no rig needed: animate the root transform) plus a "z" particle. They wake on aggro radius ×0.5 or on damage. Camps marked on the minimap by difficulty color (green/orange/red, unverified as WC3 behavior; good design regardless). | A17, A18, A19 |
| M5 | **Upkeep thresholds** | Food 0–50: no upkeep (100% gold). 51–80: low upkeep (70%). 81–100: high upkeep (40%). Max 100 food ([classic.battle.net Upkeep](https://classic.battle.net/war3/basics/upkeep.shtml)). RoC originally used 0–40 / 41–70 / 71–90 ([Hive classic mirror](https://classic.hiveworkshop.com/war3/basics/upkeep.shtml)). Lumber is not taxed (unverified). | A top-bar text label changes "No / Low / High Upkeep" with color (unverified that WC3 colors it; we should). Play a soft warning tick when crossing a threshold. Keeps armies small, which makes each unit matter. | A9, A15 |
| M6 | **Gold mine / mining loop** | Human/Orc workers carry **10 gold per trip** ([Warcraft Wiki Peasant](https://warcraft.wiki.gg/wiki/Peasant_(Warcraft_III))). A mine is "low" at 1,500 gold: an advisory warning plus a **minimap ping**, then a message when it collapses ([classic.battle.net Resources](https://classic.battle.net/war3/basics/resources.shtml)). NE entangles the mine and Wisps drain it. Undead haunts it and Acolytes mine "by magic" without carrying (5 per mine). Starting mine about 12,500 gold and ~5 workers to saturate (commonly cited, unverified). | Workers vanish into the mine for about 1 s. Our "gold-mine flash" (as the user remembers it) = a brief emissive pulse on the mine's entrance when a worker enters or exits, plus a soft coin clink when gold is deposited at the hall. Low-mine voice warning plus a minimap ping. | B16 |
| M7 | **Lumber** | 10 lumber per trip base, 20 with the first upgrade, 30 with the second ([Warcraft Wiki Peasant](https://warcraft.wiki.gg/wiki/Peasant_(Warcraft_III))). Chopping trees is a looped chop sound. Trees eventually fall. | A chop SFX loop with 3–4 variations. A tree "falls" (rotate the root and fade), since we have no rig. | B1 |
| M8 | **Building construction** | Four race styles: Human peasants build *from outside*, and extra builders speed it up at extra cost ("Power Build"). Orc peons and NE wisps build *from inside*; the wisp is consumed for Ancients and the Tree of Life. Undead acolytes *summon* and walk away ([Warcraft Wiki Building](https://warcraft.wiki.gg/wiki/Building_(Warcraft_III)), [Liquipedia Buildings](https://liquipedia.net/warcraft/Buildings)). Undead must build on blight. On completion the Peasant says "Job's done" ([Warcraft Wiki Human quotes](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance)). | Our factions should each get a **different construction verb**: scaffold rising, grown from roots, summoned from a rune circle. Use the GLB plus a shader `build_progress` uniform (a dissolve/clip-plane from the ground up) plus our own "work complete" line. | B11, B12, A6 |
| M9 | **Town Hall bell (Call to Arms)** | Ringing the bell turns nearby Peasants into Militia for 42.5 s (patch 1.36.1; formerly 40 s; Warcraft Wiki says 45 s), then they revert. "Back to Work" ends it early ([Liquipedia Town Hall](https://liquipedia.net/warcraft/Town_Hall), [Warcraft Wiki Militia](https://warcraft.wiki.gg/wiki/Militia_(Warcraft_III))). | A loud, recognizable alarm SFX audible map-wide to the owner. Workers swap weapon props (mesh swap, no rig) and gain a timed buff bar. | A5, A12 |
| M10 | **Unit acknowledgements** | Per-unit VO categories: **Ready** (on training, 1 line), **What** (select, ~4), **Yes** (order, ~4), **Attack** (~3–4), **Warcry** (1), **Pissed** (repeated clicks, 4–8 easter-egg lines), plus Job complete for workers. Peasant = 20 lines, Footman = 17 ([Warcraft Wiki Human quotes](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance)). | Budget about 17–20 original lines per unit, generated with ElevenLabs TTS / Seed Audio in distinct voices. A "pissed" counter triggers after N rapid clicks (WC3 threshold unverified, try 5). Cap simultaneous VO to 1 per player and debounce. | B13, B14 |
| M11 | **Building "voice" on select** | Each building has a characteristic one-shot when clicked: a bell, an anvil clang, a chant (listen to B11/B12). | One distinctive SFX per building type (about 1 s), plus a 2–3 frame highlight pulse. | B11, B12 |
| M12 | **Aura feedback** | Units under a hero aura show a **blue highlight at their feet** (flying units are affected but don't display it) ([classic.battle.net Heroes](https://classic.battle.net/war3/basics/heroes.shtml)). | A small team-tinted ground decal under affected units. | A7 |
| M13 | **Order confirmation ping** | Right-click ground gives a small animated marker at the target. Attack-move or attack-target gives a distinct marker/flash (WC3 specifics unverified; watch A16). | Green 3D "move" chevrons and a red "attack" ring. Selected units' rings briefly flash. See F6 Part 4. | A16, F6 |
| M14 | **Minimap pings / alerts** | Low-mine ping (sourced in M6). Attack alerts ("under attack") with a minimap flash (unverified wording). | Red ping plus a VO line, with a cooldown of about 10–15 s per alert type (unverified target; tune it). | A9 |
| M15 | **Item drops from creeps & shops** | Creeps drop items. Heroes carry 6 (sourced). Neutral shops, taverns and mercenary camps sit on the map (see C3, the neutrals comparison). | A glinting item on the ground plus a drop chime. Neutral buildings are the first assets to generate with Krea (cheap, high impact). | C3, A17 |
| M16 | **Cutscene grammar** | In-engine letterbox plus a talking portrait in the bottom-left, with subtitles. | Cheap with our assets: a CanvasLayer letterbox plus a portrait video/loop and a text box. | B4 |
| M17 | **Camera** | WC3's default game camera is about 1650 distance, 304° angle of attack (≈ −56° pitch), 70° FOV (World Editor defaults; **unverified, from memory**). Scroll zoom is limited, and the camera never goes fully top-down. | Start Godot `Camera3D` at about −56° pitch and 70° vertical FOV (Godot uses vertical FOV, so convert if needed), with a narrow zoom range. Verify against B1/A1 screenshots. | A1, B1 |

### Measuring protocol (use while watching)

For A1/A5/A7 and B1, log with a stopwatch at 0.25× playback:
1. Time from click to voice-line onset.
2. Melee attack wind-up (animation start → hit spark).
3. Hero level-up FX duration.
4. Day→night light transition duration.
5. Units on screen in the biggest fight.
6. Seconds between a creep camp aggroing and its first death.

Put the numbers in `docs/research/feel-metrics.csv` (to be created by the design lead). They become our tuning targets.

---

## H. IP guardrails (what we take vs what we never take)

- **Take:** timing, structure (voice-line categories, upkeep tiers as a *concept*, day/night length as a *tuning ratio*), camera framing, readability principles, UI layout *conventions* (portrait, command grid, minimap bottom-left are genre-wide).
- **Never take:** audio files, voice lines or close paraphrases ("Job's done", "Ready for action"), music motifs, unit/hero/faction names (Footman, Peon, Acolyte, Blademaster, etc.), Blizzard UI frame art and icons, the gold-and-stone UI chrome shapes, maps or map names, logos. Don't feed WC3 screenshots into Krea as style references. Describe styles in words instead.
- AI-generated VO should use original voices. Never clone a WC3 voice actor.

---

## Sources

**Videos (YouTube; title and channel verified via oEmbed on 2026-10-16)**
- [WCG 2008 GF Final, Round 1](https://www.youtube.com/watch?v=4gH_BFhjqwg) · [Round 2](https://www.youtube.com/watch?v=Ldx-u8coJQw) · [Round 3](https://www.youtube.com/watch?v=CjskE1xU54s) · [WCG 2010 GF Final, Set 3](https://www.youtube.com/watch?v=GQRV_HXjhes)
- [Yuwan Cup GF Moon vs Infi](https://www.youtube.com/watch?v=Lot6N4doe8Q) · [Show Cup #34 Happy vs Infi](https://www.youtube.com/watch?v=c_RivjkBo7Q) · [Happy vs Lyn TeD Cup 17](https://www.youtube.com/watch?v=4ckacR_3CFg) · [Happy vs Lyn TeD Cup 19](https://www.youtube.com/watch?v=zEvs8ramsOk) · [Happy vs Lyn cast by Grubby](https://www.youtube.com/watch?v=kmwV6WWGE2g)
- [Moon vs SoK (Grubby)](https://www.youtube.com/watch?v=PpYx1FMVTBc) · [Moon vs Sok BetBoom](https://www.youtube.com/watch?v=ihb4Oizqu28) · [Grubby vs ToD W3C](https://www.youtube.com/watch?v=fZyIhW2r1Is) · [MYM Grubby vs Moon RN34](https://www.youtube.com/watch?v=qNiy7YFS10I) · [Moon interview](https://www.youtube.com/watch?v=u3NO1nfneCM)
- [Never played WC3? (Grubby)](https://www.youtube.com/watch?v=5ygNDJdUVnY) · [Interface: Hotkeys & Control Groups](https://www.youtube.com/watch?v=QGwAUV4bdIw) · [Early Game: Creeping & Build Orders](https://www.youtube.com/watch?v=YMUTzguoT3o) · [Importance of Creeping](https://www.youtube.com/watch?v=jWnalz1L0bM) · [Planning Your Route](https://www.youtube.com/watch?v=k-gCz2MLW8o) · [Creeping guide Part II](https://www.youtube.com/watch?v=5ccoajNlgYo) · [Getting Started (WTii)](https://www.youtube.com/watch?v=EDv2lcgEEA0)
- [RoC Human Campaign longplay](https://www.youtube.com/watch?v=53Ot4lq6YsY) · [RoC Undead Campaign longplay](https://www.youtube.com/watch?v=AQIiQHvLAGQ) · [The Culling](https://www.youtube.com/watch?v=R4eom7ZUz1c) · [WC3 Movie (Original)](https://www.youtube.com/watch?v=LMPgM1IIk7c) · [RoC Intro Cinematic](https://www.youtube.com/watch?v=uAKPumG-6J4) · [Human Intro "The Warning"](https://www.youtube.com/watch?v=mi4BApIqsDA)
- [Day night cycle short](https://www.youtube.com/watch?v=JvDIC7BZDVk) · [WC3 Light Editor](https://www.youtube.com/watch?v=Yup1xH4Gmw8) · [Orcs Music & Ambience](https://www.youtube.com/watch?v=d-HYwNeJRQM) · [Blackrock & Roll](https://www.youtube.com/watch?v=uyx5AYHI2Vs) · [Rise of the Ancients](https://www.youtube.com/watch?v=nxiGNossTLg)
- [Human Building Sounds](https://www.youtube.com/watch?v=3wHMAluEC6g) · [Undead Building Sounds](https://www.youtube.com/watch?v=WHwDTfF8qdo) · [Footman Sounds](https://www.youtube.com/watch?v=KgOswctVGpA) · [Orc Quotes](https://www.youtube.com/watch?v=MXgr6SYYNZM) · [Human Funny Quotes](https://www.youtube.com/watch?v=QiwiuDW52hY) · [Level up sound](https://www.youtube.com/watch?v=r6v8zgsXJrU) · [Gold mine](https://www.youtube.com/watch?v=lD55CrlRPl0) · [Hero death sounds tier list](https://www.youtube.com/watch?v=U6ZrCOARhZc) · [Secrets in Icons & Sounds](https://www.youtube.com/watch?v=WzLnOyWTZsA)
- [Reforged vs Classic (Nick930)](https://www.youtube.com/watch?v=TUXjHKh2hpY) · [3.0 Graphics Comparison](https://www.youtube.com/watch?v=k0dJga13D1Q) · [3.0 Neutrals Comparison](https://www.youtube.com/watch?v=NV8YGW6zVCw) · [Human Models Comparison](https://www.youtube.com/watch?v=qU2TlJtBCMo) · [Night Elves Comparison](https://www.youtube.com/watch?v=41PvXoiNWWw) · [Undeads Comparison](https://www.youtube.com/watch?v=yxWHNVYiKOM) · [Demons Comparison](https://www.youtube.com/watch?v=UZgSUMt3_uM) · [ComputerBase comparison](https://www.youtube.com/watch?v=TeGv40-PoKM) · [Reforged envs + Classic HD (Grubby)](https://www.youtube.com/watch?v=FcbklFRr7jc) · [Ambient Occlusion PTR](https://www.youtube.com/watch?v=zWq-Q94ejrM) · [Xander Dorn essay](https://www.youtube.com/watch?v=-HD6E42Su8Q) · [Reforged 2.0 review (Costin)](https://www.youtube.com/watch?v=YTLVMBGF0Fg) · [HUGE WC3 changes (WTii)](https://www.youtube.com/watch?v=SeiIkWfRUW8) · [2.0 Menus critique](https://www.youtube.com/watch?v=9wefqiem_-A)
- [C&C Classic Game Postmortem](https://www.youtube.com/watch?v=rIXK3fRx4Zo) · [Game Masters: Pardo & Metzen](https://www.youtube.com/watch?v=Jsl6aKj4JW8) · [Samwise Didier (CHM)](https://www.youtube.com/watch?v=hCx6lDSlZ40) · [Samwise WonderCon 2015](https://www.youtube.com/watch?v=inLg4b38pY8) · [WC3 Cinematics (GI)](https://www.youtube.com/watch?v=Jgndut9nY0Q) · [WC3 Soundtrack (GI)](https://www.youtube.com/watch?v=ouNEzATaDMs) · [Sound of WoW (WoW Archives)](https://www.youtube.com/watch?v=gy4ePZnvuKc) · [Renew Interest in the RTS (GI)](https://www.youtube.com/watch?v=x-H99TnQnl0) · [Reforged development details (GI)](https://www.youtube.com/watch?v=vipXWdVic2Q) · [Reforged Devs BlizzCon 2019](https://www.youtube.com/watch?v=_oiRnFGgD_I) · [Level Designer AMA Pt 1](https://www.youtube.com/watch?v=C_v-zonH91s) · [Pt 3](https://www.youtube.com/watch?v=6BDckItrg3Y) · [Forsaken Kingdom What's Next (BlizzCon 2026)](https://www.youtube.com/watch?v=mHKNDO-PTs8)
- [Most Successful RTS (Nixxiom)](https://www.youtube.com/watch?v=rw4yHKcIdyw) · [Killed Its Own Genre (nelvox)](https://www.youtube.com/watch?v=YURF3AbgIw4) · [History of WC3 (WTii)](https://www.youtube.com/watch?v=5D_SbpLsMDI) · [WC3 Retrospective (acritical)](https://www.youtube.com/watch?v=zMBTnT99WyQ) · [Why Does WoW Look Like This](https://www.youtube.com/watch?v=ptwQWuDsExQ) · [Secrets of Game Feel and Juice (GMTK)](https://www.youtube.com/watch?v=216_5nu4aVQ) · [Experiential Unit Design (Stardock)](https://www.youtube.com/watch?v=nVzVL7zo2MI)
- [Stormgate: difference a year makes](https://www.youtube.com/watch?v=mZoMdLAcq24) · [Stormgate Developer Update (IGN)](https://www.youtube.com/watch?v=GvFPchpfP8M) · [Stormgate Engine/Art Reveal](https://www.youtube.com/watch?v=VkLE8FQ9nQQ) · [Stormgate Patch 0.3](https://www.youtube.com/watch?v=kN3ljseDB8w) · [Stormgate lead designer](https://www.youtube.com/watch?v=O14znz-kKKA) · [Godsworn (perafilozof)](https://www.youtube.com/watch?v=6sSoYO-vGB0) · [Godsworn EA (Bandanner)](https://www.youtube.com/watch?v=lp5MoI4Kl_8) · [The Scouring](https://www.youtube.com/watch?v=1CHc3B10Ds4)
- [Godot RTS Devlog 001](https://www.youtube.com/watch?v=KicnrR9CXXo) · [Devlog 002](https://www.youtube.com/watch?v=l9Ba3HrTKI0) · [Composition System](https://www.youtube.com/watch?v=MRwM3LOal5o) · [I release my Godot RTS](https://www.youtube.com/watch?v=UMyWbCSZqI0) · [Unit Movement and Armies](https://www.youtube.com/watch?v=2F0p1DNN1a0) · [Phantawalker demo](https://www.youtube.com/watch?v=qp6W4SLU7W8) · [3D FoW recap (ScyDev)](https://www.youtube.com/watch?v=VY2I7XdvsMY)
- [RTS from scratch 4.5+ Part 1](https://www.youtube.com/watch?v=IJAJ_d_JaeY) · [RTS Camera Part 1](https://www.youtube.com/watch?v=t-tkFxhpiCs) · [Camera Zoom](https://www.youtube.com/watch?v=MOoL7a4G46g) · [Camera Rotation](https://www.youtube.com/watch?v=EHYVbS2sWjQ) · [Smooth camera 4.3](https://www.youtube.com/watch?v=ssTa8LgeO3M) · [LegionGames Ep 1](https://www.youtube.com/watch?v=JXvNOnmBgRg) · [LegionGames Ep 3](https://www.youtube.com/watch?v=FRvqBdXMd7Q) · [Selection Part 2](https://www.youtube.com/watch?v=f6SXH_27kNA) · [Selection Part 4](https://www.youtube.com/watch?v=ysV8GnFtJkc) · [Selection Operations](https://www.youtube.com/watch?v=BnmNrGGBIPk) · [Control Units & Groups (16BitDev)](https://www.youtube.com/watch?v=eQjBLFKamms) · [Drag-select (KidsCanCode)](https://www.youtube.com/watch?v=Lx2d5cgMj5U) · [Selection Circle Shader (Dev Quest)](https://www.youtube.com/watch?v=YLhodhfV-18) · [Decals preview](https://www.youtube.com/watch?v=jAMHtxUcBUI) · [3D HP bars](https://www.youtube.com/watch?v=N69LpNSgnag) · [Navigation Agents](https://www.youtube.com/watch?v=BGevOhQq1Cw) · [RTS without physics/agents](https://www.youtube.com/watch?v=IuS-U3tDQ1c) · [FoW without physics](https://www.youtube.com/watch?v=pKlEnQUvH9Y) · [FoW Godot 4+ (Sinisperi)](https://www.youtube.com/watch?v=GeD0ZeQfi68) · [FoW under 6 min (HeartBeast)](https://www.youtube.com/watch?v=zkMSbQoUd9o) · [RTS Minimap Part 25](https://www.youtube.com/watch?v=uZtX4SfP46E) · [3D minimap (Mina Pêcheux)](https://www.youtube.com/watch?v=LXzQXoheXAA)

**GDC Vault (pages fetched)**
- [Making a Standard: Blizzard Design Philosophies (Rob Pardo)](https://www.gdcvault.com/play/1012291/Making-a-Standard-(and-Trying)
- [Rules of Engagement: Blizzard's Approach to Multiplayer Game Design (Rob Pardo)](https://www.gdcvault.com/play/315/Rules-of-Engagement-Blizzard-s)
- [The Game Design of STARCRAFT II: Designing an E-Sport (Dustin Browder)](https://www.gdcvault.com/play/1014488/The-Game-Design-of-STARCRAFT)
- [Visual Effects Summit: World of Warcraft VFX Pillars (Sarah Carmody)](https://gdcvault.com/play/1029418/Visual-Effects-Summit-World-of)
- [Classic Game Postmortem: Command & Conquer](https://www.gdcvault.com/play/1025777/Classic-Game-Postmortem-Command-Conquer)

**Podcasts, articles and mechanics references**
- [Designer Notes: Rob Pardo Part 1](https://www.idlethumbs.net/designernotes/episodes/rob-pardo-part-1) · [Part 2](https://www.idlethumbs.net/designernotes/episodes/rob-pardo-part-2) · [Designer Notes announcement post](https://www.designer-notes.com/?p=859)
- [Game Informer: Warcraft III was almost "Warcraft Legends"](https://www.gameinformer.com/b/news/archive/2014/11/03/warcraft-iii-was-almost-a-non-traditional-rts-called-warcraft-legends.aspx)
- [Inven Global: Thrice denied: Moon and the GOAT's futile quest for WCG gold](https://www.invenglobal.com/articles/15931/thrice-denied-moon-and-the-goats-futile-quest-for-wcg-gold)
- [GamingBolt: WC3 Reforged, 13 ways it's different](https://gamingbolt.com/warcraft-3-reforged-13-ways-its-different-from-warcraft-3-classic) · [Wccftech: Reforged vs Original comparison videos](https://wccftech.com/warcraft-3-reforged-comparison-video/)
- [classic.battle.net: Heroes](https://classic.battle.net/war3/basics/heroes.shtml) · [Day/Night](https://classic.battle.net/war3/basics/daynight.shtml) · [Upkeep](https://classic.battle.net/war3/basics/upkeep.shtml) · [Resources](https://classic.battle.net/war3/basics/resources.shtml) · [Hive classic mirror: Upkeep](https://classic.hiveworkshop.com/war3/basics/upkeep.shtml)
- [Liquipedia: Daytime](https://liquipedia.net/warcraft/Daytime) · [Liquipedia: Buildings](https://liquipedia.net/warcraft/Buildings) · [Liquipedia: Town Hall](https://liquipedia.net/warcraft/Town_Hall)
- [Warcraft Wiki: Quotes of Warcraft III / Human Alliance](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance) · [Peasant (WC3)](https://warcraft.wiki.gg/wiki/Peasant_(Warcraft_III)) · [Building (WC3)](https://warcraft.wiki.gg/wiki/Building_(Warcraft_III)) · [Militia (WC3)](https://warcraft.wiki.gg:443/wiki/Militia_(Warcraft_III)) · [David Fried](https://warcraft.wiki.gg/wiki/David_Fried)
- [Wowpedia: Felguard (Warcraft III)](https://wowpedia.fandom.com/wiki/Felguard_(Warcraft_III)) · [Hive Workshop: Vision guide](https://www.hiveworkshop.com/threads/vision-guide.290769/)
- [lampe-games/godot-open-rts (GitHub)](https://github.com/lampe-games/godot-open-rts) · [Open RTS on itch.io](https://lampe-games.itch.io/open-rts) · [uheartbeast/godot-fow-tutorial](https://github.com/uheartbeast/godot-fow-tutorial) · [Godsworn on Steam](https://store.steampowered.com/app/1328990/Godsworn)
