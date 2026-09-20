# iPhone Duo materials cleanup and archive record

Date: 2026-09-20

## Resulting authority

`D:\projects\creative_group\iphone-duo` is the single production-code and documentation authority for the Fold Engine, Tokyo V6.28, STORM II integration, and PixelLock image QC.

Local-only assets are separated by purpose:

- `local-archive/source-materials-2026-09-20/` — supplied planning documents and identifiable character references; ignored by Git.
- `artifacts/` — rebuildable screenshots, contact sheets, frame sequences, browser profiles, and QC runs; ignored by Git.
- `deliverables/tokyo/` — the two accepted local Tokyo V6.28 videos; ignored by Git.

## Consolidated material

- The reusable `pixellock-image-pipeline` source, presets, and tests moved to `tools/pixellock/`.
- Tokyo V6.28 source and final runtime plates were merged into the main production line.
- STORM II camera/stage and deterministic motion-reference APIs were preserved on top of V6.28.
- The V5.1 baseline document moved to `docs/archive/production-baseline-v5.1.md` as historical context.
- The Duo Base 3D Viewer proposal was reduced to ordered followups rather than mixed into the current video-production contract.

## Removed as redundant or obsolete

- `D:\projects\creative_group\iphone-duo-original`: clean duplicate checkout at upstream commit `2662ebb`, already an ancestor of the current repository.
- `C:\Users\Admin\Downloads\duo-base-glb-v0.1-prep-kit`: Apple-derived v0.1 preparation workspace. Its exported GLB SHA-256 `226B7D70B59A75D36DA5AA4FB6305EBE8C16B7BDAE8C1B28113111B566A4FFD8` is already retained and deny-listed under `duo-fit-lab/restricted/`; it is not a production input.
- Historical `collab/` goal folders and screenshots: decisions were superseded by current source, `build.json`, the V6.28 manifest, and the release receipt.
- Tokyo V6.16–V6.27 intermediate audits, candidate images, manifests, and one-off capture/review scripts.
- STORM II failed greybox and URL-bootstrap browser profiles, the superseded motion-reference v1 pack, and transient `__pycache__`/runtime folders.

## Preserved boundaries

- The dirty `duo-fit-lab` working tree was not modified.
- Identifiable character references remain internal-only.
- Apple-derived assets remain local-only and outside the MIT license.
- Source integration does not authorize Vercel deployment, platform upload, publication, or monetization.
