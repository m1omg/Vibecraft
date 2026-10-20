# Pending ledger: audio-sfx (SFX and music, branch audio/p0)

All rows dated 2026-10-20, Krea workspace (Individual Basic plan). Caps for this agent: 170 CU SFX + 130 CU music.
Full prompts for every job are in `tools/audio/sfx_jobs.json` and `tools/audio/music_jobs.json` (wrapper + clause, built by
`tools/audio/sfx_prompts.py`). Costs are the preflight quote, cross-checked against `get_balance` where noted.

Balance at start: 1419.61 CU (2026-10-20, before any job of this agent).

| Service | What | Job id | Cost | Result |
|---|---|---|---|---|
| Krea Seed Audio 1.0 | PROBE `hit_metal_l` (O, 4 × 0.5 s) | bfdff9a3-5a6f-4025-bab3-c3ff3052ff9a | 9.26 CU (balance 1419.61 → 1410.35; preflight gives no quote) | OK: 5.07 s output, 3 clean takes (asked for 4), ~1.3 s gaps; kept 3 |
| Krea Seed Audio 1.0 | `hit_metal_h` (O, 4 × 0.6 s) | a11b57c3-ebdc-4afb-b43d-89bfa3b6be31 | 10.00 CU (balance 1410.35 → 1400.35) | OK: 5.46 s output, 3 takes (asked for 4); kept 3. **Pricing: Seed Audio bills per second of output, ≈ 1.83–1.84 CU/s** (9.26 CU for 5.07 s, 10.00 CU for 5.46 s; the old 4.63 CU was a ≈ 2.5 s clip) |
| Krea Seed Audio 1.0 | `sw_slash` (O, 6 × 0.3 s) | cd1d3289-78ce-44ed-936f-9a764d02d060 | 9.82 CU (pair delta 21.07 CU, 1400.35 → 1379.28, split by output length 5.36 s / 6.14 s) | OK: 4 takes (asked for 6), kept 4 |
| Krea Seed Audio 1.0 | `sw_blunt` (O, 6 × 0.35 s) | e24545e2-8a68-4a7f-9c6f-19795fb99236 | 11.26 CU (see the row above) | OK: 4 takes (asked for 6), low noise floor between takes, kept 4 |
| Krea Seed Audio 1.0 | `hit_flesh_l` (O, 4 × 0.4 s) | fe53254d-c99d-46e7-8162-18ab2ca0ead4 | pending | submitted |
| Krea Seed Audio 1.0 | `hit_flesh_h` (O, 4 × 0.5 s) | 6a0b8a42-ce34-4a0d-962a-b3ebdd9ab7dc | pending | submitted |
