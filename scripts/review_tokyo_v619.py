"""Measure fixed-step frame accounting, screen registration and visible motion."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'artifacts/v6.19-tokyo-silent-demo'


def registration(folder):
    closed = cv2.imread(str(folder / 'calibration-closed-a.png'), 0)
    opened = cv2.imread(str(folder / 'calibration-open-a.png'), 0)
    # Match the entire tower spine, deck and lattice while excluding the UI.
    x0, x1, y0, y1, margin = 1180, 1320, 180, 720, 16
    template = opened[y0:y1, x0:x1]
    search = closed[y0-margin:y1+margin, x0-margin:x1+margin]
    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    shift = [loc[0]-margin, loc[1]-margin]
    return {'coverToInnerShiftPx':shift,'distancePx':float(np.hypot(*shift)),
            'normalizedCorrelation':score,'roi':[x0,y0,x1,y1]}


def main():
    if '--registration-only' in sys.argv:
        print(json.dumps(registration(ART), indent=2))
        return
    ledger = json.loads((ART / 'frame-ledger.json').read_text())
    frames = sorted((ART / 'frames').glob('frame_*.png'))
    assert len(frames) == 348
    assert [item['frame'] for item in ledger] == list(range(348))
    runtime = json.loads((ART / 'runtime-state.json').read_text())
    start = round(runtime['foldMotion']['closedHold'] * 60)
    end = round((runtime['foldMotion']['closedHold'] + runtime['foldMotion']['unfoldDuration']) * 60)
    motion = ledger[start:end+1]
    bbox = []
    for item in motion:
        rgb = cv2.imread(str(frames[item['frame']]))
        foreground = np.min(rgb, axis=2) < 150
        foreground[:100] = False
        foreground[1000:] = False
        bbox.append(int(np.where(foreground)[1].min()))
    full_travel = bbox[0] - bbox[-1]
    progress = [(bbox[0] - x) / full_travel for x in bbox]
    first10 = next(i + start for i, p in enumerate(progress) if p >= .1)
    first90 = next(i + start for i, p in enumerate(progress) if p >= .9)
    duplicates = [motion[i]['frame'] for i in range(1, len(motion)) if motion[i]['sha256'] == motion[i-1]['sha256']]
    metrics = {
        'numberedFrames':len(frames),'frameInterval':[0,348],'authoredDurationSeconds':5.8,
        'motionDuplicateFrameIndices':duplicates,
        'projected10To90Seconds':(first90-first10)/60,
        'projected10To90Frames':[first10,first90],
        'maximumVisibleStepPercent':max(abs(progress[i]-progress[i-1]) for i in range(1,len(progress)))*100,
        'visibleOvershootPercent':max(0,(bbox[-1]-min(bbox))/full_travel*100),
        'angleOvershootPercent':max(0,max(item['angle'] for item in ledger)/180-1)*100,
        'openCompleteFrame':next(item['frame'] for item in ledger if item['angle']==180),
        'uiFadeFrames':6, 'pulsePeakFrame':191,
        'registration':registration(ART),
        'consoleErrors':json.loads((ART/'console-errors.json').read_text()),
        'method':'Synchronous WebGL render -> PNG readback -> exactly one ordered PNG per frame index',
    }
    (ART / 'qc-summary.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    sheet = Image.new('RGB',(1280,1580),'#eeeeec')
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate([12,72,91,107,126,143,191,347]):
        x,y=(i%2)*640,(i//2)*395
        sheet.paste(Image.open(frames[frame]).convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+12,y+365),f'{frame/60:.3f}s / {ledger[frame]["angle"]:.1f} deg',font=font,fill='#333333')
    sheet.save(ART/'contact-sheet.png')
    shell=Image.new('RGB',(1440,450),'white')
    for i,name in enumerate(['shell-closed.png','shell-open.png']):
        shell.paste(Image.open(ART/name).convert('RGB').resize((720,450),Image.Resampling.LANCZOS),(720*i,0))
    shell.save(ART/'shell-contact-sheet.png')
    print(json.dumps(metrics,indent=2))


if __name__ == '__main__':
    main()
