"""Machine-check the multi-agent orchestration evidence contract."""
from __future__ import annotations

import json
from pathlib import Path

from app.data.agent_registry import LEARNING_PIPELINE_AGENTS, GRADING_AGENTS
from agents.crew import get_agents_health, get_agents_status, run_student_diagnose
import agents.llm_client as _llm_client

_llm_client.api_key_configured = lambda: False


def main():
    registered = get_agents_status()
    payload = {
        'questionTitle': '循环练习', 'questionPrompt': '输出 0 到 2',
        'code': 'i=0\nwhile i<3: print(i)', 'stderr': '',
        'stdout': '0\n1\n2', 'expectedOutput': '0\n1\n2',
        'answerStatus': 'correct', 'knowledgePoints': ['循环'],
    }
    result = run_student_diagnose(payload, fast=True)
    steps = result.get('pipelineTrace') or []
    step_contract = all(
        isinstance(step, dict)
        and step.get('agentId')
        and step.get('status')
        and step.get('latencyMs') is not None
        for step in steps
    ) if steps else False
    report = {
        'benchmark': 'multi-agent-orchestration-contract',
        'learning_registered_count': len(LEARNING_PIPELINE_AGENTS),
        'grading_registered_count': len(GRADING_AGENTS),
        'professional_agent_requirement_passed': len(LEARNING_PIPELINE_AGENTS) >= 6,
        'registered_agent_status_count': len(registered),
        'trace_step_count': len(steps),
        'trace_contract_passed': step_contract,
        'runtime_health': get_agents_health(),
        'backend': result.get('backend'),
        'degraded_mode_explicit': result.get('backend') in {'mock', 'rules', 'crewai'},
        'note': '该报告验证编排契约和本地降级链；真实模型后端仍需凭证专项测评。',
    }
    report['status'] = 'passed' if report['professional_agent_requirement_passed'] and report['trace_contract_passed'] else 'failed'
    output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-agent-orchestration-20260828.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
