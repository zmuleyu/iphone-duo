from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageDraw


def pixel_lock_check(source_path: Path, master_path: Path, extension: dict[str, int], diff_path: Path) -> dict:
    src = Image.open(source_path).convert("RGBA")
    master = Image.open(master_path).convert("RGBA")
    x, y = extension["left"], extension["top"]
    restored = master.crop((x, y, x + src.width, y + src.height))
    diff = ImageChops.difference(src, restored)
    arr = np.asarray(diff)
    changed = int(np.count_nonzero(np.any(arr != 0, axis=2)))
    max_channel_delta = int(arr.max()) if arr.size else 0
    # Make an easy-to-inspect red-on-black diff preview.
    changed_mask = np.any(arr != 0, axis=2).astype(np.uint8) * 255
    preview = Image.new("RGB", src.size, "black")
    if changed:
        red = np.zeros((src.height, src.width, 3), dtype=np.uint8)
        red[..., 0] = changed_mask
        preview = Image.fromarray(red, "RGB")
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(diff_path)
    return {"pass": changed == 0, "changed_pixels": changed, "max_channel_delta": max_channel_delta}


def seam_check(master_path: Path, extension: dict[str, int], preview_path: Path) -> dict:
    img = np.asarray(Image.open(master_path).convert("RGB"), dtype=np.float32)
    left = extension["left"]
    top = extension["top"]
    # v0.1 metric is implemented for the common left-only extension path.
    if left <= 0 or left >= img.shape[1] - 2:
        return {"pass": True, "score": 0.0, "ratio": 0.0, "note": "No left seam to inspect"}
    seam_delta = float(np.mean(np.abs(img[:, left - 1, :] - img[:, left, :])))
    local_delta = float(np.mean(np.abs(img[:, left, :] - img[:, left + 1, :])))
    ratio = seam_delta / max(local_delta, 1.0)
    passed = ratio <= 4.0 and seam_delta <= 60.0

    pil = Image.open(master_path).convert("RGB")
    x0 = max(0, left - 64)
    x1 = min(pil.width, left + 64)
    crop = pil.crop((x0, 0, x1, pil.height))
    draw = ImageDraw.Draw(crop)
    sx = left - x0
    draw.line([(sx, 0), (sx, crop.height)], fill=(255, 0, 0), width=2)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(preview_path)
    return {"pass": passed, "score": round(seam_delta, 3), "ratio": round(ratio, 3)}


def edge_map(image_path: Path, output_path: Path) -> None:
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    edges = cv2.Canny(img, 60, 160)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), edges)


def dimensions_check(path: Path, expected: tuple[int, int]) -> dict:
    size = Image.open(path).size
    return {"pass": size == expected, "actual": list(size), "expected": list(expected)}
