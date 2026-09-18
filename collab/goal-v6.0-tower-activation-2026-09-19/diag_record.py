"""V6.0 diag: why recordDone never fires — poll state through a record attempt."""
import asyncio
import json
import urllib.request

import websockets

A_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Graphic_2670x1878.png"

async def main():
    v = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
    ws = await websockets.connect(v["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
    pend = {}
    mid = [0]
    errors = []

    async def reader():
        async for raw in ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in pend:
                pend.pop(m["id"]).set_result(m)
            elif m.get("method") == "Runtime.exceptionThrown":
                errors.append(str(m["params"])[:300])
            elif m.get("method") == "Runtime.consoleAPICalled" and m["params"].get("type") == "error":
                errors.append(str(m["params"].get("args"))[:200])

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
    for dom in ("Page", "Runtime", "DOM"):
        await send(f"{dom}.enable", session=s)
    await send("Page.bringToFront", session=s)
    await send("Page.navigate", {"url": "http://127.0.0.1:8766/?cap=1&n=v60diag"}, session=s)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=s)
        if "exceptionDetails" in r:
            return "EXC: " + str(r["exceptionDetails"])[:200]
        return r.get("result", {}).get("value")

    for _ in range(100):
        if await ev("window.__duo && window.__duo.state.ready === true") is True:
            break
        await asyncio.sleep(0.2)
    print("ready ok")

    async def upload(sel, path):
        d = await send("DOM.getDocument", session=s)
        n = await send("DOM.querySelector", {"nodeId": d["root"]["nodeId"], "selector": sel}, session=s)
        await send("DOM.setFileInputFiles", {"files": [path], "nodeId": n["nodeId"]}, session=s)
        n_files = await ev(f"document.querySelector('{sel}').files.length")
        print(sel, "files:", n_files)
        await ev(f"document.querySelector('{sel}').dispatchEvent(new Event('change'))")

    await upload("#file-a", A_IMG)
    for _ in range(100):
        if await ev("window.__duo.state.customReady && window.__duo.state.customReady.reality === true"):
            break
        await asyncio.sleep(0.2)
    print("reality ready:", await ev("JSON.stringify(window.__duo.state.customReady)"))
    await upload("#file-b", B_IMG)
    for _ in range(200):
        if await ev("window.__duo.state.customReady && window.__duo.state.customReady.redblack === true"):
            break
        await asyncio.sleep(0.2)
    print("redblack ready:", await ev("JSON.stringify(window.__duo.state.customReady)"))

    await ev("window.__duo.setFoldMotion({ openHold: 2.5 })")
    await ev("document.querySelector('[data-record-format=\"16x9\"]').click()")
    await ev("document.querySelector('#enter-recording-mode').click()")
    await asyncio.sleep(0.5)
    r = await ev("document.querySelector('#record-start').click(); 'clicked'")
    print("record-start:", r)
    for i in range(24):
        st = await ev("JSON.stringify({a: window.__duo.state.angle, rd: document.documentElement.dataset.recordDone, cd: document.documentElement.dataset.captureDone, rec: window.__duo.state.recording})")
        print(i, st)
        await asyncio.sleep(0.5)
    print("errors:", errors[:4])
    await send("Target.closeTarget", {"targetId": t["targetId"]})

asyncio.run(main())