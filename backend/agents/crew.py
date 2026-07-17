# -*- coding: utf-8 -*-
"""PLEX 多智能体编排：顺序流水线 + CrewAI 可选接入。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from app.utils.time import utc_now

from . import (
    code_analysis_agent,
    feedback_agent,
    knowledge_graph_agent,
    learning_diagnosis_agent,
    learning_path_agent,
    path_recommendation_agent,
    teacher_assistant_agent,
)

_AGENT_REGISTRY = [
    {
        'id': 'learning_diagnosis',
        'name': '学习诊断智能体',
        'role': learning_diagnosis_agent.ROLE,
        'module': learning_diagnosis_agent,
    },
    {
        'id': 'code_analysis',
        'name': '代码分析智能体',
        'role': code_analysis_agent.ROLE,
        'module': code_analysis_agent,
    },
    {
        'id': 'knowledge_graph',
        'name': '知识图谱智能体',
        'role': knowledge_graph_agent.ROLE,
        'module': knowledge_graph_agent,
    },
    {
        'id': 'learning_path',
        'name': '学习路径智能体',
        'role': learning_path_agent.ROLE,
        'module': learning_path_agent,
    },
    {
        'id': 'path_recommendation',
        'name': '路径推荐智能体',
        'role': path_recommendation_agent.ROLE,
        'module': path_recommendation_agent,
    },
    {
        'id': 'feedback',
        'name': '反馈生成智能体',
        'role': feedback_agent.ROLE,
        'module': feedback_agent,
    },
    {
        'id': 'teacher_assistant',
        'name': '教师助理智能体',
        'role': teacher_assistant_agent.ROLE,
        'module': teacher_assistant_agent,
    },
]

_STATUS: dict[str, dict[str, Any]] = {
    item['id']: {
        'id': item['id'],
        'name': item['name'],
        'role': item['role'],
        'status': 'idle',
        'lastRunAt': None,
        'avgLatency': None,
        '_runs': 0,
        '_total_ms': 0.0,
    }
    for item in _AGENT_REGISTRY
}


def _now() -> str:
    return utc_now().isoformat() + 'Z'


def _crewai_venv_python() -> Path | None:
    backend_root = Path(__file__).resolve().parents[1]
    candidate = backend_root / '.venv-crewai' / 'Scripts' / 'python.exe'
    return candidate if candidate.is_file() else None


def _crewai_subprocess_ok() -> bool:
    py = _crewai_venv_python()
    if not py:
        return False
    try:
        proc = subprocess.run(
            [str(py), '-c', 'import crewai; print(crewai.__version__)'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(py.parent.parent.parent),
        )
        return proc.returncode == 0
    except Exception:
        return False


def _inject_crewai_venv() -> None:
    """同进程 import 仅在同版本 Python 下有效（如整后端跑在 3.12 venv）。"""
    backend_root = Path(__file__).resolve().parents[1]
    venv_site = backend_root / '.venv-crewai' / 'Lib' / 'site-packages'
    if venv_site.is_dir():
        site = str(venv_site)
        if site not in sys.path:
            sys.path.insert(0, site)


def _crewai_available() -> bool:
    _inject_crewai_venv()
    try:
        import crewai  # noqa: F401
        return True
    except ImportError:
        return _crewai_subprocess_ok()


def backend_name() -> str:
    backend = os.getenv('AGENT_BACKEND', 'auto').lower()
    if backend in ('crewai', 'auto'):
        if _crewai_available():
            return 'crewai'
        if backend == 'crewai':
            return 'mock'
    if backend == 'auto':
        return 'mock'
    return backend


def _track(
    agent_id: str,
    fn: Callable[[], dict],
    trace: list[dict] | None = None,
    summarize: Callable[[dict], str] | None = None,
) -> dict:
    entry = _STATUS[agent_id]
    entry['status'] = 'running'
    started = time.perf_counter()
    try:
        result = fn()
        elapsed_ms = (time.perf_counter() - started) * 1000
        entry['status'] = 'success'
        entry['lastRunAt'] = _now()
        entry['_runs'] += 1
        entry['_total_ms'] += elapsed_ms
        entry['avgLatency'] = round(entry['_total_ms'] / entry['_runs'], 1)
        if trace is not None:
            summary = ''
            if summarize:
                try:
                    summary = summarize(result)
                except Exception:
                    summary = ''
            trace.append({
                'agentId': agent_id,
                'name': entry['name'],
                'role': entry['role'],
                'status': 'success',
                'latencyMs': round(elapsed_ms, 1),
                'summary': summary,
            })
        return result
    except Exception:
        entry['status'] = 'error'
        entry['lastRunAt'] = _now()
        if trace is not None:
            trace.append({
                'agentId': agent_id,
                'name': entry['name'],
                'role': entry['role'],
                'status': 'error',
                'latencyMs': round((time.perf_counter() - started) * 1000, 1),
                'summary': '执行出错',
            })
        raise


def get_agents_status() -> list[dict]:
    rows = []
    for item in _AGENT_REGISTRY:
        entry = _STATUS[item['id']]
        rows.append({
            'id': entry['id'],
            'name': entry['name'],
            'role': entry['role'],
            'status': entry['status'],
            'lastRunAt': entry['lastRunAt'],
            'avgLatency': entry['avgLatency'],
        })
    return rows


def get_agents_health() -> dict:
    """内存态运行健康摘要，供管理端指标使用。"""
    agents = get_agents_status()
    latencies = [a['avgLatency'] for a in agents if a.get('avgLatency') is not None]
    errors = sum(1 for a in agents if a.get('status') == 'error')
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
    success_rate = round((len(agents) - errors) / max(len(agents), 1) * 100, 1)
    return {
        'avg_latency_ms': avg_latency,
        'success_rate': success_rate,
        'error_count': errors,
        'registered_count': len(agents),
    }


def crewai_venv_available() -> bool:
    return _crewai_subprocess_ok()


def _run_mock_student_pipeline(payload: dict) -> dict:
    trace: list[dict] = []

    diagnosis = _track(
        'learning_diagnosis',
        lambda: learning_diagnosis_agent.execute(payload),
        trace=trace,
        summarize=lambda r: '识别为{} · {} · 置信度 {}%'.format(
            r.get('errorLayerLabel', r.get('errorType', '')),
            r.get('proficiencyLabel', ''),
            round(float(r.get('confidence', 0)) * 100),
        ),
    )

    code_payload = {
        'code': payload.get('code', ''),
        'stdin': payload.get('stdin'),
        'stdout': payload.get('stdout'),
        'stderr': payload.get('stderr'),
        'expectedOutput': payload.get('expectedOutput'),
        'errorMessage': payload.get('errorMessage') or payload.get('stderr'),
        'diagnosis': diagnosis,
    }
    code_analysis = _track(
        'code_analysis',
        lambda: code_analysis_agent.execute(code_payload),
        trace=trace,
        summarize=lambda r: r.get('codeIssueSummary', '已生成代码问题解释'),
    )

    graph_payload = {
        'currentKnowledgePoints': payload.get('knowledgePoints') or [],
        'weakPoints': diagnosis['weakPoints'],
        'errorType': diagnosis['errorType'],
        'relatedKnowledgePoints': diagnosis.get('relatedKnowledgePoints') or [],
        'codeAnalysis': code_analysis,
    }
    graph_insight = _track(
        'knowledge_graph',
        lambda: knowledge_graph_agent.execute(graph_payload),
        trace=trace,
        summarize=lambda r: '定位相关节点：{}'.format('、'.join(r.get('relatedNodes', [])[:3])),
    )

    path_payload = {
        'weakPoints': diagnosis['weakPoints'],
        'prerequisiteNodes': graph_insight['prerequisiteNodes'],
        'graphInsight': graph_insight,
        'currentStage': payload.get('currentStage', 1),
        'completedExercises': payload.get('completedExercises') or [],
        'user_id': payload.get('user_id'),
        'diagnosis': diagnosis,
    }
    recommendation = _track(
        'learning_path',
        lambda: learning_path_agent.execute(path_payload),
        trace=trace,
        summarize=lambda r: '下一步：{}'.format(r.get('nextKnowledgePoint', '')),
    )

    feedback_payload = {
        'diagnosis': diagnosis,
        'codeAnalysis': code_analysis,
        'recommendation': recommendation,
    }
    feedback = _track(
        'feedback',
        lambda: feedback_agent.execute(feedback_payload),
        trace=trace,
        summarize=lambda r: '生成{}策略反馈'.format(r.get('strategyType', '')),
    )

    return {
        'diagnosis': diagnosis,
        'codeAnalysis': code_analysis,
        'graphInsight': graph_insight,
        'recommendation': recommendation,
        'feedback': feedback,
        'pipelineTrace': trace,
        'backend': backend_name(),
        'completedAt': _now(),
    }


def _run_crewai_subprocess(mode: str, payload: dict) -> dict | None:
    py = _crewai_venv_python()
    if not py:
        return None
    script = Path(__file__).resolve().parent / 'crewai_subprocess.py'
    try:
        proc = subprocess.run(
            [str(py), str(script), mode],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(py.parent.parent.parent),
            env=os.environ.copy(),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)
    except Exception:
        return None


def _try_crewai_student_pipeline(payload: dict) -> dict | None:
    if backend_name() != 'crewai':
        return None
    result = _run_crewai_subprocess('student', payload)
    if result:
        return result
    if _crewai_subprocess_ok():
        return None
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY')):
        return None
    try:
        from crewai import Agent, Crew, Process, Task  # type: ignore

        agents = []
        tasks = []
        for spec in _AGENT_REGISTRY[:6]:
            mod = spec['module']
            agent = Agent(
                role=mod.ROLE,
                goal=mod.GOAL,
                backstory=mod.BACKSTORY,
                verbose=False,
            )
            task = Task(
                description=f'处理 Python 初学者练习上下文：{payload}',
                expected_output='结构化 JSON 字段',
                agent=agent,
            )
            agents.append(agent)
            tasks.append(task)

        crew = Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=False)
        crew.kickoff(inputs=payload)
    except Exception:
        return None
    return _run_mock_student_pipeline(payload)


def run_student_diagnose(payload: dict) -> dict:
    try:
        crew_result = _try_crewai_student_pipeline(payload)
        if crew_result is not None:
            return crew_result
    except Exception:
        pass
    baseline = _run_mock_student_pipeline(payload)
    try:
        from agents.llm_client import api_key_configured
        from agents.pipeline_llm import enhance_student_pipeline

        if api_key_configured():
            enhanced = enhance_student_pipeline(baseline, payload)
            if enhanced.get('llmEnhanced'):
                return enhanced
    except Exception:
        pass
    return baseline


def run_learning_path_plan(payload: dict) -> dict:
    def _run():
        return learning_path_agent.execute(payload)

    result = _track('learning_path', _run)
    return {
        **result,
        'backend': backend_name(),
        'completedAt': _now(),
    }


def run_teacher_suggestion(payload: dict) -> dict:
    def _run():
        return teacher_assistant_agent.execute(payload)

    result = _track('teacher_assistant', _run)
    return {**result, 'backend': backend_name(), 'generatedAt': _now()}
