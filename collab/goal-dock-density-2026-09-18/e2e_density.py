"""Dock density & occlusion — CDP verification.

Checks: slim dock metrics, exclusive panels, floating body (dock height constant),
outside-click / Esc close, guide switch, small viewport sheet fit, recording mode,
console errors.

Usage: uv run --no-project --python 3.12 --with websockets python e2e_density.py [url] [prefix] [WxH]
"""
import asyncio
import base64
import json
import sys
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-dock-density-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "dens"
VIEW = (int(sys.argv[3].split("x")[0]), int(sys.argv[3].split("x")[1])) if len(sys.argv) > 3 else (1440, 900)


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
        return (await fut).get("result", {})

    t = await send("Target.createTarget", {"url": "about:blank"})
    a = await send("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})
    s = a["sessionId"]
    await send("Page.enable", session=s)
    await send("Runtime.enable", session=s)
    await send("Log.enable", session=s)
    await send("Emulation.setDeviceMetricsOverride", {"width": VIEW[0], "height": VIEW[1], "deviceScaleFactor": 1, "mobile": False}, session=s)
    await send("Page.navigate", {"url": URL}, session=s)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=s)
        if "exceptionDetails" in r:
            return f"JS-ERROR: {r['exceptionDetails'].get('text')}"
        return r.get("result", {}).get("value")

    async def wait(expr, timeout=30):
        for _ in range(int(timeout * 5)):
            if await ev(expr):
                return True
            await asyncio.sleep(0.2)
        return False

    async def shot(name):
        d = await send("Page.captureScreenshot", {"format": "png"}, session=s)
        with open(EVIDENCE + "\\" + name + ".png", "wb") as f:
            f.write(base64.b64decode(d["data"]))
        print("saved", name)

    async def upload(sel, path):
        doc = await send("DOM.getDocument", {"depth": -1}, session=s)
        node = await send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": sel}, session=s)
        await send("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [path]}, session=s)
        await ev("document.querySelector('" + sel + "').dispatchEvent(new Event('change', {bubbles: true}))")

    dock_h = "document.querySelector('.control-dock').offsetHeight"
    print("ready:", await wait("window.__duo && window.__duo.state.ready === true", 60))
    await asyncio.sleep(0.5)
    h0 = await ev(dock_h)
    print("dock height closed:", h0, "badge:", await ev("document.querySelector('#build-version-badge')?.textContent"))
    await shot(f"{PREFIX}_1_initial")

    # open Setup -> floating body, dock height unchanged
    await ev("document.querySelector('#setup-panel summary').click()")
    await asyncio.sleep(0.4)
    h1 = await ev(dock_h)
    print("dock height with Setup open:", h1, "(must equal closed)")
    await shot(f"{PREFIX}_2_setup_open")

    # exclusive: open Quality -> Setup closes
    await ev("document.querySelector('#master-pair-qa-panel summary').click()")
    await asyncio.sleep(0.4)
    print("exclusive:", await ev("JSON.stringify({setup: document.querySelector('#setup-panel').open, quality: document.querySelector('#master-pair-qa-panel').open})"))
    await shot(f"{PREFIX}_3_quality_open")

    # outside click closes
    await ev("document.querySelector('#viewport').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    await asyncio.sleep(0.3)
    print("after outside click, any open:", await ev("[...document.querySelectorAll('details.stage-panel')].some(d => d.open)"))

    # Esc closes
    await ev("document.querySelector('#recording-editing-panel summary').click()")
    await asyncio.sleep(0.3)
    await send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session=s)
    await send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session=s)
    await asyncio.sleep(0.3)
    print("after Esc, any open:", await ev("[...document.querySelectorAll('details.stage-panel')].some(d => d.open)"))

    # upload masters + guide switch
    await upload("#ui-upload", A_IMG)
    await wait("window.__duo.state.customReady.reality === true", 30)
    await upload("#redblack-upload", B_IMG)
    print("redblack:", await wait("window.__duo.state.customReady.redblack === true", 30))
    g0 = await ev("document.querySelector('#record-guide-toggle').getAttribute('aria-checked')")
    await ev("document.querySelector('#record-guide-toggle').click()")
    g1 = await ev("document.querySelector('#record-guide-toggle').getAttribute('aria-checked')")
    print("guide switch:", g0, "->", g1)
    await ev("document.querySelector('#record-guide-toggle').click()")
    print("guide restore:", await ev("document.querySelector('#record-guide-toggle').getAttribute('aria-checked')"))
    await shot(f"{PREFIX}_4_masters")

    # sheet fits viewport?
    await ev("document.querySelector('#export-acceptance-panel summary').click()")
    await asyncio.sleep(0.4)
    fit = await ev("(() => { const b = document.querySelector('#export-acceptance-panel .edit-panel-body').getBoundingClientRect(); return JSON.stringify({top: Math.round(b.top), bottom: Math.round(b.bottom), vh: innerHeight, fits: b.top >= 0 && b.bottom <= innerHeight}); })()")
    print("export sheet fit:", fit)
    await shot(f"{PREFIX}_5_accept_open")

    print("console errors:", len(console_errors), console_errors[:5])
    await send("Target.closeTarget", {"targetId": t["targetId"]})


asyncio.run(main())
