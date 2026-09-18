"""Production play-path verification with foreground tab (rAF unthrottled)."""
import asyncio
import base64
import json
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-control-dock-ia-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
URL = "https://iphone-duo-lv3.vercel.app/"


async def main():
    v = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
    ws = await websockets.connect(v["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
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
    await send("Page.navigate", {"url": URL}, session=s)
    await send("Page.bringToFront", session=s)

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

    async def shot(name):
        d = await send("Page.captureScreenshot", {"format": "png"}, session=s)
        with open(EVIDENCE + "\\" + name + ".png", "wb") as f:
            f.write(base64.b64decode(d["data"]))
        print("saved", name)

    print("ready:", await wait("window.__duo && window.__duo.state.ready === true", 60))
    await upload("#ui-upload", A_IMG)
    await wait("window.__duo.state.customReady.reality === true", 30)
    await upload("#redblack-upload", B_IMG)
    print("redblack:", await wait("window.__duo.state.customReady.redblack === true", 30))
    await send("Page.bringToFront", session=s)
    await ev("window.__duo.play()")
    await asyncio.sleep(1.15)
    print("mid:", await ev("JSON.stringify({angle: window.__duo.state.angle, bubble: document.querySelector('#angle-bubble').textContent, playhead: document.querySelector('#sequence-playhead').style.left})"))
    await shot("prod_dock_4b_midplay")
    ok = await wait("window.__duo.state.angle >= 180", 20)
    print("reached open:", ok)
    await asyncio.sleep(0.4)
    print("final:", await ev("JSON.stringify({angle: window.__duo.state.angle, readout: document.querySelector('#angle-readout').textContent})"))
    await shot("prod_dock_5b_open")
    print("console errors:", len(console_errors), console_errors[:3])
    await send("Target.closeTarget", {"targetId": t["targetId"]})


asyncio.run(main())
