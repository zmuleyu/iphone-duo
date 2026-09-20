from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def _roi_px(roi: dict, w: int, h: int) -> tuple[int, int, int, int]:
    x0 = max(0, min(w - 1, int(round(roi["x0"] * w))))
    y0 = max(0, min(h - 1, int(round(roi["y0"] * h))))
    x1 = max(x0 + 1, min(w, int(round(roi["x1"] * w))))
    y1 = max(y0 + 1, min(h, int(round(roi["y1"] * h))))
    return x0, y0, x1, y1


def _warm_luminous_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    mx = rgb.max(axis=2).astype(np.float32)
    # Designed as a robust proxy for Tokyo Tower illumination across Reality A
    # and red/black/yellow candidates. It is intentionally not a semantic model.
    warm = (r > 112) & (g > 52) & (r > b * 1.14) & (g > b * 0.93) & (mx > 128)
    return warm.astype(np.uint8) * 255


def detect_anchor_mask(rgb: np.ndarray, lock: dict) -> tuple[np.ndarray, dict]:
    """Return a geometry-stable proxy mask for the configured anchor.

    The detector uses a warm-luminous seed inside the anchor ROI, then selects
    the connected component that best matches the configured anchor point and
    the expected tall/vertical geometry. This keeps the backend dependency-free
    while providing a repeatable mask/bbox/center for QC.
    """
    h, w = rgb.shape[:2]
    roi = lock["anchor_roi"]
    ap = lock.get("anchor_point", {"x": 0.5, "y": 0.5})
    x0, y0, x1, y1 = _roi_px(roi, w, h)
    cx, cy = int(round(ap["x"] * w)), int(round(ap["y"] * h))

    base = _warm_luminous_mask(rgb)
    # Narrow the search around the configured anchor X so warm windows do not
    # become the winning connected component.
    half_w = max(24, int(round(lock.get("anchor_search_half_width", 0.10) * w)))
    rx0, rx1 = max(x0, cx - half_w), min(x1, cx + half_w)
    scoped = np.zeros((h, w), dtype=np.uint8)
    scoped[y0:y1, rx0:rx1] = base[y0:y1, rx0:rx1]

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 9))
    merged = cv2.morphologyEx(scoped, cv2.MORPH_CLOSE, k, iterations=2)
    n, labels, stats, cents = cv2.connectedComponentsWithStats((merged > 0).astype(np.uint8), 8)

    best = None
    target = np.array([cx, cy], dtype=np.float32)
    norm = np.array([max(w, 1), max(h, 1)], dtype=np.float32)
    for i in range(1, n):
        x, y, ww, hh, area = [int(v) for v in stats[i]]
        if area < int(lock.get("anchor_min_component_area", 100)):
            continue
        centroid = np.asarray(cents[i], dtype=np.float32)
        dist = float(np.linalg.norm((centroid - target) / norm))
        verticality = hh / max(ww, 1)
        score = area * (1.0 + min(verticality, 4.0)) / (1.0 + 25.0 * dist)
        if best is None or score > best[0]:
            best = (score, i, (x, y, ww, hh, area), centroid)

    out = np.zeros((h, w), dtype=np.uint8)
    if best is None:
        return out, {
            "found": False,
            "bbox": None,
            "center": None,
            "area": 0,
            "detector": "warm_luminous_component",
        }

    _, idx, (x, y, ww, hh, area), centroid = best
    out[labels == idx] = 255
    out = cv2.morphologyEx(
        out,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=1,
    )
    ys, xs = np.where(out > 0)
    bx0, by0, bx1, by1 = int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
    center = [round(float(xs.mean()), 3), round(float(ys.mean()), 3)]
    return out, {
        "found": True,
        "bbox": [bx0, by0, bx1, by1],
        "center": center,
        "area": int((out > 0).sum()),
        "raw_component_area": int(area),
        "detector": "warm_luminous_component",
    }


def anchor_from_path(path: Path, lock: dict, mask_output: Path | None = None) -> dict:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    mask, meta = detect_anchor_mask(rgb, lock)
    if mask_output is not None:
        mask_output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask, "L").save(mask_output)
    return meta
