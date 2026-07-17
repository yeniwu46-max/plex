"""LangGraph orchestration with sequential fallback."""
from __future__ import annotations

from typing import Any, TypedDict

from .case_checker import check_cases
from .code_checker import check_code
from .exercise_checker import check_exercises
from .knowledge_checker import check_knowledge
from .pedagogy_checker import check_pedagogy
from .report_builder import build_report
from .schema import AuditReport, StepResult


class AuditState(TypedDict, total=False):
    bundle: dict
    knowledge_key: str
    profile: dict
    confidence: float
    citations: list[dict]
    steps: list[StepResult]
    report: AuditReport


def _sequential_run(state: AuditState) -> AuditReport:
    bundle = state['bundle']
    knowledge_key = state['knowledge_key']
    profile = state.get('profile') or {}
    confidence = float(state.get('confidence') or 0.9)
    citations = state.get('citations')

    steps = [
        check_knowledge(bundle, knowledge_key, confidence=confidence, citations=citations),
        check_pedagogy(bundle, knowledge_key, profile),
        check_cases(bundle, knowledge_key),
        check_exercises(bundle, knowledge_key),
        check_code(bundle, knowledge_key),
    ]
    return build_report(
        bundle,
        knowledge_key,
        steps,
        confidence=confidence,
        citations=citations,
        backend='sequential',
    )


def run_audit_graph(state: AuditState) -> AuditReport:
    try:
        from langgraph.graph import END, START, StateGraph

        def node1(s: AuditState) -> dict[str, Any]:
            return {'steps': [check_knowledge(
                s['bundle'], s['knowledge_key'],
                confidence=float(s.get('confidence') or 0.9),
                citations=s.get('citations'),
            )]}

        def node2(s: AuditState) -> dict[str, Any]:
            steps = list(s.get('steps') or [])
            steps.append(check_pedagogy(s['bundle'], s['knowledge_key'], s.get('profile')))
            return {'steps': steps}

        def node3(s: AuditState) -> dict[str, Any]:
            steps = list(s.get('steps') or [])
            steps.append(check_cases(s['bundle'], s['knowledge_key']))
            return {'steps': steps}

        def node4(s: AuditState) -> dict[str, Any]:
            steps = list(s.get('steps') or [])
            steps.append(check_exercises(s['bundle'], s['knowledge_key']))
            return {'steps': steps}

        def node5(s: AuditState) -> dict[str, Any]:
            steps = list(s.get('steps') or [])
            steps.append(check_code(s['bundle'], s['knowledge_key']))
            return {'steps': steps}

        def node6(s: AuditState) -> dict[str, Any]:
            report = build_report(
                s['bundle'],
                s['knowledge_key'],
                list(s.get('steps') or []),
                confidence=float(s.get('confidence') or 0.9),
                citations=s.get('citations'),
                backend='langgraph',
            )
            return {'report': report}

        graph = StateGraph(AuditState)
        graph.add_node('knowledge', node1)
        graph.add_node('pedagogy', node2)
        graph.add_node('cases', node3)
        graph.add_node('exercises', node4)
        graph.add_node('code', node5)
        graph.add_node('report', node6)
        graph.add_edge(START, 'knowledge')
        graph.add_edge('knowledge', 'pedagogy')
        graph.add_edge('pedagogy', 'cases')
        graph.add_edge('cases', 'exercises')
        graph.add_edge('exercises', 'code')
        graph.add_edge('code', 'report')
        graph.add_edge('report', END)
        result = graph.compile().invoke(state)
        report = result.get('report')
        if isinstance(report, AuditReport):
            return report
    except Exception:
        pass
    return _sequential_run(state)
