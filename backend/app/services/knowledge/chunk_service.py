# -*- coding: utf-8 -*-
"""教育语义切分（Semantic Chunking）+ Chunk metadata + 概念映射。

切分原则：
- 按标题层级（#/##/###）→ 教学语义块（概念讲解 / 正例 / 反例与误区 / 练习 / 解析 / 小结 / 拓展 / 教师备注）；
- 代码块永不被切开；过长小节按段落边界聚合，短段落合并；
- 练习与答案分离为不同 knowledge_type（练习场景可过滤 solution，防止泄题）；
- 概念映射：显式 ``document_id`` 契约 > 反引号节点 id > 概念词典词法匹配。
禁止固定长度暴力切块。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.data.knowledge_node_registry import KNOWLEDGE_NODE_REGISTRY, resolve_node_id

from .settings import retrieval_config
from .text_utils import estimate_tokens, normalize_text, tokenize

_HEADING = re.compile(r'^(#{1,4})\s+(.+?)\s*$')
_PAGE_MARK = re.compile(r'^<!--\s*page:(\d+)\s*-->$')
_FENCE = re.compile(r'^```')
_DOC_ID = re.compile(r'`document_id:\s*([^`\s]+)\s*`')
_BACKTICK_ID = re.compile(r'`([a-z][a-z0-9]+(?:-[a-z0-9]+)+)`')
_NUMBERED_HEADING = re.compile(r'^\d+[\.、]\s*')

_TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('solution', ('答案', '解析', '解答', '参考实现', 'solution', 'answer')),
    ('exercise', ('练习', '习题', '题目', '基础题', '进阶题', 'exercise', 'practice', 'quiz')),
    ('misconception', ('反例', '易错', '误区', '常见错误', '错因', '坑', 'misconception', 'pitfall', 'mistake')),
    ('example', ('正例', '示例', '例子', '案例', '演示', 'example', 'demo')),
    ('summary', ('小结', '总结', '回顾', '要点', 'summary', 'recap')),
    ('extension', ('拓展', '延伸', '进阶阅读', '相关知识点', '扩展', 'extension', 'further')),
    ('teacher_note', ('教师', '备注', '教学提示', '授课', 'teacher note', 'teaching tip')),
)

_SOLUTION_LINE = re.compile(r'^-\s*(进阶)?答案要点[：:]')
_EXERCISE_LINE = re.compile(r'^-\s*(基础题|进阶题)[：:]')
_FIELD_LINE = re.compile(r'^-\s*(概念|正例|反例|常见错误|基础题|进阶题|来源|前置知识点|后续知识点)[：:]')
_FIELD_TO_TYPE = {
    '概念': 'concept_explanation',
    '来源': 'concept_explanation',
    '正例': 'example',
    '反例': 'misconception',
    '常见错误': 'misconception',
    '基础题': 'exercise',
    '进阶题': 'exercise',
    '前置知识点': 'extension',
    '后续知识点': 'extension',
}

_DOC_ID_TO_KG = {e.document_id: e.kg_id for e in KNOWLEDGE_NODE_REGISTRY if e.document_id}


@dataclass
class ChunkDraft:
    content: str
    title: str
    knowledge_type: str = 'concept_explanation'
    concept_ids: list[str] = field(default_factory=list)
    primary_concept_id: str | None = None
    difficulty: int = 2
    source_page: int | None = None
    sequence: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.content)


@dataclass
class _Section:
    level: int
    heading: str
    path: list[str]
    lines: list[str] = field(default_factory=list)
    page: int | None = None
    document_id: str | None = None


class ChunkService:
    def __init__(self, lexicon: list[dict[str, Any]] | None = None):
        cfg = retrieval_config().get('index', {})
        self.max_chars = int(cfg.get('max_chunk_chars', 1400))
        self.min_chars = int(cfg.get('min_chunk_chars', 120))
        self.merge_short = int(cfg.get('merge_short_paragraph_chars', 260))
        self._lexicon = self._prepare_lexicon(lexicon or [])

    # ------------------------------------------------------------------ public
    def chunk_markdown(
        self,
        markdown: str,
        *,
        title: str,
        default_difficulty: int = 2,
        concept_hints: list[str] | None = None,
    ) -> list[ChunkDraft]:
        sections = self._split_sections(markdown, title)
        drafts: list[ChunkDraft] = []
        inherited_doc_concept: str | None = None
        inherited_level = 0
        for section in sections:
            if section.document_id and section.document_id in _DOC_ID_TO_KG:
                inherited_doc_concept = _DOC_ID_TO_KG[section.document_id]
                inherited_level = section.level
            elif inherited_doc_concept and section.level <= inherited_level:
                # 进入了新的同级/上级小节，不再继承旧的 document_id
                inherited_doc_concept = None
            body = '\n'.join(section.lines).strip()
            if not body:
                continue
            base_type = self._classify(section.heading, body)
            pieces = self._split_by_type(body, base_type)
            for knowledge_type, text in pieces:
                for part in self._pack(text):
                    if len(part.strip()) < 20:
                        continue
                    draft = ChunkDraft(
                        content=part.strip(),
                        title=' › '.join(p for p in section.path if p) or title,
                        knowledge_type=knowledge_type,
                        source_page=section.page,
                        meta={'heading_path': list(section.path), 'section_document_id': section.document_id},
                    )
                    self._map_concepts(draft, inherited_doc_concept, concept_hints or [])
                    draft.difficulty = self._difficulty(draft, section.heading, default_difficulty)
                    drafts.append(draft)
        drafts = self._merge_tiny(drafts)
        for index, draft in enumerate(drafts):
            draft.sequence = index
        return drafts

    # ------------------------------------------------------------------ sectioning
    def _split_sections(self, markdown: str, title: str) -> list[_Section]:
        sections: list[_Section] = []
        path: list[str] = []
        current = _Section(level=0, heading=title, path=[])
        in_fence = False
        page: int | None = None
        for raw in (markdown or '').split('\n'):
            line = raw.rstrip()
            if _FENCE.match(line.strip()):
                in_fence = not in_fence
                current.lines.append(line)
                continue
            if in_fence:
                current.lines.append(line)
                continue
            page_match = _PAGE_MARK.match(line.strip())
            if page_match:
                page = int(page_match.group(1))
                if not ''.join(current.lines).strip():
                    current.page = page
                continue
            heading = _HEADING.match(line)
            if heading:
                sections.append(current)
                level = len(heading.group(1))
                text = _NUMBERED_HEADING.sub('', heading.group(2).strip())
                path = path[: level - 1] + [text]
                current = _Section(level=level, heading=text, path=list(path), page=page)
                continue
            doc_match = _DOC_ID.search(line)
            if doc_match and not current.document_id:
                current.document_id = doc_match.group(1)
                continue  # 契约行本身不进入正文
            current.lines.append(line)
        sections.append(current)
        # 顶层文档标题（# xxx）若只有一段导语，仍保留为 summary 类型的概览块
        return [s for s in sections if ''.join(s.lines).strip()]

    # ------------------------------------------------------------------ classification
    @staticmethod
    def _classify(heading: str, body: str) -> str:
        head = normalize_text(heading).lower()
        for knowledge_type, keywords in _TYPE_RULES:
            if any(k in head for k in keywords):
                return knowledge_type
        # 无标题线索时看正文开头的字段标记
        first = body.strip().splitlines()[0] if body.strip() else ''
        for knowledge_type, keywords in _TYPE_RULES:
            if first.startswith('- ') and any(first[2:].startswith(k) for k in keywords):
                return knowledge_type
        return 'concept_explanation'

    @staticmethod
    def _split_by_type(body: str, base_type: str) -> list[tuple[str, str]]:
        """练习小节把题目与答案要点拆开；紧凑型知识点小节按 ``- 字段：`` 行拆成不同教学类型；其他类型原样返回。"""
        if base_type == 'concept_explanation':
            compact = ChunkService._split_field_lines(body)
            if compact:
                return compact
        if base_type != 'exercise':
            return [(base_type, body)]
        exercise_lines: list[str] = []
        solution_lines: list[str] = []
        code_buffer: list[str] = []
        in_fence = False
        target = exercise_lines
        for line in body.splitlines():
            if _FENCE.match(line.strip()):
                in_fence = not in_fence
                target.append(line)
                continue
            if in_fence:
                target.append(line)
                continue
            if _SOLUTION_LINE.match(line.strip()):
                target = solution_lines
            elif _EXERCISE_LINE.match(line.strip()):
                target = exercise_lines
            target.append(line)
        pieces: list[tuple[str, str]] = []
        if ''.join(exercise_lines).strip():
            pieces.append(('exercise', '\n'.join(exercise_lines).strip()))
        if ''.join(solution_lines).strip():
            pieces.append(('solution', '\n'.join(solution_lines).strip()))
        del code_buffer
        return pieces or [(base_type, body)]

    @staticmethod
    def _split_field_lines(body: str) -> list[tuple[str, str]] | None:
        """紧凑小节（概念/正例/反例/常见错误/基础题/进阶题 均为单行字段）→ 按教学类型拆块。

        每个子块都带上小节导语的首句作为语境前缀，避免脱离上下文。
        """
        lines = body.splitlines()
        fields: dict[str, list[str]] = {}
        intro: list[str] = []
        in_fence = False
        for line in lines:
            if _FENCE.match(line.strip()):
                in_fence = not in_fence
            if in_fence or not _FIELD_LINE.match(line.strip()):
                intro.append(line)
                continue
            key = _FIELD_LINE.match(line.strip()).group(1)
            fields.setdefault(_FIELD_TO_TYPE.get(key, 'concept_explanation'), []).append(line.strip())
        if len(fields) < 3 or '```' in body:
            return None
        intro_text = '\n'.join(intro).strip()
        context = intro_text.split('。')[0].strip()
        context = (context + '。') if context and len(context) < 160 else ''
        pieces: list[tuple[str, str]] = []
        concept_lines = fields.pop('concept_explanation', [])
        concept_block = (intro_text + ('\n\n' if intro_text and concept_lines else '') + '\n'.join(concept_lines)).strip()
        if concept_block:
            pieces.append(('concept_explanation', concept_block))
        for knowledge_type in ('example', 'misconception', 'exercise', 'extension'):
            if knowledge_type in fields:
                text = '\n'.join(fields[knowledge_type])
                pieces.append((knowledge_type, (context + '\n' + text).strip() if context else text))
        return pieces or None

    # ------------------------------------------------------------------ packing
    def _pack(self, text: str) -> list[str]:
        """按段落聚合到 max_chars，代码块作为不可分割单元附着于前一段。"""
        units = self._paragraph_units(text)
        chunks: list[str] = []
        buffer: list[str] = []
        size = 0
        for unit in units:
            unit_len = len(unit)
            if buffer and size + unit_len + 2 > self.max_chars and size >= self.min_chars:
                chunks.append('\n\n'.join(buffer))
                buffer, size = [], 0
            buffer.append(unit)
            size += unit_len + 2
        if buffer:
            chunks.append('\n\n'.join(buffer))
        # 单个超长段落（无空行）按句子边界二次切分
        out: list[str] = []
        for chunk in chunks:
            if len(chunk) <= self.max_chars * 1.5 or '```' in chunk:
                out.append(chunk)
            else:
                out.extend(self._split_sentences(chunk))
        return out

    @staticmethod
    def _paragraph_units(text: str) -> list[str]:
        units: list[str] = []
        buffer: list[str] = []
        in_fence = False
        for line in text.splitlines():
            if _FENCE.match(line.strip()):
                if not in_fence:
                    if buffer and ''.join(buffer).strip():
                        units.append('\n'.join(buffer).strip())
                    buffer = [line]
                    in_fence = True
                else:
                    buffer.append(line)
                    code = '\n'.join(buffer)
                    # 代码块附着到前一个文字段落，保持“说明 + 代码”成对
                    if units and not units[-1].startswith('```') and len(units[-1]) + len(code) < 1800:
                        units[-1] = units[-1] + '\n\n' + code
                    else:
                        units.append(code)
                    buffer = []
                    in_fence = False
                continue
            if in_fence:
                buffer.append(line)
                continue
            if not line.strip():
                if buffer and ''.join(buffer).strip():
                    units.append('\n'.join(buffer).strip())
                buffer = []
            else:
                buffer.append(line)
        if buffer and ''.join(buffer).strip():
            units.append('\n'.join(buffer).strip())
        return units

    def _split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[。！？!?；;])\s*', text)
        out: list[str] = []
        buffer = ''
        for sentence in sentences:
            if not sentence:
                continue
            if buffer and len(buffer) + len(sentence) > self.max_chars:
                out.append(buffer)
                buffer = sentence
            else:
                buffer += sentence
        if buffer:
            out.append(buffer)
        return out

    def _merge_tiny(self, drafts: list[ChunkDraft]) -> list[ChunkDraft]:
        """相邻、同类型、同标题的过短块合并，避免产生碎片。"""
        merged: list[ChunkDraft] = []
        for draft in drafts:
            if (
                merged
                and len(draft.content) < self.merge_short
                and merged[-1].knowledge_type == draft.knowledge_type
                and merged[-1].title == draft.title
                and len(merged[-1].content) + len(draft.content) < self.max_chars
            ):
                merged[-1].content += '\n\n' + draft.content
                for cid in draft.concept_ids:
                    if cid not in merged[-1].concept_ids:
                        merged[-1].concept_ids.append(cid)
                continue
            merged.append(draft)
        return merged

    # ------------------------------------------------------------------ concept mapping
    @staticmethod
    def _prepare_lexicon(lexicon: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared = []
        for item in lexicon:
            aliases = {normalize_text(a).lower() for a in [item.get('name', '')] + list(item.get('aliases') or []) if a}
            aliases = {a for a in aliases if len(a) >= 2}
            prepared.append(
                {
                    'concept_id': item['concept_id'],
                    'aliases': aliases,
                    'tokens': set(tokenize(' '.join(aliases))),
                    'difficulty': int(item.get('difficulty') or 2),
                }
            )
        return prepared

    def _map_concepts(self, draft: ChunkDraft, inherited: str | None, hints: list[str]) -> None:
        scores: dict[str, float] = {}
        if inherited:
            scores[inherited] = 3.0
        for hint in hints:
            cid = resolve_node_id(hint) or hint
            if cid:
                scores[cid] = scores.get(cid, 0) + 2.0
        text = f'{draft.title}\n{draft.content}'
        for match in _BACKTICK_ID.findall(text):
            cid = resolve_node_id(match)
            if cid:
                scores[cid] = scores.get(cid, 0) + 1.5
        lowered = normalize_text(text).lower()
        for item in self._lexicon:
            hit = 0.0
            for alias in item['aliases']:
                if alias and alias in lowered:
                    hit += 1.0 if len(alias) >= 4 else 0.6
            if hit:
                scores[item['concept_id']] = scores.get(item['concept_id'], 0) + min(hit, 2.5)
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        draft.concept_ids = [cid for cid, score in ranked if score >= 1.0][:4]
        draft.primary_concept_id = inherited or (draft.concept_ids[0] if draft.concept_ids else None)
        if draft.primary_concept_id and draft.primary_concept_id not in draft.concept_ids:
            draft.concept_ids.insert(0, draft.primary_concept_id)
        draft.meta['concept_scores'] = {cid: round(score, 2) for cid, score in ranked[:6]}

    def _difficulty(self, draft: ChunkDraft, heading: str, default: int) -> int:
        base = default
        if draft.primary_concept_id:
            for item in self._lexicon:
                if item['concept_id'] == draft.primary_concept_id:
                    base = item['difficulty']
                    break
        head = f'{heading} {draft.content[:80]}'
        if '进阶' in head or '拓展' in head or draft.knowledge_type == 'extension':
            base += 1
        elif '基础' in head or '入门' in head:
            base = min(base, 2)
        return max(1, min(5, base))
