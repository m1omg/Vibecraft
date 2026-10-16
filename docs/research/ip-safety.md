# IP safety: making a game "like Warcraft III" (for Vibecraft)

*Research date: 2026-10-16. Audience: everyone on the team who writes code, data or text, prompts an AI model, or picks a name.*

> **This is not legal advice.** It is an engineering-grade summary of public sources, written so the team can avoid obvious
> problems. Before a public release (store page, trailer, crowdfunding, paid build), have an IP/trademark attorney in your
> jurisdiction review the name and the final art.

**How this was researched.** The shared web-search budget for this run was used up before this task started. So every
source below was **fetched directly** (court-case articles, the US Copyright Office, the Blizzard EULA, tool terms of
service). Items marked **(background, not fetched)** come from general knowledge and should be checked before anyone
relies on them. **No trademark clearance search for "Vibecraft" was performed.** §4 explains how to do one.

**Fact-check pass (2026-10-16).** The case citations, dates and quotes in §1.2, the Blizzard EULA wording, the US Copyright Office
quotes (Part 2 report and Circular 33), the USPTO wording and the Krea and ElevenLabs terms were re-checked against the fetched sources.
Corrections: the EULA "will not create any work" clause is §2.A.ix, not §2.B.ix; *Tetris* involved no 2D-to-3D change; the *Atari*
injunction was a preliminary injunction ordered on appeal. *Thaler* (D.C. Cir.), the Nemesis patent and the Midjourney suits are now verified.

Related project docs that already contain shorter guardrails, consistent with this one:
`gameplay-mechanics.md` §12, `visual-art-direction.md` §7.6, `audio-direction.md` §8, `video-references.md` §H,
`architecture.md` rule 6.

---

## 0. TL;DR (the 12 rules)

1. **Mechanics are free; expression is not.** Copyright never covers "any idea, procedure, process, system, method of
   operation, concept, principle" (17 U.S.C. §102(b)). You may copy how WC3 *plays*. You may not copy how it *looks,
   sounds or reads*.
2. **"Look and feel" can still infringe even with every asset redrawn.** *Tetris v. Xio* (2012) found infringement where the
   clone claimed to copy only the rules but reproduced Tetris's visual expression. *Spry Fox v. Lolapps/6waves* (2012) let a claim
   proceed where the clone changed the theme (a yeti for a bear, snow for a meadow) but kept the same expressive choices.
   The test is how the whole thing looks to a layman. The *Spry Fox* court said it "must focus on what is similar, not what is different".
3. **Zero Blizzard names.** No Warcraft, Blizzard, Azeroth, Horde, Alliance, Scourge, Sentinels, Night Elf, Peon, Peasant-who-says-"Job's done",
   Grunt, Acolyte, Wisp, Blademaster, Death Coil, Bladestorm, Starfall, Lost Temple, and so on. See the list in §2.1.
4. **Zero Blizzard lines or paraphrases.** No "Work work", "Zug zug", "Job's done", "Ready to work", "Something need doing?",
   "Me not that kind of orc", "Stop poking me". The Blizzard EULA explicitly claims the "catch phrases of Game characters".
5. **Never touch WC3 data.** No MPQ/CASC extraction, no World Editor maps, no Hive Workshop rips, no screenshots used as
   AI inputs. The EULA forbids copying, reverse engineering and "mining". Blizzard enforced it in court (*bnetd*, 2004/2005).
6. **No Blizzard-style trade dress.** A bottom console, a minimap at bottom-left and a 4×3 command card are generic and functional.
   The gilded or gargoyle-and-skull frame art, race-skinned consoles, the gauntlet cursor and the ornate day/night orb are expression. Ours must look different.
7. **No copied maps.** Level layouts are protectable expression (*Micro Star v. FormGen*, 1998). Design our maps from
   principles, never by tracing a WC3 ladder map.
8. **Factions must not map 1:1 onto Human/Orc/Undead/Night Elf.** Orcs, elves, undead and humans are free folklore and genre concepts.
   Blizzard's *specific* designs, palettes, emblems and signature combinations are not. Each faction must pass the distinctness rubric in §3.2.
9. **Prompt hygiene.** No IP names, artist, composer or voice-actor names, or Blizzard screenshots in any prompt or reference input,
   negative prompts included. Log every generation in `docs/asset-ledger.md`.
10. **"Vibecraft" is high-risk as a public title.** In June 2003 Blizzard sent a cease-and-desist to the open-source RTS *Freecraft*
    because the name "could cause confusion with the names StarCraft and Warcraft". The project renamed itself Stratagus.
    Treat "Vibecraft" as an **internal codename** until a clearance search and legal review are done.
11. **Our AI-only assets get thin protection, but they can still infringe.** The US Copyright Office says "prompts alone" do
    not make you the author. Human selection, arrangement and modification can be protected. Krea and ElevenLabs disclaim
    responsibility for infringing outputs, so the risk is ours.
12. **Studying is fine; transplanting is not.** Watching WC3 videos and reading wikis for timings and numbers is what
    the research docs do, and it is fine. Copying assets, text, layouts or distinctive designs is not.

---

## 1. Legal map: what is free and what is protected

### 1.1 Copyright: the idea/expression line (US, with EU notes)

**Not protected by copyright** (free to use):

| Category | Basis | What it means for us |
|---|---|---|
| Ideas, rules, systems, methods of operation | 17 U.S.C. §102(b); US Copyright Office Circular 33 (rev. 03/2021); *Lotus v. Borland* (menus as "method of operation") | Gold/lumber economy, upkeep, hero XP and levels, creeps, day/night, armor/attack tables, control groups, hotkeys, fog of war |
| Genre conventions and scènes à faire | *Data East v. Epyx* (1988); *Atari v. Philips* (1982) | Elements that follow from "a fantasy RTS": town halls, barracks, workers, mines, healers, siege units, flyers |
| Names, titles, short phrases, catchphrases, slogans, character names | Circular 33: "Words and short phrases, such as names, titles, and slogans, are uncopyrightable", including "The name of a character" and "Catchwords or catchphrases" | Copyright is *not* the issue for single names. **Trademark, contract (the EULA) and overall similarity are.** See §1.3 and §2 |
| Familiar symbols and simple shapes | Circular 33, "Familiar Symbols and Designs" (arrows, stars, common shapes) | A shield icon, sword icon or arrow cursor is fine as a concept |
| Software functionality, programming languages, file formats (EU) | CJEU C-406/10 *SAS Institute v WPL* (Grand Chamber, 2 May 2012): neither "the functionality of a computer program nor the programming language" nor data file formats are protected. Licensed users "may observe, study, or test the functioning of the program" | Re-implementing WC3-like behaviour in our own GDScript/C# code is fine. Copying Blizzard code, data files or manuals is not |
| Facts and raw numbers | *Feist* line of cases (background, not fetched) | Individual stats (e.g., "10 gold per trip") are facts. Copying the *entire* balance sheet unit-for-unit is a gray zone and reads as a re-skin (see `gameplay-mechanics.md` §12) |

**Protected by copyright** (never copy):

- **Art:** models, textures, concept art, icons, portraits, UI frame art, cursors, loading screens, terrain tiles, VFX sprites.
- **Animation:** specific animation sequences and timing curves taken from files.
- **Audio:** sound recordings (the files) *and* musical compositions (melodies and motifs), voice performances.
- **Code and data files** (in the EU the program code itself, under the Software Directive), including JASS/Lua scripts and map files.
- **Text:** tooltips, lore, campaign scripts, quest text, manuals. *SAS v WPL* found the manual infringed by "substantially reproducing its language".
- **Characters as expressive designs:** the "gobbler" and ghost designs in *Atari v. Philips*. The "wild creature" role and the object hierarchy in *Spry Fox*.
- **Levels and maps:** *Micro Star v. FormGen* treated user-made Duke Nukem 3D level files as infringing derivative works ("surely sequels").
- **Overall selection and arrangement / look and feel:** *Tetris v. Xio*. The court found protected expression in the 20×10 board, the
  ghost piece, the next-piece display, the colour change on landing and the board filling at game over. It warned that "if one has to squint
  to find distinctions only at a granular level", the works are likely substantially similar.

**EU and UK notes** (background, not fetched, verify before relying on them):

- *Bezpečnostní softwarová asociace* (CJEU C-393/09, 2010): a graphical user interface is not protected as a *computer program*.
  It **can** be protected as an ordinary work if it is "its author's own intellectual creation". Elements dictated only by technical function are excluded.
  For us: **the functional layout is free; the visual design of the HUD is protectable.**
- *Nintendo v PC Box* (CJEU C-355/12, 2014): video games are "complex matter" whose graphic and sound elements are protected as works in their own right.
- *Nova Productions v Mazooma Games* ([2007] EWCA Civ 219, UK): general ideas and rules of a game, and a few similar frames, were not infringement.
  This is the UK counterpart of the US idea/expression line.
- Some EU states also have unfair-competition rules against "slavish imitation" (e.g., Germany's supplementary protection under the UWG),
  which can apply even without copyright. This is another reason not to ship a near-replica of WC3's look.
- **EU registered and unregistered designs** can cover GUIs and icons. This is another reason to keep our UI art original.

**Patents** (background, not fetched): game mechanics *can* be patented. Any patent on a 2002-era WC3 mechanic would be
filed by about 2002–2003 and expired after its 20-year term. **Newer** systems from recent games may still be patented
(e.g., Warner Bros.' "Nemesis system" patent, US 10,926,179 B2, granted Feb 2021). Low risk for classic-RTS mechanics.
Do not copy a recent game's signature system wholesale without checking.

### 1.2 The key cases and what each one teaches us

| Case | Court / year | What happened | Lesson for Vibecraft |
|---|---|---|---|
| *Atari v. North American Philips* (Pac-Man vs K.C. Munchkin) | 7th Cir., 2 Mar 1982, 672 F.2d 607 | Maze-chase idea, scoring, dots and tunnels were unprotected. The gobbler and ghost **character designs** were protected. "It is enough that substantial parts were lifted." The appeals court reversed the denial and ordered a preliminary injunction | The genre is free. The iconic **characters** are not. Do not make "our Grunt" or "our Abomination" |
| *Data East v. Epyx* (Karate Champ vs World Karate Championship) | 9th Cir., 30 Nov 1988, 862 F.2d 204 | 15 shared features stemmed from karate itself or hardware limits. "No substantial similarity of expression will be found when the idea and its expression are inseparable." Infringement reversed | Things every fantasy RTS must have (halls, workers, mines, a minimap) are scènes à faire. Our protection comes from staying at that level |
| *Lotus v. Borland* | 1st Cir. 1995, 49 F.3d 807; aff'd 4–4 by an equally divided Supreme Court, 516 U.S. 233 (1996) | The menu command hierarchy is an uncopyrightable "method of operation", like VCR buttons | Hotkey schemes, command-card *positions* and control conventions are free. The 4–4 split set no national precedent |
| *Micro Star v. FormGen* | 9th Cir., 11 Sep 1998, 154 F.3d 1107 (Kozinski) | About 300 user-made Duke Nukem 3D levels sold on CD were infringing derivative works. They told new stories with FormGen's characters | Maps and level layouts are expression. Never rebuild Lost Temple or Turtle Rock, even in our art style |
| *Davidson & Associates v. Jung* (Blizzard v. bnetd) | E.D. Mo., Sep 2004; 8th Cir. Sep 2005, 422 F.3d 630 | Blizzard won. The EULA's ban on reverse engineering was enforceable (not preempted), and bnetd violated the DMCA | Blizzard litigates, and its EULA has teeth. Never reverse-engineer or extract WC3 files |
| *Tetris Holding v. Xio Interactive* (Mino) | D.N.J., 30 May 2012, 863 F. Supp. 2d 394 (Wolfson, J.) | Xio admitted copying. Rules were free, but the visual expression was copied, so summary judgment and a permanent injunction followed. Trade dress was also infringed (marketing in the same colours and style) | The most important case for us. Redrawing is not enough if the overall visual choices match. Marketing that mimics the original's dress adds trademark exposure |
| *Spry Fox v. Lolapps* (Triple Town vs Yeti Town) | W.D. Wash., order 18 Sep 2012 (Jones, J.), No. 2:12-cv-00147 | Motion to dismiss denied. The 6×6 grid and coins were functional or scènes à faire. The object hierarchy and the "wild creature" foil were expression. A yeti for a bear and snow for a meadow did not help. Settled Oct 2012; Spry Fox got the rights to both games | **Swapping the skin while keeping the structure of expressive choices still infringes.** Night-elf-but-blue is not original |
| *SAS Institute v World Programming* | CJEU C-406/10, 2 May 2012; UK High Court [2013] EWHC 69 (Ch) | Functionality, language and file formats are not protected. The manual's wording was infringed | Re-implement behaviour freely. Never copy text (tooltips, manuals, lore) |
| Valve vs Blizzard over "DOTA" | Opposition filed Nov 2011; agreement 11 May 2012 | Blizzard opposed Valve's "Dota" filing, "citing Blizzard's ownership of both the Warcraft III World Editor and DotA-Allstars, LLC". Valve kept commercial rights. Blizzard kept non-commercial use and renamed its game Blizzard All-Stars (later *Heroes of the Storm*, 17 Oct 2013) | Names coined around WC3 become valuable marks that Blizzard fights over. Anything built with WC3's editor gets entangled with Blizzard's ownership claims |
| Blizzard & Valve v. Lilith Games / uCool | US federal court (N.D. Cal. inferred from Judge Charles R. Breyer, unverified), c. 2015–2017 | Suits over mobile games (uCool's released 2014) using Dota/WC3-derived characters. Judge Breyer denied uCool's motion for summary dismissal. Blizzard later moved to dismiss its claims against uCool and Lilith with prejudice (outcome and terms not in the fetched source) | Blizzard actively enforces against games that reuse WC3-lineage characters |
| Blizzard vs *Freecraft* | Cease-and-desist, June 2003 | Blizzard said the name "Freecraft could cause confusion with the names StarCraft and Warcraft" and that some engine ideas were too close to Warcraft II. The project halted on 20 Jun 2003 and returned in 2004 as **Stratagus** | **Direct precedent for our name.** See §4 |
| Bethesda vs Mojang over "Scrolls" | Interim ruling Oct 2011; settled Mar 2012 | Mojang could keep the name but agreed **not to register it as a trademark**, and the game could not compete with *The Elder Scrolls*. Later renamed *Caller's Bane* (2018) | Even a single common word close to a famous game mark draws a fight. A weak, unregistrable title is a business problem |

### 1.3 Trademark and trade dress (the real risk for names)

- **Trademarks protect source identifiers**, not creativity. "Warcraft", "StarCraft", "Blizzard", "Battle.net" and "Reforged" are Blizzard marks
  in the video-game classes (Nice class 9 software, class 41 online entertainment). Registration details are unverified here, but famous status is not in doubt.
- **Likelihood of confusion** (USPTO): marks need not be identical. They can conflict if "similar in sound, appearance, or meaning, or could create
  a similar commercial impression". The goods also count: they conflict if "identical, similar or competitive". **A fantasy RTS is the exact same goods as Warcraft.**
- **Famous marks** also get anti-dilution protection, which does not require confusion (background, not fetched).
- **Trade dress** can protect a product's overall look if it is **non-functional** and **distinctive**. For product design, secondary meaning is required
  (US: *Wal-Mart v. Samara*, *TrafFix*; background, not fetched). In *Tetris* the court found Mino's marketing used the same colours and style and was likely to confuse.
  For us: the layout and readability choices are functional and free. Blizzard's ornament style, logo treatment and box/key-art style are not.
- **Nominative use** ("for fans of classic 2000s RTS") is generally safer than naming the product. **Do not put "Warcraft" in our store page,
  tags, ad keywords, trailer titles or metadata.** This is a policy choice for safety, not a statement that every mention is illegal.

### 1.4 Contract: the Blizzard EULA (last updated 21 Mar 2024)

Anyone on the team who installed WC3 or Battle.net agreed to it. Key points from the fetched text:

- Blizzard claims ownership of "The names, likenesses, inventories, and catch phrases of Game characters" (§2.A.i.3),
  of locations, artwork and animations, of themes, concepts, stories and storylines, and of "All sounds, musical compositions, recordings, and sound effects".
- Users may not "Copy or reproduce … translate, reverse engineer" the platform (§1.C.i), may not use software that "intercepts, collects, reads, or 'mines'"
  information (§1.C.vi), and "will not create any work based on the Platform" (§2.A.ix; the EULA has no §2.B).
- **Custom games** made with Blizzard's "Game Editor(s)" "are and shall remain the sole and exclusive property of Blizzard" (§1.D.ii.1). The Reforged
  "Custom Game Acceptable Use Policy" drew public criticism in Jan 2020 for the same ownership position.
- **Practical consequence:** never prototype a Vibecraft map, unit or script in the WC3 World Editor, and never import anything from a WC3 install.
  A contract claim does not need copyright to succeed (*bnetd*).

### 1.5 AI-generated assets: ownership and liability

- **US Copyright Office, *Copyright and Artificial Intelligence, Part 2: Copyrightability* (29 Jan 2025):**
  - "prompts alone do not provide sufficient human control to make users of an AI system the authors of the output".
  - A human may "select or arrange AI-generated material in a sufficiently creative way", or "modify material originally generated by AI technology"
    enough to be protected. That covers the whole work, "although not the AI-generated material alone".
  - It relies on *Thaler v. Perlmutter*, 687 F. Supp. 3d 140 (D.D.C. 2023), on human authorship. The D.C. Circuit affirmed on 18 Mar 2025 (No. 23-5233; opinion fetched).
  - **For us:** raw Krea outputs are weakly protectable. Our palette remaps, retopology, hand paint-overs, rig/animation work, and the selection and
    arrangement of the whole game add protectable human authorship. **Document those human steps in the ledger.**
- **Our outputs can still infringe.** If a generated unit looks like a Blizzard character, it does not matter that "the AI made it". Big studios
  have sued image-model companies over their outputs: Disney and Universal sued Midjourney for copyright infringement on 11 Jun 2025, and
  Warner Bros. Discovery sued on 4 Sep 2025, citing characters such as Superman and Batman (per Wikipedia's Midjourney article).
- **Krea terms** (fetched; no date shown on the page):
  - Users must not create content that "infringes or violates the intellectual property rights … of any other person".
  - Krea disclaims "copyright compliance" of material; the service is "AS-IS".
  - Commercial use "may be dependent on specific purchases or plans", and Krea "reserves the right to modify the terms of commercial use".
  - **Action:** before release, record which Krea plan was active for each asset and save a copy of the terms in force.
- **ElevenLabs terms** (fetched; "Last Updated: 09 October 2026"):
  - Free users "may only use the Services for non-commercial purposes". Paid users may use them commercially.
  - Users must have "all the rights necessary" for inputs and outputs. Section 10 notes that other users may get the same or similar output.
  - We access ElevenLabs *through Krea*, so confirm which terms govern (Krea's, ElevenLabs', or both) for shipped VO and music. This is unverified.
- **Steam** requires an AI-content disclosure ("AI Content on Steam", Steamworks post; page title verified, but the body and the
  date (reported as Jan 2024, unverified) could not be retrieved by fetch).
  From memory: there are two categories, **pre-generated** (made with AI tools during development) and **live-generated** (made at runtime).
  The developer promises the game will not include illegal or **infringing** content, and the disclosure appears on the store page.
  Verify the current form when creating the Steamworks page.

---

## 2. Red lines for this project

### 2.1 Names (code, data, UI, files, marketing)

Rule: **no Blizzard-coined or Blizzard-associated proper names anywhere in shipped content**, and none in asset filenames or prompts.
Plain dictionary words (soldier, archer, barracks, farm, knight, priest, catapult) are free and used across the genre. **Avoid pairing
them with the WC3 role and look:** a "Peasant" who chops lumber in a blue-and-gold tabard is a re-skin signal even though "peasant" is an English word.

| Category | Never use (non-exhaustive) |
|---|---|
| Trademarks / brands | Warcraft, WC3, StarCraft, Blizzard, Battle.net, Reforged, World of Warcraft, Heroes of the Storm, DotA/Dota, Hearthstone |
| Factions / peoples as branded | Human Alliance, Orcish Horde, Undead Scourge, Night Elf Sentinels, Burning Legion, Forsaken, Blood Elves, Kaldorei, Quel'dorei, Darkspear, Frostwolf |
| World and lore | Azeroth, Lordaeron, Kalimdor, Northrend, Draenor, Outland, Stormwind, Ironforge, Teldrassil, Dalaran, Ashenvale, Silvermoon, the Frozen Throne, the Lich King, Sargeras, Arthas, Thrall, Jaina, Illidan, Tyrande, Uther, Grom |
| Workers / units | Peon, Peasant (as a lumber-chopping worker), Acolyte, Wisp, Grunt, Footman (as blue line infantry), Rifleman, Spell Breaker, Raider, Kodo Beast, Wind Rider, Batrider, Tauren, Headhunter, Ghoul, Crypt Fiend, Abomination, Meat Wagon, Banshee, Frost Wyrm, Huntress, Dryad, Druid of the Claw/Talon, Mountain Giant, Hippogryph, Chimaera, Faerie Dragon, Gryphon Rider, Dragonhawk Rider, Sorceress, Mortar Team, Flying Machine |
| Heroes | Archmage, Mountain King, Paladin, Blood Mage, Blademaster, Far Seer, Tauren Chieftain, Shadow Hunter, Death Knight, Lich, Dreadlord, Crypt Lord, Demon Hunter, Keeper of the Grove, Priestess of the Moon, Warden, Pit Lord, Firelord, Naga Sea Witch, Pandaren Brewmaster, Dark Ranger, Beastmaster, Tinker, Alchemist |
| Buildings | Great Hall/Stronghold/Fortress, Necropolis/Halls of the Dead/Black Citadel, Tree of Life/Ages/Eternity, Ziggurat, Moon Well, Altar of Kings/Storms/Darkness/Elders, Burrow, Ancient of War/Lore/Wind, Haunted Gold Mine, Entangled Gold Mine, Goblin Merchant, Goblin Laboratory |
| Abilities (distinctive coined names) | Holy Light, Divine Shield, Devotion Aura, Storm Bolt, Thunder Clap, Avatar (as the MK ult), Flame Strike, Banish, Siphon Mana, Wind Walk, Mirror Image, Bladestorm, Chain Lightning (as Far Seer kit), Feral Spirit, Shockwave, War Stomp, Endurance Aura, Big Bad Voodoo, Death Coil, Death Pact, Unholy Aura, Animate Dead, Frost Nova, Dark Ritual, Death and Decay, Carrion Swarm, Vampiric Aura, Locust Swarm, Mana Burn, Metamorphosis, Entangling Roots, Force of Nature, Thorns Aura, Tranquility, Searing Arrows, Trueshot Aura, Starfall, Fan of Knives, Shadow Strike, Bloodlust, Unholy Frenzy |
| Items | Claws of Attack, Boots of Speed, Scroll of Town Portal, Tome of Experience, Orb of Frost, Ankh of Reincarnation, Kelen's Dagger, Gem of True Seeing, Potion of Clarity |
| Maps | Lost Temple, Turtle Rock, Twisted Meadows, Echo Isles, Terenas Stand, Amazonia, Gnoll Wood, Secret Valley, Northern Isles, Concealed Hill, Last Refuge |

Generic one-word mechanics such as Blink, Bash, Evasion, Critical Strike, Sleep, Hex and Earthquake are dictionary words used across many
games, so they are legally fine. **Policy:** still give every ability a Vibecraft-flavoured name. Names are cheap, and a list of WC3 names on
a command card is the fastest way to read as a clone.

**Status of the repo today:** `data/*.json` uses "Placeholder …" names only (clean). `tools/texture_tools.py`, `tools/merge_anims.py`,
`tools/render_preview.py` and `tools/process_model.py` use "footman" in usage examples. That is harmless, but rename it to a neutral word
(e.g., `soldier`) so it does not leak into asset filenames.

### 2.2 Voice lines, text and on-screen messages

- **Banned (verbatim or paraphrase):** "Work, work", "Zug zug", "Job's done", "Ready to work", "More work?", "Something need doing?",
  "Me not that kind of orc!", "Stop poking me!", "Dabu", "Lok'tar", "For the Horde!", "For the Alliance!", "Yes, milord", "Right-o",
  "Ready for action". **Rule of thumb:** if a line appears on a Warcraft Wiki "Quotes of Warcraft III" page, or a fan would recognise it, do not use it or a rewording of it.
- **Allowed:** the *categories* (select / acknowledge / attack / annoyed "piss lines" / death / ready). Repeated-click jokes are a genre convention.
  Generic advisories ("Our hall is under attack", "We need more gold") are common phrases. **Still write our own wording**, matched to each faction's voice.
- **Also avoid other Blizzard RTS lines** ("You must construct additional pylons", "Not enough minerals"). They are equally recognisable.
- **Tooltips, lore, campaign text:** written from scratch. Never adapt a WC3 tooltip. *SAS v WPL* is a manual-copying infringement.
- **Hero death / level-up banners:** use our own wording and design, not a reworded "Your hero has fallen".

### 2.3 Characters, factions and visual designs

The genre is free, but Blizzard's specific **designs** are protected. Avoid these signature combinations:

| WC3 signature (do not reproduce) | Why it is risky | Safer direction |
|---|---|---|
| Green-skinned, tusked orcs with oversized spiked pauldrons, red-brown leather, axes; hide-and-bone spiky huts | Iconic Blizzard orc design (Grunt, Peon, Great Hall) | Different skin, material, culture and architecture. If brutes exist, base them on something other than WC3 orcs |
| Blue/white/gold human knights with a lion emblem, kite shields, gryphon riders, steepled stone halls | Alliance colour/emblem/silhouette set | Different heraldic language and colours; no lion-on-blue |
| Purple-skinned, long-eared moon elves, owls/hippogryphs, living tree buildings that uproot and walk, moon wells | Night Elf identity | No purple-skinned elves with tree-ancient buildings. If plant-buildings exist, change their form completely (e.g., fungal, coral) and drop the walking-tree gimmick |
| Undead with ziggurats, a spiked necropolis, purple-black "blight" ground, crypt-fiend spider-men, stitched hook-and-cleaver abominations, gargoyles | Scourge identity and specific creature designs | Undead as a concept is free. Use a new aesthetic and creature roster |
| Hero kits identical to WC3 (e.g., holy melee + heal + aura + invulnerability + resurrect) | Expressive selection and arrangement of a known character | Mix archetypes in new combinations; use our own numbers and VFX |
| Blizzard house style in *combination* with WC3 designs (chunky heroic proportions + same palettes + same emblems) | A style alone is an idea and is free. Style plus copied designs is a look-alike | Keep the chunky readable style (art doc) but make every design, emblem and palette ours |

**Signature mechanics** (walking buildings, blight, haunted mines, wisps that sacrifice, the "detonate wisp") are *legally* free as mechanics.
Together with similar visuals they make a faction read as a WC3 faction. **Policy:** at most one WC3-derived signature mechanic per faction, presented in a visibly different way.

### 2.4 UI and HUD

- **Free (functional or generic):** bottom console; minimap at bottom-left; unit portrait; info panel; 4×3 command grid with hotkey letters;
  resources (gold, wood, supply) at top-right; day/night indicator; hero portraits down the left edge; idle-worker button; health bars;
  green/yellow/red selection circles; team colours; cooldown sweeps.
- **Never copy:**
  - Blizzard's frame art: the carved stone/gold metalwork, race-skinned consoles, gargoyle/skull corner ornaments.
  - The specific day/night orb design and the gauntlet-hand cursor (exact per-race cursor details unverified).
  - The icon border bevel art, WC3 icons themselves, the menu-button art, the font treatment and the loading-screen layout.
- **Fonts:** WC3/WoW-era UI is widely reported to use *Friz Quadrata* (unverified). It is a commercial font. Use OFL/Google Fonts or a
  properly licensed font, and record the licence in a credits file.
- **Icons:** square painted icons are a genre convention. Every icon must be generated from our own description, never from a WC3 icon,
  screenshot or icon sheet. Do not depict the same subject *composition* as a known WC3 icon (e.g., a glowing hand for a heal).

### 2.5 Audio and music

The audio doc (`audio-direction.md` §8) already covers this. In short:

- No rips, no "remakes", no WC3 melodies or motifs (including the level-up cue).
- No voice cloning of WC3 actors; ElevenLabs voices must be original or stock.
- No composer names in prompts: Tracy W. Bush, Derek Duke, Jason Hayes, Glenn Stafford and so on.
- No Hive Workshop soundsets.

### 2.6 Maps

- Never reuse WC3 map names or geometry, and never trace a minimap or overview image (*Micro Star*).
- **Free:** the principles. 2–4 start positions; a natural expansion; tiered creep camps; shops, taverns and fountains as neutral landmarks;
  chokepoints and tree walls; symmetry for fairness.
- **Process:** design on paper from a written brief, then build. Keep the sketch in `data/maps/` as evidence of independent creation.

### 2.7 Data sourcing (input hygiene)

- **Never:**
  - Open, extract or convert WC3 files (MPQ/CASC, `.mdx/.mdl`, `.blp`, `.w3x/.w3m`, `war3map.*`, `Blizzard.j` beyond reading excerpts for numbers).
  - Use WC3 or Reforged screenshots, models or icons as image-to-image, image-to-3D, style (LoRA) or moodboard inputs.
  - Use Hive Workshop or fan "WC3-style" models, skins, icons or sounds. Their provenance is unclear and many are derived from Blizzard assets.
  - Use the WC3 World Editor to prototype anything.
- **Allowed:** watching gameplay videos and reading wikis, Liquipedia or classic.battle.net to learn *mechanics, timings and numbers*.
  Write down the idea in our own words; do not paste their text into our data or tooltips.
- **Krea styles/LoRAs and moodboards** must contain only our own approved outputs (art doc §7.3).

### 2.8 Prompt hygiene for AI generation

- **Banned tokens in any prompt, negative prompt, style name, moodboard title or filename:**
  - Brands: Warcraft, WC3, Blizzard, StarCraft, Reforged, WoW, Hearthstone, Dota.
  - Every name in §2.1.
  - People: Samwise Didier, Chris Metzen, Bill Petras, Glenn Rane, Tracy W. Bush, Derek Duke, Jason Hayes, Glenn Stafford, Bill Roper, and voice actors.
  - Phrases: "in the style of [any studio, game or living artist]", "Blizzard style", "WoW style".
- **Describe qualities instead:** "chunky heroic proportions, hand-painted, saturated harmonious colours, readable silhouette, high three-quarter top-down view"
  (the art doc's global style suffix is compliant).
- **Reference images:** only our own sketches and approved outputs, or CC0 photos of real materials (stone, bark) with the licence recorded.
- **Review every output** before it enters `assets/`:
  - Put it side by side with the nearest WC3 analogue. If a fan would name the WC3 unit, icon or building at a glance, reject or redesign it.
  - Apply the *Tetris* "squint" test and the *Spry Fox* "focus on what is similar" test.
- **Log it.** In `docs/asset-ledger.md` record: service, model, plan tier, date, job id, full prompt and negative prompt, seed, reference inputs (with source and licence),
  reviewer, the similarity check result, and the human modifications made (palette remap, retopo, paint-over, rig/animation). The modifications support our authorship (§1.5).

---

## 3. Generic fantasy is fine; make the factions original anyway

### 3.1 What is free

- **Orcs:**
  - The word is Old English (Beowulf's *orcneas*). Tolkien popularised the modern sense, and D&D, Warhammer and many games use it.
  - Tolkien's *texts* are still in copyright: he died in 1973, so the EU life+70 term runs to the end of 2043 (background, not fetched).
  - Tolkien-specific names (Uruk-hai, Mordor, hobbit) are enforced as trademarks. Avoid them too.
- **Elves, dwarves, goblins, trolls, ogres, undead, liches, ghouls, gargoyles, gryphons, dragons, centaurs:** myth, folklore and heraldry, all free as concepts.
- **Humans with medieval kit:** history, free.
- **"Horde" and "alliance" as ordinary words** are free in prose. As **faction names** they are Blizzard's brand language, so do not use them as faction names.

### 3.2 Distinctness rubric (every faction must pass)

For each Vibecraft faction, find its nearest WC3 race. The faction must differ clearly on **at least 4 of these 6 axes**, and on silhouette in every case:

1. **Silhouette language** (body shapes, headgear, weapon shapes, building rooflines). Test with flat black thumbnails at 64 px.
2. **Palette** (primary and secondary colours; not lion blue/gold, Horde red/brown, NE purple/teal, or Scourge purple/black/green).
3. **Material language** (e.g., lacquered wood, coral, glass, woven reed, bronze, paper).
4. **Cultural or design inspiration** (pick sources WC3 did not use, and treat real cultures respectfully).
5. **Signature mechanic** (at most one WC3-derived, shown differently).
6. **Name set and voice** (no WC3 names; own speech style and humour; see §2.2).

Example **illustrative** directions only; the creative-direction doc decides the actual factions:
a lantern-and-canal guild of tinkers with paper-kite flyers; a fungal undergrowth people whose buildings are grown, not built;
a bronze-age salt-desert host with sun-glass towers; restless drowned dead who rise from tidal shrines. Each keeps the RTS archetypes
(worker, line infantry, ranged, caster, siege, flyer, heroes) without mapping one-to-one onto a WC3 race.

---

## 4. The name "Vibecraft"

**Findings:**

- **Precedent:** Blizzard's June 2003 cease-and-desist to *Freecraft* said the name "could cause confusion with the names StarCraft and Warcraft".
  The developers halted and later relaunched as **Stratagus** (2004). That was a free, open-source WC2-like RTS, which is very close to our situation.
- **Same goods:** a fantasy RTS that openly evokes WC3 is the *same goods* as Blizzard's "-craft" marks. Under the USPTO factors (sound, appearance,
  meaning, commercial impression, plus related goods), "X-craft + fantasy RTS + WC3 feel" is the riskiest combination.
- **The suffix itself is not owned:** "-craft" appears in many titles (Minecraft is the obvious one), and Mojang and Blizzard coexist.
  Risk is about the *whole* (name + genre + look + marketing), not the suffix in isolation. Blizzard's history (Freecraft, DOTA, Lilith/uCool) shows it enforces in the RTS space.
- **Crowding:** "vibe coding" was coined by Andrej Karpathy in February 2025 and was the Collins English Dictionary Word of the Year 2025 (verified on Wikipedia).
  "Vibecraft" is therefore a likely name for other AI-coding tools, apps or games (unverified). **No search was run** (budget exhausted). Assume conflicts may exist until checked.
- **Weak mark:** even without a conflict, a descriptive or pun name may be hard to register (compare *Scrolls*, where Mojang agreed not to register).

**Recommendation:**

1. Keep **"Vibecraft" as the repository and internal codename only.**
2. Pick the public title before any store page, trailer or social account. Avoid "-craft", "War-", "Star-" and "-storm" patterns, and any Blizzard world word.
3. **Clearance procedure** before committing to a public name:
   1. Search the USPTO Trademark Search system, EUIPO eSearch / TMview and WIPO Global Brand Database, in classes 9, 41 and 28.
   2. Search Steam, itch.io, the App Store, Google Play and GitHub.
   3. Search domains and social handles.
   4. A trademark attorney does a knock-out search and opinion.
   5. File in the target markets once chosen (US and EU at minimum).
4. **Marketing:**
   - Describe the game generically ("hero-driven fantasy RTS with base building and creeps").
   - Do not use "Warcraft" in titles, tags, ad keywords or thumbnails.
   - Do not imitate WC3 box art or logo treatment, or use gold-bevel logos with the same colour scheme (see *Tetris* trade dress).

---

## 5. Checklists

### 5.1 Dev team checklist (per pull request that adds content)

- [ ] No banned names (§2.1) in data, scenes, code identifiers visible to players, filenames, or commit messages that ship.
      Run `grep -r -i -E -f tools/ip_banned_terms.txt data src assets` (suggest adding this file and a CI check).
- [ ] No WC3 voice lines or paraphrases (§2.2). VO scripts reviewed against the Warcraft Wiki quote pages.
- [ ] Tooltips and lore written from scratch, and no text pasted from wikis.
- [ ] New units/buildings pass the side-by-side similarity review and the faction distinctness rubric (§3.2).
- [ ] UI art is original. Only the *layout* follows genre convention (§2.4).
- [ ] Maps were drawn from our own brief. No WC3 map name or geometry (§2.6).
- [ ] No files derived from a WC3 install, World Editor, Hive Workshop or fan packs (§2.7).
- [ ] Every new asset has a ledger entry with full provenance (§2.8).
- [ ] Third-party assets (fonts, CC0/CC-BY, Sonniss) are licence-checked and listed in `CREDITS.md`. Attribution is in place where required.

### 5.2 AI prompt checklist (per generation)

- [ ] The prompt and negative prompt contain no banned tokens (brands, names, artists, composers, actors, "in the style of …").
- [ ] Reference images (if any) are ours or properly licensed; they are not game screenshots.
- [ ] The subject is described by **function and qualities** ("heavily armoured spear infantry, lacquered red-wood armour, round shield, chunky proportions"),
      not by analogy ("like a Grunt").
- [ ] The palette and emblem follow *our* faction sheet.
- [ ] The output was reviewed: not recognisable as a specific WC3 unit, icon, building or UI piece; no stray logos, text or watermarks.
- [ ] The plan tier allows commercial use (Krea; ElevenLabs is non-commercial on free tiers).
- [ ] Ledger entry written, including the human modifications made afterwards.

**Prompt template (compliant):**
> full body [function-based unit description], [faction material language], [faction palette], [team-colour key], standing A-pose, front three-quarter view,
> + art-doc global style suffix. No text, no logo, no watermark.

### 5.3 Release gate (before any public build or store page)

- [ ] Public title chosen and cleared (§4). An attorney has reviewed the name and the key art.
- [ ] Full-game look-alike review: someone who knows WC3 well plays 15 minutes. List anything they say "that's just X from WC3" about, and fix it.
- [ ] Steam AI disclosure prepared (pre-generated content; describe the tools); verify the current form.
- [ ] Terms snapshots saved (Krea, ElevenLabs) for the period when assets were generated; plan tiers confirmed.
- [ ] `CREDITS.md` and the licence files are complete.
- [ ] Marketing copy, tags and trailer contain no Blizzard marks.

---

## 6. Open questions and unverified items

- No trademark or marketplace search for "Vibecraft" was performed (search budget exhausted). Do this before choosing a public name.
- EU/UK cases (C-393/09, C-355/12, *Nova v Mazooma*) and the US trade-dress cases (*Wal-Mart*, *TrafFix*) are cited from background knowledge, not fetched.
- The Lilith Games/uCool outcome beyond "Blizzard moved to dismiss with prejudice" is not confirmed, and the court (N.D. Cal.) is inferred from the judge.
- The details and date of the Steam AI disclosure come from memory. The page title was verified but the body could not be read.
- Whether Krea's or ElevenLabs' terms govern ElevenLabs outputs generated through Krea is unknown. Check with Krea support or the docs.
- The WC3 UI font (Friz Quadrata) and per-race cursor details are unverified. They only matter as things *not* to copy.

---

## Sources

**Statutes and government**
- [17 U.S.C. §102 (Cornell LII)](https://www.law.cornell.edu/uscode/text/17/102)
- [US Copyright Office, Circular 33: Works Not Protected by Copyright (rev. 03/2021)](https://www.copyright.gov/circs/circ33.pdf)
- [US Copyright Office: Copyright and Artificial Intelligence (report index)](https://www.copyright.gov/ai/)
- [US Copyright Office: Copyright and AI, Part 2: Copyrightability (29 Jan 2025, PDF)](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)
- [Thaler v. Perlmutter, D.C. Cir. No. 23-5233, decided 18 Mar 2025 (opinion PDF)](https://media.cadc.uscourts.gov/opinions/docs/2025/03/23-5233.pdf)
- [USPTO: Likelihood of confusion](https://www.uspto.gov/trademarks/search/likelihood-confusion)

**Cases and disputes**
- [Tetris Holding, LLC v. Xio Interactive, Inc. (Wikipedia)](https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc.)
- [Spry Fox, LLC v. Lolapps, Inc. (Wikipedia)](https://en.wikipedia.org/wiki/Spry_Fox,_LLC_v._Lolapps,_Inc.)
- [Triple Town (Wikipedia; lawsuit and settlement)](https://en.wikipedia.org/wiki/Triple_Town)
- [Data East USA, Inc. v. Epyx, Inc. (Wikipedia)](https://en.wikipedia.org/wiki/Data_East_USA,_Inc._v._Epyx,_Inc.)
- [Atari, Inc. v. North American Philips Consumer Electronics Corp. (Wikipedia)](https://en.wikipedia.org/wiki/Atari,_Inc._v._North_American_Philips_Consumer_Electronics_Corp.)
- [Lotus Development Corp. v. Borland International, Inc. (Wikipedia)](https://en.wikipedia.org/wiki/Lotus_Development_Corp._v._Borland_International,_Inc.)
- [Micro Star v. FormGen Inc. (Wikipedia)](https://en.wikipedia.org/wiki/Micro_Star_v._FormGen_Inc.)
- [SAS Institute Inc v World Programming Ltd (Wikipedia)](https://en.wikipedia.org/wiki/SAS_Institute_Inc_v_World_Programming_Ltd)
- [bnetd / Davidson & Associates v. Jung (Wikipedia)](https://en.wikipedia.org/wiki/Bnetd)
- [Dota 2 (Wikipedia; Valve–Blizzard trademark dispute, Lilith/uCool suits)](https://en.wikipedia.org/wiki/Dota_2)
- [Defense of the Ancients (Wikipedia; DOTA trademark, World Editor)](https://en.wikipedia.org/wiki/Defense_of_the_Ancients)
- [Heroes of the Storm (Wikipedia; Blizzard DOTA → Blizzard All-Stars → HotS)](https://en.wikipedia.org/wiki/Heroes_of_the_Storm)
- [Stratagus (Wikipedia; Freecraft cease-and-desist, June 2003)](https://en.wikipedia.org/wiki/Stratagus)
- [Scrolls (Wikipedia; Bethesda vs Mojang name dispute)](https://en.wikipedia.org/wiki/Scrolls_(video_game))

**Blizzard and Warcraft**
- [Blizzard End User License Agreement (last updated 21 Mar 2024)](https://www.blizzard.com/en-us/legal/fba4d00f-c7e4-4883-b8b9-1b4500a402ea/blizzard-end-user-license-agreement)
- [Warcraft III: Reforged (Wikipedia; Custom Game Acceptable Use Policy controversy)](https://en.wikipedia.org/wiki/Warcraft_III:_Reforged)
- [Warcraft (Wikipedia; franchise and setting names)](https://en.wikipedia.org/wiki/Warcraft)
- [Warcraft III: Reign of Chaos (Wikipedia; composers Tracy W. Bush, Derek Duke, Glenn Stafford; designer, artist, writer credits)](https://en.wikipedia.org/wiki/Warcraft_III:_Reign_of_Chaos)

**Other**
- [Nemesis system (Wikipedia; US10926179B2 granted Feb 2021)](https://en.wikipedia.org/wiki/Nemesis_system)
- [Midjourney (Wikipedia; Disney/Universal suit 11 Jun 2025, Warner Bros. Discovery suit 4 Sep 2025)](https://en.wikipedia.org/wiki/Midjourney)

**AI tools and platforms**
- [Krea Terms of Use](https://www.krea.ai/terms)
- [ElevenLabs Terms of Use (last updated 09 Oct 2026)](https://elevenlabs.io/terms-of-use)
- [Steamworks: "AI Content on Steam" (title verified; body not retrievable)](https://store.steampowered.com/news/group/4145017/view/3862463747997849618)
- [Vibe coding (Wikipedia; coined Feb 2025, Collins Word of the Year 2025)](https://en.wikipedia.org/wiki/Vibe_coding)
