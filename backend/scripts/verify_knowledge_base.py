"""Validate the canonical 16-point Python course knowledge base."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.course_knowledge import validate_course_knowledge


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args()

    report = validate_course_knowledge()
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    print(
        f"knowledge base: {report['status']} "
        f"({report['valid_knowledge_point_count']}/"
        f"{report['knowledge_point_count']}, "
        f"coverage={report['coverage_rate']:.0%})"
    )
    for error in report['errors']:
        print(f'ERROR: {error}', file=sys.stderr)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
