"""Run three persistent student-feedback loops and write an auditable report."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ['RESOURCE_TASK_SYNC'] = 'true'

from app import create_app
from app.services.student_progress import DOMAIN_CATALOG


PROFILE = {
    'major_background': '计算机专业大一',
    'knowledge_foundation': 'Python 零基础',
    'learning_goal': '掌握 Python 基础并完成校园工具',
    'explanation_preference': '代码案例优先、分步骤讲解',
    'mistake_pattern': '尚未形成稳定模式',
    'learning_pace': '每天 30 分钟',
    'interest_direction': '数据处理与校园项目',
}
ROUNDS = (
    ('loop', '循环边界'),
    ('range', 'range 边界'),
    ('cond', '条件分支边界'),
)


def require(response, expected=200):
    body = response.get_json() or {}
    if response.status_code != expected or body.get('code') != 0:
        raise RuntimeError(
            f'{response.request.path}: HTTP {response.status_code} '
            f'{body.get("message") or body}'
        )
    return body['data']


def login(client, username, password):
    return require(client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
    ))['access_token']


def auth(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


def timed(call):
    started = perf_counter()
    value = call()
    return value, round((perf_counter() - started) * 1000)


def reject_pending(client, headers):
    pending = require(client.get(
        '/api/v1/student/profile/suggestions?status=pending',
        headers=headers,
    ))
    for item in pending['items']:
        require(client.put(
            f"/api/v1/student/profile/suggestions/{item['id']}",
            headers=headers,
            json={'action': 'rejected'},
        ))


def domain_key_for(knowledge_key: str) -> str:
    return next(
        domain['key']
        for domain in DOMAIN_CATALOG
        if knowledge_key in domain['knowledge_keys']
    )


def run(output: Path) -> dict:
    app = create_app('development')
    client = app.test_client()
    student_token = login(client, 'student001', 'student123')
    teacher_token = login(client, 'teacher001', 'teacher123')
    student_headers = auth(student_token)
    teacher_headers = auth(teacher_token)
    reject_pending(client, student_headers)

    report = {
        'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'round_count': len(ROUNDS),
        'rounds': [],
        'summary': {},
    }
    for index, (knowledge_key, title) in enumerate(ROUNDS, start=1):
        timings = {}
        profile, timings['profile_reset_ms'] = timed(lambda: require(client.put(
            '/api/v1/student/profile',
            headers=student_headers,
            json={
                'changes': PROFILE,
                'reason': f'feedback_loop_round_{index}_baseline',
            },
        )))
        reject_pending(client, student_headers)

        task, timings['resource_generation_ms'] = timed(lambda: require(client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=student_headers,
            json={
                'knowledge_key': knowledge_key,
                'force_regenerate': True,
                'idempotency_key': (
                    f'feedback-loop-{index}-{datetime.now().timestamp()}'
                ),
            },
        ), 201))
        pending_resource = next(
            item for item in task['resources']
            if item['review_status'] == 'pending_review'
        )
        visible_before_review = require(client.get(
            f'/api/v1/student/personalized-resources?knowledge_key={knowledge_key}',
            headers=student_headers,
        ))
        if pending_resource['id'] in {
            item['id'] for item in visible_before_review['items']
        }:
            raise RuntimeError('pending resource leaked to student listing')

        require(client.post(
            '/api/v1/student/code-trial/runs',
            headers=student_headers,
            json={
                'question_id': f'feedback-accept-{index}-{datetime.now().timestamp()}',
                'question_title': title,
                'knowledge_key': knowledge_key,
                'topic': title,
                'cases': [{
                    'label': '边界用例',
                    'passed': False,
                    'actual': '4',
                    'expected': '5',
                }],
            },
        ))
        before = require(client.get(
            '/api/v1/student/recommendations',
            headers=student_headers,
        ))
        path_before = require(client.get(
            '/api/v1/student/learning-path',
            headers=student_headers,
        ))
        suggestion = before['profile_update_suggestion']
        if not suggestion:
            raise RuntimeError(f'round {index}: no profile suggestion')
        before_ids = [item['id'] for item in before['personalized_resources']]
        if not before_ids or before['personalized_resources'][0]['resource_type'] != 'coding_lab':
            raise RuntimeError(f'round {index}: unexpected baseline recommendation order')

        accepted, timings['suggestion_accept_ms'] = timed(lambda: require(client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=student_headers,
            json={'action': 'accepted'},
        )))
        after = require(client.get(
            '/api/v1/student/recommendations',
            headers=student_headers,
        ))
        path_after = require(client.get(
            '/api/v1/student/learning-path',
            headers=student_headers,
        ))
        after_ids = [item['id'] for item in after['personalized_resources']]
        if accepted['profile']['version'] != profile['version'] + 1:
            raise RuntimeError(f'round {index}: profile version did not increment once')
        if before_ids == after_ids:
            raise RuntimeError(f'round {index}: recommendation order did not change')
        if after['personalized_resources'][0]['resource_type'] != 'exercise_set':
            raise RuntimeError(f'round {index}: exercise resource was not prioritized')

        domain_key = domain_key_for(knowledge_key)
        before_domain = next(
            item for item in path_before['domains'] if item['key'] == domain_key
        )
        after_domain = next(
            item for item in path_after['domains'] if item['key'] == domain_key
        )
        if (
            before_domain['recommended_resource_ids']
            == after_domain['recommended_resource_ids']
        ):
            raise RuntimeError(f'round {index}: learning path resource order did not change')
        if '近期薄弱点' not in after_domain['recommendation_reason']:
            raise RuntimeError(f'round {index}: learning path reason lacks profile evidence')

        require(client.post(
            '/api/v1/student/code-trial/runs',
            headers=student_headers,
            json={
                'question_id': f'feedback-reject-{index}-{datetime.now().timestamp()}',
                'question_title': f'{title}复测',
                'knowledge_key': knowledge_key,
                'topic': title,
                'cases': [{
                    'label': '复测边界',
                    'passed': False,
                    'actual': '0',
                    'expected': '1',
                }],
            },
        ))
        pending = require(client.get(
            '/api/v1/student/profile/suggestions?status=pending',
            headers=student_headers,
        ))
        if not pending['items']:
            raise RuntimeError(f'round {index}: no second suggestion to reject')
        version_before_reject = after['profile_version']
        rejected = require(client.put(
            f"/api/v1/student/profile/suggestions/{pending['items'][0]['id']}",
            headers=student_headers,
            json={'action': 'rejected'},
        ))
        after_reject = require(client.get(
            '/api/v1/student/recommendations',
            headers=student_headers,
        ))
        if rejected['profile'] is not None:
            raise RuntimeError(f'round {index}: rejected suggestion changed profile')
        if after_reject['profile_version'] != version_before_reject:
            raise RuntimeError(f'round {index}: reject changed profile version')

        approved, timings['teacher_review_ms'] = timed(lambda: require(client.put(
            f"/api/v1/teacher/personalized-resources/{pending_resource['id']}/review",
            headers=teacher_headers,
            json={
                'review_status': 'approved',
                'reason': f'反馈闭环第 {index} 轮教师核验通过',
            },
        )))
        visible_after_review = require(client.get(
            f'/api/v1/student/personalized-resources?knowledge_key={knowledge_key}',
            headers=student_headers,
        ))
        history = require(client.get(
            '/api/v1/student/resource-generation/tasks',
            headers=student_headers,
        ))
        report['rounds'].append({
            'round': index,
            'knowledge_key': knowledge_key,
            'profile_version_before_accept': profile['version'],
            'profile_version_after_accept': accepted['profile']['version'],
            'profile_version_after_reject': after_reject['profile_version'],
            'recommendation_ids_before': before_ids,
            'recommendation_ids_after': after_ids,
            'preferred_types_after': after['recommendation_context'][
                'preferred_resource_types'
            ],
            'path_resource_ids_before': before_domain['recommended_resource_ids'],
            'path_resource_ids_after': after_domain['recommended_resource_ids'],
            'path_reason_after': after_domain['recommendation_reason'],
            'suggestion_accepted_id': suggestion['id'],
            'suggestion_rejected_id': pending['items'][0]['id'],
            'task_id': task['task_id'],
            'task_backend': task['backend'],
            'task_persisted': any(
                item['task_id'] == task['task_id'] for item in history['items']
            ),
            'approved_resource_id': approved['id'],
            'approved_resource_visible': approved['id'] in {
                item['id'] for item in visible_after_review['items']
            },
            'timings_ms': timings,
        })

    report['summary'] = {
        'rounds_passed': len(report['rounds']),
        'all_profile_versions_incremented': all(
            item['profile_version_after_accept']
            == item['profile_version_before_accept'] + 1
            for item in report['rounds']
        ),
        'all_rejections_preserved_profile': all(
            item['profile_version_after_reject']
            == item['profile_version_after_accept']
            for item in report['rounds']
        ),
        'all_recommendations_changed': all(
            item['recommendation_ids_before'] != item['recommendation_ids_after']
            for item in report['rounds']
        ),
        'all_paths_changed': all(
            item['path_resource_ids_before'] != item['path_resource_ids_after']
            for item in report['rounds']
        ),
        'all_tasks_persisted': all(item['task_persisted'] for item in report['rounds']),
        'all_reviews_visible': all(
            item['approved_resource_visible'] for item in report['rounds']
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports' / 'feedback-loop-three-rounds.json',
    )
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0 if (
        report['summary']['rounds_passed'] == 3
        and all(
            value is True
            for key, value in report['summary'].items()
            if key != 'rounds_passed'
        )
    ) else 1


if __name__ == '__main__':
    raise SystemExit(main())
