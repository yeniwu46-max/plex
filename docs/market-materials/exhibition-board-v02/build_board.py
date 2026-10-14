"""Build the editable SVG and 1:1 vector print PDF. Artwork is embedded unchanged."""
from pathlib import Path
import sys, json, base64, math, shutil, io, re
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
TMP = ROOT / 'tmp/pdfs/exhibition-board-v01'
sys.path.insert(0, str(TMP / 'deps'))
from PIL import Image
import qrcode
from fontTools.ttLib import TTFont as FontToolsFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject, NameObject

ASSETS = OUT / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
GEN = Path('C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f')
SOURCES = {
    'hero': 'exec-09bac785-3417-4461-b9ac-dfd94dab3ba9.png',
    'scene01': 'exec-7b847846-2f1a-4cad-8043-65249342c000.png',
    'scene02': 'exec-1c3df7dc-3ab1-41ab-a12d-bb7052429a91.png',
    'scene03': 'exec-3a7a0b79-b52e-4253-a162-d5d1b63fb313.png',
    'scene04': 'exec-e725ea3c-ebb4-44f2-913e-e0c7f08e9a2e.png',
}
for key, filename in SOURCES.items():
    target = ASSETS / f'xiao-e-{key}.png'
    if not target.exists():
        shutil.copy2(GEN / filename, target)
shutil.copy2(ROOT / 'frontend/public/assets/login-plex-mark.png', ASSETS / 'plex-brandmark.png')

COPY = {
    'brand': 'PLEX',
    'headline': ['把编程，', '学成一场宇宙探索。'],
    'intro': '面向编程初学者的 AI 个性化学习平台',
    'tag': '从 Python 入门出发',
    'scenes': [
        {'number':'01','title':'先认识你','body':'了解你的基础、目标与学习节奏，建立动态学习画像。'},
        {'number':'02','title':'找到你的学习航线','body':'结合知识关系与掌握情况，推荐下一步学什么、怎么学。'},
        {'number':'03','title':'卡住了，也有人陪你闯','body':'个性化讲解、练习与小 E 分步提示，让学习有方向。'},
        {'number':'04','title':'让每一步成长看得见','body':'错题复习与成长档案持续反馈，帮助调整后续学习安排。'},
    ],
    'highlights':['动态画像','游戏化学习','持续反馈'],
    'qr_caption':'扫码进入 PLEX，开启你的探索',
    'qr_url':'https://106.15.77.40/',
    'technology_title':'探索背后的引擎',
    'main_flow':['学习画像与作答记录','多智能体协同','个性化学习支持'],
    'agent_roles':'诊断 · 检索 · 资源 · 路径 · 反馈',
    'knowledge':'课程知识库＋知识图谱',
    'retrieval':'混合检索提供知识依据',
    'feedback':'反馈更新画像与学习路径',
    'teacher':'看学情 · 审资源 · 做干预',
    'stack':'Vue 3 · Flask · SQLAlchemy · MySQL · Chroma 向量检索',
    'closing':'和小 E 一起，点亮下一颗知识星。',
    'credit':'江南大学',
}
(OUT / 'copy.json').write_text(json.dumps(COPY,ensure_ascii=False,indent=2),encoding='utf-8')

# Instance variable fonts once. PDF subsets embed these; SVG embeds WOFF2 subsets.
FONTS = {}
for key, source, weight in [('regular','NotoSansSC-VF.ttf',400),('bold','NotoSansSC-VF.ttf',800),('brand','bahnschrift.ttf',700)]:
    target = TMP / f'{key}-static.ttf'
    if not target.exists():
        font = FontToolsFont(Path('C:/Windows/Fonts') / source)
        if 'fvar' in font:
            axes = {a.axisTag: a.defaultValue for a in font['fvar'].axes}
            if 'wght' in axes:
                axes['wght'] = weight
            font = instantiateVariableFont(font, axes, inplace=True)
        font.save(target)
    # Variable fonts inherit their default PostScript name after instancing.
    # Give each static face a unique name so ReportLab cannot merge weights.
    font = FontToolsFont(target)
    family = 'PLEX Noto Sans SC' if key != 'brand' else 'PLEX Bahnschrift'
    style = 'ExtraBold' if key == 'bold' else 'Bold' if key == 'brand' else 'Regular'
    postscript = ('PLEXNotoSansSC' if key != 'brand' else 'PLEXBahnschrift') + '-' + style
    for record in font['name'].names:
        values = {1:family,2:style,3:postscript,4:family+' '+style,6:postscript,16:family,17:style}
        if record.nameID in values:
            record.string = values[record.nameID].encode(record.getEncoding())
    font.save(target)
    pdfmetrics.registerFont(TTFont('Plex'+key, str(target)))
    FONTS[key] = target

MM = 72/25.4
W,H = 800,1800
CREAM,SKY,MINT,INK,TEAL,YELLOW,WHITE = '#FFFDF5','#C5E5F7','#DCF4E9','#123C46','#42BCAF','#FFE7A0','#FFFFFF'
SOFT = '#EAF5F7'
raw_pdf = TMP / 'board-raw.pdf'
pdf = canvas.Canvas(str(raw_pdf), pagesize=(810*MM,1810*MM), pageCompression=1,
                    initialFontName='Plexregular', initialFontSize=10)
pdf.setTitle('PLEX 作品展板 — 把编程，学成一场宇宙探索')
pdf.setAuthor('江南大学')
pdf.setSubject('800×1800 mm X 展架；四边 5 mm 出血；RGB；100% 实际尺寸')
pdf.translate(5*MM,5*MM)
SVG=[]
TEXT_LOG=[]
IMAGE_LOG=[]

def paint(fill=None,stroke=None,sw=1):
    if fill: pdf.setFillColor(HexColor(fill))
    if stroke: pdf.setStrokeColor(HexColor(stroke))
    pdf.setLineWidth(sw*MM)
    pdf.setLineJoin(1)
    pdf.setLineCap(1)

def attrs(fill,stroke,sw):
    return f'fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"'

def rect(x,y,w,h,fill=None,stroke=None,sw=1,r=0):
    paint(fill,stroke,sw)
    if r: pdf.roundRect(x*MM,(H-y-h)*MM,w*MM,h*MM,r*MM,stroke=bool(stroke),fill=bool(fill))
    else: pdf.rect(x*MM,(H-y-h)*MM,w*MM,h*MM,stroke=bool(stroke),fill=bool(fill))
    SVG.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" {attrs(fill,stroke,sw)}/>')

def circle(x,y,r,fill=None,stroke=None,sw=1):
    paint(fill,stroke,sw)
    pdf.circle(x*MM,(H-y)*MM,r*MM,stroke=bool(stroke),fill=bool(fill))
    SVG.append(f'<circle cx="{x}" cy="{y}" r="{r}" {attrs(fill,stroke,sw)}/>')

def path(commands,fill=None,stroke=None,sw=1,dash=None):
    paint(fill,stroke,sw)
    pdf.setDash([v*MM for v in dash] if dash else [])
    p=pdf.beginPath()
    d=[]
    for cmd in commands:
        op,*a=cmd
        d.append(op+' '.join(str(v) for v in a))
        if op=='M': p.moveTo(a[0]*MM,(H-a[1])*MM)
        elif op=='L': p.lineTo(a[0]*MM,(H-a[1])*MM)
        elif op=='C': p.curveTo(a[0]*MM,(H-a[1])*MM,a[2]*MM,(H-a[3])*MM,a[4]*MM,(H-a[5])*MM)
        elif op=='Z': p.close()
    pdf.drawPath(p,fill=bool(fill),stroke=bool(stroke))
    da=' stroke-dasharray="'+' '.join(str(v) for v in dash)+'"' if dash else ''
    SVG.append(f'<path d="{" ".join(d)}" {attrs(fill,stroke,sw)}{da}/>')
    pdf.setDash([])

def poly(points,fill=None,stroke=None,sw=1):
    path([('M',*points[0])]+[('L',*v) for v in points[1:]]+[('Z',)],fill,stroke,sw)

def line(x1,y1,x2,y2,color=INK,sw=1,dash=None):
    path([('M',x1,y1),('L',x2,y2)],stroke=color,sw=sw,dash=dash)

def star(x,y,r,color=TEAL,inner=.26,stroke=None):
    p=[]
    for i in range(8):
        angle=-math.pi/2+i*math.pi/4
        radius=r if i%2==0 else r*inner
        p.append((x+math.cos(angle)*radius,y+math.sin(angle)*radius))
    poly(p,color,stroke,1)

def text(s,x,y,pt=32,font='regular',color=INK,anchor='start',tag=''):
    width=pdfmetrics.stringWidth(s,'Plex'+font,pt)/MM
    xx=x if anchor=='start' else x-width/2 if anchor=='middle' else x-width
    pdf.setFillColor(HexColor(color))
    pdf.setFont('Plex'+font,pt)
    pdf.drawString(xx*MM,(H-y)*MM,s)
    fam='PlexBrand' if font=='brand' else 'PlexSans'
    weight=800 if font=='bold' else 700 if font=='brand' else 400
    SVG.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-weight="{weight}" font-size="{pt/MM:.6f}" text-anchor="{anchor}" fill="{color}">{escape(s)}</text>')
    asc,des=pdfmetrics.getAscentDescent('Plex'+font,pt)
    TEXT_LOG.append({'text':s,'x':xx,'y':y-asc/MM,'width_mm':width,'height_mm':(asc-des)/MM,'font_pt':pt,'font':font,'tag':tag})

def paragraph(s,x,y,width,pt=32,font='regular',leading=17,tag=''):
    lines=[]; current=''
    for char in s:
        if pdfmetrics.stringWidth(current+char,'Plex'+font,pt)/MM>width and current:
            # Avoid opening the next line with Chinese punctuation.
            if char in '，。；：！？、）':
                lines.append(current+char);current=''
            else:
                lines.append(current);current=char
        else: current+=char
    if current:lines.append(current)
    for i,s0 in enumerate(lines):text(s0,x,y+i*leading,pt,font,tag=tag)
    return len(lines)

def art(name,x,y,w):
    p=ASSETS/f'xiao-e-{name}.png'
    im=Image.open(p)
    h=w*im.height/im.width
    pdf.drawImage(ImageReader(im),x*MM,(H-y-h)*MM,w*MM,h*MM,mask='auto')
    data=base64.b64encode(p.read_bytes()).decode()
    SVG.append(f'<image id="illustration-{name}" x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{data}"/>')
    IMAGE_LOG.append({'asset':str(p.relative_to(OUT)).replace('\\','/'),'pixels':list(im.size),'placement_mm':[x,y,w,h],'effective_ppi':round(im.width/(w/25.4),2)})

def arrow(commands,color=INK,sw=1.8,head=5):
    path(commands,stroke=color,sw=sw)
    end=commands[-1]
    x,y=end[-2:]
    px,py=(end[-4:-2] if end[0]=='C' else commands[-2][-2:])
    a=math.atan2(y-py,x-px)
    poly([(x,y),(x-head*math.cos(a-.48),y-head*math.sin(a-.48)),(x-head*math.cos(a+.48),y-head*math.sin(a+.48))],color)

def badge(number,x,y):
    circle(x+2,y+3,22,TEAL)
    circle(x,y,22,CREAM,INK,1.5)
    text(number,x,y+8,64,'brand',anchor='middle')

def pill(label,x,y,w,fill=MINT,pt=31):
    rect(x,y,w,23,fill,INK,.7,r=11.5)
    text(label,x+w/2,y+16.2,pt,'bold',anchor='middle')

# Layout only; build_board.py includes this block and the shared vector renderer.
# Units: mm, from the top-left trim corner; all text remains live and horizontal.
COPY['headline']=['把编程，','学成一场','宇宙探索。']
COPY['scenes'][0]['body']='了解你的基础、目标与学习节奏，建立动态学习画像。'
COPY['scenes'][1]['body']='结合知识关系与掌握情况，推荐下一步的学习内容，也给你清楚的学习方法。'
COPY['scenes'][2]['body']='个性化讲解与练习，小 E 提供分步提示。'
COPY['scenes'][3]['body']='错题复习与成长档案，持续反馈学习表现，调整后续学习安排。'
COPY['scenes'][0]['feature']='基础 · 目标 · 节奏'
COPY['scenes'][1]['feature']='知识星轨 · 下一步推荐'
COPY['scenes'][2]['feature']='探索舱 · 小 E 陪伴'
COPY['scenes'][3]['feature']='错题复习 · 成长档案'
COPY['role_explanations']=[['诊断','看基础'],['检索','找依据'],['资源','配内容'],['路径','排顺序'],['反馈','再调整']]
(OUT/'copy.json').write_text(json.dumps(COPY,ensure_ascii=False,indent=2),encoding='utf-8')

def small_label(label,x,y,w,fill=YELLOW,pt=37):
    poly([(x,y),(x+w,y),(x+w-5,y+28),(x-5,y+28)],fill,INK,.7)
    text(label,x+w/2-2.5,y+19.5,pt,'bold',anchor='middle')

def chapter(number,x,y):
    circle(x+3,y+3,29,TEAL)
    circle(x,y,29,YELLOW,INK,1.5)
    text(number,x,y+11,88,'brand',anchor='middle')

# A typographic hero: large stacked headline and a planetary comic cutout.
rect(-5,-5,810,1810,CREAM)
poly([(458,-5),(805,-5),(805,375),(726,394),(489,304)],SKY)
poly([(719,-5),(805,-5),(805,375),(744,324),(663,117)],MINT)
circle(648,216,139,MINT)
path([('M',506,260),('C',587,352,794,248,781,155),('C',770,72,577,111,506,260)],stroke=WHITE,sw=4)
star(749,98,22,YELLOW,stroke=INK)
star(509,102,12,TEAL)
star(753,332,13,INK)

mark=ASSETS/'plex-brandmark.png'
mark_data=base64.b64encode(mark.read_bytes()).decode()
pdf.saveState()
clip=pdf.beginPath();clip.rect(43*MM,(H-112)*MM,73*MM,77*MM)
pdf.clipPath(clip,stroke=0,fill=0)
pdf.drawImage(str(mark),17*MM,(H-166.6)*MM,127*MM,169.33*MM,mask='auto')
pdf.restoreState()
SVG.append('<defs><clipPath id="brand-viewport"><rect x="43" y="35" width="73" height="77"/></clipPath></defs>')
SVG.append(f'<image x="17" y="-2.73" width="127" height="169.33" clip-path="url(#brand-viewport)" href="data:image/png;base64,{mark_data}"/>')
text('PLEX',118,107,215,'brand')
text('从 Python 入门出发',506,59,38,'bold')
text('把编程，',45,183,170,'bold')
text('学成一场',45,246,170,'bold')
poly([(35,252),(452,252),(475,329),(35,329)],INK)
text('宇宙探索。',45,314,170,'bold',CREAM)
poly([(569,157),(714,132),(742,304),(515,322)],CREAM,INK,1.5)
art('hero',533,116,212)
path([('M',749,298),('C',783,365,661,383,601,405)],stroke=TEAL,sw=4)
text(COPY['intro'],46,351,44)

# Three equal, large reading anchors instead of tiny scattered pills.
for x,label,fill in [(44,'动态画像',MINT),(290,'游戏化学习',YELLOW),(536,'持续反馈',SKY)]:
    poly([(x,367),(x+221,367),(x+210,395),(x-8,395)],fill,INK,1)
    star(x+17,381,6,INK)
    text(label,x+42,387,41,'bold')

# Four filled comic chapters. Wider text, bigger type, additional feature tags.
route=[('M',681,399),('C',663,507,16,485,53,612),('C',40,787,748,726,752,850),('C',790,1005,4,1058,47,1246)]
path(route,stroke=MINT,sw=14)
path(route,stroke=TEAL,sw=3)

poly([(45,424),(630,409),(636,596),(49,609)],TEAL)
poly([(38,416),(623,401),(629,588),(42,601)],SKY,INK,1.8)
art('scene01',51,441,298)
chapter('01',72,413)
text('先认识你',349,447,82,'bold')
for s,y in [('了解你的基础、目标',484),('与学习节奏，',508),('建立动态学习画像。',532)]:
    text(s,350,y,44,tag='scene01-body')
small_label(COPY['scenes'][0]['feature'],351,551,237,YELLOW)

poly([(49,629),(622,612),(639,806),(36,815)],TEAL)
poly([(43,621),(616,604),(633,798),(30,807)],MINT,INK,1.8)
art('scene02',53,643,298)
chapter('02',72,620)
text('找到你的学习航线',349,649,72,'bold')
for s,y in [('结合知识关系与掌握情况，',690),('推荐下一步的学习内容，',714),('也给你清楚的学习方法。',738)]:
    text(s,350,y,44,tag='scene02-body')
small_label(COPY['scenes'][1]['feature'],351,757,244,SKY)

# QR remains at standing height. Larger caption, same 90 mm vector code.
rect(650,500,114,240,TEAL,r=3)
rect(645,495,114,240,WHITE,INK,1.5,r=3)
text('探索入口',702,527,42,'bold',anchor='middle')
line(653,541,751,541,INK,.7,[2.5,2.5])
QR=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=12,border=4)
QR.add_data(COPY['qr_url']);QR.make(fit=True)
matrix=QR.get_matrix();n=len(matrix);unit=90/n
qx,qy=657,555
rect(qx,qy,90,90,WHITE)
qr_paths=[]
for row in range(n):
    col=0
    while col<n:
        if matrix[row][col]:
            start=col
            while col<n and matrix[row][col]:col+=1
            rect(qx+start*unit,qy+row*unit,(col-start)*unit,unit,INK)
            qr_paths.append(f'M{start},{row}h{col-start}v1h-{col-start}z')
        else:col+=1
QR.make_image(fill_color=INK,back_color='white').save(ASSETS/'plex-entry-qr.png')
(ASSETS/'plex-entry-qr.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="90mm" viewBox="0 0 {n} {n}"><rect width="{n}" height="{n}" fill="white"/><path d="{" ".join(qr_paths)}" fill="{INK}"/></svg>',encoding='utf-8')
text('扫码进入',702,672,38,'bold',anchor='middle')
text('PLEX，',702,694,40,'bold',anchor='middle')
text('开启你的探索',702,720,36,'bold',anchor='middle')

poly([(136,838),(766,816),(752,1016),(120,1030)],TEAL)
poly([(130,830),(760,808),(746,1008),(114,1022)],SKY,INK,1.8)
art('scene03',455,837,300)
chapter('03',99,842)
text('卡住了，',160,864,78,'bold')
text('也有人陪你闯',160,895,78,'bold')
text('个性化讲解与练习，',161,934,44,tag='scene03-body')
text('小 E 提供分步提示。',161,958,44,tag='scene03-body')
small_label(COPY['scenes'][2]['feature'],163,977,259,YELLOW)
star(69,937,22,TEAL,stroke=INK)
star(91,991,9,YELLOW,stroke=INK)

poly([(44,1053),(719,1040),(746,1238),(58,1252)],TEAL)
poly([(38,1045),(713,1032),(740,1230),(52,1244)],MINT,INK,1.8)
art('scene04',51,1068,300)
chapter('04',711,1050)
text('让每一步成长看得见',371,1090,72,'bold')
text('错题复习与成长档案，',372,1130,44,tag='scene04-body')
text('持续反馈学习表现，',372,1154,44,tag='scene04-body')
text('调整后续学习安排。',372,1178,44,tag='scene04-body')
small_label(COPY['scenes'][3]['feature'],373,1197,300,YELLOW)

# Compact, large-type engineering diagram with explicit agent role meanings.
poly([(-5,1264),(805,1246),(805,1734),(-5,1734)],SOFT)
poly([(34,1259),(565,1255),(565,1310),(34,1314)],INK)
text('探索背后的引擎',51,1297,82,'bold',CREAM)
star(718,1287,22,TEAL,stroke=INK)

rect(46,1332,354,72,MINT,INK,1.4,r=4)
text('课程知识库＋知识图谱',223,1360,47,'bold',anchor='middle')
text('混合检索提供知识依据',223,1389,40,anchor='middle')
rect(437,1332,316,72,YELLOW,INK,1.4,r=4)
text('教师侧',457,1358,46,'bold')
text('看学情 · 审资源 · 做干预',457,1389,39)
arrow([('M',223,1404),('L',223,1420),('L',377,1420),('L',377,1438)],TEAL,2)
arrow([('M',484,1404),('L',484,1438)],INK,1.3)
arrow([('M',653,1404),('L',653,1438)],INK,1.3)

rect(46,1445,189,105,WHITE,INK,1.5,r=4)
rect(287,1445,229,105,TEAL,INK,1.5,r=4)
rect(568,1445,185,105,WHITE,INK,1.5,r=4)
text('学习画像',140.5,1482,55,'bold',anchor='middle')
text('与作答记录',140.5,1520,46,anchor='middle')
text('多智能体协同',401.5,1480,54,'bold',anchor='middle')
text('诊断 · 检索 · 资源',401.5,1511,38,anchor='middle')
text('路径 · 反馈',401.5,1535,38,anchor='middle')
text('个性化',660.5,1482,55,'bold',anchor='middle')
text('学习支持',660.5,1520,55,'bold',anchor='middle')
arrow([('M',235,1497),('L',280,1497)],INK,2.2)
arrow([('M',516,1497),('L',561,1497)],INK,2.2)

arrow([('M',660,1550),('L',660,1580),('C',660,1591,655,1597,643,1597),('L',158,1597),('C',147,1597,140,1590,140,1580),('L',140,1557)],TEAL,2.4)
text('练习结果',673,1580,36)
rect(286,1581,230,31,SOFT)
text('反馈更新画像与学习路径',401,1604,43,'bold',anchor='middle')

# Five functional roles, readable to a general audience without jargon.
for i,(role,meaning) in enumerate(COPY['role_explanations']):
    x=46+i*145
    rect(x,1630,129,60,CREAM,INK,.9,r=3)
    text(role,x+64.5,1654,43,'bold',anchor='middle')
    text(meaning,x+64.5,1679,39,anchor='middle')
text(COPY['stack'],400,1718,36,anchor='middle')

# Strong closing bar, with all text above the bottom mounting safe zone.
poly([(-5,1734),(805,1734),(805,1805),(-5,1805)],INK)
text(COPY['closing'],44,1761,46,'bold',CREAM)
text(COPY['credit'],753,1761,46,'bold',CREAM,anchor='end')
star(562,1767,16,TEAL)


# Save the live-type SVG, with embedded illustration pixels and subset fonts.
all_text=''.join(v['text'] for v in TEXT_LOG)
fontcss=[]
for key,family,weight in [('regular','PlexSans',400),('bold','PlexSans',800),('brand','PlexBrand',700)]:
    font=FontToolsFont(FONTS[key])
    options=subset.Options();options.flavor='woff2'
    options.name_IDs=['*'];options.name_legacy=True;options.name_languages=['*']
    sub=subset.Subsetter(options=options);sub.populate(text=all_text);sub.subset(font)
    font.flavor='woff2';buf=io.BytesIO();font.save(buf)
    encoded=base64.b64encode(buf.getvalue()).decode()
    fontcss.append(f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};src:url(data:font/woff2;base64,{encoded}) format('woff2')}}")
svg_header=f'<svg xmlns="http://www.w3.org/2000/svg" width="810mm" height="1810mm" viewBox="0 0 810 1810"><title>PLEX 作品展板</title><desc>800×1800mm finished size, 5mm bleed. Live editable text; RGB.</desc><defs><style>{"".join(fontcss)}</style></defs><g transform="translate(5 5)">'
(OUT/'plex-exhibition-board-editable.svg').write_text(svg_header+'\n'.join(SVG)+'</g></svg>',encoding='utf-8')
pdf.showPage();pdf.save()
reader=PdfReader(raw_pdf);writer=PdfWriter();writer.append_pages_from_reader(reader)
page=writer.pages[0]
page.trimbox=RectangleObject([5*MM,5*MM,805*MM,1805*MM])
page.bleedbox=RectangleObject([0,0,810*MM,1810*MM])
writer.add_metadata(reader.metadata)
writer._root_object.update({NameObject('/ViewerPreferences'): __import__('pypdf').generic.DictionaryObject({NameObject('/PrintScaling'):NameObject('/None')})})
with (OUT/'plex-exhibition-board-print.pdf').open('wb') as f:writer.write(f)

checks={
    'finished_mm':[800,1800],'bleed_mm':5,'media_mm':[810,1810],
    'important_content_safe_inset_mm':35,'color_space':'RGB',
    'qr':{'url':COPY['qr_url'],'size_including_quiet_zone_mm':90,'quiet_zone_modules':4,'matrix_size':n,'center_above_floor_mm':1800-(qy+45),'error_correction':'M'},
    'images':IMAGE_LOG,'text_elements':TEXT_LOG,
}
for im in IMAGE_LOG:assert im['effective_ppi']>=150,im
unsafe=[t for t in TEXT_LOG if t['x']<35 or t['x']+t['width_mm']>765 or t['y']<35 or t['y']+t['height_mm']>1765]
checks['unsafe_text']=unsafe
(OUT/'preflight.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
assert not unsafe,unsafe
print(json.dumps({'pdf':str(OUT/'plex-exhibition-board-print.pdf'),'svg':str(OUT/'plex-exhibition-board-editable.svg'),'illustrations':len(IMAGE_LOG),'min_ppi':min(i['effective_ppi'] for i in IMAGE_LOG),'text_objects':len(TEXT_LOG)},ensure_ascii=False))
