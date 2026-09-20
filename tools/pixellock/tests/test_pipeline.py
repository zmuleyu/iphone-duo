from pathlib import Path
from PIL import Image
import numpy as np

from pixellock.core.geometry import prepare_target, prepare_api_input, lock_original, resize_final, crop_closed
from pixellock.core.qc import pixel_lock_check
from pixellock.providers.local_reflect import generate


def test_duo_pipeline(tmp_path: Path):
    # Create a deterministic synthetic 1448x1086 source.
    arr = np.zeros((1086, 1448, 4), dtype=np.uint8)
    arr[..., 0] = np.arange(1448, dtype=np.uint16)[None, :] % 256
    arr[..., 1] = np.arange(1086, dtype=np.uint16)[:, None] % 256
    arr[..., 2] = 120
    arr[..., 3] = 255
    src = tmp_path / "src.png"
    Image.fromarray(arr, "RGBA").save(src)
    ext = {"left": 96, "right": 0, "top": 0, "bottom": 0}
    target_path = tmp_path / "target.png"
    target = prepare_target(src, target_path, ext)
    assert target.size == (1544, 1086)
    api_input, mask = tmp_path / "api_input.png", tmp_path / "mask.png"
    api_size = prepare_api_input(target, api_input, mask, ext, 16)
    assert api_size == (1552, 1088)
    cand = tmp_path / "candidate.png"
    generate(src, cand, ext)
    locked = tmp_path / "locked.png"
    lock_original(cand, src, locked, ext)
    qc = pixel_lock_check(src, locked, ext, tmp_path / "diff.png")
    assert qc["pass"] and qc["changed_pixels"] == 0
    openp = tmp_path / "open.png"
    resize_final(locked, openp, (2670, 1878))
    closed = tmp_path / "closed.png"
    crop_closed(openp, closed, 1335, 1878, "right")
    assert Image.open(openp).size == (2670, 1878)
    assert Image.open(closed).size == (1335, 1878)
