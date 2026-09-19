"""Create the exact 16:9 Tokyo master from the deterministic browser capture."""

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
    audio = Path(sys.argv[2])
    safe_rect = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
    output = Path(sys.argv[4])
    output.parent.mkdir(parents=True, exist_ok=True)

    rect = safe_rect['rect']
    scale = float(safe_rect['canvasScale'])
    x = round(rect['x'] * scale)
    y = round(rect['y'] * scale)
    width = round(rect['w'] * scale)
    height = round(rect['h'] * scale)
    width -= width % 2
    height -= height % 2

    video_filter = (
        f'crop={width}:{height}:{x}:{y},'
        'scale=1920:1080:flags=lanczos,setsar=1,'
        'fps=60,trim=duration=5.5,setpts=PTS-STARTPTS,'
        'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709,'
        'format=yuv420p'
    )
    audio_filter = 'aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration=5.5'
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(source), '-i', str(audio),
        '-vf', video_filter, '-af', audio_filter,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
        '-pix_fmt', 'yuv420p', '-r', '60', '-vsync', 'cfr',
        '-color_range', 'tv', '-colorspace', 'bt709',
        '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
        '-shortest', str(output),
    ])
    print(output)


if __name__ == '__main__':
    main()
