# Tokyo V6.28 local final delivery

Date: 2026-09-20

## Accepted composition

- Horizontal 16:9 only.
- 4.65-second loop at 60 fps with 279 authored master frames.
- Closed hold 0.00–0.65 s; unfold 0.65–1.90 s; unlit pause 1.90–2.25 s; tower activation 2.25–2.80 s; hero hold 2.80–4.35 s; extinction and close complete at frame 278.
- Fixed camera, no motion reframe, no source upscale, no title by default, no screen UI, no halo, bloom, particles, motion blur, or audio.
- Frame 0 and the final Closed endpoint are byte-identical.

## Local deliverables

| Platform | File | Video | SHA-256 |
| --- | --- | --- | --- |
| Xiaohongshu | `deliverables/tokyo/iphone-duo-tokyo-loop-v6.28-xiaohongshu-4k60-silent.mp4` | H.264, 3840×2160, 60 fps, yuv420p, limited BT.709, silent | `1E20FDC121FD6F55D473942CFF325B822614ABA4F6B05F4D652FF6F5617C77EE` |
| X | `deliverables/tokyo/iphone-duo-tokyo-loop-v6.28-x-1080p40-silent.mp4` | H.264, 1920×1080, 40 fps, yuv420p, limited BT.709, silent | `F9291E99C5C46702B581422A11F02436D6DC812F0B232CFD2DDA1C1A9D7FFFE8` |

The deliverables directory is local-only and ignored by Git. This receipt records exact outputs; it does not authorize upload, deployment, or publication.

## Reproduction surface

- Runtime manifest: `media/tokyo/v6.28-loop-preview-manifest.json`
- Screenshot gate: `scripts/capture_tokyo_v628_loop_stills.py`
- Numbered 4K master capture: `scripts/capture_tokyo_v628_platform_master.py`
- Runtime plates: listed in `docs/tokyo-assets.md`

Historical V6.16–V6.27 candidate images, audits, and capture scripts were removed from the current tree after V6.28 delivery. Their Git history remains available if a forensic comparison is needed.
