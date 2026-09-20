from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def skyline_mask(rgb: np.ndarray, search_top: float = 0.15) -> np.ndarray:
    """Build a bottom-connected city silhouette proxy.

    Dark cloud components are rejected because only components connected to the
    bottom band are retained. The result is useful as a skyline/major-mass QC
    mask, not as semantic segmentation.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 2.0)
    h, w = gray.shape
    y0 = int(round(search_top * h))
    region = blur[y0:, :]
    _, inv = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mask = np.zeros_like(gray, dtype=np.uint8)
    mask[y0:, :] = inv
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (9, 15)),
        iterations=2,
    )
    _, labels, _, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    keep = np.zeros_like(mask, dtype=np.uint8)
    bottom_ids = set(np.unique(labels[-20:, :]).tolist()) - {0}
    for idx in bottom_ids:
        keep[labels == idx] = 255
    return keep


def skyline_from_path(path: Path, output: Path | None = None, search_top: float = 0.15) -> np.ndarray:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    mask = skyline_mask(rgb, search_top=search_top)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask, "L").save(output)
    return mask


def sky_region_from_skyline(skyline: np.ndarray, top_fraction: float = 0.02) -> np.ndarray:
    h, _ = skyline.shape
    sky = (skyline == 0).astype(np.uint8)
    # Ignore the extreme top border/padding noise.
    sky[: int(top_fraction * h), :] = 0
    return sky
