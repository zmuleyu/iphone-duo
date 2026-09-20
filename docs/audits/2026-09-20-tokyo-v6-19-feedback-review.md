---
title: Tokyo v6.19 centered UI and fixed-step video review
status: ready-for-user-review
updated: 2026-09-20
scope: iphone-duo Tokyo v6.19
---

Verdict: ready for user visual review. This cut now comes from 348 numbered PNGs,
not captureStream. It is a silent review render, not publication approval.

## Output

`artifacts/v6.19-tokyo-silent-demo/iphone-duo-tokyo-v6.19-silent-review.mp4`

The same directory contains `frames/frame_000000.png` through `frame_000347.png`,
`actual-video-contact-sheet.png`, `contact-sheet.png`, `shell-contact-sheet.png`,
`world-pair-overview.png`, `tower-ab.png`, `frame-ledger.json`, `runtime-state.json`,
`renderer-info.json`, `console-errors.json`, `asset-evidence.json`, `ffprobe.json`,
`qc-summary.json` and `encoded-motion-qc.json`.

## Four principal repairs

| Feedback | Status | Implementation and evidence |
| --- | --- | --- |
| Centered date/time and closed-state UI | covered | Independent physical-display chrome, centered on the closed cover and centered across the fully open display. The date is smaller. Closed UI fades in on frames 0–5; open UI fades in on 138–143 only after the hinge is flat. Clock/date never render across a moving hinge. Existing chrome switches still work. |
| More exposed, aligned top buttons | covered | Current Apple product images show two restrained controls outside the top silhouette. Both caps move +0.05 in world Y; their parent rotates source local -Z onto that normal. The script now guards this basis. Their sizes and other axes stay unchanged. The lower-right key retains its zero offset. |
| Right-to-left reveal and controlled unfolding | covered | Inner-only red starts at the global right edge and advances left. City and tower remain separately masked and delayed. The outer A cover exits at 18–57.6 degrees. No red samples the cover; no second B tower can appear there. A 100-unit fixed camera with matched FOV preserves the Open composition while reducing real perspective overshoot. |
| New registered A/B candidates | covered | New 2670×1878 A/B assets retain identical source coordinates. A has a neutral sky, lifted lower shadows, warm amber windows and a warm-white tower. B uses cleaned source-shaped windows, continuous depth tones, darker gold tower luminance and sub-code-value red-sky dither. Neither previous master is overwritten; city/tower masks remain byte-identical in support. |

## Official evidence and scope of interpretation

Inspected on 2026-09-20: [Apple iPhone Duo product page](https://www.apple.com/iphone-duo/),
[official display image](https://www.apple.com/v/iphone-duo/b/images/overview/product-viewer/display__bx48n0ntsgvm_large.jpg),
[official foldable image](https://www.apple.com/v/iphone-duo/b/images/overview/product-viewer/foldable__iybtpzlhgj6u_large.jpg),
and the repository's original [Apple Star White USDZ](https://www.apple.com/105/media/us/iphone-duo/2026/9305e4b9-72d9-4c05-9381-b572adadd5e5/ar/iPhone_Duo_e-sim_Star-White_Variant.usdz).

The clock digits retain the prepared Apple inner-lock-screen overlay; its
date/time are horizontally centered in the official asset. The new date text is
Fri Oct 23. The +0.05 cap translation is a bounded visual matching choice, not an
Apple dimensional specification. Source local Y actually points toward the
camera in these cap parents; source local Z=-0.05 is the correct outward move.
The source build/patch chain owns this change, not a runtime geometry offset.

The fixed camera moves from distance 40 to 100 for this profile and narrows FOV
by the same projection ratio. This is a new constant projection, not a camera
move during the shot. It was necessary because timing alone cannot remove the
old perspective-driven 5.39% silhouette overshoot. Device mesh, hinge, panels,
materials and authored UVs stay unchanged apart from the two named cap
translations. A cover sampling correction `(0.0085, 0.00025)` aligns the two
photographic projections without modifying either bitmap.

## Timing, layers and image rhythm

- Frames `[0,51)`: closed hold; `[51,138)`: unfolding; `[138,348)`: open hold.
- Open completes at 2.30 seconds. Visible silhouette 10–90% travel is 0.90 seconds
  (frames 64–118), maximum single-frame travel 3.12%, visible overshoot 1.04%.
  Hinge-angle overshoot is zero.
- Stage driver is normalized physical opening angle, not elapsed time:
  red `[0.16,0.58]`, black `[0.52,0.78]`, yellow `[0.78,0.94]`.
  Red's sweep proceeds globally from source x=1 toward x=0 on the inner display.
- One restrained, masked tower pulse peaks at frame 191 (3.183 seconds), well
  after Open. Windows receive a smaller 2.5% modulation plus a slow 1.8%
  luminance breath during the hold. There is no halo, extra text, bird, audio,
  motion blur, screen blur, camera movement, or geometry motion in the tail.

## Measured acceptance

H.264, 1920×1080, yuv420p, CFR 60, 348 frames, 5.800 seconds, one video stream,
no audio. Synchronous render/readback writes one PNG per integer frame index;
encoding applies no FPS resampling. Both source-frame and decoded-video hashes
show zero repeated adjacent frames during the unfold. Repeated frames in the
intentional closed hold are expected, not dropped capture frames.

Tower cover-to-inner registration is 2 px horizontally and 0 vertically with
0.947 normalized correlation in a fixed A/A tower ROI. A/B source-edge best
shifts are both `(0,0)`; tower edge recall within 2 px is 99.90% for A and 94.36%
for B. Shared masks prove compositing registration, not independent segmentation
quality. The final tower texture and perceived depth remain visual judgments.

The renderer is Chrome 153 / RTX 3070 / 2× supersampling / anisotropy 16. Console
and runtime errors are zero. Desktop closed/open, intermediate fold, pulse,
poster, and oblique shell views were inspected. The initial resize is settled
before frame zero. JavaScript/Python syntax and focused diff checks pass.
No GitHub Actions, UI unit tests or E2E suite was used.

## Reproduction and retained failures

Build new assets with `scripts/build_tokyo_v619_layers.py`. Rebuild the official
local model with `scripts/prepare-assets.py` and `scripts/patch-shell-asset.py`
using the existing `usd-core==26.8` runtime. Serve the repository on 8766 and use
a task-owned Chrome CDP instance on 9222. Run `scripts/capture_tokyo_v619_frames.py`,
`scripts/review_tokyo_v619.py`, and `scripts/encode_tokyo_v619.py`.

Profile: `?cap=1&tokyo=v619&nofx=1&motion=tokyo-demo&format=16x9&closedUi=1&openUi=1`.
Capture refuses to overwrite existing numbered frames; choose a new output
directory when re-rendering; review/encode also accept that output directory.
`--calibration-only` provides the two neutral A/A
registration frames without a full render.

Retained rejected evidence directories explain observed corrections:
`v6.19-rejected-depth-bands` (hard horizontal tone transitions),
`v6.19-rejected-resize-fov` (legacy resize overrode the narrowed FOV), and
`v6.19-rejected-cap-local-axis` (local Y is not the top outward normal).
The accepted v6.16/v6.18 assets and earlier videos remain intact.

## User visual validation Todo

Affected states are closed/open lock screens, the Tokyo fold/reveal, top controls,
oblique device views and the open-state pulse/breathing.

- Confirm the centered UI size and six-frame fades on both screens.
- Watch the right-to-left reveal and unfolding once for smoothness and tower lock.
- Confirm cap exposure and the flush lower-right key in close/open/3D.
- Confirm the A/B grade, cleaned tower texture and restrained 3.18-second pulse.

No local implementation blocker remains. User visual acceptance is pending.
