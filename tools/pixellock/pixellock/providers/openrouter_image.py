from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx
from PIL import Image

OPENROUTER_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") + "/chat/completions"


def _data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def _post_via_curl(payload: dict, headers: dict) -> dict:
    """POST via the curl CLI.

    Python's TLS stack (httpx/requests) gets intermittently reset on this host
    (GFW fingerprinting), while curl passes reliably through the local proxy.
    Payloads carry multi-MB base64 images, so they go through temp files.
    """
    import json
    import subprocess
    import tempfile

    proxy = os.getenv("OPENROUTER_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    last_err = "no attempt"
    for _attempt in range(3):
        req_path = resp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix="_or_req.json", delete=False, encoding="utf-8") as f:
                json.dump(payload, f)
                req_path = f.name
            resp_path = req_path.replace("_or_req.json", "_or_resp.json")
            cmd = [
                "curl.exe", "-sS", "-m", "570",
                "-H", f"Authorization: {headers['Authorization']}",
                "-H", "Content-Type: application/json",
                "-H", f"HTTP-Referer: {headers['HTTP-Referer']}",
                "-H", f"X-Title: {headers['X-Title']}",
                "--data-binary", f"@{req_path}",
                "-o", resp_path,
            ]
            if proxy:
                cmd += ["--proxy", proxy]
            cmd.append(OPENROUTER_URL)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=590)
            if proc.returncode != 0:
                last_err = f"curl exit {proc.returncode}: {proc.stderr[:400]}"
                continue
            text = Path(resp_path).read_text(encoding="utf-8", errors="replace")
            return json.loads(text)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            last_err = repr(exc)
        finally:
            for p in (req_path, resp_path):
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
    raise RuntimeError(f"OpenRouter curl POST failed after retries: {last_err}")


def generate(
    input_path: Path,
    mask_path: Path | None,  # chat-based edit APIs have no mask channel; kept for interface parity
    output_path: Path,
    prompt: str,
    model: str = "google/gemini-3-pro-image",
    quality: str = "high",
    size: str = "auto",
    api_key: str | None = None,
    style_reference_path: Path | None = None,
    api_size: tuple[int, int] | None = None,
) -> dict:
    """Call OpenRouter's chat/completions endpoint with image output modality.

    Geometry Source A is always the first image. When a style reference exists,
    it is sent as a second image input and is described by the prompt as style
    only. API credentials are read from the environment and are never written
    to project state.
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    content: list[dict] = [{"type": "text", "text": prompt}]
    content.append({"type": "image_url", "image_url": {"url": _data_url(input_path)}})
    if style_reference_path is not None and style_reference_path.exists():
        content.append({"type": "image_url", "image_url": {"url": _data_url(style_reference_path)}})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/zmuleyu/iphone-duo",
        "X-Title": "PixelLock geometry-locked restyle",
    }

    data = _post_via_curl(payload, headers)

    images = (data.get("choices") or [{}])[0].get("message", {}).get("images") or []
    if not images:
        raise RuntimeError(f"OpenRouter returned no image: {str(data)[:600]}")
    url = images[0].get("image_url", {}).get("url", "")
    if not url.startswith("data:image"):
        raise RuntimeError("OpenRouter image payload is not a data URL")
    raw = base64.b64decode(url.split(",", 1)[1])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(__import__("io").BytesIO(raw)).convert("RGBA")
    raw_size = f"{img.size[0]}x{img.size[1]}"
    if api_size and img.size != tuple(api_size):
        # Chat image models return their own canvas; normalize back to the API
        # input canvas so the deterministic crop-back stays valid.
        img = img.resize(tuple(api_size), Image.LANCZOS)
    img.save(output_path)
    return {
        "model": model,
        "quality": quality,
        "size": f"{img.size[0]}x{img.size[1]}",
        "raw_size": raw_size,
        "usage": data.get("usage"),
        "style_reference_used": bool(style_reference_path),
        "provider": "openrouter",
    }
