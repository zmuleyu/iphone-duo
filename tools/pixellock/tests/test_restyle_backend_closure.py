from pathlib import Path
import shutil

import cv2
import numpy as np
from PIL import Image

from pixellock.core.project import ProjectStore
from pixellock.core.utils import sha256_file
from pixellock.workflows.restyle import (
    prepare_project,
    set_style_reference,
    generate_candidate,
    validate_candidate,
    repair,
)

ROOT = Path(__file__).resolve().parents[1]


def make_project(tmp_path: Path):
    store = ProjectStore(tmp_path / "projects", ROOT / "presets")
    state = store.create(
        ROOT / "examples" / "tokyo_reality_master_1544x1086.png",
        "tokyo_reality_master_1544x1086.png",
        "tokyo_ab_restyle",
        "restyle",
    )
    pdir, state = store.get(state["id"])
    return store, pdir, state


def test_prepare_emits_geometry_artifacts_and_preserves_A(tmp_path: Path):
    _, pdir, state = make_project(tmp_path)
    source = pdir / state["source"]["path"]
    before = sha256_file(source)
    state = prepare_project(pdir, state)
    after = sha256_file(source)
    assert before == after
    for key in ["edge_map_A", "tower_mask_A", "skyline_mask_A", "structure_overlay_A"]:
        assert key in state["artifacts"]
        assert (pdir / state["artifacts"][key]).exists()
    assert state["restyle"]["anchor_A"]["found"]


def test_style_reference_is_separate_and_local_candidate_passes(tmp_path: Path):
    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    source_hash = sha256_file(pdir / state["source"]["path"])
    state = set_style_reference(
        pdir,
        state,
        ROOT / "examples" / "tokyo_redblack_local_demo_1544x1086.png",
    )
    assert state["restyle"]["style_reference"] == "source/style_reference.png"
    assert sha256_file(pdir / state["source"]["path"]) == source_hash

    prompt = state["preset"]["prompt"]
    state = generate_candidate(pdir, state, "local_posterize", prompt, "local", "high")
    state = validate_candidate(pdir, state)
    assert state["qc"]["geometry_pass"]
    assert state["qc"]["pass"]
    checks = state["qc"]["hard_geometry_checks"]
    assert checks["tower_anchor_shift"]["distance_px"] <= 4.0
    assert checks["tower_mask_iou"]["pass"]
    assert checks["skyline_edge_overlap"]["pass"]
    assert len(state["restyle"]["attempts"]) == 1


def test_failed_geometry_enters_repair_and_keeps_attempt_history(tmp_path: Path):
    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    prompt = state["preset"]["prompt"]
    state = generate_candidate(pdir, state, "local_posterize", prompt, "local", "high")

    candidate_path = pdir / state["artifacts"]["candidate_target"]
    arr = np.asarray(Image.open(candidate_path).convert("RGB"))
    h, w = arr.shape[:2]
    shifted = cv2.warpAffine(
        arr,
        np.float32([[1, 0, 12], [0, 1, -7]]),
        (w, h),
        borderMode=cv2.BORDER_REPLICATE,
    )
    Image.fromarray(shifted, "RGB").save(candidate_path)

    state = validate_candidate(pdir, state)
    assert not state["qc"]["pass"]
    assert state["status"] == "qc_failed"
    first_failures = list(state["qc"]["failures"])
    assert first_failures

    state = repair(pdir, state, "local_posterize", prompt, "local", "high", max_attempts=3)
    assert state["qc"]["pass"]
    assert len(state["restyle"]["attempts"]) == 2
    assert state["restyle"]["attempts"][0]["qc"]["pass"] is False
    assert state["restyle"]["attempts"][1]["qc"]["pass"] is True


def test_tower_roi_lock_hard_fails_large_translation(tmp_path: Path):
    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    assert state["restyle"]["tower_roi_lock"]["valid"]
    for key in ["tower_roi_A", "tower_roi_mask_A", "tower_roi_edges_A"]:
        assert key in state["artifacts"]
        assert (pdir / state["artifacts"][key]).exists()

    prompt = state["preset"]["prompt"]
    state = generate_candidate(pdir, state, "local_posterize", prompt, "local", "high")
    candidate_path = pdir / state["artifacts"]["candidate_target"]
    arr = np.asarray(Image.open(candidate_path).convert("RGB"))
    h, w = arr.shape[:2]
    shifted = cv2.warpAffine(
        arr,
        np.float32([[1, 0, 12], [0, 1, -7]]),
        (w, h),
        borderMode=cv2.BORDER_REPLICATE,
    )
    Image.fromarray(shifted, "RGB").save(candidate_path)

    state = validate_candidate(pdir, state)
    roi = state["qc"]["tower_roi_lock"]
    assert not roi["pass"]
    assert not roi["position_pass"]
    assert roi["severity"] == "hard_fail"
    assert "tower_roi_lock" in state["qc"]["failures"]
    assert abs(roi["translation"]["dx"]) > 4 or abs(roi["translation"]["dy"]) > 4
    assert (pdir / state["artifacts"]["tower_roi_overlay"]).exists()


def test_closed_loop_auto_repairs_failed_tower_roi(tmp_path: Path, monkeypatch):
    import pixellock.workflows.restyle as rw

    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    prompt = state["preset"]["prompt"]
    original_generate = rw.local_posterize.generate
    calls = {"n": 0}

    def fail_once(source: Path, output: Path):
        calls["n"] += 1
        original_generate(source, output)
        if calls["n"] == 1:
            arr = np.asarray(Image.open(output).convert("RGB"))
            h, w = arr.shape[:2]
            shifted = cv2.warpAffine(
                arr,
                np.float32([[1, 0, 12], [0, 1, -7]]),
                (w, h),
                borderMode=cv2.BORDER_REPLICATE,
            )
            Image.fromarray(shifted, "RGB").save(output)

    monkeypatch.setattr(rw.local_posterize, "generate", fail_once)
    state = rw.run_closed_loop(pdir, state, "local_posterize", prompt, "local", "high", max_attempts=3)

    assert state["qc"]["pass"]
    assert state["qc"]["tower_roi_lock"]["pass"]
    assert len(state["restyle"]["attempts"]) == 2
    assert state["restyle"]["attempts"][0]["qc"]["tower_roi_lock"]["pass"] is False
    assert state["restyle"]["attempts"][1]["qc"]["tower_roi_lock"]["pass"] is True
    assert state["restyle"]["auto_repair"]["pass"] is True
    assert state["restyle"]["auto_repair"]["attempts_used"] == 2


def test_geometry_source_hash_prevents_reference_drift(tmp_path: Path):
    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    assert "source_sha256" in state["restyle"]["tower_roi_lock"]
    assert (pdir / state["artifacts"]["tower_edge_template_A"]).exists()

    source = pdir / state["source"]["path"]
    arr = np.asarray(Image.open(source).convert("RGB")).copy()
    arr[0, 0] = (arr[0, 0] + 1) % 255
    Image.fromarray(arr, "RGB").save(source)

    import pytest
    with pytest.raises(ValueError, match="Geometry Source A changed after Prepare"):
        generate_candidate(pdir, state, "local_posterize", state["preset"]["prompt"], "local", "high")


def _always_shifted_generate(original_generate):
    def generate(source: Path, output: Path):
        original_generate(source, output)
        arr = np.asarray(Image.open(output).convert("RGB"))
        h, w = arr.shape[:2]
        shifted = cv2.warpAffine(
            arr,
            np.float32([[1, 0, 12], [0, 1, -7]]),
            (w, h),
            borderMode=cv2.BORDER_REPLICATE,
        )
        Image.fromarray(shifted, "RGB").save(output)
    return generate


def test_closed_loop_respects_attempt_budget_when_all_fail(tmp_path: Path, monkeypatch):
    """v0.2.3 loop-control proof: a provider that never passes must stop at the
    attempt budget and land in repair_exhausted — no unbounded looping."""
    import pixellock.workflows.restyle as rw

    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    prompt = state["preset"]["prompt"]

    monkeypatch.setattr(rw.local_posterize, "generate", _always_shifted_generate(rw.local_posterize.generate))
    state = rw.run_closed_loop(pdir, state, "local_posterize", prompt, "local", "high", max_attempts=3)

    assert not state["qc"]["pass"]
    assert state["status"] == "repair_exhausted"
    assert len(state["restyle"]["attempts"]) == 3
    assert state["restyle"]["auto_repair"]["exhausted"] is True
    assert state["restyle"]["auto_repair"]["pass"] is False


def test_repair_stops_on_time_budget(tmp_path: Path, monkeypatch):
    """v0.2.3 time-control: with a zero wall-clock budget the repair loop must
    stop before spending another attempt, with a deterministic stop reason."""
    import pixellock.workflows.restyle as rw

    _, pdir, state = make_project(tmp_path)
    state = prepare_project(pdir, state)
    prompt = state["preset"]["prompt"]

    monkeypatch.setattr(rw.local_posterize, "generate", _always_shifted_generate(rw.local_posterize.generate))
    state = rw.run_closed_loop(
        pdir, state, "local_posterize", prompt, "local", "high",
        max_attempts=5, time_budget_s=0,
    )

    assert not state["qc"]["pass"]
    assert len(state["restyle"]["attempts"]) == 1  # no repair attempt was spent
    assert state["restyle"]["auto_repair"]["stop_reason"] == "time_budget"
    assert state["status"] == "repair_exhausted"
