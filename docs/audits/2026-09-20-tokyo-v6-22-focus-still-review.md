---
title: Tokyo v6.22 focus-only still candidates and repaired tower plates
status: still-candidate / pending-user-selection
updated: 2026-09-20
scope: Static candidates only; no video or frame sequence
---

## Result and superseded direction

Seven actual 1920×1080 device stills, a source-plate before/after sheet and focused
evidence are in `artifacts/v6.22-tokyo-focus-still-review/`. No MP4, 348-frame
sequence, audio, birds, title treatment or final-video-ready status was produced.

The user rejected v6.21 colour reveal and TIME/TOKYO alternatives. Its uncommitted
source candidates, scripts, manifest, audit and four working-source snapshots
were moved to the ignored output's `rejected-v621/source/`; its old rendered
evidence remains in the original artifacts directory. These are recoverable
rejected evidence, not source delivery. The four tracked files were restored to
`b9365e4` before v6.22 implementation. No committed baseline file was deleted.

## One stable inner world, physical-panel focus only

The v6.22 inner branch never mixes photographic A into B. It samples the same
RedBlack world at every angle, so there is no colour front, wipe, panel-specific
world assignment or second tower identity. Runtime explicitly reports
`revealMode: none/focus-only`, `innerABMix: false`, `spatialFront: null`.

Only fragments belonging to the physical moving left inner panel receive
defocus. The whole panel uses one angle-derived radius:

`radius = 18 * sin(foldAngle)^2` source texture texels; 180° is exactly zero.

After the inner panel faces the viewer this decreases naturally as it flattens:
110° → 15.8944 texels; 150° → 4.5; 180° → 0. A mip-prefiltered disk sampling kernel
avoids repeated sharp ghost copies. There is no Gaussian mask travelling across
the panorama. The fixed right panel's radius is always 0. No contrast/darkening,
camera motion, device blur, shell/hinge change or UV change accompanies focus.
Legacy motion blur remains off. The cover remains A-only and retains the existing
physical-cover exit treatment, complete before 57.6°; it never samples B.

### Measured actual-frame focus

Laplacian variance uses identical registered city regions in each actual PNG.
Pixel bounds are `[left,top,right,bottom]` at 1920×1080: left
`[790,520,925,865]`; right `[1340,520,1420,865]`. Right excludes the Open flashlight
circle. The initial right ROI inadvertently included that circle's left arc;
that rejected measurement is preserved in `qc-before-excluding-shortcut-arc.json`.

| Physical angle | Moving-left variance | Fixed-right variance |
| --- | ---: | ---: |
| 110° | 1.4892 | 58.18995 |
| 150° | 2.6632 | 58.18995 |
| 180° | 54.5778 | 58.18793 |

Left sharpness strictly increases. Right spread is 0.00349%, within the declared
1% tolerance. This measures the affected static states, not temporal video
quality. `focus-transition-proof.png` and `focus-roi-closeups.png` show the actual
renders. The tower ROI `[1120,160,1360,830]` contains 0 bright neutral A-tower
residual pixels at 90°, 110° and 150°. The detector requires all channels >100
and max/min <1.25, excluding red sky and warm city lamps. The renderer's B-only
branch is the primary identity invariant; the pixel count checks the prior
visible white-tower symptom.

## Repaired source-aligned tower plates

The v6.20 repaired, mutually exclusive tower/city matte is the basis. The two
approved source-photo obstructions are upper `[1968,735,2016,805]` and lower
`[1968,905,2028,1040]`. These large black regions existed in the photograph too;
changing city ownership alone could not repair both Closed and Open.

Large dark components in those approved regions are replaced by unscaled clean
truss pixels from the same photo, with local donor offsets -140y and -360y.
The operation affects 4,942 source pixels and uses a one-pixel footprint margin.
It neither resizes/warps the whole image nor shifts the tower. Platform window
rails, outer silhouette and fine structural dark lines remain. A further 1,447
lower-support pixels previously classified as city/windows are reassigned to
tower. Tower/city overlap and tower/window overlap are both 0.

The repaired source yields three separate 2670×1878 RGBA plates sharing one
alpha: natural warm white, near-black with dark-copper edges, and warm gold.
Closed is filled from the natural plate over the direct v6.19 photographic A,
with only bounded city crispness and bottom-shadow refinement. It does not use
v6.20's dark/cold cover grade. Open weak and strong windows share exactly the same
unlit tower. Gold is a separate tower-light layer, never building-window light.

| Source ROI | Closed mean before → after | Closed largest dark component | Gold largest dark component |
| --- | --- | --- | --- |
| Upper obstruction | 96.61 → 130.34 | 496 → 9 px | 519 → 26 px |
| Lower central obstruction | 66.45 → 116.72 | 3290 → 92 px | 3638 → 99 px |

Dark-component threshold is luminance <45/255. Residual small dark structures are
intentional truss/window lines, not erased by a glow. Source and actual-render
close-ups permit visual inspection of the repair instead of relying on averages.

The unlit body averages RGB `[8.70,4.59,3.53]`; the dark-copper edge averages
`[33.32,9.30,5.43]`. Only 8.86% of tower support receives the edge grade. It stays
strictly inside alpha, with 0 outside-alpha outline pixels and no halo. Windows
retain the 22% weak-emission state and monotonically stronger state; violations
are 0. The repaired gold plate keeps photographic truss detail and does not
reintroduce the large central black blocks.

## UI and frozen device

Closed has no overlays. Open keeps only Wi-Fi and right-side flashlight/camera
shortcuts. Clock, date, TOKYO/other title and home indicator are all off; the
corresponding chrome-texture alpha regions contain 0 pixels. There is no new font
or copied film template. The fixed camera remains at 100 units, with the existing
matching FOV, pan and zoom. Device/model, hinge, authored UV, shell patch authority,
physical folding direction and top-cap positions remain unchanged.

## Verification and rerun

Console/runtime errors: 0. Nineteen frozen source assets, prior videos, model and
shell patch authority retain their hashes. Both old query profiles v6.19 and
v6.20 were compared with exact `b9365e4` source loaded through transient CDP
interception in the same browser at frames 12/91/347: every maximum pixel delta
is 0. No UI unit tests, E2E suite, GitHub Actions, deployment or publication ran.

Evidence records Chrome 152.0.7977.75, device pixel ratio 2, 2880×1800 render
canvas and ANGLE/NVIDIA RTX 3070/D3D11. Output crops are 1920×1080. Byte equality
is demonstrated only for the same-browser old-profile checks, not promised
across renderer environments.

To reproduce:

1. Run `scripts/build_tokyo_v622_focus_assets.py` in the existing Python environment.
2. Serve the repository at local port 8771 and open an isolated named browser
   session at `?cap=1&tokyo=v622&nofx=1&motion=tokyo-demo`.
3. Pass that session's `agent-browser get cdp-url` to
   `scripts/capture_tokyo_v622_focus_stills.py`.
4. Close only that task-owned browser session and local server.

User visual acceptance remains pending for Closed natural tower retouch,
left-panel optical softness at 110°/150°, unlit dark-copper readability and the
final gold structure. This is a static candidate, not an approved video master.
