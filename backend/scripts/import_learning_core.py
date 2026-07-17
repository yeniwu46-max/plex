#!/usr/bin/env python3
"""Import the masked Mulberry learning SQL export into the local A3 database.

The importer intentionally maps the dump into existing application tables
instead of executing the dump directly. This keeps the current app schema intact,
adds a second anonymization layer, and makes the imported data visible through
teacher/admin APIs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import DevelopmentConfig  # noqa: E402
from app.models import (  # noqa: E402
    Class,
    Role,
    StudentMistake,
    StudentProfile,
    Trial,
    TrialParticipation,
    TrialQuestion,
    TrialQuestionProgress,
    User,
    db,
)
from app.services.question_generator import QuestionGenerator  # noqa: E402
from app.utils.time import utc_now  # noqa: E402


CLASS_THEMES = (
    ('火箭班', '火箭启航任务舱'),
    ('星舰班', '星舰远航任务舱'),
    ('月影班', '月影探索任务舱'),
    ('银河班', '银河巡航任务舱'),
    ('星环班', '星环跃迁任务舱'),
    ('极光班', '极光观测任务舱'),
    ('辰光班', '辰光领航任务舱'),
    ('天穹班', '天穹深空任务舱'),
)
TEACHER_USERNAME = 'teacher001'
DEFAULT_STUDENT_PASSWORD = 'student123'

CONCEPT_TO_KEY = {
    'basics': 'intro',
    'datatypes': 'var',
    'operators': 'ops',
    'conditionals': 'cond',
    'loops': 'loop',
    'for loops': 'loop',
    'while loops': 'loop',
    'functions': 'func',
    'string': 'str',
    'strings': 'str',
    'lists': 'list',
    'list': 'list',
    'files': 'file',
    'exceptions': 'except',
}


@dataclass
class ImportStats:
    groups: int = 0
    users: int = 0
    profiles: int = 0
    trials: int = 0
    questions: int = 0
    progress: int = 0
    participations: int = 0
    mistakes: int = 0


def _unescape_sql_string(value: str) -> str:
    replacements = {
        r'\0': '\0',
        r'\n': '\n',
        r'\r': '\r',
        r'\t': '\t',
        r'\b': '\b',
        r'\Z': '\x1a',
        r"\'": "'",
        r'\"': '"',
        r'\\': '\\',
    }
    result = []
    index = 0
    while index < len(value):
        if value[index] == '\\' and index + 1 < len(value):
            pair = value[index:index + 2]
            result.append(replacements.get(pair, value[index + 1]))
            index += 2
        else:
            result.append(value[index])
            index += 1
    return ''.join(result)


def _convert_sql_value(token: str) -> Any:
    token = token.strip()
    if token.upper() == 'NULL':
        return None
    if token.startswith("'") and token.endswith("'"):
        return _unescape_sql_string(token[1:-1])
    if re.fullmatch(r'-?\d+', token):
        return int(token)
    if re.fullmatch(r'-?\d+\.\d+', token):
        return float(token)
    return token


def _split_tuple_values(tuple_body: str) -> list[Any]:
    values = []
    start = 0
    in_string = False
    escaped = False
    for index, char in enumerate(tuple_body):
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == "'":
                in_string = False
        else:
            if char == "'":
                in_string = True
            elif char == ',':
                values.append(_convert_sql_value(tuple_body[start:index]))
                start = index + 1
    values.append(_convert_sql_value(tuple_body[start:]))
    return values


def _iter_insert_tuples(values_sql: str):
    in_string = False
    escaped = False
    depth = 0
    start = None
    for index, char in enumerate(values_sql):
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == "'":
                in_string = False
            continue
        if char == "'":
            in_string = True
        elif char == '(':
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0 and start is not None:
                yield values_sql[start:index]
                start = None


def _iter_insert_statements(text: str):
    header_pattern = re.compile(r'INSERT INTO `(?P<table>[^`]+)` \((?P<cols>[^)]+)\) VALUES\s*', re.DOTALL)
    position = 0
    while True:
        match = header_pattern.search(text, position)
        if not match:
            return
        in_string = False
        escaped = False
        end = match.end()
        while end < len(text):
            char = text[end]
            if in_string:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == "'":
                    in_string = False
            else:
                if char == "'":
                    in_string = True
                elif char == ';':
                    yield match.group('table'), match.group('cols'), text[match.end():end]
                    position = end + 1
                    break
            end += 1
        else:
            return


def load_dump(path: Path) -> dict[str, list[dict[str, Any]]]:
    text = path.read_text(encoding='utf-8')
    tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for table, cols_sql, values_sql in _iter_insert_statements(text):
        cols = [part.strip().strip('`') for part in cols_sql.split(',')]
        for tuple_body in _iter_insert_tuples(values_sql):
            raw_values = _split_tuple_values(tuple_body)
            tables[table].append(dict(zip(cols, raw_values)))
    return dict(tables)


def make_app() -> Flask:
    app = Flask('learning-core-import')
    app.config.from_object(DevelopmentConfig)
    app.config['SQLALCHEMY_ECHO'] = False
    db.init_app(app)
    return app


def ensure_roles() -> dict[str, Role]:
    roles = {role.name: role for role in Role.query.all()}
    for name, description, color in (
        ('student', '学生', 'green'),
        ('teacher', '教师', 'orange'),
        ('admin', '管理员', 'purple'),
    ):
        if name not in roles:
            role = Role(name=name, description=description, color=color)
            db.session.add(role)
            db.session.flush()
            roles[name] = role
    return roles


def ensure_import_teacher(teacher_role: Role) -> User:
    teacher = User.query.filter_by(username=TEACHER_USERNAME).first()
    if teacher:
        return teacher
    if not teacher:
        teacher = User(username=TEACHER_USERNAME)
        db.session.add(teacher)
    teacher.email = f'{TEACHER_USERNAME}@example.local'
    teacher.password_hash = generate_password_hash('teacher123')
    teacher.real_name = '星航导师'
    teacher.role_id = teacher_role.id
    teacher.status = 'active'
    return teacher


def unix_time(value: Any) -> datetime | None:
    try:
        timestamp = int(value or 0)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp)


def clean_join_code(group_id: int) -> str:
    return f'LC{group_id:06d}'[-8:]


def themed_class_name(index: int) -> str:
    return CLASS_THEMES[index % len(CLASS_THEMES)][0]


def themed_trial_title(index: int) -> str:
    return CLASS_THEMES[index % len(CLASS_THEMES)][1]


def map_knowledge_key(problem: dict[str, Any]) -> str:
    concept = str(problem.get('concept') or '').strip().lower()
    if concept in CONCEPT_TO_KEY:
        return CONCEPT_TO_KEY[concept]
    topic = int(problem.get('topic') or 0)
    level = int(problem.get('level') or 0)
    if topic <= 1:
        return 'intro'
    if topic == 2:
        return 'var' if level <= 2 else 'ops'
    if topic == 3:
        return 'cond'
    if topic in (4, 5, 6):
        return 'loop'
    if topic >= 7:
        return 'func'
    return 'intro'


def label_for_key(key: str) -> str:
    return QuestionGenerator.label_for_key(key)


def profile_dimension(value: str, evidence: str, confidence: float = 0.8) -> dict[str, Any]:
    return {
        'value': value,
        'confidence': round(max(0.0, min(1.0, confidence)), 2),
        'evidence': [evidence],
        'source': 'imported_learning_core',
    }


def build_profile_dimensions(
    user_id: int,
    group_name: str,
    info: dict[str, Any] | None,
    player: dict[str, Any] | None,
    user_solutions: list[dict[str, Any]],
    problem_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    info = info or {}
    player = player or {}
    difficulty = int(info.get('difficulty') or 0)
    confidence_raw = int(info.get('confidence') or 0)
    programming = int(info.get('programming') or 0)
    level = int(player.get('level') or 1)
    total = len(user_solutions)
    passed = sum(1 for row in user_solutions if is_passed(row))
    accuracy = round(passed / total * 100) if total else 0
    practiced = Counter(
        map_knowledge_key(problem_by_id[row['problem_id']])
        for row in user_solutions
        if row.get('problem_id') in problem_by_id
    )
    focus_keys = [label_for_key(key) for key, _ in practiced.most_common(3)]
    foundation = (
        f'历史练习正确率 {accuracy}%，平台等级 Lv{level}'
        if total
        else f'学习档案难度自评 {difficulty}/5'
    )
    pace = f'历史累计提交 {total} 次，建议按错题和未通过题目复盘'
    mistake_label = '暂无明显错题模式'
    failed = [row for row in user_solutions if not is_passed(row)]
    if failed:
        errors = Counter(str(row.get('status') or row.get('error_name') or '未通过') for row in failed)
        mistake_label = '主要错误类型：' + '、'.join(f'{key}({count})' for key, count in errors.most_common(3))
    return {
        'major_background': profile_dimension(
            '来自星球探索班级',
            f'source_user_id={user_id}',
            0.75,
        ),
        'knowledge_foundation': profile_dimension(
            foundation,
            f'difficulty={difficulty}, programming={programming}, submissions={total}',
            (confidence_raw or 4) / 5,
        ),
        'learning_goal': profile_dimension(
            '完成 Python Normal 编程练习并提升基础编程能力',
            '由星球练习记录生成',
            0.72,
        ),
        'explanation_preference': profile_dimension(
            '偏向通过编程题、运行反馈和错题复盘学习',
            '由在线编程练习记录生成',
            0.7,
        ),
        'mistake_pattern': profile_dimension(mistake_label, '由历史提交状态统计生成', 0.82 if failed else 0.55),
        'learning_pace': profile_dimension(pace, '由历史提交次数生成', 0.8 if total else 0.45),
        'interest_direction': profile_dimension(
            '近期关注：' + ('、'.join(focus_keys) if focus_keys else 'Python 基础'),
            '由练习知识点分布生成',
            0.74 if focus_keys else 0.45,
        ),
        'cognitive_state': profile_dimension(
            '学习状态稳定' if accuracy >= 60 else '需要支持：近期练习正确率偏低',
            f'accuracy={accuracy}%',
            0.78 if total else 0.4,
        ),
    }


def is_passed(solution: dict[str, Any]) -> bool:
    return bool(solution.get('test_success')) or str(solution.get('status') or '').upper() == 'AC'


def choose_representative_solutions(solutions: list[dict[str, Any]]) -> dict[tuple[int, int, int], dict[str, Any]]:
    chosen: dict[tuple[int, int, int], dict[str, Any]] = {}
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in solutions:
        if row.get('remove_time'):
            continue
        key = (int(row['group_id']), int(row['user_id']), int(row['problem_id']))
        grouped[key].append(row)
    for key, rows in grouped.items():
        rows.sort(key=lambda item: (int(item.get('create_time') or 0), int(item.get('id') or 0)))
        passed_rows = [row for row in rows if is_passed(row)]
        chosen[key] = passed_rows[-1] if passed_rows else rows[-1]
    return chosen


def sanitize_output(output: str | None) -> str:
    if not output:
        return ''
    text = str(output)
    text = re.sub(r'[A-Za-z]:\\[^\\\r\n]+(?:\\[^\\\r\n]+)*', '[local-path]', text)
    return text[:1200]


def upsert_student_profile(
    user: User,
    dimensions: dict[str, Any],
) -> None:
    profile = StudentProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
    profile.dimensions = dimensions
    profile.completion_rate = 100
    profile.version = max(int(profile.version or 0), 1)


def ensure_mistake(
    user_id: int,
    question: TrialQuestion,
    solution: dict[str, Any],
    fail_count: int,
) -> StudentMistake:
    question_ref = f'import_learning_core:{question.id}'
    row = StudentMistake.query.filter_by(
        user_id=user_id,
        source='code_trial',
        question_ref=question_ref,
    ).first()
    if not row:
        row = StudentMistake(
            user_id=user_id,
            source='code_trial',
            question_ref=question_ref,
            last_failed_at=unix_time(solution.get('create_time')) or utc_now(),
        )
        db.session.add(row)
    row.knowledge_key = question.knowledge_key or 'intro'
    row.question_title = question.stem[:256]
    row.error_type = 'runtime_error' if solution.get('error_name') else 'wrong_output'
    row.fail_count = max(1, fail_count)
    row.last_failed_at = unix_time(solution.get('create_time')) or utc_now()
    row.meta = {
        'knowledge_label': label_for_key(row.knowledge_key),
        'question_title': row.question_title,
        'source_status': solution.get('status'),
        'source_problem_id': solution.get('problem_id'),
        'tags': ['imported_learning_core'],
    }
    return row


def import_data(dump_path: Path, dry_run: bool = False) -> dict[str, Any]:
    tables = load_dump(dump_path)
    groups = {int(row['id']): row for row in tables.get('group', [])}
    users = {int(row['id']): row for row in tables.get('user', [])}
    infos = {int(row['user_id']): row for row in tables.get('user_info', [])}
    players = {int(row['user_id']): row for row in tables.get('player', []) if row.get('remove_time') == 0}
    problems = {int(row['id']): row for row in tables.get('problem', []) if row.get('remove_time') == 0}
    solutions = tables.get('solution', [])
    representative = choose_representative_solutions(solutions)
    solutions_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    fail_counts: Counter[tuple[int, int, int]] = Counter()
    for row in solutions:
        if row.get('remove_time'):
            continue
        key = (int(row['group_id']), int(row['user_id']), int(row['problem_id']))
        if not is_passed(row):
            fail_counts[key] += 1
        solutions_by_user[int(row['user_id'])].append(row)

    concept_distribution = Counter(map_knowledge_key(problem) for problem in problems.values())
    preview = {
        'source': str(dump_path),
        'raw_counts': {table: len(rows) for table, rows in tables.items()},
        'representative_progress_rows': len(representative),
        'knowledge_distribution': dict(concept_distribution),
    }
    if dry_run:
        return {'dry_run': True, **preview}

    stats = ImportStats()
    roles = ensure_roles()
    teacher = ensure_import_teacher(roles['teacher'])
    student_role = roles['student']
    db.session.flush()

    class_by_source: dict[int, Class] = {}
    for theme_index, (group_id, group) in enumerate(sorted(groups.items())):
        join_code = clean_join_code(group_id)
        class_obj = Class.query.filter_by(join_code=join_code).first()
        if not class_obj:
            class_obj = Class(join_code=join_code)
            db.session.add(class_obj)
        class_obj.name = themed_class_name(theme_index)
        class_obj.description = '星球探索学习小队，围绕 Python 编程任务开展闯关练习。'
        class_obj.teacher_id = teacher.id
        class_obj.grade_level = None
        class_by_source[group_id] = class_obj
        stats.groups += 1
    db.session.flush()

    user_by_source: dict[int, User] = {}
    anonymized_index = 1
    for source_user_id, source_user in sorted(users.items()):
        player = players.get(source_user_id)
        if not player or int(player.get('group_id') or 0) not in class_by_source:
            continue
        class_obj = class_by_source[int(player['group_id'])]
        user = User.query.filter_by(username=f'import_s{source_user_id}').first()
        if not user:
            user = User(username=f'import_s{source_user_id}')
            db.session.add(user)
        user.email = f'import_s{source_user_id}@example.local'
        user.password_hash = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
        user.real_name = f'星航学员_{anonymized_index:04d}'
        user.gender = 'female' if int(infos.get(source_user_id, {}).get('gender') or 0) == 1 else 'male'
        user.role_id = student_role.id
        user.status = 'active'
        user.class_id = class_obj.id
        user.level = max(1, int(player.get('level') or 1))
        user.total_points = int(player.get('exp') or player.get('gold') or 0)
        user.consecutive_days = 0
        user.phone = None
        user.bio = '星球探索学习档案'
        user_by_source[source_user_id] = user
        stats.users += 1
        anonymized_index += 1
    db.session.flush()

    for group_id, class_obj in class_by_source.items():
        class_obj.student_count = sum(
            1
            for player in players.values()
            if int(player.get('group_id') or 0) == group_id and int(player['user_id']) in user_by_source
        )

    for source_user_id, user in user_by_source.items():
        player = players.get(source_user_id)
        group = groups.get(int(player.get('group_id') or 0), {}) if player else {}
        dimensions = build_profile_dimensions(
            source_user_id,
            str(group.get('name') or ''),
            infos.get(source_user_id),
            player,
            solutions_by_user.get(source_user_id, []),
            problems,
        )
        upsert_student_profile(user, dimensions)
        stats.profiles += 1

    trial_by_group: dict[int, Trial] = {}
    question_by_group_problem: dict[tuple[int, int], TrialQuestion] = {}
    problem_ids_by_group: dict[int, set[int]] = defaultdict(set)
    for group_id, _source_user_id, problem_id in representative:
        if problem_id in problems:
            problem_ids_by_group[group_id].add(problem_id)

    for theme_index, (group_id, class_obj) in enumerate(class_by_source.items()):
        title = themed_trial_title(theme_index)
        existing = Trial.query.filter_by(class_id=class_obj.id, trial_type='imported_coding').first()
        if existing:
            db.session.delete(existing)
            db.session.flush()
        group_problem_ids = sorted(problem_ids_by_group.get(group_id) or set(problems))
        knowledge_keys = sorted({map_knowledge_key(problems[pid]) for pid in group_problem_ids if pid in problems})
        trial = Trial(
            class_id=class_obj.id,
            teacher_id=teacher.id,
            title=title,
            trial_type='imported_coding',
            difficulty=50,
            duration_minutes=120,
            status='ended',
            reward_points=0,
            starts_at=unix_time(groups[group_id].get('create_time')) or utc_now(),
            ends_at=utc_now(),
        )
        trial.set_knowledge_keys(knowledge_keys or ['intro'])
        db.session.add(trial)
        db.session.flush()
        trial_by_group[group_id] = trial
        stats.trials += 1

        for order, problem_id in enumerate(group_problem_ids, start=1):
            problem = problems.get(problem_id)
            if not problem:
                continue
            key = map_knowledge_key(problem)
            question = TrialQuestion(
                trial_id=trial.id,
                sort_order=order,
                question_type='coding',
                stem=str(problem.get('cn_description') or problem.get('description') or problem.get('cn_title') or problem.get('title'))[:5000],
                options=[],
                correct_index=0,
                knowledge_key=key,
            )
            question.set_coding_meta({
                'starter_code': str(problem.get('template') or '# 在此编写代码\n'),
                'run_mode': 'stdout',
                'hint': str(problem.get('cn_title') or problem.get('title') or ''),
                'test_cases': [],
                'constraints': [],
                'examples': [],
                'source_problem_id': problem_id,
                'source_answer': str(problem.get('answer') or '')[:2000],
            })
            db.session.add(question)
            db.session.flush()
            question_by_group_problem[(group_id, problem_id)] = question
            stats.questions += 1

    participation_rows: dict[tuple[int, int], TrialParticipation] = {}
    progress_by_trial_user: dict[tuple[int, int], list[TrialQuestionProgress]] = defaultdict(list)
    for (group_id, source_user_id, problem_id), solution in sorted(representative.items()):
        user = user_by_source.get(source_user_id)
        trial = trial_by_group.get(group_id)
        question = question_by_group_problem.get((group_id, problem_id))
        if not user or not trial or not question:
            continue
        row = TrialQuestionProgress.query.filter_by(user_id=user.id, question_id=question.id).first()
        if not row:
            row = TrialQuestionProgress(user_id=user.id, question_id=question.id)
            db.session.add(row)
        passed = is_passed(solution)
        row.status = 'completed'
        row.started_at = unix_time(solution.get('create_time'))
        row.answered_at = unix_time(solution.get('create_time')) or utc_now()
        row.time_spent_sec = int(solution.get('time_spent') or solution.get('time_between') or 0)
        row.submitted_code = str(solution.get('content') or '')
        row.code_passed = passed
        row.is_correct = passed
        row.selected_index = None
        row.selected_label = None
        row.set_code_results([{
            'label': '历史判题结果',
            'expected': '通过' if passed else '未通过',
            'actual': sanitize_output(solution.get('output') or solution.get('status')),
            'passed': passed,
            'error': solution.get('error_name'),
            'source_solution_id': solution.get('id'),
        }])
        row.set_agent_trace([{
            'agent': 'learning_core_importer',
            'status': 'completed',
            'summary': '由历史练习记录生成',
        }])
        progress_by_trial_user[(trial.id, user.id)].append(row)
        stats.progress += 1
        if not passed:
            ensure_mistake(user.id, question, solution, fail_counts[(group_id, source_user_id, problem_id)])
            stats.mistakes += 1

    db.session.flush()
    for (trial_id, user_id), rows in progress_by_trial_user.items():
        part = TrialParticipation.query.filter_by(trial_id=trial_id, user_id=user_id).first()
        if not part:
            part = TrialParticipation(trial_id=trial_id, user_id=user_id)
            db.session.add(part)
        answered = len(rows)
        correct = sum(1 for row in rows if row.code_passed)
        total_questions = TrialQuestion.query.filter_by(trial_id=trial_id).count() or answered or 1
        part.status = 'completed'
        part.score = round(correct / total_questions * 100)
        part.joined_at = min((row.started_at or row.answered_at or utc_now()) for row in rows)
        part.completed_at = max((row.answered_at or utc_now()) for row in rows)
        stats.participations += 1

    db.session.commit()
    return {
        **preview,
        'imported': stats.__dict__,
        'teacher_username': TEACHER_USERNAME,
        'student_password': DEFAULT_STUDENT_PASSWORD,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Import masked learning_core SQL into A3.')
    parser.add_argument(
        '--source',
        type=Path,
        default=ROOT.parent / 'data' / 'learning_core_import' / 'learning_core_groups_masked_normal.sql',
    )
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    app = make_app()
    with app.app_context():
        db.create_all()
        result = import_data(args.source, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
