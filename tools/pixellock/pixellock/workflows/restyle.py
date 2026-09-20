from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
import shutil
import numpy as np
from PIL import Image, ImageDraw

from ..core.anchors import detect_anchor_mask
from ..core.masks import skyline_mask
from ..core.edge_compare import structural_edges, tolerant_edge_score, phase_shift, mask_iou, bbox_iou, roi_px, save_edge_overlay
from ..core.style_qc import evaluate_style
from ..core.tower_roi import (
    prepare_tower_roi_lock,
    evaluate_tower_roi_lock,
    save_tower_roi_reference_artifacts,
    save_tower_roi_overlay,
)
from ..core.restyle import prepare_restyle_input, crop_restyle_candidate
from ..core.utils import write_json, sha256_file
from ..providers import local_posterize, openai_image, openrouter_image

# v0.2.3: wall-clock guard for the repair loop. Weak/offline environments must
# fail fast with a deterministic state instead of running unbounded.
DEFAULT_TIME_BUDGET_S = float(os.getenv("PIXELLOCK_TIME_BUDGET_S", "300"))


def _rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def _save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8), "L").save(path)


def _structure_overlay(source_path: Path, tower_meta: dict, lock: dict, output: Path) -> None:
    img = Image.open(source_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    if tower_meta.get("bbox"):
        draw.rectangle(tuple(tower_meta["bbox"]), outline=(255, 205, 32), width=3)
    ap = lock.get("anchor_point", {"x": 0.5, "y": 0.5})
    ax, ay = int(ap["x"] * w), int(ap["y"] * h)
    draw.line((ax - 12, ay, ax + 12, ay), fill=(255, 50, 50), width=2)
    draw.line((ax, ay - 12, ax, ay + 12), fill=(255, 50, 50), width=2)
    br = lock["building_roi"]
    x0, y0, x1, y1 = roi_px(br, w, h)
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(80, 180, 255), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output)


def prepare_project(pdir: Path, state: dict) -> dict:
    preset = state["preset"]
    source = pdir / state["source"]["path"]
    lock = preset["geometry_lock"]
    api_input = pdir / "working" / "restyle_api_input.png"
    api_mask = pdir / "working" / "restyle_api_mask.png"
    api_size = prepare_restyle_input(source, api_input, api_mask, preset.get("api_multiple", 16))

    rgb = _rgb(source)
    edges = structural_edges(rgb)
    tower_mask, tower_meta = detect_anchor_mask(rgb, lock)
    tower_roi_ref, tower_roi_arrays = prepare_tower_roi_lock(rgb, lock)
    if not tower_roi_ref.get("valid"):
        raise ValueError("Tower ROI Lock could not detect the anchor in Geometry Source A")
    sky_mask = skyline_mask(rgb, search_top=float(lock.get("skyline_search_top", 0.15)))

    edge_path = pdir / "qc" / "edge_map_A.png"
    tower_path = pdir / "qc" / "tower_mask_A.png"
    skyline_path = pdir / "qc" / "skyline_mask_A.png"
    overlay_path = pdir / "qc" / "structure_overlay_A.png"
    tower_roi_crop_path = pdir / "qc" / "tower_roi_A.png"
    tower_roi_mask_path = pdir / "qc" / "tower_roi_mask_A.png"
    tower_roi_edges_path = pdir / "qc" / "tower_roi_edges_A.png"
    tower_edge_template_path = pdir / "qc" / "tower_edge_template_A.png"
    _save_mask(edges, edge_path)
    _save_mask(tower_mask, tower_path)
    _save_mask(sky_mask, skyline_path)
    _structure_overlay(source, tower_meta, lock, overlay_path)
    save_tower_roi_reference_artifacts(
        source, tower_roi_ref, tower_roi_arrays["tower_mask"], tower_roi_arrays["tower_edge_template"],
        tower_roi_crop_path, tower_roi_mask_path, tower_roi_edges_path,
    )
    _save_mask(tower_roi_arrays["tower_edge_template"], tower_edge_template_path)
    tower_roi_ref["source_sha256"] = sha256_file(source)
    tower_roi_ref["mask_sha256"] = sha256_file(tower_path)
    tower_roi_ref["edge_template_sha256"] = sha256_file(tower_edge_template_path)

    state.setdefault("restyle", {})
    state["restyle"].update({
        "phase": "prepared",
        "geometry_source": state["source"]["path"],
        "style_reference": state["restyle"].get("style_reference"),
        "anchor_A": tower_meta,
        "tower_roi_lock": tower_roi_ref,
        "attempts": state["restyle"].get("attempts", []),
        "active_attempt": state["restyle"].get("active_attempt"),
        "max_attempts": int(preset.get("repair", {}).get("max_attempts", 3)),
    })
    state["api_working_size"] = {"width": api_size[0], "height": api_size[1]}
    state["artifacts"].update({
        "api_input": "working/restyle_api_input.png",
        "api_mask": "working/restyle_api_mask.png",
        "edge_map_A": "qc/edge_map_A.png",
        "tower_mask_A": "qc/tower_mask_A.png",
        "skyline_mask_A": "qc/skyline_mask_A.png",
        "structure_overlay_A": "qc/structure_overlay_A.png",
        "geometry_guide": "qc/structure_overlay_A.png",
        "tower_roi_A": "qc/tower_roi_A.png",
        "tower_roi_mask_A": "qc/tower_roi_mask_A.png",
        "tower_roi_edges_A": "qc/tower_roi_edges_A.png",
        "tower_edge_template_A": "qc/tower_edge_template_A.png",
    })
    state["status"] = "prepared"
    state["qc"] = None
    return state


def set_style_reference(pdir: Path, state: dict, upload_path: Path) -> dict:
    out = pdir / "source" / "style_reference.png"
    Image.open(upload_path).convert("RGB").save(out)
    state.setdefault("restyle", {})["style_reference"] = "source/style_reference.png"
    state["artifacts"]["style_reference"] = "source/style_reference.png"
    return state


def _attempt_number(state: dict) -> int:
    return len(state.setdefault("restyle", {}).setdefault("attempts", [])) + 1


def _assert_geometry_source_integrity(pdir: Path, state: dict) -> None:
    ref = state.get("restyle", {}).get("tower_roi_lock") or {}
    expected = ref.get("source_sha256")
    if not expected:
        return
    source = pdir / state["source"]["path"]
    actual = sha256_file(source)
    if actual != expected:
        raise ValueError(
            "Geometry Source A changed after Prepare. Tower ROI Lock is invalid; restore A or run Prepare again before generating/repairing."
        )


def generate_candidate(
    pdir: Path,
    state: dict,
    provider: str,
    prompt: str,
    model: str,
    quality: str,
) -> dict:
    if state.get("status") not in {"prepared", "generated", "validated", "qc_failed", "repair_exhausted", "exported"}:
        raise ValueError("Prepare the restyle project first")
    _assert_geometry_source_integrity(pdir, state)
    attempt = _attempt_number(state)
    api_path = pdir / "generated" / f"B_candidate_{attempt:02d}_api.png"
    target_path = pdir / "generated" / f"B_candidate_{attempt:02d}.png"
    source = pdir / state["source"]["path"]

    if provider == "local_posterize":
        local_posterize.generate(source, target_path)
        Image.open(target_path).save(api_path)
        meta = {"provider": provider, "note": "Deterministic geometry-preserving backend smoke test"}
    elif provider == "openrouter":
        size = state["api_working_size"]
        style_ref_rel = state.get("restyle", {}).get("style_reference")
        style_ref = pdir / style_ref_rel if style_ref_rel else None
        meta = openrouter_image.generate(
            pdir / state["artifacts"]["api_input"],
            pdir / state["artifacts"]["api_mask"],
            api_path,
            prompt=prompt,
            model=model,
            quality=quality,
            size=f'{size["width"]}x{size["height"]}',
            style_reference_path=style_ref,
            api_size=(size["width"], size["height"]),
        )
        crop_restyle_candidate(api_path, (state["source"]["width"], state["source"]["height"]), target_path)
        meta = {"provider": provider, **meta}
    elif provider == "openai":
        size = state["api_working_size"]
        style_ref_rel = state.get("restyle", {}).get("style_reference")
        style_ref = pdir / style_ref_rel if style_ref_rel else None
        meta = openai_image.generate(
            pdir / state["artifacts"]["api_input"],
            pdir / state["artifacts"]["api_mask"],
            api_path,
            prompt=prompt,
            model=model,
            quality=quality,
            size=f'{size["width"]}x{size["height"]}',
            style_reference_path=style_ref,
        )
        crop_restyle_candidate(api_path, (state["source"]["width"], state["source"]["height"]), target_path)
        meta = {"provider": provider, **meta}
    else:
        raise ValueError("Restyle workflow supports local_posterize, openrouter or openai")

    record = {
        "attempt": attempt,
        "prompt": prompt,
        "provider": provider,
        "model": model,
        "quality": quality,
        "candidate": str(target_path.relative_to(pdir)).replace("\\", "/"),
        "candidate_api": str(api_path.relative_to(pdir)).replace("\\", "/"),
        "generation": meta,
        "qc": None,
    }
    state["restyle"]["attempts"].append(record)
    state["restyle"]["active_attempt"] = attempt
    state["generation"] = {**meta, "prompt": prompt, "attempt": attempt}
    state["artifacts"].update({
        "candidate_api": record["candidate_api"],
        "candidate_target": record["candidate"],
    })
    state["status"] = "generated"
    state["qc"] = None
    return state


def _save_anchor_preview(source_path: Path, candidate_path: Path, roi: dict, output: Path) -> None:
    a = Image.open(source_path).convert("RGB")
    b = Image.open(candidate_path).convert("RGB")
    x0, y0, x1, y1 = roi_px(roi, a.width, a.height)
    ca, cb = a.crop((x0, y0, x1, y1)), b.crop((x0, y0, x1, y1))
    gap = 8
    canvas = Image.new("RGB", (ca.width * 2 + gap, ca.height), "black")
    canvas.paste(ca, (0, 0))
    canvas.paste(cb, (ca.width + gap, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def validate_candidate(pdir: Path, state: dict) -> dict:
    if "candidate_target" not in state.get("artifacts", {}):
        raise ValueError("Generate a B candidate first")
    preset = state["preset"]
    lock = preset["geometry_lock"]
    th = lock["thresholds"]
    source_path = pdir / state["source"]["path"]
    candidate_path = pdir / state["artifacts"]["candidate_target"]
    _assert_geometry_source_integrity(pdir, state)
    a = _rgb(source_path)
    b = _rgb(candidate_path)

    dims_pass = a.shape[:2] == b.shape[:2]
    if not dims_pass:
        qc = {
            "pass": False,
            "geometry_pass": False,
            "style_pass": False,
            "dimensions_check": {"pass": False, "A": [a.shape[1], a.shape[0]], "B": [b.shape[1], b.shape[0]]},
            "failures": ["dimensions_check"],
        }
        return _store_qc(pdir, state, qc)

    ae, be = structural_edges(a), structural_edges(b)
    tol = int(lock.get("edge_tolerance_px", 4))
    h, w = ae.shape
    ar = roi_px(lock["anchor_roi"], w, h)
    br = roi_px(lock["building_roi"], w, h)
    anchor_edges = tolerant_edge_score(ae[ar[1]:ar[3], ar[0]:ar[2]], be[ar[1]:ar[3], ar[0]:ar[2]], tol)
    skyline_edges = tolerant_edge_score(ae[br[1]:br[3], br[0]:br[2]], be[br[1]:br[3], br[0]:br[2]], tol)
    shift = phase_shift(ae, be, lock["anchor_roi"])

    a_tower, a_tower_meta = detect_anchor_mask(a, lock)
    b_tower, b_tower_meta = detect_anchor_mask(b, lock)
    t_iou = mask_iou(a_tower, b_tower)
    t_bbox_iou = bbox_iou(a_tower_meta.get("bbox"), b_tower_meta.get("bbox"))
    a_skyline = skyline_mask(a, search_top=float(lock.get("skyline_search_top", 0.15)))
    b_skyline = skyline_mask(b, search_top=float(lock.get("skyline_search_top", 0.15)))
    s_iou = mask_iou(a_skyline, b_skyline)

    tower_roi_ref = state.get("restyle", {}).get("tower_roi_lock") or {}
    frozen_mask_path = state.get("artifacts", {}).get("tower_mask_A")
    frozen_edge_path = state.get("artifacts", {}).get("tower_edge_template_A")
    frozen_mask = (
        np.asarray(Image.open(pdir / frozen_mask_path).convert("L"), dtype=np.uint8)
        if frozen_mask_path and (pdir / frozen_mask_path).exists() else a_tower
    )
    frozen_edges = (
        np.asarray(Image.open(pdir / frozen_edge_path).convert("L"), dtype=np.uint8)
        if frozen_edge_path and (pdir / frozen_edge_path).exists() else None
    )
    tower_roi_qc = evaluate_tower_roi_lock(
        a, b, lock, tower_roi_ref, reference_mask=frozen_mask, reference_edge_template=frozen_edges,
    )

    center_shift = None
    if a_tower_meta.get("center") and b_tower_meta.get("center"):
        dx = b_tower_meta["center"][0] - a_tower_meta["center"][0]
        dy = b_tower_meta["center"][1] - a_tower_meta["center"][1]
        center_shift = round(float((dx * dx + dy * dy) ** 0.5), 3)

    checks = {
        "dimensions_check": {"pass": True, "A": [w, h], "B": [w, h]},
        "tower_roi_lock": tower_roi_qc,
        "tower_anchor_shift": {
            "pass": shift["distance_px"] is not None and shift["distance_px"] <= float(th["tower_anchor_shift_px_max"]),
            **shift,
            "maximum_px": float(th["tower_anchor_shift_px_max"]),
            "hard_maximum_px": float(th.get("tower_anchor_shift_px_hard_max", 8.0)),
            "detected_center_shift_px": center_shift,
        },
        "tower_mask_iou": {"pass": t_iou >= float(th["tower_mask_iou_min"]), "score": t_iou, "minimum": float(th["tower_mask_iou_min"])},
        "tower_bbox_iou": {"pass": t_bbox_iou >= float(th.get("tower_bbox_iou_min", 0.80)), "score": t_bbox_iou, "minimum": float(th.get("tower_bbox_iou_min", 0.80))},
        "anchor_edge_overlap": {"pass": anchor_edges["f1"] >= float(th["anchor_edge_f1_min"]), **anchor_edges, "minimum_f1": float(th["anchor_edge_f1_min"])},
        "skyline_edge_overlap": {"pass": skyline_edges["f1"] >= float(th["skyline_edge_f1_min"]), **skyline_edges, "minimum_f1": float(th["skyline_edge_f1_min"])},
        "skyline_mask_iou": {"pass": s_iou >= float(th["skyline_mask_iou_min"]), "score": s_iou, "minimum": float(th["skyline_mask_iou_min"])},
    }
    geometry_pass = all(v["pass"] for v in checks.values())

    style = evaluate_style(b, b_skyline, b_tower, preset.get("style_qc", {}))
    overall = geometry_pass and (style["pass"] if style.get("hard_gate") else True)
    failures = [name for name, item in checks.items() if not item["pass"]]
    if style.get("hard_gate") and not style["pass"]:
        failures.append("style_qc")

    attempt = state["restyle"]["active_attempt"]
    _save_mask(be, pdir / "qc" / f"edge_map_B_{attempt:02d}.png")
    _save_mask(b_tower, pdir / "qc" / f"tower_mask_B_{attempt:02d}.png")
    _save_mask(b_skyline, pdir / "qc" / f"skyline_mask_B_{attempt:02d}.png")
    save_edge_overlay(ae, be, pdir / "qc" / f"geometry_overlay_{attempt:02d}.png", tol)
    _save_anchor_preview(source_path, candidate_path, lock["anchor_roi"], pdir / "qc" / f"anchor_preview_{attempt:02d}.png")
    save_tower_roi_overlay(source_path, candidate_path, tower_roi_qc, pdir / "qc" / f"tower_roi_overlay_{attempt:02d}.png")

    # Compatibility aliases keep the v0.2 UI readable while the backend moves
    # to the richer hard_geometry_checks schema.
    dimensions_alias = {"pass": True, "source": [w, h], "candidate": [w, h]}
    anchor_alias = {"name": lock.get("anchor_name", "anchor"), **checks["anchor_edge_overlap"]}
    building_alias = dict(checks["skyline_edge_overlap"])
    shift_alias = dict(checks["tower_anchor_shift"])

    qc = {
        "pass": bool(overall),
        "geometry_pass": bool(geometry_pass),
        "style_pass": bool(style["pass"]),
        "dimensions": dimensions_alias,
        "anchor": anchor_alias,
        "building_contours": building_alias,
        "anchor_shift": shift_alias,
        "hard_geometry_checks": checks,
        "style_qc": style,
        "anchor_A": a_tower_meta,
        "anchor_B": b_tower_meta,
        "tower_roi_lock": tower_roi_qc,
        "failures": failures,
        "policy": "Geometry is a hard gate. Style QC is heuristic/advisory unless style_qc.hard_gate=true.",
    }
    state["artifacts"].update({
        "edge_map_B": f"qc/edge_map_B_{attempt:02d}.png",
        "tower_mask_B": f"qc/tower_mask_B_{attempt:02d}.png",
        "skyline_mask_B": f"qc/skyline_mask_B_{attempt:02d}.png",
        "geometry_overlay": f"qc/geometry_overlay_{attempt:02d}.png",
        "anchor_preview": f"qc/anchor_preview_{attempt:02d}.png",
        "tower_roi_overlay": f"qc/tower_roi_overlay_{attempt:02d}.png",
    })
    return _store_qc(pdir, state, qc)


def _store_qc(pdir: Path, state: dict, qc: dict) -> dict:
    attempt = state.get("restyle", {}).get("active_attempt") or 0
    report = pdir / "qc" / f"qc_report_{attempt:02d}.json"
    write_json(report, qc)
    state["qc"] = qc
    state["artifacts"]["qc_report"] = str(report.relative_to(pdir)).replace("\\", "/")
    if attempt and state.get("restyle", {}).get("attempts"):
        state["restyle"]["attempts"][attempt - 1]["qc"] = qc
    state["status"] = "validated" if qc.get("pass") else "qc_failed"
    if qc.get("pass"):
        accepted = pdir / "final" / "restyle_B_geometry_pass.png"
        Image.open(pdir / state["artifacts"]["candidate_target"]).convert("RGB").save(accepted)
        state["artifacts"]["restyle_b"] = "final/restyle_B_geometry_pass.png"
    else:
        state["artifacts"].pop("restyle_b", None)
    return state


def build_repair_prompt(base_prompt: str, qc: dict, attempt: int) -> str:
    failures = qc.get("failures", [])
    notes: list[str] = []
    checks = qc.get("hard_geometry_checks", {})
    if "tower_anchor_shift" in failures:
        item = checks.get("tower_anchor_shift", {})
        notes.append(f"Tokyo Tower moved by about {item.get('distance_px')} px. Keep its pixel position fixed; do not translate or rescale it.")
    if "tower_mask_iou" in failures or "tower_bbox_iou" in failures:
        notes.append("Reuse the exact Tokyo Tower silhouette and bounding box from Image A; change color/lighting only.")
    if "anchor_edge_overlap" in failures:
        notes.append("Do not redraw the tower lattice or nearby structural edges; preserve their exact outline from Image A.")
    if "skyline_edge_overlap" in failures or "skyline_mask_iou" in failures:
        notes.append("Preserve every major building mass and the complete skyline/horizon geometry from Image A.")
    if "dimensions_check" in failures:
        notes.append("Return the exact same canvas dimensions and crop as Image A.")
    if "tower_roi_lock" in failures:
        roi_qc = checks.get("tower_roi_lock", qc.get("tower_roi_lock", {}))
        tr = roi_qc.get("translation", {})
        dx, dy = tr.get("dx"), tr.get("dy")
        if dx is not None and dy is not None:
            correction_x = "left" if dx > 0 else "right"
            correction_y = "up" if dy > 0 else "down"
            notes.append(
                f"TOWER ROI HARD LOCK failed: detected A→B shift dx={dx}px, dy={dy}px. "
                f"Return Tokyo Tower to the exact A coordinates (correct roughly {abs(dx)}px {correction_x} and {abs(dy)}px {correction_y}); do not move surrounding buildings."
            )
        shape = roi_qc.get("shape", {})
        if not roi_qc.get("shape_pass", True):
            notes.append(
                "TOWER SHAPE LOCK failed: reuse the exact A tower silhouette, bbox, height, width, lattice outline, and base/tip coordinates. Change appearance only."
            )
    style = qc.get("style_qc", {})
    if not style.get("pass", True):
        notes.append("Keep geometry unchanged while strengthening only the requested color/style transformation.")
    suffix = "\n".join(f"- {n}" for n in notes) if notes else "- Preserve Image A geometry more strictly than the previous attempt."
    return (
        base_prompt.rstrip()
        + f"\n\nREPAIR PASS {attempt}: The previous candidate failed automated QC. Correct only the failed constraints:\n"
        + suffix
        + "\nThis is a repair/edit of the same scene, never a fresh composition."
    )


def repair(
    pdir: Path,
    state: dict,
    provider: str,
    base_prompt: str,
    model: str,
    quality: str,
    max_attempts: int | None = None,
    time_budget_s: float | None = None,
) -> dict:
    max_total = int(max_attempts or state.get("restyle", {}).get("max_attempts", 3))
    budget = float(time_budget_s if time_budget_s is not None else DEFAULT_TIME_BUDGET_S)
    t0 = time.monotonic()
    if state.get("qc", {}).get("pass"):
        return state
    while len(state.get("restyle", {}).get("attempts", [])) < max_total:
        # >= so that a zero budget deterministically blocks any further attempt
        if time.monotonic() - t0 >= budget:
            state["status"] = "repair_exhausted"
            state.setdefault("restyle", {})["repair_stop_reason"] = "time_budget"
            break
        next_num = len(state["restyle"]["attempts"]) + 1
        prompt = build_repair_prompt(base_prompt, state.get("qc") or {}, next_num)
        state = generate_candidate(pdir, state, provider, prompt, model, quality)
        state = validate_candidate(pdir, state)
        if state.get("qc", {}).get("pass"):
            break
    return state


def run_closed_loop(
    pdir: Path,
    state: dict,
    provider: str,
    base_prompt: str,
    model: str,
    quality: str,
    max_attempts: int | None = None,
    time_budget_s: float | None = None,
) -> dict:
    """Generate B, hard-FAIL invalid geometry, and auto-repair until PASS/exhaustion.

    `max_attempts` is scoped to this run, while the project keeps the complete
    attempt history across runs.
    """
    start_count = len(state.setdefault("restyle", {}).setdefault("attempts", []))
    run_budget = max(1, int(max_attempts or state.get("restyle", {}).get("max_attempts", 3)))
    max_total = start_count + run_budget

    state = generate_candidate(pdir, state, provider, base_prompt, model, quality)
    state = validate_candidate(pdir, state)
    started_at = state.get("restyle", {}).get("active_attempt")
    if not state.get("qc", {}).get("pass") and len(state.get("restyle", {}).get("attempts", [])) < max_total:
        state = repair(pdir, state, provider, base_prompt, model, quality, max_total, time_budget_s=time_budget_s)

    final_pass = bool(state.get("qc", {}).get("pass"))
    attempts_used = len(state.get("restyle", {}).get("attempts", [])) - start_count
    state.setdefault("restyle", {})["auto_repair"] = {
        "enabled": True,
        "run_budget": run_budget,
        "attempts_used": attempts_used,
        "pass": final_pass,
        "exhausted": not final_pass and attempts_used >= run_budget,
        "stop_reason": state.get("restyle", {}).get("repair_stop_reason"),
        "last_attempt": state.get("restyle", {}).get("active_attempt"),
        "started_at_attempt": started_at,
        "failures": list(state.get("qc", {}).get("failures", [])) if state.get("qc") else [],
        "tower_roi_lock": state.get("qc", {}).get("tower_roi_lock"),
    }
    if not final_pass and state["restyle"]["auto_repair"]["exhausted"]:
        state["status"] = "repair_exhausted"
    return state
