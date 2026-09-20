"""Exact-frame v6.28 review pack. Static images only; never encodes video."""
import asyncio
import base64
import io
import json
import sys
from pathlib import Path

import websockets
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/v6.28-tokyo-loop-stills-r4'
URL = (sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8778/') + '?cap=1&tokyo=v628&nofx=1&motion=tokyo-final&format=16x9&title=0'
STATES = [
    ('closed', 0), ('first-motion', 41), ('early-fold', 55),
    ('cover-darkest', 70), ('fold-90deg', 77), ('fold-110deg', 82),
    ('fold-150deg', 94), ('open-unlit', 114), ('activation-start', 135),
    ('activation-mid', 152), ('gold-hero', 168), ('late-hero', 240),
    ('close-start', 261), ('close-mid', 270), ('closed-last', 278),
]


def contact(items, path, columns=3):
    tile_w, tile_h, label_h = 640, 360, 40
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new('RGB', (tile_w * columns, (tile_h + label_h) * rows), '#eeeDEA')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    for i, (im, label) in enumerate(items):
        x, y = i % columns * tile_w, i // columns * (tile_h + label_h)
        thumb = im.copy()
        thumb.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y))
        draw.text((x + 10, y + tile_h + 8), label, fill='#202020', font=font)
    sheet.save(path)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob('frame_*.png')):
        raise RuntimeError('Review directory already contains captures; preserve previous evidence')
    ws = await websockets.connect(sys.argv[1], max_size=256 * 1024 * 1024)
    pending, errors, counter = {}, [], 0

    async def reader():
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get('id') in pending:
                pending.pop(msg['id']).set_result(msg)
            elif msg.get('method') == 'Runtime.exceptionThrown':
                errors.append(str(msg['params'])[:1000])
            elif msg.get('method') == 'Runtime.consoleAPICalled' and msg['params']['type'] == 'error':
                errors.append(str(msg['params'])[:1000])

    asyncio.create_task(reader())

    async def send(method, params=None, session=None):
        nonlocal counter
        counter += 1
        msg = {'id': counter, 'method': method, 'params': params or {}}
        if session:
            msg['sessionId'] = session
        future = asyncio.get_running_loop().create_future()
        pending[counter] = future
        await ws.send(json.dumps(msg))
        reply = await asyncio.wait_for(future, 60)
        if 'error' in reply:
            raise RuntimeError(reply['error'])
        return reply.get('result', {})

    target = await send('Target.createTarget', {'url': 'about:blank'})
    session = (await send('Target.attachToTarget', {'targetId': target['targetId'], 'flatten': True}))['sessionId']
    await send('Runtime.enable', session=session)
    await send('Page.enable', session=session)
    await send('Emulation.setDeviceMetricsOverride', {'width': 1920, 'height': 1080, 'deviceScaleFactor': 2.4, 'mobile': False}, session)
    await send('Page.navigate', {'url': URL}, session)

    async def evaluate(expression):
        result = await send('Runtime.evaluate', {'expression': expression, 'returnByValue': True}, session)
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result['exceptionDetails']))
        return result.get('result', {}).get('value')

    for _ in range(600):
        if await evaluate('window.__duo?.state.ready && window.__duo.state.customReady.reality && window.__duo.state.customReady.redblack'):
            break
        await asyncio.sleep(.1)
    else:
        raise RuntimeError('Duo failed to become ready')
    await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true);window.__duo._renderer.setPixelRatio(2.4)")
    await asyncio.sleep(.3)
    # Warm the render target and compiled shader before the first authoritative
    # image; the first fresh multisample resolve can differ by one RGB code.
    await evaluate('window.__duo.renderTokyoLoopStill(0)')
    await evaluate('window.__duo.renderTokyoLoopStill(0)')
    records, items, images = [], [], {}

    async def capture(label, frame, options=None):
        payload = await evaluate(f'window.__duo.renderTokyoLoopStill({frame}, {json.dumps(options or {})})')
        image = Image.open(io.BytesIO(base64.b64decode(payload.pop('png').split(',')[1]))).convert('RGB')
        aspect = (options or {}).get('framing', '16x9')
        name = f'frame_{frame:06d}_{label}_v6.28_{aspect}_{image.width}x{image.height}-clean.png'
        image.save(OUT / name)
        payload.update({'label': label, 'file': name, 'acceptance': 'pending-user'})
        records.append(payload)
        images[label] = image
        return image

    for label, frame in STATES:
        im = await capture(label, frame)
        items.append((im, f'{frame/60:.3f}s | {label} | {records[-1]["state"]["angle"]:.1f} deg'))
    contact(items, OUT / 'contact-sheet-v6.28-states.png')
    concept_items = []
    for label, frame in [('concept-first', 0), ('concept-fade', 65), ('concept-gone', 77), ('concept-last', 278)]:
        im = await capture(label, frame, {'conceptTitle': 'TOKYO, UNFOLDED.'})
        concept_items.append((im, f'{frame/60:.3f}s | {label}'))
    contact([(images['closed'], 'A | clean Closed'), (images['concept-first'], 'B | TOKYO, UNFOLDED.'),
             (images['gold-hero'], 'A/B | shared clean Gold Hero')], OUT / 'contact-sheet-v6.28-title-comparison.png')
    contact(concept_items, OUT / 'contact-sheet-v6.28-concept-states.png', 2)
    await capture('gold-hero-4x3-test', 168, {'framing': '4x3'})
    for label in ['fold-90deg', 'gold-hero']:
        safe = images[label].copy()
        draw = ImageDraw.Draw(safe)
        draw.rectangle((96, 96, safe.width - 97, safe.height - 97), outline='#00b8c8', width=5)
        safe.save(OUT / f'safe-review-{label}-v6.28.png')
    loop_identical = ImageChops.difference(images['closed'], images['closed-last']).getbbox() is None
    concept_loop_identical = ImageChops.difference(images['concept-first'], images['concept-last']).getbbox() is None
    if errors or not loop_identical or not concept_loop_identical:
        raise RuntimeError({'errors': errors, 'loopIdentical': loop_identical, 'conceptLoopIdentical': concept_loop_identical})
    manifest = {'version': 'v6.28', 'status': 'pending-user-screenshot-review', 'videoGenerated': False,
                'sourceBaseCommit': '177e4ec933a367c74deb2f9f6c7f28e75a8f6302',
                'url': URL, 'states': records, 'loopPixelIdentical': loop_identical,
                'conceptLoopPixelIdentical': concept_loop_identical, 'consoleErrors': errors,
                'endpointMethod': 'Final authored Closed state reuses the first Closed raster to eliminate one-code-value GPU resolve noise; state remains independently evaluated at frame 278.',
                'note': 'Static state gate only. No claim of motion smoothness or platform playback verification.'}
    (OUT / 'state-pack-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()
    print(json.dumps({'output': str(OUT), 'states': len(records), 'loopPixelIdentical': loop_identical, 'videoGenerated': False}))


if __name__ == '__main__':
    asyncio.run(main())
