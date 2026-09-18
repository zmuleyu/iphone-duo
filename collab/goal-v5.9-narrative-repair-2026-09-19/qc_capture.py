"""V5.9 capture QC: objective narrative-timing probe for captured footage.

Checks (16:9 raw webm, no vision needed):
1. frozen-span detection (8x4 redness grid identical across consecutive samples)
2. red onset time >= 0.30s (world follows the fold, not ahead of it)
3. full red by ~1.35s
4. tower column lags sky column at mid-fold (two-beat reveal)
Usage: qc_capture.py <webm>
"""
import subprocess
import sys

def grid(video, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ss", f"{t:.2f}",
                        "-vf", "scale=8:4", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    d = r.stdout
    if len(d) < 96:
        return None
    return [[int(d[(y * 8 + x) * 3] - (d[(y * 8 + x) * 3 + 1] + d[(y * 8 + x) * 3 + 2]) / 2)
             for x in range(8)] for y in range(4)]

def main(video, tower_crop=None):
    frames = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", video],
                            capture_output=True, text=True).stdout.strip()
    print(f"frames: {frames}")
    fails = []
    prev = None
    onset = None
    full = None
    timeline = []
    for i in range(0, 20):
        t = i / 10
        g = grid(video, t)
        if g is None:
            break
        maxr = max(v for row in g for v in row)
        sky = max(g[1][2], g[1][3])       # upper-mid-left = sky
        tower = g[1][4]                    # right-of-center = tower column
        timeline.append((t, maxr, sky, tower))
        if prev == g and 0.4 <= t <= 1.3:  # fold-motion window; closed hold is legitimately static
            fails.append(f"frozen span at t={t:.1f}")
        if onset is None and maxr > 30:
            onset = t
        prev = g
    for t, maxr, sky, tower in timeline:
        print(f"t={t:3.1f} maxRed={maxr:4d} sky={sky:4d} tower={tower:4d}")
    if onset is None:
        fails.append("red never appeared")
    elif onset < 0.30:
        fails.append(f"red onset too early: {onset:.1f}s (<0.30s)")
    # full red check at 1.3-1.4s
    late = [m for t, m, _, _ in timeline if t >= 1.3]
    if late and max(late) < 90:
        fails.append(f"not fully red by 1.3s (maxRed={max(late)})")
    # tower lag: at the sample where sky first >= 60, tower must lag by >= 25
    for t, _, sky, tower in timeline:
        if sky >= 60:
            if tower > sky - 25:
                fails.append(f"tower not lagging at t={t:.1f} (sky={sky} tower={tower})")
            break
    # second beat (raw canvas, tower crop passed as "w:h:x:y"): luminance must
    # rise >=10% across the activation window (1.15s -> 1.75s)
    if tower_crop:
        lum = {}
        for tt in [1.15, 1.75]:
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ss", f"{tt:.2f}",
                                "-vf", f"crop={tower_crop},scale=15:25",
                                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               capture_output=True)
            d = r.stdout
            if len(d) >= 3:
                lums = sorted((0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]
                               for i in range(0, len(d) - 2, 3)), reverse=True)
                lum[tt] = sum(lums[:5]) / 5  # tower lattice core, not crop mean
        if len(lum) == 2:
            rise = (lum[1.75] - lum[1.15]) / max(lum[1.15], 1e-6)
            print(f"tower-core lum: 1.15s={lum[1.15]:.1f} 1.75s={lum[1.75]:.1f} rise={rise:+.1%}")
            if rise < 0.15:
                fails.append(f"tower activation beat too weak (rise {rise:+.1%} < +15%)")
    print("QC:", "PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 0 if not fails else 1

sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
