"""Capture the ORIGINAL chuspeeism build at the same angles with the same calibration image."""
import asyncio
import base64
import json
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-v44-screen-shader-rebuild-2026-09-18\evidence"
CALIBRATION = EVIDENCE + r"\calibration.png"
URL = "http://127.0.0.1:8767/"


class CDP:
    def __init__(self):
        self.id = 0
        self.pending = {}

    async def connect(self):
        version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
        self.ws = await websockets.connect(version["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
        asyncio.create_task(self._reader())
        target = await self.send("Target.createTarget", {"url": "about:blank"}, session=False)
        attached = await self.send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}, session=False)
        self.session = attached["sessionId"]

    async def send(self, method, params=None, session=True):
        self.id += 1
        msg = {"id": self.id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = getattr(self, "session", None)
        fut = asyncio.get_event_loop().create_future()
        self.pending[self.id] = fut
        await self.ws.send(json.dumps(msg))
        result = await fut
        if "error" in result:
            raise RuntimeError(f"{method}: {result['error']}")
        return result.get("result", {})

    async def _reader(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self.pending:
                self.pending.pop(msg["id"]).set_result(msg)

    async def evaluate(self, expr):
        result = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return result.get("result", {}).get("value")

    async def shot(self, name):
        data = await self.send("Page.captureScreenshot", {"format": "png"})
        with open(f"{EVIDENCE}\\{name}.png", "wb") as f:
            f.write(base64.b64decode(data["data"]))
        print("saved", name, flush=True)


async def main():
    cdp = CDP()
    await cdp.connect()
    await cdp.send("Page.enable")
    await cdp.send("Runtime.enable")
    await cdp.send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    await cdp.send("Page.navigate", {"url": URL})
    for _ in range(150):
        if await cdp.evaluate("document.querySelector('#play') && !document.querySelector('#play').disabled"):
            break
        await asyncio.sleep(0.2)
    await asyncio.sleep(1)

    doc = await cdp.send("DOM.getDocument", {"depth": -1})
    node = await cdp.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": "#ui-upload"})
    await cdp.send("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [CALIBRATION]})
    await cdp.evaluate("document.querySelector('#ui-upload').dispatchEvent(new Event('change', {bubbles: true}))")
    await asyncio.sleep(1.5)

    for label, deg in [("35", 63), ("50", 90), ("70", 126)]:
        await cdp.evaluate(f"(() => {{ const s = document.querySelector('#angle'); s.value = {deg}; s.dispatchEvent(new Event('input', {{bubbles: true}})); }})()")
        await asyncio.sleep(0.6)
        await cdp.shot(f"orig_{label}")


asyncio.run(main())
