"""Personalized five-resource generation with progress and review controls."""
from __future__ import annotations

import os
import hashlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from flask import current_app
from jsonschema import Draft202012Validator

from app.data.knowledge_catalog import KNOWLEDGE_UNIVERSE
from app.models import PersonalizedLearningResource, ResourceGenerationTask, db
from app.services.iflytek_spark import IflytekSparkService
from app.services.question_generator import QuestionGenerator
from app.services.student_profile import StudentProfileService

RESOURCE_TYPES = (
    'lesson_document',
    'mind_map',
    'exercise_set',
    'extended_reading',
    'coding_lab',
)
OPTIONAL_RESOURCE_TYPES = ('audio_explanation',)
ALLOWED_RESOURCE_TYPES = RESOURCE_TYPES + OPTIONAL_RESOURCE_TYPES
PIPELINE_STEPS = (
    ('profile_interpreter', 10),
    ('knowledge_retriever', 25),
    ('instructional_designer', 40),
    ('resource_generator', 75),
    ('quality_reviewer', 90),
    ('path_planner', 100),
)
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='plex-resource')

POINTS = {
    point['key']: point['label']
    for domain in KNOWLEDGE_UNIVERSE
    for point in domain['points']
}
DOCUMENT_IDS = {
    'intro': 'python-stage1-program-structure',
    'comment': 'python-stage1-comments',
    'var': 'python-stage1-variables-types',
    'io': 'python-stage1-input-output',
    'ops': 'python-stage2-operators',
    'cond': 'python-stage2-condition',
    'loop': 'python-stage2-loop',
    'range': 'python-stage2-range',
    'str': 'python-stage3-string',
    'list': 'python-stage3-list',
    'dict': 'python-stage3-dict',
    'func': 'python-stage4-function',
    'except': 'python-stage4-exception',
    'file': 'python-stage4-file',
    'algo-sum': 'python-stage4-algorithm',
    'algo-search': 'python-stage4-algorithm',
}
VALID_DOCUMENT_IDS = frozenset(DOCUMENT_IDS.values())
RESOURCE_SCHEMAS = {
    'lesson_document': {
        'type': 'object', 'required': ['format', 'markdown'],
        'properties': {'format': {'const': 'markdown'}, 'markdown': {'type': 'string', 'minLength': 20}},
        'additionalProperties': True,
    },
    'mind_map': {
        'type': 'object', 'required': ['format', 'root', 'children'],
        'properties': {
            'format': {'const': 'tree'}, 'root': {'type': 'string', 'minLength': 1},
            'children': {'type': 'array', 'minItems': 2},
        },
        'additionalProperties': True,
    },
    'exercise_set': {
        'type': 'object', 'required': ['format', 'questions'],
        'properties': {
            'format': {'const': 'questions'},
            'questions': {
                'type': 'array', 'minItems': 2,
                'items': {
                    'type': 'object', 'required': ['level', 'question'],
                    'properties': {
                        'level': {'type': 'string', 'minLength': 1},
                        'question': {'type': 'string', 'minLength': 5},
                    },
                },
            },
        },
        'additionalProperties': True,
    },
    'extended_reading': {
        'type': 'object', 'required': ['format', 'markdown'],
        'properties': {'format': {'const': 'markdown'}, 'markdown': {'type': 'string', 'minLength': 20}},
        'additionalProperties': True,
    },
    'coding_lab': {
        'type': 'object', 'required': ['format', 'scenario', 'starter_code', 'checks'],
        'properties': {
            'format': {'const': 'coding_lab'},
            'scenario': {'type': 'string', 'minLength': 10},
            'starter_code': {'type': 'string'},
            'checks': {'type': 'array', 'minItems': 1},
        },
        'additionalProperties': True,
    },
    'audio_explanation': {
        'type': 'object', 'required': ['format', 'transcript'],
        'properties': {'format': {'type': 'string'}, 'transcript': {'type': 'string', 'minLength': 10}},
        'additionalProperties': True,
    },
}


class PersonalizedResourceService:
    @staticmethod
    def _safe_text(value: str) -> bool:
        lowered = value.lower()
        blocked = ('色情', '赌博', '毒品', '自杀', 'terrorism', 'porn')
        return not any(item in lowered for item in blocked)

    @staticmethod
    def _validate_request(knowledge_key: str, resource_types: list[str]):
        if knowledge_key not in POINTS:
            raise ValueError('knowledge_key超出Python课程范围')
        if not resource_types:
            raise ValueError('resource_types不能为空')
        invalid = [item for item in resource_types if item not in ALLOWED_RESOURCE_TYPES]
        if invalid:
            raise ValueError('不支持的资源类型：' + ','.join(invalid))

    @staticmethod
    def _steps():
        return [
            {'agent': agent, 'status': 'pending', 'latency_ms': None}
            for agent, _ in PIPELINE_STEPS
        ]

    @staticmethod
    def executor_status():
        return {'backend': 'in_process', 'max_workers': 2, 'available': True}

    @staticmethod
    def recover_stale_tasks(app=None):
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        rows = ResourceGenerationTask.query.filter(
            ResourceGenerationTask.status == 'running',
            ResourceGenerationTask.updated_at < cutoff,
        ).all()
        for row in rows:
            row.status = 'failed'
            row.error = '任务因服务重启或超时中断，可重新生成'
            row.current_agent = None
            row.recoverable = True
        if rows:
            db.session.commit()
        pending = ResourceGenerationTask.query.filter_by(status='pending').all()
        if app and not app.config.get('TESTING'):
            for row in pending:
                _EXECUTOR.submit(PersonalizedResourceService.run_task, app, row.task_id)
        return {'failed_stale': len(rows), 'resubmitted_pending': len(pending) if app else 0}

    @staticmethod
    def _fingerprint(user_id: int, profile_version: int, knowledge_key: str, resource_types: list[str]) -> str:
        raw = json.dumps({
            'user_id': user_id,
            'profile_version': profile_version,
            'knowledge_key': knowledge_key,
            'resource_types': sorted(resource_types),
        }, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def create_task(user_id: int, payload: dict) -> dict:
        PersonalizedResourceService.recover_stale_tasks()
        knowledge_key = str(payload.get('knowledge_key') or '').strip()
        resource_types = payload.get('resource_types') or list(RESOURCE_TYPES)
        resource_types = list(dict.fromkeys(resource_types))
        PersonalizedResourceService._validate_request(knowledge_key, resource_types)
        if not PersonalizedResourceService._safe_text(str(payload)):
            raise ValueError('输入包含不允许的内容')

        profile = StudentProfileService.get_or_create(user_id)
        profile_version = profile.version if profile.id else 0
        fingerprint = PersonalizedResourceService._fingerprint(
            user_id, profile_version, knowledge_key, resource_types
        )
        idempotency_key = str(payload.get('idempotency_key') or '').strip()[:100] or None

        if not payload.get('force_regenerate'):
            active = ResourceGenerationTask.query.filter(
                ResourceGenerationTask.user_id == user_id,
                ResourceGenerationTask.status.in_(('pending', 'running', 'completed')),
                ResourceGenerationTask.created_at >= datetime.utcnow() - timedelta(minutes=15),
                (
                    (ResourceGenerationTask.idempotency_key == idempotency_key)
                    if idempotency_key
                    else (ResourceGenerationTask.request_fingerprint == fingerprint)
                ),
            ).order_by(ResourceGenerationTask.id.desc()).first()
            if active:
                return PersonalizedResourceService.get_task(user_id, active.task_id)

        row = ResourceGenerationTask(
            task_id='rg_' + uuid.uuid4().hex[:20],
            user_id=user_id,
            knowledge_key=knowledge_key,
            requested_types=resource_types,
            steps=PersonalizedResourceService._steps(),
            retry_of=payload.get('retry_of'),
            profile_version=profile_version,
            request_fingerprint=fingerprint,
            idempotency_key=idempotency_key,
            recoverable=True,
        )
        db.session.add(row)
        db.session.commit()

        app = current_app._get_current_object()
        if app.config.get('TESTING') or os.getenv('RESOURCE_TASK_SYNC', '').lower() == 'true':
            PersonalizedResourceService.run_task(app, row.task_id)
            db.session.expire_all()
        else:
            _EXECUTOR.submit(PersonalizedResourceService.run_task, app, row.task_id)
        return PersonalizedResourceService.get_task(user_id, row.task_id)

    @staticmethod
    def _set_step(row: ResourceGenerationTask, index: int, status: str, latency_ms=None):
        steps = [dict(item) for item in (row.steps or PersonalizedResourceService._steps())]
        steps[index]['status'] = status
        steps[index]['latency_ms'] = latency_ms
        row.steps = steps
        row.current_agent = steps[index]['agent'] if status == 'running' else row.current_agent
        db.session.commit()

    @staticmethod
    def _profile_snapshot(user_id: int) -> dict:
        profile = StudentProfileService.get_or_create(user_id).to_dict()
        return {
            key: value.get('value')
            for key, value in (profile.get('dimensions') or {}).items()
            if value.get('value')
        }

    @staticmethod
    def _citation(knowledge_key: str) -> dict:
        return {
            'document_id': DOCUMENT_IDS[knowledge_key],
            'title': f"《Python程序设计基础》：{POINTS[knowledge_key]}",
            'section': knowledge_key,
            'snippet': f'{POINTS[knowledge_key]}课程知识库中的概念、示例与常见错误。',
        }

    @staticmethod
    def _citations_are_valid(citations: list[dict]) -> bool:
        return bool(citations) and all(
            isinstance(item, dict)
            and item.get('document_id') in VALID_DOCUMENT_IDS
            for item in citations
        )

    @staticmethod
    def _risk_reasons(item: dict, knowledge_key: str) -> list[str]:
        risks = []
        resource_type = item.get('resource_type')
        content = item.get('content')
        confidence = float(item.get('confidence') or 0)
        citations = item.get('citations') or []
        if confidence < 0.8:
            risks.append('low_confidence')
        expected_document = DOCUMENT_IDS[knowledge_key]
        if (
            not PersonalizedResourceService._citations_are_valid(citations)
            or any(
                citation.get('document_id') != expected_document
                or citation.get('section') != knowledge_key
                for citation in citations
            )
        ):
            risks.append('invalid_citation')
        schema = RESOURCE_SCHEMAS.get(resource_type)
        if not schema or not isinstance(content, dict) or list(Draft202012Validator(schema).iter_errors(content)):
            risks.append('schema_invalid')
        serialized = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else str(content)
        if not PersonalizedResourceService._safe_text(serialized):
            risks.append('safety_blocked')
        if knowledge_key not in POINTS:
            risks.append('out_of_scope')
        if resource_type == 'exercise_set' and isinstance(content, dict):
            questions = [
                str(row.get('question') or '').strip()
                for row in content.get('questions', [])
                if isinstance(row, dict)
            ]
            if len(set(questions)) != len(questions):
                risks.append('schema_invalid')
        if resource_type == 'coding_lab' and isinstance(content, dict):
            try:
                compile(str(content.get('starter_code') or ''), '<coding_lab>', 'exec')
            except SyntaxError:
                risks.append('schema_invalid')
        return list(dict.fromkeys(risks))

    @staticmethod
    def _local_resources(knowledge_key: str, resource_types: list[str], profile: dict) -> list[dict]:
        label = POINTS[knowledge_key]
        preference = profile.get('explanation_preference') or '分步骤讲解'
        interest = profile.get('interest_direction') or '校园学习'
        pace = profile.get('learning_pace') or '每次15分钟'
        common = {
            'difficulty': 40 if '零基础' in str(profile.get('knowledge_foundation')) else 55,
            'estimated_minutes': 15,
            'recommendation_reason': f'根据你的讲解偏好“{preference}”、学习节奏“{pace}”生成。',
            'citations': [PersonalizedResourceService._citation(knowledge_key)],
            'confidence': 0.88,
        }
        builders = {
            'lesson_document': {
                'title': f'{label}个性化讲解',
                'content': {
                    'format': 'markdown',
                    'markdown': f'# {label}\n\n采用{preference}。\n\n## 核心概念\n围绕 {label} 理解语法、执行过程和适用场景。\n\n## 示例\n```python\nprint(\"{label}\")\n```\n\n## 常见错误\n注意缩进、边界与数据类型。',
                },
            },
            'mind_map': {
                'title': f'{label}思维导图',
                'content': {
                    'format': 'tree',
                    'root': label,
                    'children': [
                        {'label': '概念'},
                        {'label': '语法'},
                        {'label': '示例'},
                        {'label': '常见错误'},
                    ],
                },
            },
            'exercise_set': {
                'title': f'{label}分层题库',
                'content': {
                    'format': 'questions',
                    'questions': [
                        {'level': '基础', 'question': f'解释 {label} 的基本作用。'},
                        {'level': '进阶', 'question': f'使用 {label} 解决一个与{interest}有关的小任务。'},
                    ],
                },
            },
            'extended_reading': {
                'title': f'{label}拓展阅读',
                'content': {
                    'format': 'markdown',
                    'markdown': f'# 从 {label} 到真实项目\n\n结合你的兴趣“{interest}”，观察该知识点如何用于数据处理、自动化或小游戏。',
                },
            },
            'coding_lab': {
                'title': f'{label}代码实操',
                'content': {
                    'format': 'coding_lab',
                    'scenario': f'围绕{interest}完成一个使用{label}的程序。',
                    'starter_code': '# 在这里编写代码\n',
                    'checks': ['程序可运行', f'正确使用{label}', '至少包含一个测试样例'],
                },
            },
            'audio_explanation': {
                'title': f'{label}语音讲解',
                'content': {
                    'format': 'audio_fallback',
                    'transcript': f'这是关于{label}的简短讲解。当前语音服务量不可用，展示文本降级内容。',
                },
                'content_url': None,
            },
        }
        return [{**common, **builders[item], 'resource_type': item} for item in resource_types]

    @staticmethod
    def _spark_resources(knowledge_key: str, resource_types: list[str], profile: dict) -> list[dict]:
        system = (
            '你是Python程序设计基础课程资源生成器。只输出JSON对象，包含resources数组。'
            '每项必须有resource_type,title,content,difficulty,estimated_minutes,recommendation_reason,confidence。'
            'resource_type只能来自请求列表，禁止引用课程范围外事实。'
        )
        result = IflytekSparkService.chat_json(
            system,
            str({
                'knowledge_key': knowledge_key,
                'knowledge_label': POINTS[knowledge_key],
                'resource_types': resource_types,
                'profile': profile,
                'required_citation': PersonalizedResourceService._citation(knowledge_key),
            }),
            timeout=45,
        )
        rows = result.get('resources')
        if not isinstance(rows, list):
            raise ValueError('spark_resources_invalid')
        by_type = {item.get('resource_type'): item for item in rows if isinstance(item, dict)}
        if any(item not in by_type for item in resource_types):
            raise ValueError('spark_resources_incomplete')
        return [
            {
                **by_type[item],
                'resource_type': item,
                'citations': [PersonalizedResourceService._citation(knowledge_key)],
            }
            for item in resource_types
        ]

    @staticmethod
    def run_task(app, task_id: str):
        with app.app_context():
            claimed = ResourceGenerationTask.query.filter_by(
                task_id=task_id, status='pending'
            ).update({
                ResourceGenerationTask.status: 'running',
                ResourceGenerationTask.started_at: datetime.utcnow(),
            }, synchronize_session=False)
            db.session.commit()
            if claimed != 1:
                return
            row = ResourceGenerationTask.query.filter_by(task_id=task_id).first()
            try:
                profile = PersonalizedResourceService._profile_snapshot(row.user_id)
                for index, (agent, progress) in enumerate(PIPELINE_STEPS):
                    started = datetime.utcnow()
                    PersonalizedResourceService._set_step(row, index, 'running')
                    if agent == 'resource_generator':
                        try:
                            generated = PersonalizedResourceService._spark_resources(
                                row.knowledge_key, row.requested_types, profile
                            )
                            row.backend = 'iflytek_spark'
                        except Exception as exc:
                            generated = PersonalizedResourceService._local_resources(
                                row.knowledge_key, row.requested_types, profile
                            )
                            row.backend = 'local_rules'
                            row.fallback_reason = str(exc)[:255]
                        PersonalizedLearningResource.query.filter_by(
                            generation_task_id=row.task_id
                        ).delete()
                        for item in generated:
                            confidence = min(max(float(item.get('confidence', 0.8)), 0), 1)
                            item['difficulty'] = min(max(int(item.get('difficulty') or 50), 0), 100)
                            item['estimated_minutes'] = min(max(int(item.get('estimated_minutes') or 15), 1), 180)
                            citations = item.get('citations') or []
                            risk_reasons = PersonalizedResourceService._risk_reasons(item, row.knowledge_key)
                            review_status = 'approved' if not risk_reasons else 'pending_review'
                            db.session.add(PersonalizedLearningResource(
                                user_id=row.user_id,
                                generation_task_id=row.task_id,
                                knowledge_key=row.knowledge_key,
                                knowledge_label=POINTS[row.knowledge_key],
                                resource_type=item['resource_type'],
                                title=str(item.get('title') or POINTS[row.knowledge_key])[:200],
                                content=item.get('content') if isinstance(item.get('content'), dict)
                                else {'format': 'markdown', 'markdown': str(item.get('content') or '')},
                                content_url=item.get('content_url'),
                                difficulty=item['difficulty'],
                                estimated_minutes=item['estimated_minutes'],
                                profile_snapshot=profile,
                                recommendation_reason=str(item.get('recommendation_reason') or '根据画像与薄弱点生成'),
                                citations=citations,
                                confidence=confidence,
                                review_status=review_status,
                                risk_reasons=risk_reasons,
                                generator_agent=agent,
                                backend=row.backend,
                            ))
                    row.progress = max(row.progress, progress)
                    elapsed = int((datetime.utcnow() - started).total_seconds() * 1000)
                    PersonalizedResourceService._set_step(row, index, 'completed', elapsed)
                row.status = 'completed'
                row.progress = 100
                row.current_agent = None
                row.completed_at = datetime.utcnow()
                row.recoverable = False
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                row = ResourceGenerationTask.query.filter_by(task_id=task_id).first()
                row.status = 'failed'
                row.error = str(exc)[:500]
                row.current_agent = None
                row.recoverable = True
                db.session.commit()

    @staticmethod
    def get_task(user_id: int, task_id: str) -> dict:
        row = ResourceGenerationTask.query.filter_by(task_id=task_id, user_id=user_id).first()
        if not row:
            raise LookupError('任务不存在')
        resources = PersonalizedLearningResource.query.filter_by(
            generation_task_id=task_id
        ).order_by(PersonalizedLearningResource.id).all()
        return row.to_dict([item.to_dict() for item in resources])

    @staticmethod
    def retry(user_id: int, task_id: str) -> dict:
        row = ResourceGenerationTask.query.filter_by(task_id=task_id, user_id=user_id).first()
        if not row:
            raise LookupError('任务不存在')
        if row.status != 'failed':
            raise ValueError('仅失败任务可以重试')
        return PersonalizedResourceService.create_task(user_id, {
            'knowledge_key': row.knowledge_key,
            'resource_types': row.requested_types,
            'force_regenerate': True,
            'retry_of': row.task_id,
        })

    @staticmethod
    def list_tasks(user_id: int, page: int = 1, page_size: int = 20) -> dict:
        query = ResourceGenerationTask.query.filter_by(user_id=user_id).order_by(
            ResourceGenerationTask.created_at.desc()
        )
        pagination = query.paginate(
            page=max(1, page),
            per_page=min(max(page_size, 1), 100),
            error_out=False,
        )
        return {
            'items': [
                PersonalizedResourceService.get_task(user_id, row.task_id)
                for row in pagination.items
            ],
            'total': pagination.total,
            'page': pagination.page,
            'page_size': pagination.per_page,
        }

    @staticmethod
    def list_student(user_id: int, args) -> dict:
        query = PersonalizedLearningResource.query.filter_by(user_id=user_id, review_status='approved')
        if args.get('knowledge_key'):
            query = query.filter_by(knowledge_key=args['knowledge_key'])
        if args.get('resource_type'):
            query = query.filter_by(resource_type=args['resource_type'])
        rows = query.order_by(PersonalizedLearningResource.created_at.desc()).all()
        return {'items': [row.to_dict() for row in rows], 'total': len(rows)}

    @staticmethod
    def list_review(status: str = 'pending_review') -> dict:
        query = PersonalizedLearningResource.query
        if status:
            query = query.filter_by(review_status=status)
        rows = query.order_by(PersonalizedLearningResource.created_at.desc()).all()
        return {'items': [row.to_dict() for row in rows], 'total': len(rows)}

    @staticmethod
    def review(resource_id: int, reviewer_id: int, status: str, reason: str = '') -> dict:
        if status not in ('approved', 'rejected'):
            raise ValueError('review_status必须为approved或rejected')
        if status == 'approved' and not reason.strip():
            raise ValueError('批准资源时必须填写审核说明')
        row = PersonalizedLearningResource.query.get(resource_id)
        if not row:
            raise LookupError('资源不存在')
        row.review_status = status
        row.review_reason = reason[:500]
        row.reviewed_by = reviewer_id
        row.reviewed_at = datetime.utcnow()
        db.session.commit()
        return row.to_dict()
