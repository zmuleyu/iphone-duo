"""Capture title-dependent review states through v6.27; never renders video."""
import asyncio
import base64
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import websockets


ROOT = Path(__file__).resolve().parents[1]
WS_URL = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8775/'
REVISION = sys.argv[3] if len(sys.argv) > 3 else 'v625'
IS_BOLD_PREVIEW = REVISION == 'v626'
IS_FINAL_MOTION = REVISION == 'v627'
VERSION_LABEL = {'v625': 'v6.25', 'v626': 'v6.26', 'v627': 'v6.27'}.get(REVISION, REVISION)
OUT = ROOT / ('artifacts/v6.27-tokyo-title-motion-stills' if IS_FINAL_MOTION else
              'artifacts/v6.26-tokyo-bold-title-preview' if IS_BOLD_PREVIEW else
              'artifacts/v6.25-tokyo-title-stills-r3')
URL = BASE + f'?cap=1&tokyo={REVISION}&nofx=1&motion=tokyo-final&format=16x9&closedUi=0&openUi=0'
STATES = [('pre-title', 287), ('title-mid-reveal', 294), ('title-reveal-complete', 302),
          ('final-title', 359)] if IS_FINAL_MOTION else [('hero-bold-title', 359)] if IS_BOLD_PREVIEW else [
    ('pre-title', 287), ('title-entry', 294), ('hero-title', 330), ('final-title', 359),
]
SAFE = (.05, .06, .95, .94)


def decode(data_url):
    return base64.b64decode(data_url.split(',', 1)[1])


def overlay_safe(image):
    result = image.copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size
    x0, y0, x1, y1 = (round(value * size) for value, size in zip(SAFE, (width, height, width, height)))
    stroke = max(2, round(width / 900))
    draw.rectangle((x0, y0, x1, y1), outline=(104, 227, 255), width=stroke)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', max(14, round(width / 100)))
    label = 'PROJECT REVIEW SAFE AREA · NOT PLATFORM SPEC'
    box = draw.textbbox((0, 0), label, font=font)
    pad = max(8, round(width / 300))
    draw.rectangle((x0, y0, x0 + box[2] + pad * 2, y0 + box[3] + pad * 2), fill=(8, 16, 20))
    draw.text((x0 + pad, y0 + pad), label, font=font, fill=(218, 248, 255))
    return result


def make_contact(items, path):
    tile = (960, 540)
    sheet = Image.new('RGB', (1920, 1168), '#eeeeec')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    for index, (image, label, frame) in enumerate(items):
        x = (index % 2) * tile[0]
        y = (index // 2) * 584
        preview = image.copy()
        preview.thumbnail(tile, Image.Resampling.LANCZOS)
        sheet.paste(preview, (x + (tile[0] - preview.width) // 2, y))
        draw.text((x + 12, y + 550), f'frame {frame:03d} · {label}', font=font, fill='#242424')
    sheet.save(path)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob('*-clean.png')):
        raise RuntimeError('Title review directory already contains clean screenshots')
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
        reply = await asyncio.wait_for(future, 60)
        if 'error' in reply:
            raise RuntimeError(f'{method}: {reply["error"]}')
        return reply.get('result', {})

    target = await send('Target.createTarget', {'url': 'about:blank'})
    session = (await send('Target.attachToTarget', {'targetId': target['targetId'], 'flatten': True}))['sessionId']
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
        raise RuntimeError(f'{VERSION_LABEL} did not become ready')
    await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true)")
    await asyncio.sleep(.35)

    items, states = [], []
    for label, frame in STATES:
        payload = await evaluate(f'window.__duo.renderTokyoPlatformStill({frame})')
        if (payload['width'], payload['height']) != (3840, 2160):
            raise RuntimeError(f'Unexpected canvas: {payload["width"]}x{payload["height"]}')
        image = Image.open(io.BytesIO(decode(payload['png']))).convert('RGB')
        prefix = f'frame_{frame:06d}_{label}_{VERSION_LABEL}_16x9'
        clean = OUT / f'{prefix}_3840x2160-clean.png'
        safe = OUT / f'{prefix}_3840x2160-safe-review.png'
        image.save(clean, optimize=True)
        overlay_safe(image).save(safe, optimize=True)
        title = payload['state']['titleLayer']
        states.append({'label': label, 'frame': frame, 'timeSeconds': frame / 60,
                       'title': title, 'clean': clean.name, 'safe': safe.name,
                       'sha256': hashlib.sha256(clean.read_bytes()).hexdigest(),
                       'acceptance': 'pending-user'})
        items.append((image, label, frame))
    make_contact(items, OUT / 'contact-sheet-title-authority.png')
    if errors:
        raise RuntimeError(f'console/runtime errors: {errors[:3]}')
    if IS_FINAL_MOTION:
        pre, mid, complete, final = [state['title'] for state in states]
        if pre['opacity'] != 0 or pre['reveal'] != 0:
            raise RuntimeError('Final title pre-entry invariant failed')
        if not (0 < mid['reveal'] < 1 and 1 < mid['scale'] < 1.04):
            raise RuntimeError('Final title right-to-left reveal invariant failed')
        if complete['reveal'] != 1 or complete['scale'] != 1 or final['reveal'] != 1:
            raise RuntimeError('Final title completion invariant failed')
    elif IS_BOLD_PREVIEW:
        title = states[0]['title']
        if title['opacity'] != 1 or title['text'] != 'TOKYO TOWER' or title['weight'] < 800:
            raise RuntimeError('Bold title preview invariant failed')
    elif states[0]['title']['opacity'] != 0 or any(state['title']['opacity'] <= 0 for state in states[1:]):
        raise RuntimeError('Title timing invariant failed')
    manifest = {
        'version': VERSION_LABEL, 'status': 'pending-user-review', 'videoGenerated': False,
        'audioGenerated': False, 'sourceBaseCommit': '4bf30a09f9e1cd2eeb047c41cfc371f588165576',
        'capture': {'canvas': [3840, 2160], 'url': URL}, 'states': states,
        'titleContract': {'surface': 'inner-display-only', 'defaultText': 'TOKYO TOWER' if IS_BOLD_PREVIEW else 'TOKYO',
                          'defaultPosition': 'horizontal-center, y=18%', 'lockScreenChrome': False},
        'consoleErrors': errors,
    }
    (OUT / 'title-state-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()
    print(json.dumps({'output': str(OUT), 'states': len(states), 'videoGenerated': False}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
