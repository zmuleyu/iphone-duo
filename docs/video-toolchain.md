# iPhone Duo video toolchain

## Current Demo lane

The Tokyo abstract Demo is intentionally local, silent, and deterministic:

1. The existing 1920x1080/60 fps silent master remains the geometry and camera source.
2. OpenCV performs the right-to-left red/black/yellow poster transition without moving the tower or replacing the Reality composition.
3. FFmpeg encodes the final H.264 file and supplies metadata/QC probes.
4. `scripts/make_tokyo_demo.py` owns the 5.5-second montage timing. It adds no birds, title copy, or tower-specific highlight.

Run:

```powershell
python scripts\make_tokyo_demo.py <silent-master.mp4> <output.mp4>
```

## Source and overlap review (2026-09-20)

| Tool | Source/license | Local state | Decision |
| --- | --- | --- | --- |
| FFmpeg | Official legal page: LGPL 2.1+ by default; optional GPL parts change the effective build license. | Installed CLI, 8.1.1; local build enables GPL and libx264. | Use for local render, packaging, and QC. Do not redistribute the bundled executable as part of this project. |
| OpenCV | Official license page: Apache 2 for 4.5.0+. | Python `cv2` 4.13.0 installed. | Use for deterministic frame transforms and masks. |
| `media-studio/remotion-studio` | Remotion has a special two-tier license, not an unconditional OSI-style license for all organizations. | Strong CLI/render pipeline, but the local repository contains unrelated uncommitted tenant work. | Keep as the preferred future code-driven composition layer; do not write to or onboard this Demo into the dirty tool repository. |
| `media-studio/opencut` | Upstream repository is MIT and actively maintained. | Local branch is dirty; preview/export is under a Rust migration. | Keep for later interactive editing, not the reproducible Demo render path. |
| ImageMagick, MoviePy, Natron, MLT/Kdenlive | Open-source alternatives. | Not installed (MoviePy/Natron/MLT/ImageMagick). | Do not add: OpenCV + FFmpeg already cover this Demo and avoid duplicate transformation/render layers. |

Primary sources:

- https://ffmpeg.org/legal.html
- https://opencv.org/license/
- https://github.com/remotion-dev/remotion/blob/main/LICENSE.md
- https://github.com/OpenCut-app/OpenCut

## Global Skill decision

Do not create a global Skill yet. The stable reusable unit is currently the project-local script because its timing and color segmentation are tied to the iPhone Duo master. Re-evaluate promotion after the same workflow succeeds on at least two additional videos or another project and the input/output contract, timing schema, and QC checks stop changing. At that point a global Skill should orchestrate existing FFmpeg/OpenCV CLIs rather than duplicate their functionality.
