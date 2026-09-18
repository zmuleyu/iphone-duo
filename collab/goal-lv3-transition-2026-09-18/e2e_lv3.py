"""Lv3 staged transition E2E: regression + deterministic stage frames + live record."""
import asyncio
import base64
import json
import urllib.request

import websockets

EVIDENCE = r"D:\projects\creative_group\iphone-duo\collab\goal-lv3-transition-2026-09-18\evidence"
A_IMG = r"C:\Users\Admin\Downloads\duo\T0B_final\A_open_2670x1878.png"
B_IMG = r"C:\Users\Admin\Downloads\duo\T0B_final\B_open_2670x1878.png"
URL = "http://127.0.0.1:8766/"

console_logs = []


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
            elif msg.get("method") == "Runtime.consoleAPICalled":
                text = " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"])
                console_logs.append((msg["params"]["type"], text))
            elif msg.get("method") == "Log.entryAdded":
                e = msg["params"]["entry"]
                console_logs.append((e["level"], e.get("text", "")))

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
        data = await self.send("Page.captureScreenshot", {"format": "png"})
        with open(f"{EVIDENCE}\\{name}.png", "wb") as f:
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

    if not await cdp.wait_expr("window.__duo && window.__duo.state.ready === true", timeout=45):
        print("FATAL not ready", console_logs[-10:])
        raise SystemExit(1)

    # Upload the T0-B final pair
    await cdp.upload("#ui-upload", A_IMG)
    await cdp.wait_expr("window.__duo.state.customReady.reality === true", timeout=20)
    await cdp.upload("#redblack-upload", B_IMG)
    await cdp.wait_expr("window.__duo.state.customReady.redblack === true", timeout=20)
    await asyncio.sleep(0.6)

    # --- Regression: panorama continuity at 35/50/70 (worldMix forced full A) ---
    await cdp.evaluate("window.__duo.setStages(0,0,0)")
    for label, deg in [("35", 63), ("70", 126)]:
        await cdp.evaluate(f"window.__duo.setAngle({deg})")
        await asyncio.sleep(0.5)
        await cdp.shot(f"regress_{label}")

    # --- Deterministic stage frames at a readable mid-open angle ---
    await cdp.evaluate("window.__duo.setAngle(100)")
    stages = [
        ("stage1_leak",  "window.__duo.setStages(0.45, 0, 0); window.__duo.setImpact(0); window.__duo.setPulse(0)"),
        ("stage2_collapse", "window.__duo.setStages(1, 0.55, 0); window.__duo.setImpact(0)"),
        ("stage3_lock",  "window.__duo.setStages(1, 1, 1); window.__duo.setImpact(0)"),
        ("impact",       "window.__duo.setStages(1, 1, 1); window.__duo.setImpact(1)"),
        ("pulse",        "window.__duo.setStages(1, 1, 1); window.__duo.setImpact(0); window.__duo.setPulse(1)"),
    ]
    for name, js in stages:
        await cdp.evaluate(js)
        await asyncio.sleep(0.45)
        await cdp.shot(name)

    # --- Live record run: verify timeline wiring (t≈1.8 leak frame) ---
    await cdp.evaluate("window.__duo.setImpact(0); window.__duo.setPulse(0); window.__duo.setStages(0,0,0); window.__duo.setAngle(0)")
    await cdp.evaluate("window.__duo.startRecord()")
    await asyncio.sleep(1.8)
    await cdp.shot("record_t1_8")
    st = await cdp.evaluate("JSON.stringify(window.__duo.state)")
    print("state @~1.8s:", st)
    await asyncio.sleep(1.7)  # ~3.5s: post-pulse region
    await cdp.shot("record_t3_5")
    st = await cdp.evaluate("JSON.stringify(window.__duo.state)")
    print("state @~3.5s:", st)
    # wait for done
    await cdp.wait_expr("document.documentElement.dataset.recordDone === '1'", timeout=8)
    print("record done flag OK")
    await cdp.shot("record_final")

    errors = [l for l in console_logs if l[0] in ("error",)]
    warns = [l for l in console_logs if l[0] in ("warning",)]
    print(f"console errors: {len(errors)}, warnings: {len(warns)}")
    for level, text in (errors + warns)[:10]:
        print(f"[{level}] {text[:250]}")


asyncio.run(main())
