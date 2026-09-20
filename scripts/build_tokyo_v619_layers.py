"""Pixel-registered Tokyo A/B grading and source-mask cleanup for v6.19."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_tokyo_v616_world_pair import edge_metrics, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'media/tokyo/candidates'
ART = ROOT / 'artifacts/v6.19-tokyo-silent-demo'


def save(path, image):
    Image.fromarray(np.clip(np.rint(image), 0, 255).astype('uint8')).save(path, optimize=True)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    source = np.array(Image.open(ROOT / 'media/tokyo/reality-wikipedia.png').convert('RGB'))
    masks = np.array(Image.open(OUT / 'layers-v6.18-mask.png').convert('RGB'))
    if source.shape != (1878, 2670, 3) or masks.shape != source.shape:
        raise ValueError('Frozen source/masks must both be 2670x1878; no resizing allowed')
    city, tower = masks[:, :, 0], masks[:, :, 1]
    ca, ta = city[:, :, None] / 255., tower[:, :, None] / 255.
    f = source.astype('float32') / 255
    lum = np.sum(f * [0.2126, 0.7152, 0.0722], axis=2, keepdims=True)
    y = np.arange(source.shape[0], dtype='float32')[:, None, None] / source.shape[0]
    bottom = np.clip((y - 0.74) / 0.26, 0, 1)
    bottom = bottom * bottom * (3 - 2 * bottom)
    neutral = lum + 0.24 * (f - lum)
    sky = lum * [1.04, 1.025, 1.012] + 0.12 * (f - lum)
    natural = neutral * ca + sky * (1 - ca)
    natural += bottom * ca * (1 - np.sqrt(lum)) * 0.039

    # Window locations come from the photograph. Small connected components
    # are retained as irregular source-shaped groups, not placed on a grid.
    warm = (f[:, :, 0] - f[:, :, 2] > .16) & (f[:, :, 1] - f[:, :, 2] > .06)
    win = ((city > 0) & (tower == 0) & (lum[:, :, 0] > .36) & warm).astype('uint8')
    win = cv2.morphologyEx(win, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(win, 8)
    keep = np.zeros(count, bool)
    keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= 6) & (stats[1:, cv2.CC_STAT_AREA] <= 1500)
    window = keep[labels] & (city > 0) & (tower == 0)
    window_alpha = window[:, :, None].astype('float32')
    strength = np.clip((lum - .28) / .5, 0, 1)
    # Warm amber is a visual approximation of 2800 K, not a measured spectrum.
    amber = np.array([.55, .32, .115]) + strength * [.37, .33, .18]
    natural = natural * (1 - window_alpha * .72) + amber * window_alpha * .72
    tower_lum = np.clip(lum * 1.06, 0, 1)
    warm_white = tower_lum * [1.05, 1.027, .967]
    natural = natural * (1 - ta) + warm_white * ta

    # B retains shared skyline/tower alpha. Luminance-only bilateral cleanup
    # simplifies the tower surface without moving or replacing its structure.
    clean_lum = cv2.bilateralFilter((lum[:, :, 0] * 255).astype('uint8'), 5, 18, 3)[:, :, None] / 255.
    gold_value = np.clip((clean_lum - .095) / .68, 0, 1) ** .70
    gold = np.array([.09, .05, .012]) + gold_value * [.80, .62, .085]
    depth = np.clip((.77 - y) / .52, 0, 1)
    # Three depth anchor values blend continuously; hard horizontal thresholds
    # would create artificial stripes crossing unrelated buildings.
    dark = .027 + .048 * depth * depth * (3 - 2 * depth)
    city_b = np.broadcast_to(dark, f.shape).copy() * [1.04, 1.0, .94]
    city_b += (clean_lum - .14) * .024
    city_b = city_b * (1 - window_alpha) + amber * window_alpha
    rng = np.random.default_rng(619)
    # Fixed 0.65/255 dither breaks codec banding without a visible texture.
    dither = rng.uniform(-.65, .65, size=lum.shape) / 255
    red_sky = np.broadcast_to(np.array([.775, .014, .020]), f.shape) + dither
    redblack = red_sky * (1 - ca) + city_b * ca
    redblack = redblack * (1 - ta) + gold * ta
    a = np.clip(np.rint(natural * 255), 0, 255).astype('uint8')
    b = np.clip(np.rint(redblack * 255), 0, 255).astype('uint8')
    save(OUT / 'reality-v6.19-natural.png', a)
    save(OUT / 'redblack-v6.19-gold.png', b)
    packed = np.stack([city, tower, window.astype('uint8') * 255], axis=-1)
    save(OUT / 'layers-v6.19-mask.png', packed)
    overview = np.concatenate([cv2.resize(im, (890, 626), interpolation=cv2.INTER_AREA) for im in (source, a, b)], axis=1)
    save(ART / 'world-pair-overview.png', overview)
    save(ART / 'tower-ab.png', np.concatenate([a[70:1370,1760:2250], b[70:1370,1760:2250]], axis=1))
    evidence = {
        'resolution': [2670, 1878], 'geometryTransform': 'identity; no resize, crop, warp or device pixels',
        'cityMaskUnchanged': bool(np.array_equal(packed[:, :, 0], masks[:, :, 0])),
        'towerMaskUnchanged': bool(np.array_equal(packed[:, :, 1], masks[:, :, 1])),
        'ditherSeed': 619, 'skyDitherAmplitude8Bit': .65, 'windowComponents': int(keep.sum()),
        'towerRegistration': {'A': edge_metrics(source, a, tower), 'B': edge_metrics(source, b, tower)},
        'outputs': {name: sha256(OUT / name) for name in ['reality-v6.19-natural.png','redblack-v6.19-gold.png','layers-v6.19-mask.png']},
        'source': 'Existing user-confirmed Wikipedia photographic authority only',
        'notes': 'A: neutral sky, lower 26% lifted, warm amber windows, warm-white tower. B: continuous transition through three depth tones, source-shaped windows, dark gold tower, fixed sub-code-value dither; no halo.'
    }
    (ART / 'asset-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
