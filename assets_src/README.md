# assets_src — paid raw generation outputs (do not delete)

Every file here was bought with Krea or Higgsfield credits. They are the inputs from which the
game-ready files under `assets/` are rebuilt with the tools in `tools/` (see `tools/README.md`).
Each file is listed with its job id, prompt and cost in `docs/asset-ledger.md`.

Layout:
- `characters/<unit_id>/concept.png` — the concept image fed to image-to-3D
- `characters/<unit_id>/model_*.glb` — raw image-to-3D output
- `characters/<unit_id>/rig_<clip>.glb` — Higgsfield 3d_rigging outputs (same mesh, one clip each)
- `characters/<unit_id>/rig_source_facing_pz.glb` — the re-oriented (+Z facing) mesh uploaded for rigging
- `characters/<unit_id>/bakeoff_*.glb` — generator bake-off results (decimated copies)
- `textures/`, `props/` — raw textures and props

Rebuild a unit (example: kingdom_infantry):
```
PY=/opt/bpyenv/v313/bin/python
S=assets_src/characters/kingdom_infantry
$PY tools/merge_anims.py -o /tmp/merged.glb --base $S/rig_walk.glb \
    --clip idle=$S/rig_idle.glb --clip walk=$S/rig_walk.glb \
    --clip attack=$S/rig_attack_sword.glb --clip death=$S/rig_death.glb
$PY tools/process_model.py /tmp/merged.glb -o assets/models/units/kingdom_infantry.glb \
    --target-tris 4500 --height 1.75 --team-mask 300:45:0.3 --name kingdom_infantry
```
Note: the raw rig files contain a stray "Icosphere" helper mesh; strip it before using a rig file as `--base`
(the current `assets/models/units/kingdom_infantry.glb` was built from a stripped copy).
