"""Source-coordinate tower plates and static focus-world candidates, without generation."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_tokyo_v616_world_pair import sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'media/tokyo/candidates'
ART = ROOT / 'artifacts/v6.22-tokyo-focus-still-review'


def read(name):
    return np.array(Image.open(OUT / name).convert('RGB')).astype('float32')


def save(name, values):
    path = OUT / name
    Image.fromarray(np.rint(np.clip(values, 0, 255)).astype('uint8')).save(path, optimize=True)
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path)}


def overview(images, names, path, box=(1740, 80, 2230, 1430)):
    sheet = Image.new('RGB', (490 * len(images), 1410), '#eeeeee')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    draw = ImageDraw.Draw(sheet)
    for i, (image, label) in enumerate(zip(images, names)):
        sheet.paste(Image.fromarray(np.rint(np.clip(image, 0, 255)).astype('uint8')).crop(box), (490 * i, 0))
        draw.text((490 * i + 10, 1365), label, font=font, fill='#222222')
    sheet.save(path)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    a = read('reality-v6.19-natural.png')
    lit = read('redblack-v6.20-lit.png')
    mask = read('layers-v6.20-mask.png')
    overview([a, lit, mask], ['A natural / before', 'B gold / before', 'V6.20 matte / before'], ART / 'tower-source-before.png')
    frozen = sorted(p for p in OUT.glob('*.png') if any(v in p.name for v in ['v6.16', 'v6.18', 'v6.19', 'v6.20']))
    frozen += sorted((ROOT / 'artifacts').glob('v6.*-tokyo-silent-demo/*.mp4'))
    frozen += [ROOT / 'assets/iPhone_Duo_Render.usdc', ROOT / 'scripts/patch-shell-asset.py']
    hashes = {str(p.relative_to(ROOT)): sha256(p) for p in frozen}
    (ART / 'frozen-input-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    original_a = a.copy()
    lum = a @ np.array([.2126, .7152, .0722], dtype='float32')
    matte = mask.astype('uint8')
    # Remove only the two approved large source-photo obstructions, not the
    # platform window rails or fine dark truss lines. Donors are unscaled local
    # clean truss pixels from this same photograph, never generated geometry.
    repair = np.zeros(lum.shape, dtype='uint8')
    upper = np.zeros_like(repair)
    upper[735:805, 1968:2016] = lum[735:805, 1968:2016] < 65
    count, labels, stats, _ = cv2.connectedComponentsWithStats(upper, 8)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] >= 150:
            repair[labels == i] = 1
    lower = np.zeros_like(repair)
    lower[905:1160, 1968:2028] = lum[905:1160, 1968:2028] < 58
    lower = cv2.morphologyEx(lower, cv2.MORPH_OPEN, np.ones((7, 7), dtype='uint8'))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(lower, 8)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] >= 150:
            repair[labels == i] = 2
    # A one-pixel expanded footprint prevents the old dark rim surviving.
    for code, offset in [(1, 140), (2, 360)]:
        support = cv2.dilate((repair == code).astype('uint8'), np.ones((3, 3), dtype='uint8')) > 0
        ys, xs = np.where(support)
        donor = original_a[ys - offset, xs].copy()
        # Donor dark lines remain detailed, but do not transplant another
        # large near-black obstruction into the repaired region.
        donor_lum = donor @ np.array([.2126, .7152, .0722], dtype='float32')
        donor *= np.maximum(1, 58 / np.maximum(donor_lum, 1))[:, None]
        a[ys, xs] = donor
        matte[ys, xs] = [0, 255, 0]
        repair[ys, xs] = code
    # Lower support pixels must never be classified as city-window emission.
    foot_roi = np.zeros_like(repair)
    for polygon in [[(1807, 1290), (1898, 1260), (1902, 1368), (1815, 1368)],
                    [(1997, 1210), (2028, 1240), (2028, 1358), (1997, 1358)]]:
        cv2.fillPoly(foot_roi, [np.array(polygon, dtype='int32')], 1)
    foot = (foot_roi > 0) & (lit[:, :, 0] > 40) & (lit[:, :, 1] > 27) & (lit[:, :, 0] > lit[:, :, 2] * 1.8) & (lit[:, :, 1] > lit[:, :, 2] * 1.5) & (matte[:, :, 1] == 0)
    matte[foot] = [0, 255, 0]
    city, tower, windows = matte.transpose(2, 0, 1)
    tower_on, window_on = tower > 0, windows > 0
    alpha = tower[:, :, None] / 255.
    # Direct v6.19 photograph with bounded city-only crispness/shadow refinement.
    padded = np.pad(lum, 1, mode='edge')
    nearby = (padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]) * .25
    detail = np.clip((lum - nearby) * .22, -3.5, 3.5)
    bottom = np.clip((np.arange(1878)[:, None] / 1878 - .76) / .24, 0, 1)
    a += (detail + bottom * 2.1 * np.clip((65 - lum) / 65, 0, 1))[:, :, None] * (city[:, :, None] / 255.)
    natural_plate = np.dstack([np.where(tower_on[:, :, None], a, 0), tower])
    clean_lum = (a @ np.array([.2126, .7152, .0722], dtype='float32')) / 255.
    # Outline tint is INSIDE existing support; never dilate a halo into sky.
    outline = np.zeros_like(tower)
    contours, _ = cv2.findContours(tower_on.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(outline, contours, -1, 255, 2)
    edge = (outline > 0) & tower_on
    unlit = np.zeros_like(a)
    unlit[tower_on] = np.array([5., 3., 3.]) + clean_lum[tower_on, None] * [7., 3., 1.]
    unlit[edge] = np.array([29., 8., 5.]) + clean_lum[edge, None] * [10., 3., 1.]
    unlit_plate = np.dstack([unlit, tower])
    light_value = np.clip((clean_lum - .08) / .70, 0, 1) ** .80
    gold = np.zeros_like(a)
    gold[tower_on] = np.array([30., 19., 7.]) + light_value[tower_on, None] * [205., 157., 43.]
    gold_plate = np.dstack([gold, tower])
    strong = lit * (1 - alpha) + unlit * alpha
    weak = strong.copy()
    # 22% emitted light in linear space, with channel-monotonic ambient base.
    dark = read('redblack-v6.20-dormant.png')
    ambient = np.minimum(dark[window_on], strong[window_on]) / 255.
    def linear(c):
        return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    def srgb(c):
        return np.where(c <= .0031308, c * 12.92, 1.055 * np.maximum(c, 0) ** (1 / 2.4) - .055)
    weak[window_on] = srgb(linear(ambient) + .22 * (linear(strong[window_on] / 255.) - linear(ambient))) * 255
    hero = strong * (1 - alpha) + gold * alpha
    outputs = [save('reality-v6.22-clean-tower.png', a), save('redblack-v6.22-weak.png', weak),
               save('redblack-v6.22-strong.png', strong), save('redblack-v6.22-hero.png', hero),
               save('tower-v6.22-natural-rgba.png', natural_plate), save('tower-v6.22-unlit-rgba.png', unlit_plate),
               save('tower-v6.22-gold-rgba.png', gold_plate), save('layers-v6.22-mask.png', matte)]
    Image.fromarray(repair * 100).save(ART / 'tower-repair-support.png')
    overview([original_a, a, lit, hero], ['Closed before', 'Closed repaired', 'Gold before', 'Gold repaired'], ART / '08-tower-plate-before-after.png')
    overview([a, weak, strong, hero], ['Natural plate', 'Weak / dark copper edge', 'Strong / same unlit plate', 'Independent warm gold'], ART / 'tower-plate-states.png')
    def region_metrics(values, region):
        x0, y0, x1, y1 = region
        gray = values[y0:y1, x0:x1] @ np.array([.2126, .7152, .0722])
        n, _, stats, _ = cv2.connectedComponentsWithStats((gray < 45).astype('uint8'), 8)
        return {'meanLuminance': float(gray.mean()), 'nearBlackPixels': int(np.count_nonzero(gray < 45)),
                'largestNearBlackComponent': int(max(stats[1:, cv2.CC_STAT_AREA], default=0))}
    rois = {'upperObstruction': [1968, 735, 2016, 805], 'lowerCentralObstruction': [1968, 905, 2028, 1040]}
    evidence = {'status': 'still-candidate / pending-user-selection', 'video': None,
        'sourceGeometry': '2670x1878 identity; no global crop, warp or resampling',
        'repairMethod': 'Local source truss donor pixels, 1:1 unscaled within approved obstruction masks only; donor offsets -140y and -360y',
        'repairPixelCount': int(np.count_nonzero(repair)), 'reassignedFootPixels': int(np.count_nonzero(foot)),
        'cityTowerOverlapPixels': int(np.count_nonzero((city > 0) & tower_on)),
        'towerWindowOverlapPixels': int(np.count_nonzero(window_on & tower_on)),
        'outlineTintFractionOfTower': float(np.count_nonzero(edge) / np.count_nonzero(tower_on)),
        'outlineOutsideAlphaPixels': 0, 'unlitBodyMeanRGB': unlit[tower_on & ~edge].mean(axis=0).tolist(),
        'unlitOutlineMeanRGB': unlit[edge].mean(axis=0).tolist(),
        'repairROIs': {name: {'bounds': roi, 'closedBefore': region_metrics(original_a, roi), 'closedAfter': region_metrics(a, roi),
                            'goldBefore': region_metrics(lit, roi), 'goldAfter': region_metrics(hero, roi)} for name, roi in rois.items()},
        'windowMonotonicViolations': int(np.count_nonzero(np.rint(strong[window_on]) < np.rint(weak[window_on]))),
        'frozenInputsUnchanged': all(sha256(ROOT / p) == h for p, h in hashes.items()), 'outputs': outputs}
    (ART / 'asset-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in evidence.items() if k != 'outputs'}, indent=2))


if __name__ == '__main__':
    main()
