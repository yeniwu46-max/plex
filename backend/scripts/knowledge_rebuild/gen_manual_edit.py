# -*- coding: utf-8 -*-
"""从 MySQL problems 表生成 MANUAL_EDIT.md 人工修改清单。"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app  # noqa: E402
from app.data.knowledge_node_registry import (  # noqa: E402
    KNOWLEDGE_DOMAINS,
    get_entry,
    nodes_for_domain,
)
from app.models import Problem  # noqa: E402

OUT = Path(__file__).resolve().parent / 'output' / 'MANUAL_EDIT.md'


def _safe(text: str | None, limit: int = 50) -> str:
    return (text or '').replace('|', '/').replace('\n', ' ').strip()[:limit]


def main() -> None:
    app = create_app()
    with app.app_context():
        active = (
            Problem.query.filter(Problem.is_active.is_(True))
            .order_by(Problem.kg_node_id, Problem.id)
            .all()
        )
        review = [p for p in active if p.needs_review]
        by_node = Counter(p.kg_node_id for p in active)
        review_by_node = Counter(p.kg_node_id for p in review)
        by_note = Counter((p.review_note or '（无备注）') for p in review)
        by_source = Counter(p.source_kind or 'unknown' for p in review)

        lines: list[str] = []
        lines.append('# 题库人工修改清单（MANUAL_EDIT）')
        lines.append('')
        lines.append(
            '> 生成时间：2026-07-30。以下条目在 MySQL `problems` 表中 '
            '`needs_review = 1`，建议你在 SQL 或管理端逐条核对后改为 `0`。'
        )
        lines.append('')
        lines.append('## 一、总览')
        lines.append('')
        lines.append(
            f'- 活跃题目 **{len(active)}** 道，覆盖 **26** 个知识点节点（每节点 ≥ 4 道）'
        )
        lines.append(f'- 待人工审核 **{len(review)}** 道（`needs_review = 1`）')
        lines.append('')
        lines.append('### 按审核原因分布')
        lines.append('')
        lines.append('| 原因（review_note） | 条数 |')
        lines.append('| --- | ---: |')
        for note, cnt in by_note.most_common():
            lines.append(f'| {note} | {cnt} |')
        lines.append('')
        lines.append('### 按来源分布（待审）')
        lines.append('')
        lines.append('| source_kind | 条数 |')
        lines.append('| --- | ---: |')
        for sk, cnt in by_source.most_common():
            lines.append(f'| {sk} | {cnt} |')
        lines.append('')
        lines.append('## 二、建议优先修改的 SQL 字段')
        lines.append('')
        lines.append('人工改题时最常动这些列：')
        lines.append('')
        lines.append('| 字段 | 说明 |')
        lines.append('| --- | --- |')
        lines.append('| `title_cn` / `description_cn` | 中文题干与题面描述 |')
        lines.append('| `input_format_cn` / `output_format_cn` | 输入输出格式说明 |')
        lines.append('| `samples_json` | 样例输入输出（JSON 数组） |')
        lines.append('| `reference_answer` | 编程题参考答案 |')
        lines.append('| `test_cases_json` | 隐藏测试点 |')
        lines.append('| `kg_node_id` / `domain_key` | 知识点归属（AI 归类有误时改） |')
        lines.append('| `options_json` / `correct_option` | 选择题选项与正确答案 |')
        lines.append(
            '| `needs_review` / `review_note` | 改完后设 `needs_review=0`，可清空 `review_note` |'
        )
        lines.append('')
        lines.append('## 三、批量查询 SQL')
        lines.append('')
        lines.append('```sql')
        lines.append('-- 全部待审题目')
        lines.append(
            'SELECT id, problem_no, kg_node_id, domain_key, question_type, '
            'source_kind, review_note, LEFT(title_cn, 60) AS title'
        )
        lines.append(
            'FROM problems WHERE is_active = 1 AND needs_review = 1 '
            'ORDER BY kg_node_id, id;'
        )
        lines.append('')
        lines.append('-- 仅 AI 新生成（样例已跑通，但措辞/难度需核对）')
        lines.append(
            "SELECT id, kg_node_id, title_cn, review_note FROM problems "
            "WHERE needs_review=1 AND source_kind='ai_generated';"
        )
        lines.append('')
        lines.append('-- 仅 AI 归类（归属可能不准）')
        lines.append(
            "SELECT id, kg_node_id, title_cn, review_note FROM problems "
            "WHERE needs_review=1 AND review_note LIKE '%AI 判定%';"
        )
        lines.append('```')
        lines.append('')
        lines.append('## 四、各节点题量（便于查漏）')
        lines.append('')
        lines.append('| 星域 | 节点 id | 节点名 | 题量 | 其中待审 |')
        lines.append('| --- | --- | --- | ---: | ---: |')
        for domain in KNOWLEDGE_DOMAINS:
            for entry in nodes_for_domain(domain.key):
                nid = entry.kg_id
                lines.append(
                    f'| {domain.title} | `{nid}` | {entry.label} | '
                    f'{by_node.get(nid, 0)} | {review_by_node.get(nid, 0)} |'
                )
        lines.append('')
        lines.append('## 五、逐条待审清单')
        lines.append('')
        grouped: dict[str, list] = defaultdict(list)
        for p in review:
            grouped[p.kg_node_id or 'unknown'].append(p)
        for node_id in sorted(grouped.keys()):
            entry = get_entry(node_id) if node_id != 'unknown' else None
            label = entry.label if entry else node_id
            lines.append(f'### {label} (`{node_id}`)')
            lines.append('')
            lines.append('| id | problem_no | 题型 | 来源 | 备注 | 题干摘要 |')
            lines.append('| ---: | --- | --- | --- | --- | --- |')
            for p in grouped[node_id]:
                title = _safe(p.title_cn or p.title_en)
                note = _safe(p.review_note, 80)
                lines.append(
                    f'| {p.id} | {p.problem_no or "-"} | '
                    f'{p.question_type or "-"} | {p.source_kind or "-"} | '
                    f'{note} | {title} |'
                )
            lines.append('')
        lines.append('## 六、改完后的验收')
        lines.append('')
        lines.append('1. `UPDATE problems SET needs_review=0, review_note=NULL WHERE id=?;`')
        lines.append(
            '2. 重跑 `python scripts/knowledge_rebuild/smoke_api.py` '
            '确认 8 域 / 26 节点 / 每节点 ≥4 题'
        )
        lines.append('3. 前端走一遍：星轨 → 答题 → 试炼中心 → 知识图谱')
        lines.append('')

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text('\n'.join(lines), encoding='utf-8')
        print(f'Wrote {OUT} ({len(review)} review items, {len(active)} active)')


if __name__ == '__main__':
    main()
