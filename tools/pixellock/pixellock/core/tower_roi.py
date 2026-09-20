from __future__ import annotations

from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .anchors import detect_anchor_mask
from .edge_compare import structural_edges, mask_iou


def _clip_roi(box: list[int], w: int, h: int, pad_x: int, pad_y: int) -> list[int]:
    x0, y0, x1, y1 = box
    return [
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(w, x1 + pad_x),
        min(h, y1 + pad_y),
    ]


def _mask_band(mask: np.ndarray, radius_px: int) -> np.ndarray:
    k = max(1, int(radius_px))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    return cv2.dilate((mask > 0).astype(np.uint8), kernel) > 0


def prepare_tower_roi_lock(rgb: np.ndarray, lock: dict) -> tuple[dict, dict[str, np.ndarray]]:
    """Build the immutable Tower ROI reference from Geometry Source A.

    The ROI is derived once from A and then reused verbatim for every B attempt.
    Candidate B is never allowed to redefine the lock region.
    """
    h, w = rgb.shape[:2]
    cfg = lock.get("tower_roi_lock", {})
    tower_mask, meta = detect_anchor_mask(rgb, lock)
    if not meta.get("found") or not meta.get("bbox"):
        return {
            "valid": False,
            "reason": "tower_not_detected_in_A",
            "roi_px": None,
            "reference_bbox": None,
            "reference_center": None,
        }, {
            "tower_mask": tower_mask,
            "tower_edge_template": np.zeros((h, w), dtype=np.uint8),
        }

    pad_x = int(cfg.get("padding_x_px", cfg.get("padding_px", 24)))
    pad_y = int(cfg.get("padding_y_px", cfg.get("padding_px", 24)))
    roi = _clip_roi(meta["bbox"], w, h, pad_x, pad_y)

    edges = structural_edges(rgb)
    band = _mask_band(tower_mask, int(cfg.get("edge_band_px", 8)))
    template = np.zeros_like(edges, dtype=np.uint8)
    template[(edges > 0) & band] = 255

    ref = {
        "valid": True,
        "roi_px": roi,
        "reference_bbox": list(meta["bbox"]),
        "reference_center": list(meta["center"]) if meta.get("center") else None,
        "reference_area": int(meta.get("area", 0)),
        "padding_px": {"x": pad_x, "y": pad_y},
        "edge_band_px": int(cfg.get("edge_band_px", 8)),
        "policy": "ROI is derived only from Geometry Source A and is immutable for all B candidates.",
    }
    return ref, {"tower_mask": tower_mask, "tower_edge_template": template}


def _shift_edge_recall(
    reference_edges: np.ndarray,
    candidate_edges: np.ndarray,
    roi: list[int],
    search_px: int,
    tolerance_px: int,
) -> dict:
    """Estimate fixed-ROI A→B translation from immutable A tower edges.

    Only sparse A edge coordinates are tested against a tolerance-dilated B
    edge map. The search window is intentionally small (default ±16 px), so
    this is both deterministic and fast while remaining insensitive to extra
    graphic/style edges added in B.
    """
    x0, y0, x1, y1 = roi
    ref = reference_edges[y0:y1, x0:x1] > 0
    ys, xs = np.where(ref)
    if len(xs) < 16:
        return {
            "dx": None,
            "dy": None,
            "distance_px": None,
            "score_at_lock": 0.0,
            "aligned_recall": 0.0,
            "search_clipped": False,
            "reference_edge_pixels": int(len(xs)),
        }

    cand = (candidate_edges[y0:y1, x0:x1] > 0).astype(np.uint8)
    tol = max(0, int(tolerance_px))
    if tol:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))
        cand = cv2.dilate(cand, k)
    cand = cand > 0
    hh, ww = cand.shape

    s = max(0, int(search_px))
    # Vectorized shift search (v0.2.3): identical semantics to the per-offset
    # loop — score(dx,dy) = hits / valid — but computed for the whole window in
    # O(1) correlations instead of (2s+1)^2 Python iterations.
    sparse = np.zeros((hh, ww), dtype=np.float32)
    sparse[ys, xs] = 1.0
    cand_pad = np.pad(cand.astype(np.float32), s, mode="constant")
    ones_pad = np.pad(np.ones((hh, ww), dtype=np.float32), s, mode="constant")
    hits_full = cv2.filter2D(cand_pad, -1, sparse, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    valid_full = cv2.filter2D(ones_pad, -1, sparse, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    hits = hits_full[: 2 * s + 1, : 2 * s + 1]
    valid = valid_full[: 2 * s + 1, : 2 * s + 1]
    scores = np.divide(hits, np.maximum(valid, 1.0))

    score0 = float(scores[s, s])
    best_score, best_dx, best_dy = -1.0, 0, 0
    offsets = sorted(
        ((dx, dy) for dy in range(-s, s + 1) for dx in range(-s, s + 1)),
        key=lambda d: (abs(d[0]) + abs(d[1]), d[0] * d[0] + d[1] * d[1]),
    )
    for dx, dy in offsets:
        current = float(scores[dy + s, dx + s])
        if current > best_score + 1e-9 or (
            abs(current - best_score) <= 1e-9
            and (abs(dx) + abs(dy), dx * dx + dy * dy)
            < (abs(best_dx) + abs(best_dy), best_dx * best_dx + best_dy * best_dy)
        ):
            best_score, best_dx, best_dy = current, dx, dy

    clipped = s > 0 and (abs(best_dx) == s or abs(best_dy) == s)
    return {
        "dx": int(best_dx),
        "dy": int(best_dy),
        "distance_px": round(float(math.hypot(best_dx, best_dy)), 3),
        "score_at_lock": round(score0, 4),
        "aligned_recall": round(float(max(best_score, 0.0)), 4),
        "search_clipped": bool(clipped),
        "reference_edge_pixels": int(len(xs)),
    }


def _roi_boolean(shape: tuple[int, int], roi: list[int]) -> np.ndarray:
    h, w = shape
    x0, y0, x1, y1 = roi
    out = np.zeros((h, w), dtype=bool)
    out[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = True
    return out


def _bbox_deltas(a: list[int] | None, b: list[int] | None) -> dict:
    if not a or not b:
        return {
            "available": False,
            "left_px": None,
            "top_px": None,
            "right_px": None,
            "bottom_px": None,
            "width_px": None,
            "height_px": None,
            "max_side_delta_px": None,
        }
    aw, ah = a[2] - a[0], a[3] - a[1]
    bw, bh = b[2] - b[0], b[3] - b[1]
    vals = {
        "available": True,
        "left_px": int(b[0] - a[0]),
        "top_px": int(b[1] - a[1]),
        "right_px": int(b[2] - a[2]),
        "bottom_px": int(b[3] - a[3]),
        "width_px": int(bw - aw),
        "height_px": int(bh - ah),
    }
    vals["max_side_delta_px"] = int(max(abs(vals[k]) for k in ("left_px", "top_px", "right_px", "bottom_px")))
    return vals


def evaluate_tower_roi_lock(
    a_rgb: np.ndarray,
    b_rgb: np.ndarray,
    lock: dict,
    reference: dict,
    reference_mask: np.ndarray | None = None,
    reference_edge_template: np.ndarray | None = None,
) -> dict:
    cfg = lock.get("tower_roi_lock", {})
    th = cfg.get("thresholds", {})
    if not reference.get("valid") or not reference.get("roi_px"):
        return {
            "pass": False,
            "position_pass": False,
            "shape_pass": False,
            "severity": "hard_fail",
            "failures": ["tower_roi_reference_invalid"],
            "policy": "Tower ROI Lock cannot run without a valid immutable reference from A.",
        }

    if a_rgb.shape[:2] != b_rgb.shape[:2]:
        return {
            "pass": False,
            "position_pass": False,
            "shape_pass": False,
            "severity": "hard_fail",
            "failures": ["dimensions_mismatch"],
            "policy": "Tower ROI Lock requires identical A/B dimensions.",
        }

    a_mask = reference_mask
    if a_mask is None:
        a_mask, _ = detect_anchor_mask(a_rgb, lock)
    b_mask, b_meta = detect_anchor_mask(b_rgb, lock)
    if reference_edge_template is None:
        a_edges = structural_edges(a_rgb)
        band = _mask_band(a_mask, int(reference.get("edge_band_px", cfg.get("edge_band_px", 8))))
        reference_edge_template = np.zeros_like(a_edges, dtype=np.uint8)
        reference_edge_template[(a_edges > 0) & band] = 255
    b_edges = structural_edges(b_rgb)

    roi = list(reference["roi_px"])
    registration = _shift_edge_recall(
        reference_edge_template,
        b_edges,
        roi,
        int(cfg.get("search_px", 16)),
        int(cfg.get("edge_tolerance_px", lock.get("edge_tolerance_px", 4))),
    )

    roi_bool = _roi_boolean(a_mask.shape, roi)
    a_roi_mask = np.where(roi_bool, a_mask, 0).astype(np.uint8)
    b_roi_mask = np.where(roi_bool, b_mask, 0).astype(np.uint8)
    roi_iou = mask_iou(a_roi_mask, b_roi_mask)
    bbox = _bbox_deltas(reference.get("reference_bbox"), b_meta.get("bbox"))

    ref_area = max(1, int(reference.get("reference_area", int((a_mask > 0).sum()))))
    cand_area = int(b_meta.get("area", 0))
    area_ratio_delta = abs(cand_area - ref_area) / ref_area if b_meta.get("found") else 1.0

    dx = registration.get("dx")
    dy = registration.get("dy")
    shift_limit = float(th.get("shift_px_max", 4.0))
    hard_limit = float(th.get("shift_px_hard_max", 8.0))
    shape_edge_min = float(th.get("aligned_edge_recall_min", 0.78))
    mask_iou_min = float(th.get("mask_iou_min", 0.72))
    bbox_delta_max = float(th.get("bbox_side_delta_px_max", 10.0))
    area_ratio_max = float(th.get("area_ratio_delta_max", 0.18))

    found_pass = bool(b_meta.get("found"))
    position_pass = (
        dx is not None
        and dy is not None
        and abs(dx) <= shift_limit
        and abs(dy) <= shift_limit
        and not registration.get("search_clipped", False)
    )
    edge_shape_pass = registration.get("aligned_recall", 0.0) >= shape_edge_min
    mask_shape_pass = roi_iou >= mask_iou_min
    bbox_shape_pass = bool(bbox.get("available")) and float(bbox.get("max_side_delta_px") or 0.0) <= bbox_delta_max
    area_shape_pass = area_ratio_delta <= area_ratio_max
    shape_pass = found_pass and edge_shape_pass and mask_shape_pass and bbox_shape_pass and area_shape_pass

    hard_shift = (
        dx is None
        or dy is None
        or abs(dx or 0) > hard_limit
        or abs(dy or 0) > hard_limit
        or registration.get("search_clipped", False)
    )

    failures: list[str] = []
    if not found_pass:
        failures.append("tower_not_detected_in_B")
    if not position_pass:
        failures.append("tower_roi_position")
    if not edge_shape_pass:
        failures.append("tower_roi_edge_shape")
    if not mask_shape_pass:
        failures.append("tower_roi_mask_shape")
    if not bbox_shape_pass:
        failures.append("tower_roi_bbox_shape")
    if not area_shape_pass:
        failures.append("tower_roi_area_shape")
    if registration.get("search_clipped"):
        failures.append("tower_roi_search_clipped")

    passed = bool(position_pass and shape_pass)
    severity = "pass" if passed else ("hard_fail" if hard_shift or not found_pass else "fail")
    return {
        "pass": passed,
        "position_pass": bool(position_pass),
        "shape_pass": bool(shape_pass),
        "severity": severity,
        "roi_px": roi,
        "reference_bbox": reference.get("reference_bbox"),
        "candidate_bbox": b_meta.get("bbox"),
        "candidate_found": found_pass,
        "translation": {
            **registration,
            "maximum_abs_dx_dy_px": shift_limit,
            "hard_maximum_abs_dx_dy_px": hard_limit,
        },
        "shape": {
            "aligned_edge_recall": {
                "pass": edge_shape_pass,
                "score": registration.get("aligned_recall", 0.0),
                "minimum": shape_edge_min,
            },
            "mask_iou": {"pass": mask_shape_pass, "score": roi_iou, "minimum": mask_iou_min},
            "bbox_delta": {"pass": bbox_shape_pass, **bbox, "maximum_side_delta_px": bbox_delta_max},
            "area_ratio_delta": {
                "pass": area_shape_pass,
                "score": round(float(area_ratio_delta), 4),
                "maximum": area_ratio_max,
            },
        },
        "failures": failures,
        "policy": "A-derived fixed Tower ROI is a hard gate. Position uses A-only tower-edge registration; shape uses aligned structural retention + locked-ROI mask/bbox checks.",
    }


def save_tower_roi_reference_artifacts(
    source_path: Path,
    reference: dict,
    tower_mask: np.ndarray,
    edge_template: np.ndarray,
    crop_path: Path,
    mask_path: Path,
    edges_path: Path,
) -> None:
    if not reference.get("valid"):
        return
    x0, y0, x1, y1 = reference["roi_px"]
    img = Image.open(source_path).convert("RGB")
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    img.crop((x0, y0, x1, y1)).save(crop_path)
    Image.fromarray(tower_mask[y0:y1, x0:x1].astype(np.uint8), "L").save(mask_path)
    Image.fromarray(edge_template[y0:y1, x0:x1].astype(np.uint8), "L").save(edges_path)


def save_tower_roi_overlay(
    source_path: Path,
    candidate_path: Path,
    qc: dict,
    output: Path,
) -> None:
    a = Image.open(source_path).convert("RGB")
    b = Image.open(candidate_path).convert("RGB")
    roi = qc.get("roi_px")
    if not roi:
        return
    x0, y0, x1, y1 = [int(v) for v in roi]
    ca = a.crop((x0, y0, x1, y1))
    cb = b.crop((x0, y0, x1, y1))
    gap = 10
    header = 34
    canvas = Image.new("RGB", (ca.width * 2 + gap, ca.height + header), (20, 20, 20))
    canvas.paste(ca, (0, header))
    canvas.paste(cb, (ca.width + gap, header))
    draw = ImageDraw.Draw(canvas)
    label = "PASS" if qc.get("pass") else f"FAIL · {qc.get('severity', 'fail')}"
    draw.text((8, 9), f"Tower ROI Lock — {label}", fill=(240, 240, 240))
    tr = qc.get("translation", {})
    draw.text((ca.width + gap + 8, 9), f"dx={tr.get('dx')} dy={tr.get('dy')} aligned={tr.get('aligned_recall')}", fill=(240, 240, 240))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
