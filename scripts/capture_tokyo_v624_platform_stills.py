"""Export screenshot-gated v6.24 Tokyo platform stills; never renders video."""
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
OUT = ROOT / 'artifacts/v6.24-tokyo-platform-stills'
WS_URL = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8773/'
URL = BASE + '?cap=1&tokyo=v624&nofx=1&motion=tokyo-final&format=16x9&closedUi=0&openUi=0'
STATES = [
    ('closed-hold', 60),
    ('first-visible-motion', 148),
    ('fold-090deg', 180),
    ('fold-110deg', 186),
    ('fold-150deg', 200),
    ('open-unlit', 222),
    ('activation-mid', 268),
    ('hero-gold', 359),
]
REVISION = 'v6.24'
SAFE = (0.05, 0.06, 0.95, 0.94)  # Conservative project review guide, not platform policy.


def decode(data_url):
    return base64.b64decode(data_url.split(',', 1)[1])


def overlay_safe(image, label):
    result = image.copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size
    x0, y0, x1, y1 = (round(width * v) for v in SAFE)
    stroke = max(2, round(width / 900))
    draw.rectangle((x0, y0, x1, y1), outline=(104, 227, 255), width=stroke)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', max(14, round(width / 100)))
    text = 'PROJECT REVIEW SAFE AREA · NOT PLATFORM SPEC'
    box = draw.textbbox((0, 0), text, font=font)
    pad = max(8, round(width / 300))
    draw.rectangle((x0, y0, x0 + (box[2] - box[0]) + pad * 2, y0 + (box[3] - box[1]) + pad * 2), fill=(8, 16, 20, 210))
    draw.text((x0 + pad, y0 + pad), text, font=font, fill=(218, 248, 255))
    return result


def contact(items, path, label):
    columns, tile = 2, (960, 540)
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * tile[0], rows * (tile[1] + 44)), '#eeeeec')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    for index, (image, state, frame) in enumerate(items):
        x, y = index % columns * tile[0], index // columns * (tile[1] + 44)
        preview = image.copy()
        preview.thumbnail(tile, Image.Resampling.LANCZOS)
        sheet.paste(preview, (x + (tile[0] - preview.width) // 2, y + (tile[1] - preview.height) // 2))
        draw.text((x + 10, y + tile[1] + 10), f'{label} · frame {frame:03d} · {state}', font=font, fill='#242424')
    sheet.save(path)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob('*-clean.png')):
        raise RuntimeError('Output already contains clean screenshots; choose a fresh state-pack directory')
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
        raise RuntimeError('v6.24 did not become ready')
    await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true)")
    await asyncio.sleep(.35)

    images_4k, images_1080, states = [], [], []
    for name, frame in STATES:
        payload = await evaluate(f'window.__duo.renderTokyoPlatformStill({frame})')
        if payload['width'] != 3840 or payload['height'] != 2160:
            raise RuntimeError(f'Expected native 3840x2160 canvas, got {payload["width"]}x{payload["height"]}')
        image = Image.open(io.BytesIO(decode(payload['png']))).convert('RGB')
        if image.size != (3840, 2160):
            raise RuntimeError(f'PNG size mismatch: {image.size}')
        prefix = f'frame_{frame:06d}_{name}_{REVISION}_16x9'
        clean4k = OUT / f'{prefix}_3840x2160-clean.png'
        safe4k = OUT / f'{prefix}_3840x2160-safe-review.png'
        clean1080 = OUT / f'{prefix}_1920x1080-clean.png'
        safe1080 = OUT / f'{prefix}_1920x1080-safe-review.png'
        image.save(clean4k, optimize=True)
        overlay_safe(image, name).save(safe4k, optimize=True)
        small = image.resize((1920, 1080), Image.Resampling.LANCZOS)
        small.save(clean1080, optimize=True)
        overlay_safe(small, name).save(safe1080, optimize=True)
        images_4k.append((image, name, frame))
        images_1080.append((small, name, frame))
        state = payload['state']
        states.append({
            'name': name, 'frame': frame, 'timeSeconds': frame / 60,
            'angle': state['angle'], 'acceptance': 'pending-user',
            'clean4k': clean4k.name, 'safeReview4k': safe4k.name,
            'clean1080': clean1080.name, 'safeReview1080': safe1080.name,
            'sha256': hashlib.sha256(clean4k.read_bytes()).hexdigest(),
            'ui': state['uiVisibility'], 'focus': state['focusTransition'],
        })
    contact(images_4k, OUT / 'contact-sheet-4k-authority.png', '3840x2160 authority')
    contact(images_1080, OUT / 'contact-sheet-1080-downsample.png', '1920x1080 downsample')
    frozen_paths = ['main_v44.js', 'motionblur381.js', 'bootstrap.js', 'assets/iPhone_Duo_Render.usdc',
                    'media/tokyo/candidates/reality-v6.22-clean-tower.png',
                    'media/tokyo/candidates/redblack-v6.23-weak.png',
                    'media/tokyo/candidates/redblack-v6.23-strong.png',
                    'media/tokyo/candidates/tower-v6.22-gold-rgba.png']
    manifest = {
        'version': REVISION, 'status': 'pending-user-review', 'videoGenerated': False,
        'audioGenerated': False, 'sourceBaseCommit': 'ba7a6c1a9ff66bcac67e0e41e61ae583fb12b2bc',
        'capture': {'browser': browser, 'canvas': [3840, 2160], 'url': URL},
        'aspects': {'authority4k': [3840, 2160], 'downsample1080': [1920, 1080],
                    'relationship': '1080p is Lanczos downsample from each 4K clean source'},
        'safeArea': {'normalized': SAFE, 'meaning': 'internal project review guide; not platform official specification'},
        'states': states,
        'frozenInputs': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in frozen_paths},
        'consoleErrors': errors,
    }
    if errors:
        raise RuntimeError(f'console/runtime errors: {errors[:3]}')
    if not all(not any(item['ui'].values()) and item['focus']['leftRadius'] == 0 and item['focus']['rightRadius'] == 0 for item in states):
        raise RuntimeError('Clean v6.24 state invariant failed')
    (OUT / 'state-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()
    print(json.dumps({'output': str(OUT), 'states': len(states), 'videoGenerated': False}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
