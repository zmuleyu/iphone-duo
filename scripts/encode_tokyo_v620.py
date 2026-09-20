"""Encode exactly 348 already-rendered PNG frames; do not resample time."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'artifacts/v6.20-tokyo-silent-demo'
VIDEO = ART / 'iphone-duo-tokyo-v6.20-silent-review.mp4'


def main():
    frames = sorted((ART / 'frames').glob('frame_*.png'))
    if [p.name for p in frames] != [f'frame_{i:06d}.png' for i in range(348)]:
        raise ValueError('Expected exactly frame_000000.png through frame_000347.png')
    subprocess.run(['ffmpeg','-y','-v','error','-framerate','60','-start_number','0',
        '-i',str(ART/'frames/frame_%06d.png'),'-frames:v','348','-an',
        '-vf','setsar=1,format=yuv420p','-c:v','libx264','-preset','slow','-crf','16',
        '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
        '-movflags','+faststart','-metadata','title=iPhone Duo Tokyo v6.20 fixed-step silent review',str(VIDEO)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(VIDEO)],text=True))
    (ART/'ffprobe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
    video=probe['streams'][0]
    assert len(probe['streams'])==1 and video['codec_type']=='video'
    assert video['width']==1920 and video['height']==1080
    assert video['avg_frame_rate']=='60/1' and int(video['nb_read_frames'])==348
    assert float(probe['format']['duration'])==5.8
    decoded = subprocess.check_output(['ffmpeg','-v','error','-i',str(VIDEO),'-map','0:v:0','-f','framemd5','-'],text=True)
    (ART/'decoded-frame-hashes.txt').write_text(decoded,encoding='utf-8')
    hashes = [line.split(',')[-1].strip() for line in decoded.splitlines() if line and not line.startswith('#')]
    duplicate_motion = [i for i in range(52,139) if hashes[i]==hashes[i-1]]
    assert len(hashes)==348 and not duplicate_motion
    (ART/'encoded-motion-qc.json').write_text(json.dumps({'decodedFrames':len(hashes),'duplicateMotionFrames':duplicate_motion,
        'note':'Identical frames in the intentional closed hold are allowed; no capture or encoding duplicates during unfold.'},indent=2),encoding='utf-8')
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(VIDEO),'-vf',
        "select='eq(n,12)+eq(n,91)+eq(n,143)+eq(n,163)+eq(n,180)+eq(n,196)+eq(n,211)+eq(n,347)',scale=640:360,tile=2x4",
        '-frames:v','1',str(ART/'actual-video-contact-sheet.png')],check=True)
    print(json.dumps({'video':str(VIDEO),'frames':348,'fps':60,'duration':5.8,'audioStreams':0}))


if __name__=='__main__':
    main()
