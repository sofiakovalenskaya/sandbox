from pathlib import Path
import sys,math,subprocess,time,json,hashlib
sys.path.insert(0,'/tmp/para-cv-tools')
import cv2,numpy as np
cv2.setNumThreads(3)
R=Path('/workspace/para-diagonal-reversed-24');O=Path('/workspace/para-promo/originals')
W,H=3840,2160;FPS=60;DURATION=3.5;FRAMES=210
CW,CH=532,724;PX,PY=580.,770.;ANGLE=math.radians(-18)
ROT=np.array([[math.cos(ANGLE),-math.sin(ANGLE)],[math.sin(ANGLE),math.cos(ANGLE)]])
BG=np.array([86,0,255],np.float32)
FONT_IDS=[1,2,5,6,9,14,21,26];TASK_IDS=[3,4,5,9,14,16,10,15]
textures={};manifest=[]

def make_sprite(p):
 a=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
 if a.shape[2]==3:a=np.dstack([a,np.full(a.shape[:2],255,np.uint8)])
 native=a.shape[:2]
 a=cv2.resize(a,(CW,CH),interpolation=cv2.INTER_AREA).astype(np.float32)/255
 alpha=a[:,:,3]
 pad=52;sh=np.zeros((CH+2*pad,CW+2*pad),np.float32)
 sh[pad+10:pad+10+CH,pad+7:pad+7+CW]=alpha
 sh=cv2.GaussianBlur(sh,(0,0),8)*.16
 # A single premultiplied sprite contains the subtle semitransparent shadow.
 rgb=np.array([51,40,45],np.float32)[None,None,:]*sh[:,:,None]
 combined=sh.copy();roi=rgb[pad:pad+CH,pad:pad+CW];oa=combined[pad:pad+CH,pad:pad+CW]
 roi[:]=a[:,:,:3]*255*alpha[:,:,None]+roi*(1-alpha[:,:,None])
 oa[:]=alpha+oa*(1-alpha)
 rgba=np.dstack([rgb,combined*255])
 h,w=rgba.shape[:2]
 corners=np.array([[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]])@ROT.T
 ow,oh=np.ceil(np.ptp(corners,axis=0)+4).astype(int)
 m=np.column_stack([ROT,np.array([ow/2,oh/2])-ROT@np.array([w/2,h/2])]).astype(np.float32)
 sprite=cv2.warpAffine(rgba,m,(int(ow),int(oh)),flags=cv2.INTER_CUBIC)
 # Quantization occurs once after rotation; the output artwork is never retyped.
 sprite=np.clip(np.rint(sprite),0,255).astype(np.uint8)
 manifest.append(dict(source=p.name,native_size=[native[1],native[0]],sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 return sprite
for kind,ids,prefix in [('font',FONT_IDS,'КАРТА ШРИФТ'),('task',TASK_IDS,'ЗАДАНИЕ')]:
 textures[kind]=[make_sprite(O/f'{prefix}-{i}.png') for i in ids]
(R/'texture_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))

def composite(canvas,sprite,cx,cy):
 hh,ww=sprite.shape[:2];left=cx-ww/2;top=cy-hh/2
 xi=int(math.floor(left));yi=int(math.floor(top));xf=left-xi;yf=top-yi
 x0=max(0,xi);y0=max(0,yi);x1=min(W,xi+ww);y1=min(H,yi+hh)
 if x1<=x0 or y1<=y0:return
 # Subpixel placement prevents jitter at 60 fps, including the diagonal axis.
 m=np.array([[1.,0.,xf],[0.,1.,yf]],np.float32)
 shifted=cv2.warpAffine(sprite,m,(ww,hh),flags=cv2.INTER_LINEAR)
 part=shifted[y0-yi:y1-yi,x0-xi:x1-xi].astype(np.float32)
 alpha=part[:,:,3:4]/255
 roi=canvas[y0:y1,x0:x1]
 roi[:]=part[:,:,:3]+roi*(1-alpha)

def render(t):
 canvas=np.empty((H,W,3),np.float32);canvas[:]=BG
 phase=(t/DURATION % 1.)*2*PX
 for row in range(-4,5):
  kind='font' if row%2==0 else 'task';direction=-1 if kind=='font' else 1
  pair=(row//2*2)%len(textures[kind]);stagger=(row%2)*PX/2
  for col in range(-8,9):
   local=np.array([col*PX+stagger+direction*phase,row*PY])
   center=ROT@local+np.array([W/2,H/2])
   sprite=textures[kind][(pair+col%2)%len(textures[kind])]
   if center[0]+sprite.shape[1]/2<0 or center[0]-sprite.shape[1]/2>W or center[1]+sprite.shape[0]/2<0 or center[1]-sprite.shape[0]/2>H:continue
   composite(canvas,sprite,float(center[0]),float(center[1]))
 return np.clip(np.rint(canvas),0,255).astype(np.uint8)

if __name__=='__main__':
 if '--proof' in sys.argv:
  for f in [0,52,105,157,209]:
   im=render(f/FPS);cv2.imwrite(str(R/f'proof-{f:03}.jpg'),im,[cv2.IMWRITE_JPEG_QUALITY,97])
  assert np.array_equal(render(0),render(DURATION))
  print('Proof frames ready; exact loop verified.',flush=True)
 else:
  p=R/'PARA_Diagonal_Marquee_Pink_Reversed_4K60.mp4'
  cmd=['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','rawvideo','-pixel_format','bgr24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-vf','scale=out_color_matrix=bt709','-c:v','libx264','-preset','slow','-crf','12','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-threads','4','-movflags','+faststart',str(p)]
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);start=time.monotonic()
  try:
   for f in range(FRAMES):
    proc.stdin.write(render(f/FPS).tobytes())
    if f%30==0:print('FRAME',f,'/',FRAMES,'elapsed',round(time.monotonic()-start,1),flush=True)
  finally:proc.stdin.close()
  assert proc.wait()==0
  print('MP4 READY',round(time.monotonic()-start,1),flush=True)
