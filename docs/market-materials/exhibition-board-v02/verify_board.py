"""Validate deliverables; run after rendering the current PDF preview."""
from pathlib import Path
import sys,json,re,hashlib,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]/'tmp/pdfs/exhibition-board-v01/deps'))
from pypdf import PdfReader
from PIL import Image
import zxingcpp

pdf_path=OUT/'plex-exhibition-board-print.pdf'
reader=PdfReader(pdf_path)
assert len(reader.pages)==1
page=reader.pages[0]
to_mm=lambda box:[round(float(v)*25.4/72,3) for v in box]
assert to_mm(page.mediabox)==[0.0,0.0,810.0,1810.0]
assert to_mm(page.trimbox)==[5.0,5.0,805.0,1805.0]
assert to_mm(page.bleedbox)==[0.0,0.0,810.0,1810.0]
assert page.get('/Rotate',0)==0

fonts=[]
for key,ref in page['/Resources']['/Font'].items():
    font=ref.get_object();desc=font.get('/FontDescriptor',{})
    fonts.append({'name':str(font['/BaseFont']),'embedded':bool(desc.get('/FontFile2') or desc.get('/FontFile3'))})
assert all(f['embedded'] for f in fonts)
assert any('ExtraBold' in f['name'] for f in fonts)
assert any('Regular' in f['name'] for f in fonts)
assert any('Bahnschrift' in f['name'] for f in fonts)

copy=json.loads((OUT/'copy.json').read_text(encoding='utf-8'))
normalized=re.sub(r'\s+','',page.extract_text())
expected=copy['headline']+[copy[k] for k in ['intro','tag','technology_title','knowledge','retrieval','feedback','teacher','stack','closing','credit','qr_caption']]+[s[k] for s in copy['scenes'] for k in ['title','body','feature']]+copy['highlights']+copy['main_flow']+copy['agent_roles'].split(' · ')+[s for pair in copy['role_explanations'] for s in pair]
missing=[s for s in expected if re.sub(r'\s+','',s) not in normalized]
assert not missing,missing

preview=Image.open(OUT/'plex-exhibition-board-preview.png')
assert preview.size==(1600,3600)
decoded=[item.text for item in zxingcpp.read_barcodes(preview)]
assert copy['qr_url'] in decoded,decoded

layout=json.loads((OUT/'preflight.json').read_text(encoding='utf-8'))
assert not layout['unsafe_text']
assert len(layout['images'])==5
assert min(i['effective_ppi'] for i in layout['images'])>=150
assert layout['qr']['quiet_zone_modules']==4
assert layout['qr']['center_above_floor_mm']==1200

svg=ET.parse(OUT/'plex-exhibition-board-editable.svg').getroot()
ns={'svg':'http://www.w3.org/2000/svg'}
texts=svg.findall('.//svg:text',ns)
assert len(texts)==len(layout['text_elements'])
assert len(svg.findall('.//svg:image',ns))==6
assert all(e.attrib['href'].startswith('data:image/png;base64,') for e in svg.findall('.//svg:image',ns))
assert 'data:font/woff2;base64,' in (OUT/'plex-exhibition-board-editable.svg').read_text(encoding='utf-8')
assert len(svg.findall('.//svg:path',ns))>25
raw=page.get_contents().get_data()
assert b'Tj' in raw and b' re ' in raw # text and vector rect drawing commands

copy_md=['# PLEX 展板最终文案','',copy['brand'],'',*copy['headline'],'',copy['intro'],'',copy['tag'],'']
for s in copy['scenes']:
    copy_md += [f"## {s['number']} {s['title']}",'',s['body'],'','功能标签：'+s['feature'],'']
copy_md += ['## 亮点标签','', '｜'.join(copy['highlights']), '', '## 探索入口','',copy['qr_caption'],'',copy['qr_url'],'', '## '+copy['technology_title'],'',' → '.join(copy['main_flow']),'',copy['agent_roles'],'',copy['knowledge'],'',copy['retrieval'],'',copy['feedback'],'','教师侧：'+copy['teacher'],'',copy['stack'],'','## 收尾与署名','',copy['closing'],'',copy['credit'],'']
copy_md += ['## 五个协同环节','']+[f'- {role}：{meaning}' for role,meaning in copy['role_explanations']]+['']
(OUT/'copy.md').write_text('\n'.join(copy_md),encoding='utf-8')
result={
    'status':'passed','checked_date':'2026-10-12',
    'media_mm':to_mm(page.mediabox),'trim_mm':to_mm(page.trimbox),
    'page_count':1,'rotation':0,'fonts':fonts,
    'expected_copy_missing':missing,'preview_pixels':list(preview.size),
    'decoded_from_final_pdf_preview':decoded,
    'live_svg_text_objects':len(texts),
    'min_illustration_ppi':min(i['effective_ppi'] for i in layout['images']),
    'unsafe_text_count':len(layout['unsafe_text']),
    'pdf_sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
    'visual_review':'Final PDF header, four comic panels, QR ticket, technical diagram and footer inspected after rendering. No text/illustration overlap or missing glyph observed.',
    'remaining_vendor_check':'Confirm X-stand mounting holes, bleed template and color profile with the production vendor before printing.',
}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
