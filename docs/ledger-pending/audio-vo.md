# Pending ledger: audio-vo (unit and hero voices, advisors; branch audio/p0)

All rows dated 2026-10-20, Krea workspace (Individual Basic plan), service `elevenlabs/tts` with `model_id: eleven_v4`.
Hard cap for this agent: **300 CU**. Pricing measured with free preflights on 2026-10-20: **exactly 2/27 CU (0.0741) per
prompt character**, newlines, spaces and bracket tags included, no per-job base fee (20 chars = 1.4815 CU, 30 = 2.2222, 59 = 4.3704).
The Krea balance is shared with the audio-sfx agent, so costs below are the exact per-character quote of each prompt; the balance
deltas are cross-checks only. Full prompts for every job: `tools/prompts/vo/vo_jobs.json`. Scripts: `docs/design/voice-lines.md`.

Balance at start: 1419.61 CU (2026-10-20, before any job of this agent).

| Service | What | Job id | Cost | Result |
|---|---|---|---|---|
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier probe: hodman what (what_01, what_02, what_03, what_04; voice N2lVS1w4EtoT3dr4eOWO; 121 chars); PROBE: separators [long pause] / [pause] / blank line; 121 chars | 10192392-602c-4eb3-817d-d2a712c8db67 | 8.96 CU | split 4/4 correct (ASR-checked); what_01 1.39 s, what_03 1.38 s, what_04 1.11 s shipped; what_02 "Thirty years. One Agnes." 2.4 s REJECTED (over 1.4 s at atempo 1.15) |
