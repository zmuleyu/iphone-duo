"""Capture and composite the deterministic STORM II character state pack.

This script captures only the declared exact-frame review states. It does not
record or encode a video. The Fold Engine supplies every device pixel; accepted
RGBA character sources are composited afterward under an aligned union mask.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import websockets
from PIL import Image, ImageChops, ImageDraw, ImageFont


URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/?nofx=1&format=16x9"
ROOT = (
    Path(sys.argv[2])
    if len(sys.argv) > 2
    else Path.cwd() / "artifacts" / "storm-ii-character-state-pack"
).resolve()
CHARACTERS = ROOT / "characters"
STATE_ROOT = ROOT / "state-pack"
WIDTH, HEIGHT = 1920, 1080
FPS = 60
FRAME_END_EXCLUSIVE = 348


@dataclass(frozen=True)
class State:
    frame: int
    phase: str
    label: str


STATES = (
    State(0, "rumor", "closed-anchor"),
    State(45, "pull", "delayed-payoff-start"),
    State(99, "formation", "first-fold-motion"),
    State(119, "formation", "reveal-25"),
    State(140, "formation", "reveal-50"),
    State(160, "formation", "reveal-75"),
    State(179, "formation", "last-pre-open"),
    State(180, "open-hold", "stable-open"),
    State(207, "pulse", "pulse-start"),
    State(240, "pulse", "pulse-peak"),
    State(273, "poster-freeze", "hero-start"),
    State(317, "poster-freeze", "hero-end"),
    State(347, "compression", "final-frame"),
)

EXPECTED_HASHES = {
    "ELON-CAL-001": "54E9BE808AD274FD307A0BA8CEB6C5AA169BAA54AE213BE53765296F60E45AE9",
    "ELON-CAL-002": "E2F2DABD745EFC915B19B1F993FFC7858C60372E8AEE307F7D058B96517E68EF",
    "ELON-OPEN-001": "E47FE2787492A5906E2E4C8DCC922C0AAC70E89D30609AFD822EBDF5D5715312",
    "JENSEN-SUP-001": "FD929B13B470D5227240CC4FB80244D277C6C22DA67FF2124D682DF7E506412A",
    "SAM-SUP-001": "9917B2587087603DFA6F5A8603C36B7109958F28B058404D56F83839E1112527",
    "DARIO-MID-001": "6D63530DD06D3F19B10F8694E2B6387815A757C49204A3AF2605081C851D1F8F",
}

COLORS = {
    "DARIO-MID-001": (122, 178, 255),
    "JENSEN-SUP-001": (102, 230, 205),
    "SAM-SUP-001": (255, 183, 99),
    "ELON-CAL-001": (241, 115, 125),
    "ELON-CAL-002": (241, 115, 125),
    "ELON-OPEN-001": (241, 115, 125),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def fold_angle(frame: int) -> float:
    if frame < 99:
        return 0.0
    if frame >= 180:
        return 180.0
    return 180.0 * smoothstep((frame - 99) / 81.0)


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def pulse_amount(frame: int) -> float:
    if frame < 207 or frame >= 273:
        return 0.0
    return math.sin(math.pi * (frame - 207) / 66.0)


def character_layout(frame: int) -> list[dict]:
    """Return deterministic screen-space placement back-to-front."""
    pulse = pulse_amount(frame)
    compress = smoothstep((frame - 318) / 30.0) if frame >= 318 else 0.0
    if frame < 99:
        pull = smoothstep((frame - 45) / 54.0) if frame >= 45 else 0.0
        return [
            {
                "id": "ELON-CAL-001",
                "x": lerp(0.72, 0.68, pull),
                "bottom": 0.925,
                "height": 0.82,
                "opacity": 1.0,
            }
        ]

    formation = smoothstep((frame - 99) / 81.0)
    elon_id = "ELON-CAL-002" if frame < 180 else "ELON-OPEN-001"
    support_opacity = 0.18 + 0.82 * formation
    layout = [
        {
            "id": "DARIO-MID-001",
            "x": lerp(0.53, 0.66, formation),
            "bottom": 0.86 - pulse * 0.006,
            "height": (0.58 + pulse * 0.015) * (1.0 - 0.02 * compress),
            "opacity": min(0.82, support_opacity * 0.82),
        },
        {
            "id": "JENSEN-SUP-001",
            "x": lerp(0.48, 0.23, formation),
            "bottom": 0.93 - pulse * 0.016,
            "height": (0.78 + pulse * 0.035) * (1.0 - 0.02 * compress),
            "opacity": support_opacity,
        },
        {
            "id": "SAM-SUP-001",
            "x": lerp(0.53, 0.78, formation),
            "bottom": 0.92 - pulse * 0.014,
            "height": (0.75 + pulse * 0.032) * (1.0 - 0.02 * compress),
            "opacity": support_opacity,
        },
        {
            "id": elon_id,
            "x": lerp(0.67, 0.50, formation),
            "bottom": 0.94 - pulse * 0.022,
            "height": (0.88 + pulse * 0.042) * (1.0 - 0.02 * compress),
            "opacity": 1.0,
        },
    ]
    return layout


def state_name(state: State) -> str:
    return f"frame_{state.frame:06d}_{state.phase}_{state.label}_16x9_r1.png"


def composite_state(clean_path: Path, state: State) -> dict:
    clean = Image.open(clean_path).convert("RGBA")
    if clean.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"Unexpected clean size {clean.size} for {clean_path}")
    composite = clean.copy()
    union_mask = Image.new("L", clean.size, 0)
    motion = clean.copy()
    motion_draw = ImageDraw.Draw(motion, "RGBA")
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 21)
    placements = []

    for spec in character_layout(state.frame):
        source_path = CHARACTERS / f"{spec['id']}.png"
        source = Image.open(source_path).convert("RGBA")
        target_height = round(HEIGHT * spec["height"])
        target_width = round(source.width * target_height / source.height)
        resized = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
        if spec["opacity"] < 1.0:
            alpha = resized.getchannel("A").point(
                lambda value: round(value * spec["opacity"])
            )
            resized.putalpha(alpha)
        x = round(WIDTH * spec["x"] - target_width / 2)
        y = round(HEIGHT * spec["bottom"] - target_height)
        composite.alpha_composite(resized, (x, y))
        alpha = resized.getchannel("A")
        union_mask.paste(ImageChops.lighter(union_mask.crop((x, y, x + target_width, y + target_height)), alpha), (x, y))
        bbox = alpha.point(lambda value: 255 if value >= 16 else 0).getbbox()
        if bbox:
            visible = (x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3])
            color = COLORS[spec["id"]]
            motion_draw.rectangle(visible, outline=(*color, 235), width=3)
            motion_draw.text(
                (visible[0] + 8, max(8, visible[1] + 8)),
                spec["id"],
                font=font,
                fill=(*color, 255),
                stroke_width=3,
                stroke_fill=(10, 12, 16, 220),
            )
        placements.append(
            {
                **spec,
                "canvas_box": [x, y, x + target_width, y + target_height],
            }
        )

    file_name = state_name(state)
    composite_path = STATE_ROOT / "composite" / file_name
    mask_path = STATE_ROOT / "character-mask" / file_name
    motion_path = STATE_ROOT / "motion-reference" / file_name
    composite.convert("RGB").save(composite_path)
    union_mask.save(mask_path)
    motion.convert("RGB").save(motion_path)

    clean_rgb = clean.convert("RGB")
    composite_rgb = composite.convert("RGB")
    diff = ImageChops.difference(clean_rgb, composite_rgb)
    inside_binary = union_mask.point(lambda value: 255 if value > 0 else 0)
    outside = ImageChops.subtract(Image.new("L", union_mask.size, 255), inside_binary)
    protected_diff = Image.composite(diff, Image.new("RGB", diff.size), outside)
    protected_bbox = protected_diff.getbbox()
    return {
        "frame": state.frame,
        "time_seconds": round(state.frame / FPS, 6),
        "phase": state.phase,
        "label": state.label,
        "fold_angle_degrees": round(fold_angle(state.frame), 6),
        "files": {
            "clean": clean_path.as_posix(),
            "composite": composite_path.as_posix(),
            "character_mask": mask_path.as_posix(),
            "motion_reference": motion_path.as_posix(),
        },
        "hashes": {
            "clean": sha256(clean_path),
            "composite": sha256(composite_path),
            "character_mask": sha256(mask_path),
            "motion_reference": sha256(motion_path),
        },
        "character_mask_bbox": list(union_mask.getbbox() or ()),
        "protected_pixel_mismatch_bbox": list(protected_bbox or ()),
        "protected_pixel_pass": protected_bbox is None,
        "placements": placements,
    }


def build_contact_sheet(records: list[dict]) -> Path:
    columns = 4
    thumb_w, thumb_h = 420, 236
    panel_w, panel_h = 436, 300
    rows = math.ceil(len(records) / columns)
    sheet = Image.new("RGB", (columns * panel_w + 36, rows * panel_h + 110), (17, 20, 26))
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 34)
    label = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 18)
    small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15)
    draw.text((28, 24), "STORM II character state pack - review r1", font=title, fill=(246, 248, 252))
    draw.text((28, 68), "Exact frame states · 1920x1080 · silent · internal rights gate", font=small, fill=(164, 175, 191))
    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x = 20 + column * panel_w
        y = 100 + row * panel_h
        image = Image.open(record["files"]["composite"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x + 8, y + 8))
        draw.rounded_rectangle((x, y, x + panel_w - 8, y + panel_h - 10), radius=12, outline=(65, 74, 89), width=2)
        draw.text((x + 10, y + 250), f"F{record['frame']:03d} · {record['phase'].upper()}", font=label, fill=(242, 245, 250))
        draw.text((x + 10, y + 273), f"{record['fold_angle_degrees']:.1f}° · {record['label']}", font=small, fill=(134, 221, 169))
    output = ROOT / "review" / "state-pack-contact-sheet-r1.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=95)
    return output


async def main() -> None:
    if not 0 < len(STATES) < FRAME_END_EXCLUSIVE:
        raise RuntimeError("Invalid state matrix")
    for path in (
        STATE_ROOT / "clean",
        STATE_ROOT / "composite",
        STATE_ROOT / "character-mask",
        STATE_ROOT / "motion-reference",
    ):
        path.mkdir(parents=True, exist_ok=True)
    for asset_id, expected in EXPECTED_HASHES.items():
        actual = sha256(CHARACTERS / f"{asset_id}.png")
        if actual != expected:
            raise RuntimeError(f"Character hash mismatch for {asset_id}: {actual}")

    version = json.loads(
        urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read()
    )
    websocket = await websockets.connect(
        version["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024
    )
    pending: dict[int, asyncio.Future] = {}
    counter = 0
    errors: list[str] = []

    async def reader() -> None:
        async for raw in websocket:
            message = json.loads(raw)
            if "id" in message and message["id"] in pending:
                pending.pop(message["id"]).set_result(message)
            elif message.get("method") == "Runtime.exceptionThrown":
                errors.append(str(message["params"])[:800])
            elif message.get("method") == "Log.entryAdded":
                entry = message["params"]["entry"]
                if entry.get("level") == "error":
                    errors.append(entry.get("text", "")[:800])

    asyncio.create_task(reader())

    async def send(method: str, params: dict | None = None, session: str | None = None):
        nonlocal counter
        counter += 1
        message = {"id": counter, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        future = asyncio.get_running_loop().create_future()
        pending[counter] = future
        await websocket.send(json.dumps(message))
        response = await future
        if "error" in response:
            raise RuntimeError(f"{method}: {response['error']}")
        return response.get("result", {})

    target = await send("Target.createTarget", {"url": "about:blank"})
    attached = await send(
        "Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}
    )
    session = attached["sessionId"]
    for method in ("Page.enable", "Runtime.enable", "Log.enable"):
        await send(method, session=session)
    await send(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": WIDTH,
            "height": HEIGHT,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
        session=session,
    )
    await send("Page.navigate", {"url": URL}, session=session)

    async def evaluate(expression: str, await_promise: bool = False):
        response = await send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
            },
            session=session,
        )
        if "exceptionDetails" in response:
            raise RuntimeError(str(response["exceptionDetails"])[:1000])
        return response.get("result", {}).get("value")

    async def wait_for(expression: str, timeout: float = 60) -> None:
        for _ in range(int(timeout * 5)):
            if await evaluate(expression):
                return
            await asyncio.sleep(0.2)
        raise TimeoutError(expression)

    await wait_for("window.__duo && window.__duo.state.ready === true")
    await evaluate("window.__duo.setRecordingMode(true)")
    await evaluate(
        "(()=>{const s=document.createElement('style');"
        "s.textContent='#stage > :not(#viewport), body > :not(#stage):not(script){visibility:hidden!important}';"
        "document.head.appendChild(s);})()"
    )
    await evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))", True)
    canvas_rect = json.loads(
        await evaluate(
            "JSON.stringify((()=>{const r=document.querySelector('#viewport canvas').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,dpr:devicePixelRatio}})())"
        )
    )
    if round(canvas_rect["width"]) != WIDTH or round(canvas_rect["height"]) != HEIGHT:
        raise RuntimeError(f"Unexpected canvas rect: {canvas_rect}")

    runtime_state = json.loads(await evaluate("JSON.stringify(window.__duo.state)"))
    records = []
    for state in STATES:
        angle = fold_angle(state.frame)
        await evaluate(f"window.__duo.setAngle({angle!r})")
        await evaluate(
            "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))",
            True,
        )
        result = await send(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": False,
                "clip": {
                    "x": canvas_rect["x"],
                    "y": canvas_rect["y"],
                    "width": canvas_rect["width"],
                    "height": canvas_rect["height"],
                    "scale": 1,
                },
            },
            session=session,
        )
        clean_path = STATE_ROOT / "clean" / state_name(state)
        clean_path.write_bytes(base64.b64decode(result["data"]))
        records.append(composite_state(clean_path, state))

    await send("Target.closeTarget", {"targetId": target["targetId"]})
    await websocket.close()
    if errors:
        raise RuntimeError(f"Browser errors: {errors[:3]}")
    if not all(record["protected_pixel_pass"] for record in records):
        raise RuntimeError("Protected clean-plate pixel comparison failed")

    contact_sheet = build_contact_sheet(records)
    qc = {
        "qc_version": "1.0",
        "run_id": "storm-fold-20260920-01",
        "url": URL,
        "resolution": [WIDTH, HEIGHT],
        "fps": FPS,
        "frame_end_exclusive": FRAME_END_EXCLUSIVE,
        "engine_commit": "33a20c5192cdb4619023c2ffa4ae68f38eb20f46",
        "engine_build": runtime_state["baseline"],
        "canvas": canvas_rect,
        "accepted_character_hashes": EXPECTED_HASHES,
        "records": records,
        "all_protected_pixels_pass": True,
        "console_errors": errors,
        "contact_sheet": contact_sheet.as_posix(),
        "status": "mechanical-pass-pending-consolidated-visual-review",
    }
    qc_path = ROOT / "state-pack-qc.json"
    qc_path.write_text(json.dumps(qc, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "qc": str(qc_path),
                "contact_sheet": str(contact_sheet),
                "state_count": len(records),
                "protected_pixel_pass": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
