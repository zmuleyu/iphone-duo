"""Quick impact + stage3 verification after impact punch-up."""
import asyncio
import base64
import json
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-lv3-transition-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\T0B_final\A_open_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\T0B_final\B_open_2670x1878.png"
URL = "http://127.0.0.1:8766/"
logs = []


class CDP:
    def __init__(self):
        self.id = 0
        self.pending = {}

    async def connect(self):
        version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
        self.ws = await websockets.connect(version["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
        asyncio.create_task(self._reader())
        t = await self.send("Target.createTarget", {"url": "about:blank"}, session=False)
        a = await self.send("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True}, session=False)
        self.session = a["sessionId"]

    async def send(self, method, params=None, session=True):
        self.id += 1
        msg = {"id": self.id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = self.session
        fut = asyncio.get_event_loop().create_future()
        self.pending[self.id] = fut
        await self.ws.send(json.dumps(msg))
        r = await fut
        if "error" in r:
            raise RuntimeError(r["error"])
        return r.get("result", {})

    async def _reader(self):
        async for raw in self.ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in self.pending:
                self.pending.pop(m["id"]).set_result(m)
            elif m.get("method") == "Runtime.consoleAPICalled":
                logs.append((m["params"]["type"], " ".join(str(a.get("value", "")) for a in m["params"]["args"])))

    async def evaluate(self, expr):
        r = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("value")

    async def wait_expr(self, expr, timeout=30):
        for _ in range(int(timeout * 5)):
            if await self.evaluate(expr):
                return True
            await asyncio.sleep(0.2)
        return False

    async def shot(self, name):
        d = await self.send("Page.captureScreenshot", {"format": "png"})
        with open(f"{EVIDENCE}\\{name}.png", "wb") as f:
            f.write(base64.b64decode(d["data"]))
        print("saved", name, flush=True)

    async def upload(self, selector, path):
        doc = await self.send("DOM.getDocument", {"depth": -1})
        node = await self.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": selector})
        await self.send("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [path]})
        await self.evaluate(f"document.querySelector('{selector}').dispatchEvent(new Event('change', {{bubbles: true}}))")


async def main():
    cdp = CDP()
    await cdp.connect()
    await cdp.send("Page.enable")
    await cdp.send("Runtime.enable")
    await cdp.send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    await cdp.send("Page.navigate", {"url": URL})
    assert await cdp.wait_expr("window.__duo && window.__duo.state.ready === true", 45)
    await cdp.upload("#ui-upload", A_IMG)
    await cdp.wait_expr("window.__duo.state.customReady.reality === true", 20)
    await cdp.upload("#redblack-upload", B_IMG)
    await cdp.wait_expr("window.__duo.state.customReady.redblack === true", 20)
    await asyncio.sleep(0.5)

    await cdp.evaluate("window.__duo.setAngle(100); window.__duo.setStages(1,1,1)")
    await asyncio.sleep(0.4)
    await cdp.evaluate("window.__duo.setImpact(1)")
    await asyncio.sleep(0.4)
    await cdp.shot("impact_v2")
    await cdp.evaluate("window.__duo.setImpact(0)")
    await asyncio.sleep(0.4)
    await cdp.shot("impact_v2_off")
    errs = [l for l in logs if l[0] == "error"]
    print("console errors:", len(errs), errs[:5])


asyncio.run(main())
