"""Create a deterministic pre/post learning-effect evidence report."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.config import TestingConfig
from app.models import (
    Class,
    ResourceGenerationTask,
    Role,
    Trial,
    TrialQuestion,
    TrialQuestionProgress,
    User,
    db,
)
from app.services.evaluation import EvaluationService


def run(output: Path) -> dict:
    TestingConfig.SQLALCHEMY_ECHO = False
    app = create_app('testing')
    with app.app_context():
        teacher = User.query.filter_by(username='teacher001').first()
        student_role = Role.query.filter_by(name='student').first()
        student = User(
            username='effect-report-student',
            email='effect-report@example.com',
            password_hash='not-used',
            role_id=student_role.id,
        )
        db.session.add(student)
        db.session.flush()
        cls = Class(name='Effect Evidence', teacher_id=teacher.id, grade_level=1)
        db.session.add(cls)
        db.session.flush()
        student.class_id = cls.id
        trial = Trial(
            class_id=cls.id,
            teacher_id=teacher.id,
            title='Loop Effect Evidence',
            trial_type='solo',
            knowledge_key='loop',
            status='ended',
        )
        db.session.add(trial)
        db.session.flush()
        intervention = datetime.now(timezone.utc).replace(tzinfo=None)
        task = ResourceGenerationTask(
            task_id='learning-effect-deterministic',
            user_id=student.id,
            knowledge_key='loop',
            requested_types=['lesson_document', 'exercise_set'],
            status='completed',
            progress=100,
            profile_version=3,
            backend='local_rules',
            completed_at=intervention,
        )
        task.created_at = intervention
        db.session.add(task)
        db.session.flush()
        for index in range(6):
            question = TrialQuestion(
                trial_id=trial.id,
                sort_order=index,
                stem=f'loop boundary {index}',
                options=['A', 'B'],
                correct_index=0,
                knowledge_key='loop',
            )
            db.session.add(question)
            db.session.flush()
            after = index >= 3
            db.session.add(TrialQuestionProgress(
                user_id=student.id,
                question_id=question.id,
                status='completed',
                selected_index=0 if after else 1,
                is_correct=after,
                answered_at=intervention + (
                    timedelta(minutes=index + 1) if after else -timedelta(minutes=index + 1)
                ),
            ))
        db.session.commit()
        result = EvaluationService.get_learning_effect(student.id, task.task_id)
        report = {
            'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'scenario': 'three incorrect attempts -> personalized resources -> three correct attempts',
            'passed': (
                result['status'] == 'sufficient'
                and result['before']['correct_rate'] == 0.0
                and result['after']['correct_rate'] == 100.0
                and result['delta']['mistake_count'] == -3
            ),
            'result': result,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports/a3-next-stage/learning-effect.json',
    )
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
