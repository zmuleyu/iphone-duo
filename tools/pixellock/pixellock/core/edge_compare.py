from __future__ import annotations

from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image


def structural_edges(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.5)
    return cv2.Canny(gray, 40, 110, L2gradient=True)


def roi_px(roi: dict, w: int, h: int) -> tuple[int, int, int, int]:
    return (
        max(0, min(w - 1, int(round(roi["x0"] * w)))),
        max(0, min(h - 1, int(round(roi["y0"] * h)))),
        max(1, min(w, int(round(roi["x1"] * w)))),
        max(1, min(h, int(round(roi["y1"] * h)))),
    )


def tolerant_edge_score(a: np.ndarray, b: np.ndarray, tolerance_px: int = 4) -> dict:
    aa, bb = a > 0, b > 0
    if not aa.any() and not bb.any():
        return {"recall": 1.0, "precision": 1.0, "f1": 1.0}
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tolerance_px + 1, 2 * tolerance_px + 1))
    ad = cv2.dilate(aa.astype(np.uint8), k) > 0
    bd = cv2.dilate(bb.astype(np.uint8), k) > 0
    recall = float(np.mean(bd[aa])) if aa.any() else 1.0
    precision = float(np.mean(ad[bb])) if bb.any() else 1.0
    f1 = 2.0 * recall * precision / max(recall + precision, 1e-9)
    return {"recall": round(recall, 4), "precision": round(precision, 4), "f1": round(f1, 4)}


def phase_shift(a: np.ndarray, b: np.ndarray, roi: dict) -> dict:
    h, w = a.shape
    x0, y0, x1, y1 = roi_px(roi, w, h)
    aa = a[y0:y1, x0:x1].astype(np.float32) / 255.0
    bb = b[y0:y1, x0:x1].astype(np.float32) / 255.0
    if aa.size == 0 or bb.size == 0 or aa.sum() < 1 or bb.sum() < 1:
        return {"dx": None, "dy": None, "distance_px": None, "response": 0.0}
    aa = cv2.GaussianBlur(aa, (0, 0), 2.0)
    bb = cv2.GaussianBlur(bb, (0, 0), 2.0)
    (dx, dy), response = cv2.phaseCorrelate(aa, bb)
    return {
        "dx": round(float(dx), 3),
        "dy": round(float(dy), 3),
        "distance_px": round(float(math.hypot(dx, dy)), 3),
        "response": round(float(response), 4),
    }


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    aa, bb = a > 0, b > 0
    union = int(np.logical_or(aa, bb).sum())
    if union == 0:
        return 1.0
    return round(float(np.logical_and(aa, bb).sum() / union), 4)


def bbox_iou(a: list[int] | None, b: list[int] | None) -> float:
    if not a or not b:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    area_a = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    area_b = max(0, bx1 - bx0) * max(0, by1 - by0)
    return round(inter / max(area_a + area_b - inter, 1), 4)


def save_edge_overlay(a: np.ndarray, b: np.ndarray, output: Path, tolerance_px: int = 4) -> None:
    aa, bb = a > 0, b > 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tolerance_px + 1, 2 * tolerance_px + 1))
    ad = cv2.dilate(aa.astype(np.uint8), k) > 0
    bd = cv2.dilate(bb.astype(np.uint8), k) > 0
    out = np.zeros((*aa.shape, 3), dtype=np.uint8)
    out[aa & bd] = (235, 235, 235)
    out[aa & ~bd] = (255, 70, 70)
    out[bb & ~ad] = (70, 190, 255)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGB").save(output)
