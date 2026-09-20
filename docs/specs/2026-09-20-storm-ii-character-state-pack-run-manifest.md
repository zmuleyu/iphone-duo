---
title: STORM II Character State Pack Run Manifest
status: state-pack-r1-generated-pending-review
updated: 2026-09-20
scope: internal STORM II iPhone Duo character-composite screenshots
---

# STORM II character state-pack run manifest

## Authority and stop condition

- Fold Engine authority: existing `main_v44.js` at Git commit `33a20c5192cdb4619023c2ffa4ae68f38eb20f46`; no device, hinge, panel, camera, Screen UV, or frame-clock edits.
- Character authority: the six user-accepted PNG hashes below. They are local ignored inputs and must not be regenerated or committed.
- Art direction: translated anchor → delay → formation → one pulse → freeze grammar only. No copied reference-film shot, setting, costume, choreography, music, grading, or edit rhythm.
- Output intent: exact-frame internal state screenshots and aligned character masks; not a review video, delivery master, publication, deployment, or commercial use.
- Stop condition: build the state pack, prove protected clean-plate pixels are unchanged outside the character mask, then stop for one consolidated visual review before any numbered 348-frame capture or video encode.

## Run contract

```yaml
run_id: storm-fold-20260920-01
intent: character-state-pack
timeline: {fps: 60, frame_start: 0, frame_end_exclusive: 348}
resolution: [1920, 1080]
aspect_ratio: 16:9
sound_policy: silent
engine:
  repo: https://github.com/zmuleyu/iphone-duo
  commit: 33a20c5192cdb4619023c2ffa4ae68f38eb20f46
  build: 6.14
capture:
  browser: local Chrome headless through CDP
  device_pixel_ratio: 1
  route: exact frame index -> deterministic fold angle -> two render-boundary waits -> lossless PNG
character_composite:
  route: deterministic Pillow RGBA composite over captured Clean Plate
  protected_pixel_rule: composite must equal Clean Plate wherever the union character mask is zero
  character_order: [DARIO-MID-001, JENSEN-SUP-001, SAM-SUP-001, ELON]
target_platforms: []
rights_status: internal-only; real-person publication and commercial rights unresolved
```

## Accepted inputs

| ID | SHA-256 |
|---|---|
| `ELON-CAL-001` | `54E9BE808AD274FD307A0BA8CEB6C5AA169BAA54AE213BE53765296F60E45AE9` |
| `ELON-CAL-002` | `E2F2DABD745EFC915B19B1F993FFC7858C60372E8AEE307F7D058B96517E68EF` |
| `ELON-OPEN-001` | `E47FE2787492A5906E2E4C8DCC922C0AAC70E89D30609AFD822EBDF5D5715312` |
| `JENSEN-SUP-001` | `FD929B13B470D5227240CC4FB80244D277C6C22DA67FF2124D682DF7E506412A` |
| `SAM-SUP-001` | `9917B2587087603DFA6F5A8603C36B7109958F28B058404D56F83839E1112527` |
| `DARIO-MID-001` | `6D63530DD06D3F19B10F8694E2B6387815A757C49204A3AF2605081C851D1F8F` |

## Exact state matrix

| Frame | Phase | Purpose |
|---:|---|---|
| 0 | RUMOR | Closed endpoint and Elon anchor |
| 45 | PULL | Delayed-payoff start |
| 99 | FORMATION | First fold-motion frame |
| 119 | FORMATION | Approximately 25% reveal |
| 140 | FORMATION | Approximately 50% reveal |
| 160 | FORMATION | Approximately 75% reveal |
| 179 | FORMATION | Last pre-open frame |
| 180 | OPEN HOLD | Stable full-open endpoint before secondary motion |
| 207 | PULSE | Synchronized pulse start |
| 240 | PULSE | Single pulse peak |
| 273 | POSTER FREEZE | Hero tableau start |
| 317 | POSTER FREEZE | Hero tableau end |
| 347 | COMPRESSION | Final frame with no second climax |

Intervals are half-open and time is always `frameIndex / 60`. The fold is closed through frame 98, eases from 0° to 180° across frames 99–179, and is exactly open from frame 180 onward. Character motion is screen-space-only, deterministic, and subordinate to the Fold Engine.

## Output layout

Local ignored outputs live under `artifacts/storm-ii-character-state-pack/`:

- `characters/` — accepted immutable inputs;
- `state-pack/clean/` — exact engine screenshots;
- `state-pack/composite/` — character-composited review screenshots;
- `state-pack/character-mask/` — aligned union masks;
- `state-pack/motion-reference/` — non-delivery labels and placement guides;
- `state-pack-qc.json` — hashes, frame state, and protected-pixel comparison;
- `review/state-pack-contact-sheet-r1.jpg` — consolidated visual gate.

## State-pack r1 result

The exact-frame state pack was generated on 2026-09-20 with 13 states at 1920×1080. Every state has aligned Clean Plate, character composite, union character mask, and labelled motion-reference files. Local QC records:

- accepted character input hashes matched all six frozen values;
- engine runtime reported the locked v5.1 production baseline under build 6.14;
- every clean and composite image has identical 1920×1080 dimensions;
- every state used the declared fold angle derived from its frame index;
- every composite pixel outside the non-zero union character mask matched the Clean Plate exactly;
- no browser/runtime console error was recorded;
- the consolidated contact sheet and original-resolution checks cover RUMOR, PULL, formation 25/50/75%, pre-open, OPEN HOLD, pulse start/peak, poster freeze, and the final compression frame.

Mechanical status is `pass`; visual status is pending the required consolidated screenshot review. A video, 348-frame numbered sequence, and delivery encode remain prohibited until that review is accepted.
