from __future__ import annotations

from pathlib import Path
import cv2
from PIL import Image


def generate(source_path: Path, output_path: Path, extension: dict[str, int]) -> None:
    """Free deterministic fallback.

    It uses OpenCV reflect padding. It is intended for smoke tests and very narrow
    extensions, not as a semantic replacement for GPT Image.
    """
    src = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if src is None:
        raise ValueError(f"Could not read {source_path}")
    out = cv2.copyMakeBorder(
        src,
        extension["top"],
        extension["bottom"],
        extension["left"],
        extension["right"],
        cv2.BORDER_REFLECT_101,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), out)
