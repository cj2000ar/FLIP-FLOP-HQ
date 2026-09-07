from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json, subprocess, sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'work/final-tour'
STAGE = ROOT / 'work/video-export'
OUT = ROOT / 'outputs'
STAGE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'work/video-tools'))
import imageio_ffmpeg

frames = json.loads((SOURCE / 'frames.json').read_text(encoding='utf-8'))
known = {f['file'] for f in frames}
for p in sorted(SOURCE.glob('[0-9]*.png')):
    if p.name not in known:
        frames.append(dict(file=p.name, label='08 · Simulación automática — entrada, TP y SL', time=p.stat().st_mtime*1000))
frames.sort(key=lambda f: f['file'])
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 23)
small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 15)
W, H = 1440, 984
concat, chapters = [], []
timeline = 0.0
for i, frame in enumerate(frames):
    with Image.open(SOURCE / frame['file']) as original:
        shot = ImageOps.contain(original.convert('RGB'), (1440, 900), Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', (W,H), '#000000')
    canvas.paste(shot, ((W-shot.width)//2, 84+(900-shot.height)//2))
    draw = ImageDraw.Draw(canvas)
    draw.line((28, 70, 1412, 70), fill='#242424', width=1)
    draw.text((30,14), frame['label'], font=font, fill='#eeeeee')
    draw.text((31,47), 'RECORRIDO DEL WEBSITE Y SU DEMO · CAPTURAS REALES DEL NAVEGADOR', font=small, fill='#8f8f8f')
    p=STAGE/f'{i:05}.png'
    canvas.save(p, compress_level=1)
    if i==0 or frame['label'] != frames[i-1]['label']:
        chapters.append(dict(seconds=round(timeline,2), title=frame['label']))
    duration = 0.2
    if i+1 < len(frames):
        duration = max(0.08, min(1.3, (frames[i+1]['time']-frame['time'])/1000))
        if frames[i+1]['label'] != frame['label']:
            duration=max(duration,1.0)
    else:
        duration=2
    concat.extend([f"file '{p.as_posix()}'",f'duration {duration:.4f}'])
    timeline += duration
concat.append(f"file '{p.as_posix()}'")
(STAGE/'frames.txt').write_text('\n'.join(concat),encoding='utf-8')
(OUT/'FlipFlop-HQ-capitulos.json').write_text(json.dumps(chapters,ensure_ascii=False,indent=2),encoding='utf-8')
video=OUT/'FlipFlop-HQ-recorrido.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(STAGE/'frames.txt'),'-vf','fps=30','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
with Image.open(SOURCE/'00015.png') as poster:
    poster.save(OUT/'FlipFlop-HQ-portada.png')
print(json.dumps(dict(video=str(video),seconds=round(timeline,1),frames=len(frames),chapters=len(chapters),bytes=video.stat().st_size)))
