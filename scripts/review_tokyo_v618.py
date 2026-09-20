"""Assemble compact visual and mechanical evidence for the silent review."""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/v6.18-tokyo-silent-demo'


def main():
    rect_info = json.loads((ART / 'safe-rect.json').read_text())
    rect, scale = rect_info['rect'], rect_info['canvasScale']
    box = tuple(round(v * scale) for v in (rect['x'], rect['y'], rect['x'] + rect['w'], rect['y'] + rect['h']))
    states = json.loads((ART / 'keyframe-states.json').read_text())
    sheet = Image.new('RGB', (1280, 4 * 395), '#eeeeec')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    for index, (name, state) in enumerate(states.items()):
        img = Image.open(ART / name).convert('RGB').crop(box).resize((640, 360), Image.Resampling.LANCZOS)
        x, y = (index % 2) * 640, (index // 2) * 395
        sheet.paste(img, (x, y))
        frame = state['recordingMode']['frame']
        draw.text((x + 16, y + 365), f'{frame/60:.3f}s / {state["angle"]:.1f} deg - {name[3:-4]}', fill='#333333', font=font)
    sheet.save(ART / 'contact-sheet.png')
    shell_sheet = Image.new('RGB', (1440, 450), '#eeeeec')
    for index, name in enumerate(['12-3d-closed-shell.png', '11-3d-open-shell.png']):
        if (ART / name).exists():
            shell_sheet.paste(Image.open(ART / name).convert('RGB').resize((720, 450), Image.Resampling.LANCZOS), (index * 720, 0))
    shell_sheet.save(ART / 'shell-contact-sheet.png')
    settle = Image.open(ART / '06-open-settled.png').convert('RGB').crop(box)
    pulse_slot = Image.open(ART / '07-future-pulse-slot.png').convert('RGB').crop(box)
    hold_diff = ImageChops.difference(settle, pulse_slot)
    video = ART / 'iphone-duo-tokyo-v6.18-silent-review-demo.mp4'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(video)], text=True))
    (ART / 'ffprobe.json').write_text(json.dumps(probe, indent=2), encoding='utf-8')
    streams = probe['streams']
    video_stream = next(s for s in streams if s['codec_type'] == 'video')
    assert video_stream['width'] == 1920 and video_stream['height'] == 1080
    assert video_stream['avg_frame_rate'] == '60/1'
    assert int(video_stream['nb_read_frames']) == 348
    assert float(probe['format']['duration']) == 5.8
    assert len(streams) == 1
    assert not json.loads((ART / 'console-errors.json').read_text())
    evidence = {
        'resolution': [1920, 1080], 'fps': 60, 'frames': 348, 'durationSeconds': 5.8,
        'audioStreams': 0, 'consoleErrors': 0, 'openSettledFrame': 135,
        'futurePulseFrame': 191, 'fullyOpenHoldBeforeFuturePulseSeconds': (191 - 135) / 60,
        'noFx': True, 'captureClass': 'captureStream review preview, not numbered-frame master',
        'settleToFuturePulseMaxChannelDelta': max(v[1] for v in hold_diff.getextrema()),
        'keyframeIndices': [s['recordingMode']['frame'] for s in states.values()],
    }
    (ART / 'qc-summary.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
