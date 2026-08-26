# -*- coding: utf-8 -*-
"""从 PLEX 现存的五个题目来源抽取成统一中间格式。

五个来源（见 REBUILD_REPORT.md 的口径说明）：

| source_kind      | 出处                                              |
| ---------------- | ------------------------------------------------- |
| legacy_bank      | `problems` 表（旧 Mulberry/HydroOJ dump 清洗后的 70 道） |
| trial_question   | `trial_questions` 表（教师试炼实际投放的题目）           |
| builtin_coding   | `app/data/coding_question_bank.py`                 |
| builtin_mcq      | `app/services/question_generator.py::QUESTION_BANK` |
| frontend_static  | `frontend/src/data/pythonTrialQuestions.ts`         |

本脚本只做"抽取 + 结构归一"，不做清洗与去重（那是 clean_merge.py 的职责），
因此产物里会保留空题干、重复题等原始脏数据，便于清洗阶段统计与追溯。

用法：
    python scripts/knowledge_rebuild/collect_sources.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
FRONTEND_JSON = OUTPUT_DIR / 'frontend_questions.json'
EXTRACTOR_JS = Path(__file__).resolve().parent / 'extract_frontend_questions.js'


def _blank(value) -> bool:
    return value is None or not str(value).strip()


def make_record(**kwargs) -> dict:
    """统一中间格式。字段缺失一律用 None / 空列表，不臆造内容。"""
    record = {
        'source_kind': None,
        'source_ref': None,          # 在原来源中的唯一标识，用于追溯
        'question_type': 'coding',   # coding | mcq
        'title_cn': None,
        'title_en': None,
        'stem': None,                # 题干/描述正文（中文）
        'stem_en': None,
        'background': None,
        'background_source': None,
        'input_format': None,
        'output_format': None,
        'input_format_en': None,
        'output_format_en': None,
        'samples': [],               # [{input, output}]
        'samples_source': None,
        'notes': [],
        'options': [],               # mcq
        'correct_index': None,       # mcq
        'test_cases': [],            # coding
        'starter_code': None,
        'run_mode': None,
        'hint': None,
        'reference_answer': None,
        'template': None,
        'difficulty': None,
        'star_difficulty': None,
        'legacy_knowledge_key': None,
        'legacy_concept': None,
        'legacy_concept_group': None,
        'legacy_problem_id': None,
        'legacy_problem_no': None,
        'time_limit_ms': None,
        'has_english': False,
    }
    record.update(kwargs)
    return record


def collect_legacy_bank(session) -> list[dict]:
    from app.models import Problem

    records = []
    for p in session.query(Problem).order_by(Problem.id).all():
        records.append(make_record(
            source_kind='legacy_bank',
            source_ref=f'problems:{p.id}',
            question_type='coding',
            title_cn=p.title_cn,
            title_en=p.title_en,
            stem=p.description_cn,
            stem_en=p.description_en,
            background=p.background,
            background_source=p.background_source,
            input_format=p.input_format_cn,
            output_format=p.output_format_cn,
            input_format_en=p.input_format_en,
            output_format_en=p.output_format_en,
            samples=p.samples_json or [],
            samples_source=p.samples_source,
            notes=p.notes_json or [],
            reference_answer=p.reference_answer,
            template=p.template,
            difficulty=p.difficulty,
            star_difficulty=p.star_difficulty,
            legacy_concept=p.concept,
            legacy_concept_group=p.concept_group,
            legacy_problem_id=p.id,
            legacy_problem_no=p.problem_no,
            time_limit_ms=p.time_limit_ms,
            has_english=bool(p.has_english),
            run_mode='stdout',
        ))
    return records


def collect_trial_questions(session) -> list[dict]:
    from app.models import TrialQuestion

    records = []
    for q in session.query(TrialQuestion).order_by(TrialQuestion.id).all():
        meta = q.coding_meta()
        options = q.options if isinstance(q.options, list) else []
        qtype = q.question_type or 'mcq'
        examples = meta.get('examples') or []
        samples = [
            {'input': str(item.get('input', '')), 'output': str(item.get('output', ''))}
            for item in examples
            if isinstance(item, dict)
        ]
        records.append(make_record(
            source_kind='trial_question',
            source_ref=f'trial_questions:{q.id}',
            question_type=qtype,
            title_cn=meta.get('title'),
            stem=q.stem,
            samples=samples,
            notes=[c for c in (meta.get('constraints') or []) if str(c).strip()],
            options=options,
            correct_index=q.correct_index if qtype == 'mcq' else None,
            test_cases=meta.get('test_cases') or [],
            starter_code=meta.get('starter_code'),
            run_mode=meta.get('run_mode') or ('stdout' if qtype == 'coding' else None),
            hint=meta.get('hint'),
            legacy_knowledge_key=q.knowledge_key,
            legacy_problem_id=meta.get('source_problem_id'),
        ))
    return records


def collect_builtin_coding() -> list[dict]:
    from app.data.coding_question_bank import CODING_QUESTION_BANK

    records = []
    for item in CODING_QUESTION_BANK:
        records.append(make_record(
            source_kind='builtin_coding',
            source_ref=f'coding_question_bank:{item.get("id")}',
            question_type='coding',
            stem=item.get('stem'),
            test_cases=item.get('test_cases') or [],
            starter_code=item.get('starter_code'),
            run_mode=item.get('run_mode') or 'stdout',
            hint=item.get('hint'),
            legacy_knowledge_key=item.get('knowledge_key'),
        ))
    return records


def collect_builtin_mcq() -> list[dict]:
    from app.services.question_generator import QUESTION_BANK

    records = []
    for bank_key, items in QUESTION_BANK.items():
        for index, item in enumerate(items):
            records.append(make_record(
                source_kind='builtin_mcq',
                source_ref=f'question_bank:{bank_key}:{index}',
                question_type='mcq',
                stem=item.get('stem'),
                options=list(item.get('options') or []),
                correct_index=item.get('correct_index'),
                legacy_knowledge_key=bank_key,
            ))
    return records


def collect_frontend_static() -> list[dict]:
    if not FRONTEND_JSON.exists():
        print('  前端题目 JSON 不存在，先运行 extract_frontend_questions.js ...')
        subprocess.run(
            ['node', str(EXTRACTOR_JS), str(FRONTEND_JSON)],
            check=True,
            cwd=str(BACKEND_ROOT),
        )

    raw = json.loads(FRONTEND_JSON.read_text(encoding='utf-8'))
    difficulty_star = {'入门': 1, '基础': 2, '进阶': 3, '挑战': 4}
    records = []
    for item in raw:
        examples = item.get('examples') or []
        records.append(make_record(
            source_kind='frontend_static',
            source_ref=f'pythonTrialQuestions:{item.get("id")}',
            question_type='coding',
            title_cn=item.get('title'),
            stem=item.get('description'),
            samples=[
                {'input': str(ex.get('input', '')), 'output': str(ex.get('output', ''))}
                for ex in examples
                if isinstance(ex, dict)
            ],
            notes=[c for c in (item.get('constraints') or []) if str(c).strip()],
            test_cases=item.get('testCases') or [],
            starter_code=item.get('starterCode'),
            run_mode=item.get('runMode') or 'stdout',
            hint=item.get('hint'),
            star_difficulty=difficulty_star.get(item.get('difficulty')),
            # 前端题目的 topic/tags 是自然语言，交给 assign_nodes.py 的规则匹配使用
            legacy_knowledge_key=None,
            legacy_concept=item.get('topic'),
            notes_extra=None,
        ) | {'frontend_tags': item.get('tags') or [], 'frontend_topic': item.get('topic')})
    return records


def main() -> None:
    from app import create_app
    from app.models import db

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = create_app('development')
    with app.app_context():
        buckets = {
            'legacy_bank': collect_legacy_bank(db.session),
            'trial_question': collect_trial_questions(db.session),
            'builtin_coding': collect_builtin_coding(),
            'builtin_mcq': collect_builtin_mcq(),
            'frontend_static': collect_frontend_static(),
        }

    all_records: list[dict] = []
    print('\n来源抽取结果：')
    for kind, records in buckets.items():
        coding = sum(1 for r in records if r['question_type'] == 'coding')
        mcq = sum(1 for r in records if r['question_type'] == 'mcq')
        blank = sum(1 for r in records if _blank(r['stem']))
        print(f'  {kind:16s} 共 {len(records):4d} 条（coding {coding}, mcq {mcq}, 空题干 {blank}）')
        all_records.extend(records)

    out_path = OUTPUT_DIR / 'collected_questions.json'
    out_path.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n合计 {len(all_records)} 条 -> {out_path}')


if __name__ == '__main__':
    main()
