"""Verify all frozen drafts in Docker and write review evidence, never publish."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flask import Flask
from app.config import DevelopmentConfig
from app.services.counterexample_contract import digest
from app.services.counterexample_validation import validate
from app.services.counterexample_validation import VALIDATOR_VERSION
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now

CATALOG=ROOT/'app/data/counterexample_catalog_v1.json'
SUMMARY=ROOT/'app/data/counterexample_catalog_v1_validation.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'output/plex-p3-catalog-validation.json')
    parser.add_argument('--resume',action='store_true',help='Retain matching passed records after an interrupted development run.')
    args=parser.parse_args()
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    assert digest({k:v for k,v in catalog.items() if k!='catalog_hash'})==catalog['catalog_hash']
    app=Flask('counterexample-catalog-validation');app.config.from_object(DevelopmentConfig)
    app.config['CODE_EXECUTION_BACKEND']='docker'
    full={'catalog_hash':catalog['catalog_hash'],'human_review_status':'pending','items':[]}
    compact={'catalog_hash':catalog['catalog_hash'],'human_review_status':'pending','items':[]}
    prior={}
    if args.resume:
        saved=json.loads(args.output.read_text(encoding='utf-8'))
        if saved.get('catalog_hash')!=catalog['catalog_hash'] or saved.get('human_review_status')!='pending':
            raise SystemExit('Cannot resume a different catalog version.')
        known={item['id']:item['content_hash'] for item in catalog['items']}
        for record in saved['items']:
            if record['id'] in prior or record['content_hash']!=known.get(record['id']) or record['report']['validator_version']!=VALIDATOR_VERSION:
                raise SystemExit('Cannot resume mismatched or duplicate records.')
            prior[record['id']]=record
    with app.app_context():
        for item in catalog['items']:
            assert digest({k:v for k,v in item.items() if k!='content_hash'})==item['content_hash']
            old=prior.get(item['id'])
            if old and old['report']['passed'] is True:
                report=old['report'];when=old['verified_at']
            else:
                try:
                    report=validate(item['specification'],item['candidate'])
                except ExecutionUnavailable as exc:
                    print(json.dumps({'id':item['id'],'status':'environment_unavailable','reason':exc.reason,'resume_supported':True}),flush=True)
                    raise SystemExit(2) from None
                when=utc_now().isoformat()+'Z'
            full['items'].append({'id':item['id'],'content_hash':item['content_hash'],'verified_at':when,'report':report})
            compact['items'].append({'id':item['id'],'content_hash':item['content_hash'],'verified_at':when,
                'passed':report['passed'],'reason':report['reason'],'validator_version':report['validator_version'],
                'report_hash':digest(report),'runtimes':report['runtimes'],'scope':report['scope'],
                'coverage':report.get('coverage'),'witness_count':report.get('witness_count',0),'elapsed_ms':report['elapsed_ms']})
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_bytes(json.dumps(full,ensure_ascii=False,indent=2).encode('utf-8'))
            SUMMARY.write_bytes(json.dumps(compact,ensure_ascii=False,indent=2).encode('utf-8'))
            print(json.dumps({'id':item['id'],'passed':report['passed'],'reason':report['reason'],
                'inputs':report.get('coverage',{}).get('total_inputs'),'elapsed_ms':report['elapsed_ms'],
                'retained':bool(old and old['report']['passed'] is True)},ensure_ascii=False),flush=True)
    failed=[item['id'] for item in compact['items'] if not item['passed']]
    print(json.dumps({'total':len(compact['items']),'failed':failed,'human_review_status':'pending'}),flush=True)
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
