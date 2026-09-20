---
title: Tokyo v6.18 feedback repair and silent review
status: ready-for-user-review
updated: 2026-09-20
scope: iphone-duo Tokyo preview and Fold Engine screen composition
---

Verdict: ready for user visual review. The MP4 is a captureStream review preview,
not a numbered-frame master. Publication and production activation remain outside
this work.

## Result

- Video: `artifacts/v6.18-tokyo-silent-demo/iphone-duo-tokyo-v6.18-silent-review-demo.mp4`
- Authored keyframes: `artifacts/v6.18-tokyo-silent-demo/contact-sheet.png`
- Actual encoded-video frames: `artifacts/v6.18-tokyo-silent-demo/video-contact-sheet.png`
- A/B grading overview: `artifacts/v6.18-tokyo-silent-demo/world-pair-overview.png`
- Closed/open 3D shell: `artifacts/v6.18-tokyo-silent-demo/shell-contact-sheet.png`
- Run manifest: `media/tokyo/v6.18-silent-demo-manifest.json`

## Feedback coverage

| Feedback | Status | Change and evidence |
| --- | --- | --- |
| Slow crawl and long settle tail | covered | 1.10 s closed hold, 1.15 s smooth unfold, fully open at 2.25 s, then an explicit 3.55 s hold. Zero overshoot. Frames 135 and 191 have identical safe-frame pixels (max channel delta 0), so the future 3.18 s pulse slot does not overlap motion. The pulse remains disabled. |
| Red leakage on closed cover | covered | The outer material samples A only. Red exists exclusively on the inner display and advances from the hinge across the fixed/right panel, then the moving/left panel. Frames 0 and 74 have no red or inner chrome. |
| Two towers during turnover | covered | The moving cover is swallowed between 18 and 57.6 degrees, before it crosses 90 degrees. It cannot display the B tower. The fixed inner tower remains the visual anchor; the actual-video sheet shows no parallel bright towers. |
| Red, black, yellow not separated | covered | A packed, source-derived city/tower mask makes sky, city and tower independently blendable. Red completes first, city darkens next, and the existing warm-white tower turns yellow last. Frames 105 and 121 demonstrate intermediate separation. |
| UI leakage and hinge compression | covered | Chrome is a separate texture sampled in physical screen UV, never mixed with A/B. Clock and date are wholly on the fixed right panel and appear at 97–100% opening. Wi-Fi and utility controls share that gate. Date is Fri Oct 23. |
| A too blue/orange | covered | New `reality-v6.18-natural.png` retains original luminance and geometry, reduces chroma to 28%, and uses the source tower mask for natural warm-white light. No image generator, crop, warp, or device pixels are involved. Both v6.16 masters remain unchanged. |
| Folded screen blur | covered | The existing shader's 72-pixel fold blur and fold darken are disabled in the v6.18 lane; external motion blur is also off. GPU anisotropy is already 16. No claim is made that anisotropy was the old cause. |
| Close/open/3D, top caps and lower key | covered | One unchanged Fold Engine model drives all states. Both top-cap meshes have identical min/max Y bounds. Lower-right-key source geometry is unchanged from the reviewed flush v6.15.1 model. Desktop and oblique shell evidence is retained. Final aesthetic judgment remains with the user. |

## Mechanical evidence

H.264, 1920×1080, yuv420p, CFR 60 fps, 348 frames, 5.800 seconds,
limited-range BT.709, one video stream and no audio stream. Browser console/runtime
errors: zero. Runtime frame range: `0..347`; capture clock check passes.

The final video and independently sampled authored frames are both inspected.
Their exact intermediate frame numbers are not promised to align: captureStream
can duplicate/drop/offset browser frames, which is why this remains a preview.
No music, sound effects, birds, impact frames, pulse, extra title, or additive tower
highlight is present.

`renderer-info.json` records Chrome 153 / NVIDIA RTX 3070 / anisotropy 16 and
live device-control bounds. `keyframe-states.json`, `runtime-state.json`,
`console-errors.json`, `ffprobe.json`, and `qc-summary.json` retain the narrow
evidence. JavaScript syntax and `git diff --check` pass. GitHub Actions, UI unit
tests and E2E suites were not used.

## Local reproduction

Serve the repository on port 8766 and use a task-owned Chrome CDP session on
9222. Open:

`http://127.0.0.1:8766/?cap=1&tokyo=v618&nofx=1&motion=tokyo-demo&timeline=tokyo&format=16x9&closedUi=0&openUi=1`

Run `scripts/build_tokyo_v618_layers.py`, then
`scripts/capture_tokyo_v618_demo.py`. Capture refuses to overwrite an existing
WebM; pass a fresh output directory for a new run. Its `--evidence-only` option
resamples the authored keyframes without replacing the source recording.
Encode with `scripts/make_tokyo_v618_silent_demo.py` (WebM, safe-rect JSON, output
MP4), then run `scripts/review_tokyo_v618.py`.

The packed masks are valid only for this registered Tokyo pair. The v6.18 route
is explicitly selected with `tokyo=v618`; the previous default/legacy sources
and production lane stay available.

## User visual validation Todo

Affected surfaces are the Tokyo v6.18 Closed/Open endpoints, fold preview,
recording preview, and independent screen-chrome controls.

- Watch once for the 1.15-second unfold and the three distinct color stages.
- Confirm the cover's early dark exit feels right and keeps attention on one tower.
- Confirm the natural A grade, warm-white to yellow tower transition, right-panel
  clock/date placement, top caps and flush lower-right control.

No blocker prevents this local review. A numbered-frame export and the user's
visual acceptance are still required before claiming an accepted final master.
