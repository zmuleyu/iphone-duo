"""Capture the 5.8-second Tokyo v6.18 silent review preview via CDP."""

import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

import websockets


URL = sys.argv[1] if len(sys.argv) > 1 else (
    "http://127.0.0.1:8766/?cap=1&tokyo=v618&nofx=1&motion=tokyo-demo"
    "&timeline=tokyo&format=16x9&closedUi=0&openUi=1"
)
OUTPUT = (
    Path(sys.argv[2])
    if len(sys.argv) > 2
    else Path.cwd() / "artifacts" / "v6.18-tokyo-silent-demo"
).resolve()
EVIDENCE_ONLY = '--evidence-only' in sys.argv[3:]


async def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    version = json.loads(
        urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read()
    )
    websocket = await websockets.connect(
        version["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024
    )
    pending = {}
    counter = 0
    errors = []

    async def reader():
        async for raw in websocket:
            message = json.loads(raw)
            if "id" in message and message["id"] in pending:
                pending.pop(message["id"]).set_result(message)
            elif message.get("method") == "Runtime.exceptionThrown":
                errors.append(str(message["params"])[:500])
            elif message.get("method") == "Log.entryAdded":
                entry = message["params"]["entry"]
                if entry.get("level") == "error":
                    errors.append(entry.get("text", "")[:500])

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
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

    await send(
        "Browser.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": str(OUTPUT), "eventsEnabled": True},
    )
    target = await send("Target.createTarget", {"url": "about:blank"})
    attached = await send(
        "Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}
    )
    session = attached["sessionId"]
    for method in ("Page.enable", "Runtime.enable", "Log.enable"):
        await send(method, session=session)
    await send(
        "Emulation.setDeviceMetricsOverride",
        {"width": 1440, "height": 900, "deviceScaleFactor": 1.25, "mobile": False},
        session=session,
    )
    await send("Page.navigate", {"url": URL}, session=session)

    async def evaluate(expression):
        response = await send(
            "Runtime.evaluate", {"expression": expression, "returnByValue": True}, session
        )
        if "exceptionDetails" in response:
            raise RuntimeError(str(response["exceptionDetails"])[:800])
        return response.get("result", {}).get("value")

    async def wait_for(expression, timeout=60):
        for _ in range(int(timeout * 10)):
            if await evaluate(expression):
                return
            await asyncio.sleep(0.1)
        raise TimeoutError(expression)

    async def screenshot(name):
        result = await send("Page.captureScreenshot", {"format": "png"}, session=session)
        (OUTPUT / name).write_bytes(base64.b64decode(result["data"]))
        return int(await evaluate("Number(document.documentElement.dataset.recordFrame || -1)"))

    await wait_for("window.__duo && window.__duo.state.ready === true")
    await wait_for(
        "window.__duo.state.customReady.reality && window.__duo.state.customReady.redblack"
    )
    state = json.loads(await evaluate("JSON.stringify(window.__duo.state)"))
    pair = state["masterPairQA"]["pair"]
    if not pair["pass"]:
        raise RuntimeError("bundled Tokyo pair failed dimension/aspect gate")
    if state["foldMotion"]["preset"] != "tokyo-demo":
        raise RuntimeError("Tokyo review preset was not activated")

    await evaluate("window.__duo.setRecordFormat('16x9'); window.__duo.setRecordFps(60)")
    await evaluate("window.__duo.setRecordingMode(true)")
    rect = json.loads(
        await evaluate(
            "(() => { const r=document.querySelector('#record-safe-frame').getBoundingClientRect();"
            "return JSON.stringify({x:Math.round(r.x),y:Math.round(r.y),"
            "w:Math.round(r.width),h:Math.round(r.height)}); })()"
        )
    )
    canvas_scale = await evaluate(
        "(() => { const c=document.querySelector('#viewport canvas'); return c.width/c.clientWidth; })()"
    )
    (OUTPUT / "safe-rect.json").write_text(
        json.dumps({"rect": rect, "canvasScale": canvas_scale, "url": URL}, indent=2),
        encoding="utf-8",
    )

    await send("Page.bringToFront", session=session)
    if not EVIDENCE_ONLY:
        if list(OUTPUT.glob('*.webm')):
            raise RuntimeError('Capture source already exists; choose a fresh output directory or --evidence-only')
        await evaluate("window.__duo.startRecord()")
        await wait_for("document.documentElement.dataset.recordDone === '1'", timeout=15)
        await wait_for("document.documentElement.dataset.captureDone === '1'", timeout=15)
        for _ in range(100):
            if list(OUTPUT.glob("*.webm")):
                break
            await asyncio.sleep(0.1)
        else:
            raise TimeoutError("recording download did not arrive")
        final_state = json.loads(await evaluate("JSON.stringify(window.__duo.state)"))
    evidence = {}
    key_states = {}
    for frame, name in (
        (0, "01-closed.png"), (74, "02-opening-no-red-leak.png"),
        (91, "03-red-hinge.png"), (105, "04-black-city.png"),
        (121, "05-yellow-lock.png"), (135, "06-open-settled.png"),
        (191, "07-future-pulse-slot.png"), (347, "08-poster-end.png"),
    ):
        await evaluate(f"window.__duo.setReviewFrame({frame})")
        await asyncio.sleep(0.1)
        evidence[name] = await screenshot(name)
        key_states[name] = json.loads(await evaluate("JSON.stringify(window.__duo.state)"))
    (OUTPUT / "keyframe-states.json").write_text(
        json.dumps(key_states, indent=2), encoding="utf-8"
    )
    await evaluate("window.__duo.setRecordingMode(false); window.__duo.setAngle(90)")
    await asyncio.sleep(0.1)
    await screenshot("09-desktop-midfold.png")
    await evaluate("window.__duo.setAngle(180)")
    await asyncio.sleep(0.1)
    await screenshot("10-desktop-open.png")
    await evaluate("window.__duo._phone.rotation.set(0.12,0.38,0)")
    await asyncio.sleep(0.1)
    await screenshot("11-3d-open-shell.png")
    await evaluate("window.__duo.setAngle(0)")
    await asyncio.sleep(0.1)
    await screenshot("12-3d-closed-shell.png")
    await evaluate("window.__duo._phone.rotation.set(0,0,0); window.__duo.setAngle(180)")
    runtime_info = await evaluate("""(() => {
      const r = window.__duo._renderer, gl = r.getContext();
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      const keys = ['YhaSRqOjDUQrQTc','FcJBPLgEScWGyXd','AjfIgUpXxKaENDl','VNIQJMrwFmXgrBf','ejUvJHtjfcqjSvM'];
      const deviceControls = window.__duo._phone.children.filter(m => keys.includes(m.name)).map(m => {
        m.geometry.computeBoundingBox();
        return {name:m.name, min:m.geometry.boundingBox.min.toArray(), max:m.geometry.boundingBox.max.toArray()};
      });
      return {userAgent:navigator.userAgent, renderer:ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        anisotropy:r.capabilities.getMaxAnisotropy(), pixelRatio:r.getPixelRatio(), deviceControls};
    })()""")
    (OUTPUT / "renderer-info.json").write_text(json.dumps(runtime_info, indent=2), encoding="utf-8")
    if not EVIDENCE_ONLY:
        (OUTPUT / "runtime-state.json").write_text(
            json.dumps(final_state, indent=2), encoding="utf-8"
        )
    (OUTPUT / "evidence-frames.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    (OUTPUT / "console-errors.json").write_text(
        json.dumps(errors, indent=2), encoding="utf-8"
    )
    if errors:
        raise RuntimeError(f"console/runtime errors: {errors[:3]}")
    print(json.dumps({"output": str(OUTPUT), "frames": evidence, "rect": rect}))


if __name__ == "__main__":
    asyncio.run(main())
