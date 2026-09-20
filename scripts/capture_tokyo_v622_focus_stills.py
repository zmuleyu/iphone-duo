"""Seven focus-state stills plus same-browser legacy checks. No video/frame sequence."""
import asyncio
import base64
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/v6.22-tokyo-focus-still-review'
BASE = 'http://127.0.0.1:8771/'
SHOTS = [
    ('01-closed-v619-refined-clean-tower', 0, 'weak'),
    ('02-fold-90deg-fixed-right-sharp', 90, 'weak'),
    ('03-fold-110deg-left-blurred', 110, 'weak'),
    ('04-fold-150deg-left-resolving', 150, 'weak'),
    ('05-open-weak-windows-edged-tower', 180, 'weak'),
    ('06-open-strong-windows-edged-tower', 180, 'strong'),
    ('07-open-lit-clean-tower', 180, 'tower'),
]


def decode(value):
    return base64.b64decode(value.split(',', 1)[1])


def sheet(items, filename, columns=2, tile=(960, 540)):
    rows = (len(items) + columns - 1) // columns
    output = Image.new('RGB', (columns * tile[0], rows * (tile[1] + 48)), '#eeeeee')
    draw = ImageDraw.Draw(output)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    for i, (image, label) in enumerate(items):
        image = image.copy()
        image.thumbnail(tile, Image.Resampling.LANCZOS)
        x, y = i % columns * tile[0], i // columns * (tile[1] + 48)
        output.paste(image, (x + (tile[0] - image.width) // 2, y))
        draw.text((x + 12, y + tile[1] + 10), label, font=font, fill='#222222')
    output.save(OUT / filename)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ws = await websockets.connect(sys.argv[1], max_size=64 * 1024 * 1024)
    pending, errors = {}, []
    counter = 0
    baseline_script = base64.b64encode(subprocess.check_output(
        ['git', 'show', 'b9365e4ede78404d050f6075af3cb957ca4b8396:main_v44.js'], cwd=ROOT)).decode()

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
            elif message.get('method') == 'Fetch.requestPaused':
                asyncio.create_task(send('Fetch.fulfillRequest', {'requestId': message['params']['requestId'],
                    'responseCode': 200, 'responseHeaders': [{'name': 'Content-Type', 'value': 'application/javascript'}],
                    'body': baseline_script}, session))

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
            raise RuntimeError(reply['error'])
        return reply.get('result', {})

    browser = await send('Browser.getVersion')
    target = await send('Target.createTarget', {'url': 'about:blank'})
    attached = await send('Target.attachToTarget', {'targetId': target['targetId'], 'flatten': True})
    session = attached['sessionId']
    for method in ['Page.enable', 'Runtime.enable', 'Log.enable']:
        await send(method, session=session)
    await send('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1.25, 'mobile': False}, session)

    async def evaluate(expression):
        result = await send('Runtime.evaluate', {'expression': expression, 'returnByValue': True}, session)
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result['exceptionDetails'])[:1000])
        return result.get('result', {}).get('value')

    async def navigate(profile):
        await send('Page.navigate', {'url': BASE + f'?cap=1&tokyo={profile}&nofx=1&motion=tokyo-demo&format=16x9'}, session)
        for _ in range(600):
            if await evaluate('window.__duo?.state.ready && window.__duo.state.customReady.reality && window.__duo.state.customReady.redblack'):
                break
            await asyncio.sleep(.1)
        else:
            raise RuntimeError('Preview did not become ready')
        await evaluate("window.__duo.setRecordFormat('16x9');window.__duo.setRecordFps(60);window.__duo.setRecordingMode(true)")
        await asyncio.sleep(.4)

    await navigate('v622')
    environment = await evaluate("(() => { const r=window.__duo._renderer,g=r.getContext(),e=g.getExtension('WEBGL_debug_renderer_info'); return {pixelRatio:r.getPixelRatio(),canvas:[r.domElement.width,r.domElement.height],vendor:g.getParameter(g.VENDOR),renderer:g.getParameter(g.RENDERER),gpu:e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):null}; })()")
    ledger = []
    for name, angle, lights in SHOTS:
        result = await evaluate('window.__duo.renderTokyoFocusStill(' + json.dumps({'angle': angle, 'lights': lights}) + ')')
        data = decode(result.pop('png'))
        (OUT / (name + '.png')).write_bytes(data)
        chrome = result.pop('chrome')
        (OUT / 'open-chrome-only.png').write_bytes(decode(chrome))
        result.update(file=name + '.png', sha256=hashlib.sha256(data).hexdigest(), runtime=await evaluate('window.__duo.state'))
        ledger.append(result)
    await evaluate('window.__duo.setRecordingMode(false);window.__duo.setAngle(180)')
    await asyncio.sleep(.1)
    desktop = await send('Page.captureScreenshot', {'format': 'png'}, session)
    (OUT / 'desktop-open.png').write_bytes(base64.b64decode(desktop['data']))
    regression = {}
    for profile in ['v619', 'v620']:
        await navigate(profile)
        frames = {}
        for frame in [12, 91, 347]:
            frames[frame] = Image.open(io.BytesIO(decode(await evaluate(f'window.__duo.renderReviewFrame({frame})')))).convert('RGB')
        await send('Fetch.enable', {'patterns': [{'urlPattern': '*/main_v44.js*', 'requestStage': 'Request'}]}, session)
        await navigate(profile)
        differences = {}
        for frame, current in frames.items():
            baseline = Image.open(io.BytesIO(decode(await evaluate(f'window.__duo.renderReviewFrame({frame})')))).convert('RGB')
            diff = ImageChops.difference(current, baseline)
            differences[str(frame)] = {'maxChannelDelta': max(v[1] for v in diff.getextrema()), 'changedBox': diff.getbbox()}
        regression[profile] = differences
        await send('Fetch.disable', session=session)
    await send('Target.closeTarget', {'targetId': target['targetId']})
    await ws.close()

    def im(index):
        return Image.open(OUT / (SHOTS[index][0] + '.png')).convert('RGB')
    sheet([(im(i), s[0].split('-', 1)[1]) for i, s in enumerate(SHOTS)], 'still-review-contact-sheet.png', tile=(640, 360))
    sheet([(im(i), f'{SHOTS[i][1]} deg / left radius {ledger[i]["focusRadiusSourceTexels"]:.2f} / fixed right radius 0') for i in [1, 2, 3, 4]],
          'focus-transition-proof.png', columns=1, tile=(1280, 720))
    sheet([(im(0).crop((1120, 200, 1370, 825)), 'Closed / repaired natural tower'),
           (im(4).crop((1120, 200, 1370, 825)), 'Unlit / near-black dark-copper edge'),
           (im(6).crop((1120, 200, 1370, 825)), 'Lit / same repaired plate in gold')],
          'actual-tower-closeups.png', columns=3, tile=(500, 800))
    # Exclude the Open flashlight's left arc near x1450. Both ROIs contain
    # the same registered city content in all three physical-angle states.
    left_roi, right_roi = [790, 520, 925, 865], [1340, 520, 1420, 865]
    def laplacian(image, roi):
        x0, y0, x1, y1 = roi
        pixels = np.array(image)[y0:y1, x0:x1]
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    focus = [{'angle': SHOTS[i][1], 'leftLaplacianVariance': laplacian(im(i), left_roi),
              'rightLaplacianVariance': laplacian(im(i), right_roi)} for i in [2, 3, 4]]
    left = [e['leftLaplacianVariance'] for e in focus]
    right = [e['rightLaplacianVariance'] for e in focus]
    sheet([(im(i).crop(tuple(left_roi)), f'{SHOTS[i][1]} deg / moving left ROI') for i in [2, 3, 4]] +
          [(im(i).crop(tuple(right_roi)), f'{SHOTS[i][1]} deg / fixed right ROI') for i in [2, 3, 4]],
          'focus-roi-closeups.png', columns=3, tile=(400, 500))
    chrome = np.array(Image.open(OUT / 'open-chrome-only.png').convert('RGBA'))
    tower_roi = [1120, 160, 1360, 830]
    a_residual = []
    for i in [1, 2, 3]:
        x0, y0, x1, y1 = tower_roi
        pixels = np.array(im(i))[y0:y1, x0:x1].astype('float32')
        neutral_white = (pixels.min(axis=2) > 100) & (pixels.max(axis=2) < pixels.min(axis=2) * 1.25)
        a_residual.append({'angle': SHOTS[i][1], 'neutralBrightATowerResidualPixels': int(np.count_nonzero(neutral_white))})
    frozen = json.loads((OUT / 'frozen-input-hashes.json').read_text(encoding='utf-8'))
    qc = {'status': 'still-candidate / pending-user-selection', 'video': None, 'size': [1920, 1080], 'stillCount': len(SHOTS),
          'browser': browser, 'rendererEnvironment': environment, 'consoleRuntimeErrors': errors, 'revealMode': 'none/focus-only', 'spatialFront': None,
          'focusROIs': {'left': left_roi, 'right': right_roi}, 'focusMeasurements': focus,
          'leftSharpnessStrictlyIncreasing': left[0] < left[1] < left[2],
          'rightSharpnessRelativeSpread': (max(right) - min(right)) / max(right), 'rightSpreadTolerance': .01,
          'noClockDateTitleAlphaPixels': int(np.count_nonzero(chrome[0:650, 0:1450, 3])),
          'noHomeAlphaPixels': int(np.count_nonzero(chrome[1060:, :, 3])),
          'towerIdentityROI': tower_roi, 'towerIdentityMeasurements': a_residual,
          'towerResidualRule': 'All RGB channels >100 and max/min <1.25; detects neutral bright A tower, excludes red sky and amber windows',
          'oldQuerySameBrowserSourceRegression': regression,
          'frozenInputsUnchanged': all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest().lower() == h.lower() for p, h in frozen.items())}
    (OUT / 'still-runtime-ledger.json').write_text(json.dumps(ledger, indent=2), encoding='utf-8')
    (OUT / 'still-qc.json').write_text(json.dumps(qc, indent=2), encoding='utf-8')
    print(json.dumps(qc, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
