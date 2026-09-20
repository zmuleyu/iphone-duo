from __future__ import annotations

from pathlib import Path
from PIL import Image
from .utils import round_up


def prepare_target(source_path: Path, target_path: Path, extension: dict[str, int]) -> Image.Image:
    src = Image.open(source_path).convert("RGBA")
    left, right = extension["left"], extension["right"]
    top, bottom = extension["top"], extension["bottom"]
    out = Image.new("RGBA", (src.width + left + right, src.height + top + bottom), (0, 0, 0, 0))
    out.paste(src, (left, top))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(target_path)
    return out


def prepare_api_input(target: Image.Image, input_path: Path, mask_path: Path, extension: dict[str, int], multiple: int = 16) -> tuple[int, int]:
    api_w = round_up(target.width, multiple)
    api_h = round_up(target.height, multiple)
    canvas = Image.new("RGBA", (api_w, api_h), (0, 0, 0, 0))
    canvas.paste(target, (0, 0))

    # For Image API edits: transparent mask pixels are editable; opaque pixels are preserved.
    mask = Image.new("RGBA", (api_w, api_h), (255, 255, 255, 255))
    pix = mask.load()
    left, right = extension["left"], extension["right"]
    top, bottom = extension["top"], extension["bottom"]
    tw, th = target.size

    for y in range(th):
        for x in range(tw):
            editable = x < left or x >= tw - right or y < top or y >= th - bottom
            if editable:
                pix[x, y] = (255, 255, 255, 0)

    input_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(input_path)
    mask.save(mask_path)
    return api_w, api_h


def crop_api_candidate(api_candidate_path: Path, target_size: tuple[int, int], output_path: Path) -> Image.Image:
    img = Image.open(api_candidate_path).convert("RGBA")
    out = img.crop((0, 0, target_size[0], target_size[1]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    return out


def lock_original(candidate_path: Path, source_path: Path, output_path: Path, extension: dict[str, int]) -> Image.Image:
    candidate = Image.open(candidate_path).convert("RGBA")
    source = Image.open(source_path).convert("RGBA")
    candidate.paste(source, (extension["left"], extension["top"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidate.save(output_path)
    return candidate


def resize_final(master_path: Path, output_path: Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(master_path).convert("RGB")
    out = img.resize(size, Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path, format="PNG")
    return out


def crop_closed(open_path: Path, output_path: Path, width: int, height: int, side: str = "right") -> Image.Image:
    img = Image.open(open_path).convert("RGB")
    if img.height != height:
        raise ValueError(f"Expected height {height}, got {img.height}")
    if width > img.width:
        raise ValueError("Closed crop is wider than open image")
    x0 = img.width - width if side == "right" else 0
    out = img.crop((x0, 0, x0 + width, height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path, format="PNG")
    return out
