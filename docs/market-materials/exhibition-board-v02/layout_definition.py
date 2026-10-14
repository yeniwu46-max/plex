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
