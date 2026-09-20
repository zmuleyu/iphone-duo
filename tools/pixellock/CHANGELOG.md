# Changelog

## v0.2.3 — 2026-09-18 — Repair Loop Guards + Vectorized ROI Search

Response to field feedback: `test_closed_loop_auto_repairs_failed_tower_roi` appeared to
run unbounded in an offline container environment. Root-cause analysis on a standard
machine: no unbounded loop exists (attempt budget always applies); the full suite runs
10 tests in ~12 s. The observed slowness is environment cost (weak CPU / non-optimized
numpy/OpenCV). Hardening shipped anyway:

- `repair()` / `run_closed_loop()` accept `time_budget_s` (default 300, env
  `PIXELLOCK_TIME_BUDGET_S`). Exhaustion lands deterministically in
  `status=repair_exhausted` with `auto_repair.stop_reason="time_budget"`.
  A zero budget blocks any repair attempt (`>=` comparison, tick-safe).
- `_shift_edge_recall` shift search vectorized: the (2s+1)^2 Python offset loop
  (1089 iterations at the default ±16 px) is replaced by two `cv2.filter2D`
  correlations with identical semantics (hits/valid, same tie-break order).
- New regression tests: `test_closed_loop_respects_attempt_budget_when_all_fail`
  (always-failing provider stops at the attempt budget) and
  `test_repair_stops_on_time_budget` (zero budget spends no repair attempt).
- Added `openrouter_image` provider (chat-completions image edit via curl CLI
  transport; works around local TLS resets that break Python HTTP stacks).

## v0.2.2 — 2026-09-18 — Tower ROI Lock + Auto FAIL/Repair

- Added immutable A-derived Tokyo Tower ROI lock.
- Added tower-only structural registration with per-axis 4 px soft limit and 8 px hard limit.
- Added independent tower position and tower shape hard gates.
- Added aligned tower-edge retention, locked-ROI mask IoU, bbox-delta, and area-drift checks.
- Added per-attempt `tower_roi_overlay_XX.png` diagnostics.
- Added automatic Generate → QC → FAIL → Repair closed loop with a default 3-attempt run budget.
- Added measured dx/dy repair directives while keeping Geometry Source A as the only generation source.
- Added `repair_exhausted` state; export stays blocked until geometry PASS.
- Kept final-art/style tuning out of this increment.

## v0.2.0 — 2026-09-18

- Added `Geometry-Locked A → B Restyle` workflow.
- Added Tokyo Reality A → Red/Black/Yellow B preset at 1544×1086.
- Added structural Canny geometry guide.
- Added Tokyo Tower anchor ROI, building-contour ROI, and configurable QC thresholds.
- Added tolerant edge F1 checks and anchor translation measurement.
- Added automatic PASS/FAIL geometry gate and acceptance artifact only on PASS.
- Added geometry overlay and anchor comparison preview.
- Added matched A/B Duo Open + Closed exports after geometry PASS.
- Added free deterministic Local Posterize provider for offline smoke testing.
- Updated browser UI with Outpaint / A→B modes.
- Kept v0.1 pixel-locked outpaint workflow and old project compatibility.

## v0.1.0 — 2026-09-18

- Added exact pixel-locked outpaint workflow.
- Added iPhone Duo 1448×1086 → 1544×1086 → 2670×1878 preset.
- Added GPT Image edit provider.
- Added free local OpenCV reflect provider for offline smoke testing.
- Added automatic 16-pixel API canvas padding and crop-back.
- Added deterministic source recompose and 0-pixel-diff QC.
- Added seam QC, edge preview, Open export and right-half Closed export.
- Added local FastAPI browser UI and Windows/macOS/Linux launch scripts.

## 0.2.1 — Geometry-Locked Restyle Backend Closure

- Geometry Source A and Style Reference B are now separate project inputs.
- Added versioned A→B candidates plus bounded repair attempts.
- Added `edge_map_A`, `tower_mask_A`, `skyline_mask_A`, and `structure_overlay_A` prepare artifacts.
- Added hard geometry gates for dimensions, tower shift, tower mask/bbox IoU, anchor edge overlap, skyline edge overlap, and skyline mask IoU.
- Added advisory style QC for sky redness, building darkness, tower warmth, and tower dominance.
- Added dedicated `/restyle/prepare`, `/restyle/generate`, `/restyle/validate`, `/restyle/repair`, and `/restyle/style-reference` endpoints.
- Legacy restyle routes now delegate to the same backend workflow.
