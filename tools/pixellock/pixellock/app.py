from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

from .core.project import ProjectStore
from .core.geometry import prepare_target, prepare_api_input, crop_api_candidate, lock_original, resize_final, crop_closed
from .core.restyle import prepare_restyle_input, crop_restyle_candidate, make_geometry_guide
from .core.qc import pixel_lock_check, seam_check, dimensions_check, edge_map
from .core.geometry_qc import geometry_lock_check
from .core.utils import write_json
from .providers import local_reflect, local_posterize, openai_image
from .workflows.restyle import (
    prepare_project as restyle_prepare_project,
    set_style_reference as restyle_set_style_reference,
    generate_candidate as restyle_generate_candidate,
    validate_candidate as restyle_validate_candidate,
    repair as restyle_repair,
    run_closed_loop as restyle_run_closed_loop,
)

BASE = Path(__file__).resolve().parent.parent
PROJECTS = Path(os.getenv("PIXELLOCK_PROJECTS_DIR", BASE / "projects"))
PRESETS = BASE / "presets"
STATIC = Path(__file__).resolve().parent / "static"
store = ProjectStore(PROJECTS, PRESETS)

app = FastAPI(title="PixelLock Image Pipeline", version="0.2.2")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class GenerateRequest(BaseModel):
    provider: Literal["local_reflect", "local_posterize", "openai"] = "local_reflect"
    prompt: str | None = None
    model: str = "gpt-image-2.5-sunburst"
    quality: str = "high"
    auto_qc: bool = True
    auto_repair: bool = True
    max_attempts: int = 3


class RepairRequest(BaseModel):
    provider: Literal["local_posterize", "openai"] = "openai"
    prompt: str | None = None
    model: str = "gpt-image-2.5-sunburst"
    quality: str = "high"
    max_attempts: int = 3


def _workflow(state: dict) -> str:
    return state.get("workflow", state.get("preset", {}).get("workflow", "outpaint"))


def _check_expected_size(state: dict) -> None:
    expected = state["preset"].get("source_expected")
    if not expected:
        return
    actual = (state["source"]["width"], state["source"]["height"])
    want = (expected["width"], expected["height"])
    if actual != want:
        raise HTTPException(400, f"Preset expects source {want[0]}×{want[1]}, got {actual[0]}×{actual[1]}.")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.2.2", "openai_key_configured": bool(os.getenv("OPENAI_API_KEY"))}


@app.post("/api/projects")
async def create_project(
    file: UploadFile = File(...),
    preset_id: str = Form("iphone_duo"),
    workflow: str = Form("outpaint"),
):
    suffix = Path(file.filename or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        try:
            return store.create(tmp_path, file.filename or "upload.png", preset_id, workflow)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    try:
        _, state = store.get(pid)
        return state
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.post("/api/projects/{pid}/prepare")
def prepare(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    _check_expected_size(state)
    preset = state["preset"]
    source = pdir / state["source"]["path"]

    if _workflow(state) == "restyle":
        state = restyle_prepare_project(pdir, state)
        store.save(pdir, state)
        return state

    ext = preset["extension"]
    target_path = pdir / "working" / "target_transparent.png"
    target = prepare_target(source, target_path, ext)
    expected = (preset["intermediate"]["width"], preset["intermediate"]["height"])
    if target.size != expected:
        raise HTTPException(400, f"Source + preset extension produced {target.size}, expected {expected}.")
    api_input = pdir / "working" / "api_input.png"
    api_mask = pdir / "working" / "api_mask.png"
    api_size = prepare_api_input(target, api_input, api_mask, ext, preset.get("api_multiple", 16))
    state["status"] = "prepared"
    state["artifacts"].update({
        "target_transparent": "working/target_transparent.png",
        "api_input": "working/api_input.png",
        "api_mask": "working/api_mask.png",
    })
    state["api_working_size"] = {"width": api_size[0], "height": api_size[1]}
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/generate")
def generate(pid: str, req: GenerateRequest):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if state["status"] not in {"prepared", "generated", "locked", "validated", "qc_failed", "repair_exhausted", "exported"}:
        raise HTTPException(400, "Prepare the project first")

    preset = state["preset"]
    prompt = req.prompt or preset.get("prompt", "Preserve geometry and change only the requested appearance.")
    api_candidate = pdir / "generated" / "candidate_api.png"
    target_candidate = pdir / "generated" / "candidate_target.png"
    workflow = _workflow(state)

    if workflow == "restyle":
        try:
            if req.auto_qc:
                if req.auto_repair:
                    state = restyle_run_closed_loop(
                        pdir, state, req.provider, prompt, req.model, req.quality, req.max_attempts
                    )
                else:
                    state = restyle_generate_candidate(
                        pdir, state, req.provider, prompt, req.model, req.quality
                    )
                    state = restyle_validate_candidate(pdir, state)
            else:
                state = restyle_generate_candidate(
                    pdir, state, req.provider, prompt, req.model, req.quality
                )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(502, str(e))
        store.save(pdir, state)
        return state

    try:
        if req.provider == "local_reflect":
            local_reflect.generate(pdir / state["source"]["path"], target_candidate, preset["extension"])
            Image.open(target_candidate).save(api_candidate)
            gen_meta = {"provider": "local_reflect", "note": "Free deterministic reflect-padding fallback"}
        elif req.provider == "openai":
            api_size = state["api_working_size"]
            meta = openai_image.generate(
                pdir / state["artifacts"]["api_input"],
                pdir / state["artifacts"]["api_mask"],
                api_candidate,
                prompt=prompt,
                model=req.model,
                quality=req.quality,
                size=f'{api_size["width"]}x{api_size["height"]}',
            )
            crop_api_candidate(api_candidate, (preset["intermediate"]["width"], preset["intermediate"]["height"]), target_candidate)
            gen_meta = {"provider": "openai", **meta}
        else:
            raise ValueError("Outpaint workflow supports local_reflect or openai")
    except Exception as e:
        raise HTTPException(502, str(e))

    state["generation"] = {**gen_meta, "prompt": prompt}
    state["status"] = "generated"
    state["qc"] = None
    state["artifacts"].update({
        "candidate_api": "generated/candidate_api.png",
        "candidate_target": "generated/candidate_target.png",
    })
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/lock")
def lock(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) == "restyle":
        raise HTTPException(400, "A→B restyle uses geometry validation instead of pixel recomposition. Run Validate Geometry.")
    if "candidate_target" not in state["artifacts"]:
        raise HTTPException(400, "Generate a candidate first")
    preset = state["preset"]
    master = pdir / "final" / f'master_locked_{preset["intermediate"]["width"]}x{preset["intermediate"]["height"]}.png'
    lock_original(pdir / state["artifacts"]["candidate_target"], pdir / state["source"]["path"], master, preset["extension"])
    state["status"] = "locked"
    state["artifacts"]["master_locked"] = str(master.relative_to(pdir)).replace("\\", "/")
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/validate")
def validate(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    preset = state["preset"]

    if _workflow(state) == "restyle":
        try:
            state = restyle_validate_candidate(pdir, state)
        except ValueError as e:
            raise HTTPException(400, str(e))
        store.save(pdir, state)
        return state

    if "master_locked" not in state["artifacts"]:
        raise HTTPException(400, "Lock the candidate first")
    master = pdir / state["artifacts"]["master_locked"]
    expected = (preset["intermediate"]["width"], preset["intermediate"]["height"])
    qc = {
        "dimensions": dimensions_check(master, expected),
        "pixel_lock": pixel_lock_check(pdir / state["source"]["path"], master, preset["extension"], pdir / "qc" / "pixel_diff.png"),
        "seam": seam_check(master, preset["extension"], pdir / "qc" / "seam_preview.png"),
    }
    edge_map(master, pdir / "qc" / "master_edges.png")
    qc["pass"] = all(item.get("pass", False) for item in qc.values() if isinstance(item, dict) and "pass" in item)
    write_json(pdir / "qc" / "qc_report.json", qc)
    state["qc"] = qc
    state["status"] = "validated" if qc["pass"] else "qc_failed"
    state["artifacts"].update({
        "pixel_diff": "qc/pixel_diff.png",
        "seam_preview": "qc/seam_preview.png",
        "master_edges": "qc/master_edges.png",
        "qc_report": "qc/qc_report.json",
    })
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/restyle/style-reference")
async def restyle_style_reference(pid: str, file: UploadFile = File(...)):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) != "restyle":
        raise HTTPException(400, "Project is not a restyle workflow")
    suffix = Path(file.filename or "style.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        state = restyle_set_style_reference(pdir, state, tmp_path)
        store.save(pdir, state)
        return state
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/projects/{pid}/restyle/prepare")
def restyle_prepare(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) != "restyle":
        raise HTTPException(400, "Project is not a restyle workflow")
    _check_expected_size(state)
    state = restyle_prepare_project(pdir, state)
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/restyle/generate")
def restyle_generate(pid: str, req: GenerateRequest):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) != "restyle":
        raise HTTPException(400, "Project is not a restyle workflow")
    prompt = req.prompt or state["preset"].get("prompt", "Preserve Image A geometry exactly and change appearance only.")
    try:
        if req.auto_qc:
            if req.auto_repair:
                state = restyle_run_closed_loop(
                    pdir, state, req.provider, prompt, req.model, req.quality, req.max_attempts
                )
            else:
                state = restyle_generate_candidate(pdir, state, req.provider, prompt, req.model, req.quality)
                state = restyle_validate_candidate(pdir, state)
        else:
            state = restyle_generate_candidate(pdir, state, req.provider, prompt, req.model, req.quality)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/restyle/validate")
def restyle_validate(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) != "restyle":
        raise HTTPException(400, "Project is not a restyle workflow")
    try:
        state = restyle_validate_candidate(pdir, state)
    except ValueError as e:
        raise HTTPException(400, str(e))
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/restyle/repair")
def restyle_repair_endpoint(pid: str, req: RepairRequest):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    if _workflow(state) != "restyle":
        raise HTTPException(400, "Project is not a restyle workflow")
    if not state.get("qc"):
        raise HTTPException(400, "Validate the current candidate before repair")
    prompt = req.prompt or state["preset"].get("prompt", "Preserve Image A geometry exactly and change appearance only.")
    try:
        state = restyle_repair(
            pdir, state, req.provider, prompt, req.model, req.quality, req.max_attempts
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))
    store.save(pdir, state)
    return state


@app.post("/api/projects/{pid}/export")
def export(pid: str):
    try:
        pdir, state = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    preset = state["preset"]
    final_size = (preset["final"]["width"], preset["final"]["height"])
    cc = preset["closed_crop"]

    if _workflow(state) == "restyle":
        if state.get("status") != "validated" or not state.get("qc", {}).get("pass") or "restyle_b" not in state["artifacts"]:
            raise HTTPException(400, "Geometry QC must PASS before A/B export")
        a_open = pdir / "final" / "A_open_2670x1878.png"
        a_closed = pdir / "final" / "A_closed_right_1335x1878.png"
        b_open = pdir / "final" / "B_open_2670x1878.png"
        b_closed = pdir / "final" / "B_closed_right_1335x1878.png"
        resize_final(pdir / state["source"]["path"], a_open, final_size)
        crop_closed(a_open, a_closed, cc["width"], cc["height"], cc.get("side", "right"))
        resize_final(pdir / state["artifacts"]["restyle_b"], b_open, final_size)
        crop_closed(b_open, b_closed, cc["width"], cc["height"], cc.get("side", "right"))
        state["artifacts"].update({
            "a_open_final": "final/A_open_2670x1878.png",
            "a_closed_final": "final/A_closed_right_1335x1878.png",
            "b_open_final": "final/B_open_2670x1878.png",
            "b_closed_final": "final/B_closed_right_1335x1878.png",
        })
        state["status"] = "exported"
        store.save(pdir, state)
        return state

    if "master_locked" not in state["artifacts"]:
        raise HTTPException(400, "Lock the candidate first")
    open_path = pdir / "final" / "open_2670x1878.png"
    resize_final(pdir / state["artifacts"]["master_locked"], open_path, final_size)
    closed_path = pdir / "final" / "closed_right_1335x1878.png"
    crop_closed(open_path, closed_path, cc["width"], cc["height"], cc.get("side", "right"))
    state["status"] = "exported"
    state["artifacts"].update({
        "open_final": "final/open_2670x1878.png",
        "closed_final": "final/closed_right_1335x1878.png",
    })
    store.save(pdir, state)
    return state


@app.get("/api/projects/{pid}/file/{relpath:path}")
def project_file(pid: str, relpath: str):
    try:
        pdir, _ = store.get(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    path = (pdir / relpath).resolve()
    if pdir.resolve() not in path.parents:
        raise HTTPException(400, "Invalid path")
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


def main():
    import uvicorn
    uvicorn.run("pixellock.app:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
