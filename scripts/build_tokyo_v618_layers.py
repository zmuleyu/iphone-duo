"""Derive the v6.18 natural A and source-registered masks without resampling.

This is an authored color transform of the existing Wikipedia-origin photo,
not generative image editing. v6.16 accepted masters are immutable inputs.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_tokyo_v616_world_pair import build_masks, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'media/tokyo/candidates'
ART = ROOT / 'artifacts/v6.18-tokyo-silent-demo'


def main():
    ART.mkdir(parents=True, exist_ok=True)
    source = np.array(Image.open(ROOT / 'media/tokyo/candidates/reality-v6.16-astra-master.png').convert('RGB'))
    if source.shape != (1878, 2670, 3):
        raise ValueError('Expected frozen 2670x1878 Reality master; refusing to resize')
    city_path = ROOT / 'artifacts/v6.16-tokyo-world-pair/city-mask.png'
    tower_path = ROOT / 'artifacts/v6.16-tokyo-world-pair/tower-mask.png'
    if city_path.exists() and tower_path.exists():
        city = np.array(Image.open(city_path).convert('L'))
        tower = np.array(Image.open(tower_path).convert('L'))
    else:
        # Rebuild from the same original photographic authority, never A's grade.
        original = np.array(Image.open(ROOT / 'media/tokyo/reality-wikipedia.png').convert('RGB'))
        city, tower, _, _ = build_masks(original)
    if city.shape != source.shape[:2] or tower.shape != source.shape[:2]:
        raise ValueError('Source-derived masks must match the frozen master exactly')
    masks = np.stack([city, tower, np.zeros_like(city)], axis=-1)
    Image.fromarray(masks).save(OUT / 'layers-v6.18-mask.png', optimize=True)

    f = source.astype(np.float32) / 255
    lum = np.sum(f * np.array([0.2126, 0.7152, 0.0722]), axis=2, keepdims=True)
    # Reduce blue/orange chroma without flattening the photographic building
    # detail. Preserve luminance; a neutral, slightly warm tower contrasts B.
    natural = lum + (f - lum) * 0.28
    natural *= np.array([1.025, 1.012, 0.98])
    tower_alpha = (cv2.GaussianBlur(tower, (3, 3), 0.42) / 255)[:, :, None]
    warm_white = np.clip(lum * np.array([1.07, 1.035, 0.965]), 0, 1)
    natural = natural * (1 - tower_alpha) + warm_white * tower_alpha
    natural = np.rint(np.clip(natural, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(natural).save(OUT / 'reality-v6.18-natural.png', optimize=True)
    b = np.array(Image.open(OUT / 'redblack-v6.16-astra-master.png').convert('RGB'))
    overview = np.concatenate([cv2.resize(im, (890, 626), interpolation=cv2.INTER_AREA) for im in (source, natural, b)], axis=1)
    Image.fromarray(overview).save(ART / 'world-pair-overview.png')
    evidence = {
        'resolution': [source.shape[1], source.shape[0]],
        'geometryTransform': 'identity; no crop, warp, resize, blur or generative reconstruction of A',
        'colorTransform': '28% source chroma, preserved luminance, masked warm-white tower',
        'layers': 'R city, G tower; same source-derived v6.16 segmentation',
        'inputs': {
            name: sha256(OUT / name) for name in ['reality-v6.16-astra-master.png', 'redblack-v6.16-astra-master.png']
        },
        'outputs': {name: sha256(OUT / name) for name in ['reality-v6.18-natural.png', 'layers-v6.18-mask.png']},
        'source': 'Existing user-confirmed Wikipedia record; no new source assertion or publication authority',
    }
    (ART / 'asset-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
