"""Load the cleaned JSON intermediates straight into the app's configured
database via the existing Flask/SQLAlchemy models -- the easiest way to
preview task 2's frontend against real data on a local SQLite dev DB.

This does **not** bypass the migration system: it assumes `problems`,
`problem_legacy_quest_map` and `problem_submissions` already exist (run
`python manage.py upgrade` first). It only performs idempotent data
upserts through the ORM, so it is safe to re-run after re-cleaning the dump.

Works against whatever `DATABASE_URL` (or the default SQLite dev file)
`backend/app/config.py` resolves -- so the same script also works for a
MySQL target if you point `DATABASE_URL` at one instead of hand-writing
`output/data.sql`.

Usage (from backend/):
    python manage.py upgrade
    python scripts/problem_bank_import/load_sqlite.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

OUT_DIR = Path(__file__).resolve().parent / 'output'


def parse_dt(value):
    return datetime.fromisoformat(value) if value else None


def load_json(name):
    with open(OUT_DIR / name, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def main():
    from app import create_app
    from app.models import Problem, ProblemLegacyQuestMap, ProblemSubmission, ProblemTag, ProblemTagMap, db

    app = create_app('development')

    problems = load_json('problems.json')
    quest_map = load_json('problem_legacy_quest_map.json')
    submissions = load_json('problem_submissions.json')
    tags_path = OUT_DIR / 'problem_tags.json'
    tag_map_path = OUT_DIR / 'problem_tag_map.json'
    tags = load_json('problem_tags.json') if tags_path.exists() else []
    raw_tag_map = load_json('problem_tag_map.json') if tag_map_path.exists() else []

    with app.app_context():
        problem_ids = [p['id'] for p in problems]

        for row in problems:
            obj = db.session.get(Problem, row['id']) or Problem(id=row['id'])
            obj.problem_no = row['problem_no']
            obj.concept = row['concept']
            obj.concept_group = row['concept_group']
            obj.title_en = row['title_en']
            obj.title_cn = row['title_cn']
            obj.background = row['background']
            obj.background_source = row.get('background_source')
            obj.description_en = row['description_en']
            obj.description_cn = row['description_cn']
            obj.has_english = row.get('has_english', False)
            obj.input_format_en = row['input_format_en']
            obj.output_format_en = row['output_format_en']
            obj.input_format_cn = row['input_format_cn']
            obj.output_format_cn = row['output_format_cn']
            obj.samples_json = row['samples_json']
            obj.samples_source = row.get('samples_source')
            obj.notes_json = row['notes_json']
            obj.difficulty = row['difficulty']
            obj.level = row['level']
            obj.star_difficulty = row.get('star_difficulty')
            obj.time_limit_ms = row.get('time_limit_ms')
            obj.topic = row['topic']
            obj.reference_answer = row['reference_answer']
            obj.template = row['template']
            obj.legacy_problem_name = row['legacy_problem_name']
            obj.legacy_author_user_id = row['legacy_author_user_id']
            obj.is_active = row['is_active']
            obj.created_at = parse_dt(row['created_at'])
            obj.updated_at = parse_dt(row['updated_at'])
            db.session.add(obj)
        db.session.commit()
        print(f'upserted {len(problems)} problems')

        ProblemLegacyQuestMap.query.filter(ProblemLegacyQuestMap.problem_id.in_(problem_ids)).delete(
            synchronize_session=False
        )
        db.session.bulk_insert_mappings(ProblemLegacyQuestMap, quest_map)
        db.session.commit()
        print(f'replaced quest map: {len(quest_map)} rows')

        if tags:
            tag_id_by_code = {}
            for t in tags:
                obj = ProblemTag.query.filter_by(code=t['code']).first() or ProblemTag(code=t['code'])
                obj.label = t['label']
                obj.tag_type = t['tag_type']
                obj.color = t.get('color')
                obj.sort_order = t.get('sort_order', 0)
                db.session.add(obj)
                db.session.flush()
                tag_id_by_code[t['code']] = obj.id
            db.session.commit()

            ProblemTagMap.query.filter(ProblemTagMap.problem_id.in_(problem_ids)).delete(synchronize_session=False)
            db.session.bulk_insert_mappings(ProblemTagMap, [
                {'problem_id': row['problem_id'], 'tag_id': tag_id_by_code[row['tag_code']]}
                for row in raw_tag_map
            ])
            db.session.commit()
            print(f'upserted {len(tags)} tags, replaced tag map: {len(raw_tag_map)} rows')
        else:
            print('no problem_tags.json found, skipping tags (run generate_tags.py first)')

        batch = []
        count = 0
        for row in submissions:
            batch.append({
                'id': row['id'],
                'problem_id': row['problem_id'],
                'legacy_user_id': row['legacy_user_id'],
                'legacy_username': row['legacy_username'],
                'legacy_student_name': row['legacy_student_name'],
                'legacy_group_id': row['legacy_group_id'],
                'legacy_group_name': row['legacy_group_name'],
                'code_content': row['code_content'],
                'status': row['status'],
                'is_accepted': row['is_accepted'],
                'compile_success': row['compile_success'],
                'test_success': row['test_success'],
                'score_points': row['score_points'],
                'score_total': row['score_total'],
                'score_percent': row['score_percent'],
                'test_case_results_json': row['test_case_results_json'],
                'raw_judge_output': row['raw_judge_output'],
                'exec_time_ms': row['exec_time_ms'],
                'exec_memory_kb': row['exec_memory_kb'],
                'time_spent_seconds': row['time_spent_seconds'],
                'self_confidence': row['self_confidence'],
                'legacy_error_name': row['legacy_error_name'],
                'returncode': row['returncode'],
                'legacy_prev_solution_id': row['legacy_prev_solution_id'],
                'submitted_at': parse_dt(row['submitted_at']),
            })
            if len(batch) >= 1000:
                _flush_submissions(db, ProblemSubmission, batch)
                count += len(batch)
                batch = []
        if batch:
            _flush_submissions(db, ProblemSubmission, batch)
            count += len(batch)
        print(f'upserted {count} submissions')


def _flush_submissions(db, model, batch):
    ids = [row['id'] for row in batch]
    model.query.filter(model.id.in_(ids)).delete(synchronize_session=False)
    db.session.bulk_insert_mappings(model, batch)
    db.session.commit()


if __name__ == '__main__':
    main()
