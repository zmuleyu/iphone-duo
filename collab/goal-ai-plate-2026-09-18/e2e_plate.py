"""T3 capture runner: records 3-format masters via in-page ?cap=1 recorder.

Per format (16x9/9x16/1x1, Fast Viral 60fps): upload masters once, enter
Recording Mode, start record, wait recordDone + captureDone, collect webm
(download redirected to delivery dir), grab safe-frame rect for post-crop.

Usage: uv run --no-project --python 3.12 --with websockets python e2e_capture.py [url]
"""
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

import websockets

GOAL = Path(r"D:\projects\creative_group\iphone-duo\collab\goal-ai-plate-2026-09-18")
EVIDENCE = GOAL / "evidence"
DELIVERY = Path(r"C:\Users\Admin\Downloads\duo\交付")
A_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/?cap=1"
FORMATS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["9x16", "16x9"]


async def main():
    DELIVERY.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    v = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
    ws = await websockets.connect(v["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024)
    pend = {}
    mid = [0]
    console_errors = []

    async def reader():
        async for raw in ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in pend:
                pend.pop(m["id"]).set_result(m)
            elif m.get("method") == "Runtime.consoleAPICalled" and m["params"].get("type") == "error":
                console_errors.append(str(m["params"].get("args"))[:200])
            elif m.get("method") == "Log.entryAdded" and m["params"]["entry"].get("level") == "error":
                console_errors.append(m["params"]["entry"].get("text", "")[:200])

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
        mid[0] += 1
        msg = {"id": mid[0], "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        fut = asyncio.get_event_loop().create_future()
        pend[mid[0]] = fut
        await ws.send(json.dumps(msg))
        r = await fut
        if "error" in r:
            print("CDP-ERR", method, r["error"])
        return r.get("result", {})

    await send("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(DELIVERY), "eventsEnabled": True})

    t = await send("Target.createTarget", {"url": "about:blank"})
    a = await send("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})
    s = a["sessionId"]
    await send("Page.enable", session=s)
    await send("Runtime.enable", session=s)
    await send("Log.enable", session=s)
    await send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, session=s)
    await send("Page.navigate", {"url": URL}, session=s)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=s)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            return "JS-ERROR: " + str(d.get("exception", {}).get("description", d.get("text", "")))[:250]
        return r.get("result", {}).get("value")

    async def wait(expr, timeout=40):
        for _ in range(int(timeout * 5)):
            if await ev(expr):
                return True
            await asyncio.sleep(0.2)
        return False

    async def upload(sel, path):
        doc = await send("DOM.getDocument", {"depth": -1}, session=s)
        node = await send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": sel}, session=s)
        await send("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [path]}, session=s)
        await ev("document.querySelector('" + sel + "').dispatchEvent(new Event('change', {bubbles: true}))")

    print("ready:", await wait("window.__duo && window.__duo.state.ready === true", 60))
    await upload("#ui-upload", A_IMG)
    print("reality:", await wait("window.__duo.state.customReady.reality === true", 30))
    await upload("#redblack-upload", B_IMG)
    print("redblack:", await wait("window.__duo.state.customReady.redblack === true", 30))
    # AI plate: extend open hold to 2.5s so post-open AI effects have room.
    await ev("window.__duo.setFoldMotion({ openHold: 2.5 })")
    print("openHold extended for plate")

    rects = {}
    for fmt in FORMATS:
        await ev(f"document.querySelector('[data-record-format=\"{fmt}\"]').click()")
        await asyncio.sleep(0.2)
        await ev("document.querySelector('#enter-recording-mode').click()")
        await asyncio.sleep(0.4)
        rects[fmt] = await ev("(() => { const r = document.querySelector('#record-safe-frame').getBoundingClientRect(); return JSON.stringify({x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}); })()")
        await send('Page.bringToFront', session=s)  # unthrottle rAF: background tabs drop capture frames
        await asyncio.sleep(0.2)
        await ev("document.querySelector('#record-start').click()")
        done = await wait("document.documentElement.dataset.recordDone === '1'", 30)
        capd = await wait("document.documentElement.dataset.captureDone === '1'", 15)
        print(f"{fmt}: recordDone={done} captureDone={capd} rect={rects[fmt]}")
        await ev("document.querySelector('#record-exit').click()")
        await asyncio.sleep(0.4)
        # reset captureDone for next run
        await ev("delete document.documentElement.dataset.captureDone; delete document.documentElement.dataset.recordDone;")

    print("console errors:", len(console_errors), console_errors[:5])
    scale = await ev("(() => { const c = document.querySelector('#viewport canvas'); return c.width / c.clientWidth; })()")
    (GOAL / "safe_rects.json").write_text(json.dumps({"captureScale": scale, "rects": rects}, indent=2), encoding="utf-8")
    await send("Target.closeTarget", {"targetId": t["targetId"]})
    print("delivery dir:", DELIVERY)


asyncio.run(main())
