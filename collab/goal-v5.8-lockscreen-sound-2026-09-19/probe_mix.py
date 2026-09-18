"""Probe: sample __duo.state.angle + worldMix during a record run (ground truth for red timing)."""
import asyncio
import json
import urllib.request

import websockets

A_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"

async def main():
    v = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
    ws = await websockets.connect(v["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
    pend = {}
    mid = [0]

    async def reader():
        async for raw in ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in pend:
                pend.pop(m["id"]).set_result(m)

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
        mid[0] += 1
        msg = {"id": mid[0], "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        fut = asyncio.get_event_loop().create_future()
        pend[mid[0]] = fut
        await ws.send(json.dumps(msg))
        return (await fut).get("result", {})

    t = await send("Target.createTarget", {"url": "about:blank"})
    a = await send("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})
    session = a["sessionId"]
    await send("Page.enable", session=session)
    await send("Runtime.enable", session=session)
    await send("Emulation.setDeviceMetricsOverride",
               {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, session=session)
    await send("Page.bringToFront", session=session)
    await send("Page.navigate", {"url": "http://127.0.0.1:8766/?cap=1&n=probe1"}, session=session)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=session)
        return r.get("result", {}).get("value")

    async def upload(sel, path):
        doc = await send("DOM.getDocument", session=session)
        node = await send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": sel}, session=session)
        await send("DOM.setFileInputFiles", {"files": [path], "nodeId": node["nodeId"]}, session=session)
        n = await ev(f"document.querySelector('{sel}').files.length")
        await ev(f"document.querySelector('{sel}').dispatchEvent(new Event('change', {{ bubbles: true }}))")
        return n

    for i in range(200):
        if await ev("window.__duo && window.__duo.state.ready === true"):
            break
        await asyncio.sleep(0.2)
    print("ready after", i, flush=True)
    print("uploads:", await upload("#ui-upload", A_IMG), await upload("#redblack-upload", B_IMG))
    for _ in range(200):
        if await ev("window.__duo.state.customReady.redblack === true"):
            break
        await asyncio.sleep(0.2)
    await ev("window.__duo.setFoldMotion({ openHold: 2.5 })")
    await ev("document.querySelector('[data-record-format=\"16x9\"]').click()")
    await ev("document.querySelector('[data-record-fps=\"60\"]').click()")
    await ev("document.querySelector('#enter-recording-mode').click()")
    await asyncio.sleep(0.5)
    await send("Page.bringToFront", session=session)
    await ev("document.querySelector('#record-start').click()")
    rows = []
    for i in range(60):
        st = await ev("({a: window.__duo.state.angle, m: window.__duo.state.worldMix})")
        if st:
            rows.append((i * 0.05, st["a"], st["m"]))
        if st and st.get("a", 0) >= 179.9 and i > 30:
            break
        await asyncio.sleep(0.05)
    for t0, ang, mix in rows:
        print(f"~{t0:4.2f}s angle={ang:6.1f} mix={mix:.3f}")
    await send("Target.closeTarget", {"targetId": t["targetId"]})

asyncio.run(main())
