# PixelLock Image Pipeline v0.2

A geometry-first image workflow for AI-assisted **Pixel-Locked Outpaint** and **Geometry-Locked A → B Restyle**.

v0.2 keeps the deterministic v0.1 outpaint path and adds the missing A/B workflow for the Tokyo Tower fold-transition project:

```text
Reality Tokyo A
  → Canny / anchor / skyline geometry guide
  → GPT Image generates Red / Black / Yellow B
  → automatic Tokyo Tower + building-contour comparison
  → threshold breach = FAIL
  → PASS exports matched A/B Duo assets
```

## What is new in v0.2

- New **Geometry-Locked A → B Restyle** workflow.
- New `tokyo_ab_restyle` preset for the locked **1544×1086 Reality master A**.
- Full-frame GPT Image edit path: style may change, geometry may not.
- Geometry guide generated from A using structural Canny edges.
- Critical-region QC:
  - Tokyo Tower anchor edge similarity.
  - Building/skyline structural-contour similarity.
  - Tokyo Tower anchor translation check using edge-map phase correlation.
- Automatic PASS / FAIL policy. Any critical metric beyond preset thresholds fails the candidate.
- Geometry overlay artifact: shared edges in white, A-only geometry in red, B-only geometry in blue.
- Anchor A/B side-by-side preview.
- Matched export pair after PASS:
  - `A_open_2670x1878.png`
  - `A_closed_right_1335x1878.png`
  - `B_open_2670x1878.png`
  - `B_closed_right_1335x1878.png`
- New free deterministic **Local Posterize** provider to smoke-test the A→B pipeline without API cost. It is a geometry/QC test, not a replacement for semantic GPT Image restyling.
- Browser UI now switches between **Outpaint** and **A → B Restyle**.

## Quick start — Windows

Double-click `run_windows.bat`, then open:

`http://127.0.0.1:8765`

For GPT Image, set the key before launching:

```bat
set OPENAI_API_KEY=your_key_here
run_windows.bat
```

## Quick start — macOS / Linux

```bash
export OPENAI_API_KEY=your_key_here   # optional
./run_macos_linux.sh
```

## Recommended Tokyo A → B flow

1. First use the v0.1/v0.2 **Outpaint** workflow to create the locked Reality master:
   - source: `1448×1086`
   - extend left by `96 px`
   - master A: `1544×1086`
2. Switch the UI to **A → B Restyle**.
3. Upload that `1544×1086` master A. The package includes:
   - `examples/tokyo_reality_master_1544x1086.png`
4. Click **Prepare** to generate the Canny geometry guide and full-frame edit mask.
5. Use **Local Posterize** for an offline smoke test, or **GPT Image** for the actual Red / Black / Yellow B.
6. Click **Validate Geometry**.
7. Only a PASS candidate is accepted as `restyle_B_geometry_pass.png` and becomes exportable.
8. Click **Export A + B** to create matched Duo Open/Closed assets.

## Geometry QC policy

The `tokyo_ab_restyle` preset currently uses a strict but editable policy:

- Tokyo Tower anchor edge F1: `>= 0.60`
- Building contour edge F1: `>= 0.56`
- Anchor translation: `<= 6 px`
- Tolerant edge matching radius: `5 px`

These are engineering gates, not claims of mathematical pixel identity. Full-frame style changes cannot use v0.1's `0 changed pixels` rule because color and rendering are intentionally different. The purpose of v0.2 is to reject visually plausible B images that moved the tower or changed the skyline geometry.

Thresholds live in:

`presets/tokyo_ab_restyle.json`

## v0.1 Outpaint remains unchanged

The original iPhone Duo preset still supports:

- Exact source placement.
- GPT Image edit provider.
- Free Local Reflect provider.
- Deterministic recompose that force-pastes A back into the locked region.
- Exact pixel-diff QC (`0 changed pixels`).
- Seam QC.
- `1448×1086 → 1544×1086 → 2670×1878` export.
- Right-half `1335×1878` Closed preview.

## Key v0.2 artifacts

For A → B Restyle, each project may contain:

```text
source/source.png                          # Reality A
working/restyle_api_input.png
working/restyle_api_mask.png
generated/candidate_api.png
generated/candidate_target.png             # Candidate B
qc/source_edges.png
qc/candidate_edges.png
qc/geometry_guide.png
qc/geometry_overlay.png
qc/anchor_preview.png
qc/qc_report.json
final/restyle_B_geometry_pass.png           # only created after PASS
final/A_open_2670x1878.png
final/A_closed_right_1335x1878.png
final/B_open_2670x1878.png
final/B_closed_right_1335x1878.png
project.json
```

## Included examples

- `examples/tokyo_reality_1448x1086.png` — original v0.1 source.
- `examples/tokyo_reality_master_1544x1086.png` — recommended v0.2 Reality A.
- `examples/tokyo_redblack_local_demo_1544x1086.png` — Local Posterize smoke-test B.
- `examples/tokyo_geometry_overlay_demo.png` — example geometry QC overlay.
- `examples/tokyo_anchor_preview_demo.png` — example Tokyo Tower A/B anchor preview.

## Security

`OPENAI_API_KEY` is read from the process environment. The UI never asks for or persists the key in a project.


## v0.2.2 Tower ROI Lock + automatic repair

The Tokyo A→B path now freezes a **Tower ROI from Geometry Source A** during Prepare. Candidate B is checked against this immutable region with tower-edge registration, per-axis position limits, shape retention, mask/bbox drift, and the existing global skyline gates. Restyle generation can run `Generate → QC → automatic Repair` for up to 3 attempts, while retaining every candidate and QC report. See `V0.2.2_TOWER_ROI_AUTO_REPAIR.md`.

## v0.2.1 Geometry-Locked A→B backend closure

The restyle path now treats the Reality master as the only geometry authority and stores style reference images separately. Use the dedicated `restyle/*` endpoints for prepare → generate → validate → repair. Hard geometry QC blocks acceptance/export; style QC is advisory by default. See `V0.2.1_BACKEND_CLOSURE.md` for the contract and artifact list.
