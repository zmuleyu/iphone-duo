from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from pixellock.core.geometry_qc import geometry_lock_check
from pixellock.core.restyle import prepare_restyle_input, crop_restyle_candidate
from pixellock.core.utils import read_json
from pixellock.providers.local_posterize import generate

ROOT = Path(__file__).resolve().parents[1]


def test_geometry_locked_restyle_pass(tmp_path: Path):
    src = ROOT / "examples" / "tokyo_reality_master_1544x1086.png"
    preset = read_json(ROOT / "presets" / "tokyo_ab_restyle.json")

    api_input = tmp_path / "api_input.png"
    api_mask = tmp_path / "api_mask.png"
    api_size = prepare_restyle_input(src, api_input, api_mask, preset["api_multiple"])
    assert api_size == (1552, 1088)

    candidate = tmp_path / "candidate.png"
    generate(src, candidate)
    qc = geometry_lock_check(
        src,
        candidate,
        preset["geometry_lock"],
        tmp_path / "overlay.png",
        tmp_path / "anchor.png",
    )
    assert qc["pass"]
    assert qc["anchor"]["f1"] >= preset["geometry_lock"]["thresholds"]["anchor_edge_f1_min"]
    assert qc["building_contours"]["f1"] >= preset["geometry_lock"]["thresholds"]["building_edge_f1_min"]


def test_shifted_restyle_fails_geometry_gate(tmp_path: Path):
    src = ROOT / "examples" / "tokyo_reality_master_1544x1086.png"
    preset = read_json(ROOT / "presets" / "tokyo_ab_restyle.json")
    candidate = tmp_path / "candidate.png"
    generate(src, candidate)

    arr = np.asarray(Image.open(candidate).convert("RGB"))
    h, w = arr.shape[:2]
    matrix = np.float32([[1, 0, 12], [0, 1, -7]])
    shifted = cv2.warpAffine(arr, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
    shifted_path = tmp_path / "shifted.png"
    Image.fromarray(shifted, "RGB").save(shifted_path)

    qc = geometry_lock_check(
        src,
        shifted_path,
        preset["geometry_lock"],
        tmp_path / "overlay_shifted.png",
        tmp_path / "anchor_shifted.png",
    )
    assert not qc["pass"]
    assert not (qc["anchor"]["pass"] and qc["building_contours"]["pass"] and qc["anchor_shift"]["pass"])


def test_crop_restyle_candidate(tmp_path: Path):
    img = Image.new("RGBA", (1552, 1088), (10, 20, 30, 255))
    src = tmp_path / "api.png"
    out = tmp_path / "target.png"
    img.save(src)
    crop_restyle_candidate(src, (1544, 1086), out)
    assert Image.open(out).size == (1544, 1086)
