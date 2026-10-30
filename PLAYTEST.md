# Vibecraft: Playtest 3, "Heroes and creeps"

Thanks for playing. This playtest is about **heroes**: levelling them on the neutral creeps and on
the enemy, learning and casting their abilities, items and shops, reviving fallen heroes, and the
two factions' worker defences. You play the same **skirmish against the computer** as in
Playtest 2, but now the computer brings its heroes too: it creeps, casts and revives. We want to
know whether heroes *feel* like the classic hero-RTS games, and whether the interface makes them
easy to use.

**New since Playtest 2:** the game starts **fullscreen** (Alt + Enter or F11 switches to a window
and back, and it remembers your choice).

If you have not answered the Playtest 2 questions yet, the short version is at the end.

## How to run it

1. Download the build as a ZIP and unpack it anywhere:
   https://github.com/m1omg/Vibecraft/archive/refs/heads/claude/clever-heisenberg-i8649y.zip
   (or `git fetch` and `git checkout claude/clever-heisenberg-i8649y`).
2. Install **Godot 4.7.2** (the standard build, not .NET) from godotengine.org.
3. Start Godot, click **Import**, and pick `project.godot` in the unpacked folder. The first
   import takes a minute or two.
4. Press **F5**. The main menu opens.
5. Under **Skirmish**, pick your side (**Play as Brennmark** or **Play as the Tormai**) and the
   computer's difficulty (**Easy / Normal / Hard**), then click **Skirmish** (or press Enter).

If it will not start or runs slowly on an older or integrated GPU, use the Compatibility renderer:
**Project → Project Settings → Rendering → Renderer → Rendering Method = `gl_compatibility`**,
then F5 again.

## The match

- You start in the **south-west** of Wether Downs with a **hall, five workers, 500 gold and 150
  lumber**. The computer starts the same way in the north-east, as the other faction.
- **Fog of war is on.** You see only what your units and buildings see. Ground you have scouted
  stays visible but dark; enemy buildings you saw stay as "ghosts" where you last saw them.
- **Neutral creeps** sit at camps around the map (the shield pips on the minimap). They leave
  you alone unless you get close, and most of them **sleep at night**.
- **Goal:** destroy **every enemy building**. You lose when you have no buildings left (units do
  not count). If you lose your last hall, you have **120 s** to finish a new one (a countdown
  appears at the top right), or all your buildings are revealed to the enemy.
- The **Normal** computer usually attacks around 8–10 minutes, after creeping with its hero.
  **Easy** waits until at least 10 minutes. **Hard** builds a little faster and attacks sooner.

## Economy and building in short (as in Playtest 2)

- **Gold:** right-click a Gold Seam with workers (or press **G** and click it). One worker is
  inside at a time; about **five workers saturate a seam** (≈ 10 gold/s). More add very little.
- **Lumber:** right-click a tree. Brennmark Hodmen carry 10 lumber per trip, Tormai Yurtwrights
  15. Lumber goes to the hall or the faction's lumber building (Timber Yard / Casting Pit), so
  build one at the tree line.
- **Return Cargo (C):** a worker carrying something takes it home, then goes back to its job.
- **Food:** every unit costs food. Crofts (+7) and Home Yurts (+10) raise the cap; halls give
  12 (Brennmark) or 10 (Tormai). Training waits when you are short, and you get a warning.
- **Upkeep:** above **50 food**, mined gold is taxed **30 %**; above **80 food**, **60 %**. The top
  bar shows the current rate (green / amber / red).
- **Building:** select a worker, press **B** (or **V** for advanced buildings), then the
  building's letter. A sketch of the building follows your mouse over a grid: **green** cells
  are free, **red** cells are blocked, black cells are unexplored. Left-click places it. Hold
  **Shift** to place several in a row. The cost is checked when you order and paid when the worker
  arrives.
  - **Brennmark** can put up to three Hodmen on one site (right-click the site): each extra one
    speeds it up but costs a little lumber. **Tormai** sites take one Yurtwright only.
  - **Cancel** a site (Esc or the Cancel button) to get 75 % back. **Repair (R)** mends damaged
    buildings for a share of their price.
- **Training:** select a building and press the unit's letter (shown on the button). **Shift**
  queues five. Click a slot in the queue (bottom middle) to cancel it, or press Esc to cancel the
  last one; the cost comes back in full. Right-click the ground, a unit or a Gold Seam to set the
  **rally point** (or press **R**): new workers sent to a seam start mining.
- **Research and tier 2:** research buttons sit on the building that researches them. The hall's
  upgrade (**U**: Walled Burg / Banner Shell) needs an Oath Hall / Naming Stones, takes about two
  minutes and unlocks the advanced buildings and units. Nothing else trains at the hall while it
  upgrades.

## Heroes

- Build your **altar** (Oath Hall / Naming Stones) and train a hero. The **first hero is free** and
  comes with a **recall item** (Way-Home Horn / Way-Home Felt). A hero costs 5 food; you get one
  hero slot at tier 1, two at tier 2.
- **XP:** a hero earns XP when its side kills enemies or creeps **within about 19 m** of it (the
  XP is shared between your heroes there; far away it is lost). Creeps give less XP as the hero
  grows and none from level 5, so a hero must fight the enemy to keep growing. The cap is
  level 10. You see XP flying to the hero as small chips, then the level-up: the ring under the
  hero lights a new segment and its emblem stands up behind it.
- **Learning:** each level gives one **skill point**. The hero's button (top left) shows "+N",
  and the card shows **Learn (O)**. On the Learn page the abilities sit on the bottom row with the
  same letters; ranks 2 and 3 need hero levels 3 and 5, the ultimate needs level 6. Esc goes back.
- **Casting:** an ability's letter (or the button) casts it. Abilities that need a target show a
  cross cursor: click a unit or the ground (area abilities show their circle under the cursor);
  right-click or Esc cancels. Mana and cooldown are spent when the spell goes off; the button
  shows a dark sweep and the seconds left, or a hatch with a blue drop when mana is short.
- **The hero bar** (top left): one button per hero with its level, health, mana and XP. Click
  selects (again: centres the camera), F1–F3 too. Fallen heroes turn grey.
- **Revive:** a fallen hero keeps its level, skills and items. Revive it at your **altar** (its
  train button becomes **Revive**, from 170 gold at level 1, taking 36 s up to 110 s), or
  instantly at the neutral **Coaching Inn** (more expensive, comes back with half its health).

| Hero | Abilities (letter) |
|---|---|
| **Wheel Marshal** (Brennmark, tough support) | **L** Linden Balm (heal, splashes to friends nearby) · **B** Brace the Wheel (nearby enemies must attack her, she gains armour) · **C** Measured Cadence (aura: faster attacks) · **R** The Wagon Ring (ultimate: friends nearby cannot drop below 1 HP for 7 s, then heal) |
| **Firewright** (Brennmark, fire caster) | **N** Naphtha Flask (fire burst, the ground keeps burning) · **F** Fuse Mark (a mark that explodes after 4 s) · **W** Incendiary Wadding (aura: ranged friends set targets burning) · **B** Grand Bombard (ultimate: a heavy gun for 25 s) |
| **The Uncut** (Tormai, duelist) | **D** Dust Veil (invisible and faster; the first blow hits harder) · **L** Braid Lash (damage, drags the target closer and roots it) · **C** Clean Cut (passive critical hits) · **T** Through the Tall Grass (ultimate: faster attacks, every blow cuts through a line) |
| **Skymirror** (Tormai, seer) | **G** Sunglint (a cone of glare: damage and misses) · **B** Bronze Window (look anywhere on the map; rank 3 shows invisible units) · **W** Hail-Swifts (summons birds) · **U** Swallowed Sun (ultimate: darkness over an area, enemies inside see 3 m and miss) |

## Creeps

- Creep camps guard the map: **green** (easy), **amber** and **red** (hard). Pulling one creep
  wakes the whole camp. Kill them for **gold** (a coin pop over each creep, taxed by upkeep) and
  hero XP; the strongest creep of a camp often carries an **item** that drops where it falls.
- **Night (18:00–06:00):** most camps fall asleep (small breaths of smoke over them). Your units
  never attack sleeping creeps on their own, so night is safe for scouting. A hit, a building
  started next to them or a trade at a nearby shop wakes them.
- Creeps that chase you too far, or fight nobody for 10 s, walk back to their camp
  **invulnerable** and heal fully there. Some creeps cast spells (smoke, heals, stuns, crows).

## Items and shops

- A selected hero shows its **six item slots** between the selection panel and the card, with
  the keys **numpad 7 8 / 4 5 / 1 2**. Click or press the key to use an item (some ask for a
  target); right-click a slot, then click the ground to drop it or another hero to hand it over.
  Rest the mouse on a slot for what it does.
- Right-click an item on the ground to pick it up. **Power-ups** (berries, a purse, a tally-stick)
  act at once. Permanent items (a gorget, a brass, an amulet) add their bonus while carried.
- **Shops:** your faction shop (Curio Cabinet / Tea Tent) and the neutral **Weighstall** sell to
  your hero when it stands next to the shop: select the shop and press the item's letter. Stock
  refills over time. The Weighstall also has the **Fair Exchange** (gold for lumber and back,
  from 3:00), and the **Coaching Inn** revives fallen heroes at once.
- **Recall** (Way-Home Horn / Felt): use it and click a spot; after 5 s the hero and up to 23 of
  your units around it return to your hall nearest that spot. Any order cancels it and keeps
  the item.

## Worker defence (faction signatures)

- **Brennmark: Levy Horn (L on the Moot Hall).** Every Hodman near the hall takes up a flail and
  fights as a **Flail Levy** for 40 s, keeping what it carried. **Lay Down Flails (D on the hall)**
  or **Lay Down the Flail (D on a levy)** sends them back to what they were doing; so does
  straying more than 30 m from the halls.
- **Tormai: Sound the Gong (G on the Shell Hall).** Yurtwrights near the hall run into **Home
  Yurts** (three each); a yurt slings stones at enemies, one sling per worker inside. Press the
  hall again (**All Clear**) or **Unload All (U)** on a yurt to let them out; a badly damaged yurt
  throws them out. A Yurtwright's **Roll the Felt (F)** sends it into the nearest yurt with room.

## Controls

| Action | Input |
|---|---|
| Select / box select / add | Left click / left drag / Shift + click |
| Select all of that type on screen | Ctrl + click, or double-click |
| Cycle the selected type | Tab (Shift + Tab goes back) |
| Smart order | Right click: ground = move, enemy = attack, Gold Seam or tree = gather, own site = help build, own hall while carrying = return cargo; a building = set its rally point |
| Queue orders | Hold Shift |
| Unit orders | **M** move, **S** stop, **H** hold, **A** attack-move, **P** patrol |
| Hero | **O** Learn; the ability letters on the bottom row (see Heroes); right-click or Esc cancels a target |
| Items | **Numpad 7 8 / 4 5 / 1 2** use the hero's item slots; right-click a slot to drop or give |
| Worker commands | **B** build, **V** build advanced, **G** gather, **C** return cargo, **R** repair |
| Building commands | the letter on each button (for example **H** Hodman, **U** hall upgrade), **R** rally |
| Back / cancel | **Esc**: leaves targeting or placement, then the build page, then cancels the last item in the queue |
| Next idle worker | **F8** or **`** (the button above the minimap shows how many; Ctrl selects all of them) |
| Select a hero / your hall | **F1–F3** or the hero buttons (top left) / **Backspace** |
| Control groups | Ctrl + 1–0 sets, Shift + 1–0 adds, 1–0 recalls, double-tap centres the camera |
| Camera | Arrow keys, screen edges, middle-drag; mouse wheel zooms |
| Jump to the last alert | **Space** |
| Menu / pause | **F10** |
| Fullscreen / window | **Alt + Enter** or **F11** (the game starts fullscreen and remembers your choice) |

**Tooltips:** rest the mouse on a command button for a moment to see its cost (missing gold or
lumber in red, for example "95 (-35)"), what it does, and what it still needs. Locked buttons are
grey with a lock; buttons you cannot afford yet are hatched, with a coin or log showing what is
short.

## Sound and game feel

- **Heroes:** a ring under every hero shows its level in ten segments (the Brennmark wheel or the
  Tormai gong) and your hero's XP; XP chips fly to the hero after a kill; level-ups light the new
  segment, raise the emblem behind the hero, slam it down with a bell that climbs one step per
  level; a fallen hero's ring breaks up with a low sting; a revive rings in.
- **Abilities:** each cast gives a soft ring at the caster's feet and its own sound; heals show
  green numbers, burning ground flickers with embers, darkness covers the Swallowed Sun, a Fuse
  Mark ticks as a red ring and bursts, the Bronze Window shows a dashed circle; your invisible
  hero is half-transparent.
- **Creeps:** sleeping camps breathe out puffs; bounties pop as coins.
- The Playtest 2 sounds (building, chopping, coins, music) are unchanged.

## Things to try

- Train your free hero early, learn its first ability, and take it with a few soldiers to the
  green camp nearest your base. Watch the XP chips and the level-up.
- Try every ability of one hero: heal, area spells (watch the circle), the ultimate at level 6.
- Creep at night and by day. Wake a sleeping camp, pull a creep far away and watch it walk home.
- Pick up a dropped item, give it to your second hero, drop it, and use a potion with the numpad.
- Buy a potion at the Weighstall, try the Fair Exchange after 3:00.
- Let your hero die, then revive it at the altar, and once at the Coaching Inn.
- Use the Levy Horn (Brennmark) or Sound the Gong (Tormai) when the computer attacks your
  workers.
- Watch the computer: it creeps with its hero, learns, casts, revives and calls its own worker
  defence when you raid its workers.
- Play once as each faction and try both heroes.

## Known issues / not in yet

- **Icons and portraits are placeholders:** buttons show names, portraits and hero buttons show
  initials.
- **Placeholder models:** the Grand Bombard, the Hail-Swifts, the Flail Levy (it looks like a
  Hodman) and some creeps.
- **Items:** no drag and drop yet (right-click a slot instead); the laptop item keys (Alt + 1–6)
  and selling items to a shop are not in the interface yet.
- **The computer** does not shop, use its recall item or expand yet (Playtest 4).
- Inn heroes (hiring at the Coaching Inn) are not in yet.
- Swallowed Sun shortens enemy sight but does not yet block lines of sight through it.
- A few conditional passives of creeps (standing still for armour) are not in yet.
- The white text at the top left (FPS, tick, unit count) is a debug line.

## Questions for you

Short notes are fine.

1. **Heroes:** did levelling feel right (XP from creeps and from the enemy, the level-up)? Was
   the Learn card clear?
2. **Abilities:** were casting and targeting natural (letters, cursor, area circle, cooldown
   sweep, mana)? Which abilities felt good, which weak or unclear?
3. **Creeps:** were the camps fair? Did sleeping at night, the bounty, the drops and creeps
   walking home make sense?
4. **Items and shops:** was the inventory easy (numpad, right-click to drop or give)? Were the
   shops and the Fair Exchange clear?
5. **Revive:** altar or inn: was it clear how and what it costs?
6. **Worker defence:** did the Levy Horn / Sound the Gong help? Were they easy to use?
7. **The computer:** did it creep, cast and revive sensibly? Was it fair at your difficulty?
8. **Juice:** the hero ring, XP chips, level-up, ability looks and sounds: readable and
   satisfying, or too much / too little?
9. **Fullscreen:** did it start fullscreen on your monitor? Did Alt + Enter / F11 work?
10. **Performance:** your FPS (top left), GPU and monitor refresh rate; any hitches in fights with
    many spells?
11. **Classic feel:** what felt most like the classic hero-RTS games, and what least?
12. **Bugs:** anything that crashed, froze or got stuck. Please copy the Godot "Output" panel text
    into your report.

**Still open from Playtest 2** (if you have not answered them): did mining, chopping and building
feel right; can you hear combat, voices and the interface over the music (too loud, too quiet,
about right); how did the faction tracks and the menu theme sound?

## How to report

Send your answers, plus screenshots or a short clip if something looked wrong. Include the commit
you played (`git log -1 --oneline`, or the ZIP's download date).
