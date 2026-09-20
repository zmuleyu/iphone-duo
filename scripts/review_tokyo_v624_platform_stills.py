"""Mechanical validation for the screenshot-only v6.24 platform state pack."""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'artifacts/v6.24-tokyo-platform-stills'


def tower_shift(reference, candidate):
    a = cv2.imread(str(reference), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(candidate), cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1, margin = 2270, 420, 2620, 1520, 12
    template = cv2.Canny(a[y0:y1, x0:x1], 45, 110)
    search = cv2.Canny(b[y0-margin:y1+margin, x0-margin:x1+margin], 45, 110)
    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    shift = [location[0] - margin, location[1] - margin]
    return {'shiftPx': shift, 'distancePx': float(np.hypot(*shift)), 'score': float(score)}


def main():
    manifest = json.loads((OUT / 'state-manifest.json').read_text(encoding='utf-8'))
    states = manifest['states']
    assert manifest['videoGenerated'] is False and manifest['audioGenerated'] is False
    assert manifest['aspects']['authority4k'] == [3840, 2160]
    assert manifest['aspects']['downsample1080'] == [1920, 1080]
    assert len(states) == 8 and all(state['acceptance'] == 'pending-user' for state in states)
    pairs = []
    for state in states:
        p4 = OUT / state['clean4k']
        p1080 = OUT / state['clean1080']
        safe4 = OUT / state['safeReview4k']
        safe1080 = OUT / state['safeReview1080']
        assert Image.open(p4).size == (3840, 2160)
        assert Image.open(p1080).size == (1920, 1080)
        assert Image.open(safe4).size == (3840, 2160)
        assert Image.open(safe1080).size == (1920, 1080)
        expected = Image.open(p4).convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS)
        actual = Image.open(p1080).convert('RGB')
        diff = ImageChops.difference(expected, actual)
        assert diff.getbbox() is None, state['name']
        assert not any(state['ui'].values())
        assert state['focus']['leftRadius'] == 0 and state['focus']['rightRadius'] == 0
        pairs.append({'state': state['name'], 'frame': state['frame'], 'sha256': hashlib.sha256(p4.read_bytes()).hexdigest()})
    assert not list(OUT.rglob('*.mp4')) and not list(OUT.rglob('*.webm')) and not list(OUT.rglob('*.mov'))
    changed = [path for path, expected in manifest['frozenInputs'].items()
               if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected]
    assert not changed
    registration = tower_shift(OUT / states[5]['clean4k'], OUT / states[7]['clean4k'])
    assert registration['distancePx'] <= 1
    qc = {
        'status': 'state-pack / pending-user-review',
        'videoGenerated': False,
        'audioGenerated': False,
        'stateCount': len(states),
        'nativeAuthorityResolution': [3840, 2160],
        'downsampleResolution': [1920, 1080],
        'downsampleProvenance': 'Pixel-exact Pillow Lanczos resize from the corresponding 4K clean PNG',
        'screenUiVisible': False,
        'authoredScreenBlurRadius': 0,
        'fixedTowerOpenUnlitToHero': registration,
        'changedFrozenInputs': changed,
        'originalSizeVisualInspection': {
            'required': True,
            'performed': '4K clean Hero and 4K/1080 contact sheets inspected by the operator; visual acceptance remains pending user review.',
            'notProvenByMetrics': ['subject scale', 'dark-city readability', 'gold-tower hierarchy', 'safe-area judgment'],
        },
        'states': pairs,
    }
    (OUT / 'qc-summary.json').write_text(json.dumps(qc, indent=2), encoding='utf-8')
    print(json.dumps(qc, indent=2))


if __name__ == '__main__':
    main()
