from __future__ import annotations

import base64
import os
from contextlib import ExitStack
from pathlib import Path
import httpx

OPENAI_EDIT_URL = "https://api.openai.com/v1/images/edits"


def generate(
    input_path: Path,
    mask_path: Path | None,
    output_path: Path,
    prompt: str,
    model: str = "gpt-image-2.5-sunburst",
    quality: str = "high",
    size: str = "auto",
    api_key: str | None = None,
    style_reference_path: Path | None = None,
    input_fidelity: str = "high",
) -> dict:
    """Call the OpenAI Image Edit endpoint.

    Geometry Source A is always the first image. When a style reference exists,
    it is sent as a second image input and is described by the prompt as style
    only. The mask applies to Geometry Source A. API credentials are read from
    the environment and are never written to project state.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    headers = {"Authorization": f"Bearer {key}"}
    data = {
        "model": model,
        "prompt": prompt,
        "n": "1",
        "quality": quality,
        "size": size,
        "output_format": "png",
        "input_fidelity": input_fidelity,
    }

    with ExitStack() as stack:
        image_f = stack.enter_context(input_path.open("rb"))
        files: list[tuple[str, tuple[str, object, str]]] = []
        if style_reference_path is not None and style_reference_path.exists():
            # GPT Image edit supports multiple image inputs. A is first and is
            # therefore explicitly treated as the geometry source by our prompt.
            style_f = stack.enter_context(style_reference_path.open("rb"))
            files.append(("image[]", (input_path.name, image_f, "image/png")))
            files.append(("image[]", (style_reference_path.name, style_f, "image/png")))
        else:
            files.append(("image", (input_path.name, image_f, "image/png")))

        if mask_path is not None and mask_path.exists():
            mask_f = stack.enter_context(mask_path.open("rb"))
            files.append(("mask", (mask_path.name, mask_f, "image/png")))

        with httpx.Client(timeout=300.0) as client:
            r = client.post(OPENAI_EDIT_URL, headers=headers, data=data, files=files)

    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI Image API error {r.status_code}: {r.text[:1200]}")
    payload = r.json()
    if not payload.get("data") or not payload["data"][0].get("b64_json"):
        raise RuntimeError("OpenAI Image API returned no base64 image data")
    raw = base64.b64decode(payload["data"][0]["b64_json"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return {
        "model": model,
        "quality": quality,
        "size": payload.get("size", size),
        "usage": payload.get("usage"),
        "style_reference_used": bool(style_reference_path),
        "input_fidelity": input_fidelity,
    }
