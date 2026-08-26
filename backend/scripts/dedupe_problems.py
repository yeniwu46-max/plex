# -*- coding: utf-8 -*-
"""软删除题库中的重复题：优先按中文标题撞名，其次按语义短标题撞名。

保留每组中最早创建（id 最小）的一条，其余 is_active=False。
搜索 / 列表只返回 is_active=True，因此彻底搜不到。
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict

sys.path.insert(0, r'd:\zhongruan\zhongruan\backend')

from app import create_app
from app.models import Problem, db
from app.services.practice_question import PracticeQuestionService


def _norm_title(text: str) -> str:
    cleaned = re.sub(r'\s+', '', (text or '').strip().lower())
    cleaned = re.sub(r'[，,。.!！？?\-—·•]', '', cleaned)
    return cleaned


def _semantic_short(problem: Problem) -> str:
    stem = PracticeQuestionService._clean_legacy_markup(
        problem.description_cn or problem.title_cn or ''
    )
    return PracticeQuestionService._infer_semantic_title(
        stem, (problem.title_cn or problem.title_en or '编程练习')[:20]
    )


def deactivate_duplicates(dry_run: bool = False) -> dict:
    rows = (
        Problem.query.filter(Problem.is_active.is_(True))
        .order_by(Problem.id.asc())
        .all()
    )
    by_title_cn: dict[str, list[Problem]] = defaultdict(list)
    by_semantic: dict[str, list[Problem]] = defaultdict(list)
    for row in rows:
        cn = _norm_title(row.title_cn or '')
        if cn:
            by_title_cn[cn].append(row)
        # 过宽语义标题（如「问候语输出」）只在同 kg 节点内去重，避免误伤
        short = _semantic_short(row)
        key = f'{row.kg_node_id or ""}::{_norm_title(short)}'
        by_semantic[key].append(row)

    keep_ids: set[int] = set()
    drop_ids: set[int] = set()
    reasons: dict[int, str] = {}

    def mark_group(group: list[Problem], reason: str):
        if len(group) < 2:
            return
        survivor = group[0]
        keep_ids.add(survivor.id)
        for dup in group[1:]:
            if dup.id in keep_ids:
                continue
            drop_ids.add(dup.id)
            reasons[dup.id] = f'{reason}; keep={survivor.problem_no}'

    for group in by_title_cn.values():
        mark_group(group, 'duplicate_title_cn')

    # 语义撞名：仅当短标题属于高重合入门题时去重
    BROAD = {'问候语输出', '标准输出', '读取输入', '变量运算', '条件分支', '循环统计'}
    for key, group in by_semantic.items():
        short = key.split('::', 1)[-1]
        # 还原短标题用于判断
        sample_short = _semantic_short(group[0])
        if sample_short not in BROAD:
            continue
        remaining = [row for row in group if row.id not in drop_ids]
        mark_group(remaining, f'duplicate_semantic:{sample_short}')

    dropped = []
    for row in rows:
        if row.id not in drop_ids:
            continue
        dropped.append({
            'id': row.id,
            'problem_no': row.problem_no,
            'title_cn': row.title_cn,
            'reason': reasons.get(row.id, ''),
        })
        if not dry_run:
            row.is_active = False
            note = (row.review_note or '') + f' [dedup:{reasons.get(row.id, "")}]'
            row.review_note = note[:500]
            row.needs_review = True

    if not dry_run and dropped:
        db.session.commit()

    return {
        'active_before': len(rows),
        'deactivated': len(dropped),
        'active_after': len(rows) - len(dropped),
        'items': dropped,
    }


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    app = create_app('development')
    with app.app_context():
        result = deactivate_duplicates(dry_run=dry)
        print(
            f"before={result['active_before']} deactivated={result['deactivated']} "
            f"after={result['active_after']} dry_run={dry}"
        )
        for item in result['items'][:40]:
            print(f"  - {item['problem_no']} id={item['id']} :: {item['reason']} :: {item['title_cn']}")
