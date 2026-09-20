---
title: Tokyo v6.23 six-second motion-video candidate
status: video-candidate / pending-user-review
updated: 2026-09-20
scope: Local silent review export; no publication or deployment
---

## Result

The final review candidate is a silent 1920x1080 H.264 MP4 with exactly 360
authored frames at 60 fps and a 6.000-second duration. Numbered PNG frames are
the timing authority; the MP4 was encoded from them without interpolation or
temporal resampling.

The video is local at
`artifacts/v6.23-tokyo-silent-video/iphone-duo-tokyo-v6.23-silent-60fps.mp4`.
Its SHA-256 is
`43DD78D158DF2612EBA7EA5B5E31DC9D9FE86C69E6C9AEC7C8599703AAD7DD27`.

## Frozen visual direction

- Closed continues the clean v6.19 photographic direction.
- The inner display uses one RedBlack panorama and one fixed UV/filtering path
  shared by both physical panels.
- There is no reveal, wipe, A/B mix, authored screen blur, title, time, date,
  TOKYO label, Wi-Fi, utility shortcut or Home Indicator in the v6.23 recording
  profile. Physical device cameras, controls, shell, hinge and bezel remain.
- The Unlit tower is a registered, near-black dark-copper plate. Its mean
  luminance is 110.26% of the local city mean, within the requested 108–112%
  range. Its outline stays inside the tower alpha with no halo or bloom.
- The accepted v6.22 gold tower plate remains the sole final activation layer.

## Timeline

| Time | Frames | State |
| --- | ---: | --- |
| 0.00–2.30 s | 0–137 | stable Closed Reality |
| 2.30–3.70 s | 138–221 | physical left-panel unfold; inner RedBlack world |
| 3.70–4.15 s | 222–249 | fully Open Unlit pause |
| 4.15–4.80 s | 250–287 | Unlit-to-Gold tower activation |
| 4.80–6.00 s | 288–359 | clean stable Hero hold |

The Fold Engine's normal endpoint snap initially completed Open one frame early.
The v6.23 record profile now holds the pre-open angle below the endpoint until
frame 222, preserving the authored 3.700-second boundary. A second rejected run
also exposed the legacy completion path resetting the final frame to Unlit; the
accepted run reapplies the final authored lighting state after endpoint lock.

## Motion and cleanliness QC

- Angle evidence: 90° frame 180; 110° frame 186; 150° frame 200; 180° frame 222.
- Authored blur radius: 0 on both panels. The 110° left-screen Laplacian
  variance improved from 1.470 in the rejected v6.22 blurred still to 128.966,
  an 87.73× increase.
- Fixed Tokyo Tower registration from 150° to 180°: 0 px shift, match score
  0.9874.
- Open pause frames 222 and 249: maximum pixel-channel delta 0.
- Hero frames 288 and 359: maximum pixel-channel delta 0.
- Tower light is exactly zero before frame 250 and reaches one at frame 288.
- Chrome/UI values are zero for every frame; screen UI is absent.
- Console/runtime errors: 0. Frozen capture inputs changed after capture: 0.
- The source sequence has one intentional sub-pixel settle duplicate at frame
  139 immediately after the 2.30-second hold, and no duplicate after visible
  travel begins. The encoded H.264 decode reports no duplicate motion frames.

## Encode and environment

The capture used Chrome 152.0.7977.75, a 2880x1800 WebGL canvas at device pixel
ratio 2, and ANGLE on an NVIDIA GeForce RTX 3070 through D3D11. FFmpeg 8.1.1
encoded H.264 at 60/1 fps, yuv420p, BT.709 metadata, one video stream and no
audio stream. `ffprobe.json`, decoded frame hashes, frame ledger, renderer data,
QC summary and review sheets are preserved beside the local video.

No UI unit tests, E2E suite, GitHub Actions, deployment, publication, title
effect, birds, sound or additional visual decoration were run or added. User
review of the actual motion candidate remains the acceptance gate.
