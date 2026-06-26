"""Audit local competition evidence and external submission blockers."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.generate_release_manifest import verify_manifest
except ModuleNotFoundError:
    from generate_release_manifest import verify_manifest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

EVIDENCE_REPORTS = {
    "personalization": "backend/reports/a3-personalization-local/personalization-evaluation.json",
    "profile_extraction": "backend/reports/a3-personalization-local/profile-extraction-evaluation.json",
    "knowledge_base": "backend/reports/a3-personalization-local/knowledge-base-validation.json",
    "feedback_loop": "backend/reports/a3-personalization-local/feedback-loop-three-rounds.json",
    "learning_effect": "backend/reports/a3-next-stage/learning-effect.json",
    "security": "backend/reports/a3-next-stage/security-validation.json",
    "performance_recovery": "backend/reports/a3-next-stage/performance-recovery.json",
    "clean_environment": "backend/reports/a3-next-stage/clean-environment.json",
    "dependency_inventory": "backend/reports/a3-submission/dependency-inventory.json",
    "deprecation_budget": "backend/reports/a3-submission/deprecation-budget.json",
    "release_manifest": "backend/reports/a3-submission/release-manifest.json",
    "defense_metrics": "backend/reports/a3-submission/defense-metrics.json",
    "frontend_bundle": "frontend/reports/bundle-budget.json",
}

REQUIRED_DOCUMENTS = {
    "requirements": "docs/submission/01-requirements.md",
    "system_design": "docs/submission/02-system-design.md",
    "multi_agent_design": "docs/submission/03-multi-agent-design.md",
    "knowledge_and_evaluation": "docs/submission/04-knowledge-and-evaluation.md",
    "testing": "docs/submission/05-testing.md",
    "deployment": "docs/submission/06-deployment.md",
    "user_manual": "docs/submission/07-user-manual.md",
    "open_source_and_ai": "docs/submission/08-open-source-and-ai-tools.md",
    "innovation": "docs/submission/09-innovation-and-value.md",
    "demo_script": "docs/submission/10-demo-script.md",
    "external_acceptance": "docs/submission/11-external-acceptance-checklist.md",
    "defense_deck_spec": "docs/submission/12-defense-deck-spec.md",
    "recording_runbook": "docs/submission/13-recording-runbook.md",
    "freeze_file_groups": "docs/submission/14-freeze-file-groups.md",
}


def _load_json(relative_path: str) -> tuple[dict | None, str | None]:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid_json:{type(exc).__name__}"


def _report_passed(name: str, report: dict) -> bool:
    if "passed" in report:
        return report["passed"] is True
    if name == "personalization":
        summary = report.get("summary", {})
        return (
            summary.get("task_success_rate", 0) >= 0.95
            and summary.get("schema_pass_rate", 0) == 1.0
            and summary.get("citation_valid_rate", 0) == 1.0
            and summary.get("counterfactual_pass_rate", 0) == 1.0
        )
    if name == "profile_extraction":
        summary = report.get("summary", report)
        return (
            summary.get("balanced_field_accuracy", 0) >= 0.85
            and summary.get("value_check_pass_rate", 0) == 1.0
        )
    if name == "knowledge_base":
        return (
            report.get("status") == "passed"
            and report.get("coverage_rate") == 1.0
            and not report.get("errors")
        )
    if name == "feedback_loop":
        summary = report.get("summary", {})
        return (
            summary.get("rounds_passed") == report.get("round_count")
            and summary.get("all_profile_versions_incremented") is True
            and summary.get("all_rejections_preserved_profile") is True
            and summary.get("all_recommendations_changed") is True
            and summary.get("all_paths_changed") is True
            and summary.get("all_tasks_persisted") is True
            and summary.get("all_reviews_visible") is True
        )
    return False


def audit(output: Path) -> dict:
    evidence = {}
    for name, relative_path in EVIDENCE_REPORTS.items():
        report, error = _load_json(relative_path)
        evidence[name] = {
            "path": relative_path,
            "present": report is not None,
            "passed": bool(report and _report_passed(name, report)),
            "error": error,
        }

    documents = {}
    for name, relative_path in REQUIRED_DOCUMENTS.items():
        path = REPO_ROOT / relative_path
        size = path.stat().st_size if path.is_file() else 0
        documents[name] = {
            "path": relative_path,
            "present": path.is_file(),
            "non_empty": size >= 200,
            "bytes": size,
        }

    clean_report, _ = _load_json(EVIDENCE_REPORTS["clean_environment"])
    external_conditions = (clean_report or {}).get("external_conditions", {})
    external_gates = {
        "iflytek_spark": external_conditions.get("iflytek_spark") == "credential_configured",
        "github_ci": external_conditions.get("github_cli") == "authenticated",
        "mysql_8": (
            (REPO_ROOT / "backend/reports/a3-next-stage/mysql-clean-environment.json").is_file()
        ),
    }
    manifest_report, _ = _load_json(EVIDENCE_REPORTS["release_manifest"])
    manifest_verification = (
        verify_manifest(manifest_report) if manifest_report else {"passed": False}
    )
    try:
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        current_commit = None
    release_metadata = (manifest_report or {}).get("release", {})
    freeze_gates = {
        "manifest_matches_worktree": manifest_verification.get("passed") is True,
        "manifest_commit_matches_head": bool(
            current_commit
            and release_metadata.get("git_commit") == current_commit
        ),
        "worktree_clean_at_manifest": release_metadata.get("worktree_dirty") is False,
    }
    deliverable_paths = {
        "defense_pptx": REPO_ROOT / "docs/submission/artifacts/PLEX-A3-defense.pptx",
        "demo_video": REPO_ROOT / "docs/submission/artifacts/PLEX-A3-demo.mp4",
    }
    delivery_gates = {
        name: path.is_file() and path.stat().st_size > 10_000
        for name, path in deliverable_paths.items()
    }
    local_passed = (
        all(item["passed"] for item in evidence.values())
        and all(item["present"] and item["non_empty"] for item in documents.values())
        and (REPO_ROOT / "start.bat").is_file()
        and (REPO_ROOT / ".github/workflows/ci.yml").is_file()
    )
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "local_passed": local_passed,
        "submission_ready": (
            local_passed
            and all(external_gates.values())
            and all(freeze_gates.values())
            and all(delivery_gates.values())
        ),
        "evidence": evidence,
        "documents": documents,
        "entrypoints": {
            "start_script": (REPO_ROOT / "start.bat").is_file(),
            "ci_workflow": (REPO_ROOT / ".github/workflows/ci.yml").is_file(),
            "environment_template": (BACKEND_ROOT / ".env.example").is_file(),
        },
        "external_gates": external_gates,
        "freeze_gates": freeze_gates,
        "delivery_gates": delivery_gates,
        "deliverables": {
            name: path.relative_to(REPO_ROOT).as_posix()
            for name, path in deliverable_paths.items()
        },
        "manifest_verification": manifest_verification,
        "blocked": [
            name
            for name, passed in {
                **external_gates,
                **freeze_gates,
                **delivery_gates,
            }.items()
            if not passed
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "reports/a3-submission/release-readiness.json",
    )
    parser.add_argument(
        "--require-external",
        action="store_true",
        help="Return failure until Spark, online CI, and MySQL 8 evidence are present.",
    )
    args = parser.parse_args()
    result = audit(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    gate = result["submission_ready"] if args.require_external else result["local_passed"]
    raise SystemExit(0 if gate else 1)
