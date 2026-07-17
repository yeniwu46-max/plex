"""Step 1: knowledge correctness checks."""
from __future__ import annotations

import re
from typing import Any

from app.data.course_knowledge import catalog_points, knowledge_section
from app.services.pedagogical_resource import build_knowledge_node
from app.services.rag_service import RagService

from .schema import CheckItem, StepResult

_FANTASY_IMPORTS = re.compile(
    r'^\s*(?:from|import)\s+(django|flask|numpy|pandas|requests|tensorflow|torch)\b',
    re.MULTILINE | re.IGNORECASE,
)
_STD_COMPLEXITY = re.compile(r'^O\((1|n|log n|n log n|n\^2)\)$', re.IGNORECASE)


def _score_from_checks(checks: list[CheckItem]) -> int:
    if not checks:
        return 100
    score = 100
    for check in checks:
        if check.level == 'FAIL':
            score -= 25
        elif check.level == 'WARNING':
            score -= 8
    return max(0, min(100, score))


def check_knowledge(
    bundle: dict,
    knowledge_key: str,
    *,
    confidence: float = 0.9,
    citations: list[dict] | None = None,
) -> StepResult:
    checks: list[CheckItem] = []
    label = catalog_points().get(knowledge_key, knowledge_key)
    kb = knowledge_section(knowledge_key)
    node = build_knowledge_node(knowledge_key)
    explain = str(bundle.get('explain') or '')

    for block in bundle.get('code') or []:
        if not isinstance(block, dict):
            continue
        src = str(block.get('source') or '')
        try:
            compile(src, '<bundle_code>', 'exec')
            checks.append(CheckItem('syntax', 'Python 语法', 'PASS', '代码块可编译'))
        except SyntaxError as exc:
            checks.append(CheckItem('syntax', 'Python 语法', 'FAIL', str(exc)))
        if _FANTASY_IMPORTS.search(src):
            checks.append(CheckItem('fantasy_api', 'API 范围', 'FAIL', '使用了课程范围外的第三方库'))
        complexity = str(block.get('complexity') or '').strip()
        if complexity and not _STD_COMPLEXITY.match(complexity):
            checks.append(CheckItem('complexity', '复杂度标注', 'WARNING', f'复杂度标注非常规：{complexity}'))

    concept = str(kb.get('concept') or '')
    if concept and concept[:20] in explain:
        checks.append(CheckItem('concept_align', '概念一致性', 'PASS', '讲解与课程知识库概念一致'))
    elif concept:
        overlap = any(token in explain for token in concept.split('，')[:2] if len(token) >= 2)
        checks.append(CheckItem(
            'concept_align',
            '概念一致性',
            'PASS' if overlap else 'WARNING',
            '讲解未明显引用课程概念，建议对照知识库',
        ))

    good = str(kb.get('good_example') or '')
    if good and good.strip()[:30] in explain:
        checks.append(CheckItem('example_align', '示例一致性', 'PASS', '正例与知识库一致'))
    elif good:
        checks.append(CheckItem('example_align', '示例一致性', 'WARNING', '未检测到知识库正例片段'))

    rag_context = ''
    try:
        rag_context = RagService.build_context(f'{label} {concept[:80]}')
    except Exception:
        rag_context = ''
    if rag_context:
        snippet = rag_context[:80]
        if snippet and snippet[:30] in explain:
            checks.append(CheckItem('rag_consistency', 'RAG 一致性', 'PASS', '与检索片段一致'))
        else:
            checks.append(CheckItem('rag_consistency', 'RAG 一致性', 'WARNING', '与 RAG 检索片段弱相关'))
    else:
        checks.append(CheckItem('rag_consistency', 'RAG 一致性', 'WARNING', 'RAG 未返回上下文，使用知识库对照'))

    prereqs = node.get('prerequisites') or []
    if prereqs:
        checks.append(CheckItem(
            'prerequisites',
            '前置知识',
            'PASS',
            f'课程建议前置：{"、".join(prereqs)}',
        ))

    if 'python 2' in explain.lower() or 'print ' in explain and 'print(' not in explain:
        checks.append(CheckItem('version', 'Python 版本', 'WARNING', '可能存在 Python 2 写法'))

    if confidence < 0.8:
        checks.append(CheckItem('confidence', '生成置信度', 'WARNING', f'置信度偏低：{confidence:.0%}'))

    if citations is not None and not citations:
        checks.append(CheckItem('citations', '引用', 'WARNING', '缺少课程引用'))

    score = _score_from_checks(checks)
    summary = '知识正确性检查通过' if score >= 80 and not any(c.level == 'FAIL' for c in checks) else '存在知识或 API 风险'
    return StepResult(step=1, name='知识正确性', checks=checks, score=score, summary=summary)
