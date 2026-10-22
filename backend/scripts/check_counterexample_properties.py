"""Actual Docker checks for three declared properties and two bad materials."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flask import Flask
from app.config import DevelopmentConfig
from app.services.counterexample_contract import specification, digest
from app.services.counterexample_validation import validate
from app.services.counterexample_properties import POLICY, build_plan
from scripts.check_counterexample_sandbox import fixtures


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'output/plex-p3-properties-live.json')
    args=parser.parse_args()
    app=Flask('counterexample-property-acceptance');app.config.from_object(DevelopmentConfig)
    app.config['CODE_EXECUTION_BACKEND']='docker'
    records=[]
    examples=[]
    properties=[['permutation_invariant','append_zero_invariant','concatenation_additive'],
                ['permutation_invariant','result_is_member'], ['duplicate_invariant','permutation_invariant']]
    for index,(spec,proposal) in enumerate(fixtures()):
        spec.pop('contract_version')
        spec['verification']={'policy_version':POLICY,'boundary_checks':True,'properties':properties[index],
            'rationale':'开发验收的人工编写性质，不计入真实教师审阅题库。'}
        examples.append((specification(spec),proposal,None))
    spec,proposal,_=deepcopy(examples[0])
    proposal['fixed_code']='def solve(data):\n    return sum(data) if len(data)<3 else 0'
    examples.append((spec,proposal,'fixed_reference_mismatch'))
    spec,proposal,_=deepcopy(examples[0])
    spec.pop('contract_version');spec['verification']['properties']=['permutation_invariant']
    spec['tests']=[{'input':[],'expected':0},{'input':[1],'expected':1},{'input':[2,2],'expected':2}]
    spec['reference_code']='def solve(data):\n    return data[0] if data else 0'
    proposal['fixed_code']=spec['reference_code']
    examples.append((specification(spec),proposal,'reference_property_mismatch'))
    with app.app_context():
        for spec,proposal,expected_reason in examples:
            report=validate(spec,proposal)
            plan=build_plan(spec['input_contract'],spec['tests'],spec['verification'])
            records.append({'specification':spec,'candidate':proposal,'plan':plan,'report':report,'expected_reason':expected_reason})
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_bytes(json.dumps({'synthetic_fixtures':True,'human_teacher_review':False,'records':records},ensure_ascii=False,indent=2).encode('utf-8'))
            assert report['reason']==expected_reason and report['passed']==(expected_reason is None), report
            assert report['coverage']['plan_hash']==plan['hash']
            assert report['artifact_hashes']['verification']==digest(spec['verification'])
            print(json.dumps({'kind':proposal['bug_kind'],'expected_rejection':expected_reason,'passed':report['passed'],
                'inputs':report['coverage']['total_inputs'],'property_checks':sum(item['checked'] for item in report['coverage']['properties']),
                'batches':report['execution_batches'],'elapsed_ms':report['elapsed_ms']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
