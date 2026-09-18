"""V5.6 bezel light verification: angle-keyed frames + open pop capture.

Drives __duo.setAngle() at 20/60/110/160, then plays to capture the open
pop within its decay window. Screenshots to evidence/bezel_*.png.
"""
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/"
GOAL = Path(__file__).parent
EVIDENCE = GOAL / "evidence"
EVIDENCE.mkdir(exist_ok=True)
A_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"

async def main():
    version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=8).read())
    ws = await websockets.connect(version["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
    pending = {}
    mid = [0]
    console_errors = []

    async def reader():
        async for raw in ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in pending:
                pending.pop(msg["id"]).set_result(msg)
            elif msg.get("method") == "Runtime.consoleAPICalled" and msg["params"].get("type") == "error":
                console_errors.append(str(msg["params"].get("args"))[:300])
            elif msg.get("method") == "Page.javascriptDialogOpening":
                asyncio.create_task(send("Page.handleJavaScriptDialog", {"accept": True}, session=msg.get("sessionId")))

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
    await send("Page.navigate", {"url": BASE}, session=session)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=session)
        if "exceptionDetails" in r:
            return "JS-ERROR: " + str(r["exceptionDetails"].get("exception", {}).get("description"))[:240]
        return r.get("result", {}).get("value")

    async def wait(flag, timeout=90):
        for _ in range(int(timeout * 5)):
            if await ev(f"window.__duo && window.__duo.state.{flag} === true"):
                return True
            await asyncio.sleep(0.2)
        return False

    async def upload(sel, path):
        doc = await send("DOM.getDocument", session=session)
        node = await send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": sel}, session=session)
        await send("DOM.setFileInputFiles", {"files": [path], "nodeId": node["nodeId"]}, session=session)
        await ev(f"document.querySelector('{sel}').dispatchEvent(new Event('change', {{ bubbles: true }}))")

    async def shot(name):
        data = (await send("Page.captureScreenshot", {"format": "png"}, session=session))["data"]
        (EVIDENCE / f"{name}.png").write_bytes(base64.b64decode(data))
        print("saved", name)

    assert await wait("ready"), "ready timeout"
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
    print("redblack:", await ev("window.__duo.state.customReady.redblack === true"))

    for ang, tag in [(45, "a045"), (75, "a075"), (130, "a130"), (160, "a160")]:
        await ev(f"window.__duo.setAngle({ang})")
        await asyncio.sleep(0.35)
        await shot(f"bezel_{tag}")

    # Open pop: manual crossing fires uBezelPop; slower decay keeps it visible.
    await ev("window.__duo.setAngle(179)")
    await asyncio.sleep(0.3)
    await ev("window.__duo.setAngle(180)")
    await asyncio.sleep(0.12)
    await shot("bezel_pop")
    print("pop captured: manual-cross")
    await asyncio.sleep(1.2)
    await shot("bezel_open_settled")
    print("console errors:", len(console_errors), console_errors[:4])
    await send("Target.closeTarget", {"targetId": target["targetId"]})

asyncio.run(main())
