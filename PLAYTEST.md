# Vibecraft: Playtest 1, "Battlefield Sandbox"

Thanks for playing. This first playtest covers only **controls, movement and combat**. There is no
economy, building or training yet: you get a ready-made army and base, and so does the enemy.
We want to know how commanding an army *feels*. Is it responsive? Is it readable? Does it feel
like the classic hero-RTS games?

## How to run it

1. Get the latest build:
   ```
   git pull
   git checkout claude/clever-heisenberg-i8649y
   ```
2. Install **Godot 4.7.2** (the standard build, not .NET) from godotengine.org.
3. Start Godot, click **Import**, and pick `project.godot` in the repository folder. The first
   import takes a minute or two (models and textures).
4. Press **F5** (or the Play button, top right). The main menu opens.
5. Click **Battlefield Sandbox**. Loading the map takes a few seconds ("Mustering the armies...").

If the game will not start or runs very slowly on an older or integrated GPU, use the
Compatibility renderer:
**Project → Project Settings → Rendering → Renderer → Rendering Method = `gl_compatibility`**,
then press F5 again. From a terminal you can also run
`godot --path . --rendering-method gl_compatibility`.

## The scenario

- **You are Brennmark** (green) in the **south-west** (bottom left) of Wether Downs. You have a
  finished base (Moot Hall, five Crofts, Drill Yard, Oath Hall, Foundry, Collegium) and an army
  standing between your hall and your ramp:
  - 6 Pavisiers (melee)
  - 4 Hookgunners (ranged)
  - 2 Linden Sisters (casters; for now they only use their basic attack)
  - 1 Bombard Wagon (siege, long range)
  - 2 heroes at level 3: the **Wheel Marshal** (melee) and the **Firewright** (ranged)
  - 5 Hodmen (workers). They just idle; the economy comes in Playtest 2.
- **The Tormai** (blue) hold the **north-east** (top right). They have a mirrored base and army
  in two groups:
  - a **guard** at the top of their ramp, which defends their base;
  - a **war-band** waiting in the field on their side of the map. **At 1:30 it marches on your
    hall.** The objective line (top right) counts down, and a warning appears when it sets out.
- **Neutral creeps** sit at three camps: just north of your base below the cliff, south-east of
  your ramp, and in the north-west (top left) of the map. They leave you alone unless you get
  close or attack them. If you hit one, or walk up to one, the whole camp fights back together.
- **Goal:** destroy **every Tormai unit and building**. You lose if you lose everything. After a
  win or a loss, a banner offers **Play again** or **Main Menu**.

## Controls

| Action | Input |
|---|---|
| Select a unit | Left click |
| Box select | Left drag (your units are preferred over your buildings). Heroes come first in the selection, then the units that cost the most food |
| Add / remove from selection | Shift + left click (Shift + drag adds a box) |
| Select all of that type on screen | Ctrl + left click, or double-click |
| Cycle the selected type (the portrait and stats panel) | Tab (Shift + Tab goes back) |
| Select a hero | **F1** (Wheel Marshal), **F2** (Firewright); press twice quickly to centre the camera |
| Select your hall | **Backspace** (centres the camera on it) |
| Control groups | Ctrl + 1–0 sets, Shift + 1–0 adds, 1–0 recalls, double-tap centres the camera |
| Smart order | Right click: ground = move, enemy = attack, own or allied unit = follow |
| Queue orders | Hold Shift while ordering |
| **Attack-move** | **A**, then left click the ground (left click an enemy = attack it) |
| Move | **M**, then left click |
| Stop | **S** |
| Hold position | **H** |
| Patrol | **P**, then left click |
| Cancel targeting | Right click or Esc |
| Command card | The buttons in the bottom right do the same as the keys |
| Pan the camera | Arrow keys, move the mouse to a screen edge, or hold the middle mouse button and drag |
| Zoom | Mouse wheel, or PgUp / PgDn |
| Jump to the last alert | **Space** ("under attack", "the war-band is marching") |
| Minimap | Left click jumps the camera; right click orders the selection there. With an order armed (**A**, **M** or **P**), a left click gives that order at that point (Shift queues it), so A + minimap click sends the army across the map |
| Game menu / pause | **F10** (or the Menu button): Resume, Restart, Quit to Main Menu, Quit to Desktop. Esc also resumes |

A selection holds at most 12 units (genre standard). Use control groups for the whole army.
A group that is close together moves at the pace of its slowest unit, so it arrives together.

## Sound and game feel

**Turn your sound on.** This build has the first real sound effects, voice lines and game-feel
("juice") effects. We want to hear what you think of them.

- **Voice lines:** your units answer when you select them ("What?"), when you order them to move
  ("Yes"), and when you order them to attack ("Attack"). An order is an attack when you use A,
  or right-click an enemy. Only the **Pavisiers, Hookgunners and Hodmen** have voices so far.
  Hookgunners have no attack lines yet, so they say a Yes line instead. The Linden Sisters, the
  Bombard Wagon and the two heroes are silent for now; they answer with a soft click. If you
  click fast, you hear clicks instead of the same line over and over. This is deliberate. On
  the Tormai side, the Yurtwright and Grappler are voiced, but you never command them.
- **Combat sounds:** sword and flail swings, hits that sound different on flesh, mail and wood,
  hookgun shots, javelin throws, Sling-Cart pots and Bombard blasts with their
  impacts, death cries and bodies hitting the ground. Each sound has several takes, and the same
  take never plays twice in a row.
- **Interface sounds:** button clicks, order and selection ticks, and an error sound when an
  order is refused. For example, press A and then click a Gold Seam (it cannot be attacked).
- **Music:** only a short kingdom opening cue at the start of the match. **There is no in-game
  music yet**, so the battle itself has none. At the end of a match the battle sounds fade down
  under the banner.
- **Game feel:** these effects follow the classic games, so they are small and quick at the
  default zoom. Zoom in to see them clearly.
  - **Orders:** a ripple and a pin where you click. Attack-move shows red chevrons. Units nod as
    they take an order.
  - **Selection:** the rings pop in from the corner where you dragged.
  - **Hits:** sparks and splinters, with a short pause on the attacker as a blow lands. The
    health bars show a trailing "damage ghost".
  - **Deaths and missiles:** units fall with a puff of dust, and arrows and javelins stick in
    the ground.
  - **Camera:** a small shake when a Bombard ball or a Sling-Cart pot lands near the centre of
    the screen.
  - **Floating text:** following the classic games, there are no damage numbers over every
    hit. Only critical hits show a number.

## Things to try

- Box-select the army and attack-move (**A** + click) down your ramp. Then try right-clicking
  single enemies to focus them.
- Put the melee units and the ranged units into separate control groups (Ctrl+1, Ctrl+2) and
  fight the war-band with the melee units in front.
- Use **H** (hold) to make a line at the top of your ramp and let the war-band come to you.
- Use **Space** when the war-band warning appears.
- Clear a creep camp with only your two heroes. Then try the camp in the north-west.
- Press **A** and click the minimap near the Tormai base to send an army across the map.
- Siege the Tormai base with the Bombard Wagon behind your army. Watch how their guard reacts.
- Pause with **F10**, then use **Restart**. Play a second game with a different plan.
- Try to lose on purpose (send units in one at a time) and check that the defeat banner appears.

## Known issues / not in yet

- **No economy, construction, training or upgrades** (Playtest 2+). Ordering workers to a Gold
  Seam or a tree does nothing useful yet.
- **Heroes** are level-3 stat blocks: no abilities, items, XP or hero portraits yet. **Heroes
  cannot be revived in this build** (there is no altar yet): a hero that dies stays dead.
- **Unit abilities** are not in (Linden Sisters do not heal, no Pavise, no Shove...). The siege
  splash and minimum range are not in either.
- **No fog of war:** the whole map is visible. The minimap is a placeholder (coloured dots).
- **Placeholder models:** the Bombard Wagon, the Sling-Cart, every creep and the Coaching Inn are
  simple stand-in shapes.
- **Team colour on the Brennmark units is too small.** Their green areas (hat bands, the Wheel
  Marshal's cloak) cover only 1-5 % of most models, so from a distance they can read as
  burgundy. Until the models are repainted, they get a stronger green outline. Tell us if you can
  still mix them up with the blue Tormai.
- **Audio:** **no in-game music yet** (only the 2-second kingdom opening cue), and no ambience.
  Several units are not voiced yet (see "Sound and game feel"), and there are no "annoyed" lines
  for clicking a unit many times. Some sounds borrow another sound for now: the Wheel Marshal's
  axe swing uses the sword swing, and arrows use the javelin impact. Spellcasters' staff swings
  and some impacts (stone, straw) have no sound of their own yet.
- **HUD:** functional stub. The portraits are initials, and there are no tooltips and no idle-worker
  button. The white text at the top left (FPS, tick, unit count) is a debug line for this test.
- **The enemy is a script, not the real AI.** One wave at 1:30, a base guard that defends and
  regroups, and a final push if you have no army left. It does not retreat, focus fire or use
  abilities.
- Creeps do not sleep at night and give no bounty, XP or item drops yet.
- The end of the match is a simple banner. The full victory and defeat sequence comes later.
- A full day/night cycle takes 8 minutes. Night is darker but does not change gameplay yet.

## Questions for you

Please answer what you can. Short notes are fine.

1. **Selection:** did every click, box, double-click, Ctrl-click and control group do what you
   expected? Note any moment when it did not.
2. **Orders:** do A-click, S, H, P and M feel natural? Did right-click always do the right thing
   (move, attack, follow)?
3. **Camera:** is the pan speed right (edge, arrows, middle-drag)? Is the zoom range right? Did
   edge pan ever trigger by accident?
4. **Combat readability:** in a big fight, could you tell who was hitting whom and who was
   winning? Were the hits, deaths and projectiles satisfying, or flat?
5. **Movement:** did units get stuck, clump badly, take odd paths (around buildings, on the
   ramps), or block each other?
6. **The war-band:** did you notice the warning? Did Space take you to it? Was 1:30 enough time
   to get ready?
7. **Difficulty:** did you win? How long did it take, and how many units did you lose? Too easy,
   too hard?
8. **Units:** which unit felt too weak or too strong? Did the heroes feel like heroes?
9. **Visuals:** can you read units and buildings at the default zoom? Are the team colours clear?
   Is anything ugly or confusing?
10. **Sound and feel:** did the voice lines, hits and shots make commanding the army feel
    better? Was any sound annoying, too loud, too quiet or repeated too often? Did any effect
    (ripples, sparks, the shake, the hit pause) feel wrong, too big or too small?
11. **Performance:** what FPS did you see (top-left), and were there any hitches? Tell us your GPU
    and monitor refresh rate. Does it feel equally smooth at 60 / 144 / 240 Hz?
12. **Classic feel:** what felt most like the classic hero-RTS games? What felt least like them?
13. **Bugs:** anything that crashed, froze, errored or got stuck. Please copy the Godot "Output"
    panel text into your report.

## How to report

Send your answers, plus screenshots or a short clip if something looked wrong, to the project
channel. Include the commit you played (`git log -1 --oneline`).
