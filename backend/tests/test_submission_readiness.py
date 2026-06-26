from pathlib import Path

from scripts.generate_dependency_inventory import generate
from scripts.generate_defense_metrics import generate as generate_defense_metrics
from scripts.generate_release_manifest import generate as generate_manifest
from scripts.generate_release_manifest import verify_manifest
from scripts.verify_deprecation_budget import run as verify_deprecation_budget
from scripts.verify_release_readiness import audit


def test_dependency_inventory_resolves_direct_dependencies(tmp_path: Path):
    report = generate(tmp_path / "dependency-inventory.json")

    assert report["passed"] is True
    assert report["summary"]["missing_licenses"] == 0
    assert report["summary"]["unresolved_versions"] == 0
    assert report["summary"]["python_runtime"] >= 10
    assert report["summary"]["node_runtime"] >= 20


def test_release_readiness_separates_local_and_external_gates(tmp_path: Path):
    report = audit(tmp_path / "release-readiness.json")

    assert report["local_passed"] is True
    assert report["submission_ready"] is (
        report["local_passed"]
        and all(report["external_gates"].values())
        and all(report["freeze_gates"].values())
        and all(report["delivery_gates"].values())
    )
    assert set(report["blocked"]) == {
        name
        for name, passed in {
            **report["external_gates"],
            **report["freeze_gates"],
            **report["delivery_gates"],
        }.items()
        if not passed
    }


def test_deprecation_budget_prevents_regression(tmp_path: Path):
    report = verify_deprecation_budget(tmp_path / "deprecation-budget.json")

    assert report["passed"] is True
    assert report["checks"]["sqlalchemy_query_get"]["count"] == 0
    assert report["checks"]["datetime_utcnow"]["count"] == 0


def test_release_manifest_excludes_local_environments(tmp_path: Path):
    report = generate_manifest(tmp_path / "release-manifest.json")
    paths = [item["path"] for item in report["files"]]

    assert report["passed"] is True
    assert report["summary"]["oversized_count"] == 0
    assert not any(
        part.startswith(".venv")
        for path in paths
        for part in path.split("/")
    )
    assert not any("node_modules" in path.split("/") for path in paths)
    assert not any(path.endswith((".db", ".sqlite", ".sqlite3")) for path in paths)
    assert verify_manifest(report)["passed"] is True


def test_defense_metrics_keep_external_evidence_unclaimed(tmp_path: Path):
    report = generate_defense_metrics(tmp_path)

    assert report["passed"] is True
    assert report["evidence_scope"] == "local_rules_and_local_environment"
    assert "iflytek_spark" in report["external_not_claimed"]
    assert "github_ci" in report["external_not_claimed"]
