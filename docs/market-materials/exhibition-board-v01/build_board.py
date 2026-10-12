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

# --- Background and header, 0–380 mm ---
rect(-5,-5,810,1810,CREAM)
poly([(452,-5),(805,-5),(805,330),(639,365),(458,301)],SKY)
poly([(630,-5),(805,-5),(805,280),(730,302),(680,184)],MINT)
path([('M',482,-5),('C',465,98,778,143,802,302)],stroke=WHITE,sw=3)
star(741,54,21,YELLOW)
star(483,301,12,TEAL)
star(750,330,10,INK)
for yy in range(327,358,9):
    for xx in range(501,556,9):
        circle(xx,yy,.8,TEAL)

# Existing project star image, placed via a viewport; source pixels unchanged.
mark=ASSETS/'plex-brandmark.png'
mark_data=base64.b64encode(mark.read_bytes()).decode()
pdf.saveState()
clip=pdf.beginPath();clip.rect(47*MM,(H-107)*MM,64*MM,67*MM)
pdf.clipPath(clip,stroke=0,fill=0)
pdf.drawImage(str(mark),23*MM,(H-154)*MM,113*MM,150.667*MM,mask='auto')
pdf.restoreState()
SVG.append('<defs><clipPath id="brand-viewport"><rect x="47" y="40" width="64" height="67"/></clipPath></defs>')
SVG.append(f'<image x="23" y="3.333" width="113" height="150.667" clip-path="url(#brand-viewport)" href="data:image/png;base64,{mark_data}"/>')
text('PLEX',115,101,176,'brand')
text('把编程，',47,188,136,'bold')
text('学成一场宇宙探索。',47,247,126,'bold')
line(49,262,443,262,TEAL,4)
text(COPY['intro'],50,298,34)
pill(COPY['tag'],50,320,178,YELLOW,31)
poly([(585,151),(699,126),(725,280),(548,306)],MINT,INK,1.3)
art('hero',535,102,210)
path([('M',746,264),('C',790,341,725,374,656,388)],stroke=TEAL,sw=2.6)
star(670,379,9,YELLOW,stroke=INK)

# --- Four distinct comic panels along an S-shaped orbital route ---
route=[('M',655,385),('C',651,465,257,483,91,578),('C',-6,702,218,810,643,754),('C',788,735,797,895,695,934),('C',522,1005,84,1063,107,1143)]
path(route,stroke=MINT,sw=14)
path(route,stroke=TEAL,sw=2.2)

poly([(43,417),(643,395),(627,565),(57,579)],TEAL)
poly([(39,408),(639,386),(623,556),(53,570)],SKY,INK,1.5)
art('scene01',61,411,278)
badge('01',62,402)
text(COPY['scenes'][0]['title'],352,448,56,'bold')
text('了解你的基础、目标与学习节奏，',352,481,32,tag='scene01-body')
text('建立动态学习画像。',352,498,32,tag='scene01-body')
pill('动态画像',654,411,105,MINT,30)

poly([(56,598),(621,571),(639,746),(41,769)],TEAL)
poly([(52,589),(617,562),(635,737),(37,760)],MINT,INK,1.5)
art('scene02',62,589,278)
badge('02',69,594)
text(COPY['scenes'][1]['title'],350,628,53,'bold')
text('结合知识关系与掌握情况，',350,662,32,tag='scene02-body')
text('推荐下一步学什么、怎么学。',350,679,32,tag='scene02-body')

# QR ticket: 90 mm incl. four-module quiet zone, centered 1.2 m above floor.
rect(650,494,114,220,TEAL,r=3)
rect(645,489,114,220,WHITE,INK,1.3,r=3)
text('探索入口',702,519,34,'bold',anchor='middle')
line(653,535,751,535,INK,.6,[2.5,2.5])
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
            x,y=qx+start*unit,qy+row*unit
            rect(x,y,(col-start)*unit,unit,INK)
            qr_paths.append(f'M{start},{row}h{col-start}v1h-{col-start}z')
        else:col+=1
QR.make_image(fill_color=INK,back_color='white').save(ASSETS/'plex-entry-qr.png')
(ASSETS/'plex-entry-qr.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="90mm" viewBox="0 0 {n} {n}"><rect width="{n}" height="{n}" fill="white"/><path d="{" ".join(qr_paths)}" fill="{INK}"/></svg>',encoding='utf-8')
text('扫码进入 PLEX，',702,672,28,'bold',anchor='middle')
text('开启你的探索',702,690,28,anchor='middle')

poly([(174,786),(764,752),(747,927),(159,952)],TEAL)
poly([(170,777),(760,743),(743,918),(155,943)],SKY,INK,1.5)
art('scene03',455,747,288)
badge('03',161,779)
text(COPY['scenes'][2]['title'],181,820,53,'bold')
text('个性化讲解、练习与小 E 分步提示，',181,854,32,tag='scene03-body')
text('让学习有方向。',181,871,32,tag='scene03-body')
pill('游戏化学习',42,830,118,YELLOW,30)
star(78,902,19,TEAL,stroke=INK)

poly([(42,977),(707,941),(741,1101),(61,1125)],TEAL)
poly([(38,968),(703,932),(737,1092),(57,1116)],MINT,INK,1.5)
art('scene04',58,938,294)
badge('04',711,955)
text(COPY['scenes'][3]['title'],377,997,53,'bold')
text('错题复习与成长档案持续反馈，',377,1031,32,tag='scene04-body')
text('帮助调整后续学习安排。',377,1048,32,tag='scene04-body')
pill('持续反馈',586,1090,111,YELLOW,30)

# --- Engineering view: clean vector diagram with a visible feedback loop ---
poly([(-5,1177),(805,1139),(805,1614),(-5,1654)],SOFT)
line(41,1178,759,1144,INK,1.5)
star(62,1187,12,TEAL)
text(COPY['technology_title'],91,1204,65,'bold')

# Knowledge input into orchestration.
rect(255,1232,292,69,MINT,INK,1.1,r=6)
text(COPY['knowledge'],401,1259,38,'bold',anchor='middle')
text(COPY['retrieval'],401,1283,30,anchor='middle')
arrow([('M',401,1301),('L',401,1331)],TEAL,2)

# Three primary stages (not a claim that every agent runs on every request).
rect(48,1333,187,105,WHITE,INK,1.3,r=5)
rect(286,1333,228,105,TEAL,INK,1.3,r=5)
rect(565,1333,187,105,WHITE,INK,1.3,r=5)
text('学习画像',141.5,1374,39,'bold',anchor='middle')
text('与作答记录',141.5,1400,34,anchor='middle')
text('多智能体协同',400,1368,40,'bold',anchor='middle')
text('诊断 · 检索 · 资源',400,1395,29,anchor='middle')
text('路径 · 反馈',400,1415,29,anchor='middle')
text('个性化',658.5,1374,39,'bold',anchor='middle')
text('学习支持',658.5,1400,39,'bold',anchor='middle')
arrow([('M',235,1385),('L',279,1385)],INK,2)
arrow([('M',514,1385),('L',558,1385)],INK,2)

# Practice results feed back into the profile and learning route.
arrow([('M',659,1438),('L',659,1480),('C',659,1490,652,1496,643,1496),('L',158,1496),('C',148,1496,141,1490,141,1480),('L',141,1445)],TEAL,2.2)
rect(312,1481,182,29,SOFT)
text(COPY['feedback'],403,1501,32,'bold',anchor='middle')
text('练习结果',676,1471,28)

# Teacher joins resource governance and learning intervention, independently.
rect(286,1532,350,57,CREAM,INK,1.1,r=5)
text('教师侧',309,1554,29,'bold')
text(COPY['teacher'],309,1577,32)
arrow([('M',286,1560),('L',260,1560),('L',260,1502),('C',268,1502,268,1490,260,1490),('L',260,1458),('L',357,1458),('L',357,1445)],INK,1.2,4)
arrow([('M',636,1560),('L',730,1560),('L',730,1445)],INK,1.2,4)
text(COPY['stack'],400,1626,28,anchor='middle')

# --- Footer: short, open, and with the school credit away from stand holes ---
path([('M',-5,1749),('C',192,1622,436,1844,805,1687)],stroke=MINT,sw=21)
path([('M',-5,1749),('C',192,1622,436,1844,805,1687)],stroke=TEAL,sw=1.5)
star(693,1706,26,YELLOW,stroke=INK)
text(COPY['closing'],48,1704,47,'bold')
text(COPY['credit'],50,1745,36,'bold')
star(257,1739,7,TEAL)

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
