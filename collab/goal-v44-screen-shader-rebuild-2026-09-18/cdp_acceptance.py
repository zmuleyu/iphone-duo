"""CDP E2E acceptance for v4.4 — Tests A/B/C/D against localhost:8766."""
import asyncio
import base64
import json
import sys
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-v44-screen-shader-rebuild-2026-09-18\evidence"
CALIBRATION = EVIDENCE + r"\calibration.png"
REALITY = r"C:\Users\Admin\Downloads\iPhone_Duo_ThirdParty_Review_v4.3.1\evidence\source_artwork\Reality.png"
REDBLACK = r"C:\Users\Admin\Downloads\iPhone_Duo_ThirdParty_Review_v4.3.1\evidence\source_artwork\RedBlack.png"
URL = "http://127.0.0.1:8766/"
PREFIX = ""
if len(sys.argv) > 1:
    URL = sys.argv[1]
if len(sys.argv) > 2:
    PREFIX = sys.argv[2]

console_logs = []


class CDP:
    def __init__(self):
        self.id = 0
        self.ws = None
        self.session = None
        self.pending = {}

    async def connect(self):
        version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5).read())
        self.ws = await websockets.connect(version["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
        asyncio.create_task(self._reader())
        target = await self.send("Target.createTarget", {"url": "about:blank"})
        target_id = target["targetId"]
        attached = await self.send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        self.session = attached["sessionId"]

    async def send(self, method, params=None, session=None):
        self.id += 1
        mid = self.id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session or self.session and method.split(".")[0] not in ("Target", "Browser"):
            msg["sessionId"] = session or self.session
        fut = asyncio.get_event_loop().create_future()
        self.pending[mid] = fut
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
            elif msg.get("method") == "Runtime.consoleAPICalled":
                level = msg["params"]["type"]
                text = " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"])
                console_logs.append((level, text))
            elif msg.get("method") == "Log.entryAdded":
                entry = msg["params"]["entry"]
                console_logs.append((entry["level"], entry.get("text", "")))

    async def evaluate(self, expr):
        result = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return result.get("result", {}).get("value")

    async def wait_expr(self, expr, timeout=30):
        for _ in range(int(timeout * 5)):
            if await self.evaluate(expr):
                return True
            await asyncio.sleep(0.2)
        return False

    async def shot(self, name):
        data = await self.send("Page.captureScreenshot", {"format": "png"})
        path = f"{EVIDENCE}\\{PREFIX}{name}.png"
        with open(path, "wb") as f:
            f.write(base64.b64decode(data["data"]))
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
    await cdp.send("Log.enable")
    await cdp.send("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    await cdp.send("Page.navigate", {"url": URL})

    ok = await cdp.wait_expr("window.__duo && window.__duo.state.ready === true", timeout=45)
    if not ok:
        print("FATAL: app not ready"); print(console_logs[-20:]); sys.exit(1)
    print("app ready:", await cdp.evaluate("JSON.stringify(window.__duo.state)"))
    await asyncio.sleep(1)

    # ---- Test A: calibration image, same for both worlds ----
    await cdp.upload("#ui-upload", CALIBRATION)
    await cdp.wait_expr("window.__duo.state.customReady.reality === true", timeout=15)
    await cdp.upload("#redblack-upload", CALIBRATION)
    await cdp.wait_expr("window.__duo.state.customReady.redblack === true", timeout=15)
    await cdp.evaluate("window.__duo.setWorldMix(0)")
    await asyncio.sleep(0.5)
    for label, deg in [("35", 63), ("50", 90), ("70", 126)]:
        await cdp.evaluate(f"window.__duo.setAngle({deg})")
        await asyncio.sleep(0.6)
        await cdp.shot(f"testA_{label}")

    # ---- Test B/C: real artwork, geometry-driven worldMix ----
    await cdp.evaluate("window.__duo.setWorldMix(null)")
    await cdp.upload("#ui-upload", REALITY)
    await cdp.wait_expr("window.__duo.state.customReady.reality === true", timeout=15)
    await cdp.upload("#redblack-upload", REDBLACK)
    await cdp.wait_expr("window.__duo.state.customReady.redblack === true", timeout=15)
    await asyncio.sleep(0.5)
    for label, deg in [("35", 63), ("50", 90), ("70", 126)]:
        await cdp.evaluate(f"window.__duo.setAngle({deg})")
        await asyncio.sleep(0.6)
        await cdp.shot(f"testB_{label}")

    # ---- Test D: worldMix sync at fixed 50% ----
    await cdp.evaluate("window.__duo.setAngle(90)")
    for mix in ["0", "0.5", "1"]:
        await cdp.evaluate(f"window.__duo.setWorldMix({mix})")
        await asyncio.sleep(0.5)
        await cdp.shot(f"testD_mix{mix.replace('.', '_')}")
    await cdp.evaluate("window.__duo.setWorldMix(null)")

    print("final state:", await cdp.evaluate("JSON.stringify(window.__duo.state)"))
    errors = [l for l in console_logs if l[0] in ("error", "warning")]
    print(f"console errors/warnings: {len(errors)}")
    for level, text in errors[:15]:
        print(f"[{level}] {text[:300]}")


asyncio.run(main())
