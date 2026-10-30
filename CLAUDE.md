# Vibecraft

A Godot 4.7.2 3D hero RTS that plays as close to the classic 2002 hero-RTS as legally possible, with 100 % original names, art,
audio and text.

**Start with `HANDOVER.md`** (repo root). It covers the project state, the user's working style, budgets and rules, and next steps.

The essentials:

- Dev branch `claude/clever-heisenberg-i8649y`: commit and push there. No PR unless asked.
- Before every commit, all tests must pass:
  `godot --headless --path . --import`, then `godot --headless --path . -s tests/run_tests.gd`.
- Before every commit, `python3 tools/ip/check_banned_terms.py` must find no banned terms.
- Gameplay runs only in the fixed 30 Hz tick. Visuals and audio use real delta and never change the sim. Nothing may depend on the
  display refresh rate.
- Log every paid generation job in `docs/asset-ledger.md`. Check the bans and prices there first.
- At each milestone, verify the build yourself, then ask the user to play-test it with simple steps (a ZIP link, then F5 in
  Godot). Otherwise keep messages to the user minimal.
