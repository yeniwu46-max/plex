"""Validate or freeze a teacher-reviewed baseline; pending labels never become scores."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.teacher_baseline_contract import ContractError, read_json, validate, freeze, verify_frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=ROOT/'output/plex-teacher-baseline-v1')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--freeze', type=Path, help='Write a new immutable artifact only after all review gates pass')
    action.add_argument('--verify', type=Path, help='Check a previously frozen artifact without changing it')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        protected = {(args.pack/name).resolve() for name in ('cases.json','corpus.json','reviews.json')}
        protected.update(p.resolve() for p in (args.freeze,args.verify) if p)
        if args.report and args.report.resolve() in protected:
            raise ContractError('Report path cannot overwrite input data or a frozen artifact')
        if args.verify:
            report = verify_frozen(read_json(args.verify))
        else:
            cases, corpus, reviews = [read_json(args.pack/name) for name in ('cases.json','corpus.json','reviews.json')]
            report = validate(cases, corpus, reviews)
            if args.freeze:
                report['frozen'] = freeze(cases, corpus, reviews, args.freeze)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ('pending_case_ids','accepted_case_ids')},
                         ensure_ascii=False, indent=2))
        return 0 if report['ready_to_freeze'] else 2
    except (ContractError, OSError, ValueError, KeyError) as exc:
        # Do not dump corpus, prompts, or filled teacher response points on failures.
        print(json.dumps({'schema_valid':False,'ready_to_freeze':False,'error':str(exc)},ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
