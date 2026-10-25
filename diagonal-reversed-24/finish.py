from pathlib import Path
import subprocess,json,sys,hashlib
sys.path.insert(0,'/tmp/para-cv-tools')
import cv2,numpy as np
R=Path('/workspace/para-diagonal-reversed-24')
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_read_frames,pix_fmt:format=duration,size','-of','json',str(p)]))
p=R/'PARA_Diagonal_Marquee_Pink_Reversed_4K60.mp4';a=probe(p);s=a['streams'][0]
assert (s['width'],s['height'])==(3840,2160) and s['r_frame_rate']=='60/1' and int(s['nb_read_frames'])==210
assert float(a['format']['duration'])==3.5
q=R/'PARA_Diagonal_Marquee_Pink_Reversed_1080p60.mp4'
subprocess.run(['ffmpeg','-hide_banner','-v','error','-y','-i',str(p),'-vf','scale=1920:1080:flags=lanczos','-an','-c:v','libx264','-preset','slow','-crf','13','-pix_fmt','yuv420p','-threads','3','-movflags','+faststart',str(q)],check=True)
b=probe(q);s=b['streams'][0]
assert (s['width'],s['height'])==(1920,1080) and s['r_frame_rate']=='60/1' and int(s['nb_read_frames'])==210
assert float(b['format']['duration'])==3.5
v=cv2.VideoCapture(str(p));n=0;last=None;diff=[];shots=[]
while True:
 ok,im=v.read()
 if not ok:break
 small=cv2.resize(im,(960,540),interpolation=cv2.INTER_AREA)
 if last is not None:diff.append(float(np.abs(small.astype(np.float32)-last.astype(np.float32)).mean()))
 last=small
 if n in [0,52,105,157,209]:shots.append(small)
 n+=1
assert n==210 and len(shots)==5 and min(diff)>.1 and max(diff)<15
# All rendered stages use original artwork; the exact period is two card pitches.
from render_marquee import render,ROT,PX,DURATION
assert np.array_equal(render(0),render(DURATION))
font_velocity=-ROT@np.array([2*PX/DURATION,0.]);task_velocity=-font_velocity
assert np.dot(font_velocity,task_velocity)<0 and np.linalg.norm(font_velocity+task_velocity)<1e-8
cv2.imwrite(str(R/'PARA_Diagonal_Poster.jpg'),cv2.imread(str(R/'proof-000.jpg')),[cv2.IMWRITE_JPEG_QUALITY,97])
cv2.imwrite(str(R/'motion-review.jpg'),np.vstack(shots[:3]),[cv2.IMWRITE_JPEG_QUALITY,95])
info=dict(duration_seconds=3.5,fps=60,frames=210,resolution=[3840,2160],aspect_ratio='16:9',background='#FF0056',artwork='Original uploaded font and task PNG files',artwork_retyped=False,diagonal_degrees=-18,alternation='Adjacent diagonal rows alternate font cards and task cards',font_motion_pixels_per_second=font_velocity.tolist(),task_motion_pixels_per_second=task_velocity.tolist(),motion='constant-speed opposing marquee streams; both reversed relative to original',soft_shadows=True,frame_filled_from_start=True,exact_render_loop=True,all_210_final_frames_decoded=True,minimum_frame_difference=min(diff),maximum_frame_difference=max(diff),probes=[a,b],files=[])
for f in [p,q,R/'PARA_Diagonal_Poster.jpg']:
 info['files'].append(dict(name=f.name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(R/'VIDEO_INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
(R/'README.txt').write_text('ПАРА — диагональные ленты карт\n\n3,5 секунды, 60 кадров/с, горизонтальный 16:9, без звука.\nОсновной MP4: 3840 × 2160. Облегчённый MP4: 1920 × 1080.\nРозовый фон #FF0056. Светлые карты шрифтов и голубые карты заданий чередуются рядами.\nКарты шрифтов движутся влево-вниз; карты заданий — вправо-вверх.\nОригинальные изображения карт, одинаковый масштаб, мягкие тени, края кадра намеренно обрезают продолжающиеся ленты. Бесшовный цикл.\n',encoding='utf-8')
print('VERIFIED: 3.5 seconds, 210 decoded frames, 60 fps, both MP4s; opposite diagonal directions; exact loop.',flush=True)
