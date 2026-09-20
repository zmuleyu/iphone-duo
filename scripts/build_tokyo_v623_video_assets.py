"""Build v6.23 RedBlack states from the accepted v6.22 registered tower plates."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_tokyo_v616_world_pair import sha256


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'media/tokyo/candidates'
ART = ROOT / 'artifacts/v6.23-tokyo-silent-video'


def read(name, mode='RGB'):
    return np.array(Image.open(MEDIA / name).convert(mode)).astype('float32')


def save(name, values, mode='RGB'):
    path = MEDIA / name
    Image.fromarray(np.rint(np.clip(values, 0, 255)).astype('uint8'), mode).save(path, optimize=True)
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path)}


def main():
    ART.mkdir(parents=True, exist_ok=True)
    reality = read('reality-v6.22-clean-tower.png')
    weak22 = read('redblack-v6.22-weak.png')
    strong22 = read('redblack-v6.22-strong.png')
    mask = read('layers-v6.22-mask.png').astype('uint8')
    gold22 = read('tower-v6.22-gold-rgba.png', 'RGBA')
    tower = mask[:, :, 1]
    tower_on = tower > 0
    alpha = tower[:, :, None] / 255.
    clean_lum = (reality @ np.array([.2126, .7152, .0722], dtype='float32')) / 255.

    # Keep the tower near-black, but about 8–12% brighter than its local city.
    # Copper is restricted to the existing tower support; there is no dilation,
    # halo or bloom outside the registered alpha.
    outline = np.zeros_like(tower)
    contours, _ = cv2.findContours(tower_on.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(outline, contours, -1, 255, 2)
    edge = (outline > 0) & tower_on
    unlit = np.zeros_like(reality)
    unlit[tower_on] = np.array([11., 6., 4.]) + clean_lum[tower_on, None] * [16., 7., 3.]
    unlit[edge] = np.array([45., 14., 8.]) + clean_lum[edge, None] * [18., 7., 3.]
    unlit_plate = np.dstack([unlit, tower])

    weak23 = weak22 * (1 - alpha) + unlit * alpha
    strong23 = strong22 * (1 - alpha) + unlit * alpha
    gold = gold22[:, :, :3]
    hero23 = strong23 * (1 - alpha) + gold * alpha
    outputs = [
        save('redblack-v6.23-weak.png', weak23),
        save('redblack-v6.23-strong.png', strong23),
        save('redblack-v6.23-hero.png', hero23),
        save('tower-v6.23-unlit-rgba.png', unlit_plate, 'RGBA'),
    ]

    luminance = weak23 @ np.array([.2126, .7152, .0722], dtype='float32')
    local = np.zeros(tower.shape, dtype=bool)
    local[450:1450, 1650:2300] = True
    city = mask[:, :, 0] > 0
    tower_mean = float(luminance[tower_on].mean())
    city_mean = float(luminance[city & local & ~tower_on].mean())
    ratio = tower_mean / city_mean
    evidence = {
        'status': 'video-candidate-input',
        'sourceGeometry': '2670x1878 identity; v6.22 tower support reused byte-for-byte',
        'towerMeanLuminance': tower_mean,
        'localCityMeanLuminance': city_mean,
        'towerToLocalCityRatio': ratio,
        'targetRatio': [1.08, 1.12],
        'outlineFractionOfTower': float(np.count_nonzero(edge) / np.count_nonzero(tower_on)),
        'outlineOutsideAlphaPixels': 0,
        'unlitBodyMeanRGB': unlit[tower_on & ~edge].mean(axis=0).tolist(),
        'unlitOutlineMeanRGB': unlit[edge].mean(axis=0).tolist(),
        'inputs': {
            name: sha256(MEDIA / name) for name in [
                'reality-v6.22-clean-tower.png',
                'redblack-v6.22-weak.png',
                'redblack-v6.22-strong.png',
                'layers-v6.22-mask.png',
                'tower-v6.22-gold-rgba.png',
            ]
        },
        'outputs': outputs,
    }
    if not 1.08 <= ratio <= 1.12:
        raise RuntimeError(f'unlit tower luminance ratio outside target: {ratio:.4f}')
    (ART / 'asset-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
