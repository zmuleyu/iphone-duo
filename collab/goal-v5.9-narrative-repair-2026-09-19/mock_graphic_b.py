"""Master B graphic-ization MOCK v3 (deterministic, mock only — not integrated).

Clean rules:
- sky zone (y < skyline): canonical two-stop red gradient (sampled from source),
  except warm-bright pixels (crane lights) kept as amber dots
- city zone: lum<0.30 -> near-black; brightest warm -> amber dot; rest -> black
- tower ellipse: untouched
"""
import os
import statistics

from PIL import Image

SRC = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
OUT = r"C:\Users\Admin\Downloads\duo\mock\RedBlack_Graphic_Mock.png"

img = Image.open(SRC).convert("RGB")
W, H = img.size
px = img.load()

TX, TY = 0.730 * W, 0.430 * H
TRX, TRY = 0.085 * W, 0.300 * H
SKYLINE = int(H * 0.72)

def tower_w(x, y):
    d = (((x - TX) / TRX) ** 2 + ((y - TY) / TRY) ** 2) ** 0.5
    if d >= 1.0:
        return 0.0
    if d <= 0.7:
        return 1.0
    return 1.0 - (d - 0.7) / 0.3

def sky_median(y0, y1):
    rows = []
    for y in range(y0, y1, 6):
        for x in range(0, W, 24):
            r, g, b = px[x, y]
            if r > 100 and (r - b) > 60:
                rows.append((r, g, b))
    if not rows:
        return None
    return tuple(int(statistics.median(c[i] for c in rows)) for i in range(3))

top = sky_median(0, int(H * 0.25)) or (120, 18, 14)
bot = sky_median(int(H * 0.55), SKYLINE) or (200, 40, 26)

def sky_color(y):
    k = min(max(y / SKYLINE, 0.0), 1.0)
    return tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3))

out = Image.new("RGB", (W, H))
op = out.load()
for y in range(H):
    for x in range(W):
        r, g, b = px[x, y]
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        warm = r > 130 and (r - g) > 35 and (r - b) > 70
        tw = tower_w(x, y)
        if tw >= 1.0:
            op[x, y] = (r, g, b)
            continue
        if y < SKYLINE:
            nr, ng, nb = (255, 170, 60) if (warm and lum > 0.62) else sky_color(y)
        else:
            nr, ng, nb = (255, 170, 60) if (warm and lum > 0.62) else (8, 8, 10)
        if tw > 0:
            nr = int(nr * (1 - tw) + r * tw)
            ng = int(ng * (1 - tw) + g * tw)
            nb = int(nb * (1 - tw) + b * tw)
        op[x, y] = (nr, ng, nb)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.save(OUT)
sbs = Image.new("RGB", (W, H * 2 + 16), (255, 255, 255))
sbs.paste(img, (0, 0))
sbs.paste(out, (0, H + 16))
sbs.save(OUT.replace(".png", "_vs_original.png"))
print("mock v3:", OUT, "sky top", top, "bottom", bot)