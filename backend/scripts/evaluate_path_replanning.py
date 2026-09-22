"""End-to-end local proof of the exam -> mistake -> SM-2 -> path replan loop."""
from __future__ import annotations

import json
from pathlib import Path

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, User, db
from app.services.learning_path import LearningPathService


def main() -> dict:
    app = create_app('testing')
    checks: dict[str, bool] = {}
    details: dict = {}
    with app.app_context():
        role = Role.query.filter_by(name='student').first()
        user = User(
            username='iflytek990-path-eval',
            email='iflytek990-path-eval@example.com',
            password_hash=generate_password_hash('student123'),
            real_name='990路径评测学生',
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        client = app.test_client()

        before = LearningPathService.plan(user.id, focus_node_id='loop-for')
        before_ids = [row['id'] for row in before.get('ordered_nodes') or []]
        failed = client.post(
            '/api/v1/student/code-trial/runs',
            headers=headers,
            json={
                'question_id': 'iflytek990-path-eval',
                'question_title': '循环边界路径评测',
                'knowledge_key': 'loop',
                'cases': [{'label': '边界样例', 'passed': False}],
            },
        )
        checks['mistake_created'] = failed.status_code == 200
        mistake_id = ((failed.get_json() or {}).get('data') or {}).get('record', {}).get('id')

        due = client.get('/api/v1/student/mistakes/reviews/due', headers=headers)
        due_items = ((due.get_json() or {}).get('data') or {}).get('items') or []
        checks['due_queue_contains_mistake'] = any(row.get('id') == mistake_id for row in due_items)

        reviewed = client.post(
            f'/api/v1/student/mistakes/{mistake_id}/review',
            headers=headers,
            json={'quality': 5},
        ) if mistake_id else None
        reviewed_data = ((reviewed.get_json() if reviewed else {}) or {}).get('data') or {}
        checks['sm2_review_saved'] = bool(reviewed and reviewed.status_code == 200)
        checks['profile_updated'] = bool((reviewed_data.get('student_profile_update') or {}).get('version', 0) >= 2)
        checks['graph_mastery_updated'] = (reviewed_data.get('knowledge_graph_update') or {}).get('status') == 'learning'
        checks['path_replanned'] = (reviewed_data.get('learning_path_update') or {}).get('replanned') is True
        after = LearningPathService.plan(user.id, focus_node_id='loop-for')
        after_ids = [row['id'] for row in after.get('ordered_nodes') or []]
        details = {
            'before_next_best_action': before.get('next_best_action'),
            'after_next_best_action': after.get('next_best_action'),
            'before_node_count': len(before_ids),
            'after_node_count': len(after_ids),
            'review_schedule': (reviewed_data.get('record') or {}).get('review_schedule'),
            'learning_path_update': reviewed_data.get('learning_path_update'),
        }
        checks['path_plan_remains_valid'] = bool(after_ids) and set(after_ids) == set(before_ids)
        passed = all(checks.values())
        report = {
            'benchmark': 'iflytek-990-learning-path-replanning-e2e',
            'backend': 'local_rules',
            'passed': passed,
            'checks': checks,
            'details': details,
            'note': '本报告证明本地闭环行为，不替代真实讯飞模型或真实课堂效果证据。',
        }
        output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-path-replanning-20260828.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        db.session.remove()
        db.drop_all()
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == '__main__':
    raise SystemExit(0 if main()['passed'] else 1)
