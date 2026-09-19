# Tokyo V6.16 Static Pair Local QC — 2026-09-20

Executed by gpt-6-astra through session tools and local Python 3.11.9, OpenCV 4.13.0,
NumPy 2.4.3 and Pillow 12.1.1. No ChatGPT browser conversation or generated image is
part of the final route. No commit, push, runtime integration or deployment performed
by this implementation subtask.

| Output | Dimensions / mode | Tower edge recall (2 px) | Best edge offset |
| --- | --- | --- | --- |
| Reality master | 2670 x 1878 RGB PNG | 0.999090 | [0, 0] px |
| RedBlack master | 2670 x 1878 RGB PNG | 0.957579 | [0, 0] px |

Both exceed the requested 0.78 edge recall and meet the displacement gate. The
actual candidate edges are measured, not a mask compared with its own copy.
An independent rerun of the checked-in recipe reproduced both final PNG SHA-256
values byte-for-byte on 2026-09-20.
The tower and skyline mattes are derived from A and shared without transforms;
this proves common compositing geometry, not independent segmentation accuracy.
The manually bounded segmentation and tone selection are visible for inspection in
`city-mask.png`, `tower-mask.png` and `skyline-mask-overlay.png`.

Visual inspection: source/Reality/RedBlack overview and final full tower crop reviewed.
Reality retains photographic clouds and structure with restrained color changes.
RedBlack has continuous crimson negative space, black city masses, sparse amber
windows and a yellow tower. The previous orange horizon band and storm sky are gone.
No horizontal compositing band or added broad glow is visible. Tower lattice holes,
observation-deck divisions and foreground occlusion remain visible. Fine tonal detail
is intentionally simplified in RedBlack; final aesthetic approval is pending the user.

Evidence under `artifacts/v6.16-tokyo-world-pair/`: `metrics.json`,
`source-reality-redblack-overview.png`, `ab-side-by-side.png`, `tower-ab.png`,
`city-mask.png`, `tower-mask.png`, `window-mask.png`, `redblack-sky-procedural.png`,
`skyline-mask-overlay.png`. Older files in that directory are not final-run evidence.

The manifest records complete output SHA-256 values. Canonical A and the previous
RedBlack baseline were not overwritten. `redblack-v6.16-cand-01.png` is an exact
compatibility copy of the new RedBlack master.
