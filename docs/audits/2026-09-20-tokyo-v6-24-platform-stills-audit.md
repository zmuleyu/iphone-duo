---
title: Tokyo v6.24 platform stills audit
status: pending-user-review
updated: 2026-09-20
scope: Screenshot gate for shared 16:9 platform framing
---

## Purpose and boundary

This is a screenshot-only review package. It does not approve or generate a
video, image sequence, audio file, platform upload, deployment or publication.
The v6.23 Fold Engine, time semantics, world assets, shell, hinge, Screen UV
and physical opening direction remain the authority.

## Shared 16:9 camera contract

The v6.24 camera increases only the platform-stills 16:9 framing scale so the
device is the primary object while retaining its complete shell, hinge and
hardware controls. It uses one camera and one 16:9 composition in two forms:

- `3840x2160`: native WebGL canvas capture, the composition authority and
  Xiaohongshu quality-review candidate;
- `1920x1080`: deterministic Lanczos downsample of the corresponding clean 4K
  PNG, the X ordinary-web upload review candidate.

No 9:16 or 2160x3840 output is generated. The internal cyan overlay is a
conservative project review guide only; it does not claim to be an official X
or Xiaohongshu safe-area specification.

## State matrix

All eight states are `pending-user`; acceptance cannot be inferred from this
audit or from mechanical QC.

| Frame | Time | State |
| ---: | ---: | --- |
| 60 | 1.000 s | Closed hold |
| 148 | 2.467 s | first visibly moving fold |
| 180 | 3.000 s | 90° fold |
| 186 | 3.100 s | 110° fold |
| 200 | 3.333 s | 150° fold |
| 222 | 3.700 s | fully Open Unlit |
| 268 | 4.467 s | activation midpoint |
| 359 | 5.983 s | final Gold Hero |

Each state has four original files: clean 4K, safe-review 4K, clean 1080p and
safe-review 1080p. The two contact sheets and `state-manifest.json` are under
`artifacts/v6.24-tokyo-platform-stills/`.

## Mechanical evidence

- The renderer canvas was exactly 3840x2160 for every authority capture.
- Every 1080p clean PNG is byte-identical to a fresh Pillow Lanczos resize of
  its paired 4K clean PNG.
- All recorded screen UI flags are false; authored left/right screen blur is
  zero; no MP4, WebM, MOV or audio exists in the state package.
- Open Unlit and final Gold tower registration measures a 0px translation.
- Frozen engine/world input hashes remained unchanged and browser console errors
  were empty.

Original-size visual inspection was performed on the 4K Hero plus both contact
sheets. It confirms that the device has a stronger horizontal presence without
cropping the shell, but it cannot replace user judgment for subject scale, dark
city legibility, gold-tower hierarchy or safe-area taste. Those are the next
required approval decisions.
