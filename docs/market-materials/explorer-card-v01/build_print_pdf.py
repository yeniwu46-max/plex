"""Package the unmodified imagegen PNGs into a two-page, physical-size PDF.

Requires reportlab, pypdf, Pillow. Does not edit, resize, or redraw PNG pixels.
Run from any directory. Intermediate verification files live in tmp/pdfs/.
"""

import hashlib
import io
import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, RectangleObject
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
QA = ROOT.parents[2] / 'tmp' / 'pdfs' / 'explorer-card-v01'
QA.mkdir(parents=True, exist_ok=True)
PDF = ROOT / 'xiao-e-explorer-card-print-61x91mm.pdf'
FILES = [ROOT / 'xiao-e-explorer-front.png', ROOT / 'xiao-e-explorer-back.png']
WIDTH, HEIGHT = 61 * mm, 91 * mm
BLEED, SAFE = 3 * mm, 6 * mm
TRIM = [BLEED, BLEED, WIDTH - BLEED, HEIGHT - BLEED]


def make_pages(guides=False):
    data = io.BytesIO()
    page = canvas.Canvas(data, pagesize=(WIDTH, HEIGHT), pageCompression=1)
    page.setTitle('Xiao E explorer card - front and back - 55x85 mm trim')
    page.setAuthor('PLEX')
    page.setSubject('RGB artwork; 3 mm bleed; upright portrait; no text in artwork')
    for image_path in FILES:
        # Physical placement only. Source image streams retain native resolution.
        page.drawImage(str(image_path), 0, 0, width=WIDTH, height=HEIGHT,
                       preserveAspectRatio=False, mask=None)
        if guides:
            page.setLineWidth(0.4)
            page.setStrokeColorRGB(1, 0, 0.75)
            page.rect(BLEED, BLEED, WIDTH - 2 * BLEED, HEIGHT - 2 * BLEED)
            page.setStrokeColorRGB(0, 1, 0.15)
            page.setDash(2, 1)
            page.rect(SAFE, SAFE, WIDTH - 2 * SAFE, HEIGHT - 2 * SAFE)
            page.setDash()
        page.showPage()
    page.save()
    data.seek(0)
    return data


writer = PdfWriter()
reader = PdfReader(make_pages())
for page in reader.pages:
    page.trimbox = RectangleObject(TRIM)
    page.bleedbox = RectangleObject([0, 0, WIDTH, HEIGHT])
    page.cropbox = RectangleObject([0, 0, WIDTH, HEIGHT])
    writer.add_page(page)
writer.add_metadata(reader.metadata)
writer._root_object[NameObject('/ViewerPreferences')] = DictionaryObject({
    NameObject('/PrintScaling'): NameObject('/None'),
    NameObject('/Duplex'): NameObject('/DuplexFlipLongEdge'),
})
with PDF.open('wb') as stream:
    writer.write(stream)

# Internal guide proof: pink = trim; green = critical-content safe area.
(QA / 'guides.pdf').write_bytes(make_pages(guides=True).getvalue())

# Internal trimmed preview, useful for checking the actual card-size composition.
trim_writer = PdfWriter()
for page in PdfReader(PDF).pages:
    page.cropbox = RectangleObject(TRIM)
    trim_writer.add_page(page)
with (QA / 'trim-preview.pdf').open('wb') as stream:
    trim_writer.write(stream)

result = {'pdf': PDF.name, 'page_count': 2, 'color': 'RGB', 'pages': []}
final = PdfReader(PDF)
assert len(final.pages) == 2
for index, (page, image_path) in enumerate(zip(final.pages, FILES), 1):
    with Image.open(image_path) as image:
        px_w, px_h = image.size
        assert image.mode == 'RGB'
        ppi_x, ppi_y = px_w / (61 / 25.4), px_h / (91 / 25.4)
        assert min(ppi_x, ppi_y) >= 300
        rgb_sha = hashlib.sha256(image.tobytes()).hexdigest()
    assert not page.extract_text().strip()
    assert page.get('/Rotate', 0) == 0
    for got, expected in zip(page.mediabox, [0, 0, WIDTH, HEIGHT]):
        assert abs(float(got) - expected) < 0.001
    for got, expected in zip(page.trimbox, TRIM):
        assert abs(float(got) - expected) < 0.001
    images = list(page.images)
    assert len(images) == 1
    assert images[0].image.size == (px_w, px_h)
    assert hashlib.sha256(images[0].image.convert('RGB').tobytes()).hexdigest() == rgb_sha
    result['pages'].append({
        'page': index, 'side': 'front' if index == 1 else 'back',
        'png': image_path.name, 'pixels': [px_w, px_h],
        'effective_ppi': [round(ppi_x, 2), round(ppi_y, 2)],
        'media_mm': [61, 91], 'bleed_mm_each_edge': 3,
        'trim_mm': [55, 85], 'trim_box_mm': [3, 3, 58, 88],
        'safe_box_mm': [6, 6, 55, 85], 'rotation': 0,
        'embedded_rgb_pixels_identical': True,
        'sha256_png': hashlib.sha256(image_path.read_bytes()).hexdigest(),
    })
(ROOT / 'print-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
