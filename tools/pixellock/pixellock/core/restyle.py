from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .utils import round_up


def prepare_restyle_input(
    source_path: Path,
    input_path: Path,
    mask_path: Path,
    multiple: int = 16,
) -> tuple[int, int]:
    """Pad A to an API-friendly canvas without resizing it.

    The source region is fully editable. Padding is protected so a crop-back is
    deterministic and never depends on generated padding pixels.
    """
    src = Image.open(source_path).convert("RGBA")
    api_w, api_h = round_up(src.width, multiple), round_up(src.height, multiple)
    canvas = Image.new("RGBA", (api_w, api_h), (0, 0, 0, 0))
    canvas.paste(src, (0, 0))

    # Image-edit mask convention used by this project: alpha=0 editable.
    mask = Image.new("RGBA", (api_w, api_h), (255, 255, 255, 255))
    editable = Image.new("RGBA", src.size, (255, 255, 255, 0))
    mask.paste(editable, (0, 0))

    input_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(input_path)
    mask.save(mask_path)
    return api_w, api_h


def crop_restyle_candidate(api_candidate_path: Path, source_size: tuple[int, int], output_path: Path) -> Image.Image:
    img = Image.open(api_candidate_path).convert("RGBA")
    out = img.crop((0, 0, source_size[0], source_size[1]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    return out


def _structural_edges_array(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.5)
    return cv2.Canny(gray, 40, 110, L2gradient=True)


def make_geometry_guide(source_path: Path, edges_path: Path, guide_path: Path, lock: dict) -> None:
    rgb = np.asarray(Image.open(source_path).convert("RGB"))
    edges = _structural_edges_array(rgb)
    edges_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(edges, "L").save(edges_path)

    h, w = edges.shape
    # Dark guide + white Canny geometry, with critical regions called out.
    base = np.zeros((h, w, 3), dtype=np.uint8)
    base[edges > 0] = (240, 240, 240)
    guide = Image.fromarray(base, "RGB")
    draw = ImageDraw.Draw(guide)

    def box(roi: dict, color: tuple[int, int, int], width: int = 3):
        x0, y0 = int(roi["x0"] * w), int(roi["y0"] * h)
        x1, y1 = int(roi["x1"] * w), int(roi["y1"] * h)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=width)

    box(lock["building_roi"], (64, 170, 255), 2)
    box(lock["anchor_roi"], (255, 192, 48), 3)
    ap = lock.get("anchor_point", {"x": 0.5, "y": 0.5})
    ax, ay = int(ap["x"] * w), int(ap["y"] * h)
    r = 14
    draw.line((ax-r, ay, ax+r, ay), fill=(255, 80, 80), width=3)
    draw.line((ax, ay-r, ax, ay+r), fill=(255, 80, 80), width=3)
    guide.save(guide_path)
