# -*- coding: utf-8 -*-
"""Append structured micro-lessons for registry nodes missing from the RAG corpus.

The canonical hand-written lessons remain untouched. This command only appends a
compact, reviewable section when its stable document_id is absent, so it is safe
to run repeatedly after curriculum-registry changes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data.course_knowledge import DOMAIN_SOURCE_FILES, KNOWLEDGE_ROOT  # noqa: E402
from app.data.knowledge_node_registry import KNOWLEDGE_DOMAINS, nodes_for_domain  # noqa: E402


DOMAIN_SOURCES = {
    'lang-basics': 'Python 3 官方教程“Python 解释器与非正式入门”、PEP 8、PEP 257。',
    'sequence': 'Python 3 官方教程“Using Python as a Calculator”及标准库文档。',
    'branch': 'Python 3 官方教程“More Control Flow Tools”。',
    'loop': 'Python 3 官方教程“for Statements”“The range() Function”。',
    'array': 'Python 3 官方教程“Data Structures”及 collections 标准库文档。',
    'string': 'Python 3 标准库 str、re、文本编码文档。',
    'function': 'Python 3 官方教程“Defining Functions”及 unittest 文档。',
    'search': 'Python 官方教程数据结构章节与课程组算法复杂度讲义。',
}


def section_text(index: int, entry) -> str:
    """Build a seven-field section accepted by the course knowledge contract."""
    return f'''\n\n## {index}. {entry.label}\n`document_id: {entry.document_id}`\n\n{entry.summary}。本知识点在 PLEX 中作为独立诊断、练习和路径重规划单元，学习后应能解释规则、写出最小程序，并用边界输入验证结果。\n\n- 概念：{entry.summary}；需要同时说清适用场景、输入输出和关键约束。\n- 正例：围绕“{entry.label}”先写一个最小可运行示例，再用正常值与边界值各运行一次，并说明每一步为何符合该知识点规则。\n- 反例：不检查前提就机械套用“{entry.label}”，或只验证一个样例便宣称程序正确；应通过最小反例定位错误并修正。\n- 常见错误：混淆相近语法、遗漏边界条件、修改了不应修改的状态，以及输出格式与题意不一致。\n- 基础题：用自己的话解释“{entry.label}”，并编写一个不超过 10 行的 Python 小程序展示其最常见用法。\n- 进阶题：为“{entry.label}”设计正常、边界、异常三类测试，对两种实现的正确性、可读性和复杂度作比较。\n- 来源：{DOMAIN_SOURCES[entry.domain_key]}\n'''


def sync() -> dict:
    appended = 0
    files_changed = 0
    for domain in KNOWLEDGE_DOMAINS:
        path = KNOWLEDGE_ROOT / DOMAIN_SOURCE_FILES[domain.key]
        text = path.read_text(encoding='utf-8')
        document_ids = set(re.findall(r'`document_id:\s*([^`\s]+)\s*`', text))
        section_count = len(re.findall(r'^##\s+\d+\.\s+', text, flags=re.MULTILINE))
        additions = []
        for entry in nodes_for_domain(domain.key):
            if entry.document_id not in document_ids:
                section_count += 1
                additions.append(section_text(section_count, entry))
                document_ids.add(entry.document_id)
                appended += 1
        if additions:
            text = text.rstrip() + ''.join(additions).rstrip() + '\n'
            files_changed += 1
        # Keep generated corpus diffs stable across Windows and Linux.
        path.write_text(text, encoding='utf-8', newline='\n')
    return {'sections_appended': appended, 'files_changed': files_changed}


if __name__ == '__main__':
    print(sync())
