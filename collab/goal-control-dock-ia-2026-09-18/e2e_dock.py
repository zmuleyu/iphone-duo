"""Control Dock IA rework — CDP verification.

Covers: initial layout, masters upload + stage nodes, snap tick jump,
play mid-flight (bubble/playhead), open state, accordion open span,
Recording Mode exclusivity (G3), exit restore, console errors.

Usage: uv run --no-project --python 3.12 --with websockets python e2e_dock.py [url] [prefix]
"""
import asyncio
import base64
import json
import sys
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-control-dock-ia-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_Closed_Silhouette_DRAFT_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\新建文件夹\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "dock"


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
    await send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, session=s)
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

    print("ready:", await wait("window.__duo && window.__duo.state.ready === true", 60))
    await asyncio.sleep(0.6)
    await shot(f"{PREFIX}_1_initial")
    print("stage@init:", await ev("JSON.stringify({setup: document.querySelector('#setup-panel').className, hudHidden: document.querySelector('#record-hud').hidden, badge: document.querySelector('#build-version-badge')?.textContent})"))

    # snap tick jump (dead infra check) — before masters, slider disabled but snap buttons not?
    print("tick90 disabled?", await ev("document.querySelector('[data-snap=\"90\"]').disabled"))

    # upload masters
    await upload("#ui-upload", A_IMG)
    print("reality:", await wait("window.__duo.state.customReady.reality === true", 30))
    await upload("#redblack-upload", B_IMG)
    print("redblack:", await wait("window.__duo.state.customReady.redblack === true", 30))
    await asyncio.sleep(0.6)
    print("stage@masters:", await ev("JSON.stringify({setup: document.querySelector('#setup-panel').className, quality: document.querySelector('#master-pair-qa-panel').className})"))
    await shot(f"{PREFIX}_2_masters")

    # snap tick jump to 90
    await ev("document.querySelector('[data-snap=\"90\"]').click()")
    await asyncio.sleep(0.5)
    print("angle after tick90:", await ev("window.__duo.state.angle"))
    await shot(f"{PREFIX}_3_tick90")

    # play mid-flight
    await ev("window.__duo.play ? window.__duo.play() : document.querySelector('#play').click()")
    await asyncio.sleep(1.15)
    print("mid:", await ev("JSON.stringify({angle: window.__duo.state.angle, bubble: document.querySelector('#angle-bubble').textContent, playhead: document.querySelector('#sequence-playhead').style.left})"))
    await shot(f"{PREFIX}_4_midplay")
    await wait("window.__duo.state.angle >= 180", 15)
    await asyncio.sleep(0.5)
    await shot(f"{PREFIX}_5_open")

    # accordion: open Quality panel
    await ev("document.querySelector('#master-pair-qa-panel summary').click()")
    await asyncio.sleep(0.4)
    await shot(f"{PREFIX}_6_quality_open")
    await ev("document.querySelector('#master-pair-qa-panel summary').click()")

    # recording mode exclusivity
    await ev("document.querySelector('#recording-editing-panel').open = true")
    await asyncio.sleep(0.3)
    await ev("document.querySelector('#enter-recording-mode').click()")
    await asyncio.sleep(0.5)
    print("recmode:", await ev("JSON.stringify({mode: document.documentElement.dataset.recordingMode || null, hudHidden: document.querySelector('#record-hud').hidden, dockOpacity: getComputedStyle(document.querySelector('.control-dock')).opacity})"))
    await shot(f"{PREFIX}_7_recordmode")
    await ev("document.querySelector('#record-exit').click()")
    await asyncio.sleep(0.5)
    print("after exit:", await ev("JSON.stringify({mode: document.documentElement.dataset.recordingMode || null, hudHidden: document.querySelector('#record-hud').hidden, dockOpacity: getComputedStyle(document.querySelector('.control-dock')).opacity})"))
    await shot(f"{PREFIX}_8_exit")

    print("console errors:", len(console_errors), console_errors[:5])
    await send("Target.closeTarget", {"targetId": t["targetId"]})


asyncio.run(main())
