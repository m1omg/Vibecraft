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
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman ready (ready_01; voice N2lVS1w4EtoT3dr4eOWO; 46 chars) | d6370497-b848-4e5a-a331-4d2a6e91c154 | 3.41 CU | ready_01: ok 3.27s atempo 1.073 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman yes (yes_01, yes_02, yes_03; voice N2lVS1w4EtoT3dr4eOWO; 63 chars) | b168f192-e1ea-41bc-bdf8-6b2944db9788 | 4.67 CU | yes_01: ok 1.17s; yes_02: ok 1.388s atempo 1.08; yes_03: ok 1.376s atempo 1.095 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: hodman attack (attack_01, attack_02; voice N2lVS1w4EtoT3dr4eOWO; 55 chars) | 0331ca24-9cc0-49bf-97e0-cae7bbb518e0 | 4.07 CU | attack_01: ok 1.44s; attack_02: ok 1.46s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright ready (ready_01; voice pqHfZKP75CvOlQylNhV4; 49 chars) | 1e67798d-77b7-42d5-bfb6-65b0cd369094 | 3.63 CU | ready_01: ok 3.25s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright what (what_01, what_02, what_03; voice pqHfZKP75CvOlQylNhV4; 66 chars) | f4c8da98-261d-4b63-9e7d-415421fe35a6 | 4.89 CU | what_01: ok 1.08s; what_02: ok 1.06s; what_03: ok 1.27s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright yes (yes_01, yes_02, yes_03; voice pqHfZKP75CvOlQylNhV4; 55 chars) | ad890167-5fa9-4bb5-9894-939146e0b62c | 4.07 CU | yes_01: ok 0.74s; yes_02: ok 1.15s; yes_03: ok 0.86s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: yurtwright attack (attack_01, attack_02; voice pqHfZKP75CvOlQylNhV4; 58 chars) | 6a490962-db4f-4f15-b7d9-598ef845a1ca | 4.30 CU | attack_01: ok 1.42s; attack_02: REJECTED 2.003s atempo 1.15 |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier ready (ready_01; voice TX3LPaxmHKxFdv7VOQHJ; 50 chars) | 74175336-c9ca-483b-9f22-7cde578e9b79 | 3.70 CU | ready_01: ok 2.72s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier what (what_01, what_02, what_04; voice TX3LPaxmHKxFdv7VOQHJ; 65 chars) | 102d1a07-d580-41f8-816c-f32b6bd96fbd | 4.81 CU | what_01: ok 0.75s; what_02: ok 1.17s; what_04: ok 0.86s |
| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | tier a: pavisier yes (yes_01, yes_02, yes_04; voice TX3LPaxmHKxFdv7VOQHJ; 69 chars) | a479d3ac-7474-4b0c-81c7-fd9e3b90de9f | 5.11 CU | yes_01: ok 1.389s atempo 1.095; yes_02: ok 1.15s; yes_04: ok 0.72s |
