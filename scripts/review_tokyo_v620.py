"""Measure fixed-step frame accounting, screen registration and visible motion."""
import json
import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'artifacts/v6.20-tokyo-silent-demo'


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
        'uiFadeFrames':6, 'legacyPulseEnabled':False,
        'registration':registration(ART),
        'consoleErrors':json.loads((ART/'console-errors.json').read_text()),
        'method':'Synchronous WebGL render -> PNG readback -> exactly one ordered PNG per frame index',
    }
    assert all(x['layers']['windowsLight']==0 for x in ledger[:148])
    assert all(x['layers']['towerLight']==0 for x in ledger[:186])
    assert all(x['layers']['pulse']==0 and x['layers']['windowBreath']==0 for x in ledger)
    assert all(x['layers']['coverChrome']==0 for x in ledger)
    assert ledger[180]['layers']['windowsLight']==1 and ledger[211]['layers']['towerLight']==1
    assert all(ledger[i]['layers']['windowsLight']>=ledger[i-1]['layers']['windowsLight'] for i in range(1,348))
    assert all(ledger[i]['layers']['towerLight']>=ledger[i-1]['layers']['towerLight'] for i in range(1,348))
    stable_pairs={}
    for a,b in [(143,147),(180,185),(211,347)]:
        diff=ImageChops.difference(Image.open(frames[a]).convert('RGB'),Image.open(frames[b]).convert('RGB'))
        stable_pairs[f'{a}-{b}']=max(v[1] for v in diff.getextrema())
    assert all(v==0 for v in stable_pairs.values())
    frozen=json.loads((ART/'frozen-input-hashes.json').read_text())
    changed=[name for name,expected in frozen.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper()!=expected]
    assert not changed, changed
    metrics.update({'lightStageFrames':{'open':138,'windowsStart':147,'windowsComplete':180,'towerStart':185,'towerComplete':211},
        'stableStateMaxChannelDelta':stable_pairs,'frozenInputsVerified':len(frozen),'changedFrozenInputs':changed,
        'closedChromeEnabled':runtime['chrome']['closed'],'heroHoldStable':True})
    preserved_media=[]
    for version in ['v6.18','v6.19']:
        previous=json.loads((ROOT/f'media/tokyo/{version}-silent-demo-manifest.json').read_text(encoding='utf-8'))
        outputs=previous.get('outputs',[previous.get('output')])
        for output in outputs:
            if output and output['path'].endswith('.mp4'):
                path=ROOT/output['path']
                if path.exists():
                    actual=hashlib.sha256(path.read_bytes()).hexdigest().upper()
                    assert actual==output['sha256'], output['path']
                    preserved_media.append(output['path'])
    metrics['preservedPriorVideos']=preserved_media
    assert .7<=metrics['projected10To90Seconds']<=.91
    assert metrics['maximumVisibleStepPercent']<=3.2
    assert metrics['visibleOvershootPercent']<=2
    assert metrics['registration']['distancePx']<=4
    assert metrics['openCompleteFrame']==138 and not duplicates
    (ART / 'qc-summary.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    sheet = Image.new('RGB',(1280,1580),'#eeeeec')
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate([12,91,143,163,180,196,211,347]):
        x,y=(i%2)*640,(i//2)*395
        sheet.paste(Image.open(frames[frame]).convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+12,y+365),f'{frame/60:.3f}s / {ledger[frame]["angle"]:.1f} deg',font=font,fill='#333333')
    sheet.save(ART/'contact-sheet.png')
    shell=Image.new('RGB',(1440,450),'white')
    for i,name in enumerate(['shell-closed.png','shell-open.png']):
        shell.paste(Image.open(ART/name).convert('RGB').resize((720,450),Image.Resampling.LANCZOS),(720*i,0))
    shell.save(ART/'shell-contact-sheet.png')
    light_sheet=Image.new('RGB',(1770,840),'#eeeeec')
    ld=ImageDraw.Draw(light_sheet)
    for i,(frame,label) in enumerate([(143,'Open dark'),(163,'Windows rising'),(180,'Buildings on'),(196,'Tower rising'),(211,'Hero'),(347,'Stable hold')]):
        x,y=(i%3)*590,(i//3)*420
        tile=Image.open(frames[frame]).convert('RGB').crop((375,115,1558,965)).resize((590,390),Image.Resampling.LANCZOS)
        light_sheet.paste(tile,(x,y))
        ld.text((x+12,y+392),f'{frame/60:.3f}s  {label}',font=font,fill='#333333')
    light_sheet.save(ART/'light-state-sheet.png')
    Image.open(frames[12]).crop((945,120,1555,965)).save(ART/'closed-ui-closeup.png')
    Image.open(frames[211]).crop((725,160,1135,425)).save(ART/'open-ui-closeup.png')
    Image.open(frames[211]).crop((380,800,1555,965)).save(ART/'open-bottom-no-indicator.png')
    print(json.dumps(metrics,indent=2))


if __name__ == '__main__':
    main()
