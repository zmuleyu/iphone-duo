# iPhone Duo Fold Engine

This repository is the production core for deterministic iPhone Duo folding, screen projection, screenshot review, and horizontal video capture.

## Current authority

- **Tokyo V6.28** is the accepted local video line. It uses a fixed camera, a 4.65-second closed-to-open-to-closed loop, no authored title by default, and separate horizontal masters for Xiaohongshu and X.
- **STORM II** is an internal experimental character-compositing line. The Fold Engine owns the device, hinge, panels, camera, Screen UV, fold timing, and occlusion. Character assets never redefine device geometry.
- **PixelLock** is the repository-local image geometry/QC tool under `tools/pixellock/`.
- Identifiable real-person assets remain local-only and cannot be published or monetized without explicit rights, non-endorsement, disclosure, territory, monetization, and legal review.

## Run locally

The application is static HTML, CSS, and JavaScript. Three.js is bundled locally.

The Apple reference assets are prepared separately and remain ignored by Git:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-assets.txt
python scripts\prepare-assets.py
python scripts\patch-shell-asset.py
python -m http.server 8766 --bind 127.0.0.1
```

Open `http://127.0.0.1:8766/`. Do not open `index.html` directly because the browser cannot load the model through `file://`.

## Production entry points

| Purpose | Query |
| --- | --- |
| Default Fold Engine | `/` |
| Tokyo V6.28 | `/?cap=1&tokyo=v628&nofx=1&motion=tokyo-final&format=16x9&title=0` |
| STORM II stage preset | `/?shot=storm-ii` |
| STORM II deterministic motion reference | `/?shot=storm-ii&timeline=motion-reference` |

Use screenshots and state packs as the approval gate. Generate video only after the required states have passed review.

## Source map

| Path | Purpose |
| --- | --- |
| `index.html` | Fold controls, production panels, and recording UI |
| `main_v44.js` | Fold Engine, Tokyo V6.28, STORM II camera/stage preset, deterministic frame APIs |
| `ui.js` | Default screen layouts |
| `style.css` | Desktop and mobile presentation |
| `media/tokyo/` | Current Tokyo source and runtime plates |
| `scripts/capture_tokyo_v628_loop_stills.py` | Screenshot-gated V6.28 review pack |
| `scripts/capture_tokyo_v628_platform_master.py` | Deterministic V6.28 numbered 4K frames |
| `tools/pixellock/` | Reusable geometry-lock and image-QC tool |
| `docs/followups.md` | Ordered future work and unresolved gates |

Local-only material is stored under ignored `local-archive/`, generated review evidence under ignored `artifacts/`, and final local exports under ignored `deliverables/`.

## Production documents

- [Tokyo V6.28 release receipt](docs/tokyo-v6.28-release.md)
- [Tokyo asset authority](docs/tokyo-assets.md)
- [Elon STORM II visual cast authority](docs/specs/2026-09-20-elon-storm-ii-visual-cast-authority.md)
- [Production followups](docs/followups.md)
- [Cleanup and archive record](docs/archive/2026-09-20-materials-cleanup.md)

## Deployment boundary

Source delivery and local exports do not authorize production deployment or publication. The Vercel project may be connected to this repository, so merging to `main` must be treated as a production-impacting action and requires explicit authorization for that deployment.

## License and sources

Application code is MIT licensed. See [third-party notices](THIRD_PARTY_NOTICES.md).

Apple models and imagery are excluded from the repository license. Local preparation scripts link to original sources, and any use remains subject to the source terms. Tokyo imagery provenance and limits are recorded in [docs/tokyo-assets.md](docs/tokyo-assets.md).
