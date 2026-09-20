"""Render 348 fixed-step Tokyo v6.20 PNG frames via synchronous CDP readback."""

import asyncio
import base64
import json
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

import websockets


URL = sys.argv[1] if len(sys.argv) > 1 else (
    "http://127.0.0.1:8770/?cap=1&tokyo=v620&nofx=1&motion=tokyo-demo"
    "&timeline=tokyo&format=16x9&closedUi=0&openUi=1"
)
OUTPUT = (
    Path(sys.argv[2])
    if len(sys.argv) > 2
    else Path.cwd() / "artifacts" / "v6.20-tokyo-silent-demo"
).resolve()


async def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    version = json.loads(
        urllib.request.urlopen("http://127.0.0.1:9230/json/version", timeout=5).read()
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
    # Settle the one-time mode layout / ResizeObserver before frame zero.
    # This wait does not advance authored time: every frame is sampled below.
    await asyncio.sleep(.4)
    if '--calibration-only' in sys.argv:
        for frame, name in [(0, 'calibration-closed-a.png'), (347, 'calibration-open-a.png')]:
            png = await evaluate(f"window.__duo.renderReviewFrame({frame}, true)")
            (OUTPUT / name).write_bytes(base64.b64decode(png.split(',', 1)[1]))
        print(json.dumps({'calibration':str(OUTPUT),'errors':errors}))
        await websocket.close()
        return
    if '--profile-check' in sys.argv:
        differences = {}
        from PIL import Image, ImageChops
        import io
        for frame in [12,91,138,191,347]:
            png = await evaluate(f"window.__duo.renderReviewFrame({frame})")
            data = base64.b64decode(png.split(',',1)[1])
            (OUTPUT / f'legacy_{frame:06d}.png').write_bytes(data)
            expected = Image.open(Path.cwd()/f'artifacts/v6.19-tokyo-silent-demo/frames/frame_{frame:06d}.png').convert('RGB')
            actual = Image.open(io.BytesIO(data)).convert('RGB')
            diff = ImageChops.difference(expected,actual)
            differences[str(frame)] = {'maxChannelDelta':max(v[1] for v in diff.getextrema()),'changedBox':diff.getbbox()}
        (OUTPUT/'v619-regression.json').write_text(json.dumps(differences,indent=2),encoding='utf-8')
        print(json.dumps(differences))
        await websocket.close()
        return
    frames_dir = OUTPUT / 'frames'
    frames_dir.mkdir(exist_ok=True)
    if list(frames_dir.glob('frame_*.png')):
        raise RuntimeError('Frame output already exists; choose a fresh run directory')
    ledger = []
    key_states = {}
    keys = {12:'01-closed',91:'02-mid-fold',143:'03-open-dark',163:'04-windows-mid',
            180:'05-buildings-on',196:'06-tower-mid',211:'07-hero',347:'08-end'}
    for frame in range(348):
        png = await evaluate(f"window.__duo.renderReviewFrame({frame})")
        data = base64.b64decode(png.split(',', 1)[1])
        filename = f'frame_{frame:06d}.png'
        (frames_dir / filename).write_bytes(data)
        state = await evaluate("window.__duo.state")
        if state['recordingMode']['frame'] != frame:
            raise RuntimeError(f'Frame clock mismatch at {frame}')
        layers = state['layeredTokyo']
        ledger.append({'frame':frame,'time':frame/60,'angle':state['angle'],
                       'layers':layers,'sha256':hashlib.sha256(data).hexdigest()})
        if frame in keys:
            shutil.copyfile(frames_dir / filename, OUTPUT / f'{keys[frame]}.png')
            key_states[str(frame)] = state
        if frame % 60 == 0:
            print(f'rendered {frame}/348', flush=True)
    final_state = await evaluate('window.__duo.state')
    for frame, name in [(0, 'calibration-closed-a.png'),(347,'calibration-open-a.png')]:
        png = await evaluate(f"window.__duo.renderReviewFrame({frame}, true)")
        (OUTPUT / name).write_bytes(base64.b64decode(png.split(',',1)[1]))
    await evaluate("window.__duo.setRecordingMode(false); window.__duo.setAngle(0)")
    await asyncio.sleep(.1)
    await screenshot('desktop-closed.png')
    await evaluate("window.__duo.setAngle(180)")
    await asyncio.sleep(.1)
    await screenshot('desktop-open.png')
    await evaluate("window.__duo._phone.rotation.set(0.18,0.42,0)")
    await asyncio.sleep(.1)
    await screenshot('shell-open.png')
    await evaluate("window.__duo.setAngle(0)")
    await asyncio.sleep(.1)
    await screenshot('shell-closed.png')
    await evaluate("window.__duo._phone.rotation.set(0,0,0); window.__duo.setAngle(180)")
    info = await evaluate("""(() => {
      const r=window.__duo._renderer, gl=r.getContext(), e=gl.getExtension('WEBGL_debug_renderer_info');
      const names=['YhaSRqOjDUQrQTc','FcJBPLgEScWGyXd','AjfIgUpXxKaENDl'];
      return {browser:navigator.userAgent,gpu:e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
        anisotropy:r.capabilities.getMaxAnisotropy(),pixelRatio:r.getPixelRatio(),
        controls:window.__duo._phone.children.filter(m=>names.includes(m.name)).map(m=>{
          m.geometry.computeBoundingBox();return {name:m.name,min:m.geometry.boundingBox.min.toArray(),max:m.geometry.boundingBox.max.toArray()};
        })};
    })()""")
    for name, content in [('frame-ledger.json',ledger),('runtime-state.json',final_state),
                          ('keyframe-states.json',key_states),('console-errors.json',errors),
                          ('renderer-info.json',info)]:
        (OUTPUT / name).write_text(json.dumps(content,indent=2),encoding='utf-8')
    if errors:
        raise RuntimeError(f'console/runtime errors: {errors[:3]}')
    print(json.dumps({'output':str(OUTPUT),'frames':len(ledger),'consoleErrors':len(errors)}))
    await websocket.close()


if __name__ == '__main__':
    asyncio.run(main())
