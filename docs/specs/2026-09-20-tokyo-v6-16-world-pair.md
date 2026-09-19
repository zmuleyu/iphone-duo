---
title: Tokyo V6.16 Static World Pair
status: local-qc-passed-awaiting-user-art-review
updated: 2026-09-20
---

# Tokyo V6.16 Static World Pair

The user's current instruction authorizes gpt-6-astra to finish both static masters.
This supersedes the earlier sky-only ChatGPT generation proposal. The final masters
use no ChatGPT browser, image generator, paid provider, video, runtime integration,
or deployment. A preliminary built-in session image-generator sky plate is retained
only as route provenance and is explicitly excluded from both final masters.

## Authority

`media/tokyo/reality-wikipedia.png` is the sole geometry, crop, skyline, tower and
occlusion authority. Its SHA-256 is
`FC096FABE3C1A822F41B977119EFA3E460F8E69952D5C60D0940E24B6C564EBD`.
It and `media/tokyo/redblack-wikipedia.png` remain unchanged. The original RedBlack
reference supplies visual language only. Source rights remain the existing project
provenance; this static edit does not grant publication rights.

## Implementation

Run `python scripts/build_tokyo_v616_world_pair.py` using the environment recorded
in the metrics. It refuses to resize the authority. Source-guided GrabCut and
source-color tower mattes are shared by both outputs with an identity transform.
The masks define compositing support; their reuse is not claimed as independent IoU.

- Reality: restrained source color correction and sky bilateral smoothing, preserving
  the photographic clouds, buildings, tower and lights.
- RedBlack: procedural continuous crimson sky, three near-black city values,
  source-derived window groups with small isolated components removed, yellow tower
  recoloring that preserves the original lattice. No generated city or tower pixels.
- Outputs: `media/tokyo/candidates/reality-v6.16-astra-master.png` and
  `media/tokyo/candidates/redblack-v6.16-astra-master.png`.
- Compatibility copy: `media/tokyo/candidates/redblack-v6.16-cand-01.png`.

## Local gates

Both masters must be 2670 x 1878 RGB PNG. The source-derived tower edge target is
tested against actual output Canny edges with two-pixel tolerance; recall must be
at least 0.78. Independent output-edge registration searches offsets within four
pixels and must remain within four pixels, with zero intended. Masks are reused
without translation, warping or resampling. Inspect the overview and tower crop
for seams, added glow, filled lattice holes, and style drift.

See `media/tokyo/v6.16-world-pair-manifest.json`,
`artifacts/v6.16-tokyo-world-pair/metrics.json`, and
`docs/audits/2026-09-20-tokyo-v6-16-pixellock.md` for actual outputs and evidence.
Final aesthetic approval remains with the user.
