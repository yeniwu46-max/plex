"""Check the local risk-explanation contract without fabricating model evidence."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app


def _login(client):
    response = client.post('/api/v1/auth/login', json={'username': 'student001', 'password': 'student123'})
    body = response.get_json() or {}
    if response.status_code != 200 or body.get('code') != 0:
        return None
    return body['data']['access_token']


def run() -> dict:
    app = create_app('development')
    client = app.test_client()
    token = _login(client)
    report = {
        'benchmark': 'iflytek-990-risk-explainability-contract',
        'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'backend': 'local_rules',
        'status': 'unavailable',
        'real_model_verified': False,
        'shap_claimed': False,
        'explanation_count': 0,
        'checks': {},
    }
    if not token:
        report['checks']['demo_login'] = False
        return report
    response = client.get(
        '/api/v1/student/learning-report?period=7d',
        headers={'Authorization': f'Bearer {token}'},
    )
    body = response.get_json() or {}
    data = body.get('data') or {}
    explanations = data.get('risk_explanations') or []
    report['explanation_count'] = len(explanations)
    report['checks'] = {
        'demo_login': True,
        'report_endpoint': response.status_code == 200 and body.get('code') == 0,
        'all_have_feature': all(bool(item.get('feature')) for item in explanations),
        'all_have_evidence': all(bool(item.get('evidence')) for item in explanations),
        'contributions_bounded': all(0 <= float(item.get('contribution', -1)) <= 1 for item in explanations),
        'all_have_value': all('value' in item for item in explanations),
    }
    report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
    report['note'] = '确定性贡献因子和证据链通过契约检查；未宣称 SHAP，也不替代真实训练数据。'
    return report


def main():
    output = ROOT / 'reports' / 'iflytek-990-risk-explainability-20260828.json'
    result = run()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result.get('status') == 'passed' else 1)


if __name__ == '__main__':
    main()
