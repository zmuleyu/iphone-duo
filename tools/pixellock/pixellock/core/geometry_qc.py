from __future__ import annotations

from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw


def _rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def structural_edges(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.5)
    return cv2.Canny(gray, 40, 110, L2gradient=True)


def _roi_px(roi: dict, w: int, h: int) -> tuple[int, int, int, int]:
    x0 = max(0, min(w - 1, int(round(roi["x0"] * w))))
    y0 = max(0, min(h - 1, int(round(roi["y0"] * h))))
    x1 = max(x0 + 1, min(w, int(round(roi["x1"] * w))))
    y1 = max(y0 + 1, min(h, int(round(roi["y1"] * h))))
    return x0, y0, x1, y1


def tolerant_edge_score(a: np.ndarray, b: np.ndarray, tolerance_px: int = 5) -> dict:
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


def anchor_shift(source_edges: np.ndarray, candidate_edges: np.ndarray, roi: dict) -> dict:
    h, w = source_edges.shape
    x0, y0, x1, y1 = _roi_px(roi, w, h)
    a = source_edges[y0:y1, x0:x1].astype(np.float32) / 255.0
    b = candidate_edges[y0:y1, x0:x1].astype(np.float32) / 255.0
    if a.size == 0 or b.size == 0 or float(a.sum()) < 1 or float(b.sum()) < 1:
        return {"dx": None, "dy": None, "distance_px": None, "response": 0.0}
    a = cv2.GaussianBlur(a, (0, 0), 2.0)
    b = cv2.GaussianBlur(b, (0, 0), 2.0)
    (dx, dy), response = cv2.phaseCorrelate(a, b)
    distance = math.hypot(dx, dy)
    return {
        "dx": round(float(dx), 3),
        "dy": round(float(dy), 3),
        "distance_px": round(float(distance), 3),
        "response": round(float(response), 4),
    }


def _save_overlay(source_edges: np.ndarray, candidate_edges: np.ndarray, output_path: Path, tolerance_px: int) -> None:
    aa, bb = source_edges > 0, candidate_edges > 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tolerance_px + 1, 2 * tolerance_px + 1))
    ad = cv2.dilate(aa.astype(np.uint8), k) > 0
    bd = cv2.dilate(bb.astype(np.uint8), k) > 0
    matched_a = aa & bd
    unmatched_a = aa & ~bd
    unmatched_b = bb & ~ad
    out = np.zeros((*aa.shape, 3), dtype=np.uint8)
    out[matched_a] = (235, 235, 235)      # shared geometry
    out[unmatched_a] = (255, 70, 70)      # A-only
    out[unmatched_b] = (70, 190, 255)     # B-only
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGB").save(output_path)


def _save_anchor_preview(source_path: Path, candidate_path: Path, roi: dict, output_path: Path) -> None:
    a = Image.open(source_path).convert("RGB")
    b = Image.open(candidate_path).convert("RGB")
    x0, y0, x1, y1 = _roi_px(roi, a.width, a.height)
    ca, cb = a.crop((x0, y0, x1, y1)), b.crop((x0, y0, x1, y1))
    gap = 8
    canvas = Image.new("RGB", (ca.width * 2 + gap, ca.height), "black")
    canvas.paste(ca, (0, 0)); canvas.paste(cb, (ca.width + gap, 0))
    draw = ImageDraw.Draw(canvas)
    draw.line((ca.width + gap // 2, 0, ca.width + gap // 2, ca.height), fill=(255, 255, 255), width=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def geometry_lock_check(
    source_path: Path,
    candidate_path: Path,
    lock: dict,
    overlay_path: Path,
    anchor_preview_path: Path,
    source_edges_path: Path | None = None,
    candidate_edges_path: Path | None = None,
) -> dict:
    a = _rgb(source_path)
    b = _rgb(candidate_path)
    if a.shape[:2] != b.shape[:2]:
        return {
            "pass": False,
            "dimensions": {"pass": False, "source": [a.shape[1], a.shape[0]], "candidate": [b.shape[1], b.shape[0]]},
            "reason": "A and B dimensions differ",
        }

    ae, be = structural_edges(a), structural_edges(b)
    if source_edges_path:
        source_edges_path.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(ae, "L").save(source_edges_path)
    if candidate_edges_path:
        candidate_edges_path.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(be, "L").save(candidate_edges_path)

    h, w = ae.shape
    tol = int(lock.get("edge_tolerance_px", 5))
    ar = _roi_px(lock["anchor_roi"], w, h)
    br = _roi_px(lock["building_roi"], w, h)
    anchor = tolerant_edge_score(ae[ar[1]:ar[3], ar[0]:ar[2]], be[ar[1]:ar[3], ar[0]:ar[2]], tol)
    building = tolerant_edge_score(ae[br[1]:br[3], br[0]:br[2]], be[br[1]:br[3], br[0]:br[2]], tol)
    shift = anchor_shift(ae, be, lock["anchor_roi"])
    th = lock["thresholds"]

    anchor_pass = anchor["f1"] >= float(th["anchor_edge_f1_min"])
    building_pass = building["f1"] >= float(th["building_edge_f1_min"])
    shift_pass = shift["distance_px"] is not None and shift["distance_px"] <= float(th["anchor_shift_px_max"])

    _save_overlay(ae, be, overlay_path, tol)
    _save_anchor_preview(source_path, candidate_path, lock["anchor_roi"], anchor_preview_path)

    return {
        "pass": bool(anchor_pass and building_pass and shift_pass),
        "dimensions": {"pass": True, "source": [w, h], "candidate": [w, h]},
        "anchor": {
            "name": lock.get("anchor_name", "anchor"),
            "pass": anchor_pass,
            **anchor,
            "minimum_f1": float(th["anchor_edge_f1_min"]),
        },
        "building_contours": {
            "pass": building_pass,
            **building,
            "minimum_f1": float(th["building_edge_f1_min"]),
        },
        "anchor_shift": {
            "pass": shift_pass,
            **shift,
            "maximum_px": float(th["anchor_shift_px_max"]),
        },
        "edge_tolerance_px": tol,
        "policy": "FAIL if Tokyo Tower anchor similarity, building contour similarity, or anchor shift exceeds the preset threshold.",
    }
