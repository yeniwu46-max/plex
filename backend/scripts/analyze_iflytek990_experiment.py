"""Analyze real PLEX teaching-experiment events without inventing missing data."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import re
from collections import defaultdict
from pathlib import Path

REQUIRED_COLUMNS = {
    'participant_id', 'stage', 'event_type', 'knowledge_key', 'question_id',
    'is_correct', 'study_minutes', 'recommendation_shown',
    'recommendation_accepted', 'due_reviews', 'completed_reviews',
    'teacher_review_minutes', 'ticket_status', 'timestamp',
}
VALID_STAGES = {'pre', 'intervention', 'post'}
PII_LIKE = re.compile(r'(?:1[3-9]\d{9}|\b\d{15,18}[0-9Xx]?\b|@)')


def _num(row, key):
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def analyze(path: Path) -> dict:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        rows = list(reader)
    schema_errors = sorted(REQUIRED_COLUMNS - columns)
    validation = {
        'missing_columns': schema_errors,
        'invalid_stage_rows': [],
        'missing_required_rows': [],
        'pii_like_participant_ids': [],
        'duplicate_event_keys': [],
    }
    seen_event_keys = set()
    for index, row in enumerate(rows, start=2):
        participant = (row.get('participant_id') or '').strip()
        stage = (row.get('stage') or '').strip().lower()
        if stage not in VALID_STAGES:
            validation['invalid_stage_rows'].append(index)
        if not participant or not stage or not (row.get('timestamp') or '').strip():
            validation['missing_required_rows'].append(index)
        if participant and PII_LIKE.search(participant):
            validation['pii_like_participant_ids'].append(index)
        event_key = tuple((row.get(key) or '').strip() for key in ('participant_id', 'event_type', 'question_id', 'stage', 'timestamp'))
        if event_key in seen_event_keys:
            validation['duplicate_event_keys'].append(index)
        seen_event_keys.add(event_key)
    participants = sorted({row.get('participant_id', '').strip() for row in rows if row.get('participant_id', '').strip()})
    by_person = defaultdict(lambda: {'pre': [], 'post': []})
    for row in rows:
        stage = row.get('stage', '').strip().lower()
        if stage in ('pre', 'post') and row.get('participant_id', '').strip() and row.get('is_correct', '').strip() != '':
            by_person[row['participant_id'].strip()][stage].append(_num(row, 'is_correct'))
    paired = []
    for participant, stages in by_person.items():
        if stages['pre'] and stages['post']:
            pre = sum(stages['pre']) / len(stages['pre'])
            post = sum(stages['post']) / len(stages['post'])
            paired.append({'participant_id': participant, 'pre_accuracy': round(pre, 4), 'post_accuracy': round(post, 4), 'delta': round(post - pre, 4)})
    shown = sum(_num(row, 'recommendation_shown') for row in rows)
    accepted = sum(_num(row, 'recommendation_accepted') for row in rows)
    due = sum(_num(row, 'due_reviews') for row in rows)
    completed = sum(_num(row, 'completed_reviews') for row in rows)
    workload = [_num(row, 'teacher_review_minutes') for row in rows if row.get('teacher_review_minutes', '').strip()]
    result = {
        'status': 'ready' if len(participants) >= 100 else 'insufficient_real_data',
        'source': str(path),
        'event_rows': len(rows),
        'participant_count': len(participants),
        'paired_pre_post_count': len(paired),
        'paired_accuracy': paired,
        'metrics': {
            'pre_accuracy_mean': round(statistics.mean(item['pre_accuracy'] for item in paired), 4) if paired else None,
            'post_accuracy_mean': round(statistics.mean(item['post_accuracy'] for item in paired), 4) if paired else None,
            'delta_mean': round(statistics.mean(item['delta'] for item in paired), 4) if paired else None,
            'delta_stddev': round(statistics.stdev(item['delta'] for item in paired), 4) if len(paired) > 1 else None,
            'delta_median': round(statistics.median(item['delta'] for item in paired), 4) if paired else None,
            'recommendation_acceptance_rate': round(accepted / shown, 4) if shown else None,
            'sm2_review_completion_rate': round(completed / due, 4) if due else None,
            'teacher_review_minutes_mean': round(statistics.mean(workload), 2) if workload else None,
        },
        'stage_counts': {
            stage: sum(1 for row in rows if (row.get('stage') or '').strip().lower() == stage)
            for stage in sorted(VALID_STAGES)
        },
        'validation': validation,
        'validation_passed': not any(validation.values()),
        'evidence_policy': 'no synthetic data; insufficient samples remain explicitly incomplete',
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = analyze(Path(args.input))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
