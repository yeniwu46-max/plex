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

from app.data.course_knowledge import catalog_points, document_ids, knowledge_section
from app.models import PersonalizedLearningResource, ResourceGenerationTask, db
from app.services.course_safety import CourseSafetyService
from app.services.iflytek_spark import IflytekSparkService
from app.services.pedagogical_resource import (
    BUNDLE_SCHEMA,
    analyze_pedagogy,
    build_knowledge_node,
    build_local_bundle,
    cases_for_knowledge,
    infer_learning_stage,
    infer_learning_styles,
    infer_target,
    llm_bundle,
    spark_bundle,
    split_bundle_to_legacy_types,
    validate_bundle_risks,
)
from app.services.resource_audit import ResourceAuditService
from app.services.student_profile import StudentProfileService
from app.utils.time import utc_now

LEGACY_RESOURCE_TYPES = (
    'lesson_document',
    'mind_map',
    'exercise_set',
    'extended_reading',
    'coding_lab',
)
RESOURCE_TYPES = ('learning_bundle',) + LEGACY_RESOURCE_TYPES
OPTIONAL_RESOURCE_TYPES = ('audio_explanation', 'video_lesson')
ALLOWED_RESOURCE_TYPES = RESOURCE_TYPES + OPTIONAL_RESOURCE_TYPES
PIPELINE_STEPS = (
    ('profile_interpreter', 10),
    ('knowledge_retriever', 25),
    ('instructional_designer', 40),
    ('resource_generator', 75),
    ('quality_reviewer', 90),
    ('path_planner', 100),
)
AGENT_CONTRACT_VERSION = 'resource-pipeline-v2'
AGENT_LABELS = {
    'profile_interpreter': '画像解释智能体',
    'knowledge_retriever': '知识检索智能体',
    'instructional_designer': '教学设计智能体',
    'resource_generator': '资源生成智能体',
    'quality_reviewer': 'AI审核智能体',
    'path_planner': '路径规划智能体',
}
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='plex-resource')
_CREATE_LOCK = Lock()

POINTS = catalog_points()
DOCUMENT_IDS = document_ids()
VALID_DOCUMENT_IDS = frozenset(DOCUMENT_IDS.values())
RESOURCE_SCHEMAS = {
    'learning_bundle': BUNDLE_SCHEMA,
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
    'video_lesson': {
        'type': 'object', 'required': ['format', 'script'],
        'properties': {'format': {'type': 'string'}, 'script': {'type': 'string', 'minLength': 10}},
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
    def _pedagogical_context_from_payload(payload: dict, profile: dict) -> dict:
        styles = payload.get('learning_style')
        if isinstance(styles, str):
            styles = [styles]
        return {
            'target': infer_target(payload.get('target')),
            'learning_stage': infer_learning_stage(profile, payload.get('learning_stage')),
            'learning_style': infer_learning_styles(profile, styles if isinstance(styles, list) else None),
        }

    @staticmethod
    def _fingerprint(
        user_id: int,
        profile_version: int,
        knowledge_key: str,
        resource_types: list[str],
        pedagogical_context: dict | None = None,
    ) -> str:
        raw = json.dumps({
            'user_id': user_id,
            'profile_version': profile_version,
            'knowledge_key': knowledge_key,
            'resource_types': sorted(resource_types),
            'pedagogical_context': pedagogical_context or {},
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

        profile_row = StudentProfileService.get_or_create(user_id)
        profile_version = profile_row.version if profile_row.id else 0
        profile = {
            key: value.get('value')
            for key, value in (profile_row.to_dict().get('dimensions') or {}).items()
            if value.get('value')
        }
        pedagogical_context = PersonalizedResourceService._pedagogical_context_from_payload(
            payload, profile
        )
        fingerprint = PersonalizedResourceService._fingerprint(
            user_id, profile_version, knowledge_key, resource_types, pedagogical_context
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

            steps = PersonalizedResourceService._steps()
            steps[0]['input_summary'] = {'pedagogical_context': pedagogical_context}
            row = ResourceGenerationTask(
                task_id='rg_' + uuid.uuid4().hex[:20],
                user_id=user_id,
                knowledge_key=knowledge_key,
                requested_types=resource_types,
                steps=steps,
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
            'focus_points': [POINTS.get(knowledge_key, knowledge_key)],
        }

    @staticmethod
    def _run_profile_interpreter(profile: dict, knowledge_key: str) -> tuple[dict, str, str]:
        from agents.resource_pipeline_agents import interpret_profile

        baseline = PersonalizedResourceService._profile_strategy(profile, knowledge_key)
        return interpret_profile(
            profile=profile,
            knowledge_key=knowledge_key,
            knowledge_label=POINTS[knowledge_key],
            baseline=baseline,
        )

    @staticmethod
    def _knowledge_context(knowledge_key: str, profile_strategy: dict) -> dict:
        citation = PersonalizedResourceService._citation(knowledge_key)
        node = build_knowledge_node(knowledge_key)
        return {
            'knowledge_key': knowledge_key,
            'knowledge_label': POINTS[knowledge_key],
            'document_id': citation['document_id'],
            'section': citation['section'],
            'citation_count': 1,
            'retrieved_snippet': citation['snippet'][:120],
            'difficulty_target': profile_strategy['difficulty_target'],
            'knowledge_node': node,
            'citations': [citation],
        }

    @staticmethod
    def _run_knowledge_retriever(
        knowledge_key: str,
        profile_strategy: dict,
    ) -> tuple[dict, str, str]:
        from agents.resource_pipeline_agents import retrieve_knowledge

        baseline = PersonalizedResourceService._knowledge_context(knowledge_key, profile_strategy)
        section = knowledge_section(knowledge_key)
        citation = PersonalizedResourceService._citation(knowledge_key)
        node = baseline.get('knowledge_node') or build_knowledge_node(knowledge_key)
        return retrieve_knowledge(
            knowledge_key=knowledge_key,
            knowledge_label=POINTS[knowledge_key],
            profile_strategy=profile_strategy,
            baseline=baseline,
            section=section,
            citation=citation,
            knowledge_node=node,
        )

    @staticmethod
    def _instructional_design(
        requested_types: list[str],
        profile_strategy: dict,
        knowledge_context: dict,
        pedagogical_context: dict,
        profile: dict,
    ) -> dict:
        node = knowledge_context.get('knowledge_node') or build_knowledge_node(
            knowledge_context['knowledge_key']
        )
        analysis = analyze_pedagogy(
            node,
            target=pedagogical_context.get('target', infer_target()),
            learning_stage=pedagogical_context.get('learning_stage', infer_learning_stage(profile)),
            learning_styles=pedagogical_context.get('learning_style') or infer_learning_styles(profile),
            profile=profile,
        )
        return {
            **analysis,
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
    def _run_instructional_designer(
        requested_types: list[str],
        profile_strategy: dict,
        knowledge_context: dict,
        pedagogical_context: dict,
        profile: dict,
    ) -> tuple[dict, str, str]:
        from agents.resource_pipeline_agents import design_instruction

        baseline = PersonalizedResourceService._instructional_design(
            requested_types,
            profile_strategy,
            knowledge_context,
            pedagogical_context,
            profile,
        )
        return design_instruction(
            requested_types=requested_types,
            profile_strategy=profile_strategy,
            knowledge_context=knowledge_context,
            pedagogical_context=pedagogical_context,
            baseline_analysis=baseline,
        )

    @staticmethod
    def _audit_risk_codes(audit_report: dict | None) -> list[str]:
        if not audit_report:
            return []
        codes: list[str] = []
        for step in audit_report.get('steps') or []:
            for check in step.get('checks') or []:
                if check.get('level') == 'FAIL':
                    check_id = str(check.get('id') or 'unknown')
                    codes.append(f'audit_{check_id}')
        return list(dict.fromkeys(codes))

    @staticmethod
    def _quality_report(
        generated: list[dict],
        knowledge_key: str,
        *,
        profile: dict | None = None,
        audit_report: dict | None = None,
        bundle: dict | None = None,
    ) -> dict:
        from agents.resource_review_agent import is_hard_risk, review_generated_resource

        audit_risks = PersonalizedResourceService._audit_risk_codes(audit_report)
        hard_audit_risks = [code for code in audit_risks if is_hard_risk(code)]
        soft_audit_risks = [code for code in audit_risks if code not in hard_audit_risks]
        items = []
        bundle_risks: list[str] = []
        for item in generated:
            risks = PersonalizedResourceService._risk_reasons(item, knowledge_key)
            # 仅把硬 audit FAIL 并入单项；软 audit 不挡自动发布
            if hard_audit_risks:
                risks = list(dict.fromkeys(risks + hard_audit_risks))
            if soft_audit_risks and item.get('resource_type') == 'learning_bundle':
                risks = list(dict.fromkeys(risks + soft_audit_risks))
            if item.get('resource_type') == 'learning_bundle':
                bundle_risks = list(risks)
            items.append({
                'resource_type': item.get('resource_type'),
                'confidence': round(float(item.get('confidence') or 0), 2),
                'risk_reasons': risks,
                'review_status': 'approved' if not any(is_hard_risk(r) for r in risks) else 'pending_review',
            })
        if bundle_risks:
            hard_bundle = [r for r in bundle_risks if is_hard_risk(r)]
            for entry in items:
                if entry['resource_type'] != 'learning_bundle' and hard_bundle:
                    merged = list(dict.fromkeys(entry['risk_reasons'] + hard_bundle))
                    entry['risk_reasons'] = merged
                    entry['review_status'] = (
                        'approved' if not any(is_hard_risk(r) for r in merged) else 'pending_review'
                    )

        # AI 审核智能体：正常内容自动批准；仅硬异常/AI 驳回进教师端
        bundle_entry = next(
            (entry for entry in items if entry.get('resource_type') == 'learning_bundle'),
            items[0] if items else None,
        )
        bundle_risks_for_ai = list((bundle_entry or {}).get('risk_reasons') or [])
        title = next(
            (
                str(item.get('title') or '')
                for item in generated
                if item.get('resource_type') == 'learning_bundle'
            ),
            '',
        )
        ai_review = review_generated_resource(
            bundle=bundle if isinstance(bundle, dict) else {},
            knowledge_key=knowledge_key,
            audit_report=audit_report,
            risk_reasons=bundle_risks_for_ai,
            title=title,
        )
        if audit_report is not None:
            metadata = dict(audit_report.get('metadata') or {})
            metadata['ai_agent_review'] = ai_review
            if ai_review.get('teacher_summary'):
                metadata['crewai_notes'] = ai_review['teacher_summary']
            audit_report['metadata'] = metadata

        decision = ai_review.get('decision')
        package_anomaly = bool(ai_review.get('is_anomaly')) or decision in (
            'needs_review',
            'reject',
        )
        for entry in items:
            entry['ai_review'] = ai_review
            item_risks = list(entry.get('risk_reasons') or [])
            item_hard = any(is_hard_risk(r) for r in item_risks)
            if decision == 'auto_approve' and not package_anomaly and not item_hard:
                entry['review_status'] = 'approved'
                entry['is_anomaly'] = False
                entry['student_warning'] = None
                entry['review_reason'] = ai_review.get('review_reason') or (
                    'AI 审核智能体：内容正常，已自动批准。'
                )
            elif package_anomaly or item_hard or decision == 'reject':
                entry['review_status'] = 'pending_review'
                entry['is_anomaly'] = True
                if package_anomaly and decision == 'reject' and 'ai_reject' not in item_risks:
                    entry['risk_reasons'] = list(dict.fromkeys(item_risks + ['ai_reject']))
                elif package_anomaly and 'ai_anomaly' not in item_risks:
                    entry['risk_reasons'] = list(dict.fromkeys(item_risks + ['ai_anomaly']))
                entry['review_reason'] = ai_review.get('review_reason')
                entry['student_warning'] = (
                    ai_review.get('student_warning')
                    if package_anomaly
                    else (
                        '本资源存在异常风险，已提交教师复核；学习时请以课堂与教材为准。'
                    )
                )
            else:
                # 仅软风险（如 low_confidence）：学生立刻可用，不进异常区
                entry['review_status'] = 'approved'
                entry['is_anomaly'] = False
                entry['student_warning'] = None
                entry['review_reason'] = ai_review.get('review_reason') or (
                    'AI 审核智能体：无硬伤，已自动批准。'
                )

        return {
            'items': items,
            'resource_count': len(items),
            'approved_count': sum(1 for item in items if item['review_status'] == 'approved'),
            'pending_review_count': sum(
                1 for item in items if item['review_status'] == 'pending_review'
            ),
            'anomaly_count': sum(1 for item in items if item.get('is_anomaly')),
            'schema_pass_count': sum(
                1 for item in items if 'schema_invalid' not in item['risk_reasons']
            ),
            'citation_pass_count': sum(
                1 for item in items if 'invalid_citation' not in item['risk_reasons']
            ),
            'audit_report': audit_report,
            'ai_review': ai_review,
            'suggested_verdict': (audit_report or {}).get('verdict'),
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
            'preview_pending': True,
            'study_order': visible_types,
        }

    @staticmethod
    def _run_path_planner(
        knowledge_key: str,
        quality_report: dict,
        profile_strategy: dict | None = None,
        instructional_design: dict | None = None,
    ) -> tuple[dict, str, str]:
        from agents.resource_pipeline_agents import plan_learning_path

        baseline = PersonalizedResourceService._path_plan(knowledge_key, quality_report)
        return plan_learning_path(
            knowledge_key=knowledge_key,
            knowledge_label=POINTS[knowledge_key],
            quality_report=quality_report,
            profile_strategy=profile_strategy,
            instructional_design=instructional_design,
            baseline=baseline,
        )

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
                review_reason=(quality.get('review_reason') or None),
                risk_reasons=quality['risk_reasons'],
                reviewed_at=utc_now() if quality['review_status'] == 'approved' else None,
                generator_agent='resource_generator',
                backend=row.backend,
                is_anomaly=bool(quality.get('is_anomaly')),
                student_warning=(quality.get('student_warning') or None),
                ai_review=quality.get('ai_review') or {},
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
        section = knowledge_section(knowledge_key)
        snippet = (
            section.get('concept')
            or f'{POINTS[knowledge_key]}课程知识库中的概念、示例与常见错误。'
        )
        return {
            'document_id': DOCUMENT_IDS[knowledge_key],
            'title': f"《Python程序设计基础》：{POINTS[knowledge_key]}",
            'section': knowledge_key,
            'snippet': snippet[:200],
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
        if resource_type == 'learning_bundle' and isinstance(content, dict):
            risks.extend(validate_bundle_risks(content))
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
    def _resource_meta(knowledge_key: str, profile: dict, analysis: dict) -> dict:
        foundation = str(profile.get('knowledge_foundation') or '')
        beginner = '零基础' in foundation
        preference = profile.get('explanation_preference') or '分步骤讲解'
        pace = profile.get('learning_pace') or '每次15分钟'
        return {
            'difficulty': 40 if beginner else 65,
            'estimated_minutes': 20 if beginner else 35,
            'recommendation_reason': (
                f'根据{analysis.get("learning_stage", "学习")}阶段、'
                f'讲解偏好「{preference}」与学习节奏「{pace}」生成。'
            ),
            'citations': [PersonalizedResourceService._citation(knowledge_key)],
            'confidence': 0.9,
        }

    @staticmethod
    def _generate_from_bundle(
        knowledge_key: str,
        resource_types: list[str],
        profile: dict,
        analysis: dict,
    ) -> tuple[list[dict], str, dict]:
        node = build_knowledge_node(knowledge_key)
        case_candidates = cases_for_knowledge(knowledge_key, 2)
        errors: list[str] = []
        bundle = None
        backend = 'local_rules'

        # 优先 DeepSeek/OpenAI（本机可用），再试讯飞星火；都失败才用本地课程模板
        try:
            from agents.llm_client import llm_provider

            if llm_provider():
                bundle = llm_bundle(
                    knowledge_key,
                    node=node,
                    analysis=analysis,
                    profile=profile,
                    case_candidates=case_candidates,
                    timeout=25.0,
                )
                backend = 'deepseek'
        except Exception as exc:
            errors.append(f'llm:{exc}')

        if bundle is None and IflytekSparkService.configured():
            try:
                bundle = spark_bundle(
                    knowledge_key,
                    node=node,
                    analysis=analysis,
                    profile=profile,
                    case_candidates=case_candidates,
                )
                backend = 'iflytek_spark'
            except Exception as exc:
                errors.append(f'spark:{exc}')

        if bundle is None:
            bundle = build_local_bundle(knowledge_key, analysis=analysis, profile=profile)
            backend = 'local_rules'
            if errors:
                # 留给任务记录，前端可提示「云端不可用」
                bundle.setdefault('_fallback_errors', errors[:3])

        split_rows = split_bundle_to_legacy_types(bundle, knowledge_key)
        interest = str(profile.get('interest_direction') or '').strip()
        if interest:
            for row in split_rows:
                if row.get('resource_type') != 'coding_lab':
                    continue
                content = dict(row.get('content') or {})
                scenario = str(content.get('scenario') or '').strip()
                if interest not in scenario:
                    content['scenario'] = (
                        f'结合兴趣「{interest}」完成：{scenario}'
                        if scenario
                        else f'结合兴趣「{interest}」编写使用{POINTS[knowledge_key]}的小程序。'
                    )
                    row['content'] = content
        meta = PersonalizedResourceService._resource_meta(knowledge_key, profile, analysis)
        by_type = {row['resource_type']: row for row in split_rows}
        generated = []
        for resource_type in resource_types:
            if resource_type == 'audio_explanation':
                label = POINTS[knowledge_key]
                transcript = bundle.get('explain', '')[:500]
                audio_url = None
                try:
                    from app.services.tts_service import TtsService

                    audio_url = TtsService.synthesize_to_media(
                        transcript, prefix=f'tts-{knowledge_key}'
                    )
                except Exception:
                    audio_url = None
                generated.append({
                    **meta,
                    'resource_type': 'audio_explanation',
                    'title': f'{label}语音讲解',
                    'confidence': 0.82 if audio_url else 0.78,
                    'content': {
                        'format': 'audio' if audio_url else 'audio_fallback',
                        'transcript': transcript,
                        'voice': os.getenv('IFLYTEK_TTS_VOICE', 'xiaoyan') if audio_url else None,
                    },
                    'content_url': audio_url,
                })
                continue
            if resource_type == 'video_lesson':
                label = POINTS[knowledge_key]
                explain = (bundle.get('explain') or '')[:280]
                script = (
                    f'教学短视频：{label}。'
                    f'先用一个生活场景引入概念，再展示 Python 代码片段，最后用一句话总结。'
                    f'讲解要点：{explain}'
                )
                video_url = None
                try:
                    from app.services.ark_media import ArkMediaService

                    if ArkMediaService.video_configured():
                        video_url = ArkMediaService.generate_video(
                            f'Educational animation, clean whiteboard style, Chinese captions, '
                            f'topic: {label}. {script}',
                            max_wait_seconds=180,
                        )
                except Exception:
                    video_url = None
                generated.append({
                    **meta,
                    'resource_type': 'video_lesson',
                    'title': f'{label}教学短视频',
                    'confidence': 0.8 if video_url else 0.72,
                    'content': {
                        'format': 'video' if video_url else 'video_script',
                        'script': script,
                        'duration_hint_seconds': 20,
                    },
                    'content_url': video_url,
                })
                continue
            row = by_type.get(resource_type)
            if not row:
                continue
            item = {**meta, **row}
            generated.append(item)
        return generated, backend, bundle

    @staticmethod
    def _extract_pedagogical_context(row: ResourceGenerationTask) -> dict:
        steps = row.steps or []
        if steps and isinstance(steps[0].get('input_summary'), dict):
            ctx = steps[0]['input_summary'].get('pedagogical_context')
            if isinstance(ctx, dict):
                return ctx
        return {}

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
            step_backend = 'in_process'
            step_model = 'deterministic_contract'
            try:
                profile = PersonalizedResourceService._profile_snapshot(row.user_id)
                pedagogical_context = PersonalizedResourceService._extract_pedagogical_context(row)
                artifacts = {}
                for index, (agent, progress) in enumerate(PIPELINE_STEPS):
                    active_index = index
                    started = utc_now()
                    step_backend = 'in_process'
                    step_model = 'deterministic_contract'
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
                        output, step_backend, step_model = (
                            PersonalizedResourceService._run_profile_interpreter(
                                profile, row.knowledge_key
                            )
                        )
                    elif agent == 'knowledge_retriever':
                        output, step_backend, step_model = (
                            PersonalizedResourceService._run_knowledge_retriever(
                                row.knowledge_key,
                                artifacts['profile_interpreter'],
                            )
                        )
                    elif agent == 'instructional_designer':
                        output, step_backend, step_model = (
                            PersonalizedResourceService._run_instructional_designer(
                                row.requested_types,
                                artifacts['profile_interpreter'],
                                artifacts['knowledge_retriever'],
                                pedagogical_context,
                                profile,
                            )
                        )
                    elif agent == 'resource_generator':
                        analysis = artifacts['instructional_designer']
                        bundle = None
                        try:
                            generated, gen_backend, bundle = PersonalizedResourceService._generate_from_bundle(
                                row.knowledge_key, row.requested_types, profile, analysis
                            )
                            row.backend = gen_backend
                            step_backend = gen_backend
                            if gen_backend == 'deepseek':
                                row.fallback_reason = None
                                step_model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
                            elif gen_backend == 'iflytek_spark':
                                row.fallback_reason = None
                                step_model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
                            elif gen_backend == 'openai':
                                row.fallback_reason = None
                                step_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
                            else:
                                row.fallback_reason = row.fallback_reason or 'llm_and_spark_unavailable'
                                step_model = 'pedagogical-v2'
                        except Exception as exc:
                            bundle = build_local_bundle(
                                row.knowledge_key,
                                analysis=analysis,
                                profile=profile,
                            )
                            split_rows = split_bundle_to_legacy_types(bundle, row.knowledge_key)
                            meta = PersonalizedResourceService._resource_meta(
                                row.knowledge_key, profile, analysis
                            )
                            by_type = {item['resource_type']: item for item in split_rows}
                            generated = [
                                {**meta, **by_type[rt]}
                                for rt in row.requested_types
                                if rt in by_type
                            ]
                            row.backend = 'local_rules'
                            row.fallback_reason = str(exc)[:255]
                            step_backend = 'local_rules'
                            step_model = 'pedagogical-v2'
                        artifacts['_bundle'] = bundle
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
                        bundle = artifacts.get('_bundle')
                        audit_report_dict = None
                        step_backend = 'openai'
                        step_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
                        if isinstance(bundle, dict):
                            bundle_item = next(
                                (item for item in generated if item.get('resource_type') == 'learning_bundle'),
                                None,
                            )
                            citations = (bundle_item or {}).get('citations') or []
                            confidence = float((bundle_item or generated[0] if generated else {}).get('confidence') or 0.9)
                            audit = ResourceAuditService.audit_bundle(
                                bundle,
                                row.knowledge_key,
                                profile,
                                confidence=confidence,
                                citations=citations,
                            )
                            audit = ResourceAuditService.enrich_with_crewai_notes(
                                audit, bundle, row.knowledge_key
                            )
                            audit_report_dict = audit.to_dict()
                            row.audit_report = audit_report_dict
                        output = PersonalizedResourceService._quality_report(
                            generated,
                            row.knowledge_key,
                            profile=profile,
                            audit_report=audit_report_dict,
                            bundle=bundle if isinstance(bundle, dict) else None,
                        )
                        ai_meta = (output.get('ai_review') or {})
                        step_backend = str(ai_meta.get('backend') or step_backend)
                        if isinstance(audit_report_dict, dict):
                            row.audit_report = audit_report_dict
                        PersonalizedResourceService._store_generated_resources(
                            row, generated, profile, output
                        )
                    elif agent == 'path_planner':
                        output, step_backend, step_model = (
                            PersonalizedResourceService._run_path_planner(
                                row.knowledge_key,
                                artifacts['quality_reviewer'],
                                artifacts.get('profile_interpreter'),
                                artifacts.get('instructional_designer'),
                            )
                        )
                    else:
                        raise RuntimeError(f'unknown_pipeline_agent:{agent}')

                    artifacts[agent] = output
                    row.progress = max(row.progress, progress)
                    elapsed = int((utc_now() - started).total_seconds() * 1000)
                    # 输出摘要去掉过大的嵌套，避免 steps JSON 膨胀
                    output_summary = output
                    if agent in (
                        'profile_interpreter',
                        'knowledge_retriever',
                        'instructional_designer',
                        'path_planner',
                    ):
                        output_summary = {
                            key: value
                            for key, value in output.items()
                            if key not in {'knowledge_node', 'course_section'}
                        }
                        if agent == 'knowledge_retriever':
                            output_summary['has_course_section'] = bool(output.get('course_section'))
                            output_summary['passage_count'] = len(output.get('retrieved_passages') or [])
                        if agent == 'profile_interpreter':
                            output_summary['rationale'] = str(output.get('profile_rationale') or '')[:160]
                        if agent == 'instructional_designer':
                            output_summary['rationale'] = str(output.get('design_rationale') or '')[:160]
                        if agent == 'path_planner':
                            output_summary['rationale'] = str(
                                output.get('path_rationale') or output.get('recommendation_reason') or ''
                            )[:160]
                    PersonalizedResourceService._set_step(
                        row,
                        index,
                        'completed',
                        elapsed,
                        backend=step_backend,
                        model=step_model,
                        input_summary=input_summary,
                        output_summary=output_summary,
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
        """学生可见：已批准 + 待审可预览；驳回不可见。优先返回已批准。"""
        query = PersonalizedLearningResource.query.filter(
            PersonalizedLearningResource.user_id == user_id,
            PersonalizedLearningResource.review_status.in_(('approved', 'pending_review')),
        )
        if args.get('knowledge_key'):
            query = query.filter_by(knowledge_key=args['knowledge_key'])
        if args.get('resource_type'):
            query = query.filter_by(resource_type=args['resource_type'])
        # 已批准优先，再按创建时间倒序，避免新待审条目盖住已发布内容
        rows = query.order_by(
            PersonalizedLearningResource.review_status.asc(),  # approved < pending_review 字母序
            PersonalizedLearningResource.created_at.desc(),
        ).all()
        # SQLite/MySQL 上 'approved' < 'pending_review'，再显式稳定排序
        rows = sorted(
            rows,
            key=lambda row: (
                0 if row.review_status == 'approved' else 1,
                -(row.id or 0),
            ),
        )
        return {'items': [row.to_dict() for row in rows], 'total': len(rows)}

    @staticmethod
    def list_review(status: str = 'pending_review', anomaly_only: bool | None = None) -> dict:
        query = PersonalizedLearningResource.query
        if status:
            query = query.filter_by(review_status=status)
        if anomaly_only is True:
            query = query.filter_by(is_anomaly=True)
        elif anomaly_only is False:
            query = query.filter_by(is_anomaly=False)
        rows = query.order_by(
            PersonalizedLearningResource.is_anomaly.desc(),
            PersonalizedLearningResource.created_at.desc(),
        ).all()
        return {'items': [row.to_dict() for row in rows], 'total': len(rows)}

    @staticmethod
    def _resolve_bundle_for_resource(row: PersonalizedLearningResource) -> dict | None:
        if row.resource_type == 'learning_bundle' and isinstance(row.content, dict):
            if row.content.get('format') == 'pedagogical_v2':
                return row.content
        sibling = PersonalizedLearningResource.query.filter_by(
            generation_task_id=row.generation_task_id,
            resource_type='learning_bundle',
        ).first()
        if sibling and isinstance(sibling.content, dict):
            if sibling.content.get('format') == 'pedagogical_v2':
                return sibling.content
        return None

    @staticmethod
    def get_audit(resource_id: int) -> dict:
        row = db.session.get(PersonalizedLearningResource, resource_id)
        if not row:
            raise LookupError('资源不存在')
        task = ResourceGenerationTask.query.filter_by(task_id=row.generation_task_id).first()
        if task and task.audit_report:
            return {
                'resource_id': resource_id,
                'generation_task_id': row.generation_task_id,
                'audit_report': task.audit_report,
            }
        bundle = PersonalizedResourceService._resolve_bundle_for_resource(row)
        if not bundle:
            raise LookupError('该资源尚无审核报告')
        profile = row.profile_snapshot if isinstance(row.profile_snapshot, dict) else {}
        audit = ResourceAuditService.audit_bundle(
            bundle,
            row.knowledge_key,
            profile,
            confidence=float(row.confidence or 0.9),
            citations=row.citations or [],
        )
        audit = ResourceAuditService.enrich_with_crewai_notes(audit, bundle, row.knowledge_key)
        report = audit.to_dict()
        if task:
            task.audit_report = report
            db.session.commit()
        return {
            'resource_id': resource_id,
            'generation_task_id': row.generation_task_id,
            'audit_report': report,
        }

    @staticmethod
    def rerun_audit(resource_id: int) -> dict:
        row = db.session.get(PersonalizedLearningResource, resource_id)
        if not row:
            raise LookupError('资源不存在')
        bundle = PersonalizedResourceService._resolve_bundle_for_resource(row)
        if not bundle:
            raise ValueError('无法找到 pedagogical_v2 资源包以重新审核')
        profile = row.profile_snapshot if isinstance(row.profile_snapshot, dict) else {}
        audit = ResourceAuditService.audit_bundle(
            bundle,
            row.knowledge_key,
            profile,
            confidence=float(row.confidence or 0.9),
            citations=row.citations or [],
        )
        audit = ResourceAuditService.enrich_with_crewai_notes(audit, bundle, row.knowledge_key)
        report = audit.to_dict()
        task = ResourceGenerationTask.query.filter_by(task_id=row.generation_task_id).first()
        if task:
            task.audit_report = report
            db.session.commit()
        return {
            'resource_id': resource_id,
            'generation_task_id': row.generation_task_id,
            'audit_report': report,
        }

    @staticmethod
    def review_metrics() -> dict:
        rows = PersonalizedLearningResource.query.all()
        status_counts = {
            status: sum(1 for row in rows if row.review_status == status)
            for status in ('pending_review', 'approved', 'rejected')
        }
        risk_counts: dict[str, int] = {}
        review_minutes = []
        verdict_counts: dict[str, int] = {}
        dimension_totals: dict[str, float] = {}
        dimension_samples = 0
        task_ids = {row.generation_task_id for row in rows}
        tasks = {
            task.task_id: task
            for task in ResourceGenerationTask.query.filter(
                ResourceGenerationTask.task_id.in_(task_ids)
            ).all()
        } if task_ids else {}
        for row in rows:
            for risk in row.risk_reasons or []:
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            if row.reviewed_at and row.created_at:
                review_minutes.append(
                    max(0, (row.reviewed_at - row.created_at).total_seconds() / 60)
                )
        counted_tasks: set[str] = set()
        for task_id, task in tasks.items():
            audit = task.audit_report if task else None
            if not isinstance(audit, dict) or task_id in counted_tasks:
                continue
            counted_tasks.add(task_id)
            verdict = str(audit.get('verdict') or '')
            if verdict:
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            dims = audit.get('dimensions') or {}
            if dims:
                dimension_samples += 1
                for key, value in dims.items():
                    dimension_totals[key] = dimension_totals.get(key, 0.0) + float(value or 0)
        avg_dimensions = {
            key: round(total / dimension_samples, 1)
            for key, total in dimension_totals.items()
        } if dimension_samples else {}
        return {
            'total_resources': len(rows),
            'status_counts': status_counts,
            'pending_review_count': status_counts['pending_review'],
            'anomaly_pending_count': sum(
                1 for row in rows
                if row.review_status == 'pending_review' and bool(row.is_anomaly)
            ),
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
            'verdict_distribution': [
                {'verdict': verdict, 'count': count}
                for verdict, count in sorted(
                    verdict_counts.items(), key=lambda item: (-item[1], item[0])
                )
            ],
            'avg_dimension_scores': avg_dimensions,
        }

    @staticmethod
    def smart_review(reviewer_id: int) -> dict:
        """教师一键智能审核：调用 OpenAI 审核智能体，正常项自动批准，异常项保留待审。"""
        from agents.resource_review_agent import is_hard_risk, review_generated_resource

        rows = PersonalizedLearningResource.query.filter_by(
            review_status='pending_review'
        ).order_by(PersonalizedLearningResource.created_at.asc()).all()
        approved = 0
        flagged = 0
        results = []
        # 按生成任务复用审核结果，避免同包重复调用 OpenAI
        cache: dict[str, dict] = {}
        for row in rows:
            task_id = row.generation_task_id
            if task_id not in cache:
                task = ResourceGenerationTask.query.filter_by(task_id=task_id).first()
                audit_report = task.audit_report if task and isinstance(task.audit_report, dict) else {}
                bundle = PersonalizedResourceService._resolve_bundle_for_resource(row) or {}
                cache[task_id] = review_generated_resource(
                    bundle=bundle,
                    knowledge_key=row.knowledge_key,
                    audit_report=audit_report,
                    risk_reasons=list(row.risk_reasons or []),
                    title=row.title or '',
                )
                if task and isinstance(audit_report, dict):
                    metadata = dict(audit_report.get('metadata') or {})
                    metadata['ai_agent_review'] = cache[task_id]
                    if cache[task_id].get('teacher_summary'):
                        metadata['crewai_notes'] = cache[task_id]['teacher_summary']
                    audit_report['metadata'] = metadata
                    task.audit_report = audit_report

            ai_review = cache[task_id]
            row.ai_review = ai_review
            item_risks = [
                r for r in (row.risk_reasons or [])
                if r not in ('ai_anomaly', 'ai_reject')
            ]
            item_hard = any(is_hard_risk(r) for r in item_risks)
            decision = ai_review.get('decision')
            # 仅硬异常 / AI 明确 needs_review|reject 留给教师；软风险立刻放行
            keep_for_teacher = (
                item_hard
                or decision == 'reject'
                or (decision == 'needs_review' and bool(ai_review.get('is_anomaly')))
            )
            if not keep_for_teacher:
                row.review_status = 'approved'
                row.review_reason = (
                    ai_review.get('review_reason')
                    or 'AI 审核智能体：内容正常，已自动批准发布。'
                )[:500]
                row.reviewed_by = reviewer_id
                row.reviewed_at = utc_now()
                row.is_anomaly = False
                row.student_warning = None
                row.risk_reasons = [
                    r for r in (row.risk_reasons or [])
                    if r not in ('ai_anomaly', 'ai_reject')
                ]
                approved += 1
                results.append({'id': row.id, 'decision': 'auto_approve'})
            else:
                row.is_anomaly = True
                row.student_warning = (
                    ai_review.get('student_warning')
                    or '本资源由 AI 生成且存在异常风险，请谨慎参考并以教师讲解为准。'
                )[:500]
                row.review_reason = (ai_review.get('review_reason') or row.review_reason or '')[:500]
                risks = list(row.risk_reasons or [])
                tag = 'ai_reject' if decision == 'reject' else 'ai_anomaly'
                if tag not in risks:
                    risks.append(tag)
                row.risk_reasons = risks
                flagged += 1
                results.append({
                    'id': row.id,
                    'decision': decision or 'needs_review',
                    'is_anomaly': True,
                })
        db.session.commit()
        return {
            'approved_count': approved,
            'flagged_count': flagged,
            'total': len(rows),
            'items': results,
        }

    @staticmethod
    def release_soft_pending(reviewer_id: int = 0) -> dict:
        """存量修复：无硬风险的 pending 立刻批准，仅硬异常留给教师。"""
        from agents.resource_review_agent import is_hard_risk

        rows = PersonalizedLearningResource.query.filter_by(
            review_status='pending_review'
        ).all()
        approved = 0
        kept = 0
        for row in rows:
            risks = [
                r for r in (row.risk_reasons or [])
                if r not in ('ai_anomaly',)
            ]
            if any(is_hard_risk(r) for r in risks) or 'ai_reject' in (row.risk_reasons or []):
                row.is_anomaly = True
                kept += 1
                continue
            row.review_status = 'approved'
            row.is_anomaly = False
            row.student_warning = None
            row.review_reason = '系统：无硬伤，自动放行给学生。'
            row.reviewed_by = reviewer_id or None
            row.reviewed_at = utc_now()
            row.risk_reasons = [
                r for r in (row.risk_reasons or [])
                if r not in ('ai_anomaly', 'ai_reject')
            ]
            approved += 1
        db.session.commit()
        return {'approved_count': approved, 'kept_anomaly_count': kept, 'total': len(rows)}

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
        if status == 'approved':
            row.is_anomaly = False
            row.student_warning = None
        db.session.commit()
        return row.to_dict()
