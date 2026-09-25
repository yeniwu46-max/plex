# -*- coding: utf-8 -*-
"""文档解析：md / txt / pdf / docx / pptx / json → 统一的 ParsedDocument（带页码的文本块）。

第三方解析库均为可选依赖：缺失时抛出 ParserError，由索引任务记录为 FAILED 并提示安装。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .text_utils import normalize_text

SUPPORTED_TYPES = ('md', 'markdown', 'txt', 'pdf', 'docx', 'pptx', 'json')


class ParserError(RuntimeError):
    pass


@dataclass
class ParsedBlock:
    text: str
    page: int | None = None
    kind: str = 'text'  # text | heading | code


@dataclass
class ParsedDocument:
    title: str
    file_type: str
    blocks: list[ParsedBlock] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def markdown(self) -> str:
        """把块拼回 markdown 文本，供语义切分器统一处理；PDF/Word 的页码以注释形式嵌入。"""
        parts: list[str] = []
        last_page = None
        for block in self.blocks:
            if block.page is not None and block.page != last_page:
                parts.append(f'<!-- page:{block.page} -->')
                last_page = block.page
            if block.kind == 'heading':
                parts.append(f'## {block.text.strip()}')
            elif block.kind == 'code':
                parts.append(f'```\n{block.text}\n```')
            else:
                parts.append(block.text)
        return '\n\n'.join(parts)


def detect_file_type(file_name: str | None, fallback: str = 'txt') -> str:
    ext = (Path(file_name or '').suffix or '').lower().lstrip('.')
    if ext == 'markdown':
        ext = 'md'
    return ext if ext in SUPPORTED_TYPES else fallback


class ParserService:
    @staticmethod
    def parse_path(path: Path, file_type: str | None = None, title: str | None = None) -> ParsedDocument:
        path = Path(path)
        if not path.is_file():
            raise ParserError(f'文件不存在：{path.name}')
        file_type = (file_type or detect_file_type(path.name)).lower()
        title = title or path.stem
        if file_type in {'md', 'markdown', 'txt'}:
            return ParserService.parse_text(path.read_text(encoding='utf-8', errors='replace'), title, file_type)
        if file_type == 'json':
            return ParserService.parse_json(path.read_text(encoding='utf-8', errors='replace'), title)
        if file_type == 'pdf':
            return ParserService.parse_pdf(path, title)
        if file_type == 'docx':
            return ParserService.parse_docx(path, title)
        if file_type == 'pptx':
            return ParserService.parse_pptx(path, title)
        raise ParserError(f'暂不支持的文件类型：{file_type}')

    @staticmethod
    def parse_text(text: str, title: str, file_type: str = 'md') -> ParsedDocument:
        cleaned = _clean_text(text)
        if not cleaned.strip():
            raise ParserError('文档内容为空')
        doc = ParsedDocument(title=title, file_type='md' if file_type in {'md', 'markdown'} else 'txt')
        # 纯文本：按空行分段，保持顺序；markdown 原样交给切分器
        doc.blocks.append(ParsedBlock(text=cleaned))
        heading = re.search(r'^#\s+(.+)$', cleaned, flags=re.MULTILINE)
        if heading:
            doc.meta['heading_title'] = heading.group(1).strip()
        return doc

    @staticmethod
    def parse_json(text: str, title: str) -> ParsedDocument:
        """练习/错题 JSON：[{title, stem|question, answer|solution, analysis, concept_ids?, difficulty?}]。"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParserError(f'JSON 解析失败：{exc}') from exc
        items = data if isinstance(data, list) else data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            raise ParserError('JSON 需为题目数组或包含 items 数组')
        doc = ParsedDocument(title=title, file_type='json', meta={'item_count': len(items)})
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            head = str(item.get('title') or f'题目 {index}').strip()
            doc.blocks.append(ParsedBlock(text=head, kind='heading'))
            stem = str(item.get('stem') or item.get('question') or item.get('content') or '').strip()
            if stem:
                doc.blocks.append(ParsedBlock(text=f'### 题目\n\n{stem}'))
            answer = str(item.get('answer') or item.get('solution') or item.get('reference_answer') or '').strip()
            if answer:
                doc.blocks.append(ParsedBlock(text=f'### 解析\n\n{answer}'))
            analysis = str(item.get('analysis') or item.get('explanation') or '').strip()
            if analysis:
                doc.blocks.append(ParsedBlock(text=f'### 错因分析\n\n{analysis}'))
            tags = item.get('concept_ids') or item.get('concepts') or item.get('knowledge_keys')
            if tags:
                doc.blocks.append(ParsedBlock(text='- 相关知识点：' + '、'.join(f'`{t}`' for t in tags)))
        return doc

    @staticmethod
    def parse_pdf(path: Path, title: str) -> ParsedDocument:
        doc = ParsedDocument(title=title, file_type='pdf')
        try:
            import pdfplumber  # type: ignore
        except ImportError:
            pdfplumber = None
        if pdfplumber is not None:
            with pdfplumber.open(str(path)) as pdf:
                for number, page in enumerate(pdf.pages, 1):
                    text = _clean_text(page.extract_text() or '')
                    if text.strip():
                        doc.blocks.append(ParsedBlock(text=text, page=number))
            doc.meta['parser'] = 'pdfplumber'
        else:
            try:
                import pypdfium2 as pdfium  # type: ignore
            except ImportError as exc:
                raise ParserError('解析 PDF 需要安装 pdfplumber 或 pypdfium2') from exc
            pdf = pdfium.PdfDocument(str(path))
            for number in range(len(pdf)):
                page = pdf[number]
                text = _clean_text(page.get_textpage().get_text_range() or '')
                if text.strip():
                    doc.blocks.append(ParsedBlock(text=text, page=number + 1))
            doc.meta['parser'] = 'pypdfium2'
        if not doc.blocks:
            raise ParserError('PDF 未提取到文本（可能是扫描件，需要 OCR）')
        return doc

    @staticmethod
    def parse_docx(path: Path, title: str) -> ParsedDocument:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise ParserError('解析 Word 需要安装 python-docx') from exc
        document = docx.Document(str(path))
        doc = ParsedDocument(title=title, file_type='docx', meta={'parser': 'python-docx'})
        for paragraph in document.paragraphs:
            text = _clean_text(paragraph.text or '')
            if not text.strip():
                continue
            style = (paragraph.style.name or '').lower() if paragraph.style is not None else ''
            if style.startswith('heading') or style.startswith('标题'):
                doc.blocks.append(ParsedBlock(text=text, kind='heading'))
            else:
                doc.blocks.append(ParsedBlock(text=text))
        for table in document.tables:
            rows = []
            for row in table.rows:
                cells = [normalize_text(c.text) for c in row.cells]
                rows.append(' | '.join(cells))
            if rows:
                doc.blocks.append(ParsedBlock(text='\n'.join(rows)))
        if not doc.blocks:
            raise ParserError('Word 文档未提取到文本')
        return doc

    @staticmethod
    def parse_pptx(path: Path, title: str) -> ParsedDocument:
        try:
            from pptx import Presentation  # type: ignore
        except ImportError as exc:
            raise ParserError('解析 PPT 需要安装 python-pptx') from exc
        presentation = Presentation(str(path))
        doc = ParsedDocument(title=title, file_type='pptx', meta={'parser': 'python-pptx'})
        for number, slide in enumerate(presentation.slides, 1):
            texts: list[str] = []
            slide_title = None
            for shape in slide.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                text = _clean_text(shape.text_frame.text or '')
                if not text.strip():
                    continue
                if slide_title is None and getattr(shape, 'name', '').lower().startswith('title'):
                    slide_title = text
                else:
                    texts.append(text)
            if slide_title:
                doc.blocks.append(ParsedBlock(text=slide_title, page=number, kind='heading'))
            if texts:
                doc.blocks.append(ParsedBlock(text='\n'.join(texts), page=number))
        if not doc.blocks:
            raise ParserError('PPT 未提取到文本')
        return doc


def _clean_text(text: str) -> str:
    """基础清洗：统一换行、去除控制字符与多余空行，保留代码块缩进。"""
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip('\n')
