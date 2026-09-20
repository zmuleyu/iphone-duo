from __future__ import annotations

import numpy as np
import cv2


def evaluate_style(rgb: np.ndarray, skyline_mask: np.ndarray, tower_mask: np.ndarray, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    h, w = rgb.shape[:2]
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Stable upper-sky band, intentionally independent of skyline extraction.
    sky_y1 = int(round(cfg.get("sky_band_bottom", 0.24) * h))
    sky = np.zeros((h, w), dtype=bool)
    sky[: max(1, sky_y1), :] = True
    red = (r > 105) & (r > g * 1.35) & (r > b * 1.20)
    sky_redness = float(np.mean(red[sky])) if sky.any() else 0.0

    buildings = skyline_mask > 0
    darkness = float(np.mean(lum[buildings] < float(cfg.get("building_dark_luma", 55)))) if buildings.any() else 0.0

    tower = tower_mask > 0
    tower_warm = (r > 135) & (g > 65) & (r > b * 1.25)
    warm_ratio = float(np.mean(tower_warm[tower])) if tower.any() else 0.0
    tower_luma = float(np.mean(lum[tower])) if tower.any() else 0.0
    city_luma = float(np.mean(lum[buildings & ~tower])) if np.any(buildings & ~tower) else 0.0
    dominance = tower_luma / max(city_luma, 1.0)

    th = cfg.get("thresholds", {})
    checks = {
        "sky_redness_score": {
            "score": round(sky_redness, 4),
            "minimum": float(th.get("sky_redness_min", 0.55)),
        },
        "building_darkness_score": {
            "score": round(darkness, 4),
            "minimum": float(th.get("building_darkness_min", 0.65)),
        },
        "tower_warmth_score": {
            "score": round(warm_ratio, 4),
            "minimum": float(th.get("tower_warmth_min", 0.45)),
        },
        "tower_dominance_score": {
            "score": round(dominance, 4),
            "minimum": float(th.get("tower_dominance_min", 1.35)),
        },
    }
    for item in checks.values():
        item["pass"] = item["score"] >= item["minimum"]
    passed = all(item["pass"] for item in checks.values())
    return {
        "pass": passed,
        "hard_gate": bool(cfg.get("hard_gate", False)),
        "checks": checks,
        "policy": "Style QC is heuristic. By default it is advisory and does not override geometry hard-gates.",
    }
