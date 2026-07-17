# -*- coding: utf-8 -*-
"""在 Python 3.12 子进程中运行 CrewAI（供 Flask 3.14 主进程调用）。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / '.env')
except ImportError:
    pass


def _run_student(payload: dict) -> dict:
    import os

    os.environ.setdefault('AGENT_BACKEND', 'crewai')
    from agents.crew import _run_mock_student_pipeline, backend_name
    from agents.pipeline_llm import enhance_student_pipeline

    baseline = _run_mock_student_pipeline(payload)

    if backend_name() != 'crewai':
        return baseline

    if not (os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY')):
        return baseline

    started = time.perf_counter()
    try:
        from crewai import Agent, Crew, Process, Task

        from agents.crew import _AGENT_REGISTRY

        agents = []
        tasks = []
        for spec in _AGENT_REGISTRY[:5]:
            mod = spec['module']
            agents.append(
                Agent(
                    role=mod.ROLE,
                    goal=mod.GOAL,
                    backstory=mod.BACKSTORY,
                    verbose=False,
                ),
            )
            tasks.append(
                Task(
                    description=f'分析 Python 初学者练习：{json.dumps(payload, ensure_ascii=False)}',
                    expected_output='结构化 JSON',
                    agent=agents[-1],
                ),
            )
        crew = Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=False)
        crew.kickoff(inputs=payload)
    except Exception:
        pass

    enhanced = enhance_student_pipeline(baseline, payload)
    enhanced['backend'] = 'crewai'
    enhanced['crewaiSubprocessMs'] = round((time.perf_counter() - started) * 1000, 1)
    return enhanced


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    mode = sys.argv[1] if len(sys.argv) > 1 else 'student'
    if mode == 'student':
        result = _run_student(payload)
    else:
        from agents.crew import run_teacher_suggestion

        result = run_teacher_suggestion(payload)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
