# iPhone Duo V5.1 — Production Fold Baseline

**Status:** Frozen production baseline  
**Baseline ID:** `v5.1-production-fold`  
**Date:** 2026-09-18

## Purpose

V5.1 is the stable Fold-only production baseline. It promotes the accepted V5.0.x work into a frozen production line for repeatable preview, recording, and export acceptance.

## Locked production behavior

- Two-source architecture only: **Reality + RedBlack**
- One shared panorama coordinate system across both physical screens
- Production reveal: **clean crossfade**
- Fixed right-panel anchor; no dynamic recenter/scale
- Hinge continuity lock
- Final ~1.2° endpoint convergence
- Exact 0° / 180° endpoint snap
- Invalid panorama coordinate guard
- Fold Motion presets:
  - Fast Viral
  - Cinematic
  - Slow Demo
  - Custom manual timing
- Motion Blur:
  - Off
  - Natural
  - Strong
- Master Pair QA at 0° / 45° / 90° / 135° / 180°
- Recording / Editing Mode
- 16:9 / 1:1 / 9:16 safe frames
- 30 / 60 fps deterministic recording clock
- Export Acceptance:
  - automatic capture/export metadata checks
  - manual Motion Blur / Hinge / Open Endpoint / Crop Safety / Compression checks

## Production defaults

- Reveal: Clean Crossfade
- Motion: Fast Viral
- Export frame: 16:9
- Recording clock: 60 fps
- Safe-frame guide: On

## Baseline guards

Normal production URLs cannot activate historical staged reveal or runtime world/stage overrides.

- `?reveal=staged` alone: blocked
- `?dev=1&reveal=staged`: developer-only experiment
- worldMix / stage override debug hooks: blocked unless `?dev=1`
- `?nofx=1`: retained for geometry QA

## Explicitly excluded

The following are not part of V5.1:

- Hero Tower FX
- Bird FX
- displacement experiments
- new reveal art
- independent Tower asset
- third visual source

## Change policy

V5.1 is not the branch for visual experiments.

Any future Tower, Bird, displacement, or transition research must begin on a separate R&D branch. Reintegration into a future production baseline requires separate visual validation and an explicit promotion decision.

## Production acceptance chain

`Master Pair QA → Fold Motion → Recording Mode → Export Acceptance → Production Fold Baseline`

This file defines the handoff boundary for all work after V5.1.
