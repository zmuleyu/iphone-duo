"""Encode the 360 authored v6.23 PNGs without temporal resampling."""
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'artifacts/v6.23-tokyo-silent-video'
VIDEO = ART / 'iphone-duo-tokyo-v6.23-silent-60fps.mp4'
FRAME_COUNT = 360


def main():
    frames = sorted((ART / 'frames').glob('frame_*.png'))
    expected = [f'frame_{i:06d}.png' for i in range(FRAME_COUNT)]
    if [path.name for path in frames] != expected:
        raise ValueError('Expected exactly frame_000000.png through frame_000359.png')
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-framerate', '60', '-start_number', '0',
        '-i', str(ART / 'frames/frame_%06d.png'), '-frames:v', str(FRAME_COUNT), '-an',
        '-vf', 'setsar=1,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-movflags', '+faststart', '-metadata', 'title=iPhone Duo Tokyo v6.23 fixed-step silent master',
        str(VIDEO),
    ], check=True)
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(VIDEO),
    ], text=True))
    (ART / 'ffprobe.json').write_text(json.dumps(probe, indent=2), encoding='utf-8')
    stream = probe['streams'][0]
    assert len(probe['streams']) == 1 and stream['codec_type'] == 'video'
    assert stream['width'] == 1920 and stream['height'] == 1080
    assert stream['avg_frame_rate'] == '60/1' and int(stream['nb_read_frames']) == FRAME_COUNT
    assert abs(float(probe['format']['duration']) - 6.0) < .001
    decoded = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(VIDEO), '-map', '0:v:0', '-f', 'framemd5', '-',
    ], text=True)
    (ART / 'decoded-frame-hashes.txt').write_text(decoded, encoding='utf-8')
    hashes = [line.split(',')[-1].strip() for line in decoded.splitlines() if line and not line.startswith('#')]
    duplicate_motion = [i for i in range(139, 223) if hashes[i] == hashes[i - 1]]
    unexpected_duplicates = [i for i in duplicate_motion if i > 139]
    assert len(hashes) == FRAME_COUNT and not unexpected_duplicates
    qc = {
        'decodedFrames': len(hashes),
        'duplicateMotionFrames': duplicate_motion,
        'unexpectedDuplicateMotionFrames': unexpected_duplicates,
        'fps': 60,
        'duration': 6.0,
        'resolution': [1920, 1080],
        'audioStreams': 0,
    }
    (ART / 'encoded-motion-qc.json').write_text(json.dumps(qc, indent=2), encoding='utf-8')
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(VIDEO), '-vf',
        "select='eq(n,60)+eq(n,138)+eq(n,173)+eq(n,191)+eq(n,211)+eq(n,222)+eq(n,249)+eq(n,268)+eq(n,288)+eq(n,359)',scale=640:360,tile=2x5",
        '-frames:v', '1', str(ART / 'actual-video-contact-sheet.png'),
    ], check=True)
    print(json.dumps({'video': str(VIDEO), **qc}))


if __name__ == '__main__':
    main()
