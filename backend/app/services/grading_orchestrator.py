"""试炼提交后的智能体编排执行 — 读取平台配置并按序运行 grading + learning pipeline。"""
from __future__ import annotations

import time
from typing import Any

from agents.crew import backend_name, run_student_diagnose
from agents import code_analysis_agent, feedback_agent, knowledge_graph_agent, learning_diagnosis_agent
from app.data.agent_registry import GRADING_AGENT_MAP, LEARNING_AGENT_MAP
from app.models import TrialQuestion, TrialQuestionProgress
from app.services.question_generator import QuestionGenerator
from app.services.system_setting import SystemSettingService

DEFAULT_BUDGET_SEC = 20.0
CREWAI_BUDGET_SEC = 55.0
AGENT_BUDGET_SEC = 5.0
CREWAI_AGENT_BUDGET_SEC = 50.0


def _total_budget_sec() -> float:
    name = backend_name()
    return CREWAI_BUDGET_SEC if name in ('crewai', 'llm') else DEFAULT_BUDGET_SEC


def _agent_budget_sec() -> float:
    name = backend_name()
    return CREWAI_AGENT_BUDGET_SEC if name in ('crewai', 'llm') else AGENT_BUDGET_SEC

_GRADING_TO_LEARNING = {
    'code-syntax': 'code_analysis',
    'logic-step': 'learning_diagnosis',
    'knowledge-coverage': 'knowledge_graph',
    'feedback-coach': 'feedback',
    'rubric-alignment': 'feedback',
}


class GradingOrchestrator:
    @staticmethod
    def summarize_trace(trace: list[dict]) -> dict:
        items = []
        for row in trace[:8]:
            items.append(
                {
                    'agentId': row.get('agentId'),
                    'name': row.get('name'),
                    'status': row.get('status', 'success'),
                    'summary': (row.get('summary') or '')[:160],
                    'backend': row.get('backend'),
                }
            )
        return {
            'count': len(trace),
            'items': items,
            'has_error': any(row.get('status') == 'error' for row in trace),
        }

    @staticmethod
    def run_after_submit(
        *,
        user_id: int,
        question: TrialQuestion,
        progress: TrialQuestionProgress,
        grade_result: dict,
    ) -> list[dict]:
        config = SystemSettingService.get_global_orchestration()
        if not config.get('enabled', True):
            return []

        qtype = question.question_type or 'mcq'
        grading_agents = list(config.get('grading_agents') or [])
        learning_pipeline = list(config.get('learning_pipeline') or [])
        pipeline_learning_ids = set(learning_pipeline)

        trace: list[dict] = []
        started = time.perf_counter()
        backend = backend_name()

        total_budget = _total_budget_sec()
        for agent_id in grading_agents:
            if time.perf_counter() - started > total_budget:
                break
            mapped_learning = _GRADING_TO_LEARNING.get(agent_id)
            if mapped_learning and mapped_learning in pipeline_learning_ids:
                continue
            if agent_id == 'sandbox-runtime' and qtype != 'coding':
                continue
            if agent_id == 'answer-correctness' and qtype == 'coding':
                continue
            item = GradingOrchestrator._run_grading_agent(
                agent_id,
                user_id=user_id,
                question=question,
                progress=progress,
                grade_result=grade_result,
                backend=backend,
            )
            if item:
                trace.append(item)

        if learning_pipeline and time.perf_counter() - started <= total_budget:
            trace.extend(
                GradingOrchestrator._run_learning_pipeline(
                    learning_pipeline,
                    user_id=user_id,
                    question=question,
                    progress=progress,
                    grade_result=grade_result,
                    backend=backend,
                )
            )

        return trace

    @staticmethod
    def _trace_item(
        agent_id: str,
        name: str,
        summary: str,
        *,
        status: str = 'success',
        latency_ms: float = 0,
        backend: str | None = None,
        role: str | None = None,
    ) -> dict:
        row = {
            'agentId': agent_id,
            'name': name,
            'status': status,
            'latencyMs': round(latency_ms, 1),
            'summary': summary,
        }
        if role:
            row['role'] = role
        if backend:
            row['backend'] = backend
        return row

    @staticmethod
    def _run_grading_agent(
        agent_id: str,
        *,
        user_id: int,
        question: TrialQuestion,
        progress: TrialQuestionProgress,
        grade_result: dict,
        backend: str,
    ) -> dict | None:
        meta = GRADING_AGENT_MAP.get(agent_id)
        if not meta:
            return None
        started = time.perf_counter()
        try:
            if agent_id == 'answer-correctness':
                is_correct = bool(grade_result.get('correct'))
                summary = '作答正确，与参考答案一致' if is_correct else '作答错误，与参考答案不一致'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    summary,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend='local_rules',
                    role=meta.get('role'),
                )

            if agent_id == 'sandbox-runtime':
                passed = bool(grade_result.get('code_passed'))
                passed_count = grade_result.get('passed_count', 0)
                total = grade_result.get('total', 0)
                summary = f'沙箱验证通过 {passed_count}/{total} 用例' if passed else f'沙箱验证未通过 {passed_count}/{total} 用例'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    summary,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=grade_result.get('execution_backend') or 'local_rules',
                    role=meta.get('role'),
                )

            if agent_id == 'plagiarism-guard':
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    '相似度 0% · 演示模式：未接入查重库',
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend='demo_stub',
                    role=meta.get('role'),
                )

            if agent_id == 'rubric-alignment':
                passed = bool(grade_result.get('correct') or grade_result.get('code_passed'))
                score = 100 if passed else 60
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    f'按默认量表评分 {score}/100（演示：未配置教师量表）',
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend='demo_stub',
                    role=meta.get('role'),
                )

            payload = GradingOrchestrator._build_agent_payload(
                user_id, question, progress, grade_result
            )

            if agent_id == 'code-syntax':
                result = code_analysis_agent.execute(payload)
                summary = result.get('codeIssueSummary') or '已完成语法与代码结构审查'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    summary,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=backend,
                    role=meta.get('role'),
                )

            if agent_id == 'logic-step':
                result = learning_diagnosis_agent.execute(payload)
                summary = result.get('diagnosis') or '已完成解题逻辑链审查'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    str(summary)[:160],
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=backend,
                    role=meta.get('role'),
                )

            if agent_id == 'knowledge-coverage':
                diagnosis = learning_diagnosis_agent.execute(payload)
                graph_payload = {
                    'currentKnowledgePoints': payload.get('knowledgePoints') or [],
                    'weakPoints': diagnosis.get('weakPoints') or [],
                    'errorType': diagnosis.get('errorType'),
                    'relatedKnowledgePoints': diagnosis.get('relatedKnowledgePoints') or [],
                }
                result = knowledge_graph_agent.execute(graph_payload)
                nodes = result.get('relatedNodes') or []
                summary = f"覆盖检查：关联节点 {'、'.join(nodes[:3])}" if nodes else '已核对知识点覆盖情况'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    summary,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=backend,
                    role=meta.get('role'),
                )

            if agent_id == 'feedback-coach':
                diagnosis = learning_diagnosis_agent.execute(payload)
                feedback_payload = {
                    'diagnosis': diagnosis,
                    'codeAnalysis': code_analysis_agent.execute({**payload, 'diagnosis': diagnosis}),
                }
                result = feedback_agent.execute(feedback_payload)
                summary = result.get('shortFeedback') or result.get('encouragement') or '已生成个性化反馈'
                return GradingOrchestrator._trace_item(
                    agent_id,
                    meta['name'],
                    str(summary)[:160],
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=backend,
                    role=meta.get('role'),
                )

        except Exception as exc:
            return GradingOrchestrator._trace_item(
                agent_id,
                meta['name'],
                f'执行失败：{exc}',
                status='error',
                latency_ms=(time.perf_counter() - started) * 1000,
                backend=backend,
                role=meta.get('role'),
            )
        return None

    @staticmethod
    def _run_learning_pipeline(
        enabled_ids: list[str],
        *,
        user_id: int,
        question: TrialQuestion,
        progress: TrialQuestionProgress,
        grade_result: dict,
        backend: str,
    ) -> list[dict]:
        enabled_set = set(enabled_ids)
        payload = GradingOrchestrator._build_agent_payload(
            user_id, question, progress, grade_result
        )
        started = time.perf_counter()
        try:
            if time.perf_counter() - started > _agent_budget_sec():
                return []
            pipeline = run_student_diagnose(payload)
            rows = pipeline.get('pipelineTrace') or []
            filtered = [row for row in rows if row.get('agentId') in enabled_set]
            for row in filtered:
                row['backend'] = pipeline.get('backend') or backend
                if pipeline.get('llmEnhanced') and row.get('source') == 'crewai_llm':
                    row['source'] = 'crewai_llm'
            return filtered
        except Exception as exc:
            name = LEARNING_AGENT_MAP.get(enabled_ids[0], {}).get('name', '学习流水线')
            return [
                GradingOrchestrator._trace_item(
                    enabled_ids[0],
                    name,
                    f'流水线执行失败：{exc}',
                    status='error',
                    latency_ms=(time.perf_counter() - started) * 1000,
                    backend=backend,
                )
            ]

    @staticmethod
    def _build_agent_payload(
        user_id: int,
        question: TrialQuestion,
        progress: TrialQuestionProgress,
        grade_result: dict,
    ) -> dict[str, Any]:
        qtype = question.question_type or 'mcq'
        knowledge_label = QuestionGenerator.label_for_key(question.knowledge_key)
        knowledge_points = [knowledge_label] if knowledge_label else []
        if question.knowledge_key:
            knowledge_points.append(question.knowledge_key)

        payload: dict[str, Any] = {
            'user_id': user_id,
            'question_id': question.id,
            'topic': knowledge_label or question.stem[:40],
            'knowledgePoints': knowledge_points,
            'knowledgeKeys': [question.knowledge_key] if question.knowledge_key else [],
            'stem': question.stem,
        }

        if qtype == 'coding':
            code = progress.submitted_code or ''
            results = progress.code_results() or grade_result.get('results') or []
            stderr = ''
            stdout = ''
            for item in results:
                if not item.get('passed'):
                    stderr = item.get('stderr') or item.get('error') or stderr
                    stdout = item.get('stdout') or stdout
            payload.update(
                {
                    'code': code,
                    'stderr': stderr,
                    'stdout': stdout,
                    'errorMessage': stderr,
                    'passed': bool(grade_result.get('code_passed')),
                }
            )
        else:
            selected = progress.selected_index
            options = question.to_dict()['options']
            selected_text = options[selected] if isinstance(selected, int) and 0 <= selected < len(options) else ''
            payload.update(
                {
                    'selectedIndex': selected,
                    'selectedText': selected_text,
                    'isCorrect': bool(grade_result.get('correct')),
                    'correctIndex': question.correct_index,
                }
            )
        return payload
