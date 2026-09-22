"""Deterministic dispatch-contract benchmark for the four trial-coach agents.

This is intentionally separate from a natural-language classifier benchmark: the
current product receives an explicit intent from the trial UI, so this measures
whether every supported intent is routed to the matching agent and preserves the
no-direct-answer policy without network calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Initialise the application package first; this avoids the legacy agents/app
# import cycle when the script is launched directly from the repository root.
from app import create_app  # noqa: F401

for _key in ('OPENROUTER_API_KEY', 'DEEPSEEK_API_KEY', 'IFLYTEK_SPARK_API_PASSWORD', 'SPARK_API_PASSWORD'):
    os.environ.pop(_key, None)

from agents.trial_coach_agents import (
    INTENT_CUSTOM,
    INTENT_ERROR,
    INTENT_OPTIMIZE,
    INTENT_QUALITY,
    VALID_INTENTS,
    execute,
    infer_intent,
)
import agents.trial_coach_agents as _coach

# Keep the benchmark deterministic even when a developer machine has provider
# credentials configured; network-backed generation is measured separately.
_coach.api_key_configured = lambda: False
_coach.llm_provider = lambda: None
_coach.IflytekSparkService = None


CASES = [
    (INTENT_ERROR, {'stderr': 'NameError: name x is not defined', 'answerStatus': 'wrong'}),
    (INTENT_QUALITY, {'code': 'for x in xs: print(x)', 'answerStatus': 'correct'}),
    (INTENT_OPTIMIZE, {'code': 'items = items + [x]', 'answerStatus': 'partial'}),
    (INTENT_CUSTOM, {'question': '请提示我如何拆解这道题', 'answerStatus': 'not_run'}),
] * 25

NATURAL_LANGUAGE_CASES = [
    (INTENT_ERROR, '为什么运行时报错 NameError？'),
    (INTENT_QUALITY, '请帮我检查代码的可读性和命名规范'),
    (INTENT_OPTIMIZE, '这段代码如何优化时间复杂度？'),
    (INTENT_CUSTOM, '我应该先从哪里开始思考？'),
] * 25


def main() -> None:
    passed = 0
    failures: list[dict] = []
    for intent, payload in CASES:
        try:
            result = execute(intent, payload)
            ok = (
                result.get('intent') == intent
                and result.get('agentId')
                and result.get('policy') == 'no_direct_answer'
            )
        except Exception as exc:  # pragma: no cover - report only
            ok = False
            result = {'error': str(exc)}
        if ok:
            passed += 1
        else:
            failures.append({'intent': intent, 'result': result})

    total = len(CASES)
    report = {
        'benchmark': 'trial-coach-intent-dispatch-contract',
        'cases': total,
        'passed': passed,
        'accuracy': round(passed / total, 4) if total else 0,
        'supported_intents': sorted(VALID_INTENTS),
        'network_required': False,
        'failures': failures,
    }
    natural_passed = sum(infer_intent({'userQuestion': text}) == intent for intent, text in NATURAL_LANGUAGE_CASES)
    report['natural_language_cases'] = len(NATURAL_LANGUAGE_CASES)
    report['natural_language_accuracy'] = round(natural_passed / len(NATURAL_LANGUAGE_CASES), 4)
    output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-intent-dispatch-20260828.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
