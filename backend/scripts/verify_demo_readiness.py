"""Run two persistent API-only demo rehearsals against the local database."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ['RESOURCE_TASK_SYNC'] = 'true'

from app import create_app


PROFILES = (
    (
        'student001',
        'student123',
        {
            'major_background': '非计算机专业大一',
            'knowledge_foundation': 'Python 零基础',
            'learning_goal': '掌握 Python 基础并完成校园小工具',
            'explanation_preference': '分步骤讲解和生活化案例',
            'mistake_pattern': '循环边界与缩进容易出错',
            'learning_pace': '每天 30 分钟',
            'interest_direction': '校园生活自动化',
        },
    ),
    (
        'student002',
        'student123',
        {
            'major_background': '软件工程专业',
            'knowledge_foundation': '具备 Python 基础',
            'learning_goal': '提升算法设计与复杂度分析能力',
            'explanation_preference': '先看代码，再做挑战题',
            'mistake_pattern': '复杂边界条件考虑不足',
            'learning_pace': '周末集中学习 3 小时',
            'interest_direction': '算法竞赛',
        },
    ),
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


def main():
    app = create_app('development')
    client = app.test_client()
    teacher_token = login(client, 'teacher001', 'teacher123')
    admin_token = login(client, 'admin', 'admin123')
    report = {
        'run_at': datetime.now().isoformat(timespec='seconds'),
        'rounds': [],
        'health': {},
    }

    for index, (username, password, dimensions) in enumerate(PROFILES, start=1):
        student_token = login(client, username, password)
        headers = auth(student_token)
        profile = require(client.put(
            '/api/v1/student/profile',
            headers=headers,
            json={'changes': dimensions, 'reason': 'demo_rehearsal'},
        ))
        task = require(client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=headers,
            json={
                'knowledge_key': 'loop',
                'force_regenerate': True,
                'idempotency_key': f'demo-rehearsal-{index}-{datetime.now().timestamp()}',
            },
        ), 201)
        pending = [
            item for item in task['resources']
            if item['review_status'] == 'pending_review'
        ]
        if len(task['resources']) != 5 or len(pending) != 1:
            raise RuntimeError(f'{username}: expected five resources and one pending review')

        require(client.post(
            '/api/v1/student/code-trial/runs',
            headers=headers,
            json={
                'question_id': f'demo-round-{index}-{datetime.now().timestamp()}',
                'question_title': '循环边界彩排题',
                'knowledge_key': 'loop',
                'topic': '循环结构',
                'cases': [{'label': '边界用例', 'passed': False, 'actual': '4', 'expected': '5'}],
            },
        ))
        recommendations = require(client.get(
            '/api/v1/student/recommendations',
            headers=headers,
        ))
        suggestion = recommendations['profile_update_suggestion']
        if not suggestion:
            raise RuntimeError(f'{username}: mistake did not create a profile suggestion')
        accepted = require(client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=headers,
            json={'action': 'accepted'},
        ))
        approved = require(client.put(
            f"/api/v1/teacher/personalized-resources/{pending[0]['id']}/review",
            headers=auth(teacher_token),
            json={'review_status': 'approved', 'reason': f'第 {index} 轮彩排核验通过'},
        ))
        resources = require(client.get(
            '/api/v1/student/personalized-resources?knowledge_key=loop',
            headers=headers,
        ))
        history = require(client.get(
            '/api/v1/student/resource-generation/tasks',
            headers=headers,
        ))
        report['rounds'].append({
            'round': index,
            'student': username,
            'profile_version_before_feedback': profile['version'],
            'profile_version_after_feedback': accepted['profile']['version'],
            'task_id': task['task_id'],
            'task_backend': task['backend'],
            'resource_count': len(task['resources']),
            'approved_resource_id': approved['id'],
            'visible_resource_count_after_review': resources['total'],
            'task_persisted_after_refresh': any(
                item['task_id'] == task['task_id'] for item in history['items']
            ),
        })

    report['health'] = {
        'application': require(client.get('/api/v1/health')),
        'ai': require(client.get('/api/v1/system/ai-health')),
        'admin_login_verified': bool(admin_token),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
