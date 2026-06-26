# -*- coding: utf-8 -*-
"""LangGraph 学习路径子图（无 LangGraph 时顺序执行同等步骤）。"""
from __future__ import annotations

import time
from typing import Any, TypedDict

from app.services.learning_path import LearningPathService
from app.services.mistake import MistakeService


class LearningPathState(TypedDict, total=False):
    user_id: int
    focus_node: str | None
    diagnosis_payload: dict | None
    recent_mistakes: list
    path_plan: dict
    rationale: str
    agent_trace: list
    errors: list


def _trace_step(agent_id: str, name: str, status: str, latency_ms: float, summary: str) -> dict:
    return {
        'agentId': agent_id,
        'name': name,
        'status': status,
        'latencyMs': round(latency_ms, 1),
        'summary': summary,
    }


def load_context(state: LearningPathState) -> LearningPathState:
    started = time.perf_counter()
    user_id = state.get('user_id')
    mistakes = []
    if user_id:
        try:
            mistakes = MistakeService.list_recent_with_meta(user_id, limit=8)
        except Exception:
            mistakes = []
    trace = list(state.get('agent_trace') or [])
    trace.append(_trace_step(
        'load_context',
        '加载学情上下文',
        'success',
        (time.perf_counter() - started) * 1000,
        f'错题 {len(mistakes)} 条',
    ))
    return {
        **state,
        'recent_mistakes': mistakes,
        'agent_trace': trace,
    }


def plan_path(state: LearningPathState) -> LearningPathState:
    started = time.perf_counter()
    user_id = state.get('user_id')
    if not user_id:
        return {**state, 'errors': ['user_id required'], 'path_plan': {}}
    plan = LearningPathService.plan(
        user_id,
        focus_node_id=state.get('focus_node'),
        diagnosis_payload=state.get('diagnosis_payload'),
    )
    trace = list(state.get('agent_trace') or [])
    active = plan.get('active_node_id')
    trace.append(_trace_step(
        'plan_path',
        '路径规划',
        'success',
        (time.perf_counter() - started) * 1000,
        f'下一步 {active or "—"} · {plan.get("graph_backend")}',
    ))
    return {**state, 'path_plan': plan, 'agent_trace': trace}


def build_rationale(state: LearningPathState) -> LearningPathState:
    started = time.perf_counter()
    plan = state.get('path_plan') or {}
    nba = plan.get('next_best_action') or {}
    remediation = plan.get('remediation_paths') or []
    parts = [nba.get('reason', '已生成学习顺序')]
    if remediation:
        parts.append(f'存在 {len(remediation)} 条补救路径待完成')
    rationale = '；'.join(parts)
    trace = list(state.get('agent_trace') or [])
    trace.append(_trace_step(
        'explain_path',
        '路径说明',
        'success',
        (time.perf_counter() - started) * 1000,
        rationale[:80],
    ))
    return {**state, 'rationale': rationale, 'agent_trace': trace}


def _run_sequential(payload: dict) -> dict:
    state: LearningPathState = {
        'user_id': payload.get('user_id'),
        'focus_node': payload.get('focus_node') or payload.get('focus_node_id'),
        'diagnosis_payload': payload.get('diagnosis') or payload.get('diagnosis_payload'),
        'agent_trace': [],
        'errors': [],
    }
    state = load_context(state)
    state = plan_path(state)
    state = build_rationale(state)
    plan = state.get('path_plan') or {}
    plan['agent_trace'] = {
        'backend': 'sequential',
        'steps': state.get('agent_trace') or [],
    }
    return {
        'ordered_nodes': plan.get('ordered_nodes', []),
        'active_node_id': plan.get('active_node_id'),
        'next_best_action': plan.get('next_best_action'),
        'remediation_paths': plan.get('remediation_paths', []),
        'graph_backend': plan.get('graph_backend'),
        'topology_source': plan.get('topology_source'),
        'rationale': state.get('rationale'),
        'agent_trace': plan.get('agent_trace'),
        'nextKnowledgePoint': _legacy_next_kp(plan),
        'recommendedExercises': _legacy_exercises(plan),
        'reviewPlan': _legacy_review(plan),
        'estimatedDifficulty': _legacy_difficulty(plan),
    }


def _legacy_next_kp(plan: dict) -> str:
    active = plan.get('active_node_id')
    if not active:
        return 'range 的边界规则'
    for node in plan.get('ordered_nodes') or []:
        if node.get('id') == active:
            return node.get('label') or active
    return active


def _legacy_exercises(plan: dict) -> list[str]:
    exercises: list[str] = []
    for node in (plan.get('ordered_nodes') or [])[:2]:
        for trial in node.get('recommended_trials') or []:
            title = trial.get('title') or trial.get('question_id')
            if title:
                exercises.append(str(title))
    return exercises[:3] or ['完成 1 道巩固练习']


def _legacy_review(plan: dict) -> list[str]:
    steps: list[str] = []
    for node in (plan.get('ordered_nodes') or [])[:3]:
        steps.append(f'学习 {node.get("label", node.get("id"))}')
    return steps or ['复习变量与基本类型', '完成巩固练习']


def _legacy_difficulty(plan: dict) -> str:
    remediation = plan.get('remediation_paths') or []
    if remediation:
        return 'easy'
    active = plan.get('active_node_id')
    for node in plan.get('ordered_nodes') or []:
        if node.get('id') == active:
            return 'easy' if node.get('default_difficulty', 1) <= 1 else 'medium'
    return 'medium'


def _build_langgraph() -> Any:
    from langgraph.graph import END, StateGraph

    graph = StateGraph(LearningPathState)
    graph.add_node('load_context', load_context)
    graph.add_node('plan_path', plan_path)
    graph.add_node('build_rationale', build_rationale)
    graph.set_entry_point('load_context')
    graph.add_edge('load_context', 'plan_path')
    graph.add_edge('plan_path', 'build_rationale')
    graph.add_edge('build_rationale', END)
    return graph.compile()


def run_learning_path_graph(payload: dict) -> dict:
    try:
        app = _build_langgraph()
        state: LearningPathState = {
            'user_id': payload.get('user_id'),
            'focus_node': payload.get('focus_node') or payload.get('focus_node_id'),
            'diagnosis_payload': payload.get('diagnosis') or payload.get('diagnosis_payload'),
            'agent_trace': [],
            'errors': [],
        }
        result = app.invoke(state)
        plan = result.get('path_plan') or {}
        plan['agent_trace'] = {
            'backend': 'langgraph',
            'steps': result.get('agent_trace') or [],
        }
        return {
            'ordered_nodes': plan.get('ordered_nodes', []),
            'active_node_id': plan.get('active_node_id'),
            'next_best_action': plan.get('next_best_action'),
            'remediation_paths': plan.get('remediation_paths', []),
            'graph_backend': plan.get('graph_backend'),
            'topology_source': plan.get('topology_source'),
            'rationale': result.get('rationale'),
            'agent_trace': plan.get('agent_trace'),
            'nextKnowledgePoint': _legacy_next_kp(plan),
            'recommendedExercises': _legacy_exercises(plan),
            'reviewPlan': _legacy_review(plan),
            'estimatedDifficulty': _legacy_difficulty(plan),
        }
    except ImportError:
        return _run_sequential(payload)
    except Exception:
        return _run_sequential(payload)
