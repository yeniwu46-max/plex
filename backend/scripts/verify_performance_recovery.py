"""Verify task concurrency, idempotency, persistence, and stale recovery."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ['RESOURCE_TASK_SYNC'] = 'true'

from flask_jwt_extended import create_access_token

from app import create_app
from app.config import TestingConfig
from app.models import PersonalizedLearningResource, ResourceGenerationTask, User, db
from app.services.personalized_resource import PersonalizedResourceService


def percentile(values, ratio):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return round(ordered[index], 2)


def run(output: Path, requests: int = 8, workers: int = 4) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    database_path = output.parent / '.performance-recovery.db'
    if database_path.exists():
        database_path.unlink()
    TestingConfig.SQLALCHEMY_DATABASE_URI = f'sqlite:///{database_path.as_posix()}'
    TestingConfig.SQLALCHEMY_ECHO = False
    app = create_app('testing')
    with app.app_context():
        student = User.query.filter_by(username='student001').first()
        token = create_access_token(identity=str(student.id))
        student_id = student.id

    def submit(_):
        try:
            client = app.test_client()
            started = perf_counter()
            response = client.post(
                '/api/v1/student/resource-generation/tasks',
                headers={'Authorization': f'Bearer {token}'},
                json={
                    'knowledge_key': 'loop',
                    'idempotency_key': 'performance-shared-request',
                },
            )
            elapsed = (perf_counter() - started) * 1000
            body = response.get_json(silent=True) or {}
            return {
                'status': response.status_code,
                'elapsed_ms': round(elapsed, 2),
                'task_id': (body.get('data') or {}).get('task_id'),
                'backend': (body.get('data') or {}).get('backend'),
            }
        except Exception as exc:
            return {
                'status': 500,
                'elapsed_ms': None,
                'task_id': None,
                'backend': None,
                'error': type(exc).__name__,
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(submit, range(requests)))
    successes = [item for item in results if item['status'] == 201 and item['task_id']]
    latencies = [item['elapsed_ms'] for item in successes]
    task_ids = {item['task_id'] for item in successes}

    with app.app_context():
        completed = ResourceGenerationTask(
            task_id='recovery-completed',
            user_id=student_id,
            knowledge_key='loop',
            requested_types=['lesson_document'],
            status='completed',
            progress=100,
            request_fingerprint='completed',
        )
        stale = ResourceGenerationTask(
            task_id='recovery-stale',
            user_id=student_id,
            knowledge_key='loop',
            requested_types=['lesson_document'],
            status='running',
            progress=30,
            request_fingerprint='stale',
        )
        stale.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
        pending = ResourceGenerationTask(
            task_id='recovery-pending',
            user_id=student_id,
            knowledge_key='loop',
            requested_types=['lesson_document'],
            status='pending',
            progress=0,
            request_fingerprint='pending',
        )
        db.session.add_all([completed, stale, pending])
        db.session.commit()
        recovery = PersonalizedResourceService.recover_stale_tasks(app)
        db.session.expire_all()
        stale_status = ResourceGenerationTask.query.filter_by(task_id='recovery-stale').first().status
        completed_status = ResourceGenerationTask.query.filter_by(task_id='recovery-completed').first().status
        generated_resources = (
            PersonalizedLearningResource.query.filter(
                PersonalizedLearningResource.generation_task_id.in_(task_ids)
            ).count()
            if task_ids
            else 0
        )

    success_rate = round((len(successes) / requests) * 100, 2)
    report = {
        'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'configuration': {'requests': requests, 'workers': workers, 'database': 'isolated SQLite'},
        'metrics': {
            'success_rate': success_rate,
            'p50_ms': percentile(latencies, 0.5) if latencies else None,
            'p95_ms': percentile(latencies, 0.95) if latencies else None,
            'idempotency_rate': round((len(successes) / max(len(task_ids), 1)) / max(len(successes), 1) * 100, 2),
            'unique_task_count': len(task_ids),
            'resource_count': generated_resources,
            'fallback_count': sum(item['backend'] == 'local_rules' for item in successes),
        },
        'recovery': {
            **recovery,
            'stale_running_status': stale_status,
            'completed_status': completed_status,
        },
        'passed': (
            success_rate >= 95
            and len(task_ids) == 1
            and generated_resources == 5
            and stale_status == 'failed'
            and completed_status == 'completed'
        ),
        'requests': results,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    if database_path.exists():
        database_path.unlink()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports/a3-next-stage/performance-recovery.json',
    )
    parser.add_argument('--requests', type=int, default=8)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    result = run(args.output, args.requests, args.workers)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
