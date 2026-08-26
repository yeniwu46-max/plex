# -*- coding: utf-8 -*-
"""把知识点节点与统一题库写入 MySQL。幂等，可反复重跑。

## 幂等键

每条记录都有稳定的 `source_ref`（AI 生成题按"节点 + 题干哈希"合成），落库时按
`problems.source_ref` 查找：存在就更新，不存在就插入。因此重跑不会产生重复行，
也不会打乱已有 id。

## 为什么必须保留旧 problem id

`problem_submissions` 有 26,756 行历史提交通过外键指向 `problems.id`，
`problem_legacy_quest_map` 也一样。所以来自 `legacy_bank` 的 70 道题**原地更新**，
id 不变；其余来源的题目从 `NEW_ID_BASE` 起分配新 id，避开旧 id 区间。

## 标签

旧的 7 个 `concept:A~G` 标签保留（它们仍标注着旧题库的原始分组，是审计线索），
另外新增 8 个 `domain:<key>` 标签对应重排后的大类，并为每道题重建大类标签映射。

用法：
    python scripts/knowledge_rebuild/load_mysql.py
    python scripts/knowledge_rebuild/load_mysql.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from collections import Counter
from pathlib import Path

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

_T0 = time.monotonic()


def log(message: str) -> None:
    """带耗时的进度输出，方便定位这类批量写入卡在哪一步。"""
    print(f'[+{time.monotonic() - _T0:6.1f}s] {message}', flush=True)


BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_session import readonly_scope, session_scope  # noqa: E402

from app.utils.time import utc_now  # noqa: E402

from app.data.knowledge_node_registry import (  # noqa: E402
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    get_domain,
    nodes_for_domain,
)
from app.data.kg_topology import KG_NODES  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
INPUT_PATH = OUTPUT_DIR / 'unified_questions.json'

_NOW = utc_now()

# 旧题库 id 最大 150；新题从 1001 起，留足余量且一眼可辨
NEW_ID_BASE = 1001

DOMAIN_NO_PREFIX = {
    'lang-basics': 'LB',
    'sequence': 'SQ',
    'branch': 'BR',
    'loop': 'LP',
    'array': 'AR',
    'string': 'ST',
    'function': 'FN',
    'search': 'SE',
}

DOMAIN_TAG_COLOR = {
    'lang-basics': '#38bdf8',
    'sequence': '#34d399',
    'branch': '#fbbf24',
    'loop': '#f472b6',
    'array': '#a78bfa',
    'string': '#22d3ee',
    'function': '#fb923c',
    'search': '#f87171',
}


def stable_source_ref(record: dict) -> str:
    """给没有天然唯一标识的记录（AI 生成题）合成稳定 key，保证重跑幂等。"""
    existing = record.get('source_ref')
    if existing:
        return existing
    basis = f'{record.get("kg_node_id")}|{(record.get("stem") or "").strip()}'
    digest = hashlib.sha1(basis.encode('utf-8')).hexdigest()[:12]
    return f'ai_generated:{record.get("kg_node_id")}:{digest}'


def sync_knowledge_nodes(session, dry_run: bool) -> tuple[int, int]:
    from app.models import KnowledgeNode

    positions = {node['id']: (node['x'], node['y']) for node in KG_NODES}
    existing = {row.id: row for row in session.query(KnowledgeNode).all()}
    inserted = updated = 0

    for domain in KNOWLEDGE_DOMAINS:
        for order, entry in enumerate(nodes_for_domain(domain.key)):
            x, y = positions.get(entry.kg_id, (None, None))
            payload = {
                'domain_key': domain.key,
                'domain_title': domain.title,
                'domain_order': domain.order,
                'title': entry.label,
                'summary': entry.summary,
                'sort_order': order,
                'level': entry.level,
                'default_difficulty': entry.default_difficulty,
                'knowledge_keys_json': list(entry.knowledge_keys),
                'legacy_kg_ids_json': list(entry.knowledge_keys),
                'document_id': entry.document_id,
                'pos_x': x,
                'pos_y': y,
            }
            row = existing.get(entry.kg_id)
            if row is None:
                if not dry_run:
                    session.add(KnowledgeNode(id=entry.kg_id, **payload))
                inserted += 1
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
                updated += 1

    # 注册表里已删除的旧节点（intro/var/cond…）不该残留在表里
    valid_ids = {e.kg_id for e in KNOWLEDGE_NODE_REGISTRY}
    stale = [row for node_id, row in existing.items() if node_id not in valid_ids]
    if stale and not dry_run:
        for row in stale:
            session.delete(row)
    return inserted, updated


def allocate_identifiers(records: list[dict], existing_by_ref: dict, existing_rows: list) -> None:
    """给新记录分配 problems.id 与 problem_no（旧记录沿用原值）。"""
    used_ids = {row.id for row in existing_rows}
    used_nos = {row.problem_no for row in existing_rows}
    next_id = max(NEW_ID_BASE, (max(used_ids) + 1) if used_ids else NEW_ID_BASE)
    counters: Counter = Counter()

    # 已有 problem_no 里同前缀的最大序号，避免重跑时序号回绕撞车
    for no in used_nos:
        match = re.fullmatch(r'([A-Z]{2})(\d{3})', no or '')
        if match:
            counters[match.group(1)] = max(counters[match.group(1)], int(match.group(2)))

    for record in records:
        ref = record['source_ref']
        row = existing_by_ref.get(ref)
        if row is not None:
            record['_problem_id'] = row.id
            record['_problem_no'] = row.problem_no
            continue
        while next_id in used_ids:
            next_id += 1
        record['_problem_id'] = next_id
        used_ids.add(next_id)

        prefix = DOMAIN_NO_PREFIX.get(record.get('domain_key'), 'XX')
        counters[prefix] += 1
        candidate = f'{prefix}{counters[prefix]:03d}'
        while candidate in used_nos:
            counters[prefix] += 1
            candidate = f'{prefix}{counters[prefix]:03d}'
        record['_problem_no'] = candidate
        used_nos.add(candidate)


def upsert_problems(session, records: list[dict], dry_run: bool) -> dict[str, int]:
    from app.models import Problem

    log('upsert_problems: 载入现有 problems')
    existing_rows = session.query(Problem).all()
    log(f'upsert_problems: 现有 {len(existing_rows)} 行')
    existing_by_ref = {row.source_ref: row for row in existing_rows if row.source_ref}
    # 首次运行时旧题的 source_ref 还是空的，按 'problems:<id>' 约定回填
    for row in existing_rows:
        if not row.source_ref:
            existing_by_ref.setdefault(f'problems:{row.id}', row)

    for record in records:
        record['source_ref'] = stable_source_ref(record)
    allocate_identifiers(records, existing_by_ref, existing_rows)
    log('upsert_problems: id 分配完成，开始写字段')

    stats = Counter()
    for index, record in enumerate(records, 1):
        if index % 25 == 0:
            log(f'upsert_problems: {index}/{len(records)}')
        row = existing_by_ref.get(record['source_ref'])
        is_new = row is None
        if is_new:
            row = Problem(id=record['_problem_id'], problem_no=record['_problem_no'])
            # created_at/updated_at 的列默认值是 db.func.now()，SQLAlchemy 会把它原样
            # 拼成 "... , now(), now())"。pymysql 的 RE_INSERT_VALUES 只认全是占位符的
            # VALUES 子句，遇到这种混了 SQL 函数的语句会匹配失败并在 40 多个占位符上
            # 指数级回溯，executemany 直接卡死。显式赋值让所有值都变成绑定参数即可绕开。
            row.created_at = _NOW
            row.updated_at = _NOW
            if not dry_run:
                session.add(row)
            stats['inserted'] += 1
        else:
            stats['updated'] += 1

        qtype = record.get('question_type') or 'coding'
        row.question_type = qtype
        row.kg_node_id = record.get('kg_node_id')
        row.domain_key = record.get('domain_key')
        row.source_kind = record.get('source_kind')
        row.source_ref = record['source_ref']
        row.title_cn = (record.get('title_cn') or record.get('stem') or '未命名题目')[:200]
        row.title_en = (record.get('title_en') or None)
        row.concept = (record.get('legacy_concept') or None)
        row.concept_group = record.get('legacy_concept_group') or None
        row.description_cn = record.get('stem')
        row.description_en = record.get('stem_en')
        row.has_english = bool(record.get('has_english'))
        row.background = record.get('background')
        row.background_source = record.get('background_source')
        row.input_format_cn = record.get('input_format')
        row.output_format_cn = record.get('output_format')
        row.input_format_en = record.get('input_format_en')
        row.output_format_en = record.get('output_format_en')
        row.samples_json = record.get('samples') or []
        row.samples_source = record.get('samples_source')
        row.notes_json = record.get('notes') or []
        row.options_json = record.get('options') or []
        row.correct_index = record.get('correct_index') if qtype == 'mcq' else None
        row.test_cases_json = record.get('test_cases') or []
        row.starter_code = record.get('starter_code')
        row.run_mode = record.get('run_mode')
        row.hint = record.get('hint')
        row.reference_answer = record.get('reference_answer')
        row.template = record.get('template')
        row.difficulty = record.get('difficulty')
        row.star_difficulty = record.get('star_difficulty')
        row.time_limit_ms = record.get('time_limit_ms')
        row.merged_from_json = record.get('merged_from') or []
        row.needs_review = bool(record.get('needs_review'))
        row.review_note = record.get('review_note')
        row.is_active = True

    return dict(stats)


def rebuild_domain_tags(session, records: list[dict], dry_run: bool) -> dict[str, int]:
    """重建 8 个大类标签及其映射（保留旧的 concept:A~G 作为审计线索）。"""
    from app.models import Problem, ProblemTag, ProblemTagMap

    tags_by_code = {tag.code: tag for tag in session.query(ProblemTag).all()}
    for domain in KNOWLEDGE_DOMAINS:
        code = f'domain:{domain.key}'
        tag = tags_by_code.get(code)
        if tag is None:
            tag = ProblemTag(
                code=code, label=domain.title, tag_type='domain',
                color=DOMAIN_TAG_COLOR.get(domain.key), sort_order=domain.order,
            )
            if not dry_run:
                session.add(tag)
            tags_by_code[code] = tag
        else:
            tag.label = domain.title
            tag.tag_type = 'domain'
            tag.color = DOMAIN_TAG_COLOR.get(domain.key)
            tag.sort_order = domain.order
    if not dry_run:
        session.flush()

    if dry_run:
        return {'domain_tags': len(KNOWLEDGE_DOMAINS)}

    domain_tag_ids = {tag.id for code, tag in tags_by_code.items() if code.startswith('domain:')}
    if domain_tag_ids:
        session.query(ProblemTagMap).filter(
            ProblemTagMap.tag_id.in_(domain_tag_ids)
        ).delete(synchronize_session=False)

    problems_by_ref = {row.source_ref: row for row in session.query(Problem).all() if row.source_ref}
    mapped = 0
    for record in records:
        row = problems_by_ref.get(record['source_ref'])
        domain_key = record.get('domain_key')
        if not row or not domain_key:
            continue
        tag = tags_by_code.get(f'domain:{domain_key}')
        if tag:
            session.add(ProblemTagMap(problem_id=row.id, tag_id=tag.id))
            mapped += 1
    return {'domain_tags': len(KNOWLEDGE_DOMAINS), 'tag_maps': mapped}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    records = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    log(f'读取 {len(records)} 道题')

    if args.dry_run:
        with readonly_scope() as session:
            inserted_nodes, updated_nodes = sync_knowledge_nodes(session, True)
            log(f'knowledge_nodes: 新增 {inserted_nodes} / 更新 {updated_nodes}')
            log(f'problems: {upsert_problems(session, records, True)}')
            log('dry-run，未写入')
        return

    with session_scope() as session:
        log('已连上数据库')
        inserted_nodes, updated_nodes = sync_knowledge_nodes(session, False)
        log(f'knowledge_nodes: 新增 {inserted_nodes} / 更新 {updated_nodes}')
        session.flush()
        log('knowledge_nodes 已 flush')

        log(f'problems: {upsert_problems(session, records, False)}')
        session.flush()
        log('problems 已 flush')

        log(f'tags: {rebuild_domain_tags(session, records, False)}')
        log('准备提交')
    log('已提交')

    _report()


def _report() -> None:
    from sqlalchemy import func

    from app.models import Problem

    with readonly_scope() as session:
        counts = dict(
            session.query(Problem.kg_node_id, func.count(Problem.id))
            .filter(Problem.is_active.is_(True))
            .group_by(Problem.kg_node_id).all()
        )
        total = sum(counts.values())
        review = session.query(func.count(Problem.id)).filter(Problem.needs_review.is_(True)).scalar()
        print(f'\n库内题目 {total} 道，其中 needs_review = 1 的 {review} 道')
        short = []
        for domain in KNOWLEDGE_DOMAINS:
            print(f'  [{domain.title}]')
            for entry in nodes_for_domain(domain.key):
                count = counts.get(entry.kg_id, 0)
                flag = '' if count >= 4 else '  <-- 不足 4 题'
                print(f'    {entry.kg_id:16s} {entry.label:12s} {count:3d}{flag}')
                if count < 4:
                    short.append(entry.kg_id)
        orphan = counts.get(None, 0)
        if orphan:
            print(f'  未挂节点的题目: {orphan} 道')
        print(f'\n不足 4 题的节点: {short or "无"}')


if __name__ == '__main__':
    main()
