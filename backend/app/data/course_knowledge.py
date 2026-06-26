"""Canonical course knowledge-source contract and integrity checks."""
from __future__ import annotations

import re
from pathlib import Path

from app.data.knowledge_catalog import KNOWLEDGE_UNIVERSE


BACKEND_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = BACKEND_ROOT / 'data' / 'rag_docs' / 'python-basics'
REQUIRED_SECTION_FIELDS = (
    '概念',
    '正例',
    '反例',
    '常见错误',
    '基础题',
    '进阶题',
    '来源',
)

COURSE_KNOWLEDGE_SOURCES = {
    'intro': ('python-stage1-program-structure', '01-python-intro.md'),
    'comment': ('python-stage1-comments', '01-python-intro.md'),
    'var': ('python-stage1-variables-types', '01-python-intro.md'),
    'io': ('python-stage1-input-output', '01-python-intro.md'),
    'ops': ('python-stage2-operators', '02-control-flow.md'),
    'cond': ('python-stage2-condition', '02-control-flow.md'),
    'loop': ('python-stage2-loop', '02-control-flow.md'),
    'range': ('python-stage2-range', '02-control-flow.md'),
    'str': ('python-stage3-string', '03-data-structures.md'),
    'list': ('python-stage3-list', '03-data-structures.md'),
    'dict': ('python-stage3-dict', '03-data-structures.md'),
    'func': ('python-stage3-function', '03-data-structures.md'),
    'file': ('python-stage4-file', '04-functions-practice.md'),
    'except': ('python-stage4-exception', '04-functions-practice.md'),
    'algo-sum': ('python-stage4-sum-statistics', '04-functions-practice.md'),
    'algo-search': ('python-stage4-linear-search', '04-functions-practice.md'),
}


def catalog_points() -> dict[str, str]:
    return {
        point['key']: point['label']
        for domain in KNOWLEDGE_UNIVERSE
        for point in domain['points']
    }


def document_ids() -> dict[str, str]:
    return {
        knowledge_key: source[0]
        for knowledge_key, source in COURSE_KNOWLEDGE_SOURCES.items()
    }


def _parse_sections(path: Path) -> list[dict]:
    text = path.read_text(encoding='utf-8')
    headings = list(re.finditer(r'^##\s+\d+\.\s+(.+?)\s*$', text, flags=re.MULTILINE))
    sections = []
    for index, heading in enumerate(headings):
        start = heading.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[start:end].strip()
        match = re.search(r'`document_id:\s*([^`\s]+)\s*`', body)
        sections.append({
            'title': heading.group(1).strip(),
            'document_id': match.group(1) if match else None,
            'body': body,
        })
    return sections


def validate_course_knowledge(root: Path | None = None) -> dict:
    root = Path(root) if root else KNOWLEDGE_ROOT
    points = catalog_points()
    errors: list[str] = []
    warnings: list[str] = []
    source_keys = set(COURSE_KNOWLEDGE_SOURCES)
    catalog_keys = set(points)

    missing_mappings = sorted(catalog_keys - source_keys)
    extra_mappings = sorted(source_keys - catalog_keys)
    if missing_mappings:
        errors.append(f'missing knowledge mappings: {missing_mappings}')
    if extra_mappings:
        errors.append(f'unknown knowledge mappings: {extra_mappings}')

    expected_ids = [item[0] for item in COURSE_KNOWLEDGE_SOURCES.values()]
    duplicate_expected_ids = sorted({
        item for item in expected_ids if expected_ids.count(item) > 1
    })
    if duplicate_expected_ids:
        errors.append(f'duplicate mapped document_ids: {duplicate_expected_ids}')

    parsed_by_id: dict[str, dict] = {}
    source_files = sorted({item[1] for item in COURSE_KNOWLEDGE_SOURCES.values()})
    missing_files = []
    for filename in source_files:
        path = root / filename
        if not path.is_file():
            missing_files.append(filename)
            continue
        for section in _parse_sections(path):
            document_id = section['document_id']
            if not document_id:
                errors.append(f'{filename}: section "{section["title"]}" has no document_id')
                continue
            if document_id in parsed_by_id:
                errors.append(f'duplicate source document_id: {document_id}')
                continue
            parsed_by_id[document_id] = {**section, 'source_file': filename}
    if missing_files:
        errors.append(f'missing source files: {missing_files}')

    rows = []
    for knowledge_key, label in points.items():
        mapping = COURSE_KNOWLEDGE_SOURCES.get(knowledge_key)
        document_id, filename = mapping if mapping else (None, None)
        section = parsed_by_id.get(document_id)
        missing_fields = []
        if not section:
            errors.append(
                f'{knowledge_key}: mapped document_id {document_id!r} not found in {filename!r}'
            )
        else:
            if section['source_file'] != filename:
                errors.append(
                    f'{knowledge_key}: {document_id} found in {section["source_file"]}, '
                    f'expected {filename}'
                )
            missing_fields = [
                field
                for field in REQUIRED_SECTION_FIELDS
                if not re.search(rf'^-\s*{re.escape(field)}：\S+', section['body'], re.MULTILINE)
            ]
            if missing_fields:
                errors.append(f'{knowledge_key}: missing section fields {missing_fields}')
        rows.append({
            'knowledge_key': knowledge_key,
            'knowledge_label': label,
            'document_id': document_id,
            'source_file': filename,
            'section_title': section['title'] if section else None,
            'missing_fields': missing_fields,
            'valid': bool(section) and not missing_fields,
        })

    orphan_document_ids = sorted(set(parsed_by_id) - set(expected_ids))
    if orphan_document_ids:
        errors.append(f'orphan source document_ids: {orphan_document_ids}')

    valid_count = sum(1 for row in rows if row['valid'])
    total = len(rows)
    return {
        'status': 'passed' if not errors else 'failed',
        'root': str(root),
        'knowledge_point_count': total,
        'valid_knowledge_point_count': valid_count,
        'coverage_rate': round(valid_count / total, 4) if total else 0,
        'document_id_count': len(parsed_by_id),
        'source_file_count': len(source_files),
        'required_section_fields': list(REQUIRED_SECTION_FIELDS),
        'items': rows,
        'errors': errors,
        'warnings': warnings,
    }
