"""Generate a safe candidate-submission manifest with SHA-256 hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

EXCLUDED_PARTS = {
    ".agents",
    ".codex",
    ".git",
    ".npm-cache",
    ".codegraph",
    ".cursor",
    ".playwright-cli",
    ".playwright-mcp",
    ".turix",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "instance",
    "uploads",
    # 非候选源码/历史归档目录；其中包含数据库转储、运行时二进制和旧版演示素材。
    "_incoming_data",
    "outputs",
    "runtime",
    "SoftwareCopyright-Skill",
    "PLEX-A3-supporting-documents-20260720",
    "demo",
    "runtime-samples",
    "output",
}
EXCLUDED_PREFIXES = (".venv",)
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
# 原始 SQL 转储不属于可运行参赛包，且常超过 25 MB；课程 RAG 文档已提供可审计知识源。
EXCLUDED_SUFFIXES.add(".sql")
EXCLUDED_SUFFIXES.add(".pyd")
SECRET_NAMES = {".env", ".env.local", ".env.production", "credentials.json"}
POST_MANIFEST_REPORTS = {"release-manifest.json", "release-readiness.json"}
MAX_FILE_BYTES = 25 * 1024 * 1024


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _include(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if any(part.startswith(EXCLUDED_PREFIXES) for part in relative.parts):
        return False
    if path.name in SECRET_NAMES:
        return False
    if path.name in POST_MANIFEST_REPORTS and "a3-submission" in relative.parts:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def _candidate_files() -> list[Path]:
    return [
        path
        for path in sorted(REPO_ROOT.rglob("*"))
        if _include(path)
    ]


def verify_manifest(report: dict) -> dict:
    expected = {item["path"]: item for item in report.get("files", [])}
    current_paths = {
        path.relative_to(REPO_ROOT).as_posix(): path
        for path in _candidate_files()
    }
    missing = sorted(set(expected) - set(current_paths))
    unexpected = sorted(set(current_paths) - set(expected))
    changed = []
    for relative in sorted(set(expected) & set(current_paths)):
        digest = hashlib.sha256(current_paths[relative].read_bytes()).hexdigest()
        if digest != expected[relative].get("sha256"):
            changed.append(relative)
    return {
        "passed": not missing and not unexpected and not changed,
        "missing": missing,
        "unexpected": unexpected,
        "changed": changed,
    }


def generate(output: Path) -> dict:
    files = []
    oversized = []
    for path in _candidate_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": relative, "bytes": size, "sha256": digest})
        if size > MAX_FILE_BYTES:
            oversized.append(relative)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": not oversized,
        "release": {
            "git_commit": _git_value("rev-parse", "HEAD"),
            "git_branch": _git_value("branch", "--show-current"),
            "worktree_dirty": bool(_git_value("status", "--porcelain")),
        },
        "summary": {
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "oversized_count": len(oversized),
        },
        "excluded": {
            "directories": sorted(EXCLUDED_PARTS),
            "directory_prefixes": list(EXCLUDED_PREFIXES),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
            "secret_names": sorted(SECRET_NAMES),
            "post_manifest_reports": sorted(POST_MANIFEST_REPORTS),
        },
        "oversized_files": oversized,
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "reports/a3-submission/release-manifest.json",
    )
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps({
        "passed": result["passed"],
        "release": result["release"],
        "summary": result["summary"],
        "oversized_files": result["oversized_files"],
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
