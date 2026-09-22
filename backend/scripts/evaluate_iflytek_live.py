"""Run a real Spark Pro smoke/benchmark when credentials are available.

The script never substitutes local rules for the live result.  Without a
credential it writes ``status=not_configured`` so the submission evidence cannot
mistakenly claim a real-model measurement.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make the script reproducible both as ``python scripts/...`` and as a module;
# otherwise a different installed package named ``app`` can win import order.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.config  # noqa: F401 — load .env and .env.spark.local
from app import create_app
from app.services.iflytek_spark import IflytekSparkService, SparkServiceError


SYSTEM = (
    '你是智慧教育学习助手。只输出JSON对象，字段为 response（不超过80字）、'
    'grounded（布尔值）、knowledge_key（字符串）。不要编造课程知识库之外的事实。'
)
PROMPT = '请用一句话解释 Python 列表索引的边界条件，并给出一个检查建议。'


def run(cases: int) -> dict:
    report = {
        'benchmark': 'iflytek-spark-live-grounding',
        'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'invocation': 'python scripts/evaluate_iflytek_live.py',
        'requested_cases': cases,
        'status': 'not_configured',
        'credential_configured': False,
        'model': None,
        'success_count': 0,
        'parse_pass_count': 0,
        'grounded_pass_count': 0,
        'latency_ms': [],
        'errors': [],
        'note': '未检测到讯飞凭证，未使用本地规则冒充真实调用。',
    }
    if not IflytekSparkService.configured():
        return report

    report['credential_configured'] = True
    report['status'] = 'running'
    for _ in range(max(1, cases)):
        started = time.monotonic()
        try:
            # Use the generic Spark credential so the benchmark matches the
            # Spark Pro APIPassword supplied for the submission, rather than
            # silently selecting a legacy trial/coach credential.
            result = IflytekSparkService.chat_json(SYSTEM, PROMPT, timeout=20)
            report['success_count'] += 1
            report['latency_ms'].append(round((time.monotonic() - started) * 1000))
            if isinstance(result.get('response'), str) and result.get('response').strip():
                report['parse_pass_count'] += 1
            if result.get('grounded') is True:
                report['grounded_pass_count'] += 1
            report['model'] = IflytekSparkService.status().get('model')
        except (SparkServiceError, Exception) as exc:  # report one failed call, keep the run auditable
            report['errors'].append(type(exc).__name__ + ':' + str(exc))
    report['status'] = 'completed' if report['success_count'] else 'failed'
    latencies = report['latency_ms']
    report['latency_summary'] = {
        'p50_ms': round(statistics.median(latencies), 1) if latencies else None,
        'p95_ms': round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1) if latencies else None,
        'target_p95_ms': 1500,
        'target_passed': bool(latencies) and sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] <= 1500,
    }
    report['grounded_rate'] = round(report['grounded_pass_count'] / report['success_count'], 4) if report['success_count'] else None
    report['parse_rate'] = round(report['parse_pass_count'] / report['success_count'], 4) if report['success_count'] else None
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=int, default=100)
    args = parser.parse_args()
    # create_app initializes config/imports consistently with the test suite.
    create_app('testing')
    report = run(args.cases)
    output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-live-20260828.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
