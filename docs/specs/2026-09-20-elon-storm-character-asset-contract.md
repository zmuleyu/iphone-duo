---
title: Elon STORM II Character Asset Contract
status: character-phase-accepted
updated: 2026-09-20
scope: STORM II-style iPhone Duo video character assets; internal preparation only
---

# Elon STORM II character asset contract

## Boundary

This contract covers the Real Elon experimental character layer for the STORM-inspired iPhone Duo branch. It does not modify the Tokyo branch, the Fold Engine, device geometry, hinge, panels, camera, Screen UV, frame clock, or any Tokyo art. Generated characters may later enter only through the Character Layer and approved masks over a Clean Plate.

This is an internal calibration lane. Source/provenance, likeness permission, territories, publication intent, monetization, and synthetic-media disclosure are unresolved. No generated result may be treated as cleared for public, commercial, advertising, product-endorsement, or release use. Voice, dialogue, quotes, logos, political content, and invented conduct are out of scope.

The user confirmed on 2026-09-20 that every current character role in this manifest is for the STORM II-style video lane. These are not generic standalone character-library assets and they are not Tokyo assets. “STORM II-style” means the approved translated anchor → delay → formation → one pulse → freeze grammar; it does not authorize copying a reference film's shots, school setting, costumes, choreography, music, grading, or edit rhythm.

## Intake receipt

```yaml
project_root: D:/projects/creative_group/iphone-duo
worktree: D:/projects/creative_group/iphone-duo-elon-character-calibration
git_head: 84c653f5158fa1d82d6f3db66f132327985cec75
branch: work/elon-storm-character-calibration
source_checkout_observed: work/v6.24-tokyo-platform-stills@177e4ec
source_checkout_dirty_paths: []
active_contract: this document
fold_authority: existing iphone-duo Fold Engine; unchanged
camera_authority: existing iphone-duo camera; unchanged
uv_authority: existing iphone-duo Screen UV; unchanged
frame_clock_authority: existing frame-index contract; unchanged
accepted_assets: [ELON-CAL-001, ELON-CAL-002]
retained_candidates: [ELON-REF-001, ELON-REF-002]
publication_authority: false
deployment_authority: false
paid_service_authority: false
```

## Shot-derived role needs

The plans converge on three Elon motion states, not a generic character sheet:

1. **Closed / RUMOR** — Elon sits in the screen-right third, looking toward screen-left/hinge in profile or three-quarter view. The final composition may crop face/shoulder, but the source asset should retain complete anatomy and enough margin for alternate crops.
2. **Opening / FORMATION** — Elon travels a short distance toward the hinge, turns from profile through three-quarter, and settles. A readable weight shift and restrained arm position are required.
3. **Full-open / HOLD-PULSE** — front or slight three-quarter anchor with one compact conductor-like downbeat after the open hold. The existing small-cue PNG remains a style and pose reference, but its baked background and upper-leg crop prevent production use; `ELON-OPEN-001` supplies the complete transparent source.

Prototype 01 also requires Jensen Huang and Sam Altman as separate counter-anchor assets, plus exactly one midground person. The user authorized continuous execution on 2026-09-20; the recommended midground choice is Dario Amodei because the safety/lab counterweight is the clearer narrative fit for the current formation. Gwynne Shotwell remains listed but is skipped for this batch. Anonymous chorus units are not celebrity assets and are outside this calibration manifest.

## Accepted style lock

- Editorial caricature with recognizable but simplified facial structure; no photoreal skin or photographic texture.
- Strong silhouette readable at small folded-screen scale: clear head shape, shoulders, hand cue, and stance before facial detail.
- Clean vector-like/polygonal planes with limited shading; crisp edges; no painterly noise.
- Dark neutral wardrobe for Elon, primarily black tee or short dark jacket; clothing folds remain subordinate to the silhouette.
- Cool cyan rim on screen-left and restrained warm amber rim on screen-right, with neutral front illumination. Lighting direction stays identical across the lane.
- One subject per file on a genuinely transparent background, no baked scene, floor, vignette, smoke, shadow cloud, or UI.
- Full anatomy for generated calibration assets: both hands, all fingers at usable size, both legs, and both shoes visible with roughly 10–15% clear padding.
- No text, labels, signatures, brands, logos, Apple/Duo device, company objects, other people, robots, collage, contact sheet, multi-pose sheet, or alternate pose in the same image.
- No imitation of STORM II wardrobe, school setting, blocking, choreography, grading, or shot composition. Only the abstract anchor → delay → formation → one pulse → freeze grammar is retained.

## Reference inventory

| File | Mechanical facts | Observed content and usability | Decision |
|---|---|---|---|
| `4o0Ga.jpg` | JPEG, 1792×1104, RGB, no alpha | Three-person editorial group on a dark background. The center figure is an Elon likeness with a small hand cue; the flanking identities appear consistent with the plan's compute/chat counter-anchors, but the file has no provenance metadata linking names. Limbs are cropped and subjects are merged. | Style/identity reference only; never a final asset and not uploaded for Elon-only calibration. |
| `92VFl.jpg` | JPEG, 1872×1056, RGB, no alpha | Three-person editorial group, chest/waist crop, dark background, cyan edge light. Random filename and no source metadata make individual identity assignment unsafe. | Unnamed style reference only; excluded from manifest prompts. |
| `ChatGPT Image 2026年9月19日 12_43_10.png` | PNG, 1122×1402, RGB, **no alpha** | Single Elon likeness, front-facing, black tee, compact right-hand cue, cyan/amber rim light. Cropped through upper legs; right fingertips approach the frame edge. Strongest current style and identity candidate but not a production cutout. | `ELON-REF-001`, retained-candidate; do not regenerate. |
| `h4YbD.jpg` | JPEG, 1168×784, RGB, no alpha | Three recognizable public-figure likenesses, head-and-shoulder crop, dark background. The source does not map names to positions, and most are outside Prototype 01. | Reference only; excluded from the current manifest. |
| `qfFrT.jpg` | JPEG, 1168×784, RGB, no alpha | Three recognizable public-figure likenesses, chest crop, dark background. One bearded figure may be relevant to the midground option, but the filename/source does not prove identity. | Reference only pending user/source confirmation; not used for calibration. |
| `Te8Tr.jpg` | JPEG, 784×1168, RGB, no alpha | Single full-body Elon likeness, neutral front stance, black clothing, adequate head/foot margin, but baked dark environment and decorative circuitry. Hands are small and one arm is visually quiet. | `ELON-REF-002`, retained-candidate for proportion/stance only; do not regenerate. |

Reference files remain read-only under `C:/Users/Admin/Downloads/duo/人物库/`. Hashes are recorded in the manifest.

## Calibration window

The first ChatGPT Chat window contains exactly two new, independent images:

- `ELON-CAL-001` — Closed/RUMOR source: full-body screen-left-facing profile/three-quarter pose designed for later screen-right placement and crop.
- `ELON-CAL-002` — Opening/FORMATION source: full-body half-turn with a restrained hinge-ward step and compact hands.

`ELON-REF-001` supplies the full-open/downbeat candidate, so calibration does not regenerate the same pose merely to fill a three-image window. ChatGPT may make at most one targeted repair per new ID for a clear blocker. A repeated localized defect should route to image editing of the best candidate, not another full regeneration.

## Continuous support batch and final human gate

The bounded Elon repair window is complete. `ELON-CAL-001` has 12.62%/13.27% top/bottom padding. `ELON-CAL-002` has a front-settled head, readable three-quarter torso, screen-left lead step and weight shift, 11.34%/13.69% top/bottom padding, and a normalized 1122×1402 canvas. Both retain real RGBA transparency; alpha values below 16 were cleared deterministically to remove distant glow without changing visible subject RGB or higher-alpha edges.

On 2026-09-20 the user confirmed the repaired direction and authorized the remaining character work to run as one continuous batch without intermediate intervention. `ELON-CAL-001` and `ELON-CAL-002` are therefore frozen as accepted baseline assets and must not be regenerated. The ordered remaining batch is:

1. `ELON-OPEN-001` — complete transparent full-open/downbeat source;
2. `JENSEN-SUP-001` — compute counter-anchor;
3. `SAM-SUP-001` — conversation counter-anchor;
4. `DARIO-MID-001` — the single selected midground counterweight.

Each ID may receive at most one whole-image repair and one localized follow-up. A blocked item must not stall later IDs. The next human decision is one consolidated review after all visible final candidates have been downloaded, mechanically checked, and assembled into the phase contact sheet. Video, composite, publication, deployment, and public/commercial use remain outside this batch. Source/likeness rights and intended use still require separate clearance before any public/commercial lane.

The continuous support batch is complete. The original four-ID master prompt was rejected before generation by the generator's content filter, so the same frozen requirements were recovered as four sequential single-character windows in the same durable chat. All four first-pass images were exported; no generative repair was used. Local processing only cleared alpha below 16 and uniformly scaled/recentered each complete subject to the frozen 10–15% safe-padding target. Original downloaded PNGs remain preserved beside the normalized finals.

`ELON-OPEN-001`, `JENSEN-SUP-001`, `SAM-SUP-001`, and `DARIO-MID-001` all pass local visual inspection for the requested identity lane, pose hierarchy, complete visible anatomy, forbidden-object absence, and cyan-left/amber-right lighting. Mechanical QC confirms 1122×1402 RGBA, real transparency, clear canvas edges, and approximately 12.4–12.6% top/bottom padding for each new asset. On 2026-09-20 the user accepted the consolidated six-asset contact sheet. All six final hashes are frozen as the accepted STORM II character source set. Fold Engine, Tokyo assets, video, composite, and publication remain untouched.
