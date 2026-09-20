---
title: Tokyo v6.20 dormant cover and sequential lighting review
status: ready-for-user-review
updated: 2026-09-20
scope: iphone-duo Tokyo v6.20 screen art and lighting only
---

Verdict: ready for user visual review. The silent cut is encoded from 348 numbered
PNG frames. No device, hinge, UV, material, fixed-camera, or top-cap change was made.

## Result and visible intent

Video: `artifacts/v6.20-tokyo-silent-demo/iphone-duo-tokyo-v6.20-silent-review.mp4`.

Closed is now a clean graphite blue-grey photographic cover: no date, clock,
Wi-Fi, shortcuts or home indicator. The physical front camera remains. Source
window emission is suppressed, the tower reads through ambient steel luminance,
and lower-quarter shadows retain facade detail. It is a dormant scene rather
than a miniature lock-screen layout.

Open retains date, clock, Wi-Fi and the right-side utility controls. The clock is
15% smaller than v6.19 and shifts from texture x=.50 to .46 and upward by .02 of
the texture height. The date is smaller in the same grouping. The home indicator
is removed. The UI remains invisible during the fold and fades in over frames
138–143, after the display is fully flat.

## Matte repair before illumination

The old city/tower support overlapped at 69,339 pixels. The new masks assign each
tower pixel exclusively to the tower, leaving zero overlap. Source-aligned,
opaque observation-deck shapes restore 10,177 missing support pixels that
previously let city black or red sky enter the platform surface. Structural dark
caps, windows and steel remain as luminance detail, rather than becoming matte
holes. The repair does not use glow and does not move the tower or skyline.

`tower-cleanup-before-after.png` reads left to right: v6.19 lit tower, old tower
matte, repaired tower matte, new dormant tower, new lit tower. Full-size
`tower-matte.png`, `city-exclusive-matte.png`, `window-matte.png`, and
`tower-matte-repair.png` permit inspection independently of the final lighting.
These masks are authored compositing support, not an independently segmented
ground-truth claim.

## One lighting climax

| Frames | Time | State |
| --- | --- | --- |
| 0–137 | 0–2.283 s | Closed and unfolding; building and tower light drivers are zero. Global inner-only reveal still travels right to left. |
| 138–147 | 2.300–2.450 s | Open dark hold; UI fades in, scene lamps remain off. |
| 147–180 | 2.450–3.000 s | Building windows wake in four far-to-near depth bands, each with three fixed sparse cohorts. Each window turns on once and stays on. |
| 180–185 | 3.000–3.083 s | Buildings-on pause; tower still dormant. |
| 185–211 | 3.083–3.517 s | Tower lighting rises from the base to the tip; the tip locks last. |
| 211–347 | 3.517–5.783 s | Stable hero hold. No second pulse, breathing climax, camera or geometry movement. |

The shared boundary frame is the exact start/end value of the corresponding
continuous ramp. The first non-zero window driver is frame 148 and the first
non-zero tower driver is 186. The old 3.183-second pulse and window breathing are
both disabled in v6.20. No audio, birds, copy, impact frame, halo or blur is added.
Window activation ranks extend from the nearest window into transparent texels,
so texture filtering cannot make a near window's edge light ahead of its batch.

## Measured evidence

- H.264, 1920×1080, yuv420p, CFR 60, 348 source PNGs and 348 decoded video frames,
  5.800 seconds, no audio. No FPS resampling occurs during encoding.
- Unfolding has zero adjacent duplicate source or decoded frames. Visible
  10–90% travel remains 0.90 seconds; maximum single-frame travel 3.114%;
  projection overshoot 1.038%; angle overshoot zero; Open completes at frame 138.
- Cover-to-inner tower registration remains `(2,0)` px with correlation 0.978 in
  the fixed A/A tower ROI. No camera or geometry adjustment was needed.
- Pixel differences are zero across the dark hold (143 vs 147), lighting pause
  (180 vs 185) and stable hero (211 vs 347). Both light drivers are monotonic;
  all earlier frames have zero light activation and the legacy pulse stays zero.
- Console/runtime errors are zero. Renderer: Chrome 153, RTX 3070, 2× capture,
  anisotropy 16. Motion blur and screen blur/darken remain disabled.
- Ten frozen inputs, including v6.16/v6.18/v6.19 candidate files, the local model
  and shell patch authority, retain their recorded hashes. Previous v6.18 and
  v6.19 MP4 hashes match their manifests.
- The v6.19 query was re-rendered at frames 12, 91, 138, 191 and 347; each is
  pixel-identical to its prior numbered frame. New behavior is v6.20-only.

JavaScript/Python syntax and focused diff checks pass. No GitHub Actions,
deployment, UI unit tests or E2E suite was used. User visual acceptance remains
pending.

## Evidence and reproduction

The output directory includes `actual-video-contact-sheet.png`,
`contact-sheet.png`, `light-state-sheet.png`, `closed-ui-closeup.png`,
`open-ui-closeup.png`, `open-bottom-no-indicator.png`, `shell-contact-sheet.png`,
the tower mattes, `world-lighting-overview.png`, `runtime-state.json`,
`frame-ledger.json`, `console-errors.json`, `renderer-info.json`, `ffprobe.json`,
`qc-summary.json`, `encoded-motion-qc.json`, `frozen-input-hashes.json` and
`v619-regression.json`.

Run the v6.20 builder, capture, review and encode scripts. Capture defaults to a
task-owned HTTP server on 8770 and Chrome CDP on 9230:

`?cap=1&tokyo=v620&nofx=1&motion=tokyo-demo&timeline=tokyo&format=16x9&closedUi=0&openUi=1`

The first candidate, which retained some cool photographic window emission, is
preserved in `artifacts/v6.20-rejected-cold-window-leaks`. All accepted older
assets and outputs remain untouched. A second candidate is retained in
`artifacts/v6.20-rejected-window-rank-edges` before the rank-filtering correction.
The Wikipedia source assertion is unchanged;
this work adds no publication or rights claim.

## User visual validation Todo

- Judge the dormant cover's photographic appeal and shadow depth.
- Confirm the smaller upper-left Open clock/date and absence of home indicators.
- Inspect the restored tower platforms while dark and while lit.
- Watch the windows establish depth, then the single base-to-tip tower climax.

No local implementation blocker remains.
