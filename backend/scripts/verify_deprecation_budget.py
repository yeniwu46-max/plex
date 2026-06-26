"""Track project-owned deprecated API usage separately from dependency noise."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (BACKEND_ROOT / "app", BACKEND_ROOT / "agents")
PATTERNS = {
    "sqlalchemy_query_get": re.compile(r"\.query\.get\("),
    "datetime_utcnow": re.compile(r"datetime\.utcnow\(\)"),
}
DEFAULT_BUDGET = {
    "sqlalchemy_query_get": 0,
    "datetime_utcnow": 0,
}


def _scan() -> dict[str, list[dict]]:
    findings = {name: [] for name in PATTERNS}
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8-sig")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for name, pattern in PATTERNS.items():
                    if pattern.search(line):
                        findings[name].append({
                            "path": path.relative_to(BACKEND_ROOT).as_posix(),
                            "line": line_number,
                        })
    return findings


def run(output: Path, budget: dict[str, int] | None = None) -> dict:
    budget = budget or DEFAULT_BUDGET
    findings = _scan()
    counts = {name: len(items) for name, items in findings.items()}
    checks = {
        name: {
            "count": counts[name],
            "budget": limit,
            "passed": counts[name] <= limit,
        }
        for name, limit in budget.items()
    }
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": all(item["passed"] for item in checks.values()),
        "checks": checks,
        "findings": findings,
        "dependency_noise": {
            "werkzeug_ast_deprecations": (
                "third-party warnings from the pinned Werkzeug 2.3 routing compiler; "
                "tracked separately from project-owned calls"
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "reports/a3-submission/deprecation-budget.json",
    )
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
