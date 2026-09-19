"""P1 probe: inventory phone meshes with bbox + material info; find button-like protrusions."""
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
    s = a["sessionId"]
    for dom in ("Page", "Runtime"):
        await send(f"{dom}.enable", session=s)
    await send("Page.navigate", {"url": "http://127.0.0.1:8766/?nofx=1"}, session=s)

    async def ev(expr):
        r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True}, session=s)
        if "exceptionDetails" in r:
            return "EXC: " + str(r["exceptionDetails"].get("text"))[:150]
        return r.get("result", {}).get("value")

    for _ in range(120):
        if await ev("window.__duo && window.__duo.state.ready === true") is True:
            break
        await asyncio.sleep(0.2)

    out = await ev("""
(() => {
  const phone = window.__duo._phone;
  const THREE_Box3 = new (window.__duo._scene.children[0].position.constructor.name === 'Vector3' ? Object : Object)();
  const rows = [];
  const v = { min: {}, max: {} };
  phone.updateMatrixWorld(true);
  phone.traverse(o => {
    if (!o.isMesh) return;
    o.geometry.computeBoundingBox();
    const bb = o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld);
    const size = { x: +(bb.max.x - bb.min.x).toFixed(2), y: +(bb.max.y - bb.min.y).toFixed(2), z: +(bb.max.z - bb.min.z).toFixed(2) };
    const ctr = { x: +((bb.max.x + bb.min.x) / 2).toFixed(2), y: +((bb.max.y + bb.min.y) / 2).toFixed(2), z: +((bb.max.z + bb.min.z) / 2).toFixed(2) };
    rows.push({ name: o.name || o.parent.name, size, ctr, mat: o.material && o.material.type, color: o.material && o.material.color ? o.material.color.getHexString() : null, metal: o.material && o.material.metalness, rough: o.material && o.material.roughness });
  });
  return rows;
})()
""")
    if isinstance(out, str):
        print(out)
    else:
        import json as _j
        Path_out = r"D:\projects\creative_group\iphone-duo\collab\goal-v6.3-restore-original-2026-09-19\shell_meshes.json"
        with open(Path_out, "w", encoding="utf-8") as fh:
            _j.dump(out, fh, indent=1)
        print(f"{len(out)} meshes -> shell_meshes.json")
        for r in out:
            print(f"  sz({r['size']['x']},{r['size']['y']},{r['size']['z']}) ctr({r['ctr']['x']},{r['ctr']['y']},{r['ctr']['z']}) {r.get('mat')} #{r.get('color')} m={r.get('metal')} r={r.get('rough')} :: {str(r.get('name'))[:40]}")
    await send("Target.closeTarget", {"targetId": t["targetId"]})

asyncio.run(main())