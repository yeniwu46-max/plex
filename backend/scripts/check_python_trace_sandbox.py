"""Real trace acceptance, Docker only, fixed synthetic examples, no DB writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flask import Flask
from app.config import DevelopmentConfig
from app.services.python_trace import PythonTraceService, POLICY
from app.services.execution_errors import ExecutionUnavailable


def cases():
    # Expected observations are handwritten; none are evaluated on the host.
    return [
        ('line_timing', 'x = 1\nx += 2\nprint(x)', '', 'completed', '3\n', {'x':'3'}),
        ('loop_boundary', 'total = 0\nfor n in range(3):\n    total += n\nprint(total)', '', 'completed', '3\n', {'total':'3'}),
        ('empty_list', 'items = []\nsize = len(items)\nprint(size)', '', 'completed', '0\n', {'size':'0'}),
        ('stdin', 'n = int(input("n? "))\nprint(n + 1)', '4\n', 'completed', 'n? 5\n', {'n':'4'}),
        ('dict_preview', 'data = {"a": 1}\nvalue = data["a"]\nprint(value)', '', 'completed', '1\n', {'value':'1'}),
        ('fullwidth', 'x＝2\nprint（x）', '', 'completed', '2\n', {'x':'2'}),
        ('cycle', 'x = [None]\nx[0] = x\nprint(len(x))', '', 'completed', '1\n', {'x':'[<cycle>]'}),
        ('runtime_error', 'x = 1\nprint(x / 0)', '', 'runtime_error', '', {'x':'1'}),
        ('step_limit', 'x = 0\nwhile True:\n    x += 1', '', 'step_limit', '', {}),
        ('output_limit', 'print("a" * 5000)', '', 'output_limit', 'a' * 4096, {}),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite an acceptance report')
    report = {'policy':POLICY, 'at':datetime.now(timezone.utc).isoformat(),
        'kind':'synthetic_docker_acceptance', 'verified':False, 'cases':[],
        'implementation_hashes':{name:hashlib.sha256((ROOT/'app/services'/name).read_bytes()).hexdigest()
            for name in ['python_trace.py','python_trace_runtime.txt','docker_execution.py']}}
    code = 2
    try:
        # Read-only availability check. Never start, reset or change Docker here.
        check = subprocess.run(['docker','version','--format','{{json .Server}}'],
            capture_output=True, timeout=12)
        if check.returncode != 0 or not isinstance(json.loads(check.stdout), dict):
            raise ExecutionUnavailable('docker_engine_unavailable')
        app = Flask(__name__); app.config.from_object(DevelopmentConfig)
        # Isolated test process only: does not enable the live application.
        app.config.update(CODE_EXECUTION_BACKEND='docker', CODE_TRACE_ENABLED=True)
        with app.app_context():
            for name, source, stdin, outcome, stdout, expected_values in cases():
                result = PythonTraceService.run(source, stdin)
                trace = result.get('trace') or {}
                valid = (trace.get('outcome') == outcome and trace.get('stdout') == stdout
                    and all(trace.get('final_variables', {}).get('values', {}).get(k) == v for k,v in expected_values.items())
                    and result.get('graded') is False)
                if name == 'line_timing':
                    valid = valid and trace.get('steps') == [
                        {'line':1,'variables':{'values':{},'omitted':0}},
                        {'line':2,'variables':{'values':{'x':'1'},'omitted':0}},
                        {'line':3,'variables':{'values':{'x':'3'},'omitted':0}}]
                if name == 'step_limit': valid = valid and len(trace.get('steps', [])) == 80
                if name == 'fullwidth': valid = valid and trace.get('code_normalized') is True
                if name == 'runtime_error': valid = valid and trace.get('error_type') == 'ZeroDivisionError'
                report['cases'].append({'case':name,'passed':valid,'trace':trace})
                print(json.dumps({'case':name,'passed':valid}, ensure_ascii=False), flush=True)
                if not valid:
                    report['reason'] = 'unexpected_trace'; code = 1; break
            else:
                report['verified'] = True; code = 0
    except (OSError, subprocess.TimeoutExpired, ValueError, ExecutionUnavailable):
        report['reason'] = 'isolated_execution_unavailable'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
    print(json.dumps({'verified':report['verified'],'completed_cases':len(report['cases']),
                      'reason':report.get('reason')}, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
