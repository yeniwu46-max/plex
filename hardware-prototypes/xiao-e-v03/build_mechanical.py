"""Parametric generic assembly trial for Xiao E. Dimensions are millimetres.

Requires manifold3d, trimesh, numpy. Does NOT generate machine G-code.
The four joints are manually articulated using purchased shafts and bearings;
motor-specific mounts and display-specific geometry require hardware selection.
"""
from pathlib import Path
import sys, json, math, zipfile, csv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'_cad_deps'))
import numpy as np
import manifold3d as md
import trimesh

STL = ROOT/'stl'
ASM = ROOT/'assembly_meshes'
THREE = ROOT/'3mf'
for folder in (STL, ASM, THREE): folder.mkdir(exist_ok=True)
M=md.Manifold
P={'shell_wall':3.0,'bearing_bore':16.20,'shaft_clearance':5.20,
   'm3_clearance':3.40,'m3_nut_af':5.80,'shell_seam_gap':0.40,
   'pitch_axis_z':174.0,'head_center_z':178.0,
   'status':'GENERIC MANUAL ASSEMBLY TRIAL / NOT MOTOR-READY / MACHINE PROFILE UNKNOWN'}
PARTS=[]

def box(size,c=(0,0,0)):
    return M.cube(tuple(size),True).translate(tuple(c))

def cyl(d,h,c=(0,0,0),axis='Z',segments=64):
    q=M.cylinder(h,d/2,circular_segments=segments,center=True)
    if axis=='X':q=q.rotate((0,90,0))
    elif axis=='Y':q=q.rotate((90,0,0))
    return q.translate(tuple(c))

def union(*args):
    return M.batch_boolean(list(args),md.OpType.Add)

def cut(base,*args):
    return M.batch_boolean([base,*args],md.OpType.Subtract)

def rrect(w,h,d,r,c=(0,0,0),axis='Z'):
    s=md.CrossSection.square((w-2*r,h-2*r),True).offset(r,circular_segments=48)
    q=s.extrude(d).translate((0,0,-d/2))
    if axis=='Y':q=q.rotate((90,0,0))
    elif axis=='X':q=q.rotate((0,90,0))
    return q.translate(tuple(c))

def rbox(size,r,c=(0,0,0)):
    q=M.cube(tuple(float(v)-2*r for v in size),True).minkowski_sum(M.sphere(r,48))
    return q.translate(tuple(c))

def hole(c,length=100,axis='Z',d=None):
    return cyl(P['m3_clearance'] if d is None else d,length,c,axis)

def nut(c,length=3.1,axis='Z',af=None):
    d=(af or P['m3_nut_af'])/math.cos(math.pi/6)
    return cyl(d,length,c,axis,6)

def slot(a,b,d=3.4,depth=30,axis='Z'):
    return union(cyl(d,depth,a,axis),cyl(d,depth,b,axis)).hull()

def ring(od,id,h,c=(0,0,0),axis='Z'):
    return cut(cyl(od,h,c,axis),cyl(id,h+2,c,axis))

def clip_y(q,front):
    return q ^ box((500,300,500),(0,-150-.2 if front else 150+.2,150))

def add(name,q,cn,group='fixed',orient=(0,0,0),qty=1,notes='',color='white',assembled=True):
    if q.is_empty():raise RuntimeError('EMPTY '+name)
    comps=q.decompose()
    if len(comps)!=1:
        raise RuntimeError(f'{name}: {len(comps)} disconnected solids; volumes {[c.volume() for c in comps]}')
    if str(q.status()).split('.')[-1]!='NoError':raise RuntimeError(f'{name}: {q.status()}')
    PARTS.append(dict(id=name,shape=q,label=cn,group=group,orientation=orient,quantity=qty,
                      notes=notes,color=color,assembled=assembled))
    print('PART',name,round(q.volume(),1),flush=True)
    return q

# ---------- Base electronics enclosure ----------
tray=cut(cyl(124,26,(0,0,13)),cyl(118,30,(0,0,18)))
base_fasteners=[]
for deg in [45,135,225,315]:
    x,y=52*math.cos(math.radians(deg)),52*math.sin(math.radians(deg))
    base_fasteners.append((x,y))
    tray=union(tray,cyl(12,23.2,(x,y,14.4)))
    tray=cut(tray,hole((x,y,18),24),nut((x,y,24.4),3.4))
for x in [-35,35]:
    for y in [-20,20]:
        tray=union(tray,cyl(9,3.2,(x,y,4.4)))
        tray=cut(tray,hole((x,y,4.5),9),nut((x,y,1.6),3.3))
tray=cut(tray,rrect(14,9,20,2,(0,-59,13),axis='Y'))
add('01_base_tray',tray,'底座电子仓',notes='底面向下；通用电源开口 14×9，后续需匹配接头。',color='dark')

locator=ring(117.0,110,1.8,(0,0,25.1))
for x,y in base_fasteners:locator=cut(locator,cyl(13,5,(x,y,25)))
lid=union(cyl(124,4,(0,0,28)),locator)
lid=cut(lid,rrect(28,18,20,3,(0,0,28)))
for x,y in base_fasteners:lid=cut(lid,hole((x,y,28),15),cyl(6.4,2,(x,y,29.2)))
for xc in [-19,19]:
    for dx in [-10,10]:
        for y in [-10,10]:lid=cut(lid,hole((xc+dx,y,28),15))
add('02_base_lid',lid,'底座上盖',notes='定位圈径向间隙约 0.5 mm；四角 M3 固定。',color='dark')

insert=rrect(90,54,2.6,5,(0,0,7.3))
for x in [-35,35]:
    for y in [-20,20]:insert=cut(insert,hole((x,y,7),10))
for x in [-27,-9,9,27]:
    for y in [-11,7]:insert=cut(insert,slot((x-5,y,7),(x+5,y,7),3.4,10))
add('03_electronics_plate',insert,'通用电子安装板',notes='扎带 / M3 长孔固定；需按选定电路板增补绝缘支座。',color='teal')

# Fixed hollow legs. Continuous bolts sandwich lid, legs and chassis.
for label,sign in [('L',-1),('R',1)]:
    x=sign*19
    leg=union(rrect(22,22,26,4,(x,0,43)),rrect(30,30,4,5,(x,0,32)),rrect(30,30,4,5,(x,0,54)))
    leg=cut(leg,rrect(14,14,32,3,(x,0,43)))
    for dx in [-10,10]:
        for y in [-10,10]:leg=cut(leg,hole((x+dx,y,43),40))
    add('04_leg_'+label,leg,'固定空心腿 '+label,notes='M3 贯穿螺栓；中孔可走线；本版不作为运动关节。')

# ---------- Body shell and load-bearing chassis ----------
body_outer=rbox((78,62,66),12,(0,0,83))
body_inner=rbox((72,56,60),9,(0,0,83))
body=cut(body_outer,body_inner,cyl(49,45,(0,0,116)),
         box((70.6,38.6,6),(0,0,58.5)),box((66.6,30.6,6),(0,0,107.5)))
for x in [-19,19]:body=cut(body,rrect(31,31,20,5,(x,0,53)))
for sign in [-1,1]:body=cut(body,box((30,39,46),(sign*39,0,87)))
body_join=[(x,z) for x in [-28,28] for z in [70,107.5]]
for x,z in body_join:
    body=union(body,cyl(10,17.7,(x,-19.15,z),'Y'),cyl(10,17.7,(x,19.15,z),'Y'))
    body=body ^ body_outer
    body=cut(body,hole((x,0,z),100,'Y'),nut((x,-20.5,z),3.2,'Y'),cyl(6.4,28,(x,34,z),'Y'))
for x in [-12,12]:
    body=union(body,cyl(10,10,(x,26,99),'Y'))
    body=cut(body,hole((x,28,99),30,'Y'),nut((x,23,99),3.2,'Y'))
for x in [-16,0,16]:body=cut(body,box((7,20,2.8),(x,31,79)))
body=cut(body,box((70.6,38.6,6),(0,0,58.5)),box((66.6,30.6,6),(0,0,107.5)))
for x in [-29,29]:
    for y in [-10,10]:body=cut(body,cyl(4,6,(x,y,64)))
front=clip_y(body,True)
back=clip_y(body,False)
add('05_torso_front',front,'躯干前壳',orient=(90,0,0),notes='开口面放置；根据切片预览添加可拆支撑。')
add('06_torso_back',back,'躯干后壳',orient=(-90,0,0),notes='后方披风螺母从内侧装入后合壳。')

chassis=union(box((70,38,5),(0,0,58.5)),box((66,30,5),(0,0,107.5)),
              box((10,20,50),(-28,0,84)),box((10,20,50),(28,0,84)),
              cyl(27,16,(0,0,102)))
chassis=cut(chassis,hole((0,0,101),35,d=11),cyl(P['bearing_bore'],5.25,(0,0,96.6)),cyl(P['bearing_bore'],5.25,(0,0,107.4)))
chassis=cut(chassis,rrect(24,16,20,3,(0,0,58)))
for xc in [-19,19]:
    for dx in [-10,10]:
        for y in [-10,10]:
            chassis=cut(chassis,hole((xc+dx,y,60),18))
            if abs(xc+dx)>20:
                chassis=cut(chassis,box((7,7,3.5),(xc+dx,y,63)))
for x,z in body_join:chassis=cut(chassis,hole((x,0,z),35,'Y'))
for sign in [-1,1]:
    for z in [74,102]:
        chassis=cut(chassis,hole((sign*28,0,z),30,'X'),nut((sign*24.5,0,z),3.2,'X'))
add('07_load_chassis',chassis,'承重骨架与转头轴承座',notes='625 轴承位 16.20；上下轴承组合；打印配合试片后再决定孔径。',color='teal')

# ---------- Two-axis neck ----------
fork=union(box((96,24,6),(0,0,123.8)),
           box((6,24,69.2),(-45,0,160.4)),box((6,24,69.2),(45,0,160.4)),
           cyl(23,10,(0,0,115.8)))
fork=cut(fork,hole((0,0,117),30,d=P['shaft_clearance']),box((.8,14,10.5),(0,7,115.7)),
         hole((0,7,115.8),32,'X'),nut((8.3,7,115.8),3.4,'X'))
# Yaw motor adapter has a replaceable four-hole interface beneath the platform.
for x in [-15,15]:
    for y in [-7,7]:fork=cut(fork,hole((x,y,124),16))
for sign in [-1,1]:
    fork=cut(fork,hole((sign*45,0,174),15,'X',11),cyl(P['bearing_bore'],5.25,(sign*45.45,0,174),'X'))
    for z in [160,188]:fork=cut(fork,hole((sign*45,0,z),16,'X'),nut((sign*43.6,0,z),3.3,'X'))
add('08_yaw_fork',fork,'转头平台与点头 U 架',group='yaw',orient=(90,0,0),notes='5 mm 钢轴夹紧；U 架两侧装 625 轴承；姿态范围仍须台架验证。',color='teal')

cradle=union(box((76,26,6),(0,0,205)),box((8,20,33),(-33,0,189.5)),box((8,20,33),(33,0,189.5)),
             cyl(21,8,(-33,0,174),'X'),cyl(21,8,(33,0,174),'X'))
for sign in [-1,1]:
    cradle=cut(cradle,hole((sign*33,0,174),18,'X',P['shaft_clearance']),
               box((9,.8,11),(sign*33,0,179.5)),hole((sign*33,0,181),30,'Y'),nut((sign*33,7.2,181),3.4,'Y'))
for x in [-32,32]:
    for y in [-8,8]:cradle=cut(cradle,hole((x,y,205),18))
add('09_head_cradle',cradle,'头部承重托架',group='head',orient=(180,0,0),notes='倒置平放；5 mm 横轴与夹紧螺栓；显示屏不承受头部重量。',color='teal')

# ---------- Hollow head with a genuine screen opening ----------
head_outer=rbox((114,88,94),20,(0,0,178))
head_inner=rbox((108,82,88),17,(0,0,178))
head=cut(head_outer,head_inner)
face_rim=cut(rrect(104,82,5,14,(0,-41.5,178),'Y'),rrect(82,60,16,8,(0,-41.5,178),'Y'))
head=union(head,face_rim)
head=cut(head,rrect(82,60,45,8,(0,-43,178),'Y'),box((104,72,60),(0,0,113)))
# The ears are hollow cosmetic rings integral with the shell; they are NOT shafts.
for sign in [-1,1]:
    ear=ring(28,18,7,(sign*56.5,0,174),'X')
    head=union(head,ear)
    head=cut(head,cyl(18,17,(sign*56.5,0,174),'X'))
# Front panel supports and through fasteners.
screen_points=[(x,z) for x in [-44,44] for z in [150,206]]
for x,z in screen_points:
    boss=cyl(11,9,(x,-39.5,z),'Y')
    head=union(head,boss)
    head=cut(head,hole((x,-37,z),40,'Y'))
head_join=[(x,216.5) for x in [-44,-14,14,44]]
for x,z in head_join:
    head=union(head,cyl(16,12,(x,-6.2,z),'Y'),cyl(16,12,(x,6.2,z),'Y'))
    head=cut(head,hole((x,0,z),100,'Y'),nut((x,-9.4,z),3.3,'Y'),cyl(6.4,50,(x,30,z),'Y'))
# Cradle mounts descend from the roof. Nuts enter from below, before assembly.
for x in [-32,32]:
    for y in [-8,8]:
        head=union(head,cyl(11,17,(x,y,216.5)))
        head=cut(head,hole((x,y,214),24),nut((x,y,209.5),3.3))
# Vent slots in the removable back shell.
for x in [-18,0,18]:head=cut(head,rrect(10,3,26,1,(x,40,193),'Y'))
# The swept crest remains simple and thick, printed with the back shell.
crest=union(M.sphere(5,32).scale((.75,1.7,1.5)).translate((0,10,227)),
            M.sphere(4,32).scale((.8,1.8,1)).translate((0,16,227)))
head=union(head,crest)
add('10_head_front',clip_y(head,True),'空心头壳前半',group='head',orient=(90,0,0),notes='无实心面罩、无眼睛；后续以窗口和内部空间校核实际屏幕。')
add('11_head_back',clip_y(head,False),'空心头壳后半',group='head',orient=(-90,0,0),notes='螺钉维护后盖；有通风孔；装入 M3 螺母后合壳。')

bezel=cut(rrect(101,79,4,13,(0,-46,178),'Y'),rrect(62,47,20,3,(0,-46,178),'Y'))
carrier=cut(rrect(100,78,4,10,(0,-32,178),'Y'),rrect(62,47,15,3,(0,-32,178),'Y'))
for x,z in screen_points:
    bezel=cut(bezel,hole((x,-46,z),15,'Y'),cyl(6.4,2,(x,-47.2,z),'Y'))
    carrier=cut(carrier,hole((x,-32,z),15,'Y'))
add('12_open_face_bezel',bezel,'开窗面框',group='head',orient=(-90,0,0),notes='窗口 62×47；这是通用试样窗口，不保证适配未选定的屏幕。',color='dark')
add('13_screen_carrier',carrier,'独立屏幕承托框',group='head',orient=(-90,0,0),notes='由 M3 螺杆、螺母及软垫调节深度；真实显示模块不可导出打印。',color='teal')

# Bearing retainers for pitch, bolted to the U-fork outer faces.
for sign,label in [(-1,'L'),(1,'R')]:
    q=box((2,22,38),(sign*49,0,174))
    q=cut(q,hole((sign*49,0,174),10,'X',11))
    for z in [160,188]:q=cut(q,hole((sign*49,0,z),10,'X'))
    add('14_pitch_retainer_'+label,q,'点头轴承压盖 '+label,group='yaw',orient=(0,90,0),color='dark')

# ---------- Independent shoulder joints ----------
for sign,label in [(-1,'L'),(1,'R')]:
    x=sign*51
    shoulder=union(box((7,24,40),(sign*36.5,0,88)),
                   box((25,6,40),(sign*51.5,-11,88)),box((25,6,40),(sign*51.5,11,88)))
    # Trim the central tie out of the arm's sweep envelope.
    for z in [74,102]:shoulder=cut(shoulder,hole((sign*36.5,0,z),30,'X'),cyl(6.4,4,(sign*39,0,z),'X'))
    shoulder=cut(shoulder,hole((x,0,88),45,'Y',11),
                 cyl(P['bearing_bore'],5.3,(x,-11.4,88),'Y'),cyl(P['bearing_bore'],5.3,(x,11.4,88),'Y'))
    for y in [-11,11]:
        for z in [74,102]:
            shoulder=cut(shoulder,hole((x,y,z),15,'Y'),nut((x,math.copysign(9.5,y),z),3.3,'Y'))
    add('15_shoulder_fork_'+label,shoulder,'肩部固定叉架 '+label,notes='两侧 625 轴承承托 5 mm 肩轴；接口留给后续电机转接。',color='teal')

    # Arm is a hollow open-ended shell joined to a strong split-clamp shoulder hub.
    arm=union(rrect(18,14,43,5,(x,0,65.5)),cyl(19,14,(x,0,88),'Y'))
    arm=cut(arm,rrect(12,8,42,2,(x,0,62)),hole((x,0,88),30,'Y',P['shaft_clearance']),
            box((.8,16,10),(x,0,93)),hole((x,0,94),28,'X'),nut((x+6.8,0,94),3.3,'X'))
    add('16_arm_'+label,arm,'空心活动臂 '+label,group='arm_'+label,notes='5 mm 钢轴夹紧；本版肘腕固定；使用动作范围试验，不安装未知舵机。')
    for ys,suffix in [(-1,'front'),(1,'back')]:
        q=box((22,2,38),(x,ys*15,88))
        q=cut(q,hole((x,ys*15,88),10,'Y',11))
        for z in [74,102]:q=cut(q,hole((x,ys*15,z),10,'Y'))
        add('17_shoulder_retainer_'+label+'_'+suffix,q,'肩部轴承压盖 '+label+' '+suffix,orient=(90,0,0),color='dark')

# ---------- Back cape with explicit joint clearance ----------
profile=md.CrossSection([np.array([[-48,55], [48,55], [20,104], [-20,104]],float)])
cape=profile.extrude(3).rotate((90,0,0)).translate((0,42,0))
# Cross-section Y becomes world Z, extrusion Z becomes -Y; cape spans Y 39..42.
for x in [-12,12]:
    cape=union(cape,ring(10,3.4,8,(x,35,99),'Y'))
    cape=cut(cape,hole((x,39,99),24,'Y'))
add('18_cape',cape,'可拆披风',orient=(-90,0,0),notes='后置结构，避开肩臂活动区；两颗 M3 螺钉和支座固定。')

# Replaceable motor mount templates are intentionally NOT assembled or claimed to fit a servo.
adapter=rrect(48,46,4,4)
adapter=cut(adapter,cyl(14,12),slot((-14,-14,0),(14,-14,0),3.4,12),slot((-14,14,0),(14,14,0),3.4,12))
for x in [-15,15]:
    for y in [-7,7]:adapter=cut(adapter,hole((x,y,0),12))
add('19_motor_adapter_template',adapter,'电机转接空白模板',assembled=False,qty=4,
    notes='仅为转接模板，不是已适配的舵机支架；器件冻结后再加工。',color='teal')

for length in [3,6,9]:
    add('20_screen_spacer_'+str(length)+'mm',ring(8,3.4,length,(0,0,length/2)),
        '屏幕调距垫柱 '+str(length)+' mm',assembled=False,qty=4,notes='试装用；按真实模块厚度选配，不压玻璃。',color='teal')

# Calibration coupon: no dimension is presented as printer-independent guaranteed fit.
coupon=rrect(106,40,6,3,(0,0,3))
for i,d in enumerate([16.0,16.1,16.2,16.3,16.4]):
    x=-42+i*21
    coupon=cut(coupon,cyl(d,10,(x,0,3)))
    for n in range(i+1):coupon=cut(coupon,box((1,3,1),(x-4+n*2,15,5.7)))
add('21_bearing_fit_coupon',coupon,'轴承配合测试片',assembled=False,notes='从左到右 16.0 / 16.1 / 16.2 / 16.3 / 16.4 mm；刻痕 1–5 对应。')
shaftcoupon=rrect(72,30,6,3,(0,0,3))
for i,d in enumerate([5.0,5.1,5.2,5.3,5.4]):
    shaftcoupon=cut(shaftcoupon,cyl(d,10,(-28+i*14,0,3)))
    for n in range(i+1):shaftcoupon=cut(shaftcoupon,box((.8,3,1),(-31+i*14+n*1.5,10,5.7)))
add('22_shaft_fit_coupon',shaftcoupon,'钢轴配合测试片',assembled=False,notes='刻痕 1–5 对应 5.0 / 5.1 / 5.2 / 5.3 / 5.4 mm。')

def tri(q):
    m=q.to_mesh()
    return trimesh.Trimesh(vertices=np.array(m.vert_properties[:,:3],float),faces=np.array(m.tri_verts),process=True)

# Purchased hardware envelopes live in a separate directory, never in print folders.
REF=ROOT/'reference_only_DO_NOT_PRINT'
REF.mkdir(exist_ok=True)
HARDWARE=[]
def hardware(name,q,group,label):
    HARDWARE.append(dict(id=name,shape=q,group=group,label=label,assembled=True))
    tri(q).export(REF/(name+'.stl'))

for z in [96.6,107.4]:hardware('625_yaw_'+str(z),ring(16,5,5,(0,0,z)),'fixed','625 轴承 / 购买件')
hardware('yaw_shaft_5x38',cyl(5,38,(0,0,106)),'yaw','5×38 钢轴 / 下料参考')
hardware('yaw_collar',ring(10,5,5,(0,0,91.5)),'yaw','5 mm 内径轴环 / 示意包络')
hardware('yaw_thrust_shim',ring(8,5,.9,(0,0,110.35)),'yaw','轴承内圈垫片 / 厚度待实配')
hardware('pitch_shaft_5x116',cyl(5,116,(0,0,174),'X'),'head','5×116 钢轴 / 下料参考')
for sign,label in [(-1,'L'),(1,'R')]:
    hardware('625_pitch_'+label,ring(16,5,5,(sign*45.45,0,174),'X'),'yaw','625 轴承 / 购买件')
    hardware('pitch_collar_'+label,ring(10,5,5,(sign*53,0,174),'X'),'head','5 mm 内径轴环 / 示意包络')
    for z in [160,188]:
        bolt=union(cyl(3,8,(sign*46,0,z),'X'),cyl(5.5,2,(sign*51,0,z),'X'))
        hardware('pitch_M3x8_'+label+'_'+str(z),bolt,'yaw','M3×8 低头螺钉 / 外形示意')
    x=sign*51
    hardware('shoulder_shaft_5x44_'+label,cyl(5,44,(x,0,88),'Y'),'arm_'+label,'5×44 钢轴 / 下料参考')
    for ys,suffix in [(-1,'front'),(1,'back')]:
        hardware('625_shoulder_'+label+'_'+suffix,ring(16,5,5,(x,ys*11.4,88),'Y'),'fixed','625 轴承 / 购买件')
        hardware('shoulder_collar_'+label+'_'+suffix,ring(10,5,5,(x,ys*19,88),'Y'),'arm_'+label,'5 mm 内径轴环 / 示意包络')
        for z in [74,102]:
            bolt=union(cyl(3,8,(x,ys*12,z),'Y'),cyl(5.5,2,(x,ys*17,z),'Y'))
            hardware('shoulder_M3x8_'+label+'_'+suffix+'_'+str(z),bolt,'fixed','M3×8 低头螺钉 / 外形示意')

def real_nut(c,axis):return cut(nut(c,2.4,axis,5.5),hole(c,5,axis,3.2))
for x,z in screen_points:
    name=f'{x}_{z}'
    bolt=union(cyl(3,20,(x,-36.2,z),'Y'),cyl(5.5,1.8,(x,-47.1,z),'Y'))
    hardware('screen_M3x20_'+name,bolt,'head','M3×20 低头面框螺钉 / 示意')
    hardware('screen_nut_'+name,real_nut((x,-28.8,z),'Y'),'head','M3 屏幕托架螺母 / 示意')
for x,z in body_join:
    name=f'{x}_{z}'
    bolt=union(cyl(3,45,(x,-2.5,z),'Y'),cyl(5.5,3,(x,21.5,z),'Y'))
    hardware('body_M3x45_'+name,bolt,'fixed','M3×45 躯干贯穿螺钉 / 示意')
    hardware('body_nut_'+name,real_nut((x,-20.5,z),'Y'),'fixed','M3 躯干螺母 / 示意')
for sign,label in [(-1,'L'),(1,'R')]:
    for z in [74,102]:
        bolt=union(cyl(3,14,(sign*30,0,z),'X'),cyl(5.5,3,(sign*38.5,0,z),'X'))
        hardware('shoulder_mount_M3x14_'+label+'_'+str(z),bolt,'fixed','M3×14 肩叉固定螺钉 / 示意')
        hardware('shoulder_mount_nut_'+label+'_'+str(z),real_nut((sign*24.5,0,z),'X'),'fixed','M3 肩叉螺母 / 示意')
for xc in [-19,19]:
    for dx in [-10,10]:
        for y in [-10,10]:
            x=xc+dx;name=f'{x}_{y}'
            bolt=union(cyl(3,40,(x,y,46)),cyl(5.5,3,(x,y,24.5)))
            hardware('leg_M3x40_'+name,bolt,'fixed','M3×40 腿部贯穿螺钉 / 示意')
            hardware('leg_nut_'+name,real_nut((x,y,63 if abs(x)>20 else 62.2),'Z'),'fixed','M3 腿部螺母 / 示意')
(ROOT/'hardware-reference.json').write_text(json.dumps([{k:v for k,v in p.items() if k!='shape'} for p in HARDWARE],ensure_ascii=False,indent=2),encoding='utf-8')

def write3mf(mesh,path,name):
    # Core 3MF geometry only: no vendor-specific printer, material or slicing profile.
    from xml.sax.saxutils import escape
    verts=''.join(f'<vertex x="{p[0]:.6f}" y="{p[1]:.6f}" z="{p[2]:.6f}"/>' for p in mesh.vertices)
    faces=''.join(f'<triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>' for f in mesh.faces)
    model=f'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">{escape(name)}</metadata><resources><object id="1" type="model"><mesh><vertices>{verts}</vertices><triangles>{faces}</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
    types='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels);z.writestr('3D/3dmodel.model',model)

manifest=[]
for p in PARTS:
    q=p['shape']
    mesh=tri(q)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise RuntimeError('INVALID '+p['id'])
    mesh.export(ASM/(p['id']+'.stl'))
    placed=tri(q.rotate(p['orientation']))
    offset=np.array([-placed.bounds[:,0].mean(),-placed.bounds[:,1].mean(),-placed.bounds[0,2]])
    placed.apply_translation(offset)
    placed.export(STL/(p['id']+'.stl'))
    write3mf(placed,THREE/(p['id']+'.3mf'),p['id'])
    row={k:v for k,v in p.items() if k!='shape'}
    row.update(dimensions_mm=placed.extents.tolist(),volume_mm3=float(mesh.volume),
               triangles=len(mesh.faces),watertight=bool(mesh.is_watertight),
               winding_consistent=bool(mesh.is_winding_consistent),components=1,
               print_translation=offset.tolist(),assembly_bounds=mesh.bounds.tolist())
    manifest.append(row)

# Independent reopened-file checks: positive volume, consistent winding, Z=0.
for row in manifest:
    again=trimesh.load_mesh(STL/(row['id']+'.stl'),process=True)
    assert again.is_watertight and again.is_winding_consistent and again.volume>0,row['id']
    assert abs(again.bounds[0,2])<1e-4,row['id']

# Neutral assembly and sampled motion collision checks, using exact volumetric intersections.
assembled=[p for p in PARTS if p['assembled']]
def intersection(a,b):
    ab=np.array(a.bounding_box()).reshape(2,3)
    bb=np.array(b.bounding_box()).reshape(2,3)
    if np.any(ab[1]<=bb[0]+.001) or np.any(bb[1]<=ab[0]+.001):return 0.0
    return (a^b).volume()
overlaps=[]
for i,a in enumerate(assembled):
    ab=np.array(a['shape'].bounding_box()).reshape(2,3)
    for b in assembled[i+1:]:
        bb=np.array(b['shape'].bounding_box()).reshape(2,3)
        if np.any(ab[1]<=bb[0]+.001) or np.any(bb[1]<=ab[0]+.001):continue
        v=intersection(a['shape'],b['shape'])
        if v>.10:overlaps.append({'a':a['id'],'b':b['id'],'intersection_mm3':round(v,3)})

def around(q,point,rotation):
    return q.translate(tuple(-np.array(point))).rotate(rotation).translate(point)

hardware_overlaps=[]
for a in HARDWARE:
    for b in assembled:
        v=intersection(a['shape'],b['shape'])
        if v>.10:hardware_overlaps.append({'hardware':a['id'],'print':b['id'],'intersection_mm3':round(v,3)})
hardware_pair_overlaps=[]
for i,a in enumerate(HARDWARE):
    for b in HARDWARE[i+1:]:
        v=intersection(a['shape'],b['shape'])
        if v>.10:hardware_pair_overlaps.append({'a':a['id'],'b':b['id'],'intersection_mm3':round(v,3)})

poses=[]
motion_parts=assembled+HARDWARE
for yaw,pitch in [(y,p) for y in range(-45,46,5) for p in range(-15,26,5)]:
    moved={}
    for p in motion_parts:
        q=p['shape']
        if p['group']=='head':q=around(q,(0,0,174),(pitch,0,0))
        if p['group'] in ['head','yaw']:q=around(q,(0,0,110),(0,0,yaw))
        moved[p['id']]=q
    for a in motion_parts:
        if a['group'] not in ['head','yaw']:continue
        for b in motion_parts:
            if a['group']==b['group']:continue
            if a['group']=='yaw' and b['group']=='head':continue
            v=intersection(moved[a['id']],moved[b['id']])
            if v>.20:poses.append({'yaw':yaw,'pitch':pitch,'a':a['id'],'b':b['id'],'intersection_mm3':round(v,3)})

for sign,label in [(-1,'L'),(1,'R')]:
    arms=[p for p in motion_parts if p['group']=='arm_'+label]
    for angle in range(0,61,5):
        for arm in arms:
            moving=around(arm['shape'],(sign*51,0,88),(0,-sign*angle,0))
            for other in motion_parts:
                if other['group']==arm['group']:continue
                v=intersection(moving,other['shape'])
                if v>.20:poses.append({'arm':label,'angle':angle,'a':arm['id'],'b':other['id'],'intersection_mm3':round(v,3)})

report={'parameters':P,'part_types':len(manifest),'print_files_passed':True,
        'neutral_intersections':overlaps,'reference_hardware_intersections':hardware_overlaps,
        'reference_hardware_pair_intersections':hardware_pair_overlaps,
        'sampled_motion_intersections':poses,'head_pose_samples':171,'shoulder_pose_samples_each':13,
        'scope':'Mesh geometry and rigid-part intersections at 5 degree samples, including simplified bearings, shafts, collars and retainer screws. No physical hardware fit, continuous collision, strength, thermal, cable or printer validation.'}
(ROOT/'parts.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'geometry-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'parts-list.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['文件','名称','数量','打印包络 mm','备注'])
    for p in manifest:w.writerow([p['id'],p['label'],p['quantity'],' × '.join(f'{v:.2f}' for v in p['dimensions_mm']),p['notes']])
print('AUDIT',json.dumps(report,ensure_ascii=False),flush=True)
