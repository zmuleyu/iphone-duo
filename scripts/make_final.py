"""make_final.py — iPhone Duo 交付剪辑（webm -> final mp4）

固化 v6.5/v6.6 起的手工 ffmpeg 链：节奏变速 + 裁切/缩放/颗粒/晕影 + 末帧定格 + 可选白片尾板。
用法：
  python scripts/make_final.py <input.webm> <output.mp4> [--card]
默认无片尾板（v6.6 起定格收尾）。--card 追加 0.9s 白底 "iPhone Duo" 石墨字片尾。

节奏曲线（v6.7，增强展开/剧情，时间轴单位=源秒）：
  0.00-0.50  x1.50  闭合 hold + 慢起步压缩
  0.50-1.15  x1.20  世界扫过加速（故事段）
  1.15-1.45  x0.75  展开着陆减速（着陆重音）
  1.45-2.05  x1.00  塔激活节拍原速（可读）
  末帧定格 0.60s
"""
import subprocess
import sys
from pathlib import Path

SEGMENTS = [(0.0, 0.5, 1.5), (0.5, 1.15, 1.2), (1.15, 1.45, 0.75), (1.45, 2.05, 1.0)]
FREEZE_S = 0.6
CROP = "1584:892:108:118"
SCALE = "1920:1080"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed: {r.stderr[-300:]}")
    return r


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    card = "--card" in sys.argv
    cut = out.with_suffix(".cut.tmp.mp4")
    parts, concat = [], ""
    for i, (a, b, spd) in enumerate(SEGMENTS):
        parts.append(f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{spd}[s{i}]")
        concat += f"[s{i}]"
    fc = ";".join(parts) + f";{concat}concat=n={len(SEGMENTS)}:v=1[rt];" + (
        f"[rt]crop={CROP},scale={SCALE},setsar=1,noise=alls=2:allf=t,"
        "vignette=angle=PI/10,format=yuv420p[v]")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-filter_complex", fc,
         "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-an", str(cut)])

    lf = out.with_suffix(".lastframe.png")
    run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.05", "-i", str(cut), "-frames:v", "1", str(lf)])

    tail = "[1:v]format=yuv420p,setsar=1[fr];[0:v][fr]concat=n=2:v=1[v]"
    inputs = ["-i", str(cut), "-loop", "1", "-t", str(FREEZE_S), "-i", str(lf)]
    if card:
        inputs += ["-f", "lavfi", "-i", "color=c=white:s=1920x1080:d=0.9:r=60"]
        tail = ("[2:v]drawtext=fontfile='C\\:/Windows/Fonts/segoeuil.ttf':text='iPhone Duo':"
                "fontcolor=0x3A3D42:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2:"
                "alpha='if(lt(t\\,0.3)\\,t/0.3\\,if(lt(t\\,0.6)\\,1\\,(0.9-t)/0.3))'[card];"
                "[1:v]format=yuv420p,setsar=1[fr];[0:v][fr][card]concat=n=3:v=1[v]")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", tail,
         "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-an", "-movflags", "+faststart", str(out)])
    cut.unlink(missing_ok=True)
    lf.unlink(missing_ok=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"final: {out.name} dur={dur}s card={card}")


main()
