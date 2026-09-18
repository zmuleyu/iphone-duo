"""Pure-A (worldMix=0) master-pair frame at 126 degrees."""
import asyncio
import base64
import json
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-lv3-transition-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"


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
    s = a["sessionId"]
    await send("Page.enable", session=s)
    await send("Runtime.enable", session=s)
    await send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, session=s)
    await send("Page.navigate", {"url": "http://127.0.0.1:8766/"}, session=s)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=s)
        return r.get("result", {}).get("value")

    async def wait(expr, timeout=30):
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

    await wait("window.__duo && window.__duo.state.ready === true", 45)
    await upload("#ui-upload", A_IMG)
    await wait("window.__duo.state.customReady.reality === true", 20)
    await upload("#redblack-upload", B_IMG)
    await wait("window.__duo.state.customReady.redblack === true", 20)
    await asyncio.sleep(0.5)
    await ev("window.__duo.setWorldMix(0)")
    await ev("window.__duo.setAngle(126)")
    print("state:", await ev("JSON.stringify(window.__duo.state)"))
    await asyncio.sleep(0.5)
    d = await send("Page.captureScreenshot", {"format": "png"}, session=s)
    with open(EVIDENCE + "\\master_pureA_70.png", "wb") as f:
        f.write(base64.b64decode(d["data"]))
    print("saved master_pureA_70")


asyncio.run(main())
