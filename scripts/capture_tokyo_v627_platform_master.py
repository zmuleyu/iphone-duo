"""Capture the approved v6.27 4K master as 360 numbered PNGs; no encoding."""
import asyncio
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import websockets


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/v6.27-tokyo-platform-master'
WS_URL = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8774/'
URL = BASE + '?cap=1&tokyo=v627&nofx=1&motion=tokyo-final&format=16x9&closedUi=0&openUi=0'
FPS, FRAME_COUNT = 60, 360
SOURCE_COMMIT = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = OUT / 'frames-4k'
    frames.mkdir(exist_ok=True)
    if list(frames.glob('frame_*.png')):
        raise RuntimeError('4K frame output already exists; choose a fresh output directory')
    (OUT / 'run-manifest.json').write_text(json.dumps({
        'version': '6.27', 'intent': 'approved Tokyo Tower title-motion platform master capture',
        'status': 'capturing', 'timeline': {'fps': FPS, 'frameStart': 0, 'frameEndExclusive': FRAME_COUNT},
        'resolution': [3840, 2160], 'soundPolicy': 'silent', 'videoGenerated': False,
        'sourceBaseCommit': SOURCE_COMMIT,
        'url': URL,
    }, indent=2), encoding='utf-8')

    ws = await websockets.connect(WS_URL, max_size=256 * 1024 * 1024)
    pending, errors, counter = {}, [], 0

    async def reader():
        async for raw in ws:
            message = json.loads(raw)
            if message.get('id') in pending:
                pending.pop(message['id']).set_result(message)
            elif message.get('method') == 'Runtime.exceptionThrown':
                errors.append(str(message['params'])[:1000])
            elif message.get('method') == 'Runtime.consoleAPICalled' and message['params']['type'] == 'error':
                errors.append(str(message['params'].get('args', []))[:1000])

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
        nonlocal counter
        counter += 1
        message = {'id': counter, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        future = asyncio.get_running_loop().create_future()
        pending[counter] = future
        await ws.send(json.dumps(message))
        reply = await asyncio.wait_for(future, 90)
        if 'error' in reply:
            raise RuntimeError(f'{method}: {reply["error"]}')
        return reply.get('result', {})

    browser = await send('Browser.getVersion')
    target = await send('Target.createTarget', {'url': 'about:blank'})
    attached = await send('Target.attachToTarget', {'targetId': target['targetId'], 'flatten': True})
    session = attached['sessionId']
    for method in ['Page.enable', 'Runtime.enable', 'Log.enable']:
        await send(method, session=session)
    await send('Emulation.setDeviceMetricsOverride', {
        'width': 1920, 'height': 1080, 'deviceScaleFactor': 2, 'mobile': False,
    }, session)
    await send('Page.navigate', {'url': URL}, session=session)

    async def evaluate(expression):
        result = await send('Runtime.evaluate', {'expression': expression, 'returnByValue': True}, session)
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result['exceptionDetails'])[:1000])
        return result.get('result', {}).get('value')

    for _ in range(600):
        if await evaluate('window.__duo?.state.ready && window.__duo.state.customReady.reality && window.__duo.state.customReady.redblack'):
            break
        await asyncio.sleep(.1)
    else:
        raise RuntimeError('v6.27 did not become ready')
    await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true)")
    await asyncio.sleep(.35)

    ledger = []
    for frame in range(FRAME_COUNT):
        payload = await evaluate(f'window.__duo.renderTokyoPlatformStill({frame})')
        if payload['width'] != 3840 or payload['height'] != 2160:
            raise RuntimeError(f'Expected 3840x2160 canvas, got {payload["width"]}x{payload["height"]}')
        data = base64.b64decode(payload['png'].split(',', 1)[1])
        path = frames / f'frame_{frame:06d}.png'
        path.write_bytes(data)
        state = payload['state']
        if state['recordingMode']['frame'] != frame:
            raise RuntimeError(f'Frame clock mismatch at {frame}')
        ledger.append({
            'frame': frame, 'timeSeconds': frame / FPS, 'angle': state['angle'],
            'layers': state['layeredTokyo'], 'focus': state['focusTransition'],
            'ui': state['uiVisibility'], 'sha256': hashlib.sha256(data).hexdigest(),
        })
        if frame % 30 == 0:
            print(f'rendered {frame}/{FRAME_COUNT}', flush=True)

    frozen = {}
    for path in ['main_v44.js', 'motionblur381.js', 'bootstrap.js', 'assets/iPhone_Duo_Render.usdc',
                 'media/tokyo/candidates/reality-v6.22-clean-tower.png',
                 'media/tokyo/candidates/redblack-v6.23-weak.png',
                 'media/tokyo/candidates/redblack-v6.23-strong.png',
                 'media/tokyo/candidates/tower-v6.22-gold-rgba.png']:
        frozen[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    environment = await evaluate("""(() => { const r=window.__duo._renderer,g=r.getContext(),e=g.getExtension('WEBGL_debug_renderer_info'); return {canvas:[r.domElement.width,r.domElement.height],pixelRatio:r.getPixelRatio(),gpu:e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER)}; })()""")
    records = {
        'frame-ledger.json': ledger,
        'frozen-input-hashes.json': frozen,
        'renderer-info.json': {'browser': browser, 'environment': environment, 'url': URL},
        'console-errors.json': errors,
        'run-manifest.json': {
            'version': '6.27', 'intent': 'approved Tokyo Tower title-motion platform master capture', 'status': 'captured-pending-qc',
            'timeline': {'fps': FPS, 'frameStart': 0, 'frameEndExclusive': FRAME_COUNT, 'durationSeconds': FRAME_COUNT / FPS},
            'resolution': [3840, 2160], 'soundPolicy': 'silent', 'videoGenerated': False,
            'sourceBaseCommit': SOURCE_COMMIT, 'capture': environment,
        },
    }
    for name, value in records.items():
        (OUT / name).write_text(json.dumps(value, indent=2), encoding='utf-8')
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()
    if errors:
        raise RuntimeError(f'console/runtime errors: {errors[:3]}')
    print(json.dumps({'output': str(OUT), 'frames': FRAME_COUNT, 'resolution': [3840, 2160], 'videoGenerated': False}))


if __name__ == '__main__':
    asyncio.run(main())
