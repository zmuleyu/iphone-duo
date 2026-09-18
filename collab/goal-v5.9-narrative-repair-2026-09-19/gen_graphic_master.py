"""Graphic master B v2 (V6.1 clean-hero): pure four-layer look.

v1 kept the whole tower ellipse -> dark halo/smoke survived; kept warm dots in sky
-> crane light columns survived. v2:
- sky zone: flat gradient for EVERYTHING above skyline (no warm-dot exemption)
- tower: protect ONLY warm lattice pixels (lum>0.22 & warm) -> halo/smoke crushed
- city: black crush lum<0.35; lights warm & lum>0.70 only (denser cut)
"""
import os
import statistics

from PIL import Image

SRC = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Final_2670x1878.png"
OUT = r"C:\Users\Admin\Downloads\duo\1-1 Tokyo_Tower_RedBlack_Graphic_2670x1878.png"

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
    return tuple(int(statistics.median(c[i] for c in rows)) for i in range(3)) if rows else None

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
        if tw > 0 and warm and lum > 0.30:  # halo band lum<=0.23, lattice p50=0.45
            # tower lattice: keep, normalized to clean amber (blend by tw)
            k = tw
            op[x, y] = (int(255 * k + r * (1 - k)), int(172 * k + g * (1 - k)), int(52 * k + b * (1 - k)))
            continue
        if y < SKYLINE:
            nr, ng, nb = sky_color(y)
        else:
            nr, ng, nb = (255, 170, 60) if (warm and lum > 0.70) else (8, 8, 10)
        op[x, y] = (nr, ng, nb)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.save(OUT)
print("graphic master v2:", OUT, "sky", top, bot)