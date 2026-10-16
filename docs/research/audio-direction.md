# Audio Direction: Sound & Music for a WC3-feel RTS (Godot 4.7)

*Research date: 2026-10-16. Scope: what made Warcraft III (2002/2003, Blizzard) sound the way it did, how to get the same **feel** with original audio, how to generate it with our tools (Krea: ElevenLabs TTS, ElevenLabs Music v2.5, Seed Audio 1.0), CC0 fallbacks, and Godot 4 implementation. We study WC3 for **structure, timing and density only**. We never copy its lines, sounds, motifs or names (see §8).*

*Confidence markers: numbers with a citation come from that source. "(unverified)" means memory, observation or inference. "(proposal)" means our own design decision. Faction names follow `docs/research/visual-art-direction.md` §7.1: **Hearth Wardens** (stalwart folk) and **Thornborn** (wild fey/beast tribe).*

---

## 0. TL;DR: the 14 rules that matter most

1. **Personality first.** WC3's audio identity is the **unit voice**: ~17–20 short lines per unit in fixed categories (Ready / What / Yes / Attack / Warcry / Pissed), mostly 0.5–2 s long, plus a run of comedic "pissed" lines on repeated clicks. Budget **~16–20 original lines per unit** and **~22–28 per hero**.
2. **Acknowledgements are 2D, not positional.** The player must always hear "their" unit respond, wherever the camera is. Play acks on a non-positional `AudioStreamPlayer` on a `Voice` bus. Play only **one ack at a time** (proposal).
3. **World sound is camera-local.** Put the `AudioListener3D` at the camera's **ground focus point**, raised about 6 m, not on the camera itself. Cull anything beyond about **50 m**, roughly 1.4 screen widths. WC3's equivalent cutoff (3000 units ≈ 47 m at our scale) sits just past the screen edge.
4. **Hard caps everywhere.** Allow at most **4 simultaneous instances of the same sound** with **≥ 60–100 ms spacing**. WC3 itself allowed 4 per file and needed 0.1 s between same-file plays ([jassbot](https://lep.duckdns.org/jassbot/doc/CreateSound)). Use a **24-voice world pool** with priority stealing.
5. **Melee = swing layer + material layer.** Model WC3's weapon-sound × armor-sound matrix with two one-shots: {slice, chop, bash, claw, pierce} × {metal, wood, flesh, stone, ethereal}. Ten families × 3 variants (30 files) cover 25 combinations.
6. **Duck, don't drown.** Sidechain compressors on the Music and Ambience buses, keyed from `Voice`, give 4–6 dB of ducking. Never duck acks for combat.
7. **Music is a slow rotation, not adaptive bombast.** WC3 rotates **4 race tracks** (Human1–3 + HumanX1, and so on) with **~20–40 s of silence between songs** ([Hive](https://www.hiveworkshop.com/threads/custom-music-lists.294961)). Album tracks run ~4–5 min ([OST list](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack)). Do the same: 3 tracks per faction at 3–4 min each, shuffled, with ambience carrying the gaps.
8. **Ambience follows day/night.** WC3's cycle is **480 s (240 s day + 240 s night)** ([Liquipedia](https://liquipedia.net/warcraft/Daytime); page rate-limited during the 2026-10-16 fact-check, so not re-verified), with a separate day and night ambient bed per tileset ([Hive Sound Editor guide](https://www.hiveworkshop.com/forums/f278/sound-editor-39234/)). Build 2 beds per biome, plus random positional "sweeteners" and a dawn/dusk stinger.
9. **Our voices come from a fixed menu.** Through Krea, ElevenLabs TTS only accepts `prompt`, `voice_id` (21 preset voices) and `model_id`. Krea's public API (`list_models`, checked 2026-10-16) exposes **no voice design and no cloning** for audio. Krea's web-app audio guide does list a "Qwen Voice Clone" model, but it is not in the API model list, and we do not use cloning anyway (§8). Faction identity therefore comes from **casting + `eleven_v4` audio tags + an ffmpeg post-chain** (pitch/formant shift, EQ, chorus).
10. **Generate all VO early and archive raw WAVs.** ElevenLabs says its default voices **expire on 31 Dec 2026** ([ElevenLabs help, IT](https://elevenlabs.io/docs/it/help-center/product/voices/my-voices/what-are-default-voices.md)). That is 2.5 months from now.
11. **Seed Audio = SFX and creature workhorse.** It is prompt-only (≤ 2048 chars). Always say "sound effect only, no music, no voice, no background". Ask for **4 variants separated by 1 s of silence** and split them with `silencedetect` (untested trick; verify cost per job).
12. **Music via ElevenLabs Music v2.5** with `force_instrumental: true` and `music_length_ms` (3,000–600,000). Never put franchise, studio or composer names in prompts.
13. **Fallback library = CC0 only by default** (Kenney, OpenGameArt CC0, Freesound CC0 filter). Sonniss GDC bundles are royalty-free without attribution, but **forbid AI training and redistribution as SFX**. Never feed them into AI tools.
14. **Godot specifics:** `AudioStreamRandomizer` (random no-repeat, pitch ±1–2 semitones for SFX, none for voices); pooled `AudioStreamPlayer3D` with `max_polyphony` 1–2; WAV (QOA) for SFX; Ogg Vorbis for VO, music and ambience; `AudioStreamPlaylist` or `AudioStreamInteractive` for music.

---

## 1. Anatomy of Warcraft III audio

### 1.1 Who made it

| Person | Role on WC3 | Source |
|---|---|---|
| **Glenn (Glen) Stafford** | Composer ("Blackrock & Roll", "Frostmourne", "Lordaeron Fall"). Described in 2007 as director of Blizzard's Audio Department. | [Warcraft Wiki OST](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack), [Engadget 2007](https://www.engadget.com/2007-07-31-who-made-warcrafts-soundtrack.html) |
| **Tracy W. Bush** | Composer with the most OST tracks ("Arrival at Kalimdor", "Awakening", "Doomhammer's Legacy", "Rise of the Ancients", "Temporary Alliances", "The Calm"). Senior sound designer, and also a voice actor. | [Warcraft Wiki OST](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack), [Warcraft Wiki: Tracy W. Bush](https://warcraft.wiki.gg/wiki/Tracy_W._Bush) |
| **Derek Duke** | Composer ("Arcane Echoes", "Blight", "Bloodlust", "Carrion Waves", "Reign of Chaos"). The GI page calls him "co-composer of Warcraft III" and says the interview covers his Orc and Undead soundtrack work. The claims that his primary role was **cinematic sound design** and that he made the "creepily inspired" Undead sounds are **(unverified)**: they are not in the GI article text and may come from the video or a Wowhead recap that was not re-checked. | [Game Informer 2018](https://www.gameinformer.com/exclusive-feature/2018/11/16/inside-the-creation-of-warcraft-iiis-soundtrack) |
| **Jason Hayes** | "Cinematic Suite" (14:47). Not credited on the TFT EP (Duke, Stafford and Bush are). | [Warcraft Wiki OST](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack), [Warcraft Wiki: TFT Soundtrack EP](https://warcraft.wiki.gg/wiki/Warcraft_III:_The_Frozen_Throne_Soundtrack_EP) |
| **Bill Roper** | Voice of the Peon across WC1–3. | [Warcraft Wiki: Peon](https://warcraft.wiki.gg/wiki/Peon) |

**Process notes:**
- A "small, tight-knit group of sound designers" wrote much of the WC3 music **in their free time**, staying late after finishing assigned work. Inspiration for sounds was often "drawn from the models themselves". **(Unverified):** attributed to a Wowhead recap of [Game Informer's feature](https://www.gameinformer.com/exclusive-feature/2018/11/16/inside-the-creation-of-warcraft-iiis-soundtrack). The GI article text does not contain these quotes, so they would have to come from the video.
- *Lesson:* the sound designers also wrote the music, which is why music, ambience and SFX feel like one world.
- Reforged (2020) **kept the original story and voice performances**. PC Gamer's headline gives the reason: "Warcraft 3 Reforged's story isn't changing to fit WoW because people love the voice actors" ([PC Gamer](https://www.pcgamer.com/uk/warcraft-3-reforgeds-story-isnt-changing-to-fit-wow-because-people-love-the-voice-actors/)). The article body could not be retrieved, so details of the audio remaster are (unverified).
- *Lesson:* unit voices are the most beloved part of the package.
- The full voice-cast list is on [IMDb](https://m.imdb.com/title/tt0259104/fullcredits/cast). Many actors voiced several units each.

### 1.2 Unit responses ("acknowledgements")

**Categories.** Modding resources name the categories **Ready, What, Yes, YesAttack, Warcry, Pissed, Death** (e.g. [Hive Voidwalker soundset](https://www.hiveworkshop.com/threads/warcraft-iii-voidwalker-soundset.345038/)). The scheme descends from Warcraft II's Ready/What/Yes/Pissed ([Quotes of Warcraft II](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_II)).

**Line counts (counted from Warcraft Wiki quote pages):**

| Unit | Ready | What | Yes | Attack | Warcry | Pissed | Other | Total |
|---|---|---|---|---|---|---|---|---|
| Peasant (worker) | 1 | 4 | 4 | 4 | 1 | 5 | 1 (job complete) | 20 |
| Footman (melee) | 1 | 4 | 4 | 3 | 1 | 4 | – | 17 |
| Rifleman (ranged) | 1 | 4 | 4 | 4 | 1 | **8** | – | 22 |
| Knight (cavalry) | 1 | 4 | 4 | 3 | 1 | 6 | – | 19 |
| Paladin (hero) | 1 | 4 | 4 | 3 | 1 | 6 | – | 19 |
| Peon (worker) | 1 | 4 | 4 | 3 | 1 | 4 | 1 ("Work complete") | 18 |
| Grunt (melee) | 1 | 4 | 4 | 3 | 1 | **7** | – | 20 |
| Tauren (heavy) | 1 | 3 | 3 | 3 | 1 | **7** | – | 18 |
| Blademaster (hero) | 1 | 4 | 4 | 3 | 1 | 4 | – | 17 |
| Far Seer (hero) | 1 | 4 | 4 | 3 | 1 | 5 | – | 18 |

Sources: [Human Alliance quotes](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance), [Orc Horde quotes](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Orc_Horde). The counts were re-checked on 2026-10-16. Knight and Paladin each have one extra beta-only line ("Charge" / "Exorcism") on the wiki, which these release-line counts leave out.

**When each category plays** (observed behaviour; trigger details unverified):

| Category | Trigger | Typical length | Tone |
|---|---|---|---|
| **Ready** | Unit finishes training or is revived | 1–2 s | Character intro, the "catchphrase" |
| **What** | Unit selected (the primary selected type speaks) | 0.4–1.2 s | Attentive, in character |
| **Yes** | Move/ability order | 0.4–1.2 s | Compliant, flavourful |
| **Attack** | Attack order | 0.5–1.5 s | Aggressive, short |
| **Warcry** | Occasional battle shout on engaging (exact rule unverified) | 1–2 s | Loudest delivery |
| **Pissed** | Same unit clicked repeatedly. Lines appear to play **in sequence**, so multi-line jokes work. The click threshold is undocumented; try 4–5 clicks within ~3 s. | 1.5–6 s | Comedy: pop-culture parody, fourth-wall breaks, self-deprecation |
| **Death** | Unit dies (non-verbal scream plus body fall) | 0.5–1.5 s | Short, readable |
| **Job complete** | Worker finishes a building | ~1 s | Satisfied |

**Comedic tone examples** (quoted only for analysis; never reuse or paraphrase):
- Peasant: "Help! Help! I'm being repressed!"
- Footman: "It's only a flesh wound."
- Rifleman: "Guns don't kill people, I do!"
- Tauren: "There's a lot at steak here!"
- Peon: "Me not that kind of orc!"

The pattern is **puns, parodies of famous films and lines, and characters complaining about their job**. The "piss lines" concept is genre-wide ([Giant Bomb](https://giantbomb.com/wiki/Concepts/Piss_Lines); the link returned 403 during the fact-check and is unverified).

### 1.3 UI and feedback sounds (inventory of event types)

The building click sounds are confirmed by the "Building Sounds" videos (§2). The remaining items in this list are observed and unverified in detail:

- **Command and button click.** Race-specific UI skin sounds (unverified).
- **Error, non-verbal.** The engine plays `Sound\Interface\Error.wav` ([Hive thread](https://www.hiveworkshop.com/threads/couple-of-questions.160141)).
- **Error, verbal.** A race "advisor" voice says the equivalent of *not enough gold / lumber / food*, *can't build there*, *invalid target* (unverified wording).
- **Alerts.** *Town under attack*, *ally under attack*, *hero has fallen*, *gold mine running low / collapsed*. A mine counts as "low" at 1,500 gold (see `docs/research/video-references.md` M6).
- **Completion.** *Building complete* (the worker's "Job complete" line plus a race cue), *upgrade complete*, *research complete*. Patch 1.10 added on-screen text naming the finished upgrade ([Neowin, 1.10 notes](https://www.neowin.net/amp/warcraft-iii-patch-v110-released/); the source returned 403 during the fact-check, so this is unverified).
- **Hero.** *Level up*: a bright rising cue with a light pillar, about 1–2 s (unverified; [YouTube: level-up](https://www.youtube.com/watch?v=r6v8zgsXJrU)). *Hero revived* plays the hero's own **Ready** line. *Hero death* is a loud, global, distinctive scream ([GrubbyTalks tier list](https://www.youtube.com/watch?v=U6ZrCOARhZc)).
- **Building select one-shots.** Each building has a characteristic "voice" when clicked, such as a bell, an anvil clang or a chant ([Human](https://www.youtube.com/watch?v=3wHMAluEC6g) / [Undead](https://www.youtube.com/watch?v=WHwDTfF8qdo) building sounds).
- **Items, gold and quests.** Item pickup/drop, creep-bounty coin clink, quest discovered/updated/completed (campaign), minimap ping (unverified details).

### 1.4 Combat sounds

**Weapon × armor sound matrix** (unverified; from World Editor field memory).
- Each unit has a *weapon sound* field, e.g. "Metal Heavy Slice", "Metal Medium Chop", "Wood Heavy Bash", "Axe Medium Chop", "Rock Heavy Bash".
- Each unit also has an *armor sound type*: Flesh, Metal, Wood, Stone or Ethereal.
- The impact sound is chosen from the combination.
- This is separate from the gameplay armor/attack types (Heavy/Medium/Light/Fortified/Hero/Divine × Normal/Piercing/Siege/Magic/Chaos/Hero; [Warcraft Wiki](https://warcraft.wiki.gg/wiki/Warcraft_III_armor_and_attack_types)).

**Missiles:**
- Missile sounds can be attached to the model as an **Event Object**: "You need to add an Event Object on the model of the missile you want to use". The sound is then "played for all units using this model on the map, in real time" ([Hive projectiles tutorial](https://www.hiveworkshop.com/threads/using-sounds-the-example-of-projectiles.179184/)). The split between attacker-animation and missile-impact events is our reading and is (unverified).
- Example asset: `Units\Human\GyroCopter\GyrocopterImpactHit1.wav`. The tutorial passes 750 ms as the duration argument; it does not confirm the file's real length.
- *Sound follows animation keys.* Our equivalent is to emit sound from the procedural animation's hit frame.

**Engine limits:**
- Same file: up to 4 concurrent instances, ≥ 0.1 s apart. Overall: 16 sounds (as documented for JASS-created sounds) ([jassbot CreateSound](https://lep.duckdns.org/jassbot/doc/CreateSound)).
- With 10 units firing every 0.4 s, "most bullet sounds were not played" ([Hive](https://www.hiveworkshop.com/threads/using-sounds-the-example-of-projectiles.179184/)). WC3 *wants* sparse combat audio. A dense big fight still reads clearly because most impacts are dropped.

**3D sound defaults:**
- A community sound library uses **min distance 600, max 10,000, cutoff 3,000** world units, "CombatSoundsEAX", channel 5 ([Hive](https://www.hiveworkshop.com/threads/using-sounds-the-example-of-projectiles.179184/)).
- At our scale (1 m = 64 WC3 units; camera distance 1650 u = 25.8 m), that is **min 9.4 m / cutoff 47 m**.

**EAX presets** (the "Effect" field): CombatSoundsEAX, KotoDrumsEAX, SpellsEAX, MissilesEAX, HeroAcksEAX, DoodadsEAX, DefaultEAXON ([jassbot](https://lep.duckdns.org/jassbot/doc/CreateSound)). *Lesson:* per-category reverb and EQ treatment, which maps directly onto Godot buses.

**File spec:** community guidance is **22,050 Hz, mono, 16-bit WAV** for imports. This comes from a reply in the [Hive Sound Editor guide](https://www.hiveworkshop.com/forums/f278/sound-editor-39234/) thread, not from the guide body. The lo-fi sample rate is part of the "crunchy" period feel. We use 44.1 kHz and can roll off highs on some buses if it sounds too hi-fi.

### 1.5 Economy loops

- **Construction:**
  - The cited page confirms only that "the method of construction differs between the Humans, Orcs, Undead, and Night Elves", and that Human Peasants can help speed construction ([Warcraft Wiki: Building](https://warcraft.wiki.gg/wiki/Building_(Warcraft_III))). The per-race details below are common game knowledge and are (unverified) against that page:
  - Human peasants hammer *outside* the building, with a looped hammering sound.
  - Orc peons and Night Elf wisps build from *inside*.
  - Undead acolytes *summon* a building and walk away.
  - Completion: the worker's "job complete" line.
  - *Lesson:* a different construction verb per faction gives a different construction sound.
- **Gold mine.** Workers vanish into the mine for about 1 s (observed). There is a mine enter/exit cue ([YouTube: gold mine](https://www.youtube.com/watch?v=lD55CrlRPl0)) and a deposit at the hall. Each trip carries 10 gold.
- **Lumber.** A looped axe-chop at the tree, 10 lumber per trip at base level. Trees eventually fall (see `video-references.md` M7).

### 1.6 Ambience and creeps

- **Ambient themes:**
  - Each tileset has a **day and night ambient theme**, e.g. "Lordaeron Summer daytime / nighttime ambient theme".
  - Triggers can switch them, and scripts can stop them (`bj_dayAmbientSound`, `bj_nightAmbientSound`).
  - **Dawn and dusk sounds** exist and can be toggled ([Hive Sound Editor guide](https://www.hiveworkshop.com/forums/f278/sound-editor-39234/)).
  - Content (observed, unverified): day has birds, insects and wind; night has crickets, owls and distant howls. Doodads (waterfalls, fires, braziers) carry their own positional loops ("DoodadsEAX").
- **Day/night cycle.** 480 s per full cycle, with dawn at 06:00 and dusk at 18:00 ([Liquipedia](https://liquipedia.net/warcraft/Daytime); rate-limited during the fact-check, so not re-verified).
- **Creeps.** Neutral monsters use non-verbal sets: aggro growl, attack grunts, pain and death. The sources are recorded and pitched animal or human vocals. Community members recognise some creep sounds from films, which suggests commercial libraries were layered and modified ([Hive thread](https://www.hiveworkshop.com/threads/where-do-sound-effects-of-warcraft-3-come-from.24729/latest); anecdotal).

### 1.7 Music

- **In-game rotation.**
  - Per race: `Sound\Music\mp3Music\Human1.mp3, Human2, Human3, HumanX1`. The same applies to Orc, Undead and NightElf. The X1 tracks were added in TFT.
  - Songs are separated by **~20–40 s timeouts** ([Hive](https://www.hiveworkshop.com/threads/custom-music-lists.294961)).
  - So music plays roughly 85% of the time (inference from album lengths; in-game file lengths are unverified), with **built-in breathing room** where ambience and unit voices dominate.
- **Track lengths.** Album tracks are 3:58–5:14, except the 1:08 / 1:12 interludes and the 14:47 cinematic suite ([Warcraft Wiki OST](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack)).
- **Faction styles** (our listening notes; verify by ear with the §2 links):
  - **Human:** sweeping orchestra (strings, horns, choir, snare) with pastoral, heroic sections. "Blackrock & Roll" is labeled an *Alliance* track by the uploader ([YouTube](https://www.youtube.com/watch?v=uyx5AYHI2Vs)).
  - **Orc:** big drums and low brass, tribal percussion, chant, some rock energy ([Orcs: Music & Ambience](https://www.youtube.com/watch?v=d-HYwNeJRQM)).
  - **Undead:** dissonant strings, dark choir, bells and organ-like pads; creeping, slow.
  - **Night Elf:** ethereal, with female voice, flutes, harp and soft percussion, mystical and calm ("Rise of the Ancients", labeled *Night Elves* by the uploader; [YouTube](https://www.youtube.com/watch?v=nxiGNossTLg)).
- **Stingers.** Short victory and defeat cues per race at the end of a match, with the score screen following (unverified details).

---

## 2. Reference links (watch and listen list)

The YouTube titles below were checked via oEmbed on 2026-10-16. Use them for **timing, density and structure** only.

| # | Link | Use it for |
|---|---|---|
| 1 | [Inside the Creation of Warcraft III's Soundtrack (Game Informer)](https://www.youtube.com/watch?v=ouNEzATaDMs) · [article](https://www.gameinformer.com/exclusive-feature/2018/11/16/inside-the-creation-of-warcraft-iiis-soundtrack) | Derek Duke on Orc/Undead music and sound design |
| 2 | [Warcraft 3 Frozen Throne: Footman Sounds (VGSoundFX)](https://www.youtube.com/watch?v=KgOswctVGpA) | A full ack set for one unit: line lengths and spacing |
| 3 | [Warcraft 3 Orc Quotes](https://www.youtube.com/watch?v=MXgr6SYYNZM) · [WC3 Funny Quotes Part 1: Humans](https://www.youtube.com/watch?v=QiwiuDW52hY) | The comedic "pissed" layer |
| 4 | [Warcraft 3: Human Building Sounds](https://www.youtube.com/watch?v=3wHMAluEC6g) · [Undead Building Sounds](https://www.youtube.com/watch?v=WHwDTfF8qdo) | Building-select one-shots: same function, different sonic identity |
| 5 | [Warcraft 3: Level up sound effect](https://www.youtube.com/watch?v=r6v8zgsXJrU) | The most iconic feedback cue: length and brightness (design our own motif) |
| 6 | [Warcraft 3: Gold mine](https://www.youtube.com/watch?v=lD55CrlRPl0) | Economy loop feel |
| 7 | [The BEST HERO DEATH SOUNDS in WC3 (GrubbyTalks)](https://www.youtube.com/watch?v=U6ZrCOARhZc) | Why hero deaths must be loud, unique and global |
| 8 | [Secrets in Warcraft 3's Icons & Sounds (Abelhawk)](https://www.youtube.com/watch?v=WzLnOyWTZsA) | How Blizzard reused and layered sounds |
| 9 | [Orcs: Music & Ambience (Everness)](https://www.youtube.com/watch?v=d-HYwNeJRQM) | Mood target for a drum-driven faction mix |
| 10 | [Blackrock & Roll](https://www.youtube.com/watch?v=uyx5AYHI2Vs) · [Rise of the Ancients](https://www.youtube.com/watch?v=nxiGNossTLg) | Two contrasting faction-music poles |
| 11 | [WC3 RoC Human Campaign longplay (VGL)](https://www.youtube.com/watch?v=53Ot4lq6YsY) | Raw in-game mix: ambience vs music vs acks, and day/night transitions |
| 12 | [How Blizzard Created the Sound of World of Warcraft (WoW Archives)](https://www.youtube.com/watch?v=gy4ePZnvuKc) | Same audio team era. Philosophy. |
| 13 | [Overwatch: The Elusive Goal: Play by Sound (GDC 2016)](https://gdcvault.com/play/1023010/Overwatch-The-Elusive-Goal-Play) · [PCGamesN summary](https://pcgamesn.com/overwatch/overwatch-devs-on-creating-a-game-you-can-play-by-sound-and-announcing-dolby-atmos-support) · [Audiokinetic write-up](https://www.audiokinetic.com/en/blog/overwatch-game-audio-using-wwise-1/) | Blizzard's **importance-based mix**. Per PCGamesN, the pillars are a "clean mix", pinpointable sounds, sounds that carry gameplay information, and descriptive hero VO. Each enemy gets an "importance" (threat) score that sets its place in the mix. A "Pavlovian response" pillar is (unverified): it is not in the PCGamesN text, and the Audiokinetic page could not be fetched. This is the conceptual model for our priority system. |
| 14 | [Diablo IV audio systems deep dive (GDC schedule)](https://schedule.gdconf.com/session/diablo-iv-audio-systems-deep-dive-living-audio/899258) | Voice limiting, importance, and ducking between VO, SFX and music in a busy top-down game. The page returned 403 during the fact-check, so its title and content are (unverified). |
| 15 | [The Sound of StarCraft II (Designing Sound)](https://designingsound.org/2010/08/17/the-sound-of-starcraft-ii-wings-of-liberty/) | Blizzard RTS sound described as "evolutionary". Organic Zerg sounds were made from homemade goop. |
| 16 | [Company of Heroes 3: audio (Relic, press)](https://www.cosmocover.com/newsroom/company-of-heroes-3-how-relic-brings-wwii-to-life-through-audio/) | Modern RTS goal, in the words of senior audio designer Sam Griffin: "how do we enhance gameplay and player awareness while still retaining an awesome, epic, cinematic mix" |
| 17 | [The Music of Age of Empires IV (Audiokinetic blog)](https://blog.audiokinetic.com/en/the-music-of-age-of-empires-iv/) | Interactive RTS music system. The author's role (Relic music lead) and the details are (unverified): the page could not be fetched. |
| 18 | [Video games and loudness standards: interview with Sony's Garry Taylor](https://designingsound.org/2012/07/30/video-games-and-loudness-standards-interview-with-sonys-garry-taylor/) | Sony's Audio Standards Working Group (ASWG) recommendation: **−23 LUFS (PS3) and −18 LUFS (PS Vita), ±2 LU**, measured per ITU BS.1770. The later ASWG-R001 document is often quoted at −24 LUFS for console; that figure is (unverified) and is not in this interview. |

---

## 3. Audio direction for our original game

### 3.1 Pillars (proposal)

1. **"Every click talks back."** Personality-rich, short, funny voice responses are the signature, as in WC3. Our jokes are **character jokes**, not pop-culture parodies (see §3.2 writing rules).
2. **Readable chaos.** In a 40-unit fight you should still hear: your acks, hero events, spell casts, and a *texture* of melee. Not 40 individual swords.
3. **Handmade, not hi-fi.** Wood, brass, leather, bone and moss. Slightly warm and compressed, like a storybook diorama (this matches the "Storm-lit Heroic Diorama" visual direction).
4. **Two factions, two acoustic worlds.** Wardens are *wood + brass + bells + human voices*. Thornborn are *bone + hide drums + breath + creaking living wood + processed voices*.

### 3.2 Vocal personalities per faction (originals; do not imitate WC3 lines)

**Writing rules (proposal):**
- Every line must be readable in ≤ 2 s, except annoyed lines (≤ 6 s).
- No real-world brand, film or celebrity references: they create IP risk and date quickly. Humor comes from **who the character is**.
- Annoyed sequences tell a **micro-story across 4–6 lines**, played in order.
- Each unit has one verbal tic: a catchphrase, a sound, or a speech pattern.
- Before recording, check each line against the WC3 quote pages ([Human](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance), [Orc](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Orc_Horde)) and reject anything close.

**Hearth Wardens: "guild-proud stubborn folk"**
- **Personality:** warm, dry, deadpan. Tradespeople who treat war as another job with paperwork, unions, tea breaks and pride in craftsmanship.
- **Register:** mid-low and unhurried. Workers sound older and wry. Soldiers sound earnest. The hero sounds calm and authoritative.
- **Advisor voice:** a clipped quartermaster ("Ledger's short on gold.").
- Example lines (original, illustrative):

| Unit | Category | Example lines |
|---|---|---|
| Hearthhand (worker) | Ready | "Hammer's warm. What needs mending?" |
| | What / Yes | "Mm?" · "Tools in hand." · "Right, then." · "I'll fetch my ladder." |
| | Job done | "Built to last. Mostly." |
| | Annoyed (sequence) | "Measure twice, poke once." → "I bill by the poke, you know." → "That's three pokes. I'm writing it down." → "Guild rules say I get a biscuit now." |
| Shieldhand (melee) | Ready / Attack / Warcry | "Shield up, boots laced." · "Lock shields!" · "Hold, Wardens, HOLD!" |
| | Annoyed (sequence) | "Do I look like a door? Stop knocking." → "My shield has a dent shaped like your finger." → "I joined for the soup. Nobody mentioned the poking." |
| Wardens advisor | Errors / alerts | "Ledger's short on gold." · "Not enough timber." · "We need more hearths." · "Can't build there, it's a bog." · "The hall is under attack!" · "Upgrade's done." |

**Thornborn: "feral, superstitious, sing-song"**
- **Personality:** a wild tribe of moss, bone and antler. They speak in first-person plural ("we") and nature metaphors, with clicks, huffs and sniffs between words. Humor comes from **literal animal logic** and grudges against trees, bees and the moon.
- **Register:** brutes are pitched down and gravelly. Hunters are breathy and quick. Shamans are whispery and doubled (chorus/reverb). The hero is huge, slow and resonant.
- **Advisor voice:** a crone-like whisper ("The hive is empty of gold…").
- Example lines (original, illustrative):

| Unit | Category | Example lines |
|---|---|---|
| Mossgrub (worker) | Ready / Yes | "*sniff* We dig. We carry." · "Roots move." · "Hrm, yes yes." |
| | Annoyed (sequence) | "You poke the bee nest also?" → "We have fleas. You want fleas?" → "Our grandmother was a stump. Very wise stump." → "…She also bit." |
| Thornbrute (melee) | Attack / Warcry | "Teeth and thorn!" · "*roar* BREAK THEM!" |
| Briar-witch (caster) | What | "The moss is listening…" · "Speak softly, the moon is near." |
| Thornborn advisor | Errors / alerts | "The hive is empty of gold…" · "Not enough deadwood." · "Our den is bleeding!" · "The rite is complete." |

**Creeps and neutrals.** These are wordless: growls, chitters, honks and squeals from Seed Audio, with pitch variants per creep size. Each creep family gets aggro, attack, pain and death sounds, 2–3 variants each.

**Line budget (proposal):**
- Regular unit: Ready 1, What 3, Yes 3, Attack 3, Warcry 1, Annoyed 4–6, Death 2 (non-verbal). About 17–19 lines.
- Worker: add Job done 1.
- Hero: What 4, Yes 4, Attack 4, plus 1 line per ability, Annoyed 6–8, Level-up 1, Revive = Ready. About 26 lines.
- Advisor per faction: about 14 lines.
- Two factions × (5 units + 2 heroes) + advisors ≈ **2 × (5×18 + 2×26 + 14) ≈ 310 lines**.

### 3.3 Music direction (proposal)

| Faction or state | Instrumentation | Harmony and tempo | Avoid (too close to WC3) |
|---|---|---|---|
| **Hearth Wardens** | Chamber folk-orchestra: strings, two French horns, field snare, **hurdy-gurdy, fiddle, low whistle, bodhrán**, wordless male choir hum, hand bells | Mixolydian/Dorian, 84–100 BPM, a "village band that marched to war". Warm, proud, slightly melancholy. | Full symphonic brass fanfares plus big choir (WC3 Human) |
| **Thornborn** | Frame drums, log drums, udu, **bone flutes, overtone/throat drone**, bowed psaltery, kalimba, creaking-wood percussion, glassy teal pads (glass harmonica) | Phrygian / pentatonic minor, 6/8 over 4/4 polyrhythm, 70–110 BPM. Primal but mystical. | Taiko + low brass + guitar (WC3 Orc), and airy elven female solo (WC3 Night Elf) as the *main* colour |
| **Menu** | Both palettes meet: hurdy-gurdy drone + frame drum + strings | Slow build, 90 s loopable | |
| **Victory / defeat** | Faction instruments, 8–15 s, a clear tonic ending (victory) or an unresolved fade (defeat) | | |
| **Night / creep-camp layer** (optional) | Sparse harp, low drone, distant drum | 60 BPM, mostly silence | |

**Structure:**
- Each in-game track is 3–4 min with an intro (15–20 s), A, B, A′ and an outro that **resolves**, so the playlist gap feels intentional.
- Leave **20–40 s of silence** between tracks (WC3 timing).
- Ship 3 tracks per faction at first (WC3 had 4).
- Music does **not** switch to "battle mode". WC3 doesn't, and constant music swings are tiring in an RTS. Optional later: a quiet percussion stem that fades in when the local player has more than 10 units in combat near the camera.

### 3.4 UI sound language (proposal)

- **Wardens:** wood knock + brass tick (click), bronze hand-bell (complete), muffled double knock (error).
- **Thornborn:** bone-rattle tick (click), hollow log-drum + breath (complete), throat-click "tsk" + low thud (error).
- **Shared:** gold-income coin clink (soft, rate-limited), minimap ping (bright, distinct from everything else), hero level-up (signature cue: rising harp + bell + choir "ah", ~1.2 s; our own motif).

### 3.5 Mixing rules for an RTS (proposal, tune by ear)

**Bus layout** (extends `architecture.md` §12). In Godot, buses can only send to a bus on their left.

| Bus (index order) | Sends to | Default volume | Effects |
|---|---|---|---|
| Master | – | 0 dB | `AudioEffectHardLimiter` (ceiling −1 dB) |
| SFX | Master | 0 dB | – |
| Voice | Master | 0 dB | light compressor (3:1) |
| Music | Master | −12 dB | Compressor, **sidechain = Voice** (ducks 4–6 dB) |
| Ambience | Master | −16 dB | Compressor, **sidechain = Voice**; optional low-shelf cut |
| UI | Master | −8 dB | – |
| Combat | SFX | −5 dB | Compressor, sidechain = Alerts (mild 2:1) |
| Spells | SFX | −3 dB | short reverb (wet 0.1) |
| World (economy, doodads, footsteps) | SFX | −9 dB | – |
| Acks | Voice | 0 dB | – |
| Alerts (advisor, hero events) | Voice | +1 dB | – |

**Priority and limits:**

| Priority | Sound class | Positional? | Max concurrent | Cooldown / spacing |
|---|---|---|---|---|
| 100 | Hero death, hero level-up, victory/defeat | 2D (global) | 2 | – |
| 95 | Advisor alerts (under attack, mine low) | 2D | 1 | 15–20 s per alert type and location; skip if that spot is on screen |
| 90 | Local-player acks (What/Yes/Attack/Annoyed) | 2D | 1 | Don't restart while one is playing unless the selection changed; 0.25 s debounce |
| 85 | Error cue + advisor error ("not enough gold") | 2D | 1 | 1.5 s per error type |
| 80 | Spell cast/impact (heroes) | 3D | 6 | 50 ms same-id |
| 70 | Building complete, research complete | 2D | 2 | – |
| 60 | Melee impacts | 3D | 4 per sound id, 10 total | 60–100 ms same-id |
| 55 | Missile launch/impact | 3D | 4 per id, 8 total | 80 ms |
| 40 | Unit deaths (non-hero) | 3D | 4 | 100 ms |
| 30 | Work loops (chop, build), coin deposit | 3D | 3 loops; coins 2/s | – |
| 20 | Doodad loops, ambience sweeteners | 3D | 4 | – |

**Rules:**
- **Cull before allocating:** a sound farther than `max_distance` from the listener never takes a voice.
- **Stealing:** when the pool is full, steal the lowest-priority voice. On a tie, steal the one that has played longest.
- **Listener:** an `AudioListener3D` follows the camera's ground focus point at y + 6 m.
- Starting distance values: `unit_size` 12–15 m, `max_distance` 50 m, `panning_strength` 0.5–0.7 (soft stereo, so off-centre sounds don't jump to one ear), and distance low-pass mostly off (`attenuation_filter_cutoff_hz` 20500, or `attenuation_filter_db` −6 instead of the default −24) for clarity. For comparison, WC3's cutoff 3000 u ≈ 47 m.
- **Mass-fight thinning:** when more than 8 melee impacts are requested within 250 ms, play the 2–3 nearest to the screen centre. Add one "battle bed" loop (a crowd clash texture) at a volume that scales with the number of fighting units on screen.
- **Ducking:** Voice → Music/Ambience sidechain. Alerts → Combat −3 dB. Never duck acks.
- **Loudness targets (proposal):**
  - Assets: SFX peak −1 dBFS. Voice ≈ −18 LUFS per line (short-term). Music masters ≈ −16 LUFS integrated, then the bus gain takes them down. Ambience ≈ −24 LUFS.
  - Final mix: around −20 to −24 LUFS integrated over a 10-minute session. Sony's 2012 ASWG recommendation is **−23 LUFS ±2 LU** for console (PS3) and −18 LUFS for handheld ([Designing Sound](https://designingsound.org/2012/07/30/video-games-and-loudness-standards-interview-with-sonys-garry-taylor/)). The −24 LUFS console figure often attributed to ASWG-R001 is (unverified).
- **Player options:** Master, Music, SFX, Voice, Ambience and UI sliders. Toggles for "unit responses" and "annoyed lines" (WC3 players muted these; [Hive](https://www.hiveworkshop.com/threads/important-game-sound-setting-modification.245352)).

---

## 4. Generation plan with our tools

### 4.1 What the Krea endpoints actually accept (verified 2026-10-16 via `get_model_schema`)

| Model id | Inputs (`additionalProperties: false`) | Notes |
|---|---|---|
| `elevenlabs/tts` | `prompt` (1–2000 chars), `voice_id` (21 presets, default Bella), `model_id` (`eleven_multilingual_v2` default, **`eleven_v4`**, `eleven_v4_turbo`) | **No voice design, no cloning, no stability/style controls.** Audio tags (`[shouts]`, `[laughs]`, `[low, threatening]`, custom descriptions) work on `eleven_v4`, `eleven_v4_turbo` and `eleven_v3` ([ElevenLabs tags](https://elevenlabs.io/blog/elevenlabs-audio-tags-list)). |
| `elevenlabs/music-v2.5` | `prompt` (1–4100 chars), `music_length_ms` (3,000–600,000; omit = model decides), `force_instrumental` (default false) | Vocals by default ([Krea docs](https://www.krea.ai/docs/api-reference/audio/elevenlabs-music-v25.md)) |
| `bytedance/seed-audio-1.0` | `prompt` only (1–2048 chars) | No duration, format or voice params on Krea ([Krea docs](https://www.krea.ai/docs/api-reference/audio/seed-audio-10)). The model does speech, dialogue, SFX, ambience and music beds in one pass, with **no stems**. Bracketed voice hints like `[voice: …]` steer delivery, and `[sound: …]` / `[Background: …]` appear in Segmind's example prompts (not a documented formal syntax). Segmind also warns that "highly specific foley … can drift" ([Segmind](https://blog.segmind.com/seed-audio-1-0-bytedances-all-in-one-audio-model-explained/)). |

**Measured cost.** One Seed Audio SFX of about 2.5 s cost **4.63 CU** (`docs/asset-ledger.md`). TTS and Music costs are not yet measured. **Run one probe each** (a 5-line TTS batch, and a 30 s music clip) before committing the budget.

**Voice designer note.** ElevenLabs' own API has a two-step Voice Design flow (`text_to_voice.design` with `eleven_multilingual_ttv_v2`, then `create`; e.g. "A massive evil ogre speaking at a quick pace…") ([ElevenLabs docs](https://elevenlabs.io/docs/eleven-api/guides/how-to/voices/voice-design)). It is **not exposed via Krea**, so we do not plan on it.

### 4.2 Voice pipeline

**Casting** (Krea preset voices; descriptions from a [third-party voice table](https://wavespeed.ai/docs/docs-api/elevenlabs/elevenlabs-voice-id)):

| Character | voice_id (name) | Why | Post-chain (ffmpeg) |
|---|---|---|---|
| Wardens worker | `pqHfZKP75CvOlQylNhV4` (Bill) | friendly older storyteller | `rubberband=pitch=0.97:formant=preserved`, warm EQ |
| Wardens melee | `SOYHLrjzK2X1ezoPC6cr` (Harry) | "animated warrior" energy | light compression only |
| Wardens ranged | `TX3LPaxmHKxFdv7VOQHJ` (Liam) | young, energetic, cocky | none |
| Wardens caster (female) | `XrExE9yKIg1WjnnlVkGX` (Matilda) | alto, composed | small room reverb |
| Wardens hero | `nPczCjzI2devNBz1zQrb` (Brian) or `JBFqnCBsd6RMkjVDRZzb` (George) | deep, resonant authority | +2 dB at 150 Hz |
| Wardens advisor | `onwK4e9ZLuTAKqWW03F9` (Daniel) | clear broadcast delivery | band-limit 200–6k Hz ("speaking-tube") |
| Thornborn worker | `N2lVS1w4EtoT3dr4eOWO` (Callum) | gravelly, unsettling | `rubberband=pitch=1.12:formant=shifted` (small goblin-ish creature) |
| Thornborn brute | `pNInz6obpgDQGcFmaJgB` (Adam) | brash, aggressive | `rubberband=pitch=0.84:formant=shifted`, +4 dB @180 Hz, −3 dB @3.2 kHz, compressor |
| Thornborn hunter (female) | `cgSgspJ2msm6clMCkdW9` (Jessica) or `FGY2WhTYpPnrIDTdsKH5` (Laura) | playful or quirky trickster | `chorus` + slight `aecho` |
| Thornborn shaman / advisor | `EXAVITQu4vr4xnSDxMaL` (Sarah) with `[whispers]` | intimate, eerie | `rubberband=pitch=1.06:formant=preserved,chorus,aecho` |
| Thornborn hero | `nPczCjzI2devNBz1zQrb` (Brian) or `JBFqnCBsd6RMkjVDRZzb` (George) | huge and slow | `rubberband=pitch=0.8:formant=shifted` + long-tail reverb |

All the ffmpeg chains above were tested to run on this container's ffmpeg build (rubberband, chorus, aecho, acompressor, loudnorm, silenceremove and libvorbis are all present). Voices that are hard to get from TTS, such as wordless creatures or "half-animal" shouts, go to **Seed Audio** with a descriptive `[voice: …]` hint.

**Batching trick** (proposal, verify on the first probe):
- Put all lines of one category for one unit into **one TTS request**, separated by `[long pause]` and blank lines.
- Split the result on silences ≥ 0.35 s (`silencedetect=noise=-40dB:d=0.35`).
- This gives a consistent performance across lines and fewer jobs.
- Example request:

```json
{"model": "elevenlabs/tts",
 "input": {"model_id": "eleven_v4", "voice_id": "SOYHLrjzK2X1ezoPC6cr",
  "prompt": "[a stubborn shield-wall soldier, earnest, slightly winded] Shield up, boots laced.\n\n[long pause]\n\n[shouts] Lock shields!\n\n[long pause]\n\n[deadpan, mildly offended] Do I look like a door? Stop knocking."}}
```

**Post-processing order:**
1. Split.
2. Trim silence (`silenceremove … areverse …`).
3. Character chain (pitch, EQ, chorus).
4. 5 ms fade-in and 20 ms fade-out.
5. Loudness to about −18 LUFS (pyloudnorm, or ffmpeg two-pass `loudnorm` for clips longer than 3 s).
6. Export as Ogg Vorbis mono `-q:a 5`, or WAV for Godot QOA.

Keep the raw TTS output in `assets_src/` (not shipped) because the default voices expire on 31 Dec 2026.

### 4.3 SFX pipeline (Seed Audio)

**Prompt template:**
```
Sound effect only. No music, no speech, no background ambience.
[sound: <what, material, weight, size, distance (close-miked)>]
<N> separate variations, each about <D> seconds, separated by one second of silence.
Each variation slightly different in pitch and texture. Dry, punchy, stylized fantasy game sound.
```

**Then:**
1. Split on silence.
2. Discard bad takes.
3. Trim, then fade.
4. Peak-normalize to −1 dBFS.
5. Export as WAV 44.1 kHz mono (Godot imports it as QOA).

**Budget.**
- About 60 SFX families × 1 job ≈ 60 × ~5–10 CU ≈ **300–600 CU** (assuming the cost scales with output length; check after the first multi-variant job).
- About 310 VO lines in about 70 batched TTS jobs: cost to be measured.
- About 10 music pieces: cost to be measured.
- The Krea balance after the ledger is 1,766 CU, so **probe first**.

### 4.4 Fifteen SFX prompts (Seed Audio 1.0)

1. **Blade on metal (Metal armor hit):** "Sound effect only. No music, no speech, no background. [sound: a heavy steel sword striking plate armor and an iron shield, sharp metallic clang with a short ringing tail, chunky cartoon-fantasy weight, close-miked] Four separate variations, each about 0.6 seconds, separated by one second of silence. Each hit slightly different in pitch and brightness."
2. **Axe into flesh/leather (Flesh chop):** "Sound effect only. No music, no speech, no background. [sound: a heavy axe chopping into a leather-armored body, meaty thud with a dull leather slap, short and punchy, no gore squelch, no scream] Four separate variations, about 0.5 seconds each, separated by one second of silence."
3. **Club on wood (Wood bash):** "Sound effect only. No music, no speech, no background. [sound: a thick wooden club hitting a round wooden shield, hollow woody knock with a splintery crack on the strongest hit] Four variations, about 0.5 seconds each, one second of silence between them."
4. **Hammer on stone (Stone hit):** "Sound effect only. No music, no speech, no background. [sound: a big warhammer smashing a stone golem, rocky crack followed by a short gravel crumble] Four variations, about 0.8 seconds each, separated by one second of silence."
5. **Sword whoosh (swing layer):** "Sound effect only. No music, no speech, no background. [sound: fast close sword swings through the air, short airy whoosh, no impact] Six variations, about 0.3 seconds each, separated by one second of silence, alternating lighter and heavier swings."
6. **Bow release (missile launch):** "Sound effect only. No music, no speech, no background. [sound: a wooden longbow released, taut string twang with a quick arrow whoosh leaving] Four variations, about 0.5 seconds each, one second of silence between them."
7. **Arrow impacts:** "Sound effect only. No music, no speech, no background. [sound: an arrow hitting targets: first a solid thunk into a wooden post, then a soft thud into a leather-covered body, then a glancing ping off a metal helmet, then a thud into dirt] Four separate impacts, about 0.4 seconds each, separated by one second of silence."
8. **Fire bolt spell (cast + impact):** "Sound effect only. No music, no speech, no background. [sound: a magical fire bolt is conjured with a rising crackling whoosh, flies, and bursts on impact with a deep warm explosion and crackling embers] One take, about 2 seconds, then two more variations of only the impact burst, each 1 second, separated by one second of silence."
9. **Construction loop, Hearth Wardens:** "Sound effect only. No music, no speech, no voices, no background. [sound: steady rhythmic medieval construction at a timber building site: wooden mallet hammering pegs, a hand saw cutting a plank, an occasional plank dropped on a pile, even density throughout so it can loop seamlessly] About 8 seconds, continuous."
10. **Construction loop, Thornborn:** "Sound effect only. No music, no speech, no background. [sound: a living wooden lodge growing out of the ground: creaking branches stretching, roots pushing through soil, soft wooden knocks and rustling leaves, with a very low breathy organic hum, even density so it can loop seamlessly] About 8 seconds, continuous."
11. **Tree chop + fall:** "Sound effect only. No music, no speech, no background. [sound: single axe strikes into a living tree trunk, solid woody tok with a little leaf rustle] Four separate strikes, about 0.5 seconds each, separated by one second of silence. Then one take of the tree cracking and falling with a heavy leafy crash, about 2.5 seconds."
12. **Gold mine enter/exit + deposit:** "Sound effect only. No music, no speech, no background. [sound: a worker enters a mine: wooden door creak, muffled pickaxe clinks deep inside, door thump] about 1.5 seconds; then separately [sound: a small sack of gold coins dropped on a wooden counter, bright coin jingle] about 0.6 seconds, in two variations. One second of silence between each."
13. **UI click (Wardens):** "Sound effect only. No music, no speech, no background. [sound: a tiny user-interface button press: soft dry wooden knock layered with a tiny brass tick, very short, very close] Six variations, each about 0.1 seconds, separated by one second of silence."
14. **Building / research complete (Wardens):** "Sound effect only. No music, no speech, no background. [sound: a satisfying completion cue: three quick hammer taps on an anvil followed by a warm bronze hand-bell ring that decays naturally] About 1.5 seconds. Then a second variation where the bell is replaced by a bright rising two-note chime with a small sparkle, about 1.2 seconds. One second of silence between them."
15. **Hero level-up (our signature cue):** "Sound effect only. No speech, no background. [sound: a heroic level-up flourish: a fast ascending harp glissando into a warm golden bell strike, with an airy wordless choir 'ah' swell and a soft shimmering tail, bright and uplifting, magical] About 1.4 seconds. Two more variations with slightly different harp runs, separated by one second of silence."

**Bonus prompts** (ambience, creeps, deaths):
- **A1, forest day bed:** "Ambient soundscape only. No music, no speech. [background: calm temperate forest at midday: gentle wind in leaves, a few distant songbirds, light insect buzz, a faraway stream; no sudden loud events, even density for seamless looping] About 60 seconds."
- **A2, forest night bed:** "Ambient soundscape only. No music, no speech. [background: temperate forest at night: steady crickets, soft wind, an occasional distant owl, very sparse; no sudden loud events, even density for looping] About 60 seconds."
- **C1, creep vocal set:** "Creature sound effects only. No music, no human speech, no background. [voice: a dog-sized hunched swamp creature with a croaky throat] An aggressive aggro snarl, then two short attack grunts, then a pained yelp, then a death gurgle. Five separate sounds, separated by one second of silence."
- **D1, Thornborn brute death:** "Creature sound effect only. No music, no speech. [voice: a huge moss-covered forest brute, deep gravelly growl] A short pained roar that collapses into a heavy body thud on soft earth with bones rattling. About 1.5 seconds, two variations separated by one second of silence."

### 4.5 Six music prompts (ElevenLabs Music v2.5, `force_instrumental: true`)

Never include franchise, studio or composer names. Describe the music instead.

1. **Hearth Wardens, in-game 1** (`music_length_ms: 210000`): "Instrumental fantasy strategy-game score for a stubborn, warm-hearted folk of builders and shield-bearers. Chamber folk-orchestra: string section, two French horns, field snare drum, hurdy-gurdy drone, fiddle melody, low whistle, bodhrán, hand bells. D Mixolydian, 92 BPM, proud but gently melancholic, storybook atmosphere. Structure: soft hurdy-gurdy and whistle intro (20 s), main theme on fiddle over strings, a broader B section where horns take the melody with snare, a quiet pastoral interlude with bells, final statement of the theme, then a calm outro that resolves fully on the tonic. Background music that never becomes overwhelming, mid-level dynamics, no vocals."
2. **Thornborn, in-game 1** (`music_length_ms: 210000`): "Instrumental fantasy strategy-game score for a wild, superstitious forest tribe of moss, bone and antler. Frame drums, log drums and udu in a 6/8 over 4/4 polyrhythm, bone flute melody, deep overtone throat-singing drone, bowed psaltery, kalimba, creaking wooden percussion, glassy teal shimmering pads. E Phrygian, 96 BPM, primal yet mystical, misty and ancient. Structure: breathy drone and kalimba intro (20 s), drums enter, bone-flute theme, a hypnotic B section with layered percussion and drone, a sparse misty bridge, return of the theme with full drums, then a slow fade to the drone that ends on the tonic. Background music, no vocals with words."
3. **Main menu theme** (`music_length_ms: 120000`): "Instrumental main-menu theme for an original heroic fantasy strategy game. It starts with a lone hurdy-gurdy drone and a distant frame drum, then strings rise with a noble, hopeful melody on French horn, then a bone flute answers it, joining two cultures. A broad climax with full strings, horns and drums at about 1:20, then a gentle, loopable ending that returns to the hurdy-gurdy drone. 80 BPM, D Dorian, cinematic but warm, no vocals."
4. **Victory stinger** (`music_length_ms: 12000`): "Short instrumental victory fanfare for a fantasy strategy game: field snare roll, two French horns and strings playing a bright rising triumphant phrase in D major, hand bells sparkle, ending on a strong held tonic chord with a natural decay. Total about 12 seconds, no vocals."
5. **Defeat stinger** (`music_length_ms: 12000`): "Short instrumental defeat cue for a fantasy strategy game: a slow low string chord in D minor, a lonely hurdy-gurdy drone, a muffled frame drum heartbeat, a falling horn phrase that does not resolve, fading into silence. Total about 12 seconds, somber, no vocals."
6. **Night / creep-camp exploration layer** (`music_length_ms: 150000`): "Sparse instrumental night-time ambient score for exploring a dark fantasy forest in a strategy game: soft low drone, distant muffled frame drum, occasional plucked harp notes and a breathy low flute, long silences between phrases, mysterious but not scary, 60 BPM, A minor, very low intensity so it can sit under game sound effects, no vocals, ends quietly."

**Loop and polish:**
- Trim the tail.
- For the menu and night layer, build a seamless loop by crossfading the last 2–4 s into the start (Python/numpy, or ffmpeg `acrossfade`).
- Master to about −16 LUFS integrated.
- Export as Ogg Vorbis stereo `-q:a 6`.
- Set the loop in Godot's import options (Ogg supports a loop offset only, forward loop).

For a wordless choir texture, `force_instrumental: true` may strip it. Generate a separate stem with `force_instrumental: false` and the prompt "wordless choir pads, no lyrics, 'ah' vowels only", then layer it (risk: it may still produce words; listen to every take).

### 4.6 Naming and folders (proposal; matches `assets/audio/{sfx,voice,music,ambience}/`)

```
assets/audio/voice/<faction>/<unit>/<category>_<nn>.ogg     # wardens/shieldhand/what_01.ogg
assets/audio/sfx/combat/<swing|hit>_<material>_<nn>.wav       # hit_metal_03.wav
assets/audio/sfx/ui/<faction>/<event>_<nn>.wav
assets/audio/sfx/economy/<event>_<nn>.wav
assets/audio/ambience/<biome>_<day|night>.ogg, sweet_<biome>_<thing>_<nn>.wav
assets/audio/music/<faction>_<nn>.ogg, menu.ogg, victory_<faction>.ogg, defeat_<faction>.ogg
assets_src/audio/...   # raw generations, never shipped; log every job in docs/asset-ledger.md
```

---

## 5. Free CC0 / royalty-free fallback sources

| Source | License | Key terms | What to grab |
|---|---|---|---|
| **Kenney** ([support](https://www.kenney.nl/support), [audio packs](https://kenney.nl/assets/category:Audio)) | **CC0** | "All game assets … are public domain licensed (CC0)". "Attribution is not required". Commercial use OK. Kenney's logo is reserved. | [Impact Sounds](https://kenney.nl/assets/impact-sounds) (130 files, CC0), [RPG Audio](https://kenney.nl/assets/rpg-audio) (50 files, CC0: foley, footsteps, weapons), plus Interface Sounds, UI Audio, Music Jingles, Voiceover Pack (Fighter) as UI and stinger placeholders |
| **OpenGameArt** ([FAQ](https://opengameart.org/content/faq)) | Mixed. **Filter to CC0.** | CC0: no credit needed. CC-BY / OGA-BY: credit plus change notes. The FAQ says CC-BY / CC-BY-SA require avoiding DRM distribution, so prefer CC0 or OGA-BY. CC-BY-SA: derivatives must be share-alike. GPL: avoid for art. | ["Medieval sound effects: Weapon impacts"](https://opengameart.org/node/146863) (CC0, 48 weapon-on-weapon WAVs), ["RPG Sound Pack"](https://opengameart.org/content/rpg-sound-pack) by artisticdude (CC0, 95 WAVs: battle, inventory, 6 UI, NPC creature sounds including ogre/beast/slime) |
| **Freesound** ([FAQ](https://freesound.org/help/faq/)) | Per sound: CC0, CC-BY or CC-BY-NC | Use the search page's **license filter → Creative Commons 0**. CC-BY needs a credits line (title, user, link, license). **Never use CC-BY-NC** for this project (it bars earning money). | Ambience sweeteners, specific foley that AI drifts on (latches, chains, bowstrings) |
| **Sonniss GDC bundles** ([license](https://sonniss.com/gdc-bundle-license/), [download](https://gdc.sonniss.com/)) | Royalty-free, "unlimited user license" | Commercial use in games OK. **No attribution required.** Usable on unlimited projects for life. **Prohibited:** distributing the sounds *as sound effects* (including modified versions) without permission, and **using them to train AI** (even generators of similar sounds) ([GameFromScratch 2024](https://gamefromscratch.com/sonniss-27-5gb-sound-effect-giveaway-at-gdc-2024/)). | Pro-grade impacts, foley and ambiences. **Keep them out of any AI pipeline**: never use them as reference audio for Seed Audio or ElevenLabs. If the game is open-sourced, the raw files cannot sit in a public repo (they would be redistributed as SFX), so ship only packed builds or exclude them. |

**Never use:** extracted WC3/Reforged files, Hive Workshop soundsets (derived from Blizzard audio), YouTube rips, or "WC3-style" packs that sample the game.

---

## 6. Godot 4 implementation tips

### 6.1 Players: 3D vs 2D in an RTS

| Use | Node | Why |
|---|---|---|
| Acks, advisor, hero events, UI, music, ambience beds | `AudioStreamPlayer` (non-positional) | They must be heard regardless of the camera. Bus routing is enough. |
| Combat, spells, deaths, work loops, doodads, ambience sweeteners | **`AudioStreamPlayer3D`**, pooled | True 3D panning and attenuation from the camera-follow listener. The camera tilts (−56° pitch), so 3D is more correct than 2D. |
| `AudioStreamPlayer2D` | Avoid | Our world is 3D. Faking it with 2D needs manual projection. |

**`AudioStreamPlayer3D` facts** ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer3d.html)):

| Property | Default | Note |
|---|---|---|
| `attenuation_model` | inverse distance | Values: 0 inverse, 1 inverse square, 2 logarithmic, 3 disabled |
| `unit_size` | 10 | – |
| `max_db` | +3 | – |
| `max_distance` | 0 (off) | Works linearly, unlike `unit_size`. Beyond it the player is not mixed at all, which saves CPU. |
| `max_polyphony` | 1 | Oldest sound is cut when exceeded |
| `panning_strength` | 1.0 | – |
| `attenuation_filter_cutoff_hz` | 5000 | 20500 disables the distance low-pass |
| `attenuation_filter_db` | −24 | – |
| `doppler_tracking` | off | Keep it off |

**Listener:** by default the listener is the current camera. Add an `AudioListener3D` and call `make_current()` to override it.

### 6.2 Variation and polyphony

- **`AudioStreamRandomizer`** ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreamrandomizer.html)):
  - `playback_mode` defaults to `PLAYBACK_RANDOM_NO_REPEATS`.
  - `random_pitch` is a frequency multiplier range (1/x … x). Use **1.06 (≈ ±1 semitone) to 1.12 (≈ ±2 semitones) for SFX** and **1.0 for voices**, so actors don't sound like chipmunks.
  - `random_volume_offset_db` is ±dB; use 1.5–2.
  - Per-stream `weight` lets rare variants appear less often.
  - Make one randomizer `.tres` per sound family.
- **`AudioStreamPolyphonic`** ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreampolyphonic.html)):
  - `polyphony` defaults to 32.
  - `get_stream_playback().play_stream(stream, from_offset=0, volume_db=0, pitch_scale=1.0, playback_type=0, bus=&"Master")` returns an id, or `INVALID_ID` (−1) when full ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaybackpolyphonic.html)).
  - Use it for **2D UI and ack layering** (one player, many one-shots, per-shot bus). It is less useful for 3D because all shots share the node's position.
- **Avoid one player per unit.** 200 units × player nodes is wasteful. Use a pool of about 24 `AudioStreamPlayer3D`s moved to the event position. Looping work sounds (chop, build) get a dedicated small pool of 3–4.

### 6.3 Music and ambience streams

- **`AudioStreamPlaylist`** ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaylist.html)) has `fade_time` 0.3 s, `loop`, `shuffle` and up to 64 streams. It has **no gap setting**, so for WC3-style 20–40 s silences, drive a single `AudioStreamPlayer` from a timer: on `finished`, wait `randf_range(20, 40)` s, then play the next shuffled track.
- **`AudioStreamInteractive`** ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreaminteractive.html)) has clips and a transition table with from-time IMMEDIATE / NEXT_BEAT / NEXT_BAR / END, fade modes (`FADE_AUTOMATIC` recommended), filler clips and auto-advance. Switch at runtime with `get_stream_playback().switch_to_clip_by_name(&"victory")` ([docs](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaybackinteractive.html)). Use it for **menu → in-game → victory/defeat** transitions.
- **Ambience:** two `AudioStreamPlayer`s (day and night beds) crossfaded with a `Tween` over ~8 s at dawn and dusk. A timer spawns 3D sweeteners at random positions within 20–35 m of the listener every 4–12 s.

### 6.4 Import settings ([docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_audio_samples.html))

- **WAV** for short, repetitive SFX. The default compression **QOA** is smaller than IMA-ADPCM with less quality loss.
- **Ogg Vorbis** for music, speech and long effects. Ogg/MP3 support only a forward loop with a **loop offset**.
- Voices and SFX: `Force > Mono` is fine for most. Voices can use `Force > Max Rate` 22,050 Hz (the docs say voices "can often go to 22 kHz", which is also WC3's rate).
- `Edit > Trim` removes silence below −50 dB and adds a 500-sample fade. **Don't** use `Normalize` on everything: it destroys the relative loudness we mastered.
- Put reverb on buses rather than baking it in. The exception is character voice colour (§4.2), which defines identity.

### 6.5 Buses and ducking

- Buses are referenced by name. Renaming a bus breaks references and silently falls back to Master. Keep names in a constants file. The layout is saved in `res://default_bus_layout.tres`. A bus that has been silent for a few seconds is auto-disabled, which saves CPU ([docs](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)).
- **Ducking:** put an `AudioEffectCompressor` on Music and set `sidechain = &"Voice"` ([docs](https://docs.godotengine.org/en/stable/classes/class_audioeffectcompressor.html)).
  - Starting values: `threshold −26 dB`, `ratio 4`, `attack_us 2000` (the maximum is 2 ms; the default of 20 µs is very fast), `release_ms 350`, `gain 0`.
  - Do the same on Ambience with ratio 3.

### 6.6 Code sketch: pooled, prioritized world SFX plus acks

```gdscript
# autoload/audio.gd (sketch, Godot 4.x)
extends Node

const POOL_SIZE := 24
const MAX_PER_ID := 4           # WC3 allowed 4 concurrent plays per file
const SAME_ID_SPACING_MS := 80  # WC3 needed 100 ms
const CULL_DIST := 50.0         # metres from listener

var listener: AudioListener3D
var _pool: Array[AudioStreamPlayer3D] = []
var _meta := {}                 # player -> {id, prio}
var _last_ms := {}              # id -> last play time (msec)

func _ready() -> void:
	listener = AudioListener3D.new()
	add_child(listener)
	listener.make_current()
	for i in POOL_SIZE:
		var p := AudioStreamPlayer3D.new()
		p.unit_size = 13.0
		p.max_distance = CULL_DIST
		p.max_db = 0.0
		p.panning_strength = 0.6
		p.attenuation_filter_cutoff_hz = 20500.0
		add_child(p)
		_pool.append(p)

func follow_camera(focus_point: Vector3) -> void:
	listener.global_position = focus_point + Vector3(0, 6, 0)

func play_at(id: StringName, stream: AudioStream, pos: Vector3, prio: int, bus: StringName = &"Combat") -> void:
	if listener.global_position.distance_to(pos) > CULL_DIST:
		return
	var now := Time.get_ticks_msec()
	if now - int(_last_ms.get(id, -100000)) < SAME_ID_SPACING_MS:
		return
	var same := 0
	for p in _pool:
		if p.playing and _meta.get(p, {}).get("id") == id:
			same += 1
	if same >= MAX_PER_ID:
		return
	var target: AudioStreamPlayer3D = null
	for p in _pool:
		if not p.playing:
			target = p
			break
	if target == null:  # steal lowest priority, oldest first
		var best_score := INF
		for p in _pool:
			var pr: int = _meta.get(p, {}).get("prio", 0)
			var score := pr * 1000.0 - p.get_playback_position()
			if pr <= prio and score < best_score:
				best_score = score
				target = p
	if target == null:
		return
	target.stop()
	target.stream = stream  # an AudioStreamRandomizer resource
	target.bus = bus
	target.global_position = pos
	_meta[target] = {"id": id, "prio": prio}
	_last_ms[id] = now
	target.play()

# --- Acks: 2D, one at a time, annoyed after rapid clicks -----------------
const ANNOY_CLICKS := 4         # WC3 threshold unverified, so tune it
const ANNOY_WINDOW_MS := 3000
@onready var _ack := AudioStreamPlayer.new()
var _click_unit: Object = null
var _click_count := 0
var _click_start := 0
var _annoy_idx := {}            # unit_type -> next line index (play in order)

func on_unit_clicked(unit: Object, vs: Dictionary) -> void:
	# vs = {"what": AudioStreamRandomizer, "annoyed": Array[AudioStream], "type": StringName}
	var now := Time.get_ticks_msec()
	if unit == _click_unit and now - _click_start < ANNOY_WINDOW_MS:
		_click_count += 1
	else:
		_click_unit = unit
		_click_count = 1
		_click_start = now
	var annoyed: Array = vs["annoyed"]
	if _click_count >= ANNOY_CLICKS and not annoyed.is_empty():
		var i: int = _annoy_idx.get(vs["type"], 0)
		_play_ack(annoyed[i % annoyed.size()])
		_annoy_idx[vs["type"]] = i + 1
	else:
		_play_ack(vs["what"])

func _play_ack(s: AudioStream) -> void:
	if _ack.get_parent() == null:
		_ack.bus = &"Acks"
		add_child(_ack)
	_ack.stream = s
	_ack.play()  # new selection interrupts the old line, like an RTS should
```

### 6.7 Event wiring (proposal)

- **Emit combat sound from the animation's hit frame,** not from damage resolution. WC3 models can carry sound Event Objects. The Hive tutorial notes that a GUI trigger tied to the attack/damage event plays the gun sound at missile impact with slow missiles: "Hearing a bullet launch 4 seconds after it is really launched by the tower is quite weird" ([Hive](https://www.hiveworkshop.com/threads/using-sounds-the-example-of-projectiles.179184/)).
- Missiles: launch at the shooter on release, and impact at the target on arrival.
- Data-driven: `data/units.json` gets `sound: {weapon: "chop", armor_material: "flesh", voice_set: "wardens/shieldhand", death: "brute"}`.
- Melee hit = `play_at("swing_chop", …)` + `play_at("hit_flesh", …)` with a 0–20 ms offset.
- Under-attack alert: fire it when a structure or unit of ours takes damage outside the current view rectangle (or the alert location is not on screen), with a 20 s cooldown per ~20 m region, plus a minimap ping.
- Building select: one-shot per building type via the UI bus (2D), so it is heard even when zoomed out.
- Tests: a headless unit test that the pool never exceeds `MAX_PER_ID` and that culling works. In CI, use `--audio-driver Dummy`.

---

## 7. Open questions and next steps

1. **Probe costs.** One `eleven_v4` TTS batch (5 lines) and one 30 s `music-v2.5` clip. Log them in `docs/asset-ledger.md`, then fix the VO and music budget.
2. **Verify the batching trick.** Do Seed Audio and TTS respect "N variations separated by silence" and `[long pause]` reliably?
3. Decide the exact annoyed-click threshold by playtest. Start at 4 clicks in 3 s.
4. Listen-test that the pitch-shifted Thornborn voices still read as **characters**, not effects. Keep pitch shifts within roughly 0.8–1.15.
5. Before 31 Dec 2026, regenerate any line that might be needed later, or switch to the replacement voices ElevenLabs maps the defaults to (not available via Krea's list yet).

## 8. IP guardrails (audio)

- No WC3/Blizzard audio files, rips or "remakes". No WC3 lines, catchphrases or close paraphrases (e.g. "Job's done", "Work work", "Ready for action"). No WC3 melodies or motifs, including the level-up cue.
- Never prompt with "Warcraft", "Blizzard", composer names or unit names. Describe the sound instead.
- No voice cloning of any WC3 actor or any other real person. Krea's public API offers no cloning, but its web app lists a "Qwen Voice Clone" model. Never use it, or any other cloning tool, on WC3 audio.
- Hive Workshop soundsets and fan "WC3-style" packs are off-limits.
- Sonniss assets stay out of AI tools (license). CC-BY assets require a credits file.

## 9. Fact-check log (2026-10-16)

**Re-verified against the source:**
- jassbot `CreateSound`: 4 plays per file, ≥ 0.1 s apart, 16 sounds overall, and the 7 EAX presets.
- Hive music-list thread: Race1–3 + RaceX1 rotation, with "timeouts of ca. 20 to 40 seconds between songs".
- Warcraft Wiki OST: composers and lengths (3:58–5:14, 1:08 / 1:12, 14:47).
- Warcraft Wiki quote pages: Human and Orc line counts and quoted lines.
- Krea API schemas:
  - TTS: 2000 chars, 21 voices, default Bella, and every casting `voice_id`.
  - Music v2.5: 4100 chars, 3,000–600,000 ms, `force_instrumental` default false.
  - Seed Audio: prompt only, 2048 chars.
- ElevenLabs:
  - Default voices expire on 31 Dec 2026.
  - Audio tags work on v4, v4 Turbo and v3.
  - Voice Design flow (`eleven_multilingual_ttv_v2`, ogre example).
- Sonniss license: no attribution, unlimited projects, no redistribution as SFX, no AI training.
- Kenney: 130 / 50 files, CC0. OpenGameArt: 48 / 95 files, CC0. Freesound license options.
- Godot docs:
  - `AudioStreamPlayer3D` defaults, plus the `max_distance` and 20500 Hz notes.
  - `AudioEffectCompressor` `attack_us` range 20–2000 (default 20).
  - `AudioStreamPlaylist` `fade_time` 0.3 s and 64 streams.
  - `AudioStreamPolyphonic` polyphony 32, and the `play_stream` signature.
  - `AudioStreamRandomizer` defaults.
  - `AudioStreamInteractive` enums.
  - Import notes: QOA default, 22 kHz voices, Trim at −50 dB with a 500-sample fade.
  - Bus routing, rename fallback and auto-disable.
- Hive projectiles tutorial: 600 / 10,000 / 3,000, channel 5, CombatSoundsEAX, and the "most of the bullets sounds were not played" quote.
- Engadget: Stafford was "director of the Audio Department".
- Warcraft Wiki: Bill Roper voiced the Peon.
- All 15 YouTube links: titles confirmed via oEmbed.

**Corrected:**
- Loudness: the cited interview says −23 LUFS, not −24.
- Krea cloning: the web app lists Qwen Voice Clone, but the API does not.
- Overwatch pillars: "Pavlovian response" is not in the cited text.
- Company of Heroes 3: the quote was missing a word ("awesome, epic, cinematic").
- Construction methods per race: not in the cited page.
- Hive Sound Editor: the 22 kHz guidance is in a reply, not the guide.
- Hive projectiles: the "late missile" claim was reworded to match the source.
- Wowpedia links were swapped for the equivalent Warcraft Wiki pages, which were verified.

**Could not verify** (blocked: 403 / 429 / 402): Liquipedia Daytime, Neowin 1.10, Giant Bomb, the GDC Diablo IV schedule, both Audiokinetic pages, the PC Gamer body, and the Wowhead recap of Game Informer.

---

## Sources

**WC3 audio, credits and mechanics**
- [Warcraft Wiki: Quotes of Warcraft III / Human Alliance](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Human_Alliance)
- [Warcraft Wiki: Quotes of Warcraft III / Orc Horde](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_III/Orc_Horde)
- [Warcraft Wiki: Quotes of Warcraft II](https://warcraft.wiki.gg/wiki/Quotes_of_Warcraft_II)
- [Warcraft Wiki: Warcraft III: Reign of Chaos Soundtrack](https://warcraft.wiki.gg/wiki/Warcraft_III:_Reign_of_Chaos_Soundtrack)
- [Warcraft Wiki: Warcraft III: The Frozen Throne Soundtrack EP](https://warcraft.wiki.gg/wiki/Warcraft_III:_The_Frozen_Throne_Soundtrack_EP)
- [Warcraft Wiki: Tracy W. Bush](https://warcraft.wiki.gg/wiki/Tracy_W._Bush)
- [Warcraft Wiki: Peon](https://warcraft.wiki.gg/wiki/Peon)
- [Warcraft Wiki: Building (Warcraft III)](https://warcraft.wiki.gg/wiki/Building_(Warcraft_III))
- [Warcraft Wiki: Warcraft III armor and attack types](https://warcraft.wiki.gg/wiki/Warcraft_III_armor_and_attack_types)
- [Engadget (2007): Who made Warcraft's soundtrack?](https://www.engadget.com/2007-07-31-who-made-warcrafts-soundtrack.html)
- [Game Informer (2018): Inside the Creation of Warcraft III's Soundtrack](https://www.gameinformer.com/exclusive-feature/2018/11/16/inside-the-creation-of-warcraft-iiis-soundtrack)
- [PC Gamer: Reforged keeps the voice actors](https://www.pcgamer.com/uk/warcraft-3-reforgeds-story-isnt-changing-to-fit-wow-because-people-love-the-voice-actors/)
- [IMDb: Warcraft III full credits](https://m.imdb.com/title/tt0259104/fullcredits/cast)
- [Hive Workshop: Custom music lists (default race music, 20–40 s gaps)](https://www.hiveworkshop.com/threads/custom-music-lists.294961)
- [Hive Workshop: Sound Editor guide (properties, day/night ambient themes, 22 kHz mono)](https://www.hiveworkshop.com/forums/f278/sound-editor-39234/)
- [Hive Workshop: Using sounds, the example of projectiles](https://www.hiveworkshop.com/threads/using-sounds-the-example-of-projectiles.179184/)
- [Hive Workshop: Voidwalker soundset (category names and counts)](https://www.hiveworkshop.com/threads/warcraft-iii-voidwalker-soundset.345038/)
- [Hive Workshop: Where do WC3 sound effects come from?](https://www.hiveworkshop.com/threads/where-do-sound-effects-of-warcraft-3-come-from.24729/latest)
- [Hive Workshop: Game sound setting modification](https://www.hiveworkshop.com/threads/important-game-sound-setting-modification.245352)
- [Hive Workshop: couple of questions (Error.wav path)](https://www.hiveworkshop.com/threads/couple-of-questions.160141)
- [jassbot: CreateSound (EAX presets, 4-per-file / 0.1 s / 16-sound limits)](https://lep.duckdns.org/jassbot/doc/CreateSound)
- [Liquipedia: Daytime (480 s cycle)](https://liquipedia.net/warcraft/Daytime) (rate-limited during the fact-check; not re-verified)
- [Neowin: WC3 patch 1.10 (upgrade/research complete text)](https://www.neowin.net/amp/warcraft-iii-patch-v110-released/) (403 during the fact-check; unverified)
- [Giant Bomb: Piss Lines](https://giantbomb.com/wiki/Concepts/Piss_Lines) (403 during the fact-check; unverified)

**Videos** (oEmbed-verified 2026-10-16)
- [GI: WC3 Soundtrack](https://www.youtube.com/watch?v=ouNEzATaDMs) · [Footman Sounds](https://www.youtube.com/watch?v=KgOswctVGpA) · [Orc Quotes](https://www.youtube.com/watch?v=MXgr6SYYNZM) · [Human Funny Quotes](https://www.youtube.com/watch?v=QiwiuDW52hY) · [Human Building Sounds](https://www.youtube.com/watch?v=3wHMAluEC6g) · [Undead Building Sounds](https://www.youtube.com/watch?v=WHwDTfF8qdo) · [Level up](https://www.youtube.com/watch?v=r6v8zgsXJrU) · [Gold mine](https://www.youtube.com/watch?v=lD55CrlRPl0) · [Hero death tier list](https://www.youtube.com/watch?v=U6ZrCOARhZc) · [Icons & Sounds secrets](https://www.youtube.com/watch?v=WzLnOyWTZsA) · [Orcs Music & Ambience](https://www.youtube.com/watch?v=d-HYwNeJRQM) · [Blackrock & Roll](https://www.youtube.com/watch?v=uyx5AYHI2Vs) · [Rise of the Ancients](https://www.youtube.com/watch?v=nxiGNossTLg) · [Human campaign longplay](https://www.youtube.com/watch?v=53Ot4lq6YsY) · [Sound of WoW](https://www.youtube.com/watch?v=gy4ePZnvuKc)

**Game-audio craft**
- [GDC Vault: Overwatch: The Elusive Goal: Play by Sound](https://gdcvault.com/play/1023010/Overwatch-The-Elusive-Goal-Play)
- [PCGamesN: Overwatch "play by sound"](https://pcgamesn.com/overwatch/overwatch-devs-on-creating-a-game-you-can-play-by-sound-and-announcing-dolby-atmos-support)
- [Audiokinetic: Overwatch game audio using Wwise](https://www.audiokinetic.com/en/blog/overwatch-game-audio-using-wwise-1/)
- [GDC schedule: Diablo IV audio systems deep dive](https://schedule.gdconf.com/session/diablo-iv-audio-systems-deep-dive-living-audio/899258) (403 during the fact-check; unverified)
- [Designing Sound: The Sound of StarCraft II](https://designingsound.org/2010/08/17/the-sound-of-starcraft-ii-wings-of-liberty/)
- [Relic: Company of Heroes 3 audio](https://www.cosmocover.com/newsroom/company-of-heroes-3-how-relic-brings-wwii-to-life-through-audio/)
- [Audiokinetic: The Music of Age of Empires IV](https://blog.audiokinetic.com/en/the-music-of-age-of-empires-iv/)
- [Designing Sound: Loudness standards interview (Garry Taylor; −23 LUFS PS3 / −18 LUFS Vita, ±2 LU)](https://designingsound.org/2012/07/30/video-games-and-loudness-standards-interview-with-sonys-garry-taylor/)
- [Unity discussions: managing hundreds of audio sources (pooling, reserved high-priority voices)](https://discussions.unity.com/t/what-is-the-recommended-way-to-manage-hundreds-to-thousands-of-audio-sources/809600)

**Generation tools**
- [Krea API: Seed Audio 1.0](https://www.krea.ai/docs/api-reference/audio/seed-audio-10)
- [Krea API: ElevenLabs TTS](https://www.krea.ai/docs/api-reference/audio/elevenlabs-tts.md)
- [Krea API: ElevenLabs Music v2.5](https://www.krea.ai/docs/api-reference/audio/elevenlabs-music-v25.md)
- [Krea API: ElevenLabs Music v2](https://www.krea.ai/docs/api-reference/audio/elevenlabs-music-v2.md)
- [Krea user guide: Audio](https://www.krea.ai/docs/user-guide/features/audio.md) (the web app lists ElevenLabs TTS/Music/Video To Music, Qwen TTS, Qwen Voice Clone, ThinkSound and MMAudio; the public API `list_models` on 2026-10-16 returned only elevenlabs/music, music-v2, music-v2.5, tts and bytedance/seed-audio-1.0)
- [Segmind: Seed Audio 1.0 explained](https://blog.segmind.com/seed-audio-1-0-bytedances-all-in-one-audio-model-explained/)
- [ElevenLabs: Voice Design guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/voices/voice-design)
- [ElevenLabs: Audio tags list (v4/v3)](https://elevenlabs.io/blog/elevenlabs-audio-tags-list)
- [ElevenLabs: Prompting Eleven v3](https://elevenlabs.io/docs/best-practices/prompting)
- [ElevenLabs help (IT): default voices expire 31 Dec 2026](https://elevenlabs.io/docs/it/help-center/product/voices/my-voices/what-are-default-voices.md)
- [Unite.AI: Eleven v4 launch](https://unite.ai/elevenlabs-launches-eleven-v4-with-low-latency-turbo-variant)
- [WaveSpeed: ElevenLabs voice ID list (voice descriptions)](https://wavespeed.ai/docs/docs-api/elevenlabs/elevenlabs-voice-id)

**Free and royalty-free libraries**
- [Kenney: support / license (CC0)](https://www.kenney.nl/support) · [Kenney audio category](https://kenney.nl/assets/category:Audio) · [Impact Sounds](https://kenney.nl/assets/impact-sounds) · [RPG Audio](https://kenney.nl/assets/rpg-audio)
- [OpenGameArt FAQ (licenses)](https://opengameart.org/content/faq) · [Medieval weapon impacts (CC0)](https://opengameart.org/node/146863) · [RPG Sound Pack (CC0)](https://opengameart.org/content/rpg-sound-pack)
- [Freesound FAQ (CC0 / CC-BY / CC-BY-NC, license filter)](https://freesound.org/help/faq/)
- [Sonniss GDC bundle license](https://sonniss.com/gdc-bundle-license/) · [Sonniss GDC download](https://gdc.sonniss.com/) · [GameFromScratch: Sonniss GDC 2024 (AI-training ban)](https://gamefromscratch.com/sonniss-27-5gb-sound-effect-giveaway-at-gdc-2024/)

**Godot 4 documentation**
- [AudioStreamPlayer3D](https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer3d.html) · [AudioStreamPlayer](https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer.html) · [AudioStreamRandomizer](https://docs.godotengine.org/en/stable/classes/class_audiostreamrandomizer.html) · [AudioStreamPolyphonic](https://docs.godotengine.org/en/stable/classes/class_audiostreampolyphonic.html) · [AudioStreamPlaybackPolyphonic](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaybackpolyphonic.html)
- [AudioStreamInteractive](https://docs.godotengine.org/en/stable/classes/class_audiostreaminteractive.html) · [AudioStreamPlaybackInteractive](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaybackinteractive.html) · [AudioStreamPlaylist](https://docs.godotengine.org/en/stable/classes/class_audiostreamplaylist.html)
- [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html) · [AudioEffectCompressor (sidechain)](https://docs.godotengine.org/en/stable/classes/class_audioeffectcompressor.html) · [Importing audio samples](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_audio_samples.html)
- [uhiyama-lab: 3D audio in Godot (guide)](https://uhiyama-lab.com/en/notes/godot/3d-audio-spatial-sound/)
