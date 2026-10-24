"""ПАРА / первая промо-анимация. Blender 4.x / 5.x, 20 секунд, 30 fps, 1920×1080.

Вставить весь скрипт в Scripting > New > Run Script.
Текстуры автоматически скачиваются с GitHub; повторный запуск использует кэш.
Shift+← — начало; Пробел — просмотр таймлайна, Numpad 0 — камера.
Сначала сохранить .blend (Ctrl+S), затем Ctrl+F12 — рендер видео рядом с проектом.
Исходные сцены пользователя не удаляются: создаётся отдельная новая сцена.
"""
import bpy
import math
import random
import os
import json
import hashlib
import urllib.request
import zipfile
import io
from pathlib import Path
from mathutils import Vector, Matrix, Euler, Quaternion

ASSET_URL = 'https://raw.githubusercontent.com/sofiakovalenskaya/sandbox/refs/heads/para-promo-01/promo-01/para-original-assets-v2.zip'
ASSET_SHA256 = '07012cd8251a9d91beef5413a8a4b6befef59464f9812ef065a369f573f7d09a'
FPS, SECONDS = 30, 20
# Motion is authored at 24 fps and retimed together, including camera and flaps.
AUTHOR_FPS=24
FINAL_FRAME = AUTHOR_FPS * SECONDS
WIDTH, HEIGHT = 1920, 1080
PINK, CREAM, BLUE = '#FF0056', '#FFF0D5', '#BDF9FD'
W, H, D = 1.46, 1.96, .48
CW, CH, CT = 1.38, 1.88, .0060
ROOT_POS = Vector((0,0,1.40))
ROOT_ROTATION = -.27
ROOT_SCALE = 1.08
random.seed(1406)

def locate_assets():
    here = Path(__file__).resolve().parent if '__file__' in globals() else None
    options = [here/'assets' if here else None]
    if bpy.data.filepath:
        options.append(Path(bpy.data.filepath).parent/'assets')
    cache = Path(bpy.app.tempdir or '/tmp')/'para_promo_01_original_assets_v2'
    options.append(cache)
    for candidate in options:
        if candidate and (candidate/'textures/font-back.png').is_file():
            try:
                info=json.loads((candidate/'manifest.json').read_text(encoding='utf-8'))
                if info.get('exact_original_files_supplied') and info.get('asset_revision',0)>=2:
                    return candidate
            except (OSError,ValueError):
                pass
    print('ПАРА: скачиваю текстуры с GitHub…')
    request = urllib.request.Request(ASSET_URL,headers={'User-Agent':'Blender-PARA-Promo'})
    with urllib.request.urlopen(request,timeout=90) as response:
        data=response.read()
    if hashlib.sha256(data).hexdigest()!=ASSET_SHA256:
        raise RuntimeError('ПАРА: контрольная сумма текстур не совпала. Файлы не используются.')
    cache.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            if Path(item.filename).is_absolute() or '..' in Path(item.filename).parts:
                raise RuntimeError('Недопустимый путь в архиве текстур')
        archive.extractall(cache)
    return cache

ASSETS = locate_assets()
TEX = ASSETS/'textures'
manifest=json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
PINK=manifest['palette']['pink'];CREAM=manifest['palette']['cream'];BLUE=manifest['palette']['blue']
SCENE = bpy.data.scenes.new('ПАРА — проморолик 01 / оригиналы')
bpy.context.window.scene=SCENE
SCENE.frame_start,SCENE.frame_end=1,FPS*SECONDS
SCENE.render.fps=FPS
SCENE.render.resolution_x,SCENE.render.resolution_y=WIDTH,HEIGHT
SCENE.render.resolution_percentage=100
SCENE.render.engine='CYCLES'
SCENE.cycles.samples=96
SCENE.cycles.use_adaptive_sampling=True
SCENE.cycles.adaptive_min_samples=16
SCENE.cycles.adaptive_threshold=.012
SCENE.cycles.use_denoising=True
SCENE.cycles.denoising_input_passes='RGB_ALBEDO_NORMAL'
SCENE.cycles.preview_samples=32
SCENE.cycles.max_bounces=1
SCENE.cycles.transparent_max_bounces=64
SCENE.render.use_persistent_data=True
SCENE.render.use_motion_blur=True
SCENE.render.motion_blur_shutter=.08
SCENE.render.filter_size=1.0
SCENE.render.dither_intensity=0
SCENE.view_settings.view_transform='Standard'
SCENE.view_settings.look='None'
SCENE.render.image_settings.color_mode='RGB'
SCENE.render.film_transparent=False
SCENE.render.fps_base=1
# Blender 5 separates images and video. Select video before its file format.
if hasattr(SCENE.render.image_settings, 'media_type'):
    SCENE.render.image_settings.media_type='VIDEO'
SCENE.render.image_settings.file_format='FFMPEG'
SCENE.render.ffmpeg.format='MPEG4'
SCENE.render.ffmpeg.codec='H264'
SCENE.render.ffmpeg.constant_rate_factor='PERC_LOSSLESS'
SCENE.render.ffmpeg.ffmpeg_preset='GOOD'
SCENE.render.filepath='//PARA_Promo_01.mp4'

def collection(name):
    result=bpy.data.collections.new(name)
    SCENE.collection.children.link(result)
    return result
BOX=collection('01 — Коробка')
LIDS=collection('02 — Крышка и клапаны')
CARDS=collection('03 — 60 игровых карт')
DIVIDER=collection('04 — Разделитель')
STUDIO=collection('05 — Камера и фон')

def obj(name,data=None,parent=None,col=BOX):
    result=bpy.data.objects.new(name,data)
    col.objects.link(result)
    if parent: result.parent=parent
    return result

def linear(code):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
                 for v in [int(code[i:i+2],16)/255 for i in (1,3,5)])

IMAGES={}
def image(name):
    if name not in IMAGES:
        IMAGES[name]=bpy.data.images.load(str(TEX/name),check_existing=True)
        IMAGES[name].colorspace_settings.name='sRGB'
    return IMAGES[name]

def graphic_material(name,texture=None,color=CREAM,checker=False):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.diffuse_color=(*linear(color),1)
    n,l=mat.node_tree.nodes,mat.node_tree.links
    n.clear()
    output=n.new('ShaderNodeOutputMaterial')
    surface=n.new('ShaderNodeBsdfPrincipled')
    surface.inputs['Base Color'].default_value=(*linear(color),1)
    surface.inputs['Emission Color'].default_value=(*linear(color),1)
    surface.inputs['Emission Strength'].default_value=.22
    surface.inputs['Roughness'].default_value=.52
    surface.inputs['Specular IOR Level'].default_value=.18
    surface.inputs['Coat Weight'].default_value=.025
    if texture:
        source=n.new('ShaderNodeTexImage')
        source.image=image(texture)
        source.interpolation='Linear'
        source.extension='EXTEND'
        # Back only the unprinted transparent canvas. Opaque artwork is unchanged.
        fallback=BLUE if texture.startswith('task-') else CREAM
        if texture.startswith('box-') and texture!='box-back.png' or texture=='divider.png':
            fallback=PINK
        mix_color=n.new('ShaderNodeMixRGB');mix_color.blend_type='MIX'
        mix_color.inputs[1].default_value=(*linear(fallback),1)
        l.new(source.outputs['Alpha'],mix_color.inputs[0])
        l.new(source.outputs['Color'],mix_color.inputs[2])
        l.new(mix_color.outputs[0],surface.inputs['Base Color'])
        l.new(mix_color.outputs[0],surface.inputs['Emission Color'])
    elif checker:
        source=n.new('ShaderNodeTexChecker')
        coord=n.new('ShaderNodeTexCoord')
        l.new(coord.outputs['Object'],source.inputs['Vector'])
        source.inputs['Color1'].default_value=(*linear(PINK),1)
        source.inputs['Color2'].default_value=(*linear(BLUE),1)
        source.inputs['Scale'].default_value=14.6
        l.new(source.outputs['Color'],surface.inputs['Base Color'])
        l.new(source.outputs['Color'],surface.inputs['Emission Color'])
    l.new(surface.outputs[0],output.inputs['Surface'])
    return mat

PAPER=graphic_material('Торцы — кремовая бумага',color=CREAM)
INNER=graphic_material('Розовая внутренняя сторона коробки',color=PINK)
FRONT=graphic_material('Лицевая сторона коробки','box-front.png')
BACK=graphic_material('Правила на обороте','box-back.png')
SIDE_L=graphic_material('Левая боковина','box-left.png')
SIDE_R=graphic_material('Правая боковина','box-right.png')
CHECKER=graphic_material('Розово-голубая шахматная клетка',checker=True)
TOP_PRINT=graphic_material('Оригинальная печать верхней крышки','box-top.png')
BOTTOM_PRINT=graphic_material('Оригинальная печать дна','box-bottom.png')
TUCK_PRINT=graphic_material('Оригинальная печать язычка','box-top-tuck.png')
DUST_PRINT=graphic_material('Голубые пылевые клапаны',color=BLUE)
FONT_BACK=graphic_material('Рубашка карт шрифтов','font-back.png')
TASK_BACK=graphic_material('Рубашка карт заданий','task-back.png')
INDEX=graphic_material('Паттерн разделителя','divider.png')
FACE_MATS={}
for p in sorted(TEX.glob('*.png')):
    if p.stem.startswith('font-') and p.stem!='font-back' or p.stem.startswith('task-') and p.stem!='task-back':
        FACE_MATS[p.stem]=graphic_material(p.stem,p.name)

def mesh_object(name,verts,faces,mats,indices=None,uv=None,parent=None,col=BOX):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces);data.update()
    for m in mats:data.materials.append(m)
    for face in data.polygons:
        if indices:face.material_index=indices[face.index]
    if uv:
        layer=data.uv_layers.new(name='UVMap')
        for loop in data.loops:
            layer.data[loop.index].uv=uv[loop.vertex_index]
    return obj(name,data,parent,col)

def panel(name,outline,front,inside=INNER,thick=.008,parent=None,col=BOX,back_flip=False):
    n=len(outline)
    verts=[(x,-thick/2,z) for x,z in outline]+[(x,thick/2,z) for x,z in outline]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    xmin,xmax=min(p[0] for p in outline),max(p[0] for p in outline)
    zmin,zmax=min(p[1] for p in outline),max(p[1] for p in outline)
    uv=[((x-xmin)/(xmax-xmin),(z-zmin)/(zmax-zmin)) for x,z in outline]
    uv+= [((1-u if back_flip else u),v) for u,v in uv]
    return mesh_object(name,verts,faces,[front,inside,PAPER],[0,1]+[2]*n,uv,parent,col)

def rect_outline(w,h):
    return [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]

def rounded(w,h,r=.088,segments=12):
    points=[]
    for cx,cz,start in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),
                         (-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
        for j in range(segments+1):
            a=math.radians(start+j*90/segments)
            points.append((cx+r*math.cos(a),cz+r*math.sin(a)))
    return points

ROOT=obj('ПАРА — общее движение коробки')
ROOT.location=ROOT_POS
front_outline=[(-W/2,-H/2),(W/2,-H/2),(W/2,H/2),(.14,H/2)]
front_outline.extend((.14*math.cos(math.pi*i/18),H/2-.09*math.sin(math.pi*i/18)) for i in range(1,19))
front_outline.append((-W/2,H/2))
front=panel('Передняя стенка с выемкой',front_outline,FRONT,parent=ROOT)
front.location.y=-D/2
back=panel('Задняя стенка',rect_outline(W,H),BACK,parent=ROOT)
back.rotation_euler.z=math.pi;back.location.y=D/2
for name,x,rotation,mat in [('Левая стенка',-W/2,-math.pi/2,SIDE_L),('Правая стенка',W/2,math.pi/2,SIDE_R)]:
    side=panel(name,rect_outline(D,H),mat,parent=ROOT)
    side.location.x=x;side.rotation_euler.z=rotation

def horizontal(name,rectangles,parent,mat=TOP_PRINT,reverse=False,uv_bounds=None):
    verts=[];faces=[];uv=[]
    for x0,x1,y0,y1 in rectangles:
        start=len(verts)
        verts.extend([(x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0)])
        faces.append(tuple(start+i for i in ([3,2,1,0] if reverse else [0,1,2,3])))
        xmin,xmax,ymin,ymax=uv_bounds or (-W/2,W/2,-D,0)
        uv.extend([((x-xmin)/(xmax-xmin),(ymax-y)/(ymax-ymin)) for x,y,z in verts[-4:]])
    result=mesh_object(name,verts,faces,[mat,INNER],uv=uv,parent=parent,col=LIDS)
    solid=result.modifiers.new('Толщина картона','SOLIDIFY')
    solid.thickness=.008;solid.offset=-1;solid.material_offset=1;solid.material_offset_rim=1
    return result

bottom=horizontal('Закрытое дно',[(-W/2,W/2,-D/2,D/2)],ROOT,mat=BOTTOM_PRINT,reverse=True,
                  uv_bounds=(-W/2,W/2,-D/2,D/2))
bottom.location.z=-H/2
LID=obj('Крышка — шарнир',parent=ROOT,col=LIDS)
LID.location=(0,D/2,H/2)
sw,sy,sh=.376,-D/2,.020
lid_rects=[(-W/2,-sw/2,-D,0),(sw/2,W/2,-D,0),
           (-sw/2,sw/2,-D,sy-sh/2),(-sw/2,sw/2,sy+sh/2,0)]
horizontal('Крышка с настоящим сквозным пазом',lid_rects,LID)
TUCK=obj('Язычок закрывания — шарнир',parent=LID,col=LIDS)
TUCK.location=(0,-D,0)
horizontal('Язычок закрывания',[(-W/2+.04,W/2-.04,-.24,0)],TUCK,mat=TUCK_PRINT,
           uv_bounds=(-W/2,W/2,-.24,0))
TUCK.rotation_euler.x=math.pi/2
FLAPS=[]
for side,sign in [('Левый',-1),('Правый',1)]:
    hinge=obj(side+' боковой клапан — шарнир',parent=ROOT,col=LIDS)
    hinge.location=(sign*W/2,0,H/2-.01)
    x0,x1=(0,.336) if sign<0 else (-.336,0)
    horizontal(side+' пылевой клапан',[(x0,x1,-D/2+.015,D/2-.015)],hinge,mat=DUST_PRINT)
    FLAPS.append((hinge,sign))

# The divider body is exactly the card size. A narrow tab passes through the lid.
index_bottom=-H/2+.012
index_shoulder=index_bottom+CH
index_top=index_shoulder+manifest['divider_tab_height_mm']*.02
outline=[(-CW/2,index_bottom),(CW/2,index_bottom),(CW/2,index_shoulder),
         (.18,index_shoulder),(.18,index_top),(-.18,index_top),
         (-.18,index_shoulder),(-CW/2,index_shoulder)]
index=panel('Разделитель — оригинальная печать',outline,INDEX,INDEX,parent=ROOT,col=DIVIDER,back_flip=True)
index.shape_key_add(name='Basis')
flex=index.shape_key_add(name='Гибкий хвостик при открывании')
for v in flex.data:
    if v.co.z>index_shoulder+.001:
        v.co.y+=.20
        v.co.z=index_shoulder+.045

def key(o,frame,location=None,rotation=None,scale=None):
    if location is not None:o.location=location;o.keyframe_insert(data_path='location',frame=frame)
    if rotation is not None:
        if o.rotation_mode=='QUATERNION':
            o.rotation_quaternion=rotation if isinstance(rotation,Quaternion) else Euler(rotation,'XYZ').to_quaternion()
            o.keyframe_insert(data_path='rotation_quaternion',frame=frame)
        else:
            o.rotation_euler=rotation;o.keyframe_insert(data_path='rotation_euler',frame=frame)
    if scale is not None:o.scale=(scale,)*3;o.keyframe_insert(data_path='scale',frame=frame)

for f,loc,angle,s in [(1,(-6.5,.0,1.4),-.68,.93),(54,(.13,0,1.4),-.30,1),
                       (66,(0,0,1.4),ROOT_ROTATION,1),(132,(0,0,1.4),2*math.pi+ROOT_ROTATION,ROOT_SCALE),
                       (FINAL_FRAME,(0,0,1.4),2*math.pi+ROOT_ROTATION,ROOT_SCALE)]:
    key(ROOT,f,loc,(0,0,angle),s)
for f,a in [(1,0),(139,0),(151,-.20),(174,-math.radians(108)),(FINAL_FRAME,-math.radians(108))]:
    key(LID,f,rotation=(a,0,0))
for f,a in [(1,math.pi/2),(132,math.pi/2),(149,.05),(FINAL_FRAME,.05)]:
    key(TUCK,f,rotation=(a,0,0))
for flap,sign in FLAPS:
    for f,a in [(1,0),(151,0),(178,sign*math.radians(102)),(FINAL_FRAME,sign*math.radians(102))]:
        key(flap,f,rotation=(0,a,0))
for f,v in [(1,0),(132,0),(144,1),(167,1),(185,0),(FINAL_FRAME,0)]:
    flex.value=v;flex.keyframe_insert(data_path='value',frame=f)

world=bpy.data.worlds.new('Фон — светло-голубой')
world.use_nodes=True
n,l=world.node_tree.nodes,world.node_tree.links;n.clear()
ambient=n.new('ShaderNodeBackground');ambient.inputs['Color'].default_value=(1,1,1,1);ambient.inputs['Strength'].default_value=.45
blue_background=n.new('ShaderNodeBackground');blue_background.inputs['Color'].default_value=(*linear(BLUE),1)
blue_background.inputs['Strength'].default_value=1
path=n.new('ShaderNodeLightPath');mix=n.new('ShaderNodeMixShader');out=n.new('ShaderNodeOutputWorld')
l.new(path.outputs['Is Camera Ray'],mix.inputs[0]);l.new(ambient.outputs[0],mix.inputs[1]);l.new(blue_background.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
SCENE.world=world
for name,location,power,size in [('Большой софтбокс',(-3,-4,7),220,4),('Мягкое заполнение',(4,-2,4),65,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size
    light=obj(name,data,col=STUDIO);light.location=location
    light.rotation_euler=(Vector((0,0,1.7))-light.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Камера 16:9')
CAMERA=obj('Камера 16:9',camera_data,col=STUDIO)
CAMERA.location=(0,-10,4.2)
TARGET=Vector((0,0,1.4))
CAMERA.rotation_euler=(TARGET-CAMERA.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='PERSP'
camera_data.sensor_width=36
camera_data.dof.use_dof=False
SCENE.camera=CAMERA
for f,s in [(1,8.2),(66,8.2),(132,7.2),(146,7.2),(200,9.6),
            (392,9.6),(460,7.7),(476,7.2),(FINAL_FRAME,7.2)]:
    camera_data.lens=36*math.sqrt(10**2+2.8**2)/s;camera_data.keyframe_insert(data_path='lens',frame=f)
for f,lift in [(1,0),(146,0),(200,.60),(392,.60),(460,.15),(476,0),(FINAL_FRAME,0)]:
    key(CAMERA,f,location=(0,-10,4.2+lift))
camera_matrix=CAMERA.rotation_euler.to_matrix()
RIGHT=camera_matrix@Vector((1,0,0))
UP=camera_matrix@Vector((0,1,0))
TOWARD=camera_matrix@Vector((0,0,1))
root_inverse=Matrix.Rotation(-ROOT_ROTATION,3,'Z')
face_base=Matrix.Rotation(-math.atan2(2.8,10),3,'X')
final_plane=face_base@Matrix.Rotation(math.radians(6),3,'X')
PLANE_UP=final_plane@Vector((0,0,1))
PLANE_NORMAL=final_plane@Vector((0,-1,0))
def local_point(world_point):
    return root_inverse@((Vector(world_point)-ROOT_POS)/ROOT_SCALE)

# A soft graphic contact shadow on the seamless blue background.
shadow_mat=bpy.data.materials.new('Мягкая тень под коробкой');shadow_mat.use_nodes=True
n,l=shadow_mat.node_tree.nodes,shadow_mat.node_tree.links;n.clear()
t=n.new('ShaderNodeTexImage');t.image=image('shadow.png')
transparent=n.new('ShaderNodeBsdfTransparent');black=n.new('ShaderNodeEmission')
black.inputs['Color'].default_value=(0,0,0,1)
mix=n.new('ShaderNodeMixShader');output=n.new('ShaderNodeOutputMaterial')
l.new(t.outputs['Alpha'],mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(black.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],output.inputs['Surface'])
shadow=mesh_object('Мягкая тень',[(-1.5,-1.5,0),(1.5,-1.5,0),(1.5,1.5,0),(-1.5,1.5,0)],[(0,1,2,3)],
                   [shadow_mat],uv=[(0,0),(1,0),(1,1),(0,1)],col=STUDIO)
for f,x in [(1,-6.5),(54,.13),(66,0),(FINAL_FRAME,0)]:
    key(shadow,f,location=(x,0,.008))

# Soft transparent edge shadows for blue task cards. The artwork itself stays
# unchanged, and the halo is invisible while the card is still inside the box.
card_shadow_mat=bpy.data.materials.new('Лёгкая тень по краю карты задания')
card_shadow_mat.use_nodes=True
n,l=card_shadow_mat.node_tree.nodes,card_shadow_mat.node_tree.links;n.clear()
shadow_tex=n.new('ShaderNodeTexImage');shadow_tex.image=image('card-soft-shadow.png')
object_info=n.new('ShaderNodeObjectInfo')
alpha=n.new('ShaderNodeMath');alpha.operation='MULTIPLY'
l.new(shadow_tex.outputs['Alpha'],alpha.inputs[0]);l.new(object_info.outputs['Alpha'],alpha.inputs[1])
transparent=n.new('ShaderNodeBsdfTransparent')
tint=n.new('ShaderNodeEmission');tint.inputs['Color'].default_value=(*linear('#233E48'),1)
mix=n.new('ShaderNodeMixShader');out=n.new('ShaderNodeOutputMaterial')
l.new(alpha.outputs[0],mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(tint.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])

AVAILABLE=set(manifest['font_faces_available'])
card_outline=rounded(CW,CH)
launch_order=[n for i in range(30) for n in (i,30+i)]
rank={card_id:i for i,card_id in enumerate(launch_order)}
# Expand from the centre in rings, reaching all four edges and the corners.
def radius_squared(cell):
    col,row=cell
    return ((col-4.5)*(7.30/9))**2+((row-2.5)*(4.26/5))**2
left_cells=sorted([(c,r) for r in range(6) for c in range(5)],
                  key=lambda cell:radius_squared(cell)+random.uniform(0,.05))
right_cells=sorted([(c,r) for r in range(6) for c in range(5,10)],
                   key=lambda cell:radius_squared(cell)+random.uniform(0,.05))
cells={}
for launch_rank,card_id in enumerate(launch_order):
    to_left=launch_rank%4 in (0,3)
    cells[card_id]=(left_cells if to_left else right_cells).pop(0)
odd=list(range(1,31,2));even=list(range(2,31,2))
face_up={
    'font':set(random.sample(odd,8)+random.sample(even,7)),
    'task':set(random.sample(even,7)+random.sample(odd,8)),
}
CARD_ROOTS=[]
for number in range(60):
    is_font=number<30;ident=number+1 if is_font else number-29
    category='Шрифт' if is_font else 'Задание'
    back_mat=FONT_BACK if is_font else TASK_BACK
    face=FACE_MATS.get(f'{"font" if is_font else "task"}-{ident:02}',back_mat)
    card=obj(f'{category} {ident:02} — движение',parent=ROOT,col=CARDS)
    card.rotation_mode='QUATERNION'
    card['card_type']='font' if is_font else 'task'
    card['card_number']=ident
    card['original_front_available']=not is_font or ident in AVAILABLE
    printed_card=panel(category+f' {ident:02}',card_outline,face,back_mat,thick=CT,parent=card,col=CARDS,back_flip=True)
    bevel=printed_card.modifiers.new('Тонкая фаска по краям карты','BEVEL')
    bevel.width=.0008;bevel.segments=2;bevel.limit_method='ANGLE'
    CARD_ROOTS.append(card)
    y=(-.212+(ident-1)*.0064) if is_font else (.025+(ident-1)*.0064)
    initial=Vector((0,y,-H/2+.012+CH/2))
    t0=176+rank[number]*4
    card['launch_frame']=t0
    card['clear_frame']=t0+4
    if not is_font:
        halo_width=CW*985/785;halo_height=CH*1268/1068
        halo=mesh_object(f'Задание {ident:02} — мягкая тень',
             [(-halo_width/2,0,-halo_height/2),(halo_width/2,0,-halo_height/2),
              (halo_width/2,0,halo_height/2),(-halo_width/2,0,halo_height/2)],
             [(0,1,2,3)],[card_shadow_mat],uv=[(0,0),(1,0),(1,1),(0,1)],parent=card,col=CARDS)
        for frame,hidden in [(1,True),(t0+4,True),(t0+5,False),(FINAL_FRAME,False)]:
            halo.hide_render=hidden;halo.keyframe_insert(data_path='hide_render',frame=frame)
            halo.hide_viewport=hidden;halo.keyframe_insert(data_path='hide_viewport',frame=frame)
        for frame,opacity in [(1,0),(t0+4,0),(t0+16,1),(FINAL_FRAME,1)]:
            halo.color=(1,1,1,opacity);halo.keyframe_insert(data_path='color',index=3,frame=frame)
    col,row=cells[number]
    card['fill_radius']=math.sqrt(radius_squared((col,row)))
    xx=-3.65+col*(7.30/9)+random.uniform(-.10,.10)
    yy=-2.13+row*(4.26/5)+random.uniform(-.10,.10)
    front_visible=ident in face_up['font' if is_font else 'task']
    card['final_face_up']=front_visible
    depth=(1.50+rank[number]*.012) if front_visible else (.75+rank[number]*.009)
    endpoint=TARGET+RIGHT*xx+PLANE_UP*yy+PLANE_NORMAL*depth
    end=local_point(endpoint)
    side_sign=-1 if col<5 else 1
    roll=side_sign*math.radians(random.uniform(12,25))
    card['tilt_degrees']=math.degrees(roll)
    card['flight_side']='left' if side_sign<0 else 'right'
    flip=0 if front_visible else math.pi
    pitch=math.radians(random.uniform(-7,7))
    yaw=math.radians(random.uniform(-9,9))
    end_matrix=(root_inverse@final_plane@Matrix.Rotation(roll,3,'Y')@
                Matrix.Rotation(flip,3,'Z'))
    end_quat=end_matrix.to_quaternion()
    initial_rotation=Quaternion((1,0,0,0))
    if initial_rotation.dot(end_quat)<0:end_quat.negate()
    key(card,1,initial,initial_rotation,1)
    key(card,t0,initial,initial_rotation,1)
    exit_position=Vector((0,y,1.98))
    exit_quat=Quaternion((1,0,0,0))
    # One complete lift per launch interval avoids a bundle of rising cards.
    key(card,t0+4,exit_position,exit_quat,1)
    # The entire card clears the opening before it tilts left or right.
    fan=exit_position.lerp(end,.24)+Vector((side_sign*.22,-.16,.10))
    fan_rotation=exit_quat.slerp(end_quat,.38)@Euler((pitch,0,yaw),'XYZ').to_quaternion()
    key(card,t0+18,fan,fan_rotation,1)
    mid=exit_position.lerp(end,.74)+Vector((side_sign*.10,-.08,.06))
    key(card,t0+38,mid,exit_quat.slerp(end_quat,.82),1)
    near=end+Vector((0,0,.035))
    key(card,t0+56,near,exit_quat.slerp(end_quat,.98),1)
    key(card,t0+64,end,end_quat,1)
    drift=local_point(endpoint+RIGHT*random.uniform(-.025,.025)+PLANE_UP*random.uniform(-.025,.025))
    key(card,FINAL_FRAME,drift,end_quat,1)

# Smooth, clamped curves prevent unwanted positional overshoot at the box mouth.
def smooth(owner):
    if not owner.animation_data or not owner.animation_data.action:return
    action=owner.animation_data.action
    if hasattr(action, 'fcurves'):
        curves=action.fcurves
    else:
        # Blender 5 stores curves in the channel bag of the assigned slot.
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        bag=action_get_channelbag_for_slot(action,owner.animation_data.action_slot)
        curves=bag.fcurves if bag else ()
    for curve in curves:
        for point in curve.keyframe_points:
            point.co.x*=FPS/AUTHOR_FPS
            point.handle_left.x*=FPS/AUTHOR_FPS
            point.handle_right.x*=FPS/AUTHOR_FPS
            point.interpolation='CONSTANT' if curve.data_path in ('hide_render','hide_viewport') else 'BEZIER'
            point.handle_left_type=point.handle_right_type='AUTO_CLAMPED'
        curve.update()
for ob in SCENE.objects:smooth(ob)
smooth(camera_data)
smooth(index.data.shape_keys)
for frame,label in [(1,'ВЪЕЗД'),(66,'ПОВОРОТ И ПРИБЛИЖЕНИЕ'),(133,'ОТКРЫТИЕ'),
                    (176,'ПОСЛЕДОВАТЕЛЬНЫЙ ВЫЛЕТ'),(320,'КАРТЫ ЗАПОЛНЯЮТ КАДР'),(476,'ФИНАЛ')]:
    SCENE.timeline_markers.new(label,frame=max(1,round(frame*FPS/AUTHOR_FPS)))
for card in CARD_ROOTS:
    card['launch_frame']=round(card['launch_frame']*FPS/AUTHOR_FPS)
    card['clear_frame']=round(card['clear_frame']*FPS/AUTHOR_FPS)
SCENE['duration_seconds']=SECONDS
SCENE['card_count']=len(CARD_ROOTS)
SCENE['quality_note']='Full HD, 30 fps, 96 samples, denoising with albedo and normal passes; subtle motion blur; no depth-of-field blur.'
SCENE['fill_pattern']='Cards spread from the centre to all four edges and corners, in expanding rings.'
SCENE['texture_note']='Все 60 лиц карт — оригинальные PNG пользователя, скопированные без изменения байтов. Рубашки, логотип, правила и упаковка получены из SVG пользователя с текстом в контурах. Шрифты не заменялись.'
SCENE['box_depth_note']='Глубина 24 мм предварительная, по предыдущему проекту.'
assert len(CARD_ROOTS)==60
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.shading.use_scene_world=True
            area.spaces.active.shading.use_scene_lights=True
            area.spaces.active.overlay.show_overlays=False
SCENE.frame_set(round(132*FPS/AUTHOR_FPS))
bpy.ops.file.pack_all()
if '__file__' in globals() and Path(__file__).is_file():
    code=bpy.data.texts.new('para_animation.py')
    code.from_string(Path(__file__).read_text(encoding='utf-8'))
if os.environ.get('PARA_SAVE_PATH'):
    bpy.ops.wm.save_as_mainfile(filepath=os.environ['PARA_SAVE_PATH'])
print('ПАРА: сцена готова — 60 объёмных карт, 20 секунд, 30 fps. Пробел — просмотр; Ctrl+F12 — видео.')
