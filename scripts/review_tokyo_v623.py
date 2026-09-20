"""QC the v6.23 fixed-frame master and produce motion review sheets."""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'artifacts/v6.23-tokyo-silent-video'
FRAME_COUNT = 360
FPS = 60


def max_delta(a, b):
    diff = ImageChops.difference(Image.open(a).convert('RGB'), Image.open(b).convert('RGB'))
    return max(value[1] for value in diff.getextrema())


def laplacian(path, roi):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1 = roi
    return float(cv2.Laplacian(image[y0:y1, x0:x1], cv2.CV_64F).var())


def fixed_tower_shift(open_path, compare_path):
    opened = cv2.imread(str(open_path), cv2.IMREAD_GRAYSCALE)
    compare = cv2.imread(str(compare_path), cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1, margin = 1160, 210, 1310, 760, 10
    template = cv2.Canny(opened[y0:y1, x0:x1], 45, 110)
    search = cv2.Canny(compare[y0-margin:y1+margin, x0-margin:x1+margin], 45, 110)
    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    shift = [location[0] - margin, location[1] - margin]
    return {'shiftPx': shift, 'distancePx': float(np.hypot(*shift)), 'score': float(score)}


def sheet(items, path, columns=2, tile=(640, 360)):
    rows = (len(items) + columns - 1) // columns
    output = Image.new('RGB', (tile[0] * columns, rows * (tile[1] + 42)), '#eeeeec')
    draw = ImageDraw.Draw(output)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    for index, (image_path, label) in enumerate(items):
        x = (index % columns) * tile[0]
        y = (index // columns) * (tile[1] + 42)
        image = Image.open(image_path).convert('RGB').resize(tile, Image.Resampling.LANCZOS)
        output.paste(image, (x, y))
        draw.text((x + 10, y + tile[1] + 9), label, font=font, fill='#242424')
    output.save(path)


def main():
    frames = sorted((ART / 'frames').glob('frame_*.png'))
    ledger = json.loads((ART / 'frame-ledger.json').read_text(encoding='utf-8'))
    angle_frames = json.loads((ART / 'angle-frames.json').read_text(encoding='utf-8'))
    assert len(frames) == FRAME_COUNT
    assert [path.name for path in frames] == [f'frame_{i:06d}.png' for i in range(FRAME_COUNT)]
    assert [entry['frame'] for entry in ledger] == list(range(FRAME_COUNT))

    unfold_start, open_frame = 138, 222
    tower_start, tower_complete = 250, 288
    first_open = next(entry['frame'] for entry in ledger if entry['angle'] == 180)
    first_tower = next(entry['frame'] for entry in ledger if entry['layers']['towerLight'] > 0)
    first_gold = next(entry['frame'] for entry in ledger if entry['layers']['towerLight'] == 1)
    duplicates = [index for index in range(unfold_start + 1, open_frame + 1)
                  if ledger[index]['sha256'] == ledger[index - 1]['sha256']]
    unexpected_duplicates = [index for index in duplicates if index > unfold_start + 1]
    assert first_open == open_frame
    assert first_tower == tower_start
    assert first_gold == tower_complete
    # One sub-pixel settle frame immediately after the 2.30 s hold is allowed;
    # no duplicate is allowed once visible travel begins.
    assert not unexpected_duplicates
    assert all(entry['layers']['towerLight'] == 0 for entry in ledger[:tower_start])
    assert all(entry['layers']['windowsLight'] == 1 for entry in ledger[216:])
    assert all(entry['focus']['leftRadius'] == 0 and entry['focus']['rightRadius'] == 0 for entry in ledger)
    assert all(not any(entry['ui'].values()) for entry in ledger)
    assert all(entry['layers']['coverChrome'] == 0 and entry['layers']['innerChrome'] == 0 for entry in ledger)

    pause_delta = max_delta(frames[open_frame], frames[249])
    hero_delta = max_delta(frames[tower_complete], frames[359])
    assert pause_delta == 0
    assert hero_delta == 0

    old_blurred = ROOT / 'artifacts/v6.22-tokyo-focus-still-review/03-fold-110deg-left-blurred.png'
    left_roi = [790, 520, 925, 865]
    frame110 = frames[angle_frames['110']]
    sharpness = {'v623At110': laplacian(frame110, left_roi)}
    if old_blurred.exists():
        sharpness['v622BlurredAt110'] = laplacian(old_blurred, left_roi)
        sharpness['improvementRatio'] = sharpness['v623At110'] / max(sharpness['v622BlurredAt110'], 1e-9)
        assert sharpness['improvementRatio'] >= 5

    tower_registration = fixed_tower_shift(frames[open_frame], frames[angle_frames['150']])
    assert tower_registration['distancePx'] <= 1
    asset = json.loads((ART / 'asset-evidence.json').read_text(encoding='utf-8'))
    assert 1.08 <= asset['towerToLocalCityRatio'] <= 1.12
    frozen = json.loads((ART / 'frozen-input-hashes.json').read_text(encoding='utf-8'))
    changed = [path for path, expected in frozen.items()
               if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected]
    assert not changed

    metrics = {
        'status': 'video-candidate / pending-user-review',
        'numberedFrames': FRAME_COUNT,
        'frameInterval': [0, FRAME_COUNT],
        'authoredDurationSeconds': FRAME_COUNT / FPS,
        'fps': FPS,
        'timelineFrames': {
            'closedHoldEnd': unfold_start,
            'openComplete': open_frame,
            'pauseEnd': 249,
            'towerActivationStart': tower_start,
            'towerActivationComplete': tower_complete,
            'heroEnd': 359,
        },
        'angleFrames': angle_frames,
        'motionDuplicateFrameIndices': duplicates,
        'unexpectedMotionDuplicateFrameIndices': unexpected_duplicates,
        'openPauseMaxChannelDelta': pause_delta,
        'heroHoldMaxChannelDelta': hero_delta,
        'authoredBlurRadius': 0,
        'screenUiVisible': False,
        'towerGoldBeforeOpen': False,
        'unlitTowerToLocalCityRatio': asset['towerToLocalCityRatio'],
        'sharpnessAt110': sharpness,
        'fixedTower150To180': tower_registration,
        'consoleErrors': json.loads((ART / 'console-errors.json').read_text(encoding='utf-8')),
        'changedFrozenInputs': changed,
        'method': 'Synchronous WebGL render to one numbered PNG per frame; frame index owns time',
    }
    assert not metrics['consoleErrors']
    (ART / 'qc-summary.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')

    angles = [(angle_frames[str(angle)], f'{angle} deg / frame {angle_frames[str(angle)]}')
              for angle in [90, 110, 150, 180]]
    sheet([(frames[frame], label) for frame, label in angles], ART / 'fold-continuity-sheet.png')
    beats = [(60, '1.00s Closed Reality'), (138, '2.30s unfold begins'),
             (angle_frames['110'], 'fold / 110 deg, no authored blur'),
             (angle_frames['150'], 'fold / 150 deg, fixed panorama'),
             (222, '3.70s Open Unlit'), (249, '4.15s pause complete'),
             (268, '4.47s tower activating'), (288, '4.80s Gold complete'),
             (359, '5.98s clean Hero')]
    sheet([(frames[frame], label) for frame, label in beats], ART / 'review-contact-sheet.png')
    Image.open(frames[359]).crop((1030, 90, 1570, 960)).save(ART / 'final-right-screen-clean.png')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
