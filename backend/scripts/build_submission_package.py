"""Build PLEX A3 competition submission archive (<= 1 GB compressed).

Organizes runnable multi-agent source, datasets, config samples, docs and reports
into a standard directory layout, then creates a zip archive.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
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
    "outputs",
    "output",
    "test-results",
}
EXCLUDED_PREFIXES = (".venv",)
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.spark.local",
    "credentials.json",
}
MAX_COMPRESSED_BYTES = 1024 * 1024 * 1024  # 1 GB

SOURCE_ROOT_FILES = (
    "README.md",
    "start.bat",
    "TECH_PLAN.md",
    "backend_api_design.md",
    "frontend_design_v2.md",
    "技术选型与约定.md",
    "AGENTS.md",
    ".gitignore",
    ".github",
)

SOURCE_DIRS = ("backend", "frontend", "picture", "ppplex")

DATA_PATHS = (
    "backend/data",
    "data",
)

CONFIG_SAMPLES = (
    ("backend/.env.example", "backend.env.example"),
    ("frontend/.env.development", "frontend.env.development"),
    ("frontend/.env.example", "frontend.env.example"),
)

DOCS_PATH = "docs/submission"

REPORT_PATHS = (
    "backend/reports",
    "frontend/reports",
)


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
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def _copy_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy included files under src into dst; return (file_count, total_bytes)."""
    count = 0
    total = 0
    if not src.exists():
        return count, total
    if src.is_file():
        if _include(src):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            size = dst.stat().st_size
            return 1, size
        return count, total
    for path in sorted(src.rglob("*")):
        if not path.is_file() or not _include(path):
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
        total += target.stat().st_size
    return count, total


def _write_readme(dest: Path, meta: dict) -> None:
    content = f"""# PLEX A3 多智能体提交包

**生成时间（UTC）**：{meta["generated_at"]}  
**Git 提交**：{meta.get("git_commit") or "unknown"}  
**分支**：{meta.get("git_branch") or "unknown"}  

## 目录说明

| 目录/文件 | 内容 |
|---|---|
| `source/` | 可完整运行的项目源码（Flask 后端 + Vue 3 前端 + 多智能体模块） |
| `data/` | 课程知识库（RAG 文档）、评测数据集、Learning Core 演示 SQL |
| `config-samples/` | 环境变量与模型部署配置样例（不含真实密钥） |
| `docs/` | 初赛配套文档（需求、设计、多智能体、测试、部署等） |
| `reports/` | 本地评测、安全、性能与 bundle 报告 |
| `release-manifest.json` | 候选文件 SHA-256 清单 |

## 快速运行（Windows）

```bat
cd source
start.bat --check
start.bat
```

浏览器访问 `http://localhost:5180`。默认演示账号见 `source/README.md`。

## 手动运行

```bash
cd source/backend
pip install -r requirements.txt
pip install -r requirements-agents.txt
python manage.py init
python run.py
```

另开终端：

```bash
cd source/frontend
npm ci
npm run dev
```

## 多智能体相关入口

- 智能体实现：`source/backend/agents/`
- 编排服务：`source/backend/app/services/agent_orchestrator.py`
- 资源审核：`source/backend/app/services/resource_audit/`
- 课程知识库：`data/backend/data/rag_docs/`
- 模型配置样例：`config-samples/backend.env.example`

## 体积说明

- 未压缩文件数：{meta["file_count"]}
- 未压缩总大小：{meta["uncompressed_mb"]:.2f} MB
- 压缩包大小：{meta["compressed_mb"]:.2f} MB（上限 1024 MB）

## 排除项

已排除虚拟环境、`node_modules`、`.env` 真实密钥、数据库文件、日志与开发工具缓存。
"""
    (dest / "README.md").write_text(content, encoding="utf-8")


def build(output_zip: Path, staging_root: Path | None = None) -> dict:
    package_name = "PLEX-A3-submission"
    staging = staging_root or (output_zip.parent / package_name)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    stats = {"file_count": 0, "total_bytes": 0}

    def add(path: Path, dest: Path) -> None:
        nonlocal stats
        c, b = _copy_tree(path, dest)
        stats["file_count"] += c
        stats["total_bytes"] += b

    source = staging / "source"
    for name in SOURCE_ROOT_FILES:
        add(REPO_ROOT / name, source / name)
    for name in SOURCE_DIRS:
        add(REPO_ROOT / name, source / name)

    data = staging / "data"
    for rel in DATA_PATHS:
        add(REPO_ROOT / rel, data / rel)

    config_dir = staging / "config-samples"
    for src_rel, dst_name in CONFIG_SAMPLES:
        src = REPO_ROOT / src_rel
        if src.exists() and _include(src):
            config_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, config_dir / dst_name)
            stats["file_count"] += 1
            stats["total_bytes"] += src.stat().st_size

    add(REPO_ROOT / DOCS_PATH, staging / "docs")

    reports = staging / "reports"
    for rel in REPORT_PATHS:
        add(REPO_ROOT / rel, reports / Path(rel).name)

    manifest_src = BACKEND_ROOT / "reports/a3-submission/release-manifest.json"
    if manifest_src.exists():
        shutil.copy2(manifest_src, staging / "release-manifest.json")
        stats["file_count"] += 1
        stats["total_bytes"] += manifest_src.stat().st_size

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "file_count": stats["file_count"],
        "uncompressed_mb": stats["total_bytes"] / (1024 * 1024),
    }
    _write_readme(staging, {**meta, "compressed_mb": 0.0})

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(staging.parent).as_posix()
                zf.write(path, arcname)

    compressed = output_zip.stat().st_size
    meta["compressed_mb"] = compressed / (1024 * 1024)
    meta["compressed_bytes"] = compressed
    meta["passed_size_limit"] = compressed <= MAX_COMPRESSED_BYTES
    meta["output_zip"] = str(output_zip.resolve())
    meta["staging_dir"] = str(staging.resolve())

    _write_readme(staging, meta)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(staging.parent).as_posix()
                zf.write(path, arcname)

    meta_path = staging / "package-meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(output_zip, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(meta_path, f"{package_name}/package-meta.json")

    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build PLEX A3 submission zip package.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT.parent / "PLEX-A3-submission.zip",
        help="Output zip path (default: ../PLEX-A3-submission.zip)",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep extracted staging directory after zipping.",
    )
    args = parser.parse_args()

    result = build(args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.keep_staging:
        staging = Path(result["staging_dir"])
        if staging.exists():
            shutil.rmtree(staging)

    if not result["passed_size_limit"]:
        print(f"ERROR: compressed size exceeds 1 GB limit.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(0)
