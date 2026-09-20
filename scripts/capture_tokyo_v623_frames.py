"""Render the 360-frame v6.23 master through synchronous CDP readback."""
import asyncio
import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path

import websockets


ROOT = Path(__file__).resolve().parents[1]
WS_URL = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8772/'
OUT = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else ROOT / 'artifacts/v6.23-tokyo-silent-video'
URL = BASE + '?cap=1&tokyo=v623&nofx=1&motion=tokyo-final&format=16x9&closedUi=0&openUi=0'
FRAME_COUNT = 360
FPS = 60


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / 'frames'
    frames_dir.mkdir(exist_ok=True)
    if list(frames_dir.glob('frame_*.png')):
        raise RuntimeError('Frame output already exists; use a fresh output directory')

    ws = await websockets.connect(WS_URL, max_size=256 * 1024 * 1024)
    pending, errors = {}, []
    counter = 0

    async def reader():
        async for raw in ws:
            message = json.loads(raw)
            if message.get('id') in pending:
                pending.pop(message['id']).set_result(message)
            elif message.get('method') == 'Runtime.exceptionThrown':
                errors.append(str(message['params'])[:1000])
            elif message.get('method') == 'Runtime.consoleAPICalled' and message['params']['type'] == 'error':
                errors.append(str(message['params'].get('args', []))[:1000])
            elif message.get('method') == 'Log.entryAdded' and message['params']['entry']['level'] == 'error':
                errors.append(message['params']['entry']['text'][:1000])

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
        reply = await asyncio.wait_for(future, 60)
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
        'width': 1440, 'height': 900, 'deviceScaleFactor': 1.25, 'mobile': False,
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
        raise RuntimeError('Preview did not become ready')

    initial = json.loads(await evaluate('JSON.stringify(window.__duo.state)'))
    if initial['foldMotion']['preset'] != 'tokyo-final':
        raise RuntimeError('Tokyo final preset was not activated')
    if not initial['masterPairQA']['pair']['pass']:
        raise RuntimeError('Bundled Tokyo pair failed dimension/aspect gate')
    await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true)")
    await asyncio.sleep(.4)

    ledger = []
    for frame in range(FRAME_COUNT):
        png = await evaluate(f'window.__duo.renderReviewFrame({frame})')
        data = base64.b64decode(png.split(',', 1)[1])
        path = frames_dir / f'frame_{frame:06d}.png'
        path.write_bytes(data)
        state = json.loads(await evaluate('JSON.stringify(window.__duo.state)'))
        if state['recordingMode']['frame'] != frame:
            raise RuntimeError(f'Frame clock mismatch at {frame}')
        ledger.append({
            'frame': frame,
            'time': frame / FPS,
            'angle': state['angle'],
            'layers': state['layeredTokyo'],
            'focus': state['focusTransition'],
            'ui': state['uiVisibility'],
            'sha256': hashlib.sha256(data).hexdigest(),
        })
        if frame % 60 == 0:
            print(f'rendered {frame}/{FRAME_COUNT}', flush=True)

    angle_frames = {}
    for target_angle in [90, 110, 150, 180]:
        item = min(ledger, key=lambda entry: abs(entry['angle'] - target_angle))
        angle_frames[str(target_angle)] = item['frame']
        shutil.copyfile(frames_dir / f'frame_{item["frame"]:06d}.png', OUT / f'fold-{target_angle:03d}deg.png')
    for frame, name in [(60, 'closed-hold'), (222, 'open-unlit'), (249, 'open-pause-end'),
                        (268, 'tower-activation-mid'), (288, 'hero-start'), (359, 'hero-end')]:
        shutil.copyfile(frames_dir / f'frame_{frame:06d}.png', OUT / f'{name}.png')

    final_state = json.loads(await evaluate('JSON.stringify(window.__duo.state)'))
    environment = await evaluate("""(() => { const r=window.__duo._renderer,g=r.getContext(),e=g.getExtension('WEBGL_debug_renderer_info'); return {pixelRatio:r.getPixelRatio(),canvas:[r.domElement.width,r.domElement.height],vendor:g.getParameter(g.VENDOR),renderer:g.getParameter(g.RENDERER),gpu:e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):null,anisotropy:r.capabilities.getMaxAnisotropy()}; })()""")
    frozen = {}
    for relative in ['main_v44.js', 'motionblur381.js', 'bootstrap.js', 'assets/iPhone_Duo_Render.usdc',
                     'media/tokyo/candidates/reality-v6.22-clean-tower.png',
                     'media/tokyo/candidates/layers-v6.22-mask.png',
                     'media/tokyo/candidates/redblack-v6.23-weak.png',
                     'media/tokyo/candidates/redblack-v6.23-strong.png',
                     'media/tokyo/candidates/tower-v6.22-gold-rgba.png']:
        frozen[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    records = {
        'frame-ledger.json': ledger,
        'runtime-state.json': final_state,
        'angle-frames.json': angle_frames,
        'console-errors.json': errors,
        'renderer-info.json': {'browser': browser, 'environment': environment, 'url': URL},
        'frozen-input-hashes.json': frozen,
    }
    for name, value in records.items():
        (OUT / name).write_text(json.dumps(value, indent=2), encoding='utf-8')
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()
    if errors:
        raise RuntimeError(f'console/runtime errors: {errors[:3]}')
    print(json.dumps({'output': str(OUT), 'frames': FRAME_COUNT, 'fps': FPS,
                      'duration': FRAME_COUNT / FPS, 'angleFrames': angle_frames}))


if __name__ == '__main__':
    asyncio.run(main())
