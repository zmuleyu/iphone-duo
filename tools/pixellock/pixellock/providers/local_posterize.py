from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def generate(source_path: Path, output_path: Path) -> None:
    """Free deterministic A→B smoke-test provider.

    This deliberately changes color/rendering without warping geometry. It is
    not intended to replace a semantic model; it proves the restyle/QC/export
    chain offline.
    """
    rgb = np.asarray(Image.open(source_path).convert("RGB"), dtype=np.uint8)
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    out = np.zeros_like(rgb)
    # Slight vertical red gradient to avoid a dead-flat debug image.
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    out[..., 0] = np.clip(125 + 30 * yy, 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(5 + 5 * yy, 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(12 + 4 * yy, 0, 255).astype(np.uint8)

    ygrid = np.arange(h, dtype=np.float32)[:, None]
    # Dark structures, with a y-dependent threshold to keep the upper sky red.
    threshold = 96 + (ygrid / max(h, 1)) * 30
    city = (gray < threshold) & (ygrid > h * 0.21)
    city |= ygrid > h * 0.72
    out[city] = (4, 4, 5)

    r, g, b = (rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16))
    warm = ((r > g * 1.10) & (g > b * 1.12) & (r > 125)) | ((r > 180) & (g > 105) & (b < 105))
    out[warm] = (244, 160, 34)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGB").save(output_path, format="PNG")
