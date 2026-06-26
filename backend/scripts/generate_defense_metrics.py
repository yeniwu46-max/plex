"""Build presentation-ready metrics from authoritative validation reports."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load(relative_path: str) -> dict:
    path = BACKEND_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metric(group: str, name: str, value: float | int, unit: str) -> dict:
    return {"group": group, "metric": name, "value": value, "unit": unit}


def generate(output_dir: Path) -> dict:
    personalization = _load(
        "reports/a3-personalization-local/personalization-evaluation.json"
    )
    extraction = _load(
        "reports/a3-personalization-local/profile-extraction-evaluation.json"
    )
    knowledge = _load(
        "reports/a3-personalization-local/knowledge-base-validation.json"
    )
    feedback = _load(
        "reports/a3-personalization-local/feedback-loop-three-rounds.json"
    )
    effect = _load("reports/a3-next-stage/learning-effect.json")
    security = _load("reports/a3-next-stage/security-validation.json")
    performance = _load("reports/a3-next-stage/performance-recovery.json")
    deprecations = _load("reports/a3-submission/deprecation-budget.json")
    bundle = json.loads(
        (BACKEND_ROOT.parent / "frontend/reports/bundle-budget.json").read_text(
            encoding="utf-8-sig"
        )
    )

    personalization_summary = personalization["summary"]
    extraction_summary = extraction["summary"]
    performance_metrics = performance["metrics"]
    effect_result = effect["result"]
    security_summary = security["summary"]

    metrics = [
        _metric(
            "personalization",
            "task_success_rate",
            personalization_summary["task_success_rate"] * 100,
            "percent",
        ),
        _metric(
            "personalization",
            "schema_pass_rate",
            personalization_summary["schema_pass_rate"] * 100,
            "percent",
        ),
        _metric(
            "personalization",
            "citation_valid_rate",
            personalization_summary["citation_valid_rate"] * 100,
            "percent",
        ),
        _metric(
            "profile",
            "balanced_field_accuracy",
            extraction_summary["balanced_field_accuracy"] * 100,
            "percent",
        ),
        _metric(
            "knowledge_base",
            "coverage_rate",
            knowledge["coverage_rate"] * 100,
            "percent",
        ),
        _metric(
            "feedback_loop",
            "rounds_passed",
            feedback["summary"]["rounds_passed"],
            "rounds",
        ),
        _metric(
            "learning_effect",
            "correct_rate_delta",
            effect_result["delta"]["correct_rate"],
            "percentage_points",
        ),
        _metric(
            "learning_effect",
            "mistake_count_delta",
            effect_result["delta"]["mistake_count"],
            "records",
        ),
        _metric(
            "security",
            "validation_pass_rate",
            security_summary["passed"] / security_summary["total"] * 100,
            "percent",
        ),
        _metric(
            "performance",
            "success_rate",
            performance_metrics["success_rate"],
            "percent",
        ),
        _metric(
            "performance",
            "idempotency_rate",
            performance_metrics["idempotency_rate"],
            "percent",
        ),
        _metric(
            "performance",
            "p95_latency",
            performance_metrics["p95_ms"],
            "ms",
        ),
        _metric(
            "engineering",
            "project_deprecated_calls",
            sum(item["count"] for item in deprecations["checks"].values()),
            "calls",
        ),
        _metric(
            "frontend",
            "initial_gzip",
            round(bundle["checks"]["initial_gzip"]["actual_bytes"] / 1024, 2),
            "KiB",
        ),
        _metric(
            "frontend",
            "largest_lazy_gzip",
            round(
                bundle["checks"]["largest_lazy_gzip"]["actual_bytes"] / 1024,
                2,
            ),
            "KiB",
        ),
    ]

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": True,
        "evidence_scope": "local_rules_and_local_environment",
        "external_not_claimed": [
            "iflytek_spark",
            "github_ci",
            "mysql_8",
            "tts",
        ],
        "metrics": metrics,
        "chart_series": {
            "quality_rates": [
                {"name": item["metric"], "value": item["value"]}
                for item in metrics
                if item["unit"] == "percent"
                and item["group"] != "performance"
            ],
            "performance": [
                {
                    "name": item["metric"],
                    "value": item["value"],
                    "unit": item["unit"],
                }
                for item in metrics
                if item["group"] == "performance"
            ],
            "learning_effect": {
                "before_correct_rate": effect_result["before"]["correct_rate"],
                "after_correct_rate": effect_result["after"]["correct_rate"],
                "before_mistakes": effect_result["before"]["mistake_count"],
                "after_mistakes": effect_result["after"]["mistake_count"],
                "evidence_count": effect_result["evidence_count"],
            },
            "frontend_bundle": [
                {
                    "name": item["metric"],
                    "value": item["value"],
                    "unit": item["unit"],
                }
                for item in metrics
                if item["group"] == "frontend"
            ],
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "defense-metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "defense-metrics.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("group", "metric", "value", "unit")
        )
        writer.writeheader()
        writer.writerows(metrics)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BACKEND_ROOT / "reports/a3-submission",
    )
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir), ensure_ascii=False, indent=2))
