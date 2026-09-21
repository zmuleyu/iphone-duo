"""Build the silent Tokyo abstract-transition demo from an existing master.

The demo intentionally contains no birds, added title copy, or separate tower
highlight pass.  It uses the existing device motion, adds a right-to-left
red/black/yellow poster transition, and keeps the back half alive with a small
montage and whole-device push-ins.

Usage:
  python scripts/make_tokyo_demo.py <silent-master.mp4> <output.mp4>
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np


FPS = 60
DURATION = 5.5


def source_time(output_time: float) -> float:
    """Map the 5.5s demo to the useful motion in the source master."""

    segments = (
        (0.00, 2.35, 0.00, 2.35),
        (2.35, 2.62, 1.02, 1.29),
        (2.62, 2.92, 1.30, 1.60),
        (2.92, 3.38, 1.66, 2.12),
        (3.38, 3.58, 1.16, 1.36),
        (3.58, 3.82, 1.38, 1.62),
        (3.82, 5.50, 2.12, 3.80),
    )
    for out_a, out_b, src_a, src_b in segments:
        if output_time <= out_b:
            mix = np.clip((output_time - out_a) / (out_b - out_a), 0.0, 1.0)
            return float(src_a + (src_b - src_a) * mix)
    return segments[-1][-1]


def whole_device_zoom(frame: np.ndarray, output_time: float) -> np.ndarray:
    """Use restrained whole-device push-ins; never isolate or glow the tower."""

    if output_time < 2.35:
        zoom = 1.0
    elif output_time < 2.62:
        zoom = 1.0 + 0.035 * ((output_time - 2.35) / 0.27)
    elif output_time < 2.92:
        zoom = 1.015 + 0.025 * ((output_time - 2.62) / 0.30)
    elif output_time < 3.82:
        zoom = 1.01 + 0.02 * ((output_time - 2.92) / 0.90)
    else:
        zoom = 1.0 + 0.032 * ((output_time - 3.82) / 1.68)

    if zoom <= 1.0001:
        return frame
    height, width = frame.shape[:2]
    crop_w = int(width / zoom) // 2 * 2
    crop_h = int(height / zoom) // 2 * 2
    x = (width - crop_w) // 2
    y = (height - crop_h) // 2
    return cv2.resize(frame[y : y + crop_h, x : x + crop_w], (width, height), interpolation=cv2.INTER_LANCZOS4)


def posterize(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert colored/dark image regions into a graphic red/black/yellow plate."""

    b, g, r = cv2.split(frame)
    b16, g16, r16 = b.astype(np.int16), g.astype(np.int16), r.astype(np.int16)
    luminance = (0.114 * b16 + 0.587 * g16 + 0.299 * r16).astype(np.uint8)
    maximum = np.maximum(np.maximum(b16, g16), r16)
    minimum = np.minimum(np.minimum(b16, g16), r16)
    chroma = maximum - minimum

    # White studio background and neutral metal stay untouched. Colored pixels
    # plus deep screen blacks form the stylized plate.
    active = (chroma > 18) | (luminance < 70)
    active &= ~((luminance > 205) & (chroma < 22))

    poster = frame.copy()
    # Dark neutral structure becomes black. Saturated red remains a red field;
    # only genuinely orange/yellow practical lights move to the yellow plate.
    dark = active & (luminance < 88) & ((chroma < 52) | (maximum < 78))
    warm = (
        active
        & (r16 > 145)
        & (g16 > 62)
        & (r16 > g16 * 1.04)
        & (r16 < g16 * 3.0)
        & (g16 > b16 * 1.35)
    )
    red_field = active & ~dark & ~warm

    poster[dark] = (3, 3, 5)
    poster[warm] = (0, 188, 255)
    red_level = np.clip(92 + luminance.astype(np.int16), 120, 228).astype(np.uint8)
    poster[red_field, 0] = 8
    poster[red_field, 1] = 8
    poster[red_field, 2] = red_level[red_field]

    edges = cv2.Canny(luminance, 72, 150)
    edge_mask = (edges > 0) & active & ~warm
    poster[edge_mask] = (0, 0, 0)
    return poster, active


def abstract_reveal(frame: np.ndarray, output_time: float) -> np.ndarray:
    if output_time < 0.68:
        return frame

    poster, active = posterize(frame)
    height, width = frame.shape[:2]
    x_grid = np.arange(width, dtype=np.float32)[None, :]

    progress = float(np.clip((output_time - 0.68) / 1.12, 0.0, 1.0))
    eased = progress * progress * (3.0 - 2.0 * progress)
    boundary = width * (0.92 - 0.84 * eased)
    feather = 34.0
    alpha_x = np.clip((x_grid - boundary + feather) / (2.0 * feather), 0.0, 1.0)
    if progress >= 1.0:
        alpha_x[:] = 1.0
    alpha = alpha_x[:, :, None] * active[:, :, None]
    result = (frame * (1.0 - alpha) + poster * alpha).astype(np.uint8)

    # A narrow yellow cutting edge makes the direction legible without adding
    # a tower-specific effect.
    if progress < 0.995:
        slash = (np.abs(x_grid - boundary) < 7.0) & active
        result[slash] = (0, 205, 255)
    return result


def write_abstract_reference(source_image: Path, output_image: Path) -> None:
    image = cv2.imread(str(source_image), cv2.IMREAD_COLOR)
    if image is None:
        return
    poster, active = posterize(image)
    result = image.copy()
    result[active] = poster[active]
    output_image.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_image), result):
        raise RuntimeError(f"Could not write {output_image}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: make_tokyo_demo.py <silent-master.mp4> <output.mp4>")

    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if not source.exists():
        raise SystemExit(f"source not found: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise SystemExit(f"cannot open: {source}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    source_fps = capture.get(cv2.CAP_PROP_FPS) or FPS

    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-movflags", "+faststart", str(output),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert encoder.stdin is not None

    frame_count = int(DURATION * FPS)
    try:
        for index in range(frame_count):
            output_time = index / FPS
            source_frame = int(round(source_time(output_time) * source_fps))
            capture.set(cv2.CAP_PROP_POS_FRAMES, source_frame)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"source frame unavailable at {source_time(output_time):.3f}s")
            frame = abstract_reveal(frame, output_time)
            frame = whole_device_zoom(frame, output_time)
            encoder.stdin.write(frame.tobytes())
    finally:
        capture.release()
        encoder.stdin.close()

    if encoder.wait() != 0:
        raise SystemExit("ffmpeg encoder failed")

    reference = Path(__file__).resolve().parents[1] / "media" / "tokyo" / "reality-wikipedia.png"
    write_abstract_reference(reference, output.with_name("tokyo-abstract-reference.png"))
    print(output)


if __name__ == "__main__":
    main()
