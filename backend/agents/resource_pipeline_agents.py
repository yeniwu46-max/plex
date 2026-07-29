# -*- coding: utf-8 -*-
"""资源生成流水线智能体：真正参考画像与课程知识库，并按角色使用独立 OpenAI Key。

- 画像解释：OPENAI_PROFILE_INTERPRETER_API_KEY
- 知识检索：OPENAI_KNOWLEDGE_RETRIEVER_API_KEY
- 教学设计：OPENAI_INSTRUCTIONAL_DESIGNER_API_KEY
- 路径规划：OPENAI_PATH_PLANNER_API_KEY
"""
from __future__ import annotations

import json
import os
from typing import Any


def _llm_json(
    system: str,
    user: str,
    *,
    agent: str,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    try:
        from flask import current_app, has_app_context

        if has_app_context() and current_app.config.get('TESTING'):
            if not current_app.config.get('LLM_ALLOW_IN_TESTS'):
                return None
    except Exception:
        pass
    try:
        from agents.llm_client import chat_json, openai_agent_provider

        provider = openai_agent_provider(agent)
        if not provider:
            return None
        return chat_json(
            system=system,
            user=user,
            timeout=timeout,
            max_tokens=900,
            provider=provider,
            temperature=0.3,
            force_json_object=True,
        )
    except Exception:
        return None


def _provider_meta(agent: str) -> tuple[str, str]:
    try:
        from agents.llm_client import openai_agent_provider

        provider = openai_agent_provider(agent)
        if not provider:
            return 'local_rules', 'deterministic_contract'
        _key, endpoint, model = provider
        if 'openai.com' in endpoint:
            return 'openai', model
        return 'llm', model
    except Exception:
        return 'local_rules', 'deterministic_contract'


def _timeout() -> float:
    return float(os.getenv('RESOURCE_PIPELINE_AGENT_TIMEOUT', '20') or 20)


def interpret_profile(
    *,
    profile: dict,
    knowledge_key: str,
    knowledge_label: str,
    baseline: dict,
) -> tuple[dict, str, str]:
    """画像解释智能体：参考真实画像字段，输出学习策略。"""
    agent = 'profile_interpreter'
    backend, model = _provider_meta(agent)
    payload = {
        'knowledge_key': knowledge_key,
        'knowledge_label': knowledge_label,
        'student_profile': profile,
        'baseline_strategy': baseline,
    }
    raw = _llm_json(
        system=(
            '你是高校 Python 课程的「画像解释智能体」。'
            '必须依据学生画像字段给出本知识点的学习策略，禁止编造画像中没有的信息。'
            '输出 JSON：'
            'difficulty_target(30-80整数)、explanation_style(字符串)、'
            'interest_context(字符串)、learning_pace(字符串)、'
            'focus_points(字符串数组,最多4条)、profile_rationale(中文,说明参考了哪些画像字段)、'
            'profile_dimensions_used(字符串数组)。'
        ),
        user=json.dumps(payload, ensure_ascii=False),
        agent=agent,
        timeout=_timeout(),
    )
    if not isinstance(raw, dict):
        out = dict(baseline)
        out['profile_rationale'] = (
            f'规则回退：依据画像字段 {", ".join(baseline.get("profile_dimensions_used") or []) or "默认"} '
            f'设定「{knowledge_label}」学习策略。'
        )
        out['focus_points'] = out.get('focus_points') or [knowledge_label]
        out['agent_backend'] = 'local_rules'
        return out, 'local_rules', 'deterministic_contract'

    result = dict(baseline)
    try:
        difficulty = int(raw.get('difficulty_target', baseline.get('difficulty_target', 55)))
    except (TypeError, ValueError):
        difficulty = int(baseline.get('difficulty_target') or 55)
    result['difficulty_target'] = max(30, min(80, difficulty))
    for key in ('explanation_style', 'interest_context', 'learning_pace', 'profile_rationale'):
        if raw.get(key):
            result[key] = str(raw[key])[:200]
    if isinstance(raw.get('focus_points'), list):
        result['focus_points'] = [str(x)[:60] for x in raw['focus_points'][:4]]
    if isinstance(raw.get('profile_dimensions_used'), list) and raw['profile_dimensions_used']:
        result['profile_dimensions_used'] = [
            str(x) for x in raw['profile_dimensions_used'] if str(x).strip()
        ][:12]
    result['agent_backend'] = backend
    return result, backend, model


def retrieve_knowledge(
    *,
    knowledge_key: str,
    knowledge_label: str,
    profile_strategy: dict,
    baseline: dict,
    section: dict,
    citation: dict,
    knowledge_node: dict,
) -> tuple[dict, str, str]:
    """知识检索智能体：必须参考课程知识库原文。"""
    agent = 'knowledge_retriever'
    backend, model = _provider_meta(agent)
    kb_excerpt = {
        'document_id': section.get('document_id') or citation.get('document_id'),
        'source_file': section.get('source_file'),
        'section_title': section.get('section_title'),
        'concept': (section.get('concept') or '')[:500],
        'good_example': (section.get('good_example') or '')[:400],
        'bad_example': (section.get('bad_example') or '')[:300],
        'common_mistakes': (section.get('common_mistakes') or '')[:300],
        'base_question': (section.get('base_question') or '')[:200],
        'advanced_question': (section.get('advanced_question') or '')[:200],
        'source': section.get('source') or '',
    }
    payload = {
        'knowledge_key': knowledge_key,
        'knowledge_label': knowledge_label,
        'profile_strategy': {
            'difficulty_target': profile_strategy.get('difficulty_target'),
            'explanation_style': profile_strategy.get('explanation_style'),
            'focus_points': profile_strategy.get('focus_points'),
            'interest_context': profile_strategy.get('interest_context'),
        },
        'course_knowledge_base': kb_excerpt,
    }
    raw = _llm_json(
        system=(
            '你是高校 Python 课程的「知识检索智能体」。'
            '只能基于提供的 course_knowledge_base 做检索与提炼，禁止引入库外知识点。'
            '输出 JSON：'
            'retrieved_snippet(字符串,摘录概念要点)、'
            'retrieved_passages(对象数组,每项含 title/snippet/field，最多4条)、'
            'teaching_hooks(字符串数组,最多3条，来自正例/反例/常见错误)、'
            'retrieval_rationale(中文,说明参考了知识库哪些字段)。'
        ),
        user=json.dumps(payload, ensure_ascii=False),
        agent=agent,
        timeout=_timeout(),
    )

    result = dict(baseline)
    result['knowledge_node'] = knowledge_node
    result['course_section'] = {
        'document_id': kb_excerpt['document_id'],
        'source_file': kb_excerpt['source_file'],
        'section_title': kb_excerpt['section_title'],
        'concept': kb_excerpt['concept'][:240],
        'source': kb_excerpt['source'],
    }
    result['citation_count'] = 1
    result['citations'] = [citation]

    if not isinstance(raw, dict):
        passages = []
        for field, title in (
            ('concept', '概念'),
            ('good_example', '正例'),
            ('common_mistakes', '常见错误'),
        ):
            text = str(kb_excerpt.get(field) or '').strip()
            if text:
                passages.append({'title': title, 'snippet': text[:160], 'field': field})
        result['retrieved_passages'] = passages
        result['teaching_hooks'] = [p['snippet'][:80] for p in passages[1:3]]
        result['retrieval_rationale'] = (
            f'规则回退：已从课程知识库 '
            f'{kb_excerpt.get("source_file") or kb_excerpt.get("document_id") or knowledge_key} '
            f'读取「{knowledge_label}」原文并建立引用。'
        )
        result['agent_backend'] = 'local_rules'
        return result, 'local_rules', 'deterministic_contract'

    if raw.get('retrieved_snippet'):
        result['retrieved_snippet'] = str(raw['retrieved_snippet'])[:240]
    passages = raw.get('retrieved_passages')
    if isinstance(passages, list) and passages:
        cleaned = []
        for row in passages[:4]:
            if not isinstance(row, dict):
                continue
            snippet = str(row.get('snippet') or '').strip()
            if not snippet:
                continue
            cleaned.append({
                'title': str(row.get('title') or '知识片段')[:40],
                'snippet': snippet[:200],
                'field': str(row.get('field') or '')[:40],
            })
        if cleaned:
            result['retrieved_passages'] = cleaned
            result['citation_count'] = max(1, len(cleaned))
    if isinstance(raw.get('teaching_hooks'), list):
        result['teaching_hooks'] = [str(x)[:100] for x in raw['teaching_hooks'][:3]]
    if raw.get('retrieval_rationale'):
        result['retrieval_rationale'] = str(raw['retrieval_rationale'])[:240]
    result['agent_backend'] = backend
    return result, backend, model


def design_instruction(
    *,
    requested_types: list[str],
    profile_strategy: dict,
    knowledge_context: dict,
    pedagogical_context: dict,
    baseline_analysis: dict,
) -> tuple[dict, str, str]:
    """教学设计智能体：参考画像策略与检索结果设计教学编排。"""
    agent = 'instructional_designer'
    backend, model = _provider_meta(agent)
    payload = {
        'requested_types': requested_types,
        'pedagogical_context': pedagogical_context,
        'profile_strategy': {
            k: profile_strategy.get(k)
            for k in (
                'difficulty_target',
                'explanation_style',
                'interest_context',
                'learning_pace',
                'focus_points',
                'profile_rationale',
            )
        },
        'retrieved_knowledge': {
            'knowledge_key': knowledge_context.get('knowledge_key'),
            'knowledge_label': knowledge_context.get('knowledge_label'),
            'retrieved_snippet': knowledge_context.get('retrieved_snippet'),
            'retrieved_passages': knowledge_context.get('retrieved_passages'),
            'teaching_hooks': knowledge_context.get('teaching_hooks'),
            'course_section': knowledge_context.get('course_section'),
        },
        'baseline_analysis': {
            'target': baseline_analysis.get('target'),
            'learning_stage': baseline_analysis.get('learning_stage'),
            'learning_styles': baseline_analysis.get('learning_styles'),
            'objectives': baseline_analysis.get('objectives'),
        },
    }
    raw = _llm_json(
        system=(
            '你是高校 Python 课程的「教学设计智能体」。'
            '必须同时参考学生画像策略与课程知识检索结果，设计本知识点的教学方案。'
            '输出 JSON：'
            'objectives(字符串数组,2-4条)、'
            'sequence(资源类型数组，只能从 requested_types 中选)、'
            'difficulty_target(30-80)、'
            'explanation_style(字符串)、'
            'case_angle(字符串,案例切入角度)、'
            'exercise_plan(字符串,练习分层说明)、'
            'design_rationale(中文,说明如何参考了画像与知识库)。'
        ),
        user=json.dumps(payload, ensure_ascii=False),
        agent=agent,
        timeout=_timeout(),
    )

    result = dict(baseline_analysis)
    result['knowledge_key'] = knowledge_context.get('knowledge_key')
    result['resource_types'] = list(requested_types)
    result['difficulty_target'] = profile_strategy.get('difficulty_target')
    result['explanation_style'] = profile_strategy.get('explanation_style')
    result['interest_context'] = profile_strategy.get('interest_context')
    result['learning_pace'] = profile_strategy.get('learning_pace')
    allowed = set(requested_types)
    result['sequence'] = list(requested_types)

    if not isinstance(raw, dict):
        result['design_rationale'] = (
            '规则回退：按画像难度与知识库概念/正例/练习字段生成教学编排。'
        )
        result['case_angle'] = str(
            (knowledge_context.get('teaching_hooks') or ['结合课程正例讲解'])[0]
        )[:120]
        result['exercise_plan'] = '基础题巩固概念，进阶题综合应用'
        result['agent_backend'] = 'local_rules'
        return result, 'local_rules', 'deterministic_contract'

    if isinstance(raw.get('objectives'), list) and raw['objectives']:
        result['objectives'] = [str(x)[:80] for x in raw['objectives'][:4]]
    if isinstance(raw.get('sequence'), list) and raw['sequence']:
        seq = [str(x) for x in raw['sequence'] if str(x) in allowed]
        if seq:
            for item in requested_types:
                if item not in seq:
                    seq.append(item)
            result['sequence'] = seq
    try:
        difficulty = int(raw.get('difficulty_target', result.get('difficulty_target') or 55))
        result['difficulty_target'] = max(30, min(80, difficulty))
    except (TypeError, ValueError):
        pass
    for key in ('explanation_style', 'case_angle', 'exercise_plan', 'design_rationale'):
        if raw.get(key):
            result[key] = str(raw[key])[:240]
    result['agent_backend'] = backend
    return result, backend, model


def plan_learning_path(
    *,
    knowledge_key: str,
    knowledge_label: str,
    quality_report: dict,
    profile_strategy: dict | None = None,
    instructional_design: dict | None = None,
    baseline: dict,
) -> tuple[dict, str, str]:
    """路径规划智能体：根据审核结果与教学设计规划可见资源顺序。"""
    agent = 'path_planner'
    backend, model = _provider_meta(agent)
    items = quality_report.get('items') or []
    payload = {
        'knowledge_key': knowledge_key,
        'knowledge_label': knowledge_label,
        'approved_types': [
            item.get('resource_type')
            for item in items
            if item.get('review_status') == 'approved'
        ],
        'pending_types': [
            item.get('resource_type')
            for item in items
            if item.get('review_status') == 'pending_review'
        ],
        'anomaly_count': sum(1 for item in items if item.get('is_anomaly')),
        'design_sequence': (instructional_design or {}).get('sequence') or [],
        'profile_strategy': {
            'difficulty_target': (profile_strategy or {}).get('difficulty_target'),
            'learning_pace': (profile_strategy or {}).get('learning_pace'),
            'focus_points': (profile_strategy or {}).get('focus_points'),
        },
        'baseline': baseline,
    }
    raw = _llm_json(
        system=(
            '你是高校 Python 课程的「路径规划智能体」。'
            '根据已批准/待审资源与教学设计，规划学生学习路径。'
            '输出 JSON：'
            'visible_resource_types(字符串数组,优先已批准类型)、'
            'study_order(字符串数组,建议学习顺序)、'
            'preview_pending(boolean,是否允许预览待审资源)、'
            'recommendation_reason(中文,说明路径依据)、'
            'next_action(中文,下一步学习建议)。'
        ),
        user=json.dumps(payload, ensure_ascii=False),
        agent=agent,
        timeout=_timeout(),
    )

    result = dict(baseline)
    result['agent_backend'] = backend
    if not isinstance(raw, dict):
        result['path_rationale'] = result.get('recommendation_reason')
        result['agent_backend'] = 'local_rules'
        return result, 'local_rules', 'deterministic_contract'

    approved = set(payload['approved_types'])
    pending = set(payload['pending_types'])
    if isinstance(raw.get('visible_resource_types'), list):
        visible = [
            str(x) for x in raw['visible_resource_types']
            if str(x) in approved or str(x) in pending
        ]
        for item in payload['approved_types']:
            if item and item not in visible:
                visible.append(item)
        if visible:
            result['visible_resource_types'] = visible
    if isinstance(raw.get('study_order'), list) and raw['study_order']:
        result['study_order'] = [str(x)[:40] for x in raw['study_order'][:8]]
    if 'preview_pending' in raw:
        result['preview_pending'] = bool(raw.get('preview_pending'))
    if raw.get('recommendation_reason'):
        result['recommendation_reason'] = str(raw['recommendation_reason'])[:240]
    if raw.get('next_action'):
        result['next_action'] = str(raw['next_action'])[:160]
    result['path_rationale'] = result.get('recommendation_reason')
    result['agent_backend'] = backend
    return result, backend, model
