# Followups

Items are ordered by dependency. A later item should not start before the earlier gate it depends on has passed.

## STORM II character and motion

- [ ] Recover `AKF-TURN-001` in a dedicated one-image edit session: Elon only, slow shoulder-led turn, head lag, forearm drawn toward the sternum, no phone, no collage, one repair maximum.
- [ ] Recover `AKF-REVEAL-001` in a separate one-image edit session: the accepted four people, Elon as the foreground anchor, three distinct delayed inward reactions, no equal-weight lineup, no split scene, one repair maximum.
- [ ] Review the resulting six-state contact sheet: Closed → Turn → Opening → Formation → Reveal → Freeze. Do not create character motion video until all six states pass.
- [ ] Define the independent post-open `AKF-PULSE-001` from a dedicated dance reference. The supplied 15-second reference only authorizes the Closed-to-Open reveal and must not be misused as the later group pulse.
- [ ] Produce a free-or-credit character-only motion demo after screenshot approval. Keep the device out of the generation prompt and composite the approved character result with the deterministic Fold Engine plates afterward.
- [ ] Before any public or monetized real-person output, clear provenance, likeness/publication rights, non-endorsement, disclosure, territory, monetization, and legal review.

## Video production workflow

- [ ] Make screenshot/state-pack approval mandatory for every future video: freeze the state manifest, review contact sheets, allow at most one targeted repair per failed state, then render deterministic frames and encode video.
- [ ] Add a reusable compositor that combines character motion with Fold Engine device plates while preserving hinge, panel, Screen UV, camera, timing, and occlusion authority.
- [ ] Keep both target platforms horizontal. Derive Xiaohongshu 4K60 and X 1080p40 from one approved horizontal master; do not redesign a vertical cut by default.

## General 3D Viewer and duo_base

- [ ] Phase 0: decide the provenance and redistribution rules for the default demonstration model. A “demo only” label does not replace copyright or commercial permission.
- [ ] Phase 1: define a `DeviceProfile` contract for root, moving panel, inner and outer screens, hinge axis and point, and open/closed angles; add GLB/glTF import first, then consider USD-family formats.
- [ ] Phase 2: continue `duo-fit-lab` geometry calibration and semantic-node work until the independent `Duo_Base_v0.2` is an acceptable self-owned default. Do not reuse the restricted Apple-derived v0.1 GLB or Prep Kit outputs.
- [ ] Phase 3: share App-preview and content-timeline state between the Viewer and this video-production repository.
- [ ] Phase 4+: add hardware adapters, case/accessory anchors, higher-quality materials, crease/reflection work, recording, multi-device views, and display-wall features only after the earlier phases are stable.

## Maintenance

- [ ] Remove the now-dead historical `TOKYO_619` through `TOKYO_627` implementation branches after confirming that no debugging workflow still calls their private frame helpers. Saved historical query URLs already resolve to V6.28, and their heavy assets and scripts are gone.
- [ ] If PixelLock is reused, run it from `tools/pixellock/` and store each run under ignored `artifacts/`; do not restore the former standalone `pixellock-image-pipeline` directory.
