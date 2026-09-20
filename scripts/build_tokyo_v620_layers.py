"""Build dormant Tokyo worlds and mutually exclusive, registered light layers."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_tokyo_v616_world_pair import polygon_mask, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'media/tokyo/candidates'
ART = ROOT / 'artifacts/v6.20-tokyo-silent-demo'


def save(path, data):
    Image.fromarray(np.rint(np.clip(data, 0, 255)).astype('uint8')).save(path, optimize=True)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    frozen = sorted(p for p in OUT.glob('*.png') if any(v in p.name for v in ['v6.16','v6.18','v6.19']))
    frozen += [ROOT/'assets/iPhone_Duo_Render.usdc', ROOT/'scripts/patch-shell-asset.py']
    frozen_hashes = {str(p.relative_to(ROOT)):sha256(p) for p in frozen}
    (ART/'frozen-input-hashes.json').write_text(json.dumps(frozen_hashes,indent=2),encoding='utf-8')
    source = np.array(Image.open(ROOT/'media/tokyo/reality-wikipedia.png').convert('RGB'))
    old = np.array(Image.open(OUT/'layers-v6.19-mask.png').convert('RGB'))
    if source.shape != (1878,2670,3) or old.shape != source.shape:
        raise ValueError('Registered 2670x1878 source and masks required; no resizing')
    f = source.astype('float32')/255
    lum = np.sum(f * np.array([.2126,.7152,.0722],dtype='float32'),axis=2)
    old_city, old_tower, old_windows = old.transpose(2,0,1)

    # Two opaque observation decks: include their actual dark panel/window
    # structure instead of allowing city-black or red sky through the deck.
    # Coordinates are source-aligned 1864x1312 annotation coordinates, as in
    # the existing v6.16 matte builder; neither tower outline nor image moves.
    upper_deck = polygon_mask([(1380,274),(1410,274),(1414,312),(1414,342),
                               (1410,351),(1380,351),(1375,342),(1375,307)])
    main_deck = polygon_mask([(1347,560),(1440,560),(1450,570),(1450,599),
                              (1444,604),(1445,629),(1438,636),(1345,636),
                              (1335,629),(1335,603),(1329,596),(1335,570)])
    deck = np.maximum(upper_deck,main_deck)
    tower = np.maximum(old_tower,deck)
    city = np.where(tower > 0,0,old_city).astype('uint8')
    windows = (old_windows > 0) & (city > 0)
    ta, ca = tower[:,:,None]/255., city[:,:,None]/255.
    opacity = np.maximum(old_city,tower)[:,:,None]/255.

    # Remove photographic emission before grading A. Retain facade edges and
    # ambient reflections; only source-local lamp pixels receive the fill.
    warm = (f[:,:,0]-f[:,:,2]>.07) & (f[:,:,1]-f[:,:,2]>.025)
    lamp = ((old_city>0)&(tower==0)&((warm&(lum>.17))|(lum>.25))).astype('uint8')*255
    lamp = np.maximum(lamp,windows.astype('uint8')*255)
    ambient_lum = cv2.inpaint((lum*255).astype('uint8'),lamp,2,cv2.INPAINT_TELEA).astype('float32')/255
    y = np.arange(1878,dtype='float32')[:,None]/1878
    lower = np.clip((y-.75)/.25,0,1)
    lower = lower*lower*(3-2*lower)
    sky = lum[:,:,None]*np.array([.83,.94,1.08]) + (f-lum[:,:,None])*.065
    city_lum = np.clip(ambient_lum*.76 + .022 + lower*.026,0,1)
    city_a = city_lum[:,:,None]*np.array([.87,.94,1.025])
    city_a += (f-lum[:,:,None])*.045*(1-lamp[:,:,None]/255)
    # Ambient steel remains readable; bright source lamp hotspots are not
    # retained as illumination in the cover or any unfolding frame.
    clean_lum = cv2.bilateralFilter((lum*255).astype('uint8'),5,18,3).astype('float32')/255
    metal_lum = .045 + np.power(clean_lum,.76)*.30
    ambient_steel = metal_lum[:,:,None]*np.array([.88,.96,1.04])
    a = sky*(1-opacity) + city_a*opacity
    a = a*(1-ta) + ambient_steel*ta

    depth = np.clip((.77-y)/.52,0,1)
    dark_lum = .027 + .048*depth*depth*(3-2*depth)
    city_dark = np.broadcast_to(dark_lum[:,:,None],f.shape).copy()*[1.02,1,.98]
    city_dark += (clean_lum[:,:,None]-.14)*.018
    rng=np.random.default_rng(620)
    red = np.broadcast_to(np.array([.775,.014,.020]),f.shape)+rng.uniform(-.65,.65,size=lum.shape)[:,:,None]/255
    b_dark = red*(1-opacity)+city_dark*opacity
    b_dark = b_dark*(1-ta) + ambient_steel*ta

    # Surface light does not alter alpha. Deck shadow panels stay bronze/dark;
    # city cannot occupy any tower pixel, even while the tower is unlit.
    light_value = np.clip((clean_lum-.08)/.70,0,1)**.80
    gold = np.array([.105,.068,.022])+light_value[:,:,None]*[.80,.62,.10]
    strength = np.clip((lum-.28)/.5,0,1)[:,:,None]
    amber = np.array([.44,.235,.07])+strength*[.36,.31,.16]
    wa=windows[:,:,None].astype('float32')
    b_lit = b_dark*(1-wa)+amber*wa
    b_lit = b_lit*(1-ta)+gold*ta

    # Four depth bands, each split into three sparse, monotonic cohorts.
    count, labels, stats, centers = cv2.connectedComponentsWithStats(windows.astype('uint8'),8)
    ranks=np.zeros(count,dtype='float32')
    for i in range(1,count):
        distance=np.clip((centers[i,1]/1878-.32)/.68,0,.999)
        band=int(distance*4)
        cohort=int(centers[i,0]//37)%3
        ranks[i]=band*.23+cohort*.05
    rank=ranks[labels]
    # Extend each window's rank into its surrounding transparent area. A zero
    # rank outside the mask would average into edge texels and make near-window
    # edges wake too early under bilinear filtering.
    _, nearest = cv2.distanceTransformWithLabels((~windows).astype('uint8'),
        cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    rank_lookup=np.zeros(int(nearest.max())+1,dtype='float32')
    rank_lookup[nearest[windows]]=rank[windows]
    rank=rank_lookup[nearest]
    packed=np.stack([city,tower,windows.astype('uint8')*255],axis=-1)
    outputs={'reality-v6.20-dormant.png':a*255,'redblack-v6.20-dormant.png':b_dark*255,
             'redblack-v6.20-lit.png':b_lit*255,'layers-v6.20-mask.png':packed,
             'light-rank-v6.20.png':np.repeat(rank[:,:,None]*255,3,axis=2)}
    for name,data in outputs.items(): save(OUT/name,data)
    save(ART/'tower-matte.png',tower)
    save(ART/'city-exclusive-matte.png',city)
    save(ART/'window-matte.png',windows.astype('uint8')*255)
    save(ART/'tower-matte-repair.png',np.where((tower>0)&(old_tower==0),255,0))
    overview=np.concatenate([cv2.resize(im,(890,626),interpolation=cv2.INTER_AREA)
                            for im in [a*255,b_dark*255,b_lit*255]],axis=1)
    save(ART/'world-lighting-overview.png',overview)
    old_b=np.array(Image.open(OUT/'redblack-v6.19-gold.png').convert('RGB'))
    crop=(slice(320,960),slice(1860,2120))
    tiles=[old_b[crop],np.repeat(old_tower[crop][:,:,None],3,axis=2),
           np.repeat(tower[crop][:,:,None],3,axis=2),(b_dark*255)[crop],(b_lit*255)[crop]]
    save(ART/'tower-cleanup-before-after.png',np.concatenate(tiles,axis=1))
    evidence={'resolution':[2670,1878],'transform':'identity; no crop, warp, device or camera changes',
        'oldTowerCityOverlapPixels':int(((old_city>0)&(old_tower>0)).sum()),
        'newTowerCityOverlapPixels':int(((city>0)&(tower>0)).sum()),
        'opaqueDeckRepairPixels':int(((tower>0)&(old_tower==0)).sum()),
        'windowComponents':int(count-1),'windowRankRange':[float(ranks[1:].min()),float(ranks.max())],
        'lightsOffMethod':'source-local photographic lamp suppression and ambient-only steel; no glow',
        'towerRepair':'source-aligned opaque decks + exclusive city/tower ownership; structural luminance retained',
        'windowOrder':'4 far-to-near depth bands x 3 fixed spatial cohorts; one monotonic activation per component',
        'rankSampling':'nearest-window rank extension prevents filtered edge pixels from activating early',
        'outputs':{name:sha256(OUT/name) for name in outputs},
        'frozenInputsUnchanged':all(sha256(ROOT/p)==h for p,h in frozen_hashes.items()),
        'source':'Existing user-confirmed Wikipedia photographic authority only'}
    (ART/'asset-evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__': main()
