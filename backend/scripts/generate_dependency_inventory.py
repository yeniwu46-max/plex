"""Generate a machine-readable inventory of direct project dependencies."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

KNOWN_LICENSES = {
    "alembic": "MIT",
    "flask": "BSD-3-Clause",
    "flask-cors": "MIT",
    "flask-jwt-extended": "MIT",
    "flask-sqlalchemy": "BSD-3-Clause",
    "jsonschema": "MIT",
    "marshmallow": "MIT",
    "marshmallow-sqlalchemy": "MIT",
    "pymysql": "MIT",
    "pytest": "MIT",
    "python-dateutil": "Apache-2.0 OR BSD-3-Clause",
    "python-dotenv": "BSD-3-Clause",
    "requests": "Apache-2.0",
    "werkzeug": "BSD-3-Clause",
}


def _normalise_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _metadata_license(package_name: str) -> str | None:
    try:
        package_metadata = metadata.metadata(package_name)
    except metadata.PackageNotFoundError:
        return None
    expression = package_metadata.get("License-Expression")
    if expression and expression.strip().upper() != "UNKNOWN":
        return expression.strip()
    license_value = package_metadata.get("License")
    if license_value and license_value.strip().upper() != "UNKNOWN":
        first_line = license_value.strip().splitlines()[0]
        if len(first_line) <= 120:
            return first_line
    for classifier in package_metadata.get_all("Classifier", []):
        prefix = "License :: "
        if classifier.startswith(prefix):
            return classifier.removeprefix(prefix)
    return None


def _python_requirements(path: Path, scope: str) -> list[dict]:
    dependencies = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("git+"):
            commit_match = re.search(r"@([0-9a-f]{40})(?:#|$)", line, re.IGNORECASE)
            dependencies.append({
                "name": "crewai",
                "scope": scope,
                "declared": line,
                "resolved_version": None,
                "license": "MIT",
                "source": "git",
                "version_pinned": bool(commit_match),
                "installed": False,
            })
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        name = match.group(1) if match else line
        declared_version = match.group(2) if match else None
        try:
            installed_version = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed_version = None
        normalised = _normalise_name(name)
        dependencies.append({
            "name": name,
            "scope": scope,
            "declared": line,
            "resolved_version": installed_version or declared_version,
            "license": _metadata_license(name) or KNOWN_LICENSES.get(normalised),
            "source": "pypi",
            "version_pinned": declared_version is not None,
            "installed": installed_version is not None,
        })
    return dependencies


def _node_dependencies() -> list[dict]:
    package_json = json.loads((REPO_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPO_ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    lock_packages = lock.get("packages", {})
    dependencies = []
    for scope_key, scope in (("dependencies", "runtime"), ("devDependencies", "development")):
        for name, declared in sorted(package_json.get(scope_key, {}).items()):
            resolved = lock_packages.get(f"node_modules/{name}", {})
            dependencies.append({
                "name": name,
                "scope": scope,
                "declared": declared,
                "resolved_version": resolved.get("version"),
                "license": resolved.get("license"),
                "source": "npm",
                "version_pinned": bool(resolved.get("version")),
                "installed": (REPO_ROOT / "frontend/node_modules" / name).exists(),
            })
    return dependencies


def generate(output: Path) -> dict:
    python_runtime = _python_requirements(BACKEND_ROOT / "requirements.txt", "runtime")
    python_optional = _python_requirements(
        BACKEND_ROOT / "requirements-agents.txt",
        "optional-agent-runtime",
    )
    node = _node_dependencies()
    release_dependencies = python_runtime + node
    missing_licenses = [
        f"{item['source']}:{item['name']}"
        for item in release_dependencies
        if not item["license"]
    ]
    unresolved_versions = [
        f"{item['source']}:{item['name']}"
        for item in release_dependencies
        if not item["resolved_version"]
    ]
    optional_warnings = [
        "optional CrewAI Git dependency is not pinned to an immutable commit"
        for item in python_optional
        if item["source"] == "git" and not item["version_pinned"]
    ]
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": not missing_licenses and not unresolved_versions,
        "summary": {
            "python_runtime": len(python_runtime),
            "python_optional": len(python_optional),
            "node_runtime": sum(item["scope"] == "runtime" for item in node),
            "node_development": sum(item["scope"] == "development" for item in node),
            "missing_licenses": len(missing_licenses),
            "unresolved_versions": len(unresolved_versions),
        },
        "issues": {
            "missing_licenses": missing_licenses,
            "unresolved_versions": unresolved_versions,
            "optional_warnings": optional_warnings,
        },
        "dependencies": {
            "python_runtime": python_runtime,
            "python_optional": python_optional,
            "node": node,
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
        default=BACKEND_ROOT / "reports/a3-submission/dependency-inventory.json",
    )
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
