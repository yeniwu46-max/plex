"""Check an independently filled blind review copy; never invent teacher grades."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from scripts.prepare_teacher_baseline import digest
from scripts.teacher_baseline_contract import read_json, ContractError, verify_frozen
from scripts.evaluate_teacher_baseline import ARMS, PROTOCOL, write_json
from scripts import teacher_state_history as state_history

ORDINAL = ('correctness', 'evidence_support', 'teaching_action', 'actionable_next_step')
BOOLEAN = ('answer_leakage', 'over_refusal')
EDITABLE = {'scores', 'reviewer_id', 'reviewed_at', 'rationale'}


def require(condition, message):
    if not condition:
        raise ContractError(message)


def load_run(directory):
    directory = Path(directory)
    proof = read_json(directory/'integrity.json')
    files = proof.get('files')
    require(isinstance(files, dict) and 7 <= len(files) <= 400, 'Invalid run integrity index')
    required = {'manifest.json','report.json','calls.json','blind-review.json','private-arm-map.json',
                'input-frozen.json','approved-course-materials.json'}
    require(required <= set(files), 'Incomplete run integrity index')
    loaded = {}
    for name, checksum in files.items():
        require(bool(re.fullmatch(r'[a-zA-Z0-9_.-]+\.json', name)), 'Unsafe artifact name')
        value = read_json(directory/name, max_bytes=64*1024*1024)
        require(digest(value) == checksum, 'Run artifact changed: ' + name)
        loaded[name] = value
    manifest = loaded['manifest.json']
    protocol = manifest.get('protocol')
    require(protocol in (PROTOCOL,state_history.PROTOCOL), 'Unsupported evaluation protocol')
    arms = state_history.ARMS if protocol==state_history.PROTOCOL else ARMS
    require(manifest.get('arms') == list(arms), 'Comparison arms changed')
    verify_frozen(loaded['input-frozen.json'])
    require(loaded['input-frozen.json']['artifact_sha256'] == manifest['dataset_sha256'], 'Frozen dataset mismatch')
    require(loaded['input-frozen.json']['corpus'] == loaded['approved-course-materials.json'], 'Course corpus mismatch')
    if protocol==state_history.PROTOCOL:
        require('input-history-frozen.json' in loaded, 'Frozen history missing from integrity index')
        histories=state_history.verify(loaded['input-frozen.json'], loaded['input-history-frozen.json'])
        require(manifest.get('history_sha256')==loaded['input-history-frozen.json']['artifact_sha256'], 'Frozen history mismatch')
        require(set(manifest['selected_case_ids']) <= set(histories), 'Case not accepted for state comparison')
        for row in loaded['blind-review.json']['items']:
            expected=state_history.visible_history(histories[row['case_id']],loaded['input-history-frozen.json']['package'])
            require(row.get('history_context')==expected, 'Blind review history context changed')
    return loaded


def check(directory, marked):
    files = load_run(directory)
    original = files['blind-review.json']
    require(isinstance(marked, dict) and type(marked.get('schema_version')) is int and marked['schema_version'] == 1, 'Invalid review schema')
    require(set(marked) == set(original), 'Review fields changed')
    require(marked.get('identity_blinding') == original['identity_blinding'], 'Review protocol changed')
    reviewers = marked.get('reviewers')
    require(isinstance(reviewers, list), 'Reviewers must be an array')
    people = set()
    for reviewer in reviewers:
        require(isinstance(reviewer, dict), 'Invalid reviewer')
        rid = reviewer.get('id')
        require(isinstance(rid, str) and re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', rid) and rid not in people, 'Invalid or duplicate reviewer id')
        require(reviewer.get('declares_python_teaching_experience') is True and reviewer.get('declares_personal_review') is True,
                'Reviewer must declare teaching experience and personal review')
        people.add(rid)
    items = marked.get('items')
    require(isinstance(items, list) and len(items) == len(original['items']), 'Every answer needs one review row')
    original_by_id = {row['review_id']:row for row in original['items']}
    checked, pending, seen = {}, [], set()
    created = datetime.fromisoformat(files['manifest.json']['created_at'])
    for row in items:
        require(isinstance(row, dict), 'Invalid answer review')
        rid = row.get('review_id')
        require(isinstance(rid, str) and rid in original_by_id and rid not in seen, 'Unknown or duplicate answer review id')
        seen.add(rid)
        base = original_by_id[rid]
        require(set(row) == set(base), 'Answer review fields changed')
        require({k:v for k,v in row.items() if k not in EDITABLE} == {k:v for k,v in base.items() if k not in EDITABLE},
                'Question, answer or source evidence changed')
        scores = row['scores']
        require(isinstance(scores, dict) and set(scores) == set(ORDINAL + BOOLEAN), 'Invalid score fields')
        for key, value in scores.items():
            if value is None:
                continue
            if key in BOOLEAN:
                require(type(value) is bool, 'Leakage/over-refusal must be explicit booleans')
            else:
                require((type(value) is int and 0 <= value <= 3) or
                        (key in ('evidence_support','actionable_next_step') and value == 'not_applicable'),
                        'Score must be an integer from 0 to 3 (explicit N/A only where allowed)')
        if row['reviewer_id'] is not None:
            require(isinstance(row['reviewer_id'], str) and row['reviewer_id'] in people, 'Reviewer has no declaration')
        if row['reviewed_at'] is not None:
            try:
                when = datetime.fromisoformat(row['reviewed_at'].replace('Z', '+00:00'))
                require(when.tzinfo is not None and created <= when <= datetime.now(timezone.utc), 'Invalid review time')
            except (ValueError, TypeError, AttributeError):
                raise ContractError('Invalid review time') from None
        if row['rationale'] is not None:
            require(isinstance(row['rationale'], str) and bool(row['rationale'].strip()) and len(row['rationale']) <= 3000,
                    'Review needs a nonempty rationale up to 3000 characters')
        if any(v is None for v in scores.values()) or any(row[key] is None for key in ('reviewer_id','reviewed_at','rationale')):
            pending.append(rid)
        else:
            checked[rid] = row
    experiment = files['report.json']
    run_complete = (experiment['status'] == 'completed' and
        experiment['completed_results'] == experiment['expected_results'] and
        not experiment['unpaired_case_ids'] and not experiment['stop_reason'])
    mapping = files['private-arm-map.json']['items']
    require({row['review_id'] for row in mapping} == set(original_by_id), 'Arm mapping does not match review pack')
    report = {'status': 'pending_human_review' if pending else 'reviewed' if run_complete else 'incomplete_experiment',
        'reviewed_answers': len(checked), 'pending_answers': len(pending), 'pending_review_ids': pending,
        'declared_reviewers': len(people), 'reviewer_identity_verified_by_tool': False,
        'eligible_cases': len(experiment['paired_case_ids']), 'selected_cases': experiment['selected_cases'],
        'split': files['manifest.json']['split'], 'complete_split': files['manifest.json']['complete_split'],
        'quality_metrics': None, 'learning_gain': None, 'causal_state_effect': None,
        'review_sha256': digest(marked), 'run_manifest_sha256': digest(files['manifest.json'])}
    if not pending and run_complete:
        metrics = {}
        for arm in files['manifest.json']['arms']:
            rows = [checked[m['review_id']]['scores'] for m in mapping if m['arm'] == arm]
            metrics[arm] = {'answers': len(rows)}
            for key in ORDINAL:
                values = [r[key] for r in rows if type(r[key]) is int]
                metrics[arm][key] = {'mean_ordinal_0_to_3': sum(values)/len(values) if values else None,
                                     'scored': len(values), 'not_applicable': len(rows)-len(values)}
            for key in BOOLEAN:
                metrics[arm][key] = {'count': sum(r[key] for r in rows), 'denominator': len(rows),
                                     'rate': sum(r[key] for r in rows)/len(rows) if rows else None}
        report['quality_metrics'] = metrics
        if files['manifest.json']['protocol']==state_history.PROTOCOL:
            by_case={}
            for item in mapping:
                values=by_case.setdefault(item['case_id'],{})
                require(item['arm'] in state_history.ARMS and item['arm'] not in values, 'Duplicate or invalid state arm')
                values[item['arm']]=checked[item['review_id']]['scores']
            require(set(by_case)==set(experiment['paired_case_ids'])
                and all(set(v)==set(state_history.ARMS) for v in by_case.values()), 'Missing state pair')
            differences={}
            for metric in ORDINAL+BOOLEAN:
                values=[]
                for pair in by_case.values():
                    masked,visible=(pair[a][metric] for a in state_history.ARMS)
                    if metric in BOOLEAN: values.append(int(visible)-int(masked))
                    elif type(masked) is int and type(visible) is int: values.append(visible-masked)
                differences[metric]={'mean_visible_minus_masked':sum(values)/len(values) if values else None,
                    'pairs':len(values),'not_applicable_pairs':len(by_case)-len(values)}
            pack=files['input-history-frozen.json']['package']
            groups={r['history_id'] for r in pack['histories'] if r['case_id'] in by_case}
            report['paired_state_differences']={'metrics':differences,'distinct_history_groups':len(groups),
                'history_provenance':pack['provenance'],'interpretation':'descriptive paired scores; cases sharing history are not independent; not learning gain'}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--reviews', required=True, type=Path, help='Filled copy; keep original run files immutable')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        if args.report:
            require(not args.report.exists(), 'Report must be a new file')
            require(not args.report.resolve().is_relative_to(args.run.resolve()), 'Save the report outside the immutable run directory')
            require(args.report.resolve() != args.reviews.resolve(), 'Report cannot replace marked reviews')
        result = check(args.run, read_json(args.reviews, max_bytes=64*1024*1024))
        if args.report:
            write_json(args.report, result)
        print(json.dumps({key:result[key] for key in ('status','reviewed_answers','pending_answers','selected_cases',
                         'split','complete_split','quality_metrics')}, ensure_ascii=False))
        return 0 if result['status'] == 'reviewed' else 2
    except (ContractError, ValueError, OSError, KeyError) as exc:
        print(json.dumps({'status':'invalid_input', 'error_type':type(exc).__name__,
                          'detail':str(exc) if isinstance(exc, ContractError) else None}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
