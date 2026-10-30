# Vibecraft: Playtest 2, "Base building"

Thanks for playing. This playtest is about **building a base**: mining gold, cutting lumber,
raising buildings, training units, food and upkeep, research and the tier-2 hall upgrade, and the
new command card and HUD. You play a **skirmish against a computer opponent** that builds its own
base and comes for you. We want to know whether running an economy *feels* like the classic
hero-RTS games, and whether the interface makes it easy.

The Playtest 1 "Battlefield Sandbox" is still in the menu if you want to compare.

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
- **Neutral creeps** sit at camps around the map. They leave you alone unless you get close.
- **Goal:** destroy **every enemy building**. You lose when you have no buildings left (units do
  not count). If you lose your last hall, you have **120 s** to finish a new one (a countdown
  appears at the top right), or all your buildings are revealed to the enemy.
- The **Normal** computer usually attacks around 7–9 minutes. **Easy** waits until at least 10
  minutes with a bigger army. **Hard** builds a little faster and attacks sooner.

## Economy and building in short

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
- **Heroes:** your first hero (from the Oath Hall or the Naming Stones) is **free**. More hero
  slots come with the tier-2 hall. Heroes have no abilities yet (Playtest 3).
- **Research and tier 2:** research buttons sit on the building that researches them. The hall's
  upgrade (**U**: Walled Burg / Banner Shell) needs an Oath Hall / Naming Stones, takes about two
  minutes and unlocks the advanced buildings and units. Nothing else trains at the hall while it
  upgrades.

## Controls

| Action | Input |
|---|---|
| Select / box select / add | Left click / left drag / Shift + click |
| Select all of that type on screen | Ctrl + click, or double-click |
| Cycle the selected type | Tab (Shift + Tab goes back) |
| Smart order | Right click: ground = move, enemy = attack, Gold Seam or tree = gather, own site = help build, own hall while carrying = return cargo; a building = set its rally point |
| Queue orders | Hold Shift |
| Unit orders | **M** move, **S** stop, **H** hold, **A** attack-move, **P** patrol |
| Worker commands | **B** build, **V** build advanced, **G** gather, **C** return cargo, **R** repair |
| Building commands | the letter on each button (for example **H** Hodman, **U** hall upgrade), **R** rally |
| Back / cancel | **Esc**: leaves targeting or placement, then the build page, then cancels the last item in the queue |
| Next idle worker | **F8** or **`** (the button above the minimap shows how many; Ctrl selects all of them) |
| Select a hero / your hall | **F1–F3** / **Backspace** |
| Control groups | Ctrl + 1–0 sets, Shift + 1–0 adds, 1–0 recalls, double-tap centres the camera |
| Camera | Arrow keys, screen edges, middle-drag; mouse wheel zooms |
| Jump to the last alert | **Space** |
| Menu / pause | **F10** |

**Tooltips:** rest the mouse on a command button for a moment to see its cost (missing gold or
lumber in red, for example "95 (-35)"), what it does, and what it still needs. Locked buttons are
grey with a lock; buttons you cannot afford yet are hatched, with a coin or log showing what is
short.

## Sound and game feel

- **New sounds:** builders' hammers (Brennmark) and mallets (Tormai) on every stroke, axe chops,
  trees falling, coins and logs arriving at the hall, the stamp when a site starts, a chime when a
  building finishes, a bigger one for the hall upgrade, buildings caving in, and a soft chime when
  research finishes. Units you train say their Ready line as they come out.
- **Music is in now:** the menu theme, then your faction's tracks during the match (with pauses
  of silence between them), and a closing piece after the end banner.
- **The sound mix changed:** music, combat, world and interface sounds now each have their own
  volume level (combat on top, music underneath). See question 9.
- **Game feel:** dust and corner puffs when a site starts, sawdust and splinters on each stroke,
  a warm flash, rings and rising sparks when a building finishes, "+7"-style food numbers over
  new supply buildings, dust and smoke when a building falls. The resource numbers roll instead
  of jumping, a refused order shakes the button and the counter that is short, and the shortfall
  ("-35") drops out under the counter.

## Things to try

- Get five workers on gold and the rest on lumber as fast as you can. Use **F8** to find idle
  workers.
- Build a supply building, a barracks (Drill Yard / Grapple Yard) and your hero's building in
  the first minute. Try placing a building on a blocked spot, then where you cannot afford it.
- Put two or three Hodmen on one Brennmark site and compare the build time.
- Queue five units with **Shift**, cancel one from the middle of the queue, and set a rally point
  on your Gold Seam for new workers.
- Push past 50 food and watch the upkeep warning and the gold per trip drop.
- Upgrade your hall to tier 2 and build an advanced building.
- Defend against the computer's attack, then destroy its base. Try **Easy** first, then
  **Normal**, and **Hard** if you like.
- Play once as the Tormai.

## Known issues / not in yet

- **Heroes have no abilities, items or levels yet**, and dead heroes cannot be revived
  (Playtest 3). Unit abilities (Levy Horn, Sound the Gong, the Pavise, Shove...) are not on the
  card yet.
- **The shops** (Curio Cabinet, Tea Tent) can be built but sell nothing yet.
- **The computer** follows a fixed build order and attacks in one push. It does not creep,
  expand, use abilities or retreat cleverly yet (Playtest 4). It banks a lot of lumber.
- **Icons are placeholders:** buttons show names and portraits show initials until the icon art
  exists.
- **Fog ghosts:** if an enemy building you saw is destroyed while you cannot see it, its ghost
  disappears at once instead of staying until you look again.
- **Placeholder models** remain for the creeps and the Coaching Inn.
- The white text at the top left (FPS, tick, unit count) is a debug line.

## Questions for you

Short notes are fine.

1. **Economy:** did mining and chopping feel right (speed, trips, five on gold)? Did workers ever
   stand idle, get stuck or walk oddly around the hall, the seam or the trees?
2. **Building:** was placing buildings easy? Was the sketch ghost and the green / red grid clear?
   Did anything block a spot when it should not have (or the other way round)?
3. **Command card:** were the build pages, letters and Esc behaviour natural? Was anything where
   you did not expect it?
4. **Training and the queue:** was it clear what was training, how long it would take and how to
   cancel? Did rally points work?
5. **Food and upkeep:** did you understand when and why training waited, and what upkeep costs
   you?
6. **Tooltips and warnings:** were the tooltips, the red error line, the shaking counter and the
   shortfall number helpful or noisy?
7. **The computer:** did it build sensibly? When did it attack, and was it fair at the difficulty
   you chose? Did the end banner appear when someone lost every building?
8. **Juice:** did the hammers, chops, coins, completion chimes and dust make the base feel alive?
   Was any of it too loud, too frequent or too small?
9. **Mix and music:** with the new volume levels, can you hear the combat, the voices and the
   interface clearly over the music? Is the music too loud, too quiet or about right? How did the
   faction tracks and the menu theme sound?
10. **Performance:** your FPS (top left), GPU and monitor refresh rate. Any hitches, especially in
    big fights or when many workers are busy?
11. **Classic feel:** what felt most like the classic hero-RTS games, and what least?
12. **Bugs:** anything that crashed, froze or got stuck. Please copy the Godot "Output" panel text
    into your report.

## How to report

Send your answers, plus screenshots or a short clip if something looked wrong. Include the commit
you played (`git log -1 --oneline`, or the ZIP's download date).
