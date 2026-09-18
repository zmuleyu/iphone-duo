"""Probe: does the compiled screen shader contain uTowerBoost, and does uTowerBoost fire at fold end?"""
import asyncio
import json
import urllib.request

import websockets

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
    await send("Page.navigate", {"url": "http://127.0.0.1:8766/?n=boostprobe"}, session=session)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=session)
        if "exceptionDetails" in r:
            return "JS-ERROR: " + str(r["exceptionDetails"].get("exception", {}).get("description"))[:300]
        return r.get("result", {}).get("value")

    for _ in range(200):
        if await ev("window.__duo && window.__duo.state.ready === true"):
            break
        await asyncio.sleep(0.2)
    print("boost in compiled screen programs:", await ev("""
      (() => {
        const gl = window.__duo._renderer.getContext();
        return window.__duo._renderer.info.programs
          .map(p => { try { return gl.getShaderSource(p.fragmentShader).includes('uTowerBoost'); } catch (e) { return 'err'; } })
          .join(',');
      })()
    """))
    await send("Target.closeTarget", {"targetId": t["targetId"]})

asyncio.run(main())
