"""Evaluate local seven-dimension profile extraction against a fixed label set."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.student_profile import PROFILE_DIMENSIONS, StudentProfileService


DEFAULT_CASES = ROOT / 'data' / 'evaluation' / 'profile_extraction_cases.json'


def evaluate(cases_path: Path = DEFAULT_CASES) -> dict:
    cases = json.loads(cases_path.read_text(encoding='utf-8'))
    totals = defaultdict(int)
    rows = []
    for case in cases:
        extracted = StudentProfileService._rule_extract(case['message'])
        actual = set(extracted)
        expected = set(case['expected_dimensions'])
        value_checks = {}
        for dimension, fragment in case.get('value_contains', {}).items():
            value = str((extracted.get(dimension) or {}).get('value') or '')
            value_checks[dimension] = fragment in value

        for dimension in PROFILE_DIMENSIONS:
            is_expected = dimension in expected
            is_actual = dimension in actual
            if is_expected and is_actual:
                totals['tp'] += 1
            elif is_expected:
                totals['fn'] += 1
            elif is_actual:
                totals['fp'] += 1
            else:
                totals['tn'] += 1
        rows.append({
            'id': case['id'],
            'category': case['category'],
            'expected_dimensions': sorted(expected),
            'actual_dimensions': sorted(actual),
            'missing_dimensions': sorted(expected - actual),
            'unexpected_dimensions': sorted(actual - expected),
            'value_checks': value_checks,
            'exact_match': expected == actual and all(value_checks.values()),
        })

    tp, tn, fp, fn = (totals[key] for key in ('tp', 'tn', 'fp', 'fn'))
    total = tp + tn + fp + fn
    recall = tp / (tp + fn) if tp + fn else 1
    specificity = tn / (tn + fp) if tn + fp else 1
    value_checks = [
        passed
        for row in rows
        for passed in row['value_checks'].values()
    ]
    return {
        'backend': 'local_rules',
        'case_count': len(cases),
        'dimension_count': len(PROFILE_DIMENSIONS),
        'confusion': dict(totals),
        'summary': {
            'field_presence_accuracy': round((tp + tn) / total, 4),
            'positive_recall': round(recall, 4),
            'negative_specificity': round(specificity, 4),
            'balanced_field_accuracy': round((recall + specificity) / 2, 4),
            'exact_case_match_rate': round(
                sum(row['exact_match'] for row in rows) / len(rows), 4
            ),
            'value_check_pass_rate': round(
                sum(value_checks) / len(value_checks), 4
            ) if value_checks else 1,
        },
        'cases': rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports' / 'profile-extraction-local.json',
    )
    args = parser.parse_args()
    report = evaluate(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0 if report['summary']['balanced_field_accuracy'] >= 0.85 else 1


if __name__ == '__main__':
    raise SystemExit(main())
