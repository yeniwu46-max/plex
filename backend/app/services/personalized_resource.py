"""Personalized five-resource generation with progress and review controls."""
from __future__ import annotations

import os
import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timedelta

from flask import current_app
from jsonschema import Draft202012Validator

from app.data.course_knowledge import catalog_points, document_ids
from app.models import PersonalizedLearningResource, ResourceGenerationTask, db
from app.services.course_safety import CourseSafetyService
from app.services.iflytek_spark import IflytekSparkService
from app.services.question_generator import QuestionGenerator
from app.services.student_profile import StudentProfileService
from app.utils.time import utc_now

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
AGENT_CONTRACT_VERSION = 'resource-pipeline-v1'
AGENT_LABELS = {
    'profile_interpreter': '画像解释智能体',
    'knowledge_retriever': '知识检索智能体',
    'instructional_designer': '教学设计智能体',
    'resource_generator': '资源生成智能体',
    'quality_reviewer': '质量审核智能体',
    'path_planner': '路径规划智能体',
}
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='plex-resource')
_CREATE_LOCK = Lock()

POINTS = catalog_points()
DOCUMENT_IDS = document_ids()
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
    def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
        """Normalize model output such as ``每次15分钟`` without failing a task."""
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            parsed = int(value)
        else:
            match = re.search(r'-?\d+', str(value or ''))
            parsed = int(match.group(0)) if match else default
        return min(max(parsed, minimum), maximum)

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
            {
                'agent': agent,
                'name': AGENT_LABELS[agent],
                'contract_version': AGENT_CONTRACT_VERSION,
                'status': 'pending',
                'latency_ms': None,
                'backend': None,
                'model': None,
                'depends_on': PIPELINE_STEPS[index - 1][0] if index else None,
                'input_summary': {},
                'output_summary': {},
                'started_at': None,
                'completed_at': None,
                'error': None,
            }
            for index, (agent, _) in enumerate(PIPELINE_STEPS)
        ]

    @staticmethod
    def executor_status():
        return {'backend': 'in_process', 'max_workers': 2, 'available': True}

    @staticmethod
    def recover_stale_tasks(app=None):
        cutoff = utc_now() - timedelta(minutes=10)
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
        CourseSafetyService.ensure_safe(str(payload), enforce_course_scope=True)
        PersonalizedResourceService._validate_request(knowledge_key, resource_types)

        profile = StudentProfileService.get_or_create(user_id)
        profile_version = profile.version if profile.id else 0
        fingerprint = PersonalizedResourceService._fingerprint(
            user_id, profile_version, knowledge_key, resource_types
        )
        idempotency_key = str(payload.get('idempotency_key') or '').strip()[:100] or None

        with _CREATE_LOCK:
            if not payload.get('force_regenerate'):
                active = ResourceGenerationTask.query.filter(
                    ResourceGenerationTask.user_id == user_id,
                    ResourceGenerationTask.status.in_(('pending', 'running', 'completed')),
                    ResourceGenerationTask.created_at >= utc_now() - timedelta(minutes=15),
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
    def _set_step(
        row: ResourceGenerationTask,
        index: int,
        status: str,
        latency_ms=None,
        *,
        backend=None,
        model=None,
        input_summary=None,
        output_summary=None,
        error=None,
    ):
        steps = [dict(item) for item in (row.steps or PersonalizedResourceService._steps())]
        step = steps[index]
        step['status'] = status
        step['latency_ms'] = latency_ms
        if status == 'running':
            step['started_at'] = utc_now().isoformat() + 'Z'
        if status in ('completed', 'failed'):
            step['completed_at'] = utc_now().isoformat() + 'Z'
        if backend is not None:
            step['backend'] = backend
        if model is not None:
            step['model'] = model
        if input_summary is not None:
            step['input_summary'] = input_summary
        if output_summary is not None:
            step['output_summary'] = output_summary
        if error is not None:
            step['error'] = str(error)[:255]
        row.steps = steps
        row.current_agent = step['agent'] if status == 'running' else row.current_agent
        db.session.commit()

    @staticmethod
    def _profile_strategy(profile: dict, knowledge_key: str) -> dict:
        foundation = str(profile.get('knowledge_foundation') or '未填写')
        return {
            'knowledge_key': knowledge_key,
            'profile_dimensions_used': sorted(profile.keys()),
            'difficulty_target': 40 if '零基础' in foundation else 55,
            'explanation_style': str(profile.get('explanation_preference') or '分步骤讲解')[:80],
            'interest_context': str(profile.get('interest_direction') or '校园学习')[:80],
            'learning_pace': str(profile.get('learning_pace') or '每次15分钟')[:80],
        }

    @staticmethod
    def _knowledge_context(knowledge_key: str, profile_strategy: dict) -> dict:
        citation = PersonalizedResourceService._citation(knowledge_key)
        return {
            'knowledge_key': knowledge_key,
            'knowledge_label': POINTS[knowledge_key],
            'document_id': citation['document_id'],
            'section': citation['section'],
            'citation_count': 1,
            'difficulty_target': profile_strategy['difficulty_target'],
        }

    @staticmethod
    def _instructional_design(
        requested_types: list[str],
        profile_strategy: dict,
        knowledge_context: dict,
    ) -> dict:
        return {
            'knowledge_key': knowledge_context['knowledge_key'],
            'resource_types': requested_types,
            'difficulty_target': profile_strategy['difficulty_target'],
            'explanation_style': profile_strategy['explanation_style'],
            'interest_context': profile_strategy['interest_context'],
            'learning_pace': profile_strategy['learning_pace'],
            'sequence': [
                item for item in RESOURCE_TYPES if item in requested_types
            ] + [
                item for item in OPTIONAL_RESOURCE_TYPES if item in requested_types
            ],
        }

    @staticmethod
    def _quality_report(generated: list[dict], knowledge_key: str) -> dict:
        items = []
        for item in generated:
            risks = PersonalizedResourceService._risk_reasons(item, knowledge_key)
            items.append({
                'resource_type': item.get('resource_type'),
                'confidence': round(float(item.get('confidence') or 0), 2),
                'risk_reasons': risks,
                'review_status': 'approved' if not risks else 'pending_review',
            })
        return {
            'items': items,
            'resource_count': len(items),
            'approved_count': sum(1 for item in items if item['review_status'] == 'approved'),
            'pending_review_count': sum(
                1 for item in items if item['review_status'] == 'pending_review'
            ),
            'schema_pass_count': sum(
                1 for item in items if 'schema_invalid' not in item['risk_reasons']
            ),
            'citation_pass_count': sum(
                1 for item in items if 'invalid_citation' not in item['risk_reasons']
            ),
        }

    @staticmethod
    def _path_plan(knowledge_key: str, quality_report: dict) -> dict:
        visible_types = [
            item['resource_type']
            for item in quality_report['items']
            if item['review_status'] == 'approved'
        ]
        return {
            'knowledge_key': knowledge_key,
            'target_route': f'/student/star-path?kp={knowledge_key}',
            'visible_resource_types': visible_types,
            'blocked_pending_review': quality_report['pending_review_count'],
            'recommendation_reason': (
                f'画像约束与 {POINTS[knowledge_key]} 当前学习进度共同决定资源顺序'
            ),
        }

    @staticmethod
    def _store_generated_resources(
        row: ResourceGenerationTask,
        generated: list[dict],
        profile: dict,
        quality_report: dict,
    ):
        quality_by_type = {
            item['resource_type']: item for item in quality_report['items']
        }
        PersonalizedLearningResource.query.filter_by(
            generation_task_id=row.task_id
        ).delete()
        for item in generated:
            quality = quality_by_type[item['resource_type']]
            confidence = min(max(float(item.get('confidence', 0.8)), 0), 1)
            item['difficulty'] = PersonalizedResourceService._bounded_int(
                item.get('difficulty'), 50, 0, 100
            )
            item['estimated_minutes'] = PersonalizedResourceService._bounded_int(
                item.get('estimated_minutes'), 15, 1, 180
            )
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
                recommendation_reason=str(
                    item.get('recommendation_reason') or '根据画像与薄弱点生成'
                ),
                citations=item.get('citations') or [],
                confidence=confidence,
                review_status=quality['review_status'],
                risk_reasons=quality['risk_reasons'],
                generator_agent='resource_generator',
                backend=row.backend,
            ))
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
        try:
            CourseSafetyService.ensure_safe(serialized, enforce_course_scope=True)
        except Exception:
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
        foundation = str(profile.get('knowledge_foundation') or '')
        beginner = '零基础' in foundation
        code_first = '先看代码' in str(preference)
        difficulty = 40 if beginner else 65
        estimated_minutes = 15 if beginner else 30
        if code_first:
            lesson_sections = (
                f'## 先看代码\n```python\nprint("{label}")\n```\n\n'
                f'## 原理拆解\n围绕 {label} 分析执行过程、复杂度和边界条件。'
            )
        else:
            lesson_sections = (
                f'## 核心概念\n围绕 {label} 理解语法、执行过程和适用场景。\n\n'
                f'## 生活化案例\n用“{interest}”场景分步骤解释。\n\n'
                f'## 示例\n```python\nprint("{label}")\n```'
            )
        exercise_levels = ('基础', '巩固') if beginner else ('进阶', '挑战')
        common = {
            'difficulty': difficulty,
            'estimated_minutes': estimated_minutes,
            'recommendation_reason': f'根据你的讲解偏好“{preference}”、学习节奏“{pace}”生成。',
            'citations': [PersonalizedResourceService._citation(knowledge_key)],
            'confidence': 0.88,
        }
        builders = {
            'lesson_document': {
                'title': f'{label}个性化讲解',
                'content': {
                    'format': 'markdown',
                    'markdown': f'# {label}\n\n采用{preference}。\n\n{lesson_sections}\n\n## 常见错误\n注意缩进、边界与数据类型。',
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
                        {
                            'level': exercise_levels[0],
                            'question': f'解释 {label} 的基本作用并给出最小示例。',
                        },
                        {
                            'level': exercise_levels[1],
                            'question': f'使用 {label} 解决一个与{interest}有关的小任务。',
                        },
                    ],
                },
            },
            'extended_reading': {
                'title': f'{label}拓展阅读',
                # Local fallback cannot independently verify broader reading claims.
                'confidence': 0.78,
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
                ResourceGenerationTask.started_at: utc_now(),
            }, synchronize_session=False)
            db.session.commit()
            if claimed != 1:
                return
            row = ResourceGenerationTask.query.filter_by(task_id=task_id).first()
            active_index = None
            try:
                profile = PersonalizedResourceService._profile_snapshot(row.user_id)
                artifacts = {}
                for index, (agent, progress) in enumerate(PIPELINE_STEPS):
                    active_index = index
                    started = utc_now()
                    input_summary = {
                        'knowledge_key': row.knowledge_key,
                        'requested_types': row.requested_types,
                        'depends_on': PIPELINE_STEPS[index - 1][0] if index else None,
                    }
                    if index:
                        previous_agent = PIPELINE_STEPS[index - 1][0]
                        input_summary['upstream_keys'] = sorted(
                            artifacts.get(previous_agent, {}).keys()
                        )
                    PersonalizedResourceService._set_step(
                        row,
                        index,
                        'running',
                        backend='in_process',
                        model='deterministic_contract',
                        input_summary=input_summary,
                    )

                    if agent == 'profile_interpreter':
                        output = PersonalizedResourceService._profile_strategy(
                            profile, row.knowledge_key
                        )
                    elif agent == 'knowledge_retriever':
                        output = PersonalizedResourceService._knowledge_context(
                            row.knowledge_key,
                            artifacts['profile_interpreter'],
                        )
                    elif agent == 'instructional_designer':
                        output = PersonalizedResourceService._instructional_design(
                            row.requested_types,
                            artifacts['profile_interpreter'],
                            artifacts['knowledge_retriever'],
                        )
                    elif agent == 'resource_generator':
                        generation_context = {
                            **profile,
                            '_instructional_design': artifacts['instructional_designer'],
                        }
                        try:
                            if not IflytekSparkService.configured():
                                raise RuntimeError('spark_not_available')
                            generated = PersonalizedResourceService._spark_resources(
                                row.knowledge_key, row.requested_types, generation_context
                            )
                            row.backend = 'iflytek_spark'
                            step_backend = 'iflytek_spark'
                            step_model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
                        except Exception as exc:
                            generated = PersonalizedResourceService._local_resources(
                                row.knowledge_key, row.requested_types, generation_context
                            )
                            row.backend = 'local_rules'
                            row.fallback_reason = str(exc)[:255]
                            step_backend = 'local_rules'
                            step_model = 'rules-v1'
                        output = {
                            'resource_count': len(generated),
                            'resource_types': [
                                item.get('resource_type') for item in generated
                            ],
                            'difficulty_range': [
                                min(PersonalizedResourceService._bounded_int(item.get('difficulty'), 50, 0, 100) for item in generated),
                                max(PersonalizedResourceService._bounded_int(item.get('difficulty'), 50, 0, 100) for item in generated),
                            ],
                        }
                        artifacts['_generated_resources'] = generated
                    elif agent == 'quality_reviewer':
                        generated = artifacts['_generated_resources']
                        output = PersonalizedResourceService._quality_report(
                            generated, row.knowledge_key
                        )
                        PersonalizedResourceService._store_generated_resources(
                            row, generated, profile, output
                        )
                    elif agent == 'path_planner':
                        output = PersonalizedResourceService._path_plan(
                            row.knowledge_key,
                            artifacts['quality_reviewer'],
                        )
                    else:
                        raise RuntimeError(f'unknown_pipeline_agent:{agent}')

                    artifacts[agent] = output
                    row.progress = max(row.progress, progress)
                    elapsed = int((utc_now() - started).total_seconds() * 1000)
                    PersonalizedResourceService._set_step(
                        row,
                        index,
                        'completed',
                        elapsed,
                        backend=step_backend if agent == 'resource_generator' else 'in_process',
                        model=step_model if agent == 'resource_generator' else 'deterministic_contract',
                        input_summary=input_summary,
                        output_summary=output,
                    )
                row.status = 'completed'
                row.progress = 100
                row.current_agent = None
                row.completed_at = utc_now()
                row.recoverable = False
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                row = ResourceGenerationTask.query.filter_by(task_id=task_id).first()
                if active_index is not None:
                    PersonalizedResourceService._set_step(
                        row,
                        active_index,
                        'failed',
                        error=exc,
                    )
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
    def review_metrics() -> dict:
        rows = PersonalizedLearningResource.query.all()
        status_counts = {
            status: sum(1 for row in rows if row.review_status == status)
            for status in ('pending_review', 'approved', 'rejected')
        }
        risk_counts: dict[str, int] = {}
        review_minutes = []
        for row in rows:
            for risk in row.risk_reasons or []:
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            if row.reviewed_at and row.created_at:
                review_minutes.append(
                    max(0, (row.reviewed_at - row.created_at).total_seconds() / 60)
                )
        return {
            'total_resources': len(rows),
            'status_counts': status_counts,
            'pending_review_count': status_counts['pending_review'],
            'average_review_minutes': (
                round(sum(review_minutes) / len(review_minutes), 1)
                if review_minutes else None
            ),
            'risk_reason_distribution': [
                {'reason': reason, 'count': count}
                for reason, count in sorted(
                    risk_counts.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        }

    @staticmethod
    def review(resource_id: int, reviewer_id: int, status: str, reason: str = '') -> dict:
        if status not in ('approved', 'rejected'):
            raise ValueError('review_status必须为approved或rejected')
        if status == 'approved' and not reason.strip():
            raise ValueError('批准资源时必须填写审核说明')
        row = db.session.get(PersonalizedLearningResource, resource_id)
        if not row:
            raise LookupError('资源不存在')
        row.review_status = status
        row.review_reason = reason[:500]
        row.reviewed_by = reviewer_id
        row.reviewed_at = utc_now()
        db.session.commit()
        return row.to_dict()
