"""Build editable Blender assembly from the validated, millimetre CAD meshes.
Run with Blender --background --factory-startup --python build_blender.py.
The purchased reference items are separated and marked DO NOT PRINT.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
PREVIEW=ROOT/'previews'; PREVIEW.mkdir(exist_ok=True)
parts=json.loads((ROOT/'parts.json').read_text(encoding='utf-8'))
hardware=json.loads((ROOT/'hardware-reference.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.001
scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES'
scene.cycles.samples=40
scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX'; prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception as e:print(e)
scene.view_settings.view_transform='AgX'
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False

def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
shell=collection('01_PRINTED_PARTS / 已打印件装配位置')
refs=collection('02_PURCHASED_REFERENCE / 金属件示意 禁止打印')
rig=collection('03_FOUR_JOINT_CONTROLS / 四关节控制')
options=collection('04_OPTIONAL_TEMPLATES / 选配模板与试片 隐藏')
studio=collection('05_STUDIO / 摄影棚 非零件')

def mat(name,rgb,metal=0,rough=.35):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*rgb,1)
    n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
    return m
mats={'white':mat('Shell / white polymer',(.81,.86,.88)),
      'teal':mat('Structure / PLEX teal',(.01,.43,.37),.04,.32),
      'dark':mat('Graphite / open bezel',(.024,.044,.058),.03,.38),
      'metal':mat('Purchased metal / NOT PRINTED',(.34,.42,.47),.72,.24)}
floor_mat=mat('Studio ground',(.10,.145,.18),0,.64)

def move(obj,coll):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    coll.objects.link(obj)

objects={}
def import_mesh(p,folder,coll,color):
    bpy.ops.wm.stl_import(filepath=str(ROOT/folder/(p['id']+'.stl')))
    obj=bpy.context.object;obj.name=p['id']+' / '+p['label']
    move(obj,coll);obj.data.materials.append(mats[color])
    obj['part_id']=p['id'];obj['units']='millimetres'
    obj['export_policy']='DO NOT PRINT - PURCHASED REFERENCE' if coll==refs else 'Use supplied stl or 3mf print-oriented files'
    if coll!=refs:
        obj['quantity']=p['quantity'];obj['assembly_notes']=p['notes']
    # Angle-based smoothing changes shading only, never the manufacturing mesh.
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    objects[p['id']]=obj
    return obj

for p in parts:import_mesh(p,'assembly_meshes',shell if p['assembled'] else options,p['color'])
for p in hardware:import_mesh(p,'reference_only_DO_NOT_PRINT',refs,'metal')
options.hide_render=True;options.hide_viewport=True

def empty(name,loc):
    o=bpy.data.objects.new(name,None);rig.objects.link(o);o.location=loc
    o.empty_display_type='ARROWS';o.empty_display_size=12
    return o
controller=empty('CONTROLS / 在自定义属性中输入角度',(0,85,15))
settings=[('J1_yaw_deg',-45,45),('J2_pitch_deg',-15,25),('J3_left_arm_deg',0,60),('J4_right_arm_deg',0,60)]
for name,lo,hi in settings:
    controller[name]=0.0;controller.id_properties_ui(name).update(min=lo,max=hi,soft_min=lo,soft_max=hi,description='Digital sample range only; physical limits must be tested.')
yaw=empty('J1 / yaw',(0,0,110));pitch=empty('J2 / pitch',(0,0,174))
left=empty('J3 / left shoulder',(-51,0,88));right=empty('J4 / right shoulder',(51,0,88))
bpy.context.view_layer.update()
def parent_keep(o,p):
    world=o.matrix_world.copy();o.parent=p;o.matrix_world=world
parent_keep(pitch,yaw)
mapping={'yaw':yaw,'head':pitch,'arm_L':left,'arm_R':right}
for p in parts+hardware:
    if p.get('assembled') and p['group'] in mapping:parent_keep(objects[p['id']],mapping[p['group']])

for o,index,prop,sign in [(yaw,2,'J1_yaw_deg',1),(pitch,0,'J2_pitch_deg',1),(left,1,'J3_left_arm_deg',1),(right,1,'J4_right_arm_deg',-1)]:
    d=o.driver_add('rotation_euler',index).driver
    d.type='SCRIPTED';v=d.variables.new();v.name='angle';v.type='SINGLE_PROP'
    v.targets[0].id=controller;v.targets[0].data_path='["'+prop+'"]'
    d.expression=f'angle * {sign*math.pi/180:.16f}'

scene['README']='Generic manual 4-DOF trial. NO DISPLAY MESH. Motors not selected; no motor-fit claim. Hardware envelopes are references. Print the per-part STL/3MF files, not this entire scene.'
scene['source']='build_mechanical.py / parameterized manifold CSG'
scene['geometry_units']='1 Blender unit = 1 mm; STL coordinates are in mm; 3MF explicitly declares millimeters.'
text=bpy.data.texts.new('START_HERE / 先读说明')
text.write('小 E v0.3 通用装配试样\n\n控制器 CONTROLS 的四个自定义属性可改变姿态。\n这是手动装配验证样机，不是已适配舵机的完整机器人。\n面部窗口是真开孔，无屏幕、无眼睛实体。\n02_PURCHASED_REFERENCE 是金属采购件包络，禁止打印。\n每个打印件的 STL 和 3MF 已单独放平。不要导出整场景打印。\n调整孔径、壁厚等制造参数时优先修改 build_mechanical.py 后重建。\n详细装配顺序、螺钉选用和已知限制见 README.md。\n')
refpath=Path('D:/Unity/Temp/codex-clipboard-154a5ec5-9940-4730-ab95-06d8ca17f1df.png')
if refpath.exists():
    img=bpy.data.images.load(str(refpath));img.name='REFERENCE / Xiao E concept';img.pack()

bpy.ops.mesh.primitive_plane_add(size=20000,location=(0,0,-.15))
floor=bpy.context.object;floor.name='Studio floor / DO NOT PRINT';move(floor,studio);floor.data.materials.append(floor_mat)
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.29,.32,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5;scene.world=world
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,energy,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);studio.objects.link(o);o.location=loc;aim(o,(0,0,125))
light('Key',(-240,-280,390),1900000,230,(1,.94,.87))
light('Fill',(220,-140,260),1500000,200,(.73,.86,1))
light('Rim',(70,220,330),2200000,180,(.68,1,.91))
def camera(name,loc,target,scale):
    data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=scale;data.clip_end=10000
    o=bpy.data.objects.new(name,data);studio.objects.link(o);o.location=loc;aim(o,target);return o
hero=camera('Camera / assembled',(320,-540,290),(0,0,116),285)
front=camera('Camera / front',(0,-550,128),(0,0,120),270)
internal=camera('Camera / open assembly',(285,-550,290),(0,0,119),290)
exploded=camera('Camera / exploded',(420,-680,420),(0,0,195),490)
scene.camera=hero
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.clip_end=10000;a.spaces.active.region_3d.view_distance=360
            a.spaces.active.region_3d.view_location=(0,0,118)
            a.spaces.active.region_3d.view_rotation=hero.rotation_euler.to_quaternion()
            a.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');controller.select_set(True);bpy.context.view_layer.objects.active=controller
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'XiaoE_v03_assembly.blend'))

def render(name,cam,w=1400,h=1500):
    scene.camera=cam;scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=str(PREVIEW/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
render('assembled',hero)
render('front',front,1100,1400)
hidden=['01_base_tray','02_base_lid','05_torso_front','10_head_front','12_open_face_bezel','13_screen_carrier']
for name in hidden:objects[name].hide_render=True
render('mechanism',internal)
for name in hidden:objects[name].hide_render=False

# Capture a real pose using the rig, then return to the neutral manufacturing state.
controller['J1_yaw_deg']=-30;controller['J2_pitch_deg']=15
controller['J3_left_arm_deg']=45;controller['J4_right_arm_deg']=30
controller.update_tag();scene.frame_set(2);bpy.context.view_layer.update()
render('articulated',hero)
for name,_,_ in settings:controller[name]=0.0
controller.update_tag();scene.frame_set(1);bpy.context.view_layer.update()

original={name:o.matrix_world.copy() for name,o in objects.items()}
for p in parts+hardware:
    if not p.get('assembled'):continue
    name=p['id'];o=objects[name]
    if p['group'] in ['head','yaw']:offset=Vector((0,0,125))
    elif p['group'].startswith('arm_'):offset=Vector((-40 if p['group']=='arm_L' else 40,0,60))
    else:offset=Vector((0,0,60))
    if name=='01_base_tray':offset=Vector((0,0,0))
    elif name=='02_base_lid':offset=Vector((0,0,30))
    elif name=='03_electronics_plate':offset=Vector((-115,-35,7))
    elif name=='05_torso_front':offset=Vector((0,-65,60))
    elif name=='06_torso_back':offset=Vector((0,65,60))
    elif name=='18_cape':offset=Vector((0,115,60))
    elif name=='10_head_front':offset=Vector((0,-100,135))
    elif name=='11_head_back':offset=Vector((0,75,135))
    elif name=='12_open_face_bezel':offset=Vector((0,-140,135))
    elif name=='13_screen_carrier':offset=Vector((0,-65,135))
    elif name.startswith('15_') or name.startswith('17_'):offset=Vector((-40 if '_L' in name else 40,0,60))
    o.matrix_world.translation+=offset
bpy.context.view_layer.update()
render('exploded',exploded,1900,1800)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'XiaoE_v03_exploded.blend'))
for name,o in objects.items():o.matrix_world=original[name]
scene.camera=hero;bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'XiaoE_v03_assembly.blend'))
print('BLENDER_COMPLETE',flush=True)
