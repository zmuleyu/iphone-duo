# Tokyo V6.17 silent review demo

Status: local review preview; not a deterministic numbered-frame master and not
authorized for production or publication.

## Result

- Silent H.264 MP4: `artifacts/v6.17-tokyo-silent-demo/iphone-duo-tokyo-v6.17-silent-review-demo.mp4`
- Evidence overview: `artifacts/v6.17-tokyo-silent-demo/contact-sheet.png`
- Runtime evidence: `artifacts/v6.17-tokyo-silent-demo/runtime-state.json`
- Run manifest: `media/tokyo/v6.17-silent-demo-manifest.json`

The 5.8-second cut uses a 0.65-second Reality hold, a 4.15-second four-beat
editorial unfold, and a 1.0-second open poster finish. The fold remains the
transition: RedBlack enters from right to left as the device opens. The accepted
v6.16 Reality and RedBlack masters remain unchanged.

No music, birds, additive tower highlight, pulse, special copy, camera move, or
extra climax is present. The close-state clock remains hidden; the open-state
chrome remains visible. Device geometry, hinge, panels, camera, Screen UV, crop,
and fixed 16:9 record framing stay on the existing Fold Engine authority.

## Mechanical evidence

- 1920×1080, H.264, yuv420p, CFR 60 fps.
- 5.800 seconds and 348 encoded frames.
- One video stream and no audio stream.
- Runtime frames are the half-open interval `0..347`; clock pass is true.
- Both source masters are 2670×1878 and pass the existing pair gate.
- Browser capture produced no console or runtime errors.

The WebM source is captured through `captureStream`; the MP4 is therefore a
review preview. A future final master must use numbered-frame capture before it
can be called deterministic.

## User review Todo

- Watch the complete cut once for the four-beat unfold rhythm and the final
  one-second hold.
- Confirm the RedBlack world enters from the right edge and advances left.
- Confirm the shared tower, skyline and crop stay registered through the fold.
- Check the closed/open chrome, aligned upper keys, flush lower-right control,
  hinge and 3D shell against the current official-state references.
- Decide whether the next pass needs montage, camera language, tower treatment,
  birds, text or music; none is assumed by this demo.
