# Music style tests (composed, rendered with tools/music)

The 40-second style tests that fixed the band sound per faction before the real pieces were written. Sources:
`tools/music/pieces/style_kingdom.py` and `style_clans.py`; rebuild with
`python3 tools/music/render.py tools/music/pieces/<name>.py` (byte-identical, see `tools/music/test_determinism.sh`).
Each has its Ogg Vorbis master (-16 LUFS, <= -1 dBTP), the spectrogram and the piano roll (with the K-weighted
loudness lane). Measurements are in `tools/music/README.md` ("Style tests"). Not game assets: docs/ is ignored by Godot.
