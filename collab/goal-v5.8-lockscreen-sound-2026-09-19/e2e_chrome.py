"""V5.7 screen chrome verification: ?ui=1 paints iOS status bar into world canvases.

Frames: open (180°) chrome on, closed (0°) chrome on cover, open chrome OFF
(baseline), toggle ON at runtime via setScreenChrome.
"""
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

import websockets

GOAL = Path(__file__).parent  # V5.8 copy: lock-screen chrome verification
EVIDENCE = GOAL / "evidence"
EVIDENCE.mkdir(exist_ok=True)
A_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"

async def boot(url):
    version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=8).read())
    ws = await websockets.connect(version["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
    pending = {}
    mid = [0]
    errs = []

    async def reader():
        async for raw in ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in pending:
                pending.pop(msg["id"]).set_result(msg)
            elif msg.get("method") == "Runtime.consoleAPICalled" and msg["params"].get("type") == "error":
                errs.append(str(msg["params"].get("args"))[:200])

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
        mid[0] += 1
        payload = {"id": mid[0], "method": method, "params": params or {}}
        if session:
            payload["sessionId"] = session
        fut = asyncio.get_event_loop().create_future()
        pending[mid[0]] = fut
        await ws.send(json.dumps(payload))
        return (await fut).get("result", {})

    target = await send("Target.createTarget", {"url": "about:blank"})
    attach = await send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
    session = attach["sessionId"]
    await send("Page.enable", session=session)
    await send("Runtime.enable", session=session)
    await send("Emulation.setDeviceMetricsOverride",
               {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, session=session)
    await send("Page.navigate", {"url": url}, session=session)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=session)
        if "exceptionDetails" in r:
            return "JS-ERROR: " + str(r["exceptionDetails"].get("exception", {}).get("description"))[:200]
        return r.get("result", {}).get("value")

    async def shot(name):
        data = (await send("Page.captureScreenshot", {"format": "png"}, session=session))["data"]
        (EVIDENCE / f"{name}.png").write_bytes(base64.b64decode(data))
        print("saved", name)

    async def upload(sel, path):
        doc = await send("DOM.getDocument", session=session)
        node = await send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": sel}, session=session)
        await send("DOM.setFileInputFiles", {"files": [path], "nodeId": node["nodeId"]}, session=session)
        await ev(f"document.querySelector('{sel}').dispatchEvent(new Event('change', {{ bubbles: true }}))")

    for _ in range(300):
        if await ev("window.__duo && window.__duo.state.ready === true"):
            break
        await asyncio.sleep(0.2)
    await upload("#ui-upload", A_IMG)
    for _ in range(150):
        if await ev("window.__duo.state.customReady.reality === true"):
            break
        await asyncio.sleep(0.2)
    await upload("#redblack-upload", B_IMG)
    for _ in range(150):
        if await ev("window.__duo.state.customReady.redblack === true"):
            break
        await asyncio.sleep(0.2)
    return ws, send, ev, shot, target, errs

async def main():
    # Pass 1: ?ui=1 — chrome on from the start
    ws, send, ev, shot, target, errs = await boot("http://127.0.0.1:8766/?ui=1&n=chr1")
    await ev("window.__duo.setAngle(180)")
    await asyncio.sleep(0.35)
    await shot("chrome_open_on")
    await ev("window.__duo.setAngle(0)")
    await asyncio.sleep(0.35)
    await shot("chrome_closed_on")
    print("pass1 console errors:", len(errs))
    await send("Target.closeTarget", {"targetId": target["targetId"]})
    await ws.close()

    # Pass 2: no ?ui — baseline off, then toggle on at runtime
    ws, send, ev, shot, target, errs = await boot("http://127.0.0.1:8766/?n=chr2")
    await ev("window.__duo.setAngle(180)")
    await asyncio.sleep(0.35)
    await shot("chrome_open_off")
    print("toggle:", await ev("window.__duo.setScreenChrome(true)"))
    await asyncio.sleep(0.3)
    await shot("chrome_open_toggled")
    print("pass2 console errors:", len(errs))
    await send("Target.closeTarget", {"targetId": target["targetId"]})
    await ws.close()

asyncio.run(main())
