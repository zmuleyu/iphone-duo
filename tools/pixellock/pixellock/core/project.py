from __future__ import annotations

import uuid
from pathlib import Path
from PIL import Image
from .utils import read_json, write_json, sha256_file


class ProjectStore:
    def __init__(self, root: Path, presets_dir: Path):
        self.root = root
        self.presets_dir = presets_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def load_preset(self, preset_id: str) -> dict:
        path = self.presets_dir / f"{preset_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Preset not found: {preset_id}")
        return read_json(path)

    def create(self, upload_path: Path, original_filename: str, preset_id: str, workflow: str | None = None) -> dict:
        preset = self.load_preset(preset_id)
        workflow = workflow or preset.get("workflow", "outpaint")
        if workflow not in {"outpaint", "restyle"}:
            raise ValueError(f"Unsupported workflow: {workflow}")
        if preset.get("workflow") and preset["workflow"] != workflow:
            raise ValueError(f"Preset {preset_id} belongs to workflow {preset['workflow']}")

        pid = uuid.uuid4().hex[:12]
        pdir = self.root / pid
        for sub in ["source", "working", "generated", "final", "qc"]:
            (pdir / sub).mkdir(parents=True, exist_ok=True)
        src_path = pdir / "source" / "source.png"
        img = Image.open(upload_path).convert("RGBA")
        img.save(src_path)
        state = {
            "id": pid,
            "version": "0.2.1",
            "workflow": workflow,
            "preset": preset,
            "source": {
                "original_filename": original_filename,
                "path": "source/source.png",
                "width": img.width,
                "height": img.height,
                "sha256": sha256_file(src_path),
            },
            "status": "created",
            "artifacts": {},
            "generation": None,
            "qc": None,
        }
        write_json(pdir / "project.json", state)
        return state

    def get(self, pid: str) -> tuple[Path, dict]:
        pdir = self.root / pid
        path = pdir / "project.json"
        if not path.exists():
            raise FileNotFoundError(pid)
        state = read_json(path)
        # v0.1 projects remain readable.
        state.setdefault("workflow", state.get("preset", {}).get("workflow", "outpaint"))
        return pdir, state

    def save(self, pdir: Path, state: dict) -> None:
        write_json(pdir / "project.json", state)
