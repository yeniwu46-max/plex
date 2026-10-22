"""Geometry/real-PDF parsing regression; no model calls or main database writes."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from app.services.knowledge.pdf_cleanup import clean_pdf_pages, lines_to_markdown
from app.services.knowledge.parser_service import ParserService, ParserError
from app.services.knowledge.chunk_service import ChunkService
from app.services.knowledge.index_service import IndexService
from app.models import KnowledgeDocument, KnowledgeChunk, db
from test_learner_state import app


def row(text, top, font='Helvetica', size=10):
    return {'text': text, 'top': top, 'bottom': top + size,
            'chars': [{'text': c, 'fontname': font, 'size': size} for c in text]}


def pages(count=4):
    return [{'height': 800, 'lines': [
        row('PLEX Python course', 20), row('An explanation of loops and stopping conditions.', 100),
        row('Boundary values need their own tests.', 120), row(f'Page {i + 1} of {count}', 775),
    ]} for i in range(count)]


def test_only_repeated_geometric_margins_are_removed():
    cleaned, report = clean_pdf_pages(pages())
    assert report['removed_line_count'] == 8
    assert report['affected_page_count'] == 4
    assert all(len(lines) == 2 for lines in cleaned)
    assert all('Boundary values' in lines[1]['text'] for lines in cleaned)


@pytest.mark.parametrize('count', [1, 2])
def test_short_documents_keep_ambiguous_margins(count):
    source = pages(count)
    cleaned, report = clean_pdf_pages(source)
    assert report['removed_line_count'] == 0
    assert cleaned == [p['lines'] for p in source]


@pytest.mark.parametrize('replacement', [
    row('for i in range(5):', 20), row('return count', 20),
    row('total += value', 20), row('Repeated code comment', 20, font='Courier'),
    row('Chapter summary', 20, font='Helvetica-Bold'), row('Chapter summary', 10, size=20),
    row('2. Boundary conditions', 20),
])
def test_repeated_code_and_headings_at_page_edge_are_kept(replacement):
    source = pages()
    for page in source:
        page['lines'][0] = replacement
    cleaned, _ = clean_pdf_pages(source)
    assert all(lines[0] == replacement for lines in cleaned)


def test_body_occurrence_protects_the_same_header_and_numeric_content():
    source = pages()
    source[0]['lines'].insert(2, row('PLEX Python course', 140))
    source[0]['lines'].insert(3, row('Page 1 of 4', 160))
    _, report = clean_pdf_pages(source)
    assert report['removed_line_count'] == 0


def test_no_majority_or_no_gap_does_not_remove_repeated_text():
    source = pages(6)
    for page in source[2:]:
        page['lines'][0] = row('A different title', 100)
    cleaned, _ = clean_pdf_pages(source)
    assert all(any(line['text'] == 'PLEX Python course' for line in lines) for lines in cleaned[:2])
    source = pages()
    for page in source:
        page['lines'][1]['top'] = 35
    cleaned, _ = clean_pdf_pages(source)
    assert all(lines[0]['text'] == 'PLEX Python course' for lines in cleaned)


def test_numeric_footer_must_follow_printed_page_order():
    source = pages()
    for page in source:
        page['lines'][-1]['text'] = '42'
    cleaned, _ = clean_pdf_pages(source)
    assert all(lines[-1]['text'] == '42' for lines in cleaned)


def write_pdf(path: Path, page_specs):
    """Small actual PDF fixture, built locally without reportlab or network access."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>']
    page_ids = []
    for spec in page_specs:
        page_id = len(objects) + 1
        page_ids.append(page_id)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 800] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {page_id + 1} 0 R >>'.encode())
        commands = []
        for text, x, y, font, size in spec:
            safe = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'BT /{font} {size} Tf {x} {y} Td ({safe}) Tj ET')
        stream = '\n'.join(commands).encode('ascii')
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
    objects[1] = f'<< /Type /Pages /Count {len(page_ids)} /Kids [{" ".join(str(i) + " 0 R" for i in page_ids)}] >>'.encode()
    content, offsets = b'%PDF-1.4\n', [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(content)
    content += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    content += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    content += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    path.write_bytes(content)


def course_pdf(path):
    specs = []
    for i in range(1, 4):
        specs.append([
            ('PLEX Python course', 72, 775, 'F1', 10),
            (f'Loops - lesson {i}', 72, 700, 'F3', 16),
            ('Check the loop boundary and the stopping condition.', 72, 665, 'F1', 12),
            ('def total(values):', 72, 625, 'F2', 12),
            ('result = 0', 101, 612, 'F2', 12),
            ('for value in values:', 101, 599, 'F2', 12),
            ('result += value', 130, 586, 'F2', 12),
            ('return result', 101, 573, 'F2', 12),
            (f'Page {i} of 3', 280, 16, 'F1', 10),
        ])
    write_pdf(path, specs)


def test_actual_pdf_retains_code_indentation_headings_and_page_numbers(tmp_path):
    pytest.importorskip('pdfplumber')
    path = tmp_path / 'course.pdf'
    course_pdf(path)
    parsed = ParserService.parse_pdf(path, 'Python')
    assert parsed.meta['cleanup']['removed_line_count'] == 6
    assert [block.page for block in parsed.blocks] == [1, 2, 3]
    assert 'Page 1 of 3' not in parsed.markdown and 'PLEX Python course' not in parsed.markdown
    assert '## Loops - lesson 1' in parsed.markdown
    assert 'def total(values):\n    result = 0\n    for value in values:\n        result += value\n    return result' in parsed.markdown
    chunks = ChunkService([]).chunk_markdown(parsed.markdown, title='Python')
    assert {chunk.source_page for chunk in chunks} == {1, 2, 3}
    assert all('Loops - lesson' in chunk.title for chunk in chunks)
    assert sum('def total(values)' in chunk.content for chunk in chunks) == 3


def test_page_boundaries_do_not_merge_small_chunks_or_lose_heading():
    text = '<!-- page:1 -->\n## 循环边界\n`document_id: python-while-extra`\n' + '第一页的课程解释需要保留原始引用位置。' * 3
    text += '\n<!-- page:3 -->\n' + '第三页继续这一章节，不能被标注成第一页。' * 3
    chunks = ChunkService([]).chunk_markdown(text, title='课程')
    assert len(chunks) == 2
    assert [chunk.source_page for chunk in chunks] == [1, 3]
    assert chunks[0].title == chunks[1].title == '循环边界'
    assert chunks[1].meta['section_document_id'] == 'python-while-extra'


def test_short_page_continuation_is_retained_instead_of_discarded():
    text = '<!-- page:1 -->\n## 数值\n第一页的解释包含足够长的课程内容和边界条件。\n<!-- page:2 -->\n结果：0'
    chunks = ChunkService([]).chunk_markdown(text, title='课程')
    assert [chunk.source_page for chunk in chunks] == [1, 2]
    assert chunks[1].content == '结果：0'


def test_code_page_comment_is_literal_and_markdown_indentation_is_untouched():
    code = '```python\ndef f():\n\tif True:\n\t\treturn "a  b"\n<!-- page:3 -->\n```'
    parsed = ParserService.parse_text('## 示例\n\n' + code, '代码')
    chunks = ChunkService([]).chunk_markdown(parsed.markdown, title='代码')
    assert code in chunks[0].content
    assert chunks[0].source_page is None


def test_literal_fences_in_pdf_code_do_not_break_chunks_or_reclassify_answers():
    lines = [row(line, 100 + i * 15, font='Courier') for i, line in enumerate([
        'example = """', '```', '## 答案', '- 基础题：这仍是字符串中的内容', '```', '"""',
    ])]
    markdown = lines_to_markdown(lines)
    assert markdown.startswith('````\n')
    chunks = ChunkService([]).chunk_markdown('## 示例\n' + markdown, title='代码')
    assert len(chunks) == 1
    assert chunks[0].knowledge_type == 'example'
    assert chunks[0].content == markdown


def test_visible_empty_rows_inside_code_are_kept():
    lines = [row('text = """hello', 100, font='Courier'),
             row('world"""', 126, font='Courier')]
    assert 'hello\n\nworld' in lines_to_markdown(lines)


def test_blank_physical_page_keeps_later_pdf_source_number(tmp_path):
    pytest.importorskip('pdfplumber')
    path = tmp_path / 'blank-page.pdf'
    body = [('The course material continues on the third physical page.', 72, 650, 'F1', 12)]
    write_pdf(path, [body, [], body])
    parsed = ParserService.parse_pdf(path, 'Course')
    assert [block.page for block in parsed.blocks] == [1, 3]
    chunks = ChunkService([]).chunk_markdown(parsed.markdown, title='Course')
    assert [chunk.source_page for chunk in chunks] == [1, 3]


def test_fallback_keeps_original_text_and_explicitly_skips_margin_cleanup(tmp_path, monkeypatch):
    pytest.importorskip('pypdfium2')
    path = tmp_path / 'fallback.pdf'
    course_pdf(path)
    monkeypatch.setitem(sys.modules, 'pdfplumber', None)
    parsed = ParserService.parse_pdf(path, 'Python')
    assert parsed.meta['cleanup']['policy'] == 'retained_without_geometry'
    assert 'PLEX Python course' in parsed.markdown
    assert [block.page for block in parsed.blocks] == [1, 2, 3]


def test_no_text_is_an_explicit_parser_error(tmp_path):
    pytest.importorskip('pdfplumber')
    path = tmp_path / 'empty.pdf'
    write_pdf(path, [[]])
    with pytest.raises(ParserError, match='OCR'):
        ParserService.parse_pdf(path, 'Empty')


def test_pdf_index_and_reindex_preserve_pages_versions_and_cleanup_audit(app, tmp_path):
    pytest.importorskip('pdfplumber')
    path = tmp_path / 'index-course.pdf'
    course_pdf(path)
    with app.app_context():
        doc = KnowledgeDocument(title='Loops', file_type='pdf', file_path=str(path),
            status='PENDING', source='upload', uploaded_by=app.config['TEST_TEACHER'],
            meta={'concept_hints': ['loop-for']})
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
        for expected_version in (1, 2):
            job = IndexService.start_index(doc_id, user_id=app.config['TEST_TEACHER'], sync=True)
            assert job.status == 'READY', job.error_message
            doc = db.session.get(KnowledgeDocument, doc_id)
            assert doc.version == expected_version
            assert doc.meta['concept_hints'] == ['loop-for']
            assert doc.meta['parsing']['version'] == expected_version
            assert doc.meta['parsing']['cleanup']['removed_line_count'] == 6
            chunks = KnowledgeChunk.query.filter_by(document_id=doc_id).all()
            assert {chunk.source_page for chunk in chunks} == {1, 2, 3}
            assert all(chunk.version == expected_version for chunk in chunks)
            assert all('    return result' in chunk.content for chunk in chunks)
            assert all('Loops - lesson' in chunk.chapter for chunk in chunks)
        with patch.object(ParserService, 'parse_path', side_effect=ParserError('fixture failed')):
            job = IndexService.start_index(doc_id, user_id=app.config['TEST_TEACHER'], sync=True)
        assert job.status == 'FAILED'
        doc = db.session.get(KnowledgeDocument, doc_id)
        assert doc.meta['parsing']['version'] == 2
        assert {c.version for c in KnowledgeChunk.query.filter_by(document_id=doc_id)} == {2}
