"""Encode the Tokyo v6.17 review preview as a silent 5.8-second MP4."""

import json
import subprocess
import sys
from pathlib import Path


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stderr[-1200:])


def main():
    source = Path(sys.argv[1])
    safe_rect = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)

    rect = safe_rect["rect"]
    scale = float(safe_rect["canvasScale"])
    x = round(rect["x"] * scale)
    y = round(rect["y"] * scale)
    width = round(rect["w"] * scale)
    height = round(rect["h"] * scale)
    width -= width % 2
    height -= height % 2
    video_filter = (
        f"crop={width}:{height}:{x}:{y},"
        "scale=1920:1080:flags=lanczos,setsar=1,"
        "fps=60,trim=duration=5.8,setpts=PTS-STARTPTS,"
        "setparams=range=limited:color_primaries=bt709:"
        "color_trc=bt709:colorspace=bt709,format=yuv420p"
    )
    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(source),
            "-vf", video_filter, "-an", "-c:v", "libx264", "-preset", "slow",
            "-crf", "16", "-pix_fmt", "yuv420p", "-r", "60", "-fps_mode", "cfr",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-movflags", "+faststart",
            "-metadata", "title=iPhone Duo Tokyo v6.17 silent review demo",
            str(output),
        ]
    )
    print(output)


if __name__ == "__main__":
    main()
