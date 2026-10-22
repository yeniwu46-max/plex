"""Actual isolated execution acceptance; synthetic fixtures, no database writes."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flask import Flask
from app.config import DevelopmentConfig
from app.services.counterexample_contract import specification, candidate
from app.services.counterexample_validation import validate


def fixtures():
    common = {'concept_id':'loop-for',
        'input_contract':{'type':'integer_array','minimum':-10,'maximum':10,'min_items':0,'max_items':10},
        'output_contract':{'type':'integer','minimum':-100,'maximum':100},
        'reference_note':'开发验收的人工编写基准，不是教师审阅题库。'}
    cases = [
        ('loop_boundary', '数组求和', '所有整数求和，空数组返回 0。',
         'def solve(data):\n    return sum(data)', 'def solve(data):\n    return sum(data[:-1])',
         [([],0),([1],1),([1,2],3),([-1,3],2)], []),
        ('empty_input', '最大值', '返回最大元素，空数组约定返回 0。',
         'def solve(data):\n    return max(data) if data else 0', 'def solve(data):\n    return max(data)',
         [([],0),([-1],-1),([3,3],3),([-3,0],0)], ['ValueError']),
        ('duplicate_elements', '不同数值之和', '每个不同整数只计一次，空数组返回 0。',
         'def solve(data):\n    return sum(set(data))', 'def solve(data):\n    return sum(data)',
         [([],0),([2,2],2),([1,2],3),([-1,-1,3],2)], []),
    ]
    for kind, title, statement, fixed, wrong, tests, exceptions in cases:
        yield specification({**common, 'title':title, 'statement':statement, 'reference_code':fixed,
            'tests':[{'input':i,'expected':e} for i,e in tests], 'allowed_bug_exceptions':exceptions}), candidate({
                'bug_kind':kind,'buggy_code':wrong,'fixed_code':fixed,'explanation':'开发验收边界错误候选。'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent/'output/plex-p3-sandbox-acceptance.json')
    args = parser.parse_args()
    app = Flask('counterexample-sandbox-acceptance')
    app.config.from_object(DevelopmentConfig)
    app.config['CODE_EXECUTION_BACKEND'] = 'docker'
    report = []
    with app.app_context():
        for spec, proposal in fixtures():
            result = validate(spec, proposal)
            report.append({'kind':proposal['bug_kind'],**result})
            print(json.dumps({'kind':proposal['bug_kind'],'passed':result['passed'],
                'reason':result['reason'],'witnesses':len(result['witnesses']),
                'runtimes':result['runtimes'],'elapsed_ms':result['elapsed_ms']},ensure_ascii=False),flush=True)
            if not result['passed']:
                args.output.write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'))
                raise SystemExit('Counterexample sandbox acceptance failed')
        spec, proposal = next(fixtures())
        proposal['buggy_code'] = 'def solve(data):\n    while True:\n        pass'
        result = validate(spec,proposal)
        report.append({'kind':'timeout-rejected',**result})
        assert not result['passed'] and result['reason']=='execution_timeout', result
        print('Infinite candidate rejected: execution_timeout',flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'))


if __name__ == '__main__':
    main()
