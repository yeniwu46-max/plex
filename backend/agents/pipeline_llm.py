# -*- coding: utf-8 -*-
"""学习流水线 LLM 增强 — 在规则 baseline 之上合并 LLM 输出。"""
from __future__ import annotations

import json
from typing import Any

from agents.llm_client import api_key_configured, chat_json


def merge_trace_summary(trace: list[dict], agent_id: str, summary: str, *, source: str) -> None:
    for row in trace:
        if row.get('agentId') == agent_id:
            row['summary'] = summary[:160]
            row['source'] = source
            return


def enhance_student_pipeline(baseline: dict, payload: dict) -> dict:
    """规则 baseline 之上用 LLM 增强 diagnosis 与 feedback。"""
    if not api_key_configured():
        return baseline

    diagnosis = baseline.get('diagnosis') or {}
    code_analysis = baseline.get('codeAnalysis') or {}
    feedback = baseline.get('feedback') or {}
    trace = list(baseline.get('pipelineTrace') or [])

    context: dict[str, Any] = {
        'code': payload.get('code', ''),
        'stderr': payload.get('stderr') or payload.get('errorMessage'),
        'expectedOutput': payload.get('expectedOutput'),
        'knowledgePoints': payload.get('knowledgePoints') or [],
        'answerStatus': payload.get('answerStatus'),
        'baselineDiagnosis': diagnosis.get('diagnosis'),
        'errorType': diagnosis.get('errorType'),
        'weakPoints': diagnosis.get('weakPoints'),
        'codeIssueSummary': code_analysis.get('codeIssueSummary'),
        'baselineFeedback': feedback.get('shortFeedback'),
    }

    llm_diagnosis = chat_json(
        system=(
            '你是 Python 初学者学习诊断专家。根据练习上下文输出 JSON，字段：'
            'diagnosis(字符串,80字内)、weakPoints(字符串数组,最多3个)、confidence(0-1浮点数)。'
            '只输出 JSON，不要 markdown。'
        ),
        user=json.dumps(context, ensure_ascii=False),
        timeout=35.0,
    )
    if llm_diagnosis:
        if llm_diagnosis.get('diagnosis'):
            diagnosis = {**diagnosis, 'diagnosis': str(llm_diagnosis['diagnosis'])[:200]}
        if isinstance(llm_diagnosis.get('weakPoints'), list) and llm_diagnosis['weakPoints']:
            diagnosis = {**diagnosis, 'weakPoints': llm_diagnosis['weakPoints'][:3]}
        if llm_diagnosis.get('confidence') is not None:
            try:
                diagnosis = {**diagnosis, 'confidence': float(llm_diagnosis['confidence'])}
            except (TypeError, ValueError):
                pass
        merge_trace_summary(
            trace,
            'learning_diagnosis',
            str(diagnosis.get('diagnosis', ''))[:160],
            source='crewai_llm',
        )

    feedback_context = {
        **context,
        'diagnosis': diagnosis.get('diagnosis'),
        'stepHintsBaseline': feedback.get('stepHints'),
    }
    llm_feedback = chat_json(
        system=(
            '你是 Python 初学者学习反馈教练。根据诊断与代码分析输出 JSON，字段：'
            'shortFeedback(字符串,100字内)、stepHints(字符串数组,2-3条)、encouragement(字符串,50字内)。'
            '不要给出完整代码答案。只输出 JSON。'
        ),
        user=json.dumps(feedback_context, ensure_ascii=False),
        timeout=35.0,
    )
    if llm_feedback:
        merged_feedback = {**feedback}
        if llm_feedback.get('shortFeedback'):
            merged_feedback['shortFeedback'] = str(llm_feedback['shortFeedback'])[:200]
        if isinstance(llm_feedback.get('stepHints'), list) and llm_feedback['stepHints']:
            merged_feedback['stepHints'] = [str(s) for s in llm_feedback['stepHints'][:3]]
        if llm_feedback.get('encouragement'):
            merged_feedback['encouragement'] = str(llm_feedback['encouragement'])[:120]
        merged_feedback['strategyType'] = merged_feedback.get('strategyType', 'micro_fix')
        feedback = merged_feedback
        merge_trace_summary(
            trace,
            'feedback',
            str(feedback.get('shortFeedback', ''))[:160],
            source='crewai_llm',
        )

    if not (llm_diagnosis or llm_feedback):
        return baseline

    for row in trace:
        if 'source' not in row:
            row['source'] = 'rules_baseline'

    from agents.crew import backend_name

    return {
        **baseline,
        'diagnosis': diagnosis,
        'feedback': feedback,
        'pipelineTrace': trace,
        'backend': backend_name() if backend_name() == 'crewai' else 'llm',
        'llmEnhanced': True,
    }
