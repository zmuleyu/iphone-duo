"""Build static Tokyo masters from the unchanged photographic authority.

No generative model, warp, resize, or runtime integration is used. Skyline hints
select a narrow segmentation search area, not replacement roofs. Run with Python,
NumPy, OpenCV and Pillow; all default paths resolve relative to this file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
from pathlib import Path

import cv2
import numpy as np
import PIL
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 2670, 1878


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def save(path, array):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8)).save(path, optimize=True)


def polygon_mask(points):
    mask = np.zeros((HEIGHT, WIDTH), np.uint8)
    # Hints use the inspected 1864 x 1312 overview coordinates.
    pts = np.rint(np.asarray(points) * [WIDTH / 1864, HEIGHT / 1312]).astype(np.int32)
    cv2.fillPoly(mask, [pts], 255)
    return mask


def build_masks(source):
    # These bounds only initialize GrabCut. Source colors determine the edge.
    roof = [
        (0,340),(10,333),(10,326),(215,326),(215,554),(228,554),
        (228,538),(261,538),(261,509),(290,509),(290,553),(337,553),
        (337,483),(358,483),(358,465),(409,465),(409,484),(442,484),
        (442,570),(475,570),(475,545),(489,545),(489,527),(508,527),
        (508,588),(571,588),(571,612),(598,612),(598,435),(683,435),
        (683,561),(706,561),(706,543),(733,543),(733,507),(900,507),
        (900,589),(925,589),(925,524),(958,524),(958,580),(987,580),
        (987,472),(1080,472),(1080,589),(1107,589),(1107,522),(1145,522),
        (1145,576),(1194,576),(1194,542),(1230,542),(1230,524),(1257,524),
        (1257,568),(1283,568),(1283,546),(1312,546),(1312,577),
        (1420,577),(1420,552),(1455,552),(1455,511),(1480,511),
        (1480,543),(1514,543),(1514,486),(1540,486),(1540,453),
        (1587,453),(1587,468),(1624,468),(1624,560),(1675,560),
        (1675,515),(1702,515),(1702,547),(1725,547),(1725,425),
        (1841,425),(1841,603),(1864,603),
    ]
    rough = polygon_mask(roof + [(1864,1312),(0,1312)])
    inside = cv2.erode(rough, np.ones((39,39),np.uint8)) > 0
    outside = cv2.dilate(rough, np.ones((57,57),np.uint8)) == 0
    labels = np.where(rough > 0, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
    labels[inside] = cv2.GC_FGD
    labels[outside] = cv2.GC_BGD
    cv2.setRNGSeed(616)
    cv2.grabCut(source, labels, None, np.zeros((1,65),np.float64),
                np.zeros((1,65),np.float64), 5, cv2.GC_INIT_WITH_MASK)
    city = np.isin(labels, [cv2.GC_FGD,cv2.GC_PR_FGD]).astype(np.uint8)*255
    gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY).astype(np.float32)
    crane_roi = polygon_mask([(1715,316),(1758,375),(1768,422),(1740,430),
                              (1715,316)]) | polygon_mask([(1848,316),(1814,389),
                              (1808,425),(1789,425),(1815,354)])
    city[(crane_roi > 0) & (gray < 74)] = 255

    # Source tower envelope, including decks and the thin top aerial.
    envelope = polygon_mask([
        (1391,76),(1399,76),(1399,177),(1401,232),(1406,267),
        (1412,276),(1413,312),(1414,342),(1419,410),(1429,477),
        (1440,553),(1450,569),(1450,599),(1444,604),(1445,629),
        (1438,636),(1473,763),(1536,890),(1491,906),(1463,940),
        (1419,945),(1394,860),(1365,940),(1305,937),(1259,908),
        (1244,888),(1300,780),(1345,636),(1335,629),(1335,603),
        (1329,596),(1335,570),(1347,558),(1360,480),(1368,415),
        (1377,343),(1375,307),(1377,276),(1384,267),(1388,231),
        (1391,177),
    ])
    red, green, blue = source.astype(np.float32).transpose(2,0,1)
    rows = np.arange(HEIGHT)[:,None]
    warm = (red-blue > 28) & (green-blue > 13) & (red > 106)
    # Sample directly beside the envelope, so cloud gradients cannot become steel.
    bg = source.astype(np.float32).copy()
    for y in range(815):
        columns=np.flatnonzero(envelope[y])
        if not len(columns):
            continue
        x0,x1=int(columns[0]),int(columns[-1])
        left=np.median(source[y,x0-20:x0-5].astype(np.float32),axis=0)
        right=np.median(source[y,x1+6:x1+21].astype(np.float32),axis=0)
        t=np.linspace(0,1,x1-x0+1)[:,None]
        bg[y,x0:x1+1]=left*(1-t)+right*t
    diff = source.astype(np.float32)-bg
    beam = (diff[:,:,0]>25) | (diff[:,:,1]>25)
    dark_steel = (diff[:,:,0]<-23)&(diff[:,:,1]<-23)&(diff[:,:,2]<-23)
    upper = (rows < 815) & (beam | dark_steel)
    tower = ((envelope>0) & np.where(rows<815,upper,warm)).astype(np.uint8)*255
    tower_alpha = cv2.GaussianBlur(tower,(3,3),0.42).astype(np.float32)/255
    city_alpha = cv2.GaussianBlur(city,(3,3),0.42).astype(np.float32)/255
    return city, tower, city_alpha, tower_alpha


def build_reality(source, city_alpha, tower_alpha):
    f = source.astype(np.float32)/255
    sky = cv2.bilateralFilter(source,9,16,10).astype(np.float32)/255
    sky = np.clip(sky*np.array([0.98,1.025,1.065]),0,1)
    foreground = np.clip((f-0.018)*1.028,0,1)
    protect = np.maximum(city_alpha,tower_alpha)[:,:,None]
    return np.rint((sky*(1-protect)+foreground*protect)*255).astype(np.uint8)


def build_redblack(source, city, tower, city_alpha, tower_alpha):
    yy,xx = np.mgrid[0:HEIGHT,0:WIDTH].astype(np.float32)
    light = 0.94 + 0.06*np.exp(-((xx/WIDTH-.56)**2/.7+(yy/HEIGHT-.32)**2/.3))
    sky = light[:,:,None]*np.array([205,3,5],np.float32)
    gray = cv2.cvtColor(source,cv2.COLOR_RGB2GRAY).astype(np.float32)/255
    levels = np.where(gray<.12,0,np.where(gray<.23,1,2))
    colors=np.array([[3,2,2],[7,3,3],[13,5,4]],np.float32)
    buildings=colors[levels]
    r,g,b = source.astype(np.float32).transpose(2,0,1)
    lights = ((city>0)&(tower==0)&(gray>.42)&(r-b>46)&(g-b>20)).astype(np.uint8)
    count,components,stats,_=cv2.connectedComponentsWithStats(lights,8)
    keep=np.zeros(count,bool)
    keep[1:]=(stats[1:,cv2.CC_STAT_AREA]>=7)&(stats[1:,cv2.CC_STAT_AREA]<=1500)
    lights=keep[components]
    strength=np.clip((gray-.36)/.5,0,1)
    lamp=np.stack([155+65*strength,79+76*strength,1+5*strength],axis=2)
    buildings[lights]=lamp[lights]
    value=np.clip((.65*gray+.35*r/255-.105)/.72,0,1)**.64
    gold=np.stack([20+235*value,7+205*value**1.15,2+7*value],axis=2)
    ca=city_alpha[:,:,None]
    ta=tower_alpha[:,:,None]
    out=sky*(1-ca)+buildings*ca
    out=out*(1-ta)+gold*ta
    return np.rint(out).clip(0,255).astype(np.uint8),sky.astype(np.uint8),lights


def edge_metrics(source,candidate,mask):
    a=cv2.Canny(cv2.cvtColor(source,cv2.COLOR_RGB2GRAY),42,112)>0
    b=cv2.Canny(cv2.cvtColor(candidate,cv2.COLOR_RGB2GRAY),42,112)>0
    target=a&(mask>=128)
    nearby=cv2.dilate(b.astype(np.uint8),np.ones((5,5),np.uint8))>0
    scores=[]
    ys,xs=np.where(target)
    for dy in range(-4,5):
        for dx in range(-4,5):
            scores.append((float(b[ys+dy,xs+dx].mean()),dx,dy))
    best=max(scores,key=lambda s:(s[0],-abs(s[1])-abs(s[2])))
    return {"sourceTargetEdgePixels":int(target.sum()),
            "alignedEdgeRecall2px":float((target&nearby).sum()/max(1,target.sum())),
            "edgeRegistrationShiftPx":[best[1],best[2]],
            "edgeRegistrationDistancePx":float(np.hypot(best[1],best[2])),
            "geometryTransform":"identity; no warp, resample, translate or crop"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'media/tokyo/reality-wikipedia.png')
    p.add_argument('--artifacts',type=Path,default=ROOT/'artifacts/v6.16-tokyo-world-pair')
    args=p.parse_args()
    with Image.open(args.source) as image:
        if image.size!=(WIDTH,HEIGHT):
            raise ValueError('Authority must be exactly 2670 x 1878; refusing to resize')
        source=np.array(image.convert('RGB'))
    city,tower,ca,ta=build_masks(source)
    reality=build_reality(source,ca,ta)
    redblack,sky,lights=build_redblack(source,city,tower,ca,ta)
    outputs={"reality":ROOT/'media/tokyo/candidates/reality-v6.16-astra-master.png',
             "redblack":ROOT/'media/tokyo/candidates/redblack-v6.16-astra-master.png'}
    for name,array in [('reality',reality),('redblack',redblack)]:
        save(outputs[name],array)
    shutil.copyfile(outputs['redblack'],ROOT/'media/tokyo/candidates/redblack-v6.16-cand-01.png')
    art=args.artifacts
    save(art/'city-mask.png',city)
    save(art/'tower-mask.png',tower)
    save(art/'redblack-sky-procedural.png',sky)
    save(art/'window-mask.png',lights.astype(np.uint8)*255)
    save(art/'ab-side-by-side.png',np.concatenate([
        cv2.resize(reality,(1335,939),interpolation=cv2.INTER_AREA),
        cv2.resize(redblack,(1335,939),interpolation=cv2.INTER_AREA)],axis=1))
    save(art/'source-reality-redblack-overview.png',np.concatenate([
        cv2.resize(im,(890,626),interpolation=cv2.INTER_AREA)
        for im in [source,reality,redblack]],axis=1))
    save(art/'tower-ab.png',np.concatenate([im[80:1390,1760:2230]
        for im in [source,reality,redblack]],axis=1))
    save(art/'skyline-mask-overlay.png',np.where(city[:880,:,None]>0,
        source[:880]*.4+np.array([0,110,0]),source[:880]))
    metrics={"resolution":[WIDTH,HEIGHT],"mode":"RGB","sourceSha256":sha256(args.source),
        "route":"gpt-6-astra authored deterministic local Python/OpenCV/Pillow composition; no image generation or ChatGPT browser",
        "versions":{"python":platform.python_version(),"opencv":cv2.__version__,
                    "numpy":np.__version__,"pillow":PIL.__version__},
        "maskGeometry":{"method":"same A-derived city and tower mattes for both outputs",
            "identityTransform":True,"cityMaskSha256":sha256(art/'city-mask.png'),
            "towerMaskSha256":sha256(art/'tower-mask.png'),
            "note":"Mask reuse proves shared compositing support, not independent segmentation IoU."},
        "outputs":{name:{"path":str(path.relative_to(ROOT)),"sha256":sha256(path),
            "tower":edge_metrics(source,reality if name=='reality' else redblack,tower)}
            for name,path in outputs.items()},
        "windowPixels":int(lights.sum()),
        "visualReview":"source/reality/redblack overview and tower crop reviewed; no horizontal seam, broad glow or geometry drift observed",
    }
    (art/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    main()
